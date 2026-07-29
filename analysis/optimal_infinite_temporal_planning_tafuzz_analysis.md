# Tollund et al. 2024 算法分析与 TAFuzz 匹配评估

本文分析论文：

```text
Optimal Infinite Temporal Planning: Cyclic Plans for Priced Timed Automata
Rasmus G. Tollund, Nicklas S. Johansen, Kristian O. Nielsen,
Alvaro Torralba, Kim G. Larsen
ICAPS 2024
```

本地 PDF：

```text
C:/Users/PC-123/Zotero/storage/69GL4Y85/Tollund 等 - 2024 - Optimal infinite temporal planning Cyclic plans for priced timed automata.pdf
```

本文重点回答三个问题：

1. 论文到底在求什么问题。
2. `S-lambda-D` 算法为什么成立、怎么运行。
3. 它和当前 TAFuzz/TAMonitor 的匹配程度、实现路线和风险。

## 1. 一句话结论

这篇论文不是普通“最短路”或“到达目标最小 cost”，而是解决：

```text
在带时间约束、带 cost、带 reward 的系统里，
找一个可以无限重复执行的循环计划，
让长期平均 cost / reward 最小。
```

论文的核心算法叫：

```text
symbolic lambda-deduction, 简写 S-lambda-D
```

它的聪明点是：

```text
ratio = Cost / Reward
```

这个目标本来不是可加的，不能直接像 Dijkstra 那样一段一段累加。论文把它转成：

```text
w_lambda = Cost - lambda * Reward
```

这样每条边、每段 delay 都有一个可加权重。只要在当前 `lambda` 下找到一个负权重 cycle，就说明发现了一个 ratio 更小的 cycle。重复改进 `lambda`，直到再也找不到负 cycle，就证明当前 cycle 最优。

白话版：

```text
先找到一个还不错的循环方案，把它的 cost/reward 比值叫 lambda。
然后问：有没有循环比 lambda 更划算？
如果有，它在 Cost - lambda * Reward 这个打分下会变成负数。
找到它，更新 lambda。
找不到了，说明没有更划算的循环了。
```

## 2. 论文模型：CRTA 是什么

论文从 timed automata 出发。

普通 timed automaton 有：

| 元素 | 白话 |
|---|---|
| location | 系统当前阶段，比如草坪短、草坪长、正在快割草 |
| clock | 计时器，记录某件事发生后过了多久 |
| guard | 边上的时间条件，比如 `x >= 2` |
| reset | 走边时把某个 clock 清零 |
| invariant | 在 location 里必须一直满足的时间条件 |

论文再给它加两套价格：

```text
c = cost
r = reward
```

于是得到 Cost-Reward Timed Automaton，简称 CRTA。

CRTA 里 cost/reward 有两种来源：

1. 在 location 里等一段时间：按 rate 累积。
2. 走一条 discrete edge：一次性加 edge cost/reward。

如果在 location `l` 等 `delta` 时间：

```text
cost += c(l) * delta
reward += r(l) * delta
```

如果走 edge `e`：

```text
cost += c(e)
reward += r(e)
```

所以一条有限执行 `pi` 的比值是：

```text
Ratio(pi) = Cost(pi) / Reward(pi)
```

无限执行 `Pi` 的比值用有限前缀的极限下确界描述：

```text
Ratio(Pi) = liminf Ratio(Pi_n)
```

论文要求系统满足几个常见限制：

| 限制 | 为什么要有 |
|---|---|
| no Zeno cycles | 不能无限执行却只过了有限时间 |
| reward-divergent | 无限运行必须积累无限 reward，否则 ratio 没意义 |
| bounded clocks | clock 值有上界，保证抽象状态有限 |

## 3. 为什么答案是 cycle

论文研究的是 infinite plan。无限计划不能真的完整列出来，只能用一个可重复结构表示：

```text
prefix + cycle + cycle + cycle + ...
```

长期来看，prefix 的一次性代价会被无限重复的 cycle 淹没，所以关键是找：

```text
ratio 最低的可重复 cycle
```

这和 “mean payoff / minimum cycle ratio” 很像。

