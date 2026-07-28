# TAFuzz 项目状态

最后更新：2026-07-29 CST（China Standard Time，中国标准时间）。

## 当前活动任务：ArduPilot 45 条 MITL 性质的命题三分类

状态：**命题分析已经完成；尚未修改 ArduPilot 源码，也尚未生成或接入任何探针。**

- 分析文件：`analysis/ardupilot_45_properties_ap_three_type_instrumentation_analysis_zh.md`。
- 范围严格限定为两份性质文件中当前公式的叶子命题：PGFuzz 历史 30 条和当前新提取
  15 条，共 45 条性质。
- `AP` 是 `Atomic Proposition`，中文为“原子命题”，即公式中最终判断真、假或无法
  确定的最小条件。
- 所有命题只分三类：持续状态命题、瞬时事件命题、记忆派生命题。参数、单位、有效性、
  坐标系和实例编号是命题附属信息，不增加新类型；模糊输入及其影响关系不属于本次分类。
- “真值未闭合”只表示尚缺精确布尔判定条件，不是第四类；对应命题暂不生成探针，避免
  人工猜测。
- 验证结果：矩阵正好 45 行、45 个唯一性质编号，其中历史性质 30 条、新性质 15 条；
  无重复编号，文档中没有“影响关系型”或“输入流型”分类。
- 工作树复查：ArduPilot 仍只有既有 `modules/CrashDebug` 状态；PGFuzz 保留既有缓存、
  PDF 和 SVF 目录；PX4、Paparazzi 干净；MightyPPL、MoniTAal 保留既有用户修改。

下一步（最多三项）：

1. 由用户先审核三类定义和 45 条逐条矩阵。
2. 用户确认后，再把每条性质的命题整理成三类统一接口所需的精确合同。
3. 只有收到明确实施指令后，才修改 ArduPilot 源码并接入探针。

## 前一活动任务：MITL 公式到可复用插桩编译方法

状态：**MITL-FIC 已按实际 fuzz 工作流修订为“单性质周期完整采样”第二版；尚未实现
代码生成器，尚未修改飞控源码，尚未执行运行时实验。**

- 新设计：`analysis/mitl_formula_to_instrumentation_compiler_design_zh.md`。
- 新模式：`analysis/mitl_single_property_instrumentation_schema_v2.json`；已删除被取代的
  多公式第一版模式，避免两套接口并存。
- `MITL-FIC` 是 `MITL Formula-to-Instrumentation Compiler`，中文为“MITL 公式到插桩
  编译器”。它可以反复为不同公式生成实例，但一次 fuzz 会话只选择一条性质、只激活该
  公式的 AP、只建立一个 TAMonitor 会话。
- 核心算法包括：单性质 AP 合同；真实语义位置的状态缓存和瞬时事件锁存；基于共同后
  支配点或版本化多点快照的采集计划；性质专用固定周期的完整真假/已知性采样；最小
  `TAFUZZ_PROPERTY_SAMPLE` 消息；丢包、乱序和重启下的单性质部分赋值恢复。
- 运行时不再执行多公式分组、跨公式 AP 装箱或多性质同时监测。正常消息只含
  `session_id`、`sequence`、`source_time_us`、`truth_bits` 和 `known_bits`；性质、位序、
  源码提交和参数哈希在会话清单中绑定，原始值只进入可选审计日志。
- 当前 TAMonitor 边界已明确：`TraceParser.cpp` 只接受完整 `0/1` 标签，`TimedEvent` 没有
  `known_bits`，且当前入口先读取事件向量再运行。部分赋值与 MAVLink 持续流式会话属于
  后续必须实现的功能，不能写成现有能力。
- 正确性目标已改为采样轨迹语义：第 `k` 个样本必须等于真实飞控采样时刻上当前性质
  全部 AP 的真假和已知性。采样间不可见变化、跨源时间区间和瞬时事件次数必须通过锁存、
  有界队列或未知状态处理；当前不宣称无条件等价于连续时间 MITL。

验证：JSON 语法复读和 JSON Schema 2020-12 元模式检查通过；第二版设计文档 573 行，
第二版模式文件 273 行。ArduPilot 仍只有既有 `modules/CrashDebug` 状态；PX4、Paparazzi
干净；MightyPPL、MoniTAal 保持用户既有修改，未清理或重置。

下一步（最多三项）：

1. 用第二版模式表达 `A.ALT_HOLD2`，冻结其四个 AP、单性质采样周期、有效性和源码锚点。
2. 实现单性质 AP 缓存/锁存、周期采样器、最小 `TAFUZZ_PROPERTY_SAMPLE` 和 GCS 会话。
3. 扩展 TAMonitor 的单公式流式会话与部分命题赋值，并执行周期采样端到端差分测试。

