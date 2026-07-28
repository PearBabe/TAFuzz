# PGFuzz 51 条历史性质：ArduPilot/PX4 当前源码绑定与作者依赖结果

## 一、先解释本报告中的英文术语

- `PGFuzz` 是 `Policy-Guided Fuzzing`，中文为“性质引导模糊测试”；本数据集采用它在论文表十二列出的历史性质和公开输入文件。
- `ADGFuzz` 是 `Assignment Dependency-Guided Fuzzing`，中文为“赋值依赖引导模糊测试”；本阶段只分析其依赖候选生成方法，没有执行下一阶段当前源码静态分析。
- `MTL` 是 `Metric Temporal Logic`，中文为“度量时序逻辑”；这是 PGFuzz 对表十二公式使用的名称。
- `MITL` 是 `Metric Interval Temporal Logic`，中文为“度量区间时序逻辑”；它是使用时间区间的 MTL 限制形式。大量表十二公式只有全局算子和相邻样本关系，所以不能笼统声称 51 条都是语法、类型和语义均正确的严格 MITL。
- `AP` 是 `Atomic Proposition`，中文为“原子命题”；它是公式中可以独立判断真假的最小条件。
- `source binding` 中文为“源码绑定”；它把论文词项对应到当前提交里的字段、变量、枚举、函数、赋值点、参数消费点或消息发送点。
- `MAVLink` 是 `Micro Air Vehicle Link`，中文为“微型飞行器通信协议”；本报告用它区分哪些 AP 可从飞控外部观测。
- `SITL` 是 `Software In The Loop`，中文为“软件在环仿真”；冻结运行值只代表某次具体仿真配置。
- `InputP`、`InputC`、`InputE` 分别是 `Parameter Input`（配置参数输入）、`Command Input`（命令或遥控输入）和 `Environmental Input`（仿真环境输入）。
- `ADG` 是 `Assignment Dependency Graph`，中文为“赋值依赖图”；它连接赋值左侧结果与右侧来源变量。
- `MIS` 采用 ADGFuzz 作者 README 的 `Matched RV Input Subset`，中文为“匹配的机器人载具输入子集”；它是经名称、同义词和物理耦合匹配得到的待验证输入组合。
- `LLVM IR` 是 `LLVM Intermediate Representation`，中文为“LLVM 项目的中间表示”；PGFuzz 论文称其参数静态映射在这种编译器中间代码上进行。
- `def-use` 是 `definition-use`，中文为“定义—使用关系”；`points-to analysis` 是“指针指向分析”；`alias analysis` 是“别名分析”。三者用于追踪值的产生、读取以及不同指针可能引用的对象。
- `Andersen analysis` 是“Andersen 指针指向分析”；它求保守的可能指向集合，因此可能保留多余候选。
- `softmax` 中文为“指数归一化函数”；ADGFuzz 公开代码用它把路径分数转换为选择概率。
- `JSON` 是 `JavaScript Object Notation`，中文为“JavaScript 对象表示法”；保存完整结构化记录。`CSV` 是 `Comma-Separated Values`，中文为“逗号分隔值”；便于表格筛选。`Markdown` 是轻量标记文本格式；用于人工阅读。
- `PASS` 中文为“自动检查通过”；只说明结构、数量、引用、路径和固定断言一致，不表示飞控性质通过。

本报告会反复使用下列机器状态：

| 机器状态 | 中文含义 | 审核边界 |
|---|---|---|
| `HISTORICAL_PROPERTY_SEED` | 历史性质种子 | 来自旧论文，尚未被当前官方文档逐条重新确认为当前规范。 |
| `NOT_ASSESSED` | 未评估实现符合性 | 不表示满足，也不表示违反。 |
| `EXACT` | 精确绑定 | 只说明某一绑定行的局部源码实体身份及该行局部含义有直接证据，不代表整个 AP 或性质精确。 |
| `MODELLED` | 建模绑定 | 需要坐标、单位、历史样本、有效性或上下文解释。 |
| `UNRESOLVED` | 尚未解决 | 当前证据不足，禁止猜测。 |
| `DIRECT` | 直接可观测 | MAVLink 字段直接携带所需值，仍需缩放、枚举和有效性检查。 |
| `DERIVED` | 派生可观测 | 需要换算、组合字段或保存历史样本。 |
| `CONDITIONAL` | 有条件可观测 | 只在消息启用、字段有效或特定运行阶段成立时可用。 |
| `INSTRUMENTATION_REQUIRED` | 需要插桩 | 标准 MAVLink 没有等价字段，需要读取内部状态。 |
| `CANDIDATE_ASSOCIATION` | 候选关联 | 作者列入输入文件，但没有公开逐项最小因果依赖证明。 |
| `NOT_TESTED` | 未执行运行写入测试 | 不等于参数不可修改，也不等于参数可以立即生效。 |

