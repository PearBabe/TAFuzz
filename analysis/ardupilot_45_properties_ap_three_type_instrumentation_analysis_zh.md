# ArduPilot 45 条性质的命题三分类与插桩存储分析

## 1. 本文只分析什么

本文只分析下面两份文件中“当前要用于插桩的公式”所含叶子命题：

- [PGFuzz 原 30 条性质的当前规范化公式](/home/lqq/project/TAFuzz/benchmark/PGFuzz重新审计/ArduPilot/PGFuzz原性质_当前审计.md:22)；
- [当前新提取的 15 条公式](/home/lqq/project/TAFuzz/benchmark/PGFuzz重新审计/ArduPilot/当前新提取MTL性质.md:18)。

`AP` 是 `Atomic Proposition`，中文为“原子命题”，这里专指公式中最终需要判断真、假或
无法确定的最小布尔条件。本文不分析 PGFuzz 候选模糊输入，不判断性质是否满足，也不评价
公式好坏。

历史文件的逐条明细仍有不少命题来自论文印刷原式，而主表“当前规范化公式”已经换成新
命题。插桩必须以当前规范化公式的叶子命题为准，不能把旧代理命题直接拿来生成代码。

表内标识符保持公式原名，便于回到原文件搜索：`prev` 是 `previous`，表示“上一条有效
性质样本”；`enter` 表示“进入”；`begin` 和 `start` 表示“开始”；`runtime(P)` 表示
参数 `P` 的本次实际运行值；`abs(x)` 表示数值 `x` 的绝对值；`¬p` 表示命题 `p` 不成立。

## 2. 三类命题

全部命题只分三类，不再增加其他事件类型。

|类型|白话含义|统一插桩位置规则|统一存储方式|
|---|---|---|---|
|持续状态命题|在一段时间内具有当前真假，例如模式、解锁状态、故障保护状态、数值是否超过阈值|在状态或数值真正形成之后更新；若由多个操作数组合，则分别在真实生产位置缓存操作数，在同一性质采集点计算最终真假|版本化状态单元：`truth`（真假）、`known`（是否可靠可知）、`version`（版本号）、`updated_us`（飞控侧最近更新时间）|
|瞬时事件命题|只在某个确定时刻发生，例如进入子状态、开始下降、成功接受新目标|在状态转换或动作已经成功提交之后记录；不能放在请求发出之前，也不能只放在遥测发送函数里|有序事件队列：保存命题编号、真实源码时间和发生顺序；周期发送时再批量取出，不在事件发生时立即发送|
|记忆派生命题|当前源码值本身不够，必须借助过去的信息，例如上一有效样本、静默起点、参考高度、条件区间起点|不伪造一个不存在的源码事件；先复用持续状态或瞬时事件探针，再由性质运行时根据历史生成命题真假|性质专用记忆记录：按公式需要保存上一有效值、最后接收时间、参考值、区间开始时间、是否初始化及重置条件|

### 2.1 持续状态命题的统一逻辑

```text
真实状态或数值更新
  → 更新该性质需要的操作数缓存
  → 检查有效性、单位和版本
  → 计算当前布尔命题
  → 写入版本化状态单元
```

数值比较仍属于持续状态命题。例如 `ALT<RTL_target_alt` 虽然用了高度和目标高度两个
数值，但最终含义是“当前是否低于目标高度”，它在每个时刻都有当前真假。

### 2.2 瞬时事件命题的统一逻辑

```text
动作或状态转换请求
  → 完成合法性检查
  → 真正提交新状态或接受动作
  → 记录 {命题编号, source_time_us, order}
  → 放入当前性质的有序事件队列
```

`source_time_us` 表示飞控源码侧事件时间，单位为微秒；`order` 表示同一发送周期内的真实
先后顺序。不能只用一个锁存位，因为同一周期内可能发生多次或发生两个有先后关系的事件。

### 2.3 记忆派生命题的统一逻辑

这一类不增加新的源码探针接口，只在当前性质的运行时保存必要记忆：

```text
上一有效样本：previous_value
最后有效事件：last_seen_us
一次条件区间：active、start_us
一次保持区间：reference_value、reference_time_us
共同字段：initialized、known、source_version、reset_rule
```

