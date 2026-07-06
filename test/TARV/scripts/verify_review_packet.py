#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import posixpath
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[3]


REQUIRED_FILES = [
    "experiment_summary.json",
    "paper_review_results.xlsx",
    "workbook_formula_error_scan.ndjson",
    "workbook_preview_manifest.csv",
    "workbook_preview_manifest.json",
    "workbook_rebuild_summary.csv",
    "workbook_rebuild_summary.json",
    "workbook_rebuild_summary.md",
    "review_guide.csv",
    "review_guide.json",
    "review_guide.md",
    "human_review_queue.csv",
    "human_review_queue.json",
    "human_review_queue.md",
    "review_signoff_template.csv",
    "review_signoff_template.json",
    "review_signoff_template.md",
    "review_signoff_validation.csv",
    "review_signoff_validation.json",
    "review_signoff_validation.md",
    "goal_completion_audit.csv",
    "goal_completion_audit.json",
    "goal_completion_audit.md",
    "manual_review_checklist.csv",
    "manual_review_checklist.json",
    "manual_review_checklist.md",
    "requirements_traceability_audit.csv",
    "requirements_traceability_audit.md",
    "mitl_correctness_audit.csv",
    "semantic_oracle_derivations.csv",
    "manual_oracle_guide.csv",
    "manual_oracle_guide.json",
    "manual_oracle_guide.md",
    "xml_proof_obligations.csv",
    "xml_proof_obligations.json",
    "xml_proof_obligations.md",
    "xml_trace_coverage_obligations.csv",
    "xml_trace_coverage_obligations.json",
    "xml_trace_coverage_obligations.md",
    "xml_original_trace_gaps.csv",
    "xml_original_trace_gaps.json",
    "xml_original_trace_gaps.md",
    "gear_original_input_response_audit.csv",
    "gear_original_input_response_audit.json",
    "gear_original_input_response_audit.md",
    "non_gear_original_input_search_audit.csv",
    "non_gear_original_input_search_audit.json",
    "non_gear_original_input_search_audit.md",
    "semantic_prefix_oracle_review.csv",
    "cli_contract_audit.csv",
    "formula_input_policy_audit.csv",
    "mightyppl_syntax_coverage_audit.csv",
    "benchmark_manifest.csv",
    "monitaal_xml_inventory.csv",
    "monitaal_translation_review.csv",
    "monitaal_transition_details.csv",
    "xml_edge_guard_proofs.csv",
    "xml_proof_appendix.csv",
    "translation_candidate_results.csv",
    "candidate_prefix_observations.csv",
    "candidate_step_audit.csv",
    "monitaal_baseline_results.csv",
    "monitaal_embedded_benchmarks.csv",
    "paper_claim_consistency_audit.csv",
    "reproducibility_manifest.csv",
]

BENCHMARK_BLOCKER_FILES = [
    "benchmark_blocker_diagnostics.csv",
    "benchmark_blocker_diagnostics.json",
    "benchmark_blocker_diagnostics.md",
]

HARDCODED_BENCHMARK_FILES = [
    "monitaal_hardcoded_benchmarks.csv",
    "monitaal_hardcoded_benchmarks.json",
    "monitaal_hardcoded_benchmarks.md",
]

SIGNOFF_EVIDENCE_BUNDLE_FILES = [
    "review_signoff_evidence_bundle.csv",
    "review_signoff_evidence_bundle.json",
    "review_signoff_evidence_bundle.md",
]

SIGNOFF_ROUNDTRIP_AUDIT_FILES = [
    "signoff_import_roundtrip_audit.csv",
    "signoff_import_roundtrip_audit.json",
    "signoff_import_roundtrip_audit.md",
]

SIGNOFF_ROUNDTRIP_REQUIRED_CHECKS = {
    "ROUNDTRIP_CSV_DRY_RUN",
    "ROUNDTRIP_XLSX_BLANK_EXTRACTION",
    "ROUNDTRIP_CSV_APPLY",
    "ROUNDTRIP_COMPLETE_VALIDATION",
    "ROUNDTRIP_COMPLETE_WORKBOOK_REBUILD",
    "ROUNDTRIP_COMPLETE_PACKET_VERIFICATION",
    "ROUNDTRIP_STALE_GENERATED_FIELD_REJECTED",
}


REQUIRED_WORKBOOK_SHEETS = [
    "Review Guide",
    "Review Queue",
    "Review Signoff",
    "Goal Audit",
    "Manual Review",
    "Correctness Audit",
    "Benchmark Manifest",
    "Candidate Results",
    "Baseline Results",
    "Paper Claim Review",
    "Oracle Derivations",
    "Manual Oracle Guide",
    "XML Obligations",
    "XML Trace Coverage",
    "Original Trace Gaps",
    "Gear Original Audit",
    "Non-Gear Input Search",
    "Prefix Oracle",
    "Syntax Coverage",
    "Input Policy",
    "Requirements Audit",
    "Repro Manifest",
]

MITL_FORMULA_CATALOG_WORKBOOK_SPECS: list[tuple[str, str]] = [
    ("MITL Semantic Catalog", "mitl_formula_catalog_semantic_regression.csv"),
    ("MITL XML Candidates", "mitl_formula_catalog_monitaal_xml_candidates.csv"),
    ("MITL Runtime Catalog", "mitl_formula_catalog_runtime_runs.csv"),
]

WORKBOOK_SHEET_SOURCE_SPECS: list[tuple[str, str, str | None]] = [
    ("Summary", "experiment_summary.csv", None),
    ("Review Guide", "review_guide.csv", "review_guide_rows"),
    ("Review Queue", "human_review_queue.csv", "human_review_queue_rows"),
    ("Review Signoff", "review_signoff_template.csv", "review_signoff_template_rows"),
    ("Signoff Evidence", "review_signoff_evidence_bundle.csv", None),
    ("Signoff Validation", "review_signoff_validation.csv", None),
    ("Signoff Roundtrip", "signoff_import_roundtrip_audit.csv", None),
    ("Goal Audit", "goal_completion_audit.csv", "goal_completion_rows"),
    ("Manual Review", "manual_review_checklist.csv", "manual_review_rows"),
    ("Correctness Audit", "mitl_correctness_audit.csv", "mitl_correctness_audit_rows"),
    ("Prefix Oracle", "semantic_prefix_oracle_review.csv", "semantic_prefix_oracle_rows"),
    ("Oracle Derivations", "semantic_oracle_derivations.csv", "semantic_oracle_derivation_rows"),
    ("Manual Oracle Guide", "manual_oracle_guide.csv", "manual_oracle_guide_rows"),
    ("Semantic Results", "semantic_regression_results.csv", "semantic_cases"),
    ("Semantic Cases", "semantic_cases.csv", "semantic_cases"),
    ("Semantic Exclusions", "semantic_exclusions.csv", "semantic_exclusion_rows"),
    ("Syntax Coverage", "mightyppl_syntax_coverage_audit.csv", "syntax_coverage_rows"),
    ("Input Policy", "formula_input_policy_audit.csv", "formula_input_policy_rows"),
    ("CLI Contract", "cli_contract_audit.csv", "cli_contract_rows"),
    ("MITL Semantic Catalog", "mitl_formula_catalog_semantic_regression.csv", None),
    ("MITL XML Candidates", "mitl_formula_catalog_monitaal_xml_candidates.csv", None),
    ("MITL Runtime Catalog", "mitl_formula_catalog_runtime_runs.csv", None),
    ("XML Inventory", "monitaal_xml_inventory.csv", "xml_templates"),
    ("Translation Review", "monitaal_translation_review.csv", "xml_pairs"),
    ("Benchmark Manifest", "benchmark_manifest.csv", "benchmark_manifest_rows"),
    ("XML Edge Proofs", "xml_edge_guard_proofs.csv", "xml_edge_guard_proof_rows"),
    ("XML Proof Appendix", "xml_proof_appendix.csv", "xml_proof_appendix_rows"),
    ("XML Obligations", "xml_proof_obligations.csv", "xml_proof_obligation_rows"),
    ("XML Trace Coverage", "xml_trace_coverage_obligations.csv", "xml_trace_coverage_rows"),
    ("Original Trace Gaps", "xml_original_trace_gaps.csv", "xml_original_trace_gap_rows"),
    ("Gear Original Audit", "gear_original_input_response_audit.csv", "gear_original_input_response_audit_rows"),
    ("Non-Gear Input Search", "non_gear_original_input_search_audit.csv", "non_gear_original_input_search_audit_rows"),
    ("Paper Claim Review", "paper_claim_review.csv", "paper_claim_review_rows"),
    ("Claim Audit", "paper_claim_consistency_audit.csv", "paper_claim_audit_rows"),
    ("Requirements Audit", "requirements_traceability_audit.csv", "requirements_audit_rows"),
    ("Repro Manifest", "reproducibility_manifest.csv", "reproducibility_manifest_rows"),
    ("Transition Details", "monitaal_transition_details.csv", "xml_transition_detail_rows"),
    ("Candidate Results", "translation_candidate_results.csv", "translation_candidate_runs"),
    ("Candidate Step Audit", "candidate_step_audit.csv", "candidate_step_audit_rows"),
    ("Baseline Results", "monitaal_baseline_results.csv", "baseline_total"),
    ("Timeout Rerun Summary", "timeout_rerun_summary.csv", None),
    ("Timeout Rerun", "timeout_rerun_details.csv", None),
    ("Embedded Benchmarks", "monitaal_embedded_benchmarks.csv", "embedded_benchmark_records"),
    ("Hardcoded Benchmarks", "monitaal_hardcoded_benchmarks.csv", None),
    ("Benchmark Blockers", "benchmark_blocker_diagnostics.csv", None),
]


HASHED_RESULT_FILES = [
    "review_guide.csv",
    "review_guide.json",
    "review_guide.md",
    "human_review_queue.csv",
    "human_review_queue.json",
    "human_review_queue.md",
    "review_signoff_template.csv",
    "review_signoff_template.json",
    "review_signoff_template.md",
    "mitl_correctness_audit.csv",
    "semantic_oracle_derivations.csv",
    "manual_oracle_guide.csv",
    "manual_oracle_guide.json",
    "manual_oracle_guide.md",
    "xml_proof_obligations.csv",
    "xml_proof_obligations.json",
    "xml_proof_obligations.md",
    "xml_trace_coverage_obligations.csv",
    "xml_trace_coverage_obligations.json",
    "xml_trace_coverage_obligations.md",
    "xml_original_trace_gaps.csv",
    "xml_original_trace_gaps.json",
    "xml_original_trace_gaps.md",
    "gear_original_input_response_audit.csv",
    "gear_original_input_response_audit.json",
    "gear_original_input_response_audit.md",
    "non_gear_original_input_search_audit.csv",
    "non_gear_original_input_search_audit.json",
    "non_gear_original_input_search_audit.md",
    "monitaal_embedded_benchmarks.csv",
    "requirements_traceability_audit.csv",
]

HASHED_SOURCE_FILES = [
    "test/TARV/scripts/analyze_benchmark_blockers.py",
    "test/TARV/scripts/audit_signoff_import_roundtrip.py",
    "test/TARV/scripts/build_signoff_evidence_bundle.py",
    "test/TARV/scripts/build_paper_review_workbook.mjs",
    "test/TARV/scripts/compare_pipeline_results.py",
    "test/TARV/scripts/import_review_signoff.py",
    "test/TARV/scripts/rebuild_review_workbook.py",
    "test/TARV/scripts/rerun_baseline_timeouts.py",
    "test/TARV/scripts/run_full_review_pipeline.py",
    "test/TARV/scripts/run_monitaal_hardcoded_benchmarks.py",
    "test/TARV/scripts/run_paper_experiments.py",
    "test/TARV/scripts/validate_review_signoff.py",
    "test/TARV/scripts/verify_pipeline_artifact_manifest.py",
    "test/TARV/scripts/verify_review_packet.py",
    "tool/MoniTAal/benchmark/main.cpp",
    "tool/MoniTAal/src/monitaal-bin/main.cpp",
]


PUBLIC_RV_VERDICTS = {"POSITIVE", "NEGATIVE", "INCONCLUSIVE"}
BUILD_ONLY_VERDICT_SENTINEL = "NOT_RUN_BUILD_ONLY"
PUBLIC_RV_OR_BUILD_ONLY = PUBLIC_RV_VERDICTS | {BUILD_ONLY_VERDICT_SENTINEL}

PUBLIC_VERDICT_COLUMN_SPECS = [
    ("semantic_cases.csv", "expected_final", PUBLIC_RV_VERDICTS, False),
    ("semantic_cases.csv", "expected_prefix", PUBLIC_RV_VERDICTS, True),
    ("semantic_regression_results.csv", "actual_final", PUBLIC_RV_OR_BUILD_ONLY, False),
    ("semantic_regression_results.csv", "expected_final", PUBLIC_RV_VERDICTS, False),
    ("semantic_regression_results.csv", "expected_prefix", PUBLIC_RV_VERDICTS, True),
    ("semantic_regression_results.csv", "oracle_verdict", PUBLIC_RV_VERDICTS, False),
    ("semantic_oracle_derivations.csv", "expected_final", PUBLIC_RV_VERDICTS, False),
    ("semantic_oracle_derivations.csv", "actual_final", PUBLIC_RV_OR_BUILD_ONLY, False),
    ("semantic_oracle_derivations.csv", "expected_prefix", PUBLIC_RV_VERDICTS, True),
    ("semantic_prefix_oracle_review.csv", "expected_final", PUBLIC_RV_VERDICTS, False),
    ("semantic_prefix_oracle_review.csv", "actual_final", PUBLIC_RV_OR_BUILD_ONLY, False),
    ("semantic_prefix_oracle_review.csv", "expected_prefix_verdict", PUBLIC_RV_VERDICTS, False),
    ("semantic_prefix_oracle_review.csv", "actual_prefix_verdict", PUBLIC_RV_VERDICTS, False),
    ("mitl_correctness_audit.csv", "runtime_verdict", PUBLIC_RV_OR_BUILD_ONLY, False),
    ("mitl_correctness_audit.csv", "oracle_verdict", PUBLIC_RV_VERDICTS, False),
    ("mitl_correctness_audit.csv", "baseline_verdict", PUBLIC_RV_VERDICTS, False),
    ("cli_contract_audit.csv", "final_verdict", PUBLIC_RV_OR_BUILD_ONLY, False),
    ("translation_candidate_results.csv", "actual_final", PUBLIC_RV_VERDICTS, False),
    ("translation_candidate_results.csv", "baseline_verdict", PUBLIC_RV_VERDICTS, False),
    ("translation_candidate_results.csv", "oracle_verdict", PUBLIC_RV_VERDICTS, False),
    ("candidate_prefix_observations.csv", "baseline_verdict", PUBLIC_RV_VERDICTS, False),
    ("candidate_prefix_observations.csv", "actual_final", PUBLIC_RV_VERDICTS, False),
    ("candidate_prefix_observations.csv", "verdict", PUBLIC_RV_VERDICTS, False),
    ("candidate_step_audit.csv", "first_decisive_verdict", PUBLIC_RV_VERDICTS, False),
    ("candidate_step_audit.csv", "actual_final", PUBLIC_RV_VERDICTS, False),
    ("candidate_step_audit.csv", "baseline_verdict", PUBLIC_RV_VERDICTS, False),
    ("monitaal_baseline_results.csv", "verdict", PUBLIC_RV_VERDICTS, False),
    ("gear_original_input_response_audit.csv", "baseline_verdict", PUBLIC_RV_VERDICTS, False),
    ("timeout_rerun_details.csv", "verdict", PUBLIC_RV_VERDICTS, False),
    ("benchmark_manifest.csv", "matched_verdicts", PUBLIC_RV_VERDICTS, True),
    ("monitaal_hardcoded_benchmarks.csv", "verdicts", PUBLIC_RV_VERDICTS, True),
]


SOURCE_ROW_RULES = [
    ("GOAL_", [("goal_completion_audit.csv", "goal_id")]),
    ("MANUAL_", [("manual_review_checklist.csv", "review_id")]),
    ("XML_PROOF_", [("xml_proof_appendix.csv", "manifest_id"), ("xml_edge_guard_proofs.csv", "manifest_id")]),
    ("XML_ORIGINAL_TRACE_GAP_", [("xml_original_trace_gaps.csv", "gap_id")]),
    ("PAPER_CLAIM_", [("paper_claim_review.csv", "manifest_id"), ("paper_claim_consistency_audit.csv", "manifest_id")]),
    ("BENCHMARK_", [("benchmark_manifest.csv", "manifest_id")]),
]