公式符号中，`G` 是 `Globally`（全局成立）；`F_[a,b]` 是 `Eventually within interval`（在区间 `[a,b]` 内最终成立）；`t-1` 是上一有效观测样本而不是一秒前；`k` 是论文没有公开逐性质具体值的经验时间上界。

共同术语的完整解释见 [GLOSSARY.md](GLOSSARY.md)，所有结构化字段的逐项解释见 [FIELD_DICTIONARY.md](FIELD_DICTIONARY.md)，源码绑定表中全部数据类型和单位/坐标原值的逐项中文解释见 [TYPE_UNIT_DICTIONARY.md](TYPE_UNIT_DICTIONARY.md)。

## 二、结论和交付规模

公式来源已经核对为 PGFuzz 论文第 18 页表十二，不是 ADGFuzz 论文最后一页。冻结范围为 51 条历史性质：ArduPilot 30 条、PX4 21 条。

| 项目 | 总数 | ArduPilot | PX4 | 如何理解 |
|---|---:|---:|---:|---|
| 历史性质 | 51 | 30 | 21 | 全部保持 `HISTORICAL_PROPERTY_SEED`。 |
| AP 出现位置 | 178 | 110 | 68 | 同一表达式在不同性质中仍分别保留；共有 99 种唯一表达式。 |
| 当前源码绑定行 | 227 | 110 | 117 | 覆盖 107 个“系统—词项”身份；一项可对应多字段、多函数和多位置。 |
| 作者性质—输入关联 | 7,569 | 5,872 | 1,697 | 完整保留重复和共享目录关系，不冒充 7,569 个独立因果关系。 |
| 当前输入身份 | 356 | 264 | 92 | 以系统、输入类别和作者历史名称去重。 |
| 性质—公式参数记录 | 20 | 10 | 10 | 其中 4 条没有出现在作者输入文件中。 |
| 官方文档语境记录 | 23 | 14 个系统专用页面加 1 个共享页面 | 8 个系统专用页面加 1 个共享页面 | 只解释当前语境，不重新确认论文公式。 |

178 个 AP 的绑定状态为：57 个 `EXACT`、107 个 `MODELLED`、14 个 `UNRESOLVED`。外部观测状态为：62 个 `DIRECT`、11 个 `DERIVED`、57 个 `CONDITIONAL`、34 个 `INSTRUMENTATION_REQUIRED`、14 个 `UNRESOLVED`。

整条性质按最弱 AP 汇总后，40 条为 `MODELLED`、11 条为 `UNRESOLVED`，没有一条被标成整条 `EXACT`。所有 `implementation_satisfaction` 字段仍为 `NOT_ASSESSED`。

目录入口：

- [ArduPilot 30 条性质目录](ArduPilot/property_catalog.md)
- [PX4 21 条性质目录](PX4/property_catalog.md)
- [51 条合并结构化目录](property_catalog.json)
- [178 个 AP 与当前源码绑定](SOURCE_BINDING_GUIDE.md)
- [7,569 条作者依赖输入总表](author_input_dependencies.csv)
- [356 个当前输入身份](current_input_identity_map.csv)
- [20 条公式直接参数覆盖](formula_parameter_coverage.csv)

## 三、性质、源码和依赖怎样连接

本数据集只按下列单向流程工作：

1. 保存论文英文原文、印刷公式和已知问题，不静默修正。
2. 把每条公式拆为 AP，并从 AP 中解析状态、参数、事件和历史样本词项。
3. 对每个词项在当前冻结源码中寻找实体身份、数据类型、单位、坐标、有效性、形成路径、消费路径和消息发送路径。
4. 若同一论文词项有多种可能解释，把它们拆成互斥的候选语义组；每个 AP 每个词项只选择一组作为当前审核主组。
5. 把 PGFuzz 作者输入文件逐行连接到性质，再查当前参数或命令身份；原始重复行和共享目录不会被删除。
6. 记录外部观测方案；标准消息不够时标为需要插桩或未解决。
7. 保持实现符合性未评估，等待用户下一阶段的静态分析和后续动态测试。

