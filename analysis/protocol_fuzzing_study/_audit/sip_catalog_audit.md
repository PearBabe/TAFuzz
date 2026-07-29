# SIP MITL candidate catalog independent audit

Date: 2026-07-13 (Asia/Shanghai)  
Scope: `SIP-TX-01..20` in the base catalog and `SIP-TX-21..26` in the
RFC 6026 staging catalog.  This was a read-only evidence audit.  No SUT was
built or run and no candidate/catalog output was changed.

## 1. Bottom line

The current 26 records are **not ready for direct admission**.  Their formula
files are syntactically executable, but syntactic execution does not establish
that the formula says what the RFC says or that an AP timestamp denotes the
right protocol event.

| Disposition | Count | IDs |
|---|---:|---|
| `APPROVE` | 0 | none |
| `FIX` | 23 | 01, 03--07, 09--13, 15--26 |
| `REJECT` | 3 | 02, 08, 14 |

Consequently, the independent-audit admission count is **0/26 until the 23
field-level fixes below are applied and revalidated**.  This does not say that
all 23 underlying RFC requirements are bad candidates.  It says their current
records still conflate timer scheduling with callback/send time, omit permitted
supersession paths, use incomplete AP/source mappings, or do not distinguish
mathematical infinite-trace `G` from MightyPPL finite-word `G*`.

At audit time the generated `protocols/sip/` directory admitted 13 records
(02, 03, 04, 11, 16, 18, 19, 21--26) and rejected the other 13 through its
source-symbol gate.  The present semantic/source audit is stricter: **none of
those 13 generated admissions should remain admitted unchanged**.  TX-02 is a
timed-catalog rejection and the other 12 require the fixes below.

The three rejected records are different: `SIP-TX-02`, `SIP-TX-08`, and
`SIP-TX-14` turn the immediate action taken *when a timer fires* into a second
exact wall-clock deadline measured from an earlier send/state event.  This is
both redundant with the corresponding timer property and unsupported without
a punctual/same-microstep or implementation-specific dispatch-latency
contract.  Preserve them as untimed adapter consistency assertions, e.g.
`timer_a_callback -> invite_passed_to_transport`, not as independent MITL
timing properties.

## 2. Evidence and reproducibility

### 2.1 Normative sources

- RFC 3261, especially sections 16.6--16.8, 17.1.1.1--17.1.2.2, and
  17.2.1--17.2.2: <https://www.rfc-editor.org/rfc/rfc3261.html>
- RFC 6026, especially sections 7.1, 7.2, 8.1, and 8.4:
  <https://www.rfc-editor.org/rfc/rfc6026.html>

The downloaded RFC text hashes used during this audit were:

```text
RFC 3261  d513777f77fea01a4de9c0a2d9d6713cb53b8231f1b7a2ab56705f8d51b066dc
RFC 6026  4f81ec1638278f19b48a6976981c4aeb003ba5667ad2f944a96819be017b4ab9
```

### 2.2 Fixed source revisions

| Implementation | Commit | Principal audited files |
|---|---|---|
| PJSIP | `bba95b8a95c0a9e8c1939166fd20083ae9e3e956` | `pjsip/src/pjsip/sip_transaction.c`, `pjsip/include/pjsip/sip_config.h` |
| Kamailio | `2648eb330b133a20f1398d59a28c53532106cad3` | `src/modules/tm/{timer.h,t_reply.c,t_lookup.c,config.h,config.c,README}` |
| Doubango | `7604ae6761534d2efdc862bc9961623abc98b9a5` | `tinySIP/src/transactions/{tsip_transac_ist.c,tsip_transac_ict.c}`, `tinySIP/src/tsip_timers.c` |

Raw fixed-commit files were fetched successfully.  Representative SHA-256
values were:

```text
PJSIP sip_transaction.c  d7a125671aab5ea8e477fc77d386fdec6ec299f935b7fae0ec8a2d272c61d56c
Kamailio timer.h          5b66b84542f7b6567aae95a1cd1fa3bfcf87fb751468ba2b1b232b87b55d9127
Kamailio config.h         397c25ea70df9916982af835df6700a7c704c7bcf7c06e6c13b4dd3f1f81c248
```

