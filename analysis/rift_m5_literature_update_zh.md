# RIFT-M5 文献更新、创新碰撞与可移植 Frontier/Recipe 架构审计

> 状态：`RESEARCH_AND_ARCHITECTURE_AUDIT / PRE_M5_IMPLEMENTATION`
>
> 证据快照日期：2026-07-18（Asia/Shanghai）
>
> 审计对象：[`rift_preimplementation_comparison_zh.md`](./rift_preimplementation_comparison_zh.md)、
> [`rift_m4_architecture_freeze_zh.md`](./rift_m4_architecture_freeze_zh.md)、M4 core/schema，以及
> 用户给定的 RIFT-M5 目标。
>
> 本文件只给出文献与架构审计，不声称新增 artifact 已经复现，也不把论文原始数字当作
> RIFT 实验结果。

## 0. 结论先行

RIFT 的研究问题仍然成立，但经过 2024--2026 年方法更新后，创新边界必须显著收窄。
以下内容已经不能作为 RIFT 的单点创新：

- demand-driven、context/path-sensitive sparse value-flow；
- 声明式 source/sink/summary/barrier model pack；
- 从性质事件向控制条件切片；
- automaton/monitor state 驱动的输入优先级；
- target-related critical variables 与状态感知 fuzzing；
- branch constraint、gradient、SMT 或边界值驱动的 mutation direction；
- callback summary、对象参数化 monitor、调用前置序列生成；
- “为什么有流、为什么无流、改变模型后会怎样”的依赖解释。

