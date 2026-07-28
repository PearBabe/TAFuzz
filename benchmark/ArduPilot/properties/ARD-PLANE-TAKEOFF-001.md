# ARD-PLANE-TAKEOFF-001 — Plane 自动起飞超时

- 系统/车型：ArduPilot / Plane
- 固件提交：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`
- 状态：`CANDIDATE`；分类：`PARAM_METADATA_CANDIDATE`
- 实现符合性：`NOT_ASSESSED`

## 自然语言证据

### ARD-PLANE-TAKEOFF-001-S1

- 类别/权威：`PARAM_METADATA` / `LOW`
- 版本状态：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` / `CURRENT`
- 位置：`baseline/ardupilot/ArduPlane/Parameters.cpp:1113-1120`
- SHA-256：`03942ea920ff5dc25381d7b79d8c1e28de3750746cdf3872a7ad6f43cdb6eb64`

```text
// @Param: TKOFF_TIMEOUT
    // @DisplayName: Takeoff timeout
    // @Description: This is the timeout for an automatic takeoff. If this is non-zero and the aircraft does not reach a ground speed of at least 4 m/s within this number of seconds then the takeoff is aborted and the vehicle disarmed. If the value is zero then no timeout applies.
    // @Range: 0 120
    // @Increment: 1
    // @Units: s
    // @User: Standard
    AP_GROUPINFO("TKOFF_TIMEOUT", 19, ParametersG2, takeoff_timeout, 0),
```

上下文：参数元数据给出自动起飞、4m/s 阈值、超时、abort/disarm 和 0 禁用语义。

## Requirement IR

- 主体：ArduPlane automatic takeoff
- 模态：`BEHAVIORAL_DESCRIPTION`
- 触发：启用 TKOFF_TIMEOUT 的自动起飞开始。
- 前置：TKOFF_TIMEOUT > 0。；从内部 automatic-takeoff start 起，地速在整个窗口内从未达到 4m/s。
- 义务：超时后中止 takeoff 并 disarm。
- 禁止：若在窗口内达到至少 4m/s，则不能仅由该 timeout 分支判为违规。
- 例外：TKOFF_TIMEOUT=0 禁用。；非 automatic-takeoff 不在范围。
- 作用域：内部 automatic-takeoff start → 达到 4m/s、takeoff abort/disarm、离开 takeoff 或 run 结束

## 时间与 MITL

- `T_takeoff`：`T_takeoff = runtime(TKOFF_TIMEOUT)`；单位 `s`；下界闭合 `True`。
  起点：automatic_takeoff_start；终点：takeoff_abort；时钟：`AUTOPILOT_MONOTONIC_BOOT`；载体：internal takeoff start millis。
  不确定性：No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty can change a boundary verdict, the verdict is INCONCLUSIVE.

- 符号公式：`G((automatic_takeoff_start & timeout_enabled) -> (G_[0,T_takeoff] speed_below_4mps -> F_[T_takeoff,infty) (takeoff_aborted & F disarmed)))`
- 单一具体公式：`null`（没有单一、已启用且上下文闭合的具体实例）
- 形式化状态：`SYMBOLIC_ONLY`

### 运行时具体实例

| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |
|---|---:|---:|---|---|---|
| ArduPilot/ArduPlane — plane / `ardupilot-plane-m6` | `0 s` | `0.0 s` | `DISABLED_BY_RUNTIME_CONFIGURATION` | `未形式化` | `benchmark/extraction_runs/milestone6/ArduPilot/runs/Plane/parameters.json` SHA-256 `0767f3f3019f5399679118cbcf0931e552bdb6ee40cc67303a8b476a6e61c4dd`，index `1217/1440` |

这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。

## 原子命题与待绑定项

