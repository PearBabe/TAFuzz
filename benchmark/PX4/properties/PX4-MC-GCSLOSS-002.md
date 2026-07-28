# PX4-MC-GCSLOSS-002 — PX4 GCS data-link loss

- 系统/车型：PX4 / multicopter SITL
- 固件提交：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### PX4-MC-GCSLOSS-002-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`v1.17.0` / `RELEASE_PINNED`
- 位置：`baseline/px4/docs/en/config/safety.md:136-153`
- SHA-256：`82b627ef4c4d323ef5e524c5630903c31570e103a9701b65a5f4b8fb33ee4db3`

```text
## Data Link Loss Failsafe

The Data Link Loss failsafe is triggered if a telemetry link (connection to ground station) is lost.

![Safety - Data Link Loss (QGC)](../../assets/qgc/setup/safety/safety_data_link_loss.png)

The settings and underlying parameters are shown below.

| Setting                | Parameter                                                                | Description                                                                       |
| ---------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| Data Link Loss Timeout | [COM_DL_LOSS_T](../advanced_config/parameter_reference.md#COM_DL_LOSS_T) | Amount of time after losing the data connection before the failsafe will trigger. |
| Failsafe Action        | [NAV_DLL_ACT](../advanced_config/parameter_reference.md#NAV_DLL_ACT)     | Disabled, Hold mode, Return mode, Land mode, Disarm, Terminate.                   |

The following settings also apply, but are not displayed in the QGC UI.

| Setting                                                     | Parameter                                                                  | Description                                          |
| ----------------------------------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------- |
| <a id="COM_DLL_EXCEPT"></a>Mode exceptions for DLL failsafe | [COM_DLL_EXCEPT](../advanced_config/parameter_reference.md#COM_DLL_EXCEPT) | Set modes where DL loss will not trigger a failsafe. |
```

上下文：定义 telemetry/GCS data-link loss、COM_DL_LOSS_T 和模式例外。

### PX4-MC-GCSLOSS-002-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` / `RELEASE_PINNED`
- 位置：`baseline/px4/src/modules/commander/commander_params.c:86-98`
- SHA-256：`4e83db4e821aac5fb5ad96aa7755bac8dffac0714581d0895688198c8e41902a`

```text
/**
 * GCS connection loss time threshold
 *
 * After this amount of seconds without datalink, the GCS connection lost mode triggers
 *
 * @group Commander
 * @unit s
 * @min 5
 * @max 300
 * @decimal 1
 * @increment 1
 */
PARAM_DEFINE_INT32(COM_DL_LOSS_T, 10);
```

上下文：冻结提交中的参数单位、范围和默认值。

## Requirement IR

- 主体：PX4 data-link-loss failsafe
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：与地面站的 telemetry link/data connection 进入 lost/unavailable 状态。
- 前置：与地面站的 telemetry/data connection 此前已建立。；NAV_DLL_ACT 未禁用该 failsafe，且 COM_DLL_EXCEPT 未将当前模式列为例外。；官方来源未定义该 connection 的精确 liveness predicate、关联键或事件载体；当前仍为待补证前置。
- 义务：自 telemetry/data connection 丢失起达到运行时 COM_DL_LOSS_T 后，Data Link Loss failsafe 触发。
- 禁止：在该 data connection loss 持续达到 COM_DL_LOSS_T 前，不得仅因该 loss 触发 Data Link Loss failsafe。
- 例外：已配置的 COM_DLL_EXCEPT 模式不触发该 failsafe。；NAV_DLL_ACT=Disabled 时不要求执行 failsafe action。
- 作用域：官方来源定义的 telemetry/data connection loss 开始 → 官方来源定义的 connection 恢复、配置例外/取消或 run 结束

## 时间与 MITL

