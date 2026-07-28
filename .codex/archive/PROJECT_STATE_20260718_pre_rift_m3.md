# TAFuzz Project State

Last updated: 2026-07-18 07:34 CST.

## Current Goal And Status

Implement RIFT (Residual-Conditioned Influence Frontier) under
`src/StaticAnalysis`: starting from evidence-bound typed MITL APs, extract
portable C/C++ source influence cones, externally controllable frontiers, and
mutation recipes for later fuzzing. The analyzer must identify value, control,
alias, lifecycle, scope, timing, and prerequisite-sequence dependencies without
letting implementation flow originate or change a requirement.

Status: two non-overlapping workstreams are active. RIFT-M0, RIFT-M1, and
RIFT-M2 are complete; RIFT-M3 weak-baseline implementation is next. The
ArduPilot/PX4 MITL benchmark has completed Milestones 1--6. Milestone 7 final
formula/trace/independent-review validation is next.

- RIFT-M0 froze the pre-implementation comparison, ten falsifiable hypotheses,
  baseline identity rules, and the portability contract.
- RIFT-M1 passed its pre-core gate: seven required steps, five child validators,
  and 185 checks passed. FGS remains `BLOCKED`; PGFuzz/MoonShine remain
  `PARTIAL`; no unavailable artifact was rewritten as a success.
- RIFT-M2 froze 120 mechanically labelled C/C++ cases across 12 dependency
  categories; schema, complete relation matrices, deterministic regeneration,
  and all 120 Clang 18 compile/link/run checks passed.
- No RIFT core implementation has been written. `src/StaticAnalysis` remains
  empty. M3 must implement all weak baselines before the novel core.
- The ArduPilot/PX4 benchmark Milestones 1--5 remain valid inputs. Milestone 6
  now has 15 property/profile parameter instances and 8 concrete formulas
  marked `CONCRETE_UNVALIDATED`; none is a conformance result. Do not let
  either workstream overwrite the other's artifacts or handoff facts.

## Frozen Identities

- ArduPilot SUT: `/home/lqq/project/TAFuzz/baseline/ardupilot`, commit
  `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`; Copter/Plane/Rover.
- ArduPilot MAVLink: `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472`.
- ArduPilot official wiki corpus: commit
  `209e532bc97e5a41966f8c9ab483323c264cae08`; sparse `common`, `copter`,
  `plane`, `rover`; document status `MAIN_ONLY`.
- PX4 SUT/docs: v1.17.0 commit
  `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`; multicopter SITL.
- PX4 MAVLink: `33af200d25ec6f0925b49b1ba82bbf1294ea5f72`.
- PGFuzz artifact: `7eaebf21116087249b8329d4ba7337a24a34ecb9`.
- ADGFuzz artifact: `203fce3f4265241340ed62b9be90aec1da0afa37`.
- Full PDF paths/hashes are in `benchmark/source_freeze_manifest.json`.

## Active Artifacts

RIFT:

- `analysis/rift_preimplementation_comparison_zh.md`: 10-method, source-backed
  pre-implementation comparison with H-RIFT-01 through H-RIFT-10.
- `analysis/data/rift_preimplementation_matrix.csv`: machine-readable 10-row,
  24-field comparison matrix.
- `benchmark/rift/README.md`: benchmark-first and portability contracts. The
  core may consume only Property IR, compilation/LLVM facts, and versioned
  model-pack interfaces; project-specific names and paths are forbidden.
- `benchmark/rift/portability_contract.json` and
  `validate_portability_contract.py`: machine-checkable core/model-pack split,
  forbidden core literals, and the final three-project zero-core-diff gate.
- `benchmark/rift/reproduction/{README.md,m1_manifest.json,validate_m1.py}`:
  aggregate M1 gate with 13 normalized statuses and 19 evidence hashes.
- `benchmark/rift/reproduction/literature_baselines/`: original LTL-Fuzzer
  Automata component/Public Problem1 smoke, 49 AP target tuples, PGFuzz
  56-policy silver import, and MoonShine read/write micro reproduction.