## 前一活动任务：TAMonitor 运行时验证科技报告

状态：**科技报告已在第四版“一个总成果、两个成果内容”结构上新增正式摘要，并将验收口径统一更新为四类缺陷和 90% 准确率目标；四张图、论文式算法图和 Word 原生公式均已嵌入，实际评审、测评和实验数字仍待完成。**

- 报告名称：《基于运行时验证的安全性质违反精确判定方法研究报告》。
- 可编辑源稿：`documents/基于运行时验证的安全性质违反精确判定方法研究报告.md`。
- 正式 Word 文档：`documents/基于运行时验证的安全性质违反精确判定方法研究报告.docx`。
- 可重复生成脚本：`documents/build_tamonitor_research_report.js`。
- 总成果名称固定为“面向运行时安全性质违反的精准判定技术”，下设“基于时间自动机
  引导的模糊测试框架”和“双层半符号化运行时验证工具原型”。开篇先写成果和两项内容，
  再按“问题与挑战—国内外研究现状—方法整体框架与关键技术—算法—实验—取得成果”
  展开；模糊测试只说明组件、数据流与反馈接口，不展开具体变异算法。
- 图件位于 `documents/figures/`：总体成果图、时间自动机引导模糊测试框架图、双层
  半符号化运行时验证图和 TAMonitor 核心算法图；后三张同时保留 SVG 矢量源文件。
- 图 3 的图内标题和正文图注均已改为“双层半符号化运行时验证方法框架图”；深蓝、紫色
  箭头头部由 12×12 缩为 8×8，避免遮挡公式、层标题和状态框文字。成果内容二的名称仍
  保持“双层半符号化运行时验证工具原型”，没有随图题改名。
- Zotero（本地文献管理软件）只读筛查覆盖“运行时验证”及全部子集合和“fuzz + rv”
  集合：219 条集合归属，按条目键去重为 207 条；186 条有已索引全文，21 条只有元数据、
  摘要或网页记录。第四版正文使用 20 篇且全部实际引用：16 篇集中于运行时验证、MITL、
  时间自动机、区域监测与 BDD，另用 4 篇只支撑模糊测试框架的组件和闭环关系。
- 方法结论绑定当前源码：正负自动机构造、统一命题位序、BDD（Binary Decision Diagram，
  二元决策图）标签精确投影、DBM（Difference-Bound Matrix，差分约束矩阵）区域状态、
  接受空间剪枝和三值前缀结论；未把 `compflatten` 或 BDD 原生运行时接口写成已实现。
- 成果主线为 MITL 性质自动规范化、正负时间自动机构造、监视器合成、BDD 离散命题
  压缩、DBM 连续时间可达和三值在线判定。BDD 的直接收益严格限定在当前已实现的构造
  与运行前标签投影阶段；未把尚不存在的 BDD 原生在线迁移或示意图比例写成实验事实。
- 指标映射已写入摘要、成果概述和实验章：方法研究指标为“实验验证自动生成对违背时序
  约束的运行时监控器功能”，由专家评审；工具指标为检测违背时序约束、异常或非法操作、
  资源使用异常、看门狗超时四类缺陷且运行时检测准确率不低于 90%，由第三方测评。实际
  状态全部为待评审或待测评，未把目标值写成既有实验结果。
- 检测准确率暂定为“与独立真值一致的有效轨迹数/全部有效测评轨迹数”；完成轨迹上的
  `INCONCLUSIVE`、内部构造失败或工具错误按未正确检测记录，不从分母剔除。最终口径和
  数值以冻结的第三方测评大纲及报告为准。

验证：`node --check`、Word 生成和 `unzip -t` 通过；正文有 57 个一至四级标题、12 个
表格、4 张嵌入 PNG 图和可更新的 1--4 级目录域。Word XML 含 87 个原生 OMML 公式对象，
其中有 1 个堆叠分式、55 个下标、20 个上标、10 个上下标组合，且不含残留 LaTeX 命令。
正文引用编号和 20 条参考文献严格对应。Markdown、Word 和构建脚本当前 SHA-256 分别为
`912f6895eff7c727fcbd7b95eebef376fe5fecb989fd6b19bae2ef22cff2ce6c`、
`7a73f66c50505e5520d08849a5d222b8a67dc034c16c47b2dfd5d5b5d5db6843` 和
`071432a07875686b3ae52350aa2af4405d125ed20a576587f283ce9171231193`。