三种绑定角色必须分开：`PRIMARY_VALUE` 表示“主真值来源”；`SUPPORTING_EVIDENCE` 表示“形成、消费、关联或发送路径的辅助证据”；`ALTERNATIVE_SEMANTICS` 表示“与主组互斥的替代语义”。辅助证据不会被误当成额外的公式合取条件，直接可读取的辅助参数也不会把一个只能条件性观测的主状态提升为直接可观测。

## 四、时间语义为何没有补造

用户当前不再强制每条性质必须有明确数值时间。本数据集仍保存论文写出的时间信息，但不把未知量人工具体化。

- `A.FLIPGeneral` 的 2.5 秒是唯一直接保留的非零具体上界；来源是论文该行的字面公式和说明。
- `A.FLIP3`、`A.BRAKE1`、`A.DRIFT1`、`PX.GPS.FS1` 含有 `k`。论文说明 `k` 通过 100 次仿真取最大观测值得到，但没有公布每条性质的完整轨迹、具体值、时钟载体和测量误差，因此保持未知。
- 论文给 `A.BRAKE1` 的约 12.7 秒只是旧仿真环境中的示例最大观测，不是 ArduPilot 官方要求，也不能迁移到其他性质。
- `t-1` 只表示同一运行、同一语义、同一坐标系下的上一有效样本。丢包、重排、重置和来源切换都会影响这个关系；它没有固定秒数。
- `PX.GPS.FS1` 的历史 `COM_POS_FS_DELAY+k` 仍按原式保存。当前 PX4 已删除 `COM_POS_FS_DELAY`，所以不能生成当前具体时间。

## 五、四个代表性性质

### 5.1 A.RTL1：历史厘米参数、当前米参数和相邻样本

论文英文原文要求当前高度低于 `RTL_ALT` 时持续爬升直到达到目标；印刷公式只检查相邻样本继续上升。因此记录了 `UNTIL_LOST`（“直到”终止条件丢失）和 `PREVIOUS_SAMPLE_NOT_TIME`（上一样本不是固定时间）两项问题。

- `ALT_t` 主绑定为 `Copter::current_loc.alt`，并要求转换为相对 Home（家点/起飞参考位置）的高度。
- `Mode_t=RTL` 可由当前 ArduCopter 模式枚举及 `HEARTBEAT.custom_mode` 判断。`HEARTBEAT` 是心跳消息；消息到达时间不是内部模式切换时刻。
- 历史 `RTL_ALT` 当前映射到 `RTL_ALT_M`。作者旧值 1500 采用旧厘米量级，当前源码默认宏经当前源码核对为 15 米，冻结运行值也是 15.0 米；这些值不是时间。
- 该性质完整保留 238 条作者候选关联、228 个去重身份。

完整记录见 [A.RTL1.md](ArduPilot/properties/A.RTL1.md)。

### 5.2 A.CHUTE1：释放锁存、执行器动作和物理展开不能混同

这条公式含 5 个 AP：降落伞开启、已经武装、模式不是 FLIP/ACRO、没有继续爬升、高于最低释放高度。

- `Parachute=on` 当前主解释选择 `AP_Parachute::released()` 的内部释放锁存状态；释放请求、舵机/继电器输出和物理伞体展开是不同阶段。
- 标准 MAVLink 没有直接发送该内部锁存量，因此这个 AP 标为 `INSTRUMENTATION_REQUIRED`。
- `CHUTE_ALT_MIN` 在公式中直接出现，却不在作者 `parameters.txt` 中，这是作者候选依赖列表的真实缺口。当前源码默认宏经复核为 10 米；冻结运行快照没有该值，不能据此猜测运行值。
- 它是唯一保存 5 条明确旧实验前置设置的性质：`CHUTE_ENABLED=1`、`CHUTE_TYPE=10`、`SERVO9_FUNCTION=27`、`SIM_PARA_ENABLE=1`、`SIM_PARA_PIN=9`。冻结运行值与多项旧设置不同，且写入生效均未测试。
- 当前官方页面中的连续 1 秒条件只适用于页面所述的自动释放机制，不能迁移成所有 `Parachute=on` 的统一时间约束。
- 该性质完整保留 243 条作者候选关联、233 个去重身份。

