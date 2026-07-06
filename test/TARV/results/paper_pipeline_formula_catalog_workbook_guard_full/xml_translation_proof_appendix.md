# XML-to-MITL Proof Appendix Draft

This appendix is generated from `xml_edge_guard_proofs.csv` and is intended for manual paper review.
It does not claim that approximate or unpromoted XML rows are formally translated.

## Scope

- Structurally proof-ready XML pairs: 15
- Excluded or not-ready XML pairs: 8
- Each proof-ready row must still be checked against the paper's final definition of trace alphabets, finite-prefix verdicts, and the G* first-observation convention.

## Structural Proof-Ready Candidates

### a_b_copy_a_leadsto_b_not_a_leadsto_b

- XML file: `a-b copy.xml`
- Templates: `a_leadsto_b` / `not_a_leadsto_b`
- Candidate MITL: `G* (a -> F [0,30] b)`
- Proof class: `bounded_response_leadsto`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements G* (a -> F [0,30] b): the positive template is accepting before an obligation, the a edge resets clock x, and the b edge with x <= 30 returns to an accepting state. The negative template reaches an accepting violation state on x > 30. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: a_leadsto_b#1:l2->l1_a;label=b;guard=x <= 30;assign=<none>;accept=no->yes;initial=no->yes | not_a_leadsto_b#4:l2->l4_a;label=a;guard=x > 30;assign=<none>;accept=no->yes;initial=no->no | a_leadsto_b#6:l1_a->l2;label=a;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | not_a_leadsto_b#10:l1->l2;label=a;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/cases/monitaal_a_b_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b_copy_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b_copy_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b_copy_rearmed_late_negative.input

Manual review notes: Manual reviewer should still check alphabet closure for labels not in the reduced traces and the G* first-observation convention.

### a_b_a_leadsto_b_not_a_leadsto_b

- XML file: `a-b.xml`
- Templates: `a_leadsto_b` / `not_a_leadsto_b`
- Candidate MITL: `G* (a -> F [0,30] b)`
- Proof class: `bounded_response_leadsto`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements G* (a -> F [0,30] b): the positive template is accepting before an obligation, the a edge resets clock x, and the b edge with x <= 30 returns to an accepting state. The negative template reaches an accepting violation state on x > 30. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: a_leadsto_b#1:l2->l1_a;label=b;guard=x <= 30;assign=<none>;accept=no->yes;initial=no->yes | not_a_leadsto_b#4:l2->l4_a;label=a;guard=x > 30;assign=<none>;accept=no->yes;initial=no->no | a_leadsto_b#6:l1_a->l2;label=a;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | not_a_leadsto_b#10:l1->l2;label=a;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/cases/monitaal_a_b_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b_rearmed_late_negative.input

Manual review notes: Manual reviewer should still check alphabet closure for labels not in the reduced traces and the G* first-observation convention.

### a_b30_a_leadsto_b_not_a_leadsto_b

- XML file: `a-b30.xml`
- Templates: `a_leadsto_b` / `not_a_leadsto_b`
- Candidate MITL: `G* (a -> F [0,30] b)`
- Proof class: `bounded_response_leadsto`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements G* (a -> F [0,30] b): the positive template is accepting before an obligation, the a edge resets clock x, and the b edge with x <= 30 returns to an accepting state. The negative template reaches an accepting violation state on x > 30. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: a_leadsto_b#1:q2->q1_a;label=b;guard=x <= 30;assign=<none>;accept=no->yes;initial=no->yes | not_a_leadsto_b#4:q2->q3_a;label=a;guard=x > 30;assign=<none>;accept=no->yes;initial=no->no | a_leadsto_b#6:q1_a->q2;label=a;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | not_a_leadsto_b#10:q1->q2;label=a;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/cases/monitaal_a_b_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b30_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b30_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/a_b30_rearmed_late_negative.input

Manual review notes: Manual reviewer should still check alphabet closure for labels not in the reduced traces and the G* first-observation convention.

### absentAQ_positive_negative

- XML file: `absentAQ.xml`
- Templates: `positive` / `negative`
- Candidate MITL: `G* (q -> G [0,10] (!p))`
- Proof class: `bounded_absence_after_trigger`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements G* (q -> G [0,10] (!p)): the trigger q resets clock c; the forbidden event p reaches the negative accepting state when c <= 10, while the positive template only treats p as safe after c > 10. This matches a closed-bound absence obligation after the trigger.

