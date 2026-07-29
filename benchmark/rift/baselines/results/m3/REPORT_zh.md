# RIFT-M3 六种弱基线实施后报告

## 1. 结论

RIFT-M3 已在同一 opaque 输入、同一结果 schema、同一 analyzer binary 和同一 trusted
evaluator 下完成六种弱基线的实现与运行。该里程碑只冻结实施前的对照能力，不包含
RIFT 新方法，也不用于宣称 RIFT 已优于基线。

本轮固定身份：

```text
track                         PAIR_CLASSIFICATION_DIAGNOSTIC
candidate source/AP anchors   GIVEN；不评价 discovery/binding
controllability               GIVEN；不评价 frontier discovery
cases / source×AP pairs       120 / 202
gold MUST / MAY / NO          66 / 84 / 52
analyzer binary SHA-256       ea0c5b10...faf8af40
sanitized input SHA-256       076e1f4d...257a229
M3 core tree SHA-256          1adddf78...2694c5b
result schema SHA-256         4ded9b57...98e8e3
```

完整身份、逐方法命令、结果哈希和外部进程性能位于
[`manifest.json`](manifest.json)，逐行指标位于 [`summary.csv`](summary.csv)。六个
analyzer 进程全部结束以后才运行 trusted evaluator，分析器运行阶段没有 gold
读取机会。

## 2. 同预算静态诊断结果

正类表示 gold `MUST|MAY`；所有 `UNKNOWN` 都按未检出计算，gold `NO` 上的
`UNKNOWN` 不计为 TN。

| 方法 | 状态 | TP/FP/FN/TN | Precision | Recall | F1 | MUST 检出 recall | 派生 actionable F1 | UNKNOWN | wall / RSS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ADGFuzz-style assignment | COMPLETE | 91/0/59/52 | 1.000 | 0.607 | 0.755 | 0.697 | 0.740 | 0 | 0.89 s / 107.2 MiB |
| MoonShine-RW | UNSUPPORTED | 0/0/150/0 | N/A | 0.000 | 0.000 | 0.000 | 0.000 | 202 | 0.93 s / 105.8 MiB |
| plain PDG/property slice | COMPLETE | 111/3/39/49 | 0.974 | 0.740 | 0.841 | 0.818 | 0.832 | 0 | 0.93 s / 109.3 MiB |
| LLVM SSA def-use | PARTIAL | 52/0/98/40 | 1.000 | 0.347 | 0.515 | 0.515 | 0.533 | 19 | 7.18 s / 89.1 MiB |
| MemorySSA + AA | COMPLETE | 96/6/54/46 | 0.941 | 0.640 | 0.762 | 0.818 | 0.748 | 0 | 4.68 s / 99.2 MiB |
| SVF 3.2 value-flow | COMPLETE | 94/6/56/46 | 0.940 | 0.627 | 0.752 | 0.879 | 0.737 | 0 | 40.21 s / 100.2 MiB |

这里的 actionable 集合由“预测正类 AND supplied controllability”派生，因此不是
frontier discovery 指标。所有弱基线都把完整路径降为 `MAY`，没有预测端到端
`MUST`；`MUST 检出 recall` 只表示 gold MUST 是否至少被识别为可能影响。

## 3. 结果解释

### 3.1 ADGFuzz-style assignment

赋值图在本 corpus 上没有 false positive，但只找到 60.7% 正依赖。它能覆盖直接赋值和
部分同函数表达式，不能覆盖过程间 actual/formal、alias、纯 control、timer/callback/
queue、lifecycle、scope 和 timing。`NO` 仅表示赋值抽象内无路径，不能解释成语义上的
不影响。

### 3.2 MoonShine-RW

120-case M2 corpus 给的是变量声明/引用 anchor，而忠实的 MoonShine `W∩R_cond` 接口
需要 producer/consumer call anchor；因此 202 pair 全部明确返回
`UNKNOWN/UNSUPPORTED`。这不是 MoonShine 质量分数，不能拿 `F1=0` 与其他方法排名。
专用 call-anchor smoke 和 M1 的 `mlockall→msync` read/write implicit-dependency
复现均通过，说明实现的字段交集规则可运行，但当前共用接口没有可比 anchor。

### 3.3 plain PDG

