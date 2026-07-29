#!/usr/bin/env python3
"""Derive the SVF AE portability-probe selectors from the frozen Clang TU.

The script consumes the existing compile database and emits only evidence for
the real `main` definition and the AST nodes on ae.cpp lines 848 and 850.  It
does not modify the SVF checkout or its build tree.
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


TARGET_SUFFIX = "/svf-llvm/tools/AE/ae.cpp"
TARGET_LINES = {848, 850}


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
        raise RuntimeError(f"expected exactly one AE TU, found {len(entries)}")
    entry = entries[0]
    source = pathlib.Path(entry["file"]).resolve(strict=True)
    source_bytes = source.read_bytes()
    line_starts = [0]
    line_starts.extend(index + 1 for index, byte in enumerate(source_bytes) if byte == 10)

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
    documents = json_stream(completed.stdout)
    main_definitions = [
        document
        for document in documents
        if document.get("kind") == "FunctionDecl"
        and document.get("name") == "main"
        and document.get("loc", {}).get("line") == 843
        and document.get("type", {}).get("qualType") == "int (int, char **)"
    ]
    if len(main_definitions) != 1:
        raise RuntimeError(
            f"expected exactly one target main definition, found {len(main_definitions)}"
        )

    evidence_nodes: list[dict[str, Any]] = []
    for node in walk(main_definitions[0]):
        source_range = node.get("range", {})
        begin = source_range.get("begin", {})
        end = source_range.get("end", {})
        if "offset" not in begin:
            continue
        begin_line, begin_column = line_column(begin["offset"])
        end_line, end_column = line_column(end.get("offset", begin["offset"]))
        if begin_line not in TARGET_LINES:
            continue
        end_column += max(int(end.get("tokLen", 1)), 1) - 1
        referenced = node.get("referencedDecl")
        evidence_nodes.append(
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
                        "canonical_type": referenced.get("type", {}).get("qualType"),
                    }
                    if isinstance(referenced, dict)
                    else None
                ),
            }
        )

    output = {
        "schema_version": "rift.portability.svf.ast-evidence.v1",
        "status": "PORTABILITY_PROBE_NOT_REQUIREMENT",
        "source": str(source),
        "source_sha256": sha256_file(source),
        "compile_database": str(database_path),
        "compile_database_sha256": sha256_file(database_path),
        "translation_unit_entry_sha256": hashlib.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "clang_command": command,
        "clang_exit_code": completed.returncode,
        "clang_stderr": completed.stderr,
        "wall_seconds": round(wall_seconds, 6),
        "main_signature": main_definitions[0]["type"]["qualType"],
        "nodes": evidence_nodes,
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"PASS source={source} nodes={len(evidence_nodes)} "
        f"output={options.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
