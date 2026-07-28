# SMTP MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：7
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## SMTP-TIMEOUT-01 — Initial 220 timeout is not shorter than five minutes

- 性质：TCP 连接建立后等待初始 220 greeting 时，SMTP 客户端不应在 300000 ms 前因该阶段超时而放弃。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.1](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.1)；强度 `SHOULD minimum`；时间 `300000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM_AND_IMPLEMENTATION_DEFAULT`）。
- 规范短摘录：“Initial 220 Message: 5 Minutes”
- 数学 MITL：`G (smtp_waiting_initial_220 -> G [0,300000) (!smtp_initial_220_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_waiting_initial_220 -> G [0,300000) (!smtp_initial_220_timeout))`
- AP：`smtp_waiting_initial_220, smtp_initial_220_timeout`
- AP 定义：{"smtp_waiting_initial_220": "smtp_connect returns a valid socket in smtp_setup_conn, opening one correlated initial-220 obligation before the later smtp_read_response call", "smtp_initial_220_timeout": "the initial-greeting smtp_read_response returns false with errno==ETIMEDOUT for that same connection before a valid initial 220 response"}
- Correlation：outbound SMTP connection identity + remote host/address + delivery attempt
- 投影：one successful-connect/initial-greeting obligation per timed word; a greeting, peer close, non-timeout I/O error, or delivery-attempt teardown closes only that generation; identifiers remain fields
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; correlate the successful connect to its initial smtp_read_response outcome before projection
- 源码：[Exim/exim@38903fb5b864 `src/src/transports/smtp.c:1544-1643;2095-2099`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L1544-L1643)；符号 `smtp_setup_conn`。
- 主源码映射 AP：`["smtp_waiting_initial_220"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "response reader and errno propagation", "path": "src/src/smtp_out.c", "symbol": "read_response_line/smtp_read_response", "lines": "457-520;548-608", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L457-L520", "atomic_propositions": ["smtp_initial_220_timeout"]}, {"role": "absolute read deadline and ETIMEDOUT", "path": "src/src/ip.c", "symbol": "fd_ready/ip_recv", "lines": "478-524;548-570", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L478-L524", "atomic_propositions": ["smtp_initial_220_timeout"]}, {"role": "SMTP timeout classification", "path": "src/src/transports/smtp.c", "symbol": "check_response", "lines": "508-525", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L508-L525", "atomic_propositions": ["smtp_initial_220_timeout"]}, {"role": "fixed timeout profile", "path": "src/src/transports/smtp.c", "symbol": "smtp_transport_option_defaults", "lines": "189-225", "atomic_propositions": ["smtp_waiting_initial_220"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L189-L225"}]`
- Hook：emit start once after successful smtp_connect; after the initial smtp_read_response returns false, inspect errno and emit timeout only for ETIMEDOUT before the RESPONSE_FAILED jump; use smtp_transport_option_defaults:222 as profile evidence
- 正例 timed word：`[{"time": 0, "props": ["smtp_waiting_initial_220"]}, {"time": 300000, "props": ["smtp_initial_220_timeout"]}, {"time": 300001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_waiting_initial_220"]}, {"time": 299999, "props": ["smtp_initial_220_timeout"]}, {"time": 300001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above; role, reachability, connect-time trigger, timeout source chain, and one-generation event contract are now explicit. Lower-bound semantics still does not require timeout at five minutes.
- 被测角色/benchmark 可达性/范围：`SMTP_CLIENT` / `NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：RFC 5321 uses SHOULD for the recommended minimum. This fixed Exim client path is absent from the inbound ProFuzzBench campaign, and a real 300-second wait has LOW wall-clock fuzzing triggerability without a validated virtual clock.

## SMTP-TIMEOUT-02 — MAIL response timeout is not shorter than five minutes

