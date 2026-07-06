# TAFuzz Project State

Last updated: 2026-07-06 01:11 CST.

Older detailed states are archived under `.codex/archive/`, including
`PROJECT_STATE_20260705_pre_evidence_consistency.md` and
`PROJECT_STATE_20260706_pre_trace_coverage_compact.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full paper-review
pipeline. Runtime uses MightyPPL flatten construction, BDD-label valuation
projection, and MoniTAal positive/negative monitor logic. Experiments continue
to drive real fixes, stronger review evidence, and more machine-checkable
coverage.

Do not mark the goal complete yet. Human `Review Signoff` is blank,
BDD-native runtime is metadata/interface only, compflatten runtime verdicts are
unsupported in v1, and XML-to-MITL proof-ready rows still require human
mathematical review.

## Workspace Boundaries

- Workspace: `/home/lqq/project/TAFuzz`; top level is not a normal Git repo.
- Nested repos: `tool/MightyPPL` and `tool/MoniTAal`.
- Handoff files live at the TAFuzz root, not inside nested tool repos.
- Preserve unrelated user work; do not revert dirty changes.

## Current Local Changes To Preserve

- Handoff: `.codex/PROJECT_STATE.md`, `.codex/SESSION_LOG.md`,
  `.codex/archive/`.
- MoniTAal: `tool/MoniTAal/src/monitaal-bin/main.cpp` EOF/INCONCLUSIVE guard
  and `tool/MoniTAal/benchmark/main.cpp` benchmark seed-output newline fix.
- MightyPPL: `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`,
  `MightyPPLRuntimeOptions.cpp`.
- Project additions/experiments: `src/TAMonitor/`, `test/TARV/`,
  `analysis/tool_projects_deep_analysis.md`.
- Latest experiment scripts add XML proof obligations, XML trace coverage,
  boundary/generated review inputs, three-valued XML coverage fixes, dedicated
  original-trace gap artifacts, workbook preview robustness, packet/manifest
  guards, and stability profiles through `xml-original-trace-gaps-added`.

## Latest Official Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/pipeline_summary.md`
- Latest review packet verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/review_packet_verification.md`
- Latest artifact manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/pipeline_artifact_manifest_verification.md`
- Latest signoff evidence bundle:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/review_signoff_evidence_bundle.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/manual_oracle_guide.md`
- Latest XML proof obligations:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/xml_proof_obligations.md`
- Latest XML trace coverage obligations:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/xml_trace_coverage_obligations.md`
- Latest XML original trace gaps:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2/xml_original_trace_gaps.md`
- Latest timeout rerun evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gaps_full_v2`
- Stability baseline for latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_boundary_traces_full`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal-bin/main.cpp`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/main.cpp`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_review_packet.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_pipeline_artifact_manifest.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/compare_pipeline_results.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_full_review_pipeline.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`

## Implemented Decisions

- v1 runtime uses BDD valuation projection to canonical MoniTAal labels.
- BDD-native runtime is metadata/interface only; do not claim implementation.
- `compflatten` runtime is build/stat only in v1; do not fake verdicts.
- `CFn/COn/CGn/CHn` and starred variants are internal Count compilation forms,
  not ordinary user-level MITL formulas.
- XML-to-MITL translation is conservative. Proof-ready rows remain draft
  trace-level candidates requiring human review.
- Correctness labels are conservative: `VERIFIED` requires a hand oracle or a
  comparable baseline match.
- Manual-oracle expectations must come from MITL semantics, not from
  TAMonitor/MoniTAal agreement.
- Generated empty inputs named `no_original_input_*` are baseline-only probes,
  not original benchmark traces or XML-to-MITL equivalence proofs.
- INCONCLUSIVE baseline rows are third-valued trace evidence, not Boolean
  satisfaction/violation and not XML-to-MITL equivalence proofs.
- Rows with INCONCLUSIVE evidence require explicit caveats and forbid
  `APPROVE_AS_CLAIMED`; use `APPROVE_WITH_CAVEAT` if a human accepts them.
- Human-filled signoff import copies only reviewer decision/date/name/notes;
  generated queue/evidence/policy fields must match the current packet.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2 --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gaps_full_v2 --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_xml_three_valued_coverage_full_v3 --stability-profile xml-original-trace-gaps-added`

Pipeline status: `PASS`, full mode, elapsed 66073 ms, failed steps 0.

Key counts:

- semantic: 87 cases, 70 runtime verified, fail/error/timeout 0/0/0.
- prefix oracle: 163 rows, 146 matches, 0 mismatches, 0 missing,
  34 carry-forward rows.
- candidate/baseline: 62/62 candidate runs succeeded; baseline
  matches/mismatches/timeouts 62/0/0; MoniTAal baselines 66 ran,
  0 timeout, 3 generated-empty baseline-only probes.
- candidate step audit: 62 rows, 62 all trace steps recorded;
  candidate prefix observation rows 123024.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- XML proof obligations: 143 rows, 125 PASS, 18 REVIEW_REQUIRED, 0 FAIL.
- XML trace coverage obligations: 114 rows, 105 PASS, 9 REVIEW_REQUIRED,
  0 FAIL; all 15 proof-ready runtime-integrity rows PASS.
- XML original trace gaps: 9 rows, all REVIEW_REQUIRED, 0 FAIL,
  non-machine-checkable; classes are 3 `no_repository_input_found` and 6
  `repository_input_inconclusive`.
- hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error,
  0 timeout.
- workbook: `ok`, valid zip, 40 worksheets/tables including
  `Original Trace Gaps`. PNG previews are disabled
  by default to avoid optional renderer memory failures.
- signoff evidence bundle: 47 PASS, 0 FAIL, generated-only and not human
  approval.