- `benchmark/rift/reproduction/libcoap/`: deterministic Clang/LLVM 18 build,
  whole-program bitcode, and MemorySSA reproduction script/results.
- `benchmark/rift/reproduction/fgs/`: auditable upstream-artifact failure
  evidence; FGS runtime results are not claimed.
- `benchmark/rift/reproduction/ardupilot/`: isolated Clang 18 Copter build,
  1,336-entry compile database, and read-only GCS-failsafe source facts.
- `benchmark/rift/reproduction/svf/`: clean SVF-3.2 LLVM 18 build and official
  WPA MAYALIAS/NOALIAS, MemorySSA, and 78-node/75-edge SVFG smoke.
- `benchmark/rift/gold/`: completed RIFT-M2 generator, common ground-truth
  schema, 120 C/C++ cases/oracles, compile DB, validator, and validation log.

Existing benchmark/property inputs:

- `benchmark/source_freeze_manifest.json`: frozen revisions and preservation
  rules.
- `benchmark/paper_audits/`: three completed method audits.
- `benchmark/schemas/`: property, catalog, DocGraph, candidate, and timed-trace
  JSON Schemas.
- `benchmark/scripts/build_corpus.py`: deterministic markup/comment/parameter
  corpus and keyword-prefilter generator.
- `benchmark/scripts/validate_corpus.py`: file/hash/node/candidate/HEAD
  integrity validator.
- `benchmark/extraction_runs/milestone3/`: generated DocGraphs, prefilter
  candidates, summaries, and reproduction notes.
- `benchmark/ArduPilot/source_and_corpus_manifest.json` and PX4 counterpart:
  complete per-file corpus manifests.
- `benchmark/ArduPilot/coverage_ledger.csv` and PX4 counterpart: one row per
  screened file, with deterministic-scan and human-review status separated.
- `benchmark/{ArduPilot,PX4}/property_catalog.{md,csv,json}` and
  `properties/*.{md,json}`: 13 schema-valid symbolic property records.
- `benchmark/{ArduPilot,PX4}/atomic_proposition_map.{csv,json}` and
  `time_constraints.csv`: 46 AP definitions and 13 symbolic time contracts.
- `benchmark/extraction_runs/milestone4/`: 36,151-row adjudication ledgers;
  every unselected prefilter hit remains `PENDING_CONTEXT_REVIEW`.
- `benchmark/scripts/build_property_catalog.py` and
  `validate_property_catalog.py`: deterministic generation and validation.
- `benchmark/extraction_runs/milestone5/`: frozen-source binding audits,
  compile-database manifest, MAVLink AP observation audit, and clangd summary.
- `benchmark/{ArduPilot,PX4}/source_bindings.csv` and
  `mavlink_observation_matrix.csv`: 227 current-source bindings and 77 AP
  observation records; runtime evidence is a separate layer.
- `benchmark/extraction_runs/milestone6/`: four selected captures plus one
  preserved failed PX4 attempt; merged parameter/message/time evidence.
- `benchmark/mavlink_catalog/`: reproducible static catalogs plus a 1,307-row
  profile×message runtime overlay, with separate static/runtime manifests.
- `benchmark/MAVLink_ArduPilot_PX4_observability.md`: 400-line reader guide
  covering wire objects, support layers, four profiles, clocks, and AP limits.

## Stable Decisions

- PGFuzz policy identification was manual; its static/dynamic work occurred
  after formula creation. Historical policies are leads, never inherited.
- ADGFuzz ground/deviation/silence rules remain `AUXILIARY_ORACLE`; their
  paper/README/code times and clocks are kept separately.
- ProtocolGuard contributes hierarchy/context recovery and identity binding;
  its single-message/history-free filter and implementation-driven rule
  decisions are excluded.
- LLM output is evidence-bound Requirement IR only. Deterministic code checks
  temporal relations and compiles formulas.
- Every time value is a document literal, parameter default/runtime snapshot,
  complete derivation, explicit paper experience, or `UNKNOWN`.
- No custom epsilon is invented. If timestamp/transport uncertainty can change
  a boundary verdict, the result is `INCONCLUSIVE`.
- AP binding is multi-to-multi and records exact/may/modelled/name-only. It
  answers where/how to observe, not whether the system satisfies a property.