Evidence: positive#3:l1->l0_a;label=p;guard=c > 10;assign=<none>;accept=no->yes;initial=no->yes | negative#6:l1->l2_a;label=p;guard=c <= 10;assign=<none>;accept=no->yes;initial=no->no | positive#2:l1->l1;label=q;guard=<none>;assign=c := 0;accept=no->no;initial=no->no | negative#4:l1->l1;label=q;guard=<none>;assign=c := 0;accept=no->no;initial=no->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/absentAQ_initial_boundary_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/absentAQ_rearmed_boundary_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/absentAQ_safe_after_bound_positive.input;/home/lqq/project/TAFuzz/tool/MoniTAal/test/models/absentAQinput.txt

Manual review notes: Manual reviewer should check repeated-trigger handling and whether the closed c <= 10 boundary matches the MITL interval.

### absentBR_positive_negative

- XML file: `absentBR.xml`
- Templates: `positive` / `negative`
- Candidate MITL: `G* (p -> G [0,10] (!r))`
- Proof class: `bounded_absence_after_trigger`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements G* (p -> G [0,10] (!r)): the trigger p resets clock c; the forbidden event r reaches the negative accepting state when c <= 10, while the positive template only treats r as safe after c > 10. This matches a closed-bound absence obligation after the trigger.

Evidence: positive#2:l1_a->l0_a;label=r;guard=c > 10;assign=<none>;accept=yes->yes;initial=no->yes | negative#6:l1->l2_a;label=r;guard=c <= 10;assign=<none>;accept=no->yes;initial=no->no | positive#3:l1_a->l1_a;label=p;guard=<none>;assign=c := 0;accept=yes->yes;initial=no->no | negative#4:l1->l1;label=p;guard=<none>;assign=c := 0;accept=no->no;initial=no->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/absentBR_initial_boundary_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/absentBR_rearmed_boundary_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/absentBR_safe_after_bound_positive.input;/home/lqq/project/TAFuzz/tool/MoniTAal/test/models/absentBRinput.txt

Manual review notes: Manual reviewer should check repeated-trigger handling and whether the closed c <= 10 boundary matches the MITL interval.

### c_after_10_positive_negative

- XML file: `c_after_10.xml`
- Templates: `positive` / `negative`
- Candidate MITL: `F [10,infty) c`
- Proof class: `eventually_after_lower_bound`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements F [10,infty) c: an event c before the lower bound is not enough, while c with x >= 10 enters the positive accepting state. The negative template tracks the complementary prefix before the lower-bound witness appears.

Evidence: positive#5:l0->l1_a;label=c;guard=x >= 10;assign=<none>;accept=no->yes;initial=yes->no | negative#1:l0_a->l0_a;label=c;guard=x < 10;assign=<none>;accept=yes->yes;initial=yes->yes | negative#5:l0_a->l1;label=c;guard=x >= 10;assign=<none>;accept=yes->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/embedded_monitaal/c_after_10_monitor_test_intersection_test2.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/c_after_10_later_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/c_after_10_no_witness_inconclusive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/c_after_10_positive.input

Manual review notes: Manual reviewer should check finite-word no-c prefixes against the intended RV semantics.

### c_after_20_positive_negative

- XML file: `c_after_20.xml`
- Templates: `positive` / `negative`
- Candidate MITL: `F [20,infty) c`
- Proof class: `eventually_after_lower_bound`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements F [20,infty) c: an event c before the lower bound is not enough, while c with x >= 20 enters the positive accepting state. The negative template tracks the complementary prefix before the lower-bound witness appears.

Evidence: positive#8:l0->l1_a;label=c;guard=x >= 20;assign=<none>;accept=no->yes;initial=yes->no | negative#3:l0_a->l0_a;label=c;guard=x < 20;assign=<none>;accept=yes->yes;initial=yes->yes | negative#4:l0_a->l1;label=c;guard=x >= 20;assign=<none>;accept=yes->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/c_after_20_later_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/c_after_20_no_witness_inconclusive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/c_after_20_positive.input