The Doubango and Kamailio local audit checkouts both resolved to the cataloged
40-character commits.  No moving branch was used as code evidence.

### 2.3 Formula rerun

All supplied positive/negative traces were independently rerun in both
symbolic and concrete modes:

```text
TAMonitor --trace <trace> --formula <formula> \
  --word finite --build-mode flatten --state <symbolic|concrete> --out /tmp/...

rerun_ok=104 rerun_bad=0 total=104
```

This confirms only that every *supplied* positive/negative pair receives its
declared verdict.  Most exact-deadline records supply only one of the two
necessary counterexamples (early versus missing/late), so the traces do not
independently exercise both conjuncts of
`G [0,T) !event && F [0,T] event`.

`agent-reach check-update` could not be run because the CLI is absent in this
environment (`command not found`).  Official RFC Editor and fixed GitHub
content remained available through HTTPS.

## 3. Catalog-wide blocking findings

The following changes apply to every `FIX` record unless a per-property entry
narrows them.

### C1. Separate timer arm, logical deadline, callback, and protocol action

Four different events are currently collapsed:

1. the timer is successfully armed;
2. its stored logical deadline becomes due;
3. the scheduler invokes the callback;
4. the callback passes a SIP message to the transport or changes state.

An RFC timer value supports a property over (1)--(2).  It does not, by itself,
prove zero scheduler latency from (2) to (3), or zero processing latency from
(3) to (4).  Every timer AP must therefore carry at least
`arm_tick`, `configured_delay`, `deadline_tick`, `callback_tick`, and a
cancellation/supersession reason.  Use a composite trigger emitted *after a
successful arm*, e.g. `timer_a_armed_t1`, rather than `udp_invite_sent`.

The timer-schedule template is:

```text
G* (timer_x_armed_T ->
    (G [0,T) (!timer_x_deadline_reached) &&
     F [0,T] (timer_x_deadline_reached || timer_x_superseded)))
```

The timestamp of `timer_x_deadline_reached` is the stored logical deadline.
Callback latency and send latency must be separate implementation-profile
properties if the experiment wants to fuzz them.

### C2. Mathematical versus finite-word semantics

`G*` is a MightyPPL finite-word operator, not standard mathematical MITL
notation.  Each record must store:

- `mathematical_mitl` using mathematical `G` and an explicit transaction
  lifetime; and
- `mightyppl_formula` using `G*`, together with a closed-projection rule.

For unbounded cancellation properties (05, 17, 24), a positive verdict is only
claimable when the adapter keeps the projection open through transaction or
dialog destruction (or another declared observation horizon).  A prefix that
ends just after ACK/1xx is not evidence that no later retransmission occurred.

### C3. One trigger generation per monitor instance

The adapter must correlate first and instantiate one monitor per timer/request
generation.  No timed word used for a bounded obligation may contain two
occurrences of its trigger AP.  This is required both for an unambiguous timer
generation and because the current TAMonitor overlapping-trigger regression can
mask one outstanding bounded obligation.  `SIP-TX-23` needs a fresh monitor
instance for every capped Timer-X generation.

### C4. Complete AP definitions and reverse source maps

The base `atomic_proposition_map.yaml` currently defines APs by expanding their
names (for example, “timer a fired”).  It does not specify an executable event
predicate, hook, event ordering, or source lines.  This fails the requested
source mapping even when the property record itself points to a containing
function.  Every AP needs:

- role, method, transport and transaction-state predicates;
- the exact pre/post hook and microstep ordering;
- its correlation fields;
- fixed-commit file/symbol/line mappings; and
- whether it is a raw event, latched cause, or derived deadline event.

### C5. Exercise both halves of every exact-bound formula

For each formula with both `G [0,T)` and `F [0,T]`, retain the exact-bound
positive trace and add **two** negatives:

- early event at `T-1`; and
- missing event through `T+1` (or event first appearing at `T+1`).

