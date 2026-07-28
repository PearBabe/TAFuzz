# ARD-COPTER-GCS-001 — Copter 指定 GCS heartbeat 超时

- 系统/车型：ArduPilot / Copter
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-COPTER-GCS-001-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`209e532bc97e5a41966f8c9ab483323c264cae08` / `MAIN_ONLY`
- 位置：`benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/gcs-failsafe.rst:8-8`
- SHA-256：`b9c449a90cafd6db10844acdb74202a1a510fb82e96d9e94ab82082ff00f4120`

```text
The Ground Station Control (GCS) failsafe controls how Copter will behave if contact with the GCS is lost.  The GCS failsafe monitors the time since the last MAVLink heartbeat from the GCS.  If no heartbeat is received :ref:`FS_GCS_TIMEOUT<FS_GCS_TIMEOUT>` seconds (Default is 5 seconds), the GCS failsafe event will trigger based on your parameter settings. Note that if no GCS is ever connected, the GCS failsafe will remain inactive regardless of parameter settings.
```

上下文：说明 GCS heartbeat 间隔达到 FS_GCS_TIMEOUT 后触发事件，且从未连接时不激活。

### ARD-COPTER-GCS-001-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/ArduCopter/Parameters.cpp:828-835`
- SHA-256：`ef28e89a26fe2baa8e9ed55b6c145c79726d6d7805d53e82ad4626da1401a0e6`

```text
// @Param: FS_GCS_TIMEOUT
    // @DisplayName: GCS failsafe timeout
    // @Description: Timeout before triggering the GCS failsafe
    // @Units: s
    // @Range: 2 120
    // @Increment: 1
    // @User: Standard
    AP_GROUPINFO("FS_GCS_TIMEOUT", 42, ParametersG2, fs_gcs_timeout, 5),
```

上下文：冻结源码中的参数说明、单位、范围和默认值；不作为实现满足证据。

## Requirement IR

- 主体：ArduCopter GCS failsafe
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：此前已收到过指定 GCS 的 MAVLink heartbeat，随后不再收到该 heartbeat。
- 前置：本 run 中指定 GCS 至少有一个 heartbeat 已被飞控收到。；归档的参数设置要求本次 GCS failsafe event 生效；精确 enable/例外规则仍需版本化官方证据。
- 义务：自最后一个指定 GCS heartbeat 起没有收到新 heartbeat 达运行时 FS_GCS_TIMEOUT 后，产生 GCS failsafe event。
- 禁止：在该 heartbeat 缺失区间达到 FS_GCS_TIMEOUT 前，不得仅因该缺失产生 GCS failsafe event。
- 例外：从未连接过 GCS（本 run 从未收到 GCS heartbeat）时，该 failsafe 保持 inactive。
- 作用域：最后一个被飞控收到的指定 GCS MAVLink heartbeat → 下一个指定 GCS heartbeat 或 run 结束；配置变化的取消语义尚未闭合

## 时间与 MITL

- `T_gcs`：`T_gcs = runtime(FS_GCS_TIMEOUT)`；单位 `s`；下界闭合 `True`。
  起点：last_designated_gcs_heartbeat_receipt；终点：gcs_failsafe_event；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：Normative event: designated-GCS heartbeat receipt; current-source exact handler carrier: AP_HAL::millis() at GCS_MAVLINK::handle_heartbeat. The aggregate last-seen timestamp is shared and only MODELLED for this normative event.。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((gcs_heartbeat_gap_start & gcs_heartbeat_seen_before & gcs_fs_enabled) -> (G_[0,T_gcs) !gcs_failsafe_event & F_[T_gcs,infty) gcs_failsafe_event))`
- 单一具体公式：`G((gcs_heartbeat_gap_start & gcs_heartbeat_seen_before & gcs_fs_enabled) -> (G_[0,5) !gcs_failsafe_event & F_[5,infty) gcs_failsafe_event))`
- 形式化状态：`MONITOR_VALIDATED`

- TAMonitor 转换候选：`G((gcs_heartbeat_gap_start && gcs_heartbeat_seen_before && gcs_fs_enabled) -> (G[0,5000) (!gcs_failsafe_event) && F[5000,infty) gcs_failsafe_event))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/ArduCopter — quad / `ardupilot-copter-m6` | `5.0 s` | `5.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((gcs_heartbeat_gap_start & gcs_heartbeat_seen_before & gcs_fs_enabled) -> (G_[0,5) !gcs_failsafe_event & F_[5,infty) gcs_failsafe_event))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/parameters.json` SHA-256 `f3d4a3e416eb7e01000deec397640cbf291c8b14805073da5b256b88c6de61ab`，index `1200/1387` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-COPTER-GCS-001-AP-01` | 最后一个被飞控收到的 designated_gcs_heartbeat 之后，在该连接范围内不再收到新 heartbeat 的边沿事件。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-COPTER-GCS-001-AP-02` | count(designated_gcs_heartbeat_receipt)>0。 | `CONDITIONAL` | `BOUND` |
| `ARD-COPTER-GCS-001-AP-03` | 已归档的参数/模式组合要求本次 GCS failsafe event 生效；精确规则仍需版本化官方证据。 | `DERIVED` | `BOUND` |
| `ARD-COPTER-GCS-001-AP-04` | GCS-specific failsafe state 从 false 变 true。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-COPTER-GCS-001-AP-01 — `gcs_heartbeat_gap_start`

