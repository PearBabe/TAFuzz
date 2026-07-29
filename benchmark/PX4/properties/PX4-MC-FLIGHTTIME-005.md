# PX4-MC-FLIGHTTIME-005 — PX4 最大飞行时间

- 系统/车型：PX4 / multicopter SITL
- 固件提交：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### PX4-MC-FLIGHTTIME-005-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/config/safety.md:96-110`
- SHA-256：`82b627ef4c4d323ef5e524c5630903c31570e103a9701b65a5f4b8fb33ee4db3`

```text
### Flight Time Failsafes

There are several other "battery related" failsafe mechanisms that may be configured using parameters:

- The "remaining flight time for safe return" failsafe ([COM_FLTT_LOW_ACT](#COM_FLTT_LOW_ACT)) is engaged when PX4 estimates that the vehicle has just enough battery remaining for a return mode landing.
  You can configure this to ignore the failsafe, warn, or engage Return mode.
- The "maximum flight time failsafe" ([COM_FLT_TIME_MAX](#COM_FLT_TIME_MAX)) allows you to set a maximum flight time after takeoff, at which the vehicle will automatically enter return mode (it will also "warn" at 90% of this time). This is like a "hard coded" estimate of the total flight time in a battery. The feature is disabled by default.
- The "minimum battery" for arming parameter ([COM_ARM_BAT_MIN](#COM_ARM_BAT_MIN)) prevents arming in the first place if the battery level is below the specified value.

The settings and underlying parameters are shown below.

| Setting                                                              | Parameter                                                                      | Description                                                                                                                     |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| <a id="COM_FLTT_LOW_ACT"></a> Low flight time for safe return action | [COM_FLTT_LOW_ACT](../advanced_config/parameter_reference.md#COM_FLTT_LOW_ACT) | Action when return mode can only just reach safety with remaining battery. `0`: None, `1`: Warning, `3`: Return mode (default). |
| <a id="COM_FLT_TIME_MAX"></a> Maximum flight time failsafe level     | [COM_FLT_TIME_MAX](../advanced_config/parameter_reference.md#COM_FLT_TIME_MAX) | Maximum allowed flight time before Return mode will be engaged, in seconds. `-1`: Disabled (default).                           |
```

上下文：定义 takeoff 后最大飞行时间、90% warning、Return 和 -1 禁用。

### PX4-MC-FLIGHTTIME-005-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` / `RELEASE_PINNED`
- 位置：`baseline/px4/src/modules/commander/commander_params.c:884-897`
- SHA-256：`4e83db4e821aac5fb5ad96aa7755bac8dffac0714581d0895688198c8e41902a`

```text
* the time since takeoff is above this value. It is not possible to resume the
 * mission or switch to any auto mode other than RTL or Land. Taking over in any manual
 * mode is still possible.
 *
 * Starting from 90% of the maximum flight time, a warning message will be sent
 * every 1 minute with the remaining time until automatic RTL.
 *
 * Set to -1 to disable.
 *
 * @unit s
 * @min -1
 * @group Commander
 */
PARAM_DEFINE_INT32(COM_FLT_TIME_MAX, -1);
```

上下文：冻结提交中的秒单位、范围、默认/禁用值。

## Requirement IR

- 主体：PX4 Commander flight-time check
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：飞控检测到 takeoff，且 COM_FLT_TIME_MAX 启用。
- 前置：COM_FLT_TIME_MAX > 0。；takeoff epoch 来自 detected takeoff，而非 arm time 或 GCS command time。
- 义务：0.9*T 时发出 warning；T 时进入 Return。
- 禁止：在相应边界前不得仅由最大飞行时间机制产生 warning/Return。
- 例外：-1/非正配置禁用。；disarm 终止本次 flight-time scope。
- 作用域：detected takeoff → disarm、run 结束或完成本次 flight scope

## 时间与 MITL