- MAVLink dialect-defined, statically supported, requestable, and runtime-
  observed sets are distinct; message fields, MAV_CMD params, and firmware
  configuration parameters are separate objects.
- Keyword hits are high-recall candidates only; `PENDING_CONTEXT_REVIEW` is not
  an accepted requirement.

## Prior Property-Benchmark Summary

- Milestones 3--4 screened 9,772 files and retained all 36,151 candidates in
  auditable ledgers, then produced 13 symbolic properties, 46 typed APs, and
  13 symbolic TimeContracts. Concrete MITL bounds, epsilon values, and
  conformance conclusions were deliberately not invented.

## Milestone 5 Results

- ArduPilot: 25/25 APs are `BOUND` through 107 bindings across the frozen
  Copter, Plane, Rover, shared GCS, arming, RC, and battery sources.
- PX4: 19 APs are `BOUND` and 2 are `PARTIALLY_BOUND`, through 120 bindings in
  commander, navigator, uORB, parameters, events, and MAVLink send/receive
  sources. Unresolved semantics remain explicit rather than guessed.
- Static AP observation classes are `DIRECT=9`, `DERIVED=6`, `CONDITIONAL=13`,
  `INSTRUMENTATION_REQUIRED=16`, and `UNRESOLVED=2`. All 77 message/field
  records remain runtime-unobserved.
- Property status is ArduPilot 6 `REVIEW_READY` plus 1 `CANDIDATE`; PX4 3
  `REVIEW_READY` plus 3 `NEEDS_CONTEXT`. There is no `ACCEPTED` property,
  concrete MITL value, invented epsilon, or implementation conformance claim.
- Milestone 6 runtime merge contains 4 `COMPLETE` captures, 4,999 parameter
  rows, 1,307 profile×message rows, 128 observed time-field rows, and 15
  property/profile values. Instance states are 10 active-unvalidated, 2
  disabled-domain, 2 context-open, and 1 unformalized; 8 properties have one
  profile-consistent concrete formula and all remain `NOT_ASSESSED`.
- Milestone-6 aggregate gate passed 1,035 checks over 111 artifact references,
  53 JSON, 14 JSONL/31,951 records, and 7 CSV/10,061 rows. Static catalog,
  runtime overlay, runtime capture, and Stage-6 property validators all pass.

## Verification Status

- `PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/gold/validate_gold.py
  --jobs 8` passed all 120 cases: 12 categories × 10, C/C++ 60/60,
  MUST/MAY/NO 48/36/36, JSON schema and exact locations 120/120, byte-identical
  regeneration, and Clang 18 object compile + executable link/run 120/120.
- M2 corpus contains 189 sources, 130 APs, 202 complete source×AP relations,
  and 373 expected edges. Influence, controllability, and frontier labels are
  independent; real-project human annotation remains `PENDING`.
- `PYTHONDONTWRITEBYTECODE=1 python3
  benchmark/rift/reproduction/validate_m1.py` passed: seven required steps,
  five child validators, 185 checks, zero failures. `src/StaticAnalysis` was
  empty at the captured pre-core gate.
- M1 observed: LTL-Fuzzer original Automata/Public Problem1 PASS; libcoap three
  deterministic Clang/LLVM 18 runs PASS; ArduPilot Clang 18 Copter build PASS;
  clean SVF-3.2 WPA/MemorySSA/SVFG smoke PASS. FGS is still upstream-blocked.
- `PYTHONDONTWRITEBYTECODE=1 python3
  benchmark/rift/validate_portability_contract.py --phase pre-core` passed with
  contract SHA-256 `e6ba3339...735962`; the final ≥3-project evaluation is
  intentionally `NOT_RUN`.
- Prior corpus/property validation remains valid: 9,772 files, 615,547 graph
  records, 36,151 candidates, 13 properties, 46 APs, and 13 TimeContracts.
- `python3 benchmark/scripts/validate_source_bindings.py --run-clangd` passed:
  13 properties, 46 APs, 227 bindings, and 77 observations. ArduPilot selected
  TUs passed 23/23; PX4 passed 14 directly and one with tweak-only diagnostics,
  with no AST/compile error. PX4 parameter generator inputs were verified
  separately and were not misrepresented as compile-database TUs.