例如 `ALT_prev<ALT` 的上一值只能在上一条性质样本成功提交后更新；第一次采样没有上一值，
该命题必须是无法确定。`gcs_gap_start` 不能在“没有收到心跳”的代码处插桩，因为那里没有
代码执行；它只能由最后一次有效心跳时间和后续时钟推进计算出来。

记忆派生器得到持续结果时，把结果写入状态单元；得到 `bad_vibe_start`、`gcs_gap_start`
这类一次性起点时，再把派生结果及其计算出的源码时间写入同一套有序事件队列。这里没有
增加第四类命题，只是同一类派生结果的最终保存形态不同。

### 2.4 三类之间的判定边界

- `disarmed`、`high_vibes`、`gcs_failsafe`、`parachute_released` 在当前公式中表示“当前
  已经处于该结果状态”，因此归为持续状态。状态由假变真的准确时刻仍可随状态更新一起
  记录，但不会因此把命题改成瞬时事件。
- `enter_loiter_at_home`、`begin_final_descent`、`new_target` 明确表示一次进入或发生，
  因此归为瞬时事件。
- `bad_vibe_start`、`terrain_missing_start`、`gcs_gap_start` 虽然名字含 `start`，但源码
  中没有一个可直接等同的独立动作；它们要由完整前件的前后状态或最后接收时间计算，
  因此归为记忆派生。

## 3. PGFuzz 历史 30 条当前公式的叶子命题分类

表中的“真值未闭合”只表示该叶子命题目前还没有足够精确的布尔判定条件；它不是第四种
命题类型。

