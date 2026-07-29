# RTSP 排除与待修候选

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

