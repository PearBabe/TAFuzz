# TAFuzz Project State

Last updated: 2026-07-05 14:20 CST

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Current status: TAMonitor v1 is implemented and exercised through a full
paper-review pipeline. Runtime verification uses MightyPPL flatten construction,
BDD-label valuation projection, and MoniTAal positive/negative monitor logic.
BDD-native runtime and compflatten runtime verdicts remain explicit v2/deferred
boundaries. The latest result packet now natively includes `Review Signoff`
validation in `pipeline_summary.json`, and the independent packet verifier
requires those validation artifacts. The full pipeline can now run the result
stability audit natively with a configured baseline/profile; the latest packet
records that audit directly in `pipeline_summary.json`. The latest packet also
adds a pipeline-level artifact manifest hashing final review artifacts, command
logs, and timeout-rerun files after all configured review steps complete. A
post-manifest sidecar verifier now rechecks that manifest's schema, required
coverage, hashes, sizes, command logs, and timeout-rerun rows.

## Latest Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/pipeline_summary.md`
- Latest pipeline artifact manifest:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/pipeline_artifact_manifest.md`
- Latest pipeline artifact manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/manual_oracle_guide.md`
- Latest result stability audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/result_stability_audit.md`
- Latest signoff validation:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/review_signoff_validation.md`
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest`
- Previous detailed active state archive:
  `.codex/archive/PROJECT_STATE_20260705_pre_manual_oracle_guide.md`

## Workspace Boundaries

- Active workspace: `/home/lqq/project/TAFuzz`; top-level workspace is not a
  normal Git repository.
- Nested repos: `/home/lqq/project/TAFuzz/tool/MightyPPL` and
  `/home/lqq/project/TAFuzz/tool/MoniTAal`.
- Handoff files live at the TAFuzz root, not inside nested tool repos.
- Preserve unrelated user work; do not revert dirty changes.

## Current Local Changes To Preserve

- Modified handoff files:
  `.codex/PROJECT_STATE.md`, `.codex/SESSION_LOG.md`
- Modified MightyPPL repo files:
  `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`
- Added/untracked:
  `src/TAMonitor/`, `test/TARV/`, `tool/MightyPPL/MightyPPLRuntimeOptions.cpp`,
  `analysis/tool_projects_deep_analysis.md`, `.codex/archive/`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/rerun_baseline_timeouts.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_review_packet.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_full_review_pipeline.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/compare_pipeline_results.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/validate_review_signoff.py`

## Implemented Decisions

- v1 runtime uses BDD valuation projection to canonical MoniTAal labels.
- BDD-native runtime is metadata/interface only; do not claim it is implemented.
- `compflatten` runtime is unsupported in v1; compflatten rows are build/stat
  only and never fake runtime verdicts.
- `CFn/COn/CGn/CHn` and starred variants are parser-visible internal compilation
  forms, not ordinary user-level MITL formulas.
- XML-to-MITL translation is conservative; proof-ready rows remain draft
  trace-level candidates requiring human review.
- Correctness labels are conservative: `VERIFIED` requires a hand oracle or a
  comparable baseline match. Timeout, build-only, no-run, and timeout-caveat
  rows are not correctness evidence.
- Stability comparison supports three profiles: `manual-oracle-added` for the
  historical packet growth, `verifier-signoff-added` for the verifier growth
  that requires signoff-validation artifacts, and `stable` for later packets
  that already contain those review layers. Stable-style profiles enforce
  normalized CSV content equality while ignoring only volatile runtime timing
  columns.
- `run_full_review_pipeline.py` supports native stability auditing via
  `--stability-baseline` and `--stability-profile`. It writes an interim
  candidate `pipeline_summary.json` for `compare_pipeline_results.py`, then
  rewrites the final summary with `result_stability_audit` evidence included.
- `run_full_review_pipeline.py` writes `pipeline_artifact_manifest.csv/json/md`
  after final summary generation. It hashes final result files, pipeline command
  logs, and matching timeout-rerun files while excluding the manifest itself.
