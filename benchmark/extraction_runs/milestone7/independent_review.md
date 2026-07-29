# Milestone 7 独立证据闭合审核

## 审核身份与边界

本报告是自动化独立审核，审核者为 Codex 子任务 `/root/adgfuzz_spec_audit`，不是人类 reviewer。人类 reviewer 数量为 0，未执行两人复核或 arbitration，也未作任何接受/拒绝决定。下文的 `PASS` 只表示某一个 gate 的现有证据闭合，不表示性质被人类接受。

审核快照为 `POST_SEMANTIC_CORRECTION_PRE_ENRICHMENT_SNAPSHOT`，时间为 `2026-07-18T08:23:39+08:00`。最终 claims audit 已先将两处“实现语义倒灌到规范”回退为来源忠实表述，本快照再记录纠偏后、Stage-7 重生成前的定义。由于性质 JSON 随后重生成，本报告不保存性质 JSON 的 SHA-256；漂移比较键是 property ID、本地路径、公式文本/实例状态以及冻结来源 locator。机器可读的逐 gate 结果见 [independent_review.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone7/independent_review.json)。

本审核不评价 ArduPilot/PX4 是否已经满足性质。实现源码只用于核对 AP 的真实变量、赋值、函数、状态、消息消费者/生产者和时钟位置；它不构成规范来源或满足性证据。

## 结论

13 条性质中：

- `NEEDS_CONTEXT`: 12
- `CANDIDATE`: 1（`ARD-PLANE-TAKEOFF-001`，唯一来源是低权威 PARAM_METADATA，且当前运行配置禁用）
- `PASS`: 0
- `NEEDS_BINDING`: 0（总体状态；逐 gate 中存在）
- `UNSUPPORTED`: 0（总体状态；13 条的 monitor-readiness gate 均为 `UNSUPPORTED`）

因此，当前没有一条性质可以由本自动审核提升为已完成的人类复核结果。两处已发现的实现语义漂移已在生成器中纠正；性质仍因版本、事件、取消/重置或 AP 观测证据不闭合而保持回退状态。

## 只读验证结果

| 命令 | 结果 |
|---|---|
| `python3 benchmark/scripts/validate_property_catalog.py --stage 6` | exit 0；13 properties、46 AP、13 time contracts；15 runtime instances、8 concrete properties |
| `python3 benchmark/scripts/validate_runtime_capture.py` | exit 0；4/4 captures COMPLETE；15 property parameters；implementation `NOT_ASSESSED` |
| `python3 benchmark/scripts/validate_source_bindings.py` | exit 0；227 source bindings、77 MAVLink observations |
| `python3 benchmark/scripts/validate_milestone6.py` | exit 0；1035 aggregate checks；会改写文件的 MAVLink catalog 子验证器按预期未运行 |

这些 validator 证明 schema、路径、哈希、quote、运行参数记录和绑定位置的一致性；它们不证明自然语言到 MITL 的语义等价，也不证明 AP 的运行时真值可以从当前 trace 精确生成。

## Gate 矩阵

缩写：`P=PASS`、`C=CANDIDATE`、`NC=NEEDS_CONTEXT`、`NB=NEEDS_BINDING`、`U=UNSUPPORTED`。

| Property | Overall | Source/version | Quote/context | Requirement IR | Event logic | Time | AP/source | MAVLink | Provenance | Monitor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ARD-COPTER-GCS-001 | NC | NC | P | NC | NC | P | P | NB | P | U |
| ARD-COPTER-GUID-002 | NC | NC | P | P | NC | P | P | NB | P | U |
| ARD-COPTER-RTL-003 | NC | NC | P | C | NC | P | P | NB | P | U |
| ARD-PLANE-TAKEOFF-001 | C | C | C | C | C | P | P | NB | C | U |
| ARD-ROVER-CRASH-002 | NC | NC | P | P | NC | P | P | NB | P | U |
| ARD-ROVER-RCFS-001 | NC | NC | P | C | NC | P | P | NB | P | U |
| ARD-SHARED-BATT-001 | NC | NC | C | P | NC | P | P | NB | P | U |
| PX4-MC-AUTODISARM-004 | NC | P | NC | NC | NC | NC | NB | NB | P | U |
| PX4-MC-FLIGHTTIME-005 | NC | P | P | P | NC | P | P | NB | P | U |
| PX4-MC-GCSLOSS-002 | NC | P | P | NC | NC | NC | NB | NB | P | U |
| PX4-MC-OFFBOARD-003 | NC | P | NC | NC | U | NC | NB | NB | P | U |
| PX4-MC-RCLOSS-001 | NC | P | P | NC | NC | P | P | NB | P | U |
| PX4-MC-RTLLOITER-006 | NC | P | NC | NC | NC | P | NB | NB | P | U |

