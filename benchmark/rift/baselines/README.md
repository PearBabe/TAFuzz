# RIFT-M3 共用弱基线评估层

## 结论与准确边界

本目录已经实现并跑通 RIFT-M3 的共用输入、结果、私有评分、答案泄漏审计契约和六种
弱基线。统一 C++20/Clang/LLVM/SVF 实现位于 `src/StaticAnalysis`，冻结的全量结果、
性能、哈希和实施后说明位于 `results/m3/`。RIFT 新方法仍从 M4 开始；M3 结果不能被
包装成 RIFT 优越性结论。

当前评估轨固定为：

```text
evaluation_track    = PAIR_CLASSIFICATION_DIAGNOSTIC
binding_mode        = GIVEN_CANDIDATE_ANCHORS_NOT_SCORED
controllability     = GIVEN_CONTROLLABILITY_NOT_SCORED
```

即分析器会收到 candidate source anchor、AP anchor 和 controllability。M3 可以评价
给定 `source×AP` pair 的 relation class、影响召回、边类型和派生 actionable 集合，
但不能报告：

- source discovery recall；
- AP 自动绑定准确率；
- standalone frontier discovery precision/recall；
- open-world candidate-generation burden；
- 无偏的论文级泛化结果。

源码中的 `RIFT_SOURCE`/`RIFT_AP` marker 按计划保留，它们明确表示 given anchors。
M4+ 才需要开放式 discovery track、分析器 binary/config 先冻结后生成的隐藏 holdout，
以及独立的 source canonicalization 规则。

## 文件

| 文件 | 作用 |
|---|---|
| `analyzer_input.schema.json` | analyzer 可见的严格无真值输入 schema |
| `prepare_inputs.py` | trusted preprocessor；在 `/tmp` 生成 opaque、重命名后的输入树 |
| `baseline_result.schema.json` | 完整 source×AP prediction matrix、边证据和执行 receipt |
| `evaluate.py` | trusted private evaluator；分析完成后才读取 gold truth |
| `no_answer_leakage.py` | analyzer 静态答案扫描与 `strace` 文件访问审计 |
| `tests/dummy_no_influence.py` | 对所有给定 pair 输出 `NO` 的 contract fixture，不是实际 baseline |
| `tests/test_evaluation.py` | 确定性、schema、指标和拒绝路径单测 |
| `validate.py` | 全流程验收，包括 120 个 sanitized source 的 Clang 编译和 strace |
| `run_m3_all.py` | 先运行完六个 analyzer，再统一进行 private evaluation 并固化哈希/性能 |
| `validate_m3_results.py` | 重算六方法 bundle 哈希、schema、pair universe、core identity 与隔离证据 |
| `results/m3/` | 六种基线 raw result、evaluation、外部性能、答案隔离证据和中文报告 |

## 1. Analyzer 输入隔离

### 可见字段

`analyzer_input.schema.json` 的每个 case 只包含：

- opaque `case_NNN`；
- 重命名为 `sources/case_NNN.c|cpp` 的 source 及其新 SHA-256；
- 只用相对路径的 compile command；
- source/AP anchor 的 ID、symbol、marker 和精确位置；
- 每个给定 source 的 `EXTERNAL|INTERNAL|MODELLED` controllability；
- 三个固定的 evaluation/binding/controllability mode。

明确不包含：

```text
原始 RIFT-GOLD case ID / 原文件名 / variant
category / case_relation / MUST_INFLUENCE 等 truth label
expected relation / channel / edge / path
fuzzable_frontier truth
precondition / joint_group / mutation recipe / negative reason
oracle derivation / ground-truth filename或hash
```

### Opaque 化策略

`prepare_inputs.py` 按冻结 source SHA-256 排序后分配 `case_001..case_120`，打散原来按
category 和 4/3/3 标签分组的 ordinal；删除源码头中的原 case、category、variant 和
relation；同时重写 source/object 文件名及 compile DB 路径。compile command 使用
`.` 和相对路径，因此在两个不同 `/tmp` 根中生成的 package 逐字节相同。

这个映射是公开、确定性的 development/regression 机制，不是隐藏实验 nonce。熟悉
当前 120 case 的实现者仍可能记住其结构，因此不能把它包装成无偏 holdout。

生成输入：

```bash
cd /home/lqq/project/TAFuzz
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/baselines/prepare_inputs.py \
  --output /tmp/rift-m3-input-example
```