完整记录见 [A.CHUTE1.md](ArduPilot/properties/A.CHUTE1.md)。

### 5.3 PX.ORBIT3：原始遥控脉宽、目标方向和实际运动方向

论文没有为该行印刷完整 PX4 专用公式，只写“与 A.CIRCLE3 相同”。数据集把展开式标为绑定解释，不冒充论文原样公式。

- `RC` 是 `Radio Control`（无线遥控），`PWM` 是 `Pulse Width Modulation`（脉冲宽度调制）。`RC_roll>1500` 必须选择当前 `RC_MAP_ROLL` 映射后的原始微秒通道值，不能选择范围约为 `[-1,1]` 的标准化横滚轴。
- `Circle_direction_t` 主解释为 `ORBIT_EXECUTION_STATUS.radius` 的符号编码目标方向；由位置和速度计算的实际运动方向只作为互斥替代语义。
- `Circle_speed_t` 主解释为内部目标切向速度 `_orbit_velocity`；实际地速为互斥替代语义。
- 当前值和 `t-1` 必须选择同一候选语义组，不能用“当前目标速度”减去“上一实际地速”。
- 该性质有 50 条作者候选关联、49 个去重身份，没有公式直接配置参数词项。

完整记录见 [PX.ORBIT3.md](PX4/properties/PX.ORBIT3.md)。

### 5.4 PX.TAKEOFF1：命令收到、接受、确认和执行是不同阶段

论文自然语言要求目标高度等于 `MIS_TAKEOFF_ALT`，印刷公式却只写当前高度小于等于该参数，因此保留 `TARGET_EQUALITY_WEAKENED`（目标等式被弱化）问题，不静默修复。

- `Command_t` 主解释选择收到起飞命令事件。
- `COMMAND_ACK` 是 `Command Acknowledgement`（命令确认消息）。`Commander` 是 PX4 的“飞行管理与命令处理模块”，`Navigator` 是 PX4 的“任务与导航状态机模块”。收到命令、Commander 接受命令、发出命令确认、Navigator 进入自动起飞执行状态是四个不同阶段。
- `AMSL` 是 `Above Mean Sea Level`（平均海平面以上高度）。`MIS_TAKEOFF_ALT` 是相对起飞参考高度，不能直接与 AMSL 高度比较；`ALT_t` 和 `Target_ALT` 均需使用同一次起飞实例捕获的参考高度。
- 当前 `MIS_TAKEOFF_ALT` 的源码默认值和冻结运行值都是 2.5 米，但运行写入和生效仍是 `NOT_TESTED`。
- 该性质完整保留 94 条作者候选关联、91 个去重身份。

完整记录见 [PX.TAKEOFF1.md](PX4/properties/PX.TAKEOFF1.md)。

## 六、PGFuzz 怎样提取性质和相关输入

PGFuzz 的真实流程不是“自然语言自动生成 MTL”，而是：

1. 两位作者人工阅读官方文档和源码注释。
2. 分别人工写 ArduPilot、PX4 和 Paparazzi 的自然语言规则。
3. 人工识别状态、参数和事件词项。
4. 套用 T1、T2、T3 模板；三者分别是有界响应、状态约束/禁止、全局条件—义务模板。
5. 人工检查并协调性质冲突。
6. 性质冻结后，再把公式词项映射到配置参数、命令/遥控和环境输入。
7. 用相关输入缩小变异空间；部分未知 `k` 再做经验测量。

### 6.1 配置参数输入

论文描述的 `InputP` 流程是：从官方参数 XML（可扩展标记语言）取得标识符，在源码中找当前程序变量，把程序编译为 LLVM IR，执行定义—使用追踪、跨函数指针指向分析和 Andersen 别名分析，再用人工同义词表把受影响源码变量与公式物理状态匹配。

优点是可以从参数定义沿数据流扩大候选集合，减少完全盲目的输入变异。局限是冻结 PGFuzz 仓库没有完整静态分析器、完整同义词表或逐边证明；路径不敏感分析还会保留实际不可达候选。因此公开 `parameters.txt` 只能作为高召回候选集合。

### 6.2 命令和环境输入

论文描述的 `InputC/InputE` 动态流程是：运行约一分钟得到基线，一次只改变一个输入，再运行约一分钟，比较状态标准差，重复十次后保存稳定变化关系。

