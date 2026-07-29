#!/usr/bin/env python3
"""Verify a generated TAMonitor pipeline artifact manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_COLUMNS = ["category", "key", "sha256", "size_bytes", "evidence"]
REQUIRED_RESULT_SUFFIXES = [
    "pipeline_summary.json",
    "pipeline_summary.csv",
    "pipeline_summary.md",
    "review_packet_verification.json",
    "review_packet_verification.csv",
    "review_packet_verification.md",
    "review_signoff_validation.json",
    "review_signoff_validation.csv",
    "review_signoff_validation.md",
    "paper_review_results.xlsx",
]
OPTIONAL_RESULT_SUFFIXES = [
    "result_stability_audit.json",
    "result_stability_audit.csv",
    "result_stability_audit.md",
]
HARDCODED_RESULT_SUFFIXES = [
    "monitaal_hardcoded_benchmarks.csv",
    "monitaal_hardcoded_benchmarks.json",
    "monitaal_hardcoded_benchmarks.md",
]
SIGNOFF_EVIDENCE_RESULT_SUFFIXES = [
    "review_signoff_evidence_bundle.csv",
    "review_signoff_evidence_bundle.json",
    "review_signoff_evidence_bundle.md",
]
SIGNOFF_ROUNDTRIP_RESULT_SUFFIXES = [
    "signoff_import_roundtrip_audit.csv",
    "signoff_import_roundtrip_audit.json",
    "signoff_import_roundtrip_audit.md",
]
XML_PROOF_OBLIGATION_RESULT_SUFFIXES = [
    "xml_proof_obligations.csv",
    "xml_proof_obligations.json",
    "xml_proof_obligations.md",
]
XML_TRACE_COVERAGE_RESULT_SUFFIXES = [
    "xml_trace_coverage_obligations.csv",
    "xml_trace_coverage_obligations.json",
    "xml_trace_coverage_obligations.md",
]
XML_ORIGINAL_TRACE_GAP_RESULT_SUFFIXES = [
    "xml_original_trace_gaps.csv",
    "xml_original_trace_gaps.json",
    "xml_original_trace_gaps.md",
]
TIMEOUT_RESULT_SUFFIXES = [
    "baseline_timeout_rerun_summary.json",
    "baseline_timeout_rerun.csv",
    "baseline_timeout_rerun.md",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_key_to_path(key: str) -> Path:
    path = Path(key)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def safe_step(step: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in step)


def add_check(
    rows: list[dict[str, str]],
    check_id: str,
    category: str,
    ok: bool,
    expected: str,
    observed: str,
    evidence: str,
    action: str,
) -> None:
    rows.append({
        "check_id": check_id,
        "category": category,
        "status": "PASS" if ok else "FAIL",
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
        "action": action,
    })


def key_has_suffix(keys: set[str], suffix: str) -> bool:
    return any(key.endswith(suffix) for key in keys)


def verify(output_dir: Path, timeout_rerun_dir: Path | None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    checks: list[dict[str, str]] = []
    manifest_csv = output_dir / "pipeline_artifact_manifest.csv"
    manifest_json = output_dir / "pipeline_artifact_manifest.json"
    manifest_md = output_dir / "pipeline_artifact_manifest.md"
    pipeline_summary_path = output_dir / "pipeline_summary.json"

    add_check(
        checks,
        "MANIFEST_FILES_PRESENT",
        "artifact_presence",
        manifest_csv.exists() and manifest_json.exists() and manifest_md.exists(),
        "pipeline_artifact_manifest.csv/json/md exist",
        f"csv={manifest_csv.exists()}; json={manifest_json.exists()}; md={manifest_md.exists()}",
        "pipeline_artifact_manifest.*",
        "Regenerate the full pipeline if the manifest files are missing.",
    )

    rows = read_csv(manifest_csv) if manifest_csv.exists() else []
    columns = list(rows[0].keys()) if rows else []
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    add_check(
        checks,
        "MANIFEST_SCHEMA",
        "schema",
        not missing_columns,
        "manifest CSV has required columns",
        "missing=" + ";".join(missing_columns),
        "pipeline_artifact_manifest.csv",
        "Do not use a manifest with missing hash columns.",
    )

    json_rows: Any = []
    try:
        json_rows = read_json(manifest_json) if manifest_json.exists() else []
    except json.JSONDecodeError as exc:
        json_rows = {"json_error": str(exc)}
    add_check(
        checks,
        "MANIFEST_JSON_ROW_COUNT",
        "schema",
        isinstance(json_rows, list) and len(json_rows) == len(rows),
        "manifest JSON is a list with the same row count as CSV",
        f"csv_rows={len(rows)}; json_rows={len(json_rows) if isinstance(json_rows, list) else 'invalid'}",
        "pipeline_artifact_manifest.csv; pipeline_artifact_manifest.json",
        "Regenerate the manifest if CSV and JSON diverge.",
    )

    keys = [row.get("key", "") for row in rows]
    key_set = set(keys)
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    self_rows = sorted(key for key in keys if Path(key).name.startswith("pipeline_artifact_manifest"))
    add_check(
        checks,
        "MANIFEST_NO_DUPLICATE_KEYS",
        "content",
        not duplicates,
        "manifest keys are unique",
        "duplicates=" + ";".join(duplicates[:12]),
        "pipeline_artifact_manifest.csv",
        "Fix duplicate manifest rows before using hash evidence.",
    )
    add_check(
        checks,
        "MANIFEST_NO_SELF_HASH",
        "content",
        not self_rows,
        "manifest excludes pipeline_artifact_manifest.*",
        "self_rows=" + ";".join(self_rows[:12]),
        "pipeline_artifact_manifest.csv",
        "Keep the manifest non-self-referential.",
    )

    missing_files: list[str] = []
    bad_hashes: list[str] = []
    bad_sizes: list[str] = []
    for row in rows:
        key = row.get("key", "")
        path = manifest_key_to_path(key)
        if not path.exists():
            missing_files.append(key)
            continue
        if sha256_file(path) != row.get("sha256", ""):
            bad_hashes.append(key)
        try:
            expected_size = int(row.get("size_bytes", "-1"))
        except ValueError:
            expected_size = -1
        if path.stat().st_size != expected_size:
            bad_sizes.append(key)
    add_check(
        checks,
        "MANIFEST_HASH_AND_SIZE_MATCH",
        "content",
        not missing_files and not bad_hashes and not bad_sizes,
        "all manifest rows point to existing files with matching sha256 and size",
        f"missing={len(missing_files)}; bad_hashes={len(bad_hashes)}; bad_sizes={len(bad_sizes)}",
        "pipeline_artifact_manifest.csv",
        "Regenerate the pipeline packet if any hash or size does not match.",
    )

    summary = read_json(pipeline_summary_path) if pipeline_summary_path.exists() else {}
    required_suffixes = list(REQUIRED_RESULT_SUFFIXES)
    if summary.get("result_stability_audit") or (output_dir / "result_stability_audit.json").exists():
        required_suffixes.extend(OPTIONAL_RESULT_SUFFIXES)
    missing_required = [suffix for suffix in required_suffixes if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_REQUIRED_RESULT_COVERAGE",
        "coverage",
        not missing_required,
        "manifest covers final review-critical result artifacts",
        "missing=" + ";".join(missing_required),
        "pipeline_artifact_manifest.csv",
        "Add missing review-critical artifacts to the pipeline manifest.",
    )

    artifacts = summary.get("artifacts", {}) if isinstance(summary.get("artifacts"), dict) else {}
    hardcoded_summary = summary.get("monitaal_hardcoded_benchmarks", {})
    hardcoded_expected = (
        "monitaal_hardcoded_benchmarks" in artifacts
        or (isinstance(hardcoded_summary, dict) and bool(hardcoded_summary))
        or any((output_dir / suffix).exists() for suffix in HARDCODED_RESULT_SUFFIXES)
    )
    missing_hardcoded = [suffix for suffix in HARDCODED_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_HARDCODED_BENCHMARK_COVERAGE",
        "coverage",
        (not hardcoded_expected and not any(key.endswith(tuple(HARDCODED_RESULT_SUFFIXES)) for key in key_set))
        or (hardcoded_expected and not missing_hardcoded),
        "manifest hard-coded benchmark coverage matches pipeline hardcoded-evidence state",
        f"hardcoded_expected={hardcoded_expected}; missing=" + ";".join(missing_hardcoded),
        "pipeline_summary.json; pipeline_artifact_manifest.csv",
        "Hash monitaal_hardcoded_benchmarks.csv/json/md when the pipeline advertises hard-coded benchmark evidence.",
    )

    signoff_evidence_summary = summary.get("review_signoff_evidence_bundle", {})
    signoff_evidence_expected = (
        "review_signoff_evidence_bundle" in artifacts
        or (isinstance(signoff_evidence_summary, dict) and bool(signoff_evidence_summary))
        or any((output_dir / suffix).exists() for suffix in SIGNOFF_EVIDENCE_RESULT_SUFFIXES)
    )
    missing_signoff_evidence = [suffix for suffix in SIGNOFF_EVIDENCE_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_SIGNOFF_EVIDENCE_COVERAGE",
        "coverage",
        (not signoff_evidence_expected and not any(key.endswith(tuple(SIGNOFF_EVIDENCE_RESULT_SUFFIXES)) for key in key_set))
        or (signoff_evidence_expected and not missing_signoff_evidence),
        "manifest signoff-evidence coverage matches pipeline signoff-evidence state",
        f"signoff_evidence_expected={signoff_evidence_expected}; missing=" + ";".join(missing_signoff_evidence),
        "pipeline_summary.json; pipeline_artifact_manifest.csv",
        "Hash review_signoff_evidence_bundle.csv/json/md when the pipeline advertises signoff evidence-bundle review artifacts.",
    )

    roundtrip_summary = summary.get("signoff_import_roundtrip_audit", {})
    roundtrip_expected = (
        "signoff_import_roundtrip_audit" in artifacts
        or (isinstance(roundtrip_summary, dict) and bool(roundtrip_summary))
        or any((output_dir / suffix).exists() for suffix in SIGNOFF_ROUNDTRIP_RESULT_SUFFIXES)
    )
    missing_roundtrip = [suffix for suffix in SIGNOFF_ROUNDTRIP_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_SIGNOFF_ROUNDTRIP_COVERAGE",
        "coverage",
        (not roundtrip_expected and not any(key.endswith(tuple(SIGNOFF_ROUNDTRIP_RESULT_SUFFIXES)) for key in key_set))
        or (roundtrip_expected and not missing_roundtrip),
        "manifest signoff-roundtrip coverage matches pipeline roundtrip-audit state",
        f"roundtrip_expected={roundtrip_expected}; missing=" + ";".join(missing_roundtrip),
        "pipeline_summary.json; pipeline_artifact_manifest.csv",
        "Hash signoff_import_roundtrip_audit.csv/json/md when the pipeline advertises synthetic import-roundtrip evidence.",
    )

    experiment_summary = summary.get("experiment_summary", {}) if isinstance(summary.get("experiment_summary"), dict) else {}
    xml_obligation_rows = experiment_summary.get("xml_proof_obligation_rows", summary.get("xml_proof_obligation_rows", 0))
    xml_obligation_expected = (
        xml_obligation_rows not in {0, "0", ""}
        or any((output_dir / suffix).exists() for suffix in XML_PROOF_OBLIGATION_RESULT_SUFFIXES)
    )
    missing_xml_obligations = [suffix for suffix in XML_PROOF_OBLIGATION_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_XML_PROOF_OBLIGATION_COVERAGE",
        "coverage",
        (not xml_obligation_expected and not any(key.endswith(tuple(XML_PROOF_OBLIGATION_RESULT_SUFFIXES)) for key in key_set))
        or (xml_obligation_expected and not missing_xml_obligations),
        "manifest XML proof-obligation coverage matches experiment summary",
        f"xml_obligation_expected={xml_obligation_expected}; missing=" + ";".join(missing_xml_obligations),
        "experiment_summary.json; pipeline_artifact_manifest.csv",
        "Hash xml_proof_obligations.csv/json/md when proof-obligation review artifacts are generated.",
    )

    xml_trace_rows = experiment_summary.get("xml_trace_coverage_rows", summary.get("xml_trace_coverage_rows", 0))
    xml_trace_expected = (
        xml_trace_rows not in {0, "0", ""}
        or any((output_dir / suffix).exists() for suffix in XML_TRACE_COVERAGE_RESULT_SUFFIXES)
    )
    missing_xml_trace = [suffix for suffix in XML_TRACE_COVERAGE_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_XML_TRACE_COVERAGE",
        "coverage",
        (not xml_trace_expected and not any(key.endswith(tuple(XML_TRACE_COVERAGE_RESULT_SUFFIXES)) for key in key_set))
        or (xml_trace_expected and not missing_xml_trace),
        "manifest XML trace-coverage coverage matches experiment summary",
        f"xml_trace_expected={xml_trace_expected}; missing=" + ";".join(missing_xml_trace),
        "experiment_summary.json; pipeline_artifact_manifest.csv",
        "Hash xml_trace_coverage_obligations.csv/json/md when trace-coverage review artifacts are generated.",
    )

    xml_gap_rows = experiment_summary.get("xml_original_trace_gap_rows", summary.get("xml_original_trace_gap_rows", 0))
    xml_gap_expected = (
        xml_gap_rows not in {0, "0", ""}
        or any((output_dir / suffix).exists() for suffix in XML_ORIGINAL_TRACE_GAP_RESULT_SUFFIXES)
    )
    missing_xml_gaps = [suffix for suffix in XML_ORIGINAL_TRACE_GAP_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_XML_ORIGINAL_TRACE_GAPS",
        "coverage",
        (not xml_gap_expected and not any(key.endswith(tuple(XML_ORIGINAL_TRACE_GAP_RESULT_SUFFIXES)) for key in key_set))
        or (xml_gap_expected and not missing_xml_gaps),
        "manifest XML original trace-gap coverage matches experiment summary",
        f"xml_gap_expected={xml_gap_expected}; missing=" + ";".join(missing_xml_gaps),
        "experiment_summary.json; pipeline_artifact_manifest.csv",
        "Hash xml_original_trace_gaps.csv/json/md when original trace-gap review artifacts are generated.",
    )

    command_steps = [command.get("step", "") for command in summary.get("commands", []) if isinstance(command, dict)]
    missing_logs: list[str] = []
    for step in command_steps:
        safe = safe_step(step)
        for stream in ["stdout", "stderr"]:
            suffix = f"pipeline_command_logs/{safe}.{stream}.txt"
            if not key_has_suffix(key_set, suffix):
                missing_logs.append(suffix)
    add_check(
        checks,
        "MANIFEST_COMMAND_LOG_COVERAGE",
        "coverage",
        not missing_logs and bool(command_steps),
        "manifest covers stdout/stderr logs for every pipeline command",
        f"commands={len(command_steps)}; missing_logs=" + ";".join(missing_logs[:12]),
        "pipeline_summary.json; pipeline_artifact_manifest.csv",
        "Hash all command logs so command evidence is reproducible.",
    )

    timeout_value = str(summary.get("timeout_rerun_dir") or "")
    if timeout_rerun_dir is None and timeout_value:
        timeout_rerun_dir = Path(timeout_value)
    timeout_expected = bool(timeout_rerun_dir and timeout_rerun_dir.exists())
    missing_timeout = [suffix for suffix in TIMEOUT_RESULT_SUFFIXES if not key_has_suffix(key_set, suffix)]
    add_check(
        checks,
        "MANIFEST_TIMEOUT_RERUN_COVERAGE",
        "coverage",
        (not timeout_expected and not any(row.get("category") == "timeout_rerun_file" for row in rows))
        or (timeout_expected and not missing_timeout),
        "manifest timeout-rerun coverage matches pipeline timeout rerun state",
        f"timeout_expected={timeout_expected}; missing=" + ";".join(missing_timeout),
        "pipeline_summary.json; pipeline_artifact_manifest.csv",
        "Hash timeout-rerun artifacts when a timeout-rerun directory is part of the packet.",
    )

    categories = Counter(row.get("category", "") for row in rows)
    required_categories = {"result_file", "command_log"}
    if timeout_expected:
        required_categories.add("timeout_rerun_file")
    missing_categories = sorted(category for category in required_categories if categories.get(category, 0) <= 0)
    add_check(
        checks,
        "MANIFEST_CATEGORY_COVERAGE",
        "coverage",
        not missing_categories,
        "manifest has required artifact categories",
        "counts=" + json.dumps(dict(sorted(categories.items())), sort_keys=True),
        "pipeline_artifact_manifest.csv",
        "Regenerate manifest if an expected artifact category is empty.",
    )

    status_counts = Counter(row["status"] for row in checks)
    summary_out = {
        "output_dir": str(output_dir),
        "timeout_rerun_dir": str(timeout_rerun_dir) if timeout_rerun_dir else "",
        "manifest_rows": len(rows),
        "categories": dict(sorted(categories.items())),
        "check_rows": len(checks),
        "pass": status_counts.get("PASS", 0),
        "fail": status_counts.get("FAIL", 0),
        "warn": status_counts.get("WARN", 0),
        "missing_files": len(missing_files),
        "bad_hashes": len(bad_hashes),
        "bad_sizes": len(bad_sizes),
    }
    return checks, summary_out


def write_outputs(output_dir: Path, checks: list[dict[str, str]], summary: dict[str, Any]) -> None:
    fieldnames = ["check_id", "category", "status", "expected", "observed", "evidence", "action"]
    write_csv(output_dir / "pipeline_artifact_manifest_verification.csv", checks, fieldnames)
    (output_dir / "pipeline_artifact_manifest_verification.json").write_text(
        json.dumps({"summary": summary, "rows": checks}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Pipeline Artifact Manifest Verification",
        "",
        "This verifies the generated pipeline artifact manifest. It is a post-manifest sidecar and is not hashed by the manifest itself.",
        "",
        "## Summary",
        "",
        f"- PASS: {summary['pass']}",
        f"- WARN: {summary['warn']}",
        f"- FAIL: {summary['fail']}",
        f"- manifest_rows: {summary['manifest_rows']}",
        "",
        "## Checks",
        "",
        "| check_id | status | category | observed | action |",
        "|---|---|---|---|---|",
    ]
    for row in checks:
        observed = row["observed"].replace("|", "\\|")
        action = row["action"].replace("|", "\\|")
        lines.append(f"| `{row['check_id']}` | `{row['status']}` | `{row['category']}` | {observed} | {action} |")
    lines.append("")
    (output_dir / "pipeline_artifact_manifest_verification.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated full pipeline output directory.")
    parser.add_argument("--timeout-rerun", type=Path, default=None, help="Optional timeout-rerun directory; defaults to pipeline_summary.json.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    timeout_rerun = args.timeout_rerun.resolve() if args.timeout_rerun else None
    checks, summary = verify(output_dir, timeout_rerun)
    write_outputs(output_dir, checks, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
