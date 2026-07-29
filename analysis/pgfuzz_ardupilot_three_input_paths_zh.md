# PGFuzz 三类输入在 ArduPilot 中的真实处理路径

## 1. 结论先行

`PGFuzz` 是 **Policy-Guided Fuzzing**，中文为“性质引导模糊测试”；它按照输入在测试中的语义，把输入分为三类：

- `InputP` 是 **Parameter Input**，中文为“配置参数输入”。它指可写入 ArduPilot 参数系统、并由飞控模块长期读取的参数。
- `InputC` 是 **Command Input**，中文为“用户命令输入”。在 PGFuzz 的实现中，它还包括 `Flight_Mode` 和 `RC1` 至 `RC4`，所以并不只等于 `MAV_CMD_*` 命令。
- `InputE` 是 **Environmental Input**，中文为“环境输入”。在 ArduPilot 工件中，它主要是 `SIM_*` 仿真参数，用于改变风、卫星、传感器、故障和仿真器状态。

这三类是测试语义分类，不是三种底层通信协议。PGFuzz 到 ArduPilot 实际使用四类 `MAVLink` 消息。`MAVLink` 是 **Micro Air Vehicle Link**，中文为“微型飞行器通信协议”；它在这里承担 PGFuzz 与飞控进程之间的消息编码、传输和分发。

| PGFuzz 类别 | PGFuzz 发送接口 | 实际 MAVLink 消息 | ArduPilot 结果 |
|---|---|---|---|
| `InputP` | `param_set_send` | `PARAM_SET` | 查找 `AP_Param` 对象、类型转换、写内存、保存持久化值；消费者随后读取同一对象 |
| `InputC`：普通命令 | `command_long_send` | `COMMAND_LONG` | 解码七个参数，转换为 `COMMAND_INT` 内部形式，按 `packet.command` 分派到通用或 Copter 专用处理器 |
| `InputC`：飞行模式 | `set_mode_send` | `SET_MODE` | 调用 `AP::vehicle()->set_mode(..., ModeReason::GCS_COMMAND)`，再执行模式准入条件与初始化 |
| `InputC`：`RC1..RC4` | `rc_channels_override_send` | `RC_CHANNELS_OVERRIDE` | 写入各 `RC_Channel::override_value`，RC 更新周期用覆盖值替代接收机输入 |
| `InputE` | `param_set_send` | `PARAM_SET` | 与 `InputP` 走完全相同的参数写入入口，但目标通常是 `SIM_*` 仿真对象，后续进入物理/传感器模型 |

所以“PGFuzz 静态分析不了命令和环境输入”不能解释为“这些输入无法进入源码”。它们明确进入源码。准确解释是：PGFuzz 的静态分析器只为配置参数变量建立正向值流，并没有为协议消息、命令编号、控制依赖、状态机前置条件、调度时序和物理闭环建立语义模型。

## 2. 版本与证据边界

- PGFuzz 工件冻结在 `7eaebf21116087249b8329d4ba7337a24a34ecb9`。
- 当前 TAFuzz 的 ArduPilot 冻结在 `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`。
- PGFuzz README 的位码构建示例针对历史 ArduPilot `68619c308737e5199992a9523bacabe9710c8e7e`。因此，本报告把“PGFuzz 如何发送输入”和“当前 ArduPilot 如何接收输入”作为两类证据分别陈述，不能把当前行号冒充论文时代行号。
- 本次只做源码与论文的只读核查，没有执行飞行仿真，也没有声称任何性质已经满足或违反。

## 3. 两层程序入口

### 3.1 PGFuzz 入口

外层入口是 `baseline/pgfuzz/ArduPilot/pgfuzz.py`：

1. 第 5 至 13 行读取 `PGFUZZ_HOME` 和 `ARDUPILOT_HOME`。
2. 第 17 至 18 行启动 `open_simulator.py`。
3. 等待 90 秒后，第 21 至 22 行启动 `fuzzing.py`。
4. 第 24 至 34 行监视 `restart.txt` 并在需要时重启仿真器。

