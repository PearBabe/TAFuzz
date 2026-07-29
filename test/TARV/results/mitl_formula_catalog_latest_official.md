# MITL Formula Catalog - Latest Official TAMonitor Packet

Source packet: `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full`

This catalog excludes internal MightyPPL compiler forms such as CFn/CGn because they are not user-level MITL formulas; those are only checked by input-policy rejection tests.

## Summary

- Semantic regression runtime cases: 87
- Unique semantic-regression formula strings: 49
- MoniTAal XML benchmark manifest entries: 23
- MoniTAal XML entries with non-empty MITL candidates: 19
- Unique non-empty XML candidate MITL formulas: 17
- Runtime rows total: 150 = 87 semantic + 63 XML candidate trace runs
- CLI contract rows in source packet: 11

## Generated CSV Catalogs

- `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/mitl_formula_catalog_semantic_regression.csv`
- `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/mitl_formula_catalog_monitaal_xml_candidates.csv`
- `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/mitl_formula_catalog_runtime_runs.csv`

## Semantic Regression Formulas

| # | case_id | category | word | formula | actual_final | correctness |
|---:|---|---|---|---|---|---|
| 1 | atom_true_under_f | atom:true | infinite | F [0,1] true | POSITIVE | VERIFIED |
| 2 | atom_false_under_f | atom:false | infinite | F [0,1] false | NEGATIVE | VERIFIED |
| 3 | atom_identifier | atom:idfr | infinite | F [0,2] p1 | POSITIVE | VERIFIED |
| 4 | formula_not | formula:! | infinite | F [0,2] (!p1) | POSITIVE | VERIFIED |
| 5 | formula_and | formula:&& | infinite | F [0,2] (p1 && p2) | POSITIVE | VERIFIED |
| 6 | formula_or | formula:\|\| | infinite | F [0,2] (p1 \|\| p2) | POSITIVE | VERIFIED |
| 7 | formula_implies | formula:-> | infinite | F [0,2] (p1 -> p2) | POSITIVE | VERIFIED |
| 8 | formula_iff | formula:<-> | infinite | F [0,2] (p1 <-> p2) | POSITIVE | VERIFIED |
| 9 | interval_left_open | interval:(] | infinite | F (0,2] p1 | POSITIVE | VERIFIED |
| 10 | interval_right_open | interval:[) | infinite | F [0,2) p1 | POSITIVE | VERIFIED |
| 11 | interval_open | interval:() | infinite | F (0,2) p1 | POSITIVE | VERIFIED |
| 12 | interval_unbounded | interval:infty | infinite | F [0,infty) p1 | POSITIVE | VERIFIED |
| 13 | future_finally_positive | future:F | infinite | F [0,2] p1 | POSITIVE | VERIFIED |
| 14 | future_finally_negative | future:F | infinite | F [0,2] p1 | NEGATIVE | VERIFIED |
| 15 | finite_finally_positive | finite:F | finite | F [0,2] p1 | POSITIVE | VERIFIED |
| 16 | finite_finally_negative | finite:F | finite | F [0,2] p1 | NEGATIVE | VERIFIED |
| 17 | finite_globally_violate | finite:G | finite | G [0,2] p1 | NEGATIVE | VERIFIED |
| 18 | finite_formula_and | finite:&& | finite | F [0,2] (p1 && p2) | POSITIVE | VERIFIED |
| 19 | finite_interval_open | finite:interval:() | finite | F (0,2) p1 | POSITIVE | VERIFIED |
| 20 | finite_until_positive | finite:U | finite | p1 U [1,3] p2 | POSITIVE | VERIFIED |
| 21 | finite_until_negative | finite:U | finite | p1 U [1,3] p2 | NEGATIVE | VERIFIED |
| 22 | finite_until_star | finite:U* | finite | p1 U* [0,3] p2 | POSITIVE | VERIFIED |
| 23 | finite_release_positive | finite:R | finite | p1 R [1,3] p2 | POSITIVE | VERIFIED |
| 24 | finite_release_star_end_positive | finite:R* | finite | p1 R* [0,3] p2 | POSITIVE | VERIFIED |
| 25 | finite_past_once_negative | finite:O | finite | O [0,2] p1 | NEGATIVE | VERIFIED |
| 26 | finite_past_historically_positive | finite:H | finite | H [0,2] p1 | POSITIVE | VERIFIED |
| 27 | finite_past_since_negative | finite:S | finite | p1 S [0,3] p2 | NEGATIVE | VERIFIED |
| 28 | finite_past_trigger_positive | finite:T | finite | p1 T [0,3] p2 | POSITIVE | VERIFIED |
| 29 | finite_pnueli_fn_positive | finite:Fn | finite | Fn[0,5](p1,p2,p3) | POSITIVE | VERIFIED |
| 30 | finite_pnueli_gn_end_positive | finite:Gn | finite | Gn[0,5](p1,p2,p3) | POSITIVE | VERIFIED |
| 31 | finite_pnueli_hn_positive | finite:Hn | finite | Hn[0,5](p1,p2,p3) | POSITIVE | VERIFIED |
| 32 | finite_atom_true_under_f | atom:true | finite | F [0,1] true | POSITIVE | VERIFIED |
| 33 | finite_atom_false_under_f | atom:false | finite | F [0,1] false | NEGATIVE | VERIFIED |
| 34 | finite_atom_identifier | atom:idfr | finite | F [0,2] p1 | POSITIVE | VERIFIED |
| 35 | finite_formula_not | formula:! | finite | F [0,2] (!p1) | POSITIVE | VERIFIED |
| 36 | finite_formula_or | formula:\|\| | finite | F [0,2] (p1 \|\| p2) | POSITIVE | VERIFIED |
| 37 | finite_formula_implies | formula:-> | finite | F [0,2] (p1 -> p2) | POSITIVE | VERIFIED |
| 38 | finite_formula_iff | formula:<-> | finite | F [0,2] (p1 <-> p2) | POSITIVE | VERIFIED |
| 39 | finite_interval_left_open | interval:(] | finite | F (0,2] p1 | POSITIVE | VERIFIED |
| 40 | finite_interval_right_open | interval:[) | finite | F [0,2) p1 | POSITIVE | VERIFIED |
| 41 | finite_interval_unbounded | interval:infty | finite | F [0,infty) p1 | POSITIVE | VERIFIED |
| 42 | finite_finally_star | future:F* | finite | F* [0,2] p1 | POSITIVE | VERIFIED |
| 43 | finite_globally_star_end_positive | future:G* | finite | G* [0,2] p1 | POSITIVE | VERIFIED |
| 44 | finite_past_once_star_negative | past:O* | finite | O* [0,2] p1 | NEGATIVE | VERIFIED |
| 45 | finite_past_historically_star_positive | past:H* | finite | H* [0,2] p1 | POSITIVE | VERIFIED |
| 46 | finite_past_since_star_negative | past:S* | finite | p1 S* [0,3] p2 | NEGATIVE | VERIFIED |
| 47 | finite_past_trigger_star_positive | past:T* | finite | p1 T* [0,3] p2 | POSITIVE | VERIFIED |
| 48 | finite_pnueli_on_negative | pnueli:On | finite | On[0,5](p1,p2,p3) | NEGATIVE | VERIFIED |
| 49 | future_finally_star | future:F* | infinite | F* [0,2] p1 | POSITIVE | VERIFIED |
| 50 | future_globally_hold_prefix | future:G | infinite | G [0,2] p1 | INCONCLUSIVE | VERIFIED |
| 51 | future_globally_violate | future:G | infinite | G [0,2] p1 | NEGATIVE | VERIFIED |
| 52 | future_globally_star | future:G* | infinite | G* [0,2] p1 | INCONCLUSIVE | VERIFIED |
| 53 | future_globally_star_initial_trigger_violate | future:G* | infinite | G* (a -> F [0,30] b) | NEGATIVE | VERIFIED |
| 54 | future_until_positive | future:U | infinite | p1 U [1,3] p2 | POSITIVE | VERIFIED |
| 55 | future_until_negative | future:U | infinite | p1 U [1,3] p2 | NEGATIVE | VERIFIED |
| 56 | future_until_star | future:U* | infinite | p1 U* [0,3] p2 | POSITIVE | VERIFIED |
| 57 | future_release | future:R | infinite | p1 R [1,3] p2 | POSITIVE | VERIFIED |
| 58 | future_release_star | future:R* | infinite | p1 R* [0,3] p2 | INCONCLUSIVE | VERIFIED |
| 59 | past_once | past:O | infinite | O [0,2] p1 | NEGATIVE | VERIFIED |
| 60 | past_once_star | past:O* | infinite | O* [0,2] p1 | INCONCLUSIVE | VERIFIED |
| 61 | past_historically | past:H | infinite | H [0,2] p1 | POSITIVE | VERIFIED |
| 62 | past_historically_star | past:H* | infinite | H* [0,2] p1 | POSITIVE | VERIFIED |
| 63 | past_since | past:S | infinite | p1 S [0,3] p2 | NEGATIVE | VERIFIED |
| 64 | past_since_star | past:S* | infinite | p1 S* [0,3] p2 | INCONCLUSIVE | VERIFIED |
| 65 | past_trigger | past:T | infinite | p1 T [0,3] p2 | POSITIVE | VERIFIED |
| 66 | past_trigger_star | past:T* | infinite | p1 T* [0,3] p2 | POSITIVE | VERIFIED |
| 67 | pnueli_fn | pnueli:Fn | infinite | Fn[0,5](p1,p2,p3) | POSITIVE | VERIFIED |
| 68 | pnueli_on | pnueli:On | infinite | On[0,5](p1,p2,p3) | NEGATIVE | VERIFIED |
| 69 | pnueli_gn | pnueli:Gn | infinite | Gn[0,5](p1,p2,p3) | INCONCLUSIVE | VERIFIED |
| 70 | pnueli_hn | pnueli:Hn | infinite | Hn[0,5](p1,p2,p3) | POSITIVE | VERIFIED |
| 71 | mighty_existing_MightyL_A_5_12_mitl | existing_mightyppl_testcase | infinite | G [1,2] p1 && G [1,2] p2 && G [1,2] p3 && G [1,2] p4 && G [1,2] p5 | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 72 | mighty_existing_MightyL_E_5_12_mitl | existing_mightyppl_testcase | infinite | F [1,2] p1 && F [1,2] p2 && F [1,2] p3 && F [1,2] p4 && F [1,2] p5 | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 73 | mighty_existing_MightyL_R_5_12_mitl | existing_mightyppl_testcase | infinite | (((p1 R [1,2] p2) R [1,2] p3) R [1,2] p4) R [1,2] p5 | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 74 | mighty_existing_MightyL_U_5_12_mitl | existing_mightyppl_testcase | infinite | (((p1 U [1,2] p2) U [1,2] p3) U [1,2] p4) U [1,2] p5 | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 75 | mighty_existing_MightyL_theta3_100_1000_mitl | existing_mightyppl_testcase | infinite | !((G F p1 && G F p2 && G F p3) -> G(q -> F[100,1000] r)) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 76 | mighty_existing_MightyL_theta4_100_1000_mitl | existing_mightyppl_testcase | infinite | !((G F p1 && G F p2 && G F p3 && G F p4) -> G(q -> F[100,1000] r)) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 77 | mighty_existing_acacia_3_mitl | existing_mightyppl_testcase | infinite | ( ((G (F [1, 2]p))  \|\|  (G (F [1, 2]q))  \|\|  (G (F [1, 2]r))) && (G (F (a))))<br><br>\|\|<br><br>( !((G (F [1, 2]p)) \|\|  (G (F [1, 2]q))  \|\|  (G (F [1, 2]r))) && !(G (F (a))) ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 78 | mighty_existing_acacia_4_mitl | existing_mightyppl_testcase | infinite | ( G Fn[0, 2] (p, q, r) && (G (F (a))))<br><br>&&<br><br>( !(G Fn[0, 2] (p, q, r)) \|\| !(G (F (a))) ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 79 | mighty_existing_acacia_5_mitl | existing_mightyppl_testcase | infinite | ( G(((p U[1, 2] q) U[1, 2] (!p)) U[1, 2] (!r)) && G (F (a)))<br><br>\|\|<br><br>( !(G(((p U[1, 2] q) U[1, 2] (!p)) U[1, 2] (!r))) && !(G (F (a))) ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 80 | mighty_existing_acacia_6_mitl | existing_mightyppl_testcase | infinite | ( F Gn[0, 2](p, q, r) && G (F (a)))<br><br>&&<br><br>( !(F Gn[0, 2](p, q, r)) \|\| !(G (F (a))) ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 81 | mighty_existing_acacia_9_mitl | existing_mightyppl_testcase | infinite | (((G (F[2, 4] p)) && (G (F[2, 4] q)) && (G (F[2, 4] r)) && (G (F[2, 4] s)) && (G (F[2, 4] u))) && (G (F (a))))<br>\|\|<br>(!((G (F[2, 4] p)) && (G (F[2, 4] q)) && (G (F[2, 4] r)) && (G (F[2, 4] s)) && (G (F[2, 4] u))) && !(G (F (a)))) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 82 | mighty_existing_newhoxha2_1_mitl | existing_mightyppl_testcase | infinite | F [10, 40] ( ( !(p1 \|\| false) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 )<br>&& ! F [10, 40] ( ( !(p1 \|\| p3) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 83 | mighty_existing_newhoxha2_2_mitl | existing_mightyppl_testcase | infinite | F [10, 40] ( ( !(p1 \|\| p3) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 )<br>&& ! F [10, 40] ( ( !(p1 \|\| false) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 84 | mighty_existing_newhoxha2_3_mitl | existing_mightyppl_testcase | infinite | F( (p2 \|\| (true S [0, 40] p2)) && ((p1 && !(true S [0, 30] (!p1))) \|\| (true S [0, 40] (p1 && !(true<br>S [0, 30] (!p1))))) && !((p1 && p2) \|\| (true S [0, 40] (p1 && p2)))<br>) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 85 | mighty_existing_newhoxha2_4_mitl | existing_mightyppl_testcase | infinite | F( (p2 \|\| (true S [0, 40] p2)) && ((p1 && !(true S [0, 30] (!p1))) \|\| (true S [0, 40] (p1 && !(true<br>S [0, 30] (!p1))))) && !((p1 \|\| p2) \|\| (true S [0, 40] (p1 \|\| p2)))<br>) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 86 | mighty_existing_newhoxha2_5_mitl | existing_mightyppl_testcase | infinite | F( ! (!(p && !(true S [10,infty) (!p)) && (true S [20,40] true)) \|\| ((p \|\| (true S[0, 20] p)) && !(true S [0,20] (!(p \|\| (true S[0,20] p)))))) ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |
| 87 | mighty_existing_newhoxha2_6_mitl | existing_mightyppl_testcase | infinite | F( ! (!(p && !(true S [10,infty) (!p)) && (true S [20,40] true)) \|\| ((p \|\| (true S[0, 20] p)) && !(true S [0,20] (!(p \|\| (true S[0,40] p)))))) ) | NOT_RUN_BUILD_ONLY | NOT_A_VERDICT_CHECK |

## MoniTAal XML Benchmark MITL Candidates

| # | manifest_id | xml_file | candidate_mitl | status | promotion | matches |
|---:|---|---|---|---|---|---:|
| 1 | a_b_copy_a_leadsto_b_not_a_leadsto_b | a-b copy.xml | G* (a -> F [0,30] b) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 2 | a_b_a_leadsto_b_not_a_leadsto_b | a-b.xml | G* (a -> F [0,30] b) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 3 | a_b30_a_leadsto_b_not_a_leadsto_b | a-b30.xml | G* (a -> F [0,30] b) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 4 | absentAQ_positive_negative | absentAQ.xml | G* (q -> G [0,10] (!p)) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 5 | absentBQR_positive_negative | absentBQR.xml | G* (q -> ((!p) U [3,10] r)) | approximate | APPROXIMATE_TRACE_ONLY | 1 |
| 6 | absentBR_positive_negative | absentBR.xml | G* (p -> G [0,10] (!r)) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 7 | c_after_10_positive_negative | c_after_10.xml | F [10,infty) c | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 8 | c_after_20_positive_negative | c_after_20.xml | F [20,infty) c | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 3 |
| 9 | delay_example_positive_negative | delay-example.xml | <not claimed> | not_claimed | NOT_CLAIMED | 0 |
| 10 | f_g_notb_and_g_f_a_positive_negative | f(g(notb)_and_g(f(a)).xml | (F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b)) | approximate | APPROXIMATE_TRACE_ONLY | 2 |
| 11 | never_b_positive_negative | never_b.xml | <not claimed> | not_claimed | NOT_CLAIMED | 0 |
| 12 | only_ab_until10_positive_negative | only_ab_until10.xml | G [0,10] (!c) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 3 |
| 13 | recurBQR_positive_negative | recurBQR.xml | G* (q -> ((F [0,10] p) U r)) | approximate | APPROXIMATE_TRACE_ONLY | 1 |
| 14 | recurGLB_positive_negative | recurGLB.xml | (F [0,10] p) && (G* (p -> F (0,10] p)) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 15 | time_must_pass_positive_negative | time-must-pass.xml | <not claimed> | not_claimed | NOT_CLAIMED | 0 |
| 16 | gear_control_properties_CloseClutch_NotCloseClutch | gear-control-properties.xml | G* (closeClutch -> F [0,150] clutchIsClosed) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 17 | gear_control_properties_OpenClutch_NotOpenClutch | gear-control-properties.xml | G* (openClutch -> F [0,150] clutchIsOpen) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 18 | gear_control_properties_ReqNeu_NotReqNeu | gear-control-properties.xml | G* (reqNeu -> F [0,200] gearNeu) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 19 | gear_control_properties_ReqSet_NotReqSet | gear-control-properties.xml | G* (reqSet -> F [0,300] gearSet) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 20 | gear_control_properties_SpeedSet_NotSpeedSet | gear-control-properties.xml | G* (speedSet -> F [0,500] reqTorque) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 21 | gear_control_properties_test1_Nottest1 | gear-control-properties.xml | G* (test1 -> F [0,900] reqTorque) | reviewed_obvious_candidate | STRONG_TRACE_LEVEL_CANDIDATE | 4 |
| 22 | b_live_a_freq_positive_negative | b_live_a_freq.xml | F (G (!b) && G (F [0,1000] a)) | approximate | APPROXIMATE_TRACE_ONLY | 1 |
| 23 | gear_controller_test_positive_negative | gear_controller_test.xml | <not claimed> | not_claimed | NOT_CLAIMED | 0 |

## Runtime Run Catalog

| # | group | run_id | formula | actual_final | oracle/baseline | comparison |
|---:|---|---|---|---|---|---|
| 1 | semantic_regression_runtime | atom_true_under_f | F [0,1] true | POSITIVE | POSITIVE | VERIFIED |
| 2 | semantic_regression_runtime | atom_false_under_f | F [0,1] false | NEGATIVE | NEGATIVE | VERIFIED |
| 3 | semantic_regression_runtime | atom_identifier | F [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 4 | semantic_regression_runtime | formula_not | F [0,2] (!p1) | POSITIVE | POSITIVE | VERIFIED |
| 5 | semantic_regression_runtime | formula_and | F [0,2] (p1 && p2) | POSITIVE | POSITIVE | VERIFIED |
| 6 | semantic_regression_runtime | formula_or | F [0,2] (p1 \|\| p2) | POSITIVE | POSITIVE | VERIFIED |
| 7 | semantic_regression_runtime | formula_implies | F [0,2] (p1 -> p2) | POSITIVE | POSITIVE | VERIFIED |
| 8 | semantic_regression_runtime | formula_iff | F [0,2] (p1 <-> p2) | POSITIVE | POSITIVE | VERIFIED |
| 9 | semantic_regression_runtime | interval_left_open | F (0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 10 | semantic_regression_runtime | interval_right_open | F [0,2) p1 | POSITIVE | POSITIVE | VERIFIED |
| 11 | semantic_regression_runtime | interval_open | F (0,2) p1 | POSITIVE | POSITIVE | VERIFIED |
| 12 | semantic_regression_runtime | interval_unbounded | F [0,infty) p1 | POSITIVE | POSITIVE | VERIFIED |
| 13 | semantic_regression_runtime | future_finally_positive | F [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 14 | semantic_regression_runtime | future_finally_negative | F [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 15 | semantic_regression_runtime | finite_finally_positive | F [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 16 | semantic_regression_runtime | finite_finally_negative | F [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 17 | semantic_regression_runtime | finite_globally_violate | G [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 18 | semantic_regression_runtime | finite_formula_and | F [0,2] (p1 && p2) | POSITIVE | POSITIVE | VERIFIED |
| 19 | semantic_regression_runtime | finite_interval_open | F (0,2) p1 | POSITIVE | POSITIVE | VERIFIED |
| 20 | semantic_regression_runtime | finite_until_positive | p1 U [1,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 21 | semantic_regression_runtime | finite_until_negative | p1 U [1,3] p2 | NEGATIVE | NEGATIVE | VERIFIED |
| 22 | semantic_regression_runtime | finite_until_star | p1 U* [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 23 | semantic_regression_runtime | finite_release_positive | p1 R [1,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 24 | semantic_regression_runtime | finite_release_star_end_positive | p1 R* [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 25 | semantic_regression_runtime | finite_past_once_negative | O [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 26 | semantic_regression_runtime | finite_past_historically_positive | H [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 27 | semantic_regression_runtime | finite_past_since_negative | p1 S [0,3] p2 | NEGATIVE | NEGATIVE | VERIFIED |
| 28 | semantic_regression_runtime | finite_past_trigger_positive | p1 T [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 29 | semantic_regression_runtime | finite_pnueli_fn_positive | Fn[0,5](p1,p2,p3) | POSITIVE | POSITIVE | VERIFIED |
| 30 | semantic_regression_runtime | finite_pnueli_gn_end_positive | Gn[0,5](p1,p2,p3) | POSITIVE | POSITIVE | VERIFIED |
| 31 | semantic_regression_runtime | finite_pnueli_hn_positive | Hn[0,5](p1,p2,p3) | POSITIVE | POSITIVE | VERIFIED |
| 32 | semantic_regression_runtime | finite_atom_true_under_f | F [0,1] true | POSITIVE | POSITIVE | VERIFIED |
| 33 | semantic_regression_runtime | finite_atom_false_under_f | F [0,1] false | NEGATIVE | NEGATIVE | VERIFIED |
| 34 | semantic_regression_runtime | finite_atom_identifier | F [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 35 | semantic_regression_runtime | finite_formula_not | F [0,2] (!p1) | POSITIVE | POSITIVE | VERIFIED |
| 36 | semantic_regression_runtime | finite_formula_or | F [0,2] (p1 \|\| p2) | POSITIVE | POSITIVE | VERIFIED |
| 37 | semantic_regression_runtime | finite_formula_implies | F [0,2] (p1 -> p2) | POSITIVE | POSITIVE | VERIFIED |
| 38 | semantic_regression_runtime | finite_formula_iff | F [0,2] (p1 <-> p2) | POSITIVE | POSITIVE | VERIFIED |
| 39 | semantic_regression_runtime | finite_interval_left_open | F (0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 40 | semantic_regression_runtime | finite_interval_right_open | F [0,2) p1 | POSITIVE | POSITIVE | VERIFIED |
| 41 | semantic_regression_runtime | finite_interval_unbounded | F [0,infty) p1 | POSITIVE | POSITIVE | VERIFIED |
| 42 | semantic_regression_runtime | finite_finally_star | F* [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 43 | semantic_regression_runtime | finite_globally_star_end_positive | G* [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 44 | semantic_regression_runtime | finite_past_once_star_negative | O* [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 45 | semantic_regression_runtime | finite_past_historically_star_positive | H* [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 46 | semantic_regression_runtime | finite_past_since_star_negative | p1 S* [0,3] p2 | NEGATIVE | NEGATIVE | VERIFIED |
| 47 | semantic_regression_runtime | finite_past_trigger_star_positive | p1 T* [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 48 | semantic_regression_runtime | finite_pnueli_on_negative | On[0,5](p1,p2,p3) | NEGATIVE | NEGATIVE | VERIFIED |
| 49 | semantic_regression_runtime | future_finally_star | F* [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 50 | semantic_regression_runtime | future_globally_hold_prefix | G [0,2] p1 | INCONCLUSIVE | INCONCLUSIVE | VERIFIED |
| 51 | semantic_regression_runtime | future_globally_violate | G [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 52 | semantic_regression_runtime | future_globally_star | G* [0,2] p1 | INCONCLUSIVE | INCONCLUSIVE | VERIFIED |
| 53 | semantic_regression_runtime | future_globally_star_initial_trigger_violate | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | VERIFIED |
| 54 | semantic_regression_runtime | future_until_positive | p1 U [1,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 55 | semantic_regression_runtime | future_until_negative | p1 U [1,3] p2 | NEGATIVE | NEGATIVE | VERIFIED |
| 56 | semantic_regression_runtime | future_until_star | p1 U* [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 57 | semantic_regression_runtime | future_release | p1 R [1,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 58 | semantic_regression_runtime | future_release_star | p1 R* [0,3] p2 | INCONCLUSIVE | INCONCLUSIVE | VERIFIED |
| 59 | semantic_regression_runtime | past_once | O [0,2] p1 | NEGATIVE | NEGATIVE | VERIFIED |
| 60 | semantic_regression_runtime | past_once_star | O* [0,2] p1 | INCONCLUSIVE | INCONCLUSIVE | VERIFIED |
| 61 | semantic_regression_runtime | past_historically | H [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 62 | semantic_regression_runtime | past_historically_star | H* [0,2] p1 | POSITIVE | POSITIVE | VERIFIED |
| 63 | semantic_regression_runtime | past_since | p1 S [0,3] p2 | NEGATIVE | NEGATIVE | VERIFIED |
| 64 | semantic_regression_runtime | past_since_star | p1 S* [0,3] p2 | INCONCLUSIVE | INCONCLUSIVE | VERIFIED |
| 65 | semantic_regression_runtime | past_trigger | p1 T [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 66 | semantic_regression_runtime | past_trigger_star | p1 T* [0,3] p2 | POSITIVE | POSITIVE | VERIFIED |
| 67 | semantic_regression_runtime | pnueli_fn | Fn[0,5](p1,p2,p3) | POSITIVE | POSITIVE | VERIFIED |
| 68 | semantic_regression_runtime | pnueli_on | On[0,5](p1,p2,p3) | NEGATIVE | NEGATIVE | VERIFIED |
| 69 | semantic_regression_runtime | pnueli_gn | Gn[0,5](p1,p2,p3) | INCONCLUSIVE | INCONCLUSIVE | VERIFIED |
| 70 | semantic_regression_runtime | pnueli_hn | Hn[0,5](p1,p2,p3) | POSITIVE | POSITIVE | VERIFIED |
| 71 | semantic_regression_runtime | mighty_existing_MightyL_A_5_12_mitl | G [1,2] p1 && G [1,2] p2 && G [1,2] p3 && G [1,2] p4 && G [1,2] p5 | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 72 | semantic_regression_runtime | mighty_existing_MightyL_E_5_12_mitl | F [1,2] p1 && F [1,2] p2 && F [1,2] p3 && F [1,2] p4 && F [1,2] p5 | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 73 | semantic_regression_runtime | mighty_existing_MightyL_R_5_12_mitl | (((p1 R [1,2] p2) R [1,2] p3) R [1,2] p4) R [1,2] p5 | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 74 | semantic_regression_runtime | mighty_existing_MightyL_U_5_12_mitl | (((p1 U [1,2] p2) U [1,2] p3) U [1,2] p4) U [1,2] p5 | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 75 | semantic_regression_runtime | mighty_existing_MightyL_theta3_100_1000_mitl | !((G F p1 && G F p2 && G F p3) -> G(q -> F[100,1000] r)) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 76 | semantic_regression_runtime | mighty_existing_MightyL_theta4_100_1000_mitl | !((G F p1 && G F p2 && G F p3 && G F p4) -> G(q -> F[100,1000] r)) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 77 | semantic_regression_runtime | mighty_existing_acacia_3_mitl | ( ((G (F [1, 2]p))  \|\|  (G (F [1, 2]q))  \|\|  (G (F [1, 2]r))) && (G (F (a))))<br><br>\|\|<br><br>( !((G (F [1, 2]p)) \|\|  (G (F [1, 2]q))  \|\|  (G (F [1, 2]r))) && !(G (F (a))) ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 78 | semantic_regression_runtime | mighty_existing_acacia_4_mitl | ( G Fn[0, 2] (p, q, r) && (G (F (a))))<br><br>&&<br><br>( !(G Fn[0, 2] (p, q, r)) \|\| !(G (F (a))) ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 79 | semantic_regression_runtime | mighty_existing_acacia_5_mitl | ( G(((p U[1, 2] q) U[1, 2] (!p)) U[1, 2] (!r)) && G (F (a)))<br><br>\|\|<br><br>( !(G(((p U[1, 2] q) U[1, 2] (!p)) U[1, 2] (!r))) && !(G (F (a))) ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 80 | semantic_regression_runtime | mighty_existing_acacia_6_mitl | ( F Gn[0, 2](p, q, r) && G (F (a)))<br><br>&&<br><br>( !(F Gn[0, 2](p, q, r)) \|\| !(G (F (a))) ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 81 | semantic_regression_runtime | mighty_existing_acacia_9_mitl | (((G (F[2, 4] p)) && (G (F[2, 4] q)) && (G (F[2, 4] r)) && (G (F[2, 4] s)) && (G (F[2, 4] u))) && (G (F (a))))<br>\|\|<br>(!((G (F[2, 4] p)) && (G (F[2, 4] q)) && (G (F[2, 4] r)) && (G (F[2, 4] s)) && (G (F[2, 4] u))) && !(G (F (a)))) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 82 | semantic_regression_runtime | mighty_existing_newhoxha2_1_mitl | F [10, 40] ( ( !(p1 \|\| false) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 )<br>&& ! F [10, 40] ( ( !(p1 \|\| p3) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 83 | semantic_regression_runtime | mighty_existing_newhoxha2_2_mitl | F [10, 40] ( ( !(p1 \|\| p3) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 )<br>&& ! F [10, 40] ( ( !(p1 \|\| false) \|\| (p2 \|\| F [0, 20] p2) ) && p4 && G [0, 30] p4 ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 84 | semantic_regression_runtime | mighty_existing_newhoxha2_3_mitl | F( (p2 \|\| (true S [0, 40] p2)) && ((p1 && !(true S [0, 30] (!p1))) \|\| (true S [0, 40] (p1 && !(true<br>S [0, 30] (!p1))))) && !((p1 && p2) \|\| (true S [0, 40] (p1 && p2)))<br>) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 85 | semantic_regression_runtime | mighty_existing_newhoxha2_4_mitl | F( (p2 \|\| (true S [0, 40] p2)) && ((p1 && !(true S [0, 30] (!p1))) \|\| (true S [0, 40] (p1 && !(true<br>S [0, 30] (!p1))))) && !((p1 \|\| p2) \|\| (true S [0, 40] (p1 \|\| p2)))<br>) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 86 | semantic_regression_runtime | mighty_existing_newhoxha2_5_mitl | F( ! (!(p && !(true S [10,infty) (!p)) && (true S [20,40] true)) \|\| ((p \|\| (true S[0, 20] p)) && !(true S [0,20] (!(p \|\| (true S[0,20] p)))))) ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 87 | semantic_regression_runtime | mighty_existing_newhoxha2_6_mitl | F( ! (!(p && !(true S [10,infty) (!p)) && (true S [20,40] true)) \|\| ((p \|\| (true S[0, 20] p)) && !(true S [0,20] (!(p \|\| (true S[0,40] p)))))) ) | NOT_RUN_BUILD_ONLY |  | NOT_A_VERDICT_CHECK |
| 88 | monitaal_xml_candidate_runtime | a_b_copy_a_leadsto_b_not_a_leadsto_b_monitaal_a_b_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 89 | monitaal_xml_candidate_runtime | a_b_copy_a_leadsto_b_not_a_leadsto_b_a_b_copy_boundary_positive | G* (a -> F [0,30] b) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 90 | monitaal_xml_candidate_runtime | a_b_copy_a_leadsto_b_not_a_leadsto_b_a_b_copy_initial_late_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 91 | monitaal_xml_candidate_runtime | a_b_copy_a_leadsto_b_not_a_leadsto_b_a_b_copy_rearmed_late_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 92 | monitaal_xml_candidate_runtime | a_b_a_leadsto_b_not_a_leadsto_b_monitaal_a_b_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 93 | monitaal_xml_candidate_runtime | a_b_a_leadsto_b_not_a_leadsto_b_a_b_boundary_positive | G* (a -> F [0,30] b) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 94 | monitaal_xml_candidate_runtime | a_b_a_leadsto_b_not_a_leadsto_b_a_b_initial_late_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 95 | monitaal_xml_candidate_runtime | a_b_a_leadsto_b_not_a_leadsto_b_a_b_rearmed_late_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 96 | monitaal_xml_candidate_runtime | a_b30_a_leadsto_b_not_a_leadsto_b_monitaal_a_b_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 97 | monitaal_xml_candidate_runtime | a_b30_a_leadsto_b_not_a_leadsto_b_a_b30_boundary_positive | G* (a -> F [0,30] b) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 98 | monitaal_xml_candidate_runtime | a_b30_a_leadsto_b_not_a_leadsto_b_a_b30_initial_late_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 99 | monitaal_xml_candidate_runtime | a_b30_a_leadsto_b_not_a_leadsto_b_a_b30_rearmed_late_negative | G* (a -> F [0,30] b) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 100 | monitaal_xml_candidate_runtime | absentAQ_positive_negative_absentAQ_initial_boundary_negative | G* (q -> G [0,10] (!p)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 101 | monitaal_xml_candidate_runtime | absentAQ_positive_negative_absentAQ_rearmed_boundary_negative | G* (q -> G [0,10] (!p)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 102 | monitaal_xml_candidate_runtime | absentAQ_positive_negative_absentAQ_safe_after_bound_positive | G* (q -> G [0,10] (!p)) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 103 | monitaal_xml_candidate_runtime | absentAQ_positive_negative_absentAQinput | G* (q -> G [0,10] (!p)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 104 | monitaal_xml_candidate_runtime | absentBQR_positive_negative_absentBQRinput | G* (q -> ((!p) U [3,10] r)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 105 | monitaal_xml_candidate_runtime | absentBR_positive_negative_absentBR_initial_boundary_negative | G* (p -> G [0,10] (!r)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 106 | monitaal_xml_candidate_runtime | absentBR_positive_negative_absentBR_rearmed_boundary_negative | G* (p -> G [0,10] (!r)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 107 | monitaal_xml_candidate_runtime | absentBR_positive_negative_absentBR_safe_after_bound_positive | G* (p -> G [0,10] (!r)) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 108 | monitaal_xml_candidate_runtime | absentBR_positive_negative_absentBRinput | G* (p -> G [0,10] (!r)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 109 | monitaal_xml_candidate_runtime | c_after_10_positive_negative_c_after_10_monitor_test_intersection_test2 | F [10,infty) c | POSITIVE | POSITIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 110 | monitaal_xml_candidate_runtime | c_after_10_positive_negative_c_after_10_later_positive | F [10,infty) c | POSITIVE | POSITIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 111 | monitaal_xml_candidate_runtime | c_after_10_positive_negative_c_after_10_no_witness_inconclusive | F [10,infty) c | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 112 | monitaal_xml_candidate_runtime | c_after_10_positive_negative_c_after_10_positive | F [10,infty) c | POSITIVE | POSITIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 113 | monitaal_xml_candidate_runtime | c_after_20_positive_negative_c_after_20_later_positive | F [20,infty) c | POSITIVE | POSITIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 114 | monitaal_xml_candidate_runtime | c_after_20_positive_negative_c_after_20_no_witness_inconclusive | F [20,infty) c | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 115 | monitaal_xml_candidate_runtime | c_after_20_positive_negative_c_after_20_positive | F [20,infty) c | POSITIVE | POSITIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 116 | monitaal_xml_candidate_runtime | f_g_notb_and_g_f_a_positive_negative_f_g_notb_first_late_negative | (F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 117 | monitaal_xml_candidate_runtime | f_g_notb_and_g_f_a_positive_negative_f_g_notb_late_a_negative | (F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 118 | monitaal_xml_candidate_runtime | only_ab_until10_positive_negative_only_ab_until10_negative | G [0,10] (!c) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 119 | monitaal_xml_candidate_runtime | only_ab_until10_positive_negative_only_ab_until10_negative_boundary | G [0,10] (!c) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 120 | monitaal_xml_candidate_runtime | only_ab_until10_positive_negative_only_ab_until10_positive_after_bound | G [0,10] (!c) | POSITIVE | POSITIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 121 | monitaal_xml_candidate_runtime | recurBQR_positive_negative_recurBQRinput | G* (q -> ((F [0,10] p) U r)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 122 | monitaal_xml_candidate_runtime | recurGLB_positive_negative_recurGLB_first_late_negative | (F [0,10] p) && (G* (p -> F (0,10] p)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 123 | monitaal_xml_candidate_runtime | recurGLB_positive_negative_recurGLB_initial_late_negative | (F [0,10] p) && (G* (p -> F (0,10] p)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 124 | monitaal_xml_candidate_runtime | recurGLB_positive_negative_recurGLB_timely_positive | (F [0,10] p) && (G* (p -> F (0,10] p)) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 125 | monitaal_xml_candidate_runtime | recurGLB_positive_negative_recurGLBinput | (F [0,10] p) && (G* (p -> F (0,10] p)) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 126 | monitaal_xml_candidate_runtime | gear_control_properties_CloseClutch_NotCloseClutch_gear_CloseClutch_boundary_positive | G* (closeClutch -> F [0,150] clutchIsClosed) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 127 | monitaal_xml_candidate_runtime | gear_control_properties_CloseClutch_NotCloseClutch_gear_CloseClutch_initial_late_negative | G* (closeClutch -> F [0,150] clutchIsClosed) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 128 | monitaal_xml_candidate_runtime | gear_control_properties_CloseClutch_NotCloseClutch_gear_CloseClutch_rearmed_late_negative | G* (closeClutch -> F [0,150] clutchIsClosed) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 129 | monitaal_xml_candidate_runtime | gear_control_properties_CloseClutch_NotCloseClutch_gear_control_input | G* (closeClutch -> F [0,150] clutchIsClosed) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 130 | monitaal_xml_candidate_runtime | gear_control_properties_OpenClutch_NotOpenClutch_gear_OpenClutch_boundary_positive | G* (openClutch -> F [0,150] clutchIsOpen) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 131 | monitaal_xml_candidate_runtime | gear_control_properties_OpenClutch_NotOpenClutch_gear_OpenClutch_initial_late_negative | G* (openClutch -> F [0,150] clutchIsOpen) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 132 | monitaal_xml_candidate_runtime | gear_control_properties_OpenClutch_NotOpenClutch_gear_OpenClutch_rearmed_late_negative | G* (openClutch -> F [0,150] clutchIsOpen) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 133 | monitaal_xml_candidate_runtime | gear_control_properties_OpenClutch_NotOpenClutch_gear_control_input | G* (openClutch -> F [0,150] clutchIsOpen) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 134 | monitaal_xml_candidate_runtime | gear_control_properties_ReqNeu_NotReqNeu_gear_ReqNeu_boundary_positive | G* (reqNeu -> F [0,200] gearNeu) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 135 | monitaal_xml_candidate_runtime | gear_control_properties_ReqNeu_NotReqNeu_gear_ReqNeu_initial_late_negative | G* (reqNeu -> F [0,200] gearNeu) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 136 | monitaal_xml_candidate_runtime | gear_control_properties_ReqNeu_NotReqNeu_gear_ReqNeu_rearmed_late_negative | G* (reqNeu -> F [0,200] gearNeu) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 137 | monitaal_xml_candidate_runtime | gear_control_properties_ReqNeu_NotReqNeu_gear_control_input | G* (reqNeu -> F [0,200] gearNeu) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 138 | monitaal_xml_candidate_runtime | gear_control_properties_ReqSet_NotReqSet_gear_ReqSet_boundary_positive | G* (reqSet -> F [0,300] gearSet) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 139 | monitaal_xml_candidate_runtime | gear_control_properties_ReqSet_NotReqSet_gear_ReqSet_initial_late_negative | G* (reqSet -> F [0,300] gearSet) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 140 | monitaal_xml_candidate_runtime | gear_control_properties_ReqSet_NotReqSet_gear_ReqSet_rearmed_late_negative | G* (reqSet -> F [0,300] gearSet) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 141 | monitaal_xml_candidate_runtime | gear_control_properties_ReqSet_NotReqSet_gear_control_input | G* (reqSet -> F [0,300] gearSet) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 142 | monitaal_xml_candidate_runtime | gear_control_properties_SpeedSet_NotSpeedSet_gear_SpeedSet_boundary_positive | G* (speedSet -> F [0,500] reqTorque) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 143 | monitaal_xml_candidate_runtime | gear_control_properties_SpeedSet_NotSpeedSet_gear_SpeedSet_initial_late_negative | G* (speedSet -> F [0,500] reqTorque) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 144 | monitaal_xml_candidate_runtime | gear_control_properties_SpeedSet_NotSpeedSet_gear_SpeedSet_rearmed_late_negative | G* (speedSet -> F [0,500] reqTorque) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 145 | monitaal_xml_candidate_runtime | gear_control_properties_SpeedSet_NotSpeedSet_gear_control_input | G* (speedSet -> F [0,500] reqTorque) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 146 | monitaal_xml_candidate_runtime | gear_control_properties_test1_Nottest1_gear_test1_boundary_positive | G* (test1 -> F [0,900] reqTorque) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 147 | monitaal_xml_candidate_runtime | gear_control_properties_test1_Nottest1_gear_test1_initial_late_negative | G* (test1 -> F [0,900] reqTorque) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 148 | monitaal_xml_candidate_runtime | gear_control_properties_test1_Nottest1_gear_test1_rearmed_late_negative | G* (test1 -> F [0,900] reqTorque) | NEGATIVE | NEGATIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 149 | monitaal_xml_candidate_runtime | gear_control_properties_test1_Nottest1_gear_control_input | G* (test1 -> F [0,900] reqTorque) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
| 150 | monitaal_xml_candidate_runtime | b_live_a_freq_positive_negative_b_live_a_freq_generated | F (G (!b) && G (F [0,1000] a)) | INCONCLUSIVE | INCONCLUSIVE | MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT |
