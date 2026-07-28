# TAFuzz Project State

Last updated: 2026-07-16 CST.

## Current Goal

Produce a source-backed literature analysis of every fuzzing-centered paper in
the Zotero collections `模糊测试/固件 fuzz 综述` and `模糊测试/总线 fuzz`, plus
their key related work.  Classify methods, remove only genuinely non-fuzz
items/duplicates, and compare PUT/SUT, input channel, execution environment,
benchmark, baseline, oracle, algorithm, black/grey/white-box status, and
reported results.  Firmware and CAN/bus experiments receive the deepest
treatment.

Status: COLLECTION INVENTORY COMPLETE; PRIMARY-PAPER EXTRACTION IN PROGRESS.

## Current Zotero Fuzz Literature State

- Zotero Desktop 9.0.6 local API is available read-only at port 23119.
- Target collections are `QCBU5MKF` (34 top-level items) and `5YWHBV73`
  (22 top-level items).  Indexed full text for the main papers is extracted to
  `/tmp/zotero_fuzz_fulltext/` for read-only analysis.
- Inclusion rule: every paper whose main subject or contribution is fuzzing is
  retained, including distributed-system, DBMS, smart-contract, stateful
  protocol, generic, ML-guided, firmware, and bus fuzzing.  Pure IDS/anomaly
  detection/physical fingerprinting/runtime verification papers are excluded;
  duplicate Zotero records are merged.
- CAN papers must distinguish the real PUT/SUT from the transport: fuzzing a
  CAN controller/protocol/driver is not the same as using CAN frames to fuzz an
  ECU application, diagnostic service, vehicle function, or state machine.
- Fuzz-enabling papers such as DICE and AI-assisted CAN state extraction are
  retained but explicitly separated from papers that actually execute a new
  fuzzer.
- Confirmed examples: FirmFuzz is QEMU full-system greybox/generation fuzzing
  of firmware web applications; UCRF directly fuzzes physical routers using
  backend-derived under-constrained HTTP seeds; DICE adds DMA emulation to
  P2IM/AFL and validates generated failures on real boards.  Most CAN papers
  use CAN as an injection channel rather than testing the CAN protocol itself.

## Current Zotero Fuzz Next Steps

1. Finish per-paper extraction for firmware, CAN/bus, and non-firmware fuzzing.
2. Build the unified experiment/baseline/oracle/result matrix and exclusion list.
3. Write and verify the detailed Markdown report under `analysis/`.

## Previous Goal: RFC7252 MITL Review

## Current RFC7252 Review State

- Scope is only RFC7252 from
  `coap_rfc_dataset/rfc_dataset/rfc7252/rfc7252.txt`.
- Current stage intentionally does not do libcoap function-level mapping,
  LLVM instrumentation, fuzzing, or runtime monitor execution.
- Rebuilt review artifacts:
  - `analysis/protocol_fuzzing_study/rfc7252_libcoap_mitl_review/README.md`
  - `analysis/protocol_fuzzing_study/rfc7252_libcoap_mitl_review/RFC7252_candidate_rules.md`
  - `analysis/protocol_fuzzing_study/rfc7252_libcoap_mitl_review/property_summary.csv`
  - `analysis/protocol_fuzzing_study/rfc7252_libcoap_mitl_review/property_review.md`
  - `analysis/protocol_fuzzing_study/rfc7252_libcoap_mitl_review/properties/property_001.yaml`
    through `property_013.yaml`
- The old `properties.json`, `properties_zh.json`, `review_report.md`, and
  `review_report_zh.md` were removed from the main artifact set.
- RFC7252 was re-scanned directly: 119 relevant normative paragraphs were
  found, manually curated into 31 candidate rules, with 13 accepted main MITL
  properties, 2 SHOULD soft properties, and 16 rejected/deferred/merged rules.
- Main properties are time-bound first: 12/13 have explicit metric intervals
  or `[0,0]` immediate bounds; the only unbounded property is the core
  Empty-ACK/separate-response ordering obligation.
- Time parameters remain symbolic in formulas. Defaults from RFC7252 4.8/4.8.2
  are recorded only as review/default values, not substituted into MITL.
