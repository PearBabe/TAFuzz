# RIFT-M4 可移植生产核心架构冻结

冻结时间：2026-07-18。本文档在生产核心完成前固定 M4 的实现边界、失败语义和验收口径；后续若修改，必须记录原因并重新运行全部门禁。

审计修订（2026-07-18）：初版 schema 和物理路径身份无法证明产物无损、重定位稳定及证书来源闭合，因此在正式 M4 结果产生前升级 semantic-index/CIG 到 `2.0.0`，并加入逻辑路径、构建期 manifest 和无损快照门禁。这是对未发布草案的 fail-closed 修复，不是对实验结果的事后调参。

## 1. M4 的目标与非目标

M4 接收 typed temporal Property IR、原始 `compile_commands.json`、C/C++ 源码以及可选的版本化声明式模型包，输出：

1. 跨翻译单元 `semantic_index.json`；
2. 联合角色 `ap_bindings.json`；
3. 带完整上下文身份的 `contextual_influence_graph.json`；
4. 不被排名裁剪的 `ap_influence_cones.json`；
5. 绑定输入、工具链、输出和不完整项的 `analysis_certificate.json`。

M4 不实现外部可控 frontier、SMT mutation recipe、residual ranking 或新的 fuzz scheduler；这些分别属于 M5 及以后。M4 也不把通用 PDG、MemorySSA、SVF、对象敏感或 Z3 本身写成创新点。当前可检验的方法贡献候选仅是：

> typed temporal-role 联合绑定，与具有 context/object/field/phase/task/scope/generation 身份和完整性证书的保守影响锥相结合。

## 2. 可移植性硬边界

通用代码仅允许位于 `src/StaticAnalysis/{core,include,cli,schema}`，并且只能消费：

- typed Property IR；
- 原始 compilation database 和由 Clang/LLVM/SVF 导出的事实；
- 符合冻结 schema 的、版本化且 property-independent 的模型包。

通用代码禁止包含项目名、项目路径、项目符号、性质 ID、benchmark case ID 或期望依赖边。协议、框架和项目知识只能进入 `model_packs/`。模型规则不得表达 per-property slice、hand-selected dependency path、expected-answer edge 或 benchmark-case branch。

最终可移植性结论必须由同一 analyzer binary、同一输出 schema、同一 canonical core tree 和相同 child-toolchain semantics 在至少三个独立 C/C++ 项目上产生，且项目之间 core source change 为零。完成 M4 微基准或单个真实项目不能等价为通过此门禁。

“同一 core”不得由项目记录自行声明。最终 evaluator 必须从 analyzer 证书、构建期嵌入 manifest 和实际文件重新计算并交叉验证。每个项目运行都要绑定真实 Property IR、compile DB、源码依赖、模型包、输出字节和资源测量；三个不同的 `project_id` 字符串不构成独立项目证据。

## 3. 数据通路

```text
raw compile DB
  -> CompilationPlan
  -> per-TU Clang fact shards
  -> SemanticIndex (USR / ExprSite / CFG / object / callsite)
                     \-> LLVM/SVF AliasOracle evidence

typed Property IR
  -> JointBinder (all temporal roles jointly constrained)
  -> conservative BindingSeedSet
  -> realizable backward query
  -> CIG + AP influence cone + completeness certificate
```

相似名称或 LLM 只允许召回候选。`CONFIRMED` 绑定至少需要一种非相似度语义证据，例如 USR、限定签名、精确源码位置、类型化字段路径、表达式结构、AST/LLVM value-flow、control/call/scope/path constraint。

## 4. 稳定语义身份

节点键固定为以下维度：

```text
<source entity, abstract object, field access path, call context,
 lifecycle/CFG phase, task or thread, scope, generation, source evidence>
```

- declaration 使用 Clang USR；字段路径使用 `FieldDecl` USR 链，而不是字段名字符串；
- 无 USR 的表达式使用文件内容摘要、spelling/expansion offset、AST kind、外围函数 USR 和 compile-command variant 构造 `ExprSiteId`；
- 行号仅作可解释证据，不作跨版本语义身份；
- 同一源文件的不同编译配置保留为独立 variant；头文件 ODR 实体只有在 USR 和 token/配置身份一致时才能合并；
- 无法区分的对象必须进入显式 `TopObject`/summary/unknown，而不是静默合并后宣称精确。

任何参与稳定身份的路径都必须先映射为：

```text
riftpath://v1/<logical-root-id>/<percent-encoded-relative-path>
```

路径映射只把稳定 root ID 纳入摘要，不能把 checkout/build 的物理绝对路径纳入节点、TU、调用点或产物身份。未落入声明 root 的非系统路径必须 fail closed；不能退化成 basename。相同输入复制到两个不同绝对目录后，四个 canonical analysis artifact 的字节与语义 ID 必须完全一致，物理路径只能出现在不参与身份的 provenance 中。

## 5. 依赖和可实现路径

M4 至少提取 initializer/assignment/compound update、SSA/def-use、memory/field、CFG control dependence、direct call/return、actual/formal、out-parameter、alias 和全局读写。

