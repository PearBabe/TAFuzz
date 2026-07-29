# SSH MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：1
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## SSH-REKEY-01 — One-hour KEXINIT initiation proxy under a controlled OpenSSH profile

- 性质：显式配置一小时 rekey_interval，认证完成、当前不在 KEX、peer 允许 rekey 且已有可发送 packet 时，本地应在一小时内发起 KEXINIT 或连接已关闭。
- 规范：[RFC 4253 RFC 4253 §9](https://www.rfc-editor.org/rfc/rfc4253.html#section-9)；强度 `CONTROLLED_PROXY_FOR_RFC_RECOMMENDATION`；时间 `3600000 ms`（`NORMATIVE_RECOMMENDED_PROFILE`）。
- 规范短摘录：“keys be changed after each gigabyte or after each hour”
- 数学 MITL：`G (ssh_rekey_eligible_one_hour_profile -> F [0,3600000] (ssh_local_kexinit_started || ssh_connection_closed))`
- MightyPPL（finite weak outer global）：`G* (ssh_rekey_eligible_one_hour_profile -> F [0,3600000] (ssh_local_kexinit_started || ssh_connection_closed))`
- AP：`ssh_rekey_eligible_one_hour_profile, ssh_local_kexinit_started, ssh_connection_closed`
- AP 定义：{"ssh_rekey_eligible_one_hour_profile": "Authenticated OpenSSH connection has rekey_interval=3600, is not already in KEX, peer permits rekey, and a packet-processing opportunity exists.", "ssh_local_kexinit_started": "The local endpoint actually begins KEXINIT for the next key exchange.", "ssh_connection_closed": "The correlated SSH transport closes before the local initiation deadline."}
- Correlation：OpenSSH ssh/session_state pointer + connection tuple; packet sequence counters remain fields
- 投影：correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[vegard/openssh-portable@7cfea58cb313 `packet.c:1043-1085`](https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L1043-L1085)；符号 `ssh_packet_need_rekeying`。
- 主源码映射 AP：`["ssh_rekey_eligible_one_hour_profile"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "successful local KEXINIT start/send path", "repository": "vegard/openssh-portable", "commit": "7cfea58cb313a27b90aa4563cf65904bdf2fc5f3", "path": "packet.c", "symbol": "ssh_packet_send2", "lines": "1313-1360", "url": "https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L1313-L1360", "legacy_exact_url": "https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L1313-L1351", "atomic_propositions": ["ssh_local_kexinit_started"]}, {"role": "one-hour profile installation into packet state", "repository": "vegard/openssh-portable", "commit": "7cfea58cb313a27b90aa4563cf65904bdf2fc5f3", "path": "packet.c", "symbol": "ssh_packet_set_rekey_limits", "lines": "2429-2435", "url": "https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L2429-L2435", "legacy_exact_url": "https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L2428-L2445", "atomic_propositions": ["ssh_rekey_eligible_one_hour_profile"]}, {"role": "server default disables time rekey unless the benchmark installs the declared profile", "repository": "vegard/openssh-portable", "commit": "7cfea58cb313a27b90aa4563cf65904bdf2fc5f3", "path": "servconf.c", "symbol": "fill_default_server_options", "lines": "284-289", "url": "https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/servconf.c#L284-L289", "atomic_propositions": ["ssh_rekey_eligible_one_hour_profile"]}, {"role": "correlated transport close action", "repository": "vegard/openssh-portable", "commit": "7cfea58cb313a27b90aa4563cf65904bdf2fc5f3", "path": "packet.c", "symbol": "ssh_packet_close", "lines": "574-588", "url": "https://github.com/vegard/openssh-portable/blob/7cfea58cb313a27b90aa4563cf65904bdf2fc5f3/packet.c#L574-L588", "atomic_propositions": ["ssh_connection_closed"]}]`
- Hook：At ssh_packet_need_rekeying's time-profile true branch, emit eligibility only after confirming rekey_interval=3600 and the declared role/peer guards. Emit ssh_local_kexinit_started only after ssh_packet_send2 successfully passes the KEXINIT packet to ssh_packet_send2_wrapped. Emit ssh_connection_closed when ssh_packet_close begins closing the correlated descriptors.
- 正例 timed word：`[{"time": 0, "props": ["ssh_rekey_eligible_one_hour_profile"]}, {"time": 3600000, "props": ["ssh_local_kexinit_started"]}, {"time": 3600001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["ssh_rekey_eligible_one_hour_profile"]}, {"time": 3600001, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["ssh_rekey_eligible_one_hour_profile"]}, {"time": 3600001, "props": []}]}`
- 独立审计：`APPROVE_WITH_CAVEAT`；AP-to-source mapping completed at fixed OpenSSH commit. The one-hour value is an explicit experiment profile installed through ssh_packet_set_rekey_limits; servconf.c proves the server default is zero, so the property is not presented as an OpenSSH default. Historical broad source URLs are retained only as nested legacy_exact_url evidence.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `MEDIUM` / `MEDIUM`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This is a controllable local-initiation proxy, not proof that new keys were installed; peer stall/completion is classified separately and no RFC-equivalence claim is made.
