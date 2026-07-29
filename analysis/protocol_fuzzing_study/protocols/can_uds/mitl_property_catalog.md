# CAN/UDS MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：5
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## CANTP-NBS-01 — Waiting for FlowControl ends or aborts at N_Bs=1000 ms

- 性质：python-can-isotp 默认 N_Bs profile 中，发送方进入 WAIT_FC 后，1000 ms 前不得以 N_Bs 超时中止；到期前必须收到 FlowControl 或执行中止。
- 规范：[AUTOSAR SWS CAN Transport Layer R24-11 §7.2.3 [SWS_CanTp_00315-SWS_CanTp_00316]; 10.2 [ECUC_CanTp_00264]](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_CANTransportLayer.pdf)；强度 `SHALL`；时间 `1000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“abort transmission of this message and notify the upper layer”
- 数学 MITL：`G (n_bs_timer_generation_started_1000 -> (G [0,1000) (!tx_aborted_n_bs) && F [0,1000] (flow_control_received || tx_aborted_n_bs || n_bs_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (n_bs_timer_generation_started_1000 -> (G [0,1000) (!tx_aborted_n_bs) && F [0,1000] (flow_control_received || tx_aborted_n_bs || n_bs_generation_cancelled)))`
- AP：`n_bs_timer_generation_started_1000, flow_control_received, tx_aborted_n_bs, n_bs_generation_cancelled`
- AP 定义：{"n_bs_timer_generation_started_1000": "The implementation enters WAIT_FC and starts timer_rx_fc with configured 1000 ms; adapter records whether this precedes an AUTOSAR Tx-confirmation start.", "flow_control_received": "A valid correlated FC(CTS/WAIT/OVFLW) is decoded before N_Bs expiry; WAIT begins a new correlated wait window.", "tx_aborted_n_bs": "FlowControlTimeoutError is raised and _stop_sending(success=False) executes for that transfer.", "n_bs_generation_cancelled": "The public stop_sending path or TransportLayerLogic.reset ends the current WAIT_FC generation before its timeout; a harness process reset is accepted only when it records the same transfer generation."}
- Correlation：ISO-TP addressing tuple + CAN channel + active send-request generation; CAN IDs and sequence numbers remain fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one segmented-send N_Bs timer generation; FC(WAIT) closes it and creates another word, CTS/OVFLW/abort/cancel closes it without overlap.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[pylessard/python-can-isotp@7b44c5282ee3 `isotp/protocol.py:987-1051`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L987-L1051)；符号 `def _process_tx`。
- 主源码映射 AP：`["flow_control_received", "tx_aborted_n_bs"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "N_Bs timer generation start", "path": "isotp/protocol.py", "symbol": "_start_rx_fc_timer", "lines": "1250-1253", "atomic_propositions": ["n_bs_timer_generation_started_1000"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L1250-L1253"}, {"role": "1000 ms receive-flow-control profile", "path": "isotp/protocol.py", "symbol": "__init__", "lines": "349-354", "atomic_propositions": ["n_bs_timer_generation_started_1000"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L349-L354"}, {"role": "strict elapsed timeout predicate", "path": "isotp/tools.py", "symbol": "is_timed_out", "lines": "48-53", "atomic_propositions": ["tx_aborted_n_bs"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/tools.py#L48-L53"}, {"role": "explicit send cancellation or layer reset", "path": "isotp/protocol.py", "symbol": "stop_sending / reset", "lines": "1321-1325;1406-1415", "atomic_propositions": ["n_bs_generation_cancelled"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L1321-L1325"}]`
- Hook：Emit trigger at _start_rx_fc_timer and record the implementation start plus any external Tx-confirmation timestamp. FC(WAIT) first satisfies the old word, then starts a new word. Emit abort only when the source action is observed; stamp its logical deadline and keep actual callback time.
- 正例 timed word：`[{"time": 0, "props": ["n_bs_timer_generation_started_1000"]}, {"time": 1000, "props": ["tx_aborted_n_bs"]}, {"time": 1001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["n_bs_timer_generation_started_1000"]}, {"time": 999, "props": ["tx_aborted_n_bs"]}, {"time": 1001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["n_bs_timer_generation_started_1000"]}, {"time": 1001, "props": ["tx_aborted_n_bs"]}, {"time": 1002, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["n_bs_timer_generation_started_1000"]}, {"time": 1001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: AUTOSAR start clause, implementation-vs-Tx-confirmation start, cancellation, per-generation projection, fixed helper hooks, and early/late traces are explicit.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：1000 ms is a python-can-isotp profile, not an AUTOSAR/ISO default. AUTOSAR starts N_Bs from Tx confirmation, while this library may start earlier; both timestamps are retained and the claim is explicitly implementation-profile-scoped. Timer::is_timed_out uses strict >, so the exact-bound oracle may expose a source discrepancy.

## CANTP-NCR-01 — Waiting for ConsecutiveFrame ends or aborts at N_Cr=1000 ms

- 性质：python-can-isotp 默认 N_Cr profile 中，接收方等待下一 ConsecutiveFrame 后，1000 ms 前不得以 N_Cr 超时中止；到期前必须收到下一帧或执行中止。
- 规范：[AUTOSAR SWS CAN Transport Layer R24-11 §7.2.2 [SWS_CanTp_00312-SWS_CanTp_00313]; 10.2 [ECUC_CanTp_00279]](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_CANTransportLayer.pdf)；强度 `SHALL`；时间 `1000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“abort reception and notify the upper layer of this failure”
- 数学 MITL：`G (n_cr_timer_generation_started_1000 -> (G [0,1000) (!rx_aborted_n_cr) && F [0,1000] (consecutive_frame_received || rx_aborted_n_cr || n_cr_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (n_cr_timer_generation_started_1000 -> (G [0,1000) (!rx_aborted_n_cr) && F [0,1000] (consecutive_frame_received || rx_aborted_n_cr || n_cr_generation_cancelled)))`
- AP：`n_cr_timer_generation_started_1000, consecutive_frame_received, rx_aborted_n_cr, n_cr_generation_cancelled`
- AP 定义：{"n_cr_timer_generation_started_1000": "A valid FirstFrame/non-final ConsecutiveFrame, or the local FC-send path, starts timer_rx_cf with configured 1000 ms; start provenance is recorded.", "consecutive_frame_received": "The next correctly sequenced correlated ConsecutiveFrame is accepted; if more data remains, it starts a new N_Cr window.", "rx_aborted_n_cr": "ConsecutiveFrameTimeoutError is raised and _stop_receiving executes for this transfer.", "n_cr_generation_cancelled": "The public stop_receiving path or TransportLayerLogic.reset ends the current WAIT_CF generation before timeout; normal successful completion is retained as a distinct terminal cause by the adapter."}
- Correlation：ISO-TP addressing tuple + CAN channel + receive generation + expected sequence number as a field
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one segmented-receive N_Cr generation; each accepted non-final CF closes it and creates another word, while completion/error/cancel ends it.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[pylessard/python-can-isotp@7b44c5282ee3 `isotp/protocol.py:890-894`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L890-L894)；符号 `def _check_timeouts_rx`。
- 主源码映射 AP：`["rx_aborted_n_cr"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "accepted consecutive-frame path", "path": "isotp/protocol.py", "symbol": "_process_rx", "lines": "895-984", "atomic_propositions": ["n_cr_timer_generation_started_1000", "consecutive_frame_received"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L895-L984"}, {"role": "N_Cr timer generation start", "path": "isotp/protocol.py", "symbol": "_start_rx_cf_timer", "lines": "1254-1257", "atomic_propositions": ["n_cr_timer_generation_started_1000"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L1254-L1257"}, {"role": "1000 ms consecutive-frame profile", "path": "isotp/protocol.py", "symbol": "__init__", "lines": "349-354", "atomic_propositions": ["n_cr_timer_generation_started_1000"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L349-L354"}, {"role": "strict elapsed timeout predicate", "path": "isotp/tools.py", "symbol": "is_timed_out", "lines": "48-53", "atomic_propositions": ["rx_aborted_n_cr"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/tools.py#L48-L53"}, {"role": "explicit receive cancellation or layer reset", "path": "isotp/protocol.py", "symbol": "stop_receiving / reset", "lines": "1341-1346;1406-1415", "atomic_propositions": ["n_cr_generation_cancelled"], "url": "https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L1341-L1346"}]`
- Hook：Emit start at _start_rx_cf_timer with its provenance; accepted CF is emitted only after sequence validation and first satisfies the old word before starting another. Emit abort only when observed, stamp its logical deadline, and retain callback time.
- 正例 timed word：`[{"time": 0, "props": ["n_cr_timer_generation_started_1000"]}, {"time": 1000, "props": ["rx_aborted_n_cr"]}, {"time": 1001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["n_cr_timer_generation_started_1000"]}, {"time": 999, "props": ["rx_aborted_n_cr"]}, {"time": 1001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["n_cr_timer_generation_started_1000"]}, {"time": 1001, "props": ["rx_aborted_n_cr"]}, {"time": 1002, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["n_cr_timer_generation_started_1000"]}, {"time": 1001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: AUTOSAR start clause, timer-start provenance, cancellation, accepted-CF/restart hook, per-generation projection, and early/late traces were added.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：1000 ms is a python-can-isotp profile, not an AUTOSAR/ISO default. The library timer may start in the local FC path rather than an external transmission confirmation, and strict elapsed > timeout may expose an exact-bound discrepancy.

## UDS-P2-01 — Initial diagnostic response or NRC 0x78 arrives within P2=50 ms

- 性质：iso14229 默认 server P2=50 ms 时，服务器接收并开始处理诊断请求后，应在 50 ms 内发送最终响应；若仍需处理，则发送 NRC 0x78。
- 规范：[AUTOSAR SWS Diagnostic Communication Manager R24-11 §7.2.4.6 [SWS_Dcm_00024]](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf)；强度 `SHALL`；时间 `50 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“shall send a negative response with NRC 0x78 when reaching the response time”
- 数学 MITL：`G (uds_request_processing_started_p2_50_adjust0 -> F [0,50] (uds_final_response_sent || uds_nrc78_sent || uds_p2_generation_cancelled))`
- MightyPPL（finite weak outer global）：`G* (uds_request_processing_started_p2_50_adjust0 -> F [0,50] (uds_final_response_sent || uds_nrc78_sent || uds_p2_generation_cancelled))`
- AP：`uds_request_processing_started_p2_50_adjust0, uds_final_response_sent, uds_nrc78_sent, uds_p2_generation_cancelled`
- AP 定义：{"uds_request_processing_started_p2_50_adjust0": "A complete valid request is accepted by UDSServerPoll with srv->p2_ms=50, normative server adjustment=0, and response suppression not selected; adapter snapshots request tick and implementation p2_timer.", "uds_final_response_sent": "UDSTpSend is invoked with a final positive or non-0x78 negative response for the correlated request.", "uds_nrc78_sent": "UDSTpSend is invoked with NRC RequestCorrectlyReceived-ResponsePending (0x78) for that request.", "uds_p2_generation_cancelled": "UDSServerInit resets the server while the correlated request is outstanding, or the harness records transport teardown for that request generation before a response handoff."}
- Correlation：transport connection + tester/source address + request generation + SID/subfunction as fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one accepted server request generation; repeated/new requests cannot share a word, and teardown/reset emits explicit cancellation.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[driftregion/iso14229@b0e92b14fcc3 `src/server.c:1581-1660`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1581-L1660)；符号 `UDSServerPoll`。
- 主源码映射 AP：`["uds_request_processing_started_p2_50_adjust0", "uds_final_response_sent", "uds_nrc78_sent"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "50 ms P2 implementation profile", "path": "src/config.h", "symbol": "UDS_SERVER_DEFAULT_P2_MS", "lines": "42-43", "atomic_propositions": ["uds_request_processing_started_p2_50_adjust0"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/config.h#L42-L43"}, {"role": "strict logical deadline predicate", "path": "src/util.h", "symbol": "UDSTimeAfter", "lines": "13", "atomic_propositions": ["uds_final_response_sent", "uds_nrc78_sent"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/util.h#L13"}, {"role": "response transport handoff", "path": "src/server.c", "symbol": "UDSServerPoll", "lines": "1617-1621", "atomic_propositions": ["uds_final_response_sent", "uds_nrc78_sent"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1617-L1621"}, {"role": "server reset cancellation", "path": "src/server.c", "symbol": "UDSServerInit", "lines": "1564-1579", "atomic_propositions": ["uds_p2_generation_cancelled"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1564-L1579"}]`
- Hook：Emit trigger after lines 1653-1658 accept/evaluate the request and snapshot request+50 plus srv->p2_timer. Emit response only at actual UDSTpSend handoff; classify NRC 0x78 versus final. Suppressed-positive requests are trigger-false; teardown/reset emits cancellation.
- 正例 timed word：`[{"time": 0, "props": ["uds_request_processing_started_p2_50_adjust0"]}, {"time": 50, "props": ["uds_nrc78_sent"]}, {"time": 51, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["uds_request_processing_started_p2_50_adjust0"]}, {"time": 51, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["uds_request_processing_started_p2_50_adjust0"]}, {"time": 51, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: adjustment=0 is a trigger precondition, request and response hooks are in fixed ranges, cancellation is explicit, and normative versus implementation deadlines are separated.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：50 ms is the locked iso14229 profile and this card explicitly assumes server adjustment=0. Other DCMs must instantiate active P2ServerMax-adjust. The source's p2_timer can predate request acceptance, so both the normative request+50 deadline and implementation snapshot are retained.

## UDS-P2STAR-01 — After NRC 0x78 another response arrives within P2*=5000 ms

- 性质：iso14229 默认 P2*=5000 ms 时，服务器发送 NRC 0x78 后，应在 5000 ms 内发送最终响应或新的 NRC 0x78。
- 规范：[AUTOSAR SWS Diagnostic Communication Manager R24-11 §7.2.4.6 [SWS_Dcm_00024]](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf)；强度 `SHALL`；时间 `5000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“when reaching the response time DcmDspSessionP2StarServerMax”
- 数学 MITL：`G (uds_nrc78_sent_p2star_5000_adjust0 -> F [0,5000] (uds_final_response_after_nrc78 || uds_nrc78_repeated || uds_p2star_generation_cancelled))`
- MightyPPL（finite weak outer global）：`G* (uds_nrc78_sent_p2star_5000_adjust0 -> F [0,5000] (uds_final_response_after_nrc78 || uds_nrc78_repeated || uds_p2star_generation_cancelled))`
- AP：`uds_nrc78_sent_p2star_5000_adjust0, uds_final_response_after_nrc78, uds_nrc78_repeated, uds_p2star_generation_cancelled`
- AP 定义：{"uds_nrc78_sent_p2star_5000_adjust0": "An NRC 0x78 is successfully handed to transport for a request with p2_star_ms=5000 and server adjustment=0.", "uds_final_response_after_nrc78": "A final correlated response is handed to the transport after that NRC 0x78.", "uds_nrc78_repeated": "Another correlated NRC 0x78 is handed to the transport, starting the next P2* window.", "uds_p2star_generation_cancelled": "UDSServerInit resets the server while the post-0x78 response is outstanding, or the harness records transport teardown for that exact request generation."}
- Correlation：same server request generation + tester/source address; consecutive NRCs are ordered fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one post-NRC response generation; each repeated NRC satisfies it and starts a separate word for the same request, while teardown/reset cancels it.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[driftregion/iso14229@b0e92b14fcc3 `src/server.c:1598-1638`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1598-L1638)；符号 `UDSServerPoll`。
- 主源码映射 AP：`["uds_nrc78_sent_p2star_5000_adjust0", "uds_final_response_after_nrc78", "uds_nrc78_repeated"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "5000 ms P2-star implementation profile", "path": "src/config.h", "symbol": "UDS_SERVER_DEFAULT_P2_STAR_MS", "lines": "47-48", "atomic_propositions": ["uds_nrc78_sent_p2star_5000_adjust0"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/config.h#L47-L48"}, {"role": "strict logical deadline predicate", "path": "src/util.h", "symbol": "UDSTimeAfter", "lines": "13", "atomic_propositions": ["uds_final_response_after_nrc78", "uds_nrc78_repeated"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/util.h#L13"}, {"role": "server reset cancellation", "path": "src/server.c", "symbol": "UDSServerInit", "lines": "1564-1579", "atomic_propositions": ["uds_p2star_generation_cancelled"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1564-L1579"}]`
- Hook：Classify each successful UDSTpSend at lines 1617-1637; a repeated NRC atomically satisfies the old word before opening another. Store the P2* logical deadline and actual handoff time; poll callback time is not the response event.
- 正例 timed word：`[{"time": 0, "props": ["uds_nrc78_sent_p2star_5000_adjust0"]}, {"time": 5000, "props": ["uds_final_response_after_nrc78"]}, {"time": 5001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["uds_nrc78_sent_p2star_5000_adjust0"]}, {"time": 5001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["uds_nrc78_sent_p2star_5000_adjust0"]}, {"time": 5001, "props": []}]}`
- 独立审计：`APPROVE`；Approved with caveat: adjustment=0 and successful transport handoff are explicit, and every repeated NRC closes one generation before starting the next.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The implementation normally repeats NRC 0x78 at 0.3*P2*=1500 ms. 5000 ms and adjustment=0 are locked implementation preconditions, not AUTOSAR universal defaults.

## UDS-S3-01 — Idle non-default session returns to default at S3=5100 ms

- 性质：锁定 iso14229 S3=5100 ms profile 后，非默认会话不得在 5100 ms 前因 S3 timeout 回到默认会话；到 deadline 应因 S3 切回，或由 owner 有效活动重置、显式会话操作/停止取消该 generation。
- 规范：[AUTOSAR SWS Diagnostic Communication Manager R24-11 §7.2.4.13 [SWS_Dcm_01670]; 7.2.4.14 [SWS_Dcm_01680]](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf)；强度 `SHALL`；时间 `5100 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“If the S3Server elapses, the Dcm shall switch back to default session”
- 数学 MITL：`G (non_default_session_idle_started_s3_5100 -> (G [0,5100) (!default_session_entered_due_to_s3) && F [0,5100] (default_session_entered_due_to_s3 || s3_resetting_activity_received || s3_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (non_default_session_idle_started_s3_5100 -> (G [0,5100) (!default_session_entered_due_to_s3) && F [0,5100] (default_session_entered_due_to_s3 || s3_resetting_activity_received || s3_generation_cancelled)))`
- AP：`non_default_session_idle_started_s3_5100, default_session_entered_due_to_s3, s3_resetting_activity_received, s3_generation_cancelled`
- AP 定义：{"non_default_session_idle_started_s3_5100": "A non-default session begins a fresh idle S3 window with srv->s3_ms=5100 after a qualifying activity/reset.", "default_session_entered_due_to_s3": "UDSServerPoll changes sessionType to UDS_LEV_DS_DS specifically because the S3 timer elapsed.", "s3_resetting_activity_received": "A valid request from the owning tester/connection that normatively resets S3 is processed before expiry.", "s3_generation_cancelled": "A valid DiagnosticSessionControl changes the session generation, or UDSServerInit resets the server, before the old S3 timeout cause occurs."}
- Correlation：server instance + transport connection + tester/source address + non-default session epoch
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one owner-scoped non-default-session idle generation; owner reset creates another word, while explicit session action/stop/profile change cancels it.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[driftregion/iso14229@b0e92b14fcc3 `src/server.c:1581-1588`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1581-L1588)；符号 `UDSServerPoll`。
- 主源码映射 AP：`["default_session_entered_due_to_s3"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "non-default session entry and explicit session change", "path": "src/server.c", "symbol": "Handle_0x10_DiagnosticSessionControl", "lines": "38-83", "atomic_propositions": ["non_default_session_idle_started_s3_5100", "s3_generation_cancelled"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L38-L83"}, {"role": "TesterPresent S3 refresh", "path": "src/server.c", "symbol": "Handle_0x3E_TesterPresent", "lines": "1304-1321", "atomic_propositions": ["s3_resetting_activity_received"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1304-L1321"}, {"role": "server initialization and reset", "path": "src/server.c", "symbol": "UDSServerInit", "lines": "1564-1579", "atomic_propositions": ["non_default_session_idle_started_s3_5100", "s3_generation_cancelled"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1564-L1579"}, {"role": "5100 ms S3 implementation profile", "path": "src/config.h", "symbol": "UDS_SERVER_DEFAULT_S3_MS", "lines": "51-53", "atomic_propositions": ["non_default_session_idle_started_s3_5100"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/config.h#L51-L53"}, {"role": "strict S3 deadline predicate", "path": "src/util.h", "symbol": "UDSTimeAfter", "lines": "13", "atomic_propositions": ["default_session_entered_due_to_s3"], "url": "https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/util.h#L13"}]`
- Hook：Start only from a fixed s3_session_timeout_timer assignment owned by the current tester/session. A reset first satisfies the old word and then opens another. Emit cause-specific timeout at lines 1583-1587, stamp logical deadline, and retain actual poll time.
- 正例 timed word：`[{"time": 0, "props": ["non_default_session_idle_started_s3_5100"]}, {"time": 5100, "props": ["default_session_entered_due_to_s3"]}, {"time": 5101, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["non_default_session_idle_started_s3_5100"]}, {"time": 5099, "props": ["default_session_entered_due_to_s3"]}, {"time": 5101, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["non_default_session_idle_started_s3_5100"]}, {"time": 5101, "props": ["default_session_entered_due_to_s3"]}, {"time": 5102, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["non_default_session_idle_started_s3_5100"]}, {"time": 5101, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: timeout cause is separated from explicit default-session entry, all start/reset/cancel hooks are fixed, and early plus late/missing boundary oracles are included.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：AUTOSAR's unoverwritten default is 5000 ms; 5100 ms is an iso14229 configured profile. UDSTimeAfter is strict >, so the exact 5100 ms conformance oracle may expose a one-tick implementation discrepancy without adding tolerance.