- 性质：客户端发出 MAIL FROM 后等待响应时，不应在 300000 ms 前因 MAIL 阶段超时而放弃。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.2](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.2)；强度 `SHOULD minimum`；时间 `300000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM_AND_IMPLEMENTATION_DEFAULT`）。
- 规范短摘录：“MAIL Command: 5 Minutes”
- 数学 MITL：`G (smtp_mail_response_wait_started -> G [0,300000) (!smtp_mail_response_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_mail_response_wait_started -> G [0,300000) (!smtp_mail_response_timeout))`
- AP：`smtp_mail_response_wait_started, smtp_mail_response_timeout`
- AP 定义：{"smtp_mail_response_wait_started": "flush_buffer successfully transmits a buffer containing the correlated MAIL FROM command; the adapter assigns that command a transaction-generation ordinal before response projection", "smtp_mail_response_timeout": "the response read associated with that pending MAIL generation returns false with errno==ETIMEDOUT"}
- Correlation：outbound connection + SMTP transaction generation + MAIL command sequence
- 投影：decode each successfully flushed command buffer, correlate the pending MAIL response slot, then project exactly one MAIL generation per timed word; command ordinals remain fields
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; one flushed MAIL command and its response outcome constitute one monitor instance
- 源码：[Exim/exim@38903fb5b864 `src/src/smtp_out.c:326-349`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L326-L349)；符号 `flush_buffer`。
- 主源码映射 AP：`["smtp_mail_response_wait_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "pipelined MAIL response slot", "path": "src/src/transports/smtp.c", "symbol": "sync_responses", "lines": "742-782", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L742-L782", "atomic_propositions": ["smtp_mail_response_wait_started", "smtp_mail_response_timeout"]}, {"role": "MAIL command and direct response path", "path": "src/src/transports/smtp.c", "symbol": "smtp_write_mail_and_rcpt_cmds", "lines": "2340-2406", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L2340-L2406", "atomic_propositions": ["smtp_mail_response_wait_started"]}, {"role": "response reader and errno propagation", "path": "src/src/smtp_out.c", "symbol": "read_response_line/smtp_read_response", "lines": "457-520;548-608", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L457-L520", "atomic_propositions": ["smtp_mail_response_timeout"]}, {"role": "absolute read deadline and ETIMEDOUT", "path": "src/src/ip.c", "symbol": "fd_ready/ip_recv", "lines": "478-524;548-570", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L478-L524", "atomic_propositions": ["smtp_mail_response_timeout"]}, {"role": "SMTP timeout classification", "path": "src/src/transports/smtp.c", "symbol": "check_response", "lines": "508-525", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L508-L525", "atomic_propositions": ["smtp_mail_response_timeout"]}, {"role": "fixed timeout profile", "path": "src/src/transports/smtp.c", "symbol": "smtp_transport_option_defaults", "lines": "189-225", "atomic_propositions": ["smtp_mail_response_wait_started"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L189-L225"}]`
- Hook：at successful flush_buffer return, parse the just-sent command buffer and emit one start for its MAIL ordinal; emit timeout only when that pending MAIL response read returns false with errno==ETIMEDOUT
- 正例 timed word：`[{"time": 0, "props": ["smtp_mail_response_wait_started"]}, {"time": 300000, "props": ["smtp_mail_response_timeout"]}, {"time": 300001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_mail_response_wait_started"]}, {"time": 299999, "props": ["smtp_mail_response_timeout"]}, {"time": 300001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above; successful flush is now the trigger, direct and pipelined response paths are separate auxiliary mappings, and role/reachability are explicit.
- 被测角色/benchmark 可达性/范围：`SMTP_CLIENT` / `NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：SHOULD-level minimum. Response arrival, connection close, and other I/O errors are not timeout APs. The current ProFuzzBench Exim server campaign cannot reach this path, and a 300-second real wait has LOW fuzzing triggerability.

## SMTP-TIMEOUT-03 — RCPT response timeout is not shorter than five minutes

