# Kamailio/SIP MITL Property Catalog (independent reanalysis)

- Generated: 2026-07-13
- Kamailio fixed commit: `2648eb330b133a20f1398d59a28c53532106cad3`
- ProfuzzBench fixed commit: `8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074`
- Scope: SIP server/UAS/stateful-proxy properties for Kamailio/ProfuzzBench; no historical SIP catalog is reused.
- Semantics: pointwise finite timed words, integer milliseconds, complete AP valuation; dynamic SIP IDs are metadata only.
- Review status: every property remains `PENDING` until the user signs off.

## SIP-KAM-001: A newly constructed INVITE server transaction enters Proceeding and exposes the request to the transaction user.

- Category/role: INVITE server transaction; UAS/server transaction
- RFC source: [RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- Evidence summary: When a server transaction is constructed for an INVITE request, it starts in Proceeding and the request is passed upward.
- Time bound: `2` ms; source: adapter microstep expansion for same callback, not an RFC tolerance
- MightyPPL: `G* (server_rx_invite_new_tx -> F [0,2] invite_tx_proceeding)`
- Mathematical MITL: `G(server_rx_invite_new_tx -> F_[0,2ms] invite_tx_proceeding)`
- APs: `server_rx_invite_new_tx, invite_tx_proceeding`
- Correlation: Call-ID + CSeq number/method + top Via branch/sent-by
- Primary hooks: HK_RX_PARSE_OK, HK_TX_NEW
- Auxiliary hooks: HK_TX_LOOKUP
- Positive timed word: `time,props ; 0,{server_rx_invite_new_tx} ; 1,{invite_tx_proceeding}`
- Negative timed word: `time,props ; 0,{server_rx_invite_new_tx} ; 3,{invite_tx_proceeding}`
- Observability/oracle: white-box hook after parser and transaction creation; high: catches transaction creation/routing regressions
- Caveat/review: PENDING; Should the benchmark count parser-rejected INVITEs separately from malformed-message oracles?

## SIP-KAM-002: If INVITE processing may take longer than the RFC 200 ms window and no earlier TU response exists, emit 100 Trying.

- Category/role: INVITE provisional response; UAS/server transaction
- RFC source: [RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — SHOULD with timer bound
- Evidence summary: The server transaction generates 100 Trying unless it knows the TU will respond within 200 ms.
- Time bound: `200` ms; source: RFC3261 section 17.2.1
- MightyPPL: `G* (invite_auto_100_obligation -> F [0,200] uas_tx_100_trying)`
- Mathematical MITL: `G(invite_auto_100_obligation -> F_[0,200ms] uas_tx_100_trying)`
- APs: `invite_auto_100_obligation, uas_tx_100_trying`
- Correlation: same INVITE server transaction
- Primary hooks: HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_TX_NEW
- Positive timed word: `time,props ; 0,{invite_auto_100_obligation} ; 100,{uas_tx_100_trying}`
- Negative timed word: `time,props ; 0,{invite_auto_100_obligation} ; 201,{uas_tx_100_trying}`
- Observability/oracle: white-box send hook; black-box packet capture can cross-check; medium/high: detects loss of early provisional feedback
- Caveat/review: Kamailio auto_inv_100 and route-script behavior must be fixed in experiment profile.; Does the chosen Kamailio cfg always enable auto_inv_100, or should this be a profile-specific property?

## SIP-KAM-003: A provisional 101-199 response selected by the transaction layer while INVITE is Proceeding is passed to transport.

- Category/role: INVITE provisional relay; UAS/proxy transaction
- RFC source: [RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- Evidence summary: In Proceeding, provisional responses from the TU are passed to the transport layer.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (invite_proceeding_tu_provisional -> F [0,2] uas_tx_provisional_response)`
- Mathematical MITL: `G(invite_proceeding_tu_provisional -> F_[0,2ms] uas_tx_provisional_response)`
- APs: `invite_proceeding_tu_provisional, uas_tx_provisional_response`
- Correlation: same INVITE transaction and response branch
- Primary hooks: HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_REPLY_RECEIVED
- Positive timed word: `time,props ; 0,{invite_proceeding_tu_provisional} ; 1,{uas_tx_provisional_response}`
- Negative timed word: `time,props ; 0,{invite_proceeding_tu_provisional} ; 3,{uas_tx_provisional_response}`
- Observability/oracle: send hook plus optional pcap; high: detects swallowed provisional responses
- Caveat/review: PENDING; Confirm whether ProfuzzBench route exposes upstream provisional responses during fuzzing.

## SIP-KAM-004: A retransmitted INVITE in Proceeding retransmits the most recent provisional response instead of creating a fresh TU event.

- Category/role: INVITE retransmission suppression; UAS/server transaction
- RFC source: [RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- Evidence summary: If a request retransmission is received in Proceeding, the most recent provisional response is retransmitted.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (invite_retransmission_in_proceeding_with_last_prov -> F [0,2] uas_retransmit_last_provisional)`
- Mathematical MITL: `G(invite_retransmission_in_proceeding_with_last_prov -> F_[0,2ms] uas_retransmit_last_provisional)`
- APs: `invite_retransmission_in_proceeding_with_last_prov, uas_retransmit_last_provisional`
- Correlation: same branch/sent-by/method transaction key
- Primary hooks: HK_TX_LOOKUP, HK_RETRANSMIT_REPLY
- Auxiliary hooks: HK_SEND_PR_BUFFER
- Positive timed word: `time,props ; 0,{invite_retransmission_in_proceeding_with_last_prov} ; 1,{uas_retransmit_last_provisional}`
- Negative timed word: `time,props ; 0,{invite_retransmission_in_proceeding_with_last_prov} ; 3,{uas_retransmit_last_provisional}`
- Observability/oracle: white-box transaction lookup and send hook; high: catches duplicate transaction/TU re-entry bugs
- Caveat/review: PENDING; Need auxiliary counter to prove TU was not re-entered if using this as a bug claim.

## SIP-KAM-005: A 300-699 final response from the TU moves INVITE server transaction to Completed and is sent.

- Category/role: INVITE final response; UAS/server transaction
- RFC source: [RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- Evidence summary: When a 300 to 699 response is passed to the server transaction, it enters Completed and passes the response to transport.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (invite_proceeding_tu_final_300_699 -> F [0,2] invite_tx_completed_non2xx)`
- Mathematical MITL: `G(invite_proceeding_tu_final_300_699 -> F_[0,2ms] invite_tx_completed_non2xx)`
- APs: `invite_proceeding_tu_final_300_699, invite_tx_completed_non2xx`
- Correlation: same INVITE server transaction
- Primary hooks: HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_TIMER_ARM
- Positive timed word: `time,props ; 0,{invite_proceeding_tu_final_300_699} ; 1,{invite_tx_completed_non2xx}`
- Negative timed word: `time,props ; 0,{invite_proceeding_tu_final_300_699} ; 3,{invite_tx_completed_non2xx}`
- Observability/oracle: send hook and transaction status update; high: detects final-response loss or wrong state
- Caveat/review: PENDING; For proxy mode, distinguish final response selected for upstream UAS from downstream branch final.

## SIP-KAM-006: After non-2xx Completed, the transaction must not be destroyed before ACK or Timer H expiry.

- Category/role: INVITE Timer H/lifetime; UAS/server transaction
- RFC source: [RFC3261 17.2.1 and Table 4](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine timer
- Evidence summary: Timer H is 64*T1 for INVITE server transactions in Completed; ACK or timeout governs termination.
- Time bound: `32000` ms; source: 64*T1 using RFC default T1=500 ms
- MightyPPL: `G* (invite_tx_completed_non2xx -> G [0,32000) (!invite_tx_terminated_without_ack_or_timer_h))`
- Mathematical MITL: `G(invite_tx_completed_non2xx -> G_[0,32000ms) not early_terminated)`
- APs: `invite_tx_completed_non2xx, invite_tx_terminated_without_ack_or_timer_h`
- Correlation: same INVITE server transaction
- Primary hooks: HK_SEND_PR_BUFFER, HK_PUT_ON_WAIT
- Auxiliary hooks: HK_TIMER_ARM, HK_TIMER_STOP
- Positive timed word: `time,props ; 0,{invite_tx_completed_non2xx} ; 1,{}`
- Negative timed word: `time,props ; 0,{invite_tx_completed_non2xx} ; 1,{invite_tx_terminated_without_ack_or_timer_h}`
- Observability/oracle: white-box wait/timer hooks; pcap alone cannot prove early destroy; medium: detects premature state drop
- Caveat/review: ProfuzzBench patch disables timer processes; callback expiry needs reference build, but early destroy remains observable.; Should a test watchdog close the trace at 32s, or should unfinished obligations be UNKNOWN?

## SIP-KAM-007: An ACK matching a Completed INVITE server transaction moves it to Confirmed and stops response retransmission.

- Category/role: INVITE ACK handling; UAS/server transaction
- RFC source: [RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- Evidence summary: When an ACK is received in Completed, the server transaction transitions to Confirmed.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (invite_completed_rx_ack -> F [0,2] invite_tx_confirmed_ack_absorbed)`
- Mathematical MITL: `G(invite_completed_rx_ack -> F_[0,2ms] invite_tx_confirmed_ack_absorbed)`
- APs: `invite_completed_rx_ack, invite_tx_confirmed_ack_absorbed`
- Correlation: same INVITE transaction; ACK matches INVITE method exception
- Primary hooks: HK_TX_LOOKUP, HK_TIMER_STOP
- Auxiliary hooks: HK_T_REPLY_MATCHING
- Positive timed word: `time,props ; 0,{invite_completed_rx_ack} ; 1,{invite_tx_confirmed_ack_absorbed}`
- Negative timed word: `time,props ; 0,{invite_completed_rx_ack} ; 3,{invite_tx_confirmed_ack_absorbed}`
- Observability/oracle: white-box lookup/timer-stop hook; high: detects ACK misclassification
- Caveat/review: PENDING; Need separate AP for 2xx ACK, because RFC6026 Accepted ACK is passed upward rather than absorbed.

## SIP-KAM-008: Under RFC6026, a 2xx to INVITE transitions the server transaction to Accepted and arms Timer L.

- Category/role: INVITE 2xx Accepted; UAS/server transaction
- RFC source: [RFC6026 7.1 and 8.7](https://www.rfc-editor.org/rfc/rfc6026.html#section-7.1) — MUST/update state-machine
- Evidence summary: The update adds Accepted and Timer L; 2xx in Proceeding transitions to Accepted and Timer L is 64*T1.
- Time bound: `2` ms; source: adapter microstep expansion for transition; Timer L value is 64*T1=32000 ms
- MightyPPL: `G* (invite_2xx_response_from_tu -> F [0,2] timer_l_64t1_armed)`
- Mathematical MITL: `G(invite_2xx_response_from_tu -> F_[0,2ms] timer_l_64t1_armed)`
- APs: `invite_2xx_response_from_tu, timer_l_64t1_armed`
- Correlation: same INVITE server transaction
- Primary hooks: HK_RELAY_REPLY, HK_TIMER_ARM
- Auxiliary hooks: HK_SEND_PR_BUFFER
- Positive timed word: `time,props ; 0,{invite_2xx_response_from_tu} ; 1,{timer_l_64t1_armed}`
- Negative timed word: `time,props ; 0,{invite_2xx_response_from_tu} ; 3,{timer_l_64t1_armed}`
- Observability/oracle: white-box timer arm and response hook; medium/high: RFC6026 conformance oracle
- Caveat/review: Likely requires reference profile and manual audit because Kamailio may encode Accepted differently from RFC names.; Can we observe an explicit Timer L equivalent, or must this be an excluded/extended property?

## SIP-KAM-009: Retransmitted INVITEs in Accepted are absorbed by the transaction and not re-delivered to the TU.

- Category/role: RFC6026 retransmitted INVITE in Accepted; UAS/server transaction
- RFC source: [RFC6026 8.7](https://www.rfc-editor.org/rfc/rfc6026.html#section-8.7) — MUST/update state-machine
- Evidence summary: The Accepted state absorbs retransmissions of the original INVITE and does not pass them to the TU.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (accepted_rx_invite_retransmission -> G [0,2] (!invite_retransmission_passed_to_tu))`
- Mathematical MITL: `G(accepted_rx_invite_retransmission -> G_[0,2ms] not passed_to_tu)`
- APs: `accepted_rx_invite_retransmission, invite_retransmission_passed_to_tu`
- Correlation: same INVITE branch/sent-by/method transaction key
- Primary hooks: HK_TX_LOOKUP, HK_TX_NEW
- Auxiliary hooks: HK_RETRANSMIT_REPLY
- Positive timed word: `time,props ; 0,{accepted_rx_invite_retransmission} ; 1,{}`
- Negative timed word: `time,props ; 0,{accepted_rx_invite_retransmission} ; 1,{invite_retransmission_passed_to_tu}`
- Observability/oracle: white-box lookup plus route/TU boundary hook; medium: detects duplicate TU delivery
- Caveat/review: Requires route-boundary hook to prove non-delivery; absence of event alone is UNKNOWN if hooks dropped.; Where should the TU delivery hook sit in Kamailio route execution for minimal perturbation?

## SIP-KAM-010: ACKs in Accepted are passed directly to the TU rather than absorbed by the transaction layer.

- Category/role: RFC6026 ACK in Accepted; UAS/server transaction
- RFC source: [RFC6026 8.7](https://www.rfc-editor.org/rfc/rfc6026.html#section-8.7) — MUST/update state-machine
- Evidence summary: ACK requests that match an Accepted transaction are passed directly to the TU.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (accepted_rx_ack -> F [0,2] ack_passed_to_tu)`
- Mathematical MITL: `G(accepted_rx_ack -> F_[0,2ms] ack_passed_to_tu)`
- APs: `accepted_rx_ack, ack_passed_to_tu`
- Correlation: same INVITE accepted transaction and ACK matching key
- Primary hooks: HK_TX_LOOKUP, HK_RX_PARSE_OK
- Auxiliary hooks: HK_TIMER_STOP
- Positive timed word: `time,props ; 0,{accepted_rx_ack} ; 1,{ack_passed_to_tu}`
- Negative timed word: `time,props ; 0,{accepted_rx_ack} ; 3,{ack_passed_to_tu}`
- Observability/oracle: white-box transaction lookup plus route/TU hook; medium: detects wrong ACK absorption
- Caveat/review: Needs manual confirmation of Kamailio route callback representing TU delivery.; Should ACK-to-TU be considered a route-level event or a tm callback event in this SUT?

## SIP-KAM-011: A newly constructed non-INVITE server transaction enters Trying and passes the request upward.

- Category/role: non-INVITE server transaction; UAS/server transaction
- RFC source: [RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- Evidence summary: For non-INVITE requests, the server transaction starts in Trying and passes the request to the TU.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (server_rx_noninvite_new_tx -> F [0,2] noninvite_tx_trying)`
- Mathematical MITL: `G(server_rx_noninvite_new_tx -> F_[0,2ms] noninvite_tx_trying)`
- APs: `server_rx_noninvite_new_tx, noninvite_tx_trying`
- Correlation: Call-ID + CSeq + top Via branch/sent-by
- Primary hooks: HK_RX_PARSE_OK, HK_TX_NEW
- Auxiliary hooks: HK_TX_LOOKUP
- Positive timed word: `time,props ; 0,{server_rx_noninvite_new_tx} ; 1,{noninvite_tx_trying}`
- Negative timed word: `time,props ; 0,{server_rx_noninvite_new_tx} ; 3,{noninvite_tx_trying}`
- Observability/oracle: white-box transaction creation; high: covers OPTIONS/BYE/CANCEL class setup
- Caveat/review: PENDING; CANCEL is handled specially; property should exclude CANCEL when original-transaction semantics are being tested separately.

## SIP-KAM-012: A retransmitted non-INVITE request in Trying is discarded, not delivered again to the TU.

- Category/role: non-INVITE retransmission discard; UAS/server transaction
- RFC source: [RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- Evidence summary: In Trying, retransmissions of non-INVITE requests are discarded.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (noninvite_retransmission_in_trying -> G [0,2] (!noninvite_retransmission_passed_to_tu))`
- Mathematical MITL: `G(noninvite_retransmission_in_trying -> G_[0,2ms] not passed_to_tu)`
- APs: `noninvite_retransmission_in_trying, noninvite_retransmission_passed_to_tu`
- Correlation: same non-INVITE transaction key
- Primary hooks: HK_TX_LOOKUP, HK_TIMER_STOP
- Auxiliary hooks: HK_RX_PARSE_OK
- Positive timed word: `time,props ; 0,{noninvite_retransmission_in_trying} ; 1,{}`
- Negative timed word: `time,props ; 0,{noninvite_retransmission_in_trying} ; 1,{noninvite_retransmission_passed_to_tu}`
- Observability/oracle: white-box lookup plus route/TU boundary hook; medium/high: detects duplicate request processing
- Caveat/review: PENDING; Needs a route/TU delivery hook to avoid interpreting missing events under event drop as pass.

## SIP-KAM-013: A provisional response for a non-INVITE transaction moves it to Proceeding and sends the response.

- Category/role: non-INVITE provisional response; UAS/server transaction
- RFC source: [RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- Evidence summary: If a provisional response is passed to the non-INVITE server transaction, it enters Proceeding and passes it to transport.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (noninvite_tu_provisional -> F [0,2] noninvite_tx_proceeding_response_sent)`
- Mathematical MITL: `G(noninvite_tu_provisional -> F_[0,2ms] noninvite_tx_proceeding_response_sent)`
- APs: `noninvite_tu_provisional, noninvite_tx_proceeding_response_sent`
- Correlation: same non-INVITE transaction
- Primary hooks: HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_TX_LOOKUP
- Positive timed word: `time,props ; 0,{noninvite_tu_provisional} ; 1,{noninvite_tx_proceeding_response_sent}`
- Negative timed word: `time,props ; 0,{noninvite_tu_provisional} ; 3,{noninvite_tx_proceeding_response_sent}`
- Observability/oracle: send hook plus status class; medium: useful for OPTIONS/BYE provisional edge cases
- Caveat/review: PENDING; RFC says UAS SHOULD NOT generally send provisional for non-INVITE; this property applies only if TU emits one.

## SIP-KAM-014: A final response to a non-INVITE server transaction enters Completed and is sent.

- Category/role: non-INVITE final response; UAS/server transaction
- RFC source: [RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- Evidence summary: Final responses 200-699 cause Completed and are passed to transport.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (noninvite_tu_final_response -> F [0,2] noninvite_tx_completed_final_sent)`
- Mathematical MITL: `G(noninvite_tu_final_response -> F_[0,2ms] noninvite_tx_completed_final_sent)`
- APs: `noninvite_tu_final_response, noninvite_tx_completed_final_sent`
- Correlation: same non-INVITE transaction
- Primary hooks: HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_PUT_ON_WAIT
- Positive timed word: `time,props ; 0,{noninvite_tu_final_response} ; 1,{noninvite_tx_completed_final_sent}`
- Negative timed word: `time,props ; 0,{noninvite_tu_final_response} ; 3,{noninvite_tx_completed_final_sent}`
- Observability/oracle: send hook plus wait-state hook; high: core non-INVITE response oracle
- Caveat/review: PENDING; Need distinguish server-side final response from proxied branch final selected for forwarding.

## SIP-KAM-015: A retransmitted non-INVITE request in Completed gets the stored final response retransmitted.

- Category/role: non-INVITE retransmission in Completed; UAS/server transaction
- RFC source: [RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- Evidence summary: In Completed, retransmissions are passed the final response previously sent.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (noninvite_retransmission_in_completed -> F [0,2] noninvite_final_response_retransmitted)`
- Mathematical MITL: `G(noninvite_retransmission_in_completed -> F_[0,2ms] noninvite_final_response_retransmitted)`
- APs: `noninvite_retransmission_in_completed, noninvite_final_response_retransmitted`
- Correlation: same non-INVITE transaction key
- Primary hooks: HK_TX_LOOKUP, HK_RETRANSMIT_REPLY
- Auxiliary hooks: HK_SEND_PR_BUFFER
- Positive timed word: `time,props ; 0,{noninvite_retransmission_in_completed} ; 1,{noninvite_final_response_retransmitted}`
- Negative timed word: `time,props ; 0,{noninvite_retransmission_in_completed} ; 3,{noninvite_final_response_retransmitted}`
- Observability/oracle: lookup and send retransmission hook; high: catches response cache/retransmission bugs
- Caveat/review: PENDING; Timer J expiry must be handled as legal supersession in long traces.

## SIP-KAM-016: Requests with RFC3261 magic-cookie branch and matching sent-by/method map to the existing transaction.

- Category/role: transaction matching; UAS/proxy transaction layer
- RFC source: [RFC3261 17.2.3](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.3) — MUST/matching rule
- Evidence summary: With magic-cookie branch, matching uses branch, sent-by, and method, except ACK matches INVITE.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (request_with_magic_cookie_matches_existing_tx -> F [0,2] tx_lookup_existing_match)`
- Mathematical MITL: `G(magic_cookie_match_candidate -> F_[0,2ms] tx_lookup_existing_match)`
- APs: `request_with_magic_cookie_matches_existing_tx, tx_lookup_existing_match`
- Correlation: top Via branch/sent-by + CSeq method exception + transaction bucket/hash
- Primary hooks: HK_TX_LOOKUP
- Auxiliary hooks: HK_RX_PARSE_OK
- Positive timed word: `time,props ; 0,{request_with_magic_cookie_matches_existing_tx} ; 1,{tx_lookup_existing_match}`
- Negative timed word: `time,props ; 0,{request_with_magic_cookie_matches_existing_tx} ; 3,{tx_lookup_existing_match}`
- Observability/oracle: white-box lookup; pcap can provide candidate fields; high: prevents transaction-key explosion/ambiguity
- Caveat/review: PENDING; AP names exclude dynamic branch values; fields live only in correlation metadata.

## SIP-KAM-017: A CANCEL that matches an existing transaction receives a 200 OK to the CANCEL itself.

- Category/role: CANCEL matched response; UAS/proxy transaction layer
- RFC source: [RFC3261 9.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-9.2) — SHOULD/MUST behavior
- Evidence summary: If a matching transaction exists, the UAS first processes the CANCEL and then answers the CANCEL with 200 OK.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (cancel_matches_original_transaction -> F [0,2] cancel_tx_200_ok)`
- Mathematical MITL: `G(cancel_matches_original_transaction -> F_[0,2ms] cancel_tx_200_ok)`
- APs: `cancel_matches_original_transaction, cancel_tx_200_ok`
- Correlation: CANCEL transaction + matched original transaction
- Primary hooks: HK_FORWARD_NONACK, HK_E2E_CANCEL, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_TX_LOOKUP
- Positive timed word: `time,props ; 0,{cancel_matches_original_transaction} ; 1,{cancel_tx_200_ok}`
- Negative timed word: `time,props ; 0,{cancel_matches_original_transaction} ; 3,{cancel_tx_200_ok}`
- Observability/oracle: white-box cancel path plus send hook; high: explicit SIP CANCEL oracle
- Caveat/review: PENDING; Separate this from 487 to the original INVITE; both may occur in the same callback.

## SIP-KAM-018: A matching CANCEL received before final response to an INVITE causes the original INVITE to receive 487.

- Category/role: CANCEL effect on INVITE; UAS/proxy transaction layer
- RFC source: [RFC3261 9.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-9.2) — SHOULD behavior
- Evidence summary: If no final response has been sent for the INVITE, the UAS behavior SHOULD generate a 487 response.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (cancel_matches_invite_before_final -> F [0,2] original_invite_tx_487)`
- Mathematical MITL: `G(cancel_matches_invite_before_final -> F_[0,2ms] original_invite_tx_487)`
- APs: `cancel_matches_invite_before_final, original_invite_tx_487`
- Correlation: CANCEL transaction + original INVITE transaction
- Primary hooks: HK_FORWARD_NONACK, HK_E2E_CANCEL, HK_SEND_PR_BUFFER
- Auxiliary hooks: HK_CANCEL_BRANCH
- Positive timed word: `time,props ; 0,{cancel_matches_invite_before_final} ; 1,{original_invite_tx_487}`
- Negative timed word: `time,props ; 0,{cancel_matches_invite_before_final} ; 3,{original_invite_tx_487}`
- Observability/oracle: white-box cancel effect and send hook; pcap cross-check; high: protocol-visible violation
- Caveat/review: PENDING; If downstream branch already sent a final response, this obligation must be suppressed by correlation state.

## SIP-KAM-019: A stateful proxy should only generate branch CANCEL after a provisional response makes that branch cancelable.

- Category/role: proxy branch CANCEL gating; stateful proxy/client transaction
- RFC source: [RFC3261 9.1 and 16.10](https://www.rfc-editor.org/rfc/rfc3261.html#section-16.10) — MUST/MAY constrained by RFC9.1/16.10
- Evidence summary: A stateful proxy cancels pending client transactions, subject to the caller-side CANCEL rule that a provisional response was received.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (branch_cancel_requested_without_provisional -> G [0,2] (!branch_cancel_sent))`
- Mathematical MITL: `G(branch_cancel_requested_without_provisional -> G_[0,2ms] not branch_cancel_sent)`
- APs: `branch_cancel_requested_without_provisional, branch_cancel_sent`
- Correlation: client branch id derived after transaction correlation
- Primary hooks: HK_CANCEL_BRANCH, HK_E2E_CANCEL
- Auxiliary hooks: HK_REPLY_RECEIVED
- Positive timed word: `time,props ; 0,{branch_cancel_requested_without_provisional} ; 1,{}`
- Negative timed word: `time,props ; 0,{branch_cancel_requested_without_provisional} ; 1,{branch_cancel_sent}`
- Observability/oracle: white-box branch state and send hook; medium/high: avoids illegal early downstream CANCEL
- Caveat/review: Manual review must classify force/local-cancel modes that intentionally deviate.; Should forced local CANCEL paths be excluded from the main property or modeled as legal supersession?

## SIP-KAM-020: A stateful proxy must not immediately forward 100 Trying responses upstream.

- Category/role: proxy 100 Trying forwarding; stateful proxy
- RFC source: [RFC3261 16.7](https://www.rfc-editor.org/rfc/rfc3261.html#section-16.7) — MUST NOT/proxy response processing
- Evidence summary: Stateful proxies forward provisional responses except 100 Trying; 100 Trying is not immediately forwarded.
- Time bound: `2` ms; source: adapter microstep expansion
- MightyPPL: `G* (proxy_rx_100_trying_response -> G [0,2] (!proxy_forward_100_trying))`
- Mathematical MITL: `G(proxy_rx_100_trying_response -> G_[0,2ms] not proxy_forward_100_trying)`
- APs: `proxy_rx_100_trying_response, proxy_forward_100_trying`
- Correlation: response branch matched to proxy response context
- Primary hooks: HK_REPLY_RECEIVED, HK_RELAY_REPLY
- Auxiliary hooks: HK_SEND_PR_BUFFER
- Positive timed word: `time,props ; 0,{proxy_rx_100_trying_response} ; 1,{}`
- Negative timed word: `time,props ; 0,{proxy_rx_100_trying_response} ; 1,{proxy_forward_100_trying}`
- Observability/oracle: upstream response hook plus actual send hook; high: externally visible proxy violation
- Caveat/review: PENDING; Needs send-direction metadata to avoid confusing downstream 100 generation with upstream forwarding.
