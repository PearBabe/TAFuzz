# ArduPilot PGFuzz 历史性质目录

`MTL` 是度量时序逻辑；`AP` 是原子命题；`NOT_ASSESSED` 是未评估实现符合性。
`EXACT`、`MODELLED`、`UNRESOLVED` 分别表示精确绑定、建模绑定和未解决绑定；都不等于性质通过。

共 30 条性质、110 个 AP、5872 条作者依赖输入关联。

| 顺序 | 性质 | 中文说明 | 绑定/观测状态 | AP | 作者关联 | 公式参数 | 审核记录 |
|---:|---|---|---|---:|---:|---:|---|
| 1 | `A.RTL1` | 当前高度低于 RTL_ALT 时持续爬升，直到达到该高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 3 | 238 | 1 | [A.RTL1.md](properties/A.RTL1.md) / [A.RTL1.json](properties/A.RTL1.json) |
| 2 | `A.RTL2` | 达到返航高度且尚未到家时，保持高度并移动到返航参考位置。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 5 | 251 | 1 | [A.RTL2.md](properties/A.RTL2.md) / [A.RTL2.json](properties/A.RTL2.json) |
| 3 | `A.RTL3` | 达到返航高度并到达返航参考位置后进入着陆模式。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 4 | 251 | 1 | [A.RTL3.md](properties/A.RTL3.md) / [A.RTL3.json](properties/A.RTL3.json) |
| 4 | `A.RTL4` | 着陆模式触地后锁定电机。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 3 | 238 | 0 | [A.RTL4.md](properties/A.RTL4.md) / [A.RTL4.json](properties/A.RTL4.json) |
| 5 | `A.FLIP1` | 满足横滚、油门、高度和前一模式条件时才允许进入翻滚模式。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 8 | 241 | 0 | [A.FLIP1.md](properties/A.FLIP1.md) / [A.FLIP1.json](properties/A.FLIP1.json) |
| 6 | `A.FLIP2` | 翻滚模式特定横滚角区间内向右以每秒 400 度滚转。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 241 | 0 | [A.FLIP2.md](properties/A.FLIP2.md) / [A.FLIP2.json](properties/A.FLIP2.json) |
| 7 | `A.FLIP3` | 完成翻滚阶段后在未知 k 时间内恢复原始姿态。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 4 | 241 | 0 | [A.FLIP3.md](properties/A.FLIP3.md) / [A.FLIP3.json](properties/A.FLIP3.json) |
| 8 | `A.FLIPGeneral` | 应在 2.5 秒内完成翻滚并恢复原飞行模式。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 2 | 241 | 0 | [A.FLIPGeneral.md](properties/A.FLIPGeneral.md) / [A.FLIPGeneral.json](properties/A.FLIPGeneral.json) |
| 9 | `A.ALT_HOLD1` | 高度来源为气压计时采用气压计高度而非 GPS 高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 3 | 238 | 0 | [A.ALT_HOLD1.md](properties/A.ALT_HOLD1.md) / [A.ALT_HOLD1.json](properties/A.ALT_HOLD1.json) |
| 10 | `A.ALT_HOLD2` | 定高模式中油门位于中值时保持高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 3 | 239 | 0 | [A.ALT_HOLD2.md](properties/A.ALT_HOLD2.md) / [A.ALT_HOLD2.json](properties/A.ALT_HOLD2.json) |
| 11 | `A.CIRCLE1` | 绕圈模式中俯仰杆向上使半径持续减小到零。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 103 | 0 | [A.CIRCLE1.md](properties/A.CIRCLE1.md) / [A.CIRCLE1.json](properties/A.CIRCLE1.json) |
| 12 | `A.CIRCLE2` | 绕圈模式中俯仰杆向下使半径增加。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 3 | 103 | 0 | [A.CIRCLE2.md](properties/A.CIRCLE2.md) / [A.CIRCLE2.json](properties/A.CIRCLE2.json) |
| 13 | `A.CIRCLE3` | 顺时针绕圈时横滚杆向右使速度增加。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 104 | 0 | [A.CIRCLE3.md](properties/A.CIRCLE3.md) / [A.CIRCLE3.json](properties/A.CIRCLE3.json) |
| 14 | `A.CIRCLE4` | 逆时针绕圈时横滚杆向右使速度减小。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 104 | 0 | [A.CIRCLE4.md](properties/A.CIRCLE4.md) / [A.CIRCLE4.json](properties/A.CIRCLE4.json) |
| 15 | `A.CIRCLE5` | 逆时针绕圈时横滚杆向左使速度增加。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 104 | 0 | [A.CIRCLE5.md](properties/A.CIRCLE5.md) / [A.CIRCLE5.json](properties/A.CIRCLE5.json) |
| 16 | `A.CIRCLE6` | 顺时针绕圈时横滚杆向左使速度减小。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 104 | 0 | [A.CIRCLE6.md](properties/A.CIRCLE6.md) / [A.CIRCLE6.json](properties/A.CIRCLE6.json) |
| 17 | `A.CIRCLE7` | 绕圈模式忽略横滚、俯仰、偏航控制，但允许油门改变高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 5 | 173 | 0 | [A.CIRCLE7.md](properties/A.CIRCLE7.md) / [A.CIRCLE7.json](properties/A.CIRCLE7.json) |
| 18 | `A.LAND1` | 着陆模式高于 10 米时按 LAND_SPEED_HIGH 参数下降。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 3 | 239 | 1 | [A.LAND1.md](properties/A.LAND1.md) / [A.LAND1.json](properties/A.LAND1.json) |
| 19 | `A.LAND2` | 着陆模式低于 10 米时按 LAND_SPEED 参数下降。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 3 | 239 | 1 | [A.LAND2.md](properties/A.LAND2.md) / [A.LAND2.json](properties/A.LAND2.json) |
| 20 | `A.AUTO1` | 自动模式忽略横滚、俯仰和油门输入，但允许偏航覆盖。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 5 | 173 | 0 | [A.AUTO1.md](properties/A.AUTO1.md) / [A.AUTO1.json](properties/A.AUTO1.json) |
| 21 | `A.BRAKE1` | 制动模式中应在未知 k 时间内停止。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 2 | 190 | 0 | [A.BRAKE1.md](properties/A.BRAKE1.md) / [A.BRAKE1.json](properties/A.BRAKE1.json) |
| 22 | `A.DRIFT1` | 漂移模式中 GPS 丢失后按 FS_EKF_ACTION 进入着陆或定高模式。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 3 | 117 | 1 | [A.DRIFT1.md](properties/A.DRIFT1.md) / [A.DRIFT1.json](properties/A.DRIFT1.json) |
| 23 | `A.LOITER1` | 定点盘旋模式保持位置、航向和高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 4 | 251 | 0 | [A.LOITER1.md](properties/A.LOITER1.md) / [A.LOITER1.json](properties/A.LOITER1.json) |
| 24 | `A.GUIDED1` | 引导模式没有剩余航点时保持位置、航向和高度。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 5 | 251 | 0 | [A.GUIDED1.md](properties/A.GUIDED1.md) / [A.GUIDED1.json](properties/A.GUIDED1.json) |
| 25 | `A.SPORT1` | 运动模式按 PILOT_SPEED_UP 参数爬升。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 2 | 239 | 1 | [A.SPORT1.md](properties/A.SPORT1.md) / [A.SPORT1.json](properties/A.SPORT1.json) |
| 26 | `A.RC.FS1` | 已解锁的特技模式中油门低于阈值时立即锁定。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 4 | 240 | 1 | [A.RC.FS1.md](properties/A.RC.FS1.md) / [A.RC.FS1.json](properties/A.RC.FS1.json) |
| 27 | `A.RC.FS2` | 油门低于 FS_THR_VALUE 时开启遥控故障保护。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 2 | 240 | 1 | [A.RC.FS2.md](properties/A.RC.FS2.md) / [A.RC.FS2.json](properties/A.RC.FS2.json) |
| 28 | `A.CHUTE1` | 释放降落伞要求电机已解锁、模式允许、没有爬升且高于最低开伞高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 5 | 243 | 1 | [A.CHUTE1.md](properties/A.CHUTE1.md) / [A.CHUTE1.json](properties/A.CHUTE1.json) |
| 29 | `A.GPS.FS1` | 检测到的 GPS 卫星少于四颗时触发 GPS 故障保护。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 2 | 118 | 0 | [A.GPS.FS1.md](properties/A.GPS.FS1.md) / [A.GPS.FS1.json](properties/A.GPS.FS1.json) |
| 30 | `A.GPS.FS2` | GPS 故障保护触发且气压计可用时改用气压计高度来源。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 3 | 118 | 0 | [A.GPS.FS2.md](properties/A.GPS.FS2.md) / [A.GPS.FS2.json](properties/A.GPS.FS2.json) |

所有 `implementation_satisfaction` 均为 `NOT_ASSESSED`，只表示尚未评估，不表示满足。
