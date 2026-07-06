# TAFuzz Project State

Last updated: 2026-07-05 21:34 CST.

Older detailed states are archived under `.codex/archive/`, including
`PROJECT_STATE_20260705_pre_signoff_roundtrip_audit.md`.

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Status: TAMonitor v1 is implemented and exercised through a full paper-review
pipeline. Runtime uses MightyPPL flatten construction, BDD-label valuation
projection, and MoniTAal positive/negative monitor logic. Real bugs found
during experiments continue to be fixed and promoted into the pipeline.

Do not mark the goal complete yet. Human `Review Signoff` is still blank in
the latest official packet, BDD-native runtime is not implemented, compflatten
runtime verdicts are unsupported in v1, and XML-to-MITL proof-ready rows still
require human mathematical review.

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
- Latest pipeline changes: official synthetic Review Signoff import roundtrip
  audit, conditional packet verifier checks for
  `signoff_import_roundtrip_audit.{csv,json,md}`, `Signoff Roundtrip` workbook
  sheet, generated `review_signoff_evidence_bundle.{csv,json,md}`,
  `Signoff Evidence` workbook sheet, stability profiles
  `signoff-roundtrip-audit-added` and `signoff-evidence-bundle-added`, and
  artifact manifest coverage for the new review artifacts.

## Latest Official Artifacts

- Latest full experiment:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full`
- Latest workbook:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/paper_review_results.xlsx`
- Latest pipeline summary:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/pipeline_summary.md`
- Latest signoff evidence bundle:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/review_signoff_evidence_bundle.md`
- Latest signoff import roundtrip audit:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/signoff_import_roundtrip_audit.md`
- Latest review packet verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/review_packet_verification.md`
- Latest artifact manifest verification:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/pipeline_artifact_manifest_verification.md`
- Latest manual-oracle guide:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full/manual_oracle_guide.md`
- Latest timeout rerun evidence:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_bundle_full`
- Stability baseline for the latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full_v2`

## Key Source Areas

- `/home/lqq/project/TAFuzz/src/TAMonitor`
- `/home/lqq/project/TAFuzz/tool/MightyPPL`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal-bin/main.cpp`
- `/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/main.cpp`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_signoff_evidence_bundle.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/audit_signoff_import_roundtrip.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/import_review_signoff.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/validate_review_signoff.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_review_packet.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/verify_pipeline_artifact_manifest.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/run_full_review_pipeline.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/compare_pipeline_results.py`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`
- `/home/lqq/project/TAFuzz/test/TARV/scripts/rebuild_review_workbook.py`

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
- Human-filled signoff import copies only `reviewer_decision`, `reviewer`,
  `review_date`, and `reviewer_notes`; generated queue/evidence/policy fields
  must match the current packet or import fails.
- Synthetic signoff roundtrip audit proves command/workflow behavior only. It
  never claims human mathematical approval.

## Latest Full Experiment Summary

Command:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full_v2 --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_signoff_roundtrip_audit_full_v2 --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full --stability-profile signoff-roundtrip-audit-added`

Superseded by:

`python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_signoff_evidence_bundle_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_bundle_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full_v2 --stability-profile signoff-evidence-bundle-added`

Pipeline status: `PASS`, full mode, elapsed 70420 ms, failed steps 0.

Key counts:

- semantic: 87 cases, 70 runtime verified, fail/error/timeout 0/0/0.
- prefix oracle: 163 rows, 146 matches, 0 mismatches, 0 missing,
  34 carry-forward rows.
- candidate/baseline: 43/43 candidate runs succeeded; baseline
  matches/mismatches/not-verified 43/0/0; MoniTAal baselines 47 ran,
  0 timeout, 3 generated-empty baseline-only probes.
- XML/benchmark: 60 templates, 386 transition rows, 23 XML pairs,
  19 MITL candidates, 15 proof-ready candidates, 8 excluded/not-promoted rows.
