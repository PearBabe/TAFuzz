# 中文术语表

| 英文原词 | 完整英文 | 中文含义及本任务作用 |
|---|---|---|
| MTL | Metric Temporal Logic | 度量时序逻辑；表示带时间或观测顺序关系的行为公式。 |
| MITL | Metric Interval Temporal Logic | 度量区间时序逻辑；使用时间区间的 MTL 限制形式。 |
| AP | Atomic Proposition | 原子命题；公式中最小的真假条件。 |
| policy | policy | 行为性质或规则；PGFuzz 对文档中行为要求使用的名称。 |
| term | term | 性质项；PGFuzz 公式中的状态、参数、命令或环境概念。 |
| source binding | source binding | 源码绑定；把命题或输入连接到当前源码身份。 |
| dependency | dependency | 依赖；某个结果在数据、控制或模型上受到另一对象影响的关系。名称相似不能单独证明依赖。 |
| InputP | configuration-parameter input | 配置参数输入；通过参数接口修改的飞控配置。 |
| InputC | command input | 命令输入；飞行模式、MAVLink 命令或遥控通道操作。 |
| InputE | environment-factor input | 环境输入；通常是仿真器中的风、传感器或故障参数。 |
| ADG | Assignment Dependency Graph | 赋值依赖图；ADGFuzz 从赋值语句反向连接结果变量和右值名称形成的图。 |
| MIS | Matched RV Input Subset | 匹配的机器人载具输入子集；采用 ADGFuzz 作者 README 的用词，指按变量词语、同义词和物理耦合表得到的候选输入组合，不是已证明的最小依赖集。 |
| template | template | 公式模板；PGFuzz 的 T1、T2、T3 三类自然语言到逻辑结构。 |
| artifact | research artifact | 研究制品；论文作者公开的代码、数据和运行脚本。 |
| historical property seed | historical property seed | 历史性质种子；可供分析和测试使用，但尚未由当前版本官方证据重新确认。 |
| implementation_satisfaction | implementation satisfaction | 实现符合性字段；记录当前被测程序是否满足性质。全部固定为 `NOT_ASSESSED`。 |
| NOT_ASSESSED | not assessed | 未评估；不表示满足或违反。 |
| EXACT | exact binding | 精确绑定；只表示某一绑定行的当前源码实体身份及该行所述局部含义有直接证据，不表示整个原子命题等价、整条性质正确或固件满足性质。 |
| MODELLED | modelled binding | 建模绑定；能够近似表达命题，但不能证明完全等价。 |
| NAME_ONLY | name-only match | 仅名称匹配；不能作为可靠依赖证明。 |
| UNRESOLVED | unresolved | 尚未解决；证据不足时保留，不猜测。 |
| MAVLink | Micro Air Vehicle Link | 微型飞行器通信链路协议；本任务用它判断命题所需状态能否从外部消息观测。 |
| uORB | micro Object Request Broker | 微型对象请求代理；PX4 内部发布—订阅消息总线，uORB 字段不一定会发送到 MAVLink。 |
| SITL | Software In The Loop | 软件在环仿真；在普通计算机上运行飞控和仿真器，本数据集的参数快照属于特定 SITL 运行配置。 |
| RC | Radio Control | 无线遥控；包括接收器连接状态和原始通道输入，两者不能混为一个布尔量。 |
| PWM | Pulse Width Modulation | 脉冲宽度调制；PGFuzz 中的 1500 通常是原始遥控通道的微秒中值，不等于标准化控制量 0。 |
| EKF | Extended Kalman Filter | 扩展卡尔曼滤波器；飞控用它融合传感器并估计位置、高度和速度，“GPS 故障”不必然等于 EKF 位置无效。 |
| GNSS | Global Navigation Satellite System | 全球卫星导航系统；GPS 是 GNSS 的一种，源码或文档使用 GNSS 时不应无条件缩窄为单一 GPS 接收器。 |
| NED | North East Down | 北—东—下坐标系；三个名称依次表示 x 轴向北、y 轴向东、z 轴向下为正，因此向上高度通常需对局部 z 取负。 |
| WGS84 | World Geodetic System 1984 | 1984 世界大地坐标系；用于解释纬度、经度和部分海拔字段。 |
| AMSL | Above Mean Sea Level | 平均海平面以上高度；与相对 Home 高度、局部 NED 高度不可直接比较。 |
| RTL | Return To Launch | 返航到起飞参考点；当前实现可能选择 Home 或 rally point，所以“返航目标”不总是 Home。 |
| Home | home position | 家点或起飞参考位置；包含经纬度和高度，是多个相对高度的基准。 |
| rally point | rally point | 备选集结点；ArduPilot 返航时可以选它而不是 Home，会影响 `home_position` 命题的解释。 |
| failsafe | failsafe behavior | 故障保护行为；指输入、估计或链路异常后的状态和动作，不应只根据一条消息缺失猜测。 |
| timestamp | timestamp | 时间戳；用来排序样本、判断新鲜度和关联命令，必须识别它是发送端启动时间还是观察端到达时间。 |
| freshness | data freshness | 数据新鲜度；判定样本是否足够新，防止用过期状态判真。 |
| instrumentation | instrumentation | 插桩或观测探针；在不改变性质的前提下读取标准 MAVLink 未发布的内部状态。 |

