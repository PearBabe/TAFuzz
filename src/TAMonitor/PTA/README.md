# TAMonitor Priced-DBM 与 Exact Mixed 分析

本目录独立实现 Parrot–Lime 2020 的后向 symbolic optimal reachability，
并增加 Roméo 风格的 exact mixed 模式：先构造 Goal 截断的可达 Zone
Graph，再仅沿图中已记录的真实 arc 反向传播 priced pieces。核心内部
沿用论文符号 `W=-V`，其中 `V` 是当前 `(location, valuation)` 到 accepting goal
的最小剩余成本；公共查询和 JSON 输出均转回直接的 `V`。完整数学契约与论文
勘误见 [AlgorithmProof.md](AlgorithmProof.md)。
已执行的 C++/MightyPPL/Romeo 结果见
[ExperimentReport.md](ExperimentReport.md)。

## 使用边界

- 只支持 `--word finite --build-mode flatten`；不把 finite reachability 冒充
  Büchi 最优成本。
- 默认分析 MightyPPL 生成的 negative TA，以 accepting locations 为 Goal。
- 默认每个 location 的 `rate=1`、每条 edge 的 `cost=0`，即最短违规剩余时间。
- `backward` 是沿原 TA 入边展开的 FIFO label-correcting worklist；
  `mixed` 先用 exact DBM Post 构图，再用 Node-scoped FIFO delta 传播。
  两者都不是 Dijkstra。
- `mixed` 不做 extrapolation；exact forward 一般不保证终止，因此命中
  node/arc/timeout 上限后不启动后向求值，也不声称最优。
- `mixed` 的 Goal 语义是 `first_hit_terminal`：首次进入 accepting location 即
  结束 reachability cost，Goal 节点不再展开。这与 Roméo mixed 实现和违规导向
  用途一致；不应将它解释为“允许离开 Goal 后通过负成本环再返回”。
- 未传 `--pta-analysis` 时 solver 完全不运行，原 verdict、四个报告文件和三个
  workbook sheet 保持不变。

显式运行：

```bash
tool/MightyPPL/build/TAMonitor \
  --formula test/TARV/cases/smoke_f_01.mitl \
  --word finite --build-mode flatten --build-only \
  --pta-analysis backward \
  --out /tmp/tamonitor-pta
```

exact mixed：

```bash
tool/MightyPPL/build/TAMonitor \
  --formula-inline '!(F [5,10] p1)' \
  --trace test/TARV/cases/smoke_f_01.trace \
  --word finite --build-mode flatten \
  --pta-analysis mixed --pta-verify-geometry \
  --out /tmp/tamonitor-pta-mixed
```

资源参数：

```text
--pta-max-pieces <positive integer>   # 默认 1000000
--pta-max-reach-nodes <positive int>  # mixed 专用，默认 100000
--pta-max-reach-arcs <positive int>   # mixed 专用，默认 1000000
--pta-timeout-ms <nonnegative integer># 默认 300000；0 表示不限时
--pta-verify-geometry                 # backward: Pre*; mixed: Reach∩Pre* + observer
```

## Cost model

可选 XML 只覆盖默认值，edge ID 是 `source location + source 局部 ordinal`：

```xml
<pta-cost-model version="1" target="negative">
  <defaults location-rate="1" edge-cost="0"/>
  <location id="3" rate="-2"/>
  <edge source="1" ordinal="0" cost="5"/>
</pta-cost-model>
```

整数使用任意精度解析。配置中的未知 element/attribute、重复 override 和未知 ID
都会被拒绝。若任何实际 location rate 或 edge cost 为负，必须显式提供
`--pta-assume-lower-bounded`；它是用户声明的数学前提，不是程序完成了负离散环
检测。未声明时输出 `assumption_required`，不会给出伪最优值。

## 状态与输出

显式 `backward` 额外生成：

- `pta_analysis.json`：算法/依赖版本、完整 cost model、location/edge/DBM 目录、
  初始查询、完整性状态和统计；
- `pta_pieces.jsonl`：每个有限 affine piece 或 `negative_infinity` region，包含
  exact DBM、`W` 与直接 cost 形式、attained、next edge、successor piece/region
  和 zero/lower-facet/upper-facet delay witness。

