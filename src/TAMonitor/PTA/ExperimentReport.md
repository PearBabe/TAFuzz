# Parrot–Lime 2020 与 Roméo-style Mixed Priced-DBM 实验报告

本报告记录 2026-07-11 在 TAFuzz 工作区完成的可重复验证。必须区分两组实验：

1. **新 TAMonitor WTA solver correctness**：验证本目录代码、DBM 几何、成本值和
   MightyPPL 接入；
2. **原版 Romeo artifact 复现**：运行论文作者发布的预编译 Time-Petri-Net
   artifact，只复现论文实现的 forward/backward 一致性，不冒充新 solver 的测试。

## 环境

```text
OS: Linux 6.18.33.2-microsoft-standard-WSL2 x86_64
Compiler: g++ 11.4.0
CMake: 3.22.1
Z3: 4.8.12.0
Pardibaal: 1eb56e87829997d02a95e1fa80635693181245eb
```

## 新 solver correctness

主命令：

```bash
cmake -S tool/MightyPPL -B tool/MightyPPL/build
cmake --build tool/MightyPPL/build --target \
  TAMonitorPTATests TAMonitorPTAReachabilityTests TAMonitorPTAMixedTests TAMonitor -j2
ctest --test-dir tool/MightyPPL/build -R '^TAMonitorPTA' --output-on-failure
```

结果：5 个正式 PTA tests 全部通过：`TAMonitorPTATests`、
`TAMonitorPTAReachabilityTests`、`TAMonitorPTAMixedTests`、
`TAMonitorPTAIntegration` 和 `TAMonitorPTAMixedIntegration`。覆盖包括：

- Definition 5 rebase 的逐点评价不变；
- 正/零/负 edge cost，单/多 clock reset，以及 diagonal + 非零 gradient；
- lower/zero/upper 三类 time slope、严格上下界和 `attained=false` 的
  epsilon-optimal 查询；
- priced-time pieces 的 Federation 几何并集与普通 Pardibaal `past()` 精确相等；
- crossing affine functions 不被 Definition 10 错剪；
- subsumption 开/关以及同层入边存储顺序改变后，逐点 cost/attained 不变；
- `ASSUMPTION_REQUIRED`、`INCOMPLETE_RESOURCE_LIMIT`、局部/全局
  `negative_infinity` 与可重放 successor-region witness；
- 论文 Fig. 1 初始最优成本 `9`，并由独立 Z3 QF_LRA path encoding 证明
  `cost<9` 不可满足且 `cost=9` 可满足；
- 论文 Fig. 2 产生三个分片并符合代表点评价；
- 默认 rate=1/edge=0 的一边模型成本为 `3`，MoniTAal 的不重置全局
  observer-clock oracle 精确验证 `T<=2` 不可达、`T<=3` 可达；
- ASan/UBSan + `-Wall -Wextra -Wpedantic -Werror` 独立构建运行通过。

### MightyPPL/MoniTAal 实际生成 TA

以下均使用 finite word、negative TA、accepting goals、rate=1、edge=0。启用
`--pta-verify-geometry` 后，把 priced snapshot 的全部 finite pieces 和
`negative_infinity` regions，逐 location 与 MoniTAal 原生 Federation
`Pre*(Goal)` 精确比较；六例全部 `equal=true`。

| case | MITL | status | initial cost | accepted pieces | subsumed | ms |
|---|---|---|---:|---:|---:|---:|
| future | `F [0,2] p1` | complete | 0 | 5 | 17 | 11 |
| globally | `G [0,2] p1` | complete | 0 | 7 | 21 | 11 |
| until | `p1 U [1,3] p2` | complete | 0 | 7 | 39 | 15 |
| once | `O [0,2] p1` | complete | 0 | 7 | 31 | 14 |
| historically | `H [0,2] p1` | unreachable | +infinity | 0 | 0 | 5 |
| since | `p1 S [0,3] p2` | complete | 0 | 7 | 39 | 16 |

这里的 `0` 是 finite-word negative accepting 语义的结果，不是把任意运行时间
强行设为零。每个有限初始结果都带 `piece_id`、next `EdgeId` 和 delay witness。

### Exact mixed forward/backward

mixed 模式在普通 TA 上实现 Roméo 的“先可达图、后成本传播”结构，
但禁用 Roméo 默认 `kxapprox`，因此输出的 reachable DBM 是 valuation-level
exact 域。Goal 采用 `first_hit_terminal` 语义，并在 schema 2 summary 中
显式记录；下述 mixed/pure 比较使用非负成本或无 Goal 出边的模型。
新增测试覆盖：

- 两时钟 reset/diagonal/strict exact Post，Goal cutoff，one-way inclusion 与
  每条 arc 独立 fire/entry/post 域；
