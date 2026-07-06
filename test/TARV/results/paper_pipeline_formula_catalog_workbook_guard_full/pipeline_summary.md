# TAMonitor Full Review Pipeline

This file records a one-command execution of the TAMonitor paper-review pipeline.
It is reproducibility evidence only; human mathematical signoff is still recorded separately in the review workbook.

## Summary

- status: `PASS`
- mode: `full`
- started: `2026-07-06T20:20:09+08:00`
- finished: `2026-07-06T20:21:24+08:00`
- elapsed_ms: `78887`
- output directory: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full`
- timeout rerun directory: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full`
- workbook: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/paper_review_results.xlsx`
- failed steps: ``
- caveats: `experiment_baseline_generated_empty_no_original_input:3; experiment_goal_completion_pass_with_caveat:1; experiment_requirements_audit_pass_with_caveat:2; experiment_manual_review_pass_with_caveat:2; experiment_manual_review_review_required:4; experiment_goal_completion_review_required:2`

## Experiment Counts

- semantic_cases: `87`
- semantic_correctness_verified: `70`
- semantic_fail: `0`
- semantic_error: `0`
- semantic_timeout: `0`
- semantic_prefix_oracle_mismatch: `0`
- semantic_oracle_review_required: `0`
- manual_oracle_guide_rows: `10`
- manual_oracle_guide_p0: `7`
- syntax_coverage_missing: `0`
- cli_contract_fail: `0`
- baseline_runs: `67`
- baseline_timeouts: `0`
- baseline_generated_empty_no_original_input: `3`
- translation_candidate_baseline_matches: `63`
- translation_candidate_baseline_mismatches: `0`
- translation_candidate_baseline_not_verified: `0`
- human_review_queue_fail: `0`
- requirements_audit_fail: `0`
- workbook_status: `ok`

## Timeout Rerun

- selected_timeout_rows: `0`
- rerun_completed: `0`
- rerun_ran: `0`
- rerun_timeouts: `0`

## MoniTAal Hard-Coded Benchmarks

- row_count: `7`
- ran: `7`
- timeout: `0`
- error: `0`
- parse_failed: `0`
- binary_exists: `True`
- build_ok: `True`

## Packet Verification

- check_rows: `151`
- pass: `151`
- warn: `0`
- fail: `0`

## Signoff Evidence Bundle

- row_count: `56`
- pass: `56`
- warn: `0`
- fail: `0`
- missing_queue_rows: `0`
- missing_source_rows: `0`
- unresolved_evidence_tokens: `0`
- generated_only: `True`
- human_signoff_claim: `not_claimed`

## Signoff Import Roundtrip

- row_count: `7`
- pass: `7`
- warn: `0`
- fail: `0`
- expected_signoff_rows: `56`
- imported_nonblank_decisions: `56`
- synthetic_only: `True`
- human_signoff_claim: `not_claimed`

## Signoff Validation

- mode: `pre-review`
- completion_state: `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`
- validation_rows: `16`
- pass: `16`
- fail: `0`
- signoff_rows: `56`
- blank_decisions: `56`
- nonblank_decisions: `0`
- policy_mismatch_rows: `0`
- forbidden_decision_rows: `0`
- unresolved_evidence_tokens: `0`
- missing_queue_evidence_rows: `0`
- unresolved_queue_evidence_tokens: `0`
- unresolved_source_sheet_tokens: `0`
- unresolved_source_rows: `0`
- unresolved_queue_source_sheet_tokens: `0`
- unresolved_queue_source_rows: `0`

## Result Stability

- profile: `formula-catalog-integrated`
- rows: `190`
- pass: `190`
- warn: `0`
- fail: `0`

## Review Artifacts

- workbook: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/paper_review_results.xlsx`
- review_guide: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/review_guide.md`
- manual_oracle_guide: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/manual_oracle_guide.md`
- review_queue: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/human_review_queue.md`
- review_signoff_template: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/review_signoff_template.md`
- review_signoff_evidence_bundle: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/review_signoff_evidence_bundle.md`
- review_signoff_validation: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/review_signoff_validation.md`
- xml_proof_obligations: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/xml_proof_obligations.md`
- xml_trace_coverage_obligations: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/xml_trace_coverage_obligations.md`
- xml_original_trace_gaps: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/xml_original_trace_gaps.md`
- signoff_import_roundtrip_audit: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/signoff_import_roundtrip_audit.md`
- reproducibility_manifest: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/reproducibility_manifest.md`
- review_packet_verification: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/review_packet_verification.md`
- benchmark_blocker_diagnostics: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/benchmark_blocker_diagnostics.md`
- workbook_rebuild_summary: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/workbook_rebuild_summary.md`
- pipeline_artifact_manifest: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_artifact_manifest.md`
- pipeline_artifact_manifest_verification: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_artifact_manifest_verification.md`
- pipeline_summary: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_summary.md`
- monitaal_hardcoded_benchmarks: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/monitaal_hardcoded_benchmarks.md`
- result_stability_audit: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/result_stability_audit.md`
- timeout_rerun: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full/baseline_timeout_rerun.md`
- mitl_formula_catalog: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/mitl_formula_catalog_latest_official.md`
- mitl_formula_catalog_summary: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/mitl_formula_catalog_summary.json`

## Commands

| step | returncode | timeout | elapsed_ms | stdout | stderr |
|---|---:|---|---:|---|---|
| `py_compile_pipeline_scripts` | 0 | `False` | 121 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/py_compile_pipeline_scripts.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/py_compile_pipeline_scripts.stderr.txt` |
| `build_tamonitor` | 0 | `False` | 1987 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/build_tamonitor.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/build_tamonitor.stderr.txt` |
| `run_paper_experiments` | 0 | `False` | 30345 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/run_paper_experiments.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/run_paper_experiments.stderr.txt` |
| `validate_review_signoff` | 0 | `False` | 95 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/validate_review_signoff.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/validate_review_signoff.stderr.txt` |
| `build_signoff_evidence_bundle` | 0 | `False` | 42 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/build_signoff_evidence_bundle.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/build_signoff_evidence_bundle.stderr.txt` |
| `rerun_baseline_timeouts` | 0 | `False` | 52 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/rerun_baseline_timeouts.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/rerun_baseline_timeouts.stderr.txt` |
| `audit_signoff_import_roundtrip` | 0 | `False` | 22021 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/audit_signoff_import_roundtrip.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/audit_signoff_import_roundtrip.stderr.txt` |
| `analyze_benchmark_blockers` | 0 | `False` | 831 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/analyze_benchmark_blockers.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/analyze_benchmark_blockers.stderr.txt` |
| `run_monitaal_hardcoded_benchmarks` | 0 | `False` | 79 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/run_monitaal_hardcoded_benchmarks.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/run_monitaal_hardcoded_benchmarks.stderr.txt` |
| `build_mitl_formula_catalog` | 0 | `False` | 32 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/build_mitl_formula_catalog.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/build_mitl_formula_catalog.stderr.txt` |
| `rebuild_review_workbook_after_late_sidecars` | 0 | `False` | 16788 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/rebuild_review_workbook_after_late_sidecars.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/rebuild_review_workbook_after_late_sidecars.stderr.txt` |
| `verify_review_packet` | 0 | `False` | 4919 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/verify_review_packet.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/verify_review_packet.stderr.txt` |
| `compare_result_stability` | 0 | `False` | 1476 | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/compare_result_stability.stdout.txt` | `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/pipeline_command_logs/compare_result_stability.stderr.txt` |
