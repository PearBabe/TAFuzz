# RIFT-M1 文献基线复现报告

## 结论

本目录形成了三条可审计证据链，但它们的完成级别不同：

| 基线 | 已完成 | 未完成或不能声称 |
|---|---|---|
| LTL-Fuzzer（ICSE 2022） | 冻结官方 commit；核心库与 AFLGo 构建；导入 49 个公开 AP target tuple；运行公开 Problem1；调用原始 `Automata` 实现处理公开 LTL 性质 | 因官方 LLVM 11 插桩 pass 无法用现有 LLVM 14 构建，没有端到端 fuzz campaign |
| PGFuzz（NDSS 2021） | 按论文 Table XII 冻结 56 条逻辑 policy，并逐文件导入公开 input map | 公开仓库只覆盖其中 51 条；这些 map 是 silver standard，不是因果 gold truth |
| MoonShine（USENIX Security 2018） | 官方预计算表确认 `mlockall → msync`；用 Clang AST 忠实执行论文的 `W ∩ R_cond` 规则；负对照通过 | 公开仓库没有论文中的 Smatch 提取 hooks；当前环境也缺 Ragel、Go、goyacc，不能声称运行了原始静态提取器 |

这满足“先运行至少一个原始 CCF-A artifact 组件”的最小门槛：LTL-Fuzzer 的未修改 `Automata` 库已在其公开 Problem1 性质上成功运行。这里刻意不把“组件成功”写成“完整 artifact 端到端复现”。

## 1. LTL-Fuzzer

冻结版本为 `716ac301fa3a8ea39814bc80eeebba49c19c1378`。核心 CMake 工程和其捆绑 AFLGo 构建成功；AFLGo 自测报告插桩 wrapper 可以工作。

严格 importer 共读到 49 个 target tuple：

- Problem1 的 46 个目标均被解析到精确源码行、整数输出和 AP 名称；
- Telnet 的 3 个目标被保留为 unresolved，而不是静默丢弃；
- unresolved 原因是 `experiment/testTelnet/contiki` 只有 gitlink `32b5b17f674232867c22916bb2e2534c8e9a92ff`，仓库却没有 `.gitmodules`；
- importer 还记录了 `WILLDISABLED` 与 `WILL_DISABLED` 的上游标识符不一致。

公开 Problem1 的 1000-byte seed 运行退出码为 0，产生 107 个输出事件和 894 条 `Invalid input`。这两个流都作为原始证据保留，不能把 stderr 当成复现失败，也不能隐藏。

`Automata` smoke test 使用 artifact 自带公式：

```text
!(! (true U oU) | (! oU U ((oZ & ! oU) & X (! oU U oP))))
```

输入事件前缀为 `iH,oZ,iB,oZ`，每一步都得到合法 successor，输出以 `status PASS` 结束。
精确编译/运行命令、两个退出码和三份 SHA-256 固化在
`results/ltl_fuzzer/automata_smoke_receipt.txt`。其 claim boundary 是
“original artifact component on public Problem1”，不是端到端 campaign。

完整 LTL-Fuzzer 插桩没有成功：README 固定 LLVM 11，而本机只有 LLVM 14。保留的构建失败显示 `sys::fs::F_None`、`CreateConstGEP2_64` 等 API 不兼容，并发现缺失显式 `<map>` include。此处没有修改上游源码来伪造“原版通过”。

## 2. PGFuzz 56-policy silver standard

论文 Table XII 给出 ArduPilot 30、PX4 21、Paparazzi 5，共 56 条逻辑 policy。公开 artifact 的物理目录不能直接当成 56 条：

- 51/56 条 policy 有公开 input map；缺失的 5 条全部来自 Paparazzi；
- 51 条逻辑 policy 复用 49 个物理 map 目录；
- `A.CIRCLE4/5/6 → A.CIRCLE4_6`、`PX.ORBIT4/5 → PX.ORBIT4_5` 等 alias 已显式记录；
- artifact 还有未被 Table XII 这 56 条引用的 `PX.CHUTE`，也被单独记录；
- 每个 `parameters.txt`、`cmds.txt`、`envs.txt`、`preconditions.txt` 都保存 SHA-256、行数、去重名称和重复项。

使用边界必须保持清楚：PGFuzz map 可用于比较 RIFT 是否找回论文作者认为值得变异的输入集合，但不能证明每个输入都能因果改变 AP，也不能证明列表完整。因此指标应称为 silver-set overlap/recall，而不是 gold causal precision/recall。

## 3. MoonShine `mlockall → msync`

冻结版本为 `95e5f6dfd2760a9d763fc2bc90623c9e1e74e804`。官方 `implicit_dependencies.json` 有 228 个 reader key、9891 条去重 edge；`msync` 有 13 个候选 predecessor，其中包含 `mlockall`。

论文规则被实现为：

```text
W(upstream_call) ∩ R_cond(target_call) != ∅
```

在忠实微例上，Clang JSON AST 得到：

```text
W(mlockall)          = { vm_area_struct.vm_flags }
R_cond(msync)        = { vm_area_struct.vm_flags }
intersection         = { vm_area_struct.vm_flags }
unrelated ∩ R_cond   = ∅
```

该复现也验证了跨 helper 的 summary closure：`mlockall` 的写通过 `mlock_fixup_lock` 汇总。微例明确标注为 `FAITHFUL_CLANG_MICRO_REPRODUCTION_NOT_ORIGINAL_SMATCH_EXTRACTOR`。这是对论文算法的可执行复现，不是对未公开实现的冒充。

MoonShine 适合成为 RIFT-M3 的弱基线，但不适合作为 RIFT 主方法：论文自己报告了 path/value 缺失造成过估、alias 造成漏报、对象实例不精确及跨线程/进程 producer 不支持。RIFT 对比时应固定这些限制，而不是逐项目手改 MoonShine 结果。

## 4. 跨项目通用部分与项目特定部分

| 来源 | 可跨项目复用的机制 | 必须由项目模型或源码重新获得的内容 |
|---|---|---|
| LTL-Fuzzer | AP target tuple schema；target/source/AP 字典一致性校验；monitor 独立 smoke test | Problem1 数字事件、Telnet vocabulary、具体源码位置、LLVM 11 pass |
| PGFuzz | parameter/command/environment/prerequisite 四类输入；规范化集合比较；缺失和 grouped policy 的显式记账 | 飞控参数名、MAVLink 命令和值、SITL 环境字段、mode、policy alias 和人工排除项 |
| MoonShine | `W ∩ R_cond`；过程间 summary closure；producer-before-consumer 顺序 | Linux syscall/调用图、`vm_area_struct.vm_flags` 语义、Smatch 表和 Syzkaller 格式 |

对 RIFT 的约束因此是：通用分析器只能内建“依赖类型和证据结构”，不能内建 ArduPilot、Telnet 或 Linux 的具体名字；项目特定规则必须落在版本化 framework model 中，并在 certificate 中标为 `modelled`。

## 5. 重跑与验证

从 TAFuzz 根目录执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/reproduction/literature_baselines/validate_literature_baselines.py
```

验证器会重新生成两份 importer 输出、重新执行 MoonShine AST 微复现、重新编译并运行 Problem1 和 Automata smoke，并检查 frozen commit、关键哈希、输出计数与已记录失败。不会运行耗时 fuzz campaign，也不会修改三个外部 artifact。

完整冻结环境、命令、状态和非声明项见 `reproduction_manifest.json`。
