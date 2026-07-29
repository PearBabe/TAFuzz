# ProtocolGuard 与 CoAP 需求测试：研究者级精读与对照

阅读日期：2026-07-15

页码约定：本文所称 PDF p.N 均指 PDF 物理页；两份论文的正文页码与物理页一致。

输入文献：

- Asadian et al., Testing IoT Protocol Requirements Using Fuzzing and
  Symbolic Execution: Application to CoAP, 2024。
  SHA-256:
  ca8cbd6c6ad9d48c7c4bc7a79356369f35f761b5e300daab390825f25bde7633
- Song et al., ProtocolGuard: Detecting Protocol Non-compliance Bugs via
  LLM-guided Static Analysis and Dynamic Verification, NDSS 2026。
  SHA-256:
  58ca7687749493ad350495b25fee0e510a0c39a22cb6b667845eee183229d11f

阅读方法：

- 逐页抽取并阅读全文：CoAP 论文 7 页，ProtocolGuard 18 页。
- 视觉核验 CoAP PDF pp.4-5 的 Tables I-II，以及 ProtocolGuard PDF
  pp.9-12 的 Tables II-IV 和 Fig.2。
- 对论文表格中的 TP/FP/FN、宏平均、微平均和 crash 汇总重新计算。
- 本次不联网，不执行作者 artifact，也不独立核验 GitHub issue、厂商确认或修复。
  因而厂商状态属于论文报告的证据，不是本次复现实验的结论。

## 1. 结论先行

两篇论文共同抓住了协议测试中最容易被忽略的本质：

> 协议 non-compliance 往往是没有自然 crash 的语义错误。Fuzzer 或 symbolic
> execution 只有在获得显式、可信的 requirement oracle 后，才能把这种错误稳定地暴露出来。

但两文解决的是正交问题：

- CoAP 论文回答“小范围内怎样把手工 RFC 需求变成可执行断言，并比较 AFL++ 与
  KLEE 的反例搜索行为”。它是一项清晰、有说服力的可行性研究，不是完整 CoAP
  一致性验证，也不是严格公平的 fuzzing-SE 基准。
- ProtocolGuard 回答“怎样规模化地从规范和源码中提出候选不一致，并自动辅助构造
  assertion、seed 与 PoC”。它是候选发现和可达性验证流水线，不是形式化合规证明器。

对 TAFuzz 最重要的组合方式是：

1. 用 ProtocolGuard 风格方法做规则、源码位置和 ActionTape seed 的候选前端。
2. 用 CoAP 论文的小而明确的需求集做 adapter/stateful harness 的受控验收。
3. 正式 verdict 仍由 TAFuzz 的 versioned raw event -> AP contract -> external
   monitor -> validity/closure gate 产生。

两文都不能证明 TAFuzz 的 MITL soundness、UNKNOWN 语义、capability-aware
validity 或 cost guidance 有效。它们支持的是“显式语义 oracle 很重要”和“高质量、
定向、格式合法的输入很重要”，不应扩大为对整条 TAFuzz 路线的实证背书。

## 2. 两篇论文的共同问题与根本差异

| 维度 | ProtocolGuard | CoAP 需求测试 |
|---|---|---|
| 研究目标 | 规模化发现候选不一致并辅助 PoC | 在固定 harness 中比较 fuzzing 与 SE |
| 规范处理 | 关键词筛选 + LLM 上下文化和结构化 | 人工选择 12 条需求并人工写断言 |
| 源码映射 | LLM-guided LLVM/AST/SVF slicing | 人工选择两个响应发送 API |
| 动态后端 | AFLNet + SelectFuzz | AFL++ 4.10c 与 KLEE 3.0 |
| 初始输入 | LLM 反例描述 -> Scapy -> PCAP | 样例程序预抓包 |
| 跨包状态 | 消息序列 seed，但受 AFLNet 两方模型限制 | 多包装进固定 offset 的单一 buffer |
| oracle | LLM/agent 生成的内联 assertion | 人工内联 assertion |
| verdict | assertion-triggered crash | assertion-triggered crash |
| 阴性结论 | 不主张证明无 bug | KLEE 完成受限搜索时给条件性说明 |
| metric time | 无 | 所选 12 条也无真实 metric deadline |

共同盲点：

- assertion 的语义正确性本身成为新的 oracle-risk。
- assertion crash 只能表达二值触发，不能表达 UNKNOWN、NOT_EXERCISED、事件丢失、
  capability 缺失或 horizon 未闭合。
- 两文均没有把 trigger 与 outcome 的证据生产链显式分离。
- 两文均没有处理真正的 metric-time deadline、timer capability 和时钟边界。
- 多包或多方状态被简化，尚不足以覆盖 SIP/Kamailio 一类 callback/timer/transaction-heavy
  系统。

## 3. ProtocolGuard 精读

### 3.1 它真正解决了什么

