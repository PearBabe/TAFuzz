# ArduPilot / PX4 MITL Benchmark

This directory contains specification-derived, source-bound MITL properties
for ArduPilot and PX4.  The benchmark is evidence-first: every accepted
property retains its natural-language source, temporal provenance, atomic
proposition contract, source bindings, MAVLink observability, and validation
traces.

The existence of a source binding is **not** evidence that the implementation
satisfies the property.  All records use
`implementation_satisfaction = NOT_ASSESSED` until a separate fuzzing campaign
produces a verdict.

See `source_freeze_manifest.json` for the exact paper and source revisions.
The reader-facing method and result summaries are written in Chinese in
`METHOD.md` and `RESULTS.md`.
