# TAFuzz Project State

Last updated: 2026-07-06 00:20 CST.

Older detailed states are archived under `.codex/archive/`, including
`PROJECT_STATE_20260705_pre_evidence_consistency.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full paper-review
pipeline. Runtime uses MightyPPL flatten construction, BDD-label valuation
projection, and MoniTAal positive/negative monitor logic. Real bugs found by
experiments are still being fixed and promoted into the pipeline.

Do not mark the goal complete yet. Human `Review Signoff` is still blank,
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
- Latest XML trace-coverage changes: `xml_trace_coverage_obligations.{csv,json,md}`,
  workbook sheet `XML Trace Coverage`, packet verifier guard
  `XML_TRACE_COVERAGE_AUDIT`, artifact-manifest coverage, and stability
  profile `xml-trace-coverage-added`.

## Latest Official Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/pipeline_summary.md`
- Latest review packet verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/review_packet_verification.md`
- Latest signoff evidence bundle:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/review_signoff_evidence_bundle.md`
- Latest signoff import roundtrip audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/signoff_import_roundtrip_audit.md`
- Latest artifact manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/manual_oracle_guide.md`
- Latest XML proof obligations:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/xml_proof_obligations.md`
- Latest XML trace coverage obligations:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full/xml_trace_coverage_obligations.md`
- Latest timeout rerun evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_trace_coverage_full`
- Stability baseline for the latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_obligations_full`
- Failed first evidence-consistency run kept as bug evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_evidence_consistency_full`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal-bin/main.cpp`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/main.cpp`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_review_packet.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/validate_review_signoff.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/rerun_baseline_timeouts.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/compare_pipeline_results.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_full_review_pipeline.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/audit_signoff_import_roundtrip.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_signoff_evidence_bundle.py`

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
- INCONCLUSIVE original-input baseline rows are third-valued trace evidence,
  not Boolean satisfaction/violation and not XML-to-MITL equivalence proofs.
- Human-filled signoff import copies only `reviewer_decision`, `reviewer`,
  `review_date`, and `reviewer_notes`; generated queue/evidence/policy fields
  must match the current packet or import fails.
