# PGFuzz Table XII 公式与原子命题清单

本文件忠实保存论文表十二转录，并把用于源码绑定的解释单独列出。所有条目均为历史性质种子；不表示当前官方规范已经确认，也不表示当前实现满足性质。

## 状态说明

- `AP`：`Atomic Proposition`，中文为“原子命题”；表示公式中能够单独判断真假的最小条件。
- `HISTORICAL_PROPERTY_SEED`：历史性质种子；仅说明它来自 PGFuzz 论文，不确认它是当前官方规范。
- `NOT_ASSESSED`：未评估；不判断当前固件是否满足该性质。

角色说明：

- `antecedent`：论文印刷公式的蕴含前件，即触发或前置条件。
- `consequent`：论文印刷公式的蕴含后件，即作者要求出现或保持的结果。
- `negated_consequent`：论文印刷公式后件中带否定的条件；不代表自然语言一定采用相同极性。
- `consequent_disjunct`：论文印刷公式后件中的析取分支；其作用范围可能受括号歧义影响。
- `antecedent_as_printed`：只来自论文印刷公式的前件，已知可能与自然语言冲突。
- `consequent_as_printed`：只来自论文印刷公式的后件，已知可能弱化或误写自然语言要求。
- `antecedent_from_description`：来自同一行英文自然语言、但被印刷公式遗漏的前件；不用于静默改写原式。
- `condition_from_description`：来自同一行英文自然语言的条件，用于显示自然语言与公式的差异。
- `target_from_description`：来自同一行英文自然语言的目标状态；印刷公式没有完整表达它。

## 总览

| 顺序 | 系统 | 性质 | 模板 | 原子命题数 | 制品目录 | 问题数 |
|---:|---|---|---|---:|---|---:|
| 1 | ArduPilot | `A.RTL1` | `T3` | 3 | `A.RTL1` | 2 |
| 2 | ArduPilot | `A.RTL2` | `T3` | 5 | `A.RTL2` | 2 |
| 3 | ArduPilot | `A.RTL3` | `T3` | 4 | `A.RTL3` | 1 |
| 4 | ArduPilot | `A.RTL4` | `T3` | 3 | `A.RTL4` | 2 |
| 5 | ArduPilot | `A.FLIP1` | `T2` | 8 | `A.FLIP1` | 4 |
| 6 | ArduPilot | `A.FLIP2` | `T3` | 4 | `A.FLIP2` | 1 |
| 7 | ArduPilot | `A.FLIP3` | `T1&T3` | 4 | `A.FLIP3` | 3 |
| 8 | ArduPilot | `A.FLIPGeneral` | `T1` | 2 | `A.FLIP4` | 2 |
| 9 | ArduPilot | `A.ALT_HOLD1` | `T3` | 3 | `A.ALT_HOLD1` | 2 |
| 10 | ArduPilot | `A.ALT_HOLD2` | `T3` | 3 | `A.ALT_HOLD2` | 2 |
| 11 | ArduPilot | `A.CIRCLE1` | `T3` | 4 | `A.CIRCLE1` | 2 |
| 12 | ArduPilot | `A.CIRCLE2` | `T3` | 3 | `A.CIRCLE2` | 1 |
| 13 | ArduPilot | `A.CIRCLE3` | `T3` | 4 | `A.CIRCLE3` | 2 |
| 14 | ArduPilot | `A.CIRCLE4` | `T3` | 4 | `A.CIRCLE4_6` | 2 |
| 15 | ArduPilot | `A.CIRCLE5` | `T3` | 4 | `A.CIRCLE4_6` | 2 |
| 16 | ArduPilot | `A.CIRCLE6` | `T3` | 4 | `A.CIRCLE4_6` | 2 |
| 17 | ArduPilot | `A.CIRCLE7` | `T3` | 5 | `A.CIRCLE7` | 3 |
| 18 | ArduPilot | `A.LAND1` | `T3` | 3 | `A.LAND1` | 3 |
| 19 | ArduPilot | `A.LAND2` | `T3` | 3 | `A.LAND2` | 3 |
| 20 | ArduPilot | `A.AUTO1` | `T3` | 5 | `A.AUTO1` | 3 |
| 21 | ArduPilot | `A.BRAKE1` | `T1` | 2 | `A.BRAKE1` | 3 |
| 22 | ArduPilot | `A.DRIFT1` | `T1` | 3 | `A.DRIFT1` | 2 |
| 23 | ArduPilot | `A.LOITER1` | `T3` | 4 | `A.LOITER1` | 2 |
| 24 | ArduPilot | `A.GUIDED1` | `T3` | 5 | `A.GUIDED1` | 3 |
| 25 | ArduPilot | `A.SPORT1` | `T3` | 2 | `A.SPORT1` | 2 |
| 26 | ArduPilot | `A.RC.FS1` | `T3` | 4 | `A.RC.FS1` | 3 |
| 27 | ArduPilot | `A.RC.FS2` | `T3` | 2 | `A.RC.FS2` | 0 |
| 28 | ArduPilot | `A.CHUTE1` | `T2` | 5 | `A.CHUTE` | 1 |
| 29 | ArduPilot | `A.GPS.FS1` | `T3` | 2 | `A.GPS.FS1` | 1 |
| 30 | ArduPilot | `A.GPS.FS2` | `T3` | 3 | `A.GPS.FS2` | 2 |

