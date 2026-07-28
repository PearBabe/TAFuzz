# QUIC 排除与待修候选

## 研究阶段排除：_staging/transport_security_protocols/quic/excluded.md

# QUIC excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Immediate ACK for Initial/Handshake packets | `PUNCTUAL_ONLY` | RFC 9000 says immediately but provides no numeric non-zero interval; a same-callback Boolean oracle can be kept outside the timed main catalog. |
| Closing/draining state persists for 3*PTO | `NO_FIXED_SOURCE_MAP` | RFC 9000 gives the duration, but ngtcp2 exposes closing/draining state while application code owns final state disposal; no single fixed library hook proves the full retention lifecycle. |
| Generic max_idle_timeout | `NO_NUMERIC_BOUND` | RFC default is zero/disabled. Only the ngtcp2 example's documented 30 s profile is proposed. |
| Application-data PTO before handshake confirmation must not be armed | `NO_NUMERIC_BOUND` | Strong state prohibition, but it has no numeric interval and is better a Boolean protocol-state oracle. |
| ACK every N packets | `FORMULA_UNSUPPORTED` | ACK frequency/count rules are not time bounds and need counters rather than current MITL AP timing. |
| PTO expiry immediately schedules an ack-eliciting probe | `TRACE_NOT_DECISIVE` | The same-callback action has no numeric interval; its missing-consequent trace is INCONCLUSIVE under current finite `G*`, and adding 1 ms would be artificial. |
| Old read-key discard within 3*PTO | `NO_FIXED_SOURCE_MAP` | RFC 9001 gives a dynamic upper bound, but the locked implementation lazily replaces/deletes key material as update state advances; a single fixed expiry event is not exposed. |

