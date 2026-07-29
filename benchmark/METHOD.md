# ArduPilot / PX4 可审计 MITL 性质提取方法

## 1. 目的与结论边界

本 benchmark 面向“性质驱动 fuzz”：先从独立于实现控制流的自然语言与接口材料建立待检验性质，再把原子命题（AP）绑定到冻结源码和可观测接口。源码绑定只回答“状态在哪里、怎样取值、怎样观察”，不能证明被测系统满足性质，也不能反向产生、修改或删除性质。

所有性质固定包含：

```text
implementation_satisfaction = NOT_ASSESSED
```

本阶段没有运行完整 fuzz campaign，也没有输出 ArduPilot 或 PX4 的符合/不符合结论。公式上的解析、可满足性和合成轨迹验证，只验证 benchmark 记录及监视器编码是否自洽，不验证飞控实现。

冻结对象和哈希见 [`source_freeze_manifest.json`](source_freeze_manifest.json)：

- ArduPilot：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`，Copter、Plane、Rover；
- ArduPilot MAVLink：`13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472`；
- PX4 v1.17.0：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`，multicopter SITL；
- PX4 MAVLink：`33af200d25ec6f0925b49b1ba82bbf1294ea5f72`；
- ArduPilot 官方 wiki 镜像：`209e532bc97e5a41966f8c9ab483323c264cae08`，状态为 `MAIN_ONLY`，不是与 SUT 配对的 release 文档；
- PGFuzz、ADGFuzz、ProtocolGuard 的论文和 artifact 只作方法或历史规则对照。

## 2. 三篇论文怎样被采用

### 2.1 PGFuzz：采用人工识别—模板编译的顺序，不继承历史性质

完整审计见 [`paper_audits/PGFuzz_MTL_extraction_audit.md`](paper_audits/PGFuzz_MTL_extraction_audit.md)。PGFuzz 的真实过程不是端到端自然语言抽取，而是：

1. 两位作者人工阅读 documentation 与 source-code comments；
2. 人工写自然语言 policy；
3. 人工套用 T1/T2/T3 形状并处理冲突；
4. 公式确定后，静态/动态 profiling 才建立 term—input/state 映射或估计未知 `k`。

因此，本方法采用“先证据和公式、后源码 binding”的隔离顺序。PGFuzz 的历史公式、旧版本网页和 artifact predicate 只可充当 `HISTORICAL_LEAD`，不能自动成为当前 ArduPilot/PX4 性质。

PGFuzz 时间值按真实来源分别保存：

- 文档字面值，例如历史 `A.FLIPGeneral` 的 2.5 s；
- 100 次仿真最大观测值，例如 `A.BRAKE1` 的 12.7 s，标签为 `PAPER_EMPIRICAL_MAX`，不是产品规范；
- 参数加调度余量，例如 `COM_POS_FS_DELAY + k_schedule`；未公开的 `k` 和操作数保持 `UNKNOWN`；
- `t-1` 只表示上一观测索引。没有采样周期证据时，绝不解释成一秒。

### 2.2 ADGFuzz：三类规则保留为辅助判定器

完整审计见 [`paper_audits/ADGFuzz_oracle_rule_audit.md`](paper_audits/ADGFuzz_oracle_rule_audit.md)。论文、README 和代码中的 ground、route deviation、message silence/software crash 规则存在阈值、消息和计时差异：

- ground 使用状态枚举、文本、landed 转移或代码内距离阈值；
- route deviation 混有 7 s 示例、5 s/3 次、12 s/7 次、12 s/9 次及 PX4 0.05 m/4 次等不同规则；
- silence 的论文值是 2 s，代码实际是 6 次 × 0.3 s、且检测任意 MAVLink 消息而不只是 HEARTBEAT。

这些数值没有当前系统正式要求依据，时钟又可能是测试机 wall/monotonic clock 或不定周期计数。因此三类规则只保留为 `AUXILIARY_ORACLE`，不会进入两个系统的 MITL 性质计数。ADGFuzz Python 位置是判定器实现位置，不是被测飞控 AP 的源码绑定。