## A.RTL1

- 英文原文：If the current altitude is less than RTL_ALT, then altitude must be increased until the altitude is greater or equal to RTL_ALT.
- 中文说明：当前高度低于 RTL_ALT 时持续爬升，直到达到该高度。
- 论文模板：`T3`
- 论文原式转录：`G(((ALT_t < RTL_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))`
- 绑定用解释：`G(((ALT_t < RTL_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))`
- PGFuzz 制品目录：`A.RTL1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `ALT_t < RTL_ALT` | 当前高度低于 ArduPilot 返航高度参数。 | `ALT_t`, `RTL_ALT` |
| AP02 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP03 | `consequent` | `ALT_t-1 < ALT_t` | 当前观测高度高于上一观测高度。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `UNTIL_LOST`：自然语言包含‘直到达到目标’，论文公式只要求相邻观测朝目标变化。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## A.RTL2

- 英文原文：If the current altitude is greater or equal to RTL_ALT, current flight mode is RTL, and the current vehicle is not at home position, then the vehicle must move to the home position while maintaining the current altitude.
- 中文说明：达到返航高度且尚未到家时，保持高度并移动到返航参考位置。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = RTL) & (ALT_t >= RTL_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))`
- 绑定用解释：`G(((Mode_t = RTL) & (ALT_t >= RTL_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))`
- PGFuzz 制品目录：`A.RTL2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP02 | `antecedent` | `ALT_t >= RTL_ALT` | 当前高度达到或超过 ArduPilot 返航高度参数。 | `ALT_t`, `RTL_ALT` |
| AP03 | `antecedent` | `Pos_t != home_position` | 当前位置不等于返航参考位置。 | `Pos_t`, `home_position` |
| AP04 | `consequent` | `Pos_t-1 != Pos_t` | 当前位置与上一观测位置不同。 | `Pos_t-1`, `Pos_t` |
| AP05 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## A.RTL3

- 英文原文：If current altitude is greater or equal to RTL_ALT and current position is the same as home position, then flight mode must be LAND.
- 中文说明：达到返航高度并到达返航参考位置后进入着陆模式。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = RTL) & (ALT_t >= RTL_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))`
- 绑定用解释：`G(((Mode_t = RTL) & (ALT_t >= RTL_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))`
- PGFuzz 制品目录：`A.RTL3`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP02 | `antecedent` | `ALT_t >= RTL_ALT` | 当前高度达到或超过 ArduPilot 返航高度参数。 | `ALT_t`, `RTL_ALT` |
| AP03 | `antecedent` | `Pos_t = home_position` | 当前位置等于返航参考位置。 | `Pos_t`, `home_position` |
| AP04 | `consequent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |

问题与限制：

- `SAME_SAMPLE_MODE_CONTRADICTION`：同一采样点的前件和后件要求互斥飞行模式。

## A.RTL4

- 英文原文：If current flight mode is LAND and the vehicle touches the ground, then the vehicle must disarm motors.
- 中文说明：着陆模式触地后锁定电机。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = LAND) & (ALT_t = GroundALT)) -> (Disarm = on))`
- 绑定用解释：`G(((Mode_t = LAND) & (ALT_t = GroundALT)) -> (Disarm = on))`
- PGFuzz 制品目录：`A.RTL4`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |
| AP02 | `antecedent` | `ALT_t = GroundALT` | 当前高度严格等于论文所称地面高度。 | `ALT_t`, `GroundALT` |
| AP03 | `consequent` | `Disarm = on` | 电机处于锁定状态。 | `Disarm` |

问题与限制：

- `IMMEDIACY_UNBOUNDED`：自然语言写‘立即’，公式没有可追溯的时间界限。
- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。

## A.FLIP1

- 英文原文：If and only if roll is less than 45 degree, throttle is greater or equal to 1,500, altitude is more than 10 meters, and the current flight mode is one of ACRO and ALT_HOLD, then the flight mode can be changed to FLIP.
- 中文说明：满足横滚、油门、高度和前一模式条件时才允许进入翻滚模式。
- 论文模板：`T2`
- 论文原式转录：`G((Mode_t = FLIP) -> ((Mode_t-1 = ACRO/ALT_HOLD) & !(Roll_t > 45) | (Throttle_t <= 1500) | (ALT_t < 10)))`
- 绑定用解释：`G((Mode_t = FLIP) -> ((Mode_t-1 = ACRO/ALT_HOLD) & !(Roll_t > 45) | (Throttle_t <= 1500) | (ALT_t < 10)))`
- PGFuzz 制品目录：`A.FLIP1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = FLIP` | 当前飞行模式是翻滚模式。 | `Mode_t`, `FLIP` |
| AP02 | `consequent` | `Mode_t-1 in {ACRO,ALT_HOLD}` | 上一观测模式是特技或定高模式。 | `Mode_t-1`, `ACRO`, `ALT_HOLD` |
| AP03 | `negated_consequent` | `Roll_t > 45deg` | 当前横滚角大于 45 度。 | `Roll_t` |
| AP04 | `consequent_disjunct` | `Throttle_t <= 1500` | 当前油门通道值不超过 1500。 | `Throttle_t` |
| AP05 | `consequent_disjunct` | `ALT_t < 10m` | 当前高度低于 10 米。 | `ALT_t` |
| AP06 | `condition_from_description` | `Roll_t < 45deg` | 当前横滚角小于 45 度；该条件来自论文自然语言，不是印刷公式中的同向原子。 | `Roll_t` |
| AP07 | `condition_from_description` | `Throttle_t >= 1500` | 当前油门通道值达到或超过 1500；该条件来自论文自然语言。 | `Throttle_t` |
| AP08 | `condition_from_description` | `ALT_t > 10m` | 当前高度高于 10 米；该条件来自论文自然语言。 | `ALT_t` |

