# PX4 规范候选审计草案

本目录只覆盖冻结源码 `PX4-Autopilot v1.17.0`、提交
`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`、multicopter SITL。所有条目都是待人工审核的
外部规范候选，不是“源码已经实现的性质”，也没有据此判断 PX4 是否满足性质。

## 当前结论

- 共建立 14 条候选：9 条含参数化时间约束，3 条只有未量化的时间/顺序语义，2 条是无上界的最终性或优先级候选。
- 所有条目的 `implementation_satisfaction` 均为 `NOT_ASSESSED`，MITL 均为 `NOT_VALIDATED`。
- 发现三个会阻止直接生成可执行监视器的问题：Offboard 文档的 `2 Hz`/`>2 Hz` 边界不一致；
  RTL 文档默认 `0.5 s` 与参数元数据默认 `0.0 s` 不一致；位置失效文档在“最后融合”与“最后收到样本”之间不一致。
- 发现一个规范—实现绑定差异：预飞自动解锁文档把起点描述为“arming 后”，当前实现绑定还加入
  `COM_SPOOLUP_TIME`。该差异只作为映射风险记录，未用来判定实现满足性。
- 纯 MAVLink 黑盒能直接取得模式、armed、landed、位置、目标位置、电池警告和运行时参数；无法直接取得
  “最后一次成功融合”、完整 failsafe 原因集合、选中的手动控制源或内部 geofence 结果。后者必须用事件、
  ULog/uORB 伴随探针，或明确标记为派生命题。

## 证据纪律

候选的规范起点只允许来自当前冻结版本的官方仓库文档和面向用户的参数元数据。源码控制流、条件分支、
循环周期、内部 hysteresis、单元测试以及历史 PGFuzz/ADGFuzz 规则不得发起新性质。源码仅用于：

1. 把自然语言命题绑定到可能涉及的变量、赋值点和函数；
2. 证明某个 MAVLink 字段确实由什么内部状态生成；
3. 暴露歧义或冲突，阻止未经证实的公式进入执行阶段。

`properties/*.yaml` 保存逐条候选和自然语言原文；`ap_bindings.yaml` 保存 AP 到多个源码位置的多对多证据；
`mavlink_observability_draft.csv` 保存线缆可观测性；三者通过 `AP-*` 和 `OBS-*` 标识连接。

## 时间解释规则

- 参数化上界必须在每次 fuzz 运行前以 MAVLink `PARAM_REQUEST_READ`/`PARAM_VALUE` 读取并归档；源码默认值只是
  一个配置实例，不能替代运行时值。
- PX4 内部 HRT 的单位是微秒。POSIX SITL 在 lockstep 构建中使用 lockstep scheduler 的绝对时间，否则使用
  `CLOCK_MONOTONIC`（`platforms/posix/src/px4/common/drv_hrt.cpp:103-115`）。它不是 UTC，也不是墙钟。
- `HEARTBEAT`、`CURRENT_MODE`、`EXTENDED_SYS_STATE` 没有消息内时间戳；黑盒监视器必须给接收帧附加同一个
  host monotonic 时间。`LOCAL_POSITION_NED` 等消息的 `time_boot_ms` 来自 PX4 HRT，不能在没有时钟对齐的情况下
  与 host 时间混算。
- `EVENT.event_time_boot_ms` 是 PX4 boot/HRT 域；若使用事件作为命题，必须记录事件元数据版本和丢包/补发处理。
- 文档中的 “immediately”“shortly” 不能人工换成数值。候选会保留 `NEEDS_TIME_BOUND`。
- 精确阈值的采样和调度容差没有官方数值来源。本草案用符号 `EPS_OBS` 表示待定观测容差，不给它赋值；
  在 `EPS_OBS` 有可审计来源前，公式不能进入验证。

## 可观测等级

- `DIRECT_WIRE`：字段在冻结版本的 PX4 MAVLink 输出流中直接编码。
- `DIRECT_INPUT`：由测试器发送的输入帧直接定义，但不保证它被 PX4 接受或选中。
- `DERIVED_WIRE`：需要组合多个消息、配置或几何计算，且必须记录推导过程。
- `EVENT_METADATA`：可由 MAVLink Events 观测，但语义依赖与固件匹配的事件元数据。
- `INTERNAL_REQUIRED`：标准 MAVLink 输出不足，需 uORB/ULog/专用探针。
- `NOT_EXPOSED`：冻结版本没有对应输出流；不能用“协议里定义了消息”冒充 PX4 会发送。

## 审核顺序

1. 先读 `source_conflicts.yaml` 和 `exclusions.yaml`。
2. 在 `candidate_index.csv` 选候选，检查对应 `properties/*.yaml` 的原文、时间起点和未决项。
3. 用 `ap_bindings.yaml` 检查一个 AP 是否跨多个变量、函数或赋值点。
4. 用 `mavlink_observability_draft.csv` 判断能否黑盒观测；`INTERNAL_REQUIRED` 不能静默降级成推断。
5. 只有解决所有 `NEEDS_*`、固定运行时参数、定义时钟适配器并通过语法/轨迹验证后，才能创建 accepted MITL。

## 文件

- `corpus_manifest.csv`：本轮实际审阅的冻结语料和 SHA-256。
- `coverage_ledger.csv`：文档章节到候选/排除项的覆盖账本。
- `candidate_index.csv`：14 条候选摘要。
- `properties/`：逐条规范候选。
- `ap_bindings.yaml`：AP 多对多源码绑定。
- `mavlink_observability_draft.csv`：MAVLink 观测草案。
- `source_conflicts.yaml`：冲突和未决解释。
- `exclusions.yaml`：明确排除的伪规范来源。
- `validation/`：结构校验脚本和验证说明；本轮未运行 SITL/TAMonitor 性质判定。