真正的测试逻辑入口是 `fuzzing.py::main()`：

1. 第 35 行通过 `pymavlink` 创建 `udp:127.0.0.1:14551` 连接。`pymavlink` 是 MAVLink 的 Python 生成与通信库；`UDP` 是 **User Datagram Protocol**，中文为“用户数据报协议”，这里承载序列化后的测试消息。
2. 第 2422 至 2451 行分别加载 `parameters.txt`、`cmds.txt` 和 `envs.txt`。
3. 第 2454 行等待飞控心跳，随后完成模式切换、解锁和起飞等状态准备。
4. 第 2582 至 2587 行通过参数写入应用性质所需的前置条件。
5. 主循环调用 `pick_up_cmd()`；该函数在三类输入之间随机选择，再调用对应发送函数。

### 3.2 ArduPilot 入口

当前 Copter 的进程入口不是手写的普通 `main()`：

1. `ArduCopter/Copter.cpp:999-1002` 创建全局 `copter`，然后使用 `AP_HAL_MAIN_CALLBACKS(&copter)`。
2. `libraries/AP_HAL/AP_HAL_Main.h:35-40` 展开该宏，生成 `main()` 并调用 `hal.run(argc, argv, &copter)`。
3. `AP_Vehicle::setup()` 初始化参数表、加载持久化参数并初始化任务调度器。
4. `AP_Vehicle::loop()` 反复调用 `scheduler.loop()`。
5. `ArduCopter/Copter.cpp:207` 注册 `GCS::update_receive`，当前任务表的目标频率是 400 Hz。`GCS` 是 **Ground Control Station**，中文为“地面控制站”；在代码中也指管理 MAVLink 通道的接收/发送层。

## 4. MAVLink 统一收包与分发入口

不论 PGFuzz 发送哪一类消息，当前 ArduPilot 都先经过以下公共路径：

```text
GCS 调度任务
  -> GCS::update_receive()
  -> 每个通道的 GCS_MAVLINK::update_receive()
  -> 从端口逐字节读取
  -> mavlink_frame_char_buffer() 组帧
  -> raw_packetReceived()
  -> routing.check_and_forward() 路由检查
  -> accept_packet() 来源/接收检查
  -> handle_message()
  -> switch(msg.msgid) 分发
```

证据位于 `libraries/GCS_MAVLink/GCS_Common.cpp`：

- 第 1925 至 1979 行读取端口并组帧。
- 第 1881 至 1922 行完成帧状态、路由、来源检查并调用 `handle_message()`。
- 第 4369 行开始按 `msg.msgid` 分发。
- `PARAM_SET` 在第 4387 至 4391 行分到参数处理器。
- `SET_MODE` 在第 4441 至 4443 行分到模式处理器。
- `COMMAND_LONG` 在第 4464 至 4466 行分到命令处理器。
- `RC_CHANNELS_OVERRIDE` 在第 4589 至 4592 行分到遥控覆盖处理器。

## 5. `InputP`：配置参数如何进入并被模块消费

PGFuzz 的 `change_parameter()` 在 `fuzzing.py:365-434` 中产生变异值，并在第 415 至 418 行调用：

```python
master.mav.param_set_send(..., param_name, param_value,
                          MAV_PARAM_TYPE_REAL32)
```

ArduPilot 的处理闭环是：

1. `GCS_MAVLINK::handle_param_set()` 解码 `mavlink_param_set_t`。
2. `AP_Param::find(key, ...)` 按消息中的 `param_id` 找到真实参数对象；找不到时返回参数不存在。
3. 检查非数、无穷和写权限。
4. `vp->set_float(packet.param_value, var_type)` 根据目标真实类型写入 `AP_Float`、`AP_Int32`、`AP_Int16` 或 `AP_Int8`。
5. `vp->save(force_save)` 保存变化。
6. 飞控模块不需要再次“领取”一个消息值；它持有的成员就是刚刚被更新的 `AP_Param` 包装对象，后续任务周期直接读取它。