- Long RFC natural-language paragraphs are referenced by local file line ranges
  and short context summaries rather than copied wholesale.
- No libcoap source file was modified.

## Current RFC7252 Verification

- Python/PyYAML validation succeeded for all 13
  `properties/property_*.yaml` files: required fields present, unique IDs,
  non-empty AP/correlation/time fields, and RFC line ranges readable.
- `property_summary.csv` IDs exactly match the YAML property IDs.
- Time coverage check passed: `time_bound=12`, `unbounded=1`.
- Scope check passed: main property files and summary do not contain
  Max-Age/proxy/multicast/DTLS/security/format-only rules.
- `git -C benchmark/coap/libcoap status --short` is clean.
- Not yet run: MITL grammar compilation, TAMonitor execution, LLVM
  instrumentation, or end-to-end verdict generation.

## Current RFC7252 Next Steps

1. User reviews and accepts/rejects individual RFC7252 interpretations.
2. Lower accepted properties into executable AP extraction and MITL syntax.
3. Build the libcoap instrumentation/verdict path for the selected properties.

## Previous Goal: Mixed PTA Analysis

Implement a Roméo-style exact mixed forward/backward PTA analysis in
`src/TAMonitor/PTA`: precompute the Goal-truncated reachable Zone Graph, then
propagate Parrot--Lime priced pieces only along recorded reachable arcs.

Status: COMPLETE.

The existing pure `--pta-analysis backward` solver, default-disabled online
path, and repaired `tool/Romeo` tree are protected baselines.

## Previous Mixed-Analysis Decisions

- Add an opt-in `--pta-analysis mixed`; do not change pure `backward`.
- Use exact Pardibaal DBMs without extrapolation; stop expanding Goal nodes.
- Persist stable graph nodes/arcs plus exact fire/entry/post domains.
- Scope priced pieces, dominance, and witnesses by reachable graph node.
- Do not start backward optimization after an incomplete forward phase.
- Default MightyPPL cost model remains location rate 1 and edge cost 0.
- Baseline command `cmake --build tool/MightyPPL/build --target
  TAMonitorPTATests TAMonitor -j2 && ctest --test-dir tool/MightyPPL/build -R
  '^TAMonitorPTA' --output-on-failure` passed 2/2 before mixed edits.
- Milestone 1 is complete: `ReachableZoneGraph` implements exact initial/Post,
  strict DBMs, stable FIFO/EdgeId traversal, one-way inclusion with retained
  fire/entry/post arc domains, Goal cutoff, and explicit node/arc/timeout
  incompleteness. Its standalone target and all existing PTA tests pass 3/3.
- Milestone 2 is complete: `MixedPricedSolver` scopes finite/-infinity labels,
  dominance, deltas, queries, and witnesses by reachable NodeId. Goal seeds use
  reachable node zones; predecessor order is entry-domain, inverse reset,
  edge cost, guard/source zone, then priced time predecessor. The snapshot is
  structurally bound to the exact automaton that generated it.
- Milestone 3 is complete: `--pta-analysis mixed`, schema-2 summary,
  nodes/arcs/pieces JSONL, phased resource states, `first_hit_terminal` Goal
  semantics, geometry oracle, and observer-clock oracle are integrated.
- Actual runtime MightyPPL formula `!(F [5,10] p1)` is exact with initial cost
  5; assigning cost 3 to every initial valuation-labelled edge yields 8.
  Future/globally/until/once/historically/since mixed geometry checks pass.

## Protected Baseline

- TAMonitor provides the existing MITL-to-TA runtime verification workflow.
- Formal verdicts remain `POSITIVE`, `NEGATIVE`, or `INCONCLUSIVE`.
- Without `--pta-analysis`, no PTA solver runs and no PTA output is emitted.
  The original four artifacts and three workbook sheets remain unchanged.
- The pre-existing non-PTA changes are preserved:
  - `--print-steps` terminal output;
  - interval-valued CSV trace parsing;
  - MightyPPL export of clocks actually referenced by guards, invariants, and
    resets.

## Active Implementation

- The approved implementation scope is the Parrot-Lime 2020 backward
  cost-to-go algorithm. Bouyer-Colange-Markey 2016 is only a forward/theory
  oracle and benchmark fallback.