- `T_dl_loss`：`T_dl_loss = runtime(COM_DL_LOSS_T)`；单位 `s`；下界闭合 `True`。
  起点：telemetry_data_link_loss_start；终点：gcs_connection_lost；时钟：`UNKNOWN`；载体：Official sources do not define a liveness-event timestamp carrier or clock. The current PX4 MAV_TYPE_GCS heartbeat/HRT flow is retained only as a MODELLED implementation candidate.。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((data_link_loss_gap_start & dl_loss_applicable) -> (G_[0,T_dl_loss) !gcs_connection_lost & F_[T_dl_loss,infty) gcs_connection_lost))`
- 单一具体公式：`G((data_link_loss_gap_start & dl_loss_applicable) -> (G_[0,10) !gcs_connection_lost & F_[10,infty) gcs_connection_lost))`
- 形式化状态：`MONITOR_VALIDATED`

- TAMonitor 转换候选：`G((data_link_loss_gap_start && dl_loss_applicable) -> (G[0,10000) (!gcs_connection_lost) && F[10000,infty) gcs_connection_lost))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| PX4/multicopter — px4_sitl_default sihsim_quadx internal headless SIH instance 42 / `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` | `10 s` | `10.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((data_link_loss_gap_start & dl_loss_applicable) -> (G_[0,10) !gcs_connection_lost & F_[10,infty) gcs_connection_lost))` | `benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json` SHA-256 `42d4fae5d576488a3584526c725330411f03dc438df24db7ab7ad7bdeb61af44`，index `260/900` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `PX4-MC-GCSLOSS-002-AP-01` | 与地面站的 source-defined telemetry/data connection 从 available 变为 lost/unavailable；精确 liveness predicate、关联键和时钟尚未解析。 | `UNRESOLVED` | `PARTIALLY_BOUND` |
| `PX4-MC-GCSLOSS-002-AP-02` | NAV_DLL_ACT、COM_DLL_EXCEPT 和 current mode 的组合允许检查。 | `DERIVED` | `BOUND` |
| `PX4-MC-GCSLOSS-002-AP-03` | gcs_connection_lost 从 false 变 true；该字段是对官方 failsafe-trigger 结果的当前源码映射，不反向定义规范输入。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### PX4-MC-GCSLOSS-002-AP-01 — `data_link_loss_gap_start`

- 受控自然语言：官方来源所指 telemetry/data connection 的丢失区间开始。
- 真值条件：与地面站的 source-defined telemetry/data connection 从 available 变为 lost/unavailable；精确 liveness predicate、关联键和时钟尚未解析。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`UNRESOLVED`；绑定状态：`PARTIALLY_BOUND`

源码绑定：

- `Current implementation candidate HEARTBEAT consumer; the official source does not establish equivalence to the normative telemetry/data-connection liveness event.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:2142`；symbol `MavlinkReceiver::handle_message_heartbeat`；kind `MESSAGE_CONSUMER`；function `MavlinkReceiver::handle_message_heartbeat`；type `void(mavlink_message_t *)`；role `CONSUMER`；confidence `MODELLED`。
  证据：This handler decodes incoming HEARTBEAT and classifies GCS type. It locates the current realization only and is not normative evidence. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L2142
- `Current implementation heartbeat-classification guard; it does not define general telemetry/data-connection availability.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:2154`；symbol `MAV_TYPE_GCS`；kind `OTHER`；function `MavlinkReceiver::handle_message_heartbeat`；type `bool expression`；role `GUARD`；confidence `MODELLED`。
  证据：The source accepts MAV_TYPE_GCS independent of same_system and retains no normative connection identity; official docs do not make this the liveness predicate. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L2154
- `Current implementation HRT epoch for an accepted GCS heartbeat; only a MODELLED candidate for the unresolved normative connection event.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:2164`；symbol `_heartbeat_type_gcs`；kind `ASSIGNMENT`；function `MavlinkReceiver::handle_message_heartbeat`；type `hrt_abstime`；role `WRITE`；confidence `MODELLED`。
  证据：The handler stores current hrt time for an accepted GCS heartbeat, but official data-link-loss sources do not identify this as the normative start carrier. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L2164