这里 `AP_Param` 是 **ArduPilot Parameter System**，中文为“ArduPilot 参数系统”；它把外部字符串参数名映射到带真实类型和存储位置的 C++ 对象。它决定了 `PARAM_SET` 并非仅把字符串留在协议层，而是真正改写模块成员。

### 5.1 真实例子：`FS_THR_VALUE`

PGFuzz 的多份性质输入文件包含 `FS_THR_VALUE`。当前源码链是：

```text
PGFuzz param_set_send("FS_THR_VALUE", v)
  -> PARAM_SET
  -> AP_Param::find("FS_THR_VALUE")
  -> Parameters::failsafe_throttle_value (AP_Int16)
  -> Copter::set_throttle_and_failsafe(throttle_pwm)
  -> throttle_pwm < failsafe_throttle_value
  -> 连续三次低值后 set_failsafe_radio(true)
```

- `ArduCopter/Parameters.cpp:132-139` 把外部名 `FS_THR_VALUE` 注册到成员 `failsafe_throttle_value`，类型是 `AP_Int16`。
- `ArduCopter/radio.cpp:137-160` 在无线电失效保护判断中读取该成员。
- 这个结果也说明，仅沿参数的数值流能找到阈值比较，但要得到可执行测试配方，还必须联合 `RC3`、解锁状态、曾经见过遥控输入和“连续三次”的事件条件。

## 6. `InputC`：用户命令不是一条通道，而是三条

### 6.1 普通 `MAV_CMD_*` 命令

PGFuzz 的 `execute_cmd()` 对一般命令调用 `command_long_send`，传入命令编号和七个随机参数。

当前 ArduPilot 的处理是：

```text
COMMAND_LONG
  -> handle_command_long()
  -> 解码 command + param1..param7
  -> try_command_long_as_command_int()
  -> 转为 mavlink_command_int_t
  -> Copter::handle_command_int_packet()
  -> switch(packet.command)
  -> 具体命令处理函数
  -> 返回 MAV_RESULT
  -> COMMAND_ACK
```

`COMMAND_ACK` 中的 `ACK` 是 **Acknowledgement**，中文为“确认”；它反映命令是接受、拒绝、失败还是不支持。只观察发送动作而不读取该结果，会把大量被拒命令误判为有效输入。

真实例子 `MAV_CMD_NAV_TAKEOFF`：

- `GCS_Common.cpp:5416-5448` 解码 `COMMAND_LONG`、执行命令并发送确认。
- `GCS_Common.cpp:5365-5379` 把长格式命令转为内部整数格式。
- `GCS_MAVLink_Copter.cpp:468-490` 按命令编号选择起飞处理器。
- `GCS_MAVLink_Copter.cpp:578-596` 检查坐标系，把 `packet.z` 作为起飞高度，再调用当前飞行模式的 `do_user_takeoff_U_m()`。

因此七个 `param` 字段不会统一存到某个全局“命令参数表”；它们随命令处理函数分别解释。相同的 `param1` 在不同命令中可以表示完全不同的量。

### 6.2 `Flight_Mode`

PGFuzz 对 `Flight_Mode` 不发送 `COMMAND_LONG`，而是发送 `SET_MODE`：

```text
SET_MODE
  -> handle_set_mode()
  -> _set_mode_common()
  -> AP::vehicle()->set_mode(custom_mode, GCS_COMMAND)
  -> Copter::set_mode()
  -> 模式是否存在、是否被 GCS 禁用、位置/高度估计、围栏、失效保护等准入检查
  -> new_flightmode->init()
  -> flightmode = new_flightmode
```