Manual review notes: Manual reviewer should check finite-word no-c prefixes against the intended RV semantics.

### only_ab_until10_positive_negative

- XML file: `only_ab_until10.xml`
- Templates: `positive` / `negative`
- Candidate MITL: `G [0,10] (!c)`
- Proof class: `bounded_global_absence`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements G [0,10] (!c): labels other than c remain in the safe accepting region, while c with x <= 10 reaches the negative accepting state. The x > 10 edge keeps the positive template safe after the monitored interval.

Evidence: positive#2:l0_a->l1;label=c;guard=x <= 10;assign=<none>;accept=yes->no;initial=yes->no | positive#1:l0_a->l0_a;label=c;guard=x > 10;assign=<none>;accept=yes->yes;initial=yes->yes | negative#6:l0->l1_a;label=c;guard=x <= 10;assign=<none>;accept=no->yes;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/only_ab_until10_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/only_ab_until10_negative_boundary.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/only_ab_until10_positive_after_bound.input

Manual review notes: Manual reviewer should check whether XML lacks an explicit c > 10 negative escape because finite acceptance already represents the complement.

### recurGLB_positive_negative

- XML file: `recurGLB.xml`
- Templates: `positive` / `negative`
- Candidate MITL: `(F [0,10] p) && (G* (p -> F (0,10] p))`
- Proof class: `bounded_recurrence_after_event`
- Claim scope: Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence.

The XML pair implements (F [0,10] p) && (G* (p -> F (0,10] p)): a p event with c <= 10 satisfies either the initial obligation or a re-armed recurrence obligation and resets c. A p event with c > 10 reaches the negative accepting state. After each reset, the next response must be a later event, which accounts for the strict lower bound in the MITL subformula.

Evidence: positive#1:l0_a->l0_a;label=p;guard=c <= 10;assign=c := 0;accept=yes->yes;initial=yes->yes | negative#2:l0->l1_a;label=p;guard=c > 10;assign=<none>;accept=no->yes;initial=yes->no | positive#1:l0_a->l0_a;label=p;guard=c <= 10;assign=c := 0;accept=yes->yes;initial=yes->yes

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/recurGLB_first_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/recurGLB_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/recurGLB_timely_positive.input;/home/lqq/project/TAFuzz/tool/MoniTAal/test/models/recurGLBinput.txt

Manual review notes: The initial F [0,10] p obligation is witnessed by the same initial c <= 10 edge; the strict lower-bound (0,10] for later p responses follows from the reset-after-p event-index semantics rather than a separate XML guard.

### gear_control_properties_CloseClutch_NotCloseClutch

- XML file: `gear-control-properties.xml`
- Templates: `CloseClutch` / `NotCloseClutch`
- Candidate MITL: `G* (closeClutch -> F [0,150] clutchIsClosed)`
- Proof class: `gear_bounded_request_response`
- Claim scope: Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available.

The XML pair implements G* (closeClutch -> F [0,150] clutchIsClosed): the positive template is accepting before an obligation, the CloseClutch edge resets clock x, and the ClutchIsClosed edge with x <= 150 returns to an accepting state. The negative template reaches an accepting violation state on x > 150. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: CloseClutch#3:q_1->q0_a;label=ClutchIsClosed;guard=x <= 150;assign=<none>;accept=no->yes;initial=no->yes | NotCloseClutch#3:q1->q2_a;label=CloseClutch;guard=x > 150;assign=<none>;accept=no->yes;initial=no->no | CloseClutch#4:q0_a->q_1;label=CloseClutch;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | NotCloseClutch#8:q0->q1;label=CloseClutch;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_CloseClutch_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_CloseClutch_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_CloseClutch_rearmed_late_negative.input;/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/gear-control-input.txt

Manual review notes: Original gear-control-input baseline terminates with INCONCLUSIVE in this run; treat that as third-valued trace evidence, not Boolean satisfaction, violation, or XML-to-MITL equivalence proof. Generated reduced traces provide NEGATIVE late-response boundary evidence.

### gear_control_properties_OpenClutch_NotOpenClutch

- XML file: `gear-control-properties.xml`
- Templates: `OpenClutch` / `NotOpenClutch`
- Candidate MITL: `G* (openClutch -> F [0,150] clutchIsOpen)`
- Proof class: `gear_bounded_request_response`
- Claim scope: Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available.