ProtocolGuard 试图连接四个长期割裂的步骤：

~~~text
规范规则候选
  -> 规则相关代码切片
  -> 规则与实现的不一致判断
  -> assertion + 定向 seed + fuzzing PoC
~~~

其贡献不是让 LLM 直接阅读整个代码库并宣判 bug，而是把 LLM 放进静态分析限定出的
工作流中，再把 silent inconsistency 转成 fuzzer 可观察的 assertion failure
（PDF pp.1-3, Fig.1 on p.4）。

贡献边界：

- 不证明规则抽取完整。
- 不证明代码切片完整。
- 不证明 LLM 判定或生成 assertion 具有形式正确性。
- 动态阶段证明的是合成谓词可达且可被违反，不一定直接观察未插桩程序的真实错误输出。
- 当前只支持 C，且强依赖 handler-centric/event-driven 架构。
- 规则 JSON 只有原文、请求/响应类型和字段，缺少前置条件、角色、实例 key、量词、
  时间区间、闭包、capability 和规范版本升级语义。

### 3.2 四阶段方法与每类工具的职责

#### A. 规则抽取

ProtocolGuard 先用 lxml 清理和分句，再构造三类关键词：

- 协议关键词：LLM 读取 Wireshark dissector，提取消息与字段词汇。
- 规范强度词：RFC 2119 modal words；排除 MAY、OPTIONAL 等纯可选词。
- 数值比较词：复用既有工作，并用 LLM 扩展同义表达。

句子至少同时含协议词和 modal/comparative 词才成为候选。随后 LLM 在章节上下文中
补全指代、因果和省略，最后输出 rule、req_type、req_fields、res_type、
res_fields 等 JSON 字段（PDF pp.3-4）。

优点是先用启发式限制候选，再让 LLM 补语义；主要漏项包括：

- 没有 modal keyword 的隐式不变量。
- 表格、状态图、ABNF 与跨章节联合约束。
- timer、生命周期、资源上限和多方交互语义。
- 可选但安全敏感的行为。

Wireshark dissector 还会把候选空间偏向 wire-visible 字段，对内部 transaction、
timer、cleanup 和异步状态不利。

#### B. LLM-guided program slicing

静态模块使用 GLLVM、LLVM passes、Clang AST 与 SVF（PDF pp.5-8）：

1. 从 recv/recvmsg 等网络接收点逆向追踪 message buffer 的起源。
2. 再正向构造只含消息处理逻辑的 MessageCG。
3. LLM 在 MessageCG 上识别 handler、上游连接/资源函数、规则字段变量和辅助变量。
4. debug info 把源码变量映射到 LLVM instruction。
5. LLVM def-use 做跨过程 forward slice。
6. AST 补回 if/switch 条件、return、break、goto 等控制结构。
7. LLM 补回日志和错误码等语义线索，并剪掉规则无关函数。

设计上的强点是“LLM 选择语义目标，静态分析负责可重复的结构追踪”。作者也直接观察到
它的系统性弱点（PDF pp.10-12）：

- callback/decoupled 架构中，cleanup、response sending 等不在 handler call path 上。
- SVF 对间接调用保守，会把大量无关 target 放进 slice。
- 多 transport 实现会膨胀上下文，libcoap 甚至接近或超过 DeepSeek R1 的 128K
  context 限制。
- 深层结构字段经过多个中间函数时，当前 data dependency 追踪会断裂。

这不是偶发工程瑕疵，而是 ProtocolGuard 迁移到 Kamailio 时最重要的结构性风险。

#### C. LLM inconsistency detection

DeepSeek R1 读取规则与切片，输出是否存在 violation、理由、函数、文件与行号。
每个 rule-slice pair 查询三次，再让模型分析先前输出以形成 self-consistency 结论
（PDF pp.6-7）。

这里的 self-consistency 没有独立消融、输出方差或跨运行稳定性报告；三次相关的
模型输出也不能替代独立 ground truth。

#### D. assertion、seed 与定向 fuzzing

Cursor 中的 Claude 3.7 agent 根据规则、静态报告和源码生成 assertion/helper，
编译失败时迭代修复。随后：

1. LLM 先给自然语言 counterexample，描述消息序列和关键字段。
2. agent 生成 Scapy Python 脚本。
3. 脚本输出 PCAP。
4. tshark 检查包的结构和顺序。
5. assertion 位置成为 directed targets。
6. AFLNet + SelectFuzz 触发 assertion 并保存 PoC（PDF pp.7-8）。

需要严格区分四层证据：

- 编译成功：只证明语法和类型可接受。
- 人工语义审查：判断 assertion 是否表达预期规则。
- assertion 被触发：证明输入能到达该点并违反合成谓词。
- 未插桩实现的外部错误行为：论文通常没有独立 oracle 再确认这一层。

