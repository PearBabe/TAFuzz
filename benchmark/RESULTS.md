# ArduPilot / PX4 MITL Benchmark 结果

## 1. 先读结论

本次交付生成了 13 条证据绑定性质、46 个类型化 AP、227 个当前源码 binding 和 77 行 AP—MAVLink/插桩观测映射。两个系统均保持：

```text
implementation_satisfaction = NOT_ASSESSED
accepted = 0
```

`accepted=0` 不是“没有性质”，而是没有冒充用户的人工审核决定。自动独立证据审核发现全部记录仍有未关闭的上下文、版本、事件生命周期或观测门禁，因此没有保留 `REVIEW_READY`：

| 系统 | `REVIEW_READY` | `CANDIDATE` | `NEEDS_CONTEXT` | `ACCEPTED` |
|---|---:|---:|---:|---:|
| ArduPilot | 0 | 1 | 6 | 0 |
| PX4 | 0 | 0 | 6 | 0 |
| 合计 | 0 | 1 | 12 | 0 |

这次回退不是人工 `REJECT`：审核者是独立的自动证据审计，不是两位人工 reviewer，也没有仲裁权。逐性质九门审核、证据和建议见 [`extraction_runs/milestone7/independent_review.md`](extraction_runs/milestone7/independent_review.md)。

ADGFuzz 的 ground、route-deviation、message-silence 三类规则另存为 3 类 `AUXILIARY_ORACLE` 方法记录，不计入 ArduPilot/PX4 系统性质。当前没有把 prefilter 命中误标为 rejected：36,151 个候选中，47 个命中与 13 条性质的来源区间重叠，其余 36,104 个均保留为 `PENDING_CONTEXT_REVIEW`。

## 2. 13 条性质与当前 SITL 参数实例

表中的数值来自保存的 MAVLink PARAM 快照，不是人工填写，也不是从控制流 timeout 反推。具体公式只说明数值代换和公式验证范围，不表示飞控满足性质。

| ID | 自然语言主题 | 性质状态 | 公式门禁 | 来源类别 | 时间参数 | 保存的运行值 | AP / binding |
|---|---|---|---|---|---|---|---:|
| [`ARD-COPTER-GCS-001`](ArduPilot/properties/ARD-COPTER-GCS-001.md) | Copter 指定 GCS heartbeat 超时 | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` | `OFFICIAL_BEHAVIOR` | `FS_GCS_TIMEOUT` | Copter `5.0 s` | 4 / 17 |
| [`ARD-COPTER-GUID-002`](ArduPilot/properties/ARD-COPTER-GUID-002.md) | Copter Guided 指令更新超时 | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` | `OFFICIAL_BEHAVIOR` | `GUID_TIMEOUT` | Copter `3.0 s` | 3 / 17 |
| [`ARD-COPTER-RTL-003`](ArduPilot/properties/ARD-COPTER-RTL-003.md) | Copter RTL Home 上方等待 | `NEEDS_CONTEXT` | `UNSUPPORTED_BY_MONITOR` | `OFFICIAL_BEHAVIOR` | `RTL_LOIT_TIME` | Copter `5000 ms = 5 s` | 3 / 10 |
| [`ARD-PLANE-TAKEOFF-001`](ArduPilot/properties/ARD-PLANE-TAKEOFF-001.md) | Plane 自动起飞超时 | `CANDIDATE` | `SYMBOLIC_ONLY` | `PARAM_METADATA_CANDIDATE` | `TKOFF_TIMEOUT` | Plane `0 s`，官方禁用域 | 5 / 18 |
| [`ARD-ROVER-RCFS-001`](ArduPilot/properties/ARD-ROVER-RCFS-001.md) | Rover 低油门持续触发 failsafe | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` | `OFFICIAL_BEHAVIOR` | `FS_TIMEOUT` | Rover `1.5 s` | 4 / 16 |
| [`ARD-ROVER-CRASH-002`](ArduPilot/properties/ARD-ROVER-CRASH-002.md) | Rover crash 条件持续时间 | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` | `OFFICIAL_BEHAVIOR` | `CRASH_TIMEOUT` | Rover `2.0 s` | 3 / 14 |
| [`ARD-SHARED-BATT-001`](ArduPilot/properties/ARD-SHARED-BATT-001.md) | ArduPilot 持续低电压 failsafe | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` | `OFFICIAL_BEHAVIOR` | `BATTx_LOW_TIMER` | Copter/Plane/Rover 均 `10 s` | 3 / 15 |
| [`PX4-MC-RCLOSS-001`](PX4/properties/PX4-MC-RCLOSS-001.md) | PX4 selected manual source 丢失 | `NEEDS_CONTEXT` | `MONITOR_VALIDATION_FAILED` | `OFFICIAL_BEHAVIOR` | `COM_RC_LOSS_T` | PX4 SIH `0.5 s` | 3 / 17 |
| [`PX4-MC-GCSLOSS-002`](PX4/properties/PX4-MC-GCSLOSS-002.md) | PX4 GCS data-link loss | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` | `OFFICIAL_BEHAVIOR` | `COM_DL_LOSS_T` | PX4 SIH `10 s` | 3 / 17 |
| [`PX4-MC-OFFBOARD-003`](PX4/properties/PX4-MC-OFFBOARD-003.md) | PX4 Offboard proof-of-life 时序 | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` | `OFFICIAL_BEHAVIOR` | `COM_OF_LOSS_T` | PX4 SIH `1.0 s`；未形式化 | 4 / 26 |
| [`PX4-MC-AUTODISARM-004`](PX4/properties/PX4-MC-AUTODISARM-004.md) | PX4 落地后自动 disarm | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` | `OFFICIAL_BEHAVIOR` | `COM_DISARM_LAND` | PX4 SIH `2.0 s`；eligibility 未闭合 | 4 / 25 |
| [`PX4-MC-FLIGHTTIME-005`](PX4/properties/PX4-MC-FLIGHTTIME-005.md) | PX4 最大飞行时间 | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` | `OFFICIAL_BEHAVIOR` | `COM_FLT_TIME_MAX` | PX4 SIH `-1 s`，官方禁用域 | 4 / 19 |
| [`PX4-MC-RTLLOITER-006`](PX4/properties/PX4-MC-RTLLOITER-006.md) | PX4 RTL 目的地等待后着陆 | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` | `OFFICIAL_BEHAVIOR` | `RTL_LAND_DELAY` | PX4 SIH `0.0 s`；路径/phase 未闭合 | 3 / 16 |

