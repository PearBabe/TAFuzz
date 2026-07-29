# Kamailio/SIP MITL 性质目录（独立重新分析）

- 生成日期：2026-07-13
- Kamailio 固定 commit：`2648eb330b133a20f1398d59a28c53532106cad3`
- ProfuzzBench 固定 commit：`8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074`
- 范围：面向 Kamailio/ProfuzzBench 的 SIP server、UAS、stateful proxy 性质；未复用历史 SIP catalog。
- 语义：pointwise finite timed word、整数毫秒、完整 AP valuation；动态 SIP ID 只作为 metadata。
- 审核状态：所有性质在用户签字前均保持 `PENDING`。

## SIP-KAM-001：新建 INVITE server transaction 进入 Proceeding，并把请求暴露给 transaction user

- 类别/角色：INVITE server transaction；UAS/server transaction
- RFC 来源：[RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- 证据摘要：为 INVITE 请求构造 server transaction 时，它从 Proceeding 状态开始，并把请求向上传递。
- 时间界限：`2` ms；来源：同一回调内的 adapter microstep expansion，不是 RFC 容差。
- MightyPPL：`G* (server_rx_invite_new_tx -> F [0,2] invite_tx_proceeding)`
- 数学 MITL：`G(server_rx_invite_new_tx -> F_[0,2ms] invite_tx_proceeding)`
- AP：`server_rx_invite_new_tx, invite_tx_proceeding`
- 关联键：Call-ID + CSeq number/method + top Via branch/sent-by
- 主 hook：HK_RX_PARSE_OK, HK_TX_NEW
- 辅助 hook：HK_TX_LOOKUP
- 正例 timed word：`time,props ; 0,{server_rx_invite_new_tx} ; 1,{invite_tx_proceeding}`
- 反例 timed word：`time,props ; 0,{server_rx_invite_new_tx} ; 3,{invite_tx_proceeding}`
- 可观测性/oracle：parser 与 transaction 创建后的白盒 hook；价值高，可捕获 transaction 创建/路由回归。
- 注意/审核：PENDING；benchmark 是否应把 parser 拒绝的 INVITE 与 malformed-message oracle 分开统计？

## SIP-KAM-002：若 INVITE 处理可能超过 RFC 200 ms 窗口且没有更早 TU response，则发送 100 Trying

- 类别/角色：INVITE provisional response；UAS/server transaction
- RFC 来源：[RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — SHOULD with timer bound
- 证据摘要：除非 server transaction 知道 TU 会在 200 ms 内响应，否则它会生成 100 Trying。
- 时间界限：`200` ms；来源：RFC3261 section 17.2.1
- MightyPPL：`G* (invite_auto_100_obligation -> F [0,200] uas_tx_100_trying)`
- 数学 MITL：`G(invite_auto_100_obligation -> F_[0,200ms] uas_tx_100_trying)`
- AP：`invite_auto_100_obligation, uas_tx_100_trying`
- 关联键：同一个 INVITE server transaction
- 主 hook：HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- 辅助 hook：HK_TX_NEW
- 正例 timed word：`time,props ; 0,{invite_auto_100_obligation} ; 100,{uas_tx_100_trying}`
- 反例 timed word：`time,props ; 0,{invite_auto_100_obligation} ; 201,{uas_tx_100_trying}`
- 可观测性/oracle：白盒 send hook；可用黑盒抓包交叉检查；价值中/高，可检测早期 provisional feedback 丢失。
- 注意/审核：必须固定 Kamailio `auto_inv_100` 与 route-script 行为；所选 Kamailio cfg 是否总是启用 `auto_inv_100`，还是应把它写成 profile-specific property？

## SIP-KAM-003：INVITE 处于 Proceeding 时，transaction layer 选择的 101-199 provisional response 会传给 transport

- 类别/角色：INVITE provisional relay；UAS/proxy transaction
- RFC 来源：[RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- 证据摘要：在 Proceeding 状态中，来自 TU 的 provisional response 会被传给 transport layer。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (invite_proceeding_tu_provisional -> F [0,2] uas_tx_provisional_response)`
- 数学 MITL：`G(invite_proceeding_tu_provisional -> F_[0,2ms] uas_tx_provisional_response)`
- AP：`invite_proceeding_tu_provisional, uas_tx_provisional_response`
- 关联键：同一个 INVITE transaction 与 response branch
- 主 hook：HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- 辅助 hook：HK_REPLY_RECEIVED
- 正例 timed word：`time,props ; 0,{invite_proceeding_tu_provisional} ; 1,{uas_tx_provisional_response}`
- 反例 timed word：`time,props ; 0,{invite_proceeding_tu_provisional} ; 3,{uas_tx_provisional_response}`
- 可观测性/oracle：send hook 加可选 pcap；价值高，可检测 provisional response 被吞掉的问题。
- 注意/审核：PENDING；确认 ProfuzzBench route 在 fuzzing 时是否暴露 upstream provisional response。

## SIP-KAM-004：Proceeding 中收到重传 INVITE 时，应重传最近的 provisional response，而不是创建新的 TU 事件

- 类别/角色：INVITE retransmission suppression；UAS/server transaction
- RFC 来源：[RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- 证据摘要：如果在 Proceeding 状态收到请求重传，则重传最近的 provisional response。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (invite_retransmission_in_proceeding_with_last_prov -> F [0,2] uas_retransmit_last_provisional)`
- 数学 MITL：`G(invite_retransmission_in_proceeding_with_last_prov -> F_[0,2ms] uas_retransmit_last_provisional)`
- AP：`invite_retransmission_in_proceeding_with_last_prov, uas_retransmit_last_provisional`
- 关联键：同一个 branch/sent-by/method transaction key
- 主 hook：HK_TX_LOOKUP, HK_RETRANSMIT_REPLY
- 辅助 hook：HK_SEND_PR_BUFFER
- 正例 timed word：`time,props ; 0,{invite_retransmission_in_proceeding_with_last_prov} ; 1,{uas_retransmit_last_provisional}`
- 反例 timed word：`time,props ; 0,{invite_retransmission_in_proceeding_with_last_prov} ; 3,{uas_retransmit_last_provisional}`
- 可观测性/oracle：白盒 transaction lookup 与 send hook；价值高，可捕获重复 transaction/TU re-entry bug。
- 注意/审核：PENDING；若要把它作为 bug claim，需要辅助计数器证明 TU 未被重新进入。

## SIP-KAM-005：TU 给出 300-699 final response 后，INVITE server transaction 进入 Completed 并发送该响应

- 类别/角色：INVITE final response；UAS/server transaction
- RFC 来源：[RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- 证据摘要：当 300 到 699 response 被传给 server transaction 时，它进入 Completed 并把 response 传给 transport。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (invite_proceeding_tu_final_300_699 -> F [0,2] invite_tx_completed_non2xx)`
- 数学 MITL：`G(invite_proceeding_tu_final_300_699 -> F_[0,2ms] invite_tx_completed_non2xx)`
- AP：`invite_proceeding_tu_final_300_699, invite_tx_completed_non2xx`
- 关联键：同一个 INVITE server transaction
- 主 hook：HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- 辅助 hook：HK_TIMER_ARM
- 正例 timed word：`time,props ; 0,{invite_proceeding_tu_final_300_699} ; 1,{invite_tx_completed_non2xx}`
- 反例 timed word：`time,props ; 0,{invite_proceeding_tu_final_300_699} ; 3,{invite_tx_completed_non2xx}`
- 可观测性/oracle：send hook 与 transaction status update；价值高，可检测 final-response 丢失或状态错误。
- 注意/审核：PENDING；proxy mode 下需区分为 upstream UAS 选择的 final response 与 downstream branch final。

## SIP-KAM-006：non-2xx Completed 后，transaction 在 ACK 或 Timer H 到期前不得被销毁

- 类别/角色：INVITE Timer H/lifetime；UAS/server transaction
- RFC 来源：[RFC3261 17.2.1 and Table 4](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine timer
- 证据摘要：INVITE server transaction 在 Completed 状态的 Timer H 为 64*T1；ACK 或 timeout 决定 termination。
- 时间界限：`32000` ms；来源：64*T1，使用 RFC 默认 T1=500 ms
- MightyPPL：`G* (invite_tx_completed_non2xx -> G [0,32000) (!invite_tx_terminated_without_ack_or_timer_h))`
- 数学 MITL：`G(invite_tx_completed_non2xx -> G_[0,32000ms) not early_terminated)`
- AP：`invite_tx_completed_non2xx, invite_tx_terminated_without_ack_or_timer_h`
- 关联键：同一个 INVITE server transaction
- 主 hook：HK_SEND_PR_BUFFER, HK_PUT_ON_WAIT
- 辅助 hook：HK_TIMER_ARM, HK_TIMER_STOP
- 正例 timed word：`time,props ; 0,{invite_tx_completed_non2xx} ; 1,{}`
- 反例 timed word：`time,props ; 0,{invite_tx_completed_non2xx} ; 1,{invite_tx_terminated_without_ack_or_timer_h}`
- 可观测性/oracle：白盒 wait/timer hook；单靠 pcap 无法证明 early destroy；价值中，可检测过早丢弃状态。
- 注意/审核：ProfuzzBench patch 关闭 timer process；callback expiry 需要 reference build，但 early destroy 仍可观察。测试 watchdog 是否应在 32s 关闭 trace，还是未完成 obligation 应为 UNKNOWN？

## SIP-KAM-007：匹配 Completed INVITE server transaction 的 ACK 使其进入 Confirmed，并停止 response retransmission

- 类别/角色：INVITE ACK handling；UAS/server transaction
- RFC 来源：[RFC3261 17.2.1](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1) — MUST/state-machine
- 证据摘要：在 Completed 中收到 ACK 时，server transaction 转入 Confirmed。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (invite_completed_rx_ack -> F [0,2] invite_tx_confirmed_ack_absorbed)`
- 数学 MITL：`G(invite_completed_rx_ack -> F_[0,2ms] invite_tx_confirmed_ack_absorbed)`
- AP：`invite_completed_rx_ack, invite_tx_confirmed_ack_absorbed`
- 关联键：同一个 INVITE transaction；ACK 匹配 INVITE method exception
- 主 hook：HK_TX_LOOKUP, HK_TIMER_STOP
- 辅助 hook：HK_T_REPLY_MATCHING
- 正例 timed word：`time,props ; 0,{invite_completed_rx_ack} ; 1,{invite_tx_confirmed_ack_absorbed}`
- 反例 timed word：`time,props ; 0,{invite_completed_rx_ack} ; 3,{invite_tx_confirmed_ack_absorbed}`
- 可观测性/oracle：白盒 lookup/timer-stop hook；价值高，可检测 ACK 误分类。
- 注意/审核：PENDING；需要为 2xx ACK 单独设置 AP，因为 RFC6026 Accepted ACK 是向上传递而不是被吸收。

## SIP-KAM-008：根据 RFC6026，INVITE 的 2xx response 使 server transaction 转入 Accepted 并 arm Timer L

- 类别/角色：INVITE 2xx Accepted；UAS/server transaction
- RFC 来源：[RFC6026 7.1 and 8.7](https://www.rfc-editor.org/rfc/rfc6026.html#section-7.1) — MUST/update state-machine
- 证据摘要：该更新增加 Accepted 与 Timer L；Proceeding 中的 2xx 使 transaction 转入 Accepted，并且 Timer L 为 64*T1。
- 时间界限：`2` ms；来源：transition 使用 adapter microstep expansion；Timer L 值为 64*T1=32000 ms
- MightyPPL：`G* (invite_2xx_response_from_tu -> F [0,2] timer_l_64t1_armed)`
- 数学 MITL：`G(invite_2xx_response_from_tu -> F_[0,2ms] timer_l_64t1_armed)`
- AP：`invite_2xx_response_from_tu, timer_l_64t1_armed`
- 关联键：同一个 INVITE server transaction
- 主 hook：HK_RELAY_REPLY, HK_TIMER_ARM
- 辅助 hook：HK_SEND_PR_BUFFER
- 正例 timed word：`time,props ; 0,{invite_2xx_response_from_tu} ; 1,{timer_l_64t1_armed}`
- 反例 timed word：`time,props ; 0,{invite_2xx_response_from_tu} ; 3,{timer_l_64t1_armed}`
- 可观测性/oracle：白盒 timer arm 与 response hook；价值中/高，可作为 RFC6026 conformance oracle。
- 注意/审核：可能需要 reference profile 与人工审计，因为 Kamailio 可能不直接用 RFC 名称编码 Accepted。能否观察明确的 Timer L 等价物，还是必须把它放入 excluded/extended property？

## SIP-KAM-009：Accepted 中的重传 INVITE 被 transaction 吸收，不再重新传给 TU

- 类别/角色：RFC6026 retransmitted INVITE in Accepted；UAS/server transaction
- RFC 来源：[RFC6026 8.7](https://www.rfc-editor.org/rfc/rfc6026.html#section-8.7) — MUST/update state-machine
- 证据摘要：Accepted 状态会吸收原始 INVITE 的重传，并且不把它传给 TU。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (accepted_rx_invite_retransmission -> G [0,2] (!invite_retransmission_passed_to_tu))`
- 数学 MITL：`G(accepted_rx_invite_retransmission -> G_[0,2ms] not passed_to_tu)`
- AP：`accepted_rx_invite_retransmission, invite_retransmission_passed_to_tu`
- 关联键：同一个 INVITE branch/sent-by/method transaction key
- 主 hook：HK_TX_LOOKUP, HK_TX_NEW
- 辅助 hook：HK_RETRANSMIT_REPLY
- 正例 timed word：`time,props ; 0,{accepted_rx_invite_retransmission} ; 1,{}`
- 反例 timed word：`time,props ; 0,{accepted_rx_invite_retransmission} ; 1,{invite_retransmission_passed_to_tu}`
- 可观测性/oracle：白盒 lookup 加 route/TU 边界 hook；价值中，可检测重复 TU delivery。
- 注意/审核：需要 route-boundary hook 证明未投递；如果 hook 丢失，单纯缺少事件只能判为 UNKNOWN。最小扰动下，TU delivery hook 应放在 Kamailio route execution 的哪个位置？

## SIP-KAM-010：Accepted 中的 ACK 直接传给 TU，而不是被 transaction layer 吸收

- 类别/角色：RFC6026 ACK in Accepted；UAS/server transaction
- RFC 来源：[RFC6026 8.7](https://www.rfc-editor.org/rfc/rfc6026.html#section-8.7) — MUST/update state-machine
- 证据摘要：匹配 Accepted transaction 的 ACK request 会直接传给 TU。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (accepted_rx_ack -> F [0,2] ack_passed_to_tu)`
- 数学 MITL：`G(accepted_rx_ack -> F_[0,2ms] ack_passed_to_tu)`
- AP：`accepted_rx_ack, ack_passed_to_tu`
- 关联键：同一个 INVITE accepted transaction 与 ACK matching key
- 主 hook：HK_TX_LOOKUP, HK_RX_PARSE_OK
- 辅助 hook：HK_TIMER_STOP
- 正例 timed word：`time,props ; 0,{accepted_rx_ack} ; 1,{ack_passed_to_tu}`
- 反例 timed word：`time,props ; 0,{accepted_rx_ack} ; 3,{ack_passed_to_tu}`
- 可观测性/oracle：白盒 transaction lookup 加 route/TU hook；价值中，可检测错误 ACK absorption。
- 注意/审核：需要人工确认 Kamailio 中代表 TU delivery 的 route callback。ACK-to-TU 应被视作 route-level event，还是 tm callback event？

## SIP-KAM-011：新建 non-INVITE server transaction 进入 Trying，并把请求向上传递

- 类别/角色：non-INVITE server transaction；UAS/server transaction
- RFC 来源：[RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- 证据摘要：对 non-INVITE 请求，server transaction 从 Trying 状态开始，并把请求传给 TU。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (server_rx_noninvite_new_tx -> F [0,2] noninvite_tx_trying)`
- 数学 MITL：`G(server_rx_noninvite_new_tx -> F_[0,2ms] noninvite_tx_trying)`
- AP：`server_rx_noninvite_new_tx, noninvite_tx_trying`
- 关联键：Call-ID + CSeq + top Via branch/sent-by
- 主 hook：HK_RX_PARSE_OK, HK_TX_NEW
- 辅助 hook：HK_TX_LOOKUP
- 正例 timed word：`time,props ; 0,{server_rx_noninvite_new_tx} ; 1,{noninvite_tx_trying}`
- 反例 timed word：`time,props ; 0,{server_rx_noninvite_new_tx} ; 3,{noninvite_tx_trying}`
- 可观测性/oracle：白盒 transaction creation；价值高，覆盖 OPTIONS/BYE/CANCEL 类 setup。
- 注意/审核：PENDING；CANCEL 有特殊处理；测试原事务语义时，该性质应排除 CANCEL。

## SIP-KAM-012：Trying 中的 non-INVITE 重传被丢弃，不会再次传给 TU

- 类别/角色：non-INVITE retransmission discard；UAS/server transaction
- RFC 来源：[RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- 证据摘要：Trying 状态中，non-INVITE 请求的重传会被丢弃。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (noninvite_retransmission_in_trying -> G [0,2] (!noninvite_retransmission_passed_to_tu))`
- 数学 MITL：`G(noninvite_retransmission_in_trying -> G_[0,2ms] not passed_to_tu)`
- AP：`noninvite_retransmission_in_trying, noninvite_retransmission_passed_to_tu`
- 关联键：同一个 non-INVITE transaction key
- 主 hook：HK_TX_LOOKUP, HK_TIMER_STOP
- 辅助 hook：HK_RX_PARSE_OK
- 正例 timed word：`time,props ; 0,{noninvite_retransmission_in_trying} ; 1,{}`
- 反例 timed word：`time,props ; 0,{noninvite_retransmission_in_trying} ; 1,{noninvite_retransmission_passed_to_tu}`
- 可观测性/oracle：白盒 lookup 加 route/TU 边界 hook；价值中/高，可检测重复 request processing。
- 注意/审核：PENDING；需要 route/TU delivery hook，避免在事件丢失时把缺失事件误判为未投递。

## SIP-KAM-013：non-INVITE transaction 的 provisional response 使其进入 Proceeding 并发送响应

- 类别/角色：non-INVITE provisional response；UAS/server transaction
- RFC 来源：[RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- 证据摘要：如果 provisional response 被传给 non-INVITE server transaction，它进入 Proceeding 并把 response 传给 transport。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (noninvite_tu_provisional -> F [0,2] noninvite_tx_proceeding_response_sent)`
- 数学 MITL：`G(noninvite_tu_provisional -> F_[0,2ms] noninvite_tx_proceeding_response_sent)`
- AP：`noninvite_tu_provisional, noninvite_tx_proceeding_response_sent`
- 关联键：同一个 non-INVITE transaction
- 主 hook：HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- 辅助 hook：HK_TX_LOOKUP
- 正例 timed word：`time,props ; 0,{noninvite_tu_provisional} ; 1,{noninvite_tx_proceeding_response_sent}`
- 反例 timed word：`time,props ; 0,{noninvite_tu_provisional} ; 3,{noninvite_tx_proceeding_response_sent}`
- 可观测性/oracle：send hook 加 status class；价值中，适合 OPTIONS/BYE provisional 边界情况。
- 注意/审核：PENDING；RFC 说 UAS 通常 SHOULD NOT 为 non-INVITE 发送 provisional；该性质只适用于 TU 确实发出 provisional 的情况。

## SIP-KAM-014：non-INVITE server transaction 的 final response 使其进入 Completed 并发送响应

- 类别/角色：non-INVITE final response；UAS/server transaction
- RFC 来源：[RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- 证据摘要：200-699 final response 使 transaction 进入 Completed，并传给 transport。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (noninvite_tu_final_response -> F [0,2] noninvite_tx_completed_final_sent)`
- 数学 MITL：`G(noninvite_tu_final_response -> F_[0,2ms] noninvite_tx_completed_final_sent)`
- AP：`noninvite_tu_final_response, noninvite_tx_completed_final_sent`
- 关联键：同一个 non-INVITE transaction
- 主 hook：HK_RELAY_REPLY, HK_SEND_PR_BUFFER
- 辅助 hook：HK_PUT_ON_WAIT
- 正例 timed word：`time,props ; 0,{noninvite_tu_final_response} ; 1,{noninvite_tx_completed_final_sent}`
- 反例 timed word：`time,props ; 0,{noninvite_tu_final_response} ; 3,{noninvite_tx_completed_final_sent}`
- 可观测性/oracle：send hook 加 wait-state hook；价值高，是核心 non-INVITE response oracle。
- 注意/审核：PENDING；需要区分 server-side final response 与被选中转发的 proxied branch final。

## SIP-KAM-015：Completed 中重传 non-INVITE request 时，重传已保存的 final response

- 类别/角色：non-INVITE retransmission in Completed；UAS/server transaction
- RFC 来源：[RFC3261 17.2.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2) — MUST/state-machine
- 证据摘要：在 Completed 中，重传请求会收到此前发送过的 final response。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (noninvite_retransmission_in_completed -> F [0,2] noninvite_final_response_retransmitted)`
- 数学 MITL：`G(noninvite_retransmission_in_completed -> F_[0,2ms] noninvite_final_response_retransmitted)`
- AP：`noninvite_retransmission_in_completed, noninvite_final_response_retransmitted`
- 关联键：同一个 non-INVITE transaction key
- 主 hook：HK_TX_LOOKUP, HK_RETRANSMIT_REPLY
- 辅助 hook：HK_SEND_PR_BUFFER
- 正例 timed word：`time,props ; 0,{noninvite_retransmission_in_completed} ; 1,{noninvite_final_response_retransmitted}`
- 反例 timed word：`time,props ; 0,{noninvite_retransmission_in_completed} ; 3,{noninvite_final_response_retransmitted}`
- 可观测性/oracle：lookup 与 send retransmission hook；价值高，可捕获 response cache/retransmission bug。
- 注意/审核：PENDING；长 trace 中必须把 Timer J expiry 作为合法 supersession 处理。

## SIP-KAM-016：带 RFC3261 magic-cookie branch 且 sent-by/method 匹配的请求映射到已有 transaction

- 类别/角色：transaction matching；UAS/proxy transaction layer
- RFC 来源：[RFC3261 17.2.3](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.3) — MUST/matching rule
- 证据摘要：存在 magic-cookie branch 时，匹配使用 branch、sent-by 和 method；ACK 匹配 INVITE 是例外。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (request_with_magic_cookie_matches_existing_tx -> F [0,2] tx_lookup_existing_match)`
- 数学 MITL：`G(magic_cookie_match_candidate -> F_[0,2ms] tx_lookup_existing_match)`
- AP：`request_with_magic_cookie_matches_existing_tx, tx_lookup_existing_match`
- 关联键：top Via branch/sent-by + CSeq method exception + transaction bucket/hash
- 主 hook：HK_TX_LOOKUP
- 辅助 hook：HK_RX_PARSE_OK
- 正例 timed word：`time,props ; 0,{request_with_magic_cookie_matches_existing_tx} ; 1,{tx_lookup_existing_match}`
- 反例 timed word：`time,props ; 0,{request_with_magic_cookie_matches_existing_tx} ; 3,{tx_lookup_existing_match}`
- 可观测性/oracle：白盒 lookup；pcap 可提供候选字段；价值高，可防止 transaction-key 爆炸/歧义。
- 注意/审核：PENDING；AP 名称不包含动态 branch 值；这些字段只存在于 correlation metadata 中。

## SIP-KAM-017：匹配已有 transaction 的 CANCEL 自身收到 200 OK

- 类别/角色：CANCEL matched response；UAS/proxy transaction layer
- RFC 来源：[RFC3261 9.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-9.2) — SHOULD/MUST behavior
- 证据摘要：如果存在匹配 transaction，UAS 首先处理 CANCEL，然后用 200 OK 响应该 CANCEL。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (cancel_matches_original_transaction -> F [0,2] cancel_tx_200_ok)`
- 数学 MITL：`G(cancel_matches_original_transaction -> F_[0,2ms] cancel_tx_200_ok)`
- AP：`cancel_matches_original_transaction, cancel_tx_200_ok`
- 关联键：CANCEL transaction + matched original transaction
- 主 hook：HK_FORWARD_NONACK, HK_E2E_CANCEL, HK_SEND_PR_BUFFER
- 辅助 hook：HK_TX_LOOKUP
- 正例 timed word：`time,props ; 0,{cancel_matches_original_transaction} ; 1,{cancel_tx_200_ok}`
- 反例 timed word：`time,props ; 0,{cancel_matches_original_transaction} ; 3,{cancel_tx_200_ok}`
- 可观测性/oracle：白盒 cancel path 加 send hook；价值高，是明确的 SIP CANCEL oracle。
- 注意/审核：PENDING；需要把它与原 INVITE 的 487 分开；二者可能在同一回调中发生。

## SIP-KAM-018：final response 之前收到匹配 INVITE 的 CANCEL 时，原 INVITE 收到 487

- 类别/角色：CANCEL effect on INVITE；UAS/proxy transaction layer
- RFC 来源：[RFC3261 9.2](https://www.rfc-editor.org/rfc/rfc3261.html#section-9.2) — SHOULD behavior
- 证据摘要：如果 INVITE 尚未发送 final response，UAS 行为 SHOULD 生成 487 response。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (cancel_matches_invite_before_final -> F [0,2] original_invite_tx_487)`
- 数学 MITL：`G(cancel_matches_invite_before_final -> F_[0,2ms] original_invite_tx_487)`
- AP：`cancel_matches_invite_before_final, original_invite_tx_487`
- 关联键：CANCEL transaction + original INVITE transaction
- 主 hook：HK_FORWARD_NONACK, HK_E2E_CANCEL, HK_SEND_PR_BUFFER
- 辅助 hook：HK_CANCEL_BRANCH
- 正例 timed word：`time,props ; 0,{cancel_matches_invite_before_final} ; 1,{original_invite_tx_487}`
- 反例 timed word：`time,props ; 0,{cancel_matches_invite_before_final} ; 3,{original_invite_tx_487}`
- 可观测性/oracle：白盒 cancel effect 与 send hook；可用 pcap 交叉检查；价值高，是协议可见违反。
- 注意/审核：PENDING；如果 downstream branch 已经发送 final response，则 correlation state 必须抑制该 obligation。

## SIP-KAM-019：stateful proxy 只能在 provisional response 使 branch 可取消后，才生成 branch CANCEL

- 类别/角色：proxy branch CANCEL gating；stateful proxy/client transaction
- RFC 来源：[RFC3261 9.1 and 16.10](https://www.rfc-editor.org/rfc/rfc3261.html#section-16.10) — MUST/MAY constrained by RFC9.1/16.10
- 证据摘要：stateful proxy 会取消 pending client transactions，但受 caller-side CANCEL 规则约束：必须先收到 provisional response。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (branch_cancel_requested_without_provisional -> G [0,2] (!branch_cancel_sent))`
- 数学 MITL：`G(branch_cancel_requested_without_provisional -> G_[0,2ms] not branch_cancel_sent)`
- AP：`branch_cancel_requested_without_provisional, branch_cancel_sent`
- 关联键：transaction correlation 后派生的 client branch id
- 主 hook：HK_CANCEL_BRANCH, HK_E2E_CANCEL
- 辅助 hook：HK_REPLY_RECEIVED
- 正例 timed word：`time,props ; 0,{branch_cancel_requested_without_provisional} ; 1,{}`
- 反例 timed word：`time,props ; 0,{branch_cancel_requested_without_provisional} ; 1,{branch_cancel_sent}`
- 可观测性/oracle：白盒 branch state 与 send hook；价值中/高，可避免非法 early downstream CANCEL。
- 注意/审核：人工审核必须分类 force/local-cancel 等有意偏离路径。强制 local CANCEL 路径应排除在主性质之外，还是建模为 legal supersession？

## SIP-KAM-020：stateful proxy 不得立即向上游转发 100 Trying response

- 类别/角色：proxy 100 Trying forwarding；stateful proxy
- RFC 来源：[RFC3261 16.7](https://www.rfc-editor.org/rfc/rfc3261.html#section-16.7) — MUST NOT/proxy response processing
- 证据摘要：stateful proxy 会转发 provisional response，但 100 Trying 例外；100 Trying 不会被立即转发。
- 时间界限：`2` ms；来源：adapter microstep expansion
- MightyPPL：`G* (proxy_rx_100_trying_response -> G [0,2] (!proxy_forward_100_trying))`
- 数学 MITL：`G(proxy_rx_100_trying_response -> G_[0,2ms] not proxy_forward_100_trying)`
- AP：`proxy_rx_100_trying_response, proxy_forward_100_trying`
- 关联键：匹配到 proxy response context 的 response branch
- 主 hook：HK_REPLY_RECEIVED, HK_RELAY_REPLY
- 辅助 hook：HK_SEND_PR_BUFFER
- 正例 timed word：`time,props ; 0,{proxy_rx_100_trying_response} ; 1,{}`
- 反例 timed word：`time,props ; 0,{proxy_rx_100_trying_response} ; 1,{proxy_forward_100_trying}`
- 可观测性/oracle：upstream response hook 加实际 send hook；价值高，是外部可见的 proxy violation。
- 注意/审核：PENDING；需要 send-direction metadata，避免把 downstream 100 generation 与 upstream forwarding 混淆。
