# PGFuzz 的 MTL 性质提取与时间语义审计

## 1. 审计结论

PGFuzz 没有实现“从自然语言自动抽取 MTL 性质”的流水线。论文描述的真实顺序是：两位熟悉系统的作者人工阅读官方文档和源码注释，人工写出自然语言 policy，人工套用 T1/T2/T3 模板并处理冲突；性质和公式冻结之后，profiling engine 才把公式中的 term 映射到输入与状态，并用静态/动态分析缩小 fuzz 空间或估计未知时间 `k`。

因此，本 benchmark 只采用 PGFuzz 的三点经验：

1. 从官方行为文档、参数说明和源码注释建立高召回候选；
2. 将自然语言先拆成主体、触发、条件、义务、例外、时间和 AP，再机械编译公式；
3. 对未知调度余量保留来源与测量方案。

不采用的部分是：把历史 policy 直接移植到当前系统、把一次观测或循环次数当成秒、用当前实现行为补齐规范、以及把 artifact 中的手写 predicate 当成论文公式的等价实现。

本文件仅审计方法和历史条目，不判断当前 ArduPilot/PX4 是否满足任何性质。所有转入系统目录的条目仍须在冻结版本中重新找到官方证据，并固定 `implementation_satisfaction: NOT_ASSESSED`。

## 2. 冻结证据