### 2.3 ProtocolGuard：采用上下文树和身份绑定，拒绝实现驱动筛选

完整审计与 2023–2026 方法矩阵见 [`paper_audits/ProtocolGuard_NLP_adaptation.md`](paper_audits/ProtocolGuard_NLP_adaptation.md)。采用的部分是：

- 保存章节层级与邻近上下文；
- 恢复指代、因果、定义和依赖从句；
- 保留规范字段到源码语义身份的证据链。

不采用的部分是：

- 只保留 single-message flow；
- 排除历史状态、后续消息和并发关系；
- 删除无数值的 before/after；
- 只输出 request/response type/field；
- 用当前实现或 DUT 上“成立”来筛选、修正规范。

本方法结合 nl2spec、NL2TL、SYNTHTL、GraFT、ParCleanse、时间归一化、DocTree/DocGraph 和事件关系研究，但不把任何 LLM 自由输出当作最终公式。LLM 只提出带原始证据跨度的结构化 IR；确定性程序完成一致性检查、时间归一化和公式编译。

## 3. 来源层级与“不能从实现反推”的防火墙

候选来源按以下层级分别记录，不用单一置信分数混合：

| 来源类别 | 用途 | 约束 |
|---|---|---|
| `FORMAL_REQUIREMENT` | 正式要求 | 仍需闭合适用范围、例外和版本 |
| `OFFICIAL_BEHAVIOR` | 官方行为说明 | 可产生性质，但不自动等同强制要求 |
| `PARAM_METADATA` | 参数定义、单位、禁用域 | 可参数化或产生低权威候选；运行值须另取快照 |
| `SOURCE_COMMENT` | 当前源码注释 | 只产生低权威候选；不得使用普通控制流替代注释 |
| `MAVLINK_INTERFACE_DEFINITION` | 消息、字段、枚举、单位 | 定义观测语义，不自动定义飞控行为义务 |
| `PAPER_AUTHOR_EXPERIENCE` | 论文经验阈值 | 只作辅助/历史规则，明确样本和聚合方法 |

明确禁止作为性质来源的材料包括：普通 `if`/guard、已有 timeout 实现、watchdog、循环计数器、测试 sleep、生成 predicate 和一次运行轨迹。它们可用于定位 AP 或执行测试，但不能发起规范。

## 4. 冻结语料、DocGraph 与高召回预筛

冻结语料覆盖：

- ArduPilot Copter/Plane/Rover 的 mode、arming、failsafe、mission、navigation、参数元数据、MAVLink 支持材料和源码注释；
- PX4 v1.17 multicopter 的 mode、failsafe、mission、Offboard、parameters、events、uORB、MAVLink 文档和源码注释；
- 两个源码树固定 MAVLink 子模块的实际 XML 方言闭包。

[`scripts/build_corpus.py`](scripts/build_corpus.py) 将文档、表格、列表、参数记录、定义、注释和 MAVLink 实体规范化为 DocGraph。节点保存版本、路径、哈希、行/节/anchor 和原文；边保存 parent、defines、refers-to、parameterizes、exception、coreference、precondition 和 temporal relation。

预筛关键词分为规范性、时间性、状态性、条件/例外和参数实体五组。关键词只提高 recall，不决定候选是否为规范。

本轮确定性扫描覆盖 9,772 个文件：

- ArduPilot：4,225 文件、112,821 节点、213,227 边、19,003 个候选命中；
- PX4：5,547 文件、102,029 节点、187,470 边、17,148 个候选命中。

共 36,151 个候选全部保留在 adjudication ledger。47 个与 13 条已建性质的证据区间重叠；其余 36,104 个状态为 `PENDING_CONTEXT_REVIEW`。这里的“语料穷尽”指每个纳入文件均被确定性扫描和登记，不表示 36,151 个命中均已完成人工上下文裁决。

相关产物：