公开代码与论文不一致：默认测量约 1 秒、重复 3 次。单输入标准差只能说明旧环境中观察到稳定相关变化，不能证明唯一因果关系，也不能证明某输入是性质违反的必要条件。

### 6.3 前置输入和时间上界

若目标输入单独不能产生预期状态变化，PGFuzz 会尝试先执行另一个输入、等待稳定、再执行目标输入，最多重复十次。公开制品中只有 A.CHUTE 保存了非空前置设置。这个结果只说明旧实验顺序，不是当前版本的形式必要条件。

未知 `k` 则通过触发前件、测量目标状态出现、重复 100 次并取最大观测值估计。该方法能提供实验预算，但最大观测值不是官方规范上界，也没有概率置信保证。

详细源码与论文差异见 [DEPENDENCY_METHOD_AND_WORKFLOW.md](DEPENDENCY_METHOD_AND_WORKFLOW.md)。

## 七、ADGFuzz 的赋值依赖工作流

ADGFuzz 不是性质提取器。它只能在性质与 AP 已冻结后，为目标变量生成待验证输入组合：

1. 按函数提取 `y=f(X)` 形式的赋值。
2. 规范化变量名称并建立 ADG。
3. 从目标赋值变量反向遍历，区分根变量、中间变量和叶变量。
4. 把叶变量、命令、配置参数和环境输入的名称按下划线拆词。
5. 用同义词表和物理耦合表扩展词项，删除动词和过短词项。
6. 按名称匹配形成一个或多个 MIS。
7. 根据图节点数和词项匹配强度计算路径分数并选择输入组合。
8. 每条路径执行 50 到 500 次，按结果动态调整分数。

公开实现与论文存在四个重要差异：

- 代码用正则表达式近似解析 C++，不是完整语义分析。
- 解析会删除数字、作用域、运算符、分支条件和一部分对象身份。
- 代码实际把中间依赖节点计数 `node_count` 与名称匹配累积分量 `H_sum` 线性相加，不是论文中的对数公式；二者的逐步计算含义见依赖方法文档的符号表。
- 代码使用 softmax 选路径，不是论文写出的 `E/sum(E)`。

因此，ADGFuzz 的优点是能沿多层赋值扩大输入组合，不必人工枚举所有组合；缺点是对象、条件、常量和跨函数语义容易丢失，名称匹配可能误配。下一阶段正确用法是：以本数据集冻结的 AP 源码身份为目标，让 ADGFuzz 风格分析扩展候选输入，再由动态测试验证；禁止从赋值图反向生成“系统必须满足”的规范。

## 八、作者依赖方法的总体优缺点

| 方法 | 优点 | 缺点 | 当前采用方式 |
|---|---|---|---|
| PGFuzz 人工性质提取 | 规则容易人工阅读；公式、状态和输入能显式关联 | 依赖人工和版本语境；模板会丢失取消、重置和例外；表十二自身含方向、单位和条件错误 | 作为 51 条历史性质种子，不作为当前规范确认 |
| PGFuzz 参数静态映射 | 能从参数定义沿数据流扩大候选空间 | 完整分析器和同义词表未公开；路径不敏感会增加误报；作者列表高度重复 | 保存全部作者候选，再绑定当前身份 |
| PGFuzz 命令/环境动态映射 | 能发现名称难以推断的运行相关性和旧实验前置顺序 | 单输入标准差不证明因果；论文与代码的时长和次数不一致；状态类别会合并不同物理量 | 作为候选排序证据，不作为因果证明 |
| ADGFuzz 赋值依赖图 | 能沿多层赋值自动扩大组合并设置优先级 | 正则解析不理解完整 C++；丢失常量、分支和对象；论文与代码评分不同 | 仅供下一阶段扩展已知 AP 的候选输入，不产生性质 |

## 九、默认配置在实际运行中能否更改

结论是：很多参数原则上可以通过飞控参数机制覆盖源码默认值，但本数据集没有逐参数证明它们能在飞行中立即修改或立即生效。

必须区分四层：

1. 作者历史默认值：PGFuzz 旧测试种子中的值。
2. 当前源码默认值：当前版本没有保存覆盖值时采用的初始值。
3. 冻结运行值：某一次 SITL 参数下载中的实际值。
4. 写入验证：实际写入、回读并观察模块何时使用新值。

