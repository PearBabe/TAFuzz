# Paper Claim Consistency Audit

This generated audit checks whether paper-facing claim rows respect the proof appendix boundary.
It is a safety check for overclaiming; it is not a substitute for the mathematical proof review.

## Counts

- PASS: 23
- WARN: 0
- FAIL: 0

## Checked Rows

| manifest_id | audit_status | claim_strength | checked_rules |
|---|---|---|---|
| `a_b_copy_a_leadsto_b_not_a_leadsto_b` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `a_b_a_leadsto_b_not_a_leadsto_b` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `a_b30_a_leadsto_b_not_a_leadsto_b` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `absentAQ_positive_negative` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `absentBQR_positive_negative` | `PASS` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | excluded rows must not be body-ready or appendix-ready claims |
| `absentBR_positive_negative` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `c_after_10_positive_negative` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `c_after_20_positive_negative` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats |
| `delay_example_positive_negative` | `PASS` | `EXCLUDED_NO_CANDIDATE` | excluded rows must not be body-ready or appendix-ready claims |
| `f_g_notb_and_g_f_a_positive_negative` | `PASS` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | excluded rows must not be body-ready or appendix-ready claims |
| `never_b_positive_negative` | `PASS` | `EXCLUDED_NO_CANDIDATE` | excluded rows must not be body-ready or appendix-ready claims |
| `only_ab_until10_positive_negative` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats |
| `recurBQR_positive_negative` | `PASS` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | excluded rows must not be body-ready or appendix-ready claims |
| `recurGLB_positive_negative` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt |
| `time_must_pass_positive_negative` | `PASS` | `EXCLUDED_NO_CANDIDATE` | excluded rows must not be body-ready or appendix-ready claims |
| `gear_control_properties_CloseClutch_NotCloseClutch` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats | gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat |
| `gear_control_properties_OpenClutch_NotOpenClutch` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats | gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat |
| `gear_control_properties_ReqNeu_NotReqNeu` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats | gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat |
| `gear_control_properties_ReqSet_NotReqSet` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats | gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat |
| `gear_control_properties_SpeedSet_NotSpeedSet` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats | gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat |
| `gear_control_properties_test1_Nottest1` | `PASS` | `BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF` | body-ready rows must be proof-ready rows without timeout baseline debt | body-ready rows with original-trace gaps must expose explicit provenance caveats | gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat |
| `b_live_a_freq_positive_negative` | `PASS` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | excluded rows must not be body-ready or appendix-ready claims |
| `gear_controller_test_positive_negative` | `PASS` | `EXCLUDED_NO_CANDIDATE` | excluded rows must not be body-ready or appendix-ready claims |
