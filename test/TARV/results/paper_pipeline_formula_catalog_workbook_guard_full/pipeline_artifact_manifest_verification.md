# Pipeline Artifact Manifest Verification

This verifies the generated pipeline artifact manifest. It is a post-manifest sidecar and is not hashed by the manifest itself.

## Summary

- PASS: 16
- WARN: 0
- FAIL: 0
- manifest_rows: 151

## Checks

| check_id | status | category | observed | action |
|---|---|---|---|---|
| `MANIFEST_FILES_PRESENT` | `PASS` | `artifact_presence` | csv=True; json=True; md=True | Regenerate the full pipeline if the manifest files are missing. |
| `MANIFEST_SCHEMA` | `PASS` | `schema` | missing= | Do not use a manifest with missing hash columns. |
| `MANIFEST_JSON_ROW_COUNT` | `PASS` | `schema` | csv_rows=151; json_rows=151 | Regenerate the manifest if CSV and JSON diverge. |
| `MANIFEST_NO_DUPLICATE_KEYS` | `PASS` | `content` | duplicates= | Fix duplicate manifest rows before using hash evidence. |
| `MANIFEST_NO_SELF_HASH` | `PASS` | `content` | self_rows= | Keep the manifest non-self-referential. |
| `MANIFEST_HASH_AND_SIZE_MATCH` | `PASS` | `content` | missing=0; bad_hashes=0; bad_sizes=0 | Regenerate the pipeline packet if any hash or size does not match. |
| `MANIFEST_REQUIRED_RESULT_COVERAGE` | `PASS` | `coverage` | missing= | Add missing review-critical artifacts to the pipeline manifest. |
| `MANIFEST_HARDCODED_BENCHMARK_COVERAGE` | `PASS` | `coverage` | hardcoded_expected=True; missing= | Hash monitaal_hardcoded_benchmarks.csv/json/md when the pipeline advertises hard-coded benchmark evidence. |
| `MANIFEST_SIGNOFF_EVIDENCE_COVERAGE` | `PASS` | `coverage` | signoff_evidence_expected=True; missing= | Hash review_signoff_evidence_bundle.csv/json/md when the pipeline advertises signoff evidence-bundle review artifacts. |
| `MANIFEST_SIGNOFF_ROUNDTRIP_COVERAGE` | `PASS` | `coverage` | roundtrip_expected=True; missing= | Hash signoff_import_roundtrip_audit.csv/json/md when the pipeline advertises synthetic import-roundtrip evidence. |
| `MANIFEST_XML_PROOF_OBLIGATION_COVERAGE` | `PASS` | `coverage` | xml_obligation_expected=True; missing= | Hash xml_proof_obligations.csv/json/md when proof-obligation review artifacts are generated. |
| `MANIFEST_XML_TRACE_COVERAGE` | `PASS` | `coverage` | xml_trace_expected=True; missing= | Hash xml_trace_coverage_obligations.csv/json/md when trace-coverage review artifacts are generated. |
| `MANIFEST_XML_ORIGINAL_TRACE_GAPS` | `PASS` | `coverage` | xml_gap_expected=True; missing= | Hash xml_original_trace_gaps.csv/json/md when original trace-gap review artifacts are generated. |
| `MANIFEST_COMMAND_LOG_COVERAGE` | `PASS` | `coverage` | commands=13; missing_logs= | Hash all command logs so command evidence is reproducible. |
| `MANIFEST_TIMEOUT_RERUN_COVERAGE` | `PASS` | `coverage` | timeout_expected=True; missing= | Hash timeout-rerun artifacts when a timeout-rerun directory is part of the packet. |
| `MANIFEST_CATEGORY_COVERAGE` | `PASS` | `coverage` | counts={"command_log": 26, "result_file": 122, "timeout_rerun_file": 3} | Regenerate manifest if an expected artifact category is empty. |