`ArduCopter/mode.cpp:313-480` 显示模式命令的实际效果取决于运行时状态。消息到达源码并不等于模式必然改变。

### 6.3 `RC1` 至 `RC4`

PGFuzz 的 `set_rc_channel_pwm()` 发送 `RC_CHANNELS_OVERRIDE`。当前 ArduPilot：

1. 验证消息来源是不是配置的 GCS。
2. 解码 16 个通道值；特殊值表示忽略或取消覆盖。
3. 调用 `RC_Channels::set_override()`。
4. `RC_Channel::set_override()` 写入 `override_value` 和时间戳。
5. `RC_Channel::update()` 在覆盖仍有效且未配置忽略时，用 `override_value` 替代物理接收机值，再换算为控制输入。

所以 RC 输入既进入了源码，也有明确的数据流；但它的行为取决于覆盖超时、忽略选项、飞行模式和控制环，不能只靠一个参数变量的 def-use 链描述。

## 7. `InputE`：环境因素为何也使用 `PARAM_SET`

PGFuzz 的 `execute_env()` 在 `fuzzing.py:2343-2375` 中选择 `SIM_*` 名字和值，第 2361 至 2364 行仍调用 `param_set_send()`。因此它在通信和参数存储层与 `InputP` 没有差别；差别在消费者语义。

### 7.1 真实例子：`SIM_WIND_SPD`

当前源码闭环是：

```text
PGFuzz param_set_send("SIM_WIND_SPD", v)
  -> PARAM_SET
  -> AP_Param::find("SIM_WIND_SPD")
  -> SITL::SIM::wind_speed
  -> SIMState::update_simulated_wind()
  -> 低通/延迟/高度风型处理
  -> input.wind.speed
  -> Aircraft::update_wind()
  -> wind_ef
  -> 飞行动力学与模拟传感器
  -> 飞控估计器和控制器观测到状态变化
```

`SITL` 是 **Software In The Loop**，中文为“软件在环仿真”；飞控和仿真环境都以软件运行，环境参数经物理模型和模拟传感器反馈到飞控。

- `ArduCopter/Parameters.cpp:422-425` 用 `SIM_` 前缀注册整个仿真参数组。
- `libraries/SITL/SITL.cpp:83-101` 把 `WIND_SPD`、`WIND_DIR` 和 `WIND_TURB` 映射到仿真对象成员。
- `libraries/AP_HAL/SIMState.cpp:281-338` 把目标风速经过起始延迟、时间常数和高度模型转换成 `input.wind`。
- `libraries/SITL/SIM_Aircraft.cpp:901-929` 把它转换成地球坐标系风矢量并叠加湍流。

该链条说明环境参数不是“传不进去”，而是最终影响性质命题通常要跨越参数层、仿真物理、传感器生成、驱动读取、状态估计和控制循环。

### 7.2 真实例子：GPS 卫星数

PGFuzz 历史工件使用 `SIM_GPS_NUMSATS`。当前源码已把 GPS 仿真参数改成分实例命名，如 `SIM_GPS1_NUMSATS`：

- `libraries/SITL/SITL.cpp:710-719` 注册 `GPS1_`、`GPS2_` 子组。
- `libraries/SITL/SIM_GPS.cpp:65-68` 注册 `NUMSATS` 成员。
- `libraries/SITL/SIM_GPS.cpp:490-506` 把该值写入生成的 GPS 数据 `d.num_sats`。

这也说明 PGFuzz 的历史输入文件不能原样视为当前 ArduPilot 的有效参数目录；静态分析与执行器都需要版本感知的参数身份迁移。

## 8. 为什么 PGFuzz 对 `InputC` 和 `InputE` 使用动态分析

`LLVM IR` 是 **Low Level Virtual Machine Intermediate Representation**，中文为“LLVM 中间表示”；PGFuzz 把飞控编译成这种统一指令形式。`def-use chain` 是“定义—使用链”，记录一个值在哪里产生、又在哪里被读取。`SVF` 是 **Static Value-Flow Analysis Framework**，中文为“静态值流分析框架”；工件使用它和 Andersen 指针分析生成值流图。

