# DTLS MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：3
- 自动拒绝/待修：1
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## DTLS12-RTX-01 — Initial handshake retransmission timer is one second

- 性质：OpenSSL DTLS 1.2 datagram、无 timer_cb override 的默认分支实际按 1000 ms arm 后，不得提前到期，并须在期限到达或被期望 flight/重设取消。
- 规范：[RFC 6347 RFC 6347 (DTLS 1.2) §4.2.4.1](https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1)；强度 `SHOULD`；时间 `1000 ms`（`NORMATIVE_RECOMMENDED_DEFAULT`）。
- 规范短摘录：“Implementations SHOULD use an initial timer value of 1 second”
- 数学 MITL：`G (dtls12_timer_armed_1000ms_default_profile -> (G [0,1000) (!dtls12_timer_deadline_reached) && F [0,1000] (dtls12_timer_deadline_reached || dtls12_timer_superseded)))`
- MightyPPL（finite weak outer global）：`G* (dtls12_timer_armed_1000ms_default_profile -> (G [0,1000) (!dtls12_timer_deadline_reached) && F [0,1000] (dtls12_timer_deadline_reached || dtls12_timer_superseded)))`
- AP：`dtls12_timer_armed_1000ms_default_profile, dtls12_timer_deadline_reached, dtls12_timer_superseded`
- AP 定义：{"dtls12_timer_armed_1000ms_default_profile": "A non-SCTP DTLS 1.2 flight with no timer callback actually stores timeout_duration_us=1000000 and next_timeout in dtls1_start_timer.", "dtls12_timer_deadline_reached": "DERIVED adapter event at the exact next_timeout stored for this timer generation; it is not OpenSSL's callback or its sub-15-ms coalescing decision.", "dtls12_timer_superseded": "A later dtls1_start_timer replaces this active generation or dtls1_stop_timer clears it; adapter generation IDs prevent the replacement from satisfying the old deadline AP."}
- Correlation：SSL object + handshake generation + message_seq range/epoch as fields
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[openssl/openssl@0437435a9601 `ssl/d1_lib.c:242-284`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L242-L284)；符号 `dtls1_start_timer`。
- 主源码映射 AP：`["dtls12_timer_armed_1000ms_default_profile", "dtls12_timer_deadline_reached"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "restart overwrites an active timer generation", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/d1_lib.c", "symbol": "dtls1_start_timer", "lines": "242-284", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L242-L284", "atomic_propositions": ["dtls12_timer_superseded"]}, {"role": "timer stop clears the active generation", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/d1_lib.c", "symbol": "dtls1_stop_timer", "lines": "352-362", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L352-L362", "atomic_propositions": ["dtls12_timer_superseded"]}, {"role": "expected peer-handshake processing invokes timer stop", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/statem/statem.c", "symbol": "read_state_machine", "lines": "637-683", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/statem/statem.c#L637-L683", "atomic_propositions": ["dtls12_timer_superseded"]}]`
- Hook：After dtls1_start_timer stores next_timeout, emit the arm only for non-SCTP, timer_cb=NULL, timeout_duration_us=1000000. Schedule the logical deadline AP from that stored absolute timestamp. If dtls1_stop_timer clears it or another dtls1_start_timer overwrites it first, emit superseded for the old adapter generation and close that projection.
- 正例 timed word：`[{"time": 0, "props": ["dtls12_timer_armed_1000ms_default_profile"]}, {"time": 1000, "props": ["dtls12_timer_deadline_reached"]}, {"time": 1001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["dtls12_timer_armed_1000ms_default_profile"]}, {"time": 999, "props": ["dtls12_timer_deadline_reached"]}, {"time": 1001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["dtls12_timer_armed_1000ms_default_profile"]}, {"time": 1001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Every AP is mapped at the fixed OpenSSL commit. The deadline is explicitly derived from the implementation's stored next_timeout and is kept separate from dtls1_is_timer_expired, which intentionally coalesces less than 15 ms; stop and replacement mappings close the old generation.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：ProFuzzBench's pinned TinyDTLS fork uses 2000 ms, so it is a known conformance-divergence target and is not the source oracle for this property.

## DTLS12-RTX-03 — First retransmission doubles the next timer to two seconds

- 性质：第一次重传后实际按 2000 ms arm 的 DTLS generation 不得提前到期，并须在期限到达或因期望/重复 flight 重启而失效。
- 规范：[RFC 6347 RFC 6347 (DTLS 1.2) §4.2.4.1](https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1)；强度 `SHOULD`；时间 `2000 ms`（`NORMATIVE_DERIVED`）。
- 规范短摘录：“double the value at each retransmission”
- 数学 MITL：`G (dtls12_timer_rearmed_2000ms -> (G [0,2000) (!dtls12_second_deadline_reached) && F [0,2000] (dtls12_second_deadline_reached || dtls12_second_timer_superseded)))`
- MightyPPL（finite weak outer global）：`G* (dtls12_timer_rearmed_2000ms -> (G [0,2000) (!dtls12_second_deadline_reached) && F [0,2000] (dtls12_second_deadline_reached || dtls12_second_timer_superseded)))`
- AP：`dtls12_timer_rearmed_2000ms, dtls12_second_deadline_reached, dtls12_second_timer_superseded`
- AP 定义：{"dtls12_timer_rearmed_2000ms": "After the first expiry, dtls1_double_timeout changes timeout_duration_us from 1000000 to 2000000 and calls dtls1_start_timer for this generation.", "dtls12_second_deadline_reached": "DERIVED adapter event at the exact next_timeout stored by dtls1_start_timer for this 2000-ms generation; not callback dispatch.", "dtls12_second_timer_superseded": "A later dtls1_start_timer replaces this active 2000-ms generation or dtls1_stop_timer clears it; generation IDs keep the old and new deadlines distinct."}
- Correlation：SSL object + handshake generation + retransmission count
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[openssl/openssl@0437435a9601 `ssl/d1_lib.c:344-350`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L344-L350)；符号 `dtls1_double_timeout`。
- 主源码映射 AP：`["dtls12_timer_rearmed_2000ms"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "store the rearmed generation's absolute deadline and detect restart replacement", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/d1_lib.c", "symbol": "dtls1_start_timer", "lines": "242-284", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L242-L284", "atomic_propositions": ["dtls12_second_deadline_reached", "dtls12_second_timer_superseded"]}, {"role": "timer stop clears the active 2000-ms generation", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/d1_lib.c", "symbol": "dtls1_stop_timer", "lines": "352-362", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L352-L362", "atomic_propositions": ["dtls12_second_timer_superseded"]}, {"role": "expected peer-handshake processing invokes timer stop", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/statem/statem.c", "symbol": "read_state_machine", "lines": "637-683", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/statem/statem.c#L637-L683", "atomic_propositions": ["dtls12_second_timer_superseded"]}]`
- Hook：Emit the trigger only after dtls1_double_timeout has produced timeout_duration_us=2000000 and dtls1_start_timer stores its next_timeout. Derive the deadline from that stored timestamp. Close the old generation as superseded when a later start overwrites it or stop_timer clears it.
- 正例 timed word：`[{"time": 0, "props": ["dtls12_timer_rearmed_2000ms"]}, {"time": 2000, "props": ["dtls12_second_deadline_reached"]}, {"time": 2001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["dtls12_timer_rearmed_2000ms"]}, {"time": 1999, "props": ["dtls12_second_deadline_reached"]}, {"time": 2001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["dtls12_timer_rearmed_2000ms"]}, {"time": 2001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；All three APs now have fixed-commit implementation mappings. Deadline is a derived event from stored next_timeout, while restart/stop are real OpenSSL calls correlated by SSL pointer plus adapter timer generation.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Only one representative doubling is a catalog property; 4/8/16/32-second copies are duplicate obligations.

## DTLS12-RTX-04 — Retransmission timer caps at 60 seconds

- 性质：OpenSSL profile 达到并实际按 60000 ms arm 的 capped generation 不得提前到期，并须到期或因期望/重复 flight 重启而失效。
- 规范：[RFC 6347 RFC 6347 (DTLS 1.2) §4.2.4.1](https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1)；强度 `SHOULD`；时间 `60000 ms`（`NORMATIVE_RECOMMENDED_CAP_PROFILE`）。
- 规范短摘录：“up to no less than the RFC 6298 maximum of 60 seconds”
- 数学 MITL：`G (dtls12_timer_rearmed_60000ms_cap -> (G [0,60000) (!dtls12_capped_deadline_reached) && F [0,60000] (dtls12_capped_deadline_reached || dtls12_capped_timer_superseded)))`
- MightyPPL（finite weak outer global）：`G* (dtls12_timer_rearmed_60000ms_cap -> (G [0,60000) (!dtls12_capped_deadline_reached) && F [0,60000] (dtls12_capped_deadline_reached || dtls12_capped_timer_superseded)))`
- AP：`dtls12_timer_rearmed_60000ms_cap, dtls12_capped_deadline_reached, dtls12_capped_timer_superseded`
- AP 定义：{"dtls12_timer_rearmed_60000ms_cap": "dtls1_double_timeout clamps timeout_duration_us to 60000000 and calls dtls1_start_timer for this capped generation.", "dtls12_capped_deadline_reached": "DERIVED adapter event at the exact next_timeout stored by dtls1_start_timer for this capped generation; not callback dispatch.", "dtls12_capped_timer_superseded": "A later dtls1_start_timer replaces this active capped generation or dtls1_stop_timer clears it; generation IDs keep the old and new deadlines distinct."}
- Correlation：SSL object + handshake generation + retransmission count
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[openssl/openssl@0437435a9601 `ssl/d1_lib.c:344-350`](https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L344-L350)；符号 `dtls1_double_timeout`。
- 主源码映射 AP：`["dtls12_timer_rearmed_60000ms_cap"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "store the capped generation's absolute deadline and detect restart replacement", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/d1_lib.c", "symbol": "dtls1_start_timer", "lines": "242-284", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L242-L284", "atomic_propositions": ["dtls12_capped_deadline_reached", "dtls12_capped_timer_superseded"]}, {"role": "timer stop clears the active capped generation", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/d1_lib.c", "symbol": "dtls1_stop_timer", "lines": "352-362", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/d1_lib.c#L352-L362", "atomic_propositions": ["dtls12_capped_timer_superseded"]}, {"role": "expected peer-handshake processing invokes timer stop", "repository": "openssl/openssl", "commit": "0437435a960123be1ced766d18d715f939698345", "path": "ssl/statem/statem.c", "symbol": "read_state_machine", "lines": "637-683", "url": "https://github.com/openssl/openssl/blob/0437435a960123be1ced766d18d715f939698345/ssl/statem/statem.c#L637-L683", "atomic_propositions": ["dtls12_capped_timer_superseded"]}]`
- Hook：Emit the trigger only after dtls1_double_timeout clamps timeout_duration_us=60000000 and dtls1_start_timer stores its next_timeout. Derive the deadline from that timestamp. Close the generation as superseded if a later start overwrites it or stop_timer clears it.
- 正例 timed word：`[{"time": 0, "props": ["dtls12_timer_rearmed_60000ms_cap"]}, {"time": 60000, "props": ["dtls12_capped_deadline_reached"]}, {"time": 60001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["dtls12_timer_rearmed_60000ms_cap"]}, {"time": 59999, "props": ["dtls12_capped_deadline_reached"]}, {"time": 60001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["dtls12_timer_rearmed_60000ms_cap"]}, {"time": 60001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；All three APs now have fixed-commit implementation mappings. The exact 60-second value remains an OpenSSL profile cap as already stated; restart/stop are correlated per adapter timer generation.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The RFC wording permits a larger implementation maximum; this exact 60-second property is the OpenSSL profile, not a universal maximum.