Add positive supersession traces for every allowed alternative.  In
particular, Timer B must test a 1xx transition, Timer E tests must cover the
1xx/T2 transition, and client timers must cover transport failure where RFC
3261 permits it.

### C6. Source map must include constants and all terminal paths

A call to `tsx_schedule_timer()` is not enough.  Add the definitions that
supply T1/T2/T4/64*T1 and every source path that can cancel or terminate the
obligation.  Important common anchors are:

- PJSIP `sip_config.h:1075-1091`, `sip_transaction.c:125-134,441-454`;
- PJSIP callback/transport paths
  `sip_transaction.c:1116-1195,1933-1982,2110-2137,2215-2237`;
- Doubango `tsip_timers.c:80-126` and the FSM registration/initialization
  blocks, not only the action callbacks.

## 4. Per-property dispositions and direct fixes

Intervals below use the existing integer-millisecond pointwise profile.  AP
names ending in `_deadline` mean the logical stored deadline, not callback
entry or successful network send.

### SIP-TX-01 — `FIX`

- **RFC:** RFC 3261 section 17.1.1.2 requires an unreliable INVITE client
  transaction to start Timer A at T1.
- **Problem:** the trigger is `udp_invite_sent`, while PJSIP sends first and
  arms Timer A later (`sip_transaction.c:2499-2524`).  `timer_a_fired` is not
  defined as deadline versus callback.  The sole negative tests only early
  firing.
- **Patch:** use
  `G* (timer_a_armed_t1 -> (G [0,500) !timer_a_deadline && F [0,500]
  (timer_a_deadline || invite_transaction_stopped)))`.  Emit the trigger after
  successful `tsx_schedule_timer`; add constants at `sip_config.h:1075-1091`
  and `sip_transaction.c:125-134,441-454`; add a missing-at-501 negative.

### SIP-TX-02 — `REJECT`

- **RFC:** RFC 3261 says that *when Timer A fires*, the request is passed to
  the transport again.
- **Problem:** the formula instead requires a transport action at exactly
  500 ms after the original send.  PJSIP re-arms before calling
  `tsx_send_msg()` (`sip_transaction.c:2383-2424`), and the RFC supplies no
  non-punctual scheduler/dispatch-latency bound.  It duplicates TX-01.
- **Disposition:** remove from the MITL timing count.  Keep the untimed
  same-callback consistency assertion
  `timer_a_callback -> invite_retransmit_requested`, with callback-before-send
  microsteps explicitly ordered.

### SIP-TX-03 — `FIX`

- **RFC:** INVITE Timer-A intervals double without a T2 cap while Calling.
- **Problem:** `timer_a_first_cycle_completed` does not say whether the new
  timer was armed; the future event is an actual send/callback.  The source
  range omits `tsx_retransmit()` and the provided negative covers only early
  action.
- **Patch:** trigger `timer_a_rearmed_2t1` after
  `tsx_resched_retransmission`; monitor `timer_a_deadline` or transaction stop.
  Map `sip_transaction.c:2336-2376,2383-2424`; add missing/late and stop
  traces.

### SIP-TX-04 — `FIX`

- **RFC:** Timer B is started at 64*T1 while the INVITE client is Calling.  A
  provisional response moves it to Proceeding; a transport error may also end
  the transaction.
- **Problem:** `invite_client_calling_entered` is not a post-arm AP, and the
  formula accepts only final response or Timer B.  It therefore reports a
  compliant early 1xx transition or transport failure as a violation.
- **Patch:** use `timer_b_armed_64t1` and alternatives
  `timer_b_deadline || invite_provisional_received ||
  invite_final_response_received || invite_transport_error`.  Map
  `sip_transaction.c:2505-2512,2557-2570,2586-2623` plus the shared constant
  and transport-error lines.  Add positive 1xx/transport supersession and
  missing-at-32001 traces.  Record strength as `MUST` for arm and `SHOULD` for
  timeout notification, not an undifferentiated `MUST/SHOULD`.

### SIP-TX-05 — `FIX`

