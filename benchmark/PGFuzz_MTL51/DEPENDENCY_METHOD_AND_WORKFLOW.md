# PGFuzz 与 ADGFuzz 依赖提取算法、工作流和适用边界

本文回答三个问题：PGFuzz 怎样从性质找到相关输入；ADGFuzz 怎样从赋值语句生成输入组合；这两种方法怎样用于当前 51 条历史性质而不把源码实现误当成规范。

## 一、术语图例

- `PGFuzz` 是 `Policy-Guided Fuzzing`，中文为“性质引导模糊测试”；本任务从它取得 51 条历史性质及作者候选输入。
- `ADGFuzz` 是 `Assignment Dependency-Guided Fuzzing`，中文为“赋值依赖引导模糊测试”；本任务只分析并借鉴它的依赖组合算法，不让它从源码反推规范。
- `MTL` 是 `Metric Temporal Logic`，中文为“度量时序逻辑”；PGFuzz 用它表示带有时间窗口或相邻观测关系的性质。
- `AP` 是 `Atomic Proposition`，中文为“原子命题”；它是公式中可独立判断真假的最小条件，例如“模式为 RTL”。
- `term` 中文为“公式词项”；它是原子命题中的状态名、参数名或事件名，例如 `ALT`、`RTL_ALT` 和 `GPS_fail`。
- `InputP` 是 `Parameter Input`，中文为“配置参数输入”；它指可配置飞控参数。
- `InputC` 是 `Command Input`，中文为“命令输入”；它包括飞行命令、模式切换和遥控通道输入。
- `InputE` 是 `Environmental Input`，中文为“环境输入”；它通常是软件在环仿真中的传感器、天气、电池或位置扰动参数。
- `SITL` 是 `Software In The Loop`，中文为“软件在环仿真”；飞控二进制在普通计算机上运行并连接模拟传感器和动力学。
- `MAVLink` 是 `Micro Air Vehicle Link`，中文可理解为“微型飞行器通信协议”；这里用于发送命令、读取参数和接收飞控状态消息。
- `LLVM IR` 是 `LLVM Intermediate Representation`，中文为“LLVM 项目的中间表示”；它是编译器将源码转换后的统一低层程序表示。LLVM 名称历史上源于 `Low Level Virtual Machine`，但现在是项目正式名称。
- `def-use` 是 `definition-use`，中文为“定义—使用关系”；它追踪一个值在哪里产生，又在哪里被读取。
- `points-to analysis` 中文为“指针指向分析”；它估计指针可能指向哪些内存对象。
- `alias analysis` 中文为“别名分析”；它判断不同表达式是否可能引用同一个存储位置。
- `flow-sensitive` 中文为“流敏感”；分析考虑语句执行先后顺序。
- `path-insensitive` 中文为“路径不敏感”；分析不区分各分支的可达条件，所以可能保留实际不可达的候选依赖。
- `ADG` 是 `Assignment Dependency Graph`，中文为“赋值依赖图”；ADGFuzz 用图表示赋值左侧变量依赖哪些右侧变量。
- `MIS` 采用作者 README 的 `Matched RV Input Subset`，中文为“匹配的机器人载具输入子集”；它是把依赖图叶节点名称与命令、参数、环境输入名称匹配后得到的候选输入组合，不是已证明的最小依赖集。
- `LHS` 是 `Left-Hand Side`，中文为“赋值左侧”；`RHS` 是 `Right-Hand Side`，中文为“赋值右侧”。
- `entropy` 中文为“熵”；ADGFuzz 用它给依赖路径排序。这里是作者定义的路径复杂度分数，不是完整概率分布的信息熵估计。
- `softmax` 中文为“指数归一化函数”；它把一组分数转换为总和为一的选择概率。
- `Andersen analysis` 中文为“Andersen 指针指向分析”；它用包含约束求保守的可能指向集合，召回率高但会保留额外候选。
- `XML` 是 `Extensible Markup Language`，中文为“可扩展标记语言”；这里指作者读取的参数或 MAVLink 机器定义文件。
- `regular expression` 中文为“正则表达式”；公开 ADGFuzz 代码用文本模式近似解析 C++，不能恢复完整语义身份。
- `artifact` 中文为“论文公开研究制品”；本文特指作者仓库中的脚本、性质目录和输入文件。
- `CANDIDATE_ASSOCIATION` 中文为“候选关联”；表示作者把输入列入某条性质，但没有公开逐项数据流证明。
- `EXPLICIT_PRECONDITION` 中文为“明确前置条件”；表示作者制品要求先设置某个值，再执行目标测试输入。
- `NOT_ASSESSED` 中文为“未评估”；本文不判断当前 ArduPilot 或 PX4 是否满足论文性质。
- `T1` 是 `bounded-response template`，中文为“有界响应模板”；触发后要求结果在给定区间内发生。`T2` 是 `state-constraint or prohibition template`，中文为“状态约束或禁止模板”；规定某状态下允许或禁止的行为。`T3` 是 `global condition-obligation template`，中文为“全局条件—义务模板”；每当条件成立就要求对应义务成立。

