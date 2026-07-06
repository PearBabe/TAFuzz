# TAFuzz Project State

Last updated: 2026-07-05 16:19 CST. Latest official packet now includes
`MOG_INDEPENDENCE`, benchmark blocker diagnostics, the Excel
`Benchmark Blockers`, `Signoff Validation`, `Timeout Rerun Summary`, and
`Timeout Rerun` sheets, plus source hashes for all review-pipeline scripts.
Detailed pre-compaction state is
archived at:
`.codex/archive/PROJECT_STATE_20260705_pre_manifest_verification_compact.md`.
Older detailed archive:
`.codex/archive/PROJECT_STATE_20260705_pre_manual_oracle_guide.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Current status: TAMonitor v1 is implemented and exercised through a full
paper-review pipeline. Runtime verification uses MightyPPL flatten construction,
BDD-label valuation projection, and MoniTAal positive/negative monitor logic.
BDD-native runtime and compflatten runtime verdicts remain explicit v2/deferred
boundaries. The latest packet includes native result-stability audit,
review-signoff validation, final pipeline summaries, command logs, timeout
rerun evidence, and a pipeline-level artifact manifest plus a post-manifest
sidecar verifier. It also includes `MOG_INDEPENDENCE` in
`manual_oracle_guide.*`, making explicit that hand-oracle expectations must come
from MITL semantics and not from TAMonitor/MoniTAal agreement. The latest
pipeline runs `analyze_benchmark_blockers.py`, rebuilds the workbook after
blocker and timeout-rerun diagnostics, and hashes the final 34-sheet workbook
for review.

Do not mark the goal complete yet. Human `Review Signoff` is still blank, BDD
runtime is not implemented, compflatten runtime verdicts are unsupported in v1,
and timeout rows remain caveats.

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
- MightyPPL repo: `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`,
  `MightyPPLRuntimeOptions.cpp`.
- Added/modified project areas: `src/TAMonitor/`, `test/TARV/`,
  `analysis/tool_projects_deep_analysis.md`.

## Latest Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/pipeline_summary.md`
- Latest artifact manifest:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/pipeline_artifact_manifest.md`
- Latest artifact-manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/manual_oracle_guide.md`
- Latest benchmark blocker diagnostics:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/benchmark_blocker_diagnostics.md`
- Latest result-stability audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/result_stability_audit.md`
- Latest signoff validation:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full/review_signoff_validation.md`
- Latest 60-second timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_timeout_workbook_full`
- Previous stability baseline:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_source_hashes_full`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`
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
  comparable baseline match. Timeout, build-only, no-run, and timeout-caveat
  rows are not correctness evidence.
- Manual-oracle guide generation now includes `MOG_INDEPENDENCE`, requiring the
  expected verdict source to be independent of TAMonitor, MoniTAal, stdout
  parsing, and generated verdict summaries.
- `never_b.xml` is explicitly `not_claimed`: tested MightyPPL encodings do not
  match the MoniTAal TA's current-event boundary, so the old unsafe name-based
  `never_b -> G(!b)` heuristic is disabled.
- `time-must-pass.xml` is explicitly `not_claimed` as a time-divergence test,
  not an ordinary trace-level MITL benchmark formula.
- `run_full_review_pipeline.py` can run native stability auditing with
  `--stability-baseline` and `--stability-profile`; final summaries include
  `result_stability_audit`.
- `pipeline_artifact_manifest.csv/json/md` hashes final result files, command
  logs, and timeout-rerun files while excluding self/circular manifest rows.