- **RFC:** RFC 3261 section 17.1.1.2 says the client in Proceeding SHOULD NOT
  continue INVITE retransmission.
- **Problem:** this is a soft, unbounded state property, not a 32000-ms
  property; the catalog nevertheless records `time_value_ms=32000`.  Its
  mathematical formula incorrectly contains MightyPPL `G*`, and the AP map
  does not define post-cancellation ordering.
- **Patch:** set no numeric time constant; mathematical formula
  `G (entered_proceeding_after_1xx -> G !invite_retransmitted)`; MightyPPL
  formula may retain `G*` only with a projection closed at transaction end.
  Define the trigger after lines 2600-2617 cancel Timer A and map the continued
  state handling through `sip_transaction.c:2973-3020`.  Keep
  `SHOULD_NOT_SOFT_ORACLE` in the strength/review fields.

### SIP-TX-06 — `FIX`

- **RFC:** RFC 6026 section 8.4 updates Timer D to a MUST and keeps the
  unreliable-transport value at least 32 seconds.  RFC 3261 transport-error
  handling can terminate a client transaction early.
- **Problem:** the record cites only the older RFC 3261 SHOULD, treats all
  early termination as a Timer-D violation, and emits its state AP before the
  later timer schedule in PJSIP.
- **Patch:** trigger `udp_invite_completed_timer_d_armed`; formula
  `G* (trigger -> G [0,32000) (!transaction_terminated ||
  client_transport_abort))`.  Require `client_transport_abort` and termination
  in the same microstep.  Map `sip_transaction.c:3131-3196` plus the shared
  transport-error paths and add RFC 6026 section 8.4 as the current normative
  anchor.

### SIP-TX-07 — `FIX`

- **RFC:** unreliable non-INVITE clients start Timer E at T1.
- **Problem:** send and arm are collapsed; a first provisional response
  supersedes the original Timer-E generation, and transport failure is also
  missing from the alternatives.
- **Patch:** trigger `timer_e_armed_t1`; outcomes
  `timer_e_deadline || timer_e_rearmed_on_first_1xx ||
  noninvite_final_response_received || noninvite_transport_error`.  Map
  `sip_transaction.c:2514-2524,2586-2623` and constants; add missing,
  provisional-supersession, and transport-supersession traces.

### SIP-TX-08 — `REJECT`

- **Problem:** like TX-02, it converts “if Timer E fires, pass the request to
  transport” into an exact action deadline from the original send.  This is
  redundant with TX-07 and has no RFC dispatch-latency interval.
- **Disposition:** retain only
  `timer_e_callback -> noninvite_retransmit_requested` as an untimed adapter
  assertion; include `sip_transaction.c:2383-2424,2546-2555` in that assertion's
  source map.

### SIP-TX-09 — `FIX`

- **RFC:** Trying-state Timer E uses `min(2*old,T2)`.
- **Problem:** a 1xx received before the pending 2*T1 expiry moves the
  transaction to Proceeding and changes the Timer-E regime, but the formula
  accepts only a final response.  Callback/send is again used as deadline.
- **Patch:** trigger `timer_e_rearmed_2t1`; outcomes
  `timer_e_deadline || timer_e_rearmed_on_first_1xx || final ||
  transport_error`.  Map `sip_transaction.c:2336-2354,2383-2424,2586-2623`;
  add missing and 1xx-supersession traces.

### SIP-TX-10 — `FIX`

- **RFC:** RFC 3261 requires T2 spacing for retransmissions in Proceeding, but
  its formal text directly requires a T2 reset when Timer E fires *while in
  Proceeding*.  It does not unambiguously state an exact new deadline measured
  from the instant every 1xx is received.
- **Problem:** the generic `noninvite_provisional_received` trigger can repeat
  and overstates the standard by anchoring a new 4-second period to each 1xx.
  PJSIP's immediate cancel/re-arm at lines 2600-2623 is an implementation
  choice.