因此动态阶段更准确的名称是 reachability/triggerability verification，而不是完全独立的
semantic verification。静态怀疑与 assertion 由同一规则和相近 LLM 链条产生，存在相关
错误和循环确认风险。

### 3.3 数据集与 RQ

Table I（PDF p.8）包含 11 个 C 项目：

- MQTT：Sol、TinyMQTT、Mosquitto。
- CoAP：libcoap、FreeCoAP。
- FTP：pure-ftpd、uFTP。
- TLS 1.3：TLSE、wolfSSL。
- DHCPv6：Dnsmasq、NDHS。

规模从 4.4K 到 1456.3K LoC。论文称覆盖 6 个 protocols；若按协议族只有 5 类，
只有把 MQTT 3.1.1 与 MQTT 5.0 作为两个协议/版本类别时才得到 6。

环境是 Docker、Ubuntu 22.04、Xeon Gold 6226R 和 256 GB RAM。DeepSeek 使用
default parameters，但没有固定 API snapshot、采样随机种子、token 成本或响应缓存
（PDF p.8）。

### 3.4 RQ1：真实项目中的候选与 bug

Table II（PDF p.9）需要按四层数量理解：

| 层级 | 数量 | 含义 |
|---|---:|---|
| distinct rules | 420 | 跨所用规范统计；同一规则集会复用于多个实现 |
| rule-implementation checks | 722 | 将 Table II 每项目 Rules 相加所得 |
| candidate reports | 198 | 181 TP + 17 FP |
| true inconsistency reports | 181 | 人工判定为真实不一致的报告 |
| unique bugs | 158 | 合并同根因并排除合理扩展/新草案允许行为后 |

论文的 90.6% precision 是 11 个项目 precision 的宏平均。按全部报告池化，
micro precision 是 181/198 = 91.4%。原先把“181 个不一致 + 17 FP”理解为
181 个总报告是不准确的。

158 个 unique bugs 中：

- 156 个被作者认定为此前未知。
- 2 个已知但尚未修复。
- 158 个均已报告给 vendor。
- 70 个获得 confirmed。
- 17 个标为 fixed。

这些状态是写作时的作者报告。70/158 约 44.3%，17/158 约 10.8%；不能把
158 全部写成厂商确认漏洞，更不能写成 158 个 CVE。论文中唯一明确出现的 CVE
是作为动机引用的 MatrixSSL CVE-2022-46505，不是本文新分配的 CVE（PDF p.1）。

根因分布（PDF p.9）：

- Parsing：约 37%。
- State：22%。
- Error handling：16%。
- Session management：13%。
- Security mechanisms：12%。

这支持“non-compliance 不只存在于 parser”的判断，但分类由作者完成，不能据此推断
总体协议软件中的真实 bug 分布。

三个 case study 也应区分证据等级：

- wolfSSL ID 61：TLS 1.3 version negotiation 问题，Table V 为 Fixed。
- Sol ID 93：首包未强制 CONNECT，安全影响描述较强，但 Table V 仍为 Reported。
- uFTP ID 55：AUTH 后未重新认证，Table V 为 Fixed。

其中 wolfSSL case 从“强制降到 TLS 1.2”进一步推到“消除 forward secrecy、可回溯解密”
需要具体 TLS 1.2 cipher suite 和完整攻击链支持；论文没有给出端到端安全实验，因此应把
代码不合规与最坏安全影响分开陈述。

### 3.5 RQ2：与 Cursor 的比较

Table III（PDF p.10）只覆盖 Sol、pure-ftpd、libcoap 和 TLSE 四个对象。论文报告：

| 方法 | 论文 Average precision | 论文 Average recall |
|---|---:|---:|
| Cursor + Claude 3.7 | 71.7% | 76.8% |
| Cursor + DeepSeek R1 | 49.3% | 52.0% |
| ProtocolGuard + DeepSeek R1 | 86.3% | 81.3% |

但这些 Average 无法由表中四行按标准宏平均或微平均复算：

| 方法 | 由四行复算的宏 P/R | 由 TP/FP/FN 池化的微 P/R |
|---|---:|---:|
| Cursor + Claude | 74.9% / 77.6% | 79.8% / 79.8% |
| Cursor + DeepSeek | 54.1% / 51.9% | 56.5% / 48.5% |
| ProtocolGuard | 89.3% / 80.0% | 92.4% / 85.9% |

除非存在未披露的重复试验或不同聚合方法，否则这是明确的复现疑点。论文说
significantly outperforms，但没有显著性检验。

比较本身还存在边界：

- Cursor 是通用 agent/editor，不是等范围的 protocol non-compliance pipeline。
- 同领域工具因不开源、范围不同或需要大量适配而未直接运行。
- 结果更能证明专门的上下文构造优于通用代码检索，不能证明优于所有现有方法。
- FN ground truth 如何完整构造没有充分说明；未知 bug 场景下 recall 分母并非天然可知。

