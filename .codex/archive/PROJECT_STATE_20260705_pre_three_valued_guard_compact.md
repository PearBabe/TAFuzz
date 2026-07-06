# TAFuzz Project State

Last updated: 2026-07-05 17:50 CST.

Detailed pre-fix state is archived at:
`.codex/archive/PROJECT_STATE_20260705_pre_monitaal_eof_fix.md`.
Older archives:
`.codex/archive/PROJECT_STATE_20260705_pre_manifest_verification_compact.md`;
`.codex/archive/PROJECT_STATE_20260705_pre_manual_oracle_guide.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full
paper-review pipeline. Runtime uses MightyPPL flatten construction, BDD-label
valuation projection, and MoniTAal positive/negative monitor logic. Real bugs
found during experiments have been fixed and promoted: MoniTAal file-mode EOF
plus `INCONCLUSIVE` no longer spins forever; workbook previews no longer crash
on wide/large sheets; generated-empty XML baseline probes are disclosed; and
MoniTAal `benchmark/main.cpp` hard-coded benchmark entrypoints now have a
separate evidence path, workbook sheet, packet verifier checks, and artifact
manifest coverage; finite-word hand-oracle coverage was broadened across all
user-level MightyPPL runtime syntax rows, and TAMonitor finite monitoring no
longer exposes a fourth `INCONSISTENT` verdict.

Do not mark the goal complete yet. Human `Review Signoff` is still blank,
BDD-native runtime is not implemented, compflatten runtime verdicts are
unsupported in v1, and XML-to-MITL proof-ready rows still require human review.

## Workspace Boundaries

- Active workspace: `/home/lqq/project/TAFuzz`; top level is not a normal Git
  repository.
- Nested repos: `/home/lqq/project/TAFuzz/tool/MightyPPL` and
  `/home/lqq/project/TAFuzz/tool/MoniTAal`.
- Handoff files live at the TAFuzz root, not inside nested tool repos.
- Preserve unrelated user work; do not revert dirty changes.

## Current Local Changes To Preserve

- Handoff: `.codex/PROJECT_STATE.md`, `.codex/SESSION_LOG.md`,
  `.codex/archive/`.
- MoniTAal: `tool/MoniTAal/src/monitaal-bin/main.cpp` EOF loop fix and
  `tool/MoniTAal/benchmark/main.cpp` benchmark seed-output newline fix.
- MightyPPL repo: `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`,
  `MightyPPLRuntimeOptions.cpp`.
- Added/modified project areas: `src/TAMonitor/`, `test/TARV/`,
  `analysis/tool_projects_deep_analysis.md`.
- Current experiment script changes include generated-empty input disclosure,
  hard-coded benchmark sidecar evidence, stricter verifier checks, profile-aware
  stability deltas, finite/infinite syntax-oracle coverage, benchmark-manifest
  input-origin counts, artifact-manifest hardcoded coverage checks, and
  allowlisted workbook previews.

## Latest Official Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/pipeline_summary.md`
- Latest artifact manifest:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/pipeline_artifact_manifest.md`
- Latest artifact-manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/manual_oracle_guide.md`
- Latest benchmark blocker diagnostics:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/benchmark_blocker_diagnostics.md`
- Latest hard-coded MoniTAal benchmark evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/monitaal_hardcoded_benchmarks.md`
- Latest result-stability audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/result_stability_audit.md`
- Latest signoff validation:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full/review_signoff_validation.md`
- Latest timeout rerun evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_finite_syntax_oracles_full`
- Previous official baseline:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_hardcoded_benchmarks_manifest_full`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal-bin/main.cpp`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/main.cpp`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_monitaal_hardcoded_benchmarks.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/rebuild_review_workbook.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/rerun_baseline_timeouts.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_review_packet.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_pipeline_artifact_manifest.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_full_review_pipeline.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/compare_pipeline_results.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/analyze_benchmark_blockers.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/validate_review_signoff.py`

## Implemented Decisions

- v1 runtime uses BDD valuation projection to canonical MoniTAal labels.
- BDD-native runtime is metadata/interface only; do not claim implementation.
- `compflatten` runtime is build/stat only in v1; do not fake verdicts.
- `CFn/COn/CGn/CHn` and starred variants are parser-visible internal Count
  compilation forms, not ordinary user-level MITL formulas.
- XML-to-MITL translation is conservative. Proof-ready rows remain draft
  trace-level candidates requiring human review.
- Correctness labels are conservative: `VERIFIED` requires a hand oracle or a
  comparable baseline match.
- Manual-oracle guide includes `MOG_INDEPENDENCE`: hand-oracle expectations
  must come from MITL semantics, not TAMonitor/MoniTAal agreement.
- `never_b.xml` is `not_claimed`; current-event boundary did not match tested
  MITL encodings.
- `time-must-pass.xml` is `not_claimed` as a time-divergence test, not an
  ordinary trace-level MITL benchmark formula.
- MoniTAal XML-file baselines classify exit code `1` with verdict
  `INCONCLUSIVE` as `ran/INCONCLUSIVE`, not timeout or failure.
- Generated empty inputs named `no_original_input_*` are baseline-only probes
  for XML pairs with no repository input; never cite them as original benchmark
  traces or XML-to-MITL equivalence proofs.
- Workbook PNG previews are allowlisted review aids. Full evidence remains in
  CSV/XLSX sheets; skipped previews are recorded in `workbook_preview_manifest`.
- `monitaal-benchmark` is a separate hard-coded benchmark path using C++ models
  and delay/testing monitors. Do not conflate it with XML-file
  `MoniTAal-bin` baseline evidence.
- Finite monitor overlap/gap states are exposed conservatively as
  `INCONCLUSIVE`; TAMonitor public RV verdicts stay three-valued.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_finite_syntax_oracles_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_finite_syntax_oracles_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_hardcoded_benchmarks_manifest_full --stability-profile finite-syntax-oracles-added`

