# ARD-COPTER-GUID-002 — Copter Guided 指令更新超时

- 系统/车型：ArduPilot / Copter
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-COPTER-GUID-002-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`209e532bc97e5a41966f8c9ab483323c264cae08` / `MAIN_ONLY`
- 位置：`benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/ac2_guidedmode.rst:115-115`
- SHA-256：`fad8514331716f739bf851cd20241d96665ee28028941b7dbc0f980125e6e350`

```text
The :ref:`GUID_TIMEOUT<GUID_TIMEOUT>` parameter holds the timeout (in seconds) when the vehicle is being controlled using attitude, velocity and/or acceleration commands. If no commands are received from the companion computer for this many seconds, the vehicle will slow to a stop (if velocity and/or acceleration commands were being provided) or hold a level hover (if attitude commands were provided). The default setting is 3 seconds.
```

上下文：定义 attitude/velocity/acceleration 指令缺失后的超时与分类型响应。

### ARD-COPTER-GUID-002-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/ArduCopter/Parameters.cpp:866-872`
- SHA-256：`ef28e89a26fe2baa8e9ed55b6c145c79726d6d7805d53e82ad4626da1401a0e6`

```text
// @Param: GUID_TIMEOUT
    // @DisplayName: Guided mode timeout
    // @Description: Guided mode timeout after which vehicle will stop or return to level if no updates are received from caller. Only applicable during any combination of velocity, acceleration, angle control, and/or angular rate control
    // @Units: s
    // @Range: 0.1 5
    // @User: Advanced
    AP_GROUPINFO("GUID_TIMEOUT", 46, ParametersG2, guided_timeout, 3.0),
```

上下文：冻结源码中的 GUID_TIMEOUT 参数说明和范围。

## Requirement IR

- 主体：ArduCopter Guided controller
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：Guided attitude、velocity 或 acceleration 控制期间不再收到相应 caller command。
- 前置：当前为 Guided，并记录本次控制组合。；只对文档列出的 attitude/velocity/acceleration 类命令建模。
- 义务：运行时 GUID_TIMEOUT 到期后，velocity/acceleration 变体开始减速至停止；attitude 变体开始回到水平悬停。
- 禁止：在 GUID_TIMEOUT 到期前不得仅因命令间隔启动该 timeout response。
- 例外：position-only 目标不自动继承 velocity/attitude 的响应语义。；新适用 command 会重置间隔。
- 作用域：最后一个被接受且适用于当前 Guided 控制组合的 command → 新适用 command、离开 Guided 或 run 结束

## 时间与 MITL

- `T_guid`：`T_guid = runtime(GUID_TIMEOUT)`；单位 `s`；下界闭合 `True`。
  起点：last_applicable_guided_command；终点：timeout_response_started；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：vehicle receipt millis; MAVLink sender time_boot_ms is not the anchor。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((guided_gap_start & guided_variant_active) -> (G_[0,T_guid) !timeout_response_started & F_[T_guid,infty) timeout_response_started))`
- 单一具体公式：`G((guided_gap_start & guided_variant_active) -> (G_[0,3) !timeout_response_started & F_[3,infty) timeout_response_started))`
- 形式化状态：`MONITOR_VALIDATED`

- TAMonitor 转换候选：`G((guided_gap_start && guided_variant_active) -> (G[0,3000) (!timeout_response_started) && F[3000,infty) timeout_response_started))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/ArduCopter — quad / `ardupilot-copter-m6` | `3.0 s` | `3.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((guided_gap_start & guided_variant_active) -> (G_[0,3) !timeout_response_started & F_[3,infty) timeout_response_started))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/parameters.json` SHA-256 `f3d4a3e416eb7e01000deec397640cbf291c8b14805073da5b256b88c6de61ab`，index `1204/1387` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-COPTER-GUID-002-AP-01` | 最后一个被接受的适用 command 之后未再接受同类更新。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-COPTER-GUID-002-AP-02` | 当前 Guided 控制组合属于已枚举变体之一。 | `CONDITIONAL` | `BOUND` |
| `ARD-COPTER-GUID-002-AP-03` | velocity/acceleration: 开始零目标/减速；attitude: 开始回水平/零角速率。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-COPTER-GUID-002-AP-01 — `guided_gap_start`

