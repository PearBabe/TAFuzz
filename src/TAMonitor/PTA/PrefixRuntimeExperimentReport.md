# 在线 Prefix Cost-to-Go 正确性与性能报告

## 环境与可复现命令

- 日期：2026-07-12 CST
- 环境：WSL2 Linux 6.18.33.2，AMD Ryzen 9 9950X，16 cores / 32 threads，
  可用内存 15 GiB。
- 编译器：GCC 11.4；Z3 4.8.12；精确 DBM 为 Pardibaal。

核心命令：

```text
TAMonitorPTARomeoDifferential --seed 0x524f4d454f44424d --cases 20000
TAMonitorPTARomeoOriginalTests
TAMonitorPTAPrefixBenchmark --iterations 10000 --output <result-dir>
TAMonitor ... --pta-prefix-cost --pta-prefix-benchmark-iterations 2000
```

原始结果：

- `test/TARV/results/pta_prefix_mighty_z3_20260712-042225/`
- `test/TARV/results/pta_prefix_mighty_cost3_z3_20260712-042251/`
- `test/TARV/results/romeo_dbm_differential_potential_20260712-043922/`
- `test/TARV/results/pta_prefix_benchmark_20260712-044336/`
- `test/TARV/results/pta_prefix_mighty_replay_20260712-044614/`

## 正确性结论

- 手算 WTA 固定 trace 得到 `[10,7,5,3,0]`，delay `[0,5,3,1,0]`；每步
  独立 Z3 path encoding 均证明 `cost<expected` UNSAT、`cost=expected` SAT。
- MightyPPL `!(F [5,10] p1)` 固定 trace 的 symbolic/concrete 结果均为
  `[5,5,4,2,0]`；初始两条边 cost=3 后为 `[8,5,4,2,0]`。
- 最后一个 prefix 同时保留 Goal 与非 Goal 两个 live candidates，first-hit aggregate
  为 0，`next_edge/next_arc=null`。
- 小维整数枚举 200 例、Z3/Roméo-derived 随机 20,000 例、直接原 Roméo
  `DBM::min` 安全语料 1,000 例均为零差异。
- 全部 next edge/arc/delay/reset/successor witness 均通过 DBM membership 与
  Bellman 等式回放。

## 性能结果

同一 synthetic mixed snapshot、预热后每组 10,000 次；单位为微秒：

| Domain | Backend | P50 | P95 | P99 | Max | QPS |
|---|---|---:|---:|---:|---:|---:|
| point | fast path | 5 | 6 | 15 | 107 | 185113 |
| interval | Z3 | 575 | 780 | 968 | 1970 | 1674 |
| interval | Roméo DBM | 164 | 255 | 313 | 826 | 5468 |
| interval | crosscheck | 768 | 946 | 1191 | 2566 | 1282 |
| Federation(2 DBM) | Z3 | 1112 | 1376 | 1887 | 5970 | 872 |
| Federation(2 DBM) | Roméo DBM | 355 | 581 | 770 | 3506 | 2545 |
| Federation(2 DBM) | crosscheck | 1554 | 2085 | 2703 | 5682 | 618 |

Roméo-derived 相对 Z3 的 P95 加速：interval 约 `3.06x`，双 DBM Federation
约 `2.37x`。完整 benchmark 47.99 s，峰值 RSS 102296 KiB；mixed precompute
7733 us。

实际 MightyPPL snapshot 对五个 prefix 各重放 2,000 次，共 10,000 次：

```text
P50=6 us, P95=8 us, P99=21 us, max=282 us, mismatch=0
```

10,000 条结果的 JSON 内存编码 P50/P95/P99=`3/5/8 us`；两个 JSONL 共约
27 MiB，统一写盘 47219 us。I/O 在 monitor 完成后执行，不进入 fuzzing 热路径。

## 优化与 fuzzing 适用性

当前实现已经按顺序启用：

1. singleton point fast path；
2. location → reachable-node/piece 索引；
3. DBM `is_intersecting` 粗过滤后才精确 intersection；
4. 热路径只保存结构化结果，JSON 编码/写盘后置；
5. thread-local Z3 context，避免每个候选重建 context。

point 和实际 Mighty replay 的 P95 分别为 6 us、8 us，远低于同步 fuzzing 的
1 ms 门槛；Roméo interval/Federation P95 也分别为 255 us、581 us。因此：

- concrete/point 与小 Federation：适合每个 fuzzing iteration 同步排序；
- 一般 symbolic Federation：默认推荐 `romeo-dbm`；
- `crosscheck` 用于测试/离线审计，不建议同步热路径；
- Z3 双 DBM P95=1.376 ms，适合异步批量或低频复核，不应作为高频默认。

未加入生产 LRU/cache：重复 point 查询已经只有约 6--8 us，而缓存需要 canonical
DBM 序列化、锁和复制完整 candidates/witness，可能增加延迟和内存。若将来大型 TA
的 candidate filtering 成为瓶颈，优先增加线程局部、容量受限的 fingerprint cache，
key 必须包含 target、location、canonical DBM、snapshot identity、backend 与查询
资源契约；命中结果仍需保持 cost、attained、IDs 和 witness 完全一致。

## 最终工程验收

- `TAMonitorPTA` 生产库、Affine/Prefix/Roméo differential/benchmark 测试及本次
  修改的 main/options/runner/runtime 适配文件均以 `-Werror` 重建通过。
- 常规 CTest：10/10 passed；默认无 PTA、pure backward、普通 mixed 与 prefix
  integration 均验证 verdict、退出码、原四个文件和 workbook sheets 未回归。
- ASan+UBSan 核心：6/6 passed；默认/pure/mixed/prefix 端到端 integration 3/3
  passed（`detect_leaks=0`, `halt_on_error=1`）。
- sanitizer 首轮发现 MightyPPL 既有 `TAwithBDDEdges::intersection` 在 erase 后
  解引用 `std::set` iterator；改成先复制 LocationId 再 erase 后，三套端到端测试
  全部通过。该修复不改变 TA 构造语义。
- 原 Roméo source oracle 是只读测试目标，常规 1,000 例通过；其完整源对象在
  UBSan 下会因未链接的 unused `LinearExpression` RTTI 阻止 gc-link，因此不作为
  production sanitizer target。Roméo-derived 生产后端已在 sanitizer differential
  中覆盖并通过。
