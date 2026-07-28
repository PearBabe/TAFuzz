# ARD-COPTER-RTL-003 — Copter RTL Home 上方等待

- 系统/车型：ArduPilot / Copter
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`NEEDS_CONTEXT`；分类：`OFFICIAL_BEHAVIOR`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-COPTER-RTL-003-S1

- 类别/权威：`OFFICIAL_BEHAVIOR` / `HIGH`
- 版本状态：`209e532bc97e5a41966f8c9ab483323c264cae08` / `MAIN_ONLY`
- 位置：`benchmark/extraction_runs/corpus_sources/ardupilot_wiki/copter/source/docs/rtl-mode.rst:65-68`
- SHA-256：`c7f8bbe421d4e3b4f00dc41cf0f8f032a155249fc738a159faf17600d5ab0991`

```text
-  :ref:`RTL_LOIT_TIME <RTL_LOIT_TIME>`:
   Time in milliseconds to hover/pause above the "Home" position before
   beginning final descent.
```

上下文：定义到达 Home 上方后、最终下降前的暂停区间。

### ARD-COPTER-RTL-003-S2

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/ArduCopter/Parameters.cpp:80-87`
- SHA-256：`ef28e89a26fe2baa8e9ed55b6c145c79726d6d7805d53e82ad4626da1401a0e6`

```text
// @Param: RTL_LOIT_TIME
    // @DisplayName: RTL loiter time
    // @Description: Time (in milliseconds) to loiter above home before beginning final descent
    // @Units: ms
    // @Range: 0 60000
    // @Increment: 1000
    // @User: Standard
    GSCALAR(rtl_loiter_time,      "RTL_LOIT_TIME",    RTL_LOITER_TIME),
```

上下文：冻结源码中的毫秒单位、范围和默认值。

## Requirement IR

- 主体：ArduCopter RTL mode
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：RTL 到达 Home 上方并进入 loiter/pause 阶段。
- 前置：RTL 未被取消，且 RTL_ALT_FINAL 等配置选择最终下降/着陆路径。
- 义务：等待运行时 RTL_LOIT_TIME 后开始最终下降。
- 禁止：持续符合条件时，在 RTL_LOIT_TIME 结束前不得开始最终下降。
- 例外：离开 RTL、改变为非下降结尾或外部合法 mode transition 会取消本次义务。
- 作用域：进入 Home 上方 loiter/pause 阶段 → 开始最终下降、RTL 取消或 run 结束

## 时间与 MITL

- `T_rtl_loiter`：`T_rtl_loiter = runtime(RTL_LOIT_TIME)`；单位 `ms`；下界闭合 `True`。
  起点：enter_loiter_at_home；终点：begin_final_descent；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：vehicle millis at RTL sub-state entry。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G(enter_loiter_at_home -> (G_[0,T_rtl_loiter] rtl_loiter_eligible -> (G_[0,T_rtl_loiter) !begin_final_descent & F_[T_rtl_loiter,infty) begin_final_descent)))`
- 单一具体公式：`G(enter_loiter_at_home -> (G_[0,5] rtl_loiter_eligible -> (G_[0,5) !begin_final_descent & F_[5,infty) begin_final_descent)))`
- 形式化状态：`UNSUPPORTED_BY_MONITOR`