- `verify_pipeline_artifact_manifest.py` is a post-manifest sidecar checker and
  is intentionally not included in the manifest it verifies.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_timeout_workbook_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_timeout_workbook_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_source_hashes_full --stability-profile timeout-rerun-workbook-added`

Pipeline status: `PASS`, mode `full`, elapsed 787975 ms, failed steps 0.
Explicit caveats: 8 baseline timeouts, 3 skipped-no-input XML rows, 7 candidate
baseline-not-verified rows, 8 rows still timing out in the 60-second rerun.

Key evidence counts:

- semantic: 70 cases, 53 runtime verified, 17 finite verified,
  36 infinite verified, fail/error/timeout 0/0/0.
- prefix oracle: 132 rows, 115 matches, 0 mismatches, 0 missing,
  28 carry-forward rows.
- oracle derivations: 70 rows, 53 `HAND_ORACLE_VERIFIED`,
  17 `CONSTRUCTION_STATS_ONLY`, 0 review-required, 0 prefix mismatch.
- manual oracle guide: 9 rows, 6 P0, 3 P1; includes `MOG_INDEPENDENCE`.
- syntax/input policy: 45 syntax rows with 0 missing; 8 internal Count-form
  probes; 8 controlled diagnostics; 0 assert-like failures.
- CLI contract: 10 direct TAMonitor probes, 10 PASS, 0 FAIL,
  5 controlled-error paths.
- review packet: Review Guide 13 rows; Review Queue 70 rows with 0 FAIL;
  Review Signoff 54 blank reviewer decisions.
- manual/goal/requirements: manual review 16 rows with 0 FAIL; goal audit
  17 rows with 0 FAIL; requirements audit 23 rows with 0 FAIL.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- candidate/baseline: 43/43 candidate runs succeeded; baseline
  matches/mismatches/not-verified 36/0/7; MoniTAal baselines 36 ran,
  8 timed out, 3 skipped no input.
- reproducibility manifest: 98 rows, 23 source hashes, 56 result hashes,
  6 git rows; includes all 10 `test/TARV/scripts` pipeline/review scripts.
- benchmark blocker diagnostics: 8 rows; classes
  `approximate_candidate_needs_edge_proof=4`, `no_conservative_candidate=2`,
  `current_event_boundary_no_candidate=1`, `time_divergence_not_trace_formula=1`.
- pipeline artifact manifest: 146 rows; categories `command_log=18`,
  `result_file=125`, `timeout_rerun_file=3`; includes timeout workbook CSVs
  and preview images.
- workbook: `ok`, 34 worksheets/tables including `Benchmark Blockers`,
  `Signoff Validation`, `Timeout Rerun Summary`, and `Timeout Rerun`.
- independent packet verifier: 70 PASS, 0 WARN, 0 FAIL.
- result stability audit: profile `timeout-rerun-workbook-added`, 148 PASS,
  0 WARN, 0 FAIL.
- signoff validation: 8 PASS, 0 FAIL, mode `pre-review`, completion state
  `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`, 54 blank decisions.
- pipeline artifact manifest verification: 10 PASS, 0 WARN, 0 FAIL;
  0 missing files, 0 bad hashes, 0 bad sizes.

## Latest Verification

Passed evidence:

- Full pipeline command above completed with `pipeline_status=PASS`.
- Native `compare_result_stability` used profile
  `timeout-rerun-workbook-added` and produced 148 PASS, 0 WARN, 0 FAIL.
- `analyze_benchmark_blockers.py` ran inside the full pipeline and produced
  8 blocker rows; `rebuild_review_workbook.py` then rebuilt the workbook so
  `Benchmark Blockers` appears in `paper_review_results.xlsx`.
- `manual_oracle_guide.md/csv` contain `MOG_INDEPENDENCE`, `decision_rule`, and
  `must_not_claim`; direct assertions confirmed the row is P0, section
  `independence`, and forbids substituting implementation agreement for a hand
  oracle.
- Independent packet verifier produced 70 PASS, 0 WARN, 0 FAIL and now requires
  blocker diagnostic files, the timeout-rerun workbook evidence sheets, and
  source hashes for all review-pipeline scripts.
- `validate_review_signoff.py` produced 8 PASS, 0 FAIL in pre-review mode.
- `verify_pipeline_artifact_manifest.py` produced 10 PASS, 0 WARN, 0 FAIL.
- Python compilation passed for pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`.
- Node syntax check passed for `build_paper_review_workbook.mjs`.
- `cmake --build tool/MightyPPL/build --target TAMonitor -j2` passed.
- `python3 -m json.tool` passed for key JSON artifacts.
- `unzip -t` passed for latest workbook.
- Direct packet assertions confirmed full PASS, nine pipeline commands in the
  expected order, verifier 70 PASS, stability 148 PASS, signoff validation 8/0,
  manifest 146 rows, 34 workbook sheets, 23 source hashes/10 script hashes,
  timeout workbook rows 8, semantic fail 0, prefix mismatch 0, candidate
  baseline mismatch 0, `MOG_INDEPENDENCE` present, and blocker diagnostics
  covered.
- `git -C tool/MightyPPL diff --check -- ...` passed.

Latest manifest verifier command:

`python3 test/TARV/scripts/verify_pipeline_artifact_manifest.py --output-dir test/TARV/results/paper_pipeline_timeout_workbook_full --timeout-rerun test/TARV/results/baseline_timeout_rerun_60s_timeout_workbook_full`

## Known Limits / Risks

- BDD-native runtime is not implemented in v1.
- `compflatten` runtime verdicts are not claimed in v1.
- 7 candidate MITL rows lack comparable original-input baseline verdict because
  MoniTAal baseline timed out.
- 8 MoniTAal baseline runs timed out even with the 60-second rerun; 3 XML rows
  have no input. These remain caveats, not correctness evidence.
- Gear-controller original long inputs still time out; reduced/generated traces
  are trace-level validation aids only.
- `f(g(notb)_and_g(f(a)).xml` remains excluded from formal claims until a real
  edge/guard proof and liveness/finite-prefix review are complete.
- `xml_proof_appendix.csv` is a draft proof ledger, not a final theorem.
- `Review Signoff` is blank by design. Blank reviewer decisions mean ready for
  human review, not completed human review.

## Next Steps

1. Start manual review from `pipeline_summary.md`, workbook `Review Guide`,
   `Manual Oracle Guide`, `Benchmark Blockers`, `Timeout Rerun`,
   `Review Queue`, and `Review Signoff`.
2. Keep timeout rows as caveats unless a longer justified baseline campaign is
   explicitly required.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full`；
60 秒 timeout 补充重跑目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_timeout_workbook_full`。