| 对象 | 冻结身份 | 本审计用途 |
|---|---|---|
| 论文 PDF | 18 页；SHA-256 `bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa94c90d7fcd` | 方法、模板、历史 policy、实验性时间值 |
| PGFuzz artifact | `/home/lqq/project/TAFuzz/baseline/pgfuzz`；commit `7eaebf21116087249b8329d4ba7337a24a34ecb9` | 核对 predicate 与计时实现，不作为当前系统规范 |
| 当前 ArduPilot | commit `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` | 后续独立重抽取与绑定 |
| 当前 PX4 | v1.17.0；commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` | 后续独立重抽取与绑定 |

完整冻结记录见 [`source_freeze_manifest.json`](../source_freeze_manifest.json)。论文使用的是 ArduPilot 4.0.3 和较早 PX4；它与当前冻结 SUT 不是同一基线。

## 3. 论文中的真实提取过程

### 3.1 性质来源与人工步骤

论文第 4 页 §V-A1 明确说明，作者从 ArduPilot、PX4、Paparazzi 的 documentation 和 source-code comments 中人工识别 policy，先写成自然语言，再写成 MTL。两位作者完成 ArduPilot、PX4、Paparazzi 的识别和公式化分别耗时 7.5、3.5、2.4 小时；耗时包括阅读官方文档/源码、写自然语言 policy、翻译为 MTL、发现冲突并协调冲突。

这段证据确定了五个边界：

- “documentation/comments”是历史来源集合，不表示任意控制流可以反推规范；
- policy identification 是人工工作，不是 LLVM 分析或 predicate generator 的产物；
- 冲突检查发生在公式化阶段，冲突不是用当前实现行为裁决；
- 静态分析只在已有公式之后建立参数—term 关系；
- dynamic analysis 估计部分未知时间或输入—状态关系，不赋予条目规范权威性。

### 3.2 T1/T2/T3 模板

论文 Table I 的三个模板是：

| 模板 | 论文意图 | 规范化理解 | 本任务采用限制 |
|---|---|---|---|
| T1 | `termi → ◇[0,k] termj` | 触发后在有界未来满足响应 | 必须给出触发边沿、取消/重置、时钟域和 `k` 的来源 |
| T2 | 条件成立时若干 term 为真、另一些为假 | 状态约束/禁止 | 必须恢复作用域、例外和逻辑括号；不能照抄论文排版式 |
| T3 | `□(termi ∧ … ∧ termn → termj)` | 全局条件—义务 | `t-1` 只能表示“上一观测”，除非采样周期有独立证据，否则不是一秒 |

这些模板有助于编译，但并不能代替上下文恢复。尤其是模式进入、模式持续、模式退出、任务项目切换和消息丢失是不同事件；只用 `Mode_t = X` 会在每个采样点重复启动义务。

### 3.3 公式之后的 term/input 映射

论文第 5–7 页的 profiling engine 流程为：

1. 将已存在的 policy 分解为物理状态、配置参数、环境因素等 term；
2. 从手册建立物理状态与同义词列表；
3. 将参数名映射到源码成员，再从参数变量构建 def-use 链；
4. 用动态分析筛掉只读/不支持输入并估计输入对状态的影响；
5. 汇总 input-policy map；
6. 对仍为未知的时间 `k` 运行仿真估计。

这不是“源码先发现性质”。本 benchmark 保持同样的顺序隔离：性质 lane 先冻结原文、IR、时间来源和符号公式；binding lane 之后只回答 AP 在当前源码中的身份与观测位置。

### 3.4 predicate generator 的范围

Appendix B 的 predicate generator 解析已有 MTL，构造表达式树并生成距离计算代码。它只自动化“已有公式到距离 predicate”的步骤，不能：

- 找文档；
- 判断句子是否为规范；
- 补全上下文或例外；
- 证明时间值正确；
- 自动把历史公式映射到新版本源码。

公开仓库进一步说明 artifact 并非完整审计数据集：现有 policy 目录为 ArduPilot 28 个、PX4 21 个；49 个 `preconditions.txt` 中只有 1 个非空。仓库没有为每条 policy 保存最短完整原文、页面/段落、公式 AST、term 真值条件、时间推导或当前源码符号身份。

## 4. 时间约束逐项审计

### 4.1 时间来源分类

| 历史条目 | 数值/表达式 | 论文给出的来源 | 起止语义 | 时钟/载体 | 审计结论 |
|---|---:|---|---|---|---|
| `A.FLIPGeneral` | 2.5 s | Table XII 自然语言中的文档字面值 | 进入 FLIP/开始翻滚 → 完成翻滚并回到原模式 | 论文未明确；artifact 用测试机单调计时器 | `DOCUMENT_LITERAL` 历史线索；当前版本须重新找文档 |
| `A.FLIP3` | `k` | 未报告具体估计 | 完成 `A.FLIP2` → 姿态恢复 | 未说明 | `UNKNOWN`，不可补数 |
| `A.BRAKE1` | 12.7 s | 100 次仿真中达到目标状态的最大用时 | 满足 BRAKE 前置条件 → 位置不再变化/停止 | 仿真测量；论文未给 timestamp carrier 和采样误差 | `PAPER_EMPIRICAL_MAX`，不是产品规范时间 |
| `A.DRIFT1` | `k` | 论文没有报告数值 | GPS failure in DRIFT → 进入 `FS_EKF_ACTION` 指定模式 | 未说明 | `UNKNOWN` |
| `PX.GPS.FS1` | `COM_POS_FS_DELAY + k` | 参数定义给出基础延迟；`k` 为软实时调度额外延迟 | GPS loss detected → GPS failsafe triggered | 论文未固定消息/内部时钟 | 符号式可保留；参数值与 `k` 必须分别溯源 |
| `ALIVE`/类似等待 | `k` | 未公开完整估计 | 依条目而异 | 未说明 | 不得从代码 sleep 推导 |

### 4.2 `A.BRAKE1` 的 12.7 秒怎样得到

论文第 7 页 §V-A2 说明其估计过程：选择与 policy 相关的随机输入，使车辆满足前置条件，例如进入 BRAKE；测量达到目标状态（示例为 `Pos_t = Pos_{t-1}`）所需时间；否定前置条件后重测；重复 100 次；把最大所需时间定义为 `k`。论文报告 BRAKE 的最大值为 12.7 秒。

该数值的正确标签是：

```text
source_type = PAPER_EMPIRICAL_MAX
sample_count = 100
aggregation = max
reported_value = 12.7 s
clock_domain = simulator_measurement_unspecified
timestamp_carrier = UNKNOWN
configuration_snapshot = NOT_REPORTED
measurement_uncertainty = NOT_REPORTED
```

不能把 12.7 秒解释成 ArduPilot 官方要求，也不能把它自动用于当前 commit、不同质量/速度/任务或不同 SITL speedup。

### 4.3 `PX.GPS.FS1` 的参数时间与调度余量

论文第 14–15 页说明：`COM_POS_FS_DELAY` 表示检测到 GPS/全局位置丢失到触发 failsafe 的配置延迟；公式另加 `k`，作者称其来自软实时任务调度。作者重复测量到的额外延迟小于一秒，并采用“两倍最大延迟”作为余量，但没有公开这个最大值、实际 `k`、采样分布、配置快照或 timestamp carrier。

因此可审计表达只能写为：

```text
upper_bound = COM_POS_FS_DELAY(snapshot) + k_schedule
k_schedule.source = PAPER_EMPIRICAL_RULE
k_schedule.formula = 2 * max(observed_scheduler_delay_samples)
k_schedule.operands = UNPUBLISHED
k_schedule.concrete_value = UNKNOWN
```

在没有当前 PX4 官方要求与当前 SITL 参数快照前，该条目只是历史候选。不能把 PGFuzz artifact 的循环次数当作 `COM_POS_FS_DELAY` 秒。

### 4.4 `t-1` 不是一秒

论文 Figure 13 明示 `c` 和 `p` 分别指 current time `t` 与 previous time `t-1`。它是离散观测索引，不提供观测周期。若实际循环受消息速率、阻塞接收、`sleep` 或仿真 speedup 影响，则 `t-1` 的物理时间差是变量。

本 benchmark 中凡使用“上一观测”的 AP 必须保存：消息类型、生产 timestamp、到达 timestamp、采样策略、最大 freshness 与丢样处理；没有这些信息时不得把索引差写为秒制 MITL 区间。

### 4.5 论文中不属于性质时间的数值

以下时间只描述 profiling、fuzz campaign 或 harness，不能进入系统性质：

- 每种 operation mode 记录一分钟；
- 输入依赖最多重复 10 次；
- 100 次仿真是 `k` 的估计样本数；
- 总 fuzzing 时间预算 `τ`；
- artifact 的 `sleep(3)`、`sleep(4)` 等观察等待。

## 5. Table XII 公式与自然语言的内部不一致

这些问题说明 PGFuzz 表格只能作为候选线索，不能直接复制为 benchmark 公式。

| 条目 | 问题 | 本任务处理 |
|---|---|---|
| `A.GPS.FS1` | 自然语言是“卫星数少于 4 时触发 GPS failsafe”，表中公式却写成 `GPSfail → GPScount < 4`，蕴含方向相反 | 只保留原文候选；当前官方证据重新形式化 |
| `PX.RTL4` | 原文条件是 `RTL_LAND_DELAY = -1`，公式前件却检查 `RTL_DESCEND_ALT = -1` | 公式拒绝；不得修正后冒充论文原式 |
| `PX.ORBIT6` | 原文说最大 acceleration 为 `2 m/s²`，公式比较 `Circle_speed` 且仍写 `m/s²` | 类型/单位错误，拒绝 |
| `A.FLIP3` | “恢复 roll/pitch/yaw within k” 的排版公式把 `◇[0,k]` 与等式混接，语法/语义不可直接解析 | 回到原文建立三条有界义务或复合响应 |
| `A.LAND1/2` | 公式出现多余 `∧→`，且需要确认速度符号、单位与容差 | 公式拒绝，当前文档重抽取 |
| `A.RTL1` | 原文含“升高直到达到阈值”，表中只比较相邻样本，丢失 until/终止语义 | 需要完整事件/状态图 |
| `A.FLIPGeneral` | 自然语言包含“完成 rolling 且返回原模式”，公式仅用模式变化近似完成事件 | AP grounding 不充分 |
| `A.LOITER1` 等 | 用相邻样本严格相等表示保持位置/姿态，未表达估计噪声、坐标系、freshness | 不能原样接受 |

此外，正文个别案例描述使用“eventually”，对应示例/实现却使用固定窗口或相邻观测；遇到这种差异必须保存 `paper_prose`、`paper_table_formula`、`artifact_predicate` 三个层次，不以其中任一层静默覆盖另两层。

## 6. 论文与 artifact 的计时/谓词偏差

### 6.1 `A.FLIPGeneral` / artifact `A.FLIP4`

[`ArduPilot/fuzzing.py:602`](../../baseline/pgfuzz/ArduPilot/fuzzing.py#L602) 在每个 FLIP 状态的 `NAV_CONTROLLER_OUTPUT` 处理过程中重写 `flip_start_time`；[`ArduPilot/fuzzing.py:1404`](../../baseline/pgfuzz/ArduPilot/fuzzing.py#L1404) 用测试机 `timeit.default_timer()` 求差，而 [`ArduPilot/fuzzing.py:1423`](../../baseline/pgfuzz/ArduPilot/fuzzing.py#L1423) 每轮又将起点清零。这不是稳定的“FLIP 进入事件到完成事件”的计时器。

### 6.2 `A.BRAKE1`

论文的 `k=12.7s` 来自 100 次仿真最大值；artifact 的 [`ArduPilot/fuzzing.py:2148`](../../baseline/pgfuzz/ArduPilot/fuzzing.py#L2148) 仅给非零地速两次宽限机会，而主循环在 [`ArduPilot/fuzzing.py:2624`](../../baseline/pgfuzz/ArduPilot/fuzzing.py#L2624) 每轮 `sleep(4)`。这组合成与消息/循环相关的计数规则，不是精确 12.7 秒窗口。

### 6.3 `PX.GPS.FS1`

[`PX4/fuzzing.py:1734`](../../baseline/pgfuzz/PX4/fuzzing.py#L1734) 把 `gps_failsafe_count` 与参数数值比较；主循环 [`PX4/fuzzing.py:2332`](../../baseline/pgfuzz/PX4/fuzzing.py#L2332) 每轮 `sleep(3)`，参数请求还可额外等待最多 5 秒。循环次数、参数秒数和主机等待混在一起，不能视为论文 MITL 的实现。

### 6.4 未使用的 MAVLink 时间

两份 fuzzer 都读取 `SYSTEM_TIME.time_unix_usec`，例如 [`PX4/fuzzing.py:686`](../../baseline/pgfuzz/PX4/fuzzing.py#L686)，但上述三个 predicate 没有用它计算窗口。读取一个时间字段不等于公式采用了 sender Unix 时间；实际计时仍主要来自 host timer/循环计数。

## 7. 面向本 benchmark 的改造流程

PGFuzz 方法被改造成以下可审计流程：

1. **先冻结语料**：当前官方文档、当前参数元数据、当前源码注释和当前 MAVLink XML 分层保存版本、哈希、段落与抓取日期。
2. **高召回预筛**：情态、时间、状态、条件/例外、参数 ID 只用于找候选。
3. **上下文闭合**：读取父节、列表/表格、定义、参数链接、例外和跨节引用；不只摘单句。
4. **类型化 Requirement IR**：LLM 只能输出证据跨度绑定的 actor/trigger/precondition/obligation/exception/scope/correlation/time。
5. **时间防火墙**：字面值、参数值、派生值、论文经验、未知分别标记；无数值的 immediately 不补阈值。
6. **确定性公式编译**：由 IR 生成符号 MITL，再用实际 SITL 参数快照实例化；每个子公式反链到原文。
7. **AP binding 后置**：只在公式冻结后映射当前源码变量、函数、赋值点、消息生成/消费点；不从控制流修补性质。
8. **三层验证**：公式语法/类型/可满足性，人工语义审核，正例与单边界变异轨迹的 TAMonitor 结果。

## 8. 历史条目进入当前 benchmark 的判定

| 情况 | 决策 |
|---|---|
| 在当前官方文档找到同义要求，时间与例外闭合，当前源码可绑定 | 可作为新性质；新的 property ID 与证据，不继承历史满足结论 |
| 只有 PGFuzz Table XII 或旧版本链接 | `HISTORICAL_LEAD` / candidate |
| 只有 PGFuzz artifact predicate | rejected：实现不能发起性质 |
| 时间仅有未公开 `k` | `NEEDS_TIME_BOUND`，保留符号式或定性顺序 |
| AP 只能由相邻消息猜测或字段单位不匹配 | `NEEDS_BINDING` / `UNRESOLVED` |
| 公式与自然语言冲突 | 保存冲突并回到当前原文，不能“修正后照搬” |

## 9. 可复核命令

```bash
sha256sum "/mnt/c/Users/PC-123/Zotero/storage/5UFRMB89/Kim 等 - 2021 - PGFUZZ Policy-guided fuzzing for robotic vehicles.pdf"
git -C /home/lqq/project/TAFuzz/baseline/pgfuzz rev-parse HEAD
find /home/lqq/project/TAFuzz/baseline/pgfuzz/ArduPilot/policies -mindepth 1 -maxdepth 1 -type d | wc -l
find /home/lqq/project/TAFuzz/baseline/pgfuzz/PX4/policies -mindepth 1 -maxdepth 1 -type d | wc -l
nl -ba /home/lqq/project/TAFuzz/baseline/pgfuzz/ArduPilot/fuzzing.py | sed -n '590,615p;1398,1425p;2130,2156p;2618,2626p'
nl -ba /home/lqq/project/TAFuzz/baseline/pgfuzz/PX4/fuzzing.py | sed -n '686,692p;1705,1743p;2326,2334p'
```

## 10. 未决证据

- 论文没有公开 100 次 `k` 估计的原始轨迹、SITL 配置、timestamp carrier 和误差；12.7 秒只能按论文经验值保存。
- `PX.GPS.FS1` 的实际 `k_schedule` 及其样本操作数未公开。
- 论文历史链接部分使用短链接且版本不稳定，不能证明其文本仍适用于当前 SUT。
- 公开 artifact 缺少完整原文—公式—term—源码身份链；后续映射必须完全基于当前冻结源码重建。

