# TAFuzz Project State

Last updated: 2026-07-05 05:05 CST

## Current Goal

完整实现并验证 TAMonitor 论文级运行时验证扩展：一边运行
MightyPPL/MoniTAal 语义与 benchmark 实验，一边修复实验暴露的真实实现缺陷，
持续更新交接文件并产出可人工审查的结果。

Current status: TAMonitor v1 and paper-review experiment harness are in place.
The newest primary output is:

`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_recur_fix_full`

Current in-progress milestone: paper-facing XML proof appendix generation has
been added to the experiment harness and workbook builder. A no-run/no-workbook
probe at
`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_proof_appendix_norun_probe`
confirmed `xml_proof_appendix.csv` and `xml_translation_proof_appendix.md` are
generated with 23 rows, and that evidence-free `--no-run` execution marks 0 rows
as `PROOF_DRAFT_READY` rather than overclaiming equivalence. Full experiment
and workbook QA are still pending for this appendix milestone.

This run keeps explicit hand oracles for all previously manual semantic REVIEW
cases and fixes construction/statistics handling for large MightyPPL cases.
Flatten runtime still performs SAT and positive/negative TA monitoring.
Compflatten build-only now uses the real MightyPPL component-construction path,
records component-level statistics, skips BDD valuation expansion, and reports
`NOT_CHECKED_COMPFLATTEN_BUILD_ONLY` instead of pretending to have a runtime
verdict or SAT proof. This newest run also keeps the generated/reduced
MoniTAal review inputs and fixes the XML-to-MITL candidate formulas that represent
MoniTAal-style first-event monitoring. Event-triggered global candidates now
use MightyPPL's starred/current-inclusive `G*`, not strict `G`, after a
targeted probe showed strict `G` missed a first-observation request violation.
Trace-level XML candidate/baseline matches are now 33 with 0 mismatches.
The newest run also keeps `benchmark_manifest.csv/json`, a promotion ledger that
aggregates XML pair evidence into paper-review statuses without claiming formal
XML-to-MITL equivalence. The 8 previously single-trace rows now have second
independent generated review traces: `c_after_10` and `c_after_20` gained later
positive witnesses, and the six gear request/response templates gained re-armed
late-response negative witnesses.

This latest run keeps `xml_edge_guard_proofs.csv/json` and an `XML Edge Proofs`
workbook sheet. The proof ledger is conservative: it records parsed
transition/guard/reset/acceptance evidence for each XML pair, while keeping
full XML-to-MITL equivalence as a human-review claim. A targeted `recurGLB`
probe exposed and fixed a real candidate-formula omission: the XML negative
template rejects a first `p` arriving after the initial closed 10-bound, but the
previous candidate `G* (p -> F (0,10] p)` only constrained gaps after observed
`p` events. The candidate is now
`(F [0,10] p) && (G* (p -> F (0,10] p))`, with an added generated
`@0; @11 p` negative review input. The latest full run marks all 15 strong
trace-level XML candidates as `EDGE_GUARD_PROOF_READY`, with 0
`EDGE_GUARD_REVIEW_REQUIRED` rows.

## Current Workspace Shape

- Active workspace: `/home/lqq/project/TAFuzz`
- Handoff files:
  - `/home/lqq/project/TAFuzz/AGENTS.md`
  - `/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md`
  - `/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`
  - `/home/lqq/project/TAFuzz/.codex/HANDOFF_TEMPLATE.md`
