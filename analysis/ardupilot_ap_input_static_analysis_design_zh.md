# ArduPilot 中影响 MTL 原子命题的输入：静态分析方法调研与落地设计

更新时间：2026-07-23  
状态：方法调研与设计完成；尚未生成当前整程序 LLVM IR，尚未在真实 ArduPilot 上运行本文方案

## 1. 结论先行

当前最合适的路线不是完整程序依赖图、符号执行，也不是 ADGFuzz 的名称匹配赋值链，而是一个单一的、分层实现的方法：

> **AP 锚定的分层后向影响切片**：以 MTL 原子命题的实现观测点为终点，使用 SVF 3.2 的跨过程稀疏值流从终点向后追踪；只在已命中的函数内补控制依赖；再用一小组有源码证据、随 ArduPilot 版本冻结的语义桥，补齐 MAVLink 解码、参数注册、调度回调和“事件停止发生”这类 LLVM 值流无法表达的关系。

这里的 **AP（Atomic Proposition，原子命题）** 是 MTL/MITL 公式中一次采样即可判真或判假的最小条件，例如 `failsafe_gcs = true` 或 `high_vibes = true`。**MTL（Metric Temporal Logic，度量时序逻辑）** 和 **MITL（Metric Interval Temporal Logic，度量区间时序逻辑）** 用带时间区间的逻辑算子描述执行轨迹。

该方法只回答：

```text
哪些外部输入可能影响这个 AP？
程序结构上经过了哪些数据、内存、调用、控制或语义桥？
这条候选关系有多少静态不确定性？
```

它不回答：

```text
输入增大还是减小会使 AP 为 true？
某个输入在当前飞行状态下一定能改变 AP 吗？
输入后多少秒一定触发 AP？
MTL/MITL 性质最终满足还是违反？
```

因此，静态分析输出的是后续 fuzz 的**候选输入集合和冷启动 cost 先验**，不是最终边触发难度。`p` 与 `!p` 在静态阶段使用相同先验；方向和真正的整条布尔边 `false -> true` 成功率留给后续动态测试校准。

## 2. 当前工程边界

### 2.1 已验证的可用基础

- 当前 ArduPilot 冻结提交为 `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`；既有 `modules/CrashDebug` 状态必须保留。
- 已有 Copter-only 的 Clang 18 编译数据库快照，共 1,336 个翻译单元；其原构建目录位于历史 `/tmp` 路径，所以使用前必须重建可追溯的当前 LLVM IR。
- 本地已冻结并构建 SVF 3.2，提交为 `197a6590bd9c695a9c3daf52622dea912ef9a002`。最小用例已验证 Andersen 指针分析、MemorySSA 和完整 SVFG 能运行。
- **LLVM IR（LLVM Intermediate Representation，LLVM 中间表示）** 是 Clang 把 C/C++ 源码降低后的统一程序表示。
- **SVFG（Sparse Value-Flow Graph，稀疏值流图）** 把普通 SSA 值、内存定义—使用、实参与形参、返回值等关系组织成可遍历的跨过程值流图。
- **MemorySSA（Memory Static Single Assignment，内存静态单赋值）** 把内存写入和读取组织成定义—使用关系，用于补足普通寄存器 SSA 无法追踪的对象字段和指针读写。

本地证据：

- [ArduPilot Clang 18 构建清单](/home/lqq/project/TAFuzz/benchmark/rift/reproduction/ardupilot/build_manifest.json)
- [SVF 3.2 复现记录](/home/lqq/project/TAFuzz/benchmark/rift/reproduction/svf/README.md)
- [现有静态基线说明](/home/lqq/project/TAFuzz/benchmark/rift/baselines/README.md)

### 2.2 当前不可直接使用的材料

