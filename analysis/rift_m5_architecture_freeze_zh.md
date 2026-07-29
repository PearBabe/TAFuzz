# RIFT-M5 可移植 TAFC 架构冻结

> 冻结日期：2026-07-18  
> 状态：`IMPLEMENTATION_CONTRACT / PRE_PRODUCTION_CODE`  
> 前置：RIFT-M0--M4 已完成；M4 保守 cone 与证书语义不变。  
> 研究对象：`PENDING_NOVELTY`，不是既成创新结论。

## 1. 冻结结论

M5 不把 backward slice、前后向可达、SMT、model pack 或 monitor ranking
单独包装成新算法。这些组件都存在强先例。M5 唯一待实验检验的研究对象是：

> **TAFC（Temporal Action Frontier Contract）**：把 typed metric-temporal
> AP 转换为携带边界绑定、可实现 witness、scope/generation/lifecycle、前置
> 偏序、相对时间窗、变异关系、证据轴和 replay obligation 的语义外部动作
> 合同。

最强碰撞是 CFPOFuzz、CodeQL custom models、关系求解和 RESTler/OGHARN 的
组合。若公平复合基线在同一输出合同上没有实质差异，M9 必须把贡献降级为
工程集成，不得更换指标。

## 2. 可移植性是发布硬门禁

通用核心只能读取：

```text
typed Property IR
canonical Clang/LLVM semantic facts
immutable M4 CIG/cone
versioned declarative model packs
optional executor capability manifest
optional residual state used only for ranking
```

核心目录中禁止出现项目、协议、性质、AP、benchmark case、期望 node/edge、
物理路径、源码行号或答案常量。项目知识只能进入独立 pack；应用私有符号的
pack 必须标记 `project_adapter`，不能支持 framework portability 声明。

最终可移植性必须同时满足：

1. 至少三个独立真实 C/C++ 项目使用相同 analyzer binary、core hash、schema
   bundle 和子工具链语义；
2. 项目间 core source diff 为零；
3. pack digest 在读取 Property IR、gold 或实验 outcome 前冻结；
4. 至少一个 platform/framework pack 在未见性质或共享框架 holdout 上零修改
   复用；
5. 分开报告 pack 规则量、人工时间、UNKNOWN、executor adapter 工作量；
6. 真实项目准确率仍需两名真人独立标注与仲裁。

只在三个项目生成 JSON 不足以通过门禁。每条性质新增规则、每个 AP 写专用
selector，或把应用私有函数伪装成 framework API，均判 portability 失败。

## 3. Benchmark-first 证据

生产实现前已冻结并执行独立 gate：

- CFPOFuzz 官方 ICSE 2026 repo：
  `62ee6abf14e0698af15743676ea56ee4db845d0c`；官方只发布 Docker 镜像，
  当前 WSL 未启用 Docker integration，因此 demo 为
  `BLOCKED_ENVIRONMENT`，不是复现成功；
- 官方 `sv-benchmarks@svcomp26`：
  `7efe28dd29576b46927b7a34e8f742bd90966a75`；
- 9/9 deterministic bit-vector task 的 `reach_error` 结果与 YAML 一致；
- 15/15 signed-overflow task 的 Clang 18 UBSan concrete result 与 YAML
  一致；该结果不是通用证明；
- 10/10 infeasible-control-flow task 已编译为 LLVM IR，官方 verdict 仅作为
  challenge label，尚无 reference verifier 复现；
- gate SHA-256：
  `01c63e66ee528d7672c3cd57331e4df9916942980005c509566aa5ff9b51bdf6`。

M1 已成功执行至少一个原始 CCF-A artifact，因此外部 CFPOFuzz 环境阻塞不
阻止编码；它仍阻止任何“已优于 CFPOFuzz”表述。

## 4. 不可变 M4 与 M5 sidecar

M5 不修改、删除或重新分类 M4 cone member。即使局部 solver 把某一条
witness 判为 UNSAT，也只能改变该 frontier witness 的 feasibility；保守 cone
和其它 UNKNOWN 路径保持原样。

这里的“不可变”严格指**同一次分析中 M4 阶段产出的 cone 不会被后续 M5
阶段裁剪或改写**，不表示不同 analyzer 版本必须与 2026-07-18 冻结的 M4
binary 逐字节相同。若 M5 集成期间修复了 M4 indexer/binder 的通用缺陷，必须
重新跑受影响的 M4 benchmark 并报告差异；`m4_cone_immutable` 不能被解释为
跨版本 byte-equivalence 声明。当前 case_001 enriched 输入已经和冻结 M4 四产物
逐字节核对；完整 120-case 仍由最终 M5 sealed run 重新评估。

新增产物固定为：

```text
model_fact_overlay.json
predicate_occurrence_bindings.json
frontier_candidates.json
fuzzable_frontier.json
mutation_recipes.json
recipe_replay_obligations.json
m5_analysis_certificate.json
```

