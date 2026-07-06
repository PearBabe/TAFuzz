# Formula Input Policy Audit

This generated audit checks that parser-visible internal Count forms are rejected with a controlled TAMonitor diagnostic.
These probes are not MITL semantic regression cases and are not counted as user-level formula correctness evidence.
The concrete probe formulas are intentionally redacted from the review table; use the `form` token and diagnostic class for review.

## Counts

- `PASS`: 8

## Rows

| policy_id | form | expected | actual | pass_status | assert_like_failure |
|---|---|---|---|---|---|
| `internal_count_input_CFn` | `CFn` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_CFn_star` | `CFn*` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_COn` | `COn` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_COn_star` | `COn*` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_CGn` | `CGn` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_CGn_star` | `CGn*` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_CHn` | `CHn` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
| `internal_count_input_CHn_star` | `CHn*` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `EXPLICIT_UNSUPPORTED_USER_FORMULA` | `PASS` | `false` |