Pipeline status: `PASS`, full mode, elapsed 48311 ms, failed steps 0.
Explicit caveats exclude baseline timeouts and skipped-no-input rows. Remaining
caveats are 3 generated-empty baseline-only probes, blank human signoff,
proof-review gates, and v2 deferrals.

Key counts:

- semantic: 87 cases, 70 runtime verified, 34 finite verified,
  36 infinite verified, fail/error/timeout 0/0/0.
- prefix oracle: 163 rows, 146 matches, 0 mismatches, 0 missing,
  34 carry-forward rows.
- oracle derivations: 87 rows, 70 `HAND_ORACLE_VERIFIED`,
  17 `CONSTRUCTION_STATS_ONLY`, 0 review-required, 0 prefix mismatch.
- syntax/input policy: 45 syntax rows with 36 user-level runtime rows verified
  in both finite and infinite modes, 0 missing; 8 internal Count-form probes;
  8 controlled diagnostics; 0 assert-like failures.
- CLI contract: 10 direct TAMonitor probes, 10 PASS, 0 FAIL.
- review packet: Review Guide 13 rows; Review Queue 63 rows with 0 FAIL;
  Review Signoff 47 blank reviewer decisions.
- manual/goal/requirements: manual review 16 rows with 0 FAIL; goal audit
  17 rows with 0 FAIL; requirements audit 23 rows with 0 FAIL.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- candidate/baseline: 43/43 candidate runs succeeded; baseline
  matches/mismatches/not-verified 43/0/0; MoniTAal baselines 47 ran,
  0 timed out, 0 skipped no input, 3 generated-empty baseline-only probes.
- paper claim review: 15 body-pattern-ready-after-human-signoff rows,
  0 appendix timeout-caveat rows, 8 excluded rows.
- hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error, 0 timeout,
  separate from XML-to-MITL equivalence claims; workbook sheet present.
- reproducibility manifest: 101 rows, 26 source hashes, 56 result hashes,
  6 git rows; includes `tool/MoniTAal/src/monitaal-bin/main.cpp`,
  `tool/MoniTAal/benchmark/main.cpp`, and hardcoded sidecar scripts.
