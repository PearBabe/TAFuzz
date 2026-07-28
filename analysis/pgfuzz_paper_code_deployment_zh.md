# PGFuzz 论文与源码工程分析

日期：2026-07-16

本报告基于本地论文 PDF `baseline/pgfuzz/Kim 等 - 2021 - PGFUZZ Policy-guided fuzzing for robotic vehicles.pdf`、本地源码仓库 `baseline/pgfuzz`，以及当前工作机环境检查结果。目标是帮助后续在 PGFuzz 背景下开展方法实验，而不是系统学习机器人或飞控。

## 1. 一句话结论

PGFuzz 的核心不是“懂飞控控制理论后再测”，而是把飞控文档里的功能/安全策略写成 MTL/LTL 风格性质，再把性质拆成可变输入、可观测状态和距离函数，用 ArduPilot/PX4/Paparazzi 的 SITL 仿真反复执行输入序列，观察策略是否被违反。

对你的实验，最小可行路径应从 ArduPilot SITL + MAVLink + 一个简单 policy 开始，不建议一开始复现 PX4/Paparazzi 全量论文实验。

## 2. 论文方法拆解

PGFuzz 分三步：

1. Pre-processing：从文档/代码注释提取 policy，并表达成 MTL 公式；然后缩小输入空间。
2. Policy-guided fuzzing：在缩小后的输入空间中变异参数、命令、环境因素；用 propositional distance 引导下一步输入，用 global distance 判断 violation。
3. Bug post-processing：对导致 violation 的输入序列做最小化，留下真正必要的输入和值。

论文中的输入分三类：

- `InputP`：configuration parameters，例如 `RTL_ALT`、`CHUTE_ALT_MIN`、`COM_POS_FS_DELAY`。
- `InputC`：user commands，例如切换飞行模式、起飞、返航、降落、释放 parachute、RC 通道输入。
- `InputE`：environment factors，主要是 SITL 提供的 `SIM_*` 参数，例如风、GPS/气压计/IMU 噪声或故障。

论文中的可观测状态不需要你从飞控源码里全部理解。实验开始只需要理解这些状态类型：

- 位置：经纬度、高度。
- 姿态：roll、pitch、yaw 及角速度。
- 操作状态：飞行模式、油门、降落伞状态、是否 armed。
- RC 输入：RC1 到 RC4。
- 系统状态：heartbeat、是否落地/失控、mission、pre-arm。
- 传感器状态：GPS、barometer、accelerometer、gyroscope、magnetometer。

## 3. 论文实验参数

论文声称实验对象如下：

- ArduPilot 4.0.3，quadrotor，APM SITL/Gazebo。
- PX4 1.9，quadrotor，JSBSim/Gazebo。
- Paparazzi 5.16，quadrotor，NPS/Gazebo。
- Ubuntu 18.04 64-bit，i7-7700，32 GB RAM。
- 总运行 48 小时。
- 提取 56 条策略：ArduPilot 30、PX4 21、Paparazzi 5。

源码仓库与论文并不完全一致：

- 本地 `baseline/pgfuzz` 是 Git 仓库，远端为 `https://github.com/purseclab/PGFuzz.git`，当前 commit 为 `7eaebf2 Update README.md`。
- 本地只有 ArduPilot 和 PX4 脚本，没有 Paparazzi 实现目录。
- ArduPilot policy 目录为 28 个，PX4 policy 目录为 21 个。
- 论文提到的 predicate generator、完整 SVF 静态分析实现、Paparazzi 的 PPRZLINK 实现不在这个仓库里；README 只给外部仓库/工具安装说明。

## 4. 源码结构

关键目录：