- **Patch:** for a normative property, trigger
  `timer_e_fired_in_proceeding_and_rearmed_t2` and monitor its next deadline.
  If the current first-1xx trigger is retained, relabel the record
  `PJSIP_IMPLEMENTATION_PROFILE`, use only the Trying-to-Proceeding transition,
  and do not claim RFC MUST conformance.  Add late/missing and transport/final
  supersession traces.

### SIP-TX-11 — `FIX`

- **RFC:** the client SHOULD set Timer F at 64*T1; timeout handling is also
  SHOULD in Trying, while Proceeding contains stronger transition language.
- **Problem:** the trigger is not post-arm, transport error is omitted, and
  `SHOULD/MUST` obscures which action has which strength.
- **Patch:** trigger `timer_f_armed_64t1`; outcomes
  `timer_f_deadline || noninvite_final_response_received ||
  noninvite_transport_error`.  Map `sip_transaction.c:2505-2512,2557-2570,
  2973-3013` plus constants/transport paths.  Add missing and transport traces;
  use `SHOULD` for the arm property.

### SIP-TX-12 — `FIX`

- **RFC:** Timer K is T4 on unreliable transport and termination follows its
  firing.
- **Problem:** the source range covers the 2xx completion path but not the
  300--699 path or the Completed-state timeout handler.  Early permitted
  transport termination and logical deadline versus callback are not modeled;
  only the early half is tested.
- **Patch:** trigger `udp_noninvite_completed_timer_k_armed`; exact-deadline
  formula with `transaction_terminated || client_transport_abort`.  Require
  an atomic abort+termination event.  Map
  `sip_transaction.c:3037-3069,3131-3196,3322-3336` plus constants and
  transport paths; add missing/late and abort-positive traces.

### SIP-TX-13 — `FIX`

- **RFC:** RFC 3261 section 17.2.1 specifies Timer G at T1 for unreliable
  300--699 INVITE server responses, but that sentence is normative procedure,
  not an RFC 2119 `MUST` token.
- **Problem:** strength is inflated to MUST; entry and arm are collapsed;
  transport failure is omitted and only early expiry is tested.
- **Patch:** use `timer_g_armed_t1`; outcomes
  `timer_g_deadline || matched_non2xx_ack || server_transport_error`.
  Map `sip_transaction.c:2865-2915,3211-3295` plus constants/transport paths;
  set strength `NORMATIVE_PROCEDURE`; add missing and transport/ACK traces.

### SIP-TX-14 — `REJECT`

- **Problem:** like 02/08, this duplicates the Timer-G deadline and invents a
  zero-latency wall-clock guarantee for passing the response to transport.
- **Disposition:** retain only the untimed assertion
  `timer_g_callback -> final_response_retransmit_requested`, sourced to
  `sip_transaction.c:2383-2424,2928-2944`; do not count it as a separate MITL
  timing property.

### SIP-TX-15 — `FIX`

- **RFC:** Timer G doubles with a T2 cap as normative procedure.
- **Problem:** callback/action and deadline are collapsed, source lines omit
  the callback/re-arm caller, transport termination is absent, strength is
  inflated, and no missing/late negative exists.
- **Patch:** trigger `timer_g_rearmed_min_2old_t2`; outcomes
  `timer_g_deadline || matched_non2xx_ack || server_transport_error`.
  Map `sip_transaction.c:2336-2376,2383-2424,3274-3284`; set strength
  `NORMATIVE_PROCEDURE`; add late and supersession traces.

### SIP-TX-16 — `FIX`

- **RFC:** Timer H MUST be set at 64*T1 in Completed; ACK or transport error
  can end/supersede that state.
- **Problem:** the record omits transport error, does not use a post-arm
  trigger, and tests only early expiry.
- **Patch:** trigger `timer_h_armed_64t1`; outcomes
  `timer_h_deadline || matched_non2xx_ack || server_transport_error`.
  Map `sip_transaction.c:2878-2888,3211-3295` plus constants/transport paths;
  add late and transport traces.

### SIP-TX-17 — `FIX`

- **RFC:** a matched non-2xx ACK moves Completed to Confirmed and Timer-G
  retransmission ceases.
