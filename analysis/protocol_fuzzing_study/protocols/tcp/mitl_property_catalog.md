# TCP MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：9
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## TCP-ACK-01 — Delayed ACK remains below 500 ms

- 性质：对需要确认且采用 delayed ACK 的报文段，ACK 延迟必须严格小于 500 ms。
- 规范：[RFC 9293 RFC 9293 §3.8.6.3](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.3)；强度 `MUST`；时间 `500 (strict upper bound) ms`（`NORMATIVE_BOUND`）。
- 规范短摘录：“the delay MUST be less than 0.5 seconds”
- 数学 MITL：`G (tcp_delayed_ack_obligation_started -> F [0,500) (tcp_ack_sent))`
- MightyPPL（finite weak outer global）：`G* (tcp_delayed_ack_obligation_started -> F [0,500) (tcp_ack_sent))`
- AP：`tcp_delayed_ack_obligation_started, tcp_ack_sent`
- AP 定义：{"tcp_delayed_ack_obligation_started": "A processed segment requires ACK and enters the delayed-ACK rather than immediate-ACK branch.", "tcp_ack_sent": "An ACK covering the correlated receive sequence is handed to IP output."}
- Correlation：socket cookie + receive-direction sequence interval
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `net/ipv4/tcp_output.c:4409-4463`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4409-L4463)；符号 `tcp_send_delayed_ack`。
- 主源码映射 AP：`["tcp_delayed_ack_obligation_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "pure ACK construction and transmission handoff", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_output.c", "symbol": "__tcp_send_ack", "lines": "4466-4506", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4466-L4506", "atomic_propositions": ["tcp_ack_sent"]}]`
- Hook：Emit the trigger immediately before sk_reset_timer; emit ACK after tcp_send_ack/output using the same socket cookie.
- 正例 timed word：`[{"time": 0, "props": ["tcp_delayed_ack_obligation_started"]}, {"time": 499, "props": ["tcp_ack_sent"]}, {"time": 501, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_delayed_ack_obligation_started"]}, {"time": 500, "props": ["tcp_ack_sent"]}, {"time": 501, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["tcp_delayed_ack_obligation_started"]}, {"time": 501, "props": []}]}`
- 独立审计：`APPROVE`；Independent standard/formula/source audit approved this card without a semantic correction.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The Linux default cap is normally 200 ms, which is stricter; 500 ms remains the protocol oracle.

## TCP-KA-01 — Default keep-alive idle period is at least two hours

