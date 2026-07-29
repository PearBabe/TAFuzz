# PX4：PGFuzz 原 21 条性质的当前审计

## 术语与边界

- `PX4` 是飞控项目名称；本文件冻结 v1.17.0 多旋翼源码。`uORB` 是 PX4 内部发布—订阅消息总线，原子命题常对应其中的消息字段。
- `AP` 是 Atomic Proposition，中文为“原子命题”；`MAVLink` 是 Micro Air Vehicle Link，中文为“微型飞行器通信协议”。源码绑定只证明变量身份和观测路径，不证明性质满足。
- `RTL` 是 Return To Launch，中文为“返航”；`Offboard` 是“外部控制模式”。`t-1` 只表示上一条有效观测，绝不是一秒前。
- `InputP/InputC/InputE` 分别是配置参数输入、命令/遥控输入、环境输入；它们是 PGFuzz 作者列出的候选影响输入，不是已证明因果依赖。
- 所有状态值使用中文；公式、参数、消息、变量和函数保持源码英文标识符，便于搜索。每条固定“实现符合性：未评估”。

## 21 条总表

|编号|当前规范状态|论文英文原文和中文解释|当前官方依据与精确位置|论文印刷公式原样|当前规范化公式和修改说明|原子命题、源码变量/函数和 MAVLink 摘要|作者候选输入与参数|时间来源、时钟和边界|实现符合性|
|---|---|---|---|---|---|---|---|---|---|
| PX.RTL1 | 需按当前版本改写 | If the current altitude is less than RTL_RETURN_ALT, then altitude must be increased until the altitude is greater or equal to RTL_RETURN_ALT.<br>当前高度低于 RTL_RETURN_ALT 时持续爬升，直到达到该高度。 | [return.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L152-L181)，`docs/en/flight_modes/return.md:152-181`。当前返航高度还受 RTL_CONE_ANG、RTL_DESCEND_ALT、目的地类型和当前高度共同影响。 | `G(((ALT_t < RTL_RETURN_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))` | `G((Mode=RTL ∧ below_current_return_target) → F_[0,∞) at_or_above_current_return_target)`<br>当前返航高度还受 RTL_CONE_ANG、RTL_DESCEND_ALT、目的地类型和当前高度共同影响。 | `ALT_t < RTL_RETURN_ALT`：建模对应/需要插桩；`RTL_RETURN_ALT` [baseline/px4/src/modules/navigator/rtl_params.c:59](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L59-L59)<br>`Mode_t = RTL`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL` [baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)<br>`ALT_t-1 < ALT_t`：建模对应/需要插桩； | 制品目录 `PX.RTL1`；93 条候选关联（InputC=52, InputE=11, InputP=30）；`RTL_RETURN_ALT` 默认 `60.0`、冻结 SITL `30.0`、单位 `m`、可修改 | 上一有效观测顺序关系，不是秒；样本必须同一运行、同一坐标系。 | 未评估 |
| PX.RTL2 | 需按当前版本改写 | If the current altitude is greater or equal to RTL_RETURN_ALT, current flight mode is RTL, and the current vehicle is not home position, then the vehicle must move to the home position while maintaining the current altitude.<br>达到 PX4 返航高度且尚未到家时保持高度并移动到家。 | [return.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L152-L181)，`docs/en/flight_modes/return.md:152-181`。当前返航路径可能是直接路径、任务路径、集结点或着陆序列，不能固定成“保持当前高度直飞 Home”。 | `G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))` | `G((Mode=RTL ∧ direct_return_leg ∧ ¬at_selected_destination) → F_[0,∞) at_selected_destination)`<br>当前返航路径可能是直接路径、任务路径、集结点或着陆序列，不能固定成“保持当前高度直飞 Home”。 | `Mode_t = RTL`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL` [baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)<br>`ALT_t >= RTL_RETURN_ALT`：建模对应/需要插桩；`RTL_RETURN_ALT` [baseline/px4/src/modules/navigator/rtl_params.c:59](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L59-L59)<br>`Pos_t != home_position`：建模对应/可直接观测；`vehicle_global_position.lat,lon` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)、`home_position.lat,lon` [baseline/px4/msg/versioned/HomePosition.msg:7](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/HomePosition.msg#L7-L7)<br>`Pos_t-1 != Pos_t`：建模对应/可计算得到；`previous_accepted(vehicle_global_position.lat,lon)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)、`vehicle_global_position.lat,lon` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)<br>`ALT_t-1 = ALT_t`：建模对应/需要插桩； | 制品目录 `PX.RTL2`；92 条候选关联（InputC=51, InputE=11, InputP=30）；`RTL_RETURN_ALT` 默认 `60.0`、冻结 SITL `30.0`、单位 `m`、可修改 | 上一有效观测顺序关系，不是秒；样本必须同一运行、同一坐标系。 | 未评估 |
| PX.RTL3 | 需按当前版本改写 | If current altitude is greater or equal to RTL_RETURN_ALT and current position is the same as home position, then flight mode must be LAND.<br>达到返航高度并到家后进入着陆模式。 | [return.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L183-L194)，`docs/en/flight_modes/return.md:183-194`。到达目的地后先下降到 RTL_DESCEND_ALT 并按 RTL_LAND_DELAY 等待；不是同一采样点立刻 LAND。 | `G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))` | `G(enter_rtl_destination_loiter → (G_[0,T_rtl_land) ¬Mode_LAND ∧ F_[T_rtl_land,∞) Mode_LAND))`<br>到达目的地后先下降到 RTL_DESCEND_ALT 并按 RTL_LAND_DELAY 等待；不是同一采样点立刻 LAND。 | `Mode_t = RTL`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL` [baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)<br>`ALT_t >= RTL_RETURN_ALT`：建模对应/需要插桩；`RTL_RETURN_ALT` [baseline/px4/src/modules/navigator/rtl_params.c:59](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L59-L59)<br>`Pos_t = home_position`：建模对应/可直接观测；`vehicle_global_position.lat,lon` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)、`home_position.lat,lon` [baseline/px4/msg/versioned/HomePosition.msg:7](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/HomePosition.msg#L7-L7)<br>`Mode_t = LAND`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND` [baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54) | 制品目录 `PX.RTL3`；92 条候选关联（InputC=51, InputE=11, InputP=30）；`RTL_RETURN_ALT` 默认 `60.0`、冻结 SITL `30.0`、单位 `m`、可修改 | 无明确时间或无界性质。 | 未评估 |
| PX.RTL4 | 需按当前版本改写 | If RTL_LAND_DELAY parameter has -1, the vehicle must hover at RTL_DESCEND_ALT.<br>RTL_LAND_DELAY 为负一时在 RTL_DESCEND_ALT 高度盘旋。 | [return.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L183-L194)，`docs/en/flight_modes/return.md:183-194`。论文自然语言写 RTL_LAND_DELAY=-1，印刷公式却写 RTL_DESCEND_ALT=-1；当前应使用 RTL_LAND_DELAY。 | `G(((Mode_t = RTL) & (RTL_DESCEND_ALT = -1)) -> ((Pos_t = Pos_t-1) & (ALT_t = ALT_t-1)))` | `G((Mode=RTL ∧ runtime(RTL_LAND_DELAY)=-1 ∧ at_descent_altitude) → loiter_at_destination)`<br>论文自然语言写 RTL_LAND_DELAY=-1，印刷公式却写 RTL_DESCEND_ALT=-1；当前应使用 RTL_LAND_DELAY。 | `Mode_t = RTL`：建模对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL` [baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)<br>`RTL_DESCEND_ALT = -1`：建模对应/可直接观测；`RTL_DESCEND_ALT` [baseline/px4/src/modules/navigator/rtl_params.c:75](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L75-L75)<br>`RTL_LAND_DELAY = -1`：建模对应/可直接观测；`RTL_LAND_DELAY` [baseline/px4/src/modules/navigator/rtl_params.c:89](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L89-L89)<br>`Pos_t = Pos_t-1`：建模对应/可计算得到；`vehicle_global_position.lat,lon` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)、`previous_accepted(vehicle_global_position.lat,lon)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)<br>`ALT_t-1 = ALT_t`：建模对应/需要插桩； | 制品目录 `PX.RTL4`；92 条候选关联（InputC=51, InputE=11, InputP=30）；`RTL_DESCEND_ALT` 默认 `30.0`、冻结 SITL `10.0`、单位 `m`、可修改；`RTL_LAND_DELAY` 默认 `0.0`、冻结 SITL `0.0`、单位 `s`、可修改 | 上一有效观测顺序关系，不是秒；样本必须同一运行、同一坐标系。 | 未评估 |
| PX.RTL5 | 需按当前版本改写 | It is the same as A.RTL4.<br>与 A.RTL4 相同：着陆触地后锁定电机。 | [land.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/land.md#L23-L37)，`docs/en/flight_modes_mc/land.md:23-37`。当前着陆后自动锁定由 COM_DISARM_LAND 决定，且可禁用，不是无条件同一时刻锁定。 | `It is the same as A.RTL4.` | `G((landed_start ∧ runtime(COM_DISARM_LAND)>0) → (G_[0,T_disarm) armed ∧ F_[T_disarm,∞) disarmed))`<br>当前着陆后自动锁定由 COM_DISARM_LAND 决定，且可禁用，不是无条件同一时刻锁定。 | `Mode_t = LAND`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND` [baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54)<br>`ALT_t = GroundALT`：无法确认/无法确认；`no type-compatible numeric GroundALT definition`（无可靠位置）<br>`Disarm = on`：精确对应/可直接观测；`vehicle_status.arming_state == ARMING_STATE_DISARMED` [baseline/px4/msg/versioned/VehicleStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L10-L10) | 制品目录 `PX.RTL5`；92 条候选关联（InputC=51, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.ORBIT1 | 有条件必须满足 | It is the same as A.CIRCLE1.<br>继承 A.CIRCLE1，并把绕圈模式解释为 PX4 ORBIT。 | [orbit.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L27-L50)，`docs/en/flight_modes_mc/orbit.md:27-50`。当前俯仰杆改变环绕半径，中心杆锁定当前半径；必须加入已启动 Orbit 和有效 RC 前提。 | `It is the same as A.CIRCLE1.` | `G((Mode=ORBIT ∧ orbit_active ∧ pitch_radius_decrease) → commanded_radius_decreases)`<br>当前俯仰杆改变环绕半径，中心杆锁定当前半径；必须加入已启动 Orbit 和有效 RC 前提。 | `Mode_t = ORBIT`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ORBIT` [baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)<br>`RC_pitch < 1500`：建模对应/条件可观测；`input_rc.values[RC_MAP_PITCH-1]` [baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)<br>`Circle_radius_t > 0`：建模对应/需要插桩；`FlightTaskOrbit::_orbit_radius` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)<br>`Circle_radius_t < Circle_radius_t-1`：建模对应/需要插桩；`FlightTaskOrbit::_orbit_radius` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)、`previous_accepted(fabs(orbit_status.radius))` [baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10) | 制品目录 `PX.ORBIT1`；50 条候选关联（InputC=9, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.ORBIT2 | 有条件必须满足 | It is the same as A.CIRCLE2.<br>继承 A.CIRCLE2，并把绕圈模式解释为 PX4 ORBIT。 | [orbit.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L27-L50)，`docs/en/flight_modes_mc/orbit.md:27-50`。当前俯仰杆改变环绕半径，方向需按当前手册解释。 | `It is the same as A.CIRCLE2.` | `G((Mode=ORBIT ∧ orbit_active ∧ pitch_radius_increase) → commanded_radius_increases)`<br>当前俯仰杆改变环绕半径，方向需按当前手册解释。 | `Mode_t = ORBIT`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ORBIT` [baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)<br>`RC_pitch > 1500`：建模对应/条件可观测；`input_rc.values[RC_MAP_PITCH-1]` [baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)<br>`Circle_radius_t > Circle_radius_t-1`：建模对应/需要插桩；`FlightTaskOrbit::_orbit_radius` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)、`previous_accepted(fabs(orbit_status.radius))` [baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10) | 制品目录 `PX.ORBIT2`；50 条候选关联（InputC=9, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.ORBIT3 | 有条件必须满足 | It is the same as A.CIRCLE3.<br>继承 A.CIRCLE3，并把绕圈模式解释为 PX4 ORBIT。 | [orbit.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L38-L50)，`docs/en/flight_modes_mc/orbit.md:38-50`。横滚杆控制环绕加速度、速度和方向；不能仅用相邻速度样本严格单调代替控制目标。 | `It is the same as A.CIRCLE3.` | `G((Mode=ORBIT ∧ orbit_active ∧ roll_accel_clockwise) → commanded_tangential_acceleration_clockwise)`<br>横滚杆控制环绕加速度、速度和方向；不能仅用相邻速度样本严格单调代替控制目标。 | `Mode_t = ORBIT`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ORBIT` [baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)<br>`RC_roll > 1500`：建模对应/条件可观测；`input_rc.values[RC_MAP_ROLL-1]` [baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)<br>`Circle_direction_t = clockwise`：建模对应/可直接观测；`sign(orbit_status.radius)` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:138](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp#L138-L138)<br>`Circle_speed_t > Circle_speed_t-1`：建模对应/需要插桩；`fabs(FlightTaskOrbit::_orbit_velocity)` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)、`previous_accepted(fabs(FlightTaskOrbit::_orbit_velocity))` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118) | 制品目录 `PX.ORBIT3`；50 条候选关联（InputC=9, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.ORBIT4 | 有条件必须满足 | It is the same as A.CIRCLE4.<br>继承 A.CIRCLE4，并把绕圈模式解释为 PX4 ORBIT。 | [orbit.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L38-L50)，`docs/en/flight_modes_mc/orbit.md:38-50`。横滚杆控制顺/逆时针加速度，必须保留方向和限幅上下文。 | `It is the same as A.CIRCLE4.` | `G((Mode=ORBIT ∧ orbit_active ∧ roll_accel_counterclockwise) → commanded_tangential_acceleration_counterclockwise)`<br>横滚杆控制顺/逆时针加速度，必须保留方向和限幅上下文。 | `Mode_t = ORBIT`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ORBIT` [baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)<br>`RC_roll > 1500`：建模对应/条件可观测；`input_rc.values[RC_MAP_ROLL-1]` [baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)<br>`Circle_direction_t = counterclockwise`：建模对应/可直接观测；`sign(orbit_status.radius)` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:138](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp#L138-L138)<br>`Circle_speed_t < Circle_speed_t-1`：建模对应/需要插桩；`fabs(FlightTaskOrbit::_orbit_velocity)` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)、`previous_accepted(fabs(FlightTaskOrbit::_orbit_velocity))` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118) | 制品目录 `PX.ORBIT4_5`；50 条候选关联（InputC=9, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.ORBIT5 | 需按当前版本改写 | The maximum radius must be 100 meters.<br>绕点飞行最大半径为 100 米。 | [orbit.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L60-L66)，`docs/en/flight_modes_mc/orbit.md:60-66`。当前 MC_ORBIT_RAD_MAX 默认 1000 m，论文固定 100 m 已过时。 | `G((Mode_t = ORBIT) -> (Circle_radius_t < 100))` | `G(Mode=ORBIT → commanded_radius≤runtime(MC_ORBIT_RAD_MAX))`<br>当前 MC_ORBIT_RAD_MAX 默认 1000 m，论文固定 100 m 已过时。 | `Mode_t = ORBIT`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ORBIT` [baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)<br>`Circle_radius_t < 100m`：建模对应/需要插桩；`FlightTaskOrbit::_orbit_radius` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119) | 制品目录 `PX.ORBIT4_5`；50 条候选关联（InputC=9, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.ORBIT6 | 需按当前版本改写 | The maximum acceleration must be limited to 2m/s^2.<br>绕点飞行最大加速度限制为每平方秒 2 米。 | [orbit.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L69-L80)，`docs/en/flight_modes_mc/orbit.md:69-80`。官方限制向心加速度为 2 m/s²；论文公式却把 Circle_speed 与加速度单位比较，量纲错误。 | `G((Mode_t = ORBIT) -> (Circle_speed_t < 2m/s^2))` | `G(Mode=ORBIT → centripetal_acceleration≤2m/s²)`<br>官方限制向心加速度为 2 m/s²；论文公式却把 Circle_speed 与加速度单位比较，量纲错误。 | `Mode_t = ORBIT`：建模对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ORBIT` [baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)<br>`Circle_speed_t < 2m/s^2`：建模对应/需要插桩；`fabs(FlightTaskOrbit::_orbit_velocity)` [baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118) | 制品目录 `PX.ORBIT6`；50 条候选关联（InputC=9, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.LAND1 | 有条件必须满足 | Descending speed must be the same as MPC_LAND_SPEED parameter.<br>下降速度等于 MPC_LAND_SPEED 参数。 | [land.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/land.md#L23-L37)，`docs/en/flight_modes_mc/land.md:23-37`。MPC_LAND_SPEED 是下降目标速率；实际速度不要求每个样本严格等于参数。 | `G((Mode_t = LAND) -> (Speed_vertical_t = MPC_LAND_SPEED))` | `G(Mode=LAND → commanded_descent_rate=runtime(MPC_LAND_SPEED))`<br>MPC_LAND_SPEED 是下降目标速率；实际速度不要求每个样本严格等于参数。 | `Mode_t = LAND`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND` [baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54)<br>`Speed_vertical_t = MPC_LAND_SPEED`：建模对应/可直接观测；`vehicle_local_position.vz` [baseline/px4/msg/versioned/VehicleLocalPosition.msg:28](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L28-L28)、`MPC_LAND_SPEED` [baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c:111](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c#L111-L111) | 制品目录 `PX.LAND1`；94 条候选关联（InputC=53, InputE=11, InputP=30）；`MPC_LAND_SPEED` 默认 `0.7`、冻结 SITL `0.699999988079071`、单位 `m/s`、可修改 | 无明确时间或无界性质。 | 未评估 |
| PX.ALTITUDE1 | 有条件必须满足 | It is the same as A.ALT_HOLD2.<br>继承 A.ALT_HOLD2，并把模式解释为 PX4 ALTITUDE。 | [altitude.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/altitude.md#L20-L50)，`docs/en/flight_modes_mc/altitude.md:20-50`。中位油门保持当前高度，死区与有效高度估计是前提；不是原始 PWM 恰等于 1500 的物理恒等式。 | `It is the same as A.ALT_HOLD2.` | `G((Mode=ALTITUDE ∧ throttle_in_deadzone) → altitude_setpoint_held)`<br>中位油门保持当前高度，死区与有效高度估计是前提；不是原始 PWM 恰等于 1500 的物理恒等式。 | `Mode_t = ALTITUDE`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ALTCTL` [baseline/px4/msg/versioned/VehicleStatus.msg:37](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L37-L37)<br>`Throttle_t = 1500`：建模对应/条件可观测；`input_rc.values[RC_MAP_THROTTLE-1]` [baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)<br>`ALT_t-1 = ALT_t`：建模对应/条件可观测；`previous_accepted(vehicle_global_position.alt)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)、`vehicle_global_position.alt` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15) | 制品目录 `PX.ALTITUDE1`；93 条候选关联（InputC=52, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.POSITION1 | 有条件必须满足 | The vehicle must maintain a constant position.<br>位置控制模式保持位置不变。 | [position.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/position.md#L20-L62)，`docs/en/flight_modes_mc/position.md:20-62`。摇杆居中时保持位置；有飞手输入时位置应改变，论文漏掉前提。 | `G((Mode_t = POSITION) -> (Pos_t = Pos_t-1))` | `G((Mode=POSITION ∧ sticks_centered) → position_setpoint_held)`<br>摇杆居中时保持位置；有飞手输入时位置应改变，论文漏掉前提。 | `Mode_t = POSITION`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_POSCTL` [baseline/px4/msg/versioned/VehicleStatus.msg:38](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L38-L38)<br>`Pos_t = Pos_t-1`：建模对应/可计算得到；`vehicle_global_position.lat,lon` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)、`previous_accepted(vehicle_global_position.lat,lon)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13) | 制品目录 `PX.POSITION1`；93 条候选关联（InputC=52, InputE=11, InputP=30） | 上一有效观测顺序关系，不是秒；样本必须同一运行、同一坐标系。 | 未评估 |
| PX.HOLD1 | 需按当前版本改写 | It is the same as A.LOITER1.<br>继承 A.LOITER1，并把模式解释为 PX4 HOLD。 | [hold.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/hold.md#L20-L48)，`docs/en/flight_modes_mc/hold.md:20-48`。Hold 是自动悬停/盘旋行为，不能直接继承 ArduPilot LOITER 的摇杆语义。 | `It is the same as A.LOITER1.` | `G(enter_HOLD → F_[0,∞) hold_position_or_loiter)`<br>Hold 是自动悬停/盘旋行为，不能直接继承 ArduPilot LOITER 的摇杆语义。 | `Mode_t = HOLD`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_LOITER` [baseline/px4/msg/versioned/VehicleStatus.msg:40](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L40-L40)<br>`Pos_t = Pos_t-1`：建模对应/可计算得到；`vehicle_global_position.lat,lon` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)、`previous_accepted(vehicle_global_position.lat,lon)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)<br>`Yaw_t = Yaw_t-1`：建模对应/可计算得到；`vehicle_local_position.heading` [baseline/px4/msg/versioned/VehicleLocalPosition.msg:42](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L42-L42)、`previous_accepted(vehicle_local_position.heading)` [baseline/px4/msg/versioned/VehicleLocalPosition.msg:42](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L42-L42)<br>`ALT_t-1 = ALT_t`：建模对应/条件可观测；`previous_accepted(vehicle_global_position.alt)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)、`vehicle_global_position.alt` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15) | 制品目录 `PX.HOLD1`；93 条候选关联（InputC=52, InputE=11, InputP=30） | 无明确时间或无界性质。 | 未评估 |
| PX.HOLD2 | 有条件必须满足 | If MIS_LTRMIN_ALT is not -1 and current altitude is less than the parameter value, then the vehicle must ascend to this altitude.<br>最小盘旋高度启用且当前高度低于它时爬升到该高度。 | [hold.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/hold.md#L35-L48)，`docs/en/flight_modes_mc/hold.md:35-48`。MIS_LTRMIN_ALT 当前决定进入 Hold 时的最低高度，但 -1 禁用、参考高度和达到过程必须保留。 | `G(((Mode_t = HOLD) & (MIS_LTRMIN_ALT != -1)) -> (ALT_t > ALT_t-1))` | `G((enter_HOLD ∧ runtime(MIS_LTRMIN_ALT)≠-1 ∧ ALT<minimum_hold_altitude) → F_[0,∞) ALT≥minimum_hold_altitude)`<br>MIS_LTRMIN_ALT 当前决定进入 Hold 时的最低高度，但 -1 禁用、参考高度和达到过程必须保留。 | `Mode_t = HOLD`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_LOITER` [baseline/px4/msg/versioned/VehicleStatus.msg:40](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L40-L40)<br>`MIS_LTRMIN_ALT != -1`：建模对应/可直接观测；`NAV_MIN_LTR_ALT` [baseline/px4/src/modules/navigator/navigator_params.c:192](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator_params.c#L192-L192)<br>`ALT_t < MIS_LTRMIN_ALT`：建模对应/条件可观测；`NAV_MIN_LTR_ALT` [baseline/px4/src/modules/navigator/navigator_params.c:192](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator_params.c#L192-L192)<br>`ALT_t-1 < ALT_t`：建模对应/条件可观测；`previous_accepted(vehicle_global_position.alt)` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)、`vehicle_global_position.alt` [baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)<br>`Target_ALT = MIS_LTRMIN_ALT`：建模对应/可计算得到；`NAV_MIN_LTR_ALT` [baseline/px4/src/modules/navigator/navigator_params.c:192](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator_params.c#L192-L192) | 制品目录 `PX.HOLD2`；93 条候选关联（InputC=52, InputE=11, InputP=30）；`NAV_MIN_LTR_ALT` 默认 `-1.0`、冻结 SITL `-1.0`、单位 `m`、可修改 | 上一有效观测顺序关系，不是秒；样本必须同一运行、同一坐标系。 | 未评估 |
| PX.TAKEOFF1 | 有条件必须满足 | When the vehicle conducts a taking off command, the target altitude must be the MIS_TAKEOFF_ALT parameter value.<br>执行起飞命令时目标高度应等于 MIS_TAKEOFF_ALT。 | [takeoff.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/takeoff.md#L20-L44)，`docs/en/flight_modes_mc/takeoff.md:20-44`。起飞目标高度使用 MIS_TAKEOFF_ALT，但公式应表达目标/达到过程，不是所有时刻 ALT≤参数。 | `G((Command_t = takeoff) -> (ALT_t <= MIS_TAKEOFF_ALT))` | `G(accepted_takeoff → F_[0,∞) target_altitude_reached(runtime(MIS_TAKEOFF_ALT)))`<br>起飞目标高度使用 MIS_TAKEOFF_ALT，但公式应表达目标/达到过程，不是所有时刻 ALT≤参数。 | `Command_t = takeoff`：建模对应/条件可观测；`vehicle_command.command` [baseline/px4/msg/versioned/VehicleCommand.msg:190](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L190-L190)、`vehicle_command_s::VEHICLE_CMD_NAV_TAKEOFF` [baseline/px4/msg/versioned/VehicleCommand.msg:17](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L17-L17)<br>`ALT_t <= MIS_TAKEOFF_ALT`：建模对应/可计算得到；`MIS_TAKEOFF_ALT` [baseline/px4/src/modules/navigator/mission_params.c:58](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_params.c#L58-L58)<br>`Target_ALT = MIS_TAKEOFF_ALT`：建模对应/可计算得到；`MIS_TAKEOFF_ALT` [baseline/px4/src/modules/navigator/mission_params.c:58](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_params.c#L58-L58) | 制品目录 `PX.TAKEOFF1`；94 条候选关联（InputC=53, InputE=11, InputP=30）；`MIS_TAKEOFF_ALT` 默认 `2.5`、冻结 SITL `2.5`、单位 `m`、可修改 | 论文经验时间或参数加经验余量；具体 k 未公开，不能补秒数；论文也未公开可靠时钟载体。 | 未评估 |
| PX.TAKEOFF2 | 有条件必须满足 | When the vehicle conducts a taking off command, the speed of ascent must be the MPC_TKO_SPEED parameter value.<br>执行起飞命令时上升速度应等于 MPC_TKO_SPEED。 | [takeoff.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/takeoff.md#L20-L44)，`docs/en/flight_modes_mc/takeoff.md:20-44`。MPC_TKO_SPEED 是上升目标速度/上限语义，实测速度不要求逐样本严格相等。 | `G((Command_t = takeoff) -> (Speed_vertical_t = MPC_TKO_SPEED))` | `G((takeoff_climb_active) → commanded_climb_rate=runtime(MPC_TKO_SPEED))`<br>MPC_TKO_SPEED 是上升目标速度/上限语义，实测速度不要求逐样本严格相等。 | `Command_t = takeoff`：建模对应/条件可观测；`vehicle_command.command` [baseline/px4/msg/versioned/VehicleCommand.msg:190](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L190-L190)、`vehicle_command_s::VEHICLE_CMD_NAV_TAKEOFF` [baseline/px4/msg/versioned/VehicleCommand.msg:17](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L17-L17)<br>`Speed_vertical_t = MPC_TKO_SPEED`：建模对应/可直接观测；`vehicle_local_position.vz` [baseline/px4/msg/versioned/VehicleLocalPosition.msg:28](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L28-L28)、`MPC_TKO_SPEED` [baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c#L57-L57) | 制品目录 `PX.TAKEOFF2`；94 条候选关联（InputC=53, InputE=11, InputP=30）；`MPC_TKO_SPEED` 默认 `1.5`、冻结 SITL `1.5`、单位 `m/s`、可修改 | 论文经验时间或参数加经验余量；具体 k 未公开，不能补秒数；论文也未公开可靠时钟载体。 | 未评估 |
| PX.GPS.FS1 | 需按当前版本改写 | If time exceeds COM_POS_FS_DELAY seconds after GPS loss is detected, the GPS fail-safe must be triggered.<br>检测到 GPS 丢失后，在 COM_POS_FS_DELAY 加调度余量内触发故障保护。 | [safety.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/config/safety.md#L190-L211)，`docs/en/config/safety.md:190-211`。历史 COM_POS_FS_DELAY 已删除；当前位置丢失由 EKF2_NOAID_TOUT 和 COM_POS_FS_EPH 等机制组合判断。 | `G((GPS_loss = on) -> F_[0,COM_POS_FS_DELAY+k](GPS_fail = on))` | `G((position_estimate_invalid_start ∧ position_required) → F_[0,∞) position_loss_failsafe)`<br>历史 COM_POS_FS_DELAY 已删除；当前位置丢失由 EKF2_NOAID_TOUT 和 COM_POS_FS_EPH 等机制组合判断。 | `GPS_loss = on`：建模对应/可直接观测；`sensor_gps.timestamp,fix_type` [baseline/px4/msg/SensorGps.msg:3](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/SensorGps.msg#L3-L3)<br>`F_[0,COM_POS_FS_DELAY+k](GPS_fail = on)`：无法确认/无法确认；`failsafe_flags.global_position_invalid` [baseline/px4/msg/FailsafeFlags.msg:32](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L32-L32)、`COM_POS_FS_DELAY` [baseline/px4/docs/en/releases/1.16.md:58](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/releases/1.16.md#L58-L58) | 制品目录 `PX.GPS.FS1`；94 条候选关联（InputC=52, InputE=11, InputP=31）；`COM_POS_FS_DELAY` 默认 ``、冻结 SITL ``、单位 ``、可修改 | 论文经验时间或参数加经验余量；具体 k 未公开，不能补秒数；论文也未公开可靠时钟载体。 | 未评估 |
| PX.GPS.FS2 | 需按当前版本改写 | If the GPS fail-safe is triggered and a remote controller is available, the flight mode must be changed to ALTITUDE mode.<br>GPS 故障保护触发且遥控可用时进入高度模式。 | [safety.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/config/safety.md#L190-L211)，`docs/en/config/safety.md:190-211`。当前多旋翼位置丢失时有高度估计则切 Altitude，否则 Stabilized；不以 RC 可用性作为论文所写的唯一分支。 | `G(((GPS_fail = on) & (RC_t = on)) -> (Mode_t = ALTITUDE))` | `G((position_loss_failsafe ∧ height_estimate_valid) → F_[0,∞) Mode=ALTITUDE)`<br>当前多旋翼位置丢失时有高度估计则切 Altitude，否则 Stabilized；不以 RC 可用性作为论文所写的唯一分支。 | `GPS_fail = on`：无法确认/无法确认；`failsafe_flags.global_position_invalid` [baseline/px4/msg/FailsafeFlags.msg:32](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L32-L32)<br>`RC_t = on`：建模对应/条件可观测；`!(input_rc.rc_lost \|\| input_rc.rc_failsafe)` [baseline/px4/msg/InputRc.msg:29](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L29-L29)<br>`Mode_t = ALTITUDE`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_ALTCTL` [baseline/px4/msg/versioned/VehicleStatus.msg:37](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L37-L37) | 制品目录 `PX.GPS.FS2`；94 条候选关联（InputC=52, InputE=11, InputP=31） | 无明确时间或无界性质。 | 未评估 |
| PX.GPS.FS3 | 需按当前版本改写 | If the GPS fail-safe is triggered and a remote controller is not available, the flight mode must be changed to LAND mode.<br>GPS 故障保护触发且遥控不可用时进入着陆模式。 | [safety.md：当前栏目](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/config/safety.md#L190-L211)，`docs/en/config/safety.md:190-211`。当前无高度估计时切 Stabilized，而非简单地因 RC 不可用必然 LAND。 | `G(((GPS_fail = on) & (RC_t = off)) -> (Mode_t = LAND))` | `G((position_loss_failsafe ∧ ¬height_estimate_valid) → F_[0,∞) Mode=STABILIZED)`<br>当前无高度估计时切 Stabilized，而非简单地因 RC 不可用必然 LAND。 | `GPS_fail = on`：无法确认/无法确认；`failsafe_flags.global_position_invalid` [baseline/px4/msg/FailsafeFlags.msg:32](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L32-L32)<br>`RC_t = off`：建模对应/条件可观测；`!(input_rc.rc_lost \|\| input_rc.rc_failsafe)` [baseline/px4/msg/InputRc.msg:29](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L29-L29)<br>`Mode_t = LAND`：精确对应/可直接观测；`vehicle_status.nav_state` [baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)、`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND` [baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54) | 制品目录 `PX.GPS.FS3`；94 条候选关联（InputC=52, InputE=11, InputP=31） | 无明确时间或无界性质。 | 未评估 |

## 每条性质的完整源码绑定与作者输入

<details><summary><strong>PX.RTL1</strong>：当前高度低于 RTL_RETURN_ALT 时持续爬升，直到达到该高度。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G(((ALT_t < RTL_RETURN_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))`。
- 当前式：`G((Mode=RTL ∧ below_current_return_target) → F_[0,∞) at_or_above_current_return_target)`。
- 官方位置：[docs/en/flight_modes/return.md:152-181](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L152-L181)。当前返航高度还受 RTL_CONE_ANG、RTL_DESCEND_ALT、目的地类型和当前高度共同影响。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `ALT_t < RTL_RETURN_ALT` | PX4 当前高度低于返航高度参数。 | 建模对应 | 需要插桩 | `vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。<br>`RTL_RETURN_ALT`，[baseline/px4/src/modules/navigator/rtl_params.c:59](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L59-L59)；当前运行参数值等于 PARAM 协议读取值。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`RTL::_param_rtl_return_alt`，[baseline/px4/src/modules/navigator/rtl.h:236](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.h#L236-L236)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_rtl_return_alt.get()`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L477)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。<br>`_param_rtl_return_alt.get()`，[baseline/px4/src/modules/navigator/rtl.cpp:530](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L530-L530)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `Mode_t = RTL` | 当前飞行模式是返航模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)；Mode_t == NAVIGATION_STATE_AUTO_RTL。  |
| `ALT_t-1 < ALT_t` | 当前观测高度高于上一观测高度。 | 建模对应 | 需要插桩 | `previous_accepted(current AMSL-selected RTL destination AMSL)`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L477)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。<br>`vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。 |

**公式参数**

- 论文 `None` → 当前 `RTL_RETURN_ALT`；默认 `60.0`，冻结 SITL `30.0`，单位 `m`，范围 `0.0..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,6`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:2`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:3`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:4`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:5`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:6`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:7`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:8`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:9`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:10`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:11`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:18`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:19`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:20`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:21`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:24`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:25`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:28`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:30`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:32`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:35`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:36`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.RTL2</strong>：达到 PX4 返航高度且尚未到家时保持高度并移动到家。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))`。
- 当前式：`G((Mode=RTL ∧ direct_return_leg ∧ ¬at_selected_destination) → F_[0,∞) at_selected_destination)`。
- 官方位置：[docs/en/flight_modes/return.md:152-181](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L152-L181)。当前返航路径可能是直接路径、任务路径、集结点或着陆序列，不能固定成“保持当前高度直飞 Home”。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = RTL` | 当前飞行模式是返航模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)；Mode_t == NAVIGATION_STATE_AUTO_RTL。  |
| `ALT_t >= RTL_RETURN_ALT` | PX4 当前高度达到或超过返航高度参数。 | 建模对应 | 需要插桩 | `vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。<br>`RTL_RETURN_ALT`，[baseline/px4/src/modules/navigator/rtl_params.c:59](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L59-L59)；当前运行参数值等于 PARAM 协议读取值。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`RTL::_param_rtl_return_alt`，[baseline/px4/src/modules/navigator/rtl.h:236](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.h#L236-L236)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_rtl_return_alt.get()`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L477)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。<br>`_param_rtl_return_alt.get()`，[baseline/px4/src/modules/navigator/rtl.cpp:530](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L530-L530)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `Pos_t != home_position` | 当前位置不等于返航参考位置。 | 建模对应 | 可直接观测 | `vehicle_global_position.lat,lon`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；读取 lat/lon 且 lat_lon_valid=true。 检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。<br>`home_position.lat,lon`，[baseline/px4/msg/versioned/HomePosition.msg:7](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/HomePosition.msg#L7-L7)；读取 Home 经纬度且 valid_hpos=true。 检查 timestamp、valid_hpos 和 update_count。 |
| `Pos_t-1 != Pos_t` | 当前位置与上一观测位置不同。 | 建模对应 | 可计算得到 | `previous_accepted(vehicle_global_position.lat,lon)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；取同一数据源、同一坐标系的前一个已接受有效样本。 必须与当前 Pos_t 使用同一候选组；拒绝跨 xy/lat_lon reset counter 的样本。<br>`vehicle_global_position.lat,lon`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；读取 lat/lon 且 lat_lon_valid=true。 检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。 |
| `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | 建模对应 | 需要插桩 | `previous_accepted(current AMSL-selected RTL destination AMSL)`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L477)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。<br>`vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。 |

**公式参数**

- 论文 `None` → 当前 `RTL_RETURN_ALT`；默认 `60.0`，冻结 SITL `30.0`，单位 `m`，范围 `0.0..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）51 条：
  - `Flight_Mode,5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:2`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:3`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:4`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:5`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:6`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:7`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:8`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:9`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:10`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:11`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:12`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:13`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:16`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:17`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:18`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:19`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:20`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:21`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:24`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:25`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:28`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:30`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:32`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:35`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:36`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:37`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:38`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:39`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:40`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:41`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:42`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:43`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:46`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:49`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:50`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/cmds.txt:51`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL2/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.RTL3</strong>：达到返航高度并到家后进入着陆模式。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))`。
- 当前式：`G(enter_rtl_destination_loiter → (G_[0,T_rtl_land) ¬Mode_LAND ∧ F_[T_rtl_land,∞) Mode_LAND))`。
- 官方位置：[docs/en/flight_modes/return.md:183-194](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L183-L194)。到达目的地后先下降到 RTL_DESCEND_ALT 并按 RTL_LAND_DELAY 等待；不是同一采样点立刻 LAND。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = RTL` | 当前飞行模式是返航模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)；Mode_t == NAVIGATION_STATE_AUTO_RTL。  |
| `ALT_t >= RTL_RETURN_ALT` | PX4 当前高度达到或超过返航高度参数。 | 建模对应 | 需要插桩 | `vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。<br>`RTL_RETURN_ALT`，[baseline/px4/src/modules/navigator/rtl_params.c:59](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L59-L59)；当前运行参数值等于 PARAM 协议读取值。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`RTL::_param_rtl_return_alt`，[baseline/px4/src/modules/navigator/rtl.h:236](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.h#L236-L236)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_rtl_return_alt.get()`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L477)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。<br>`_param_rtl_return_alt.get()`，[baseline/px4/src/modules/navigator/rtl.cpp:530](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L530-L530)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `Pos_t = home_position` | 当前位置等于返航参考位置。 | 建模对应 | 可直接观测 | `vehicle_global_position.lat,lon`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；读取 lat/lon 且 lat_lon_valid=true。 检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。<br>`home_position.lat,lon`，[baseline/px4/msg/versioned/HomePosition.msg:7](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/HomePosition.msg#L7-L7)；读取 Home 经纬度且 valid_hpos=true。 检查 timestamp、valid_hpos 和 update_count。 |
| `Mode_t = LAND` | 当前飞行模式是着陆模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND`，[baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54)；Mode_t == NAVIGATION_STATE_AUTO_LAND。  |

**公式参数**

- 论文 `None` → 当前 `RTL_RETURN_ALT`；默认 `60.0`，冻结 SITL `30.0`，单位 `m`，范围 `0.0..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）51 条：
  - `Flight_Mode,5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:2`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:3`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:4`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:5`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:6`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:7`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:8`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:9`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:10`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:11`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:12`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:13`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:16`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:17`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:18`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:19`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:20`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:21`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:24`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:25`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:28`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:30`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:32`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:35`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:36`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:37`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:38`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:39`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:40`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:41`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:42`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:43`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:46`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:49`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:50`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/cmds.txt:51`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL3/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.RTL4</strong>：RTL_LAND_DELAY 为负一时在 RTL_DESCEND_ALT 高度盘旋。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G(((Mode_t = RTL) & (RTL_DESCEND_ALT = -1)) -> ((Pos_t = Pos_t-1) & (ALT_t = ALT_t-1)))`。
- 当前式：`G((Mode=RTL ∧ runtime(RTL_LAND_DELAY)=-1 ∧ at_descent_altitude) → loiter_at_destination)`。
- 官方位置：[docs/en/flight_modes/return.md:183-194](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes/return.md#L183-L194)。论文自然语言写 RTL_LAND_DELAY=-1，印刷公式却写 RTL_DESCEND_ALT=-1；当前应使用 RTL_LAND_DELAY。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = RTL` | 当前飞行模式是返航模式。 | 建模对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_RTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:41](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L41-L41)；Mode_t == NAVIGATION_STATE_AUTO_RTL。  |
| `RTL_DESCEND_ALT = -1` | 论文公式错误地把返航下降高度参数与负一比较。 | 建模对应 | 可直接观测 | `RTL_DESCEND_ALT`，[baseline/px4/src/modules/navigator/rtl_params.c:75](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L75-L75)；当前运行参数值等于 PARAM 协议读取值。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`RtlDirect::_param_rtl_descend_alt`，[baseline/px4/src/modules/navigator/rtl_direct.h:176](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.h#L176-L176)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_rtl_descend_alt.get()`，[baseline/px4/src/modules/navigator/rtl_direct.cpp:587](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L587-L587)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `RTL_LAND_DELAY = -1` | PX4 返航着陆等待参数为负一，表示不着陆而保持盘旋。 | 建模对应 | 可直接观测 | `RTL_LAND_DELAY`，[baseline/px4/src/modules/navigator/rtl_params.c:89](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_params.c#L89-L89)；读取当前延迟；-1 明确定义为不着陆并在 RTL_DESCEND_ALT 盘旋。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`RtlDirect::_param_rtl_land_delay`，[baseline/px4/src/modules/navigator/rtl_direct.h:177](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.h#L177-L177)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_rtl_land_delay.get()`，[baseline/px4/src/modules/navigator/rtl_direct.cpp:166](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L166-L166)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。<br>`_param_rtl_land_delay.get()`，[baseline/px4/src/modules/navigator/rtl_direct.cpp:307](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L307-L307)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。<br>`_param_rtl_land_delay.get() < -FLT_EPSILON`，[baseline/px4/src/modules/navigator/rtl_direct.cpp:309](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl_direct.cpp#L309-L309)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | 建模对应 | 可计算得到 | `vehicle_global_position.lat,lon`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；读取 lat/lon 且 lat_lon_valid=true。 检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。<br>`previous_accepted(vehicle_global_position.lat,lon)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；取同一数据源、同一坐标系的前一个已接受有效样本。 必须与当前 Pos_t 使用同一候选组；拒绝跨 xy/lat_lon reset counter 的样本。 |
| `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | 建模对应 | 需要插桩 | `previous_accepted(current AMSL-selected RTL destination AMSL)`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L477)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。<br>`vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。 |

**公式参数**

- 论文 `None` → 当前 `RTL_DESCEND_ALT`；默认 `30.0`，冻结 SITL `10.0`，单位 `m`，范围 `0.0..`；配置是否飞行中即时生效未实测。
- 论文 `None` → 当前 `RTL_LAND_DELAY`；默认 `0.0`，冻结 SITL `0.0`，单位 `s`，范围 `-1.0..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）51 条：
  - `Flight_Mode,5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:2`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:3`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:4`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:5`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:6`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:7`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:8`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:9`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:10`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:11`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:12`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:13`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:16`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:17`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:18`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:19`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:20`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:21`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:24`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:25`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:28`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:30`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:32`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:35`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:36`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:37`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:38`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:39`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:40`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:41`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:42`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:43`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:46`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:49`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:50`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/cmds.txt:51`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL4/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.RTL5</strong>：与 A.RTL4 相同：着陆触地后锁定电机。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`It is the same as A.RTL4.`。
- 当前式：`G((landed_start ∧ runtime(COM_DISARM_LAND)>0) → (G_[0,T_disarm) armed ∧ F_[T_disarm,∞) disarmed))`。
- 官方位置：[docs/en/flight_modes_mc/land.md:23-37](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/land.md#L23-L37)。当前着陆后自动锁定由 COM_DISARM_LAND 决定，且可禁用，不是无条件同一时刻锁定。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = LAND` | 当前飞行模式是着陆模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND`，[baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54)；Mode_t == NAVIGATION_STATE_AUTO_LAND。  |
| `ALT_t = GroundALT` | 当前高度严格等于论文所称地面高度。 | 无法确认 | 无法确认 | `vehicle_global_position.alt - selected RTL destination altitude`，[baseline/px4/src/modules/navigator/rtl.cpp:477](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/rtl.cpp#L477-L530)；RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。 必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。<br>`no type-compatible numeric GroundALT definition`，无可靠源码位置；论文没有给 GroundALT 的数值类型、参考面或容差，不能把 vehicle_land_detected.landed 布尔量代入高度等式。 补充数值地面参考定义或明确改写为 landed 布尔性质前不判真。 |
| `Disarm = on` | 电机处于锁定状态。 | 精确对应 | 可直接观测 | `vehicle_status.arming_state == ARMING_STATE_DISARMED`，[baseline/px4/msg/versioned/VehicleStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L10-L10)；arming_state 等于 ARMING_STATE_DISARMED。 <br>`vehicle_status_s::ARMING_STATE_DISARMED`，[baseline/px4/msg/versioned/VehicleStatus.msg:11](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L11-L11)；Disarm 的主状态比较值为 ARMING_STATE_DISARMED。 <br>`actuator_armed.armed == false`，[baseline/px4/msg/ActuatorArmed.msg:3](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/ActuatorArmed.msg#L3-L3)；执行器武装字段为 false。  |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）51 条：
  - `Flight_Mode,5`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:2`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:3`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:4`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:5`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:6`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:7`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:8`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:9`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:10`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:11`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:12`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:13`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:16`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:17`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:18`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:19`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:20`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:21`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:24`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:25`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:28`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:30`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:32`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:35`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:36`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:37`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:38`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:39`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:40`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:41`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:42`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:43`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:46`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:49`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:50`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/cmds.txt:51`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.RTL5/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ORBIT1</strong>：继承 A.CIRCLE1，并把绕圈模式解释为 PX4 ORBIT。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`It is the same as A.CIRCLE1.`。
- 当前式：`G((Mode=ORBIT ∧ orbit_active ∧ pitch_radius_decrease) → commanded_radius_decreases)`。
- 官方位置：[docs/en/flight_modes_mc/orbit.md:27-50](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L27-L50)。当前俯仰杆改变环绕半径，中心杆锁定当前半径；必须加入已启动 Orbit 和有效 RC 前提。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ORBIT`，[baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)；Mode_t == NAVIGATION_STATE_ORBIT。  |
| `RC_pitch < 1500` | 俯仰遥控输入小于通道中值。 | 建模对应 | 条件可观测 | `input_rc.values[RC_MAP_PITCH-1]`，[baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)；论文与 1500 比较时使用当前 RC_MAP 选择的原始俯仰通道。 RC_MAP 必须有效；检查 rc_lost、rc_failsafe、timestamp_last_signal。<br>`RCUpdate::_rc.function[FUNCTION_PITCH] = RC_MAP_PITCH - 1`，[baseline/px4/src/modules/rc_update/rc_update.cpp:195](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L195-L195)；当前 RC_MAP_PITCH 参数减一得到俯仰功能对应的 values[] 索引。 参数值必须在有效通道范围内，并与当前 channel_count 联合检查。 |
| `Circle_radius_t > 0` | 当前绕圈半径为正数。 | 建模对应 | 需要插桩 | `FlightTaskOrbit::_orbit_radius`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)；读取内部无符号目标半径。 只在当前 ORBIT 任务实例激活时有效。<br>`fabs(orbit_status.radius)`，[baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10)；取发布的带符号半径绝对值。 按 orbit_status.timestamp/ORBIT_EXECUTION_STATUS.time_usec 检查新鲜度。 |
| `Circle_radius_t < Circle_radius_t-1` | 绕圈半径比上一观测减小。 | 建模对应 | 需要插桩 | `FlightTaskOrbit::_orbit_radius`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)；读取内部无符号目标半径。 只在当前 ORBIT 任务实例激活时有效。<br>`fabs(orbit_status.radius)`，[baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10)；取发布的带符号半径绝对值。 按 orbit_status.timestamp/ORBIT_EXECUTION_STATUS.time_usec 检查新鲜度。<br>`previous_accepted(fabs(orbit_status.radius))`，[baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10)；取同一数据源、同一坐标系的前一个已接受有效样本。 只接受同一 ORBIT 实例且发送时间递增的样本。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）9 条：
  - `Flight_Mode,7`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:2`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:3`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:4`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:5`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:6`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:7`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:8`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/cmds.txt:9`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ORBIT2</strong>：继承 A.CIRCLE2，并把绕圈模式解释为 PX4 ORBIT。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`It is the same as A.CIRCLE2.`。
- 当前式：`G((Mode=ORBIT ∧ orbit_active ∧ pitch_radius_increase) → commanded_radius_increases)`。
- 官方位置：[docs/en/flight_modes_mc/orbit.md:27-50](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L27-L50)。当前俯仰杆改变环绕半径，方向需按当前手册解释。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ORBIT`，[baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)；Mode_t == NAVIGATION_STATE_ORBIT。  |
| `RC_pitch > 1500` | 俯仰遥控输入大于通道中值。 | 建模对应 | 条件可观测 | `input_rc.values[RC_MAP_PITCH-1]`，[baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)；论文与 1500 比较时使用当前 RC_MAP 选择的原始俯仰通道。 RC_MAP 必须有效；检查 rc_lost、rc_failsafe、timestamp_last_signal。<br>`RCUpdate::_rc.function[FUNCTION_PITCH] = RC_MAP_PITCH - 1`，[baseline/px4/src/modules/rc_update/rc_update.cpp:195](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L195-L195)；当前 RC_MAP_PITCH 参数减一得到俯仰功能对应的 values[] 索引。 参数值必须在有效通道范围内，并与当前 channel_count 联合检查。 |
| `Circle_radius_t > Circle_radius_t-1` | 绕圈半径比上一观测增大。 | 建模对应 | 需要插桩 | `FlightTaskOrbit::_orbit_radius`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)；读取内部无符号目标半径。 只在当前 ORBIT 任务实例激活时有效。<br>`fabs(orbit_status.radius)`，[baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10)；取发布的带符号半径绝对值。 按 orbit_status.timestamp/ORBIT_EXECUTION_STATUS.time_usec 检查新鲜度。<br>`previous_accepted(fabs(orbit_status.radius))`，[baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10)；取同一数据源、同一坐标系的前一个已接受有效样本。 只接受同一 ORBIT 实例且发送时间递增的样本。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）9 条：
  - `Flight_Mode,7`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:2`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:3`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:4`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:5`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:6`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:7`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:8`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/cmds.txt:9`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT2/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ORBIT3</strong>：继承 A.CIRCLE3，并把绕圈模式解释为 PX4 ORBIT。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`It is the same as A.CIRCLE3.`。
- 当前式：`G((Mode=ORBIT ∧ orbit_active ∧ roll_accel_clockwise) → commanded_tangential_acceleration_clockwise)`。
- 官方位置：[docs/en/flight_modes_mc/orbit.md:38-50](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L38-L50)。横滚杆控制环绕加速度、速度和方向；不能仅用相邻速度样本严格单调代替控制目标。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ORBIT`，[baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)；Mode_t == NAVIGATION_STATE_ORBIT。  |
| `RC_roll > 1500` | 横滚遥控输入大于通道中值。 | 建模对应 | 条件可观测 | `input_rc.values[RC_MAP_ROLL-1]`，[baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)；论文与 1500 比较时使用当前 RC_MAP 选择的原始横滚通道。 RC_MAP 必须有效；检查 rc_lost、rc_failsafe、timestamp_last_signal。<br>`RCUpdate::_rc.function[FUNCTION_ROLL] = RC_MAP_ROLL - 1`，[baseline/px4/src/modules/rc_update/rc_update.cpp:194](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L194-L194)；当前 RC_MAP_ROLL 参数减一得到横滚功能对应的 values[] 索引。 参数值必须在有效通道范围内，并与当前 channel_count 联合检查。 |
| `Circle_direction_t = clockwise` | 绕圈方向是顺时针。 | 建模对应 | 可直接观测 | `sign(orbit_status.radius)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:138](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp#L138-L138)；radius>0 表示顺时针，radius<0 表示逆时针。 消息必须属于当前 ORBIT 实例；发布端 signNoZero 在 _orbit_velocity==0 时仍编码正半径，因此正号只是目标/编码方向，不证明正在运动。<br>`sign(FlightTaskOrbit::_orbit_velocity)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；内部目标圆周速度的符号决定旋转方向，并在发布 orbit_status.radius 时编码到半径符号。 只在当前 ORBIT 任务实例激活且 _orbit_velocity 非零时有方向意义。<br>`FlightTaskOrbit::applyCommandParameters(): command.param1 sign -> _orbit_velocity`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:68](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp#L68-L68)；ORBIT 命令 param1 的符号选方向，param2 提供速度大小，最后写入带符号 _orbit_velocity。 参数必须为有限数并通过半径范围检查。<br>`MavlinkStreamOrbitStatus::send()`，[baseline/px4/src/modules/mavlink/streams/ORBIT_EXECUTION_STATUS.hpp:70](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/ORBIT_EXECUTION_STATUS.hpp#L70-L70)；将 orbit_status.radius 保持符号发送为 ORBIT_EXECUTION_STATUS.radius。 按 orbit_status.timestamp 关联当前 ORBIT 实例。 |
| `Circle_speed_t > Circle_speed_t-1` | 绕圈速度比上一观测增大。 | 建模对应 | 需要插桩 | `fabs(FlightTaskOrbit::_orbit_velocity)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；若论文 speed 指内部目标圆周速度，则取 _orbit_velocity 绝对值。 只在 ORBIT 激活时有效，并保留方向符号供 direction 命题使用。<br>`previous_accepted(fabs(FlightTaskOrbit::_orbit_velocity))`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后必须与当前 Circle_speed_t 使用同一候选组；不能混用目标速度和实际地速。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）9 条：
  - `Flight_Mode,7`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:2`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:3`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:4`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:5`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:6`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:7`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:8`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/cmds.txt:9`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT3/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ORBIT4</strong>：继承 A.CIRCLE4，并把绕圈模式解释为 PX4 ORBIT。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`It is the same as A.CIRCLE4.`。
- 当前式：`G((Mode=ORBIT ∧ orbit_active ∧ roll_accel_counterclockwise) → commanded_tangential_acceleration_counterclockwise)`。
- 官方位置：[docs/en/flight_modes_mc/orbit.md:38-50](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L38-L50)。横滚杆控制顺/逆时针加速度，必须保留方向和限幅上下文。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ORBIT`，[baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)；Mode_t == NAVIGATION_STATE_ORBIT。  |
| `RC_roll > 1500` | 横滚遥控输入大于通道中值。 | 建模对应 | 条件可观测 | `input_rc.values[RC_MAP_ROLL-1]`，[baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)；论文与 1500 比较时使用当前 RC_MAP 选择的原始横滚通道。 RC_MAP 必须有效；检查 rc_lost、rc_failsafe、timestamp_last_signal。<br>`RCUpdate::_rc.function[FUNCTION_ROLL] = RC_MAP_ROLL - 1`，[baseline/px4/src/modules/rc_update/rc_update.cpp:194](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L194-L194)；当前 RC_MAP_ROLL 参数减一得到横滚功能对应的 values[] 索引。 参数值必须在有效通道范围内，并与当前 channel_count 联合检查。 |
| `Circle_direction_t = counterclockwise` | 绕圈方向是逆时针。 | 建模对应 | 可直接观测 | `sign(orbit_status.radius)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:138](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp#L138-L138)；radius>0 表示顺时针，radius<0 表示逆时针。 消息必须属于当前 ORBIT 实例；发布端 signNoZero 在 _orbit_velocity==0 时仍编码正半径，因此正号只是目标/编码方向，不证明正在运动。<br>`sign(FlightTaskOrbit::_orbit_velocity)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；内部目标圆周速度的符号决定旋转方向，并在发布 orbit_status.radius 时编码到半径符号。 只在当前 ORBIT 任务实例激活且 _orbit_velocity 非零时有方向意义。<br>`FlightTaskOrbit::applyCommandParameters(): command.param1 sign -> _orbit_velocity`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:68](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp#L68-L68)；ORBIT 命令 param1 的符号选方向，param2 提供速度大小，最后写入带符号 _orbit_velocity。 参数必须为有限数并通过半径范围检查。<br>`MavlinkStreamOrbitStatus::send()`，[baseline/px4/src/modules/mavlink/streams/ORBIT_EXECUTION_STATUS.hpp:70](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/ORBIT_EXECUTION_STATUS.hpp#L70-L70)；将 orbit_status.radius 保持符号发送为 ORBIT_EXECUTION_STATUS.radius。 按 orbit_status.timestamp 关联当前 ORBIT 实例。 |
| `Circle_speed_t < Circle_speed_t-1` | 绕圈速度比上一观测减小。 | 建模对应 | 需要插桩 | `fabs(FlightTaskOrbit::_orbit_velocity)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；若论文 speed 指内部目标圆周速度，则取 _orbit_velocity 绝对值。 只在 ORBIT 激活时有效，并保留方向符号供 direction 命题使用。<br>`previous_accepted(fabs(FlightTaskOrbit::_orbit_velocity))`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后必须与当前 Circle_speed_t 使用同一候选组；不能混用目标速度和实际地速。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）9 条：
  - `Flight_Mode,7`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:2`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:3`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:4`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:5`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:6`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:7`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:8`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:9`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ORBIT5</strong>：绕点飞行最大半径为 100 米。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G((Mode_t = ORBIT) -> (Circle_radius_t < 100))`。
- 当前式：`G(Mode=ORBIT → commanded_radius≤runtime(MC_ORBIT_RAD_MAX))`。
- 官方位置：[docs/en/flight_modes_mc/orbit.md:60-66](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L60-L66)。当前 MC_ORBIT_RAD_MAX 默认 1000 m，论文固定 100 m 已过时。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ORBIT`，[baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)；Mode_t == NAVIGATION_STATE_ORBIT。  |
| `Circle_radius_t < 100m` | 论文抽象的绕点半径严格小于 100 米。 | 建模对应 | 需要插桩 | `FlightTaskOrbit::_orbit_radius`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L119-L119)；读取内部无符号目标半径。 只在当前 ORBIT 任务实例激活时有效。<br>`fabs(orbit_status.radius)`，[baseline/px4/msg/OrbitStatus.msg:10](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/OrbitStatus.msg#L10-L10)；取发布的带符号半径绝对值。 按 orbit_status.timestamp/ORBIT_EXECUTION_STATUS.time_usec 检查新鲜度。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）9 条：
  - `Flight_Mode,7`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:2`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:3`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:4`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:5`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:6`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:7`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:8`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/cmds.txt:9`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT4_5/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ORBIT6</strong>：绕点飞行最大加速度限制为每平方秒 2 米。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G((Mode_t = ORBIT) -> (Circle_speed_t < 2m/s^2))`。
- 当前式：`G(Mode=ORBIT → centripetal_acceleration≤2m/s²)`。
- 官方位置：[docs/en/flight_modes_mc/orbit.md:69-80](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/orbit.md#L69-L80)。官方限制向心加速度为 2 m/s²；论文公式却把 Circle_speed 与加速度单位比较，量纲错误。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | 建模对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ORBIT`，[baseline/px4/msg/versioned/VehicleStatus.msg:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L57-L57)；Mode_t == NAVIGATION_STATE_ORBIT。  |
| `Circle_speed_t < 2m/s^2` | 论文用速度变量与加速度单位阈值比较。 | 建模对应 | 需要插桩 | `fabs(FlightTaskOrbit::_orbit_velocity)`，[baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp#L118-L118)；若论文 speed 指内部目标圆周速度，则取 _orbit_velocity 绝对值。 只在 ORBIT 激活时有效，并保留方向符号供 direction 命题使用。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）9 条：
  - `Flight_Mode,7`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:2`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:3`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:4`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:5`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:6`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:7`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:8`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/cmds.txt:9`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ORBIT6/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.LAND1</strong>：下降速度等于 MPC_LAND_SPEED 参数。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`G((Mode_t = LAND) -> (Speed_vertical_t = MPC_LAND_SPEED))`。
- 当前式：`G(Mode=LAND → commanded_descent_rate=runtime(MPC_LAND_SPEED))`。
- 官方位置：[docs/en/flight_modes_mc/land.md:23-37](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/land.md#L23-L37)。MPC_LAND_SPEED 是下降目标速率；实际速度不要求每个样本严格等于参数。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = LAND` | 当前飞行模式是着陆模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND`，[baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54)；Mode_t == NAVIGATION_STATE_AUTO_LAND。  |
| `Speed_vertical_t = MPC_LAND_SPEED` | 垂直速度严格等于 PX4 着陆速度参数。 | 建模对应 | 可直接观测 | `vehicle_local_position.vz`，[baseline/px4/msg/versioned/VehicleLocalPosition.msg:28](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L28-L28)；着陆下降速率取 +vz；起飞上升速率取 -vz；要求 v_z_valid。 检查 timestamp、v_z_valid 和 vz_reset_counter。<br>`MPC_LAND_SPEED`，[baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c:111](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c#L111-L111)；读取当前着陆下降速率配置；实际 setpoint 还会插值或使用 crawl 速率。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`FlightTaskAuto::_param_mpc_land_speed`，[baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp:169](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp#L169-L169)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_mpc_land_speed.get()`，[baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp:234](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp#L234-L234)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。<br>`_param_mpc_land_speed.get()`，[baseline/px4/src/modules/flight_mode_manager/tasks/Descend/FlightTaskDescend.cpp:52](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Descend/FlightTaskDescend.cpp#L52-L52)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |

**公式参数**

- 论文 `None` → 当前 `MPC_LAND_SPEED`；默认 `0.7`，冻结 SITL `0.699999988079071`，单位 `m/s`，范围 `0.6..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）53 条：
  - `Flight_Mode,6`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,11`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:37`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:39`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:40`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:41`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:42`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:43`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:44`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:47`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:50`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:51`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:52`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/cmds.txt:53`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.LAND1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.ALTITUDE1</strong>：继承 A.ALT_HOLD2，并把模式解释为 PX4 ALTITUDE。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`It is the same as A.ALT_HOLD2.`。
- 当前式：`G((Mode=ALTITUDE ∧ throttle_in_deadzone) → altitude_setpoint_held)`。
- 官方位置：[docs/en/flight_modes_mc/altitude.md:20-50](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/altitude.md#L20-L50)。中位油门保持当前高度，死区与有效高度估计是前提；不是原始 PWM 恰等于 1500 的物理恒等式。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = ALTITUDE` | 当前 PX4 模式是高度控制模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ALTCTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:37](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L37-L37)；Mode_t == NAVIGATION_STATE_ALTCTL。  |
| `Throttle_t = 1500` | 油门输入严格等于通道中值 1500。 | 建模对应 | 条件可观测 | `input_rc.values[RC_MAP_THROTTLE-1]`，[baseline/px4/src/modules/rc_update/rc_update.cpp:440](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L440-L440)；论文与 1500 比较时使用当前 RC_MAP 选择的原始油门通道。 RC_MAP 必须有效；检查 rc_lost、rc_failsafe、timestamp_last_signal。<br>`RCUpdate::_rc.function[FUNCTION_THROTTLE] = RC_MAP_THROTTLE - 1`，[baseline/px4/src/modules/rc_update/rc_update.cpp:193](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/rc_update/rc_update.cpp#L193-L193)；当前 RC_MAP_THROTTLE 参数减一得到油门功能对应的 values[] 索引。 参数值必须在有效通道范围内，并与当前 channel_count 联合检查。 |
| `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | 建模对应 | 条件可观测 | `previous_accepted(vehicle_global_position.alt)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。<br>`vehicle_global_position.alt`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)；读取 alt 且 alt_valid=true。 检查 timestamp、timestamp_sample、alt_valid 和 alt_reset_counter。<br>`EKF2::PublishGlobalPosition(): lla.altitude(), alt_valid, alt_reset_counter`，[baseline/px4/src/modules/ekf2/EKF2.cpp:1200](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/ekf2/EKF2.cpp#L1200-L1212)；由 EKF 的 WGS84 高度形成 alt，并分别发布垂直有效位和重置计数。 判真必须同时订阅 alt_valid、alt_reset_counter、timestamp 和 timestamp_sample。<br>`MavlinkStreamGlobalPositionInt::send(): msg.alt = gpos.alt * 1000`，[baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:87](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp#L87-L87)；将 gpos.alt 编码到 GLOBAL_POSITION_INT.alt。 发送函数没有把 gpos.alt_valid 和 alt_reset_counter 一同编码。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,6`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:2`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:3`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:4`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:5`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:6`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:7`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:8`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:9`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:10`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:11`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:18`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:19`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:20`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:21`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:24`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:25`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:28`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:30`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:32`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:35`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:36`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.ALTITUDE1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.POSITION1</strong>：位置控制模式保持位置不变。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`G((Mode_t = POSITION) -> (Pos_t = Pos_t-1))`。
- 当前式：`G((Mode=POSITION ∧ sticks_centered) → position_setpoint_held)`。
- 官方位置：[docs/en/flight_modes_mc/position.md:20-62](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/position.md#L20-L62)。摇杆居中时保持位置；有飞手输入时位置应改变，论文漏掉前提。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = POSITION` | 当前 PX4 模式是位置控制模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_POSCTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:38](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L38-L38)；Mode_t == NAVIGATION_STATE_POSCTL。  |
| `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | 建模对应 | 可计算得到 | `vehicle_global_position.lat,lon`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；读取 lat/lon 且 lat_lon_valid=true。 检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。<br>`previous_accepted(vehicle_global_position.lat,lon)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；取同一数据源、同一坐标系的前一个已接受有效样本。 必须与当前 Pos_t 使用同一候选组；拒绝跨 xy/lat_lon reset counter 的样本。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,2`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,3`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.POSITION1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.HOLD1</strong>：继承 A.LOITER1，并把模式解释为 PX4 HOLD。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`It is the same as A.LOITER1.`。
- 当前式：`G(enter_HOLD → F_[0,∞) hold_position_or_loiter)`。
- 官方位置：[docs/en/flight_modes_mc/hold.md:20-48](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/hold.md#L20-L48)。Hold 是自动悬停/盘旋行为，不能直接继承 ArduPilot LOITER 的摇杆语义。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = HOLD` | 当前 PX4 模式是保持模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_LOITER`，[baseline/px4/msg/versioned/VehicleStatus.msg:40](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L40-L40)；Mode_t == NAVIGATION_STATE_AUTO_LOITER。  |
| `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | 建模对应 | 可计算得到 | `vehicle_global_position.lat,lon`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；读取 lat/lon 且 lat_lon_valid=true。 检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。<br>`previous_accepted(vehicle_global_position.lat,lon)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L13-L13)；取同一数据源、同一坐标系的前一个已接受有效样本。 必须与当前 Pos_t 使用同一候选组；拒绝跨 xy/lat_lon reset counter 的样本。 |
| `Yaw_t = Yaw_t-1` | 当前偏航与上一观测严格相等。 | 建模对应 | 可计算得到 | `vehicle_local_position.heading`，[baseline/px4/msg/versioned/VehicleLocalPosition.msg:42](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L42-L42)；读取 heading，并要求 heading_good_for_control。 检查 timestamp 和 heading_reset_counter；使用环形角差。<br>`previous_accepted(vehicle_local_position.heading)`，[baseline/px4/msg/versioned/VehicleLocalPosition.msg:42](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L42-L42)；取同一数据源、同一坐标系的前一个已接受有效样本。 只接受 heading_reset_counter 未变化的有序有效样本，并用环形角差。 |
| `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | 建模对应 | 条件可观测 | `previous_accepted(vehicle_global_position.alt)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。<br>`vehicle_global_position.alt`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)；读取 alt 且 alt_valid=true。 检查 timestamp、timestamp_sample、alt_valid 和 alt_reset_counter。<br>`EKF2::PublishGlobalPosition(): lla.altitude(), alt_valid, alt_reset_counter`，[baseline/px4/src/modules/ekf2/EKF2.cpp:1200](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/ekf2/EKF2.cpp#L1200-L1212)；由 EKF 的 WGS84 高度形成 alt，并分别发布垂直有效位和重置计数。 判真必须同时订阅 alt_valid、alt_reset_counter、timestamp 和 timestamp_sample。<br>`MavlinkStreamGlobalPositionInt::send(): msg.alt = gpos.alt * 1000`，[baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:87](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp#L87-L87)；将 gpos.alt 编码到 GLOBAL_POSITION_INT.alt。 发送函数没有把 gpos.alt_valid 和 alt_reset_counter 一同编码。 |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,2`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,3`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.HOLD2</strong>：最小盘旋高度启用且当前高度低于它时爬升到该高度。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`G(((Mode_t = HOLD) & (MIS_LTRMIN_ALT != -1)) -> (ALT_t > ALT_t-1))`。
- 当前式：`G((enter_HOLD ∧ runtime(MIS_LTRMIN_ALT)≠-1 ∧ ALT<minimum_hold_altitude) → F_[0,∞) ALT≥minimum_hold_altitude)`。
- 官方位置：[docs/en/flight_modes_mc/hold.md:35-48](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/hold.md#L35-L48)。MIS_LTRMIN_ALT 当前决定进入 Hold 时的最低高度，但 -1 禁用、参考高度和达到过程必须保留。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Mode_t = HOLD` | 当前 PX4 模式是保持模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_LOITER`，[baseline/px4/msg/versioned/VehicleStatus.msg:40](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L40-L40)；Mode_t == NAVIGATION_STATE_AUTO_LOITER。  |
| `MIS_LTRMIN_ALT != -1` | 最小盘旋高度参数没有使用禁用值负一。 | 建模对应 | 可直接观测 | `NAV_MIN_LTR_ALT`，[baseline/px4/src/modules/navigator/navigator_params.c:192](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator_params.c#L192-L192)；读取当前语义后继 NAV_MIN_LTR_ALT；负值表示禁用。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`Navigator::_param_min_ltr_alt`，[baseline/px4/src/modules/navigator/navigator.h:437](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator.h#L437-L437)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`Navigator::get_loiter_min_alt()`，[baseline/px4/src/modules/navigator/mission_block.cpp:727](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_block.cpp#L727-L727)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `ALT_t < MIS_LTRMIN_ALT` | 当前高度低于最小盘旋高度参数；该前件来自论文自然语言但被印刷公式遗漏。 | 建模对应 | 条件可观测 | `vehicle_global_position.alt - home_position.alt`，[baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:77](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp#L77-L77)；当 Home 高度有效时，用全球高度减 Home 高度。 要求 gpos.alt_valid、home.valid_alt 和同一时间基准。<br>`NAV_MIN_LTR_ALT`，[baseline/px4/src/modules/navigator/navigator_params.c:192](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator_params.c#L192-L192)；读取当前语义后继 NAV_MIN_LTR_ALT；负值表示禁用。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`Navigator::_param_min_ltr_alt`，[baseline/px4/src/modules/navigator/navigator.h:437](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator.h#L437-L437)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`Navigator::get_loiter_min_alt()`，[baseline/px4/src/modules/navigator/mission_block.cpp:727](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_block.cpp#L727-L727)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `ALT_t-1 < ALT_t` | 当前观测高度高于上一观测高度。 | 建模对应 | 条件可观测 | `previous_accepted(vehicle_global_position.alt)`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)；取同一数据源、同一坐标系的前一个已接受有效样本。 前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。<br>`vehicle_global_position.alt`，[baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleGlobalPosition.msg#L15-L15)；读取 alt 且 alt_valid=true。 检查 timestamp、timestamp_sample、alt_valid 和 alt_reset_counter。<br>`EKF2::PublishGlobalPosition(): lla.altitude(), alt_valid, alt_reset_counter`，[baseline/px4/src/modules/ekf2/EKF2.cpp:1200](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/ekf2/EKF2.cpp#L1200-L1212)；由 EKF 的 WGS84 高度形成 alt，并分别发布垂直有效位和重置计数。 判真必须同时订阅 alt_valid、alt_reset_counter、timestamp 和 timestamp_sample。<br>`MavlinkStreamGlobalPositionInt::send(): msg.alt = gpos.alt * 1000`，[baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:87](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp#L87-L87)；将 gpos.alt 编码到 GLOBAL_POSITION_INT.alt。 发送函数没有把 gpos.alt_valid 和 alt_reset_counter 一同编码。 |
| `Target_ALT = MIS_LTRMIN_ALT` | 目标高度等于最小盘旋高度参数；该目标来自论文自然语言，印刷公式只保留了上升趋势。 | 建模对应 | 可计算得到 | `position_setpoint_triplet.current.alt - home_position.alt`，[baseline/px4/src/modules/mavlink/streams/POSITION_TARGET_GLOBAL_INT.hpp:75](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/streams/POSITION_TARGET_GLOBAL_INT.hpp#L75-L84)；HOLD 最小高度参数以 Home 为参考时，用当前目标 AMSL 减 Home AMSL 后与 NAV_MIN_LTR_ALT 比较。 要求 setpoint、Home 和消息有效且属于同一 HOLD 实例；还要记录多旋翼 braking 路径可能绕过最小高度逻辑。<br>`NAV_MIN_LTR_ALT`，[baseline/px4/src/modules/navigator/navigator_params.c:192](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator_params.c#L192-L192)；读取当前语义后继 NAV_MIN_LTR_ALT；负值表示禁用。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`Navigator::_param_min_ltr_alt`，[baseline/px4/src/modules/navigator/navigator.h:437](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator.h#L437-L437)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`Navigator::get_loiter_min_alt()`，[baseline/px4/src/modules/navigator/mission_block.cpp:727](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_block.cpp#L727-L727)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |

**公式参数**

- 论文 `None` → 当前 `NAV_MIN_LTR_ALT`；默认 `-1.0`，冻结 SITL `-1.0`，单位 `m`，范围 `-1.0..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,2`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,3`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.HOLD2/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.TAKEOFF1</strong>：执行起飞命令时目标高度应等于 MIS_TAKEOFF_ALT。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`G((Command_t = takeoff) -> (ALT_t <= MIS_TAKEOFF_ALT))`。
- 当前式：`G(accepted_takeoff → F_[0,∞) target_altitude_reached(runtime(MIS_TAKEOFF_ALT)))`。
- 官方位置：[docs/en/flight_modes_mc/takeoff.md:20-44](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/takeoff.md#L20-L44)。起飞目标高度使用 MIS_TAKEOFF_ALT，但公式应表达目标/达到过程，不是所有时刻 ALT≤参数。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Command_t = takeoff` | 当前处理的是起飞命令。 | 建模对应 | 条件可观测 | `vehicle_command.command`，[baseline/px4/msg/versioned/VehicleCommand.msg:190](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L190-L190)；读取当前 vehicle_command.command，并保存 timestamp、source_system 和 source_component。 收到命令不等于接受或执行；应关联 COMMAND_ACK 或后续模式状态。<br>`vehicle_command.param1..param7,source_system,source_component`，[baseline/px4/msg/versioned/VehicleCommand.msg:183](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L183-L196)；对 Command_t 的完整关联需保留 param1–7 和发送端身份；特别是 NAV_TAKEOFF 的 param7 携带绝对目标高度。 该行是命令上下文，不是 command ID 本身；必须与同一 timestamp 和 source 关联。<br>`MavlinkReceiver::handle_message_command_long(): COMMAND_LONG -> vehicle_command`，[baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:484](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L484-L500)；把外部 COMMAND_LONG 的 command、param1–7 和来源身份复制到 vehicle_command，再交给公共处理函数。 保留 from_external、source_system、source_component 和 timestamp；无效参数会在此前拒绝。<br>`MavlinkReceiver::handle_message_command_int(): COMMAND_INT -> vehicle_command`，[baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:520](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L520-L545)；把 COMMAND_INT 参数、缩放后的 x/y、z、命令身份和来源复制到 vehicle_command。 INT32_MAX/NAN 特殊值和来源身份必须与原消息一起保存。<br>`MavlinkReceiver::handle_message_command_both(): publish vehicle_command`，[baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:548](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L548-L753)；公共路径处理本地 microservice 后，在无需立即 ACK 时发布 vehicle_command。 某些命令在 MAVLink 模块内处理并只返回 ACK，不会发布同一 uORB 输入事件。<br>`vehicle_command_s::VEHICLE_CMD_NAV_TAKEOFF`，[baseline/px4/msg/versioned/VehicleCommand.msg:17](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L17-L17)；Command_t == VEHICLE_CMD_NAV_TAKEOFF。  |
| `ALT_t <= MIS_TAKEOFF_ALT` | 当前高度不超过任务起飞高度参数。 | 建模对应 | 可计算得到 | `vehicle_global_position.alt - takeoff-reference altitude captured at command/activation`，[baseline/px4/src/modules/navigator/takeoff.cpp:188](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/takeoff.cpp#L188-L199)；默认起飞目标由当前 AMSL 加 MIS_TAKEOFF_ALT 形成；监视时应在同一起飞实例捕获参考高度后计算相对高度。 必须关联同一 TAKEOFF 命令/模式实例；若命令已提供绝对目标高度，则默认参数路径不适用。<br>`MIS_TAKEOFF_ALT`，[baseline/px4/src/modules/navigator/mission_params.c:58](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_params.c#L58-L58)；读取未另行指定目标时使用的默认相对起飞高度。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`Navigator::_param_mis_takeoff_alt`，[baseline/px4/src/modules/navigator/navigator.h:442](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator.h#L442-L442)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`Navigator::get_param_mis_takeoff_alt()`，[baseline/px4/src/modules/navigator/takeoff.cpp:188](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/takeoff.cpp#L188-L188)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |
| `Target_ALT = MIS_TAKEOFF_ALT` | 起飞目标高度等于任务起飞高度参数；该等式来自论文自然语言。 | 建模对应 | 可计算得到 | `position_setpoint_triplet.current.alt - captured takeoff-reference altitude`，[baseline/px4/src/modules/navigator/takeoff.cpp:188](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/takeoff.cpp#L188-L199)；默认起飞路径把当前 AMSL 加 MIS_TAKEOFF_ALT 作为目标；相对目标需减去同一起飞实例捕获的参考高度。 若输入命令已提供有限绝对目标高度，则默认参数等式不适用。<br>`MIS_TAKEOFF_ALT`，[baseline/px4/src/modules/navigator/mission_params.c:58](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/mission_params.c#L58-L58)；读取未另行指定目标时使用的默认相对起飞高度。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`Navigator::_param_mis_takeoff_alt`，[baseline/px4/src/modules/navigator/navigator.h:442](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/navigator.h#L442-L442)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`Navigator::get_param_mis_takeoff_alt()`，[baseline/px4/src/modules/navigator/takeoff.cpp:188](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/navigator/takeoff.cpp#L188-L188)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |

**公式参数**

- 论文 `None` → 当前 `MIS_TAKEOFF_ALT`；默认 `2.5`，冻结 SITL `2.5`，单位 `m`，范围 `0.0..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）53 条：
  - `Flight_Mode,6`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,11`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:37`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:39`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:40`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:41`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:42`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:43`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:44`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:47`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:50`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:51`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:52`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/cmds.txt:53`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.TAKEOFF2</strong>：执行起飞命令时上升速度应等于 MPC_TKO_SPEED。</summary>

- 当前规范状态：**有条件必须满足**。
- 论文原式：`G((Command_t = takeoff) -> (Speed_vertical_t = MPC_TKO_SPEED))`。
- 当前式：`G((takeoff_climb_active) → commanded_climb_rate=runtime(MPC_TKO_SPEED))`。
- 官方位置：[docs/en/flight_modes_mc/takeoff.md:20-44](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/flight_modes_mc/takeoff.md#L20-L44)。MPC_TKO_SPEED 是上升目标速度/上限语义，实测速度不要求逐样本严格相等。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `Command_t = takeoff` | 当前处理的是起飞命令。 | 建模对应 | 条件可观测 | `vehicle_command.command`，[baseline/px4/msg/versioned/VehicleCommand.msg:190](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L190-L190)；读取当前 vehicle_command.command，并保存 timestamp、source_system 和 source_component。 收到命令不等于接受或执行；应关联 COMMAND_ACK 或后续模式状态。<br>`vehicle_command.param1..param7,source_system,source_component`，[baseline/px4/msg/versioned/VehicleCommand.msg:183](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L183-L196)；对 Command_t 的完整关联需保留 param1–7 和发送端身份；特别是 NAV_TAKEOFF 的 param7 携带绝对目标高度。 该行是命令上下文，不是 command ID 本身；必须与同一 timestamp 和 source 关联。<br>`MavlinkReceiver::handle_message_command_long(): COMMAND_LONG -> vehicle_command`，[baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:484](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L484-L500)；把外部 COMMAND_LONG 的 command、param1–7 和来源身份复制到 vehicle_command，再交给公共处理函数。 保留 from_external、source_system、source_component 和 timestamp；无效参数会在此前拒绝。<br>`MavlinkReceiver::handle_message_command_int(): COMMAND_INT -> vehicle_command`，[baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:520](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L520-L545)；把 COMMAND_INT 参数、缩放后的 x/y、z、命令身份和来源复制到 vehicle_command。 INT32_MAX/NAN 特殊值和来源身份必须与原消息一起保存。<br>`MavlinkReceiver::handle_message_command_both(): publish vehicle_command`，[baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:548](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/mavlink_receiver.cpp#L548-L753)；公共路径处理本地 microservice 后，在无需立即 ACK 时发布 vehicle_command。 某些命令在 MAVLink 模块内处理并只返回 ACK，不会发布同一 uORB 输入事件。<br>`vehicle_command_s::VEHICLE_CMD_NAV_TAKEOFF`，[baseline/px4/msg/versioned/VehicleCommand.msg:17](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleCommand.msg#L17-L17)；Command_t == VEHICLE_CMD_NAV_TAKEOFF。  |
| `Speed_vertical_t = MPC_TKO_SPEED` | 垂直速度严格等于 PX4 起飞速度参数。 | 建模对应 | 可直接观测 | `vehicle_local_position.vz`，[baseline/px4/msg/versioned/VehicleLocalPosition.msg:28](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleLocalPosition.msg#L28-L28)；着陆下降速率取 +vz；起飞上升速率取 -vz；要求 v_z_valid。 检查 timestamp、v_z_valid 和 vz_reset_counter。<br>`MPC_TKO_SPEED`，[baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c:57](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c#L57-L57)；读取当前起飞速度约束；不等于每个实际物理样本必须严格相等。 在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。<br>`FlightTaskAuto::_param_mpc_tko_speed`，[baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp:178](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp#L178-L178)；该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。 参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。<br>`_param_mpc_tko_speed.get()`，[baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp:812](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp#L812-L812)；该 .get() 或 getter 调用是当前参数值被使用的具体路径。 只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。 |

**公式参数**

- 论文 `None` → 当前 `MPC_TKO_SPEED`；默认 `1.5`，冻结 SITL `1.5`，单位 `m/s`，范围 `1.0..5.0`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）30 条：
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:1`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:2`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:3`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:4`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:5`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:6`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:7`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:8`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:9`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:10`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:11`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:12`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:13`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:14`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:15`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:16`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:17`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:18`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:19`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:20`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:22`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:23`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:24`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:25`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:26`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:27`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:28`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:29`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/parameters.txt:30`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）53 条：
  - `Flight_Mode,6`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,11`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:37`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:38`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:39`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:40`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:41`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:42`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:43`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:44`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:47`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:50`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:51`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:52`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/cmds.txt:53`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.TAKEOFF2/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.GPS.FS1</strong>：检测到 GPS 丢失后，在 COM_POS_FS_DELAY 加调度余量内触发故障保护。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G((GPS_loss = on) -> F_[0,COM_POS_FS_DELAY+k](GPS_fail = on))`。
- 当前式：`G((position_estimate_invalid_start ∧ position_required) → F_[0,∞) position_loss_failsafe)`。
- 官方位置：[docs/en/config/safety.md:190-211](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/config/safety.md#L190-L211)。历史 COM_POS_FS_DELAY 已删除；当前位置丢失由 EKF2_NOAID_TOUT 和 COM_POS_FS_EPH 等机制组合判断。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `GPS_loss = on` | 论文抽象的 GPS 丢失事件已经发生。 | 建模对应 | 可直接观测 | `sensor_gps.timestamp,fix_type`，[baseline/px4/msg/SensorGps.msg:3](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/SensorGps.msg#L3-L3)；只能在另有来源的 freshness 阈值或最低 fix_type 规则下判定丢失。 论文没有给出 loss 超时和最低 fix_type，不能人工补值。<br>`sensor_gps.fix_type`，[baseline/px4/msg/SensorGps.msg:22](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/SensorGps.msg#L22-L22)；GPS_loss 候选定义需保留修复类型，不能只看时间戳。 最低可接受 fix_type 和超时均未由论文给出。 |
| `F_[0,COM_POS_FS_DELAY+k](GPS_fail = on)` | 在位置故障延迟参数加调度余量内触发 GPS 故障保护。 | 无法确认 | 无法确认 | `failsafe_flags.global_position_invalid`，[baseline/px4/msg/FailsafeFlags.msg:32](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L32-L32)；候选解释：当前全球位置估计无效标志为 true。 该状态可能由 GNSS、视觉、光流等定位链共同决定，不是 GPS 专用故障。<br>`global_position_invalid = !checkPosVelValidity(...) `，[baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp:681](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp#L681-L681)；按当前位置有效性、精度、新鲜度和迟滞逻辑计算。 <br>`COM_POS_FS_DELAY`，[baseline/px4/docs/en/releases/1.16.md:58](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/releases/1.16.md#L58-L58)；当前没有可读取的同名运行参数值。 当前发行说明写明该位置丢失延迟参数已删除。<br>`no current PX4 symbol`，无可靠源码位置；PGFuzz 未公开调度余量操作数和具体数值。  |

**公式参数**

- 论文 `None` → 当前 `COM_POS_FS_DELAY`；默认 ``，冻结 SITL ``，单位 ``，范围 `..`；配置是否飞行中即时生效未实测。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）31 条：
  - `COM_POS_FS_DELAY,X,1,1,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:1`；当前对应 `COM_POS_FS_DELAY`；身份状态按当前证据为“当前定义未找到”。
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:2`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:3`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:4`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:5`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:6`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:7`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:8`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:9`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:10`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:11`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:12`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:13`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:14`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:15`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:16`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:17`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:18`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:19`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:20`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:22`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:23`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:24`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:25`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:26`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:27`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:28`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:29`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:30`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/parameters.txt:31`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,2`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,3`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS1/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.GPS.FS2</strong>：GPS 故障保护触发且遥控可用时进入高度模式。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G(((GPS_fail = on) & (RC_t = on)) -> (Mode_t = ALTITUDE))`。
- 当前式：`G((position_loss_failsafe ∧ height_estimate_valid) → F_[0,∞) Mode=ALTITUDE)`。
- 官方位置：[docs/en/config/safety.md:190-211](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/config/safety.md#L190-L211)。当前多旋翼位置丢失时有高度估计则切 Altitude，否则 Stabilized；不以 RC 可用性作为论文所写的唯一分支。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | 无法确认 | 无法确认 | `failsafe_flags.global_position_invalid`，[baseline/px4/msg/FailsafeFlags.msg:32](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L32-L32)；候选解释：当前全球位置估计无效标志为 true。 该状态可能由 GNSS、视觉、光流等定位链共同决定，不是 GPS 专用故障。<br>`global_position_invalid = !checkPosVelValidity(...) `，[baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp:681](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp#L681-L681)；按当前位置有效性、精度、新鲜度和迟滞逻辑计算。  |
| `RC_t = on` | 遥控器输入被论文抽象为可用。 | 建模对应 | 条件可观测 | `!(input_rc.rc_lost \|\| input_rc.rc_failsafe)`，[baseline/px4/msg/InputRc.msg:29](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L29-L29)；若 RC_t 只指底层接收器链路，则 rc_lost 和 rc_failsafe 均为 false 时候选为 on。 同时检查 timestamp_last_signal 与 input_source；部分接收器在链路丢失后仍发帧，因此两个标志都可能不完整。<br>`input_rc.timestamp_last_signal`，[baseline/px4/msg/InputRc.msg:22](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L22-L22)；物理接收器候选必须确认最后一次有效信号时间仍新鲜。 阈值必须来自当前接收器/检查逻辑，不能用观察端任意秒数。<br>`input_rc.input_source`，[baseline/px4/msg/InputRc.msg:36](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L36-L36)；确认 input_rc 来自哪一种物理接收器或 MAVLink 输入源。 物理 RC 解释需要排除 RC_INPUT_SOURCE_MAVLINK 等非接收器来源。<br>`input_rc.rc_lost`，[baseline/px4/msg/InputRc.msg:30](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L30-L30)；物理 RC 候选还要求 rc_lost==false；该位表示预期时间内未收到帧。 与 rc_failsafe、timestamp_last_signal 和 input_source 联合判定。 |
| `Mode_t = ALTITUDE` | 当前 PX4 模式是高度控制模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_ALTCTL`，[baseline/px4/msg/versioned/VehicleStatus.msg:37](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L37-L37)；Mode_t == NAVIGATION_STATE_ALTCTL。  |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）31 条：
  - `COM_POS_FS_DELAY,X,1,1,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:1`；当前对应 `COM_POS_FS_DELAY`；身份状态按当前证据为“当前定义未找到”。
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:2`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:3`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:4`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:5`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:6`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:7`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:8`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:9`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:10`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:11`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:12`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:13`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:14`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:15`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:16`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:17`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:18`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:19`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:20`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:22`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:23`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:24`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:25`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:26`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:27`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:28`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:29`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:30`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/parameters.txt:31`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,2`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,3`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS2/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

<details><summary><strong>PX.GPS.FS3</strong>：GPS 故障保护触发且遥控不可用时进入着陆模式。</summary>

- 当前规范状态：**需按当前版本改写**。
- 论文原式：`G(((GPS_fail = on) & (RC_t = off)) -> (Mode_t = LAND))`。
- 当前式：`G((position_loss_failsafe ∧ ¬height_estimate_valid) → F_[0,∞) Mode=STABILIZED)`。
- 官方位置：[docs/en/config/safety.md:190-211](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/docs/en/config/safety.md#L190-L211)。当前无高度估计时切 Stabilized，而非简单地因 RC 不可用必然 LAND。
- 实现符合性：**未评估**。

|原子命题|白话真值|对应状态|MAVLink 观测|源码定义、更新、消费或发送位置|
|---|---|---|---|---|
| `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | 无法确认 | 无法确认 | `failsafe_flags.global_position_invalid`，[baseline/px4/msg/FailsafeFlags.msg:32](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/FailsafeFlags.msg#L32-L32)；候选解释：当前全球位置估计无效标志为 true。 该状态可能由 GNSS、视觉、光流等定位链共同决定，不是 GPS 专用故障。<br>`global_position_invalid = !checkPosVelValidity(...) `，[baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp:681](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp#L681-L681)；按当前位置有效性、精度、新鲜度和迟滞逻辑计算。  |
| `RC_t = off` | 遥控器输入被论文抽象为不可用。 | 建模对应 | 条件可观测 | `!(input_rc.rc_lost \|\| input_rc.rc_failsafe)`，[baseline/px4/msg/InputRc.msg:29](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L29-L29)；若 RC_t 只指底层接收器链路，则 rc_lost 和 rc_failsafe 均为 false 时候选为 on。 同时检查 timestamp_last_signal 与 input_source；部分接收器在链路丢失后仍发帧，因此两个标志都可能不完整。<br>`input_rc.timestamp_last_signal`，[baseline/px4/msg/InputRc.msg:22](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L22-L22)；物理接收器候选必须确认最后一次有效信号时间仍新鲜。 阈值必须来自当前接收器/检查逻辑，不能用观察端任意秒数。<br>`input_rc.input_source`，[baseline/px4/msg/InputRc.msg:36](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L36-L36)；确认 input_rc 来自哪一种物理接收器或 MAVLink 输入源。 物理 RC 解释需要排除 RC_INPUT_SOURCE_MAVLINK 等非接收器来源。<br>`input_rc.rc_lost`，[baseline/px4/msg/InputRc.msg:30](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/InputRc.msg#L30-L30)；物理 RC 候选还要求 rc_lost==false；该位表示预期时间内未收到帧。 与 rc_failsafe、timestamp_last_signal 和 input_source 联合判定。 |
| `Mode_t = LAND` | 当前飞行模式是着陆模式。 | 精确对应 | 可直接观测 | `vehicle_status.nav_state`，[baseline/px4/msg/versioned/VehicleStatus.msg:35](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L35-L35)；读取 Commander 发布的当前实际导航状态 nav_state。 使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。<br>`get_px4_custom_mode(vehicle_status.nav_state)`，[baseline/px4/src/modules/commander/px4_custom_mode.h:102](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/commander/px4_custom_mode.h#L102-L102)；把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。 <br>`vehicle_status_s::NAVIGATION_STATE_AUTO_LAND`，[baseline/px4/msg/versioned/VehicleStatus.msg:54](https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/msg/versioned/VehicleStatus.msg#L54-L54)；Mode_t == NAVIGATION_STATE_AUTO_LAND。  |

**公式参数**

- 没有可直接实例化的当前配置参数；历史常量和未知 `k` 不人工补值。

**PGFuzz 作者制品全部候选输入**

- InputP（Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。）31 条：
  - `COM_POS_FS_DELAY,X,1,1,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:1`；当前对应 `COM_POS_FS_DELAY`；身份状态按当前证据为“当前定义未找到”。
  - `MC_PITCHRATE_FF,X,0,0,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:2`；当前对应 `MC_PITCHRATE_FF`；身份状态按当前证据为“当前同名定义已找到”。
  - `COM_FLTMODE1,X,-1,0,13,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:3`；当前对应 `COM_FLTMODE1`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_BARO_NOISE,X,3.5,0.01,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:4`；当前对应 `EKF2_BARO_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_GPS_CTRL,X,7,0,15,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:5`；当前对应 `EKF2_GPS_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_A_HMAX,X,5,1,10,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:6`；当前对应 `EKF2_RNG_A_HMAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_RNG_CTRL,X,1,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:7`；当前对应 `EKF2_RNG_CTRL`；身份状态按当前证据为“当前同名定义已找到”。
  - `EKF2_TERR_NOISE,X,5,0.5,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:8`；当前对应 `EKF2_TERR_NOISE`；身份状态按当前证据为“当前同名定义已找到”。
  - `FLW_TGT_ALT_M,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:9`；当前对应 `FLW_TGT_ALT_M`；身份状态按当前证据为“当前同名定义已找到”。
  - `GF_ALTMODE,X,0,0,1,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:10`；当前对应 `GF_ALTMODE`；身份状态按当前证据为“当前定义未找到”。
  - `LNDMC_ALT_GND,X,2,-1,X,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:11`；当前对应 `LNDMC_ALT_GND`；身份状态按当前证据为“当前同名定义已找到”。
  - `LNDMC_ALT_MAX,X,-1,-1,10000,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:12`；当前对应 `LNDMC_ALT_MAX`；身份状态按当前证据为“当前定义未找到”。
  - `LPE_BAR_Z,X,3,0.01,100,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:13`；当前对应 `LPE_BAR_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_FUSION,X,145,0,255,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:14`；当前对应 `LPE_FUSION`；身份状态按当前证据为“当前同名定义已找到”。
  - `LPE_Z_PUB,X,1,0.3,5,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:15`；当前对应 `LPE_Z_PUB`；身份状态按当前证据为“当前同名定义已找到”。
  - `MIS_LTRMIN_ALT,X,-1,-1,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:16`；当前对应 `NAV_MIN_LTR_ALT`；身份状态按当前证据为“当前更名定义已找到”。
  - `MIS_TAKEOFF_ALT,X,2.5,0,80,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:17`；当前对应 `MIS_TAKEOFF_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `NAV_MC_ALT_RAD,X,0.8,0.05,200,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:18`；当前对应 `NAV_MC_ALT_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_ALT_MODE,X,0,0,2,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:19`；当前对应 `MPC_ALT_MODE`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT1,X,10,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:20`；当前对应 `MPC_LAND_ALT1`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,5,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:21`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_LAND_ALT2,X,1,0,122,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:22`；当前对应 `MPC_LAND_ALT2`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_MAN_TILT_MAX,X,35,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:23`；当前对应 `MPC_MAN_TILT_MAX`；身份状态按当前证据为“当前同名定义已找到”。
  - `MPC_THR_HOVER,X,0.5,0.1,0.8,0.01`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:24`；当前对应 `MPC_THR_HOVER`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_FAPPR_ALT,X,0.1,0,10,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:25`；当前对应 `PLD_FAPPR_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `PLD_SRCH_ALT,X,10,0,100,0.1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:26`；当前对应 `PLD_SRCH_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_CONE_ANG,X,45,0,90,1`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:27`；当前对应 `RTL_CONE_ANG`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_DESCEND_ALT,X,30,2,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:28`；当前对应 `RTL_DESCEND_ALT`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_LOITER_RAD,X,80,25,1000,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:29`；当前对应 `RTL_LOITER_RAD`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_MIN_DIST,X,10,0.5,100,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:30`；当前对应 `RTL_MIN_DIST`；身份状态按当前证据为“当前同名定义已找到”。
  - `RTL_RETURN_ALT,X,60,0,150,0.5`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/parameters.txt:31`；当前对应 `RTL_RETURN_ALT`；身份状态按当前证据为“当前同名定义已找到”。
- InputC（Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。）52 条：
  - `Flight_Mode,2`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:1`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `Flight_Mode,3`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:2`；当前对应 `Flight_Mode`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_DO_PARACHUTE,208`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:3`；当前对应 `MAV_CMD_DO_PARACHUTE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SEND_BANNER,42428`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:4`；当前对应 `MAV_CMD_DO_SEND_BANNER`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SET_FACTORY_TEST_MODE,42427`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:5`；当前对应 `MAV_CMD_SET_FACTORY_TEST_MODE`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_GIMBAL_RESET,42501`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:6`；当前对应 `MAV_CMD_GIMBAL_RESET`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_NAV_WAYPOINT,16`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:7`；当前对应 `MAV_CMD_NAV_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `RC1,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:8`；当前对应 `RC1`；身份状态按当前证据为“特殊控制输入”。
  - `RC2,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:9`；当前对应 `RC2`；身份状态按当前证据为“特殊控制输入”。
  - `RC3,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:10`；当前对应 `RC3`；身份状态按当前证据为“特殊控制输入”。
  - `RC4,0`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:11`；当前对应 `RC4`；身份状态按当前证据为“特殊控制输入”。
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH,20`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:12`；当前对应 `MAV_CMD_NAV_RETURN_TO_LAUNCH`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_TAKEOFF,22`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:13`；当前对应 `MAV_CMD_NAV_TAKEOFF`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LAND,21`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:14`；当前对应 `MAV_CMD_NAV_LAND`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TURNS,18`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:15`；当前对应 `MAV_CMD_NAV_LOITER_TURNS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_LOITER_TIME,19`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:16`；当前对应 `MAV_CMD_NAV_LOITER_TIME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_SPLINE_WAYPOINT,82`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:17`；当前对应 `MAV_CMD_NAV_SPLINE_WAYPOINT`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_GUIDED_ENABLE,92`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:18`；当前对应 `MAV_CMD_NAV_GUIDED_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_JUMP,177`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:19`；当前对应 `MAV_CMD_DO_JUMP`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_MISSION_START,300`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:20`；当前对应 `MAV_CMD_MISSION_START`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_COMPONENT_ARM_DISARM,400`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:21`；当前对应 `MAV_CMD_COMPONENT_ARM_DISARM`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DELAY,112`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:22`；当前对应 `MAV_CMD_CONDITION_DELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_DISTANCE,114`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:23`；当前对应 `MAV_CMD_CONDITION_DISTANCE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_CONDITION_YAW,115`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:24`；当前对应 `MAV_CMD_CONDITION_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_CHANGE_SPEED,178`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:25`；当前对应 `MAV_CMD_DO_CHANGE_SPEED`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_HOME,179`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:26`；当前对应 `MAV_CMD_DO_SET_HOME`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_SERVO,183`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:27`；当前对应 `MAV_CMD_DO_SET_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_RELAY,181`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:28`；当前对应 `MAV_CMD_DO_SET_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_SERVO,184`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:29`；当前对应 `MAV_CMD_DO_REPEAT_SERVO`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPEAT_RELAY,182`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:30`；当前对应 `MAV_CMD_DO_REPEAT_RELAY`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONFIGURE,202`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:31`；当前对应 `MAV_CMD_DO_DIGICAM_CONFIGURE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_DIGICAM_CONTROL,203`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:32`；当前对应 `MAV_CMD_DO_DIGICAM_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_CAM_TRIGG_DIST,206`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:33`；当前对应 `MAV_CMD_DO_SET_CAM_TRIGG_DIST`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_ROI,201`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:34`；当前对应 `MAV_CMD_DO_SET_ROI`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_SET_MODE,176`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:35`；当前对应 `MAV_CMD_DO_SET_MODE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_MOUNT_CONTROL,205`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:36`；当前对应 `MAV_CMD_DO_MOUNT_CONTROL`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GRIPPER,211`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:37`；当前对应 `MAV_CMD_DO_GRIPPER`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_GUIDED_LIMITS,222`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:38`；当前对应 `MAV_CMD_DO_GUIDED_LIMITS`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_REPOSITION,192`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:39`；当前对应 `MAV_CMD_DO_REPOSITION`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_AUTOTUNE_ENABLE,212`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:40`；当前对应 `MAV_CMD_DO_AUTOTUNE_ENABLE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_PAUSE_CONTINUE,193`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:41`；当前对应 `MAV_CMD_DO_PAUSE_CONTINUE`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_NAV_ALTITUDE_WAIT,83`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:42`；当前对应 `MAV_CMD_NAV_ALTITUDE_WAIT`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_POWER_OFF_INITIATED,42000`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:43`；当前对应 `MAV_CMD_POWER_OFF_INITIATED`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_CLICK,42001`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:44`；当前对应 `MAV_CMD_SOLO_BTN_FLY_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_FLY_HOLD,42002`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:45`；当前对应 `MAV_CMD_SOLO_BTN_FLY_HOLD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_SOLO_BTN_PAUSE_CLICK,42003`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:46`；当前对应 `MAV_CMD_SOLO_BTN_PAUSE_CLICK`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL,42004`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:47`；当前对应 `MAV_CMD_FIXED_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_FIELD,42005`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:48`；当前对应 `MAV_CMD_FIXED_MAG_CAL_FIELD`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_FIXED_MAG_CAL_YAW,42006`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:49`；当前对应 `MAV_CMD_FIXED_MAG_CAL_YAW`；身份状态按当前证据为“当前命令 XML 定义已找到”。
  - `MAV_CMD_DO_START_MAG_CAL,42424`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:50`；当前对应 `MAV_CMD_DO_START_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_ACCEPT_MAG_CAL,42425`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:51`；当前对应 `MAV_CMD_DO_ACCEPT_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
  - `MAV_CMD_DO_CANCEL_MAG_CAL,42426`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/cmds.txt:52`；当前对应 `MAV_CMD_DO_CANCEL_MAG_CAL`；身份状态按当前证据为“当前命令 XML 定义未找到”。
- InputE（Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。）11 条：
  - `SIM_BARO_OFF_P`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:1`；当前对应 `SIM_BARO_OFF_P`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BARO_OFF_T`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:2`；当前对应 `SIM_BARO_OFF_T`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_GPS_USED`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:3`；当前对应 `SIM_GPS_USED`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_IGN_HOME_ALT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:4`；当前对应 `SIM_IGN_HOME_ALT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LAT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:5`；当前对应 `SIM_IGN_HOME_LAT`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_IGN_HOME_LON`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:6`；当前对应 `SIM_IGN_HOME_LON`；身份状态按当前证据为“当前定义未找到”。
  - `SIM_MAG_OFFSET_X`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:7`；当前对应 `SIM_MAG_OFFSET_X`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Y`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:8`；当前对应 `SIM_MAG_OFFSET_Y`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_MAG_OFFSET_Z`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:9`；当前对应 `SIM_MAG_OFFSET_Z`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_DRAIN`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:10`；当前对应 `SIM_BAT_DRAIN`；身份状态按当前证据为“当前同名定义已找到”。
  - `SIM_BAT_MIN_PCT`；来源 `baseline/pgfuzz/PX4/policies/PX.GPS.FS3/envs.txt:11`；当前对应 `SIM_BAT_MIN_PCT`；身份状态按当前证据为“当前同名定义已找到”。

</details>

## 统计与审计边界

- 主表严格 21 条。公开制品 `PX.ORBIT4/5` 共用目录 `PX.ORBIT4_5`；另有论文表中不存在的 `PX.CHUTE`，本表不把它补成第 22 条。
- 全部源码位置来自冻结提交；绑定是变量、字段、枚举、函数和消息路径的身份链，不是实现符合性判断。
- 历史 `COM_POS_FS_DELAY` 在当前版本找不到等价同名参数；`EKF2_NOAID_TOUT` 和 `COM_POS_FS_EPH` 仅是当前机制组成，不能冒充一对一改名。
