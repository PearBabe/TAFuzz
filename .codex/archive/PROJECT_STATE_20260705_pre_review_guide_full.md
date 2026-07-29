# TAFuzz Project State

Last updated: 2026-07-05 11:39 CST

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Current status: TAMonitor v1 is implemented with BDD-label projection,
flatten-mode runtime verification, finite/infinite semantic regressions,
stepwise hand-oracle review, semantic oracle derivation ledger, XML benchmark
inventory/translation review, candidate step audit, proof/claim/requirement
ledgers, reproducibility manifest, MightyPPL syntax coverage ledger,
Count-form input-policy audit, TAMonitor CLI contract audit, top-level goal
completion audit, a prioritized human-review queue, and consolidated
`Review Queue`/`Review Signoff`/`Goal Audit`/`Manual Review` workbook entry
sheets.

Newest primary output:

`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_signoff_full`

Newest review workbook:

`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_signoff_full/paper_review_results.xlsx`

Latest supplementary timeout-rerun evidence:

`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff`

Prior long handoff archive:
`.codex/archive/PROJECT_STATE_20260705_pre_proof_appendix_full.md`

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
- `/home/lqq/project/TAFuzz/tool/MoniTAal`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`

## Implemented Decisions

- v1 uses BDD-label projection to canonical MoniTAal labels; BDD-native runtime
  remains metadata/interface only.
- finite-word monitor finalization preserves decisive POSITIVE/NEGATIVE step
  verdicts instead of recomputing an inconclusive final verdict.
- `compflatten` runtime remains explicitly unsupported in v1; compflatten rows
  are build/stat-only and never get fake runtime verdicts.
- `CFn/COn/CGn/CHn` and starred variants are parser-visible but internal
  compilation/NNF forms. They are excluded from user-level MITL semantic
  regression and rejected by TAMonitor with controlled `unsupported_user_formula`
  diagnostics.
- XML-to-MITL translation remains conservative: only proof-ready trace-level
  rows enter paper-review claims; approximate, timeout, no-input, and unclaimed
  rows stay visible as caveats/exclusions.
- Correctness labels:
  `VERIFIED` requires a hand oracle or comparable baseline match.
  `TIMEOUT`, `RESOURCE_LIMIT`, build-only, no-run, and timeout-caveat rows are
  not counted as verified correctness.

## Latest Full Experiment

Command:

`python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --out test/TARV/results/paper_experiments_signoff_full`

Summary:

- semantic: 70 cases, 53 verified, 17 finite verified, 36 infinite verified,
  0 fail/error, 17 existing MightyPPL testcase rows build/stat-only.
- semantic prefix oracle: 132 rows, 115 matches, 0 mismatches, 0 missing,
  28 carry-forward rows after decisive verdicts.
- semantic oracle derivations: 70 rows, 53 `HAND_ORACLE_VERIFIED`,
  17 `CONSTRUCTION_STATS_ONLY`, 0 `ORACLE_REVIEW_REQUIRED`, 0 prefix mismatch.
- syntax coverage: 45 rows, 36 runtime-verified rows, 17 finite+infinite rows,
  1 build-stats-only corpus row, 8 internal Count exclusions, 0 missing.
- input policy: 8 internal Count-form probes, 8 controlled diagnostics, 0 fail,
  0 assert-like failures.
- CLI contract: 10 direct TAMonitor command probes, 10 PASS, 0 FAIL,
  5 controlled-error paths.
- goal completion audit: 17 rows, 12 PASS, 2 PASS_WITH_CAVEAT,
  2 REVIEW_REQUIRED, 1 V1_DEFERRED, 0 FAIL.
- human review queue: 70 rows, 47 human-required rows, 29 P0 rows, 23 P1 rows,
  2 P2 rows, 16 P3 rows, 0 fail rows.
- review signoff template: 54 rows, 54 blank reviewer decisions, 29 P0 rows,
  23 P1 rows, 2 P2 rows.
- manual review checklist: 16 rows, 8 PASS, 4 PASS_WITH_CAVEAT,
  3 REVIEW_REQUIRED, 1 V1_DEFERRED, 0 FAIL, 12 human-decision-required gates.
- XML inventory/review: 60 templates, 386 transition rows, 23 pairs, 19 MITL
  candidates, 23 manifest rows.
- XML proof/claims: 15 strong trace-level candidates, 3 approximate trace-only,
  8 not promoted; proof appendix ready/excluded 15/8; claim audit pass/warn/fail
  23/0/0.
- requirements audit: 22 rows, 19 PASS, 2 PASS_WITH_CAVEAT, 1 V1_DEFERRED,
  0 FAIL.
- reproducibility manifest: 85 rows, 16 source hashes, 50 result hashes, 6 git
  rows.
- TAMonitor candidate runs: 43/43 succeeded; baseline matches/mismatches/not
  verified due timeout: 36/0/7.
- candidate prefix observations: 122975 raw rows; compact audit 43 rows, all
  complete, 29988 carry-forward rows.
- MoniTAal baselines: 36 ran, 8 timed out, 3 skipped no input; embedded/generated
  benchmark records: 30; workbook status: `ok`.

Important artifacts:

- `paper_review_results.xlsx`
- `experiment_summary.json`
- `semantic_cases.csv`
- `semantic_regression_results.csv`
- `mitl_correctness_audit.csv`
- `semantic_prefix_oracle_review.csv/md`
- `semantic_oracle_derivations.csv/json/md`
- `semantic_exclusions.csv/json/md`
- `mightyppl_syntax_coverage_audit.csv/json/md`
- `formula_input_policy_audit.csv/json/md`
- `cli_contract_audit.csv/json/md`
- `human_review_queue.csv/json/md`
- `review_signoff_template.csv/json/md`
- `goal_completion_audit.csv/json/md`
- `manual_review_checklist.csv/json/md`
- `benchmark_manifest.csv/json`
- `xml_edge_guard_proofs.csv/json`
- `xml_proof_appendix.csv`
- `xml_translation_proof_appendix.md`
- `paper_claim_review.csv/md`
- `paper_claim_consistency_audit.csv/md`
- `requirements_traceability_audit.csv/md`
- `reproducibility_manifest.csv/json/md`
- `candidate_step_audit.csv/md`
- `candidate_prefix_observations.csv`
- `translation_candidate_results.csv`
- `monitaal_baseline_results.csv`
- `monitaal_embedded_benchmarks.csv`

Workbook sheets:

Summary, Review Queue, Review Signoff, Goal Audit, Manual Review,
Correctness Audit, Prefix Oracle, Oracle Derivations, Semantic Results,
Semantic Cases, Semantic Exclusions, Syntax Coverage, Input Policy,
CLI Contract, XML Inventory, Translation Review, Benchmark Manifest,
XML Edge Proofs, XML Proof Appendix, Paper Claim Review, Claim Audit,
Requirements Audit, Repro Manifest, Transition Details, Candidate Results,
Candidate Step Audit, Baseline Results, Embedded Benchmarks.

## Latest Verification

Passed:

- `cmake --build tool/MightyPPL/build --target TAMonitor -j2`
- `python3 -m py_compile test/TARV/scripts/run_paper_experiments.py
  test/TARV/scripts/rerun_baseline_timeouts.py src/TAMonitor/make_tamonitor_xlsx.py`
- bundled Node syntax check for `build_paper_review_workbook.mjs`
- `python3 -m json.tool` for summary, human-review-queue, review-signoff,
  goal-completion, CLI contract, semantic-oracle, manual-review, manifest, proof,
  reproducibility, semantic-exclusion, syntax, input-policy, and timeout-rerun
  JSON files.
- `unzip -t paper_review_results.xlsx`
- workbook formula-error scan matched 0 entries.
- workbook XML contains 28 sheets and 28 tables, including `Review Queue`,
  `Review Signoff`, `Goal Audit`, `CLI Contract`, `Oracle Derivations`,
  `Manual Review`, `Syntax Coverage`, and `Input Policy`.
- CSV checks:
  CLI contract 10 rows/10 pass/0 fail/5 controlled-error paths;
  human review queue 70 rows/47 human-required/29 P0/23 P1/2 P2/16 P3/0 fail;
  review signoff template 54 rows/54 blank decisions/29 P0/23 P1/2 P2;
  goal completion 17 rows/12 pass/2 caveat/2 review-required/1 deferred/0 fail;
  oracle derivations 70 rows/53 verified/17 build-only/0 review-required/0
  prefix mismatch; manual review 16 rows/0 fail; requirements 22 rows/0 fail;
  input policy 8 rows/8 pass/0 assert-like failures; syntax coverage 45 rows/0
  missing; prefix oracle 132 rows/0 mismatches; candidate step audit 43 rows;
  candidate prefix observations 122975 rows.
- preview PNG dimensions checked for `review_signoff_preview.png`,
  `review_queue_preview.png`, `goal_audit_preview.png`, and
  `manual_review_preview.png`; previous `Manual Review` status-column clipping
  bug remains fixed.
- `git -C tool/MightyPPL diff --check -- ...` passed for edited source/handoff
  paths.
- supplementary timeout rerun:
  `python3 test/TARV/scripts/rerun_baseline_timeouts.py --source
  test/TARV/results/paper_experiments_signoff_full --timeout 60
  --out test/TARV/results/baseline_timeout_rerun_60s_signoff`
  selected all 8 timeout rows; 0 finished with verdict and 8 still timed out.

## Known Limits / Risks

- BDD-native runtime is not implemented in v1.
- `compflatten` runtime verdicts are not claimed in v1.
- 7 candidate MITL rows still lack comparable original-input baseline verdict
  because MoniTAal baseline timed out.
- 8 MoniTAal baseline runs timed out even with the 60-second supplementary rerun;
  3 XML rows have no input. These remain caveats, not correctness evidence.
- Gear-controller original long inputs still time out; reduced/generated traces
  are trace-level validation aids only.
- `f(g(notb)_and_g(f(a)).xml` remains excluded from formal claims until a real
  edge/guard proof and liveness/finite-prefix review are complete.
- `xml_proof_appendix.csv` is a draft proof ledger, not a final theorem. Human
  review is still required before paper wording.

## Next Steps

1. Open workbook sheets `Review Queue` and `Review Signoff` first, then follow
   rows to `Goal Audit`, `Manual Review`, `XML Proof Appendix`,
   `Paper Claim Review`, `Claim Audit`, `Oracle Derivations`, `Prefix Oracle`,
   `Syntax Coverage`, `Input Policy`, `Requirements Audit`, and `Repro Manifest`.
2. Keep timeout rows as caveats unless a longer justified baseline campaign is
   explicitly required.
3. If paper claims expand beyond operator-level finite regressions, add
   theorem-specific finite-word hand-oracle cases.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_signoff_full`；
60 秒 timeout 补充重跑目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff`。