- The production representation follows the paper's sign convention
  `W = -remaining_cost`; the public API exposes direct cost-to-go.
- MightyPPL integration defaults to the negative automaton, accepting
  locations as goals, location rate 1, and edge cost 0. PTA analysis is
  finite-word only and disabled unless explicitly requested.
- Signed weights require an explicit lower-boundedness contract. Resource
  interruption and unverified assumptions must never be reported as optimal.
- Pardibaal DBM operations are reused without changing MoniTAal or
  Pardibaal. Ordinary Federation merging is not valid for priced pieces.
- Exact affine dominance uses the installed Z3 QF_LRA library; floating
  LP solvers are excluded from proof-critical pruning.
- The pre-change baseline was reconfigured and rebuilt successfully. The
  `smoke_f_01` run remained `POSITIVE`, produced only the four v1 artifacts,
  and the workbook retained exactly `Steps`, `Summary`, and `Metadata`.

## Prior Baseline Handoff

- The earlier PTA hybrid prototype was fully removed before this task; the
  rollback and its verification remain recorded in `.codex/SESSION_LOG.md`.
- Existing non-PTA user changes (`--print-steps`, interval CSV parsing, and
  MightyPPL clock export fixes) must be preserved.
- The worktree was already dirty when this task began; no reset/revert is
  permitted.

## Active Changed Files

- Imported and repaired official Roméo 3.10.12 sources under `tool/Romeo/`;
  provenance and the complete repair boundary are documented in
  `tool/Romeo/UPSTREAM.md` and `tool/Romeo/REPAIR_NOTES.md`. No existing
  TAMonitor, MightyPPL, or MoniTAal implementation file was changed.
- New algorithm, proof, test, and experiment files under `src/TAMonitor/PTA/`.
- `src/TAMonitor/TAMonitor.h`, `src/TAMonitor/TAMonitorOptions.cpp`, and
  `src/TAMonitor/TAMonitorMain.cpp` for the optional, independent PTA path.
- `tool/MightyPPL/CMakeLists.txt` for the independent PTA library/test target.
- `.codex/PROJECT_STATE.md` and `.codex/SESSION_LOG.md` for continuity.
- Mixed increment specifically adds `ReachableZoneGraph.{h,cpp}`,
  `MixedPricedSolver.{h,cpp}`, their isolated C++ tests, and
  `PTAMixedIntegrationTest.py`; extends `PTAAnalysis` for schema-2 mixed
  output; adds outgoing/EdgeId lookup to `WeightedAutomatonView`; and updates
  the PTA proof, README, experiment report, CLI, main dispatch, and CMake.
- No MoniTAal, Pardibaal, or Roméo source was changed by the mixed increment.

## Active Verification

- Final mixed completion audit found no remaining P0/P1/P2 issue. The public
  graph snapshot is bound by exact structural comparison to its source TA,
  closing the same-topology/different-guard misuse counterexample.
- Final `ctest --test-dir tool/MightyPPL/build -R '^TAMonitorPTA'
  --output-on-failure` passed 5/5: pure primitives, reachable graph, mixed
  solver, pure integration, and mixed integration.
- Exact forward tests cover reset/diagonal/strict Post, Goal cutoff, stable
  EdgeId order, one-way inclusion with retained fire/entry/post domains,
  initial Goal, node/arc limits, and final timeout completeness checks.
- Mixed tests cover finite values, reachable `+infinity`, reachable and
  unreachable `-infinity` regions, outside-domain queries, entry-domain arc
  restriction, subsumption on/off, genuinely different FIFO/EdgeId orders,
  structural graph binding, phased limits, and lower-bound contracts.
- Independent numeric oracles pass: hand WTA cost 14 has Z3 `cost<14` UNSAT
  and `cost=14` SAT; its strict version keeps infimum 14 with
  `attained=false`; a MoniTAal observer model proves cost 3.
- Actual MightyPPL runtime TA for `!(F [5,10] p1)` has mixed initial cost 5,
  exact `Reach intersect Pre*(Goal)` support, `T<5` unreachable and `T<=5`
  reachable. Cost 3 on every initial valuation-labelled edge yields 8.