下一步（最多三项）：

1. 按第 2.4.4 节准备并执行自动生成运行时监控器的功能实验，形成专家评审材料。
2. 与第三方冻结四类缺陷用例、90% 准确率口径和工具版本，执行测评并填写第 2.4.6 节。
3. 后续补充模糊测试具体算法和实验时，继续把反馈启发式与运行时判定结论分开。

## 保留任务：ArduPilot AP 影响输入静态分析方法

状态：**近期方法调研和 v1 设计已完成；尚未实现或运行真实 ArduPilot
source→AP 分析。**

- 新报告：`analysis/ardupilot_ap_input_static_analysis_design_zh.md`。
- 唯一推荐方法为“AP 锚定的分层后向影响切片”：当前构建的 SVF 3.2
  反向 SVFG 为数据主干，只在值切片命中的函数内补控制依赖，再用版本化
  ArduPilot 语义桥补 MAVLink、AP_Param、RC、调度/事件缺失和 SITL 传感器边界。
- 静态结果只输出候选输入、逐边证据、`MUST_DATA/MAY_DATA/CONTROL/MODELLED/UNKNOWN`
  和冷启动先验；不得推断 AP 真/假方向、实际可达性、精确触发时间或 MITL 符合性。
- `UNKNOWN` 与数值 cost 分离；`p` 和 `!p` 使用相同静态特征。动态阶段以后只按完整
  布尔边 `false -> true` 校准，冻结边权后再计算反向剩余 cost。
- 当前硬门槛：虽有 1,336 TU 的 Clang 18 Copter-only 编译数据库快照和已验证的
  SVF 3.2，但没有与当前提交和真实 ArduCopter SITL 链接闭包绑定的整程序 bitcode；
  旧 LLVM 13 `copter_4_1_llvm_13.bc` 不得作为当前证据。

下一步（最多三项）：

1. 在隔离目录重建当前提交的 Clang 18 LLVM IR，并按真实 SITL 链接命令冻结闭包。
2. 冻结 `mode==RTL`、`failsafe.gcs`、`high_vibes` 三个 AP 的 sink 和结构化 source 清单。
3. 先实现纯 SVFG 后向路径导出，通过后再加入局部控制依赖和最小语义桥。

## 前一活动任务：PGFuzz 56 条性质重新审计与三飞控当前规范提取

状态：**里程碑 1--7 已完成。ArduCopter、PX4、Paparazzi 各两份结果文档、当前
源码绑定、三系统可观测性总分析、临时公式总表和最终一致性验证均已交付。所有性质
继续保持“实现符合性：未评估”，本任务不宣称飞控满足整条性质。**

本任务最终只在 `benchmark/PGFuzz重新审计/` 新增七份结果文档；判断状态全部
使用中文，论文公式、参数、消息和源码标识符保持原名并在首次出现处解释。

用户在里程碑 2 完成后明确增加第八份临时结果文件
`benchmark/PGFuzz重新审计/全部公式与来源_临时.csv`。CSV（Comma-Separated
Values，逗号分隔值表格）当前含论文 56 行和三系统新性质 28 行，共 84 行。这是对原
“只新增七份文档”约束的明确例外；公式、来源链接与实现符合性字段已经齐备，最终
验证后封表。

### 里程碑 1 冻结结果（2026-07-23）

- PGFuzz 论文 PDF（便携式文档格式文件）SHA-256（用于核对文件内容是否完全
  一致的 256 位哈希值）：
  `bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa94c90d7fcd`；
  Zotero 原件与工作区副本一致。
- PGFuzz 公开仓库：`7eaebf21116087249b8329d4ba7337a24a34ecb9`。保留既有
  Python 缓存、论文文件和 `SVF-data-flow/`，未清理或重置。
- ArduCopter：`8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`；只观察到用户
  既有 `modules/CrashDebug` 子模块脏状态，未修改。
- PX4 v1.17.0 多旋翼：
  `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`；工作树干净。
- Paparazzi 官方 `master`（主开发分支）冻结为
  `b51490c88bf972b764229d5f034957a41b6ce57c`，日期 2026-07-22；采用
  `conf/conf_example.xml` 中官方 `Bebop2` 配置及其 NPS（Networked Physics
  Simulation，网络物理仿真）目标；工作树干净。所需子模块提交已记录，未初始化的
  可选子模块不冒充已冻结依赖。