- 性质：客户端发出每个 RCPT TO 后等待相应响应时，不应在 300000 ms 前因该 RCPT 阶段超时而放弃。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.3](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.3)；强度 `SHOULD minimum`；时间 `300000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM_AND_IMPLEMENTATION_DEFAULT`）。
- 规范短摘录：“RCPT Command: 5 Minutes”
- 数学 MITL：`G (smtp_rcpt_response_wait_started -> G [0,300000) (!smtp_rcpt_response_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_rcpt_response_wait_started -> G [0,300000) (!smtp_rcpt_response_timeout))`
- AP：`smtp_rcpt_response_wait_started, smtp_rcpt_response_timeout`
- AP 定义：{"smtp_rcpt_response_wait_started": "flush_buffer successfully transmits a buffer containing the correlated RCPT command and assigns it a transaction-local RCPT ordinal", "smtp_rcpt_response_timeout": "sync_responses maps the pending response slot to that RCPT ordinal and its smtp_read_response returns false with errno==ETIMEDOUT"}
- Correlation：outbound connection + SMTP transaction generation + RCPT ordinal/address field
- 投影：decode each successful flush, assign RCPT ordinals, correlate sync_responses slots in order, then spawn one obligation projection per RCPT ordinal; address remains an event field
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each flushed RCPT ordinal and its single response outcome are monitored separately
- 源码：[Exim/exim@38903fb5b864 `src/src/transports/smtp.c:786-825`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L786-L825)；符号 `sync_responses`。
- 主源码映射 AP：`["smtp_rcpt_response_wait_started", "smtp_rcpt_response_timeout"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "RCPT command enqueue/flush and sync invocation", "path": "src/src/transports/smtp.c", "symbol": "smtp_write_mail_and_rcpt_cmds", "lines": "2440-2480", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L2440-L2480", "atomic_propositions": ["smtp_rcpt_response_wait_started"]}, {"role": "actual pipelined command-buffer flush", "path": "src/src/smtp_out.c", "symbol": "flush_buffer", "lines": "326-349", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L326-L349", "atomic_propositions": ["smtp_rcpt_response_wait_started"]}, {"role": "response reader and errno propagation", "path": "src/src/smtp_out.c", "symbol": "read_response_line/smtp_read_response", "lines": "457-520;548-608", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L457-L520", "atomic_propositions": ["smtp_rcpt_response_timeout"]}, {"role": "absolute read deadline and ETIMEDOUT", "path": "src/src/ip.c", "symbol": "fd_ready/ip_recv", "lines": "478-524;548-570", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L478-L524", "atomic_propositions": ["smtp_rcpt_response_timeout"]}, {"role": "fixed timeout profile", "path": "src/src/transports/smtp.c", "symbol": "smtp_transport_option_defaults", "lines": "189-225", "atomic_propositions": ["smtp_rcpt_response_wait_started"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L189-L225"}]`
- Hook：emit start after the successful command-buffer flush for this RCPT ordinal; in sync_responses emit timeout only after ordinal correlation and only on the complete errno==ETIMEDOUT branch at lines 816-825
- 正例 timed word：`[{"time": 0, "props": ["smtp_rcpt_response_wait_started"]}, {"time": 300000, "props": ["smtp_rcpt_response_timeout"]}, {"time": 300001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_rcpt_response_wait_started"]}, {"time": 299999, "props": ["smtp_rcpt_response_timeout"]}, {"time": 300001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above; full ETIMEDOUT branch, successful-flush trigger, separate source mappings, and one-monitor-per-RCPT contract are now explicit.
- 被测角色/benchmark 可达性/范围：`SMTP_CLIENT` / `NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The RFC notes that list/alias processing can need longer; this card asserts only the recommended minimum. The path is unreachable in the current server harness and a real 300-second delay is LOW-triggerability.

## SMTP-TIMEOUT-04 — DATA initiation timeout is not shorter than two minutes