- Mixed future/globally/until/once/historically/since formula cases are exact
  and pass the geometry oracle. Default, pure backward, and mixed preserve the
  same online verdict; default outputs remain four files/three workbook
  sheets, and pure backward remains schema 1 with two PTA files.
- Latest core build passes `-Wall -Wextra -Wpedantic -Werror` and
  ASan/UBSan. LeakSanitizer cannot run under the current ptrace environment,
  so no new leak-free claim is made. `BUILD_TESTING=OFF` exposes only the
  production TAMonitor/TAMonitorPTA targets.
- Roméo FORMATS quick was rerun 4/4 with the fixed values; the preserved full
  artifact result remains 9/9 with every forward/backward pair equal.

- Roméo's optimized full CLI build and `make check` pass. The new suite covers
  CostDBM slope/strictness/assignment/dimension cases, hash and pairing-heap
  safety, type-safe BV/BCV dispatch, initial/zero/positive/negative costs,
  overflow rejection, signed-cycle interruption, and the forward oracle.
- `make check-sanitize` passes ASan/UBSan. A focused LSan comparison reduces
  backward-only leaks from 2600 B/46 allocations to the pre-existing
  parser/CTS baseline of 768 B/18 allocations; no priced graph/CostDBM stack
  remains. LeakSanitizer is deliberately separate from the ASan/UBSan target.
- The repaired optimized Roméo passes all four FORMATS 2020 quick numeric
  oracles with equal forward/backward values: aircraft3 -1140, aircraft4
  -4140, scheduling2 -1760, and scheduling3 -2560. Roméo 3.10.12 prints bare
  numbers, so the older `= value` artifact parser mislabels these runs even
  though independent exact parsing confirms 4/4.

- Pre-change TAMonitor configure/build and `smoke_f_01` passed; final verdict
  remained `POSITIVE`, only four v1 artifacts were emitted, and the workbook
  retained the three v1 sheets.
- `TAMonitorPTA` and `TAMonitorPTATests` configure and build successfully with
  Pardibaal commit `1eb56e87829997d02a95e1fa80635693181245eb` and Z3 4.8.12.
- `TAMonitorPTATests` passes weighted-zone rebase/reset, all time-predecessor
  slope cases, strict-bound attainment, Fig. 2 splitting, exact dominance,
  resource limits, domain-sensitive `-infinity`, shortest time, and Fig. 1
  optimum 9.
- The analysis adapter compiles a stable `source+ordinal` WTA snapshot from
  the selected MightyPPL TA, loads exact integer XML costs, and serializes
  exact `pta_analysis.json` plus `pta_pieces.jsonl` with witness/completeness
  metadata.
- `TAMonitorPTAIntegration` passes default-off artifact/workbook regression,
  explicit finite negative-TA analysis, exact JSON parsing, signed-weight
  `ASSUMPTION_REQUIRED`, resource limits, stable cost overrides, malformed
  config rejection, and infinite-word rejection.
- The expanded C++ suite passes exact Federation past equivalence, multi-reset
  diagonal weights, strict epsilon optima, crossing affine dominance,
  subsumption/order invariance, replayable `-infinity` regions, an independent
  Z3 path oracle, and a MoniTAal observer-clock shortest-time oracle.
- Five additional future/past/binary MITL formulas plus `smoke_f_01` all have
  exact snapshots; priced support equals MoniTAal `Pre*(Goal)` at every
  location when `--pta-verify-geometry` is enabled.
- ASan/UBSan and warning-as-error builds pass. `BUILD_TESTING=OFF` excludes
  both PTA test targets without requiring Python test discovery.
- Romeo FORMATS 2020 full artifact run passed 9/9; every model's original
  forward/backward cost agrees. Results are recorded in
  `src/TAMonitor/PTA/ExperimentReport.md`.
- Final default online smoke remained `POSITIVE`, emitted only the four v1
  files and retained exactly `Steps`, `Summary`, and `Metadata`; explicit
  analysis emitted only the two additional PTA files.

## Research Note: Bouyer-Colange-Markey 2016

- Read the Zotero copy of *Symbolic optimal reachability in weighted timed
  automata* (item `9ATR45NY`, attachment `FTXCYREL`) and the authors' arXiv
  appendix.
