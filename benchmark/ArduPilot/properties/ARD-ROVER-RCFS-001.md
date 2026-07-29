# ARD-ROVER-RCFS-001 — Rover 低油门持续触发 failsafe

- 系统/车型：ArduPilot / Rover
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-ROVER-RCFS-001-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`209e532bc97e5a41966f8c9ab483323c264cae08` / `MAIN_ONLY`
- 位置：`benchmark/extraction_runs/corpus_sources/ardupilot_wiki/rover/source/docs/rover-failsafes.rst:15-22`
- SHA-256：`f68a1c10ab43b3f831d2600a4233d3bc1e1cec6326bcdc57b03baf3c8afd1576`

```text
This failsafe is triggered if the connection between the user's transmitter and the receiver on the vehicle is lost for at least :ref:`FS_TIMEOUT <FS_TIMEOUT>` seconds (default = 1 sec).

- the loss of transmitter/receiver connection is detected by:

  - no signals being sent from the receiver to the autopilot board OR
  - the throttle channel (normally input channel 3) value falling below the :ref:`FS_THR_VALUE <FS_THR_VALUE>` parameter value OR
  - RC_OVERRIDES are lost if :ref:`using a GCS only <common-gcs-only-operation>` is being used,
```

上下文：列出连接丢失、低油门和 RC override 丢失三种来源及持续时间。

### ARD-ROVER-RCFS-001-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/Rover/Parameters.cpp:100-122`
- SHA-256：`84ffa3f20ff0acb1f1125a66b272e64fb82c6cc50b103688b996e15ca5ef462f`

```text
// @Param: FS_TIMEOUT
    // @DisplayName: Failsafe timeout
    // @Description: The time in seconds that a failsafe condition must persist before the failsafe action is triggered
    // @Units: s
    // @Range: 1 100
    // @Increment: 0.5
    // @User: Standard
    GSCALAR(fs_timeout,    "FS_TIMEOUT",     1.5),

    // @Param: FS_THR_ENABLE
    // @DisplayName: Throttle Failsafe Enable
    // @Description: The throttle failsafe allows you to configure a software failsafe activated by a setting on the throttle input channel to a low value. This can be used to detect the RC transmitter going out of range. Failsafe will be triggered when the throttle channel goes below the FS_THR_VALUE for FS_TIMEOUT seconds.
    // @Values: 0:Disabled,1:Enabled,2:Enabled Continue with Mission in Auto
    // @User: Standard
    GSCALAR(fs_throttle_enabled,    "FS_THR_ENABLE",     FS_THR_ENABLED),

    // @Param: FS_THR_VALUE
    // @DisplayName: Throttle Failsafe Value
    // @Description: The PWM level on the throttle channel below which throttle failsafe triggers.
    // @Range: 910 1100
    // @Increment: 1
    // @User: Standard
    GSCALAR(fs_throttle_value,      "FS_THR_VALUE",     910),
```

上下文：冻结源码中 FS_TIMEOUT、FS_THR_ENABLE 和 FS_THR_VALUE 的参数语义。

## Requirement IR

- 主体：ArduRover radio/throttle failsafe
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：有效 RC throttle channel 持续低于运行时 FS_THR_VALUE。
- 前置：FS_THR_ENABLE 对当前模式生效。；持续发送有效 RC frame，以隔离独立的 RC_FS_TIMEOUT 路径。；throttle channel 由运行时 RCMAP_THROTTLE 决定。
- 义务：条件持续运行时 FS_TIMEOUT 后触发配置的 failsafe action。
- 禁止：在 FS_TIMEOUT 结束前不得仅由该低 PWM 条件触发 action。
- 例外：低值条件中断会重置持续时间。；FS_THR_ENABLE 的 Auto 例外配置必须尊重。
- 作用域：有效 throttle PWM 首次低于 FS_THR_VALUE → PWM 恢复、frame 无效、failsafe 禁用、action 或 run 结束

## 时间与 MITL

