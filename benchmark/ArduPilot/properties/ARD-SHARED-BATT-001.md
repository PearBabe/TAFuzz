# ARD-SHARED-BATT-001 — ArduPilot 持续低电压 failsafe

- 系统/车型：ArduPilot / Copter, Plane, Rover
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-SHARED-BATT-001-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`209e532bc97e5a41966f8c9ab483323c264cae08` / `MAIN_ONLY`
- 位置：`benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/failsafe-battery.rst:93-96`
- SHA-256：`a34676dda9ba0afbcaae28709416dac45a31370271e778c4fe579a55155cf36b`

```text
- :ref:`BATT_FS_VOLTSRC <BATT_FS_VOLTSRC>` allows configuring whether the raw battery voltage or a sag corrected voltage is used
- :ref:`BATT_LOW_TIMER <BATT_LOW_TIMER>` can configure how long the voltage must be below the threshold for the failsafe to trigger
- ``BATTx_`` parameters can be setup to trigger the failsafe on other batteries
```

上下文：说明电压源、LOW_TIMER 与多电池实例化。

### ARD-SHARED-BATT-001-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Params.cpp:95-129`
- SHA-256：`c674aab5ff5631b1c19e9e556a23d7386cb2f89e57b807d2a70060c6096f0563`

```text
// @Param: LOW_TIMER
    // @DisplayName: Low voltage timeout
    // @Description: This is the timeout in seconds before a low voltage event will be triggered. For aircraft with low C batteries it may be necessary to raise this in order to cope with low voltage on long takeoffs. A value of zero disables low voltage errors.
    // @Units: s
    // @Increment: 1
    // @Range: 0 120
    // @User: Advanced
    AP_GROUPINFO("LOW_TIMER", 10, AP_BattMonitor_Params, _low_voltage_timeout, 10),

    // @Param: FS_VOLTSRC
    // @DisplayName: Failsafe voltage source
    // @Description: Voltage type used for detection of low voltage event
    // @Values: 0:Raw Voltage, 1:Sag Compensated Voltage
    // @User: Advanced
    AP_GROUPINFO("FS_VOLTSRC", 11, AP_BattMonitor_Params, _failsafe_voltage_source, BattMonitor_LowVoltageSource_Raw),

    // @Param: LOW_VOLT
    // @DisplayName: Low battery voltage
    // @Description: Battery voltage that triggers a low battery failsafe. Set to 0 to disable. If the battery voltage drops below this voltage continuously for more then the period specified by the @PREFIX@LOW_TIMER parameter then the vehicle will perform the failsafe specified by the @PREFIX@FS_LOW_ACT parameter.
    // @Units: V
    // @Increment: 0.1
    // @User: Standard
    AP_GROUPINFO("LOW_VOLT", 12, AP_BattMonitor_Params, _low_voltage, DEFAULT_LOW_BATTERY_VOLTAGE),

    // @Param: LOW_MAH
    // @DisplayName: Low battery capacity
    // @Description: Battery capacity at which the low battery failsafe is triggered. Set to 0 to disable battery remaining failsafe. If the battery capacity drops below this level the vehicle will perform the failsafe specified by the @PREFIX@FS_LOW_ACT parameter.
    // @Units: mAh
    // @Increment: 50
    // @User: Standard
    AP_GROUPINFO("LOW_MAH", 13, AP_BattMonitor_Params, _low_capacity, 0),

    // @Param: CRT_VOLT
    // @DisplayName: Critical battery voltage
    // @Description: Battery voltage that triggers a critical battery failsafe. Set to 0 to disable. If the battery voltage drops below this voltage continuously for more then the period specified by the @PREFIX@LOW_TIMER parameter then the vehicle will perform the failsafe specified by the @PREFIX@FS_CRT_ACT parameter.
```

上下文：冻结源码中的 LOW_TIMER、LOW_VOLT、CRT_VOLT 及连续超过时间的语义。

## Requirement IR

