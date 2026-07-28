# PX4-MC-RTLLOITER-006 — PX4 RTL 目的地等待后着陆

- 系统/车型：PX4 / multicopter SITL
- 固件提交：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### PX4-MC-RTLLOITER-006-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/flight_modes/return.md:183-194`
- SHA-256：`691fd37e377e26dc2ec7bf4b92ebdc733d52f3278a5ec5167739ca1eefef9f22`

```text
## Loiter/Landing at Destination

Unless executing a [mission landing pattern](#mission-landing-pattern) as part of the return mode, the vehicle will arrive at its destination, and rapidly descend to the [RTL_DESCEND_ALT](#RTL_DESCEND_ALT) altitude, where it will loiter for [RTL_LAND_DELAY](#RTL_LAND_DELAY) before landing.
If `RTL_LAND_DELAY=-1` it will loiter indefinitely.

The default landing configuration is vehicle dependent:

- Multicopters are configured to hover for a short while, deploying landing gear if needed, and then land.
- Fixed-wing vehicles use a return mode with a [mission landing pattern](#mission-landing-pattern), as this enables automated landing.
  If not using a mission landing, the default configuration is to loiter indefinitely, so the user can take over and manually land.
- VTOLs in MC mode fly and land exactly as a multicopter.
- VTOLS in FW mode head towards the landing point, transition to MC mode, and then land on the destination.
```

上下文：定义非 mission landing 时到达目的地、RTL_DESCEND_ALT、等待与 landing。

### PX4-MC-RTLLOITER-006-S2

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/flight_modes/return.md:204-218`
- SHA-256：`691fd37e377e26dc2ec7bf4b92ebdc733d52f3278a5ec5167739ca1eefef9f22`

```text
## Parameters