- `T_flight_max`：`T_warning = 0.9 * runtime(COM_FLT_TIME_MAX); T_flight_max = runtime(COM_FLT_TIME_MAX)`；单位 `s`；下界闭合 `True`。
  起点：detected_takeoff；终点：enter_return；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：PX4 vehicle_status.takeoff_time HRT。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((detected_takeoff & max_flight_time_enabled) -> ((G_[0,0.9*T_flight_max) !flight_time_warning & F_[0.9*T_flight_max,infty) flight_time_warning) & (G_[0,T_flight_max) !mode_return & F_[T_flight_max,infty) mode_return)))`
- 单一具体公式：`null`（没有单一、已启用且上下文闭合的具体实例）
- 形式化状态：`NEEDS_CONTEXT`

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| PX4/multicopter — px4_sitl_default sihsim_quadx internal headless SIH instance 42 / `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` | `-1 s` | `-1.0 s` | `DISABLED_BY_RUNTIME_CONFIGURATION` | `未形式化` | `benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json` SHA-256 `42d4fae5d576488a3584526c725330411f03dc438df24db7ab7ad7bdeb61af44`，index `271/900` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `PX4-MC-FLIGHTTIME-005-AP-01` | landed true->false while armed 的 takeoff event。 | `CONDITIONAL` | `BOUND` |
| `PX4-MC-FLIGHTTIME-005-AP-02` | PARAM_VALUE(COM_FLT_TIME_MAX)>0。 | `DIRECT` | `BOUND` |
| `PX4-MC-FLIGHTTIME-005-AP-03` | 与当前 takeoff epoch/COM_FLT_TIME_MAX 关联的 warning event。 | `CONDITIONAL` | `BOUND` |
| `PX4-MC-FLIGHTTIME-005-AP-04` | current navigation mode/custom mode 为 RTL/Return。 | `DIRECT` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### PX4-MC-FLIGHTTIME-005-AP-01 — `detected_takeoff`

- 受控自然语言：Commander 记录本次 takeoff epoch。
- 真值条件：landed true->false while armed 的 takeoff event。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Commander-recorded takeoff epoch in vehicle boot microseconds.` — `baseline/px4/msg/versioned/VehicleStatus.msg:8`；symbol `takeoff_time`；kind `FIELD`；function ``；type `uint64`；role `DEFINITION`；confidence `EXACT`。
  证据：The field stores the detected takeoff timestamp used by flight-time checks. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L8
- `Commander consumer for vehicle_land_detected transitions.` — `baseline/px4/src/modules/commander/Commander.cpp:2124`；symbol `Commander::landDetectorUpdate`；kind `FUNCTION`；function `Commander::landDetectorUpdate`；type `void()`；role `CONSUMER`；confidence `EXACT`。
  证据：The function copies the land-detector topic and compares previous/current landed state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2124
- `Armed landed-to-air transition guard for takeoff detection.` — `baseline/px4/src/modules/commander/Commander.cpp:2136`；symbol `was_landed`；kind `OTHER`；function `Commander::landDetectorUpdate`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：The enclosing armed guard and this previous/current comparison identify detected takeoff. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2136
- `Named event emitted at the detected takeoff transition.` — `baseline/px4/src/modules/commander/Commander.cpp:2138`；symbol `commander_takeoff_detected`；kind `EVENT`；function `Commander::landDetectorUpdate`；type `events::ID`；role `PRODUCER`；confidence `EXACT`。
  证据：The event is generated immediately before takeoff_time is written. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2138
- `Assignment of the detected takeoff epoch to VehicleStatus.` — `baseline/px4/src/modules/commander/Commander.cpp:2139`；symbol `_vehicle_status.takeoff_time`；kind `ASSIGNMENT`；function `Commander::landDetectorUpdate`；type `uint64_t`；role `WRITE`；confidence `EXACT`。
  证据：The vehicle's hrt clock is sampled at the transition. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2139

MAVLink/观测映射：

- `EXTENDED_SYS_STATE.landed_state` (ID 245)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。MAV_LANDED_STATE_ON_GROUND directly reports state; message has no timestamp, so the transition epoch needs EVENT/internal HRT for strict timing.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `EVENT.id` (ID 410)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `event_time_boot_ms (PX4 system boot clock)`。May carry takeoff-detected event with vehicle boot timestamp. Requires firmware-matched component metadata to decode id/arguments.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-FLIGHTTIME-005-AP-02 — `max_flight_time_enabled`

- 受控自然语言：运行时 COM_FLT_TIME_MAX 为正。
- 真值条件：PARAM_VALUE(COM_FLT_TIME_MAX)>0。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Runtime maximum flight-time parameter in seconds; positive means enabled in the normalized AP.` — `baseline/px4/src/modules/commander/commander_params.c:897`；symbol `COM_FLT_TIME_MAX`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：The source defines identity and default -1; only captured runtime value is used by the AP. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L897
- `Typed Commander parameter wrapper consumed by FlightTimeChecks.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.hpp:50`；symbol `COM_FLT_TIME_MAX`；kind `PARAMETER`；function `FlightTimeChecks::checkAndReport`；type `ParamInt<px4::params::COM_FLT_TIME_MAX>`；role `READ`；confidence `EXACT`。
  证据：The wrapper supplies the runtime value to flight-time logic. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.hpp#L50
- `Positive-value guard enabling warning-time calculation.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp:63`；symbol `_param_com_flt_time_max`；kind `OTHER`；function `FlightTimeChecks::checkAndReport`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：The check compares the runtime parameter to zero. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp#L63
- `MAVLink PARAM_VALUE producer used to return runtime parameter values.` — `baseline/px4/src/modules/mavlink/mavlink_parameters.cpp:549`；symbol `mavlink_msg_param_value_send_struct`；kind `MESSAGE_PRODUCER`；function `MavlinkParametersManager::send_param`；type `mavlink_param_value_t`；role `PRODUCER`；confidence `EXACT`。
  证据：param_id is populated at line 525 and the typed value is sent here. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_parameters.cpp#L549

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects COM_FLT_TIME_MAX; enabled iff >0
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-FLIGHTTIME-005-AP-03 — `flight_time_warning`

- 受控自然语言：90% flight-time warning 发生。
- 真值条件：与当前 takeoff epoch/COM_FLT_TIME_MAX 关联的 warning event。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Remaining-flight-time derivation from takeoff_time and COM_FLT_TIME_MAX.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp:65`；symbol `remaining_flight_time_sec`；kind `VARIABLE`；function `FlightTimeChecks::checkAndReport`；type `const float`；role `DERIVATION`；confidence `EXACT`。
  证据：The following lines subtract elapsed flight time from the runtime limit. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp#L65
