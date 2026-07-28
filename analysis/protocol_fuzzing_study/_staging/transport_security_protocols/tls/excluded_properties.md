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
