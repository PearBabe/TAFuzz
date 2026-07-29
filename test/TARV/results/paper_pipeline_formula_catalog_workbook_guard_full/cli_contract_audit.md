# TAMonitor CLI Contract Audit

This generated audit runs the TAMonitor command surface directly.
It covers formula file input, inline formula input, trace file formats, stdin trace input, build modes, state modes, BDD-interface metadata, and controlled error paths.

## Counts

- `PASS`: 11

## Rows

| audit_id | pass_status | expected_exit | actual_exit | evidence |
|---|---|---|---|---|
| `cli_formula_file_trace_file_finite_symbolic` | `PASS` | `OK` | `OK` | Command completed with exit code 0. |
| `cli_formula_inline_bits_infinite_concrete` | `PASS` | `OK` | `OK` | Command completed with exit code 0. |
| `cli_trace_csv_header_time_props` | `PASS` | `OK` | `OK` | Command completed with exit code 0. |
| `cli_stdin_trace_interactive_path` | `PASS` | `OK` | `OK` | Command completed with exit code 0. |
| `cli_at_time_trace_format` | `PASS` | `OK` | `OK` | Command completed with exit code 0. |
| `cli_compflatten_build_only` | `PASS` | `OK` | `OK` | Command completed with exit code 0. |
| `cli_compflatten_runtime_rejected` | `PASS` | `CONTROLLED_ERROR` | `CONTROLLED_ERROR` | Command failed with expected diagnostic: unsupported_runtime_mode. |
| `cli_mutually_exclusive_formula_inputs` | `PASS` | `CONTROLLED_ERROR` | `CONTROLLED_ERROR` | Command failed with expected diagnostic: Provide at most one of --formula or --formula-inline. |
| `cli_invalid_trace_unknown_prop` | `PASS` | `CONTROLLED_ERROR` | `CONTROLLED_ERROR` | Command failed with expected diagnostic: Trace references proposition not present in formula. |
| `cli_missing_formula_file` | `PASS` | `CONTROLLED_ERROR` | `CONTROLLED_ERROR` | Command failed with expected diagnostic: Could not open formula file. |
| `cli_invalid_max_valuations` | `PASS` | `CONTROLLED_ERROR` | `CONTROLLED_ERROR` | Command failed with expected diagnostic: --max-valuations must be positive. |