- 受控自然语言：指定 GCS heartbeat 的缺失区间开始。
- 真值条件：最后一个被飞控收到的 designated_gcs_heartbeat 之后，在该连接范围内不再收到新 heartbeat 的边沿事件。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Accepted HEARTBEAT from a configured GCS system ID refreshes designated-GCS last-seen time.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:4357`；symbol `GCS_MAVLINK::handle_heartbeat`；kind `MESSAGE_CONSUMER`；function `GCS_MAVLINK::handle_heartbeat`；type `void(const mavlink_message_t&)`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 4359-4363 test sysid_is_gcs and call sysid_mygcs_seen(AP_HAL::millis()). Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L4357
- `Current implementation conflict: accepted RC_CHANNELS_OVERRIDE refreshes the shared last-seen clock, but it is not a normative designated-GCS heartbeat event.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:4243`；symbol `MAVLINK_MSG_ID_RC_CHANNELS_OVERRIDE -> sysid_mygcs_seen`；kind `MESSAGE_CONSUMER`；function `GCS_MAVLINK::handle_rc_channels_override`；type `mavlink_rc_channels_override_t`；role `CONSUMER`；confidence `MODELLED`。
  证据：After GCS sysid validation and override application, line 4243 calls sysid_mygcs_seen(tnow). This path is retained to expose non-heartbeat interference, not as AP truth. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L4243
- `Current implementation conflict: accepted MANUAL_CONTROL refreshes the shared last-seen clock, but it is not a normative designated-GCS heartbeat event.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:7655`；symbol `MAVLINK_MSG_ID_MANUAL_CONTROL -> sysid_mygcs_seen`；kind `MESSAGE_CONSUMER`；function `GCS_MAVLINK::handle_manual_control`；type `mavlink_manual_control_t`；role `CONSUMER`；confidence `MODELLED`。
  证据：Lines 7638-7647 validate GCS sysid and target; line 7655 records tnow as seen. This path is retained to expose non-heartbeat interference, not as AP truth. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L7655
- `Shared implementation sink for aggregate GCS last-seen timestamps; it is not heartbeat-exclusive and therefore only models the normative heartbeat receipt state.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:7660`；symbol `GCS_MAVLINK::sysid_mygcs_seen`；kind `ASSIGNMENT`；function `GCS_MAVLINK::sysid_mygcs_seen`；type `uint32_t milliseconds`；role `WRITE`；confidence `MODELLED`。
  证据：Lines 7662-7663 write GCS::_sysid_gcs_last_seen_time_ms and GCS_MAVLINK::_sysid_gcs_last_seen_time_ms for heartbeat and non-heartbeat producers. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L7660
- `Elapsed interval since the shared implementation last-seen state; it can model but cannot exactly prove the normative designated-heartbeat gap.` — `baseline/ardupilot/ArduCopter/events.cpp:140`；symbol `last_gcs_update_ms = millis() - gcs_last_seen_ms`；kind `VARIABLE`；function `Copter::failsafe_gcs_check`；type `const uint32_t milliseconds`；role `DERIVATION`；confidence `MODELLED`。
  证据：Lines 133-141 read the aggregate timestamp and derive elapsed time and runtime timeout; the aggregate can include non-heartbeat refreshes. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L140

MAVLink/观测映射：

- `HEARTBEAT` (ID 0)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Harness controls the normative designated-GCS heartbeat input, but HEARTBEAT has no embedded receipt timestamp. The current shared last-seen state is also refreshed by accepted MANUAL_CONTROL/RC_CHANNELS_OVERRIDE; those paths are an implementation conflict, not alternative normative heartbeat events.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-GCS-001-AP-02 — `gcs_heartbeat_seen_before`

- 受控自然语言：本 run 中指定 GCS 之前至少有一个 heartbeat 被飞控收到。
- 真值条件：count(designated_gcs_heartbeat_receipt)>0。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Aggregate current-source last-seen field. It is not heartbeat-exclusive, so nonzero only models designated-heartbeat history.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS.h:1359`；symbol `GCS::_sysid_gcs_last_seen_time_ms`；kind `FIELD`；function ``；type `uint32_t milliseconds`；role `DEFINITION`；confidence `MODELLED`。
  证据：GCS.h lines 1356-1359 define the aggregate field; heartbeat, RC override, and manual-control paths can write it. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS.h#L1359