- **Problem:** `ack_received` is too broad, its AP definition is not executable,
  and mathematical `G` is not separated from weak finite `G*`.
- **Patch:** AP `matched_non2xx_ack_post_timer_g_cancel`, defined after
  `sip_transaction.c:3232-3271`; mathematical formula
  `G (matched_ack -> G !final_response_retransmitted)`; finite formula keeps
  `G*` only on a projection closed through Timer I/destruction.  The existing
  retransmission-after-ACK negative is decisive once this contract is added.

### SIP-TX-18 — `FIX`

- **RFC:** Timer I is T4 on unreliable transport and the transaction
  terminates when it fires.
- **Problem:** state entry and successful arm are not distinguished, callback
  time is used as deadline, and no missing/late trace exists.
- **Patch:** trigger `udp_confirmed_timer_i_armed`; monitor logical deadline
  and generic termination.  Map `sip_transaction.c:3232-3271,3377-3411` plus
  T4 constants; add a missing-at-5001 negative.

### SIP-TX-19 — `FIX`

- **RFC:** unreliable non-INVITE server Completed state uses Timer J at
  64*T1 and terminates when it fires.
- **Problem:** the current APs do not prove the timer arm, callback and deadline
  are collapsed, and only early termination is tested.
- **Patch:** trigger `udp_noninvite_completed_timer_j_armed`; exact logical
  deadline formula.  Map `sip_transaction.c:2889-2897,3299-3303` plus
  constants; add a missing-at-32001 negative.

### SIP-TX-20 — `FIX` (current source map is materially wrong)

- **RFC:** Timer C must be set for each proxied INVITE and its value, including
  resets after 101--199, must be strictly greater than three minutes.
- **Problem 1:** the formula checks only “not fired by 180000” and therefore
  passes if Timer C was never armed.
- **Problem 2:** `_set_fr_retr` at `timer.h:159-220` operates Kamailio branch
  final-response/retransmission timers.  It is not by itself a sufficient map
  for RFC Timer C.  Kamailio uses `fr_inv_timeout`, provisional-reply restart,
  and a transaction-wide `max_inv_lifetime` interaction.
- **Problem 3:** the fixed source defaults are `fr_inv_timer=120000` and
  `max_inv_lifetime=180000`; Kamailio's own README labels the latter a Timer-C
  value, but RFC 3261 requires **greater than**, not equal to, 180000 ms.
- **Patch:** use
  `G* (proxy_invite_forwarded -> (timer_c_armed_gt_180000 &&
  G [0,180000] !timer_c_deadline))`.  Repeat it for every 101--199 reset.
  Define `timer_c_armed_gt_180000` from the stored delay/deadline, so a missing
  or short timer is immediately false.  Replace/extend the source map with:
  `t_lookup.c:1232-1250`, `t_reply.c:2696-2703`,
  `timer.h:159-220,268-288,331-343`, `config.h:47-68`,
  `config.c:50-71`, and `README:728-774,870-885`.  Declare the default fixed
  commit an expected violating profile unless configuration is pinned above
  180000.  Keep boundary-fire-at-180000 negative and add missing-arm plus
  compliant-180001 configuration traces.

### SIP-TX-21 — `FIX`

- **RFC:** RFC 6026 section 8.1 puts UAS-core 2xx retransmission at an interval
  starting at T1, with ACK cancellation.
- **Problem:** Doubango implements Timer X inside its server-transaction file,
  even though RFC 6026 section 7.1 says the server transaction itself must not
  originate 2xx retransmissions.  This is an implementation architecture
  caveat.  The record also maps actual callback send as an exact deadline and
  omits constant/initialization lines.
- **Patch:** distinguish `timer_x_armed_t1`, `timer_x_deadline`, and
  `uas_2xx_retransmit_requested`; use the timer schedule template for the first
  two and an untimed callback/action assertion for the third.  Add
  `tsip_timers.c:80-126`, `tsip_transac_ist.c:257-283,310-317,470-509,
  646-657`; add missing/late and ACK-supersession traces.  Keep the RFC
  UAS-core versus Doubango IST caveat explicit.

