# Manual XML Candidate Review

This file records manual-review guidance for the XML-to-MITL candidate layer.
It is generated with the experiment artifacts and is not an automatic
equivalence proof. Authoritative evidence tables:

- `monitaal_translation_review.csv`
- `monitaal_transition_details.csv`
- `translation_candidate_results.csv`
- `monitaal_baseline_results.csv`
- `benchmark_manifest.csv`
- `xml_edge_guard_proofs.csv`
- `xml_proof_appendix.csv`
- `xml_translation_proof_appendix.md`
- `paper_claim_review.csv`
- `paper_claim_review.md`

## Strong Trace-Level Candidates

These candidates have clear transition/guard structure and match the available
MoniTAal baseline input. They may be treated as strong trace-level candidates
for paper review, but still require formal equivalence proof before being
claimed as fully translated benchmarks.

- `a-b copy.xml`, `a-b.xml`, `a-b30.xml`: `G* (a -> F [0,30] b)`
- `absentAQ.xml`: `G* (q -> G [0,10] (!p))`
- `absentBR.xml`: `G* (p -> G [0,10] (!r))`
- `recurGLB.xml`: `(F [0,10] p) && (G* (p -> F (0,10] p))`
- `c_after_10.xml`: `F [10,infty) c` on generated traces
  `@0 a; @10 c` and `@0 a; @11 c`
- `c_after_20.xml`: `F [20,infty) c` on generated traces
  `@0 a; @20 c` and `@0 a; @21 c`
- `only_ab_until10.xml`: `G [0,10] (!c)` on generated trace `@0 a; @5 c`
- Gear-controller request/response templates: `G* (request -> F [0,bound] response)`
  on generated reduced negative traces where either the first observed request
  is answered just after the closed bound or one boundary-satisfied request is
  followed by a re-armed late-response violation.

## Edge/Guard Proof Ledger

`xml_edge_guard_proofs.csv` records one machine-checkable proof-review row per
XML pair. `EDGE_GUARD_PROOF_READY` means the expected trigger/response or
forbidden-event edges, clock bounds, resets, and accepting-location roles were
found in the parsed XML. It is still a proof checklist for human review, not a
published theorem by itself.

`xml_translation_proof_appendix.md` is a paper-facing draft derived from the
proof ledger. It includes only `PROOF_DRAFT_READY` rows in the formal proof
section and lists approximate, unclaimed, and input-debt rows separately.

`recurGLB.xml` includes both an initial closed-bound recurrence obligation and
later re-armed recurrence obligations. The strict lower bound in
`F (0,10] p` is justified from the reset-after-p event-index semantics rather
than a separate XML guard; the corresponding evidence row records this caveat.

## Must Remain Approximate Or Unpromoted

- `absentBQR.xml` and `recurBQR.xml`: translation table marks these
  approximate; one matching input is not enough for equivalence.
- `b_live_a_freq.xml`: approximate; use the current baseline-status section
  below instead of carrying forward stale timeout wording.
- `f(g(notb)_and_g(f(a)).xml`: corrected candidate
  `(F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b))` has reduced
  negative trace evidence for first-late and re-armed-late `a`, but the
  eventual no-b liveness suffix and finite-prefix semantics still need proof
  review, so it remains approximate.
- `delay-example.xml`, `never_b.xml`, `time-must-pass.xml`,
  `gear_controller_test.xml`: no claimed MITL candidate.

## Baseline Timeout Cases

This run has no MoniTAal baseline timeout rows. Do not describe any current benchmark input as timed out from this packet.

INCONCLUSIVE baseline rows are third-valued trace evidence. They are not Boolean satisfaction, not Boolean violation, and not XML-to-MITL equivalence proofs.
Examples: :a_b30_boundary_positive.input; :a_b_boundary_positive.input; :a_b_copy_boundary_positive.input; :absentAQ_safe_after_bound_positive.input; :absentBR_safe_after_bound_positive.input; :b_live_a_freq_generated.input; :c_after_10_no_witness_inconclusive.input; :c_after_20_no_witness_inconclusive.input; :gear-control-input.txt; :gear_CloseClutch_boundary_positive.input; :gear_OpenClutch_boundary_positive.input; :gear_ReqNeu_boundary_positive.input; ...

## Open Review Questions

- For any future timeout row, rerun with a longer timeout or document a justified
  reduced input; for INCONCLUSIVE rows, keep the third-valued caveat explicit.
- Add formal edge/guard proofs before claiming full XML-to-MITL equivalence;
  the current manifest remains a trace-level promotion ledger.
