# TAFuzz Session Log

## 2026-06-26 CST

- Created the top-level Codex handoff system for `/home/lqq/download/TAFuzz`.
- Added `AGENTS.md`, `.codex/PROJECT_STATE.md`, `.codex/SESSION_LOG.md`,
  `.codex/HANDOFF_TEMPLATE.md`, and `.codex/agents/README.md`.
- Confirmed the top-level `.git/` directory was empty and not a valid Git
  repository, then moved it to `.git.EMPTY_DIR_DO_NOT_USE_20260626` to avoid
  future root-level Git confusion.
- Recorded existing nested repository changes in `tool/MightyPPL` and
  `tool/MoniTAal`.
- Verified the handoff files exist and are readable, both nested repository
  statuses are preserved, and the empty `.git/` directory has been safely
  isolated.
- Did not modify source files inside `tool/MightyPPL` or `tool/MoniTAal`.
- Next: use the recovery prompt in `.codex/PROJECT_STATE.md` when continuing in
  a new thread/model or after context compaction.

## 2026-06-26 09:05 CST

- Goal: move MightyPPL and MoniTAal under `TAFuzz/tool/` and make MightyPPL
  build directly against the adjacent MoniTAal working tree.
- Work completed: moved the repositories to `tool/MightyPPL` and `tool/MoniTAal`;
  changed MightyPPL's `monitaal` ExternalProject to use `SOURCE_DIR
  ${CMAKE_CURRENT_SOURCE_DIR}/../MoniTAal`; removed pinned MoniTAal clone/patch
  behavior; adapted MightyPPL calls to the current MoniTAal API; fixed MoniTAal
  CMake dependency ordering and template header qualifiers needed by MightyPPL.
- Files changed: `tool/MightyPPL/CMakeLists.txt`,
  `tool/MightyPPL/main.cpp`, `tool/MightyPPL/TAwithBDDEdges.cpp`,
  `tool/MoniTAal/CMakeLists.txt`,
  `tool/MoniTAal/src/monitaal/CMakeLists.txt`,
  `tool/MoniTAal/src/monitaal/state.h`.
- Verification: `cmake --build . -j2` from
  `/home/lqq/download/TAFuzz/tool/MightyPPL/build` completed successfully;
  `build/mitppl --help` printed usage and exited `1` as expected when no spec
  file is supplied.
- Blockers / skipped checks: no full spec-based semantic test was run; clean
  external builds may still hit transient GitHub HTTPS clone failures for
  MoniTAal's external dependencies, but retry succeeded during this session.
- Next: continue using `tool/MoniTAal` as the editable MoniTAal working tree and
  rebuild with `cmake --build . -j2` from `tool/MightyPPL/build`.

## 2026-06-26 09:30 CST

- Goal: publish the full TAFuzz source workspace, including handoff files, to
  `PearBabe/TAFuzz` on `main`.
- Work completed: created `/home/lqq/download/TAFuzz_publish_main` as a clean
  clone of the remote, synced `AGENTS.md`, `.codex/`, `tool/MightyPPL/`, and
  `tool/MoniTAal/`, excluded nested Git metadata and build artifacts, committed
  the snapshot, and pushed it to GitHub.
- Files changed: no source files were edited; `.codex/PROJECT_STATE.md` and
  `.codex/SESSION_LOG.md` were updated after publishing to record the result.
- Verification: the initial source snapshot commit was
  `2b6594ceb41c9429a2327b7989f723067063943e`; the publish clone had no nested
  `.git` paths and no `160000` gitlink entries; key paths such as `AGENTS.md`,
  `.codex/PROJECT_STATE.md`, `tool/MightyPPL/CMakeLists.txt`, and
  `tool/MoniTAal/CMakeLists.txt` existed in the published commit.
- Blockers / skipped checks: HTTPS push could not prompt for credentials, so
  the publish clone was switched to SSH remote `git@github.com:PearBabe/TAFuzz.git`;
  no rebuild was run during publishing.
- Next: for future publishes, use `/home/lqq/download/TAFuzz_publish_main` and
  re-run the nested `.git` plus gitlink checks before pushing.

## 2026-06-26 09:45 CST

- Goal: create a reusable Codex skill for one-command TAFuzz publishing after
  source edits.
- Work completed: created local skill `publish-tafuzz` under
  `/mnt/c/Users/lqq27/.codex/skills/publish-tafuzz`; added
  `scripts/publish_tafuzz.sh` to sync `/home/lqq/download/TAFuzz` into
  `/home/lqq/download/TAFuzz_publish_main`, remove nested Git metadata, force-add
  required ignored external dependency files, verify no gitlinks, commit, and
  push to `git@github.com:PearBabe/TAFuzz.git`.
- Files changed: skill files under `/mnt/c/Users/lqq27/.codex/skills/publish-tafuzz`;
  this handoff entry in `.codex/SESSION_LOG.md`; matching state update in
  `.codex/PROJECT_STATE.md`.
- Verification: `bash -n` passed for the publish script; skill validation
  reported `Skill is valid!`; a dry run from `/home/lqq/download/TAFuzz` updated
  the publish clone and reported no changes when already in sync.
- Blockers / skipped checks: no source rebuild was run because this change only
  added publish automation and handoff notes.
- Next: after editing TAFuzz, run
  `/mnt/c/Users/lqq27/.codex/skills/publish-tafuzz/scripts/publish_tafuzz.sh -m
  "Update TAFuzz workspace"` from anywhere under the source tree.

## 2026-06-26 13:49 CST

- Goal: generate a Chinese static HTML report mapping the MightyPPL and
  MoniTAal papers to the current code worktrees under `tool/`.
- Work completed: added
  `analysis/scripts/generate_paper_code_report.py`, generated
  `analysis/mightyppl_monitaal_paper_code_report.html`, and wrote supporting
  compact PDF/page, code inventory, mapping summary, and status JSON files under
  `analysis/data/`.
- Report coverage: includes project overview, MightyPPL paper-code chapter,
  MoniTAal paper-code chapter, cross-repo reuse mapping, gaps/engineering
  deviations, file inventory, verification notes, inline SVG diagrams, and
  local code links with line anchors.
- Verification: `python3 -m py_compile` passed for the generator; regenerating
  the report succeeded; every JSON file in `analysis/data/` parsed
  successfully; the final HTML contained the required section keywords; it had
  72 local TAFuzz links, 0 external URLs, 0 `<script>` tags, and 3 inline SVGs;
  `tool/MightyPPL/build/mitppl --help` printed usage and exited `1` as
  expected without a spec file.
- Blockers / skipped checks: no full spec-based semantic test and no full paper
  experiment reproduction were run; the report marks these as not re-run.
- Next: open
  `/home/lqq/download/TAFuzz/analysis/mightyppl_monitaal_paper_code_report.html`
  in a browser for reading, or rerun
  `python3 /home/lqq/download/TAFuzz/analysis/scripts/generate_paper_code_report.py`
  after code/PDF changes.

## 2026-07-04 23:14 CST

- Goal: implement the approved plan to create a detailed Markdown engineering
  analysis of `tool/MightyPPL` and `tool/MoniTAal` for future TAMonitor work.
- Work completed: added `analysis/tool_projects_deep_analysis.md` with a
  Chinese deep dive covering build entrypoints, CLI behavior, MITL visitor
  flow, BDD-labelled automata, flatten/compflatten modes, MoniTAal
  TA/Parser/EventParser/Fixpoint/Monitor/state internals, integration risks,
  and recommended TAMonitor cut points.
- Files changed: `analysis/tool_projects_deep_analysis.md`,
  `.codex/PROJECT_STATE.md`, and this session log.
- Verification: `test -s` plus `wc -l` confirmed the report exists with 755
  lines; `rg` found the required keywords `MightyPPL`, `MoniTAal`,
  `TAMonitor`, `BDD`, `flatten`, `compflatten`, `Fixpoint`, `Monitor`, and
  `风险`; `git -C tool/MightyPPL status --short` and `git -C tool/MoniTAal
  status --short` showed only top-level documentation/handoff changes from
  this task, not tool source edits.
- Blockers / skipped checks: no source build, unit test, or benchmark was run
  because this was a documentation-only task.
- Next: use `analysis/tool_projects_deep_analysis.md` as the starting map for
  TAMonitor implementation, especially the BDD-label, XML-dialect, dual
  automata, and global-state boundaries.

## 2026-07-04 23:54 CST

- Goal: implement the approved TAMonitor v1 plan connecting MightyPPL and
  MoniTAal for research-grade MITL runtime verification.
- Work completed: added the `TAMonitor` executable target in
  `tool/MightyPPL/CMakeLists.txt`; added `src/TAMonitor/` with CLI parsing,
  MightyPPL adapter, trace parser, MoniTAal-based monitor runner, CSV/JSON/XLSX
  reporting, and a BDD-native metadata stub; added
  `tool/MightyPPL/MightyPPLRuntimeOptions.cpp`; extended MightyPPL to expose
  NNF/proposition/projection metadata; added
  `TAwithBDDEdges::projection_expanded(...)` to expand BDD labels into
  canonical `bits:<...>` labels for MoniTAal.
- Test artifacts added: `test/TARV/cases/smoke_f_01.mitl`,
  `test/TARV/cases/smoke_f_01.trace`,
  `test/TARV/cases/benchmark_manifest.json`,
  `test/TARV/baselines/xml-mitl-mapping.v1.json`, and
  `test/TARV/cases/monitaal_a_b_negative.input`.
- Verification: CMake configure for `tool/MightyPPL/build` succeeded after a
  transient external `pugixml` clone retry; `cmake --build
  tool/MightyPPL/build --target TAMonitor -j2` succeeded; `cmake --build
  tool/MightyPPL/build --target mitppl -j2` succeeded; infinite and finite
  smoke runs for `F [0,2] p1` returned SAT and final verdict `POSITIVE`;
  generated CSV/JSON/XLSX files were present; `unzip -t` passed for both
  smoke workbooks; generated JSON parsed successfully.
- Baseline check: built `MoniTAal-bin` with `MONITAAL_BUILD_BIN=ON` in the
  external MoniTAal build tree and ran `a-b.xml` with the recorded input; it
  monitored 11 events and ended with verdict `NEGATIVE`.
- Debug note: the first TAMonitor smoke revealed a reset-clock index mismatch
  in the new canonical projection path; fixed by deriving copied clock names
  from actual invariants, guards, and resets rather than trusting the old
  product clock count.
- Known limits: runtime monitoring is implemented for `--build-mode flatten`;
  `compflatten` now fails explicitly as `unsupported_runtime_mode`; BDD-native
  runtime is metadata/interface only; XML-to-MITL benchmark equivalence remains
  manual and conservative.
- Next: run final lightweight verification after the handoff update, inspect
  diffs for accidental debug/dead code, and then report the completed v1 status
  plus remaining research-scale benchmark work.

## 2026-07-04 23:59 CST

- Goal: final TAMonitor v1 cleanup and verification after updating the handoff.
- Work completed: removed temporary canonical-projection construction output
  from `TAwithBDDEdges::projection_expanded`; changed TAMonitor
  satisfiability checks to match MoniTAal monitor initialization by checking
  non-empty intersection of the initial state with the finite/infinite accepting
  region; allowed interactive MITL formula entry when neither `--formula` nor
  `--formula-inline` is provided.
- Verification: rebuilt `TAMonitor` successfully; re-ran infinite and finite
  smoke cases for `F [0,2] p1`, both SAT with final verdict `POSITIVE`; piped
  an interactive formula into `TAMonitor` and got SAT / `POSITIVE`;
  `python3 -m py_compile src/TAMonitor/make_tamonitor_xlsx.py` succeeded;
  generated metadata JSON parsed; `unzip -t` passed for the final smoke XLSX.
- Guard checks: `--build-mode compflatten` fails explicitly with
  `unsupported_runtime_mode`; `--max-valuations 1` fails explicitly with
  `BDD projection valuation limit exceeded`.
- Current state: TAMonitor v1 flatten runtime is implemented and smoke
  verified; compflatten and BDD-native runtime remain intentionally unsupported
  runtime paths for future research implementation.
- Next: expand semantic regression cases and manually reviewed benchmarks
  before claiming paper-level experimental completeness.

## 2026-07-05 00:15 CST

- Goal: extend TAMonitor experiments toward paper-review coverage for
  MightyPPL grammar semantics and MoniTAal benchmarks/XML review.
- Work completed: added `test/TARV/scripts/run_paper_experiments.py` to
  generate and run semantic regression cases, existing MightyPPL testcase
  construction/stat cases, MoniTAal XML inventory, positive/negative template
  pairing, conservative candidate MITL translation rows, and available XML
  baseline runs; added `test/TARV/scripts/build_paper_review_workbook.mjs` to
  generate a review workbook from the produced CSV/JSON files.
- Subagent result incorporated: MightyPPL `CFn/COn/CGn/CHn` are grammar-visible
  Count forms but should be treated as internal NNF/construction branches, so
  the harness labels them `internal_grammar_branch` instead of claiming normal
  user-level MITL support.
- Verification so far: scripts have been written but not yet executed.
- Next: py-compile the Python harness, run the paper experiment script, inspect
  CSV/XLSX outputs, then update handoff with observed counts and blockers.

## 2026-07-05 00:41 CST

- Goal: execute the paper-review TAMonitor experiment expansion and produce
  hand-reviewable results.
- Work completed: incorporated both read-only subagent findings; tightened
  MightyPPL Count handling as `internal_grammar_branch`; added MoniTAal
  uppercase-label to MightyPPL AP mapping; extracted embedded MoniTAal benchmark
  XML/input for `b_live_a_freq` and `gear_controller_test`; recorded
  `gear_controller_model` as duplicate of `gear-control-properties.xml` and
  `gear_controller_newgear_prop.h` as C++-constructed TA, not direct XML.
- Execution: ran
  `python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --out
  test/TARV/results/paper_experiments_full`; earlier partial runs exposed two
  harness bugs, which were fixed before the final run: process-group timeout
  cleanup for `MoniTAal-bin`, and over-broad input matching where `a-b` matched
  `absent*input`.
- Final outputs: generated CSV/JSON artifacts and
  `test/TARV/results/paper_experiments_full/paper_review_results.xlsx` with 8
  sheets: Summary, Semantic Results, Semantic Cases, XML Inventory,
  Translation Review, Candidate Results, Baseline Results, Embedded Benchmarks.
- Observed results: 60 semantic cases ran; 20 PASS, 5 FAIL, 10 REVIEW, 17
  ERROR, 8 REVIEW_UNSUPPORTED Count/internal grammar cases. MoniTAal inventory
  found 60 templates and 23 positive/negative pairs. The harness produced 19
  candidate MITL translations and ran 15 candidate MITL cases through
  TAMonitor; 14 exited successfully and one approximate candidate crashed.
  MoniTAal XML baselines completed 8 runs, timed out 8 gear/embedded runs, and
  skipped 7 pairs with no input file.
- QA: `unzip -t paper_review_results.xlsx` passed; all 8 workbook sheets were
  rendered to preview PNGs; workbook formula-error scan found 0 entries;
  `python3 -m py_compile test/TARV/scripts/run_paper_experiments.py` passed;
  `git diff --check` passed.
- Current blockers exposed by real experiments: unbounded interval `stoi`,
  Pnueli crashes, Count/internal grammar crashes, BDD projection valuation
  limits, and memory corruption on several large MightyPPL existing benchmarks.
- Next: manually review the workbook, then fix the exposed correctness/stability
  issues before treating the benchmark set as paper-grade final evidence.

## 2026-07-05 01:12 CST

- Goal: start fixing real TAMonitor/MightyPPL bugs exposed by the full
  paper-review experiment run while preserving handoff continuity.
- Work completed: fixed raw Count-form handling in TAMonitor so
  `CFn/COn/CGn/CHn` now return a clear `unsupported_user_formula` error instead
  of aborting; fixed product-bound normalization when `gcd == 0`, which removed
  the `SIGFPE` path for untimed or `[0,infty)` formulas; fixed old
  `TAwithBDDEdges::projection()` and `projection_bdd()` clock-map copying by
  sharing the safer referenced-clock inference/validation used by canonical
  projection; added `normalized_formula` to TAMonitor reports.
- Verification: rebuilt `TAMonitor`; `F [0,infty) p1`, `F p1`, pure `p1`, and
  the four Pnueli semantic cases all completed without crashes; all eight raw
  Count cases now fail cleanly with the explicit unsupported diagnostic;
  selected bugfix metadata JSON and XLSX artifacts validated successfully.
- Subagent results incorporated: Pnueli crash came from internal
  `intersection()` calling old projection before final canonical projection;
  XML-to-MITL benchmark candidates should remain manually tiered, with `a-b*`,
  selected gear response templates, and `recurGLB` as strongest review
  candidates, while approximate/not-claimed rows must not be advertised as
  equivalent.
- Next: run the full experiment harness again after these fixes, inspect
  remaining failures/memory corruptions, and continue fixing real causes before
  producing updated workbook results.

## 2026-07-05 01:36 CST

- Goal: continue the experiment-and-fix loop, remove non-user Count formulas
  from ordinary MITL semantic regression, fix remaining true/open-interval
  failures, and regenerate paper-review results.
- User clarification incorporated: `CGn/CFn/COn/CHn` are internal MightyPPL
  compiled formulas, not ordinary MITL formulas, so they should not be tested
  as user-level MITL formulas. The harness now excludes them from semantic
  regression and records eight internal Count forms as excluded metadata.
- Work completed: added a TAMonitor-specific runtime option to disable
  MightyPPL product-bound gcd scaling. This fixes the time-scale mismatch where
  product guards were divided by `gcd` but TAMonitor traces remained in
  MoniTAal's absolute input time scale. The bug caused `F [0,2) p1` and
  `F (0,2) p1` with `p1` at time 1 to return `NEGATIVE`; both now return
  `POSITIVE`.
- Harness fixes: changed `atom_true_under_f` to include a future observation at
  time 1; classified existing MightyPPL testcases as `BUILD_STATS`,
  `RESOURCE_LIMIT`, or `TIMEOUT` instead of semantic failures; preserved
  explicit summary fields for resource limits and timeouts.
- Verification: rebuilt `TAMonitor` and `mitppl`; ran targeted interval tests
  for `F [0,2) p1`, `F (0,2) p1`, `F [0,2] p1`, and `F [0,infty) p1`, all SAT
  / `POSITIVE`; ran semantic-only regression with 52 cases and got no
  `FAIL`/`ERROR`; ran full paper experiment to
  `test/TARV/results/paper_experiments_scale_fix`.
- Final scale-fix results: semantic 21 PASS, 14 REVIEW, 6 BUILD_STATS,
  7 RESOURCE_LIMIT, 4 TIMEOUT, 0 FAIL, 0 ERROR. XML inventory: 60 templates,
  23 positive/negative pairs, 19 MITL candidates. TAMonitor candidate runs:
  15/15 successful. MoniTAal native baselines: 8 ran, 8 timed out, 7 skipped for
  no input. Workbook generated successfully.
- QA: `unzip -t paper_review_results.xlsx` passed; `python3 -m json.tool
  experiment_summary.json` passed; `python3 -m py_compile
  test/TARV/scripts/run_paper_experiments.py src/TAMonitor/make_tamonitor_xlsx.py`
  passed; `git diff --check` passed.
- Next: manually review the workbook, especially XML-to-MITL candidates. Strong
  candidates include `a-b*`, `recurGLB`, and gear request-response templates;
  approximate candidates such as `absentBQR`, `recurBQR`, and `b_live_a_freq`
  must not be claimed equivalent without manual edge/guard review. Decide
  whether v1 resource-limit/timeouts are acceptable boundaries or whether to
  implement BDD-native runtime before large-testcase claims.

## 2026-07-05 01:47 CST

- Goal: answer the user's correctness concern by separating successful runs
  from verified verdicts and improving manual XML/MITL review evidence.
- Work completed: added `monitaal_transition_details.csv` with one row per XML
  transition, including source/target locations, accepting/initial flags,
  guards, assignments, sync labels, AP candidates, pair role, and linked
  candidate MITL metadata; added workbook sheets `Transition Details` and
  `Correctness Audit`; added correctness fields to semantic and candidate
  result CSVs.
- Real bug fixed during experiment: the audit found one candidate/baseline
  mismatch for `recurGLB.xml`. The previous candidate `G (F [0,10] p)` produced
  TAMonitor `INCONCLUSIVE` while MoniTAal baseline was `NEGATIVE`; updated the
  candidate to `G (p -> F (0,10] p)`, which now returns `NEGATIVE` and matches
  the baseline on the available input.
- Files changed: `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`,
  `/home/lqq/project/TAFuzz/test/TARV/scripts/build_paper_review_workbook.mjs`,
  `/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md`,
  `/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md`, and
  `/home/lqq/project/TAFuzz/.codex/archive/PROJECT_STATE_20260705_pre_correctness_fix.md`.
- Verification: ran full experiment to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_correctness_fix`;
  semantic correctness verified 21, needs manual oracle 14, resource limit 7,
  timeout 4, build/stat-only 6, fail/error 0/0; candidate/baseline matches 8,
  mismatches 0, baseline-timeout not verified 7; XML transition detail rows
  386; workbook status ok.
- QA: `python3 -m py_compile test/TARV/scripts/run_paper_experiments.py
  src/TAMonitor/make_tamonitor_xlsx.py` passed; `python3 -m json.tool` passed
  for the latest summary; `unzip -t paper_review_results.xlsx` passed; workbook
  formula-error scan matched 0 entries; workbook inspect found 10 sheets and
  10 tables; preview PNGs exist for all sheets; `git diff --check` passed.
- Blockers / skipped checks: not every MITL verdict is verified yet. The
  unverified set is explicit in `mitl_correctness_audit.csv`: 14 semantic cases
  need hand oracle review, 7 large cases hit resource limits, 4 timed out, and
  7 XML candidates lack a baseline verdict because MoniTAal timed out.
- Next: add hand oracles for the 14 manual semantic cases, manually review XML
  transition details before promoting candidates, and decide whether to
  implement BDD-native runtime or treat resource-limit/timeouts as v1 limits.

## 2026-07-05 02:04 CST

- Goal: reduce semantic correctness debt by turning the 14
  `NEEDS_MANUAL_ORACLE` MITL semantic cases into independently checked oracle
  cases where justified.
- Work completed: added explicit hand oracle verdicts, SAT expectations, and
  rationale strings for Release/Release*, strict and weak past O/H/S/T, and
  Pnueli Fn/On/Gn/Hn regression cases in
  `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py`.
  Clarified in state that a hand oracle is an expected answer derived from the
  operator semantics and trace, not TAMonitor's own output.
- Verification: semantic-only rerun produced `PASS: 35`,
  `RESOURCE_LIMIT: 7`, `BUILD_STATS: 6`, `TIMEOUT: 4`, with no FAIL/ERROR.
  Full rerun to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_oracle_fix`
  produced semantic verified 35, manual oracle debt 0, fail/error 0/0,
  candidate/baseline matches 8, candidate/baseline mismatches 0, and 7
  candidate rows still not verified because MoniTAal baseline timed out.
- QA: `python3 -m py_compile test/TARV/scripts/run_paper_experiments.py`
  passed; `python3 -m json.tool` passed for the oracle-fix summary; `unzip -t`
  passed for the oracle-fix workbook; workbook formula-error scan matched 0
  entries; workbook inspect found 10 sheets and 10 tables; all 10 preview PNGs
  exist; `git diff --check` passed.
- Blockers / skipped checks: resource-limit and timeout rows are still not
  verified correct; baseline-timeout XML candidates remain not verified against
  MoniTAal; XML-to-MITL equivalence is still candidate/manual-review level.
- Next: manually review XML transition details before promoting candidates,
  decide whether to implement BDD-native runtime or formalize v1 resource
  limits, and add extra independent boundary traces if paper coverage needs
  more than one oracle per complex operator.

## 2026-07-05 02:24 CST

- Goal: separate construction/statistics experiments from runtime verdict
  verification so large MightyPPL cases are not mislabeled as runtime resource
  limits or runtime timeouts.
- Work completed: added TAMonitor `--build-only`, including CLI parsing,
  config plumbing, report metadata `run_mode`, build-only final verdict
  `NOT_RUN_BUILD_ONLY`, disabled canonical BDD valuation expansion for
  build-only runs, and allowed compflatten construction checks without claiming
  runtime monitoring support.
- Harness update: existing MightyPPL build/stat cases now pass `--build-only`;
  construction timeouts are classified as `BUILD_TIMEOUT` with correctness
  status `NOT_A_VERDICT_CHECK_BUILD_TIMEOUT` instead of runtime verdict
  failures.
- Verification: rebuilt `TAMonitor`; full experiment rerun to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_build_only_fix`
  produced semantic verified 35, manual oracle debt 0, runtime resource limit
  0, runtime timeout 0, build/stat-only 11, construction build timeout 6,
  fail/error 0/0, candidate/baseline matches 8, mismatches 0, and 7 candidate
  rows still not verified because MoniTAal baseline timed out.
- QA: `python3 -m json.tool` passed for the latest summary; `unzip -t` passed
  for the latest workbook and both smoke workbooks; workbook formula-error scan
  matched 0 entries; workbook inspect found 10 sheets and 10 tables; rendered
  preview PNGs exist; `python3 -m py_compile` passed for the experiment scripts;
  `git diff --check` passed.
- Smoke results: runtime smoke `F [0,2] p1` on
  `test/TARV/cases/smoke_f_01.trace` returned final verdict `POSITIVE`;
  build-only smoke for the same formula returned `NOT_RUN_BUILD_ONLY` with
  `run_mode=build_only`.
- Remaining limits: 6 large construction cases still time out during TA
  construction; 7 XML-derived MITL candidates still lack a comparable MoniTAal
  baseline verdict because the native baseline timed out; XML-to-MITL candidates
  remain manual-review candidates, not formal equivalence claims.

## 2026-07-05 02:45 CST

- Goal: remove the remaining construction-timeout debt without changing MITL
  semantics, and make compflatten build-only honest rather than a disguised
  flatten run.
- Real bugs fixed: TAMonitor's MightyPPL stdout capture is now bounded, avoiding
  unbounded GB-scale diagnostic strings during large product construction;
  TAMonitor now exposes `--bdd-nodes`, `--bdd-cache`, and
  `--bdd-max-increase` and records those values in reports; `compflatten
  --build-only` now uses MightyPPL's component-construction path and reports
  component-level stats with satisfiability
  `NOT_CHECKED_COMPFLATTEN_BUILD_ONLY`.
- Harness update: existing MightyPPL testcase rows now run as compflatten
  construction/statistics-only cases, while the 35 semantic oracle cases still
  run flatten runtime monitoring. Semantic CSVs now include `build_mode` and
  component counts.
- Verification: rebuilt `TAMonitor`; flatten runtime smoke for `F [0,2] p1`
  returned `POSITIVE`; compflatten build-only smoke returned
  `NOT_RUN_BUILD_ONLY`; acacia3 compflatten build-only completed in about
  0.24s and about 49 MB RSS, where the previous pseudo-compflatten path timed
  out around 45s and several GB RSS.