## 源码绑定与观测状态

| 机器字段或状态 | 完整英文 | 中文含义及审核作用 |
|---|---|---|
| binding_kind | binding kind | 绑定类型；区分字段、函数返回、赋值、参数定义、派生表达式等证据身份。 |
| binding_role | binding role | 绑定角色；区分用于判真的主值、形成/发送/消费路径的辅助证据，以及与主组互斥的替代语义。 |
| candidate_group | candidate group | 候选语义组；同组行共同描述一种词项解释，原子命题每个词项只选一组，不把互斥组当成合取。 |
| source_path / source_line / source_end_line | source path / source start line / source end line | 源文件路径、证据起始行和结束行；二者形成闭区间，用于在冻结版本中复核完整上下文，版本变化后必须重新校验。 |
| function_context | function context | 函数上下文；说明字段在哪个函数里读取或写入。 |
| truth_condition_zh | truth condition in Chinese | 中文真值条件；给出如何由该绑定判定命题真假。 |
| validity_freshness_zh | validity and freshness condition in Chinese | 中文有效性与新鲜度条件；防止用无效、过期或跨重置样本。 |
| DIRECT | directly observable | 直接可观测；指定 MAVLink 字段直接携带该值，但仍需按单位和枚举解码。 |
| DERIVED | derived observation | 派生观测；需要组合多个字段、保存历史样本或进行数学换算。 |
| CONDITIONAL | conditional observation | 有条件可观测；只在消息启用、配置或运行阶段满足时可用。 |
| INSTRUMENTATION_REQUIRED | instrumentation required | 需要插桩；标准 MAVLink 没有等价字段，需要读取内部状态。 |
| TRACE_PREVIOUS_SAMPLE | trace previous sample | 轨迹前一有效样本；由监视器保存，不是源码里独立的 `t-1` 变量，也不表示一秒前。 |
| PARAMETER_DEFINITION | parameter definition | 参数定义；记录名称、类型、默认值、单位和范围的当前源位置。 |
| PARAMETER_ACCESSOR | parameter accessor | 参数访问器；这是早期临时名称，当前交付已拆成 `PARAMETER_HANDLE`（句柄声明）和 `PARAMETER_CONSUMER`（真实消费点），防止把声明误当使用。 |
| SEMANTIC_CANDIDATE | semantic candidate | 语义候选；源码概念只在某种解释下对应论文词项，必须人工确认。 |
| NON_EQUIVALENT_CANDIDATE | non-equivalent candidate | 非等价候选；仅说明当前有相关概念，禁止直接代入历史公式。 |
| REMOVED_PARAMETER | removed parameter | 已删除参数；当前版本无同名运行参数，且没有证据时不得猜测替代项。 |
| UNRESOLVED_BOUND | unresolved bound | 未解决的边界值；例如 PGFuzz 未公开具体值的 `k`，不得用循环次数或人工秒数补写。 |
| ASSOCIATED_FIELD | associated field | 关联字段；它不是命题主值，但是正确关联同一命令或事件所必需的上下文。 |
| PRIMARY_VALUE | primary value | 主真值来源；当前选定语义组中用于判定命题真假的核心实体。 |
| SUPPORTING_EVIDENCE | supporting evidence | 辅助证据；证明主值怎样形成、发送、关联或被消费，不是额外的公式合取条件。 |
| ALTERNATIVE_SEMANTICS | alternative semantics | 替代语义；当论文词项有多种可能解释时保留的互斥候选，需人工切换，不与主组同时判真。 |
| PRIMARY_SELECTED | primary selected | 已选定主语义；该原子命题没有其他互斥候选组。 |
| PRIMARY_WITH_ALTERNATIVES | primary with alternatives | 已选主语义但仍有替代组；当前可按主组审核，同时必须注意论文词义可能需人工更换。 |
| UNRESOLVED_PRIMARY | unresolved primary | 主语义未解决；即使有相关候选，补证前也不计算真值。 |
| selected_term_binding_ids | selected term binding identifiers | 已选词项绑定标识符；只包含当前每个词项选定语义组的行。 |
| alternative_term_binding_ids | alternative term binding identifiers | 替代词项绑定标识符；保留互斥语义组，默认不参与当前真值计算。 |
| PARAMETER_HANDLE | parameter handle | 参数句柄；模块内的强类型参数成员，它证明成员身份，但不单独证明已在某分支消费。 |
| PARAMETER_CONSUMER | parameter consumer | 参数消费点；真实调用 `.get()` 或 getter 使用当前参数值的源码位置。 |
| SELECTION_GUARD | selection guard | 选择守卫条件；说明运行时候选源何时被选中或回退，只用于身份绑定，不用于反推规范。 |
| MAVLINK_SENDER | MAVLink sender | MAVLink 发送端；把内部字段编码成协议消息的函数。 |
| COMMAND_ACCEPTANCE | command acceptance | 命令接受阶段；飞控已决定接受或拒绝输入命令，与“收到”和“正在执行”分开。 |
| COMMAND_ACK | Command Acknowledgement | 命令确认；使用 ACK 消息返回接受、临时拒绝等结果，必须与原命令身份关联。 |
| EXECUTION_STATE | execution state | 执行状态；表示飞控已进入对应导航/控制阶段，通常晚于命令收到和接受。 |
| PASS / FAIL | pass / fail | 自动检查通过/失败；只表示数据结构、引用、路径和固定断言一致，不表示固件性质通过。 |