- The paper's new step is a cost-aware implicit-abstraction subsumption
  `sqsubseteq_M` over exact priced zones; it does not explicitly apply the
  classical DBM `Extra_M` operator.
- The inclusion test partitions valuations by the clocks still at or below
  their maximal constants, eliminates the other clocks through minimizing
  facets, and compares finitely many affine objectives.
- The result removes the global bounded-clock assumption. Termination still
  needs a uniform lower bound for generated bounded-below cost functions;
  indefinitely descending negative-cost cycles are not covered by an
  unconditional termination theorem.
- This was a read-only research task. No TAMonitor/PTA source was restored or
  changed; only these handoff notes were updated.
- Follow-up design conclusion: paper states `(location, zone, affine prefix
  cost)` can be generated offline for fuzzing, but the paper's affine cost is
  cost-from-initial, not cost-to-violation. A useful offline guide therefore
  needs a persisted priced-zone graph plus a separate backward/Bellman `h` or
  action-`Q` analysis. Runtime lookup must match the full positive/negative
  MoniTAal state sets by location and Federation/DBM intersection; current
  TAMonitor reports only their counts, so a read-only state snapshot API would
  be required. No implementation was authorized or added.
- Refined target architecture: offline analysis should compile each timed edge
  into piecewise source domains carrying feasible delay intervals, optimal
  delay witnesses, local step-cost expressions, successor pieces, and
  cost-to-go/action-Q functions. Exact table hits need only evaluate these
  functions online; misses can run a bounded A*/best-first search using
  certified offline lower bounds. A single scalar cost per edge is
  insufficient because feasibility and downstream value depend on the current
  clock valuation.

## Research Note: MightyPPL 2025 Reverse TA

- Read the Zotero PDF *MightyPPL: Verification of MITL with Past and Pnueli
  Modalities* and checked its reverse-language construction, implementation
  section, decidability argument, and the current MightyPPL/MoniTAal sources.
- Lemma 1 constructs a generic finite-word language reversal `A -> A^R` using
  locations `(s,b)`, a bit for each `(clock, original edge)`, and upper/lower
  auxiliary clocks. This is a new TA accepting reversed timed words, not a DBM
  predecessor computation on the original TA.
- The current source does not implement that generic transformer. It directly
  builds optimized past tester templates in `Once.cpp`, `Historically.cpp`,
  `Since.cpp`, `Trigger.cpp`, `PnueliOn.cpp`, `PnueliHn.cpp`, `CountOn.cpp`, and
  `CountHn.cpp`, which is consistent with the paper's decision to avoid the
  generic reversal blow-up.
- The distinct backward-reachability implementation is present: MightyPPL
  calls MoniTAal's finite/Buchi fixpoints, which traverse original TA incoming
  edges and compute Federation/DBM predecessors via `past`, inverse reset,
  guard restriction, and another `past`.
- Theorem 1 explicitly proves unilateral MITPPL satisfiability and model
  checking PSPACE-complete. Full MITPPL decidability follows from Lemmas 9-16
  and the effective translation to finite standard TAs plus decidable TA
  emptiness; the paper does not state a separate tight complexity theorem for
  full MITPPL.

## Research Note: Backward Priced-DBM Design

- Read and visually checked Parrot and Lime (FORMATS 2020), *Backward
  Symbolic Optimal Reachability in Weighted Timed Automata*, against the
  current MoniTAal DBM predecessor implementation.
- The correct extension is a min-plus Bellman predecessor over overlapping
  priced pieces `(location, DBM zone, affine cost-to-go)`, not a scalar cost
  attached to an ordinary Federation.  The represented value is the pointwise
  lower envelope of all pieces covering a valuation.
- A discrete predecessor intersects the target invariant, applies the exact
  inverse reset `free_R(Z intersect R=0)`, substitutes reset clocks by zero in
  the affine cost, intersects the guard/source invariant, and adds the edge
  cost.
- A time predecessor computes
  `inf_d(rate(location)*d + h(v+d))`.  Its objective has delay slope
  `lambda = rate + sum(affine coefficients)`: positive lambda selects lower
  facets, negative lambda selects upper facets, and zero lambda preserves the
  affine form over the ordinary past zone.  Facet substitution yields finitely
  many DBM-affine pieces.
