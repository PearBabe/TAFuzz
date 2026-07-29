# CoAP RFC → MITL → libcoap 审计范围与准入契约

状态：`FROZEN_SCOPE / NO_PROPERTY_APPROVED`

冻结日期：2026-07-15（Asia/Shanghai）

## 1. 目标

本轮工作建立两条彼此分离、但最终可复用同一事件与 verdict 基础设施的链路：

1. **完整规范审计链**：从十份 CoAP RFC 中穷举与时间、顺序、状态保持、状态终止、
   生命周期、重传和有界等待有关的候选；逐条核对完整规范上下文；给出参数化 MITL、
   数据谓词和固定 libcoap 源码映射。
2. **CVE 差分 demo 链**：选择一个已有公开记录、已有修复、能够在旧版与修复版间稳定
   复现差异的 libcoap CVE，跑通依赖分析、LLVM 插桩和 verdict。不得为了迁就 CVE
   而伪造 RFC 性质；若某 CVE 只能证明崩溃而不能证明 RFC 时间性质，必须明确区分
   robustness verdict 与 RFC-conformance verdict。

端到端目标为：

~~~text
RFC evidence
  -> reviewed semantic candidate
  -> parameterized MITL + data predicates
  -> EventRequirement
  -> fixed-commit libcoap dependency/source mapping
  -> HookPlan
  -> LLVM instrumentation
  -> raw event trace
  -> AP projection / correlation / closure
  -> SATISFIED / VIOLATED / UNKNOWN / NOT_EXERCISED
~~~

## 2. 冻结 RFC 语料

首轮完整语料严格限定为以下十份：

1. RFC 7252 — The Constrained Application Protocol (CoAP)
2. RFC 7641 — Observing Resources in CoAP
3. RFC 7959 — Block-Wise Transfers in CoAP
4. RFC 8132 — PATCH and FETCH Methods for CoAP
5. RFC 8323 — CoAP over TCP, TLS, and WebSockets
6. RFC 8613 — OSCORE
7. RFC 8768 — CoAP Hop-Limit Option
8. RFC 8974 — Extended Tokens and Stateless Clients in CoAP
9. RFC 9175 — Echo, Request-Tag, and Token Processing
10. RFC 9177 — Q-Block1/Q-Block2 Robust Block-Wise Transfer

只有在解释以上 RFC 的定义、更新关系、勘误、参数来源或规范前提确有必要时，才追踪
它们引用的其他 RFC。当前 libcoap README 另外列出的 RFC 7390、7967、8516 不属于
本轮首批语料，不得静默扩充范围。

## 3. 冻结实现与首个运行 profile

- 源码：`benchmark/coap/libcoap`
- commit：`94bacc8939dd6711169cd2332a002a361ec62531`
- describe：`v4.3.5-390-g94bacc89`
- 首个 runnable profile：基础 CoAP/UDP、no-DTLS。
- 十份 RFC 仍全部做规范候选和源码映射审计；不在首个构建 profile 中启用的功能必须
  标记为 `PROFILE_DISABLED`，不能据此判定实现满足或违反性质。

所有源码证据必须固定到上述 commit，至少记录文件、函数、行、相关字段或数据结构、
写入点、分支/调用条件、可能的多个 producer，以及最终 truth point 的选择理由。

## 4. 规范证据要求

每条候选必须记录：

- RFC 编号、正式版本、章节、页码、段落边界和官方链接；
- 足以判断语义的上下文，包括定义、前置条件、例外、取消、替代路径和配置条款；
- 忠实的完整中文语义拆解和必要的短原文片段；
- RFC errata、updates/obsoletes 关系及其对本条规则的影响；
- 规范强度和角色：`MUST/MUST NOT/SHALL`、严格算法蕴含、`SHOULD`、`MAY`、
  informative；
- 每一个数值界的逐步来源。不得把默认值冒充通用值，不得把实现观察窗口冒充 RFC
  deadline，不得自行增加有限上界。