## 交付格式与版本词语

| 英文原词 | 完整英文 | 中文含义及本任务作用 |
|---|---|---|
| JSON | JavaScript Object Notation | JavaScript 对象表示法；保存完整嵌套审计记录，供脚本处理。 |
| CSV | Comma-Separated Values | 逗号分隔值；保存扁平表格，便于人工筛选和统计。 |
| Markdown | Markdown | 轻量标记文本格式；用于生成可直接阅读的中文审计报告。 |
| SHA-256 | Secure Hash Algorithm 256-bit | 256 位安全散列算法；这里只用于校验论文和语料文件是否改变。 |
| commit | source-control commit | 源码版本提交；固定绑定所依赖的精确 ArduPilot/PX4 版本。 |

完整机器字段另见 [FIELD_DICTIONARY.md](FIELD_DICTIONARY.md)。字段字典解释结构和值类型；它与本术语表一样，不证明公式正确或固件符合性质。

## 公式符号、模板与角色

| 英文或符号 | 完整英文 | 中文含义及本任务作用 |
|---|---|---|
| `G φ` | Globally | 全局成立；在被监视范围的每一个采样点都要求公式 `φ` 成立。 |
| `F_[a,b] φ` | Eventually within interval | 区间内最终成立；触发后在闭区间 `[a,b]` 中至少有一个观测点满足 `φ`。本数据集保留论文括号，不擅自改变边界开闭。 |
| `->` | implication | 逻辑蕴含；只有前件为真时才要求后件为真，方向写反会改变性质。 |
| `&` | conjunction | 逻辑与；各子条件必须同时为真。 |
| `or` / `|` | disjunction | 逻辑或；至少一个分支为真。源码或作者文件中的竖线也可能是位运算或分隔符，必须结合上下文。 |
| `!` / `not` | negation | 逻辑非；把条件真值取反。 |
| `t-1` | previous accepted observation | 上一有效观测样本；表示轨迹顺序，不是一秒前，也不是源码中的独立变量。 |
| `k` | empirical time-bound symbol | 经验时间上界符号；PGFuzz 论文称其由 100 次仿真的最大观测时间得到，但没有公布逐性质数值，所以当前保持未知。 |
| T1 | bounded-response template | 有界响应模板；触发后要求结果在时间区间内发生。 |
| T2 | state-constraint or prohibition template | 状态约束或禁止模板；规定某状态下允许或禁止的行为。 |
| T3 | global condition-obligation template | 全局条件—义务模板；每当条件成立，就要求相应义务成立。 |
| antecedent | antecedent | 前件或触发条件；蕴含式箭头左侧的条件。 |
| consequent | consequent | 后件或义务；蕴含式箭头右侧的条件。 |
| consequent_disjunct | consequent disjunct | 后件析取分支；后件逻辑或中的一个候选分支。 |
| negated_consequent | negated consequent | 被取反的后件；用于禁止型条件。 |
| `*_as_printed` | role as printed | 按论文印刷公式识别的角色；不由自然语言补写。 |
| `*_from_description` | role from description | 只来自论文自然语言描述、未印在公式中的角色；审核时不能冒充原公式已有条件。 |

