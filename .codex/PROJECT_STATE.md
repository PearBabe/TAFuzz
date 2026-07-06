# TAFuzz Project State

Last updated: 2026-07-06 20:52 CST.

This file is the active handoff source of truth. Read it before resuming work.

## Current Goal

Goal: 完整实现并验证 TAMonitor 论文级运行时验证扩展，保留可人工审查的最终实验结果，并清理中间结果。

Status: COMPLETE. Do not continue changing TAMonitor, benchmark experiments, XML-to-MITL review/signoff, BDD-native runtime, or compflatten runtime unless the user explicitly asks.

## Latest GitHub Publish

- Published branch: `codex/tafuzz-20260706-204744`.
- Latest pushed commit: `450ec460238bacb9f6e907805ad80a08ac3fd4d9`
  (`Publish TAMonitor v1 workspace`).
- Compare URL:
  `https://github.com/PearBabe/TAFuzz/compare/main...codex/tafuzz-20260706-204744?expand=1`.
- Draft PR creation through the GitHub connector failed with GitHub API 404,
  so the branch was pushed but no PR was created automatically.
- Publish used `--skip-build` after an initial build attempt failed in
  `tool/MightyPPL/build` because the external `antlr4_runtime` update step
  tried to check out `master` from the wrong Git context after generated build
  metadata cleanup. Existing final verification remains recorded below.
- GitHub warned that
  `test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/candidate_prefix_observations.csv`
  is 82.33 MB, above the recommended 50 MB threshold but below the hard push
  limit.

## Completed v1 Runtime Scope

- MightyPPL parses supported user MITL formulas and builds flatten timed automata.
- TAMonitor builds positive/negative automata for `phi` and `!(phi)`.
- BDD edge labels are projected into canonical MoniTAal labels such as `bits:10`.
- MoniTAal positive/negative monitor produces three-valued runtime verdicts.
- Formula satisfiability is recorded before reporting runtime results.
- Outputs include `steps.csv`, `summary.csv`, `metadata.json`, and `results.xlsx`.
- `--emit-bdd-interface` writes reserved metadata only.
- `--build-mode compflatten --build-only` supports construction/statistics only.

## Explicit v1 Deferred Scope

- BDD-native runtime is not implemented.
- compflatten runtime verdicts are not implemented.
- XML-to-MITL equivalence rows marked `REVIEW_REQUIRED` still need human mathematical review.
- Human Review Signoff remains blank; no human approval is claimed.

## Final Result Entrypoints

- Results root:
  `/home/lqq/project/TAFuzz/test/TARV/results`
- Final README:
  `/home/lqq/project/TAFuzz/test/TARV/results/FINAL_RESULTS_README.md`
- Final packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full`
- Main workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/paper_review_results.xlsx`
- Supporting timeout rerun packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full`
- MITL catalog entrypoints:
  `/home/lqq/project/TAFuzz/test/TARV/results/mitl_formula_catalog_latest_official.md`,
  `/home/lqq/project/TAFuzz/test/TARV/results/mitl_formula_catalog_semantic_regression.csv`,
  `/home/lqq/project/TAFuzz/test/TARV/results/mitl_formula_catalog_monitaal_xml_candidates.csv`,
  `/home/lqq/project/TAFuzz/test/TARV/results/mitl_formula_catalog_runtime_runs.csv`.

## User Manual

- Manual directory:
  `/home/lqq/project/TAFuzz/analysis/manual`
- Entry README:
  `/home/lqq/project/TAFuzz/analysis/manual/README.md`
- Full manual:
  `/home/lqq/project/TAFuzz/analysis/manual/TAMonitor_User_Manual.md`

The manual documents accepted MITL syntax, trace formats, CLI parameters, outputs, examples, final experiment result locations, and v1 boundaries.

## Final Cleanup

- `test/TARV/results` was reduced from 276 top-level entries and about 14G to 7 top-level entries and about 130M.
- Removed historical intermediate experiment outputs and stale rerun packets.
- Kept only the final review packet, its supporting timeout rerun packet, MITL catalog entrypoints, and `FINAL_RESULTS_README.md`.
- The paused XML-to-MITL / Review Signoff experiment-review track was not continued.
- Two unverified paused-track script additions were removed:
  `XML_EQUIVALENCE_SIGNOFF_COVERAGE_AUDIT` from `test/TARV/scripts/verify_review_packet.py`
  and `EXPECTED_XML_EQUIVALENCE_SIGNOFF_COVERAGE_VERIFIER_DELTA` from
  `test/TARV/scripts/compare_pipeline_results.py`.

## Final Verification

- `python3 -m py_compile test/TARV/scripts/verify_review_packet.py test/TARV/scripts/compare_pipeline_results.py` passed after removing paused-track edits.
- Final kept entries under `test/TARV/results`:
  `FINAL_RESULTS_README.md`,
  `baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full`,
  `mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`,
  `mitl_formula_catalog_runtime_runs.csv`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `paper_pipeline_formula_catalog_workbook_guard_full`.
- `unzip -t paper_review_results.xlsx` passed.
- Final packet summary: pipeline `PASS`, failed steps `[]`.
- Review packet verifier JSON: 151 PASS, 0 WARN, 0 FAIL.
- Artifact manifest verifier JSON: 16 PASS, 0 WARN, 0 FAIL, 151 manifest rows.
- TAMonitor final smoke test:
  `tool/MightyPPL/build/TAMonitor --formula-inline 'F [0,2] p1' --trace /tmp/tamonitor_final_manual_trace.csv --word finite --state symbolic --build-mode flatten --out /tmp/tamonitor_final_manual_smoke`
  returned `Formula satisfiable: SAT`, `Final verdict: POSITIVE`, 2 events, 2 processed steps.

## Workspace Boundaries

- Top-level `/home/lqq/project/TAFuzz` is currently a normal Git repository
  with remote `git@github.com:PearBabe/TAFuzz.git`.
- `tool/MightyPPL` and `tool/MoniTAal` are now ordinary tracked directories in
  the top-level repository; older handoff/archive entries may still describe
  them as nested repositories.
- Handoff files live at the TAFuzz root.
- Preserve unrelated user work; do not revert dirty changes.

## Known Limits / Risks

- BDD projection can grow exponentially; `--max-valuations` intentionally fails rather than silently approximating.
- Numeric CLI options should be plain positive integers.
- `--help` currently prints usage through the error path and exits nonzero.
- The 8 original-trace benchmark gaps and XML equivalence `REVIEW_REQUIRED` rows remain manual-review topics, not completed algorithm claims.

## Next Steps

1. No further action now; wait for a new explicit user request.
2. If the user asks for bug fixes, start by reading this file and the manual, then inspect the relevant source files directly.
3. Do not resume XML-to-MITL proof/signoff expansion, BDD-native runtime, or compflatten runtime unless explicitly requested.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`。当前 TAMonitor v1 目标已经完成；最终结果入口在
`/home/lqq/project/TAFuzz/test/TARV/results/FINAL_RESULTS_README.md`，使用文档在
`/home/lqq/project/TAFuzz/analysis/manual/TAMonitor_User_Manual.md`。不要继续改代码或实验，除非用户提出新的明确 bug 或功能请求。
