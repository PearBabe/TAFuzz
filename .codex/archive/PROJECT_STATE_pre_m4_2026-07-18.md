# TAFuzz Project State

Last updated: 2026-07-18 08:48 CST.

## Current Goal And Status

Implement RIFT (Residual-Conditioned Influence Frontier) under
`src/StaticAnalysis`: starting from evidence-bound typed MITL APs, extract
portable C/C++ source influence cones, externally controllable frontiers, and
mutation recipes for later fuzzing.

Status: RIFT-M0, M1, M2, and M3 are complete. RIFT-M4 (portable production
Property IR/AP binding and complete influence cone) is next. The separate
ArduPilot/PX4 MITL property benchmark has completed Milestones 1--7 and its
final evidence gates; it did not overwrite RIFT artifacts.

- M0 froze the method comparison, ten falsifiable H-RIFT hypotheses, baseline
  identities, and portability contract before core implementation.
- M1 passed the benchmark-first gate: original LTL-Fuzzer component, libcoap,
  ArduPilot Clang build, and SVF 3.2 smoke ran; FGS remains honestly blocked by
  its unavailable upstream image.
- M2 froze 120 mechanically labelled C/C++ cases across 12 dependency
  categories; all schema/location/relation and Clang compile/link/run gates
  pass.
- M3 implemented and evaluated six weak baselines with one binary/input/schema:
  ADGFuzz assignment, MoonShine-RW, plain PDG, LLVM SSA, MemorySSA+AA, and
  SVF 3.2 value-flow. No RIFT advantage is claimed from M3.
- MITL-M7 completed formula/trace validation, independent evidence review,
  permalink/link/catalog validation, and final METHOD/RESULTS delivery. A
  post-delivery claims audit then corrected two implementation-semantic bleed
  cases and isolated the superseded PX4 14-candidate draft. No property was
  accepted and no firmware-conformance conclusion was made.

## MITL Benchmark Final State

- Primary entrypoints: `benchmark/METHOD.md`, `benchmark/RESULTS.md`,
  `benchmark/ArduPilot/property_catalog.md`, `benchmark/PX4/property_catalog.md`,
  and `benchmark/MAVLink_ArduPilot_PX4_observability.md`.
- Final corpus products contain 13 properties, 46 typed APs, 227 frozen-source
  bindings, and 77 AP observation rows. Property readiness is 12
  `NEEDS_CONTEXT` plus 1 `CANDIDATE`; `ACCEPTED=0` and all 13 remain
  `implementation_satisfaction=NOT_ASSESSED`.
- AP mapping is 43 `BOUND` plus 3 `PARTIALLY_BOUND`. Observability is 9
  `DIRECT`, 6 `DERIVED`, 12 `CONDITIONAL`, 16
  `INSTRUMENTATION_REQUIRED`, and 3 `UNRESOLVED`.
- Four default SITL captures remain complete: 4,999 runtime parameter rows,
  1,307 profile×static-message rows plus 3 supplemental BAD_DATA observations,
  128 observed time-field rows, and 15 property/profile parameter instances.
- Eight concrete formulas entered the synthetic monitor gate. Six formula
  suites passed, PX4 RC-loss retained one exact-endpoint verdict mismatch, and
  ArduPilot RTL retained six default BDD-limit executions plus a non-closing
  65,536-valuation diagnostic. The 49 primary traces are 42 comparison PASS,
  1 mismatch, and 6 unsupported; all use absolute global millisecond ticks.
- Independent automated review is not a human arbitration. It records the
  version/context/reset/cancel/continuous-condition/AP-observation blockers in
  `benchmark/extraction_runs/milestone7/independent_review.{md,json}`.
- Final aggregate `validate_benchmark.py` passed 89,979 checks with zero
  failures (`--facts-only --skip-subvalidators`: 89,934/0); M6 regression
  passed 1,035 checks; 34 Markdown files/250 local
  targets had zero broken links. Monitor details are under
  `benchmark/extraction_runs/milestone7/monitor_validation/`.

## MITL Post-M7 Semantic And Directory Corrections

- `ARD-COPTER-GCS-001` now derives its trigger/reset only from the official
  designated-GCS heartbeat wording. RC override, manual control, shared
  last-seen state, and aggregate-gap sites are retained only as `MODELLED`
  implementation conflicts.
- `PX4-MC-GCSLOSS-002` remains the source-defined telemetry/data-connection
  loss requirement. Its normative liveness event, recovery identity, and
  clock remain `UNRESOLVED/UNKNOWN`; all heartbeat/HRT input-gap candidates are
  `MODELLED`, not requirement definitions.
- Catalogs now distinguish `evidence_snapshot_at` from
  `stage7_enriched_at/generated_at`. The MAVLink AP observation generator was
  corrected to consume `static_support_matrix.csv`, not the M6 runtime overlay.