- ArduPilot 官方文档当前提交为
  `826ef054a04e23b1ceeb3fb01a4df1d270efebcd`。本地完整快照为
  `209e532bc97e5a41966f8c9ab483323c264cae08`；两者的全部 Copter 文档无差异，
  Common（共用）文档只有 AIS、合作伙伴、测距仪等 9 个与本任务无关的页面变化。
  因远端补取 9 个缺失对象两分钟超时，穷尽扫描使用本地完整快照，涉及性质的页面再
  以当前提交固定链接复核；不得把这项限制写成“当前全部文档已本地检出”。

### 当前阻塞与验证边界

- 没有阻塞里程碑 2 的问题。
- 本阶段只冻结版本，不代表任何性质已通过当前规范审计或当前飞控符合性检查。
- `/tmp/tafuzz-ardupilot-wiki-current` 是失败的临时稀疏工作区，不作为证据；
  主文档克隆保持干净。

### 里程碑 2 复核结果（2026-07-23）

- 以 PDF 第 18 页原始图像为主证据，文字层为检索辅助，复核出 ArduPilot 30 条、
  PX4 21 条、Paparazzi 5 条，共 56 条；不是沿用 51 条旧数据后推测 Paparazzi。
- PX4 的 `PX.ORBIT1-4` 在论文中合并为一行，但计数和最终表均拆成四条；
  `PX.RTL5`、`PX.ALTITUDE1`、`PX.HOLD1`、Paparazzi 的 `PP.HoverZ`、
  `PP.HoverC` 均保留论文“与另一条相同”的印刷文字，再另列展开式。
- 原样保留并标注的主要问题包括：`A.LAND1/2` 的悬空合取符；`A.FLIP3`
  把时序算子写进等式右端；`A.FLIP1` 的括号和正反条件冲突；`PX.RTL4` 的自然语言
  写 `RTL_LAND_DELAY=-1`、公式却写 `RTL_DESCEND_ALT=-1`；`PX.ORBIT6`
  自然语言要求加速度，公式却比较 `Circle_speed` 与 `2m/s²`；多条“直到/移动到/下降”
  要求在公式中被弱化为相邻样本变化。
- 所有 `t-1` 固定解释为同一运行、同一语义坐标系中的上一条有效观测；论文没有给
  采样周期，因此绝不解释为一秒前。`k` 继续保留为论文经验时间，不伪装成官方时间。
- 现有 51 条结构化清单仅用于逐字符交叉检查；Paparazzi 五条重新从页面读取。当前
  结果文档尚未写入判断结论，需在里程碑 3 后与作者输入关联一起落表。
- 临时公式总表已写入 56 行并用 CSV 解析器复读：56 个唯一编号，系统计数
  30/21/5，全部“实现符合性”为“未评估”。Paparazzi 两条继承式在当前源码身份
  查清前不擅自展开，`PP.HOME1` 也未人工补造距离函数。

### 里程碑 3 作者制品核对结果（2026-07-23）

- 公开仓库包含 ArduPilot 28 个性质目录、PX4 21 个性质目录，每个目录均有
  `parameters.txt`、`cmds.txt`、`envs.txt`、`preconditions.txt` 四类文件；公开仓库
  没有 Paparazzi 性质目录。
- ArduPilot 论文 30 条与 28 目录的关系：`A.FLIPGeneral` 使用 `A.FLIP4`；
  `A.CHUTE1` 使用 `A.CHUTE`；`A.CIRCLE4/5/6` 共用 `A.CIRCLE4_6`。源码监视块也
  以 `A.FLIP4`、`A.CHUTE`、`A.CIRCLE4-6` 命名。
- PX4 的 `PX.ORBIT4/5` 共用 `PX.ORBIT4_5`；代码另含论文表 XII 没有的
  `PX.CHUTE` 目录和监视块。因此“21 个目录”不能直接解释成“21 条论文性质各有
  独立目录”。
- 共解析 7,569 条性质—输入关联：配置参数 2,501、命令/遥控 2,079、环境因素
  2,984、明确前置设置 5。因共享目录，去除重复后的原始文件行是 7,311 条。
  其中 7,564 条只能标为作者候选关联，5 条明确前置设置全来自
  `A.CHUTE/preconditions.txt`：`CHUTE_ENABLED=1`、`CHUTE_TYPE=10`、
  `SERVO9_FUNCTION=27`、`SIM_PARA_ENABLE=1`、`SIM_PARA_PIN=9`。
- 对所有 7,569 条记录重新核验制品文件 SHA-256、行号和原文，错误为 0；只有 18 条
  关联的输入名直接出现在公式词项中，不能把其余候选写成已证明因果关系。
