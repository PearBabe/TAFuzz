# Paper Claim Review

This review is generated from the proof appendix and baseline tables.
It is a writing and manual-review guide, not an additional proof rule.

## Counts

- Body-pattern candidates eligible only after human signoff: 15
- Appendix-ready instances with timeout caveat: 0
- Excluded rows: 8
- Body/proof candidates with unresolved original-trace caveats: 8

## Proof Pattern Counts

| proof_class | rows |
|---|---:|
| `bounded_absence_after_trigger` | 2 |
| `bounded_global_absence` | 1 |
| `bounded_recurrence_after_event` | 1 |
| `bounded_response_leadsto` | 3 |
| `eventually_after_lower_bound` | 2 |
| `gear_bounded_request_response` | 6 |

## Body-Safe Pattern Summaries Eligible Only After Human Signoff

Use these only after checking the final paper definitions for alphabets, finite-prefix verdicts, and G*.

| manifest_id | candidate | recommendation |
|---|---|---|
| `a_b_copy_a_leadsto_b_not_a_leadsto_b` | `G* (a -> F [0,30] b)` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `a_b_a_leadsto_b_not_a_leadsto_b` | `G* (a -> F [0,30] b)` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `a_b30_a_leadsto_b_not_a_leadsto_b` | `G* (a -> F [0,30] b)` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `absentAQ_positive_negative` | `G* (q -> G [0,10] (!p))` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `absentBR_positive_negative` | `G* (p -> G [0,10] (!r))` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `c_after_10_positive_negative` | `F [10,infty) c` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `c_after_20_positive_negative` | `F [20,infty) c` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `only_ab_until10_positive_negative` | `G [0,10] (!c)` | Body may summarize this proof pattern after human signoff on the alphabet, finite-prefix verdict, and G* first-observation convention. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `recurGLB_positive_negative` | `(F [0,10] p) && (G* (p -> F (0,10] p))` | Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat. |
| `gear_control_properties_CloseClutch_NotCloseClutch` | `G* (closeClutch -> F [0,150] clutchIsClosed)` | Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `gear_control_properties_OpenClutch_NotOpenClutch` | `G* (openClutch -> F [0,150] clutchIsOpen)` | Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `gear_control_properties_ReqNeu_NotReqNeu` | `G* (reqNeu -> F [0,200] gearNeu)` | Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `gear_control_properties_ReqSet_NotReqSet` | `G* (reqSet -> F [0,300] gearSet)` | Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `gear_control_properties_SpeedSet_NotSpeedSet` | `G* (speedSet -> F [0,500] reqTorque)` | Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |
| `gear_control_properties_test1_Nottest1` | `G* (test1 -> F [0,900] reqTorque)` | Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces. Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer. |

## Appendix-Ready With Timeout Caveat

These rows have structural edge/guard proof evidence but still lack original-input baseline verdicts. Treat them as appendix-only until a justified original-input verdict or reduction is recorded.

| manifest_id | candidate | must_not_claim |
|---|---|---|

## Original-Trace Caveats

These paper-facing rows are structurally/proof-review candidates, but original timed-word coverage remains unresolved or non-decisive.

| manifest_id | candidate | original_trace_gap_boundary | must_not_claim |
|---|---|---|---|
| `c_after_20_positive_negative` | `F [20,infty) c` | gap_status=REVIEW_REQUIRED; gap_class=no_repository_input_found; observed=original_like=0; decisive_original=0; generated_empty=0; reason=No repository, embedded, or external timed-word input was found for this XML pair. | Do not call this an automatic theorem, Boolean satisfaction/violation result, or completed XML-to-MITL equivalence proof from INCONCLUSIVE trace evidence; keep the third-valued caveat until human proof review. Do not treat generated review traces as original benchmark evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `only_ab_until10_positive_negative` | `G [0,10] (!c)` | gap_status=REVIEW_REQUIRED; gap_class=no_repository_input_found; observed=original_like=0; decisive_original=0; generated_empty=0; reason=No repository, embedded, or external timed-word input was found for this XML pair. | Do not call this an automatic theorem without the human proof review recorded. Do not treat generated review traces as original benchmark evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `gear_control_properties_CloseClutch_NotCloseClutch` | `G* (closeClutch -> F [0,150] clutchIsClosed)` | gap_status=REVIEW_REQUIRED; gap_class=repository_input_inconclusive; observed=original_like=1; decisive_original=0; generated_empty=0; reason=A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE. | Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic XML-to-MITL equivalence theorem, or human proof signoff. Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `gear_control_properties_OpenClutch_NotOpenClutch` | `G* (openClutch -> F [0,150] clutchIsOpen)` | gap_status=REVIEW_REQUIRED; gap_class=repository_input_inconclusive; observed=original_like=1; decisive_original=0; generated_empty=0; reason=A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE. | Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic XML-to-MITL equivalence theorem, or human proof signoff. Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `gear_control_properties_ReqNeu_NotReqNeu` | `G* (reqNeu -> F [0,200] gearNeu)` | gap_status=REVIEW_REQUIRED; gap_class=repository_input_inconclusive; observed=original_like=1; decisive_original=0; generated_empty=0; reason=A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE. | Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic XML-to-MITL equivalence theorem, or human proof signoff. Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `gear_control_properties_ReqSet_NotReqSet` | `G* (reqSet -> F [0,300] gearSet)` | gap_status=REVIEW_REQUIRED; gap_class=repository_input_inconclusive; observed=original_like=1; decisive_original=0; generated_empty=0; reason=A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE. | Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic XML-to-MITL equivalence theorem, or human proof signoff. Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `gear_control_properties_SpeedSet_NotSpeedSet` | `G* (speedSet -> F [0,500] reqTorque)` | gap_status=REVIEW_REQUIRED; gap_class=repository_input_inconclusive; observed=original_like=1; decisive_original=0; generated_empty=0; reason=A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE. | Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic XML-to-MITL equivalence theorem, or human proof signoff. Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |
| `gear_control_properties_test1_Nottest1` | `G* (test1 -> F [0,900] reqTorque)` | gap_status=REVIEW_REQUIRED; gap_class=repository_input_inconclusive; observed=original_like=1; decisive_original=0; generated_empty=0; reason=A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE. | Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic XML-to-MITL equivalence theorem, or human proof signoff. Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence. Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated. |

## Excluded Rows

| manifest_id | claim_strength | next_manual_action |
|---|---|---|
| `absentBQR_positive_negative` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | Add a formal edge/guard proof for the approximate candidate or keep excluded. |
| `delay_example_positive_negative` | `EXCLUDED_NO_CANDIDATE` | Add a conservative candidate only after edge/guard semantics are derived. |
| `f_g_notb_and_g_f_a_positive_negative` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | Add a formal edge/guard proof for the approximate candidate or keep excluded. |
| `never_b_positive_negative` | `EXCLUDED_NO_CANDIDATE` | Add a conservative candidate only after edge/guard semantics are derived. |
| `recurBQR_positive_negative` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | Add a formal edge/guard proof for the approximate candidate or keep excluded. |
| `time_must_pass_positive_negative` | `EXCLUDED_NO_CANDIDATE` | Add a conservative candidate only after edge/guard semantics are derived. |
| `b_live_a_freq_positive_negative` | `EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE` | Add a formal edge/guard proof for the approximate candidate or keep excluded. |
| `gear_controller_test_positive_negative` | `EXCLUDED_NO_CANDIDATE` | Add a conservative candidate only after edge/guard semantics are derived. |
