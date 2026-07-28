# CAN/UDS、DDS/RTPS、Modbus/TCP、OPC UA 候选性质独立审计

审计日期：2026-07-13（Asia/Shanghai）  
审计范围：`_staging/industrial_protocols/` 下 20 条候选性质，以及对应
`evidence.json`、`excluded.md` 和固定 commit 源码。  
审计约束：只读核验 staging；未修改候选、未构建 SUT、未运行 fuzzing。本文件是本次
审计的唯一写入。

## 结论摘要

| 结果 | 数量 | 条目 |
|---|---:|---|
| `APPROVE` | 3 | UDS-P2STAR-01、OPCUA-SC-02、OPCUA-PUB-01 |
| `FIX` | 15 | CANTP-NBS-01、CANTP-NCR-01、UDS-P2-01、UDS-S3-01、RTPS-REL-01、RTPS-REL-02、RTPS-DISC-01、RTPS-DISC-02、DDS-WRITE-01、OPCUA-SC-01、OPCUA-SESS-01、OPCUA-SUB-01、OPCUA-SUB-02、OPCUA-SUB-03、OPCUA-SUB-04 |
| `REJECT` | 2 | UDS-S3-02、MODBUS-TCP-01 |

`APPROVE` 表示该条的规范义务、实例化常数、AP 和主要源码证据实质上成立；由于三个协议组
的证据清单仍为 `IN_PROGRESS`，并且下述 `G*`/重复触发问题仍需做全局处理，它不等于已经
允许直接进入论文主张或最终目录。`REJECT` 针对当前公式与 claim；底层主题可重新设计成
不同性质后再提交。

## 跨协议阻断项

1. **证据包尚未完成。** CAN/UDS、DDS/RTPS、OPC UA 的 `evidence.json` 都标为
   `IN_PROGRESS`，三份 `excluded.md` 也只有“提取中”的占位文字。CAN/UDS evidence
   还漏列实际使用的 DCM §7.2.4.14；DDS/RTPS evidence 漏列 RTPS-REL-01 使用的
   §8.4.7.1/§8.4.9.2.11 和 DDS-WRITE-01 使用的 §2.2.2.4.2.11。当前不满足“证据账本与
   排除项闭合”的入库门槛。
2. **没有使用付费 ISO 二手文本，但作用域必须收窄。** CAN-TP/UDS 六条只以公开的
   AUTOSAR R24-11 文本为规范依据；它们不能写成 ISO 15765 或 ISO 14229 全局合规性质。
   `CAN/UDS` 应显示为 “AUTOSAR CAN-TP/DCM + 指定实现 profile”。
3. **所有 20 条的 `mathematical_mitl` 都写了 `G*`。** MightyPPL README 明确把带星号
   的时序算子定义为 weak semantics；这不是普通 MITL 文献里无条件可互换的 `G`。
   与此同时卡片又统一写 “strict pointwise”。应把“数学 MITL”字段改成普通 `G`，把
   MightyPPL 为有限词选择 `G*` 的理由和末尾语义单独写清，或证明二者在每条投影上的
   等价性。
4. **重复触发压力测试暴露了实际风险。** 对
   `G* (a -> (G [0,200) !b && F [0,200] b))`，TAMonitor 对
   `0:{a},100:{a},300:{b}` 给出 `POSITIVE`，而单触发
   `0:{a},300:{b}` 给出 `NEGATIVE`，symbolic/concrete 一致。前者若按普通 MITL 理解，
   第一个 obligation 已逾期；若按“第二次事件重启并取消旧 timer”理解，则结果又是期望
   的。当前公式没有 cancellation AP，因此不能靠这个结果区分逻辑语义与 timer-restart
   语义。涉及 restart/coalescing 的卡片必须采用“每个 timer generation 单独投影”，或
   显式加入 `superseded/cancelled` AP，再做多触发 oracle。
5. **构造通过不代表规范通过。** 20/20 当前公式均能以 `finite + flatten` build；当前
   positive 都是 `POSITIVE`、negative 都是 `NEGATIVE`，symbolic/concrete 一致。但绝大
   多数双边窗口只测试“过早动作”，没有测试“到点仍无动作”；删掉 liveness 分支的错误
   公式也可能通过现有负例。每条双边窗口至少应有 `negative_early` 与
   `negative_late_or_missing`。
