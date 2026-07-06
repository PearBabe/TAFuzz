#!/usr/bin/env python3
"""Compare two TAMonitor paper-review result packets.

The comparison is intentionally conservative: semantic/runtime/benchmark
metrics must stay stable, while explicitly allowed review-packet growth such as
adding a new guide sheet can be acknowledged as expected.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[3]


STABLE_EXPERIMENT_KEYS = [
    "semantic_cases",
    "semantic_ran",
    "semantic_pass",
    "semantic_fail",
    "semantic_correctness_verified",
    "semantic_finite_verified",
    "semantic_infinite_verified",
    "semantic_correctness_needs_manual_oracle",
    "semantic_correctness_not_verified_resource_limit",
    "semantic_correctness_not_verified_timeout",
    "semantic_correctness_not_a_verdict_check",
    "semantic_correctness_build_timeout_not_a_verdict_check",
    "semantic_prefix_oracle_rows",
    "semantic_prefix_oracle_match",
    "semantic_prefix_oracle_mismatch",
    "semantic_prefix_oracle_missing_observed_step",
    "semantic_prefix_final_verdict_only",
    "semantic_prefix_carry_forward_steps",
    "semantic_oracle_derivation_rows",
    "semantic_oracle_hand_verified",
    "semantic_oracle_construction_stats_only",
    "semantic_oracle_review_required",
    "semantic_oracle_prefix_mismatches",
    "mitl_correctness_audit_rows",
    "semantic_review",
    "semantic_build_stats",
    "semantic_build_timeout",
    "semantic_resource_limit",
    "semantic_timeout",
    "semantic_error",
    "semantic_review_unsupported",
    "semantic_exclusion_rows",
    "internal_count_forms_excluded",
    "syntax_coverage_rows",
    "syntax_coverage_verified_runtime",
    "syntax_coverage_finite_and_infinite",
    "syntax_coverage_build_stats_only",
    "syntax_coverage_excluded_internal",
    "syntax_coverage_missing",
    "formula_input_policy_rows",
    "formula_input_policy_pass",
    "formula_input_policy_fail",
    "formula_input_policy_assert_like_failures",
    "cli_contract_rows",
    "cli_contract_pass",
    "cli_contract_fail",
    "cli_contract_controlled_errors",
    "review_guide_rows",
    "review_guide_p0",
    "review_guide_p1",
    "goal_completion_rows",
    "goal_completion_pass",
    "goal_completion_pass_with_caveat",
    "goal_completion_review_required",
    "goal_completion_v1_deferred",
    "goal_completion_fail",
    "human_review_queue_rows",
    "human_review_queue_human_required",
    "human_review_queue_p0",
    "human_review_queue_p1",
    "human_review_queue_p2",
    "human_review_queue_p3",
    "human_review_queue_fail",
    "review_signoff_template_rows",
    "review_signoff_template_blank_decisions",
    "review_signoff_template_p0",
    "review_signoff_template_p1",
    "review_signoff_template_p2",
    "manual_review_rows",
    "manual_review_pass",
    "manual_review_pass_with_caveat",
    "manual_review_review_required",
    "manual_review_v1_deferred",
    "manual_review_fail",
    "manual_review_human_required",
    "xml_templates",
    "xml_transition_detail_rows",
    "xml_pairs",
    "translation_candidates",
    "benchmark_manifest_rows",
    "benchmark_manifest_strong_trace_level",
    "benchmark_manifest_single_trace_level",
    "benchmark_manifest_approximate_trace_only",
    "benchmark_manifest_not_promoted",
    "xml_edge_guard_proof_rows",
    "xml_edge_guard_proof_ready",
    "xml_edge_guard_review_required",
    "xml_edge_guard_not_ready",
    "xml_edge_guard_incomplete",
    "xml_proof_appendix_rows",
    "xml_proof_appendix_ready",
    "xml_proof_appendix_excluded",
    "xml_proof_obligation_rows",
    "xml_proof_obligation_pass",
    "xml_proof_obligation_review_required",
    "xml_proof_obligation_fail",
    "xml_trace_coverage_rows",
    "xml_trace_coverage_pass",
    "xml_trace_coverage_review_required",
    "xml_trace_coverage_fail",
    "xml_original_trace_gap_rows",
    "xml_original_trace_gap_review_required",
    "xml_original_trace_gap_fail",
    "paper_claim_review_rows",
    "paper_claim_body_pattern_ready",
    "paper_claim_appendix_timeout_caveat",
    "paper_claim_excluded",
    "paper_claim_audit_rows",
    "paper_claim_audit_pass",
    "paper_claim_audit_warn",
    "paper_claim_audit_fail",
    "requirements_audit_rows",
    "requirements_audit_pass",
    "requirements_audit_pass_with_caveat",
    "requirements_audit_v1_deferred",
    "requirements_audit_fail",
    "translation_candidate_runs",
    "translation_candidate_success",
    "translation_candidate_timeouts",
    "translation_candidate_baseline_matches",
    "translation_candidate_baseline_mismatches",
    "translation_candidate_baseline_not_verified",
    "candidate_prefix_observation_rows",
    "candidate_step_audit_rows",
    "candidate_step_all_trace_steps_recorded",
    "candidate_step_missing_or_incomplete",
    "candidate_prefix_carry_forward_steps",
    "baseline_runs",
    "baseline_timeouts",
    "baseline_skipped_no_input",
    "baseline_generated_empty_no_original_input",
    "embedded_benchmark_records",
    "workbook_status",
]


EXPECTED_NEW_MANUAL_ORACLE_KEYS = {
    "manual_oracle_guide_rows": 8,
    "manual_oracle_guide_p0": 5,
    "manual_oracle_guide_p1": 3,
}


EXPECTED_REPRO_DELTA = {
    "reproducibility_manifest_rows": 3,
    "reproducibility_result_hashes": 3,
    "reproducibility_source_hashes": 0,
    "reproducibility_git_rows": 0,
}


EXPECTED_VERIFIER_DELTA = {
    "check_rows": 5,
    "pass": 5,
    "warn": 0,
    "fail": 0,
}


EXPECTED_SIGNOFF_VERIFIER_DELTA = {
    "check_rows": 6,
    "pass": 6,
    "warn": 0,
    "fail": 0,
}

EXPECTED_QUEUE_SOURCE_VERIFIER_DELTA = {
    "check_rows": 2,
    "pass": 2,
    "warn": 0,
    "fail": 0,
}

EXPECTED_QUEUE_EVIDENCE_VERIFIER_DELTA = {
    "check_rows": 2,
    "pass": 2,
    "warn": 0,
    "fail": 0,
}

EXPECTED_BLOCKER_VERIFIER_DELTA = {
    "check_rows": 4,
    "pass": 4,
    "warn": 0,
    "fail": 0,
}

EXPECTED_PIPELINE_SOURCE_HASH_REPRO_DELTA = {
    "reproducibility_manifest_rows": 7,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 7,
    "reproducibility_git_rows": 0,
}

EXPECTED_FORMULA_CATALOG_REPRO_DELTA = {
    "reproducibility_manifest_rows": 1,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 1,
    "reproducibility_git_rows": 0,
}

EXPECTED_FORMULA_CATALOG_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_PIPELINE_SOURCE_HASH_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_TIMEOUT_WORKBOOK_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_MONITAAL_EOF_FIX_DELTAS = {
    "baseline_runs": 8,
    "baseline_timeouts": -8,
    "translation_candidate_baseline_matches": 7,
    "translation_candidate_baseline_not_verified": -7,
    "paper_claim_body_pattern_ready": 6,
    "paper_claim_appendix_timeout_caveat": -6,
    "benchmark_manifest_approximate_trace_only": 1,
    "goal_completion_pass": 1,
    "goal_completion_pass_with_caveat": -1,
    "human_review_queue_rows": -7,
    "human_review_queue_human_required": -1,
    "human_review_queue_p0": 6,
    "human_review_queue_p1": -13,
    "review_signoff_template_rows": -7,
    "review_signoff_template_blank_decisions": -7,
    "review_signoff_template_p0": 6,
    "review_signoff_template_p1": -13,
    "manual_review_pass": 2,
    "manual_review_pass_with_caveat": -2,
}

EXPECTED_MONITAAL_EOF_FIX_REPRO_DELTA = {
    "reproducibility_manifest_rows": 1,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 1,
    "reproducibility_git_rows": 0,
}

EXPECTED_GENERATED_EMPTY_INPUT_DELTAS = {
    "baseline_runs": 3,
    "baseline_skipped_no_input": -3,
    "baseline_generated_empty_no_original_input": 3,
    "embedded_benchmark_records": 3,
}

EXPECTED_GENERATED_EMPTY_INPUT_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_GENERATED_EMPTY_INPUT_CSV_ROW_DELTAS: dict[str, int] = {}

EXPECTED_HARDCODED_BENCHMARK_REPRO_DELTA = {
    "reproducibility_manifest_rows": 2,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 2,
    "reproducibility_git_rows": 0,
}

EXPECTED_HARDCODED_BENCHMARK_VERIFIER_DELTA = {
    "check_rows": 4,
    "pass": 4,
    "warn": 0,
    "fail": 0,
}

EXPECTED_FINITE_SYNTAX_ORACLE_DELTAS = {
    "semantic_cases": 17,
    "semantic_ran": 17,
    "semantic_pass": 17,
    "semantic_correctness_verified": 17,
    "semantic_finite_verified": 17,
    "semantic_prefix_oracle_rows": 31,
    "semantic_prefix_oracle_match": 31,
    "semantic_prefix_carry_forward_steps": 6,
    "semantic_oracle_derivation_rows": 17,
    "semantic_oracle_hand_verified": 17,
    "syntax_coverage_finite_and_infinite": 19,
}

EXPECTED_FINITE_SYNTAX_ORACLE_CSV_ROW_DELTAS = {
    "semantic_regression_results.csv": 17,
    "semantic_prefix_oracle_review.csv": 31,
    "semantic_oracle_derivations.csv": 17,
    "mitl_correctness_audit.csv": 17,
}

EXPECTED_THREE_VALUED_GUARD_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_SIGNOFF_POLICY_VALIDATION_DELTA = {
    "validation_rows": 1,
    "pass": 1,
    "fail": 0,
    "policy_mismatch_rows": 0,
    "forbidden_decision_rows": 0,
}

EXPECTED_SIGNOFF_EVIDENCE_RESOLUTION_DELTA = {
    "validation_rows": 1,
    "pass": 1,
    "fail": 0,
    "policy_mismatch_rows": 0,
    "forbidden_decision_rows": 0,
    "unresolved_evidence_tokens": 0,
}

EXPECTED_SIGNOFF_SOURCE_RESOLUTION_DELTA = {
    "validation_rows": 2,
    "pass": 2,
    "fail": 0,
    "policy_mismatch_rows": 0,
    "forbidden_decision_rows": 0,
    "unresolved_evidence_tokens": 0,
    "unresolved_source_sheet_tokens": 0,
    "unresolved_source_rows": 0,
}

EXPECTED_QUEUE_SOURCE_RESOLUTION_DELTA = {
    "validation_rows": 2,
    "pass": 2,
    "fail": 0,
    "policy_mismatch_rows": 0,
    "forbidden_decision_rows": 0,
    "unresolved_evidence_tokens": 0,
    "unresolved_source_sheet_tokens": 0,
    "unresolved_source_rows": 0,
    "unresolved_queue_source_sheet_tokens": 0,
    "unresolved_queue_source_rows": 0,
}

EXPECTED_QUEUE_EVIDENCE_RESOLUTION_DELTA = {
    "validation_rows": 2,
    "pass": 2,
    "fail": 0,
    "policy_mismatch_rows": 0,
    "forbidden_decision_rows": 0,
    "unresolved_evidence_tokens": 0,
    "missing_queue_evidence_rows": 0,
    "unresolved_queue_evidence_tokens": 0,
    "unresolved_source_sheet_tokens": 0,
    "unresolved_source_rows": 0,
    "unresolved_queue_source_sheet_tokens": 0,
    "unresolved_queue_source_rows": 0,
}


EXPECTED_SIGNOFF_IMPORT_EXPERIMENT_DELTAS = {
    "review_guide_rows": 1,
    "review_guide_p0": 1,
}

EXPECTED_SIGNOFF_IMPORT_REPRO_DELTA = {
    "reproducibility_manifest_rows": 1,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 1,
    "reproducibility_git_rows": 0,
}

EXPECTED_SIGNOFF_ROUNDTRIP_REPRO_DELTA = {
    "reproducibility_manifest_rows": 1,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 1,
    "reproducibility_git_rows": 0,
}

EXPECTED_SIGNOFF_ROUNDTRIP_VERIFIER_DELTA = {
    "check_rows": 5,
    "pass": 5,
    "warn": 0,
    "fail": 0,
}

EXPECTED_SIGNOFF_EVIDENCE_BUNDLE_REPRO_DELTA = {
    "reproducibility_manifest_rows": 1,
    "reproducibility_result_hashes": 0,
    "reproducibility_source_hashes": 1,
    "reproducibility_git_rows": 0,
}

EXPECTED_SIGNOFF_EVIDENCE_BUNDLE_VERIFIER_DELTA = {
    "check_rows": 5,
    "pass": 5,
    "warn": 0,
    "fail": 0,
}

EXPECTED_EVIDENCE_CONSISTENCY_VERIFIER_DELTA = {
    "check_rows": 2,
    "pass": 2,
    "warn": 0,
    "fail": 0,
}

EXPECTED_XML_PROOF_OBLIGATION_DELTAS = {
    "xml_proof_obligation_rows": 143,
    "xml_proof_obligation_pass": 125,
    "xml_proof_obligation_review_required": 18,
    "xml_proof_obligation_fail": 0,
}

EXPECTED_XML_PROOF_OBLIGATION_REPRO_DELTA = {
    "reproducibility_manifest_rows": 3,
    "reproducibility_result_hashes": 3,
    "reproducibility_source_hashes": 0,
    "reproducibility_git_rows": 0,
}

EXPECTED_XML_PROOF_OBLIGATION_VERIFIER_DELTA = {
    "check_rows": 5,
    "pass": 5,
    "warn": 0,
    "fail": 0,
}

EXPECTED_XML_TRACE_COVERAGE_DELTAS = {
    "xml_trace_coverage_rows": 120,
    "xml_trace_coverage_pass": 84,
    "xml_trace_coverage_review_required": 36,
    "xml_trace_coverage_fail": 0,
}

EXPECTED_XML_TRACE_COVERAGE_REPRO_DELTA = {
    "reproducibility_manifest_rows": 3,
    "reproducibility_result_hashes": 3,
    "reproducibility_source_hashes": 0,
    "reproducibility_git_rows": 0,
}

EXPECTED_XML_TRACE_COVERAGE_VERIFIER_DELTA = {
    "check_rows": 5,
    "pass": 5,
    "warn": 0,
    "fail": 0,
}

EXPECTED_XML_BOUNDARY_TRACE_DELTAS = {
    "xml_trace_coverage_rows": 0,
    "xml_trace_coverage_pass": 3,
    "xml_trace_coverage_review_required": -3,
    "xml_trace_coverage_fail": 0,
    "translation_candidate_runs": 11,
    "translation_candidate_success": 11,
    "translation_candidate_timeouts": 0,
    "translation_candidate_baseline_matches": 11,
    "translation_candidate_baseline_mismatches": 0,
    "translation_candidate_baseline_not_verified": 0,
    "candidate_prefix_observation_rows": 22,
    "candidate_step_audit_rows": 11,
    "candidate_step_all_trace_steps_recorded": 11,
    "candidate_step_missing_or_incomplete": 0,
    "candidate_prefix_carry_forward_steps": 0,
    "baseline_runs": 11,
    "baseline_timeouts": 0,
    "baseline_skipped_no_input": 0,
    "baseline_generated_empty_no_original_input": 0,
    "embedded_benchmark_records": 11,
}

EXPECTED_XML_BOUNDARY_TRACE_CSV_ROW_DELTAS = {
    "mitl_correctness_audit.csv": 11,
    "translation_candidate_results.csv": 11,
    "candidate_step_audit.csv": 11,
    "monitaal_baseline_results.csv": 11,
}

EXPECTED_XML_THREE_VALUED_COVERAGE_DELTAS = {
    "xml_trace_coverage_rows": -6,
    "xml_trace_coverage_pass": 18,
    "xml_trace_coverage_review_required": -24,
    "xml_trace_coverage_fail": 0,
    "translation_candidate_runs": 8,
    "translation_candidate_success": 8,
    "translation_candidate_timeouts": 0,
    "translation_candidate_baseline_matches": 8,
    "translation_candidate_baseline_mismatches": 0,
    "translation_candidate_baseline_not_verified": 0,
    "candidate_prefix_observation_rows": 27,
    "candidate_step_audit_rows": 8,
    "candidate_step_all_trace_steps_recorded": 8,
    "candidate_step_missing_or_incomplete": 0,
    "candidate_prefix_carry_forward_steps": 0,
    "baseline_runs": 8,
    "baseline_timeouts": 0,
    "baseline_skipped_no_input": 0,
    "baseline_generated_empty_no_original_input": 0,
    "embedded_benchmark_records": 8,
}

EXPECTED_XML_THREE_VALUED_COVERAGE_CSV_ROW_DELTAS = {
    "mitl_correctness_audit.csv": 8,
    "translation_candidate_results.csv": 8,
    "candidate_step_audit.csv": 8,
    "monitaal_baseline_results.csv": 8,
}

EXPECTED_XML_ORIGINAL_TRACE_GAP_DELTAS = {
    "xml_original_trace_gap_rows": 9,
    "xml_original_trace_gap_review_required": 9,
    "xml_original_trace_gap_fail": 0,
}

EXPECTED_XML_ORIGINAL_TRACE_GAP_REPRO_DELTA = {
    "reproducibility_manifest_rows": 3,
    "reproducibility_result_hashes": 3,
    "reproducibility_source_hashes": 0,
    "reproducibility_git_rows": 0,
}

EXPECTED_XML_ORIGINAL_TRACE_GAP_VERIFIER_DELTA = {
    "check_rows": 5,
    "pass": 5,
    "warn": 0,
    "fail": 0,
}

EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_DELTAS = {
    "review_guide_rows": 1,
    "review_guide_p0": 1,
    "review_guide_p1": 0,
    "manual_review_rows": 1,
    "manual_review_pass": 0,
    "manual_review_pass_with_caveat": 0,
    "manual_review_review_required": 1,
    "manual_review_v1_deferred": 0,
    "manual_review_fail": 0,
    "manual_review_human_required": 1,
    "human_review_queue_rows": 10,
    "human_review_queue_human_required": 10,
    "human_review_queue_p0": 10,
    "human_review_queue_p1": 0,
    "human_review_queue_p2": 0,
    "human_review_queue_p3": 0,
    "human_review_queue_fail": 0,
    "review_signoff_template_rows": 10,
    "review_signoff_template_blank_decisions": 10,
    "review_signoff_template_p0": 10,
    "review_signoff_template_p1": 0,
    "review_signoff_template_p2": 0,
}

EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_PAPER_CLAIM_GAP_CAVEAT_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_EMBEDDED_C_AFTER10_DELTAS = {
    "human_review_queue_rows": -1,
    "human_review_queue_human_required": -1,
    "human_review_queue_p0": -1,
    "human_review_queue_p1": 0,
    "human_review_queue_p2": 0,
    "human_review_queue_p3": 0,
    "human_review_queue_fail": 0,
    "review_signoff_template_rows": -1,
    "review_signoff_template_blank_decisions": -1,
    "review_signoff_template_p0": -1,
    "review_signoff_template_p1": 0,
    "review_signoff_template_p2": 0,
    "xml_proof_obligation_pass": 1,
    "xml_proof_obligation_review_required": -1,
    "xml_proof_obligation_fail": 0,
    "xml_trace_coverage_pass": 1,
    "xml_trace_coverage_review_required": -1,
    "xml_trace_coverage_fail": 0,
    "xml_original_trace_gap_rows": -1,
    "xml_original_trace_gap_review_required": -1,
    "xml_original_trace_gap_fail": 0,
    "translation_candidate_runs": 1,
    "translation_candidate_success": 1,
    "translation_candidate_timeouts": 0,
    "translation_candidate_baseline_matches": 1,
    "translation_candidate_baseline_mismatches": 0,
    "translation_candidate_baseline_not_verified": 0,
    "candidate_prefix_observation_rows": 4,
    "candidate_step_audit_rows": 1,
    "candidate_step_all_trace_steps_recorded": 1,
    "candidate_step_missing_or_incomplete": 0,
    "candidate_prefix_carry_forward_steps": 1,
    "baseline_runs": 1,
    "baseline_timeouts": 0,
    "baseline_skipped_no_input": 0,
    "baseline_generated_empty_no_original_input": 0,
    "embedded_benchmark_records": 1,
}

EXPECTED_EMBEDDED_C_AFTER10_CSV_ROW_DELTAS = {
    "mitl_correctness_audit.csv": 1,
    "translation_candidate_results.csv": 1,
    "candidate_step_audit.csv": 1,
    "monitaal_baseline_results.csv": 1,
}

EXPECTED_EMBEDDED_C_AFTER10_SIGNOFF_VALIDATION_DELTA = {
    "signoff_rows": -1,
    "blank_decisions": -1,
    "nonblank_decisions": 0,
}

EXPECTED_EMBEDDED_C_AFTER10_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_EMBEDDED_C_AFTER10_PROVENANCE_VERIFIER_DELTA = {
    "check_rows": 3,
    "pass": 3,
    "warn": 0,
    "fail": 0,
}

EXPECTED_BASELINE_MATCH_ORACLE_BOUNDARY_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_WORKBOOK_PREVIEW_MANIFEST_VERIFIER_DELTA = {
    "check_rows": 3,
    "pass": 3,
    "warn": 0,
    "fail": 0,
}

EXPECTED_WORKBOOK_SOURCE_COVERAGE_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_WORKBOOK_XLSX_TABLE_SHAPE_VERIFIER_DELTA = {
    "check_rows": 1,
    "pass": 1,
    "warn": 0,
    "fail": 0,
}

EXPECTED_CORRECTNESS_AUDIT_ROWCOUNT_VERIFIER_DELTA = {
    "check_rows": 2,
    "pass": 2,
    "warn": 0,
    "fail": 0,
}

EXPECTED_WORKBOOK_REBUILD_SUMMARY_VERIFIER_DELTA = {
    "check_rows": 4,
    "pass": 4,
    "warn": 0,
    "fail": 0,
}

EXPECTED_CANDIDATE_PREFIX_OBSERVATIONS_VERIFIER_DELTA = {
    "check_rows": 3,
    "pass": 3,
    "warn": 0,
    "fail": 0,
}

EXPECTED_MONITAAL_XML_STRUCTURAL_LEDGER_VERIFIER_DELTA = {
    "check_rows": 7,
    "pass": 7,
    "warn": 0,
    "fail": 0,
}

EXPECTED_MANUAL_REVIEW_ENTRYPOINT_REFERENCE_VERIFIER_DELTA = {
    "check_rows": 6,
    "pass": 6,
    "warn": 0,
    "fail": 0,
}

EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_VALIDATION_DELTA = {
    "signoff_rows": 10,
    "blank_decisions": 10,
    "nonblank_decisions": 0,
}


EXPECTED_MANUAL_ORACLE_INDEPENDENCE_KEYS = {
    "manual_oracle_guide_rows": (8, 9),
    "manual_oracle_guide_p0": (5, 6),
    "manual_oracle_guide_p1": (3, 3),
}


EXPECTED_MANUAL_ORACLE_BASELINE_BOUNDARY_KEYS = {
    "manual_oracle_guide_rows": (9, 10),
    "manual_oracle_guide_p0": (6, 7),
    "manual_oracle_guide_p1": (3, 3),
}


EXPECTED_CLI_TRACE_HEADER_CONTRACT_DELTAS = {
    "cli_contract_rows": 1,
    "cli_contract_pass": 1,
    "cli_contract_fail": 0,
    "cli_contract_controlled_errors": 0,
}


EXPECTED_CLI_TRACE_HEADER_CONTRACT_CSV_ROW_DELTAS = {
    "cli_contract_audit.csv": 1,
}


CSV_FILES_TO_COMPARE = [
    "semantic_regression_results.csv",
    "semantic_prefix_oracle_review.csv",
    "semantic_oracle_derivations.csv",
    "mitl_correctness_audit.csv",
    "mightyppl_syntax_coverage_audit.csv",
    "formula_input_policy_audit.csv",
    "cli_contract_audit.csv",
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
    "review_guide.csv",
    "goal_completion_audit.csv",
    "manual_review_checklist.csv",
    "paper_claim_consistency_audit.csv",
    "requirements_traceability_audit.csv",
]


STABLE_SIGNOFF_KEYS = [
    "mode",
    "completion_state",
    "validation_rows",
    "pass",
    "fail",
    "signoff_rows",
    "blank_decisions",
    "nonblank_decisions",
    "invalid_decisions",
    "policy_mismatch_rows",
    "forbidden_decision_rows",
    "unresolved_evidence_tokens",
    "missing_queue_evidence_rows",
    "unresolved_queue_evidence_tokens",
    "unresolved_source_sheet_tokens",
    "unresolved_source_rows",
    "unresolved_queue_source_sheet_tokens",
    "unresolved_queue_source_rows",
]


STABLE_CSV_IGNORED_COLUMNS = {
    "elapsed_ms",
}


BENCHMARK_BLOCKER_REASON_XMLS = {
    "never_b.xml",
    "time-must-pass.xml",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return {}
    return read_json(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def csv_path_replacements(baseline_dir: Path, candidate_dir: Path) -> tuple[tuple[str, str], ...]:
    baseline_resolved = baseline_dir.resolve()
    candidate_resolved = candidate_dir.resolve()
    return (
        (str(baseline_resolved), "<RESULT_DIR>"),
        (str(candidate_resolved), "<RESULT_DIR>"),
        (baseline_resolved.as_posix(), "<RESULT_DIR>"),
        (candidate_resolved.as_posix(), "<RESULT_DIR>"),
        (baseline_dir.name, "<RESULT_DIR>"),
        (candidate_dir.name, "<RESULT_DIR>"),
    )


def normalize_csv_cell(value: str, replacements: tuple[tuple[str, str], ...]) -> str:
    normalized = value or ""
    for source, target in replacements:
        normalized = normalized.replace(source, target)
    return normalized


def normalized_csv_rows(
    rows: list[dict[str, str]],
    replacements: tuple[tuple[str, str], ...],
) -> list[dict[str, str]]:
    return [
        {
            key: normalize_csv_cell(value, replacements)
            for key, value in row.items()
            if key not in STABLE_CSV_IGNORED_COLUMNS
        }
        for row in rows
    ]


def normalized_csv_rows_for_profile(
    file_name: str,
    rows: list[dict[str, str]],
    baseline_dir: Path,
    candidate_dir: Path,
    profile: str,
    replacements: tuple[tuple[str, str], ...],
) -> list[dict[str, str]]:
    normalized = normalized_csv_rows(rows, replacements)
    if profile == "benchmark-blocker-diagnostics-added" and file_name == "benchmark_manifest.csv":
        for row in normalized:
            if row.get("xml_file") in BENCHMARK_BLOCKER_REASON_XMLS:
                row["translation_reason"] = "<explicit_blocker_reason_refined>"
    return normalized


def rows_hash(rows: list[dict[str, str]]) -> str:
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def first_row_diff(
    baseline_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> str:
    for index, (baseline_row, candidate_row) in enumerate(zip(baseline_rows, candidate_rows)):
        if baseline_row != candidate_row:
            differing_keys = sorted(
                key
                for key in set(baseline_row) | set(candidate_row)
                if baseline_row.get(key) != candidate_row.get(key)
            )
            preview = "; ".join(
                f"{key}: {baseline_row.get(key, '')!r} != {candidate_row.get(key, '')!r}"
                for key in differing_keys[:5]
            )
            return f"first_diff_row={index}; keys={','.join(differing_keys[:12])}; {preview}"
    if len(baseline_rows) != len(candidate_rows):
        return f"row_count_diff={len(baseline_rows)}!={len(candidate_rows)}"
    return ""


def int_value(data: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(data.get(key, default))
    except (TypeError, ValueError):
        return default


def workbook_sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("xl/workbook.xml"))
    return [
        element.attrib.get("name", "")
        for element in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
        if element.attrib.get("name")
    ]


def add_row(
    rows: list[dict[str, str]],
    check_id: str,
    category: str,
    status: str,
    baseline_value: Any,
    candidate_value: Any,
    expected: str,
    evidence: str,
    notes: str = "",
) -> None:
    rows.append({
        "check_id": check_id,
        "category": category,
        "status": status,
        "baseline_value": normalize(baseline_value),
        "candidate_value": normalize(candidate_value),
        "expected": expected,
        "evidence": evidence,
        "notes": notes,
    })


def compare_csv_files(
    baseline_dir: Path,
    candidate_dir: Path,
    rows: list[dict[str, str]],
    profile: str,
) -> None:
    replacements = csv_path_replacements(baseline_dir, candidate_dir)
    for file_name in CSV_FILES_TO_COMPARE:
        baseline_rows = read_csv(baseline_dir / file_name)
        candidate_rows = read_csv(candidate_dir / file_name)
        expected_row_delta = 0
        if profile == "generated-empty-inputs-added":
            expected_row_delta = EXPECTED_GENERATED_EMPTY_INPUT_CSV_ROW_DELTAS.get(file_name, 0)
        elif profile in {"finite-syntax-oracles-added", "finite-syntax-oracles-and-three-valued-guard-added"}:
            expected_row_delta = EXPECTED_FINITE_SYNTAX_ORACLE_CSV_ROW_DELTAS.get(file_name, 0)
        elif profile == "xml-boundary-traces-added":
            expected_row_delta = EXPECTED_XML_BOUNDARY_TRACE_CSV_ROW_DELTAS.get(file_name, 0)
        elif profile == "xml-three-valued-coverage-fixed":
            expected_row_delta = EXPECTED_XML_THREE_VALUED_COVERAGE_CSV_ROW_DELTAS.get(file_name, 0)
        elif profile == "embedded-c-after10-original-trace-added":
            expected_row_delta = EXPECTED_EMBEDDED_C_AFTER10_CSV_ROW_DELTAS.get(file_name, 0)
        elif profile == "cli-trace-header-contract-added":
            expected_row_delta = EXPECTED_CLI_TRACE_HEADER_CONTRACT_CSV_ROW_DELTAS.get(file_name, 0)
        add_row(
            rows,
            f"CSV_ROW_COUNT_{file_name.replace('.', '_')}",
            "expected_csv_row_count_growth" if expected_row_delta else "stable_csv_row_count",
            "PASS" if len(candidate_rows) - len(baseline_rows) == expected_row_delta else "FAIL",
            len(baseline_rows),
            len(candidate_rows),
            f"candidate-baseline={expected_row_delta}",
            file_name,
        )
        if profile in {
            "stable",
            "verifier-signoff-added",
            "manual-oracle-independence-added",
            "benchmark-blocker-diagnostics-added",
            "workbook-source-coverage-guard-added",
            "workbook-xlsx-table-shape-guard-added",
            "correctness-audit-rowcount-guard-added",
            "monitaal-xml-structural-ledger-guard-added",
        }:
            normalized_baseline = normalized_csv_rows_for_profile(file_name, baseline_rows, baseline_dir, candidate_dir, profile, replacements)
            normalized_candidate = normalized_csv_rows_for_profile(file_name, candidate_rows, baseline_dir, candidate_dir, profile, replacements)
            baseline_hash = rows_hash(normalized_baseline)
            candidate_hash = rows_hash(normalized_candidate)
            add_row(
                rows,
                f"STABLE_CSV_CONTENT_{file_name.replace('.', '_')}",
                "stable_csv_content",
                "PASS" if normalized_baseline == normalized_candidate else "FAIL",
                baseline_hash,
                candidate_hash,
                "normalized CSV content remains stable; ignored columns=elapsed_ms",
                file_name,
                first_row_diff(normalized_baseline, normalized_candidate),
            )


def compare_packets(
    baseline_dir: Path,
    candidate_dir: Path,
    profile: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows: list[dict[str, str]] = []
    baseline_pipeline = read_json(baseline_dir / "pipeline_summary.json")
    candidate_pipeline = read_json(candidate_dir / "pipeline_summary.json")
    baseline_summary = read_json(baseline_dir / "experiment_summary.json")
    candidate_summary = read_json(candidate_dir / "experiment_summary.json")
    baseline_verifier = read_json(baseline_dir / "review_packet_verification.json")
    candidate_verifier = read_json(candidate_dir / "review_packet_verification.json")
    baseline_signoff = read_json_if_exists(baseline_dir / "review_signoff_validation.json")
    candidate_signoff = read_json_if_exists(candidate_dir / "review_signoff_validation.json")
    baseline_signoff_summary = baseline_signoff.get("summary", {}) if isinstance(baseline_signoff, dict) else {}
    candidate_signoff_summary = candidate_signoff.get("summary", {}) if isinstance(candidate_signoff, dict) else {}

    for label, data in [("baseline", baseline_pipeline), ("candidate", candidate_pipeline)]:
        add_row(
            rows,
            f"PIPELINE_STATUS_{label.upper()}",
            "pipeline",
            "PASS" if data.get("pipeline_status") == "PASS" and data.get("pipeline_mode") == "full" and not data.get("failed_steps") else "FAIL",
            "PASS/full/no failed steps",
            f"{data.get('pipeline_status')}/{data.get('pipeline_mode')}/{data.get('failed_steps')}",
            "both packets are full passing pipeline runs",
            f"{label}/pipeline_summary.json",
        )

    for key in STABLE_EXPERIMENT_KEYS:
        baseline_value = baseline_summary.get(key)
        candidate_value = candidate_summary.get(key)
        if profile == "monitaal-eof-fix" and key in EXPECTED_MONITAAL_EOF_FIX_DELTAS:
            expected_delta = EXPECTED_MONITAAL_EOF_FIX_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_MONITAAL_EOF_FIX_{key}",
                "expected_monitaal_eof_fix_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; monitaal_baseline_results.csv; translation_candidate_results.csv",
            )
            continue
        if profile == "generated-empty-inputs-added" and key in EXPECTED_GENERATED_EMPTY_INPUT_DELTAS:
            expected_delta = EXPECTED_GENERATED_EMPTY_INPUT_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_GENERATED_EMPTY_INPUT_{key}",
                "expected_generated_empty_input_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; monitaal_baseline_results.csv",
            )
            continue
        if profile == "xml-proof-obligations-added" and key in EXPECTED_XML_PROOF_OBLIGATION_DELTAS:
            expected_delta = EXPECTED_XML_PROOF_OBLIGATION_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_XML_PROOF_OBLIGATION_{key}",
                "expected_xml_proof_obligation_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; xml_proof_obligations.csv",
            )
            continue
        if profile == "xml-trace-coverage-added" and key in EXPECTED_XML_TRACE_COVERAGE_DELTAS:
            expected_delta = EXPECTED_XML_TRACE_COVERAGE_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_XML_TRACE_COVERAGE_{key}",
                "expected_xml_trace_coverage_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; xml_trace_coverage_obligations.csv",
            )
            continue
        if profile == "xml-boundary-traces-added" and key in EXPECTED_XML_BOUNDARY_TRACE_DELTAS:
            expected_delta = EXPECTED_XML_BOUNDARY_TRACE_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_XML_BOUNDARY_TRACE_{key}",
                "expected_xml_boundary_trace_metric" if expected_delta else "stable_xml_boundary_trace_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; translation_candidate_results.csv; xml_trace_coverage_obligations.csv",
            )
            continue
        if profile == "xml-three-valued-coverage-fixed" and key in EXPECTED_XML_THREE_VALUED_COVERAGE_DELTAS:
            expected_delta = EXPECTED_XML_THREE_VALUED_COVERAGE_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_XML_THREE_VALUED_COVERAGE_{key}",
                "expected_xml_three_valued_coverage_metric" if expected_delta else "stable_xml_three_valued_coverage_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; translation_candidate_results.csv; xml_trace_coverage_obligations.csv",
            )
            continue
        if profile == "xml-original-trace-gaps-added" and key in EXPECTED_XML_ORIGINAL_TRACE_GAP_DELTAS:
            expected_delta = EXPECTED_XML_ORIGINAL_TRACE_GAP_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_XML_ORIGINAL_TRACE_GAP_{key}",
                "expected_xml_original_trace_gap_metric" if expected_delta else "stable_xml_original_trace_gap_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; xml_original_trace_gaps.csv",
            )
            continue
        if profile == "xml-original-trace-gap-signoff-added" and key in EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_DELTAS:
            expected_delta = EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_{key}",
                "expected_xml_original_trace_gap_signoff_metric" if expected_delta else "stable_xml_original_trace_gap_signoff_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; human_review_queue.csv; review_signoff_template.csv; manual_review_checklist.csv; review_guide.csv",
            )
            continue
        if profile == "embedded-c-after10-original-trace-added" and key in EXPECTED_EMBEDDED_C_AFTER10_DELTAS:
            expected_delta = EXPECTED_EMBEDDED_C_AFTER10_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_EMBEDDED_C_AFTER10_{key}",
                "expected_embedded_c_after10_original_trace_metric" if expected_delta else "stable_embedded_c_after10_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; monitaal_embedded_benchmarks.csv; xml_original_trace_gaps.csv; translation_candidate_results.csv",
            )
            continue
        if profile in {"finite-syntax-oracles-added", "finite-syntax-oracles-and-three-valued-guard-added"} and key in EXPECTED_FINITE_SYNTAX_ORACLE_DELTAS:
            expected_delta = EXPECTED_FINITE_SYNTAX_ORACLE_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_FINITE_SYNTAX_ORACLE_{key}",
                "expected_finite_syntax_oracle_growth",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; semantic_cases.csv; semantic_oracle_derivations.csv; mightyppl_syntax_coverage_audit.csv",
            )
            continue
        if profile == "signoff-import-added" and key in EXPECTED_SIGNOFF_IMPORT_EXPERIMENT_DELTAS:
            expected_delta = EXPECTED_SIGNOFF_IMPORT_EXPERIMENT_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_SIGNOFF_IMPORT_{key}",
                "expected_signoff_import_review_guidance",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; review_guide.csv",
            )
            continue
        if profile == "correctness-audit-rowcount-guard-added" and key == "mitl_correctness_audit_rows":
            expected_candidate = int_value(candidate_summary, "semantic_cases") + int_value(candidate_summary, "translation_candidate_runs")
            add_row(
                rows,
                "EXPECTED_CORRECTNESS_AUDIT_ROWCOUNT_SUMMARY",
                "expected_correctness_audit_summary_growth",
                "PASS" if key not in baseline_summary and int_value(candidate_summary, key, -1) == expected_candidate else "FAIL",
                baseline_value if key in baseline_summary else "<absent>",
                candidate_value,
                f"baseline absent and candidate=semantic_cases+translation_candidate_runs={expected_candidate}",
                "experiment_summary.json; mitl_correctness_audit.csv",
            )
            continue
        if profile == "cli-trace-header-contract-added" and key in EXPECTED_CLI_TRACE_HEADER_CONTRACT_DELTAS:
            expected_delta = EXPECTED_CLI_TRACE_HEADER_CONTRACT_DELTAS[key]
            add_row(
                rows,
                f"EXPECTED_CLI_TRACE_HEADER_CONTRACT_{key}",
                "expected_cli_contract_growth" if expected_delta else "stable_cli_contract_metric",
                "PASS" if int_value(candidate_summary, key) - int_value(baseline_summary, key) == expected_delta else "FAIL",
                baseline_value,
                candidate_value,
                f"candidate-baseline={expected_delta}",
                "experiment_summary.json; cli_contract_audit.csv",
            )
            continue
        add_row(
            rows,
            f"STABLE_{key}",
            "stable_experiment_metric",
            "PASS" if normalize(baseline_value) == normalize(candidate_value) else "FAIL",
            baseline_value,
            candidate_value,
            "candidate equals baseline",
            "experiment_summary.json",
        )

    if profile == "manual-oracle-added":
        for key, expected_candidate in EXPECTED_NEW_MANUAL_ORACLE_KEYS.items():
            add_row(
                rows,
                f"EXPECTED_NEW_{key}",
                "expected_manual_oracle_growth",
                "PASS" if key not in baseline_summary and int_value(candidate_summary, key, -1) == expected_candidate else "FAIL",
                baseline_summary.get(key, "<absent>"),
                candidate_summary.get(key),
                f"baseline absent and candidate={expected_candidate}",
                "experiment_summary.json; manual_oracle_guide.csv",
            )
        expected_repro_delta = EXPECTED_REPRO_DELTA
        expected_verifier_delta = EXPECTED_VERIFIER_DELTA
    elif profile == "manual-oracle-independence-added":
        for key, (expected_baseline, expected_candidate) in EXPECTED_MANUAL_ORACLE_INDEPENDENCE_KEYS.items():
            baseline_value = int_value(baseline_summary, key, -1)
            candidate_value = int_value(candidate_summary, key, -1)
            add_row(
                rows,
                f"EXPECTED_INDEPENDENCE_{key}",
                "expected_manual_oracle_protocol_growth",
                "PASS" if baseline_value == expected_baseline and candidate_value == expected_candidate else "FAIL",
                baseline_summary.get(key),
                candidate_summary.get(key),
                f"baseline={expected_baseline}; candidate={expected_candidate}",
                "experiment_summary.json; manual_oracle_guide.csv",
            )
        expected_repro_delta = {key: 0 for key in EXPECTED_REPRO_DELTA}
        expected_verifier_delta = {key: 0 for key in EXPECTED_VERIFIER_DELTA}
    elif profile == "manual-oracle-baseline-boundary-added":
        for key, (expected_baseline, expected_candidate) in EXPECTED_MANUAL_ORACLE_BASELINE_BOUNDARY_KEYS.items():
            baseline_value = int_value(baseline_summary, key, -1)
            candidate_value = int_value(candidate_summary, key, -1)
            add_row(
                rows,
                f"EXPECTED_BASELINE_BOUNDARY_{key}",
                "expected_manual_oracle_protocol_growth",
                "PASS" if baseline_value == expected_baseline and candidate_value == expected_candidate else "FAIL",
                baseline_summary.get(key),
                candidate_summary.get(key),
                f"baseline={expected_baseline}; candidate={expected_candidate}",
                "experiment_summary.json; manual_oracle_guide.csv",
            )
        expected_repro_delta = {key: 0 for key in EXPECTED_REPRO_DELTA}
        expected_verifier_delta = {key: 0 for key in EXPECTED_VERIFIER_DELTA}
    else:
        for key in EXPECTED_NEW_MANUAL_ORACLE_KEYS:
            baseline_value = baseline_summary.get(key)
            candidate_value = candidate_summary.get(key)
            add_row(
                rows,
                f"STABLE_{key}",
                "stable_manual_oracle_metric",
                "PASS" if normalize(baseline_value) == normalize(candidate_value) else "FAIL",
                baseline_value,
                candidate_value,
                "candidate equals baseline",
                "experiment_summary.json; manual_oracle_guide.csv",
            )
        expected_repro_delta = {key: 0 for key in EXPECTED_REPRO_DELTA}
        if profile == "verifier-signoff-added":
            expected_verifier_delta = EXPECTED_SIGNOFF_VERIFIER_DELTA
        elif profile == "benchmark-blocker-diagnostics-added":
            expected_verifier_delta = EXPECTED_BLOCKER_VERIFIER_DELTA
        elif profile == "pipeline-source-hashes-added":
            expected_repro_delta = EXPECTED_PIPELINE_SOURCE_HASH_REPRO_DELTA
            expected_verifier_delta = EXPECTED_PIPELINE_SOURCE_HASH_VERIFIER_DELTA
        elif profile == "formula-catalog-integrated":
            expected_repro_delta = EXPECTED_FORMULA_CATALOG_REPRO_DELTA
            expected_verifier_delta = EXPECTED_FORMULA_CATALOG_VERIFIER_DELTA
        elif profile == "timeout-rerun-workbook-added":
            expected_verifier_delta = EXPECTED_TIMEOUT_WORKBOOK_VERIFIER_DELTA
        elif profile == "monitaal-eof-fix":
            expected_repro_delta = EXPECTED_MONITAAL_EOF_FIX_REPRO_DELTA
            expected_verifier_delta = {key: 0 for key in EXPECTED_VERIFIER_DELTA}
        elif profile == "generated-empty-inputs-added":
            expected_verifier_delta = EXPECTED_GENERATED_EMPTY_INPUT_VERIFIER_DELTA
        elif profile == "hardcoded-benchmarks-added":
            expected_repro_delta = EXPECTED_HARDCODED_BENCHMARK_REPRO_DELTA
            expected_verifier_delta = EXPECTED_HARDCODED_BENCHMARK_VERIFIER_DELTA
        elif profile == "finite-syntax-oracles-added":
            expected_verifier_delta = {key: 0 for key in EXPECTED_VERIFIER_DELTA}
        elif profile == "finite-syntax-oracles-and-three-valued-guard-added":
            expected_verifier_delta = EXPECTED_THREE_VALUED_GUARD_VERIFIER_DELTA
        elif profile == "three-valued-verdict-guard-added":
            expected_verifier_delta = EXPECTED_THREE_VALUED_GUARD_VERIFIER_DELTA
        elif profile == "signoff-import-added":
            expected_repro_delta = EXPECTED_SIGNOFF_IMPORT_REPRO_DELTA
            expected_verifier_delta = {key: 0 for key in EXPECTED_VERIFIER_DELTA}
        elif profile == "signoff-roundtrip-audit-added":
            expected_repro_delta = EXPECTED_SIGNOFF_ROUNDTRIP_REPRO_DELTA
            expected_verifier_delta = EXPECTED_SIGNOFF_ROUNDTRIP_VERIFIER_DELTA
        elif profile == "signoff-evidence-bundle-added":
            expected_repro_delta = EXPECTED_SIGNOFF_EVIDENCE_BUNDLE_REPRO_DELTA
            expected_verifier_delta = EXPECTED_SIGNOFF_EVIDENCE_BUNDLE_VERIFIER_DELTA
        elif profile == "evidence-consistency-guards-added":
            expected_verifier_delta = EXPECTED_EVIDENCE_CONSISTENCY_VERIFIER_DELTA
        elif profile == "xml-proof-obligations-added":
            expected_repro_delta = EXPECTED_XML_PROOF_OBLIGATION_REPRO_DELTA
            expected_verifier_delta = EXPECTED_XML_PROOF_OBLIGATION_VERIFIER_DELTA
        elif profile == "xml-trace-coverage-added":
            expected_repro_delta = EXPECTED_XML_TRACE_COVERAGE_REPRO_DELTA
            expected_verifier_delta = EXPECTED_XML_TRACE_COVERAGE_VERIFIER_DELTA
        elif profile == "xml-original-trace-gaps-added":
            expected_repro_delta = EXPECTED_XML_ORIGINAL_TRACE_GAP_REPRO_DELTA
            expected_verifier_delta = EXPECTED_XML_ORIGINAL_TRACE_GAP_VERIFIER_DELTA
        elif profile == "xml-original-trace-gap-signoff-added":
            expected_verifier_delta = EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_VERIFIER_DELTA
        elif profile == "paper-claim-gap-caveat-guard-added":
            expected_verifier_delta = EXPECTED_PAPER_CLAIM_GAP_CAVEAT_VERIFIER_DELTA
        elif profile == "embedded-c-after10-original-trace-added":
            expected_verifier_delta = EXPECTED_EMBEDDED_C_AFTER10_VERIFIER_DELTA
        elif profile == "embedded-c-after10-provenance-guard-added":
            expected_verifier_delta = EXPECTED_EMBEDDED_C_AFTER10_PROVENANCE_VERIFIER_DELTA
        elif profile == "baseline-match-oracle-boundary-guard-added":
            expected_verifier_delta = EXPECTED_BASELINE_MATCH_ORACLE_BOUNDARY_VERIFIER_DELTA
        elif profile == "workbook-preview-manifest-guard-added":
            expected_verifier_delta = EXPECTED_WORKBOOK_PREVIEW_MANIFEST_VERIFIER_DELTA
        elif profile == "workbook-source-coverage-guard-added":
            expected_verifier_delta = EXPECTED_WORKBOOK_SOURCE_COVERAGE_VERIFIER_DELTA
        elif profile == "workbook-xlsx-table-shape-guard-added":
            expected_verifier_delta = EXPECTED_WORKBOOK_XLSX_TABLE_SHAPE_VERIFIER_DELTA
        elif profile == "correctness-audit-rowcount-guard-added":
            expected_verifier_delta = EXPECTED_CORRECTNESS_AUDIT_ROWCOUNT_VERIFIER_DELTA
        elif profile == "workbook-rebuild-summary-guard-added":
            expected_verifier_delta = EXPECTED_WORKBOOK_REBUILD_SUMMARY_VERIFIER_DELTA
        elif profile == "candidate-prefix-observations-guard-added":
            expected_verifier_delta = EXPECTED_CANDIDATE_PREFIX_OBSERVATIONS_VERIFIER_DELTA
        elif profile == "monitaal-xml-structural-ledger-guard-added":
            expected_verifier_delta = EXPECTED_MONITAAL_XML_STRUCTURAL_LEDGER_VERIFIER_DELTA
        elif profile == "manual-review-entrypoint-reference-guard-added":
            expected_verifier_delta = EXPECTED_MANUAL_REVIEW_ENTRYPOINT_REFERENCE_VERIFIER_DELTA
        elif profile == "gear-original-input-response-audit-added":
            expected_repro_delta = EXPECTED_REPRO_DELTA
            expected_verifier_delta = EXPECTED_VERIFIER_DELTA
        elif profile == "non-gear-original-input-search-audit-added":
            expected_repro_delta = EXPECTED_REPRO_DELTA
            expected_verifier_delta = EXPECTED_VERIFIER_DELTA
        elif profile == "review-queue-source-resolution-added":
            expected_verifier_delta = EXPECTED_QUEUE_SOURCE_VERIFIER_DELTA
        elif profile == "review-queue-evidence-resolution-added":
            expected_verifier_delta = EXPECTED_QUEUE_EVIDENCE_VERIFIER_DELTA
        else:
            expected_verifier_delta = {key: 0 for key in EXPECTED_VERIFIER_DELTA}

    for key, expected_delta in expected_repro_delta.items():
        baseline_value = int_value(baseline_summary, key)
        candidate_value = int_value(candidate_summary, key)
        add_row(
            rows,
            f"EXPECTED_REPRO_DELTA_{key}",
            "expected_reproducibility_growth" if expected_delta else "stable_reproducibility_metric",
            "PASS" if candidate_value - baseline_value == expected_delta else "FAIL",
            baseline_value,
            candidate_value,
            f"candidate-baseline={expected_delta}",
            "experiment_summary.json; reproducibility_manifest.csv",
        )

    for key, expected_delta in expected_verifier_delta.items():
        baseline_value = int_value(baseline_verifier, key)
        candidate_value = int_value(candidate_verifier, key)
        add_row(
            rows,
            f"EXPECTED_VERIFIER_DELTA_{key}",
            "expected_verifier_growth" if expected_delta else "stable_verifier_metric",
            "PASS" if candidate_value - baseline_value == expected_delta else "FAIL",
            baseline_value,
            candidate_value,
            f"candidate-baseline={expected_delta}",
            "review_packet_verification.json",
        )

    baseline_sheets = workbook_sheet_names(baseline_dir / "paper_review_results.xlsx")
    candidate_sheets = workbook_sheet_names(candidate_dir / "paper_review_results.xlsx")
    added_sheets = sorted(set(candidate_sheets) - set(baseline_sheets))
    removed_sheets = sorted(set(baseline_sheets) - set(candidate_sheets))
    if profile == "manual-oracle-added":
        expected_added_sheets = ["Manual Oracle Guide"]
    elif profile == "benchmark-blocker-diagnostics-added":
        expected_added_sheets = ["Benchmark Blockers"]
    elif profile == "formula-catalog-integrated":
        expected_added_sheets = ["MITL Runtime Catalog", "MITL Semantic Catalog", "MITL XML Candidates"]
    elif profile == "timeout-rerun-workbook-added":
        expected_added_sheets = ["Signoff Validation", "Timeout Rerun", "Timeout Rerun Summary"]
    elif profile == "hardcoded-benchmarks-added":
        expected_added_sheets = ["Hardcoded Benchmarks"]
    elif profile == "signoff-roundtrip-audit-added":
        expected_added_sheets = ["Signoff Roundtrip"]
    elif profile == "signoff-evidence-bundle-added":
        expected_added_sheets = ["Signoff Evidence"]
    elif profile == "xml-proof-obligations-added":
        expected_added_sheets = ["XML Obligations"]
    elif profile == "xml-trace-coverage-added":
        expected_added_sheets = ["XML Trace Coverage"]
    elif profile == "xml-original-trace-gaps-added":
        expected_added_sheets = ["Original Trace Gaps"]
    elif profile == "gear-original-input-response-audit-added":
        expected_added_sheets = ["Gear Original Audit"]
    elif profile == "non-gear-original-input-search-audit-added":
        expected_added_sheets = ["Non-Gear Input Search"]
    else:
        expected_added_sheets = []
    add_row(
        rows,
        "WORKBOOK_SHEET_DELTA",
        "expected_workbook_growth" if expected_added_sheets else "stable_workbook_schema",
        "PASS" if added_sheets == expected_added_sheets and not removed_sheets else "FAIL",
        baseline_sheets,
        candidate_sheets,
        f"added sheets={expected_added_sheets}; removed sheets=[]",
        "paper_review_results.xlsx",
        f"added={added_sheets}; removed={removed_sheets}",
    )

    manual_guide_rows = read_csv(candidate_dir / "manual_oracle_guide.csv")
    required_ids = {
        "MOG_DEFINITION",
        "MOG_THREE_VALUED_PREFIX",
        "MOG_FINAL_VERDICT",
        "MOG_BUILD_STATS_BOUNDARY",
        "MOG_FIX_POLICY",
        "MOG_SIGNOFF_BOUNDARY",
    }
    expected_manual_oracle_rows = int_value(candidate_summary, "manual_oracle_guide_rows", 8)
    if profile == "manual-oracle-independence-added":
        required_ids.add("MOG_INDEPENDENCE")
    guide_ids = {row.get("guide_id", "") for row in manual_guide_rows}
    add_row(
        rows,
        "MANUAL_ORACLE_REQUIRED_IDS",
        "expected_manual_oracle_growth",
        "PASS" if len(manual_guide_rows) == expected_manual_oracle_rows and required_ids.issubset(guide_ids) else "FAIL",
        "<absent>",
        sorted(guide_ids),
        f"candidate manual oracle guide has {expected_manual_oracle_rows} rows and required protocol IDs",
        "manual_oracle_guide.csv",
    )

    if profile == "manual-oracle-independence-added":
        baseline_guide_rows = read_csv(baseline_dir / "manual_oracle_guide.csv")
        baseline_ids = {row.get("guide_id", "") for row in baseline_guide_rows}
        independence_rows = [row for row in manual_guide_rows if row.get("guide_id") == "MOG_INDEPENDENCE"]
        independence_row = independence_rows[0] if independence_rows else {}
        add_row(
            rows,
            "MANUAL_ORACLE_INDEPENDENCE_ROW_DELTA",
            "expected_manual_oracle_protocol_growth",
            "PASS" if "MOG_INDEPENDENCE" not in baseline_ids and "MOG_INDEPENDENCE" in guide_ids else "FAIL",
            sorted(baseline_ids),
            sorted(guide_ids),
            "candidate adds MOG_INDEPENDENCE and baseline lacks it",
            "manual_oracle_guide.csv",
        )
        add_row(
            rows,
            "MANUAL_ORACLE_INDEPENDENCE_TEXT",
            "expected_manual_oracle_protocol_growth",
            (
                "PASS"
                if independence_row.get("priority") == "P0"
                and independence_row.get("section") == "independence"
                and "independent of TAMonitor" in independence_row.get("protocol_step", "")
                and "agreement between two implementations" in independence_row.get("must_not_claim", "")
                else "FAIL"
            ),
            "",
            independence_row,
            "independence row states source independence and forbids implementation-agreement substitution",
            "manual_oracle_guide.csv",
        )
        manual_guide_md = (candidate_dir / "manual_oracle_guide.md").read_text(encoding="utf-8")
        add_row(
            rows,
            "MANUAL_ORACLE_MARKDOWN_COLUMNS",
            "expected_manual_oracle_protocol_growth",
            "PASS" if "decision_rule" in manual_guide_md and "must_not_claim" in manual_guide_md else "FAIL",
            "",
            "decision_rule/must_not_claim present",
            "Markdown guide exposes decision_rule and must_not_claim",
            "manual_oracle_guide.md",
        )

    if profile in {"stable", "verifier-signoff-added", "manual-oracle-independence-added", "manual-oracle-baseline-boundary-added", "benchmark-blocker-diagnostics-added", "formula-catalog-integrated", "signoff-policy-added", "signoff-evidence-resolution-added", "signoff-import-added", "signoff-source-resolution-added", "review-queue-source-resolution-added", "review-queue-evidence-resolution-added", "signoff-roundtrip-audit-added", "signoff-evidence-bundle-added", "evidence-consistency-guards-added", "xml-original-trace-gap-signoff-added", "paper-claim-gap-caveat-guard-added", "embedded-c-after10-original-trace-added", "embedded-c-after10-provenance-guard-added", "baseline-match-oracle-boundary-guard-added", "workbook-preview-manifest-guard-added", "workbook-source-coverage-guard-added", "workbook-xlsx-table-shape-guard-added", "correctness-audit-rowcount-guard-added", "workbook-rebuild-summary-guard-added", "candidate-prefix-observations-guard-added", "monitaal-xml-structural-ledger-guard-added", "manual-review-entrypoint-reference-guard-added", "gear-original-input-response-audit-added", "non-gear-original-input-search-audit-added", "cli-trace-header-contract-added"}:
        expected_signoff_deltas: dict[str, int] = {}
        if profile == "signoff-policy-added":
            expected_signoff_deltas = EXPECTED_SIGNOFF_POLICY_VALIDATION_DELTA
        elif profile == "signoff-evidence-resolution-added":
            expected_signoff_deltas = EXPECTED_SIGNOFF_EVIDENCE_RESOLUTION_DELTA
        elif profile == "signoff-source-resolution-added":
            expected_signoff_deltas = EXPECTED_SIGNOFF_SOURCE_RESOLUTION_DELTA
        elif profile == "review-queue-source-resolution-added":
            expected_signoff_deltas = EXPECTED_QUEUE_SOURCE_RESOLUTION_DELTA
        elif profile == "review-queue-evidence-resolution-added":
            expected_signoff_deltas = EXPECTED_QUEUE_EVIDENCE_RESOLUTION_DELTA
        elif profile == "xml-original-trace-gap-signoff-added":
            expected_signoff_deltas = EXPECTED_XML_ORIGINAL_TRACE_GAP_SIGNOFF_VALIDATION_DELTA
        elif profile == "embedded-c-after10-original-trace-added":
            expected_signoff_deltas = EXPECTED_EMBEDDED_C_AFTER10_SIGNOFF_VALIDATION_DELTA
        for label, signoff_summary in [("baseline", baseline_signoff_summary), ("candidate", candidate_signoff_summary)]:
            add_row(
                rows,
                f"SIGNOFF_VALIDATION_PASS_{label.upper()}",
                "stable_signoff_validation",
                "PASS" if signoff_summary.get("mode") == "pre-review" and int_value(signoff_summary, "fail", -1) == 0 else "FAIL",
                "mode=pre-review/fail=0",
                {
                    "mode": signoff_summary.get("mode", ""),
                    "fail": signoff_summary.get("fail", ""),
                },
                "both stable packets include passing generated signoff validation",
                f"{label}/review_signoff_validation.json",
            )
        for key in STABLE_SIGNOFF_KEYS:
            baseline_value = baseline_signoff_summary.get(key)
            candidate_value = candidate_signoff_summary.get(key)
            if key in expected_signoff_deltas:
                expected_delta = expected_signoff_deltas[key]
                add_row(
                    rows,
                    f"EXPECTED_SIGNOFF_VALIDATION_{key}",
                    "expected_signoff_validation_growth" if expected_delta else "stable_signoff_validation_metric",
                    "PASS" if int_value(candidate_signoff_summary, key) - int_value(baseline_signoff_summary, key) == expected_delta else "FAIL",
                    baseline_value,
                    candidate_value,
                    f"candidate-baseline={expected_delta}",
                    "review_signoff_validation.json",
                )
                continue
            add_row(
                rows,
                f"STABLE_SIGNOFF_{key}",
                "stable_signoff_validation",
                "PASS" if normalize(baseline_value) == normalize(candidate_value) else "FAIL",
                baseline_value,
                candidate_value,
                "candidate equals baseline",
                "review_signoff_validation.json",
            )

    compare_csv_files(baseline_dir, candidate_dir, rows, profile)

    status_counts = Counter(row["status"] for row in rows)
    summary = {
        "baseline_dir": str(baseline_dir),
        "candidate_dir": str(candidate_dir),
        "profile": profile,
        "rows": len(rows),
        "pass": status_counts.get("PASS", 0),
        "fail": status_counts.get("FAIL", 0),
        "warn": status_counts.get("WARN", 0),
        "expected_added_sheets": expected_added_sheets,
        "expected_manual_oracle_rows": int_value(candidate_summary, "manual_oracle_guide_rows", 8),
        "expected_verifier_delta": expected_verifier_delta,
        "expected_repro_delta": expected_repro_delta,
    }
    return rows, summary


def write_markdown(path: Path, rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    lines = [
        "# Result Stability Audit",
        "",
        "This audit compares two full TAMonitor paper-review result packets.",
        "It is designed to prove that review-packet instrumentation did not change semantic, runtime, benchmark, or claim-safety results.",
        "",
        "## Summary",
        "",
        f"- baseline: `{summary['baseline_dir']}`",
        f"- candidate: `{summary['candidate_dir']}`",
        f"- profile: `{summary['profile']}`",
        f"- PASS: {summary['pass']}",
        f"- WARN: {summary['warn']}",
        f"- FAIL: {summary['fail']}",
        f"- expected added sheets: `{summary['expected_added_sheets']}`",
        "",
        "## Checks",
        "",
        "| check_id | status | category | baseline | candidate | expected |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        baseline = row["baseline_value"].replace("|", "\\|")[:180]
        candidate = row["candidate_value"].replace("|", "\\|")[:180]
        expected = row["expected"].replace("|", "\\|")
        lines.append(f"| `{row['check_id']}` | `{row['status']}` | `{row['category']}` | {baseline} | {candidate} | {expected} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline result directory.")
    parser.add_argument("--candidate", type=Path, required=True, help="Candidate result directory.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for audit files. Defaults to candidate directory.")
    parser.add_argument(
        "--profile",
        choices=[
            "manual-oracle-added",
            "stable",
            "verifier-signoff-added",
            "manual-oracle-independence-added",
            "manual-oracle-baseline-boundary-added",
            "benchmark-blocker-diagnostics-added",
            "formula-catalog-integrated",
            "pipeline-source-hashes-added",
            "timeout-rerun-workbook-added",
            "monitaal-eof-fix",
            "generated-empty-inputs-added",
            "hardcoded-benchmarks-added",
            "finite-syntax-oracles-added",
            "finite-syntax-oracles-and-three-valued-guard-added",
            "three-valued-verdict-guard-added",
            "signoff-policy-added",
            "signoff-evidence-resolution-added",
            "signoff-import-added",
            "signoff-source-resolution-added",
            "review-queue-source-resolution-added",
            "review-queue-evidence-resolution-added",
            "signoff-roundtrip-audit-added",
            "signoff-evidence-bundle-added",
            "evidence-consistency-guards-added",
            "xml-proof-obligations-added",
            "xml-trace-coverage-added",
            "xml-boundary-traces-added",
            "xml-three-valued-coverage-fixed",
            "xml-original-trace-gaps-added",
            "xml-original-trace-gap-signoff-added",
            "paper-claim-gap-caveat-guard-added",
            "embedded-c-after10-original-trace-added",
            "embedded-c-after10-provenance-guard-added",
            "baseline-match-oracle-boundary-guard-added",
            "workbook-preview-manifest-guard-added",
            "workbook-source-coverage-guard-added",
            "workbook-xlsx-table-shape-guard-added",
            "correctness-audit-rowcount-guard-added",
            "workbook-rebuild-summary-guard-added",
            "candidate-prefix-observations-guard-added",
            "monitaal-xml-structural-ledger-guard-added",
            "manual-review-entrypoint-reference-guard-added",
            "gear-original-input-response-audit-added",
            "non-gear-original-input-search-audit-added",
            "cli-trace-header-contract-added",
        ],
        default="manual-oracle-added",
        help=(
            "Expected packet relationship. Use manual-oracle-added when the "
            "candidate first adds the Manual Oracle Guide; use stable when "
            "both packets already contain that review layer; use "
            "verifier-signoff-added when the candidate only strengthens the "
            "packet verifier with signoff-validation checks; use "
            "manual-oracle-independence-added when the candidate only adds the "
            "MOG_INDEPENDENCE protocol row and exposes manual-oracle decision "
            "columns in Markdown; use manual-oracle-baseline-boundary-added when "
            "the candidate only adds the MOG_BASELINE_NOT_HAND_ORACLE protocol row "
            "distinguishing MoniTAal baseline matches from hand oracles; use benchmark-blocker-diagnostics-added when "
            "the candidate only adds benchmark blocker diagnostics and refines "
            "not-claimed blocker reasons without changing verdict evidence; use "
            "pipeline-source-hashes-added when the candidate only broadens source "
            "hash coverage for review-pipeline scripts; use "
            "formula-catalog-integrated when the candidate only adds the "
            "packet-local MITL formula catalog generator source hash and "
            "workbook catalog sheets while leaving semantic/runtime/benchmark "
            "evidence stable; use "
            "timeout-rerun-workbook-added when the candidate only adds signoff "
            "validation and timeout-rerun evidence sheets to the workbook; use "
            "monitaal-eof-fix when the candidate fixes MoniTAal-bin file-mode "
            "EOF handling so old baseline timeouts become ran/INCONCLUSIVE "
            "trace-level comparisons; use generated-empty-inputs-added when "
            "the candidate adds explicit generated empty timed-word probes for "
            "XML pairs with no repository input, without promoting them as "
            "original-input benchmark evidence; use hardcoded-benchmarks-added "
            "when the candidate only adds separate MoniTAal benchmark/main.cpp "
            "evidence without changing XML-to-MITL trace-level comparisons; use "
            "finite-syntax-oracles-added when the candidate only adds finite-word "
            "hand-oracle rows for existing user-level MightyPPL syntax families; use "
            "finite-syntax-oracles-and-three-valued-guard-added when those rows and "
            "the public-verdict guard are introduced in the same candidate packet; use "
            "three-valued-verdict-guard-added when the candidate only strengthens "
            "packet verification so public runtime-verdict artifacts cannot expose "
            "internal non-three-valued monitor states; use signoff-policy-added "
            "when the candidate only adds row-level signoff decision guidance and "
            "scope-policy validation; use signoff-evidence-resolution-added when "
            "the candidate only adds evidence-artifact resolution checks and clearer "
            "manual-review Markdown; use signoff-import-added when the candidate only "
            "adds the safe human-signoff import roundtrip and its review-guide row; "
            "use signoff-source-resolution-added when the candidate only adds "
            "source_sheet/source_id resolution checks for signoff rows; use "
            "review-queue-source-resolution-added when the candidate only adds "
            "source_sheet/source_id resolution checks for every human_review_queue "
            "row plus stale-validation packet guards; use "
            "review-queue-evidence-resolution-added when the candidate only adds "
            "evidence_artifacts resolution checks for every human_review_queue row "
            "plus stale-validation packet guards; use signoff-roundtrip-audit-added "
            "when the candidate only promotes the synthetic Review Signoff import "
            "roundtrip regression into official packet artifacts and a workbook sheet; "
            "use signoff-evidence-bundle-added when the candidate only adds the "
            "generated Review Signoff evidence bundle and workbook sheet; use "
            "evidence-consistency-guards-added when the candidate only fixes stale "
            "timeout/INCONCLUSIVE evidence wording and adds packet verifier guards; use "
            "xml-proof-obligations-added when the candidate only adds XML proof-obligation "
            "audit artifacts, workbook sheet, and packet/manifest guards; use "
            "xml-trace-coverage-added when the candidate only adds XML boundary/trace "
            "coverage-obligation artifacts, workbook sheet, and packet/manifest guards; use "
            "xml-boundary-traces-added when the candidate only adds generated boundary "
            "review traces that increase XML candidate/baseline rows and reduce trace-coverage REVIEW_REQUIRED rows; use "
            "xml-three-valued-coverage-fixed when the candidate corrects XML trace-coverage obligations "
            "to respect infinite-word three-valued semantics and adds the matching generated traces; use "
            "xml-original-trace-gaps-added when the candidate only extracts the remaining original-input "
            "trace provenance gaps into dedicated review artifacts and a workbook sheet; use "
            "xml-original-trace-gap-signoff-added when the candidate only makes those original-trace "
            "gap rows first-class manual-review/signoff items; use "
            "paper-claim-gap-caveat-guard-added when the candidate only propagates unresolved "
            "original-trace gaps into paper-facing claim caveats and verifier guards; use "
            "embedded-c-after10-original-trace-added when the candidate adds the MoniTAal "
            "Monitor_test.cpp c_after_10 embedded timed-word evidence and closes exactly that "
            "original-trace gap; use embedded-c-after10-provenance-guard-added when the candidate "
            "only adds packet-verifier and hash-coverage guards for that embedded c_after_10 evidence; use "
            "baseline-match-oracle-boundary-guard-added when the candidate only adds a packet verifier guard "
            "that keeps MoniTAal baseline matches separate from hand-oracle and XML-equivalence claims; use "
            "workbook-preview-manifest-guard-added when the candidate only adds packet-verifier guards for "
            "workbook preview manifest presence and sheet/source-CSV consistency; use "
            "workbook-source-coverage-guard-added when the candidate only adds packet-verifier guards for "
            "exact review-sheet/source-CSV bindings and summary row-count consistency; use "
            "workbook-xlsx-table-shape-guard-added when the candidate only adds packet-verifier guards "
            "that parse xlsx internal table ranges and compare them with manifest/source CSV dimensions; use "
            "correctness-audit-rowcount-guard-added when the candidate only adds a first-class "
            "mitl_correctness_audit_rows summary key plus required/hash/count guards for the Correctness Audit sheet; use "
            "workbook-rebuild-summary-guard-added when the candidate only adds packet-verifier guards for "
            "the final workbook rebuild summary and late sidecar sheet evidence; use "
            "candidate-prefix-observations-guard-added when the candidate only adds packet-verifier guards "
            "for raw candidate prefix observations and per-run steps.csv consistency; use "
            "monitaal-xml-structural-ledger-guard-added when the candidate only adds structural packet-verifier "
            "guards for MoniTAal XML inventory, transition details, edge-proof ledger, and appendix consistency "
            "without claiming automatic XML-to-MITL equivalence; use "
            "manual-review-entrypoint-reference-guard-added when the candidate only fixes upstream manual-review "
            "entrypoint evidence references and adds packet-verifier guards for review guide, goal audit, "
            "manual checklist, and requirements audit references without claiming human signoff; use "
            "gear-original-input-response-audit-added when the candidate only adds finite-prefix response "
            "accounting for the original gear-control-input repository trace while preserving its "
            "INCONCLUSIVE online-verdict boundary; use "
            "non-gear-original-input-search-audit-added when the candidate only adds repository-input "
            "search evidence for non-gear original-trace gaps while preserving generated-review-trace caveats; use "
            "cli-trace-header-contract-added when the candidate only adds a CLI contract probe for "
            "`time,props` trace headers."
        ),
    )
    args = parser.parse_args()

    baseline_dir = args.baseline.resolve()
    candidate_dir = args.candidate.resolve()
    out_dir = (args.out_dir or candidate_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, summary = compare_packets(baseline_dir, candidate_dir, args.profile)
    fieldnames = ["check_id", "category", "status", "baseline_value", "candidate_value", "expected", "evidence", "notes"]
    write_csv(out_dir / "result_stability_audit.csv", rows, fieldnames)
    (out_dir / "result_stability_audit.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown(out_dir / "result_stability_audit.md", rows, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