脚本只接受尚不存在且位于 `/tmp` 下的输出目录，不覆盖已有目录。结果包含：

```text
/tmp/rift-m3-input-example/
├── analyzer_input.json
├── compile_commands.json
├── sources/case_NNN.{c,cpp}
└── build/
```

preprocessor 只枚举 `cases/`、读取 source 和 compile DB：anchor 来自公开 marker，
controllability 按当前 fixture 的公共 source-boundary 规则派生——marked declaration 接收
`read_arg(...)` 为 `EXTERNAL`，否则为 `INTERNAL`。它不读取 `ground_truth/`、gold
manifest 或 relation/path/frontier truth。生成完成后，baseline analyzer 的 mount、cwd、
参数和环境中只能出现 sanitized tree；`evaluate.py` 是分析阶段唯一读取 truth 的组件。

## 2. Baseline 结果契约

`baseline_result.schema.json` 要求每个 input case 中每个 source×AP 组合恰好一条
prediction。JSON Schema 检查字段结构，`evaluate.py` 再强制完整 cross product、唯一
pair 和状态一致性。

关系预测：

```text
MUST | MAY | NO | UNKNOWN
```

状态与关键不变量：

- concrete `MUST/MAY/NO` 必须是 `ANALYZED`；
- `UNKNOWN` 必须是 `UNSUPPORTED` 或 `ERROR`；
- `UNKNOWN` 不能带边，且永远不能 densify 为 `NO`；
- `NO` 不能带 positive-path edge；
- `MUST/MAY` 至少带一条 edge；
- 每条 edge 必须给出 kind、certainty、status、evidence 和 limitations；
- case/top-level `COMPLETE|PARTIAL|UNSUPPORTED|ERROR` 必须能由 pair 状态唯一推出。

执行 receipt 是公平比较的必需字段：

```json
{
  "exit_code": 0,
  "wall_seconds": 1.25,
  "peak_rss_bytes": 123456789,
  "toolchain": [{"name": "clang", "version": "18.1.8"}],
  "analyzed_units": 120
}
```

还必须记录 analyzer ID/version/implementation/configuration/command、analyzer artifact
SHA-256 和绑定的 `input_manifest_sha256`。RSS 无法可靠测量时可写 `null`，不能写猜测值。

## 3. 私有评估与指标

当前 pair universe 不是 case 级的 48/36/36，而是完整 source×AP matrix：

```text
cases             120
sources           189
APs               130
pairs              202
MUST / MAY / NO  66 / 84 / 52
positive pairs     150
derived actionable 143 true / 59 false
pair×edge-kind      314
exact gold edges    373
```

评分命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/baselines/evaluate.py \
  --input /tmp/rift-m3-input-example/analyzer_input.json \
  --result /tmp/rift-m3-input-example/baseline_result.json \
  --output /tmp/rift-m3-private-evaluation.json
```

private evaluation 输出必须放在 sanitized tree 外。它含 category 和 truth diagnostics，
若放回 analyzer mount 会构成直接答案泄漏。

### Influence 与 UNKNOWN

```text
positive = MUST or MAY
TP = gold positive 且 predicted positive
FP = gold NO 且 predicted positive
FN = gold positive 且 predicted NO/UNKNOWN/unsupported
TN = gold NO 且 predicted NO
```

gold `NO` 上的 `UNKNOWN` 单独计为 `unknown_on_negative`，不能计入 TN。没有 positive
prediction 时 precision 是 `null`，不是 1；本 corpus 有 150 个 positive，因此 recall
和 F1 为 0。

### MUST 与 exact class

同时报告：

- `must.detection_recall`：gold MUST 被预测成 MUST 或 MAY；
- `must.exact_recall`：gold MUST 被准确预测成 MUST；
- MUST precision、MUST→MAY downgrade 和 unresolved rate；
- 三类 one-vs-rest precision/recall/F1；
- `exact_accuracy_unknown_is_wrong` 和 macro-F1；
- 总体及 12 个 category 的同构指标。

### Actionable 只是派生 diagnostic

分析器不提交 frontier prediction。评估器按以下公式派生：

```text
predicted actionable
= predicted relation in {MUST, MAY}
  AND supplied controllability in {EXTERNAL, MODELLED}
