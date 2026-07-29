# TCP 排除与待修候选

## 研究阶段排除：_staging/ietf_app_protocols/dns/excluded.md

# DNS excluded candidates

## Result and source identity

Core and later formal DNS RFCs were screened for resolver retry/backoff,
positive and negative TTL expiry, SOA timers, failure/dead-server caching,
DNS-over-TCP idle/keepalive, validation-derived expiry, and serve-stale timing.
No candidate passed every admission gate, so no AP alphabet, formula, or
positive/negative timed word was emitted.

The fixed source is
`imp/dnsmasq@b8f16556d36924cd8dc7663cb4129d7b1f3fc2be` (`v2.73rc6`,
2015-04-22).  **`imp/dnsmasq` is a GitHub mirror of the upstream official
dnsmasq Git repository; the SHA is an official-history snapshot mirrored to
GitHub, not an official GitHub origin.**  The mirror identifies itself as
“Mirror of the upstream dnsmasq repository”; the upstream project is
[thekelleys.org.uk/dnsmasq](https://thekelleys.org.uk/dnsmasq/), with the
[official-git commit URL](https://thekelleys.org.uk/gitweb/?p=dnsmasq.git;a=commit;h=b8f16556d36924cd8dc7663cb4129d7b1f3fc2be)
recorded separately.

## Exhaustive numeric-timing screening

- `DNS-UDP-RETX-2-5` — RFC 1035 §4.2.1 recommends a 2–5-second minimum UDP
  retransmission interval when history is unavailable.  dnsmasq's
  [`TIMEOUT=10`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/config.h#L17-L26)
  retires forwarding records; it is not a retransmission timer.  The
  [`forward_query`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/forward.c#L304-L315)
  retry branch is entered by a repeated downstream query, not by an autonomous
  2–5-second task.  Rejected: `NO_FIXED_SOURCE_MAP`.

- `DNS-UDP-RETX-5` — RFC 1123 §6.1.3.3 says that, absent RTT data, the default
  should be no less than 5 seconds and retries should use bounded exponential
  backoff.  The fixed forwarder does not schedule that upstream retry.
  Rejected: `NO_FIXED_SOURCE_MAP`.

- `DNS-TCP-IDLE-120` — RFC 1035 §4.2.2 suggested an idle period on the order
  of two minutes.  RFC 7766 §6.2.3 supersedes this with “on the order of
  seconds” and deliberately specifies no value.  dnsmasq defines a
  [`CHILD_LIFETIME` of 150 seconds](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/config.h#L17-L20)
  and arms one process-lifetime alarm at
  [`dnsmasq.c:1687-1723`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/dnsmasq.c#L1687-L1723);
  it is not a reset-on-complete-message idle timer.  The snapshot also predates
  RFC 7766.  Rejected: `VERSION_MISMATCH`, `NO_NUMERIC_BOUND`,
  `NO_FIXED_SOURCE_MAP`.

- `DNS-RR-TTL-DYNAMIC` — RFC 1034 §3.6 and RFC 1035 §3.2.1 expire cached RRs
  after the message-carried TTL.  The TTL is administrator/data selected, not
  a standard constant.  [`cache_insert`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/cache.c#L452-L468)
  stores `ttd=now+ttl` at
  [`cache.c:603-607`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/cache.c#L603-L607),
  and [`is_expired`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/cache.c#L314-L323)
  checks that dynamic deadline.  Rejected: `NO_NUMERIC_BOUND`.

- `DNS-ZERO-TTL` — RFC 1123 §6.1.2.1 says TTL zero data is usable only for
  the current transaction and MUST NOT be cached.  A zero-width interval is a
  forbidden singleton; adding one millisecond would invent an epsilon.
  Rejected: `PUNCTUAL_ONLY`.

- `DNS-SOA-TIMERS-DYNAMIC` — RFC 1034 §4.4 defines secondary REFRESH, RETRY,
  and EXPIRE using values carried in each zone's SOA.  No universal values and
  no secondary-zone-transfer state machine exist in the fixed source.
  Rejected: `NO_NUMERIC_BOUND`, `NO_FIXED_SOURCE_MAP`.

- `DNS-NEGATIVE-TTL-DYNAMIC` — RFC 2308 §§3, 5, and 6 use
  `min(SOA TTL, SOA.MINIMUM)` and decrement it to zero.  The fixed
  [`find_soa`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/rfc1035.c#L866-L917)
  extracts that dynamic value and
  [`extract_addresses`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/rfc1035.c#L1152-L1168)
  passes it to the cache.  Rejected: `NO_NUMERIC_BOUND`.

- `DNS-NEGATIVE-CAP-1-3H` — RFC 2308 §5 describes one to three hours as a
  sensible tunable default, not a universal mandatory value.  dnsmasq
  [zero-initializes `neg_ttl`](https://github.com/imp/dnsmasq/blob/b8f16556d36924cd8dc7663cb4129d7b1f3fc2be/src/option.c#L4376-L4398),
  so the locked default does not select this profile.  Rejected:
  `NO_NUMERIC_BOUND`.

- `DNS-SERVFAIL-CACHE-300` — RFC 2308 §7.1 says an optionally cached server
  failure MUST NOT remain longer than five minutes.  No SERVFAIL-cache object
  or five-minute expiry path exists in the locked source.  Rejected:
  `NO_FIXED_SOURCE_MAP`.

- `DNS-DEAD-SERVER-120-300` — RFC 2308 §7.2 permits considering a server
  unreachable after 120 seconds and limits an optional dead-server indication
  to five minutes.  The fixed forwarder has no matching per-server detection
  and cache state.  Rejected: `NO_FIXED_SOURCE_MAP`.

- `DNS-VALIDATION-TTL-DYNAMIC` — RFC 4035 §§4.7 and 5.3.3 derives accepted
  RRset lifetime from received TTLs and signature expiration, while requiring
  only a “small” validation-failure cache TTL.  The endpoints are dynamic or
  unspecified.  Rejected: `NO_NUMERIC_BOUND`.

- `DNS-EDNS-KEEPALIVE-DYNAMIC` — RFC 7828 encodes a server-selected timeout in
  100-millisecond units but sets no universal default.  The 2015 snapshot
  predates the RFC and has no matching option path.  Rejected:
  `VERSION_MISMATCH`, `NO_NUMERIC_BOUND`, `NO_FIXED_SOURCE_MAP`.

- `DNS-SERVE-STALE-TIMERS` — RFC 8767 recommends a 30-second stale TTL and
  failure recheck, a 1.8-second client timer, a 7-day TTL clamp, and a 1–3-day
  stale window.  The locked 2015 snapshot predates the RFC and contains no
  serve-stale state machine.  Rejected: `VERSION_MISMATCH`,
  `NO_FIXED_SOURCE_MAP`.

- `DNS-RESOLUTION-FAILURE-CACHE` — RFC 9520 §§3.1–3.2 requires caching
  resolution failures for at least 1 second and no more than 5 minutes.  The
  locked snapshot predates the RFC by more than eight years and has no matching
  failure cache.  Rejected: `VERSION_MISMATCH`, `NO_FIXED_SOURCE_MAP`.

- `DNS-RFC4697-REQUERY` — RFC 4697 limits unnecessary requery patterns but
  gives no fixed elapsed-time interval; its zero-TTL discussion reduces to the
  punctual case above.  Rejected: `NO_NUMERIC_BOUND`, `PUNCTUAL_ONLY`.

## Safety and execution note

This was a document/source audit only.  No dnsmasq process was built or
started, no DNS query was sent, and no formula or trace was executed.

## 研究阶段排除：_staging/ietf_app_protocols/rtsp/excluded.md

# RTSP excluded candidates

## Result and scope correction

The locked `rgaufman/live555@ceeb4f462709695b145852de309d8cd25e2dca01`
snapshot emits `RTSP/1.0`, so RFC 2326—not only RFC 7826—must be screened.
RFC 2326 §12.37 permits a server to declare a Session timeout other than its
60-second default, and Appendix A.2 makes inactivity teardown optional.  The
fixed implementation defaults `reclamationSeconds` to 65, emits `timeout=65`,
and reschedules the per-session liveness task with the same value.

One property, `RTSP-SESSION-01`, is therefore proposed as an
`IMPLEMENTATION_PROFILE` no-early invariant.  It does **not** turn RFC 2326's
`MAY` into a `MUST`, does not require the callback to run at 65 seconds, and
does not claim that 65 seconds is a universal RTSP constant.  RFC 2326
§12.37's default, Appendix A.2's one-minute discussion, and the declared
LIVE555 override are treated as one obligation rather than mechanically split
into duplicate properties.

The RTSP/1.0 version evidence is
[`liveMedia/RTSPServer.cpp:1425-1499`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L1425-L1499).

## Exhaustive numeric-timing exclusions

- `RTSP10-UNRELIABLE-RTT-500` — RFC 2326 §9.2 gives connectionless RTSP an
  initial RTT value of 500 ms and permits retransmission after one RTT.  The
  locked client accepts only `rtsp://` at
  [`RTSPClient.cpp:247-258`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPClient.cpp#L247-L258)
  and creates a stream/TCP socket at
  [`RTSPClient.cpp:850-880`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPClient.cpp#L850-L880).
  The server likewise listens on a stream socket at
  [`GenericMediaServer.cpp:141-204`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/GenericMediaServer.cpp#L141-L204).
  No `rtspu://` control path, unreliable-request retransmission state, or
  500 ms RTT timer exists.  Rejected: `NO_FIXED_SOURCE_MAP`.

- `RTSP20-SESSION-60` — RFC 7826 §§10.5 and 18.49 define an RTSP/2.0
  60-second default and discourage values below 30 seconds.  The fixed server
  is RTSP/1.0, and its corresponding RFC 2326/LIVE555 liveness obligation is
  already represented once by `RTSP-SESSION-01`.  Rejected:
  `VERSION_MISMATCH`.

- `RTSP20-TEARDOWN-CLOSE-10` — RFC 7826 §10.3 says the server SHOULD wait at
  least 10 seconds after a TEARDOWN response before closing the connection.
  [`handleCmd_TEARDOWN`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L1570-L1596)
  sends the RTSP/1.0 response and deletes an empty session but defines no
  10-second connection-close timer.  Rejected: `VERSION_MISMATCH`,
  `NO_FIXED_SOURCE_MAP`.

- `RTSP20-INCOMPLETE-10` — RFC 7826 §10.3 recommends waiting at least
  10 seconds for an incomplete message.  The fixed
  [`handleRequestBytes`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L607-L724)
  path retains partial bytes until another read but has no matching delayed
  task.  Rejected: `VERSION_MISMATCH`, `NO_FIXED_SOURCE_MAP`.

- `RTSP20-RESPONDER-5` — RFC 7826 §10.4 says a responder SHOULD answer within
  5 seconds or send 100 Continue and repeat it every 5 seconds.  The server
  dispatches and sends RTSP/1.0 responses synchronously in
  [`RTSPServer.cpp:735-898`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L735-L898),
  with no 100 Continue timer.  Rejected: `VERSION_MISMATCH`,
  `NO_FIXED_SOURCE_MAP`.

- `RTSP20-REQUESTER-10` — RFC 7826 §10.4 says a requester SHOULD wait at
  least 10 seconds and continue waiting after 100 Continue.  The fixed client
  has a pending-request queue at
  [`RTSPClient.cpp:196-203`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPClient.cpp#L196-L203)
  but no corresponding response deadline.  Rejected: `VERSION_MISMATCH`,
  `NO_FIXED_SOURCE_MAP`.

- `RTSP20-OVERLOAD-BACKOFF` — RFC 7826 §10.7 starts no-response backoff at
  5 seconds, doubles to a 30-minute mean, and selects each delay from
  0.5–1.5 times that mean.  LIVE555's
  [`scheduleDESCRIBECommand`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/ProxyServerMediaSession.cpp#L509-L523)
  is a different RTSP/1.0 retry policy (1, 2, ... 256 seconds, then 256–511)
  and does not implement Retry-After.  Rejected: `VERSION_MISMATCH`,
  `NO_FIXED_SOURCE_MAP`.

- `RTSP20-PLAY-NOTIFY-300` — RFC 7826 §13.5.2 recommends PLAY_NOTIFY about
  every 5 minutes, with intervals greater than 1 minute and less than 2 hours.
  The fixed server's
  [`allowedCommandNames`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L116-L118)
  omits PLAY_NOTIFY.  Rejected: `VERSION_MISMATCH`, `NO_FIXED_SOURCE_MAP`.

- `RTSP20-VALIDATOR-60` — RFC 7826 §16.1.3 uses a 60-second separation between
  message-carried Date and Last-Modified values when classifying a validator.
  This is an absolute-header comparison rather than an elapsed event timer,
  and no matching validator symbol exists in the fixed source.  Rejected:
  `FORMULA_UNSUPPORTED`, `NO_FIXED_SOURCE_MAP`.

- `RTSP20-RETRY-AFTER-DYNAMIC` — RFC 7826 §18.44 defines a sender-selected
  absolute date or delay; its 120-second value is only an example.  No
  universal constant and no LIVE555 Retry-After path exist.  Rejected:
  `NO_NUMERIC_BOUND`, `NO_FIXED_SOURCE_MAP`.

## Formula and execution note

`RTSP-SESSION-01` was built and run with the existing TAMonitor in finite,
`flatten` mode.  Its 65000 ms boundary trace was `POSITIVE`, and its 64999 ms
early-callback trace was `NEGATIVE`, with identical symbolic and concrete
verdicts.  Because the property is deliberately one-sided, a late or missing
callback is not a counterexample.

No LIVE555 service was built or started and no RTSP message was sent.  The
only execution was local formula/trace validation by TAMonitor.

## 研究阶段排除：_staging/ietf_app_protocols/smtp/excluded.md

# SMTP excluded candidates

The seven distinct numeric phase minima in RFC 5321 §4.5.3.2 are admitted as lower-bound properties. They are not mechanically duplicated constants: each has a separate protocol phase and source hook.

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Exact timeout at the RFC minimum | `OVERSTRONG_FORMULA` | RFC 5321 says the values SHOULD be minimums; a client may wait longer. Main formulas therefore prohibit early timeout only. |
| Whole-message transaction timeout | `NO_NUMERIC_BOUND` | RFC requires per-command and per-buffer timers and intentionally makes total duration proportional to message size. |
| Retry schedule after temporary failure | `CONTEXT_DEPENDENT_SOFT_GUIDANCE` | RFC 5321 §4.5.4.1 gives an “in general” SHOULD-level retry interval of at least 30 minutes and a looser 4–5 day give-up recommendation, but explicitly permits reason-aware variable strategies. Exim 4.89's default rule begins at 15 minutes. Without an adapter predicate proving the generic-policy context, 1800000 ms is not an unconditional protocol oracle. |
| Exim connect_timeout as SMTP property | `DUPLICATE_OBLIGATION` | TCP connection establishment belongs to the TCP catalog, not an SMTP response phase. |

## Role and benchmark boundary

- `SMTP-TIMEOUT-01`–`06` describe Exim's outbound SMTP-client transport. The pinned ProFuzzBench Exim campaign starts an inbound TCP/25 server, so those six properties are protocol-catalog entries but are not reachable in that server harness without a separate outbound-client harness.
- `SMTP-TIMEOUT-07` is limited to the pinned plaintext Exim-server profile. STARTTLS requires separate fixed-source timer hooks.
- The real bounds are 2–10 minutes. They remain valid offline/long-trace or virtual-time oracles, but their wall-clock triggerability is `LOW`; the RFC constants are not scaled down for throughput.

## 研究阶段排除：_staging/industrial_protocols/modbus_tcp/excluded.md

# Modbus/TCP excluded candidates

The official V1.0b guide states in §4.4.1.4 that no required transaction response time is specified. Therefore this protocol contributes zero normative numeric MITL cards after independent audit.

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| MODBUS-TCP-01 full confirmation within 500 ms | `REJECT_OR_FIX` | `NO_PROTOCOL_BOUND_AND_INCORRECT_IMPLEMENTATION_ORACLE` | 500 ms is a libmodbus default, not a protocol value; response_timeout governs the initial read and byte_timeout is reloaded for remaining chunks, so full confirmation may exceed 500 ms. | Split into initial-response and per-byte implementation profiles and keep them outside the normative main catalogue. |
| Universal MODBUS/TCP response deadline | `KEEP_EXCLUDED` | `NO_NUMERIC_BOUND` | §4.4.1.4 deliberately defines none. | A deployment-specific profile may be studied but cannot be generalized. |
| Universal retry deadline | `KEEP_EXCLUDED` | `NO_NUMERIC_BOUND` | The guide only requires a reasonable timeout based on expected transport delay. | Provide a locked deployment profile and mark it non-normative. |
| 500 ms byte-to-byte protocol timeout | `KEEP_EXCLUDED` | `IMPLEMENTATION_PROFILE_ONLY` | `_BYTE_TIMEOUT` is a libmodbus default with no Modbus/TCP normative requirement. | Keep only as a libmodbus appendix property. |
| 75 s TCP connect/keepalive/RTO properties | `KEEP_EXCLUDED` | `DUPLICATE_TRANSPORT_OBLIGATION` | These are TCP behavior, not Modbus application semantics. | Compare in the TCP catalogue, not here. |
| Server indication timeout | `KEEP_EXCLUDED` | `NO_FINITE_DEFAULT` | libmodbus leaves it unset and the guide provides no number. | Supply an explicit application profile. |

`MODBUS-TCP-01` is not emitted in `proposals.json` and is not counted toward catalogue size.

## 研究阶段排除：_staging/transport_security_protocols/tcp/excluded.md

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