RQ2 的标注由两名研究者独立分析、第三人处理分歧，这一点优于单人标注；但该详细流程
没有明确扩展到 RQ1 的全部 11 个项目。

### 3.6 RQ3：生成 assertion 是否有效

Table IV（PDF p.11）：

- 共生成 198 个 assertion。
- 198 个经 agent 迭代后都能编译。
- 177 个经人工判定语义正确。
- 139 个产生 assertion-triggered unique crashes。

论文报告的 88.9% semantic rate 与 68.4% crash rate 是逐项目宏平均。
池化口径为：

- semantic: 177/198 = 89.4%。
- crash: 139/198 = 70.2%。
- 若仅以语义正确的 assertion 为分母，trigger rate 为 139/177 = 78.5%。

“全部可编译”不能被写成“全部 oracle 正确”。另外，crash 的 unique 定义没有充分说明，
同一根因可能对应多个 assertion；139 不能直接等同于 139 个已独立动态确认的 unique
bugs。

作者给 fuzzing-based verification 设 24 小时预算，但正文未充分说明预算究竟按每个
assertion、每项目还是每配置计算，也没有报告总 CPU-hours、重试次数和触发时间分布。

### 3.7 RQ4：LLM 生成 seed 的增益

Fig.2（PDF p.12）的 Random -> ProtocolGuard crash 数：

| 项目 | Random | ProtocolGuard |
|---|---:|---:|
| Sol | 32 | 32 |
| TinyMQTT | 23 | 24 |
| Mosquitto | 10 | 12 |
| libcoap | 1 | 2 |
| FreeCoAP | 2 | 2 |
| pure-ftpd | 14 | 17 |
| uFTP | 11 | 15 |
| TLSE | 4 | 15 |
| wolfSSL | 1 | 4 |
| Dnsmasq | 2 | 9 |
| NDHS | 1 | 7 |

论文所称平均多 155.2% 是逐项目相对提升的宏平均，受到 1 -> 7、2 -> 9 等小基数
显著放大。合计是 101 -> 139，即增加 38，micro/aggregate 增幅约 37.6%。
而且 Sol 和 FreeCoAP 是持平，不是严格地在每个项目上都 outperform。

更重要的实验设计限制：

- 无重复次数、方差、置信区间或统计检验。
- random baseline 与规则定向、格式合法的 seed 差距过大。
- 没有与数量/长度匹配的合法抓包 seed、grammar seed 或 protocol-aware mutation 比较。
- rule-specific seed 可能在初始状态就非常接近甚至直接满足 assertion trigger，正文没有
  说明如何排除该混杂因素。

因此强结论只能是“针对这些 assertion，语义定向 seed 明显优于所用 random baseline”，
不能直接量化为一般协议 fuzzing 提升 155.2%。

### 3.8 ProtocolGuard 的效度与可复现性

内部效度：

- 规则理解、静态 bug 判断和 assertion 合成共享同一信息链，错误可能相关。
- assertion 可能在原始 bug 行为发生前 abort，改变 SUT 控制流。
- 多个 assertion 相互遮蔽；当前实现需要人工注释已触发 assertion 并重启 fuzzing。
- 配置未启用、AFLNet 破坏格式和两方模型不足都会造成未触发。

构念效度：

- assertion crash 是人工制造的观察信号，不是自然 crash。
- precision 是人工判定报告是否为规则不一致，不是 vendor confirmation rate。
- new、confirmed、fixed、security vulnerability 和 CVE 是不同证据层级。
- 规范版本本身是 oracle 的一部分；作者已因新草案允许某些行为而排除部分发现。

外部效度：

- 仅 C、开源、活跃项目。
- handler-centric 假设不适合 callback/timer/actor/threaded architecture。
- RQ2 只有四个对象。
- AFLNet 两方模型难覆盖 MQTT 等多方逻辑。

结论效度：

- Table III Average 无法复算。
- seed 提升的宏平均受小基数放大。
- fuzzing 未报告重复、随机种子和统计检验。
- 缺少规则抽取、上下文化、slice completion、pruning、self-consistency 与
  SelectFuzz 的完整消融。

复现性判断：

- 架构级复现：中等。论文提供 Zenodo/GitHub、Apache-2.0、Docker，以及 LLVM 14、
  Python 3.10、Go 1.18 要求（PDF p.17）。
- 精确数字复现：偏低。DeepSeek API、Cursor/Claude 行为和模型快照不可固定；缺少
  LLM 成本、完整运行参数、随机种子、原始标签与人工合并日志。
- Artifact Appendix 写有 Benchmarks: None，与正文的 11 个 subject evaluation
  至少在措辞上不一致。

## 4. CoAP 需求测试论文精读

### 4.1 它真正解决了什么

这篇论文的主要贡献不是新的 fuzzer 或 symbolic executor，而是一套共用的
requirement-aware harness：