- `Implementation last-ten-percent guard.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp:69`；symbol `remaining_flight_time_sec`；kind `OTHER`；function `FlightTimeChecks::checkAndReport`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：The guard compares remaining time with 0.1 times the configured maximum. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp#L69
- `Seconds-form warning event identity for the final minute.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp:86`；symbol `commander_max_flight_time_warning_seconds`；kind `EVENT`；function `FlightTimeChecks::checkAndReport`；type `events::ID with int16 argument`；role `PRODUCER`；confidence `EXACT`。
  证据：The event argument is floored remaining seconds. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp#L86
- `Minutes-form warning event identity for earlier whole-minute warnings.` — `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp:103`；symbol `commander_max_flight_time_warning_minutes`；kind `EVENT`；function `FlightTimeChecks::checkAndReport`；type `events::ID with int16 argument`；role `PRODUCER`；confidence `EXACT`。
  证据：The event is emitted on the guarded whole-minute schedule. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/flightTimeCheck.cpp#L103
- `MAVLink EVENT producer preserving PX4 warning event ID, arguments, and vehicle time.` — `baseline/px4/src/modules/mavlink/mavlink_events.cpp:209`；symbol `SendProtocol::send_event`；kind `MESSAGE_PRODUCER`；function `SendProtocol::send_event`；type `void(const Event &)`；role `PRODUCER`；confidence `EXACT`。
  证据：event_time_boot_ms, ID, and arguments are sent by this function. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_events.cpp#L209

MAVLink/观测映射：

- `EVENT.id` (ID 410)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `event_time_boot_ms (PX4 system boot clock)`。Carries maximum-flight-time warning when emitted. Requires firmware-matched component metadata to decode id/arguments.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-FLIGHTTIME-005-AP-04 — `mode_return`

- 受控自然语言：PX4 进入 Return。
- 真值条件：current navigation mode/custom mode 为 RTL/Return。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Internal maximum-flight-time-exceeded cause flag.` — `baseline/px4/msg/FailsafeFlags.msg:52`；symbol `flight_time_limit_exceeded`；kind `FIELD`；function ``；type `bool`；role `DEFINITION`；confidence `EXACT`。
  证据：This cause is upstream of the nondeferable RTL action. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L52
- `Failsafe invocation mapping the flight-time limit cause to a nondeferable RTL action.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:544`；symbol `flight_time_limit_exceeded`；kind `OTHER`；function `Failsafe::update`；type `CHECK_FAILSAFE invocation`；role `DERIVATION`；confidence `EXACT`。
  证据：The macro call identifies the cause-to-action mapping; it does not assess whether the cause occurs. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L544
- `Failsafe action-to-VehicleStatus AUTO_RTL mode mapping.` — `baseline/px4/src/modules/commander/failsafe/framework.cpp:682`；symbol `Action::RTL`；kind `RETURN`；function `FailsafeBase::modeFromAction`；type `uint8_t`；role `DERIVATION`；confidence `EXACT`。
  证据：Action::RTL returns NAVIGATION_STATE_AUTO_RTL. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/framework.cpp#L682
- `Commander assignment of the selected and available failsafe mode to current nav_state.` — `baseline/px4/src/modules/commander/Commander.cpp:2371`；symbol `_vehicle_status.nav_state`；kind `ASSIGNMENT`；function `Commander::Run`；type `uint8_t`；role `WRITE`；confidence `EXACT`。
  证据：Mode management may replace an unavailable requested state before this write. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2371
- `VehicleStatus enum constant for Return/RTL mode.` — `baseline/px4/msg/versioned/VehicleStatus.msg:41`；symbol `NAVIGATION_STATE_AUTO_RTL`；kind `OTHER`；function ``；type `uint8 constant`；role `DEFINITION`；confidence `EXACT`。
  证据：This is the direct internal mode identity for the AP. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Decode AUTO_RTL/Return. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `CURRENT_MODE.custom_mode` (ID 436)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Direct current mode; no embedded timestamp.
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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=symbolic formula weakens boundary/repetition semantics; current runtime disabled; EVENT IDs not demonstrated; no concrete monitor formula. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- 默认 -1 表示 disabled；不得生成默认 concrete 公式。
- M7 automated independent audit: symbolic formula weakens boundary/repetition semantics
- M7 automated independent audit: current runtime disabled
- M7 automated independent audit: EVENT IDs not demonstrated
- M7 automated independent audit: no concrete monitor formula

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
