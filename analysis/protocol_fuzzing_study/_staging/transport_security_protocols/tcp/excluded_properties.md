# TCP excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Live RTT-derived RTO formula for arbitrary connections | `FORMULA_UNSUPPORTED` | The bound is data-dependent (`SRTT + max(G,4*RTTVAR)`) and current MightyPPL intervals are integer constants. |
| RTO maximum must be at least 60 s | `TRACE_NOT_DECISIVE` | RFC 6298 constrains an implementation cap; it is a configuration/value invariant, not by itself a timed-event obligation. |
| One failed keep-alive probe must not kill the connection | `NO_NUMERIC_BOUND` | Normative and useful, but the prohibition has no time interval and duplicates a pure state/action oracle. |
| ACK at least every second full-sized segment | `FORMULA_UNSUPPORTED` | This is a packet-count obligation rather than a time-bound obligation. |
| SYN fallback RTO of 3 seconds | `DUPLICATE_OBLIGATION` | RFC 6298 resets to 3 s after SYN/SYN-ACK loss; it is the same RTO scheduling obligation under another explicitly detectable branch. |
| RTO expiry immediately retransmits earliest unacknowledged segment | `TRACE_NOT_DECISIVE` | The same-microstep `G* (fire -> retransmit)` negative trace is INCONCLUSIVE under current finite semantics; `F[0,1)` would invent a non-normative adapter bound. |
| R1 is at least three retransmissions | `FORMULA_UNSUPPORTED` | RFC 9293 defines a count threshold, not an elapsed-time interval. |
| TCP User Timeout Option lower/upper negotiation | `NO_FIXED_SOURCE_MAP` | RFC 5482 has numeric guidance, but the locked Linux source does not provide a directly corresponding on-wire UTO option implementation hook for this catalog. |
| Quiet time of one MSL after loss of sequence-number memory | `NO_FIXED_SOURCE_MAP` | RFC 9293 gives MSL=2 minutes, but no stable Linux TCP hook exposes the rare host-recovery condition and its retained sequence-memory premise. |
| Sender SWS override timeout of 0.1-1.0 seconds | `NO_FIXED_SOURCE_MAP` | RFC 9293 gives a recommended range, but the locked Linux code does not expose a single corresponding timer event separable from zero-window/resource probes. |
| Legacy OPEN-call global user timeout of five minutes | `VERSION_MISMATCH` | RFC 9293 preserves RFC 793 API text, while Linux defaults to stack R2 behavior unless TCP_USER_TIMEOUT is explicitly set. |
