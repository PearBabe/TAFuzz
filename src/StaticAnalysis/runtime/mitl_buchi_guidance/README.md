# MITL 布希套索引导原型

本目录实现一个只用于模糊测试调度的最小原型。它不会把有限仿真包装成形式化证明。

## 术语与判断边界

- `MITL`：Metric Interval Temporal Logic，度量区间时序逻辑；本项目中是带时间区间约束的性质语言，决定自动机边上的时钟约束。
- `Büchi automaton`：布希自动机；识别无限轨迹，接受条件是无限次访问接受集合。仅到达一次接受位置不能证明无界性质违反。
- `lasso-shaped trace`：套索形轨迹；有限前缀后接可重复循环，写作 `prefix · cycle^ω`。原型在有限执行里只寻找循环候选及重放证据。
- `accepting fixpoint`：接受不动点；仍有可能无限次回到接受位置的符号状态集合。字段 `accepting_fixpoint=true` 表示当前状态没有离开该可行域。
- `zone signature`：时钟区签名；时间自动机位置上的规范化时钟约束摘要。`PROPERTY_CLOCKS_ONLY` 要求已移除绝对观测时钟，否则循环永远无法匹配。
- `state projection`：状态投影；只保留本性质相关的飞控字段。它避免仿真时钟、日志计数器和无关噪声破坏循环匹配，也意味着结果是抽象证据而非完整状态相等证明。
- `PTA`：Priced Timed Automaton，赋价时间自动机；当前 TAMonitor 输出到目标区域的精确 `cost-to-go`（剩余代价），本原型直接读取现有 `pta_prefix_costs.jsonl`。
- `JSONL`：JSON Lines，每行一条 JSON 记录；用于逐前缀追加反馈。

## 状态值

- `NO_PROGRESS`：本前缀没有产生可证明的剩余代价下降。
- `PREFIX_PROGRESS`：到接受前沿的精确剩余代价下降；可提高该种子的调度优先级。
- `ACCEPTING_FRONTIER`：已进入接受位置或剩余代价为零；对无界性质仍不等于违反。
- `LASSO_CANDIDATE`：同一“自动机位置 + 性质时钟区 + 性质相关飞控状态”再次出现，循环包含接受位置且飞控时间正增长。
- `REPLAY_CONFIRMED_LASSO`：同一种子在至少两个干净重放中产生相同循环签名。它是高优先级问题候选，仍不是对所有无限行为的证明。
- `FINITE_VIOLATION`：仅允许 `property_kind=FINITE_PREFIX` 且有限监视器已经给出终止否定结论时输出。
- `INCONCLUSIVE`：证据不足；不能理解成性质满足。

## 输入契约

`runtime_prefixes.jsonl` 的每条记录必须包含：

- `run_id`、`seed_id`、`prefix_index`；
- 使用飞控源时钟得到的单调 `time_us`；
- `automaton_location`、移除全局时钟后的 `zone_signature`；
- `accepting` 与 `accepting_fixpoint`；
- `property_state`，并由配置中的 `state_projection_fields` 明确选择参与哈希的字段；
- 可选的 `event_label`、`transition_id`、`monitor_verdict`。

`cycle_time_quantum_us` 把循环内的相对飞控时间离散到指定微秒粒度；跨重放确认要求事件、自动机状态、性质状态以及相对时间桶均一致。它只吸收已声明粒度内的调度抖动，不能使用墙钟时间代替飞控源时钟。

配置中的 `edge_mutations` 把 TAMonitor 的 `next_edge` 映射到候选输入。候选排序综合：静态相关性、PGFuzz 动态影响证据、变异方向是否匹配以及能否恢复。这个映射必须来自当前性质的原子命题绑定或影响分析，示例文件中的映射明确标为合成示例，不能当作 ArduPilot 事实。

只有 `domain_status=complete` 且 `aggregate.exact=true` 的 PTA 记录可以产生剩余代价、下一边或变异建议；超时、不完整和近似结果一律不参与引导。

## 运行

```bash
cd src/StaticAnalysis/runtime/mitl_buchi_guidance
python3 mitl_buchi_guidance.py \
  --config examples/config.json \
  --runtime-prefixes examples/runtime_prefixes.jsonl \
  --output-dir /tmp/tafuzz-buchi-example
python3 -m unittest discover -s tests -v
```

若要同时使用当前 PTA 输出，追加：

```bash
--pta-prefix-costs \
  ../../../../test/TARV/results/pta_prefix_mighty_cost3_z3_20260712-042251/pta_prefix_costs.jsonl
```

输出：

- `guidance.jsonl`：逐前缀阶段、证据状态、剩余代价、下一条边与候选变异；
- `summary.json`：套索候选、跨重放确认和种子优先级汇总。

## 还未接通的生产接口

当前原型已经复用现有 PTA 逐前缀文件并验证套索/重放逻辑，但 TAMonitor 的无限词路径目前不输出本原型所需的逐前缀时钟区签名；ArduPilot 也尚未生成性质相关的内部状态投影。因此现阶段可确认“算法和离线反馈契约可运行”，不能声称“完整 SITL 活性性质闭环已经运行”。生产接入必须补两个窄接口：TAMonitor 导出负性质自动机的逐前缀接受不动点状态，ArduPilot 插桩导出由性质绑定明确列出的字段。
