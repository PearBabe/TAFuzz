# TAMonitor 科研级运行时验证工具使用手册

本文档对应当前仓库中的 TAMonitor v1 实现。

## 1. 工具定位

TAMonitor 将 MightyPPL 和 MoniTAal 串成一个自动化运行时验证流程：

1. 输入用户 MITL 公式。
2. MightyPPL 完成 typing、NNF、BDD 标记时间自动机构造。
3. TAMonitor 将 BDD 标签展开并投影为 canonical label，格式为 `bits:<valuation>`。
4. 对公式 `phi` 和否定公式 `!(phi)` 分别构造正/负时间自动机。
5. 在正式输出运行时验证结果前，记录正公式和负公式的可满足性检查结果。
6. MoniTAal 使用正/负自动机执行三值监控，输出 `POSITIVE`、`NEGATIVE` 或 `INCONCLUSIVE`。
7. 生成 `steps.csv`、`summary.csv`、`metadata.json`、`results.xlsx`。

v1 已验证的运行时路径是 `--build-mode flatten`。`BDD-native runtime` 和 `compflatten runtime` 在 v1 中只保留接口，不伪造运行时结果。

## 2. 构建和可执行文件

构建命令：

```bash
cmake --build /home/lqq/project/TAFuzz/tool/MightyPPL/build --target TAMonitor -j2
```

可执行文件：

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor
```

查看 usage：

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor --help
```

当前实现会把 usage 打印到错误通道并以非零码退出；这是帮助路径，不代表监控失败。

## 3. 命令行参数

基本格式：

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  [--trace path] \
  [--formula path | --formula-inline text] \
  [--build-mode flatten|compflatten] \
  [--word finite|infinite] \
  [--state symbolic|concrete] \
  [--out path] \
  [--max-valuations n] \
  [--bdd-nodes n] \
  [--bdd-cache n] \
  [--bdd-max-increase n] \
  [--emit-bdd-interface] \
  [--print-steps] \
  [--build-only]
```

参数说明：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--trace <path>` | 无 | 输入 timed word 文件。不提供时进入交互输入。 |
| `--formula <path>` | 无 | 从文件读取 MITL 公式。 |
| `--formula-inline '<text>'` | 无 | 直接在命令行给出 MITL 公式。不能和 `--formula` 同时使用。 |
| `--build-mode flatten|compflatten` | `flatten` | `flatten` 支持运行时验证；`compflatten` 只支持 `--build-only` 构造和统计。 |
| `--word finite|infinite` | `infinite` | 选择有限词或无限词语义。 |
| `--state symbolic|concrete` | `symbolic` | 选择 MoniTAal monitor 状态表示。 |
| `--out <path>` | `test/TARV/results/<timestamp>` | 输出目录。 |
| `--max-valuations <n>` | `4096` | 单条 BDD 标签允许展开的最大 valuation 数。超过时失败，避免指数爆炸。 |
| `--bdd-nodes <n>` | `1000000` | BuDDy BDD 初始节点数。 |
| `--bdd-cache <n>` | `100000` | BuDDy BDD cache 大小。 |
| `--bdd-max-increase <n>` | `500000` | BuDDy 自动扩容上限。 |
| `--emit-bdd-interface` | false | 输出 `bdd_interface.json`，状态为保留接口，不表示 BDD-native runtime 已实现。 |
| `--print-steps` | false | 在终端打印每个 timed word prefix 的逐步 verdict。文件输出中的 `steps.csv` 始终生成；此参数只控制终端是否同步显示。 |
| `--build-only` | false | 只构造自动机和报告统计，不运行 trace monitor。主要用于 `compflatten`。 |

所有数值参数应使用纯数字正整数。

## 4. 支持的 MITL 公式语法

TAMonitor 使用 MightyPPL 的 `Mitl.g4` 语法。空白字符可以自由添加。

### 4.1 原子命题和常量

```text
true
false
p
p1
request_0
```

标识符格式：以小写字母开头，后续可以是大小写字母、数字或下划线。

合法例子：

```text
p
p1
a_b
requestAck2
```