## 二、先区分性质提取和依赖提取

PGFuzz 不是“自然语言自动生成 MTL”的系统。论文第 4 页说明，两位作者人工阅读官方文档和源码注释，分别为 ArduPilot、PX4、Paparazzi 写出 30、21、5 条自然语言规则，再人工套用公式模板和协调冲突。输入依赖分析发生在性质和公式已经写好之后。

真实顺序是：

1. 人工读官方说明和源码注释。
2. 人工写自然语言规则。
3. 识别规则中的状态、参数和事件词项。
4. 选择 `T1`、`T2` 或 `T3` 模板并写公式。
5. 人工检查规则间冲突。
6. 公式冻结后，才把公式词项映射到 `InputP`、`InputC`、`InputE`。
7. 根据映射结果缩小变异输入空间，并为部分未知时间 `k` 做实验估计。

因此，本数据集把表十二公式称为 `HISTORICAL_PROPERTY_SEED`，中文为“历史性质种子”。当前源码只用于回答“词项在哪里、如何观测、历史输入现在叫什么”，不能反向证明这条规则是当前规范。

## 三、PGFuzz 的依赖提取算法

### 3.1 公式词项与物理状态列表

作者先人工建立飞行器物理状态列表，例如高度、位置、模式、横滚、俯仰、偏航、GPS、气压计和任务状态。然后扫描公式，确定每个词项属于：

- 配置参数，例如 `RTL_ALT`；
- 可观测飞行状态，例如 `ALT_t`；
- 命令或遥控输入，例如 `takeoff`、`RC_pitch`；
- 环境或故障输入，例如 GPS 模拟故障。

公开动态分析说明列出 34 个原始状态，并进一步合并为 roll、pitch、altitude、position、GPS 等 15 类。证据见 [动态分析说明](../../baseline/pgfuzz/ArduPilot/Dynamic%20analysis/README.md)。这种合并提高召回率，但会丢失“横滚角”和“横滚角速度”等物理量差异。

### 3.2 `InputP`：配置参数的静态映射

论文描述的流程是：

1. 从官方参数 XML 或参数手册取得参数标识符。
2. 在源码中找到该参数对应的程序变量。
3. 把飞控编译为 LLVM IR。
4. 对标量执行读取/写入追踪，建立定义—使用关系。
5. 对指针执行跨函数、流敏感、路径不敏感的指针指向和 Andersen 别名分析。
6. 从参数变量沿数据流图收集受影响变量。
7. 用人工同义词表，把源码变量名与公式物理状态词项匹配。