## 共同发现

### 来源与上下文

ArduPilot 六条官方行为性质都引用 HIGH authority 的 wiki 快照，但 `document_status=MAIN_ONLY`，尚未证明 wiki revision `209e532...` 与固件 commit `8f2e5d...` 的版本关系。其 quote 内容通常完整，但版本 gate 不能闭合。Plane takeoff 的唯一来源是 [ArduPlane/Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduPlane/Parameters.cpp:1113) 中的 LOW `PARAM_METADATA`；它只能保留为候选，不能作为独立规范直接提升。

PX4 官方文档为 v1.17 release-pinned，来源版本 gate 普遍闭合，但三处上下文冲突仍然存在：

- Auto-disarm：官方页写 `-1` 禁用；冻结 metadata 写 `<=0` 禁用。
- Offboard：同一冻结页同时写 `2 Hz`、`>2 Hz`、`below 2 Hz`，同时写 `more than a second` 和 `at least a second`。
- RTL loiter：官方参数表默认 `0.5 s`，冻结 metadata 默认 `0.0 s`。运行实例必须使用捕获的 PARAM_VALUE，但这不能消除规范文本冲突。

### Requirement IR 与事件关系

最终 claims audit 发现并已回退两条明确的实现语义倒灌：

- `ARD-COPTER-GCS-001` 现已恢复为“最后一个指定 GCS heartbeat 后的缺失区间”；`MANUAL_CONTROL`/`RC_CHANNELS_OVERRIDE` 及 aggregate last-seen 均只标为 `MODELLED` implementation conflict/输入干扰路径。
- `PX4-MC-GCSLOSS-002` 现已恢复为 telemetry/data connection loss；因官方来源没有定义 liveness predicate、关联键或时钟，`MAV_TYPE_GCS` heartbeat/HRT 只保留为 `MODELLED` 当前源码候选映射。

8 条 concrete 公式以及多条 symbolic 公式还有共同的 obligation-lifetime 问题：Requirement IR/time contract 写了 reset/cancel，但 standalone MITL 在 `gap_start` 或 `condition_start` 后仍永久要求未来 response。若在 T 前恢复输入、条件中断、离开模式或禁用性质，公式仍可能要求事件。除非另有经过验证的 trace slicer 在 reset/cancel 时终止 obligation，否则这些公式不闭合。

具体表现包括：

- GCS、Guided、PX4 data-link loss、PX4 manual-control loss：新输入 reset 没进入公式。
- Rover crash：规范要求四个条件连续成立 T 秒，公式只有 start edge。
- Rover low-throttle failsafe：低油门必须连续保持，恢复 reset 未进入公式。
- Battery low-voltage：来源明确写 `continuously`，恢复 reset 未进入公式。
- Flight-time：`eventually` 弱化了 90% warning 和 maximum-time Return，还漏掉每分钟重复 warning。
- RTL：离开模式发生在 T 后、response 前时，unbounded eventual obligation 仍未取消。

### 时间证据

10/13 条性质的数值、禁用域、单位换算和 clock gate 可以独立闭合；所有 concrete 数值仍可从保存的运行参数追溯，而不是源码默认值：

- ArduPilot：5 s GCS、3 s Guided、5000 ms→5 s RTL、2 s crash、1.5 s RC failsafe、10 s battery；Plane `TKOFF_TIMEOUT=0` 明确禁用。
- PX4：10 s data-link loss、0.5 s→500 ms RC loss；Flight-time `-1` 明确禁用；RTL land delay 捕获为 `0.0 s`，其语义是立即边界而不是 `-1` indefinite。

Auto-disarm 的当前 `2 s` 实例可记录，但参数全域因 `-1` 与 `<=0` 冲突不能闭合。Offboard 的 `COM_OF_LOSS_T=1 s` 只解决进入 Offboard 后的 loss window，不解决 2 Hz 与 admission one-second 的冲突。