- 主体：AP_BattMonitor and vehicle failsafe callback
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：某 battery instance 的选定电压源持续低于运行时 LOW_VOLT。
- 前置：该 instance 的 LOW_VOLT 非零。；记录 BATTx_FS_VOLTSRC，区分 raw 与 sag-corrected resting estimate。；low 与 critical variant 分开验证。
- 义务：连续低于阈值超过运行时 LOW_TIMER 后触发该 instance 对应 low/critical event 和配置 action。
- 禁止：在严格超过 LOW_TIMER 前不得仅由该低电压区间触发。
- 例外：电压恢复到不低于阈值会重置持续区间。；capacity-based path 不属于本性质。
- 作用域：选定电压源首次低于 instance threshold → 电压恢复、event/action、monitor instance disabled 或 run 结束

## 时间与 MITL

- `T_low_voltage`：`T_low_voltage = runtime(BATTx_LOW_TIMER)`；单位 `s`；下界闭合 `False`。
  起点：low_voltage_interval_start；终点：battery_failsafe_event；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：battery-backend vehicle millis。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((low_voltage_start & voltage_threshold_enabled) -> (G_[0,T_low_voltage] !battery_failsafe_event & F_(T_low_voltage,infty) battery_failsafe_event))`
- 单一具体公式：`G((low_voltage_start & voltage_threshold_enabled) -> (G_[0,10] !battery_failsafe_event & F_(10,infty) battery_failsafe_event))`
- 形式化状态：`MONITOR_VALIDATED`

- TAMonitor 转换候选：`G((low_voltage_start && voltage_threshold_enabled) -> (G[0,10000] (!battery_failsafe_event) && F(10000,infty) battery_failsafe_event))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/ArduCopter — quad / `ardupilot-copter-m6` | `10 s` | `10.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((low_voltage_start & voltage_threshold_enabled) -> (G_[0,10] !battery_failsafe_event & F_(10,infty) battery_failsafe_event))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/parameters.json` SHA-256 `f3d4a3e416eb7e01000deec397640cbf291c8b14805073da5b256b88c6de61ab`，index `337/1387` |
| ArduPilot/ArduPlane — plane / `ardupilot-plane-m6` | `10 s` | `10.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((low_voltage_start & voltage_threshold_enabled) -> (G_[0,10] !battery_failsafe_event & F_(10,infty) battery_failsafe_event))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Plane/parameters.json` SHA-256 `0767f3f3019f5399679118cbcf0931e552bdb6ee40cc67303a8b476a6e61c4dd`，index `442/1440` |
| ArduPilot/Rover — rover / `ardupilot-rover-m6` | `10 s` | `10.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((low_voltage_start & voltage_threshold_enabled) -> (G_[0,10] !battery_failsafe_event & F_(10,infty) battery_failsafe_event))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Rover/parameters.json` SHA-256 `ed4de8b303095cf19449c9e6181678863cf25ba3eee8ff47ae5bf683e432fd79`，index `612/1271` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-SHARED-BATT-001-AP-01` | selected_voltage(instance)<PARAM_VALUE(BATTx_LOW_VOLT) 的上升沿。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-SHARED-BATT-001-AP-02` | PARAM_VALUE(BATTx_LOW_VOLT)>0。 | `DIRECT` | `BOUND` |
| `ARD-SHARED-BATT-001-AP-03` | AP_BattMonitor event level 与 instance/variant 匹配。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-SHARED-BATT-001-AP-01 — `low_voltage_start`