- Node-scoped dominance、reachable/outside/unknown query、forward/backward 分阶段
  resource status；
- 手算非零 WTA 初始成本 `14`，Z3 证明 `cost<14` UNSAT、
  `cost=14` SAT；strict 版保持 infimum `14` 且 `attained=false`；
- 可达负 rate 区域传播为精确 `-infinity`，未声明 lower-bound
  契约时返回 `assumption_required`。

MightyPPL 实际生成 TA 固定 oracle：

| MITL | mode | rate/edge | initial cost | geometry | observer |
|---|---|---|---:|---|---|
| `!(F [5,10] p1)` | mixed, negative TA | `1 / 0` | `5` | `Reach∩Pre*` equal | `T<5` 不可达，`T≤5` 可达 |
| 同上 | mixed, negative TA | 所有初始出边 cost `3` | `8` | equal | 不适用（含 edge cost） |

实际 runtime trace 构造下，该 MightyPPL TA 的初始位置有两条 valuation-label
出边；非零 edge-cost 试验对两条稳定 EdgeId 都设为 `3`，避免未加权
并行边绕过成本。

最终验证的 `ctest -R '^TAMonitorPTA'` 为 `5/5 passed`。mixed 核心还用
`-Wall -Wextra -Wpedantic -Werror` 独立重编并通过；ASan/UBSan
(`-fsanitize=address,undefined`, `detect_leaks=0`) 通过。LeakSanitizer 在当前
ptrace 执行环境会自身 fatal，因而不把该环境限制误写成 leak-free 证明。

## 原版 Romeo FORMATS 2020 artifact

归档来源及固定身份：

```text
URL: https://web.archive.org/web/20220214052637id_/http://romeo.rts-software.org/releases/FORMATS2020.tgz
SHA-256: 6045841f964a5e37fcb6354eae6999355f8e308292406ff5a09412bccd2d9a29
```

运行命令：

```bash
python3 src/TAMonitor/PTA/experiments/run_romeo_benchmarks.py \
  --suite full \
  --archive /tmp/tafuzz-formats-cache-agent/FORMATS2020-6045841f964a.tgz \
  --timeout 3600 \
  --output-dir /tmp/tafuzz-romeo-full-final
```

结果为 `9/9 passed`；每个模型均正常退出、未超时且 forward/backward cost
完全相同。时间和内存是本机观测，不用于和论文旧硬件做绝对性能断言。

| model | forward cost | backward cost | forward s | backward s | forward MB | backward MB |
|---|---:|---:|---:|---:|---:|---:|
| aircraft3 | -1140 | -1140 | 0.5 | 0.6 | 0.0 | 6.2 |
| aircraft4 | -4140 | -4140 | 2.1 | 4.5 | 30.0 | 111.7 |
| aircraft5 | -4530 | -4530 | 7.9 | 32.4 | 186.5 | 505.1 |
| aircraft6 | -4980 | -4980 | 27.9 | 206.2 | 737.6 | 1802.5 |
| scheduling2 | -1760 | -1760 | 0.8 | 0.6 | 0.0 | 12.1 |
| scheduling3 | -2560 | -2560 | 12.5 | 4.5 | 158.8 | 61.2 |
| scheduling4 | -2540 | -2540 | 141.1 | 30.9 | 1481.8 | 208.7 |
| scheduling5 | -2540 | -2540 | 815.0 | 156.5 | 5805.4 | 704.0 |
| scheduling_original | -1550 | -1550 | 37.8 | 47.0 | 765.8 | 401.5 |

Quick suite 的四个固定 oracle（aircraft3/4、scheduling2/3）也全部匹配计划中的
`-1140/-4140/-1760/-2560`。
在 mixed 完成审计中又独立重跑 quick suite，`4/4 passed`，结果保持不变。

## 默认流程回归与解释边界

不传 PTA 参数的在线 `smoke_f_01` 保持 `POSITIVE`，只生成
`steps.csv`、`summary.csv`、`metadata.json`、`results.xlsx`；workbook 仍只有
`Steps`、`Summary`、`Metadata`。显式 pure backward 只额外生成两个独立
文件；mixed 额外生成 summary/pieces/nodes/arcs 四个 PTA 文件。两者都不向
原四个产物增加字段或 sheet。

本实现不声称解决论文未给出的一般负离散环检测。signed weight 必须由用户声明
统一 lower bound；资源截断和缺失前提都输出不完整状态。实现只处理 finite
reachability，本轮没有实现 fuzzing 排序器，也没有把 Romeo 的 Petri-net mixed
forward/backward 结果解释为新 MoniTAal WTA solver 的运行结果。