- Full experiment rerun:
  `python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --out
  test/TARV/results/paper_experiments_compflatten_stats_fix`. Summary:
  semantic verified 35, manual oracle debt 0, runtime resource limit 0,
  runtime timeout 0, compflatten build/stat-only 17, build timeout 0,
  fail/error 0/0, candidate/baseline matches 8, mismatches 0, and 7 candidates
  still not verified because MoniTAal baseline timed out.
- Workbook/manual-review artifacts: generated
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_compflatten_stats_fix/paper_review_results.xlsx`
  and
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_compflatten_stats_fix/manual_xml_candidate_review.md`.
  The manual review notes preserve the XML candidate classification from the
  read-only subagent: strong trace-level candidates are `a-b*`, `absentAQ`,
  `absentBR`, and `recurGLB`; approximate/no-input/baseline-timeout candidates
  remain unpromoted.
- QA: `python3 -m py_compile` passed for experiment scripts; latest
  `experiment_summary.json` parsed; `unzip -t` passed for the workbook;
  workbook formula-error scan matched 0 entries; workbook inspect found 10
  sheets and 10 tables; all 10 preview PNGs exist and were visually checked;
  semantic-only regression showed `PASS: 35` and `BUILD_STATS: 17`; no
  semantic FAIL/ERROR/RESOURCE_LIMIT/TIMEOUT/BUILD_TIMEOUT rows remain.
- Remaining limits: flatten monolithic construction can still explode on large
  negative automata; compflatten runtime monitoring is still unsupported in v1;
  compflatten build-only intentionally does not claim SAT; 7 XML candidates are
  still not baseline-verified because MoniTAal timed out; BDD-native runtime is
  still future work.

## 2026-07-05 03:09 CST

- Goal: reduce XML benchmark no-input debt and make the manual-review artifacts
  stricter before paper inspection.
- Work completed: added generated MoniTAal review inputs for
  `c_after_10.xml`, `c_after_20.xml`, and `only_ab_until10.xml` inside the
  experiment harness; each input is recorded in `monitaal_embedded_benchmarks.csv`
  and written under `generated_monitaal_inputs/` in the result directory.
