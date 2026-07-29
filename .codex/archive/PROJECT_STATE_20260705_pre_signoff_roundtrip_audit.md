# TAFuzz Project State

Last updated: 2026-07-05 19:48 CST.

Older detailed states are archived under `.codex/archive/`, including
`PROJECT_STATE_20260705_pre_signoff_source_resolution.md` and earlier
pre-milestone snapshots.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full paper-review
pipeline. Runtime uses MightyPPL flatten construction, BDD-label valuation
projection, and MoniTAal positive/negative monitor logic. Real bugs found
during experiments have been fixed and promoted into the pipeline.

Do not mark the goal complete yet. Human `Review Signoff` is still blank in
the latest official packet, BDD-native runtime is not implemented, compflatten
runtime verdicts are unsupported in v1, and XML-to-MITL proof-ready rows still
require human review.

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
- MoniTAal: `tool/MoniTAal/src/monitaal-bin/main.cpp` EOF/INCONCLUSIVE guard
  and `tool/MoniTAal/benchmark/main.cpp` benchmark seed-output newline fix.
- MightyPPL: `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`,
  `MightyPPLRuntimeOptions.cpp`.
- Project additions: `src/TAMonitor/`, `test/TARV/`,
  `analysis/tool_projects_deep_analysis.md`.
- Latest script changes: `validate_review_signoff.py` now resolves signoff-row
  and queue-wide evidence/source references;
  `verify_review_packet.py` independently checks every `human_review_queue.csv`
  evidence/source reference and rejects stale signoff-validation artifacts;
  stability scripts support `review-queue-evidence-resolution-added`.

## Latest Official Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/pipeline_summary.md`
- Latest review packet verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/review_packet_verification.md`
- Latest artifact manifest:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/pipeline_artifact_manifest.md`
- Latest artifact-manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/manual_oracle_guide.md`
- Latest hard-coded MoniTAal benchmark evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/monitaal_hardcoded_benchmarks.md`
- Latest result-stability audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/result_stability_audit.md`
- Latest signoff validation:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full/review_signoff_validation.md`
- Latest timeout rerun evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_review_queue_evidence_resolution_full`
- Previous official packet and stability baseline:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_source_resolution_full`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal-bin/main.cpp`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/main.cpp`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/import_review_signoff.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/validate_review_signoff.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_review_packet.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_pipeline_artifact_manifest.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_full_review_pipeline.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/compare_pipeline_results.py`
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
- `monitaal-benchmark` is separate hard-coded C++ benchmark evidence, not
  XML-file MoniTAal-bin baseline evidence.
- Public TAMonitor RV verdict artifacts must stay three-valued; internal
  overlap/gap states are exposed conservatively as `INCONCLUSIVE`.
- Human signoff cannot approve rows beyond their generated decision policy.
  Evidence tokens must resolve to packet artifacts, workbook sheets, or
  matching `glob:` artifacts for both signoff rows and all review queue rows.
  Source references must resolve to workbook sheet names and generated source
  CSV rows for both signoff rows and all review queue rows, including
  queue-only P3 exclusion-audit rows.
- Human-filled signoff import copies only `reviewer_decision`, `reviewer`,
  `review_date`, and `reviewer_notes`; generated queue/evidence/policy fields
  must match the current packet or import fails.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_review_queue_evidence_resolution_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_review_queue_source_resolution_full --stability-profile review-queue-evidence-resolution-added`

Pipeline status: `PASS`, full mode, elapsed 48259 ms, failed steps 0.
Remaining caveats are 3 generated-empty baseline-only probes, blank human
signoff, proof-review gates, and v2 deferrals.

Key counts:

- semantic: 87 cases, 70 runtime verified, 34 finite verified,
  36 infinite verified, fail/error/timeout 0/0/0.
- prefix oracle: 163 rows, 146 matches, 0 mismatches, 0 missing,
  34 carry-forward rows.
- syntax/input policy: all 36 user-level runtime rows verified in both finite
  and infinite modes; 8 internal Count-form probes excluded.
- candidate/baseline: 43/43 candidate runs succeeded; baseline
  matches/mismatches/not-verified 43/0/0; MoniTAal baselines 47 ran,
  0 timed out, 0 skipped no input, 3 generated-empty baseline-only probes.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error,
  0 timeout; workbook sheet present.
