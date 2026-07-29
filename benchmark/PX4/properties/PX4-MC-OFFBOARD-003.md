# PX4-MC-OFFBOARD-003 — PX4 Offboard proof-of-life 时序

- 系统/车型：PX4 / multicopter SITL
- 固件提交：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### PX4-MC-OFFBOARD-003-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/flight_modes/offboard.md:5-18`
- SHA-256：`42c1bddd291b9b1b5ae3a22484871087ffe786357c528d51bb24aa46dfecbab7`

```text
The vehicle obeys position, velocity, acceleration, attitude, attitude rates or thrust/torque setpoints provided by some source that is external to the flight stack, such as a companion computer.
The setpoints may be provided using MAVLink (or a MAVLink API such as [MAVSDK](https://mavsdk.mavlink.io/)) or by [ROS 2](../ros2/index.md).

PX4 requires that the external controller provides a continuous 2Hz "proof of life" signal, by streaming any of the supported MAVLink setpoint messages or the ROS 2 [OffboardControlMode](../msg_docs/OffboardControlMode.md) message.
PX4 enables offboard control only after receiving the signal for more than a second, and will regain control if the signal stops.

::: info

- This mode requires position or pose/attitude information - e.g. GPS, optical flow, visual-inertial odometry, mocap, etc.
- RC control is disabled except to change modes (you can also fly without any manual controller at all by setting the parameter [COM_RC_IN_MODE](../advanced_config/parameter_reference.md#COM_RC_IN_MODE) to 4: Stick input disabled).
- The vehicle must be already be receiving a stream of MAVLink setpoint messages or ROS 2 [OffboardControlMode](../msg_docs/OffboardControlMode.md) messages before arming in offboard mode or switching to offboard mode when flying.
- The vehicle will exit offboard mode if MAVLink setpoint messages or `OffboardControlMode` are not received at a rate of > 2Hz.
- Not all coordinate frames and field values allowed by MAVLink are supported for all setpoint messages and vehicles.
  Read the sections below _carefully_ to ensure only supported values are used.
```

上下文：定义进入 Offboard 前的 proof-of-life 速率和持续时间。

### PX4-MC-OFFBOARD-003-S2

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/flight_modes/offboard.md:24-31`
- SHA-256：`42c1bddd291b9b1b5ae3a22484871087ffe786357c528d51bb24aa46dfecbab7`

```text
Offboard mode is used for controlling vehicle movement and attitude, by setting position, velocity, acceleration, attitude, attitude rates or thrust/torque setpoints.