问题与限制：

- `IFF_NOT_ENCODED`：自然语言使用‘当且仅当’，公式只编码单向蕴含。
- `PRECEDENCE_AMBIGUOUS`：合取、析取和蕴含的括号不足，逻辑优先级不唯一。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DESCRIPTION_FORMULA_POLARITY_CONFLICT`：自然语言给出允许进入的正向条件，论文公式却混入其反向条件；不能把两者当作同一逻辑表达。

## A.FLIP2

- 英文原文：If the current flight mode is FLIP and roll is between -90 and 45 degree, then rolling right at 400 degree per second.
- 中文说明：翻滚模式特定横滚角区间内向右以每秒 400 度滚转。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = FLIP) & (-90 <= Roll_t <= 45)) -> ((Roll_rate = 400) & (Roll_direction = right)))`
- 绑定用解释：`G(((Mode_t = FLIP) & (-90 <= Roll_t <= 45)) -> ((Roll_rate = 400) & (Roll_direction = right)))`
- PGFuzz 制品目录：`A.FLIP2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = FLIP` | 当前飞行模式是翻滚模式。 | `Mode_t`, `FLIP` |
| AP02 | `antecedent` | `-90deg <= Roll_t <= 45deg` | 当前横滚角位于负 90 度到 45 度之间。 | `Roll_t` |
| AP03 | `consequent` | `Roll_rate = 400deg/s` | 横滚角速度严格等于每秒 400 度。 | `Roll_rate` |
| AP04 | `consequent` | `Roll_direction = right` | 横滚方向为右。 | `Roll_direction` |

问题与限制：

- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。

## A.FLIP3

- 英文原文：After the vehicle finishes A.FLIP2, the vehicle must recover the original attitude (i.e., roll, pitch, and yaw) within k seconds.
- 中文说明：完成翻滚阶段后在未知 k 时间内恢复原始姿态。
- 论文模板：`T1&T3`
- 论文原式转录：`G((Mode_t = FLIP3) -> ((Roll_t = F_[0,k] Roll_original) & (Pitch_t = F_[0,k] Pitch_original) & (Yaw_t = F_[0,k] Yaw_original)))`
- 绑定用解释：`G((Mode_t = FLIP3) -> ((Roll_t = F_[0,k] Roll_original) & (Pitch_t = F_[0,k] Pitch_original) & (Yaw_t = F_[0,k] Yaw_original)))`
- PGFuzz 制品目录：`A.FLIP3`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = FLIP3` | 论文内部的 FLIP3 恢复阶段标签成立。 | `Mode_t`, `FLIP3` |
| AP02 | `consequent` | `F_[0,k](Roll_t = Roll_original)` | 在未知 k 时间内横滚恢复到原值。 | `Roll_t`, `Roll_original`, `k` |
| AP03 | `consequent` | `F_[0,k](Pitch_t = Pitch_original)` | 在未知 k 时间内俯仰恢复到原值。 | `Pitch_t`, `Pitch_original`, `k` |
| AP04 | `consequent` | `F_[0,k](Yaw_t = Yaw_original)` | 在未知 k 时间内偏航恢复到原值。 | `Yaw_t`, `Yaw_original`, `k` |

问题与限制：

- `MALFORMED_EVENTUAL_EQUALITY`：论文把等式与 eventually 运算符错误连接，不能按标准 MTL 直接解析。
- `PHASE_SENTINEL_UNGROUNDED`：FLIP1/FLIP3 是论文阶段标签，不是已证明存在的飞行模式状态。
- `EMPIRICAL_K_NOT_NORMATIVE`：k 来自论文仿真经验或未公开测量，不是当前官方时间要求。

## A.FLIPGeneral

- 英文原文：The vehicle should complete the rolling (A.FLIP2) within 2.5 seconds and must return to the original flight mode.
- 中文说明：应在 2.5 秒内完成翻滚并恢复原飞行模式。
- 论文模板：`T1`
- 论文原式转录：`G((Mode_t = FLIP1) -> F_[0,2.5](Mode_t = FLIP3))`
- 绑定用解释：`G((Mode_t = FLIP1) -> F_[0,2.5](Mode_t = FLIP3))`
- PGFuzz 制品目录：`A.FLIP4`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = FLIP1` | 论文内部的 FLIP1 开始阶段标签成立。 | `Mode_t`, `FLIP1` |
| AP02 | `consequent` | `F_[0,2.5s](Mode_t = FLIP3)` | 2.5 秒内到达论文的 FLIP3 阶段。 | `Mode_t`, `FLIP3` |

