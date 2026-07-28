# TAFuzz Project State

Last updated: 2026-07-20 CST (PGFuzz dynamic migration M4 delivered).

## Current Goal And Status

Current focus: implement a Python 3 migration of PGFuzz's ArduPilot dynamic
input-to-state profiler for the frozen current ArduCopter SITL. The adapter must
discover current parameters/commands/environment inputs, preserve PGFuzz's
15-file text interface, add typed evidence and robust effect classification,
and stop after three representative smoke tests. The user, not Codex, will run
the full `current_safe_full` campaign.

Status: **PGFuzz dynamic migration M0--M4 are complete. The final unified
three-case smoke certificate is `PASS`; implementation, compatibility files,
structured evidence, recovery/restart behavior, sequential sharding, user
manual and full-campaign handoff are delivered. Codex did not run the full
campaign; the user may now execute it. PGFuzz-MTL51 remains complete and
RIFT-M5 remains paused.**

## PGFuzz Dynamic Migration M4 Complete

- Added `src/StaticAnalysis/runtime/pgfuzz_adapter/README.md`, a Chinese user
  manual covering terminology, dependency checks, live catalog construction,
  dry-run audit, exact-name single-input selection, sequential eight-shard
  execution, resume, output evidence, limitations, and a complete
  `FS_GCS_TIMEOUT` example.
- Added `requirements.txt`, freezing the accepted `pymavlink==2.4.49`; the
  accepted host interpreter was Python 3.10.12.
- Hardened full-campaign execution after delivery audit: every input and
  restoration must verify across all repetitions; failed verification is
  `INCONCLUSIVE` and restarts SITL. Checkpoints distinguish global plan size,
  current shard size and cumulative completions.
- Added append-only `experiment_plans.jsonl`, manifest fields that distinguish
  dry-run, partial execution and true global completion, and persistent session
  numbering across separate `--resume` invocations so prior logs are not
  overwritten. Same-directory concurrent shard writes remain intentionally
  unsupported and are documented; use sequential shards for one cumulative
  result.
- State windows now preserve ranges/counts for message-provided onboard time
  fields alongside host monotonic window boundaries. The clock boundary remains
  explicit: host receipt is not internal firmware event time.
- Smoke outputs now include root `trials.jsonl` (nine repetitions),
  `checkpoint.json`, smoke-aware `manifest.json`, exact protocol field
  identities, and all required compatibility files.
- Final accepted run is
  `output/pgfuzz_dynamic/smoke-acceptance-final-20260720/`. Certificate `PASS`:
  `SIM_BATT_VOLTAGE -> status`, `RC1 -> roll`, and
  `FS_GCS_TIMEOUT -> status`, each with three repetitions and confirmed
  restoration. `results/roll.txt` is exactly `RC1`; `results/status.txt` is
  exactly `FS_GCS_TIMEOUT` and `SIM_BATT_VOLTAGE`.
- Final validation: 20 unit tests passed; 20 JSON and four JSONL files parsed;
  15 confirmed plus 15 legacy result filenames matched exactly; artifact
  assertions, recovery assertions and no-process check passed. All five PGFuzz
  upstream blob identities, target commits and ArduCopter binary SHA-256 still
  match the M0 manifest. Adapter bytecode caches were removed.
- Preservation: ArduPilot still has only the pre-existing
  `modules/CrashDebug` state; PX4 is clean; PGFuzz retains its pre-existing
  `.pyc`, cache, PDF and SVF-data-flow artifacts. None were reset or cleaned.
- Full campaign was not executed. Blockers: none. Next steps are user-owned:
  create a fresh live catalog, inspect `--dry-run`, then execute shards 0--7
  sequentially with `--resume` as documented.

## PGFuzz Dynamic Migration M3 Complete

- Added the three gated smoke workflows in `tafuzz_pgfuzz/smoke.py`: paired
  ground battery-voltage intervention; normal-check airborne RC1 override;
  and airborne GCS-failsafe latency comparison with parameter/precondition
  restoration. All use three repetitions and explicit input confirmation.
- The first RC run correctly failed before intervention because normal pre-arm
  checks reported inconsistent accelerometers and AHRS waiting for home. The
  implementation now waits and retries for a bounded 50 seconds while keeping
  normal checks enabled; no force-arm value is used. The failed run remains at
  `output/pgfuzz_dynamic/smoke-command-20260720-1/`.
