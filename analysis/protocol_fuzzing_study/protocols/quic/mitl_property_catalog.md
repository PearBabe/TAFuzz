# QUIC MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：7
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## QUIC-ACK-01 — 1-RTT ACK respects the default 25 ms max_ack_delay

- 性质：未显式发送 max_ack_delay 参数时，已解密处理的 ack-eliciting 1-RTT 包必须在 25 ms 内至少确认一次。
- 规范：[RFC 9000 RFC 9000 (QUIC v1) §13.2.1, 18.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-13.2.1)；强度 `MUST`；时间 `25 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“MUST be acknowledged at least once within the maximum delay”
- 数学 MITL：`G (quic_1rtt_ack_eliciting_packet_processed_default_ack_delay -> F [0,25] (quic_ack_covering_packet_sent))`
- MightyPPL（finite weak outer global）：`G* (quic_1rtt_ack_eliciting_packet_processed_default_ack_delay -> F [0,25] (quic_ack_covering_packet_sent))`
- AP：`quic_1rtt_ack_eliciting_packet_processed_default_ack_delay, quic_ack_covering_packet_sent`
- AP 定义：{"quic_1rtt_ack_eliciting_packet_processed_default_ack_delay": "Protected 1-RTT packet is fully processed, is ack-eliciting, and local max_ack_delay is the absent-parameter default.", "quic_ack_covering_packet_sent": "An outgoing ACK frame contains the correlated packet number."}
- Correlation：QUIC connection object + packet number space + packet number; packet numbers stay fields
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_conn.c:1847-1855`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L1847-L1855)；符号 `conn_compute_ack_delay`。
- 主源码映射 AP：`["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "default max_ack_delay profile constant", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/includes/ngtcp2/ngtcp2.h", "symbol": "NGTCP2_DEFAULT_MAX_ACK_DELAY", "lines": "1278-1285", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L1278-L1285", "atomic_propositions": ["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"]}, {"role": "commit fully processed ack-eliciting packet number", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "pktns_commit_recv_pkt_num", "lines": "6293-6337", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L6293-L6337", "atomic_propositions": ["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"]}, {"role": "ACK frame range construction for outgoing packet", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_acktr.c", "symbol": "ngtcp2_acktr_create_ack_frame", "lines": "340-426", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_acktr.c#L340-L426", "atomic_propositions": ["quic_ack_covering_packet_sent"]}]`
- Hook：Start at pktns_commit_recv_pkt_num; finish when ngtcp2_acktr_create_ack_frame output is serialized.
- 正例 timed word：`[{"time": 0, "props": ["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"]}, {"time": 25, "props": ["quic_ack_covering_packet_sent"]}, {"time": 26, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"]}, {"time": 26, "props": ["quic_ack_covering_packet_sent"]}, {"time": 27, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"]}, {"time": 26, "props": []}]}`
- 独立审计：`APPROVE`；Independent audit confirmed the 25 ms closed upper bound and default-parameter trigger.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Initial and Handshake packets use immediate ACK semantics and are excluded from this 25 ms property.

## QUIC-IDLE-01 — ngtcp2 example profile does not discard state before 30 s idle