- 受控自然语言：指定 battery instance 的选定电压源进入低阈值区间。
- 真值条件：selected_voltage(instance)<PARAM_VALUE(BATTx_LOW_VOLT) 的上升沿。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Per-instance selection of raw state.voltage or sag-compensated voltage_resting_estimate.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:243`；symbol `failsafe_voltage_source switch`；kind `FUNCTION`；function `AP_BattMonitor_Backend::check_failsafe_types`；type `float voltage_used`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 243-250 select the voltage source from BATTx_FS_VOLTSRC. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L243
- `Per-instance predicate voltage_used > 0, LOW_VOLT > 0, and voltage_used < LOW_VOLT.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:268`；symbol `low_voltage predicate`；kind `OTHER`；function `AP_BattMonitor_Backend::check_failsafe_types`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 268-272 set low_voltage true or false. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L268
- `Per-backend low-voltage persistence start epoch in autopilot boot milliseconds.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor.h:120`；symbol `BattMonitor_State::low_voltage_start_ms`；kind `FIELD`；function ``；type `uint32_t milliseconds`；role `DEFINITION`；confidence `EXACT`。
  证据：BattMonitor_State also stores instance at line 140 and failsafe level at line 130. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor.h#L120
- `Canonical low_voltage_start edge when the predicate is true and the per-instance timer is unset.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:177`；symbol `_state.low_voltage_start_ms = now`；kind `ASSIGNMENT`；function `AP_BattMonitor_Backend::update_failsafes`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 175-181 start the timer or return Low after persistence. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L177
- `Cancels/resets the low-voltage interval when the predicate becomes false.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:185`；symbol `_state.low_voltage_start_ms = 0`；kind `ASSIGNMENT`；function `AP_BattMonitor_Backend::update_failsafes`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：The reset is in the else branch for low_voltage=false. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L185

MAVLink/观测映射：

- `BATTERY_STATUS.voltages` (ID 147)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Per-instance voltage array; select by id and interpret invalid sentinel. No embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SYS_STATUS.voltage_battery` (ID 1)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Aggregate voltage only; not per-instance and no timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects BATTx_FS_VOLTSRC, BATTx_LOW_VOLT; select voltage source and threshold
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-SHARED-BATT-001-AP-02 — `voltage_threshold_enabled`

- 受控自然语言：该 instance 的低电压阈值启用。
- 真值条件：PARAM_VALUE(BATTx_LOW_VOLT)>0。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Per-instance low-voltage threshold in volts; zero disables.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Params.cpp:117`；symbol `BATTx_LOW_VOLT / AP_BattMonitor_Params::_low_voltage`；kind `PARAMETER`；function ``；type `AP_Float volts`；role `DEFINITION`；confidence `EXACT`。
  证据：AP_GROUPINFO registers LOW_VOLT inside each monitor parameter subgroup; field is Params.h:72. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Params.cpp#L117
- `Direct runtime threshold-enable comparison for this backend instance.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:268`；symbol `_params._low_voltage > 0`；kind `OTHER`；function `AP_BattMonitor_Backend::check_failsafe_types`；type `bool over AP_Float`；role `GUARD`；confidence `EXACT`。
  证据：The threshold must be positive along with a positive selected voltage. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L268
- `Frontend preserves the per-instance parameter/backend identity when checking failsafes.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor.cpp:904`；symbol `for each battery instance`；kind `FUNCTION`；function `AP_BattMonitor::check_failsafes`；type `uint8_t instance index`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 904-909 iterate drivers and invoke the matching backend. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor.cpp#L904

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects BATTx_LOW_VOLT; enabled iff >0; correlate instance by param_id
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-SHARED-BATT-001-AP-03 — `battery_failsafe_event`

- 受控自然语言：该 instance 的 low/critical voltage event 已触发。
- 真值条件：AP_BattMonitor event level 与 instance/variant 匹配。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Per-instance Low severity producer after low voltage persists longer than LOW_TIMER.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:179`；symbol `return AP_BattMonitor::Failsafe::Low`；kind `RETURN`；function `AP_BattMonitor_Backend::update_failsafes`；type `AP_BattMonitor::Failsafe`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 179-181 use strict greater-than and positive LOW_TIMER. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L179
- `Per-instance Critical severity producer after critical voltage persists longer than the same LOW_TIMER.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:162`；symbol `return AP_BattMonitor::Failsafe::Critical`；kind `RETURN`；function `AP_BattMonitor_Backend::update_failsafes`；type `AP_BattMonitor::Failsafe`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 158-164 maintain the independent critical-voltage timer. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L162
- `Frontend consumes the per-instance backend severity and ignores non-increasing severity.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor.cpp:909`；symbol `drivers[i]->update_failsafes()`；kind `FUNCTION`；function `AP_BattMonitor::check_failsafes`；type `AP_BattMonitor::Failsafe`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 909-912 compare the returned enum to state[i].failsafe. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor.cpp#L909
- `Produces a warning text with one-based battery number, low/critical label, voltage, and used capacity.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor.cpp:934`；symbol `Battery instance/severity STATUSTEXT`；kind `MESSAGE_PRODUCER`；function `AP_BattMonitor::check_failsafes`；type `STATUSTEXT text`；role `PRODUCER`；confidence `MAY`。
  证据：Lines 934-935 include instance and severity but no embedded event timestamp or cause subtype. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor.cpp#L934
