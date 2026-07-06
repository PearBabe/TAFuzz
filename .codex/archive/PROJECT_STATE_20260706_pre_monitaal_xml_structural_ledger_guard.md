# TAFuzz Project State

Last updated: 2026-07-06 02:38 CST.

Older detailed states are archived under `.codex/archive/`, especially
`PROJECT_STATE_20260706_pre_gap_signoff_closure.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full paper-review
pipeline. Runtime uses MightyPPL flatten construction, BDD-label valuation
projection, and MoniTAal positive/negative monitor logic.

Do not mark the goal complete. Human `Review Signoff` is still blank,
BDD-native runtime is metadata/interface only, compflatten runtime verdicts are
unsupported in v1, and XML-to-MITL proof-ready rows still require human
mathematical review.

## Workspace Boundaries

- Workspace: `/home/lqq/project/TAFuzz`; top level is not a normal Git repo.
- Nested repos: `tool/MightyPPL` and `tool/MoniTAal`.
- Handoff files live at the TAFuzz root.
- Preserve unrelated user work; do not revert dirty changes.

## Current Local Changes To Preserve

- Handoff: `.codex/PROJECT_STATE.md`, `.codex/SESSION_LOG.md`,
  `.codex/archive/`.
- MoniTAal: `tool/MoniTAal/src/monitaal-bin/main.cpp`,
  `tool/MoniTAal/benchmark/main.cpp`.
- MightyPPL: `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`,
  `MightyPPLRuntimeOptions.cpp`.
- Project additions/experiments: `src/TAMonitor/`, `test/TARV/`,
  `analysis/tool_projects_deep_analysis.md`.

## Latest Official Artifacts

- Full packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full`
- Timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_candidate_prefix_observations_guard_full`
- Workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full/paper_review_results.xlsx`
- Pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full/pipeline_summary.md`
- Review packet verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full/review_packet_verification.md`
- Artifact manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full/pipeline_artifact_manifest_verification.md`
- XML original trace gaps:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full/xml_original_trace_gaps.md`
- Review Signoff template:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full/review_signoff_template.md`

## Latest Full Run

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_candidate_prefix_observations_guard_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_workbook_rebuild_summary_guard_full --stability-profile candidate-prefix-observations-guard-added`

Result:

- Pipeline: `PASS`, full mode, failed steps 0, elapsed 71977 ms.
- Semantic regression: 87 cases, 70 runtime verified, 0 fail/error/timeout.
- Prefix oracle: 163 rows, 146 matches, 0 mismatches, 34 carry-forward rows.
- Candidate/baseline: 63/63 candidate runs succeeded and matched MoniTAal;
  baseline runs 67, timeouts 0, generated-empty baseline-only probes 3.
- XML proof obligations: 143 rows, 126 PASS, 17 REVIEW_REQUIRED, 0 FAIL.
- XML trace coverage: 114 rows, 106 PASS, 8 REVIEW_REQUIRED, 0 FAIL.
- XML original trace gaps: 8 rows, all REVIEW_REQUIRED, 0 FAIL; classes are
  2 `no_repository_input_found` and 6 `repository_input_inconclusive`.
- Human review queue: 72 rows, 55 human-required, 44 P0.
- Review Signoff template: 56 blank rows, 44 P0. The 8
  `XML_ORIGINAL_TRACE_GAP_*` rows all recommend `APPROVE_WITH_CAVEAT` and
  forbid `APPROVE_AS_CLAIMED`.
- Manual Oracle Guide: 10 rows, 7 P0. New row
  `MOG_BASELINE_NOT_HAND_ORACLE` states that MoniTAal XML baseline agreement is
  trace-level cross-tool evidence, not a hand-derived MITL semantic oracle.
- Workbook: valid zip, 40 sheets including `Original Trace Gaps`.
- Review packet verifier: 123 PASS, 0 WARN, 0 FAIL. New guard
  `CANDIDATE_PREFIX_OBSERVATIONS_AUDIT` observed `violations=none`.
- Artifact manifest verifier: 16 PASS, 0 WARN, 0 FAIL, 138 manifest rows.
- Stability audit: profile `candidate-prefix-observations-guard-added`,
  181 PASS, 0 WARN, 0 FAIL, expected verifier delta +3.
- Signoff validation: 16 PASS, 0 FAIL, pre-review mode, 56 blank decisions.
- Signoff evidence bundle: 56 PASS, 0 FAIL, generated-only.
- Signoff import roundtrip: 7 PASS, 0 FAIL, synthetic-only,
  imported_nonblank_decisions 56.
- Hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error/timeout.
- Candidate prefix raw evidence: 123028 rows; 63/63 candidate step audits have
  all trace steps recorded; 29989 carry-forward rows.
