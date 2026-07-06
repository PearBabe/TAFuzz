# Review Guide

This generated guide explains how to use the TAMonitor paper-review packet.
It is intentionally conservative: it tells reviewers when evidence is usable, caveated, deferred, or excluded.

## Sections

- `benchmark_caveats`: 1
- `bug_fix_loop`: 1
- `correctness_evidence`: 1
- `current_status`: 2
- `decision_options`: 5
- `entrypoint`: 1
- `paper_claims`: 1
- `reproducibility`: 1
- `xml_translation`: 2

## Guide Rows

| guide_id | priority | section | instruction | decision_rule | must_not_claim |
|---|---|---|---|---|---|
| `RG_START_HERE` | `P0` | `entrypoint` | Start with Review Queue, then Review Signoff. There are 44 P0 rows and 10 P1 rows; inspect P0 rows before paper wording. | No paper-facing claim may be promoted from REVIEW_REQUIRED, BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF, or timeout-caveat status without a filled signoff row. | Do not treat generated queues or templates as human approval. |
| `RG_DECISION_APPROVE_AS_CLAIMED` | `P0` | `decision_options` | `APPROVE_AS_CLAIMED` means the reviewer accepts the row's current claim scope exactly as stated. | Use only when evidence, proof notes, caveats, and must_not_claim text are all consistent with the final paper statement. | Do not use APPROVE_AS_CLAIMED for rows with unresolved timeout, approximate, or v2-deferred evidence debt. |
| `RG_DECISION_APPROVE_WITH_CAVEAT` | `P0` | `decision_options` | `APPROVE_WITH_CAVEAT` means the claim can be cited only with the exact caveat shown in the evidence sheets. | Use for timeout, generated/reduced-trace, compflatten build-only, or BDD-projection-only claims that remain useful but bounded. | Do not collapse caveated rows into verified correctness or theorem-level equivalence claims. |
| `RG_DECISION_REJECT_OR_FIX` | `P0` | `decision_options` | `REJECT_OR_FIX` means the row exposes a real defect, unsupported claim, or inadequate evidence. | Use when a row has inconsistent evidence, failed audit status, or a claim that cannot be justified by its proof/baseline/oracle artifacts. | Do not leave REJECT_OR_FIX rows for the user to repair without recording the bug or required code/data fix. |
| `RG_DECISION_DEFER_TO_V2` | `P1` | `decision_options` | `DEFER_TO_V2` means the scope is intentionally reserved for a later BDD-native or composition-aware implementation. | Use for BDD-native runtime or compflatten runtime claims until a real implementation and oracle suite exist. | Do not claim BDD-native runtime, BDD-native speedups, or compflatten runtime RV in v1. |
| `RG_DECISION_KEEP_EXCLUDED` | `P1` | `decision_options` | `KEEP_EXCLUDED` means the row remains in inventory for transparency but is outside formal claims. | Use for internal Count forms, approximate XML candidates, no-candidate XML rows, and rows with unresolved proof debt. | Do not infer MITL equivalence from XML file names or from parser-visible internal forms. |
| `RG_MITL_ORACLE_BOUNDARY` | `P0` | `correctness_evidence` | MITL runtime correctness claims rely on hand-oracle derivations: 70 verified rows and 17 construction/stat-only rows. | Only rows marked HAND_ORACLE_VERIFIED/VERIFIED and prefix-match evidence may support runtime correctness claims. | Do not count construction/stat-only rows or missing oracle rows as runtime correctness evidence. |
| `RG_XML_PROOF_BOUNDARY` | `P0` | `xml_translation` | XML-to-MITL rows are structural proof drafts; use XML Obligations, XML Trace Coverage, and Original Trace Gaps first to separate machine-checked prerequisites from human theorem-review obligations. | A proof-ready row may be promoted only after all machine-checkable obligations have no FAIL status and the reviewer signs off that the candidate MITL formula matches the XML pair under the stated trace assumptions. | Do not claim all MoniTAal XML benchmarks were equivalently converted to MITL. |
| `RG_XML_ORIGINAL_TRACE_GAPS` | `P0` | `xml_translation` | Original Trace Gaps lists proof-ready XML rows whose repository/original timed-word evidence is missing or INCONCLUSIVE; every XML_ORIGINAL_TRACE_GAP_* row needs an explicit human caveat or a decisive original trace. | Use APPROVE_WITH_CAVEAT only if the paper wording keeps the original-input provenance caveat; use REJECT_OR_FIX if the paper claim requires decisive original-input evidence. | Do not use APPROVE_AS_CLAIMED for generated-only or INCONCLUSIVE original-input provenance gaps. |
| `RG_PAPER_CLAIM_AUDIT` | `P1` | `paper_claims` | Paper claim consistency audit has 0 FAIL rows; use it as a safety check, not as a mathematical proof. | A PASS claim audit means no generated consistency issue was found; human signoff is still required for proof-ready body rows. | Do not call generated proof ledgers final theorem proofs without reviewer approval. |
| `RG_TIMEOUT_POLICY` | `P1` | `benchmark_caveats` | MoniTAal baseline has 0 timeout rows, 0 skipped-no-input rows, and 3 generated empty probes for XML pairs without repository inputs; completed baseline rows may still be INCONCLUSIVE. | Rows with a MoniTAal verdict can support trace-level final-verdict comparison; timeout and skipped-input rows cannot. | Do not report generated empty probes, skipped-input rows, or INCONCLUSIVE baseline matches as XML-to-MITL equivalence proofs or original-input benchmark evidence. |
| `RG_REPRODUCIBILITY` | `P1` | `reproducibility` | Tie any paper table or manual decision to the matching result directory and reproducibility manifest. | Every cited result should point to a concrete output directory, command, source hash, result hash, and dirty-worktree state. | Do not separate copied tables from the matching manifest and workbook. |
| `RG_RERUN_AFTER_FIX` | `P1` | `bug_fix_loop` | If any review row exposes a real bug, fix the cause, rerun the full experiment, regenerate the workbook, and update handoff files. | A fix is accepted only when the relevant audit rows and regression outputs pass after rerun. | Do not patch expected results or weaken oracle semantics to make a test pass. |
| `RG_CURRENT_SIGNOFF_STATUS` | `P0` | `current_status` | The generated signoff template currently has 56 blank reviewer decisions; this is expected before human review. | Blank reviewer decisions mean the artifact is ready for review, not signed off. | Do not state that human review is complete until decisions are filled and checked. |
| `RG_SIGNOFF_IMPORT_ROUNDTRIP` | `P0` | `current_status` | After manual review, import reviewer-owned fields from a filled CSV or Review Signoff workbook sheet instead of hand-editing generated queue, policy, or evidence columns. | Only reviewer_decision, reviewer, review_date, and reviewer_notes are human-owned import fields; generated evidence and decision-policy fields must match the current packet. | Do not overwrite generated signoff rows with a stale workbook export or cite completed human signoff before complete-mode validation passes. |
