# PGFuzz-MTL51 性质记录完整字段字典

## 一、先解释本文件使用的英文技术词

- `PGFuzz` 是 `Policy-Guided Fuzzing`，中文为“性质或策略引导的模糊测试”；本目录保存其论文表十二的 51 条历史性质种子。
- `JSON` 是 `JavaScript Object Notation`，中文为“JavaScript 对象表示法”；本任务用它保存可由程序读取的嵌套审计记录，文件扩展名为 `.json`。
- `JSON Schema` 中的 `Schema` 是“数据结构模式”；它可规定字段是否必需、值的类型及嵌套结构。结构校验通过只说明记录符合数据接口，不证明公式语义正确、源码绑定等价或飞控满足性质。
- `field dictionary` 中文为“字段字典”；本文件逐项解释机器字段名、实际值类型、当前常见值以及人工审核时的防误读边界。
- `Markdown` 是轻量标记文本格式；本文件是便于人工阅读的版本，完整机器可读版本见 [FIELD_DICTIONARY.json](FIELD_DICTIONARY.json)。

本字段字典的结论边界：字段覆盖完整、路径存在、散列一致或自动校验通过，都不能提升任何性质的实现符合性。所有性质的实现符合性仍是 `NOT_ASSESSED`，即“未评估”，不表示满足或违反。

## 二、覆盖范围与值类型

- 当前性质记录：51 个 JSON 文件。
- 递归收集的唯一字段键：221 个。
- 每个字段只在字典中登记一次；同名字段若在不同嵌套路径复用，中文含义会明确提示必须结合完整路径读取。
- 大写状态名和输入类别名也可能成为 JSON 对象中的动态键：它们的值有时是中文图例，有时是计数，不能脱离父对象解释。

值类型图例：

- `string`：字符串，即文本值。
- `integer`：整数。
- `number`：一般数值，当前主要是浮点时间值。
- `boolean`：布尔值，只能为真或假。
- `array`：数组，即保持顺序的多项值集合。
- `object`：对象，即由子字段组成的键值结构。
- `null`：空值，表示该位置明确没有可用具体值；不能自动解释为零、假或空字符串。

## 三、完整字段表

### 机器状态值与动态统计键

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `CANDIDATE_ASSOCIATION` | 候选关联状态键；表示作者把输入列入某条性质，但没有公开逐项因果或数据流证明。 | 字符串、整数；当前常见值：候选关联；作者列入输入文件，但未公开逐项因果证明、238、239 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `COMMAND_XML_DEFINITION_FOUND` | 命令 XML 定义已找到状态键；只表示冻结 MAVLink 方言中存在同名命令定义。 | 字符串、整数；当前常见值：当前 MAVLink 命令 XML 定义已找到、47、20、46、4、34 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `COMMAND_XML_DEFINITION_NOT_FOUND` | 命令 XML 定义未找到状态键；表示冻结 MAVLink 方言搜索中未找到同名定义。 | 字符串、整数；当前常见值：当前 MAVLink 命令 XML 定义未找到、13、3 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `CONDITIONAL` | 有条件可观测状态键；只有消息启用、实例、有效性、配置或运行阶段条件成立时才能观测。 | 整数、字符串；当前常见值：1、有条件可观测；消息、实例、有效性或配置条件必须成立、2、4 | 缺少启用、有效性或运行阶段证据时，观测结论应为不可用或无结论。 |
| `CURRENT_DEFINITION_NOT_FOUND` | 当前定义未找到状态键；表示冻结源码和元数据搜索没有定位到可靠定义。 | 字符串、整数；当前常见值：当前定义未找到、4、2、1、5、6 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `DERIVED` | 派生可观测状态键；需要组合字段、保存历史样本或执行换算才能得到命题值。 | 整数、字符串；当前常见值：1、派生可观测；需要组合字段、保存历史或换算、2 | 必须保存换算、输入字段和历史窗口，不能把派生值冒充直接源码变量。 |
| `DIRECT` | 直接可观测状态键；列出的消息字段直接携带所需值，但仍需解码、关联和有效性检查。 | 整数、字符串；当前常见值：1、直接可观测；字段直接携带所需值，仍需解码和有效性检查、2、3 | 只表示字段承载能力；仍要检查消息实际出现、单位、枚举、时间和关联键。 |
| `EXACT` | 精确绑定状态键；只保证某条绑定记录的局部实体身份和该行局部含义有直接证据。 | 整数、字符串；当前常见值：1、精确绑定；该绑定行的局部实体身份及该行所述局部含义有直接证据，不代表整条命题或性质正确、3、2 | 只能作为局部绑定证据；禁止据此宣称整个命题等价或固件符合性质。 |
| `EXACT_CURRENT_DEFINITION` | 当前同名定义已找到状态键；表示冻结版本中定位到同名参数或输入定义。 | 字符串、整数；当前常见值：当前同名定义已找到、136、137、122、100、141 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `EXPLICIT_PRECONDITION` | 明确前置设置状态键；表示作者旧制品显式要求先设置该输入。 | 字符串、整数；当前常见值：明确前置设置；只证明作者旧实验先设置该值、5 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `HISTORICAL_PROPERTY_SEED` | 历史性质种子状态键；性质来自 PGFuzz 论文，尚未由当前官方材料重新确认为现行要求。 | 字符串；当前常见值：历史性质种子；来自论文，尚未被当前官方材料重新确认为规范 | 防止把论文历史公式误标成当前 ArduPilot/PX4 官方规范。 |
| `INSTRUMENTATION_REQUIRED` | 需要插桩状态键；标准 MAVLink 没有等价外部字段，需要内部订阅或观测探针。 | 字符串、整数；当前常见值：需要插桩；标准 MAVLink 没有等价字段、2、1 | 没有内部探针时不能声称该命题已从标准 MAVLink 轨迹判定。 |
| `InputC` | 命令输入类别键；包括命令、模式切换或遥控输入。 | 字符串、整数；当前常见值：命令、模式或遥控输入、52、25、51、9、53 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `InputE` | 环境输入类别键；包括软件在环仿真中的传感器、天气或故障扰动输入。 | 字符串、整数；当前常见值：仿真环境或故障输入、124、125、86、77、32 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `InputP` | 配置参数输入类别键；表示通过飞控参数接口提供的输入。 | 字符串、整数；当前常见值：配置参数输入、62、63、30、31 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `MODELLED` | 建模绑定状态键；实体可定位，但需要单位、坐标、上下文、历史或语义假设。 | 字符串、整数；当前常见值：建模绑定；需要单位、坐标、上下文或历史样本解释、3、2、4、5、1 | 审核时必须读取转换和假设；禁止把建模近似当作精确等价。 |
| `NOT_ASSESSED` | 未评估实现符合性状态键；不表示满足，也不表示违反。 | 字符串；当前常见值：未评估；不表示当前固件满足或违反该性质 | 这是全局符合性边界；任何验证通过计数都不得改变该值。 |
| `PRECONDITION` | 前置输入类别键；表示作者制品中保存的测试前设置。 | 字符串、整数；当前常见值：作者制品明确保存的前置设置、5 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `PRIMARY_SELECTED` | 唯一主语义组已选状态键；当前没有其他互斥候选组。 | 字符串；当前常见值：已选定唯一主语义组 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `PRIMARY_WITH_ALTERNATIVES` | 主语义已选但仍有替代组状态键；替代组默认不同时参与判真。 | 字符串；当前常见值：已选主语义组，同时保留互斥替代解释 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `RENAMED_CURRENT_DEFINITION` | 当前更名或迁移定义已找到状态键；严格等价程度还要结合匹配置信度。 | 字符串、整数；当前常见值：当前更名或迁移后的定义已找到、46、22、37、18、19 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `SPECIAL_CONTROL_INPUT` | 特殊控制输入状态键；表示该输入不是普通配置参数。 | 字符串、整数；当前常见值：特殊控制输入；不是普通配置参数、5、6 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |
| `UNRESOLVED` | 未解决状态键；证据不足时保留未知，不猜测实体、数值或可观测性。 | 字符串、整数；当前常见值：未解决；证据不足，禁止猜测、1、2、3 | 该值要求保留未知并停止自动判真，不能用名称相似或经验值补齐。 |
| `UNRESOLVED_PRIMARY` | 主语义未解决状态键；补证前不能计算该原子命题真值。 | 字符串；当前常见值：主语义未解决，补证前不能判真 | 该键可能同时用于状态中文图例或数量统计；必须结合所在 JSON 路径读取，计数不代表性质质量。 |

