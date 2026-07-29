# PX4 v1.17 Milestone-6 runtime capture

Status: **FAILED**. This is an observation artifact only; implementation satisfaction is **NOT_ASSESSED**.

## Frozen target and launch

- PX4 commit: `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- MAVLink commit: `33af200d25ec6f0925b49b1ba82bbf1294ea5f72`
- Vehicle/profile: `px4_sitl_default`, multicopter `none_iris`, headless, instance 42
- PX4 command: `/home/lqq/project/TAFuzz/baseline/px4/build/px4_sitl_default/bin/px4 -i 42 -d /home/lqq/project/TAFuzz/baseline/px4/build/px4_sitl_default/etc`
- PX4 working directory: `/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/runtime_state`
- MAVLink connection: `udpout:127.0.0.1:18612`, collector SYSID/COMPID `250:190`
- Observed autopilot SYSID/COMPID: `None:None`

## Phase separation

1. **BASELINE**: 12.0 seconds after the first autopilot heartbeat, with only the collector GCS heartbeat and no parameter/message request.
2. **PARAMETER_DOWNLOAD**: one `PARAM_REQUEST_LIST`, followed by named `PARAM_REQUEST_READ` probes for the required property/selector/action/exception parameters.
3. **REQUEST_SWEEP**: `MAV_CMD_REQUEST_MESSAGE (512)` sent serially for all 243 unique message IDs generated from frozen `development.xml`.

Startup traffic before the first autopilot heartbeat is labelled `STARTUP` and is not counted as baseline.

## Observed result

- MAVLink messages: 0 across 0 distinct ID/name pairs.
- Baseline distinct messages: 0.
- PARAM snapshot: FAILED; expected None, unique indices 0, unique names 0, missing indices 0.
- Required named parameters observed: 0/18.
- Request sweep: FAILED; attempted 0/243, matching message observed for 0, unsupported ACK for 0, no ACK/no matching frame for 0.
- PX4 exit code: 255; isolated process cleanup: True.
- PX4 source HEAD unchanged and worktree clean after run: True.

## Primary evidence

- `manifest.json`: schema-oriented capture manifest and artifact hashes.
- `mavlink_messages.jsonl`: every decoded frame with raw hex, phase, host monotonic/wall arrival time, SYSID/COMPID, fields, and onboard-time fields.
- `mavlink_capture.tlog`: MAVLink frames with standard wall-clock tlog prefixes.
- `message_inventory.json`: per ID/name/phase counts, field names, first/last host arrival, onboard-time samples, and SYSID/COMPID counts.
- `parameters_runtime.json`: full observed runtime PARAM snapshot, raw wire float bits, PX4 bytewise decoded values, type/index/count, source IDs, and key named-request results.
- `message_request_sweep.json`: one record per frozen dialect message ID with ACK, matching-frame window, latency, baseline count, and causal-attribution caveat.
- `px4.stdout.log` / `px4.stderr.log`: exact PX4 process output.
- `process_lifecycle.json`: spawned PID/PGID identity, signals, exit code, process-group cleanup, port release, and exact instance temp-object cleanup.
- `source_integrity.json`: HEAD, worktree, and recursive submodule snapshots before/after.

## Limitations

- This is runtime acquisition only; implementation/property satisfaction is NOT_ASSESSED.
- PX4 used the none_iris multicopter airframe without an external physics simulator; no arming, takeoff, or flight path was attempted.
- Host CLOCK_MONOTONIC_NS arrival time is not substituted for PX4 onboard time fields.
- MAV_CMD_REQUEST_MESSAGE COMMAND_ACK identifies command 512 but not the requested message ID; correlation is sequential and temporal.
- A matching frame after a request is not asserted causal when that message was already present in BASELINE.
- No PARAM_SET, stream-interval change, arming command, mode command, or actuator command was sent.
- Capture encountered an exception recorded in capture_details.json and capture_driver.log.
- PARAM download was FAILED; expected=None, missing_indices=0.
- Required runtime parameters not observed: COM_RC_LOSS_T, COM_RC_IN_MODE, COM_RCL_EXCEPT, NAV_RCL_ACT, COM_DL_LOSS_T, COM_DLL_EXCEPT, NAV_DLL_ACT, COM_OF_LOSS_T, COM_OBL_RC_ACT, COM_DISARM_LAND, COM_DISARM_PRFLT, COM_FLT_TIME_MAX, RTL_LAND_DELAY, RTL_TYPE, RTL_DESCEND_ALT, MAV_SYS_ID, MAV_TYPE, SYS_AUTOSTART