论文的目标是回答“哪些参数可能影响公式中的状态词项”。但是冻结的 PGFuzz 仓库没有包含完整静态分析器、完整同义词表和每条边的证明。仓库 [README](../../baseline/pgfuzz/README.md#L95) 只保留旧版构建配置、手工链接位码文件和外部静态值流框架分叉地址。

因此，公开 `parameters.txt` 只能按作者候选集保存，不能声称清单中每一项都存在已复核的数据流路径。

### 3.3 `InputC` 和 `InputE`：单输入动态映射

论文描述的动态映射流程是：

1. 让一个飞行模式先运行约一分钟，得到各状态的基线。
2. 一次只改变一个命令或环境输入。
3. 再运行约一分钟。
4. 比较输入前后各状态的标准差。
5. 重复十次；状态变化稳定时，建立输入—状态候选关系。

这里的标准差只能说明“状态随着输入发生了稳定变化”，不能证明输入是该状态变化的唯一原因，也不能证明输入是性质违反的必要条件。

公开代码与论文不一致：[profiling_cmd_env.py](../../baseline/pgfuzz/ArduPilot/Dynamic%20analysis/profiling_cmd_env.py#L114) 默认测量 1 秒、重复 3 次，而不是论文所述的一分钟和 10 次。数据集中必须同时记录论文方法和制品实际配置，不能任选其一冒充完整复现。

### 3.4 前置输入发现

若目标输入 `j` 单独执行没有产生预期状态变化，PGFuzz：

1. 选择另一个输入 `k`；
2. 先执行 `k` 并等待系统稳定；
3. 再执行 `j`；
4. 最多重复十次；
5. 若出现预期变化，记录“执行 `j` 之前需要 `k`”；
6. 所有 `k` 都失败时，把 `j` 标为当前环境不支持。

这个过程得到的是旧实验环境中的候选输入顺序，不是形式逻辑上的必要条件。冻结制品 49 个性质目录的 `preconditions.txt` 只有 ArduPilot `A.CHUTE` 非空，内容为：

```text
CHUTE_ENABLED 1
CHUTE_TYPE 10
SERVO9_FUNCTION 27
SIM_PARA_ENABLE 1
SIM_PARA_PIN 9
```

这些配置只说明 PGFuzz 旧实验如何启用降落伞仿真；是否仍适用于当前版本，需要当前参数身份和运行测试重新确认。

### 3.5 未知时间 `k` 的经验估计

当模板需要未知上界 `k` 时，作者随机选择相关输入使前件成立，测量到目标状态出现的时间；取消前件后再测量；重复 100 次，并把最大观测值作为 `k`。论文给 `A.BRAKE1` 的示例最大值约为 12.7 秒。

必须保留四个边界：

- 12.7 秒是论文仿真环境的最大观测值，不是官方规范时间；
- 原始 100 条轨迹没有公开；
- 时间戳载体、采样误差和调度误差没有公开；
- 公开代码用循环计数和固定等待实现近似，不能自动解释成 12.7 秒。

论文中的 `t-1` 只表示“前一个观测样本”，不表示“一秒以前”。本任务暂不强制每条性质必须有数值时间，因此不会为 `t-1` 或未知 `k` 人工补秒数。

### 3.6 公开输入文件的真实含义

每个性质目录包含：

- `parameters.txt`：配置参数候选；
- `cmds.txt`：命令、模式和遥控候选；
- `envs.txt`：仿真环境候选；
- `preconditions.txt`：作者明确保存的前置设置。

加载逻辑见 [ArduPilot read_inputs.py](../../baseline/pgfuzz/ArduPilot/read_inputs.py#L23) 和 [PX4 read_inputs.py](../../baseline/pgfuzz/PX4/read_inputs.py#L23)。参数行有六列：名字、重启标记、作者默认值、作者最小值、作者最大值、第六列原值。代码把第六列命名为 `param_units`，但大量第六列值像参数增量；本文不擅自判定它是单位还是增量。

51 条逻辑性质展开后共有 7,569 条性质—输入关联，其中 ArduPilot 5,872 条、PX4 1,697 条。去重后只有 356 个“系统—输入类别—历史名称”身份。这种高重复度说明公开列表是高召回候选集合，而不是每条性质各自精确的最小依赖集合。完整逐行证据在 [author_input_dependencies.csv](author_input_dependencies.csv)，去重身份在 [current_input_identity_map.csv](current_input_identity_map.csv)。

## 四、PGFuzz 工作流示例

### 4.1 `A.RTL1`：公式参数、旧列表和当前参数不是同一个层次

论文公式包含历史参数 `RTL_ALT`。PGFuzz 的 `A.RTL1/parameters.txt` 确实列出 `RTL_ALT=1500`，作者当时的数值单位语义是厘米量级。当前冻结 ArduPilot 已将参数改为 `RTL_ALT_M`，源码定义在 [mode_rtl.cpp](../../baseline/ardupilot/ArduCopter/mode_rtl.cpp#L8)，当前 ArduCopter 仿真快照值为 15.0 米。

这条链应读成：

```text
论文词项 RTL_ALT
  -> PGFuzz 历史配置候选 RTL_ALT=1500
  -> 当前参数身份 RTL_ALT_M
  -> 当前冻结仿真值 15.0 m
```

它不应读成“当前默认值就是 15 秒/15 米且不可更改”。当前源码默认、当前仿真实际值和作者历史默认值是三个不同字段；运行中能否修改、是否需要重启和何时生效还需要逐参数验证。

### 4.2 `A.CHUTE1`：明确前置条件与公式直接参数缺失

`A.CHUTE1` 是唯一保存五条明确前置设置的性质。但公式直接出现的 `CHUTE_ALT_MIN` 不在作者 `parameters.txt` 中，PGFuzz 谓词代码却会读取它。当前源码中该参数定义在 [AP_Parachute.cpp](../../baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp#L52)。

这说明 `parameters.txt` 既不是公式参数全集，也不是最小因果依赖集。人工审核必须同时看公式词项覆盖表和作者候选输入表。

### 4.3 `PX.HOLD2`：自然语言条件、旧参数和当前参数迁移

论文自然语言要求：`MIS_LTRMIN_ALT != -1`、当前高度低于该值，然后爬升到该高度。印刷公式遗漏“当前高度低于参数”和“达到目标高度”，只保留上升趋势。当前 PX4 已用 `NAV_MIN_LTR_ALT` 替代旧名，定义在 [navigator_params.c](../../baseline/px4/src/modules/navigator/navigator_params.c#L178)，冻结仿真值为 -1，即当前配置禁用该最小盘旋高度规则。

源码绑定只能说明当前参数身份和运行值。它不能自动修复论文公式，也不能由当前值 -1 得出固件满足或违反性质。

## 五、ADGFuzz 的赋值依赖算法

ADGFuzz 不是性质提取器。它从当前源码赋值关系寻找可能共同影响执行路径的输入组合，可以在 PGFuzz 性质和原子命题已经冻结后用于扩大候选输入空间。

### 5.1 论文工作流

1. 按函数提取形如 `y = f(X)` 的赋值。
2. 规范化变量名称并构建赋值依赖图。
3. 从目标赋值变量反向遍历依赖。
4. 把变量分为根变量、中间变量和叶变量。
5. 将叶变量名称按下划线拆分为词项。
6. 对命令、配置参数和环境输入名称做相同拆词。
7. 用同义词表和物理耦合表扩展词项。
8. 删除动词和过短词项。
9. 按名称匹配得到一个或多个 MIS。
10. 根据图节点数和词项匹配强度计算路径熵。
11. 按熵选择输入集，重启仿真并随机执行集合中的输入和值。
12. 根据测试结果调整输入集的熵。

论文给出的评分是：

```text
E_num(MIS)  = log2(|N| + 1)
E_qual(MIS) = log2(1 + sum over v in V_leaf of M(v))
M(v)        = sum from i=1 to k of (i / T_i)
E(MIS)      = E_num(MIS) + E_qual(MIS)
p(MIS)      = E(MIS) / sum over L in MISs of E(L)
```

每个符号的含义如下；这里的 `k` 属于 ADGFuzz 词项计数，与 PGFuzz 时间公式中的经验上界 `k` 完全不是同一个量。

| 符号 | 英文原意 | 本文采用的中文解释与判断作用 |
|---|---|---|
| `E_num(MIS)` | number-based entropy | 数量熵分量；用赋值依赖图中半依赖节点的数量表示中间计算链丰富程度。论文排版写作 `Enum`，这里加下标只是为了防止误读成 C/C++ 枚举。 |
| `E_qual(MIS)` | quality-based entropy | 质量熵分量；用叶变量词项与飞控输入名称匹配的数量和专一性表示语义丰富程度。论文排版写作 `Equal`。 |
| `N`、`|N|` | semi-dependent-node set and its cardinality | `N` 是该赋值依赖图的半依赖节点集合；半依赖节点指自身还由更早赋值计算、位于根结果与叶变量之间的中间变量。`|N|` 是集合元素个数。 |
| `V_leaf` | set of leaf variables | 叶变量集合；这些变量在当前赋值依赖图中不再依赖其他已提取赋值。 |
| `v` | one leaf variable | 一个叶变量；作者把它的名称拆成若干词项后与飞控输入名称匹配。 |
| `k` | number of terms in `v` | 叶变量 `v` 含有的词项数量；不是秒数，也不是 PGFuzz 的时间上界。 |
| `i` | term-count index | 从 1 到 `k` 的词项数量索引。论文说“使用 `v` 中的 `i` 个词项”，但没有规定多词项的顺序。 |
| `T_i` | uniquely matched RV inputs for `i` terms | 使用 `i` 个词项时共同匹配到的唯一机器人载具输入数量。论文没有严格说明它是“恰好 i 个词命中”还是“前 i 个词累计命中”，因此复现前必须固定分组语义。 |
| `M(v)` | effective information entropy of variable `v` | 叶变量的有效信息分数；匹配词项更多会增大分数，而同一词项匹配输入越多会降低专一性。它是作者启发式，不是从运行概率估计出的香农熵。 |
| `E(MIS)` | total entropy score | 一个候选输入子集的总分，即数量分量与质量分量相加。 |
| `MISs`、`L` | collection of MISs and one member | `MISs` 是所有候选输入子集的集合，`L` 是求和中的一个候选子集。 |
| `p(MIS)` | selection probability | 论文规定的线性选择概率；一个子集的总分除以全部子集总分。若总分和为零，论文正文没有在该公式处给出处理规则。 |
| `log2` | base-2 logarithm | 以 2 为底的对数，用来压缩节点数或匹配分数的增长幅度。 |

论文把每条路径的测试次数限制在至少 50、至多 500。

### 5.2 公开代码与论文的差异

- 公开实现使用正则表达式解析 `.cpp`，不是完整 C++ 语义分析；入口见 [tree_parse.py](../../baseline/ADGFuzz/static/tree_parse.py#L324)。
- 它删除注释、数字、作用域和大量运算符信息，再把图压缩为“函数—顶层变量—叶变量”；对象身份和条件语义会丢失。
- 词项匹配实现见 [Mapping.py](../../baseline/ADGFuzz/model/Mapping.py#L229)。
- `node_count` 中文为“中间依赖节点计数”；`tree_parse.py` 只对类型为 `node` 的中间节点去重计数，随后以 `node_num` 传入映射阶段。代码把它赋给 `H_count`（节点数量分量），再用线性 `H_count + H_sum` 作为总分，而不是论文的两个对数公式；见 [tree_parse.py](../../baseline/ADGFuzz/static/tree_parse.py#L129) 和 [Mapping.py](../../baseline/ADGFuzz/model/Mapping.py#L294)。
- `H_sum` 中文为“名称匹配累积分量”。命令或环境词项匹配 `n` 个输入时，代码加 `1/n`；参数匹配则对每个参数累计 `match_count / len(matched_params[match_count])`，其中 `match_count` 是该参数命中的词项数，`matched_params[match_count]` 是当前已扫描到的同命中数参数列表。遥控输入当前不增加该分量。因此代码实现不等于论文的 `i/T_i` 分组公式；见 [Mapping.py](../../baseline/ADGFuzz/model/Mapping.py#L330)。
- 路径选择使用 softmax，而不是论文的 `E/sum(E)`；见 [fuzz.py](../../baseline/ADGFuzz/fuzzer/fuzz.py#L122)。
- 50–500 次截断见 [fuzz.py](../../baseline/ADGFuzz/fuzzer/fuzz.py#L206)。

因此，ADGFuzz 输出适合标为“待验证输入组合”，不能标为精确数据依赖，也不能从赋值图生成规范义务、例外或时间含义。

## 六、两种方法怎样组合

推荐组合是单向的：

```text
PGFuzz 论文/官方文档性质
  -> 冻结公式和 AP
  -> 当前源码只做 AP 身份与可观测性绑定
  -> PGFuzz 作者候选输入作为第一层输入空间
  -> ADGFuzz 赋值图为已知 AP 扩展候选输入组合和优先级
  -> 动态测试再验证关联
```

禁止反向操作：

- 不能因为源码有某个 `if` 条件，就把条件提升为当前官方性质；
- 不能因为某参数出现在赋值链，就判断它必然影响某条性质；
- 不能因为当前代码实现了某个超时，就把超时数值写成规范时间；
- 不能因为监视器例子通过，就判断固件符合性质。

## 七、优点与缺点

| 方法 | 优点 | 缺点 | 本任务中的用途 |
|---|---|---|---|
| PGFuzz 人工性质提取 | 规则容易人工阅读；公式、状态和输入能显式关联；可保存经验时间 | 依赖人工和同义词；文档版本敏感；模板丢失取消、重置和例外；表十二本身有语法、方向和单位错误 | 作为 51 条历史性质种子，不作为当前规范确认 |
| PGFuzz 参数静态映射 | 能从参数定义沿数据流扩大候选输入；适合缩小盲目变异空间 | 完整分析器和原始映射未公开；路径不敏感会产生多余候选；公开列表高度复制 | 保存作者候选集，再映射当前参数身份 |
| PGFuzz 命令/环境动态映射 | 可发现名字无法推断的运行相关性；可测试先后前置输入 | 单输入标准差不能证明因果；论文与代码的测量时长/次数不一致；状态分类会合并不同物理量 | 作为候选排序证据，不作为真实依赖证明 |
| ADGFuzz 赋值依赖图 | 不需要先手写每个输入组合；能沿多层赋值扩展组合；适合输入空间优先级 | 正则解析不理解完整 C++；丢失常量、分支、对象和跨函数身份；名称/同义词匹配易误配；论文与代码熵公式不同 | 后续静态分析阶段为已知 AP 扩展输入候选，不产生性质 |

## 八、审计结论

1. PGFuzz 先人工得到性质，再分析依赖；它不是从源码自动提取性质。
2. 公开输入文件是高召回候选集，唯一明确保存的前置配置只有 `A.CHUTE` 五项。
3. 当前参数同名、重命名、运行值和作者历史默认值必须分栏；任何一栏都不能替代其他栏。
4. ADGFuzz 可以扩展“测试哪些输入组合”，但不能回答“系统必须满足什么”。
5. 本阶段所有性质的 `implementation_satisfaction` 继续为 `NOT_ASSESSED`。
