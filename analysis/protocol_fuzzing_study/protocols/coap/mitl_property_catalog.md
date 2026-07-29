# CoAP MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：7
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## COAP-MCAST-01 — A committed multicast response is sent within the five-second default leisure

- 性质：服务器已经决定响应 multicast 请求、又没有可用于计算 Leisure 的数据时，libcoap 默认 profile 在 0--5000 ms 的 DEFAULT_LEISURE 内选择随机时刻发送单播响应。
- 规范：[RFC 7252 RFC 7252 (June 2014) §8.2; 4.8](https://www.rfc-editor.org/rfc/rfc7252.html#section-8.2)；强度 `SHOULD with MAY default`；时间 `5000 ms`（`NORMATIVE_DEFAULT_PROFILE`）。
- 规范短摘录：“The server SHOULD then pick a random point of time within the chosen leisure period”
- 数学 MITL：`G (coap_multicast_response_committed_default_leisure -> F [0,5000] (coap_multicast_response_sent))`
- MightyPPL（finite weak outer global）：`G* (coap_multicast_response_committed_default_leisure -> F [0,5000] (coap_multicast_response_sent))`
- AP：`coap_multicast_response_committed_default_leisure, coap_multicast_response_sent`
- AP 定义：{"coap_multicast_response_committed_default_leisure": "The request arrived via multicast, the resource handler committed a response, delay suppression is off, and the default leisure queue path is selected.", "coap_multicast_response_sent": "The queued unicast response for that requester token and responder endpoint is successfully written."}
- Correlation：incoming multicast request token + responder local endpoint + request generation + response queue node
- 投影：correlate the committed response to one multicast request and responder before projecting; tokens and addresses remain fields
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:3552-3604`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L3552-L3604)；符号 `handle_request`。
- 主源码映射 AP：`["coap_multicast_response_committed_default_leisure"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "delayed multicast response send", "path": "src/coap_net.c", "symbol": "coap_retransmit", "lines": "1908-1969", "atomic_propositions": ["coap_multicast_response_sent"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1908-L1969"}]`
- Hook：emit the trigger after the random delay is stored and coap_wait_ack inserts the multicast node; emit sent after the delayed write succeeds
- 正例 timed word：`[{"time": 0, "props": ["coap_multicast_response_committed_default_leisure"]}, {"time": 4000, "props": ["coap_multicast_response_sent"]}, {"time": 5001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_multicast_response_committed_default_leisure"]}, {"time": 5001, "props": []}]`
- 附加反例：`{"late_or_missing_response": [{"time": 0, "props": ["coap_multicast_response_committed_default_leisure"]}, {"time": 5001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["coap_multicast_response_committed_default_leisure"]}, {"time": 5001, "props": []}]}`
- 独立审计：`ROOT_REVIEWED`；Root review confirmed the property is limited to the default-leisure delayed-response path and that its existing negative trace is the late/missing eventuality case.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `MEDIUM` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：规范允许应用计算其他 Leisure；本条只覆盖 RFC 默认值和固定 libcoap 默认 delayed-response 路径。negative 与命名附加反例均覆盖 5000 ms 后仍缺少发送的 late/missing 情形。

## COAP-MID-01 — A Message ID is not reused within 247 seconds

- 性质：默认 EXCHANGE_LIFETIME=247000 ms；同一通信端点对中的 Message ID 在首次使用后的该开放窗口内不得再次用于新的 CON 或 NON 消息。
- 规范：[RFC 7252 RFC 7252 (June 2014) §4.4; 4.8.2](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.4)；强度 `MUST NOT`；时间 `247000 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“The same Message ID MUST NOT be reused (in communicating with the same endpoint) within the EXCHANGE_LIFETIME”
- 数学 MITL：`G (coap_mid_first_used -> G [0,247000) (!coap_same_mid_reused))`
- MightyPPL（finite weak outer global）：`G* (coap_mid_first_used -> G [0,247000) (!coap_same_mid_reused))`
- AP：`coap_mid_first_used, coap_same_mid_reused`
- AP 定义：{"coap_mid_first_used": "A new outbound CON or NON generation first uses the tracked Message ID for one fixed local/remote endpoint pair.", "coap_same_mid_reused": "A distinct outbound message generation uses that same Message ID with the same endpoint pair before the window ends."}
- Correlation：local IP/port + remote IP/port + transport protocol + 16-bit Message ID; message generation distinguishes reuse from retransmission
- 投影：group by endpoint pair and Message ID, classify retransmissions as the existing generation, then project first-use/reuse APs
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:1014-1050`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1014-L1050)；符号 `coap_send_pdu`。
- 主源码映射 AP：`["coap_mid_first_used", "coap_same_mid_reused"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "Message ID allocation prerequisite", "path": "src/coap_session.c", "symbol": "coap_new_message_id_lkd", "lines": "1909-1915", "atomic_propositions": ["coap_mid_first_used", "coap_same_mid_reused"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_session.c#L1909-L1915"}]`
- Hook：emit after a newly allocated MID is attached to a first-send PDU; the adapter retains endpoint-pair MID history for 247000 ms
- 正例 timed word：`[{"time": 0, "props": ["coap_mid_first_used"]}, {"time": 247000, "props": ["coap_same_mid_reused"]}, {"time": 247001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_mid_first_used"]}, {"time": 246999, "props": ["coap_same_mid_reused"]}, {"time": 247001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED_WITH_ADAPTER_CAVEAT`；Root review accepts the RFC obligation and allocator hook, with the explicit caveat that 247-second endpoint-pair history and generation classification are supplied by the observation adapter rather than libcoap retention code.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：固定源码仅展示每会话递增分配点；247 秒历史保持与 endpoint-pair generation 分类属于观测适配器职责。

## COAP-TX-01 — Initial Confirmable retransmission timeout is between two and three seconds

- 性质：在 RFC 7252 默认参数 ACK_TIMEOUT=2 s、ACK_RANDOM_FACTOR=1.5 下，CON 进入等待 ACK/RST 状态后，首次重传计时器不得早于 2000 ms，到 3000 ms 前应到期，除非匹配 ACK/RST 或显式取消已解除该义务。
- 规范：[RFC 7252 RFC 7252 (June 2014) §4.2; 4.8](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.2)；强度 `NORMATIVE PROCEDURE`；时间 `2000-3000 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“the initial timeout is set to a random duration”
- 数学 MITL：`G (coap_con_wait_started -> (G [0,2000) (!coap_first_retransmit_deadline_reached) && F [0,3000] (coap_first_retransmit_deadline_reached || coap_matching_ack_or_reset_received || coap_attempt_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (coap_con_wait_started -> (G [0,2000) (!coap_first_retransmit_deadline_reached) && F [0,3000] (coap_first_retransmit_deadline_reached || coap_matching_ack_or_reset_received || coap_attempt_cancelled)))`
- AP：`coap_con_wait_started, coap_first_retransmit_deadline_reached, coap_matching_ack_or_reset_received, coap_attempt_cancelled`
- AP 定义：{"coap_con_wait_started": "The initial CON PDU is sent and its per-exchange retransmission node is inserted into the send queue.", "coap_first_retransmit_deadline_reached": "Monotonic time reaches the absolute first-retransmission deadline stored for this queue-node generation, independently of when the callback is dispatched.", "coap_matching_ack_or_reset_received": "coap_dispatch receives an ACK or RST whose endpoint and Message ID match the current exchange, and coap_remove_from_queue removes that exact queue-node generation.", "coap_attempt_cancelled": "An allowed non-ACK/RST local cancellation path removes the current queue-node generation before its stored deadline."}
- Correlation：local endpoint + remote endpoint + transport protocol + Message ID + queue-node generation
- 投影：correlate one CON exchange before projection; endpoint and Message ID values remain event fields and never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:1123-1180;1883-1901`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1123-L1180)；符号 `coap_calc_timeout / coap_wait_ack / coap_send_internal`。
- 主源码映射 AP：`["coap_con_wait_started", "coap_first_retransmit_deadline_reached"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "matching ACK/RST queue removal", "path": "src/coap_net.c", "symbol": "coap_dispatch", "lines": "3983-3993;4128-4133", "atomic_propositions": ["coap_matching_ack_or_reset_received"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L3983-L3993"}, {"role": "explicit local exchange cancellation", "path": "src/coap_net.c", "symbol": "coap_cancel_session_messages / coap_cancel_all_messages", "lines": "2573-2613;2616-2646", "atomic_propositions": ["coap_attempt_cancelled"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L2573-L2613"}]`
- Hook：emit the trigger after the node timeout and absolute queue deadline are committed; emit deadline-reached when monotonic time crosses that stored absolute deadline, not when the event-loop callback runs; emit discharge after queue removal
- 正例 timed word：`[{"time": 0, "props": ["coap_con_wait_started"]}, {"time": 2500, "props": ["coap_first_retransmit_deadline_reached"]}, {"time": 3001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_con_wait_started"]}, {"time": 1999, "props": ["coap_first_retransmit_deadline_reached"]}, {"time": 3001, "props": []}]`
- 附加反例：`{"late_or_missing_deadline": [{"time": 0, "props": ["coap_con_wait_started"]}, {"time": 3001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["coap_con_wait_started"]}, {"time": 3001, "props": []}]}`
- 独立审计：`ROOT_REVIEWED`；Root review required the bounded result to be the stored absolute deadline crossing, not callback dispatch, and confirmed early plus late/missing counterexamples.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：RFC 7252 允许实际发送因节点调度而变晚；本性质核对已存储绝对期限的到达窗口，callback 与实际报文发送分别作为诊断和 MAX_TRANSMIT_SPAN 观测。

## COAP-TX-02 — The second retransmission timeout lies between four and six seconds

- 性质：默认初始随机超时位于 2000--3000 ms；第一次重传完成后，计时器翻倍，所以第二次重传计时器不得早于 4000 ms，并应在 6000 ms 内到期或被 ACK/RST/取消解除。
- 规范：[RFC 7252 RFC 7252 (June 2014) §4.2; 4.8](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.2)；强度 `NORMATIVE PROCEDURE`；时间 `4000-6000 ms`（`NORMATIVE_DERIVED`）。
- 规范短摘录：“the message is retransmitted, the retransmission counter is incremented, and the timeout is doubled”
- 数学 MITL：`G (coap_first_retransmission_completed -> (G [0,4000) (!coap_second_retransmit_deadline_reached) && F [0,6000] (coap_second_retransmit_deadline_reached || coap_matching_ack_or_reset_received || coap_attempt_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (coap_first_retransmission_completed -> (G [0,4000) (!coap_second_retransmit_deadline_reached) && F [0,6000] (coap_second_retransmit_deadline_reached || coap_matching_ack_or_reset_received || coap_attempt_cancelled)))`
- AP：`coap_first_retransmission_completed, coap_second_retransmit_deadline_reached, coap_matching_ack_or_reset_received, coap_attempt_cancelled`
- AP 定义：{"coap_first_retransmission_completed": "The first retransmission for the correlated CON is written and retransmit_cnt becomes 1 before the next deadline is queued.", "coap_second_retransmit_deadline_reached": "Monotonic time reaches the next absolute deadline stored for the same queue-node generation after retransmit_cnt becomes 1, independently of callback dispatch.", "coap_matching_ack_or_reset_received": "coap_dispatch receives an ACK or RST whose endpoint and Message ID match the current exchange, and coap_remove_from_queue removes that exact queue-node generation.", "coap_attempt_cancelled": "An allowed non-ACK/RST local cancellation path removes the current queue-node generation before its stored deadline."}
- Correlation：local endpoint + remote endpoint + transport protocol + Message ID + queue-node generation + retransmit_cnt
- 投影：correlate one CON exchange and derive the cycle index from retransmit_cnt before projecting the fixed AP alphabet
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:1908-1969`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1908-L1969)；符号 `coap_retransmit`。
- 主源码映射 AP：`["coap_first_retransmission_completed", "coap_second_retransmit_deadline_reached"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "matching ACK/RST queue removal", "path": "src/coap_net.c", "symbol": "coap_dispatch", "lines": "3983-3993;4128-4133", "atomic_propositions": ["coap_matching_ack_or_reset_received"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L3983-L3993"}, {"role": "explicit local exchange cancellation", "path": "src/coap_net.c", "symbol": "coap_cancel_session_messages / coap_cancel_all_messages", "lines": "2573-2613;2616-2646", "atomic_propositions": ["coap_attempt_cancelled"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L2573-L2613"}]`
- Hook：emit the trigger after retransmit_cnt increments and the next absolute deadline is committed; emit deadline-reached when monotonic time crosses that stored value, not when the callback runs
- 正例 timed word：`[{"time": 0, "props": ["coap_first_retransmission_completed"]}, {"time": 5000, "props": ["coap_second_retransmit_deadline_reached"]}, {"time": 6001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_first_retransmission_completed"]}, {"time": 3999, "props": ["coap_second_retransmit_deadline_reached"]}, {"time": 6001, "props": []}]`
- 附加反例：`{"late_or_missing_deadline": [{"time": 0, "props": ["coap_first_retransmission_completed"]}, {"time": 6001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["coap_first_retransmission_completed"]}, {"time": 6001, "props": []}]}`
- 独立审计：`ROOT_REVIEWED`；Root review confirmed the second-cycle absolute deadline semantics and required a late/missing counterexample in addition to the early one.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：公式验证默认参数下第二周期绝对期限的合法包络；初始随机值与后续精确二倍关系仍需由同一 queue node 的 timeout 字段关联核对。

## COAP-TX-03 — After the fourth retransmission the final wait deadline is reached without a fifth send

- 性质：默认 MAX_RETRANSMIT=4。第四次重传完成后不得再发送第五次重传；若没有匹配 ACK/RST 或显式取消，该 generation 的 final-wait 绝对期限应在 32000--48000 ms 内到达，随后失败 callback 仅作为诊断动作记录。
- 规范：[RFC 7252 RFC 7252 (June 2014) §4.2; 4.8](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.2)；强度 `NORMATIVE PROCEDURE`；时间 `32000-48000 ms`（`NORMATIVE_DERIVED`）。
- 规范短摘录：“the attempt to transmit the message is canceled and the application process informed of failure”
- 数学 MITL：`G (coap_fourth_retransmission_completed -> (G [0,32000) (!coap_final_wait_deadline_reached) && F [0,48000] (coap_final_wait_deadline_reached || coap_matching_ack_or_reset_received || coap_attempt_cancelled) && G (!coap_fifth_retransmission_sent)))`
- MightyPPL（finite weak outer global）：`G* (coap_fourth_retransmission_completed -> (G [0,32000) (!coap_final_wait_deadline_reached) && F [0,48000] (coap_final_wait_deadline_reached || coap_matching_ack_or_reset_received || coap_attempt_cancelled) && G* (!coap_fifth_retransmission_sent)))`
- AP：`coap_fourth_retransmission_completed, coap_final_wait_deadline_reached, coap_matching_ack_or_reset_received, coap_attempt_cancelled, coap_fifth_retransmission_sent`
- AP 定义：{"coap_fourth_retransmission_completed": "The correlated CON has just been retransmitted with retransmit_cnt incremented to 4 and its final wait is queued.", "coap_final_wait_deadline_reached": "Monotonic time reaches the absolute final-wait deadline stored after retransmit_cnt becomes 4, before any event-loop dispatch or nack callback completion.", "coap_matching_ack_or_reset_received": "coap_dispatch receives an ACK or RST whose endpoint and Message ID match the current exchange, and coap_remove_from_queue removes that exact queue-node generation.", "coap_attempt_cancelled": "An allowed non-ACK/RST local cancellation path removes the current queue-node generation before its stored deadline.", "coap_fifth_retransmission_sent": "A fifth network send is performed for the same queue-node generation; this must remain false."}
- Correlation：local endpoint + remote endpoint + transport protocol + Message ID + queue-node generation + retransmit_cnt
- 投影：retain one exchange through its stored final-wait deadline and subsequent diagnostic action; a later legitimate reuse of the Message ID starts a new generation
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:1908-2007`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1908-L2007)；符号 `coap_retransmit`。
- 主源码映射 AP：`["coap_fourth_retransmission_completed", "coap_final_wait_deadline_reached", "coap_fifth_retransmission_sent"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "matching ACK/RST queue removal", "path": "src/coap_net.c", "symbol": "coap_dispatch", "lines": "3983-3993;4128-4133", "atomic_propositions": ["coap_matching_ack_or_reset_received"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L3983-L3993"}, {"role": "explicit local exchange cancellation", "path": "src/coap_net.c", "symbol": "coap_cancel_session_messages / coap_cancel_all_messages", "lines": "2573-2613;2616-2646", "atomic_propositions": ["coap_attempt_cancelled"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L2573-L2613"}]`
- Hook：emit the trigger after retransmit_cnt becomes 4 and the final absolute deadline is committed; emit deadline-reached when monotonic time crosses it; separately record the later COAP_NACK_TOO_MANY_RETRIES callback as a diagnostic Boolean, not as the bounded result
- 正例 timed word：`[{"time": 0, "props": ["coap_fourth_retransmission_completed"]}, {"time": 40000, "props": ["coap_final_wait_deadline_reached"]}, {"time": 48001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_fourth_retransmission_completed"]}, {"time": 32000, "props": ["coap_fifth_retransmission_sent"]}, {"time": 40000, "props": ["coap_final_wait_deadline_reached"]}, {"time": 48001, "props": []}]`
- 附加反例：`{"early_deadline": [{"time": 0, "props": ["coap_fourth_retransmission_completed"]}, {"time": 31999, "props": ["coap_final_wait_deadline_reached"]}, {"time": 48001, "props": []}], "late_or_missing_deadline": [{"time": 0, "props": ["coap_fourth_retransmission_completed"]}, {"time": 48001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["coap_fourth_retransmission_completed"]}, {"time": 48001, "props": []}]}`
- 独立审计：`ROOT_REVIEWED`；Root review replaced callback completion with the final absolute deadline, preserved the no-fifth-send safety oracle, and required early plus late/missing deadline counterexamples.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：32000--48000 ms 是默认随机初值的派生范围；COAP_NACK_TOO_MANY_RETRIES callback 仅作为期限到达后的诊断布尔，不参与有界结果；本条不机械展开其他周期。

## COAP-TX-04 — All retransmissions stay inside the 45-second transmit span

- 性质：使用 RFC 7252 默认传输参数时，同一 CON 的最后一次重传最晚可在初次发送后 45000 ms 发生；45000 ms 之后不得再重传该交换。
- 规范：[RFC 7252 RFC 7252 (June 2014) §4.2; 4.8.2](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.8.2)；强度 `MUST`；时间 `45000 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“the entire sequence of (re-)transmissions MUST stay in the envelope of MAX_TRANSMIT_SPAN”
- 数学 MITL：`G (coap_con_initial_sent -> G (45000,infty) (!coap_same_con_retransmitted))`
- MightyPPL（finite weak outer global）：`G* (coap_con_initial_sent -> G (45000,infty) (!coap_same_con_retransmitted))`
- AP：`coap_con_initial_sent, coap_same_con_retransmitted`
- AP 定义：{"coap_con_initial_sent": "The first datagram of one correlated Confirmable exchange is successfully written.", "coap_same_con_retransmitted": "coap_send_pdu successfully writes a later datagram for the same queue-node generation and Message ID."}
- Correlation：local endpoint + remote endpoint + transport protocol + Message ID + queue-node generation
- 投影：correlate all wire sends to one queue-node generation before projection; do not merge a later Message ID reuse
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:1855-1969`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1855-L1969)；符号 `coap_send_internal / coap_retransmit`。
- 主源码映射 AP：`["coap_con_initial_sent", "coap_same_con_retransmitted"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "MAX_TRANSMIT_SPAN implementation expression", "path": "include/coap3/coap_session_internal.h", "symbol": "COAP_MAX_TRANSMIT_SPAN", "lines": "618-628", "atomic_propositions": ["coap_con_initial_sent"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/include/coap3/coap_session_internal.h#L618-L628"}]`
- Hook：timestamp each successful coap_send_pdu completion and retain the queue-node generation until ACK/RST/cancel/failure
- 正例 timed word：`[{"time": 0, "props": ["coap_con_initial_sent"]}, {"time": 45000, "props": ["coap_same_con_retransmitted"]}, {"time": 45001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_con_initial_sent"]}, {"time": 45001, "props": ["coap_same_con_retransmitted"]}, {"time": 45002, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED`；Root review moved the primary source mapping to the actual initial and retransmission send hooks and retained the MAX_TRANSMIT_SPAN macro as additional evidence.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：有限词的 POSITIVE 只说明给定观察词内没有越界重传；实际采集必须持续到交换结束或声明的终止观察点。45 s 常数定义保留为额外源码证据，主映射使用真实 initial/retransmit send hooks。

## COAP-TX-05 — A matching ACK or Reset stops retransmission

- 性质：发送端收到与活动 CON 匹配的 ACK 或 RST 后，该 queue-node generation 的重传序列结束，之后不得再次发送同一交换。
- 规范：[RFC 7252 RFC 7252 (June 2014) §4.2](https://www.rfc-editor.org/rfc/rfc7252.html#section-4.2)；强度 `NORMATIVE PROCEDURE`；时间 `unbounded ms`（`NORMATIVE_UNBOUNDED`）。
- 规范短摘录：“until it receives an acknowledgement (or Reset message) or runs out of attempts”
- 数学 MITL：`G (coap_matching_ack_or_reset_received -> G (!coap_same_con_retransmitted))`
- MightyPPL（finite weak outer global）：`G* (coap_matching_ack_or_reset_received -> G* (!coap_same_con_retransmitted))`
- AP：`coap_matching_ack_or_reset_received, coap_same_con_retransmitted`
- AP 定义：{"coap_matching_ack_or_reset_received": "coap_dispatch receives an ACK or RST whose endpoint and Message ID match the current exchange, and coap_remove_from_queue removes that exact queue-node generation.", "coap_same_con_retransmitted": "coap_send_pdu successfully writes a later datagram for the same queue-node generation and Message ID."}
- Correlation：local endpoint + remote endpoint + transport protocol + Message ID + queue-node generation
- 投影：match the ACK/RST to an active sendqueue node first, then keep only events for that node generation through the terminal observation
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[obgm/libcoap@7cf7465b784b `src/coap_net.c:3983-3993;4089-4139`](https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L3983-L3993)；符号 `coap_dispatch`。
- 主源码映射 AP：`["coap_matching_ack_or_reset_received"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "subsequent send for the same queue-node generation", "path": "src/coap_net.c", "symbol": "coap_retransmit", "lines": "1908-1969", "atomic_propositions": ["coap_same_con_retransmitted"], "url": "https://github.com/obgm/libcoap/blob/7cf7465b784baded4de183290c547d582becfd28/src/coap_net.c#L1908-L1969"}]`
- Hook：emit ACK/RST only after coap_remove_from_queue returns the matching node; mark that generation closed before any later send event is projected
- 正例 timed word：`[{"time": 0, "props": ["coap_matching_ack_or_reset_received"]}, {"time": 5000, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["coap_matching_ack_or_reset_received"]}, {"time": 1, "props": ["coap_same_con_retransmitted"]}, {"time": 5000, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED`；Root review confirmed ACK/RST discharge is emitted only after active-node matching and that finite weak monitoring must end with the correlated generation lifecycle.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：该义务没有有限协议截止时间；有限词通过仅是该词上的判定，采集终点必须与 queue-node generation 的生命周期一致。