| AP | 真值条件 | 可观测性 | 绑定状态 |
|---|---|---|---|
| `ARD-PLANE-TAKEOFF-001-AP-01` | 当前 takeoff attempt 的内部 start epoch 从 unset 变为有效。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-PLANE-TAKEOFF-001-AP-02` | PARAM_VALUE(TKOFF_TIMEOUT)>0。 | `DIRECT` | `BOUND` |
| `ARD-PLANE-TAKEOFF-001-AP-03` | AP::gps ground speed < 4.0 m/s 且 GPS speed 有效/新鲜。 | `CONDITIONAL` | `BOUND` |
| `ARD-PLANE-TAKEOFF-001-AP-04` | takeoff-abort event 与当前 attempt correlation key 匹配。 | `INSTRUMENTATION_REQUIRED` | `BOUND` |
| `ARD-PLANE-TAKEOFF-001-AP-05` | armed state 为 false。 | `DIRECT` | `BOUND` |

## AP 当前源码与 MAVLink 详细映射

### ARD-PLANE-TAKEOFF-001-AP-01 — `automatic_takeoff_start`

- 受控自然语言：自动起飞计时起点发生。
- 真值条件：当前 takeoff attempt 的内部 start epoch 从 unset 变为有效。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Per-attempt autopilot monotonic-boot start epoch used by TKOFF_TIMEOUT.` — `baseline/ardupilot/ArduPlane/Plane.h:447`；symbol `Plane::takeoff_state.start_time_ms`；kind `FIELD`；function ``；type `uint32_t milliseconds`；role `DEFINITION`；confidence `EXACT`。
  证据：Plane.h:439-452 defines takeoff_state and its timers. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/Plane.h#L447
- `AUTO takeoff start after launch acceleration/delay/speed/attitude checks trigger.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:130`；symbol `takeoff_state.start_time_ms = now`；kind `ASSIGNMENT`；function `Plane::auto_takeoff_check`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 124-134 accept the launch and initialize start, level-off, and throttle-max timers. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L130
- `TAKEOFF-mode start after position/home setup, throttle unsuppressed, and sufficient groundspeed.` — `baseline/ardupilot/ArduPlane/mode_takeoff.cpp:132`；symbol `plane.takeoff_state.start_time_ms = millis()`；kind `ASSIGNMENT`；function `ModeTakeoff::update`；type `uint32_t milliseconds`；role `WRITE`；confidence `EXACT`。
  证据：Lines 128-136 initialize the takeoff attempt timers and course. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/mode_takeoff.cpp#L132

MAVLink/观测映射：

- `HEARTBEAT.custom_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。Can confirm coarse TAKEOFF/AUTO mode, without the start epoch. HEARTBEAT has no embedded timestamp.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-PLANE-TAKEOFF-001-AP-02 — `timeout_enabled`

- 受控自然语言：运行时 TKOFF_TIMEOUT 大于零。
- 真值条件：PARAM_VALUE(TKOFF_TIMEOUT)>0。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Runtime automatic-takeoff timeout in seconds; zero disables.` — `baseline/ardupilot/ArduPlane/Parameters.cpp:1120`；symbol `TKOFF_TIMEOUT / ParametersG2::takeoff_timeout`；kind `PARAMETER`；function ``；type `AP_Int8`；role `DEFINITION`；confidence `EXACT`。
  证据：AP_GROUPINFO binds TKOFF_TIMEOUT; field type is at Parameters.h:522. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/Parameters.cpp#L1120
- `Direct runtime enable predicate combined with a valid start epoch.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:393`；symbol `g2.takeoff_timeout > 0`；kind `OTHER`；function `Plane::check_takeoff_timeout`；type `bool over AP_Int8`；role `GUARD`；confidence `EXACT`。
  证据：The function enters timeout logic only when start_time_ms is nonzero and TKOFF_TIMEOUT is positive. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L393
- `Seconds-to-milliseconds conversion for the runtime timeout.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:401`；symbol `1000U * g2.takeoff_timeout`；kind `OTHER`；function `Plane::check_takeoff_timeout`；type `uint32_t milliseconds`；role `DERIVATION`；confidence `EXACT`。
  证据：The strict greater-than elapsed-time comparison performs the conversion inline. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L401

MAVLink/观测映射：

- `PARAM_VALUE.param_value` (ID 22)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。PARAM_VALUE.param_id selects TKOFF_TIMEOUT; truth is param_value > 0; PARAM_VALUE has no timestamp
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-PLANE-TAKEOFF-001-AP-03 — `speed_below_4mps`

