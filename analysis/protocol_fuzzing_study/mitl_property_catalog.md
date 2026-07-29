# SIP MITL 真实性质目录（20 条主目录）

> 状态：机器构造与手工正反例验证完成；所有人审状态仍为 `PENDING`，不得直接进入论文主张。

统一语义：按事务关联后投影；绝对整数毫秒；完整 AP valuation；缺失 AP=false；finite + flatten + pointwise；动态事务标识不进入 AP。

## SIP-TX-01 — Timer A initial schedule

- RFC：[RFC 3261 §17.1.1.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.2)；强度 `MUST`。
- 性质：UDP INVITE 进入 Calling 后，Timer A 在 T1 前不得触发，并应在 T1 时触发或因事务停止而取消。
- MightyPPL：`G* (udp_invite_sent -> (G [0,500) (!timer_a_fired) && F [0,500] (timer_a_fired || invite_transaction_stopped)))`
- AP：`udp_invite_sent, timer_a_fired, invite_transaction_stopped`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2505-2524`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2505)，符号 `tsx_on_state_null`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-02 — Timer A causes the first INVITE retransmission

- RFC：[RFC 3261 §17.1.1.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.2)；强度 `MUST`。
- 性质：未被响应或停止的 UDP INVITE 必须在首个 T1 周期结束前产生第一次重传。
- MightyPPL：`G* (udp_invite_sent -> (G [0,500) (!invite_retransmitted) && F [0,500] (invite_retransmitted || invite_transaction_stopped)))`
- AP：`udp_invite_sent, invite_retransmitted, invite_transaction_stopped`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2540-2555`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2540)，符号 `tsx_on_state_calling`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-03 — Timer A second interval doubles

- RFC：[RFC 3261 §17.1.1.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.2)；强度 `MUST`。
- 性质：第一次 Timer A 周期完成后，下一次重传间隔必须为 2*T1，除非事务提前停止。
- MightyPPL：`G* (timer_a_first_cycle_completed -> (G [0,1000) (!invite_retransmitted) && F [0,1000] (invite_retransmitted || invite_transaction_stopped)))`
- AP：`timer_a_first_cycle_completed, invite_retransmitted, invite_transaction_stopped`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2336-2376`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2336)，符号 `tsx_resched_retransmission`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-04 — Timer B transaction deadline

- RFC：[RFC 3261 §17.1.1.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.2)；强度 `MUST/SHOULD`。
- 性质：INVITE 客户事务在 64*T1 前不得 Timer B 超时，并应在该时刻前收到最终响应或 Timer B 触发。
- MightyPPL：`G* (invite_client_calling_entered -> (G [0,32000) (!timer_b_fired) && F [0,32000] (timer_b_fired || invite_final_response_received)))`
- AP：`invite_client_calling_entered, timer_b_fired, invite_final_response_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2505-2512;2557-2570`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2505)，符号 `tsx_on_state_null/tsx_on_state_calling`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-05 — Provisional response stops INVITE retransmission

- RFC：[RFC 3261 §17.1.1.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.2)；强度 `SHOULD NOT`。
- 性质：同一 INVITE 事务收到 1xx 后不应继续重传 INVITE。
- MightyPPL：`G* (invite_provisional_received -> G* (!invite_retransmitted))`
- AP：`invite_provisional_received, invite_retransmitted`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2586-2623`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2586)，符号 `tsx_on_state_calling`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：SHOULD NOT 被用作异常 oracle；请确认是否作为论文主性质或降为软违反。

## SIP-TX-06 — Timer D minimum retention

