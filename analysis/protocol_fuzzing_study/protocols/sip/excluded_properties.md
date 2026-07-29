# SIP 排除与待修候选

## 研究阶段排除：_staging/root_sip_extensions/sip/excluded.md

# SIP 审计排除项与已知偏差

## 从 MITL 计时目录去重的三条性质

- `SIP-TX-02`：拒绝“从初始 INVITE 发送起恰好 500 ms 内完成首次重传”的独立计时性质。RFC 只规定 Timer A callback 触发传输动作，没有给出 callback/send 的非 punctual 调度延迟界；它与 `SIP-TX-01` 的 Timer-A deadline 重复。仅保留无时间断言 `timer_a_callback -> invite_retransmit_requested`。
- `SIP-TX-08`：同理拒绝把 Timer E callback 动作改写成从初始 non-INVITE 发送起的精确动作 deadline；与 `SIP-TX-07` 重复。仅保留 `timer_e_callback -> noninvite_retransmit_requested`。
- `SIP-TX-14`：同理拒绝把 Timer G callback 后的最终响应重传改写成从 Completed entry 起的精确动作 deadline；与 `SIP-TX-13` 重复。仅保留 `timer_g_callback -> final_response_retransmit_requested`。

三条 replacement assertion 都在 `audit_overrides.json` 中具有独立 AP 定义和 AP-specific 固定源码映射，但不计入 MITL 性质数量。

## 固定实现的已知偏差 profile

- `SIP-TX-20 / Kamailio Timer C`：固定 commit 的 `fr_inv_timeout=120000 ms`，`max_inv_lifetime=180000 ms`；RFC 3261 要求严格大于 180000 ms。规范性质保留为 strict-bound oracle，默认 profile 标记 `EXPECTED_VIOLATION`，不得把等于边界解释为合规。
- `SIP-TX-22 / Doubango Timer X`：初始 schedule 后先将 500 左移到 1000，第一次 callback 又先左移再 schedule，因此下一实际间隔是 2000 ms，而非规范期望的 1000 ms。保留 2000-ms source-realistic 反例。
- `SIP-TX-23 / Doubango Timer X cap`：callback 中只有 `timeout <<= 1`，没有 `min(...,T2)`；达到 T2 后仍可能出现 8000 ms。每个 post-cap generation 必须单独实例化 4000-ms monitor。
- `SIP-TX-25 / Doubango Timer L`：FSM 存在 `Any transport error -> Terminated`。服务侧 RFC 6026 retention 性质不允许静默把该路径当作例外；所有 Terminated 路径都必须发 AP，提前传输错误 trace 应判违反。

这些条目是固定源码的研究 oracle，不是已运行 SUT 后的动态合规结论。

## 其他未纳入候选

- `RFC6026-ACCEPTED-ABSORB`：Accepted 状态吸收重传 INVITE 是真实 MUST，但没有数值时间边界；若强行表达“同一时刻不上传 TU”会依赖 microstep/punctual 语义，留在事件一致性断言。
- `RFC6026-STRAY-RESPONSE`：不转发无匹配事务的响应更适合无时间协议状态断言。
- `RFC4320-NICT-100`：100 Trying 延迟规则有时序价值，但当前固定 Doubango 版本没有已确认的匹配调度控制流，保留为 `NO_FIXED_SOURCE_MAP`。

## 审核门

`FIXED_AFTER_AUDIT` 只表示审计问题已落实为 staging override，不表示人工批准。所有 23 条修复性质和 3 条排除决定仍为 `PENDING`；未签字前不得进入论文最终主张或 fuzzer 实现需求。

## 自动质量门拒绝

- `SIP-TX-02` Timer A causes the first INVITE retransmission: `AP_WITHOUT_SOURCE_MAPPING:invite_retransmitted,invite_transaction_stopped,udp_invite_sent, INDEPENDENT_AUDIT_REJECT, PRIMARY_SOURCE_APS_MISSING_OR_EMPTY, UNKNOWN_OR_UNAPPROVED_AUDIT_STATUS:REJECT`
- `SIP-TX-08` Timer E causes the first non-INVITE retransmission: `AP_WITHOUT_SOURCE_MAPPING:noninvite_final_response_received,noninvite_retransmitted,udp_noninvite_sent, INDEPENDENT_AUDIT_REJECT, PRIMARY_SOURCE_APS_MISSING_OR_EMPTY, UNKNOWN_OR_UNAPPROVED_AUDIT_STATUS:REJECT`
- `SIP-TX-14` Timer G causes the first final-response retransmission: `AP_WITHOUT_SOURCE_MAPPING:ack_received,final_response_retransmitted,udp_invite_server_completed, INDEPENDENT_AUDIT_REJECT, PRIMARY_SOURCE_APS_MISSING_OR_EMPTY, UNKNOWN_OR_UNAPPROVED_AUDIT_STATUS:REJECT`
