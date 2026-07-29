# TLS 排除与待修候选

## 研究阶段排除：_staging/transport_security_protocols/tls/excluded.md

# TLS excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| KeyUpdate response before next application data | `NO_NUMERIC_BOUND` | RFC 8446 orders messages but provides no numeric deadline. |
| PSK ticket-age freshness tolerance | `NO_NUMERIC_BOUND` | The acceptance tolerance is implementation-defined. |
| TLS handshake timeout | `NO_PUBLIC_NORMATIVE_TEXT` | RFC 8446 defines no general numeric handshake timeout. |
| close_notify timing | `NO_NUMERIC_BOUND` | The alert ordering requirement has no numeric interval. |
| Record/key usage limits | `FORMULA_UNSUPPORTED` | Limits are record/byte counters, not elapsed-time obligations. |
| Server ticket_lifetime field <= 604800 | `TRACE_NOT_DECISIVE` | This is a message-field invariant; the timed catalog instead monitors client usability/cache lifetime. |
| Client ticket usability/cache lifetime | `INDEPENDENT_AUDIT_REJECT` | The first extraction used an adapter-derived `became_unusable` event, making the consequent self-fulfilling; the locked source has no fixed cache/use transition that proves expiry at seven days. |

## 自动质量门拒绝

- `TLS13-TICKET-01` TLS 1.3 tickets become unusable within seven days: `AP_WITHOUT_SOURCE_MAPPING:tls13_ticket_became_unusable,tls13_ticket_cached,tls13_ticket_removed, INDEPENDENT_AUDIT_REJECT, PRIMARY_SOURCE_APS_MISSING_OR_EMPTY, UNKNOWN_OR_UNAPPROVED_AUDIT_STATUS:REJECT_OR_FIX, UNSTRUCTURED_SOURCE_URLS:https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/statem/statem_clnt.c#L2574-L2665`