- workbook: `ok`, 35 worksheets/tables.
- review packet verifier: 80 PASS, 0 WARN, 0 FAIL.
- signoff validation: 16 PASS, 0 FAIL, mode `pre-review`, completion state
  `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`; blank decisions 47; policy mismatches
  0; forbidden decisions 0; unresolved signoff evidence tokens 0; missing
  queue evidence rows 0; unresolved queue evidence tokens 0; unresolved source
  sheet/row tokens 0; unresolved queue source sheet/row tokens 0.
- result stability audit: profile `review-queue-evidence-resolution-added`,
  169 PASS, 0 WARN, 0 FAIL.
- artifact manifest verification: 11 PASS, 0 WARN, 0 FAIL; 132 manifest rows,
  0 missing files, 0 bad hashes, 0 bad sizes.

## Latest Verification

Passed evidence:

- Full review-queue evidence-resolution pipeline completed with
  `pipeline_status=PASS`.
- `review_signoff_validation.md` shows new checks
  `SIGNOFF_EVIDENCE_RESOLUTION`, `QUEUE_EVIDENCE_FIELDS_PRESENT`,
  `QUEUE_EVIDENCE_RESOLUTION`, `SIGNOFF_SOURCE_SHEET_RESOLUTION`,
  `SIGNOFF_SOURCE_ROW_RESOLUTION`, `QUEUE_SOURCE_SHEET_RESOLUTION`, and
  `QUEUE_SOURCE_ROW_RESOLUTION` passing.
- `review_packet_verification.md` shows `REVIEW_QUEUE_EVIDENCE_REFERENCES`,
  `REVIEW_QUEUE_SOURCE_REFERENCES`, `SIGNOFF_VALIDATION_QUEUE_EVIDENCE_CHECKS`,
  and `SIGNOFF_VALIDATION_QUEUE_SOURCE_CHECKS` passing, so old
  signoff-validation artifacts cannot silently hide queue-only dangling
  references.
- `verify_pipeline_artifact_manifest.py` passed: 11 PASS/0 FAIL, 132 manifest
  rows, no missing files, bad hashes, or bad sizes.
- `unzip -t` passed for the latest workbook.
- Python compilation passed for changed pipeline scripts.
- Bundled Node `/mnt/c/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe --check`
  passed for `build_paper_review_workbook.mjs`.
- Whitespace scan on changed pipeline scripts found no trailing whitespace.
- Nested repo `diff --check` passed for the modified MightyPPL and MoniTAal
  files.
- Negative tests on isolated temp packets passed: bogus signoff-row references
  fail validation; bogus P3 queue-only `source_sheet`/`source_id` references
  fail both validation and packet verification; bogus P3 `evidence_artifacts`
  and missing review context also fail both gates.
- Latest isolated complete-mode import regression passed on a copied packet:
  dry import `status=PASS`, applied import copied 47 nonblank reviewer
  decisions, `validate_review_signoff.py --mode complete` passed 16/16 with
  `HUMAN_SIGNOFF_COMPLETE`, and `verify_review_packet.py --signoff-mode
  complete` passed 80/80. A stale generated `source_id` import failed as
  expected with one immutable-field mismatch and did not apply.

## Known Limits / Risks

- BDD-native runtime is not implemented in v1.
- `compflatten` runtime verdicts are not claimed in v1.
- Human `Review Signoff` is blank by design in the latest official packet;
  blank decisions mean ready for human review, not completed human review.
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
   `Review Queue`, `Review Signoff`, `Signoff Validation`, and
   `Review Packet Verification`.
2. After filling review decisions, use
   `import_review_signoff.py --output-dir <packet> --from-csv <filled.csv>`
   or `--from-xlsx <filled.xlsx>`, inspect `review_signoff_import_report.*`,
   then use `--apply` only on a clean import.
3. Run `validate_review_signoff.py --mode complete` and
   `verify_review_packet.py --signoff-mode complete` on any completed-review
   packet; keep forbidden decisions, unresolved evidence/source references,
   stale generated fields, or failed verifier rows as blockers.
4. Keep BDD-native runtime and compflatten runtime as v2 work until real
   algorithms and oracle suites are implemented.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_review_queue_evidence_resolution_full`。
