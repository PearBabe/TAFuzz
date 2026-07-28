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