- Key source areas:
  - `/home/lqq/project/TAFuzz/src/TAMonitor`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL`
  - `/home/lqq/project/TAFuzz/tool/MoniTAal`
  - `/home/lqq/project/TAFuzz/test/TARV/scripts`

## Known Local Changes To Preserve

- Modified:
  - `/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md`
  - `/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL/CMakeLists.txt`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL/MightyPPL.cpp`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL/MightyPPL.h`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL/TAwithBDDEdges.cpp`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL/TAwithBDDEdges.h`
- Untracked / added:
  - `/home/lqq/project/TAFuzz/src/TAMonitor/`
  - `/home/lqq/project/TAFuzz/test/TARV/`
  - `/home/lqq/project/TAFuzz/tool/MightyPPL/MightyPPLRuntimeOptions.cpp`
  - `/home/lqq/project/TAFuzz/analysis/tool_projects_deep_analysis.md`
  - `/home/lqq/project/TAFuzz/.codex/archive/PROJECT_STATE_20260705_pre_correctness_fix.md`

Do not revert unrelated user work.

## Key Decisions

- v1 uses BDD-label projection to canonical MoniTAal labels and keeps
  BDD-native runtime as interface/metadata only.
- `compflatten` runtime remains an explicit unsupported mode in v1; no fake
  runtime verdicts.
- `CFn/COn/CGn/CHn` are excluded from user-level MITL regression because the
  user clarified they are internal compiled forms.
- XML-to-MITL output is a conservative candidate layer for manual review, not
  an automatic equivalence proof.
- Correctness is now tracked separately from execution success:
  - `VERIFIED` means a hand oracle or comparable baseline exists and matches.
  - `NEEDS_MANUAL_ORACLE`, `RESOURCE_LIMIT`, `TIMEOUT`, `BUILD_TIMEOUT`, and
    baseline timeout rows are not counted as verified.
- Hand oracle means an expected verdict written independently of TAMonitor from
  the MITL/operator semantics and the concrete trace, recorded in
  `semantic_cases.csv` as `expected_final`, `expected_sat`, and `rationale`.
- The 14 previously `NEEDS_MANUAL_ORACLE` semantic cases now have hand oracles
  for Release/Trigger, past strict/weak operators, and Pnueli cases. With the
  added `G*` regression, the semantic verified count is now 36 and semantic
  manual-oracle debt is 0.
- A real mismatch exposed by the correctness audit was fixed:
  `recurGLB.xml` changed from candidate `G (F [0,10] p)` to
  `G (p -> F (0,10] p)`, matching MoniTAal baseline on the available input.
- A later `recurGLB` prefix-semantics probe found the above still missed the
  XML initial p-within-10 obligation. The current candidate is
  `(F [0,10] p) && (G* (p -> F (0,10] p))`, verified on original, first-late,
  and re-armed-late traces.
- A real first-event semantic bug in XML candidate generation was fixed:
  request/response, absence, and recurrence candidates generated with strict
  `G` missed violations when the triggering event was the first observation.
  They now use `G*`, and the regression case
  `future_globally_star_initial_trigger_violate` verifies
  `G* (a -> F [0,30] b)` returns `NEGATIVE` on `@0 a; @31 b`.
- TAMonitor now has `--build-only`. Flatten build-only still performs SAT and
  construction/statistics; compflatten build-only performs component
  construction/statistics only. Both explicitly report final verdict
  `NOT_RUN_BUILD_ONLY` with `run_mode=build_only`.
- TAMonitor now exposes BDD resource parameters in CLI/report output:
  `--bdd-nodes`, `--bdd-cache`, and `--bdd-max-increase`.
- MightyPPL stdout capture inside TAMonitor is bounded to avoid GB-scale
  diagnostic strings during large product construction.
- XML candidate manual-review notes for the latest run are in
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_recur_fix_full/manual_xml_candidate_review.md`.
- Generated review inputs are explicitly tracked in
  `monitaal_embedded_benchmarks.csv` and under
  `generated_monitaal_inputs/`; they are trace-level validation aids, not
  original MoniTAal benchmark inputs.
- Generated review inputs are now bound to specific positive/negative template
  pairs, preventing one reduced gear-controller trace from being run against
  unrelated templates in the same XML file.
- `benchmark_manifest.csv/json` is now the promotion handoff artifact:
  15 XML pairs are `STRONG_TRACE_LEVEL_CANDIDATE`, 2 are
  `APPROXIMATE_TRACE_ONLY`, 4 are `NOT_CLAIMED`, 1 is
  `APPROXIMATE_UNVERIFIED`, and 1 is `NO_INPUT_NOT_PROMOTED`. There are now
  0 `SINGLE_TRACE_LEVEL_CANDIDATE` rows. All promoted rows still explicitly
  require formal edge/guard proof before full XML-to-MITL equivalence is claimed.
- Pure gear boundary-positive traces were not used as second evidence because
  MoniTAal did not terminate quickly on those finite prefixes. The accepted
  second gear traces instead test request-obligation reset: one boundary-timely
  response followed by a re-armed late response.