### 数据集身份、冻结版本与审核边界

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `audit_boundary_zh` | 性质审核边界的中文说明对象。 | 对象；子字段见本字典相应条目 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `commit` | 冻结源码仓库的提交散列标识。 | 字符串；当前常见值：8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e、d6f12ad1c4f70ad3230afd7d86e971421e02fef4 | 确保行号和符号可复核；提交变化后映射必须重新校验。 |
| `conclusion_limit_zh` | 性质绑定汇总结论的中文边界。 | 字符串；当前常见值：绑定只回答实体位置与观测方法，不评估固件是否满足公式。 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `conformance` | 审核边界中关于实现符合性检查范围的说明。 | 字符串；当前常见值：没有执行完整轨迹监测、fuzz campaign 或实现符合性判断。 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `dataset_id` | 本数据集的稳定机器标识符。 | 字符串；当前常见值：PGFUZZ_TABLE_XII_ARDUPILOT_PX4_51 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `dataset_role` | 性质在本数据集中的证据角色。 | 字符串；当前常见值：HISTORICAL_PROPERTY_SEED | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `frozen_current_source` | 当前系统冻结源码身份、提交和范围对象。 | 对象；子字段见本字典相应条目 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `implementation_satisfaction` | 当前固件是否满足性质的评估状态；本数据集固定为未评估。 | 字符串；当前常见值：NOT_ASSESSED | 始终保持 NOT_ASSESSED，源码定位和结构校验都不能提升它。 |
| `path` | 冻结源码或论文文件相对于工作区的路径。 | 字符串；当前常见值：baseline/ardupilot、baseline/px4 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `property_id` | 性质的稳定机器标识符。 | 字符串；当前常见值：A.ALT_HOLD1、A.ALT_HOLD2、A.AUTO1 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `requirement_origin` | 审核边界中性质要求来源的说明。 | 字符串；当前常见值：性质来自 PGFuzz 论文表十二，不由当前源码控制流反推。 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `schema_version` | 性质记录数据结构的版本号。 | 字符串；当前常见值：1.0 | 用于选择兼容的读取器和校验规则；版本相同也不证明内容语义正确。 |
| `scope` | 冻结源码绑定覆盖的飞行器类型或组件范围数组。 | 数组；当前长度范围 1–1 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `sha256` | 冻结文件内容的 SHA-256 散列值。 | 字符串；当前常见值：bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa9… | 仅检测内容漂移，不证明文档权威性或公式正确。 |
| `source_binding` | 审核边界中当前源码绑定用途的说明。 | 字符串；当前常见值：当前源码只用于身份、真值条件、有效性和观测方案。 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `static_analysis` | 审核边界中下一阶段静态分析是否已执行的说明。 | 字符串；当前常见值：尚未执行用户下一阶段要求的当前源码依赖静态分析。 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `status_legend_zh` | 当前记录实际使用状态值的中文图例对象。 | 对象；子字段见本字典相应条目 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |
| `system` | 性质所属被测飞控系统。 | 字符串；当前常见值：ArduPilot、PX4 | 用于锁定证据版本和结论边界；结构或版本一致不表示固件满足性质。 |