- 受控自然语言：地速低于 4m/s。
- 真值条件：AP::gps ground speed < 4.0 m/s 且 GPS speed 有效/新鲜。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`CONDITIONAL`；绑定状态：`BOUND`

源码绑定：

- `Backend-populated primary GPS ground speed in metres per second.` — `baseline/ardupilot/libraries/AP_GPS/AP_GPS.h:197`；symbol `AP_GPS::GPS_State::ground_speed`；kind `FIELD`；function ``；type `float m/s`；role `DEFINITION`；confidence `EXACT`。
  证据：GPS_State is filled by the selected backend; inline accessor is at AP_GPS.h:369-373. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_GPS/AP_GPS.h#L197
- `Reads the primary GPS ground-speed sample used by the timeout check.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:394`；symbol `ground_speed = AP::gps().ground_speed()`；kind `VARIABLE`；function `Plane::check_takeoff_timeout`；type `const float m/s`；role `READ`；confidence `EXACT`。
  证据：Lines 394-396 bind the GPS value, literal 4 m/s threshold, and comparison. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L394
- `Clears the timeout epoch at 4 m/s or above; the else path is the source identity for below 4 m/s.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:396`；symbol `ground_speed >= takeoff_min_ground_speed`；kind `OTHER`；function `Plane::check_takeoff_timeout`；type `bool`；role `GUARD`；confidence `EXACT`。
  证据：Threshold is const float 4 at line 395; lines 396-399 clear the timer on reaching it. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L396
- `Candidate freshness carrier for the primary GPS instance, separate from ground_speed.` — `baseline/ardupilot/libraries/AP_GPS/AP_GPS.h:448`；symbol `AP_GPS::last_message_time_ms`；kind `FUNCTION`；function `AP_GPS::last_message_time_ms`；type `uint32_t milliseconds`；role `OBSERVATION_SITE`；confidence `MAY`。
  证据：AP_GPS.h:446-452 exposes last processed GPS-message time; check_takeoff_timeout does not read it. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_GPS/AP_GPS.h#L448

MAVLink/观测映射：

- `GPS_RAW_INT.vel` (ID 24)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `time_usec (ambiguous UNIX epoch or system boot; GPS fix time)`。Ground speed in cm/s; predicate is vel < 400 with valid fresh fix. time_usec may be UNIX epoch or system boot per XML.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-PLANE-TAKEOFF-001-AP-04 — `takeoff_aborted`

- 受控自然语言：本次自动起飞被 timeout 原因中止。
- 真值条件：takeoff-abort event 与当前 attempt correlation key 匹配。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`INSTRUMENTATION_REQUIRED`；绑定状态：`BOUND`

源码绑定：

- `Elapsed time above runtime TKOFF_TIMEOUT while ground speed remains below 4 m/s.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:401`；symbol `takeoff timeout branch`；kind `EVENT`；function `Plane::check_takeoff_timeout`；type `bool edge`；role `PRODUCER`；confidence `EXACT`。
  证据：Lines 401-405 emit text, disarm with TAKEOFFTIMEOUT, clear the epoch, and return true. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L401
- `Human-readable timeout consequence including measured ground speed.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:402`；symbol `Takeoff timeout STATUSTEXT`；kind `MESSAGE_PRODUCER`；function `Plane::check_takeoff_timeout`；type `STATUSTEXT text`；role `PRODUCER`；confidence `MAY`。
  证据：send_text queues a text message; it is not a typed attempt identifier or exact clock carrier. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L402
- `Cause-specific disarm request for this timeout event.` — `baseline/ardupilot/ArduPlane/takeoff.cpp:403`；symbol `arming.disarm(AP_Arming::Method::TAKEOFFTIMEOUT)`；kind `FUNCTION`；function `Plane::check_takeoff_timeout`；type `AP_Arming::Method::TAKEOFFTIMEOUT`；role `PRODUCER`；confidence `EXACT`。
  证据：Method value 27 is declared at AP_Arming.h:80. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/takeoff.cpp#L403