每条链接中的 Markdown 和 JSON 都包含：最短完整英文原文、精确路径/行/哈希、上下文摘要、Requirement IR、TimeContract、符号/具体 MITL、每个 AP 的真值条件、所有源码位置和固定 commit permalink、MAVLink/插桩观测方案、验证状态和未决冲突。

## 3. 为什么 5 条记录没有进入具体监视器公式

| 性质 | 原因 | 当前处理 |
|---|---|---|
| `ARD-PLANE-TAKEOFF-001` | `TKOFF_TIMEOUT=0` 是禁用值，且只有参数元数据低权威来源 | 保存候选和配置证据，不构造 `[0,0]` 伪义务 |
| `PX4-MC-OFFBOARD-003` | 2 Hz proof-of-life、loss timeout、模式进入/维持/退出的关系尚未闭合 | `NOT_FORMALIZED`，不让 LLM 补公式 |
| `PX4-MC-FLIGHTTIME-005` | `COM_FLT_TIME_MAX=-1` 是禁用值 | 保存性质和运行配置，不构造负区间 |
| `PX4-MC-AUTODISARM-004` / `PX4-MC-RTLLOITER-006` | 数值存在，但 eligibility、mission landing exclusion 或精确 phase 尚未闭合 | 保存 profile-specific 代换，状态保持 `NEEDS_CONTEXT`，不送监视器 |

最后一行包含两条上下文开放性质，因此没有具体监视器公式的性质总数是 5；当前有 8 条性质进入公式级门禁。

## 4. 公式与合成轨迹门禁

8 条具体公式都保留了“展示用数学式”和“监视器整数毫秒式”。原式直接交给 TAMonitor 的 8 次 probe 均因表示语法不兼容而保留为 `UNSUPPORTED_SYNTAX`；确定性转换只做 `&`→`&&`、temporal interval 语法适配、否定括号化和秒×1000 的精确整数缩放，区间开闭不变、没有 epsilon。转换式 8/8 可解析，正公式 8/8 SAT，负公式 8/8 SAT，独立完整有限词 oracle 的 trigger/non-trigger 非空洞对 8/8 通过。

合成轨迹统一使用单调递增的绝对全局毫秒时间戳；不是事件间 delay。独立 oracle 使用完整有限点式词，TAMonitor 使用 `--word infinite --state symbolic` 的无限词前缀语义，两类 verdict 分开保存。49 条轨迹的实际结果是：

| 层级 | 结果 |
|---|---|
| 性质公式 | 6 `PASS` / 1 `FAILED` / 1 `UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME` |
| 轨迹比较 | 42 `PASS` / 1 `FAILED_VERDICT_MISMATCH` / 6 `BDD_PROJECTION_VALUATION_LIMIT` |
| 42 个匹配 | 34 个预期/实际均 `INCONCLUSIVE`；8 个预期/实际均 `NEGATIVE` |

