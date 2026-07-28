# PX4-MC-RCLOSS-001 — PX4 selected manual source 丢失

- 系统/车型：PX4 / multicopter SITL
- 固件提交：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### PX4-MC-RCLOSS-001-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/config/safety.md:112-134`
- SHA-256：`82b627ef4c4d323ef5e524c5630903c31570e103a9701b65a5f4b8fb33ee4db3`

```text
## Manual Control Loss Failsafe

The manual control loss failsafe may be triggered if the connection to the [RC transmitter](../getting_started/rc_transmitter_receiver.md) or [joystick](../config/joystick.md) is lost, and there is no fallback.
If using an [RC transmitter](../getting_started/rc_transmitter_receiver.md) this is triggered if the RC [transmitter link is lost](../getting_started/rc_transmitter_receiver.md#set-signal-loss-behaviour).
If using [joysticks](../config/joystick.md) connected over a MAVLink data link, this is triggered if the joysticks are disconnected or the data link is lost.

::: info
PX4 and the receiver may also need to be configured in order to _detect RC loss_: [Radio Setup > RC Loss Detection](../config/radio.md#rc-loss-detection).
:::

![Safety - RC Loss (QGC)](../../assets/qgc/setup/safety/safety_rc_loss.png)

The QGCroundControl Safety UI allows you to set the [failsafe action](#failsafe-actions) and [RC Loss timeout](#COM_RC_LOSS_T).
Users that want to disable the RC loss failsafe in specific automatic modes (mission, hold, offboard) can do so using the parameter [COM_RCL_EXCEPT](#COM_RCL_EXCEPT).

Additional (and underlying) parameter settings are shown below.

| Parameter                                                                                             | Setting                     | Description                                                                                                                                                                                                                                                                                                                                                                                              |
| ----------------------------------------------------------------------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <a id="COM_RC_LOSS_T"></a>[COM_RC_LOSS_T](../advanced_config/parameter_reference.md#COM_RC_LOSS_T)    | Manual Control Loss Timeout | Time after last setpoint received from the selected manual control source after which manual control is considered lost. This must be kept short because the vehicle will continue to fly using the old manual control setpoint until the timeout triggers.                                                                                                                                              |
| <a id="COM_FAIL_ACT_T"></a>[COM_FAIL_ACT_T](../advanced_config/parameter_reference.md#COM_FAIL_ACT_T) | Failsafe Reaction Delay     | Delay in seconds between failsafe condition being triggered (`COM_RC_LOSS_T`) and failsafe action (RTL, Land, Hold). In this state the vehicle waits in hold mode for the manual control source to reconnect. This might be set longer for long-range flights so that intermittent connection loss doesn't immediately invoke the failsafe. It can be to zero so that the failsafe triggers immediately. |
| <a id="NAV_RCL_ACT"></a>[NAV_RCL_ACT](../advanced_config/parameter_reference.md#NAV_RCL_ACT)          | Failsafe Action             | Disabled, Loiter, Return, Land, Disarm, Terminate.                                                                                                                                                                                                                                                                                                                                                       |
| <a id="COM_RCL_EXCEPT"></a>[COM_RCL_EXCEPT](../advanced_config/parameter_reference.md#COM_RCL_EXCEPT) | RC Loss Exceptions          | Set the modes in which manual control loss is ignored: Mission, Hold, Offboard.                                                                                                                                                                                                                                                                                                                          |
```

上下文：定义 selected manual source 的最后 setpoint 起点、COM_RC_LOSS_T 和模式例外。

### PX4-MC-RCLOSS-001-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` / `RELEASE_PINNED`
- 位置：`baseline/px4/src/modules/commander/commander_params.c:125-139`
- SHA-256：`4e83db4e821aac5fb5ad96aa7755bac8dffac0714581d0895688198c8e41902a`

```text
/**
 * Manual control loss timeout
 *
 * The time in seconds without a new setpoint from RC or Joystick, after which the connection is considered lost.
 * This must be kept short as the vehicle will use the last supplied setpoint until the timeout triggers.
 * Ensure the value is not set lower than the update interval of the RC or Joystick.
 *
 * @group Commander
 * @unit s
 * @min 0
 * @max 35
 * @decimal 1
 * @increment 0.1
 */
PARAM_DEFINE_FLOAT(COM_RC_LOSS_T, 0.5f);
```

上下文：冻结提交中的参数单位、范围和默认值。

