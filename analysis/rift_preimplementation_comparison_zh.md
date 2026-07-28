# RIFT 实施前方法比较、Artifact 审计与可证伪假设

> 状态：`PRE_IMPLEMENTATION / RIFT-M0`
>
> 证据快照日期：2026-07-18（Asia/Shanghai）
>
> 机器可读矩阵：[`analysis/data/rift_preimplementation_matrix.csv`](./data/rift_preimplementation_matrix.csv)

## 0. 结论先行

用户提出的方向是合理的，但必须把目标从“找与 MITL 命题名字相似的变量”收紧为：

> 给定一条已审阅的 MITL 性质及其 typed AP，保守地寻找能够改变 AP 真值、改变 AP
> 发生时刻、改变动态时间界或改变 AP 可达前置状态的程序内依赖；再从这些依赖中识别
> 外部可控的参数、消息字段、命令、环境量和操作顺序，供后续 fuzzing 选择输入区域。

这条链分为三个不能混淆的对象：

1. **AP influence cone**：静态上可能影响 AP/guard/bound 的完整依赖锥；
2. **fuzzable influence frontier**：依赖锥中可以由测试执行器控制的入口；
3. **mutation recipe**：如何取值、何时发送、先做什么以及作用于哪个 scope 的可执行建议。

现有方法分别覆盖其中一部分：ADGFuzz 提供轻量赋值名反向关联，PGFuzz 提供
“参数→性质 term”的 value-flow 与人工词表，MoonShine 提供跨操作显式/隐式依赖闭包，
LTL-Fuzzer 提供人工 AP location tuple 后的时序引导，ProtocolGuard 提供规则相关 handler
切片，FGS 提供 automaton-guided tempo-spatial multi-point slicing，PDG/MemorySSA/SVF
提供通用程序依赖基础。**当前证据不支持“RIFT 已经优于这些方法”**。

本文件把 RIFT 的全部优势写成编号为 `H-RIFT-*` 的**待验证假设**。实施后只有在相同
benchmark、相同 gold set、相同输入接口、相同资源预算和相同 evaluator 下超过最强
可运行基线，才能将相应假设改写为实验结论。

另一个重要结论是：普通 property-directed backward slice、automaton-guided slicing、
data/control dependency graph、别名分析本身都不是足够的新颖点。RIFT 的候选贡献必须落在
“typed MITL AP 的联合绑定 → scope/lifecycle-aware influence → controllable frontier →
可验证 mutation recipe → residual-conditioned ranking”这一完整问题定义及其实证上。

---

## 1. 比较对象和统一问题定义

### 1.1 RIFT 要回答的查询

对性质 `φ` 中的 AP `a`，定义查询：

```text
InfluenceQuery =
  <property_id, ap_id, ap_role, candidate_sink_set,
   time_bound_symbols, scope_schema, compile_database, framework_models>
```

`ap_role` 至少区分：

```text
trigger | response | cancel | state | guard | bound | clock | scope
```

若外部输入 `u` 经由程序路径能够改变以下任一对象，则 `u` 是候选 influencer：

- `a` 的布尔真值；
- `a` 从 false→true 或 true→false 的发生时刻；
- 计算 `a` 的 guard、比较阈值或动态 MITL bound；
- 到达 AP sink 所需的 mode、resource、session、generation 或命令前置状态；
- timer/callback/queue/scheduler 导致的事件先后关系。

### 1.2 必须区分的证据强度

静态图中的可达不能自动称为动态因果。统一输出使用以下状态：

| 状态 | 含义 |
|---|---|
| `MUST_STATIC` | 在声明的抽象与路径条件下，每条匹配执行均经过该依赖 |
| `MAY_STATIC` | 存在保守静态路径，但 alias/path/scope 尚未证明可行 |
| `MODELLED` | 依赖来自显式、版本化的 framework model |
| `DYNAMIC_CONFIRMED` | 固定实验中改变该输入后观察到 AP 或其时刻改变 |
| `UNKNOWN` | 缺失模型、预算耗尽或语义信息不足 |

`DYNAMIC_CONFIRMED` 只能支持给定版本、场景和输入范围内的结果，不反向证明完整静态
因果关系。`MAY_STATIC` 也不能直接包装成高置信 mutation recipe。

### 1.3 统一比较单元

所有方法在实施前后使用同一组最小评价单元：

```text
BindingUnit   = <ap_id, site_id, phase, scope_schema>
InfluencerUnit= <ap_id, source_id, channel, field_or_parameter, scope_schema>
EdgeUnit      = <src_id, dst_id, edge_kind, confidence>
RecipeUnit    = <source_id, mutation_kind, direction,
                 prerequisites, timing_window, scope_schema>
```

源码行号不是稳定 `site_id`。实现阶段应使用项目相对路径、源码哈希、Clang USR、AST role、
宏 spelling/expansion location 和 LLVM debug fingerprint 的组合身份。

---

## 2. 证据来源与审阅边界

本次 M0 使用了以下本地材料：

- [`ADGFuzz 论文—代码深读`](./adgfuzz_paper_code_deep_reading_zh.md)；
- [`PGFuzz 论文—代码部署分析`](./pgfuzz_paper_code_deployment_zh.md)；
- [`ProtocolGuard 与 CoAP 需求测试精读`](./protocol_fuzzing_study/paper_notes/protocolguard_coap_requirement_testing_reading_20260715.zh.md)；
- [`现有 TAFuzz-MITL 设计`](../documents/TAFuzz_MITL_CCFA_design.md)；
- 用户提供的 MoonShine PDF，SHA-256：
  `b7705ad1f69b29d65ab42d875c001acda32d328b8bc08e2a9e6ba76093a2ae12`。