## 时间来源、时钟与具体值状态

| 机器值或字段 | 完整英文 | 中文含义及本任务作用 |
|---|---|---|
| PAPER_LITERAL | paper literal | 论文原式字面值；只说明论文明确写了该数值和单位。 |
| SYMBOLIC_UNRESOLVED | symbolic unresolved bound | 未解析的符号边界；例如含 `k` 的上界，不能生成当前具体秒数。 |
| PREVIOUS_OBSERVATION | previous observation | 上一有效观测；只有顺序关系，没有固定经过时间。 |
| UNSPECIFIED_BY_PAPER | unspecified by paper | 论文未说明时钟域或时间戳载体。 |
| AVAILABLE | concrete value available | 有可追溯具体值；仍必须查看其来源是论文字面值、当前参数还是运行观测。 |
| UNKNOWN | unknown concrete value | 具体值未知；禁止人工补值。 |
| TRACE_ORDER | trace order | 轨迹样本顺序；不代表任何固定经过时间。 |
| CONTEXT_ONLY_NOT_CURRENT_REQUIREMENT_CONFIRMATION | context only, not current-requirement confirmation | 只作当前行为语境说明；不确认论文性质是当前官方要求。 |
| s | second | 秒；时间单位。 |
| ms | millisecond | 毫秒，等于千分之一秒。 |
| us / µs | microsecond | 微秒，等于百万分之一秒。源码标识符通常用 ASCII 写法 `us`。 |
| time_boot_ms | time since boot in milliseconds | 发送端启动后的毫秒数；不是 Unix 日历时间，32 位字段还需考虑回绕。 |
| time_usec | time in microseconds | 微秒时间字段；它表示启动时间还是 Unix 纪元时间必须按具体 MAVLink 消息定义判断。 |
| uORB timestamp | uORB monotonic timestamp | PX4 内部消息时间戳，通常为启动后的单调微秒时间；不能直接当作 Unix 时间。 |
| observation arrival time | observer-side arrival time | 观察端到达时间；包含传输、排队和调度延迟，不能冒充内部状态改变时刻。 |

## 输入身份、依赖强度与参数证据状态

