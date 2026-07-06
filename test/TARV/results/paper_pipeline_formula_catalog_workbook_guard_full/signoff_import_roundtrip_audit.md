# Signoff Import Roundtrip Audit

This is a synthetic regression check for the supported Review Signoff import workflow.
It does not record human mathematical approval.

## Summary

- PASS: 7
- FAIL: 0
- synthetic_only: `True`
- human_signoff_claim: `not_claimed`

## Checks

| check_id | status | category | observed | reviewer_boundary |
|---|---|---|---|---|
| `ROUNDTRIP_CSV_DRY_RUN` | `PASS` | `import_roundtrip` | returncode=0; status=PASS; applied=False; imported_nonblank_decisions=56; expected_signoff_rows=56; errors=; stderr= | Synthetic decisions are not human approval. |
| `ROUNDTRIP_XLSX_BLANK_EXTRACTION` | `PASS` | `import_roundtrip` | returncode=0; status=PASS; import_rows=56; expected_signoff_rows=56; imported_nonblank_decisions=0; errors=; stderr= | Blank workbook extraction means ready for review, not signed off. |
| `ROUNDTRIP_CSV_APPLY` | `PASS` | `import_roundtrip` | returncode=0; status=PASS; applied=True; imported_nonblank_decisions=56; expected_signoff_rows=56; errors=; stderr= | Apply happened only in a temporary packet copy. |
| `ROUNDTRIP_COMPLETE_VALIDATION` | `PASS` | `complete_mode` | returncode=0; completion_state=HUMAN_SIGNOFF_COMPLETE; pass=16; fail=0; nonblank_decisions=56; expected_signoff_rows=56; stderr= | Synthetic complete mode proves command behavior, not human math approval. |
| `ROUNDTRIP_COMPLETE_WORKBOOK_REBUILD` | `PASS` | `complete_mode` | returncode=0; status=ok; workbook_path=/tmp/tamonitor_signoff_roundtrip_0y_gk0yv/packet/paper_review_results.xlsx; timeout_summary=True; timeout_details=True; stderr= | Workbook rebuild happened only in the temporary packet copy. |
| `ROUNDTRIP_COMPLETE_PACKET_VERIFICATION` | `PASS` | `complete_mode` | returncode=0; pass=138; fail=0; check_rows=138; failed_checks=; stderr= | Synthetic complete packet is a regression fixture only. |
| `ROUNDTRIP_STALE_GENERATED_FIELD_REJECTED` | `PASS` | `negative_import` | returncode=1; status=FAIL; immutable_field_mismatches=1; applied=False; stderr= | Generated fields remain owned by the packet generator. |