- `T_rover_fs`：`T_rover_fs = runtime(FS_TIMEOUT)`；单位 `s`；下界闭合 `True`。
  起点：low_throttle_interval_start；终点：configured_failsafe_action；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：vehicle millis for failsafe condition。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((low_throttle_start & valid_rc_frames & throttle_fs_enabled) -> (G_[0,T_rover_fs) !configured_failsafe_action & F_[T_rover_fs,infty) configured_failsafe_action))`
- 单一具体公式：`G((low_throttle_start & valid_rc_frames & throttle_fs_enabled) -> (G_[0,1.5) !configured_failsafe_action & F_[1.5,infty) configured_failsafe_action))`
- 形式化状态：`MONITOR_VALIDATED`

- TAMonitor 转换候选：`G((low_throttle_start && valid_rc_frames && throttle_fs_enabled) -> (G[0,1500) (!configured_failsafe_action) && F[1500,infty) configured_failsafe_action))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/Rover — rover / `ardupilot-rover-m6` | `1.5 s` | `1.5 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((low_throttle_start & valid_rc_frames & throttle_fs_enabled) -> (G_[0,1.5) !configured_failsafe_action & F_[1.5,infty) configured_failsafe_action))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Rover/parameters.json` SHA-256 `ed4de8b303095cf19449c9e6181678863cf25ba3eee8ff47ae5bf683e432fd79`，index `11/1271` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-ROVER-RCFS-001-AP-01` | valid RC frame 且 chan[RCMAP_THROTTLE] < PARAM_VALUE(FS_THR_VALUE) 的上升沿。 | `CONDITIONAL` | `BOUND` |
| `ARD-ROVER-RCFS-001-AP-02` | 每个 freshness 窗口内存在被接收器接受的 RC frame。 | `CONDITIONAL` | `BOUND` |
| `ARD-ROVER-RCFS-001-AP-03` | 运行时 FS_THR_ENABLE 和模式不属于例外。 | `DERIVED` | `BOUND` |
| `ARD-ROVER-RCFS-001-AP-04` | 运行时 FS_ACTION 映射到的结果 mode/action 成立，并与本次低油门 event 关联。 | `CONDITIONAL` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-ROVER-RCFS-001-AP-01 — `low_throttle_start`

- 受控自然语言：映射后的 throttle PWM 进入低于阈值的连续区间。
- 真值条件：valid RC frame 且 chan[RCMAP_THROTTLE] < PARAM_VALUE(FS_THR_VALUE) 的上升沿。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Resolves the runtime RCMAP_THROTTLE channel to the Rover throttle input object.` — `baseline/ardupilot/Rover/radio.cpp:11`；symbol `channel_throttle = &rc().get_throttle_channel()`；kind `ASSIGNMENT`；function `Rover::set_control_channels`；type `RC_Channel*`；role `WRITE`；confidence `EXACT`。
  证据：RC_Channels::get_throttle_channel maps AP::rcmap()->throttle() at RC_Channels.cpp:418-424. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/radio.cpp#L11
- `Consumes mapped raw PWM after read_input returned true and last_valid_rc_ms was refreshed.` — `baseline/ardupilot/Rover/radio.cpp:74`；symbol `radio_failsafe_check(channel_throttle->get_radio_in())`；kind `FUNCTION`；function `Rover::read_radio`；type `uint16_t PWM`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 66-75 separate unsuccessful and successful input cycles. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/radio.cpp#L74
- `Direct low-throttle comparison against runtime FS_THR_VALUE.` — `baseline/ardupilot/Rover/radio.cpp:85`；symbol `failed = pwm < g.fs_throttle_value`；kind `OTHER`；function `Rover::radio_failsafe_check`；type `bool over uint16_t/AP_Int16`；role `DERIVATION`；confidence `EXACT`。
  证据：Line 85 initializes failed from the low-PWM predicate; lines 86-89 can also force it for stale input. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/radio.cpp#L85
- `Shared failsafe interval epoch when the first active failsafe bit begins.` — `baseline/ardupilot/Rover/failsafe.cpp:55`；symbol `failsafe.bits 0 -> nonzero; failsafe.start_time = millis()`；kind `EVENT`；function `Rover::failsafe_trigger`；type `uint8_t bitmask and uint32_t milliseconds`；role `PRODUCER`；confidence `MODELLED`。
  证据：Lines 49-58 update bits and initialize start_time only when the aggregate mask transitions from zero. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/failsafe.cpp#L55