- `baseline/pgfuzz/SVF-data-flow/copter_4_1_llvm_13.bc` 虽然后缀为 `.bc`，实际是旧 LLVM 13 文本 IR，不能代表当前提交。
- 当前六种静态基线只在微型、预先给定 source×AP 锚点的机械数据集上评估，不能外推为真实 ArduPilot 的准确率。
- 当前工作区没有完成“外部输入自动发现 + 当前 AP 自动绑定 + 完整 ArduPilot 值流”的真实运行。

## 3. 近年来相关方法的比较

### 3.1 术语图例

- **SSA（Static Single Assignment，静态单赋值）**：每个中间变量只有一个定义，适合直接追踪寄存器值，但不自动解决内存别名。
- **pointer/points-to analysis（指针/指向分析）**：估计一个指针可能指向哪些对象，是 C/C++ 跨对象字段追踪的基础。
- **value-flow analysis（值流分析）**：追踪一个值经赋值、内存、调用与返回传播到其他位置的可能路径。
- **program slicing（程序切片）**：保留与某个目标点相关的语句或图节点；本任务采用从 AP 向后的切片。
- **control dependence（控制依赖）**：一个分支条件决定某条赋值、调用或状态提交是否执行。
- **PDG（Program Dependence Graph，程序依赖图）**：同时表示数据依赖和控制依赖。
- **IFDS/IDE（Interprocedural Finite Distributive Subset / Interprocedural Distributive Environment，跨过程有限分配子集/跨过程分配环境）**：用于求解一类跨过程数据流问题的通用框架。
- **CPG（Code Property Graph，代码属性图）**：把语法、控制流和数据流组合为统一可查询图。
- **directed greybox fuzzing（定向灰盒模糊测试）**：利用轻量程序反馈把测试集中到指定代码目标或状态附近。

### 3.2 方法评估表

| 方法 | 能解决什么 | 主要优点 | 对当前任务的缺点 | 裁决 |
|---|---|---|---|---|
| 名称/赋值依赖图，如 ADGFuzz | 函数内赋值链、按变量名映射输入 | 快，容易实现，适合高召回候选 | 漏跨函数、别名、对象字段、控制、调度和事件；名称相似不等于影响 | 只作弱基线或候选补充 |
| 调用图/CFG 距离，如 AFLGo | 当前代码位置到目标代码位置的距离 | 适合定向到基本块 | 不能回答哪个输入影响 AP；短代码距离不等于容易改变布尔条件 | 后续同组候选排序可用，不能作主分析 |
| 纯 LLVM SSA def-use | 局部直接数值传播 | 简单、精确、速度通常可控 | `store/load`、对象字段、别名和控制依赖大量缺失 | 只作单元构件 |
| MemorySSA + 基础别名 | 函数内或有限范围的内存定义—使用 | 比纯 SSA 更接近 C++ 状态字段 | 单独使用时跨过程、虚调用和控制语义不够 | 只作单元构件 |
| 全程序 PDG/SDG | 数据和控制依赖统一切片 | 表达力全面 | 全 ArduPilot 上图大、上下文污染明显，工程和调参成本高 | 不做全量；只做局部控制覆盖层 |
| SVF 稀疏值流 | 跨过程 SSA、内存、别名、调用与返回 | 当前本地已有、LLVM 适配好、路径证据可导出 | 不自动表示事件缺失、调度、物理反馈和 MTL 时间语义 | **v1 主引擎** |
| PhASAR IFDS/IDE | 自定义事实、状态和跨过程求解 | 很适合研究型定制分析 | 要设计流函数、格值、调用摘要和路径证据；v1 工程量偏大 | 后续局部交叉验证，不作 v1 主干 |
| CodeQL 全局数据流 | 以 source/sink 查询快速显示源码路径 | 交互审计方便，路径展示成熟 | ArduPilot 领域模型仍需手写；数据库和查询不适合作为当前自动 cost 核心 | 人工探索辅助 |
| Joern CPG | 源码级语法/控制/数据统一查询 | 不要求完整成功构建时也便于侦察 | C++ 模板、宏、虚调用和类型恢复可能产生噪声；不是当前编译产物事实 | 人工侦察辅助 |
| DFI 等新型可扩展值流 | 面向大型程序降低内存和运行时间 | 2023 年工作显示很强的扩展性潜力 | 当前工作区无成熟集成、验证和模型资产；迁移风险高于收益 | 跟踪研究，暂不采用 |
| 稀疏 IDE | 减少通用 IDE 求解中的无关流传播 | 2024 年工作表明可降低部分分析开销 | 主要实现与评估生态不直接面向当前 LLVM/ArduPilot 流程 | 暂不采用 |
| 符号执行/抽象执行 | 可推理数值条件和部分路径约束 | 理论上可能接近方向与可达性 | 飞控循环、浮点、虚调用、外部模型和状态空间导致建模及路径爆炸 | 不作输入发现 v1 |

