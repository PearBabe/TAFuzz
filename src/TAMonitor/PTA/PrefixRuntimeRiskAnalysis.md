# 在线前缀剩余代价实现风险审计

本文档记录在线 prefix cost-to-go、符号 Federation 查询、witness 回放和
Roméo-derived DBM 线性目标优化器在正式编码前的风险审计。结论只适用于
finite-word、flatten、Goal-first-hit 的现有 mixed solver 语义。

## 1. 基线与依赖

- 当前 `ctest --test-dir tool/MightyPPL/build -R '^TAMonitorPTA'` 为 5/5 通过。
- Z3 为 4.8.12.0，编译器为 GCC 11.4.0。
- 已构建 Pardibaal 源 checkout 为
  `22ecff40d8c397cf658b1b6fe7fe32cc05458d23`；现有 TAMonitor build flags
  仍记录旧配置 commit `1eb56e...`，正式重配后必须刷新报告中的依赖版本。
- Roméo 源为官方 3.10.12，archive SHA-256：
  `8f04ecdc141c622a700fe065ca567c4cebbf6d94b58c2820e967d3c4467e0050`。
- 当前 worktree 已有 `.codex/PROJECT_STATE.md` 与 `.codex/SESSION_LOG.md`
  用户工作，禁止重置或回退。

## 2. 必须保持的数学不变量

对 runtime 状态集合

\[
S=\bigcup_k \{l_k\}\times F_k
\]

和 mixed finite piece \(P_i=(n_i,Z_i,W_i)\)，在线标量定义为

\[
V_\exists(S)
=-\max_{k,D\in F_k,i}\sup_{v\in D\cap Z_i}W_i(v).
\]

必须保持：

1. 候选 `D intersect Z_i` 可以重叠；候选集合表示上包络 `max W`，不能称为
   互斥 DBM 分区。
2. runtime symbolic/concrete 状态都比 PTA DBM 多最后一个绝对时间 observer；
   只能在副本上删除最后一维，不能删除参考钟 0 或修改 monitor 原状态。
3. 对严格交集域 \(I\)，先在拓扑闭包 \(\bar I\) 上求最大值：

   \[
   \sup_I W=\max_{\bar I}W.
   \]

   再在原域检查 `I and W=q` 是否可满足。
4. `domain optimizer actual`、当前 delay 是否取得、suffix 是否取得和总代价
   是否取得是四个不同事实，不能共用一个布尔值。
5. `MixedUnboundedRegion` 表示一个实际点的 suffix 已经是 `-infinity`；finite
   affine 函数在整个 runtime Federation 上无界仅表示存在语义的聚合为
   `-infinity`，两者必须使用不同原因码。
6. incomplete forward/backward/query 不允许输出当前局部最优值；除完整
   `-infinity` certificate 外只能返回 `Unknown`。
7. 任意 attained witness 必须满足 source delay、fire zone、reset、entry zone、
   successor piece 和 Bellman 等式。

## 3. Z3 严格域风险

独立探针已复现 Z3 4.8.12 的行为：

```text
closed  0 <= x <= 1 : upper vector = (0,1,0)
strict  0 <= x < 1  : upper vector = (0,0,0)   # 错误
unbounded x >= 0    : upper vector = (1,0,0)
```

因此生产实现必须：

1. 构造 `topological_closure(I)`；
2. 只对闭包调用 `Optimize::maximize`；
3. 使用 `Z3_optimize_get_upper_as_vector`，长度必须为 3；
4. 使用 numeral 的 numerator/denominator 精确解析任意精度有理数；
5. closure 下只接受 `c=0`；`a>0` 为正无穷，`a=0` 的 `b` 为有限值；
6. 普通 QF_LRA 证明 `closure and W>b` UNSAT；
7. 分别用 `closure and W=b`、`I and W=b` 提取 limit/actual valuation；
8. 任一 Optimize/Solver UNKNOWN、timeout 或解析异常都传播为 `Unknown`。

不能使用 Optimize 返回的 model 作为最优 valuation。

## 4. Runtime 状态机与 Goal 风险

现有 finite monitor 在构造时把初态与 `Pre*(Goal)` 相交；事件后先 delay、
检查 invariant、执行匹配 edge，再次与 `Pre*(Goal)` 相交。在线适配采用只读
状态 accessor 和 callback，不修改该顺序。

prefix 状态机固定为：

1. `prefix_index=0` 查询构造完成后的初态；
2. 每次真实调用 `input()` 后查询一次；
3. overall verdict 终止后仍与 trace 行数对齐，但输出
   `not_evaluated_monitor_terminal`，不重复旧 cost 或计时；
4. target side 首次出现 accepting state 时置独立 `goal_hit` latch，输出 cost 0、
   delay 0、空 edge/arc；之后输出 `goal_already_hit`；
5. target states 为空且未命中 Goal 时输出 `NoLiveState` 和精确 `+infinity`；
6. Goal 前的实际 runtime domain 若不完全属于 exact forward support，则视为
   `DomainMismatch`，不能静默忽略 outside 部分。

只在 `--pta-prefix-cost` 下把 mixed 预计算提前到 monitor 之前。默认、pure
backward 和 mixed-without-prefix 保持现有调用顺序与产物集合。

## 5. Witness 回放风险

现有 facet metadata 对一般 attained witness 不总是充分。flat-delay objective
允许使用内部 delay，而 piece 仍可能记录 closure facet。因此实现采用：

