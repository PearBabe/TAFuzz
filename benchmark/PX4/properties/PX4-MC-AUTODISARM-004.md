# PX4-MC-AUTODISARM-004 — PX4 落地后自动 disarm

- 系统/车型：PX4 / multicopter SITL
- 固件提交：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### PX4-MC-AUTODISARM-004-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/advanced_config/prearm_arm_disarm.md:86-94`
- SHA-256：`23e06ca80b9a01629ac9b28bc240575ea13eb98c1cab9bdf9fd8df939f351c27`

```text
## Auto-Disarming

By default vehicles will automatically disarm on landing, or if you take too long to take off after arming.
The feature is configured using the following timeouts.

| Parameter                                                                                                   | Description                                                                     |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| <a id="COM_DISARM_LAND"></a>[COM_DISARM_LAND](../advanced_config/parameter_reference.md#COM_DISARM_LAND)    | Time-out for auto disarm after landing. Default: 2s (-1 to disable).            |
| <a id="COM_DISARM_PRFLT"></a>[COM_DISARM_PRFLT](../advanced_config/parameter_reference.md#COM_DISARM_PRFLT) | Time-out for auto disarm if too slow to takeoff. Default: 10s (<=0 to disable). |
```

上下文：定义落地后自动 disarm 的时间参数和文档禁用值。

### PX4-MC-AUTODISARM-004-S2

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/flight_modes_mc/land.md:23-37`
- SHA-256：`16fcdf6dbeb3ea286ae61d5f0642687f965343d8f75120ca4501870e19708d87`

```text
## Technical Summary