The XML pair implements G* (openClutch -> F [0,150] clutchIsOpen): the positive template is accepting before an obligation, the OpenClutch edge resets clock x, and the ClutchIsOpen edge with x <= 150 returns to an accepting state. The negative template reaches an accepting violation state on x > 150. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: OpenClutch#3:q_1->q0_a;label=ClutchIsOpen;guard=x <= 150;assign=<none>;accept=no->yes;initial=no->yes | NotOpenClutch#3:q1->q2_a;label=OpenClutch;guard=x > 150;assign=<none>;accept=no->yes;initial=no->no | OpenClutch#4:q0_a->q_1;label=OpenClutch;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | NotOpenClutch#8:q0->q1;label=OpenClutch;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_OpenClutch_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_OpenClutch_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_OpenClutch_rearmed_late_negative.input;/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/gear-control-input.txt

Manual review notes: Original gear-control-input baseline terminates with INCONCLUSIVE in this run; treat that as third-valued trace evidence, not Boolean satisfaction, violation, or XML-to-MITL equivalence proof. Generated reduced traces provide NEGATIVE late-response boundary evidence.

### gear_control_properties_ReqNeu_NotReqNeu

- XML file: `gear-control-properties.xml`
- Templates: `ReqNeu` / `NotReqNeu`
- Candidate MITL: `G* (reqNeu -> F [0,200] gearNeu)`
- Proof class: `gear_bounded_request_response`
- Claim scope: Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available.

The XML pair implements G* (reqNeu -> F [0,200] gearNeu): the positive template is accepting before an obligation, the ReqNeu edge resets clock x, and the GearNeu edge with x <= 200 returns to an accepting state. The negative template reaches an accepting violation state on x > 200. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: ReqNeu#3:q_1->q0_a;label=GearNeu;guard=x <= 200;assign=<none>;accept=no->yes;initial=no->yes | NotReqNeu#3:q1->q2_a;label=ReqNeu;guard=x > 200;assign=<none>;accept=no->yes;initial=no->no | ReqNeu#4:q0_a->q_1;label=ReqNeu;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | NotReqNeu#8:q0->q1;label=ReqNeu;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_ReqNeu_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_ReqNeu_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_ReqNeu_rearmed_late_negative.input;/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/gear-control-input.txt

Manual review notes: Original gear-control-input baseline terminates with INCONCLUSIVE in this run; treat that as third-valued trace evidence, not Boolean satisfaction, violation, or XML-to-MITL equivalence proof. Generated reduced traces provide NEGATIVE late-response boundary evidence.

### gear_control_properties_ReqSet_NotReqSet

- XML file: `gear-control-properties.xml`
- Templates: `ReqSet` / `NotReqSet`
- Candidate MITL: `G* (reqSet -> F [0,300] gearSet)`
- Proof class: `gear_bounded_request_response`
- Claim scope: Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available.

The XML pair implements G* (reqSet -> F [0,300] gearSet): the positive template is accepting before an obligation, the ReqSet edge resets clock x, and the GearSet edge with x <= 300 returns to an accepting state. The negative template reaches an accepting violation state on x > 300. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: ReqSet#3:q_1->q0_a;label=GearSet;guard=x <= 300;assign=<none>;accept=no->yes;initial=no->yes | NotReqSet#3:q1->q2_a;label=ReqSet;guard=x > 300;assign=<none>;accept=no->yes;initial=no->no | ReqSet#4:q0_a->q_1;label=ReqSet;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | NotReqSet#8:q0->q1;label=ReqSet;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_ReqSet_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_ReqSet_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_ReqSet_rearmed_late_negative.input;/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/gear-control-input.txt

Manual review notes: Original gear-control-input baseline terminates with INCONCLUSIVE in this run; treat that as third-valued trace evidence, not Boolean satisfaction, violation, or XML-to-MITL equivalence proof. Generated reduced traces provide NEGATIVE late-response boundary evidence.

### gear_control_properties_SpeedSet_NotSpeedSet

- XML file: `gear-control-properties.xml`
- Templates: `SpeedSet` / `NotSpeedSet`
- Candidate MITL: `G* (speedSet -> F [0,500] reqTorque)`
- Proof class: `gear_bounded_request_response`
- Claim scope: Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available.