## Requirement IR

- 主体：PX4 Commander manual-control-loss check
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：selected manual control source 的最后 setpoint 之后不再有新 setpoint。
- 前置：当前 manual source 已被明确选中。；COM_RCL_EXCEPT 不排除当前模式。；测试器能证明输入被接受并被 selector 选中。
- 义务：运行时 COM_RC_LOSS_T 后 manual control 被视为 lost。
- 禁止：在超时前不得仅由 selected-source gap 标记 lost。
- 例外：source selection 切换或新 selected-source setpoint 会重置。；配置的 mode exception 取消 action 义务，但不一定改变低层 signal-lost 分类。
- 作用域：selected source 的最后 accepted setpoint → 新 selected setpoint、source switch、disarm 或 run 结束

## 时间与 MITL

- `T_rc_loss`：`T_rc_loss = runtime(COM_RC_LOSS_T)`；单位 `s`；下界闭合 `True`。
  起点：last_selected_manual_setpoint；终点：manual_control_lost；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：PX4 HRT timestamp of selected ManualControlSetpoint。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((manual_gap_start & rc_loss_applicable) -> (G_[0,T_rc_loss) !manual_control_lost & F_[T_rc_loss,infty) manual_control_lost))`
- 单一具体公式：`G((manual_gap_start & rc_loss_applicable) -> (G_[0,0.5) !manual_control_lost & F_[0.5,infty) manual_control_lost))`
- 形式化状态：`MONITOR_VALIDATION_FAILED`

- TAMonitor 转换候选：`G((manual_gap_start && rc_loss_applicable) -> (G[0,500) (!manual_control_lost) && F[500,infty) manual_control_lost))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| PX4/multicopter — px4_sitl_default sihsim_quadx internal headless SIH instance 42 / `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` | `0.5 s` | `0.5 s` | `INSTANTIATED_UNVALIDATED` | `G((manual_gap_start & rc_loss_applicable) -> (G_[0,0.5) !manual_control_lost & F_[0.5,infty) manual_control_lost))` | `benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json` SHA-256 `42d4fae5d576488a3584526c725330411f03dc438df24db7ab7ad7bdeb61af44`，index `297/900` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `PX4-MC-RCLOSS-001-AP-01` | selected ManualControlSetpoint timestamp 不再更新的区间起点。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `PX4-MC-RCLOSS-001-AP-02` | runtime mode、COM_RCL_EXCEPT、RC source configuration 允许本次检查。 | `DERIVED` | `BOUND` |
| `PX4-MC-RCLOSS-001-AP-03` | manual_control_signal_lost 状态从 false 变 true。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### PX4-MC-RCLOSS-001-AP-01 — `manual_gap_start`

- 受控自然语言：selected manual source 的 accepted setpoint 间隔开始。
- 真值条件：selected ManualControlSetpoint timestamp 不再更新的区间起点。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Vehicle-boot timestamp of the selected manual-control setpoint topic sample.` — `baseline/px4/msg/versioned/ManualControlSetpoint.msg:3`；symbol `timestamp`；kind `FIELD`；function ``；type `uint64`；role `DEFINITION`；confidence `EXACT`。
  证据：The message definition assigns timestamp to each manual_control_setpoint sample. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/ManualControlSetpoint.msg#L3
- `Selector entry point that accepts a candidate source sample and may replace the selected setpoint.` — `baseline/px4/src/modules/manual_control/ManualControlSelector.cpp:44`；symbol `ManualControlSelector::updateWithNewInputSample`；kind `FUNCTION`；function `ManualControlSelector::updateWithNewInputSample`；type `void(uint64_t,const manual_control_setpoint_s &,int)`；role `CONSUMER`；confidence `EXACT`。
  证据：The function owns selected-source replacement; candidate receipt alone is not equivalent to selection. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/manual_control/ManualControlSelector.cpp#L44
- `Selector writes the selected setpoint receipt epoch while preserving timestamp_sample.` — `baseline/px4/src/modules/manual_control/ManualControlSelector.cpp:53`；symbol `_setpoint.timestamp`；kind `ASSIGNMENT`；function `ManualControlSelector::updateWithNewInputSample`；type `uint64`；role `WRITE`；confidence `EXACT`。
  证据：This assignment is the source-level epoch update for a newly selected input sample. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/manual_control/ManualControlSelector.cpp#L53
- `ManualControl refreshes the selected setpoint publication timestamp when the selected sample changes.` — `baseline/px4/src/modules/manual_control/ManualControl.cpp:124`；symbol `_selector.setpoint().timestamp`；kind `ASSIGNMENT`；function `ManualControl::Run`；type `uint64`；role `WRITE`；confidence `EXACT`。
  证据：The current vehicle time is written immediately before publishing the selected sample. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/manual_control/ManualControl.cpp#L124
- `uORB producer for the selected manual_control_setpoint sample whose timestamp defines the gap epoch.` — `baseline/px4/src/modules/manual_control/ManualControl.cpp:125`；symbol `_manual_control_setpoint_pub.publish`；kind `MESSAGE_PRODUCER`；function `ManualControl::Run`；type `uORB::Publication<manual_control_setpoint_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：The selected setpoint and its vehicle timestamp are published together. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/manual_control/ManualControl.cpp#L125
- `Vehicle receipt timestamp assigned to a MAVLink manual-control candidate before selector processing.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:2136`；symbol `manual_control_setpoint.timestamp`；kind `ASSIGNMENT`；function `MavlinkReceiver::handle_message_manual_control`；type `uint64`；role `WRITE`；confidence `EXACT`。
  证据：This is exact for the MAVLink candidate receipt, but the candidate may not become the selected source. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L2136