当来源或当前源码证据能确立时，性质保留 autopilot monotonic boot clock。`PX4-MC-GCSLOSS-002` 的数值为运行时 `10 s`，但规范 loss-start 时钟/载体保持 `UNKNOWN`。发送方 `time_boot_ms`、无时间字段的 heartbeat、GCS host arrival time、GPS `time_usec` 均不能静默替代飞控接收/状态转换时钟；边界受采样影响时应输出 `INCONCLUSIVE`，不能人工补 epsilon。

### AP 多对多绑定与 MAVLink

现有绑定完整性验证通过：ArduPilot 25/25 AP 标为 BOUND；PX4 18 BOUND、3 PARTIALLY_BOUND；共 227 个真实源码绑定。PX4 新增的 partial 来自 data-link-loss 规范事件未能与当前 heartbeat 实现建立等价关系。绑定覆盖变量、字段、赋值、guard、函数、消息消费者/生产者、内部 event 和派生关系。`PASS` 或“存在绑定”不表示现成 wire trace 能直接得到 AP。

三个未闭合的 PX4 AP 是：

- `PX4-MC-AUTODISARM-004-AP-02 auto_disarm_eligible`
- `PX4-MC-OFFBOARD-003-AP-02 offboard_proof_qualified`
- `PX4-MC-GCSLOSS-002-AP-01 data_link_loss_gap_start`

`PX4-MC-RTLLOITER-006` 虽然字段状态为 BOUND，但 exact path/phase 仍依赖缺失的 mission snapshot，因此性质级 AP gate 也保持 `NEEDS_BINDING`。

所有 13 条性质的 MAVLink gate 都是 `NEEDS_BINDING`。常见原因：

- HEARTBEAT 只给粗模式/armed 状态且无内嵌时间，不能证明内部子状态、原因或事件边沿。
- STATUSTEXT 是可丢失、无精确原因/时间的 consequence。
- MAVLink 输入帧证明“发送”，不证明被目标 mode/frame/type-mask/selector 接受。
- ArduPilot GCS/Guided/RTL/crash/battery 和 PX4 selector/connection-lost/phase 等 AP 需要同一 boot clock 的内部 probe。
- PX4 EVENT 在默认 SITL capture 中出现过，但“消息存在”不等于所需 event ID、metadata 和状态转换已经出现；必须冻结 event metadata 并按 ID/boot time 关联。

### Monitor readiness

实测二进制：

- `tool/MightyPPL/build/TAMonitor` SHA-256 `e2dc4f9a77c49fe900e80d544078d9215c01d894a9396e689dd6fab6dd91d7f4`
- `tool/MightyPPL/build/mitppl` SHA-256 `8e2ae06959eec8d3624eb1ce1923cce03c9115790075f317e16658ed933c7951`

8 条 `mitl.concrete` 原文逐条调用 TAMonitor，0/8 可解析。原因可由 [Mitl.g4](/home/lqq/project/TAFuzz/tool/MightyPPL/Mitl.g4:14) 直接复核：grammar 使用 `&&`/`||`，模态后直接接 interval，bound 仅接受整数，并且 temporal modality 的直接操作数必须是 atom，因此 `!ap` 需要括号。catalog 当前使用单 `&`、`G_`/`F_`，两条使用小数秒，且直接写 `G interval !ap`。

执行以下显式转换后，8/8 在 `--word finite --build-mode flatten --build-only` 下 exit 0，正公式均 SAT：

1. 单 `&`/`|` 转 `&&`/`||`；
2. 去掉 modality 与 interval 间的 `_`；
3. 秒边界统一缩放为整数毫秒 tick；
4. 直接位于 temporal modality 下的否定 AP 加括号。

这个结果只证明“转换后的字符串能构建”，不证明 catalog 文本通过 parser、不证明转换语义等价，也不证明 non-tautology、non-vacuity、trace 或 conformance。`monitor_syntax` 当前仍为空。

[TraceParser.cpp](/home/lqq/project/TAFuzz/src/TAMonitor/TraceParser.cpp:46) 只接受无符号整数时间点/闭区间，并支持 `@time props`、`time,props` 和 bit valuation。[MonitorRunner.cpp](/home/lqq/project/TAFuzz/src/TAMonitor/MonitorRunner.cpp:17) 输出 `POSITIVE/NEGATIVE/INCONCLUSIVE`。代表性 finite GCS smoke 中，在 time 0 同时设置 antecedent 与 `gcs_failsafe_event`，最终仍为 `POSITIVE`；按预期 point-valuation 解读，这看起来应是“过早事件”反例。因此在建立小公式 oracle、明确 finite-word/valuation 语义并做差分 trace 测试前，不能信任 verdict。临时输出只写入 `/tmp`，未进入 workspace。