- `Aggregate implementation sentinel for no shared GCS refresh; it is not an exact sentinel for no designated heartbeat.` — `baseline/ardupilot/ArduCopter/events.cpp:134`；symbol `gcs_last_seen_ms == 0`；kind `OTHER`；function `Copter::failsafe_gcs_check`；type `bool over uint32_t`；role `GUARD`；confidence `MODELLED`。
  证据：Lines 133-136 return when the aggregate last-seen timestamp is zero; non-heartbeat refreshes can make it nonzero. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L134
- `Shared aggregate write sink reached by the normative heartbeat handler and non-normative refresh paths; only a model for heartbeat-seen history.` — `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:7662`；symbol `gcs().sysid_mygcs_seen(seen_time_ms)`；kind `ASSIGNMENT`；function `GCS_MAVLINK::sysid_mygcs_seen`；type `uint32_t milliseconds`；role `WRITE`；confidence `MODELLED`。
  证据：This is the common sink reached by HEARTBEAT, RC_CHANNELS_OVERRIDE, and MANUAL_CONTROL consumers; exact heartbeat history must be separated upstream. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L7662

MAVLink/观测映射：

- `HEARTBEAT` (ID 0)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Harness controls the normative designated-GCS heartbeat input, but HEARTBEAT has no embedded receipt timestamp. The current shared last-seen state is also refreshed by accepted MANUAL_CONTROL/RC_CHANNELS_OVERRIDE; those paths are an implementation conflict, not alternative normative heartbeat events.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-GCS-001-AP-03 — `gcs_fs_enabled`

- 受控自然语言：GCS failsafe 对当前归档配置生效。
- 真值条件：已归档的参数/模式组合要求本次 GCS failsafe event 生效；精确规则仍需版本化官方证据。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DERIVED`；绑定状态：`BOUND`

源码绑定：

- `Runtime enum selecting disabled or a GCS failsafe response class.` — `baseline/ardupilot/ArduCopter/Parameters.cpp:102`；symbol `FS_GCS_ENABLE / Parameters::failsafe_gcs`；kind `PARAMETER`；function ``；type `AP_Enum<Parameters::FS_GCS_Action>`；role `DEFINITION`；confidence `EXACT`。
  证据：GSCALAR registers FS_GCS_ENABLE; enum and field are declared at Parameters.h:407-418. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Parameters.cpp#L102
- `Direct event-enable guard; disabled bypasses GCS failsafe evaluation.` — `baseline/ardupilot/ArduCopter/events.cpp:129`；symbol `g.failsafe_gcs == FS_GCS_Action::DISABLED`；kind `OTHER`；function `Copter::failsafe_gcs_check`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 128-135 bypass when disabled or never connected. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L129
- `Bitmask used to allow continuation in landing, Auto, or pilot-controlled modes after a failsafe event.` — `baseline/ardupilot/ArduCopter/Parameters.cpp:787`；symbol `FS_OPTIONS / ParametersG2::fs_options`；kind `PARAMETER`；function ``；type `AP_Int32`；role `DEFINITION`；confidence `EXACT`。
  证据：AP_GROUPINFO registers FS_OPTIONS; option use is at events.cpp:213-226. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Parameters.cpp#L787
- `Maps FS_GCS_ENABLE to the candidate FailsafeAction.` — `baseline/ardupilot/ArduCopter/events.cpp:170`；symbol `switch ((FS_GCS_Action)g.failsafe_gcs)`；kind `FUNCTION`；function `Copter::failsafe_gcs_on_event`；type `FailsafeAction`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 170-195 map enum values to RTL, SmartRTL, Land, Auto land-start, or Brake/Land actions. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L170
- `Armed, ground, landing, Auto, pilot-control, battery-failsafe, and FS_OPTIONS state can replace or suppress the selected response.` — `baseline/ardupilot/ArduCopter/events.cpp:197`；symbol `GCS failsafe response deviation conditions`；kind `FUNCTION`；function `Copter::failsafe_gcs_on_event`；type `FailsafeAction`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 197-232 derive the final desired_action and call do_failsafe_action. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L197

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects FS_GCS_ENABLE, FS_OPTIONS, MAV_GCS_SYSID(_HI); combine with target HEARTBEAT mode/armed state
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Decode current vehicle mode and system identity. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-GCS-001-AP-04 — `gcs_failsafe_event`

- 受控自然语言：飞控将 GCS failsafe event 标为 active。
- 真值条件：GCS-specific failsafe state 从 false 变 true。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Detects elapsed time above timeout while the GCS failsafe flag is false and initiates the event.` — `baseline/ardupilot/ArduCopter/events.cpp:155`；symbol `new GCS failsafe branch`；kind `EVENT`；function `Copter::failsafe_gcs_check`；type `bool edge`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 155-158 call set_failsafe_gcs(true) then failsafe_gcs_on_event(). Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L155
- `Canonical vehicle-local GCS failsafe state write.` — `baseline/ardupilot/ArduCopter/AP_State.cpp:75`；symbol `Copter::failsafe.gcs = b`；kind `ASSIGNMENT`；function `Copter::set_failsafe_gcs`；type `uint8_t bit-field interpreted as bool`；role `WRITE`；confidence `EXACT`。
  证据：Copter.h:403 declares the bit; AP_State.cpp:73-79 writes it and its AP_Notify mirror. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/AP_State.cpp#L75
