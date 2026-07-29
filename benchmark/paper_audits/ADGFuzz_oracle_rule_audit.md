# ADGFuzz 三类判定器、阈值与时间来源审计

## 1. 结论

ADGFuzz 没有从 ArduPilot/PX4 文档中提取产品规范。论文的 ground、route deviation、software crash 三个“invariant”是作者手工设计的测试结果判定器；论文、README 和公开代码之间还存在消息、阈值、连续性与计时差异。它们在本 benchmark 中统一初始分类为：

```text
classification: AUXILIARY_ORACLE
accepted_as_system_mitl_property: false
implementation_satisfaction: NOT_ASSESSED
reason: no current system-specific normative source and known context-dependent false positives
```

只有在当前 ArduPilot/PX4 官方材料中另行找到独立要求，闭合适用状态、合法例外、时间来源和 AP 绑定后，才可新建系统性质。ADGFuzz 的 Python 代码位置只能记录为 `oracle_implementation`，不能冒充被测飞控源码变量。

## 2. 冻结证据与版本差异

| 对象 | 冻结身份 |
|---|---|
| ADGFuzz PDF | 19 页；SHA-256 `bb86bc3177c4e4bf2c8fe73e14e99760ab4dd662deb7902afafb502cfacaed72` |
| 公开仓库 | `/home/lqq/project/TAFuzz/baseline/ADGFuzz`；commit `203fce3f4265241340ed62b9be90aec1da0afa37` |
| 论文 SUT | ArduPilot `564879594ebb8d31c6400461b96f5dc442f14533`；PX4 `d35c5f4a4e9515542d9527594f339cd97ab0c70b` |
| 当前 benchmark SUT | ArduPilot `8f2e5db…`；PX4 v1.17.0 `d6f12ad…` |

当前系统与论文 SUT 不同，任何历史变量、消息可用性或默认参数都必须在当前源码中重新证明。更完整的逐行历史分析见 [`analysis/adgfuzz_paper_code_deep_reading_zh.md`](../../analysis/adgfuzz_paper_code_deep_reading_zh.md)。

## 3. 判定器总览

| 判定器 | 论文表述 | README 表述 | 公开代码实际规则 | 时间域/数值来源 | 作为当前性质 |
|---|---|---|---|---|---|
| Ground | system status messages + runtime logs 判断意外落地 | 消息说明存在字段对调 | ArduPilot 文本/状态；PX4 landed 转移或 `<1 m` | 无规范时间；枚举来自 MAVLink，`1 m` code-only | `AUXILIARY_ORACLE` |
| Route deviation | 短窗口内距离持续增加，示例 7 s | Copter/Rover 5 s/3 次；Plane 12 s/7 次 | ArduPilot 12 s/9 次非连续累计；PX4 `>0.05 m` 连续 4 次且无窗口 | host wall clock 或不定采样计数；阈值无官方依据 | `AUXILIARY_ORACLE` |
| Software crash | 2 s 无 heartbeat | 多次尝试无 MAVLink exchange | 6×0.3 s 无任意 MAVLink 消息，结果名 `ArithmException` | GCS/测试机 wall clock；名义 1.8 s | `AUXILIARY_ORACLE` |

## 4. Ground 判定器

### 4.1 论文语义

论文 PDF p.8 §IV-E 将其描述为：飞行器因动力或其他故障而意外接地，通过 system status messages 和 runtime logs 判断。论文没有给出具体消息字段、枚举值、距离阈值、时间窗或合法 LAND/DISARM 例外。

### 4.2 ArduPilot 实现

公开代码中的活动规则为：

- `STATUSTEXT.text` 包含精确子串 `Hit ground`；
- 或 `HEARTBEAT.system_status == 6`；
- 或 `HEARTBEAT.system_status == 7`；
- `status_bug OR hit_ground` 最终统一保存为 `StatusError`。