每个产物 canonical sort、稳定 ID、摘要闭包并可独立验证。`frontier_candidates`
保留 candidate、actionable、rejected 与 UNKNOWN 完整账本；
`fuzzable_frontier` 只是方便消费者读取的 actionable projection，不是删减证据。

`predicate_occurrence_bindings` 是 M5 additive sidecar：它只对 Property IR 中
predicate 引用的 source-location selector 定向重解析相关 TU，把精确
`DeclRefExpr/MemberExpr` token 绑定到现有 M4 semantic identity。它不得新增、
改写或重分类 M4 SemanticIndex/CIG/cone 节点；宏、pointer alias、跨 TU 多候选
或唯一 identity 无法闭合时必须输出 `UNKNOWN`。

## 5. ExternalAction 与程序节点分离

```text
ExternalAction =
  <action_schema_id, action_class, channel, operation,
   typed_payload_schema, payload_slot,
   scope_schema, generation_schema, timing_capability>

BoundaryAttachment =
  <external_action_id, contextual_node_id,
   transfer_relation, rule_match_evidence>
```

parser 后局部字段、参数缓存和内部状态不是 external action。一个 action 可以
attach 到多个编译变体/边界节点；一个节点也可由多个 channel/action 到达。
去重按完整 action identity，不按变量名、最近节点或 shortest path。

pack 只能声明 `required_capability`。实际 controllability 必须和独立 executor
capability manifest 求交：`DIRECT/SEQUENCE/TIMING/ENVIRONMENT/UNAVAILABLE/
UNKNOWN`。没有 executor manifest 时不得由 pack 自证“可直接控制”。

## 6. Model-pack/2.0.0 有限 VM

`model-pack/1.0.0` 保留为 M4 非执行占位；M5 只执行不兼容的 v2。VM 必须在
Property IR 进入进程级 pipeline 之前运行，只能读取 canonical SemanticIndex
事实。其指令集冻结为：

```text
MATCH(selector -> canonical program fact)
CAPTURE(typed role -> match/projection)
JOIN(same_object | same_scope | same_generation |
     same_handle | same_callsite | same_task)
EMIT(fixed typed fact)
```

允许输出：

```text
external_boundary
semantic_transfer
event_link
timer_transition
queue_transition
lifecycle_transition
scope_key
clock_relation
persistence_transition
```

首版允许固定 projection，例如 function formal parameter、call argument、receiver
和 return slot；这些 projection 由 core 定义，pack 不能提供脚本。禁止任意
代码、递归、负递归、动态库、文件/网络/环境访问、自定义算术、Property/AP
查询和图 reachability 查询。closure、balanced traversal 和 solver 由 core
实现。

pack fact 只能是 `MODELLED` 或 `UNKNOWN`，不能直接产生 `MUST`。每条 fact
必须记录 pack ID/version/digest、layer、target version/ABI、rule、selector、
capture、匹配 site、certainty 和资源账本。

### 6.1 静态拒绝

portable platform/framework pack 必须拒绝：

- 任意字符串字段中的 property/AP/case/expected-answer/oracle 标记；
- source-location、物理/相对路径、行列 selector；
- analyzer node/edge ID、手选 dependency path、gold/result/replay 输入；
- 重复 ID、dangling ref、未绑定 EMIT capture、空 rule/capture；
- 未声明 layer/version/ABI/evidence/digest policy；
- 递归、未绑定变量、越界 projection、资源上限为零；
- framework layer 中的已声明应用私有 signature。

schema 无法识别改名或哈希后的答案编码，所以还必须执行 pack-before-property、
字符串扫描、digest freeze、holdout、规则复用率和人工审计。

## 7. Frontier 算法

对 AP/role sink `a` 与动作 `x`：

```text
B(a) = immutable M4 backward cone
F(x) = balanced forward reach from every boundary attachment
W(x,a) = compatible concatenable witnesses in B(a) intersect F(x)
```

不能只做节点集合交集。witness 必须检查 call/return、object/field、scope、
generation、task 与 lifecycle 相容性，并保留 DAG/多路径而非一条 shortest
path。

分类规则：

- 存在 witness：保留 candidate；
- 空交且任一 attachment/forward/cone/compatibility ledger 不完整：`UNKNOWN`；
- 空交且全部闭合：`NO_STATIC_WITNESS`；
- 至少一条 SAT：existentially feasible；
- 只有全部 attachment、全部 witness 都 UNSAT，且枚举和 encoding 完整，才可
  从 actionable projection 排除；rejected ledger 仍保留；
- Top-k 只限制 solver/ranking 预算，不裁剪 candidate/witness；
- dynamic refutation 与 residual ranking 都不能删除静态 candidate。

M4 四类 path mask 语义继续使用。pack attachment 为 MODELLED，因此经 pack
发现的 action-to-AP witness 通常至多 MODELLED。SAT、executor capability 和
runtime replay 分别只更新自己的证据轴，不能升级 reachability。

## 8. Recipe 与 C/C++ 语义

证据固定拆成：

```text
reachability
controllability
path_feasibility
mutation_semantics
runtime_evidence
model_provenance
completeness_ledger
```

