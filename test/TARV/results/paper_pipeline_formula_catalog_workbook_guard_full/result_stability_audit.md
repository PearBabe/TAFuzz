# Result Stability Audit

This audit compares two full TAMonitor paper-review result packets.
It is designed to prove that review-packet instrumentation did not change semantic, runtime, benchmark, or claim-safety results.

## Summary

- baseline: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_cli_trace_header_contract_full`
- candidate: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full`
- profile: `formula-catalog-integrated`
- PASS: 190
- WARN: 0
- FAIL: 0
- expected added sheets: `['MITL Runtime Catalog', 'MITL Semantic Catalog', 'MITL XML Candidates']`

## Checks

| check_id | status | category | baseline | candidate | expected |
|---|---|---|---|---|---|
| `PIPELINE_STATUS_BASELINE` | `PASS` | `pipeline` | PASS/full/no failed steps | PASS/full/[] | both packets are full passing pipeline runs |
| `PIPELINE_STATUS_CANDIDATE` | `PASS` | `pipeline` | PASS/full/no failed steps | PASS/full/[] | both packets are full passing pipeline runs |
| `STABLE_semantic_cases` | `PASS` | `stable_experiment_metric` | 87 | 87 | candidate equals baseline |
| `STABLE_semantic_ran` | `PASS` | `stable_experiment_metric` | 87 | 87 | candidate equals baseline |
| `STABLE_semantic_pass` | `PASS` | `stable_experiment_metric` | 70 | 70 | candidate equals baseline |
| `STABLE_semantic_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_correctness_verified` | `PASS` | `stable_experiment_metric` | 70 | 70 | candidate equals baseline |
| `STABLE_semantic_finite_verified` | `PASS` | `stable_experiment_metric` | 34 | 34 | candidate equals baseline |
| `STABLE_semantic_infinite_verified` | `PASS` | `stable_experiment_metric` | 36 | 36 | candidate equals baseline |
| `STABLE_semantic_correctness_needs_manual_oracle` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_correctness_not_verified_resource_limit` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_correctness_not_verified_timeout` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_correctness_not_a_verdict_check` | `PASS` | `stable_experiment_metric` | 17 | 17 | candidate equals baseline |
| `STABLE_semantic_correctness_build_timeout_not_a_verdict_check` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_prefix_oracle_rows` | `PASS` | `stable_experiment_metric` | 163 | 163 | candidate equals baseline |
| `STABLE_semantic_prefix_oracle_match` | `PASS` | `stable_experiment_metric` | 146 | 146 | candidate equals baseline |
| `STABLE_semantic_prefix_oracle_mismatch` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_prefix_oracle_missing_observed_step` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_prefix_final_verdict_only` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_prefix_carry_forward_steps` | `PASS` | `stable_experiment_metric` | 34 | 34 | candidate equals baseline |
| `STABLE_semantic_oracle_derivation_rows` | `PASS` | `stable_experiment_metric` | 87 | 87 | candidate equals baseline |
| `STABLE_semantic_oracle_hand_verified` | `PASS` | `stable_experiment_metric` | 70 | 70 | candidate equals baseline |
| `STABLE_semantic_oracle_construction_stats_only` | `PASS` | `stable_experiment_metric` | 17 | 17 | candidate equals baseline |
| `STABLE_semantic_oracle_review_required` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_oracle_prefix_mismatches` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_mitl_correctness_audit_rows` | `PASS` | `stable_experiment_metric` | 150 | 150 | candidate equals baseline |
| `STABLE_semantic_review` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_build_stats` | `PASS` | `stable_experiment_metric` | 17 | 17 | candidate equals baseline |
| `STABLE_semantic_build_timeout` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_resource_limit` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_timeout` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_error` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_review_unsupported` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_semantic_exclusion_rows` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_internal_count_forms_excluded` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_syntax_coverage_rows` | `PASS` | `stable_experiment_metric` | 45 | 45 | candidate equals baseline |
| `STABLE_syntax_coverage_verified_runtime` | `PASS` | `stable_experiment_metric` | 36 | 36 | candidate equals baseline |
| `STABLE_syntax_coverage_finite_and_infinite` | `PASS` | `stable_experiment_metric` | 36 | 36 | candidate equals baseline |
| `STABLE_syntax_coverage_build_stats_only` | `PASS` | `stable_experiment_metric` | 1 | 1 | candidate equals baseline |
| `STABLE_syntax_coverage_excluded_internal` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_syntax_coverage_missing` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_formula_input_policy_rows` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_formula_input_policy_pass` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_formula_input_policy_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_formula_input_policy_assert_like_failures` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_cli_contract_rows` | `PASS` | `stable_experiment_metric` | 11 | 11 | candidate equals baseline |
| `STABLE_cli_contract_pass` | `PASS` | `stable_experiment_metric` | 11 | 11 | candidate equals baseline |
| `STABLE_cli_contract_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_cli_contract_controlled_errors` | `PASS` | `stable_experiment_metric` | 5 | 5 | candidate equals baseline |
| `STABLE_review_guide_rows` | `PASS` | `stable_experiment_metric` | 15 | 15 | candidate equals baseline |
| `STABLE_review_guide_p0` | `PASS` | `stable_experiment_metric` | 9 | 9 | candidate equals baseline |
| `STABLE_review_guide_p1` | `PASS` | `stable_experiment_metric` | 6 | 6 | candidate equals baseline |
| `STABLE_goal_completion_rows` | `PASS` | `stable_experiment_metric` | 17 | 17 | candidate equals baseline |
| `STABLE_goal_completion_pass` | `PASS` | `stable_experiment_metric` | 13 | 13 | candidate equals baseline |
| `STABLE_goal_completion_pass_with_caveat` | `PASS` | `stable_experiment_metric` | 1 | 1 | candidate equals baseline |
| `STABLE_goal_completion_review_required` | `PASS` | `stable_experiment_metric` | 2 | 2 | candidate equals baseline |
| `STABLE_goal_completion_v1_deferred` | `PASS` | `stable_experiment_metric` | 1 | 1 | candidate equals baseline |
| `STABLE_goal_completion_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_human_review_queue_rows` | `PASS` | `stable_experiment_metric` | 72 | 72 | candidate equals baseline |
| `STABLE_human_review_queue_human_required` | `PASS` | `stable_experiment_metric` | 55 | 55 | candidate equals baseline |
| `STABLE_human_review_queue_p0` | `PASS` | `stable_experiment_metric` | 44 | 44 | candidate equals baseline |
| `STABLE_human_review_queue_p1` | `PASS` | `stable_experiment_metric` | 10 | 10 | candidate equals baseline |
| `STABLE_human_review_queue_p2` | `PASS` | `stable_experiment_metric` | 2 | 2 | candidate equals baseline |
| `STABLE_human_review_queue_p3` | `PASS` | `stable_experiment_metric` | 16 | 16 | candidate equals baseline |
| `STABLE_human_review_queue_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_review_signoff_template_rows` | `PASS` | `stable_experiment_metric` | 56 | 56 | candidate equals baseline |
| `STABLE_review_signoff_template_blank_decisions` | `PASS` | `stable_experiment_metric` | 56 | 56 | candidate equals baseline |
| `STABLE_review_signoff_template_p0` | `PASS` | `stable_experiment_metric` | 44 | 44 | candidate equals baseline |
| `STABLE_review_signoff_template_p1` | `PASS` | `stable_experiment_metric` | 10 | 10 | candidate equals baseline |
| `STABLE_review_signoff_template_p2` | `PASS` | `stable_experiment_metric` | 2 | 2 | candidate equals baseline |
| `STABLE_manual_review_rows` | `PASS` | `stable_experiment_metric` | 17 | 17 | candidate equals baseline |
| `STABLE_manual_review_pass` | `PASS` | `stable_experiment_metric` | 10 | 10 | candidate equals baseline |
| `STABLE_manual_review_pass_with_caveat` | `PASS` | `stable_experiment_metric` | 2 | 2 | candidate equals baseline |
| `STABLE_manual_review_review_required` | `PASS` | `stable_experiment_metric` | 4 | 4 | candidate equals baseline |
| `STABLE_manual_review_v1_deferred` | `PASS` | `stable_experiment_metric` | 1 | 1 | candidate equals baseline |
| `STABLE_manual_review_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_manual_review_human_required` | `PASS` | `stable_experiment_metric` | 13 | 13 | candidate equals baseline |
| `STABLE_xml_templates` | `PASS` | `stable_experiment_metric` | 60 | 60 | candidate equals baseline |
| `STABLE_xml_transition_detail_rows` | `PASS` | `stable_experiment_metric` | 386 | 386 | candidate equals baseline |
| `STABLE_xml_pairs` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_translation_candidates` | `PASS` | `stable_experiment_metric` | 19 | 19 | candidate equals baseline |
| `STABLE_benchmark_manifest_rows` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_benchmark_manifest_strong_trace_level` | `PASS` | `stable_experiment_metric` | 15 | 15 | candidate equals baseline |
| `STABLE_benchmark_manifest_single_trace_level` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_benchmark_manifest_approximate_trace_only` | `PASS` | `stable_experiment_metric` | 4 | 4 | candidate equals baseline |
| `STABLE_benchmark_manifest_not_promoted` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_xml_edge_guard_proof_rows` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_xml_edge_guard_proof_ready` | `PASS` | `stable_experiment_metric` | 15 | 15 | candidate equals baseline |
| `STABLE_xml_edge_guard_review_required` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_xml_edge_guard_not_ready` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_xml_edge_guard_incomplete` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_xml_proof_appendix_rows` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_xml_proof_appendix_ready` | `PASS` | `stable_experiment_metric` | 15 | 15 | candidate equals baseline |
| `STABLE_xml_proof_appendix_excluded` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_xml_proof_obligation_rows` | `PASS` | `stable_experiment_metric` | 143 | 143 | candidate equals baseline |
| `STABLE_xml_proof_obligation_pass` | `PASS` | `stable_experiment_metric` | 126 | 126 | candidate equals baseline |
| `STABLE_xml_proof_obligation_review_required` | `PASS` | `stable_experiment_metric` | 17 | 17 | candidate equals baseline |
| `STABLE_xml_proof_obligation_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_xml_trace_coverage_rows` | `PASS` | `stable_experiment_metric` | 114 | 114 | candidate equals baseline |
| `STABLE_xml_trace_coverage_pass` | `PASS` | `stable_experiment_metric` | 106 | 106 | candidate equals baseline |
| `STABLE_xml_trace_coverage_review_required` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_xml_trace_coverage_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_xml_original_trace_gap_rows` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_xml_original_trace_gap_review_required` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_xml_original_trace_gap_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_paper_claim_review_rows` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_paper_claim_body_pattern_ready` | `PASS` | `stable_experiment_metric` | 15 | 15 | candidate equals baseline |
| `STABLE_paper_claim_appendix_timeout_caveat` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_paper_claim_excluded` | `PASS` | `stable_experiment_metric` | 8 | 8 | candidate equals baseline |
| `STABLE_paper_claim_audit_rows` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_paper_claim_audit_pass` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_paper_claim_audit_warn` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_paper_claim_audit_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_requirements_audit_rows` | `PASS` | `stable_experiment_metric` | 23 | 23 | candidate equals baseline |
| `STABLE_requirements_audit_pass` | `PASS` | `stable_experiment_metric` | 20 | 20 | candidate equals baseline |
| `STABLE_requirements_audit_pass_with_caveat` | `PASS` | `stable_experiment_metric` | 2 | 2 | candidate equals baseline |
| `STABLE_requirements_audit_v1_deferred` | `PASS` | `stable_experiment_metric` | 1 | 1 | candidate equals baseline |
| `STABLE_requirements_audit_fail` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_translation_candidate_runs` | `PASS` | `stable_experiment_metric` | 63 | 63 | candidate equals baseline |
| `STABLE_translation_candidate_success` | `PASS` | `stable_experiment_metric` | 63 | 63 | candidate equals baseline |
| `STABLE_translation_candidate_timeouts` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_translation_candidate_baseline_matches` | `PASS` | `stable_experiment_metric` | 63 | 63 | candidate equals baseline |
| `STABLE_translation_candidate_baseline_mismatches` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_translation_candidate_baseline_not_verified` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_candidate_prefix_observation_rows` | `PASS` | `stable_experiment_metric` | 123028 | 123028 | candidate equals baseline |
| `STABLE_candidate_step_audit_rows` | `PASS` | `stable_experiment_metric` | 63 | 63 | candidate equals baseline |
| `STABLE_candidate_step_all_trace_steps_recorded` | `PASS` | `stable_experiment_metric` | 63 | 63 | candidate equals baseline |
| `STABLE_candidate_step_missing_or_incomplete` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_candidate_prefix_carry_forward_steps` | `PASS` | `stable_experiment_metric` | 29989 | 29989 | candidate equals baseline |
| `STABLE_baseline_runs` | `PASS` | `stable_experiment_metric` | 67 | 67 | candidate equals baseline |
| `STABLE_baseline_timeouts` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_baseline_skipped_no_input` | `PASS` | `stable_experiment_metric` | 0 | 0 | candidate equals baseline |
| `STABLE_baseline_generated_empty_no_original_input` | `PASS` | `stable_experiment_metric` | 3 | 3 | candidate equals baseline |
| `STABLE_embedded_benchmark_records` | `PASS` | `stable_experiment_metric` | 53 | 53 | candidate equals baseline |
| `STABLE_workbook_status` | `PASS` | `stable_experiment_metric` | ok | ok | candidate equals baseline |
| `STABLE_manual_oracle_guide_rows` | `PASS` | `stable_manual_oracle_metric` | 10 | 10 | candidate equals baseline |
| `STABLE_manual_oracle_guide_p0` | `PASS` | `stable_manual_oracle_metric` | 7 | 7 | candidate equals baseline |
| `STABLE_manual_oracle_guide_p1` | `PASS` | `stable_manual_oracle_metric` | 3 | 3 | candidate equals baseline |
| `EXPECTED_REPRO_DELTA_reproducibility_manifest_rows` | `PASS` | `expected_reproducibility_growth` | 119 | 120 | candidate-baseline=1 |
| `EXPECTED_REPRO_DELTA_reproducibility_result_hashes` | `PASS` | `stable_reproducibility_metric` | 71 | 71 | candidate-baseline=0 |
| `EXPECTED_REPRO_DELTA_reproducibility_source_hashes` | `PASS` | `expected_reproducibility_growth` | 29 | 30 | candidate-baseline=1 |
| `EXPECTED_REPRO_DELTA_reproducibility_git_rows` | `PASS` | `stable_reproducibility_metric` | 6 | 6 | candidate-baseline=0 |
| `EXPECTED_VERIFIER_DELTA_check_rows` | `PASS` | `expected_verifier_growth` | 150 | 151 | candidate-baseline=1 |
| `EXPECTED_VERIFIER_DELTA_pass` | `PASS` | `expected_verifier_growth` | 150 | 151 | candidate-baseline=1 |
| `EXPECTED_VERIFIER_DELTA_warn` | `PASS` | `stable_verifier_metric` | 0 | 0 | candidate-baseline=0 |
| `EXPECTED_VERIFIER_DELTA_fail` | `PASS` | `stable_verifier_metric` | 0 | 0 | candidate-baseline=0 |
| `WORKBOOK_SHEET_DELTA` | `PASS` | `expected_workbook_growth` | ["Summary", "Review Guide", "Review Queue", "Review Signoff", "Signoff Evidence", "Signoff Validation", "Signoff Roundtrip", "Goal Audit", "Manual Review", "Correctness Audit", "Pr | ["Summary", "Review Guide", "Review Queue", "Review Signoff", "Signoff Evidence", "Signoff Validation", "Signoff Roundtrip", "Goal Audit", "Manual Review", "Correctness Audit", "Pr | added sheets=['MITL Runtime Catalog', 'MITL Semantic Catalog', 'MITL XML Candidates']; removed sheets=[] |
| `MANUAL_ORACLE_REQUIRED_IDS` | `PASS` | `expected_manual_oracle_growth` | <absent> | ["MOG_BASELINE_NOT_HAND_ORACLE", "MOG_BUILD_STATS_BOUNDARY", "MOG_DEFINITION", "MOG_FINAL_VERDICT", "MOG_FIX_POLICY", "MOG_INDEPENDENCE", "MOG_OPERATOR_SPOT_CHECK", "MOG_SAT_CHECK" | candidate manual oracle guide has 10 rows and required protocol IDs |
| `SIGNOFF_VALIDATION_PASS_BASELINE` | `PASS` | `stable_signoff_validation` | mode=pre-review/fail=0 | {'mode': 'pre-review', 'fail': 0} | both stable packets include passing generated signoff validation |
| `SIGNOFF_VALIDATION_PASS_CANDIDATE` | `PASS` | `stable_signoff_validation` | mode=pre-review/fail=0 | {'mode': 'pre-review', 'fail': 0} | both stable packets include passing generated signoff validation |
| `STABLE_SIGNOFF_mode` | `PASS` | `stable_signoff_validation` | pre-review | pre-review | candidate equals baseline |
| `STABLE_SIGNOFF_completion_state` | `PASS` | `stable_signoff_validation` | READY_FOR_HUMAN_REVIEW_NOT_SIGNED | READY_FOR_HUMAN_REVIEW_NOT_SIGNED | candidate equals baseline |
| `STABLE_SIGNOFF_validation_rows` | `PASS` | `stable_signoff_validation` | 16 | 16 | candidate equals baseline |
| `STABLE_SIGNOFF_pass` | `PASS` | `stable_signoff_validation` | 16 | 16 | candidate equals baseline |
| `STABLE_SIGNOFF_fail` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_signoff_rows` | `PASS` | `stable_signoff_validation` | 56 | 56 | candidate equals baseline |
| `STABLE_SIGNOFF_blank_decisions` | `PASS` | `stable_signoff_validation` | 56 | 56 | candidate equals baseline |
| `STABLE_SIGNOFF_nonblank_decisions` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_invalid_decisions` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_policy_mismatch_rows` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_forbidden_decision_rows` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_unresolved_evidence_tokens` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_missing_queue_evidence_rows` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_unresolved_queue_evidence_tokens` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_unresolved_source_sheet_tokens` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_unresolved_source_rows` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_unresolved_queue_source_sheet_tokens` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `STABLE_SIGNOFF_unresolved_queue_source_rows` | `PASS` | `stable_signoff_validation` | 0 | 0 | candidate equals baseline |
| `CSV_ROW_COUNT_semantic_regression_results_csv` | `PASS` | `stable_csv_row_count` | 87 | 87 | candidate-baseline=0 |
| `CSV_ROW_COUNT_semantic_prefix_oracle_review_csv` | `PASS` | `stable_csv_row_count` | 163 | 163 | candidate-baseline=0 |
| `CSV_ROW_COUNT_semantic_oracle_derivations_csv` | `PASS` | `stable_csv_row_count` | 87 | 87 | candidate-baseline=0 |
| `CSV_ROW_COUNT_mitl_correctness_audit_csv` | `PASS` | `stable_csv_row_count` | 150 | 150 | candidate-baseline=0 |
| `CSV_ROW_COUNT_mightyppl_syntax_coverage_audit_csv` | `PASS` | `stable_csv_row_count` | 45 | 45 | candidate-baseline=0 |
| `CSV_ROW_COUNT_formula_input_policy_audit_csv` | `PASS` | `stable_csv_row_count` | 8 | 8 | candidate-baseline=0 |
| `CSV_ROW_COUNT_cli_contract_audit_csv` | `PASS` | `stable_csv_row_count` | 11 | 11 | candidate-baseline=0 |
| `CSV_ROW_COUNT_benchmark_manifest_csv` | `PASS` | `stable_csv_row_count` | 23 | 23 | candidate-baseline=0 |
| `CSV_ROW_COUNT_monitaal_xml_inventory_csv` | `PASS` | `stable_csv_row_count` | 60 | 60 | candidate-baseline=0 |
| `CSV_ROW_COUNT_monitaal_translation_review_csv` | `PASS` | `stable_csv_row_count` | 23 | 23 | candidate-baseline=0 |
| `CSV_ROW_COUNT_monitaal_transition_details_csv` | `PASS` | `stable_csv_row_count` | 386 | 386 | candidate-baseline=0 |
| `CSV_ROW_COUNT_xml_edge_guard_proofs_csv` | `PASS` | `stable_csv_row_count` | 23 | 23 | candidate-baseline=0 |
| `CSV_ROW_COUNT_xml_proof_appendix_csv` | `PASS` | `stable_csv_row_count` | 23 | 23 | candidate-baseline=0 |
| `CSV_ROW_COUNT_translation_candidate_results_csv` | `PASS` | `stable_csv_row_count` | 63 | 63 | candidate-baseline=0 |
| `CSV_ROW_COUNT_candidate_prefix_observations_csv` | `PASS` | `stable_csv_row_count` | 123028 | 123028 | candidate-baseline=0 |
| `CSV_ROW_COUNT_candidate_step_audit_csv` | `PASS` | `stable_csv_row_count` | 63 | 63 | candidate-baseline=0 |
| `CSV_ROW_COUNT_monitaal_baseline_results_csv` | `PASS` | `stable_csv_row_count` | 67 | 67 | candidate-baseline=0 |
| `CSV_ROW_COUNT_review_guide_csv` | `PASS` | `stable_csv_row_count` | 15 | 15 | candidate-baseline=0 |
| `CSV_ROW_COUNT_goal_completion_audit_csv` | `PASS` | `stable_csv_row_count` | 17 | 17 | candidate-baseline=0 |
| `CSV_ROW_COUNT_manual_review_checklist_csv` | `PASS` | `stable_csv_row_count` | 17 | 17 | candidate-baseline=0 |
| `CSV_ROW_COUNT_paper_claim_consistency_audit_csv` | `PASS` | `stable_csv_row_count` | 23 | 23 | candidate-baseline=0 |
| `CSV_ROW_COUNT_requirements_traceability_audit_csv` | `PASS` | `stable_csv_row_count` | 23 | 23 | candidate-baseline=0 |