6. **deadline 与 callback 不能混用。** 多个标准约束 timer 的配置/到期，卡片却监测事件
   循环回调或真正发送。OS 调度延迟会把 deadline 正确的实现判成迟到。协议 verdict 应
   优先记录 `timer_armed(deadline)`、`deadline_reached`；callback dispatch 单独作为实现
   性能事件。不能未经规范依据添加 epsilon。
7. 20/20 主 `source_path` 和所列行号都能从 40 位固定 commit 解析，且处于相应 enclosing
   symbol；但若干关键 AP 只在 `instrumentation_timing` 里提到另一个函数/行号，未成为可
   机器核验的独立 hook。尤其是 UDS-P2-01 trigger、RTPS-REL-01 restart、RTPS-DISC-01
   实际 send、DDS-WRITE-01 实际 resource wait、OPC UA Session/Subscription reset。

## CAN/UDS

规范依据是公开的
[AUTOSAR CP SWS CAN Transport Layer R24-11](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_CANTransportLayer.pdf)
和
[AUTOSAR CP SWS Diagnostic Communication Manager R24-11](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf)。
前者 SHA-256 为
`7334d633b02c443aacbe0ca25e20c319e977104eeb4bf8e67ac0358cfea34a22`，后者为
`cf5aeee78fda6e5a25f982f04cb146ce4a75586de7ba41913d46b0cea1cc2407`。

### CANTP-NBS-01 — `FIX`

- AUTOSAR 的 N_Bs abort 义务和参数单位成立，1000 ms 也确实是
  python-can-isotp 固定 commit 的默认值：
  [`protocol.py:349-354`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L349-L354)。
  但 AUTOSAR 没有给 N_Bs 通用默认值，因此只能是实现 profile。
- 规范锚点应同时列启动规则 `[SWS_CanTp_00315]` 和 abort 规则
  `[SWS_CanTp_00316]`。当前只列后者，无法证明计时起点。
- AUTOSAR 从 FirstFrame/最后一帧的发送确认或 FC(WAIT) 开始 N_Bs；该库在
  [`_start_rx_fc_timer`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L1250-L1252)
  处直接启动，可能早于外部 `txfn` 的实际发送确认。必须选择并声明“实现 timer profile”
  或改到真实 Tx-confirmation hook，不能把两个起点当成同一事件。