PGFuzz 的静态分析实现范围很窄：

1. `trace_target_list.txt` 填的是参数对应的 LLVM 变量名。
2. `SVF-data-flow.cpp:330-360` 只在 `store` 指令的目标名字与列表匹配时启动正向遍历。
3. `traverseOnVFG()` 沿值流后继收集使用点，主要打印到达的 `store` 目标名字。
4. 它不从 `msg.msgid`、`packet.command`、`packet.param1..7` 或 RC 通道字段建立语义根。
5. 它不把 `switch` 分支、命令接受条件、模式状态机、调度时间、连续事件和仿真反馈闭环编码进依赖结果。

论文选择动态分析还有两个直接原因：

- 一个命令在不同模式下可能被解释或忽略。源码中的 `Copter::set_mode()`、起飞处理器和 RC 覆盖超时都证实了这种状态依赖。
- 环境因素往往通过物理闭环间接改变很多状态。例如风可能同时改变位置、速度、姿态、控制输出和估计量。普通的程序值流不能自动回答“实际运行时哪些可观测状态显著变化”。

工件的 `profiling_cmd_env.py` 因此在每个飞行模式下：

1. 先采集无输入基线。
2. 单独执行一个命令或环境输入。
3. 采集 34 个运行状态。
4. 比较标准差，并把发生变化的状态归入输入—状态映射。

工件默认 `Measuring_duration=1`、`Measuring_iteration=3`，即每次测量 1 秒、重复 3 次；论文描述的实验设置更长。工件 README 也明确允许提高二者以改善稳定性。因此公开工件结果应视为经验相关映射，不是静态因果证明。

## 9. “静态分析不了”的准确边界

| 判断 | 结论 | 依据 |
|---|---|---|
| 命令是否传入 ArduPilot 源码 | 是 | `COMMAND_LONG`、`SET_MODE`、`RC_CHANNELS_OVERRIDE` 均有明确接收和处理函数 |
| 环境参数是否传入 ArduPilot 源码 | 是 | PGFuzz 发送 `PARAM_SET`，当前 `SIM_*` 参数由 `AP_Param` 查找并更新 |
| PGFuzz 的公开静态工具能否直接分析它们 | 通常不能 | 工具根目标是参数变量名，未建模消息类型、命令编号和运行状态 |
| 更强的静态分析能否分析命令 | 可以分析一部分 | 可以从消息字段建立污点/值流/控制依赖并追踪处理器，但必须保留状态前置条件和接受结果 |
| 更强的静态分析能否分析环境因素 | 可以分析软件链的一部分 | 可以追踪 `SIM_*` 到仿真变量和传感器生成；跨时间物理效果仍需模型或动态确认 |
| 动态分析是否自动等于因果证明 | 否 | 单输入扰动和状态差异只能形成经验相关证据，还受模式、噪声、测量时长和未控状态影响 |

对 RIFT 的直接启示是：统一入口不应只叫“变量”，而应定义为带通道和事件语义的外部源：

```text
PARAM_SET(param_id, param_value)
COMMAND_LONG(command, param1..param7)
SET_MODE(custom_mode)
RC_CHANNELS_OVERRIDE(channel, pwm, timestamp)
SIM_* parameter -> physics/sensor feedback
```

然后把结果分成：

- 源码内可证明的值依赖；
- 只通过分支和状态机成立的控制依赖；
- 需要先满足模式、解锁、设备启用等条件的事件依赖；
- 经仿真物理和时间演化才能确认的模型化依赖；
- 动态实验已经确认或仍未确认的影响。

这比把 `InputC`/`InputE` 统一标成“静态分析不了”更精确，也正是从 MITL 命题反推可模糊测试影响源时必须补齐的部分。