MAVLink/观测映射：

- `RC_CHANNELS.chan3_raw` (ID 65)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (vehicle boot clock)`。Use chanN_raw where N=runtime(RCMAP_THROTTLE), not hard-coded channel 3; time_boot_ms is vehicle boot time.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects RCMAP_THROTTLE, FS_THR_VALUE; select chanN_raw and threshold
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-ROVER-RCFS-001-AP-02 — `valid_rc_frames`

- 受控自然语言：低 PWM 区间内仍持续有有效 RC frame。
- 真值条件：每个 freshness 窗口内存在被接收器接受的 RC frame。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Returns true when new receiver input or new overrides produce at least one channel update.` — `baseline/ardupilot/libraries/RC_Channel/RC_Channels.cpp:89`；symbol `RC_Channels::read_input`；kind `FUNCTION`；function `RC_Channels::read_input`；type `bool()`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 91-100 accept receiver input or has_new_overrides; lines 104-119 update channels and return success. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/RC_Channel/RC_Channels.cpp#L89
- `Vehicle receipt-clock timestamp of the most recent successful RC input update.` — `baseline/ardupilot/Rover/radio.cpp:72`；symbol `failsafe.last_valid_rc_ms = AP_HAL::millis()`；kind `ASSIGNMENT`；function `Rover::read_radio`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：The write occurs only after rc().read_input() returns true. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/radio.cpp#L72
- `Current-source freshness predicate used to classify RC input as stale.` — `baseline/ardupilot/Rover/radio.cpp:86`；symbol `millis() - last_valid_rc_ms > rc().get_fs_timeout_ms()`；kind `OTHER`；function `Rover::radio_failsafe_check`；type `bool over uint32_t milliseconds`；role `GUARD`；confidence `EXACT`。
  证据：Lines 86-89 force failed=true after the runtime RC freshness timeout. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/radio.cpp#L86

MAVLink/观测映射：

- `RC_CHANNELS.chan3_raw` (ID 65)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (vehicle boot clock)`。Use chanN_raw where N=runtime(RCMAP_THROTTLE), not hard-coded channel 3; time_boot_ms is vehicle boot time.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-ROVER-RCFS-001-AP-03 — `throttle_fs_enabled`

- 受控自然语言：throttle failsafe 对当前模式生效。
- 真值条件：运行时 FS_THR_ENABLE 和模式不属于例外。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DERIVED`；绑定状态：`BOUND`

源码绑定：

- `Runtime throttle-failsafe mode: disabled, enabled, or enabled-continue-mission-in-Auto.` — `baseline/ardupilot/Rover/Parameters.cpp:114`；symbol `FS_THR_ENABLE / Parameters::fs_throttle_enabled`；kind `PARAMETER`；function ``；type `AP_Int8 / enum fs_thr_enable`；role `DEFINITION`；confidence `EXACT`。
  证据：GSCALAR registers the parameter; enum values are Rover/defines.h:55-60. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/Parameters.cpp#L114
- `Direct disabled guard; clears AP_Notify radio flag and bypasses throttle-failsafe evaluation.` — `baseline/ardupilot/Rover/radio.cpp:79`；symbol `!g.fs_throttle_enabled`；kind `OTHER`；function `Rover::radio_failsafe_check`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 79-83 return when FS_THR_ENABLE is zero. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/radio.cpp#L79
- `Action is delayed by FS_TIMEOUT and suppressed in RTL and normally in Hold.` — `baseline/ardupilot/Rover/failsafe.cpp:70`；symbol `failsafe.triggered == 0 && failsafe.bits != 0`；kind `OTHER`；function `Rover::failsafe_trigger`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 70-75 require no prior trigger, active bits, elapsed FS_TIMEOUT, non-RTL mode, and Hold option if in Hold. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/failsafe.cpp#L70
- `When in Auto with FS_THR_ENABLE=2, records the failsafe but continues the mission rather than applying FS_ACTION.` — `baseline/ardupilot/Rover/failsafe.cpp:81`；symbol `FS_THR_ENABLED_CONTINUE_MISSION Auto exception`；kind `OTHER`；function `Rover::failsafe_trigger`；type `bool`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 81-86 implement the continue-mission exception. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/failsafe.cpp#L81

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects FS_THR_ENABLE; combine with mode exceptions
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Current mode only. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-ROVER-RCFS-001-AP-04 — `configured_failsafe_action`