- Synthetic signoff roundtrip audit proves command/workflow behavior only. It
  never claims human mathematical approval.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_xml_trace_coverage_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_xml_trace_coverage_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_xml_obligations_full --stability-profile xml-trace-coverage-added`

Pipeline status: `PASS`, full mode, elapsed 83556 ms, failed steps 0.

Key counts:

- semantic: 87 cases, 70 runtime verified, fail/error/timeout 0/0/0.
- prefix oracle: 163 rows, 146 matches, 0 mismatches, 0 missing,
  34 carry-forward rows.
- candidate/baseline: 43/43 candidate runs succeeded; baseline
  matches/mismatches/not-verified 43/0/0; MoniTAal baselines 47 ran,
  0 timeout, 3 generated-empty baseline-only probes.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- XML proof obligations: 143 rows, 125 PASS, 18 REVIEW_REQUIRED, 0 FAIL.
  All 15 proof-ready XML rows have a human equivalence signoff obligation.
- XML trace coverage obligations: 120 rows, 84 PASS, 36 REVIEW_REQUIRED,
  0 FAIL. All 15 proof-ready XML rows have runtime-integrity PASS coverage.
- hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error,
  0 timeout.
- workbook: `ok`, 39 worksheets/tables, including `XML Obligations` and
  `XML Trace Coverage`.
- signoff evidence bundle: 47 PASS, 0 FAIL, generated-only and not human
  approval.
- signoff import roundtrip audit: 7 PASS, 0 FAIL, expected/imported synthetic
  signoff decisions 47/47, `human_signoff_claim=not_claimed`.
- review packet verifier: 102 PASS, 0 WARN, 0 FAIL.
- signoff validation: 16 PASS, 0 FAIL, mode `pre-review`,
  completion state `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`; blank decisions 47.
- result stability audit: profile `xml-trace-coverage-added`,
  157 PASS, 0 WARN, 0 FAIL.
- artifact manifest verifier: 15 PASS, 0 WARN, 0 FAIL; 152 manifest rows,
  0 missing files, bad hashes, or bad sizes.

## Latest Verification

Passed evidence:

- Full XML trace-coverage pipeline completed with `pipeline_status=PASS`.
- `verify_review_packet.py` passed: 102 PASS/0 FAIL, including
  `XML_PROOF_OBLIGATION_AUDIT` and `XML_TRACE_COVERAGE_AUDIT`.
- `verify_pipeline_artifact_manifest.py` passed: 15 PASS/0 FAIL, 152 manifest
  rows, no missing files, bad hashes, or bad sizes.
- `unzip -t` passed for the latest workbook.
- Stale timeout fact scan over the latest packet returned no matches for
  `still times out`, `timed out in baseline`,
  `NOT_VERIFIED_BASELINE_TIMEOUT`, `original-input timeout caveat`, or
  `baseline timed out`.
- Stability audit passed for `xml-trace-coverage-added`: 157 PASS/0 FAIL.
- `XML Trace Coverage` sheet is present and the workbook/repro manifest hashes
  `xml_trace_coverage_obligations.csv/json/md`.
- Gear proof row now states original `gear-control-input.txt` terminates with
  `INCONCLUSIVE` and is third-valued trace evidence; generated reduced traces
  provide NEGATIVE boundary evidence.
- Gear paper-claim and XML-proof signoff rows now recommend
  `APPROVE_WITH_CAVEAT` and forbid `APPROVE_AS_CLAIMED` when INCONCLUSIVE
  evidence appears.
- Python compilation passed for changed pipeline scripts via the full pipeline.
- Bundled Node syntax check passed for `build_paper_review_workbook.mjs`.
- Whitespace scan on changed pipeline scripts found no trailing whitespace.
- Nested repo `diff --check` passed for the modified MightyPPL and MoniTAal
  files.

Real bugs fixed during this milestone:

- First XML trace-coverage probe produced 15 false `runtime_trace_integrity`
  FAIL rows because `as_int(0, -999)` returned the default. `as_int` now treats
  only `None`/empty string as default.
- `only_ab_until10_negative_boundary.input` was not recognized as a closed
  boundary trace because the classifier only matched `boundary_negative`, not
  `negative_boundary`.
- The new trace-coverage profile and workbook/manifest guards now expose
  missing positive/negative/boundary strengthening traces as REVIEW_REQUIRED,
  while keeping runtime mismatch, timeout/error, step loss, and generated-empty
  proof use as machine-checkable FAIL conditions.
- The first XML proof-obligation probe falsely marked 15 runtime step-recording
  obligations as FAIL because generated CSV integers were compared to string
  row values. The check now normalizes both sides with `as_int`.
- The `xml-proof-obligations-added` stability profile still carried draft
  obligation-count deltas. It now matches the real generated packet:
  143 rows, 125 PASS, 18 REVIEW_REQUIRED, 0 FAIL.
- Stale gear proof/appendix/review/signoff evidence claimed the original long
  gear input still timed out even though current baselines show 0 timeouts and
  `gear-control-input.txt:INCONCLUSIVE`.
- `manual_xml_candidate_review.md` carried static timeout wording for
  `gear-control-properties.xml`, `b_live_a_freq.xml`, and
  `gear_controller_test.xml`; it now derives timeout/INCONCLUSIVE wording from
  actual baseline rows.
- Paper claim/signoff wording treated INCONCLUSIVE original-input evidence too
  much like an ordinary baseline match; it now explicitly requires a
  third-valued caveat and forbids approve-as-claimed signoff for those rows.
- Timeout rerun Markdown now states that an empty rerun is expected evidence
  when the source experiment has 0 timeout rows.
- First full evidence-consistency run failed because the new guard found the
  last static stale timeout sentence; the fixed v2 rerun passed.

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
   `Hardcoded Benchmarks`, `Benchmark Blockers`, `XML Obligations`,
   `XML Trace Coverage`, `Paper Claim Review`, `Review Queue`,
   `Review Signoff`, `Signoff Validation`, `Signoff Evidence`,
   `Signoff Roundtrip`, and `Review Packet Verification`.
2. After filling review decisions, use
   `import_review_signoff.py --output-dir <packet> --from-csv <filled.csv>`
   or `--from-xlsx <filled.xlsx>`, inspect `review_signoff_import_report.*`,
   then use `--apply` only on a clean import.
3. Run `validate_review_signoff.py --mode complete` and
   `verify_review_packet.py --signoff-mode complete` on any completed-review
   packet; keep forbidden decisions, unresolved evidence/source references,
   stale generated fields, or failed verifier rows as blockers.
4. Continue automatable evidence work before final paper claims: generate the
   currently REVIEW_REQUIRED strengthening traces where semantics are clear
   (positive response at bound, safe absence after bound, eventuality negative,
   timely recurrence positive) and keep BDD-native runtime and compflatten
   runtime as v2 work until real algorithms and oracle suites are implemented.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，不要重新从头探索，
不要回滚用户改动。当前最新完整结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_trace_coverage_full`。
