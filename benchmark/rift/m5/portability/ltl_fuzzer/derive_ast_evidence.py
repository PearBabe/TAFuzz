#!/usr/bin/env python3
"""Derive the LTL-Fuzzer portability probe from a Clang 18 compile database.

The script selects the real ``src/main.cc`` translation unit, replays its
compile command as a syntax-only JSON AST dump, checks the frozen ``main``
signature and ``argc < 2`` nodes, and writes both a one-entry compile database
and a compact evidence document.  It never edits the external checkout.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import pathlib
import shlex
import subprocess
import sys
import time
from typing import Any, Iterator


TARGET_SUFFIX = "/src/main.cc"
MAIN_LINE = 9
TARGET_LINE = 10
EXPECTED_COMMIT = "716ac301fa3a8ea39814bc80eeebba49c19c1378"
EXPECTED_TREE = "ee7f4a651abf3e7f6104be92751e4880385ead85"
EXPECTED_ARGC_USR = "c:main.cc@156@F@main#I#**C#@argc"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def walk(node: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield node
    for child in node.get("inner", []):
        yield from walk(child)


def json_stream(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    offset = 0
    documents: list[dict[str, Any]] = []
    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset == len(text):
            break
        value, offset = decoder.raw_decode(text, offset)
        if isinstance(value, dict):
            documents.append(value)
    return documents


def ast_command(entry: dict[str, Any]) -> list[str]:
    arguments = (
        list(entry["arguments"])
        if "arguments" in entry
        else shlex.split(entry["command"])
    )
    result: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "-c" or argument == entry["file"]:
            index += 1
            continue
        if argument == "-o":
            index += 2
            continue
        result.append(argument)
        index += 1
    result.extend(
        [
            "-fsyntax-only",
            "-Xclang",
            "-ast-dump=json",
            "-Xclang",
            "-ast-dump-filter=main",
            entry["file"],
        ]
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile-db", type=pathlib.Path, required=True)
    parser.add_argument("--single-tu-db", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    options = parser.parse_args()

    database_path = options.compile_db.resolve(strict=True)
    database = json.loads(database_path.read_text(encoding="utf-8"))
    entries = [
        entry
        for entry in database
        if pathlib.Path(entry["file"]).as_posix().endswith(TARGET_SUFFIX)
    ]
    if len(entries) != 1:
        raise RuntimeError(f"expected exactly one main.cc TU, found {len(entries)}")
    entry = entries[0]
    source = pathlib.Path(entry["file"]).resolve(strict=True)
    repository = pathlib.Path(
        subprocess.run(
            ["git", "-C", str(source.parent), "rev-parse", "--show-toplevel"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.strip()
    ).resolve(strict=True)
    commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD^{commit}"],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD^{tree}"],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    tracked_status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=no"],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    if commit != EXPECTED_COMMIT or tree != EXPECTED_TREE or tracked_status:
        raise RuntimeError(
            "frozen checkout mismatch: "
            f"commit={commit} tree={tree} tracked_status={tracked_status!r}"
        )
    source_bytes = source.read_bytes()
    line_starts = [0]
    line_starts.extend(
        index + 1 for index, byte in enumerate(source_bytes) if byte == 10
    )

    def line_column(offset: int) -> tuple[int, int]:
        line_index = bisect.bisect_right(line_starts, offset) - 1
        return line_index + 1, offset - line_starts[line_index] + 1

    command = ast_command(entry)
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=entry["directory"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    wall_seconds = time.monotonic() - started
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        return completed.returncode

    definitions = [
        document
        for document in json_stream(completed.stdout)
        if document.get("kind") == "FunctionDecl"
        and document.get("name") == "main"
        and document.get("loc", {}).get("line") == MAIN_LINE
        and document.get("type", {}).get("qualType") == "int (int, char **)"
    ]
    if len(definitions) != 1:
        raise RuntimeError(
            f"expected exactly one frozen main definition, found {len(definitions)}"
        )

    nodes: list[dict[str, Any]] = []
    for node in walk(definitions[0]):
        source_range = node.get("range", {})
        begin = source_range.get("begin", {})
        end = source_range.get("end", {})
        if "offset" not in begin:
            continue
        begin_line, begin_column = line_column(begin["offset"])
        if begin_line != TARGET_LINE:
            continue
        end_line, end_column = line_column(end.get("offset", begin["offset"]))
        end_column += max(int(end.get("tokLen", 1)), 1) - 1
        referenced = node.get("referencedDecl")
        nodes.append(
            {
                "kind": node.get("kind"),
                "opcode": node.get("opcode"),
                "value_category": node.get("valueCategory"),
                "canonical_type": node.get("type", {}).get("qualType"),
                "begin": {"line": begin_line, "column": begin_column},
                "end": {"line": end_line, "column": end_column},
                "referenced_decl": (
                    {
                        "kind": referenced.get("kind"),
                        "name": referenced.get("name"),
                        "canonical_type": referenced.get("type", {}).get(
                            "qualType"
                        ),
                    }
                    if isinstance(referenced, dict)
                    else None
                ),
            }
        )

    required = {
        ("BinaryOperator", "<", "bool", 8, 15),
        ("DeclRefExpr", None, "int", 8, 11),
        ("IntegerLiteral", None, "int", 15, 15),
    }
    observed = {
        (
            node["kind"],
            node["opcode"],
            node["canonical_type"],
            node["begin"]["column"],
            node["end"]["column"],
        )
        for node in nodes
    }
    missing = sorted(required - observed, key=repr)
    if missing:
        raise RuntimeError(f"missing frozen target AST facts: {missing!r}")
    argc_refs = [
        node
        for node in nodes
        if node["kind"] == "DeclRefExpr"
        and node["referenced_decl"]
        and node["referenced_decl"]["name"] == "argc"
        and node["referenced_decl"]["kind"] == "ParmVarDecl"
    ]
    if len(argc_refs) != 1:
        raise RuntimeError(f"expected exactly one argc reference, found {len(argc_refs)}")

    options.single_tu_db.parent.mkdir(parents=True, exist_ok=True)
    options.single_tu_db.write_text(
        json.dumps([entry], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output = {
        "schema_version": "rift.portability.ltl-fuzzer.ast-evidence.v1",
        "status": "PORTABILITY_PROBE_NOT_REQUIREMENT",
        "frozen_source": {
            "repository": str(repository),
            "commit": commit,
            "tree": tree,
            "tracked_worktree_clean": True,
            "untracked_files_ignored": True,
        },
        "source": str(source),
        "source_sha256": sha256_file(source),
        "compile_database": str(database_path),
        "compile_database_sha256": sha256_file(database_path),
        "compile_database_entries": len(database),
        "single_tu_compile_database": str(options.single_tu_db.resolve()),
        "single_tu_compile_database_sha256": sha256_file(options.single_tu_db),
        "translation_unit_entry_sha256": hashlib.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "clang_command": command,
        "clang_exit_code": completed.returncode,
        "clang_stderr_sha256": hashlib.sha256(
            completed.stderr.encode("utf-8")
        ).hexdigest(),
        "clang_stderr_line_count": len(completed.stderr.splitlines()),
        "clang_warning_count": completed.stderr.count("warning:"),
        "wall_seconds": round(wall_seconds, 6),
        "main_signature": definitions[0]["type"]["qualType"],
        "property_selector_usr": {
            "expected": EXPECTED_ARGC_USR,
            "evidence_boundary": "The detached probe verifier must match this exact selector against the emitted Clang semantic index; JSON AST itself does not expose USRs.",
        },
        "nodes": nodes,
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"PASS source={source} nodes={len(nodes)} "
        f"single_tu_db={options.single_tu_db} output={options.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
