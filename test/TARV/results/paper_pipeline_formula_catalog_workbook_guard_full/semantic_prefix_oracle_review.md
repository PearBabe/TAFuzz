# Semantic Prefix Oracle Review

This generated review index gives one row per recorded TAMonitor prefix step.
Rows with `MATCH` compare the observed prefix verdict against a hand-written prefix oracle.
Rows with `monitor_advanced=false` are stable carry-forward verdicts after the monitor has already reached POSITIVE or NEGATIVE.

## Counts

- `MATCH`: 146
- `NOT_A_RUNTIME_VERDICT_CHECK`: 17

## Review Table

| case_id | step | expected | actual | status | monitor_advanced |
|---|---:|---|---|---|---|
| `atom_true_under_f` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `atom_true_under_f` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `atom_false_under_f` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `atom_false_under_f` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `atom_identifier` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `atom_identifier` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `formula_not` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `formula_not` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `formula_and` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `formula_and` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `formula_or` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `formula_or` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `formula_implies` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `formula_implies` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `formula_iff` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `formula_iff` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `interval_left_open` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `interval_left_open` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `interval_right_open` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `interval_right_open` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `interval_open` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `interval_open` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `interval_unbounded` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `interval_unbounded` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `future_finally_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_finally_positive` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `future_finally_negative` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_finally_negative` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `finite_finally_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_finally_positive` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_finally_negative` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_finally_negative` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `finite_globally_violate` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_globally_violate` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `finite_formula_and` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_formula_and` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_interval_open` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_interval_open` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_until_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_until_positive` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_until_positive` | 3 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_until_negative` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_until_negative` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_until_negative` | 3 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `finite_until_star` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_release_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_release_positive` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_release_positive` | 3 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_release_star_end_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_past_once_negative` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_past_once_negative` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_past_historically_positive` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_past_historically_positive` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_past_since_negative` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_past_since_negative` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_past_trigger_positive` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_past_trigger_positive` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_pnueli_fn_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_fn_positive` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_fn_positive` | 3 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_fn_positive` | 4 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_pnueli_gn_end_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_gn_end_positive` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_gn_end_positive` | 3 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_gn_end_positive` | 4 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_pnueli_hn_positive` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_pnueli_hn_positive` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_pnueli_hn_positive` | 3 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_atom_true_under_f` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_atom_true_under_f` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_atom_false_under_f` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_atom_false_under_f` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_atom_identifier` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_atom_identifier` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_formula_not` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_formula_not` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_formula_or` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_formula_or` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_formula_implies` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_formula_implies` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_formula_iff` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_formula_iff` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_interval_left_open` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_interval_left_open` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_interval_right_open` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_interval_right_open` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_interval_unbounded` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_interval_unbounded` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_finally_star` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_globally_star_end_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_globally_star_end_positive` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `finite_past_once_star_negative` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `finite_past_historically_star_positive` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_past_historically_star_positive` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `finite_past_since_star_negative` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `finite_past_trigger_star_positive` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `finite_pnueli_on_negative` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_pnueli_on_negative` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `finite_pnueli_on_negative` | 3 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `future_finally_star` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `future_globally_hold_prefix` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_globally_hold_prefix` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_globally_violate` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_globally_violate` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `future_globally_star` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_globally_star` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_globally_star_initial_trigger_violate` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_globally_star_initial_trigger_violate` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `future_until_positive` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_until_positive` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_until_positive` | 3 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `future_until_negative` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_until_negative` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_until_negative` | 3 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `true` |
| `future_until_star` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `future_release` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_release` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `future_release` | 3 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `future_release_star` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `past_once` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `past_once` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `past_once_star` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `past_historically` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `past_historically` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `past_historically_star` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `past_historically_star` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `past_since` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `past_since` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `past_since_star` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `past_trigger` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `past_trigger` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `past_trigger_star` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `pnueli_fn` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_fn` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_fn` | 3 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_fn` | 4 | `POSITIVE` | `POSITIVE` | `MATCH` | `true` |
| `pnueli_on` | 1 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `pnueli_on` | 2 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `pnueli_on` | 3 | `NEGATIVE` | `NEGATIVE` | `MATCH` | `false` |
| `pnueli_gn` | 1 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_gn` | 2 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_gn` | 3 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_gn` | 4 | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCH` | `true` |
| `pnueli_hn` | 1 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `pnueli_hn` | 2 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `pnueli_hn` | 3 | `POSITIVE` | `POSITIVE` | `MATCH` | `false` |
| `mighty_existing_MightyL_A_5_12_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_MightyL_E_5_12_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_MightyL_R_5_12_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_MightyL_U_5_12_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_MightyL_theta3_100_1000_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_MightyL_theta4_100_1000_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_acacia_3_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_acacia_4_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_acacia_5_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_acacia_6_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_acacia_9_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_newhoxha2_1_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_newhoxha2_2_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_newhoxha2_3_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_newhoxha2_4_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_newhoxha2_5_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
| `mighty_existing_newhoxha2_6_mitl` |  | `` | `` | `NOT_A_RUNTIME_VERDICT_CHECK` | `` |
