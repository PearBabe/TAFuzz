#!/usr/bin/env python3
"""Deterministic milestone-3 corpus integrity checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


CANDIDATE_KEYS = {
    "candidate_id", "system", "source_class", "authority", "document_id", "node_id", "path", "url",
    "commit", "file_sha256", "section_path", "anchor", "line_start", "line_end", "exact_text",
    "text_sha256", "keyword_hits", "prefilter_score", "scan_decision", "review_status",
    "implementation_satisfaction",
}
NODE_KEYS = {
    "record_type", "node_id", "system", "source_class", "document_id", "path", "file_sha256",
    "node_type", "section_path", "anchor", "line_start", "line_end", "text", "text_sha256",
}
EDGE_KEYS = {"record_type", "edge_id", "system", "from", "relation", "to", "confidence", "evidence"}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def validate_system(workspace: Path, system: str, errors: list[str]) -> dict[str, int]:
    system_dir = workspace / "benchmark" / system
    run_dir = workspace / "benchmark/extraction_runs/milestone3" / system
    manifest = json.loads((system_dir / "source_and_corpus_manifest.json").read_text(encoding="utf-8"))
    coverage_path = system_dir / "coverage_ledger.csv"
    graph_path = run_dir / "docgraph.jsonl"
    candidate_path = run_dir / "prefilter_candidates.jsonl"

    sources = manifest["sources"]
    source_by_path = {record["path"]: record for record in sources}
    if len(source_by_path) != len(sources):
        errors.append(f"{system}: duplicate manifest source path")
    coverage_by_path: dict[str, dict[str, str]] = {}
    with coverage_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["path"] in coverage_by_path:
                errors.append(f"{system}: duplicate coverage path {row['path']}")
            coverage_by_path[row["path"]] = row
    if set(source_by_path) != set(coverage_by_path):
        errors.append(f"{system}: manifest/coverage path sets differ")

    for path_text, record in source_by_path.items():
        path = Path(path_text)
        if not path.is_file():
            errors.append(f"{system}: missing source {path}")
            continue
        observed_hash = sha256_path(path)
        if observed_hash != record["sha256"]:
            errors.append(f"{system}: hash drift {path}")
        row = coverage_by_path[path_text]
        if row["file_sha256"] != record["sha256"]:
            errors.append(f"{system}: coverage hash mismatch {path}")
        if row["scan_status"] != "SCREENED_BY_DETERMINISTIC_PREFILTER":
            errors.append(f"{system}: unscreened path {path}")

    node_ids: set[str] = set()
    edge_count = 0
    graph_lines = 0
    with graph_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            graph_lines += 1
            record = json.loads(line)
            expected = NODE_KEYS if record.get("record_type") == "node" else EDGE_KEYS
            if set(record) != expected:
                errors.append(f"{system}: graph keys line {line_no}")
                if len(errors) > 100:
                    break
            if record.get("system") != system:
                errors.append(f"{system}: wrong graph system line {line_no}")
            if record.get("record_type") == "node":
                node_ids.add(record["node_id"])
                if hashlib.sha256(record["text"].encode()).hexdigest() != record["text_sha256"]:
                    errors.append(f"{system}: node text hash line {line_no}")
            else:
                edge_count += 1

    candidate_count = 0
    classes = Counter()
    with candidate_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            candidate_count += 1
            record = json.loads(line)
            if set(record) != CANDIDATE_KEYS:
                errors.append(f"{system}: candidate keys line {line_no}")
            if record.get("system") != system:
                errors.append(f"{system}: wrong candidate system line {line_no}")
            if record.get("node_id") not in node_ids:
                errors.append(f"{system}: missing candidate node line {line_no}")
            if record.get("implementation_satisfaction") != "NOT_ASSESSED":
                errors.append(f"{system}: satisfaction changed line {line_no}")
            if hashlib.sha256(record["exact_text"].encode()).hexdigest() != record["text_sha256"]:
                errors.append(f"{system}: candidate text hash line {line_no}")
            classes[record["source_class"]] += 1
            if len(errors) > 100:
                break

    aggregate = manifest["aggregate"]
    if aggregate["files"] != len(source_by_path):
        errors.append(f"{system}: aggregate file count")
    if aggregate["candidates"] != candidate_count:
        errors.append(f"{system}: aggregate candidate count")
    if aggregate["nodes"] != len(node_ids):
        errors.append(f"{system}: aggregate node count")
    return {
        "files": len(source_by_path),
        "graph_records": graph_lines,
        "nodes": len(node_ids),
        "edges": edge_count,
        "candidates": candidate_count,
        **{f"candidate_{key.lower()}": value for key, value in sorted(classes.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    errors: list[str] = []
    summaries = {
        system: validate_system(workspace, system, errors)
        for system in ("ArduPilot", "PX4")
    }
    expected_heads = {
        "ArduPilot": (workspace / "baseline/ardupilot", "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e"),
        "PX4": (workspace / "baseline/px4", "d6f12ad1c4f70ad3230afd7d86e971421e02fef4"),
        "ArduPilotWiki": (
            workspace / "benchmark/extraction_runs/corpus_sources/ardupilot_wiki",
            "209e532bc97e5a41966f8c9ab483323c264cae08",
        ),
    }
    for name, (repo, expected) in expected_heads.items():
        observed = git_head(repo)
        if observed != expected:
            errors.append(f"{name}: HEAD drift {observed}")
    report = {"status": "PASS" if not errors else "FAIL", "summaries": summaries, "errors": errors}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