- RFC：[RFC 3261 §17.1.1.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.2)；强度 `SHOULD`。
- 性质：UDP INVITE 客户事务进入 Completed 后至少 32 秒内不得终止。
- MightyPPL：`G* (udp_invite_client_completed -> G [0,32000) (!transaction_terminated))`
- AP：`udp_invite_client_completed, transaction_terminated`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:3131-3196`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L3131)，符号 `tsx_on_state_proceeding_uac`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-07 — Timer E initial schedule

- RFC：[RFC 3261 §17.1.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.2.2)；强度 `MUST`。
- 性质：UDP non-INVITE 进入 Trying 后，Timer E 在 T1 前不得触发，并应在 T1 时触发或因最终响应停止。
- MightyPPL：`G* (udp_noninvite_sent -> (G [0,500) (!timer_e_fired) && F [0,500] (timer_e_fired || noninvite_final_response_received)))`
- AP：`udp_noninvite_sent, timer_e_fired, noninvite_final_response_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2514-2524`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2514)，符号 `tsx_on_state_null`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-08 — Timer E causes the first non-INVITE retransmission

- RFC：[RFC 3261 §17.1.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.2.2)；强度 `MUST`。
- 性质：未收到最终响应的 UDP non-INVITE 必须在首个 T1 周期结束前产生第一次重传。
- MightyPPL：`G* (udp_noninvite_sent -> (G [0,500) (!noninvite_retransmitted) && F [0,500] (noninvite_retransmitted || noninvite_final_response_received)))`
- AP：`udp_noninvite_sent, noninvite_retransmitted, noninvite_final_response_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2546-2555`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2546)，符号 `tsx_on_state_calling`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-09 — Timer E second interval doubles

- RFC：[RFC 3261 §17.1.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.2.2)；强度 `MUST`。
- 性质：第一次 Timer E 周期完成后，下一次重传间隔必须为 MIN(2*T1,T2)。
- MightyPPL：`G* (timer_e_first_cycle_completed -> (G [0,1000) (!noninvite_retransmitted) && F [0,1000] (noninvite_retransmitted || noninvite_final_response_received)))`
- AP：`timer_e_first_cycle_completed, noninvite_retransmitted, noninvite_final_response_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2342-2354`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2342)，符号 `tsx_resched_retransmission`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-10 — Timer E switches to T2 after provisional

- RFC：[RFC 3261 §17.1.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.2.2)；强度 `MUST`。
- 性质：收到 non-INVITE 1xx 后，Timer E 应切换为 T2；在 T2 前不得触发，并在 T2 时触发或被最终响应取消。
- MightyPPL：`G* (noninvite_provisional_received -> (G [0,4000) (!timer_e_fired) && F [0,4000] (timer_e_fired || noninvite_final_response_received)))`
- AP：`noninvite_provisional_received, timer_e_fired, noninvite_final_response_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2600-2623`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2600)，符号 `tsx_on_state_calling`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-11 — Timer F transaction deadline

- RFC：[RFC 3261 §17.1.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.2.2)；强度 `SHOULD/MUST`。
- 性质：non-INVITE 客户事务在 64*T1 前不得 Timer F 超时，并应在该时刻前收到最终响应或 Timer F 触发。
- MightyPPL：`G* (noninvite_trying_entered -> (G [0,32000) (!timer_f_fired) && F [0,32000] (timer_f_fired || noninvite_final_response_received)))`
- AP：`noninvite_trying_entered, timer_f_fired, noninvite_final_response_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2505-2512;2557-2570`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2505)，符号 `tsx_on_state_null/tsx_on_state_calling`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-12 — Timer K retention

- RFC：[RFC 3261 §17.1.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.2.2)；强度 `MUST`。
- 性质：UDP non-INVITE 客户事务进入 Completed 后保持 T4，然后在 Timer K 触发时终止。
- MightyPPL：`G* (udp_noninvite_client_completed -> (G [0,5000) (!transaction_terminated) && F [0,5000] transaction_terminated))`
- AP：`udp_noninvite_client_completed, transaction_terminated`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:3037-3069`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L3037)，符号 `tsx_on_state_proceeding_uac`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-13 — Timer G initial schedule

- RFC：[RFC 3261 §17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1)；强度 `MUST`。
- 性质：UDP INVITE 服务事务发出 300--699 并进入 Completed 后，Timer G 在 T1 前不得触发。
- MightyPPL：`G* (udp_invite_server_completed -> (G [0,500) (!timer_g_fired) && F [0,500] (timer_g_fired || ack_received)))`
- AP：`udp_invite_server_completed, timer_g_fired, ack_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2865-2915`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2865)，符号 `tsx_on_state_proceeding_uas`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-14 — Timer G causes the first final-response retransmission

- RFC：[RFC 3261 §17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1)；强度 `MUST`。
- 性质：未收到 ACK 的 UDP INVITE 服务事务必须在首个 T1 周期结束前重传 300--699 最终响应。
- MightyPPL：`G* (udp_invite_server_completed -> (G [0,500) (!final_response_retransmitted) && F [0,500] (final_response_retransmitted || ack_received)))`
- AP：`udp_invite_server_completed, final_response_retransmitted, ack_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2928-2944`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2928)，符号 `tsx_on_state_proceeding_uas`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-15 — Timer G second interval doubles