The XML pair implements G* (speedSet -> F [0,500] reqTorque): the positive template is accepting before an obligation, the SpeedSet edge resets clock x, and the ReqTorque edge with x <= 500 returns to an accepting state. The negative template reaches an accepting violation state on x > 500. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: SpeedSet#3:q_1->q0_a;label=ReqTorque;guard=x <= 500;assign=<none>;accept=no->yes;initial=no->yes | NotSpeedSet#3:q1->q2_a;label=SpeedSet;guard=x > 500;assign=<none>;accept=no->yes;initial=no->no | SpeedSet#4:q0_a->q_1;label=SpeedSet;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | NotSpeedSet#8:q0->q1;label=SpeedSet;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_SpeedSet_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_SpeedSet_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_SpeedSet_rearmed_late_negative.input;/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/gear-control-input.txt

Manual review notes: Original gear-control-input baseline terminates with INCONCLUSIVE in this run; treat that as third-valued trace evidence, not Boolean satisfaction, violation, or XML-to-MITL equivalence proof. Generated reduced traces provide NEGATIVE late-response boundary evidence.

### gear_control_properties_test1_Nottest1

- XML file: `gear-control-properties.xml`
- Templates: `test1` / `Nottest1`
- Candidate MITL: `G* (test1 -> F [0,900] reqTorque)`
- Proof class: `gear_bounded_request_response`
- Claim scope: Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available.

The XML pair implements G* (test1 -> F [0,900] reqTorque): the positive template is accepting before an obligation, the test1 edge resets clock x, and the ReqTorque edge with x <= 900 returns to an accepting state. The negative template reaches an accepting violation state on x > 900. Thus every observed request/trigger must be followed by the response within the closed bound.

Evidence: test1#3:q_1->q0_a;label=ReqTorque;guard=x <= 900;assign=<none>;accept=no->yes;initial=no->yes | Nottest1#3:q1->q2_a;label=test1;guard=x > 900;assign=<none>;accept=no->yes;initial=no->no | test1#4:q0_a->q_1;label=test1;guard=<none>;assign=x := 0;accept=yes->no;initial=yes->no | Nottest1#8:q0->q1;label=test1;guard=<none>;assign=x := 0;accept=no->no;initial=yes->no

Trace evidence: /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_test1_boundary_positive.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_test1_initial_late_negative.input;/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/generated_monitaal_inputs/gear_test1_rearmed_late_negative.input;/home/lqq/project/TAFuzz/tool/MoniTAal/benchmark/gear-control-input.txt

Manual review notes: Original gear-control-input baseline terminates with INCONCLUSIVE in this run; treat that as third-valued trace evidence, not Boolean satisfaction, violation, or XML-to-MITL equivalence proof. Generated reduced traces provide NEGATIVE late-response boundary evidence.

## Excluded Rows

The following rows are intentionally excluded from the formal XML-to-MITL translation claim in this draft.

| manifest_id | status | reason |
|---|---|---|
| `absentBQR_positive_negative` | `EXCLUDED_APPROXIMATE` | Excluded from formal translation claims because the MITL candidate is approximate. |
| `delay_example_positive_negative` | `EXCLUDED_NO_MITL_CANDIDATE` | Excluded because no conservative MITL candidate is claimed. |
| `f_g_notb_and_g_f_a_positive_negative` | `EXCLUDED_APPROXIMATE` | Excluded from formal translation claims because the MITL candidate is approximate. |
| `never_b_positive_negative` | `EXCLUDED_NO_MITL_CANDIDATE` | Excluded because no conservative MITL candidate is claimed. |
| `recurBQR_positive_negative` | `EXCLUDED_APPROXIMATE` | Excluded from formal translation claims because the MITL candidate is approximate. |
| `time_must_pass_positive_negative` | `EXCLUDED_NO_MITL_CANDIDATE` | Excluded because no conservative MITL candidate is claimed. |
| `b_live_a_freq_positive_negative` | `EXCLUDED_APPROXIMATE` | Excluded from formal translation claims because the MITL candidate is approximate. |
| `gear_controller_test_positive_negative` | `EXCLUDED_NO_MITL_CANDIDATE` | Excluded because no conservative MITL candidate is claimed. |