因此 6 条记录的 `MONITOR_VALIDATED` 只表示“当前转换公式在既定合成前缀套件上通过”，不表示其自然语言上下文已闭合，更不表示飞控满足性质。两个未关闭项是：

- `PX4-MC-RCLOSS-001` 在 500 ms 精确边界上预期 `INCONCLUSIVE`，TAMonitor 返回 `NEGATIVE`，所以标为 `MONITOR_VALIDATION_FAILED`；
- `ARD-COPTER-RTL-003` 的 6 条主运行在默认 4096 valuation 上触发 BDD 投影上限。诊断性 65536 运行虽能执行 too-early 轨迹，却返回 `INCONCLUSIVE` 而不是预期 `NEGATIVE`，所以仍为 `UNSUPPORTED_BY_MONITOR`。

完整命令、工具哈希、49 条 JSON/CSV trace、stdout/stderr、逐步结果和 RTL 诊断见 [`extraction_runs/milestone7/monitor_validation/README.md`](extraction_runs/milestone7/monitor_validation/README.md)。这些全部是合成 AP 赋值；没有把任何 SITL 飞行轨迹伪装成性质验证。

## 5. AP、源码与可观测性结果

| 系统 | AP | `BOUND` | `PARTIALLY_BOUND` | 源码 binding | AP 观测表行 |
|---|---:|---:|---:|---:|---:|
| ArduPilot | 25 | 25 | 0 | 107 | 43 |
| PX4 | 21 | 18 | 3 | 120 | 34 |
| 合计 | 46 | 43 | 3 | 227 | 77 |

按 AP 的最高可观测性分类：

| `DIRECT` | `DERIVED` | `CONDITIONAL` | `INSTRUMENTATION_REQUIRED` | `UNRESOLVED` |
|---:|---:|---:|---:|---:|
| 9 | 6 | 12 | 16 | 3 |

这意味着标准 MAVLink 单字段可直接判定的 AP 只占 `9/46`。即使把确定性派生和条件性消息也算入，仍有 19 个 AP 需要内部探针或继续补证。人工审核不能把“消息存在”误写成“AP 可直接观测”。

详细文件：

- [`ArduPilot/atomic_proposition_map.csv`](ArduPilot/atomic_proposition_map.csv) / [`PX4/atomic_proposition_map.csv`](PX4/atomic_proposition_map.csv)；
- [`ArduPilot/source_bindings.csv`](ArduPilot/source_bindings.csv) / [`PX4/source_bindings.csv`](PX4/source_bindings.csv)；
- [`ArduPilot/mavlink_observation_matrix.csv`](ArduPilot/mavlink_observation_matrix.csv) / [`PX4/mavlink_observation_matrix.csv`](PX4/mavlink_observation_matrix.csv)。

## 6. MAVLink 全目录与运行支持面

完整解释见 [`MAVLink_ArduPilot_PX4_observability.md`](MAVLink_ArduPilot_PX4_observability.md)，详细字段见 [`mavlink_catalog/`](mavlink_catalog/)。静态 XML 目录统计如下：

| 系统 | 方言消息 | 消息字段 | `MAV_CMD` | command param 槽 | 配置参数行 | time catalog 行 |
|---|---:|---:|---:|---:|---:|---:|
| ArduPilot | 352 | 2,708 | 216 | 1,512 | 16,904（Copter/Plane/Rover scope 行） | 2,628 |
| PX4 | 251 | 2,018 | 176 | 1,232 | 1,418 | 463 |

这些是固定 entrypoint include closure 的定义全集，不是“每个车型运行时都会发送”的集合。运行 overlay 包含 4 个 profile、1,307 个 profile×定义消息行和 3 个保留的非目录观测：

- `DEFAULT_STREAM_OBSERVED=94`；
- `REQUEST_WINDOW_MESSAGE_OBSERVED=97`；
- `REQUEST_ACK_ACCEPTED_NO_MATCHING_FRAME=114`；
- `REQUEST_ACK_DENIED=189`；
- `REQUEST_ACK_FAILED=805`；
- 辅助方言未进入 request sweep 且未观察到 `8`。

`FAILED` 或 `DENIED` 是这次 profile/request 的观测，不等于协议或固件全局不支持。完整方向、ACK、baseline/request、消息字段类型、数组、扩展字段、枚举、单位、无效值、时间字段和参数语义均在 CSV/JSON 中逐行保存。

## 7. SITL 证据

四个选定运行捕获均为 `COMPLETE`：

- ArduCopter quad；
- ArduPlane；
- Rover；
- PX4 v1.17.0 SIH multicopter quad_x。