- RFC：[RFC 3261 §17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1)；强度 `MUST`。
- 性质：第一次 Timer G 周期完成后，下一次最终响应重传间隔必须为 MIN(2*T1,T2)。
- MightyPPL：`G* (timer_g_first_cycle_completed -> (G [0,1000) (!final_response_retransmitted) && F [0,1000] (final_response_retransmitted || ack_received)))`
- AP：`timer_g_first_cycle_completed, final_response_retransmitted, ack_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2355-2367`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2355)，符号 `tsx_resched_retransmission`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-16 — Timer H transaction deadline

- RFC：[RFC 3261 §17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1)；强度 `MUST`。
- 性质：INVITE 服务事务进入 Completed 后，Timer H 在 64*T1 前不得触发，并应在期限内收到 ACK 或 Timer H 触发。
- MightyPPL：`G* (invite_server_completed -> (G [0,32000) (!timer_h_fired) && F [0,32000] (timer_h_fired || ack_received)))`
- AP：`invite_server_completed, timer_h_fired, ack_received`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2878-2888;3285-3295`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2878)，符号 `tsx_on_state_proceeding_uas/tsx_on_state_completed_uas`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-17 — ACK stops Timer G retransmissions

- RFC：[RFC 3261 §17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1)；强度 `MUST`。
- 性质：Completed 中收到匹配 ACK 后，最终响应重传必须停止。
- MightyPPL：`G* (ack_received -> G* (!final_response_retransmitted))`
- AP：`ack_received, final_response_retransmitted`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:3232-3271`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L3232)，符号 `tsx_on_state_completed_uas`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-18 — Timer I retention

- RFC：[RFC 3261 §17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1)；强度 `MUST`。
- 性质：UDP INVITE 服务事务进入 Confirmed 后保持 T4，并在 Timer I 触发时终止。
- MightyPPL：`G* (udp_invite_server_confirmed -> (G [0,5000) (!transaction_terminated) && F [0,5000] transaction_terminated))`
- AP：`udp_invite_server_confirmed, transaction_terminated`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:3251-3267;3399-3411`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L3251)，符号 `tsx_on_state_completed_uas/tsx_on_state_confirmed`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-19 — Timer J retention

- RFC：[RFC 3261 §17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2)；强度 `MUST`。
- 性质：UDP non-INVITE 服务事务进入 Completed 后保持 64*T1，并在 Timer J 触发时终止。
- MightyPPL：`G* (udp_noninvite_server_completed -> (G [0,32000) (!transaction_terminated) && F [0,32000] transaction_terminated))`
- AP：`udp_noninvite_server_completed, transaction_terminated`
- 源码：[`pjsip/src/pjsip/sip_transaction.c:2889-2897;3299-3303`](https://github.com/pjsip/pjproject/blob/bba95b8a95c0a9e8c1939166fd20083ae9e3e956/pjsip/src/pjsip/sip_transaction.c#L2889)，符号 `tsx_on_state_proceeding_uas/tsx_on_state_completed_uas`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：请确认该事务投影与 RFC 角色/传输条件一致。

## SIP-TX-20 — Timer C exceeds three minutes

- RFC：[RFC 3261 §16.6](https://www.rfc-editor.org/rfc/rfc3261.html#section-16.6)；强度 `MUST`。
- 性质：有状态代理转发每个 INVITE 客户事务时必须设置 Timer C，且 3 分钟内（含边界）不得触发。
- MightyPPL：`G* (proxy_invite_forwarded -> G [0,180000] (!timer_c_fired))`
- AP：`proxy_invite_forwarded, timer_c_fired`
- 源码：[`src/modules/tm/timer.h:171-200`](https://github.com/kamailio/kamailio/blob/2648eb330b133a20f1398d59a28c53532106cad3/src/modules/tm/timer.h#L171)，符号 `_set_fr_retr`。
- 机器验证：`PASS`；positive=POSITIVE，negative=NEGATIVE，symbolic/concrete=True。
- 待审：RFC 要求严格大于 3 分钟；Kamailio 的 180000 ms 默认值需要人工判断为实现偏差、代理级 lifetime 近似或配置要求。