- `baseline/pgfuzz/README.md`：总说明、依赖、源码到 bitcode、SVF-data-flow 安装。
- `baseline/pgfuzz/ArduPilot/README.md`：ArduPilot 运行说明。
- `baseline/pgfuzz/PX4/README.md`：PX4 运行说明。
- `baseline/pgfuzz/ArduPilot/fuzzing.py`：ArduPilot 主 fuzzing loop，约 2657 行。
- `baseline/pgfuzz/PX4/fuzzing.py`：PX4 主 fuzzing loop，约 2358 行。
- `baseline/pgfuzz/*/pgfuzz.py`：启动两个终端，一个跑模拟器，一个跑 fuzzing。
- `baseline/pgfuzz/*/open_simulator.py`：启动 SITL，并在 `shared_variables.txt` 要求 reboot 时重启。
- `baseline/pgfuzz/*/read_inputs.py`：读取 policy 下的 `parameters.txt`、`cmds.txt`、`envs.txt`。
- `baseline/pgfuzz/*/policies/<policy>/`：每个 policy 的输入空间。
- `baseline/pgfuzz/ArduPilot/Dynamic analysis/`：命令/环境因素到状态的动态映射脚本与结果。
- `baseline/pgfuzz/*/xml_parse/`：从飞控参数 XML 中提取参数范围。

每个 policy 目录固定有四个文件：

- `parameters.txt`：可变飞控参数，格式大致为 `name,reboot,default,min,max,unit`。
- `cmds.txt`：可发 MAVLink command 或 RC/flight mode。
- `envs.txt`：可变仿真环境参数。
- `preconditions.txt`：运行该 policy 前需要设置的参数；当前很多是空文件。

## 5. 运行逻辑

ArduPilot 的入口是：

```bash
cd baseline/pgfuzz/ArduPilot
python2 pgfuzz.py
```

`pgfuzz.py` 做两件事：

1. 用 `gnome-terminal -- python2 .../open_simulator.py` 启动 ArduPilot SITL。
2. 等 90 秒后用另一个终端启动 `fuzzing.py`。

`fuzzing.py` 的大致流程：

1. 读取 `Current_policy` 对应的 `parameters/cmds/envs`。
2. 连接 `udp:127.0.0.1:14551` 的 MAVLink。
3. 等待 heartbeat，读取 home altitude / home position。
4. 切到 `GUIDED`，arm，takeoff 到 100m。
5. 启动读状态线程、油门保持线程、liveness 线程。
6. 应用 `preconditions.txt`。
7. 每轮：
   - 计算距离；
   - 随机选 input type：参数、命令、环境因素；
   - 随机或复用 guidance log 中的值；
   - 等 4 秒；
   - 再算距离；
   - 如果 global distance 负值，写入 `policy_violations/<n>.txt`。

PX4 类似，但 `PX4/fuzzing.py` 的启动逻辑大量写在文件顶层，不是 `main()`；导入该文件会直接连接 MAVLink 并执行 mission/arming 逻辑。二次开发前需要特别小心。

## 6. 需要学习的最小知识

### 6.1 先学会 SITL 是什么

SITL 是 Software-in-the-Loop。它不是实机飞控板，而是在电脑上跑飞控程序和简化物理仿真。你只需要知道：

- ArduPilot/PX4 作为被测程序运行。
- PGFuzz 通过 MAVLink 给它发命令/改参数。
- SITL 会产生高度、姿态、GPS、heartbeat 等状态。
- 测试结论首先是仿真结论，必要时再考虑实机复现。

### 6.2 学会 MAVLink 的基本概念

不需要完整读协议，只要会这些：

- heartbeat：判断飞控是否活着、当前模式/状态。
- `PARAM_SET` / `PARAM_VALUE`：读写配置参数。
- `COMMAND_LONG`：发送起飞、降落、返航、降落伞等命令。
- `SET_MODE`：切换飞行模式。
- `RC_CHANNELS_OVERRIDE`：模拟摇杆通道。
- 常见 telemetry：`VFR_HUD`、`ATTITUDE`、`GLOBAL_POSITION_INT`、`NAV_CONTROLLER_OUTPUT`、`STATUSTEXT`、`GPS_RAW_INT`。

### 6.3 学会几个飞控词

够用级别如下：

- arm/disarm：电机解锁/锁定。
- takeoff/land/RTL：起飞、降落、返航。
- mode：飞行模式，如 `GUIDED`、`ALT_HOLD`、`LOITER`、`RTL`、`FLIP`、`ACRO`。
- roll/pitch/yaw：横滚、俯仰、偏航。
- altitude / vertical speed：高度/垂直速度。
- failsafe：某类传感器/遥控/GPS 异常时进入的应急行为。
- parameter：飞控配置项，有默认值、范围、单位，有些需要 reboot。