MAVLink/观测映射：

- `MANUAL_CONTROL` (ID 69)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Directly controls a MAVLink manual input, but the message has no timestamp and does not prove selector acceptance/selection.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-RCLOSS-001-AP-02 — `rc_loss_applicable`

- 受控自然语言：当前配置/模式不排除 manual control loss。
- 真值条件：runtime mode、COM_RCL_EXCEPT、RC source configuration 允许本次检查。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DERIVED`；绑定状态：`BOUND`

源码绑定：

- `Runtime bitmask parameter naming manual-control-loss mode exceptions.` — `baseline/px4/src/modules/commander/commander_params.c:633`；symbol `COM_RCL_EXCEPT`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：PARAM_DEFINE_INT32 defines the frozen-source parameter identity; its runtime value must be captured separately. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L633
- `Runtime manual-control input-source configuration parameter.` — `baseline/px4/src/modules/commander/commander_params.c:199`；symbol `COM_RC_IN_MODE`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：The source defines the parameter name and default only; applicability uses its runtime value. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L199
- `Failsafe state input used as the current intended navigation-mode discriminator.` — `baseline/px4/src/modules/commander/failsafe/framework.h:128`；symbol `user_intended_mode`；kind `FIELD`；function `FailsafeBase::update`；type `uint8_t`；role `READ`；confidence `EXACT`。
  证据：Mode exception derivation reads this field; it is not itself the complete AP. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/framework.h#L128
- `Implementation aggregation of manual-control-loss exception and transient ignore predicates.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:489`；symbol `rc_loss_ignored`；kind `VARIABLE`；function `Failsafe::update`；type `const bool`；role `DERIVATION`；confidence `MODELLED`。
  证据：The expression combines mode exception bits with VTOL-takeoff, lost-at-arming, external-mode, and altitude-cruise conditions. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L489
- `Implementation guard requiring manual control to be enabled and the aggregate ignore predicate to be false.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:493`；symbol `_param_com_rc_in_mode`；kind `OTHER`；function `Failsafe::update`；type `bool expression`；role `GUARD`；confidence `MODELLED`。
  证据：This is an implementation applicability site, not a substitute for the normalized official truth source. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L493

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects COM_RCL_EXCEPT, COM_RC_IN_MODE, NAV_RCL_ACT; derive configured applicability
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Current custom mode. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-RCLOSS-001-AP-03 — `manual_control_lost`

- 受控自然语言：PX4 将 manual control signal 标为 lost。
- 真值条件：manual_control_signal_lost 状态从 false 变 true。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `uORB failsafe flag whose false-to-true transition is the normalized AP.` — `baseline/px4/msg/FailsafeFlags.msg:39`；symbol `manual_control_signal_lost`；kind `FIELD`；function ``；type `bool`；role `DEFINITION`；confidence `EXACT`。
  证据：The field is explicitly documented as manual-control signal lost. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L39
- `Freshness and validity guard that decides the manual-control lost branch.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp:48`；symbol `manual_control_setpoint.valid`；kind `OTHER`；function `RcAndDataLinkChecks::checkAndReport`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：The branch also compares the selected timestamp against COM_RC_LOSS_T on following lines. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp#L48
- `Assignment that marks the report flag true in the lost branch.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp:57`；symbol `manual_control_signal_lost`；kind `ASSIGNMENT`；function `RcAndDataLinkChecks::checkAndReport`；type `bool`；role `WRITE`；confidence `EXACT`。
  证据：This is the direct true write for the AP state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp#L57
- `uORB producer that publishes failsafe_flags with a vehicle timestamp.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/HealthAndArmingChecks.cpp:111`；symbol `_failsafe_flags_pub.publish`；kind `MESSAGE_PRODUCER`；function `HealthAndArmingChecks::runChecks`；type `uORB::Publication<failsafe_flags_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Instrumentation can observe the field transition on this published topic. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/HealthAndArmingChecks.cpp#L111
- `Named PX4 event emitted on entry into the manual-control lost branch.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp:53`；symbol `commander_rc_lost`；kind `EVENT`；function `RcAndDataLinkChecks::checkAndReport`；type `events::ID`；role `PRODUCER`；confidence `EXACT`。
  证据：The named event is transition-oriented evidence; exact flag state remains the uORB field. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp#L53
