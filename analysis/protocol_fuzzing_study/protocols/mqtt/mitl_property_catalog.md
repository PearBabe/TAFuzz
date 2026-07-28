# MQTT MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：3
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## MQTT-KA-01 — An idle default-profile client starts another control packet within 60 seconds

- 性质：在 Mosquitto 命令行客户端未覆盖 Keep Alive 的固定 profile 中，值为 60 s。客户端完成一个 MQTT 控制报文后，若连接继续存活，必须在 60000 ms 内开始下一个控制报文；没有其他控制报文时应发送 PINGREQ。
- 规范：[MQTT Version 5.0 OASIS Standard 07 March 2019 §3.1.2.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html#_Keep_Alive_1)；强度 `MUST`；时间 `60000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“in the absence of sending any other MQTT Control Packets, the Client MUST send a PINGREQ packet”
- 数学 MITL：`G (mqtt_client_outbound_window_started -> F [0,60000] (mqtt_pingreq_started || mqtt_other_control_packet_started || mqtt_network_connection_closed))`
- MightyPPL（finite weak outer global）：`G* (mqtt_client_outbound_window_started -> F [0,60000] (mqtt_pingreq_started || mqtt_other_control_packet_started || mqtt_network_connection_closed))`
- AP：`mqtt_client_outbound_window_started, mqtt_pingreq_started, mqtt_other_control_packet_started, mqtt_network_connection_closed`
- AP 定义：{"mqtt_client_outbound_window_started": "The profiled client finishes transmitting one MQTT Control Packet on an active connection and commits next_msg_out for Keep Alive 60.", "mqtt_pingreq_started": "The first byte of a PINGREQ for the correlated client connection starts transmission.", "mqtt_other_control_packet_started": "The first byte of a non-PINGREQ MQTT Control Packet for that connection starts transmission.", "mqtt_network_connection_closed": "The correlated connection generation transitions from connected to inactive at net__socket_close; a broker Keep Alive reason, when present, is retained as an event field."}
- Correlation：Mosquitto client instance + network-connection generation + direction; the fixed profile requires effective Keep Alive=60
- 投影：select one active connection generation with the fixed default profile, order completed and newly started outbound packets, then project the fixed AP alphabet
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eclipse-mosquitto/mosquitto@672ae3e57f8b `lib/packet_mosq.c:227-358`](https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/packet_mosq.c#L227-L358)；符号 `packet__write`。
- 主源码映射 AP：`["mqtt_client_outbound_window_started", "mqtt_pingreq_started", "mqtt_other_control_packet_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "Keep Alive scheduling eligibility", "path": "lib/util_mosq.c", "symbol": "mosquitto__check_keepalive", "lines": "62-143", "atomic_propositions": ["mqtt_client_outbound_window_started", "mqtt_pingreq_started"], "url": "https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/util_mosq.c#L62-L143"}, {"role": "network connection generation close", "path": "lib/net_mosq.c", "symbol": "net__socket_close", "lines": "214-267", "atomic_propositions": ["mqtt_network_connection_closed"], "url": "https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/net_mosq.c#L214-L267"}]`
- Hook：emit the trigger after packet completion updates next_msg_out; emit a start AP when the first byte is handed to the socket, or close after the connection state changes
- 正例 timed word：`[{"time": 0, "props": ["mqtt_client_outbound_window_started"]}, {"time": 60000, "props": ["mqtt_pingreq_started"]}, {"time": 60001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["mqtt_client_outbound_window_started"]}, {"time": 60001, "props": []}]`
- 附加反例：`{"late_or_missing_next_control_packet": [{"time": 0, "props": ["mqtt_client_outbound_window_started"]}, {"time": 60001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["mqtt_client_outbound_window_started"]}, {"time": 60001, "props": []}]}`
- 独立审计：`ROOT_REVIEWED`；Root review confirmed the implementation-profile scope, effective-Keep-Alive correlation, and that the existing negative trace covers the late/missing eventuality case.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：60 s 不是 MQTT 通用常数；API 调用、命令行选项或 Server Keep Alive 都可改变有效值，因此该条仅适用于明确锁定的默认 profile。negative 与命名附加反例均覆盖截止后仍缺少后继控制报文或关闭的 late/missing 情形。

## MQTT-KA-02 — The broker receives a control packet or closes by the 90-second Keep Alive deadline

- 性质：对有效 Keep Alive=60 s 的固定连接 profile，服务器从客户端最后一个 MQTT 控制报文接收完成起，若 90000 ms 内没有收到下一个控制报文，必须关闭该网络连接。
- 规范：[MQTT Version 5.0 OASIS Standard 07 March 2019 §3.1.2.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html#_Keep_Alive_1)；强度 `MUST`；时间 `90000 ms`（`IMPLEMENTATION_PROFILE_DERIVED`）。
- 规范短摘录：“within one and a half times the Keep Alive time period, it MUST close the Network Connection”
- 数学 MITL：`G (mqtt_server_inbound_window_started -> F [0,90000] (mqtt_client_control_packet_received || mqtt_network_connection_closed))`
- MightyPPL（finite weak outer global）：`G* (mqtt_server_inbound_window_started -> F [0,90000] (mqtt_client_control_packet_received || mqtt_network_connection_closed))`
- AP：`mqtt_server_inbound_window_started, mqtt_client_control_packet_received, mqtt_network_connection_closed`
- AP 定义：{"mqtt_server_inbound_window_started": "Mosquitto finishes receiving a valid MQTT Control Packet for an active non-bridge client and refreshes last_msg_in with effective Keep Alive 60.", "mqtt_client_control_packet_received": "A later valid MQTT Control Packet from that client is completely received and refreshes the same connection's Keep Alive state.", "mqtt_network_connection_closed": "The correlated connection generation transitions from connected to inactive at net__socket_close; a broker Keep Alive reason, when present, is retained as an event field."}
- Correlation：broker listener + client identity + network-connection generation + inbound direction; effective Keep Alive=60
- 投影：derive the effective Keep Alive after CONNECT/CONNACK negotiation, select one non-bridge connection generation, then project refresh, receive, and close events
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eclipse-mosquitto/mosquitto@672ae3e57f8b `lib/packet_mosq.c:361-589`](https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/packet_mosq.c#L361-L589)；符号 `packet__read`。
- 主源码映射 AP：`["mqtt_server_inbound_window_started", "mqtt_client_control_packet_received"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "broker Keep Alive expiry decision", "path": "src/keepalive.c", "symbol": "keepalive__check", "lines": "127-175", "atomic_propositions": ["mqtt_network_connection_closed"], "url": "https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/src/keepalive.c#L127-L175"}, {"role": "network connection generation close", "path": "lib/net_mosq.c", "symbol": "net__socket_close", "lines": "214-267", "atomic_propositions": ["mqtt_network_connection_closed"], "url": "https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/net_mosq.c#L214-L267"}]`
- Hook：emit the trigger after last_msg_in is refreshed; emit receive after the next valid packet refresh, and emit close after do_disconnect changes the connection state
- 正例 timed word：`[{"time": 0, "props": ["mqtt_server_inbound_window_started"]}, {"time": 90000, "props": ["mqtt_network_connection_closed"]}, {"time": 90001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["mqtt_server_inbound_window_started"]}, {"time": 90001, "props": []}]`
- 附加反例：`{"late_or_missing_receive_or_close": [{"time": 0, "props": ["mqtt_server_inbound_window_started"]}, {"time": 90001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["mqtt_server_inbound_window_started"]}, {"time": 90001, "props": []}]}`
- 独立审计：`ROOT_REVIEWED`；Root review confirmed the 1.5 multiplier and fixed effective-60-second profile; the exact time-wheel boundary remains an explicit implementation oracle, with a late/missing negative trace.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：该固定数值依赖 Keep Alive=60 的 profile；Mosquitto 的秒级时间轮和主循环调度可能暴露边界延后，这正是该 oracle 要检测的实现行为。negative 与命名附加反例均覆盖 90000 ms 后仍未接收或关闭的 late/missing 情形。

## MQTT-RTX-01 — A PUBLISH negatively acknowledged with reason code 0x80 or greater is never retransmitted

- 性质：收到 Reason Code 大于等于 0x80 的 PUBACK 或 PUBREC 后，对应 PUBLISH 被视为已确认；在该消息 generation 的剩余生命周期内不得再次重传。
- 规范：[MQTT Version 5.0 OASIS Standard 07 March 2019 §4.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html#_Message_delivery_retry)；强度 `MUST NOT`；时间 `unbounded ms`（`NORMATIVE_UNBOUNDED`）。
- 规范短摘录：“the corresponding PUBLISH packet is treated as acknowledged, and MUST NOT be retransmitted”
- 数学 MITL：`G (mqtt_publish_negative_ack_received -> G (!mqtt_same_publish_retransmitted))`
- MightyPPL（finite weak outer global）：`G* (mqtt_publish_negative_ack_received -> G* (!mqtt_same_publish_retransmitted))`
- AP：`mqtt_publish_negative_ack_received, mqtt_same_publish_retransmitted`
- AP 定义：{"mqtt_publish_negative_ack_received": "A valid PUBACK or PUBREC with Reason Code at least 0x80 matches an active outbound PUBLISH generation by Packet Identifier and removes or completes its stored state.", "mqtt_same_publish_retransmitted": "The sender starts another PUBLISH for that same stored message generation; a later legitimate Packet Identifier reuse for new content is not the same generation."}
- Correlation：client/broker role + network-session generation + outbound direction + Packet Identifier + stored-message generation + QoS
- 投影：match PUBACK/PUBREC to the active stored PUBLISH before projection and retain its generation identity after deletion so Packet Identifier reuse is not conflated
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eclipse-mosquitto/mosquitto@672ae3e57f8b `lib/handle_pubrec.c:93-125`](https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/handle_pubrec.c#L93-L125)；符号 `handle__pubrec`。
- 主源码映射 AP：`["mqtt_publish_negative_ack_received"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "negative PUBACK state completion", "path": "lib/handle_pubackcomp.c", "symbol": "handle__pubackcomp", "lines": "41-168", "atomic_propositions": ["mqtt_publish_negative_ack_received"], "url": "https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/handle_pubackcomp.c#L41-L168"}, {"role": "later PUBLISH send for retained message generation", "path": "lib/send_publish.c", "symbol": "send__publish / send__real_publish", "lines": "42-134;137-221", "atomic_propositions": ["mqtt_same_publish_retransmitted"], "url": "https://github.com/eclipse-mosquitto/mosquitto/blob/672ae3e57f8b4e086f6ce2dec836734cc38258c3/lib/send_publish.c#L42-L134"}]`
- Hook：emit the trigger only after reason validation and successful message-state deletion; emit retransmission at the first byte of a later send for the retained generation identity
- 正例 timed word：`[{"time": 0, "props": ["mqtt_publish_negative_ack_received"]}, {"time": 1000, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["mqtt_publish_negative_ack_received"]}, {"time": 1, "props": ["mqtt_same_publish_retransmitted"]}, {"time": 1000, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED`；Root review confirmed negative PUBACK/PUBREC generation matching, state deletion evidence, and the weak-finite terminal-projection caveat for the unbounded safety check.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：该义务无有限截止时间；有限词通过仅代表观察窗口内未重传，采集终点应覆盖 stored-message generation 的完整生命周期。