```

gold actionable 仍由 positive influence 和 gold fuzzable-frontier 联合给出。因为
controllability 是输入，不是分析器发现结果，这个 precision/recall/F1 只能说明 relation
classification 对 actionable selection 的后果，不能称为 frontier discovery 质量。

### Edge 与 candidate 边界

跨方法 headline edge 指标是：

```text
(opaque case, given source, given AP, edge kind)
```

AST、LLVM、MemorySSA 和 SVF 的 entity 粒度不同，当前尚无统一 graph→gold anchor
projection。因此 exact endpoint 结果明确标为
`UNPROJECTED_DIAGNOSTIC_NOT_HEADLINE`；在投影规则冻结前不能用于方法优越性结论。

`candidate_set_size_ratio` 和 false-candidate inflation 也只在给定的 202-pair universe
内计算，并标为 `candidate_inflation_pair_classification_diagnostic`。它不是 open-world
source candidate inflation；ratio 小于 1 也可能只是漏报，必须和 recall 联合解释。

## 4. 无答案泄漏审计

静态扫描 analyzer core/source/config：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/baselines/no_answer_leakage.py scan \
  --analyzer-root /path/to/analyzer/core \
  --report /tmp/rift-m3-static-leakage.json
```

硬禁项包括：gold/ground-truth 路径、`RIFT-GOLD-NNN`、原始带
`category_must|may|negative_vN` 的文件名、`case_relation`、expected relation/edge/path
字段、完整 gold relation label 和 12 个 benchmark category literal。合法的结果枚举
`MUST/MAY/NO/UNKNOWN` 不会被笼统禁止。

运行时审计：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/baselines/no_answer_leakage.py audit \
  --sanitized-root /tmp/rift-m3-input-example \
  --analyzer-root /path/to/analyzer/core \
  --trace-output /tmp/rift-m3-analyzer.strace \
  --report /tmp/rift-m3-runtime-leakage.json \
  -- /path/to/analyzer --input /tmp/rift-m3-input-example/analyzer_input.json
```

`audit` 会先扫描 analyzer 与 sanitized package，再用 `strace -f -e trace=%file` 运行
命令。允许读取 sanitized tree、显式 analyzer root、系统 loader/toolchain/runtime
library；对 gold、`.codex` 或其他未列路径的访问都失败。它是可审计检测，不是内核级
sandbox；正式实验仍应使用只读 mount/namespace 做物理隔离。

## 5. Dummy fixture 与完整验证

dummy 只验证 contract 和评分器，不是 weak baseline：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/baselines/tests/dummy_no_influence.py \
  --input /tmp/rift-m3-input-example/analyzer_input.json \
  --output /tmp/rift-m3-input-example/dummy_result.json
```

它在 202 pair 上得到：

```text
influence TP=0 FP=0 FN=150 TN=52
precision=null recall=0 F1=0
exact relation=52/202
MUST detection recall=0
derived actionable FN=143 TN=59
predicted pair-edge-kind=0/314
```

一键验收：

```bash
cd /home/lqq/project/TAFuzz
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/baselines/validate.py --jobs 8
```

validator 会检查两个 JSON Schema，执行 7 个单测，在两个独立 `/tmp` 根生成并逐字节
比较 package，编译全部 120 个 sanitized C/C++ source，运行 dummy 和 private
evaluator，并用 strace 审计 dummy。当前实测结果：

```text
SUMMARY status=PASS schemas=2 unit_tests=7 sanitized_cases=120
source_anchors=189 ap_anchors=130 pairs=202 compiled=120
dummy_exact=52/202 unknown_not_tn=PASS strace=PASS failures=0
```

`--skip-strace` 只用于缺少 strace 的移植诊断，不能作为完整 M3 evaluation-layer
验收结果。

## M3 baseline 接入门禁

每个实际弱 baseline 必须：

1. 只读取 sanitized package；
2. 在 analyzer binary/config hash 冻结后运行；
3. 输出 schema-valid 且完整的 202-row matrix；
4. 不能用 UNKNOWN 回避难例后再缩小 recall denominator；
5. 保存 execution receipt、raw result SHA-256、static scan 和 strace report；
6. 用同一 input hash、schema 和 evaluator 与其他 baseline 比较；
7. 将 unsupported construct、model requirement、budget exhaustion 和 tool error 明确写进 limitations/status，而不是静默当作 NO。

后续开放发现评估还需新增 hidden source/AP universe、unmatched extra candidate 计分、
canonical input-source abstraction、graph endpoint projection，以及 binary-frozen hidden
holdout；在这些条件完成前，本层只支持 pair-classification engineering diagnostic。