- [`extraction_runs/milestone3/`](extraction_runs/milestone3/)：DocGraph、候选和覆盖摘要；
- [`ArduPilot/coverage_ledger.csv`](ArduPilot/coverage_ledger.csv) 与 [`PX4/coverage_ledger.csv`](PX4/coverage_ledger.csv)：逐文件覆盖状态；
- [`extraction_runs/milestone4/ArduPilot_adjudication_ledger.jsonl`](extraction_runs/milestone4/ArduPilot_adjudication_ledger.jsonl) 与 [`extraction_runs/milestone4/PX4_adjudication_ledger.jsonl`](extraction_runs/milestone4/PX4_adjudication_ledger.jsonl)：逐候选状态。

PX4 早期 14-candidate YAML 专项草案不属于最终语料入口。它已移至
[`extraction_runs/milestone4/superseded_px4_draft/ARCHIVE_NOTICE.md`](extraction_runs/milestone4/superseded_px4_draft/ARCHIVE_NOTICE.md)，
状态固定为 `SUPERSEDED_NON_CANONICAL_DRAFT`；24 个文件由 manifest 固定归档隔离时的哈希和字节数。
正式 `PX4/` 目录禁止遗留 YAML、无数值 epsilon 占位符和把 heartbeat/HRT 实现候选反向当作
telemetry/data-connection 规范事件的旁路输入。最终 gate 同时校验正式目录隔离和归档后不可漂移；因没有归档前外部锚定收据，它不独立证明更早历史身份。

## 5. 上下文恢复与 Requirement IR

一个候选不会只截取含数字的单句。上下文窗口按以下顺序扩展：

1. 当前句的列表项、表格行、参数项或注释块；
2. 当前小节的定义、前置段落和紧随其后的例外；
3. 交叉链接的参数、mode、failsafe、mission 和 MAVLink 定义；
4. 指代对象、取消/重置条件、合法 mode transition；
5. 版本冲突或同一概念的多处定义。

LLM 或人工提议被转成类型化 Requirement IR：actor、modality、trigger、preconditions、obligations、prohibitions、exceptions、scope start/end、correlation keys、event relations 和 unresolved references。每个字段反链到原始 source span；指代消解只作 overlay，不能覆盖原文。

确定性检查包括：

- before/after 逆关系与传递性；
- 事件图无环性；
- 互斥状态不能在同一时点成立；
- trigger/response/cancel/reset 使用同一车辆和 campaign correlation；
- 类型、单位、坐标系和 freshness 一致；
- 多来源冲突保留为 unresolved，不用实现行为裁决。

## 6. TimeContract：数值、起止和时钟均须可追溯

每个时间表达保存：

```text
semantic_start_event / semantic_end_event
cancel_event / reset_event
raw_expression
lower / upper / interval openness / unit
source_type / parameter_id / derivation operands
clock_domain / timestamp_carrier
conversion / measurement_uncertainty / freshness
```

允许的时间数值来源只有：

1. 当前官方文档字面值；
2. 参数元数据加实际运行参数快照；
3. 所有操作数可追溯的完整派生式；
4. 明确标记的论文作者经验；
5. `UNKNOWN`。

13 条当前性质的时间均来自 `RUNTIME_PARAMETER`。源码默认值只用于说明元数据，具体公式使用里程碑 6 保存的 `PARAM_VALUE`；禁用值不会被代入零或负区间。比如：

- `RTL_LOIT_TIME=5000 ms` 保留原始值并按 `5000 / 1000 = 5 s` 精确转换；
- `TKOFF_TIMEOUT=0` 和 `COM_FLT_TIME_MAX=-1` 落在官方禁用域，因此不产生具体公式；
- 0.5 s、1.5 s 等小数界在 TAMonitor 中用整数毫秒 tick 精确缩放，不舍入、不加入 epsilon。

时钟域严格区分：飞控单调启动时钟、SITL 仿真时钟、MAVLink sender boot time、Unix/UTC、GPS 时间、GCS 单调到达时间和插桩单调时钟。当前 TimeContract 选择的是 `AUTOPILOT_MONOTONIC_BOOT`；若 AP 只能用 GCS 到达时刻近似，则必须记录转换和传输/队列/调度不确定性，不能把到达时刻冒充内部事件时刻。