## 逐性质审核

### ARD-COPTER-GCS-001 — NEEDS_CONTEXT

证据：性质 [ARD-COPTER-GCS-001.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-COPTER-GCS-001.json)；官方 quote [gcs-failsafe.rst](/home/lqq/project/TAFuzz/benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/gcs-failsafe.rst:8)；参数 [Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduCopter/Parameters.cpp:828)。

- 来源版本：`NEEDS_CONTEXT`，HIGH wiki 为 MAIN_ONLY。
- Quote：`PASS`，四句话完整给出 heartbeat、timeout、event 和 never-connected exception。
- IR：已恢复为指定 GCS heartbeat；精确 enable/例外/取消仍为 `NEEDS_CONTEXT`。Provenance 门禁因实现路径不再进入 IR 而为 `PASS`。
- Event logic：`NEEDS_CONTEXT`，new designated heartbeat reset 与 cancel 未进入公式。
- Time：`PASS`，捕获 `FS_GCS_TIMEOUT=5 s`；精确候选锚点是 heartbeat handler 中的 `AP_HAL::millis()`，aggregate last-seen 只是 `MODELLED`。
- AP/source：`PASS`，HEARTBEAT consumer 给出规范事件身份；RC override、manual control 和 aggregate last-seen 均显式保留为 `MODELLED` implementation conflict。
- MAVLink：`NEEDS_BINDING`，heartbeat-gap 起点和 GCS-specific event 必须 probe；STATUSTEXT/system_status 只是 lossy consequence。
- Monitor：本报告的 pre-enrichment 快照对 presentation syntax 记为 `UNSUPPORTED`；随后 Stage 7 保存的确定性 monitor-syntax 转换与合成轨迹门禁另行验证，不能把早期 probe 描述成最终监视器结果。

建议：保持 `NEEDS_CONTEXT`；规范 trigger/reset 已恢复为官方 heartbeat 表述，后续只闭合版本、applicability、reset/cancel 和 heartbeat-exclusive 观测。

### ARD-COPTER-GUID-002 — NEEDS_CONTEXT

证据：[ARD-COPTER-GUID-002.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-COPTER-GUID-002.json)；[ac2_guidedmode.rst](/home/lqq/project/TAFuzz/benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/ac2_guidedmode.rst:115)；[Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduCopter/Parameters.cpp:866)。

- Source/version `NEEDS_CONTEXT`；quote 与 Requirement IR `PASS`。作者没有给停止/水平完成上界，当前只约束 response start 是正确的，不能人工添加完成时限。
- Event logic `NEEDS_CONTEXT`：新适用 command 和离开 Guided 的 reset/cancel 未进入公式。
- Time `PASS`：运行 `3 s`，飞控接收 millis；sender `time_boot_ms` 不是 anchor。
- AP/source `PASS`：三类 setpoint consumer、各 controller update time、Guided submode 与 response-start sites 已映射。
- MAVLink `NEEDS_BINDING`：发送 setpoint 不等于接受，outgoing target 也不携带 response cause。
- Monitor `UNSUPPORTED`。

建议：从 `REVIEW_READY` 回退，保留 variant 拆分和“无完成上界”，补 obligation reset/cancel。

### ARD-COPTER-RTL-003 — NEEDS_CONTEXT

证据：[ARD-COPTER-RTL-003.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-COPTER-RTL-003.json)；[rtl-mode.rst](/home/lqq/project/TAFuzz/benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/rtl-mode.rst:65)；[Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduCopter/Parameters.cpp:80)。

- Source/version `NEEDS_CONTEXT`；quote `PASS`；离开 RTL/non-landing cancellation 的规范依据只有 `CANDIDATE`。
- Event logic `NEEDS_CONTEXT`：eligibility 只守到 T；T 后、descent 前离开 RTL 时，unbounded eventual descent 仍未取消。
- Time `PASS`：运行 `5000 ms` 明确转换为 `5 s`，锚点是 RTL sub-state entry。
- AP/source `PASS`，三 AP 都绑定到内部 RTL substate；MAVLink `NEEDS_BINDING`，HEARTBEAT 只能证明 coarse RTL。
- Monitor `UNSUPPORTED`。