~~~text
样例程序产生合法交互
  -> tcpdump/Wireshark 抓取包序列
  -> common harness 逐步调用 SUT API
  -> 人工把 RFC 需求写成 assertion
  -> AFL++ 变异输入，或 KLEE 对相关字段 symbolic execution
  -> assertion failure 成为反例
~~~

它回答的是：在固定的 CoAP 实现、交互和 12 条手工需求下，AFL++ 与 KLEE 是否都能
快速暴露已编码的 non-conformance，以及二者在“找反例”和“完成受限搜索”上有何差别
（PDF pp.1-5）。

它没有：

- 自动抽取 RFC 需求。
- 构造完整 CoAP 状态机。
- 把 fuzzing 与 KLEE 组合成 hybrid system。
- 验证全部 CoAP、真实网络、丢包、重排、Observe、proxy、DTLS、timer 或多方交互。
- 给出实现级的全局无 bug 证明。

### 4.2 harness、assertion 与状态表示

论文在两处发送函数插 assertion（PDF p.4）：

- libcoap: coap_session_send_pdu。
- FreeCoAP: coap_server_trans_send。

响应字段从发送函数的 pout 指针获取；接收包字段从 harness 维护的全局 pin 指针获取。
Message ID Echo 的逻辑是：

~~~text
若 pin 是 CON/NON 且 pout 是 ACK/RST，
则 pin.message_id == pout.message_id
~~~

跨包 block-wise transfer 没有使用真正 stateful fuzzer，而是把所需多包装进一个大
buffer 的固定 offsets，由 harness 按步骤读取。AFL++ 一次启用全部 assertions；
KLEE 每次只查一条 requirement，只把人工选定的相关字段 symbolic，其他字段保持
concrete，并通过 parser/serializer 重编码（PDF p.5）。

这两个输入空间并不对称，所以论文所谓 common harness 或 unbiased comparison 只能理解为
共用 SUT 场景和 oracle，不是严格对等的算法比较。

### 4.3 12 条需求

Table I（PDF p.4）：

| 类别 | Requirements |
|---|---|
| 单包格式/拒绝 | Version Validity, Matching Message Type, Reserved Code, Token Length Validity, Repeatable Options, Unrecognized Options |
| 单包跨字段 | Block Size Validity, Content Format |
| 请求-响应关联 | Token Echo, Message ID Echo |
| 跨包状态 | Further Request Block Size, Missing Blocks |

前三类主要是值关系、顺序和状态性质，不包含真实 metric-time deadline。

最值得警惕的是 Further Request Block Size：

- RFC 原文要求 client SHOULD 遵循 server 给出的 block-size preference。
- RFC 没有明确规定 server 收到过大后续块时必须返回什么。
- 作者明确说以 common sense 要求 server 返回某种 error（PDF p.4）。

因此该 assertion 把 SHOULD 加作者 policy 强化成近似 MUST-like rejection oracle。
这可以是合理的测试政策，却不能不加限定地称为严格 RFC non-conformance。

其他 oracle 风险：

- Version Validity 的 silently ignored 属于 absence；只在发送函数放断言没有显式
  macrostep/horizon closure。
- Unrecognized Options 的表格摘要没有展示 CoAP 对 critical/elective unknown option
  的细分；完整 assertion 未在 PDF 中给出。
- Content Format 需要 body 的独立 ground truth，论文没有说明如何判定实际内容格式。
- 全局 pin 隐含请求-响应同步一一对应，不适合异步、重传、多连接或响应延迟。

### 4.4 实验设置

- SUT: libcoap 4.3.1；FreeCoAP commit ffc87fd。
- Fuzzer: AFL++ 4.10c。
- SE: KLEE 3.0。
- Seeds: 样例程序产生的合法预抓包。
- Fuzzing TTE/MTE: 5 次 campaign 的平均。
- KLEE TTE: 脚注称为 5 次 KLEE run 的平均。
- KLEE completion timeout: 24 小时。

未报告：

- CPU、RAM、OS 和完整编译参数。
- AFL++/KLEE 命令、solver/search 参数和随机种子。
- fuzzing 对未发现违例需求的统一 campaign 时限。
- 原始五次结果、方差或置信区间。

### 4.5 Table II 的完整结果