| 机器值 | 完整英文 | 中文含义及本任务作用 |
|---|---|---|
| PRECONDITION | precondition input | 前置输入；作者旧实验明确先设置的值，不自动继承为当前版本前置条件。 |
| CANDIDATE_ASSOCIATION | candidate association | 候选关联；作者把输入列进性质目录，但没有公开逐项最小因果依赖证明。 |
| EXPLICIT_PRECONDITION | explicit precondition | 明确前置设置；只证明作者旧实验流程保存了该设置。 |
| EXACT_CURRENT_DEFINITION | exact current definition | 冻结源码中找到同名参数定义；不证明它影响性质。 |
| RENAMED_CURRENT_DEFINITION | renamed current definition | 找到更名或迁移后的当前定义；是否严格等价还要查看匹配置信度。 |
| CURRENT_DEFINITION_NOT_FOUND | current definition not found | 本次冻结语料中未找到可信定义；不等于数学意义上的不存在证明。 |
| COMMAND_XML_DEFINITION_FOUND | command XML definition found | 在冻结 MAVLink XML 中找到同名命令；不证明当前固件接收或执行它。 |
| COMMAND_XML_DEFINITION_NOT_FOUND | command XML definition not found | 在冻结 MAVLink XML 中未找到同名命令；不猜测替代命令。 |
| SPECIAL_CONTROL_INPUT | special control input | PGFuzz 自定义的模式或遥控输入，不是普通配置参数。 |
| NOT_TESTED | not tested | 未执行运行时写入与生效测试；不等于参数不可修改。 |
| NOT_APPLICABLE | not applicable | 当前字段或比较不适用。 |
| EXACT_SAME_NAME | exact same-name historical/current relation | 论文历史词项与当前源码使用同名身份；只说明名称与局部实体一致，不自动证明整条命题语义相同。 |
| RENAMED_AND_SCALED_0.01 | renamed and scaled by 0.01 | 历史参数已更名，旧数值还需乘以 0.01 才能转换到当前单位；未换算时禁止直接比较。 |
| REMOVED_NO_EQUIVALENT | removed with no proven equivalent | 历史参数已删除且没有已证明等价的当前参数；公式必须保持未解决。 |
| SEMANTIC_SUCCESSOR_NOT_PROVEN_RENAME | semantic successor, not a proven rename | 当前概念可能承接部分历史用途，但没有证据证明它只是严格更名；只能作为建模迁移。 |
| EXACT_NAME_DEFINITION | exact-name definition match | 当前同名源码定义匹配。 |
| EXACT_NAME_XML_DEFINITION | exact-name XML definition match | 当前同名 XML 命令定义匹配。 |
| CURATED_RENAME_EXACT | curated exact rename | 有人工证据支持的精确更名。 |
| CURATED_MIGRATION_MODELLED | curated modelled migration | 人工整理的相关迁移；不能当作严格等价。 |
| CURATED_INSTANCE1_MIGRATION_MODELLED | curated instance-one modelled migration | 只对第一传感器实例建立的建模迁移；不能推广到全部实例。 |
| MODELLED_SPECIAL_INPUT | modelled special input | 特殊控制输入的建模身份；需要进一步绑定当前编码。 |
| CURATED_FROZEN_SOURCE_RESOLUTION | curated frozen-source resolution | 依据冻结源码中的直接宏或枚举证据人工复核出的默认值。 |
| SOURCE_METADATA_LITERAL_OR_EXPRESSION | source-metadata literal or expression | 参数目录中的字面值或未求值表达式；宏名不能冒充具体数值。 |
| observed_in_frozen_runtime_parameter_download | observed in frozen runtime parameter download | 冻结参数下载中出现过；只证明该运行可读取该值。 |
| protocol_capable_runtime_presence_not_observed | protocol-capable, runtime presence not observed | 参数协议理论上能传输，但冻结运行下载中未确认该参数。 |
| MATCH | identifier match | 作者命令数字标识与当前 XML 定义一致。 |
| MISMATCH_OR_MULTIPLE | identifier mismatch or multiple definitions | 命令数字标识冲突或存在多个定义候选。 |
| confirmed_by_frozen_runtime_snapshot | confirmed by frozen runtime snapshot | 冻结运行快照确认该参数被包含。 |
| not_compile_option_resolved | compile-option inclusion unresolved | 尚未解析编译选项是否包含该参数。 |
| not_px4_sitl_module_list_resolved | PX4 SITL module-list inclusion unresolved | 尚未确认 PX4 软件在环模块列表是否包含该参数。 |
| exact_metadata_unique | exact unique metadata location | 参数元数据解析只找到一个同名定义位置；只证明位置唯一，不证明参数与性质存在依赖。 |
| exact_metadata_multiple | exact multiple metadata locations | 参数元数据解析找到多个同名定义位置；全部位置都保留，不能擅自只选一个实例或车型。 |
| exact_definition_unique | exact unique source definition | 补充源码定义目录只找到一个同名定义位置；不等于已经验证运行时包含或消费。 |
| exact_definition_curated | exact manually curated source definition | 该定义位置由人工核对补入；仍需结合冻结提交和上下文复核。 |
| curated_alias_evidence | manually curated alias evidence | 当前更名/迁移位置取自人工核对的别名证据；若参数目录命中不同文件，就不会继承其类型、默认值或范围。 |
| unresolved（小写原值） | unresolved source-location confidence | 源位置置信度未解决；这里是作者输入身份目录保存的小写原值，判断作用与“证据不足、禁止猜测”一致。 |
| 空字符串（source-location confidence） | empty source-location confidence | 当前没有可用源位置置信度；不能解释为零置信度之外的任何具体结论。 |
| AUTHOR_PARSER_CALLS_UNITS_BUT_ARTIFACT_VALUES_MAY_BE_INCREMENT | author parser calls units, but artifact values may be increment | 作者解析器把第六列称作单位，但制品值可能是步进量；本数据集只保留原值，不擅自选定解释。 |
| X（作者参数原值） | author-artifact placeholder X | PGFuzz 参数行中的原样占位符；公开读取代码没有定义它究竟表示“缺失”还是“不适用”，因此不能把它解释为 0、false、任意范围或具体单位。 |
| TRUE（artifact_reboot_raw） | author-artifact reboot flag TRUE | PGFuzz 作者参数行第二列的重启标记；其读取代码把该列命名为 `param_reboot`，所以它表示旧制品标记“需要重启”，不证明当前版本仍需重启。 |
| True / False（覆盖表） | Boolean true / false | 布尔真/假；在公式参数覆盖表中分别表示作者输入文件“列出/未列出”该参数，不表示性质真假。 |
| True（current_reboot_required） | current metadata says reboot required | 当前参数元数据标记修改后需要重启；本任务没有执行写入、重启和生效测试，所以只作为元数据证据。 |
| 空字符串（current_reboot_required） | reboot metadata not extracted | 没有提取到当前重启元数据；不能解释为“不需要重启”。 |
| 空字符串（current_build_inclusion_status） | build-inclusion evidence not obtained | 当前没有取得该输入已纳入冻结构建或运行配置的证据；不能解释为“已纳入”，也不能解释为“未纳入”。 |