例如一个生产系统：

```text
cycle A: 每 10 秒生产 2 个单位，花费 30
ratio = 30 / 2 = 15

cycle B: 每 20 秒生产 5 个单位，花费 60
ratio = 60 / 5 = 12
```

如果 reward 表示产量，cost 表示耗能，那么 B 的长期单位产出成本更低。

论文的 lawnmower 例子也是这个结构：割草机要无限维持草坪状态。单次走快割或慢割不是重点，重点是长期循环后 “cost / lawn-quality reward” 最小。

## 4. 难点：ratio 不能直接累加

如果目标是普通最小 cost：

```text
path cost = edge1 cost + edge2 cost + ...
```

可以用很多图搜索算法。

但 ratio 不行：

```text
Cost / Reward
```

两个局部片段的 ratio 谁更好，依赖后面怎么接。

论文举的思想可以白话化为：

```text
片段 A: cost/reward = 1/1
片段 B: cost/reward = 2/3
```

单看 B 好一些，因为 `2/3 < 1`。但如果后面必须接一个只加 cost、不加 reward 的片段，最后谁好可能变化。ratio 不是简单可加量，所以不能只保留每个状态下“当前 ratio 最小”的路径。

论文没有维护完整 Pareto front，而是用 lambda 转换把 ratio 问题变成单权重问题。

## 5. lambda-deduction 推导

假设当前最好的 cycle 是 `C_lambda`：

```text
lambda = Ratio(C_lambda)
       = Cost(C_lambda) / Reward(C_lambda)
```

现在想判断另一个 cycle `x` 是否更好：

```text
Ratio(x) < lambda
```

展开：

```text
Cost(x) / Reward(x) < lambda
```

因为 reward 为正：

```text
Cost(x) < lambda * Reward(x)
```

移到一边：

```text
Cost(x) - lambda * Reward(x) < 0
```

定义：

```text
w_lambda(x) = Cost(x) - lambda * Reward(x)
```

于是：

```text
w_lambda(x) < 0
等价于
Ratio(x) < lambda
```

这就是论文 Proposition 3 的核心。

白话：

```text
如果我当前的心理价位是 lambda，
那么每拿到 1 点 reward，最多愿意花 lambda 点 cost。
实际花费 cost 减去“心理可接受花费 lambda * reward”。
如果结果是负数，说明这条 cycle 比当前心理价位更划算。
```

### 5.1 数字例子

当前 cycle：

```text
Cost = 10
Reward = 20
lambda = 10 / 20 = 0.5
```

候选 cycle A：

```text
Cost = 9
Reward = 30
Ratio = 0.3
w_lambda = 9 - 0.5 * 30 = -6
```

`w_lambda` 为负，所以 A 更好。

候选 cycle B：

```text
Cost = 9
Reward = 10
Ratio = 0.9
w_lambda = 9 - 0.5 * 10 = 4
```

`w_lambda` 为正，所以 B 不如当前方案。

## 6. Algorithm 1：抽象 lambda-deduction

论文 Algorithm 1 的逻辑是：

```text
input:
  一个 bounded 且 strongly reward-divergent 的 CRTA A

output:
  ratio-optimal concrete cycle，或者 NO CYCLE

1. 如果 A 没有 cycle，返回 NO CYCLE。
2. 任取一个 cycle C_lambda。
3. lambda = Ratio(C_lambda)。
4. while A_lambda 中存在 negative-weight simple discrete cycle C:
       lambda = Ratio(C)
       C_lambda = C
5. 返回 C_lambda。
```

这里 `A_lambda` 是把原来的 CRTA 改成 single-priced TA：

```text
w_lambda(a) = c(a) - lambda * r(a)
```

对 location 和 edge 都这样做。

### 6.1 为什么终止

论文依赖 corner-point abstraction 的结论：

```text
bounded timed automata 的整数角点抽象里，
simple discrete cycles 数量有限，
并且存在 ratio-optimal 的 discrete cycle。
```

每次找到负 cycle，就说明：

```text
new lambda < old lambda
```

也就是严格变好。有限个候选 cycle 不可能无限严格下降，所以 Algorithm 1 终止。

