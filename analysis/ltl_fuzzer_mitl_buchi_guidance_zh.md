# LTL-Fuzzer 对 ArduPilot MITL 模糊测试的可复用机制与已实现方案

更新时间：2026-07-22

## 1. 先给结论

可以把“性质的否定”编译成布希自动机，并利用其接受条件引导 ArduPilot 的 MITL 模糊测试；但必须分清两个结论：

1. **有限可判定违反**：安全性质或带有限截止时间的性质，例如“请求后 5 秒内响应”。截止时间已过且仍无响应时，有限轨迹就足以判定违反。
2. **无界活性候选**：例如“请求后未来某时最终响应”。有限轨迹到达一次否定自动机的接受位置仍不够；最多可以找到一个可重复的接受循环，并把它作为高优先级、可重放的问题候选。

LTL-Fuzzer 正是用“程序状态重复 + 接受循环”的套索证据处理第二类问题。这个思路可借鉴，但不能原样搬到 ArduPilot：飞控仿真具有连续物理状态、调度抖动、传感器噪声和单调时钟，整体内存很难两次完全相等。

本次已经实现并运行了一个最小原型：

- 直接读取当前 TAMonitor 的 `pta_prefix_costs.jsonl`；
- 组合否定自动机位置、性质时钟区、性质相关飞控状态和飞控源时间；
- 检测可跨多条自动机边的正时间接受套索；
- 要求至少两个独立重放具有相同事件、状态和相对时间签名才升级证据；
- 用精确剩余代价和目标边选择种子，用静态相关性与 PGFuzz 动态影响结果选择变异；
- 无界性质永不从有限轨迹输出 `FINITE_VIOLATION`。

原型代码位于 `src/StaticAnalysis/runtime/mitl_buchi_guidance/`。12 个自动测试全部通过，命令行端到端示例也通过。当前能确认的是**离线引导算法与数据接口可行**；TAMonitor 无限词逐前缀导出和 ArduPilot 性质相关插桩还没有接通，因此不能声称完整 SITL 闭环已经完成。

## 2. 术语图例

| 原词 | 完整英文与中文 | 在本方案中的含义 | 对结论的影响 |
|---|---|---|---|
| `LTL` | Linear-time Temporal Logic，线性时序逻辑 | 描述事件先后与无限行为，不直接带数值时间区间 | LTL-Fuzzer 的性质语言 |
| `MTL` | Metric Temporal Logic，度量时序逻辑 | 给时序算子增加数值时间约束 | PGFuzz 使用的性质形式 |
| `MITL` | Metric Interval Temporal Logic，度量区间时序逻辑 | MTL 的非奇异区间子类，可翻译为时间布希自动机 | TAFuzz 当前性质与监视器接口 |
| `TBA` | Timed Büchi Automaton，时间布希自动机 | 状态中含时钟，接受运行需无限次访问接受集合 | 无界性质不能靠一次接受命中判定 |
| `AP` | Atomic Proposition，原子命题 | 可在某个观测点判真假的最小性质条件 | 决定插桩字段和下一步变异目标 |
| `lasso` | lasso-shaped trace，套索形轨迹 | `prefix · cycle^ω`，即有限前缀后接无限重复循环 | 把无限接受目标变成可搜索的有限循环证据 |
| `accepting fixpoint` | accepting fixpoint，接受不动点 | 从中仍有可能无限次回到接受位置的符号状态域 | 状态离开该域后不应继续奖励“接受进度” |
| `zone` | clock zone，时钟区 | 一组满足差分时钟约束的估值，用 DBM 表示 | 图可达不等于时间约束可行，必须保留时钟区 |
| `DBM` | Difference Bound Matrix，差分约束矩阵 | 规范化保存 `x-y≤c` 一类时钟约束 | 用规范化签名比较时间自动机循环状态 |
| `PTA` | Priced Timed Automaton，赋价时间自动机 | 在时间自动机上计算到目标的剩余代价 | 比 PGFuzz 单点公式距离保留更多历史与时间语义 |
| `SITL` | Software In The Loop，软件在环仿真 | 在普通主机运行真实飞控程序和仿真环境 | 本方案首个生产验证环境，不等于真实硬件 |
| `oracle` | test oracle，测试判定器 | 决定一条执行是否构成性质违反或问题候选 | 有限违反与无界套索必须使用不同状态值 |
| `JSONL` | JSON Lines，逐行 JSON 文件 | 每行一条逐前缀记录，适合在线追加 | 原型与 TAMonitor 现有输出的连接格式 |