第一版的 total semantics 是：任何 unsupported、timeout、模型缺口都输出
`UNKNOWN`，不得缺项或静默删除。

Tier 0 支持整数/枚举/布尔比较、bitmask、仿射式、threshold/interval、
presence/absence/count/drop/repeat/reorder 和显式 timeout/deadline。优先输出
boundary set，而不是未经证明的 UP/DOWN。

Tier 1 两副本局部查询：

```text
Phi_w(X,S) and Phi_w'(X',S')
and SameExceptTargetAction(X,X')
and SameInitialScopeGenerationState(S,S')
and AP(X,S) != AP(X',S')
```

结果区分 `SAME_PATH_FLIP` 与 `CROSS_PATH_FLIP`。SAT 只证明局部 summary 下
存在 candidate pair。只有反方向 counterexample 为 UNSAT 才能输出
`MONOTONE_UP/DOWN`。保存 query digest、assumption literals、solver/version、
model 或 UNSAT core、timeout。

必须保持 Clang 位宽、signedness、integer promotion、cast、unsigned wrap 和
signed-UB 条件；浮点必须使用 IEEE-754 并考虑 NaN/Inf/signed zero。不能完整
编码时输出 HEURISTIC/UNKNOWN。当前本机 Z3 是 `4.8.12`，证书记录实际版本，
不得写成计划中的其它版本。

## 9. Prerequisite、joint action 与 timing

recipe 是带选择的偏序族：

```text
OR {
  joint-action hyperedge,
  prerequisite DAG,
  scope/generation constraints,
  relative timing constraints
}
```

多个输入联合才能改变 AP 时必须保留一个 hyperedge，不能拆成多个各自声称
可翻转的 recipe。alternative path 保留 DNF/choice groups，不能取错误 union
或 intersection。cycle、callback handle 或 generation alias 不闭合时输出
`PARTIAL_ORDER_UNKNOWN`。

timing 至少绑定 clock/source、unit、epoch、quantum、jitter、wrap、comparison
endpoint、start/end event 和 scope/generation。缺项时只给宽化区间与
pause/drop/repeat/reorder 动作类型；不得伪造精确纳秒。

## 10. CLI 与阶段顺序

```text
tafuzz-sa influence   # M4-only contract remains available
tafuzz-sa frontier    # full M4 + model VM + frontier sidecars
tafuzz-sa recipes     # full M4 + frontier + recipe/replay sidecars
tafuzz-sa explain     # M9 explanation projection
```

`frontier/recipes` 至少需要 `--compile-db --property --model-pack
--output-dir`，可重复 `--model-pack`。执行顺序固定：

```text
compile plan/index
-> load/freeze packs
-> execute VM without Property IR
-> load Property IR
-> exact predicate-occurrence sidecar (M4 remains immutable)
-> bind AP
-> build immutable CIG/cone
-> materialize contextual overlay
-> bidirectional frontier
-> local recipe queries
-> serialize all sidecars
-> certificate digest closure
```

## 11. 最低实现门禁

M5 不能仅以“能输出 JSON”完成。最低门禁是：

1. v2 schema 与 C++ loader 对重复/dangling/路径/答案泄漏/空规则/错误 capture/
   资源耗尽 fail closed；
2. 指令/规则/selector 顺序置换产生相同 canonical overlay；
3. parser 后内部字段不会被误报为 external action；
4. one-action/multi-attachment 与 multi-action/one-node 不错误合并；
5. shared-callsite、object、scope、generation 负例不产生已确认假路径；
6. 空 meet + coverage gap 为 UNKNOWN，不是 NO_STATIC_WITNESS；
7. solver timeout/unsupported 不删除 candidate；
8. signed/unsigned promotion、overflow、bitmask、bool、enum、float special value
   用官方 SV-COMP challenge 回归或明确 UNKNOWN；
9. joint input 保留 hyperedge，prerequisite alternatives 保留 choice；
10. checkout relocation 后 canonical sidecar byte-identical；
11. 关闭 pack 时 M4 四产物不变，只增加 model gap/UNKNOWN；
12. 同一 binary/schema/core 至少在三个真实项目零 core 修改运行，才允许使用
    “portable”实验结论。
13. 动态阈值的 observed/bound selector 必须由 exact occurrence identity 分开；
    单引用 AP-site 回退只能是 HEURISTIC，多引用不得猜测，control-only 必须
    保持 UNKNOWN。
14. 正式 benchmark analyzer 必须运行在最小只读 allowlist sandbox，逐 case
    私有 `/tmp`，既有 gold/评估结果和其它 case 输出不可见；evaluator 必须用
    冻结 verifier 重验物理证书并接受外部 run-manifest SHA commitment。

静态目标继续采用用户预注册门槛：fuzzable-source recall >=95%、critical/must
detection 100%、supported direction accuracy >=90% 且覆盖率必须同时报告。
真实对象 Top-5 actionable precision 和 fuzz utility 的优势必须留到 M8/M9，
当前不得预写为结果。
