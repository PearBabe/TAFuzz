# ADGFuzz 论文—源码完全精读与 TAFuzz 借鉴方案

> 论文：Yuncheng Wang 等，*ADGFUZZ: Assignment Dependency-Guided Fuzzing for Robotic Vehicles*，NDSS 2026。  
> 本地 PDF：[Wang 等 - 2026 - ADGFUZZ Assignment dependency-guided fuzzing for robotic vehicles.pdf](</mnt/c/Users/PC-123/Zotero/storage/X8VTAKST/Wang 等 - 2026 - ADGFUZZ Assignment dependency-guided fuzzing for robotic vehicles.pdf>)。  
> 公开仓库：[wyunc/ADGFuzz](https://github.com/wyunc/ADGFuzz)，本地检出为 commit [`203fce3`](https://github.com/wyunc/ADGFuzz/commit/203fce3f4265241340ed62b9be90aec1da0afa37)，2026-01-04。  
> PDF SHA-256：`bb86bc3177c4e4bf2c8fe73e14e99760ab4dd662deb7902afafb502cfacaed72`。  
> 分析日期：2026-07-17。

## 0. 先给出最重要的结论

ADGFuzz 的真正方法链是：

```text
飞控 C++ 源码
  → 用正则抽取函数内赋值语句
  → 从某个结果变量反向串起赋值依赖，形成 ADG
  → 只保留 ADG 叶变量名称和中间节点数量
  → 按变量名中的词匹配参数、命令和仿真输入，形成 MIS
  → 用“链复杂度 + 名称匹配专一性”启发式分数选择 MIS
  → 在完整 SITL 任务中随机选择 MIS 内输入并重新取值
  → 用坠地、远离航点、遥测中断三个 oracle 判异常
  → 保存整个输入序列，再重启、回放、近似约简
```

这里有四个必须先澄清的认识：

1. **它没有 AFL/libFuzzer 意义上的 seed corpus。** MIS 是“本轮允许从哪些结构化输入中抽样”的模板，不是可变异的父种子。
2. **它没有在线代码覆盖、状态覆盖或赋值覆盖反馈。** 在线反馈只有 oracle 是否触发，以及据此衰减 MIS 分数。
3. **它没有源码插桩。** 静态阶段是 Python 正则；运行时通过 MAVLink 从系统外部改参数、发命令、读遥测。
4. **它没有自动性质提取。** 三个 oracle 是作者依据历史故障、经验和已有工作人工规定的后果判定，不是从 ADG、注释或文档自动合成的性质。

因此，对当前 TAFuzz 最有价值的是一种组织思想：

```text
待观察性质/AP
  → 反向依赖切片
  → 与该性质相关的可控输入子空间
  → 分子空间调度
  → 完整状态工作流执行
  → 保存并约简带时间的触发序列
```

不应直接照搬的是它的正则静态分析、名称即依赖、固定 oracle、分数公式和运行时代码。

---

## 1. 不懂飞控也能读懂这篇论文所需的最小知识

### 1.1 系统中各组件是什么

| 名称 | 在论文中的作用 | 可以怎样类比到协议 fuzzing |
|---|---|---|
| ArduPilot / PX4 | 真正被测的飞控程序 | 协议服务器或客户端实现 |
| SITL | 运行真实飞控代码，但传感器、空气动力和车辆运动由软件模拟 | 被测程序加可控环境模型 |
| MAVLink | 地面站和飞控之间的消息协议 | 你的协议线格式/API |
| pymavlink | Python 发送、接收和解码 MAVLink 的库 | 协议驱动器/适配器 |
| MAVProxy | 地面控制站及控制台、地图前端 | 测试客户端和可视化工具 |
| mission | 一系列 waypoint 和动作，形成完整任务 | 一条合法、可达深状态的协议会话脚本 |
| oracle | 从遥测或状态中判断异常 | MITL/TA monitor 加后果 oracle |

SITL 不是“重写了一个简化飞控”。它通常运行真实 ArduPilot/PX4 控制程序，只把 GPS、IMU、风、位置、执行器和车辆运动放进仿真。因而它适合发现控制逻辑、状态组合和参数处理问题，但不能完整代表真实传感器噪声、电气故障、执行器延迟和硬件时序。

### 1.2 输入、命令、遥测不要混淆

ADGFuzz 面对四类实际对象：

- **配置参数**：长期或半长期设置，例如最大速度、最小 PWM、控制增益。可以在起飞前或飞行中通过 `PARAM_SET` 改写。
- **MAVLink 命令**：一次性动作，例如起飞、改变速度、导航到某点、设置 ROI。
- **RC 通道**：模拟遥控器的 roll、pitch、throttle、yaw 等通道值。
- **遥测消息**：飞控向外报告状态，例如心跳、当前位置、当前 waypoint、到 waypoint 的距离和状态文本。它们主要供 oracle 观察，而不是 fuzz 输入。

论文把仿真风、GPS 偏置等称为环境输入。ArduPilot 实际上通常把它们暴露为 `SIM_*` 配置参数，所以代码仍可通过参数接口修改，例如 `SIM_WIND_SPD`。

### 1.3 几个飞行词汇

- `roll`：左右倾斜；`pitch`：机头抬起/压下；`yaw`：机头水平转向。
- `throttle/thrust`：推力或油门。
- `PWM`：控制电机或舵机的脉宽数值；ESC 是把 PWM 等控制信号转换为电机输出的设备。
- `waypoint`：任务中的目标位置。
- `arm`：允许电机/执行机构进入工作状态；`takeoff`：起飞。
- `GUIDED/AUTO`：外部引导或自动执行任务的模式。
- `feed-forward`：根据目标量直接给出一部分控制输出；数值过大可能把微小目标变化放大。
- `TECS`：固定翼中协调高度、速度、俯仰和油门的控制逻辑。理解“存在相互约束的俯仰和油门状态”即可，不必推导控制方程。

Copter 能悬停；Plane 必须保持向前飞且到 waypoint 附近可能盘旋；Rover 在地面行驶。因此同一个“离目标距离增加”的 oracle 不能天然共用完全相同阈值。

### 1.4 你不需要先学什么

为了借鉴 ADGFuzz，不需要先掌握完整空气动力学、PID 稳定性证明、EKF 推导、ROS、真实无人机组装或 HITL。需要掌握的是：SITL 生命周期、状态/任务、参数与命令、遥测字段、重启恢复、输入回放和结果约简。这与做状态协议 fuzzing 的工程结构高度相似。

---

## 2. 论文想解决的具体问题

### 2.1 动机数据

作者检查了 ArduPilot 从 2015 年 1 月到 2025 年 1 月的 819 个 `BUG` issue，过滤编译错误、显示问题、功能增强等后留下 207 个语义/逻辑缺陷。按修复代码分类（论文 pp.3–4）：

| 修复类型 | 数量 | 比例 |
|---|---:|---:|
| 赋值语句修正 | 58 | 28.02% |
| 增加或删除逻辑 | 111 | 53.62% |
| 修改函数调用 | 16 | 7.74% |
| 修改返回类型或数值单位 | 11 | 5.31% |
| 调整默认值 | 11 | 5.31% |

作者据此把目标限定为 assignment-statement bugs：物理公式、运动模型和控制计算被实现为赋值表达式时发生错误，或者几个本来各自合法的参数通过赋值链产生意外组合效果。

论文随后把其余 71.98% 概括成“missing inputs”，但表 I 实际列的是逻辑、调用、类型/单位和默认值等多种修复。这一归纳并没有由表中分类直接证明。

### 2.2 输入空间为什么大

论文称 ArduCopter 有 4,000 多个配置/仿真参数和 164 个控制命令。不同输入还会影响同一物理概念，例如一个参数调节 throttle curve，另一个命令直接改变 throttle。单输入边界、双输入冲突、状态依赖和执行顺序叠加后，笛卡尔积非常大。（论文 pp.2–3）

### 2.3 方法的核心假设

作者的关键假设是：

1. 赋值链中的叶变量名称有较强语义；
2. 飞控内部变量和对外参数遵循相似的命名规范；
3. 因此可以用名称相似性，把某条赋值链映射到一小组可能影响它的外部输入；
4. 赋值链越深、名称匹配越专一，这组输入越值得优先测试。

前三步是启发式相关性，不是严格数据流证明。论文最成功的地方不是证明“输入 A 一定到达语句 S”，而是把巨大的输入空间切成许多语义上可能合作的子空间，再在真实任务状态中组合测试。

---

## 3. 论文总体框架

论文图 3（p.5）可以拆为六个阶段：

1. **赋值抽取**：逐函数抽取赋值语句。
2. **ADG 构建**：为结果变量建立反向赋值依赖图。
3. **MIS 推断**：从叶变量词语映射到外部可控输入。
4. **优先级计算**：用 ADG 中间节点数量和名称匹配质量计算启发式“熵”。
5. **SITL fuzzing**：选择 MIS，随机选其中的输入和值，在完整 mission 中注入。
6. **后处理**：保存从本轮开始到异常出现的整段序列，重启重放、近似最小化、去重。

三个运行模块并行工作（论文 pp.7–8）：

```text
Simulation Module：启动/重启 SITL，装载 mission，推进飞行状态
Execution Module ：选择 MIS，生成并注入参数、命令、RC
Oracle Module    ：接收遥测，判断坠地、路线偏离或软件失联
```

论文说“每轮启动 fresh simulator”。公开代码的实际粒度是：选定一个 MIS，在同一 SITL 中累计执行该 MIS 的 50–500 个输入批次；本 MIS 结束或首次检测到异常后才重启 SITL。单个批次并不是独立、干净的测试用例。

---

## 4. ADG：论文算法、代码实现和真实能力

### 4.1 论文定义

论文把一条赋值语句定义为：

\[
S=(y,X,O)
\]

- \(y\)：左值，即依赖结果；
- \(X=\{x_1,\dots,x_n\}\)：右侧操作数或函数调用；
- \(O\)：算术或逻辑运算符。（论文 p.4）

ADG 节点分为：

- `root`：作为左值，但不再作为其他赋值的 RHS；
- `semi`：既做左值，又被后面的赋值使用；
- `leaf`：只在 RHS 出现，当前函数内没有找到定义。

边方向是“结果指向其依赖”。例如：

```cpp
a = b + c;
d = a * e;
```

理论 ADG 为：

```text
d (root)
├── a (semi)
│   ├── b (leaf)
│   └── c (leaf)
└── e (leaf)
```

### 4.2 Algorithm 1 的论文意图

论文 pp.5–6 的算法可还原为：

1. 一次处理一个函数；
2. 用模式匹配留下赋值语句；
3. 规范化变量名并按源码顺序排列；
4. 从最后出现、尚未处理的左值开始，把它视为 root；
5. 找其 RHS 变量并建边；
6. RHS 名称若也有赋值定义，则标为 semi 并继续反向查找；否则标为 leaf；
7. 删除可能造成环的重复关系；
8. 对函数内剩余结果变量重复，得到若干 ADG。

论文明确写明实现使用 **pattern-based string matching**，并未声称采用 AST、CFG、SSA 或编译器数据流。（论文 pp.5、9）

Algorithm 1 伪代码本身不完全可复现：`PROCESSSEMINODE` 没展示完整递归队列；`s.index < i` 的定义也可能排除当前 semi 自己的定义。因此必须以公开实现为准。

### 4.3 公开代码的完整静态链路

| 步骤 | 代码 | 实际行为 |
|---|---|---|
| 遍历源码 | [`process_files()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:425>) | `os.walk`，只处理 `.cpp` |
| 删除注释 | [`parse_cpp_file9()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:333>) | 正则删 `//` 和 `/*...*/` |
| 识别函数 | [函数正则](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:339>) | 只接受有限原生返回类型 |
| 识别赋值 | [赋值正则](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:353>) | `([\w.]+)\s*([+\-*/]?=)\s*(.+?);` |
| 规范化 RHS | [RHS 处理](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:377>) | 去数字/命名空间，成员符号改 `_`，函数调用变合成词 |
| 反向扫描 | [赋值列表反转](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:370>) | 后写的赋值先处理 |
| “去环” | [`remove_circular_dependencies()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:36>) | 删除已在反向扫描中见过的名字，并非真正图环检测 |
| 建树 | [`build_tree1()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:62>) | 每个名字一个 `TreeNode`，依赖为 `set` |
| 剪枝 | [`convert_tree()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:115>) | 删除中间边，只输出叶子列表和 `node` 数量 |
| 装载 JSON | [`read_initfile()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/adgfuzz.py:113>) | 以裸函数名 `dict.update` 合并 |
| 交给 MIS | [主入口](</home/lqq/project/TAFuzz/baseline/ADGFuzz/adgfuzz.py:239>) | 丢掉文件、函数、root，只传叶子列表和节点数 |

它输出的并不是可供后续遍历的完整 ADG，而是：

```json
{
  "function_name": {
    "top_lvalue": [
      ["leaf_1", "leaf_2", "leaf_3"],
      2
    ]
  }
}
```

其中 `2` 只是递归可达的 `node` 类型对象数量。源码位置、运算符、控制条件、中间节点、边、类型和调用上下文都已经丢失。README 也明确把这些文件称为“semi-dependent nodes removed”的 pruned ADG，见 [`README.md`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/README.md:187>)。

### 4.4 一个具体例子

论文 Figure 2/12 的根变量是 `s_finished`，它表示“虚拟轨迹目标是否到达 waypoint”。简化赋值链是：

```cpp
track_error = position_error.dot(track_direction);
track_velocity = velocity.dot(track_direction);
track_scaler_dt = f(track_velocity, track_error, target_velocity);
_track_scalar_dt += g(track_scaler_dt, dt, acceleration, jerk);
s_finished = advance(..., _track_scalar_dt, waypoint_radius, ...);
```

理论 ADG 从 `s_finished` 反向经过 `_track_scalar_dt`、`track_scaler_dt` 等 semi 节点，最后得到 position、velocity、direction、acceleration、jerk、waypoint radius 等 leaf 概念。之后名称映射把它扩展到 `WPNAV_RADIUS`、`ATC_ACCEL_*`、`SIM_WIND_SPD`、`MAV_CMD_NAV_WAYPOINT` 等输入。

这展示了方法的价值：它能猜出强风、速度、位置和 waypoint 参数可能共同影响“到点”结果。它也展示了过近似：只要输入名包含常见词，就可能进入一个很大的 MIS，却没有真实数据流证据证明它能到达该 root。

### 4.5 它没有什么静态语义

当前实现没有：

- `.h/.hpp/.c/.cc/.cxx` 分析；
- AST `DeclRefExpr`、`MemberExpr`、`FieldDecl`；
- 类型、字段所属 record、继承和模板实例；
- CFG、控制依赖、分支可达性；
- SSA、MemorySSA、def-use、phi；
- 指针/引用/数组/别名分析；
- 跨函数参数、返回值、全局状态传播；
- 调用图、虚调用解析、函数摘要；
- 宏展开和真实编译条件；
- 源码位置和可插桩位置。

函数调用只被改写成合成名称。例如 `out = callee(input)` 可能变成叶子 `callee_input`，不会进入 `callee()` 分析返回值来源。相关实现见 [`replace_function_calls()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:300>)。

### 4.6 对象字段到底怎样“获取”

这是用户问题中最容易被论文图误导的部分。答案是：**ADGFuzz 没有真正获取类的字段定义或运行时对象字段值。**

源码侧只做字符串处理：

- LHS 正则允许 `.`，所以 `out.field = x` 可原样留下 `out.field`；
- LHS 不支持 `->`，`ptr->field = x` 往往只捕获 `field`，丢掉 `ptr`；
- LHS 不支持数组下标，`arr[i] = x` 往往整条丢失；
- RHS 的 `.` 和 `->` 都在 [第 386 行](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:386>) 被换成 `_`；
- 只有 RHS 做 camelCase→snake_case，LHS 保留原字符串。

因此：

```cpp
out.field = mid;
next = out.field;
```

可能分别得到 `out.field` 和 `out_field`，它们不是同一个名字，依赖链会断。仓库解析器的只读实验还表明：

```cpp
ptr->lost = out.field; // 可能只得到 lost <- out_field
arr[i] = src;          // 赋值丢失
if (x == y);           // 可能被误识别为 x = y
```

遥测侧的字段是另一回事。`pymavlink` 根据 MAVLink 消息定义生成 Python 消息对象，代码直接访问：

- `HEARTBEAT.system_status`
- `STATUSTEXT.text`
- `NAV_CONTROLLER_OUTPUT.wp_dist`
- `EXTENDED_SYS_STATE.landed_state`
- `GLOBAL_POSITION_INT.relative_alt/lat/lon`

这些是协议解码后的消息属性，不是从 C++ 对象中反射出来的字段。

### 4.7 裸函数名冲突造成的实测路径损失

解析器只保存 `match.group(3)`，即裸函数名，忽略类名、命名空间、参数类型和重载签名，见 [`tree_parse.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:362>)。同一文件内 `A::update()` 和 `B::update()` 会合并；不同 JSON 文件又被 `init_paths.update(data)` 后者覆盖前者。

对仓库预置静态结果按当前装载逻辑做只读量化：

| 目标 | JSON 文件 | 函数记录 | 唯一裸函数名 | 全部 root 路径 | 装载后保留 | 损失 |
|---|---:|---:|---:|---:|---:|---:|
| Copter + libraries | 1328 | 5997 | 4094 | 20994 | 13891 | 7103，33.8% |
| Plane + libraries | 1318 | 6042 | 4133 | 21176 | 14101 | 7075，33.4% |
| Rover + libraries | 1293 | 5858 | 3978 | 20521 | 13592 | 6929，33.8% |
| PX4 lib + modules | 609 | 2295 | 1748 | 9454 | 6975 | 2479，26.2% |

Copter 数据中裸函数名 `init` 出现 242 次，`update` 出现 227 次。保留哪一个还会受未排序 `os.walk` 顺序影响。

### 4.8 其他可复现性问题

- `TreeNode.dependencies` 是 `set`，叶子顺序受 `PYTHONHASHSEED` 影响。
- README 说输出在 `static/initpath`，代码却把 ArduPilot `res_dir` 写成 `inpath`，见 [`tree_parse.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:465>)。
- README 从仓库根目录给出 `python tree_parse.py`，实际脚本位于 `static/tree_parse.py`。
- PX4 输入路径用字符串 `f'{PX4_HOME}src'` 拼接，依赖环境变量尾部 `/`，且在 `None` 检查前已转换成字符串。
- 输出目录不清理，重新分析后可能混入旧 JSON。
- 部分生成词表所需的原始 HTML 和 `px4_terms` 中间文件未入库。
- `static/test1.bc` 没被任何代码引用；它不能证明当前流程使用 LLVM。

结论：这套静态分析足以做轻量名称启发式实验，不足以承担 TAFuzz 的 AP 绑定、对象字段解析、跨过程切片或插桩点生成。

---

## 5. MIS：如何从叶变量得到外部输入子集

### 5.1 论文算法

对每个 ADG，作者取所有 leaf variable names，按下划线拆词，再通过两类 term association table 扩展（论文 pp.5–6）：

1. **同义词/缩写**：`velocity ↔ vel/spd/speed`，`roll ↔ rll` 等。
2. **物理耦合**：概念不同但在物理上相关，例如角度改变水平推力和加速度：

\[
F_x=T\sin\theta,\qquad
a=\frac{T\sin\theta}{m}\approx\frac{T\theta}{m}
\]

所以 `angle` 可以扩展到 `acceleration`。随后用这些词匹配完整配置参数、命令、环境输入和 RC 通道名，所有命中输入组成该 ADG 的 MIS。

论文称同义词表主要由领域知识和既有工作人工构建；物理耦合表通过“抽取源码注释 + 未指明的 LLM”一次性半自动生成。论文未披露模型、版本、prompt、原始注释集、候选表或人工验收过程。

### 5.2 公开代码实际使用的词表

核心是 [`model/Mapping.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/model/Mapping.py:155>)：

- `map/cmd_term1.txt`
- `map/param_copter_term.txt` / `param_plane_term.txt` / `param_rover_term.txt` / `param_px4_term.txt`
- `map/env_term.txt`
- [`map/fix.txt`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/map/fix.txt:1>)
- `model/constant.py` 中的 RC 词→通道表

`fix.txt` 只有 25 个非空映射，例如：

```text
vel        → vel, spd, speed
velocity   → spd, speed
accel      → accel, angle
rate       → rate, flow
roll       → roll, rll
attitude   → attitude, rll, pit, yaw
servo      → servo, svo, sv, srv
```

公开仓库没有“从注释调用 LLM 生成物理表”的实现；静态解析器反而先删除注释。因而可见 artifact 只能复现最终人工字典，不能复现论文描述的半自动建表过程。

### 5.3 代码匹配细节

[`parse_paths()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/model/Mapping.py:223>) 对每个 leaf：

1. 按一个或多个 `_` 拆词；
2. 删除纯数字 term；
3. **若变量少于两个 term，整条 leaf 跳过**，所以单独的 `alt`、`roll`、`mode` 即便有意义也不匹配；
4. 用 `fix.txt` 精确扩展 term；
5. 先判断 term 属于 command/parameter/environment/RC 哪一类；
6. 再把 term 展开成完整输入名。

完整名匹配规则为：

- MAV 命令：输入名以 term 开头或包含 `_TERM`；
- 参数：term 必须是下划线分隔的完整段；
- 环境：与命令相似；
- RC：直接映射到通道号。

参数节点形如：

```python
['paramset', 'WPNAV_SPEED', 1]
```

末尾 `1` 是参数名命中了几个 leaf term，不是数值、概率或通道。

### 5.4 MIS 并不等于真实动态切片

从赋值 root 到 leaf 尚且只是函数内文本依赖；从 leaf 到外部输入完全是名称语义匹配。例如 `pos` 可能命中大量 GPS、光流、相机、降落、跟随和仿真位置参数。它们概念相关，但不一定在目标函数的真实调用上下文中到达 root。

论文对 150 个 ADG–MIS 做的“准确性”人工检查，也只是判断名称语义是否合理，不是做动态因果验证。后文实验部分会进一步解释。

### 5.5 代码中 MIS 身份再次丢失

主程序在 [`adgfuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/adgfuzz.py:246>) 把 JSON 转为：

```python
path_init.append((leaf_names, node_count))
```

文件、类、函数、root 左值和中间边全部丢弃。`Mapping.py` 又在展开完整输入前，按 term/category 中间结果去重。两个不同 ADG 若得到相同 term 模板，后者被丢弃，即使它们的 root、函数和节点数不同。

最终内存元素是：

```python
(
    final_unique_inputs,
    entropy_score,
    original_leaf_names
)
```

仓库另附预计算文件：Copter 4928 个、Plane 4729 个、Rover 4548 个 MIS；当前主入口并不读取这些文件，也没有公开它们的完整生成元数据。

---

## 6. “熵”：论文公式与代码实现不是一回事

### 6.1 论文公式

作者把 MIS 分数称为 entropy，但它不是从测试结果统计出的 Shannon entropy，而是静态启发式。

设 ADG 有 \(|N|\) 个 semi 节点：

\[
E_{num}(MIS)=\log_2(|N|+1)
\]

对一个 leaf variable \(v\)，其词语按匹配数量分组。若使用 \(i\) 个有效词时命中 \(T_i\) 个唯一 RV 输入：

\[
M(v)=\sum_{i=1}^{k}\frac{i}{T_i}
\]

再定义：

\[
E_{qual}(MIS)=\log_2\left(1+\sum_{v\in V_{leaf}}M(v)\right)
\]

总分和选择概率为：

\[
E(MIS)=E_{num}(MIS)+E_{qual}(MIS)
\]

\[
p(MIS)=\frac{E(MIS)}{\sum_{L\in MISs}E(L)}
\]

直觉是：

- semi 多，说明从输入到结果的计算链较丰富；
- 一个 leaf 命中多个词，比只命中一个词更有语义；
- 一个常见词命中几百个输入，专一性应低于命中少数输入的词。

这个定义仍有歧义：论文没有严格定义多个词的顺序和 \(T_i\) 是“恰好 i 个词命中”还是“前 i 个词累计命中”。因此即便照公式实现，也需先固定分组语义。

### 6.2 公开代码的初始分数

[`Mapping.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/model/Mapping.py:294>) 直接令：

```python
H_count = node_num
entropy = H_count + H_sum
```

没有两个 `log2`，`max_Hcount` 虽传入构造器却没有用于归一化。

命令和环境 term 命中 `n` 个完整输入时加 `1/n`，较接近论文“越泛化越低”的直觉。参数却在扫描每个命中项时执行：

```python
H_sum += match_count / len(matched_params[match_count])
```

见 [`Mapping.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/model/Mapping.py:354>)。若有 \(T_i\) 个参数都命中 \(i\) 个词，代码贡献接近：

\[
i\left(1+\frac12+\cdots+\frac1{T_i}\right)=iH_{T_i}
\]

而论文公式是单项 \(i/T_i\)。二者方向甚至可能相反：匹配参数越多，代码中的调和和仍会增长。RC 完全不增加 `H_sum`。

### 6.3 选择概率：代码使用 softmax

[`fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:122>) 和 PX4 版本实际计算：

```python
exp_entropies = np.exp(entropies - np.max(entropies))
probabilities = exp_entropies / np.sum(exp_entropies)
```

这不是论文的线性 \(E/\sum E\)。例如分数 `[10, 5, 1]`：

```text
论文线性：约 [0.6250, 0.3125, 0.0625]
代码 softmax：约 [0.9932, 0.0067, 0.0001]
```

把仓库附带的预计算 MIS 初始分数直接代入两种调度，得到：

| 数据 | 论文线性下最高单项概率 | 线性有效样本数 | 代码 softmax 最高单项概率 | softmax 有效样本数 |
|---|---:|---:|---:|---:|
| Copter | 0.279% | 2475.8 | 97.024% | 1.06 |
| Plane | 0.300% | 2372.9 | 99.956% | 1.00 |
| Rover | 0.362% | 2088.3 | 约 100% | 1.00 |

“有效样本数”使用 \(1/\sum p_i^2\) 计算。这个离线代入不是一次真实 campaign，但清楚表明初始 softmax 几乎退化为选最高分项。选中后最高项会被大幅衰减，下一项再成为最高，因此实际行为更像近确定性的降序队列，而不是论文描述的宽概率探索。

### 6.4 使用后的分数反馈

论文正文说：

- 找到 bug：熵减半，但保留少量继续探索；
- 未找到：逐渐降低；
- 小于 1：删除。

Algorithm 2 还存在 `UPDATEBUGENTROPY` 未定义、普通更新可能再次执行等伪代码歧义。

代码实际为：

- bug：`min(E - 1, E / 2)`，见 [`adj_entropy()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:135>)；
- 无 bug：`min(E - 2, 0.6E)`，见 [`adj_entropy_notfound()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:147>)；
- 结果非正时删除，不是小于 1 即删除；
- 每次选择前重算 softmax，不维护独立概率对象。

### 6.5 执行能量

论文说把 entropy 转成本轮执行次数 \(\kappa\)，下限 50、上限 500。代码直接使用当前原始分数：

```python
run_time = 50
if entropy > 500:
    run_time = 500
elif entropy > 50:
    run_time = int(entropy)
```

见 [`fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:201>)。这也解释了代码为何没有照论文取对数：若真使用两个对数项，大部分分数会远小于 50，几乎所有 MIS 都只得到最低预算。

---

## 7. “种子如何选择”：准确答案是没有传统种子

### 7.1 三个容易混淆的对象

| 对象 | 是什么 | 是否为 AFL 式 seed |
|---|---|---|
| mission 文件 | 把系统带入 arm、takeoff、navigation、turn 等状态的合法场景骨架 | 否，类似会话初始化脚本 |
| MIS | 一组语义上可能共同影响某条赋值链的输入名称 | 否，类似 mutation region/template |
| 本轮已执行序列 | 具体参数值和命令参数的累计序列 | 只有发现异常后用于回放，不进入演化 corpus |

ADGFuzz 没有 parent seed、favored seed、corpus admission、coverage-increasing seed retention，也不从一个成功输入继续产生子代。

### 7.2 MIS 选择流程

1. 从所有静态 JSON 形成 leaf path；
2. 映射成 `(MIS, score, leaf_names)`；
3. 用 softmax 选一个索引；
4. 在该 MIS 上执行 50–500 个批次；
5. 根据 oracle 结果衰减分数；
6. 清空本轮具体序列并重启 SITL；
7. 再选 MIS。

[`outfile/bug_input.txt`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/outfile/bug_input.txt:1>) 也不是 seed。它保存作者认为会造成固有行为/误报的输入名，如 `MAV_CMD_NAV_LAND`、`SIM_GPS1_ENABLE`、`SYSID_THISMAV`；ArduPilot 主循环会提前跳过这些名字，见 [`load_found_buginputs()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:112>)。

### 7.3 quicktest 的具体例子

预置 quicktest 的抽象 leaf 是：

```text
height_amsl_cm
terrain_difference
terrain_altitude
node_count = 0
```

当前映射器会得到一个包含 `TERRAIN_ENABLE`、`TERRAIN_SPACING`、`SIM_TERRAIN`、多个 altitude 参数以及 `MAV_CMD_DO_CHANGE_ALTITUDE` 的 MIS。分数约 8.97，所以本轮执行最低 50 次。它说明 MIS 是“terrain/altitude 相关输入池”，不是一个已经带值的输入文件。

---

## 8. 它如何“变异”

ADGFuzz 的变异不是 bit flip，而是两层随机化：

```text
从当前 MIS 选输入类别和输入子集
  +
按照参数/命令元数据为每个输入重新生成结构化值
```

### 8.1 类别选择并非任意混合子集

代码先把 MIS 分为 parameter、MAV command 和 other（RC/env 等），见 [`fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:220>)。每个批次均匀选择 `type ∈ {1,2,3,4}`：

- `type == 1` 且有 command：只发命令批次；
- `type == 3` 且有 other：只执行 other；
- 其余只要存在 parameter：只改参数批次。

三类都存在时，近似为 command 25%、other 25%、parameter 50%。没有 other 时，`type == 3` 也落入参数分支，因此约为 command 25%、parameter 75%。单个批次并不混合三个类别；跨类别组合依靠同一 SITL 中多个批次的状态累积。

### 8.2 子集大小

命令：

- 少于 5 个：全发；
- 5–59 个：随机 5 个；
- 60 个及以上：约取总数的 1/5。

参数：

- 少于 10 个：全改；
- 10–109 个：随机 10 个；
- 110 个及以上：约取总数的 1/5。

见 [`fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:238>)。因此论文所说“随机选一个子集”在代码中是较大的批量，而不是显式控制单输入、双输入、三输入比例。

### 8.3 多输入 bug 如何产生

参数设置会在当前 SITL 实例中持续生效。一个批次设置 A，后续批次再设置 B，即使两个批次分别生成，也可能形成 A+B 状态。因此论文的双输入/三输入 bug 主要来自本轮累积，而非一次显式抽取二元或三元组合。

这也意味着所谓一次 `case` 并不隔离。若第 40 批次触发异常，保存的日志包含从 MIS 开始到第 40 批次的全部输入；真正触发项可能很早就写入，只是后果延迟出现。

### 8.4 配置参数值生成

[`RuntimeDictionary`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/runtimedict.py:107>) 从 CSV 读取：

```text
Parameter_Name, Increment, Range_Min, Range_Max, Value
```

规则为：

- 枚举/位掩码 `B/V`：从 Value 列表选；无列表时退化到 0–100；
- 无 increment、有范围：最小值 10%、最大值 10%、内部 80%；
- 有 increment：最小值 20%、最大值 20%、合法步长内部值 60%；
- 无范围：默认 `[0,10000]`，按十进制数量级选择区间。

论文举例 `[0,100]` 分 `[0,1)`、`[1,10)`、`[10,100]` 等概率。代码大体试图实现这种数量级采样，但负区间和跨零区间的分支额外除以 `100`，可能把 `[-100,100]` 的非零部分压缩到约 `[-1,1]`；不能把代码实现视为精确的通用几何分桶。

另一个重要缺陷是 [`RuntimeDictionary.load_parameters()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/runtimedict.py:128>) 默认永远加载 `data/ap-copter-v470.csv`。Plane、Rover 和 PX4 都无参数地实例化它，因此：

- MIS 名称可能来自对应车型表；
- 具体取值元数据却仍来自 Copter 表；
- 找不到名字时退化到 `[0,10000]`。

参数通过 [`rvmethod.paramset()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/rvmethod.py:210>) 发送。ArduPilot 无论值是否浮点都声明 `MAV_PARAM_TYPE_INT8`，PX4 则声明 `REAL32`。代码不等待 `PARAM_VALUE` 回显或确认，因此被拒绝、截断或异步未生效的值仍被记入执行日志。

### 8.5 MAV_CMD 的七参数生成

[`MavcmdDictionary`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/runtimedict.py:10>) 为每个 `MAV_CMD_*` 保存 command ID 和七个参数元数据。代码规则包括：

- `E` → 0；
- `N`、`m` → 0–1000；
- `[min,max,step]` → 合法整数步长值；
- `deg` → -180 到 315，步长 45；
- `m/s` → 0–50；
- `rad` → -3.14 到 6.28；
- `s` → 0–100；
- `degE7` → `[-1.8e9,1.8e9]`；
- `deg/s` → 0–360；
- 未识别元数据 → 1。

七个具体值经 [`COMMAND_LONG`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/rvmethod.py:269>) 发送，也没有检查 `COMMAND_ACK`。

### 8.6 RC 和环境路径实际不可用

RC 计划生成 1000–2000 PWM，但调用写成：

```python
rvmethod.set_rc_channel_pwm(rc_channel, pwm)
```

函数签名实际是 `set_rc_channel_pwm(master, channel_id, pwm=1500)`，见 [`rvmethod.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/rvmethod.py:57>)。调用点只传入两个位置参数，因此不会抛出 `TypeError`：`rc_channel` 被错误绑定为 `master`，而随机生成的 1000–2000 PWM 值被错误绑定为 `channel_id`。该值随即被 `channel_id > 18` 检查拦截并直接返回，所以当前实现实际没有发送 RC override。函数还只创建 8 个通道槽，却声明允许 ID 1–18；即使修复漏参，9–18 也会越界。

`Mapping.py` 可产生 `envset`，但执行器没有 `envset` 分支，`data/env.csv` 也只有占位项 `Test`。公开实现中的实际环境变异主要是把 `SIM_*` 当普通 `paramset`，不是独立环境接口。

### 8.7 没有随机种子复现

代码同时使用 Python `random` 和 NumPy RNG，却没有显式 seed，也不把 RNG 状态写入 bug 日志。`runtimedict.py` 甚至在模块 import 时生成并打印一次随机 MAV command 参数。这意味着仅靠保存的 MIS 无法重放原随机过程，只能依赖已经记录的具体值。

---

## 9. 完整运行状态与 SITL 生命周期

### 9.1 ArduPilot 主流程

入口通过 [`adgfuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/adgfuzz.py:26>) 启动：

```text
sim_vehicle.py -v ArduCopter|ArduPlane|Rover
--console --map -w
--out=udp:127.0.0.1:14550
--out=udp:127.0.0.1:14551
```

- 14550 用于执行输入；
- 14551 用于 oracle；
- `-w` 清空/重建参数存储；
- 启动后固定等待 50 秒。

fuzzer 随后：

1. 切 `GUIDED`；
2. 发送 arm；
3. 发送 takeoff 到 30m；
4. 固定 sleep；
5. 上传 `missiondata/case1.txt`；
6. 切 `AUTO`；
7. 开始当前 MIS 的 50–500 个批次。

代码不检查“arm 成功”“已到达高度”“当前 waypoint/模式满足前置条件”，主要依赖固定 sleep。论文也明确说不做显式动态状态检测，而是用 idle、takeoff、navigation、turning 等多阶段 mission 自然经过多种状态。（论文 p.8）

每个 MIS 结束后，[`close_and_relunch()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:445>)：

- 清线程事件并 join；
- `pkill -SIGINT -f sim_vehicle.py`；
- 重启 SITL；
- 固定等待 60 秒；
- 重新连接、GUIDED、arm、takeoff。

### 9.2 PX4 主流程

PX4 使用 `make px4_sitl_default jmavsim`，通过 `gnome-terminal → bash` 启动并用 PID 文件杀进程组。每轮会删除参数 BSON 和日志，再重新 make、等待约 20 秒、上传 QGC WPL 110 mission、进入 `AUTO.MISSION` 并 arm。代码见 [`fuzzpx4.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzzpx4.py:396>) 和 [`rvmethod.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/rvmethod.py:138>)。

mission item 被直接连续发送，没有按协议等待每个 `MISSION_REQUEST_INT` 和最终 ACK。这是 artifact 工程实现，不是论文算法的必要组成。

### 9.3 三条监控线程

每轮启动：

- `rvstatus_thread`：接收 MAVLink 消息并判断通信沉默；
- `msgprocess_thread`：从队列分发 HEARTBEAT/STATUSTEXT/位置消息；
- `oracle_thread`：单独计算 waypoint deviation。

见 [`fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:252>)。ArduPilot 的 status 接收线程和 route 线程会在同一个 `oracle_master` 上并发 `recv_match()`，没有锁或统一接收器，存在消息竞争消费。`process_messages()` 若队列连续 5 秒为空，异常处理位于整个循环外，线程会直接结束而不是继续等待，见 [`oracle.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:304>)。

---

## 10. 在线反馈究竟是什么

ADGFuzz 的主循环没有读取：

- line/edge/branch coverage；
- ADG root 或 assignment 是否命中；
- 新状态、模式、waypoint 或状态转换；
- 与 oracle 的连续距离；
- 新路径或新 timed trace；
- 触发输入的因果贡献。

在线反馈只有四值结果：

```text
ground/status anomaly
no-message timeout
waypoint deviation
本 MIS 预算内未发现异常
```

前三者使当前 MIS 用 bug 规则衰减，最后一种用 no-bug 规则衰减。触发输入不会加入新 corpus，不会生成新 MIS，也不会提升相邻输入的优先级。

论文附录 pp.16–17 的代码覆盖 Venn 图是事后评估：按熵四分位各抽 100 个 MIS，比较累计覆盖。仓库只有 [`outfile/read_cov.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/outfile/read_cov.py:1>)、`cov_veen.py`、`compara_cov.py` 对 lcov `.info` 做离线汇总；核心 fuzzer 从不读取覆盖。完整覆盖采集命令和 `.info` 数据也未随当前仓库提供。

因此准确表述是：**ADGFuzz 是静态优先级指导 + 后果反馈调度，不是 coverage-guided 或 state-guided fuzzer。**

---

## 11. Oracle：论文性质、README 描述与代码判定

### 11.1 oracle 在这里是什么意思

oracle 是“根据外部可观测消息判断是否出现某类不良结果”的判定器。它不是从规范自动提取的性质，也不是 ADG 的一部分。

论文说三个 invariant 来自历史 issue、仿真经验和既有 RV 检测工作（p.8）：

1. 空中车辆不应意外坠地；
2. 执行 waypoint 任务时不应持续远离目标；
3. 控制软件不应停止通信/崩溃。

### 11.2 软件 crash oracle

| 层次 | 判定 |
|---|---|
| 论文 | 连续约 2 秒没有 heartbeat |
| README | 多次阻塞收消息仍没有交换，认为 crash |
| 代码 | 6 次 × 0.3 秒内没收到**任何 MAVLink 消息**即置位 |

代码见 [`check_status()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:273>)。它不检查 SITL 进程退出码、signal、core dump、堆栈或 heartbeat 类型。因此日志名 `ArithmException` 只是推断：通信沉默可能来自算术/浮点异常，也可能来自改了 system ID、链路、仿真变慢或接收线程竞争。

### 11.3 ArduPilot 坠地/异常状态 oracle

[`handle_statustext()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:233>) 和 [`handle_heartbeat()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:213>) 处理：

- `STATUSTEXT.text` 含 `Hit ground` → `hit_ground`；
- HEARTBEAT `system_status == EMERGENCY(6)` → `status_bug`；
- HEARTBEAT `system_status == POWEROFF(7)` → `status_bug`；
- `Internal Errors` → internal flag；
- `no link`/`link 1 down` → timeout flag。

主循环把 `status_bug or hit_ground` 合并写为 `StatusError`，因此这个类别并不全是物理坠地。Internal Errors 的单独保存分支被注释掉。

### 11.4 PX4 坠地 oracle

代码使用：

- `EXTENDED_SYS_STATE.landed_state == IN_AIR` 先标记曾经起飞；
- 之后 `landed_state == ON_GROUND` 判异常落地；
- 或 `GLOBAL_POSITION_INT.relative_alt < 1m` 且曾经 airborne。

见 [`oracle.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:248>)。README 把 `landed_state` 和高度所属消息写反，并称绝对高度；代码实际是相对高度。正常任务降落若没有任务阶段过滤，也可能命中。

### 11.5 ArduPilot 路线偏离 oracle

读取 `NAV_CONTROLLER_OUTPUT.wp_dist`，见 [`check_wp_deviation()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:108>)。代码实际规则是：

1. 当前距离大于上一次；
2. 记录此次增加时间；
3. 保留 12 秒内的增加事件；
4. 累计达到 9 次即触发。

一次距离下降不会清空历史增加事件，所以不要求连续。也没有按车型分阈值：

| 来源 | Copter/Rover | Plane |
|---|---|---|
| 论文 p.8 | 只举“例如 7 秒” | 未精确区分 |
| README | 5 秒内连续 3 次 | 12 秒内 7 次 |
| 代码注释 | 5 秒、3 次 | 12 秒、9 次 |
| 代码实际 | 12 秒累计 9 次 | 12 秒累计 9 次 |

`reset_all()` 还没有清空 `deviation_times` 和 `wp_distance`，理论上历史可跨 SITL round 残留。

### 11.6 PX4 路线偏离 oracle

代码读取 `MISSION_CURRENT.seq` 和 `GLOBAL_POSITION_INT.lat/lon`，再用 `geopy.geodesic` 计算到 mission waypoint 的距离。若距离比上次增加超过 0.05m，计数加一；否则清零；超过 3 即 4 次连续增加触发。见 [`oracle.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:366>)。

### 11.7 遥测字段来源

PyMAVLink 依据 MAVLink XML 方言生成消息类，`recv_match()` 返回解码对象。代码直接读取属性：

```python
msg.get_type()
msg.system_status
msg.text
msg.landed_state
msg.relative_alt
msg.lat
msg.lon
msg.wp_dist
msg.seq
```

这就是运行时“获取对象变量字段”的实际方式：获取的是协议消息字段。它与静态 C++ `obj.field` 的字符串扁平化完全是两条路径。

### 11.8 误报过滤不是全自动

论文附录 p.16 明确列出并由一名作者人工排除：

- 主动降低电机最大输出导致坠地；
- 禁用 GPS 后系统按设计 LAND；
- `NAV_LAND`、`ARM_DISARM` 本来就降落/停机；
- 低速度加大风后车辆无法前进；
- 人工制造巨大 GPS 跳变；
- 修改 `SYSID_THISMAV` 使 GCS 收不到消息。

公开代码把其中一部分单输入写入 `bug_input.txt` 并在 ArduPilot fuzzing 前跳过，但组合行为和新误报仍需人工审查。最终 87 个结果不是单纯运行 oracle 即可自动得到的原始计数。

---

## 12. 延迟故障、日志、最小化与去重

### 12.1 为什么保存整个序列

输入写入和后果出现可能相隔数秒甚至更久。一个参数先改变控制状态，车辆经过下一次转弯才偏航；或数十次控制循环后数值才溢出。论文因此保存从选中 MIS 到 oracle 触发的整段输入。（论文 pp.8–9）

### 12.2 公开日志保存什么

[`save_bug()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:535>) 写：

```text
init_path: 静态叶变量列表
RVpath: 完整 MIS
paramset NAME VALUE
mavcmd NAME [p1,...,p7]
...
```

文件名包含 bug 序号、粗类型和距 campaign 开始的秒数。但每条输入没有：

- 单独时间戳和真实间隔；
- 当时的任务阶段、mode、waypoint、前置状态；
- Python/NumPy RNG seed；
- PARAM_VALUE/COMMAND_ACK；
- 触发 oracle 的原始消息和窗口计数；
- SITL/mission/参数基线 hash；
- core、`.BIN`、`.tlog` 的关联 ID。

对时间自动机 fuzzing 而言，这一点尤其不能照搬：必须把动作和 delay schedule 一并记录，否则最小化会改变时序语义。

### 12.3 论文最小化算法

论文描述：

1. 新建 simulator；
2. 从序列某方向逐个执行，每个输入后等待经验延迟 \(\tau\)；
3. 某输入后出现异常就加入候选最小集；
4. 重启，只回放当前候选；
5. 不能复现则反向搜索；
6. 延迟过大时退化为逐项删除。

这是一种启发式约简，没有全局最小或 1-minimal 证明。

### 12.4 代码实际后处理范围

入口 [`adgfuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/adgfuzz.py:198>) 只自动处理文件名含 `_ArithmException_` 的 no-message bug；坠地和路线偏离需要人工监督，README 也明确承认每个案例约 10 分钟且由作者决定何时重启/重放。

后处理解析只保留 `paramset` 和 `mavcmd`，丢掉 RC、mode 等。如果发现 `SIM_RATE_HZ`，直接把该名字写成最小集，不做 replay 验证。

[`PostProcess.minm_inputs()`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/postprocess.py:173>) 以固定 sleep 和前后索引搜索重放。fallback 末尾把空的 `result_min` 传给保存函数，而非 `result_min_indices`，可能写出空最小集；RC replay 也同样漏传 `master`。

### 12.5 去重没有按论文全局实现

论文说：同 bug 类型下，完全相同的最小输入集合只保留较早一项。当前代码的 `_logged_min_sets` 只属于单个 `PostProcess` 对象，而主入口为每个 bug 文件新建一个对象；因此不能跨 bug 文件全局去重。也没有按栈回溯、崩溃 PC、异常位置、root ADG 或行为轨迹聚类。

同一根因若有不同触发输入集仍会保留为不同报告；不同根因若碰巧最小输入集相同也难区分。

---

## 13. 三个案例如何理解

### 13.1 电压补偿 × 最小 PWM 导致 Copter 坠地

输入：`MOT_BAT_VOLT_MAX` 与 `MOT_PWM_MIN`。（论文 p.12）

简化机制：

1. 配置的最大电池电压高于实际电压；
2. 补偿增益约为 `configured_max / actual_voltage`，例如 45.42/42 ≈ 1.08；
3. thrust、roll、pitch、yaw 修正都被放大；
4. 四旋翼 mixer 对某个电机使用 `thrust - roll - pitch - yaw`；
5. 该电机的归一化 actuator 值可能被限制到 0；
6. 输出只剩 `MOT_PWM_MIN`；
7. 若最小 PWM 极低，ESC 可能把它解释为丢失信号，电机停转。

关键不是某一个参数越界，而是两个文档内合法值经赋值链产生组合后果。这正是 MIS 分组的强项。

### 13.2 Rover 过高速度增益导致假到达 waypoint

输入：`ATC_SPEED_FF`。（论文 pp.12–13）

1. 过高 feed-forward 增益让实际速度达到约 20m/s，而任务假设约 5m/s；
2. waypoint 快速转换逻辑依赖由 `distance = speed × time` 得到的内部进度/定时估计；
3. 真实位置和内部虚拟进度发生偏差；
4. Rover 越过目标，却被标记为已到达。

这说明“控制软件不崩溃”并不等于正确；必须有任务/协议语义 oracle。对 TAFuzz 的对应物是：进程活着，但事务状态、序号、租约或重传状态已经错误。

### 13.3 Plane 俯仰和油门逻辑冲突

输入：正的 `TECS_PITCH_MIN` 与过大的 `PTCH_RATE_D_FF`。（论文 p.13）

1. 正的最小俯仰限制使某个“机头向下时减少油门”的分支条件永远不成立；
2. TECS 只能不断通过 pitch 调节高度；
3. 过大的 pitch-rate feed-forward 又把小调整放大为接近极限舵面；
4. 高度和俯仰振荡，最后失控下降。

这个案例强调 state combination：两个局部配置分别作用于不同逻辑，冲突只有在真实控制状态演化中才出现。

---

## 14. 实验结果与证据边界

### 14.1 运行设置

论文主实验环境（p.9）：Ubuntu 20.04 VM、Intel i9-11950H、32GB RAM、Python 3.8.10；Copter、Plane、Rover 各运行 24 小时。SUT 是 ArduPilot，SITL 负责仿真，MAVProxy 是 GCS，MAVLink/pymavlink 负责交互。

README 当前固定：

- ArduPilot `564879594ebb8d31c6400461b96f5dc442f14533`；
- PX4 `d35c5f4a4e9515542d9527594f339cd97ab0c70b`。

### 14.2 主要结果

| 车型 | 总 bug | 坠地 | 路线偏离 | 软件 crash |
|---|---:|---:|---:|---:|
| Copter | 60 | 14 | 6 | 40 |
| Plane | 54 | 14 | 2 | 38 |
| Rover | 42 | 0 | 7 | 35 |
| 跨车型去重 | 87 | 26 | 15 | 46 |

其中 78 个此前未知，45 个在实体 RV 上重现，42 个为 SITL-only 或无法重建所需真实环境。16 个被开发者考虑修复。（论文 pp.9–10、14、17）

### 14.3 熵消融

| 车型 | 完整 ADGFuzz | 全输入 RANDOM | 仅节点数 NUM | 仅匹配质量 QUAL |
|---|---:|---:|---:|---:|
| Copter | 60 | 34 | 47 | 55 |
| Plane | 54 | 31 | 42 | 49 |
| Rover | 42 | 25 | 33 | 38 |

另一变体 `NOE` 是保留 MIS、仅随机选择 MIS，不要与“从全输入空间随机”的 RANDOM 混淆。完整方法比 NOE 多发现 Copter 18、Plane 16、Rover 9 个。（论文 pp.10–11）

但论文没有多随机种子重复、均值/标准差、置信区间或显著性检验。当前 artifact 也不记录 seed，所以无法从公开材料恢复一套严格统计重复。

### 14.4 ADG–MIS 准确性

两名作者人工检查 150 对随机 ADG–MIS：

- 131/150（87.33%）被认为名称语义准确；
- 14 个变量名无有效语义；
- 3 个有歧义，如 `posvel`；
- 2 个与 RV 输入无关，如 ROS topic。

按 entropy 概率抽样的 150 对中，142/150（94.67%）被认为准确。作者还报告 RHS 的 20,858 个唯一变量中 17,276 个匹配，3,582 个（17.17%）未匹配；成功 MIS 的并集覆盖 5005/5006 个输入。（论文 pp.11–12）

这些数字只能支持“名称看起来相关”和“全局输入名几乎都至少出现于一个 MIS”，不能支持：

- 输入动态到达目标 root；
- 切片 sound/complete；
- 5005 个输入都被有效执行；
- 未匹配变量不会漏 bug。

实际上全体 MIS 的并集几乎等于全输入空间，效率来自局部分组和优先级，而不是全局删掉大多数输入。

### 14.5 PGFuzz 比较的含义

论文把结果与 PGFuzz 已公开 bug 报告比对：8 个重叠，声称另有 79 个。它不是在同 SUT commit、同 mission、同硬件、同 24 小时预算下重跑 PGFuzz，因此不能视为严格 head-to-head 性能实验。两者目标也不同：PGFuzz 从文档 policy 出发，ADGFuzz 从实现赋值名称出发。

### 14.6 内在数字与术语问题

- 论文称 77 个单输入、11 个双输入、1 个三输入，总和为 89，不是 87。
- 摘要/正文有时把软件 crash 称为 memory overflow，有时又指 arithmetic/floating-point overflow；代码 oracle 实际只观察通信沉默，无法直接区分。
- 论文称其余 71.98% 历史缺陷为 missing inputs，但表 I 并未支持这一统一因果解释。
- PX4 移植段落说因为命名相似可“跳过 Step (1) 构建 ADG”，逻辑上更可能是想说可减少词表适配；公开仓库实际包含 PX4 静态 ADG。
- Artifact Appendix 提到 `fuzz.sh`、`env_set.sh` 和自动去重，当前 GitHub 检出缺少前两个脚本，去重也没有全局实现。实验 VM 可能含有不同版本，无法仅凭公开仓库确认。

### 14.7 论文承认的局限

- 输入激活到异常表现有不可量化延迟；作者用频繁转弯 mission 缩短偏航显现时间。
- SITL 不代表传感器噪声、执行器故障、真实延迟和电气问题。
- 仿真未激活、只在实机路径执行的赋值无法测试。
- 无源码或变量名没有语义时，方法失效。
- 移植新平台需要重新整理可控输入、术语表、注入、反馈和误报过滤。

---

## 15. 代码中到底用了哪些工具

### 15.1 核心方法依赖与辅助依赖要分开

| 层次 | 工具/库 | 具体用途 | 是否属于 ADGFuzz 的核心算法 |
|---|---|---|---|
| 静态抽取 | Python `re`、`os`、`json` | 扫描 `.cpp`、正则识别函数和赋值、输出 JSON | 是 |
| 名称映射 | Python `csv`、字符串切分、手工词表 | 叶变量词语映射到参数、命令、环境和 RC | 是 |
| 调度/取值 | NumPy、Pandas、Python `random` | softmax 抽 MIS、读参数表、生成取值 | 是 |
| RV 交互 | `pymavlink`、MAVLink | 改参数、发命令、上传 mission、读遥测 | 是 |
| 距离 oracle | `geopy`、`geographiclib` | PX4 路线偏离时计算经纬度距离 | 是 |
| 被测系统 | ArduPilot、PX4 | 被测飞控实现 | 是，但不是仓库 Python 代码的一部分 |
| 仿真 | ArduPilot SITL、PX4 SITL、jMAVSim | 提供传感器和车辆运动环境 | 是 |
| 地面站/启动 | MAVProxy、`sim_vehicle.py`、GNOME Terminal、Bash | 启动飞控、控制台和网络端点 | 运行环境 |
| 数据整理 | BeautifulSoup、lxml | 从网页/HTML 整理参数和命令 CSV | 离线辅助 |
| 覆盖实验 | `lcov`/`genhtml` 相关脚本与结果读取 | 论文附加的离线覆盖比较 | 不是在线反馈 |
| 构建环境 | `make`、编译器、Java JDK 15+ | 构建 ArduPilot/PX4、运行 jMAVSim | 运行环境 |
| VM | VMware、VirtualBox、Parallels | 运行作者提供的预配置镜像 | 可选复现环境 |
| 一次性语义整理 | 未公开型号/提示词的 LLM | 论文称帮助从注释构建 physical coupling 表 | 只用于离线词表准备，运行时不用 |

代码直接导入的关键第三方包可见：

- [`fuzzer/fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py:1>)：NumPy、pymavlink；
- [`fuzzer/runtimedict.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/runtimedict.py:1>)：Pandas、NumPy；
- [`fuzzer/oracle.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py:1>)：pymavlink、geopy；
- [`static/tree_parse.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py:1>)：只有 Python 标准库。

[`requirements.txt`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/requirements.txt:1>) 固定了 56 个 Python 包，其中很多是 PX4/DroneCAN/MAVLink 工具链、绘图或传递依赖，并不意味着 ADGFuzz 算法逐一调用它们。反过来，运行说明依赖的 MAVProxy、GNOME Terminal、SITL、jMAVSim、lcov 和系统编译工具也不能只靠这份 requirements 安装。

### 15.2 明确没有使用的静态分析工具

公开实现没有使用以下任何一种：

- Clang AST/LibTooling；
- LLVM IR、LLVM Pass、`opt`；
- SVF、Andersen/Steensgaard pointer analysis；
- Tree-sitter；
- CodeQL、Joern、Coccinelle；
- Ghidra、IDA 或二进制分析；
- SanitizerCoverage、AFL instrumentation、libFuzzer coverage；
- 动态污点分析。

仓库中虽有一个 [`static/test1.bc`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/test1.bc>)，但主静态链路从未读取它；不能据此说作者用 LLVM 构建 ADG。

### 15.3 从命令行到 oracle 的代码调用链

```text
adgfuzz.py
  ├─ read_initfile()              读 static/initpath 或用户给定 ADG JSON
  ├─ Mapp.parse_ipaths()          叶名 → MIS + 初始分数
  ├─ ardupilot_init()/px4_init()  启动 SITL/GCS
  └─ ADGfuzzer.run()/PX4fuzzer.run()
       ├─ connect_init()          UDP 14550 执行连接
       ├─ Oconn_init()            UDP 14551 oracle 连接
       ├─ mission/arm/takeoff     建立有效任务状态
       ├─ select_from_paths()     softmax 选 MIS
       ├─ RuntimeDictionary       取参数值
       ├─ rvmethod.paramset()     PARAM_SET
       ├─ rvmethod.send_mav_cmd() COMMAND_LONG
       ├─ oracle 三线程           读消息、分发、判异常
       ├─ save_bug()              保存当前 MIS 的累积输入序列
       └─ close_and_relunch()     结束并重启 SITL
```

论文步骤与公开代码的最短索引如下：

| 论文概念 | 主要代码位置 |
|---|---|
| ADG 构建 | [`static/tree_parse.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/static/tree_parse.py>) |
| MIS 和“熵” | [`model/Mapping.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/model/Mapping.py>) |
| 主程序和仿真启动 | [`adgfuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/adgfuzz.py>) |
| ArduPilot fuzz loop | [`fuzzer/fuzz.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzz.py>) |
| PX4 fuzz loop | [`fuzzer/fuzzpx4.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/fuzzpx4.py>) |
| 参数/命令取值 | [`fuzzer/runtimedict.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/runtimedict.py>) |
| MAVLink 操作 | [`fuzzer/rvmethod.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/rvmethod.py>) |
| 三类 oracle | [`fuzzer/oracle.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/oracle.py>) |
| 自动后处理 | [`fuzzer/postprocess.py`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/fuzzer/postprocess.py>) |
| 参数、命令、枚举元数据 | [`data/`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/data>) |
| 名称和物理耦合表 | [`map/`](</home/lqq/project/TAFuzz/baseline/ADGFuzz/map>) |

---

## 16. 对 TAFuzz：哪些应该借，哪些不能照搬

### 16.1 可迁移的方法思想

| ADGFuzz 思想 | 对 TAFuzz 的对应实现 |
|---|---|
| 从结果变量向输入反向追依赖 | 从 MITL 原子命题、事件和计时器向报文字节/API/配置反向构造 TPDG |
| MIS 把巨大空间分成局部相关输入集 | 每条性质产生 `mutation_region`、操作序列候选和状态前置条件 |
| 完整 mission 保持深状态可达 | 使用合法协议会话 seed，把握手、建链、协商等前缀固定或低频变异 |
| 多输入在同一状态演化中累积 | 在同一 scoped transaction/session 中组合字段、消息顺序、延迟和丢包变异 |
| 后果 oracle 与过程无关 | TAMonitor 判性质；另保留 crash、timeout、deadlock、资源异常等通用结果 oracle |
| 保存整段输入并重放约简 | 保存报文、调度时间、线程/连接、随机种子和 AP trace，做时序保持的序列最小化 |

### 16.2 不应迁移的实现选择

1. **不要用正则解析 C/C++。** 宏、模板、重载、字段、指针和跨函数依赖是协议实现的常态。
2. **不要把名称相似当成最终依赖。** 名称适合作为候选召回证据，不能替代 Decl、def-use、alias 和调用关系。
3. **不要丢掉完整图。** 必须保留源码位置、类型、边种类、函数上下文、置信度和解释路径。
4. **不要让裸 softmax 吃原始分数。** 当前 ADGFuzz 的初始选择几乎退化为按最高分顺序轮询；TAFuzz 需要归一化和显式探索。
5. **不要只在出 bug/不出 bug 后衰减。** 你的时间自动机已经能提供更细的进度、转移和距离反馈。
6. **不要把通信静默直接等同 crash。** 分别报告进程退出、信号、超时、死锁、连接关闭、协议无响应和监控不完整。
7. **不要让不同线程竞争消费同一消息流。** 单接收器排序、复制或事件总线分发，才能保证 AP trace 完整。
8. **不要省略随机性和时间日志。** 没有 RNG seed、调度延迟和 ACK/响应证据，时序故障很难精确重放。

### 16.3 最关键的边界

ADGFuzz 可以帮助你设计 **guidance**，却不能填补你的 **property extraction** 和 **instrumentation**：

```text
ADGFuzz 已有                         TAFuzz 必须新增
-------------------------------     --------------------------------------
人工固定的后果 oracle               RFC → 有来源证据的类型化时间性质
名称启发的函数内叶变量              AP → C/C++ Decl/Field/Event/Timer 绑定
外部 MAVLink 输入注入               报文字节/网络调度/配置/API 多入口变异
外部遥测观察                        生命周期正确的内部选择性插桩
bug/no-bug 分数衰减                  TA 转移、距离、AP 和切片命中动态反馈
```

因此，你现有“时间自动机验证已完成”的工作不是 ADGFuzz 的同类模块，而是比它的固定 oracle 更强的后端。下一步应先把性质和 AP 可靠地接到源码事件，再接种子调度。

---

## 17. 性质提取：ADGFuzz 没有做，TAFuzz 应怎样做

### 17.1 先区分四个对象

| 对象 | 例子 | 谁负责产生 |
|---|---|---|
| 规范性质 | “无 ACK/RST 时，首次重传应在参数定义的时间窗内发生” | RFC context + typed Property IR |
| 原子命题 AP | `con_sent(mid)`、`ack_received(mid)`、`timer_fired(mid)` | Property IR 分解 |
| 源码观测 | 某 timer registration、send call、state transition、字段更新 | binder + TPDG + observation planner |
| verdict/oracle | `POSITIVE/NEGATIVE/INCONCLUSIVE` | TAMonitor；另加通用运行异常 oracle |

ADGFuzz 直接手写了最后一列中的三个后果条件，没有前三列的自动管线。你的“性质提取”不应理解成搜到一句含 `MUST` 的文本后直接让 LLM 写 MITL。

### 17.2 推荐的 RFC → Property IR 管线

1. **规范源固定**：保存 RFC 版本、section、段落 ID、原文哈希和引用范围。
2. **候选召回**：召回包含规范词、定时器、持续时间、重传、等待、过期、周期或顺序约束的句子。
3. **上下文恢复**：解析交叉引用、术语定义、默认值、公式、例外、状态前提和参数约束。
4. **类型化抽取**：输出 trigger、guard、obligation/prohibition、time bound、scope、exception、参数来源，而不是 MITL 字符串。
5. **符号界限解析**：例如上界不是常数，而是 `ACK_TIMEOUT × ACK_RANDOM_FACTOR`；参数取运行配置或规范默认值。
6. **确定性模板编译**：由受测试的模板把已通过 schema 的 IR 编译成 MITL/监控自动机。
7. **验证门**：schema、来源、单位、上下界、正/反例、可满足性和 TAMonitor 解析全部通过后才允许执行。
8. **人工审阅状态**：保留 `candidate/reviewed/accepted/rejected`，不能把 LLM 候选直接当 ground truth。

建议 Property IR 至少具有：

```json
{
  "property_id": "rfc7252-first-retransmission-window",
  "provenance": {
    "document": "RFC 7252",
    "sections": ["4.2", "4.8"],
    "source_hash": "..."
  },
  "scope": {"kind": "coap_exchange", "keys": ["endpoint", "mid", "token"]},
  "trigger": "con_sent",
  "guard": "no_ack_or_rst",
  "obligation": "con_retransmitted",
  "window": {
    "lower": "ACK_TIMEOUT",
    "upper": "ACK_TIMEOUT * ACK_RANDOM_FACTOR",
    "unit": "s"
  },
  "exceptions": ["exchange_cancelled", "transport_closed"],
  "review_status": "reviewed"
}
```

这里的字段是设计示意，不是从 ADGFuzz 代码已有格式改名而来。

### 17.3 LLM 可以做什么，不能做什么

LLM 适合：

- 给候选句分类；
- 在已提供的规范上下文中抽 trigger/guard/exception；
- 把规范词与可能的源码同义词关联；
- 为人工审阅生成解释。

LLM 不应独立决定：

- 最终时间数字和单位；
- 最终 MITL 字符串；
- 某 C/C++ 字段必然实现了某 AP；
- 插桩放在赋值前还是后；
- 测试 verdict。

这些必须由规范证据、类型检查、静态语义、运行 trace 和确定性验证共同约束。这一点正好修正 ADGFuzz 的弱点：其 physical table 由注释和一次性 LLM 帮助整理，却没有公开生成器、模型、提示词和人工决策记录。

### 17.4 与现有设计的连接

工作区已有详细前端设计：

- [TAFuzz-MITL 系统设计](</home/lqq/project/TAFuzz/documents/TAFuzz_MITL_CCFA_design.md>)；
- [TAFuzz MITL Front-end 实施计划](</home/lqq/project/TAFuzz/documents/TAFuzz_MITL_implementation_plan.md>)；
- [原子命题映射样例](</home/lqq/project/TAFuzz/analysis/protocol_fuzzing_study/atomic_proposition_map.yaml>)；
- [插桩 hook 样例](</home/lqq/project/TAFuzz/analysis/protocol_fuzzing_study/instrumentation_hooks.csv>)。

ADGFuzz 的研究不会推翻这套设计。它强化了其中 TPDG 的必要性：不仅为 AP 选择观测点，还应反向导出影响 AP 的输入区域和组合关系。

---

## 18. 如何做静态分析、获取对象字段并选择插桩点

### 18.1 为什么“找到变量名”不够

设协议实现中有：

```cpp
struct Exchange {
    uint16_t message_id;
    State state;
    Timer retransmit;
    unsigned retry_count;
};

ex->retry_count += 1;
schedule(&ex->retransmit, deadline);
```

ADGFuzz 的正则近似会把 RHS 的 `ex->retry_count` 变成一个字符串，把左值、类型和对象上下文处理得不一致。真正需要回答的是：

1. `retry_count` 是哪个 `RecordDecl` 的哪个 `FieldDecl`？
2. `ex` 的静态类型是什么，可能指向哪些 allocation/object？
3. 当前写入是 read-modify-write 还是全覆盖？
4. 哪些网络输入、配置和回调能到达它？
5. 这个写入发生在重传 send 前、后，还是 timer 注册时？
6. 运行时哪一个 `Exchange` 实例对应当前 MID/token？

### 18.2 源码层：Clang AST 获取声明、字段和访问路径

以 `compile_commands.json` 作为唯一编译事实，使用与目标相同的宏、include、语言版本和 target。对每个翻译单元建立索引：

- `RecordDecl/CXXRecordDecl`：结构体/类；
- `FieldDecl`：字段名、类型、偏移相关声明、所属 record；
- `VarDecl/ParmVarDecl`：全局、局部和参数；
- `FunctionDecl/CXXMethodDecl`：完整限定名、签名、模板实例；
- `MemberExpr`：`obj.field` 或 `ptr->field`；
- `DeclRefExpr`：变量和函数引用；
- `CallExpr/CXXMemberCallExpr`：调用；
- `BinaryOperator/CompoundAssignOperator`：写入和 read-modify-write；
- `ArraySubscriptExpr`：数组/表项；
- `IfStmt/SwitchStmt`：控制条件。

每个实体不能只存名字，应存稳定身份：

```text
decl_id     = Clang USR 或“canonical declaration + project-relative location”
record_id   = 完整限定 record USR
field_id    = record_id + FieldDecl USR/位置
access_path = ex -> retransmit -> deadline
type        = canonical QualType
site_id     = source hash + file + expansion/spelling location + AST role
```

宏内代码要同时保存 spelling location 和 expansion location。C++ 重载函数用 USR/签名区分，不能像 ADGFuzz 一样用裸函数名覆盖。

### 18.3 IR 层：字段在 LLVM 中怎样出现

编译成带 debug metadata 的 LLVM bitcode 后，结构体字段访问通常成为 `getelementptr`（GEP）：

```llvm
%field_ptr = getelementptr inbounds %struct.Exchange,
             ptr %ex, i32 0, i32 3
%old = load i32, ptr %field_ptr
%new = add i32 %old, 1
store i32 %new, ptr %field_ptr
```

其中 `i32 3` 是布局索引，不应该直接当业务字段名。需把 GEP source element type、索引和 `DICompositeType/DIDerivedType` 调试信息映回 `Exchange::retry_count`。当优化使 debug 信息不完整时，以 AST 语义索引为主，IR 地址/def-use 为辅，并标注置信度。

在 IR 上构建：

- SSA def-use；
- `MemorySSA` 的 memory def/use；
- LLVM Alias Analysis；
- call graph 和参数/返回值传播；
- branch/control dependence；
- callback registration → callback target；
- timer schedule/cancel → timer fire callback；
- thread/task/queue enqueue → dequeue/handler；
- network receive buffer → parser → state/field；
- state/field/timer → serializer/send。

如果第一版不上完整 SVF，也可以先用 LLVM AA + MemorySSA + 框架摘要做保守切片；边必须带 `exact/may/modelled/name-only` 置信度，不能把所有边伪装成确定事实。

### 18.4 “对象字段”有三个不同层次

| 层次 | 要获取的内容 | 方法 |
|---|---|---|
| 类型字段 | `Exchange::retry_count` 存在、类型、所属类 | Clang `FieldDecl` |
| 访问字段 | 某语句在读/写 `ex->retry_count` | Clang `MemberExpr` + AST parent；IR GEP/store 复核 |
| 运行实例字段 | 这次观测属于哪一个 exchange | 运行时 scope/correlation key；对象地址只作辅助 |

对象地址不能作为跨重启的稳定身份，allocator 还会复用地址。协议监控应优先使用语义 scope：

```text
(connection_id, endpoint, message_id, token, stream_id, transaction_id)
```

如果业务 key 尚未初始化，可短暂使用 `(process_epoch, object_address, allocation_generation)`，随后在解析出 MID/token 时绑定语义 key。释放时发 `scope_end`，避免地址复用把两个事务混成一个。

### 18.5 从 AP 反向构建 TPDG

不要从“所有赋值”出发建一个无边界大图，而从已审阅 AP 的候选 sink 出发：

```text
AP sink
  ← 字段/局部变量的 def-use
  ← 控制条件
  ← 调用参数和返回值
  ← timer/callback/queue 异步边
  ← parser/serializer 字段
  ← 外部输入字节、API、配置、故障调度
```

TPDG 节点至少分为：

- `InputByte/PacketField/APIArg/Config`；
- `Decl/Field/MemoryRegion`；
- `Predicate/Branch/StateTransition`；
- `TimerStart/Cancel/Fire`；
- `CallbackRegister/Invoke`；
- `QueueEnqueue/Dequeue`；
- `NetworkSend/Receive`；
- `AtomicProposition`。

边至少包括 data、control、alias、call/return、parse/serialize、timer、callback、queue、happens-before 和 scope-correlation。最终产物不能只是一张图，还要输出每条 AP 的解释路径：

```text
packet byte[2:4]
  --parse--> header.mid
  --compare--> transaction.mid
  --control--> cancel_timer(transaction.timer)
  --event--> ack_received(mid)
```

### 18.6 Observation Contract 决定在哪里插桩

每个 AP 都要有一份 contract：

```text
AP id             timer_cancelled
scope key         connection_id + MID/token
source expression timer object + reason
capture phase     before cancel-and-clear
value type        event + timer generation
timestamp clock   CLOCK_MONOTONIC_RAW 或平台一致单调时钟
validity guard    timer_active && matching_generation
fallback          send/cancel wrapper hook
confidence        exact/modelled/heuristic
```

“最靠近字段的 store”不一定是正确观测点：

- 若函数先清空 transaction 再返回，应在清空前捕获 `transaction_done`；
- 若 AP 是“值已更新”，应在 store 后捕获；
- 若 AP 是“准备发送”，内部 enqueue 和真正 socket send 是两个事件；
- 若 timer callback 被取消但已入队，cancel 与 callback 是否执行要分别记录；
- 若状态在多个分支写入，优先在统一状态转换函数插桩，同时保留原因和旧/新状态。

### 18.7 选择性插桩，不是插所有赋值

推荐目标函数：

\[
\min \sum_{s\in S} cost(s)
\]

约束是每个 AP 的值、时间、scope 和生命周期必须可重建，并覆盖所有高置信实现路径。候选点排序可考虑：

- 是否位于统一 wrapper/transition API；
- 是否能同时观测多个 AP；
- 是否避免高频循环；
- 是否在编译优化后仍稳定；
- 是否拥有完整 scope；
- 是否会改变时序；
- 是否有语义等价的 fallback 点。

用 full instrumentation 作为实验 oracle：同一 workload 下，选择性 trace 与全插桩 trace 投影后必须给出相同 TAMonitor verdict。只有这样才能声称插桩“足够”。

### 18.8 运行时记录格式

建议固定二进制或紧凑 POD 记录：

```text
schema_version
process_epoch
monotonic_timestamp_ns
global_or_thread_sequence
thread_id
scope_kind + scope_id_hash
ap_id/event_id/site_id
phase                 # before/after/edge
value_type + value
flags                 # inferred, truncated, dropped, clock-sync...
```

写入 thread-local ring buffer，异步批量消费。队列溢出必须记录 drop count；只要缺失事件可能改变 verdict，就输出 `INCONCLUSIVE`，不能把缺失 AP 当 false。多线程合并采用 `(timestamp, thread_seq)` 和同步事件约束；跨进程/机器则必须显式校时并报告误差界。

---

## 19. TAFuzz 的种子、变异、反馈应该怎样借鉴 ADGFuzz

### 19.1 你的系统确实需要传统 seed

ADGFuzz 能在每次 mission 中直接调用结构化 MAVLink API，所以不需要字节串 seed。协议 fuzzer 要到达深状态，通常必须有合法会话：

```text
连接 → 协商/注册 → 请求 → 响应/确认 → 重传/超时/关闭
```

因此 TAFuzz 应保留两层对象：

- **Seed/session trace**：能到达目标协议状态的消息与调度序列；
- **Property-specific mutation plan**：由 TPDG 从目标 AP 反推的可变异字段、消息、时延、状态操作和配置。

前者解决可达性，后者缩小输入空间。不能把两者合并成 ADGFuzz 那样一个 MIS。

### 19.2 种子选择

每条 seed 维护分离的静态先验和动态反馈：

```text
static_prior:
  AP 绑定置信度
  TPDG 路径长度/分支数
  可影响 AP 的字段专一性
  目标状态可达性

dynamic_reward:
  新 AP/边/状态命中
  新 TA location/transition
  violation distance 改善
  新协议状态组合
  新 outcome/crash/timeout/deadlock/resource exception
  稳定可重放性
```

先对每个分量按 property/seed pool 归一化，再使用温度可控 softmax 或 UCB/Thompson sampling；同时保留 `epsilon` 随机探索和 round-robin 最低配额。不要把原始图节点数直接放进指数函数。

一个可解释的第一版分数可以是：

\[
S(s,p)=w_r R_{static}(s,p)+w_t N_{TA}(s,p)+w_a N_{AP}(s,p)
      +w_d \Delta D_{violation}(s,p)+w_o N_{outcome}(s)
\]

其中每项先缩放到 `[0,1]`。这不是唯一公式；重要的是指标可消融、量纲一致、保留探索，并记录每次调度决策的组成。

### 19.3 变异区域

TPDG 为每条性质导出：

```text
message_indices       哪些消息可改
byte_ranges           编码后的字节范围
semantic_fields       MID/token/type/code/option/length/payload...
state_actions         reconnect/cancel/rebind/duplicate...
schedule_actions      delay/drop/reorder/duplicate/fragment
configuration         timer/retry/window/buffer limits
guards                保持目标状态可达的约束
coupled_groups         必须联合或一致变异的字段
```

变异器按层工作：

1. **结构保持型**：在合法编码内变边界、枚举、长度、计数和交叉字段；
2. **结构破坏型**：长度不一致、重复 option、截断、非法组合；
3. **序列型**：删、插、重复、交换消息或 API 操作；
4. **时间型**：改变发送间隔、响应延迟、丢包、重排、timer 参数；
5. **状态型**：连接重建、并发 transaction、取消/关闭与回调竞争；
6. **组合型**：按 TPDG 的 shared sink 联合变异两个或多个输入。

始终保留一部分“非相关区域”低概率探索，因为静态切片可能漏 alias、动态注册、宏或外部环境依赖。

### 19.4 反馈不只是 coverage

你的时间自动机后端可提供 ADGFuzz 没有的细粒度反馈：

| 反馈 | 含义 | 调度作用 |
|---|---|---|
| AP reach | 哪些 AP 曾出现 | 奖励抵达目标观测链 |
| AP order/pair | 新的 AP 顺序或组合 | 奖励时序路径新颖性 |
| TA location | 到达的新自动机位置 | 状态覆盖 |
| TA transition | 新触发的 guard/clock transition | 时间/逻辑覆盖 |
| priced distance | 到 violation/目标边的剩余 cost | 连续进度信号 |
| TPDG slice hit | 输入实际到达哪些 sink/site | 校正静态先验 |
| protocol state | 连接/事务/重传等状态组合 | 防止只覆盖代码浅层 |
| outcome | crash、timeout、deadlock、资源异常 | 独立结果类别 |
| reproducibility | 相同调度重放成功率 | 抑制不稳定噪声 |

静态先验只负责冷启动；动态观测应逐渐修正“名字/图上可能相关”与“运行时确实相关”的差别。即使本轮没有违反性质，只要更靠近目标 clock guard、触发了新的 AP 顺序或激活了未见状态，也应得到正反馈。

### 19.5 能量和停止条件

执行能量不应像 ADGFuzz 那样直接等于未经归一化的 entropy。可根据：

- 到目标状态前缀的成本；
- 最近若干执行的 reward slope；
- seed 执行时间；
- 稳定性；
- property 剩余未覆盖转移；
- 当前 mutation region 大小；
- 全局公平预算。

设置最小/最大能量、无进展退火和每条性质的公平配额。触发违反后先冻结完整证据，再进行重放；不能立刻覆盖原始 seed/trace。

### 19.6 可重现日志与约简

每次执行至少保存：

- SUT commit/build manifest、编译参数、插桩 schema；
- property/AP/binding/TPDG 版本和哈希；
- 初始 seed、每个 mutation operator 及偏移/语义字段；
- Python/C++/网络调度 RNG seed；
- 每个消息和动作的计划时间、实际时间、返回/ACK；
- process/thread/connection/scope 标识；
- 原始 AP event log、drop count、assembled timed word；
- TAMonitor verdict、自动机轨迹、通用 outcome；
- 重放次数与成功次数。

最小化要同时处理消息、字段、并发和时间：先删除不必要前后缀，再做序列 delta debugging，然后字段归零/规范化，最后收缩 delay/window；每一步都从干净状态重放，并要求相同 property、scope 和 violation witness，而不是只要求“程序又沉默”。

---

## 20. 一个与飞控无关的完整 CoAP 例子

以下是架构示例，源码标识是示意名称，不声称对应某个 libcoap 版本的精确字段。

### 20.1 规范性质

目标：Confirmable（CON）消息发出后，在同一 exchange 未收到匹配 ACK/RST 且未被取消时，首次重传发生在由 `ACK_TIMEOUT` 和 `ACK_RANDOM_FACTOR` 决定的窗口内。

这里必须明确两个可能的观测语义：

- **timer obligation**：首次重传 timer 被安排/触发在窗口内；
- **wire obligation**：真正的重传报文到达 socket send/wire hook 的时间在窗口内。

enqueue、timer fire 和实际 send 可能因线程调度而不同。论文级实验应分别定义，不能用其中一个偷偷替代另一个。

### 20.2 Scoped AP

对每个 `(connection, endpoint, MID, token)` 建一个 monitor instance：

```text
con_sent
ack_or_rst_received
retransmit_timer_started(deadline, generation)
retransmit_timer_fired(generation)
con_retransmitted
timer_cancelled(reason)
exchange_done(reason)
```

“没有 ACK/RST”不是一条孤立事件，而是从 `con_sent` 到目标时间内状态保持为 false。收到不同 MID 的 ACK 不能取消此 instance。

### 20.3 源码绑定和 TPDG

候选 sink：

- 初始 CON 的统一 send wrapper；
- packet parser 中确认类型和 MID/token 的位置；
- transaction lookup；
- retransmission timer schedule/cancel/fire；
- retry counter/state transition；
- 重传 send wrapper；
- exchange 释放/结束。

反向切片可能得到：

```text
wire bytes: type/MID/token
  → parser header fields
  → transaction lookup key
  → ACK/RST branch
  → cancel(timer generation)

config: ACK_TIMEOUT, ACK_RANDOM_FACTOR
  → randomized initial timeout
  → timer deadline
  → callback
  → retransmit state
  → encoded CON send
```

### 20.4 选择性插桩

| 位置 | 事件 | 采样时机 | 原因 |
|---|---|---|---|
| 初始 send wrapper | `con_sent` | send 成功后 | 以真实发送为时间零点 |
| timer schedule wrapper | `timer_started` | deadline 确定后 | 记录参数求值结果和 generation |
| parser + lookup 成功 | `ack_or_rst_received` | 匹配 scope 后 | 排除其他事务确认 |
| cancel wrapper | `timer_cancelled` | 清空 timer 前 | 保留 generation/reason |
| timer callback 入口 | `timer_fired` | callback 开始 | 区分触发与发送延迟 |
| 重传 send wrapper | `con_retransmitted` | send 成功后 | 监控 wire obligation |
| transaction destructor/end | `exchange_done` | key 被清除前 | 正确结束 scoped monitor |

若只在 `retry_count++` 插桩，会同时漏掉“计数变了但报文没发”和“发送由另一条路径完成”两种情况。

### 20.5 种子和变异

Seed 是一个可成功完成的 CON→ACK 会话。为测试该性质：

1. 保持建立 socket、构造 endpoint 和初始 CON 的前缀；
2. 网络调度器对匹配 ACK 做 drop/delay/reorder；
3. 对 MID/token 做一致或不一致的 coupled mutation；
4. 改 `ACK_TIMEOUT`、`ACK_RANDOM_FACTOR` 或运行配置边界；
5. 可并发第二个 exchange，测试 timer/scope 串扰；
6. 观察 timer generation、send event 和 TA 转移。

如果把 ACK 直接删掉后程序按时重传，这不是 bug，但它可覆盖目标 AP/转移；下一轮可围绕窗口边界做更细 delay/config 变异。

### 20.6 一条示例 trace

```text
0.000000  scope=E17  con_sent(mid=0x1234)
0.000120  scope=E17  timer_started(deadline=2.37s,generation=8)
2.371006  scope=E17  timer_fired(generation=8)
2.373281  scope=E17  con_retransmitted(mid=0x1234)
2.500000  scope=E17  ack_received(mid=0x1234)
2.500042  scope=E17  timer_cancelled(reason=ack,generation=9)
2.500101  scope=E17  exchange_done(reason=success)
```

Assembler 将 event 转成该 scope 的 timed word；参数解析器在执行 manifest 中记录本轮 `ACK_TIMEOUT` 和 `ACK_RANDOM_FACTOR`，TAMonitor 据此实例化边界。generation 可防止旧 timer callback 被错误归入新一轮重传。

### 20.7 失败证据必须说明是哪一种失败

可能结果包括：

- timer 本身过早/过晚；
- timer 按时 fire，但 send queue 延迟过大；
- ACK 匹配正确，却没有取消 timer；
- 另一个 exchange 的 ACK 错误取消当前 timer；
- AP trace 丢失，结果只能是 `INCONCLUSIVE`；
- 进程退出/无响应，但尚不能断言是哪条性质违反。

这比 ADGFuzz 的“2 秒收不到任意 MAVLink 消息就记 software crash”提供了更精确的因果边界。

---

## 21. 结合你当前进度的实施顺序

你已经完成时间自动机验证，因此不要先写 ADGFuzz 风格的调度器。最短闭环应是：

```text
一条真实 RFC 时间性质
  → 类型化 Property IR
  → 3–8 个 scoped AP
  → AP 到真实 C/C++ 源码的可审计绑定
  → 生命周期正确的选择性插桩
  → event assembler
  → 现有 TAMonitor verdict
  → 一条可重放正例和一条可重放反例
```

### 21.1 阶段 A：性质与证据闭环

先只选 RFC 7252/libcoap 的一条重传性质：

- 固定规范来源和完整上下文；
- 完成 typed IR、符号参数和 exception；
- 人工给出正/反例 timed trace；
- 用现有 TAMonitor 确认预期 verdict；
- 冻结 property schema version。

验收：不看源码也能审计“这条公式为何如此、数字来自哪里、例外是什么”。

### 21.2 阶段 B：语义索引和 AP binder

- 从真实 `compile_commands.json` 建 Clang AST 索引；
- 记录函数 USR、record、field、member access、call、state comparison 和源码范围；
- 给每个 AP 生成多个候选及分项证据；
- 人工确认 gold binding；
- 输出 binding confidence 和解释，不静默选最高分。

验收：字段同名、函数重载、`obj.field`/`ptr->field`、宏展开和跨文件调用不会被合并成同一字符串。

### 21.3 阶段 C：TPDG 和异步模型

- 生成 LLVM 18 bitcode；
- 实现 def-use、MemorySSA、AA 和 call/return；
- 为 libcoap 的 timer、callback、queue、send/recv 建小而明确的框架摘要；
- 从 AP sink 反切到输入/配置；
- 与人工 gold slice 比较 precision/recall。

验收：至少能解释 `ACK bytes → lookup → cancel timer` 和 `timeout config → schedule → callback → retransmit` 两条路径。

### 21.4 阶段 D：选择性插桩和 trace assembler

- 生成独立 instrumented build tree；
- 实现带 schema/site/AP/scope 的低开销 event runtime；
- 明确 before/after、timer generation、scope start/end；
- 把 event/state 投影为 TAMonitor timed word；
- drop/不完整 scope 输出 `INCONCLUSIVE`；
- 对 full instrumentation 做 verdict equivalence。

验收：正例、早发、晚发、ACK 取消、错误 MID 和丢事件六类 fixture 均产生预期 verdict。

### 21.5 阶段 E：再接入 ADGFuzz 式输入指导

- TPDG 输出 property-specific mutation region；
- 维护合法会话 seed；
- 加网络 schedule mutator；
- 用 AP/TA/price/状态新颖性反馈调度；
- 记录全部 RNG 和时间；
- 做时序保持的 replay/minimize。

验收：与随机字段、普通 coverage、全消息变异和无 TPDG 版本比较 time-to-first-violation、有效执行率、深状态到达率与可重放率。

### 21.6 建议暂缓的范围

第一条性质闭环前，暂缓：

- 同时支持多个协议；
- 全量 RFC 自动抽取；
- 全程序所有赋值插桩；
- 复杂跨机器 eBPF 方案；
- 完整 SVF 接入；
- 五种调度算法同时实现；
- 仅凭 LLM 自动批准源码绑定。

这是工程依赖关系，不是能力限制：没有可信 AP trace，任何高级 seed feedback 都只是在优化错误信号。

---

## 22. 对用户问题的逐项直接答案

### 22.1 作者如何静态分析

只分析 `.cpp`；删除注释；用正则识别有限函数签名和赋值；在单函数内按字符串名称反向连接赋值；剪掉中间节点，只保存 root 的叶名和节点数。没有 AST、LLVM、CFG、跨过程、alias、类型和字段敏感分析。

### 22.2 作者如何选择种子

没有传统 seed corpus。先 softmax 选择一个 MIS，再从 MIS 的命令/参数/RC/环境类别中选择子集。实际 softmax 极度尖锐，使它近似按高原始分数顺序消费 MIS。

### 22.3 作者如何变异

对结构化参数和命令重新生成值：枚举/bitmask/边界/几何数量级/命令七参数；在一个 MIS 对应的同一 SITL 生命周期里累计多批输入。公开 RC 和独立环境路径存在实现缺陷；真正环境量多作为 `SIM_*` 参数进入。

### 22.4 反馈是什么

在线没有代码或状态覆盖。只有三类 oracle 触发与否，然后衰减/删除 MIS 分数。mission 状态本身不反馈给调度器。

### 22.5 oracle 是什么

测试判定器。ADGFuzz 人工定义三类：坠地/异常状态、到当前 waypoint 的距离持续或累计增加、连续若干次收不到任意 MAVLink 消息。它不是自动提取的规范性质，也不能直接证明内部算术根因。

### 22.6 作者如何获取对象的变量字段

静态阶段没有真正获取对象字段：RHS 的 `.`/`->` 被改成下划线字符串，丢失 record/type/instance 语义；遥测阶段的字段是 pymavlink 解码消息后的 Python 属性。若 TAFuzz 要正确获取字段，应使用 Clang `RecordDecl/FieldDecl/MemberExpr`，LLVM GEP+debug metadata 复核，并在运行时用 transaction/session correlation key 区分实例。

### 22.7 代码用了什么

核心是 Python 正则/JSON/CSV、NumPy、Pandas、pymavlink、geopy，加 ArduPilot/PX4、SITL、MAVProxy/MAVLink、jMAVSim 和系统构建工具；离线网页整理用 BeautifulSoup/lxml，论文称一次性借助未公开 LLM 整理物理词表。没有编译器静态分析或在线覆盖插桩工具。

### 22.8 你最应该借什么

借“从目标结果反向得到局部输入子空间、在完整状态工作流里组合执行、保存整段延迟触发序列并最小化”。不要借其正则分析、名称即依赖、raw softmax、固定后果 oracle 和不完整日志。

---

## 23. 阅读与复核入口

### 23.1 推荐阅读顺序

1. 先读本文 0、1、3，建立总体框架；
2. 读 4、5、6，理解 ADG、MIS 和 entropy 的论文—代码差异；
3. 读 7–12，理解实际 fuzz loop、反馈、oracle 和最小化；
4. 读 13、14，理解案例、实验和证据边界；
5. 读 16–21，把方法迁移到 TAFuzz。

### 23.2 本次复核基线

- 论文 PDF：19 页，逐页抽取并阅读，SHA-256 见文首；
- 代码：本地 commit `203fce3f4265241340ed62b9be90aec1da0afa37`；
- 静态结果实测覆盖 ArduPilot Copter/Plane/Rover 和 PX4 的公开 JSON；
- 未运行完整 SITL 24 小时实验；运行时行为结论来自源码路径、数据文件和 README 对照；
- 仓库原本已有运行产物和未提交文件，本次精读没有修改 ADGFuzz 源码或清理用户文件。

### 23.3 关键复核命令

```bash
# 锁定论文
sha256sum "/mnt/c/Users/PC-123/Zotero/storage/X8VTAKST/Wang 等 - 2026 - ADGFUZZ Assignment dependency-guided fuzzing for robotic vehicles.pdf"

# 锁定仓库
git -C /home/lqq/project/TAFuzz/baseline/ADGFuzz rev-parse HEAD
git -C /home/lqq/project/TAFuzz/baseline/ADGFuzz status --short

# 静态入口和运行入口
rg -n "def (parse_cpp_file9|process_files|parse_ipaths|select_from_paths|run|check_status|all_oracles|minm_inputs)" \
  /home/lqq/project/TAFuzz/baseline/ADGFuzz

# 直接依赖
rg -n "^(import|from) " \
  /home/lqq/project/TAFuzz/baseline/ADGFuzz/{adgfuzz.py,static,model,fuzzer}
```

这篇论文的最佳定位不是“可直接移植的高精度静态分析器”，而是一个很有启发性的 **assignment-name-guided structured stateful fuzzer**。你的时间自动机后端使 TAFuzz 有机会把它最弱的 oracle/feedback 部分变成强项；Clang/LLVM 语义索引、TPDG、scoped AP 和生命周期正确插桩则是必须补齐的前端壁垒。