- TAMonitor 转换候选：`G(enter_loiter_at_home -> (G[0,5000] rtl_loiter_eligible -> (G[0,5000) (!begin_final_descent) && F[5000,infty) begin_final_descent)))`
- 时间编码：源单位 `s` → monitor `ms`，每源单位 `1000` ticks；All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; no rounding or epsilon is introduced.
- 监视语义：Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts.
- 监视证据：`benchmark/extraction_runs/milestone7/monitor_validation/monitor_validation.json` SHA-256 `06cfc09caafc2776e7ebc4a6dd1534fab9aba1337d10eb75ad031184ad6502e4`。

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/ArduCopter — quad / `ardupilot-copter-m6` | `5000 ms` | `5.0 s` | `INSTANTIATED_UNVALIDATED` | `G(enter_loiter_at_home -> (G_[0,5] rtl_loiter_eligible -> (G_[0,5) !begin_final_descent & F_[5,infty) begin_final_descent)))` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/parameters.json` SHA-256 `f3d4a3e416eb7e01000deec397640cbf291c8b14805073da5b256b88c6de61ab`，index `5/1387` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-COPTER-RTL-003-AP-01` | 内部 RTL sub-state 的进入边沿。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-COPTER-RTL-003-AP-02` | 在所检查时间范围内 RTL 和 landing-path eligibility 均持续为 true。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-COPTER-RTL-003-AP-03` | 内部 RTL sub-state 进入 final descent 的边沿。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-COPTER-RTL-003-AP-01 — `enter_loiter_at_home`

- 受控自然语言：RTL 进入 Home 上方等待子状态。
- 真值条件：内部 RTL sub-state 的进入边沿。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `State-machine transition call after RETURN_HOME reports complete.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:148`；symbol `RETURN_HOME -> loiterathome_start`；kind `EVENT`；function `ModeRTL::run`；type `ModeRTL::SubMode transition`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 138-150 dispatch loiterathome_start when _state_complete is true in RETURN_HOME. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L148
- `Canonical internal sub-state write for entering the Home loiter stage.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:258`；symbol `_state = SubMode::LOITER_AT_HOME`；kind `ASSIGNMENT`；function `ModeRTL::loiterathome_start`；type `ModeRTL::SubMode`；role `WRITE`；confidence `EXACT`。
  证据：loiterathome_start writes the state and clears _state_complete. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L258
- `Autopilot monotonic-boot epoch for this LOITER_AT_HOME entry.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:260`；symbol `_loiter_start_time = millis()`；kind `ASSIGNMENT`；function `ModeRTL::loiterathome_start`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：The timer is initialized in the same function immediately after the state write. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L260

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Confirms coarse RTL mode only. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-RTL-003-AP-02 — `rtl_loiter_eligible`