- `Current implementation heartbeat-freshness projection; not an official definition of telemetry/data-connection availability.` — `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:2923`；symbol `heartbeat_type_gcs`；kind `ASSIGNMENT`；function `MavlinkReceiver::CheckHeartbeats`；type `bool`；role `DERIVATION`；confidence `MODELLED`。
  证据：This is a 2.5-second heartbeat freshness projection, not a source-defined data-connection liveness event. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L2923
- `Current implementation uORB heartbeat-freshness field; only a candidate projection for the unresolved normative data-link predicate.` — `baseline/px4/msg/TelemetryStatus.msg:42`；symbol `heartbeat_type_gcs`；kind `FIELD`；function ``；type `bool`；role `DEFINITION`；confidence `MODELLED`。
  证据：The message field carries per-link heartbeat freshness. No selected official source equates it with all telemetry/data-connection liveness. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/TelemetryStatus.msg#L42
- `Commander copies telemetry_status publication time while heartbeat_type_gcs remains true.` — `baseline/px4/src/modules/commander/Commander.cpp:2792`；symbol `_datalink_last_heartbeat_gcs`；kind `ASSIGNMENT`；function `Commander::dataLinkCheck`；type `hrt_abstime`；role `WRITE`；confidence `MODELLED`。
  证据：telemetry.timestamp is later than the underlying receipt epoch and can refresh during the 2.5-second receiver freshness window. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2792

MAVLink/观测映射：

- `HEARTBEAT.type` (ID 0)，方向 `INCOMING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Harness can exercise the current PX4 MAV_TYPE_GCS-heartbeat realization, but the official v1.17 source does not equate that flow with the normative telemetry/data-connection liveness event. HEARTBEAT has no embedded receipt timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-GCSLOSS-002-AP-02 — `dl_loss_applicable`

- 受控自然语言：data-link loss 对当前模式/配置生效。
- 真值条件：NAV_DLL_ACT、COM_DLL_EXCEPT 和 current mode 的组合允许检查。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DERIVED`；绑定状态：`BOUND`

源码绑定：

- `Runtime GCS data-link-loss action parameter, including disabled.` — `baseline/px4/src/modules/commander/commander_params.c:598`；symbol `NAV_DLL_ACT`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：The frozen source defines parameter identity and default; campaign capture supplies the runtime value. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L598
- `Runtime data-link-loss mode-exception bitmask.` — `baseline/px4/src/modules/commander/commander_params.c:647`；symbol `COM_DLL_EXCEPT`；kind `PARAMETER`；function ``；type `int32`；role `DEFINITION`；confidence `EXACT`。
  证据：The parameter is one input to applicability. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/commander_params.c#L647
- `Current intended navigation mode consumed by the data-link exception derivation.` — `baseline/px4/src/modules/commander/failsafe/framework.h:128`；symbol `user_intended_mode`；kind `FIELD`；function `FailsafeBase::update`；type `uint8_t`；role `READ`；confidence `EXACT`。
  证据：Mode is combined with exception bits and implementation-specific ignore states. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/framework.h#L128
- `Implementation aggregate for GCS-loss ignore conditions.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:512`；symbol `dll_loss_ignored`；kind `VARIABLE`；function `Failsafe::update`；type `const bool`；role `DERIVATION`；confidence `MODELLED`。
  证据：The aggregate covers mission, hold, offboard, takeoff, VTOL-takeoff, and unconditional land/precland handling. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L512
- `Implementation guard requiring NAV_DLL_ACT to be enabled and no ignore predicate to hold.` — `baseline/px4/src/modules/commander/failsafe/failsafe.cpp:515`；symbol `_param_nav_dll_act`；kind `OTHER`；function `Failsafe::update`；type `bool expression`；role `GUARD`；confidence `MODELLED`。
  证据：The guard locates the implementation decision but does not redefine the normalized official AP. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/failsafe/failsafe.cpp#L515

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects NAV_DLL_ACT, COM_DLL_EXCEPT; derive configured applicability
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Current mode. HEARTBEAT has no embedded timestamp.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### PX4-MC-GCSLOSS-002-AP-03 — `gcs_connection_lost`

