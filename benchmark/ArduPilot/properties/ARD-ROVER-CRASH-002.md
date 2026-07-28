# ARD-ROVER-CRASH-002 — Rover crash 条件持续时间

- 系统/车型：ArduPilot / Rover
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-ROVER-CRASH-002-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`209e532bc97e5a41966f8c9ab483323c264cae08` / `MAIN_ONLY`
- 位置：`benchmark/extraction_runs/corpus_sources/ardupilot_wiki/rover/source/docs/rover-failsafes.rst:97-106`
- SHA-256：`f68a1c10ab43b3f831d2600a4233d3bc1e1cec6326bcdc57b03baf3c8afd1576`

```text
If enabled by setting the :ref:`FS_CRASH_CHECK <FS_CRASH_CHECK>` parameter to "1" (for :ref:`Hold <hold-mode>`) or "2" (for :ref:`Hold <hold-mode>` and Disarm) this failsafe will switch the vehicle to Hold and then (optionally) disarm the vehicle if all the following are true for at least :ref:`CRASH_TIMEOUT <CRASH_TIMEOUT>` seconds:

- the vehicle is in :ref:`Auto <auto-mode>`, :ref:`Guided <guided-mode>`, :ref:`RTL <rtl-mode>` or :ref:`SmartRTL <smartrtl-mode>` mode
- velocity falls below :ref:`CRASH_VEL_MIN <CRASH_VEL_MIN>`
- the vehicle is turning at less than :ref:`CRASH_TRAT_MIN <CRASH_TRAT_MIN>`
- demanded throttle to the motors (from the pilot or autopilot) is at least :ref:`CRASH_THR_MIN <CRASH_THR_MIN>`

In addition, the :ref:`CRASH_ANGLE <CRASH_ANGLE>` parameter immediately enables the same actions above if the vehicle's roll or pitch angle exceeds that value. "0" disables this check.

A `Lua script applet <https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Scripting/applets/crash-actions.md>`_ is available to extend crash check actions.
```

上下文：给出适用模式、速度、转率、油门合取条件、持续时间和角度替代路径。

### ARD-ROVER-CRASH-002-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/Rover/Parameters.cpp:634-668`
- SHA-256：`84ffa3f20ff0acb1f1125a66b272e64fb82c6cc50b103688b996e15ca5ef462f`

```text
// @Param: CRASH_THR_MIN
    // @DisplayName: Crash throttle minimum
    // @Description: Throttle above this threshold accompanied by a low speed condition triggers crash detection. Zero disables velocity and turn rate checks.
    // @Units: %
    // @Range: 0 100
    // @Increment: 1
    // @User: Advanced
    AP_GROUPINFO("CRASH_THR_MIN", 58, ParametersG2, crash_thr_min, 5),

    // @Param: CRASH_VEL_MIN
    // @DisplayName: Crash velocity minimum
    // @Description: Velocity below this threshold with accompanying throttle demand triggers crash detection. Zero disables velocity check.
    // @Units: m/s
    // @Range: 0 60
    // @Increment: 0.1
    // @User: Advanced
    AP_GROUPINFO("CRASH_VEL_MIN", 59, ParametersG2, crash_vel_min, 0.08),

    // @Param: CRASH_TRAT_MIN
    // @DisplayName: Crash turn rate minimum
    // @Description: Turn rate below this threshold with accompanying throttle demand triggers crash detection. Zero disables turn rate check.
    // @Units: deg/s
    // @Range: 0 360
    // @Increment: 1
    // @User: Advanced
    AP_GROUPINFO("CRASH_TRAT_MIN", 60, ParametersG2, crash_turn_rate_min, 10.0),

    // @Param: CRASH_TIMEOUT
    // @DisplayName: Crash timeout
    // @Description: Crash conditions persisting for this duration trigger crash detection.
    // @Units: s
    // @Range: 0 60
    // @Increment: 0.5
    // @User: Advanced
    AP_GROUPINFO("CRASH_TIMEOUT", 61, ParametersG2, crash_timeout, 2.0),
```

上下文：冻结源码中的四个阈值/时间参数、单位、禁用值和默认值。

## Requirement IR

- 主体：ArduRover crash check
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：适用模式内 crash 条件合取首次连续成立。
- 前置：FS_CRASH_CHECK 为 1 或 2。；模式为 Auto/Guided/RTL/SmartRTL。；速度、转率和 demanded throttle 均使用各自运行时阈值。；隔离 CRASH_ANGLE 立即路径。
- 义务：条件持续至少 CRASH_TIMEOUT 后切换 Hold，并在配置为 2 时 disarm。
- 禁止：在 CRASH_TIMEOUT 结束前不得仅由 persistence 分支触发 crash action。
- 例外：任一合取条件中断会重置持续区间。；CRASH_ANGLE 是独立立即触发路径。
- 作用域：crash conjunction 从 false 变 true → 任一条件恢复、crash action、failsafe 禁用或 run 结束

## 时间与 MITL