- 性质：双方使用 ngtcp2 example 的默认 30 秒 max_idle_timeout 时，连接持续空闲满 30 秒以前不得丢弃连接状态。
- 规范：[RFC 9000 RFC 9000 (QUIC v1) §10.1](https://www.rfc-editor.org/rfc/rfc9000.html#section-10.1)；强度 `protocol contract + implementation profile`；时间 `30000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“closed and its state is discarded when it remains idle for longer”
- 数学 MITL：`G (quic_connection_became_idle_ngtcp2_30s_profile -> G [0,30000] ((!quic_connection_state_discarded) || quic_explicit_close_or_terminal_received))`
- MightyPPL（finite weak outer global）：`G* (quic_connection_became_idle_ngtcp2_30s_profile -> G [0,30000] ((!quic_connection_state_discarded) || quic_explicit_close_or_terminal_received))`
- AP：`quic_connection_became_idle_ngtcp2_30s_profile, quic_connection_state_discarded, quic_explicit_close_or_terminal_received`
- AP 定义：{"quic_connection_became_idle_ngtcp2_30s_profile": "Negotiated effective idle timeout is 30000 ms and the last activity timestamp starts a new idle generation.", "quic_connection_state_discarded": "Connection state is disposed specifically by the idle-expiry path.", "quic_explicit_close_or_terminal_received": "Application close, peer close/stateless reset, or terminal transport error legitimately ends the open-idle profile."}
- Correlation：ngtcp2 connection object + negotiated transport-parameter snapshot
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_conn.c:14060-14092`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L14060-L14092)；符号 `ngtcp2_conn_get_idle_expiry`。
- 主源码映射 AP：`["quic_connection_became_idle_ngtcp2_30s_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "example server installs configured idle timeout transport parameter", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "examples/server.cc", "symbol": "Handler::init", "lines": "817-827", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/examples/server.cc#L817-L827", "atomic_propositions": ["quic_connection_became_idle_ngtcp2_30s_profile"], "legacy_exact_url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/examples/server_base.h#L70-L80"}, {"role": "read activity starts a new idle generation", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_restart_timer_on_read", "lines": "2163-2166", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L2163-L2166", "atomic_propositions": ["quic_connection_became_idle_ngtcp2_30s_profile"]}, {"role": "write activity starts a new idle generation", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_restart_timer_on_write", "lines": "2158-2161", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L2158-L2161", "atomic_propositions": ["quic_connection_became_idle_ngtcp2_30s_profile"]}, {"role": "connection-state disposal hook", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "ngtcp2_conn_del", "lines": "1740-1845", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L1740-L1845", "atomic_propositions": ["quic_connection_state_discarded"]}, {"role": "peer CONNECTION_CLOSE transition to draining", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_recv_connection_close", "lines": "6054-6084", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L6054-L6084", "atomic_propositions": ["quic_explicit_close_or_terminal_received"]}, {"role": "validated stateless reset transition to draining", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_on_stateless_reset", "lines": "8046-8074", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L8046-L8074", "atomic_propositions": ["quic_explicit_close_or_terminal_received"]}, {"role": "local CONNECTION_CLOSE transition to closing", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "ngtcp2_conn_write_connection_close_pkt", "lines": "12688-12749", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L12688-L12749", "atomic_propositions": ["quic_explicit_close_or_terminal_received"]}]`
- Hook：Emit idle start whenever conn_restart_timer_on_read/write updates idle_ts; emit discard immediately before application connection removal.
- 正例 timed word：`[{"time": 0, "props": ["quic_connection_became_idle_ngtcp2_30s_profile"]}, {"time": 30001, "props": ["quic_connection_state_discarded"]}, {"time": 30002, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_connection_became_idle_ngtcp2_30s_profile"]}, {"time": 29999, "props": ["quic_connection_state_discarded"]}, {"time": 30001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Explicit close, stateless reset, and terminal transport outcomes now discharge the idle-only profile.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The library computes expiry but the example application performs destruction; this property needs one library hook and one application hook.

## QUIC-KU-01 — Subsequent key update waits three PTO periods

- 性质：前一次 key update 已被 ACK 确认后，在默认 application PTO=1024 ms 的 profile 下，端点不应在 3072 ms 前再主动更新密钥。
- 规范：[RFC 9001 RFC 9001 §6.5](https://www.rfc-editor.org/rfc/rfc9001.html#section-6.5)；强度 `SHOULD`；时间 `3072 ms`（`NORMATIVE_RECOMMENDED_DERIVED_PROFILE`）。
- 规范短摘录：“Endpoints SHOULD wait three times the PTO before initiating a key update”
- 数学 MITL：`G (quic_previous_key_update_confirmed_initial_profile -> G [0,3072) (!quic_local_next_key_update_started))`
- MightyPPL（finite weak outer global）：`G* (quic_previous_key_update_confirmed_initial_profile -> G [0,3072) (!quic_local_next_key_update_started))`
- AP：`quic_previous_key_update_confirmed_initial_profile, quic_local_next_key_update_started`
- AP 定义：{"quic_previous_key_update_confirmed_initial_profile": "ACK confirms the previous key phase and current PTO inputs still equal the initial/default application profile.", "quic_local_next_key_update_started": "Local endpoint rotates transmit/receive keys to initiate the next key phase."}
- Correlation：ngtcp2 connection object + monotonically increasing key-update generation
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_conn.c:11281-11297`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L11281-L11297)；符号 `conn_initiate_key_update`。
- 主源码映射 AP：`["quic_local_next_key_update_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "previous key-update ACK confirmation timestamp", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_handle_unconfirmed_key_update_from_remote", "lines": "3455-3474", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L3455-L3474", "atomic_propositions": ["quic_previous_key_update_confirmed_initial_profile"]}, {"role": "default initial RTT input to key-update spacing profile", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/includes/ngtcp2/ngtcp2.h", "symbol": "NGTCP2_DEFAULT_INITIAL_RTT", "lines": "434-439", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L434-L439", "atomic_propositions": ["quic_previous_key_update_confirmed_initial_profile"]}, {"role": "default max_ack_delay input to key-update spacing profile", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/includes/ngtcp2/ngtcp2.h", "symbol": "NGTCP2_DEFAULT_MAX_ACK_DELAY", "lines": "1278-1285", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L1278-L1285", "atomic_propositions": ["quic_previous_key_update_confirmed_initial_profile"]}]`
- Hook：Emit confirmation when confirmed_ts is assigned; emit next-start after conn_rotate_keys succeeds as initiator.
- 正例 timed word：`[{"time": 0, "props": ["quic_previous_key_update_confirmed_initial_profile"]}, {"time": 3072, "props": ["quic_local_next_key_update_started"]}, {"time": 3073, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_previous_key_update_confirmed_initial_profile"]}, {"time": 3071, "props": ["quic_local_next_key_update_started"]}, {"time": 3073, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED_PROFILE`；Root review confirmed a no-early safety obligation under the explicitly frozen 1024 ms application-PTO profile; reinstantiate if live PTO differs.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Only applies while current smoothed_rtt/rttvar and peer max_ack_delay equal the declared profile; otherwise the live 3*PTO bound must be projected into a separately instantiated property.

## QUIC-PC-01 — Persistent congestion is not declared before three PTO periods

- 性质：在默认 initial RTT 和 max_ack_delay profile 下，连续丢失区间尚未达到 3072 ms 时不得宣告 persistent congestion。
- 规范：[RFC 9002 RFC 9002 §7.6.1](https://www.rfc-editor.org/rfc/rfc9002.html#section-7.6.1)；强度 `RECOMMENDED threshold`；时间 `3072 ms`（`NORMATIVE_RECOMMENDED_DERIVED_PROFILE`）。
- 规范短摘录：“The RECOMMENDED value for kPersistentCongestionThreshold is 3”
- 数学 MITL：`G (quic_app_loss_run_started_initial_profile -> G [0,3072) (!quic_persistent_congestion_declared))`
- MightyPPL（finite weak outer global）：`G* (quic_app_loss_run_started_initial_profile -> G [0,3072) (!quic_persistent_congestion_declared))`
- AP：`quic_app_loss_run_started_initial_profile, quic_persistent_congestion_declared`
- AP 定义：{"quic_app_loss_run_started_initial_profile": "Oldest packet in a contiguous all-lost application-space run is sent after handshake confirmation with initial RTT and default max_ack_delay.", "quic_persistent_congestion_declared": "Congestion controller's on_persistent_congestion callback is invoked for that loss run."}
- Correlation：connection object + application packet-number space + contiguous sent-packet range
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_rtb.c:1045-1085`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_rtb.c#L1045-L1085)；符号 `rtb_detect_lost_pkt`。
- 主源码映射 AP：`["quic_app_loss_run_started_initial_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "persistent-congestion threshold constant", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_cc.h", "symbol": "NGTCP2_PERSISTENT_CONGESTION_THRESHOLD", "lines": "34-38", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_cc.h#L34-L38", "atomic_propositions": ["quic_app_loss_run_started_initial_profile", "quic_persistent_congestion_declared"]}, {"role": "persistent-congestion decision and callback", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_rtb.c", "symbol": "rtb_detect_lost_pkt", "lines": "1162-1185", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_rtb.c#L1162-L1185", "atomic_propositions": ["quic_persistent_congestion_declared"]}, {"role": "default initial RTT input to fixed profile", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/includes/ngtcp2/ngtcp2.h", "symbol": "NGTCP2_DEFAULT_INITIAL_RTT", "lines": "434-439", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L434-L439", "atomic_propositions": ["quic_app_loss_run_started_initial_profile"]}, {"role": "default max_ack_delay input to fixed profile", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/includes/ngtcp2/ngtcp2.h", "symbol": "NGTCP2_DEFAULT_MAX_ACK_DELAY", "lines": "1278-1285", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L1278-L1285", "atomic_propositions": ["quic_app_loss_run_started_initial_profile"]}]`
- Hook：Record the oldest timestamp when the contiguous loss-run candidate begins; emit declaration at on_persistent_congestion.
- 正例 timed word：`[{"time": 0, "props": ["quic_app_loss_run_started_initial_profile"]}, {"time": 3072, "props": ["quic_persistent_congestion_declared"]}, {"time": 3073, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_app_loss_run_started_initial_profile"]}, {"time": 3071, "props": ["quic_persistent_congestion_declared"]}, {"time": 3073, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED_PROFILE`；Root review confirmed a no-early safety obligation under the explicitly frozen 1024 ms application-PTO profile; reinstantiate if live PTO differs.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This is a no-early-declaration safety oracle. Establishment also requires all relevant ack-eliciting packets in the duration to be declared lost.

## QUIC-PTO-01 — Initial handshake PTO is approximately one second

- 性质：ngtcp2 初始 profile 实际 arm 999 ms PTO generation 后，该 generation 不得提前到期，并须在 999 ms 到期或因新的 loss timer/ACK/key discard 重设而失效。
- 规范：[RFC 9002 RFC 9002 §6.2.1-6.2.2](https://www.rfc-editor.org/rfc/rfc9002.html#section-6.2.2)；强度 `SHOULD/MUST computation`；时间 `999..1000 ms`（`NORMATIVE_DERIVED_WITH_DOCUMENTED_ROUNDING`）。
- 规范短摘录：“the initial RTT SHOULD be set to 333 milliseconds”
- 数学 MITL：`G (quic_pto_armed_999ms_initial_profile -> (G [0,999) (!quic_pto_deadline_reached) && F [0,999] (quic_pto_deadline_reached || quic_pto_generation_superseded)))`
- MightyPPL（finite weak outer global）：`G* (quic_pto_armed_999ms_initial_profile -> (G [0,999) (!quic_pto_deadline_reached) && F [0,999] (quic_pto_deadline_reached || quic_pto_generation_superseded)))`
- AP：`quic_pto_armed_999ms_initial_profile, quic_pto_deadline_reached, quic_pto_generation_superseded`
- AP 定义：{"quic_pto_armed_999ms_initial_profile": "Loss detection actually selects PTO (not time-threshold loss) and arms a generation at 999 ms with pto_count=0.", "quic_pto_deadline_reached": "The absolute deadline for that exact PTO generation is reached.", "quic_pto_generation_superseded": "A qualifying ACK, later ack-eliciting send, key discard, or loss-timer replacement rearms/cancels that generation."}
- Correlation：connection object + Initial/Handshake packet-number space
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_conn.c:954-979`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L954-L979)；符号 `conn_compute_initial_pto`。
- 主源码映射 AP：`["quic_pto_armed_999ms_initial_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "default initial RTT profile constant", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/includes/ngtcp2/ngtcp2.h", "symbol": "NGTCP2_DEFAULT_INITIAL_RTT", "lines": "434-439", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/includes/ngtcp2/ngtcp2.h#L434-L439", "atomic_propositions": ["quic_pto_armed_999ms_initial_profile"]}, {"role": "PTO selection, arm, cancellation, and replacement", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "ngtcp2_conn_set_loss_detection_timer", "lines": "13427-13469", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L13427-L13469", "atomic_propositions": ["quic_pto_armed_999ms_initial_profile", "quic_pto_generation_superseded"]}, {"role": "loss-detection deadline dispatch", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "ngtcp2_conn_on_loss_detection_timer", "lines": "13478-13546", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L13478-L13546", "atomic_propositions": ["quic_pto_deadline_reached"]}]`
- Hook：Record the computed absolute loss_detection_timer and PTO inputs after ngtcp2_conn_set_loss_detection_timer.
- 正例 timed word：`[{"time": 0, "props": ["quic_pto_armed_999ms_initial_profile"]}, {"time": 999, "props": ["quic_pto_deadline_reached"]}, {"time": 1000, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_pto_armed_999ms_initial_profile"]}, {"time": 998, "props": ["quic_pto_deadline_reached"]}, {"time": 1000, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["quic_pto_armed_999ms_initial_profile"]}, {"time": 1000, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Obligation begins at the actual selected PTO arm and is cancelled by all RFC timer-supersession events.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The 999..1000 range is a documented arithmetic/narrative discrepancy, not an injected epsilon; resumed RTT profiles are outside scope.

## QUIC-PTO-02 — Consecutive PTO doubles after the first expiry

- 性质：pto_count=1 且默认 profile 实际按 1998 ms arm 下一 PTO generation 后，不得提前到期；须到期或被真正重置 backoff 的 ACK/重发事件替换。
- 规范：[RFC 9002 RFC 9002 §6.2.1](https://www.rfc-editor.org/rfc/rfc9002.html#section-6.2.1)；强度 `MUST`；时间 `1998 ms`（`NORMATIVE_DERIVED_IMPLEMENTATION_ARITHMETIC`）。
- 规范短摘录：“the PTO period being set to twice its current value”
- 数学 MITL：`G (quic_pto_backoff_armed_1998ms -> (G [0,1998) (!quic_second_pto_deadline_reached) && F [0,1998] (quic_second_pto_deadline_reached || quic_second_pto_superseded)))`
- MightyPPL（finite weak outer global）：`G* (quic_pto_backoff_armed_1998ms -> (G [0,1998) (!quic_second_pto_deadline_reached) && F [0,1998] (quic_second_pto_deadline_reached || quic_second_pto_superseded)))`
- AP：`quic_pto_backoff_armed_1998ms, quic_second_pto_deadline_reached, quic_second_pto_superseded`
- AP 定义：{"quic_pto_backoff_armed_1998ms": "After probe transmission pto_count=1 and the selected PTO generation is actually armed at 1998 ms.", "quic_second_pto_deadline_reached": "That exact backoff generation reaches its absolute deadline.", "quic_second_pto_superseded": "A later send/rearm or an ACK that RFC 9002 says resets PTO backoff replaces that exact generation."}
- Correlation：connection object + global PTO generation across packet-number spaces
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_conn.c:13387-13424`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L13387-L13424)；符号 `conn_get_earliest_pto_expiry`。
- 主源码映射 AP：`["quic_pto_backoff_armed_1998ms"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "PTO deadline, pto_count increment, and backoff rearm", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "ngtcp2_conn_on_loss_detection_timer", "lines": "13478-13546", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L13478-L13546", "atomic_propositions": ["quic_pto_backoff_armed_1998ms", "quic_second_pto_deadline_reached"]}, {"role": "backoff timer replacement or cancellation", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "ngtcp2_conn_set_loss_detection_timer", "lines": "13427-13469", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L13427-L13469", "atomic_propositions": ["quic_second_pto_superseded"]}]`
- Hook：Emit first completion after pto_count increments; emit second fire when ngtcp2_conn_on_loss_detection_timer enters the PTO branch again.
- 正例 timed word：`[{"time": 0, "props": ["quic_pto_backoff_armed_1998ms"]}, {"time": 1998, "props": ["quic_second_pto_deadline_reached"]}, {"time": 1999, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_pto_backoff_armed_1998ms"]}, {"time": 1997, "props": ["quic_second_pto_deadline_reached"]}, {"time": 1999, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["quic_pto_backoff_armed_1998ms"]}, {"time": 1999, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Trigger is actual pto_count=1 rearm; broad ACK discharge was replaced with generation-specific supersession.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Uses ngtcp2's exact 999 ms initial computation; implementations rounding the first PTO to 1000 ms need a separately declared 2000 ms profile.

## QUIC-PV-01 — Initial-profile path validation timeout is 2997 ms

- 性质：两个 PTO 快照均为 999 ms 且实际 arm 2997 ms path-validation generation 后，不得因 timeout 提前放弃；须在期限成功、timeout，或被新迁移/应用决策替换。
- 规范：[RFC 9000 RFC 9000 + RFC 9002 §8.2.4](https://www.rfc-editor.org/rfc/rfc9000.html#section-8.2.4)；强度 `RECOMMENDED`；时间 `2997 ms`（`NORMATIVE_RECOMMENDED_DERIVED_PROFILE`）。
- 规范短摘录：“three times the larger of the current PTO or the PTO”
- 数学 MITL：`G (quic_path_validation_armed_2997ms_profile -> (G [0,2997) (!quic_path_abandoned_by_timeout) && F [0,2997] (quic_path_validated || quic_path_abandoned_by_timeout || quic_path_validation_superseded)))`
- MightyPPL（finite weak outer global）：`G* (quic_path_validation_armed_2997ms_profile -> (G [0,2997) (!quic_path_abandoned_by_timeout) && F [0,2997] (quic_path_validated || quic_path_abandoned_by_timeout || quic_path_validation_superseded)))`
- AP：`quic_path_validation_armed_2997ms_profile, quic_path_validated, quic_path_abandoned_by_timeout, quic_path_validation_superseded`
- AP 定义：{"quic_path_validation_armed_2997ms_profile": "Path validation is actually armed at 3*max(999,999)=2997 ms with both PTO snapshots recorded.", "quic_path_validated": "Matching PATH_RESPONSE validates that path generation.", "quic_path_abandoned_by_timeout": "That generation is abandoned specifically because its validation deadline expires.", "quic_path_validation_superseded": "New migration/path challenge or explicit application decision replaces that generation."}
- Correlation：connection object + path tuple + PATH_CHALLENGE token stored only as correlation data
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[ngtcp2/ngtcp2@fcb5cdaba44a `lib/ngtcp2_conn.c:995-1012`](https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L995-L1012)；符号 `conn_compute_pv_timeout_pto`。
- 主源码映射 AP：`["quic_path_validation_armed_2997ms_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "path-validation object creation with timeout", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_pv.c", "symbol": "ngtcp2_pv_new", "lines": "46-68", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_pv.c#L46-L68", "atomic_propositions": ["quic_path_validation_armed_2997ms_profile"]}, {"role": "matching PATH_RESPONSE validation success", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_recv_path_response", "lines": "6161-6268", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L6161-L6268", "atomic_propositions": ["quic_path_validated"]}, {"role": "path-validation timeout abandonment", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_write_path_challenge", "lines": "5203-5232", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L5203-L5232", "atomic_propositions": ["quic_path_abandoned_by_timeout"]}, {"role": "migration/application replacement abort", "repository": "ngtcp2/ngtcp2", "commit": "fcb5cdaba44a8fb1c821319af306e3f38f18e738", "path": "lib/ngtcp2_conn.c", "symbol": "conn_abort_pv", "lines": "5117-5132", "url": "https://github.com/ngtcp2/ngtcp2/blob/fcb5cdaba44a8fb1c821319af306e3f38f18e738/lib/ngtcp2_conn.c#L5117-L5132", "atomic_propositions": ["quic_path_validation_superseded"]}]`
- Hook：Record the computed pv expiry when the validation object is created; emit success/abandon at matching response or expiry.
- 正例 timed word：`[{"time": 0, "props": ["quic_path_validation_armed_2997ms_profile"]}, {"time": 2997, "props": ["quic_path_abandoned_by_timeout"]}, {"time": 2998, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["quic_path_validation_armed_2997ms_profile"]}, {"time": 2996, "props": ["quic_path_abandoned_by_timeout"]}, {"time": 2998, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["quic_path_validation_armed_2997ms_profile"]}, {"time": 2998, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Separated timeout abandonment from supersession and bound the trigger to both PTO snapshots plus actual arm.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：RFC 9000 labels the 3*PTO value RECOMMENDED, not MUST; migration that supersedes an old validation attempt must be tagged as a non-timeout cancellation.