- 受控自然语言：Data Link Loss failsafe 触发时的当前源码内部 GCS-connection-lost 事件。
- 真值条件：gcs_connection_lost 从 false 变 true；该字段是对官方 failsafe-trigger 结果的当前源码映射，不反向定义规范输入。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `VehicleStatus boolean whose false-to-true transition is the normalized AP.` — `baseline/px4/msg/versioned/VehicleStatus.msg:106`；symbol `gcs_connection_lost`；kind `FIELD`；function ``；type `bool`；role `DEFINITION`；confidence `EXACT`。
  证据：The field explicitly represents lost data link to GCS. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L106
- `Commander timeout guard using COM_DL_LOSS_T against its last-GCS time state.` — `baseline/px4/src/modules/commander/Commander.cpp:2849`；symbol `_datalink_last_heartbeat_gcs`；kind `OTHER`；function `Commander::dataLinkCheck`；type `bool expression`；role `GUARD`；confidence `EXACT`。
  证据：The guard identifies the internal transition site. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2849
- `Assignment marking VehicleStatus GCS connection lost true.` — `baseline/px4/src/modules/commander/Commander.cpp:2851`；symbol `gcs_connection_lost`；kind `ASSIGNMENT`；function `Commander::dataLinkCheck`；type `bool`；role `WRITE`；confidence `EXACT`。
  证据：This is the direct true write for the AP. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2851
- `Named event emitted when Commander enters the GCS-lost state.` — `baseline/px4/src/modules/commander/Commander.cpp:2855`；symbol `commander_gcs_lost`；kind `EVENT`；function `Commander::dataLinkCheck`；type `events::ID`；role `PRODUCER`；confidence `EXACT`。
  证据：The event is colocated with the flag transition and counter increment. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L2855
- `uORB producer for VehicleStatus, including gcs_connection_lost and a vehicle timestamp.` — `baseline/px4/src/modules/commander/Commander.cpp:1945`；symbol `_vehicle_status_pub.publish`；kind `MESSAGE_PRODUCER`；function `Commander::Run`；type `uORB::Publication<vehicle_status_s>`；role `PRODUCER`；confidence `EXACT`。
  证据：Internal instrumentation can observe the state transition on vehicle_status. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/Commander.cpp#L1945
- `MAVLink EVENT ID field populated from the PX4 event identity.` — `baseline/px4/src/modules/mavlink/mavlink_events.cpp:216`；symbol `event_msg.id`；kind `ASSIGNMENT`；function `SendProtocol::send_event`；type `uint32_t`；role `WRITE`；confidence `EXACT`。
  证据：The generic EVENT producer preserves the named event ID. Fixed permalink: https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_events.cpp#L216

MAVLink/观测映射：

- `EVENT.id` (ID 410)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `event_time_boot_ms (PX4 system boot clock)`。May carry GCS/data-link lost event. Requires firmware-matched component metadata to decode id/arguments.
  证据：baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `PX4-MC-GCSLOSS-002--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-GCSLOSS-002/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `PX4-MC-GCSLOSS-002--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-GCSLOSS-002/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 边界反例 | `PX4-MC-GCSLOSS-002--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-GCSLOSS-002/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `PX4-MC-GCSLOSS-002--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-GCSLOSS-002/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `PX4-MC-GCSLOSS-002--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/PX4-MC-GCSLOSS-002/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=official data-link liveness predicate/correlation/clock unresolved; gap reset/cancel omitted; heartbeat-only source bindings are MODELLED; exact event observation absent; monitor syntax unsupported. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- 官方 data-link loss 事件的 liveness predicate/时钟未解析；HEARTBEAT 及 GCS host arrival time 不能自动替代。
- M7 automated independent audit: official data-link liveness predicate/correlation/clock unresolved
- M7 automated independent audit: gap reset/cancel omitted
- M7 automated independent audit: heartbeat-only source bindings are MODELLED
- M7 automated independent audit: exact event observation absent
- M7 automated independent audit: monitor syntax unsupported

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
