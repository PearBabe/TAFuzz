# RIFT flight-controller target freeze

This directory is the headline real-project validation scope for RIFT.  The
same analyzer binary, production-core digest, schema bundle, typed-transfer
semantics, and certificate verifier must be used for both targets.  Target
knowledge is input data only: typed Property IR, versioned declarative model
packs, and executor-capability manifests.

## Frozen targets

| Target | Frozen revision | Primary property | Full compile database |
|---|---|---|---|
| ArduPilot Copter | `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` | `ARD-COPTER-GCS-001` designated-GCS timeout | `/tmp/rift-ardupilot-clang/build/sitl/compile_commands.json`, 1,336 Clang 18 TUs |
| PX4 SITL | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` | `PX4-MC-GCSLOSS-002` GCS data-link loss | `/tmp/rift-px4-clang-v1/build/compile_commands.json`, 868 entries / 826 unique TUs, Clang 18 |

The PX4 Clang build identity and its explicit evidence boundary are recorded in
`px4/clang18_build_manifest.json`.  The build and compile database are complete
inputs for a future full-project analysis, but creating them is not itself an
AP-binding, influence, recipe, or runtime-validation result.

The existing requirement records under `benchmark/ArduPilot` and
`benchmark/PX4` remain the normative/evidence source.  They are monitor
validated but are not firmware-conformance verdicts and currently have no
human-accepted implementation labels.

## ArduPilot dependency question

For the AP `gcs_failsafe_event`, the analysis must recover, or explicitly mark
unknown, the paths through:

- `Copter::set_failsafe_gcs(bool)` and `failsafe.gcs`;
- the strict timeout guards in `Copter::failsafe_gcs_check()`;
- `AP_HAL::millis()`, designated-GCS last-seen time, and the 3 Hz check cadence;
- `FS_GCS_TIMEOUT`, failsafe enable/action/options, armed state, and mode;
- MAVLink heartbeat `sysid`, `SYSID_MYGCS`, initial-seen prerequisite, pause,
  recovery, and the shared-last-seen implementation conflict.

Source anchors are frozen in `baseline/ardupilot/ArduCopter/events.cpp`,
`baseline/ardupilot/ArduCopter/AP_State.cpp`, and
`baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp`.

## PX4 dependency question

For the AP `gcs_connection_lost`, the analysis must recover, or explicitly
mark unknown, the paths through:

- the write and strict timeout guard in `Commander::Run()`;
- `_datalink_last_heartbeat_gcs`, `hrt_elapsed_time`, and `COM_DL_LOSS_T`;
- MAVLink heartbeat decoding, `MAV_TYPE_GCS`, telemetry-status publication,
  subscription, instance identity, and heartbeat/check cadence;
- `NAV_DLL_ACT`, `COM_DLL_EXCEPT`, intended mode, takeoff/land and VTOL guards
  when the downstream failsafe action is requested.

Source anchors are frozen in `baseline/px4/src/modules/commander/Commander.cpp`,
`baseline/px4/src/modules/commander/failsafe/failsafe.cpp`, and
`baseline/px4/src/modules/mavlink/mavlink_receiver.cpp`.

## Portability and evidence gates

1. No ArduPilot/PX4 symbol, path, property ID, answer edge, or expected recipe
   may occur in `src/StaticAnalysis/{core,include,cli,schema}`.
2. A selected-TU probe is reported only as a selected-TU probe.  The final
   portability claim requires the complete frozen compile database for each
   target and accounts for every skipped/failed TU.
3. Every actionable recipe must close the chain
   `external payload -> typed value transfer -> contextual path -> AP predicate`
   and bind its physical artifacts into the M5 certificate.
4. Project adapters may identify stable interfaces and framework semantics but
   must be property-independent.  They may not add an edge solely because it
   is expected for either GCS-loss property.
5. Static `may/modelled/unknown` evidence, executor controllability, and a
   runtime AP flip are separate verdicts.  A static path alone is not reported
   as an experimentally validated recipe.
6. The 120-case corpus and libcoap remain regression/independence guards; they
   are not headline targets and cannot substitute for either flight controller.

## Final comparison axes

The unchanged RIFT run is compared with ADGFuzz-style assignment dependency,
MoonShine read/write conditional dependency, LLVM def-use, MemorySSA+AA, SVF
backward value flow, and plain PDG on the same property anchors.  Report at
least dependency/source recall where labels exist, Top-k actionable precision,
direction accuracy, prerequisite/timing completeness, wall time, peak RSS,
unknown rate, and failure localization.  Real-project gold metrics remain
blocked until two independent humans label and arbitrate them.