关键资料均采用论文、官方文档或官方仓库：

- [SVF 官方能力说明](https://svf-tools.github.io/SVF/)
- [SVF 官方仓库](https://github.com/SVF-tools/SVF)
- [LLVM Program Dependence Graph 官方文档](https://llvm.org/docs/DependenceGraphs/)
- [Clang 数据流分析官方介绍](https://clang.llvm.org/docs/DataFlowAnalysisIntro.html)
- [PhASAR 官方仓库](https://github.com/secure-software-engineering/phasar)
- [CodeQL C/C++ 数据流官方文档](https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-cpp/)
- [Joern CPG 官方文档](https://docs.joern.io/code-property-graph/)
- [DFI：面向大型代码库的跨过程值流框架，CGO 2023](https://arxiv.org/abs/2209.02638)
- [Sparse IDE：符号特定稀疏化，2024](https://arxiv.org/abs/2401.14813)
- [ADGFuzz 官方 NDSS 2026 论文页](https://www.ndss-symposium.org/ndss-paper/adgfuzz-assignment-dependency-guided-fuzzing-for-robotic-vehicles/)
- [CSFuzz 官方 ICSE 2025 论文页](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/182/Critical-Variable-State-Aware-Directed-Greybox-Fuzzing)
- [CFPOFuzz 官方 ICSE 2026 论文页](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/231/Context-Free-Property-Oriented-Fuzzing)

## 4. 唯一推荐方法：AP 锚定的分层后向影响切片

它不是并排运行多个工具后投票，而是在一个带类型的影响图上分层补充不同语义。

### 4.1 输入 source 的定义

**source（源点）** 在本任务中不是 UDP 字节读取函数，而是 fuzzer 能表达和重放的结构化外部动作：

1. MAVLink 消息解码后的 `(message_id, field)`；
2. `AP_Param` 参数的 `(parameter_name, typed_value)`，包括 `SIM_*`；
3. RC 通道或规范化 RC 控制值；
4. mission item、command 和 mode action 的字段；
5. SITL 环境或传感器模型参数；
6. 事件动作，例如“发送 HEARTBEAT”“停止 HEARTBEAT”“延迟下一条消息”。

前五类可以绑定到数据值；第六类必须作为事件 source 保留，不能强行伪装成一个普通整数变量。

source 目录必须至少包含：

```text
input_id
action_kind
protocol/parameter identity
type and unit
IR/source anchor
runtime writable scope
required mode/state if already known
provenance commit and file location
```

### 4.2 AP sink 的定义

**sink（汇点）** 是静态分析反向追踪的终点。一个 AP 必须先有明确的实现观测绑定：

- 若 AP 在飞控源码中已有布尔提交点，例如 `failsafe.gcs = b`，sink 是该布尔状态写入或产生它的条件值；
- 若 AP 是监视器中的外部比较，例如 `altitude < 5m`，sink 不是监视器代码，而是 `altitude` 的主观测值在飞控中的生产/发布点；常数 `5m` 属于性质，不进入飞控反切；
- 若 AP 有多个非恒定操作数，分别建立 sink，最后在 AP 绑定层保留原布尔组合；
- 若主观测值、对象、单位或有效性没有解决，状态必须是 `UNRESOLVED_BINDING`，不得自动猜一个变量。

### 4.3 统一影响图

建立有向图：

\[
G=(V,E)
\]

节点 `V` 只保留以下类型：

```text
EXTERNAL_INPUT       结构化外部输入或事件
IR_VALUE             LLVM SSA 值或 SVFG 节点
MEMORY_OBJECT        对象/字段的抽象内存位置
BRANCH_PREDICATE     控制条件
CALL_BOUNDARY        实参、形参、返回值、间接调用
MODEL_BOUNDARY       调度、事件缺失或 SITL 边界
AP_OPERAND           AP 的实现观测操作数
```

边 `E` 只保留以下类型：

| 边类型 | 精确定义 | 不能解释成什么 |
|---|---|---|
| `MUST_DATA` | 当前编译 IR 中显式 SSA、实参/形参、返回值，或唯一对象上的确定内存定义—使用 | 不表示运行时一定执行，更不表示一定改变 AP |
| `MAY_DATA` | 保守别名、多个潜在对象、未唯一解析的虚调用所产生的可能值流 | 不表示已证明因果 |
| `CONTROL` | 某分支条件控制一个已在值流切片中的状态写入、调用或 AP 提交 | 不表示该条件的值直接成为 AP 数值 |
| `MODELLED` | 有版本化源码证据的 ArduPilot 语义桥 | 不表示通用静态工具自动推导 |
| `UNKNOWN` | 外部库、内联汇编、未解析回调、预算截断或缺失模型造成的断点 | 不得当作无影响 |

`MUST_DATA` 中的 `MUST` 仅表示“这条抽象值流边的对象解析是确定的”，不是“这个外部输入必然触发 AP”。一条候选路径只要经过 `MAY_DATA`、`MODELLED` 或 `UNKNOWN`，最终就不能标成纯 `MUST_DATA`。

### 4.4 反向算法

第一版算法如下：

```text
输入：
    当前提交及当前构建配置的 LLVM IR
    已冻结的 external_input_catalog
    一个 AP 的一个或多个 sink
    ArduPilot semantic_bridge_pack

1. 用 SVF 3.2 构造 AndersenWaveDiff、MemorySSA 和完整 SVFG。
2. 从 AP sink 对应的 SVFG 节点反向遍历：
       收集 SSA、内存、调用、返回和别名路径。
3. 识别反向切片命中的“状态写入、关键调用和 AP 提交”所在基本块。
4. 只在这些函数中用后支配关系计算控制依赖：
       加入控制这些基本块的分支条件；
       再从分支条件操作数做一次反向值流扩展。
5. 对新增切片函数重复第 3--4 步，直到稳定或达到明确节点预算；
       达到预算则标记 TRUNCATED，不删除已找到候选。
6. 将 semantic_bridge_pack 加入图：
       external input -> decoder/parameter/scheduler/event/model anchor。
7. 当反向路径到达 external input 时，导出最短证据路径和所有替代来源摘要。
8. 所有 UNKNOWN 和未匹配边界均进入输出；排序可以降级，禁止静默裁剪。
```

这样做比全程序 PDG 更省：控制依赖只在值流已经证明“与 AP 有结构关系”的局部区域扩展；又比纯 SVF 完整，因为 `type_mask`、启用开关、armed、模式和超时判断等控制门不会被漏掉。

第一版采用路径不敏感、轻上下文策略。调用和返回必须基本配对，防止明显的跨调用污染；不实现完整 k-CFA、全路径条件求解或上下文敏感流敏感指针分析。

### 4.5 ArduPilot 最小语义桥包

**semantic bridge（语义桥）** 是“通用 LLVM 图无法自然表达，但有明确 ArduPilot 源码模式支持”的版本化边。v1 只做五类：

1. `MAVLINK_DECODE`：外部 `(msgid, field)` 到生成解码函数后的 `packet.field`；
2. `AP_PARAM_BINDING`：外部参数名及值到 `AP_GROUPINFO/AP_SUBGROUPINFO` 注册的对象字段；
3. `SCHEDULER_CALLBACK`：调度表中的任务函数指针到周期回调；
4. `EVENT_ABSENCE_TIMER`：某消息/事件更新 `last_seen`，而 `now-last_seen > timeout` 触发状态时，引入“停止/延迟该事件”的外部动作候选；
5. `SITL_SENSOR_BOUNDARY`：`SIM_*` 参数到模拟传感器样本注入位置；其后的物理、滤波或跨进程传播如果没有普通值流证据，保持 `MODELLED` 或 `UNKNOWN`。

每条桥必须记录：匹配的源码模式、文件/行、适用提交、输入身份、桥两端节点和人工审核状态。不得建立“输入名像变量名，所以连接”的桥。

## 5. 静态输出 schema

建议每个 `input -> AP` 候选输出一条 JSON 记录。**JSON（JavaScript Object Notation，JavaScript 对象表示法）** 是用于机器读取的键值文本格式。

```json
{
  "schema_version": "tafuzz.ap-impact.v1",
  "source_freeze": {
    "commit": "8f2e5db2...",
    "compile_db_sha256": "...",
    "ir_manifest_sha256": "..."
  },
  "input": {
    "id": "PARAM:SIM_VIB_FREQ",
    "kind": "AP_PARAM",
    "type": "Vector3f",
    "unit": "Hz",
    "anchor": "libraries/SITL/SITL.cpp:326"
  },
  "ap": {
    "id": "AP_HIGH_VIBES",
    "binding_status": "BOUND",
    "sink": "ArduCopter/ekf_check.cpp:303"
  },
  "relation": "MODELLED",
  "analysis_status": "ANALYZED",
  "path_summary": {
    "semantic_segments": 9,
    "must_data": 5,
    "may_data": 1,
    "control": 3,
    "modelled": 1,
    "unknown": 0
  },
  "evidence_path": [
    {"kind": "MODELLED", "from": "PARAM:SIM_VIB_FREQ", "to": "SITL::vibe_freq"},
    {"kind": "MUST_DATA", "from": "SITL::vibe_freq", "to": "simulated_accel"},
    {"kind": "CONTROL", "from": "motors_on", "to": "vibration_injection"}
  ],
  "prerequisites": ["MOTORS_ON", "FS_VIBE_ENABLE", "NON_MANUAL_THROTTLE"],
  "clock_context": ["AP_HAL::millis", "10Hz check", ">1000ms persistence"],
  "static_features": {
    "weighted_structural_distance": 18,
    "uncertainty_class": "MODELLED",
    "prior_status": "AVAILABLE",
    "provisional_cost": 5
  },
  "limitations": [
    "NO_TRUTH_DIRECTION",
    "NO_RUNTIME_REACHABILITY",
    "NO_TIMING_GUARANTEE",
    "NO_CONFORMANCE_CLAIM"
  ]
}
```

### 5.1 聚合状态规则

- `ANALYZED`：在预算内完成了全部已建模图遍历；不等于关系为真。
- `TRUNCATED`：达到时间、内存或节点预算；保留已有候选并加 `UNKNOWN`。
- `UNRESOLVED_BINDING`：AP 的实现观测点本身未解决，禁止计算正式先验。
- `NO_STATIC_PATH`：在当前模型和构建中没有发现路径；不能写成“输入绝对无影响”。

## 6. 如何为后续 cost 做准备

### 6.1 为什么不能直接用 LLVM 边数

路径越长不一定越难触发：

- 内联与优化会改变 IR 指令数，但不会改变外部动作难度；
- 一条很长的赋值/单位换算链可能由一个参数直接控制；
- 一条很短的控制边可能要求特定模式、armed、持续时间和多个条件同时成立；
- SITL 物理反馈、滤波和调度延迟不在普通值流边数中；
- 静态路径不知道阈值当前差多少，也不知道输入应增大还是减小。

因此保存原始特征向量比只保存一个数字更重要。

### 6.2 稳定的语义段距离

先折叠同一函数内连续的普通 SSA 边，避免编译器把一个表达式拆成多少指令直接主导距离。对路径 `P` 保存：

\[
Q(P)=
n_{must}
+2n_{may}
+2n_{control}
+3n_{model}
+4n_{unknown}
+\left\lceil\log_2(1+a+i)\right\rceil
\]

各项都是**语义段**数量：

- `must`：确定的 SSA、调用/返回或唯一对象内存段；
- `may`：一个保守别名、多个到达定义或未唯一解析虚调用段；
- `control`：一个独立控制门；
- `model`：一个人工审核语义桥；
- `unknown`：一个没有被当前模型闭合的缺口；
- `a`：额外别名候选数；
- `i`：额外间接调用候选数。

权重 `1/2/3/4` 只表达证据从直接到不确定的序关系，不声称物理难度比例。先按 `(n_unknown, Q)` 字典序选路径，使无未知缺口的完整路径优先于“很短但断掉”的路径；同时保留替代路径和完整计数。

### 6.3 1--8 的临时静态先验

若后续调度器在动态数据尚为空时必须要一个整数，可用：

\[
C_s(x,a)=
\begin{cases}
\text{UNKNOWN}, & n_{unknown}>0\text{ 或分析被截断}\\
\operatorname{clip}_{[1,8]}
\left(\left\lceil\log_2(1+\min_P Q(P))\right\rceil\right), & \text{其他情况}
\end{cases}
\]

这里 `x` 是结构化输入，`a` 是 AP。对 `a` 与 `!a`：

\[
C_s(x,a)=C_s(x,!a)
\]

该公式的对数压缩避免超长实现链把 cost 拉得过大。`UNKNOWN` 必须与数值 8 分开：前者表示证据不完整，后者才表示在完整静态路径中结构先验较高。调度器应为 `UNKNOWN` 保留独立探索份额，不能把它解释成“已证明很难”。

若需要给自动机布尔边一个临时先验，先把守卫限制性地展开为最小满足子句；正文字和负文字都只使用 AP 身份，不推断方向。对于每个子句，寻找能覆盖其中 AP 的最小结构化 action 集合：同一个 action 若可能影响多个 AP，只计一次。

v1 只枚举最多两个 action，并限制子句数；超过上限、只能靠 `UNKNOWN` 覆盖或布尔展开被截断时，边的 `prior_status` 设为 `UNKNOWN`。这比直接相加 AP cost 更合理，因为一个 MAVLink 字段或参数可能同时影响多个 AP，也避免把复杂布尔公式展开成无界工程。

这只是冷启动规则。正式 fuzz 应以完整边条件的动态 `false -> true` 结果校准并冻结最终边权，再反向计算自动机剩余代价。

## 7. 两条 ArduPilot 链如何被分析

### 7.1 振动保护

当前源码可核查的关键点：

1. `SIM_VIB_FREQ` 注册到 `SITL::vibe_freq`：[SITL.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/libraries/SITL/SITL.cpp:321)
2. 仅在 `motors_on` 且频率非零时向模拟加速度加入振动：[AP_InertialSensor_SITL.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_SITL.cpp:131)
3. `bad_vibe_detected` 由创新量、方差或 AHRS 振动状态组合产生；动作还受 `FS_VIBE_ENABLE`、armed 和非手动油门控制：[ekf_check.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduCopter/ekf_check.cpp:266)
4. 条件持续严格超过 1000 ms 后才写 `high_vibes=true`，清除需严格超过 15000 ms。

算法能找到：

- `SIM_VIB_FREQ` 是主要数据候选；
- `motors_on` 是振动注入的控制前提；
- `FS_VIBE_ENABLE`、armed、manual-throttle/mode 是状态提交的控制候选；
- `AP_HAL::millis`、`start_ms` 和 `>1000` 是时间前提；
- AHRS/EKF 虚调用、滤波和不同后端会引入 `MAY_DATA` 或 `UNKNOWN`。

算法找不到或不能断言：

- 哪个频率/幅值必然让创新量越过阈值；
- 在某姿态、噪声和马达状态下 AP 是否一定翻转；
- 输入后恰好 1 秒触发；10 Hz 调度点和严格 `>` 会影响可观测时间；
- `SIM_VIB_FREQ` 应增大还是减小。

### 7.2 GCS 失联保护

当前源码链：

1. 合法 GCS 的 HEARTBEAT 到达后，`handle_heartbeat` 调用 `sysid_mygcs_seen(AP_HAL::millis())`：[GCS_Common.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:4357)
2. `failsafe_gcs_check` 读取 last-seen，并比较 `millis()-last_seen` 与超时参数：[events.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduCopter/events.cpp:125)
3. 超时且尚未触发时调用 `set_failsafe_gcs(true)`：[AP_State.cpp](/home/lqq/project/TAFuzz/baseline/ardupilot/ArduCopter/AP_State.cpp:73)

纯 SVF 能找到：

- `FS_GCS_TIMEOUT` 参数到超时比较的值流；
- `last_seen` 对象字段到超时比较的内存值流；
- 比较结果控制 `set_failsafe_gcs(true)`；
- AP sink `failsafe.gcs` 的最终写入。

`EVENT_ABSENCE_TIMER` 语义桥补充：

- `HEARTBEAT.received` 更新 last-seen；
- 要让 elapsed time 增长，fuzzer 的可执行候选是 `HEARTBEAT.withhold/delay`，而不是把 last-seen 伪装成可直接写的输入。

算法仍必须报告：

- `MANUAL_CONTROL` 也可能刷新同一 last-seen，停止 HEARTBEAT 并不必然使计时继续；
- GCS 身份检查是前提；
- 检查周期会引入额外调度延迟；
- 静态分析不证明这次暂停一定触发性质边。

## 8. 分阶段实现与验收

### M0：当前构建 IR 冻结

任务：使用当前提交和 Copter SITL 配置，在隔离构建目录重建 Clang 18 编译闭包和带源码位置的 LLVM IR；从真实链接闭包生成模块清单。

验收：

- commit、配置、编译命令、IR 哈希和链接闭包均记录；
- 不使用旧 LLVM 13 文件；
- 不修改 ArduPilot 源码；
- 至少能由 SVF 加载并构造 ICFG、MemorySSA 和 SVFG。

### M1：source 目录和 AP sink 绑定

先选三类不同难度的 AP：

1. `mode == RTL`：验证直接命令/状态链；
2. `failsafe.gcs`：验证跨循环字段、参数和事件缺失桥；
3. `vibration_check.high_vibes`：验证对象、虚调用、控制前提和 SITL 边界。

验收：每个 source 和 sink 都有当前源码锚点、单位/类型、对象范围和冻结身份；未解决项输出 `UNRESOLVED_BINDING`。

### M2：SVF 反向值流

任务：实现 AP sink 到输入锚点的后向 SVFG 遍历和路径导出。

验收：

- 微型跨函数、对象字段、别名和虚调用测试可区分 `MUST_DATA/MAY_DATA`；
- 每条路径能回映源码位置；
- 真实 AP 至少导出值流候选或明确 `NO_STATIC_PATH/UNKNOWN`；
- 每个 AP 独立进程运行，避免 SVF 全局状态污染。

### M3：局部控制依赖

任务：只对 M2 命中的函数计算后支配控制依赖，并从控制条件反向追 source。

验收：

- 能在振动链识别 enable、armed、manual-throttle 和 motors-on；
- 数据候选与控制前提分列，不混为一个分数；
- 节点预算、截断位置和 `TRUNCATED` 可复现。

### M4：最小语义桥包

任务：实现五类桥，先完成 `AP_PARAM_BINDING`、`MAVLINK_DECODE` 和 `EVENT_ABSENCE_TIMER`。

验收：

- GCS 例子能输出 `HEARTBEAT.withhold`，同时列出 `MANUAL_CONTROL` 共享刷新冲突；
- 振动例子能输出 `SIM_VIB_FREQ`，但关系不高于 `MODELLED/MAY_DATA`；
- 每条桥均带匹配源码和版本。

### M5：人工金标准与静态先验

建立一个小而真实的审核集，不追求论文规模。建议 8--12 个 AP，覆盖：直接参数、MAVLink 命令、模式、RC、超时、SITL 传感器和物理状态。

验收指标：

- 已知相关输入的候选召回率；
- Top-3/Top-5 候选人工有效率；
- `MUST/MAY/CONTROL/MODELLED/UNKNOWN` 分类错误率；
- 分析时间、峰值内存、截断率；
- 输出路径可由源码复核的比例。

只有该阶段完成，才能选择是否调整语义段权重。微型基线结果不能当真实 ArduPilot 指标。

## 9. 失败模式与停止条件

| 失败模式 | 处理 |
|---|---|
| AP sink 语义不清 | 停止该 AP，输出 `UNRESOLVED_BINDING` |
| 旧 IR 或构建闭包不一致 | 停止运行，不混合不同提交/LLVM 版本 |
| 未解析虚调用或外部库 | 保留 `MAY_DATA/UNKNOWN`，不造路径 |
| 控制扩展爆炸 | 达到预算即 `TRUNCATED`，保留已有候选 |
| 事件缺失被误当标量 | 必须经 `EVENT_ABSENCE_TIMER`；无证据则 `UNKNOWN` |
| 物理/跨进程链断开 | 截止到明确模型边界，标 `MODELLED/UNKNOWN` |
| 只有名称相似而无值流/桥证据 | 可留作低优先探索候选，不进入 `MUST/MAY_DATA` |
| 静态 cost 与动态结果明显冲突 | 以动态完整布尔边结果校准；不得修改静态证据路径来迎合结果 |

若在前三个代表 AP 上出现以下任一情况，应暂停扩大范围：

- 当前 IR 无法稳定构造或内存超预算；
- Top-5 候选中绝大多数无法从源码解释；
- 局部控制扩展仍接近全程序规模；
- 语义桥数量迅速增长到每个 AP 都要特写规则。

此时应先缩小分析闭包或改进 source/sink 绑定，而不是直接上更重的符号执行或全 PDG。

## 10. 与已有工作的关系

- ADGFuzz 说明“静态依赖候选帮助缩小机器人载具输入空间”有实际价值；本文路线用编译级值流替代名称驱动的函数内赋值链。
- AFLGo 的目标距离适合后续衡量候选执行是否接近某代码点，但不能替代 input→AP 关系。
- CSFuzz 提示“目标附近关键变量状态”值得作为后续 seed 保留反馈；它不解决当前的外部输入发现。
- CFPOFuzz 已经把性质状态、静态/动态影响和距离结合用于性质导向 fuzz，因此 TAFuzz 的创新点不能只写成“静态依赖 + 动态反馈 + 状态距离”。更可信的差异应放在：结构化飞控动作、时间自动机边、事件缺失、飞控单调时钟、可审计语义桥和冻结后的反向剩余 cost。

## 11. 最终方法边界

本报告完成的是方法选择和可编码设计，不是方法实现。当前可支持的结论是：

```text
SVF 3.2 + 局部控制依赖 + 小型 ArduPilot 语义桥
是当前准确性、实现成本、可审计性和后续 cost 接口之间最合理的平衡。
```

当前不能支持的结论是：

```text
已经自动提取出当前全部 ArduPilot 输入到 AP 的关系；
已经测得真实静态准确率；
已经确定任意布尔边的最终 cost；
已经证明输入方向、时间边界或性质违反。
```

下一步应只做 M0 和 M1：重建当前可追溯 LLVM IR，并把三个代表 AP 的 source/sink 目录冻结。此后再进入 SVF 真实 ArduPilot 切片，而不是继续扩充理论框架。