- 论文流程复核：先拆性质词项；用 LLVM IR（LLVM Intermediate Representation，
  LLVM 编译器中间表示）的定义—使用链和人工同义词表映射配置参数；再用仿真标准差
  实验识别命令/环境影响与输入先后依赖；合并成性质输入表；未知 `k` 通过 100 次仿真
  响应的最大值确定。A.BRAKE 的论文示例为 12.7 秒，属于论文经验时间。
- 代码偏差：第六列被解析器命名为单位，但制品中常表现为步长；ArduPilot 的
  A.FLIP2 直接把不可监测的横滚速率当真；A.FLIP3 未实现 `k` 时间窗；A.GPS.FS1
  与 A.BRAKE 使用循环“再给两次机会”，不能解释成秒；PX.GPS.FS1 把
  `COM_POS_FS_DELAY` 数值直接与循环计数比较，也没有证明循环周期为一秒；PX4
  参数无上下界分支还存在条件写反的代码问题。结果文档会把论文、制品和代码三层分开。

### 里程碑 4 完成结果（2026-07-23）

- 已生成 `benchmark/PGFuzz重新审计/ArduPilot/PGFuzz原性质_当前审计.md`：严格
  30 行主表、30 个逐性质折叠明细；完整保留作者候选输入，并把全部判断状态翻译为中文。
- 已生成 `benchmark/PGFuzz重新审计/ArduPilot/当前新提取MTL性质.md`：15 条高置信
  性质，其中官方固定阈值 7 条、可修改参数时间 5 条、无界 3 条。固定阈值公式已从
  错误的点区间改为“阈值前禁止、阈值起无界最终发生”，避免把 MTL 点时刻误称 MITL，
  也没有擅自补有限最晚上界。
- 临时公式 CSV 已更新为 71 行、71 个唯一编号：论文 56 行 + ArduCopter 新性质
  15 行；所有公式和来源链接非空。
- 验证：两份 ArduCopter 文档中 577 个冻结官网/源码链接全部能映射到本地文件且行号
  有效；历史主表严格 30 个唯一编号；CSV 编号唯一、公式和来源非空。
- 4,225 个语料文件全部完成预筛，19,003 条候选全部完成范围与证据闭合裁决：直接
  支撑接受性质的候选跨度 21 条；范围外 2,522 条；普通实现注释 10,348 条；仅参数
  元数据或缺少完整条件—义务关系 724 条；官方文本证据不足 5,388 条；待审核 0。
  `ARD-NEW-AUTO-015` 来自上下文阅读但未被关键词命中，单独记录，避免把预筛召回率
  冒充完整语义覆盖。
- 裁决不是 19,003 次逐字人工阅读：先按范围、来源类型和已接受证据跨度逐条确定性
  分类，再对闭合性质做上下文审核；所有未闭合条目继续保留为证据不足，不人工补造。
- TAMonitor 全量轨迹验证仍按原计划归入里程碑 7，不影响里程碑 4 的提取与裁决验收；
  当前 15 条监视器结果仍明确写为待验证。
- 工作树复查：ArduPilot 仍只有既存 `modules/CrashDebug` 脏状态；PX4、Paparazzi
  干净；PGFuzz 仍只有既存缓存、PDF 与 `SVF-data-flow/`，未清理或重置。

### 里程碑 5 完成结果（2026-07-23）

- 生成 `benchmark/PGFuzz重新审计/PX4/PGFuzz原性质_当前审计.md`，主表严格
  21 条；每条含论文原式、当前式、官方固定文档行、原子命题、当前源码变量/函数、
  作者全部候选输入和时间边界。
- 生成 `benchmark/PGFuzz重新审计/PX4/当前新提取MTL性质.md`：5 条证据闭合
  性质和 1 条 Offboard 证据不足候选；所有参数均分开记录源码默认值、冻结 SITL
  运行值和可修改性。`COM_FLT_TIME_MAX=-1` 明确表示本次配置未激活，而非性质删除。
- PX4 17,148 条预筛候选全部裁决：接受来源跨度 30、范围外 440、普通实现注释
  10,557、参数元数据证据不足 329、官方文本证据不足 5,792、待审核 0。
- 临时公式 CSV 现为 77 行：论文 56 + ArduCopter 新 15 + PX4 新 6；编号唯一且
  公式/来源非空。两份 PX4 文档的 539 个固定链接本地路径和行号错误为 0。
- 工作树复查：PX4、Paparazzi 干净；ArduPilot 仍只有既有 CrashDebug 子模块状态。

### 里程碑 6 完成结果（2026-07-23）