建议：从 `REVIEW_READY` 回退；补官方 cancellation/path context，并在一个 boot clock 暴露 substate entry/exit。

### ARD-PLANE-TAKEOFF-001 — CANDIDATE

证据：[ARD-PLANE-TAKEOFF-001.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-PLANE-TAKEOFF-001.json)；唯一 quote [Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduPlane/Parameters.cpp:1113)。

- Source/version、quote、IR、event logic、provenance 均为 `CANDIDATE`：唯一来源是 SUT 内 LOW PARAM_METADATA，存在循环来源风险。
- Time `PASS`：运行 `TKOFF_TIMEOUT=0`，来源明确表示 disabled，因此不生成 zero-second active formula。
- AP/source `PASS`；MAVLink `NEEDS_BINDING`，automatic-takeoff start 与 abort 为内部事件，GPS `time_usec` 不是 takeoff clock。
- Monitor `UNSUPPORTED`：当前 profile 禁用且无 concrete formula。

建议：只保留候选；没有独立官方行为来源前不提升，不用实现 flow 代替来源。

### ARD-ROVER-CRASH-002 — NEEDS_CONTEXT

证据：[ARD-ROVER-CRASH-002.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-ROVER-CRASH-002.json)；[rover-failsafes.rst](/home/lqq/project/TAFuzz/benchmark/extraction_runs/corpus_sources/ardupilot_wiki/rover/source/docs/rover-failsafes.rst:97)；[Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/Rover/Parameters.cpp:634)。

- Source/version `NEEDS_CONTEXT`；quote/IR `PASS`，quote 包含四条件合取、T、action 和单独的 immediate angle alternative。
- Event logic `NEEDS_CONTEXT`：规范要求四条件连续成立，公式没有 condition-break reset。
- Time `PASS`：运行 `CRASH_TIMEOUT=2 s`，单一 vehicle-side clock。
- AP/source `PASS`；MAVLink `NEEDS_BINDING`：VFR_HUD 无时间，ATTITUDE 有 boot time，不能从 wire 构造同采样时刻合取；demanded throttle/action 也不直接可见。
- Monitor `UNSUPPORTED`。

建议：从 `REVIEW_READY` 回退，正式编码 sustained conjunction 和 reset；保留 angle-only 路径的排除。

### ARD-ROVER-RCFS-001 — NEEDS_CONTEXT

证据：[ARD-ROVER-RCFS-001.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-ROVER-RCFS-001.json)；[rover-failsafes.rst](/home/lqq/project/TAFuzz/benchmark/extraction_runs/corpus_sources/ardupilot_wiki/rover/source/docs/rover-failsafes.rst:15)；[Parameters.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/Rover/Parameters.cpp:100)。

- Source/version `NEEDS_CONTEXT`；quote `PASS`；IR `CANDIDATE`，RCMAP_THROTTLE/valid-frame 是观察细节，不在选中 quote 中。
- Event logic `NEEDS_CONTEXT`：低油门持续性和恢复 reset 未进入公式。
- Time `PASS`：使用捕获 `1.5 s`，不使用 wiki default `1 s`。
- AP/source `PASS`；MAVLink `NEEDS_BINDING`，所有 AP 都是 conditional/derived，RC_CHANNELS 不证明 timer/action cause。
- Monitor `UNSUPPORTED`。

建议：从 `REVIEW_READY` 回退，编码 mapped-throttle sustained-low 与 valid-frame recovery。

### ARD-SHARED-BATT-001 — NEEDS_CONTEXT

证据：[ARD-SHARED-BATT-001.json](/home/lqq/project/TAFuzz/benchmark/ArduPilot/properties/ARD-SHARED-BATT-001.json)；[failsafe-battery.rst](/home/lqq/project/TAFuzz/benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/failsafe-battery.rst:93)；[AP_BattMonitor_Params.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Params.cpp:95)。

- Source/version `NEEDS_CONTEXT`；quote `CANDIDATE`，metadata 摘录比最低完整 low-voltage span 更长，应拆短但不能丢掉 continuous/disable 语义。
- IR `PASS`；event logic `NEEDS_CONTEXT`：来源明确写 continuously，公式却无 continued-low/recovery reset。
- Time `PASS`：各 profile/instance 捕获 `10 s`；`LOW_TIMER=0`、`LOW_VOLT=0` 禁用域有来源。
- AP/source `PASS`；MAVLink `NEEDS_BINDING`：sag-corrected selected voltage 和 exact event time 不是直接 field。
- Monitor `UNSUPPORTED`。