- `Global notification mirror of the vehicle-local GCS failsafe state.` — `baseline/ardupilot/ArduCopter/AP_State.cpp:78`；symbol `AP_Notify::flags.failsafe_gcs = b`；kind `ASSIGNMENT`；function `Copter::set_failsafe_gcs`；type `bool`；role `OBSERVATION_SITE`；confidence `MAY`。
  证据：The mirror is exact for this setter but is a shared notification surface, not the canonical Copter field. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/AP_State.cpp#L78
- `DataFlash log producer for occurrence of the GCS failsafe response handler.` — `baseline/ardupilot/ArduCopter/events.cpp:165`；symbol `LOGGER_WRITE_ERROR(FAILSAFE_GCS, FAILSAFE_OCCURRED)`；kind `MESSAGE_PRODUCER`；function `Copter::failsafe_gcs_on_event`；type `LogErrorSubsystem/LogErrorCode`；role `PRODUCER`；confidence `EXACT`。
  证据：The first operation in failsafe_gcs_on_event records FAILSAFE_GCS/FAILSAFE_OCCURRED. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L165

MAVLink/观测映射：

- `STATUSTEXT.text` (ID 253)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。May contain a GCS failsafe notice; queueing/loss and no timestamp prevent exact event timing.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.system_status` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。MAV_STATE_CRITICAL is not GCS-cause-specific and has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `ARD-COPTER-GCS-001--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GCS-001/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `ARD-COPTER-GCS-001--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GCS-001/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 边界反例 | `ARD-COPTER-GCS-001--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GCS-001/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-COPTER-GCS-001--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GCS-001/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-COPTER-GCS-001--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-GCS-001/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=MAIN_ONLY version gap; enable/cancel context not version-closed; heartbeat reset/cancel omitted from standalone formula; heartbeat-exclusive internal AP observation absent; presentation formula requires the recorded deterministic monitor-syntax transform. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- ArduPilot wiki 为 MAIN_ONLY，未与冻结固件 release 配对。
- 当前实现的 aggregate last-seen 可由非 heartbeat 消息刷新；该实现行为只作 MODELLED binding/conflict。
- FS_GCS_ENABLE 的旧参数文案写死 5s；该性质只使用运行时 FS_GCS_TIMEOUT。
- M7 automated independent audit: MAIN_ONLY version gap
- M7 automated independent audit: enable/cancel context not version-closed
- M7 automated independent audit: heartbeat reset/cancel omitted from standalone formula
- M7 automated independent audit: heartbeat-exclusive internal AP observation absent
- M7 automated independent audit: presentation formula requires the recorded deterministic monitor-syntax transform

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