- `Canonical per-instance monotonic severity-state write, with _has_triggered_failsafe and AP_Notify aggregate mirrors.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor.cpp:940`；symbol `state[i].failsafe = type`；kind `ASSIGNMENT`；function `AP_BattMonitor::check_failsafes`；type `AP_BattMonitor::Failsafe : uint8_t`；role `WRITE`；confidence `EXACT`。
  证据：Lines 936-940 set aggregate flags and the typed per-instance state. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor.cpp#L940
- `Vehicle callback producer for the selected low/critical action when its priority is high enough.` — `baseline/ardupilot/libraries/AP_BattMonitor/AP_BattMonitor.cpp:957`；symbol `_battery_failsafe_handler_fn(type_str, action)`；kind `CALLBACK`；function `AP_BattMonitor::check_failsafes`；type `void(const char*, int8_t)`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 942-958 map action priority and invoke the bound vehicle handler. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor.cpp#L957
- `Outgoing per-instance charge_state derived from state[i].failsafe; Low and Critical map to corresponding MAV_BATTERY_CHARGE_STATE values.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:419`；symbol `BATTERY_STATUS.charge_state producer`；kind `MESSAGE_PRODUCER`；function `GCS_MAVLINK::send_battery_status`；type `MAV_BATTERY_CHARGE_STATE`；role `OBSERVATION_SITE`；confidence `MAY`。
  证据：AP_BattMonitor.cpp:1169-1182 maps the enum; GCS_Common.cpp:408-422 sends BATTERY_STATUS with instance id. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L419

MAVLink/观测映射：

- `BATTERY_STATUS.charge_state` (ID 147)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。May expose a battery charge state per id, but does not prove the exact internal low-voltage path.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `STATUSTEXT.text` (ID 253)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。May report battery failsafe; no timestamp and lossy correlation.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `ARD-SHARED-BATT-001--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-SHARED-BATT-001/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `ARD-SHARED-BATT-001--boundary_first_grid_point_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-SHARED-BATT-001/traces/boundary_first_grid_point_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | boundary_first_grid_point_legal: An open dense-time lower boundary has no least legal instant; T+1 ms is an exact grid witness, not epsilon. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 边界反例 | `ARD-SHARED-BATT-001--boundary_exact_excluded` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-SHARED-BATT-001/traces/boundary_exact_excluded/trace.json)) | `VIOLATED` | `VIOLATED` | boundary_exact_excluded: The response is prohibited through the closed threshold and the eventual interval is open at that threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 边界反例 | `ARD-SHARED-BATT-001--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-SHARED-BATT-001/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-SHARED-BATT-001--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-SHARED-BATT-001/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-SHARED-BATT-001--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-SHARED-BATT-001/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

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
| `monitor` | `PASS` | TAMonitor infinite-prefix status=PASS; trace comparisons={"PASS": 7}. All synthetic infinite-prefix trace verdicts matched the separately recorded TAMonitor expectations. This validates only the encoded formula/test adapter, not the requirement context or firmware. Exact stdout/stderr and result metadata are retained. |
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=MAIN_ONLY version gap; continuous-low reset omitted; selected voltage/event require instrumentation; monitor syntax unsupported. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- MAIN_ONLY 文档未 release-pair。
- strict 'more than' 使用开下界；不引入 epsilon。
- M7 automated independent audit: MAIN_ONLY version gap
- M7 automated independent audit: continuous-low reset omitted
- M7 automated independent audit: selected voltage/event require instrumentation
- M7 automated independent audit: monitor syntax unsupported

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