无独立数值的 immediately/promptly 不补人工阈值。边界判断可能受采样或传输误差影响时，结论固定为 `INCONCLUSIVE`。

## 7. 从 IR 到数学 MITL 和 TAMonitor 语法

IR 只通过确定性模板编译。典型的“超时前禁止、达到超时后最终触发”形状是：

```text
G((trigger & applicable) ->
  (G_[0,T) !response & F_[T,infty) response))
```

公式必须使用 trigger edge，而不是持续状态在每个采样点重复开启窗口；区间开闭、例外、cancel/reset 和作用域必须来自 IR。

数学表示与具体监视器语法分开保存。MightyPPL/TAMonitor 当前语法使用整数 interval bound、`&&`/`||`、无下划线的 temporal interval，并要求某些否定 temporal operand 加括号。Stage 7 转换遵守：

- 秒制数学公式精确缩放为毫秒 tick；
- 区间开闭原样保留；
- `infty` 保留为无上界，不人为添加“迟到”阈值；
- 不增加 epsilon；
- 保存原公式 probe、转换后的 parser/build 命令、stdout/stderr、工具和语法源码哈希。

对外层 `G` 和无上界 `F_[T,infty)`，有限合法前缀通常只能得到 `INCONCLUSIVE`，而不是 `SATISFIED`。超时前错误触发属于有限 safety counterexample，可得到 `VIOLATED`。缺失或“更晚但仍无上界”的有限前缀不能被伪造成违反。

合成 trace 的时间列使用单调递增的绝对全局毫秒时刻。TAMonitor 的 trace parser 原样保存时间，MoniTAal symbolic state 把全局 clock 约束到该值；因此不能把事件间 delay 当作输入时刻。Stage 7 的 49 条最终 trace 结果为 42 个预期/实际 verdict 匹配、6 个 RTL 默认 BDD 投影上限、1 个 PX4 RC-loss 精确端点 mismatch。六条公式仅获得“合成 trace suite 的 monitor gate 通过”；一条失败、一条不支持。任何公式门禁状态都不会改变性质上下文状态或 `implementation_satisfaction`。

## 8. AP 真值条件与当前源码多对多绑定

每个 AP 在查看源码 binding 之前先定义：受控自然语言、布尔真值条件、类型、单位/坐标系、validity guard、freshness、scope、aggregation 和 correlation key。

随后针对冻结提交建立多对多映射：

- ArduPilot：AP_Param、flight mode/state、mission/failsafe 状态、MAVLink handler/sender、赋值与消费点；
- PX4：parameters、uORB topics、commander/navigator module state、events、MAVLink stream/receiver；
- 一个 AP 可绑定多个变量、字段、函数、返回、赋值、回调、producer/consumer 和 observation site；
- 每个 binding 保存 commit、文件、行、symbol、semantic identity、type、function、role、`EXACT/MAY/MODELLED/NAME_ONLY` 和固定 commit permalink。

当前共有 46 个 AP、227 个源码 binding：

- ArduPilot：25 AP，107 binding，全部 `BOUND`；
- PX4：21 AP，120 binding，其中 18 `BOUND`、3 `PARTIALLY_BOUND`。新增的 partial 是 `PX4-MC-GCSLOSS-002-AP-01`：官方 data-link loss 未定义 liveness predicate/时钟，当前 heartbeat/HRT 位置只是 `MODELLED` 候选。

详细数据见两个系统的 `atomic_proposition_map.{csv,json}`、`source_bindings.csv` 和每条 `properties/<id>.{md,json}`。无法证明的语义保持 `PARTIALLY_BOUND`/`UNRESOLVED`，不按名字猜测。

## 9. MAVLink 可观测性与完整目录

完整读者说明见 [`MAVLink_ArduPilot_PX4_observability.md`](MAVLink_ArduPilot_PX4_observability.md)，机器可读目录在 [`mavlink_catalog/`](mavlink_catalog/)。必须区分三种对象：