### 6.2 为什么正确

如果还有更好的 cycle：

```text
Ratio(C) < lambda
```

那它在 `A_lambda` 中就是负权重 cycle：

```text
w_lambda(C) < 0
```

如果已经找不到负 cycle，就等价于找不到 ratio 小于当前 lambda 的 cycle。当前 cycle 因此最优。

## 7. 为什么不能只用 corner-point abstraction

corner-point abstraction 会把 dense time 离散化到有限图上。理论上好用，但工程上有大问题：

```text
状态数随 clock 数量和时间常数快速膨胀。
```

如果最大时间常数从 10 放大到 1000，离散角点图会变大很多。

这对 TAFuzz 很关键：MITL 公式里常见 `F [0,900] b`、`G [0,1000] p` 这种大边界。如果用角点全枚举，很容易把搜索拖垮。

论文的 S-lambda-D 就是为了解决这个问题：不用显式枚举所有角点，而是用 zone/priced zone 做符号搜索。

## 8. priced zone：普通 zone 加一个价格平面

普通 zone 表示一堆 clock valuation：

```text
1 <= x <= 3
y <= 2
x - y >= 0
```

它不是一个点，而是一片区域。

priced zone 在 zone 上再加一个仿射价格函数：

```text
w(u) = a1 * u(x1) + a2 * u(x2) + ... + b
```

含义：

```text
在这个 zone 内，到达 valuation u 的最低 lambda-deducted weight 是 w(u)。
```

一个 symbolic state 是：

```text
S = (location, zone, price_function)
```

论文用 DBM 表示 zone，用 affine function 表示价格。

白话：

```text
普通 zone 说：“我可能在这一片时间区域里。”
priced zone 说：“我可能在这一片时间区域里，并且到每个点的最低代价大概是一张斜着的平面。”
```

## 9. priced successor：delay 和 edge 怎么推进

S-lambda-D 的搜索节点是 priced symbolic state。推进有两种动作：

```text
Post_e(S): 走一条 discrete edge
Post_epsilon(S): 让时间流逝
```

### 9.1 edge successor

走 edge 时做普通 TA 操作：

1. 和 guard 相交。
2. 加 edge weight。
3. reset 对应 clocks。
4. 进入目标 location。
5. 和目标 invariant 相交。
6. 更新 price function。

### 9.2 delay successor

delay 更微妙。假设在当前 location 等待，location 的 lambda-deducted rate 是：

```text
r = c(location) - lambda * reward(location)
```

当前 priced zone 的价格函数沿着“所有 clock 一起增加”的方向有一个斜率，论文叫 `q`。

直觉：

```text
如果等待本身比较便宜，就尽量等久一点。
如果等待本身比较贵，就尽量少等一点。
```

论文写成：

```text
if r <= q: delay as much as possible
if r >= q: delay the least possible
```

delay 之后可能不是一个 zone，而是拆成多个 priced zones。论文图 2 展示了绿色 zone delay 后拆出红色和蓝色 successor。

## 10. symbolic cycle 为什么难

在 concrete graph 里，cycle 很简单：

```text
从同一个 concrete state 出发，又回到同一个 concrete state。
```

但 symbolic path 只有 zone：

```text
S1 = (l, Z1, w1)
...
Sn = (l, Zn, wn)
```

即使 `Z1` 和 `Zn` 有交集，也不一定存在一个具体点 `u`，能从 `(l,u)` 出发又回到 `(l,u)`。

还有一个更隐蔽的问题：

```text
priced zone 只记录到达某个 end valuation 的最低价格，
但不记录这条最低价格路径来自哪个 start valuation。
```

所以不能看到 zone 重叠就说有 cycle。论文必须额外做“从 symbolic path 中抽出 concrete cycle”的优化问题。

## 11. Theorem 7：不用考虑绕同一个 symbolic cycle 多圈

给定一个 symbolic cycle `Pi`，理论上 concrete cycle 可能绕它多圈：

```text
Pi
Pi^2
Pi^3
...
```

论文 Theorem 7 说：

```text
多圈里的最优 concrete cycle，
ratio 不会比一圈里的最优 concrete cycle 更好。
```