- `xml_edge_guard_proofs.csv/json` is now the edge/guard proof handoff
  artifact. It is a proof checklist, not a theorem: `EDGE_GUARD_PROOF_READY`
  means the parsed XML has the expected trigger/response or forbidden-event
  edges, clock guards, resets, and acceptance roles for manual proof review.
- `f(g(notb)_and_g(f(a)).xml` remains unpromoted: a diagnostic negative probe
  did not align with the current candidate semantics, and a longer baseline
  probe timed out. Do not claim this XML has a valid MITL translation until the
  formula is revised and rechecked.

## Current Result Artifacts

Newest review workbook:

`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_recur_fix_full/paper_review_results.xlsx`

Important CSV/JSON files in the same directory:

- `experiment_summary.json`
- `mitl_correctness_audit.csv`
- `semantic_regression_results.csv`
- `monitaal_xml_inventory.csv`
- `monitaal_translation_review.csv`
- `benchmark_manifest.csv`
- `benchmark_manifest.json`
- `xml_edge_guard_proofs.csv`
- `xml_edge_guard_proofs.json`
- `monitaal_transition_details.csv`
- `translation_candidate_results.csv`
- `monitaal_baseline_results.csv`
- `monitaal_embedded_benchmarks.csv`

Workbook now has 12 sheets:

Summary, Correctness Audit, Semantic Results, Semantic Cases, XML Inventory,
Translation Review, Benchmark Manifest, XML Edge Proofs, Transition Details,
Candidate Results, Baseline Results, Embedded Benchmarks.

## Verification Status

Latest full command:

`python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --out test/TARV/results/paper_experiments_recur_fix_full`

Latest milestone probe command:

`python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --no-workbook --out test/TARV/results/paper_experiments_second_traces_probe`

Probe summary:

- semantic cases: 53
- semantic correctness verified: 36
- semantic fail/error: 0/0
- Benchmark manifest rows: 23
- Manifest strong trace-level candidates: 15
- Manifest single trace-level candidates: 0
- Manifest approximate trace-only candidates: 2
- Candidate/baseline matches: 33
- Candidate/baseline mismatches: 0
- Candidate baseline not verified due timeout: 7
- MoniTAal baselines: 33 ran, 8 timed out, 4 skipped no input
- Embedded/generated benchmark records: 29
- Workbook status: skipped for this probe

Summary from `experiment_summary.json`:

- semantic cases: 53
- semantic correctness verified: 36
- semantic needs manual oracle: 0
- semantic runtime resource limit: 0
- semantic runtime timeout: 0
- semantic compflatten build/stat-only: 17
- semantic build timeout: 0
- semantic fail/error: 0/0
- XML templates: 60
- XML transition detail rows: 386
- XML pairs: 23
- XML-to-MITL candidates: 19
- Benchmark manifest rows: 23
- Manifest strong trace-level candidates: 15
- Manifest single trace-level candidates: 0
- Manifest approximate trace-only candidates: 2
- Manifest rows not immediately eligible for manual paper review: 8
- XML edge/guard proof rows: 23
- XML edge/guard proof ready: 15
- XML edge/guard review required: 0
- XML edge/guard not ready: 8
- XML edge/guard incomplete: 0
- TAMonitor candidate runs: 41/41 succeeded
- Candidate/baseline matches: 34
- Candidate/baseline mismatches: 0
- Candidate baseline not verified due timeout: 7
- MoniTAal baselines: 34 ran, 8 timed out, 4 skipped no input
- Embedded/generated benchmark records: 30

QA checks completed:

- `python3 -m py_compile test/TARV/scripts/run_paper_experiments.py src/TAMonitor/make_tamonitor_xlsx.py`
- `python3 -m json.tool test/TARV/results/paper_experiments_recur_fix_full/experiment_summary.json`
- `python3 -m json.tool test/TARV/results/paper_experiments_recur_fix_full/benchmark_manifest.json`
- `python3 -m json.tool test/TARV/results/paper_experiments_recur_fix_full/xml_edge_guard_proofs.json`
- `unzip -t test/TARV/results/paper_experiments_recur_fix_full/paper_review_results.xlsx`
- workbook formula-error scan matched 0 entries
- workbook inspect found 12 sheets and 12 tables
- rendered preview PNGs exist for all 12 sheets and key sheets were visually checked
- benchmark manifest status counts:
  - `STRONG_TRACE_LEVEL_CANDIDATE`: 15
  - `SINGLE_TRACE_LEVEL_CANDIDATE`: 0
  - `APPROXIMATE_TRACE_ONLY`: 2
  - `APPROXIMATE_UNVERIFIED`: 1
  - `NOT_CLAIMED`: 4
  - `NO_INPUT_NOT_PROMOTED`: 1