- 生成 `Paparazzi/PGFuzz原性质_当前审计.md`，论文主表严格 5 行；将 Hover 拆成
  `autopilot.mode`、`guidance_h.mode`、`guidance_v.mode` 三层，并逐项列出位置、
  高度、偏航、任务块、HOME 目标的定义、更新、消费和消息发送位置。
- 生成 `Paparazzi/当前新提取MTL性质.md`：3 条含固定任务时间阈值、4 条无可靠有限
  上界的性质。10 秒、3 秒只来自冻结飞行计划的 `block_time/stage_time` 条件；2 米、
  4.5 米/秒和 150 米明确是空间/速度配置，不人工换算成保证时间。
- 冻结 Bebop2 默认使用 PPRZLink；默认 `ROTORCRAFT_STATUS`、`ROTORCRAFT_FP`、
  `ROTORCRAFT_NAV_STATUS` 与可选 MAVLink 路径分开标记，未把模块存在冒充当前启用。
- Paparazzi 范围的 1,704 个去重语料路径完成高召回预筛，17,645 个行命中按系统范围、
  来源类型和完整条件—义务关系裁决；普通控制流只用于绑定，不产生性质。作者公开制品
  没有 Paparazzi 输入目录，所有作者依赖均如实保留为“公开制品未提供”。
- 临时公式 CSV 更新为 84 个唯一编号：论文 56 + ArduCopter 新 15 + PX4 新 6 +
  Paparazzi 新 7。两份 Paparazzi 文档 66 个固定源码/文档链接的文件和行号错误为 0。
- 工作树复查：Paparazzi、PX4 干净；ArduPilot 仍只有既有 CrashDebug 子模块状态；
  PGFuzz 仍为既有缓存、论文文件和 `SVF-data-flow/`，未清理或重置。

### 里程碑 7 完成结果（2026-07-23）

- 生成 `三系统原子命题类型与MAVLink可观测性总分析.md`。论文 56 条共拆出
  194 个原子命题：可直接观测 66、可计算得到 22、条件可观测 58、需要插桩 34、
  无法确认 14；另逐条覆盖当前新提取的 28 条性质。
- 可观测性严格区分协议定义、源码静态支持、配置启用和本次仿真实际出现四层。
  ArduPilot 静态枚举 1,056 个车型—消息组合，本次观测到 146 个组合；PX4 静态
  支持 251 个消息编号，本次观测到 54 个。Paparazzi 冻结 Bebop2 默认采用
  PPRZLink；其 MAVLink 是可选配置，未把静态模块存在写成运行时已观测。
- 统一结构验证通过：历史表严格为 30/21/5 行且编号唯一；当前新性质为 15/6/7；
  临时 CSV 为 84 行、84 个唯一编号，公式和来源均非空，所有实现符合性均为“未评估”。
- 共验证七份文档中的 1,192 个冻结 GitHub 链接，全部可映射到相应冻结本地源码或
  文档文件且行号有效；七份文档中的英文判断状态残留数为 0。
- `TAMonitor`（本项目的时间自动机性质监视器）执行门当前覆盖 8 条公式、49 条轨迹：
  6 条通过，1 条因边界期望不一致而失败，1 条因无限运行语义不受当前执行器支持而
  未执行；其余 22 条新性质没有冒充已通过监视器验证。
- Paparazzi NPS（网络物理仿真）构建因本机缺少 `ocamlbuild`（OCaml 构建工具）
  未完成；`sudo` 需要交互密码且 `opam` 尚未初始化。故 Paparazzi 的源码、配置和
  静态消息绑定已完成，但运行时消息捕获明确保留为未验证，不影响源码身份映射结论。
- 最终工作树保护检查：PX4、Paparazzi 干净；ArduPilot 仍只有既有
  `modules/CrashDebug` 状态；PGFuzz 仍只有既有缓存、论文和 `SVF-data-flow/`；
  MightyPPL、MoniTAal 的用户修改均未覆盖或重置。

### 本任务后续（最多三项）

1. 等待用户下一个静态分析任务指令。
2. 若用户要求 Paparazzi 运行时证据，先补齐 OCaml 构建依赖，再构建 Bebop2 NPS。
3. 若用户要求扩大监视器覆盖，优先处理当前 1 条边界期望不一致和 1 条无限运行限制。

## 以下为前一任务历史状态（不再是当前目标）

## 当前目标与状态

当前目标：从 Zotero 的固件模糊测试和分布式实时系统文献中筛选具有固定、非参数
时间约束的 MITL（Metric Interval Temporal Logic，度量区间时序逻辑）实验背景，
并补审计 ArduPilot 官方行为规范、冻结源码和可执行 SITL 路径。