直觉是 convexity：

1. zone 是凸的。
2. 多圈执行可以分成若干段。
3. 把这些段的 valuation 和 delay 做凸组合，可以压回一圈里。
4. ratio 也保持对应组合，不会凭空变得更优。

这很重要，因为它把“无限多个 Pi^k”压成：

```text
只检查 Pi 的一圈。
```

Corollary 8 对 single weight 情况给出类似结论：

```text
一圈有 weight w
等价于 k 圈有 weight k*w
```

## 12. 如何从 symbolic path 抽出 best concrete cycle

论文用 linear-fractional programming。

核心变量是每个动作发生的 timestamp：

```text
t_i = action alpha_i 发生时距离 cycle 起点的时间
t_{n+1} = cycle 总时长
```

zone 中的 clock constraint 要翻译成 timestamp constraint。

例如在第 `i` 个位置有：

```text
x <= n
```

要找到 clock `x` 最近一次 reset 的位置 `j`。

如果 reset 在本轮 cycle 内，而且 `j <= i`：

```text
t_i - t_j <= n
```

如果 reset 发生在上一轮，也就是 `j > i`：

```text
t_i + t_{n+1} - t_j <= n
```

有了这些线性约束，就能优化：

```text
minimize Cost / Reward
```

如果最优 ratio 小于当前 `lambda`，就等价于存在 negative-weight concrete cycle。

白话：

```text
symbolic path 给的是“走哪几条边”的骨架；
linear-fractional program 负责给每一步选择具体时间点，
让这一圈的 cost/reward 最小。
```

## 13. Algorithm 2：S-lambda-D 如何找负 cycle

Algorithm 2 是 Algorithm 1 中 “找 A_lambda 的负 cycle” 的符号实现。

它的输入是：

```text
A_lambda = (L, l0, E, I, w_lambda)
```

输出是：

```text
negative weight simple discrete cycle
或者 NO CYCLE
```

主过程：

```text
Waiting = {initial symbolic state}
Parent[initial] = NIL

while Waiting not empty:
    S = EXTRACT-MIN(Waiting)

    for every edge e:
        for every successor S' in Post_epsilon(Post_e(S)):
            if no previously discovered state dominates S':
                Parent[S'] = (S, e)
                insert S' into Waiting

                if NEG-CYCLE(parent path ending in S') finds cycle:
                    return cycle

return NO CYCLE
```

### 13.1 Waiting 的优先级

论文说优先级不影响正确性和终止性，但影响效率。

推荐选择：

```text
包含最小 weight valuation 的 state 先扩展。
```

白话：

```text
越便宜的区域越可能藏着负 cycle，
所以先搜便宜区域。
```

### 13.2 Parent 指针

每个新 state 记录：

```text
Parent[S'] = (S, action)
```

这样当生成新 state 时，可以沿 Parent 往回找 suffix：

```text
S_k -> ... -> S'
```

如果某个 suffix 是 negative-weight symbolic cycle，就返回它抽出的 best concrete cycle。

### 13.3 NEG-CYCLE 子过程

`NEG-CYCLE` 的逻辑是：

```text
给定当前 parent chain 的一个 suffix。
如果这个 suffix 能抽出 negative concrete cycle：
    返回 best concrete cycle
否则继续把 suffix 往前扩一格
如果到 NIL 还没有：
    返回 NO CYCLE
```

关键检测不是简单判断 location/zone 是否相同，而是用第 12 节的优化问题抽具体 cycle。

## 14. domination 剪枝

如果只按 `(location, zone)` 去重，会出错。

原因：

```text
同一个 location + zone，
可能第一次到达很贵，第二次到达很便宜。
便宜的那次可能通向最优 cycle。
```

论文 Proposition 9 专门说明：最优 concrete cycle 可能藏在 non-simple symbolic cycle 里，也就是 symbolic state 会重复出现。

所以论文定义 domination：

```text
S = (l, Z, w) dominates S' = (l', Z', w')
当且仅当：
1. l = l'
2. Z 包含 Z'
3. 对所有 u in Z'，w(u) <= w'(u)
```