- `On true, leaves TAKEOFF flight stage and clears takeoff_mode_setup.` — `baseline/ardupilot/ArduPlane/mode_takeoff.cpp:141`；symbol `plane.check_takeoff_timeout()`；kind `RETURN`；function `ModeTakeoff::update`；type `bool`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 140-144 consume check_takeoff_timeout(). Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/mode_takeoff.cpp#L141
- `On true, resets the current mission after the timeout event.` — `baseline/ardupilot/ArduPlane/commands_logic.cpp:601`；symbol `AUTO mission takeoff timeout consumer`；kind `RETURN`；function `Plane::verify_takeoff`；type `bool`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 600-603 consume the timeout return and call mission.reset(). Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/commands_logic.cpp#L601

MAVLink/观测映射：

- `STATUSTEXT.text` (ID 253)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。May contain Takeoff timeout text; no timestamp and delivery may be delayed/lost.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/common.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE

### ARD-PLANE-TAKEOFF-001-AP-05 — `disarmed`

- 受控自然语言：飞控处于 disarmed。
- 真值条件：armed state 为 false。
- 有效性：Only evaluate inside the property scope and after configuration capture.
- freshness：Must be sampled in the selected property clock domain; stale observations are invalid.
- 可观测性：`DIRECT`；绑定状态：`BOUND`

源码绑定：

- `Canonical raw armed-state transition to false after disarm checks pass.` — `baseline/ardupilot/libraries/AP_Arming/AP_Arming.cpp:1970`；symbol `AP_Arming::armed = false`；kind `ASSIGNMENT`；function `AP_Arming::disarm`；type `bool`；role `WRITE`；confidence `EXACT`。
  证据：Lines 1954-1974 reject already-disarmed/invalid rudder requests, then write armed=false and record the method. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_Arming/AP_Arming.cpp#L1970
- `Plane-specific disarm path delegates the raw state transition, then changes throttle/mode-related state.` — `baseline/ardupilot/ArduPlane/AP_Arming_Plane.cpp:336`；symbol `AP_Arming::disarm(method, do_disarm_checks)`；kind `FUNCTION`；function `AP_Arming_Plane::disarm`；type `bool(AP_Arming::Method,bool)`；role `CONSUMER`；confidence `EXACT`。
  证据：Lines 325-371 implement the Plane override; line 370 emits Throttle disarmed text after success. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduPlane/AP_Arming_Plane.cpp#L336
- `Public armed-state accessor used throughout vehicle logic.` — `baseline/ardupilot/libraries/AP_Arming/AP_Arming.cpp:308`；symbol `AP_Arming::is_armed`；kind `FUNCTION`；function `AP_Arming::is_armed`；type `bool() const`；role `READ`；confidence `EXACT`。
  证据：Line 310 returns raw armed OR arming_required()==Required::NO. Fixed permalink: https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_Arming/AP_Arming.cpp#L308

MAVLink/观测映射：

- `HEARTBEAT.base_mode` (ID 0)，方向 `OUTGOING`，支持 `STATIC_SUPPORTED`，时间字段 `无`。MAV_MODE_FLAG_SAFETY_ARMED clear means disarmed for the target autopilot.
  证据：baseline/ardupilot/modules/mavlink/message_definitions/v1.0/minimal.xml; static_support_matrix=STATIC_REFERENCE_FOUND; static_catalog_runtime_column=NOT_RUN_NO_CAPTURE


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
| `independent_review` | `INCONCLUSIVE` | Automated non-human audit completed 9 gates and recommends CANDIDATE; blockers=sole LOW implementation metadata source; current runtime disables property; internal start/abort APs; no concrete monitor formula. No human reviewer or arbitration was claimed. |

完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。


源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。

## 冲突与验证

- 0 是源码默认且表示 disabled；不得生成默认 concrete 公式。
- abort 到 disarm 没有独立数值上界，公式只保留定性 eventually。
- M7 automated independent audit: sole LOW implementation metadata source
- M7 automated independent audit: current runtime disables property
- M7 automated independent audit: internal start/abort APs
- M7 automated independent audit: no concrete monitor formula

Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。`implementation_satisfaction` 固定为 `NOT_ASSESSED`。
