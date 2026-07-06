# Gear Original Input Response Audit

This ledger audits the MoniTAal repository `gear-control-input.txt` finite prefix for the six gear request-response XML pairs.
It does not close the original-trace gaps: the online infinite-word baseline verdict remains `INCONCLUSIVE` for these rows.

## Counts

- rows: 6
- late response rows: 0
- pending trigger rows: 2
- expired-without-response rows: 0

## Rows

| audit_id | trigger -> response | bound | baseline | triggers | within_bound | late | pending | finite_status |
|---|---|---:|---|---:|---:|---:|---:|---|
| `gear_original_gear_control_properties_CloseClutch_NotCloseClutch` | `CloseClutch -> ClutchIsClosed` | 150 | `ran/INCONCLUSIVE` | 642 | 642 | 0 | 0 | `NO_LATE_RESPONSE_OBSERVED_BUT_ONLINE_FUTURE_OPEN` |
| `gear_original_gear_control_properties_OpenClutch_NotOpenClutch` | `OpenClutch -> ClutchIsOpen` | 150 | `ran/INCONCLUSIVE` | 643 | 643 | 0 | 0 | `NO_LATE_RESPONSE_OBSERVED_BUT_ONLINE_FUTURE_OPEN` |
| `gear_original_gear_control_properties_ReqNeu_NotReqNeu` | `ReqNeu -> GearNeu` | 200 | `ran/INCONCLUSIVE` | 793 | 793 | 0 | 0 | `NO_LATE_RESPONSE_OBSERVED_BUT_ONLINE_FUTURE_OPEN` |
| `gear_original_gear_control_properties_ReqSet_NotReqSet` | `ReqSet -> GearSet` | 300 | `ran/INCONCLUSIVE` | 794 | 793 | 0 | 1 | `PENDING_TRIGGER_AT_TRACE_END` |
| `gear_original_gear_control_properties_SpeedSet_NotSpeedSet` | `SpeedSet -> ReqTorque` | 500 | `ran/INCONCLUSIVE` | 252 | 252 | 0 | 0 | `NO_LATE_RESPONSE_OBSERVED_BUT_ONLINE_FUTURE_OPEN` |
| `gear_original_gear_control_properties_test1_Nottest1` | `test1 -> ReqTorque` | 900 | `ran/INCONCLUSIVE` | 542 | 541 | 0 | 1 | `PENDING_TRIGGER_AT_TRACE_END` |