### 6.4 学会 policy 到测试的映射

对每条 policy，你要能写清楚：

- precondition：怎么让系统进入测试状态。
- controllable input：可以变异哪些参数/命令/环境因素。
- observable state：用哪些 MAVLink 消息或日志判断状态。
- oracle：什么情况算违反。
- distance：每个原子条件离违反有多近。
- replay/minimize：违反后如何重放和删减输入序列。

这是你做方法实验最关键的抽象，飞控知识只是支撑这个映射。

### 6.5 学会 MTL 的够用子集

只需要掌握：

- `[]` / always：一直应该满足。
- `<>[0,k]` / eventually within k：k 秒内必须发生。
- implication：如果 A 发生，那么 B 应该发生。
- conjunction/disjunction/negation：与、或、非。
- bounded future：PGFuzz 运行时只能在线检查有界未来，不适合无界未来公式。

论文使用的模板主要是：

- T1：`termi -> eventually[0,k] termj`。
- T2：如果 `termi` 为真，则若干条件必须为真/为假。
- T3：如果一组条件为真，则另一个条件也必须为真。

## 7. 当前工作机不能直接跑的原因

当前工作机检查结果：

- 系统：WSL2 Ubuntu 22.04.5。
- 缺 `python2`。
- 缺 `gnome-terminal`。
- 缺 `sim_vehicle.py` / MAVProxy。
- 本地 `baseline/pgfuzz/ArduPilot/venv/bin/python2.7` 能启动，但缺 `pymavlink`、`psutil`、`lxml`，且有 `PYTHONHOME`/stdlib 路径警告，不能作为可靠运行环境。
- 本地 `baseline/ardupilot` 是一个独立仓库，当前在 `master` commit `e7805549c5`，不是论文 ArduPilot 4.0.3，也不是 README 中建议 checkout 的 PGFuzz 测试版本。
- 本地没有 `baseline/px4`。

结论：不要直接在当前 WSL2 里跑原始 PGFuzz。先准备隔离 VM 或容器/桌面 Linux 环境。

## 8. 推荐部署路线

### 路线 A：最稳，Ubuntu 18.04 VM

这是最接近论文和 README 的路线，适合先跑通 baseline。

1. 准备 Ubuntu 18.04 64-bit VM，建议 4 CPU、16 GB RAM、80 GB 磁盘，带图形桌面。
2. 安装基础包：

```bash
sudo apt update
sudo apt install -y git curl gcc g++ make cmake python2 python-dev python-pip \
  python-numpy python-lxml python-psutil gnome-terminal xterm
```

3. 克隆 PGFuzz：

```bash
mkdir -p ~/PGFuzz
cd ~/PGFuzz
git clone https://github.com/purseclab/PGFuzz.git PGFuzz
```

4. 安装 pymavlink。README 建议从 ArduPilot/mavlink 源码装：

```bash
cd ~/PGFuzz
git clone https://github.com/ArduPilot/mavlink.git
cd mavlink
git submodule update --init --recursive
cd pymavlink
sudo MDEF="$(pwd)/../message_definitions" python2 -m pip install . -v
```

5. 安装 ArduPilot 依赖，然后克隆被测 ArduPilot：

```bash
cd ~/PGFuzz
git clone https://github.com/ArduPilot/ardupilot.git ardupilot_pgfuzz
cd ardupilot_pgfuzz
git checkout ea559a56aa2ce9ede932e22e5ea28eb1df07781c
git submodule update --init --recursive
```

6. 按 ArduPilot 官方脚本安装依赖：

```bash
cd ~/PGFuzz/ardupilot_pgfuzz
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile
```

7. 先单独验证 ArduPilot SITL：

```bash
cd ~/PGFuzz/ardupilot_pgfuzz
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map -w
```

看到 MAVProxy console、地图窗口、heartbeat/状态输出后，再进行 PGFuzz。

