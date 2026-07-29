# Review Signoff Validation

This validates the paper-review signoff state. It does not make human decisions.

## Summary

- mode: `pre-review`
- completion_state: `READY_FOR_HUMAN_REVIEW_NOT_SIGNED`
- PASS: 16
- FAIL: 0
- signoff_rows: 56
- blank_decisions: 56
- nonblank_decisions: 0
- policy_mismatch_rows: 0
- forbidden_decision_rows: 0
- unresolved_evidence_tokens: 0
- missing_queue_evidence_rows: 0
- unresolved_queue_evidence_tokens: 0
- unresolved_source_sheet_tokens: 0
- unresolved_source_rows: 0
- unresolved_queue_source_sheet_tokens: 0
- unresolved_queue_source_rows: 0

## Checks

| check_id | status | category | observed | reviewer_action |
|---|---|---|---|---|
| `SIGNOFF_FILES_PRESENT` | `PASS` | `artifact_presence` | queue_exists=True; signoff_exists=True | Regenerate the review packet if either file is missing. |
| `SIGNOFF_REQUIRED_COLUMNS` | `PASS` | `schema` | missing_signoff=; missing_queue= | Do not use a signoff sheet with missing review columns. |
| `SIGNOFF_QUEUE_COVERAGE` | `PASS` | `coverage` | expected=56; actual=56; missing=; extra= | Fix queue/signoff generation before asking for human signoff. |
| `SIGNOFF_PRIORITY_AND_REQUIRED_FLAGS` | `PASS` | `schema` | bad_priority=; missing_required= | Only paper-facing P0/P1/P2 rows should require signoff. |
| `SIGNOFF_QUEUE_FIELD_SYNC` | `PASS` | `coverage` | mismatched= | Regenerate signoff rows if they drift from the review queue. |
| `SIGNOFF_ALLOWED_DECISIONS` | `PASS` | `decision_policy` | bad_allowed=; invalid_decisions= | Use only the allowed signoff decisions. |
| `SIGNOFF_DECISION_SCOPE_POLICY` | `PASS` | `decision_policy` | policy_mismatch=; forbidden_decisions= | Use recommended_decision/completion_requirements as guidance; never approve rows whose policy forbids that decision. |
| `SIGNOFF_EVIDENCE_FIELDS_PRESENT` | `PASS` | `reviewability` | missing_evidence_fields= | Do not ask for signoff on rows without enough review context. |
| `SIGNOFF_EVIDENCE_RESOLUTION` | `PASS` | `reviewability` | unresolved= | Fix evidence_artifacts before asking for human signoff; use concrete files or explicit glob: patterns for generated run artifacts. |
| `QUEUE_EVIDENCE_FIELDS_PRESENT` | `PASS` | `reviewability` | missing_evidence_fields= | Do not ask reviewers to use queue rows without enough review context. |
| `QUEUE_EVIDENCE_RESOLUTION` | `PASS` | `reviewability` | unresolved= | Fix queue evidence_artifacts before asking for manual review. |
| `SIGNOFF_SOURCE_SHEET_RESOLUTION` | `PASS` | `reviewability` | unresolved= | Fix source_sheet names before asking reviewers to follow workbook references. |
| `SIGNOFF_SOURCE_ROW_RESOLUTION` | `PASS` | `reviewability` | unresolved= | Fix dangling source_id values before using the signoff row for human review. |
| `QUEUE_SOURCE_SHEET_RESOLUTION` | `PASS` | `reviewability` | unresolved= | Fix source_sheet names before using the queue for manual review. |
| `QUEUE_SOURCE_ROW_RESOLUTION` | `PASS` | `reviewability` | unresolved= | Fix dangling source_id values before using the queue for manual review. |
| `SIGNOFF_PRE_REVIEW_BLANK` | `PASS` | `completion_boundary` | blank_decisions=56; nonblank_decisions=0 | Blank decisions mean ready for review, not approved. |