- 受控自然语言：FS_ACTION 对应的 action 已发生。
- 真值条件：运行时 FS_ACTION 映射到的结果 mode/action 成立，并与本次低油门 event 关联。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Runtime enum selecting None, RTL, Hold, SmartRTL, Terminate, or Loiter/Hold fallback.` — `baseline/ardupilot/Rover/Parameters.cpp:98`；symbol `FS_ACTION / Parameters::fs_action`；kind `PARAMETER`；function ``；type `AP_Int8 / Rover::FailsafeAction`；role `DEFINITION`；confidence `EXACT`。
  证据：GSCALAR registers FS_ACTION; enum is Rover.h:404-412. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/Parameters.cpp#L98
- `Latches all currently active failsafe bits when the shared persistence timeout expires.` — `baseline/ardupilot/Rover/failsafe.cpp:75`；symbol `failsafe.triggered = failsafe.bits`；kind `ASSIGNMENT`；function `Rover::failsafe_trigger`；type `uint8_t bitmask`；role `WRITE`；confidence `EXACT`。
  证据：Line 76 also produces a warning STATUSTEXT with the caller type string. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/failsafe.cpp#L75
- `Maps runtime FS_ACTION to None, mode transitions with fallbacks, or disarm.` — `baseline/ardupilot/Rover/failsafe.cpp:87`；symbol `switch ((FailsafeAction)g.fs_action.get())`；kind `FUNCTION`；function `Rover::failsafe_trigger`；type `Rover::FailsafeAction`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 87-116 implement every action and fallback. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/failsafe.cpp#L87
- `Canonical successful Rover mode-result write for RTL/Hold/SmartRTL/Loiter actions.` — `baseline/ardupilot/Rover/system.cpp:269`；symbol `control_mode = &new_mode`；kind `ASSIGNMENT`；function `Rover::set_mode`；type `Mode*`；role `WRITE`；confidence `EXACT`。
  证据：On successful entry, lines 269 and 284 write the mode and ModeReason; line 288 queues HEARTBEAT. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/system.cpp#L269
- `Terminate action result with cause-specific disarm method.` — `baseline/ardupilot/Rover/failsafe.cpp:114`；symbol `arming.disarm(AP_Arming::Method::FAILSAFE_ACTION_TERMINATE)`；kind `FUNCTION`；function `Rover::failsafe_trigger`；type `AP_Arming::Method`；role `PRODUCER`；confidence `EXACT`。
  证据：FailsafeAction::Terminate directly requests disarm. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/failsafe.cpp#L114

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects FS_ACTION; maps expected action
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Observe resulting mode. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `STATUSTEXT.text` (ID 253)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。May announce failsafe but has no timestamp/cause-complete guarantee.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `ARD-ROVER-RCFS-001--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-RCFS-001/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `ARD-ROVER-RCFS-001--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-RCFS-001/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 边界反例 | `ARD-ROVER-RCFS-001--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-RCFS-001/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-ROVER-RCFS-001--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-RCFS-001/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-ROVER-RCFS-001--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-RCFS-001/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=MAIN_ONLY version gap; sustained-threshold/reset omitted; conditional MAVLink reconstruction; monitor syntax unsupported. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- ArduPilot wiki MAIN_ONLY 且默认值与冻结源码不一致。
- RC_FS_TIMEOUT 是另一条性质，不与 FS_TIMEOUT 合并。
- M7 automated independent audit: MAIN_ONLY version gap
- M7 automated independent audit: sustained-threshold/reset omitted
- M7 automated independent audit: conditional MAVLink reconstruction
- M7 automated independent audit: monitor syntax unsupported

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