- 库的
  [`Timer::is_timed_out`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/tools.py#L48-L52)
  使用严格 `elapsed > timeout`。因此当前“1000 ms 恰好 abort”的 positive trace 与锁定源码
  不一致；它只可作为规范 oracle。补 `1001 ms abort/no FC` 的实现压力 trace，并明确该差异。
- 当前反例只覆盖 999 ms 提前 abort。增加 1000 ms 后仍无 FC/abort 的 late/missing 反例；
  FC(WAIT) 在同一 valuation 中结束旧 generation 并启动新 generation。

### CANTP-NCR-01 — `FIX`

- 1000 ms 默认值和 AUTOSAR 的 N_Cr abort 义务成立；规范锚点应补启动条款
  `[SWS_CanTp_00312]`，当前只列 `[SWS_CanTp_00313]`。
- 主源码范围
  [`protocol.py:890-894`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L890-L894)
  只覆盖 timeout abort；还需固定 accepted-CF/restart
  [`protocol.py:959`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L959)
  和 timer start
  [`protocol.py:1254-1256`](https://github.com/pylessard/python-can-isotp/blob/7b44c5282ee390df4977b710218564eb73e2dc2a/isotp/protocol.py#L1254-L1256)。
- 同样受 `elapsed > timeout` 影响，当前 1000 ms 正例不是锁定实现的实际边界。需区分规范
  deadline 与 callback，并补 late/missing 反例。
- correlation 的 receive generation + expected sequence number 合理；错误序号不得被标成
  `consecutive_frame_received`，非 final CF 应在同一 microstep 结束旧窗口并开始新窗口。

### UDS-P2-01 — `FIX`

- `[SWS_Dcm_00024]` 的真实义务是在 `P2ServerMax`/`P2StarServerMax` 减去相应 server
  adjustment 时发送最终响应或 NRC 0x78。50 ms 只来自 iso14229 的
  `UDS_SERVER_DEFAULT_P2_MS`，不是 AUTOSAR 默认；该 profile 必须显式固定 adjustment=0。
- 卡片的主源码范围
  [`server.c:1581-1638`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1581-L1638)
  不包含其 trigger 所称的 request acceptance
  [`server.c:1653-1658`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1653-L1658)。
  应把 request-start、NRC/final send、配置常数做成三个可机器核验 hook。
- `UDSTimeAfter` 是严格 `>`；同时该实现的 `p2_timer` 可能早于本次 request acceptance，
  所以实际响应可以提前，但不应晚于 profile 上界。记录 `deadline_snapshot`，不要用 poll
  callback 时间替代协议起点。
- 当前 missing-at-51 ms 反例有效；再增加 suppress-positive-response、transport failure 的
  明确分类，防止 projection 文字与公式行为不一致。

### UDS-P2STAR-01 — `APPROVE`

- `[SWS_Dcm_00024]` 支持 NRC 0x78 后在 P2* 窗口内继续给最终响应或新的 0x78；5000 ms
  被正确标为 iso14229 implementation profile，而非 AUTOSAR 默认。
- 固定
  [`UDSServerPoll:1598-1638`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1598-L1638)
  覆盖实际 `UDSTpSend` 和重复 NRC 的 0.3×P2* rearm；正常 1500 ms 重复响应满足 5000 ms
  最大期限。
- AP 以同一 request generation + tester address 关联，并把重复 NRC 同时作为旧窗口结果和
  新窗口 trigger，设计合理。入库时补一句该锁定 profile 等价于 adjustment=0，并为多次
  NRC trace 做一次重复触发回归。

### UDS-S3-01 — `FIX`

- AUTOSAR `[SWS_Dcm_01670]` 的 S3 到期回默认会话义务成立；未覆盖配置时的 AUTOSAR
  默认是 5000 ms，`5100` 是 iso14229 `src/config.h:51-53` 的实现 profile。卡片已正确披露
  这一点。
- trigger 应固定到真实 assignment：进入非默认会话的
  [`server.c:65`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L59-L66)、
  TesterPresent 的
  [`server.c:1313`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1304-L1317)
  和初始化 `server.c:1574`；当前主范围只覆盖 timeout consumer。
- timeout 判断在
  [`server.c:1583-1587`](https://github.com/driftregion/iso14229/blob/b0e92b14fcc384d42bfd01ecd7f745addb6bf761/src/server.c#L1583-L1587)
  使用严格 `UDSTimeAfter(now, deadline)`，所以当前 5100 ms 正例可能在实现上变成 5101 ms。
  这可以保留为 off-by-one conformance oracle，但必须增加 late trace 并在卡片中明确“预期
  发现锁定实现偏差”，而不是暗示源码会通过。
- trigger 必须同时记录 session 非默认；reset AP 只能来自拥有该 session 的连接/测试者。

### UDS-S3-02 — `REJECT`

- 当前公式在同一个 5100 ms 常数上，只把 UDS-S3-01 的“一般 qualifying reset”收窄为
  “已被接受的 TesterPresent”；它被 S3-01 逻辑包含，是同一义务换 trigger，不是新的独立
  性质。
- 卡片引用 `[SWS_Dcm_01666-01667]` 的价值在**并发 TesterPresent 与 DcmDslConnection
  归属**，但公式只在正确连接的请求已经被接受后触发，完全检测不到 foreign connection
  错误重置 owner S3。
- 锁定 iso14229 又没有多个 DcmDslConnection 的模型。若要重新提交，需换成支持多连接的
  SUT，或由 adapter 明确模拟 owner/foreign：`foreign_tester_present` 不得产生
  `owner_s3_reset`，原 owner deadline 仍应生效。否则移入 `DUPLICATE_OBLIGATION`/不支持
  多连接的排除清单。

## DDS/RTPS

规范依据为官方
[OMG DDSI-RTPS 2.5](https://www.omg.org/spec/DDSI-RTPS/2.5/PDF)（SHA-256
`c362eaa590c9c95fc6223359ce1ebfa57776cf7ea1e47824f58d48dc16907088`）和
[OMG DDS 1.4](https://www.omg.org/spec/DDS/1.4/PDF)（SHA-256
`16d6f8385c2ba79f7346dc18c867b624bc6dcc8fcf7c2ec52c55b7ae3dc113f2`）。

### RTPS-REL-01 — `FIX`

- RTPS 2.5 的 reference default `nackResponseDelay=200 ms` 和 must-repair timer transition
  均真实。Fast-DDS 固有默认是 5 ms，因此测试必须显式配置 200 ms，当前 limitations 正确。
- 主源码范围只覆盖 TimedEvent callback
  [`StatefulWriter.cpp:225-232`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L225-L232)；
  真正 restart 在
  [`StatefulWriter.cpp:1953-1956`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L1953-L1956)，
  应成为正式 trigger hook。
- Fast-DDS 的 `nack_response_event_` 是 writer-wide timer，而当前 correlation 以单一
  ReaderProxy 为实例。另一 reader 的 ACKNACK 也可能重启同一 timer；adapter 必须以
  `writer GUID + timer generation + pending reader set` 建模，或明确只允许单 reader
  profile。
- RTPS reference state machine 是进入 must-repair 后等待；Fast-DDS 对后续 ACKNACK 调用
  `restart_timer()`。这是实现 profile 行为，不能悄悄当成 reference transition。加入
  `timer_superseded` AP/逐 generation 投影，并补 late/missing 反例。前述重复触发压力测试
  正是该公式的最小复现。

### RTPS-REL-02 — `FIX`

- RTPS 2.5 的 `heartbeatResponseDelay=500 ms` reference default 和 timer transition 成立；
  Fast-DDS 默认 5 ms，必须由 manifest 记录显式覆盖。
- 固定
  [`WriterProxy.cpp:535-593`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/reader/WriterProxy.cpp#L535-L593)
  同时覆盖 `restart_timer()` 与 `send_acknack()`，主要源码映射成立。
- 新 HEARTBEAT 会重启/合并 timer，但公式只有 unmatch discharge，没有 supersession。把每个
  WriterProxy timer generation 分开，或加入 `heartbeat_response_timer_restarted`；不能让
  第二个 trigger 无声明地消灭第一个 obligation。
- 当前反例只测 499 ms 提前 ACKNACK。增加 500 ms 后仍无 send/unmatch 的反例；send AP
  应在实际 RTPS send handoff，而不是 callback entry。

### RTPS-DISC-01 — `FIX`

- RTPS 2.5 §9.6.2.4 明确定义 SPDP periodic announcement reference default 为 30 秒；
  Fast-DDS stock profile 是 3 秒，必须显式配置 30 秒，当前限定正确。
- 主源码
  [`PDP.cpp:1534-1545`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/builtin/discovery/participant/PDP.cpp#L1534-L1545)
  只设置下一 interval，没有覆盖 AP 所称的实际发送。补
  [`PDP.cpp:534-539`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/builtin/discovery/participant/PDP.cpp#L534-L539)
  的 `announceParticipantState(false)` 固定 hook。
- 明确选择监测 timer deadline 还是事件循环中的实际 announcement；若监测后者，30 秒精确
  liveness 会混入 scheduler delay。保留 early 与 late/missing 两类反例，并保证 startup
  burst/directed announcement 不进入 AP。

### RTPS-DISC-02 — `FIX`

- 当 `PID_PARTICIPANT_LEASE_DURATION` 缺失时，表 9.18 的 100 秒 default 成立；CycloneDDS
  固定
  [`q_ddsi_discovery.c:835-840`](https://github.com/eclipse-cyclonedds/cyclonedds/blob/2cdd114cbd18340c606573b4cc8dc20cc161ec5a/src/core/ddsi/src/q_ddsi_discovery.c#L835-L840)
  也按 100 秒实例化。
- 规范表述是超过 lease 后 participant **可以**被认为已离开；一旦本地作出该结论，才要求
  reconfigure。它没有给出“100000 ms 恰好完成物理删除”的强 liveness deadline。当前
  `F[0,100000] removed` 过度增强规范。
- 修复为协议级 no-early-removal safety：100 秒前不得仅因该 lease 删除。若另做 CycloneDDS
  实现 liveness，需给 event-loop/lease scanner 的真实上界；不能自造 epsilon。
- 固定
  [`q_lease.c:218-292`](https://github.com/eclipse-cyclonedds/cyclonedds/blob/2cdd114cbd18340c606573b4cc8dc20cc161ec5a/src/core/ddsi/src/q_lease.c#L218-L292)
  还明确对依赖 privileged participant 的条目推迟 200 ms。当前 limitations 虽提到，但
  trigger/AP 必须编码该排除，而不能只写自然语言。

### DDS-WRITE-01 — `FIX`

- DDS 1.4 的默认 `max_blocking_time=100 ms`、资源等待最大时长、TIMEOUT 以及特定条件下
  可立即 OUT_OF_RESOURCES 均有正式依据；公式没有强迫必须等满 100 ms，边界方向正确。
- 固定
  [`DataWriterImpl.cpp:1003-1071`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/fastdds/publisher/DataWriterImpl.cpp#L1003-L1071)
  只证明函数入口计算 absolute deadline 并把它传给 history。它没有证明 AP 所称“无法立即
  reserve 后实际进入 resource wait”的具体 predicate/hook。
- `max_blocking_time` 约束因资源不足产生的阻塞，不是序列化或整次 `write()` 的总执行时长。
  应在 history 的 wait predicate 上补固定 commit/文件/行，或把 trigger 改成
  `write_deadline_created_100ms` 并相应收窄 claim。
- 增加“立即 OUT_OF_RESOURCES”正例和“resource wait 超过 100 ms 才返回”的负例；保留
  writer GUID + thread operation sequence correlation。

## Modbus/TCP

规范依据为官方
[MODBUS Messaging on TCP/IP Implementation Guide V1.0b](https://www.modbus.org/file/secure/messagingimplementationguide.pdf)
（SHA-256 `065d71170475642e82f370c648bf5135263cb20f61ce92c921add975fab6f669`）。

### MODBUS-TCP-01 — `REJECT`

- §4.4.1.4 明确拒绝给 MODBUS/TCP transaction 规定统一 response time；500 ms 仅是
  libmodbus 固定
  [`_RESPONSE_TIMEOUT`](https://github.com/stephane/libmodbus/blob/5190e5e141780ae481f24be16d7b39a5f3ad8f8f/src/modbus-private.h#L40-L42)
  的实现默认值。因此它不能计入“具有规范锚点的协议主性质”。
- 更严重的是，当前实现 profile 公式本身也错误：
  [`_modbus_receive_msg:409-415`](https://github.com/stephane/libmodbus/blob/5190e5e141780ae481f24be16d7b39a5f3ad8f8f/src/modbus.c#L409-L415)
  先用 response timeout 等初始数据；一旦仍需读后续字节，
  [`src/modbus.c:510-520`](https://github.com/stephane/libmodbus/blob/5190e5e141780ae481f24be16d7b39a5f3ad8f8f/src/modbus.c#L510-L520)
  会改用并重新装载 byte timeout。即使两个默认值均为 500 ms，完整 confirmation 也可能在
  500 ms 之后合法完成。
- 自定义 trace `wait@0, full-confirmation@800` 被当前公式判为 `NEGATIVE`，但只要首字节在
  500 ms 内且相邻读取未超 byte timeout，它可以符合锁定 libmodbus 行为。这证明不是单纯
  “标准强度标签”问题，而是 consequent 选错了事件。
- 从主目录撤回。若需要实现附录，重写为：(a) 首个可读响应数据或初始 ETIMEDOUT 在配置的
  response timeout 内；(b) 每个后续 read generation 的 byte-gap timeout。二者都标
  `IMPLEMENTATION_PROFILE`，不能用于 MODBUS/TCP 跨实现合规结论。

## OPC UA

规范依据为 OPC Foundation 官方、版本固定的 OPC 10000-4 v1.05.07 页面：
[§5.6.2.1](https://reference.opcfoundation.org/Core/Part4/v105/docs/5.6.2.1)、
[§5.7.2.2](https://reference.opcfoundation.org/Core/Part4/v105/docs/5.7.2.2)、
[§5.14.1.1](https://reference.opcfoundation.org/Core/Part4/v105/docs/5.14.1.1)、
[§5.14.2.2](https://reference.opcfoundation.org/Core/Part4/v105/docs/5.14.2.2) 和
[§7.32](https://reference.opcfoundation.org/Core/Part4/v105/docs/7.32)。

### OPCUA-SC-01 — `FIX`

- §5.6.2.1 的指导是 client 在 token lifetime 已经过 75% 后请求新 token；它不是
  “450000 ms 恰好请求”。600000 ms 是 open62541 profile，来源
  [`ua_config_default.c:1115-1118`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/plugins/ua_config_default.c#L1115-L1118)
  正确。
- 当前 `no renew before 450000 && F[0,450000] renew` 把 after-75% 错写成精确 75%。一个
  在 500000 ms、旧 token 尚未到期前发出的 renewal 被当前 TAMonitor 判为 `NEGATIVE`，
  但不应仅因不是恰好 75% 就判违规。
- 保留 `G[0,450000)(!renew)` 的 no-early 部分；若要给上界，应基于“旧 token 到期前请求”
  将 `SHOULD` 实例化为 `[450000,600000)`，并把 channel close/supersession 明确 discharge。
- 固定源码
  [`ua_client_connect.c:560-565`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/client/ua_client_connect.c#L560-L565)
  确实计算 75% deadline，`__Client_renewSecureChannel` 在到达/超过它时才发起；源码映射本身
  成立。

### OPCUA-SC-02 — `APPROVE`

- §5.6.2.1 明确建议 client 在 token 到期后最长 25% lifetime 的 overlap 内接受用旧 token
  保护的消息；600000 ms profile 对应 150000 ms，当前条件式 safety oracle 与 AP 方向
  正确。
- correlation 以 SecureChannelId + old tokenId + requestId；只对通过 framing/crypto 前置
  条件的消息置 `old_token_message_received`，并把同一 callback 的 GOOD result 原子合并，
  可避免不同消息互相满足。
- 固定
  [`checkSymHeader:505-568`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/ua_securechannel_crypto.c#L505-L568)
  在原 lifetime 后就会关闭 channel，可能不实现 25% grace；卡片已正确把它当成预期能发现
  偏差的 conformance oracle，而不是声称实现会通过。
- 入库时保留“显式 channel close/old-token rollover 后结束该 token projection”，并在人工
  审核中确认整数毫秒端点 150000 取闭区间的约定。

### OPCUA-SESS-01 — `FIX`

- §5.7.2.2 把 revisedSessionTimeout 定义为 session 无活动保持 open 的实际最大毫秒数，
  超过该区间 server 应自动终止；以服务端返回的 revised value 实例化是正确方法。
- 1200000 ms 只是 client request default：
  [`ua_config_default.c:1173-1174`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/plugins/ua_config_default.c#L1173-L1174)。
  trigger 已要求 revised value 恰为该值，避免把 request 当 negotiated result，这点成立。
- 主源码只列 cleanup
  [`ua_services_session.c:114-125`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_session.c#L114-L125)；
  应把 `UA_Session_updateLifetime` 和实际 Service activity 的固定 hook 作为正式映射，并加入
  explicit CloseSession/server shutdown discharge。
- 锁定源码使用 `validTill >= now -> continue`，因此只在 `now > validTill` 时清理；当前公式
  会把 1200001 ms 才终止判为 `NEGATIVE`。这可作为精确上界 oracle，但要明确是预期源码
  discrepancy，并区分 timer deadline 与周期 cleanup callback；不能悄悄加 1 ms 容差。

### OPCUA-SUB-01 — `FIX`

- §5.14.1.1 明确说明创建 Subscription 后第一个 Message 在第一个 publishing cycle 末发送；
  无 notification 时也应发首次 keep-alive。500 ms 只来自 client request default，卡片已
  要求 revised interval=500，方向正确。
- 当前 trigger 只证明起点时已有 Publish request，文字却要求它“整个首周期持续可用”。若
  request 中途因 timeout/Session close 消失，公式仍强制 response。加入
  `publish_request_unavailable/session_closed/subscription_deleted` discharge，或给出可执行的
  generation 投影规则，不能靠未来条件静默删 trace。
- 固定
  [`Subscription_setState:707-758`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L707-L758)
  证明 repeated callback 注册和首次 keepalive counter 设置；还需把 CreateSubscription
  success、revised value 与实际 `sendResponse` 做成独立 hooks。
- 公式精确要求 500 ms actual send，会混入 scheduler delay。协议 oracle 记录 publishing
  timer deadline，actual response 作为后续性能/实现事件；新增到点仍无 response 的反例。

### OPCUA-SUB-02 — `FIX`

- §5.14.1.1/§5.14.2.2 对 maxKeepAliveCount 的计数义务真实；revised 500 ms × count 10
  得到 5000 ms profile 合理。
- 当前 projection 声称 notification、删除、参数变化、Publish queue 消失都结束窗口，但
  公式只有 notification result，没有其余 cancellation AP。在线 adapter 不能仅靠自然语言
  让已有 obligation 消失。
- 固定
  [`UA_Subscription_publish:477-510`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L477-L510)
  覆盖 counter/check/send 分支，但 trigger 所称的 counter reset 在 `609-610`，超出主范围；
  补正式 hook。
- 加 `keepalive_window_cancelled` 或逐 generation 投影，区分 timer deadline 与 send callback，
  并补 late/missing 反例。

### OPCUA-SUB-03 — `FIX`

- 规范要求没有可用 Publish request 时每个 publishing cycle 增加 lifetime counter，并在
  counter **达到** revisedLifetimeCount 时关闭。500 ms × 10000 的 profile 有真实依据。
- 固定
  [`ua_subscription.c:455-474`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L455-L474)
  先 increment、再用 `currentLifetimeCount > lifeTimeCount`，看起来会比规范晚一个周期；这是
  有价值的 conformance oracle，不应通过改成 5000500 ms 来迎合源码。
- 但当前公式没有编码 manual deletion、transfer、parameter change 等 projection 终止，且
  trigger 所称 `Subscription_resetLifetime`/queue transition 没有完整固定 hook。补
  `lifetime_window_cancelled` 或逐 generation 的显式结束规则。
- 当前反例只测 5000001 ms 仍未关闭，补“5000000 ms 前因 lifetime 提前关闭”反例，覆盖
  公式的 safety 半边。

### OPCUA-SUB-04 — `FIX`

- “publishing disabled 时不发送 NotificationMessage，但继续周期执行并发送 keep-alive”是
  §5.14.1.1 的真实独立义务；open62541
  [`ua_subscription.c:477-494`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L477-L494)
  也在 disabled 时将 notification count 置零。
- 当前 5000 ms keepalive 半边与 SUB-02 重复；唯一新增价值是 disabled epoch 内无
  notification。建议拆成：(a) disabled-until-reenabled 的 safety；(b) 引用 SUB-02 的
  keepalive timer，而不是用同一常数再造一条主性质。
- 公式没有 `reenabled/deleted/queue_unavailable/parameter_changed` discharge。特别是在
  5000 ms microstep 恰好 re-enable 并发送 notification 时，闭区间
  `G[0,5000] !notification` 会误报。必须声明 microstep 顺序和 epoch end AP。
- 当前 trigger 是 adapter 合成的 counter boundary，而非 SetPublishingMode reception；这是
  可行 profile，但要给 counter reset、mode transition、sendResponse 三个固定 hooks。

### OPCUA-PUB-01 — `APPROVE`

- §7.32 将 timeoutHint 定义为 server 可参考的 hint，并要求 server 在取消前至少等待该
  timeout；它不要求到点必须取消。当前只有
  `G[0,5000)(!publish_bad_timeout)`，没有虚构 exact-eventual，强度正确。
- 5000 ms 来自实际 request field，而不是实现默认；Session + Publish requestId correlation
  清晰，正常 response 后不会再为同一 requestId 产生 Bad_Timeout。
- 固定
  [`ua_subscription.c:427-452`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L427-L452)
  使用 `pre->maxTime < now`，与“5000 ms 前不得取消、5000 ms 处允许但不强制”的公式相容。
  入库时把 `ua_services_subscription.c:304-315` 的 queue/maxTime producer 也登记为第二 hook。

## 证据包修复清单

| 协议组 | 当前状态 | 必须修复 |
|---|---|---|
| CAN/UDS | `IN_PROGRESS`；排除清单为占位 | 明确 AUTOSAR-only scope；补 DCM §7.2.4.14、CAN-TP timer-start 条款；列 ISO 付费文本未使用；登记两条 profile 常数及重复 S3 排除 |
| DDS/RTPS | `IN_PROGRESS`；排除清单为占位 | 补实际 sections；记录 Fast-DDS 5 ms/3 s/20 s stock profile 与 reference profile 差异；列 infinite/configurable QoS、lease exact-removal 排除 |
| Modbus/TCP | `COMPLETE_PENDING_MACHINE_VALIDATION` | 将主候选撤回；保留“规范无数值上界”结论；若留 libmodbus 附录，拆分 initial-response 与 byte-gap 两种 timer |
| OPC UA | `IN_PROGRESS`；排除清单为占位 | 给所有 revised 参数写明 request≠revised；记录 SHOULD 与 SHALL；补 close/re-enable/transfer/queue-loss 例外和 open62541 已知边界偏差 |

## 证据与验证记录

### 读取的证据文件

- `analysis/protocol_fuzzing_study/_staging/industrial_protocols/{can_uds,dds_rtps,modbus_tcp,opc_ua}/proposals.json`
- 同目录每个协议组的 `evidence.json` 与 `excluded.md`
- 上述 AUTOSAR、OMG、Modbus Organization、OPC Foundation 官方规范
- 候选记录的固定 commit 源码；补查 python-can-isotp `tools.py`、iso14229 `config.h`、
  Fast-DDS 的实际 timer restart/send、CycloneDDS lease default、open62541 config/session/
  subscription producer hooks、libmodbus byte-timeout 分支
- MightyPPL README 对 strict/weak（starred）模态的定义

### 实际验证命令与观察结果

```text
python3 -m json.tool <each proposals.json/evidence.json>
# 8/8 JSON 可解析；候选计数为 6 + 5 + 1 + 8 = 20。

# 在 /tmp/industrial_audit_validation 下为每条生成 formula/positive/negative，调用：
tool/MightyPPL/build/TAMonitor --formula <formula> --word finite \
  --build-mode flatten --state {symbolic,concrete} --trace <trace> --out <tmp-out>
# 20/20 build rc=0；20/20 positive=POSITIVE；20/20 negative=NEGATIVE；
# symbolic/concrete 20/20 一致。未写 staging 或正式 validation 目录。

# 对固定 raw source 检查 source_lines，并人工核验 enclosing symbol 与辅助 hook。
# 20/20 主 source 文件存在，20/20 所列行号有效；关键辅助 hook 缺口见逐条意见。

# 附加边界/真实性压力 trace（symbolic 与 concrete 结果一致）：
RTPS repeated trigger: 0:{a},100:{a},300:{b} -> POSITIVE
RTPS single trigger:   0:{a},300:{b}          -> NEGATIVE
OPCUA-SC-01 renew@500000                     -> NEGATIVE
RTPS-DISC-02 remove@101000                   -> NEGATIVE
MODBUS-TCP-01 full confirmation@800          -> NEGATIVE
OPCUA-SESS-01 cleanup@1200001                -> NEGATIVE
```

官方规范文件在本次审计中的下载日期均为 2026-07-13；上文列出的 SHA-256 可用于后续复核
版本。未使用受限 ISO 文本或第三方转述替代规范。

## 未决问题

1. 需要主代理决定数学目录是否坚持普通 MITL `G`，以及 MightyPPL 有限词为什么使用
   weak `G*`；在该解释固定前，不应把 single-trigger PASS 写成逻辑正确性证明。
2. restart/coalescing 性质是统一加入 `timer_generation_superseded` AP，还是由 trace adapter
   保证每个 generation 恰好一个 trigger，需要形成全局 schema 决策。
3. 对规范给出精确最大值、但实现采用周期 callback/严格 `>` 的情况，应同时保留
   normative deadline oracle 和 callback-latency 诊断；不能为让实现通过而添加无依据容差。
4. OPC UA SC-02 的 25% 端点在整数毫秒模型中采用闭还是开区间，应由人工审核统一；这不
   影响“open62541 在 grace period 内提前拒绝”这一主要 oracle。
5. Modbus/TCP 若主目录硬性要求正式协议数值锚点，应计 0 条主性质，而不是保留一个
   implementation profile 凑数。