### SIP-TX-22 — `FIX` (useful known-deviation oracle)

- **RFC:** the interval after the first 2xx retransmission should be 2*T1,
  i.e. 1000 ms in the default profile.
- **Source finding:** Doubango initializes Timer X to 500
  (`tsip_transac_ist.c:317`), schedules it and immediately shifts the stored
  value to 1000 (`497-498`), then the first callback shifts it again to 2000
  before scheduling (`646-657`).  Thus the next observed interval is 2000 ms,
  not 1000 ms.  The current source range hides the first shift.
- **Patch:** keep the normative property as a deliberate bug oracle, but label
  the fixed commit `EXPECTED_VIOLATION`; trigger a post-first-send
  `timer_x_rearmed_expected_2t1`, retain raw and expected delay fields, and map
  `tsip_transac_ist.c:310-317,470-509,646-657` plus timer constants.  Add a
  missing/late negative and a source-realistic 2000-ms violating trace.

### SIP-TX-23 — `FIX` (useful known-deviation oracle)

- **RFC:** after reaching T2, every later 2xx retransmission interval remains
  capped at T2.
- **Source finding:** Doubango uses `timeout <<= 1` with no `min(...,T2)` at
  `tsip_transac_ist.c:655`, so Timer X eventually schedules 8000 ms and beyond.
- **Problem:** `uas_2xx_interval_at_t2` can be read as a one-shot transition;
  that would test one 4000-ms interval but miss the following uncapped one.
- **Patch:** instantiate one monitor for **each** post-retransmission
  generation once the expected interval has reached T2.  AP must carry
  `raw_delay_ms` and `expected_delay_ms=min(2*previous,T2)`.  Map
  `tsip_transac_ist.c:310-317,470-509,646-657` and `tsip_timers.c:80-130`.
  Add an early-at-3999 negative and a source-realistic next-at-8000 negative.

### SIP-TX-24 — `FIX`

- **RFC/source:** the network behavior is sound: RFC 6026 section 8.1 stops
  2xx retransmission on the matching ACK, and Doubango cancels Timer X at
  `tsip_transac_ist.c:664-670` while callback sends are at 646-657.
- **Remaining blockers:** `mathematical_mitl` still uses non-standard `G*`;
  the handling of a timer callback and ACK with the same integer timestamp is
  not ordered; a short finite positive trace is not a lifetime guarantee.
- **Patch:** mathematical formula
  `G (matched_2xx_ack_post_cancel -> G !uas_2xx_retransmitted)`; finite formula
  may use `G*` only after the projection continues through Timer L/dialog
  close.  Do not merge a pre-ACK timer callback with the ACK position: emit
  deterministic microsteps, order callback-send before ACK if it happened
  first, and emit the ACK AP only after successful cancellation.  With these
  fields patched, this is the closest record to approval.

### SIP-TX-25 — `FIX`

- **RFC:** Timer L is 64*T1 and the server transaction must not discard state
  merely because sending a response encounters a non-recoverable transport
  error.
- **Problem:** `server_transaction_terminated` is defined only as the Timer-L
  transition, so an early transport-error termination can disappear rather
  than violate the lower bound.  Doubango actually registers Any transport
  error -> Terminated at `tsip_transac_ist.c:295-300`, a potentially valuable
  known-deviation path omitted from the source map.
- **Patch:** emit the termination AP on **every** transition to Terminated;
  no transport-error exception is allowed for the RFC 6026 server property.
  Trigger only after Timer L arm.  Map `tsip_timers.c:80-126` and
  `tsip_transac_ist.c:257-317,470-509,673-716`; add missing/late and explicit
  early-transport-error negative traces.  Separate logical deadline from
  callback timestamp.

### SIP-TX-26 — `FIX`

- **RFC:** Timer M is 64*T1, while RFC 6026 permits client transaction state to
  be discarded on unrecoverable transport error.
- **Problem:** the current formula allows `client_transport_abort` alone to
  satisfy the eventual outcome, even if no termination was observed.  The
  source map omits the Any transport-error transitions and timer constants.