|性质|持续状态命题|瞬时事件命题|记忆派生命题|所需存储|
|---|---|---|---|---|
|`A.RTL1`|`Mode=RTL`；`ALT<RTL_target_alt`|—|`ALT_prev<ALT`|状态单元 + 上一有效高度|
|`A.RTL2`|`Mode=RTL`；`return_leg`；`¬at_return_point`；`commanded_ALT=RTL_target_alt`|—|`distance_to_return_prev>distance_to_return`|状态单元 + 上一有效距离|
|`A.RTL3`|—|`enter_loiter_at_home`；`enter_land`|—|有序事件队列|
|`A.RTL4`|`Mode=LAND`；`landed`；`throttle_min`；`disarmed`|—|—|状态单元|
|`A.FLIP1`|`abs(roll)<45°`；`armed`；`¬landed`|`enter_FLIP`|`previous_mode∈allowed_flip_modes`|状态单元 + 事件队列 + 进入前模式|
|`A.FLIP2`|`Mode=FLIP`；`flip_stage=rotate`；`commanded_roll_rate=direction×400°/s`|—|—|状态单元|
|`A.FLIP3`|—|`enter_flip_recovery`|`entry_attitude_reached`；`previous_mode_restored`|事件队列 + 进入姿态和进入前模式|
|`A.FLIPGeneral`|—|`enter_flip_start`；`flip_recovery_or_abort`|`previous_mode_restored`|事件队列 + 进入前模式|
|`A.ALT_HOLD1`|`Mode=ALT_HOLD`；`barometer_primary`；`¬valid_rangefinder_override`；`altitude_control_uses_pressure_altitude`（真值未闭合）|—|—|状态单元|
|`A.ALT_HOLD2`|`Mode=ALT_HOLD`；`throttle_in_runtime_deadzone`|—|`altitude_target_held`（参考值和容差尚须闭合）|状态单元 + 参考高度或参考目标|
|`A.CIRCLE1`|`Mode=CIRCLE`；`stick_adjust_enabled`；`¬radio_failsafe`；`pitch_up`；`radius>0`|—|`radius_prev>radius`|状态单元 + 上一有效半径|
|`A.CIRCLE2`|`Mode=CIRCLE`；`stick_adjust_enabled`；`¬radio_failsafe`；`pitch_down`|—|`radius_prev<radius`|状态单元 + 上一有效半径|
|`A.CIRCLE3`|`Mode=CIRCLE`；`stick_adjust_enabled`；`¬radio_failsafe`；`roll_right`；`clockwise`|—|`rate_prev<rate`|状态单元 + 上一有效角速度|
|`A.CIRCLE4`|`Mode=CIRCLE`；`stick_adjust_enabled`；`¬radio_failsafe`；`roll_right`；`counterclockwise`；`rate≠0`|—|`abs(rate_prev)>abs(rate)`|状态单元 + 上一有效角速度|
|`A.CIRCLE5`|`Mode=CIRCLE`；`stick_adjust_enabled`；`¬radio_failsafe`；`roll_left`；`counterclockwise`|—|`abs(rate_prev)<abs(rate)`|状态单元 + 上一有效角速度|
|`A.CIRCLE6`|`Mode=CIRCLE`；`stick_adjust_enabled`；`¬radio_failsafe`；`roll_left`；`clockwise`；`rate≠0`|—|`abs(rate_prev)>abs(rate)`|状态单元 + 上一有效角速度|
|`A.CIRCLE7`|`Mode=CIRCLE`；`¬stick_adjust_enabled`；`roll_pitch_inputs_ignored`（真值未闭合）；`yaw_input_allowed`（真值未闭合）；`throttle_altitude_control_allowed`（真值未闭合）|—|—|已闭合命题用状态单元；三个未闭合命题暂不生成探针|
|`A.LAND1`|`Mode=LAND`；`above_runtime_land_transition`；`descent_target=runtime(LAND_SPD_HIGH_MS or WP_SPD_DN)`|—|—|状态单元|
|`A.LAND2`|`Mode=LAND`；`below_runtime_land_transition`；`descent_target=runtime(LAND_SPD_MS)`|—|—|状态单元|
|`A.AUTO1`|`Mode=AUTO`；`roll_pitch_throttle_ignored`（真值未闭合）；`AUTO_OPTIONS_ignore_yaw`；`yaw_override_allowed`（真值未闭合）|—|—|已闭合命题用状态单元；两个未闭合命题暂不生成探针|
|`A.BRAKE1`|`stopped`（停止容差尚须闭合）|`enter_BRAKE`|—|状态单元 + 事件队列|
|`A.DRIFT1`|`Mode=DRIFT`；`position_estimate_lost`；`Mode=LAND`；`Mode=ALT_HOLD`|—|—|状态单元|
|`A.LOITER1`|`Mode=LOITER`；`pilot_sticks_released`|—|`hold_current_position_heading_altitude`（参考值和容差尚须闭合）|状态单元 + 位置、航向和高度参考记录|
|`A.GUIDED1`|`Mode=GUIDED`|`guided_target_reached`；`new_target_or_mode_change`|`no_new_target`；`hold_at_target`（参考值和容差尚须闭合）|状态单元 + 事件队列 + 目标代次和参考目标|
|`A.SPORT1`|`Mode=SPORT`；`full_climb_command`；`vertical_climb_speed≤runtime(PILOT_SPD_UP)`|—|—|状态单元|
|`A.RC.FS1`|`radio_failsafe`；`armed`；`landed`；`Mode∈{STABILIZE,ACRO}`；`throttle_min`；`¬AirMode`；`disarmed`|—|—|状态单元|
|`A.RC.FS2`|`FS_THR_ENABLE`；`throttle<runtime(FS_THR_VALUE)`；`radio_failsafe`|—|—|状态单元|
|`A.CHUTE1`|`auto_chute_conditions`；`parachute_released`|—|`auto_loss_of_control_start`|状态单元 + 条件区间记录 + 派生事件队列|
|`A.GPS.FS1`|当前规范状态为“当前不再适用”，没有当前插桩公式|—|—|不生成|
|`A.GPS.FS2`|当前规范状态为“当前不再适用”，没有当前插桩公式|—|—|不生成|

## 4. 当前新提取 15 条公式的叶子命题分类