两篇论文（ProtocolGuard；2024 CoAP requirement-testing）只可用于候选发现、源码切片
线索和实验设计，不可充当 RFC 真值来源，也不可替代本轮上下文审计。

## 5. Verdict 边界

- `MUST/MUST NOT/SHALL` 和能从规范算法严格推出的约束，才可进入正式
  RFC-conformance `VIOLATED`。
- `SHOULD/SHOULD NOT` 单独报告为 recommendation deviation，不与强制违反混合。
- `MAY` 只定义允许路径、取消、supersession 或边界，不独立构成违反 oracle。
- profile 未启用、事件丢失、时钟/顺序/关联歧义、源码映射未证明、closure 未完成，
  必须返回 `UNKNOWN`；零 trigger 为 `NOT_EXERCISED`。
- CVE 造成的崩溃可作为单独 robustness verdict；只有存在完整 RFC 推导时，才允许同时
  声称 RFC-conformance violation。

## 6. 参数化与形式化要求

每条带参数的性质同时保留：

1. RFC 符号公式；
2. RFC 默认 profile 实例；
3. 运行时 libcoap 配置实例及读取证据。

若准确性质超出现有五种模板，允许扩展 `RFCtoMITL`、PropertyContract、sidecar 和监控
逻辑；不得为了复用模板而改变 RFC 语义。数据相关条件先定义为可审计 AP predicate，
MITL AP 字母表保持稳定，动态 MID、Token、Block NUM、endpoint 等值只作 correlation
metadata。

## 7. AP 与源码映射要求

AP 可以依赖以下任意组合：

- CoAP header、code、type、MID、Token 和 option 字段；
- `coap_session_t`、sendqueue、large-transfer、observer、OSCORE 等内部状态；
- timeout、absolute tick、counter 和配置参数；
- 数据结构插入、删除、重排、generation 变化；
- 函数调用、具体 callsite、基本块、分支和返回结果；
- 网络写入 attempt/success 和 peer 输入事实。

SUT 只发 raw facts，不能直接发复合 AP 或“违规事件”。trigger 与 decisive outcome/bad
必须有独立证据链。若同一 AP 有多个可能生产点，全部列出并说明覆盖关系；函数返回点
过宽时必须细化到调用点、分支或路径条件。

## 8. 候选准入状态

状态只能按证据推进：

~~~text
CANDIDATE
  -> RFC_CONTEXT_CHECKED
  -> FORMULA_CROSS_CHECKED
  -> SOURCE_MAPPED
  -> INSTRUMENTED
  -> RUNTIME_VALIDATED
  -> USER_APPROVED
~~~

任何自动工具、LLM、Codex 或自填 reviewer 字符串均不能产生 `USER_APPROVED`。每轮内部
复核必须记录检查内容和发现的问题，但不得称为独立人工审阅。

## 9. 历史材料处置

以下材料只作线索源，所有性质都必须从 RFC 正文重新推导：

- `src/RFCtoMITL/fixtures/rfc7252/` 中现有四条 CoAP fixture；
- `analysis/protocol_fuzzing_study/protocols/coap/` 中现有七条“合格性质”及其
  `ROOT_REVIEWED` 标签；
- 使用旧 libcoap commit `7cf7465b...` 的历史源码行号和 Hook 描述。

在本轮审计完成并经用户确认前，以上材料不得被描述为已批准的正式 oracle。

## 10. CVE demo 准入门槛

CVE 候选至少满足：

- 有正式 CVE 或上游 issue/PR/commit 证据；
- 可固定一个受影响 commit 和一个修复 commit；
- 可以离线、确定性、合理时长地复现旧版结果；
- 相同 testcase 在修复版产生明确不同结果；
- 触发序列、构建 profile、退出码、异常和日志可保存；
- 能定义非循环的 trigger 与结果观察点，并通过真实 LLVM hook 产生 trace；
- 不把不可复现的长时间 fuzz 报告或后来被上游判为 false positive 的条目当成 demo。