The RTL parameters are listed in [Parameter Reference > Return Mode](../advanced_config/parameter_reference.md#return-mode) (and summarised below).

| Parameter                                                                                                   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <a id="RTL_TYPE"></a>[RTL_TYPE](../advanced_config/parameter_reference.md#RTL_TYPE)                         | Return mechanism (path and destination).<br>`0`: Return to a rally point or home (whichever is closest) via direct path.<br>`1`: Return to a rally point or the mission landing pattern start point (whichever is closest), via direct path. If neither mission landing or rally points are defined return home via a direct path. If the destination is a mission landing pattern, follow the pattern to land.<br>`2`: Use mission path fast-forward to landing if a landing pattern is defined, otherwise fast-reverse to home. Ignore rally points. Fly direct to home if no mission plan is defined.<br>`3`: Return via direct path to closest destination: home, start of mission landing pattern or safe point. If the destination is a mission landing pattern, follow the pattern to land. |
| <a id="RTL_RETURN_ALT"></a>[RTL_RETURN_ALT](../advanced_config/parameter_reference.md#RTL_RETURN_ALT)       | Return altitude in meters (default: 60m) when [RTL_CONE_ANG](../advanced_config/parameter_reference.md#RTL_CONE_ANG) is 0. If already above this value the vehicle will return at its current altitude.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| <a id="RTL_DESCEND_ALT"></a>[RTL_DESCEND_ALT](../advanced_config/parameter_reference.md#RTL_DESCEND_ALT)    | Minimum return altitude and altitude at which the vehicle will slow or stop its initial descent from a higher return altitude (default: 30m)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| <a id="RTL_LAND_DELAY"></a>[RTL_LAND_DELAY](../advanced_config/parameter_reference.md#RTL_LAND_DELAY)       | Time to wait at `RTL_DESCEND_ALT` before landing (default: 0.5s) -by default this period is short so that the vehicle will simply slow and then land immediately. If set to -1 the system will loiter at `RTL_DESCEND_ALT` rather than landing. The delay is provided to allow you to configure time for landing gear to be deployed (triggered automatically).                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| <a id="RTL_MIN_DIST"></a>[RTL_MIN_DIST](../advanced_config/parameter_reference.md#RTL_MIN_DIST)             | Minimum horizontal distance from home position to trigger ascent to the return altitude specified by the "cone". If the vehicle is horizontally closer than this distance to home, it will return at its current altitude or `RTL_DESCEND_ALT` (whichever is higher) instead of first ascending to RTL_RETURN_ALT.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| <a id="RTL_CONE_ANG"></a>[RTL_CONE_ANG](../advanced_config/parameter_reference.md#RTL_CONE_ANG)             | Half-angle of the cone that defines the vehicle RTL return altitude. Values (in degrees): 0, 25, 45, 65, 80, 90. Note that 0 is "no cone" (always return at `RTL_RETURN_ALT` or higher), while 90 indicates that the vehicle must return at the current altitude or `RTL_DESCEND_ALT` (whichever is higher).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| <a id="COM_RC_OVERRIDE"></a>[COM_RC_OVERRIDE](../advanced_config/parameter_reference.md#COM_RC_OVERRIDE)    | Controls whether stick movement on a multicopter (or VTOL in MC mode) causes a mode change to [Position mode](../flight_modes_mc/position.md) (except when vehicle is handling a critical battery failsafe). This can be separately enabled for auto modes and for offboard mode, and is enabled in auto modes by default.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| <a id="COM_RC_STICK_OV"></a>[COM_RC_STICK_OV](../advanced_config/parameter_reference.md#COM_RC_STICK_OV)    | The amount of stick movement that causes a transition to [Position mode](../flight_modes_mc/position.md) (if [COM_RC_OVERRIDE](#COM_RC_OVERRIDE) is enabled).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| <a id="RTL_LOITER_RAD"></a>[RTL_LOITER_RAD](../advanced_config/parameter_reference.md#RTL_LOITER_RAD)       | [Fixed-wing Only] The radius of the loiter circle (at [RTL_LAND_DELAY](#RTL_LAND_DELAY)).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
```

上下文：参数表给出 RTL_LAND_DELAY 文档默认 0.5s 和 -1 indefinite。

### PX4-MC-RTLLOITER-006-S3

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` / `RELEASE_PINNED`
- 位置：`baseline/px4/src/modules/navigator/rtl_params.c:63-89`
- SHA-256：`22c2a14bc18a04f5ac0efad16ddcca0ca723cc8d8579277fc60de858f4805fc0`

```text
* Return mode loiter altitude
 *
 * Descend to this altitude (above destination position) after return, and wait for time defined in RTL_LAND_DELAY.
 * Land (i.e. slowly descend) from this altitude if autolanding allowed.
 * VTOLs do transition to hover in this altitdue above the landing point.
 *
 * @unit m
 * @min 0
 * @decimal 1
 * @increment 0.5
 * @group Return Mode
 */
PARAM_DEFINE_FLOAT(RTL_DESCEND_ALT, 30.f);

/**
 * Return mode delay
 *
 * Delay before landing (after initial descent) in Return mode.
 * If set to -1 the system will not land but loiter at RTL_DESCEND_ALT.
 *
 * @unit s
 * @min -1
 * @decimal 1
 * @increment 0.5
 * @group Return Mode
 */
PARAM_DEFINE_FLOAT(RTL_LAND_DELAY, 0.0f);
```

上下文：冻结提交元数据默认 0.0s，与文档默认 0.5s 冲突；运行时值优先。

## Requirement IR

- 主体：PX4 Navigator direct Return
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：非 mission landing 的 Return 到达目的地 RTL_DESCEND_ALT 并进入等待阶段。
- 前置：使用适用的 direct-return landing path。；RTL_LAND_DELAY >= 0；-1 的 indefinite 变体单独处理。
- 义务：等待运行时 RTL_LAND_DELAY 后开始 Land。
- 禁止：等待期间不得在配置时间结束前进入 Land。
- 例外：mission landing pattern 不使用此直接等待义务。；RTL_LAND_DELAY=-1 表示 indefinite，合法 mode transition 可结束。
- 作用域：进入目的地 RTL_DESCEND_ALT loiter phase → Land、离开 Return、indefinite override 或 run 结束

## 时间与 MITL

- `T_rtl_land`：`T_rtl_land = runtime(RTL_LAND_DELAY)`；单位 `s`；下界闭合 `True`。
  起点：enter_rtl_destination_loiter；终点：enter_land；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：PX4 Navigator HRT phase entry。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((enter_rtl_destination_loiter & direct_return_landing_path) -> (G_[0,T_rtl_land) !mode_land & F_[T_rtl_land,infty) mode_land))`
- 单一具体公式：`null`（没有单一、已启用且上下文闭合的具体实例）
- 形式化状态：`NEEDS_CONTEXT`

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| PX4/multicopter — px4_sitl_default sihsim_quadx internal headless SIH instance 42 / `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` | `0.0 s` | `0.0 s` | `NEEDS_CONTEXT` | `G((enter_rtl_destination_loiter & direct_return_landing_path) -> (G_[0,0) !mode_land & F_[0,infty) mode_land))` | `benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json` SHA-256 `42d4fae5d576488a3584526c725330411f03dc438df24db7ab7ad7bdeb61af44`，index `796/900` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `PX4-MC-RTLLOITER-006-AP-01` | Navigator RTL phase entry event；纯 wire 推导必须同时满足 mode/target/position freshness。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `PX4-MC-RTLLOITER-006-AP-02` | runtime RTL_TYPE/mission state 选择 direct landing path。 | `DERIVED` | `BOUND` |
| `PX4-MC-RTLLOITER-006-AP-03` | current navigation mode 为 AUTO_LAND；是否计入 DESCEND 必须在 campaign 前固定。 | `DIRECT` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### PX4-MC-RTLLOITER-006-AP-01 — `enter_rtl_destination_loiter`

- 受控自然语言：direct RTL 到达目的地下降高度并进入等待 phase。
- 真值条件：Navigator RTL phase entry event；纯 wire 推导必须同时满足 mode/target/position freshness。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Direct-RTL state-machine phase for destination loiter hold.` — `baseline/px4/src/modules/navigator/rtl_direct.h:124`；symbol `LOITER_HOLD`；kind `OTHER`；function ``；type `RtlDirect::RTLState`；role `DEFINITION`；confidence `EXACT`。
  证据：The AP's internal phase identity is this enum value. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.h#L124
- `State-machine transition target after LOITER_DOWN reaches its mission item.` — `baseline/px4/src/modules/navigator/rtl_direct.cpp:187`；symbol `RTLState::LOITER_HOLD`；kind `ASSIGNMENT`；function `RtlDirect::_updateRtlState`；type `RtlDirect::RTLState`；role `WRITE`；confidence `EXACT`。
  证据：new_state is set to LOITER_HOLD in the LOITER_DOWN branch. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L187
- `Commit of the computed direct-RTL phase transition.` — `baseline/px4/src/modules/navigator/rtl_direct.cpp:223`；symbol `_rtl_state`；kind `ASSIGNMENT`；function `RtlDirect::_updateRtlState`；type `RtlDirect::RTLState`；role `WRITE`；confidence `EXACT`。
  证据：Instrumentation at this assignment gives the exact phase-entry event. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L223
- `Logging projection of current direct-RTL enum value into navigator_mission_item.sequence_current.` — `baseline/px4/src/modules/navigator/rtl_direct.cpp:601`；symbol `navigator_mission_item.sequence_current`；kind `ASSIGNMENT`；function `RtlDirect::publish_rtl_direct_navigator_mission_item`；type `uint16_t`；role `OBSERVATION_SITE`；confidence `MODELLED`。
  证据：The projection is exact only when interpreted in the direct-RTL producer context; the field has other semantics in other Navigator paths. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L601
- `uORB/log producer for the current direct-RTL phase projection and vehicle timestamp.` — `baseline/px4/src/modules/navigator/rtl_direct.cpp:623`；symbol `_navigator_mission_item_pub.publish`；kind `MESSAGE_PRODUCER`；function `RtlDirect::publish_rtl_direct_navigator_mission_item`；type `uORB::Publication<navigator_mission_item_s>`；role `PRODUCER`；confidence `MODELLED`。
  证据：Use only with direct-RTL context and sequence_current enum mapping. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L623

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Confirms Return mode only. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-RTLLOITER-006-AP-02 — `direct_return_landing_path`

- 受控自然语言：当前 Return 不使用 mission landing pattern。
- 真值条件：runtime RTL_TYPE/mission state 选择 direct landing path。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DERIVED`；绑定状态：`BOUND`

源码绑定：

- `Runtime RTL path-preference parameter.` — `baseline/px4/src/modules/navigator/rtl_params.c:118`；symbol `RTL_TYPE`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：The parameter influences but does not alone determine the selected runtime RtlType. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L118
- `Runtime path-selection function combining RTL_TYPE, mission landing availability, safe points, and destination choice.` — `baseline/px4/src/modules/navigator/rtl.cpp:311`；symbol `RTL::setRtlTypeAndDestination`；kind `FUNCTION`；function `RTL::setRtlTypeAndDestination`；type `void()`；role `DERIVATION`；confidence `EXACT`。
  证据：This function resolves the actual RTL type rather than copying RTL_TYPE directly. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L311
- `Selection of direct travel to a mission landing pattern, which is excluded by the normalized direct-landing-path AP.` — `baseline/px4/src/modules/navigator/rtl.cpp:327`；symbol `RTL_DIRECT_MISSION_LAND`；kind `ASSIGNMENT`；function `RTL::setRtlTypeAndDestination`；type `RTL::RtlType`；role `WRITE`；confidence `EXACT`。
  证据：Destination type MISSION_LAND selects the distinct runtime type. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L327
- `Selection of direct safe-point/home landing path.` — `baseline/px4/src/modules/navigator/rtl.cpp:348`；symbol `RtlType::RTL_DIRECT`；kind `ASSIGNMENT`；function `RTL::setRtlTypeAndDestination`；type `RTL::RtlType`；role `WRITE`；confidence `EXACT`。
  证据：This is the runtime type matching the normalized direct path. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L348
- `uORB rtl_status field assignment exposing the resolved runtime RTL type.` — `baseline/px4/src/modules/navigator/rtl.cpp:362`；symbol `rtl_type`；kind `ASSIGNMENT`；function `RTL::setRtlTypeAndDestination`；type `uint8_t`；role `PRODUCER`；confidence `EXACT`。
  证据：RtlType::RTL_DIRECT maps to RtlStatus direct safe-point value 1 and is published at line 365. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L362

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects RTL_TYPE, RTL_LAND_DELAY; combine with mission snapshot
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Current Return mode. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-RTLLOITER-006-AP-03 — `mode_land`

- 受控自然语言：PX4 进入 Land/明确约定的 descend outcome。
- 真值条件：current navigation mode 为 AUTO_LAND；是否计入 DESCEND 必须在 campaign 前固定。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Current active navigation-state field used for exact internal Land-mode identity.` — `baseline/px4/msg/versioned/VehicleStatus.msg:35`；symbol `nav_state`；kind `FIELD`；function ``；type `uint8`；role `DEFINITION`；confidence `EXACT`。
  证据：The exact catalog default compares this field with NAVIGATION_STATE_AUTO_LAND. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35
- `VehicleStatus enum constant for Auto Land mode.` — `baseline/px4/msg/versioned/VehicleStatus.msg:54`；symbol `NAVIGATION_STATE_AUTO_LAND`；kind `OTHER`；function ``；type `uint8 constant`；role `DEFINITION`；confidence `EXACT`。
  证据：This is the exact internal mode identity specified by the catalog default. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54
- `Distinct internal Descend navigation state whose inclusion is a campaign-level choice.` — `baseline/px4/msg/versioned/VehicleStatus.msg:48`；symbol `NAVIGATION_STATE_DESCEND`；kind `OTHER`；function ``；type `uint8 constant`；role `DEFINITION`；confidence `EXACT`。
  证据：It is not AUTO_LAND internally even though PX4 custom-mode mapping conflates them. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L48
- `Direct-RTL internal phase that builds a land mission item; it is related path evidence, not identical to VehicleStatus AUTO_LAND.` — `baseline/px4/src/modules/navigator/rtl_direct.cpp:365`；symbol `RTLState::LAND`；kind `OTHER`；function `RtlDirect::set_rtl_item`；type `RtlDirect::RTLState`；role `DERIVATION`；confidence `MAY`。
  证据：Navigator LAND phase can execute while coarse vehicle mode remains RTL; do not substitute it for nav_state. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L365
- `uORB producer for exact current nav_state and vehicle timestamp.` — `baseline/px4/src/modules/commander/Commander.cpp:1945`；symbol `_vehicle_status_pub.publish`；kind `MESSAGE_PRODUCER`；function `Commander::Run`；type `uORB::Publication<vehicle_status_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Internal vehicle_status instrumentation distinguishes AUTO_LAND from DESCEND. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L1945
- `Custom-mode mapping branch that maps internal DESCEND to PX4 AUTO_LAND wire submode.` — `baseline/px4/src/modules/commander/px4_custom_mode.h:148`；symbol `NAVIGATION_STATE_DESCEND`；kind `OTHER`；function `get_px4_custom_mode`；type `switch case`；role `DERIVATION`；confidence `EXACT`。
  证据：AUTO_LAND is also mapped to the same wire submode at lines 170-172, creating a wire ambiguity. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L148

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Decode AUTO_LAND; no timestamp. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `CURRENT_MODE.custom_mode` (ID 436)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Direct current mode; no timestamp.
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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=default conflict and essential path context; mission snapshot missing; phase/cancel/indefinite semantics unresolved; exact phase not MAVLink-observable; no concrete formula. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- docs default 0.5s vs source metadata default 0.0s。
- mission landing exclusion 和 exact phase 需要绑定。
- M7 automated independent audit: default conflict and essential path context
- M7 automated independent audit: mission snapshot missing
- M7 automated independent audit: phase/cancel/indefinite semantics unresolved
- M7 automated independent audit: exact phase not MAVLink-observable
- M7 automated independent audit: no concrete formula

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