STALE_TIMEOUT_FACT_PHRASES_WHEN_NO_TIMEOUTS = [
    "still times out",
    "timed out in baseline",
    "baseline timed out",
    "NOT_VERIFIED_BASELINE_TIMEOUT",
    "original-input timeout caveat",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def csv_table_shape(path: Path) -> tuple[int, int]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return len(rows), max((len(row) for row in rows), default=0)


def count_rows(rows: list[dict[str, str]], **criteria: str) -> int:
    return sum(1 for row in rows if all(row.get(key, "") == value for key, value in criteria.items()))


def status_row(
    check_id: str,
    category: str,
    status: str,
    expected: str,
    observed: str,
    evidence_artifact: str,
    reviewer_action: str,
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "category": category,
        "status": status,
        "expected": expected,
        "observed": observed,
        "evidence_artifact": evidence_artifact,
        "reviewer_action": reviewer_action,
    }


def add_bool_check(
    rows: list[dict[str, str]],
    check_id: str,
    category: str,
    ok: bool,
    expected: str,
    observed: str,
    evidence_artifact: str,
    reviewer_action: str,
) -> None:
    rows.append(status_row(
        check_id,
        category,
        "PASS" if ok else "FAIL",
        expected,
        observed,
        evidence_artifact,
        reviewer_action,
    ))


def summary_int(summary: dict[str, Any], key: str) -> int:
    value = summary.get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def split_verdict_tokens(value: str) -> list[str]:
    return [token.strip() for token in re.split(r"[;,|]", value) if token.strip()]


def split_semicolon_tokens(value: str) -> list[str]:
    return [token.strip() for token in value.split(";") if token.strip()]


def collect_stale_timeout_fact_claims(output_dir: Path, baseline_timeout_count: int) -> list[str]:
    if baseline_timeout_count != 0:
        return []
    violations: list[str] = []
    for path in sorted(output_dir.iterdir()):
        if path.suffix not in {".csv", ".json", ".md"}:
            continue
        if path.name.startswith("review_packet_verification"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower_text = text.lower()
        for phrase in STALE_TIMEOUT_FACT_PHRASES_WHEN_NO_TIMEOUTS:
            phrase_lower = phrase.lower()
            if phrase_lower not in lower_text:
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                if phrase_lower in line.lower():
                    violations.append(f"{path.name}:{line_number}:{phrase}")
                    break
    return violations


def collect_inconclusive_claim_boundary_violations(
    paper_claim_rows: list[dict[str, str]],
    signoff_rows: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    bad_claims: list[str] = []
    for row in paper_claim_rows:
        boundary = row.get("baseline_evidence_boundary", "")
        must_not_claim = row.get("must_not_claim", "")
        if row.get("claim_strength") != "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF":
            continue
        if "INCONCLUSIVE" not in boundary:
            continue
        if "INCONCLUSIVE" not in must_not_claim or "third-valued" not in must_not_claim.lower():
            bad_claims.append(row.get("manifest_id", "") or row.get("review_id", ""))

    bad_signoffs: list[str] = []
    for row in signoff_rows:
        must_not_claim = row.get("must_not_claim", "")
        if "INCONCLUSIVE" not in must_not_claim:
            continue
        if row.get("recommended_decision") != "APPROVE_WITH_CAVEAT" or "APPROVE_AS_CLAIMED" not in row.get("forbidden_decisions", ""):
            bad_signoffs.append(row.get("signoff_id", "") or row.get("queue_id", ""))
    return bad_claims, bad_signoffs


def collect_original_trace_gap_claim_violations(
    paper_claim_rows: list[dict[str, str]],
    signoff_rows: list[dict[str, str]],
    xml_gap_rows: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    gap_manifest_ids = {row.get("manifest_id", "") for row in xml_gap_rows if row.get("manifest_id")}
    bad_claims: list[str] = []
    for row in paper_claim_rows:
        manifest_id = row.get("manifest_id", "")
        if manifest_id not in gap_manifest_ids:
            continue
        must_not_claim = row.get("must_not_claim", "")
        if not row.get("original_trace_gap_boundary"):
            bad_claims.append(f"{manifest_id}:missing_boundary")
            continue
        if "original-input benchmark coverage" not in must_not_claim:
            bad_claims.append(f"{manifest_id}:missing_must_not_claim")

    bad_signoffs: list[str] = []
    for row in signoff_rows:
        if not row.get("queue_id", "").startswith("PAPER_CLAIM_"):
            continue
        source_id = row.get("source_id", "")
        if source_id not in gap_manifest_ids:
            continue
        if row.get("recommended_decision") != "APPROVE_WITH_CAVEAT" or "APPROVE_AS_CLAIMED" not in row.get("forbidden_decisions", ""):
            bad_signoffs.append(row.get("signoff_id", "") or row.get("queue_id", ""))
    return bad_claims, bad_signoffs


def collect_gear_original_input_response_audit_violations(
    output_dir: Path,
    sheet_names: set[str],
    summary: dict[str, Any],
    baseline_rows: list[dict[str, str]],
    xml_gap_rows: list[dict[str, str]],
) -> list[str]:
    violations: list[str] = []
    csv_path = output_dir / "gear_original_input_response_audit.csv"
    json_path = output_dir / "gear_original_input_response_audit.json"
    md_path = output_dir / "gear_original_input_response_audit.md"
    if not csv_path.exists() or not json_path.exists() or not md_path.exists():
        return ["gear_audit_artifact_missing"]

    rows = read_csv(csv_path)
    data = read_json(json_path)
    audit_summary = data.get("summary", {}) if isinstance(data, dict) else {}
    md_text = md_path.read_text(encoding="utf-8", errors="replace")

    gear_gap_manifest_ids = {
        row.get("manifest_id", "")
        for row in xml_gap_rows
        if row.get("xml_file") == "gear-control-properties.xml"
        and row.get("gap_class") == "repository_input_inconclusive"
    }
    row_manifest_ids = {row.get("manifest_id", "") for row in rows}
    if len(rows) != 6:
        violations.append(f"row_count={len(rows)}")
    if summary_int(summary, "gear_original_input_response_audit_rows") != len(rows):
        violations.append(
            "summary_row_count="
            f"{summary_int(summary, 'gear_original_input_response_audit_rows')}!={len(rows)}"
        )
    if summary_int(audit_summary, "row_count") != len(rows):
        violations.append(f"json_row_count={summary_int(audit_summary, 'row_count')}!={len(rows)}")
    if gear_gap_manifest_ids != row_manifest_ids:
        violations.append(
            "manifest_set_mismatch:gaps="
            f"{len(gear_gap_manifest_ids)}:rows={len(row_manifest_ids)}"
        )
    if "Gear Original Audit" not in sheet_names:
        violations.append("workbook_sheet_missing")

    baseline_by_key = {
        (
            Path(row.get("xml_path", "")).name,
            row.get("positive_template", ""),
            row.get("negative_template", ""),
            Path(row.get("input_path", "")).name,
        ): row
        for row in baseline_rows
    }
    pending_templates: set[str] = set()
    no_pending_templates: set[str] = set()
    for row in rows:
        audit_id = row.get("audit_id", "")
        for token in [audit_id, row.get("manifest_id", "")]:
            if token and token not in md_text:
                violations.append(f"md_token_missing:{token}")
        if Path(row.get("input_path", "")).name != "gear-control-input.txt":
            violations.append(f"{audit_id}:input_name={Path(row.get('input_path', '')).name}")
        if not Path(row.get("input_path", "")).exists():
            violations.append(f"{audit_id}:input_missing")
        if row.get("input_origin") != "repository_input":
            violations.append(f"{audit_id}:input_origin={row.get('input_origin', '')}")
        if row.get("baseline_status") != "ran" or row.get("baseline_verdict") != "INCONCLUSIVE":
            violations.append(
                f"{audit_id}:baseline={row.get('baseline_status', '')}/{row.get('baseline_verdict', '')}"
            )
        baseline = baseline_by_key.get((
            row.get("xml_file", ""),
            row.get("positive_template", ""),
            row.get("negative_template", ""),
            Path(row.get("input_path", "")).name,
        ))
        if not baseline:
            violations.append(f"{audit_id}:baseline_row_missing")
        elif baseline.get("status") != row.get("baseline_status") or baseline.get("verdict") != row.get("baseline_verdict"):
            violations.append(f"{audit_id}:baseline_drift")
        if summary_int(row, "timed_event_rows") != 12126:
            violations.append(f"{audit_id}:timed_event_rows={row.get('timed_event_rows', '')}")
        if summary_int(row, "nonblank_event_count") <= 0:
            violations.append(f"{audit_id}:nonblank_event_count={row.get('nonblank_event_count', '')}")
        if summary_int(row, "trigger_count") <= 0:
            violations.append(f"{audit_id}:trigger_count={row.get('trigger_count', '')}")
        if summary_int(row, "response_count") <= 0:
            violations.append(f"{audit_id}:response_count={row.get('response_count', '')}")
        if summary_int(row, "late_response_count") != 0:
            violations.append(f"{audit_id}:late_response_count={row.get('late_response_count', '')}")
        if summary_int(row, "expired_without_response_count") != 0:
            violations.append(f"{audit_id}:expired_without_response_count={row.get('expired_without_response_count', '')}")
        if "INCONCLUSIVE" not in row.get("online_verdict_boundary", ""):
            violations.append(f"{audit_id}:missing_inconclusive_boundary")
        if "not Boolean satisfaction" not in row.get("online_verdict_boundary", ""):
            violations.append(f"{audit_id}:missing_boolean_boundary")
        if not row.get("evidence_summary", "").strip():
            violations.append(f"{audit_id}:missing_evidence_summary")

        if summary_int(row, "pending_trigger_count") > 0:
            pending_templates.add(row.get("positive_template", ""))
            if row.get("finite_trace_response_status") != "PENDING_TRIGGER_AT_TRACE_END":
                violations.append(f"{audit_id}:pending_status={row.get('finite_trace_response_status', '')}")
        else:
            no_pending_templates.add(row.get("positive_template", ""))
            if row.get("finite_trace_response_status") != "NO_LATE_RESPONSE_OBSERVED_BUT_ONLINE_FUTURE_OPEN":
                violations.append(f"{audit_id}:no_pending_status={row.get('finite_trace_response_status', '')}")

    if pending_templates != {"ReqSet", "test1"}:
        violations.append(f"pending_templates={';'.join(sorted(pending_templates))}")
    expected_no_pending = {"CloseClutch", "OpenClutch", "ReqNeu", "SpeedSet"}
    if no_pending_templates != expected_no_pending:
        violations.append(f"no_pending_templates={';'.join(sorted(no_pending_templates))}")
    if summary_int(summary, "gear_original_input_response_audit_late_response_rows") != 0:
        violations.append(
            "summary_late_rows="
            f"{summary_int(summary, 'gear_original_input_response_audit_late_response_rows')}"
        )
    if summary_int(summary, "gear_original_input_response_audit_pending_rows") != 2:
        violations.append(
            "summary_pending_rows="
            f"{summary_int(summary, 'gear_original_input_response_audit_pending_rows')}"
        )
    if summary_int(summary, "gear_original_input_response_audit_expired_rows") != 0:
        violations.append(
            "summary_expired_rows="
            f"{summary_int(summary, 'gear_original_input_response_audit_expired_rows')}"
        )
    if summary_int(audit_summary, "late_response_rows") != 0:
        violations.append(f"json_late_rows={summary_int(audit_summary, 'late_response_rows')}")
    if summary_int(audit_summary, "pending_trigger_rows") != 2:
        violations.append(f"json_pending_rows={summary_int(audit_summary, 'pending_trigger_rows')}")
    if summary_int(audit_summary, "expired_without_response_rows") != 0:
        violations.append(
            f"json_expired_rows={summary_int(audit_summary, 'expired_without_response_rows')}"
        )
    return violations


def collect_non_gear_original_input_search_audit_violations(
    output_dir: Path,
    sheet_names: set[str],
    summary: dict[str, Any],
    xml_gap_rows: list[dict[str, str]],
    baseline_rows: list[dict[str, str]],
) -> list[str]:
    violations: list[str] = []
    csv_path = output_dir / "non_gear_original_input_search_audit.csv"
    json_path = output_dir / "non_gear_original_input_search_audit.json"
    md_path = output_dir / "non_gear_original_input_search_audit.md"
    if not csv_path.exists() or not json_path.exists() or not md_path.exists():
        return ["non_gear_search_artifact_missing"]

    rows = read_csv(csv_path)
    data = read_json(json_path)
    audit_summary = data.get("summary", {}) if isinstance(data, dict) else {}
    md_text = md_path.read_text(encoding="utf-8", errors="replace")

    expected_gap_manifest_ids = {
        row.get("manifest_id", "")
        for row in xml_gap_rows
        if row.get("gap_class") == "no_repository_input_found"
        and row.get("xml_file") != "gear-control-properties.xml"
    }
    row_manifest_ids = {row.get("manifest_id", "") for row in rows}
    if len(rows) != 2:
        violations.append(f"row_count={len(rows)}")
    if row_manifest_ids != expected_gap_manifest_ids:
        violations.append(
            f"manifest_set_mismatch:gaps={len(expected_gap_manifest_ids)}:rows={len(row_manifest_ids)}"
        )
    if summary_int(summary, "non_gear_original_input_search_audit_rows") != len(rows):
        violations.append(
            "summary_row_count="
            f"{summary_int(summary, 'non_gear_original_input_search_audit_rows')}!={len(rows)}"
        )
    if summary_int(audit_summary, "row_count") != len(rows):
        violations.append(f"json_row_count={summary_int(audit_summary, 'row_count')}!={len(rows)}")
    if "Non-Gear Input Search" not in sheet_names:
        violations.append("workbook_sheet_missing")

    baseline_by_pair: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in baseline_rows:
        key = (
            Path(row.get("xml_path", "")).name,
            row.get("positive_template", ""),
            row.get("negative_template", ""),
        )
        baseline_by_pair.setdefault(key, []).append(row)

    for row in rows:
        audit_id = row.get("audit_id", "")
        for token in [audit_id, row.get("manifest_id", "")]:
            if token and token not in md_text:
                violations.append(f"md_token_missing:{token}")
        if row.get("search_status") != "NO_ORIGINAL_TIMED_WORD_FOUND":
            violations.append(f"{audit_id}:search_status={row.get('search_status', '')}")
        if row.get("gap_class") != "no_repository_input_found":
            violations.append(f"{audit_id}:gap_class={row.get('gap_class', '')}")
        if row.get("xml_exists") != "true":
            violations.append(f"{audit_id}:xml_exists={row.get('xml_exists', '')}")
        if row.get("monitaal_models_cmake_lists_reference") != "true":
            violations.append(f"{audit_id}:cmake_reference={row.get('monitaal_models_cmake_lists_reference', '')}")
        if summary_int(row, "sibling_input_txt_count") <= 0:
            violations.append(f"{audit_id}:sibling_input_txt_count={row.get('sibling_input_txt_count', '')}")
        if summary_int(row, "prefix_matched_sibling_input_count") != 0:
            violations.append(
                f"{audit_id}:prefix_matched_sibling_input_count={row.get('prefix_matched_sibling_input_count', '')}"
            )
        if summary_int(row, "repository_same_stem_file_count") != 1:
            violations.append(f"{audit_id}:repository_same_stem_file_count={row.get('repository_same_stem_file_count', '')}")
        if summary_int(row, "repository_non_xml_same_stem_file_count") != 0:
            violations.append(
                f"{audit_id}:repository_non_xml_same_stem_file_count={row.get('repository_non_xml_same_stem_file_count', '')}"
            )
        if summary_int(row, "original_like_baseline_count") != 0:
            violations.append(f"{audit_id}:original_like_baseline_count={row.get('original_like_baseline_count', '')}")
        if summary_int(row, "generated_review_input_count") != 3:
            violations.append(f"{audit_id}:generated_review_input_count={row.get('generated_review_input_count', '')}")
        if summary_int(row, "generated_empty_input_count") != 0:
            violations.append(f"{audit_id}:generated_empty_input_count={row.get('generated_empty_input_count', '')}")
        boundary_lower = row.get("boundary", "").lower()
        if (
            "generated review traces" not in boundary_lower
            or "not" not in boundary_lower
            or "original benchmark traces" not in boundary_lower
        ):
            violations.append(f"{audit_id}:missing_boundary")
        if not row.get("evidence_summary", "").strip():
            violations.append(f"{audit_id}:missing_evidence_summary")

        pair_rows = baseline_by_pair.get((
            row.get("xml_file", ""),
            row.get("positive_template", ""),
            row.get("negative_template", ""),
        ), [])
        original_like = [
            baseline
            for baseline in pair_rows
            if baseline.get("input_origin") in {
                "repository_input",
                "embedded_benchmark_input",
                "external_or_case_input",
            }
        ]
        generated_review = [
            baseline
            for baseline in pair_rows
            if baseline.get("input_origin") == "generated_review_input"
        ]
        if original_like:
            violations.append(f"{audit_id}:baseline_original_like_rows={len(original_like)}")
        if len(generated_review) != 3:
            violations.append(f"{audit_id}:baseline_generated_review_rows={len(generated_review)}")

    if summary_int(summary, "non_gear_original_input_search_no_original_rows") != 2:
        violations.append(
            "summary_no_original_rows="
            f"{summary_int(summary, 'non_gear_original_input_search_no_original_rows')}"
        )
    if summary_int(summary, "non_gear_original_input_search_possible_original_rows") != 0:
        violations.append(
            "summary_possible_original_rows="
            f"{summary_int(summary, 'non_gear_original_input_search_possible_original_rows')}"
        )
    if summary_int(summary, "non_gear_original_input_search_original_like_baseline_rows") != 0:
        violations.append(
            "summary_original_like_baseline_rows="
            f"{summary_int(summary, 'non_gear_original_input_search_original_like_baseline_rows')}"
        )
    if summary_int(summary, "non_gear_original_input_search_generated_review_input_rows") != 6:
        violations.append(
            "summary_generated_review_input_rows="
            f"{summary_int(summary, 'non_gear_original_input_search_generated_review_input_rows')}"
        )
    if summary_int(audit_summary, "no_original_timed_word_found") != 2:
        violations.append(
            f"json_no_original_timed_word_found={summary_int(audit_summary, 'no_original_timed_word_found')}"
        )
    if summary_int(audit_summary, "review_required_possible_original_input") != 0:
        violations.append(
            "json_possible_original_input="
            f"{summary_int(audit_summary, 'review_required_possible_original_input')}"
        )
    if summary_int(audit_summary, "original_like_baseline_rows") != 0:
        violations.append(
            f"json_original_like_baseline_rows={summary_int(audit_summary, 'original_like_baseline_rows')}"
        )
    if summary_int(audit_summary, "generated_review_input_rows") != 6:
        violations.append(
            f"json_generated_review_input_rows={summary_int(audit_summary, 'generated_review_input_rows')}"
        )
    return violations


def collect_c_after10_embedded_provenance_violations(
    output_dir: Path,
    embedded_rows: list[dict[str, str]],
    baseline_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    xml_trace_rows: list[dict[str, str]],
    xml_gap_rows: list[dict[str, str]],
) -> list[str]:
    violations: list[str] = []
    case_id = "c_after_10_monitor_test_intersection_test2"
    candidate_id = "c_after_10_positive_negative_c_after_10_monitor_test_intersection_test2"
    input_name = f"{case_id}.input"
    expected_input_text = "@0 a\n@5 c\n@15 c\n@20 b\n"
    input_path = output_dir / "embedded_monitaal" / input_name

    if not input_path.exists():
        violations.append("input_missing")
    elif input_path.read_text(encoding="utf-8") != expected_input_text:
        violations.append("input_content_mismatch")

    source_path = REPO_ROOT / "tool" / "MoniTAal" / "test" / "Monitor_test.cpp"
    if not source_path.exists():
        violations.append("source_missing")
    else:
        source_text = source_path.read_text(encoding="utf-8", errors="replace")
        source_markers = [
            "BOOST_AUTO_TEST_CASE(intersection_test2)",
            'Parser::parse_file("models/c_after_10.xml", "positive")',
            'Parser::parse_file("models/c_after_10.xml", "negative")',
            'monitor_c.input({0, "a"});',
            'monitor_c.input({5, "c"});',
            'monitor_c.input({15, "c"});',
            'monitor_c.input({20, "b"});',
            "BOOST_CHECK(monitor_c.status() == POSITIVE);",
        ]
        for marker in source_markers:
            if marker not in source_text:
                violations.append(f"source_marker_missing:{marker}")

    matching_embedded = [row for row in embedded_rows if row.get("case_id") == case_id]
    if len(matching_embedded) != 1:
        violations.append(f"embedded_row_count={len(matching_embedded)}")
    else:
        row = matching_embedded[0]
        if Path(row.get("header", "")).name != "Monitor_test.cpp":
            violations.append("embedded_header_not_monitor_test")
        if "intersection_test2" not in row.get("status", "") or "POSITIVE" not in row.get("status", ""):
            violations.append("embedded_status_lacks_test_or_verdict")

    matching_baseline = [row for row in baseline_rows if Path(row.get("input_path", "")).name == input_name]
    if len(matching_baseline) != 1:
        violations.append(f"baseline_row_count={len(matching_baseline)}")
    else:
        row = matching_baseline[0]
        expected = {
            "positive_template": "positive",
            "negative_template": "negative",
            "status": "ran",
            "verdict": "POSITIVE",
            "input_origin": "embedded_benchmark_input",
        }
        for key, value in expected.items():
            if row.get(key) != value:
                violations.append(f"baseline_{key}={row.get(key, '')}")
        if Path(row.get("xml_path", "")).name != "c_after_10.xml":
            violations.append("baseline_xml_not_c_after_10")

    matching_candidate = [row for row in candidate_rows if row.get("candidate_id") == candidate_id]
    if len(matching_candidate) != 1:
        violations.append(f"candidate_row_count={len(matching_candidate)}")
    else:
        row = matching_candidate[0]
        expected = {
            "xml_file": "c_after_10.xml",
            "positive_template": "positive",
            "negative_template": "negative",
            "actual_final": "POSITIVE",
            "baseline_verdict": "POSITIVE",
            "baseline_comparison_status": "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT",
            "mapped_events": "4",
            "processed_steps": "4",
        }
        for key, value in expected.items():
            if row.get(key) != value:
                violations.append(f"candidate_{key}={row.get(key, '')}")
        if Path(row.get("input_path", "")).name != input_name:
            violations.append("candidate_input_name_mismatch")

    coverage_rows = [
        row for row in xml_trace_rows
        if row.get("manifest_id") == "c_after_10_positive_negative"
        and row.get("coverage_name") == "original_decisive_trace_boundary"
    ]
    if len(coverage_rows) != 1:
        violations.append(f"coverage_row_count={len(coverage_rows)}")
    else:
        row = coverage_rows[0]
        if row.get("coverage_status") != "PASS":
            violations.append(f"coverage_status={row.get('coverage_status', '')}")
        for token in [
            "original_like=1",
            "decisive_original=1",
            candidate_id,
            "POSITIVE|embedded_benchmark_input|embedded_monitor_test_positive",
        ]:
            if token not in " ".join(row.values()):
                violations.append(f"coverage_token_missing:{token}")

    if any(row.get("manifest_id") == "c_after_10_positive_negative" for row in xml_gap_rows):
        violations.append("c_after_10_still_listed_as_gap")
    return violations


def collect_baseline_match_oracle_boundary_violations(candidate_rows: list[dict[str, str]]) -> list[str]:
    violations: list[str] = []
    for row in candidate_rows:
        if row.get("oracle_type") != "monitaal_xml_baseline_same_input":
            continue
        candidate_id = row.get("candidate_id", "<missing-candidate-id>")
        evidence_lower = row.get("correctness_evidence", "").lower()
        comparison_status = row.get("baseline_comparison_status", "")
        if comparison_status in {
            "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT",
            "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT",
        }:
            if "trace-level evidence" not in evidence_lower:
                violations.append(f"{candidate_id}:missing_trace_level_caveat")
            if "not an automatic xml-to-mitl equivalence proof" not in evidence_lower:
                violations.append(f"{candidate_id}:missing_non_equivalence_caveat")
        if "hand oracle" in evidence_lower or "hand-oracle" in evidence_lower:
            violations.append(f"{candidate_id}:calls_baseline_hand_oracle")
        if "manual oracle" in evidence_lower or "manual-oracle" in evidence_lower:
            violations.append(f"{candidate_id}:calls_baseline_manual_oracle")
    return violations


def evidence_token_resolves(output_dir: Path, workbook_sheets: set[str], token: str) -> bool:
    if not token:
        return False
    if token in workbook_sheets:
        return True
    if token.startswith("glob:"):
        pattern = token[len("glob:"):].strip()
        return bool(pattern) and any(output_dir.glob(pattern))

    candidates = [output_dir / token, REPO_ROOT / token]
    if token.startswith("/"):
        candidates.append(Path(token))
    return any(path.exists() for path in candidates)


def collect_evidence_reference_violations(
    output_dir: Path,
    workbook_sheets: set[str],
    rows: list[dict[str, str]],
    row_id_key: str,
) -> tuple[list[str], list[str]]:
    missing_context_rows: list[str] = []
    unresolved_tokens: list[str] = []

    for row in rows:
        row_id = row.get(row_id_key, "") or "<missing-row-id>"
        if (
            not row.get("evidence_artifacts", "").strip()
            or not row.get("review_focus", "").strip()
            or not row.get("must_not_claim", "").strip()
            or not row.get("next_action", "").strip()
            or ("evidence_summary" in row and not row.get("evidence_summary", "").strip())
        ):
            missing_context_rows.append(row_id)
        tokens = split_semicolon_tokens(row.get("evidence_artifacts", ""))
        if not tokens:
            unresolved_tokens.append(f"{row_id}:<blank>")
        for token in tokens:
            if not evidence_token_resolves(output_dir, workbook_sheets, token):
                unresolved_tokens.append(f"{row_id}:{token}")

    return missing_context_rows, unresolved_tokens


def source_row_specs(queue_id: str) -> list[tuple[str, str]]:
    for prefix, specs in SOURCE_ROW_RULES:
        if queue_id.startswith(prefix):
            return specs
    return []


def build_source_row_index(output_dir: Path) -> dict[tuple[str, str], set[str]]:
    index: dict[tuple[str, str], set[str]] = {}
    for _, specs in SOURCE_ROW_RULES:
        for file_name, column in specs:
            key = (file_name, column)
            if key in index:
                continue
            path = output_dir / file_name
            if not path.exists():
                index[key] = set()
                continue
            index[key] = {row.get(column, "") for row in read_csv(path) if row.get(column, "")}
    return index


def collect_source_reference_violations(
    output_dir: Path,
    workbook_sheets: set[str],
    rows: list[dict[str, str]],
    row_id_key: str,
) -> tuple[list[str], list[str]]:
    source_index = build_source_row_index(output_dir)
    unresolved_sheets: list[str] = []
    unresolved_rows: list[str] = []

    for row in rows:
        row_id = row.get(row_id_key, "") or "<missing-row-id>"
        source_sheets = split_semicolon_tokens(row.get("source_sheet", ""))
        if not source_sheets:
            unresolved_sheets.append(f"{row_id}:<blank>")
        for sheet_name in source_sheets:
            if sheet_name not in workbook_sheets:
                unresolved_sheets.append(f"{row_id}:{sheet_name}")

        specs = source_row_specs(row.get("queue_id", row_id))
        source_id = row.get("source_id", "")
        if not specs:
            unresolved_rows.append(f"{row_id}:no_rule:{row.get('queue_id', row_id)}")
        elif not source_id:
            unresolved_rows.append(f"{row_id}:<blank>:{'|'.join(f'{file_name}:{column}' for file_name, column in specs)}")
        elif not any(source_id in source_index.get(spec, set()) for spec in specs):
            expected = "|".join(f"{file_name}:{column}" for file_name, column in specs)
            unresolved_rows.append(f"{row_id}:{source_id}:{expected}")

    return unresolved_sheets, unresolved_rows


def collect_review_entrypoint_reference_violations(
    output_dir: Path,
    workbook_sheets: set[str],
    summary: dict[str, Any],
    review_guide_rows: list[dict[str, str]],
    goal_rows: list[dict[str, str]],
    manual_rows: list[dict[str, str]],
    requirements_rows: list[dict[str, str]],
    allow_roundtrip_self_reference: bool = False,
) -> list[str]:
    violations: list[str] = []

    table_specs = [
        (
            "review_guide.csv",
            "guide_id",
            review_guide_rows,
            "review_guide_rows",
            ["instruction", "decision_rule", "must_not_claim", "next_action"],
            "",
        ),
        (
            "goal_completion_audit.csv",
            "goal_id",
            goal_rows,
            "goal_completion_rows",
            ["requested_goal", "evidence_summary", "must_not_claim", "next_action"],
            "review_gate",
        ),
        (
            "manual_review_checklist.csv",
            "review_id",
            manual_rows,
            "manual_review_rows",
            ["review_question", "evidence_summary", "must_not_claim", "suggested_action"],
            "workbook_sheet",
        ),
        (
            "requirements_traceability_audit.csv",
            "requirement_id",
            requirements_rows,
            "requirements_audit_rows",
            ["requirement", "evidence_summary", "next_action"],
            "",
        ),
    ]
    for file_name, id_column, rows, summary_key, context_columns, sheet_column in table_specs:
        expected_rows = summary_int(summary, summary_key)
        if len(rows) != expected_rows:
            violations.append(f"{file_name}:rows:{len(rows)}!={summary_key}:{expected_rows}")
        duplicates = duplicate_ids(rows, id_column)
        if duplicates:
            violations.append(f"{file_name}:duplicate_{id_column}=" + ",".join(duplicates[:8]))
        for row in rows:
            row_id = row.get(id_column, "") or "<missing-row-id>"
            for column in context_columns:
                if not row.get(column, "").strip():
                    violations.append(f"{file_name}:{row_id}:blank_{column}")
            evidence_tokens = split_semicolon_tokens(row.get("evidence_artifacts", ""))
            if not evidence_tokens:
                violations.append(f"{file_name}:{row_id}:blank_evidence_artifacts")
            for token in evidence_tokens:
                if (
                    allow_roundtrip_self_reference
                    and token in {"signoff_import_roundtrip_audit.csv", "signoff_import_roundtrip_audit.json", "signoff_import_roundtrip_audit.md"}
                ):
                    continue
                if not evidence_token_resolves(output_dir, workbook_sheets, token):
                    violations.append(f"{file_name}:{row_id}:unresolved_evidence:{token}")
            if sheet_column:
                sheet_tokens = split_semicolon_tokens(row.get(sheet_column, ""))
                if not sheet_tokens:
                    violations.append(f"{file_name}:{row_id}:blank_{sheet_column}")
                for sheet_name in sheet_tokens:
                    if sheet_name not in workbook_sheets:
                        violations.append(f"{file_name}:{row_id}:unresolved_sheet:{sheet_name}")

    review_priorities = Counter(row.get("priority", "") for row in review_guide_rows)
    if review_priorities.get("P0", 0) != summary_int(summary, "review_guide_p0"):
        violations.append(f"review_guide:P0:{review_priorities.get('P0', 0)}!={summary_int(summary, 'review_guide_p0')}")
    if review_priorities.get("P1", 0) != summary_int(summary, "review_guide_p1"):
        violations.append(f"review_guide:P1:{review_priorities.get('P1', 0)}!={summary_int(summary, 'review_guide_p1')}")
    if set(review_priorities) - {"P0", "P1", "P2", "P3"}:
        violations.append("review_guide:invalid_priorities=" + ",".join(sorted(set(review_priorities) - {"P0", "P1", "P2", "P3"})[:8]))

    goal_statuses = Counter(row.get("status", "") for row in goal_rows)
    for status, summary_key in [
        ("PASS", "goal_completion_pass"),
        ("PASS_WITH_CAVEAT", "goal_completion_pass_with_caveat"),
        ("REVIEW_REQUIRED", "goal_completion_review_required"),
        ("V1_DEFERRED", "goal_completion_v1_deferred"),
        ("FAIL", "goal_completion_fail"),
    ]:
        if goal_statuses.get(status, 0) != summary_int(summary, summary_key):
            violations.append(f"goal_status:{status}:{goal_statuses.get(status, 0)}!={summary_key}:{summary_int(summary, summary_key)}")

    manual_statuses = Counter(row.get("automatic_status", "") for row in manual_rows)
    for status, summary_key in [
        ("PASS", "manual_review_pass"),
        ("PASS_WITH_CAVEAT", "manual_review_pass_with_caveat"),
        ("REVIEW_REQUIRED", "manual_review_review_required"),
        ("V1_DEFERRED", "manual_review_v1_deferred"),
        ("FAIL", "manual_review_fail"),
    ]:
        if manual_statuses.get(status, 0) != summary_int(summary, summary_key):
            violations.append(f"manual_status:{status}:{manual_statuses.get(status, 0)}!={summary_key}:{summary_int(summary, summary_key)}")
    manual_required = sum(1 for row in manual_rows if row.get("human_decision_required", "") == "true")
    invalid_manual_required = [
        row.get("review_id", "")
        for row in manual_rows
        if row.get("human_decision_required", "") not in {"true", "false"}
    ]
    if manual_required != summary_int(summary, "manual_review_human_required"):
        violations.append(f"manual_human_required:{manual_required}!={summary_int(summary, 'manual_review_human_required')}")
    if invalid_manual_required:
        violations.append("manual_invalid_human_decision_required=" + ",".join(invalid_manual_required[:8]))

    requirement_statuses = Counter(row.get("status", "") for row in requirements_rows)
    for status, summary_key in [
        ("PASS", "requirements_audit_pass"),
        ("PASS_WITH_CAVEAT", "requirements_audit_pass_with_caveat"),
        ("V1_DEFERRED", "requirements_audit_v1_deferred"),
        ("FAIL", "requirements_audit_fail"),
    ]:
        if requirement_statuses.get(status, 0) != summary_int(summary, summary_key):
            violations.append(f"requirements_status:{status}:{requirement_statuses.get(status, 0)}!={summary_key}:{summary_int(summary, summary_key)}")

    sidecar_expectations = [
        ("review_guide.csv", "review_guide.json", "guide_id", review_guide_rows),
        ("goal_completion_audit.csv", "goal_completion_audit.json", "goal_id", goal_rows),
        ("manual_review_checklist.csv", "manual_review_checklist.json", "review_id", manual_rows),
    ]
    for csv_name, json_name, id_column, rows in sidecar_expectations:
        json_path = output_dir / json_name
        try:
            json_rows = read_json(json_path) if json_path.exists() else []
        except Exception as exc:
            violations.append(f"{json_name}:parse_error:{exc}")
            continue
        if not isinstance(json_rows, list):
            violations.append(f"{json_name}:not_list")
            continue
        csv_ids = {row.get(id_column, "") for row in rows if row.get(id_column, "")}
        json_ids = {str(row.get(id_column, "")) for row in json_rows if isinstance(row, dict) and row.get(id_column, "")}
        if csv_ids != json_ids:
            violations.append(
                f"{json_name}:id_set_mismatch:"
                f"missing={','.join(sorted(csv_ids - json_ids)[:8])};"
                f"extra={','.join(sorted(json_ids - csv_ids)[:8])}"
            )
        if len(json_rows) != len(rows):
            violations.append(f"{json_name}:rows:{len(json_rows)}!={csv_name}:{len(rows)}")

    for md_name, rows, id_column in [
        ("review_guide.md", review_guide_rows, "guide_id"),
        ("goal_completion_audit.md", goal_rows, "goal_id"),
        ("manual_review_checklist.md", manual_rows, "review_id"),
        ("requirements_traceability_audit.md", requirements_rows, "requirement_id"),
    ]:
        md_path = output_dir / md_name
        text = md_path.read_text(encoding="utf-8", errors="replace") if md_path.exists() else ""
        if not text.strip():
            violations.append(f"{md_name}:blank_or_missing")
            continue
        missing_ids = [row.get(id_column, "") for row in rows if row.get(id_column, "") and row.get(id_column, "") not in text]
        if missing_ids:
            violations.append(f"{md_name}:missing_ids=" + ",".join(missing_ids[:8]))

    return violations


def collect_public_verdict_violations(output_dir: Path) -> tuple[list[str], Counter[str], int, int, int]:
    violations: list[str] = []
    observed: Counter[str] = Counter()
    checked_sources = 0
    checked_columns = 0
    checked_values = 0

    def relative(path: Path) -> str:
        try:
            return str(path.relative_to(output_dir))
        except ValueError:
            return str(path)

    def note_violation(source: str, value: str) -> None:
        violations.append(f"{source}:{value}"[:240])

    def check_value(source: str, raw_value: str, allowed: set[str], multi_value: bool = False) -> None:
        nonlocal checked_values
        raw_value = (raw_value or "").strip()
        if not raw_value:
            return
        values = split_verdict_tokens(raw_value) if multi_value else [raw_value]
        for value in values:
            checked_values += 1
            observed[value] += 1
            if value not in allowed:
                note_violation(source, value)

    def check_csv_column(path: Path, column: str, allowed: set[str], multi_value: bool = False) -> None:
        nonlocal checked_sources, checked_columns
        if not path.exists():
            return
        checked_sources += 1
        checked_columns += 1
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if column not in fieldnames:
                note_violation(f"{relative(path)}:{column}", "<missing_column>")
                return
            for line_number, row in enumerate(reader, start=2):
                check_value(
                    f"{relative(path)}:{column}:line{line_number}",
                    row.get(column, ""),
                    allowed,
                    multi_value,
                )

    def check_json_column(path: Path, column: str, allowed: set[str], multi_value: bool = False) -> None:
        nonlocal checked_sources, checked_columns
        if not path.exists():
            return
        try:
            data = read_json(path)
        except Exception as exc:
            note_violation(f"{relative(path)}:{column}", f"<json_error:{exc}>")
            return
        seen = False

        def visit(value: Any, location: str) -> None:
            nonlocal seen
            if isinstance(value, dict):
                if column in value:
                    seen = True
                    raw = value.get(column)
                    if isinstance(raw, list):
                        for index, item in enumerate(raw):
                            check_value(f"{location}:{column}[{index}]", str(item), allowed, multi_value)
                    else:
                        check_value(f"{location}:{column}", str(raw or ""), allowed, multi_value)
                for key, child in value.items():
                    visit(child, f"{location}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{location}[{index}]")

        visit(data, relative(path))
        if seen:
            checked_sources += 1
            checked_columns += 1

    def check_summary_csv(path: Path) -> None:
        nonlocal checked_sources, checked_columns
        if not path.exists():
            return
        checked_sources += 1
        checked_columns += 1
        saw_final_verdict = False
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            if not {"metric", "value"}.issubset(fieldnames):
                note_violation(f"{relative(path)}:final_verdict", "<missing_metric_value_columns>")
                return
            for line_number, row in enumerate(reader, start=2):
                if row.get("metric") == "final_verdict":
                    saw_final_verdict = True
                    check_value(
                        f"{relative(path)}:final_verdict:line{line_number}",
                        row.get("value", ""),
                        PUBLIC_RV_OR_BUILD_ONLY,
                    )
        if not saw_final_verdict:
            note_violation(f"{relative(path)}:final_verdict", "<missing_metric>")

    def check_metadata_json(path: Path) -> None:
        nonlocal checked_sources, checked_columns
        if not path.exists():
            return
        checked_sources += 1
        checked_columns += 1
        try:
            data = read_json(path)
        except Exception as exc:
            note_violation(f"{relative(path)}:final_verdict", f"<json_error:{exc}>")
            return
        if not isinstance(data, dict) or "final_verdict" not in data:
            note_violation(f"{relative(path)}:final_verdict", "<missing_key>")
            return
        check_value(
            f"{relative(path)}:final_verdict",
            str(data.get("final_verdict", "")),
            PUBLIC_RV_OR_BUILD_ONLY,
        )

    for file_name, column, allowed, multi_value in PUBLIC_VERDICT_COLUMN_SPECS:
        check_csv_column(output_dir / file_name, column, allowed, multi_value)
        check_json_column(output_dir / Path(file_name).with_suffix(".json"), column, allowed, multi_value)
    for path in sorted(output_dir.glob("**/steps.csv")):
        check_csv_column(path, "verdict", PUBLIC_RV_VERDICTS)
    for path in sorted(output_dir.glob("**/summary.csv")):
        check_summary_csv(path)
    for path in sorted(output_dir.glob("**/metadata.json")):
        check_metadata_json(path)

    return violations, observed, checked_sources, checked_columns, checked_values


def resolve_workbook_path(output_dir: Path, summary: dict[str, Any]) -> Path:
    local_workbook = output_dir / "paper_review_results.xlsx"
    if local_workbook.exists():
        return local_workbook
    workbook_path = str(summary.get("workbook_path") or "")
    if workbook_path:
        candidate = Path(workbook_path)
        if candidate.is_absolute():
            return candidate
        repo_candidate = REPO_ROOT / candidate
        if repo_candidate.exists():
            return repo_candidate
    return output_dir / "paper_review_results.xlsx"


def workbook_sheet_names(workbook: Path) -> tuple[list[str], int, int, str | None]:
    try:
        with zipfile.ZipFile(workbook) as archive:
            bad = archive.testzip()
            names = archive.namelist()
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8", errors="replace")
            root = ET.fromstring(workbook_xml)
            sheets = [
                element.attrib.get("name", "")
                for element in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
                if element.attrib.get("name")
            ]
            worksheet_count = sum(1 for name in names if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
            table_count = sum(1 for name in names if name.startswith("xl/tables/table") and name.endswith(".xml"))
            return sheets, worksheet_count, table_count, bad
    except Exception as exc:
        return [], 0, 0, str(exc)


def resolve_zip_relationship_target(base_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base_path), target))


def relationship_rels_path(part_path: str) -> str:
    return posixpath.join(
        posixpath.dirname(part_path),
        "_rels",
        posixpath.basename(part_path) + ".rels",
    )


def column_index(column: str) -> int:
    value = 0
    for char in column.upper():
        if not ("A" <= char <= "Z"):
            raise ValueError(f"invalid column {column!r}")
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


CELL_REF_RE = re.compile(r"^\$?([A-Za-z]+)\$?([0-9]+)$")


def parse_excel_range_shape(ref: str) -> tuple[int, int]:
    range_ref = ref.split("!", 1)[-1].replace("$", "")
    if ":" in range_ref:
        start_ref, end_ref = range_ref.split(":", 1)
    else:
        start_ref = end_ref = range_ref
    start_match = CELL_REF_RE.match(start_ref)
    end_match = CELL_REF_RE.match(end_ref)
    if not start_match or not end_match:
        raise ValueError(f"unsupported range ref {ref!r}")
    start_col, start_row = start_match.group(1), int(start_match.group(2))
    end_col, end_row = end_match.group(1), int(end_match.group(2))
    row_count = end_row - start_row + 1
    col_count = column_index(end_col) - column_index(start_col) + 1
    if row_count <= 0 or col_count <= 0:
        raise ValueError(f"non-positive range shape {ref!r}")
    return row_count, col_count


def workbook_table_shapes(workbook: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    shapes: dict[str, dict[str, Any]] = {}
    violations: list[str] = []
    try:
        with zipfile.ZipFile(workbook) as archive:
            workbook_part = "xl/workbook.xml"
            workbook_xml = ET.fromstring(archive.read(workbook_part))
            workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            workbook_targets = {
                rel.attrib.get("Id", ""): resolve_zip_relationship_target(workbook_part, rel.attrib.get("Target", ""))
                for rel in workbook_rels.findall(".//pkgrel:Relationship", ns)
            }
            for sheet in workbook_xml.findall(".//main:sheet", ns):
                sheet_name = sheet.attrib.get("name", "")
                rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "")
                worksheet_path = workbook_targets.get(rel_id, "")
                if not sheet_name:
                    violations.append("blank_sheet_name")
                    continue
                if not worksheet_path:
                    violations.append(f"{sheet_name}:missing_workbook_relationship={rel_id}")
                    continue
                if worksheet_path not in archive.namelist():
                    violations.append(f"{sheet_name}:missing_worksheet_part={worksheet_path}")
                    continue
                worksheet_xml = ET.fromstring(archive.read(worksheet_path))
                table_parts = worksheet_xml.findall(".//main:tablePart", ns)
                if len(table_parts) != 1:
                    violations.append(f"{sheet_name}:tablePart_count={len(table_parts)}")
                    continue
                table_rel_id = table_parts[0].attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "")
                worksheet_rels_path = relationship_rels_path(worksheet_path)
                if worksheet_rels_path not in archive.namelist():
                    violations.append(f"{sheet_name}:missing_worksheet_rels={worksheet_rels_path}")
                    continue
                worksheet_rels = ET.fromstring(archive.read(worksheet_rels_path))
                table_targets = {
                    rel.attrib.get("Id", ""): resolve_zip_relationship_target(worksheet_path, rel.attrib.get("Target", ""))
                    for rel in worksheet_rels.findall(".//pkgrel:Relationship", ns)
                }
                table_path = table_targets.get(table_rel_id, "")
                if not table_path:
                    violations.append(f"{sheet_name}:missing_table_relationship={table_rel_id}")
                    continue
                if table_path not in archive.namelist():
                    violations.append(f"{sheet_name}:missing_table_part={table_path}")
                    continue
                table_xml = ET.fromstring(archive.read(table_path))
                table_ref = table_xml.attrib.get("ref", "")
                table_name = table_xml.attrib.get("displayName", "") or table_xml.attrib.get("name", "")
                try:
                    row_count, col_count = parse_excel_range_shape(table_ref)
                except ValueError as exc:
                    violations.append(f"{sheet_name}:bad_table_ref={table_ref}:{exc}")
                    continue
                shapes[sheet_name] = {
                    "worksheet_path": worksheet_path,
                    "table_path": table_path,
                    "table_name": table_name,
                    "table_ref": table_ref,
                    "row_count": row_count,
                    "col_count": col_count,
                }
    except Exception as exc:
        return {}, [f"xlsx_parse_error:{exc}"]
    return shapes, violations


def int_cell(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def bool_cell(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def is_safe_relative_artifact_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def resolve_packet_artifact_path(output_dir: Path, value: str) -> Path:
    if not value:
        return Path()
    raw_path = Path(value)
    candidates: list[Path] = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(output_dir / raw_path)
    for marker in ("translation_candidate_runs", "translation_candidate_cases", "generated_monitaal_inputs", "embedded_monitaal"):
        if marker in raw_path.parts:
            suffix = Path(*raw_path.parts[raw_path.parts.index(marker):])
            candidates.append(output_dir / suffix)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1] if candidates else raw_path


def normalize_preview_manifest_row(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(row.get("sheetName", "")),
        str(row.get("fileName", "")),
        str(row.get("rowCount", "")),
        str(row.get("colCount", "")),
        str(row.get("preview_path", "")),
        str(row.get("preview_status", "")),
        str(row.get("preview_reason", "")),
    )


def collect_workbook_preview_manifest_violations(
    output_dir: Path,
    sheet_names: list[str],
    worksheet_count: int,
    required_workbook_sheets: list[str],
) -> list[str]:
    csv_path = output_dir / "workbook_preview_manifest.csv"
    json_path = output_dir / "workbook_preview_manifest.json"
    violations: list[str] = []

    try:
        csv_rows = read_csv(csv_path) if csv_path.exists() else []
    except Exception as exc:
        violations.append(f"csv_parse_error:{exc}")
        csv_rows = []

    try:
        json_data = read_json(json_path) if json_path.exists() else []
    except Exception as exc:
        violations.append(f"json_parse_error:{exc}")
        json_data = []

    json_rows = json_data if isinstance(json_data, list) else []
    if json_path.exists() and not isinstance(json_data, list):
        violations.append("json_not_list")

    if len(csv_rows) != len(json_rows):
        violations.append(f"csv_json_row_count:{len(csv_rows)}!={len(json_rows)}")
    else:
        csv_normalized = sorted(normalize_preview_manifest_row(row) for row in csv_rows)
        json_normalized = sorted(normalize_preview_manifest_row(row) for row in json_rows)
        if csv_normalized != json_normalized:
            violations.append("csv_json_content_mismatch")

    csv_sheet_names = [row.get("sheetName", "") for row in csv_rows]
    csv_sheet_set = {name for name in csv_sheet_names if name}
    workbook_sheet_set = set(sheet_names)
    duplicate_sheet_names = sorted(name for name, count in Counter(csv_sheet_names).items() if name and count > 1)
    if duplicate_sheet_names:
        violations.append("duplicate_sheets=" + ",".join(duplicate_sheet_names[:10]))
    if len(csv_rows) != worksheet_count:
        violations.append(f"manifest_rows_vs_workbook:{len(csv_rows)}!={worksheet_count}")
    missing_workbook_sheets = sorted(workbook_sheet_set - csv_sheet_set)
    extra_manifest_sheets = sorted(csv_sheet_set - workbook_sheet_set)
    if missing_workbook_sheets:
        violations.append("missing_workbook_sheets=" + ",".join(missing_workbook_sheets[:10]))
    if extra_manifest_sheets:
        violations.append("extra_manifest_sheets=" + ",".join(extra_manifest_sheets[:10]))
    missing_required = [sheet for sheet in required_workbook_sheets if sheet not in csv_sheet_set]
    if missing_required:
        violations.append("missing_required_sheets=" + ",".join(missing_required[:10]))

    for index, row in enumerate(csv_rows, start=2):
        sheet_name = row.get("sheetName", "") or f"row{index}"
        file_name = row.get("fileName", "")
        if not is_safe_relative_artifact_path(file_name):
            violations.append(f"{sheet_name}:unsafe_fileName={file_name}")
            continue
        source_path = output_dir / file_name
        if not source_path.exists():
            violations.append(f"{sheet_name}:missing_source={file_name}")
        else:
            actual_rows, actual_cols = csv_table_shape(source_path)
            manifest_rows = int_cell(row.get("rowCount"))
            manifest_cols = int_cell(row.get("colCount"))
            if manifest_rows != actual_rows:
                violations.append(f"{sheet_name}:rowCount:{manifest_rows}!={actual_rows}")
            if manifest_cols != actual_cols:
                violations.append(f"{sheet_name}:colCount:{manifest_cols}!={actual_cols}")

        preview_status = row.get("preview_status", "")
        preview_path = row.get("preview_path", "")
        preview_reason = row.get("preview_reason", "")
        if preview_status == "rendered":
            if not is_safe_relative_artifact_path(preview_path):
                violations.append(f"{sheet_name}:rendered_preview_path_invalid={preview_path}")
            elif not (output_dir / preview_path).exists():
                violations.append(f"{sheet_name}:rendered_preview_missing={preview_path}")
        elif preview_status == "skipped":
            if preview_path:
                violations.append(f"{sheet_name}:skipped_preview_path_should_be_empty={preview_path}")
            if not preview_reason:
                violations.append(f"{sheet_name}:skipped_preview_reason_missing")
        else:
            violations.append(f"{sheet_name}:preview_status={preview_status}")

    return violations


def expected_summary_count(summary: dict[str, Any], summary_key: str) -> int:
    if summary_key == "baseline_total":
        return (
            summary_int(summary, "baseline_runs")
            + summary_int(summary, "baseline_timeouts")
            + summary_int(summary, "baseline_skipped_no_input")
        )
    return summary_int(summary, summary_key)


def collect_workbook_source_coverage_violations(
    output_dir: Path,
    summary: dict[str, Any],
    required_workbook_sheets: list[str],
) -> list[str]:
    manifest_path = output_dir / "workbook_preview_manifest.csv"
    violations: list[str] = []
    try:
        manifest_rows = read_csv(manifest_path) if manifest_path.exists() else []
    except Exception as exc:
        return [f"manifest_parse_error:{exc}"]

    rows_by_sheet = {row.get("sheetName", ""): row for row in manifest_rows if row.get("sheetName", "")}
    required_or_present = set(required_workbook_sheets) | set(rows_by_sheet)

    for sheet_name, expected_file, summary_key in WORKBOOK_SHEET_SOURCE_SPECS:
        source_exists = (output_dir / expected_file).exists()
        row = rows_by_sheet.get(sheet_name)
        if row is None:
            if sheet_name in required_or_present or source_exists:
                violations.append(f"{sheet_name}:missing_manifest_row_for={expected_file}")
            continue

        observed_file = row.get("fileName", "")
        if observed_file != expected_file:
            violations.append(f"{sheet_name}:fileName:{observed_file}!={expected_file}")
            continue

        source_path = output_dir / observed_file
        if not source_path.exists():
            violations.append(f"{sheet_name}:missing_source={observed_file}")
            continue

        if summary_key:
            manifest_row_count = int_cell(row.get("rowCount"))
            if manifest_row_count is None:
                violations.append(f"{sheet_name}:rowCount_not_int={row.get('rowCount', '')}")
                continue
            expected_data_rows = expected_summary_count(summary, summary_key)
            observed_data_rows = max(0, manifest_row_count - 1)
            if observed_data_rows != expected_data_rows:
                violations.append(
                    f"{sheet_name}:data_rows:{observed_data_rows}!={summary_key}:{expected_data_rows}"
                )

    expected_by_sheet = {sheet_name: expected_file for sheet_name, expected_file, _ in WORKBOOK_SHEET_SOURCE_SPECS}
    for sheet_name, row in rows_by_sheet.items():
        expected_file = expected_by_sheet.get(sheet_name)
        if expected_file and row.get("fileName", "") != expected_file:
            violations.append(f"{sheet_name}:unexpected_source:{row.get('fileName', '')}!={expected_file}")

    return violations


def collect_workbook_xlsx_table_shape_violations(
    output_dir: Path,
    workbook: Path,
    required_workbook_sheets: list[str],
) -> list[str]:
    manifest_path = output_dir / "workbook_preview_manifest.csv"
    violations: list[str] = []
    try:
        manifest_rows = read_csv(manifest_path) if manifest_path.exists() else []
    except Exception as exc:
        return [f"manifest_parse_error:{exc}"]

    manifest_by_sheet = {row.get("sheetName", ""): row for row in manifest_rows if row.get("sheetName", "")}
    shapes, parse_violations = workbook_table_shapes(workbook)
    violations.extend(parse_violations)

    missing_required_shapes = [sheet for sheet in required_workbook_sheets if sheet not in shapes]
    if missing_required_shapes:
        violations.append("missing_required_table_shapes=" + ",".join(missing_required_shapes[:10]))

    manifest_sheet_set = set(manifest_by_sheet)
    shape_sheet_set = set(shapes)
    missing_shapes = sorted(manifest_sheet_set - shape_sheet_set)
    extra_shapes = sorted(shape_sheet_set - manifest_sheet_set)
    if missing_shapes:
        violations.append("missing_manifest_table_shapes=" + ",".join(missing_shapes[:10]))
    if extra_shapes:
        violations.append("extra_xlsx_table_shapes=" + ",".join(extra_shapes[:10]))

    for sheet_name, manifest_row in manifest_by_sheet.items():
        shape = shapes.get(sheet_name)
        if not shape:
            continue
        manifest_rows = int_cell(manifest_row.get("rowCount"))
        manifest_cols = int_cell(manifest_row.get("colCount"))
        if manifest_rows != shape.get("row_count"):
            violations.append(f"{sheet_name}:xlsx_rows:{shape.get('row_count')}!=manifest:{manifest_rows}")
        if manifest_cols != shape.get("col_count"):
            violations.append(f"{sheet_name}:xlsx_cols:{shape.get('col_count')}!=manifest:{manifest_cols}")

        file_name = manifest_row.get("fileName", "")
        if not is_safe_relative_artifact_path(file_name):
            violations.append(f"{sheet_name}:unsafe_fileName={file_name}")
            continue
        source_path = output_dir / file_name
        if source_path.exists():
            source_rows, source_cols = csv_table_shape(source_path)
            if shape.get("row_count") != source_rows:
                violations.append(f"{sheet_name}:xlsx_rows:{shape.get('row_count')}!=source:{source_rows}")
            if shape.get("col_count") != source_cols:
                violations.append(f"{sheet_name}:xlsx_cols:{shape.get('col_count')}!=source:{source_cols}")
        else:
            violations.append(f"{sheet_name}:missing_source={file_name}")

    return violations


def collect_mitl_formula_catalog_workbook_violations(
    output_dir: Path,
    workbook: Path,
    sheet_names: list[str],
) -> list[str]:
    any_catalog_artifact = any(
        (output_dir / csv_file).exists() or sheet_name in sheet_names
        for sheet_name, csv_file in MITL_FORMULA_CATALOG_WORKBOOK_SPECS
    )
    if not any_catalog_artifact:
        return []

    violations: list[str] = []
    sheet_set = set(sheet_names)
    shapes, shape_violations = workbook_table_shapes(workbook)
    violations.extend(f"xlsx:{violation}" for violation in shape_violations)

    for sheet_name, csv_file in MITL_FORMULA_CATALOG_WORKBOOK_SPECS:
        csv_path = output_dir / csv_file
        if not csv_path.exists():
            violations.append(f"{sheet_name}:missing_source_csv={csv_file}")
            continue
        if sheet_name not in sheet_set:
            violations.append(f"{sheet_name}:missing_workbook_sheet")
            continue
        shape = shapes.get(sheet_name)
        if shape is None:
            violations.append(f"{sheet_name}:missing_xlsx_table_shape")
            continue
        source_rows, source_cols = csv_table_shape(csv_path)
        if shape.get("row_count") != source_rows:
            violations.append(f"{sheet_name}:xlsx_rows:{shape.get('row_count')}!=source:{source_rows}")
        if shape.get("col_count") != source_cols:
            violations.append(f"{sheet_name}:xlsx_cols:{shape.get('col_count')}!=source:{source_cols}")

    return violations


def collect_workbook_rebuild_summary_violations(
    output_dir: Path,
    timeout_rerun_dir: Path | None,
    summary: dict[str, Any],
    workbook: Path,
    sheet_names: list[str],
) -> list[str]:
    json_path = output_dir / "workbook_rebuild_summary.json"
    csv_path = output_dir / "workbook_rebuild_summary.csv"
    violations: list[str] = []

    try:
        json_data = read_json(json_path) if json_path.exists() else {}
    except Exception as exc:
        violations.append(f"json_parse_error:{exc}")
        json_data = {}
    if not isinstance(json_data, dict):
        violations.append("json_not_object")
        json_data = {}

    try:
        csv_rows = read_csv(csv_path) if csv_path.exists() else []
    except Exception as exc:
        violations.append(f"csv_parse_error:{exc}")
        csv_rows = []
    if len(csv_rows) != 1:
        violations.append(f"csv_rows:{len(csv_rows)}!=1")
        csv_row: dict[str, str] = {}
    else:
        csv_row = csv_rows[0]

    for key, json_value in json_data.items():
        if key not in csv_row:
            violations.append(f"csv_missing_key={key}")
            continue
        csv_value = csv_row.get(key, "")
        if isinstance(json_value, bool):
            if bool_cell(csv_value) != json_value:
                violations.append(f"csv_json_bool_mismatch:{key}:{csv_value}!={json_value}")
        elif str(json_value) != csv_value:
            violations.append(f"csv_json_mismatch:{key}:{csv_value}!={json_value}")

    if json_data.get("status") != "ok":
        violations.append(f"status={json_data.get('status', '')}")
    if summary.get("workbook_status") != json_data.get("status"):
        violations.append(f"summary_status:{summary.get('workbook_status', '')}!={json_data.get('status', '')}")

    rebuild_workbook_path = str(json_data.get("workbook_path", ""))
    summary_workbook_path = str(summary.get("workbook_path", ""))
    if rebuild_workbook_path != summary_workbook_path:
        violations.append(f"workbook_path_summary_mismatch:{rebuild_workbook_path}!={summary_workbook_path}")
    if rebuild_workbook_path and not Path(rebuild_workbook_path).exists() and not workbook.exists():
        violations.append(f"workbook_path_missing={rebuild_workbook_path}")

    output_dir_value = str(json_data.get("output_dir", ""))
    summary_output_dir = str(summary.get("output_dir", ""))
    if output_dir_value != summary_output_dir:
        violations.append(f"output_dir_summary_mismatch:{output_dir_value}!={summary_output_dir}")

    optional_sheet_checks = [
        ("benchmark_blocker_diagnostics.csv", "benchmark_blocker_diagnostics_present", "benchmark_blocker_sheet_expected", "Benchmark Blockers"),
        ("monitaal_hardcoded_benchmarks.csv", "monitaal_hardcoded_benchmarks_present", "monitaal_hardcoded_benchmarks_sheet_expected", "Hardcoded Benchmarks"),
    ]
    for file_name, present_key, expected_key, sheet_name in optional_sheet_checks:
        source_exists = (output_dir / file_name).exists()
        present = bool_cell(json_data.get(present_key, False))
        expected = bool_cell(json_data.get(expected_key, False))
        sheet_present = sheet_name in sheet_names
        if present != source_exists:
            violations.append(f"{present_key}:{present}!={source_exists}")
        if expected != source_exists:
            violations.append(f"{expected_key}:{expected}!={source_exists}")
        if source_exists and not sheet_present:
            violations.append(f"missing_sheet={sheet_name}")

    if timeout_rerun_dir:
        rerun_dir_value = str(json_data.get("timeout_rerun_dir", ""))
        if not rerun_dir_value or Path(rerun_dir_value).resolve() != timeout_rerun_dir.resolve():
            violations.append(f"timeout_rerun_dir_mismatch:{rerun_dir_value}!={timeout_rerun_dir}")
        timeout_summary_present = bool_cell(json_data.get("timeout_rerun_summary_present", False))
        timeout_details_present = bool_cell(json_data.get("timeout_rerun_details_present", False))
        if not timeout_summary_present or not (output_dir / "timeout_rerun_summary.csv").exists() or "Timeout Rerun Summary" not in sheet_names:
            violations.append(
                "timeout_summary_evidence:"
                f"summary_flag={timeout_summary_present}; csv={(output_dir / 'timeout_rerun_summary.csv').exists()}; "
                f"sheet={'Timeout Rerun Summary' in sheet_names}"
            )
        if not timeout_details_present or not (output_dir / "timeout_rerun_details.csv").exists() or "Timeout Rerun" not in sheet_names:
            violations.append(
                "timeout_details_evidence:"
                f"details_flag={timeout_details_present}; csv={(output_dir / 'timeout_rerun_details.csv').exists()}; "
                f"sheet={'Timeout Rerun' in sheet_names}"
            )
    else:
        if str(json_data.get("timeout_rerun_dir", "")):
            violations.append(f"unexpected_timeout_rerun_dir={json_data.get('timeout_rerun_dir', '')}")

    return violations


def duplicate_ids(rows: list[dict[str, str]], key: str) -> list[str]:
    counts = Counter(row.get(key, "") for row in rows if row.get(key, ""))
    return sorted(identifier for identifier, count in counts.items() if count > 1)


def collect_candidate_prefix_observation_violations(
    output_dir: Path,
    summary: dict[str, Any],
    candidate_rows: list[dict[str, str]],
    prefix_rows: list[dict[str, str]],
    step_audit_rows: list[dict[str, str]],
) -> list[str]:
    violations: list[str] = []
    if len(prefix_rows) != summary_int(summary, "candidate_prefix_observation_rows"):
        violations.append(f"prefix_rows:{len(prefix_rows)}!={summary_int(summary, 'candidate_prefix_observation_rows')}")
    if len(step_audit_rows) != summary_int(summary, "candidate_step_audit_rows"):
        violations.append(f"step_audit_rows:{len(step_audit_rows)}!={summary_int(summary, 'candidate_step_audit_rows')}")
    if len(candidate_rows) != summary_int(summary, "translation_candidate_runs"):
        violations.append(f"candidate_rows:{len(candidate_rows)}!={summary_int(summary, 'translation_candidate_runs')}")

    candidate_duplicates = duplicate_ids(candidate_rows, "candidate_id")
    step_duplicates = duplicate_ids(step_audit_rows, "candidate_id")
    if candidate_duplicates:
        violations.append("duplicate_candidate_rows=" + ",".join(candidate_duplicates[:8]))
    if step_duplicates:
        violations.append("duplicate_step_audit_rows=" + ",".join(step_duplicates[:8]))

    candidate_by_id = {row.get("candidate_id", ""): row for row in candidate_rows if row.get("candidate_id", "")}
    step_by_id = {row.get("candidate_id", ""): row for row in step_audit_rows if row.get("candidate_id", "")}
    prefix_by_id: dict[str, list[dict[str, str]]] = {}
    for row in prefix_rows:
        prefix_by_id.setdefault(row.get("candidate_id", ""), []).append(row)

    candidate_ids = set(candidate_by_id)
    step_ids = set(step_by_id)
    prefix_ids = {candidate_id for candidate_id in prefix_by_id if candidate_id}
    if candidate_ids != step_ids:
        violations.append(
            "candidate_vs_step_ids:"
            f"missing_step={','.join(sorted(candidate_ids - step_ids)[:8])}; "
            f"extra_step={','.join(sorted(step_ids - candidate_ids)[:8])}"
        )
    if candidate_ids != prefix_ids:
        violations.append(
            "candidate_vs_prefix_ids:"
            f"missing_prefix={','.join(sorted(candidate_ids - prefix_ids)[:8])}; "
            f"extra_prefix={','.join(sorted(prefix_ids - candidate_ids)[:8])}"
        )

    carry_forward_count = sum(1 for row in prefix_rows if row.get("monitor_advanced", "") == "false")
    if carry_forward_count != summary_int(summary, "candidate_prefix_carry_forward_steps"):
        violations.append(
            f"carry_forward_rows:{carry_forward_count}!={summary_int(summary, 'candidate_prefix_carry_forward_steps')}"
        )
    complete_count = sum(1 for row in step_audit_rows if row.get("all_trace_steps_recorded", "") == "true")
    if complete_count != summary_int(summary, "candidate_step_all_trace_steps_recorded"):
        violations.append(
            f"complete_step_audit_rows:{complete_count}!={summary_int(summary, 'candidate_step_all_trace_steps_recorded')}"
        )
    incomplete_count = len(step_audit_rows) - complete_count
    if incomplete_count != summary_int(summary, "candidate_step_missing_or_incomplete"):
        violations.append(
            f"incomplete_step_audit_rows:{incomplete_count}!={summary_int(summary, 'candidate_step_missing_or_incomplete')}"
        )

    step_fields = [
        "step",
        "time",
        "canonical_label",
        "human_label",
        "verdict",
        "positive_states",
        "negative_states",
        "monitor_advanced",
    ]
    per_candidate_violations = 0
    for candidate_id in sorted(candidate_ids):
        candidate = candidate_by_id[candidate_id]
        step_audit = step_by_id.get(candidate_id, {})
        prefix_group = prefix_by_id.get(candidate_id, [])
        if not step_audit or not prefix_group:
            continue

        candidate_mapped = int_cell(candidate.get("mapped_events"))
        candidate_processed = int_cell(candidate.get("processed_steps"))
        audit_mapped = int_cell(step_audit.get("mapped_events"))
        audit_processed = int_cell(step_audit.get("processed_steps"))
        audit_observed = int_cell(step_audit.get("observed_steps"))
        prefix_count = len(prefix_group)
        if None in {candidate_mapped, candidate_processed, audit_mapped, audit_processed, audit_observed}:
            violations.append(f"{candidate_id}:non_integer_step_counts")
            per_candidate_violations += 1
            continue
        if not (candidate_mapped == candidate_processed == audit_mapped == audit_processed == audit_observed == prefix_count):
            violations.append(
                f"{candidate_id}:step_count_mismatch:"
                f"candidate_mapped={candidate_mapped}; candidate_processed={candidate_processed}; "
                f"audit_mapped={audit_mapped}; audit_processed={audit_processed}; audit_observed={audit_observed}; "
                f"prefix_rows={prefix_count}"
            )
            per_candidate_violations += 1
        if step_audit.get("all_trace_steps_recorded", "") != "true":
            violations.append(f"{candidate_id}:all_trace_steps_recorded={step_audit.get('all_trace_steps_recorded', '')}")
            per_candidate_violations += 1
        if prefix_group[-1].get("verdict", "") != candidate.get("actual_final", ""):
            violations.append(
                f"{candidate_id}:final_prefix_verdict:{prefix_group[-1].get('verdict', '')}!={candidate.get('actual_final', '')}"
            )
            per_candidate_violations += 1
        if any(row.get("actual_final", "") != candidate.get("actual_final", "") for row in prefix_group):
            violations.append(f"{candidate_id}:prefix_actual_final_drift")
            per_candidate_violations += 1
        if any(row.get("baseline_verdict", "") != candidate.get("baseline_verdict", "") for row in prefix_group):
            violations.append(f"{candidate_id}:prefix_baseline_verdict_drift")
            per_candidate_violations += 1

        prefix_carry = sum(1 for row in prefix_group if row.get("monitor_advanced", "") == "false")
        audit_carry = int_cell(step_audit.get("carry_forward_steps"))
        if audit_carry != prefix_carry:
            violations.append(f"{candidate_id}:carry_forward:{prefix_carry}!={audit_carry}")
            per_candidate_violations += 1

        steps_paths = {row.get("steps_path", "") for row in prefix_group if row.get("steps_path", "")}
        if len(steps_paths) != 1:
            violations.append(f"{candidate_id}:steps_path_count={len(steps_paths)}")
            per_candidate_violations += 1
            steps_path_value = step_audit.get("raw_step_artifact", "")
        else:
            steps_path_value = next(iter(steps_paths))
            if step_audit.get("raw_step_artifact", "") and step_audit.get("raw_step_artifact", "") != steps_path_value:
                violations.append(f"{candidate_id}:raw_step_artifact_drift")
                per_candidate_violations += 1
        steps_path = resolve_packet_artifact_path(output_dir, steps_path_value)
        if not steps_path.exists():
            violations.append(f"{candidate_id}:missing_steps_path={steps_path_value}")
            per_candidate_violations += 1
            if per_candidate_violations >= 20:
                break
            continue

        try:
            steps_rows = read_csv(steps_path)
        except Exception as exc:
            violations.append(f"{candidate_id}:steps_parse_error:{exc}")
            per_candidate_violations += 1
            if per_candidate_violations >= 20:
                break
            continue
        if len(steps_rows) != prefix_count:
            violations.append(f"{candidate_id}:steps_rows:{len(steps_rows)}!={prefix_count}")
            per_candidate_violations += 1
        else:
            for index, (prefix_row, step_row) in enumerate(zip(prefix_group, steps_rows), start=1):
                mismatched_fields = [field for field in step_fields if prefix_row.get(field, "") != step_row.get(field, "")]
                if mismatched_fields:
                    violations.append(f"{candidate_id}:step_row_{index}_mismatch={','.join(mismatched_fields[:8])}")
                    per_candidate_violations += 1
                    break

        if per_candidate_violations >= 20:
            violations.append("per_candidate_violation_limit_reached")
            break

    return violations


def transition_evidence_refs(value: str) -> tuple[list[tuple[str, str]], list[str]]:
    refs: list[tuple[str, str]] = []
    unparsable: list[str] = []
    for part in value.split("|"):
        fragment = part.strip()
        if not fragment:
            continue
        match = re.match(r"([^#|]+)#(\d+):", fragment)
        if not match:
            unparsable.append(fragment)
            continue
        refs.append((match.group(1), match.group(2)))
    return refs, unparsable


def collect_monitaal_transition_detail_violations(
    output_dir: Path,
    summary: dict[str, Any],
    manifest_rows: list[dict[str, str]],
    inventory_rows: list[dict[str, str]],
    translation_rows: list[dict[str, str]],
    transition_rows: list[dict[str, str]],
    edge_rows: list[dict[str, str]],
    appendix_rows: list[dict[str, str]],
) -> list[str]:
    violations: list[str] = []

    count_expectations = [
        ("benchmark_manifest.csv", len(manifest_rows), "benchmark_manifest_rows"),
        ("monitaal_xml_inventory.csv", len(inventory_rows), "xml_templates"),
        ("monitaal_translation_review.csv", len(translation_rows), "xml_pairs"),
        ("monitaal_transition_details.csv", len(transition_rows), "xml_transition_detail_rows"),
        ("xml_edge_guard_proofs.csv", len(edge_rows), "xml_edge_guard_proof_rows"),
        ("xml_proof_appendix.csv", len(appendix_rows), "xml_proof_appendix_rows"),
    ]
    for file_name, observed, summary_key in count_expectations:
        expected = summary_int(summary, summary_key)
        if observed != expected:
            violations.append(f"{file_name}:{observed}!={summary_key}:{expected}")

    for file_name, rows, key in [
        ("benchmark_manifest.csv", manifest_rows, "manifest_id"),
        ("xml_edge_guard_proofs.csv", edge_rows, "manifest_id"),
        ("xml_proof_appendix.csv", appendix_rows, "manifest_id"),
    ]:
        duplicates = duplicate_ids(rows, key)
        if duplicates:
            violations.append(f"{file_name}:duplicate_{key}=" + ",".join(duplicates[:8]))

    inventory_by_template: dict[tuple[str, str], dict[str, str]] = {}
    for row in inventory_rows:
        key = (row.get("xml_path", ""), row.get("template", ""))
        if key in inventory_by_template:
            violations.append(f"duplicate_inventory_template:{Path(key[0]).name}:{key[1]}")
        inventory_by_template[key] = row

    transition_by_template: dict[tuple[str, str], list[dict[str, str]]] = {}
    indexed_transition_keys: Counter[tuple[str, str, str]] = Counter()
    for row in transition_rows:
        template_key = (row.get("xml_path", ""), row.get("template", ""))
        transition_by_template.setdefault(template_key, []).append(row)
        if row.get("transition_index", ""):
            indexed_transition_keys[(row.get("xml_path", ""), row.get("template", ""), row.get("transition_index", ""))] += 1
    duplicate_transition_keys = [
        f"{Path(xml_path).name}:{template}#{index}"
        for (xml_path, template, index), count in indexed_transition_keys.items()
        if count > 1
    ]
    if duplicate_transition_keys:
        violations.append("duplicate_transition_refs=" + ",".join(duplicate_transition_keys[:8]))

    for key, inventory in inventory_by_template.items():
        details = transition_by_template.get(key, [])
        expected_transitions = int_cell(inventory.get("transitions"))
        if not details:
            violations.append(f"missing_transition_details:{Path(key[0]).name}:{key[1]}")
            continue
        if inventory.get("parse_status", "") != "ok":
            continue
        indexed_ok = [
            row for row in details
            if row.get("parse_status", "") == "ok" and row.get("transition_index", "")
        ]
        if expected_transitions is None:
            violations.append(f"inventory_transition_count_invalid:{Path(key[0]).name}:{key[1]}")
        elif len(indexed_ok) != expected_transitions:
            violations.append(
                f"inventory_transition_count:{Path(key[0]).name}:{key[1]}:{len(indexed_ok)}!={expected_transitions}"
            )

    manifest_by_id = {row.get("manifest_id", ""): row for row in manifest_rows if row.get("manifest_id", "")}
    manifest_by_pair = {
        (row.get("xml_path", ""), row.get("positive_template", ""), row.get("negative_template", "")): row
        for row in manifest_rows
    }
    translation_by_pair = {
        (row.get("xml_path", ""), row.get("positive_template", ""), row.get("negative_template", "")): row
        for row in translation_rows
    }
    translation_duplicates = duplicate_ids(
        [
            {
                "pair_key": "\0".join([
                    row.get("xml_path", ""),
                    row.get("positive_template", ""),
                    row.get("negative_template", ""),
                ])
            }
            for row in translation_rows
        ],
        "pair_key",
    )
    if translation_duplicates:
        violations.append(f"duplicate_translation_pairs={len(translation_duplicates)}")

    paired_field_names = [
        "pair_method",
        "ap_mapping",
        "candidate_mitl",
        "candidate_confidence",
        "mitl_equivalence_status",
        "review_status",
        "translation_reason",
    ]
    transition_ref_set = {
        (row.get("xml_path", ""), row.get("template", ""), row.get("transition_index", ""))
        for row in transition_rows
        if row.get("parse_status", "") == "ok" and row.get("transition_index", "")
    }

    for row in transition_rows:
        template_key = (row.get("xml_path", ""), row.get("template", ""))
        inventory = inventory_by_template.get(template_key)
        row_name = f"{Path(row.get('xml_path', '')).name}:{row.get('template', '')}#{row.get('transition_index', '')}"
        if not inventory:
            violations.append(f"transition_without_inventory:{row_name}")
            continue
        if row.get("parse_status", "") == "ok" and row.get("transition_index", ""):
            index = int_cell(row.get("transition_index"))
            expected_transitions = int_cell(inventory.get("transitions"))
            if index is None or expected_transitions is None or index < 1 or index > expected_transitions:
                violations.append(f"transition_index_out_of_range:{row_name}:max={inventory.get('transitions', '')}")
            if not row.get("source_id", "") or not row.get("target_id", ""):
                violations.append(f"transition_missing_endpoint:{row_name}")

        pair_role = row.get("pair_role", "")
        if pair_role not in {"positive", "negative", "unpaired"}:
            violations.append(f"invalid_pair_role:{row_name}:{pair_role}")
            continue
        if pair_role == "unpaired":
            if any(row.get(field, "") for field in ["positive_template", "negative_template", "pair_method", "candidate_mitl", "candidate_confidence"]):
                violations.append(f"unpaired_has_candidate_fields:{row_name}")
            if row.get("mitl_equivalence_status", "") != "not_claimed" or row.get("review_status", "") != "xml_baseline_only":
                violations.append(f"unpaired_status:{row_name}:{row.get('mitl_equivalence_status', '')}/{row.get('review_status', '')}")
            continue

        pair_key = (row.get("xml_path", ""), row.get("positive_template", ""), row.get("negative_template", ""))
        review = translation_by_pair.get(pair_key)
        if not review:
            violations.append(f"paired_transition_without_review:{row_name}")
            continue
        expected_template = row.get("positive_template", "") if pair_role == "positive" else row.get("negative_template", "")
        if row.get("template", "") != expected_template:
            violations.append(f"pair_role_template_mismatch:{row_name}:{pair_role}->{expected_template}")
        for field in paired_field_names:
            if row.get(field, "") != review.get(field, ""):
                violations.append(f"transition_review_field_drift:{row_name}:{field}")
                break

    for row in translation_rows:
        pair_key = (row.get("xml_path", ""), row.get("positive_template", ""), row.get("negative_template", ""))
        if pair_key not in manifest_by_pair:
            violations.append(f"translation_pair_missing_manifest:{Path(row.get('xml_path', '')).name}:{row.get('positive_template', '')}/{row.get('negative_template', '')}")
        positive_count = sum(
            1 for detail in transition_rows
            if detail.get("xml_path", "") == row.get("xml_path", "")
            and detail.get("template", "") == row.get("positive_template", "")
            and detail.get("positive_template", "") == row.get("positive_template", "")
            and detail.get("negative_template", "") == row.get("negative_template", "")
            and detail.get("pair_role", "") == "positive"
            and detail.get("transition_index", "")
        )
        negative_count = sum(
            1 for detail in transition_rows
            if detail.get("xml_path", "") == row.get("xml_path", "")
            and detail.get("template", "") == row.get("negative_template", "")
            and detail.get("positive_template", "") == row.get("positive_template", "")
            and detail.get("negative_template", "") == row.get("negative_template", "")
            and detail.get("pair_role", "") == "negative"
            and detail.get("transition_index", "")
        )
        expected_positive = int_cell(row.get("positive_edges"))
        expected_negative = int_cell(row.get("negative_edges"))
        if positive_count != expected_positive or negative_count != expected_negative:
            violations.append(
                f"translation_edge_count:{Path(row.get('xml_path', '')).name}:"
                f"{positive_count}/{negative_count}!={row.get('positive_edges', '')}/{row.get('negative_edges', '')}"
            )

    edge_ids = {row.get("manifest_id", "") for row in edge_rows if row.get("manifest_id", "")}
    appendix_ids = {row.get("manifest_id", "") for row in appendix_rows if row.get("manifest_id", "")}
    manifest_ids = {row.get("manifest_id", "") for row in manifest_rows if row.get("manifest_id", "")}
    if edge_ids != manifest_ids:
        violations.append(
            "edge_manifest_id_set:"
            f"missing={','.join(sorted(manifest_ids - edge_ids)[:8])};"
            f"extra={','.join(sorted(edge_ids - manifest_ids)[:8])}"
        )
    if appendix_ids != edge_ids:
        violations.append(
            "appendix_manifest_id_set:"
            f"missing={','.join(sorted(edge_ids - appendix_ids)[:8])};"
            f"extra={','.join(sorted(appendix_ids - edge_ids)[:8])}"
        )

    edge_status_counts = Counter(row.get("proof_status", "") for row in edge_rows)
    for status, summary_key in [
        ("EDGE_GUARD_PROOF_READY", "xml_edge_guard_proof_ready"),
        ("EDGE_GUARD_REVIEW_REQUIRED", "xml_edge_guard_review_required"),
        ("EDGE_GUARD_EVIDENCE_INCOMPLETE", "xml_edge_guard_incomplete"),
    ]:
        expected = summary_int(summary, summary_key)
        if edge_status_counts.get(status, 0) != expected:
            violations.append(f"edge_status_count:{status}:{edge_status_counts.get(status, 0)}!={summary_key}:{expected}")
    not_ready = sum(1 for row in edge_rows if row.get("proof_status", "").startswith("NOT_"))
    if not_ready != summary_int(summary, "xml_edge_guard_not_ready"):
        violations.append(f"edge_status_count:NOT_*:{not_ready}!={summary_int(summary, 'xml_edge_guard_not_ready')}")

    appendix_by_manifest = {row.get("manifest_id", ""): row for row in appendix_rows if row.get("manifest_id", "")}
    edge_manifest_fields = [
        "xml_path",
        "xml_file",
        "source_kind",
        "positive_template",
        "negative_template",
        "candidate_mitl",
        "promotion_status",
    ]
    edge_evidence_fields = ["positive_edge_evidence", "negative_edge_evidence", "reset_edge_evidence"]
    for edge in edge_rows:
        manifest_id = edge.get("manifest_id", "")
        manifest = manifest_by_id.get(manifest_id)
        if not manifest:
            violations.append(f"edge_without_manifest:{manifest_id}")
            continue
        for field in edge_manifest_fields:
            if edge.get(field, "") != manifest.get(field, ""):
                violations.append(f"edge_manifest_field_drift:{manifest_id}:{field}")
                break
        if edge.get("proof_id", "") != f"proof_{manifest_id}":
            violations.append(f"edge_proof_id:{manifest_id}:{edge.get('proof_id', '')}")

        for field in edge_evidence_fields:
            refs, unparsable = transition_evidence_refs(edge.get(field, ""))
            for fragment in unparsable:
                violations.append(f"edge_evidence_unparsable:{manifest_id}:{field}:{fragment[:80]}")
            for template, index in refs:
                if (edge.get("xml_path", ""), template, index) not in transition_ref_set:
                    violations.append(f"edge_evidence_missing_transition:{manifest_id}:{field}:{template}#{index}")

        proof_ready = edge.get("proof_status", "") == "EDGE_GUARD_PROOF_READY"
        if proof_ready:
            for field in ["positive_edge_evidence", "negative_edge_evidence", "acceptance_evidence", "trace_evidence"]:
                if not edge.get(field, "").strip():
                    violations.append(f"proof_ready_missing_{field}:{manifest_id}")

        for trace_token in split_semicolon_tokens(edge.get("trace_evidence", "")):
            if not resolve_packet_artifact_path(output_dir, trace_token).exists():
                violations.append(f"edge_trace_evidence_missing:{manifest_id}:{trace_token}")

        appendix = appendix_by_manifest.get(manifest_id)
        if not appendix:
            continue
        for field in ["xml_file", "positive_template", "negative_template", "candidate_mitl", "proof_status", "proof_class"]:
            if appendix.get(field, "") != edge.get(field, ""):
                violations.append(f"appendix_edge_field_drift:{manifest_id}:{field}")
                break
        if proof_ready:
            if appendix.get("appendix_status", "") != "PROOF_DRAFT_READY" or not appendix.get("edge_guard_evidence", "").strip():
                violations.append(f"appendix_ready_status:{manifest_id}:{appendix.get('appendix_status', '')}")
        else:
            expected_exclusion_status = {
                "NOT_PROOF_READY_APPROXIMATE": "EXCLUDED_APPROXIMATE",
                "NOT_APPLICABLE_NO_CANDIDATE": "EXCLUDED_NO_MITL_CANDIDATE",
            }.get(edge.get("proof_status", ""))
            if not appendix.get("appendix_status", "").startswith("EXCLUDED_") or not appendix.get("exclusion_reason", "").strip():
                violations.append(f"appendix_exclusion_status:{manifest_id}:{appendix.get('appendix_status', '')}")
            if expected_exclusion_status and appendix.get("appendix_status", "") != expected_exclusion_status:
                violations.append(f"appendix_exclusion_mapping:{manifest_id}:{appendix.get('appendix_status', '')}!={expected_exclusion_status}")

        if len(violations) >= 80:
            violations.append("transition_detail_violation_limit_reached")
            break

    return violations


def verify_packet(output_dir: Path, timeout_rerun_dir: Path | None, signoff_mode: str = "pre-review") -> tuple[list[dict[str, str]], int, int]:
    checks: list[dict[str, str]] = []

    for file_name in REQUIRED_FILES:
        path = output_dir / file_name
        add_bool_check(
            checks,
            f"FILE_{file_name.replace('.', '_').replace('/', '_')}",
            "artifact_presence",
            path.exists(),
            "required artifact exists",
            "exists" if path.exists() else "missing",
            file_name,
            "Regenerate the full experiment if this artifact is missing.",
        )

    blocker_diagnostics_expected = any((output_dir / file_name).exists() for file_name in BENCHMARK_BLOCKER_FILES)
    if blocker_diagnostics_expected:
        for file_name in BENCHMARK_BLOCKER_FILES:
            path = output_dir / file_name
            add_bool_check(
                checks,
                f"FILE_{file_name.replace('.', '_').replace('/', '_')}",
                "artifact_presence",
                path.exists(),
                "benchmark blocker diagnostic artifact exists",
                "exists" if path.exists() else "missing",
                file_name,
                "Run analyze_benchmark_blockers.py before packet verification.",
            )

    hardcoded_benchmark_expected = any((output_dir / file_name).exists() for file_name in HARDCODED_BENCHMARK_FILES)
    if hardcoded_benchmark_expected:
        for file_name in HARDCODED_BENCHMARK_FILES:
            path = output_dir / file_name
            add_bool_check(
                checks,
                f"FILE_{file_name.replace('.', '_').replace('/', '_')}",
                "artifact_presence",
                path.exists(),
                "hard-coded MoniTAal benchmark artifact exists",
                "exists" if path.exists() else "missing",
                file_name,
                "Run run_monitaal_hardcoded_benchmarks.py before packet verification.",
            )

    signoff_evidence_expected = any((output_dir / file_name).exists() for file_name in SIGNOFF_EVIDENCE_BUNDLE_FILES)
    if signoff_evidence_expected:
        for file_name in SIGNOFF_EVIDENCE_BUNDLE_FILES:
            path = output_dir / file_name
            add_bool_check(
                checks,
                f"FILE_{file_name.replace('.', '_').replace('/', '_')}",
                "artifact_presence",
                path.exists(),
                "review signoff evidence bundle artifact exists",
                "exists" if path.exists() else "missing",
                file_name,
                "Run build_signoff_evidence_bundle.py before packet verification.",
            )

    signoff_roundtrip_expected = any((output_dir / file_name).exists() for file_name in SIGNOFF_ROUNDTRIP_AUDIT_FILES)
    if signoff_roundtrip_expected:
        for file_name in SIGNOFF_ROUNDTRIP_AUDIT_FILES:
            path = output_dir / file_name
            add_bool_check(
                checks,
                f"FILE_{file_name.replace('.', '_').replace('/', '_')}",
                "artifact_presence",
                path.exists(),
                "signoff import roundtrip audit artifact exists",
                "exists" if path.exists() else "missing",
                file_name,
                "Run audit_signoff_import_roundtrip.py before packet verification.",
            )

    summary_path = output_dir / "experiment_summary.json"
    summary = read_json(summary_path) if summary_path.exists() else {}

    add_bool_check(
        checks,
        "SUMMARY_WORKBOOK_STATUS",
        "summary",
        summary.get("workbook_status") == "ok",
        "workbook_status=ok",
        f"workbook_status={summary.get('workbook_status', '')}",
        "experiment_summary.json",
        "Do not use the workbook if workbook_status is not ok.",
    )

    workbook = resolve_workbook_path(output_dir, summary)
    sheet_names, worksheet_count, table_count, workbook_error = workbook_sheet_names(workbook)
    optional_workbook_sheets: list[str] = []
    if blocker_diagnostics_expected:
        optional_workbook_sheets.append("Benchmark Blockers")
    if hardcoded_benchmark_expected:
        optional_workbook_sheets.append("Hardcoded Benchmarks")
    if signoff_evidence_expected:
        optional_workbook_sheets.append("Signoff Evidence")
    if (output_dir / "review_signoff_validation.csv").exists():
        optional_workbook_sheets.append("Signoff Validation")
    if (output_dir / "signoff_import_roundtrip_audit.csv").exists():
        optional_workbook_sheets.append("Signoff Roundtrip")
    timeout_workbook_evidence_expected = (output_dir / "timeout_rerun_summary.csv").exists() or (output_dir / "timeout_rerun_details.csv").exists()
    if timeout_workbook_evidence_expected:
        optional_workbook_sheets.extend(["Timeout Rerun Summary", "Timeout Rerun"])
    formula_catalog_workbook_expected = any(
        (output_dir / csv_file).exists() or sheet_name in sheet_names
        for sheet_name, csv_file in MITL_FORMULA_CATALOG_WORKBOOK_SPECS
    )
    if formula_catalog_workbook_expected:
        optional_workbook_sheets.extend(sheet_name for sheet_name, _ in MITL_FORMULA_CATALOG_WORKBOOK_SPECS)
    minimum_workbook_items = 30 + len(optional_workbook_sheets)
    add_bool_check(
        checks,
        "WORKBOOK_ZIP_OK",
        "workbook",
        workbook.exists() and workbook_error is None,
        "xlsx exists and zip integrity check passes",
        "ok" if workbook.exists() and workbook_error is None else f"error={workbook_error or 'missing'}",
        "paper_review_results.xlsx",
        "Rebuild the workbook before manual review.",
    )
    add_bool_check(
        checks,
        "WORKBOOK_SHEET_TABLE_COUNT",
        "workbook",
        worksheet_count >= minimum_workbook_items
        and table_count >= minimum_workbook_items,
        "workbook has all core sheets plus any generated optional review-evidence sheets",
        f"worksheets={worksheet_count}; tables={table_count}",
        "paper_review_results.xlsx",
        "Inspect workbook generation if sheet/table counts shrink.",
    )
    required_workbook_sheets = list(REQUIRED_WORKBOOK_SHEETS)
    required_workbook_sheets.extend(optional_workbook_sheets)
    missing_sheets = [sheet for sheet in required_workbook_sheets if sheet not in sheet_names]
    add_bool_check(
        checks,
        "WORKBOOK_REVIEW_SHEETS",
        "workbook",
        not missing_sheets,
        "review-critical sheets are present",
        "missing=" + ";".join(missing_sheets),
        "paper_review_results.xlsx",
        "Do not start manual review from an incomplete workbook.",
    )

    scan_path = output_dir / "workbook_formula_error_scan.ndjson"
    scan_text = scan_path.read_text(encoding="utf-8", errors="replace") if scan_path.exists() else ""
    add_bool_check(
        checks,
        "WORKBOOK_FORMULA_ERROR_SCAN",
        "workbook",
        "matched 0 entries" in scan_text,
        "formula error scan matched 0 entries",
        scan_text.strip()[:200],
        "workbook_formula_error_scan.ndjson",
        "Investigate formula errors before citing workbook tables.",
    )

    preview_manifest_violations = collect_workbook_preview_manifest_violations(
        output_dir,
        sheet_names,
        worksheet_count,
        required_workbook_sheets,
    )
    add_bool_check(
        checks,
        "WORKBOOK_PREVIEW_MANIFEST_AUDIT",
        "workbook",
        not preview_manifest_violations,
        "workbook preview manifest maps every workbook sheet to an existing source CSV with matching shape and valid preview status",
        "violations=" + (";".join(preview_manifest_violations[:20]) if preview_manifest_violations else "none"),
        "workbook_preview_manifest.csv; workbook_preview_manifest.json; paper_review_results.xlsx",
        "Rebuild the workbook if sheet/source mappings, CSV shapes, or preview statuses drift.",
    )

    workbook_source_violations = collect_workbook_source_coverage_violations(
        output_dir,
        summary,
        required_workbook_sheets,
    )
    add_bool_check(
        checks,
        "WORKBOOK_SOURCE_COVERAGE_AUDIT",
        "workbook",
        not workbook_source_violations,
        "review workbook sheets are bound to their expected source CSVs and summary row counts",
        "violations=" + (";".join(workbook_source_violations[:20]) if workbook_source_violations else "none"),
        "workbook_preview_manifest.csv; experiment_summary.json; paper_review_results.xlsx",
        "Rebuild the workbook and fix the sheet/source specification if review sheets point at the wrong CSV or row counts drift.",
    )

    xlsx_table_shape_violations = collect_workbook_xlsx_table_shape_violations(
        output_dir,
        workbook,
        required_workbook_sheets,
    )
    add_bool_check(
        checks,
        "WORKBOOK_XLSX_TABLE_SHAPE_AUDIT",
        "workbook",
        not xlsx_table_shape_violations,
        "xlsx internal table ranges match workbook manifest and source CSV shapes",
        "violations=" + (";".join(xlsx_table_shape_violations[:20]) if xlsx_table_shape_violations else "none"),
        "paper_review_results.xlsx; workbook_preview_manifest.csv; source CSV files",
        "Regenerate the workbook if the xlsx table ranges drift from the manifest or source CSV dimensions.",
    )

    mitl_catalog_workbook_violations = collect_mitl_formula_catalog_workbook_violations(
        output_dir,
        workbook,
        sheet_names,
    )
    add_bool_check(
        checks,
        "MITL_FORMULA_CATALOG_WORKBOOK_AUDIT",
        "workbook",
        not mitl_catalog_workbook_violations,
        "MITL formula catalog CSVs, workbook sheets, and xlsx table ranges are complete and shape-aligned when catalog artifacts are generated",
        "violations=" + (";".join(mitl_catalog_workbook_violations[:20]) if mitl_catalog_workbook_violations else "none"),
        "mitl_formula_catalog_semantic_regression.csv; mitl_formula_catalog_monitaal_xml_candidates.csv; mitl_formula_catalog_runtime_runs.csv; paper_review_results.xlsx",
        "Regenerate the formula catalog and rebuild the workbook before manual review.",
    )

    rebuild_summary_violations = collect_workbook_rebuild_summary_violations(
        output_dir,
        timeout_rerun_dir,
        summary,
        workbook,
        sheet_names,
    )
    add_bool_check(
        checks,
        "WORKBOOK_REBUILD_SUMMARY_AUDIT",
        "workbook",
        not rebuild_summary_violations,
        "final workbook rebuild summary matches experiment summary, workbook path, late sidecar CSVs, and late workbook sheets",
        "violations=" + (";".join(rebuild_summary_violations[:20]) if rebuild_summary_violations else "none"),
        "workbook_rebuild_summary.csv; workbook_rebuild_summary.json; paper_review_results.xlsx",
        "Run rebuild_review_workbook.py after late sidecars and before packet verification.",
    )

    csv_specs = [
        ("review_guide.csv", "review_guide_rows", None),
        ("human_review_queue.csv", "human_review_queue_rows", None),
        ("review_signoff_template.csv", "review_signoff_template_rows", None),
        ("goal_completion_audit.csv", "goal_completion_rows", None),
        ("manual_review_checklist.csv", "manual_review_rows", None),
        ("requirements_traceability_audit.csv", "requirements_audit_rows", None),
        ("mitl_correctness_audit.csv", "mitl_correctness_audit_rows", None),
        ("semantic_oracle_derivations.csv", "semantic_oracle_derivation_rows", None),
        ("manual_oracle_guide.csv", "manual_oracle_guide_rows", None),
        ("xml_proof_obligations.csv", "xml_proof_obligation_rows", None),
        ("xml_trace_coverage_obligations.csv", "xml_trace_coverage_rows", None),
        ("xml_original_trace_gaps.csv", "xml_original_trace_gap_rows", None),
        ("gear_original_input_response_audit.csv", "gear_original_input_response_audit_rows", None),
        ("non_gear_original_input_search_audit.csv", "non_gear_original_input_search_audit_rows", None),
        ("semantic_prefix_oracle_review.csv", "semantic_prefix_oracle_rows", None),
        ("cli_contract_audit.csv", "cli_contract_rows", None),
        ("translation_candidate_results.csv", "translation_candidate_runs", None),
        ("monitaal_baseline_results.csv", None, "baseline"),
        ("monitaal_embedded_benchmarks.csv", "embedded_benchmark_records", None),
    ]
    csv_cache: dict[str, list[dict[str, str]]] = {}
    for file_name, summary_key, special in csv_specs:
        path = output_dir / file_name
        rows = read_csv(path) if path.exists() else []
        csv_cache[file_name] = rows
        if summary_key:
            expected = summary_int(summary, summary_key)
            ok = len(rows) == expected
            observed = f"rows={len(rows)}; summary={expected}"
        else:
            expected = summary_int(summary, "baseline_runs") + summary_int(summary, "baseline_timeouts") + summary_int(summary, "baseline_skipped_no_input")
            ok = len(rows) == expected
            observed = f"rows={len(rows)}; summary_baseline_total={expected}"
        add_bool_check(
            checks,
            f"CSV_COUNT_{file_name.replace('.', '_')}",
            "csv_summary_consistency",
            ok,
            "CSV row count matches experiment_summary.json",
            observed,
            file_name,
            "Rerun packet generation if summary and CSV row counts diverge.",
        )

    candidate_prefix_rows = read_csv(output_dir / "candidate_prefix_observations.csv") if (output_dir / "candidate_prefix_observations.csv").exists() else []
    candidate_step_rows = read_csv(output_dir / "candidate_step_audit.csv") if (output_dir / "candidate_step_audit.csv").exists() else []
    candidate_prefix_violations = collect_candidate_prefix_observation_violations(
        output_dir,
        summary,
        csv_cache.get("translation_candidate_results.csv", []),
        candidate_prefix_rows,
        candidate_step_rows,
    )
    add_bool_check(
        checks,
        "CANDIDATE_PREFIX_OBSERVATIONS_AUDIT",
        "runtime_evidence",
        not candidate_prefix_violations,
        "candidate raw prefix observations match summary counts, compact step audit rows, and per-run steps.csv artifacts",
        "violations=" + (";".join(candidate_prefix_violations[:20]) if candidate_prefix_violations else "none"),
        "candidate_prefix_observations.csv; candidate_step_audit.csv; translation_candidate_runs/*/steps.csv",
        "Regenerate candidate runtime evidence if raw prefix rows drift from compact step audit rows or per-run steps.csv files.",
    )

    monitaal_transition_violations = collect_monitaal_transition_detail_violations(
        output_dir,
        summary,
        read_csv(output_dir / "benchmark_manifest.csv") if (output_dir / "benchmark_manifest.csv").exists() else [],
        read_csv(output_dir / "monitaal_xml_inventory.csv") if (output_dir / "monitaal_xml_inventory.csv").exists() else [],
        read_csv(output_dir / "monitaal_translation_review.csv") if (output_dir / "monitaal_translation_review.csv").exists() else [],
        read_csv(output_dir / "monitaal_transition_details.csv") if (output_dir / "monitaal_transition_details.csv").exists() else [],
        read_csv(output_dir / "xml_edge_guard_proofs.csv") if (output_dir / "xml_edge_guard_proofs.csv").exists() else [],
        read_csv(output_dir / "xml_proof_appendix.csv") if (output_dir / "xml_proof_appendix.csv").exists() else [],
    )
    add_bool_check(
        checks,
        "MONITAAL_XML_STRUCTURAL_LEDGER_AUDIT",
        "claim_safety",
        not monitaal_transition_violations,
        "MoniTAal XML inventory, transition details, translation candidates, edge-proof ledger, and appendix are structurally consistent without claiming XML-to-MITL equivalence",
        "violations=" + (";".join(monitaal_transition_violations[:20]) if monitaal_transition_violations else "none"),
        "benchmark_manifest.csv; monitaal_xml_inventory.csv; monitaal_translation_review.csv; monitaal_transition_details.csv; xml_edge_guard_proofs.csv; xml_proof_appendix.csv",
        "Regenerate XML review artifacts or fix the producer if structural counts, pair references, transition evidence, or appendix mappings drift.",
    )

    (
        verdict_violations,
        observed_verdicts,
        checked_verdict_sources,
        checked_verdict_columns,
        checked_verdict_values,
    ) = collect_public_verdict_violations(output_dir)
    invalid_preview = ";".join(verdict_violations[:8])
    observed_preview = ",".join(
        f"{key}={observed_verdicts[key]}"
        for key in sorted(observed_verdicts)
    )
    add_bool_check(
        checks,
        "PUBLIC_RV_THREE_VALUED_VERDICTS",
        "runtime_surface",
        not verdict_violations
        and checked_verdict_sources > 0
        and checked_verdict_columns > 0
        and checked_verdict_values > 0,
        "public RV verdict fields are POSITIVE/NEGATIVE/INCONCLUSIVE, with NOT_RUN_BUILD_ONLY only for build-only final-verdict fields",
        (
            f"sources={checked_verdict_sources}; columns={checked_verdict_columns}; "
            f"values={checked_verdict_values}; observed={observed_preview}; "
            f"invalid={invalid_preview or 'none'}"
        ),
        "semantic_regression_results.csv; semantic_prefix_oracle_review.csv; translation_candidate_results.csv; per-run steps.csv; per-run metadata.json",
        "Fix the producer if an internal monitor state such as INCONSISTENT leaks into any public runtime-verdict artifact.",
    )

    if blocker_diagnostics_expected:
        blocker_csv = output_dir / "benchmark_blocker_diagnostics.csv"
        blocker_json = output_dir / "benchmark_blocker_diagnostics.json"
        blocker_rows = read_csv(blocker_csv) if blocker_csv.exists() else []
        blocker_data = read_json(blocker_json) if blocker_json.exists() else {}
        expected_rows = summary_int(blocker_data, "row_count")
        add_bool_check(
            checks,
            "BENCHMARK_BLOCKER_DIAGNOSTICS_COUNT",
            "benchmark_blocker_diagnostics",
            len(blocker_rows) == expected_rows and expected_rows > 0,
            "blocker diagnostics CSV row count matches JSON row_count",
            f"csv_rows={len(blocker_rows)}; json_row_count={expected_rows}",
            "benchmark_blocker_diagnostics.csv; benchmark_blocker_diagnostics.json",
            "Regenerate blocker diagnostics before using the workbook for XML blocker review.",
        )

    if hardcoded_benchmark_expected:
        hardcoded_csv = output_dir / "monitaal_hardcoded_benchmarks.csv"
        hardcoded_json = output_dir / "monitaal_hardcoded_benchmarks.json"
        hardcoded_rows = read_csv(hardcoded_csv) if hardcoded_csv.exists() else []
        hardcoded_data = read_json(hardcoded_json) if hardcoded_json.exists() else {}
        expected_rows = summary_int(hardcoded_data, "row_count")
        bad_rows = [
            row for row in hardcoded_rows
            if row.get("status") != "ran"
            or row.get("parse_status") != "parsed"
            or row.get("source_kind") != "monitaal_hardcoded_cpp"
            or "do not cite as XML-to-MITL equivalence proof" not in row.get("evidence_boundary", "")
        ]
        add_bool_check(
            checks,
            "HARDCODED_BENCHMARK_BOUNDARY",
            "monitaal_hardcoded_benchmarks",
            len(hardcoded_rows) == expected_rows
            and expected_rows >= 7
            and hardcoded_data.get("error") == 0
            and hardcoded_data.get("timeout") == 0
            and hardcoded_data.get("parse_failed") == 0
            and not bad_rows
            and "Hardcoded Benchmarks" in sheet_names,
            "hard-coded MoniTAal benchmark rows are complete, parsed, and separated from XML-to-MITL claims",
            (
                f"csv_rows={len(hardcoded_rows)}; json_row_count={expected_rows}; "
                f"error={hardcoded_data.get('error')}; timeout={hardcoded_data.get('timeout')}; "
                f"parse_failed={hardcoded_data.get('parse_failed')}; bad_rows={len(bad_rows)}; "
                f"sheet={'Hardcoded Benchmarks' in sheet_names}"
            ),
            "monitaal_hardcoded_benchmarks.csv; monitaal_hardcoded_benchmarks.json; paper_review_results.xlsx",
            "Keep hard-coded benchmark evidence separate from XML MoniTAal-bin baseline claims.",
        )

    if signoff_evidence_expected:
        evidence_csv = output_dir / "review_signoff_evidence_bundle.csv"
        evidence_json = output_dir / "review_signoff_evidence_bundle.json"
        evidence_rows = read_csv(evidence_csv) if evidence_csv.exists() else []
        evidence_data = read_json(evidence_json) if evidence_json.exists() else {}
        evidence_summary = (
            evidence_data.get("summary", {})
            if isinstance(evidence_data, dict)
            else {}
        )
        evidence_signoff_rows = csv_cache.get("review_signoff_template.csv", [])
        fail_rows = count_rows(evidence_rows, bundle_status="FAIL")
        missing_boundaries = [
            row.get("signoff_id", "")
            for row in evidence_rows
            if not row.get("reviewer_boundary", "").strip()
        ]
        add_bool_check(
            checks,
            "SIGNOFF_EVIDENCE_BUNDLE_SUMMARY",
            "review_packet",
            len(evidence_rows) == summary_int(evidence_summary, "row_count")
            and len(evidence_rows) == len(evidence_signoff_rows)
            and summary_int(evidence_summary, "pass") == len(evidence_rows)
            and summary_int(evidence_summary, "fail") == 0
            and summary_int(evidence_summary, "missing_queue_rows") == 0
            and summary_int(evidence_summary, "missing_source_rows") == 0
            and summary_int(evidence_summary, "unresolved_evidence_tokens") == 0
            and evidence_summary.get("generated_only") is True
            and evidence_summary.get("human_signoff_claim") == "not_claimed"
            and not fail_rows
            and not missing_boundaries
            and "Signoff Evidence" in sheet_names,
            "signoff evidence bundle covers every signoff row, resolves queue/source/evidence references, and does not claim human approval",
            (
                f"csv_rows={len(evidence_rows)}; signoff_rows={len(evidence_signoff_rows)}; "
                f"json_row_count={evidence_summary.get('row_count', '')}; "
                f"pass={evidence_summary.get('pass', '')}; fail={evidence_summary.get('fail', '')}; "
                f"missing_queue_rows={evidence_summary.get('missing_queue_rows', '')}; "
                f"missing_source_rows={evidence_summary.get('missing_source_rows', '')}; "
                f"unresolved_evidence_tokens={evidence_summary.get('unresolved_evidence_tokens', '')}; "
                f"generated_only={evidence_summary.get('generated_only', '')}; "
                f"human_signoff_claim={evidence_summary.get('human_signoff_claim', '')}; "
                f"csv_fail_rows={fail_rows}; missing_boundaries={len(missing_boundaries)}; "
                f"sheet={'Signoff Evidence' in sheet_names}"
            ),
            "review_signoff_evidence_bundle.csv; review_signoff_evidence_bundle.json; paper_review_results.xlsx",
            "Use the bundle as a review index only; reviewer_decision must still be filled by a human.",
        )
        bad_source_counts = [
            row.get("signoff_id", "")
            for row in evidence_rows
            if summary_int(row, "source_row_count") <= 0
            or not row.get("source_excerpt", "").strip()
            or not row.get("must_not_claim", "").strip()
            or not row.get("next_action", "").strip()
        ]
        add_bool_check(
            checks,
            "SIGNOFF_EVIDENCE_BUNDLE_CONTEXT",
            "review_packet",
            not bad_source_counts,
            "each signoff evidence row includes source excerpt, source row count, must_not_claim, and next_action context",
            f"bad_rows={len(bad_source_counts)}; preview={';'.join(bad_source_counts[:8])}",
            "review_signoff_evidence_bundle.csv",
            "Fix missing bundle context before asking a reviewer to sign off the packet.",
        )

    if signoff_roundtrip_expected:
        roundtrip_csv = output_dir / "signoff_import_roundtrip_audit.csv"
        roundtrip_json = output_dir / "signoff_import_roundtrip_audit.json"
        roundtrip_rows = read_csv(roundtrip_csv) if roundtrip_csv.exists() else []
        roundtrip_data = read_json(roundtrip_json) if roundtrip_json.exists() else {}
        roundtrip_summary = (
            roundtrip_data.get("summary", {})
            if isinstance(roundtrip_data, dict)
            else {}
        )
        roundtrip_fail_rows = count_rows(roundtrip_rows, status="FAIL")
        roundtrip_ids = {row.get("check_id", "") for row in roundtrip_rows}
        missing_roundtrip_ids = sorted(SIGNOFF_ROUNDTRIP_REQUIRED_CHECKS - roundtrip_ids)
        add_bool_check(
            checks,
            "SIGNOFF_ROUNDTRIP_AUDIT_SUMMARY",
            "review_packet",
            len(roundtrip_rows) == summary_int(roundtrip_summary, "row_count")
            and summary_int(roundtrip_summary, "pass") == len(roundtrip_rows)
            and summary_int(roundtrip_summary, "fail") == 0
            and summary_int(roundtrip_summary, "warn") == 0
            and summary_int(roundtrip_summary, "expected_signoff_rows") > 0
            and summary_int(roundtrip_summary, "imported_nonblank_decisions") == summary_int(roundtrip_summary, "expected_signoff_rows")
            and roundtrip_summary.get("synthetic_only") is True
            and roundtrip_summary.get("human_signoff_claim") == "not_claimed"
            and roundtrip_fail_rows == 0
            and "Signoff Roundtrip" in sheet_names,
            "synthetic signoff import roundtrip audit passes and is exposed in the workbook without claiming human approval",
            (
                f"csv_rows={len(roundtrip_rows)}; json_row_count={roundtrip_summary.get('row_count', '')}; "
                f"pass={roundtrip_summary.get('pass', '')}; fail={roundtrip_summary.get('fail', '')}; "
                f"warn={roundtrip_summary.get('warn', '')}; synthetic_only={roundtrip_summary.get('synthetic_only', '')}; "
                f"expected_signoff_rows={roundtrip_summary.get('expected_signoff_rows', '')}; "
                f"imported_nonblank_decisions={roundtrip_summary.get('imported_nonblank_decisions', '')}; "
                f"human_signoff_claim={roundtrip_summary.get('human_signoff_claim', '')}; "
                f"csv_fail={roundtrip_fail_rows}; sheet={'Signoff Roundtrip' in sheet_names}"
            ),
            "signoff_import_roundtrip_audit.csv; signoff_import_roundtrip_audit.json; paper_review_results.xlsx",
            "Treat this as import-workflow regression evidence only; it is not a substitute for human MITL-oracle signoff.",
        )
        add_bool_check(
            checks,
            "SIGNOFF_ROUNDTRIP_REQUIRED_CHECKS",
            "review_packet",
            not missing_roundtrip_ids
            and all(row.get("reviewer_boundary", "") for row in roundtrip_rows),
            "roundtrip audit covers CSV dry-run, workbook extraction, CSV apply, complete validation, workbook rebuild, complete packet verification, and stale generated-field rejection",
            (
                f"missing_checks={';'.join(missing_roundtrip_ids)}; "
                f"rows_with_boundary={sum(1 for row in roundtrip_rows if row.get('reviewer_boundary', ''))}/{len(roundtrip_rows)}"
            ),
            "signoff_import_roundtrip_audit.csv",
            "Keep stale-field rejection and synthetic-vs-human boundaries visible before using the import path for completed review.",
        )

    if timeout_rerun_dir:
        timeout_summary_csv = output_dir / "timeout_rerun_summary.csv"
        timeout_details_csv = output_dir / "timeout_rerun_details.csv"
        add_bool_check(
            checks,
            "TIMEOUT_RERUN_WORKBOOK_EVIDENCE",
            "benchmark_caveats",
            timeout_summary_csv.exists()
            and timeout_details_csv.exists()
            and "Timeout Rerun Summary" in sheet_names
            and "Timeout Rerun" in sheet_names,
            "timeout rerun summary/details are copied into the review workbook",
            (
                f"summary_csv={timeout_summary_csv.exists()}; details_csv={timeout_details_csv.exists()}; "
                f"summary_sheet={'Timeout Rerun Summary' in sheet_names}; details_sheet={'Timeout Rerun' in sheet_names}"
            ),
            "timeout_rerun_summary.csv; timeout_rerun_details.csv; paper_review_results.xlsx",
            "Run rebuild_review_workbook.py with --timeout-rerun-dir before packet verification.",
        )

    review_guide = csv_cache.get("review_guide.csv", [])
    add_bool_check(
        checks,
        "REVIEW_GUIDE_SCOPE",
        "review_packet",
        len(review_guide) >= 13 and count_rows(review_guide, priority="P0") >= 7,
        "review guide has at least 13 rows and 7 P0 rows",
        f"rows={len(review_guide)}; p0={count_rows(review_guide, priority='P0')}",
        "review_guide.csv",
        "Keep review instructions conservative and visible.",
    )
    review_entrypoint_violations = collect_review_entrypoint_reference_violations(
        output_dir,
        set(sheet_names),
        summary,
        review_guide,
        csv_cache.get("goal_completion_audit.csv", []),
        csv_cache.get("manual_review_checklist.csv", []),
        csv_cache.get("requirements_traceability_audit.csv", []),
        allow_roundtrip_self_reference=signoff_mode == "complete",
    )
    add_bool_check(
        checks,
        "MANUAL_REVIEW_ENTRYPOINT_REFERENCES",
        "review_packet",
        not review_entrypoint_violations,
        "review guide, goal audit, manual checklist, and requirements audit rows have resolving evidence artifacts, workbook-sheet references, sidecar IDs, and summary-aligned statuses",
        "violations=" + (";".join(review_entrypoint_violations[:20]) if review_entrypoint_violations else "none"),
        "review_guide.csv/json/md; goal_completion_audit.csv/json/md; manual_review_checklist.csv/json/md; requirements_traceability_audit.csv/md; paper_review_results.xlsx",
        "Fix dangling manual-review entrypoint evidence before asking a human reviewer to use the packet.",
    )

    queue_rows = csv_cache.get("human_review_queue.csv", [])
    add_bool_check(
        checks,
        "REVIEW_QUEUE_NO_FAIL",
        "review_packet",
        count_rows(queue_rows, review_status="FAIL") == 0 and len(queue_rows) == summary_int(summary, "human_review_queue_rows"),
        "review queue has no FAIL rows and matches summary count",
        f"rows={len(queue_rows)}; fail={count_rows(queue_rows, review_status='FAIL')}",
        "human_review_queue.csv",
        "Fix failing queue evidence before manual signoff.",
    )
    queue_unresolved_sheets, queue_unresolved_rows = collect_source_reference_violations(
        output_dir,
        set(sheet_names),
        queue_rows,
        "queue_id",
    )
    add_bool_check(
        checks,
        "REVIEW_QUEUE_SOURCE_REFERENCES",
        "review_packet",
        not queue_unresolved_sheets and not queue_unresolved_rows,
        "every review queue source_sheet resolves to a workbook sheet and every source_id resolves to its generated source CSV row",
        (
            f"rows={len(queue_rows)}; "
            f"unresolved_source_sheets={len(queue_unresolved_sheets)}; "
            f"unresolved_source_rows={len(queue_unresolved_rows)}; "
            f"source_sheet_preview={';'.join(queue_unresolved_sheets[:8])}; "
            f"source_row_preview={';'.join(queue_unresolved_rows[:8])}"
        ),
        "human_review_queue.csv; paper_review_results.xlsx; linked source CSV artifacts",
        "Fix dangling review queue source references before asking for manual review.",
    )
    queue_missing_evidence_rows, queue_unresolved_evidence_tokens = collect_evidence_reference_violations(
        output_dir,
        set(sheet_names),
        queue_rows,
        "queue_id",
    )
    add_bool_check(
        checks,
        "REVIEW_QUEUE_EVIDENCE_REFERENCES",
        "review_packet",
        not queue_missing_evidence_rows and not queue_unresolved_evidence_tokens,
        "every review queue row has review context and each evidence_artifacts token resolves",
        (
            f"rows={len(queue_rows)}; "
            f"missing_context_rows={len(queue_missing_evidence_rows)}; "
            f"unresolved_evidence_tokens={len(queue_unresolved_evidence_tokens)}; "
            f"missing_preview={';'.join(queue_missing_evidence_rows[:8])}; "
            f"unresolved_preview={';'.join(queue_unresolved_evidence_tokens[:8])}"
        ),
        "human_review_queue.csv; paper_review_results.xlsx; linked evidence artifacts",
        "Fix dangling review queue evidence references before asking for manual review.",
    )

    signoff_rows = csv_cache.get("review_signoff_template.csv", [])
    blank_decisions = sum(1 for row in signoff_rows if not row.get("reviewer_decision"))
    nonblank_decisions = len(signoff_rows) - blank_decisions
    signoff_complete_mode = signoff_mode == "complete"
    add_bool_check(
        checks,
        "REVIEW_SIGNOFF_COMPLETION_BOUNDARY" if signoff_complete_mode else "REVIEW_SIGNOFF_BLANK",
        "review_packet",
        (
            blank_decisions == 0
            and nonblank_decisions == len(signoff_rows) == summary_int(summary, "review_signoff_template_rows")
            if signoff_complete_mode
            else blank_decisions == len(signoff_rows) == summary_int(summary, "review_signoff_template_rows")
        ),
        "all signoff decisions are filled after human review" if signoff_complete_mode else "all generated signoff decisions remain blank before human review",
        f"rows={len(signoff_rows)}; blank_decisions={blank_decisions}; nonblank_decisions={nonblank_decisions}; mode={signoff_mode}",
        "review_signoff_template.csv",
        "Use complete mode only after importing human decisions and running complete signoff validation." if signoff_complete_mode else "Do not claim human review is complete from a blank template.",
    )

    signoff_validation_csv = read_csv(output_dir / "review_signoff_validation.csv") if (output_dir / "review_signoff_validation.csv").exists() else []
    signoff_validation_json = read_json(output_dir / "review_signoff_validation.json") if (output_dir / "review_signoff_validation.json").exists() else {}
    signoff_validation_summary = (
        signoff_validation_json.get("summary", {})
        if isinstance(signoff_validation_json, dict)
        else {}
    )
    signoff_validation_fail_rows = count_rows(signoff_validation_csv, status="FAIL")
    add_bool_check(
        checks,
        "SIGNOFF_VALIDATION_SUMMARY_PASS",
        "review_packet",
        signoff_validation_summary.get("mode") == signoff_mode
        and signoff_validation_summary.get("completion_state") == ("HUMAN_SIGNOFF_COMPLETE" if signoff_complete_mode else "READY_FOR_HUMAN_REVIEW_NOT_SIGNED")
        and summary_int(signoff_validation_summary, "pass") == summary_int(signoff_validation_summary, "validation_rows")
        and summary_int(signoff_validation_summary, "fail") == 0,
        "review signoff validation is a passing complete check" if signoff_complete_mode else "review signoff validation is a passing pre-review check",
        (
            f"mode={signoff_validation_summary.get('mode', '')}; "
            f"completion_state={signoff_validation_summary.get('completion_state', '')}; "
            f"pass={signoff_validation_summary.get('pass', '')}; "
            f"fail={signoff_validation_summary.get('fail', '')}"
        ),
        "review_signoff_validation.json",
        "Run validate_review_signoff.py --mode complete after importing human decisions." if signoff_complete_mode else "Run validate_review_signoff.py before treating the packet as ready for human review.",
    )
    add_bool_check(
        checks,
        "SIGNOFF_VALIDATION_ROW_COUNT",
        "review_packet",
        len(signoff_validation_csv) == summary_int(signoff_validation_summary, "validation_rows")
        and signoff_validation_fail_rows == 0,
        "validation CSV row count matches JSON summary and has no FAIL rows",
        (
            f"csv_rows={len(signoff_validation_csv)}; "
            f"summary_rows={signoff_validation_summary.get('validation_rows', '')}; "
            f"csv_fail={signoff_validation_fail_rows}"
        ),
        "review_signoff_validation.csv; review_signoff_validation.json",
        "Regenerate signoff validation if the CSV and JSON disagree.",
    )
    signoff_validation_check_ids = {row.get("check_id", "") for row in signoff_validation_csv}
    missing_queue_source_validation_checks = sorted({
        "QUEUE_SOURCE_SHEET_RESOLUTION",
        "QUEUE_SOURCE_ROW_RESOLUTION",
    } - signoff_validation_check_ids)
    add_bool_check(
        checks,
        "SIGNOFF_VALIDATION_QUEUE_SOURCE_CHECKS",
        "review_packet",
        not missing_queue_source_validation_checks
        and summary_int(signoff_validation_summary, "unresolved_queue_source_sheet_tokens") == 0
        and summary_int(signoff_validation_summary, "unresolved_queue_source_rows") == 0,
        "signoff validation artifact includes passing queue-wide source reference checks",
        (
            f"missing_checks={';'.join(missing_queue_source_validation_checks)}; "
            f"unresolved_queue_source_sheet_tokens={signoff_validation_summary.get('unresolved_queue_source_sheet_tokens', '')}; "
            f"unresolved_queue_source_rows={signoff_validation_summary.get('unresolved_queue_source_rows', '')}"
        ),
        "review_signoff_validation.csv; review_signoff_validation.json",
        "Regenerate signoff validation with the current validator before packet verification.",
    )
    missing_queue_evidence_validation_checks = sorted({
        "QUEUE_EVIDENCE_FIELDS_PRESENT",
        "QUEUE_EVIDENCE_RESOLUTION",
    } - signoff_validation_check_ids)
    add_bool_check(
        checks,
        "SIGNOFF_VALIDATION_QUEUE_EVIDENCE_CHECKS",
        "review_packet",
        not missing_queue_evidence_validation_checks
        and summary_int(signoff_validation_summary, "missing_queue_evidence_rows") == 0
        and summary_int(signoff_validation_summary, "unresolved_queue_evidence_tokens") == 0,
        "signoff validation artifact includes passing queue-wide evidence reference checks",
        (
            f"missing_checks={';'.join(missing_queue_evidence_validation_checks)}; "
            f"missing_queue_evidence_rows={signoff_validation_summary.get('missing_queue_evidence_rows', '')}; "
            f"unresolved_queue_evidence_tokens={signoff_validation_summary.get('unresolved_queue_evidence_tokens', '')}"
        ),
        "review_signoff_validation.csv; review_signoff_validation.json",
        "Regenerate signoff validation with the current validator before packet verification.",
    )
    add_bool_check(
        checks,
        "SIGNOFF_VALIDATION_TEMPLATE_SYNC",
        "review_packet",
        summary_int(signoff_validation_summary, "signoff_rows") == len(signoff_rows)
        and summary_int(signoff_validation_summary, "blank_decisions") == blank_decisions
        and summary_int(signoff_validation_summary, "nonblank_decisions") == nonblank_decisions
        and summary_int(signoff_validation_summary, "expected_signoff_queue_rows") == len(signoff_rows),
        "signoff validation is synchronized with the complete signoff template" if signoff_complete_mode else "signoff validation is synchronized with the blank generated signoff template",
        (
            f"validation_signoff_rows={signoff_validation_summary.get('signoff_rows', '')}; "
            f"template_rows={len(signoff_rows)}; "
            f"blank_decisions={signoff_validation_summary.get('blank_decisions', '')}; "
            f"nonblank_decisions={signoff_validation_summary.get('nonblank_decisions', '')}; "
            f"expected_queue_rows={signoff_validation_summary.get('expected_signoff_queue_rows', '')}"
        ),
        "review_signoff_validation.json; review_signoff_template.csv",
        "Do not cite the signoff sheet if validation and template counts drift.",
    )

    requirements = csv_cache.get("requirements_traceability_audit.csv", [])
    add_bool_check(
        checks,
        "REQUIREMENTS_NO_FAIL",
        "claim_safety",
        count_rows(requirements, status="FAIL") == 0,
        "requirements audit has 0 FAIL rows",
        f"fail={count_rows(requirements, status='FAIL')}; rows={len(requirements)}",
        "requirements_traceability_audit.csv",
        "Fix failed requirements before citing packet completeness.",
    )

    oracle_rows = csv_cache.get("semantic_oracle_derivations.csv", [])
    add_bool_check(
        checks,
        "ORACLE_DERIVATIONS_BOUNDARY",
        "correctness",
        count_rows(oracle_rows, oracle_status="HAND_ORACLE_VERIFIED") == summary_int(summary, "semantic_oracle_hand_verified")
        and count_rows(oracle_rows, oracle_status="CONSTRUCTION_STATS_ONLY") == summary_int(summary, "semantic_oracle_construction_stats_only")
        and summary_int(summary, "semantic_oracle_review_required") == 0
        and summary_int(summary, "semantic_oracle_prefix_mismatches") == 0,
        "oracle derivation counts match summary and have no review-required/prefix-mismatch rows",
        (
            f"hand={count_rows(oracle_rows, oracle_status='HAND_ORACLE_VERIFIED')}; "
            f"build_only={count_rows(oracle_rows, oracle_status='CONSTRUCTION_STATS_ONLY')}; "
            f"review_required={summary_int(summary, 'semantic_oracle_review_required')}; "
            f"prefix_mismatches={summary_int(summary, 'semantic_oracle_prefix_mismatches')}"
        ),
        "semantic_oracle_derivations.csv",
        "Do not count construction/stat-only rows as runtime correctness evidence.",
    )

    manual_oracle_guide = csv_cache.get("manual_oracle_guide.csv", [])
    guide_ids = {row.get("guide_id", "") for row in manual_oracle_guide}
    required_manual_oracle_ids = {
        "MOG_DEFINITION",
        "MOG_INDEPENDENCE",
        "MOG_BASELINE_NOT_HAND_ORACLE",
        "MOG_THREE_VALUED_PREFIX",
        "MOG_FINAL_VERDICT",
        "MOG_BUILD_STATS_BOUNDARY",
        "MOG_FIX_POLICY",
        "MOG_SIGNOFF_BOUNDARY",
    }
    missing_manual_oracle_ids = sorted(required_manual_oracle_ids - guide_ids)
    add_bool_check(
        checks,
        "MANUAL_ORACLE_GUIDE_PROTOCOL",
        "correctness",
        len(manual_oracle_guide) >= 8
        and count_rows(manual_oracle_guide, priority="P0") >= 4
        and not missing_manual_oracle_ids,
        "manual oracle guide has protocol rows for definition, independence, baseline-vs-hand-oracle boundary, prefix/final verdicts, build-only boundary, fix policy, and signoff boundary",
        (
            f"rows={len(manual_oracle_guide)}; p0={count_rows(manual_oracle_guide, priority='P0')}; "
            "missing=" + ";".join(missing_manual_oracle_ids)
        ),
        "manual_oracle_guide.csv",
        "Keep the hand-oracle review protocol visible before citing semantic correctness.",
    )

    prefix_rows = csv_cache.get("semantic_prefix_oracle_review.csv", [])
    add_bool_check(
        checks,
        "PREFIX_ORACLE_NO_MISMATCH",
        "correctness",
        count_rows(prefix_rows, prefix_oracle_status="MISMATCH") == 0
        and count_rows(prefix_rows, prefix_oracle_status="MISSING_OBSERVED_STEP") == 0
        and summary_int(summary, "semantic_prefix_oracle_mismatch") == 0
        and summary_int(summary, "semantic_prefix_oracle_missing_observed_step") == 0,
        "prefix oracle has no mismatch or missing observed-step rows",
        (
            f"csv_mismatch={count_rows(prefix_rows, prefix_oracle_status='MISMATCH')}; "
            f"csv_missing={count_rows(prefix_rows, prefix_oracle_status='MISSING_OBSERVED_STEP')}"
        ),
        "semantic_prefix_oracle_review.csv",
        "Investigate prefix mismatches before claiming stepwise RV correctness.",
    )

    cli_rows = csv_cache.get("cli_contract_audit.csv", [])
    add_bool_check(
        checks,
        "CLI_CONTRACT_PASS",
        "runtime_surface",
        count_rows(cli_rows, pass_status="FAIL") == 0 and count_rows(cli_rows, pass_status="PASS") == summary_int(summary, "cli_contract_pass"),
        "all CLI contract probes pass",
        f"pass={count_rows(cli_rows, pass_status='PASS')}; fail={count_rows(cli_rows, pass_status='FAIL')}",
        "cli_contract_audit.csv",
        "Fix CLI contract failures before demoing TAMonitor.",
    )

    claim_audit = read_csv(output_dir / "paper_claim_consistency_audit.csv") if (output_dir / "paper_claim_consistency_audit.csv").exists() else []
    paper_claim_rows = read_csv(output_dir / "paper_claim_review.csv") if (output_dir / "paper_claim_review.csv").exists() else []
    xml_obligation_rows = csv_cache.get("xml_proof_obligations.csv", [])
    xml_obligation_json = read_json(output_dir / "xml_proof_obligations.json") if (output_dir / "xml_proof_obligations.json").exists() else {}
    xml_obligation_summary = xml_obligation_json.get("summary", {}) if isinstance(xml_obligation_json, dict) else {}
    ready_manifest_ids = {
        row.get("manifest_id", "")
        for row in read_csv(output_dir / "xml_proof_appendix.csv")
        if row.get("appendix_status") == "PROOF_DRAFT_READY"
    } if (output_dir / "xml_proof_appendix.csv").exists() else set()
    machine_fail_rows = [
        row.get("obligation_id", "")
        for row in xml_obligation_rows
        if row.get("machine_checkable") == "true" and row.get("obligation_status") == "FAIL"
    ]
    human_review_manifest_ids = {
        row.get("manifest_id", "")
        for row in xml_obligation_rows
        if row.get("obligation_name") == "human_equivalence_signoff_required"
        and row.get("obligation_status") == "REVIEW_REQUIRED"
    }
    add_bool_check(
        checks,
        "XML_PROOF_OBLIGATION_AUDIT",
        "claim_safety",
        len(xml_obligation_rows) == summary_int(summary, "xml_proof_obligation_rows")
        and len(xml_obligation_rows) == summary_int(xml_obligation_summary, "row_count")
        and not machine_fail_rows
        and ready_manifest_ids == human_review_manifest_ids
        and summary_int(summary, "xml_proof_obligation_fail") == 0
        and summary_int(xml_obligation_summary, "fail") == 0,
        "XML proof obligations exist, have no machine-checkable FAIL rows, and keep one human equivalence signoff obligation per proof-ready XML row",
        (
            f"rows={len(xml_obligation_rows)}; summary_rows={summary_int(summary, 'xml_proof_obligation_rows')}; "
            f"json_rows={summary_int(xml_obligation_summary, 'row_count')}; "
            f"machine_fail={len(machine_fail_rows)}; ready={len(ready_manifest_ids)}; "
            f"human_review={len(human_review_manifest_ids)}; json_fail={summary_int(xml_obligation_summary, 'fail')}; "
            f"bad_preview={';'.join(machine_fail_rows[:8])}"
        ),
        "xml_proof_obligations.csv; xml_proof_obligations.json; xml_proof_appendix.csv",
        "Fix machine-checkable proof prerequisites before manual review; keep REVIEW_REQUIRED rows as human proof obligations, not automatic failures.",
    )
    xml_trace_rows = csv_cache.get("xml_trace_coverage_obligations.csv", [])
    xml_trace_json = read_json(output_dir / "xml_trace_coverage_obligations.json") if (output_dir / "xml_trace_coverage_obligations.json").exists() else {}
    xml_trace_summary = xml_trace_json.get("summary", {}) if isinstance(xml_trace_json, dict) else {}
    trace_machine_fail_rows = [
        row.get("coverage_id", "")
        for row in xml_trace_rows
        if row.get("machine_checkable") == "true" and row.get("coverage_status") == "FAIL"
    ]
    trace_integrity_manifest_ids = {
        row.get("manifest_id", "")
        for row in xml_trace_rows
        if row.get("coverage_name") == "runtime_trace_integrity"
        and row.get("coverage_status") == "PASS"
    }
    trace_review_rows = [
        row.get("coverage_id", "")
        for row in xml_trace_rows
        if row.get("coverage_status") == "REVIEW_REQUIRED"
    ]
    add_bool_check(
        checks,
        "XML_TRACE_COVERAGE_AUDIT",
        "claim_safety",
        len(xml_trace_rows) == summary_int(summary, "xml_trace_coverage_rows")
        and len(xml_trace_rows) == summary_int(xml_trace_summary, "row_count")
        and not trace_machine_fail_rows
        and ready_manifest_ids == trace_integrity_manifest_ids
        and summary_int(summary, "xml_trace_coverage_fail") == 0
        and summary_int(xml_trace_summary, "fail") == 0,
        "XML trace coverage obligations exist, have no machine-checkable FAIL rows, and preserve one runtime-integrity PASS row per proof-ready XML row",
        (
            f"rows={len(xml_trace_rows)}; summary_rows={summary_int(summary, 'xml_trace_coverage_rows')}; "
            f"json_rows={summary_int(xml_trace_summary, 'row_count')}; "
            f"machine_fail={len(trace_machine_fail_rows)}; ready={len(ready_manifest_ids)}; "
            f"runtime_integrity={len(trace_integrity_manifest_ids)}; "
            f"review_required={len(trace_review_rows)}; "
            f"json_fail={summary_int(xml_trace_summary, 'fail')}; "
            f"bad_preview={';'.join(trace_machine_fail_rows[:8])}"
        ),
        "xml_trace_coverage_obligations.csv; xml_trace_coverage_obligations.json; xml_proof_appendix.csv",
        "Fix runtime/provenance trace failures before manual review; keep missing strengthening traces as REVIEW_REQUIRED coverage gaps, not theorem failures.",
    )
    xml_gap_rows = csv_cache.get("xml_original_trace_gaps.csv", [])
    xml_gap_json = read_json(output_dir / "xml_original_trace_gaps.json") if (output_dir / "xml_original_trace_gaps.json").exists() else {}
    xml_gap_summary = xml_gap_json.get("summary", {}) if isinstance(xml_gap_json, dict) else {}
    coverage_by_id = {row.get("coverage_id", ""): row for row in xml_trace_rows}
    bad_gap_rows = []
    for row in xml_gap_rows:
        source = coverage_by_id.get(row.get("source_coverage_id", ""))
        if (
            row.get("gap_status") != "REVIEW_REQUIRED"
            or row.get("machine_checkable") != "false"
            or not source
            or source.get("coverage_name") != "original_decisive_trace_boundary"
            or source.get("coverage_status") != "REVIEW_REQUIRED"
        ):
            bad_gap_rows.append(row.get("gap_id", ""))
    add_bool_check(
        checks,
        "XML_ORIGINAL_TRACE_GAP_AUDIT",
        "claim_safety",
        len(xml_gap_rows) == summary_int(summary, "xml_original_trace_gap_rows")
        and len(xml_gap_rows) == summary_int(xml_gap_summary, "row_count")
        and summary_int(summary, "xml_original_trace_gap_fail") == 0
        and summary_int(xml_gap_summary, "fail") == 0
        and summary_int(summary, "xml_original_trace_gap_review_required") == len(xml_gap_rows)
        and not bad_gap_rows,
        "XML original trace gaps are isolated as non-machine-checkable REVIEW_REQUIRED rows backed by original_decisive_trace_boundary coverage gaps",
        (
            f"rows={len(xml_gap_rows)}; summary_rows={summary_int(summary, 'xml_original_trace_gap_rows')}; "
            f"json_rows={summary_int(xml_gap_summary, 'row_count')}; "
            f"summary_review_required={summary_int(summary, 'xml_original_trace_gap_review_required')}; "
            f"json_fail={summary_int(xml_gap_summary, 'fail')}; bad_preview={';'.join(bad_gap_rows[:8])}"
        ),
        "xml_original_trace_gaps.csv; xml_original_trace_gaps.json; xml_trace_coverage_obligations.csv",
        "Keep original-trace provenance gaps in human review; do not convert generated or INCONCLUSIVE traces into decisive original evidence.",
    )
    gap_ids = {row.get("gap_id", "") for row in xml_gap_rows}
    gap_queue_rows = [row for row in queue_rows if row.get("queue_id", "").startswith("XML_ORIGINAL_TRACE_GAP_")]
    gap_signoff_rows = [row for row in signoff_rows if row.get("queue_id", "").startswith("XML_ORIGINAL_TRACE_GAP_")]
    gap_queue_ids = {row.get("source_id", "") for row in gap_queue_rows}
    gap_signoff_ids = {row.get("source_id", "") for row in gap_signoff_rows}
    bad_gap_signoffs = [
        row.get("queue_id", "")
        for row in gap_signoff_rows
        if row.get("recommended_decision") != "APPROVE_WITH_CAVEAT"
        or "APPROVE_AS_CLAIMED" not in row.get("forbidden_decisions", "")
        or row.get("source_sheet") != "Original Trace Gaps"
    ]
    add_bool_check(
        checks,
        "XML_ORIGINAL_TRACE_GAP_SIGNOFF_AUDIT",
        "claim_safety",
        gap_ids == gap_queue_ids == gap_signoff_ids and not bad_gap_signoffs,
        "every XML original trace gap has a queue and signoff row that requires caveated review and forbids approve-as-claimed",
        (
            f"gap_ids={len(gap_ids)}; queue_ids={len(gap_queue_ids)}; signoff_ids={len(gap_signoff_ids)}; "
            f"bad_gap_signoffs={';'.join(bad_gap_signoffs[:8])}"
        ),
        "xml_original_trace_gaps.csv; human_review_queue.csv; review_signoff_template.csv",
        "Keep original-trace provenance gaps as explicit human signoff items with APPROVE_AS_CLAIMED forbidden.",
    )
    bad_gap_claims, bad_gap_claim_signoffs = collect_original_trace_gap_claim_violations(paper_claim_rows, signoff_rows, xml_gap_rows)
    add_bool_check(
        checks,
        "PAPER_CLAIM_ORIGINAL_TRACE_GAP_CAVEAT_AUDIT",
        "claim_safety",
        not bad_gap_claims and not bad_gap_claim_signoffs,
        "paper-facing claim rows linked to unresolved original-trace gaps expose provenance caveats and forbid approve-as-claimed signoff",
        (
            "bad_claims=" + ";".join(bad_gap_claims[:12])
            + "; bad_signoffs=" + ";".join(bad_gap_claim_signoffs[:12])
        ),
        "paper_claim_review.csv; xml_original_trace_gaps.csv; review_signoff_template.csv",
        "Do not let a paper-facing claim recommend approve-as-claimed while its original-input benchmark coverage remains unresolved.",
    )
    add_bool_check(
        checks,
        "PAPER_CLAIM_AUDIT_NO_FAIL",
        "claim_safety",
        count_rows(claim_audit, audit_status="FAIL") == 0 and summary_int(summary, "paper_claim_audit_fail") == 0,
        "paper claim audit has 0 FAIL rows",
        f"csv_fail={count_rows(claim_audit, audit_status='FAIL')}; summary_fail={summary_int(summary, 'paper_claim_audit_fail')}",
        "paper_claim_consistency_audit.csv",
        "Do not promote paper claims until claim-audit failures are resolved.",
    )

    baseline_rows = csv_cache.get("monitaal_baseline_results.csv", [])
    candidate_rows = csv_cache.get("translation_candidate_results.csv", [])
    embedded_rows = csv_cache.get("monitaal_embedded_benchmarks.csv", [])
    gear_original_audit_violations = collect_gear_original_input_response_audit_violations(
        output_dir,
        set(sheet_names),
        summary,
        baseline_rows,
        xml_gap_rows,
    )
    add_bool_check(
        checks,
        "GEAR_ORIGINAL_INPUT_RESPONSE_AUDIT",
        "claim_safety",
        not gear_original_audit_violations,
        "gear-control original repository input has six audited request-response rows, all baseline INCONCLUSIVE, no late/expired finite-prefix responses, two pending end-of-trace triggers, and explicit non-Boolean verdict boundaries",
        "violations=" + (";".join(gear_original_audit_violations[:20]) if gear_original_audit_violations else "none"),
        "gear_original_input_response_audit.csv; gear_original_input_response_audit.json; gear_original_input_response_audit.md; monitaal_baseline_results.csv; xml_original_trace_gaps.csv; paper_review_results.xlsx",
        "Do not close gear original-trace gaps as decisive evidence; use this audit to review the repository input and keep INCONCLUSIVE online semantics visible.",
    )
    non_gear_input_search_violations = collect_non_gear_original_input_search_audit_violations(
        output_dir,
        set(sheet_names),
        summary,
        xml_gap_rows,
        baseline_rows,
    )
    add_bool_check(
        checks,
        "NON_GEAR_ORIGINAL_INPUT_SEARCH_AUDIT",
        "claim_safety",
        not non_gear_input_search_violations,
        "non-gear XML original-trace gaps have explicit repository-input search evidence showing no original timed-word input, no original-like baseline rows, and only generated review inputs",
        "violations=" + (";".join(non_gear_input_search_violations[:20]) if non_gear_input_search_violations else "none"),
        "non_gear_original_input_search_audit.csv; non_gear_original_input_search_audit.json; non_gear_original_input_search_audit.md; xml_original_trace_gaps.csv; monitaal_baseline_results.csv; paper_review_results.xlsx",
        "Do not close non-gear original-trace gaps from generated traces; use this audit to review the absence of repository/original timed-word evidence.",
    )
    c_after10_provenance_violations = collect_c_after10_embedded_provenance_violations(
        output_dir,
        embedded_rows,
        baseline_rows,
        candidate_rows,
        xml_trace_rows,
        xml_gap_rows,
    )
    add_bool_check(
        checks,
        "EMBEDDED_C_AFTER10_PROVENANCE_AUDIT",
        "claim_safety",
        not c_after10_provenance_violations,
        "c_after_10 embedded unit-test timed-word evidence is tied to Monitor_test.cpp source assertions, exact input text, MoniTAal baseline, TAMonitor candidate, and XML trace coverage",
        "violations=" + (";".join(c_after10_provenance_violations[:12]) or "none"),
        "tool/MoniTAal/test/Monitor_test.cpp; monitaal_embedded_benchmarks.csv; monitaal_baseline_results.csv; translation_candidate_results.csv; xml_trace_coverage_obligations.csv",
        "Do not treat the c_after_10 original-trace gap as closed if the embedded unit-test source, transcribed input, or matching verdict rows drift.",
    )
    baseline_oracle_boundary_violations = collect_baseline_match_oracle_boundary_violations(candidate_rows)
    add_bool_check(
        checks,
        "BASELINE_MATCH_NOT_HAND_ORACLE_BOUNDARY",
        "benchmark_caveats",
        not baseline_oracle_boundary_violations,
        "MoniTAal XML baseline comparison rows are labeled as trace-level cross-tool evidence, not hand-oracle or automatic XML-to-MITL equivalence proof",
        "violations=" + (";".join(baseline_oracle_boundary_violations[:12]) or "none"),
        "translation_candidate_results.csv; manual_oracle_guide.csv",
        "Keep baseline-match wording separate from hand-oracle semantic derivations and human XML-to-MITL proof review.",
    )
    baseline_counts = Counter(row.get("status", "") for row in baseline_rows)
    stale_timeout_fact_claims = collect_stale_timeout_fact_claims(output_dir, baseline_counts.get("timeout", 0))
    add_bool_check(
        checks,
        "NO_STALE_TIMEOUT_FACT_CLAIMS",
        "benchmark_caveats",
        not stale_timeout_fact_claims,
        "when baseline timeout count is zero, generated artifacts do not claim current benchmark rows still time out",
        (
            f"baseline_timeouts={baseline_counts.get('timeout', 0)}; "
            f"stale_claims={';'.join(stale_timeout_fact_claims[:12]) or 'none'}"
        ),
        "monitaal_baseline_results.csv; generated review CSV/JSON/MD artifacts",
        "Regenerate wording from actual baseline rows; do not keep stale timeout caveats after the baseline terminates.",
    )
    add_bool_check(
        checks,
        "BASELINE_TIMEOUT_BOUNDARY",
        "benchmark_caveats",
        baseline_counts.get("timeout", 0) == summary_int(summary, "baseline_timeouts")
        and baseline_counts.get("skipped_no_input", 0) == summary_int(summary, "baseline_skipped_no_input")
        and summary_int(summary, "translation_candidate_baseline_mismatches") == 0,
        "baseline timeout/skipped counts match summary and candidate mismatches are 0",
        (
            f"timeouts={baseline_counts.get('timeout', 0)}; skipped={baseline_counts.get('skipped_no_input', 0)}; "
            f"candidate_mismatches={summary_int(summary, 'translation_candidate_baseline_mismatches')}"
        ),
        "monitaal_baseline_results.csv; translation_candidate_results.csv",
        "Keep timeout rows as caveats, not verified matches.",
    )
    generated_empty_rows = [
        row for row in baseline_rows
        if row.get("input_origin") == "generated_empty_no_original_input"
    ]
    bad_generated_empty_rows = [
        row for row in generated_empty_rows
        if row.get("status") != "ran"
        or not row.get("verdict")
        or "generated_monitaal_inputs" not in row.get("input_path", "")
        or not Path(row.get("input_path", "")).name.startswith("no_original_input_")
        or "baseline-only evidence" not in row.get("input_rationale", "")
        or "not as an original benchmark trace" not in row.get("input_rationale", "")
    ]
    add_bool_check(
        checks,
        "BASELINE_GENERATED_EMPTY_BOUNDARY",
        "benchmark_caveats",
        len(generated_empty_rows) == summary_int(summary, "baseline_generated_empty_no_original_input")
        and not bad_generated_empty_rows,
        "generated empty baseline probes are counted, labeled baseline-only, and have explicit MoniTAal verdicts",
        (
            f"csv_generated_empty={len(generated_empty_rows)}; "
            f"summary_generated_empty={summary_int(summary, 'baseline_generated_empty_no_original_input')}; "
            f"bad_rows={len(bad_generated_empty_rows)}"
        ),
        "monitaal_baseline_results.csv",
        "Do not cite generated empty probes as original benchmark inputs or XML-to-MITL equivalence proofs.",
    )
    bad_timeout_matches = [
        row.get("candidate_id", "")
        for row in candidate_rows
        if row.get("baseline_status") == "timeout"
        and row.get("baseline_comparison_status") in {
            "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT",
            "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT",
        }
    ]
    add_bool_check(
        checks,
        "TIMEOUTS_NOT_MATCHES",
        "benchmark_caveats",
        not bad_timeout_matches,
        "timeout candidate rows are not labeled as matches or mismatches",
        "bad_candidates=" + ";".join(bad_timeout_matches[:10]),
        "translation_candidate_results.csv",
        "Fix baseline comparison labeling before using benchmark claims.",
    )
    bad_inconclusive_claims, bad_inconclusive_signoffs = collect_inconclusive_claim_boundary_violations(paper_claim_rows, signoff_rows)
    add_bool_check(
        checks,
        "INCONCLUSIVE_CLAIM_CAVEAT_BOUNDARY",
        "claim_safety",
        not bad_inconclusive_claims and not bad_inconclusive_signoffs,
        "paper-facing rows with INCONCLUSIVE evidence expose a third-valued caveat and forbid approve-as-claimed signoff",
        (
            "bad_claims=" + ";".join(bad_inconclusive_claims[:12])
            + "; bad_signoffs=" + ";".join(bad_inconclusive_signoffs[:12])
        ),
        "paper_claim_review.csv; review_signoff_template.csv",
        "Make INCONCLUSIVE evidence explicit as a third-valued caveat before asking for human signoff.",
    )

    repro_rows = read_csv(output_dir / "reproducibility_manifest.csv") if (output_dir / "reproducibility_manifest.csv").exists() else []
    result_hash_keys = {row.get("key", "") for row in repro_rows if row.get("category") == "result_sha256"}
    missing_hashes = [name for name in HASHED_RESULT_FILES if name not in result_hash_keys]
    add_bool_check(
        checks,
        "REPRO_HASH_COVERAGE",
        "reproducibility",
        not missing_hashes and summary_int(summary, "reproducibility_result_hashes") >= len(HASHED_RESULT_FILES),
        "reproducibility manifest hashes review-critical generated artifacts",
        "missing=" + ";".join(missing_hashes),
        "reproducibility_manifest.csv",
        "Regenerate the manifest if review-critical hashes are missing.",
    )
    source_hash_keys = {row.get("key", "") for row in repro_rows if row.get("category") == "source_sha256"}
    missing_source_hashes = [name for name in HASHED_SOURCE_FILES if name not in source_hash_keys]
    add_bool_check(
        checks,
        "REPRO_SOURCE_HASH_COVERAGE",
        "reproducibility",
        not missing_source_hashes and summary_int(summary, "reproducibility_source_hashes") >= len(HASHED_SOURCE_FILES),
        "reproducibility manifest hashes all review-pipeline source scripts",
        "missing=" + ";".join(missing_source_hashes),
        "reproducibility_manifest.csv",
        "Regenerate the manifest if review-pipeline script hashes are missing.",
    )

    if timeout_rerun_dir:
        timeout_summary = timeout_rerun_dir / "baseline_timeout_rerun_summary.json"
        timeout_csv = timeout_rerun_dir / "baseline_timeout_rerun.csv"
        timeout_data = read_json(timeout_summary) if timeout_summary.exists() else {}
        timeout_rows = read_csv(timeout_csv) if timeout_csv.exists() else []
        add_bool_check(
            checks,
            "TIMEOUT_RERUN_PRESENT",
            "benchmark_caveats",
            timeout_summary.exists() and timeout_csv.exists(),
            "timeout rerun summary and CSV exist",
            f"summary_exists={timeout_summary.exists()}; csv_exists={timeout_csv.exists()}",
            str(timeout_rerun_dir),
            "Run rerun_baseline_timeouts.py for the matching full experiment.",
        )
        selected_timeout_rows = int(timeout_data.get("selected_timeout_rows", -1))
        rerun_completed = int(timeout_data.get("rerun_completed", -1))
        rerun_ran = int(timeout_data.get("rerun_ran", -1))
        rerun_timeouts = int(timeout_data.get("rerun_timeouts", -1))
        current_baseline_timeouts = summary_int(summary, "baseline_timeouts")
        csv_timeout_rows = count_rows(timeout_rows, status="timeout")
        csv_ran_rows = count_rows(timeout_rows, status="ran")
        add_bool_check(
            checks,
            "TIMEOUT_RERUN_MATCHES_CURRENT_TIMEOUTS",
            "benchmark_caveats",
            selected_timeout_rows == current_baseline_timeouts
            and rerun_completed == selected_timeout_rows
            and len(timeout_rows) == selected_timeout_rows
            and rerun_ran + rerun_timeouts == rerun_completed
            and csv_timeout_rows == rerun_timeouts
            and csv_ran_rows == rerun_ran,
            "timeout rerun selection and outcomes match the current baseline timeout rows",
            (
                f"baseline_timeouts={current_baseline_timeouts}; selected={selected_timeout_rows}; "
                f"completed={rerun_completed}; ran={rerun_ran}; timeouts={rerun_timeouts}; "
                f"csv_rows={len(timeout_rows)}; csv_ran={csv_ran_rows}; csv_timeout={csv_timeout_rows}"
            ),
            str(timeout_rerun_dir),
            "If timeout rows remain, keep them as caveats; if the count is zero, the empty rerun is the expected evidence.",
        )

    fail_count = count_rows(checks, status="FAIL")
    warn_count = count_rows(checks, status="WARN")
    return checks, fail_count, warn_count


def write_outputs(output_dir: Path, rows: list[dict[str, str]], fail_count: int, warn_count: int) -> None:
    csv_path = output_dir / "review_packet_verification.csv"
    fieldnames = ["check_id", "category", "status", "expected", "observed", "evidence_artifact", "reviewer_action"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    (output_dir / "review_packet_verification.json").write_text(
        json.dumps({
            "rows": rows,
            "check_rows": len(rows),
            "pass": count_rows(rows, status="PASS"),
            "warn": warn_count,
            "fail": fail_count,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Review Packet Verification",
        "",
        "This is an independent consistency check over an already generated TAMonitor paper-review result directory.",
        "It does not prove the mathematics and does not replace human signoff.",
        "",
        "## Counts",
        "",
        f"- PASS: {count_rows(rows, status='PASS')}",
        f"- WARN: {warn_count}",
        f"- FAIL: {fail_count}",
        "",
        "## Checks",
        "",
        "| check_id | status | category | observed | reviewer_action |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        observed = row["observed"].replace("|", "\\|")
        action = row["reviewer_action"].replace("|", "\\|")
        lines.append(f"| `{row['check_id']}` | `{row['status']}` | `{row['category']}` | {observed} | {action} |")
    lines.append("")
    (output_dir / "review_packet_verification.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a generated TAMonitor paper-review result packet.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated paper experiment output directory.")
    parser.add_argument("--timeout-rerun", type=Path, default=None, help="Matching baseline timeout rerun directory.")
    parser.add_argument("--signoff-mode", choices=["pre-review", "complete"], default="pre-review", help="Expected signoff state for review_signoff_template.csv and review_signoff_validation.json.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    timeout_rerun = args.timeout_rerun.resolve() if args.timeout_rerun else None
    rows, fail_count, warn_count = verify_packet(output_dir, timeout_rerun, args.signoff_mode)
    write_outputs(output_dir, rows, fail_count, warn_count)
    print(json.dumps({
        "output_dir": str(output_dir),
        "timeout_rerun": str(timeout_rerun) if timeout_rerun else "",
        "check_rows": len(rows),
        "pass": count_rows(rows, status="PASS"),
        "warn": warn_count,
        "fail": fail_count,
        "csv": str(output_dir / "review_packet_verification.csv"),
        "json": str(output_dir / "review_packet_verification.json"),
        "md": str(output_dir / "review_packet_verification.md"),
    }, indent=2, ensure_ascii=False))
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
