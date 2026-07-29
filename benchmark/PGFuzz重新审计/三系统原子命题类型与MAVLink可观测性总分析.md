# 三系统原子命题类型与 MAVLink/PPRZLink 可观测性总分析

## 一、先解释本文件中的英文和缩写

- `AP` 是 Atomic Proposition，中文为“原子命题”，即公式中可单独判真假的最小条件。
- `MAVLink` 是 Micro Air Vehicle Link，中文为“微型飞行器通信协议”，ArduPilot 与 PX4 默认大量使用；`PPRZLink` 是 Paparazzi 的原生通信协议，冻结 Bebop2 配置默认使用它。
- `SITL` 是 Software In The Loop，中文为“软件在环仿真”；`NPS` 是 Networked Physics Simulation，中文为“网络物理仿真”，是 Paparazzi 的仿真目标。
- `RC` 是 Radio Control，中文为“遥控输入”；`PWM` 是 Pulse Width Modulation，中文为“脉宽调制”，论文常把 1500 微秒当作摇杆中值，但该数值不能跨飞控直接继承。
- `ENU` 是 East-North-Up，中文为“东—北—天”坐标；`NED` 是 North-East-Down，中文为“北—东—地”坐标。高度、垂直速度和前后样本比较必须先统一坐标系。
- `S1` 到 `S6` 是 PGFuzz 的状态分类：`S1` 位置，`S2` 姿态，`S3` 飞行运行，`S4` 遥控输入，`S5` 系统，`S6` 传感器。`InputP` 是配置参数输入，`InputC` 是用户命令输入，`InputE` 是环境因素输入。状态类别与输入类别是两套分类，不能混用。
- 本文件的中文可观测状态含义：
  - “可直接观测”：一条已启用消息的一个字段或明确枚举即可判真；
  - “可计算得到”：必须组合字段、做单位/坐标转换或保存上一有效样本；
  - “条件可观测”：协议与源码支持，但还依赖消息流、模块、参数、输入记录或有效性条件；
  - “需要插桩”：必须在飞控内部增加事件/状态导出才能严格判真；
  - “无法确认”：当前证据不足，不能猜。

所有公式的实现符合性均为：**未评估**。可观测只表示“能否取得判定所需信息”，不表示飞控满足性质。

## 二、必须分开的四个证据层次

|层次|它实际证明什么|不能推出什么|
|---|---|---|
|协议定义|XML 方言中定义了消息编号、字段、单位和枚举|不能推出某飞控源码实现它|
|源码静态支持|冻结源码有发送、接收或参数处理路径|不能推出当前机型/配置启用|
|当前配置启用|机体与遥测配置选择了对应模块和消息流|不能推出本次运行一定产生条件性消息|
|本次仿真实际观察|抓取记录中出现了该消息和字段|只能证明该次运行可取得，不能证明性质满足|