- The old PX4 14-candidate YAML set was moved without deletion to
  `benchmark/extraction_runs/milestone4/superseded_px4_draft/`. A 24-file
  manifest fixes every post-isolation byte count and SHA-256; the aggregate validator forbids
  legacy YAML, the old epsilon token, and former in-place YAML references in
  canonical `benchmark/PX4/`. No externally anchored pre-move receipt exists,
  so this proves post-isolation integrity rather than earlier historical identity.
- Final independent read-only review found 26 canonical PX4 files, zero YAML,
  zero legacy paths/tokens, and 24/24 archive members matching 96,182 bytes and
  SHA-256. The archive manifest digest is
  `d748b136cc16dc6d82b10b9c91599cdfd8d96338e72c8b22e4a449915051b032`.
- Main changed implementation/report files:
  `benchmark/scripts/build_property_catalog.py`,
  `benchmark/scripts/build_mavlink_ap_observations.py`,
  `benchmark/scripts/validate_benchmark.py`,
  `benchmark/schemas/catalog.schema.json`, `benchmark/METHOD.md`,
  `benchmark/RESULTS.md`, both generated system catalogs, Milestone-5 binding/
  observation audits, and Milestone-7 independent/link audits.

## Portability Is A Hard Gate

Generic code under `src/StaticAnalysis/{core,include,cli,schema}` may consume
only typed Property IR, compile/LLVM facts, and versioned external model packs.
It must not contain project names, paths, symbols, or per-property expected
edges. Protocol/framework/project knowledge belongs under `model_packs/`.

Final portability requires the same analyzer binary, output schema, canonical
generic-core tree, and verified child-toolchain semantics on at least three
independent C/C++ projects with zero core changes. The evidence validator now
recomputes real artifact hashes; fabricated 64-character digests, non-boolean
change claims, and divergent toolchains are rejected.

Current implementation-phase gate passes, but the real three-project gate has
not run and must not be claimed. M3 is a candidate-given diagnostic, not a
production multi-TU RIFT interface.

## Frozen Identities

- ArduPilot: `/home/lqq/project/TAFuzz/baseline/ardupilot`, commit
  `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`; pre-existing dirty
  `modules/CrashDebug` must remain.