过程间查询必须是 callsite-tagged 且调用栈平衡的：反向越过某个 return 边时压入其 callsite，离开 formal 时只能匹配同一 callsite。递归超出上下文预算时折叠为 `RECURSIVE_WILDCARD/MAY` 并登记不完整项，不能截断候选。该约束专门消除 M3 plain-PDG 中共享 formal/return 造成的跨调用点污染。

函数 summary 至少表达：

- formal 到 return；
- formal/global 到 pointer/reference out-write；
- global read/write；
- 条件和 control prerequisite；
- unresolved indirect call 或 unknown memory effect。

SVF/MemorySSA/AA 是 alias/间接调用的证据提供器；SVF 运行时数字 node ID 不得成为稳定身份。

## 6. 失败语义与完整性账本

所有产物必须显式保留 `must`、`may`、`modelled` 和 `unknown`。至少区分：完整保守结果、歧义绑定、需要模型、未解析调用、上下文/资源预算耗尽和工具失败。

只有 coverage ledger 证明相关 TU、绑定候选、调用目标和内存效果均已闭合时，无路径才可解释成分析抽象下的 `NO_INFLUENCE`。否则只能输出 `UNKNOWN` 或 `CONSERVATIVE_INCOMPLETE`，并列出影响范围。排名永远不能删除完整 cone 中的候选。

## 7. M4 验收口径

### 7.1 机械 gold 微基准

分析阶段只能读取源码、原始 compile DB 和由公开 AP marker/源码语义生成的 Property IR。全部分析完成后，独立 evaluator 才能读取 M2 ground truth。

主 recall 门禁定义为：所有 gold `MUST_INFLUENCE` source-to-AP pair 均至少出现在 conservative cone。它不要求分析器把每条路径的静态 certainty 冒进地标成 `must`；模板的 MUST 关系也不表示任意输入值改变都能翻转 AP。另行报告：

- exact MUST classification；
- MAY/MUST precision 和 recall；
- influence-edge kind recall；
- AP binding Top-1 site/phase/scope；
- unsupported、unknown 和 incomplete 数量；
- 共享 helper 的两调用点污染回归；
- pointer out-write、early return、switch、宏 variant 和多 TU 同名实体回归。

### 7.2 当前真实项目

当前可运行 libcoap 冻结版本是 `94bacc8939dd6711169cd2332a002a361ec62531`；既有 COAP-TX-01 map 属于旧 `7cf7465b...`，只能作历史线索。M4 必须在当前 commit 重新定位并保留 source-version drift；在两名真人独立标注和仲裁完成前，不得声称真实项目 gold recall 100%。

M4 可验证当前源码中不依赖框架模型的值流，例如 ACK timeout/random factor 到 timeout/deadline/queue state 的路径。queue/timer/callback 的完整 property-independent 外部模型和跨协议迁移属于 M6；不得为了通过一个性质在 M4 core 中手加边。

## 8. 冻结的生产 schema

M4 使用八个 Draft-07 schema：semantic index 与 CIG 为无损 `2.0.0`；analysis certificate 为来源闭合的 `2.0.0`；common、typed property IR、AP bindings、AP influence cones 和 model pack 保持 `1.0.0`。此前 semantic-index/CIG `1.0.0` 会折叠枚举并遗漏下游消费字段，certificate `1.0.0` 也不能闭合证明构建、环境、运行时映射与源码输入，均视为未发布且不可用于验收的草案。schema 关闭额外字段，要求完整候选记账、显式 unknown、modelled edge 的 rule evidence，以及可重算的 binary/core/schema/toolchain/source-input 哈希。

`semantic_index.json` 和 `contextual_influence_graph.json` 必须是参与后续计算的 canonical analysis snapshot，而不只是解释投影。改变 `access_path`、callsite、condition、uncertainty、semantic-node reference 或其他下游消费事实必须改变相应 artifact digest。生产源码和 schema 摘要在构建时按相对路径与文件字节生成并嵌入 analyzer；运行时参数不能用另一目录覆盖该声明。

JSON Schema 只负责结构；loader 还必须验证跨文件引用、ID 唯一性、公式/AP/selector 引用闭合、区间 `lower <= upper`、输入/输出 digest 和模型 selector/capture 引用。

## 9. M4 完成条件

以下条件全部满足后才能宣布 M4 完成：

1. raw compile DB 多 TU index、typed joint binding、CIG 和 conservative cone 使用同一生产二进制跑通；
2. M2 gold MUST cone recall 达到 100%，并完整报告 precision/UNKNOWN/失败案例；
3. libcoap 当前 commit 的 provisional acceptance 跑通，版本漂移和真人仲裁状态明确；
4. schema、core regression、M3 historical bundle、portability implementation gate 全部通过；
5. 未在通用核心发现项目/性质/答案字面量；
6. 生产 binary 不链接仅供 M3 weak-baseline 使用的实现；SVF/Z3 只有在生产语义实际消费时才进入依赖和证书；构建 manifest 的重定位与 core/schema 分离回归通过；
7. relocation A/B 的 canonical 产物与语义 ID 完全相同；
8. `.codex/PROJECT_STATE.md` 和 `.codex/SESSION_LOG.md` 已更新。

M4 通过仍只证明核心边界和当前对象的实现证据。只有后续同一 binary/schema/core 在至少三个独立真实 C/C++ 项目上由 artifact-backed gate 复核通过，最终报告才允许写“已验证可移植”。