- timeout rerun: 0 available timeout rows, 0 selected, 0 rerun timeouts.
- workbook: `ok`, 35 worksheets/tables including `Hardcoded Benchmarks`,
  `Benchmark Blockers`, `Signoff Validation`, `Timeout Rerun Summary`, and
  `Timeout Rerun`.
- independent packet verifier: 75 PASS, 0 WARN, 0 FAIL.
- result stability audit: profile `finite-syntax-oracles-added`, 149 PASS,
  0 WARN, 0 FAIL.
- signoff validation: 8 PASS, 0 FAIL, mode `pre-review`, completion state
  `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`.
- pipeline artifact manifest verification: 11 PASS, 0 WARN, 0 FAIL;
  133 manifest rows, 0 missing files, 0 bad hashes, 0 bad sizes; includes
  explicit `MANIFEST_HARDCODED_BENCHMARK_COVERAGE`.
- workbook preview manifest: 13 rendered review-entry previews and 21 skipped
  full-evidence sheets; skipped previews remain available as XLSX/CSV data.

## Latest Verification

Passed evidence:

- Full pipeline command above completed with `pipeline_status=PASS`.
- `verify_review_packet.py` produced 75 PASS/0 FAIL, including
  `HARDCODED_BENCHMARK_BOUNDARY` and `BASELINE_GENERATED_EMPTY_BOUNDARY`.
- `compare_pipeline_results.py --profile finite-syntax-oracles-added` produced
  149 PASS/0 FAIL and allowed only the expected finite syntax-oracle additions.
- `verify_pipeline_artifact_manifest.py` produced 11 PASS/0 FAIL with
  133 manifest rows and explicit hardcoded benchmark coverage.
- JSON parsing passed for pipeline/experiment/verifier/stability/timeout
  summary artifacts.
- `unzip -t` passed for the workbook.
- Direct assertions passed for 47 baseline runs, 0 baseline timeouts,
  0 skipped-no-input rows, 3 generated-empty `ran/INCONCLUSIVE` rows,
  43/43 candidate baseline matches, 70 hand-oracle runtime rows, 34 finite
  verified rows, 36 syntax runtime rows with finite+infinite evidence, 0
  `INCONSISTENT` runtime verdicts, 7/7 hard-coded benchmark rows ran/parsed,
  and 35 workbook sheets including `Hardcoded Benchmarks`.
- Python compilation passed for pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`.
- Bundled Node `--check` passed for `build_paper_review_workbook.mjs`.
- `git -C tool/MoniTAal diff --check -- src/monitaal-bin/main.cpp benchmark/main.cpp` passed.
- `git -C tool/MightyPPL diff --check -- ...` passed.

## Known Limits / Risks

- BDD-native runtime is not implemented in v1.
- `compflatten` runtime verdicts are not claimed in v1.
- Human `Review Signoff` is blank by design; blank decisions mean ready for
  human review, not completed human review.
- XML-to-MITL proof-ready rows are still proof drafts requiring human review.
- 3 XML rows use generated empty timed-word probes because no repository input
  exists; these are baseline-only evidence, not original benchmark traces.
- `f(g(notb)_and_g(f(a)).xml` remains excluded until a real edge/guard proof
  and liveness/finite-prefix review are complete.
- `xml_proof_appendix.csv` is a draft proof ledger, not a final theorem.

## Next Steps

1. Start human review from the latest workbook's `Review Guide`,
   `Manual Oracle Guide`, `Benchmark Manifest`, `Baseline Results`,
   `Hardcoded Benchmarks`, `Benchmark Blockers`, `Paper Claim Review`,
   `Review Queue`, and `Review Signoff`.
2. Keep BDD-native runtime and compflatten runtime as v2 work until real
   algorithms and oracle suites are implemented.
3. Preserve the evidence boundary: `Hardcoded Benchmarks` is executable
   MoniTAal C++ benchmark evidence, not XML-to-MITL equivalence proof.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_finite_syntax_oracles_full`。