- signoff import roundtrip audit: 7 PASS, 0 FAIL, synthetic workflow only.
- review packet verifier: 107 PASS, 0 WARN, 0 FAIL.
- signoff validation: 16 PASS, 0 FAIL, mode `pre-review`,
  completion state `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`; blank decisions 47.
- result stability audit: profile `xml-original-trace-gaps-added`,
  160 PASS, 0 WARN, 0 FAIL.
- artifact manifest verifier: 16 PASS, 0 WARN, 0 FAIL; 138 manifest rows,
  0 missing files, bad hashes, or bad sizes.

## Latest Verification

Passed evidence:

- Full v2 original-trace-gap pipeline completed with `pipeline_status=PASS`.
- `verify_review_packet.py --timeout-rerun ...` passed: 107 PASS/0 FAIL.
- `verify_pipeline_artifact_manifest.py --timeout-rerun ...` passed:
  16 PASS/0 FAIL, 138 manifest rows, no missing/bad hash/bad size.
- `unzip -t` passed for the latest workbook.
- Stale timeout phrase scan over latest packet and timeout-rerun packet found
  no matches.
- Stability audit passed for `xml-original-trace-gaps-added`: 160 PASS/0 FAIL.
- Python `py_compile` passed for changed pipeline scripts.
- Bundled Node `--check` passed for `build_paper_review_workbook.mjs`.
- Nested repo `diff --check` passed for modified MightyPPL and MoniTAal files.
- Read-only subagent `Laplace` independently confirmed the old
  `positive_verdict_trace_present`/`negative_verdict_trace_present`
  requirements were incorrect for infinite-word three-valued RV on G* and
  unbounded eventuality classes.

Real bugs/risks fixed or surfaced during the latest milestones:

- Fixed XML trace-coverage theory bug: finite prefixes of G* response,
  absence, recurrence, and gear request-response formulas should not be
  forced to `POSITIVE`; no-witness prefixes of `F [lower,infty)` should not be
  forced to `NEGATIVE`. Coverage now requires INCONCLUSIVE/non-violation
  evidence where MITL RV semantics demands it.
- Added generated traces for c-after no-witness INCONCLUSIVE, a-b re-arm late
  violations, absence re-arm boundary violations, and timely recurrence
  non-violation. All new candidate runs match MoniTAal baselines.
- Fixed `input_trace_purpose`: `safe_after_bound_positive` is now classified
  as after-bound non-violation evidence, not closed-bound positive.
- Added stability profile `xml-three-valued-coverage-fixed`.
- Fixed workbook robustness: artifact PNG preview generation is optional and
  disabled by default via `TAMONITOR_RENDER_WORKBOOK_PREVIEWS=1` opt-in. This
  avoids native renderer abort/OOM while preserving the 39-sheet Excel packet.
- Added dedicated original-trace gap artifacts and guards so the remaining 9
  provenance gaps are visible for manual review instead of buried in the trace
  coverage table.
- Fixed a real orchestration gap: `run_full_review_pipeline.py` now runs
  `verify_pipeline_artifact_manifest.py` as a post-manifest sidecar check and
  fails the command if artifact-manifest verification fails.
- Earlier boundary/trace and evidence-consistency fixes are recorded in
  `.codex/archive/PROJECT_STATE_20260706_pre_trace_coverage_compact.md` and
  previous SESSION_LOG entries.

## Known Limits / Risks

- BDD-native runtime is not implemented in v1.
- `compflatten` runtime verdicts are not claimed in v1.
- Human `Review Signoff` is blank by design; blank decisions mean ready for
  human review, not completed human review.
- XML-to-MITL proof-ready rows are still proof drafts requiring human review.
- 3 XML rows use generated empty timed-word probes because no repository input
  exists; these are baseline-only evidence, not original benchmark traces.
- The 9 remaining XML trace coverage REVIEW_REQUIRED rows are isolated in
  `xml_original_trace_gaps.*`: generated-only c-after/only-ab rows and gear
  repository traces whose original input remains INCONCLUSIVE.
- Repository search found no real `c_after_10`, `c_after_20`, or
  `only_ab_until10` timed-word input files; MoniTAal tests only load those XMLs
  as models. Gear has `gear-control-input.txt`, but its original long trace is
  correctly INCONCLUSIVE for the proof-ready request/response rows.
- `f(g(notb)_and_g(f(a)).xml` remains excluded until a real edge/guard proof
  and liveness/finite-prefix review are complete.
- `xml_proof_appendix.csv` is a draft proof ledger, not a final theorem.

## Next Steps

1. Continue automatable evidence work only where sound: look for real
   repository/original input traces that can close the 9
   `original_decisive_trace_boundary` gaps, without fabricating original
   benchmark evidence.
2. Re-run the full pipeline after each trace/script milestone with a matching
   stability profile and update this handoff plus `SESSION_LOG.md`.
3. Start human review from the latest workbook sheets: `Review Guide`,
   `Manual Oracle Guide`, `Benchmark Manifest`, `Baseline Results`,
   `Hardcoded Benchmarks`, `Benchmark Blockers`, `XML Obligations`,
   `XML Trace Coverage`, `Original Trace Gaps`, `Paper Claim Review`, `Review Queue`,
   `Review Signoff`, `Signoff Validation`, `Signoff Evidence`,
   `Signoff Roundtrip`, and `Review Packet Verification`.
4. After filling review decisions, use `import_review_signoff.py` on the latest
   packet, then run `validate_review_signoff.py --mode complete` and
   `verify_review_packet.py --signoff-mode complete --timeout-rerun ...`.
5. Keep BDD-native runtime and compflatten runtime as v2 work until real
   algorithms and oracle suites are implemented.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gaps_full_v2`。