不合法例子：

```text
P
1p
_p
```

### 4.2 布尔连接词

```text
! p
p && q
p || q
p -> q
p <-> q
!(p && q)
(p || q) && r
```

建议复杂公式显式加括号，避免不同连接词混合时产生不符合预期的解析结构。

### 4.3 时间区间

区间边界是非负整数或 `infty`：

```text
[0,5]
(0,5]
[1,10)
(2,infty)
```

当前实现会把时间算子上的全域区间 `[0,infty)` 规范化省略，例如 `F [0,infty) p` 按 `F p` 构造。这是对 MightyPPL 现有构造路径的规范化，不改变全域区间语义。

### 4.4 一元未来和过去算子

```text
F p
F [0,5] p
G [1,10) p
O [0,3] p
H (0,infty) p
```

含义：

| 算子 | 名称 |
| --- | --- |
| `F` | Finally，未来最终 |
| `G` | Globally，未来一直 |
| `O` | Once，过去曾经 |
| `H` | Historically，过去一直 |

弱语义星号写在算子后、区间前：

```text
F* [0,5] p
G* p
O* [1,4] p
H* p
```

### 4.5 二元未来和过去算子

```text
p U [0,5] q
p R [1,10] q
p S [0,3] q
p T (0,infty) q
```

含义：

| 算子 | 名称 |
| --- | --- |
| `U` | Until |
| `R` | Release |
| `S` | Since |
| `T` | Trigger |

星号弱语义同样写在算子后、区间前：

```text
p U* [0,5] q
p R* q
p S* [1,4] q
p T* q
```

### 4.6 Pnueli 算子

支持未来和过去的 Pnueli 形式。参数至少两个：

```text
Fn [0,10] (p, q)
Fn [0,10] (p, q, r)
Gn [0,10] (p, q)
On [0,10] (p, q)
Hn [0,10] (p, q)
```

含义：

| 算子 | 名称 |
| --- | --- |
| `Fn` | Future Pnueli eventually sequence |
| `Gn` | Future Pnueli globally/count-derived construction |
| `On` | Past Pnueli once sequence |
| `Hn` | Past Pnueli historically/count-derived construction |

### 4.7 不作为用户输入支持的内部语法

MightyPPL 语法文件中存在这些 count-construction 形式：

```text
CFn
COn
CGn
CHn
```

它们是 MightyPPL 内部编译和 NNF 转换可能产生的构造形式，不是普通用户 MITL 输入。TAMonitor v1 会拒绝用户公式中直接出现这些符号，并输出：

```text
unsupported_user_formula: CFn/COn/CGn/CHn ...
```

## 5. Trace 输入格式

Trace 文件表示 timed word。每行一个 timed event，空行和 `#` 注释行会被忽略。

### 5.1 CSV 形式

可以带表头：

```text
time,props
0,{}
1,{p1}
2,{p1,p2}
```

也可以直接写：

```text
0,{}
1,p1
2,p1 p2
3,p1;p2
4,p1|p2
5,p1+p2
```

空 valuation 可以写成：

```text
0,{}
0,-
0,empty
```

### 5.2 bits 形式

`bits` 的长度必须等于 `metadata.json` 里的 `proposition_order` 长度。

例如 proposition order 是 `["p1","p2"]`：

```text
time,bits
0,bits:00
1,bits:10
2,11
```

`bits:10` 表示 `p1=true, p2=false`。

### 5.3 MoniTAal 风格导入

```text
@0 {}
@1 p1
@2 bits:10
```

### 5.4 区间时间

时间可以是点，也可以是闭区间：

```text
0,{p}
[1,3],{q}
```

区间要求下界不大于上界。时间值必须是非负整数，并且不能超过 MoniTAal 的时间范围。

### 5.5 交互输入

不提供 `--trace` 时进入交互输入：

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  --formula-inline 'F [0,2] p1' \
  --word finite \
  --out /tmp/tamonitor_interactive