当前所有 `runtime_write_change_verification` 都是 `NOT_TESTED`。因此本数据集不能保证：飞行中允许修改、解锁状态下是否拒绝、是否需要重启、哪个控制周期开始生效、是否持久保存，以及参数虽被协议回读但目标控制路径是否已经重新消费。

`current_reboot_required` 为空也不能解释为“不需要重启”；它可能只是当前参数目录没有提取到该元数据。对公式直接涉及的 7 个唯一 ArduPilot 参数，本数据集额外保存了参数目录原值、规范化表达式、冻结源码复核默认值和具体源码证据；运行可变性仍保持未测试。

## 十、必须人工关注的未解决项

- 14 个 AP 和 13 条词项绑定为 `UNRESOLVED`。
- `GroundALT` 没有统一类型和参考面；“已落地”、Home 高度和地形高度不能相互替代。
- 论文 `GPS_fail` 与当前 GPS 接收器状态、EKF（`Extended Kalman Filter`，扩展卡尔曼滤波器）位置有效性及故障保护动作没有一对一等价关系。
- Guided 模式的 `Waypoint=empty` 没有可证明等价的单一当前布尔字段。
- `k` 没有公开逐性质测量轨迹，不能补人工秒数。
- PX4 历史 `COM_POS_FS_DELAY` 已删除。当前 `EKF2_NOAID_TOUT` 是微秒制惯性航推超时，`COM_POS_FS_EPH` 是米制位置精度阈值；二者都不是等价替代项。
- 作者依赖文件遗漏 4 个公式直接参数：`CHUTE_ALT_MIN`、`RTL_LAND_DELAY`、`MPC_LAND_SPEED`、`MPC_TKO_SPEED`。
- 论文转录保留 A.FLIP1 极性/优先级冲突、A.RC.FS1 漏印武装前件、A.GPS.FS1 蕴含方向相反、PX.RTL4 参数冲突、PX.ORBIT6 类型/单位冲突、PX.HOLD2 条件遗漏和 PX.TAKEOFF1 目标等式弱化等问题。

## 十一、验证与禁止声称的结论

五个验证器的最终结果如下。这里的“检查项”是程序实际执行的布尔断言数量；数量越多不代表性质越正确，只表示交付内部的一致性检查更细。

| 验证对象 | 检查项 | 失败项 | 报告 |
|---|---:|---:|---|
| 51 条公式及 178 个 AP 的转录 | 292 | 0 | [formula_inventory_validation.json](validation/formula_inventory_validation.json) |
| 7,569 条作者候选关联和 356 个当前输入身份 | 98,275 | 0 | [author_dependency_validation.json](validation/author_dependency_validation.json) |
| 227 条当前源码绑定、178 个 AP 的绑定选择及 196 个类型/单位原值解释 | 11,700 | 0 | [source_binding_validation.json](validation/source_binding_validation.json) |
| 51 条逐性质记录、证据连接和 221 个字段中文解释 | 11,096 | 0 | [property_record_validation.json](validation/property_record_validation.json) |
| 65 个 Markdown 文件的本地文件和行号链接 | 16,366 个本地链接 | 0 | [local_link_validation.json](validation/local_link_validation.json) |

此外，最终只读链接检查覆盖 65 个 Markdown 文件中的 16,366 个本地文件链接，其中 16,054 个链接带有源码或作者制品行号；目标文件和行号均有效。该链接检查只证明交付位置可打开，仍不证明绑定在语义上等价。

验证命令：

```bash
python3 benchmark/PGFuzz_MTL51/scripts/validate_formula_inventory.py
python3 benchmark/PGFuzz_MTL51/scripts/validate_author_dependencies.py
python3 benchmark/PGFuzz_MTL51/scripts/validate_source_bindings.py
python3 benchmark/PGFuzz_MTL51/scripts/validate_property_records.py
python3 benchmark/PGFuzz_MTL51/scripts/validate_local_links.py
```

最终验证报告位于 [validation](validation/) 目录。通过这些检查后，仍然禁止声称：

- 51 条公式均为当前官方规范；
- 51 条公式均为语法和语义正确的严格 MITL；
- 当前 ArduPilot 或 PX4 满足/违反这些性质；
- 7,569 条作者关联均为已证明的因果依赖；
- 协议 XML 中存在某消息或命令就等于当前构建一定发送、接收或执行；
- 冻结运行值就是不可修改的默认值；
- 已经执行用户下一阶段要求的当前源码依赖静态分析、完整模糊测试活动或固件符合性验证。