- Correctness result: full experiment rerun to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_generated_inputs_fix`
  produced semantic verified 35, manual oracle debt 0, compflatten build/stat-only
  17, runtime resource limit 0, runtime timeout 0, build timeout 0, fail/error
  0/0, candidate runs 18/18, candidate/baseline matches 11, mismatches 0, and
  7 candidate rows still not verified because MoniTAal baseline timed out.
- Baseline status: MoniTAal baselines now show 11 ran, 8 timed out, and 4
  skipped due no input. The three generated-input promotions matched:
  `c_after_10.xml` POSITIVE/POSITIVE, `c_after_20.xml` POSITIVE/POSITIVE, and
  `only_ab_until10.xml` NEGATIVE/NEGATIVE.
- Manual-review safeguard: updated `manual_xml_candidate_review.md` generation
  so `f(g(notb)_and_g(f(a)).xml` remains explicitly unpromoted because a small
  diagnostic negative probe did not align with the current candidate semantics,
  while a longer baseline probe timed out.
- QA: `python3 -m json.tool` passed for the latest summary; `unzip -t` passed
  for the workbook; workbook formula-error scan matched 0 entries; workbook
  inspect found 10 sheets and 10 tables; all 10 preview PNGs exist and were
  visually checked; `python3 -m py_compile` passed for the experiment scripts;
  `git diff --check` passed.
- Next: define formal promotion criteria for the 11 trace-level XML matches,
  rerun or reduce gear-controller/b_live_a_freq timeout baselines, and revise or
  drop the current `f(g(notb)_and_g(f(a)).xml` MITL candidate.

## 2026-07-05 03:44 CST

- Goal: strengthen XML candidate promotion evidence and fix any semantic
  issue exposed by added reduced traces.
- Real bug found and fixed: XML request/response-style candidates were using
  strict `G`, which in MightyPPL does not include the first observed event.
  A reduced probe such as `G (a -> F [0,30] b)` on `@0 a; @31 b` stayed
  `INCONCLUSIVE`, while MoniTAal XML correctly returned `NEGATIVE`. Candidate
  generation now uses `G*` for event-triggered global patterns so first-event
  triggers are monitored.
- Regression added: semantic case
  `future_globally_star_initial_trigger_violate` verifies
  `G* (a -> F [0,30] b)` returns `NEGATIVE` on `@0 a; @31 b`.
- Harness fix: generated MoniTAal review inputs are now bound to specific
  positive/negative template pairs. This prevents reduced gear-controller
  traces from being run against unrelated templates in the same XML file.
- Experiment expansion: added reduced generated inputs for initial-trigger
  negative cases covering `a-b*`, `absentAQ`, `absentBR`, `recurGLB`, and the
  gear-controller templates `CloseClutch`, `OpenClutch`, `ReqNeu`, `ReqSet`,
  `SpeedSet`, and `test1`; added extra `only_ab_until10` positive/boundary
  variants.
- Verification: targeted XML run produced 25 baseline matches, 0 mismatches,
  7 candidate rows still unverified due MoniTAal baseline timeout, 8 baseline
  timeouts, and 4 skipped no-input rows.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_gstar_promotion_fix`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  compflatten build/stat-only 17, runtime resource limit 0, runtime timeout 0,
  build timeout 0, fail/error 0/0, candidate runs 32/32, candidate/baseline
  matches 25, mismatches 0, baseline not verified due timeout 7, MoniTAal
  baselines 25 ran / 8 timeout / 4 skipped no input, embedded/generated records
  21.
- QA: `python3 -m json.tool` passed for the latest summary; `unzip -t` passed
  for the workbook; workbook formula-error scan matched 0 entries; workbook
  inspect found 10 sheets and 10 tables; all 10 preview PNGs exist and key
  sheets were visually checked; `python3 -m py_compile` passed for experiment
  scripts; `git diff --check` passed.
- Remaining limits: 7 candidate rows still lack original MoniTAal baseline
  verdicts due timeout; original large gear input still times out, though
  reduced negative traces now match; XML-to-MITL candidates remain trace-level
  evidence until formal edge proofs or second independent trace criteria are
  adopted; BDD-native runtime remains future work.

## 2026-07-05 04:06 CST

- Goal: make XML candidate promotion status directly auditable instead of
  requiring manual aggregation from per-input candidate rows.
- Work completed: added `benchmark_manifest.csv` and
  `benchmark_manifest.json`, one row per MoniTAal XML positive/negative pair.
  The manifest aggregates match/mismatch/timeout/no-input counts, separates
  original versus generated input evidence, and assigns explicit
  `promotion_status`, `paper_action`, and `evidence_grade` values.
- Workbook update: added a new `Benchmark Manifest` sheet to
  `paper_review_results.xlsx`; workbook now has 11 sheets and 11 tables.
- Probe verification: a short `--no-workbook` run produced 23 manifest rows,
  with 7 `STRONG_TRACE_LEVEL_CANDIDATE`, 8
  `SINGLE_TRACE_LEVEL_CANDIDATE`, 2 `APPROXIMATE_TRACE_ONLY`, 1
  `APPROXIMATE_UNVERIFIED`, 4 `NOT_CLAIMED`, and 1
  `NO_INPUT_NOT_PROMOTED`; no manifest row had a mismatch.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_manifest_fix`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  compflatten build/stat-only 17, candidate runs 32/32, candidate/baseline
  matches 25, mismatches 0, baseline not verified due timeout 7, MoniTAal
  baselines 25 ran / 8 timeout / 4 skipped no input, embedded/generated records
  21, manifest rows 23.
- QA: `python3 -m json.tool` passed for `experiment_summary.json` and
  `benchmark_manifest.json`; `unzip -t` passed for the workbook; workbook
  formula-error scan matched 0 entries; workbook inspect found 11 sheets and
  11 tables; all 11 preview PNGs exist and key sheets including
  `Benchmark Manifest` were visually checked; Python and bundled Node syntax
  checks passed; `git diff --check` passed.
- Next: add second independent traces or manual edge proofs for the 8
  `SINGLE_TRACE_LEVEL_CANDIDATE` rows if they should be promoted to strong
  trace-level status; rerun original long gear/b_live baselines only if the
  paper requires original-input verdicts.

## 2026-07-05 04:22 CST

- Goal: strengthen the 8 single-trace XML benchmark candidates with independent
  trace-level evidence before the next paper-review workbook.
- Work completed: added second generated review traces in
  `test/TARV/scripts/run_paper_experiments.py` for `c_after_10`,
  `c_after_20`, and the six gear request/response templates. The gear traces
  use one boundary-satisfied request followed by a second late response so that
  MoniTAal reaches a finite negative verdict; pure boundary-positive gear
  prefixes were rejected because MoniTAal did not terminate quickly on them.
- Verification: an ad-hoc `/tmp` probe showed 8/8 new traces match MoniTAal
  XML baseline and TAMonitor candidate verdicts. A formal no-workbook run to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_second_traces_probe`
  produced semantic verified 36, fail/error 0/0, manifest strong trace-level
  15, single trace-level 0, candidate/baseline matches 33, mismatches 0,
  baseline not verified due timeout 7, and embedded/generated records 29.
- Next: run the same experiment with workbook generation, inspect the workbook,
  and then update the handoff files with final artifact paths and QA results.

## 2026-07-05 04:33 CST

- Goal: publish the second-trace benchmark evidence as the current paper-review
  artifact set.
- Work completed: reran the full experiment with workbook generation to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_second_traces_full`.
  Also updated `manual_xml_candidate_review.md` generation so it no longer
  describes the former single-trace state and now records the re-armed gear
  evidence plus the remaining need for formal edge/guard proofs.
- Verification result: semantic cases 53, semantic verified 36, manual oracle
  debt 0, compflatten build/stat-only 17, fail/error 0/0, manifest rows 23,
  strong trace-level candidates 15, single trace-level candidates 0,
  candidate/baseline matches 33, mismatches 0, baseline timeout-not-verified 7,
  MoniTAal baselines 33 ran / 8 timed out / 4 skipped no input, generated
  benchmark records 29, workbook status `ok`.
- QA: `python3 -m json.tool` passed for `experiment_summary.json` and
  `benchmark_manifest.json`; `unzip -t` passed for
  `paper_review_results.xlsx`; workbook formula-error scan matched 0 entries;
  workbook inspect found 11 sheets and 11 tables; key preview PNGs were
  visually checked; Python and bundled Node syntax checks passed;
  `git diff --check` passed.
- Next: add formal XML edge/guard proofs for the 15 strong trace-level
  candidates before claiming full translation equivalence; optionally rerun
  original long gear/b_live baselines with longer timeout if the paper needs
  original-input verdicts.

## 2026-07-05 04:39 CST

- Goal: turn the 15 strong trace-level XML candidates into a more auditable
  edge/guard proof ledger without overclaiming formal equivalence.
- Work completed: added `xml_edge_guard_proofs.csv/json` generation in
  `test/TARV/scripts/run_paper_experiments.py`, with one proof-review row per
  XML pair. The ledger records pattern class, trigger/response/forbidden APs,
  bounds, clock, positive/negative/reset transition evidence, acceptance
  evidence, matched trace evidence, and manual-review notes. Updated workbook
  builder to include an `XML Edge Proofs` sheet and updated manual review notes
  to explain the proof ledger.
- Verification so far: Python syntax check and bundled Node `--check` passed.
  A `--no-run --no-workbook` probe to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_edge_proofs_norun_probe`
  confirmed the new proof CSV/JSON files are generated. Because that probe
  skipped candidate/baseline execution, all proof rows were correctly not-ready.
- External read-only review: subagent recommended 14/15 strong candidates as
  edge/guard proof ready and keeping `recurGLB` as trace-level pending prefix
  semantics. The implementation matches that by marking `recurGLB` as
  `EDGE_GUARD_REVIEW_REQUIRED`.
- Next: run the full experiment with workbook generation, then perform
  JSON/XLSX/workbook-preview/diff QA and update the handoff again.

## 2026-07-05 04:44 CST

- Goal: publish the edge/guard proof ledger as the current paper-review
  artifact set.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_edge_proofs_full`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  compflatten build/stat-only 17, fail/error 0/0, manifest strong trace-level
  15, single trace-level 0, candidate/baseline matches 33, mismatches 0,
  XML edge/guard proof rows 23, proof-ready 14, review-required 1, not-ready 8,
  incomplete 0, workbook status `ok`.
- Proof result: all leadsto, absence, c-after, only-ab-until10, and gear
  request/response strong candidates are marked `EDGE_GUARD_PROOF_READY`.
  `recurGLB_positive_negative` is intentionally
  `EDGE_GUARD_REVIEW_REQUIRED` because the strict lower-bound `(0,10]` and
  initial-prefix semantics need human proof text.
- QA: `python3 -m json.tool` passed for `experiment_summary.json`,
  `benchmark_manifest.json`, and `xml_edge_guard_proofs.json`; `unzip -t`
  passed for `paper_review_results.xlsx`; workbook formula-error scan matched
  0 entries; workbook inspect found 12 sheets and 12 tables; key previews
  including `XML Edge Proofs` were visually checked; Python and bundled Node
  syntax checks passed; `git diff --check` passed.
- Next: manually review and, if acceptable, write paper-facing proof text from
  `xml_edge_guard_proofs.csv`; otherwise keep `recurGLB` trace-level only or
  revise its candidate formula/initial-obligation interpretation.

## 2026-07-05 04:53 CST

- Goal: resolve the remaining `recurGLB` proof-review gap by testing the
  suspected initial-prefix semantics instead of leaving it vague.
- Real issue found and fixed: MoniTAal `recurGLB.xml` rejects `@0; @11 p`
  because the first `p` arrives after the initial closed 10-bound. The previous
  MITL candidate `G* (p -> F (0,10] p)` missed that initial obligation and
  stayed inconclusive on the same trace. The candidate is now
  `(F [0,10] p) && (G* (p -> F (0,10] p))`.
- Experiment expansion: added generated review input
  `recurGLB_first_late_negative` (`@0; @11 p`) to cover the initial-bound
  obligation. Updated the edge-proof text so the same `c <= 10` reset edge
  witnesses both the initial and re-armed recurrence obligations.
- Verification so far: targeted probes show MoniTAal/TAMonitor both
  `NEGATIVE` on first-late, next-late, and normal-then-late recurrence traces.
  A no-workbook full probe to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_recur_fix_probe`
  produced semantic verified 36, fail/error 0/0, proof-ready 15,
  review-required 0, candidate/baseline matches 34, mismatches 0, and generated
  benchmark records 30.
- Next: run the corrected experiment with workbook generation and update the
  handoff to the new final artifact directory after QA.

## 2026-07-05 04:58 CST

- Goal: publish the corrected `recurGLB` candidate and updated proof-ready
  workbook.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_recur_fix_full`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  compflatten build/stat-only 17, fail/error 0/0, manifest strong trace-level
  15, single trace-level 0, candidate/baseline matches 34, mismatches 0,
  XML edge/guard proof rows 23, proof-ready 15, review-required 0, not-ready 8,
  incomplete 0, generated benchmark records 30, workbook status `ok`.
- Proof result: `recurGLB_positive_negative` is now
  `EDGE_GUARD_PROOF_READY` with candidate
  `(F [0,10] p) && (G* (p -> F (0,10] p))` and trace evidence covering the
  original input, initial p followed by late p, and first p arriving after the
  initial closed 10-bound.
- QA: `python3 -m json.tool` passed for `experiment_summary.json`,
  `benchmark_manifest.json`, and `xml_edge_guard_proofs.json`; `unzip -t`
  passed for `paper_review_results.xlsx`; workbook formula-error scan matched
  0 entries; workbook inspect found 12 sheets and 12 tables; key previews were
  visually checked; Python and bundled Node syntax checks passed;
  `git diff --check` passed.
- Next: derive concise paper-facing proof text from
  `xml_edge_guard_proofs.csv`, and keep approximate/unclaimed XML rows out of
  the formal translation claim.

## 2026-07-05 05:05 CST

- Goal: add a paper-facing XML-to-MITL proof appendix artifact derived from the
  conservative `xml_edge_guard_proofs.csv` ledger.
- Work completed: added appendix generation to
  `test/TARV/scripts/run_paper_experiments.py` and added an `XML Proof
  Appendix` sheet to `test/TARV/scripts/build_paper_review_workbook.mjs`.
  The appendix emits `xml_proof_appendix.csv` plus
  `xml_translation_proof_appendix.md`, with proof-ready rows separated from
  approximate/unclaimed/input-debt rows.
- Verification so far: a no-run/no-workbook probe at
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_proof_appendix_norun_probe`
  generated 23 appendix rows and correctly marked 0 rows as
  `PROOF_DRAFT_READY` because candidate/baseline evidence was intentionally
  skipped. Python syntax and bundled Node syntax checks had already passed
  before the probe.
- Next: run the full experiment with workbook generation, then perform
  JSON/XLSX/workbook-preview/diff QA and update this handoff again.

## 2026-07-05 05:12 CST

- Goal: publish the paper-facing proof appendix as a QA-checked review
  artifact without overclaiming approximate XML rows.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_proof_appendix_full`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  compflatten build/stat-only 17, fail/error 0/0, manifest strong trace-level
  15, single trace-level 0, candidate/baseline matches 34, mismatches 0,
  XML edge/guard proof-ready 15, proof appendix rows 23, proof appendix ready
  15, proof appendix excluded 8, generated benchmark records 30, workbook
  status `ok`.
- Appendix result: `xml_proof_appendix.csv` and
  `xml_translation_proof_appendix.md` are generated. The formal proof-ready
  section contains only the 15 `PROOF_DRAFT_READY` rows; 8 approximate,
  no-candidate, or input-debt rows are excluded from formal translation claims.
- QA: `python3 -m json.tool` passed for `experiment_summary.json`,
  `benchmark_manifest.json`, and `xml_edge_guard_proofs.json`; `unzip -t`
  passed for `paper_review_results.xlsx`; workbook formula-error scan matched
  0 entries; workbook inspect found 13 sheets and 13 tables; all 13 preview
  PNGs exist and summary/manifest/proof-appendix previews were visually
  checked; Python and bundled Node syntax checks passed; `git diff --check`
  passed.
- Continuity: archived the previous long project state to
  `.codex/archive/PROJECT_STATE_20260705_pre_proof_appendix_full.md` and
  compacted `.codex/PROJECT_STATE.md` to the active latest-state handoff.
- Next: manually review the 15 proof draft rows for paper wording, optionally
  rerun original baseline timeout rows with longer limits, and keep
  `f(g(notb)_and_g(f(a)).xml` unpromoted until fixed.

## 2026-07-05 05:15 CST

- Goal: make the proof appendix easier to manually审查 for paper writing by
  separating body-summary recommendations from appendix-only/timeout/excluded
  claims.
- Work completed: added `paper_claim_review.csv` and `paper_claim_review.md`
  generation to `test/TARV/scripts/run_paper_experiments.py`, and wired a new
  `Paper Claim Review` sheet into
  `test/TARV/scripts/build_paper_review_workbook.mjs`.
- Verification so far: Python syntax check and bundled Node `--check` passed.
  A no-run/no-workbook probe to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_claim_review_norun_probe`
  generated 23 review rows and conservatively marked 0 body-ready rows, 0
  appendix-timeout-caveat rows, and 23 excluded rows because execution evidence
  was intentionally skipped.
- Next: run the full experiment with workbook generation and QA the expected
  14-sheet workbook.

## 2026-07-05 05:30 CST

- Goal: publish the paper-claim review workbook and add reproducible evidence
  for the remaining original-input baseline timeouts.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_claim_review_full`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  compflatten build/stat-only 17, fail/error 0/0, manifest strong trace-level
  15, candidate/baseline matches 34, mismatches 0, XML proof appendix ready 15,
  paper claim review rows 23, body-pattern rows 9, appendix timeout-caveat rows
  6, excluded rows 8, workbook status `ok`.
- Workbook result: added `Paper Claim Review` as the 14th sheet. It separates
  9 body-pattern candidates after human signoff, 6 gear appendix-ready rows
  with original-input timeout caveats, and 8 excluded rows.
- Supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s`.
  Command selected all 8 MoniTAal baseline timeout rows from the claim-review
  full run and retried each with a 60-second per-row timeout. Result:
  `rerun_ran=0`, `rerun_timeouts=8`, so original-input timeout caveats remain
  justified.
- QA: `python3 -m json.tool` passed for `experiment_summary.json`,
  `benchmark_manifest.json`, `xml_edge_guard_proofs.json`, and
  `baseline_timeout_rerun_summary.json`; `unzip -t` passed for
  `paper_review_results.xlsx`; workbook formula-error scan matched 0 entries;
  workbook inspect found 14 sheets and 14 tables; all 14 preview PNGs exist and
  the Paper Claim Review preview was visually checked; Python and bundled Node
  syntax checks passed; `git diff --check` passed.
- Next: human-review the wording in `paper_claim_review.md` and
  `xml_translation_proof_appendix.md`; keep unpromoted XML rows and original
  timeout rows out of formal equivalence claims.

## 2026-07-05 05:42 CST

- Goal: fix the `f(g(notb)_and_g(f(a)).xml` candidate bug instead of leaving it
  as a vague unpromoted row.
- Real issue found: the old candidate `F (G (!b) && G (F [0,10] a))` was too
  weak. On `@0 a; @11 a`, MoniTAal XML returns `NEGATIVE`, while the old
  TAMonitor candidate stayed `INCONCLUSIVE`. The XML has initial and re-armed
  a-within-10 obligations in addition to the eventual no-b suffix.
- Work completed: changed the harness candidate to
  `(F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b))`, downgraded it to
  `approximate`, and added two reduced negative review inputs:
  `f_g_notb_first_late_negative.input` and
  `f_g_notb_late_a_negative.input`.
- Verification so far: targeted probes show corrected TAMonitor/MoniTAal both
  `NEGATIVE` on first-late and re-armed-late `a` traces. A no-workbook full
  probe to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_f_g_notb_fix_probe`
  produced candidate runs 43, candidate/baseline matches 36, mismatches 0,
  approximate trace-only rows 3, and kept f_g excluded from proof-ready claims.
- Next: run the full workbook experiment and QA the updated artifact set.

## 2026-07-05 05:51 CST

- Goal: publish and QA the full workbook after the `f(g(notb)_and_g(f(a)).xml`
  candidate fix.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_f_g_notb_fix_full`.
  Summary: semantic cases 53, semantic verified 36, manual oracle debt 0,
  fail/error 0/0, XML pairs 23, strong trace-level candidates 15,
  approximate trace-only candidates 3, not-promoted rows 8, candidate runs
  43/43, candidate/baseline matches 36, mismatches 0, baseline runs 36,
  baseline timeouts 8, skipped no-input 3, workbook status `ok`.
- `f_g` result: corrected approximate candidate
  `(F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b))` matches MoniTAal
  XML baseline on two reduced negative traces and remains
  `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE`, not a promoted benchmark claim.
- QA: parsed `experiment_summary.json`, `benchmark_manifest.json`, and
  `xml_edge_guard_proofs.json`; `unzip -t` passed for the workbook; formula
  error scan matched 0 entries; workbook inspect found 14 sheets and 14 tables;
  all 14 preview PNGs exist; Summary and Paper Claim Review previews were
  visually checked; Python and bundled Node syntax checks passed; `git diff
  --check` passed.
- Next: manual paper wording review for `paper_claim_review.md` and
  `xml_translation_proof_appendix.md`; keep approximate and timeout-caveat rows
  out of formal equivalence claims unless stronger proof evidence is added.

## 2026-07-05 06:01 CST

- Goal: align supplementary MoniTAal timeout evidence with the current latest
  full experiment directory after the `f_g` fix.
- Rerun:
  `python3 test/TARV/scripts/rerun_baseline_timeouts.py --source test/TARV/results/paper_experiments_f_g_notb_fix_full --timeout 60 --out test/TARV/results/baseline_timeout_rerun_60s_f_g_fix`.
- Result: selected all 8 timeout rows from the current full run; rerun
  completed 8/8; 0 rows finished with a verdict; 8 rows still timed out.
  Rows were the six `gear-control-properties.xml` original long-input
  templates plus `b_live_a_freq.xml` generated input and
  `gear_controller_test.xml` embedded input.
- QA: `baseline_timeout_rerun_summary.json` parsed with `python3 -m
  json.tool`; `baseline_timeout_rerun.csv` had 8 rows and all statuses were
  `timeout`; `baseline_timeout_rerun.md` was generated with the current source
  directory recorded.
- Next: keep these rows as timeout-caveat evidence unless a justified input
  reduction, algorithmic optimization, or much longer run is explicitly added.

## 2026-07-05 06:23 CST

- Goal: harden paper-facing claim artifacts against overclaiming and fix a
  real manifest/reporting bug found during review.
- Read-only subagent Singer reviewed the previous latest paper artifacts and
  found no strict accidental promotion, but flagged ambiguous gear timeout
  wording and a real inconsistency: `gear_controller_test` had a MoniTAal
  baseline timeout while `benchmark_manifest.csv` reported
  `baseline_timeout_count=0`.
- Work completed: added generated `paper_claim_consistency_audit.csv/md`,
  added a `Claim Audit` workbook sheet, made gear rows appendix-only structural
  candidates with original-input timeout caveats, renamed proof-ready wording
  to structural proof-ready, and fixed benchmark manifest aggregation so
  baseline timeout counts come from `monitaal_baseline_results.csv` even when
  there is no MITL candidate run.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_claim_audit_manifest_fix_full`.
  Summary: semantic cases 53, semantic verified 36, fail/error 0/0,
  candidate/baseline matches 36, mismatches 0, paper claim audit rows 23,
  pass/warn/fail 23/0/0, workbook status `ok`. Workbook now has 15 sheets and
  15 tables.
- Specific bug verification: `gear_controller_test_positive_negative` now has
  `baseline_timeout_count=1` and the timeout input path in
  `benchmark_manifest.csv`; its claim audit row remains `PASS` as
  `EXCLUDED_NO_CANDIDATE`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_claim_audit_manifest_fix`.
  It selected all 8 timeout rows from the current full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: JSON parsing passed for the summary/manifest/proof files and timeout
  rerun summary; `unzip -t` passed for the workbook; formula-error scan matched
  0 entries; workbook inspect found 15 sheets/15 tables; 15 preview PNGs exist
  and the Claim Audit preview was visually checked; Python and bundled Node
  syntax checks passed; `git diff --check` passed.
- Next: human-review the final wording in `paper_claim_review.md`,
  `paper_claim_consistency_audit.md`, and `xml_translation_proof_appendix.md`;
  keep BDD-native runtime as v2 work.

## 2026-07-05 06:41 CST

- Goal: close the finite/infinite-word evidence gap and add a user-requirement
  to evidence traceability artifact for paper review.
- Work completed: added three finite-word hand-oracle semantic regression cases
  (`finite_finally_positive`, `finite_finally_negative`,
  `finite_globally_violate`), added generated
  `requirements_traceability_audit.csv/md`, added a `Requirements Audit`
  workbook sheet, and added requirements-audit summary counters.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_requirements_audit_full`.
  Summary: semantic cases 56, semantic verified 39, semantic fail/error 0/0,
  finite verified 3, candidate/baseline matches 36, mismatches 0, requirements
  audit rows 11 with 8 PASS, 2 PASS_WITH_CAVEAT, 1 V1_DEFERRED, 0 FAIL, and
  workbook status `ok`. Workbook now has 16 sheets and 16 tables.
- Requirements audit result: PASS rows cover TAMonitor target/options, user MITL
  semantic regression, flatten runtime, finite+infinite words, BDD projection,
  XML benchmark review, and output reports. Caveat rows cover compflatten
  runtime boundary and timeout/skipped-input claim caveats. BDD-native runtime
  remains explicitly `V1_DEFERRED`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_requirements_audit`.
  It selected all 8 timeout rows from the current full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: JSON parsing passed for summary/manifest/proof and timeout rerun summary;
  `unzip -t` passed for the workbook; formula-error scan matched 0 entries;
  workbook inspect found 16 sheets/16 tables; 16 preview PNGs exist and the
  Requirements Audit preview was visually checked; Python and bundled Node
  syntax checks passed; `git diff --check` passed.
- Next: human-review `requirements_traceability_audit.md` together with the
  paper claim/proof appendix artifacts; add more finite-word cases only if the
  paper claims broader finite-word semantics than the current smoke-oracle set.

## 2026-07-05 06:58 CST

- Goal: add reproducibility evidence that ties the paper-review results to the
  exact command, dirty workspace state, source files, and result artifacts.
- Work completed: added generated `reproducibility_manifest.json/csv/md`,
  added a `Repro Manifest` workbook sheet, and added summary counters for
  manifest rows, source hashes, result hashes, and git-state rows. Requirements
  Audit now includes `REQ_REPRODUCIBILITY_MANIFEST`.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_repro_manifest_full`.
  Summary: semantic cases 56, semantic verified 39, fail/error 0/0,
  candidate/baseline matches 36, mismatches 0, requirements audit rows 12 with
  9 PASS, 2 PASS_WITH_CAVEAT, 1 V1_DEFERRED, 0 FAIL, reproducibility manifest
  rows 53 with 16 source hashes, 18 result hashes, and 6 git rows, workbook
  status `ok`. Workbook now has 17 sheets and 17 tables.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_repro_manifest`.
  It selected all 8 timeout rows from the current full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: JSON parsing passed for summary/manifest/proof/reproducibility files and
  timeout rerun summary; `unzip -t` passed for the workbook; formula-error scan
  matched 0 entries; workbook inspect found 17 sheets/17 tables; 17 preview
  PNGs exist and the Repro Manifest preview was visually checked; Python and
  bundled Node syntax checks passed; `git diff --check` passed.
- Next: use `reproducibility_manifest.md` together with
  `requirements_traceability_audit.md` as the front-door review index before
  final paper wording.

## 2026-07-05 08:04 CST

- Goal: close the semantic stepwise-verdict review gap and make internal
  Count-form exclusions auditable one row at a time.
- Work completed: fixed TAMonitor reporting so `steps.csv` records every trace
  event. After POSITIVE/NEGATIVE is already decided, later events are reported
  with a stable carry-forward verdict and `monitor_advanced=false`; the core
  MoniTAal monitor is not advanced after a definitive verdict. Added
  `advanced_steps` and `carry_forward_steps` to per-run summaries/metadata.
- Work completed: added hand-written prefix oracle sequences for all 39 runtime
  semantic regression cases, filled missing rationale text, added
  `expected_sat_scope`, added `semantic_prefix_oracle_review.csv/md`, and added
  `semantic_exclusions.csv/json/md` for `CFn/CFn*/COn/COn*/CGn/CGn*/CHn/CHn*`.
  Workbook now includes `Prefix Oracle` and `Semantic Exclusions` sheets.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_stepwise_oracle_full`.
  Summary: semantic cases 56, semantic verified 39, semantic fail/error 0/0,
  prefix-oracle rows/matches/mismatches/missing 98/81/0/0, carry-forward steps
  17, semantic exclusions 8, requirements audit rows 13 with 10 PASS, 2
  PASS_WITH_CAVEAT, 1 V1_DEFERRED, 0 FAIL, reproducibility rows 58 with 16
  source hashes, 23 result hashes, 6 git rows, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_stepwise_oracle`.
  It selected all 8 timeout rows from the current full run; 0 finished with
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt successfully; smoke test for `F [0,1] false` showed
  both trace events in `steps.csv`; JSON parsing passed for summary/manifest/
  proof/reproducibility/exclusion files; `unzip -t` passed for workbook;
  formula-error scan matched 0 entries; workbook inspect reported 19 sheets and
  19 tables; prefix/exclusion preview images were visually checked; all 39
  runtime semantic rows have `processed_steps == trace_events`; all
  `expected_checked` cases have nonempty rationale; Python/Node syntax checks
  and `git diff --check` passed.
- Next: human-review the new `Prefix Oracle` and `Semantic Exclusions` workbook
  sheets together with `paper_claim_review.md`, `requirements_traceability_audit.md`,
  `reproducibility_manifest.md`, and `xml_translation_proof_appendix.md`.

## 2026-07-05 07:44 CST

- Goal: expose per-prefix TAMonitor observations for XML-to-MITL benchmark
  candidate runs without overloading the Excel workbook.
- Work completed: added generated `candidate_prefix_observations.csv` with the
  full raw per-step export for all translation candidate runs, added compact
  `candidate_step_audit.csv/md`, added a `Candidate Step Audit` workbook sheet,
  and added `REQ_BENCHMARK_CANDIDATE_STEP_OUTPUT` to the requirements audit.
  The raw per-step CSV is kept outside the workbook; the workbook carries a
  43-row index with links to per-run `steps.csv` files.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_candidate_step_audit_full`.
  Summary: semantic cases 56, semantic verified 39, fail/error 0/0,
  prefix-oracle rows/matches/mismatches/missing 98/81/0/0, candidate prefix
  observation rows 122975, candidate step audit rows 43 with 43 complete and 0
  missing/incomplete, candidate carry-forward rows 29988, requirements audit
  rows 14 with 11 PASS, 2 PASS_WITH_CAVEAT, 1 V1_DEFERRED, 0 FAIL,
  reproducibility rows 61 with 16 source hashes, 26 result hashes, 6 git rows,
  workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_candidate_step_audit`.
  It selected all 8 timeout rows from the current full run; 0 finished with
  verdict and 8 still timed out at 60 seconds.
- QA: JSON parsing passed for summary/manifest/proof/reproducibility/exclusion
  files; `unzip -t` passed for workbook; formula-error scan matched 0 entries;
  workbook inspect reported 20 sheets and 20 tables; `candidate_step_audit.csv`
  has 43 rows and `candidate_prefix_observations.csv` has 122975 rows; all 43
  candidate rows have `observed_steps == mapped_events == processed_steps`;
  `candidate_step_audit_preview.png` was visually checked; Python/Node syntax
  checks and `git diff --check` passed.
- Next: use `Candidate Step Audit` plus raw `candidate_prefix_observations.csv`
  when manually reviewing benchmark trace behavior; timeout rows remain caveats.

## 2026-07-05 08:03 CST

- Goal: strengthen finite-word evidence beyond the earlier 3-case smoke set
  and fix any finite-mode bug exposed by broader probes.
- Bug fixed: finite-word `MonitorRunner` could emit definitive per-step
  `NEGATIVE/POSITIVE` verdicts for past formulas while recomputing
  `final_verdict=INCONCLUSIVE` from accepting states at end-of-word. The runner
  now preserves a definitive finite verdict once reached.
- Work completed: added 14 finite-word hand-oracle semantic regression cases,
  covering Boolean conjunction, open intervals, U/U*, R/R*, past O/H/S/T, and
  Pnueli Fn/Gn/Hn. Requirements audit now requires at least 17 finite verified
  cases rather than the earlier 3-case smoke threshold.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_finite_extended_full`.
  Summary: semantic cases 70, semantic verified 53, finite verified 17,
  infinite verified 36, fail/error 0/0, prefix-oracle rows/matches/mismatches/
  missing 132/115/0/0, requirements audit rows 14 with 11 PASS, 2
  PASS_WITH_CAVEAT, 1 V1_DEFERRED, 0 FAIL, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_finite_extended`.
  It selected all 8 timeout rows from the current full run; 0 finished with
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt successfully; JSON parsing passed for summary/manifest/
  proof/reproducibility/exclusion files; `unzip -t` passed for workbook;
  formula-error scan matched 0 entries; workbook inspect reported 20 sheets and
  20 tables; semantic results preview was visually checked; finite verified
  IDs matched the 17 expected cases; Python/Node syntax checks and
  `git diff --check` passed.
- Next: keep finite-word claims to operator-level hand-oracle regression unless
  additional paper-specific theorem cases are added.

## 2026-07-05 08:36 CST

- Goal: make the "all MightyPPL user-level syntax/semantics regression" claim
  auditable instead of relying on prose.
- Work completed: added `mightyppl_syntax_coverage_audit.csv/json/md` and a
  workbook `Syntax Coverage` sheet. The ledger maps `Mitl.g4` user-level atoms,
  Boolean connectives, interval forms, future/past/starred operators, Pnueli
  `Fn/On/Gn/Hn`, finite/infinite word coverage, existing MightyPPL testcase
  build/stat rows, and the 8 internal Count-form exclusions. `CFn/COn/CGn/CHn`
  and starred variants are recorded as parser-visible but internal NNF/compiler
  forms, not ordinary user MITL formulas.
- Read-only subagent Boole confirmed the grammar/visitor basis: README exposes
  MITL/Pnueli syntax, `Mitl.g4` contains Count alternatives/tokens, and
  `MitlToNNFVisitor.cpp` asserts original formulas should contain no
  `CFn/COn/CGn/CHn` while rewriting some non-unilateral/general cases into
  Count forms internally.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_syntax_coverage_polished_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, syntax coverage rows 45 with verified-runtime/build-only/
  internal-excluded/missing 36/1/8/0, requirements rows pass/caveat/deferred/fail
  15/12/2/1/0, candidate baseline matches/mismatches/not-verified 36/0/7,
  workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_syntax_coverage_polished`.
  It selected all 8 timeout rows from the polished full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python/Node syntax checks passed; JSON parsing passed
  for summary/manifest/proof/reproducibility/exclusion/syntax files;
  `unzip -t` passed for `paper_review_results.xlsx`; formula-error scan matched
  0 entries; workbook XML has 21 sheets/21 tables including `Syntax Coverage`;
  CSV checks passed for syntax coverage, prefix oracle, exclusions, candidate
  step audit, raw candidate observations, requirements, and reproducibility
  manifests; `syntax_coverage_preview.png` was visually checked after widening
  `expected_policy`; `git diff --check` passed.
- Next: human-review the new `Syntax Coverage` sheet together with `Prefix
  Oracle`, `Semantic Exclusions`, `Requirements Audit`, `Paper Claim Review`,
  `Claim Audit`, `Repro Manifest`, and `XML Proof Appendix`.

## 2026-07-05 09:01 CST

- Goal: harden and document the parser-visible/internal Count-form input
  boundary so TAMonitor behaves like an industrial tool instead of relying on
  downstream MightyPPL asserts.
- Finding: `src/TAMonitor/TAMonitorMightyAdapter.cpp` already has
  `reject_unsupported_internal_syntax()` and rejects `CFn/COn/CGn/CHn` tokens
  with `unsupported_user_formula`. A direct probe of `CFn[0,1](p1,p2)` returned
  exit code 1 with the controlled diagnostic, not an abort.
- Work completed: added `formula_input_policy_audit.csv/json/md`, workbook
  `Input Policy` sheet, summary counters, reproducibility hashes, and
  `REQ_INTERNAL_FORM_INPUT_POLICY`. The audit runs 8 redacted minimal probes
  for `CFn/CFn*/COn/COn*/CGn/CGn*/CHn/CHn*`; it does not add them as semantic
  MITL regression formulas or correctness oracles.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_input_policy_polished_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, syntax coverage rows 45 with 0 missing,
  input-policy rows/pass/fail/assert-like 8/8/0/0, requirements rows
  pass/caveat/deferred/fail 16/13/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_input_policy_polished`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python/Node syntax checks passed; JSON parsing passed
  for summary/manifest/proof/reproducibility/exclusion/syntax/input-policy
  files; `unzip -t` passed for `paper_review_results.xlsx`; formula-error scan
  matched 0 entries; workbook XML has 22 sheets/22 tables including
  `Input Policy`; CSV checks passed for input policy, syntax coverage, prefix
  oracle, candidate step audit, raw candidate observations, requirements, and
  reproducibility manifests; `input_policy_preview.png` was visually checked
  after widening `probe_policy`; `git diff --check` passed.
- Next: human-review `Input Policy` together with `Syntax Coverage`, `Prefix
  Oracle`, `Semantic Exclusions`, `Requirements Audit`, `Paper Claim Review`,
  `Claim Audit`, `Repro Manifest`, and `XML Proof Appendix`.

## 2026-07-05 09:33 CST

- Goal: add a single human-review entry point so the user can manually inspect
  paper-facing TAMonitor evidence without hunting across many sheets.
- Work completed: added `manual_review_checklist.csv/json/md`, workbook
  `Manual Review` sheet, summary counters, result hashes, and
  `REQ_MANUAL_REVIEW_PACKET`. The checklist has 15 rows covering semantic
  final oracles, prefix oracles, finite/infinite scope, syntax coverage,
  internal Count-form input policy, BDD projection/native boundary,
  compflatten boundary, XML translation tiers, XML edge proofs, paper claim
  boundaries, baseline/gear timeout caveats, candidate step output, and
  reproducibility.
- Read-only subagent Wegener confirmed the needed manual-review gates and
  warned against overclaiming full XML-to-MITL equivalence, compflatten runtime
  verification, BDD-native runtime, gear original-input baseline agreement, or
  Count forms as user-level MITL.
- Bug fixed during experiment review: the new workbook status columns were too
  narrow and clipped `PASS_WITH_CAVEAT`/`human_decision_required` values in the
  rendered `Manual Review` sheet. `build_paper_review_workbook.mjs` now has a
  medium-width column class for review IDs/status fields; the preview was
  rechecked visually.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_manual_review_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, syntax coverage rows 45 with 0 missing, input-policy rows/pass/
  fail/assert-like 8/8/0/0, manual review rows pass/caveat/review/deferred/fail
  15/7/4/3/1/0, requirements rows pass/caveat/deferred/fail 17/14/2/1/0,
  candidate baseline matches/mismatches/not-verified 36/0/7, workbook status
  `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_manual_review`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python/Node syntax checks passed; JSON parsing passed
  for summary/manual-review/manifest/proof/reproducibility/exclusion/syntax/
  input-policy files; `unzip -t` passed; formula-error scan matched 0 entries;
  workbook XML has 23 sheets/23 tables including `Manual Review`; CSV checks
  passed for manual review, requirements, syntax coverage, input policy, prefix
  oracle, candidate step audit, and timeout rerun; `manual_review_preview.png`
  was visually checked; `git diff --check` passed.
- Next: start manual paper review from the workbook `Manual Review` sheet, then
  follow each row to the referenced evidence sheets before drafting claims.

## 2026-07-05 09:52 CST

- Goal: strengthen the answer to "how do we know each MITL runtime verdict is
  correct?" by adding a human-readable oracle derivation ledger rather than only
  final verdict/pass counters.
- Work completed: added `semantic_oracle_derivations.csv/json/md`, workbook
  `Oracle Derivations` sheet, summary counters, result hashes, and
  `REQ_SEMANTIC_ORACLE_DERIVATIONS`. The ledger maps each semantic case to its
  formula, trace, word mode, expected/actual final verdict, optional prefix
  oracle checks, SAT expectation, semantic rule family, hand rationale, and
  review action. The 17 MightyPPL existing corpus rows are explicitly marked
  `CONSTRUCTION_STATS_ONLY`, not runtime correctness oracles.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_oracle_derivations_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, oracle derivations rows/verified/build-only/review-required/
  prefix-mismatch 70/53/17/0/0, syntax coverage rows 45 with 0 missing,
  input-policy rows/pass/fail/assert-like 8/8/0/0, manual review rows
  pass/caveat/review/deferred/fail 15/7/4/3/1/0, requirements rows
  pass/caveat/deferred/fail 18/15/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_oracle_derivations`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python/Node syntax checks passed; JSON parsing passed
  for summary/oracle-derivations/manual-review/manifest/proof/reproducibility/
  exclusion/syntax/input-policy files; `unzip -t` passed; formula-error scan
  matched 0 entries; workbook XML has 24 sheets/24 tables including
  `Oracle Derivations`; CSV checks passed for oracle derivations, manual review,
  requirements, syntax coverage, input policy, prefix oracle, candidate step
  audit, and timeout rerun; `oracle_derivations_preview.png` was visually
  checked; `git diff --check` passed.
- Handoff: `.codex/PROJECT_STATE.md` was compacted from the previous 240-line
  active state into a fresher active handoff focused on the latest result paths,
  metrics, verification, risks, and recovery prompt.
- Next: use the workbook `Manual Review` and `Oracle Derivations` sheets as the
  first two manual-review entry points before drafting paper claims.

## 2026-07-05 10:15 CST

- Goal: turn the TAMonitor command-line surface itself into audited evidence
  instead of relying only on source-option inspection and indirect semantic
  runs.
- Work completed: added `cli_contract_audit.csv/json/md`, workbook
  `CLI Contract` sheet, summary counters, result hashes, `MR_CLI_CONTRACT`, and
  `REQ_CLI_CONTRACT_AUDIT`. The audit directly probes formula-file input,
  inline formula input, trace-file formats (`time,props`, `bits:...`,
  `@time label`), stdin trace entry, finite/infinite word modes,
  symbolic/concrete state modes, BDD interface metadata, compflatten build-only
  mode, compflatten runtime rejection, mutually exclusive formula inputs,
  unknown trace propositions, missing formula files, and invalid valuation caps.
- Harness fix: `run_command` now accepts optional stdin text so the no-`--trace`
  interactive trace path can be tested without hanging. Existing calls keep the
  previous behavior.
- Fast no-workbook probe:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_cli_contract_probe`.
  It confirmed CLI contract rows/pass/fail/controlled-error 10/10/0/5 before
  running the full workbook experiment.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_cli_contract_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, oracle derivations 70/53/17/0/0, syntax coverage rows 45 with
  0 missing, input-policy rows/pass/fail/assert-like 8/8/0/0, CLI contract
  rows/pass/fail/controlled-error 10/10/0/5, manual review rows
  pass/caveat/review/deferred/fail 16/8/4/3/1/0, requirements rows
  pass/caveat/deferred/fail 19/16/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_cli_contract`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python/Node syntax checks passed; JSON parsing passed
  for summary/CLI-contract/oracle-derivations/manual-review/manifest/proof/
  reproducibility/exclusion/syntax/input-policy files; `unzip -t` passed;
  formula-error scan matched 0 entries; workbook XML has 25 sheets/25 tables
  including `CLI Contract`; CSV checks passed for CLI contract, oracle
  derivations, manual review, requirements, syntax coverage, input policy,
  prefix oracle, candidate step audit, and timeout rerun; `cli_contract_preview.png`
  was visually checked; `git diff --check` passed.
- Next: use the workbook `Manual Review`, `Oracle Derivations`, and
  `CLI Contract` sheets as the first manual-review entry points before drafting
  paper claims or scripting demos.

## 2026-07-05 10:54 CST

- Goal: add a top-level completion audit so the original TAMonitor objective can
  be reviewed requirement-by-requirement instead of inferred from separate
  ledgers.
- Work completed: added `goal_completion_audit.csv/json/md`, workbook
  `Goal Audit` sheet, summary counters, result hashes, and
  `REQ_GOAL_COMPLETION_AUDIT`. The audit maps 17 original goal items to
  evidence, caveats, deferrals, review gates, forbidden paper claims, and next
  actions.
- Independent review: read-only subagent Harvey flagged the missing total goal
  audit and a stale latest-result path in `.codex/PROJECT_STATE.md`; the stale
  path is now replaced by the Goal Audit full-run path.
- Harness bug fixed while wiring the audit: an accidental function-signature
  mismatch caused the first no-workbook probe to fail with a missing argument.
  The signatures were corrected and the probe then passed with
  goal-completion rows/pass/caveat/review/deferred/fail 17/12/2/2/1/0.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_goal_audit_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, oracle derivations 70/53/17/0/0, syntax coverage rows 45 with
  0 missing, input-policy rows/pass/fail/assert-like 8/8/0/0, CLI contract
  rows/pass/fail/controlled-error 10/10/0/5, goal completion rows
  pass/caveat/review/deferred/fail 17/12/2/2/1/0, manual review rows
  pass/caveat/review/deferred/fail 16/8/4/3/1/0, requirements rows
  pass/caveat/deferred/fail 20/17/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_goal_audit`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python syntax checks passed; JSON parsing passed for
  summary, goal completion, and timeout rerun files; `unzip -t` passed for the
  workbook; formula-error scan reported 0 matched cells; workbook XML has
  26 sheets/26 tables including `Goal Audit`; CSV checks passed for goal
  completion, manual review, requirements, CLI contract, oracle derivations, and
  timeout rerun; preview PNG dimensions were checked; `git diff --check` passed.
- Next: start human inspection from workbook `Goal Audit`, then `Manual Review`
  and `Oracle Derivations`; keep the 8 timeout rows as caveats unless a stronger
  baseline campaign is explicitly required.

## 2026-07-05 11:17 CST

- Goal: make the remaining human-review work easier to inspect by aggregating
  review-required, caveated, deferred, XML-proof, paper-claim, and benchmark
  boundary rows into a single prioritized queue.
- Work completed: added `human_review_queue.csv/json/md`, workbook
  `Review Queue` sheet, summary counters, result hashes, and
  `REQ_HUMAN_REVIEW_QUEUE`. The queue does not promote any row to a stronger
  claim; it only points reviewers to the correct evidence sheet and must-not-
  claim boundary.
- Probe rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_review_queue_probe`.
  It confirmed queue rows/human-required/P0/P1/P2/P3/fail
  70/47/29/23/2/16/0 before generating the full workbook.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_review_queue_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, oracle derivations 70/53/17/0/0, syntax coverage rows 45 with
  0 missing, input-policy rows/pass/fail/assert-like 8/8/0/0, CLI contract
  rows/pass/fail/controlled-error 10/10/0/5, goal completion rows
  pass/caveat/review/deferred/fail 17/12/2/2/1/0, human review queue
  rows/human-required/P0/P1/P2/P3/fail 70/47/29/23/2/16/0, manual review rows
  pass/caveat/review/deferred/fail 16/8/4/3/1/0, requirements rows
  pass/caveat/deferred/fail 21/18/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_review_queue`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python and bundled-Node syntax checks passed; JSON
  parsing passed for summary, human review queue, goal completion, CLI contract,
  oracle derivations, manual review, benchmark manifest, XML proof, reproducibility,
  semantic exclusions, syntax coverage, input policy, and timeout rerun files;
  `unzip -t` passed for the workbook; formula-error scan reported 0 matched
  cells; workbook XML has 27 sheets/27 tables including `Review Queue`; CSV
  checks passed for human review queue, goal completion, manual review,
  requirements, CLI contract, oracle derivations, and timeout rerun; preview PNG
  dimensions were checked; `git diff --check` passed.
- Next: start human inspection from workbook `Review Queue`; treat its P0 rows
  as the first signoff queue before drilling into `Goal Audit`, `Manual Review`,
  `XML Proof Appendix`, and `Paper Claim Review`.

## 2026-07-05 11:39 CST

- Goal: convert the centralized review queue into an auditable human signoff
  entry point without auto-filling any reviewer decisions.
- Work completed: added `review_signoff_template.csv/json/md`, workbook
  `Review Signoff` sheet, summary counters, result hashes, and
  `REQ_REVIEW_SIGNOFF_TEMPLATE`. The template includes P0/P1/P2 paper-facing
  review items and leaves `reviewer_decision`, `reviewer`, `review_date`, and
  `reviewer_notes` blank by design.
- Probe rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_signoff_probe`.
  It confirmed signoff rows/blank-decisions/P0/P1/P2 54/54/29/23/2 and
  requirements rows/pass/caveat/deferred/fail 22/19/2/1/0 before the full
  workbook run.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_signoff_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, oracle derivations 70/53/17/0/0, syntax coverage rows 45 with
  0 missing, input-policy rows/pass/fail/assert-like 8/8/0/0, CLI contract
  rows/pass/fail/controlled-error 10/10/0/5, goal completion rows
  pass/caveat/review/deferred/fail 17/12/2/2/1/0, human review queue
  rows/human-required/P0/P1/P2/P3/fail 70/47/29/23/2/16/0, review signoff
  rows/blank-decisions/P0/P1/P2 54/54/29/23/2, manual review rows
  pass/caveat/review/deferred/fail 16/8/4/3/1/0, requirements rows
  pass/caveat/deferred/fail 22/19/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python and bundled-Node syntax checks passed; JSON
  parsing passed for summary, human review queue, review signoff, goal
  completion, CLI contract, oracle derivations, manual review, benchmark
  manifest, XML proof, reproducibility, semantic exclusions, syntax coverage,
  input policy, and timeout rerun files; `unzip -t` passed for the workbook;
  formula-error scan reported 0 matched cells; workbook XML has 28 sheets/28
  tables including `Review Signoff`; CSV checks passed for review signoff,
  human review queue, requirements, goal completion, manual review, CLI
  contract, oracle derivations, and timeout rerun; preview PNG dimensions were
  checked; `git diff --check` passed.
- Next: use `Review Queue` to decide review order, then fill `Review Signoff`
  only after inspecting linked evidence sheets. Blank reviewer decisions are
  expected until a human reviewer signs off.

## 2026-07-05 12:00 CST

- Goal: add a conservative reviewer guide so the workbook explains review order,
  allowed signoff decisions, evidence boundaries, timeout policy, and paper claim
  limits instead of relying only on queue rows.
- Work completed: added `review_guide.csv/json/md`, workbook `Review Guide`
  sheet, summary counters, result hashes, and `REQ_REVIEW_GUIDE`. The guide
  includes 13 rows covering entrypoint, five signoff decisions, MITL oracle
  boundaries, XML proof boundaries, paper claim audit scope, timeout policy,
  reproducibility, bug-fix loop, and current blank-signoff status.
- Probe rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_review_guide_probe`.
  It confirmed review guide rows/P0/P1 13/7/6 and requirements
  rows/pass/caveat/deferred/fail 23/20/2/1/0 before the full workbook run.
- Full rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_review_guide_full`.
  Summary: semantic cases 70, semantic verified 53, finite/infinite verified
  17/36, semantic fail/error 0/0, prefix oracle rows/matches/mismatches/missing
  132/115/0/0, oracle derivations 70/53/17/0/0, syntax coverage rows 45 with
  0 missing, input-policy rows/pass/fail/assert-like 8/8/0/0, CLI contract
  rows/pass/fail/controlled-error 10/10/0/5, review guide rows/P0/P1 13/7/6,
  human review queue rows/human-required/P0/P1/P2/P3/fail 70/47/29/23/2/16/0,
  review signoff rows/blank-decisions/P0/P1/P2 54/54/29/23/2, goal completion
  rows pass/caveat/review/deferred/fail 17/12/2/2/1/0, requirements rows
  pass/caveat/deferred/fail 23/20/2/1/0, candidate baseline
  matches/mismatches/not-verified 36/0/7, workbook status `ok`.
- Latest supplementary timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_review_guide`.
  It selected all 8 timeout rows from the latest full run; 0 finished with a
  verdict and 8 still timed out at 60 seconds.
- QA: TAMonitor rebuilt; Python and bundled-Node syntax checks passed; JSON
  parsing passed for summary, review guide, review queue, review signoff, goal
  completion, CLI contract, oracle derivations, manual review, benchmark
  manifest, XML proof, reproducibility, semantic exclusions, syntax coverage,
  input policy, and timeout rerun files; `unzip -t` passed for the workbook;
  formula-error scan reported 0 matched cells; workbook XML has 29 sheets/29
  tables including `Review Guide`; CSV checks passed for review guide, review
  signoff, human review queue, requirements, goal completion, manual review,
  CLI contract, oracle derivations, and timeout rerun; preview PNG dimensions
  were checked; `git diff --check` passed.
- Handoff maintenance: archived the previous 242-line PROJECT_STATE to
  `.codex/archive/PROJECT_STATE_20260705_pre_review_guide_full.md` and compacted
  active `.codex/PROJECT_STATE.md` so future work starts from latest evidence
  without stale path drift.
- Next: start human review from workbook `Review Guide`, then `Review Queue`,
  then fill `Review Signoff` only after checking linked sheets. Blank signoff
  decisions remain expected before human review.

## 2026-07-05 12:06 CST

- Goal: add an independent consistency verifier for the generated TAMonitor
  paper-review result packet, so the latest directory is checked after generation
  rather than trusted only because the generator reported success.
- Work completed: added `test/TARV/scripts/verify_review_packet.py`. It checks
  required artifact presence, workbook zip structure and review-critical sheets,
  formula-error scan output, summary-vs-CSV row counts, review guide/queue/
  signoff invariants, oracle and prefix-oracle boundaries, CLI contract, paper
  claim audit, timeout caveat policy, and reproducibility hash coverage.
- Bug fixed while testing the verifier: the first verifier run failed
  `WORKBOOK_REVIEW_SHEETS` because the verifier used brittle string parsing for
  `xl/workbook.xml` and missed namespaced `<x:sheet>` elements. The workbook
  was valid; `verify_review_packet.py` now parses workbook XML with
  `xml.etree.ElementTree`.
- Verification command:
  `python3 test/TARV/scripts/verify_review_packet.py --output-dir
  test/TARV/results/paper_experiments_review_guide_full --timeout-rerun
  test/TARV/results/baseline_timeout_rerun_60s_review_guide`.
  Final result: 53 checks, 53 PASS, 0 WARN, 0 FAIL. Outputs were written to
  `review_packet_verification.csv/json/md` in the latest full result directory.
- QA: Python compilation passed for the verifier and existing experiment scripts;
  `review_packet_verification.json` parses; category counts are artifact
  presence 24, workbook 4, csv-summary consistency 11, review packet 3,
  benchmark caveats 4, correctness 2, claim safety 2, plus summary/runtime/
  reproducibility checks; `git diff --check` passed.
- Next: use `review_packet_verification.*` as the first automated sanity check
  after each future full experiment rerun, before opening `Review Guide` and
  filling `Review Signoff`.

## 2026-07-05 12:29 CST

- Goal: turn the TAMonitor paper-review experiment from a sequence of manual
  commands into a single reproducible, auditable pipeline entry point.
- Work completed: added
  `test/TARV/scripts/run_full_review_pipeline.py`. The pipeline runs Python
  syntax preflight, builds TAMonitor, executes the full paper experiment, reruns
  MoniTAal baseline timeout rows with a 60-second timeout, runs the independent
  review-packet verifier, and writes `pipeline_summary.csv/json/md`.
- Real risk fixed during implementation: the first smoke run reported
  `PASS` even when `--no-run`, `--no-workbook`, timeout rerun, and verifier were
  skipped. The script now reports `PARTIAL` for reduced modes and only reports
  full `PASS` when no reduction flags are used and all safety gates pass.
- Additional safety gates added after read-only subagent review: nonzero
  semantic fail/error/timeout, prefix mismatch/missing, syntax missing, CLI
  fail, requirements fail, paper-claim fail, candidate baseline mismatch,
  candidate-step incompleteness, missing TAMonitor binary, workbook failure,
  timeout-rerun inconsistency, or verifier failure all make the pipeline fail.
- Full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_pipeline --timeout 30
  --timeout-rerun-seconds 60`.
  Result: `pipeline_status=PASS`, `pipeline_mode=full`, elapsed 766255 ms,
  failed steps 0.
- Latest review packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_full`; workbook
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_full/paper_review_results.xlsx`.
  Verifier result: 53 PASS, 0 WARN, 0 FAIL.
- Latest timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_pipeline`;
  selected/completed 8 rows, 0 finished with verdict, 8 still timed out,
  skipped-no-binary 0.
- QA: JSON parsing passed for pipeline summary, experiment summary, verifier
  JSON, and timeout-rerun summary; `unzip -t` passed for the workbook; direct
  pipeline summary assertions passed; `git diff --check` passed for the touched
  source/result/handoff paths.
- Next: use `pipeline_summary.md` as the first entry point, then open workbook
  `Review Guide`, `Review Queue`, and `Review Signoff` for human paper review.

## 2026-07-05 12:52 CST

- Goal: make the hand-oracle correctness review path explicit and auditable,
  following the user's question about what a manual oracle is.
- Work completed: added `manual_oracle_guide.csv/json/md` generation to
  `test/TARV/scripts/run_paper_experiments.py`, added a `Manual Oracle Guide`
  workbook sheet in `build_paper_review_workbook.mjs`, exposed the artifact in
  `run_full_review_pipeline.py`, and updated `verify_review_packet.py` to
  require the files, workbook sheet, row count consistency, and protocol rows.
- The new guide defines the manual oracle as an independent MITL-semantics
  expectation, separates prefix and final three-valued verdict checks, keeps
  SAT separate from runtime satisfaction, blocks build/stat-only rows from being
  counted as RV correctness, and records a fix policy for mismatches.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_manual_oracle_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_manual_oracle --timeout 30
  --timeout-rerun-seconds 60`.
  Result: `pipeline_status=PASS`, `pipeline_mode=full`, elapsed 760825 ms,
  failed steps 0.
- Latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_manual_oracle_full`;
  workbook has 30 sheets/30 tables including `Manual Oracle Guide`.
  Manual-oracle guide rows/P0/P1: 8/5/3. Verifier result: 58 PASS, 0 WARN,
  0 FAIL.
- Timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_manual_oracle`;
  selected/completed 8 rows, 0 finished with verdict, 8 still timed out,
  skipped-no-binary 0.
- QA: Python and bundled-Node syntax checks passed; JSON parsing passed for
  pipeline summary, experiment summary, verifier JSON, manual-oracle guide JSON,
  and timeout-rerun summary; `unzip -t` passed for the workbook; direct packet
  assertions confirmed `Manual Oracle Guide` sheet and required guide IDs;
  `git diff --check` passed.
- Handoff maintenance: archived the previous active 12:29 state summary in
  `.codex/archive/PROJECT_STATE_20260705_pre_manual_oracle_guide.md` and
  compacted `.codex/PROJECT_STATE.md` to keep the active handoff under the
  roughly-250-line threshold.
- Next: begin human review from `pipeline_summary.md`, then workbook
  `Review Guide`, `Manual Oracle Guide`, `Review Queue`, and `Review Signoff`.

## 2026-07-05 12:58 CST

- Goal: prove that adding the `Manual Oracle Guide` review layer did not change
  TAMonitor semantic/runtime/benchmark results.
- Work completed: added `test/TARV/scripts/compare_pipeline_results.py`, a
  packet-to-packet stability audit. It compares two full pipeline result
  directories, requires stable semantic, prefix-oracle, syntax, CLI, XML,
  candidate, baseline, and claim-safety metrics, and permits only expected
  review-packet growth such as the new manual-oracle guide rows, workbook sheet,
  reproducibility hashes, and verifier checks.
- Comparison run:
  `python3 test/TARV/scripts/compare_pipeline_results.py --baseline
  test/TARV/results/paper_pipeline_full --candidate
  test/TARV/results/paper_pipeline_manual_oracle_full`.
  Result: 148 PASS, 0 WARN, 0 FAIL. Outputs:
  `result_stability_audit.csv/json/md` in
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_manual_oracle_full`.
- Follow-up integration: added the comparison script to the pipeline syntax
  preflight list and added `result_stability_audit.md` to future pipeline
  artifact indexes.
- QA: Python compilation passed for pipeline, experiment, verifier, timeout
  rerun, compare, and TAMonitor xlsx helper scripts; `result_stability_audit`
  JSON parses; direct assertions confirmed 148 PASS and no non-PASS rows;
  `git diff --check` passed.
- Next: use `result_stability_audit.md` when explaining that the manual-oracle
  review layer is instrumentation only and did not alter runtime verdicts.

## 2026-07-05 13:02 CST

- Goal: prevent the blank `Review Signoff` template from being mistaken for
  completed human review and provide a future strict validator for filled
  reviewer decisions.
- Work completed: added `test/TARV/scripts/validate_review_signoff.py`. In
  default `pre-review` mode it checks required columns, queue/signoff coverage,
  P0/P1/P2 scope, queue-field synchronization, allowed decision set, evidence
  fields, and intentionally blank reviewer-owned fields. It also supports
  `complete` mode for future human-filled signoff validation.
- Current packet validation:
  `python3 test/TARV/scripts/validate_review_signoff.py --output-dir
  test/TARV/results/paper_pipeline_manual_oracle_full --mode pre-review`.
  Result: 8 PASS, 0 FAIL; 54 signoff rows; 54 blank decisions; completion
  state `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`. Outputs were written to
  `review_signoff_validation.csv/json/md`.
- Pipeline integration: added the validator to the pipeline Python preflight,
  artifact index, command flow, summary CSV/Markdown/JSON, and failure gates.
  A smoke run with `--no-build --no-run --no-workbook --skip-timeout-rerun
  --skip-verify` returned `PARTIAL` and showed signoff validation 8 PASS,
  0 FAIL.
- QA: Python compilation passed for `validate_review_signoff.py` and the updated
  pipeline script; latest signoff validation JSON parses; direct assertions
  confirmed mode `pre-review`, 8 PASS, 0 FAIL, 54 blank decisions; `git
  diff --check` passed.
- Next: after a human fills `Review Signoff`, rerun the validator in
  `--mode complete` to prove decisions, reviewer/date fields, and caveat notes
  are complete before marking human review done.

## 2026-07-05 13:20 CST

- Goal: regenerate the latest full packet with native `Review Signoff`
  validation in `pipeline_summary.json`, and strengthen stability evidence so
  later packets are compared by content rather than row counts alone.
- Work completed: updated `test/TARV/scripts/compare_pipeline_results.py` with
  `--profile manual-oracle-added|stable`. The historical profile keeps the old
  expected Manual Oracle Guide growth behavior; `stable` requires unchanged
  manual-oracle metrics, zero reproducibility/verifier deltas, unchanged
  workbook sheet set, passing signoff validation in both packets, and normalized
  stable CSV content equality while ignoring only volatile `elapsed_ms`.
- Real bug fixed during QA: the first signoff-validation read tried to open
  `review_signoff_validation.json` even for the old `manual-oracle-added`
  baseline packet that predates that file. The script now reads missing signoff
  JSON as `{}` and only enforces signoff-validation equality in `stable` mode.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_signoff_validation_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_signoff_validation --timeout 30
  --timeout-rerun-seconds 60`.
  Result: `pipeline_status=PASS`, `pipeline_mode=full`, elapsed 771442 ms,
  failed steps 0. The pipeline summary now includes
  `review_signoff_validation`: 8 PASS, 0 FAIL, 54 blank decisions,
  completion state `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`.
- Stable comparison:
  `python3 test/TARV/scripts/compare_pipeline_results.py --profile stable
  --baseline test/TARV/results/paper_pipeline_manual_oracle_full --candidate
  test/TARV/results/paper_pipeline_signoff_validation_full`.
  Result: 172 PASS, 0 WARN, 0 FAIL. Outputs were written to
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_validation_full/result_stability_audit.csv/json/md`.
- QA: `python3 -m py_compile` passed for all pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`; JSON parsing passed for the new
  pipeline summary, signoff validation, result stability audit, and timeout
  rerun summary; `unzip -t` passed for the new workbook; direct packet
  assertions confirmed full PASS, stable profile 172 PASS, signoff validation
  8/0, 30 workbook sheets including `Manual Oracle Guide`, semantic fail 0,
  prefix mismatch 0, and candidate baseline mismatch 0; `git diff --check`
  passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_validation_full`.
  Timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_validation`.
- Next: continue manual review from `pipeline_summary.md`, workbook
  `Review Guide`, `Manual Oracle Guide`, `Review Queue`, and `Review Signoff`;
  keep the 8 baseline timeout rows and 7 baseline-not-verified candidate rows
  as caveats unless a stronger baseline campaign is explicitly requested.

## 2026-07-05 13:38 CST

- Goal: close the remaining review-packet verifier gap so generated
  `Review Signoff` validation is checked by the independent packet verifier,
  not only by the full pipeline orchestrator.
- Work completed: updated `test/TARV/scripts/verify_review_packet.py` to require
  `review_signoff_validation.csv/json/md` and add three hard checks:
  `SIGNOFF_VALIDATION_SUMMARY_PASS`, `SIGNOFF_VALIDATION_ROW_COUNT`, and
  `SIGNOFF_VALIDATION_TEMPLATE_SYNC`. These checks confirm pre-review mode,
  8 PASS/0 FAIL, 54 signoff rows, 54 blank decisions, no nonblank decisions,
  and synchronization with the generated signoff template.
- Stability tooling: updated `test/TARV/scripts/compare_pipeline_results.py`
  with `--profile verifier-signoff-added`, which expects exactly +6 verifier
  checks/+6 verifier passes while keeping semantic/runtime/benchmark metrics,
  workbook sheets, reproducibility counts, signoff validation, and normalized
  stable CSV content unchanged.
- Targeted QA before full rerun: direct verifier run on
  `paper_pipeline_signoff_validation_full` returned 64 PASS, 0 WARN, 0 FAIL;
  old `manual-oracle-added` comparison remained 148 PASS; the new
  `verifier-signoff-added` comparison returned 172 PASS, 0 WARN, 0 FAIL.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_verifier_signoff_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_verifier_signoff --timeout 30
  --timeout-rerun-seconds 60`.
  Result: `pipeline_status=PASS`, `pipeline_mode=full`, elapsed 760018 ms,
  failed steps 0. The full pipeline summary now natively embeds
  `review_packet_verification` with 64 PASS, 0 WARN, 0 FAIL and
  `review_signoff_validation` with 8 PASS, 0 FAIL.
- Stable/growth audit:
  `python3 test/TARV/scripts/compare_pipeline_results.py --profile
  verifier-signoff-added --baseline
  test/TARV/results/paper_pipeline_manual_oracle_full --candidate
  test/TARV/results/paper_pipeline_verifier_signoff_full`.
  Result: 172 PASS, 0 WARN, 0 FAIL, with expected verifier delta
  `check_rows=+6`, `pass=+6`, `warn=0`, `fail=0`.
- QA: Python compilation passed for all pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`; JSON parsing passed for new
  pipeline summary, verifier JSON, signoff validation JSON, result stability
  audit JSON, and timeout rerun summary; `unzip -t` passed for the new workbook;
  direct packet assertions confirmed full PASS, verifier 64 PASS, stability
  172 PASS, signoff validation 8/0, 30 workbook sheets including
  `Manual Oracle Guide`, semantic fail 0, prefix mismatch 0, and candidate
  baseline mismatch 0; `git diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_verifier_signoff_full`.
  Timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_verifier_signoff`.
- Next: start or continue human review from `pipeline_summary.md`, workbook
  `Review Guide`, `Manual Oracle Guide`, `Review Queue`, and `Review Signoff`;
  after reviewer decisions are filled, run
  `validate_review_signoff.py --mode complete` and then `verify_review_packet.py`
  again before claiming human signoff is complete.

## 2026-07-05 13:56 CST

- Goal: make result stability auditing a native part of the full pipeline
  rather than a manual post-pipeline command, so `pipeline_summary.json`
  records the baseline, profile, command result, and audit counts.
- Work completed: updated `test/TARV/scripts/run_full_review_pipeline.py` with
  `--stability-baseline`, `--stability-profile`, `--stability-timeout`, and
  `--skip-stability-audit`. When a baseline is provided, the pipeline now writes
  an interim candidate summary, runs `compare_pipeline_results.py`, then writes
  the final summary with `result_stability_audit` embedded. If no stability
  baseline is configured, the pipeline no longer advertises a missing
  `result_stability_audit` artifact.
- Smoke QA: a partial `--no-run --no-workbook --skip-*` pipeline run confirmed
  the new options and summary writing path; the temporary smoke directories were
  deleted afterward.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_native_stability_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_native_stability --timeout 30
  --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_manual_oracle_full --stability-profile
  verifier-signoff-added`.
  Result: `pipeline_status=PASS`, `pipeline_mode=full`, elapsed 761484 ms,
  failed steps 0. The command list now includes `compare_result_stability`.
- Native stability result: `result_stability_audit` is embedded in
  `pipeline_summary.json` with profile `verifier-signoff-added`, 172 PASS,
  0 WARN, 0 FAIL, expected verifier delta `check_rows=+6`, `pass=+6`, and
  zero reproducibility delta.
- QA: Python compilation passed for all pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`; JSON parsing passed for new
  pipeline summary, verifier JSON, signoff validation JSON, result stability
  audit JSON, and timeout rerun summary; `unzip -t` passed for the new workbook;
  direct packet assertions confirmed full PASS, seven pipeline commands
  including `compare_result_stability`, verifier 64 PASS, stability 172 PASS,
  signoff validation 8/0, 30 workbook sheets including `Manual Oracle Guide`,
  semantic fail 0, prefix mismatch 0, and candidate baseline mismatch 0;
  `git diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_native_stability_full`.
  Timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_native_stability`.
- Next: continue human review from the latest `pipeline_summary.md`, workbook
  `Review Guide`, `Manual Oracle Guide`, `Review Queue`, and `Review Signoff`.
  Future full reruns should pass `--stability-baseline` and
  `--stability-profile` when the run is intended to produce a paper-review
  stability packet.

## 2026-07-05 14:12 CST

- Goal: close the reproducibility gap left by the experiment-level manifest,
  which is written before late pipeline artifacts such as signoff validation,
  packet verification, native stability audit, final pipeline summary, and
  command logs.
- Work completed: updated `test/TARV/scripts/run_full_review_pipeline.py` to
  write `pipeline_artifact_manifest.csv/json/md` after final pipeline outputs.
  The manifest hashes final top-level result files, `pipeline_command_logs`, and
  matching timeout-rerun files, while excluding `pipeline_artifact_manifest.*`
  itself to avoid self-referential hashes. The manifest is listed in final
  `pipeline_summary.json` artifacts.
- Smoke QA: partial pipeline run confirmed manifest generation and no self-hash
  rows; temporary smoke directories were deleted.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_artifact_manifest_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest --timeout 30
  --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_manual_oracle_full --stability-profile
  verifier-signoff-added`.
  Result: `pipeline_status=PASS`, `pipeline_mode=full`, elapsed 761752 ms,
  failed steps 0.
- Pipeline artifact manifest result: 130 rows, covering final
  `pipeline_summary.*`, `review_packet_verification.*`,
  `review_signoff_validation.*`, `result_stability_audit.*`,
  `paper_review_results.xlsx`, `compare_result_stability` command logs, and
  timeout-rerun files. Direct assertions confirmed no self-hash rows and the
  expected categories `result_file`, `command_log`, and `timeout_rerun_file`.
- QA: Python compilation passed for all pipeline scripts and
  `src/TAMonitor/make_tamonitor_xlsx.py`; JSON parsing passed for the new
  pipeline summary, pipeline artifact manifest, verifier JSON, signoff
  validation JSON, result stability audit JSON, and timeout rerun summary;
  `unzip -t` passed for the new workbook; direct packet assertions confirmed
  full PASS, seven pipeline commands including `compare_result_stability`,
  verifier 64 PASS, stability 172 PASS, signoff validation 8/0, manifest 130
  rows, 30 workbook sheets including `Manual Oracle Guide`, semantic fail 0,
  prefix mismatch 0, and candidate baseline mismatch 0; `git diff --check`
  passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full`.
  Timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest`.
- Next: continue human review from the latest `pipeline_summary.md`, workbook
  `Review Guide`, `Manual Oracle Guide`, `Review Queue`, and `Review Signoff`;
  use `pipeline_artifact_manifest.md` as the final hash ledger for all
  pipeline-level review artifacts.

## 2026-07-05 14:20 CST

- Goal: make the new pipeline artifact manifest independently checkable without
  relying on one-off ad hoc assertions.
- Work completed: added
  `test/TARV/scripts/verify_pipeline_artifact_manifest.py`. The checker writes
  `pipeline_artifact_manifest_verification.csv/json/md` and verifies manifest
  files, schema, CSV/JSON row-count sync, unique keys, no self-hash rows, file
  existence, sha256 and size matches, required final artifact coverage, command
  log coverage for every pipeline command, timeout-rerun coverage, and required
  categories. It is intentionally a post-manifest sidecar and is not hashed by
  `pipeline_artifact_manifest.*`.
- Pipeline maintenance: added the new verifier to
  `run_full_review_pipeline.py`'s Python syntax preflight list and excluded
  `pipeline_artifact_manifest_verification.*` from future artifact-manifest
  rows to avoid stale sidecar/circular hashing.
- Verification run:
  `python3 test/TARV/scripts/verify_pipeline_artifact_manifest.py --output-dir
  test/TARV/results/paper_pipeline_artifact_manifest_full --timeout-rerun
  test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest`.
  Result: 10 PASS, 0 WARN, 0 FAIL; 130 manifest rows; categories
  `command_log=14`, `result_file=113`, `timeout_rerun_file=3`; missing files,
  bad hashes, and bad sizes all 0.
- QA: Python compilation passed for `verify_pipeline_artifact_manifest.py` and
  updated `run_full_review_pipeline.py`; verification JSON parsed; direct
  assertions confirmed all 10 required check IDs are present and all pass;
  `git diff --check` passed.
- Current latest packet remains
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full`.
  New sidecar:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full/pipeline_artifact_manifest_verification.md`.
- Next: continue human review from latest `pipeline_summary.md` and workbook;
  use `pipeline_artifact_manifest_verification.md` to confirm the final hash
  ledger before citing the packet's reproducibility evidence.

## 2026-07-05 14:25 CST

- Goal: keep the handoff mechanism healthy after `.codex/PROJECT_STATE.md`
  exceeded the roughly 250-line threshold.
- Work completed: confirmed
  `.codex/archive/PROJECT_STATE_20260705_pre_manifest_verification_compact.md`
  exists, then compacted `.codex/PROJECT_STATE.md` into an active handoff that
  keeps the latest packet paths, implemented decisions, key counts,
  verification evidence, limits, and next steps while pointing to the archived
  detailed state.
- Current latest packet remains
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_artifact_manifest_full`;
  timeout rerun remains
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_artifact_manifest`.
- Next: verify line counts and archive/state references, then continue from the
  compacted state without redoing broad exploration.

## 2026-07-05 14:35 CST

- Goal: make the generated manual-oracle review protocol clearer after the user
  asked what a hand/manual oracle means.
- Work completed: updated
  `test/TARV/scripts/run_paper_experiments.py` so future packets add
  `MOG_INDEPENDENCE`, explicitly requiring oracle expectations to be derived
  from MITL semantics rather than TAMonitor, MoniTAal, stdout parsing, or
  generated verdict summaries. The Markdown writer now includes
  `decision_rule` and `must_not_claim` columns so the key review boundary is
  visible without opening the CSV.
- Verification: `python3 -m py_compile
  test/TARV/scripts/run_paper_experiments.py` passed. A no-run documentation
  smoke test,
  `python3 test/TARV/scripts/run_paper_experiments.py --out
  /tmp/tamonitor_manual_oracle_doc_smoke --no-run --no-workbook --timeout 1`,
  generated `manual_oracle_guide_rows=9`, `manual_oracle_guide_p0=6`, and
  included `MOG_INDEPENDENCE` plus the new Markdown columns.
- Important boundary: the official latest packet under
  `test/TARV/results/paper_pipeline_artifact_manifest_full` was not hand-edited,
  preserving its already verified manifest hashes. Rerun the full pipeline into
  a new directory before citing the stronger guide as part of official results.

## 2026-07-05 14:45 CST

- Goal: promote the manual-oracle independence protocol from a source-only
  improvement into an official, hashed, reviewable result packet.
- Work completed: updated `compare_pipeline_results.py` with profile
  `manual-oracle-independence-added`, allowing only
  `manual_oracle_guide_rows +1`, `manual_oracle_guide_p0 +1`,
  `manual_oracle_guide_p1 +0`, no workbook sheet delta, no verifier-count
  delta, no reproducibility-count delta, and stable normalized content for the
  semantic/runtime/benchmark CSV set. Updated `run_full_review_pipeline.py` to
  accept the new profile. Updated `verify_review_packet.py` so
  `MOG_INDEPENDENCE` is required by the manual-oracle protocol gate.
- Subagent: read-only explorer confirmed the expected doc-only diffs and the
  needed profile/verifier allowances; it made no file changes.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_manual_oracle_independence_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_manual_oracle_independence_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_artifact_manifest_full --stability-profile
  manual-oracle-independence-added`.
  Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 768408 ms.
- Key results: manual-oracle guide rows 9, P0 rows 6, P1 rows 3; semantic
  correctness verified 53; semantic fail 0; prefix mismatch 0; candidate
  baseline mismatches 0; review packet verifier 64 PASS/0 FAIL; signoff
  validation 8 PASS/0 FAIL with 54 blank decisions; result stability audit
  175 PASS/0 FAIL; timeout rerun still has 8/8 timeout caveats at 60 seconds.
- Additional QA: `verify_pipeline_artifact_manifest.py` on the new packet
  produced 10 PASS, 0 WARN, 0 FAIL, 130 manifest rows, 0 missing files, 0 bad
  hashes, and 0 bad sizes. JSON parsing passed for key summary/verifier files;
  `unzip -t` passed for the workbook; direct assertions confirmed
  `MOG_INDEPENDENCE` is P0, section `independence`, and forbids substituting
  implementation agreement for a hand oracle. `git diff --check` passed.
- Current latest packet is now
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_manual_oracle_independence_full`.
  Current timeout rerun is
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_manual_oracle_independence_full`.

## 2026-07-05 15:09 CST

- Goal: reduce benchmark-translation ambiguity by turning excluded/not-promoted
  XML rows into explicit, reproducible blocker evidence instead of leaving them
  as generic review debt.
- Work completed: fixed a source-level hazard in
  `test/TARV/scripts/run_paper_experiments.py`: `never_b.xml` is now explicitly
  `not_claimed` because tested MightyPPL strict/weak global and `!F` encodings
  do not match the MoniTAal TA current-event boundary; the old unsafe
  name-based `never_b -> G(!b)` heuristic is disabled. `time-must-pass.xml` is
  now explicitly `not_claimed` as a time-divergence/time-must-pass automaton
  rather than an ordinary trace-level MITL benchmark formula.
- Added `test/TARV/scripts/analyze_benchmark_blockers.py`, which reads a packet
  and writes `benchmark_blocker_diagnostics.csv/json/md`. For `never_b.xml` it
  runs TAMonitor probes documenting that natural candidate encodings fail the
  first-event or later-b boundary; for the other 7 non-proof-ready XML rows it
  records approximate/no-candidate/time-divergence blocker classes.
- Pipeline integration: `run_full_review_pipeline.py` now runs
  `analyze_benchmark_blockers` as a formal command and lists
  `benchmark_blocker_diagnostics.md` in `pipeline_summary` artifacts.
  `compare_pipeline_results.py` gained profile
  `benchmark-blocker-diagnostics-added`, allowing only the refined not-claimed
  blocker reason text for `never_b.xml` and `time-must-pass.xml` while keeping
  semantic/runtime/benchmark verdict evidence stable.
- Full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_benchmark_blocker_diagnostics_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_benchmark_blocker_diagnostics_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_manual_oracle_independence_full
  --stability-profile benchmark-blocker-diagnostics-added`.
  Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 767880 ms.
- Key results: semantic correctness verified 53; semantic fail 0; prefix
  mismatch 0; candidate baseline mismatches 0; review packet verifier 64
  PASS/0 FAIL; signoff validation 8 PASS/0 FAIL with 54 blank decisions;
  result stability audit 172 PASS/0 FAIL; blocker diagnostics 8 rows with
  classes `approximate_candidate_needs_edge_proof=4`,
  `no_conservative_candidate=2`, `current_event_boundary_no_candidate=1`,
  `time_divergence_not_trace_formula=1`; timeout rerun still has 8/8 timeout
  caveats at 60 seconds.
- Additional QA: `verify_pipeline_artifact_manifest.py` produced 10 PASS,
  0 WARN, 0 FAIL with 135 manifest rows, 0 missing files, 0 bad hashes, and
  0 bad sizes. The manifest covers `benchmark_blocker_diagnostics.*` and
  `analyze_benchmark_blockers` command logs. JSON parsing, workbook `unzip -t`,
  direct packet assertions, Python compilation, and `git diff --check` passed.
- Current latest packet is now
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_benchmark_blocker_diagnostics_full`.
  Current timeout rerun is
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_benchmark_blocker_diagnostics_full`.

## 2026-07-05 15:19 CST

- Goal: close the manual-review visibility gap where `benchmark_blocker_diagnostics.*` was hashed in the packet but absent from `paper_review_results.xlsx`.
- Work completed: updated `build_paper_review_workbook.mjs` with optional `Benchmark Blockers` sheet support; added `rebuild_review_workbook.py`; changed `run_full_review_pipeline.py` so blocker diagnostics are generated before packet verification and the workbook is rebuilt afterward; strengthened `verify_review_packet.py` to require blocker files/sheet when present and to prefer the current output directory workbook over stale absolute summary paths; updated `compare_pipeline_results.py` so `benchmark-blocker-diagnostics-added` expects the new sheet and +4 verifier checks.
- Verification: Python compile passed for updated pipeline/verifier/stability/rebuild/analyzer/experiment scripts; Node `--check` passed for the workbook builder. Smoke copy `/tmp/tamonitor_workbook_blocker_smoke` rebuilt successfully with 31 sheets/tables and `Benchmark Blockers`; `verify_review_packet.py` produced 68 PASS/0 FAIL; `compare_pipeline_results.py --profile benchmark-blocker-diagnostics-added` produced 172 PASS/0 FAIL with expected added sheet `Benchmark Blockers`.
- Next: run a fresh full pipeline into a new official packet, then run artifact-manifest and workbook integrity checks before promoting it as latest.

## 2026-07-05 15:35 CST

- Goal: promote the blocker-workbook fix into the official review packet rather than leaving it as a smoke-tested source change.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_blocker_workbook_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_blocker_workbook_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_benchmark_blocker_diagnostics_full --stability-profile benchmark-blocker-diagnostics-added`.
- Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 789976 ms. Commands now include `analyze_benchmark_blockers`, `rebuild_review_workbook_after_blockers`, `verify_review_packet`, and `compare_result_stability` in that order.
- Key evidence: workbook has 31 sheets/tables and includes `Benchmark Blockers`; packet verifier 68 PASS/0 FAIL; result stability audit 172 PASS/0 FAIL with expected added sheet `Benchmark Blockers`; blocker diagnostics remain 8 rows with classes 4 approximate-edge-proof, 2 no-candidate, 1 current-event-boundary, 1 time-divergence; signoff validation 8 PASS/0 FAIL; timeout rerun still has 8/8 timeouts at 60 seconds.
- Additional QA: artifact manifest verifier 10 PASS/0 FAIL with 141 manifest rows (`command_log=18`, `result_file=120`, `timeout_rerun_file=3`); JSON parsing passed for key result files; `unzip -t` passed for `paper_review_results.xlsx`; direct assertions passed for command order, sheet/table counts, manifest coverage, semantic zero-failure metrics, prefix mismatch 0, candidate baseline mismatch 0, and formula-error scan matched 0 entries. Python compile, Node `--check`, and `git -C tool/MightyPPL diff --check` passed.
- Current latest packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_blocker_workbook_full`. Current timeout rerun: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_blocker_workbook_full`.

## 2026-07-05 15:41 CST

- Goal: close a reproducibility gap where final review-pipeline scripts were not all included in `reproducibility_manifest.csv` source hashes.
- Work completed: changed `run_paper_experiments.py` so `source_hash_paths()` includes all `test/TARV/scripts/*.py` and `*.mjs` plus existing TAMonitor/MightyPPL sources. Added `REPRO_SOURCE_HASH_COVERAGE` in `verify_review_packet.py`. Added stability profile `pipeline-source-hashes-added` in `compare_pipeline_results.py` and `run_full_review_pipeline.py`, expecting only `reproducibility_manifest_rows +7`, `reproducibility_source_hashes +7`, and verifier `check_rows/pass +1`.
- Verification: Python compile passed for changed scripts; Node `--check` passed for workbook builder. A no-run smoke packet under `/tmp/tamonitor_source_hash_smoke` produced `reproducibility_source_hashes=23`, `reproducibility_manifest_rows=98`, and all 10 required pipeline script source hashes.
- Next: run a full pipeline into a new packet with `--stability-profile pipeline-source-hashes-added`, then run manifest/workbook/direct checks before promoting it as latest.

## 2026-07-05 15:57 CST

- Goal: promote review-pipeline source-hash coverage into the official result packet.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_source_hashes_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_source_hashes_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_blocker_workbook_full --stability-profile pipeline-source-hashes-added`.
- Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 790383 ms. `run_paper_experiments` now reports `reproducibility_manifest_rows=98`, `reproducibility_source_hashes=23`, `reproducibility_result_hashes=56`.
- Key evidence: all 10 `test/TARV/scripts` review-pipeline scripts are present as `source_sha256` rows; `verify_review_packet.py` produced 69 PASS/0 FAIL including `REPRO_SOURCE_HASH_COVERAGE`; result stability audit profile `pipeline-source-hashes-added` produced 148 PASS/0 FAIL and allowed only source-hash/reproducibility growth plus verifier +1.
- Additional QA: artifact manifest verifier 10 PASS/0 FAIL with 141 manifest rows; JSON parsing passed for key result files; `unzip -t` passed for workbook; direct assertions passed for source-hash coverage, command order, workbook 31 sheets/tables with `Benchmark Blockers`, semantic zero-failure metrics, prefix mismatch 0, candidate baseline mismatch 0, timeout rerun 8/8 still timeouts, and formula-error scan matched 0 entries. Python compile, Node `--check`, and `git -C tool/MightyPPL diff --check` passed.
- Current latest packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_source_hashes_full`. Current timeout rerun: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_source_hashes_full`.

## 2026-07-05 16:03 CST

- Goal: improve manual-review visibility for timeout caveats and signoff validation inside the Excel workbook.
- Work completed: added optional `Signoff Validation`, `Timeout Rerun Summary`, and `Timeout Rerun` sheets to `build_paper_review_workbook.mjs`; changed `rebuild_review_workbook.py` to prepare `timeout_rerun_summary.csv` and `timeout_rerun_details.csv` from the timeout-rerun directory before rebuilding; changed `run_full_review_pipeline.py` to pass `--timeout-rerun-dir` to the workbook rebuild; strengthened `verify_review_packet.py` to require those sheets/files when timeout-rerun evidence exists; added stability profile `timeout-rerun-workbook-added`.
- Verification: Python compile and Node `--check` passed. Smoke copy `/tmp/tamonitor_timeout_workbook_smoke` rebuilt to 34 sheets/tables with the three new sheets; `verify_review_packet.py` produced 70 PASS/0 FAIL; `compare_pipeline_results.py --profile timeout-rerun-workbook-added` produced 148 PASS/0 FAIL; timeout summary/detail CSVs had 11 and 8 rows respectively.
- Next: run a fresh full pipeline into a new packet with `--stability-profile timeout-rerun-workbook-added`, then run artifact-manifest/workbook/direct checks before promoting it as latest.

## 2026-07-05 16:19 CST

- Goal: promote signoff-validation and timeout-rerun workbook evidence into the official review packet.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_timeout_workbook_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_timeout_workbook_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_source_hashes_full --stability-profile timeout-rerun-workbook-added`.
- Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 787975 ms. `rebuild_review_workbook_after_blockers` now runs with `--timeout-rerun-dir` and reports timeout summary/details present.
- Key evidence: workbook has 34 sheets/tables and includes `Signoff Validation`, `Timeout Rerun Summary`, `Timeout Rerun`, and `Benchmark Blockers`; `verify_review_packet.py` produced 70 PASS/0 FAIL including `TIMEOUT_RERUN_WORKBOOK_EVIDENCE`; result stability audit profile `timeout-rerun-workbook-added` produced 148 PASS/0 FAIL and allowed only the three new workbook sheets plus verifier +1.
- Additional QA: artifact manifest verifier 10 PASS/0 FAIL with 146 manifest rows (`command_log=18`, `result_file=125`, `timeout_rerun_file=3`); JSON parsing passed for key result files; `unzip -t` passed for workbook; direct assertions passed for timeout workbook CSV/sheet presence, timeout detail rows 8 all `timeout`, command order, workbook 34 sheets/tables, semantic zero-failure metrics, prefix mismatch 0, candidate baseline mismatch 0, source hashes 23, and formula-error scan matched 0 entries. Python compile, Node `--check`, and `git -C tool/MightyPPL diff --check` passed.
- Current latest packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_timeout_workbook_full`. Current timeout rerun: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_timeout_workbook_full`.

## 2026-07-05 16:34 CST

- Goal: investigate and fix the remaining 8 MoniTAal baseline timeout caveats rather than leaving them to the user.
- Bug found and fixed: `tool/MoniTAal/src/monitaal-bin/main.cpp` used `while (not input.eof() || monitor.status() == INCONCLUSIVE)` in file monitoring, causing EOF plus inconclusive verdict to spin forever on empty reads. Changed it to `while (not input.eof() && monitor.status() == INCONCLUSIVE)`.
- Verification: rebuilt `MoniTAal-bin`; a one-event inconclusive input now exits immediately with `INCONCLUSIVE` and monitored 1 event. `rerun_baseline_timeouts.py --source test/TARV/results/paper_pipeline_timeout_workbook_full --out test/TARV/results/baseline_timeout_rerun_after_monitaal_eof_fix_probe --timeout 60` reran all 8 old timeout rows as `ran/INCONCLUSIVE`, 0 timeouts, elapsed 39 ms.
- Main experiment probe: `python3 test/TARV/scripts/run_paper_experiments.py --out test/TARV/results/paper_pipeline_monitaal_eof_fix_probe2 --timeout 30` produced semantic fail 0, prefix mismatch 0, baseline runs 44, baseline timeouts 0, skipped-no-input 3, translation candidate matches 43, mismatches 0, not-verified 0, claim audit 23 PASS/0 WARN/0 FAIL, goal fail 0, requirements fail 0, human review queue fail 0.
- Review logic updated: `run_paper_experiments.py` no longer treats gear rows as mandatory appendix timeout caveats when original-input MoniTAal baselines finish; gear proof-ready rows become `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` with explicit wording that baseline matches are trace-level evidence, not automatic XML-to-MITL equivalence proofs.
- Subagent evidence: read-only explorer Hegel confirmed `MoniTAal-bin` exposes only concrete/interval plus inclusion/clock-abstraction/div options, and current binary returns all 8 old timeout commands as `INCONCLUSIVE`.
- Next: update stability/verifier expectations, run a fresh full official pipeline, verify artifact manifest/workbook/direct assertions, then promote the new packet.

## 2026-07-05 16:47 CST

- Goal: promote the MoniTAal EOF fix into the official paper-review packet with verifier/stability coverage.
- Work completed: added `tool/MoniTAal/src/monitaal-bin/main.cpp` to reproducibility source hashes; changed `verify_review_packet.py` timeout-rerun logic from hard-coded 8-still-timeout to `TIMEOUT_RERUN_MATCHES_CURRENT_TIMEOUTS`; added `monitaal-eof-fix` stability profile in `compare_pipeline_results.py` and `run_full_review_pipeline.py`.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_monitaal_eof_fix_full --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_monitaal_eof_fix_full --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_timeout_workbook_full --stability-profile monitaal-eof-fix`.
- Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 72208 ms. Baseline timeouts are now 0; MoniTAal baselines ran 44 rows with 3 skipped-no-input rows; translation candidate baseline matches/mismatches/not-verified are 43/0/0.
- Key evidence: semantic fail 0; prefix mismatch 0; verifier 70 PASS/0 FAIL; stability audit 148 PASS/0 FAIL; signoff validation 8 PASS/0 FAIL with 47 blank signoff rows; paper claim audit 23 PASS/0 WARN/0 FAIL; timeout rerun selected 0 rows because current baseline has no timeout rows; workbook has 34 sheets including timeout-rerun and blocker sheets.
- Additional QA: artifact manifest verifier 10 PASS/0 FAIL with 146 manifest rows; JSON parsing passed; `unzip -t` passed for workbook; direct assertions passed for 0 baseline timeouts, 43/43 candidate matches, 8 `INCONCLUSIVE` baseline verdicts, gear theorem-boundary wording, MoniTAal source hash coverage, empty timeout rerun evidence, and formula error scan 0 entries. Python compile, bundled Node `--check`, `git -C tool/MoniTAal diff --check`, and `git -C tool/MightyPPL diff --check` passed.
- Current latest packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_monitaal_eof_fix_full`. Current timeout rerun: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_monitaal_eof_fix_full`.

## 2026-07-05 17:13 CST

- Goal: remove the last skipped-no-input XML baseline caveat without pretending
  generated probes are original benchmark traces.
- Work completed: added generated empty timed-word probes for
  `delay-example.xml`, `never_b.xml`, and `time-must-pass.xml`; each row is
  labeled `input_origin=generated_empty_no_original_input` with explicit
  baseline-only/not-original rationale. Strengthened
  `verify_review_packet.py` to require that rationale. Added
  `generated-empty-inputs-added` stability expectations and benchmark-manifest
  input-origin match counts so `original_input_match_count` means repository
  input, not arbitrary non-generated input.
- Bug found and fixed: `build_paper_review_workbook.mjs` could abort with
  `fatal runtime error: Rust cannot catch foreign exceptions` while rendering
  many wide/large PNG previews. Workbook generation now renders only an
  allowlisted set of review-entry previews and records skipped preview sheets in
  `workbook_preview_manifest.*`; full evidence remains in XLSX/CSV.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_generated_empty_inputs_v5_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_generated_empty_inputs_v5_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_monitaal_eof_fix_full --stability-profile
  generated-empty-inputs-added`.
- Result: `pipeline_status=PASS`, full mode, failed steps 0, elapsed 51211 ms.
  MoniTAal baselines: 47 ran, 0 timeouts, 0 skipped-no-input, 3 generated empty
  baseline-only probes. Translation candidate baseline matches/mismatches:
  43/0. Semantic fail 0; prefix mismatch 0.
- Key evidence: verifier 71 PASS/0 FAIL including
  `BASELINE_GENERATED_EMPTY_BOUNDARY`; stability audit 149 PASS/0 FAIL; signoff
  validation 8 PASS/0 FAIL with 47 blank decisions; workbook 34 sheets/tables;
  preview manifest 13 rendered review-entry previews and 21 skipped
  full-evidence sheets.
- Additional QA: artifact manifest verifier 10 PASS/0 FAIL with 127 manifest
  rows; JSON parsing passed; `unzip -t` passed for workbook; direct assertions
  passed for 3 generated-empty `ran/INCONCLUSIVE` rows and all required
  benchmark/baseline workbook sheets. Python compile, bundled Node `--check`,
  `git -C tool/MoniTAal diff --check`, and `git -C tool/MightyPPL diff --check`
  passed.
- Current latest packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_generated_empty_inputs_v5_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_generated_empty_inputs_v5_full`.

## 2026-07-05 17:35 CST

- Goal: add MoniTAal `benchmark/main.cpp` hard-coded benchmark evidence without
  conflating it with XML-file `MoniTAal-bin` baseline or XML-to-MITL proof
  claims.
- Work completed: added `run_monitaal_hardcoded_benchmarks.py`; enabled
  `MONITAAL_BUILD_BENCH` in MightyPPL's MoniTAal external build; fixed
  `benchmark/main.cpp` seed output newline; integrated the hardcoded sidecar
  into `run_full_review_pipeline.py` before final workbook rebuild and packet
  verification; added optional `Hardcoded Benchmarks` workbook sheet; added
  packet verifier boundary checks; added stability profile
  `hardcoded-benchmarks-added`; hardened artifact-manifest verification with
  `MANIFEST_HARDCODED_BENCHMARK_COVERAGE`.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_hardcoded_benchmarks_manifest_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_hardcoded_benchmarks_manifest_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_generated_empty_inputs_v5_full
  --stability-profile hardcoded-benchmarks-added`.
- Result: `pipeline_status=PASS`, failed steps 0. Hard-coded benchmark rows:
  7 ran, 0 timeout, 0 error, 0 parse_failed. Workbook has 35 sheets including
  `Hardcoded Benchmarks`. Packet verifier: 75 PASS/0 FAIL. Stability audit:
  149 PASS/0 FAIL. Artifact-manifest verifier: 11 PASS/0 FAIL with 133
  manifest rows and explicit hardcoded coverage. Direct assertions, xlsx unzip,
  Python compile, bundled Node `--check`, and nested-repo `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_hardcoded_benchmarks_manifest_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_hardcoded_benchmarks_manifest_full`.

## 2026-07-05 17:50 CST

- Goal: strengthen MightyPPL user-level syntax semantics coverage for finite
  words while continuing to fix experiment-exposed runtime issues.
- Work completed: added 17 finite-word hand-oracle semantic cases covering
  user-level formula/atom/interval/starred/past/Pnueli constructs that
  previously only had infinite-word runtime evidence; tightened syntax coverage
  so all 36 user-level runtime grammar rows now require finite+infinite
  evidence. Added stability profile `finite-syntax-oracles-added`.
- Bug found and fixed: finite monitoring could expose a fourth public verdict
  `INCONSISTENT` when positive and negative finite monitors overlapped or both
  emptied. `src/TAMonitor/MonitorRunner.cpp` now maps those overlap/gap states
  conservatively to `INCONCLUSIVE`, preserving the required three-valued RV
  verdict surface.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_finite_syntax_oracles_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_finite_syntax_oracles_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_hardcoded_benchmarks_manifest_full
  --stability-profile finite-syntax-oracles-added`.
- Result: `pipeline_status=PASS`, failed steps 0. Semantic cases: 87 total,
  70 hand-oracle runtime verified, 34 finite verified, 36 infinite verified,
  0 semantic fail, 0 prefix mismatch, 0 oracle review-required. Syntax
  coverage: 36/36 user-level runtime rows finite+infinite verified, missing 0.
  Packet verifier: 75 PASS/0 FAIL. Stability audit: 149 PASS/0 FAIL. Artifact
  manifest verifier: 11 PASS/0 FAIL. Direct assertions confirmed no
  `INCONSISTENT` runtime verdicts. Xlsx unzip, Python compile, bundled Node
  `--check`, whitespace scan, and nested-repo `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_finite_syntax_oracles_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_finite_syntax_oracles_full`.

## 2026-07-05 17:56 CST

- Goal: promote the "no fourth public verdict" property from a one-off
  assertion into an automatic review-packet invariant.
- Subagent: read-only explorer inspected verdict-bearing artifacts in
  `paper_pipeline_finite_syntax_oracles_full`; found no structured
  `INCONSISTENT` verdicts and identified extra fields such as `expected_prefix`,
  `semantic_oracle_derivations.actual_final`, candidate prefix `actual_final`,
  and mirrored JSON artifacts that should be checked.
- Work completed: added `PUBLIC_RV_THREE_VALUED_VERDICTS` to
  `test/TARV/scripts/verify_review_packet.py`. The guard scans selected
  top-level CSV/JSON verdict columns, semicolon/comma/pipe-separated verdict
  lists, every generated `steps.csv`, every run `summary.csv` final verdict,
  and every run `metadata.json` final verdict. It permits only
  `POSITIVE`, `NEGATIVE`, `INCONCLUSIVE`, with `NOT_RUN_BUILD_ONLY` allowed
  only for build-only final-verdict fields. Added stability profiles
  `three-valued-verdict-guard-added` and
  `finite-syntax-oracles-and-three-valued-guard-added` to
  `compare_pipeline_results.py` and `run_full_review_pipeline.py`.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_three_valued_guard_v2_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_three_valued_guard_v2_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_hardcoded_benchmarks_manifest_full
  --stability-profile finite-syntax-oracles-and-three-valued-guard-added`.
- Result: `pipeline_status=PASS`, failed steps 0, elapsed 49198 ms. Packet
  verifier: 76 PASS/0 FAIL. New guard checked 440 verdict sources/columns and
  494773 verdict tokens; observed `INCONCLUSIVE=332109`, `NEGATIVE=161285`,
  `NOT_RUN_BUILD_ONLY=123`, `POSITIVE=1256`, invalid=none. Stability audit:
  149 PASS/0 FAIL. Artifact-manifest verifier: 11 PASS/0 FAIL with 133 rows,
  0 missing files, 0 bad hashes, 0 bad sizes. Workbook unzip, Python compile,
  bundled Node `--check`, whitespace scan, and nested-repo `diff --check`
  passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_three_valued_guard_v2_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_three_valued_guard_v2_full`.

## 2026-07-05 18:22 CST

- Goal: strengthen the manual-review/signoff packet so the user can hand-audit
  claims without hidden approval ambiguity or dangling evidence references.
- Work completed: added row-level signoff policy fields
  `recommended_decision`, `forbidden_decisions`, and
  `completion_requirements`; `validate_review_signoff.py` now checks generated
  policy consistency, rejects forbidden human decisions, requires reviewer notes
  for completed decisions, and resolves every signoff `evidence_artifacts`
  token to a packet file, repo file, workbook sheet, or nonempty `glob:`
  pattern. `Review Signoff` and `Manual Oracle Guide` markdown/CSV output now
  expose the evidence and reviewer action fields needed for hand review.
- Bugs found and fixed while experimenting: final workbook rebuild could fix
  `paper_review_results.xlsx` while leaving `experiment_summary.json/csv` at a
  stale `workbook_status=failed`, which caused packet verification and
  stability audit failures. Added synchronized summary JSON/CSV writing in
  `run_paper_experiments.py`, final rebuild status back-propagation in
  `rebuild_review_workbook.py`, and a post-rebuild summary reload in
  `run_full_review_pipeline.py`. Also removed `Review Signoff` from the
  workbook preview allowlist after its wide policy columns made preview
  rendering fail.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_signoff_evidence_resolution_v3_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_resolution_v3_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_signoff_policy_full --stability-profile
  signoff-evidence-resolution-added`.
- Result: `pipeline_status=PASS`, failed steps 0, elapsed 53384 ms. Experiment
  workbook status is `ok` in both JSON and CSV. Signoff validation: 10 PASS,
  0 FAIL, 47 blank decisions, 0 policy mismatches, 0 forbidden decisions,
  0 unresolved evidence tokens. Packet verifier: 76 PASS/0 FAIL. Stability
  audit: 163 PASS/0 FAIL. Artifact-manifest verifier: 11 PASS/0 FAIL with
  132 rows.
- Negative tests: a temp complete-mode signoff copy with a forbidden
  `APPROVE_AS_CLAIMED` row failed as expected with
  `forbidden_decision_rows=1`; a temp pre-review copy with a bogus evidence
  token failed as expected with `unresolved_evidence_tokens=1`.
- Additional QA: old failure directory
  `paper_pipeline_signoff_evidence_resolution_v2_full` was targeted with the
  rebuild fix and then passed packet verification 76/76; `unzip -t` passed for
  the v3 workbook; Python compilation and bundled Node `--check` passed;
  whitespace scan found no trailing whitespace; nested MoniTAal and MightyPPL
  `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_resolution_v3_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_resolution_v3_full`.

## 2026-07-05 18:36 CST

- Goal: close the manual-review roundtrip gap so a human-filled `Review
  Signoff` can be safely imported and validated without trusting stale workbook
  or CSV-generated columns.
- Subagent: read-only explorer confirmed there was no first-class import path;
  existing support only validated `review_signoff_template.csv` in place, and
  packet verification always assumed pre-review blank signoff.
- Work completed: added `test/TARV/scripts/import_review_signoff.py`. The
  importer accepts `--from-csv` or `--from-xlsx`, reads the `Review Signoff`
  sheet for XLSX, merges only reviewer-owned fields
  `reviewer_decision/reviewer/review_date/reviewer_notes`, rejects missing or
  extra signoff IDs and immutable generated-field mismatches, writes
  `review_signoff_imported.csv` plus `review_signoff_import_report.*`, and
  applies only with `--apply` after a clean import and backup. Added
  `validate_review_signoff.py --signoff-csv` and `--output-prefix`, and added
  `verify_review_packet.py --signoff-mode pre-review|complete`.
- Review packet change: `run_paper_experiments.py` now adds
  `RG_SIGNOFF_IMPORT_ROUNDTRIP` to `Review Guide`, telling reviewers to import
  human-owned fields and then run complete-mode validation/verifier. Source hash
  and pipeline py-compile coverage now include `import_review_signoff.py`.
- Bugs found and fixed while experimenting: `compare_pipeline_results.py`
  initially lacked `signoff-import-added` in argparse choices, so the first
  full pipeline failed at stability despite runtime and packet verifier passing.
  Added the profile to compare CLI choices and help text. Also found a test
  isolation mistake where a temp symlink clone let complete-mode validation
  write through to the v3 baseline; restored v3 pre-review validation and made
  later temp clones copy all writable validation/verifier files.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_signoff_import_v2_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_signoff_import_v2_full --timeout
  30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_signoff_evidence_resolution_v3_full
  --stability-profile signoff-import-added`.
- Result: `pipeline_status=PASS`, failed steps 0, elapsed 48881 ms. Review
  guide rows/P0: 14/8; source hashes: 27. Signoff validation: 10 PASS/0 FAIL,
  47 blank decisions, 0 policy mismatches, 0 forbidden decisions, 0 unresolved
  evidence tokens. Packet verifier: 76 PASS/0 FAIL. Stability audit:
  163 PASS/0 FAIL. Artifact-manifest verifier: 11 PASS/0 FAIL with 132 rows.
- Import QA: isolated filled-CSV import applied 47 nonblank decisions, complete
  validation passed, and complete-mode packet verifier passed 76/76. Isolated
  XLSX extraction from the v2 workbook returned 47 blank rows and pre-review
  validation passed 10/10. Stale generated-field import failed as expected with
  one immutable field mismatch and did not apply.
- Additional QA: `unzip -t` passed for the v2 workbook; Python compilation and
  bundled Node `--check` passed; whitespace scan found no trailing whitespace;
  nested MoniTAal and MightyPPL `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_import_v2_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_import_v2_full`.

## 2026-07-05 18:46 CST

- Goal: close the remaining signoff reviewability gap where a `Review
  Signoff` row could name a workbook sheet or source row that did not actually
  exist, making manual review harder to audit.
- Work completed: `validate_review_signoff.py` now parses semicolon-separated
  `source_sheet` names and checks them against `paper_review_results.xlsx`;
  it also resolves each signoff `source_id` against the expected generated CSV
  source rows by queue type (`GOAL_`, `MANUAL_`, `XML_PROOF_`,
  `PAPER_CLAIM_`, and `BENCHMARK_`). `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` now include the
  `signoff-source-resolution-added` profile and expose unresolved source
  counts in summaries.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_signoff_source_resolution_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_signoff_source_resolution_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_signoff_import_v2_full --stability-profile
  signoff-source-resolution-added`.
- Result: `pipeline_status=PASS`, failed steps 0, elapsed 49635 ms. Signoff
  validation: 12 PASS/0 FAIL, 47 blank decisions, 0 policy mismatches,
  0 forbidden decisions, 0 unresolved evidence tokens,
  0 unresolved source sheet tokens, and 0 unresolved source rows. Packet
  verifier: 76 PASS/0 FAIL. Stability audit: 165 PASS/0 FAIL. Artifact
  manifest verifier: 11 PASS/0 FAIL with 132 rows.
- Negative tests: an isolated copied packet with a bogus `source_sheet` failed
  validation as expected with `unresolved_source_sheet_tokens=1`; a copied
  packet with a bogus `source_id` failed as expected with
  `unresolved_source_rows=1`.
- Additional QA: latest workbook passed `unzip -t`; Python compilation passed
  for changed pipeline scripts; bundled Node `--check` passed for
  `build_paper_review_workbook.mjs`; whitespace scan found no trailing
  whitespace; nested MoniTAal and MightyPPL `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_source_resolution_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_source_resolution_full`.

## 2026-07-05 19:38 CST

- Goal: close the queue-wide source-reference reviewability gap left after
  signoff-row source resolution. Subagent Kuhn confirmed the gap: signoff
  validation covered only 47 P0/P1/P2 signoff rows, while 16 queue-only
  `P3_EXCLUSION_AUDIT` rows in `human_review_queue.csv` were not guaranteed by
  an automated source reference check.
- Work completed: `validate_review_signoff.py` now emits
  `QUEUE_SOURCE_SHEET_RESOLUTION` and `QUEUE_SOURCE_ROW_RESOLUTION` and summary
  counters for unresolved queue source references. `verify_review_packet.py`
  now independently checks every `human_review_queue.csv` row with
  `REVIEW_QUEUE_SOURCE_REFERENCES` and rejects stale validation artifacts via
  `SIGNOFF_VALIDATION_QUEUE_SOURCE_CHECKS`. Stability scripts now support
  `review-queue-source-resolution-added`.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_review_queue_source_resolution_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_review_queue_source_resolution_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_signoff_source_resolution_full
  --stability-profile review-queue-source-resolution-added`.
- Result: `pipeline_status=PASS`, failed steps 0, elapsed 50511 ms. Signoff
  validation: 14 PASS/0 FAIL, 47 blank decisions, 0 unresolved signoff source
  sheets/rows, and 0 unresolved queue source sheets/rows. Packet verifier:
  78 PASS/0 FAIL. Stability audit: 167 PASS/0 FAIL. Artifact manifest verifier:
  11 PASS/0 FAIL with 132 rows.
- Negative tests: an isolated copied packet with a bogus P3 queue-only
  `source_sheet` failed validation with
  `unresolved_queue_source_sheet_tokens=1` and packet verification failed; a
  bogus P3 queue-only `source_id` failed validation with
  `unresolved_queue_source_rows=1` and packet verification failed.
- Additional QA: latest workbook passed `unzip -t`; Python compilation passed
  for changed pipeline scripts; bundled Node `--check` passed for
  `build_paper_review_workbook.mjs`; whitespace scan found no trailing
  whitespace; nested MoniTAal and MightyPPL `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_source_resolution_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_review_queue_source_resolution_full`.

## 2026-07-05 19:43 CST

- Goal: close the adjacent review queue evidence-reference gap after queue-wide
  source references were guarded. Queue-only P3 rows can also carry
  `evidence_artifacts`, so dangling evidence links needed the same treatment.
- Work completed: `validate_review_signoff.py` now emits
  `QUEUE_EVIDENCE_FIELDS_PRESENT` and `QUEUE_EVIDENCE_RESOLUTION`, with summary
  counters for `missing_queue_evidence_rows` and
  `unresolved_queue_evidence_tokens`. `verify_review_packet.py` now
  independently checks `REVIEW_QUEUE_EVIDENCE_REFERENCES` and rejects stale
  validation artifacts via `SIGNOFF_VALIDATION_QUEUE_EVIDENCE_CHECKS`.
  Stability scripts now support `review-queue-evidence-resolution-added`.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_review_queue_evidence_resolution_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_review_queue_source_resolution_full
  --stability-profile review-queue-evidence-resolution-added`.
- Result: `pipeline_status=PASS`, failed steps 0, elapsed 48259 ms. Signoff
  validation: 16 PASS/0 FAIL, 47 blank decisions,
  0 missing queue evidence rows, 0 unresolved queue evidence tokens,
  0 unresolved signoff evidence tokens, and 0 unresolved source rows/tokens.
  Packet verifier: 80 PASS/0 FAIL. Stability audit: 169 PASS/0 FAIL. Artifact
  manifest verifier: 11 PASS/0 FAIL with 132 rows.
- Negative tests: an isolated copied packet with a bogus P3 queue-only
  `evidence_artifacts` token failed validation with
  `unresolved_queue_evidence_tokens=1` and packet verification failed; a copied
  packet with missing P3 `review_focus` failed validation with
  `missing_queue_evidence_rows=1` and packet verification failed.
- Additional QA: latest workbook passed `unzip -t`; Python compilation passed
  for changed pipeline scripts; bundled Node `--check` passed for
  `build_paper_review_workbook.mjs`; whitespace scan found no trailing
  whitespace; nested MoniTAal and MightyPPL `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_review_queue_evidence_resolution_full`.

## 2026-07-05 19:48 CST

- Goal: verify that the latest queue-wide evidence/source checks did not break
  the safe human-signoff import path or completed-review packet verification.
- Isolated complete-mode import regression: copied
  `paper_pipeline_review_queue_evidence_resolution_full`, generated a filled
  `Review Signoff` CSV using reviewer-owned fields only, ran
  `import_review_signoff.py` dry-run and `--apply`, then ran
  `validate_review_signoff.py --mode complete` and
  `verify_review_packet.py --signoff-mode complete`.
- Result: dry import `status=PASS` with no errors; apply `status=PASS`,
  `applied=True`, and `imported_nonblank_decisions=47`. Complete validation
  returned `HUMAN_SIGNOFF_COMPLETE`, 16 PASS/0 FAIL, 47 nonblank decisions,
  and 0 unresolved queue evidence/source counts. Complete packet verification
  returned 80 PASS/0 FAIL.
- Negative test: a stale generated-field import with a modified `source_id`
  failed as expected with `immutable_field_mismatches=1`, return code 1, and
  `applied=False`.
- No official result directory was modified; the test ran in a temporary copy
  of the latest packet.

## 2026-07-05 20:43 CST

- Goal: promote the isolated Review Signoff import regression into an official
  pipeline artifact and workbook sheet so the manual-review workflow is itself
  reproducible evidence.
- Work completed: added `audit_signoff_import_roundtrip.py`, wired
  `run_full_review_pipeline.py` to run it, added optional workbook sheet
  `Signoff Roundtrip`, added conditional packet verifier checks for
  `signoff_import_roundtrip_audit.{csv,json,md}`, added artifact-manifest
  coverage, and added stability profile `signoff-roundtrip-audit-added`.
- Real bugs fixed while experimenting:
  roundtrip audit artifacts were initially globally required by
  `verify_review_packet.py`, which created a recursion risk; complete
  validation was initially written under a synthetic prefix, so complete-mode
  packet verification still read pre-review validation; the temporary
  completed-review packet initially skipped workbook rebuild; Python `tempfile`
  selected `/mnt/c/...`, where workbook generation failed; and the audit
  hard-coded 47 signoff rows instead of deriving the count from
  `review_signoff_template.csv`.
- Failed run kept as evidence:
  `test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full` failed with
  `audit_signoff_import_roundtrip`, `verify_review_packet`, and stability
  failures. The failure exposed the missing temp workbook rebuild and temp-dir
  bug above.
- Passing full rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_signoff_roundtrip_audit_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_review_queue_evidence_resolution_full
  --stability-profile signoff-roundtrip-audit-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 68222 ms. Signoff roundtrip
  audit: 7 PASS/0 FAIL, expected/imported signoff rows 47/47,
  `synthetic_only=True`, `human_signoff_claim=not_claimed`. Packet verifier:
  85 PASS/0 FAIL. Stability audit: 169 PASS/0 FAIL. Artifact manifest verifier:
  12 PASS/0 FAIL with 138 rows. Workbook has 36 sheets and includes
  `Signoff Roundtrip`.
- Additional QA: focused roundtrip regression passed 7/7; workbook `unzip -t`
  passed; Python `py_compile` passed for changed pipeline scripts; bundled Node
  `--check` passed for `build_paper_review_workbook.mjs`; whitespace scan found
  no trailing whitespace; nested MoniTAal and MightyPPL `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full_v2`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_roundtrip_audit_full_v2`.

## 2026-07-05 21:34 CST

- Goal: reduce manual signoff friction without weakening claim boundaries by
  generating a reviewer-facing evidence bundle for every `Review Signoff` row.
- Work completed: added `build_signoff_evidence_bundle.py`, wired it into
  `run_full_review_pipeline.py`, added optional workbook sheet
  `Signoff Evidence`, added conditional packet verifier checks for
  `review_signoff_evidence_bundle.{csv,json,md}`, added artifact-manifest
  coverage, updated Review Guide evidence references, and added stability
  profile `signoff-evidence-bundle-added`.
- Focused check: on a copied previous packet, bundle generation produced
  47 PASS/0 FAIL, missing queue/source rows 0, unresolved evidence tokens 0,
  and workbook rebuild exposed `Signoff Evidence`. Packet verification on that
  copied old packet had one expected `REPRO_SOURCE_HASH_COVERAGE` failure
  because the old reproducibility manifest lacked the new generator script.
- Full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_signoff_evidence_bundle_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_bundle_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_signoff_roundtrip_audit_full_v2
  --stability-profile signoff-evidence-bundle-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 70420 ms. Signoff evidence
  bundle: 47 PASS/0 FAIL, missing source rows 0, unresolved evidence tokens 0,
  blank decisions 47, `generated_only=True`, `human_signoff_claim=not_claimed`.
  Packet verifier: 90 PASS/0 FAIL. Stability audit: 169 PASS/0 FAIL. Artifact
  manifest verifier: 13 PASS/0 FAIL with 144 rows. Workbook has 37 sheets and
  includes `Signoff Evidence`.
- Additional QA: latest workbook passed `unzip -t`; Python compilation passed
  for changed pipeline scripts; bundled Node `--check` passed for
  `build_paper_review_workbook.mjs`; whitespace scan found no trailing
  whitespace; nested MoniTAal and MightyPPL `diff --check` passed.
- Read-only subagent audit of the previous packet categorized remaining gaps:
  human-only signoff/proof-review rows, v2 BDD-native and compflatten runtime
  deferrals, and automatable evidence gaps. The recommended next milestone is
  evidence consistency and boundary-trace expansion, starting with stale gear
  timeout wording in XML proof ledgers.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_signoff_evidence_bundle_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_signoff_evidence_bundle_full`.
## 2026-07-05 23:08 CST

- Goal: fix automatable evidence-consistency gaps found by the previous
  subagent audit, especially stale timeout wording and INCONCLUSIVE claim
  boundaries in the TAMonitor paper-review packet.
- Work completed: updated `run_paper_experiments.py` so gear XML proof notes
  are driven by actual baseline fields; `manual_xml_candidate_review.md` now
  derives timeout/INCONCLUSIVE status from `monitaal_baseline_results.csv`;
  paper-claim and XML-proof signoff rows with INCONCLUSIVE evidence now
  recommend `APPROVE_WITH_CAVEAT` and forbid `APPROVE_AS_CLAIMED`; timeout
  rerun Markdown now reports an empty rerun as expected evidence when no
  timeout rows exist.
- Added guards: `verify_review_packet.py` now checks
  `NO_STALE_TIMEOUT_FACT_CLAIMS` and `INCONCLUSIVE_CLAIM_CAVEAT_BOUNDARY`;
  `compare_pipeline_results.py` and `run_full_review_pipeline.py` now support
  stability profile `evidence-consistency-guards-added`; `validate_review_signoff.py`
  mirrors the INCONCLUSIVE/third-valued caveat policy.
- Real bug found while experimenting: the first full run
  `test/TARV/results/paper_pipeline_evidence_consistency_full` failed because
  the new guard caught one remaining static `b_live_a_freq.xml` stale baseline
  timeout sentence, which also caused complete-mode synthetic roundtrip packet
  verification to fail. The generator wording was fixed and the rerun passed.
- Passing full rerun: `python3 test/TARV/scripts/run_full_review_pipeline.py
  --out test/TARV/results/paper_pipeline_evidence_consistency_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_evidence_consistency_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_signoff_evidence_bundle_full
  --stability-profile evidence-consistency-guards-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 72439 ms. Packet verifier
  92 PASS/0 FAIL, including both new evidence-consistency guards. Result
  stability 169 PASS/0 FAIL. Signoff roundtrip audit 7 PASS/0 FAIL.
  Artifact manifest verifier 13 PASS/0 FAIL with 144 manifest rows. Workbook
  `unzip -t` passed. Stale timeout phrase scan over the latest packet returned
  no matches.
- Additional QA: whitespace scan on changed scripts found no trailing
  whitespace; nested MightyPPL and MoniTAal `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_evidence_consistency_full_v2`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_evidence_consistency_full_v2`.

## 2026-07-05 23:23 CST

- Goal: add machine-checkable XML proof-obligation artifacts so proof-ready
  XML-to-MITL rows can be reviewed without confusing automatic prerequisites
  with human mathematical equivalence approval.
- Work completed: added generation of `xml_proof_obligations.csv/json/md`,
  workbook sheet `XML Obligations`, review-guide references, packet verifier
  guard `XML_PROOF_OBLIGATION_AUDIT`, artifact-manifest coverage, and stability
  profile `xml-proof-obligations-added`.
- Real bugs fixed while experimenting: the first probe falsely failed 15
  `runtime_step_recording_boundary` rows because integer counts were compared
  with string CSV values; the check now normalizes both sides with `as_int`.
  The stability profile also had stale draft deltas and now expects the real
  generated counts: 143 rows, 125 PASS, 18 REVIEW_REQUIRED, 0 FAIL.
- Focused probe:
  `python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --out
  test/TARV/results/xml_obligation_probe --tamonitor
  tool/MightyPPL/build/TAMonitor` produced 143 XML obligations, 125 PASS,
  18 REVIEW_REQUIRED, 0 FAIL. Focused `verify_review_packet.py` had 7 expected
  failures because it was not a full pipeline packet and lacked signoff
  validation sidecars; `XML_PROOF_OBLIGATION_AUDIT` itself passed.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_xml_obligations_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_xml_obligations_full --timeout
  30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_evidence_consistency_full_v2
  --stability-profile xml-proof-obligations-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 77879 ms. Packet verifier
  97 PASS/0 FAIL. Stability audit 153 PASS/0 FAIL. Artifact manifest verifier
  14 PASS/0 FAIL with 148 manifest rows. Signoff validation 16 PASS/0 FAIL,
  signoff evidence 47 PASS/0 FAIL, roundtrip audit 7 PASS/0 FAIL.
- Additional QA: workbook `unzip -t` passed; stale timeout phrase scan over the
  latest packet and timeout-rerun packet returned no matches; bundled Node
  syntax check passed for `build_paper_review_workbook.mjs`; whitespace scan
  on changed pipeline scripts found no trailing whitespace; nested MightyPPL
  and MoniTAal `diff --check` commands passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_obligations_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_obligations_full`.

## 2026-07-06 00:20 CST

- Goal: strengthen XML proof-ready review evidence with explicit
  boundary/trace coverage obligations, while preserving the boundary between
  machine-checkable trace prerequisites and human XML-to-MITL equivalence
  approval.
- Work completed: added `xml_trace_coverage_obligations.csv/json/md`, workbook
  sheet `XML Trace Coverage`, packet verifier guard
  `XML_TRACE_COVERAGE_AUDIT`, artifact-manifest coverage, and stability
  profile `xml-trace-coverage-added`.
- Read-only subagent Mill audited the latest XML-obligation packet and
  recommended class-specific trace coverage: response exact-bound/late/re-arm,
  absence closed-bound/safe, eventuality lower-bound/negative, global absence
  inside/boundary/after-bound, recurrence initial/rearmed/timely, and gear
  initial/rearmed/repository-INCONCLUSIVE caveats.
- Real bugs fixed while experimenting: first trace-coverage probe produced
  15 false `runtime_trace_integrity` FAIL rows because `as_int(0, -999)`
  returned the default; `as_int` now only defaults on `None`/empty string.
  `only_ab_until10_negative_boundary.input` was not classified as a closed
  boundary trace because the classifier only matched `boundary_negative`; it
  now also matches `negative_boundary`.
- Focused probe:
  `python3 test/TARV/scripts/run_paper_experiments.py --timeout 30 --out
  test/TARV/results/xml_trace_coverage_probe --tamonitor
  tool/MightyPPL/build/TAMonitor` produced 120 XML trace-coverage obligations,
  84 PASS, 36 REVIEW_REQUIRED, 0 FAIL. Focused packet verification had 7
  expected non-full-pipeline signoff-validation failures; both
  `XML_PROOF_OBLIGATION_AUDIT` and `XML_TRACE_COVERAGE_AUDIT` passed.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_xml_trace_coverage_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_xml_trace_coverage_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_xml_obligations_full --stability-profile
  xml-trace-coverage-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 83556 ms. Packet verifier
  102 PASS/0 FAIL. Stability audit 157 PASS/0 FAIL. Artifact manifest verifier
  15 PASS/0 FAIL with 152 manifest rows. XML trace coverage: 120 rows,
  84 PASS, 36 REVIEW_REQUIRED, 0 FAIL, and 15/15 proof-ready runtime-integrity
  rows PASS.
- Additional QA: workbook `unzip -t` passed; stale timeout phrase scan over the
  latest packet and timeout-rerun packet returned no matches; Python
  `py_compile` passed for changed pipeline scripts; bundled Node syntax check
  passed for `build_paper_review_workbook.mjs`; whitespace scan found no
  trailing whitespace; nested MightyPPL and MoniTAal `diff --check` commands
  passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_trace_coverage_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_trace_coverage_full`.

## 2026-07-06 00:55 CST

- Goal: promote the latest boundary-trace strengthening experiment to the
  official handoff state and verify the packet after context compaction.
- Passing full run already produced:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_xml_boundary_traces_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_xml_boundary_traces_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_xml_trace_coverage_full --stability-profile
  xml-boundary-traces-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 82384 ms. Candidate runs
  54/54 succeeded and matched baseline; baseline runs 58, timeouts 0;
  XML proof obligations 143 rows, 125 PASS, 18 REVIEW_REQUIRED, 0 FAIL;
  XML trace coverage 120 rows, 87 PASS, 33 REVIEW_REQUIRED, 0 FAIL.
- Verification rerun after compaction: `verify_review_packet.py
  --timeout-rerun ...` passed 102 PASS/0 FAIL; artifact manifest verifier
  passed 15 PASS/0 FAIL with 152 manifest rows and no missing/bad hashes;
  workbook `unzip -t` passed; stale timeout phrase scan found 0 matches;
  Python `py_compile`, bundled Node `--check`, and nested MightyPPL/MoniTAal
  `diff --check` all passed.
- Read-only subagent `Linnaeus` independently checked the latest packet and
  timeout rerun directory, confirmed verifier/stability counts, and found no
  stale timeout facts or uncaveated INCONCLUSIVE-as-Boolean proof claim.
- Workflow hazard noted: running `verify_review_packet.py` without
  `--timeout-rerun` writes a 99-check sidecar; rerunning with the timeout-rerun
  path restores the official 102-check sidecar.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_boundary_traces_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_boundary_traces_full`.

## 2026-07-06 01:05 CST

- Goal: fix XML trace-coverage obligations so they respect infinite-word
  three-valued RV semantics, add sound generated evidence, and promote a new
  full passing paper-review packet.
- Read-only subagent `Laplace` confirmed the old coverage requirements were
  theoretical bugs: G*/request-response/absence/recurrence finite prefixes
  should not be forced to `POSITIVE`, and no-witness prefixes of
  `F [lower,infty)` should not be forced to `NEGATIVE`.
- Code changes: `run_paper_experiments.py` now expects INCONCLUSIVE or
  non-violation evidence for those classes, adds c-after no-witness traces,
  a-b re-arm late traces, absence re-arm boundary traces, and recurrence
  timely non-violation traces; `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` add stability profile
  `xml-three-valued-coverage-fixed`.
- Real workbook bug fixed: optional PNG preview rendering caused native
  renderer abort/OOM during full workbook rebuild. `build_paper_review_workbook.mjs`
  now disables previews by default and keeps them opt-in via
  `TAMONITOR_RENDER_WORKBOOK_PREVIEWS=1`; the Excel workbook still contains all
  39 review sheets.
- Failed evidence kept for diagnosis:
  `paper_pipeline_xml_three_valued_coverage_full` failed because workbook
  preview crashed at XML Obligations; `_full_v2` failed because late workbook
  rebuild OOMed after preview rendering. Both failures led to the preview
  robustness fix.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_xml_three_valued_coverage_full_v3
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_xml_three_valued_coverage_full_v3
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_xml_boundary_traces_full --stability-profile
  xml-three-valued-coverage-fixed`.
- Result: pipeline `PASS`, failed steps 0, elapsed 65953 ms. Candidate runs
  62/62 succeeded and matched baseline; baseline runs 66, timeouts 0;
  XML proof obligations 143 rows, 125 PASS, 18 REVIEW_REQUIRED, 0 FAIL;
  XML trace coverage 114 rows, 105 PASS, 9 REVIEW_REQUIRED, 0 FAIL. The
  remaining 9 trace-coverage REVIEW_REQUIRED rows are all
  `original_decisive_trace_boundary` provenance/original-input gaps.
- Verification: packet verifier 102 PASS/0 FAIL; stability audit 157 PASS/0
  FAIL; artifact manifest verifier 15 PASS/0 FAIL with 135 manifest rows;
  workbook `unzip -t` passed; stale timeout phrase scan found 0 matches;
  Python `py_compile`, bundled Node `--check`, and nested MightyPPL/MoniTAal
  `diff --check` all passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_three_valued_coverage_full_v3`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_three_valued_coverage_full_v3`.

## 2026-07-06 01:12 CST

- Goal: check whether the 9 remaining XML trace-coverage
  `original_decisive_trace_boundary` gaps can be closed with real repository
  inputs instead of generated review traces.
- Result: no additional original input was found for `c_after_10.xml`,
  `c_after_20.xml`, or `only_ab_until10.xml`; MoniTAal tests load those XMLs
  as models but do not provide paired timed-word inputs. Gear has the real
  `tool/MoniTAal/benchmark/gear-control-input.txt`, and current baseline
  evidence correctly leaves its proof-ready request/response rows
  INCONCLUSIVE.
- Decision: keep the 9 rows as REVIEW_REQUIRED provenance/original-input gaps.
  Do not relabel generated review traces as original benchmark evidence.

## 2026-07-06 01:05 CST

- Goal: isolate the remaining 9 XML `original_decisive_trace_boundary` provenance gaps into dedicated human-review artifacts without changing TAMonitor/MoniTAal verdict logic.
- Code changes: `run_paper_experiments.py` now writes `xml_original_trace_gaps.csv/json/md`; workbook builder adds `Original Trace Gaps`; packet verifier adds `XML_ORIGINAL_TRACE_GAP_AUDIT`; pipeline artifact manifest verifier checks the new gap artifacts; stability profile `xml-original-trace-gaps-added` is wired into compare/full-pipeline scripts.
- Verification: Python `py_compile` passed for changed pipeline scripts; bundled Node `--check` passed for workbook builder. Focused run `test/TARV/results/xml_original_trace_gaps_probe` completed with 9 gaps, all REVIEW_REQUIRED, 0 FAIL; gap classes are 3 `no_repository_input_found` and 6 `repository_input_inconclusive`. Focused verifier showed `XML_ORIGINAL_TRACE_GAP_AUDIT` PASS; remaining 7 failures are expected because this was not a full pipeline packet with signoff-validation sidecars.
- Next: run the full review pipeline against `paper_pipeline_xml_three_valued_coverage_full_v3` using stability profile `xml-original-trace-gaps-added`, then update the official latest packet if all gates pass.

## 2026-07-06 01:11 CST

- Goal: promote original-trace gap artifacts to a full official paper-review packet and fix any real pipeline bug found during verification.
- Real bug fixed: `run_full_review_pipeline.py` wrote `pipeline_artifact_manifest.*` but did not run `verify_pipeline_artifact_manifest.py`. The script now runs the manifest verifier as a post-manifest sidecar and returns failure if that verifier fails, avoiding self-referential manifest hashing.
- Passing full run: `python3 test/TARV/scripts/run_full_review_pipeline.py --out test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2 --timeout-rerun-out test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gaps_full_v2 --timeout 30 --timeout-rerun-seconds 60 --stability-baseline test/TARV/results/paper_pipeline_xml_three_valued_coverage_full_v3 --stability-profile xml-original-trace-gaps-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 66073 ms. Packet verifier 107 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with 138 manifest rows; stability audit 160 PASS/0 FAIL; workbook zip valid with 40 sheets including `Original Trace Gaps`.
- Experiment counts: XML original trace gaps 9 rows, 9 REVIEW_REQUIRED, 0 FAIL; classes are 3 `no_repository_input_found` and 6 `repository_input_inconclusive`. Candidate runs 62/62 succeeded and matched MoniTAal baseline; baseline runs 66, timeouts 0.
- Additional QA: Python `py_compile` passed for changed scripts; bundled Node `--check` passed for workbook builder; workbook `unzip -t` passed; stale timeout phrase scan excluding verifier/pipeline logs returned no matches; nested MightyPPL and MoniTAal `diff --check` passed.
- Current latest packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2`. Current timeout rerun: `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gaps_full_v2`.

## 2026-07-06 01:27 CST

- Goal: make the 9 XML original trace provenance gaps first-class manual
  review/signoff items instead of only a workbook sheet.
- Code changes: `run_paper_experiments.py` now adds
  `MR_XML_ORIGINAL_TRACE_GAPS`, 9 `XML_ORIGINAL_TRACE_GAP_*` queue rows, and
  matching signoff rows that recommend `APPROVE_WITH_CAVEAT` and forbid
  `APPROVE_AS_CLAIMED`; `validate_review_signoff.py`,
  `build_signoff_evidence_bundle.py`, and `verify_review_packet.py` now
  resolve the new source prefix; `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` add stability profile
  `xml-original-trace-gap-signoff-added`.
- Real bug fixed: `audit_signoff_import_roundtrip.py` still expected 47
  workbook Review Signoff rows during blank XLSX extraction. The packet now has
  57 signoff rows, so the audit now compares against the current generated
  signoff row count.
- Failed run kept for diagnosis:
  `test/TARV/results/paper_pipeline_xml_original_trace_gap_signoff_full`
  failed because the old roundtrip audit hardcoded 47 rows.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_xml_original_trace_gap_signoff_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gap_signoff_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_xml_original_trace_gaps_full_v2
  --stability-profile xml-original-trace-gap-signoff-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 66507 ms. Review packet
  verifier 108 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 180 PASS/0 FAIL; signoff validation
  16 PASS/0 FAIL with 57 blank signoff rows; signoff import roundtrip 7 PASS/0
  FAIL; signoff evidence bundle 57 PASS/0 FAIL.
- Experiment counts: Review Guide 15 rows, Human Review Queue 73 rows,
  Review Signoff 57 rows, Manual Review 17 rows, XML original trace gaps 9
  rows. Candidate runs remain 62/62 matched; baseline runs 66, timeouts 0.
- Additional QA: Python `py_compile`, bundled Node `--check`, workbook
  `unzip -t`, stale timeout phrase scan, and nested MightyPPL/MoniTAal
  `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_xml_original_trace_gap_signoff_full_v2`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_xml_original_trace_gap_signoff_full_v2`.

## 2026-07-06 01:43 CST

- Goal: continue closing automatable XML original-trace evidence gaps without
  relabeling generated review traces as original benchmark evidence.
- Read-only explorer `Chandrasekhar` found one real repository embedded
  timed-word source: `tool/MoniTAal/test/Monitor_test.cpp::intersection_test2`
  parses `models/c_after_10.xml`, feeds `@0 a`, `@5 c`, `@15 c`, `@20 b`,
  and asserts `monitor_c` becomes/remains `POSITIVE`. No sound closer was
  found for `c_after_20.xml`, `only_ab_until10.xml`, or the six gear rows.
- Code changes: `run_paper_experiments.py` now records the c_after_10 unit-test
  timed word as `embedded_benchmark_input`, propagates unresolved original
  trace gaps into `paper_claim_review.csv` via
  `original_trace_gap_boundary`, and makes paper-claim signoff rows with such
  gaps caveat-only. `validate_review_signoff.py` uses the same caveat policy.
  `verify_review_packet.py` adds
  `PAPER_CLAIM_ORIGINAL_TRACE_GAP_CAVEAT_AUDIT`. `compare_pipeline_results.py`
  and `run_full_review_pipeline.py` add stability profile
  `embedded-c-after10-original-trace-added`.
- Focused probe `test/TARV/results/embedded_c_after10_probe` confirmed
  `c_after_10_positive_negative` original_decisive_trace_boundary changed to
  PASS with `original_like=1; decisive_original=1` and candidate/baseline
  verdict `POSITIVE`.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_embedded_c_after10_full --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_embedded_c_after10_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_xml_original_trace_gap_signoff_full_v2
  --stability-profile embedded-c-after10-original-trace-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 74012 ms. Candidate runs
  63/63 matched MoniTAal; baseline runs 67, timeouts 0. XML original trace gaps
  are now 8 rows, all REVIEW_REQUIRED, 0 FAIL: `c_after_20`,
  `only_ab_until10`, and six gear `repository_input_inconclusive` rows.
  Review packet verifier 109 PASS/0 FAIL; artifact manifest verifier
  16 PASS/0 FAIL with 138 manifest rows; stability audit 180 PASS/0 FAIL;
  signoff validation 16 PASS/0 FAIL with 56 blank rows; evidence bundle
  56 PASS/0 FAIL; roundtrip audit 7 PASS/0 FAIL.
- Additional QA: Python `py_compile` passed for changed scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned no matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_embedded_c_after10_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_embedded_c_after10_full`.

## 2026-07-06 01:50 CST

- Goal: make the c_after_10 embedded original-trace closure resistant to
  provenance drift instead of relying only on aggregate PASS counts.
- Code changes: `verify_review_packet.py` now requires and hash-covers
  `monitaal_embedded_benchmarks.csv` and adds
  `EMBEDDED_C_AFTER10_PROVENANCE_AUDIT`; it checks
  `tool/MoniTAal/test/Monitor_test.cpp::intersection_test2`, the exact
  transcribed input `@0 a`, `@5 c`, `@15 c`, `@20 b`, and matching MoniTAal
  baseline/TAMonitor candidate/XML trace-coverage rows. `compare_pipeline_results.py`
  and `run_full_review_pipeline.py` add stability profile
  `embedded-c-after10-provenance-guard-added`.
- Focused probe: `test/TARV/results/embedded_c_after10_provenance_guard_probe`
  produced review packet verifier 112 PASS, 0 WARN, 0 FAIL.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_embedded_c_after10_provenance_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_embedded_c_after10_provenance_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_embedded_c_after10_full
  --stability-profile embedded-c-after10-provenance-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 69354 ms. Review packet
  verifier 112 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 180 PASS/0 FAIL; signoff validation
  16 PASS/0 FAIL with 56 blank rows; evidence bundle 56 PASS/0 FAIL;
  roundtrip audit 7 PASS/0 FAIL. Candidate/baseline remain 63/63 matched,
  baseline runs 67, timeouts 0.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Remaining unresolved original-trace gaps stay at 8:
  `c_after_20_positive_negative`, `only_ab_until10_positive_negative`, and six
  `gear-control-properties.xml` rows whose repository input evidence is
  INCONCLUSIVE. Do not promote generated traces to original evidence.
- Read-only explorer `Dirac` independently rechecked the 8 remaining gaps and
  found no additional repository/embedded timed-word input or status assertion.
  `c_after_20.xml` and `only_ab_until10.xml` only have XML model files copied
  into tests, not paired inputs. Gear has the real `gear-control-input.txt`,
  but MoniTAal baseline and TAMonitor candidate are both `INCONCLUSIVE`, and
  the benchmark code prints verdicts rather than asserting a decisive status.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_embedded_c_after10_provenance_guard_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_embedded_c_after10_provenance_guard_full`.

## 2026-07-06 01:59 CST

- Goal: turn the user's "manual oracle" clarification into a generated review
  protocol so future paper review cannot confuse MoniTAal XML baseline matches
  with hand-derived MITL semantic oracles.
- Code changes: `run_paper_experiments.py` adds
  `MOG_BASELINE_NOT_HAND_ORACLE` to `Manual Oracle Guide`;
  `verify_review_packet.py` requires that row in
  `MANUAL_ORACLE_GUIDE_PROTOCOL`; `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` add stability profile
  `manual-oracle-baseline-boundary-added`.
- Focused probe: `test/TARV/results/manual_oracle_baseline_boundary_probe`
  produced `manual_oracle_guide_rows=10`, `manual_oracle_guide_p0=7`, and the
  new guide row.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_manual_oracle_baseline_boundary_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_manual_oracle_baseline_boundary_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_embedded_c_after10_provenance_guard_full
  --stability-profile manual-oracle-baseline-boundary-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 66993 ms. Manual Oracle
  Guide 10 rows/7 P0; review packet verifier 112 PASS/0 FAIL; artifact
  manifest verifier 16 PASS/0 FAIL with 138 manifest rows; stability audit
  180 PASS/0 FAIL; signoff validation 16 PASS/0 FAIL with 56 blank rows.
  Candidate/baseline remain 63/63 matched, baseline runs 67, timeouts 0, and
  XML original-trace gaps remain 8 REVIEW_REQUIRED/0 FAIL.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_manual_oracle_baseline_boundary_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_manual_oracle_baseline_boundary_full`.

## 2026-07-06 02:05 CST

- Goal: harden the manual-oracle boundary by checking generated candidate
  result rows, not only the guide text.
- Code changes: `verify_review_packet.py` adds
  `BASELINE_MATCH_NOT_HAND_ORACLE_BOUNDARY`, which scans
  `translation_candidate_results.csv` rows with
  `oracle_type=monitaal_xml_baseline_same_input` and requires trace-level,
  non-equivalence caveat wording while forbidding hand/manual-oracle wording.
  `compare_pipeline_results.py` and `run_full_review_pipeline.py` add
  stability profile `baseline-match-oracle-boundary-guard-added`.
- Focused probe:
  `test/TARV/results/baseline_match_oracle_boundary_guard_probe` copied the
  previous packet and produced review packet verifier 113 PASS, 0 WARN, 0
  FAIL; the new guard observed `violations=none`.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_baseline_match_oracle_boundary_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_baseline_match_oracle_boundary_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_manual_oracle_baseline_boundary_full
  --stability-profile baseline-match-oracle-boundary-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 68925 ms. Review packet
  verifier 113 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 180 PASS/0 FAIL with expected verifier
  delta +1; signoff validation 16 PASS/0 FAIL with 56 blank rows.
  Candidate/baseline remain 63/63 matched, baseline runs 67, timeouts 0, and
  XML original-trace gaps remain 8 REVIEW_REQUIRED/0 FAIL.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_baseline_match_oracle_boundary_guard_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_baseline_match_oracle_boundary_guard_full`.

## 2026-07-06 02:15 CST

- Goal: harden the Excel/manual-review packet by auditing the generated
  workbook preview manifest rather than merely producing it.
- Code changes: `verify_review_packet.py` now requires
  `workbook_preview_manifest.csv/json` and adds
  `WORKBOOK_PREVIEW_MANIFEST_AUDIT`; the audit checks CSV/JSON equality,
  workbook sheet coverage, required review sheets, source CSV existence,
  source CSV row/column shape, and preview status/path consistency.
  `compare_pipeline_results.py` and `run_full_review_pipeline.py` add
  stability profile `workbook-preview-manifest-guard-added`.
- Focused probe: `test/TARV/results/workbook_preview_manifest_guard_probe`
  copied the previous packet and produced review packet verifier 116 PASS,
  0 WARN, 0 FAIL; `WORKBOOK_PREVIEW_MANIFEST_AUDIT` observed
  `violations=none`. Focused stability comparison against the previous
  official packet produced 180 PASS, 0 WARN, 0 FAIL with expected verifier
  delta +3.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_workbook_preview_manifest_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_workbook_preview_manifest_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_baseline_match_oracle_boundary_guard_full
  --stability-profile workbook-preview-manifest-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 70450 ms. Review packet
  verifier 116 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 180 PASS/0 FAIL with expected verifier
  delta +3. Candidate/baseline remain 63/63 matched, baseline runs 67,
  timeouts 0, and XML original-trace gaps remain 8 REVIEW_REQUIRED/0 FAIL.
  Workbook preview manifest has 40 rows, all skipped by the OOM-safe preview
  policy, with no sheet/source CSV shape violations.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_workbook_preview_manifest_guard_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_workbook_preview_manifest_guard_full`.

## 2026-07-06 02:25 CST

- Goal: harden the final workbook rebuild evidence so late sidecars cannot be
  generated but silently omitted or drift away from the manual-review workbook.
- Code changes: `verify_review_packet.py` now requires
  `workbook_rebuild_summary.csv/json/md` and adds
  `WORKBOOK_REBUILD_SUMMARY_AUDIT`; it checks rebuild summary status, summary
  path consistency, final workbook path evidence, benchmark-blocker and
  hardcoded benchmark late sheets, and timeout-rerun copied CSV/sheet evidence.
  `compare_pipeline_results.py` and `run_full_review_pipeline.py` add
  stability profile `workbook-rebuild-summary-guard-added`.
- Bug exposed and fixed: the first full rerun failed because
  `audit_signoff_import_roundtrip.py` copied packets into `/tmp` but kept stale
  `experiment_summary.output_dir/workbook_path`, so complete-mode packet
  verification failed the new rebuild-summary guard. Added
  `sync_copied_packet_summary_paths()` to rewrite the temporary packet summary
  before synthetic import/rebuild/verification. Focused rerun of
  `audit_signoff_import_roundtrip.py` then produced 7 PASS/0 FAIL with
  `imported_nonblank_decisions=56`.
- Focused probe: `test/TARV/results/workbook_rebuild_summary_guard_probe`
  copied the previous packet and produced review packet verifier 120 PASS,
  0 WARN, 0 FAIL; `WORKBOOK_REBUILD_SUMMARY_AUDIT` observed
  `violations=none`. Focused stability comparison against the previous
  official packet produced 180 PASS, 0 WARN, 0 FAIL with expected verifier
  delta +4.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_workbook_rebuild_summary_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_workbook_rebuild_summary_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_workbook_preview_manifest_guard_full
  --stability-profile workbook-rebuild-summary-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 66898 ms. Review packet
  verifier 120 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 180 PASS/0 FAIL with expected verifier
  delta +4. Candidate/baseline remain 63/63 matched, baseline runs 67,
  timeouts 0, candidate prefix observations 123028 rows, and XML original-trace
  gaps remain 8 REVIEW_REQUIRED/0 FAIL.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Read-only explorer `Darwin` found the next automatable guard candidate:
  `candidate_prefix_observations.csv` raw prefix evidence is generated, hashed,
  and cited by manual review, but packet verification currently mostly gives it
  public-verdict scanning rather than row/step coverage checks. Suggested next
  guard: `CANDIDATE_PREFIX_OBSERVATIONS_AUDIT`, mechanically checking raw row
  count, carry-forward count, per-candidate step coverage, and linked
  `steps_path` files without changing MITL/RV semantics.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_workbook_rebuild_summary_guard_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_workbook_rebuild_summary_guard_full`.

## 2026-07-06 02:38 CST

- Goal: make the raw per-prefix candidate runtime evidence a first-class
  packet-verifier target instead of only a generated/hash-covered CSV.
- Code changes: `verify_review_packet.py` now requires
  `candidate_prefix_observations.csv` and `candidate_step_audit.csv`, adds
  `CANDIDATE_PREFIX_OBSERVATIONS_AUDIT`, and resolves copied-packet artifact
  paths back to local `translation_candidate_runs/*/steps.csv` when needed.
  The audit checks raw prefix row counts, carry-forward counts, candidate/step
  ID alignment, per-candidate mapped/processed/observed step counts, final
  prefix verdicts, and row-by-row consistency with each run's `steps.csv`.
  `compare_pipeline_results.py` adds `candidate_prefix_observations.csv` row
  count stability and profile `candidate-prefix-observations-guard-added`;
  `run_full_review_pipeline.py` accepts that profile.
- Focused probe: `test/TARV/results/candidate_prefix_observations_guard_probe`
  copied the previous packet and produced review packet verifier 123 PASS,
  0 WARN, 0 FAIL; `CANDIDATE_PREFIX_OBSERVATIONS_AUDIT` observed
  `violations=none`. Focused stability comparison against the previous
  official packet produced 181 PASS, 0 WARN, 0 FAIL with expected verifier
  delta +3.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_candidate_prefix_observations_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_workbook_rebuild_summary_guard_full
  --stability-profile candidate-prefix-observations-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 71977 ms. Review packet
  verifier 123 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 181 PASS/0 FAIL with expected verifier
  delta +3. Candidate/baseline remain 63/63 matched, baseline runs 67,
  timeouts 0, candidate prefix observations 123028 rows, carry-forward rows
  29989, and XML original-trace gaps remain 8 REVIEW_REQUIRED/0 FAIL.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches; nested MightyPPL and MoniTAal
  `diff --check` passed.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_candidate_prefix_observations_guard_full`.

## 2026-07-06 02:58 CST

- Goal: make MoniTAal XML transition/proof ledger evidence first-class packet
  verifier material without claiming automatic XML-to-MITL semantic equivalence.
- Code changes: `verify_review_packet.py` now requires `benchmark_manifest.csv`,
  `monitaal_xml_inventory.csv`, `monitaal_translation_review.csv`,
  `monitaal_transition_details.csv`, `xml_edge_guard_proofs.csv`, and
  `xml_proof_appendix.csv`; it adds `MONITAAL_XML_STRUCTURAL_LEDGER_AUDIT`
  checking summary counts, inventory-to-transition counts, paired/unpaired
  transition metadata, manifest/proof/appendix ID closure, edge evidence
  transition refs, trace evidence paths, proof status counts, and appendix
  status mapping. `compare_pipeline_results.py` adds CSV stability coverage for
  the XML ledger files and profile `monitaal-xml-structural-ledger-guard-added`;
  `run_full_review_pipeline.py` accepts that profile.
- Bugs exposed and fixed: the first focused verifier failed because the guard
  incorrectly expected `translation_reason` to be identical between manifest
  and edge-proof rows; that field is not part of the edge-proof schema, so the
  guard now only compares intended shared identity/status fields. The first
  focused stability comparison was interrupted after exposing a performance bug:
  CSV normalization called `Path.resolve()` per cell; path replacements are now
  precomputed once per comparison.
- Focused probe: `test/TARV/results/monitaal_xml_structural_ledger_guard_probe`
  copied the previous packet and produced review packet verifier 130 PASS,
  0 WARN, 0 FAIL; `MONITAAL_XML_STRUCTURAL_LEDGER_AUDIT` observed
  `violations=none`. Focused stability comparison against the previous
  official packet produced 205 PASS, 0 WARN, 0 FAIL with expected verifier
  delta +7.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_monitaal_xml_structural_ledger_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_monitaal_xml_structural_ledger_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_candidate_prefix_observations_guard_full
  --stability-profile monitaal-xml-structural-ledger-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 73853 ms. Review packet
  verifier 130 PASS/0 FAIL; artifact manifest verifier 16 PASS/0 FAIL with
  138 manifest rows; stability audit 205 PASS/0 FAIL with expected verifier
  delta +7. XML structural ledger has 60 templates, 386 transition-detail rows,
  23 manifest/proof/appendix rows, 15 proof-ready rows, and 8 excluded/not-ready
  rows. Candidate/baseline remain 63/63 matched, baseline runs 67, timeouts 0,
  candidate prefix observations 123028 rows, and XML original-trace gaps remain
  8 REVIEW_REQUIRED/0 FAIL.
- QA: Python `py_compile` passed for changed Python scripts; bundled Node
  `--check` passed for workbook builder; workbook `unzip -t` passed; stale
  timeout phrase scan returned 0 matches (`rg` exit 1); nested MightyPPL and
  MoniTAal `diff --check` passed.
- Handoff: archived the previous 249-line `PROJECT_STATE.md` as
  `.codex/archive/PROJECT_STATE_20260706_pre_monitaal_xml_structural_ledger_guard.md`
  and replaced the active state file with a compact latest-packet handoff.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_monitaal_xml_structural_ledger_guard_full`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_monitaal_xml_structural_ledger_guard_full`.

## 2026-07-06 16:23 CST

- User asked for the complete MITL formula directory used for verification and
  testing.
- Generated review catalogs from the latest passing official packet
  `paper_pipeline_monitaal_xml_structural_ledger_guard_full`:
  `mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`, and
  `mitl_formula_catalog_runtime_runs.csv` under `test/TARV/results/`.
- Catalog excludes internal compiler forms such as CFn/CGn from the MITL
  formula list; those remain only in input-policy rejection checks.

## 2026-07-06 16:33 CST

- Goal: harden the human-review entrypoint evidence so review guide / goal
  audit / manual checklist / requirements audit references resolve to real
  packet artifacts, workbook sheets, repo files, or explicit globs.
- Code changes: `verify_review_packet.py` adds
  `MANUAL_REVIEW_ENTRYPOINT_REFERENCES`; `run_paper_experiments.py` now writes
  resolved review evidence tokens and retries only transient WSL `node.exe`
  workbook launch failures; `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` support profile
  `manual-review-entrypoint-reference-guard-added`.
- Bugs exposed and fixed: the first full run failed because workbook generation
  hit transient `UtilBindVsockAnyPort/socket failed`; retrying the narrow WSL
  launch failure fixed it. The next full run exposed a synthetic complete-mode
  signoff roundtrip self-reference: the new review guide cited
  `signoff_import_roundtrip_audit.*` before that audit file existed inside the
  temporary packet copy. `verify_review_packet.py` now exempts only those
  roundtrip self-reference tokens during `--signoff-mode complete`; normal
  pre-review packet verification still requires them.
- Focused checks: `py_compile` passed; standalone workbook rebuild on the
  failed packet succeeded; focused signoff roundtrip audit produced 7 PASS,
  0 WARN, 0 FAIL.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_manual_review_entrypoint_reference_guard_full_v3
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_manual_review_entrypoint_reference_guard_full_v3
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_monitaal_xml_structural_ledger_guard_full
  --stability-profile manual-review-entrypoint-reference-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 80181 ms. Review packet
  verifier 136 PASS/0 FAIL, including `MANUAL_REVIEW_ENTRYPOINT_REFERENCES`;
  artifact manifest verifier 16 PASS/0 FAIL; stability audit 189 PASS/0 FAIL
  with expected verifier delta +6. Signoff validation 16 PASS/0 FAIL, signoff
  evidence bundle 56 PASS/0 FAIL, synthetic signoff roundtrip 7 PASS/0 FAIL.
  Candidate/baseline remain 63/63 matched; baseline runs 67, timeouts 0; XML
  original-trace gaps remain 8 REVIEW_REQUIRED/0 FAIL.
- QA: bundled Node `--check` passed for the workbook builder; workbook
  `unzip -t` passed; stale timeout phrase scan returned no matches (`rg` exit
  1); nested MightyPPL and MoniTAal `diff --check` passed. Formula catalogs in
  `test/TARV/results/mitl_formula_catalog_*` were regenerated to point at the
  v3 packet.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_manual_review_entrypoint_reference_guard_full_v3`.
  Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_manual_review_entrypoint_reference_guard_full_v3`.

## 2026-07-06 16:58 CST

- Goal: make the six gear-control original-input gaps reviewable with machine
  evidence without incorrectly closing them as decisive POSITIVE/NEGATIVE
  original timed-word evidence.
- Subagent evidence: Rawls checked the 8 original-trace gaps read-only. The two
  small XML rows still have no real original input; six gear rows have
  repository input `tool/MoniTAal/benchmark/gear-control-input.txt`, but
  MoniTAal baseline verdicts are all `INCONCLUSIVE`, so they cannot be closed.
- Code changes: `run_paper_experiments.py` now writes
  `gear_original_input_response_audit.csv/json/md`, parses MoniTAal `@time`
  inputs preserving same-timestamp event order, computes trigger/response
  finite-prefix counts from `xml_edge_guard_proofs.csv`, and links gear gap
  evidence to the new audit. `build_paper_review_workbook.mjs` adds sheet
  `Gear Original Audit`. `verify_review_packet.py` requires the new artifacts
  and adds guard `GEAR_ORIGINAL_INPUT_RESPONSE_AUDIT`. `compare_pipeline_results.py`
  and `run_full_review_pipeline.py` add profile
  `gear-original-input-response-audit-added`.
- Bugs exposed and fixed: first full gear-audit run produced a passing packet
  verifier but failed stability because `Gear Original Audit` was not allowed
  as an added workbook sheet for the new profile. The profile now explicitly
  expects that sheet.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_gear_original_input_response_audit_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_gear_original_input_response_audit_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_manual_review_entrypoint_reference_guard_full_v3
  --stability-profile gear-original-input-response-audit-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 75892 ms. Review packet
  verifier 141 PASS/0 FAIL, including `GEAR_ORIGINAL_INPUT_RESPONSE_AUDIT`.
  Stability audit 189 PASS/0 FAIL with expected repro delta +3 and verifier
  delta +5. Artifact manifest verifier 16 PASS/0 FAIL with 141 manifest rows.
  Candidate/baseline remain 63/63 matched; baseline runs 67, timeouts 0; XML
  original trace gaps remain 8 REVIEW_REQUIRED/0 FAIL.
- Gear audit: 6 rows, 0 late-response rows, 2 pending-trigger rows, 0 expired
  rows. CloseClutch 642/642, OpenClutch 643/643, ReqNeu 793/793, SpeedSet
  252/252, ReqSet 793/794 with 1 pending, test1 541/542 with 1 pending; all
  original baseline verdicts are `INCONCLUSIVE`.
- QA: `py_compile` passed; bundled Node `--check` passed for workbook builder;
  v2 workbook `unzip -t` passed; stale timeout scan excluding verifier/pipeline
  summary found no matches (`rg` exit 1); nested MightyPPL and MoniTAal
  `diff --check` passed. Formula catalogs in `test/TARV/results/mitl_formula_catalog_*`
  were regenerated to point at the v2 packet.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_gear_original_input_response_audit_full_v2`.
- Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_gear_original_input_response_audit_full_v2`.

## 2026-07-06 17:09 CST

- Goal: make the remaining two non-gear XML original-trace gaps auditable
  without pretending generated review inputs are original MoniTAal benchmark
  traces.
- Code changes: `run_paper_experiments.py` now writes
  `non_gear_original_input_search_audit.csv/json/md` for non-gear
  `no_repository_input_found` rows; the audit checks same-stem repository files,
  sibling input files, baseline provenance, generated review inputs, and CMake
  XML references. `build_paper_review_workbook.mjs` adds sheet
  `Non-Gear Input Search`. `verify_review_packet.py` requires the new artifacts
  and adds guard `NON_GEAR_ORIGINAL_INPUT_SEARCH_AUDIT`.
  `compare_pipeline_results.py` and `run_full_review_pipeline.py` add profile
  `non-gear-original-input-search-audit-added`.
- Bugs exposed and fixed: the first non-gear audit run failed packet
  verification because the new boundary-text guard was accidentally
  case-sensitive (`Generated review traces...`). The verifier now checks the
  intended generated-vs-original boundary case-insensitively.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_non_gear_original_input_search_audit_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_non_gear_original_input_search_audit_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_gear_original_input_response_audit_full_v2
  --stability-profile non-gear-original-input-search-audit-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 74572 ms. Review packet
  verifier 146 PASS/0 FAIL including
  `NON_GEAR_ORIGINAL_INPUT_SEARCH_AUDIT`; stability audit 189 PASS/0 FAIL with
  expected added workbook sheet `Non-Gear Input Search`; candidate/baseline
  remain 63/63 matched; baseline runs 67, timeouts 0.
- Non-gear original input search audit: 2 rows. `c_after_20.xml` and
  `only_ab_until10.xml` are both `NO_ORIGINAL_TIMED_WORD_FOUND`; original-like
  baseline count 0, generated review input count 3 each, repository same-stem
  file count 1 each, non-XML same-stem repository file count 0 each.
- Formula catalogs were regenerated to point at the new v2 packet:
  `test/TARV/results/mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`, and
  `mitl_formula_catalog_runtime_runs.csv`. Counts: 87 semantic rows, 23 XML
  manifest rows, 19 non-empty XML candidates, 150 runtime rows.
- QA: `py_compile` passed; bundled Node `--check` passed; workbook `unzip -t`
  passed; stale timeout phrase scan excluding verifier/pipeline summary found
  no matches; formula catalog path check found no references to the previous
  gear-audit packet.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_non_gear_original_input_search_audit_full_v2`.
- Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_non_gear_original_input_search_audit_full_v2`.

## 2026-07-06 17:36 CST

- Goal: harden the paper-review workbook so human reviewers do not inspect an
  Excel sheet that is silently bound to the wrong CSV or missing a summary row
  count.
- Code changes: `verify_review_packet.py` now has
  `WORKBOOK_SOURCE_COVERAGE_AUDIT` and a `WORKBOOK_SHEET_SOURCE_SPECS` contract
  for review sheet/source-CSV bindings. `run_paper_experiments.py` now writes
  `mitl_correctness_audit_rows = 150` in `experiment_summary.json`.
  `mitl_correctness_audit.csv` is now required, hash-covered, and checked by
  `CSV_COUNT_mitl_correctness_audit_csv`. `compare_pipeline_results.py` and
  `run_full_review_pipeline.py` add profiles
  `workbook-source-coverage-guard-added` and
  `correctness-audit-rowcount-guard-added`.
- Evidence: a full workbook-source-coverage run passed:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_workbook_source_coverage_guard_full`.
  Then the stricter correctness-rowcount guard intentionally made the older
  workbook-source packet fail two verifier checks because it lacked
  `mitl_correctness_audit_rows`: `WORKBOOK_SOURCE_COVERAGE_AUDIT` and
  `CSV_COUNT_mitl_correctness_audit_csv`.
- Bugs/risks exposed and handled: the first correctness-rowcount full run used
  the mutated workbook-source probe directory as stability baseline, so stability
  failed for the wrong reason. The passing v2 run uses the previous official
  non-gear packet as the baseline.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_correctness_audit_rowcount_guard_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_correctness_audit_rowcount_guard_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_non_gear_original_input_search_audit_full_v2
  --stability-profile correctness-audit-rowcount-guard-added`.
- Result: pipeline `PASS`, failed steps 0, elapsed 83027 ms. Review packet
  verifier 149 PASS/0 FAIL. Stability audit 212 PASS/0 FAIL with expected
  verifier delta +2. `Correctness Audit` maps to `mitl_correctness_audit.csv`;
  workbook manifest rowCount is 151 including header, and
  `CSV_COUNT_mitl_correctness_audit_csv` reports rows=150/summary=150.
- QA: py_compile passed in full pipeline; bundled Node `--check` passed for the
  workbook builder; workbook `unzip -t` passed; stale timeout phrase scan found
  no matches; nested MightyPPL and MoniTAal `diff --check` passed.
- Formula catalogs were regenerated to point at the new v2 packet:
  `test/TARV/results/mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`, and
  `mitl_formula_catalog_runtime_runs.csv`. Counts remain 87 semantic rows,
  23 XML manifest rows, 19 non-empty XML candidates, and 150 runtime rows.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_correctness_audit_rowcount_guard_full_v2`.
- Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_correctness_audit_rowcount_guard_full_v2`.

## 2026-07-06 17:48 CST

- Goal: harden the paper-review Excel workbook against a subtler failure mode:
  the visible workbook exists and the preview manifest says row counts are
  correct, but the real `.xlsx` table ranges inside the zip could still point at
  the wrong dimensions.
- Code changes: `verify_review_packet.py` now parses `.xlsx` internals directly:
  workbook relationships, worksheet relationships, table XML files, and table
  `ref` ranges such as `A1:S151`. It adds
  `WORKBOOK_XLSX_TABLE_SHAPE_AUDIT` to compare real table dimensions against
  `workbook_preview_manifest.csv` and source CSV shapes. `compare_pipeline_results.py`
  and `run_full_review_pipeline.py` add profile
  `workbook-xlsx-table-shape-guard-added`.
- Bug/risk exposed and handled: after a focused verifier probe, the previous
  official packet was already mutated from 149 to 150 verifier checks, so the
  first full xlsx-shape run failed stability because the delta profile expected
  +1. The final official run used `--stability-profile stable` against that
  already-probed baseline; this confirms no semantic/runtime/benchmark drift.
- Passing full run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_workbook_xlsx_table_shape_guard_full_v2
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_workbook_xlsx_table_shape_guard_full_v2
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_correctness_audit_rowcount_guard_full_v2
  --stability-profile stable`.
- Result: pipeline `PASS`, failed steps 0, elapsed 80647 ms. Review packet
  verifier 150 PASS/0 FAIL including
  `WORKBOOK_XLSX_TABLE_SHAPE_AUDIT`; stability audit 212 PASS/0 FAIL. Semantic
  regression remains 87 cases with 70 runtime-verified verdict checks and
  0 fail/error/timeout. Candidate/baseline remain 63/63 matched; baseline runs
  67, timeouts 0.
- QA: `py_compile` passed for changed Python scripts; bundled Node `--check`
  passed for workbook builder; workbook `unzip -t` passed; xlsx-shape spot check
  reported `violations=none`; stale timeout phrase scan found no matches;
  nested MightyPPL and MoniTAal `diff --check` passed.
- Formula catalogs were updated to point at the new v2 packet:
  `test/TARV/results/mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`, and
  `mitl_formula_catalog_runtime_runs.csv`. Counts remain 87 semantic rows,
  23 XML manifest rows, and 150 runtime rows.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_workbook_xlsx_table_shape_guard_full_v2`.
- Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_workbook_xlsx_table_shape_guard_full_v2`.

## 2026-07-06 18:06 CST

- User challenged whether the current work was drifting into experiment
  packaging instead of core TAMonitor algorithm capability. Answer: yes, the
  just-started workbook-tamper negative regression was an experiment-integrity
  guard, not a core runtime-verification algorithm implementation.
- Action taken: stopped that side branch and removed the half-integrated
  `audit_workbook_xlsx_tamper.py` script plus all `workbook_xlsx_tamper`
  references from `run_full_review_pipeline.py`, `verify_review_packet.py`,
  `verify_pipeline_artifact_manifest.py`, and `compare_pipeline_results.py`.
- Verification: `python3 -m py_compile` passed for those four pipeline scripts;
  `rg` found no remaining tamper-audit references; re-running
  `verify_review_packet.py` on the latest official packet with the timeout
  rerun directory still produced `fail: 0`.
- Current clarification for future work: do not claim all algorithmic functions
  are complete. v1 flatten + BDD-label projection + MoniTAal positive/negative
  runtime monitor has evidence. BDD-native runtime remains interface/metadata
  only, compflatten runtime verdicts remain unsupported, XML-to-MITL proof rows
  still need human review, and human `Review Signoff` is blank.
- Next focus: core algorithm capability audit/implementation rather than more
  experiment-packaging guards.

## 2026-07-06 20:14 CST

- Milestone: put the MITL formula catalogs directly into the paper-review
  workbook so human reviewers can inspect formulas from the main Excel file,
  not only from sidecar CSV/Markdown files.
- Code changes: `test/TARV/scripts/build_paper_review_workbook.mjs` now adds
  optional sheets `MITL Semantic Catalog`, `MITL XML Candidates`, and
  `MITL Runtime Catalog`. `test/TARV/scripts/run_full_review_pipeline.py` now
  runs `build_mitl_formula_catalog` before the final workbook rebuild, so the
  sheets are present in `paper_review_results.xlsx`. The
  `formula-catalog-integrated` stability profile in
  `test/TARV/scripts/compare_pipeline_results.py` now treats those three
  workbook sheets as expected additions while keeping semantic/runtime and
  benchmark evidence stable.
- Verification: `python3 -m py_compile
  test/TARV/scripts/run_full_review_pipeline.py
  test/TARV/scripts/compare_pipeline_results.py` passed. Full stability-backed
  pipeline command:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_formula_catalog_workbook_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_workbook_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_cli_trace_header_contract_full
  --stability-profile formula-catalog-integrated`.
- Result: pipeline PASS/full, failed steps 0, elapsed 80375 ms. Semantic
  regression remained 87 cases/70 runtime verified/0 fail/error/timeout.
  Candidate/baseline remained 63/63 matched with baseline timeouts 0. Review
  verifier 150 PASS/0 FAIL. Artifact manifest verifier 16 PASS/0 FAIL with
  151 manifest rows. Stability audit 190 PASS/0 FAIL. Formula catalog counts:
  87 semantic rows, 23 XML rows, and 150 runtime rows. Workbook `unzip -t`
  passed.
- Workbook sheet evidence: `paper_review_results.xlsx` has 45 sheets total,
  including `MITL Semantic Catalog` with 88 rows including header,
  `MITL XML Candidates` with 24 rows including header, and
  `MITL Runtime Catalog` with 151 rows including header. Latest global MITL
  formula catalog entrypoints now point to
  `paper_pipeline_formula_catalog_workbook_full`.
- Next: continue XML-to-MITL equivalence/manual Review Signoff preparation; do
  not implement or claim BDD-native runtime or compflatten runtime in v1.

## 2026-07-06 20:08 CST

- Milestone: made the formula-catalog integrated packet stability-backed.
- Code changes: added stability profile `formula-catalog-integrated` to
  `test/TARV/scripts/compare_pipeline_results.py` and
  `test/TARV/scripts/run_full_review_pipeline.py`. The profile permits only
  the expected reproducibility growth from the new formula-catalog generator:
  `reproducibility_manifest_rows +1`, `reproducibility_source_hashes +1`,
  `reproducibility_result_hashes +0`, and `reproducibility_git_rows +0`.
- Verification: `python3 -m py_compile
  test/TARV/scripts/compare_pipeline_results.py
  test/TARV/scripts/run_full_review_pipeline.py` passed. Direct compare from
  `paper_pipeline_cli_trace_header_contract_full` to
  `paper_pipeline_formula_catalog_integrated_full` with profile
  `formula-catalog-integrated` produced 190 PASS/0 WARN/0 FAIL.
- Full stability-backed run:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_formula_catalog_stability_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_stability_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_cli_trace_header_contract_full
  --stability-profile formula-catalog-integrated`.
- Result: pipeline PASS/full, failed steps 0, elapsed 78981 ms. Semantic
  regression remained 87 cases/70 runtime verified/0 fail/error/timeout.
  Candidate/baseline remained 63/63 matched with baseline timeouts 0. Review
  verifier 150 PASS/0 FAIL. Artifact manifest verifier 16 PASS/0 FAIL with
  151 manifest rows. Stability audit 190 PASS/0 FAIL. Formula catalog counts:
  87 semantic rows, 23 XML rows, and 150 runtime rows. Workbook `unzip -t`
  passed. Latest global MITL formula catalog entrypoints now point to this
  stability-backed packet.
- Next: continue XML-to-MITL equivalence/manual Review Signoff preparation; do
  not implement or claim BDD-native runtime or compflatten runtime in v1.

## 2026-07-06 20:03 CST

- Milestone: ran the first full paper-review pipeline with the integrated
  packet-local MITL formula catalog step.
- Command:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_formula_catalog_integrated_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_integrated_full
  --timeout 30 --timeout-rerun-seconds 60`.
- Result: pipeline `PASS`, full mode, failed steps 0, elapsed 78135 ms.
  Semantic regression stayed at 87 cases, 70 runtime verified, 0
  fail/error/timeout. Candidate/baseline stayed at 63/63 matches, baseline
  timeouts 0. Review packet verifier reported 150 PASS/0 WARN/0 FAIL.
  Artifact manifest verifier reported 16 PASS/0 WARN/0 FAIL and 146 manifest
  rows. Workbook `unzip -t` passed.
- Formula catalog evidence: the new pipeline command
  `build_mitl_formula_catalog` ran successfully inside the packet and produced
  packet-local `mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`,
  `mitl_formula_catalog_runtime_runs.csv`, and
  `mitl_formula_catalog_summary.json`. Counts: 87 semantic rows, 23 XML rows,
  19 non-empty XML MITL candidates, 17 unique XML candidate formulas, and 150
  runtime rows. The pipeline artifact manifest hashes all five catalog files
  plus the formula-catalog command logs.
- Latest global formula catalog entrypoints in `test/TARV/results/` were synced
  to this new packet. This full run did not include a stability-baseline
  comparison; the previous stability-backed packet remains
  `paper_pipeline_cli_trace_header_contract_full`.
- Next: continue core/manual-review work; only add a formula-catalog stability
  profile if another stability-backed official packet is required.

## 2026-07-06 20:00 CST

- Milestone: made the MITL formula catalog reproducible instead of relying on
  hand-synced latest-official files.
- Code changes: `test/TARV/scripts/run_full_review_pipeline.py` now includes
  `build_mitl_formula_catalog.py` in Python syntax preflight, exposes
  `--formula-catalog-timeout` and `--skip-formula-catalog`, runs
  `build_mitl_formula_catalog` after the main packet/workbook artifacts are
  produced, and advertises packet-local MITL catalog artifacts in the pipeline
  summary when present.
- Verification: `python3 -m py_compile
  test/TARV/scripts/build_mitl_formula_catalog.py
  test/TARV/scripts/run_full_review_pipeline.py` passed. Running
  `build_mitl_formula_catalog.py` against
  `test/TARV/results/paper_pipeline_cli_trace_header_contract_full` produced
  87 semantic rows, 23 XML rows, 19 non-empty XML MITL candidates, 17 unique
  XML candidate formulas, and 150 runtime rows. Latest-official catalog files
  were regenerated through the script, row counts are 87/23/150, and no old
  `paper_pipeline_workbook_xlsx_table_shape_guard_full_v2` reference remains
  in the latest catalog entrypoints.
- Subagent note: a read-only formula-catalog explorer was spawned but did not
  finish within the short wait window and was closed; no subagent conclusion
  was used.
- Next: the next full paper pipeline run should use the integrated formula
  catalog step and then confirm packet-local `mitl_formula_catalog_*` artifacts
  are present in the final review packet.

## 2026-07-06 19:56 CST

- User clarified again that the current target must not implement BDD-native
  runtime or `compflatten` runtime verification; both should remain reserved
  interfaces for v1.
- Scope verification: `TAMonitor --help` states that `compflatten` is
  construction/statistics-only; `--build-mode compflatten` without
  `--build-only` returned controlled `unsupported_runtime_mode`; `--build-mode
  compflatten --build-only` returned `NOT_CHECKED_COMPFLATTEN_BUILD_ONLY` and
  `NOT_RUN_BUILD_ONLY` with construction statistics; `--emit-bdd-interface`
  produced `bdd_interface.json` with `interface_reserved_not_implemented`.
- Code result: no source patch needed for this clarification; current
  implementation already enforces the v1 boundary at CLI, adapter, report, and
  experiment-audit levels.
- Next: continue only on the evidence-backed v1 runtime path
  `flatten + BDD-label canonical projection + MoniTAal positive/negative
  monitor`, plus reproducible manual-review artifacts.

## 2026-07-06 18:27 CST

- User asked whether all non-experiment algorithm functions are already fully
  implemented and verified correct. Answer recorded for continuity: no.
  Evidence-backed v1 scope is flatten TA construction + BDD-label projection +
  MoniTAal positive/negative runtime monitoring. BDD-native runtime remains
  interface/metadata only; composition-aware compflatten runtime verdicts are
  not implemented.
- Core fix: moved the `compflatten` runtime rejection down into
  `src/TAMonitor/TAMonitorMightyAdapter.cpp::build_automata_pair`, not just
  `TAMonitorMain.cpp`, so direct library callers cannot bypass the CLI guard
  and accidentally get an unsupported runtime-verdict path. Updated the CLI
  error/help wording to say compflatten is construction/statistics-only in v1.
- Verification: `cmake --build tool/MightyPPL/build --target TAMonitor -j2`
  passed. `TAMonitor --build-mode flatten --word finite` on `F [0,2] p1` with
  `test/TARV/cases/smoke_f_01.trace` returned SAT/final POSITIVE and two
  report rows. `--build-mode compflatten` without `--build-only` returned
  controlled `unsupported_runtime_mode`. `--build-mode compflatten
  --build-only` returned `NOT_CHECKED_COMPFLATTEN_BUILD_ONLY` and
  `NOT_RUN_BUILD_ONLY` with component/location/edge/clock statistics.
- Next core step: inspect whether BDD-native runtime should remain a reserved
  interface or can be implemented incrementally without violating MightyPPL BDD
  semantics; do not claim compflatten runtime correctness until a real
  composition-aware monitor exists.

## 2026-07-06 18:49 CST

- Goal: continue core TAMonitor capability work, focusing on the BDD projection
  and trace-input layer that feeds the verified flatten runtime path.
- Bug reproduced: a trace file with a plain CSV header
  `time,props\n0,{}\n1,{p1}\n` failed with a bare `stoul` diagnostic, so the
  user-requested `time,props` trace shape was not robustly supported.
- Code changes:
  `src/TAMonitor/TraceParser.cpp` now skips `time,props` and `time,bits`
  header rows, validates point and interval times with controlled diagnostics,
  checks interval ordering, and checks the `uint32_t` MoniTAal time range.
  `tool/MightyPPL/TAwithBDDEdges.cpp` now clears
  `mightypplcpp::sat_paths` immediately before each BDD `allsat` projection
  call to prevent stale global patterns from contaminating canonical labels if
  future build paths change. `test/TARV/scripts/run_paper_experiments.py` now
  adds CLI contract case `cli_trace_csv_header_time_props`.
- Verification: initial sandboxed build failed because CMake tried the
  antlr4_runtime remote update and network was blocked. The approved re-run
  `cmake --build tool/MightyPPL/build --target TAMonitor -j2` passed and
  rebuilt `TraceParser.cpp` and `TAwithBDDEdges.cpp`. `python3 -m py_compile
  test/TARV/scripts/run_paper_experiments.py` passed.
- Runtime checks: header trace now returns SAT/final POSITIVE with
  `events=2` and `processed_steps=2`; bad time `0abc` now returns controlled
  `Invalid time value in trace: 0abc`; `--max-valuations 1` still returns
  controlled `BDD projection valuation limit exceeded`; focused
  `build_cli_contract_audit(...)` produced 11 rows, 0 failures, and header case
  PASS. `git -C tool/MightyPPL diff --check` passed.
- Handoff maintenance: `.codex/PROJECT_STATE.md` was at 247 lines, so it was
  compacted in place. A direct `cp` archive attempt to
  `.codex/archive/PROJECT_STATE_20260706_1827_before_trace_header_fix.md`
  failed with `Read-only file system`; the active state records this.
- Subagent note: a read-only BDD-native explorer was spawned, but
  `wait_agent` returned `not_found`, so no delegated conclusion is available.
- Next core step: determine whether BDD-native runtime can be implemented
  incrementally from `TAwithBDDEdges` without changing MightyPPL BDD semantics,
  then re-run the full review pipeline so the official packet includes the new
  header-trace CLI contract row.

## 2026-07-06 19:02 CST

- User clarified v1 scope: do not implement BDD-native runtime and do not
  implement `compflatten` runtime verification now; keep both as explicit
  reserved interfaces.
- Handoff update: `.codex/PROJECT_STATE.md` now records this as
  user-confirmed deferred scope. Future work should focus on the verified
  flatten + canonical BDD-label projection + MoniTAal runtime path, plus
  complete review-pipeline evidence and manual-review artifacts.

## 2026-07-06 19:55 CST

- Goal: move the trace-header/core fix into the full paper-review pipeline
  without weakening stability checks.
- Code changes: added stability profile `cli-trace-header-contract-added` to
  `test/TARV/scripts/compare_pipeline_results.py` and
  `test/TARV/scripts/run_full_review_pipeline.py`. The profile permits exactly
  the intended CLI contract growth: `cli_contract_rows +1`,
  `cli_contract_pass +1`, `cli_contract_fail +0`,
  `cli_contract_controlled_errors +0`, and `cli_contract_audit.csv +1` row.
- Verification: `python3 -m py_compile` passed for
  `run_full_review_pipeline.py`, `compare_pipeline_results.py`, and
  `run_paper_experiments.py`.
- Full passing pipeline:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_cli_trace_header_contract_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_cli_trace_header_contract_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_workbook_xlsx_table_shape_guard_full_v2
  --stability-profile cli-trace-header-contract-added`.
- Result: pipeline PASS/full, failed steps 0, elapsed 80095 ms. Semantic
  regression remained 87 cases/70 runtime verified/0 fail/error/timeout.
  Candidate/baseline remained 63/63 matched. Review verifier 150 PASS/0 FAIL.
  Stability audit 190 PASS/0 FAIL. CLI contract rows are now 11/11 PASS,
  including `cli_trace_csv_header_time_props` with final POSITIVE and
  2 events/2 processed steps. Workbook `unzip -t` passed.
- Formula catalogs regenerated:
  `test/TARV/results/mitl_formula_catalog_latest_official.md`,
  `mitl_formula_catalog_semantic_regression.csv`,
  `mitl_formula_catalog_monitaal_xml_candidates.csv`, and
  `mitl_formula_catalog_runtime_runs.csv`. Counts: 87 semantic rows, 23 XML
  rows, 150 runtime rows; path scan found no references to the previous
  xlsx-shape packet in those catalog files.
- Current latest packet:
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_cli_trace_header_contract_full`.
- Current timeout rerun:
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_cli_trace_header_contract_full`.

## 2026-07-06 20:22 CST

- Milestone: added a review-packet guard so the MITL formula catalog is not only
  generated, but also forced into the final manual-review workbook with correct
  xlsx table shapes.
- Code changes: `test/TARV/scripts/verify_review_packet.py` now defines the
  three MITL catalog workbook sheet/source pairs, requires the sheets whenever
  catalog artifacts are generated, and adds
  `MITL_FORMULA_CATALOG_WORKBOOK_AUDIT`. `test/TARV/scripts/compare_pipeline_results.py`
  now expects `formula-catalog-integrated` to add exactly one verifier PASS row.
- Verification: `python3 -m py_compile` passed for
  `verify_review_packet.py`, `compare_pipeline_results.py`, and
  `run_full_review_pipeline.py`. Targeted verifier on the previous latest
  packet produced 151 PASS/0 FAIL. Targeted stability compare produced
  190 PASS/0 FAIL with expected verifier delta `check_rows +1/pass +1`.
- Full pipeline rerun:
  `python3 test/TARV/scripts/run_full_review_pipeline.py --out
  test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full
  --timeout-rerun-out
  test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full
  --timeout 30 --timeout-rerun-seconds 60 --stability-baseline
  test/TARV/results/paper_pipeline_cli_trace_header_contract_full
  --stability-profile formula-catalog-integrated`.
- Result: pipeline PASS/full, failed steps 0, elapsed 78887 ms. Review verifier
  151 PASS/0 FAIL, artifact manifest verifier 16 PASS/0 FAIL with 151 manifest
  rows, stability audit 190 PASS/0 FAIL, and `unzip -t
  paper_review_results.xlsx` passed.
- Workbook shape evidence: `MITL Semantic Catalog` 88x17, `MITL XML Candidates`
  24x16, and `MITL Runtime Catalog` 151x11 exactly match the source CSV shapes.
  Global formula catalog latest files were resynced to the new guard packet.
- Current status: latest official packet is
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full`;
  timeout rerun is
  `/home/lqq/project/TAFuzz/test/TARV/results/baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full`.
- Next: continue manual-review preparation for XML-to-MITL equivalence and
  Review Signoff without claiming BDD-native runtime, compflatten runtime, or
  human approval.

## 2026-07-06 20:28 CST

- User instruction recorded: after the full TAMonitor goal is complete, keep
  only one clear final experiment/result packet suitable for manual review
  and clean up intermediate experiment directories, temporary rerun packets,
  and stale result data that are not needed to support the final claim.
- No experiment cleanup was run now because the goal is still active and the
  final packet has not been declared complete. No experiment pipeline was run.

## 2026-07-06 20:30 CST

- User had paused the XML-to-MITL / Review Signoff experiment-review track, so
  no benchmark or review-packet experiment pipeline was run.
- Core TAMonitor health check only: ran the existing
  `finite_atom_identifier` formula/trace through `tool/MightyPPL/build/TAMonitor`
  into `/tmp/tamonitor_core_health`. Result: SAT, final POSITIVE, two processed
  steps, step verdicts `INCONCLUSIVE` then `POSITIVE`, and generated
  `summary.csv`, `steps.csv`, `metadata.json`, and `results.xlsx`.
- Output verification: `results.xlsx` passed `unzip -t`; `metadata.json`
  contains formula, positive/negative NNF, proposition order, satisfiability,
  final verdict, positive/negative TA stats, and build/monitor timing.
- v1 boundary checks: `compflatten` runtime returned controlled
  `unsupported_runtime_mode`; `--emit-bdd-interface` generated
  `bdd_interface.json` with `status=interface_reserved_not_implemented`.
- No code changes were made during this health check. The previously noted
  unverified experiment-script edits remain untouched.

## 2026-07-06 20:39 CST

- Finalization milestone: user requested no more experiment expansion now,
  cleanup of intermediate results, and a project usage manual under
  `/home/lqq/project/TAFuzz/analysis/manual`.
- Removed paused-track, unverified experiment-script additions:
  `XML_EQUIVALENCE_SIGNOFF_COVERAGE_AUDIT` from
  `test/TARV/scripts/verify_review_packet.py` and
  `EXPECTED_XML_EQUIVALENCE_SIGNOFF_COVERAGE_VERIFIER_DELTA` from
  `test/TARV/scripts/compare_pipeline_results.py`.
  Verification: `python3 -m py_compile` passed for both scripts.
- Cleaned `test/TARV/results`: removed 270 historical/intermediate top-level
  entries, reducing the directory from about 14G to about 130M. Kept only the
  final packet, the supporting timeout rerun packet, four MITL catalog
  entrypoint files, and `FINAL_RESULTS_README.md`.
- Added final result entrypoint:
  `test/TARV/results/FINAL_RESULTS_README.md`.
- Added documentation:
  `analysis/manual/README.md` and
  `analysis/manual/TAMonitor_User_Manual.md`. The manual covers accepted MITL
  syntax, trace formats, CLI parameters, outputs, examples, final experiment
  locations, and v1 deferred scope.
- Final verification: final workbook `unzip -t` passed; final packet summary
  reads pipeline `PASS` and failed steps `[]`; review packet verifier JSON has
  151 PASS/0 WARN/0 FAIL; artifact manifest verifier JSON has 16 PASS/0 WARN/0
  FAIL and 151 manifest rows. A final TAMonitor smoke run for
  `F [0,2] p1` with a two-event finite trace returned `SAT` and final
  `POSITIVE`.
- Current status: TAMonitor v1 goal is complete. Do not continue code changes,
  XML proof/signoff expansion, BDD-native runtime, or compflatten runtime unless
  the user explicitly asks.