- 受控自然语言：适用 Guided command 的接收间隔开始。
- 真值条件：最后一个被接受的适用 command 之后未再接受同类更新。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Validates Guided mode, type mask, quaternion, body rates, and thrust before calling ModeGuided::set_angle.` — `baseline/ardupilot/ArduCopter/GCS_MAVLink_Copter.cpp:890`；symbol `GCS_MAVLINK_Copter::handle_message_set_attitude_target`；kind `MESSAGE_CONSUMER`；function `GCS_MAVLINK_Copter::handle_message_set_attitude_target`；type `mavlink_set_attitude_target_t`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 890-963 decode and validate the packet; line 962 calls set_angle. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/GCS_MAVLink_Copter.cpp#L890
- `Validates local frame and type mask, then dispatches accepted position/velocity/acceleration combinations.` — `baseline/ardupilot/ArduCopter/GCS_MAVLink_Copter.cpp:966`；symbol `GCS_MAVLINK_Copter::handle_message_set_position_target_local_ned`；kind `MESSAGE_CONSUMER`；function `GCS_MAVLINK_Copter::handle_message_set_position_target_local_ned`；type `mavlink_set_position_target_local_ned_t`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 966-1074 validate; lines 1063-1070 dispatch supported combinations. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/GCS_MAVLink_Copter.cpp#L966
- `Validates global target inputs and dispatches accepted position/velocity/acceleration combinations.` — `baseline/ardupilot/ArduCopter/GCS_MAVLink_Copter.cpp:1077`；symbol `GCS_MAVLINK_Copter::handle_message_set_position_target_global_int`；kind `MESSAGE_CONSUMER`；function `GCS_MAVLINK_Copter::handle_message_set_position_target_global_int`；type `mavlink_set_position_target_global_int_t`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 1077-1173 decode, validate, and dispatch accepted combinations. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/GCS_MAVLink_Copter.cpp#L1077
- `Receipt-clock update for accepted acceleration-only targets.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:569`；symbol `update_time_ms = millis()`；kind `ASSIGNMENT`；function `ModeGuided::set_accel_NED_mss`；type `static uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 554-569 select Accel submode, store targets, and update time. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L569
- `Receipt-clock update for accepted velocity-plus-acceleration targets.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:601`；symbol `update_time_ms = millis()`；kind `ASSIGNMENT`；function `ModeGuided::set_vel_accel_NED_m`；type `static uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 586-601 select VelAccel submode, store targets, and update time. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L601
- `Receipt-clock update for accepted position-velocity-acceleration targets.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:638`；symbol `update_time_ms = millis()`；kind `ASSIGNMENT`；function `ModeGuided::set_pos_vel_accel_NED_m`；type `static uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 617-642 validate/store the combined target and update time. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L638
- `Receipt-clock update for accepted attitude/angular-rate targets.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:704`；symbol `guided_angle_state.update_time_ms = millis()`；kind `ASSIGNMENT`；function `ModeGuided::set_angle`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 682-704 select Angle submode, store targets, and update the separate angle timestamp. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L704

MAVLink/观测映射：

- `SET_ATTITUDE_TARGET.type_mask` (ID 82)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Attitude/rate Guided input; time_boot_ms belongs to the sender and is not the vehicle receipt clock.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SET_POSITION_TARGET_LOCAL_NED.type_mask` (ID 84)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Local position/velocity/acceleration input; acceptance depends on mask/frame/mode.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SET_POSITION_TARGET_GLOBAL_INT.type_mask` (ID 86)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Global position/velocity/acceleration input; acceptance depends on mask/frame/mode.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-GUID-002-AP-02 — `guided_variant_active`

- 受控自然语言：记录 velocity/acceleration 或 attitude/rate 变体。
- 真值条件：当前 Guided 控制组合属于已枚举变体之一。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Internal enum for TakeOff, WP, Pos, PosVelAccel, VelAccel, Accel, and Angle controllers.` — `baseline/ardupilot/ArduCopter/mode.h:1163`；symbol `ModeGuided::SubMode`；kind `FIELD`；function ``；type `enum class ModeGuided::SubMode`；role `DEFINITION`；confidence `EXACT`。
  证据：mode.h:1163-1171 defines the variants; mode.h:1236 stores guided_mode. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode.h#L1163
- `Activates acceleration-only Guided control.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:287`；symbol `guided_mode = SubMode::Accel`；kind `ASSIGNMENT`；function `ModeGuided::accel_control_start`；type `ModeGuided::SubMode`；role `WRITE`；confidence `EXACT`。
  证据：accel_control_start assigns Accel before initializing PVA control. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L287
- `Activates velocity-plus-acceleration Guided control.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:297`；symbol `guided_mode = SubMode::VelAccel`；kind `ASSIGNMENT`；function `ModeGuided::velaccel_control_start`；type `ModeGuided::SubMode`；role `WRITE`；confidence `EXACT`。
  证据：velaccel_control_start assigns VelAccel before initializing PVA control. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L297
- `Activates combined position-velocity-acceleration Guided control.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:307`；symbol `guided_mode = SubMode::PosVelAccel`；kind `ASSIGNMENT`；function `ModeGuided::posvelaccel_control_start`；type `ModeGuided::SubMode`；role `WRITE`；confidence `EXACT`。
  证据：posvelaccel_control_start assigns PosVelAccel before initializing PVA control. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L307
- `Activates attitude and/or angular-rate Guided control.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:346`；symbol `guided_mode = SubMode::Angle`；kind `ASSIGNMENT`；function `ModeGuided::angle_control_start`；type `ModeGuided::SubMode`；role `WRITE`；confidence `EXACT`。
  证据：angle_control_start assigns Angle and initializes its timestamp and targets. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L346

MAVLink/观测映射：

- `SET_ATTITUDE_TARGET.type_mask` (ID 82)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Attitude/rate Guided input; time_boot_ms belongs to the sender and is not the vehicle receipt clock.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SET_POSITION_TARGET_LOCAL_NED.type_mask` (ID 84)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Local position/velocity/acceleration input; acceptance depends on mask/frame/mode.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `SET_POSITION_TARGET_GLOBAL_INT.type_mask` (ID 86)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (sender boot clock)`。Global position/velocity/acceleration input; acceptance depends on mask/frame/mode.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-GUID-002-AP-03 — `timeout_response_started`

- 受控自然语言：对应变体的 timeout response 已启动。
- 真值条件：velocity/acceleration: 开始零目标/减速；attitude: 开始回水平/零角速率。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Converts runtime GUID_TIMEOUT to a minimum 0.1-second timeout in milliseconds.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:1195`；symbol `ModeGuided::get_timeout_ms`；kind `FUNCTION`；function `ModeGuided::get_timeout_ms`；type `uint32_t milliseconds`；role `DERIVATION`；confidence `EXACT`。
  证据：Line 1197 returns MAX(copter.g2.guided_timeout, 0.1) * 1000. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L1195