`mixed` 使用 `pta_analysis.json` schema 2，并额外生成：

- `pta_reachable_nodes.jsonl`：稳定 NodeId、location、Goal 标记和 exact DBM；
- `pta_reachable_arcs.jsonl`：稳定 ArcId/EdgeId，以及每条 arc 的
  `fire_zone`/`entry_zone`/`post_zone`；
- `pta_pieces.jsonl`：每个 piece/region 额外带 reachable NodeId、next ArcId、
  successor node/piece witness。

`--pta-verify-geometry` 会在 priced snapshot 完整时，逐 location 将所有 finite
pieces 与 `negative_infinity` regions 的几何并集，和 MoniTAal 原生 Federation
`Pre*(Goal)` 做精确相等判定。mixed 模式则比较
`Support=Reach∩Pre*(Goal)`；对 rate=1/edge=0 且初始最优值为可达整数时，
还用 MoniTAal 内置不 reset observer clock 独立验证严格阈值不可达、
非严格阈值可达。它用于 correctness suite，默认关闭，以免把额外
oracle 成本混入生产 solver 的 timeout。

成本、rate、gradient 和 DBM bound 均以十进制或有理数字符串保存，避免 JSON
浮点舍入。状态含义：

- `complete`：worklist fixed point 完成，查询值精确；
- `unreachable`：fixed point 证明初态不可达 Goal；
- `unbounded_below`：精确证明初始 cost 为 `-infinity`，但提前停止的全域表不会
  标成 exact；
- `assumption_required`：signed model 缺少 lower-bound 契约；
- `incomplete_resource_limit`：timeout 或 piece 上限，禁止解释为全局最优。
- `incomplete_forward_resource_limit`：mixed 的 exact graph 未穷尽，后向阶段未启动；
- `incomplete_backward_resource_limit`：forward exact，但 priced worklist 未穷尽。

## C++ 离线接口

`BackwardPricedSolver.h` 提供：

```cpp
AnalysisSnapshot solve(const WeightedAutomatonView&, const GoalSpec&,
                       const CostModel&, const SolverOptions&);
CostToGoResult AnalysisSnapshot::query(
    LocationId, const RationalValuation&) const;
const std::vector<PricedPiece>& AnalysisSnapshot::pieces(LocationId) const;
```

`ReachableZoneGraph.h` 和 `MixedPricedSolver.h` 另外提供：

```cpp
ReachabilitySnapshot compute_reachable_zone_graph(
    const WeightedAutomatonView&, const GoalSpec&, const ReachabilityOptions&);
MixedAnalysisSnapshot solve_mixed(
    const WeightedAutomatonView&, const ReachabilitySnapshot&,
    const CostModel&, const SolverOptions&);
MixedCostToGoResult MixedAnalysisSnapshot::query(
    LocationId, const RationalValuation&) const;
```

mixed query 显式区分 `reachable` / `outside_reachable_domain` / `unknown`，
不会把“不在真实前向域”伪装成“可达但到 Goal 的 cost 为 `+infinity`”。

snapshot 不可变，保留稳定 `EdgeId`、piece/region ID 与 derivation witness，供未来
fuzzing 只读查表。本轮不实现在线 fuzzing 排序器，也不改变 runtime monitor 的
state/verdict 更新。

## 构建与验证

```bash
cmake -S tool/MightyPPL -B tool/MightyPPL/build
cmake --build tool/MightyPPL/build --target \
  TAMonitorPTATests TAMonitorPTAReachabilityTests TAMonitorPTAMixedTests TAMonitor -j2
ctest --test-dir tool/MightyPPL/build -R '^TAMonitorPTA' --output-on-failure
```

生产 solver 的 proof-critical dominance 使用 Z3 QF_LRA，因此 TAMonitor 二进制
运行时依赖 Z3 shared library；当前验证版本会写入 `pta_analysis.json`。Romeo
artifact 的运行方法见 [experiments/README.md](experiments/README.md)，它只复现
论文原 artifact，不能替代本模块的 C++ correctness tests。
