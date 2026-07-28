# ProtocolGuard 方法审计与自然语言到 MITL 的适配方案

## 1. 采用结论

ProtocolGuard 可借鉴两类能力：

- 保留章节层级，在同节上下文中恢复指代、因果和依赖从句；
- 把规范字段绑定到源码语义身份，并保留切片/位置证据。

不能照搬其候选过滤、规则 JSON、单消息流约束、时间词处理、由当前实现筛选规则或最终一致性判断。它的任务是从网络协议规范中抽取单次消息处理规则并检查实现，而本任务需要跨模式、跨消息、历史状态、配置参数、连续时间和多时钟域的性质。ProtocolGuard 的最终规则结构也没有足够字段表达 MITL 的触发、取消、例外、时钟与关联语义。

本适配方案建立“规范提取 lane”和“源码绑定 lane”的硬隔离；任何源码、测试或运行轨迹都不能发起、修改或删除性质。固定结论仍为 `implementation_satisfaction: NOT_ASSESSED`。

## 2. 冻结材料

| 对象 | 身份/链接 | 用途 |
|---|---|---|
| 论文 PDF | 18 页；SHA-256 `58ca7687749493ad350495b25fee0e510a0c39a22cb6b667845eee183229d11f` | 论文方法 |
| 官方论文页 | [NDSS 2026 ProtocolGuard](https://www.ndss-symposium.org/ndss-paper/protocolguard-detecting-protocol-non-compliance-bugs-via-llm-guided-static-analysis-and-dynamic-verification/) | 作者、摘要、官方 PDF 入口 |
| 官方 artifact | [Zenodo record 17933922](https://zenodo.org/records/17933922)，version v1，DOI `10.5281/zenodo.17933922` | 核对实际代码 |
| 本地 artifact | `/home/lqq/project/TAFuzz/tool/ProtocolGuard` | 逐行审计 |
| artifact ZIP | SHA-256 `20b84c9910a91c1132516f15a1cc446e34f32849b7a8b028a10c8d259ef8f5c7` | 完整性记录 |

官方 Zenodo 页面标明 artifact 于 2025-12-15 发布、v1、文件 MD5 `beb20443b72171c263644da5428ca466`。本地代码审计以已解包 artifact 为准，不把 GitHub README 当成完整实现。

## 3. ProtocolGuard 论文所述流程

### 3.1 规则候选和上下文恢复

论文 PDF 第 3–4 页的流程为：

1. 去除目录、HTML 等非正文；
2. 按句切分，同时保留章节层级；
3. 建立协议实体、RFC 2119 情态词和数值比较词三组关键词；
4. 用关键词筛候选句；
5. LLM 读取同章节上下文，合并因果关系、指代和依赖从句，把候选重写为自包含规则；
6. 输出 `rule`, `req_type`, `req_fields`, `res_type`, `res_fields`。

这一步有价值的是“候选句不脱离章节”和“改写前读取上下文”。不足是输出没有：actor、飞行状态、trigger edge、取消/重置、例外、作用域、时间起止、单位来源、时钟域、证据跨度和跨消息 correlation key。

### 3.2 源码映射与动态检查

论文后续从 `recv/recvmsg` 输入根源做跨过程传播，建立 MessageCG，定位消息处理函数与字段对应变量，利用调试信息绑定 LLVM 指令，再沿 def-use 与控制条件生成切片。LLM 评估规则和代码语义并生成运行断言/测试输入。

该阶段适合回答“字段在源码中的语义身份是什么、有哪些定义/使用/控制位置”，不适合回答“这条性质是否应该存在”。本 benchmark 只复用前一部分的身份绑定思路，不执行由代码反向修正规范的步骤。

## 4. 论文描述与 artifact 实际实现的差异

### 4.1 第一轮过滤更宽

[`first_rule.py`](../../tool/ProtocolGuard/rule_extraction/ruleProcess/first_rule.py) 的实际条件允许：至少两个协议关键词，或者一个协议关键词加一个情态/比较词。它比论文简化描述的“实体词加情态/比较词”更宽。对本任务的启示是：关键词只应作为高召回索引，不能决定规范性。

### 4.2 第二轮主动排除本任务所需语义

[`second_rule.py:26`](../../tool/ProtocolGuard/rule_extraction/ruleProcess/second_rule.py#L26) 明确只保留 single message handling flow，并排除 concurrency、subsequent input message types 和 historical state dependencies。

这会丢掉：

- heartbeat/message silence；
- GPS loss 后的延时响应；
- mode enter—stay—exit；
- mission item 切换与 ACK；
- failsafe 触发、取消与恢复；
- 需要多消息关联的 command/ack/state 性质。

因此本 benchmark 明确拒绝该过滤器。

### 4.3 第三轮字段结构过窄

[`third_rule.py`](../../tool/ProtocolGuard/rule_extraction/ruleProcess/third_rule.py) 最终只抽 request/response type 和 fields。它不能表达配置参数、uORB/event、内部状态、作用域、合法例外和时间合同。本任务用 Requirement IR + TimeContract + AP bindings 取代它。

### 4.4 时间词被错误削弱

[`keywords_final.py:182`](../../tool/ProtocolGuard/rule_extraction/keywordProcess/keywords_final.py#L182) 指示删除非数值型 `before/after` 等 temporal comparisons。飞控文档中的 `after loss`, `before arming`, `until landed`, `once activated` 即使没有显式数值，也定义事件顺序或作用域，不能删除。无数值表达应保留为定性关系或 `NEEDS_TIME_BOUND`。

### 4.5 改写造成证据漂移风险

`separate_sentences.py` 让 LLM 消解代词并把句子改写为 self-contained 文本。中间结果虽含原句，后续主要使用改写句，最终规则没有强制保留原始字符跨度。改写可能新增主体、条件或指代对象。

本任务将改写保存为 `coreference_overlay`；原文、字符跨度与上下文节点不可被覆盖，每个 IR 字段都必须反链到原始证据。

### 4.6 自一致性实现不完整

[`violation_check.py:220`](../../tool/ProtocolGuard/inconsistency_detection/violation_check.py#L220) 声称综合三个回答，但实际只把前两个注入 prompt，第三个变量被注释；artifact 也没有完整记录 temperature/seed。多数票不能替代事件图一致性、类型/单位检查和人工裁决。

## 5. 2023–2026 方法调研矩阵

| 工作/标准 | 可复用能力 | 对本任务的限制 | 采用决策 |
|---|---|---|---|
| [nl2spec, CAV 2023](https://arxiv.org/abs/2303.04864) | 将子公式反映射到自然语言片段，支持人逐片修改 | 仍依赖正确的上下文与 AP grounding | 采用 subformula-evidence map |
| [NL2TL, 2023](https://arxiv.org/abs/2305.07766) | lifted NL/TL 学习与 AP 识别分离 | 通用数据不能替代飞控参数、状态与单位证据 | 只采用“逻辑骨架与 grounding 分离” |
| [SYNTHTL, FMCAD 2024](https://cs.stanford.edu/people/trippel/pubs/mendoza_FMCAD24.pdf) | 分层 sub-translation tree、model-checker 辅助发现歧义 | 其“公式应在 DUT 上成立”的搜索目标会向当前实现拟合 | 采用分解/组合；拒绝 DUT 成立性筛选 |
| [GraFT, ICML 2025](https://openreview.net/forum?id=p411a7WHox) | 先 AP grounding，再语法约束解码 | 训练集 grounding 不等于当前源码语义身份 | 采用 typed grounding 与 grammar validation |
| [GinSign, ICLR 2026 submission](https://openreview.net/forum?id=UjA74iO9Mf) | 将 AP 到系统 signature 的映射建模为结构化分类 | 尚不能替代固定 commit 的语义/位置证据 | 用于候选排序，不作最终绑定证明 |
| [ParCleanse, ISSTA 2025](https://qingkaishi.github.io/public_pdfs/ISSTA25.pdf) | DocTree、局部抽取、语法检查、底向上合并、可追溯 RFC 节点 | 面向协议格式；依赖约束 recall 仍有限 | 采用 DocGraph/traceability；扩展到时间、状态、例外 |
| [EACL 2023 时间归一化](https://aclanthology.org/2023.eacl-main.84/) | 将时间表达识别与归一化分层 | 主要面向日历时间，不提供飞控事件锚点/时钟域 | 借鉴分层，不直接输出 MITL bound |
| [OWL-Time](https://www.w3.org/TR/owl-time/) | 区分瞬间、区间、时长、顺序关系与 temporal reference system | 不是 MITL 编译器 | 用于 TimeContract 词汇和时钟域显式化 |
| [TimeBench, ACL 2024](https://aclanthology.org/2024.acl-long.66/) | 展示 LLM 与人在时间推理上仍有显著差距 | 不能把自由生成当作可信事件关系图 | 强制确定性图检查与人工审核 |
| [TIMELINE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.1016/) | 关注长距离和非动词事件的完整时序标注 | 新闻域与飞控域不同 | 提醒扫描跨段/跨节事件关系 |

调研结论不是选择一个端到端模型，而是组合“高召回检索 + 证据绑定 IR + 确定性编译 + 独立源码 grounding”。

## 6. 面向 ArduPilot/PX4 的 DocGraph

### 6.1 节点

```text
Document
  Section
    Paragraph
      Sentence / ListItem
    Table
      Row / Cell
    ParameterRecord
    Definition
    FigureCaption
    SourceComment
    MAVLinkMessage / Field / Enum
```

每个节点保存：文档标题、产品/版本、URL 或路径、抓取日期、内容哈希、DOM anchor/页/节、原文、字符跨度和来源级别。

### 6.2 边

- `parent_of`
- `defines`
- `refers_to`
- `parameterizes`
- `exception_to`
- `corefers_to`
- `precondition_of`
- `causes/triggers`
- `before/after/overlaps/during`
- `supersedes/deprecated_by`
- `observed_by`

指代边只是 overlay；它不能修改原文节点。冲突边保留两种解释和未决原因。

## 7. 高召回候选检索

关键词仅用于预筛，不用于决定 requirement 真值。

| 类别 | 示例 |
|---|---|
| 规范性 | `must`, `shall`, `required`, `should`, `recommended`, `only`, `never`, `cannot`, `must not` |
| 时间性 | `within`, `no later than`, `at least`, `at most`, `after`, `before`, `until`, `once`, `immediately`, `timeout`, `delay`, `hold`, `debounce`, `dwell`, `retry`, `heartbeat`, `Hz`, `ms`, `s`, `cycles` |
| 状态性 | `armed`, `landed`, `mode`, `failsafe`, `healthy`, `valid`, `link lost`, `GPS`, `battery`, `mission`, `waypoint`, `recover`, `reset` |
| 条件/例外 | `if`, `when`, `unless`, `except`, `provided`, `otherwise`, `then`, `only when` |
| 实体 | 大写参数 ID、MAVLink message/field、uORB topic、mode、event ID、数值—单位 |

[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html) 的适用范围是 IETF BCP 14：大写关键词才有特殊定义，但规范文本可以不使用这些词而仍是规范性的。因此本 benchmark 不把大小写或 MUST 命中当作通用权威判定；ArduPilot/PX4 文档的情态强度按其上下文与来源类别独立记录。[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html) 的 `SHOULD` 也允许有充分理由的例外，不能编译成没有 exception 的绝对义务。

## 8. 带证据的 Requirement IR

LLM 输出只能是 JSON 型 IR，不直接自由生成最终 MITL：

```text
actor / system / vehicle_scope
modality
trigger_event
preconditions[]
obligation | prohibition
target_event | target_state
exceptions[]
scope_start / scope_end
correlation_key
event_relations[]
time_expressions[]
parameters[]
unresolved_references[]
evidence_spans[] per field
```

IR 验证器检查：

- before/after 的逆关系；
- simultaneously/overlap 的对称性；
- before 的传递性和无环性；
- mutually-exclusive 状态不可同点成立；
- trigger、response、cancel/reset 的主体与关联键一致；
- 数值类型、单位和坐标系一致。

多个模型输出冲突时保存 disagreement，不能用多数票静默裁决。

## 9. TimeContract

每个时间表达必须保存：

```text
semantic_start_event
semantic_end_event
cancel_event / reset_event
raw_expression and exact evidence span
lower / upper / lower_closed / upper_closed / unit
source_type
parameter_id / formula / all operands
clock_domain
timestamp_carrier
conversion
measurement_uncertainty
freshness
```

允许的数值来源只有：

1. 当前官方文档字面值；
2. 当前官方参数元数据及实际参数快照；
3. 全部操作数可追溯的派生式；
4. 明确标记的论文作者经验/实验设置；
5. `UNKNOWN`。

必须区分：飞控单调启动时钟、SITL 仿真时钟、MAVLink sender boot time、Unix/UTC、GPS time、GCS 单调到达时间和插桩时钟。`time_usec` 若 XML 自身允许 boot/Unix 两种解释就保持 `AMBIGUOUS`。网络到达时间包含传输、队列和调度延迟，不自动等于内部事件时间。

`immediately`、`promptly` 等无数值词保留定性顺序或 `NEEDS_TIME_BOUND`；绝不自定义 epsilon。误差可能改变边界结论时输出 `INCONCLUSIVE`。

## 10. IR 到 MITL 的确定性编译

示例模板只描述编译形状，不提供任何系统事实或数值：

```text
bounded_response:
  G((trigger ∧ preconditions ∧ ¬exception) -> F_[L,U] response)

bounded_prohibition:
  G((trigger ∧ preconditions) -> G_[L,U] ¬forbidden)

until_cancel:
  G(scope_start -> (obligation U cancel))
```

实际编译器必须：

- 用 trigger edge，而非持续状态重复启动窗口；
- 明确区间开闭；
- 将每个子公式映射回 IR 字段和原始跨度；
- 同时输出符号式与当前 SITL 参数快照实例；
- 另行输出 MightyPPL/TAMonitor 接受的具体语法；
- 若 monitor 不支持某语义，保留 `UNSUPPORTED_BY_MONITOR`，不改写要求。

## 11. AP grounding 与源码绑定防火墙

每个 AP 先定义与源码无关的真值条件、类型、单位/坐标系、有效性、freshness、聚合与关联键；然后才映射当前源码：

- 变量/字段/枚举；
- 函数返回、回调、赋值点、消费点；
- ArduPilot `AP_Param`、mode/state、mission/failsafe、MAVLink sender/handler；
- PX4 参数、uORB topic、module state、events、MAVLink stream/receiver；
- MAVLink 消息与字段，以及需要跨消息派生的状态。

一个 AP 可以绑定多处；每个 binding 标记 `exact | may | modelled | name-only` 并附当前 commit 的文件、行、语义身份。源码绑定阶段不得补时间、删性质或给出满足结论。无法证明时标 `NEEDS_BINDING`。

## 12. 采纳门槛

一条性质只有同时满足以下条件才进入 `accepted`：

- 有版本化来源、哈希、精确原文和页/节/anchor；
- 来源不是普通控制流、单测或生成实现；
- 定义、指代、交叉引用和例外闭合；
- 每个时间数值和操作数可追溯；
- 起止/取消事件、时钟和 timestamp carrier 明确；
- IR 可由确定性模板编译；
- 每个 AP 有真值条件、当前源码多对多绑定和观测契约；
- 公式通过解析、类型/单位、可满足性、非重言式和非空洞检查；
- 正例、边界反例和缺失/错误关联反例有 TAMonitor 结果；
- 人工审核通过；
- `implementation_satisfaction` 仍为 `NOT_ASSESSED`。

## 13. 可复核命令

```bash
sha256sum "/mnt/c/Users/PC-123/Zotero/storage/8WI6R8KH/Song 等 - 2026 - ProtocolGuard Detecting protocol non-compliance bugs via LLM-guided static analysis and dynamic ver.pdf"
nl -ba /home/lqq/project/TAFuzz/tool/ProtocolGuard/rule_extraction/ruleProcess/first_rule.py
nl -ba /home/lqq/project/TAFuzz/tool/ProtocolGuard/rule_extraction/ruleProcess/second_rule.py
nl -ba /home/lqq/project/TAFuzz/tool/ProtocolGuard/rule_extraction/ruleProcess/third_rule.py
nl -ba /home/lqq/project/TAFuzz/tool/ProtocolGuard/rule_extraction/keywordProcess/keywords_final.py | sed -n '150,200p'
nl -ba /home/lqq/project/TAFuzz/tool/ProtocolGuard/inconsistency_detection/violation_check.py | sed -n '200,270p'
```

## 14. 未决限制

- 上述 NLP 研究多以 LTL、协议格式或日历时间为目标，不能直接证明飞控 MITL 语义正确。
- ArduPilot/PX4 官方网页存在 release/main 混合风险，必须在 corpus manifest 中保存版本与抓取日期。
- 网页改写、参数生成文件与源码注释的权威级别不同，候选必须分层，不能用单一置信分数掩盖。
- LLM 的事件/时间推理只作提议；最终关系图、时间数值、公式和绑定均需确定性验证及人工审核。