## 常见源码、分析和文件术语

| 英文原词 | 完整英文 | 中文含义及本任务作用 |
|---|---|---|
| PGFuzz | Policy-Guided Fuzzing | 性质引导模糊测试；本数据集的 51 条历史公式及作者输入文件来源。 |
| ADGFuzz | Assignment Dependency-Guided Fuzzing | 赋值依赖引导模糊测试；本任务只参考其依赖候选生成工作流。 |
| GPS | Global Positioning System | 全球定位系统；消息丢失、定位质量下降、估计器位置无效和故障保护状态不能自动视为同一个布尔量。 |
| AHRS | Attitude and Heading Reference System | 姿态与航向参考系统；提供融合后的姿态、位置或速度状态，不是一个原始传感器。 |
| GCS | Ground Control Station | 地面控制站；源码中的 GCS 类常是遥测编码/发送层，不表示外部地面站本身状态。 |
| JSON Schema | JSON Schema | JSON 数据结构约束规范；检查必需字段与类型，不检查公式语义或飞控符合性。 |
| schema | data schema | 数据结构模式；规定字段组织和允许类型。 |
| PDF | Portable Document Format | 便携式文档格式；用于保存论文原始版面证据。 |
| XML | Extensible Markup Language | 可扩展标记语言；MAVLink 方言用它定义消息、字段和命令。 |
| LLVM IR | LLVM Intermediate Representation | LLVM 项目的中间表示；PGFuzz 静态分析在该代码表示上进行。LLVM 名称历史上源于 Low Level Virtual Machine。 |
| Andersen analysis | Andersen points-to analysis | Andersen 包含约束式指针指向分析；给出保守的“可能指向”集合，因此可能引入额外候选。 |
| C++ / .cpp | C++ source language / C++ source-file extension | C++ 编程语言及其源码文件扩展名；源码绑定常指向这类文件。 |
| Python / .py | Python language / Python script-file extension | Python 编程语言及脚本文件扩展名；本数据集构建器和验证器使用它。 |
| macro | preprocessor macro | 预处理宏；必须解析定义后才能得到具体默认值。 |
| getter | getter function | 取值函数；证明代码能读取值，不证明目标路径在某次运行实际消费它。 |
| fuzz campaign | fuzz-testing campaign | 一轮或一批完整模糊测试活动；本阶段没有执行。 |
| enum | enumerated type | 枚举类型；数字必须结合冻结提交的枚举定义解码，不能跨系统或版本直接比较。 |
| bool | Boolean | 布尔类型；只有真和假，论文 `on/off` 必须明确映射到具体字段及是否取反。 |
| uint8_t | unsigned 8-bit integer type | 8 位无符号整数；范围 0 到 255。 |
| int32_t | signed 32-bit integer type | 32 位有符号整数；缩放和符号会影响高度或坐标解码。 |
| uint64_t | unsigned 64-bit integer type | 64 位无符号整数；常承载较大的时间计数。 |
| float32 / float64 | 32-bit / 64-bit floating-point number | 32 位/64 位浮点数；严格相等可能受表示误差影响，但本任务不会自行增加容差。 |

