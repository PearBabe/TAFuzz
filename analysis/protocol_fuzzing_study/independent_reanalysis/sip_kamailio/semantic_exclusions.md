# Semantic exclusions and caveats

- No STL/ZOH continuous signal semantics are introduced.
- No dynamic SIP identifier enters the AP alphabet.
- Timer callback/expiry properties are not claimed for the ProfuzzBench patched Kamailio target unless a reference timer profile is used.
- Unfinished obligations at test end are `UNKNOWN` unless the harness explicitly closes the trace with a watchdog timeout event.
- RFC6026 Accepted/Timer L properties are retained as review candidates.  They require manual confirmation that Kamailio's internal retention state is equivalent to the RFC Accepted state.
