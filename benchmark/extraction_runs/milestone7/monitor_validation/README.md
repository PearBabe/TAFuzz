# Milestone 7 monitor validation

This directory contains synthetic formula/trace validation only. It does not contain or evaluate flight-controller traces, and it does not change `implementation_satisfaction=NOT_ASSESSED`.

## Result

- Properties: 8
- Synthetic timed traces: 49
- Property results: `{"FAILED": 1, "PASS": 6, "UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME": 1}`
- Trace comparisons: `{"FAILED_VERDICT_MISMATCH": 1, "PASS": 42, "UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT": 6}`
- TAMonitor execution statuses: `{"EXECUTED": 43, "UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT": 6}`
- Source syntax probes: `{"UNSUPPORTED_SYNTAX": 8}`
- Adapted monitor syntax probes: `{"PASS": 8}`
- MightyPPL infinite-word satisfiability: `{"SATISFIABLE": 8}`
- Normalized pass/inconclusive/unsupported/failure counts: `{"monitor_formula_parser": {"failed": 0, "passed": 8, "unsupported": 0}, "property_monitor_runs": {"failed": 1, "inconclusive": 0, "passed": 6, "unsupported": 1}, "reference_oracle_properties": {"failed": 0, "passed": 8}, "source_formula_parser": {"failed": 0, "passed": 0, "unsupported": 8}, "trace_comparisons": {"failed": 1, "inconclusive": 0, "passed": 42, "unsupported": 6}, "trace_executions": {"executed": 43, "failed": 0, "unsupported": 6}}`

## Tool identity and syntax boundary

- TAMonitor: `e2dc4f9a77c49fe900e80d544078d9215c01d894a9396e689dd6fab6dd91d7f4`
- MightyPPL `mitppl`: `8e2ae06959eec8d3624eb1ce1923cce03c9115790075f317e16658ed933c7951`
- Standalone MoniTAal: `cb9a1c83df348df5ec141899db4ad8702ca64e8aa29e210910f98d09b586c774`
- Original catalog formulas are probed verbatim and their parser errors are retained. The monitor encoding is an exact seconds-to-integer-milliseconds rescaling with interval openness preserved.
- Standalone MoniTAal consumes positive and negative UPPAAL automata, not formulas. Property runs therefore use the existing TAMonitor integration, which builds MightyPPL automata and runs the linked MoniTAal monitor.

## Boundary policy

No epsilon or tolerance is introduced. Source seconds are rescaled exactly to integer milliseconds. T-1 and T+1 are distinct synthetic clock ticks used only to exercise open/closed endpoints; they do not move a property boundary.

Each trace begins with an all-false sentinel at 0 ms and places the actual trigger at 1000 ms. This is required because MightyPPL documents strict temporal semantics; it prevents a time-zero trigger from being silently outside an outer strict `G` observation.

The schema-valid JSON traces and TAMonitor CSV use the same monotonically increasing absolute synthetic global clock. MoniTAal's symbolic state constrains its global clock to each supplied value; its concrete state computes the elapsed amount by subtracting the current global-clock valuation.

The lower-only response formulas have no finite upper deadline. Therefore `late_response_unbounded_legal` is positive in the complete-word reference oracle. A missing finite prefix remains extendable and is expected `INCONCLUSIVE` from the infinite-extension monitor.

## Runtime blockers

All eight adapted formulas build and are satisfiable. Synthetic property outcomes: pass=6; runtime-unsupported=1; retained-comparison-failure=1. These formula/trace results do not assess firmware implementation satisfaction.

- `UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT`: 6 traces; representative `ARD-COPTER-RTL-003--positive_after_threshold` (exit `1`): `TAMonitor error: BDD projection valuation limit exceeded`

## Retained verdict mismatches

- `PX4-MC-RCLOSS-001--boundary_exact_legal`: expected infinite-prefix `INCONCLUSIVE`, observed TAMonitor `NEGATIVE`; the result, stdout, and step log remain linked in the machine-readable record.

The RTL bounded diagnostics do not change the primary configuration or trace comparisons. Their execution statuses are `{"EXECUTED": 1, "UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT": 1}` and comparison statuses are `{"INCONCLUSIVE_TAMONITOR_PREFIX": 1, "UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT": 1}`: `symbolic_max_valuations_65536=EXECUTED/INCONCLUSIVE/INCONCLUSIVE_TAMONITOR_PREFIX; concrete_default_max_valuations=UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT/NO_VERDICT/UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT`.

## Per-property evidence

| Property | Source parser | Monitor parser | SAT | Reference oracle | TAMonitor trace comparisons | Overall |
|---|---|---|---|---|---|---|
| `ARD-COPTER-GCS-001` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"PASS": 6}` | `PASS` |
| `ARD-COPTER-GUID-002` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"PASS": 6}` | `PASS` |
| `ARD-COPTER-RTL-003` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT": 6}` | `UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME` |
| `ARD-ROVER-CRASH-002` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"PASS": 6}` | `PASS` |
| `ARD-ROVER-RCFS-001` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"PASS": 6}` | `PASS` |
| `ARD-SHARED-BATT-001` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"PASS": 7}` | `PASS` |
| `PX4-MC-GCSLOSS-002` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"PASS": 6}` | `PASS` |
| `PX4-MC-RCLOSS-001` | `UNSUPPORTED_SYNTAX` | `PASS` | `SATISFIABLE` | `PASS/PASS/PASS` | `{"FAILED_VERDICT_MISMATCH": 1, "PASS": 5}` | `FAILED` |

## Honest unresolved semantics

- The primary TAMonitor runs use infinite-word mode. For an outer unbounded `G`, successful and vacuous finite prefixes are expected to remain `INCONCLUSIVE`; only irreversible prefix violations are expected `NEGATIVE`.
- Every raw TAMonitor `INCONCLUSIVE` verdict remains explicit in the per-trace result. When it equals the expected infinite-prefix verdict, the separate comparison status is `PASS`; otherwise the mismatch/diagnostic status remains explicit. The complete-word oracle never replaces the monitor verdict.
- The reference oracle uses complete finite-word pointwise semantics. TAMonitor's three-valued result concerns its positive/negative automata state estimates; disagreements remain visible per trace.
- Synthetic AP valuations test formula structure and endpoints only. They provide no evidence that firmware AP instrumentation, timestamps, correlation, or runtime behavior satisfies a property.
- No implementation-satisfaction field in the source property catalogs is modified.

## Reproduction

```console
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --force
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check
```