状态：**47/47 个 Zotero 顶层条目已分类，固定时间 MITL 候选报告已完成；
ArduPilot 筛出 6 组优先性质，但尚未实跑这些新增性质。既有离线布希引导原型仍是
12/12 单元测试通过，完整 SITL（Software In The Loop，软件在环仿真）在线闭环
尚未完成。**

## 2026-07-23 — 固定时间 MITL 背景与基准审计

- 新增 `analysis/zotero_fixed_time_mitl_benchmark_audit_zh.md`，完整覆盖 Zotero
  “模糊测试/固件 fuzz 综述”34 条和“运行时验证/分布式实时系统”13 条。
- 新增只读快照脚本 `analysis/scripts/snapshot_zotero_collections.py`，冻结两目录元数据
  与已索引全文到 `analysis/data/zotero_mtl_source_snapshot/`；脚本通过 Python 语法
  编译检查，报告核对表确认为 34+13 条。
- 已按用户要求丢弃既有公式清单作为证据，直接从 PGFuzz 原论文 PDF 第 18 页重读
  表 XII：原表 56 条，其中 ArduPilot/PX4 51 条只有 5 条印刷公式含有界 `F`，
  仅 `A.FLIPGeneral` 直接使用固定数值 `[0,2.5]`；其余依赖经验量 `k` 或运行参数。
- ArduPilot 新候选：振动保护 1 秒触发/15 秒恢复、降落伞连续 1 秒、坠毁检查
  2 秒、EKF 故障保护 1 秒、地形数据官方 2 秒对源码 5 秒、左舵解除官方 2 秒对
  源码 3 秒。后两者及降落伞连续性目前只是规范—源码冲突候选，
  `implementation_satisfaction` 仍为 `NOT_ASSESSED`。
- 其他背景排序：Mecel 齿轮控制器最容易立即接入，但时间是基准模型常量；联合国
  第 152 号自动紧急制动法规是最强外部固定规范且有自动驾驶模糊测试生态；铁路道口
  时间规范最清楚但现有性质引导模糊测试链较弱；CPFuzz/ARCH-COMP 适合算法对照，
  不能冒充外部规范。
- 本轮只做文献、网页、源码和模型只读审计；没有运行完整模糊测试批次，也没有对
  新增性质作符合性判断。

## 2026-07-22 — MITL 布希套索引导原型

- 冻结并审计本地 `benchmark/rift/external/ltl_fuzzer`，提交为
  `716ac301fa3a8ea39814bc80eeebba49c19c1378`；同时核对 GitHub 当前
  `main` 的关键源码。
- 论文与源码审计结论：无界未来性质不能因有限执行一次进入接受状态而判
  违反；LTL-Fuzzer 使用程序状态重复与接受循环构造 lasso（套索形轨迹）
  候选。公开代码主要检查接受状态的直接自环，且论文中的前缀适应度在
  当前公开 `PathStore.cc` 中退化为常数 `1.0`。
- 新增 `src/StaticAnalysis/runtime/mitl_buchi_guidance/`：
  - `model.py` 定义运行时前缀、精确 PTA（Priced Timed Automaton，赋价
    时间自动机）代价、性质状态投影和配置契约；
  - `engine.py` 实现多边接受循环、正时间约束、接受不动点约束、跨独立
    重放确认、种子优先级和变异候选排序；
  - `cli.py` 读取逐行 JSON（JSON Lines，简称 `JSONL`）前缀、当前
    TAMonitor 的 `pta_prefix_costs.jsonl` 与配置，输出引导和汇总；
  - `examples/` 只含明确标记的合成绑定，不宣称为真实 ArduPilot 映射。
- 新增详细中文报告
  `analysis/ltl_fuzzer_mitl_buchi_guidance_zh.md`，逐项对应论文、代码、
  PGFuzz、MoniTAal、现有 TAMonitor 接口和生产接入步骤。

## 已锁定的语义边界

- `FINITE_VIOLATION`：有限前缀已经足够判定违反，只允许有界截止性质或
  其他终止否定性质使用。
- `LASSO_CANDIDATE`：单次执行中观察到正时间接受循环，只是高优先级测试
  候选，不是无界性质的形式化反例证明。
- `REPLAY_CONFIRMED_LASSO`：至少两个不同 `run_id` 的干净重放具有相同
  事件、组合状态和相对时间签名；仍按模糊测试证据解释。
- `INCONCLUSIVE`：证据不足；不得解释成性质满足。
- 无界性质即使监视器在有限前缀给出 `NEGATIVE`，原型也不会输出
  `FINITE_VIOLATION`。
