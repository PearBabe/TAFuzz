# ArduCopter 当前新提取 MTL/MITL 性质

## 术语与阅读规则

- `MTL`（Metric Temporal Logic，度量时序逻辑）和 `MITL`（Metric Interval Temporal Logic，度量区间时序逻辑）用于表达“某个状态持续多久后应发生什么”。
- `G` 表示“全程检查”；`F_[a,b] p` 表示“a 到 b 时间内最终出现 p”；`U` 是 `Until`，中文为“前件持续成立直到后件发生”。
- `AP`（Atomic Proposition，原子命题）是公式中能单独判真的条件。`SITL`（Software In The Loop，软件在环仿真）参数值只代表冻结运行。
- `HEARTBEAT` 是 MAVLink 的“心跳消息”；`STATUSTEXT` 是“状态文本消息”。消息能看到某结果，不等于它能给出内部事件的精确发生时刻。
- “当前仍须满足/有条件必须满足”来自官方要求的当前适用性；源码控制流仅用于绑定，不用于反推出性质；每条固定写“实现符合性：未评估”。

## 冻结范围与提取原则

- ArduCopter 源码提交 `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`；官方文档固定提交 `826ef054a04e23b1ceeb3fb01a4df1d270efebcd`。
- 固定时间性质在前；可修改参数决定下界的性质居中；无界性质在后。无来源时间绝不补秒数。
- 公式采用事件起点 AP，避免把“循环次数”冒充秒。参数默认值、冻结 SITL 实际值、是否可修改分开写。
- 正例/反例是公式级人工审查轨迹；本文件生成阶段尚未为新增 15 条全部重新运行 TAMonitor，因此监视器结果标为“见总分析第九节；未进入执行门的性质不得解释为通过”，不能写成已通过。

## 新性质总表

