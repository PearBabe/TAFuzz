# TCP / QUIC / TLS / DTLS / SSH / DICOM 候选性质独立审计

审计日期：2026-07-13（Asia/Shanghai）  
审计范围：`_staging/transport_security_protocols/` 中 21 条候选性质、6 份
`evidence.json` 及对应排除清单。  
审计约束：只读核验候选文件；本文件是唯一写入。未构建 SUT、未修改候选、未运行
fuzzing。

## 结论摘要

| 结果 | 数量 | 条目 |
|---|---:|---|
| `APPROVE` | 5 | TCP-ACK-01、TCP-KA-01、TCP-R2-01、TCP-SYN-01、QUIC-ACK-01 |
| `FIX` | 14 | TCP-RTO-01、TCP-RTO-03、TCP-ZWP-01、TCP-ZWP-02、TCP-TW-01、QUIC-PTO-01、QUIC-PTO-02、QUIC-IDLE-01、QUIC-PV-01、DTLS12-RTX-01、DTLS12-RTX-03、DTLS12-RTX-04、SSH-REKEY-01、DICOM-ARTIM-01 |
| `REJECT` | 2 | TLS13-TICKET-01、DTLS12-FINAL-01 |

这里的 `REJECT` 针对**当前公式/AP/源码证据组合**，不否认底层标准条款有价值；两条都可在重新设计 oracle 后作为新候选提交。

## 跨条目发现

1. 21/21 当前公式都能由 TAMonitor 以 `finite + flatten` 构造；当前正例均为
   `POSITIVE`，当前反例均为 `NEGATIVE`，symbolic/concrete 一致。这只证明候选与
   自造 trace 自洽，不是标准一致性证明。
2. 对形如 `G[0,T)(!early) && F[0,T](fire || cancel)` 的双边窗口性质，现有单条
   反例几乎都只覆盖“过早触发”，没有覆盖“到期仍不触发”。应至少保留
   `negative_early` 与 `negative_late_or_missing` 两条反例，否则删掉 `F` 分支的错误
   公式也可能通过当前 oracle。
3. 标准通常规定“设置一个在 T 后到期的计时器”，实现 hook 却多处定义为“回调被
   调度/执行”。OS 调度延迟会把正确的 deadline 错报为晚触发。应优先记录
   `timer_armed(deadline)` / `timer_expired_at_deadline`，把 callback dispatch 单列为
   实现性能事件。
4. 所有 40 位 commit、主 `source_path`、行号范围和 `source_symbol` 都能从固定
   GitHub raw source 解析；但是“文件/符号存在”不等于所有 AP 已映射。若触发、取消、
   终止分别位于不同函数，应保留多个固定 permalink，而不是只在自然语言中写函数名。
5. `TCP/evidence.json` 漏列了 TCP-R2-01/TCP-SYN-01 实际使用的 RFC 9293
   §3.8.3；六组 `evidence.json` 的 `status: COMPLETE` 应在本审计问题修复前降为
   `UNDER_REVIEW`。
6. 每个协议下 `excluded.md` 与 `excluded_properties.md` 内容重复。它不改变语义，
   但会让汇总器重复收录排除理由，建议只保留一个权威文件或按 hash 去重。

## TCP