- 性质：应用显式启用 keep-alive 且使用默认参数时，空闲连接在两小时内不得发送 keep-alive probe。
- 规范：[RFC 9293 RFC 9293 §3.8.4](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.4)；强度 `MUST`；时间 `7200000 ms`（`NORMATIVE_DEFAULT_AND_IMPLEMENTATION_DEFAULT`）。
- 规范短摘录：“MUST default to no less than two hours”
- 数学 MITL：`G (tcp_default_keepalive_enabled_on_idle_connection -> G [0,7200000) (!tcp_keepalive_probe_sent))`
- MightyPPL（finite weak outer global）：`G* (tcp_default_keepalive_enabled_on_idle_connection -> G [0,7200000) (!tcp_keepalive_probe_sent))`
- AP：`tcp_default_keepalive_enabled_on_idle_connection, tcp_keepalive_probe_sent`
- AP 定义：{"tcp_default_keepalive_enabled_on_idle_connection": "SO_KEEPALIVE becomes active with no per-socket keepidle override and no outstanding data.", "tcp_keepalive_probe_sent": "tcp_write_wakeup emits a keep-alive probe for the correlated socket."}
- Correlation：network namespace + socket cookie
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `include/net/tcp.h:175-180`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L175-L180)；符号 `TCP_KEEPALIVE_TIME`。
- 主源码映射 AP：`["tcp_default_keepalive_enabled_on_idle_connection"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "SO_KEEPALIVE enable and default timer arm", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_timer.c", "symbol": "tcp_set_keepalive", "lines": "768-777", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L768-L777", "atomic_propositions": ["tcp_default_keepalive_enabled_on_idle_connection"]}, {"role": "keep-alive expiry and probe send attempt", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_timer.c", "symbol": "tcp_keepalive_timer", "lines": "779-866", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L779-L866", "atomic_propositions": ["tcp_keepalive_probe_sent"]}]`
- Hook：Record enablement after tcp_set_keepalive arms the timer; emit probe only after tcp_write_wakeup succeeds.
- 正例 timed word：`[{"time": 0, "props": ["tcp_default_keepalive_enabled_on_idle_connection"]}, {"time": 7200000, "props": ["tcp_keepalive_probe_sent"]}, {"time": 7200001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_default_keepalive_enabled_on_idle_connection"]}, {"time": 7199999, "props": ["tcp_keepalive_probe_sent"]}, {"time": 7200001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`APPROVE`；Independent standard/formula/source audit approved this card without a semantic correction.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Keep-alive is optional and disabled unless the application requests it; virtual time is needed for practical fuzzing.

## TCP-R2-01 — Data retransmission R2 is at least 100 seconds

- 性质：已建立连接因同一数据持续重传进入默认 R2 计时时，在 100 秒前不应因 excessive retransmission 关闭。
- 规范：[RFC 9293 RFC 9293 §3.8.3](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.3)；强度 `SHOULD`；时间 `100000 ms`（`NORMATIVE_MINIMUM`）。
- 规范短摘录：“The value of R2 SHOULD correspond to at least 100 seconds”
- 数学 MITL：`G (tcp_data_r2_episode_started -> G [0,100000) (!tcp_closed_by_data_r2_expiry))`
- MightyPPL（finite weak outer global）：`G* (tcp_data_r2_episode_started -> G [0,100000) (!tcp_closed_by_data_r2_expiry))`
- AP：`tcp_data_r2_episode_started, tcp_closed_by_data_r2_expiry`
- AP 定义：{"tcp_data_r2_episode_started": "First retransmission timestamp is established for data in an established connection using default R2 policy.", "tcp_closed_by_data_r2_expiry": "tcp_write_timeout reports expired and tcp_write_err closes specifically because the data R2 threshold is reached."}
- Correlation：network namespace + socket cookie + retransmission episode
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `net/ipv4/tcp_timer.c:242-305`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L242-L305)；符号 `tcp_write_timeout`。
- 主源码映射 AP：`["tcp_closed_by_data_r2_expiry"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "first attempted data retransmission timestamp", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_output.c", "symbol": "tcp_retransmit_skb", "lines": "3695-3717", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L3695-L3717", "atomic_propositions": ["tcp_data_r2_episode_started"]}]`
- Hook：Emit start when retrans_stamp is first set; emit expiry immediately before tcp_write_err with state outside SYN_SENT/SYN_RECV and expired=true.
- 正例 timed word：`[{"time": 0, "props": ["tcp_data_r2_episode_started"]}, {"time": 100000, "props": ["tcp_closed_by_data_r2_expiry"]}, {"time": 100001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_data_r2_episode_started"]}, {"time": 99999, "props": ["tcp_closed_by_data_r2_expiry"]}, {"time": 100001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`APPROVE`；Independent standard/formula/source audit approved this card without a semantic correction.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：An application-selected TCP_USER_TIMEOUT, external RST/ICMP, resource pressure or application close is not `tcp_closed_by_data_r2_expiry`.

## TCP-RTO-01 — Linux RFC-recommended initial RTO profile arms 1000 ms

- 性质：Linux 未采用 3 秒 fallback、thin-stream 或自定义策略且实际按 1000 ms arm 初始 RTO 后，该 timer generation 不得提前到期，并须在 1000 ms 到期或被关联事件替换/取消。
- 规范：[RFC 6298 RFC 6298 §2.1](https://www.rfc-editor.org/rfc/rfc6298.html#section-2.1)；强度 `SHOULD`；时间 `1000 ms`（`NORMATIVE_RECOMMENDED_DEFAULT`）。
- 规范短摘录：“the sender SHOULD set RTO <- 1 second”
- 数学 MITL：`G (tcp_initial_rto_armed_1000ms_profile -> (G [0,1000) (!tcp_initial_rto_deadline_reached) && F [0,1000] (tcp_initial_rto_deadline_reached || tcp_initial_rto_superseded)))`
- MightyPPL（finite weak outer global）：`G* (tcp_initial_rto_armed_1000ms_profile -> (G [0,1000) (!tcp_initial_rto_deadline_reached) && F [0,1000] (tcp_initial_rto_deadline_reached || tcp_initial_rto_superseded)))`
- AP：`tcp_initial_rto_armed_1000ms_profile, tcp_initial_rto_deadline_reached, tcp_initial_rto_superseded`
- AP 定义：{"tcp_initial_rto_armed_1000ms_profile": "ICSK_TIME_RETRANS is actually armed with a 1000 ms absolute deadline and fallback/override branches are false.", "tcp_initial_rto_deadline_reached": "The absolute deadline of that exact retransmission-timer generation is reached.", "tcp_initial_rto_superseded": "A correlated ACK, loss-state change, or explicit timer restart/cancel replaces that exact timer generation."}
- Correlation：network namespace + socket cookie + 4-tuple; sequence numbers correlate ACKs but are fields, not AP names
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `include/net/tcp.h:160-173`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L160-L173)；符号 `TCP_TIMEOUT_INIT`。
- 主源码映射 AP：`["tcp_initial_rto_armed_1000ms_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "initial RTO timer arm after active-open send", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_output.c", "symbol": "tcp_connect", "lines": "4393-4398", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4393-L4398", "atomic_propositions": ["tcp_initial_rto_armed_1000ms_profile"]}, {"role": "retransmission timer deadline dispatch", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_timer.c", "symbol": "tcp_write_timer_handler", "lines": "695-728", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L695-L728", "atomic_propositions": ["tcp_initial_rto_deadline_reached"]}, {"role": "ACK-driven retransmission timer cancellation or replacement", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_input.c", "symbol": "tcp_rearm_rto", "lines": "3524-3550", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_input.c#L3524-L3550", "atomic_propositions": ["tcp_initial_rto_superseded"]}]`
- Hook：Emit trigger from the timer-arm hook with deadline and generation; emit deadline independently of callback dispatch; emit superseded only when that generation is cancelled/rearmed.
- 正例 timed word：`[{"time": 0, "props": ["tcp_initial_rto_armed_1000ms_profile"]}, {"time": 1000, "props": ["tcp_initial_rto_deadline_reached"]}, {"time": 1001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_initial_rto_armed_1000ms_profile"]}, {"time": 999, "props": ["tcp_initial_rto_deadline_reached"]}, {"time": 1001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["tcp_initial_rto_armed_1000ms_profile"]}, {"time": 1001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Trigger now binds the actual 1000 ms arm generation, excludes fallback, observes deadline rather than callback, and has early plus missing negatives.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Linux can switch to the RFC 6298 3-second fallback after SYN/SYN-ACK loss; that branch needs a separate profile and is excluded here.

## TCP-RTO-03 — RTO backs off by two after expiry

- 性质：正常指数退避分支实际按 2000 ms 重设第二个 RTO generation 后，不得提前到期，并须在 2000 ms 到期或被有效 ACK/重设取消。
- 规范：[RFC 6298 RFC 6298 §5.5-5.6](https://www.rfc-editor.org/rfc/rfc6298.html#section-5)；强度 `MUST`；时间 `2000 ms`（`NORMATIVE_DERIVED`）。
- 规范短摘录：“The host MUST set RTO <- RTO * 2”
- 数学 MITL：`G (tcp_second_rto_armed_2000ms_normal_backoff -> (G [0,2000) (!tcp_second_rto_deadline_reached) && F [0,2000] (tcp_second_rto_deadline_reached || tcp_second_rto_superseded)))`
- MightyPPL（finite weak outer global）：`G* (tcp_second_rto_armed_2000ms_normal_backoff -> (G [0,2000) (!tcp_second_rto_deadline_reached) && F [0,2000] (tcp_second_rto_deadline_reached || tcp_second_rto_superseded)))`
- AP：`tcp_second_rto_armed_2000ms_normal_backoff, tcp_second_rto_deadline_reached, tcp_second_rto_superseded`
- AP 定义：{"tcp_second_rto_armed_2000ms_normal_backoff": "The normal non-linear, non-thin-stream branch doubles 1000 ms to 2000 ms and arms a new timer generation.", "tcp_second_rto_deadline_reached": "The absolute deadline of that exact 2000 ms generation is reached.", "tcp_second_rto_superseded": "A qualifying ACK or timer restart/cancel replaces that exact generation."}
- Correlation：socket cookie + retransmission generation counter
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `net/ipv4/tcp_timer.c:657-685`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L657-L685)；符号 `tcp_retransmit_timer`。
- 主源码映射 AP：`["tcp_second_rto_armed_2000ms_normal_backoff"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "retransmission timer deadline dispatch", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_timer.c", "symbol": "tcp_write_timer_handler", "lines": "695-728", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L695-L728", "atomic_propositions": ["tcp_second_rto_deadline_reached"]}, {"role": "ACK-driven retransmission timer cancellation or replacement", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_input.c", "symbol": "tcp_rearm_rto", "lines": "3524-3550", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_input.c#L3524-L3550", "atomic_propositions": ["tcp_second_rto_superseded"]}]`
- Hook：After icsk_rto is doubled and tcp_reset_xmit_timer succeeds, emit the trigger with old/new RTO fields.
- 正例 timed word：`[{"time": 0, "props": ["tcp_second_rto_armed_2000ms_normal_backoff"]}, {"time": 2000, "props": ["tcp_second_rto_deadline_reached"]}, {"time": 2001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_second_rto_armed_2000ms_normal_backoff"]}, {"time": 1999, "props": ["tcp_second_rto_deadline_reached"]}, {"time": 2001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["tcp_second_rto_armed_2000ms_normal_backoff"]}, {"time": 2001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Encoded normal-backoff branch, correlated supersession, deadline event, and late/missing negative.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Linux thin-stream linear timeout mode is excluded; the adapter must require the normal exponential-backoff branch.

## TCP-SYN-01 — SYN retransmission R2 covers at least three minutes

- 性质：主动打开在无 RST、ICMP 或应用取消时，不得在首个 SYN 后 180 秒内因 SYN excessive retransmission 的 R2 阈值失败。
- 规范：[RFC 9293 RFC 9293 §3.8.3](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.3)；强度 `MUST`；时间 `180000 ms`（`NORMATIVE_MINIMUM`）。
- 规范短摘录：“R2 for a SYN segment MUST be set ... for at least 3 minutes”
- 数学 MITL：`G (tcp_active_open_syn_r2_started -> G [0,180000) (!tcp_open_failed_by_syn_r2_expiry))`
- MightyPPL（finite weak outer global）：`G* (tcp_active_open_syn_r2_started -> G [0,180000) (!tcp_open_failed_by_syn_r2_expiry))`
- AP：`tcp_active_open_syn_r2_started, tcp_open_failed_by_syn_r2_expiry`
- AP 定义：{"tcp_active_open_syn_r2_started": "Initial SYN is transmitted for an active open under the stack's default SYN-retry policy.", "tcp_open_failed_by_syn_r2_expiry": "tcp_write_timeout closes SYN_SENT specifically because its retransmission R2 threshold expired."}
- Correlation：network namespace + socket cookie + active-open attempt
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `net/ipv4/tcp_timer.c:242-298`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L242-L298)；符号 `tcp_write_timeout`。
- 主源码映射 AP：`["tcp_open_failed_by_syn_r2_expiry"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "initial active-open SYN transmission and retransmission timer arm", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_output.c", "symbol": "tcp_connect", "lines": "4360-4398", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4360-L4398", "atomic_propositions": ["tcp_active_open_syn_r2_started"]}, {"role": "locked Linux SYN retry-policy deviation evidence", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "include/net/tcp.h", "symbol": "TCP_SYN_RETRIES", "lines": "124-131", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L124-L131", "atomic_propositions": ["tcp_active_open_syn_r2_started", "tcp_open_failed_by_syn_r2_expiry"]}]`
- Hook：Start at initial SYN output; emit failure immediately before tcp_write_err when SYN_SENT and expired is due to retry_until.
- 正例 timed word：`[{"time": 0, "props": ["tcp_active_open_syn_r2_started"]}, {"time": 180000, "props": ["tcp_open_failed_by_syn_r2_expiry"]}, {"time": 180001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_active_open_syn_r2_started"]}, {"time": 179999, "props": ["tcp_open_failed_by_syn_r2_expiry"]}, {"time": 180001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`APPROVE`；Independent standard/formula/source audit approved this card without a semantic correction.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The RFC allows the application to close sooner; RST, ICMP unreachable and application cancellation are deliberately separate terminal causes.

## TCP-TW-01 — Linux TIME-WAIT 60-second profile with guarded reopen

- 性质：Linux 60 秒 TIME-WAIT profile 中，若未发生 RFC 允许的 guarded reopen/reuse 或管理性清理，状态不得在 60000 ms 前因普通 TIME-WAIT expiry 被销毁。
- 规范：[RFC 9293 RFC 9293 §3.6.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.6.1)；强度 `MUST`；时间 `60000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“it MUST linger in the TIME-WAIT state for a time 2xMSL”
- 数学 MITL：`G (tcp_time_wait_entered_linux_profile -> G [0,60000) ((!tcp_time_wait_state_destroyed) || tcp_valid_timewait_reopen_or_admin_cleanup))`
- MightyPPL（finite weak outer global）：`G* (tcp_time_wait_entered_linux_profile -> G [0,60000) ((!tcp_time_wait_state_destroyed) || tcp_valid_timewait_reopen_or_admin_cleanup))`
- AP：`tcp_time_wait_entered_linux_profile, tcp_time_wait_state_destroyed, tcp_valid_timewait_reopen_or_admin_cleanup`
- AP 定义：{"tcp_time_wait_entered_linux_profile": "A TIME-WAIT bucket is created with Linux TCP_TIMEWAIT_LEN=60 seconds.", "tcp_time_wait_state_destroyed": "The bucket is removed by the ordinary TIME-WAIT expiry path.", "tcp_valid_timewait_reopen_or_admin_cleanup": "Guarded RFC reopen/reuse or explicit administrative cleanup causes early removal and is classified separately."}
- Correlation：network namespace + 4-tuple + TIME-WAIT bucket cookie
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `include/net/tcp.h:140-148`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L140-L148)；符号 `TCP_TIMEWAIT_LEN`。
- 主源码映射 AP：`["tcp_time_wait_entered_linux_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "TIME-WAIT bucket creation and scheduling", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_minisocks.c", "symbol": "tcp_time_wait", "lines": "326-394", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_minisocks.c#L326-L394", "atomic_propositions": ["tcp_time_wait_entered_linux_profile"]}, {"role": "ordinary TIME-WAIT expiry destruction", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/inet_timewait_sock.c", "symbol": "tw_timer_handler", "lines": "161-166", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/inet_timewait_sock.c#L161-L166", "atomic_propositions": ["tcp_time_wait_state_destroyed"]}, {"role": "guarded direct reopen and exceptional early removal classification", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_minisocks.c", "symbol": "tcp_timewait_state_process", "lines": "186-261", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_minisocks.c#L186-L261", "atomic_propositions": ["tcp_valid_timewait_reopen_or_admin_cleanup"]}]`
- Hook：Emit entry at tcp_time_wait creation and destruction immediately before inet_twsk_kill/deschedule.
- 正例 timed word：`[{"time": 0, "props": ["tcp_time_wait_entered_linux_profile"]}, {"time": 60000, "props": ["tcp_time_wait_state_destroyed"]}, {"time": 60001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_time_wait_entered_linux_profile"]}, {"time": 59999, "props": ["tcp_time_wait_state_destroyed"]}, {"time": 60001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Restored the locked Linux 60 s profile and encoded RFC-permitted guarded reopen/administrative cleanup.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Linux's 60-second constant is shorter than the RFC-derived 240 seconds. RFC 9293 also permits guarded direct reopen from TIME-WAIT under explicit sequence-number safeguards.

## TCP-ZWP-01 — First zero-window probe follows one RTO

- 性质：发送窗口为零且当前 RTO=1000 ms 时，实际 arm 的首个 probe timer 不得提前到期，并须在 1000 ms 到期/尝试发送，或因窗口打开、连接终止而取消。
- 规范：[RFC 9293 RFC 9293 §3.8.6.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.1)；强度 `SHOULD`；时间 `1000 ms`（`NORMATIVE_DERIVED_PROFILE`）。
- 规范短摘录：“SHOULD send the first zero-window probe when a zero window has existed”
- 数学 MITL：`G (tcp_probe0_timer_armed_1000ms -> (G [0,1000) (!tcp_probe0_deadline_or_attempt) && F [0,1000] (tcp_probe0_deadline_or_attempt || tcp_probe0_superseded)))`
- MightyPPL（finite weak outer global）：`G* (tcp_probe0_timer_armed_1000ms -> (G [0,1000) (!tcp_probe0_deadline_or_attempt) && F [0,1000] (tcp_probe0_deadline_or_attempt || tcp_probe0_superseded)))`
- AP：`tcp_probe0_timer_armed_1000ms, tcp_probe0_deadline_or_attempt, tcp_probe0_superseded`
- AP 定义：{"tcp_probe0_timer_armed_1000ms": "ICSK_TIME_PROBE0 is actually armed at a 1000 ms deadline for one zero-window generation.", "tcp_probe0_deadline_or_attempt": "That generation reaches its deadline and enters the probe-attempt path, independent of local send success.", "tcp_probe0_superseded": "Window-open, user-timeout, connection termination, or explicit timer replacement cancels that generation."}
- Correlation：socket cookie + advertised-window update generation
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `include/net/tcp.h:1640-1667`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L1640-L1667)；符号 `tcp_check_probe_timer`。
- 主源码映射 AP：`["tcp_probe0_timer_armed_1000ms"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "PROBE0 deadline dispatch and attempt entry", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_timer.c", "symbol": "tcp_write_timer_handler", "lines": "695-728", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L695-L728", "atomic_propositions": ["tcp_probe0_deadline_or_attempt"]}, {"role": "window-open clear or probe-timer rearm", "repository": "torvalds/linux", "commit": "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9", "path": "net/ipv4/tcp_input.c", "symbol": "tcp_ack_probe", "lines": "3807-3828", "url": "https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_input.c#L3807-L3828", "atomic_propositions": ["tcp_probe0_superseded"]}]`
- Hook：Record the zero-window trigger when ICSK_TIME_PROBE0 is armed; record the probe at tcp_send_probe0/tcp_write_wakeup success.
- 正例 timed word：`[{"time": 0, "props": ["tcp_probe0_timer_armed_1000ms"]}, {"time": 1000, "props": ["tcp_probe0_deadline_or_attempt"]}, {"time": 1001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_probe0_timer_armed_1000ms"]}, {"time": 999, "props": ["tcp_probe0_deadline_or_attempt"]}, {"time": 1001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["tcp_probe0_timer_armed_1000ms"]}, {"time": 1001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Separated timer/attempt correctness from successful local transmission and encoded correlated cancellation.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Requires current icsk_rto=1000 ms and excludes an earlier RTT-derived RTO or local-resource failure.

## TCP-ZWP-02 — Zero-window probes back off exponentially

- 性质：正常 probe 退避分支实际按 2000 ms arm 下一 generation 后，不得提前到期，并须在 2000 ms 到期/尝试发送，或被窗口打开、资源重调度、终止所替换。
- 规范：[RFC 9293 RFC 9293 §3.8.6.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.1)；强度 `SHOULD`；时间 `2000 ms`（`NORMATIVE_DERIVED_PROFILE`）。
- 规范短摘录：“increase exponentially the interval between successive probes”
- 数学 MITL：`G (tcp_probe0_backoff_armed_2000ms -> (G [0,2000) (!tcp_probe0_second_deadline_or_attempt) && F [0,2000] (tcp_probe0_second_deadline_or_attempt || tcp_probe0_second_superseded)))`
- MightyPPL（finite weak outer global）：`G* (tcp_probe0_backoff_armed_2000ms -> (G [0,2000) (!tcp_probe0_second_deadline_or_attempt) && F [0,2000] (tcp_probe0_second_deadline_or_attempt || tcp_probe0_second_superseded)))`
- AP：`tcp_probe0_backoff_armed_2000ms, tcp_probe0_second_deadline_or_attempt, tcp_probe0_second_superseded`
- AP 定义：{"tcp_probe0_backoff_armed_2000ms": "Normal zero-window backoff increments and arms the next timer generation at 2000 ms.", "tcp_probe0_second_deadline_or_attempt": "That exact generation reaches deadline and enters its send-attempt path.", "tcp_probe0_second_superseded": "Window-open, local-resource reschedule, user-timeout, termination, or explicit rearm replaces the generation."}
- Correlation：socket cookie + zero-window probe generation
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[torvalds/linux@f4fb100039e9 `net/ipv4/tcp_output.c:4601-4635`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4601-L4635)；符号 `tcp_send_probe0`。
- 主源码映射 AP：`["tcp_probe0_backoff_armed_2000ms", "tcp_probe0_second_deadline_or_attempt", "tcp_probe0_second_superseded"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[]`
- Hook：After icsk_backoff increments and tcp_probe0_when computes the next timer, record old/new interval and probe generation.
- 正例 timed word：`[{"time": 0, "props": ["tcp_probe0_backoff_armed_2000ms"]}, {"time": 2000, "props": ["tcp_probe0_second_deadline_or_attempt"]}, {"time": 2001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["tcp_probe0_backoff_armed_2000ms"]}, {"time": 1999, "props": ["tcp_probe0_second_deadline_or_attempt"]}, {"time": 2001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["tcp_probe0_backoff_armed_2000ms"]}, {"time": 2001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Uses rearm/deadline/attempt and explicit resource/cancel supersession instead of send success.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Only the first backoff step is instantiated; later steps are the same obligation and are not duplicated as properties.
