#!/usr/bin/env python3
"""Prepare truth-free, opaque analyzer inputs from RIFT-GOLD-120.

This benchmark-preparation step reads only case sources and compile commands.
It discovers the explicit source/AP markers and derives the fixture's public
controllability boundary from whether the marked declaration receives
``read_arg``.  It never reads ground_truth, category, relation, expected edge,
recipe, prerequisite, or frontier labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
DEFAULT_GOLD = WORKSPACE / "benchmark" / "rift" / "gold"
TEMP_ROOT = Path("/tmp")

HEADER = """/*
 * Opaque analyzer input {case_id}.
 * Evaluation metadata is intentionally excluded.
 * Source and AP marker comments are preserved.
 */
"""
HEADER_PATTERN = re.compile(r"\A/\*.*?\*/\n", re.DOTALL)
TOKEN_PATTERN = r"(?<![A-Za-z0-9_]){token}(?![A-Za-z0-9_])"
FORBIDDEN_OUTPUT_PATTERNS = (
    re.compile(r"RIFT-GOLD-[0-9]{3}", re.IGNORECASE),
    re.compile(r"\b(?:MUST_INFLUENCE|MAY_INFLUENCE|NO_INFLUENCE)\b", re.IGNORECASE),
    re.compile(r"\bnegative\b", re.IGNORECASE),
    re.compile(
        r"\b(?:direct_data|indirect_data|control_only|alias_object_field|"
        r"config_threshold|message_parser_state|async_timer_callback_queue|"
        r"setup_mode_prerequisite|timing_drop_repeat_reorder|"
        r"uncontrollable_false_correlation|one_input_multi_ap|joint_inputs)\b",
        re.IGNORECASE,
    ),
)


class PreparationError(ValueError):
    """Raised when the frozen corpus cannot be sanitized without ambiguity."""


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def assert_no_output_leakage(text: str, label: str) -> None:
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        match = pattern.search(text)
        if match:
            raise PreparationError(
                f"sanitized {label} leaks forbidden token {match.group(0)!r}"
            )


def sanitize_source(text: str, opaque_case_id: str) -> str:
    match = HEADER_PATTERN.match(text)
    if not match:
        raise PreparationError("source lacks the expected generated header")
    replacement = HEADER.format(case_id=opaque_case_id)
    if match.group(0).count("\n") != replacement.count("\n"):
        raise PreparationError("sanitized header would change anchor line numbers")
    sanitized = replacement + text[match.end() :]
    if "RIFT_SOURCE:" not in sanitized or "RIFT_AP:" not in sanitized:
        raise PreparationError("source/AP markers were lost during sanitization")
    assert_no_output_leakage(sanitized, opaque_case_id)
    return sanitized


def locate_anchor(
    source: str,
    *,
    kind: str,
    identifier: str,
    symbol: str,
    relative_file: str,
) -> dict[str, Any]:
    marker = f"RIFT_{kind}:{identifier}"
    lines = source.splitlines()
    marker_lines = [index for index, line in enumerate(lines) if marker in line]
    if len(marker_lines) != 1:
        raise PreparationError(
            f"expected exactly one {marker}, found {len(marker_lines)}"
        )

    token_expression = re.compile(TOKEN_PATTERN.format(token=re.escape(symbol)))
    for index in range(marker_lines[0] + 1, min(marker_lines[0] + 6, len(lines))):
        token = token_expression.search(lines[index])
        if token:
            return {
                "id": identifier,
                "symbol": symbol,
                "marker": marker,
                "location": {
                    "file": relative_file,
                    "line": index + 1,
                    "column": token.start() + 1,
                },
            }
    raise PreparationError(f"could not locate token {symbol!r} after {marker}")


def load_source_records(gold_root: Path) -> list[dict[str, Any]]:
    compile_commands = read_json(gold_root / "compile_commands.json")
    if not isinstance(compile_commands, list):
        raise PreparationError("gold compile_commands is not a list")

    commands_by_file: dict[Path, dict[str, Any]] = {}
    for command in compile_commands:
        file_path = Path(command["file"])
        if not file_path.is_absolute():
            file_path = Path(command["directory"]) / file_path
        resolved = file_path.resolve()
        if resolved in commands_by_file:
            raise PreparationError(f"duplicate compile command for {resolved}")
        commands_by_file[resolved] = command

    records: list[dict[str, Any]] = []
    source_hashes: set[str] = set()
    source_paths = sorted(
        path
        for path in (gold_root / "cases").iterdir()
        if path.is_file() and path.suffix in {".c", ".cpp"}
    )
    if not source_paths:
        raise PreparationError("case source directory is empty")
    for source_path in source_paths:
        source_hash = sha256_file(source_path)
        if source_hash in source_hashes:
            raise PreparationError("source hashes are not unique; opaque ordering is ambiguous")
        source_hashes.add(source_hash)
        command = commands_by_file.get(source_path.resolve())
        if command is None:
            raise PreparationError(f"missing compile command for {source_path}")
        records.append(
            {
                "source_path": source_path,
                "source_sha256": source_hash,
                "source_text": source_path.read_text(encoding="utf-8"),
                "compile_command": command,
            }
        )

    # Hash order intentionally breaks the category/variant grouping of original filenames.
    records.sort(key=lambda item: (item["source_sha256"], item["source_path"].name))
    for index, record in enumerate(records, start=1):
        record["opaque_case_id"] = f"case_{index:03d}"
    return records


def rewrite_compile_command(
    original: dict[str, Any],
    *,
    original_source: Path,
    renamed_source: str,
    renamed_object: str,
    gold_root: Path,
) -> dict[str, Any]:
    arguments = original.get("arguments")
    if not isinstance(arguments, list) or not arguments:
        raise PreparationError("compile command must use a non-empty arguments array")

    rewritten: list[str] = []
    replaced_source = 0
    replaced_output = 0
    index = 0
    while index < len(arguments):
        argument = str(arguments[index])
        if argument == "-o":
            if index + 1 >= len(arguments):
                raise PreparationError("compile command ends after -o")
            rewritten.extend(["-o", renamed_object])
            replaced_output += 1
            index += 2
            continue

        candidate = Path(argument)
        is_source = False
        if candidate.is_absolute():
            is_source = candidate.resolve() == original_source.resolve()
        elif argument == original_source.name or argument == str(original_source):
            is_source = True
        if is_source:
            rewritten.append(renamed_source)
            replaced_source += 1
        else:
            if str(gold_root.resolve()) in argument or "RIFT-GOLD-" in argument:
                raise PreparationError(f"compile argument leaks gold path: {argument}")
            rewritten.append(argument)
        index += 1

    if replaced_source != 1 or replaced_output != 1:
        raise PreparationError(
            f"compile rewrite expected one source/output, got {replaced_source}/{replaced_output}"
        )
    return {"directory": ".", "file": renamed_source, "arguments": rewritten}


def discover_anchors(source: str, *, kind: str, relative_file: str) -> list[dict[str, Any]]:
    marker_pattern = re.compile(rf"RIFT_{kind}:([a-z][a-z0-9_]*)")
    identifiers = marker_pattern.findall(source)
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise PreparationError(f"{kind} marker IDs are absent or duplicated")
    return [
        locate_anchor(
            source,
            kind=kind,
            identifier=identifier,
            symbol=identifier,
            relative_file=relative_file,
        )
        for identifier in sorted(identifiers)
    ]


def derive_controllability(source: str, anchors: list[dict[str, Any]]) -> list[dict[str, str]]:
    lines = source.splitlines()
    result = []
    for anchor in anchors:
        declaration = lines[anchor["location"]["line"] - 1]
        classification = "EXTERNAL" if "read_arg(" in declaration else "INTERNAL"
        result.append({"source_id": anchor["id"], "classification": classification})
    return result


def build_sanitized_case(record: dict[str, Any], gold_root: Path) -> tuple[dict[str, Any], str]:
    opaque = record["opaque_case_id"]
    extension = record["source_path"].suffix
    relative_source = f"sources/{opaque}{extension}"
    relative_object = f"build/{opaque}.o"
    sanitized_source = sanitize_source(record["source_text"], opaque)
    source_anchors = discover_anchors(
        sanitized_source, kind="SOURCE", relative_file=relative_source
    )
    ap_anchors = discover_anchors(
        sanitized_source, kind="AP", relative_file=relative_source
    )
    controllability = derive_controllability(sanitized_source, source_anchors)
    compile_command = rewrite_compile_command(
        record["compile_command"],
        original_source=record["source_path"],
        renamed_source=relative_source,
        renamed_object=relative_object,
        gold_root=gold_root,
    )
    encoded_source = sanitized_source.encode("utf-8")
    case = {
        "case_id": opaque,
        "source": {
            "file": relative_source,
            "sha256": sha256_bytes(encoded_source),
        },
        "compile_command": compile_command,
        "source_anchors": source_anchors,
        "ap_anchors": ap_anchors,
        "controllability": controllability,
    }
    return case, sanitized_source


def require_safe_output(output: Path) -> Path:
    resolved = output.resolve()
    temporary_root = TEMP_ROOT.resolve()
    try:
        resolved.relative_to(temporary_root)
    except ValueError as error:
        raise PreparationError(f"output must be below {temporary_root}: {resolved}") from error
    if resolved == temporary_root:
        raise PreparationError("refusing to use the temporary root itself as output")
    if resolved.exists():
        raise PreparationError(f"output already exists; refusing to overwrite: {resolved}")
    return resolved


def prepare(gold_root: Path, output: Path) -> dict[str, Any]:
    gold_root = gold_root.resolve()
    output = require_safe_output(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=str(output.parent))
    )
    completed = False
    try:
        records = load_source_records(gold_root)
        cases: list[dict[str, Any]] = []
        compile_commands: list[dict[str, Any]] = []
        for record in records:
            case, source = build_sanitized_case(record, gold_root)
            cases.append(case)
            compile_commands.append(case["compile_command"])
            write_bytes(staging / case["source"]["file"], source.encode("utf-8"))

        manifest = {
            "schema_version": "rift.analyzer-input.v1",
            "evaluation_track": "PAIR_CLASSIFICATION_DIAGNOSTIC",
            "binding_mode": "GIVEN_CANDIDATE_ANCHORS_NOT_SCORED",
            "controllability_mode": "GIVEN_CONTROLLABILITY_NOT_SCORED",
            "cases": cases,
        }
        manifest_bytes = canonical_json(manifest)
        compile_bytes = canonical_json(compile_commands)
        assert_no_output_leakage(manifest_bytes.decode("utf-8"), "analyzer_input.json")
        assert_no_output_leakage(compile_bytes.decode("utf-8"), "compile_commands.json")
        write_bytes(staging / "analyzer_input.json", manifest_bytes)
        write_bytes(staging / "compile_commands.json", compile_bytes)
        (staging / "build").mkdir()

        os.replace(staging, output)
        completed = True
        return {
            "output": str(output),
            "cases": len(cases),
            "source_anchors": sum(len(case["source_anchors"]) for case in cases),
            "ap_anchors": sum(len(case["ap_anchors"]) for case in cases),
            "manifest_sha256": sha256_bytes(manifest_bytes),
        }
    finally:
        # A failed staging tree is retained for diagnosis; no recursive deletion is performed.
        if not completed and staging.exists():
            print(f"PARTIAL staging retained at {staging}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument(
        "--output",
        type=Path,
        help="new output directory below /tmp; defaults to a fresh mkdtemp path",
    )
    args = parser.parse_args()

    output = args.output
    if output is None:
        placeholder = Path(
            tempfile.mkdtemp(prefix="rift-m3-reservation-", dir=str(TEMP_ROOT))
        )
        placeholder.rmdir()
        output = placeholder
    try:
        result = prepare(args.gold, output)
    except (OSError, PreparationError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "PASS",
        f"output={result['output']}",
        f"cases={result['cases']}",
        f"source_anchors={result['source_anchors']}",
        f"ap_anchors={result['ap_anchors']}",
        f"manifest_sha256={result['manifest_sha256']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