白话：

```text
S 覆盖的时间区域更大，
而且在 S' 的每个具体点上，S 的到达代价都不更高。
那 S' 没必要继续搜。
```

这比普通 zone inclusion 更强，因为它还比较 price function。

## 15. Algorithm 2 为什么终止

论文 Lemma 11 的证明比较技术化，可以抓住两个分支：

### 15.1 如果 price 不断下降

如果 priced symbolic state 的价格一直变得更便宜，最终会低于一个阈值 `w_min`。

论文定义的 `w_min` 可以理解为：

```text
在 corner-point 抽象里所有负 lambda edge 权重的总和。
```

如果一条 path 的 weight 比 `w_min` 还低，它必然重复用了某些负边，因此里面必然含有 negative cycle。

也就是：

```text
无限变便宜 -> 必然暴露负 cycle -> 算法返回
```

### 15.2 如果没有 negative cycle

bounded timed automata 只有有限种 unpriced zones。

再结合 domination 是 well-quasi-order：

```text
不会无限生成互不支配的新 state。
```

所以最终 `Waiting` 会空，算法返回 `NO CYCLE`。

## 16. Theorem 12：完整 S-lambda-D 的正确性

完整算法是：

```text
Algorithm 1 的 lambda-deduction
    +
Algorithm 2 的 symbolic negative-cycle search
```

论文 Theorem 12 说明它：

| 性质 | 含义 |
|---|---|
| termination | 会停 |
| soundness | 返回的 cycle 确实可达、确实是 negative/improving |
| completeness | 如果存在 negative cycle，就能找到 |
| optimality | 最终返回 ratio-optimal concrete cycle |

## 17. 实验结论

论文比较：

| 方法 | 思路 |
|---|---|
| CP-MCR | 构造完整 corner-point concrete graph，再跑 minimum cycle ratio |
| S-lambda-D | 用 priced zone on-the-fly 搜索 negative cycle |

实验域：

| 域 | 含义 |
|---|---|
| Surveillance | 多 agent 周期性巡检地点 |
| Job Scheduling | 周期性生产/机器调度 |
| Volunteer | 志愿者维护冰箱补给，同时兼顾工作 |

主要结论：

1. 在 job 和 surveillance 域，S-lambda-D 通常明显更快、状态更少。
2. S-lambda-D anytime 行为好，常常很快给出一个可用但尚未证明最优的 cycle。
3. 当 clock 常数整体放大时，CP-MCR 受影响很大，因为离散角点图变大；S-lambda-D 对大时间常数更稳。
4. Volunteer 域里 CP-MCR 有时更好，原因包括 S-lambda-D 每次 lambda 迭代没有复用已探索状态，以及该域 zone 符号表示不够划算。

这给 TAFuzz 的启发是：

```text
如果公式里时间边界很大，priced-zone search 更有希望；
如果 automaton 很小、clock 常数也小，直接图搜索或启发式可能更简单更快。
```

## 18. 和当前 TAFuzz 的匹配程度

当前 TAFuzz/TAMonitor 主要链路：

```text
MITL formula phi
-> MightyPPL parser / NNF / BDD-labelled TA
-> TAMonitor 展开 BDD edge label 为 bits:...
-> MoniTAal positive monitor for phi
-> MoniTAal negative monitor for !phi
-> finite/infinite 三值 verdict
-> steps.csv / summary.csv / metadata.json / results.xlsx
```

关键代码入口：

| 能力 | 文件 |
|---|---|
| TAMonitor 选项、结果结构 | `/home/lqq/project/TAFuzz/src/TAMonitor/TAMonitor.h` |
| 构造 `phi` 和 `!phi` 两个 automata | `/home/lqq/project/TAFuzz/src/TAMonitor/TAMonitorMightyAdapter.cpp` |
| finite/infinite monitor runner | `/home/lqq/project/TAFuzz/src/TAMonitor/MonitorRunner.cpp` |
| MoniTAal symbolic state / zone | `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal/state.h` |
| MoniTAal DBM/federation 操作 | `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal/symbolic_state_base.*` |
| 普通 TA location/edge | `/home/lqq/project/TAFuzz/tool/MoniTAal/src/monitaal/TA.h` |
| BDD edge TA 与 projection | `/home/lqq/project/TAFuzz/tool/MightyPPL/TAwithBDDEdges.*` |