- 受控自然语言：本次 RTL 持续选择最终下降路径且未被取消。
- 真值条件：在所检查时间范围内 RTL 和 landing-path eligibility 均持续为 true。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Internal RTL state enum and current-state field; LOITER_AT_HOME is the timed stage.` — `baseline/ardupilot/ArduCopter/mode.h:1534`；symbol `ModeRTL::SubMode and ModeRTL::_state`；kind `FIELD`；function ``；type `enum class ModeRTL::SubMode : uint8_t`；role `DEFINITION`；confidence `EXACT`。
  证据：mode.h:1534-1542 defines enum/accessor and mode.h:1603 stores _state. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode.h#L1534
- `Path-selection field: true chooses direct landing after loiter; false permits FINAL_DESCENT when radio failsafe is also false.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:462`；symbol `rtl_path.land = alt_final_m.get() <= 0`；kind `ASSIGNMENT`；function `ModeRTL::build_path`；type `bool`；role `WRITE`；confidence `EXACT`。
  证据：build_path derives land from runtime RTL_ALT_FINAL_M. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L462
- `Transition guard selecting LAND versus FINAL_DESCENT after Home loiter completes.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:152`；symbol `rtl_path.land || copter.failsafe.radio`；kind `OTHER`；function `ModeRTL::run`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 151-156 call land_start on true and descent_start on false. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L152
- `RTL run stops state progression when motors are not armed.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:134`；symbol `motors->armed()`；kind `OTHER`；function `ModeRTL::run`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Lines 132-136 return immediately when disarmed. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L134

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Confirms coarse RTL mode only. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-COPTER-RTL-003-AP-03 — `begin_final_descent`

- 受控自然语言：RTL 开始最终下降。
- 真值条件：内部 RTL sub-state 进入 final descent 的边沿。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `After elapsed RTL_LOIT_TIME and yaw-reset completion, sets _state_complete true.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:294`；symbol `RTL loiter completion guard`；kind `OTHER`；function `ModeRTL::loiterathome_run`；type `bool over uint32_t milliseconds`；role `GUARD`；confidence `EXACT`。
  证据：Lines 294-304 compare elapsed time with runtime rtl_loiter_time and complete the stage. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L294
- `State-machine producer chosen when Home loiter is complete, rtl_path.land is false, and radio failsafe is false.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:155`；symbol `descent_start()`；kind `EVENT`；function `ModeRTL::run`；type `ModeRTL transition`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 151-156 choose between land_start and descent_start. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L155
- `Canonical internal sub-state write for final descent start.` — `baseline/ardupilot/ArduCopter/mode_rtl.cpp:311`；symbol `_state = SubMode::FINAL_DESCENT`；kind `ASSIGNMENT`；function `ModeRTL::descent_start`；type `ModeRTL::SubMode`；role `WRITE`；confidence `EXACT`。
  证据：descent_start writes FINAL_DESCENT, clears completion, and initializes vertical/yaw controllers. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L311

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Confirms coarse RTL mode only. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


## 合成公式/轨迹门禁

| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |
|---|---|---|---|---|
| 正例/合法边界 | `ARD-COPTER-RTL-003--positive_after_threshold` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-RTL-003/traces/positive_after_threshold/trace.json)) | `SATISFIED` | `NOT_RUN` | positive_after_threshold: Response occurs strictly after the lower threshold and no response occurs before it. TAMonitor prefix expectation=INCONCLUSIVE; comparison=UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT. |
| 正例/合法边界 | `ARD-COPTER-RTL-003--boundary_exact_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-RTL-003/traces/boundary_exact_legal/trace.json)) | `SATISFIED` | `NOT_RUN` | boundary_exact_legal: Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal. TAMonitor prefix expectation=INCONCLUSIVE; comparison=UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT. |
| 边界反例 | `ARD-COPTER-RTL-003--too_early_one_tick` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-RTL-003/traces/too_early_one_tick/trace.json)) | `VIOLATED` | `NOT_RUN` | too_early_one_tick: Response occurs one exact monitor tick before the threshold. TAMonitor prefix expectation=NEGATIVE; comparison=UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT. |
| 迟到或缺失 | `ARD-COPTER-RTL-003--late_response_unbounded_legal` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-RTL-003/traces/late_response_unbounded_legal/trace.json)) | `SATISFIED` | `NOT_RUN` | late_response_unbounded_legal: The source formula has no finite upper response bound; a late response is legal, not a violation. TAMonitor prefix expectation=INCONCLUSIVE; comparison=UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT. |
| 迟到或缺失 | `ARD-COPTER-RTL-003--missing_completed_trace` ([JSON](../../../benchmark/extraction_runs/milestone7/monitor_validation/properties/ARD-COPTER-RTL-003/traces/missing_completed_trace/trace.json)) | `VIOLATED` | `NOT_RUN` | missing_completed_trace: The independent oracle treats this synthetic finite word as complete and no required response occurs. TAMonitor prefix expectation=INCONCLUSIVE; comparison=UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT. |

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
| `monitor` | `INCONCLUSIVE` | TAMonitor infinite-prefix status=UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME; trace comparisons={"UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT": 6}. At least one required synthetic trace could not execute under the primary TAMonitor configuration. The resource/semantic blocker is retained and the formula instance remains unvalidated. Exact stdout/stderr and result metadata are retained. |
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends NEEDS_CONTEXT; blockers=MAIN_ONLY version gap; cancellation is not closed in source/formula; all APs internal; monitor syntax unsupported. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- ArduPilot wiki 是 MAIN_ONLY。
- 0ms 是合法运行时值；边界需要同一飞控时钟的事件探针。
- M7 automated independent audit: MAIN_ONLY version gap
- M7 automated independent audit: cancellation is not closed in source/formula
- M7 automated independent audit: all APs internal
- M7 automated independent audit: monitor syntax unsupported

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