- **Patch:** use
  `G* (client_accepted_timer_m_armed ->
  (G [0,32000) (!client_transaction_terminated || client_transport_abort) &&
   F [0,32000] client_transaction_terminated))`, and enforce the AP invariant
  `client_transport_abort -> client_transaction_terminated` in the same
  microstep.  Map `tsip_timers.c:80-126` and
  `tsip_transac_ict.c:234-315,619-645,699-731`; add an allowed early
  abort+termination positive, abort-without-termination negative, and late
  Timer-M negative.

## 5. De-duplication decision

The following relationships must be explicit in the final catalog:

| Timer scheduling property | Immediate action assertion | Decision |
|---|---|---|
| TX-01 Timer A arm/deadline | TX-02 retransmit on callback | keep TX-01; move TX-02 to untimed adapter assertions |
| TX-07 Timer E arm/deadline | TX-08 retransmit on callback | keep TX-07; move TX-08 to untimed adapter assertions |
| TX-13 Timer G arm/deadline | TX-14 retransmit on callback | keep TX-13; move TX-14 to untimed adapter assertions |
| TX-21/22/23 Timer X schedule | callback passes saved 2xx | keep schedule properties; use one shared untimed callback assertion |

TX-05, TX-17, and TX-24 are not duplicate timer deadlines.  They are
cancellation/lifetime properties and may remain after their mathematical-
versus-finite semantics and observation-horizon fields are repaired.

## 6. Admission checklist after repair

A repaired SIP record may move from `FIX` to `APPROVE` only when all of these
are machine-checked:

1. AP definitions are executable predicates with fixed source hooks and reverse
   source mappings.
2. Every trigger is post-arm and occurs at most once per monitor projection.
3. Deadline, callback, send, cancel, and termination are distinct events.
4. Every RFC-permitted supersession/cancellation path has a positive trace.
5. Every dual-bound formula has exact-bound positive, early negative, and
   missing/late negative traces in symbolic and concrete modes.
6. `mathematical_mitl` uses mathematical `G`; `mightyppl_formula` and the
   finite closed-projection contract are stored separately.
7. Normative strength follows the exact RFC 2119 word or is labeled
   `NORMATIVE_PROCEDURE`; implementation-profile statements are not promoted
   to RFC requirements.
8. Fixed source ranges include timer constants, arm, cancel/supersession,
   callback, action, and all terminal paths.
9. Known implementation deviations (Kamailio Timer C; Doubango Timer X) are
   labeled expected violations, not presented as conforming source evidence.

## 7. Unresolved questions for human review

1. Will protocol-event timestamps represent stored logical deadlines, actual
   callback times, or both?  The audit recommends both fields and separate
   properties.
2. Is the experiment willing to treat PJSIP's immediate first-1xx Timer-E
   re-arm as an implementation profile rather than an RFC-wide MUST claim?
3. Should Kamailio be configured to `>180000` for a conforming control run and
   also run at its default 180000/120000 settings as a known violating target?
4. Should Doubango Timer-X doubling/cap behavior be retained as a historical
   real-bug target?  It is strong fuzzing evidence, but must not be described as
   a conforming implementation mapping.
5. For soft RFC `SHOULD/SHOULD NOT` properties such as TX-05 and Timer F, will
   the paper count them as soft protocol anomalies rather than hard failures?

## 8. Verification limitations

- This audit verified standards text, fixed source, formulas, and the supplied
  synthetic traces.  It did not compile or execute PJSIP, Kamailio, or
  Doubango, so it does not claim observed runtime conformance or violation.
- Source line locations are pinned to the stated commits; generated builds or
  vendor forks may differ.
- RFC timers are abstract protocol deadlines.  Real scheduler jitter cannot be
  silently converted into a standards tolerance; any tolerance must be an
  explicitly labeled implementation-profile property.
- The current MightyPPL overlapping-trigger behavior is handled here by the
  one-generation-per-monitor projection contract, not by claiming that the
  underlying monitor issue is fixed.
