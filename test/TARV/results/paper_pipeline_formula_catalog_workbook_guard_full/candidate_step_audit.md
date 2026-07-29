# Candidate Step Audit

This generated audit indexes TAMonitor per-prefix outputs for XML-to-MITL benchmark candidates.
`candidate_prefix_observations.csv` contains the full raw per-step export.
The rows here are a compact paper-review index; correctness claims remain final-verdict baseline comparisons unless otherwise proved.

## Counts

- candidate rows: 63
- all trace steps recorded: 63
- `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT`: 63

## Review Table

| candidate_id | observed_steps | first_decisive | final | baseline | comparison |
|---|---:|---|---|---|---|
| `a_b_copy_a_leadsto_b_not_a_leadsto_b_monitaal_a_b_negative` | 11 | `11:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_copy_a_leadsto_b_not_a_leadsto_b_a_b_copy_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_copy_a_leadsto_b_not_a_leadsto_b_a_b_copy_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_copy_a_leadsto_b_not_a_leadsto_b_a_b_copy_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_a_leadsto_b_not_a_leadsto_b_monitaal_a_b_negative` | 11 | `11:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_a_leadsto_b_not_a_leadsto_b_a_b_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_a_leadsto_b_not_a_leadsto_b_a_b_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b_a_leadsto_b_not_a_leadsto_b_a_b_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b30_a_leadsto_b_not_a_leadsto_b_monitaal_a_b_negative` | 11 | `11:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b30_a_leadsto_b_not_a_leadsto_b_a_b30_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b30_a_leadsto_b_not_a_leadsto_b_a_b30_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `a_b30_a_leadsto_b_not_a_leadsto_b_a_b30_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentAQ_positive_negative_absentAQ_initial_boundary_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentAQ_positive_negative_absentAQ_rearmed_boundary_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentAQ_positive_negative_absentAQ_safe_after_bound_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentAQ_positive_negative_absentAQinput` | 10028 | `10028:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentBQR_positive_negative_absentBQRinput` | 10012 | `17:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentBR_positive_negative_absentBR_initial_boundary_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentBR_positive_negative_absentBR_rearmed_boundary_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentBR_positive_negative_absentBR_safe_after_bound_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `absentBR_positive_negative_absentBRinput` | 10028 | `10028:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_10_positive_negative_c_after_10_monitor_test_intersection_test2` | 4 | `3:POSITIVE` | `POSITIVE` | `POSITIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_10_positive_negative_c_after_10_later_positive` | 2 | `2:POSITIVE` | `POSITIVE` | `POSITIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_10_positive_negative_c_after_10_no_witness_inconclusive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_10_positive_negative_c_after_10_positive` | 2 | `2:POSITIVE` | `POSITIVE` | `POSITIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_20_positive_negative_c_after_20_later_positive` | 2 | `2:POSITIVE` | `POSITIVE` | `POSITIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_20_positive_negative_c_after_20_no_witness_inconclusive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `c_after_20_positive_negative_c_after_20_positive` | 2 | `2:POSITIVE` | `POSITIVE` | `POSITIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `f_g_notb_and_g_f_a_positive_negative_f_g_notb_first_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `f_g_notb_and_g_f_a_positive_negative_f_g_notb_late_a_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `only_ab_until10_positive_negative_only_ab_until10_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `only_ab_until10_positive_negative_only_ab_until10_negative_boundary` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `only_ab_until10_positive_negative_only_ab_until10_positive_after_bound` | 2 | `2:POSITIVE` | `POSITIVE` | `POSITIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `recurBQR_positive_negative_recurBQRinput` | 10015 | `35:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `recurGLB_positive_negative_recurGLB_first_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `recurGLB_positive_negative_recurGLB_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `recurGLB_positive_negative_recurGLB_timely_positive` | 3 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `recurGLB_positive_negative_recurGLBinput` | 10015 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_CloseClutch_NotCloseClutch_gear_CloseClutch_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_CloseClutch_NotCloseClutch_gear_CloseClutch_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_CloseClutch_NotCloseClutch_gear_CloseClutch_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_CloseClutch_NotCloseClutch_gear_control_input` | 12126 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_OpenClutch_NotOpenClutch_gear_OpenClutch_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_OpenClutch_NotOpenClutch_gear_OpenClutch_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_OpenClutch_NotOpenClutch_gear_OpenClutch_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_OpenClutch_NotOpenClutch_gear_control_input` | 12126 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqNeu_NotReqNeu_gear_ReqNeu_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqNeu_NotReqNeu_gear_ReqNeu_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqNeu_NotReqNeu_gear_ReqNeu_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqNeu_NotReqNeu_gear_control_input` | 12126 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqSet_NotReqSet_gear_ReqSet_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqSet_NotReqSet_gear_ReqSet_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqSet_NotReqSet_gear_ReqSet_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_ReqSet_NotReqSet_gear_control_input` | 12126 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_SpeedSet_NotSpeedSet_gear_SpeedSet_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_SpeedSet_NotSpeedSet_gear_SpeedSet_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_SpeedSet_NotSpeedSet_gear_SpeedSet_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_SpeedSet_NotSpeedSet_gear_control_input` | 12126 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_test1_Nottest1_gear_test1_boundary_positive` | 2 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_test1_Nottest1_gear_test1_initial_late_negative` | 2 | `2:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_test1_Nottest1_gear_test1_rearmed_late_negative` | 4 | `4:NEGATIVE` | `NEGATIVE` | `NEGATIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `gear_control_properties_test1_Nottest1_gear_control_input` | 12126 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
| `b_live_a_freq_positive_negative_b_live_a_freq_generated` | 20 | `:` | `INCONCLUSIVE` | `INCONCLUSIVE` | `MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT` |