- Workbook preview manifest: 40 rows, all `skipped` by OOM-safe preview policy,
  with every sheet mapped to an existing source CSV and matching row/column
  shape.

## Latest Fixes

- Added dedicated `xml_original_trace_gaps.csv/json/md` artifacts and workbook
  sheet `Original Trace Gaps`.
- Added explicit `XML_ORIGINAL_TRACE_GAP_*` human queue and signoff rows so the
  provenance gaps are first-class manual-review items.
- Added a real embedded MoniTAal unit-test timed word for `c_after_10.xml` from
  `tool/MoniTAal/test/Monitor_test.cpp::intersection_test2`. The trace
  `@0 a; @5 c; @15 c; @20 b` is now recorded as
  `embedded_benchmark_input`, matches MoniTAal and TAMonitor as `POSITIVE`,
  and closes the `c_after_10_positive_negative` original-trace gap.
- Propagated unresolved original-trace gaps into `paper_claim_review.csv` via
  `original_trace_gap_boundary`; paper-facing claim signoff rows linked to
  unresolved gaps now recommend `APPROVE_WITH_CAVEAT` and forbid
  `APPROVE_AS_CLAIMED`.
- Added packet guard `PAPER_CLAIM_ORIGINAL_TRACE_GAP_CAVEAT_AUDIT` and
  stability profile `embedded-c-after10-original-trace-added`.
- Added packet guard `EMBEDDED_C_AFTER10_PROVENANCE_AUDIT`, added
  `monitaal_embedded_benchmarks.csv` to required/hash-covered packet files, and
  added stability profile `embedded-c-after10-provenance-guard-added`. This
  fails if the c_after_10 embedded evidence drifts away from
  `tool/MoniTAal/test/Monitor_test.cpp::intersection_test2`, the exact
  transcribed input `@0 a; @5 c; @15 c; @20 b`, the MoniTAal baseline row, the
  TAMonitor candidate row, or the XML trace-coverage row.
- Added `MOG_BASELINE_NOT_HAND_ORACLE` to `Manual Oracle Guide`, required it in
  `MANUAL_ORACLE_GUIDE_PROTOCOL`, and added stability profile
  `manual-oracle-baseline-boundary-added`. This prevents review or paper text
  from treating MoniTAal/TAMonitor agreement as a hand oracle.
- Added packet verifier guard `BASELINE_MATCH_NOT_HAND_ORACLE_BOUNDARY` and
  stability profile `baseline-match-oracle-boundary-guard-added`. This checks
  every `translation_candidate_results.csv` row with
  `oracle_type=monitaal_xml_baseline_same_input` keeps trace-level caveat text
  and never calls MoniTAal baseline agreement a hand/manual oracle or automatic
  XML-to-MITL equivalence proof.
- Added required packet files `workbook_preview_manifest.csv/json`, packet
  verifier guard `WORKBOOK_PREVIEW_MANIFEST_AUDIT`, and stability profile
  `workbook-preview-manifest-guard-added`. This checks CSV/JSON manifest
  equality, workbook sheet coverage, required review sheets, source CSV
  existence, source CSV row/column shape, and preview status/path consistency.
- Added required packet files `workbook_rebuild_summary.csv/json/md`, packet
  verifier guard `WORKBOOK_REBUILD_SUMMARY_AUDIT`, and stability profile
  `workbook-rebuild-summary-guard-added`. This checks final workbook rebuild
  summary consistency with experiment summary, workbook path, late sidecar CSVs,
  timeout rerun evidence, and late workbook sheets.
- Fixed `audit_signoff_import_roundtrip.py` so isolated temporary packet copies
  synchronize `experiment_summary` `output_dir` and `workbook_path` before
  complete-mode import/rebuild/verification. The new rebuild-summary guard
  exposed this real path-consistency bug during the first full rerun.
- Added required packet files `candidate_prefix_observations.csv` and
  `candidate_step_audit.csv`, packet verifier guard
  `CANDIDATE_PREFIX_OBSERVATIONS_AUDIT`, and stability profile
  `candidate-prefix-observations-guard-added`. This checks raw prefix row
  counts, carry-forward counts, per-candidate mapped/processed/observed step
  counts, candidate/step/prefix ID alignment, final prefix verdicts, and
  row-by-row consistency with each candidate run's `steps.csv`.
- Added packet verifier guard `XML_ORIGINAL_TRACE_GAP_SIGNOFF_AUDIT`.
- Fixed `run_full_review_pipeline.py` so it runs
  `verify_pipeline_artifact_manifest.py` as a post-manifest sidecar and fails
  if manifest verification fails.
- Fixed `audit_signoff_import_roundtrip.py` hardcoded 47-row workbook import
  expectation; it now uses the current signoff row count.