证据：[`oracle.py:213`](../../baseline/ADGFuzz/fuzzer/oracle.py#L213)、[`oracle.py:233`](../../baseline/ADGFuzz/fuzzer/oracle.py#L233)、[`fuzz.py:322`](../../baseline/ADGFuzz/fuzzer/fuzz.py#L322)。

`6` 与 `7` 分别是 MAVLink `MAV_STATE_EMERGENCY` 和 `MAV_STATE_POWEROFF` 的协议枚举值；它们的数值来源可追溯到 MAVLink XML。把二者统一解释成“ground crash”则是作者判定策略，不是协议或 ArduPilot 的规范要求。

### 4.3 PX4 实现

公开代码中的规则为：

1. 观察 `EXTENDED_SYS_STATE.landed_state == 2 (IN_AIR)` 后锁存 `airborne=True`；
2. 之后观察 `landed_state == 1 (ON_GROUND)` 即判 ground；
3. 或者曾经 airborne 且 `GLOBAL_POSITION_INT.relative_alt / 1000 < 1 m`。

证据：[`oracle.py:248`](../../baseline/ADGFuzz/fuzzer/oracle.py#L248)、[`oracle.py:260`](../../baseline/ADGFuzz/fuzzer/oracle.py#L260)、[`fuzzpx4.py:296`](../../baseline/ADGFuzz/fuzzer/fuzzpx4.py#L296)。

字段/数值来源分别为：

| 项 | 来源 | 审计标签 |
|---|---|---|
| `landed_state=1/2` | MAVLink `MAV_LANDED_STATE` 枚举 | `MAVLINK_INTERFACE_DEFINITION` |
| `relative_alt` | MAVLink `GLOBAL_POSITION_INT`，单位 mm，相对 home | `MAVLINK_INTERFACE_DEFINITION` |
| `/1000` | mm→m 单位转换 | `DERIVED_EXACT` |
| `<1 m` | 只出现在 ADGFuzz Python 代码；论文/README/官方配置未给推导 | `CODE_ONLY_HEURISTIC`, derivation `UNKNOWN` |

README 还把两种消息的职责写反：`GLOBAL_POSITION_INT` 没有 `landed_state`，`EXTENDED_SYS_STATE` 没有 altitude；代码读取的是 relative altitude，而不是 README 所称 absolute altitude。见 [`README.md:224`](../../baseline/ADGFuzz/README.md#L224)。

### 4.4 合法上下文与误报

正常 LAND、DISARM、某些 failsafe 的预期 LAND、关停或 Rover 的状态变化都可能满足上述观测。论文 Appendix A 也记录了由人工剔除的合法 LAND/DISARM 等误报；Rover 在论文概念上不适用 airborne ground 类别，但 ArduPilot handler 没有按车型关闭 `system_status` 规则。

故它不能形式化成无条件的 `airborne → ¬on_ground`。若当前官方文档存在具体“在状态 S、非例外 E 时不得接地”的要求，必须独立恢复 S、E、任务作用域和接地真值条件。

## 5. Route deviation 判定器

### 5.1 论文与 README

论文 PDF p.8 的自然语言是：waypoint navigation 中，车辆到目标的距离在一个短时间窗内持续增加，并以“e.g., 7 seconds”举例。`7 seconds` 明确是示例，不是规范数值，也没有定义采样率、连续性的重置规则或时钟。

README 则给出：

- Copter/Rover：5 秒内连续增加 3 次；
- Plane：12 秒内连续增加 7 次，理由是飞机接近 waypoint 时可能盘旋。

证据：[`README.md:226`](../../baseline/ADGFuzz/README.md#L226)。

### 5.2 ArduPilot 代码实际规则

[`oracle.py:108`](../../baseline/ADGFuzz/fuzzer/oracle.py#L108) 起的实现：

1. 读取 `NAV_CONTROLLER_OUTPUT.wp_dist`，协议单位为米；
2. 当前距离大于上次距离时记录测试机 `time.time()`；
3. 只保留最近 12 秒的增加事件；
4. 事件达到 9 次时判 route deviation；
5. 距离下降不会清空事件列表，所以并非“连续增加”；
6. Copter/Plane/Rover 共用该实现，没有 README 所述车型阈值分支；
7. 循环含 `sleep(0.5)`，但 `recv_match(... timeout=1)` 与消息竞争令采样周期不固定。

时间合同只能诚实写为：

```text
raw_window = 12 s
source_type = ADGFUZZ_CODE_CONSTANT
clock_domain = GCS_HOST_WALL_CLOCK
timestamp_carrier = Python time.time()
event = observed wp_dist increase at oracle receive loop
count_threshold = 9
continuity = false
sampling_period = variable
derivation/calibration = UNKNOWN
```

这 12 秒不是消息 sender boot time、飞控 monotonic time、任务相对时间或 SITL 仿真时间。改变 `SIM_SPEEDUP`、消息速率、阻塞时间或主机调度，会改变窗口内可出现的样本数。

代码状态跨轮次问题也应精确描述：`wp_distance` 和事件列表未在 `reset_all()` 清空；重启常规等待 60 秒会使旧事件在下一次增加时因窗口过期，但上一轮 `wp_distance` 仍可能参与下一轮第一次比较。

### 5.3 PX4 代码实际规则

[`oracle.py:366`](../../baseline/ADGFuzz/fuzzer/oracle.py#L366) 起的实现：

1. 用 `MISSION_CURRENT.seq` 选择仓库任务文件中的目标 waypoint；
2. 将 `GLOBAL_POSITION_INT.lat/lon` 除以 `1e7` 得到度制经纬度；
3. 用 `geopy.geodesic` 计算当前点到目标的米制距离；
4. 比上次距离增加超过 `0.05 m` 时计数，否则清零；
5. `deviate_count > 3`，即连续 4 次增加，触发判定；
6. 没有总时间窗；循环 sleep 与两次最多 1 秒的阻塞接收令样本间隔可变。

`0.05 m` 唯一说明是代码注释用于过滤小扰动，属于作者经验型代码启发式；连续 4 次没有来源或校准数据。不能将它改写成固定秒数 MITL 约束。

### 5.4 不能从路线 oracle 直接得到的性质

以下内容均缺失：

- 当前 waypoint 的关联键与任务切换边界；
- 接近 waypoint 时的 acceptance radius；
- Plane loiter/turn 的合法例外；
- path-following 与 direct-to-waypoint 的几何区别；
- GPS/position estimate 的有效性与 freshness；
- distance increase 的容差、坐标系和不确定度；
- 规范给出的持续时间。

因此 route 判定器只能保留为 fuzzing 异常线索。若官方任务/导航文档另有要求，需从该原文重新建 IR。

## 6. Software crash / message silence 判定器

### 6.1 三层差异

| 层次 | 规则 |
|---|---|
| 论文 p.8 | 连续 2 秒没有 heartbeat 即认为 software crash |
| README | 多次尝试仍没有任何 MAVLink message exchange |
| 代码 | 6 次 `recv_match(blocking=True, timeout=0.3)` 均无任意类型消息 |

代码证据：[`oracle.py:273`](../../baseline/ADGFuzz/fuzzer/oracle.py#L273)、[`fuzz.py:343`](../../baseline/ADGFuzz/fuzzer/fuzz.py#L343)、[`fuzzpx4.py:316`](../../baseline/ADGFuzz/fuzzer/fuzzpx4.py#L316)。

### 6.2 时间的真实含义

```text
attempts = 6
per_attempt_timeout = 0.3 s
nominal_total = 6 * 0.3 s = 1.8 s
source_type = ADGFUZZ_CODE_CONSTANT_AND_DERIVATION
clock_domain = GCS_HOST_WALL_CLOCK
timestamp_carrier = PyMAVLink receive timeout / time.time()
actual_upper_bound = not guaranteed; scheduling can extend it
message_filter = ANY, not HEARTBEAT
```

监控线程从当前 MIS 开始持续运行；计时不是“某输入注入后 1.8 秒”的专用窗口。结果文件名中的时间是 campaign 开始到主循环记录结果的 wall-clock 时间，也不是静默开始或最后 heartbeat 的 timestamp。

### 6.3 观测结论的边界

这个规则最多证明“该接收者在名义窗口内未解码到 MAVLink 消息”。它不检查：

- SITL/PX4 进程是否退出；
- exit code、signal、异常类型、core 或 stack；
- 网络/UDP 端口是否改变；
- sysid/compid 是否改变；
- heartbeat 是否缺失但其他消息仍在；
- 接收线程是否被另一线程抢走消息。

公开代码却把结果保存为 `ArithmException`；该名称不能提供算术异常证据。论文 Appendix A 也指出修改 `SYSID_THISMAV` 会造成观测通道断开并产生误报。

若 benchmark 将来需要“消息静默”性质，应另从 MAVLink/飞控官方 heartbeat 或 stream-rate 文档提取，并把它定义为通信可观测性质，而不是 software crash 的充分条件。

## 7. 并发观测对三类判定的影响

ArduPilot 和 PX4 的静默线程、route 线程会并发调用同一个 `oracle_master.recv_match()`，状态分发线程再消费队列。route 线程可能取走并丢弃状态消息，静默线程也可能抢走 route 所需消息。因此各判定器的实际观测不是独立、无丢失的消息流。

证据：[`fuzz.py:252`](../../baseline/ADGFuzz/fuzzer/fuzz.py#L252)、[`fuzzpx4.py:235`](../../baseline/ADGFuzz/fuzzer/fuzzpx4.py#L235)。

这会使“连续 N 次”“T 秒无消息”依赖线程调度。迁移任何规则前必须建立单一接收/分发点、保存 sender timestamp 与 arrival timestamp，并对消息缺失输出 `INCONCLUSIVE`，而不是自动判违反。

## 8. 其他时间值的分类

| 数值 | 所在用途 | 来源 | 是否为系统性质 |
|---|---|---|---|
| 50–500 次/MIS | fuzzing energy | 论文称 empirical observations | 否 |
| post-processing `τ` | 输入序列重放/最小化等待 | 论文称按类别经验确定；多数未给值 | 否 |
| 60 s | 重启后等待 | harness sleep | 否 |
| 5/8/10/20 s | 起飞、启动、模式准备等待 | harness sleep | 否 |
| 末轮 5 s | 观察等待 | harness | 否 |
| 24 h | campaign budget | 实验设置 | 否 |
| Table IV 中约 1–2 s/数秒 | 特定输入后观察到的表现 | 个案观察 | 否；不是 oracle 阈值 |

代码中的 `check_position_error > 10`、姿态角 `>1.0`、`rv_alive(timeout=1)`、`position_threshold=10` 等不在活动的三 oracle 调用链，也不能被当作论文规则。

## 9. 当前 benchmark 的采用规则

每一条 ADGFuzz 相关记录必须区分：

- `paper_rule`
- `readme_rule`
- `artifact_rule`
- `official_current_requirement`（若找到）
- `selected_interpretation`
- `selection_reason`

且至少保存：

1. 规则分类：`AUXILIARY_ORACLE`、`HEURISTIC_FILTER`、`EXPERIMENT_BUDGET`、`REPLAY_DELAY` 或当前官方 requirement；
2. 原始值、单位、归一化值、完整派生式、来源与未知操作数；
3. 起止/重置事件、clock domain、timestamp carrier、采样抖动；
4. 车型、任务阶段、mode、airborne、当前 waypoint 与合法例外；
5. MAVLink 消息/字段/枚举/单位与 freshness；
6. 当前 SUT 源码绑定；ADGFuzz Python 位置另列；
7. 观测竞争、丢包和 `INCONCLUSIVE` 规则。

## 10. 可复核命令

```bash
sha256sum "/mnt/c/Users/PC-123/Zotero/storage/X8VTAKST/Wang 等 - 2026 - ADGFUZZ Assignment dependency-guided fuzzing for robotic vehicles.pdf"
git -C /home/lqq/project/TAFuzz/baseline/ADGFuzz rev-parse HEAD
nl -ba /home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py | sed -n '100,140p;205,290p;320,415p'
nl -ba /home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py | sed -n '240,360p'
nl -ba /home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzzpx4.py | sed -n '225,335p'
```

## 11. 未决证据

- `2 s`、示例 `7 s`、README 的 `5 s/3` 与 `12 s/7`、代码的 `12 s/9`、`1 m`、`0.05 m/4` 均无公开原始校准数据。
- 论文所称 runtime-log ground detection 在公开 Python 实现中没有对应证据。
- artifact VM 可能不同于公开仓库，但当前没有可审计版本身份。
- PX4 的聚合结果没有逐条轨迹与阈值校准。
- 三类判定器均未提供当前 ArduPilot/PX4 内部变量/函数绑定；这部分必须针对冻结源码独立完成。