- `verify_pipeline_artifact_manifest.py` is a post-manifest sidecar checker. It
  verifies manifest schema, row count, no self-hash rows, unique keys, file
  existence, sha256/size matches, review-critical artifact coverage, command
  log coverage, timeout-rerun coverage, and required categories.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_artifact_manifest_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_manual_oracle_full --stability-profile verifier-signoff-added`

Pipeline status: `PASS`, mode `full`, elapsed 761752 ms. Failed steps: none.
Caveats are explicit: 8 baseline timeouts, 3 skipped-no-input XML rows,
7 candidate baseline-not-verified rows, and 8 rows still timing out in the
60-second rerun.

Key counts:

- semantic: 70 cases, 53 runtime verified, 17 finite verified,
  36 infinite verified, semantic fail/error/timeout 0/0/0.
- prefix oracle: 132 rows, 115 matches, 0 mismatches, 0 missing,
  28 carry-forward rows.
- oracle derivations: 70 rows, 53 `HAND_ORACLE_VERIFIED`,
  17 `CONSTRUCTION_STATS_ONLY`, 0 review-required, 0 prefix mismatch.
- manual oracle guide: 8 rows, 5 P0, 3 P1; verifier checks required protocol
  rows for definition, prefix/final verdicts, build-only boundary, fix policy,
  and human signoff boundary.
- syntax/input policy: 45 syntax rows with 0 missing; 8 internal Count-form
  probes, 8 controlled diagnostics, 0 assert-like failures.
- CLI contract: 10 direct TAMonitor probes, 10 PASS, 0 FAIL,
  5 controlled-error paths.
- review packet: Review Guide 13 rows; Review Queue 70 rows with 0 FAIL;
  Review Signoff 54 blank reviewer decisions.
- manual/goal/requirements: manual review 16 rows with 0 FAIL; goal audit
  17 rows with 0 FAIL; requirements audit 23 rows with 0 FAIL.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- candidate/baseline: 43/43 candidate runs succeeded; baseline matches/
  mismatches/not-verified 36/0/7; MoniTAal baselines 36 ran, 8 timed out,
  3 skipped no input.
- reproducibility manifest: 91 rows, 16 source hashes, 56 result hashes,
  6 git rows.
- pipeline artifact manifest: 130 rows hashing final result files, command logs,
  and timeout-rerun files; direct assertions confirmed it includes final
  `pipeline_summary.*`, `review_packet_verification.*`,
  `review_signoff_validation.*`, `result_stability_audit.*`, workbook, and
  `compare_result_stability` command log hashes, with no self-hash rows.
- pipeline artifact manifest verification: 10 PASS, 0 WARN, 0 FAIL; 130
  manifest rows, categories `command_log=14`, `result_file=113`,
  `timeout_rerun_file=3`, and 0 missing files/bad hashes/bad sizes.
- workbook: `ok`, 30 worksheets and 30 tables.
- independent packet verifier: 64 PASS, 0 WARN, 0 FAIL; it now checks the
  presence of `review_signoff_validation.csv/json/md`, the pre-review PASS
  summary, and synchronization with the blank 54-row signoff template.
- result stability audit against `paper_pipeline_manual_oracle_full` using
  `--profile verifier-signoff-added`: 172 PASS, 0 WARN, 0 FAIL. This now
  includes normalized row-content equality for stable CSV evidence and confirms
  that adding native signoff-validation reporting plus 6 verifier checks did
  not alter semantic, prefix-oracle, CLI, benchmark, candidate, baseline, or
  claim-safety metrics. The audit was run as the native pipeline command
  `compare_result_stability`.
- signoff validation: 8 PASS, 0 FAIL in `pre-review` mode. It confirms the
  54-row `Review Signoff` template is structurally synced with the P0/P1/P2
  review queue, all reviewer-owned fields are blank, and completion state is
  `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`.

## Latest Verification

Passed:

- full pipeline command listed above.
- `compare_pipeline_results.py` was fixed after a caught compatibility bug:
  old `manual-oracle-added` comparisons no longer require
  `review_signoff_validation.json`, while `stable` comparisons require passing
  signoff validation in both packets.
- `verify_review_packet.py` now requires signoff-validation artifacts and checks
  `SIGNOFF_VALIDATION_SUMMARY_PASS`, `SIGNOFF_VALIDATION_ROW_COUNT`, and
  `SIGNOFF_VALIDATION_TEMPLATE_SYNC`.
- `run_full_review_pipeline.py` now includes optional native
  `compare_result_stability` execution and records `result_stability_audit`
  summary/options/artifacts in the final pipeline summary.
- `run_full_review_pipeline.py` now writes `pipeline_artifact_manifest.csv/json/md`
  after final pipeline outputs; this covers artifacts generated after the
  experiment-level reproducibility manifest.
- `verify_pipeline_artifact_manifest.py` was added and run on the latest packet.
- pipeline preflight `python3 -m py_compile` for experiment/verifier/pipeline
  scripts and `src/TAMonitor/make_tamonitor_xlsx.py`.
- bundled Node syntax check for `build_paper_review_workbook.mjs`.
- pipeline build step `cmake --build tool/MightyPPL/build --target TAMonitor -j2`.
- `python3 -m json.tool` for pipeline summary, experiment summary, verifier
  JSON, manual-oracle guide JSON, and timeout-rerun summary JSON.
- `unzip -t` for latest workbook.
- direct packet assertions: status `PASS`, mode `full`, no failed steps,
  verifier fail/warn 0/0, manual-oracle guide rows 8, P0 rows >= 5,
  `Manual Oracle Guide` workbook sheet present, semantic fail 0,
  prefix mismatch 0, candidate baseline mismatch 0.
- result stability audit command:
  `python3 test/TARV/scripts/compare_pipeline_results.py --profile
  verifier-signoff-added --baseline
  test/TARV/results/paper_pipeline_manual_oracle_full --candidate
  test/TARV/results/paper_pipeline_artifact_manifest_full`, producing
  `result_stability_audit.csv/json/md` with 172 PASS, 0 WARN, 0 FAIL.
- direct packet assertions confirmed `review_signoff_validation` is present in
  `pipeline_summary.json`, mode `pre-review`, completion state
  `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`, 8 PASS, 0 FAIL, 54 blank decisions,
  verifier 64 PASS, native `compare_result_stability` command present,
  pipeline artifact manifest 130 rows with no self-hash rows, 30 workbook
  sheets including `Manual Oracle Guide`, semantic fail 0, prefix mismatch 0,
  and candidate baseline mismatch 0.
- manifest verifier command:
  `python3 test/TARV/scripts/verify_pipeline_artifact_manifest.py --output-dir
  test/TARV/results/paper_pipeline_artifact_manifest_full --timeout-rerun
  test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest`, producing
  `pipeline_artifact_manifest_verification.csv/json/md` with 10 PASS,
  0 WARN, 0 FAIL.
- `git -C tool/MightyPPL diff --check -- ...` passed.

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

1. Start manual review from `pipeline_summary.md`, then workbook sheets
   `Review Guide`, `Manual Oracle Guide`, `Review Queue`, and `Review Signoff`.
2. Keep timeout rows as caveats unless a longer justified baseline campaign is
   explicitly required.
3. If paper claims expand beyond operator-level finite regressions, add
   theorem-specific finite-word hand-oracle cases.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full`；
60 秒 timeout 补充重跑目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest`。