### 18.1 强匹配点

这篇论文和 TAFuzz 的研究方向高度相关，尤其是已有的 `CoPTA-Fuzz` 设想：

```text
把 MITL violation automaton 提升成 priced timed automaton，
用 cost-to-violation 作为 fuzzing guidance。
```

匹配点：

| 论文能力 | TAFuzz 可用位置 |
|---|---|
| timed automata | MightyPPL 已能从 MITL 构造 TA |
| symbolic zones | MoniTAal 已用 DBM/federation 表示 symbolic states |
| infinite behavior | TAMonitor 已支持 `--word infinite` |
| negative automaton | TAMonitor 已构造 `!phi` |
| anytime improving | 很适合作为 fuzzing seed scheduler |
| large clock constants robustness | MITL fuzzing 经常有大时间窗口 |

### 18.2 中等匹配点

论文的 `ratio-optimal cycle` 可以映射到 fuzzing 的长期搜索策略：

```text
cost   = 生成/变异 timed trace 的代价
reward = 接近 violation、覆盖新 zone、进入 negative accepting frontier 的收益
```

例如：

```text
Cost:
  delay shift 幅度
  AP bit flip 数量
  插入/删除事件数量
  走已高频 edge 的惩罚

Reward:
  到达 !phi automaton 的 accepting frontier
  新 location / new zone bucket
  接近时间边界
  触发 pending obligation
```

这样 S-lambda-D 不一定直接“证明违反”，但可以找：

```text
单位变异代价下，最稳定推进 violation/coverage 的循环策略。
```

### 18.3 不匹配点

这篇论文不能直接塞进当前 TAMonitor，原因很明确：

| 差异 | 影响 |
|---|---|
| 论文输入是 CRTA，TAFuzz 当前只有普通 TA/TBA | 需要新增 cost/reward annotation |
| 论文做 planning/synthesis，TAMonitor 做 runtime verification | 不能替代 verdict，只能做 guidance |
| 论文假设 action 可控，真实 SUT 行为未必可控 | 对真实程序 fuzzing 要通过输入变异间接控制 trace |
| 论文要求 bounded/reward-divergent/no-Zeno | TAFuzz 需要 horizon、reward 设计和合法性检查 |
| 论文要 priced zones，MoniTAal 目前只有 unpriced federation | 需要新增 priced symbolic layer |
| 论文要 linear-fractional programming | 当前仓库没有 LP/LFP solver |
| 当前 BDD label 展开可能指数爆炸 | exact S-lambda-D 最好与 BDD-native 或 lazy valuation 结合 |

## 19. 可实现性分级

### 19.1 v1：启发式 GuidanceScorer，高可实现

建议先实现：

```text
graph distance + guard slack + label hamming distance + boundary bonus
```

它不声称 S-lambda-D 最优性，但能快速服务 fuzzing。

输入：

```text
当前 trace prefix
negative automaton 当前 state estimate
```

输出：

```text
violation_cost
best_next_label
best_delay
energy
```

优点：

1. 可直接复用 TAMonitor 的 positive/negative automata。
2. 可复用 MoniTAal symbolic state 的 location/zone。
3. 不需要 priced zone affine function。
4. 不需要 LP solver。
5. 很适合先做 timed trace fuzzer。

推荐程度：

```text
非常高。适合作为论文原型第一阶段。
```

### 19.2 v2：有限 horizon priced-zone scorer，中等可实现

实现 priced zone，但先不做完整 ratio-optimal infinite cycle。

范围：

```text
从当前 frontier 到 accepting location 的 minimum priced reachability
```

而不是：

```text
全局 optimal infinite cycle ratio
```

这更接近已有 PTA-guided fuzzing 设计里的：

```text
cost-to-violation
```

需要新增：