最强的直接碰撞来自 ICSE 2026 的
[CFPOFuzz](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/231/Context-Free-Property-Oriented-Fuzzing)：
它已经把性质表示成 CFG/PDA，静态寻找性质事件相关控制条件，运行时维护对象参数化 monitor，
再用输入分块扰动、monitor state 和到接受状态的距离指导 mutation。其次，
[Falcon](https://doi.org/10.1145/3656400)、
[Tuna](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/141/Efficient-Strong-Updates-For-Path-Sensitive-Data-Dependence-Analysis)、
[CodeQL models-as-data](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-cpp/)、
[CSFuzz](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/182/Critical-Variable-State-Aware-Directed-Greybox-Fuzzing)、
[CGMiner](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.4) 和
[OGHARN](https://doi.org/10.1109/ICSE55347.2025.00239) 分别覆盖高精度值流、模型包、关键变量、
callback summary 和前置调用序列。

因此，M5 不应再被包装成“一个新的 slicer”。当前仍值得实现并验证的候选贡献是：

> **RIFT Temporal Action Frontier Contract（TAFC）**：从 typed MITL AP 的 trigger、response、
> cancel、guard、bound、clock、scope 等角色出发，在不裁剪 M4 保守影响锥的前提下，把程序内
> value/control/event/lifecycle witness 提升成外部测试动作；输出动作通道、payload slot、
> scope/generation、前置偏序、相对时间窗、关系型 mutation constraint，以及彼此独立的证据轴。

这项候选贡献与 CFPOFuzz 的根本任务差异应写成：

```text
CFPOFuzz：在当前 seed 中，哪一段 byte/input part 更值得变异？
RIFT-TAFC：哪一种外部语义动作能够改变这个 typed MITL AP，
           通过什么源码 witness，在什么 scope/lifecycle/time contract 下执行？
```

但这仍是 `PENDING_NOVELTY`，不是已经证明的“首创”。CodeQL 加定制模型、Falcon 类值流、
RESTler 类操作依赖和现有时序 fuzzing 可以组合出相近能力。只有完成更广的 collision search、
实现、统一基线和跨项目实证后，才能判断该完整合同是否形成足够根本的方法贡献。

可移植性必须是算法约束而不是口号：同一个 core binary/schema 只消费 typed Property IR、
Clang/LLVM 事实和版本化、property-independent model packs；执行器如何编码 MAVLink、CoAP、
socket 或 API call 必须放在 core 外的 adapter。ArduPilot 名称、路径、性质 ID、答案边或行号
不得进入 core。单项目跑通不构成可移植性证据。

---

## 1. 审阅边界与检索策略

### 1.1 为什么不能只搜“static slicing”

用户要找的不是一般变量相关性，而是可用于后续 fuzzing 的外部可控影响源。为避免由既有知识
限制搜索，本轮把问题拆成八个相邻领域：

| 检索领域 | 必须回答的问题 | 代表性一手来源 | 对 RIFT 的影响 |
|---|---|---|---|
| 稀疏值流、切片、taint | 如何在大型 C/C++ 中保持 context/path/object/field precision | [Falcon, PLDI 2024](https://pldi24.sigplan.org/details/pldi-2024-papers/24/Falcon-A-Fused-Approach-to-Path-Sensitive-Sparse-Data-Dependence-Analysis)、[Tuna, ICSE 2026](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/141/Efficient-Strong-Updates-For-Path-Sensitive-Data-Dependence-Analysis) | 底层值流不是创新；采用 demand-driven staged query |
| 抽象解释与符号执行 | alias、区间、路径条件如何互相精化；何时调用 SMT | [CSA, ICSE 2024](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/235/Precise-Sparse-Abstract-Execution-via-Cross-Domain-Interaction)、[Concrete Constraint Guided SE artifact](https://zenodo.org/records/10516325) | 只对 frontier witness 做分层约束，不做全程序符号执行 |
| source/sink 与可控性建模 | 如何声明外部边界、库 summary、guard/barrier | [CodeQL C/C++ global flow](https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-cpp/)、[C/C++ custom models](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-cpp/) | model pack 本身不是新意；必须加入动作、时序、生命周期合同 |
| async/event/lifecycle | callback、timer、queue、register/invoke 与执行顺序如何恢复 | [CGMiner, ECOOP 2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.4)、[Asynchronous JavaScript analysis, ECOOP 2019](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2019.8) | 采用显式 event/lifecycle facts；不能声称首次建 callback summary |
| temporal/property-guided fuzzing | monitor/automaton state 如何指导输入与事件 | [LTL-Fuzzer, ICSE 2022](https://doi.org/10.1145/3510003.3510082)、[CFPOFuzz, ICSE 2026](https://github.com/zbchen/CFPOFuzz)、[PGFuzz](https://doi.org/10.14722/ndss.2021.24096) | residual ranking 与 property guidance 已有先例；差异应落在语义 action frontier |
| directed/data-flow-sensitive fuzzing | 如何找关键输入、控制前置条件和 mutation direction | [CSFuzz, ICSE 2025](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/182/Critical-Variable-State-Aware-Directed-Greybox-Fuzzing)、[GREYONE](https://www.usenix.org/conference/usenixsecurity20/presentation/gan)、[Matryoshka](https://www.cs.ucdavis.edu/~hchen/paper/chen2019matryoshka.pdf) | 关键变量、taint、constraint distance、嵌套 guard 均不是新意 |
| 状态化 API 与 harness | 如何恢复 producer-consumer、初始化和操作序列 | [RESTler](https://www.microsoft.com/en-us/research/publication/restler-stateful-rest-api-fuzzing/)、[OGHARN artifact](https://zenodo.org/records/14727592) | prerequisite sequence 不是首次提出；RIFT 应输出偏序合同而非宣称新 harness generator |
| 依赖解释与可复用 summary | 如何让用户审计模型、why/why-not 和库摘要 | [WhyFlow, ICSE 2026](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/103/WhyFlow-Interrogative-Debugger-for-Sensemaking-Taint-Analysis)、[LibAlchemy, ICSE 2024](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/131/LibAlchemy-A-Two-Layer-Persistent-Summary-Design-for-Taming-Third-Party-Libraries-in) | `explain` 和 persistent summary 不是新意；证书必须具体到 AP-action contract |

### 1.2 证据规则

本轮只用论文作者 PDF、会议/出版方页面、官方 artifact、官方源码或官方工具文档支持事实。
搜索结果没有找到 artifact 时只写“本轮未定位到”，不能据此证明不存在。论文报告的精度、
速度或 bug 数只描述原论文设置，不能作为 RIFT 的横向实验结论。

针对 “MITL/MTL + source dependency + fuzzing” 的定向检索仍以 PGFuzz 为最接近的已审阅工作；
但检索未命中不构成新颖性证明。最终论文若使用 “to our knowledge”，必须公开数据库、query、
时间截点、纳入排除标准和 collision matrix，并在投稿前重新执行一次检索。

---

## 2. 最接近方法与根本差异

### 2.1 高精度 data-dependence：Falcon、Tuna、CSA、CSP

[Falcon](https://rainoftime.github.io/files/PLDI24.pdf) 先构建 context- 与 semi-path-sensitive 的
guarded/storeless value-flow graph，再按 client query demand-driven 地解析 fully path-sensitive
pointer/value-flow。论文在 16 个、13 KLoC 到 8 MLoC 的 C/C++ 程序上评价 thin slicing 和
value-flow bug finding。这直接否定“预计算稀疏图 + 按 AP 查询路径敏感依赖”本身的新颖性。

[Tuna](https://yiyuaner.github.io/files/icse26.pdf) 进一步把 heap strong update 分阶段处理：先用
must-kill 解决容易情况，只把剩余关系交给昂贵的 path-sensitive 推理。
[CSP, ICSE 2026](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/312/Fast-Flow-Sensitive-C-Program-Partitioning-via-Iterative-Value-Flow-Refinement)
也采用 sparse demand-driven pointer analysis，并在发现 partition conflict 后局部迭代精化。

[CSA](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/235/Precise-Sparse-Abstract-Execution-via-Cross-Domain-Interaction)
让地址域与区间域在线双向精化；其
[官方 artifact README](https://zenodo.org/records/10578637/files/README.pdf) 提供 Docker、快速测试和
自定义程序入口，但完整实验资源需求较高。

RIFT 的合理定位不是替代这些基础分析，而是作为 client：M4 给出保守 CIG/cone；M5 对
`external action -> AP` 的少量 witness 分阶段精化，并把结果提升为 temporal fuzz action。
若将 Falcon/Tuna/CSA 的技术重新实现，必须明确写成工程采用或适配，不能写成 RIFT 创新。

### 2.2 声明式 source/sink/model pack：CodeQL 已经覆盖通用形态

CodeQL C/C++ global data flow 已经定义 source、sink、barrier 和 additional flow step，并可输出
path query。[官方 C/C++ model 文档](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-cpp/)
允许在 YAML data extension 中声明 source、sink、summary、barrier 与 barrier guard，并记录
provenance；[GitHub 文档](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/query-packs)
明确区分 query、library 和 model packs。2026 年的
[官方更新](https://github.blog/changelog/2026-04-21-codeql-now-supports-sanitizers-and-validators-in-models-as-data/)
还把 validator/guard 声明纳入 models-as-data。

所以 M4 当前 `model_pack.schema.json` 的“selector + source/summary/event rule”是正确工程方向，
但不是论文贡献。RIFT 只有在以下增量同时成立并被评价时才可能形成差异：

- source 不是泛化 taint source，而是可执行器控制的 typed external action；
- witness 同时覆盖 value、control、event、lifecycle、scope、generation 和 clock；
- 输出不是 source-sink path，而是能够 replay 的 mutation relation、前置偏序和时间窗；
- 所有结论保留证据轴和 UNKNOWN，不把 modelled flow 误称为动态因果；
- pack 与 property 分离，同一规则可服务未见过的性质。

即使满足这些条件，贡献也应表述成“新的 temporal fuzzability client/contract”，而不是“首次
可扩展 source-sink 建模”。

### 2.3 最强 property-guided 碰撞：CFPOFuzz

[CFPOFuzz 论文](https://zbchen.github.io/files/icse2026.pdf) 与
[官方 artifact](https://github.com/zbchen/CFPOFuzz) 已经实现 C/C++ context-free
property-oriented fuzzing：性质事件被插桩，运行时使用 PDA/monitor；属性事件到相关 branch
condition 的关系由静态 interprocedural CFG/control dependence 获得；输入分块通过多次动态
扰动及 entropy-style influence 建图；当前 monitor state、可能事件与到接受状态距离参与输入
优先级。artifact 还展示以对象地址参数化不同 `std::stack` 实例。

这意味着 RIFT 不得声称：

- 首次从性质事件寻找控制条件；
- 首次使用对象参数化 temporal monitor；
- 首次根据 monitor/residual state 选择 mutation inputs；
- 首次把 property distance 与输入依赖结合。

两者仍有可检验差异：CFPOFuzz 的输入单位主要是具体 seed 的 byte/input part，依赖由动态
扰动发现；property event 和 instrumentation 由用户定义。RIFT-TAFC 计划从 typed MITL AP
反向发现尚未列出的参数、消息字段、时间动作和前置操作，并给出源码 witness、scope/generation
及 metric-time contract。CFPOFuzz 论文也把 runtime object precision、仅处理数值条件以及可用
更重 taint/symbolic analysis 改善精度列为边界。

这一区分必须通过共同 target 上的实验来证明，不能只靠文字：至少比较“发现的外部 action
exactness”“cold-start、尚无有效 seed 时的 Top-k actionability”“deadline mutation”和
“新增性质是否需要手工 event/input mapping”。若 CFPOFuzz 的动态 pilot 在相同预算内取得相同
或更好的 action map，RIFT 的静态 frontier 实用性主张即不成立。

artifact 的 quick demo 预计分钟级，但完整说明要求约 500 GB 空间，并报告 128 核、256 GB、
约 9600 core-hours 的完整复现设置。后续只允许把 demo 标为低成本门禁；完整比较必须固定
Docker image digest，不能继续依赖可漂移的 `latest` 标签。

### 2.4 target state 与 mutation direction：CSFuzz、Angora、SynFuzz、GREYONE、Matryoshka

[CSFuzz](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/182/Critical-Variable-State-Aware-Directed-Greybox-Fuzzing)
已经从 target site 静态提取 critical variables，在运行时监测其值，并自适应划分值域形成
state corpus。因此“从 AP 找关键变量，再按变量状态指导 fuzz”不是新颖点。

[Angora](https://angorafuzzer.github.io/) 使用 byte-level taint、context-sensitive branch count 和
gradient search；[SynFuzz](https://arxiv.org/abs/1905.09532) 用动态 taint、branch-condition synthesis
与 SMT 生成翻转分支的输入；[GREYONE](https://www.usenix.org/conference/usenixsecurity20/presentation/gan)
用 fuzzing-driven taint inference、constraint conformance 决定改哪些 byte、往哪个方向改；
[Matryoshka](https://www.cs.ucdavis.edu/~hchen/paper/chen2019matryoshka.pdf) 联合 control-dependent
和 data-flow-dependent nested conditions。

所以比较表达式、仿射关系、bitmask、SMT model、branch distance、UP/DOWN 或前置 guard 都不能
单独作为 RIFT 创新。RIFT 可验证的增量是把 solver model 映射回“参数设置、协议字段、消息丢失、
延迟、重复、重排或操作序列”等 typed action，并携带 MITL role/time/scope contract。

### 2.5 callback、lifecycle、序列与解释：CGMiner、RESTler、OGHARN、WhyFlow

[CGMiner](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.4) 动态采集 sample app
来生成可复用 callback call-graph summary；论文报告正确边比例超过 94%，集成 FlowDroid 后发现的
data flows 增加 40%。其
[DARTS artifact](https://doi.org/10.4230/DARTS.10.2.2) 和
[源码](https://github.com/Fraunhofer-SIT/ECOOP2024-DynamicCallbackSummaries/) 可用。虽然对象是
Java/Android，它足以否定“动态校准 callback summary”是 RIFT 首创。

[RESTler](https://github.com/microsoft/restler-fuzzer) 从 OpenAPI 推断 request producer-consumer
依赖并探索状态化 request sequences；
[OGHARN](https://zenodo.org/records/14727592) 从 C API header 生成候选 harness，再用编译、执行和
coverage oracle 筛选初始化、参数与调用序列。因此“自动生成前置操作序列”也不是 RIFT 首创。
RIFT 的不同点应是从 AP witness 得到必要的**偏序合同**，而不是生成一个完整 harness；具体
编码与合法化可以交给 OGHARN-style executor adapter。

[WhyFlow](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/103/WhyFlow-Interrogative-Debugger-for-Sensemaking-Taint-Analysis)
支持对 source-sink 流提出 why、why-not 和 what-if，并分析 third-party model 对连接性的影响。
因此 `tafuzz-sa explain` 也不能宣称首次解释 taint/value-flow；它应聚焦“这个 external action
为何可能改变此 typed AP、证据在哪一层不完整、下一次 replay 应验证什么”。

### 2.6 方法碰撞总表

| 方法 | 已覆盖能力 | 与 RIFT 的直接碰撞 | RIFT 仅剩的可检验差异 | Artifact 状态（本轮） |
|---|---|---|---|---|
| Falcon / Tuna / CSP | demand-driven、path/context-sensitive sparse dependence、局部精化 | 值流核心算法 | temporal action client 与证据合同 | 未定位到官方可运行 artifact；只作方法基线 |
| CSA | value-flow 与 interval domain 双向精化 | 多域抽象 + sparse analysis | 只对 AP-action witness 求关系型 recipe | [Docker artifact](https://zenodo.org/records/10461661)，重型候选 |
| CodeQL | global flow、path、sources/sinks/summaries/barriers、model packs | 声明式模型与 source-sink discovery | event/lifecycle/time/action contract | 官方 CLI/文档可用；应新增强基线 |
| LibAlchemy | 可持久化两层库 summary | reusable library summary | property-role/action-specific消费 | 本轮未定位官方 artifact |
| CFPOFuzz | property automaton/PDA、对象 monitor、静态控制依赖、动态输入 influence、property-state ranking | 几乎全部“性质驱动输入优先级”表述 | typed MITL 到未知 semantic action、scope/time contract | [官方 Docker artifact](https://github.com/zbchen/CFPOFuzz)，必须跑 demo |
| CSFuzz | target-related critical variables、runtime state corpus | AP-related variables、状态感知 fuzz | external action frontier、metric time、证据 | 本轮未定位官方 artifact |
| LTL-Fuzzer / PGFuzz | temporal property guidance、MTL distance、输入空间缩减 | temporal guidance 与 residual distance | 自动 action discovery 与源码 witness | 既有 M0 artifact 状态沿用 |
| ProtocolGuard | 规则相关 handler 切片、动态验证 | property/rule-guided slice + verification | 继续反向到 external action contract | [官方仓库](https://github.com/songxpu/ProtocolGuard)，既有审计为部分可用 |
| CGMiner | 动态生成 callback summaries | callback 模型自动校准 | C/C++ typed handle/scope/generation/time facts | 官方 artifact 可运行候选，但语言不同 |
| RESTler | producer-consumer 与状态化 request sequence | prerequisites 与操作序列 | 从源码 AP witness 生成偏序、而非只从接口规范 | 官方源码/Docker 可用 |
| OGHARN | C API 初始化与调用序列生成 | harness/prerequisite inference | RIFT 只输出 AP-specific abstract obligations | [Zenodo artifact](https://zenodo.org/records/14727592) 可运行候选 |
| Angora/SynFuzz/GREYONE/Matryoshka | input-byte influence、constraint solving、direction、nested guards | mutation direction 和 path feasibility | 映射成 semantic action + MITL timing | 多个作者/官方实现可用；按子能力比较 |
| WhyFlow | why/why-not/what-if taint explanation | explainability | AP-action proof ledger 和 replay obligation | 本轮未定位官方 artifact |

---

## 3. 创新碰撞红线

### 3.1 `RED`：不得作为新颖性主张

以下表述必须从论文贡献列表中删除：

1. “首次 demand-driven/path-sensitive/context-sensitive 地提取依赖”；
2. “首次把 static slicing 用于 property-guided fuzzing”；
3. “首次使用 automaton/residual state 排序 fuzz inputs”；
4. “首次从 target/AP 提取 critical variables”；
5. “首次使用双向 source-sink reachability/meet-in-the-middle”；
6. “首次用 SMT 推导 branch/mutation direction”；
7. “首次声明式建模外部输入、库 summary 或 guard”；
8. “首次建模 callback、timer、queue 或 lifecycle”；
9. “首次生成初始化、producer-consumer 或 prerequisite sequence”；
10. “首次提供依赖路径解释”。

其中第 5 项尤其容易误判。`BackwardCone(AP) ∩ ForwardReach(Source)` 是通用 source-sink
reachability 的实现形式；它可以显著改善工程精度，但不是独立算法创新。

### 3.2 `YELLOW`：可能形成组合贡献，但必须做 collision 与消融

以下组合尚值得验证，但不能预先写成结论：

- typed MITL 多角色联合绑定后，自动恢复 external semantic actions；
- value/control/event/lifecycle/scope/generation/clock 的统一 witness；
- 对 external action 与 AP 做两副本 truth-change relational query；
- 输出前置偏序和相对 deadline window，而不是单个数值或 byte offset；
- 将静态、模型、求解与 replay 证据拆成多轴，避免单一 `must/confidence`；
- property-independent pack 在未见性质和多个项目间迁移。

CodeQL + custom models、Falcon 类 analysis、LTL-Fuzzer/CFPOFuzz monitor 和 RESTler/OGHARN
sequence engine 可以拼出其中多部分。因此最终贡献是否足够“根本性”，取决于统一语义合同是否
带来可重复、显著的静态与 fuzzing 收益，而不是模块数量。

### 3.3 `GREEN-CANDIDATE`：建议冻结的 M5 研究对象

建议把 M5 的方法对象冻结为 TAFC：

```text
TAFC = <property/AP role,
        external action schema,
        program-boundary attachment,
        realizable witness DAG,
        scope/generation/lifecycle contract,
        prerequisite partial order,
        relative-time window,
        mutation relation/candidate set,
        independent evidence axes,
        replay obligation>
```

“候选”二字必须保留到 M9。若新增检索发现相同合同，或 CodeQL/CFPOFuzz 组合基线在同一输出
schema 下没有显著差异，应主动降级为工程贡献。

---

## 4. 可移植的 M5 实现设计

### 4.1 不修改 M4 保守结果

M5 输入固定为：

- M4 `contextual_influence_graph.json` 与 `ap_influence_cones.json`；
- typed temporal Property IR 和 AP bindings；
- 版本化 model packs；
- 可选 residual monitor state，只用于排名；
- 可选 executor capability manifest，用于判断动作是否真的可发出。

M5 不得重写或裁剪 M4 cone。新增模型事实和求解结论写入 sidecar overlay，并由新的 certificate
绑定输入摘要。即使 path solver 判定某个 witness 不可行，也只影响 frontier candidate 的状态；
原保守 cone 和其它未知路径仍保留。

建议新增以下产物，而不是把信息压回一个 `confidence` 字段：

```text
model_fact_overlay.json
frontier_candidates.json
fuzzable_frontier.json
mutation_recipes.json
recipe_replay_obligations.json
m5_analysis_certificate.json
```

### 4.2 把“外部动作”与“源码节点”分开

最容易犯的错误是把 parser 后的内部字段当成 fuzz input。M5 应显式区分：

```text
ExternalAction
  = <action_class, channel, operation, payload_schema,
     payload_slot, scope_schema, timing_capability>

BoundaryAttachment
  = <external_action_id, CIG node_id, transfer_relation,
     model_rule_evidence>
```

例如 `heartbeat.sysid` 是 external action payload slot；解码后的局部变量、message struct field 和
`last_seen` 是程序节点。一个 action 可 attach 到多个编译变体或 parser site；一个程序节点也可由
多个 action 到达。frontier 应按 action identity 去重，同时保留全部 attachment/witness。

这样可以避免含糊的“图上离外部最近节点”定义。令 `G=(V,E)` 为 M4 CIG，`A` 为 AP sink，
`X` 为 external actions，`B(x) ⊆ V` 为 action 的边界 attachment：

\[
Cone(a)=\{v\mid v\leadsto a\},\qquad
Cand(x,a)=\{\pi\mid b\in B(x),\ b\leadsto_{\pi} a\}
\]

```text
CandidateFrontier(a) = { x in X | Cand(x,a) 非空或因分析不完整而 UNKNOWN }
ActionableFrontier(a) = { x | 至少一条 witness 为 SAT，或仍为可解释 UNKNOWN }
```

只有在 coverage ledger 完整且某 action 的所有 witness 都被证明 UNSAT 时，才可从 actionable
集合排除；它仍必须出现在 `frontier_candidates.json` 的 rejected section。不同 channel、scope、
generation 或 operation 的 action 不得因 graph dominance 被错误合并。

### 4.3 Model-pack VM：有限、声明式、可审计

M4 的 `model-pack/1.0.0` 目前只是输入边界，不是执行引擎。M5 建议增加兼容的
`model-pack/2.0.0` 与一个有限关系规则 VM。VM 只允许四类操作：

```text
MATCH(selector -> relation)
CAPTURE(semantic_role, matched_node)
JOIN(on same_object | same_scope | same_generation | same_handle | same_callsite)
EMIT(typed semantic fact)
```

首版不允许 arbitrary code、递归规则、文件/网络/环境访问、动态加载函数或用户自定义算术。
递归 closure、balanced call、图可达与 solver query 由 core 执行，而不是藏在 pack 中。执行顺序、
stable sort、资源限额和 overflow 语义固定；预算耗尽必须进入 completeness ledger。

VM 可输出的关系固定为：

```text
external_boundary(action_schema, node, transfer_relation)
semantic_transfer(src, dst, relation)
event_link(register, invoke, handle, context)
timer_transition(arm, fire, cancel, clock, handle)
queue_transition(enqueue, dequeue, drop, queue, payload)
lifecycle_transition(object, generation, from_state, to_state)
scope_key(node, key_kind, key_value_source)
clock_relation(clock, unit, quantum, jitter, wrap_semantics)
persistence_transition(load, store, commit, key)
```

每条 emitted fact 必须携带：pack ID/version/digest、rule ID、selector/capture、匹配源码 site、
certainty、适用版本范围和生成时间。没有该 provenance 的 modelled edge 必须 fail closed。

#### Pack 分层

```text
Layer A: platform/ABI pack
  argv, environment, file, socket, time, POSIX/C runtime

Layer B: library/framework/protocol pack
  parser, parameter registry, callback, timer, queue, scheduler, persistence

Layer C: executor adapter（不进入 analyzer model VM）
  把 abstract action 编成 MAVLink frame、CoAP packet、SITL call 或 API sequence
```

把 action encoder 从 analyzer pack 拆出非常关键。否则 core 会隐含某个 fuzzer 的 seed layout，
既破坏可移植性，也会把“影响分析正确性”和“执行器能否构造输入”混成一个指标。

#### 静态拒绝规则

生产 portability run 中应拒绝：

- `property_id`、`ap_id`、benchmark case ID、expected node/edge ID；
- hand-selected dependency path；
- 物理绝对路径和行号 selector；
- 读取 gold label 或运行结果的规则；
- 未声明版本和 digest 的 pack；
- 引用不存在 selector/capture、非分层负递归或未绑定变量。

qualified signature/USR 可以出现在 framework pack，因为框架 API 本来就需要语义身份；但包含
某个应用私有符号的 pack 必须标成 `project_adapter`，不能用来支持“framework-level portable”
结论。仅有 `property_independent: true` 不能证明独立性：规则可能通过一个过窄的函数签名暗中
编码答案。因此还必须在读取 Property IR 前冻结 pack digest，并用未见性质迁移、规则复用率和
人工审计补充验证。

### 4.4 双向确认是实现策略，不是创新口号

建议使用以下确定性 pipeline：

```text
for each AP role sink a:
    cone = immutable M4 backward cone(a)

    for each external action x:
        attachments = model_vm.attachments(x)
        forward = balanced_forward_reach(attachments)
        witness_subgraph = cone intersect forward

        if witness_subgraph empty and ledger complete:
            classify NO_STATIC_WITNESS
        else:
            preserve all candidate witnesses
            check object/scope/generation/lifecycle compatibility
            summarize top-k local path regions
            solve supported relational constraints
            emit TAFC candidate plus evidence axes

rank candidates using residual Need(r), deadline proximity,
executor capability and evidence; never change candidate membership
```

`witness_subgraph` 应保留为 DAG/多路径集合，不能只导出一条 shortest path。单条最短路径会遗漏
替代 alias、错误返回、不同 scheduler phase 或多个联合输入。

### 4.5 证据必须拆轴

M0 的单一 `MUST_STATIC/MAY_STATIC/MODELLED/DYNAMIC_CONFIRMED` 在 recipe 层会混淆不同问题。
M4 edge certainty 保留不变；TAFC 额外使用至少五个正交轴：

| 证据轴 | 建议枚举 | 回答的问题 |
|---|---|---|
| `reachability` | `BALANCED_STATIC / MAY_STATIC / MODELLED / UNKNOWN` | action boundary 是否有 realizable-looking witness 到 AP |
| `controllability` | `DIRECT / SEQUENCE / TIMING / ENVIRONMENT / UNKNOWN` | executor 通过什么机制控制它 |
| `path_feasibility` | `SAT / UNSAT / UNKNOWN / NOT_CHECKED` | 支持子集内的路径条件是否可满足 |
| `mutation_semantics` | `PROVED_RELATION / PROVED_BOUNDARY / HEURISTIC / UNKNOWN` | 候选值/方向的证明强度 |
| `runtime_evidence` | `CONFIRMED / REFUTED_IN_SCENARIO / NOT_RUN` | 固定 replay 中 AP/时刻是否改变 |

另行记录 `model_provenance` 与 completeness ledger。**不得把 `MUST_STATIC` 翻译为“这个 mutation
一定翻转 AP”**：must edge、路径可行、输入可控、方向正确和动态翻转是五件不同的事。

### 4.6 Constraint/recipe engine：对 witness 做关系求解

#### Tier 0：无 solver 的精确模板

首版支持并明确覆盖范围：

- 整数/枚举/布尔比较；
- 位掩码 set/clear；
- 线性仿射表达式；
- threshold crossing 与区间端点；
- presence/absence、count、drop/repeat/reorder；
- 显式 timeout/deadline comparison。

输出优先使用 boundary set，而不是冒进的 `UP/DOWN`：

```text
{min, threshold-1, threshold, threshold+1, max}
{enum alternatives}
{mask clear, mask set}
```

#### Tier 1：局部 SSA/interval + 两副本 relational query

对一个 action `x` 和 AP expression `a`，复制支持的局部 summary，固定非目标 external actions 和
scope/generation，查询：

\[
\Phi(X,S) \land \Phi(X',S') \land SameExcept_x(X,X')
\land a(X,S) \ne a(X',S')
\]

若 SAT，model 给出一对在当前抽象下可能改变 AP 的 action values；这只证明局部 summary 下的
existential flip，不是整个程序的动态保证。若要输出 `MONOTONE_UP/DOWN`，还必须查询相反方向
的 counterexample 并得到 UNSAT；否则只输出 boundary/candidate pair。

#### Tier 2：仅对 Top-k 做 bounded interprocedural summary

昂贵 path summary 只应用于排名靠前且 Tier 0/1 无法决定的 witness。使用 assumption literal 绑定
edge、guard 和 model fact，保存 SAT model/UNSAT core；超时返回 UNKNOWN，不能删除 candidate。

#### C/C++ 语义门禁

Z3 中必须保留 Clang 导出的位宽、signedness、integer promotion、cast 和 wrap/UB 条件；浮点使用
IEEE-754 sort，并显式覆盖 NaN/Inf。若实现仍把 C++ 浮点或溢出当数学实数/整数，只能输出
`HEURISTIC/UNKNOWN`。涉及 native clock wrap、volatile、atomic memory order、inline asm 或未建模
库调用时同样降级，不能声称求解器证明了源码行为。

### 4.7 前置序列、异步和 timing recipe

control dependence 给出状态 guard；event/lifecycle facts 给出发生偏序：

```text
register < invoke
arm < fire
enqueue < dequeue
create(g) < use(g) < cancel/destroy(g)
destroy(g) < create(g+1)
commit(parameter) < scheduler/read(parameter)
```

M5 将必要事件构造成带 scope/generation 的偏序 DAG，并求一个最小必要事件集。若存在多个合法
拓扑序，recipe 输出偏序而不是伪造唯一总序；若有 cycle、未知 callback 或 generation alias，
输出 `PARTIAL_ORDER_UNKNOWN`。

多个输入联合才能改变 AP 时，使用 `joint_action_group`/hyperedge：

```text
enable_failsafe = true
AND gcs_seen_once = true
AND heartbeat_gap > timeout
```

禁止把它拆成三个各自声称可翻转 AP 的 recipe。

timing recipe 必须绑定 clock source、单位、scheduler quantum、jitter 和 comparison semantics。
在信息不全时只给 deadline 周围的区间及动作类型，例如 `pause/resume around T`，不能给虚假的
精确纳秒。MITL residual 只影响优先级：当前 transition 所需 AP、即将到期 deadline 和 matching
scope 优先；它永远不能把完整 frontier candidate 从结果中删除。

### 4.8 可选动态确认

M5 第一版不需要新通用插桩器。executor adapter 可利用已有 autotest、protocol harness 或可观察
AP 运行 recipe，并记录 AP truth、transition time、property distance 与 replay log。

需要更细粒度 evidence 时，可选使用 LLVM
[DataFlowSanitizer](https://clang.llvm.org/docs/DataFlowSanitizer.html)：官方文档提供 label propagation、
comparison/event callbacks 和 experimental conditional callbacks。但它只能确认具体执行；ABI list、
uninstrumented library 与未走路径仍会造成盲区。动态 `REFUTED_IN_SCENARIO` 不得从保守 cone 删除
静态候选，`CONFIRMED` 也不得反推对所有场景的因果必然性。

---

## 5. Benchmark 与 Artifact 执行建议

### 5.1 Artifact 分层

| 优先级 | 对象 | 验证子问题 | 一手入口 | 当前表述上限 |
|---|---|---|---|---|
| P0 | M2 120-case gold | exact action、scope、joint input、direction、prerequisite、timing | 本地既有 benchmark | 可作为 RIFT 主静态 gold，但 evaluator 必须隔离 |
| P0 | CFPOFuzz quick demo | 最强 property-guided collision、monitor/input priority | [官方 artifact](https://github.com/zbchen/CFPOFuzz) | `RUNNABLE_CANDIDATE`，尚未在本轮执行 |
| P0 | CodeQL C/C++ global flow + custom model | source-sink/model-pack 强基线 | [官方 C/C++ 文档](https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-cpp/) | 应实现同 schema adapter，不可只文字比较 |
| P0 | NIST Juliet C/C++ 1.3 | data/control/interprocedural/source variant | [NIST SARD #112](https://samate.nist.gov/SARD/test-suites/112) | 只验证其明确 source/sink subset；不验证 async/time |
| P0 | SV-COMP C ReachSafety subset | path feasibility、bitvector、control、overflow | [官方 2026 tasks](https://sv-comp.sosy-lab.org/2026/benchmarks.php)、tag `svcomp26` | 用 YAML truth 验证 solver/path，不直接当 fuzz recipe gold |
| P1 | Concrete Constraint Guided SE | KLEE/path feasibility 对照 | [ICSE artifact page](https://conf.researchr.org/details/icse-2024/icse-2024-artifact-evaluation/3/Concrete-Constraint-Guided-Symbolic-Execution)、[Zenodo](https://zenodo.org/records/10516325) | `RUNNABLE_CANDIDATE` |
| P1 | OGHARN | C API init/call prerequisite 与 adapter 兼容性 | [Zenodo](https://zenodo.org/records/14727592) | 只比较 sequence/harness 子问题 |
| P1 | PhASAR v2403 / ECOOP 2024 subjects | C/C++ interprocedural scale | [论文](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.36)、[源码 tag](https://github.com/secure-software-engineering/phasar/tree/v2403) | scale baseline，不是 recipe truth |
| P2 | CSA artifact | cross-domain precision 和大型项目性能 | [artifact README](https://zenodo.org/records/10578637/files/README.pdf) | 资源允许时运行 quick/selected，不承诺完整复现 |
| P2 | CGMiner | callback summary 生成与 provenance 设计 | [DARTS](https://doi.org/10.4230/DARTS.10.2.2) | Java/Android，仅作机制验证，不支持 C++ portability |
| P2 | FuzzBench/Magma | 后续固定预算 fuzz 工程 | [FuzzBench](https://github.com/google/fuzzbench)、[Magma](https://github.com/HexHive/magma) | 只有共享 executable/action adapter 后才有意义 |

Juliet #112 有 64,099 个 C/C++ test cases，但不能把整个套件机械标成 RIFT ground truth；只选择
能从 NIST metadata 和模板明确恢复 input source/flow variant 的子集。SV-COMP 同理：它能提供
reachability/overflow truth，却没有 RIFT 的 external action、scope 或 timing label。

### 5.2 真实项目阶梯

建议保留用户计划中的真实对象顺序：

```text
libcoap
  -> FreeCoAP
  -> Mosquitto
  -> TinyMQTT
  -> ArduPilot GCS failsafe
```

其中前四个对象用于测试 protocol/framework pack 的迁移，ArduPilot 用于复杂参数、MAVLink、
scheduler、mode、armed、clock 和 process epoch。每个项目必须冻结 commit、compile DB、工具链、
model-pack digest 与 executor adapter digest。

“三个项目都跑出 JSON”不是可移植性。强门禁至少要求：

- 同一 core binary、core manifest 和 output schema；
- 项目间 core source change 为零；
- pack 在读取测试性质前冻结；
- 至少一个 framework/protocol pack 在未见性质或共享框架的另一项目上零修改复用；
- 报告每项目新增 pack rule/LOC、人时、unmodelled API 和 UNKNOWN；
- core 和 pack 均扫描项目名、性质 ID、benchmark ID、答案 edge、物理路径/行号；
- 两名真人对真实项目 action/source/recipe 独立标注并仲裁。

### 5.3 公平比较矩阵

M5 静态对比至少加入：

```text
ADGFuzz-style assignment
MoonShine-RW
LLVM def-use / MemorySSA+AA
SVF backward value-flow
plain PDG/property slice
CodeQL GlobalFlow + equivalent custom models
RIFT cone only
RIFT-TAFC
```

Falcon、Tuna、CSFuzz 没有在本轮定位到可运行 artifact 时，只能做 method-level comparison；禁止
用论文数字拼接成伪实验表。CFPOFuzz 的公平比较分两部分：静态 external-action discovery 不应
强迫它回答原本不回答的 schema；fuzz utility 则在共享 target、property、seed、operator、预算和
机器下比较 time-to-AP-flip/property progress，并单独记录其 event/input mapping 人工成本。

---

## 6. 可证伪指标与预注册建议

### 6.1 静态与 recipe 正确性

建议把评价单元扩展为：

```text
FrontierUnit = <ap_id, action_class, channel, operation,
                payload_slot, scope_schema, generation_schema>

WitnessUnit  = <frontier_unit, AP binding,
                edge-kind sequence, path condition class>

RecipeUnit   = <frontier_unit, mutation relation/candidate set,
                joint_action_group, prerequisite partial order,
                timing interval, evidence axes>
```

必须报告：

- exact Frontier Top-1/Top-5 precision、recall、F1；
- critical/must influencer recall；
- witness edge-kind recall 与 spurious cross-call/object/scope rate；
- direction accuracy **以及 supported coverage**，防止全部 abstain 获得虚高准确率；
- SAT model replay rate、AP flip rate、property-distance improvement；
- prerequisite partial-order precision/recall、最小性和 replay 成功率；
- timing interval coverage、宽度和 deadline-side classification；
- 每个证据轴的 calibration；错误的强 `PROVED_*` 计为 hard failure；
- UNKNOWN/timeout/model-gap 数量，不能从 denominator 删除。

用户计划的 direction accuracy `>= 90%` 可以保留，但必须同时预注册最低 coverage，例如支持模板
子集内至少 60% 的 numeric/enum/bitmask gold；否则方法可通过拒答规避难例。具体 coverage 阈值
应在查看最终 gold outcome 前冻结。

### 6.2 可移植性指标

- core binary/schema/manifest digest equality；
- zero core changes across projects；
- pack reuse rate、rules per KLoC/API family、model-authoring time；
- unseen-property transfer precision/recall；
- unseen-project transfer，在共享 framework/protocol 时的 zero-edit rate；
- action adapter effort与analysis pack effort分开；
- 关闭某 pack 后的 UNKNOWN 增量，而不是只看 precision；
- 物理 checkout relocation 后 canonical artifact byte equality。

若每条性质都需要增加一个专用 selector/rule，即使 core 未改也判定 portability 失败。若一个 pack
只能在一个项目、一个 commit、一个 AP 上工作，只能称 project adapter，不能称 transferable model。

### 6.3 性能与消融

继续使用既有预算：libcoap `<= 60 s / 2 GiB`，ArduPilot 单性质
`<= 30 min / 12 GiB`。另行报告 M5 相对 M4 的增量时间/内存、每个 frontier solver query 数、
SAT/UNSAT/UNKNOWN/timeout 分布和 certificate 大小。

必要消融：

```text
- control dependence
- path feasibility
- scope/generation
- async/lifecycle model
- bidirectional witness
- relational truth-change query
- residual ranking
- model packs
```

所有消融都必须保留同一个 M4 conservative cone；否则无法判断收益来自更好 ranking 还是偷偷
删掉 may-dependency。

### 6.4 直接推翻 RIFT 主张的条件

以下任一结果都应触发降级，而不是调换指标：

1. `CodeQL GlobalFlow + 公平 custom models` 在 Frontier/Recipe schema 上与 RIFT 无显著差异；
2. CFPOFuzz dynamic pilot 在相同 cold-start 预算内取得相同或更好的 external action precision；
3. 两副本 relational query 的 SAT model replay 率低，且错误主要来自不可修复的 summary mismatch；
4. direction 只有在低覆盖、简单比较上准确，真实项目大多为 UNKNOWN；
5. callback/timer/queue pack 需要逐性质手工加边；
6. ArduPilot 结果依赖 core 中的项目符号或硬编码 source site；
7. 去掉 scope/lifecycle/relational query 后无可解释退化；
8. Top-k actionability 未超过最佳静态基线预注册门槛；
9. 固定预算 fuzz 的收益只来自新增 operator/scheduler，而非 guidance。

---

## 7. 论文写作中明确不能说什么

### 7.1 当前禁止主张

- “RIFT 是首个 property-guided/static-dependency-guided fuzzer”；
- “RIFT 首次自动发现影响 temporal property 的输入”；
- “双向 influence confirmation 是新算法”；
- “model-pack VM 本身是新颖 static analysis”；
- “RIFT 的 `must` influencer 一定能翻转 AP”；
- “Z3 证明 recipe 对 C++ 源码正确”，除非位宽、FP、cast、UB、库和路径语义均闭合；
- “动态确认证明因果关系”或“单次未翻转证明无影响”；
- “已验证跨项目可移植”，直到强门禁和真实项目仲裁完成；
- “文献中从未出现过该方法”，因为有限检索无法证明全局不存在；
- 用原论文报告数字声称 RIFT 优于 Falcon、CFPOFuzz、CSFuzz 或其它方法。

### 7.2 完成实验后可能允许的窄表述

若证据支持，可以表述为：

> 我们提出并评价一种面向 typed metric-temporal AP 的 evidence-carrying external-action
> frontier contract；它将保守 value/control/event/lifecycle influence witness 转换为带
> scope、generation、前置偏序、相对时间窗和 mutation relation 的 fuzz guidance。

还可以如实写：

> 在冻结的 N 个 C/C++ 项目和 M 条性质上，同一个 core binary/schema 未修改；版本化模型包
> 的规则量、人工成本和迁移结果如下。

“to our knowledge” 只能修饰精确定义的合同组合，不能修饰 slicing、source-sink、SMT、callback
model 或 property-guided fuzzing 这些已广泛存在的组件。

---

## 8. M5 开工前必须冻结的决定

1. **动作身份**：`channel + operation + payload slot + scope/generation` 的 canonical identity，
   以及一个动作多 attachment 的合并规则；
2. **pack 分层**：platform/framework pack 与 executor adapter 的 schema 边界；
3. **C++ 求解语义**：bitvector、FP、UB、clock wrap 和 unsupported expression 的降级策略；
4. **frontier 完整性**：candidate/rejected/actionable 三个集合及 UNSAT/UNKNOWN 保留规则；
5. **证据轴**：禁止 recipe 复用 M4 单一 confidence；
6. **joint action**：多输入 recipe 用 hyperedge，不拆成虚假的独立影响源；
7. **artifact 顺序**：先跑 CFPOFuzz demo、CodeQL adapter、Juliet/SV-COMP selected set，再写
   TAFC production code；
8. **可移植性预注册**：在看真实 outcome 前冻结 zero-core-change、pack reuse 和人工成本指标。

### 未决问题

- `source_location` selector 是否完全从 portable pack 禁用，还是只允许自动生成且有 relocation
  digest 的测试 pack；本审计建议生产 portability run 完全禁用。
- framework-specific qualified signature 必不可少，但如何机械区分 framework pack 与伪装的
  per-property project rule；schema 无法单独解决，需 pack freeze + holdout + review。
- 两副本 query 是对同一路径、两条不同路径还是 bounded path family 求解；首版建议分别输出
  `SAME_PATH_FLIP` 与 `CROSS_PATH_FLIP`，避免语义混淆。
- executor 能否对“时间流逝、drop、reorder、scheduler phase”提供统一 capability manifest；若不能，
  recipe 必须标 `ANALYSIS_ACTION_ONLY/EXECUTOR_UNAVAILABLE`。
- 真实项目 gold 的两名标注者与仲裁流程尚未落实；在此之前不能发布真实项目 precision/recall。

---

## 9. 一手来源索引

### 静态分析、值流与 summary

- [Falcon, PLDI 2024](https://doi.org/10.1145/3656400)
- [Tuna, ICSE 2026](https://doi.org/10.1145/3744916.3773183)
- [Fast Flow-Sensitive C Program Partitioning, ICSE 2026](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/312/Fast-Flow-Sensitive-C-Program-Partitioning-via-Iterative-Value-Flow-Refinement)
- [Precise Sparse Abstract Execution, ICSE 2024](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/235/Precise-Sparse-Abstract-Execution-via-Cross-Domain-Interaction)
- [CSA artifact README](https://zenodo.org/records/10578637/files/README.pdf)
- [Scaling Interprocedural Data-Flow Analysis / PhASAR, ECOOP 2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.36)
- [LibAlchemy, ICSE 2024](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/131/LibAlchemy-A-Two-Layer-Persistent-Summary-Design-for-Taming-Third-Party-Libraries-in)
- [CodeQL C/C++ data flow](https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-cpp/)
- [CodeQL C/C++ custom models](https://codeql.github.com/docs/codeql-language-guides/customizing-library-models-for-cpp/)

### Property/temporal 与 fuzzing

- [CFPOFuzz, ICSE 2026 paper](https://zbchen.github.io/files/icse2026.pdf)
- [CFPOFuzz official artifact](https://github.com/zbchen/CFPOFuzz)
- [CSFuzz, ICSE 2025](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/182/Critical-Variable-State-Aware-Directed-Greybox-Fuzzing)
- [LTL-Fuzzer, ICSE 2022](https://doi.org/10.1145/3510003.3510082)
- [PGFuzz, NDSS 2021](https://doi.org/10.14722/ndss.2021.24096)
- [ProtocolGuard, NDSS 2026](https://www.ndss-symposium.org/ndss-paper/protocolguard-detecting-protocol-non-compliance-bugs-via-llm-guided-static-analysis-and-dynamic-verification/)
- [GREYONE, USENIX Security 2020](https://www.usenix.org/conference/usenixsecurity20/presentation/gan)
- [Angora official project](https://angorafuzzer.github.io/)
- [SynFuzz author preprint](https://arxiv.org/abs/1905.09532)
- [Matryoshka author PDF](https://www.cs.ucdavis.edu/~hchen/paper/chen2019matryoshka.pdf)

### Async、sequence、explanation 与 benchmark

- [CGMiner, ECOOP 2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.4)
- [CGMiner evaluated artifact](https://doi.org/10.4230/DARTS.10.2.2)
- [Static Analysis for Asynchronous JavaScript, ECOOP 2019](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2019.8)
- [RESTler official repository](https://github.com/microsoft/restler-fuzzer)
- [OGHARN official artifact](https://zenodo.org/records/14727592)
- [WhyFlow, ICSE 2026](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/103/WhyFlow-Interrogative-Debugger-for-Sensemaking-Taint-Analysis)
- [LLVM DataFlowSanitizer](https://clang.llvm.org/docs/DataFlowSanitizer.html)
- [NIST Juliet C/C++ 1.3, SARD #112](https://samate.nist.gov/SARD/test-suites/112)
- [SV-COMP 2026 benchmark tasks](https://sv-comp.sosy-lab.org/2026/benchmarks.php)
- [Concrete Constraint Guided Symbolic Execution artifact](https://zenodo.org/records/10516325)
- [FuzzBench official repository](https://github.com/google/fuzzbench)
- [Magma official repository](https://github.com/HexHive/magma)