- 性质：客户端发出 DATA 后等待 354 Start Input 时，不应在 120000 ms 前因 DATA-initiation 阶段超时。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.4](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.4)；强度 `SHOULD minimum`；时间 `120000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM`）。
- 规范短摘录：“DATA Initiation: 2 Minutes”
- 数学 MITL：`G (smtp_data_354_wait_started -> G [0,120000) (!smtp_data_354_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_data_354_wait_started -> G [0,120000) (!smtp_data_354_timeout))`
- AP：`smtp_data_354_wait_started, smtp_data_354_timeout`
- AP 定义：{"smtp_data_354_wait_started": "smtp_write_command(..., FALSE, DATA) successfully flushes the correlated classic-DATA command and opens one 354-wait generation", "smtp_data_354_timeout": "the pending-DATA response slot correlated by sync_responses returns false with errno==ETIMEDOUT before a 354 reply"}
- Correlation：outbound connection + SMTP transaction generation + DATA command ordinal
- 投影：after successful DATA flush, correlate the pending_DATA slot after any preceding pipelined MAIL/RCPT slots, then project one DATA-initiation generation per transaction
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; one successfully flushed DATA command and its pending_DATA response outcome form one monitor instance
- 源码：[Exim/exim@38903fb5b864 `src/src/transports/smtp.c:2659-2665`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L2659-L2665)；符号 `smtp_deliver`。
- 主源码映射 AP：`["smtp_data_354_wait_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "pending DATA response slot", "path": "src/src/transports/smtp.c", "symbol": "sync_responses", "lines": "911-930", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L911-L930", "atomic_propositions": ["smtp_data_354_wait_started", "smtp_data_354_timeout"]}, {"role": "actual command-buffer flush", "path": "src/src/smtp_out.c", "symbol": "smtp_write_command/flush_buffer", "lines": "326-349;373-430", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L326-L349", "atomic_propositions": ["smtp_data_354_wait_started"]}, {"role": "response reader and errno propagation", "path": "src/src/smtp_out.c", "symbol": "read_response_line/smtp_read_response", "lines": "457-520;548-608", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L457-L520", "atomic_propositions": ["smtp_data_354_timeout"]}, {"role": "absolute read deadline and ETIMEDOUT", "path": "src/src/ip.c", "symbol": "fd_ready/ip_recv", "lines": "478-524;548-570", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L478-L524", "atomic_propositions": ["smtp_data_354_timeout"]}, {"role": "SMTP timeout classification", "path": "src/src/transports/smtp.c", "symbol": "check_response", "lines": "508-525", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L508-L525", "atomic_propositions": ["smtp_data_354_timeout"]}, {"role": "fixed timeout profile", "path": "src/src/transports/smtp.c", "symbol": "smtp_transport_option_defaults", "lines": "189-225", "atomic_propositions": ["smtp_data_354_wait_started"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L189-L225"}]`
- Hook：emit start after the DATA command's successful forced flush; when sync_responses reaches that pending_DATA slot, emit timeout only for false return with errno==ETIMEDOUT
- 正例 timed word：`[{"time": 0, "props": ["smtp_data_354_wait_started"]}, {"time": 120000, "props": ["smtp_data_354_timeout"]}, {"time": 120001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_data_354_wait_started"]}, {"time": 119999, "props": ["smtp_data_354_timeout"]}, {"time": 120001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above; the wire-flush trigger, pending_DATA response correlation, classic-DATA scope, common timeout sources, and role are now explicit.
- 被测角色/benchmark 可达性/范围：`SMTP_CLIENT` / `NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This lower bound does not claim timeout at two minutes. Exim's default is longer, the current inbound server harness cannot reach the path, and a real 120-second stall remains LOW-triggerability.

## SMTP-TIMEOUT-05 — Each DATA block send timeout is not shorter than three minutes

