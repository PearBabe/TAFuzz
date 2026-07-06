# TAMonitor Final Results

This directory has been cleaned to keep only the final review packet and the
small set of entrypoint files needed for manual inspection.

## Main Review Packet

- Packet directory:
  `paper_pipeline_formula_catalog_workbook_guard_full/`
- Main workbook:
  `paper_pipeline_formula_catalog_workbook_guard_full/paper_review_results.xlsx`
- Pipeline summary:
  `paper_pipeline_formula_catalog_workbook_guard_full/pipeline_summary.json`
- Review-packet verifier:
  `paper_pipeline_formula_catalog_workbook_guard_full/review_packet_verification.json`
- Artifact manifest:
  `paper_pipeline_formula_catalog_workbook_guard_full/pipeline_artifact_manifest.json`
- Human review/signoff template:
  `paper_pipeline_formula_catalog_workbook_guard_full/review_signoff_template.md`

## MITL Formula Catalog Entrypoints

- `mitl_formula_catalog_latest_official.md`
- `mitl_formula_catalog_semantic_regression.csv`
- `mitl_formula_catalog_monitaal_xml_candidates.csv`
- `mitl_formula_catalog_runtime_runs.csv`

## Retained Supporting Packet

- `baseline_timeout_rerun_60s_formula_catalog_workbook_guard_full/`

The supporting packet is retained because the final review packet references
the 60-second timeout rerun evidence for MoniTAal baseline stability.

## Latest Verified Counts

- Full pipeline: PASS, failed steps 0.
- Semantic regression: 87 cases, 70 runtime-verified, 0 fail/error/timeout.
- Candidate/baseline: 63/63 matched, 0 timeout after the 60-second rerun.
- Review packet verifier: 151 PASS, 0 WARN, 0 FAIL.
- Artifact manifest verifier: 16 PASS, 0 WARN, 0 FAIL.
- Stability audit: 190 PASS, 0 WARN, 0 FAIL.
- CLI contract: 11 PASS, 0 FAIL.

## Scope Notes

- TAMonitor v1 supports flatten-mode runtime monitoring.
- BDD-native runtime and compflatten runtime are intentionally reserved
  interfaces in v1 and are not claimed as implemented.
- XML-to-MITL equivalence rows marked `REVIEW_REQUIRED` still require human
  mathematical review; no human approval is claimed by this packet.
