# DICOM MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：1
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## DICOM-ARTIM-01 — DCMTK profile expires ARTIM after 30 seconds awaiting A-ASSOCIATE-RQ

- 性质：DCMTK storescp 30 秒 acceptor profile 中，接受 TCP 后 ARTIM 不得提前 expiry；须在 30000 ms expiry，或此前收到 A-ASSOCIATE-RQ、连接关闭/解析终止。
- 规范：[DICOM PS3.8 DICOM PS3.8 2026c §9.1.5, 9.2.2 AE-5/AA-2T](https://dicom.nema.org/medical/dicom/current/output/chtml/part08/chapter_9.html#sect_9.1.5)；强度 `SHALL timer; duration IMPLEMENTATION_PROFILE`；时间 `30000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“a timer ARTIM (Association Request/Reject/Release Timer) shall be set”
- 数学 MITL：`G (dicom_tcp_connection_accepted_dcmtk_30s_profile -> (G [0,30000) (!dicom_artim_expired) && F [0,30000] (dicom_artim_expired || dicom_associate_rq_received || dicom_transport_closed_or_parse_abort)))`
- MightyPPL（finite weak outer global）：`G* (dicom_tcp_connection_accepted_dcmtk_30s_profile -> (G [0,30000) (!dicom_artim_expired) && F [0,30000] (dicom_artim_expired || dicom_associate_rq_received || dicom_transport_closed_or_parse_abort)))`
- AP：`dicom_tcp_connection_accepted_dcmtk_30s_profile, dicom_artim_expired, dicom_associate_rq_received, dicom_transport_closed_or_parse_abort`
- AP 定义：{"dicom_tcp_connection_accepted_dcmtk_30s_profile": "storescp acceptor passes opt_acse_timeout=30 and DUL receives the TCP transport connection.", "dicom_artim_expired": "PRV_NextPDUType returns DUL_READTIMEOUT and dispatches ARTIM_TIMER_EXPIRED.", "dicom_associate_rq_received": "A valid A-ASSOCIATE-RQ PDU is recognized for this association.", "dicom_transport_closed_or_parse_abort": "Peer transport close or terminal malformed-PDU/abort branch ends this waiting generation."}
- Correlation：DUL association pointer + TCP 4-tuple; presentation-context IDs stay fields
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[DCMTK/dcmtk@7f8564cf11e5 `dcmnet/libsrc/dul.cc:687-707`](https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/libsrc/dul.cc#L687-L707)；符号 `DUL_ReceiveAssociationRQ`。
- 主源码映射 AP：`["dicom_tcp_connection_accepted_dcmtk_30s_profile", "dicom_artim_expired", "dicom_associate_rq_received", "dicom_transport_closed_or_parse_abort"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "storescp ACSE timeout profile constant", "repository": "DCMTK/dcmtk", "commit": "7f8564cf11e5531689dd329523fb16023aeda3ed", "path": "dcmnet/apps/storescp.cc", "symbol": "opt_acse_timeout", "lines": "173", "url": "https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/apps/storescp.cc#L173", "legacy_exact_url": "https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/apps/storescp.cc#L165-L175", "atomic_propositions": ["dicom_tcp_connection_accepted_dcmtk_30s_profile"]}, {"role": "storescp passes the 30-second ACSE profile into the acceptor network", "repository": "DCMTK/dcmtk", "commit": "7f8564cf11e5531689dd329523fb16023aeda3ed", "path": "dcmnet/apps/storescp.cc", "symbol": "main", "lines": "928-940", "url": "https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/apps/storescp.cc#L928-L940", "atomic_propositions": ["dicom_tcp_connection_accepted_dcmtk_30s_profile"]}, {"role": "DUL FSM transport-connection response transition", "repository": "DCMTK/dcmtk", "commit": "7f8564cf11e5531689dd329523fb16023aeda3ed", "path": "dcmnet/libsrc/dulfsm.cc", "symbol": "AE_5_TransportConnectResponse", "lines": "1118-1127", "url": "https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/libsrc/dulfsm.cc#L1118-L1127", "legacy_exact_url": "https://github.com/DCMTK/dcmtk/blob/7f8564cf11e5531689dd329523fb16023aeda3ed/dcmnet/libsrc/dulfsm.cc#L1096-L1127", "atomic_propositions": ["dicom_tcp_connection_accepted_dcmtk_30s_profile"]}]`
- Hook：Emit the trigger after receiveTransportConnection has succeeded and immediately before PRV_StateMachine/PRV_NextPDUType in DUL_ReceiveAssociationRQ, after checking association->timeout=30. Emit timeout, valid A-ASSOCIATE-RQ, transport-close, and parse-abort outcomes from the mutually exclusive branches at dul.cc:698-707; do not synthesize them from wall-clock time alone.
- 正例 timed word：`[{"time": 0, "props": ["dicom_tcp_connection_accepted_dcmtk_30s_profile"]}, {"time": 30000, "props": ["dicom_artim_expired"]}, {"time": 30001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["dicom_tcp_connection_accepted_dcmtk_30s_profile"]}, {"time": 29999, "props": ["dicom_artim_expired"]}, {"time": 30001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["dicom_tcp_connection_accepted_dcmtk_30s_profile"]}, {"time": 30001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Fixed-commit mapping now covers every AP in DUL_ReceiveAssociationRQ: successful transport acceptance, DUL_READTIMEOUT to ARTIM_TIMER_EXPIRED, A-ASSOCIATE-RQ recognition, and close/parse-error termination. storescp profile declaration/use and the historical FSM anchor are structured auxiliary evidence; broad legacy URLs are nested rather than top-level.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The 2020 DCMTK source predates PS3.8 2026c, but the cited ARTIM actions are unchanged; this is a source/profile mapping, not a claim that 30 seconds is standardized.
