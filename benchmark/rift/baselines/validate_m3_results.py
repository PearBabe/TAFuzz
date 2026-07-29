#!/usr/bin/env python3
"""Validate the frozen RIFT-M3 six-baseline result bundle."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import sys
import tarfile
from typing import Any

import jsonschema


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
DEFAULT_RESULTS = HERE / "results" / "m3"
RESULT_SCHEMA = HERE / "baseline_result.schema.json"
METHODS = (
    "adgfuzz-assignment",
    "moonshine-rw",
    "plain-pdg",
    "llvm-def-use",
    "memoryssa-aa",
    "svf-value-flow",
)
M3_CORE_SNAPSHOT = "m3-core-tree.snapshot.tar.gz"
M3_CORE_SNAPSHOT_SHA256 = (
    "ae7448da826e4977c0397af2c00999ccae2e78a47ba6bf3d382d72adbddd4c1c"
)


class ValidationFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def historical_core_hash(snapshot: Path) -> str:
    """Recompute M3's core identity from its immutable source snapshot.

    Comparing a historical run with the live source tree made every later
    milestone invalidate M3 even when none of M3's evidence changed.  The
    snapshot contains exactly the 19 generic source files used by M3; archive
    metadata is ignored and the original canonical byte-level hash algorithm
    is applied to member names and contents.
    """
    require(snapshot.is_file(), f"historical core snapshot is missing: {snapshot}")
    require(
        sha256(snapshot) == M3_CORE_SNAPSHOT_SHA256,
        "historical core snapshot SHA-256 mismatch",
    )
    digest = hashlib.sha256()
    files: list[tuple[str, bytes]] = []
    with tarfile.open(snapshot, "r:gz") as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            require(
                not path.is_absolute() and ".." not in path.parts,
                f"unsafe historical core member: {member.name}",
            )
            require(
                member.isdir() or member.isfile(),
                f"non-regular historical core member: {member.name}",
            )
            if member.isdir():
                continue
            require(
                path.parts and path.parts[0] in {"core", "include", "cli", "schema"},
                f"historical core member outside generic roots: {member.name}",
            )
            stream = archive.extractfile(member)
            require(stream is not None, f"cannot read historical member: {member.name}")
            files.append((path.as_posix(), stream.read()))
    require(len(files) == 19, f"historical core file count changed: {len(files)}")
    names = [name for name, _ in files]
    require(len(names) == len(set(names)), "duplicate historical core member")
    for name, payload in sorted(files):
        relative = name.encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def pair_count(result: dict[str, Any]) -> int:
    identities: set[tuple[str, str, str]] = set()
    for case in result["cases"]:
        for prediction in case["predictions"]:
            identity = (
                case["case_id"], prediction["source_id"], prediction["ap_id"]
            )
            require(identity not in identities, f"duplicate prediction {identity}")
            identities.add(identity)
    return len(identities)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    arguments = parser.parse_args()
    root = arguments.results.resolve(strict=True)
    manifest = load_json(root / "manifest.json")
    require(manifest.get("schema_version") == "rift.m3-run.v1", "manifest schema changed")
    require(
        manifest.get("analyzer_stage_completed_before_evaluation") is True,
        "analyzer/evaluator stage ordering was not recorded",
    )
    require(set(manifest["methods"]) == set(METHODS), "six-method universe changed")
    require(
        sha256(root / "summary.csv") == manifest["summary_sha256"],
        "summary.csv hash mismatch",
    )
    require(
        historical_core_hash(root / M3_CORE_SNAPSHOT) ==
        manifest["core_tree_sha256"],
        "historical core snapshot differs from the frozen M3 run",
    )

    schema = load_json(RESULT_SCHEMA)
    jsonschema.Draft7Validator.check_schema(schema)
    validator = jsonschema.Draft7Validator(schema)
    summaries: dict[str, dict[str, str]] = {}
    with (root / "summary.csv").open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            summaries[row["method"]] = row
    require(set(summaries) == set(METHODS), "summary method universe changed")

    common_binary_hashes: set[str] = set()
    common_input_hashes: set[str] = set()
    total_pairs = 0
    for method in METHODS:
        record = manifest["methods"][method]
        result_path = root / f"{method}.result.json"
        evaluation_path = root / f"{method}.evaluation.json"
        time_path = root / f"{method}.time.txt"
        require(sha256(result_path) == record["result_sha256"], f"{method} result hash mismatch")
        require(
            sha256(evaluation_path) == record["evaluation_sha256"],
            f"{method} evaluation hash mismatch",
        )
        require(sha256(time_path) == record["time_sha256"], f"{method} time hash mismatch")
        result = load_json(result_path)
        evaluation = load_json(evaluation_path)
        errors = sorted(validator.iter_errors(result), key=lambda item: list(item.path))
        require(not errors, f"{method} result schema failure: {errors[0].message if errors else ''}")
        require(len(result["cases"]) == 120, f"{method} case count changed")
        count = pair_count(result)
        require(count == 202, f"{method} pair count changed: {count}")
        total_pairs += count
        require(result["analysis_status"] != "ERROR", f"{method} has ERROR status")
        require(
            evaluation["evidence_identity"]["result_sha256"] == sha256(result_path),
            f"{method} evaluation is not bound to its raw result",
        )
        require(
            evaluation["evidence_identity"]["pair_count"] == 202,
            f"{method} evaluation pair universe changed",
        )
        require(
            summaries[method]["analysis_status"] == result["analysis_status"],
            f"{method} summary status mismatch",
        )
        common_binary_hashes.add(result["analyzer"]["artifact_sha256"])
        common_input_hashes.add(result["input_manifest_sha256"])

    require(
        common_binary_hashes == {manifest["analyzer_binary_sha256"]},
        "methods did not use one analyzer binary",
    )
    require(
        common_input_hashes == {manifest["input_manifest_sha256"]},
        "methods did not use one sanitized input",
    )
    leakage = load_json(root / "no-answer-leakage-final.json")
    require(leakage.get("status") == "PASS", "no-answer runtime audit did not pass")
    require(leakage.get("violations") == [], "no-answer runtime audit has violations")
    with gzip.open(root / "no-answer-leakage-final.trace.gz", "rt", encoding="utf-8") as stream:
        trace = stream.read()
    require("benchmark/rift/gold" not in trace, "runtime trace contains a gold path")
    require("/.codex" not in trace, "runtime trace contains a handoff path")
    require((root / "REPORT_zh.md").is_file(), "M3 report is missing")
    print(
        "PASS",
        f"methods={len(METHODS)}",
        f"cases={len(METHODS) * 120}",
        f"pairs={total_pairs}",
        f"binary_sha256={manifest['analyzer_binary_sha256']}",
        f"core_tree_sha256={manifest['core_tree_sha256']}",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        tarfile.TarError,
        ValidationFailure,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