| 组件 | 内容 |
|---|---|
| `PricedZone` | zone + affine cost function |
| `PricedState` | location + priced zone |
| successor | guard/intersection/reset/delay/price update |
| domination | zone inclusion + price comparison |
| search | branch-and-bound 或 A* |

推荐程度：

```text
高，但应作为 v2。实现量明显大于 v1。
```

### 19.3 v3：完整 S-lambda-D，中等偏低但有研究价值

完整复现论文算法需要：

1. CRTA cost/reward 建模。
2. lambda-deducted automaton。
3. priced zone successor。
4. symbolic negative-cycle search。
5. concrete cycle extraction 的 linear-fractional programming。
6. domination 和 termination-safe search。
7. boundedness/reward-divergence/no-Zeno 检查或保守约束。
8. 和 `!phi` Büchi/finite acceptance 的语义对齐。

这不是小改动，应该当成独立研究模块。

推荐程度：

```text
适合做高水平方法章节，但不适合直接作为下一个小功能补丁。
```

## 20. 对 TAFuzz 的推荐实现路线

推荐路线不是马上完整实现 S-lambda-D，而是三阶段走。

### 阶段 A：先做 trace-level guidance

新增概念：

```cpp
struct GuidanceScore {
    double violation_cost;
    double satisfaction_cost;
    double boundary_bonus;
    std::string best_next_label;
    uint32_t best_delay;
    double energy;
};
```

新增输出：

```text
guidance.csv
```

每个 prefix 记录：

```text
step,time,label,verdict,negative_states,violation_cost,best_next_label,best_delay,energy
```

这一步和论文的关系：

```text
把论文的 cost/reward 思想先落成 fuzzing distance，
但暂不声称 ratio-optimal。
```

### 阶段 B：导出 automaton，做 Python/C++ priced prototype

先别直接侵入 MoniTAal。

建议新增导出：

```text
tamonitor --emit-automata-json
```

JSON 包含：

```text
locations
edges
guards
resets
labels / bdd labels
accepting flags
clock names
```

然后单独写 prototype：

```text
analysis/scripts/priced_guidance_prototype.py
```

优点：

1. 实验快。
2. 不污染当前 verified TAMonitor runtime。
3. 可以先用 Python LP/scipy 或小型自写 LP 测试想法。
4. 失败也不会影响现有 verdict 语义。

### 阶段 C：实现 exact-ish S-lambda-D 子集

先选受限输入：

```text
bounded integer guards
non-strict constraints
small AP alphabet
finite exported TA
explicit labels
```

先跑小公式：

```text
F [0,2] p
G (a -> F [0,30] b)
```

验证结果：

```text
S-lambda-D cycle / guidance
vs random
vs heuristic GuidanceScorer
```

再考虑 BDD-native 和 compflatten。

## 21. 论文算法怎么用于 `G (a -> F [0,30] b)`

性质：

```text
G (a -> F [0,30] b)
```

违反条件：

```text
某次 a 之后，30 时间单位内没有 b。
```

当前 TAMonitor 会构造：

```text
positive: phi
negative: !phi
```

如果把 negative automaton 当 guidance target：

```text
reward:
  更接近 pending a obligation 超时
  进入 !phi accepting frontier

cost:
  等待时间
  插入/删除事件
  AP bit flip
```

trace prefix：

```text
0,{a}
29,{}
```

启发式 scorer 会给低 violation_cost，因为只差一点越过 30。

完整 S-lambda-D 更进一步会问：

```text
有没有一个可循环策略，
能以最低 mutation/time cost 反复制造 pending obligation 并推向 violation？
```

这对 long-running system fuzzing 很有价值。

## 22. 与现有 `CoPTA-Fuzz` 设计的关系

已有文档 `analysis/priced_timed_automata_guided_fuzzing.md` 提出：

```text
CoPTA-Fuzz = Cost-to-Violation Priced Timed Automata Guided Fuzzing
```

Tollund et al. 2024 可以作为 `CoPTA-Fuzz` 的更强理论后盾：