- 套索组合键只含否定自动机位置、性质时钟区和显式性质状态投影；绝对
  单调时钟只用于证明循环经过正时间，不进入重复状态摘要。
- 只有 `domain_status=complete` 且 `aggregate.exact=true` 的 PTA 记录
  可以驱动剩余代价、下一自动机边和变异选择。

## 验证结果

执行：

```text
cd src/StaticAnalysis/runtime/mitl_buchi_guidance
python3 -m unittest discover -s tests -v
```

观察：12/12 通过，覆盖单次接受命中拒绝、零时间循环拒绝、一般多边接受
循环、相同/不同定时重放、有限/无界判定隔离、不完整 PTA 关闭引导、绝对
时钟投影隔离，以及真实 PTA 输出解析。

端到端示例观察：6 个逐前缀记录、2 个套索记录；同一套索在两个独立运行
中确认，最高种子阶段为 `REPLAY_CONFIRMED_LASSO`，未产生有限违反。

真实文件
`test/TARV/results/pta_prefix_mighty_cost3_z3_20260712-042251/pta_prefix_costs.jsonl`
可直接读取，测试确认前五个精确剩余代价为 `8 -> 5 -> 4 -> 2 -> 0`。

## 尚未完成和不能声称的内容

- 尚未为 TAMonitor 无限词模式实现只读 `BuchiPrefixObserver`；现有有限词
  `PrefixRuntimeObserver` 不能直接复用终止语义。
- 尚未生成真实 ArduPilot `observation_plan.json`，也未在性质对应源码点
  接入 `TAFUZZ_EMIT` 与 `AP_HAL::micros64()` 飞控源时间。
- 尚未把 `next_edge` 接入 PGFuzz 动态影响目录和实际 SITL 变异执行器。
- 尚未在真实性质、真实 ArduPilot 插桩和固定预算下完成 PGFuzz 对照与
  消融实验，所以“优于 PGFuzz”目前是有具体机制支撑但仍待实验验证的假设。
- 没有运行完整模糊测试 campaign（完整批次），也没有真实硬件结论。

## 相关既有里程碑

- PGFuzz 动态迁移 M0--M4 已完成；最终三用例烟雾测试为 `PASS`，但用户
  尚未运行完整 `current_safe_full` 批次。
- `benchmark/PGFuzz_MTL51/` 的 51 条历史性质记录已完成；全部保持
  `implementation_satisfaction=NOT_ASSESSED`，即未评估当前固件符合性。
- RIFT-M5 继续停在既有检查点，不因本次原型自动恢复。

旧的详细状态已原样归档为
`.codex/archive/PROJECT_STATE_2026-07-20_pgfuzz_dynamic_m4.md`。

## 必须保留的本地状态

- 工作区根目录不是 Git 仓库，不能执行根级 Git 命令。
- ArduPilot 的 `modules/CrashDebug` 是既有用户改动，不得清理或重置。
- `tool/MightyPPL` 和 `tool/MoniTAal` 是独立嵌套 Git 仓库；本次没有修改。
- LTL-Fuzzer 冻结目录已有构建产物；本次只读审计，没有清理或重置。

## 下一步（最多三项）

1. 以振动保护为代表案例，生成 `requirement.md`、`formula.mitl`、
   `observation_plan.json`，并用源端单调时钟跑出第一条真实 SITL 轨迹。
2. 为地形 2/5 秒、左舵 2/3 秒和降落伞连续性建立定向输入与重放测试；运行前保持
   `implementation_satisfaction=NOT_ASSESSED`。
3. 在 ArduPilot 闭环稳定后，选择 Mecel 齿轮控制器作算法横向对照，或选择联合国
   第 152 号自动紧急制动法规作外部规范泛化实验。

## 恢复提示词

```text
先读 AGENTS.md、.codex/PROJECT_STATE.md、.codex/SESSION_LOG.md、
analysis/zotero_fixed_time_mitl_benchmark_audit_zh.md 和
analysis/ltl_fuzzer_mitl_buchi_guidance_zh.md。固定时间背景审计已覆盖两个 Zotero
目录 47/47 条，并筛出 6 组 ArduPilot 候选。下一步先用振动保护 1 秒启用/15 秒
恢复做 requirement、formula、observation plan 和真实 SITL 轨迹；地形、左舵和
降落伞目前只是规范—源码冲突候选，未实跑前保持 NOT_ASSESSED。既有无界性质套索
语义边界继续有效，不要恢复已暂停的 RIFT-M5。
```