- Confirmed current RC release semantics from
  `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp`: zero releases the
  first eight channels used here. The GCS identity now defaults to system ID
  255, matching current `MAV_GCS_SYSID`, and each timed trial first clears the
  prior 3 Hz GCS-failsafe state.
- Added the exact protocol field
  `RC_CHANNELS_OVERRIDE.chan1_raw` to JSON/CSV structured evidence while
  retaining PGFuzz's unprefixed `RC1` compatibility name in `cmds.txt` and
  `results/roll.txt`.
- Earlier unified acceptance run:
  `output/pgfuzz_dynamic/smoke-acceptance-20260720-1/`. Its
  `smoke_certificate.json` is `PASS`: `SIM_BATT_VOLTAGE -> status`,
  `RC1 -> roll`, and `FS_GCS_TIMEOUT -> status` are all
  `CONFIRMED_EFFECT` and present by exact name in the expected files.
- `FS_GCS_TIMEOUT` baseline/mutation/recovery observed latencies were about
  5.25/2.31/5.30, 5.29/2.31/5.30, and 5.30/2.31/5.30 seconds. These are host
  harness observations, not internal firmware event timestamps.
- All requested recoveries passed: battery parameter readback, RC release,
  landing/disarm, `FS_GCS_TIMEOUT`, `FS_GCS_ENABLE`, and `FS_OPTIONS` restore.
  `ps -C arducopter` returned no process after acceptance.
- This was superseded by the M4 final acceptance after evidence/recovery
  hardening. Individual passing reruns are preserved at
  `smoke-environment-20260720-1`, `smoke-command-20260720-2`, and
  `smoke-parameter-20260720-1`.
- No full campaign ran. Blockers: none before M4 documentation/handoff.

## PGFuzz Dynamic Migration M2 Complete

- Added `states.py`, `metrics.py`, `compat.py`, `engine.py`, and `report.py`.
  The state layer reproduces the original 34 raw values and fifteen groups,
  preserves the original standard-deviation predicate, and separately records
  current numeric/categorical state features.
- Added isolated baseline/treatment/recovery windows, raw MAVLink JSONL traces,
  parameter readback, RC override/release, mode confirmation, typed command
  ACK handling, recovery checks, checkpoint/resume, deterministic sharding and
  exact-name compatible result regeneration.
- `results/*.txt` receives only `CONFIRMED_EFFECT`; `results_legacy/*.txt`
  receives the original PGFuzz predicate. Both directories always contain the
  same fifteen filenames and one unprefixed identifier per line.
- Reduced `READY_SAFE` command recipes to the two actually implemented safe
  commands (`MAV_CMD_COMPONENT_ARM_DISARM`, `MAV_CMD_DO_SEND_BANNER`). Other
  source-handled commands remain visible but fail closed as requiring a typed
  precondition/recipe; they are not sent with random arguments.
- Thirteen unit tests pass, covering runtime-authoritative catalogs, exact
  identifier semantics, migration states, legacy threshold, repeat-direction
  aggregation, compatibility files, selection and disjoint sharding.
- A no-input `--dry-run` on shard 0/8 generated 668 work items. It created the
  state registry and all 30 compatible result files without opening a socket
  or executing an input. `report.md` was generated successfully.
- Dynamic execution has not yet been accepted: M3 must run the three gated live
  smoke cases and may expose runtime regressions.
- Blockers: none before M3.

## PGFuzz Dynamic Migration M1 Complete

- Added Python package and stable entry point under
  `src/StaticAnalysis/runtime/pgfuzz_adapter/`, including current parameter
  metadata merge, command/source intersection, mode/RC discovery, safety
  classification, legacy migration report, isolated SITL ownership, and
  compatibility input files.