- generated-input candidates:
  - `a-b copy.xml`, `a-b.xml`, and `a-b30.xml` on initial late-response
    reduced traces: MoniTAal `NEGATIVE`, TAMonitor `NEGATIVE` with
    `G* (a -> F [0,30] b)`
  - `absentAQ.xml` and `absentBR.xml` on initial boundary-violation reduced
    traces: MoniTAal `NEGATIVE`, TAMonitor `NEGATIVE` with `G*` absence
    candidates
  - `c_after_10.xml` on `@0 a; @10 c`: MoniTAal `POSITIVE`, TAMonitor
    `POSITIVE`
  - `c_after_10.xml` on `@0 a; @11 c`: MoniTAal `POSITIVE`, TAMonitor
    `POSITIVE`
  - `c_after_20.xml` on `@0 a; @20 c`: MoniTAal `POSITIVE`, TAMonitor
    `POSITIVE`
  - `c_after_20.xml` on `@0 a; @21 c`: MoniTAal `POSITIVE`, TAMonitor
    `POSITIVE`
  - `only_ab_until10.xml` on `@0 a; @5 c`: MoniTAal `NEGATIVE`, TAMonitor
    `NEGATIVE`
  - `only_ab_until10.xml` after-bound and boundary variants:
    MoniTAal/TAMonitor `POSITIVE` and `NEGATIVE` respectively
  - `recurGLB.xml` initial late recurrence: MoniTAal `NEGATIVE`, TAMonitor
    `NEGATIVE` with `(F [0,10] p) && (G* (p -> F (0,10] p))`
  - `recurGLB.xml` first late p `@0; @11 p`: MoniTAal `NEGATIVE`, TAMonitor
    `NEGATIVE` with the same corrected candidate
  - gear-controller initial-late and re-armed-late reduced negative traces for
    `CloseClutch`, `OpenClutch`, `ReqNeu`, `ReqSet`, `SpeedSet`, and `test1`:
    MoniTAal `NEGATIVE`, TAMonitor `NEGATIVE`
- runtime smoke for `F [0,2] p1` produced final verdict `POSITIVE` and a
  valid `results.xlsx`
- build-only smoke for `F [0,2] p1` produced final verdict
  `NOT_RUN_BUILD_ONLY`, `run_mode=build_only`, and a valid `results.xlsx`
- `git diff --check`

## Active Risks / Known Limits

- Not every benchmark-derived row is verified correct yet:
  - 7 candidate MITL rows lack comparable baseline verdict because MoniTAal
    baseline timed out.
- Flatten monolithic construction still explodes on some large negative
  automata; v1 now uses compflatten build-only statistics for those construction
  cases instead of claiming a flatten runtime verdict.
- Compflatten build-only reports construction statistics only; formula
  satisfiability is explicitly `NOT_CHECKED_COMPFLATTEN_BUILD_ONLY`.
- XML-to-MITL candidates still require manual transition/guard review before
  being claimed as formal equivalence; the manifest is a promotion ledger, not
  a proof.
- Four XML rows still have no input and no generated trace-level review input.
- BDD-native runtime is not implemented in v1.

## Next Steps

1. Run the full proof-appendix experiment with workbook generation and QA; the
   expected promoted appendix count is 15 `PROOF_DRAFT_READY` rows and 8
   excluded rows.
2. Rerun the original gear-controller and `b_live_a_freq` baseline timeout
   rows with longer timeout if the paper needs original-input baseline verdicts;
   reduced negative gear traces are already verified.
3. Revisit or drop the current candidate for
   `f(g(notb)_and_g(f(a)).xml`; do not promote it in its current form.

## Recovery Prompt

请先读 `/home/lqq/project/TAFuzz/AGENTS.md`、
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md` 和
`/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`，然后从当前状态继续，
不要重新从头探索，不要回滚用户改动。当前最新结果目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_recur_fix_full`；
当前进行中的 proof appendix 探针目录是
`/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_proof_appendix_norun_probe`。