8. 设置环境变量：

```bash
export PGFUZZ_HOME=$HOME/PGFuzz/PGFuzz/
export ARDUPILOT_HOME=$HOME/PGFuzz/ardupilot_pgfuzz/
```

9. 首次运行前创建输出目录，避免 `store_mutated_inputs()` 写文件失败：

```bash
mkdir -p "$PGFUZZ_HOME/ArduPilot/policy_violations"
touch "$PGFUZZ_HOME/ArduPilot/shared_variables.txt"
touch "$PGFUZZ_HOME/ArduPilot/restart.txt"
```

10. 运行 ArduPilot PGFuzz：

```bash
cd "$PGFUZZ_HOME/ArduPilot"
python2 pgfuzz.py
```

### 路线 B：Ubuntu 20.04/22.04 上做现代化适配

这条路线适合你已经能跑实验后，再为了自动化/CI 改造。需要处理：

- Python 2 依赖迁移到 Python 3，或用 pyenv/conda 固定 Python 2。
- 去掉 `gnome-terminal`，改成一个 Python supervisor 或 tmux 脚本。
- 把 `fuzzing.py` 拆成可导入库和 CLI。
- 明确每次实验的随机种子、policy、时间预算、输出目录。
- 把 `policy_violations`、`mutated_log.txt`、`guidance_log.txt` 改为 run-specific 目录。
- 将 simulator 启动、MAVLink 端口、等待 heartbeat、重启逻辑参数化。

不建议在还没跑通 baseline 前走这条路。

### 路线 C：只复用思想，不复现飞控

如果你的新方法核心是“规范/时间逻辑 oracle + fuzzing guidance”，可以先把 PGFuzz 的 policy/input/distance 抽象迁移到一个 host-executable 协议 benchmark，例如 CoAP/SIP/SOME-IP-SD。这样能避开飞控环境成本。但如果论文背景必须是 PGFuzz/robotic vehicle，则仍建议至少跑通一个 ArduPilot SITL policy 作为 grounding。

## 9. 建议先跑哪条 policy

不建议从 `A.FLIP1` 开始，虽然源码默认是它。它涉及姿态、飞行模式、油门、高度，且可能需要更稳定的仿真调参。

更适合作为第一条 smoke test 的候选：

- `A.CHUTE`：论文 motivating example，语义清楚，涉及 `MAV_CMD_DO_PARACHUTE`、mode、altitude、armed、`CHUTE_ALT_MIN`。
- `A.RTL1`：涉及高度和 `RTL_ALT`，动作路径比较直观。
- `A.ALT_HOLD2`：油门中位保持高度，状态容易观察，但噪声处理会影响判断。

首轮建议：

1. 先只跑 `A.CHUTE`。
2. 修改 `ArduPilot/fuzzing.py` 中：

```python
Current_policy = "A.CHUTE"
Current_policy_P_length = 5
```

3. 确认 `ArduPilot/policies/A.CHUTE/preconditions.txt` 中包含 parachute 相关仿真配置；若为空，参考动态分析 README 的示例：

```text
CHUTE_ENABLED 1
CHUTE_TYPE 10
SERVO9_FUNCTION 27
SIM_PARA_ENABLE 1
SIM_PARA_PIN 9
```

4. 每次 run 只保留一个清晰输出目录，记录：

- policy 名称；
- ArduPilot commit；
- PGFuzz commit；
- OS/VM 配置；
- random seed；
- 起止时间；
- `mutated_log.txt`；
- `guidance_log.txt`；
- `policy_violations/*.txt`；
- MAVProxy/SITL 控制台日志；
- 是否能重放最小输入序列。

## 10. 你做方法实验时最该注意的坑