规范依据：[RFC 6298 §2.1](https://www.rfc-editor.org/rfc/rfc6298.html#section-2.1)、
[RFC 6298 §5](https://www.rfc-editor.org/rfc/rfc6298.html#section-5)、
[RFC 9293 §3.6.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.6.1)、
[§3.8.3](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.3)、
[§3.8.4](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.4)、
[§3.8.6.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.1)、
[§3.8.6.3](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.3)。

### TCP-RTO-01 — `FIX`

- RFC 6298 的 1 秒是 `SHOULD`；紧接着明确允许 3 秒或任意大于 1 秒的值。候选可作为
  “RFC 推荐的 Linux 1 秒 profile”，不能把所有“无 RTT 样本”发送都作为触发。
- Linux 固定源码同时定义 `TCP_TIMEOUT_INIT=1s` 与三次握手重传后可能采用的
  `TCP_TIMEOUT_FALLBACK=3s`。当前 AP `tcp_first_segment_sent_without_rtt` 会覆盖后者，
  仅在 `limitations` 中排除不足以改变 valuation。
- 公式观测 callback fire，而标准直接约束的是 RTO 值和 timer deadline。
- 当前反例只测 999 ms 早触发，没有测 1000 ms 后仍未到期/未取消。
- 修复：触发改为 `tcp_initial_rto_armed_1000ms_profile`，显式要求未采用 fallback；
  结果 AP 改为 deadline expiry（或另给 callback-jitter profile）；新增 late/missing
  反例。源码继续使用固定
  [`include/net/tcp.h:160`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L160-L173)，
  并补实际 arm/cancel/fire 的固定函数行。

### TCP-RTO-03 — `FIX`

- RFC 6298 §5.5 的倍增义务真实，Linux 正常分支也在固定
  [`tcp_timer.c:657`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L657-L685)
  将 RTO 左移一位并重置 timer。
- 当前 trigger 定义没有把源码中的 thin-stream linear timeout 与 SYN linear timeout
  排除条件编码进 valuation；写在 `limitations` 中不能避免误触发。
- ACK 应只在它确实重启/替换本次 retransmission timer 时解除该实例；建议 AP 改为
  `tcp_ack_restarted_or_cancelled_correlated_rto`，而不是泛化的 `SND.UNA` 任意推进。
- 补“未按 2 秒 deadline 到期”的第二条负例，并给 timer rearm 与 cancellation 各自
  固定源码行。

### TCP-ACK-01 — `APPROVE`

- RFC 9293 明确规定 delayed ACK 的延迟必须**严格小于** 0.5 秒；
  `F[0,500)` 与 499/500 ms 正反边界完全吻合。
- trigger 已限制为进入 delayed-ACK 分支，避免把本应立即 ACK 的乱序/填洞分支混入。
- Linux 固定 [`tcp_send_delayed_ack`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4409-L4463)
  确实对 ACK timer 设界；ACK 以 socket cookie + receive sequence interval 关联合理。
- 非阻塞改进：为实际 `tcp_send_ack`/输出点补第二 permalink，便于插桩复核。

### TCP-ZWP-01 — `FIX`

- RFC 9293 的“一 RTO 后首 probe”条款真实，固定
  [`tcp_check_probe_timer`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L1640-L1667)
  也使用当前 RTO。
- 当前 consequent 是“成功发出 probe”。本地 qdisc/资源失败时 timer 正确到期、实现也
  尝试发送，但该 AP 仍为 false，产生与协议计时无关的假阳性。源码注释明确同时处理
  qdisc 满、零窗口和 pacing。
- 修复：主计时性质监测 `probe_timer_expired_or_probe_attempted`；成功发包另做 fuzzing
  观测。若坚持成功事件，必须给 `local_resource_failure` 合法 discharge。补 late/missing
  反例与真正 send-attempt 源码行。

### TCP-ZWP-02 — `FIX`

- 指数退避条款和 Linux `icsk_backoff++`/`tcp_probe0_when` 证据成立：
  [`tcp_output.c:4601`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_output.c#L4601-L4635)。
- 与上一条相同，`tcp_second_zero_window_probe_sent` 把 timer/backoff 正确性与本地发送
  成功混合；`err>0` 资源路径会改用资源 probe interval，当前公式没有 discharge。
- 修复为 rearm deadline/attempt oracle，并将 `err>0`、窗口重新打开、用户 timeout
  分别编码；新增未到期负例。

### TCP-KA-01 — `APPROVE`

- RFC 9293 要求 keep-alive 默认关闭；若实现提供并由应用开启，其默认空闲间隔不得短于
  两小时。trigger 已同时要求应用开启、无 per-socket override、无 outstanding data。
- `G[0,7200000)(!probe)` 只施加协议给出的下界，没有虚构“两小时必须发送”的上界；
  7200000 ms 处允许发送，边界正确。
- Linux 固定
  [`TCP_KEEPALIVE_TIME`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L175-L180)
  是两小时。配置变更时应结束该 profile projection，但不影响当前受限 claim。

### TCP-TW-01 — `FIX`

- 60 秒被正确标为 Linux `2*MSL` 实现 profile，而非 RFC 通用常数；固定
  [`TCP_TIMEWAIT_LEN`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/include/net/tcp.h#L140-L148)
  证据真实。
- RFC 9293 §3.6.1 明确允许在满足新 ISN 条件时从 TIME-WAIT 接受新 SYN，并在发现旧
  SYN 时返回 TIME-WAIT。当前公式无条件禁止 60 秒内 state destruction，遗漏这一合法
  reopen/reuse 例外；`limitations` 已承认但公式未表达。
- 修复：在“未发生 RFC 允许 reopen、未发生管理性清理”的明确 profile 下触发，或加入
  `tcp_valid_timewait_reopen` discharge；补 entry、reuse、destroy 的固定源码 hooks。

### TCP-R2-01 — `APPROVE`

- RFC 9293 §3.8.3 的 data R2 `SHOULD` 至少对应 100 秒。公式仅禁止
  `closed_by_data_r2_expiry` 在 100 秒前发生，没有要求恰在 100 秒关闭，强度正确。
- AP 把 application `TCP_USER_TIMEOUT`、RST/ICMP、资源压力和应用 close 与 R2 cause
  分开；固定
  [`tcp_write_timeout`](https://github.com/torvalds/linux/blob/f4fb100039e96211609dfc44fb24b9e4a8a0f2f9/net/ipv4/tcp_timer.c#L242-L305)
  能观测 `expired` 和 `tcp_write_err`。
- 修订 evidence manifest 时补列 RFC 9293 §3.8.3。

### TCP-SYN-01 — `APPROVE`

- RFC 9293 要求 SYN R2 足以持续重传至少三分钟，并明确应用可以更早放弃。
- 公式只禁止“由 SYN R2 expiry 导致的失败”在 180 秒前发生；RST、ICMP、应用取消均不
  使用该 AP，未遗漏标准例外。
- 固定 `tcp_write_timeout` 的 SYN_SENT 分支提供 cause hook。建议运行时保留
  `retry_until`、`icsk_retransmits` 和 elapsed time 字段用于人工复核，但无需改公式。

## QUIC

规范依据：[RFC 9000 §8.2.4](https://www.rfc-editor.org/rfc/rfc9000.html#section-8.2.4)、
[§10.1](https://www.rfc-editor.org/rfc/rfc9000.html#section-10.1)、
[§13.2.1](https://www.rfc-editor.org/rfc/rfc9000.html#section-13.2.1)、
[§18.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-18.2)，以及
[RFC 9002 §6.2](https://www.rfc-editor.org/rfc/rfc9002.html#section-6.2)。

### QUIC-ACK-01 — `APPROVE`

- RFC 9000 要求已处理的 ack-eliciting 1-RTT packet 在 advertised/default
  `max_ack_delay` 内被至少确认一次；参数缺失时默认 25 ms。
- trigger 明确要求“已完全处理、可解密、1-RTT、默认参数”，避开握手确认前缺密钥的
  缓冲例外；`F[0,25]` 与 25/26 ms 正反 trace 正确。
- ngtcp2 固定
  [`conn_compute_ack_delay`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L1847-L1855)
  和
  [`NGTCP2_DEFAULT_MAX_ACK_DELAY`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L1278-L1285)
  支持该映射。

### QUIC-PTO-01 — `FIX`

- 333 ms initial RTT 及 Initial/Handshake PTO 不计 `max_ack_delay` 的依据真实；ngtcp2
  整数计算得到 999 ms，而 RFC 叙述称 1 秒，候选已正确披露差异。
- 主要错误是 trigger 绑定“发送一个 ack-eliciting packet”。RFC 9002 建议在后续
  ack-eliciting packet 发送/确认、或丢弃 Initial/Handshake keys 时重启 PTO。旧 trigger
  的 999/1000 ms obligation 仍存活，会把合法重启误报为超时。
- 修复：以实际 `loss_detection_timer_armed/rearmed(deadline, pto_count=0)` 为实例起点，
  或加入 `pto_restarted_or_loss_timer_superseded` discharge；同时编码“time-threshold loss
  timer 已设置时不得设置 PTO”的分支。补早/晚两类负例及 arm/fire 固定源码行。

### QUIC-PTO-02 — `FIX`

- 跨 packet-number space 指数倍增是真实 `MUST`，固定
  [`conn_get_earliest_pto_expiry`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L13387-L13424)
  也乘以 `2^pto_count`。
- 当前 ACK discharge 太宽。RFC 9002 明确规定：地址尚未验证的 client 收到 Initial ACK
  时不重置 PTO backoff。AP 应改为 `quic_ack_that_resets_pto_backoff`。
- 第二期限应从 PTO probe 实际发送/新 timer rearm 的时间算，而不是模糊的“first PTO
  completed”；期间新的 ack-eliciting send 也会重启 timer。补 restart discharge、
  `pto_count` increment/probe send/rearm hooks，以及 missing/late 反例。

### QUIC-IDLE-01 — `FIX`

- 30 秒仅是 ngtcp2 example profile，候选标签正确；库函数也按协商值与 `3*PTO` 取大：
  [`ngtcp2_conn_get_idle_expiry`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L14060-L14092)。
- RFC 9000 允许 endpoint 在 idle timeout 前主动放弃连接，只要求先 initiating an
  immediate close；随后可在合法 closing/draining 期结束后丢弃状态。当前公式禁止任何
  30 秒前 discard，因此会把显式应用 close/transport close 误报。
- 修复：加入 `quic_explicit_close_started`、stateless reset/transport terminal 等合法
  discharge，或把 trigger profile 限定为“连接保持 open 且仅由 idle timer 终止”。
  30 秒来源应继续指向 `examples/server_base.h:76-77`，并补应用 destruction hook。

### QUIC-PV-01 — `FIX`

- RFC 9000 的推荐值确为 `3*max(current PTO,new-path PTO)`；ngtcp2 固定计算函数也吻合。
- 当前 `quic_path_validation_abandoned` 混合了 timer expiry 与被新 migration/应用决策
  supersede 的非超时取消。候选在 `limitations` 中要求单独标记，却没有在公式中提供
  cancellation AP，因而仍会误报合法早取消。
- 改为 `abandoned_by_validation_timeout`，加入 `validation_superseded` discharge；触发
  必须记录两个 PTO 都为 999 ms 的快照。补未在 2997 ms 成功/超时的负例和实际
  create/success/expiry 源码 hooks。

## TLS

规范依据：[RFC 8446 §4.6.1](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.6.1)
及 [§4.2.11.1](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.2.11.1)。

### TLS13-TICKET-01 — `REJECT`

- 七天上限是真实条款，但当前 consequent `tls13_ticket_became_unusable` 被定义为
  “adapter/client 在 min(ticket_lifetime,7d) 标记”。若 adapter 仅依据标准时钟自行发出
  该 AP，公式会无条件通过，无法检测实现是否仍缓存/仍发送 PSK identity，属于
  self-fulfilling oracle。
- 固定
  [`tls_construct_ctos_psk:1094-1118`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/statem/extensions_clnt.c#L1094-L1118)
  只比较服务器提供的 `tick_lifetime_hint`，还为秒级取整主动减一；它没有证明客户端在
  7 天处主动 eviction/mark，也没有把七天 clamp 映射到源码。
- 公式 OR `became_unusable || removed` 还会让物理 cache 中长期保留、仅由 observer
  宣称“不可用”的 ticket 通过“不得缓存超过七天”这一独立 MUST NOT。
- 新候选应选择一个可证 oracle：例如固定 source hook 的 `not_resumable`/cache removal
  转移，或在虚拟时间超过七天后主动发起 resumption 并监测是否实际序列化该 ticket 的
  PSK identity。后者是使用禁令测试，不应再用 observer 生成的“unusable”作结论 AP。

## DTLS

规范依据：[RFC 6347 §4.2.4](https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4)
和 [§4.2.4.1](https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1)。

### DTLS12-RTX-01 — `FIX`

- 1 秒初值是 `SHOULD`，不是通用 MUST。OpenSSL 固定源码还允许 `timer_cb` 覆盖该值，
  并对 SCTP 直接禁用 timer：
  [`dtls1_start_timer`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L242-L284)。
- 当前 trigger 仅说“flight sent/WAITING”，没有要求 datagram 非 SCTP、`timer_cb==NULL`
  且实际 duration=1000000 us，因而会在合法配置上误触发。
- 改为“默认 OpenSSL DTLS 1.2 timer 已按 1 秒 arm”的 profile trigger；监测 deadline
  而非 callback dispatch；补 late/missing 反例和 stop/peer-flight hook。

### DTLS12-RTX-03 — `FIX`

- RFC 的 doubling 建议和 OpenSSL 固定
  [`dtls1_double_timeout`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L344-L350)
  均真实。
- WAITING 期间若收到 peer previous-flight duplicate，RFC 状态机会立即重传本方 flight
  并 reset timer；这是合法的新 timer 实例。当前公式只允许 expected next flight
  discharge，旧 2 秒 obligation 不会被取消，可能误报。
- 加入 `dtls_timer_restarted_by_duplicate_flight`/supersession discharge，trigger 绑定
  实际 2 秒 rearm deadline，并补 missing/late 反例。

### DTLS12-RTX-04 — `FIX`

- RFC 只要求实现允许的最大 backoff **不低于** 60 秒；候选已把“恰好 cap=60 秒”标为
  OpenSSL profile，因此没有把实现常数冒充通用标准。
- 与 RTX-03 相同，60 秒等待中 duplicate-flight retransmission 可合法 reset timer；当前
  obligation 未被替换。需加入 restart/supersession discharge，并补第二条负例。
- source hook 还应记录 clamp 后的值与随后 `dtls1_start_timer` 的 absolute deadline，
  不能只记录函数符号存在。

### DTLS12-FINAL-01 — `REJECT`

- RFC 6347 的真实要求是：last-flight sender 至少在 `2*default TCP MSL` 期间保留响应
  能力，并在收到对端 previous-flight retransmit 时作出响应。RFC 没有要求 response 与
  duplicate 在同一个 pointwise timestamp/microstep。
- 当前 `duplicate -> retransmitted` 是同位置 Boolean implication；它会拒绝任何在 1 ms
  后响应的实现，实际把无数字时限的响应义务变成 punctual/zero-delay 义务。
- 固定
  [`rec_layer_d1.c:662-679`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/record/rec_layer_d1.c#L662-L679)
  只展示收到重复 Finished 后立即调用 retransmit；没有证明 240 秒 retention timer 或
  buffer 生命周期。它最多支持 OpenSSL 同回调 action oracle，不能支持当前协议级 4 分钟
  MITL claim。
- 应拆为：(a) 若能找到 buffer/state disposal 的固定 hook，则做“240 秒内不丢弃响应
  能力”的 retention 性质；(b) duplicate 后响应保留为无数值 Boolean/action oracle，
  或明确标作 OpenSSL microstep profile，不能计作 RFC 的非 punctual 主性质。

## SSH

规范依据：[RFC 4253 §9](https://www.rfc-editor.org/rfc/rfc4253.html#section-9)。

### SSH-REKEY-01 — `FIX`

- RFC 推荐的是“keys be changed after each gigabyte or after each hour, whichever comes
  sooner”；当前 consequent 只要求 `rekey_started`，比“keys changed”弱。
- 对 fuzzing 中不合作 peer，要求在一小时内完成 KEX 也会把 peer stall 错归给 SUT。
  因此可保留“本地在一小时内发出 KEXINIT”作为**可控端代理指标**，但必须改标题、
  `natural_language` 和 `limitations`，明确它不是 RFC 完成义务的等价翻译。
- pinned OpenSSH 默认 `rekey_interval=0`，候选已披露；只有实验显式设置一小时 profile
  后才可触发。固定
  [`ssh_packet_need_rekeying`](https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L1043-L1085)
  还要求认证完成、非 KEX 中、peer 可 rekey、已有 packet。AP 应包含这些 branch
  conditions。
- 若要忠实 RFC claim，应另建 `newkeys_installed` 完成性质，并把 peer close/stall 作为
  环境假设或 outcome 分类；不要将“启动”等同于“已更换”。

## DICOM

规范依据：[DICOM PS3.8 §9.1.2–9.1.5](https://dicom.nema.org/medical/dicom/current/output/chtml/part08/chapter_9.html)
及 §9.2 state machine。

### DICOM-ARTIM-01 — `FIX`

- DICOM 确实要求 accept transport connection 后设置 ARTIM，也要求该值可配置；30 秒
  被正确标为 DCMTK profile，不是 DICOM 通用数值。
- 当前公式遗漏合法的 early transport close。固定 `DUL_ReceiveAssociationRQ` 在等待
  首 PDU 时会分别产生 `TRANS_CONN_CLOSED`、`ARTIM_TIMER_EXPIRED` 或
  `A_ASSOCIATE_RQ_PDU_RCV`；若 peer 在 10 秒主动断开，当前公式仍要求 30 秒出现 expiry
  或 request，造成假阳性。应加入 `dicom_transport_connection_closed` discharge，并对
  解析错误/abort outcome 作显式分类。
- 当前 `profile_source_url` 指向 `dcmnet/libsrc/scu.cc` 的 `DcmSCU` 构造函数，这是请求方
  类，与候选的 SCP/acceptor 角色不匹配。30 秒 acceptor profile 的正确固定证据是
  `dcmnet/apps/storescp.cc` 的 `opt_acse_timeout=30`（line 173）及传入
  `ASC_initializeNetwork`（line 936）；核心等待/分支证据仍是
  [`dul.cc:687-707`](https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/libsrc/dul.cc#L687-L707)。
- 当前反例只测 29999 ms 早 expiry；增加“30 秒后仍无 expiry/request/close”的负例。

## 证据与验证记录

### 读取的证据文件

- `analysis/protocol_fuzzing_study/_staging/transport_security_protocols/{tcp,quic,tls,dtls,ssh,dicom}/proposals.json`
- 同目录每个协议的 `evidence.json`、`excluded.md`、`excluded_properties.md`
- RFC Editor 固定文档：RFC 6298、9293、9000、9002、8446、6347、793、4253
- DICOM PS3.8 2026c 官方 HTML 第 9 章
- 候选记录的 40 位 GitHub commit raw source；另核验了 OpenSSL ticket/session cache、
  DCMTK `storescp.cc`/`assoc.cc`/`dul.cc` 的关联路径。

### 实际验证命令与结果

```text
python3 -m json.tool <each proposals.json>
# 6/6 JSON 可解析。

# 通过 import generate_multi_protocol_catalog.py，在 /tmp 下调用
# normalize_candidate + validate_property；未写候选目录。
# 结果：21/21 build PASS；正例 POSITIVE；反例 NEGATIVE；
#       symbolic/concrete 21/21 一致。

# 对 21 条调用 verify_source(normalized_candidate)。
# 结果：21/21 source_file_verified=true；
#       21/21 source_line_verified=true；
#       21/21 source_symbol_verified=true。

curl https://www.rfc-editor.org/rfc/rfc{6298,9293,9000,9002,8446,6347,793,4253}.txt
curl https://dicom.nema.org/medical/dicom/current/output/chtml/part08/chapter_9.html
# 回查所有引用条款、例外和边界。
```

## 未决问题

1. 总汇总器当前只接受一个 `negative_trace`；是否扩展为多个命名反例，或在每条验证目录
   额外保留 early/late 两类 trace，需要主代理决定。
2. timer AP 最终统一采用“absolute deadline reached”还是“callback dispatched”，关系到
   所有 retransmission 类性质是否会受调度 jitter 干扰；建议前者用于协议 verdict，后者
   仅作性能/实现诊断。
3. TLS 七天 ticket 性质若无法找到真实 cache-state transition，应移入排除清单，而不是
   用 adapter 根据同一条标准自行生成 consequent。
4. DTLS final-flight 的 240 秒 retention 在所锁 OpenSSL commit 中尚无对应定时销毁 hook；
   在找到该 hook 前不能作为主目录 MITL 性质。