- 性质：传输一个 DATA 数据块并等待该 TCP SEND 完成时，不应在 180000 ms 前因 data-block send timeout 放弃。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.5](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.5)；强度 `SHOULD minimum`；时间 `180000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM`）。
- 规范短摘录：“Data Block: 3 Minutes”
- 数学 MITL：`G (smtp_data_block_send_wait_started -> G [0,180000) (!smtp_data_block_send_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_data_block_send_wait_started -> G [0,180000) (!smtp_data_block_send_timeout))`
- AP：`smtp_data_block_send_wait_started, smtp_data_block_send_timeout`
- AP 定义：{"smtp_data_block_send_wait_started": "one SMTP-guarded transport_write_block invocation starts with transport_write_timeout copied from smtp_deliver's data_timeout; the event does not assert that the first write is already known to block", "smtp_data_block_send_timeout": "that same invocation returns false with errno==ETIMEDOUT through sigalrm_seen or exhausted local_timeout"}
- Correlation：outbound connection + SMTP transaction generation + monotonically increasing DATA block ordinal
- 投影：guard the generic function by outbound SMTP data context, allocate one block ordinal on function entry, emit exactly one trigger for that invocation, then project it independently; loop retries do not open new generations
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; one SMTP DATA transport_write_block invocation, including all of its partial-write retries, is one monitor instance
- 源码：[Exim/exim@38903fb5b864 `src/src/transport.c:216-306`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transport.c#L216-L306)；符号 `transport_write_block`。
- 主源码映射 AP：`["smtp_data_block_send_wait_started", "smtp_data_block_send_timeout"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "SMTP data-timeout selection and outbound message write", "path": "src/src/transports/smtp.c", "symbol": "smtp_deliver", "lines": "2682-2750", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L2682-L2750", "atomic_propositions": ["smtp_data_block_send_wait_started"]}, {"role": "buffer flushes that invoke the primary hook", "path": "src/src/transport.c", "symbol": "write_chunk", "lines": "425-447", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transport.c#L425-L447", "atomic_propositions": ["smtp_data_block_send_wait_started"]}, {"role": "fixed timeout profile", "path": "src/src/transports/smtp.c", "symbol": "smtp_transport_option_defaults", "lines": "189-225", "atomic_propositions": ["smtp_data_block_send_wait_started"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L189-L225"}]`
- Hook：after verifying the SMTP outbound data guard, emit one start per transport_write_block invocation before its first timed write; do not re-emit inside the retry loop; emit timeout only at the two ETIMEDOUT returns; smtp_deliver:2736-2738 proves the selected data_timeout profile
- 正例 timed word：`[{"time": 0, "props": ["smtp_data_block_send_wait_started"]}, {"time": 180000, "props": ["smtp_data_block_send_timeout"]}, {"time": 180001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_data_block_send_wait_started"]}, {"time": 179999, "props": ["smtp_data_block_send_timeout"]}, {"time": 180001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above. The primary hook remains transport_write_block:216-306; SMTP guard, exactly-once invocation trigger, two timeout exits, role, and reachability are now explicit.
- 被测角色/benchmark 可达性/范围：`SMTP_CLIENT` / `NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：RFC 5321 applies a separate minimum timer to each classic DATA buffer; total message duration is unbounded. The generic source hook must exclude every non-SMTP caller, and the real 180-second threshold is LOW-triggerability without validated virtual time.

## SMTP-TIMEOUT-06 — Classic DATA termination timeout is not shorter than ten minutes

- 性质：客户端通过 classic DATA 发送 final period 后等待 250 OK 时，不应在 600000 ms 前因 final-response timeout 放弃。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.6](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.6)；强度 `SHOULD minimum`；时间 `600000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM_AND_IMPLEMENTATION_DEFAULT`）。
- 规范短摘录：“DATA Termination: 10 Minutes”
- 数学 MITL：`G (smtp_final_250_wait_started -> G [0,600000) (!smtp_final_250_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_final_250_wait_started -> G [0,600000) (!smtp_final_250_timeout))`
- AP：`smtp_final_250_wait_started, smtp_final_250_timeout`
- AP 定义：{"smtp_final_250_wait_started": "non-CHUNKING smtp_deliver successfully transmits the final data buffer containing the terminating period and enters the non-LMTP final-response phase", "smtp_final_250_timeout": "the corresponding non-PRDR, non-LMTP smtp_read_response expecting 2xx returns false with errno==ETIMEDOUT before a 250 response"}
- Correlation：outbound connection + SMTP transaction generation + end-of-data marker
- 投影：require classic DATA/non-LMTP/non-PRDR context, correlate the successfully sent terminating-period buffer to the following final response, and project one generation per transaction
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; one classic DATA end marker and its single final-response outcome form one monitor instance
- 源码：[Exim/exim@38903fb5b864 `src/src/transports/smtp.c:2736-2750;2766-2772;2815-2827`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L2736-L2827)；符号 `smtp_deliver`。
- 主源码映射 AP：`["smtp_final_250_wait_started", "smtp_final_250_timeout"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "response reader and errno propagation", "path": "src/src/smtp_out.c", "symbol": "read_response_line/smtp_read_response", "lines": "457-520;548-608", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L457-L520", "atomic_propositions": ["smtp_final_250_timeout"]}, {"role": "absolute read deadline and ETIMEDOUT", "path": "src/src/ip.c", "symbol": "fd_ready/ip_recv", "lines": "478-524;548-570", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L478-L524", "atomic_propositions": ["smtp_final_250_timeout"]}, {"role": "SMTP timeout classification", "path": "src/src/transports/smtp.c", "symbol": "check_response", "lines": "508-525", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L508-L525", "atomic_propositions": ["smtp_final_250_timeout"]}, {"role": "fixed timeout profile", "path": "src/src/transports/smtp.c", "symbol": "smtp_transport_option_defaults", "lines": "189-225", "atomic_propositions": ["smtp_final_250_wait_started"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L189-L225"}]`
- Hook：guard classic DATA/non-CHUNKING/non-LMTP/non-PRDR context; emit start once after the terminating-period write succeeds and before the final read; emit timeout only for that read's ETIMEDOUT outcome
- 正例 timed word：`[{"time": 0, "props": ["smtp_final_250_wait_started"]}, {"time": 600000, "props": ["smtp_final_250_timeout"]}, {"time": 600001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_final_250_wait_started"]}, {"time": 599999, "props": ["smtp_final_250_timeout"]}, {"time": 600001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above; the property is now restricted to classic DATA and its single non-LMTP final response, with role and timeout source chain explicit.
- 被测角色/benchmark 可达性/范围：`SMTP_CLIENT` / `NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：A 4xx/5xx response, peer close, or other I/O error is not a timeout. Extension paths are excluded. The client path is absent from the current server harness, and a real 600-second wait is LOW-triggerability.

