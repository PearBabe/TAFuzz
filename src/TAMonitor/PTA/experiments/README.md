# 文件功能：说明 FORMATS 2020 Romeo 基准复现方法及报告边界

本工作区 2026-07-11 的 full-suite 观测结果汇总在
[`../ExperimentReport.md`](../ExperimentReport.md)；归档、binary 和 raw 日志不
提交到项目，以下脚本可重新生成 JSON/CSV/原始输出。

`run_romeo_benchmarks.py` 运行 Parrot–Lime 2020 论文随附的原版 Romeo
artifact。脚本只信任以下归档：

```text
URL: https://web.archive.org/web/20220214052637id_/http://romeo.rts-software.org/releases/FORMATS2020.tgz
SHA-256: 6045841f964a5e37fcb6354eae6999355f8e308292406ff5a09412bccd2d9a29
```

归档和其中的预编译 binary 不提交到项目。默认将归档下载到用户 cache，把内容
解包到运行期临时目录；可用 `--archive` 指定已经下载的归档，用
`--extract-dir` 指定持久解包目录。无论来源如何都会重新校验 SHA-256。

## Quick suite

```bash
python3 src/TAMonitor/PTA/experiments/run_romeo_benchmarks.py \
  --suite quick \
  --output-dir /tmp/tafuzz-romeo-quick
```

本地已有归档时：

```bash
python3 src/TAMonitor/PTA/experiments/run_romeo_benchmarks.py \
  --suite quick \
  --archive /path/to/FORMATS2020.tgz \
  --timeout 120 \
  --output-dir /tmp/tafuzz-romeo-quick
```

Quick 的固定 oracle 为：

| model | forward | backward |
|---|---:|---:|
| aircraft3 | -1140 | -1140 |
| aircraft4 | -4140 | -4140 |
| scheduling2 | -1760 | -1760 |
| scheduling3 | -2560 | -2560 |

任一模式解析失败、进程失败/超时、前后向 cost 不一致或不符合上述 oracle，脚本
返回 1。下载、SHA、解包或 binary 前置条件失败时返回 2。

## Full suite

```bash
python3 src/TAMonitor/PTA/experiments/run_romeo_benchmarks.py \
  --suite full \
  --timeout 3600 \
  --output-dir /tmp/tafuzz-romeo-full
```

Full 运行归档中的 9 个模型：aircraft 3–6、scheduling 2–5 以及
`scheduling_original`。四个 quick 模型仍检查固定 oracle；其余模型检查原版
Romeo forward/backward cost 完全一致。论文的绝对 time/memory 来自特定旧硬件，
本脚本只记录当前环境观测值，不把它们设为通过阈值。

## 输出

- `romeo_benchmarks.json`：artifact 来源、环境、逐模型命令、精确 cost 字符串、
  total/user/system time、max memory、oracle 和失败原因；
- `romeo_benchmarks.csv`：适合表格分析的扁平结果；
- `raw/*.stdout.txt` 与 `raw/*.stderr.txt`：保留带 ANSI 的原始进程输出，供审计。

Romeo `-v` 一次运行依次输出 forward 和 backward 两个区块。解析器按
`Checking mincost` / `Checking backward mincost` 区分区块，而不是依赖行号。

解析器的无网络单元测试可运行：

```bash
python3 src/TAMonitor/PTA/experiments/test_run_romeo_benchmarks.py -v
```

## 解释边界

该实验复现的是论文发布的 Romeo/Time-Petri-Net artifact。论文明确说明其实现先
做 reachable-space 预计算，再做 backward，属于 mixed forward/backward。它能验证
论文原 artifact 的前后向最优值一致，不能单独证明新 MoniTAal Priced-DBM 模块
正确；新模块仍须通过 `AlgorithmProof.md` 所列的 DBM 原语、全局 oracle 和
MightyPPL 集成测试。