- The clean solver invariant stores already-computed suffix values and applies
  exactly one priced source-time predecessor after each discrete predecessor.
  MoniTAal's existing leading target `past()` is only an idempotent geometric
  convenience for unpriced reachability and should not be copied blindly into
  the new value solver.
- Cost-aware pruning requires both zone inclusion and pointwise affine-cost
  dominance.  Current same-location Federation merging is unsound for priced
  pieces because it discards geometrically included DBMs without considering
  their costs.
- Bellman iteration is exact by induction on the maximum number of discrete
  edges in a goal-reaching suffix.  Exactness alone does not imply termination;
  a first implementation should use nonnegative rates/edge costs, with general
  negative weights requiring explicit negative-cycle and `-infinity` handling.
- This was a read-only design task. No MoniTAal, MightyPPL, or TAMonitor source
  was changed.

## Research Note: Parrot-Lime 2020 Source Availability

- The paper's Section 4 and footnote 3 identify Roméo as the implementation
  and link `http://romeo.rts-software.org/releases/FORMATS2020.tgz`.
- The original URL now returns 404, but the 2022-02-14 Wayback snapshot is
  downloadable. Its README explicitly says that it provides only Linux and
  Windows 64-bit computation-engine binaries. The archive contains those two
  binaries, nine `.cts` benchmark models, and the README; it has no source.
- The Linux artifact embeds
  `version FORMATS20, 2020-03-27 -- f634bf9d05625e04019e5056080c7eb243091060`.
  Searches of Software Heritage, GitHub, Sourcegraph, GitLab, Zenodo, HAL,
  author pages, and general web indexes found no public repository or source
  snapshot for that exact revision.
- Roméo's current official site publishes full CeCILL-licensed sources. The
  still-online 3.9.1 and current 3.10.12 source tarballs contain
  `backward_mincost.{cc,hh}`, `bvzone.{cc,hh}`, `cost_dbm.{cc,hh}`, `parser.y`,
  and the build files. These implement the paper's mixed forward-state-space /
  backward-cost propagation, weighted action predecessor, facet-based time
  predecessor, and cost-aware reduction, but are later evolved releases and
  cannot be claimed as byte-identical to the 2020 revision.
- Practical conclusion: use the Wayback artifact for exact Table 1 binary
  reproduction, or the official 3.9.1/3.10.12 sources for study and porting.
  Obtaining the exact 2020 source requires asking Rémi Parrot or Didier Lime
  for a `git archive` of revision `f634bf9d...`.
- At the availability-search stage, verification was read-only and no binary
  was executed. The later 3.10.12 audit below executed the archived Linux
  artifact and a supplied 3.10.12 CLI binary; no project source was modified.

## Research Note: Roméo 3.10.12 Backward-Cost Audit

- Audited the official 3.10.12 source archive against Parrot-Lime Definitions
  3-10, Theorems 1-2, Algorithm 1, and the Section 4 mixed implementation.
  `CostDBM` correctly represents a DBM plus affine paper-sign value `W=-V`;
  restriction/rebase, inverse mapping, edge-cost subtraction, facet slopes,
  pointwise max-dominance, delta propagation, and final sign conversion map
  directly to the paper for closed zones.
- Roméo uses enabled-transition ages as DBM dimensions and first constructs a
  reachable marking/zone graph, then propagates priced pieces backward along
  recorded edges. Goal graph nodes are seeded with their actual reachable DBM
  at `W=0`, rather than the pure paper algorithm's universal goal zone.
- Confirmed a 3.10.12 CLI routing regression. `BackwardMincost` does not
  override `has_cost()`, so an ordinary `check[zones] mincost(goal)` creates a
  `VZone`; `BVZone::init` has no dispatcher call, while the evaluator performs
  invalid `BVZone*` downcasts. A minimal model returned forward mincost `5`,
  zones backward mincost `true`, and cost-control `5`. The official 2020 Linux
  artifact still returned matching forward/backward `-1760` on scheduling2.