## SMTP-TIMEOUT-07 — Plaintext server command-read timeout is not shorter than five minutes

- 性质：plaintext SMTP server 的输入 buffer 为空并等待发送方下一段命令输入时，不应在 300000 ms 前因 command-phase receive timeout 关闭连接。
- 规范：[RFC 5321 RFC 5321 §4.5.3.2.7](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2.7)；强度 `SHOULD minimum`；时间 `300000 ms`（`NORMATIVE_RECOMMENDED_MINIMUM_AND_IMPLEMENTATION_DEFAULT`）。
- 规范短摘录：“An SMTP server SHOULD have a timeout of at least 5 minutes”
- 数学 MITL：`G (smtp_server_command_wait_started -> G [0,300000) (!smtp_server_command_idle_timeout))`
- MightyPPL（finite weak outer global）：`G* (smtp_server_command_wait_started -> G [0,300000) (!smtp_server_command_idle_timeout))`
- AP：`smtp_server_command_wait_started, smtp_server_command_idle_timeout`
- AP 定义：{"smtp_server_command_wait_started": "while smtp_read_command has command_timeout_handler installed, plaintext smtp_getc finds its input buffer empty and arms smtp_receive_timeout immediately before read", "smtp_server_command_idle_timeout": "that same command-read generation reaches command_timeout_handler because the armed receive alarm expires and closes the correlated connection"}
- Correlation：accepted server connection + command-read generation
- 投影：spawn one plaintext command-read generation each time smtp_getc arms a receive alarm under smtp_read_command; bytes/read completion, command completion, phase change, or connection close ends that generation before the next one
- 监控实例：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each plaintext smtp_getc alarm arm in command phase is a separate monitor instance
- 源码：[Exim/exim@38903fb5b864 `src/src/smtp_in.c:416-430`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_in.c#L416-L430)；符号 `smtp_getc`。
- 主源码映射 AP：`["smtp_server_command_wait_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "command-phase signal-handler installation and read loop", "path": "src/src/smtp_in.c", "symbol": "smtp_read_command", "lines": "1424-1450", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_in.c#L1424-L1450", "atomic_propositions": ["smtp_server_command_wait_started"]}, {"role": "command timeout outcome and connection close", "path": "src/src/smtp_in.c", "symbol": "command_timeout_handler", "lines": "838-850", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_in.c#L838-L850", "atomic_propositions": ["smtp_server_command_idle_timeout"]}, {"role": "default timeout profile", "path": "src/src/globals.c", "symbol": "smtp_receive_timeout", "lines": "1325-1326", "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/globals.c#L1325-L1326", "atomic_propositions": ["smtp_server_command_wait_started"]}, {"role": "fixed timeout profile", "path": "src/src/globals.c", "symbol": "smtp_receive_timeout", "lines": "1325", "atomic_propositions": ["smtp_server_command_wait_started"], "url": "https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/globals.c#L1325"}]`
- Hook：emit start only when plaintext smtp_getc arms the receive alarm while smtp_read_command has installed command_timeout_handler; emit timeout only inside that handler and correlate by accepted connection/read generation
- 正例 timed word：`[{"time": 0, "props": ["smtp_server_command_wait_started"]}, {"time": 300000, "props": ["smtp_server_command_idle_timeout"]}, {"time": 300001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["smtp_server_command_wait_started"]}, {"time": 299999, "props": ["smtp_server_command_idle_timeout"]}, {"time": 300001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original disposition FIX retained above; the card is now explicitly plaintext command-phase, maps handler installation and timeout outcome, and distinguishes role reachability from practical deadline triggerability.
- 被测角色/benchmark 可达性/范围：`SMTP_SERVER` / `ROLE_REACHED_BUT_DEADLINE_IMPRACTICAL_PER_TESTCASE` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This card covers each plaintext command-read alarm generation, not an absolute whole-line deadline and not DATA/TLS reads. Although the server role is benchmark-reachable, the real 300-second deadline has LOW per-testcase triggerability without validated virtual time.
