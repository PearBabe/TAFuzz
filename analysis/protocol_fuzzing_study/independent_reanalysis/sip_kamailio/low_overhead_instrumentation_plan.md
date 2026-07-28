# Low-overhead instrumentation plan

Instrumentation should record compact binary events inside Kamailio and defer all JSON/string work to an offline adapter.

## Hot-path event record

Recommended fixed-size fields:

`timestamp_tick, session_id, transaction_id, branch_id, hook_id, direction, event_type, method_or_status_class, flags, correlation_hashes`

Use a single monotonic clock source for all hooks.  If pcap timestamps are also used, keep both timestamps plus uncertainty metadata; do not coerce uncertain time into a precise formal verdict.

## Emission strategy

- Thread-local or per-process SPSC ring buffer.
- No global lock in send/lookup hot paths.
- No heap allocation, JSON, reason-phrase formatting, or dynamic AP name generation in Kamailio.
- Batch export to sidecar; dropped events mark affected properties `UNKNOWN`.
- Hook after facts are committed: parse success, transaction creation/match, successful send, successful timer arm/cancel.

## Timer caveat

ProfuzzBench's Kamailio patch disables timer child processes.  Timer-arm and early-destroy properties can still be observed in the patched target, but timer-expiry/callback claims need a reference profile.  Fuzzing guidance may use PTA cost with uncertain timestamps; formal verdicts must remain three-valued when timestamp error overlaps a deadline.

## Performance gate

Measure hooks/event, bytes/test, monitor overhead, and PTA prefix query P50/P95/P99.  If synchronous guidance P95 exceeds 1 ms, switch to batch/asynchronous guidance and keep crash/MITL verdict replay offline.
