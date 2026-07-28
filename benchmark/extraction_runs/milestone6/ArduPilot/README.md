# ArduPilot Milestone 6 runtime capture

This directory contains read-only runtime evidence from the frozen ArduPilot 
commit `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` and MAVLink commit `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472`.
It does **not** contain a property-satisfaction or conformance conclusion.
Source defaults were not substituted for runtime parameter values.

## Capture phases

Each vehicle was run in an isolated working directory, HOME, port set, and process group:

1. `STARTUP`: passive receive until the expected HEARTBEAT, plus passive warmup.
2. `BASELINE`: at least 12.0s passive traffic with no request.
3. `PARAMETER_DOWNLOAD`: `PARAM_REQUEST_LIST`, with bounded read-only repair requests for missing indices.
4. `REQUEST_SWEEP`: one serialized `MAV_CMD_REQUEST_MESSAGE` (512) for each of the 352 frozen `all.xml` message IDs.
5. `RELEVANT_STREAM_SAMPLE`: selected nonpersistent stream-interval requests followed by timed observation.

Baseline counts are retained separately so a packet seen after a request is not automatically classified as request-caused.

## Results

| Vehicle | Status | Parameters | Baseline message kinds | Request sweep | Observed in window | ACK accepted | ACK failed | Unsupported | No ACK/message | Cleanup |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ArduCopter | COMPLETE | 1387/1387 | 2 | 352 | 45 | 80 | 272 | 0 | 0 | PID gone=True |
| ArduPlane | COMPLETE | 1440/1440 | 33 | 352 | 46 | 82 | 270 | 0 | 0 | PID gone=True |
| Rover | COMPLETE | 1271/1271 | 26 | 352 | 40 | 81 | 271 | 0 | 0 | PID gone=True |

## Evidence layout

For each vehicle under `runs/<Vehicle>/`:

- `command.txt`, `launch.json`, `stdout.log`, `stderr.log`: exact launch and process output.
- `messages.jsonl`: authoritative decoded capture with one host-monotonic record per received message.
- `messages.tlog` and `messages.raw`: logging was requested through pymavlink, but both files remained zero bytes in all three runs. They are retained and hashed as failed/empty auxiliary artifacts; no raw-byte evidence is claimed from them.
- `message_summary.json`: names/IDs/fields/counts, first/last host monotonic arrival, source SYSID/COMPID, phase counts, and vehicle timestamp samples.
- `parameters.jsonl`, `parameters.json`, `required_parameters.json`: complete wire observations and selected property/exception parameters.
- `request_sweep.jsonl`, `request_sweep.json`: per-ID command ACK, window observation, latency, and baseline ambiguity.
- `process_cleanup.json`: exact owned PID/process-group signals, return code, and post-wait absence.
- `runtime/`: isolated EEPROM/DataFlash/SITL state produced by that run.

The full snapshots also establish the current parameter names used by this revision. In particular, vehicle identity is `MAV_SYSID`, serial-0 parameter rate is `MAV1_PARAMS`, and Copter's metric-unit names include `RTL_ALT_M`, `RTL_ALT_FINAL_M`, `LAND_SPD_MS`, and `LAND_SPD_HIGH_MS`. Older aliases that were queried in `required_parameters.json` remain explicitly `NOT_PRESENT`; no default was inserted for them.

`manifest.json` inventories every other file with SHA-256. The manifest cannot include its own hash without recursion; hash it externally when consuming it.

## Preservation checks

- Firmware HEAD before: `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- Firmware HEAD after: `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- Firmware status before: `[' m modules/CrashDebug']`
- Firmware status after: `[' m modules/CrashDebug']`
- Matching SITL processes before: `[]`
- Matching SITL processes after: `[]`

The only pre-existing firmware worktree status was ` m modules/CrashDebug`; it was not modified or cleaned.

## Limits

- Host monotonic arrival time and onboard timestamps remain separate clock domains.
- `COMMAND_ACK` for command 512 has no request sequence; serialized pairing reduces but does not eliminate late-ACK ambiguity.
- ArduPilot answered every command-512 request, but most unsupported/unavailable one-shot messages were reported as `MAV_RESULT_FAILED`, not `MAV_RESULT_UNSUPPORTED`; the exact per-ID result is retained.
- Startup `BAD_DATA` records contain ArduPilot's plain-text serial boot banner before MAVLink framing begins, rather than an inferred message identity.
- The attempted pymavlink tlog/raw hooks produced empty files. The nonempty JSONL traces, message summaries, stdout/stderr, and parameter JSONL are the runtime traffic evidence.
- Unsupported, unobserved, and conditionally emitted messages are retained as results rather than treated as errors.
- These are idle-SITL support observations, not flight-scenario property verdicts.

## Reproduction

```bash
cd /home/lqq/project/TAFuzz
python3 benchmark/extraction_runs/milestone6/ArduPilot/collect_runtime.py
```

The collector refuses to overwrite existing `runs/<Vehicle>` directories.