```

终端中逐行输入 timed event，空行或 `q` 结束。

## 6. 输出文件

每次运行会在 `--out` 指定目录下生成：

| 文件 | 说明 |
| --- | --- |
| `steps.csv` | 每个 timed word prefix 的逐步判定结果。 |
| `summary.csv` | 公式可满足性、最终 verdict、构造和监控耗时、自动机规模、BDD projection 统计。 |
| `metadata.json` | 结构化元数据，包括公式、规范化公式、正/负 NNF、proposition order、正/负自动机统计。 |
| `results.xlsx` | Excel 可视化，包含 `Steps`、`Summary`、`Metadata` 三张表。 |
| `bdd_interface.json` | 仅在 `--emit-bdd-interface` 时生成，状态固定为 `interface_reserved_not_implemented`。 |
| `results.xlsx.error.txt` | 仅在 Excel 生成失败时出现。CSV/JSON 仍是权威输出。 |

默认终端输出会显示工具完成状态、公式可满足性、最终 verdict 和输出目录。若希望在终端同步看到每一步 prefix 的判定，加 `--print-steps`：

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  --formula-inline 'F [0,2] p1' \
  --trace /tmp/tamonitor_trace.csv \
  --word finite \
  --state symbolic \
  --build-mode flatten \
  --print-steps \
  --out /tmp/tamonitor_example
```

终端逐步输出格式：

```text
Step verdicts:
  step 1: time=0, label=bits:0, human_label={}, verdict=INCONCLUSIVE, positive_states=1, negative_states=1, advanced=true
  step 2: time=1, label=bits:1, human_label={p1}, verdict=POSITIVE, positive_states=1, negative_states=0, advanced=true
```

字段含义和 `steps.csv` 对应。`advanced=false` 表示之前已经得到确定 verdict，后续事件只在报告中 carry forward，不再继续推进 monitor。

`steps.csv` 字段：

| 字段 | 说明 |
| --- | --- |
| `step` | 第几步事件。 |
| `time` | 事件时间或时间区间。 |
| `canonical_label` | 投影后的 MoniTAal 标签，如 `bits:10`。 |
| `human_label` | 原 trace 中的人类可读标签。 |
| `verdict` | 当前 prefix 的三值结果。 |
| `positive_states` | 正自动机 monitor 当前状态数量。 |
| `negative_states` | 负自动机 monitor 当前状态数量。 |
| `monitor_advanced` | 已经得到确定 verdict 后，后续事件不会继续推进 monitor，此字段会变为 `false`。 |

`summary.csv` 关键字段：

| 字段 | 说明 |
| --- | --- |
| `formula_satisfiable` | 原公式可满足性，`SAT` 或 `UNSAT`。 |
| `negative_formula_satisfiable` | 否定公式可满足性。 |
| `final_verdict` | trace 结束后的整体判定。 |
| `positive_locations` / `negative_locations` | 正/负自动机位置数量。 |
| `positive_edges` / `negative_edges` | 正/负自动机边数量。 |
| `positive_projection_valuations` / `negative_projection_valuations` | BDD 投影展开出的 valuation 数量。 |
| `build_ms` / `monitor_ms` | 构造和监控耗时，单位毫秒。 |

## 7. 运行例子

### 7.1 最小 finite 例子

准备 trace：

```bash
cat >/tmp/tamonitor_trace.csv <<'EOF'
time,props
0,{}
1,{p1}
EOF
```

运行：

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  --formula-inline 'F [0,2] p1' \
  --trace /tmp/tamonitor_trace.csv \
  --word finite \
  --state symbolic \
  --build-mode flatten \
  --print-steps \
  --out /tmp/tamonitor_example
```

期望：

- `Formula satisfiable: SAT`
- 终端出现 `Step verdicts:`，并逐步显示每个 prefix 的 verdict。
- `Final verdict: POSITIVE`
- `/tmp/tamonitor_example/results.xlsx` 可打开。

### 7.2 使用 formula 文件

```bash
cat >/tmp/formula.mitl <<'EOF'
G [0,5] (p -> F [0,2] q)
EOF

/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  --formula /tmp/formula.mitl \
  --trace /tmp/tamonitor_trace.csv \
  --word infinite \
  --out /tmp/tamonitor_formula_file
