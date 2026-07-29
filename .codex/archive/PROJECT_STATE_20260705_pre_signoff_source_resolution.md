# TAFuzz Project State

Last updated: 2026-07-05 18:36 CST.

Detailed older states are archived under `.codex/archive/`, including:
`.codex/archive/PROJECT_STATE_20260705_pre_three_valued_guard_compact.md`,
`.codex/archive/PROJECT_STATE_20260705_pre_monitaal_eof_fix.md`,
`.codex/archive/PROJECT_STATE_20260705_pre_manifest_verification_compact.md`,
and `.codex/archive/PROJECT_STATE_20260705_pre_manual_oracle_guide.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full paper-review
pipeline. Runtime uses MightyPPL flatten construction, BDD-label valuation
projection, and MoniTAal positive/negative monitor logic. Real bugs found
during experiments have been fixed and promoted: MoniTAal file-mode EOF plus
`INCONCLUSIVE` no longer spins forever; workbook previews avoid wide/large
sheet crashes; generated-empty XML baseline probes are disclosed; MoniTAal
hard-coded benchmark entrypoints have separate evidence; finite-word
hand-oracle coverage spans all user-level MightyPPL runtime syntax rows; public
runtime verdict artifacts are guarded to the three-valued surface; review
signoff templates include row-level decision policy plus resolvable evidence
artifact checks; and a safe human-signoff import roundtrip now supports filled
CSV/XLSX review results without trusting stale generated columns.

Do not mark the goal complete yet. Human `Review Signoff` is still blank in the
latest official packet, BDD-native runtime is not implemented, compflatten
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
- MoniTAal: `tool/MoniTAal/src/monitaal-bin/main.cpp` EOF loop fix and
  `tool/MoniTAal/benchmark/main.cpp` benchmark seed-output newline fix.
- MightyPPL repo: `CMakeLists.txt`, `MightyPPL.cpp`, `MightyPPL.h`,
  `TAwithBDDEdges.cpp`, `TAwithBDDEdges.h`,
  `MightyPPLRuntimeOptions.cpp`.
- Added/modified project areas: `src/TAMonitor/`, `test/TARV/`,
  `analysis/tool_projects_deep_analysis.md`.
- Latest script changes: `import_review_signoff.py` safe import bridge;
  `validate_review_signoff.py` supports `--signoff-csv` and custom output
  prefixes; `verify_review_packet.py` supports
  `--signoff-mode pre-review|complete`; `run_paper_experiments.py` adds
  `RG_SIGNOFF_IMPORT_ROUNDTRIP`; `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` support `signoff-import-added`.

## Latest Official Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/pipeline_summary.md`
- Latest review packet verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/review_packet_verification.md`
- Latest artifact manifest:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/pipeline_artifact_manifest.md`
- Latest artifact-manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/manual_oracle_guide.md`
- Latest hard-coded MoniTAal benchmark evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/monitaal_hardcoded_benchmarks.md`
- Latest result-stability audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/result_stability_audit.md`
- Latest signoff validation:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full/review_signoff_validation.md`
- Latest timeout rerun evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_import_v2_full`
- Previous official packet and stability baseline:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_resolution_v3_full`

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
- Human signoff cannot approve rows beyond their generated decision policy; v2
  deferred rows forbid `APPROVE_AS_CLAIMED`, and all signoff evidence tokens
  must resolve to concrete packet artifacts, workbook sheets, or matching
  `glob:` artifacts.
- Human-filled signoff import copies only `reviewer_decision`, `reviewer`,
  `review_date`, and `reviewer_notes`; generated queue/evidence/policy fields
  must match the current packet or import fails.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_signoff_import_v2_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_signoff_import_v2_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_signoff_evidence_resolution_v3_full --stability-profile signoff-import-added`

Pipeline status: `PASS`, full mode, elapsed 48881 ms, failed steps 0.
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
- review guide: 14 rows, 8 P0 rows, including `RG_SIGNOFF_IMPORT_ROUNDTRIP`.
- hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error,
  0 timeout; workbook sheet present.
- workbook: `ok`, 35 worksheets/tables including `Hardcoded Benchmarks`,
  `Benchmark Blockers`, `Signoff Validation`, `Timeout Rerun Summary`, and
  `Timeout Rerun`.
- review packet verifier: 76 PASS, 0 WARN, 0 FAIL.
- signoff validation: 10 PASS, 0 FAIL, mode `pre-review`, completion state
  `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`; blank decisions 47; policy mismatches
  0; forbidden decisions 0; unresolved evidence tokens 0.
- result stability audit: profile `signoff-import-added`, 163 PASS,
  0 WARN, 0 FAIL. Expected deltas: review guide rows +1/P0 +1 and source
  hashes +1.
- artifact manifest verification: 11 PASS, 0 WARN, 0 FAIL; 132 manifest rows,
  0 missing files, 0 bad hashes, 0 bad sizes.

## Latest Verification

Passed evidence:

- Full v2 pipeline command above completed with `pipeline_status=PASS`.
- `verify_review_packet.py` produced 76 PASS/0 FAIL for v2.
- `compare_pipeline_results.py --profile signoff-import-added` produced
  163 PASS/0 FAIL.
- `verify_pipeline_artifact_manifest.py` produced 11 PASS/0 FAIL.
- `unzip -t` passed for the v2 workbook.
- Python compilation passed for changed pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`.
- Bundled Node `--check` passed for `build_paper_review_workbook.mjs`.
- Positive CSV import test on an isolated v2 copy passed: 47 imported
  nonblank decisions, `validate_review_signoff.py --mode complete` passed,
  and `verify_review_packet.py --signoff-mode complete` passed 76/76.
- XLSX import test on the v2 workbook passed: `Review Signoff` sheet extracted
  47 rows and pre-review validation on the imported CSV passed 10/10.
- Stale generated-field negative test failed as expected with one immutable
  field mismatch; import did not apply.
- Integration bug found/fixed: `compare_pipeline_results.py` initially lacked
  `signoff-import-added` in argparse choices even though the full pipeline knew
  the profile.
- Test isolation bug found/fixed operationally: an earlier temp symlink clone
  wrote complete-mode validation through a symlink into the v3 baseline; v3
  pre-review validation was restored and later temp clones copy all writable
  validation/verifier files.
- Whitespace scan on changed pipeline scripts found no trailing whitespace.
- Nested repo `diff --check` passed for the modified MightyPPL and MoniTAal
  files.

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
   packet; keep forbidden decisions, unresolved evidence, stale generated
   fields, or failed verifier rows as blockers.
4. Keep BDD-native runtime and compflatten runtime as v2 work until real
   algorithms and oracle suites are implemented.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_import_v2_full`。
