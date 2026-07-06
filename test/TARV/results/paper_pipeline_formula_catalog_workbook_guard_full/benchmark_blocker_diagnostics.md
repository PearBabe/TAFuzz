# Benchmark Blocker Diagnostics

This sidecar explains why non-proof-ready MoniTAal XML rows remain excluded from formal XML-to-MITL claims.
It is diagnostic evidence for human review; it does not override the hashed pipeline artifact manifest.

## Counts

- `approximate_candidate_needs_edge_proof`: 4
- `current_event_boundary_no_candidate`: 1
- `no_conservative_candidate`: 2
- `time_divergence_not_trace_formula`: 1

## Rows

| blocker_id | xml_file | blocker_class | promotion_status | recommended_action |
|---|---|---|---|---|
| `BLOCKER_absentBQR_positive_negative` | `absentBQR.xml` | `approximate_candidate_needs_edge_proof` | `APPROXIMATE_TRACE_ONLY` | Add a formal edge/guard/reset/acceptance proof or keep excluded from formal XML-to-MITL claims. |
| `BLOCKER_delay_example_positive_negative` | `delay-example.xml` | `no_conservative_candidate` | `NOT_CLAIMED` | Add a candidate only after deriving the scope, event roles, clocks, guards, resets, and accepting locations from the TA. |
| `BLOCKER_f_g_notb_and_g_f_a_positive_negative` | `f(g(notb)_and_g(f(a)).xml` | `approximate_candidate_needs_edge_proof` | `APPROXIMATE_TRACE_ONLY` | Add a formal edge/guard/reset/acceptance proof or keep excluded from formal XML-to-MITL claims. |
| `BLOCKER_never_b_positive_negative` | `never_b.xml` | `current_event_boundary_no_candidate` | `NOT_CLAIMED` | Do not promote from the file name. A proof must show a MightyPPL formula with the same first-event and later-b verdict boundaries as the MoniTAal positive/negative TA. |
| `BLOCKER_recurBQR_positive_negative` | `recurBQR.xml` | `approximate_candidate_needs_edge_proof` | `APPROXIMATE_TRACE_ONLY` | Add a formal edge/guard/reset/acceptance proof or keep excluded from formal XML-to-MITL claims. |
| `BLOCKER_time_must_pass_positive_negative` | `time-must-pass.xml` | `time_divergence_not_trace_formula` | `NOT_CLAIMED` | Keep as XML baseline-only unless a paper theorem explicitly covers time-divergence automata rather than trace-level MITL RV. |
| `BLOCKER_b_live_a_freq_positive_negative` | `b_live_a_freq.xml` | `approximate_candidate_needs_edge_proof` | `APPROXIMATE_TRACE_ONLY` | Add a formal edge/guard/reset/acceptance proof or keep excluded from formal XML-to-MITL claims. |
| `BLOCKER_gear_controller_test_positive_negative` | `gear_controller_test.xml` | `no_conservative_candidate` | `NOT_CLAIMED` | Add a candidate only after deriving the scope, event roles, clocks, guards, resets, and accepting locations from the TA. |