```

### 7.3 compflatten 构造统计

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  --formula-inline 'F [0,2] p1' \
  --build-mode compflatten \
  --build-only \
  --out /tmp/tamonitor_compflatten_stats
```

`compflatten` 不支持 runtime monitor。如果去掉 `--build-only`，TAMonitor 会返回受控错误：

```text
unsupported_runtime_mode: compflatten runtime monitoring is not implemented in TAMonitor v1
```

### 7.4 BDD-native 接口占位

```bash
/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor \
  --formula-inline 'F [0,2] p1' \
  --trace /tmp/tamonitor_trace.csv \
  --emit-bdd-interface \
  --out /tmp/tamonitor_bdd_interface
```

输出 `bdd_interface.json`，其中 `status` 是：

```json
"interface_reserved_not_implemented"
```

这只表示未来 BDD-native runtime 的接口和 metadata 已预留，不表示该算法已实现。

## 8. 最终实验结果和人工审查入口

清理后保留的最终结果目录：

```text
/home/lqq/project/TAFuzz/test/TARV/results
```

最重要入口：

```text
/home/lqq/project/TAFuzz/test/TARV/results/FINAL_RESULTS_README.md
/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full/paper_review_results.xlsx
/home/lqq/project/TAFuzz/test/TARV/results/mitl_formula_catalog_latest_official.md
```

最终保留结果概况：

| 项目 | 结果 |
| --- | --- |
| Full pipeline | PASS，failed steps 0 |
| Semantic regression | 87 cases，70 runtime verified，0 fail/error/timeout |
| Candidate/baseline | 63/63 matched，0 timeout after 60s rerun |
| Review packet verifier | 151 PASS，0 WARN，0 FAIL |
| Artifact manifest verifier | 16 PASS，0 WARN，0 FAIL |
| Stability audit | 190 PASS，0 WARN，0 FAIL |
| CLI contract | 11 PASS，0 FAIL |

人工审查注意：

- `paper_review_results.xlsx` 是主审查文件。
- `Review Signoff` 仍为空，不声称人工批准。
- XML-to-MITL 等价中标为 `REVIEW_REQUIRED` 的行仍需要人工数学审查。
- BDD-native runtime 和 compflatten runtime 不在 v1 完成范围内。

## 9. 常见错误

### 9.1 `unsupported_runtime_mode`

原因：使用 `--build-mode compflatten` 但没有 `--build-only`。

处理：运行时验证改用 `--build-mode flatten`；如果只要构造统计，加 `--build-only`。

### 9.2 `BDD projection valuation limit exceeded`

原因：某条 BDD 边标签满足的 proposition valuation 数超过 `--max-valuations`。

处理：增大 `--max-valuations`，或缩小公式/命题规模。不要把该错误绕过成不精确投影，否则会破坏运行时验证语义。

### 9.3 `Trace references proposition not present in formula`

原因：trace 里出现了公式中没有的命题。

处理：检查 trace 标签和公式原子命题名是否一致。

### 9.4 `Trace bits length does not match proposition order`

原因：`bits` 长度和 `metadata.json` 中 `proposition_order` 长度不同。

处理：按 proposition order 补齐或缩短 bits。

### 9.5 `unsupported_user_formula: CFn/COn/CGn/CHn`

原因：用户公式直接写了内部 count-construction 语法。

处理：改写为普通 MITL 或 Pnueli 公式，不直接写 `CFn/COn/CGn/CHn`。

## 10. v1 边界声明

当前可以正式使用并审查的能力：

- 用户 MITL 公式解析。
- flatten 时间自动机构造。
- BDD 标签 valuation 投影。
- MoniTAal 正/负自动机三值运行时验证。
- 有限词和无限词模式。
- symbolic 和 concrete 状态模式。
- CSV/JSON/XLSX 报告。
- 可满足性检查结果输出。

当前只保留接口、不声称完成的能力：

- BDD-native runtime。
- compflatten runtime verdict。
- XML-to-MITL 全自动语义等价证明。
- 人工 signoff 自动批准。