问题与限制：

- `PHASE_SENTINEL_UNGROUNDED`：FLIP1/FLIP3 是论文阶段标签，不是已证明存在的飞行模式状态。
- `RETURN_ORIGINAL_MODE_OMITTED`：自然语言要求恢复原飞行模式，公式只检查阶段标签变化。

## A.ALT_HOLD1

- 英文原文：If the altitude source is the barometer, the vehicle must follow the altitude computed by this source, rather than the GPS.
- 中文说明：高度来源为气压计时采用气压计高度而非 GPS 高度。
- 论文模板：`T3`
- 论文原式转录：`G((ALT_src = Baro) -> ((ALT_t = ALT_Baro) & (ALT_t != ALT_GPS)))`
- 绑定用解释：`G((ALT_src = Baro) -> ((ALT_t = ALT_Baro) & (ALT_t != ALT_GPS)))`
- PGFuzz 制品目录：`A.ALT_HOLD1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `ALT_src = Baro` | 论文抽象的高度来源被标记为气压计。 | `ALT_src`, `Baro` |
| AP02 | `consequent` | `ALT_t = ALT_Baro` | 当前高度严格等于气压计高度。 | `ALT_t`, `ALT_Baro` |
| AP03 | `consequent` | `ALT_t != ALT_GPS` | 当前高度不等于 GPS 高度。 | `ALT_t`, `ALT_GPS` |

问题与限制：

- `SOURCE_ABSTRACTION_UNDEFINED`：高度来源、Baro/GPS 高度的坐标系和融合语义没有定义。
- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。

## A.ALT_HOLD2

- 英文原文：If the throttle stick is in the middle (i.e., 1,500) the vehicle must maintain the current altitude.
- 中文说明：定高模式中油门位于中值时保持高度。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = ALT_HOLD) & (Throttle_t = 1500)) -> (ALT_t = ALT_t-1))`
- 绑定用解释：`G(((Mode_t = ALT_HOLD) & (Throttle_t = 1500)) -> (ALT_t = ALT_t-1))`
- PGFuzz 制品目录：`A.ALT_HOLD2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ALT_HOLD` | 当前模式是 ArduPilot 定高模式。 | `Mode_t`, `ALT_HOLD` |
| AP02 | `antecedent` | `Throttle_t = 1500` | 油门输入严格等于通道中值 1500。 | `Throttle_t` |
| AP03 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## A.CIRCLE1

- 英文原文：Pitch stick up must reduce the radius until it reaches zero.
- 中文说明：绕圈模式中俯仰杆向上使半径持续减小到零。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = CIRCLE) & (RC_pitch < 1500) & (Circle_radius_t > 0)) -> (Circle_radius_t < Circle_radius_t-1))`
- 绑定用解释：`G(((Mode_t = CIRCLE) & (RC_pitch < 1500) & (Circle_radius_t > 0)) -> (Circle_radius_t < Circle_radius_t-1))`
- PGFuzz 制品目录：`A.CIRCLE1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `antecedent` | `RC_pitch < 1500` | 俯仰遥控输入小于通道中值。 | `RC_pitch` |
| AP03 | `antecedent` | `Circle_radius_t > 0` | 当前绕圈半径为正数。 | `Circle_radius_t` |
| AP04 | `consequent` | `Circle_radius_t < Circle_radius_t-1` | 绕圈半径比上一观测减小。 | `Circle_radius_t`, `Circle_radius_t-1` |

问题与限制：

- `UNTIL_LOST`：自然语言包含‘直到达到目标’，论文公式只要求相邻观测朝目标变化。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## A.CIRCLE2

- 英文原文：Pitch stick down must increase the radius.
- 中文说明：绕圈模式中俯仰杆向下使半径增加。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = CIRCLE) & (RC_pitch > 1500)) -> (Circle_radius_t > Circle_radius_t-1))`
- 绑定用解释：`G(((Mode_t = CIRCLE) & (RC_pitch > 1500)) -> (Circle_radius_t > Circle_radius_t-1))`
- PGFuzz 制品目录：`A.CIRCLE2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `antecedent` | `RC_pitch > 1500` | 俯仰遥控输入大于通道中值。 | `RC_pitch` |
| AP03 | `consequent` | `Circle_radius_t > Circle_radius_t-1` | 绕圈半径比上一观测增大。 | `Circle_radius_t`, `Circle_radius_t-1` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## A.CIRCLE3