1. `ZERO`、普通 facet 先尝试闭式 delay；
2. 用当前/limit valuation、arc fire/entry DBM、reset 和 successor piece 精确回放；
3. 回放失败时，用共享 QF_LRA 对单变量 delay 求可行解并验证 Bellman 等式；
4. strict limit 使用 closure 约束，明确 `delay_attained=false`；
5. `unbounded_delay=true` 不构造有限 delay。

回放需要 automaton reset/guard、location rate 和 edge cost。现有
`MixedAnalysisSnapshot::Impl` 未保存这些数据，因此新增独立
`PrefixCostAnalyzer`，构造时绑定 `WeightedAutomatonView`、`CostModel` 和
`MixedAnalysisSnapshot` 的不可变生命周期；不改变既有 point-query API。

## 6. Roméo-derived 优化器风险与决定

Roméo `DBM::min/max` 是 difference-constraint graph 上的
successive-shortest-path/min-cost-transshipment：objective 变为 node
supply/demand，DBM bounds 为弧成本，Bellman-Ford 更新 potentials，随后沿
最短路增广并维护 residual reverse arcs。

禁止逐行移植以下实现细节：

- VLA；
- `int32/int64 cvalue`；
- 饱和到 `{-1,0,1}` 的 `Avalue::epsilon`；
- 被注释掉的 unbounded 预检查；
- 依赖 infinity valuation 的末尾启发式无界判断；
- 忽略 `LinearExpression` denominator 的入口。

迁移版只接受 canonical、nonempty、reference clock=0、整数 gradient 的
Pardibaal DBM，在拓扑闭包上用 `BigInt/BigRational` 求精确值和 limit
valuation。无界由有限弧 residual graph 上供需不可路由显式报告。

严格域的权威 `attained` 首版复用共享 QF_LRA equality checker；迁移版可以
保存任意精度 lexicographic epsilon 作为诊断，但不得单独作为证明。Z3 与
Roméo crosscheck 比较 value、infinity、attained 和各自 optimizer 合法性，
不要求非唯一 optimizer valuation 字面相等。

Roméo 是 CeCILL。新模块采用数学算法重写、独立类型和独立代码，不链接 Roméo
production binary，并记录版本、hash 和来源。TAFuzz 根许可边界不清晰；本地
研究实现不因此阻塞，但对外分发前必须做许可审查，文档不得宣称已取得法律结论。

Pardibaal bound 仍为 `int32_t` 且上游算术缺少 overflow guard。BigInt optimizer
只能避免优化阶段溢出，不能修复已经溢出的输入 DBM；构造测试必须避开或显式
拒绝上游不可表示范围。

## 7. 失败状态

| 条件 | 对外状态 | 是否返回 witness |
| --- | --- | --- |
| mixed snapshot 不完整 | `Unknown` | 否 |
| prefix deadline/max-regions | `IncompleteQuery` | 否 |
| Goal 前 runtime 域不在 forward support | `DomainMismatch` | 否 |
| target 无 live state | `NoLiveState/+infinity` | 否 |
| 已命中 Goal | `GoalAlreadyHit/0` | goal seed，无 edge/arc |
| pointwise unbounded certificate | `NegativeInfinity/pointwise` | certificate witness |
| affine 对 runtime 域无界 | `NegativeInfinity/domain_aggregate` | 无有限 optimizer |
| 可达但无 suffix piece | `PositiveInfinity` | 否 |
| optimizer 或 replay UNKNOWN | `Unknown` | 否 |

## 8. 验证 oracle

- 手算单时钟 WTA 逐前缀 `10,7,5,3,0`，每步验证 Bellman 等式。
- MightyPPL `!(F [5,10] p1)` 固定 trace 得到 `5,5,4,2,0`；初始边 cost 3
  后得到 `8,5,4,2,0`。
- singleton symbolic/concrete 与现有 point query 完全一致。
- closed/strict interval、diagonal、unbounded、多 states/Federation。
- 小维度 bounded DBM 枚举、原 Roméo、安全范围 corpus、Z3、迁移后端三方比较。
- 固定种子至少 20,000 个 dimension 2--12 differential cases。
- witness 必须逐条回放，不只比较 scalar。
- incomplete、Outside、NoLiveState、`+/-infinity` 独立测试。

## 9. 性能测量

callback 只记录内存结果；JSON 编码和写盘在 monitor 完成后执行。分别记录
extraction、projection、filter、intersection、optimizer、replay、core total 和
serialization。`monitor_ms` 包含 callback，不能作为纯查询时间。

独立 benchmark 在同一 snapshot/domain/candidate list 上预热后执行至少 10,000
次，分别测 point fast path、Z3、Roméo、crosscheck、interval Federation 和真实
MightyPPL replay，报告 P50/P95/P99/max、QPS、RSS 和 mismatch。同步 fuzzing
门槛是 point core-query P95 <= 1 ms。

只缓存 exact finite/infinity/outside；timeout/Unknown 不缓存。cache key 必须包含
snapshot identity、backend、location 和 canonical DBM bounds。

## 10. 进入编码阶段的结论

审计结论：允许进入编码阶段，但必须按以下顺序执行：

1. 共享 exact QF_LRA/closure extrema 与 Z3 reference backend；
2. Federation 候选下包络和 witness materializer；
3. 核心单元测试通过；
4. finite monitor callback、CLI、JSONL 和固定 trace；
5. Roméo-derived closure optimizer 与 crosscheck；
6. 性能基线后再实现索引、快路径和缓存。

上述顺序不得颠倒，且任何不完整状态不得冒充最优结果。