机器状态值解释：

- `NO_PROGRESS`：未观察到可信剩余代价下降。
- `PREFIX_PROGRESS`：精确剩余代价下降，种子应提高优先级。
- `ACCEPTING_FRONTIER`：到达接受位置或接受前沿，但无界性质仍未判定违反。
- `LASSO_CANDIDATE`：一次执行内出现正时间接受循环候选。
- `REPLAY_CONFIRMED_LASSO`：至少两个独立重放复现相同定时循环；仅作高优先级模糊测试证据。
- `FINITE_VIOLATION`：仅限有限前缀语义且监视器给出终止否定结论。
- `INCONCLUSIVE`：证据不足；不表示性质满足。

## 3. 为什么“否定性质 + 布希条件”不能直接解决有限在线判定

设原性质为：

```text
φ = G(request -> F response)
```

其含义是“每次请求最终都会响应”。否定为：

```text
¬φ = F(request & G !response)
```

否定自动机要接受一条无限轨迹，必须看到某次请求后永久不再响应。有限时刻 `t` 只能看到“目前还没有响应”，未来仍可能响应，所以只进入一次接受位置不能完成判定。

MoniTAal 的论文把在线三值语义定义得很清楚：只有当一个有限前缀的**所有**无限扩展都满足性质时才返回真，所有无限扩展都违反时才返回假，否则返回未知；论文还明确指出，无界响应 `G(a -> F b)` 的任何有限前缀都只能得到未知。[Monitoring Timed Properties (Revisited), pp. 5–7](https://arxiv.org/pdf/2206.14590)

但是模糊测试不要求证明所有行为，只需要找到一个具体的坏行为见证。若已经得到：

```text
prefix · cycle · cycle
```

而且：

- `cycle` 回到相同的被测系统状态；
- 否定自动机也回到相同位置和时钟状态域；
- 循环中访问接受集合；
- 循环持续正时间；
- 相同输入和时间安排可再次复现；

那么就有很强的工程证据说明这个有限执行可以延伸成 `prefix · cycle^ω`。这就是 LTL-Fuzzer 的活性反例策略，而不是普通在线监视器的一次接受判断。[LTL-Fuzzer 论文第 3 页](https://arxiv.org/pdf/2109.02312)

## 4. LTL-Fuzzer 论文方法与公开代码逐项对应

证据版本：GitHub 当前 `main` 与本地冻结版本的关键文件内容一致，本地提交为 `716ac301fa3a8ea39814bc80eeebba49c19c1378`。GitHub 仓库为 [ltlfuzzer/LTL-Fuzzer](https://github.com/ltlfuzzer/LTL-Fuzzer)。

### 4.1 性质与 AP 位置

论文先把自然语言要求人工写成 LTL，再为每个 AP 创建三元组：源码位置、AP 名称、判真谓词。论文示例的这一步由作者人工完成，约 20 分钟；它没有实现从一般 C/C++ 程序自动提取完整性质。[论文第 2 页](https://arxiv.org/pdf/2109.02312)

对 TAFuzz 的启示：性质提取、AP 源码绑定和当前实现是否满足性质必须分开。现有 `benchmark/PGFuzz_MTL51` 可以当历史性质种子和绑定材料，不能自动升级为当前 ArduPilot 规范。

### 4.2 生成否定自动机

论文描述的是把 `¬φ` 交给 Spot 生成布希自动机。公开代码中的 `Automata::set_formula()` 只是解析并翻译传入字符串，并不会在函数内部自动加否定：[automata.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/716ac301fa3a8ea39814bc80eeebba49c19c1378/src/automata/automata.cc#L255-L291)。

因此实际使用时必须保证环境变量 `LTL` 或 `ltl.txt` 中保存的是要被接受的公式，若目标是找 `φ` 的反例，就应传入规范化的 `¬φ`。这个边界在新的接口中应做成显式字段，不能靠调用者记忆。

### 4.3 事件和程序状态插桩

论文描述两个模块：

1. 事件生成器在 AP 谓词成立处生成事件；
2. 监视器收集事件、运行否定自动机，并在活性检查时记录程序状态。

公开 LLVM 插桩代码在 AP 对应源码位置调用 `proposition_handler()` 和 `state_handler()`：[afl-llvm-pass.so.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/716ac301fa3a8ea39814bc80eeebba49c19c1378/AFLGo/llvm_mode/afl-llvm-pass.so.cc#L521-L617)。状态处理器把选择的内存字节哈希后放入 `state_vector`，随后查找重复哈希。

### 4.4 自动机轨迹与输入前缀

`model_check_events()` 从初始状态开始逐事件推进，并保存每一步状态号和接受标志：[automata.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/716ac301fa3a8ea39814bc80eeebba49c19c1378/src/automata/automata.cc#L311-L347)。

`extract_prefix_automata_path()` 保存自动机状态序列，以及让程序走到该状态的最短已见输入前缀；`PathWriter`/`PathsStore` 把它们放入共享内存或前缀文件。下一轮模糊测试会固定此前前缀，只变异后缀，从而按顺序实现多个事件，而不只是接近一个代码位置。

### 4.5 下一事件与目标位置

主循环执行以下过程：[LTLFuzzer.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/716ac301fa3a8ea39814bc80eeebba49c19c1378/src/LTLFuzzer.cc#L125-L195)

```text
选择已见自动机路径和输入前缀
  -> 从最后自动机状态选择一条转换
  -> 从转换条件选一个 AP 事件
  -> 把事件映射到源码位置或直接输入
  -> 固定前缀并调用 AFLGo 接近该位置
  -> 执行后收集更长的自动机路径和新前缀
```

`AFLGo` 是面向目标位置的定向灰盒模糊测试器。它的控制流图距离只负责“如何到达下一 AP 位置”；跨 AP 的顺序由自动机路径和固定输入前缀负责。

### 4.6 活性反例判定

论文定义的核心是：到达否定自动机接受状态后，若程序状态在以后再次相同，并且中间事件满足返回该接受状态的循环条件，就把轨迹视为可扩展套索；论文还要求重放循环排除状态抽象导致的伪报告。[论文第 3、5 页](https://arxiv.org/pdf/2109.02312)

公开代码中的 `check_acceptance()` 会：

1. 找到接受状态；
2. 查找最后自动机状态的直接自环条件；
3. 在后续 `state_vector` 中寻找相同程序状态哈希；
4. 检查重复区间的事件是否满足该自环；
5. 抛出 `a counterexample!` 作为测试判定信号。

对应实现见 [CodeBean.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/716ac301fa3a8ea39814bc80eeebba49c19c1378/src/instrumentation/CodeBean.cc#L247-L332)。

## 5. 不能直接复制 LTL-Fuzzer 公开实现的地方

### 5.1 论文中的前缀适应度没有在冻结公开代码中实现

论文给出的前缀适应度同时考虑：已经走过的自动机路径长度、到接受状态的最短距离、输入前缀长度。[论文第 4 页](https://arxiv.org/pdf/2109.02312)

但当前 GitHub `main` 的 `compute_prefix_fitness()` 直接返回 `1.0`，路径和前缀最终是等权随机选择：[PathStore.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/main/src/PathStore.cc#L194-L220)。所以不能把公开代码说成已经完整实现论文适应度。

本方案使用 TAMonitor 已有的精确 PTA `cost-to-go` 代替这部分，不再靠自动机无权图步数。

### 5.2 公开代码主要处理接受自环，不覆盖一般接受 SCC

`SCC` 是 Strongly Connected Component，强连通分量；分量内任意状态都可到达彼此。一般布希接受循环可能是 `q1 -> q2 -> q3 -> q1`，不一定存在一条 `q1 -> q1` 的直接边。

LTL-Fuzzer 的 `check_acceptance()` 只从当前状态的出边中寻找 `e.second == last_state`。本次原型以“组合状态再次出现”为闭环条件，中间允许经过任意多条自动机边，因此能覆盖一般接受 SCC。

### 5.3 状态快照实现不适合 ArduPilot

论文说实际工具会保存寄存器和可寻址内存的抽象。公开 LLVM 辅助代码实际枚举全局变量和调试信息中的栈分配对象；更重要的是，它用 `getAlignment()` 返回的**对齐量**作为复制字节数：[ltl-instr-func.cc](https://github.com/ltlfuzzer/LTL-Fuzzer/blob/716ac301fa3a8ea39814bc80eeebba49c19c1378/AFLGo/llvm_mode/ltl-instr-func.cc#L59-L97)。对齐量不是对象真实大小。

即使修正大小，ArduPilot 整体状态仍包含：

- 单调系统时间；
- 调度器和通信计数器；
- 传感器与物理仿真浮点噪声；
- 与当前性质无关的大量控制器内部状态。

全量哈希会造成大量假阴性；过粗哈希又会造成假阳性。因此应由性质绑定生成显式状态投影，并保存原始值供重放诊断。

### 5.4 LTL-Fuzzer 的确定性假设在 SITL 中只能近似成立

论文推导套索时假设反应式系统确定：相同状态施加相同输入会产生相同执行。ArduPilot SITL 在固定随机种子、初始状态、参数快照和输入相对时间后可以提高可重复性，但操作系统调度和仿真噪声仍可能造成差异。

因此本方案把单次套索设为 `LASSO_CANDIDATE`，只有独立干净重放一致才升级为 `REPLAY_CONFIRMED_LASSO`，而且仍不称为形式化证明。

## 6. 相对 PGFuzz 的改进方案

方案名称：`Time-divergent Accepting-Lasso Guidance`，中文为“时间发散接受套索引导”，下文简称 TALG。`time-divergent` 表示循环重复时物理时间持续增长，不允许用零时间循环伪造无限行为。

### 6.1 总体数据流

```text
MITL 性质 φ
  -> 显式构造否定性质 ¬φ
  -> MightyL/MoniTAal 生成负性质 TBA
  -> 计算接受不动点与 PTA 剩余代价
  -> 当前前缀得到 next_edge + clock-zone + cost-to-go
  -> next_edge 的 AP 标签映射到 ArduPilot 状态/输入绑定
  -> 静态相关性 + PGFuzz 动态影响证据排序变异
  -> SITL 执行并由插桩输出 AP、源时间、性质状态投影
  -> 套索检测、独立重放确认、种子重新排序
```

### 6.2 为什么比 PGFuzz 的公式距离多一层信息

PGFuzz 计算命题距离和全局距离，选择能让当前命题更接近违反的输入；其算法随机选择相关输入和值，若某个输入值改善命题距离就记住并复用。[PGFuzz 论文第 7–8 页](https://www.cs.purdue.edu/homes/dxu/pubs/NDSS21_PGFuzz.pdf)

单点数值距离不一定知道以下历史：

- 触发事件是否已经发生；
- 当前欠缺的是哪一个时序阶段；
- 某个 AP 现在变真会前进还是回退；
- 进入接受状态后能否形成可重复的时间循环。

TALG 的反馈是分层的：

1. `cost_progress`：精确 PTA 剩余代价是否下降；
2. `next_edge_key`：下一条可行时间自动机边；
3. `ACCEPTING_FRONTIER`：是否进入否定性质的接受前沿；
4. `LASSO_CANDIDATE`：是否在正时间后回到同一组合状态且循环访问接受集合；
5. `REPLAY_CONFIRMED_LASSO`：独立重放是否复现同一状态和相对时间序列。

PGFuzz 的命题距离仍可保留，用于在同一 AP 内选择数值变异方向；自动机层负责决定“当前应该推进哪个 AP”。两者是组合而不是互相替代。

### 6.3 种子选择

当前原型为每个逐前缀记录计算确定性的 `priority_score`：

```text
精确剩余代价下降             + 20 + min(20, 下降量)
离接受前沿越近               + 10 / (1 + 剩余代价)
进入接受前沿                 + 30
形成一次正时间接受套索       + 50
跨独立重放确认               + 30
```

然后按每个种子的最高分生成 `seed_ranking`。这些权重只是调度默认值，不具备逻辑语义，正式实验必须通过消融实验比较，不能把分数解释成违反概率。

只有 `domain_status=complete` 且 `aggregate.exact=true` 的 PTA 记录能参与距离、目标边和变异选择；超时、不完整或近似记录会关闭相关引导，防止伪精确反馈。

### 6.4 变异选择

每个 `next_edge_key` 先解析其 AP 条件，再从以下来源合并候选输入：

1. 当前性质的 AP 源码绑定和影响锥，给出 `static_relevance`；
2. PGFuzz 动态分析适配器的已观测输入—状态影响，给出 `dynamic_effect` 与 `dynamic_status`；
3. 自动机边谓词要求的真假方向，给出 `direction_match`；
4. 输入执行后是否能可靠恢复，给出 `reversible`。

原型的候选分数为：

```text
0.40 * static_relevance
+ 0.35 * dynamic_effect * dynamic_status_factor
+ 0.15 * direction_match
+ 0.10 * reversible
```

其中 `CONFIRMED_EFFECT` 的状态因子为 1，`INCONCLUSIVE` 为 0.35，`NO_OBSERVED_EFFECT` 为 0。这里的 `INCONCLUSIVE` 表示动态试验不能确认影响，不等于不存在依赖，所以仍保留较低权重。

### 6.5 时间套索判据

一次 `LASSO_CANDIDATE` 必须满足：

```text
起点组合键 == 终点组合键
组合键 = TBA 位置 + 性质时钟区签名 + 性质状态投影摘要
循环区间至少访问一次接受位置
循环区间所有状态都在 accepting fixpoint 内
飞控源时间增量 >= min_cycle_time_us > 0
```

跨重放签名还包含：

- 循环内每个自动机位置和时钟区；
- 每个性质状态投影摘要；
- 事件与自动机边编号；
- 按 `cycle_time_quantum_us` 离散后的相对飞控时间。

这比 LTL-Fuzzer 的直接接受自环更一般，也比“某个循环出现 `m` 次”更严格；但因为状态投影和时间量化仍是抽象，所以仍只输出测试证据状态。

## 7. 已实现原型与实际验证

### 7.1 文件

- `src/StaticAnalysis/runtime/mitl_buchi_guidance/tafuzz_buchi_guidance/model.py`：输入契约、精确有理数代价、性质状态投影摘要。
- `src/StaticAnalysis/runtime/mitl_buchi_guidance/tafuzz_buchi_guidance/engine.py`：多边套索、正时间与接受不动点检查、重放确认、种子和变异排序。
- `src/StaticAnalysis/runtime/mitl_buchi_guidance/tafuzz_buchi_guidance/cli.py`：读取配置、运行时 JSONL 和现有 PTA JSONL，写出逐前缀反馈与汇总。
- `src/StaticAnalysis/runtime/mitl_buchi_guidance/tests/test_engine.py`：12 个自动测试。
- `src/StaticAnalysis/runtime/mitl_buchi_guidance/examples/`：明确标成合成绑定的端到端示例。

### 7.2 已验证行为

自动测试覆盖：

1. 单次接受命中不会变成套索；
2. 正时间、含接受位置的多边循环能成为候选；
3. 零时间循环被拒绝；
4. 两个独立重放的相同循环得到重放确认；
5. 不同相对时间安排不会错误合并；
6. 无界性质的有限 `NEGATIVE` 不会升级为有限违反；
7. 有限前缀性质的终止否定可以输出有限违反；
8. 不完整或不精确 PTA 结果不能产生引导；
9. 绝对时钟没有进入性质状态投影摘要；
10. 当前 TAMonitor 的真实输出可以原样解析。

真实 PTA 文件 `test/TARV/results/pta_prefix_mighty_cost3_z3_20260712-042251/pta_prefix_costs.jsonl` 的前五个精确代价 `8 -> 5 -> 4 -> 2 -> 0` 已由测试读取并断言，无需转换旧格式。

执行命令：

```bash
cd src/StaticAnalysis/runtime/mitl_buchi_guidance
python3 -m unittest discover -s tests -v

python3 mitl_buchi_guidance.py \
  --config examples/config.json \
  --runtime-prefixes examples/runtime_prefixes.jsonl \
  --pta-prefix-costs \
    ../../../../test/TARV/results/pta_prefix_mighty_cost3_z3_20260712-042251/pta_prefix_costs.jsonl \
  --output-dir /tmp/tafuzz-buchi-example
```

观察结果：12/12 测试通过；端到端示例输出 6 个前缀、2 个套索记录、两个套索均在两个独立运行中得到相同签名，种子最高阶段为 `REPLAY_CONFIRMED_LASSO`。

## 8. ArduPilot 生产接入方案

### M1：扩展 TAMonitor 的只读逐前缀导出

当前 `MonitorRunner.cpp` 在无限词模式使用 MoniTAal 的布希接受不动点，但明确禁止现有有限词 `PrefixRuntimeObserver`。不要把有限词 Goal 锁存逻辑硬套到无限词；增加独立 `BuchiPrefixObserver`，逐事件只读导出：

```text
property_id
prefix_index
source_time_us
negative_automaton_location
canonical_property_clock_zone
accepting
accepting_fixpoint
next_edge
cost_to_accepting_frontier
```

时钟区导出前必须移除 MoniTAal 的全局观测时钟，只保留性质时钟。已有 `PrefixRuntimeObserver` 移除 observer clock 的实现可以复用投影方式，但不能复用有限词终止语义。

### M2：生成性质驱动的 ArduPilot 插桩计划

输入：

- 性质 IR；
- AP 绑定；
- 当前 ArduPilot 源码索引；
- AP 影响锥；
- 单位、坐标系和有效性条件。

输出 `observation_plan.json`，每个 AP 明确：

```text
在哪个当前源码位置采样
读取哪个字段或调用哪个无副作用访问器
如何判定 AP 真值
使用什么飞控源时钟
哪些字段进入性质状态投影
连续值如何量化以及原始值如何保留
```

插桩应调用固定接口，例如：

```cpp
TAFUZZ_EMIT(property_id, ap_id, AP_HAL::micros64(), ap_value, state_view);
```

`AP_HAL::micros64()` 是 ArduPilot 硬件抽象层的 64 位微秒时钟；这里用于把 AP 事件、状态快照和输入动作放在同一飞控时间域。不要用地面控制脚本的接收墙钟替代内部事件时间。

建议只在以下位置插桩：

1. AP 真值可能改变的已绑定写点或稳定读取点；
2. 模式切换、故障状态切换等离散边界；
3. 输入实际应用与恢复确认点。

不要像 LTL-Fuzzer 公开实现那样枚举所有全局和局部变量。状态投影只含性质项、当前控制阶段以及静态影响分析确认会改变循环可重复性的少量字段。浮点状态同时保存原值和带滞回的量化桶，重放审核使用原值解释抽象是否过粗。

### M3：把自动机边连接到变异器

每次从 TAMonitor 得到 `next_edge` 后：

1. 解析边上的 AP 合取/析取及所需真假方向；
2. 用当前 `fuzzable_frontier` 和 `mutation_recipes` 找到可控输入；
3. 合并 `pgfuzz_adapter` 的动态影响结果；
4. 优先选择已确认影响、方向匹配、可恢复的输入；
5. 如果当前边仅依赖时间流逝，按 PTA 给出的 delay witness 等待，而不是随机改变输入；
6. 运行一次变异，记录输入应用确认、飞控源时间和恢复结果。

### M4：套索重放确认

发现 `LASSO_CANDIDATE` 后暂停普通队列扩展，对同一种子执行至少两次干净重放：

- 重新启动 SITL；
- 恢复冻结参数和任务初态；
- 固定仿真随机种子与环境配置；
- 按相同相对飞控时间重放输入序列；
- 比较事件、TBA 状态、性质状态投影和时间桶；
- 保存最小不一致前缀。

只有相同循环签名跨重放出现时输出 `REPLAY_CONFIRMED_LASSO`。如果只有一次出现，保留为普通队列种子；如果重放分歧，降级为 `INCONCLUSIVE` 并保存分歧原因。

### M5：测试判定器分层

| 性质类别 | 自动判定输出 | 是否需要套索 |
|---|---|---|
| 状态安全或有界响应 | `FINITE_VIOLATION` | 否，监视器终止否定已足够 |
| 无界响应/活性 | `LASSO_CANDIDATE` | 是 |
| 无界响应且跨重放一致 | `REPLAY_CONFIRMED_LASSO` | 是，但仍是测试证据 |
| 监视器或插桩证据缺失 | `INCONCLUSIVE` | 不得推断满足 |

## 9. 一个具体例子

假设性质为：

```text
每次 request 出现后，最终出现 response。
φ = G(request -> F response)
```

否定自动机接受：

```text
某次 request 后永久没有 response。
¬φ = F(request & G !response)
```

一次执行可能得到：

```text
前缀 0: q0，LOITER，cost=8
前缀 1: q1，request 已发生，cost=5
前缀 2: q2，进入接受前沿，cost=2
前缀 3: q3，无 response，cost=0
前缀 8: 再次回到 q3 + 同一性质时钟区 + 同一飞控状态投影
```

如果前缀 3 到 8 经过了正飞控时间、一直处于接受不动点、没有 response，而且第二次干净重放再次出现相同循环，TALG 将该种子升为 `REPLAY_CONFIRMED_LASSO`。

如果性质改成“5 秒内出现 response”，那么 5 秒截止时监视器就可以直接输出 `FINITE_VIOLATION`，不必等待套索。这是有界未来与无界未来在测试判定器中的根本区别。

## 10. 如何证明它确实优于 PGFuzz，而不是只换名字

生产闭环完成后，用相同性质、输入目录、初始种子和墙钟预算比较以下四组：

1. `PGFuzz-distance`：命题/全局距离；
2. `LTL-Fuzzer-style`：无时间自动机路径 + 接受自环；
3. `TALG-no-replay`：时间自动机剩余代价 + 一次套索；
4. `TALG-full`：时间自动机剩余代价 + 多边接受套索 + 独立重放 + 静动态变异排序。

主要指标：

- 首次到达接受前沿的时间；
- 首次套索候选时间；
- 首次可重放套索时间；
- 每小时独立可重放问题候选数；
- 套索候选重放失败率；
- 插桩和逐前缀求解的时间开销；
- 相同预算下的 AP/自动机边覆盖；
- 变异后 `cost_progress>0` 的比例。

这组对照能分别回答：自动机历史是否有用、时钟区是否有用、一般 SCC 是否优于直接自环、重放是否降低伪候选、静动态输入排序是否减少无效试验。在真实数据出来以前，只能把“优于 PGFuzz”称为待验证假设。

## 11. 最终可行性判断

| 项目 | 当前判断 | 证据 |
|---|---|---|
| 否定性质 TBA 用于模糊测试引导 | 可行 | LTL-Fuzzer 论文/代码与 MoniTAal 接受不动点 |
| 一次接受命中判断无界违反 | 不可行 | 布希接受要求无限次访问；无界响应有限前缀不可判定 |
| 套索作为无界问题候选 | 可行 | LTL-Fuzzer 状态循环方法；本原型已通过正/负测试 |
| 时间发散、多边 SCC、跨重放扩展 | 离线核心可行 | 12/12 测试与端到端示例通过 |
| 直接读取现有 PTA 代价 | 可行 | 真实 `8 -> 5 -> 4 -> 2 -> 0` 文件已解析断言 |
| 完整 ArduPilot SITL 在线闭环 | 尚未验证 | 缺 TAMonitor 无限词逐前缀导出和性质相关源码插桩 |
| 形式化证明性质违反 | 不作为目标 | 本方案明确只做模糊测试引导与可重放问题发现 |

最合适的落地方式不是把 PGFuzz 的监视器替换成一个“到达接受状态即报错”的布希自动机，而是保留 PGFuzz 的输入影响学习，把 TAMonitor 的时间自动机剩余代价作为第一层反馈，再以时间发散接受套索和独立重放作为第二层反馈。这样既确实扩展了 PGFuzz 的局部数值距离，又没有把有限仿真包装成无界性质的完整判定。