- `Generic PX4 EVENT MAVLink producer used for named commander events.` — `baseline/px4/src/modules/mavlink/mavlink_events.cpp:209`；symbol `SendProtocol::send_event`；kind `MESSAGE_PRODUCER`；function `SendProtocol::send_event`；type `void(const Event &)`；role `PRODUCER`；confidence `EXACT`。
  证据：The producer maps event timestamp and ID into MAVLink EVENT. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_events.cpp#L209

MAVLink/观测映射：

- `EVENT.id` (ID 410)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `event_time_boot_ms (PX4 system boot clock)`。May carry manual-control-lost event with vehicle event timestamp. Requires firmware-matched component metadata to decode id/arguments.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `PX4-MC-RCLOSS-001--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-RCLOSS-001/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `PX4-MC-RCLOSS-001--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-RCLOSS-001/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `VIOLATED` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=FAILED_VERDICT_MISMATCH. |
| 边界反例 | `PX4-MC-RCLOSS-001--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-RCLOSS-001/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `PX4-MC-RCLOSS-001--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-RCLOSS-001/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `PX4-MC-RCLOSS-001--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-RCLOSS-001/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

### 验证状态

| Gate | 状态 | 证据 |
|---|---|---|
| `schema` | `PASS` | Generated object is validated against property.schema.json. |
| `source` | `PASS` | All source files, hashes, line ranges, and exact quotes are checked by the validator. |
| `type_unit` | `PASS` | Runtime wire value, decoded value, raw unit, seconds normalization, param index/count, source path, and SHA-256 are retained per profile. |
| `temporal_graph` | `PASS` | Relations contain no self-edge or inverse-cycle in this property record. |
| `parser` | `PASS` | The presentation formula probe is preserved as unsupported; the explicit integer-ms monitor encoding parses/builds. |
| `satisfiable` | `PASS` | TAMonitor build metadata reports the transformed positive formula SAT. |
| `non_tautology` | `PASS` | TAMonitor build metadata reports the negated transformed formula SAT; this excludes a tautology under the compiled syntax. |
| `non_vacuity` | `PASS` | The explicitly identified complete-word reference oracle distinguishes a triggered counterexample from a trigger-disabled control; it is not TAMonitor. |
| `source_lines` | `PASS` | Every binding path/line/symbol is validated against the frozen checkout. |
| `permalinks` | `PASS` | Binding commit/path/line can be converted deterministically to a fixed GitHub commit permalink. |
| `monitor` | `FAIL` | TAMonitor infinite-prefix status=FAILED; trace comparisons={"FAILED_VERDICT_MISMATCH": 1, "PASS": 5}. At least one executed synthetic trace produced a TAMonitor verdict different from the expected infinite-prefix verdict. The mismatch is retained and the formula instance remains unvalidated. Exact stdout/stderr and result metadata are retained. |
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=classification versus action-exception ambiguity; selected-source reset omitted; selector/lost APs internal; direct syntax unsupported. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- 标准 MAVLink 不能单独证明 selected source。
- M7 automated independent audit: classification versus action-exception ambiguity
- M7 automated independent audit: selected-source reset omitted
- M7 automated independent audit: selector/lost APs internal
- M7 automated independent audit: direct syntax unsupported

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
