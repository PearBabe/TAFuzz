# DTLS 排除与待修候选

## 研究阶段排除：_staging/transport_security_protocols/dtls/excluded.md

# DTLS excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| RFC 9147 DTLS 1.3 ACK delay <= RTO/4 | `VERSION_MISMATCH` | ProFuzzBench TinyDTLS and OpenSSL 0437435a implement DTLS 1.2, not DTLS 1.3. |
| RFC 9147 DTLS 1.3 ACK/retransmission state machine | `VERSION_MISMATCH` | No selected mature benchmark implementation at the locked revision implements the RFC 9147 state machine. |
| TinyDTLS initial 1-second timer mapping | `VERSION_MISMATCH` | `assist-project/tinydtls-fuzz@06995d4...` sets `n->timeout = 2 * DTLS_TICKS_PER_SECOND`, while RFC 6347 recommends 1 second. It is retained as a differential test target, not source evidence for the 1-second oracle. |
| Duplicate peer flight causes immediate retransmission | `PUNCTUAL_ONLY` | RFC 6347 says transition/retransmit on receipt but has no positive numeric bound. |
| Complete expected flight cancels timer | `NO_NUMERIC_BOUND` | Normative state-machine behavior but no numeric interval; it is already used as a discharge event in bounded timer properties. |
| Reset timer after long idle >=10*current timer | `NO_NUMERIC_BOUND` | The timer is dynamic and the action is optional (`may`), so a fixed main-catalog verdict would overclaim. |
| Separate 4/8/16/32-second backoff entries | `DUPLICATE_OBLIGATION` | They mechanically repeat the same doubling requirement represented by DTLS12-RTX-03. |
| Timer expiry immediately retransmits buffered flight | `TRACE_NOT_DECISIVE` | The action is same-microstep and has no normative positive delay; current finite `G*` does not produce a NEGATIVE trace without an invented interval. |
| Final-flight retransmission and 240-second retention | `INDEPENDENT_AUDIT_REJECT` | The candidate invented a same-position retransmission obligation, while the selected source hook did not prove that final-flight state remains retained for the claimed 240 seconds. |

## 自动质量门拒绝

- `DTLS12-FINAL-01` Final-flight sender responds to duplicates for twice TCP MSL: `AP_WITHOUT_SOURCE_MAPPING:dtls_final_flight_retransmitted,dtls_final_flight_sent,dtls_peer_previous_flight_duplicate, INDEPENDENT_AUDIT_REJECT, PRIMARY_SOURCE_APS_MISSING_OR_EMPTY, UNKNOWN_OR_UNAPPROVED_AUDIT_STATUS:REJECT_OR_FIX, UNSTRUCTURED_SOURCE_URLS:https://www.rfc-editor.org/rfc/rfc793.html#section-3.3`