合并后保存 4,999 个运行参数、1,307 个 profile×消息主行、128 个实际 time-field 行和 15 个 property/profile 时间值。失败的 PX4 external simulator 尝试也保留，不覆盖为成功。ArduPilot 的权威消息证据是解码 JSONL；PX4 同时有非空 tlog 与 JSONL。

捕获没有执行起飞、failsafe 或任务性质场景，所以这些文件不能用于报告实现符合性。

## 8. 尚需人工关闭的实质问题

1. ArduPilot 官方 wiki 是 `MAIN_ONLY`，不是与冻结 SUT 提交配对的 release 文档；6 条 ArduPilot 行为性质因此均为 `NEEDS_CONTEXT`。GCS 性质已恢复为官方 heartbeat 范围；`MANUAL_CONTROL`/`RC_CHANNELS_OVERRIDE` 和 aggregate last-seen 只作 `MODELLED` implementation conflict，仍需闭合版本、applicability、reset/cancel 与 heartbeat-exclusive 观测。
2. 自动审核指出 8 条具体公式尚未完整编码取消、重置或“条件持续成立”的 lifetime。Rover RC/crash、电池连续低压、RTL eligibility 等不能只靠起点采样替代持续语义。
3. PX4 的官方 data-link loss 已保持为 source-defined telemetry/data connection loss；其 liveness predicate、关联键、恢复事件和时钟仍为 `UNKNOWN`，不得无证据收窄为实现 heartbeat。Offboard 2 Hz equality、auto-disarm eligibility、flight-time 90%/逐分钟重复、RTL direct/mission landing path 与 exact Navigator phase 仍有上下文缺口。
4. `INSTRUMENTATION_REQUIRED` AP 必须按保存的源码语义身份实现探针；三个 PX4 AP 仍为 `PARTIALLY_BOUND`。GCS arrival time 不能替代飞控内部时钟，也不能替代官方来源未定义的 data-link loss 时钟。
5. PX4 RC-loss 的 500 ms 端点 mismatch 与 ArduPilot RTL 的 BDD-limit/65536 诊断 mismatch 必须先关闭，不能调整边界或添加 epsilon 来迎合监视器。
6. wrong-correlation 需要 trace 预处理器按 vehicle/sysid/component/campaign scope 拒绝；外层全局公式与无上界 eventuality 在有限合法前缀上常为 `INCONCLUSIVE`，不能为得到二值结果而发明 deadline。
7. 36,104 个预筛命中仍待逐条上下文审查。当前 13 条是经严格证据门禁形成的可审集合，不是“所有潜在官方句子均已人工裁决”的声明。
8. PX4 早期 14 条 YAML 草案已作为 `SUPERSEDED_NON_CANONICAL_DRAFT` 隔离归档，不再与正式六条性质并列。正式目录和最终验证禁止其无来源 epsilon 占位符及 heartbeat/HRT 实现语义旁路；24 个文件按归档时哈希固定，见 [`ARCHIVE_NOTICE.md`](extraction_runs/milestone4/superseded_px4_draft/ARCHIVE_NOTICE.md)。这能证明归档后未漂移；没有归档前外部锚定收据，不能独立证明更早历史身份。

## 9. 主要交付入口

- 方法：[`METHOD.md`](METHOD.md)
- PGFuzz 审计：[`paper_audits/PGFuzz_MTL_extraction_audit.md`](paper_audits/PGFuzz_MTL_extraction_audit.md)
- ADGFuzz 审计：[`paper_audits/ADGFuzz_oracle_rule_audit.md`](paper_audits/ADGFuzz_oracle_rule_audit.md)
- ProtocolGuard/NLP 适配：[`paper_audits/ProtocolGuard_NLP_adaptation.md`](paper_audits/ProtocolGuard_NLP_adaptation.md)
- 独立证据审核：[`extraction_runs/milestone7/independent_review.md`](extraction_runs/milestone7/independent_review.md)
- 公式/合成轨迹结果：[`extraction_runs/milestone7/monitor_validation/README.md`](extraction_runs/milestone7/monitor_validation/README.md)
- ArduPilot 目录：[`ArduPilot/property_catalog.md`](ArduPilot/property_catalog.md)
- PX4 目录：[`PX4/property_catalog.md`](PX4/property_catalog.md)
- PX4 正式入口与旧草稿隔离说明：[`PX4/README.md`](PX4/README.md)
- MAVLink 学习/审计说明：[`MAVLink_ArduPilot_PX4_observability.md`](MAVLink_ArduPilot_PX4_observability.md)
- 冻结版本：[`source_freeze_manifest.json`](source_freeze_manifest.json)