| Requirement | libcoap: AFL TTE/MTE; KLEE TTE/completion/paths | FreeCoAP: AFL TTE/MTE; KLEE TTE/completion/paths |
|---|---|---|
| Version Validity | <1s/193; 1s/1s/2 | no bug; 43s/6 |
| Matching Message Type | <1s/371; 4s/16s/38 | no bug; 2h51m4s/7844 |
| Reserved Code | <2s/546; 4s/17s/41 | no bug; 2h55m32s/7844 |
| Token Length Validity | no bug; 12m42s/31 | no bug; 3h00m14s/7083 |
| Token Echo | no bug; 1s/2 | no bug; 20s/4 |
| Message ID Echo | no bug; 1s/1 | no bug; 11s/32 |
| Repeatable Options | <1s/205; 56s/2m29s/213 | <2s/789; 3m30s/24h timeout/28949 |
| Unrecognized Options | no bug; 2m36s/196 | no bug; 24h timeout/28917 |
| Block Size Validity | <1s/286; 1s/2h25m28s/17971 | no bug; 37s/203 |
| Content Format | no bug; 1s/4 | no bug; 1s/1 |
| Further Request Block Size | <2s/891; 2s/19m14s/27 | about 40s/36824; 3s/45m13s/8497 |
| Missing Blocks | <1s/255; 6s/3m51s/359 | no bug; 1h24m17s/22979 |

这里的 no bug 只表示论文没有报告 assertion violation，不是一般意义上的“无 bug”。

归纳：

- libcoap 在 12 条中有 7 条报告 non-conformance，写作时均标为 Fixed。
- FreeCoAP 有 2 条，均标为 Reported。
- 24 个 implementation-requirement cells 中 9 个为正例；这不是总体 bug rate。
- 9 个正例中，AFL++ 对 8 个平均在 2 秒内触发；例外是 FreeCoAP Further Request
  Block Size，约 40 秒、36,824 mutations。
- KLEE 找到反例和完成搜索是两种完全不同的成本。例如 FreeCoAP Repeatable
  Options 在 3m30s 找到反例，但 24h 仍未穷尽。
- libcoap 最重的已完成搜索是 Block Size Validity：2h25m28s、17,971 paths。
- FreeCoAP 有四项完成搜索超过 1 小时，另两项达到 24 小时 timeout。

作者说两者没有 significant difference，但论文没有做统计显著性检验。更稳妥的结论是：

- 在这组手工 oracle 和固定场景中，两者都能很快找到多数已存在的反例。
- fuzzing 对快速正例搜索略占优势。
- KLEE 在搜索完整结束时能给出更强的阴性证据，但只对受限 symbolic space 有效。

### 4.6 报告的 non-conformance

PDF p.6 讨论了七类根因：

1. invalid version 返回 RST，而不是静默忽略。
2. ACK 携带 request 时未拒绝，反而用 NON 返回资源。
3. 接受 reserved code。
4. 接受重复的不可重复 option；两个实现均出现。
5. SZX 与实际 payload size 不一致；libcoap 首次修复只覆盖 server receiving
   request，二次修复才覆盖 client receiving response。
6. 后续 block size 偏离 preference 时继续跟随；两个实现均出现。
7. final block 到达但前序 block 缺失时未返回 4.08。

论文摘要所说九个 non-conformances 更准确地理解为 9 个
implementation-requirement findings，而不必然是 9 个相互独立的根因。

PDF p.7 还明确致谢：一些 libcoap bugs 已由 Sabor Amini 的硕士工作先行发现和报告。
因此不能把所有九项都写成本文首次发现。

### 4.7 CoAP 论文的效度与可复现性

内部效度：

- fuzzing 同时启用全部 assertions，KLEE 每次只查一个。
- KLEE 获得人工字段裁剪；AFL++ 变异原始 buffer。
- pin 全局指针假定同步一一对应。
- 单一发送 hook 可能漏掉旁路、异步或未来发送。
- 样例程序、抓包和固定交互决定可达状态。
- 高频 assertion 是否遮蔽其他 oracle 没有说明。

构念效度：

- assertion failure 被直接视为 requirement violation。
- SHOULD 和作者补充 policy 被混入硬 oracle。
- 未触发不能区分满足、不可达、未闭合或不可观测。
- effectiveness 主要由 TTE/MTE 表示，没有性质覆盖率、oracle precision 或独立
  behavior oracle。

外部效度：

- 仅两个 C 语言 CoAP 实现和 12 条人工需求。
- 不覆盖真实 UDP 调度、丢包、timer、多客户端或代理。
- 不能从 CoAP 直接推广到所有 IoT、SIP 或一般协议。

结论效度：

- 没有统计检验、方差和置信区间。
- <1s/<2s 粗粒度值不支持细致排名。
- 两个 24 小时右删失样本使均值比较不完整。
- fuzzing 对阴性单元不报告统一预算。

复现性判断：

- 概念复现：中等。SUT/tool 版本、需求表、插桩点和两条 oracle 示例足够清楚。
- 定量复现：偏低。缺少完整 harness、12 条 assertion、抓包 seed、命令、硬件、
  KLEE 参数、随机种子和原始五次数据。
- KLEE 的 absence guarantee 只在固定 harness、环境模型、symbolic fields、正确
  parser/serializer/assertion 和已完成搜索的交集内成立。

## 5. 对 TAFuzz 的组合架构

建议将两文放进“候选前端 + 可信运行时”的分层架构：