- `On timeout, zeros velocity and acceleration targets and immediately feeds zero targets to both position-controller axes.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:796`；symbol `Accel timeout response`；kind `ASSIGNMENT`；function `ModeGuided::accel_control_run`；type `Vector3f target reset`；role `WRITE`；confidence `EXACT`。
  证据：Lines 796-803 execute the zero-target response while the strict greater-than guard remains true. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L796
- `On timeout, zeros velocity and acceleration targets and changes rate/angle-rate yaw to hold.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:841`；symbol `tnow - update_time_ms > get_timeout_ms()`；kind `ASSIGNMENT`；function `ModeGuided::velaccel_control_run`；type `Vector3f target reset`；role `WRITE`；confidence `EXACT`。
  证据：Lines 841-846 apply the response. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L841
- `On timeout, zeros velocity and acceleration targets while retaining/adjusting position according to stabilization options.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:926`；symbol `tnow - update_time_ms > get_timeout_ms()`；kind `ASSIGNMENT`；function `ModeGuided::posvelaccel_control_run`；type `Vector3f target reset`；role `WRITE`；confidence `EXACT`。
  证据：Lines 926-931 apply target and yaw response; lines 934-959 feed controller targets. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L926
- `On timeout, commands level roll/pitch with current target yaw, zeros angular velocity and climb rate, and exits direct-thrust mode.` — `baseline/ardupilot/ArduCopter/mode_guided.cpp:984`；symbol `Angle timeout response`；kind `ASSIGNMENT`；function `ModeGuided::angle_control_run`；type `Quaternion/Vector3f/float/bool reset`；role `WRITE`；confidence `EXACT`。
  证据：Lines 984-992 perform the attitude/rate response. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_guided.cpp#L984

MAVLink/观测映射：

- `ATTITUDE_TARGET.type_mask` (ID 83)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (vehicle boot clock)`。Reports current commanded attitude/rates with vehicle boot timestamp; does not identify why targets changed.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `POSITION_TARGET_LOCAL_NED.type_mask` (ID 85)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (vehicle boot clock)`。Reports current position/velocity/acceleration target when streamed; does not expose timeout flag.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `ARD-COPTER-GUID-002--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GUID-002/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `ARD-COPTER-GUID-002--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GUID-002/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 边界反例 | `ARD-COPTER-GUID-002--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GUID-002/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-COPTER-GUID-002--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GUID-002/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-COPTER-GUID-002--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GUID-002/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

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
| `monitor` | `PASS` | TAMonitor infinite-prefix status=PASS; trace comparisons={"PASS": 6}. All synthetic infinite-prefix trace verdicts matched the separately recorded TAMonitor expectations. This validates only the encoded formula/test adapter, not the requirement context or firmware. Exact stdout/stderr and result metadata are retained. |
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=MAIN_ONLY version gap; reset/cancel not represented; internal acceptance/response APs; monitor syntax and trace adapter absent. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- MAIN_ONLY 文档与冻结源码版本关系需人工复核。
- 完成响应无规范上界，因此不把 stopped/level 的完成时刻写入 MITL。
- M7 automated independent audit: MAIN_ONLY version gap
- M7 automated independent audit: reset/cancel not represented
- M7 automated independent audit: internal acceptance/response APs
- M7 automated independent audit: monitor syntax and trace adapter absent

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