1. MAVLink message field：在线消息载荷字段；
2. `MAV_CMD` 的 `param1`–`param7`：某个命令的参数槽；
3. firmware configuration parameter：通过 PARAM microservice 读取/写入的 AP_Param/PX4 参数。

目录还区分四层支持证据：方言 XML 定义、冻结源码静态引用、默认 SITL 运行观测、请求窗口观测。`FAILED`/`DENIED` ACK、默认流中未出现、或“定义于方言”均不能单独推出全局不支持。

AP 可观测性使用：

- `DIRECT`：一个消息字段和有效性条件即可判断；
- `DERIVED`：需要同一或多条消息的确定性派生；
- `CONDITIONAL`：只在特定 stream/request/mode/config 下存在；
- `INSTRUMENTATION_REQUIRED`：标准 MAVLink 不足，需源码绑定探针；
- `UNRESOLVED`：缺少可靠等价观测。

46 个 AP 的分布为：`DIRECT=9`、`DERIVED=6`、`CONDITIONAL=12`、`INSTRUMENTATION_REQUIRED=16`、`UNRESOLVED=3`。消息中的时间字段逐项标注 boot、Unix、GPS、ambiguous `time_usec` 或无时间字段；主机接收时间另列，绝不静默替代 sender/internal time。

## 10. 运行参数与消息面捕获

里程碑 6 在冻结构建上完成四个默认 SITL profile：ArduCopter、ArduPlane、Rover、PX4 SIH multicopter。保存启动命令、参数快照、被动 baseline、逐消息 request sweep、ACK、解码消息、host monotonic arrival 和 time-field 证据。

聚合结果为：

- 4,999 个运行参数行；
- 1,307 个 profile × 静态消息定义行，另保留 3 个非目录 `BAD_DATA` 观测；
- 128 个实际观测 time-field 行；
- 15 个 property/profile 参数实例；
- 8 条性质具有单一具体公式。

这些捕获只证明配置值、消息出现和时间载体，不执行性质场景、不判断实现满足性。

## 11. 验证与审核门禁

每条性质的门禁分为：

1. JSON Schema；
2. 原文路径、哈希、行/节和 exact quote；
3. 类型、单位、坐标系；
4. event/time graph；
5. 数学公式到 monitor syntax 的解析；
6. formula 和 negated formula 的可满足性，用于排除不可满足与重言式；
7. 非空洞 trigger/non-trigger 合成轨迹对；
8. 边界、缺失、例外和错误关联轨迹；
9. 源码 symbol/line/permalink；
10. 独立自动审计；
11. 最终人工审核。

自动审计不是“两位人工审核”，不会设置 `review.decision=ACCEPT`。本轮独立自动证据审计把 12 条记录回退为 `NEEDS_CONTEXT`、保留 1 条参数元数据记录为 `CANDIDATE`；`REVIEW_READY=0`、`ACCEPTED=0`。这不是人工 reject。人工审核应重点核对：ArduPilot `MAIN_ONLY` 文档与冻结 SUT 的版本关系、取消/重置/连续条件 lifetime、任务/模式例外、AP 关联与 freshness、内部时钟探针、以及有限前缀 `INCONCLUSIVE` 的含义。Catalog 级 `evidence_snapshot_at` 保留 M6 运行证据快照时间，`stage7_enriched_at` 记录 M7 语义纠偏/审核快照，`generated_at` 在 M7 交付中与后者一致，不再把 M6 时间冒充最终产物时间。

## 12. 复现顺序

在 `/home/lqq/project/TAFuzz` 执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_corpus.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_corpus.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 6
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --force
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 7
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_property_catalog.py --stage 7
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_source_bindings.py --run-clangd
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/mavlink_catalog/validate_catalog.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/apply_runtime_catalog.py --check
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_milestone6.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_benchmark.py
```

具体 monitor 命令、输入轨迹、stdout/stderr、metadata 和 hash 位于 `extraction_runs/milestone7/monitor_validation/`。最终结果与尚未关闭的人工门禁见 [`RESULTS.md`](RESULTS.md)。