1. 论文的 MTL 到距离代码，在公开仓库里并不是完整自动生成流程。源码里大量 policy 距离是手写在 `calculate_distance()` 中的。
2. `Current_policy` 只控制 guidance 的目标 policy，但 `calculate_distance()` 会计算很多 policy；任意 `print_distance()` 的 global distance 为负都会触发 violation 存储。统计时要区分“目标 policy violation”和“旁路 policy violation”。
3. 很多 `preconditions.txt` 为空，不代表该 policy 不需要前置条件；可能是 artifact 不完整或依赖默认 SITL 设置。
4. `policy_violations/` 目录不存在时，第一次 violation 可能因为写文件失败中断。
5. 论文说有 post-processing 最小化，但本地主流程主要是存储输入日志；完整最小化实现不明显，需要单独补。
6. 原始脚本强依赖 GUI 终端和固定等待时间，例如 ArduPilot 等 90 秒、PX4 等 50 秒，稳定性不适合自动化实验。
7. PX4 版本老，README 使用 `make px4_sitl_default jmavsim`；现代 PX4/Java/jMAVSim 依赖会更难装，先不要碰。
8. 论文中有 Paparazzi 结果，但本地仓库没有 Paparazzi 代码，不能直接复现三系统完整实验。
9. SITL 的 timing 和真实硬件不同。你的结论应表述为仿真环境下的可复现行为，除非后续有实机复核。
10. 对你的 TAFuzz 方向，最重要的不是飞控名词，而是把 policy 拆成可控事件、可观测 AP、时间窗口、状态后果和可重放输入序列。

## 11. 最小学习顺序

按这个顺序学，够做测试即可：

1. ArduPilot SITL：能启动 `sim_vehicle.py`，知道 console/map 是什么。
2. MAVLink via pymavlink：会连 UDP 端口、等 heartbeat、收 `VFR_HUD/ATTITUDE/GLOBAL_POSITION_INT`、发 command、改 parameter。
3. ArduPilot flight modes：只看 `GUIDED`、`ALT_HOLD`、`LOITER`、`RTL`、`LAND`、`ACRO`、`FLIP`。
4. Parameters：知道参数名、默认值、范围、单位、是否 reboot required。
5. PGFuzz policy format：读懂 `parameters.txt/cmds.txt/envs.txt/preconditions.txt`。
6. MTL 模板：T1/T2/T3 和 bounded future。
7. Distance oracle：看懂 `A.CHUTE` 的 P1-P5 和 global distance。
8. 实验记录：run id、seed、commit、policy、输入序列、violation、replay/minimize。

## 12. 面向你后续方法的实验建议

先不要试图复现论文 48 小时和 156 bugs。建议分三阶段：

### 阶段 1：baseline smoke

目标：证明环境能跑、能连 MAVLink、能记录 violation。

- 只跑 ArduPilot。
- 只跑一个 policy，例如 `A.CHUTE`。
- 运行 10 到 30 分钟。
- 手动检查日志和 MAVLink 状态。

### 阶段 2：受控复现实验

目标：得到可重放、可最小化的 policy violation。

- 固定 random seed。
- 每次 run 清空输出目录。
- 将 simulator 日志、PGFuzz 日志、输入序列保存到同一目录。
- 写一个 replay 脚本按 `mutated_log.txt` 重放。
- 写一个简单 reducer 删除输入项，验证 violation 是否还出现。

### 阶段 3：接入你的方法

目标：把 TAFuzz 的规范/时间逻辑 oracle 或输入选择策略与 PGFuzz baseline 比较。

可比较维度：

- 同一 policy 下 violation 首次发现时间。
- 同一预算下找到的 unique violation 数。
- 输入序列长度和最小化后长度。
- oracle 误报/不可重放比例。
- 可控输入覆盖：参数/命令/环境因素组合。
- 状态/AP 覆盖：高度、模式、姿态、failsafe、heartbeat 等。

## 13. 立即下一步

建议下一步只做部署，不做方法改造：

1. 新建 Ubuntu 18.04 VM。
2. 克隆 PGFuzz 和 ArduPilot 指定版本。
3. 单独跑通 ArduPilot SITL。
4. 跑通 `python2` + `pymavlink` 最小连接脚本。
5. 创建 `policy_violations/`，把 `Current_policy` 改为 `A.CHUTE`。
6. 运行 `python2 pgfuzz.py`，观察是否能产生 `mutated_log.txt`、`guidance_log.txt`。
7. 如果发现 violation，先做手动 replay，再考虑接入新方法。