ArduPilot/PX4 的运行证据来自 [`runtime_message_support_matrix.csv`](../extraction_runs/milestone6/runtime_message_support_matrix.csv)；Paparazzi 冻结配置入口明确选择 `telemetry/default_rotorcraft.xml`，见 [`conf_example.xml:2-10`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/conf/conf_example.xml#L2-L10)。

## 三、PGFuzz 原 56 条性质：全部原子命题的可观测性

### 3.1 数量总览

|系统|论文性质数|拆分原子命题数|可直接观测|可计算得到|条件可观测|需要插桩|无法确认|
|---|---:|---:|---:|---:|---:|---:|---:|
|ArduPilot|30|110|32|3|44|21|10|
|PX4|21|68|30|8|13|13|4|
|Paparazzi|5|16|4|11|1|0|0|
|合计|56|194|66|22|58|34|14|

ArduPilot/PX4 的 178 个拆分项可由当前结构化清单 [`atomic_proposition_bindings.csv`](../PGFuzz_MTL51/atomic_proposition_bindings.csv) 逐行复查；下面用中文状态重新汇总。Paparazzi 16 项由论文 5 条重新拆分，详细源码位置见 [Paparazzi 当前审计](Paparazzi/PGFuzz原性质_当前审计.md)。

### 3.2 ArduPilot 30 条逐公式总览

|性质|可直接观测的原子命题|可计算/条件可观测|需要插桩|无法确认|
|---|---|---|---|---|
|`A.RTL1`|`Mode_t=RTL`|`ALT_t<RTL_ALT`、`ALT_t-1<ALT_t`|—|—|
|`A.RTL2`|`Mode_t=RTL`|`ALT_t≥RTL_ALT`、`Pos_t≠home_position`、位置/高度前后比较|—|—|
|`A.RTL3`|`Mode_t=RTL`、`Mode_t=LAND`|高度与 HOME 位置关系|—|—|
|`A.RTL4`|`Mode_t=LAND`、`Disarm=on`|—|—|`ALT_t=GroundALT`|
|`A.FLIP1`|模式、横滚角|上一模式、油门通道、高度|—|—|
|`A.FLIP2`|模式、横滚角|—|`Roll_rate=400deg/s`、翻滚方向|—|
|`A.FLIP3`|—|—|`Mode_t=FLIP3`|`k` 时间内恢复原横滚/俯仰/偏航|
|`A.FLIPGeneral`|—|—|`FLIP1→FLIP3` 内部阶段|—|
|`A.ALT_HOLD1`|—|GPS 高度对照|高度源选择、气压计高度身份|—|
|`A.ALT_HOLD2`|`Mode_t=ALT_HOLD`|油门通道、前后高度|—|—|
|`A.CIRCLE1`|`Mode_t=CIRCLE`|`RC_pitch<1500`|半径及半径变化|—|
|`A.CIRCLE2`|`Mode_t=CIRCLE`|`RC_pitch>1500`|半径变化|—|
|`A.CIRCLE3`|`Mode_t=CIRCLE`|`RC_roll>1500`|方向、速度变化|—|
|`A.CIRCLE4`|`Mode_t=CIRCLE`|`RC_roll>1500`|方向、速度变化|—|
|`A.CIRCLE5`|`Mode_t=CIRCLE`|`RC_roll<1500`|方向、速度变化|—|
|`A.CIRCLE6`|`Mode_t=CIRCLE`|`RC_roll<1500`|方向、速度变化|—|
|`A.CIRCLE7`|`Mode_t=CIRCLE`|四个 RC 通道前后样本|—|—|
|`A.LAND1`|`Mode_t=LAND`|高度、垂直速度、`LAND_SPEED_HIGH` 参数|—|—|
|`A.LAND2`|`Mode_t=LAND`|高度、垂直速度、`LAND_SPEED` 参数|—|—|
|`A.AUTO1`|`Mode_t=AUTO`|四个 RC 通道前后样本|—|—|
|`A.BRAKE1`|`Mode_t=BRAKE`|—|—|经验时间 `k` 内位置停止|
|`A.DRIFT1`|`Mode_t=DRIFT`|—|—|`GPS_fail` 与 `FS_EKF_ACTION` 的严格事件关系|
|`A.LOITER1`|`Mode_t=LOITER`|位置、偏航、高度前后样本|—|—|
|`A.GUIDED1`|`Mode_t=GUIDED`|位置、偏航、高度前后样本|—|`Waypoint=empty`|
|`A.SPORT1`|`Mode_t=SPORT`|垂直速度与 `PILOT_SPEED_UP`|—|—|
|`A.RC.FS1`|模式、已解锁、锁定|油门与 `FS_THR_VALUE`|—|—|
|`A.RC.FS2`|—|油门与 `FS_THR_VALUE`|`RC_fail=on`|—|
|`A.CHUTE1`|已解锁、禁止模式|高度趋势与 `CHUTE_ALT_MIN`|`Parachute=on`|—|
|`A.GPS.FS1`|—|卫星数|—|旧 `GPS_fail`|
|`A.GPS.FS2`|—|气压计健康|当前高度源|旧 `GPS_fail`|

主要消息路径：模式/解锁用 `HEARTBEAT`（编号 0）；姿态用 `ATTITUDE`（30）；位置/高度/垂直速度用 `GLOBAL_POSITION_INT`（33）；遥控用 `RC_CHANNELS`（65）；参数用 `PARAM_VALUE`（22）；HOME 用 `HOME_POSITION`（242）；卫星数用 `GPS_RAW_INT`（24）。精确变量、函数和行号在 [ArduPilot 30 条当前审计](ArduPilot/PGFuzz原性质_当前审计.md) 每条明细中。

### 3.3 PX4 21 条逐公式总览

|性质|可直接观测的原子命题|可计算/条件可观测|需要插桩|无法确认|
|---|---|---|---|---|
|`PX.RTL1`|`Mode_t=RTL`、参数值|—|当前返回目标与高度趋势|—|
|`PX.RTL2`|模式、当前位置与 HOME|位置前后变化|当前返回目标与高度保持|—|
|`PX.RTL3`|RTL/LAND 模式、HOME 关系|—|当前返回目标高度|—|
|`PX.RTL4`|模式、`RTL_DESCEND_ALT`、`RTL_LAND_DELAY`|位置前后变化|高度保持|—|
|`PX.RTL5`|LAND 模式、锁定|—|—|`GroundALT` 数值身份|
|`PX.ORBIT1`|ORBIT 模式|RC 俯仰通道|当前半径及历史半径的严格内部值|—|
|`PX.ORBIT2`|ORBIT 模式|RC 俯仰通道|半径变化|—|
|`PX.ORBIT3`|ORBIT 模式、方向|RC 横滚通道|速度变化|—|
|`PX.ORBIT4`|ORBIT 模式、方向|RC 横滚通道|速度变化|—|
|`PX.ORBIT5`|ORBIT 模式|—|半径小于 100 米|—|
|`PX.ORBIT6`|ORBIT 模式|—|论文把速度和加速度单位混写的内部量|—|
|`PX.LAND1`|LAND 模式、垂直速度、`MPC_LAND_SPEED`|—|—|—|
|`PX.ALTITUDE1`|ALTITUDE 模式|油门通道、高度前后样本|—|—|
|`PX.POSITION1`|POSITION 模式|位置前后样本|—|—|
|`PX.HOLD1`|HOLD 模式|位置、偏航、高度前后样本|—|—|
|`PX.HOLD2`|HOLD 模式、`NAV_MIN_LTR_ALT` 参数|高度关系、目标高度|—|—|
|`PX.TAKEOFF1`|—|起飞命令记录、当前/目标高度、`MIS_TAKEOFF_ALT`|—|—|
|`PX.TAKEOFF2`|垂直速度、`MPC_TKO_SPEED`|起飞命令记录|—|—|
|`PX.GPS.FS1`|GPS 丢失|—|—|`GPS_fail` 精确事件及论文 `k`|
|`PX.GPS.FS2`|ALTITUDE 模式|RC 存在|—|`GPS_fail` 精确事件|
|`PX.GPS.FS3`|LAND 模式|RC 不存在|—|`GPS_fail` 精确事件|

PX4 的 ORBIT 半径消息 `ORBIT_EXECUTION_STATUS`（360）在协议中存在，但论文需要的若干控制器内部半径/速度语义不能自动等同该外部字段，所以保留“需要插桩”。精确 `uORB`（PX4 内部发布—订阅消息总线）字段和源码行见 [PX4 21 条当前审计](PX4/PGFuzz原性质_当前审计.md)。

### 3.4 Paparazzi 5 条逐公式总览

|性质|原子命题拆分|PGFuzz 类型|默认 PPRZLink|可选 MAVLink|
|---|---|---|---|---|
|`PP.Hover`|Hover 模式；位置保持；偏航保持|S3；S1；S2|三者均可由 `ROTORCRAFT_STATUS` 与 `ROTORCRAFT_FP` 计算|模式只能条件恢复；位置/偏航条件可计算|
|`PP.HoverZ`|垂直保持模式；垂直输入居中；高度保持|S3；S4；S1|模式直接、高度计算；遥控输入在冻结 dummy/datalink 配置下为条件可观测|需启用 `RC_CHANNELS` 流；高度可计算|
|`PP.HoverC`|水平+垂直悬停；位置；偏航；高度|S3；S1；S2；S1|同一 `ROTORCRAFT_STATUS/FP` 组合计算|目标值缺失，部分需要插桩|
|`PP.TAKEOFF1`|Takeoff 任务块；当前高度与 HOME+5 关系|InputC/S3；S1|`ROTORCRAFT_NAV_STATUS.cur_block` 与 `ROTORCRAFT_FP.up`，HOME 值来自任务快照|标准流没有当前块；需 missionlib 或插桩|
|`PP.HOME1`|HOME 模式；未着陆；高度变化；位置变化|S3；S3；S1；S1|模式/在地状态直接，位置高度保存历史后计算|启用可选模块后位置/在地状态可观测，HOME 模式映射需验证|

Paparazzi 默认三条关键消息：

|消息|编号|字段和含义|生成位置|冻结默认周期|
|---|---:|---|---|---:|
|`ROTORCRAFT_STATUS`|231|`ap_mode` 飞控模式、`ap_in_flight` 是否飞行、`ap_h_mode` 水平引导模式、`ap_v_mode` 垂直引导模式、`cpu_time` 启动秒数|[`autopilot_firmware.c:114-135`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/airborne/firmwares/rotorcraft/autopilot_firmware.c#L114-L135)|1.2 秒|
|`ROTORCRAFT_FP`|147|ENU 位置/速度、姿态、引导 carrot 目标和 `flight_time`；位置缩放 0.0039063 米，姿态缩放 0.0139882 度|[`autopilot_firmware.c:151-180`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/airborne/firmwares/rotorcraft/autopilot_firmware.c#L151-L180)|0.25 秒|
|`ROTORCRAFT_NAV_STATUS`|159|`block_time`、`stage_time`、HOME/航点距离、当前块/阶段和水平导航模式|[`nav_rotorcraft_base.c:281-289`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/airborne/modules/nav/nav_rotorcraft_base.c#L281-L289)|1.6 秒|

消息字段正式定义分别见 [`messages.xml:1360-1376`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/ext/pprzlink/message_definitions/v1.0/messages.xml#L1360-L1376)、[`1505-1513`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/ext/pprzlink/message_definitions/v1.0/messages.xml#L1505-L1513)、[`2244-2259`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/ext/pprzlink/message_definitions/v1.0/messages.xml#L2244-L2259)；冻结周期见 [`default_rotorcraft.xml:8-16`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/conf/telemetry/default_rotorcraft.xml#L8-L16)。

## 四、三系统新提取性质的观测结论

|系统/性质|关键原子命题|观测结论|
|---|---|---|
|ArduPilot `ARD-NEW-VIBE-001/002`|估计器异常、`high_vibes`|严格真值需要插桩；`STATUSTEXT` 只能条件提示|
|ArduPilot `ARD-NEW-TERRAIN-003`|地形缺失起点、任务需地形、RTL/锁定动作|起点需要插桩；动作可由 `HEARTBEAT` 直接观察|
|ArduPilot `ARD-NEW-RUDDER-004`|有效左舵+最小油门、锁定|RC 条件可观测，锁定直接观测；精确接收时刻需插桩|
|ArduPilot `ARD-NEW-CHUTE-005`|自动失控起点、释放事件|需要插桩；文本仅作条件证据|
|ArduPilot `ARD-NEW-CRASH-006`|坠毁复合条件、锁定|复合条件需要插桩；锁定直接观测|
|ArduPilot `ARD-NEW-EKF-007`|两项方差越界、EKF 保护状态|需要插桩；标准估计器状态不等价完整内部判据|
|ArduPilot `ARD-NEW-GCS-008`|飞控接收最后一条指定 GCS 心跳、超时动作|输入由测试端控制，但飞控接收时刻需要插桩；模式/锁定动作可直接观察|
|ArduPilot `ARD-NEW-RC-009`|最后有效 RC 输入、丢失、动作|RC 流条件可观测；内部丢失事件需要插桩；动作直接/条件可见|
|ArduPilot `ARD-NEW-BATT-010`|指定电池电压、实例化低压事件|原始电压可计算；压降补偿电压与带实例事件需要插桩|
|ArduPilot `ARD-NEW-RTL-011`|RTL 等待子状态、最终下降开始|两者均为内部阶段，需要插桩|
|ArduPilot `ARD-NEW-GUID-012`|最后有效外部目标接收、超时响应开始|测试端输入记录为条件证据；飞控接受与控制响应起点需要插桩|
|ArduPilot `ARD-NEW-LOITER-013`|模式、摇杆释放、停止并保持位置|模式直接、摇杆条件、停止/保持由速度位置计算|
|ArduPilot `ARD-NEW-GUIDWAIT-014`|目标到达、新目标、目标悬停|输入可记录；内部目标到达需要插桩；悬停可计算但需有来源容差|
|ArduPilot `ARD-NEW-AUTO-015`|飞手输入是否影响任务目标|必须做配对输入试验或内部插桩，单条消息无法证明“不影响”|
|PX4 `PX4-MC-RCLOSS-001`|选定人工源最后更新时间、适用条件、丢失状态|输入流条件可见；精确内部事件/例外组合需插桩或 uORB 导出|
|PX4 `PX4-MC-GCSLOSS-002`|GCS 心跳接收、例外、`gcs_connection_lost`|心跳由测试端控制；接收时刻需插桩；结果可由事件/状态条件观察|
|PX4 `PX4-MC-OFFBOARD-003`|有效外部控制存活、丢失动作|消息输入可记录；有效接受与动作起点需要内部事件|
|PX4 `PX4-MC-AUTODISARM-004`|着陆开始、已解锁/锁定|`EXTENDED_SYS_STATE.landed_state` 与 `HEARTBEAT.base_mode` 可直接组合|
|PX4 `PX4-MC-FLIGHTTIME-005`|起飞时刻、警告、返航|起飞/警告事件条件可见，返航模式直接；完整关联需事件序列|
|PX4 `PX4-MC-RTLLOITER-006`|进入 RTL 目的地等待、开始 LAND|内部 RTL 子状态需要插桩，LAND 模式直接可见|
|Paparazzi `PAP-NEW-GEOINIT-001`|Geo init 块/块时间、设置参考事件|块与时间直接；设置事件需要插桩|
|Paparazzi `PAP-NEW-P2WAIT-002`|p2 阶段、阶段时间、目标|默认 PPRZLink 可直接/计算得到|
|Paparazzi `PAP-NEW-YAWSTEP-003`|阶段时间、循环 `i`、目标航向|时间和目标可见；需生成块表关联 `i`|
|Paparazzi `PAP-NEW-TAKEOFF-004`|块、高度、爬升目标、Standby|块/高度可见；爬升目标需要插桩|
|Paparazzi `PAP-NEW-STANDBY-005`|块、STDBY 目标|默认 PPRZLink 可计算得到|
|Paparazzi `PAP-NEW-GEOFENCE-006`|HOME 距离、NAV/HOME 模式|默认 PPRZLink 可直接观测|
|Paparazzi `PAP-NEW-HOME-007`|HOME 模式、水平/高度目标|模式直接，目标由 carrot 与任务航点计算；严格内部目标可插桩|

## 五、MAVLink 消息、命令参数、飞控配置参数不是同一对象

|对象|例子|用途|本任务中的正确处理|
|---|---|---|---|
|消息字段|`GLOBAL_POSITION_INT.relative_alt`|飞控发送的一次状态观测|必须保留消息编号、单位、时间字段和有效性|
|`MAV_CMD` 的 `param1`–`param7`|`MAV_CMD_NAV_TAKEOFF` 的命令参数|某一条命令携带的七个位置参数|只属于该命令实例，不是长期配置参数|
|飞控配置参数|`RTL_ALT`、`COM_RC_LOSS_T`|长期配置，可经参数协议读取/写入|每次运行读取实际值；源码默认不等于当前值|

常用 MAVLink 观测面：

|消息|编号|关键字段|方向|单位/缩放|能支持的命题|
|---|---:|---|---|---|---|
|`HEARTBEAT`|0|`base_mode`,`custom_mode`,`system_status`|飞控→地面；也可地面→飞控作心跳|枚举/位图|模式、解锁；不能给事件时间|
|`SYSTEM_TIME`|2|`time_boot_ms`,`time_unix_usec`|飞控→地面|毫秒；微秒|启动时间与 Unix 时间对照|
|`PARAM_VALUE`|22|`param_id`,`param_value`,`param_type`|飞控→地面|由参数元数据解释|运行参数值；浮点线值需按类型解码|
|`GPS_RAW_INT`|24|`fix_type`,`satellites_visible`,`alt`,`time_usec`|飞控→地面|高度毫米；时间微秒|GPS 状态、卫星数、高度|
|`ATTITUDE`|30|`roll`,`pitch`,`yaw`,`rollspeed` 等|飞控→地面|弧度、弧度/秒|姿态和体轴角速度|
|`LOCAL_POSITION_NED`|32|`x,y,z,vx,vy,vz,time_boot_ms`|飞控→地面|米、米/秒、毫秒|局部位置/速度；z 向下为正|
|`GLOBAL_POSITION_INT`|33|`lat,lon,alt,relative_alt,vx,vy,vz,hdg,time_boot_ms`|飞控→地面|经纬 1e-7 度；高度毫米；速度厘米/秒|全球位置、高度、速度、航向|
|`RC_CHANNELS`|65|`chanN_raw`,`rssi`,`time_boot_ms`|飞控→地面|PWM 微秒/信号值|遥控通道；必须先读取通道映射|
|`COMMAND_LONG/COMMAND_INT`|76/75|`command`,`param1`–`param7` 或 `x,y,z`|地面→飞控|按具体命令定义|起飞、模式、轨道命令输入记录|
|`COMMAND_ACK`|77|`command`,`result`|飞控→地面|枚举|命令是否被接受；不等于动作完成|
|`BATTERY_STATUS`|147|`id`,`voltages`,`current_battery`,`battery_remaining`|飞控→地面|毫伏、厘安、百分比|带实例电池观测|
|`ESTIMATOR_STATUS`|230|`flags` 与方差比|飞控→地面|比值/位图|估计器外部摘要；不自动等同内部复合判据|
|`HOME_POSITION`|242|经纬高、局部 `x,y,z`,`time_usec`|飞控→地面|协议规定单位|HOME 目标；需与当前位置同一参考|
|`EXTENDED_SYS_STATE`|245|`landed_state`|飞控→地面|枚举|落地/空中状态|
|`ORBIT_EXECUTION_STATUS`|360|`radius`,`x`,`y`,`z`,`time_usec`|飞控→地面|米等|PX4 Orbit 状态；当前源码支持与配置仍需逐层核验|
|`EVENT`|410|事件编号、序列、参数|PX4→地面|事件协议|PX4 内部事件的条件观测和关联|

## 六、时间字段到底表示哪里的时间

|时间载体|含义|适合什么|主要风险|
|---|---|---|---|
|`time_boot_ms`|消息发送方自启动后的毫秒数|同一飞控运行内排序和差值|32 位约 49.7 天回绕；不是消息接收时刻|
|`time_unix_usec`|Unix 纪元微秒|跨系统日历时间|依赖时钟同步，启动早期可能无效|
|模糊 `time_usec`|XML 允许 Unix 时间或启动时间，接收端按数值量级判断|GPS/部分消息排序|必须先判定时间域，不能混用|
|Paparazzi `flight_time/cpu_time`|飞控启动/飞行的 `uint16` 秒计数|粗粒度运行时间|约 65,535 秒回绕，分辨率只有 1 秒|
|Paparazzi `block_time/stage_time`|当前任务块/阶段内部整秒计数|冻结任务的 10 秒/3 秒条件|切块/切阶段重置；1.6 秒消息周期会漏掉精确边沿|
|地面端单调到达时间|记录进程本机的单调时钟|衡量观测到达顺序和链路延迟|包含传输、排队和解码延迟，不能替代机载事件时刻|

任何 `t-1` 都只是上一条通过有效性与新鲜度检查的观测。消息丢失、乱序、时间回绕或坐标原点变化时，应暂停比较或判“无法确认”，不能硬算。

## 七、实际支持与仿真验证边界

- ArduPilot 运行矩阵覆盖 ArduCopter、ArduPlane、Rover，每个方言 352 个消息编号，共 1,056 个“车型—消息”行：61 行默认流观察到，76 行请求窗口观察到，114 行命令接受但未见匹配帧，805 行请求失败；实际出现 146 个“车型—消息”组合。数字按车型计数，不是 146 个不同消息名。
- PX4 v1.17 多旋翼矩阵有 251 个消息编号：33 个默认流观察到、21 个请求窗口观察到、189 个请求被拒绝、8 个未进入请求扫描且未观察；共实际出现 54 个消息编号。
- 这些运行抓取证明消息可取得，不证明任何 MTL 性质满足。请求窗口中出现本来就在周期发送的消息时，不能声称请求导致了它。
- Paparazzi 的默认 PPRZLink 消息定义、生成函数和遥测周期已经静态闭合；可选 MAVLink 注册函数见 [`mavlink.c:116-140`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/sw/airborne/modules/datalink/mavlink.c#L116-L140)，可选周期表见 [`default_rotorcraft_mavlink.xml:5-36`](https://github.com/paparazzi/paparazzi/blob/b51490c88bf972b764229d5f034957a41b6ce57c/conf/telemetry/default_rotorcraft_mavlink.xml#L5-L36)。冻结 Bebop2 没有启用该模块/遥测表。
- 本机 Paparazzi NPS 构建执行 `make AIRCRAFT=Bebop2 nps.compile` 时，生成器缺失；继续执行 `make generators` 明确失败于 `ocamlbuild: No such file or directory`。因此 Paparazzi 本轮没有运行抓取，状态只能是“静态支持、运行未验证”。失败没有修改 Paparazzi 工作树。

## 八、审核时最容易犯的四个错误

1. 看到 MAVLink XML 有字段，就写“当前飞控可直接观测”——还缺源码、配置和运行三层证据。
2. 看到 `STATUSTEXT` 或后续模式变化，就当作内部事件精确时刻——文本和结果通常只提供延迟的条件证据。
3. 把 `t-1` 当一秒前——它只是上一有效样本，间隔由消息流决定。
4. 用默认参数值替代运行值——性质实例必须在测试开始读取参数；Paparazzi XML 编译常量则要记录任务/机体快照，不能冒充 MAVLink 参数。

## 九、TAMonitor 公式级验证结果

`TAMonitor` 是本项目的“时间自动机运行时监视器”，用于把公式与带时间戳的真假轨迹对照。这里的“通过”只表示合成轨迹的公式编码与独立预期一致；“失败”表示监视器边界判定不一致；“运行不支持”表示公式能构建，但当前监视器在状态投影上超过限制；“未进入执行门”表示上下文、具体参数或当前监视器语法尚未闭合。任何一种状态都不改变“实现符合性：未评估”。

本轮复查命令：`PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check`。结果为 8 个已入门公式、49 条合成轨迹：6 个公式通过、1 个失败、1 个运行不支持。与当前 28 条新性质直接同式对应的结果如下：

|当前新性质|监视器状态|证据与解释|
|---|---|---|
|`ARD-NEW-GCS-008`|通过|对应既有具体实例 `ARD-COPTER-GCS-001`，6 条轨迹一致|
|`ARD-NEW-BATT-010`|通过|对应 `ARD-SHARED-BATT-001`，7 条轨迹一致；开区间边界保留|
|`ARD-NEW-RTL-011`|运行不支持|对应 `ARD-COPTER-RTL-003`；公式可构建，但当前二元决策图投影估值超过上限|
|`ARD-NEW-GUID-012`|通过|对应 `ARD-COPTER-GUID-002`，6 条轨迹一致|
|`PX4-MC-RCLOSS-001`|失败|6 条中 5 条一致；恰在闭下界触发的合法轨迹被判为违反，保留差异|
|`PX4-MC-GCSLOSS-002`|通过|6 条轨迹一致|
|其余 ArduPilot 11 条|未进入执行门|公式含尚未闭合的复合上下文、定性 `U` 义务或未形成当前监视器支持的具体实例；各自正/反例仍保留在系统文档|
|其余 PX4 4 条|未进入执行门|Offboard 证据冲突或内部事件/参数上下文未闭合|
|Paparazzi 7 条|未进入执行门|PPRZLink AP 适配器和生成任务块编号尚未接入 TAMonitor；不能拿 MAVLink 适配器替代|

完整执行证据在 [`monitor_validation/README.md`](../extraction_runs/milestone7/monitor_validation/README.md)。没有进入执行门的性质不是“已验证通过”，也不是“飞控违反”；它们仍可作为人工审核和下一阶段适配器实现的输入。
