# Manual Review Checklist

This generated checklist is the human-review entry point for the TAMonitor paper experiment packet.
It summarizes where each claim should be reviewed and what must not be claimed from the current evidence.

## Counts

- human_decision_required: 13
- `PASS`: 10
- `PASS_WITH_CAVEAT`: 2
- `REVIEW_REQUIRED`: 4
- `V1_DEFERRED`: 1

## Rows

| review_id | status | human_required | question | evidence | must_not_claim |
|---|---|---|---|---|---|
| `MR_HAND_ORACLE_FINAL_VERDICTS` | `PASS` | `true` | Do the manually specified final verdict oracles match TAMonitor output for all claimed MITL semantic cases? | semantic_verified=70; oracle_verified=70; build_only_not_oracle=17; oracle_review_required=0; semantic_fail=0. | Do not claim cases with build-only, timeout, resource-limit, or missing-oracle statuses as verified correctness. |
| `MR_PREFIX_ORACLE` | `PASS` | `true` | Does each recorded timed-word prefix verdict match the hand oracle where an oracle is defined? | prefix_matches=146; prefix_mismatches=0; missing_observed_steps=0; oracle_derivation_prefix_mismatches=0. | Do not use final-verdict correctness alone as evidence for per-prefix runtime verification. |
| `MR_FINITE_INFINITE_WORD_MODES` | `PASS` | `true` | Are finite-word and infinite-word claims backed by separate hand-oracle rows? | finite_verified=34; infinite_verified=36. | Do not generalize finite-word theorem claims beyond the operator-level cases present in this suite. |
| `MR_MIGHTYPPL_SYNTAX_COVERAGE` | `PASS` | `true` | Does every user-level MightyPPL grammar construct have runtime evidence, build/stat evidence, or an explicit exclusion? | syntax_rows=45; runtime_verified=36; internal_excluded=8; missing=0. | Do not list internal Count forms as ordinary user MITL formulas. |
| `MR_INTERNAL_COUNT_INPUT_BOUNDARY` | `PASS` | `true` | Are CFn/COn/CGn/CHn and starred variants excluded from MITL semantic tests and rejected through controlled diagnostics? | exclusion_rows=8; input_policy_pass=8; input_policy_fail=0; assert_like_failures=0. | Do not disclose or count redacted internal-form probes as MITL runtime-oracle formulas. |
| `MR_BDD_PROJECTION_RUNTIME` | `PASS` | `false` | Did flatten-mode runtime rows record positive and negative BDD valuation projection counts? | flatten_projection_rows=70. | Do not claim BDD-native runtime performance from valuation-projection evidence. |
| `MR_CLI_CONTRACT` | `PASS` | `false` | Does the TAMonitor command surface work for file/inline formula input, trace-file/stdin input, modes, reports, BDD metadata, and controlled errors? | cli_contract_rows=11; pass=11; fail=0; controlled_error_paths=5. | Do not claim an industrial CLI surface if any CLI contract probe fails. |
| `MR_COMPFLATTEN_SCOPE` | `PASS_WITH_CAVEAT` | `true` | Is compflatten represented only as construction/statistics evidence, never as a v1 runtime verdict? | compflatten_build_stats_rows=17. | Do not claim compflatten runtime RV until a composition-aware or BDD-native monitor is implemented. |
| `MR_XML_TRANSLATION_SCOPE` | `REVIEW_REQUIRED` | `true` | Which MoniTAal XML benchmark pairs are genuinely reviewable MITL candidates, and which remain excluded? | manifest_rows=23; proof_ready=15; excluded=8. | Do not state that all XML benchmarks were equivalently converted to MITL. |
| `MR_XML_EDGE_PROOFS` | `REVIEW_REQUIRED` | `true` | Do the edge/guard proof rows justify each candidate MITL pattern at trace level? | proof_appendix_ready=15; proof_appendix_excluded=8. | Do not treat the generated proof ledger as a final theorem without human proof review. |
| `MR_XML_ORIGINAL_TRACE_GAPS` | `REVIEW_REQUIRED` | `true` | Do the remaining XML original-input provenance gaps have explicit human-review decisions and caveats? | gap_rows=8; review_required=8; fail=0; classes=no_repository_input_found:2;repository_input_inconclusive:6 | Do not treat generated review traces or INCONCLUSIVE repository traces as decisive original benchmark evidence. |
| `MR_PAPER_CLAIM_BOUNDARIES` | `REVIEW_REQUIRED` | `true` | Do paper-facing claim labels preserve timeout, approximate, and excluded-row caveats? | claim_audit_fail=0; claim_audit_warn=0; body_ready_after_signoff=15; timeout_caveat_claims=0. | Do not move BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF rows into paper body text before human signoff. |
| `MR_BASELINE_TIMEOUT_CAVEATS` | `PASS` | `true` | Are MoniTAal baseline timeout and no-input rows handled according to their actual status? | candidate_matches=63; candidate_mismatches=0; candidate_not_verified=0; baseline_timeouts=0; skipped_no_input=0; generated_empty_no_original_input=3. | Do not report skipped-no-input or generated-empty rows as original benchmark-input matches, and do not reinterpret INCONCLUSIVE as POSITIVE or NEGATIVE. |
| `MR_GEAR_BASELINE_EVIDENCE` | `PASS` | `true` | Do gear benchmark rows record original-input MoniTAal baseline matches while still requiring human XML-to-MITL proof signoff? | gear_body_ready_after_signoff=6; gear_timeout_caveat_claims=0; baseline_timeouts=0; skipped_no_input=0. | Do not treat gear baseline matches as automatic XML-to-MITL equivalence proofs. |
| `MR_CANDIDATE_STEP_AUDIT` | `PASS_WITH_CAVEAT` | `false` | Did every TAMonitor candidate run expose all mapped trace steps in the compact step audit? | candidate_step_rows=63; complete=63; incomplete=0. | Do not infer correctness from step completeness without baseline or hand-oracle evidence. |
| `MR_BDD_NATIVE_DEFERRAL` | `V1_DEFERRED` | `true` | Is BDD-native runtime clearly reserved rather than falsely implemented in v1? | bdd_interface_metadata=reserved_not_implemented. | Do not claim BDD-native runtime monitoring or BDD-native speedups in v1. |
| `MR_REPRODUCIBILITY_PACKET` | `PASS` | `false` | Does the experiment packet record command, tool paths, dirty git state, source hashes, and result hashes? | reproducibility_manifest_generation=present. | Do not present results without the matching result directory and reproducibility manifest. |