- ArduPilot MAVLink: `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472`.
- PX4: v1.17.0 commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`.
- PGFuzz artifact: `7eaebf21116087249b8329d4ba7337a24a34ecb9`.
- ADGFuzz artifact: `203fce3f4265241340ed62b9be90aec1da0afa37`.
- Full PDF paths/hashes and source revisions are in
  `benchmark/source_freeze_manifest.json`.

## M3 Implementation And Evidence

Core implementation:

- `src/StaticAnalysis/CMakeLists.txt`, `README.md`, and
  `scripts/bootstrap_clang18_headers.sh`.
- `include/rift/baselines/{ast,llvm}/` public APIs.
- `core/baselines/ast/`: assignment, MoonShine-RW, plain PDG and smokes.
- `core/baselines/llvm/`: SSA, MemorySSA+AA, SVF 3.2 and smoke.
- `cli/baseline_main.cpp`: complete result adapter, Clang/LLVM bitcode build,
  failure mapping, binary hashing, and per-case SVF process isolation.
- `tests/cli_regressions.py`: compile-cwd, PATH, tool-error, and repeated-method
  black-box tests.

Evaluation and portability:

- `benchmark/rift/baselines/{prepare_inputs.py,evaluate.py,validate.py}`.
- `benchmark/rift/baselines/run_m3_all.py`: all analyzers finish before private
  evaluation; external GNU-time receipts and hashes are frozen.
- `benchmark/rift/baselines/validate_m3_results.py`: bundle hash/schema/pair/
  core/no-answer checks.
- `benchmark/rift/baselines/results/m3/`: raw results, private evaluations,
  performance, manifest, compressed trace, summary, and `REPORT_zh.md`.
- `benchmark/rift/validate_portability_contract.py` plus
  `portability_tests/`: artifact-backed gate and four deterministic tests.

M3 frozen identity:

```text
analyzer binary SHA-256  ea0c5b10b787f4370ad1e8f00e970d7f87b35332de98dba38bcee762faf8af40
sanitized input SHA-256  076e1f4d333be3e729391d5de0857dbaeee43b7ebef6ef17e2f42fec1257a229
result schema SHA-256    4ded9b571a8a821718025ec4c8fb04480c2192529a47837c235e150ca998e8e3
generic core SHA-256     1adddf78662f22eca07940c00f839421be4bf8359eae119eff5267ffa2694c5b
```

M3 pair-classification diagnostic (202 source×AP pairs):

| Baseline | Status | Precision | Recall | F1 | MUST detection | Unknown |
|---|---|---:|---:|---:|---:|---:|
| ADGFuzz assignment | COMPLETE | 1.000 | 0.607 | 0.755 | 0.697 | 0 |
| MoonShine-RW | UNSUPPORTED | N/A | 0.000 | 0.000 | 0.000 | 202 |
| plain PDG | COMPLETE | 0.974 | 0.740 | 0.841 | 0.818 | 0 |
| LLVM SSA | PARTIAL | 1.000 | 0.347 | 0.515 | 0.515 | 19 |
| MemorySSA+AA | COMPLETE | 0.941 | 0.640 | 0.762 | 0.818 | 0 |
| SVF 3.2 | COMPLETE | 0.940 | 0.627 | 0.752 | 0.879 | 0 |

MoonShine's all-UNKNOWN result is an anchor-interface incompatibility, not a
quality score; its call-anchor smoke and M1 `mlockall→msync` reproduction pass.
Plain PDG's three false positives are retained as an explicit context-
insensitive weak-baseline limitation. Exact graph endpoints remain unprojected
and are not headline metrics.

## Verification Status

- CMake/Ninja Clang++ 18 build passed; CTest passed 8/8.
- `benchmark/rift/baselines/validate.py --jobs 8` passed two schemas, seven
  evaluator tests, 120 sanitized compilations, dummy metrics, and strace:
  `failures=0`.
- `validate_m3_results.py` passed 6 methods, 720 case results and 1,212 pair
  predictions, with one binary/input/core identity.
- Final analyzer no-answer scan passed 23 files. Runtime strace passed 526
  observed paths and zero violations after explicitly allowlisting only fixed
  analyzer/toolchain/compiler-probe roots.
- `validate_gold.py --jobs 8` passed 120/120 schema/location/relation and
  Clang compile/link/run checks with deterministic regeneration.
- Portability `--phase implementation` passed; four artifact-backed gate tests
  passed. The three-real-project evaluation remains NOT_RUN.
- M3 external performance: ADG 0.89 s, MoonShine 0.93 s, PDG 0.93 s, LLVM SSA
  7.18 s, MemorySSA 4.68 s, SVF 40.21 s; peak RSS 89--109 MiB.

## Honest Boundaries And Blockers

- M3 receives candidate source/AP anchors and controllability; discovery,
  automatic AP binding, and frontier precision are not measured.
- M2 is exact synthetic ground truth. Real-project labels still require two
  independent human reviewers and arbitration; agents cannot mark that done.
- FGS remains `BLOCKED_UPSTREAM_ARTIFACT_UNAVAILABLE`.
- Current production gaps: no typed Property IR/model-pack schemas or loader,
  no raw compile-DB multi-TU index, no CIG/cone/frontier/recipe/certificate
  pipeline, and no real three-project portability evidence.
- No conformance verdict or full fuzz campaign has been performed. TAMonitor
  was run only on synthetic AP valuations to test formula encoding/endpoints;
  no firmware property trace was evaluated.

## Local Changes To Preserve

- Root workspace is not a Git repository; do not run root-level Git commands.
- ArduPilot remains at the frozen commit with pre-existing CrashDebug and
  runtime/log artifacts; never reset or clean them.
- ADGFuzz runtime/log/tlog/parm/cache/core artifacts and PGFuzz caches/paper
  copy are pre-existing user state; preserve them.
- MightyPPL, MoniTAal, TAMonitor, analysis and test outputs contain user changes;
  do not revert them. RIFT work must not modify nested tool repositories.

## Next Steps

1. RIFT-M4: freeze production schemas and implement project-neutral raw
   compile-DB index, typed joint AP binding, CIG, and complete conservative
   influence cone; reach 100% must-dependency recall on microbench/libcoap.
2. RIFT-M5: implement declarative model-pack VM, external frontier,
   bidirectional confirmation, SMT direction/prerequisite/timing recipes, and
   minimize every failure into a regression.
3. Then run RIFT-M6 protocol transfer and RIFT-M7 ArduPilot GCS-failsafe
   validation before any RIFT-M8 fixed-budget fuzz comparison or M9 advantage
   claim. The separate MITL benchmark M7 is already complete.

## Recovery Prompt

```text
先读 /home/lqq/project/TAFuzz/AGENTS.md、.codex/PROJECT_STATE.md、.codex/SESSION_LOG.md、benchmark/rift/baselines/results/m3/REPORT_zh.md、benchmark/rift/README.md、benchmark/METHOD.md 和 benchmark/RESULTS.md。RIFT-M0--M3 已完成；下一步是 RIFT-M4 project-neutral production core。MITL benchmark M1--M7 及最终 claims 纠偏已完成：13 properties/46 AP/227 bindings/77 observations，43 BOUND+3 PARTIALLY_BOUND，12 NEEDS_CONTEXT+1 CANDIDATE，ACCEPTED=0，6 formula suites pass/1 endpoint mismatch/1 RTL unsupported，89,979 checks/0 failures，始终 NOT_ASSESSED。Ardu GCS 只采用指定 heartbeat 规范语义；PX4 data-link liveness/clock 保持 unresolved；旧 PX4 14-YAML 草案已按 24-file hash manifest 隔离归档。不得在 generic core 写项目名/符号/路径，不得提前实现 property-specific model edge，不得声称三项目 portability、性质人工接受或飞控符合性已通过。每个里程碑结束必须更新 PROJECT_STATE 和追加 SESSION_LOG，并保留 ArduPilot/ADGFuzz/PGFuzz/MightyPPL/MoniTAal 既存改动。
```