- Direct execution of the original 3.10.12 `CostDBM` kernel confirmed a core
  Theorem-2 omission: for `p > sum(r)`, `past_max` adds lower-facet pasts but
  omits the original zero-delay zone. For `Z=[2,5], r=0, p=1`, it produced
  `[0,2]` and incorrectly excluded `x=3`. The `p == sum(r)` rebase path was
  separately checked and was correct.
- Strict-zone tests found two additional exactness failures in the same
  kernel: topological closure in the non-equal-slope facet path can leak an
  unreachable strict diagonal boundary, and `time_bound` strictness can remain
  in `coffset` after restriction to an attained point (`W(2)=0` represented as
  `0-epsilon`). These can affect dominance/results. `past_min` also has a
  separate equal-slope offset error, but that is in the control/game path, not
  the paper's `past_max` reachability path.
- The source audit and tests were read-only with respect to TAFuzz, TAMonitor,
  MightyPPL, and MoniTAal. Only these handoff notes were updated; temporary
  source, PDF render, binary, and harness files were removed after analysis.

## Research Note: PGFUZZ Paper-Code Audit

- Read and visually checked Kim et al. (NDSS 2021), *PGFUZZ: Policy-Guided
  Fuzzing for Robotic Vehicles*, and audited `purseclab/PGFuzz` main commit
  `7eaebf21116087249b8329d4ba7337a24a34ecb9` through the GitHub connector and
  a disposable shallow clone.
- The released ArduPilot/PX4 code implements the paper's distinctive online
  core: policy-specific input pools, MAVLink/SITL execution, reference-state
  averaging, hand-coded propositional/global distances, negative-distance
  oracle, and reuse of input values that improve a proposition.
- It is not the complete paper artifact: there is no generic MTL parser or
  expression-tree generator, no deletion/replay Bug Post-Processing, no
  1,000-input/2-hour policy scheduler, no Paparazzi implementation, and the
  static analysis stage is an external unpinned dependency.
- Exact A.CHUTE1 distance code matches the paper's example, but the release has
  material execution hazards: PX4's default policy label/length mismatch makes
  guidance inert, combined-policy names use `_` in directories and `-` in
  callbacks, and the required `policy_violations/` directories are absent.
- Paper-level reproduction was not attempted: it requires Python 2, GUI tools,
  external target checkouts/simulators, and missing experiment orchestration.
  No project implementation source was changed; only these handoff notes were
  updated. Temporary PDF/source inspection data stayed outside the workspace.

## Research Note: ProtocolGuard Rule-Extraction Audit

- Audited the NDSS 2026 paper and the complete Zenodo v1 artifact
  (`10.5281/zenodo.17933922`, MD5 `beb20443b72171c263644da5428ca466`).
  The public GitHub repository currently contains only its README, license,
  and images; the rule-extraction source is present only in the Zenodo ZIP.
- The released pipeline accepts one HTML specification per run, removes and
  separately serializes tables, constructs message/field terms from the live
  Wireshark `master` dissector with DeepSeek, filters headings, resolves
  sentence coreferences, expands protocol/modal/comparative keyword variants,
  applies literal substring candidate matching, uses a second LLM pass to
  retain server-side single-message processing rules, and finally emits
  `rule/req_type/req_fields/res_type/res_fields` JSON objects.
- The actual first-stage source accepts either two protocol-specific terms or
  one protocol-specific term plus a modal/comparative term. This is broader
  than the paper's stated one-specific-plus-one-modal/comparative rule. Tables
  are not consumed after extraction, and the released source has no multi-RFC
  merge/deduplication path for the five FTP RFCs.
- Evaluation sources are OASIS MQTT 3.1.1 (83 rules), OASIS MQTT 5.0 (118),
  CoAP RFC 7252 (30), FTP RFCs 959/2228/2389/2428/3659 (54), TLS 1.3 RFC 8446
  (58), and DHCPv6 RFC 8415 (77), totaling 420 unique rules. RFC 2119 supplies
  the modal vocabulary and is not itself one of the target protocol corpora.
- Artifact completeness is limited: only MQTT 5.0 input and intermediates are
  included; its saved workbook has 1,514 sentences, 1,205 heuristic matches,
  but only three recorded second-pass decisions. `example/MQTTv5.json` has 126
  rules while the paper reports 118, and the source producing its grouped form
  is absent. No DeepSeek calls or full extraction run were repeated.
