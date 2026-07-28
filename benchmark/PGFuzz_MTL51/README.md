# PGFuzz 51 条历史性质数据集入口

## 先解释目录中反复出现的英文词

- `MTL` 是 `Metric Temporal Logic`，中文为“度量时序逻辑”；这里指 PGFuzz 论文表十二使用的公式表示。
- `AP` 是 `Atomic Proposition`，中文为“原子命题”；它是公式中可独立判断真假的最小条件。
- `source binding` 中文为“源码绑定”；它记录 AP 词项在当前冻结 ArduPilot/PX4 源码中的变量、字段、函数、形成或消费位置。
- `JSON` 是 `JavaScript Object Notation`，中文为“JavaScript 对象表示法”；它保存完整机器可读记录。
- `CSV` 是 `Comma-Separated Values`，中文为“逗号分隔值”；它便于用表格软件筛选。
- `Markdown` 是轻量标记文本格式；它保存便于人工逐条审核的报告。
- `PASS` 表示“自动一致性检查通过”，不表示飞控通过性质。
- `NOT_ASSESSED` 表示“未评估实现符合性”，既不表示满足，也不表示违反。

## 建议阅读顺序

1. [最终结果与四个完整例子](RESULTS.md)：先了解范围、数量、结论边界、参数可变性和未解决项。
2. [51 条性质合并目录](property_catalog.json)：按性质编号进入对应的 ArduPilot 或 PX4 记录。
3. [ArduPilot 的 30 条人工审核页](ArduPilot/property_catalog.md)；[PX4 的 21 条人工审核页](PX4/property_catalog.md)。
4. [源码绑定总指南](SOURCE_BINDING_GUIDE.md)：查看 178 个 AP 如何连接到 227 条当前源码绑定。
5. [PGFuzz/ADGFuzz 依赖算法、工作流与优缺点](DEPENDENCY_METHOD_AND_WORKFLOW.md)。
6. [全部英文术语解释](GLOSSARY.md)、[全部 221 个机器字段解释](FIELD_DICTIONARY.md)，以及[源码绑定中全部类型与单位/坐标原值的中文解释](TYPE_UNIT_DICTIONARY.md)。

## 核心机器数据

- [论文表十二 51 条公式](table_xii_formula_inventory.json)
- [178 个原子命题及当前绑定](atomic_proposition_bindings.json)
- [227 条源码绑定](term_source_bindings.json)
- [7,569 条作者性质—输入候选关联](author_input_dependencies.json)
- [356 个当前输入身份](current_input_identity_map.json)
- [20 条公式直接参数覆盖记录](formula_parameter_coverage.json)
- [固定版本和证据来源清单](source_manifest.json)

## 重新生成与验证

在 `/home/lqq/project/TAFuzz` 执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/build_formula_inventory.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/build_author_dependencies.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/build_source_bindings.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/build_property_records.py

PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/validate_formula_inventory.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/validate_author_dependencies.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/validate_source_bindings.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/validate_property_records.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/PGFuzz_MTL51/scripts/validate_local_links.py
```

构建脚本会覆盖本目录中由它们生成的清单和逐性质记录；验证脚本只检查交付一致性。任何 `PASS` 都不能改变 `implementation_satisfaction=NOT_ASSESSED`。