- 英文原文：Roll stick right (think clockwise) must increase the speed while moving clockwise.
- 中文说明：顺时针绕圈时横滚杆向右使速度增加。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = CIRCLE) & (RC_roll > 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t > Circle_speed_t-1))`
- 绑定用解释：`G(((Mode_t = CIRCLE) & (RC_roll > 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t > Circle_speed_t-1))`
- PGFuzz 制品目录：`A.CIRCLE3`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `antecedent` | `RC_roll > 1500` | 横滚遥控输入大于通道中值。 | `RC_roll` |
| AP03 | `antecedent` | `Circle_direction_t = clockwise` | 绕圈方向是顺时针。 | `Circle_direction_t` |
| AP04 | `consequent` | `Circle_speed_t > Circle_speed_t-1` | 绕圈速度比上一观测增大。 | `Circle_speed_t`, `Circle_speed_t-1` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.CIRCLE4

- 英文原文：Roll stick right (think clockwise) must decrease the speed while moving counterclockwise.
- 中文说明：逆时针绕圈时横滚杆向右使速度减小。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = CIRCLE) & (RC_roll > 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t < Circle_speed_t-1))`
- 绑定用解释：`G(((Mode_t = CIRCLE) & (RC_roll > 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t < Circle_speed_t-1))`
- PGFuzz 制品目录：`A.CIRCLE4_6`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `antecedent` | `RC_roll > 1500` | 横滚遥控输入大于通道中值。 | `RC_roll` |
| AP03 | `antecedent` | `Circle_direction_t = counterclockwise` | 绕圈方向是逆时针。 | `Circle_direction_t` |
| AP04 | `consequent` | `Circle_speed_t < Circle_speed_t-1` | 绕圈速度比上一观测减小。 | `Circle_speed_t`, `Circle_speed_t-1` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.CIRCLE5

- 英文原文：Roll stick left (think counterclockwise) must increase the speed while moving counterclockwise.
- 中文说明：逆时针绕圈时横滚杆向左使速度增加。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = CIRCLE) & (RC_roll < 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t > Circle_speed_t-1))`
- 绑定用解释：`G(((Mode_t = CIRCLE) & (RC_roll < 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t > Circle_speed_t-1))`
- PGFuzz 制品目录：`A.CIRCLE4_6`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `antecedent` | `RC_roll < 1500` | 横滚遥控输入小于通道中值。 | `RC_roll` |
| AP03 | `antecedent` | `Circle_direction_t = counterclockwise` | 绕圈方向是逆时针。 | `Circle_direction_t` |
| AP04 | `consequent` | `Circle_speed_t > Circle_speed_t-1` | 绕圈速度比上一观测增大。 | `Circle_speed_t`, `Circle_speed_t-1` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.CIRCLE6

- 英文原文：Roll stick left (think counterclockwise) must decrease the speed while moving clockwise.
- 中文说明：顺时针绕圈时横滚杆向左使速度减小。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = CIRCLE) & (RC_roll < 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t < Circle_speed_t-1))`
- 绑定用解释：`G(((Mode_t = CIRCLE) & (RC_roll < 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t < Circle_speed_t-1))`
- PGFuzz 制品目录：`A.CIRCLE4_6`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `antecedent` | `RC_roll < 1500` | 横滚遥控输入小于通道中值。 | `RC_roll` |
| AP03 | `antecedent` | `Circle_direction_t = clockwise` | 绕圈方向是顺时针。 | `Circle_direction_t` |
| AP04 | `consequent` | `Circle_speed_t < Circle_speed_t-1` | 绕圈速度比上一观测减小。 | `Circle_speed_t`, `Circle_speed_t-1` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.CIRCLE7

- 英文原文：The users do not have any control over the roll, pitch, and yaw but can change the altitude with the throttle stick.
- 中文说明：绕圈模式忽略横滚、俯仰、偏航控制，但允许油门改变高度。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = CIRCLE) -> ((RC_roll_t/RC_pitch_t/RC_yaw_t = RC_roll_t-1/RC_pitch_t-1/RC_yaw_t-1) & ((RC_throttle_t <= RC_throttle_t-1) | (RC_throttle_t >= RC_throttle_t-1))))`
- 绑定用解释：`G((Mode_t = CIRCLE) -> ((RC_roll_t/RC_pitch_t/RC_yaw_t = RC_roll_t-1/RC_pitch_t-1/RC_yaw_t-1) & ((RC_throttle_t <= RC_throttle_t-1) | (RC_throttle_t >= RC_throttle_t-1))))`
- PGFuzz 制品目录：`A.CIRCLE7`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = CIRCLE` | 当前模式是 ArduPilot 绕圈模式。 | `Mode_t`, `CIRCLE` |
| AP02 | `consequent` | `RC_roll_t = RC_roll_t-1` | 横滚输入与上一观测严格相等。 | `RC_roll_t`, `RC_roll_t-1` |
| AP03 | `consequent` | `RC_pitch_t = RC_pitch_t-1` | 俯仰输入与上一观测严格相等。 | `RC_pitch_t`, `RC_pitch_t-1` |
| AP04 | `consequent` | `RC_yaw_t = RC_yaw_t-1` | 偏航输入与上一观测严格相等。 | `RC_yaw_t`, `RC_yaw_t-1` |
| AP05 | `consequent` | `RC_throttle_t <= RC_throttle_t-1 or RC_throttle_t >= RC_throttle_t-1` | 油门输入不大于或不小于上一值；对普通数值是恒真析取。 | `RC_throttle_t`, `RC_throttle_t-1` |

问题与限制：

