# IADG-Lite：已绑定输入的有限跨函数上下文图

`IADG` 是 **Interprocedural Assignment/Dependency Graph**，中文为“跨过程赋值/依赖图”。本原型不做完整 C++ 指针分析；它验证一个更小、更清楚的研究想法：

1. 从三类固定输入及其候选源码绑定出发；
2. 在当前 ArduPilot 源码中重新确认直接消费函数，找不到时按字段精确词重新定位；
3. 从消费函数向前扩展最多 `k` 层词法函数调用，并做一次受限共享字段扩展；
4. 对所有到达函数中的变量名、字段名、函数名和文件名使用固定的 15 类状态词典匹配；
5. 一次输出 `input -> possible states`，供后续任意 MITL 性质按状态并集查询。

## 为什么不需要先寻找“源码里的全部状态变量”

状态在这里是概念标签，而不是一个预先枚举的 C++ 变量。分析器扫描 `ArduCopter/` 和 `libraries/` 的全部 C/C++ 源码；对某个输入，只在它能到达的函数上下文中检查所有标识符。因此 `altitude`、`roll` 或 `mission` 出现在多少文件都不影响算法，也不会只绑定某一个状态文件。

## MAV_CMD 的处理

每个 `MAV_CMD_*` 从自己的 `case MAV_CMD_*:` 分支起步。分析器只读取该分支的标识符和调用，再进入其 handler；不会把公共 `handle_command_int_packet()` 中其他命令的代码混进来。

## 运行

```bash
python3 iadg_lite.py \
  --source /path/to/ardupilot \
  --manifest input_manifest.csv \
  --out out \
  --include-root ArduCopter \
  --include-root libraries \
  --call-hops 3 \
  --field-hop-from 1 \
  --progress
```

输出：

- `binding_validation.csv`：每个输入的源码绑定复核状态；
- `input_state_relations.csv`：输入—状态候选及最短证据；
- `state_to_inputs.json`：MITL 查询直接使用的状态到输入表；
- `althold2_comparison.json`：与 PGFuzz A.ALT_HOLD2 三类集合的差异；
- `summary.json`：文件、函数、调用边、运行时间和参数；
- `experiment_report.md`：自动汇总报告。

## 与 ADGFuzz 的单一核心差异

ADGFuzz 主要在函数内构造赋值依赖，再按变量词项映射输入。本原型把输入先锚定到真实消费函数，然后只增加一个机制：**有限的跨函数上下文扩展**。因此它仍然是名称语义辅助的轻量方法，但能自动覆盖参数 getter、命令 handler、SITL 模型函数和传感器后端之间的多文件传播。

## 当前边界

这是候选生成器，不是完备的 C++ 值流分析。重载、函数指针、别名和宏生成调用可能未解析；同名函数会保守连接。结果允许误报，主要检验召回和候选集合缩减能否同时成立。