|性质|持续状态命题|瞬时事件命题|记忆派生命题|所需存储|
|---|---|---|---|---|
|`ARD-NEW-VIBE-001`|`vibe_applicable`；`bad_vibe_conditions`；`high_vibes`|—|`bad_vibe_start`|状态单元 + 异常条件区间记录 + 派生事件队列|
|`ARD-NEW-VIBE-002`|`high_vibes`；`normal_vibe`|—|`normal_vibe_start`|状态单元 + 恢复条件区间记录 + 派生事件队列|
|`ARD-NEW-TERRAIN-003`|`mission_requires_terrain`；`terrain_missing`；`terrain_action`|—|`terrain_missing_start`|状态单元 + 地形缺失区间记录 + 派生事件队列|
|`ARD-NEW-RUDDER-004`|`rudder_disarm_enabled`；`allowed_mode`；`throttle_min`；`rudder_left`；`disarmed`|—|`rudder_disarm_start`|状态单元 + 完整手势区间记录 + 派生事件队列|
|`ARD-NEW-CHUTE-005`|`auto_chute_conditions`；`parachute_released`|—|`auto_control_loss_start`|状态单元 + 自动失控区间记录 + 派生事件队列|
|`ARD-NEW-CRASH-006`|`crash_check_enabled`；`crash_conditions`；`disarmed`|—|`crash_condition_start`|状态单元 + 坠毁条件区间记录 + 派生事件队列|
|`ARD-NEW-EKF-007`|`ekf_fs_enabled`；`two_variances_bad`；`ekf_failsafe`|—|`two_variances_bad_start`|状态单元 + 方差异常区间记录 + 派生事件队列|
|`ARD-NEW-GCS-008`|`gcs_fs_enabled`；`gcs_failsafe`|—|`gcs_gap_start`；`seen_gcs_before`|状态单元 + 最后有效心跳时间和已见标志 + 派生事件队列|
|`ARD-NEW-RC-009`|`rc_fs_enabled`；`radio_failsafe`|—|`rc_gap_start`；`rc_seen_or_armed`|状态单元 + 最后有效遥控帧时间和已见标志 + 派生事件队列|
|`ARD-NEW-BATT-010`|`voltage_threshold_enabled`；`battery_failsafe`|—|`low_voltage_start`|按电池实例保存状态单元、低电压区间记录和派生事件队列|
|`ARD-NEW-RTL-011`|—|`enter_loiter_at_home`；`begin_final_descent`|—|有序事件队列|
|`ARD-NEW-GUID-012`|`guided_timeout_applicable`|`timeout_response_start`|`guided_command_gap_start`|状态单元 + 最后有效指令时间 + 有序事件队列|
|`ARD-NEW-LOITER-013`|`Mode=LOITER`；`sticks_released`；`stopped`（停止容差尚须闭合）|—|`position_held`（参考值和容差尚须闭合）|状态单元 + 释放摇杆时的位置参考|
|`ARD-NEW-GUIDWAIT-014`|`Mode=GUIDED`|`target_reached`；`new_target`；`mode_change`|`hover_at_target`（参考值和容差尚须闭合）|状态单元 + 有序事件队列 + 目标代次和参考目标|
|`ARD-NEW-AUTO-015`|`Mode=AUTO`；`mission_running`；`roll_pitch_throttle_ignored`（真值未闭合）；`ignore_pilot_yaw`；`yaw_override_allowed`（真值未闭合）|—|—|已闭合命题用状态单元；两个未闭合命题暂不生成探针|

## 5. 三类命题怎样落到可复用代码

只需要三套通用运行时能力。

### 5.1 状态更新接口

```cpp
TAFUZZ_SET_STATE(ap_index, truth, known, source_time_us, version);
```

它适用于所有模式、标志和阈值命题。调用只更新状态单元，不发送消息。

### 5.2 事件记录接口

```cpp
TAFUZZ_RECORD_EVENT(ap_index, source_time_us, order);
```

它适用于所有真正的进入、开始和新目标事件。默认写入有序队列；只有编译器已经证明同一
周期最多发生一次且公式不关心顺序时，才允许退化成单个锁存位。

### 5.3 记忆派生器

```text
TAFUZZ_DERIVE(ap_index, current_states, event_queue, property_memory)
```

它不直接插入具体业务源码，而是由当前性质运行时调用。`property_memory` 中文为“当前
性质专用记忆”，只保存当前公式实际需要的上一值、最后接收时间、参考值或区间起点。

这三套能力已经覆盖两份文件里全部具有当前插桩公式的命题。参数、单位、有效性、坐标系、
实例编号和动作原因只附着在状态单元、事件记录或性质记忆上，不增加命题类型。
