# RIFT-GOLD-120：上下文影响依赖机械基准

## 结论与边界

本目录包含恰好 120 个可独立编译、链接和运行的 C/C++ case，用于在进入真实项目前验证 RIFT 及各弱基线对 source→AP 上下文依赖的识别能力。

ground truth 是 `MECHANICAL_TEMPLATE_ORACLE`：生成器在构造源码时已经知道 source、AP、依赖路径、边类型、前置条件和负对照，因此真值不是由待测分析器反推出来的。它适合查找分析器中的漏边、错边、对象混淆和 controllability 混淆，但不能代替真实项目标注。

真实项目标注状态固定为：

```text
status = PENDING
required_annotators = 2
arbitration_required = true
```

本目录没有伪造双人标注结果、标注一致性或真实项目精度。

## Corpus 组成

12 类各 10 例，每类均为 4 个 `MUST_INFLUENCE`、3 个 `MAY_INFLUENCE`、3 个 `NO_INFLUENCE`：

| 类别 | 主要覆盖点 |
|---|---|
| `direct_data` | source 直接赋值到 AP 使用值 |
| `indirect_data` | 多 helper、call/return 和仿射传播 |
| `control_only` | source 只出现在 guard，不进入 AP 数据值 |
| `alias_object_field` | 指针 alias、对象身份和字段区分 |
| `config_threshold` | configuration→动态 bound，同时保留 observation 输入 |
| `message_parser_state` | message field→typed object→parser→state commit |
| `async_timer_callback_queue` | enqueue、drop、dequeue、callback 和异步状态提交 |
| `setup_mode_prerequisite` | initialize、mode、提交顺序和无效的 pre-setup update |
| `timing_drop_repeat_reorder` | delay、drop、repeat、reorder 和相对 deadline |
| `uncontrollable_false_correlation` | 可影响但不可控的内部状态，以及名称/值相似的外部伪相关输入 |
| `one_input_multi_ap` | 一个输入经共享节点影响两个 AP |
| `joint_inputs` | 两个输入联合满足 guard，记录 joint mutation group |

全局分布：

```text
case             120
C11               60
C++20             60
MUST_INFLUENCE    48
MAY_INFLUENCE     36
NO_INFLUENCE      36
```

所有源码标识符都使用项目中立命名。生成器和验证器会拒绝在 case 标识符中混入具体飞控、协议栈或消息框架名称。

## MUST、MAY 和 negative 的精确定义

- `MUST_INFLUENCE`：在 case 已记录的 lifecycle/调用前提下，模板的每条相关执行都保留 source→AP 的程序依赖路径。
- `MAY_INFLUENCE`：存在 source→AP 路径，但路径受 guard、alias 选择、消息类型、queue 接收或 setup 状态约束。
- `NO_INFLUENCE`：对指定 source/AP pair，模板不存在 value、control、event 或 lifecycle path。一个 negative source 所在 case 仍可能包含另一个真正影响 AP 的 source。

这里的 `MUST` 不表示“任意数值变化都一定翻转 AP”。例如比较式仍需跨越边界。它表示机械模板中的依赖确定性；具体 truth-change 由 `mutation_recipe`、前置条件和边界值描述。

## Influence 与 controllability 分离

每个 source 同时包含：

```json
{
  "controllability": "EXTERNAL | INTERNAL | MODELLED",
  "fuzzable_frontier": true
}
```

`relation` 回答“能否影响 AP”，`controllability` 回答“测试执行器能否直接控制”，两者不能合并。

例如 `RIFT-GOLD-091` 中：

- `source_internal → ap_primary` 是 `MUST_INFLUENCE`；
- 但 `source_internal.controllability == INTERNAL` 且 `fuzzable_frontier == false`；
- 名称和值相似的 `source_external_similar` 可控，却是 `NO_INFLUENCE`。

因此 actionable frontier 至少要求：

```text
positive influence relation
AND
fuzzable_frontier == true
```

不能仅凭变量相关性、命名相似度或 influence cone 成员资格生成 fuzz recipe。

## Ground-truth schema

统一 JSON Schema 位于 `ground_truth.schema.json`。每个 case 的 JSON 包含：

- 精确 source/AP 文件、行、列和 marker；
- source kind、scope、controllability 和 frontier 状态；
- 每个 source×AP pair 的完整关系矩阵；
- `data/control/call/alias/field/parse/callback/queue/setup/timing/event_order` 等边；
- must/may certainty、路径节点和前置条件；
- mutation recipe 或 negative reason；
- joint input group；
- mechanical-oracle 来源与限制；
- 真实项目双人标注的 `PENDING` 状态。

每个 source×AP pair 都必须有且仅有一条 relation，避免只标正例而遗漏负例。

源码中的稳定 marker 形式为：

```c
/* RIFT_SOURCE:source_primary */
int source_primary = ...;

/* RIFT_NODE:node_state */
int node_state = ...;

/* RIFT_AP:ap_primary */
int ap_primary = ...;
```

生成器计算并写入 marker 后一行中 token 的精确位置，验证器再次按源码核对。

## 目录结构

```text
benchmark/rift/gold/
├── cases/                       # 120 个独立 C/C++ case
├── ground_truth/                # 120 份逐 case oracle
├── build/                       # compile_commands 的 object 输出目录
├── compile_commands.json        # 120 条 Clang 18 编译命令
├── manifest.json                # 分布、哈希、oracle 与标注状态
├── ground_truth.schema.json     # Draft-07 JSON Schema
├── generate_gold.py             # 确定性生成器
├── validate_gold.py             # schema、重生成、编译、运行验证器
└── validation.log               # 最终验证证据
```

## 确定性重生成

从 TAFuzz 根目录执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/gold/generate_gold.py \
  --output benchmark/rift/gold \
  --command-root /home/lqq/project/TAFuzz/benchmark/rift/gold
```

生成器只覆盖预期的 120 个 source 和 120 个 truth 文件。若发现未知的同扩展名文件，会拒绝运行，不会替用户删除文件。

## 全量验证

依赖：

```text
Python 3
python jsonschema
clang-18
clang++-18
```

执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/gold/validate_gold.py --jobs 8
```

验证器会：

1. 校验 120 份 JSON Schema；
2. 校验 12×10、4/3/3 和 C/C++ 60/60 分布；
3. 校验全部 source/AP marker 的精确位置；
4. 校验完整 source×AP relation matrix；
5. 校验 influence 与 controllability/frontier 没有混淆；
6. 在 `/tmp` 重新生成 corpus 并逐字节比较；
7. 执行 `compile_commands.json` 中的 120 条 Clang 18 object 编译；
8. 再链接并运行 120 个独立 executable；
9. 使用 `-Wall -Wextra -Werror`，任何 warning 都作为失败；
10. 校验生成目录中没有 Python bytecode cache。

成功摘要应为：

```text
SUMMARY status=PASS cases=120 schema=120 locations=120 relations=120 controllability=120 project_neutral=120 failures=0
```

## 用于分析器评估

建议至少分别报告：

- `MUST_INFLUENCE` recall；
- `MAY_INFLUENCE` recall 和 precision；
- negative false-positive rate；
- edge-kind recall；
- source/AP location accuracy；
- fuzzable-frontier precision/recall；
- prerequisite 和 joint-group accuracy。

不要把一个 analyzer 找到的所有 influence source 都计作 fuzzable source；也不要把本 corpus 的模板成绩外推成真实项目成绩。真实项目仍需按计划进行两名真人独立标注和仲裁。