- `T_crash`：`T_crash = runtime(CRASH_TIMEOUT)`；单位 `s`；下界闭合 `True`。
  起点：crash_condition_start；终点：crash_action；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：single vehicle-side instrumentation clock。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((crash_condition_start & crash_check_enabled) -> (G_[0,T_crash) !crash_action & F_[T_crash,infty) crash_action))`
- 单一具体公式：`G((crash_condition_start & crash_check_enabled) -> (G_[0,2) !crash_action & F_[2,infty) crash_action))`
- 形式化状态：`MONITOR_VALIDATED`

- TAMonitor 转换候选：`G((crash_condition_start && crash_check_enabled) -> (G[0,2000) (!crash_action) && F[2000,infty) crash_action))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/Rover — rover / `ardupilot-rover-m6` | `2.0 s` | `2.0 s` | `INSTANTIATED_FORMULA_VALIDATED` | `G((crash_condition_start & crash_check_enabled) -> (G_[0,2) !crash_action & F_[2,infty) crash_action))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Rover/parameters.json` SHA-256 `ed4de8b303095cf19449c9e6181678863cf25ba3eee8ff47ae5bf683e432fd79`，index `1132/1271` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-ROVER-CRASH-002-AP-01` | eligible_mode & armed & demanded_throttle>=CRASH_THR_MIN & groundspeed<CRASH_VEL_MIN & abs(turn_rate)<CRASH_TRAT_MIN 的上升沿。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-ROVER-CRASH-002-AP-02` | FS_CRASH_CHECK in {1,2} 且 CRASH_ANGLE=0 或姿态保证不越界。 | `DERIVED` | `BOUND` |
| `ARD-ROVER-CRASH-002-AP-03` | 进入 Hold；若 FS_CRASH_CHECK=2，同时最终 disarmed。 | `CONDITIONAL` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-ROVER-CRASH-002-AP-01 — `crash_condition_start`

- 受控自然语言：完整 crash 合取条件开始连续成立。
- 真值条件：eligible_mode & armed & demanded_throttle>=CRASH_THR_MIN & groundspeed<CRASH_VEL_MIN & abs(turn_rate)<CRASH_TRAT_MIN 的上升沿。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Static sample counter for consecutive crash-condition checks.` — `baseline/ardupilot/Rover/crash_check.cpp:11`；symbol `crash_counter`；kind `VARIABLE`；function `Rover::crash_check`；type `static uint16_t samples`；role `DEFINITION`；confidence `EXACT`。
  证据：The function is scheduled at 10 Hz and resets/increments this counter. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L11
- `Requires armed, FS_CRASH_CHECK nonzero, and autopilot mode unless the vehicle is a balancebot.` — `baseline/ardupilot/Rover/crash_check.cpp:15`；symbol `armed/enabled/eligible-mode guard`；kind `OTHER`；function `Rover::crash_check`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 14-18 reset the counter and return when ineligible. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L15
- `When enabled, continued counting requires low groundspeed, low absolute yaw rate, and absolute demanded throttle at or above their runtime thresholds, subject to zero-threshold disable rules.` — `baseline/ardupilot/Rover/crash_check.cpp:28`；symbol `persistence crash conjunction`；kind `OTHER`；function `Rover::crash_check`；type `bool over AP_Float and sensor/actuator values`；role `DERIVATION`；confidence `EXACT`。
  证据：Lines 28-35 reset on any threshold-negating disjunct. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L28
- `First increment from zero is the modelled crash_condition_start edge; subsequent increments represent persistence.` — `baseline/ardupilot/Rover/crash_check.cpp:38`；symbol `crash_counter++`；kind `ASSIGNMENT`；function `Rover::crash_check`；type `uint16_t samples`；role `WRITE`；confidence `MODELLED`。
  证据：No separate edge flag or timestamp is written. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L38
- `Nominal 10-Hz sampling schedule used to convert CRASH_TIMEOUT seconds to counter ticks.` — `baseline/ardupilot/Rover/Rover.cpp:130`；symbol `SCHED_TASK(crash_check, 10, ...)`；kind `FUNCTION`；function `Rover::scheduler_tasks`；type `10 Hz scheduled callback`；role `DERIVATION`；confidence `EXACT`。
  证据：crash_check compares crash_counter with crash_timeout * 10 at crash_check.cpp:41. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/Rover.cpp#L130

MAVLink/观测映射：

- `VFR_HUD.groundspeed` (ID 74)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Groundspeed and throttle fields approximate two conjuncts; VFR_HUD has no timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `VFR_HUD.throttle` (ID 74)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Demanded throttle for Rover; VFR_HUD has no timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `ATTITUDE.yawspeed` (ID 30)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `time_boot_ms (vehicle boot clock)`。Yaw rate with vehicle boot timestamp; cannot be strictly aligned to VFR_HUD from embedded fields.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Mode/armed are coarse state inputs. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-ROVER-CRASH-002-AP-02 — `crash_check_enabled`

- 受控自然语言：persistence crash check 已启用且 angle 路径被隔离。
- 真值条件：FS_CRASH_CHECK in {1,2} 且 CRASH_ANGLE=0 或姿态保证不越界。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DERIVED`；绑定状态：`BOUND`

源码绑定：