- `CONTROL_EFFECT_CONFUSED_WITH_INPUT`：自然语言描述输入应被忽略，公式却限制输入本身不变化。
- `TAUTOLOGICAL_INPUT_CHANGE`：小于等于或大于等于上一值的析取对普通数值总成立，不能约束行为。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## A.LAND1

- 英文原文：Above 10 meters the vehicle must descend at the rate specified in the LAND_SPEED_HIGH parameter.
- 中文说明：着陆模式高于 10 米时按 LAND_SPEED_HIGH 参数下降。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = LAND) & (ALT_t >= 10) &) -> (Speed_vertical_t = LAND_SPEED_HIGH))`
- 绑定用解释：`G(((Mode_t = LAND) & (ALT_t >= 10) &) -> (Speed_vertical_t = LAND_SPEED_HIGH))`
- PGFuzz 制品目录：`A.LAND1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |
| AP02 | `antecedent` | `ALT_t >= 10m` | 当前高度达到或超过 10 米。 | `ALT_t` |
| AP03 | `consequent` | `Speed_vertical_t = LAND_SPEED_HIGH` | 垂直速度严格等于高空着陆速度参数。 | `Speed_vertical_t`, `LAND_SPEED_HIGH` |

问题与限制：

- `FORMULA_SYNTAX_EXTRA_CONJUNCTION`：论文公式在蕴含前出现多余合取符号。
- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.LAND2

- 英文原文：Below 10 meters the vehicle must descend at the rate specified in the LAND_SPEED parameter.
- 中文说明：着陆模式低于 10 米时按 LAND_SPEED 参数下降。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = LAND) & (ALT_t < 10) &) -> (Speed_vertical_t = LAND_SPEED))`
- 绑定用解释：`G(((Mode_t = LAND) & (ALT_t < 10) &) -> (Speed_vertical_t = LAND_SPEED))`
- PGFuzz 制品目录：`A.LAND2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |
| AP02 | `antecedent` | `ALT_t < 10m` | 当前高度低于 10 米。 | `ALT_t` |
| AP03 | `consequent` | `Speed_vertical_t = LAND_SPEED` | 垂直速度严格等于低空着陆速度参数。 | `Speed_vertical_t`, `LAND_SPEED` |

问题与限制：

- `FORMULA_SYNTAX_EXTRA_CONJUNCTION`：论文公式在蕴含前出现多余合取符号。
- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.AUTO1

- 英文原文：The pilot's roll, pitch and throttle inputs must be ignored but the yaw can be overridden with the yaw stick.
- 中文说明：自动模式忽略横滚、俯仰和油门输入，但允许偏航覆盖。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = AUTO) -> ((RC_roll_t/RC_pitch_t/RC_throttle_t = RC_roll_t-1/RC_pitch_t-1/RC_throttle_t-1) & ((RC_yaw_t <= RC_yaw_t-1) | (RC_yaw_t >= RC_yaw_t-1))))`
- 绑定用解释：`G((Mode_t = AUTO) -> ((RC_roll_t/RC_pitch_t/RC_throttle_t = RC_roll_t-1/RC_pitch_t-1/RC_throttle_t-1) & ((RC_yaw_t <= RC_yaw_t-1) | (RC_yaw_t >= RC_yaw_t-1))))`
- PGFuzz 制品目录：`A.AUTO1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = AUTO` | 当前模式是自动任务模式。 | `Mode_t`, `AUTO` |
| AP02 | `consequent` | `RC_roll_t = RC_roll_t-1` | 横滚输入与上一观测严格相等。 | `RC_roll_t`, `RC_roll_t-1` |
| AP03 | `consequent` | `RC_pitch_t = RC_pitch_t-1` | 俯仰输入与上一观测严格相等。 | `RC_pitch_t`, `RC_pitch_t-1` |
| AP04 | `consequent` | `RC_throttle_t = RC_throttle_t-1` | 油门输入与上一观测严格相等。 | `RC_throttle_t`, `RC_throttle_t-1` |
| AP05 | `consequent` | `RC_yaw_t <= RC_yaw_t-1 or RC_yaw_t >= RC_yaw_t-1` | 偏航输入不大于或不小于上一值；对普通数值是恒真析取。 | `RC_yaw_t`, `RC_yaw_t-1` |

问题与限制：

- `CONTROL_EFFECT_CONFUSED_WITH_INPUT`：自然语言描述输入应被忽略，公式却限制输入本身不变化。
- `TAUTOLOGICAL_INPUT_CHANGE`：小于等于或大于等于上一值的析取对普通数值总成立，不能约束行为。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## A.BRAKE1

- 英文原文：When the vehicle is in BRAKE mode, it must stop within k seconds.
- 中文说明：制动模式中应在未知 k 时间内停止。
- 论文模板：`T1`
- 论文原式转录：`G((Mode_t = BRAKE) -> F_[0,k](Pos_t = Pos_t-1))`
- 绑定用解释：`G((Mode_t = BRAKE) -> F_[0,k](Pos_t = Pos_t-1))`
- PGFuzz 制品目录：`A.BRAKE1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = BRAKE` | 当前模式是制动模式。 | `Mode_t`, `BRAKE` |
| AP02 | `consequent` | `F_[0,k](Pos_t = Pos_t-1)` | 在未知 k 时间内当前位置与上一观测位置相同。 | `Pos_t`, `Pos_t-1`, `k` |

问题与限制：

- `EMPIRICAL_K_NOT_NORMATIVE`：k 来自论文仿真经验或未公开测量，不是当前官方时间要求。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## A.DRIFT1

- 英文原文：If the vehicle loses GPS signals in flight while in DRIFT mode, the vehicle must either LAND or enter ALT_HOLD mode based on FS_EKF_ACTION parameter.
- 中文说明：漂移模式中 GPS 丢失后按 FS_EKF_ACTION 进入着陆或定高模式。
- 论文模板：`T1`
- 论文原式转录：`G(((GPS_fail = on) & (Mode_t = DRIFT)) -> F_[0,k](Mode_t = FS_EKF_ACTION))`
- 绑定用解释：`G(((GPS_fail = on) & (Mode_t = DRIFT)) -> F_[0,k](Mode_t = FS_EKF_ACTION))`
- PGFuzz 制品目录：`A.DRIFT1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | `GPS_fail` |
| AP02 | `antecedent` | `Mode_t = DRIFT` | 当前模式是漂移模式。 | `Mode_t`, `DRIFT` |
| AP03 | `consequent` | `F_[0,k](Mode_t = FS_EKF_ACTION)` | 在未知 k 时间内模式变成参数 FS_EKF_ACTION 指定的动作。 | `Mode_t`, `FS_EKF_ACTION`, `k` |