PX4 must receive a stream of MAVLink setpoint messages or the ROS 2 [OffboardControlMode](../msg_docs/OffboardControlMode.md) at 2 Hz as proof that the external controller is healthy.
The stream must be sent for at least a second before PX4 will arm in offboard mode, or switch to offboard mode when flying.
If the rate falls below 2Hz while under external control PX4 will switch out of offboard mode after a timeout ([COM_OF_LOSS_T](#COM_OF_LOSS_T)), and attempt to land or perform some other failsafe action.
The action depends on whether or not RC control is available, and is defined in the parameter [COM_OBL_RC_ACT](#COM_OBL_RC_ACT).

When using MAVLink the setpoint messages convey both the signal to indicate that the external source is "alive", and the setpoint value itself.
```

上下文：同页对 2Hz、>2Hz、below 2Hz 的边界表述存在冲突。

### PX4-MC-OFFBOARD-003-S3

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` / `RELEASE_PINNED`
- 位置：`baseline/px4/src/modules/commander/commander_params.c:329-369`
- SHA-256：`4e83db4e821aac5fb5ad96aa7755bac8dffac0714581d0895688198c8e41902a`

```text
/**
 * Time-out to wait when offboard connection is lost before triggering offboard lost action.
 *
 * See COM_OBL_RC_ACT to configure action.
 *
 * @group Commander
 * @unit s
 * @min 0
 * @max 60
 * @increment 0.01
 */
PARAM_DEFINE_FLOAT(COM_OF_LOSS_T, 1.0f);

/**
 * Set action after a quadchute
 *
 * @value -1 Warning only
 * @value  0 Return mode
 * @value  1 Land mode
 * @value  2 Hold mode
 * @group Commander
 */
PARAM_DEFINE_INT32(COM_QC_ACT, 0);

/**
 * Set offboard loss failsafe mode
 *
 * The offboard loss failsafe will only be entered after a timeout,
 * set by COM_OF_LOSS_T in seconds.
 *
 * @value 0 Position mode
 * @value 1 Altitude mode
 * @value 2 Stabilized
 * @value 3 Return mode
 * @value 4 Land mode
 * @value 5 Hold mode
 * @value 6 Terminate
 * @value 7 Disarm
 * @group Commander
 */
PARAM_DEFINE_INT32(COM_OBL_RC_ACT, 0);
```

上下文：冻结提交中的 COM_OF_LOSS_T 和 COM_OBL_RC_ACT 元数据。

## Requirement IR

- 主体：PX4 Offboard mode manager
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：受支持的 Offboard proof-of-life stream 出现或停止。
- 前置：消息被 PX4 接受且字段/type-mask 对当前 Offboard control mode 有效。
- 义务：进入 Offboard 前需持续约一秒满足文档规定的 rate；进入后 proof loss 持续 COM_OF_LOSS_T 时退出或执行配置 action。
- 禁止：无
- 例外：RC availability 会改变配置 action。；离开 Offboard 或合法 mode override 取消 loss 义务。
- 作用域：accepted Offboard proof stream → 离开 Offboard、恢复 proof stream 或 run 结束

## 时间与 MITL

- `T_offboard_loss`：`T_offboard_loss = runtime(COM_OF_LOSS_T)`；单位 `s`；下界闭合 `True`。
  起点：offboard_proof_loss_epoch；终点：offboard_loss_action；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：PX4 HRT on accepted offboard_control_mode。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`None`
- 单一具体公式：`null`（没有单一、已启用且上下文闭合的具体实例）
- 形式化状态：`NEEDS_CONTEXT`

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| PX4/multicopter — px4_sitl_default sihsim_quadx internal headless SIH instance 42 / `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` | `1.0 s` | `1.0 s` | `NOT_FORMALIZED` | `未形式化` | `benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json` SHA-256 `42d4fae5d576488a3584526c725330411f03dc438df24db7ab7ad7bdeb61af44`，index `285/900` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `PX4-MC-OFFBOARD-003-AP-01` | accepted setpoint/offboard-control update 对当前 control mode 有效。 | `CONDITIONAL` | `BOUND` |
| `PX4-MC-OFFBOARD-003-AP-02` | 待解决 2Hz equality 和持续时长边界后才能定义。 | `UNRESOLVED` | `PARTIALLY_BOUND` |
| `PX4-MC-OFFBOARD-003-AP-03` | vehicle navigation state 映射为 Offboard。 | `DIRECT` | `BOUND` |
| `PX4-MC-OFFBOARD-003-AP-04` | 结果 mode/action 与 COM_OBL_RC_ACT 和 RC availability 匹配。 | `CONDITIONAL` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### PX4-MC-OFFBOARD-003-AP-01 — `offboard_proof`

- 受控自然语言：受支持且被接受的 Offboard proof message。
- 真值条件：accepted setpoint/offboard-control update 对当前 control mode 有效。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Vehicle receipt timestamp on the accepted offboard_control_mode update.` — `baseline/px4/msg/OffboardControlMode.msg:3`；symbol `timestamp`；kind `FIELD`；function ``；type `uint64`；role `DEFINITION`；confidence `EXACT`。
  证据：The uORB message timestamp is set by accepted MAVLink handlers in vehicle boot time. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OffboardControlMode.msg#L3
- `Consumer for local-NED Offboard proof candidates.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1034`；symbol `MavlinkReceiver::handle_message_set_position_target_local_ned`；kind `MESSAGE_CONSUMER`；function `MavlinkReceiver::handle_message_set_position_target_local_ned`；type `void(mavlink_message_t *)`；role `CONSUMER`；confidence `EXACT`。
  证据：The handler applies forwarding, target, frame, mask, and validity checks before publishing control mode. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1034
- `Acceptance guard requiring at least one supported local position, velocity, or acceleration control dimension.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1131`；symbol `ocm.position`；kind `OTHER`；function `MavlinkReceiver::handle_message_set_position_target_local_ned`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：Only a non-empty supported control-mode update reaches the publisher. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1131
- `uORB producer for an accepted local-NED Offboard control-mode update.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1134`；symbol `_offboard_control_mode_pub.publish`；kind `MESSAGE_PRODUCER`；function `MavlinkReceiver::handle_message_set_position_target_local_ned`；type `uORB::Publication<offboard_control_mode_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Publication occurs after the handler's target, frame, mask, and finite-value checks. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1134
- `Consumer for global-int Offboard proof candidates.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1154`；symbol `MavlinkReceiver::handle_message_set_position_target_global_int`；kind `MESSAGE_CONSUMER`；function `MavlinkReceiver::handle_message_set_position_target_global_int`；type `void(mavlink_message_t *)`；role `CONSUMER`；confidence `EXACT`。
  证据：This is a distinct accepted proof path for supported global position/velocity/acceleration input. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1154
- `uORB producer for an accepted global-int Offboard control-mode update.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1256`；symbol `_offboard_control_mode_pub.publish`；kind `MESSAGE_PRODUCER`；function `MavlinkReceiver::handle_message_set_position_target_global_int`；type `uORB::Publication<offboard_control_mode_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：The update is published only after a supported and valid control dimension is established. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1256
- `Consumer for attitude or body-rate Offboard proof candidates.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1616`；symbol `MavlinkReceiver::handle_message_set_attitude_target`；kind `MESSAGE_CONSUMER`；function `MavlinkReceiver::handle_message_set_attitude_target`；type `void(mavlink_message_t *)`；role `CONSUMER`；confidence `EXACT`。
  证据：This is the supported attitude/rate proof path. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1616
- `uORB producer for an accepted attitude or body-rate Offboard control-mode update.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:1641`；symbol `_offboard_control_mode_pub.publish`；kind `MESSAGE_PRODUCER`；function `MavlinkReceiver::handle_message_set_attitude_target`；type `uORB::Publication<offboard_control_mode_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：The handler stamps vehicle receipt time at line 1640 and publishes at this site. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L1641

MAVLink/观测映射：

- `SET_POSITION_TARGET_LOCAL_NED.type_mask` (ID 84)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Potential proof/setpoint; time_boot_ms is sender boot time and does not prove PX4 acceptance.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SET_ATTITUDE_TARGET.type_mask` (ID 82)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Potential attitude/rate proof; acceptance depends on supported fields and estimates.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-OFFBOARD-003-AP-02 — `offboard_proof_qualified`

- 受控自然语言：proof history 满足 admission rate/duration。
- 真值条件：待解决 2Hz equality 和持续时长边界后才能定义。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`UNRESOLVED`；绑定状态：`PARTIALLY_BOUND`

源码绑定：

- `Commander health-check consumer for the latest offboard_control_mode sample.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp:38`；symbol `OffboardChecks::checkAndReport`；kind `FUNCTION`；function `OffboardChecks::checkAndReport`；type `void(const Context &,Report &)`；role `CONSUMER`；confidence `EXACT`。
  证据：The check reads one latest uORB sample; no history buffer is maintained here. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp#L38
- `Read of the latest offboard-control proof state.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp:44`；symbol `_offboard_control_mode_sub.copy`；kind `MESSAGE_CONSUMER`；function `OffboardChecks::checkAndReport`；type `uORB::Subscription`；role `CONSUMER`；confidence `EXACT`。
  证据：Only the most recent sample is copied. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp#L44
- `Single-sample freshness derivation using timestamp plus COM_OF_LOSS_T.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp:46`；symbol `data_is_recent`；kind `VARIABLE`；function `OffboardChecks::checkAndReport`；type `bool`；role `DERIVATION`；confidence `MODELLED`。
  证据：This locates current freshness but does not encode a 2 Hz equality rule or one-second history. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp#L46
- `Derived availability from supported control bits and current freshness.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp:49`；symbol `offboard_available`；kind `VARIABLE`；function `OffboardChecks::checkAndReport`；type `bool`；role `DERIVATION`；confidence `MODELLED`。
  证据：Estimator validity can further clear the value; it is not a historical admission qualifier. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp#L49
- `Current loss flag derived as the inverse of offboard_available.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp:65`；symbol `offboard_control_signal_lost`；kind `ASSIGNMENT`；function `OffboardChecks::checkAndReport`；type `bool`；role `WRITE`；confidence `MODELLED`。
  证据：This is a current availability consequence, not proof of historical rate/duration qualification. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/offboardCheck.cpp#L65
- `Runtime offboard-loss timeout used by the current freshness check.` — `baseline/px4/src/modules/commander/commander_params.c:340`；symbol `COM_OF_LOSS_T`；kind `PARAMETER`；function ``；type `float`；role `DEFINITION`；confidence `EXACT`。
  证据：The parameter defines tolerated staleness, not admission history duration. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L340

MAVLink/观测映射：

- `SET_POSITION_TARGET_LOCAL_NED.type_mask` (ID 84)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Potential proof/setpoint; time_boot_ms is sender boot time and does not prove PX4 acceptance.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SET_ATTITUDE_TARGET.type_mask` (ID 82)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Potential attitude/rate proof; acceptance depends on supported fields and estimates.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-OFFBOARD-003-AP-03 — `mode_offboard`

- 受控自然语言：PX4 当前处于 Offboard。
- 真值条件：vehicle navigation state 映射为 Offboard。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Current active vehicle navigation-state field.` — `baseline/px4/msg/versioned/VehicleStatus.msg:35`；symbol `nav_state`；kind `FIELD`；function ``；type `uint8`；role `DEFINITION`；confidence `EXACT`。
  证据：The AP is true when this field equals the OFFBOARD enum. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35
- `VehicleStatus enum constant identifying Offboard mode.` — `baseline/px4/msg/versioned/VehicleStatus.msg:50`；symbol `NAVIGATION_STATE_OFFBOARD`；kind `OTHER`；function ``；type `uint8 constant`；role `DEFINITION`；confidence `EXACT`。
  证据：This is the direct internal mode identity. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L50
- `uORB producer for the current nav_state and vehicle timestamp.` — `baseline/px4/src/modules/commander/Commander.cpp:1945`；symbol `_vehicle_status_pub.publish`；kind `MESSAGE_PRODUCER`；function `Commander::Run`；type `uORB::Publication<vehicle_status_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Internal observation of vehicle_status gives exact state identity. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L1945
- `Mapping branch from internal Offboard nav_state to PX4 custom mode.` — `baseline/px4/src/modules/commander/px4_custom_mode.h:157`；symbol `NAVIGATION_STATE_OFFBOARD`；kind `OTHER`；function `get_px4_custom_mode`；type `switch case`；role `DERIVATION`；confidence `EXACT`。
  证据：The branch selects PX4_CUSTOM_MAIN_MODE_OFFBOARD. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L157
- `HEARTBEAT producer derives custom_mode from current VehicleStatus nav_state.` — `baseline/px4/src/modules/mavlink/streams/HEARTBEAT.hpp:104`；symbol `get_px4_custom_mode`；kind `MESSAGE_PRODUCER`；function `MavlinkStreamHeartbeat::send`；type `px4_custom_mode`；role `DERIVATION`；confidence `EXACT`。
  证据：The mapped mode is sent in HEARTBEAT at lines 129-130. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/HEARTBEAT.hpp#L104
- `CURRENT_MODE wire producer for current and intended PX4 custom mode.` — `baseline/px4/src/modules/mavlink/streams/CURRENT_MODE.hpp:71`；symbol `mavlink_msg_current_mode_send_struct`；kind `MESSAGE_PRODUCER`；function `MavlinkStreamCurrentMode::send`；type `mavlink_current_mode_t`；role `PRODUCER`；confidence `EXACT`。
  证据：The stream sends custom_mode derived from vehicle_status.nav_state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/CURRENT_MODE.hpp#L71

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Decode PX4 custom OFFBOARD mode. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `CURRENT_MODE.custom_mode` (ID 436)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Direct current custom mode with no timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-OFFBOARD-003-AP-04 — `offboard_loss_action`

- 受控自然语言：退出 Offboard 并执行运行时配置的 loss action。
- 真值条件：结果 mode/action 与 COM_OBL_RC_ACT 和 RC availability 匹配。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Runtime parameter selecting the primary Offboard-loss action.` — `baseline/px4/src/modules/commander/commander_params.c:369`；symbol `COM_OBL_RC_ACT`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：Runtime capture, not the source default, is needed for correlation. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L369
- `Parameter-to-failsafe-action and intended-mode mapping function.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:280`；symbol `Failsafe::fromOffboardLossActParam`；kind `FUNCTION`；function `Failsafe::fromOffboardLossActParam`；type `FailsafeBase::Action(int,uint8_t &)`；role `DERIVATION`；confidence `EXACT`。
  证据：The switch maps all COM_OBL_RC_ACT values to fallback, RTL, Land, Hold, Terminate, or Disarm. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L280
- `Guard requiring Offboard signal loss to matter for the intended mode.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:665`；symbol `offboard_control_signal_lost`；kind `OTHER`；function `Failsafe::checkModeFallback`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：The guard combines the loss flag with mode_req_offboard_signal. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L665
- `Runtime action derivation from COM_OBL_RC_ACT.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:666`；symbol `fromOffboardLossActParam`；kind `ASSIGNMENT`；function `Failsafe::checkModeFallback`；type `FailsafeBase::Action`；role `DERIVATION`；confidence `EXACT`。
  证据：This is the primary configured-action selection site. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L666
- `RC-availability fallback guard for position, altitude, or stabilized actions.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:675`；symbol `manual_control_signal_lost`；kind `FIELD`；function `Failsafe::checkModeFallback`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：If manual control is lost, NAV_RCL_ACT replaces an RC-dependent fallback action. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L675
- `Commander writes the selected failsafe action's available mode replacement to current nav_state.` — `baseline/px4/src/modules/commander/Commander.cpp:2371`；symbol `_vehicle_status.nav_state`；kind `ASSIGNMENT`；function `Commander::Run`；type `uint8_t`；role `WRITE`；confidence `EXACT`。
  证据：Mode management can replace unavailable modes, so final state is a downstream result rather than a cause tag. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2371

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects COM_OBL_RC_ACT, COM_OF_LOSS_T; expected action and timeout
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Observe resulting mode. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `EVENT.id` (ID 410)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `event_time_boot_ms (PX4 system boot clock)`。May identify Offboard-control-loss cause/action. Requires firmware-matched component metadata to decode id/arguments.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| — | — | — | `NOT_RUN` | 没有上下文闭合且启用的具体公式，故未生成合成 monitor trace。 |

### 验证状态

| Gate | 状态 | 证据 |
|---|---|---|
| `schema` | `PASS` | Generated object is validated against property.schema.json. |
| `source` | `PASS` | All source files, hashes, line ranges, and exact quotes are checked by the validator. |
| `type_unit` | `PASS` | Runtime wire value, decoded value, raw unit, seconds normalization, param index/count, source path, and SHA-256 are retained per profile. |
| `temporal_graph` | `PASS` | Relations contain no self-edge or inverse-cycle in this property record. |
| `parser` | `NOT_APPLICABLE` | No enabled, context-closed concrete formula entered the monitor gate. |
| `satisfiable` | `NOT_APPLICABLE` | No enabled, context-closed concrete formula entered the monitor gate. |
| `non_tautology` | `NOT_APPLICABLE` | No enabled, context-closed concrete formula entered the monitor gate. |
| `non_vacuity` | `NOT_APPLICABLE` | No enabled, context-closed concrete formula entered the monitor gate. |
| `source_lines` | `PASS` | Every binding path/line/symbol is validated against the frozen checkout. |
| `permalinks` | `PASS` | Binding commit/path/line can be converted deterministically to a fixed GitHub commit permalink. |
| `monitor` | `NOT_APPLICABLE` | No enabled, context-closed concrete formula entered the monitor gate. |
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=same-version rate and inclusivity conflict; qualification AP partial; acceptance not wire-observable; no formula. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- rate equality 冲突未解决，禁止生成 admission concrete MITL。
- COM_OF_LOSS_T 仅解决 post-admission loss window。
- M7 automated independent audit: same-version rate and inclusivity conflict
- M7 automated independent audit: qualification AP partial
- M7 automated independent audit: acceptance not wire-observable
- M7 automated independent audit: no formula

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