- `Runtime action enum: disabled, Hold, or HoldAndDisarm.` — `baseline/ardupilot/Rover/Parameters.cpp:136`；symbol `FS_CRASH_CHECK / Parameters::fs_crash_check`；kind `PARAMETER`；function ``；type `AP_Int8 / enum fs_crash_action`；role `DEFINITION`；confidence `EXACT`。
  证据：Enum values are Rover/defines.h:69-73. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/Parameters.cpp#L136
- `Independent roll/pitch crash threshold; zero disables this path.` — `baseline/ardupilot/Rover/Parameters.cpp:454`；symbol `CRASH_ANGLE / ParametersG2::crash_angle`；kind `PARAMETER`；function ``；type `AP_Int8 degrees`；role `DEFINITION`；confidence `EXACT`。
  证据：Metadata and macro define the angle threshold. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/Parameters.cpp#L454
- `Sets crashed immediately when nonzero CRASH_ANGLE is exceeded, independently of persistence completion.` — `baseline/ardupilot/Rover/crash_check.cpp:21`；symbol `crash-angle path`；kind `OTHER`；function `Rover::crash_check`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 20-23 compare pitch and roll and set crashed=true. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L21
- `Enables the persistence counter path; velocity and turn-rate subchecks are individually enabled by positive thresholds.` — `baseline/ardupilot/Rover/crash_check.cpp:28`；symbol `crash_thr_min > 0 && crash_timeout > 0`；kind `OTHER`；function `Rover::crash_check`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 28-44 contain the persistence path. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L28

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects FS_CRASH_CHECK, CRASH_ANGLE, CRASH_THR_MIN, CRASH_VEL_MIN, CRASH_TRAT_MIN; configuration snapshot
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-ROVER-CRASH-002-AP-03 — `crash_action`

- 受控自然语言：配置的 Hold/optional-disarm crash action 发生。
- 真值条件：进入 Hold；若 FS_CRASH_CHECK=2，同时最终 disarmed。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Common action producer after angle or persistence crash detection.` — `baseline/ardupilot/Rover/crash_check.cpp:46`；symbol `crashed action branch`；kind `EVENT`；function `Rover::crash_check`；type `bool crashed`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 46-63 log and select balancebot or ordinary Rover action. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L46
- `Ordinary Rover requests Hold with a cause-specific mode reason.` — `baseline/ardupilot/Rover/crash_check.cpp:58`；symbol `set_mode(mode_hold, ModeReason::CRASH_FAILSAFE)`；kind `FUNCTION`；function `Rover::crash_check`；type `bool mode transition request`；role `PRODUCER`；confidence `EXACT`。
  证据：Line 56 also produces Crash: Going to HOLD STATUSTEXT. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L58
- `When FS_CRASH_CHECK=2, requests disarm with AP_Arming::Method::CRASH after Hold request.` — `baseline/ardupilot/Rover/crash_check.cpp:59`；symbol `FS_CRASH_HOLD_AND_DISARM branch`；kind `FUNCTION`；function `Rover::crash_check`；type `AP_Arming::Method::CRASH`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 59-60 implement the optional disarm. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L59
- `Successful Hold transition records CRASH_FAILSAFE as the canonical cause and logs/sends mode state.` — `baseline/ardupilot/Rover/system.cpp:284`；symbol `control_mode_reason = reason`；kind `ASSIGNMENT`；function `Rover::set_mode`；type `ModeReason`；role `WRITE`；confidence `EXACT`。
  证据：Rover::is_crashed reads this reason at crash_check.cpp:69-72. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/system.cpp#L284
- `Balancebot variant emits Crash: Disarming and disarms directly without entering Hold.` — `baseline/ardupilot/Rover/crash_check.cpp:50`；symbol `balancebot crash action`；kind `EVENT`；function `Rover::crash_check`；type `AP_Arming::Method::CRASH`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 50-54 are the explicit alternate branch. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/Rover/crash_check.cpp#L50

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Observe Hold custom_mode and armed bit. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE
- `STATUSTEXT.text` (ID 253)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。May contain Crash: Going to HOLD; no timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `ARD-ROVER-CRASH-002--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-CRASH-002/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 正例/合法边界 | `ARD-ROVER-CRASH-002--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-CRASH-002/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 边界反例 | `ARD-ROVER-CRASH-002--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-CRASH-002/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `VIOLATED` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-ROVER-CRASH-002--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-CRASH-002/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `INCONCLUSIVE` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |
| 迟到或缺失 | `ARD-ROVER-CRASH-002--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-ROVER-CRASH-002/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `INCONCLUSIVE` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=PASS. |

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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=MAIN_ONLY version gap; continuous conjunction reset omitted; wire clock mismatch; monitor syntax unsupported. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- 需要统一飞控侧采样，不能按不同消息主机到达时间随意对齐。
- 阈值为运行时参数；源码默认仅记录。
- M7 automated independent audit: MAIN_ONLY version gap
- M7 automated independent audit: continuous conjunction reset omitted
- M7 automated independent audit: wire clock mismatch
- M7 automated independent audit: monitor syntax unsupported

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
