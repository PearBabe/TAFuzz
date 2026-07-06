# XML Original Trace Gaps

This ledger isolates proof-ready XML rows whose original/repository timed-word evidence is not decisive.
All rows are REVIEW_REQUIRED and non-machine-checkable; generated review traces must not be reclassified as original benchmark evidence.

## Counts

- `REVIEW_REQUIRED`: 8
- `FAIL`: 0

## Gap Classes

| gap_class | rows |
|---|---:|
| `no_repository_input_found` | 2 |
| `repository_input_inconclusive` | 6 |

## Gaps

| manifest_id | xml_file | gap_class | observed | candidates | manual_review_action |
|---|---|---|---|---|---|
| `c_after_20_positive_negative` | `c_after_20.xml` | `no_repository_input_found` | original_like=0; decisive_original=0; generated_empty=0 |  | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `only_ab_until10_positive_negative` | `only_ab_until10.xml` | `no_repository_input_found` | original_like=0; decisive_original=0; generated_empty=0 |  | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `gear_control_properties_CloseClutch_NotCloseClutch` | `gear-control-properties.xml` | `repository_input_inconclusive` | original_like=1; decisive_original=0; generated_empty=0 | gear_control_properties_CloseClutch_NotCloseClutch_gear_control_input[INCONCLUSIVE\|repository_input\|repository_inconclusive_long_trace\|t=?] | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `gear_control_properties_OpenClutch_NotOpenClutch` | `gear-control-properties.xml` | `repository_input_inconclusive` | original_like=1; decisive_original=0; generated_empty=0 | gear_control_properties_OpenClutch_NotOpenClutch_gear_control_input[INCONCLUSIVE\|repository_input\|repository_inconclusive_long_trace\|t=?] | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `gear_control_properties_ReqNeu_NotReqNeu` | `gear-control-properties.xml` | `repository_input_inconclusive` | original_like=1; decisive_original=0; generated_empty=0 | gear_control_properties_ReqNeu_NotReqNeu_gear_control_input[INCONCLUSIVE\|repository_input\|repository_inconclusive_long_trace\|t=?] | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `gear_control_properties_ReqSet_NotReqSet` | `gear-control-properties.xml` | `repository_input_inconclusive` | original_like=1; decisive_original=0; generated_empty=0 | gear_control_properties_ReqSet_NotReqSet_gear_control_input[INCONCLUSIVE\|repository_input\|repository_inconclusive_long_trace\|t=?] | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `gear_control_properties_SpeedSet_NotSpeedSet` | `gear-control-properties.xml` | `repository_input_inconclusive` | original_like=1; decisive_original=0; generated_empty=0 | gear_control_properties_SpeedSet_NotSpeedSet_gear_control_input[INCONCLUSIVE\|repository_input\|repository_inconclusive_long_trace\|t=?] | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
| `gear_control_properties_test1_Nottest1` | `gear-control-properties.xml` | `repository_input_inconclusive` | original_like=1; decisive_original=0; generated_empty=0 | gear_control_properties_test1_Nottest1_gear_control_input[INCONCLUSIVE\|repository_input\|repository_inconclusive_long_trace\|t=?] | Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, or keep the paper claim caveated to generated trace evidence and structural proof obligations. |