- hard-coded MoniTAal benchmarks: 7 entrypoints ran/parsed, 0 error,
  0 timeout.
- workbook: `ok`, 37 worksheets/tables, includes `Signoff Evidence` and
  `Signoff Roundtrip`.
- signoff evidence bundle: 47 PASS, 0 FAIL, missing queue/source rows 0,
  unresolved evidence tokens 0, generated-only and not human approval.
- signoff import roundtrip audit: 7 PASS, 0 FAIL, expected/imported signoff
  decisions 47/47, `synthetic_only=True`, `human_signoff_claim=not_claimed`.
- review packet verifier: 90 PASS, 0 WARN, 0 FAIL.
- signoff validation: 16 PASS, 0 FAIL, mode `pre-review`,
  completion state `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`; blank decisions 47.
- result stability audit: profile `signoff-evidence-bundle-added`,
  169 PASS, 0 WARN, 0 FAIL.
- artifact manifest verifier: 13 PASS, 0 WARN, 0 FAIL; 144 manifest rows,
  0 missing files, bad hashes, or bad sizes.

## Latest Verification

Passed evidence:

- Full signoff-evidence-bundle pipeline completed with `pipeline_status=PASS`.
- Focused signoff evidence bundle regression passed: copied packet, generated
  bundle, rebuilt workbook, and verified bundle checks. The only focused
  verifier failure was expected on the copied old packet because its
  reproducibility manifest lacked the new generator script hash.
- Focused roundtrip regression passed after fixes: copied packet, synthetic
  import, complete validation, temporary workbook rebuild, complete packet
  verification, and stale generated-field rejection all passed.
- `verify_pipeline_artifact_manifest.py` passed: 13 PASS/0 FAIL, 144 manifest
  rows, no missing files, bad hashes, or bad sizes.
- `unzip -t` passed for the latest workbook.
- Python compilation passed for changed pipeline scripts.
- Bundled Node
  `/mnt/c/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe --check`
  passed for `build_paper_review_workbook.mjs`.
- Whitespace scan on changed pipeline scripts found no trailing whitespace.
- Nested repo `diff --check` passed for the modified MightyPPL and MoniTAal
  files.

Real bugs fixed during this milestone:

- `verify_review_packet.py` initially made roundtrip audit files globally
  required, which would make the audit recursively fail before it could create
  its own artifacts. It now verifies the roundtrip files strictly only when
  they exist.
- The roundtrip script initially wrote complete validation to a synthetic
  prefix, so complete-mode packet verification still read pre-review validation.
  It now updates the temporary packet's default validation artifacts.
- The temporary complete-review packet initially skipped workbook rebuild and
  failed workbook sheet/table checks. It now rebuilds the temp workbook before
  complete-mode packet verification.
- Python `tempfile` selected `/mnt/c/...` from the host environment, where
  workbook generation failed. The roundtrip audit now forces POSIX `/tmp`.
- The audit previously hard-coded 47 signoff rows; it now derives the expected
  signoff row count from `review_signoff_template.csv`.
- The new signoff evidence bundle gives each of the 47 signoff rows a generated
  source/evidence review index, while keeping `reviewer_decision` blank and
  `human_signoff_claim=not_claimed`.

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
- Subagent gap audit found stale gear timeout wording in proof ledgers and
  recommended an evidence consistency/boundary-trace milestone before human
  signoff.

## Next Steps

1. Start human review from the latest workbook's `Review Guide`,
   `Manual Oracle Guide`, `Benchmark Manifest`, `Baseline Results`,
   `Hardcoded Benchmarks`, `Benchmark Blockers`, `Paper Claim Review`,
   `Review Queue`, `Review Signoff`, `Signoff Validation`,
   `Signoff Evidence`, `Signoff Roundtrip`, and `Review Packet Verification`.
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
`/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full`；
timeout rerun 目录是
`/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_bundle_full`。