| CoPTA-Fuzz 需要 | 本论文提供 |
|---|---|
| cost/reward guidance 的理论语言 | CRTA 和 ratio objective |
| 大时间常数下避免角点爆炸 | priced zone symbolic search |
| anytime seed scheduling | S-lambda-D anytime improving |
| 无限运行/循环行为 | ratio-optimal cyclic plan |
| v2/v3 exact algorithm 方向 | lambda-deduction + negative-cycle search |

但要注意：

```text
CoPTA-Fuzz 的第一目标是更快找 violation；
论文第一目标是证明 ratio-optimal infinite cycle。
```

所以写论文时可以这样定位：

```text
Our v1 scorer is a practical heuristic inspired by cost-reward timed planning.
Our v2 exact scorer adapts symbolic lambda-deduction to violation-oriented priced timed automata.
```

## 23. 最大工程风险

### 23.1 priced zone 和 MoniTAal federation 的接口

MoniTAal 当前 `symbolic_state_t` 只有：

```text
location + Federation
```

没有：

```text
affine price function
```

要实现论文算法，不能只改 `StepResult` 加个字段。需要新数据结构。

### 23.2 LP/LFP solver

论文抽 concrete cycle 需要 linear-fractional programming。

可选路线：

| 路线 | 优缺点 |
|---|---|
| Python scipy prototype | 快，但依赖 Python 环境 |
| C++ GLPK / HiGHS | 工程稳，但要引入依赖 |
| 自写小型 difference constraints + fractional search | 适合受限场景，但容易不完整 |

### 23.3 BDD label 爆炸

当前 TAMonitor v1 把 BDD labels 展开成 `bits:` labels，有 `--max-valuations` 防爆。

S-lambda-D 如果也在展开后的 alphabet 上跑，AP 多时会爆。

长期更好的方向：

```text
priced search 保留 BDD guard，
只在需要比较 label mutation cost 时 lazy 求可满足 valuation。
```

这和项目里已明确 deferred 的 BDD-native runtime 有交集。

### 23.4 infinite acceptance 语义

论文找普通 CRTA cycle；TAMonitor infinite 模式用 positive/negative automata 的 Büchi/fixpoint 语义。

要严谨适配，需要定义：

```text
cycle 必须满足哪些 accepting condition？
reward 如何保证和 Büchi accepting visits 绑定？
```

简单做法：

```text
先把 accepting frontier 当 reward，
不声明完整 S-lambda-D optimality。
```

严谨做法：

```text
把 accepting condition 编进 product automaton，
类似 current infinite round-robin accepting counter，
然后在该 product CRTA 上跑 cycle-ratio search。
```

## 24. 最终匹配评分

| 维度 | 评分 | 说明 |
|---|---:|---|
| 研究方向相关性 | 9/10 | 与 PTA-guided fuzzing、cost-to-violation 高度贴合 |
| 直接可复用性 | 4/10 | 当前没有 CRTA/priced zone/LFP solver |
| 作为 v1 guidance 启发 | 9/10 | lambda/cost/reward 思想很好转成 seed energy |
| 完整算法实现难度 | 8/10 | 需要新 symbolic optimization 子系统 |
| 对项目论文价值 | 9/10 | 能把 CoPTA-Fuzz 从启发式推进到理论型方法 |
| 短期落地风险 | 中 | 不应直接承诺 optimality |
| 长期落地价值 | 高 | 适合 v2/v3 研究模块 |

## 25. 建议结论

对当前 TAFuzz 来说，这篇论文最适合作为：

```text
CoPTA-Fuzz v2/v3 的理论核心，
而不是 TAMonitor v1 的直接代码补丁。
```

最稳的落地顺序是：

1. 先实现 heuristic `GuidanceScorer`，输出 `guidance.csv`。
2. 用 `!phi` automaton 做 violation-oriented scoring。
3. 加 trace-level fuzzer，证明比 random 更快找到 violation。
4. 再实现 priced-zone minimum cost-to-violation。
5. 最后考虑完整 S-lambda-D ratio-optimal infinite cycle。

这样写论文或开题时也更自然：

```text
TAMonitor gives verdicts.
CoPTA-Fuzz adds continuous guidance.
Priced timed automata give the mathematical distance model.
S-lambda-D gives the long-term optimal cyclic planning extension.
```