### 论文公式与官方文档证据

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `binding_formula_interpretation` | 为词项绑定而展开或解释后的公式；不得覆盖论文原样公式。 | 字符串；当前常见值：G((ALT_src = Baro) -> ((ALT_t = ALT_Baro) & (ALT_t != A…、G(((Mode_t = ALT_HOLD) & (Throttle_t = 1500)) -> (ALT_t…、G((Mode_t = AUTO) -> ((RC_roll_t/RC_pitch_t/RC_throttle… | 只用于展开绑定；与论文原式不同时不得覆盖原始证据。 |
| `code` | 论文公式问题的机器可读问题代码。 | 字符串；当前常见值：SOURCE_ABSTRACTION_UNDEFINED、EXACT_PHYSICAL_EQUALITY、PREVIOUS_SAMPLE_NOT_TIME | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `description_en` | PGFuzz 论文表十二中的最短完整英文性质描述。 | 字符串；当前常见值：If the altitude source is the barometer, the vehicle mu…、If the throttle stick is in the middle (i.e., 1,500) th…、The pilot's roll, pitch and throttle inputs must be ign… | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `description_zh` | 论文英文性质描述的中文解释。 | 字符串；当前常见值：高度来源为气压计时采用气压计高度而非 GPS 高度。、定高模式中油门位于中值时保持高度。、自动模式忽略横滚、俯仰和油门输入，但允许偏航覆盖。 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `document_id` | 一条官方文档语境记录的唯一标识符。 | 字符串；当前常见值：ARD-DOC-ALTHOLD、ARD-DOC-AUTO、ARD-DOC-BRAKE | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `evidence_role` | 官方文档在本性质中的证据角色状态。 | 字符串；当前常见值：CONTEXT_ONLY_NOT_CURRENT_REQUIREMENT_CONFIRMATION | 官方页面仅作语境时，禁止把它写成对论文公式的当前规范确认。 |
| `explanation_zh` | 论文公式问题代码的中文解释。 | 字符串；当前常见值：高度来源、Baro/GPS 高度的坐标系和融合语义没有定义。、要求物理状态精确等于常量或参数，未给容差和采样语义。、t-1 仅是上一观测索引，论文没有给出固定采样周期。 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `inherits_from` | 论文该行继承公式结构的来源性质标识；无继承时为空。 | 空值、字符串；当前常见值：null、A.ALT_HOLD2、A.LOITER1、A.CIRCLE1、A.CIRCLE2、A.CIRCLE3 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `issues` | 该性质已登记论文公式问题的代码和解释数组。 | 数组；当前长度范围 0–4 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `official_context_limit_zh` | 官方文档语境不能被当作当前性质确认的中文限制。 | 字符串；当前常见值：官方页面只用于解释模式、参数或消息的当前语境；没有逐句重新提取并确认本论文公式，因此本条仍是历史性质种子。 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `official_document_context` | 与该性质相关的官方文档语境记录数组。 | 数组；当前长度范围 1–2 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `page_count` | 论文 PDF 的总页数。 | 整数；当前常见值：18 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `page_one_based` | 证据在论文中的一基页码。 | 整数；当前常见值：18 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `paper` | 冻结论文文件身份对象。 | 对象；子字段见本字典相应条目 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `paper_evidence` | 性质对应的论文原文、公式、模板和问题对象。 | 对象；子字段见本字典相应条目 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `paper_formula_transcription` | 严格按论文表十二转录的公式原文。 | 字符串；当前常见值：G((ALT_src = Baro) -> ((ALT_t = ALT_Baro) & (ALT_t != A…、G(((Mode_t = ALT_HOLD) & (Throttle_t = 1500)) -> (ALT_t…、G((Mode_t = AUTO) -> ((RC_roll_t/RC_pitch_t/RC_throttle… | 这是不可静默修复的论文证据基线；所有解释必须与其分栏。 |
| `paper_order` | 性质在论文表十二中的顺序号。 | 整数；当前常见值：9、10、20 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `property_ids` | 官方文档语境记录覆盖的性质标识数组。 | 数组；当前长度范围 1–14 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `property_issue_codes` | 原子命题所属性质继承的论文问题代码数组。 | 数组；当前长度范围 0–4 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `release` | 冻结软件发布版本标签。 | 字符串；当前常见值：v1.17.0 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `relevance_zh` | 官方文档与性质相关性的中文说明。 | 字符串；当前常见值：解释中位油门保持高度及气压计通常作为主要高度来源；不证明融合高度与气压/GPS 高度严格相等或不等。、解释自动执行任务的总体语义；不支持所有遥控轴逐采样严格不变的历史表达。、解释尽快停止、忽略输入和需要位置估计；没有给位置严格相等或每条性质专用 k。 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `row_property_id` | 论文表格行对应的性质标识符。 | 字符串；当前常见值：A.ALT_HOLD1、A.ALT_HOLD2、A.AUTO1 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `specific_current_fields` | 官方文档语境记录特别涉及的当前参数、消息或状态字段数组。 | 数组；当前长度范围 0–6 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `table` | 论文证据所在表格名称。 | 字符串；当前常见值：Table XII | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `template` | PGFuzz 论文采用的 T1、T2 或 T3 公式模板标签。 | 字符串；当前常见值：T3、T1、T2、T1&T3 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `title_en` | 官方文档页面的英文标题原文。 | 字符串；当前常见值：Altitude Hold Mode — Copter documentation、Auto Mode — Copter documentation、Brake Mode — Copter documentation | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `title_zh` | 官方文档页面标题的中文说明。 | 字符串；当前常见值：ArduPilot Copter 定高模式、ArduPilot Copter 自动任务模式、ArduPilot Copter 制动模式 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `url` | 官方文档页面的网络地址。 | 字符串；当前常见值：https://ardupilot.org/copter/docs/altholdmode.html、https://ardupilot.org/copter/docs/auto-mode.html、https://ardupilot.org/copter/docs/brake-mode.html | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |
| `version_scope` | 官方文档语境记录适用的版本范围。 | 字符串；当前常见值：current Copter documentation observed 2026-07-18、PX4 v1.17 | 用于追溯论文或官方语境；官方语境不能自动确认论文公式为当前规范。 |

### 时间窗口与相邻观测

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `additional_limit_zh` | 时间上界或参数迁移的额外中文限制说明。 | 字符串；当前常见值：COM_POS_FS_DELAY 是历史 PX4 参数；当前冻结版本未找到等价定义。即使保留加法表达式，也不能… | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `cancel_reset_zh` | 时间义务取消、重置和重复触发语义的中文说明。 | 字符串；当前常见值：论文未说明取消、重置或重复触发语义。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `clock_carrier_zh` | 时间值由哪种时间戳或观察时刻承载的中文说明。 | 字符串；当前常见值：论文未公开是仿真时钟、机载启动时钟还是观察端到达时钟。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `clock_domain` | 时间比较采用的时钟域状态。 | 字符串；当前常见值：TRACE_ORDER、UNSPECIFIED_BY_PAPER | 时钟域未知时不能比较来自不同时间载体的时间差。 |
| `concrete_time_policy_zh` | 本数据集允许保存哪些具体时间值的中文策略。 | 字符串；当前常见值：仅保存论文明确写出的 2.5 秒；k、参数加 k 和 t-1 均不补人工秒数。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `concrete_value_status` | 时间边界是否具有可追溯具体数值的状态。 | 字符串；当前常见值：UNKNOWN、AVAILABLE | UNKNOWN 时禁止产生数值实例；AVAILABLE 仍必须检查来源类型。 |
| `elapsed_time_value` | 相邻观测关系对应的实际经过时间值；未知时为空。 | 空值；当前常见值：null | 空值表示没有可追溯经过时间，不能把样本索引解释为秒。 |
| `end_event_zh` | 时间窗口终点事件的中文说明。 | 字符串；当前常见值：相应 eventually 后件第一次成立的观测点。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `explicit_eventually_windows` | 公式中显式有界最终发生时间窗口的记录数组。 | 数组；当前长度范围 0–3 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `freshness_requirement_zh` | 相邻样本或观测必须满足的数据新鲜度条件。 | 字符串；当前常见值：两个样本必须属于同一运行、同一坐标系和同一有效性阶段；跨重置比较无结论。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `interval_brackets_zh` | 论文时间区间括号及监视器转换状态的中文说明。 | 字符串；当前常见值：论文印刷使用方括号；本数据集保留原样，尚未据此运行监视器语义转换。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `lower_bound` | 一个显式时间窗口的下界记录对象。 | 对象；子字段见本字典相应条目 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `meaning_zh` | 相邻观测关系的中文语义。 | 字符串；当前常见值：t-1 表示监视轨迹中同一信号的上一有效样本，不表示一秒以前。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `measurement_uncertainty_zh` | 时间测量、采样和传输不确定度的中文说明。 | 字符串；当前常见值：UNKNOWN；论文未公开采样周期、传输延迟和测量不确定度。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `operator` | 时间逻辑运算符机器符号。 | 字符串；当前常见值：F | 必须按对应时间逻辑语义解释，不能把字符 F 当作普通函数或字段。 |
| `operator_zh` | 时间逻辑运算符的中文含义。 | 字符串；当前常见值：最终发生：要求后件在印刷区间内某次成立 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `previous_observation_contract` | 公式中上一有效观测关系的契约对象；未使用时为空。 | 空值、对象；当前常见值：null | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `provenance_zh` | 时间数值或符号上界来源的中文溯源说明。 | 字符串；当前常见值：数值 2.5 和秒单位直接来自 PGFuzz 表十二该行公式与描述；不是当前固件参数。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `raw` | 时间边界操作数的论文原始文本。 | 字符串；当前常见值：0、k、2.5、COM_POS_FS_DELAY+k | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `raw_fragment` | 从论文公式识别出的完整时间窗口片段。 | 字符串；当前常见值：F_[0,k]、F_[0,2.5]、F_[0,COM_POS_FS_DELAY+k] | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `relation_type` | 相邻观测关系的机器类型。 | 字符串；当前常见值：PREVIOUS_OBSERVATION | PREVIOUS_OBSERVATION 只给顺序，不给固定经过时间。 |
| `source_type` | 时间边界数值或符号的来源类型状态。 | 字符串；当前常见值：PAPER_LITERAL、SYMBOLIC_UNRESOLVED | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `start_event_zh` | 时间窗口起点事件的中文说明。 | 字符串；当前常见值：论文只给当前前件成立的采样点，没有更精细的触发关联事件。 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `temporal_semantics` | 性质的时间窗口和相邻观测语义对象。 | 对象；子字段见本字典相应条目 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `unit` | 时间边界的单位说明。 | 字符串；当前常见值：秒（按论文的经过时间轴解释时）、秒（仅在论文实验确实使用秒时；当前具体值不可得）、s | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `upper_bound` | 一个显式时间窗口的上界记录对象。 | 对象；子字段见本字典相应条目 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `uses_previous_observation` | 公式是否使用上一有效观测记号。 | 布尔值；当前常见值：False、True | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |
| `value` | 时间边界经证据确认的具体数值；未知时为空。 | 整数、空值、数值；当前常见值：0、null、2.5 | 用于保持时间来源、时钟和相邻样本边界；缺值时不得人工补秒数。 |

### 原子命题、源码绑定与外部观测

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `all_candidate_observation_fields` | 某原子命题全部候选语义组可能使用的观测字段集合。 | 数组；当前长度范围 0–8 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `alternative_binding_count` | 整条性质中互斥备选源码绑定标识符的数量。 | 整数；当前常见值：5、0、2 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `alternative_source_bindings` | 某原子命题未被当前选择、但保留供人工切换的源码绑定记录数组。 | 数组；当前长度范围 0–12 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `alternative_term_binding_ids` | 某原子命题互斥备选词项绑定标识符数组。 | 数组；当前长度范围 0–12 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `ap_count` | 性质包含的原子命题出现次数。 | 整数；当前常见值：3、5、2、4、8 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `ap_id` | 原子命题出现的唯一标识符。 | 字符串；当前常见值：A.ALT_HOLD1-AP01、A.ALT_HOLD1-AP02、A.ALT_HOLD1-AP03 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `atomic_propositions` | 性质的原子命题审计记录数组。 | 数组；当前长度范围 2–8 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_group_summary` | 原子命题各词项候选语义组及选择情况的汇总数组。 | 数组；当前长度范围 1–12 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_id` | 一条当前源码词项绑定记录的唯一标识符。 | 字符串；当前常见值：ARD-TB-022、ARD-TB-023、ARD-TB-024 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_kind` | 源码绑定的实体种类，例如状态字段、函数返回、赋值或参数消费点。 | 字符串；当前常见值：STATE_FIELD、FUNCTION_RETURN、SELECTION_GUARD | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_role` | 源码绑定在候选组中的角色：主真值、辅助证据或替代语义。 | 字符串；当前常见值：PRIMARY_VALUE、SUPPORTING_EVIDENCE、ALTERNATIVE_SEMANTICS | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_selection_reason_zh` | 为何为该原子命题选择当前候选语义组的中文理由。 | 字符串；当前常见值：ALT_src：性质询问实际高度来源，因此选择 EKF 运行时 activeHgtSource，而不是三套配置…、ALT_t：该词项只有一个当前主语义组，按其真值、有效性和观测限制使用；ALT_Baro：该词项只有一个当前主…、ALT_t：该词项只有一个当前主语义组，按其真值、有效性和观测限制使用；ALT_GPS：该词项只有一个当前主语… | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_selection_status` | 原子命题主语义组的选择状态。 | 字符串；当前常见值：PRIMARY_WITH_ALTERNATIVES、PRIMARY_SELECTED、UNRESOLVED_PRIMARY | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_status` | 原子命题或汇总对象的源码绑定证据状态。 | 字符串；当前常见值：MODELLED、EXACT、UNRESOLVED | 这是证据绑定分级，不是性质判定结果。 |
| `binding_status_counts` | 按绑定状态统计的原子命题数量对象。 | 对象；子字段见本字典相应条目 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `binding_status_reason_zh` | 原子命题获得当前绑定状态的中文理由。 | 字符串；当前常见值：需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。、本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。、包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。、论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。、命题实体可定位，但所在性质存在论文公式冲突，不能据此修复整条公式。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `candidate_group` | 同一论文词项的一种互斥候选语义组标识符。 | 字符串；当前常见值：ALT_src:runtime_active、Baro:source_enum、ALT_src:configured_source_set_1 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `confidence` | 单条源码绑定记录的证据置信状态。 | 字符串；当前常见值：MODELLED、EXACT、UNRESOLVED | 这是单条绑定记录置信度，不得与整条命题或性质状态混淆。 |
| `confidence_reason_zh` | 单条源码绑定为何获得当前置信状态的中文理由。 | 字符串；当前常见值：运行字段明确，但当前活动估计器和多核选择需要上下文。、当前内联访问器直接返回每个核的活动源集。、活动源集到垂直位置配置的访问路径直接可证。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `current_parameter_name` | 源码词项绑定对应的当前飞控配置参数名；空值表示不是参数绑定。 | 字符串；当前常见值：、EK3_SRC1_POSZ、EK3_SRC2_POSZ | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `data_type` | 当前源码绑定实体的程序数据类型。 | 字符串；当前常见值：AP_NavEKF_Source::SourceZ enum、uint8_t source-set index、SourceZ enum | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `evaluation_plan_zh` | 如何依据绑定、有效性和观测换算判定原子命题的中文方案。 | 字符串；当前常见值：按所列源码实体、真值条件、有效性条件和观测换算判定。、解码当前模式字段并与当前枚举比较；若还有其他词项，再按各自绑定条件合取。、保留原式和全部候选绑定；缺失定义或数值补证前不得给真值。、从当前运行实例读取参数值并按元数据单位解释；不要硬编码作者历史默认值或源码默认值。、明确选择内部目标量或实际测量量，保持前后样本定义一致，并按半径符号解析方向。、读取实际垂直速度，执行厘米/秒到米/秒及 NED 符号转换；参数使用本次运行实际值而非默认值。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `function_context` | 源码绑定所在函数的完整上下文签名。 | 字符串；当前常见值：、AP_NavEKF_Source::getActiveSourceSet(uint8_t) const、AP_NavEKF_Source::getPosZSource(uint8_t) const | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `mavlink_message_fields` | 单条源码绑定可使用的 MAVLink 消息字段原文。 | 字符串；当前常见值：、PARAM_VALUE.param_id=EK3_SRC1_POSZ,param_value、PARAM_VALUE.param_id=EK3_SRC2_POSZ,param_value | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `mavlink_observability` | 原子命题或源码绑定的 MAVLink 外部可观测性状态。 | 字符串；当前常见值：INSTRUMENTATION_REQUIRED、DIRECT、CONDITIONAL、DERIVED、UNRESOLVED | 这是观测分级，不是实现符合性；必须同时读取消息字段和限制。 |
| `mavlink_observation_bindings` | 原子命题选定源码绑定与其消息字段的结构化对应数组。 | 数组；当前长度范围 0–6 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `mavlink_observation_fields` | 原子命题当前选定语义组使用的去重消息字段数组。 | 数组；当前长度范围 0–6 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `message_fields_raw` | 结构化观测对应的原始消息字段字符串。 | 字符串；当前常见值：GLOBAL_POSITION_INT.relative_alt,time_boot_ms、GLOBAL_POSITION_INT.relative_alt、GPS_RAW_INT.alt,time_usec,fix_type | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `observability_counts` | 按 MAVLink 可观测性状态统计的原子命题数量对象。 | 对象；子字段见本字典相应条目 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `observation_conversion_zh` | 从消息字段换算为命题值的中文方法。 | 字符串；当前常见值：、按 SourceZ 枚举解码参数值。、relative_alt 从毫米除以 1000 得到米。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `observation_limit_zh` | 外部观测不能证明或无法区分的中文限制。 | 字符串；当前常见值：标准 MAVLink 没有直接发布 activeHgtSource。、标准 MAVLink 不发布每个 EKF 核的活动源集。、 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `property_binding_summary` | 整条性质的绑定、观测和数量汇总对象。 | 对象；子字段见本字典相应条目 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `role` | 原子命题在公式中的角色机器值。 | 字符串；当前常见值：antecedent、consequent、negated_consequent、consequent_disjunct、condition_from_description、antecedent_from_description | 决定该命题是触发还是义务；角色来自描述时不能冒充印刷公式内容。 |
| `selected_binding_count` | 整条性质当前选定源码绑定标识符的数量。 | 整数；当前常见值：13、8、15 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `selected_source_bindings` | 某原子命题当前用于判真的源码绑定记录数组。 | 数组；当前长度范围 1–6 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `selected_term_binding_ids` | 某原子命题当前选择的词项绑定标识符数组。 | 数组；当前长度范围 1–6 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `selection_note_zh` | 单条源码绑定参与候选组选择的中文说明。 | 字符串；当前常见值：该行是其候选组的核心真值实体；只有该组被性质选择时才参与判真。、该行只说明形成、消费、关联或发送路径，不会单独改善主值的可观测性。、该行属于互斥替代解释；只有人工切换到本候选组后才参与判真。、配置源只是实际源的候选，不能替代 activeHgtSource。、只在公式把 Command_t 定义为“已接受命令”时选用。、只在公式把 Command_t 定义为“正在执行起飞”时选用。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `source_end_line` | 源码证据范围的结束行号；与起始行共同形成闭区间。 | 整数；当前常见值：1481、68、247 | 防止只引用范围首行而遗漏赋值、条件或函数上下文。 |
| `source_line` | 源码证据范围的起始行号。 | 整数；当前常见值：1481、66、239 | 必须与 source_end_line、source_path 和冻结提交一起定位证据。 |
| `source_path` | 源码绑定证据相对于工作区的冻结文件路径。 | 字符串；当前常见值：baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_core…、baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source…、baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source… | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `symbol` | 当前源码变量、字段、函数、表达式或参数的原样符号。 | 字符串；当前常见值：AP_NavEKF3_core::activeHgtSource、AP_NavEKF_Source::getActiveSourceSet(core_index)、AP_NavEKF_Source::getPosZSource(core_index) | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `term` | 论文公式中的状态、参数、命令或环境词项。 | 字符串；当前常见值：ALT_src、Baro、ALT_t | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `term_binding_ids` | 原子命题涉及的全部词项源码绑定标识符数组。 | 数组；当前长度范围 1–14 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `terms` | 原子命题拆分出的论文词项数组。 | 数组；当前长度范围 1–3 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `truth_condition_zh` | 单条源码绑定怎样判定真假的中文条件。 | 字符串；当前常见值：读取当前 EKF3 核实际生效的高度源。、根据当前 EKF 核索引读取正在使用的源集编号。、从活动源集读取垂直位置配置，并在没有气压计实例时把 BARO 配置退化为 NONE。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `truth_meaning_zh` | 原子命题表达式的中文真值含义。 | 字符串；当前常见值：论文抽象的高度来源被标记为气压计。、当前高度严格等于气压计高度。、当前高度不等于 GPS 高度。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `unit_coordinate` | 源码绑定值的单位、坐标系或参考面说明。 | 字符串；当前常见值：、0..2 selecting EK3 source set 1..3、0:none, 1:barometer, 2:rangefinder, 3:GPS, 4:beacon, 6:… | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `validity_freshness_zh` | 源码绑定值有效、同源且足够新所需的中文条件。 | 字符串；当前常见值：必须知道当前活动 EKF 核；参数配置源不等于运行时实际源。、必须与同一 core_index 的 getPosZSource() 和 activeHgtSource 配对。、返回的是活动源集的配置选择；selectHeightForFusion() 仍可能按新鲜度和回退规则形成实际 … | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |
| `version_note_zh` | 源码绑定相对历史论文或版本迁移的中文说明。 | 字符串；当前常见值：、历史 LAND_SPEED_HIGH 厘米/秒迁移到 LAND_SPD_HIGH_MS 米/秒。、历史 LAND_SPEED 厘米/秒迁移到 LAND_SPD_MS 米/秒。、历史 RTL_ALT 厘米值迁移到 RTL_ALT_M 米值。、历史 PILOT_SPEED_UP 迁移到 PILOT_SPD_UP。、旧 MIS_LTRMIN_ALT 当前不存在；源码语义相近，但没有本地历史证明一对一迁移。 | 用于复核命题真值实体和观测路径；源码绑定不能反向生成要求或符合性结论。 |

### PGFuzz 作者依赖输入制品

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `artifact_column_6_interpretation` | PGFuzz 参数文件第六列的解释状态。 | 字符串；当前常见值：AUTHOR_PARSER_CALLS_UNITS_BUT_ARTIFACT_VALUES_MAY_BE_IN… | 防止把作者可能表示步进量的第六列无依据地写成单位。 |
| `artifact_column_6_raw` | PGFuzz 参数文件第六列的原始文本。 | 字符串；当前常见值：1、0.1、0.5 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_default_raw` | 作者制品保存的默认值原文；在参数值契约对象中同名键保存该字段的中文解释。 | 字符串；当前常见值：作者旧制品保存的默认栏，不等于当前源码默认值。、0、1500 | 必须结合完整 JSON 路径读取；作者旧默认不能替代当前默认或运行值。 |
| `artifact_file_sha256` | 作者输入制品文件的 SHA-256 内容散列值。 | 字符串；当前常见值：86cd4587e0e9ca721a0fdbc8b106d5bcc22e620ba91fa585341c8f4…、bcbdf48fcc97bf2129f33a8bd125d010defe4dc080808b210949424…、8fcbc9937327d538a6884892da2be67ab85fc79070212e9364171e6… | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_max_raw` | 作者制品保存的最大值原文。 | 字符串；当前常见值：X、2、10 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_min_raw` | 作者制品保存的最小值原文。 | 字符串；当前常见值：X、0、200 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_name` | 作者制品中的历史输入名称。 | 字符串；当前常见值：GND_TEMP、GND_ALT_OFFSET、GND_PRIMARY | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_numeric_id_raw` | 作者制品中命令或输入的数字标识原文。 | 字符串；当前常见值：、2、208 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_policy_directory` | 该逻辑性质读取的 PGFuzz 作者性质目录名。 | 字符串；当前常见值：A.ALT_HOLD1、A.ALT_HOLD2、A.AUTO1 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_precondition_value_raw` | 作者前置条件文件保存的目标值原文。 | 字符串；当前常见值：、1、10、27、9 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_raw` | 作者输入文件整行原文。 | 字符串；当前常见值：GND_TEMP,X,0,X,X,1、GND_ALT_OFFSET,X,0,X,X,0.1、GND_PRIMARY,X,0,0,2,1 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_raw_variants` | 同一历史输入身份在作者制品中出现过的不同原始行集合。 | 字符串；当前常见值：Flight_Mode,1 \|\| Flight_Mode,11 \|\| Flight_Mode,13 \|\| Fl…、MAV_CMD_COMPONENT_ARM_DISARM,400、MAV_CMD_CONDITION_DELAY,112 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_reboot_raw` | 作者参数文件保存的重启标记原文。 | 字符串；当前常见值：X、TRUE、 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_source_files` | 同一历史输入身份出现过的作者制品源文件集合。 | 字符串；当前常见值：baseline/pgfuzz/ArduPilot/policies/A.ALT_HOLD1/cmds.txt…、baseline/pgfuzz/ArduPilot/policies/A.ALT_HOLD1/cmds.txt…、baseline/pgfuzz/ArduPilot/policies/A.ALT_HOLD1/cmds.txt… | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_source_line` | 作者制品原始输入所在的一基行号。 | 整数；当前常见值：1、2、3 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `artifact_source_path` | 作者制品原始输入所在的相对文件路径。 | 字符串；当前常见值：baseline/pgfuzz/ArduPilot/policies/A.ALT_HOLD1/paramete…、baseline/pgfuzz/ArduPilot/policies/A.ALT_HOLD1/cmds.txt、baseline/pgfuzz/ArduPilot/policies/A.ALT_HOLD1/envs.txt | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `association_count` | 某性质包含的作者性质—输入关联总行数。 | 整数；当前常见值：238、239、173 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `association_id` | 一条性质—作者输入关联的唯一标识符。 | 字符串；当前常见值：A.ALT_HOLD1:InputP:0001、A.ALT_HOLD1:InputP:0002、A.ALT_HOLD1:InputP:0003 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `association_occurrences` | 某去重输入身份在全部性质关联中出现的次数。 | 整数；当前常见值：36、22、30 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `author_dependency_summary` | 某性质作者候选依赖输入的汇总对象。 | 对象；子字段见本字典相应条目 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `author_input_classes` | 某公式直接参数在作者输入文件中出现过的输入类别集合。 | 字符串；当前常见值：、InputP | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `author_input_dependencies` | 该性质全部作者输入关联记录数组；保留重复行。 | 数组；当前长度范围 50–251 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `by_current_identity_status` | 作者输入关联按当前身份状态统计的数量对象。 | 对象；子字段见本字典相应条目 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `by_dependency_strength` | 作者输入关联按依赖证据强度统计的数量对象。 | 对象；子字段见本字典相应条目 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `by_input_class` | 作者输入关联按输入类别统计的数量对象。 | 对象；子字段见本字典相应条目 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `claim_limit_zh` | 作者依赖输入汇总能够支持何种结论的中文限制。 | 字符串；当前常见值：PGFuzz 输入文件是高召回候选关联。除明确前置设置外，公开制品没有给出每行到命题的完整数据流证明。 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `dependency_claim_limit_zh` | 单条作者输入关联能够支持何种依赖结论的中文限制。 | 字符串；当前常见值：作者 policy 文件中的高召回候选关联；没有逐项公开真实数据依赖证明。、作者制品明确要求先设置的值；只对旧制品实验流程成立。 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `dependency_evidence` | 作者输入关联的证据来源类别。 | 字符串；当前常见值：PGFUZZ_ARTIFACT_ASSOCIATION | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `dependency_strength` | 作者输入关联的依赖证据强度状态。 | 字符串；当前常见值：CANDIDATE_ASSOCIATION、EXPLICIT_PRECONDITION | 候选关联和明确前置设置都不是当前源码因果依赖证明。 |
| `formula_parameter` | 论文公式直接出现的配置参数词项。 | 字符串；当前常见值：CHUTE_ALT_MIN、FS_EKF_ACTION、LAND_SPEED_HIGH | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `formula_parameters` | 该性质全部公式直接参数的当前身份与数值证据数组。 | 数组；当前长度范围 0–2 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `input_class` | 作者输入类别机器值。 | 字符串；当前常见值：InputP、InputC、InputE、PRECONDITION | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `input_class_zh` | 作者输入类别的中文解释和任务作用。 | 字符串；当前常见值：Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。、Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。、前置条件；作者要求先设置该值，再执行目标测试输入。 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `policies` | 某去重输入身份关联到的性质标识集合。 | 字符串；当前常见值：A.ALT_HOLD1\|A.ALT_HOLD2\|A.AUTO1\|A.BRAKE1\|A.CHUTE1\|A.CIR…、A.ALT_HOLD1\|A.ALT_HOLD2\|A.BRAKE1\|A.CHUTE1\|A.DRIFT1\|A.FL…、A.ALT_HOLD1\|A.ALT_HOLD2\|A.AUTO1\|A.BRAKE1\|A.CHUTE1\|A.CIR… | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `policy_id` | 作者依赖记录所属的性质标识符。 | 字符串；当前常见值：A.ALT_HOLD1、A.ALT_HOLD2、A.AUTO1 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `present_in_author_input_files` | 公式直接参数是否出现在作者公开输入文件中。 | 布尔值；当前常见值：False、True | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `shared_artifact_directory_policy_count` | 共享同一作者制品目录的逻辑性质数量。 | 整数；当前常见值：1、3、2 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |
| `unique_input_identity_count` | 某性质作者输入关联去重后的当前输入身份数量。 | 整数；当前常见值：228、229、164 | 用于完整保留作者高召回候选输入；重复、同名或作者列入都不证明因果依赖。 |

### 当前输入身份、参数与命令

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `appears_as_exact_formula_term` | 作者输入名称是否以完全相同词形直接出现在论文公式中。 | 布尔值；当前常见值：False、True | 同名只说明词形覆盖，不证明该输入真实影响命题。 |
| `command_id_consistency` | 作者数字命令标识与当前 MAVLink XML 定义的一致性状态。 | 字符串；当前常见值：NOT_APPLICABLE、MATCH、MISMATCH_OR_MULTIPLE | 数字一致只证明定义对齐；不证明固件处理、接受或执行命令。 |
| `current_alias_evidence` | 历史输入更名或迁移到当前身份的证据位置。 | 字符串；当前常见值：baseline/ardupilot/libraries/AP_Baro/AP_Baro.cpp:103、baseline/ardupilot/libraries/AP_Baro/AP_Baro.cpp:115、baseline/ardupilot/libraries/AP_Baro/AP_Baro.cpp:123 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_alias_note_zh` | 历史名称与当前名称关系的中文说明。 | 字符串；当前常见值：当前地面温度参数位于 BARO 参数组。、当前气压计参数组采用 BARO 前缀；未发现完整单项迁移证明。、当前主气压计参数采用 BARO 前缀。 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_build_inclusion_status` | 当前参数或输入是否纳入冻结构建或运行配置的证据状态。 | 字符串；当前常见值：not_compile_option_resolved、、not_px4_sitl_module_list_resolved、confirmed_by_frozen_runtime_snapshot | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_command_description` | 当前 MAVLink XML 给出的命令英文描述原文。 | 字符串；当前常见值：、Mission item/command to release a parachute or enable/d…、Reply with the version banner. | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_command_id` | 当前 MAVLink XML 中的命令数字标识。 | 字符串；当前常见值：、208、42428 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_command_origin` | 当前命令定义所在的冻结 XML 文件及行号。 | 字符串；当前常见值：、baseline/ardupilot/modules/mavlink/message_definitions/…、baseline/ardupilot/modules/mavlink/message_definitions/… | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_default` | 当前源码或元数据得到的默认值；在参数值契约对象中同名键保存该字段的中文解释。 | 字符串；当前常见值：规范化或经冻结源码复核的当前默认值；其证据状态和源位置必须同时查看。、、EK3_PRIMARY_DEFAULT | 必须结合完整 JSON 路径、证据状态和原始目录值读取，不能与运行值混用。 |
| `current_default_evidence_note_zh` | 当前默认值证据的中文说明和限制。 | 字符串；当前常见值：当前目录没有可用默认值证据。、保存参数目录解析出的字面值或未求值源码表达式；它不是运行值，宏表达式不能冒充已求值数值。、RTL_ALT_M_DEFAULT 在冻结源码中直接定义为 15 米。、FS_THR_VALUE_DEFAULT 在冻结源码中直接定义为 975 微秒 PWM。、AP_PARACHUTE_ALT_MIN_DEFAULT 在冻结源码中直接定义为 10 米。、默认宏为 FS_EKF_Action::LAND；该冻结枚举值对应 1，运行快照也为 1。 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_default_evidence_source` | 当前默认值证据所在的冻结源码或元数据位置。 | 字符串；当前常见值：、baseline/ardupilot/ArduPlane/Parameters.cpp:229、baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3.cpp:… | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_default_evidence_status` | 当前默认值的证据来源与可求值程度状态。 | 字符串；当前常见值：UNKNOWN、SOURCE_METADATA_LITERAL_OR_EXPRESSION、CURATED_FROZEN_SOURCE_RESOLUTION | 区分未知、源码或元数据字面式和人工冻结源码求值；宏原文不能冒充已求值数值。 |
| `current_default_raw_catalog` | 参数目录解析器保留的当前默认值原始文本。 | 字符串；当前常见值：参数目录解析器的原始默认字段；部分 ArduPilot 行带有已知的额外右括号。、、EK3_PRIMARY_DEFAULT) | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_identity_status` | 作者历史输入在当前冻结版本中的身份定位状态。 | 字符串；当前常见值：RENAMED_CURRENT_DEFINITION、EXACT_CURRENT_DEFINITION、CURRENT_DEFINITION_NOT_FOUND、SPECIAL_CONTROL_INPUT、COMMAND_XML_DEFINITION_FOUND、COMMAND_XML_DEFINITION_NOT_FOUND | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_increment` | 当前参数元数据中的建议步进值。 | 字符串；当前常见值：1、0.1、、0.5、0.01、0.05 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_input_identities` | 该性质涉及的去重当前输入身份记录数组。 | 数组；当前长度范围 49–242 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_match_confidence` | 历史输入名称映射到当前身份的匹配置信类别。 | 字符串；当前常见值：CURATED_MIGRATION_MODELLED、EXACT_NAME_DEFINITION、CURATED_RENAME_EXACT、UNRESOLVED、MODELLED_SPECIAL_INPUT、EXACT_NAME_XML_DEFINITION | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_mavlink_parameter_transport` | 当前参数通过 MAVLink 参数协议的观测证据状态。 | 字符串；当前常见值：protocol_capable_runtime_presence_not_observed、、observed_in_frozen_runtime_parameter_download | 参数协议可传输或快照出现都不证明飞行中可写、即时生效或影响目标路径。 |
| `current_maximum` | 当前参数元数据中的最大值原文。 | 字符串；当前常见值：、10、10.0 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_minimum` | 当前参数元数据中的最小值原文。 | 字符串；当前常见值：、0、0.0 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_name` | 作者历史输入对应的当前参数、命令或特殊输入名称。 | 字符串；当前常见值：BARO_GND_TEMP、BARO_ALT_OFFSET、BARO_PRIMARY | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_reboot_required` | 当前参数元数据中的重启要求原文。 | 字符串；当前常见值：、True | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_runtime_capture` | 冻结运行参数值来源的捕获记录标识。 | 字符串；当前常见值：ardupilot-copter-m6、、PX4-M6-MC-SIHSIM-QUADX-I42-20260718 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_runtime_profile` | 冻结软件在环运行所用的机型或配置档案名称。 | 字符串；当前常见值：quad、 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_runtime_value` | 冻结软件在环参数下载中的实际值；在参数值契约对象中同名键保存该字段的中文解释。 | 字符串；当前常见值：冻结 SITL 参数下载中的实际值，只代表该运行配置。、0.0、0 | 只代表指定冻结运行快照，不能当作不可修改的默认值或所有运行通用值。 |
| `current_source_location_confidence` | 当前源码或元数据位置定位的证据置信状态。 | 字符串；当前常见值：unresolved、exact_metadata_unique、、exact_metadata_multiple、exact_definition_unique、exact_definition_curated | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_source_locations` | 当前参数、命令或输入定义的一个或多个冻结源码位置。 | 字符串；当前常见值：、baseline/ardupilot/ArduPlane/Parameters.cpp:229、baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3.cpp:… | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_type` | 当前参数或输入的类型元数据。 | 字符串；当前常见值：not_exposed_by_param_metadata_parser、、Float、enum、float、bitmask | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `current_units` | 当前参数元数据中的单位原文。 | 字符串；当前常见值：degC、m、 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `historical_current_relation` | 论文历史词项与当前源码实体之间的关系状态。 | 字符串；当前常见值：NOT_APPLICABLE、EXACT_SAME_NAME、RENAMED_AND_SCALED_0.01、REMOVED_NO_EQUIVALENT、NON_EQUIVALENT_CANDIDATE、SEMANTIC_SUCCESSOR_NOT_PROVEN_RENAME | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `identity_limit_zh` | 当前输入身份映射能够支持何种结论的中文限制。 | 字符串；当前常见值：参数身份和定义位置已找到；这不证明它与该性质存在真实数据依赖，也未执行写入变更测试。、当前只发现弃用槽位，没有可证明等价的现行参数。、只确认协议 XML 定义；未由此证明当前飞控构建接受、执行或影响该性质。、当前冻结参数目录中没有找到可信同名或重命名定义；没有使用字符串相似度猜测。、当前固定 MAVLink XML 未找到同名命令；没有据此猜测替代命令。、该参数在 PX4 1.16 发行说明中已删除，不能自动用其他估计器超时参数替代。 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `parameter_value_contract_zh` | 作者默认、当前默认、运行值及可变性的中文区分契约。 | 对象；子字段见本字典相应条目 | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `runtime_mutability` | 参数默认值是否可覆盖、运行中能否修改和何时生效的中文限制。 | 字符串；当前常见值：默认值不是固定运行值。参数协议可传输只说明接口能力；是否允许飞行中修改、是否需要重启、何时被模块重新读取及修改… | 用于区分历史名称、当前定义、默认值和运行快照；任何身份匹配都不证明性质依赖或可变性。 |
| `runtime_write_change_verification` | 是否实际执行参数写入及生效验证的状态。 | 字符串；当前常见值：NOT_TESTED | NOT_TESTED 只表示未测试，不能解释为可修改或不可修改。 |

### 汇总与复用结构

| 英文机器字段 | 准确中文含义 | 实际值类型与当前常见值 | 本任务的判断作用或防误读边界 |
|---|---|---|---|
| `expression` | 原子命题表达式原文。 | 字符串；当前常见值：ALT_src = Baro、ALT_t = ALT_Baro、ALT_t != ALT_GPS | 用于导航、统计或复用子结构；数量和结构完整不等于语义正确。 |

## 四、覆盖检查

以下命令使用 Python（Python 编程语言）重新递归扫描两个系统的 51 个性质 JSON 文件，并要求字段集合与机器可读字段字典完全相等：

```bash
python3 - <<'PY'
import json
from pathlib import Path

root = Path('benchmark/PGFuzz_MTL51')
files = sorted((root / 'ArduPilot/properties').glob('*.json')) + sorted((root / 'PX4/properties').glob('*.json'))
keys = set()

def walk(value):
    if isinstance(value, dict):
        keys.update(value)
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)

for path in files:
    walk(json.loads(path.read_text(encoding='utf-8')))

dictionary = json.loads((root / 'FIELD_DICTIONARY.json').read_text(encoding='utf-8'))
dictionary_keys = {row['field'] for row in dictionary['fields']}

assert len(files) == 51
assert len(dictionary_keys) == dictionary['field_count']
assert keys == dictionary_keys
print(f'PASS properties={len(files)} fields={len(keys)}')
PY
```

本文件生成时的预期输出为 `PASS properties=51 fields=221`。其中 `PASS` 中文为“自动覆盖检查通过”；它只表示字段没有遗漏，不表示性质、源码绑定或固件符合性通过。