|顺序|编号|时间类别|当前规范状态|官方英文原文与中文解释|官方位置与来源权威性|MITL 公式|AP、物理状态、源码绑定与 MAVLink 观测|参数默认值、SITL 值与可修改性|时间来源、时钟与边界|正例与边界反例|实现符合性|
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ARD-NEW-VIBE-001 | 官方固定时间 | 有条件必须满足 | The vibration failsafe will trigger if all of the following are true for at least one second: EKF vertical velocity innovations are positive, EKF vertical position innovations are positive, and EKF velocity variance is 1 or higher.<br>启用振动保护、已解锁且不是人工油门模式时，三项估计器异常条件连续至少一秒，应进入高振动补偿状态。 | [Vibration Failsafe — When the failsafe will trigger](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/vibration-failsafe.rst#L17-L23)，`copter/source/docs/vibration-failsafe.rst:17-23`；官方行为说明 | `G((bad_vibe_start ∧ vibe_applicable ∧ G_[0,1s] bad_vibe_conditions) → (G_[0,1s) ¬high_vibes ∧ F_[1s,∞) high_vibes))` | `bad_vibe_conditions`：IVD>0、IPD>0 且速度方差≥1，或当前估计器明确报告振动影响；估计器创新量/方差，无量纲及内部单位组合；`bad_vibe_detected`，[`ArduCopter/ekf_check.cpp:274-292`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/ekf_check.cpp#L274-L292)；观测：需要插桩<br>`high_vibes`：振动补偿状态已开启；布尔状态；`vibration_check.high_vibes`，[`ArduCopter/Copter.h:320`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Copter.h#L320-L320)；写入 [`ekf_check.cpp:294-306`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/ekf_check.cpp#L294-L306)；观测：条件可观测：可监听 `STATUSTEXT` 文本，但严格真值需插桩 | `FS_VIBE_ENABLE`：默认 1，冻结 SITL 值 1；可修改开关，不是时间参数。 | 官方固定时间 1 秒；起点为三项异常条件首次同时为真；条件恢复会取消；终点为 `high_vibes`；使用飞控单调启动毫秒时钟；文档没有给采样误差，边界受误差影响时判为无法确认。 | 正例：t=0 条件开始且持续；t=1.000 s 或其后 `high_vibes=true`，满足。<br>边界反例：t=0 条件开始且持续；t=0.999 s 已置真，违反阈值前禁止；仅在 t=1.000 s 尚未置真不能单独判违反，因为来源没有有限最晚上界。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 2 | ARD-NEW-VIBE-002 | 官方固定时间 | 有条件必须满足 | Vibration failsafe will deactivate 15 seconds after the EKF returns to normal.<br>高振动补偿已经开启后，估计器恢复正常并连续保持十五秒，应关闭高振动补偿。 | [Vibration Failsafe — Recovery from the failsafe](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/vibration-failsafe.rst#L34-L39)，`copter/source/docs/vibration-failsafe.rst:34-39`；官方行为说明 | `G((normal_vibe_start ∧ high_vibes ∧ G_[0,15s] normal_vibe) → (G_[0,15s) high_vibes ∧ F_[15s,∞) ¬high_vibes))` | `normal_vibe`：不再满足高振动判据；估计器组合状态；`!do_bad_vibe_actions`，[`ArduCopter/ekf_check.cpp:290-313`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/ekf_check.cpp#L290-L313)；观测：需要插桩<br>`¬high_vibes`：补偿状态已关闭；布尔状态；`vibration_check.high_vibes=false`，[`ArduCopter/ekf_check.cpp:313-321`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/ekf_check.cpp#L313-L321)；观测：条件可观测：`STATUSTEXT` 文本；严格真值需插桩 | `FS_VIBE_ENABLE` 默认与 SITL 均为 1；可修改。 | 官方固定时间 15 秒；起点为异常条件恢复正常；再次异常会重置恢复计时；终点为 `high_vibes=false`；飞控单调启动毫秒时钟。 | 正例：t=0 恢复正常并保持；t=15.000 s 或其后关闭，满足。<br>边界反例：t=14.999 s 已关闭，违反阈值前禁止；t=15.000 s 仍开启尚不足以在有限前缀判违反。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 3 | ARD-NEW-TERRAIN-003 | 官方固定时间 | 当前仍须满足 | If the vehicle is executing a mission command that requires terrain data but it is unable to retrieve terrain data for two seconds, the vehicle will switch to RTL mode (if it is flying) or disarm (if it is landed).<br>正在执行需要地形数据的任务时，如果连续两秒取不到地形数据，飞行中应转入返航，已着陆则应锁定。 | [Terrain Following — Failsafe in case of no Terrain data](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/terrain-following.rst#L74-L78)，`copter/source/docs/terrain-following.rst:74-78`；官方行为说明 | `G((terrain_missing_start ∧ mission_requires_terrain ∧ G_[0,2s] terrain_missing) → (G_[0,2s) ¬terrain_action ∧ F_[2s,∞) terrain_action))` | `mission_requires_terrain ∧ terrain_missing`：当前任务/模式要求地形且获取失败；任务导航内部状态；`flightmode->requires_terrain_failsafe()` 与失败时间戳，[`ArduCopter/events.cpp:242-275`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/events.cpp#L242-L275)；观测：需要插桩<br>`Mode=RTL`：当前模式为返航；模式枚举；`Mode::Number::RTL`，[`ArduCopter/mode.h:84`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode.h#L84-L84)；观测：可直接观测：`HEARTBEAT.custom_mode`<br>`disarmed`：电机未解锁；布尔状态；`!motors->armed()`，[`libraries/AP_Motors/AP_Motors_Class.h:117`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_Motors/AP_Motors_Class.h#L117-L117)；观测：可直接观测：`HEARTBEAT.base_mode` | 无时间参数；当前源码 `FS_TERRAIN_TIMEOUT_MS=5000` 是实现常量，不是从官方要求推导的新时间。 | 官方固定时间 2 秒；`terrain_action=((flying ∧ Mode=RTL) ∨ (landed ∧ disarmed))`。起点为需要地形数据时首次取数失败；恢复数据会取消；飞控单调启动时钟。冻结源码常量是 5 秒，与文档 2 秒冲突；冲突是测试目标，不修改规范。 | 正例：t=0 连续缺地形；飞行中 t=2.000 s 或其后进入 RTL，满足。<br>边界反例：t=1.999 s 已仅因该缺失进入 RTL，违反提前禁止；源码 5 秒常量不能改变规范阈值。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 4 | ARD-NEW-RUDDER-004 | 官方固定时间 | 有条件必须满足 | Check that your flight mode switch is set to Stabilize, ACRO, AltHold, Loiter, or PosHold. Hold throttle at minimum and rudder to the left for 2 seconds. The LED will start flashing indicating the vehicle is disarmed.<br>在允许舵量锁定的模式与配置下，油门最小并把方向舵保持在左侧两秒，应锁定电机。 | [Arming the Motors — Disarming the motors](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/arming_the_motors.rst#L52-L60)，`copter/source/docs/arming_the_motors.rst:52-60`；官方行为说明 | `G((rudder_disarm_start ∧ rudder_disarm_enabled ∧ allowed_mode ∧ G_[0,2s](throttle_min ∧ rudder_left)) → (G_[0,2s) ¬disarmed ∧ F_[2s,∞) disarmed))` | `throttle_min ∧ rudder_left`：油门控制量为最小且锁定舵通道控制量<-4000；归一化遥控输入；`RC_Channels::rudder_arm_disarm_check`，[`libraries/RC_Channel/RC_Channels.cpp:456-515`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/RC_Channel/RC_Channels.cpp#L456-L515)；观测：条件可观测：`RC_CHANNELS`，但飞控内部阈值与接收时刻需插桩确认<br>`disarmed`：电机未解锁；布尔状态；`AP::arming().disarm(AP_Arming::Method::RUDDER)`，[`RC_Channels.cpp:511-514`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/RC_Channel/RC_Channels.cpp#L511-L514)；观测：可直接观测：`HEARTBEAT.base_mode` | `ARMING_RUDDER` 控制是否允许舵量锁定；不是固定时间来源。冻结源码内实现计时 3000 ms 仅记录冲突。 | 官方固定时间 2 秒；起点为允许模式中油门最小且左舵达到有效阈值；中立或离开阈值重置；飞控单调启动时钟。当前共享 RC 代码使用 3000 ms，与文档冲突。 | 正例：t=0 左舵与最小油门开始；t=2.000 s 或其后锁定，满足。<br>边界反例：t=1.999 s 已仅因该手势锁定，违反提前禁止；t=2.000 s 仍解锁的有限前缀尚不足以判永久违反。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 5 | ARD-NEW-CHUTE-005 | 官方固定时间 | 有条件必须满足 | The following must all be true for a full 1 second for automatic release to trigger: motors armed; not FLIP or ACRO; barometer shows the vehicle is not climbing; and above CHUTE_ALT_MIN when loss of control is first detected.<br>自动开伞适用且四组条件连续满一秒时，应触发降落伞释放；手动释放不属于这条性质。 | [Parachute — When will the parachute deploy?](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/common/source/docs/common-parachute.rst#L126-L137)，`common/source/docs/common-parachute.rst:126-137`；官方行为说明 | `G((auto_control_loss_start ∧ G_[0,1s] auto_chute_conditions) → (G_[0,1s) ¬parachute_released ∧ F_[1s,∞) parachute_released))` | `auto_control_loss_start`：姿态误差超过阈值的自动失控区间起点；内部事件；`control_loss_count` 与 `angle_error`，[`ArduCopter/crash_check.cpp:243-325`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/crash_check.cpp#L243-L325)；观测：需要插桩<br>`parachute_released`：释放已启动；布尔/事件状态；`parachute_release()`，[`ArduCopter/crash_check.cpp:325-330`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/crash_check.cpp#L325-L330)；观测：条件可观测：`STATUSTEXT`；严格事件需插桩 | `CHUTE_ALT_MIN` 默认 10 m；当前 Copter SITL 参数下载没有该参数，说明当前构建未纳入或未公开该功能，不能编造运行值。参数本身可配置。 | 官方固定时间 1 秒；`auto_chute_conditions=(armed ∧ allowed_chute_mode ∧ not_climbing ∧ above_CHUTE_ALT_MIN)`。起点为首次检测到自动失控且高度门槛成立；条件恢复/模式不适用会取消；内部主循环计数对应飞控单调时间。 | 正例：t=0 自动失控条件开始且持续；t=1.000 s 或其后释放，满足。<br>边界反例：t=0.999 s 已仅因自动判据释放，违反提前禁止；到 t=1.000 s 未释放的有限前缀仍无法证明永不释放。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 6 | ARD-NEW-CRASH-006 | 官方固定时间 | 有条件必须满足 | When all the following are true for 2 full seconds: the vehicle is armed; not landed; current flight mode is not ACRO or FLIP; acceleration is not more than 3m/s/s; and actual lean angle has diverged from desired lean angle by more than 30 degrees. The motors will disarm.<br>坠毁检查已启用且附加内部门控适用时，官方列出的异常条件连续满两秒，应锁定电机。 | [Crash Check — When will the crash check disarm the motors?](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/crash_check.rst#L11-L28)，`copter/source/docs/crash_check.rst:11-28`；官方行为说明 | `G((crash_condition_start ∧ crash_check_enabled ∧ G_[0,2s] crash_conditions) → (G_[0,2s) ¬disarmed ∧ F_[2s,∞) disarmed))` | `crash_conditions`：已解锁、未着陆、模式适用、加速度<3 m/s²、姿态误差>30°，并满足文档允许的附加门控；姿态/加速度/模式复合状态；`Copter::crash_check()`，[`ArduCopter/crash_check.cpp:19-90`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/crash_check.cpp#L19-L90)；观测：需要插桩<br>`disarmed`：电机未解锁；布尔状态；`arming.disarm(...CRASH)`，[`ArduCopter/crash_check.cpp:89-95`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/crash_check.cpp#L89-L95)；观测：可直接观测：`HEARTBEAT.base_mode` | `FS_CRASH_CHECK` 默认 1，冻结 SITL 值 1，可修改开关；2 秒来自官方文本，不是参数。 | 官方固定时间 2 秒；任一条件恢复即重置；飞控单调主循环时间。官方注释明确“附加内部门控可能适用”，所以其适用性必须作为前置条件。 | 正例：t=0 全部条件开始并持续；t=2.000 s 或其后锁定，满足。<br>边界反例：t=1.999 s 已仅因该判据锁定，违反提前禁止；t=2.000 s 仍解锁的有限前缀尚不能证明无界最终义务失败。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 7 | ARD-NEW-EKF-007 | 官方固定时间 | 有条件必须满足 | The EKF failsafe will trigger when any two of the EKF variances for compass, position or velocity are higher than the FS_EKF_THRESH parameter value for 1 second.<br>估计器保护启用且已具备有效原点后，罗盘、位置、速度三类方差中任意两类连续一秒超过运行时阈值，应触发 EKF 故障保护。 | [EKF Failsafe — When will it trigger?](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/ekf-inav-failsafe.rst#L9-L13)，`copter/source/docs/ekf-inav-failsafe.rst:9-13`；官方行为说明 | `G((two_variances_bad_start ∧ ekf_fs_enabled ∧ G_[0,1s] two_variances_bad) → (G_[0,1s) ¬ekf_failsafe ∧ F_[1s,∞) ekf_failsafe))` | `two_variances_bad`：罗盘、位置、速度方差中至少两项超过 FS_EKF_THRESH；估计器方差比/无量纲；`ekf_over_threshold()` 和 `fail_count`，[`ArduCopter/ekf_check.cpp:28-89`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/ekf_check.cpp#L28-L89)；观测：需要插桩；标准 `ESTIMATOR_STATUS` 比值不等价于全部内部判据<br>`ekf_failsafe`：EKF 故障保护状态已置真；布尔状态；`failsafe.ekf`，[`ArduCopter/ekf_check.cpp:165-178`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/ekf_check.cpp#L165-L178)；观测：条件可观测：状态文本/后续模式；严格真值需插桩 | `FS_EKF_THRESH` 默认 0.8，冻结 SITL 读取为约 0.8；可修改阈值，不改变 1 秒官方时间。 | 官方固定时间 1 秒；起点为任意两类方差首次同时超过阈值；恢复会衰减/重置；飞控 10 Hz 检查任务的单调时钟。 | 正例：t=0 两项方差越界并持续；t=1.000 s 或其后触发，满足。<br>边界反例：t=0.999 s 已仅因该方差条件触发，违反提前禁止；t=1.000 s 尚未触发的有限前缀不能证明最终义务失败。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 8 | ARD-NEW-GCS-008 | 可修改参数决定下界 | 有条件必须满足 | If no heartbeat is received FS_GCS_TIMEOUT seconds (Default is 5 seconds), the GCS failsafe event will trigger based on your parameter settings. If no GCS is ever connected, the failsafe remains inactive.<br>本次运行曾收到指定地面站心跳、保护启用且之后持续收不到心跳时，到运行参数 FS_GCS_TIMEOUT 之前不得触发；到期后应最终触发。 | [GCS Failsafe](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/gcs-failsafe.rst#L6-L8)，`copter/source/docs/gcs-failsafe.rst:6-8`；官方行为说明+参数元数据 | `G((gcs_gap_start ∧ seen_gcs_before ∧ gcs_fs_enabled) → (G_[0,T_gcs) ¬gcs_failsafe ∧ F_[T_gcs,∞) gcs_failsafe))` | `gcs_gap_start`：最后一个已接受的指定 GCS 心跳后缺失区间开始；消息接收事件；`GCS_MAVLINK::handle_heartbeat`，[`libraries/GCS_MAVLink/GCS_Common.cpp:4357-4363`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/GCS_MAVLink/GCS_Common.cpp#L4357-L4363)；观测：需要在飞控接收端关联；只看地面端发送不足以证明<br>`gcs_failsafe`：地面站故障保护状态为真；布尔状态；`failsafe.gcs` 及处理路径，参数定义 [`ArduCopter/Parameters.cpp:828-835`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Parameters.cpp#L828-L835)；观测：需要插桩或由模式/状态文本条件推断 | `FS_GCS_TIMEOUT` 默认 5 s、范围 2..120 s、冻结 SITL 5 s；可修改，写入后何时重读未实测。 | 可修改参数时间 `T_gcs=runtime(FS_GCS_TIMEOUT)`；默认 5 s，冻结 SITL 5 s；飞控收到指定 GCS 心跳的单调启动时间，不是地面端到达时间；下界闭合、提前区间右端开。 | 正例：SITL 值 5 s：t=0 最后心跳，t<5 不触发，t=5 或之后触发，满足。<br>边界反例：t=4.999 s 已触发，违反提前禁止；若仅缺失但轨迹未结束，晚触发在无有限上界公式中仍无法判违反。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 9 | ARD-NEW-RC-009 | 可修改参数决定下界 | 有条件必须满足 | If enabled and set-up correctly the radio failsafe will trigger if loss conditions occur for more than RC_FS_TIMEOUT seconds (default = 1 sec).<br>电台保护启用且此前有过遥控输入或飞行器已解锁时，遥控更新持续缺失超过运行时 RC_FS_TIMEOUT 后，应触发遥控故障保护。 | [Radio Failsafe — When the failsafe will trigger](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/radio-failsafe.rst#L20-L32)，`copter/source/docs/radio-failsafe.rst:20-32`；官方行为说明+参数元数据 | `G((rc_gap_start ∧ rc_fs_enabled ∧ rc_seen_or_armed) → (G_[0,T_rc] ¬radio_failsafe ∧ F_(T_rc,∞) radio_failsafe))` | `rc_gap_start`：最后一帧有效遥控输入后不再更新；消息/接收机事件；`last_radio_update_ms`，[`ArduCopter/radio.cpp:100-134`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/radio.cpp#L100-L134)；观测：需要飞控接收端事件；地面到达时间不等价<br>`radio_failsafe`：遥控故障保护状态为真；布尔状态；`failsafe.radio`；参数 `_fs_timeout`，[`libraries/RC_Channel/RC_Channels_VarInfo.h:107-113`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/RC_Channel/RC_Channels_VarInfo.h#L107-L113)；观测：需要插桩或条件推断 | `RC_FS_TIMEOUT` 默认 1.0 s、范围 0.1..10 s、冻结 SITL 1.0 s；可修改。 | 可修改参数时间，且官方写“more than”，所以 `T_rc` 处仍禁止，最终区间左端开；飞控最后有效 RC 更新的单调启动毫秒时钟。默认与冻结 SITL 均 1 s。 | 正例：T=1 s：t=1.000 s 尚不触发，t=1.001 s 触发，满足离散毫秒见证；这 1 ms 是采样网格，不是人工 epsilon。<br>边界反例：t=1.000 s 已触发，违反开边界；缺失结束前无法以有限前缀证明“永不触发”。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 10 | ARD-NEW-BATT-010 | 可修改参数决定下界 | 有条件必须满足 | BATT_LOW_TIMER can configure how long the voltage must be below the threshold for the failsafe to trigger. The metadata says continuously for more than LOW_TIMER.<br>选定电池实例的有效电压源持续低于非零阈值，严格超过运行时 LOW_TIMER 后，应产生该实例的低电压故障保护事件。 | [Battery Failsafe — Advanced Settings](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/failsafe-battery.rst#L91-L96)，`copter/source/docs/failsafe-battery.rst:91-96`；官方行为说明+参数元数据 | `G((low_voltage_start ∧ voltage_threshold_enabled) → (G_[0,T_batt] ¬battery_failsafe ∧ F_(T_batt,∞) battery_failsafe))` | `low_voltage_start`：所选原始或压降补偿电压首次低于该实例阈值；电压，V；`AP_BattMonitor_Backend::check_failsafe_types`，[`libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp:243-272`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Backend.cpp#L243-L272)；观测：原始电压可由 `BATTERY_STATUS` 计算；压降补偿值需要插桩<br>`battery_failsafe`：该电池实例低电压事件已发生；带实例键的事件；参数元数据 [`AP_BattMonitor_Params.cpp:95-129`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/libraries/AP_BattMonitor/AP_BattMonitor_Params.cpp#L95-L129)；观测：需要插桩/状态文本；必须按电池实例关联 | `BATTx_LOW_TIMER` 默认 10 s、范围 0..120 s、冻结 Copter 的 `BATT_LOW_TIMER=10 s`；0 禁用；可修改。 | 可修改参数时间；源码参数元数据明确“more than”，下界为开；每个电池实例分别关联；飞控后端毫秒时钟。默认与冻结 SITL `BATT_LOW_TIMER=10 s`。 | 正例：T=10 s：低电压持续，t=10.000 s 不触发，t=10.001 s 触发，满足。<br>边界反例：t=10.000 s 触发，违反“超过”边界；若压降补偿源不可见则观测结论无法确认。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 11 | ARD-NEW-RTL-011 | 可修改参数决定下界 | 有条件必须满足 | RTL_LOIT_TIME is the time in milliseconds to hover/pause above the Home position before beginning final descent.<br>返航到 Home 上方并进入等待阶段后，运行参数 RTL_LOIT_TIME 到期前不得开始最终下降；到期后应最终开始下降。 | [RTL Mode — RTL_LOIT_TIME](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/rtl-mode.rst#L65-L69)，`copter/source/docs/rtl-mode.rst:65-69`；官方行为说明+参数元数据 | `G(enter_loiter_at_home → (G_[0,T_rtl) ¬begin_final_descent ∧ F_[T_rtl,∞) begin_final_descent))` | `enter_loiter_at_home`：RTL 进入 Home 上方等待子状态；内部状态进入事件；`ModeRTL::loiterathome_start` 与 `_loiter_start_time`，[`ArduCopter/mode_rtl.cpp:258-260`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode_rtl.cpp#L258-L260)；观测：需要插桩<br>`begin_final_descent`：RTL 开始最终下降阶段；内部子状态事件；`ModeRTL` 状态转换；参数定义 [`Parameters.cpp:80-87`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Parameters.cpp#L80-L87)；观测：需要插桩；仅看到最终 LAND 模式会丢失精确起点 | `RTL_LOIT_TIME` 默认 5000 ms、范围 0..60000 ms、冻结 SITL 5000 ms；可修改。 | 可修改参数时间，单位毫秒；默认 5000 ms，冻结 SITL 5000 ms；起点是内部 LOITER_AT_HOME 进入时间，飞控单调启动毫秒时钟；提前禁止区间右开。 | 正例：T=5000 ms：t<5000 不下降，t=5000 或之后进入最终下降，满足。<br>边界反例：t=4999 ms 已进入最终下降，违反；若只观察 HEARTBEAT 模式，无法定位内部阶段。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 12 | ARD-NEW-GUID-012 | 可修改参数决定下界 | 有条件必须满足 | If no attitude, velocity and/or acceleration commands are received for GUID_TIMEOUT seconds, the vehicle will slow to a stop or hold a level hover. The default setting is 3 seconds.<br>外部控制模式中相应指令持续缺失到运行时 GUID_TIMEOUT 后，速度/加速度控制应开始减速，姿态控制应开始回到水平悬停。 | [Guided Mode — GUID_TIMEOUT](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/ac2_guidedmode.rst#L115-L115)，`copter/source/docs/ac2_guidedmode.rst:115-115`；官方行为说明+参数元数据 | `G((guided_command_gap_start ∧ guided_timeout_applicable) → (G_[0,T_guid) ¬timeout_response_start ∧ F_[T_guid,∞) timeout_response_start))` | `guided_command_gap_start`：最后一条有效姿态/速度/加速度目标被飞控接受后缺失；消息接收事件；`handle_message_set_attitude_target` 等，[`ArduCopter/GCS_MAVLink_Copter.cpp:890-1074`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/GCS_MAVLink_Copter.cpp#L890-L1074)；观测：需要按消息类型和接受结果关联<br>`timeout_response_start`：减速到停止或水平悬停响应开始；控制器内部状态/过程；`GUID_TIMEOUT` 参数元数据，[`ArduCopter/Parameters.cpp:866-872`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Parameters.cpp#L866-L872)；观测：需要插桩；外部速度只能延迟派生 | `GUID_TIMEOUT` 默认 3.0 s、范围 0.1..5 s、冻结 SITL 3.0 s；可修改。 | 可修改参数时间；默认与冻结 SITL 均 3 s；起点是飞控接受最后一条适用指令，不是伴随计算机发送或地面端到达时刻；飞控单调启动时钟。 | 正例：T=3 s：t<3 不启动超时响应，t=3 或之后启动，满足。<br>边界反例：t=2.999 s 已启动，仅由该缺失导致则违反；若从发送端计时则时钟使用错误。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 13 | ARD-NEW-LOITER-013 | 无界性质 | 有条件必须满足 | When the sticks are released, the vehicle will slow to a stop and hold position.<br>定点模式下飞手释放控制杆后，飞行器应减速到停止并保持位置；飞手仍在输入时不适用。 | [Loiter Mode — overview and controls](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/loiter-mode.rst#L7-L24)，`copter/source/docs/loiter-mode.rst:7-24`；官方行为说明 | `G((Mode=LOITER ∧ sticks_released) → F_[0,∞)(stopped ∧ position_held))` | `Mode=LOITER`：当前模式为定点；模式枚举；`Mode::Number::LOITER`，[`ArduCopter/mode.h:83`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/mode.h#L83-L83)；观测：可直接观测：`HEARTBEAT.custom_mode`<br>`stopped ∧ position_held`：水平速度进入有来源容差并持续保持参考位置；速度/经纬度或局部位置；`current_loc` 与速度估计，[`ArduCopter/Copter.h:469`](https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/ArduCopter/Copter.h#L469-L469)；观测：可计算得到；容差没有官方数值时不得擅自下结论 | 速度、加速度与定点控制参数会影响响应，但本要求没有固定时间参数。 | 无界性质；官方没有承诺有限停止时间，不能人工添加秒数。轨迹顺序使用同一运行与同一坐标系。 | 正例：摇杆释放后，后续某时刻水平速度为零并保持位置，满足有限见证。<br>边界反例：完整有限测试终止前始终未停止，可作为测试反例；对无限语义的有限前缀只能暂时无法确认。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 14 | ARD-NEW-GUIDWAIT-014 | 无界性质 | 有条件必须满足 | Once the location is reached, the copter will hover at that location, waiting for the next target.<br>外部控制目标位置已经到达后，在收到新目标或切换模式以前，飞行器应在该位置悬停等待。 | [Guided Mode — overview](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/ac2_guidedmode.rst#L21-L25)，`copter/source/docs/ac2_guidedmode.rst:21-25`；官方行为说明 | `G((Mode=GUIDED ∧ target_reached) → (hover_at_target U (new_target ∨ mode_change)))` | `target_reached`：当前引导目标在当前坐标系中被判定达到；目标/导航状态；Guided 目标处理位于 `mode_guided.cpp`；论文旧 `Waypoint=empty` 无单一对应；观测：需要插桩<br>`hover_at_target`：位置与高度围绕目标保持；位置/高度/速度复合状态；`current_loc` 和 Guided 目标状态；观测：可计算得到；需要有来源的容差 | 位置速度参数影响控制，但不是本性质时间来源。 | 无界性质；持续到新目标或模式变化，没有有限秒数。`U` 是 until，中文为“保持前件直到后件发生”。 | 正例：t=0 到达目标，直到 t=8 新目标前持续悬停，满足。<br>边界反例：到达后且无新目标/模式变化时离开目标区域，违反。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |
| 15 | ARD-NEW-AUTO-015 | 无界性质 | 有条件必须满足 | During the mission the pilot’s roll, pitch and throttle inputs are ignored but the yaw can be overridden with the yaw stick. AUTO_OPTIONS can be set to always ignore pilot yaw input.<br>自动任务期间，横滚、俯仰和油门输入应被忽略；只有未配置忽略偏航时，偏航杆才允许覆盖。 | [Auto Mode — pilot input](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/auto-mode.rst#L62-L67)，`copter/source/docs/auto-mode.rst:62-67`；官方行为说明 | `G((Mode=AUTO ∧ mission_running) → (roll_pitch_throttle_ignored ∧ (¬ignore_pilot_yaw → yaw_override_allowed)))` | `roll_pitch_throttle_ignored`：改变这些飞手输入不会改变任务控制目标；需配对输入试验判定；输入—控制输出关系；AUTO 模式输入消费路径；模式枚举 `Mode::Number::AUTO`；观测：需要插桩或配对运行建模<br>`yaw_override_allowed`：未设置忽略位时偏航杆可改变航向目标；输入—目标关系；`AUTO_OPTIONS` 参数与 AUTO 控制路径；观测：需要插桩或配对运行建模 | `AUTO_OPTIONS` 决定是否始终忽略偏航；运行值必须在测试开始时读取，默认不等于实际配置。 | 无界状态性质；不是要求遥控输入本身保持不变，而是要求控制输出不受这些输入影响。 | 正例：AUTO 任务中改变横滚/俯仰/油门，任务目标不变；未忽略偏航时偏航目标随杆变化。<br>边界反例：只有横滚输入变化却改变任务横向目标，违反；必须排除同时发生的任务更新。<br>监视器结果：见总分析第九节；未进入执行门的性质不得解释为通过 | 未评估 |

## 公式逐条白话核对

### 1. ARD-NEW-VIBE-001：振动保护连续一秒触发

- 白话：启用振动保护、已解锁且不是人工油门模式时，三项估计器异常条件连续至少一秒，应进入高振动补偿状态。
- 形式化：`G((bad_vibe_start ∧ vibe_applicable ∧ G_[0,1s] bad_vibe_conditions) → (G_[0,1s) ¬high_vibes ∧ F_[1s,∞) high_vibes))`
- 来源：[Vibration Failsafe — When the failsafe will trigger](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/vibration-failsafe.rst#L17-L23)，固定行 `17-23`。
- 时间：官方固定时间 1 秒；起点为三项异常条件首次同时为真；条件恢复会取消；终点为 `high_vibes`；使用飞控单调启动毫秒时钟；文档没有给采样误差，边界受误差影响时判为无法确认。
- 参数：`FS_VIBE_ENABLE`：默认 1，冻结 SITL 值 1；可修改开关，不是时间参数。
- 正例：t=0 条件开始且持续；t=1.000 s 或其后 `high_vibes=true`，满足。
- 违反例：t=0 条件开始且持续；t=0.999 s 已置真，违反阈值前禁止；仅在 t=1.000 s 尚未置真不能单独判违反，因为来源没有有限最晚上界。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 2. ARD-NEW-VIBE-002：振动保护恢复十五秒后关闭

- 白话：高振动补偿已经开启后，估计器恢复正常并连续保持十五秒，应关闭高振动补偿。
- 形式化：`G((normal_vibe_start ∧ high_vibes ∧ G_[0,15s] normal_vibe) → (G_[0,15s) high_vibes ∧ F_[15s,∞) ¬high_vibes))`
- 来源：[Vibration Failsafe — Recovery from the failsafe](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/vibration-failsafe.rst#L34-L39)，固定行 `34-39`。
- 时间：官方固定时间 15 秒；起点为异常条件恢复正常；再次异常会重置恢复计时；终点为 `high_vibes=false`；飞控单调启动毫秒时钟。
- 参数：`FS_VIBE_ENABLE` 默认与 SITL 均为 1；可修改。
- 正例：t=0 恢复正常并保持；t=15.000 s 或其后关闭，满足。
- 违反例：t=14.999 s 已关闭，违反阈值前禁止；t=15.000 s 仍开启尚不足以在有限前缀判违反。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 3. ARD-NEW-TERRAIN-003：地形数据缺失两秒后的动作

- 白话：正在执行需要地形数据的任务时，如果连续两秒取不到地形数据，飞行中应转入返航，已着陆则应锁定。
- 形式化：`G((terrain_missing_start ∧ mission_requires_terrain ∧ G_[0,2s] terrain_missing) → (G_[0,2s) ¬terrain_action ∧ F_[2s,∞) terrain_action))`
- 来源：[Terrain Following — Failsafe in case of no Terrain data](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/terrain-following.rst#L74-L78)，固定行 `74-78`。
- 时间：官方固定时间 2 秒；`terrain_action=((flying ∧ Mode=RTL) ∨ (landed ∧ disarmed))`。起点为需要地形数据时首次取数失败；恢复数据会取消；飞控单调启动时钟。冻结源码常量是 5 秒，与文档 2 秒冲突；冲突是测试目标，不修改规范。
- 参数：无时间参数；当前源码 `FS_TERRAIN_TIMEOUT_MS=5000` 是实现常量，不是从官方要求推导的新时间。
- 正例：t=0 连续缺地形；飞行中 t=2.000 s 或其后进入 RTL，满足。
- 违反例：t=1.999 s 已仅因该缺失进入 RTL，违反提前禁止；源码 5 秒常量不能改变规范阈值。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 4. ARD-NEW-RUDDER-004：左舵保持两秒锁定

- 白话：在允许舵量锁定的模式与配置下，油门最小并把方向舵保持在左侧两秒，应锁定电机。
- 形式化：`G((rudder_disarm_start ∧ rudder_disarm_enabled ∧ allowed_mode ∧ G_[0,2s](throttle_min ∧ rudder_left)) → (G_[0,2s) ¬disarmed ∧ F_[2s,∞) disarmed))`
- 来源：[Arming the Motors — Disarming the motors](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/arming_the_motors.rst#L52-L60)，固定行 `52-60`。
- 时间：官方固定时间 2 秒；起点为允许模式中油门最小且左舵达到有效阈值；中立或离开阈值重置；飞控单调启动时钟。当前共享 RC 代码使用 3000 ms，与文档冲突。
- 参数：`ARMING_RUDDER` 控制是否允许舵量锁定；不是固定时间来源。冻结源码内实现计时 3000 ms 仅记录冲突。
- 正例：t=0 左舵与最小油门开始；t=2.000 s 或其后锁定，满足。
- 违反例：t=1.999 s 已仅因该手势锁定，违反提前禁止；t=2.000 s 仍解锁的有限前缀尚不足以判永久违反。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 5. ARD-NEW-CHUTE-005：自动降落伞连续一秒释放

- 白话：自动开伞适用且四组条件连续满一秒时，应触发降落伞释放；手动释放不属于这条性质。
- 形式化：`G((auto_control_loss_start ∧ G_[0,1s] auto_chute_conditions) → (G_[0,1s) ¬parachute_released ∧ F_[1s,∞) parachute_released))`
- 来源：[Parachute — When will the parachute deploy?](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/common/source/docs/common-parachute.rst#L126-L137)，固定行 `126-137`。
- 时间：官方固定时间 1 秒；`auto_chute_conditions=(armed ∧ allowed_chute_mode ∧ not_climbing ∧ above_CHUTE_ALT_MIN)`。起点为首次检测到自动失控且高度门槛成立；条件恢复/模式不适用会取消；内部主循环计数对应飞控单调时间。
- 参数：`CHUTE_ALT_MIN` 默认 10 m；当前 Copter SITL 参数下载没有该参数，说明当前构建未纳入或未公开该功能，不能编造运行值。参数本身可配置。
- 正例：t=0 自动失控条件开始且持续；t=1.000 s 或其后释放，满足。
- 违反例：t=0.999 s 已仅因自动判据释放，违反提前禁止；到 t=1.000 s 未释放的有限前缀仍无法证明永不释放。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 6. ARD-NEW-CRASH-006：坠毁判据持续两秒后锁定

- 白话：坠毁检查已启用且附加内部门控适用时，官方列出的异常条件连续满两秒，应锁定电机。
- 形式化：`G((crash_condition_start ∧ crash_check_enabled ∧ G_[0,2s] crash_conditions) → (G_[0,2s) ¬disarmed ∧ F_[2s,∞) disarmed))`
- 来源：[Crash Check — When will the crash check disarm the motors?](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/crash_check.rst#L11-L28)，固定行 `11-28`。
- 时间：官方固定时间 2 秒；任一条件恢复即重置；飞控单调主循环时间。官方注释明确“附加内部门控可能适用”，所以其适用性必须作为前置条件。
- 参数：`FS_CRASH_CHECK` 默认 1，冻结 SITL 值 1，可修改开关；2 秒来自官方文本，不是参数。
- 正例：t=0 全部条件开始并持续；t=2.000 s 或其后锁定，满足。
- 违反例：t=1.999 s 已仅因该判据锁定，违反提前禁止；t=2.000 s 仍解锁的有限前缀尚不能证明无界最终义务失败。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 7. ARD-NEW-EKF-007：两项估计器方差异常一秒触发

- 白话：估计器保护启用且已具备有效原点后，罗盘、位置、速度三类方差中任意两类连续一秒超过运行时阈值，应触发 EKF 故障保护。
- 形式化：`G((two_variances_bad_start ∧ ekf_fs_enabled ∧ G_[0,1s] two_variances_bad) → (G_[0,1s) ¬ekf_failsafe ∧ F_[1s,∞) ekf_failsafe))`
- 来源：[EKF Failsafe — When will it trigger?](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/ekf-inav-failsafe.rst#L9-L13)，固定行 `9-13`。
- 时间：官方固定时间 1 秒；起点为任意两类方差首次同时超过阈值；恢复会衰减/重置；飞控 10 Hz 检查任务的单调时钟。
- 参数：`FS_EKF_THRESH` 默认 0.8，冻结 SITL 读取为约 0.8；可修改阈值，不改变 1 秒官方时间。
- 正例：t=0 两项方差越界并持续；t=1.000 s 或其后触发，满足。
- 违反例：t=0.999 s 已仅因该方差条件触发，违反提前禁止；t=1.000 s 尚未触发的有限前缀不能证明最终义务失败。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 8. ARD-NEW-GCS-008：地面站心跳丢失超时

- 白话：本次运行曾收到指定地面站心跳、保护启用且之后持续收不到心跳时，到运行参数 FS_GCS_TIMEOUT 之前不得触发；到期后应最终触发。
- 形式化：`G((gcs_gap_start ∧ seen_gcs_before ∧ gcs_fs_enabled) → (G_[0,T_gcs) ¬gcs_failsafe ∧ F_[T_gcs,∞) gcs_failsafe))`
- 来源：[GCS Failsafe](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/gcs-failsafe.rst#L6-L8)，固定行 `6-8`。
- 时间：可修改参数时间 `T_gcs=runtime(FS_GCS_TIMEOUT)`；默认 5 s，冻结 SITL 5 s；飞控收到指定 GCS 心跳的单调启动时间，不是地面端到达时间；下界闭合、提前区间右端开。
- 参数：`FS_GCS_TIMEOUT` 默认 5 s、范围 2..120 s、冻结 SITL 5 s；可修改，写入后何时重读未实测。
- 正例：SITL 值 5 s：t=0 最后心跳，t<5 不触发，t=5 或之后触发，满足。
- 违反例：t=4.999 s 已触发，违反提前禁止；若仅缺失但轨迹未结束，晚触发在无有限上界公式中仍无法判违反。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 9. ARD-NEW-RC-009：遥控链路丢失超时

- 白话：电台保护启用且此前有过遥控输入或飞行器已解锁时，遥控更新持续缺失超过运行时 RC_FS_TIMEOUT 后，应触发遥控故障保护。
- 形式化：`G((rc_gap_start ∧ rc_fs_enabled ∧ rc_seen_or_armed) → (G_[0,T_rc] ¬radio_failsafe ∧ F_(T_rc,∞) radio_failsafe))`
- 来源：[Radio Failsafe — When the failsafe will trigger](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/radio-failsafe.rst#L20-L32)，固定行 `20-32`。
- 时间：可修改参数时间，且官方写“more than”，所以 `T_rc` 处仍禁止，最终区间左端开；飞控最后有效 RC 更新的单调启动毫秒时钟。默认与冻结 SITL 均 1 s。
- 参数：`RC_FS_TIMEOUT` 默认 1.0 s、范围 0.1..10 s、冻结 SITL 1.0 s；可修改。
- 正例：T=1 s：t=1.000 s 尚不触发，t=1.001 s 触发，满足离散毫秒见证；这 1 ms 是采样网格，不是人工 epsilon。
- 违反例：t=1.000 s 已触发，违反开边界；缺失结束前无法以有限前缀证明“永不触发”。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 10. ARD-NEW-BATT-010：低电压持续超时

- 白话：选定电池实例的有效电压源持续低于非零阈值，严格超过运行时 LOW_TIMER 后，应产生该实例的低电压故障保护事件。
- 形式化：`G((low_voltage_start ∧ voltage_threshold_enabled) → (G_[0,T_batt] ¬battery_failsafe ∧ F_(T_batt,∞) battery_failsafe))`
- 来源：[Battery Failsafe — Advanced Settings](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/failsafe-battery.rst#L91-L96)，固定行 `91-96`。
- 时间：可修改参数时间；源码参数元数据明确“more than”，下界为开；每个电池实例分别关联；飞控后端毫秒时钟。默认与冻结 SITL `BATT_LOW_TIMER=10 s`。
- 参数：`BATTx_LOW_TIMER` 默认 10 s、范围 0..120 s、冻结 Copter 的 `BATT_LOW_TIMER=10 s`；0 禁用；可修改。
- 正例：T=10 s：低电压持续，t=10.000 s 不触发，t=10.001 s 触发，满足。
- 违反例：t=10.000 s 触发，违反“超过”边界；若压降补偿源不可见则观测结论无法确认。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 11. ARD-NEW-RTL-011：返航点上方等待后开始下降

- 白话：返航到 Home 上方并进入等待阶段后，运行参数 RTL_LOIT_TIME 到期前不得开始最终下降；到期后应最终开始下降。
- 形式化：`G(enter_loiter_at_home → (G_[0,T_rtl) ¬begin_final_descent ∧ F_[T_rtl,∞) begin_final_descent))`
- 来源：[RTL Mode — RTL_LOIT_TIME](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/rtl-mode.rst#L65-L69)，固定行 `65-69`。
- 时间：可修改参数时间，单位毫秒；默认 5000 ms，冻结 SITL 5000 ms；起点是内部 LOITER_AT_HOME 进入时间，飞控单调启动毫秒时钟；提前禁止区间右开。
- 参数：`RTL_LOIT_TIME` 默认 5000 ms、范围 0..60000 ms、冻结 SITL 5000 ms；可修改。
- 正例：T=5000 ms：t<5000 不下降，t=5000 或之后进入最终下降，满足。
- 违反例：t=4999 ms 已进入最终下降，违反；若只观察 HEARTBEAT 模式，无法定位内部阶段。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 12. ARD-NEW-GUID-012：外部控制指令缺失超时

- 白话：外部控制模式中相应指令持续缺失到运行时 GUID_TIMEOUT 后，速度/加速度控制应开始减速，姿态控制应开始回到水平悬停。
- 形式化：`G((guided_command_gap_start ∧ guided_timeout_applicable) → (G_[0,T_guid) ¬timeout_response_start ∧ F_[T_guid,∞) timeout_response_start))`
- 来源：[Guided Mode — GUID_TIMEOUT](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/ac2_guidedmode.rst#L115-L115)，固定行 `115-115`。
- 时间：可修改参数时间；默认与冻结 SITL 均 3 s；起点是飞控接受最后一条适用指令，不是伴随计算机发送或地面端到达时刻；飞控单调启动时钟。
- 参数：`GUID_TIMEOUT` 默认 3.0 s、范围 0.1..5 s、冻结 SITL 3.0 s；可修改。
- 正例：T=3 s：t<3 不启动超时响应，t=3 或之后启动，满足。
- 违反例：t=2.999 s 已启动，仅由该缺失导致则违反；若从发送端计时则时钟使用错误。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 13. ARD-NEW-LOITER-013：定点模式释放摇杆后保持

- 白话：定点模式下飞手释放控制杆后，飞行器应减速到停止并保持位置；飞手仍在输入时不适用。
- 形式化：`G((Mode=LOITER ∧ sticks_released) → F_[0,∞)(stopped ∧ position_held))`
- 来源：[Loiter Mode — overview and controls](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/loiter-mode.rst#L7-L24)，固定行 `7-24`。
- 时间：无界性质；官方没有承诺有限停止时间，不能人工添加秒数。轨迹顺序使用同一运行与同一坐标系。
- 参数：速度、加速度与定点控制参数会影响响应，但本要求没有固定时间参数。
- 正例：摇杆释放后，后续某时刻水平速度为零并保持位置，满足有限见证。
- 违反例：完整有限测试终止前始终未停止，可作为测试反例；对无限语义的有限前缀只能暂时无法确认。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 14. ARD-NEW-GUIDWAIT-014：到达外部目标后等待

- 白话：外部控制目标位置已经到达后，在收到新目标或切换模式以前，飞行器应在该位置悬停等待。
- 形式化：`G((Mode=GUIDED ∧ target_reached) → (hover_at_target U (new_target ∨ mode_change)))`
- 来源：[Guided Mode — overview](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/ac2_guidedmode.rst#L21-L25)，固定行 `21-25`。
- 时间：无界性质；持续到新目标或模式变化，没有有限秒数。`U` 是 until，中文为“保持前件直到后件发生”。
- 参数：位置速度参数影响控制，但不是本性质时间来源。
- 正例：t=0 到达目标，直到 t=8 新目标前持续悬停，满足。
- 违反例：到达后且无新目标/模式变化时离开目标区域，违反。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

### 15. ARD-NEW-AUTO-015：自动任务中的飞手输入处理

- 白话：自动任务期间，横滚、俯仰和油门输入应被忽略；只有未配置忽略偏航时，偏航杆才允许覆盖。
- 形式化：`G((Mode=AUTO ∧ mission_running) → (roll_pitch_throttle_ignored ∧ (¬ignore_pilot_yaw → yaw_override_allowed)))`
- 来源：[Auto Mode — pilot input](https://github.com/ArduPilot/ardupilot_wiki/blob/826ef054a04e23b1ceeb3fb01a4df1d270efebcd/copter/source/docs/auto-mode.rst#L62-L67)，固定行 `62-67`。
- 时间：无界状态性质；不是要求遥控输入本身保持不变，而是要求控制输出不受这些输入影响。
- 参数：`AUTO_OPTIONS` 决定是否始终忽略偏航；运行值必须在测试开始时读取，默认不等于实际配置。
- 正例：AUTO 任务中改变横滚/俯仰/油门，任务目标不变；未忽略偏航时偏航目标随杆变化。
- 违反例：只有横滚输入变化却改变任务横向目标，违反；必须排除同时发生的任务更新。
- 监视器结果：**见总分析第九节；未进入执行门的性质不得解释为通过**。
- 实现符合性：**未评估**。

## 覆盖摘要与诚实边界

- 纳入冻结语料文件：4,225 个；确定性关键词和文档结构扫描：4,225/4,225；产生预筛候选 19,003 条。
- 19,003 条预筛候选均已完成范围与证据闭合裁决，待上下文审核数为 0。逐条结果保存在既有裁决账本中：21 条候选跨度直接支撑 14 条已接受性质；`ARD-NEW-AUTO-015` 的官方段落未被关键词预筛命中，但经上下文阅读后接受；2,522 条属于 Plane/Rover 范围；10,348 条是不能单独产生规范的普通实现注释；724 条只有参数元数据或缺少完整条件—义务关系；5,388 条官方文本属于教程、建议、重复说明、接口列表，或没有闭合成可独立审核的义务，统一保留为“证据不足”。“证据不足”不是认定不存在规范，而是拒绝人工补造。
- 接受性质：15 条；其中官方固定时间 7 条，可修改参数决定时间下界 5 条，无界 3 条。
- 当前明确的规范—源码时间冲突候选：地形 2 秒对源码 5 秒；左舵锁定 2 秒对共享源码 3 秒。冲突只用于后续测试，不在这里下符合性结论。
- 排除规则：教程步骤/硬件说明不是飞控运行性质；“可能/建议”且没有确定结果的不接受；普通 if/计数器不能产生要求；没有可靠数值的“立即/尽快”不补时间；相同要求的多页面重复合并。
- 裁决方法边界：19,003 条先按系统范围、来源类别和接受性质的证据跨度逐条确定性分类，再对闭合性质做上下文阅读；不能把这种“逐候选裁决”写成逐字逐句人工阅读 19,003 次。TAMonitor 已入门实例与未进入执行门的原因见总分析第九节；监视验证不会变成实现符合性结论。