plain PDG 在弱基线中得到最高 influence F1（0.841），说明加入 ordinary data、control
和 direct-call 边能明显补足 assignment-only 图。三个 false positive 均来自共享
formal/return 节点造成的跨 callsite 污染；该实现明确保留为 context-insensitive 弱基线，
不冒充 RIFT 的上下文敏感分析。

### 3.4 LLVM def-use 与 MemorySSA

mem2reg 后的 LLVM SSA 只连接寄存器 operand，不能跨 load/store 建立内存流，因此 recall
为 0.347。修复源码 anchor 到 `DILocalVariable` 的“列号不可用”映射后，已经从首轮
202/202 UNKNOWN 恢复到 183/202 resolved；余下 19 个由优化后缺失或歧义 debug value
明确保留 UNKNOWN。

MemorySSA + BasicAA/TBAA/ScopedNoAliasAA 把 recall 提升到 0.640，但仍是函数内 memory
clobber 证据。它对 control-only 类别为零召回，并且对过程间 parser/state 与同 helper
调用实例可能产生漏报或误报。MustAlias 只提高一条 memory edge 的证据强度，不代表整条
路径 must-execute。

### 3.5 SVF 3.2

SVF 构建 `SVFIR → AndersenWaveDiff → full SVFG` 并显式遍历 direct、indirect、call、
return 和 thread-MHP edge。首轮在同一进程分析第二个 module 时触发 SVF 3.2 singleton
状态 assertion；最终 CLI 使用同一 binary 的逐 case 子进程隔离，120/120 case 完成，
失败子进程会变成完整 ERROR matrix 而不是令父进程崩溃。结果配置记录
`svf_process_isolation.mode=PER_CASE_SUBPROCESS`。

SVF 的 MUST 检出 recall 最高（0.879），但 influence F1 仍低于 plain PDG；原因与任务
预期一致：value-flow 不等于 control/event/time/scope 依赖，而且 field/object/call-context
精度会影响 false positive。40.21 秒包含 120 个独立 SVF 进程，不能与单进程库调用时间
混淆。

## 4. 工程修复与回归门禁

本里程碑除了六种算法，还修复并固定了以下 adapter 语义：

- compile command 的相对 include 以 sanitized input root 为 cwd；
- `PATH` basename 调用仍解析并哈希真实 analyzer binary；
- frontend/bitcode tool error 输出 `ERROR/UNKNOWN` 完整矩阵并退出 1；
- `--method` 重复时采用最后一个值，不残留另一 backend；
- source path 采用规范化 suffix/唯一实体匹配，避免 blind basename collision；
- LLVM debug metadata 缺列号时以 exact file/line/symbol/uniqueness 解析；
- SVF 多 case 采用进程隔离，并保留 case 顺序、父命令和 artifact hash；
- 内部 receipt 明确不是 headline 性能，完整性能由外部 GNU time 采集。

当前 CTest 包含 8 项：三种 AST smoke、LLVM/MemorySSA/SVF smoke、compile-directory、
PATH、tool-error 和 repeated-method 黑盒回归，全部通过。

## 5. 答案隔离与诚实边界

最终静态扫描和 `strace -f -e trace=%file` 审计通过：526 个观测路径只落在 sanitized
输入、analyzer、固定 SVF/Clang/LLVM runtime 和显式 compiler probe root；没有读取
`benchmark/rift/gold`、`.codex` 或其他工作区文件。审计摘要见
[`no-answer-leakage-final.json`](no-answer-leakage-final.json)，压缩原始 trace 见
[`no-answer-leakage-final.trace.gz`](no-answer-leakage-final.trace.gz)。

本报告不能支持以下结论：

- 不能评价 source discovery、AP 自动 binding 或 frontier discovery；
- 不能把 exact internal graph endpoint 当 headline，因为跨方法 projection 尚未冻结；
- 不能把 MoonShine 的接口不兼容写成算法劣势；
- 不能由 M2 机械 corpus 推导真实项目准确率；
- 不能声称 RIFT 优于任何基线，因为 M4+ 新方法尚未进入本轮实验；
- 不能声称已经满足三真实项目 portability gate。

M3 的价值是冻结一个可运行、可复现、失败语义明确的实施前基线面。M4 必须在同一
Property IR、版本、schema 和测试 universe 上比较，并把所有新优势继续视为待验证
假设。