- This was a read-only source/PDF audit. No TAFuzz implementation or nested
  repository source was changed; only these handoff notes were updated.

## Research Note: Natural Language to Metric Temporal Logic

- Surveyed 2021--2026 primary literature and audited the currently linked
  repositories for automatic natural-language-to-temporal-logic translation.
- No public implementation was found that directly targets and enforces the
  MITL fragment. The two accessible direct-MTL prototypes are DSVA (IEEE
  Access 2026, implementation on the `nl2mtl` branch) and NL2MTL (EDOC 2024
  revised proceedings, published 2025, GPL-3.0).
- Both direct-MTL prototypes require an external LLM API and neither performs
  parser/model-checker-based semantic validation or enforces non-punctual MITL
  intervals. DSVA uses MTL-to-NL back-translation similarity; NL2MTL is a
  prompt-based document prototype whose published outputs contain nonstandard
  or non-MITL-safe forms such as `X^k`.
- The strongest source-backed adjacent systems are FRET (structured FRETish to
  discrete-time future/past metric LTL), NL2TL, DeepSTL, and DialogueSTL (the
  latter three target STL/PSTL). TR2MTL directly targets MTL but its public
  repository currently contains data rather than the paper's implementation.
- For an RFC-to-MITL pipeline, the evidence supports a typed MITL-safe
  intermediate representation, explicit AP/time-unit grounding, constrained
  parsing, and validation with positive/negative timed traces or TA/monitor
  semantics. No implementation was added during this research task.

## Research Note: LTL-Fuzzer Automaton Guidance

- Read and visually checked Meng et al. (ICSE 2022), *Linear-time Temporal
  Logic guided Greybox Fuzzing*, and audited `ltlfuzzer/LTL-Fuzzer` main commit
  `716ac301fa3a8ea39814bc80eeebba49c19c1378` through the GitHub connector and
  a disposable shallow clone.
- The paper uses two distinct heuristics: Buchi-automaton distance ranks saved
  input-prefix/automaton-path tuples and chooses a label on a progress edge;
  AFLGo CFG distance then biases suffix mutations toward a program location
  associated with that label.
- The selected automaton edge is not controlled or guaranteed feasible. The
  saved prefix replays prior progress under the paper's deterministic-reactive
  assumption; the mutated suffix executes the real program, whose observed
  event trace determines the actual automaton transition. Infeasible labels or
  targets can consume their time budget without progress.
- The released main implementation is materially weaker than Algorithm 1:
  `compute_prefix_fitness()` returns `1.0`, `RandomStrategy` ignores supplied
  weights, transition selection randomly prefers unvisited successor states
  rather than decreasing accepting-state distance, `MCState.distance` is
  always populated with zero, and `get_state_paths()` is unused.
- The paper's proposition-to-code mapping is an explicit list of tuples
  `(location, proposition, enabling condition)` produced manually for the
  running example; it notes that a general implementation would require alias
  analysis. The public artifact contains no alias, def-use, data-dependence, or
  slicing implementation. Its LLVM pass consumes hand-authored
  `file:line:event` files, matches debug locations, and injects trace/state
  callbacks mechanically.
- The artifact does extract call graphs and CFGs to compute AFLGo target
  distances, but this is control-flow guidance rather than proposition data
  dependency extraction. State hashing broadly gathers module globals and
  debug-declared stack variables instead of an AP-relevant dependency slice.
- The protocol pass supports `-pevents`, but the checked-in
  `instrument-telnet.sh` second compilation supplies only `-distance`; with the
  protocol source omitted, the repository does not show a complete runnable
  path that activates its location-to-proposition callback insertion.
- This was a read-only paper/code audit. No TAFuzz or nested tool source was
  changed; only handoff notes were updated.

## Blockers

None.

## Next Steps

1. Future fuzzing may consume immutable graph nodes/arcs, cost pieces, and
   witnesses; an online ranking policy remains intentionally out of scope.
2. Automatic proof of lower-boundedness for general signed discrete cycles is
   still a separate algorithm; the explicit user contract remains in force.