建议：从 `REVIEW_READY` 回退；缩短 quote，编码 per-instance continuous low voltage 与 recovery。

### PX4-MC-AUTODISARM-004 — NEEDS_CONTEXT

证据：[PX4-MC-AUTODISARM-004.json](/home/lqq/project/TAFuzz/benchmark/PX4/properties/PX4-MC-AUTODISARM-004.json)；[prearm_arm_disarm.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/advanced_config/prearm_arm_disarm.md:86)；[land.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/flight_modes_mc/land.md:23)；[commander_params.c](/home/lqq/project/TAFuzz/baseline/px4/src/modules/commander/commander_params.c:215)。

- Source/version `PASS`，但 quote/IR/time `NEEDS_CONTEXT`：`-1` 与 `<=0` disable domain 冲突，eligibility exception 不完整。
- Event logic `NEEDS_CONTEXT`：landed 变 false 或 eligibility 丢失未取消 obligation。
- AP/source `NEEDS_BINDING`：`auto_disarm_eligible` 为 PARTIALLY_BOUND/UNRESOLVED。
- MAVLink `NEEDS_BINDING`：EXTENDED_SYS_STATE 无时间，HEARTBEAT disarm 无原因，EVENT 需冻结 metadata/ID。
- Monitor `UNSUPPORTED`：无 concrete formula。

建议：保持 `NEEDS_CONTEXT`，不得从 Commander guard 补成规范 exception。

### PX4-MC-FLIGHTTIME-005 — NEEDS_CONTEXT

证据：[PX4-MC-FLIGHTTIME-005.json](/home/lqq/project/TAFuzz/benchmark/PX4/properties/PX4-MC-FLIGHTTIME-005.json)；[safety.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/config/safety.md:96)；[commander_params.c](/home/lqq/project/TAFuzz/baseline/px4/src/modules/commander/commander_params.c:884)。

- Source/version、quote、IR、time、AP/source 均 `PASS`。
- Event logic `NEEDS_CONTEXT`：`eventually` 弱化 90% warning 与 T 时 Return，漏掉每分钟 warning，并未说明 flight-end cancellation。
- 运行 `COM_FLT_TIME_MAX=-1`，当前 profile disabled；所以无 concrete formula。
- MAVLink `NEEDS_BINDING`：PX4 EVENT 在 baseline 出现只证明 message 可见，不证明所需 takeoff/warning IDs 已发生并正确映射。
- Monitor `UNSUPPORTED`。

建议：从 `REVIEW_READY` 回退；先修 first-warning、repetition、Return 与 scope 形式化，再采 enabled profile。

### PX4-MC-GCSLOSS-002 — NEEDS_CONTEXT

证据：[PX4-MC-GCSLOSS-002.json](/home/lqq/project/TAFuzz/benchmark/PX4/properties/PX4-MC-GCSLOSS-002.json)；[safety.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/config/safety.md:136)；[commander_params.c](/home/lqq/project/TAFuzz/baseline/px4/src/modules/commander/commander_params.c:86)。

- Source/version 与 quote `PASS`；IR 已恢复为官方 telemetry/data connection loss，因精确 liveness predicate/关联键/恢复事件未定义仍为 `NEEDS_CONTEXT`；provenance `PASS`。
- Event logic `NEEDS_CONTEXT`：new connection/restoration 与 exception reset/cancel 未进入公式。
- 时间数值使用捕获的 `COM_DL_LOSS_T=10 s`，但规范 loss-start 载体/时钟为 `UNKNOWN`；PX4 heartbeat HRT 和 host arrival 都不能代替。
- AP/source `NEEDS_BINDING`：当前 heartbeat/HRT 位置全部仅为 `MODELLED` 候选；MAVLink 同样 `NEEDS_BINDING`，connection-lost edge 需内部证据；Monitor `UNSUPPORTED`。

建议：保持 `NEEDS_CONTEXT`；官方 data-link wording 已恢复，后续不得在没有官方证据时将 heartbeat 当作规范等价事件。

### PX4-MC-OFFBOARD-003 — NEEDS_CONTEXT

证据：[PX4-MC-OFFBOARD-003.json](/home/lqq/project/TAFuzz/benchmark/PX4/properties/PX4-MC-OFFBOARD-003.json)；[offboard.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/flight_modes/offboard.md:5) 和 [同页第二段](/home/lqq/project/TAFuzz/baseline/px4/docs/en/flight_modes/offboard.md:24)；[commander_params.c](/home/lqq/project/TAFuzz/baseline/px4/src/modules/commander/commander_params.c:329)。

