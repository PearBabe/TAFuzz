# Review Signoff Evidence Bundle

This generated bundle joins Review Signoff rows with their queue row, source row, and evidence references.
It is designed for human review convenience and does not record human approval.

## Summary

- rows: 56
- PASS: 56
- FAIL: 0
- blank_decisions: 56
- generated_only: `True`
- human_signoff_claim: `not_claimed`

## Rows

| signoff_id | status | decision | source | issue | focus |
|---|---|---|---|---|---|
| `SIGNOFF_001` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_XML_TRANSLATION_SCOPE (1 rows) | none | Which MoniTAal XML benchmark pairs are genuinely reviewable MITL candidates, and which remain excluded? |
| `SIGNOFF_002` | `PASS` | `APPROVE_WITH_CAVEAT` | GOAL_MONITAAL_XML_BENCHMARKS (1 rows) | none | Inventory MoniTAal benchmark XML and analyze conservative XML-to-MITL candidates. |
| `SIGNOFF_003` | `PASS` | `APPROVE_WITH_CAVEAT` | GOAL_PAPER_CLAIM_SAFETY (1 rows) | none | Prevent overclaiming in paper-facing XML/MITL and benchmark statements. |
| `SIGNOFF_004` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_XML_ORIGINAL_TRACE_GAPS (1 rows) | none | Do the remaining XML original-input provenance gaps have explicit human-review decisions and caveats? |
| `SIGNOFF_005` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_c_after_20_positive_negative_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `c_after_20_positive_negative`: no_repository_input_found. |
| `SIGNOFF_006` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_gear_control_properties_CloseClutch_NotCloseClutch_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `gear_control_properties_CloseClutch_NotCloseClutch`: repository_input_inconclusive. |
| `SIGNOFF_007` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_gear_control_properties_OpenClutch_NotOpenClutch_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `gear_control_properties_OpenClutch_NotOpenClutch`: repository_input_inconclusive. |
| `SIGNOFF_008` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_gear_control_properties_ReqNeu_NotReqNeu_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `gear_control_properties_ReqNeu_NotReqNeu`: repository_input_inconclusive. |
| `SIGNOFF_009` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_gear_control_properties_ReqSet_NotReqSet_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `gear_control_properties_ReqSet_NotReqSet`: repository_input_inconclusive. |
| `SIGNOFF_010` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_gear_control_properties_SpeedSet_NotSpeedSet_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `gear_control_properties_SpeedSet_NotSpeedSet`: repository_input_inconclusive. |
| `SIGNOFF_011` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_gear_control_properties_test1_Nottest1_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `gear_control_properties_test1_Nottest1`: repository_input_inconclusive. |
| `SIGNOFF_012` | `PASS` | `APPROVE_WITH_CAVEAT` | original_gap_trace_only_ab_until10_positive_negative_original_decisive_trace_boundary (1 rows) | none | Review original-input provenance gap `only_ab_until10_positive_negative`: no_repository_input_found. |
| `SIGNOFF_013` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_PAPER_CLAIM_BOUNDARIES (1 rows) | none | Do paper-facing claim labels preserve timeout, approximate, and excluded-row caveats? |
| `SIGNOFF_014` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_XML_EDGE_PROOFS (1 rows) | none | Do the edge/guard proof rows justify each candidate MITL pattern at trace level? |
| `SIGNOFF_015` | `PASS` | `APPROVE_WITH_CAVEAT` | a_b30_a_leadsto_b_not_a_leadsto_b (2 rows) | none | Approve or reject paper-facing wording for `a_b30_a_leadsto_b_not_a_leadsto_b`. |
| `SIGNOFF_016` | `PASS` | `APPROVE_WITH_CAVEAT` | a_b_a_leadsto_b_not_a_leadsto_b (2 rows) | none | Approve or reject paper-facing wording for `a_b_a_leadsto_b_not_a_leadsto_b`. |
| `SIGNOFF_017` | `PASS` | `APPROVE_WITH_CAVEAT` | a_b_copy_a_leadsto_b_not_a_leadsto_b (2 rows) | none | Approve or reject paper-facing wording for `a_b_copy_a_leadsto_b_not_a_leadsto_b`. |
| `SIGNOFF_018` | `PASS` | `APPROVE_WITH_CAVEAT` | absentAQ_positive_negative (2 rows) | none | Approve or reject paper-facing wording for `absentAQ_positive_negative`. |
| `SIGNOFF_019` | `PASS` | `APPROVE_WITH_CAVEAT` | absentBR_positive_negative (2 rows) | none | Approve or reject paper-facing wording for `absentBR_positive_negative`. |
| `SIGNOFF_020` | `PASS` | `APPROVE_WITH_CAVEAT` | c_after_10_positive_negative (2 rows) | none | Approve or reject paper-facing wording for `c_after_10_positive_negative`. |
| `SIGNOFF_021` | `PASS` | `APPROVE_WITH_CAVEAT` | c_after_20_positive_negative (2 rows) | none | Approve or reject paper-facing wording for `c_after_20_positive_negative`. |
| `SIGNOFF_022` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_CloseClutch_NotCloseClutch (2 rows) | none | Approve or reject paper-facing wording for `gear_control_properties_CloseClutch_NotCloseClutch`. |
| `SIGNOFF_023` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_OpenClutch_NotOpenClutch (2 rows) | none | Approve or reject paper-facing wording for `gear_control_properties_OpenClutch_NotOpenClutch`. |
| `SIGNOFF_024` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_ReqNeu_NotReqNeu (2 rows) | none | Approve or reject paper-facing wording for `gear_control_properties_ReqNeu_NotReqNeu`. |
| `SIGNOFF_025` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_ReqSet_NotReqSet (2 rows) | none | Approve or reject paper-facing wording for `gear_control_properties_ReqSet_NotReqSet`. |
| `SIGNOFF_026` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_SpeedSet_NotSpeedSet (2 rows) | none | Approve or reject paper-facing wording for `gear_control_properties_SpeedSet_NotSpeedSet`. |
| `SIGNOFF_027` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_test1_Nottest1 (2 rows) | none | Approve or reject paper-facing wording for `gear_control_properties_test1_Nottest1`. |
| `SIGNOFF_028` | `PASS` | `APPROVE_WITH_CAVEAT` | only_ab_until10_positive_negative (2 rows) | none | Approve or reject paper-facing wording for `only_ab_until10_positive_negative`. |
| `SIGNOFF_029` | `PASS` | `APPROVE_WITH_CAVEAT` | recurGLB_positive_negative (2 rows) | none | Approve or reject paper-facing wording for `recurGLB_positive_negative`. |
| `SIGNOFF_030` | `PASS` | `APPROVE_AS_CLAIMED` | a_b30_a_leadsto_b_not_a_leadsto_b (2 rows) | none | Review XML-to-MITL proof appendix row `a_b30_a_leadsto_b_not_a_leadsto_b`: G* (a -> F [0,30] b) |
| `SIGNOFF_031` | `PASS` | `APPROVE_AS_CLAIMED` | a_b_a_leadsto_b_not_a_leadsto_b (2 rows) | none | Review XML-to-MITL proof appendix row `a_b_a_leadsto_b_not_a_leadsto_b`: G* (a -> F [0,30] b) |
| `SIGNOFF_032` | `PASS` | `APPROVE_AS_CLAIMED` | a_b_copy_a_leadsto_b_not_a_leadsto_b (2 rows) | none | Review XML-to-MITL proof appendix row `a_b_copy_a_leadsto_b_not_a_leadsto_b`: G* (a -> F [0,30] b) |
| `SIGNOFF_033` | `PASS` | `APPROVE_AS_CLAIMED` | absentAQ_positive_negative (2 rows) | none | Review XML-to-MITL proof appendix row `absentAQ_positive_negative`: G* (q -> G [0,10] (!p)) |
| `SIGNOFF_034` | `PASS` | `APPROVE_AS_CLAIMED` | absentBR_positive_negative (2 rows) | none | Review XML-to-MITL proof appendix row `absentBR_positive_negative`: G* (p -> G [0,10] (!r)) |
| `SIGNOFF_035` | `PASS` | `APPROVE_AS_CLAIMED` | c_after_10_positive_negative (2 rows) | none | Review XML-to-MITL proof appendix row `c_after_10_positive_negative`: F [10,infty) c |
| `SIGNOFF_036` | `PASS` | `APPROVE_AS_CLAIMED` | c_after_20_positive_negative (2 rows) | none | Review XML-to-MITL proof appendix row `c_after_20_positive_negative`: F [20,infty) c |
| `SIGNOFF_037` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_CloseClutch_NotCloseClutch (2 rows) | none | Review XML-to-MITL proof appendix row `gear_control_properties_CloseClutch_NotCloseClutch`: G* (closeClutch -> F [0,150] clutchIsClosed) |
| `SIGNOFF_038` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_OpenClutch_NotOpenClutch (2 rows) | none | Review XML-to-MITL proof appendix row `gear_control_properties_OpenClutch_NotOpenClutch`: G* (openClutch -> F [0,150] clutchIsOpen) |
| `SIGNOFF_039` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_ReqNeu_NotReqNeu (2 rows) | none | Review XML-to-MITL proof appendix row `gear_control_properties_ReqNeu_NotReqNeu`: G* (reqNeu -> F [0,200] gearNeu) |
| `SIGNOFF_040` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_ReqSet_NotReqSet (2 rows) | none | Review XML-to-MITL proof appendix row `gear_control_properties_ReqSet_NotReqSet`: G* (reqSet -> F [0,300] gearSet) |
| `SIGNOFF_041` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_SpeedSet_NotSpeedSet (2 rows) | none | Review XML-to-MITL proof appendix row `gear_control_properties_SpeedSet_NotSpeedSet`: G* (speedSet -> F [0,500] reqTorque) |
| `SIGNOFF_042` | `PASS` | `APPROVE_WITH_CAVEAT` | gear_control_properties_test1_Nottest1 (2 rows) | none | Review XML-to-MITL proof appendix row `gear_control_properties_test1_Nottest1`: G* (test1 -> F [0,900] reqTorque) |
| `SIGNOFF_043` | `PASS` | `APPROVE_AS_CLAIMED` | only_ab_until10_positive_negative (2 rows) | none | Review XML-to-MITL proof appendix row `only_ab_until10_positive_negative`: G [0,10] (!c) |
| `SIGNOFF_044` | `PASS` | `APPROVE_AS_CLAIMED` | recurGLB_positive_negative (2 rows) | none | Review XML-to-MITL proof appendix row `recurGLB_positive_negative`: (F [0,10] p) && (G* (p -> F (0,10] p)) |
| `SIGNOFF_045` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_CANDIDATE_STEP_AUDIT (1 rows) | none | Did every TAMonitor candidate run expose all mapped trace steps in the compact step audit? |
| `SIGNOFF_046` | `PASS` | `APPROVE_WITH_CAVEAT` | GOAL_COMPFLATTEN_BOUNDARY (1 rows) | none | Support compflatten construction/statistics while avoiding fake runtime verdicts. |
| `SIGNOFF_047` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_COMPFLATTEN_SCOPE (1 rows) | none | Is compflatten represented only as construction/statistics evidence, never as a v1 runtime verdict? |
| `SIGNOFF_048` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_BASELINE_TIMEOUT_CAVEATS (1 rows) | none | Are MoniTAal baseline timeout and no-input rows handled according to their actual status? |
| `SIGNOFF_049` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_HAND_ORACLE_FINAL_VERDICTS (1 rows) | none | Do the manually specified final verdict oracles match TAMonitor output for all claimed MITL semantic cases? |
| `SIGNOFF_050` | `PASS` | `APPROVE_AS_CLAIMED` | MR_INTERNAL_COUNT_INPUT_BOUNDARY (1 rows) | none | Are CFn/COn/CGn/CHn and starred variants excluded from MITL semantic tests and rejected through controlled diagnostics? |
| `SIGNOFF_051` | `PASS` | `APPROVE_WITH_CAVEAT` | MR_GEAR_BASELINE_EVIDENCE (1 rows) | none | Do gear benchmark rows record original-input MoniTAal baseline matches while still requiring human XML-to-MITL proof signoff? |
| `SIGNOFF_052` | `PASS` | `APPROVE_AS_CLAIMED` | MR_PREFIX_ORACLE (1 rows) | none | Does each recorded timed-word prefix verdict match the hand oracle where an oracle is defined? |
| `SIGNOFF_053` | `PASS` | `APPROVE_AS_CLAIMED` | MR_FINITE_INFINITE_WORD_MODES (1 rows) | none | Are finite-word and infinite-word claims backed by separate hand-oracle rows? |
| `SIGNOFF_054` | `PASS` | `APPROVE_AS_CLAIMED` | MR_MIGHTYPPL_SYNTAX_COVERAGE (1 rows) | none | Does every user-level MightyPPL grammar construct have runtime evidence, build/stat evidence, or an explicit exclusion? |
| `SIGNOFF_055` | `PASS` | `DEFER_TO_V2` | GOAL_BDD_NATIVE_INTERFACE (1 rows) | none | Reserve a BDD-native runtime interface without pretending it is implemented. |
| `SIGNOFF_056` | `PASS` | `DEFER_TO_V2` | MR_BDD_NATIVE_DEFERRAL (1 rows) | none | Is BDD-native runtime clearly reserved rather than falsely implemented in v1? |