## 常见 MAVLink 消息和字段族

| 消息标识符 | 中文含义及审核作用 |
|---|---|
| HEARTBEAT | 心跳消息；常携带模式和武装标志，但到达时间不是模式切换或武装动作的内部时刻。 |
| ATTITUDE | 姿态消息；携带滚转、俯仰、偏航和角速度。 |
| GLOBAL_POSITION_INT | 整数全球位置消息；携带纬经度、海拔、相对高度和速度，必须按字段缩放。 |
| GPS_RAW_INT | 原始 GPS 状态消息；携带定位类型、卫星数等，不等于飞控故障保护状态。 |
| HOME_POSITION | 家点消息；携带当前 Home 坐标和高度参考。 |
| LOCAL_POSITION_NED | 局部北东地向下位置消息；z 轴向下为正。 |
| SYS_STATUS | 系统状态消息；包含传感器启用、健康等位掩码，不直接等于具体内部故障原因。 |
| RC_CHANNELS | 遥控通道消息；携带原始通道脉宽和接收强度。 |
| MANUAL_CONTROL | 标准化手动控制消息；轴值不能直接与 `RC_CHANNELS` 的 1500 微秒中值比较。 |
| EXTENDED_SYS_STATE | 扩展系统状态消息；可报告空中/地面和垂直起降状态。 |
| COMMAND_LONG / COMMAND_INT | 长格式/整数坐标格式命令输入；“收到命令”不等于接受或执行。 |
| COMMAND_ACK | 命令确认消息；报告命令处理结果，必须用命令身份关联。 |
| POSITION_TARGET_GLOBAL_INT | 全球位置目标消息；携带目标位置/高度，不是实际位置。 |
| PARAM_VALUE | 参数值消息；证明参数值可读取，不证明控制路径已消费它。 |
| DISTANCE_SENSOR | 距离传感器消息；需检查方向、最小/最大范围和有效性。 |
| ALTITUDE | 多参考面高度消息；不同字段的参考面不能混用。 |
| MISSION_COUNT | 任务项计数消息；只反映任务协议状态，不自动等于 Guided 航点状态。 |
| ORBIT_EXECUTION_STATUS | 盘旋执行状态消息；携带盘旋半径、速度和中心等目标/执行信息。 |
| HIGH_LATENCY2 | 高延迟汇总遥测消息；更新频率和字段精度低于常规流。 |
| STATUSTEXT | 状态文本消息；只能作提示，不能自动替代类型化内部状态。 |
| EVENT | 事件消息族；是否存在、是否启用及事件编号语义须按当前版本定义核对。 |
