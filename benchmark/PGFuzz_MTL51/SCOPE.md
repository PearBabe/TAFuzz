# PGFuzz 表十二 ArduPilot/PX4 MTL 数据集范围

## 1. 当前目标

本目录以 PGFuzz 论文第 18 页 `Table XII`（表十二）为历史公式来源，逐条重建：

- ArduPilot 的 30 条 `A.*` 性质；
- PX4 的 21 条 `PX.*` 性质；
- 每条公式中的原子命题、参数操作数和相邻观测关系；
- PGFuzz 作者制品为该性质保存的配置参数、命令、环境输入和前置配置；
- 上述命题和输入在当前冻结 ArduPilot/PX4 源码中的变量、字段、函数、状态转换和消息位置；
- PGFuzz/ADGFuzz 依赖提取方法的算法、工作流、示例及优缺点。

本轮不再要求每条性质都有可靠的具体秒数。论文中的 `k` 保留为未知符号，`t-1` 只表示上一观测，不解释成一秒。

## 2. 已核实的来源边界

用户提供的 ADGFuzz PDF 共 19 页，最后一页是 `Artifact Appendix`（制品附录），没有 MTL 公式。所指公式实际位于 PGFuzz PDF 第 18 页的表十二。表十二共 56 条：ArduPilot 30 条、PX4 21 条、Paparazzi 5 条；本目录只纳入前两类，共 51 条。

PGFuzz 公开仓库与论文表格并非一一同形：

- ArduPilot 有 28 个 policy 目录，因为 `A.CIRCLE4_6` 共用 A.CIRCLE4、A.CIRCLE5、A.CIRCLE6 的输入集合，`A.FLIP4` 对应论文的 `A.FLIPGeneral`；
- PX4 有 21 个目录，`PX.ORBIT4_5` 共用 PX.ORBIT4、PX.ORBIT5 的输入集合，并额外存在论文表十二没有的 `PX.CHUTE`；
- 数据集保留上述差异，不能用目录数直接替代表格性质数。

## 3. 证据和结论等级

所有 51 条记录固定使用：

```text
dataset_role = HISTORICAL_PROPERTY_SEED
implementation_satisfaction = NOT_ASSESSED
```

`HISTORICAL_PROPERTY_SEED` 表示“历史论文性质种子”：可作为后续静态分析和模糊测试的目标，但尚未被当前版本官方文档重新确认为规范。`NOT_ASSESSED` 表示“没有评估当前实现是否满足性质”。

源码映射只回答“当前源码中可能对应什么、在哪里、怎样读取”，不从控制流反推出新性质，也不给出符合性结论。映射采用以下等级：

- `EXACT`：类型、语义、作用域和使用路径均有直接证据；
- `MODELLED`：可以建模该命题，但不是规范概念的精确等价物；
- `NAME_ONLY`：只有名称相似，不能作为可靠数据依赖；
- `UNRESOLVED`：当前证据不足，不进行猜测。

## 4. 与原 13 条数据集的关系

原目录 `benchmark/ArduPilot/` 和 `benchmark/PX4/` 是依据当前官方材料建立的证据优先数据集，继续原样保留。本目录是独立的 PGFuzz 历史性质数据集，不覆盖、不合并原有性质状态。

## 5. 冻结版本

完整机器可读信息见 `source_manifest.json`。核心版本为：

- PGFuzz PDF：18 页，SHA-256 `bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa94c90d7fcd`；
- PGFuzz 仓库：`7eaebf21116087249b8329d4ba7337a24a34ecb9`；
- ADGFuzz PDF：19 页，SHA-256 `bb86bc3177c4e4bf2c8fe73e14e99760ab4dd662deb7902afafb502cfacaed72`；
- ADGFuzz 仓库：`203fce3f4265241340ed62b9be90aec1da0afa37`；
- ArduPilot：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`；
- PX4 v1.17.0：`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`。