- Added transparent policy `data/safety_policy.json` and five catalog unit
  tests. All five pass with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest
  discover -s src/StaticAnalysis/runtime/pgfuzz_adapter/tests -v`.
- Offline end-to-end check generated 1,025 `INPUT_P`, 362 `INPUT_E`, and 135
  `INPUT_C` rows from the previous complete snapshot.
- Fresh live run `output/pgfuzz_dynamic/catalog-current-20260720-v2/` completed
  a new `PARAM_REQUEST_LIST/PARAM_VALUE` download: 1,387/1,387 unique indices,
  zero missing. It generated 1,025 `INPUT_P`, 362 `INPUT_E`, and 136 `INPUT_C`
  rows, including 27 runtime-advertised modes.
- Execution classes: 823 `READY_SAFE`, 382 `UNKNOWN_METADATA`, 197
  `REQUIRES_RESTART`, 87 `REQUIRES_PRECONDITION`, and 34
  `DISRUPTIVE_EXCLUDED`. These are catalog classifications, not evidence that
  every ready input changes a state.
- Legacy migration: 172 `EXACT`, 17 `RENAMED`, 43 `REMOVED`; no ambiguous row
  in this current catalog. Four of five old preconditions map to current names.
- First live attempt was blocked by sandbox UDP permissions; the approved
  rerun exposed and fixed an invalid pymavlink dialect lookup. The successful
  run ended the SITL process with SIGTERM (`return_code=-15`) and `pgrep`
  found no residual ArduCopter process.
- Blockers: none at M1.

## PGFuzz Dynamic Migration M0 Complete

- New implementation root:
  `src/StaticAnalysis/runtime/pgfuzz_adapter/`.
- Added `UPSTREAM_COMPATIBILITY.md` and
  `data/upstream_manifest.json`.
- Verified the five local PGFuzz dynamic files match the upstream Git blob
  identities: README `ccf24c...`, commands `e106b7...`, environment
  `f31969...`, preconditions `5a9fd9...`, profiler `750865...`.
- Frozen ArduPilot `8f2e5db2...`, MAVLink `13f2f735...`, PGFuzz
  `7eaebf2...`, and ArduCopter binary SHA-256 `cc678abb...7715`.
- Compatibility contract fixes `cmds.txt`, `envs.txt`, `preconditions.txt`,
  added `params.txt`, and the exact fifteen `results/*.txt` plus
  `results_legacy/*.txt` files. Each result remains one unprefixed input name
  per line; exact identifier equality replaces the upstream substring
  de-duplication bug.
- Verification: manifest parses with `python3 -m json.tool`; compatibility
  document is nonempty; all five local Git blob hashes were rechecked.
- Blockers: none at M0.

Standing communication requirement: `AGENTS.md` now requires Chinese-first,
term-by-term explanation of every newly introduced English technical term,
acronym, status/field value, tool name, and file format. Exact machine-readable
identifiers remain unchanged but must have adjacent Chinese meaning and
task-specific interpretation in reports and handoffs.

## PGFuzz-MTL51 Current Dataset Task

- Canonical new root: `benchmark/PGFuzz_MTL51/`; the existing evidence-first
  13-property benchmark remains untouched and separate.
- Scope is PGFuzz PDF page 18 Table XII: ArduPilot 30 + PX4 21 = 51. ADGFuzz
  PDF page 19 is an artifact appendix, not the MTL formula source.
- M1 froze both PDFs, both artifact repositories, ArduPilot/PX4 commits,
  relevant-tree digests, policy-directory counts, and preservation state in
  `source_manifest.json` and `SCOPE.md`.
- M2 transcribed all 51 Table-XII rows without silently repairing the paper,
  separated printed formulas from binding interpretations and description-only
  conditions, and generated 178 AP occurrences / 99 unique AP expressions.
  `validate_formula_inventory.py` passed 292 checks with zero failures.
- M2 explicitly records the A.FLIP1 polarity/precedence conflict, omitted armed
  condition in A.RC.FS1, reversed implication in A.GPS.FS1, PX.RTL4 parameter
  conflict, PX.ORBIT6 unit/type conflict, omitted PX.HOLD2 altitude condition,
  weakened PX.TAKEOFF1 target equality, and inherited formulas not printed by
  the paper. These are audit findings, not silent formula corrections.
- Every record is a `HISTORICAL_PROPERTY_SEED` with
  `implementation_satisfaction=NOT_ASSESSED`; current-source mapping cannot be
  reported as current official requirement confirmation or conformance.
- M3 reconstructed PGFuzz's manual policy process, LLVM/static `InputP`
  candidate mapping, single-input dynamic `InputC`/`InputE` profiling,
  precondition search, and 100-run empirical `k` procedure. It also documents
  ADGFuzz's assignment-dependency-graph to matched-input-set workflow and the
  paper/artifact algorithm differences.
- M3 expanded all author files into 7,569 property-input associations and 356
  unique current identities. ArduPilot contributes 5,872 associations; PX4
  contributes 1,697. The strengthened `validate_author_dependencies.py`
  currently passes 98,275 checks, including 239 validated current source
  locations, with zero failures.
- M3 preserves candidate correlation rather than claiming proven causality.
  It records duplicate/conflicting artifact rows, deleted or renamed current
  parameters, formula-direct parameters omitted by the author lists, and the
  incompatibility between PGFuzz's PX4 small-integer `Flight_Mode` encoding
  and current packed PX4 `custom_mode` encoding.
- M4 completed current-source proposition binding after independent semantic
  audit corrections: 227 binding rows cover 107 system--term identities and
  all 178 AP occurrences. The split is 110 ArduPilot rows and 117 PX4 rows;
  AP results are 57 `EXACT`, 107 `MODELLED`, and 14 `UNRESOLVED`, while every
  conformance field remains
  `implementation_satisfaction=NOT_ASSESSED`.
- M4 now separates `PRIMARY_VALUE`, `SUPPORTING_EVIDENCE`, and
  `ALTERNATIVE_SEMANTICS`; candidate groups prevent mutually exclusive
  interpretations from being treated as simultaneous truth conditions.  APs
  record selected and alternative binding identifiers plus selection reasons.
- M4 added the formation/consumption/sending paths needed for Home, parachute,
  GPS, vertical speed, roll direction, PX4 altitude frames, orbit direction,
  RC, command stages, and parameter consumers.  The numeric PX4
  `ALT_t = GroundALT` interpretation stays unresolved, and removed
  `COM_POS_FS_DELAY` is not replaced by `EKF2_NOAID_TOUT`.
- `validate_source_bindings.py` passed 11,700 checks with zero failures. It now
  checks full source-line ranges, nonempty selection reasons, structured
  MAVLink observation references, current/previous semantic-group pairing,
  critical function identities, and both non-equivalent current candidates
  for removed PX4 `COM_POS_FS_DELAY`. It also proves exact coverage of all 196
  distinct source-binding and current-input type/unit original values by the
  Chinese `TYPE_UNIT_DICTIONARY`. The
  preservation audit confirmed PX4 clean, ArduPilot changed only at the
  pre-existing `modules/CrashDebug`, and PGFuzz/ADGFuzz plus MightyPPL/MoniTAal
  retained their pre-existing artifacts and edits.

## PGFuzz-MTL51 Milestone 5 Complete

- Generated 51 paired per-property records under `ArduPilot/properties/` and
  `PX4/properties/`: `JSON` is the machine-readable JavaScript Object Notation
  format, while `Markdown` is the lightweight human-review text format.
- Each record losslessly joins its paper wording and printed formula, formula
  audit issues, 178 AP occurrences, selected/alternative current-source
  bindings, 7,569 author candidate associations, 356 current input identities,
  20 formula-parameter rows, current runtime snapshots, MAVLink observation
  guidance and 23 official-document context records.
- Added `RESULTS.md`, `FIELD_DICTIONARY.{md,json}`, the Draft-07 JSON record
  schema, deterministic record builder, and independent record validator.
  The field dictionary explains all 221 unique machine keys in Chinese and is
  now a mandatory exact-set validation input.
- Added `TYPE_UNIT_DICTIONARY.{md,json}` with Chinese explanations and audit
  effects for 100 source data-type values, 61 unit/coordinate values, 7 current
  input types and 28 current input units; all 196 rows exactly match their two
  source datasets, including explicitly explained missing-value states.
- Corrected default-value and runtime-observation provenance: seven unique
  ArduPilot formula parameters use curated frozen-source default evidence;
  raw catalog expressions remain preserved; same-suffix alias mismatches no
  longer import unrelated type/default/range metadata; observed runtime
  parameter downloads are distinguished from protocol-only capability.
- `validate_property_records.py` passes 11,096 checks with zero failures. It
  validates all 51 records against the schema, checks lossless joins, source
  ranges, conservative time semantics, official document roles, default-value
  evidence, catalogs, and exact coverage by the 221-entry Chinese field
  dictionary. `PASS` means automated consistency only; all implementation
  satisfaction remains `NOT_ASSESSED` (not assessed).
- Final validation is green with zero failures: formula inventory 292 checks,
  author dependencies 98,275, source bindings/type-unit dictionary 11,700,
  per-property records/field dictionary 11,096, and local links across 65
  Markdown files / 16,366 local links / 16,054 source-line links.
- Final preservation audit found the expected frozen heads: ArduPilot
  `8f2e5db2...` with only pre-existing `modules/CrashDebug`, PX4
  `d6f12ad1...` clean, PGFuzz `7eaebf2...` with its prior PDF/cache files, and
  ADGFuzz `203fce3...` with its prior runtime artifacts. MightyPPL/MoniTAal
  existing user changes remain present and were not reset or cleaned.

## Paused RIFT-M5 And Headline Target Freeze

- The user narrowed the headline real-project scope to **ArduPilot Copter and
  PX4 SITL**.  Both must use one unchanged project-neutral analyzer core,
  schema bundle, typed-transfer semantics, and verifier.  Target knowledge is
  restricted to typed Property IR plus property-independent declarative
  framework packs.
- Frozen AP projections are
  `benchmark/rift/flight_controllers/ardupilot/gcs_failsafe_ap_property_ir.json`
  and
  `benchmark/rift/flight_controllers/px4/gcs_connection_lost_ap_property_ir.json`.
  They bind canonical state writes for dependency analysis; they are not full
  temporal-property or firmware-conformance replacements.
- The reboot removed both complete `/tmp` build databases.  ArduPilot's 1,336
  TU Clang 18 database remains recoverable from the persistent compressed
  snapshot
  `benchmark/rift/reproduction/ardupilot/clang18_compile_commands.json.gz`
  (archive SHA-256 `134e1dc5...23236a`).  PX4's successful 868-entry / 826
  unique-TU build identity remains recorded in
  `benchmark/rift/flight_controllers/px4/clang18_build_manifest.json`, but its
  temporary database must be rebuilt before the full-target run.
- Three-TU receipts for early probes explicitly claim
  `SELECTED_TRANSLATION_UNITS_ONLY`; they cannot be reported as full-project
  evidence.  PX4's selected receipt now derives from the Clang 18 database.
- At the frozen 18:09 checkpoint, the M5 model-pack VM, controllable frontier,
  recipes, timing/joint schema, certificate verifier expansion, and evaluator
  regressions were under integration. The property-independent typed value-transfer sidecar and the
  new one-coordinate payload projection compile; the dedicated payload
  projection smoke test passes.  Recipe code now accepts the typed sidecar and
  rewrites supported affine expressions into the external coordinate, but the
  recipe smoke suite is currently red because its fixtures and the production
  CLI still call the fail-closed legacy overload.  No sealed M5/full-target
  result is claimed at this checkpoint.
- A soundness audit rejected treating generic CIG data edges as value identity.
  Actionable direction must instead prove the chain `one external payload
  coordinate -> exact typed transfer DAG -> contextual path -> AP predicate`,
  with unknown alternatives and unresolved scope/generation failing closed.

## ADGFuzz Paper/Current-Artifact Focused Audit

- Rechecked the 19-page NDSS 2026 PDF (SHA-256 `bb86bc31...ed72`) against the
  current GitHub `main` head and local frozen checkout; all resolve to ADGFuzz
  commit `203fce3f4265241340ed62b9be90aec1da0afa37`, and the inspected README,
  `tree_parse.py`, and `Mapping.py` blob identities match the connector copies.
- The ADG scans recognized `.cpp` function bodies and assignment left/right
  textual names; it does not retain C++ data types. Numeric and Boolean values
  can both occur as nodes, but literal numbers and `true`/`false` are removed,
  operators/guards are discarded, and a leaf is only the parser's intrafunction
  dependency frontier—not proof of an externally controllable input.
- The paper's executable input universe is configuration parameters, MAVLink
  commands, and simulated environmental data. Current mapping code also emits
  RC candidates. In practice `SIM_*` values are injected as ordinary parameter
  writes; the standalone `envset` catalog/executor is only a stub, and the RC
  call misbinds its two arguments and returns before sending an override.
- A read-only reproduction of the supplied `s_finished` ADG found 17 leaf-list
  entries (16 unique names) and 7 intermediate nodes; name mapping expanded it
  to 276 candidates (254
  parameters, 22 commands), including 31 `SIM_*` entries. This demonstrates
  high-recall semantic fan-out, not confirmed value-flow causality.

## PGFuzz Three-Input ArduPilot Ingress Audit

- Added `analysis/pgfuzz_ardupilot_three_input_paths_zh.md`, separating
  PGFuzz's semantic `InputP`/`InputC`/`InputE` categories from their four
  concrete MAVLink message paths: `PARAM_SET`, `COMMAND_LONG`, `SET_MODE`, and
  `RC_CHANNELS_OVERRIDE`.
- Current-source evidence proves commands and `SIM_*` environmental parameters
  do enter ArduPilot. The limitation is PGFuzz's chosen parameter-rooted SVF
  value-flow model, not an inability to pass those values into source code.
- Traced representative consumers for `FS_THR_VALUE`, takeoff, mode changes,
  RC overrides, `SIM_WIND_SPD`, and GPS satellite count. This is a read-only
  source mapping; no simulator run or current firmware conformance claim was
  made.

The previous detailed pre-M4 state is archived at
`.codex/archive/PROJECT_STATE_pre_m4_2026-07-18.md` (SHA-256
`f1941f6ed6cadce4db920673f98b2d1bba24ebc1838eee2e9dd2592082f5a98b`).

## Paused RIFT Context

RIFT-M5 is frozen at the 18:09 checkpoint. Its detailed M4 history is already
archived in `.codex/archive/PROJECT_STATE_pre_m4_2026-07-18.md`; do not resume
or reinterpret RIFT results until the user completes this dataset task and
issues the next static-analysis instruction.

## Local State To Preserve

- Root workspace is not a Git repository. Do not run root-level Git commands.
- ArduPilot is frozen at `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
  with pre-existing dirty `modules/CrashDebug`; never reset/clean it.
- PX4 is frozen at `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`.
- ADGFuzz runtime/log/tlog/parm/cache/core artifacts and PGFuzz caches/paper are
  user state. Preserve them.
- `tool/MightyPPL` and `tool/MoniTAal` are independent nested Git repositories;
  do not modify them for RIFT.
- Never use or reinstall `academic-research-suite` or any `superpowers:*`
  skill.

## Next Steps (At Most Three)

1. Run and stabilize `SIM_BATT_VOLTAGE` environment-input smoke with verified
   voltage state change and restoration.
2. Run and stabilize airborne RC1 and temporal `FS_GCS_TIMEOUT` smoke cases,
   minimizing each failure into a regression first.
3. Seal the smoke evidence and then write the user manual; do not run the full
   `current_safe_full` campaign or resume RIFT-M5.

## Recovery Prompt

```text
先读 /home/lqq/project/TAFuzz/AGENTS.md、.codex/PROJECT_STATE.md、.codex/SESSION_LOG.md，以及 benchmark/PGFuzz_MTL51 下的 README.md、RESULTS.md、GLOSSARY.md、FIELD_DICTIONARY.md、TYPE_UNIT_DICTIONARY.md、SOURCE_BINDING_GUIDE.md、DEPENDENCY_METHOD_AND_WORKFLOW.md 和 validation 报告。PGFuzz-MTL51 已完成：51 条性质记录、178 个 AP、227 条当前源码绑定、7,569 条作者候选输入关联、356 个当前输入身份、221 个逐项中文解释的机器字段和 196 个逐项中文解释的类型/单位原值。五个验证器均零失败：公式 292 项、依赖 98,275 项、源码绑定/类型单位 11,700 项、逐性质/字段字典 11,096 项、本地链接 65 个 Markdown/16,366 个链接。所有性质保持 implementation_satisfaction=NOT_ASSESSED，不得由源码反推规范、补写时间值或声称固件符合。RIFT-M5 保持 18:09 暂停，等待用户下一条静态分析指令。
```