- Previous fixes include XML trace-coverage three-valued semantics, generated
  boundary traces, MoniTAal EOF handling, workbook preview OOM guard, and
  evidence-caveat wording.

## Verification Commands Passed

- Full run command above.
- Focused verifier probe
  `test/TARV/results/candidate_prefix_observations_guard_probe` copied the
  previous packet and produced 123 PASS, 0 WARN, 0 FAIL; new guard
  `CANDIDATE_PREFIX_OBSERVATIONS_AUDIT` observed `violations=none`.
- Focused stability probe comparing that copied packet against the previous
  official packet with profile `candidate-prefix-observations-guard-added`
  produced 181 PASS, 0 WARN, 0 FAIL and expected verifier delta +3.
- Focused verifier probe
  `test/TARV/results/workbook_rebuild_summary_guard_probe` copied the previous
  packet and produced 120 PASS, 0 WARN, 0 FAIL; new guard
  `WORKBOOK_REBUILD_SUMMARY_AUDIT` observed `violations=none`.
- Focused stability probe comparing that copied packet against the previous
  official packet with profile `workbook-rebuild-summary-guard-added`
  produced 180 PASS, 0 WARN, 0 FAIL and expected verifier delta +4.
- First full rerun with the new guard failed because complete-mode signoff
  roundtrip copied packets kept stale `experiment_summary` paths; after fixing
  `sync_copied_packet_summary_paths`, the clean full rerun above passed.
- Focused verifier probe
  `test/TARV/results/workbook_preview_manifest_guard_probe` copied the previous
  packet and produced 116 PASS, 0 WARN, 0 FAIL; new guard
  `WORKBOOK_PREVIEW_MANIFEST_AUDIT` observed `violations=none`.
- Focused stability probe comparing that copied packet against the previous
  official packet with profile `workbook-preview-manifest-guard-added`
  produced 180 PASS, 0 WARN, 0 FAIL and expected verifier delta +3.
- Focused verifier probe
  `test/TARV/results/baseline_match_oracle_boundary_guard_probe` copied the
  previous packet and produced 113 PASS, 0 WARN, 0 FAIL; new guard
  `BASELINE_MATCH_NOT_HAND_ORACLE_BOUNDARY` observed `violations=none`.
- `python3 -m py_compile` over changed Python pipeline scripts.
- Bundled Node `--check` for `build_paper_review_workbook.mjs`.
- `unzip -t` for latest workbook.
- Stale timeout phrase scan over latest packet and timeout rerun, excluding
  verifier/pipeline logs, found no matches.
- `git -C tool/MightyPPL diff --check` and
  `git -C tool/MoniTAal diff --check`.

## Known Limits / Risks

- Human `Review Signoff` is blank by design; current packet is ready for human
  review, not completed human review.
- XML-to-MITL proof-ready rows are proof drafts requiring human review.
- The 8 remaining original-trace gaps remain unresolved until a real decisive original
  timed-word input is found or a reviewer accepts the caveat.
- Remaining original-trace gap manifests are `c_after_20_positive_negative`,
  `only_ab_until10_positive_negative`, and six `gear-control-properties.xml`
  rows whose original `gear-control-input.txt` evidence is `INCONCLUSIVE`.
- Read-only explorer `Dirac` rechecked these 8 gaps on 2026-07-06 01:50 CST:
  `c_after_20.xml` and `only_ab_until10.xml` have no repository/embedded
  timed-word input or C++ status assertion; the six gear rows have the real
  repository input but only `INCONCLUSIVE` MoniTAal/TAMonitor verdicts, so they
  cannot be promoted to decisive original oracle evidence.
- Generated empty inputs are baseline-only probes, not original benchmark
  traces.
- BDD-native runtime and compflatten runtime are v2 work.
- `f(g(notb)_and_g(f(a)).xml` remains excluded pending a real edge/guard proof
  and liveness/finite-prefix review.

## Next Steps

1. Start manual review from `Review Guide`, `Manual Oracle Guide`,
   `XML Obligations`, `XML Trace Coverage`, `Original Trace Gaps`,
   `Paper Claim Review`, `Review Queue`, and `Review Signoff`.
2. If human decisions are filled, run `import_review_signoff.py`, then
   `validate_review_signoff.py --mode complete`, then
   `verify_review_packet.py --signoff-mode complete --timeout-rerun ...`.
3. Next automatable guard candidate from read-only explorer `Darwin`:
   `monitaal_transition_details.csv` row/count/reference coverage, or a general
   manual-checklist evidence-artifact resolution guard.
4. Keep rerunning the full pipeline after each script/evidence milestone and
   update this handoff plus `SESSION_LOG.md`.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_candidate_prefix_observations_guard_full`。