- Source/version `PASS`；quote、IR、time `NEEDS_CONTEXT`，2 Hz equality 和 one-second inclusivity 冲突。
- Event logic `UNSUPPORTED`：有意不生成公式是正确的。
- AP/source `NEEDS_BINDING`：`offboard_proof_qualified` PARTIALLY_BOUND/UNRESOLVED。
- MAVLink `NEEDS_BINDING`：sender timestamp 和已发送 setpoint 不证明 PX4 接受；request-message denial 也不能解释 inbound command support。
- Monitor `UNSUPPORTED`。

建议：保持 `NEEDS_CONTEXT`，先分离 admission 与 post-admission loss，再解决边界冲突。

### PX4-MC-RCLOSS-001 — NEEDS_CONTEXT

证据：[PX4-MC-RCLOSS-001.json](/home/lqq/project/TAFuzz/benchmark/PX4/properties/PX4-MC-RCLOSS-001.json)；[safety.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/config/safety.md:112)；[commander_params.c](/home/lqq/project/TAFuzz/baseline/px4/src/modules/commander/commander_params.c:125)。

- Source/version、quote、time、AP/source、provenance `PASS`。
- IR `NEEDS_CONTEXT`：`rc_loss_applicable` 是否应让 COM_RCL_EXCEPT 抑制 low-level `manual_control_lost`，还是只抑制 action，来源没有闭合。
- Event logic `NEEDS_CONTEXT`：selected source 新 setpoint/source switch reset 未进入公式。
- Time：`0.5 s` 明确换为 `500 ms`，锚点 selected ManualControlSetpoint HRT。
- MAVLink `NEEDS_BINDING`：MANUAL_CONTROL 无时间且不证明成为 selected source；lost edge 内部。
- Monitor `UNSUPPORTED`，原小数界不能直接解析。

建议：从 `REVIEW_READY` 回退；拆分 connection-lost classification 与 configured action applicability。

### PX4-MC-RTLLOITER-006 — NEEDS_CONTEXT

证据：[PX4-MC-RTLLOITER-006.json](/home/lqq/project/TAFuzz/benchmark/PX4/properties/PX4-MC-RTLLOITER-006.json)；[return.md](/home/lqq/project/TAFuzz/baseline/px4/docs/en/flight_modes/return.md:183)；[参数表](/home/lqq/project/TAFuzz/baseline/px4/docs/en/flight_modes/return.md:204)；[rtl_params.c](/home/lqq/project/TAFuzz/baseline/px4/src/modules/navigator/rtl_params.c:63)。

- Source/version `PASS`；quote/IR `NEEDS_CONTEXT`：默认冲突、mission landing、RTL_TYPE/path、vehicle class 和 exact phase 都是必要上下文。
- Event logic `NEEDS_CONTEXT`：leave Return、`-1` indefinite 与 exact land-phase event 未闭合。
- Time `PASS`：捕获 `0.0 s` 是立即 active boundary，不是 `-1`；锚点 Navigator phase-entry HRT。
- AP/source `NEEDS_BINDING`：缺 mission snapshot，mode_land 不能替代 precise DESCEND/loiter→AUTO_LAND phase。
- MAVLink `NEEDS_BINDING`：HEARTBEAT/CURRENT_MODE 只能给 coarse mode；Monitor `UNSUPPORTED`。

建议：保持 `NEEDS_CONTEXT`；PARAM_VALUE 只解决数值，不解决 path/phase 语义。

## 未解决事项

1. 仍需两名真实人类 reviewer 和 arbitration；本报告不能替代。
2. ArduPilot MAIN_ONLY wiki 与冻结固件的版本关系未闭合。
3. 需要一个版本化、可复核的 `MITL catalog syntax → TAMonitor syntax` 编译器及语义等价测试。
4. 需要为每条 active 公式准备正例、反例、reset/cancel、exact-bound、禁用域、clock-skew 与 non-vacuity trace。
5. 所有性质至少有一个 conditional/derived/unresolved/instrumentation-required MAVLink AP；没有一条是完整的 wire-only oracle。
6. `implementation_satisfaction` 必须继续保持 `NOT_ASSESSED`；不得把当前实现 flow 变成规范来源。