The vehicle will land at the location at which the mode was engaged.
The vehicle descends at the rate specified in [MPC_LAND_SPEED](#MPC_LAND_SPEED) and will disarm after landing (by [default](#COM_DISARM_LAND)).

RC stick movement will change the vehicle to [Position mode](../flight_modes_mc/position.md) (by [default](#COM_RC_OVERRIDE)).

### Parameters

Land mode behaviour can be configured using the parameters below.

| Parameter                                                                                                | Description                                                                                                                                                                                                                                                  |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| <a id="MPC_LAND_SPEED"></a>[MPC_LAND_SPEED](../advanced_config/parameter_reference.md#MPC_LAND_SPEED)    | The rate of descent during landing. This should be kept fairly low as the ground conditions are not known.                                                                                                                                                   |
| <a id="COM_DISARM_LAND"></a>[COM_DISARM_LAND](../advanced_config/parameter_reference.md#COM_DISARM_LAND) | Time-out for auto disarm after landing, in seconds. If set to -1 the vehicle will not disarm on landing.                                                                                                                                                     |
```

上下文：说明 landed 状态和 COM_DISARM_LAND 触发自动 disarm。

### PX4-MC-AUTODISARM-004-S3

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` / `RELEASE_PINNED`
- 位置：`baseline/px4/src/modules/commander/commander_params.c:215-227`
- SHA-256：`4e83db4e821aac5fb5ad96aa7755bac8dffac0714581d0895688198c8e41902a`

```text
*
 * A non-zero, positive value specifies the time-out period in seconds after which the vehicle will be
 * automatically disarmed in case a landing situation has been detected during this period.
 *
 * A zero or negative value means that automatic disarming triggered by landing detection is disabled.
 *
 * @group Commander
 * @unit s
 * @decimal 1
 * @increment 0.1
 */

PARAM_DEFINE_FLOAT(COM_DISARM_LAND, 2.0f);
```

上下文：参数元数据将零或负值均列为禁用，与文档 -1 表述不同。

## Requirement IR

- 主体：PX4 Commander auto-disarm
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：armed vehicle 的 landed 状态开始连续成立。
- 前置：运行时 COM_DISARM_LAND 启用。；只使用官方来源确认的 eligibility/exception；实现 guard 不反推为规范。
- 义务：连续 landed 达 COM_DISARM_LAND 后自动 disarm。
- 禁止：在时间结束前不得仅由 landing timer 自动 disarm。
- 例外：mission/config overrides 和 throw-launch 等例外尚需官方上下文。；文档 -1 与参数元数据 <=0 的禁用域冲突。
- 作用域：landed transition while armed → landed false、disarm、eligibility cancel 或 run 结束

## 时间与 MITL

- `T_disarm_land`：`T_disarm_land = runtime(COM_DISARM_LAND)`；单位 `s`；下界闭合 `True`。
  起点：landed_interval_start；终点：automatic_disarm；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：PX4 HRT land-detector/commander events。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((landed_start & auto_disarm_eligible) -> (G_[0,T_disarm_land) armed & F_[T_disarm_land,infty) disarmed))`
- 单一具体公式：`null`（没有单一、已启用且上下文闭合的具体实例）
- 形式化状态：`NEEDS_CONTEXT`

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| PX4/multicopter — px4_sitl_default sihsim_quadx internal headless SIH instance 42 / `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` | `2.0 s` | `2.0 s` | `NEEDS_CONTEXT` | `G((landed_start & auto_disarm_eligible) -> (G_[0,2) armed & F_[2,infty) disarmed))` | `benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json` SHA-256 `42d4fae5d576488a3584526c725330411f03dc438df24db7ab7ad7bdeb61af44`，index `256/900` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `PX4-MC-AUTODISARM-004-AP-01` | vehicle landed 从 false 变 true。 | `CONDITIONAL` | `BOUND` |
| `PX4-MC-AUTODISARM-004-AP-02` | 待补全官方例外后定义；不能使用实现 guard 充当来源。 | `UNRESOLVED` | `PARTIALLY_BOUND` |
| `PX4-MC-AUTODISARM-004-AP-03` | HEARTBEAT armed bit 对目标 autopilot 为 true。 | `DIRECT` | `BOUND` |
| `PX4-MC-AUTODISARM-004-AP-04` | HEARTBEAT armed bit 为 false。 | `DIRECT` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### PX4-MC-AUTODISARM-004-AP-01 — `landed_start`

- 受控自然语言：land detector 进入 landed。
- 真值条件：vehicle landed 从 false 变 true。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Vehicle landed state whose false-to-true transition defines the AP.` — `baseline/px4/msg/versioned/VehicleLandDetected.msg:8`；symbol `landed`；kind `FIELD`；function ``；type `bool`；role `DEFINITION`；confidence `EXACT`。
  证据：The message defines the final land-detector stage state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLandDetected.msg#L8
- `Hysteresis-qualified landed-state derivation.` — `baseline/px4/src/modules/land_detector/LandDetector.cpp:148`；symbol `landDetected`；kind `VARIABLE`；function `LandDetector::Run`；type `const bool`；role `DERIVATION`；confidence `EXACT`。
  证据：The value is read from the landed hysteresis state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/land_detector/LandDetector.cpp#L148
- `Assignment of the qualified state to vehicle_land_detected.` — `baseline/px4/src/modules/land_detector/LandDetector.cpp:169`；symbol `_land_detected.landed`；kind `ASSIGNMENT`；function `LandDetector::Run`；type `bool`；role `WRITE`；confidence `EXACT`。
  证据：The state change is committed here before publication. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/land_detector/LandDetector.cpp#L169
- `uORB producer for landed state with a vehicle timestamp.` — `baseline/px4/src/modules/land_detector/LandDetector.cpp:182`；symbol `_vehicle_land_detected_pub.publish`；kind `MESSAGE_PRODUCER`；function `LandDetector::Run`；type `uORB::Publication<vehicle_land_detected_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Internal instrumentation can observe the exact state transition. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/land_detector/LandDetector.cpp#L182
- `Named Commander event emitted on armed false-to-true landed transition.` — `baseline/px4/src/modules/commander/Commander.cpp:2134`；symbol `commander_landing_detected`；kind `EVENT`；function `Commander::landDetectorUpdate`；type `events::ID`；role `PRODUCER`；confidence `EXACT`。
  证据：Commander compares the prior and current landed states before sending this event. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2134
- `Wire projection mapping internal landed true to MAV_LANDED_STATE_ON_GROUND.` — `baseline/px4/src/modules/mavlink/streams/EXTENDED_SYS_STATE.hpp:101`；symbol `land_detected.landed`；kind `MESSAGE_PRODUCER`；function `MavlinkStreamExtendedSysState::send`；type `mavlink_extended_sys_state_t`；role `DERIVATION`；confidence `EXACT`。
  证据：The stream consumes vehicle_land_detected and sends EXTENDED_SYS_STATE. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/EXTENDED_SYS_STATE.hpp#L101

MAVLink/观测映射：

- `EXTENDED_SYS_STATE.landed_state` (ID 245)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。MAV_LANDED_STATE_ON_GROUND directly reports state; message has no timestamp, so the transition epoch needs EVENT/internal HRT for strict timing.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-AUTODISARM-004-AP-02 — `auto_disarm_eligible`

- 受控自然语言：官方规范定义的 auto-disarm eligibility 全部成立。
- 真值条件：待补全官方例外后定义；不能使用实现 guard 充当来源。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`UNRESOLVED`；绑定状态：`PARTIALLY_BOUND`

源码绑定：

- `Runtime landed auto-disarm delay parameter; positive enables one implementation input.` — `baseline/px4/src/modules/commander/commander_params.c:227`；symbol `COM_DISARM_LAND`；kind `PARAMETER`；function ``；type `float`；role `DEFINITION`；confidence `EXACT`。
  证据：Source default is not substituted for the campaign runtime value. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L227
- `Implementation function evaluating automatic disarm guards.` — `baseline/px4/src/modules/commander/Commander.cpp:2279`；symbol `Commander::handleAutoDisarm`；kind `FUNCTION`；function `Commander::handleAutoDisarm`；type `void()`；role `DERIVATION`；confidence `MODELLED`。
  证据：The function is implementation identity only; catalog truth awaits complete official eligibility. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2279
- `Implementation guard requiring the vehicle to be armed.` — `baseline/px4/src/modules/commander/Commander.cpp:2282`；symbol `isArmed`；kind `OTHER`；function `Commander::handleAutoDisarm`；type `bool expression`；role `GUARD`；confidence `MODELLED`。
  证据：Recorded as implementation guard, not as normative source. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2282
- `Implementation conjunction of positive delay, no mission in progress, and no disable override.` — `baseline/px4/src/modules/commander/Commander.cpp:2287`；symbol `auto_disarm_land_enabled`；kind `VARIABLE`；function `Commander::handleAutoDisarm`；type `const bool`；role `DERIVATION`；confidence `MODELLED`。
  证据：This implementation conjunction cannot fill missing official exceptions. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2287
- `Implementation guard requiring a detected takeoff since arming.` — `baseline/px4/src/modules/commander/Commander.cpp:2290`；symbol `_have_taken_off_since_arming`；kind `VARIABLE`；function `Commander::handleAutoDisarm`；type `bool`；role `GUARD`；confidence `MODELLED`。
  证据：This guard is recorded for identity only. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2290
- `Implementation delay configuration from COM_DISARM_LAND.` — `baseline/px4/src/modules/commander/Commander.cpp:2291`；symbol `_auto_disarm_landed.set_hysteresis_time_from`；kind `ASSIGNMENT`；function `Commander::handleAutoDisarm`；type `Hysteresis`；role `DERIVATION`；confidence `MODELLED`。
  证据：The landed false-to-true hysteresis duration is set at this site. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2291
- `Implementation exclusion while multicopter throw launch is in progress.` — `baseline/px4/src/modules/commander/Commander.cpp:2300`；symbol `isThrowLaunchInProgress`；kind `OTHER`；function `Commander::handleAutoDisarm`；type `bool expression`；role `GUARD`；confidence `MODELLED`。
  证据：The exclusion appears immediately before the disarm call. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2300
- `Implementation call-site reason for landed auto-disarm after guards and hysteresis.` — `baseline/px4/src/modules/commander/Commander.cpp:2302`；symbol `auto_disarm_land`；kind `ASSIGNMENT`；function `Commander::handleAutoDisarm`；type `arm_disarm_reason_t`；role `OBSERVATION_SITE`；confidence `MODELLED`。
  证据：The call identifies the implementation outcome but not a complete official eligibility definition. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2302

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects COM_DISARM_LAND; capture value and disable-domain conflict
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Current mode only. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-AUTODISARM-004-AP-03 — `armed`

- 受控自然语言：PX4 当前 armed。
- 真值条件：HEARTBEAT armed bit 对目标 autopilot 为 true。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Current vehicle arming-state field.` — `baseline/px4/msg/versioned/VehicleStatus.msg:10`；symbol `arming_state`；kind `FIELD`；function ``；type `uint8`；role `DEFINITION`；confidence `EXACT`。
  证据：The AP is true when arming_state equals ARMING_STATE_ARMED. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L10
- `VehicleStatus enum value for armed.` — `baseline/px4/msg/versioned/VehicleStatus.msg:12`；symbol `ARMING_STATE_ARMED`；kind `OTHER`；function ``；type `uint8 constant`；role `DEFINITION`；confidence `EXACT`。
  证据：Direct internal state identity. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L12
- `Commander assignment entering armed state.` — `baseline/px4/src/modules/commander/Commander.cpp:622`；symbol `_vehicle_status.arming_state`；kind `ASSIGNMENT`；function `Commander::arm`；type `uint8_t`；role `WRITE`；confidence `EXACT`。
  证据：The assignment is paired with armed_time and arming reason. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L622
- `uORB producer for current arming_state.` — `baseline/px4/src/modules/commander/Commander.cpp:1945`；symbol `_vehicle_status_pub.publish`；kind `MESSAGE_PRODUCER`；function `Commander::Run`；type `uORB::Publication<vehicle_status_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Internal state publication includes a vehicle timestamp. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L1945
- `Wire derivation guard setting MAV_MODE_FLAG_SAFETY_ARMED.` — `baseline/px4/src/modules/mavlink/streams/HEARTBEAT.hpp:82`；symbol `ARMING_STATE_ARMED`；kind `MESSAGE_PRODUCER`；function `MavlinkStreamHeartbeat::send`；type `bool expression`；role `DERIVATION`；confidence `EXACT`。
  证据：HEARTBEAT base_mode is derived directly from vehicle_status.arming_state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/HEARTBEAT.hpp#L82

MAVLink/观测映射：

- `HEARTBEAT.base_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。MAV_MODE_FLAG_SAFETY_ARMED reports state; no timestamp or disarm reason.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-AUTODISARM-004-AP-04 — `disarmed`

- 受控自然语言：PX4 当前 disarmed。
- 真值条件：HEARTBEAT armed bit 为 false。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `VehicleStatus enum value for disarmed.` — `baseline/px4/msg/versioned/VehicleStatus.msg:11`；symbol `ARMING_STATE_DISARMED`；kind `OTHER`；function ``；type `uint8 constant`；role `DEFINITION`；confidence `EXACT`。
  证据：Direct internal state identity. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L11
- `Commander state-transition function for disarming.` — `baseline/px4/src/modules/commander/Commander.cpp:638`；symbol `Commander::disarm`；kind `FUNCTION`；function `Commander::disarm`；type `transition_result_t(arm_disarm_reason_t,bool)`；role `DERIVATION`；confidence `EXACT`。
  证据：Successful calls write DISARMED and clear armed/takeoff time. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L638
- `Commander assignment entering disarmed state.` — `baseline/px4/src/modules/commander/Commander.cpp:667`；symbol `_vehicle_status.arming_state`；kind `ASSIGNMENT`；function `Commander::disarm`；type `uint8_t`；role `WRITE`；confidence `EXACT`。
  证据：This is the direct state write for the AP. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L667
- `VehicleStatus reason assignment allowing auto_disarm_land to be distinguished internally.` — `baseline/px4/src/modules/commander/Commander.cpp:668`；symbol `latest_disarming_reason`；kind `ASSIGNMENT`；function `Commander::disarm`；type `uint8_t`；role `WRITE`；confidence `EXACT`。
  证据：The AP itself is state-based; reason is supplementary correlation evidence. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L668
- `Named event carrying arm_disarm_reason_t for a disarm transition.` — `baseline/px4/src/modules/commander/Commander.cpp:678`；symbol `commander_disarmed_by`；kind `EVENT`；function `Commander::disarm`；type `events::ID with enum argument`；role `PRODUCER`；confidence `EXACT`。
  证据：Argument value AUTO_DISARM_LAND identifies the landed auto-disarm reason when applicable. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L678
- `HEARTBEAT producer tests armed state; the absence of MAV_MODE_FLAG_SAFETY_ARMED projects disarmed for the target autopilot.` — `baseline/px4/src/modules/mavlink/streams/HEARTBEAT.hpp:82`；symbol `vehicle_status.arming_state`；kind `MESSAGE_PRODUCER`；function `MavlinkStreamHeartbeat::send`；type `bool expression`；role `DERIVATION`；confidence `EXACT`。
  证据：The base-mode armed bit is set only for ARMING_STATE_ARMED. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/HEARTBEAT.hpp#L82

MAVLink/观测映射：

- `HEARTBEAT.base_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。MAV_MODE_FLAG_SAFETY_ARMED reports state; no timestamp or disarm reason.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `EVENT.id` (ID 410)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `event_time_boot_ms (PX4 system boot clock)`。May carry automatic-disarm reason and event timestamp. Requires firmware-matched component metadata to decode id/arguments.
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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=disable-domain source conflict; eligibility exceptions incomplete; cancel semantics absent; PARTIALLY_BOUND AP; no concrete monitor formula. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- COM_DISARM_LAND 禁用域冲突。
- eligibility 官方上下文尚未闭合。
- M7 automated independent audit: disable-domain source conflict
- M7 automated independent audit: eligibility exceptions incomplete
- M7 automated independent audit: cancel semantics absent
- M7 automated independent audit: PARTIALLY_BOUND AP
- M7 automated independent audit: no concrete monitor formula

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