~~~text
规范/RFC
  -> RuleCandidateMiner
  -> Normativity/Ambiguity/Profile Gate
  -> SourceMappingCandidateGenerator
  -> 人工/静态工具证明 raw producer truth point
  -> versioned RawEvent schema
  -> SUT hook / peer observation
  -> sidecar integrity, capability, drop, clock checks
  -> correlation + subject/generation split
  -> versioned AP contract registry
  -> per-obligation timed word
  -> MITL 或 finite postcondition monitor
  -> validity/closure gate
  -> SATISFIED / VIOLATED / UNKNOWN / NOT_EXERCISED

规则 + 静态怀疑
  -> Counterexample/ActionTapeSeedGenerator
  -> FramerAdapter / field repair / peer harness
  -> fuzzer

KLEE
  -> bounded counterexample / small-field contract cross-check
  -> scope manifest
  -> 不升级为全局“性质满足”
~~~

### 5.1 论文组件到 TAFuzz 模块的映射

| 论文组件 | TAFuzz 模块 | 信任边界 |
|---|---|---|
| ProtocolGuard rule extraction | RuleCandidateMiner | 只输出 CANDIDATE，保留版本、页码、原文、角色 |
| LLM slicing | SourceMappingCandidateGenerator | 只给 hook/producer 候选，不能产生 verdict |
| LLM inconsistency report | StaticTriage | 排序人工审计，不进入 monitor |
| generated assertion | DebugOracleAdapter | 用于双重核验；abort 不可替代正式 oracle |
| LLM PCAP/script | ActionTapeSeedGenerator | 先输出 action，再由 adapter 编码和修复 |
| SelectFuzz target | EventDistanceHint | 只影响 guidance，不进入 trace_bits/verdict |
| CoAP common harness | coap adapter/framer/executor | 用显式 ActionTape 替换固定 offset buffer |
| CoAP assertions | CoAPPropertyPack/golden traces | 先审计规范忠实度，再外部化 |
| KLEE | BoundedCounterexampleOracle | 输出 symbolic scope、path、timeout manifest |

### 5.2 正式 property admission gate

ProtocolGuard 或人工需求只有同时通过以下闸门，才可从候选升级为 TAFuzz 正式性质：

1. Normative source：精确 RFC 版本、章节、原文和角色。
2. Strength：MUST/SHOULD/policy/implementation expectation 明确分级。
3. Preconditions：配置、角色、连接状态和消息历史完整。
4. Trigger/outcome independence：两者有独立 producer 和证据链。
5. Observability：每个事实有 hook/peer producer、truth point 和 source mapping status。
6. Correlation：subject key、generation、并发和标识复用规则明确。
7. Closure：何时足以判定 absence 或义务完成。
8. Required capabilities：send、timer、peer、clock、drop-free 等能力明确。
9. Profile：PFB-COMPAT/MITL-VALID 等运行配置明确。
10. Controllability/actionability：DIRECT、PEER、SCHEDULER、AUTONOMOUS 分级。

任一关键条件缺失，应为 CANDIDATE、UNSUPPORTED 或运行时 UNKNOWN，而不是强行二值化。

### 5.3 CoAP 性质如何外部化

优先级较高：

- Message ID Echo：MID 作为 correlation metadata；在 correlated RX/TX raw facts 上
  检查关系，不把动态 MID 放入 AP alphabet。
- Token Echo：同理。
- Block Size Validity：分开记录 Block option、payload length、parse decision 和
  acceptance；不能用一个复合 AP 同时证明输入异常与实现错误接受。
- Missing Blocks：以 transfer subject_id + generation 维护 committed block range；
  final block 到来且存在 gap 后，检查 correlated 4.08 send。
- Version Validity：记录 RX header/version 和全部 correlated send results；
  silent ignore 必须在 handler/macrostep 或异步 horizon 闭合且 send capability 完整时
  才能判定。

谨慎处理：

- Further Request Block Size 首先应按 client-role SHOULD property 建模。若测试
  server 是否返回 error，则必须标记为 project policy，而非直接称 RFC MUST verdict。
- Content Format 在没有独立 body-type oracle 前应保持 UNKNOWN/CANDIDATE。
- Unrecognized Options 必须先恢复 critical/elective option 的完整规范条件。

## 6. 可检验研究假设与最小实验