问题与限制：

- `EMPIRICAL_K_NOT_NORMATIVE`：k 来自论文仿真经验或未公开测量，不是当前官方时间要求。
- `SYMBOLIC_PARAMETER_AS_STATE`：把参数值直接当作飞行模式后件，缺少枚举和状态转换定义。

## A.LOITER1

- 英文原文：The vehicle must maintain a constant location, heading, and altitude.
- 中文说明：定点盘旋模式保持位置、航向和高度。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = LOITER) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))`
- 绑定用解释：`G((Mode_t = LOITER) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))`
- PGFuzz 制品目录：`A.LOITER1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = LOITER` | 当前模式是定点盘旋模式。 | `Mode_t`, `LOITER` |
| AP02 | `consequent` | `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | `Pos_t`, `Pos_t-1` |
| AP03 | `consequent` | `Yaw_t = Yaw_t-1` | 当前偏航与上一观测严格相等。 | `Yaw_t`, `Yaw_t-1` |
| AP04 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## A.GUIDED1

- 英文原文：If there is no more way point, the vehicle must stay at the same location, heading, and altitude.
- 中文说明：引导模式没有剩余航点时保持位置、航向和高度。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = GUIDED) & (Waypoint = empty)) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))`
- 绑定用解释：`G(((Mode_t = GUIDED) & (Waypoint = empty)) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))`
- PGFuzz 制品目录：`A.GUIDED1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = GUIDED` | 当前模式是外部引导模式。 | `Mode_t`, `GUIDED` |
| AP02 | `antecedent` | `Waypoint = empty` | 论文抽象的航点集合为空。 | `Waypoint` |
| AP03 | `consequent` | `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | `Pos_t`, `Pos_t-1` |
| AP04 | `consequent` | `Yaw_t = Yaw_t-1` | 当前偏航与上一观测严格相等。 | `Yaw_t`, `Yaw_t-1` |
| AP05 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `EMPTY_WAYPOINT_UNDEFINED`：Waypoint=空 的任务范围、队列和完成事件没有定义。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## A.SPORT1

- 英文原文：In SPORT mode, the vehicle must climb as indicated by the PILOT_SPEED_UP parameter.
- 中文说明：运动模式按 PILOT_SPEED_UP 参数爬升。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = SPORT) -> (Speed_vertical_t = PILOT_SPEED_UP))`
- 绑定用解释：`G((Mode_t = SPORT) -> (Speed_vertical_t = PILOT_SPEED_UP))`
- PGFuzz 制品目录：`A.SPORT1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = SPORT` | 当前模式是运动模式。 | `Mode_t`, `SPORT` |
| AP02 | `consequent` | `Speed_vertical_t = PILOT_SPEED_UP` | 垂直速度严格等于飞手上升速度参数。 | `Speed_vertical_t`, `PILOT_SPEED_UP` |

问题与限制：

- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## A.RC.FS1

- 英文原文：If and only if the vehicle is armed in ACRO mode and the throttle input is less than the minimum (FS_THR_VALUE parameter), the vehicle must immediately disarm.
- 中文说明：已解锁的特技模式中油门低于阈值时立即锁定。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = ACRO) & (Throttle_t < FS_THR_VALUE)) -> (Disarm = on))`
- 绑定用解释：`G(((Mode_t = ACRO) & (Throttle_t < FS_THR_VALUE)) -> (Disarm = on))`
- PGFuzz 制品目录：`A.RC.FS1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ACRO` | 当前模式是特技模式。 | `Mode_t`, `ACRO` |
| AP02 | `antecedent` | `Throttle_t < FS_THR_VALUE` | 油门输入低于遥控故障保护阈值参数。 | `Throttle_t`, `FS_THR_VALUE` |
| AP03 | `antecedent_from_description` | `Armed = true` | 飞行器电机已经解锁。 | `Armed` |
| AP04 | `consequent` | `Disarm = on` | 电机处于锁定状态。 | `Disarm` |