使用的官方/作者主来源：

- [MoonShine, USENIX Security 2018](https://www.usenix.org/conference/usenixsecurity18/presentation/pailoor)
  及[作者代码](https://github.com/shankarapailoor/moonshine)；
- [PGFuzz, NDSS 2021](https://doi.org/10.14722/ndss.2021.24096)；
- [LTL-Fuzzer, ICSE 2022](https://doi.org/10.1145/3510003.3510082)
  及[Zenodo artifact](https://doi.org/10.5281/zenodo.5420327)；
- [FGS, FSE 2024](https://doi.org/10.1145/3643749)
  及[Zenodo artifact](https://doi.org/10.5281/zenodo.12770067)；
- [ProtocolGuard, NDSS 2026](https://www.ndss-symposium.org/ndss-paper/protocolguard-detecting-protocol-non-compliance-bugs-via-llm-guided-static-analysis-and-dynamic-verification/)
  及[作者仓库](https://github.com/songxpu/ProtocolGuard)；
- [LLVM MemorySSA](https://llvm.org/docs/MemorySSA.html)、
  [LLVM Dependence Graphs](https://llvm.org/docs/DependenceGraphs/) 和
  [SVF](https://svf-tools.github.io/SVF/)。

本文件是实施前比较，不声称已经复现任何新增论文数字。论文原始数字只用于理解目标与
设置；RIFT 的优劣必须由后续统一实验重新测量。

---

## 3. 方法逐项拆解

### 3.1 ADGFuzz：assignment-name-guided input grouping

#### 实际静态方法

ADGFuzz 的公开静态链路扫描 `.cpp`，用 Python 正则识别有限函数签名和赋值，在单函数内
从赋值左值反向收集 RHS 名称，再把中间节点剪掉，只保留 root 的 leaf names 和节点数。
成员访问在字符串规范化中丢失 record/type/instance 语义；调用被合成为字符串，不进入
callee。leaf 再借人工同义词/物理词表映射到配置参数、命令、环境量和 RC 通道，形成 MIS。

#### 对 RIFT 的真实价值

- 它直接提出“从结果变量反向得到局部输入集合”，与 RIFT 的 fuzzable frontier 动机一致；
- MIS 可作为低成本、高召回但低置信的 `name-only` baseline；
- 多输入共享一个 assignment root 的分组可作为联合 mutation 候选。

#### 不足与公平比较要求

- 无 AST、CFG、类型、alias、control dependence、跨过程或对象实例；
- 名称语义相关不等于输入动态到达 AP；
- 论文人工检查的 87.33%/94.67% 是 ADG–MIS 名称语义判断，不是 slice recall 或因果准确率；
- 原方法没有 MITL/AP 输入。若把 AP sink 作为 root 适配，必须标为
  `ADGFuzz-style`，不得冒充原始 artifact 结果。

#### Artifact 状态

本地仓库冻结在 `203fce3f4265241340ed62b9be90aec1da0afa37`。静态脚本和预计算
JSON 可审计，但论文 appendix 提到的部分脚本/自动去重与当前公开树不一致。状态：
`LOCAL_AUDITED_PARTIAL`。

### 3.2 PGFuzz：parameter-to-term value-flow plus dynamic maps

#### 实际静态方法

PGFuzz 先人工把文档 policy 写成 MTL 并拆成 terms。对配置参数，它定位参数导入变量，
在 LLVM IR 上构建 def-use；标量递归跟踪 load/store，指针使用 Andersen points-to，论文
描述为 interprocedural、path-insensitive、flow-sensitive，随后使用 SSA DFG。末端变量名
借人工 synonym table 映射到 policy term。命令和环境因素主要依靠 SITL 动态分析映射到
physical states；输入间前置依赖也主要由动态配对实验寻找。

#### 对 RIFT 的真实价值

- 它已经证明“性质 term → 相关输入子空间”对 RV fuzzing 是有意义的问题；
- `InputP/InputC/InputE` 分类和 prerequisite inputs 可直接约束 RIFT 输出 schema；
- 它是 ArduPilot/PX4 上最接近 RIFT 任务的实用基线。

#### 不足与公平比较要求

- 静态方向从已知参数 import point 向 term 展开，不是从任意 AP sink 自动反向发现所有入口；
- policy、term、synonym 和部分 source variable mapping 需要人工；
- control-only、timer/callback/queue、object generation 和 metric-time source dependency
  没有形成统一静态图；
- 公开仓库没有论文的完整 SVF 静态实现、predicate generator 或 Paparazzi 部分。

因此后续比较应分开报告：

1. `PGFuzz-released-map`：把发布的 policy input maps 当 silver standard；
2. `PGFuzz-style-SVF`：按论文描述重实现 parameter→term pipeline；
3. 不能把第 2 项标成“原 PGFuzz artifact 复现”。

#### Artifact 状态

本地仓库冻结在 `7eaebf21116087249b8329d4ba7337a24a34ecb9`，包含 ArduPilot/PX4
运行脚本和 policy 输入文件，但缺上述静态组件。状态：`RUNTIME_PARTIAL_STATIC_MISSING`。

### 3.3 MoonShine：trace explicit dependency + static `W ∩ R_cond`

#### 显式依赖

MoonShine 从真实程序 syscall trace 构造 argument/result graph。result 和 argument 都记录
值及类型；若上游 syscall 返回的 `(type,value)` 与下游参数相同，就建立显式依赖。它还
特别处理 output arguments、`mmap` 地址区间和 parent→child process 资源继承。

这部分不是纯静态分析：依赖候选来自一次具体动态 trace 的值匹配。

#### 隐式依赖

MoonShine 使用 Smatch AST hooks 对每个 syscall 可达实现提取：

```text
READ_deps(call)  = 在 conditional expression 中读取的 struct.field
WRITE_deps(call) = 任意 assignment/unary assignment 写入的 struct.field
```

若上游调用 `ca` 与下游调用 `cb` 满足：

```text
WRITE_deps(ca) ∩ READ_deps(cb) != ∅
```

则 `ca` 是 `cb` 的候选 implicit dependency。显式和隐式依赖递归调用彼此，再按原 trace
顺序合并。`mlockall → msync` 的核心是前者写 `vma->vm_flags`，后者在条件中读取同一字段。

#### 对 RIFT 的真实价值

MoonShine 最值得保留的是：

1. 区分直接 value passing 与经共享状态改变 control path 的隐式依赖；
2. 对依赖做递归闭包，而不是只返回一跳字段名；
3. mutation/seed sequence 保持原有因果顺序；
4. 用完整 trace coverage recovery 验证“依赖是否保住行为”，而不只人工看图。

#### 不能直接迁移的部分

- `struct.field` 相等不代表同一对象实例；论文明确把 pointer imprecision 作为误报来源；
- alias 会导致漏报，条件取值不满足会导致误报；
- 不追踪跨线程/跨进程依赖；
- 不理解 AP、MITL、scope、deadline 或 mutation direction；
- syscall trace 中 `(type,value)` 相等可能碰撞，且只能看到已有 trace 的依赖。

后续实现 `MoonShine-RW` 时，只能称为**适配基线**：把 syscall operation 换成函数/
framework event，把字段集合换成 AST/IR memory object 集，但保留 `W ∩ R_cond` 判定。

#### Artifact 状态

作者仓库 HEAD 为 `95e5f6dfd2760a9d763fc2bc90623c9e1e74e804`（2019-05-09）。
README 固定 Ubuntu 16.04、Go 1.10.3、旧 strace 和 Syzkaller
`f48c20b8f9b2a6c26629f11cc15e1c9c316572c8`；提供 sample traces 链接和完整
distiller 源码。状态：`AVAILABLE_LEGACY_NOT_YET_REPRODUCED`。

### 3.4 LTL-Fuzzer：人工 AP tuple 后的 automaton-guided fuzzing

LTL-Fuzzer 把 LTL 的 negation 编译为 Büchi automaton，通过 AFL instrumentation 记录
事件和状态，并保存使 automaton 前进的输入 prefix。它可从当前 automaton state 选择能
向 accepting state 前进的 AP，再以对应源码位置作为 AFLGo target。

关键边界是：其论文示例把 AP 表示为 `<location, proposition, predicate>` tuple；性质和
tuple 由人工写下，示例报告约 20 分钟。它会寻找 AP 变量及 aliases 的更新位置，但论文
没有提供 RIFT 所要求的“从 AP 到外部可控参数/消息字段的带 scope 影响解释”。

对 RIFT 来说，LTL-Fuzzer 是两种不同基线：

- `manual-AP-oracle`：人工 tuple 给出 AP 位置，隔离 AP 自动绑定误差；
- `automaton-guidance`：比较只按 AP target/CFG distance 与按影响 frontier 选择输入。

Zenodo v8 提供约 1.2 GB dataset、约 109.7 MB source archive、性质 PDF 和 CVE log。
M1 当前已冻结官方 commit `716ac301fa3a8ea39814bc80eeebba49c19c1378`：18 个核心
target 与 AFLGo 已构建；公开 target importer 对 RERS target 解析为 46/46；Telnet 的
3 个 target 因仓库缺失已声明的 gitlink 而仍不可解析。完整端到端 smoke 尚未完成，
因此状态是 `PARTIAL_BUILD_AND_IMPORT_PASS_SMOKE_PENDING`，不能写成原 artifact 已复现。

### 3.5 ProtocolGuard：handler-centric rule-oriented forward slice

ProtocolGuard 从协议 message receive path 建 MessageCG，让 LLM 识别 handler、规则字段和
相关变量，再以 LLVM def-use 做跨过程 forward slice；Clang AST 补控制结构，SVF 处理
间接调用，LLM 再补回日志/错误码并剪枝。

它与 RIFT 的邻近之处是“语义规则选择 slicing criteria + 静态结构追踪”，但目标仍不同：

- ProtocolGuard 从消息字段向 handler 后果 forward slice；
- RIFT 计划从 typed temporal AP sink 向所有可控入口 backward cone，再做 source→sink
  forward confirmation；
- ProtocolGuard 的 rule JSON 不编码 metric bound、scope generation 或 MITL residual；
- 论文已报告 callback/decoupled cleanup/send path、深层字段流和多 transport context
  是困难点。

#### Artifact 状态

论文给出 Zenodo `10.5281/zenodo.17933922` 和 GitHub。2026-07-18 审计时：

- GitHub HEAD `ecaf41613ff4e59979ddd9d1862058d82b1545ce` 的递归 tree 只有
  8 个 README/LICENSE/image 条目；
- 本地解包副本包含 Python、header 和 CMake 文件，但没有 README 命令所需的
  `program_slicing/src`，无法生成 `libAnalyzerPass.so/libASTPass.so/libMatchPass.so`；
- 论文 Artifact Appendix 自报 `Benchmarks: None`。

因此原静态 pass 当前状态为 `PUBLISHED_ARTIFACT_INCOMPLETE_UNRUNNABLE`。后续只能使用
其论文数据/subjects，或实现明确标注的 `ProtocolGuard-style handler slice`，不能声称运行了
原 ProtocolGuard 静态分析器。

### 3.6 FGS：automaton-guided tempo-spatial multi-point slicing

FGS 输入有限状态 automaton 和 LLVM IR，使用 SVF 的 ICFG、PDG 和 call graph。它先以
path-insensitive analysis 过近似抽取 multi-point marker sequences，再结合：

- temporal multi-point slicing：保留包含 marker sequence 的执行路径；
- spatial multi-point slicing：保留 marker 的 data/control dependencies；
- 两者交集用于简化 path-sensitive typestate analysis 的 ICFG。

这使 FGS 成为最重要的近邻：它已经做了 automaton-guided、temporal-order-aware、
control/data-aware multi-point slicing。RIFT 不能把“按 temporal property 做切片”本身当作
根本创新。

区别必须由实验验证，而不能只靠命名：FGS 的 temporal 是 typestate operation order；其
客户端检测 memory leak/double-free/use-after-free/null dereference。它没有直接输出 typed
MITL AP→external fuzz input、metric clock/deadline、scope generation 或 mutation recipe。

论文在 846 个 NIST 程序和 10 个真实 C/C++ 项目上报告：相对 ESP，平均 ICFG nodes
减少 89%、edges 减少 86%、calling contexts 减少 88%，大项目平均 116× 加速、93%
内存下降。这些是论文原始数字，不是本机复现结果。

#### Artifact 状态

Zenodo v5 只保存 374,218-byte README；README 将 binary、source 和 testcases 全部指向
`rmrepo/fgs:latest` Docker image。M1 审计时 Docker Hub repository API 返回 404，OCI
registry 对 `latest` manifest 返回 401；因此无法取得 image digest、smoke 输入或 NIST
用例，smoke 与 NIST-846 均未运行。状态是
`BLOCKED_UPSTREAM_ARTIFACT_UNAVAILABLE`。这只说明发布工件当前不可获得，不是 FGS
算法失败，也不能据此比较 RIFT 与 FGS 的运行时间、内存或精度。

### 3.7 Plain PDG

PDG 表示程序元素间 data 和 control dependencies。LLVM 官方文档同时指出，graph builder
只考虑给定 instruction/basic-block range，范围外的依赖被忽略。普通 PDG backward slice
是必要强基线，但它本身不包含：

- AP 的角色、scope、lifecycle phase；
- timer/callback/queue 的领域事件边；
- 外部输入可控性；
- mutation direction、prerequisite sequence 或 metric-time residual。

“Plain PDG”不是单一论文 artifact。后续必须固定一个实现（建议同一 RIFT graph core 的
`data+control only` 模式），并公布边构造规则，避免不同工具差异污染算法比较。状态：
`CONCEPTUAL_BASELINE_IMPLEMENTATION_REQUIRED`。

### 3.8 LLVM MemorySSA

MemorySSA 为内存操作构造 SSA-like def-use/use-def 关系，walker 借助 alias-analysis stack
查询 clobber。LLVM 官方文档明确写明其实现是 **intraprocedural**。因此它适合作为函数内
memory baseline 或 RIFT 的一层证据，不能单独承担全程序 AP influence。

状态：LLVM 18 本机可用；`LIBRARY_AVAILABLE_BASELINE_NOT_YET_IMPLEMENTED`。

### 3.9 SVF

SVF 以 LLVM IR 为输入，提供 interprocedural value-flow、pointer analysis、ICFG/VFG 等
基础设施。PGFuzz、ProtocolGuard、FGS 都借用了它的不同能力，说明它是合理的强基础
基线，但 SVF 本身不知道 MITL AP、可控输入、时钟、scope 或 recipe。

SVF 3.2 tag 为 `197a6590bd9c695a9c3daf52622dea912ef9a002`，官方 release 明确
升级到 LLVM 18。状态：`AVAILABLE_VERSION_PINNED_NOT_YET_BUILT`。

---

## 4. RIFT 与近邻方法的实施前定位

下表中的“RIFT 差异”全部是**设计目标**，不是已经证实的优势。

| 方法 | 它已经解决的核心问题 | 没有覆盖的 RIFT 目标 | RIFT 待验证差异 |
|---|---|---|---|
| ADGFuzz | assignment leaf 名称→输入分组 | typed AP、真实 def-use/alias/control、scope | `H-RIFT-01/02`：结构绑定与依赖 recall/precision 待验证优于名称图 |
| PGFuzz | 参数→MTL term；命令/环境→状态动态 map | 任意 AP 反向发现、统一 async/lifecycle graph | `H-RIFT-03/05`：自动 frontier 与 prerequisite 待验证减少人工并提高 actionable precision |
| MoonShine | trace 内显式资源依赖与 `W∩R_cond` 隐式依赖 | AP/metric time/object scope/recipe | `H-RIFT-04/05`：对象/phase/scope 化隐式依赖待验证减少误报并保住关键依赖 |
| LTL-Fuzzer | AP tuple→automaton progress→target fuzzing | AP→可控输入路径和方向 | `H-RIFT-01/06/08`：自动绑定和 frontier/residual guidance 待验证减少 AP flip 时间 |
| ProtocolGuard | rule field→handler forward slice→LLM pruning | MITL、反向输入 frontier、scope/timer | `H-RIFT-02/05`：meet-in-the-middle 和 async model 待验证覆盖 decoupled path |
| FGS | automaton marker 的 tempo-spatial slice | metric zone、external controllability、recipe | `H-RIFT-06/07`：residual ranking 与 task-specific frontier 待验证带来额外效益且成本可接受 |
| Plain PDG | data/control dependency closure | alias 精度、async/time/scope、actionability | `H-RIFT-02/03`：typed context 与 frontier 待验证提高精度 |
| MemorySSA | 函数内 memory def/use 和 clobber query | 过程间、AP/time/actionability | 仅作为证据层；不预注册“优于 MemorySSA”这种不对等主张 |
| SVF | 全程序 pointer/value-flow 基础 | control/event/time/scope/recipe | `H-RIFT-03/05`：在 SVF 上增加任务语义待验证提升 actionable output |

### 4.1 RIFT 不能主张的内容

- 不能主张首次提出 property-directed slicing；
- 不能主张首次把 automaton 与 slicing 结合；
- 不能把 MemorySSA/SVF/PDG 的能力写成 RIFT 自创新；
- 不能以“输出更多节点”证明更完整，也不能以“输出更少节点”证明更准确；
- 不能把 static reachability 写成真实因果；
- 不能以同一作者/LLM 生成并检查的标签充当独立 ground truth；
- 不能把 `PGFuzz-style`、`MoonShine-RW` 或 `ProtocolGuard-style` 适配器写成原 artifact。

---

## 5. 可运行 Artifact 与基线身份审计

| 方法 | 官方/本地身份 | 当前可执行性 | M1 允许的比较角色 |
|---|---|---|---|
| ADGFuzz | local `203fce3...` | 静态脚本可审计；完整论文工作流有缺口 | 原 parser smoke + `ADGFuzz-style` 统一 schema 基线 |
| PGFuzz | local `7eaebf2...` | runtime/policy files 部分可用；静态实现缺失 | released maps silver standard + 明示重实现 |
| MoonShine | GitHub `95e5f6d...` | 完整旧环境源码；尚未在本机跑通 | 原 `mlockall→msync` reproduction + `MoonShine-RW` adaptation |
| LTL-Fuzzer | commit `716ac301...`; Zenodo v8 | 18 个核心 target 与 AFLGo 已构建；RERS target 46/46 已解析；Telnet 3 个 target 因缺失 gitlink 未解析；完整 smoke 待完成 | manual AP tuple oracle 与 automaton guidance baseline |
| ProtocolGuard | GitHub `ecaf416...`; Zenodo 17933922 | 原 static pass 源码缺失，当前不可构建 | subjects/data；仅明示 `ProtocolGuard-style` baseline |
| FGS | Zenodo 12770067; `rmrepo/fgs:latest` | `BLOCKED_UPSTREAM_ARTIFACT_UNAVAILABLE`：Docker Hub 404/registry 401；smoke 与 NIST 未运行 | 方法级对照；工件恢复前不得列为 executed runtime baseline |
| Plain PDG | LLVM/DG 概念 | 需固定实现 | 同一 graph core 的 data+control-only baseline |
| MemorySSA | LLVM 18 | 库可用 | intra-procedural memory baseline |
| SVF | tag `SVF-3.2` / `197a659...` | LLVM 18 对齐；尚未构建 | interprocedural value-flow baseline |

### 5.1 基线命名规则

每个实验结果必须带 `implementation_provenance`：

```text
ORIGINAL_ARTIFACT
ORIGINAL_ARTIFACT_WITH_BUILD_PATCH
PAPER_DESCRIPTION_REIMPLEMENTATION
STYLE_ADAPTATION
RIFT_ABLATION
```

build patch 只能修复依赖/编译问题，不能改变算法；否则降级为 reimplementation。任何
style adaptation 必须同时保留原算法的最小可识别规则，并列出为统一任务新增的接口。

---

## 6. 实施前/实施后严格相同的评价协议

### 6.1 两阶段冻结

#### Phase A：RIFT 实施前

1. 固定 SUT commit、compile database、Property IR、AP gold、framework model version；
2. 在同一 evaluator 上运行所有可运行 baseline；
3. 输出原始 prediction JSON、日志、wall time、peak RSS 和失败状态；
4. 对不能运行的 artifact 给出可核验原因，不用零分代替；
5. 对 development/holdout split、随机种子和阈值做哈希冻结。

#### Phase B：RIFT 实施后

1. 使用完全相同的输入、gold、evaluator、机器资源上限和统计脚本；
2. RIFT 与全部 ablation 输出同一 schema；
3. evaluator 若修 bug，baseline 与 RIFT 全部重跑；
4. gold 若经仲裁修订，发布旧/新版本差异并全部重跑；
5. 禁止只展示 RIFT 成功而基线失败的筛选样本。

### 6.2 Gold set

#### 机械 gold

120 个模板化 C/C++ case 自动生成 dependency ground truth，并包含正负对照：

- direct/indirect data flow；
- control-only influence；
- alias/field/object identity；
- parameter→threshold；
- message→parser→state；
- timer/callback/queue/cancel；
- prerequisite sequence 和 mode；
- relative timing/drop/repeat/reorder；
- fake same-name/same-field dependencies；
- 多输入合取才能改变 AP。

#### 真实项目 gold

- 至少 libcoap `COAP-TX-01` 与 ArduPilot GCS failsafe；
- exact binding 和 influencers 由两名真人独立标注后仲裁；
- 报告 Cohen's κ/原始分歧，不把 Codex 输出当第二位人工标注者；
- 动态 mutation/replay 只校验可操作性，不替代静态漏边的人工/机械 gold。

### 6.3 静态指标

所有方法使用以下同一公式：

```text
Binding Top-k recall
Binding exact-match F1 on <site,phase,scope>
Influencer precision / recall / F1
Critical(MUST) influencer recall
Edge precision / recall by edge_kind
Top-k actionable precision
May/Must ratio
Slice node/edge count and reduction ratio
Recipe direction accuracy
Prerequisite exact-match and set-F1
Timing-window overlap / boundary classification accuracy
Wall time, peak RSS, timeout rate, UNKNOWN rate
```

`Top-k actionable precision` 的 denominator 包括错误和无法执行的 recipe，不能只在成功
触发的子集上计算。`UNKNOWN` 单独报告，不能当 true negative。

### 6.4 Fuzz 实用性指标

固定 harness、seed corpus、mutation operators、执行预算和 reset 策略，只替换 guidance：

```text
time-to-first-AP-flip
AP true/false valuation coverage
AP edge-transition coverage
MITL monitor location/transition coverage
deadline-boundary coverage
valid execution ratio
replay success rate
minimum prerequisite/input sequence length
time-to-first-property-violation（存在可复现 violation 时）
```

每组至少 30 个独立随机种子。time-to-event 使用 Kaplan–Meier/受限平均时间或明确的超时
处理，不能把 timeout 简单丢弃后只比较成功 run 的均值。

---

## 7. 预注册的 RIFT 待验证假设与否证门槛

### H-RIFT-01：AP 联合绑定

**待验证假设**：类型、常量、数据流、AP role 与跨 AP scope constraints 的联合绑定，相比
名称匹配和独立 AP 排名，能提高 exact `<site,phase,scope>` binding。

- 对照：name-only、ADGFuzz-style、independent lexical binding；
- 指标：Top-1 F1、Top-5 recall、abstention precision；
- 支持门槛：真实 holdout 上 Top-1 F1 ≥ 0.90、Top-5 recall ≥ 0.98，且 Top-1 F1 比最强
  自动基线至少高 10 个百分点；
- **否证门槛**：任一关键 AP 被高置信绑定到错误 phase/scope，或提升 < 5 个百分点；
- 中间区间标记 `INCONCLUSIVE`，不得写“显著优于”。

### H-RIFT-02：完整影响依赖

**待验证假设**：data+control+call/return+alias 的 contextual graph 比 assignment graph、
MemorySSA-only、SVF-value-flow-only 和 plain PDG 更完整，同时保持可接受 precision。

- 指标：critical influencer recall、总体 influencer/edge precision/recall；
- 支持门槛：机械 gold critical recall 100%，真实 gold critical recall 100%，总体 recall ≥ 95%；
- **否证门槛**：出现未标 `UNKNOWN/MODEL_REQUIRED` 的 critical false negative，立即否定
  “保守完整”主张；
- precision 若不高于 plain PDG，则只能主张功能扩展，不能主张更准确。

### H-RIFT-03：可控 frontier 的 actionability

**待验证假设**：从完整 cone 识别外部 channel/field/parameter，并进行 source→sink forward
confirmation，能比原始 backward slice 输出更高精度的可执行输入建议。

- 指标：Top-1/Top-5 actionable precision、gold source recall、无效输入率；
- 支持门槛：至少两个真实对象上 Top-5 actionable precision 比最强静态基线高 ≥ 20 个
  百分点，同时 gold source recall ≥ 95%；
- **否证门槛**：提升 < 10 个百分点，或靠删除 candidates 使 recall < 95%；
- 只有一个对象达标时结果为 `INCONCLUSIVE_EXTERNAL_VALIDITY`。

### H-RIFT-04：mutation direction 与 recipe

**待验证假设**：比较/仿射/bitmask/布尔/timeout 的局部 constraint summary 能正确给出
boundary-crossing、increase/decrease、toggle、delay/drop/repeat/reorder 建议。

- 对照：random valid value、boundary-only、PGFuzz released direction/人工 map；
- 指标：支持表达式子集的 direction accuracy、Top-k AP-flip rate；
- 支持门槛：direction accuracy ≥ 90%，且 Top-5 recipe AP-flip rate 高于最佳基线 ≥ 15 个百分点；
- **否证门槛**：任何错误 recipe 被标为 `MUST_STATIC`，或 accuracy < 80%；
- 非线性/外部状态未知必须返回 `UNKNOWN_DIRECTION`，不得猜测。

### H-RIFT-05：async/lifecycle/scope 模型

**待验证假设**：timer、callback、queue、cancel、generation 和 scope correlation 边能覆盖
MoonShine/PGFuzz/handler-centric slice 丢失的跨阶段影响，同时降低同字段不同实例误报。

- 对照：no-async、no-scope、MoonShine-RW、ProtocolGuard-style；
- 指标：async edge recall、same-field false-positive rate、prerequisite F1；
- 支持门槛：异步机械 gold critical recall 100%，same-field negative cases precision ≥ 90%；
- **否证门槛**：依赖逐性质手写 edge 才能通过，或跨对象错误仍与 field-name baseline 相同；
- framework model 必须 property-independent、版本化并在 holdout property 上复用。

### H-RIFT-06：residual-conditioned ranking

**待验证假设**：当前 MITL monitor residual/clock-zone/scope 只用于重排完整 frontier 时，能
比静态固定排序或随机 AP target 更快改变当前仍相关的 AP/monitor transition。

- 完整 cone 不允许因 residual ranking 删除节点；
- 对照：no-residual、random frontier、LTL-Fuzzer-style AP target；
- 指标：time-to-next-monitor-transition、time-to-first-AP-flip、deadline-boundary coverage；
- 支持门槛：至少两个对象的 median time-to-first relevant AP flip 改善 ≥ 1.5×，bootstrap
  95% CI 不跨 1.0；
- **否证门槛**：改善 < 1.2×、只对训练性质有效，或 residual ranking 造成 frontier recall
  下降；
- 未接入可靠 MITL residual 前，不允许提前声称该假设成立。

### H-RIFT-07：伸缩性

**待验证假设**：需求驱动、按需构图和缓存能在真实 C/C++ 项目上控制分析成本，而不会用
不保守 candidate truncation 换速度。

- 指标：wall time、peak RSS、timeout/UNKNOWN、cache hit、graph size；
- 支持门槛：libcoap 单性质 ≤ 60 s/2 GiB；ArduPilot 单性质 ≤ 30 min/12 GiB；
- **否证门槛**：超限、必须关闭 alias/control/async 才能完成，或预算耗尽却返回完整状态；
- 与 FGS 比较时分开报告任务差异，不能把不同客户端的 wall time 直接作倍数结论。

### H-RIFT-08：fuzzing 实用收益

**待验证假设**：RIFT guidance 在相同 fuzzer 下比 all-input/random、PGFuzz map、ADGFuzz、
MoonShine-RW 和 SVF slice 更快改变 AP 并覆盖 MITL transitions。

- 指标：第 6.4 节全部指标；
- 支持门槛：至少一个协议对象及 ArduPilot 上 median time-to-first AP flip ≥ 1.5× 改善，
  且不降低 valid execution ratio/replay rate；
- **否证门槛**：收益来自额外 mutation operator、不同 seed/harness、更多执行预算，或固定
  输入空间后效果与最强 baseline 无差异；
- 该假设属于 M8，不得用静态 benchmark 结果替代。

### H-RIFT-09：人工工作量

**待验证假设**：联合绑定和 reusable framework models 比逐 AP tuple、人工 synonym map、
逐性质 async edge 更少人工工作。

- 指标：每个新 property/新 SUT 的人工分钟数、人工源码定位数、property-specific model 行数；
- 支持门槛：在第二个真实 SUT 上人工时间比 PGFuzz/LTL tuple 流程降低 ≥ 50%，且准确率门槛
  不下降；
- **否证门槛**：每条性质仍需提供源码行或手写依赖路径，或 framework model 不能跨性质复用。

### H-RIFT-10：核心—model pack 分离与跨项目可移植性

**待验证假设**：RIFT core 只依赖 typed Property IR、`compile_commands.json` 和通用
Clang/LLVM/SVF graph semantics；协议栈、MAVLink 和 ArduPilot 的 API/lifecycle 知识可以
全部放在外置、声明式、property-independent model pack 中，从而在不修改核心源码的情况
下迁移到独立 C/C++ 项目。

核心与 pack 的固定边界为：

```text
RIFT core inputs:
  Property IR + compile DB + source/IR + generic graph rules + model-pack interface

External model pack:
  ingress/config/timer/callback/queue/scheduler API matchers
  argument roles, callback target, scope-key extraction, lifecycle transition

Model pack forbidden content:
  property_id/AP_id special case
  hard-coded AP source line
  property-specific dependency edge
  project-name branch compiled into core
```

libcoap、FreeCoAP/MQTT、MAVLink 和 ArduPilot 规则必须通过同一版本化 schema 外置；缺少
pack 时 core 保守返回 `MODEL_REQUIRED`，不能在 core 中补项目名判断。

- 对照：PGFuzz 的六步人工 port、LTL-Fuzzer 的逐性质 tuple、ProtocolGuard 的逐项目 config；
- 冻结方式：在微基准和 libcoap development set 完成后，记录 core tree hash；portability
  evaluation 期间 core hash 必须保持不变；
- 独立迁移对象：至少 FreeCoAP、Mosquitto 和 ArduPilot 三个独立 C/C++ 项目；若在冻结前
  因构建条件替换对象，替换理由与对象必须随 benchmark manifest 一并冻结；
- 指标：`core_changed`、core diff LoC、model-pack LoC、pack 编写分钟数、property-specific
  rule count、model reuse ratio、`MODEL_REQUIRED` rate、迁移后的 binding/influencer 指标；
- 支持门槛：至少 3 个独立 C/C++ 项目均为 `core_changed=false`、core diff LoC=0，且每个
  项目继续满足 H-RIFT-01/02 的准确率门槛；所有项目知识只存在于外置 pack；
- **否证门槛**：任一项目需要修改 core 才能完成分析；pack 含 property/AP 特判或硬编码
  源码行；或零 core 改动是通过大量 `MODEL_REQUIRED` 逃避且准确率跌破门槛；
- 若发现真正通用的 core bug，可以修复并重跑全部对象，但该次 portability trial 记失败，
  重新冻结新 core version 后才能开始下一次 trial，不能回填为“零改动迁移”。

---

## 8. 实施前与实施后比较表的固定写法

实施前只能写：

```text
Baseline observed result: <measurement>
RIFT hypothesis: PENDING
Expected mechanism: <mechanism, not a result>
Falsification gate: <pre-registered threshold>
```

实施后每个假设必须落入且只能落入：

```text
SUPPORTED
NOT_SUPPORTED
INCONCLUSIVE
```

推荐最终表结构：

| 假设 | 实施前最强基线 | RIFT 结果 | 效应量/CI | 状态 | 失败案例 |
|---|---:|---:|---:|---|---|
| H-RIFT-01 | 待 M1/M3 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-02 | 待 M3 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-03 | 待 M3 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-04 | 待 M5 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-05 | 待 M6 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-06 | 待 monitor 接入 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-07 | 待 M1/M3 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-08 | 待 M8 填写 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-09 | 待人工计时 | 待实现 | 待实现 | `PENDING` | 保留 |
| H-RIFT-10 | 待 portability freeze | 待实现 | 待实现 | `PENDING` | 保留 |

不能把失败案例删除后重算；应按 alias、control、async、scope、binding、recipe、build 和
timeout 分类，作为下一轮实现的回归集。

---

## 9. 由比较结果导出的实现约束

以下是工程约束，不是优越性结论：

1. **名称只负责召回。** 任一高置信 binding/influencer 至少需要 type、constant、data-flow、
   control、alias、framework model 或动态确认中的一项结构证据。
2. **完整 cone 与 ranked frontier 分离。** residual 只能排序，不得删除保守 cone。
3. **双向确认不能破坏 recall。** backward cone 中无法 forward-confirm 的节点仍以
   `MAY_STATIC` 保留，只降低 actionable rank。
4. **对象和 scope 进入节点身份。** 不能复刻 MoonShine 的纯 `struct.field` 相等。
5. **过程间分析不能只靠 MemorySSA。** MemorySSA 明确是 intraprocedural；跨过程由 SVF/
   summaries/call-return edges 承担。
6. **async edge 必须可审计。** timer/callback/queue 模型记录版本、API matcher、参数角色和
   unknown fallback，缺模型返回 `MODEL_REQUIRED`。
7. **original 与 adaptation 分开。** 统一 schema adapter 不得隐藏算法变化。
8. **所有不确定性显式化。** `AMBIGUOUS`、`MODEL_REQUIRED`、`BUDGET_EXHAUSTED`、
   `UNKNOWN_DIRECTION` 和 `INCONCLUSIVE` 都进入指标。
9. **项目知识全部外置。** core 只接受 Property IR、compile DB、通用图和 model-pack
   interface；libcoap/MQTT/MAVLink/ArduPilot 规则只能进入通过 schema 验证的 model pack。

---

## 10. MoonShine 对 RIFT 的最终判断

MoonShine 对本任务**有用，但不是可以直接移植的静态分析器**。

最有价值的抽象是：

```text
external operation A
  --writes shared semantic state-->
conditional/event of operation B
  --changes control path-->
target AP
```

这补充了单纯 def-use slice 容易忽视的“某个先前操作通过共享状态改变后续分支”问题，也
提示 fuzz guidance 必须输出前置操作序列。然而，MoonShine 的 `W∩R_cond` 只在
`struct.field` 粒度工作，既不验证同一实例，也不表达写入值是否真的能改变条件。因此：

- 把它实现为低成本 baseline 是合理的；
- 把它作为 RIFT 候选 event edge 的高召回生成器是合理的；
- 把它当 alias/path/scope 正确的依赖 oracle 不合理；
- 把 MoonShine 原论文覆盖提升直接外推到 MITL AP fuzzing 不合理。

---

## 11. M0 完成判定与下一道硬门

RIFT-M0 的完成产物是本文件和机器可读矩阵。此时可成立的只有：

1. 问题定义已经从“插桩位置”收紧为“AP influence→controllable frontier→recipe”；
2. MoonShine 的可复用机制和不可迁移假设已经分离；
3. 与 ADGFuzz、PGFuzz、LTL-Fuzzer、ProtocolGuard、FGS、PDG、MemorySSA、SVF 的边界已
   显式化；
4. 十个 RIFT 优势均保持 `PENDING`，并有实施前/后相同 evaluator 和否证门槛；
5. 不能运行的原 artifact 不会被伪装成公平 baseline。

下一道硬门是 RIFT-M1：至少跑通一个原始高质量论文 artifact，并冻结 baseline 输出、
容器/image digest、测试集和资源数据。LTL-Fuzzer 的部分构建与 target 导入尚不等于完整
smoke；FGS 的上游不可用状态应作为阻塞证据保留。在硬门关闭前，不应将 RIFT 设计目标
写成已验证结论。