- Frozen compile DBs contain 1,543 ArduPilot and 868 PX4 entries; Plane/Rover
  and PX4 SITL builds completed at the recorded commits. Static MAVLink catalog
  validation passed for 352 ArduPilot and 251 PX4 messages. Runtime and Stage-6
  property validators pass after re-merging final capture-manifest hashes.
- No conformance assessment, fuzz campaign, or TAMonitor property run has yet
  been performed.

## Local Changes To Preserve

- Root workspace is not to be treated as a Git repository.
- ArduPilot has the pre-existing dirty `m modules/CrashDebug`; never reset or
  clean it.
- ADGFuzz has pre-existing modified runtime state/log/tlog/parm files and
  untracked core, stack, cache, log, and quick-result artifacts; preserve all.
- PGFuzz has pre-existing `__pycache__` and an untracked paper copy; preserve.
- MightyPPL/MoniTAal and existing analysis/test outputs contain user changes;
  do not revert them. They are read-only except for proportionate monitor runs.
- The official wiki sparse checkout is clean at its frozen commit; do not pull
  or silently update it.

## Current Blockers And Honest Boundaries

- FGS FSE 2024's Zenodo record currently exposes only a README pointing to an
  unavailable `rmrepo/fgs:latest`; smoke and NIST-846 were not run. It remains
  a method-level comparison, not an executed runtime baseline.
- Mechanical templates provide exact synthetic ground truth. Real-project
  labels still require two independent human reviewers and arbitration; that
  requirement must not be marked complete by an agent.
- M2's deterministic async cases model queue/timer/callback stages but do not
  replace real scheduler, thread, object-lifecycle, or framework-model tests.
- Portability is a hard result: the same core binary/schema must run on at
  least three independent C/C++ projects with zero core changes. libcoap,
  MAVLink, ArduPilot, and MQTT knowledge must remain external model packs.

Prior benchmark boundaries:

- ArduPilot wiki `MAIN_ONLY` is not release-paired with the frozen SUT; each
  accepted property must record and review that version relationship.
- Current candidates are deterministic recall output, not exhaustive human
  adjudication. Accepted properties require context/exception/time/AP gates.
- Runtime parameter and message evidence now exists. ArduPilot's authoritative
  traffic is decoded JSONL because auxiliary tlog/raw hooks were empty; PX4 has
  nonempty tlog and JSONL.
- Records remain intentionally not `ACCEPTED`: parser/trace validation,
  context conflicts, and final independent review are open Milestone-7 gates.
- Hardware firmware/runtime validation is out of current scope; no specific
  flight-controller board or ARM toolchain is available.

## Next Steps

1. Implement and evaluate the six RIFT-M3 weak baselines against the frozen M2
   schema before writing the novel core.
2. Run MITL Milestone 7 parser/trace/independent-review gates without
   assessing firmware conformance or running a fuzz campaign.
3. Produce final `METHOD.md` / `RESULTS.md`, accepted/candidate/auxiliary/
   rejected counts, unresolved items, commands, and delivery links.

## Recovery Prompt

```text
发生上下文压缩或任务恢复时，先读 /home/lqq/project/TAFuzz/AGENTS.md、/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md、/home/lqq/project/TAFuzz/.codex/SESSION_LOG.md、benchmark/rift/reproduction/README.md、benchmark/rift/gold/README_zh.md 和 benchmark/rift/README.md。RIFT-M0/M1/M2 已完成且 M3 弱基线仍是下一步；FGS 仍 BLOCKED。MITL M1--M6 已完成：四个 COMPLETE captures、4,999 参数行、1,307 profile×message 行、15 参数实例、8 个 CONCRETE_UNVALIDATED 公式，M6 aggregate 1035 checks/0 failures。下一步只进入 M7 parser/trace/independent review，并生成 METHOD/RESULTS；不得作固件合规结论、不得运行完整 fuzz campaign、不得由实现流产生或改写性质，也不要清理用户既存修改。
```