| 假设 | 最小实验 | 否证条件 |
|---|---|---|
| H1 property gate 降低错误 oracle | 12 条 CoAP + 10 条 SIP 候选，对比直接生成与 gate 后 oracle；专家盲审 | precision/unsupported calibration 无提升 |
| H2 外部 monitor 与可信内联断言在完整 trace 上等价，故障时更诚实 | 5 条 CoAP 双 oracle replay；注入 event drop、send hook 缺失、提前结束 | 完整 trace verdict 不一致，或故障时仍给 SATISFIED |
| H3 LLM slicing 减少 source mapping 成本但不能替代证明 | 10 个 CoAP/Kamailio mapping；测 proven producer recall、审阅行数和耗时 | 无节省或漏掉关键 trigger/outcome |
| H4 ActionTape + framer/repair 提高深层可达性 | 5 条 CoAP 性质，raw-byte vs structured action，等预算、至少 5 次重复 | parse-valid、trigger、closed obligations、TTE 无改善 |
| H5 LLM seed 优势来自语义而非仅“不是随机” | 随机、合法抓包、LLM ActionTape 三组等数量/长度 seed | 只优于随机，不优于合法抓包 |
| H6 capability gate 消除假满足 | timer/send hook on/off、ring drop、open horizon 故障注入 | 缺能力时出现 false SATISFIED |
| H7 generation correlation 防止跨会话串案 | 两条并发 block transfer，复用 token/MID，插 RESET | 与朴素 key 相比错配 verdict 不下降 |
| H8 KLEE scope manifest 能正确限定阴性结论 | 小有限域 exhaustive ground truth 与 KLEE 对照；故意 concrete 化关键字段 | manifest 未暴露反例空间缺口 |

实验报告应同时给：

- 原始 counts、micro aggregate 和 per-project macro。
- 重复次数、随机种子、均值/中位数、方差或置信区间。
- parse-valid rate、triggered obligations、closed obligations、UNKNOWN 和 violations。
- seed 本身是否直接触发、crash/AP 的去重定义和总 CPU-hours。

这样可以避免 ProtocolGuard Fig.2 的 155.2% 小基数放大问题，也避免只用 TTE 描述
CoAP 后端比较。

## 7. related work 可直接使用的严谨表述

Asadian et al. 在一个人工构造的固定 CoAP harness 中，将 12 条手工选择的
RFC 7252/7959 需求编码为断言，并在 libcoap 4.3.1 与 FreeCoAP ffc87fd 上比较
AFL++ 与 KLEE。两种技术在该受限场景内暴露了 9 个
implementation-requirement nonconformance；其多包测试使用固定 offset buffer，
KLEE 仅符号化预选字段，且完成探索所得阴性结论依赖 harness、环境模型和 assertion
的正确性。

ProtocolGuard 将规范规则候选抽取、LLM-guided program slicing、LLM 不一致分析、
assertion/seed 生成及 directed protocol fuzzing 组合到 11 个 C 实现。论文报告
198 个候选不一致中的 181 个 true positives 和 17 个 false positives，并将相关发现
归并为 158 个作者判定的 unique bugs，其中 70 个获得厂商确认。其评估支持把
LLM/静态分析作为候选发现与 PoC 辅助前端，但 assertion 语义正确性和动态可触发性
并非完备，因而不能将其视为形式化合规判定器。

TAFuzz 与上述工作互补：它不把 LLM 静态判断或 assertion crash 当作最终 oracle，
而关注版本化 raw observations、独立 trigger/outcome 证据、跨执行 correlation、
metric-time monitoring，以及在事件丢失、时钟边界、能力缺失和 horizon 未闭合时
给出 UNKNOWN。ProtocolGuard 风格方法可提供候选规则、源码位置和 ActionTape seeds；
CoAP 需求集可提供受控的跨协议 adapter/stateful benchmark，但两文均未验证 TAFuzz
的 MITL、capability-aware validity 或在线 cost guidance。

不宜写：

- ProtocolGuard 动态确认了全部 158 个 bug。
- 158 个结果都是安全漏洞或 CVE。
- KLEE 证明两个 CoAP 实现满足其余需求。
- 两文证明外部 MITL monitor 优于 assertion。
- CoAP 的 12 条需求验证了 metric-time fuzzing。
- ProtocolGuard 让总 crash 数提高了 155.2%。
- 一个 CoAP adapter 足以证明 TAFuzz 完全协议无关。

## 8. 最终评价

ProtocolGuard 的学术价值在于把规范候选、源码语义和 PoC 构造连接成一条规模化工程
流水线；它对 TAFuzz 最适合作为不可信但高产的前端。其最大研究风险是“同源规则和 LLM
同时产生怀疑与 oracle”，加上 handler-centric slicing 对 callback/timer 架构的系统性
盲区。

CoAP 论文的学术价值在于清楚证明：一旦 requirement 被准确编码，普通 AFL++ 和 KLEE
都能迅速暴露 silent non-conformance。它对 TAFuzz 最适合作为小规模、可控的跨协议
oracle/adapter benchmark。其最大研究风险是把手工 policy、固定 harness 和受限
symbolic space 中的结果扩大成完整 RFC conformance。

成熟的吸收方式不是复制两文的 assertion crash，而是保留它们的候选发现、合法定向 seed
和受控实验思路，再用 TAFuzz 的 raw-event/AP/closure/capability/UNKNOWN 机制承担正式
语义责任。