问题与限制：

- `IFF_NOT_ENCODED`：自然语言使用‘当且仅当’，公式只编码单向蕴含。
- `IMMEDIACY_UNBOUNDED`：自然语言写‘立即’，公式没有可追溯的时间界限。
- `ANTECEDENT_MISSING_ARMED`：自然语言要求飞行器已解锁，论文公式前件遗漏该条件。

## A.RC.FS2

- 英文原文：If the throttle input is less than FS_THR_VALUE parameter, it must change the current mode to the RC fail-safe mode.
- 中文说明：油门低于 FS_THR_VALUE 时开启遥控故障保护。
- 论文模板：`T3`
- 论文原式转录：`G((Throttle_t < FS_THR_VALUE) -> (RC_fail = on))`
- 绑定用解释：`G((Throttle_t < FS_THR_VALUE) -> (RC_fail = on))`
- PGFuzz 制品目录：`A.RC.FS2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Throttle_t < FS_THR_VALUE` | 油门输入低于遥控故障保护阈值参数。 | `Throttle_t`, `FS_THR_VALUE` |
| AP02 | `consequent` | `RC_fail = on` | 遥控故障保护状态开启。 | `RC_fail` |

问题与限制：当前只记录一般的版本漂移和源码绑定门禁，没有发现表内直接冲突。

## A.CHUTE1

- 英文原文：Deploying a parachute requires following conditions: motors armed, mode not FLIP or ACRO, not climbing, and altitude above CHUTE_ALT_MIN.
- 中文说明：释放降落伞要求电机已解锁、模式允许、没有爬升且高于最低开伞高度。
- 论文模板：`T2`
- 论文原式转录：`G((Parachute = on) -> ((Armed = true) & (Mode_t notin FLIP/ACRO) & (ALT_t <= ALT_t-1) & (ALT_t > CHUTE_ALT_MIN)))`
- 绑定用解释：`G((Parachute = on) -> ((Armed = true) & (Mode_t notin FLIP/ACRO) & (ALT_t <= ALT_t-1) & (ALT_t > CHUTE_ALT_MIN)))`
- PGFuzz 制品目录：`A.CHUTE`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Parachute = on` | 降落伞已经释放。 | `Parachute` |
| AP02 | `consequent` | `Armed = true` | 飞行器电机已经解锁。 | `Armed` |
| AP03 | `consequent` | `Mode_t notin {FLIP,ACRO}` | 当前模式既不是翻滚也不是特技模式。 | `Mode_t`, `FLIP`, `ACRO` |
| AP04 | `consequent` | `ALT_t <= ALT_t-1` | 当前高度不高于上一观测高度，即论文所称不在爬升。 | `ALT_t`, `ALT_t-1` |
| AP05 | `consequent` | `ALT_t > CHUTE_ALT_MIN` | 当前高度高于最低开伞高度参数。 | `ALT_t`, `CHUTE_ALT_MIN` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## A.GPS.FS1

- 英文原文：When the number of detected GPS satellites is less than four, the vehicle must trigger the GPS fail-safe mode.
- 中文说明：检测到的 GPS 卫星少于四颗时触发 GPS 故障保护。
- 论文模板：`T3`
- 论文原式转录：`G((GPS_fail = on) -> (GPS_count < 4))`
- 绑定用解释：`G((GPS_fail = on) -> (GPS_count < 4))`
- PGFuzz 制品目录：`A.GPS.FS1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | `GPS_fail` |
| AP02 | `consequent` | `GPS_count < 4` | 可见 GPS 卫星数量少于四。 | `GPS_count` |

问题与限制：

- `FAILSAFE_IMPLICATION_REVERSED`：自然语言是低卫星数触发故障保护，论文公式反向写成故障保护推出低卫星数。

## A.GPS.FS2

- 英文原文：When the GPS fail-safe mode is triggered and there is a secondary altitude sensor, the vehicle must change the current primary altitude source to the secondary sensor.
- 中文说明：GPS 故障保护触发且气压计可用时改用气压计高度来源。
- 论文模板：`T3`
- 论文原式转录：`G(((GPS_fail = on) & (Baro = on)) -> (ALT_src = Baro))`
- 绑定用解释：`G(((GPS_fail = on) & (Baro = on)) -> (ALT_src = Baro))`
- PGFuzz 制品目录：`A.GPS.FS2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | `GPS_fail` |
| AP02 | `antecedent` | `Baro = on` | 论文抽象的气压计可用状态开启。 | `Baro` |
| AP03 | `consequent` | `ALT_src = Baro` | 论文抽象的高度来源被标记为气压计。 | `ALT_src`, `Baro` |

问题与限制：

- `BARO_ON_UNDEFINED`：Baro=on 没有说明健康、启用、被选择或仅有数据中的哪一种。
- `SOURCE_ABSTRACTION_UNDEFINED`：高度来源、Baro/GPS 高度的坐标系和融合语义没有定义。
