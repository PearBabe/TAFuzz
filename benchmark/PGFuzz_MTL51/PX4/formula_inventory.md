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
| 31 | PX4 | `PX.RTL1` | `T3` | 3 | `PX.RTL1` | 2 |
| 32 | PX4 | `PX.RTL2` | `T3` | 5 | `PX.RTL2` | 2 |
| 33 | PX4 | `PX.RTL3` | `T3` | 4 | `PX.RTL3` | 1 |
| 34 | PX4 | `PX.RTL4` | `T3` | 5 | `PX.RTL4` | 3 |
| 35 | PX4 | `PX.RTL5` | `T3` | 3 | `PX.RTL5` | 3 |
| 36 | PX4 | `PX.ORBIT1` | `T3` | 4 | `PX.ORBIT1` | 4 |
| 37 | PX4 | `PX.ORBIT2` | `T3` | 3 | `PX.ORBIT2` | 3 |
| 38 | PX4 | `PX.ORBIT3` | `T3` | 4 | `PX.ORBIT3` | 4 |
| 39 | PX4 | `PX.ORBIT4` | `T3` | 4 | `PX.ORBIT4_5` | 4 |
| 40 | PX4 | `PX.ORBIT5` | `T3` | 2 | `PX.ORBIT4_5` | 1 |
| 41 | PX4 | `PX.ORBIT6` | `T3` | 2 | `PX.ORBIT6` | 2 |
| 42 | PX4 | `PX.LAND1` | `T3` | 2 | `PX.LAND1` | 2 |
| 43 | PX4 | `PX.ALTITUDE1` | `T3` | 3 | `PX.ALTITUDE1` | 4 |
| 44 | PX4 | `PX.POSITION1` | `T3` | 2 | `PX.POSITION1` | 2 |
| 45 | PX4 | `PX.HOLD1` | `T3` | 4 | `PX.HOLD1` | 4 |
| 46 | PX4 | `PX.HOLD2` | `T3` | 5 | `PX.HOLD2` | 3 |
| 47 | PX4 | `PX.TAKEOFF1` | `T3` | 3 | `PX.TAKEOFF1` | 1 |
| 48 | PX4 | `PX.TAKEOFF2` | `T3` | 2 | `PX.TAKEOFF2` | 2 |
| 49 | PX4 | `PX.GPS.FS1` | `T1` | 2 | `PX.GPS.FS1` | 1 |
| 50 | PX4 | `PX.GPS.FS2` | `T3` | 3 | `PX.GPS.FS2` | 0 |
| 51 | PX4 | `PX.GPS.FS3` | `T3` | 3 | `PX.GPS.FS3` | 0 |

## PX.RTL1

- 英文原文：If the current altitude is less than RTL_RETURN_ALT, then altitude must be increased until the altitude is greater or equal to RTL_RETURN_ALT.
- 中文说明：当前高度低于 RTL_RETURN_ALT 时持续爬升，直到达到该高度。
- 论文模板：`T3`
- 论文原式转录：`G(((ALT_t < RTL_RETURN_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))`
- 绑定用解释：`G(((ALT_t < RTL_RETURN_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))`
- PGFuzz 制品目录：`PX.RTL1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `ALT_t < RTL_RETURN_ALT` | PX4 当前高度低于返航高度参数。 | `ALT_t`, `RTL_RETURN_ALT` |
| AP02 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP03 | `consequent` | `ALT_t-1 < ALT_t` | 当前观测高度高于上一观测高度。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `UNTIL_LOST`：自然语言包含‘直到达到目标’，论文公式只要求相邻观测朝目标变化。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## PX.RTL2

- 英文原文：If the current altitude is greater or equal to RTL_RETURN_ALT, current flight mode is RTL, and the current vehicle is not home position, then the vehicle must move to the home position while maintaining the current altitude.
- 中文说明：达到 PX4 返航高度且尚未到家时保持高度并移动到家。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))`
- 绑定用解释：`G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))`
- PGFuzz 制品目录：`PX.RTL2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP02 | `antecedent` | `ALT_t >= RTL_RETURN_ALT` | PX4 当前高度达到或超过返航高度参数。 | `ALT_t`, `RTL_RETURN_ALT` |
| AP03 | `antecedent` | `Pos_t != home_position` | 当前位置不等于返航参考位置。 | `Pos_t`, `home_position` |
| AP04 | `consequent` | `Pos_t-1 != Pos_t` | 当前位置与上一观测位置不同。 | `Pos_t-1`, `Pos_t` |
| AP05 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## PX.RTL3

- 英文原文：If current altitude is greater or equal to RTL_RETURN_ALT and current position is the same as home position, then flight mode must be LAND.
- 中文说明：达到返航高度并到家后进入着陆模式。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))`
- 绑定用解释：`G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))`
- PGFuzz 制品目录：`PX.RTL3`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP02 | `antecedent` | `ALT_t >= RTL_RETURN_ALT` | PX4 当前高度达到或超过返航高度参数。 | `ALT_t`, `RTL_RETURN_ALT` |
| AP03 | `antecedent` | `Pos_t = home_position` | 当前位置等于返航参考位置。 | `Pos_t`, `home_position` |
| AP04 | `consequent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |

问题与限制：

- `SAME_SAMPLE_MODE_CONTRADICTION`：同一采样点的前件和后件要求互斥飞行模式。

## PX.RTL4

- 英文原文：If RTL_LAND_DELAY parameter has -1, the vehicle must hover at RTL_DESCEND_ALT.
- 中文说明：RTL_LAND_DELAY 为负一时在 RTL_DESCEND_ALT 高度盘旋。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = RTL) & (RTL_DESCEND_ALT = -1)) -> ((Pos_t = Pos_t-1) & (ALT_t = ALT_t-1)))`
- 绑定用解释：`G(((Mode_t = RTL) & (RTL_LAND_DELAY = -1)) -> ((Pos_t = Pos_t-1) & (ALT_t = ALT_t-1)))`
- PGFuzz 制品目录：`PX.RTL4`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = RTL` | 当前飞行模式是返航模式。 | `Mode_t`, `RTL` |
| AP02 | `antecedent_as_printed` | `RTL_DESCEND_ALT = -1` | 论文公式错误地把返航下降高度参数与负一比较。 | `RTL_DESCEND_ALT` |
| AP03 | `antecedent_from_description` | `RTL_LAND_DELAY = -1` | PX4 返航着陆等待参数为负一，表示不着陆而保持盘旋。 | `RTL_LAND_DELAY` |
| AP04 | `consequent` | `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | `Pos_t`, `Pos_t-1` |
| AP05 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `WRONG_PARAMETER_IN_FORMULA`：自然语言与论文公式使用了不同参数。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## PX.RTL5

- 英文原文：It is the same as A.RTL4.
- 中文说明：与 A.RTL4 相同：着陆触地后锁定电机。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.RTL4.`
- 绑定用解释：`G(((Mode_t = LAND) & (ALT_t = GroundALT)) -> (Disarm = on))`
- PGFuzz 制品目录：`PX.RTL5`
- 继承来源：`A.RTL4`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |
| AP02 | `antecedent` | `ALT_t = GroundALT` | 当前高度严格等于论文所称地面高度。 | `ALT_t`, `GroundALT` |
| AP03 | `consequent` | `Disarm = on` | 电机处于锁定状态。 | `Disarm` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `IMMEDIACY_UNBOUNDED`：自然语言写‘立即’，公式没有可追溯的时间界限。
- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。

## PX.ORBIT1

- 英文原文：It is the same as A.CIRCLE1.
- 中文说明：继承 A.CIRCLE1，并把绕圈模式解释为 PX4 ORBIT。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.CIRCLE1.`
- 绑定用解释：`G(((Mode_t = ORBIT) & (RC_pitch < 1500) & (Circle_radius_t > 0)) -> (Circle_radius_t < Circle_radius_t-1))`
- PGFuzz 制品目录：`PX.ORBIT1`
- 继承来源：`A.CIRCLE1`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | `Mode_t`, `ORBIT` |
| AP02 | `antecedent` | `RC_pitch < 1500` | 俯仰遥控输入小于通道中值。 | `RC_pitch` |
| AP03 | `antecedent` | `Circle_radius_t > 0` | 当前绕圈半径为正数。 | `Circle_radius_t` |
| AP04 | `consequent` | `Circle_radius_t < Circle_radius_t-1` | 绕圈半径比上一观测减小。 | `Circle_radius_t`, `Circle_radius_t-1` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `MODE_SUBSTITUTION_REQUIRED`：继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。
- `UNTIL_LOST`：自然语言包含‘直到达到目标’，论文公式只要求相邻观测朝目标变化。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## PX.ORBIT2

- 英文原文：It is the same as A.CIRCLE2.
- 中文说明：继承 A.CIRCLE2，并把绕圈模式解释为 PX4 ORBIT。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.CIRCLE2.`
- 绑定用解释：`G(((Mode_t = ORBIT) & (RC_pitch > 1500)) -> (Circle_radius_t > Circle_radius_t-1))`
- PGFuzz 制品目录：`PX.ORBIT2`
- 继承来源：`A.CIRCLE2`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | `Mode_t`, `ORBIT` |
| AP02 | `antecedent` | `RC_pitch > 1500` | 俯仰遥控输入大于通道中值。 | `RC_pitch` |
| AP03 | `consequent` | `Circle_radius_t > Circle_radius_t-1` | 绕圈半径比上一观测增大。 | `Circle_radius_t`, `Circle_radius_t-1` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `MODE_SUBSTITUTION_REQUIRED`：继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## PX.ORBIT3

- 英文原文：It is the same as A.CIRCLE3.
- 中文说明：继承 A.CIRCLE3，并把绕圈模式解释为 PX4 ORBIT。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.CIRCLE3.`
- 绑定用解释：`G(((Mode_t = ORBIT) & (RC_roll > 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t > Circle_speed_t-1))`
- PGFuzz 制品目录：`PX.ORBIT3`
- 继承来源：`A.CIRCLE3`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | `Mode_t`, `ORBIT` |
| AP02 | `antecedent` | `RC_roll > 1500` | 横滚遥控输入大于通道中值。 | `RC_roll` |
| AP03 | `antecedent` | `Circle_direction_t = clockwise` | 绕圈方向是顺时针。 | `Circle_direction_t` |
| AP04 | `consequent` | `Circle_speed_t > Circle_speed_t-1` | 绕圈速度比上一观测增大。 | `Circle_speed_t`, `Circle_speed_t-1` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `MODE_SUBSTITUTION_REQUIRED`：继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## PX.ORBIT4

- 英文原文：It is the same as A.CIRCLE4.
- 中文说明：继承 A.CIRCLE4，并把绕圈模式解释为 PX4 ORBIT。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.CIRCLE4.`
- 绑定用解释：`G(((Mode_t = ORBIT) & (RC_roll > 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t < Circle_speed_t-1))`
- PGFuzz 制品目录：`PX.ORBIT4_5`
- 继承来源：`A.CIRCLE4`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | `Mode_t`, `ORBIT` |
| AP02 | `antecedent` | `RC_roll > 1500` | 横滚遥控输入大于通道中值。 | `RC_roll` |
| AP03 | `antecedent` | `Circle_direction_t = counterclockwise` | 绕圈方向是逆时针。 | `Circle_direction_t` |
| AP04 | `consequent` | `Circle_speed_t < Circle_speed_t-1` | 绕圈速度比上一观测减小。 | `Circle_speed_t`, `Circle_speed_t-1` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `MODE_SUBSTITUTION_REQUIRED`：继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## PX.ORBIT5

- 英文原文：The maximum radius must be 100 meters.
- 中文说明：绕点飞行最大半径为 100 米。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = ORBIT) -> (Circle_radius_t < 100))`
- 绑定用解释：`G((Mode_t = ORBIT) -> (Circle_radius_t < 100))`
- PGFuzz 制品目录：`PX.ORBIT4_5`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | `Mode_t`, `ORBIT` |
| AP02 | `consequent` | `Circle_radius_t < 100m` | 论文抽象的绕点半径严格小于 100 米。 | `Circle_radius_t` |

问题与限制：

- `STRICT_MAX_BOUND`：自然语言的最大值通常允许等于边界，公式却使用严格小于。

## PX.ORBIT6

- 英文原文：The maximum acceleration must be limited to 2m/s^2.
- 中文说明：绕点飞行最大加速度限制为每平方秒 2 米。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = ORBIT) -> (Circle_speed_t < 2m/s^2))`
- 绑定用解释：`G((Mode_t = ORBIT) -> (Circle_speed_t < 2m/s^2))`
- PGFuzz 制品目录：`PX.ORBIT6`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ORBIT` | 当前 PX4 模式是绕点飞行模式。 | `Mode_t`, `ORBIT` |
| AP02 | `consequent` | `Circle_speed_t < 2m/s^2` | 论文用速度变量与加速度单位阈值比较。 | `Circle_speed_t` |

问题与限制：

- `TYPE_UNIT_MISMATCH`：公式比较的变量类型与自然语言物理量或单位不一致。
- `STRICT_MAX_BOUND`：自然语言的最大值通常允许等于边界，公式却使用严格小于。

## PX.LAND1

- 英文原文：Descending speed must be the same as MPC_LAND_SPEED parameter.
- 中文说明：下降速度等于 MPC_LAND_SPEED 参数。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = LAND) -> (Speed_vertical_t = MPC_LAND_SPEED))`
- 绑定用解释：`G((Mode_t = LAND) -> (Speed_vertical_t = MPC_LAND_SPEED))`
- PGFuzz 制品目录：`PX.LAND1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |
| AP02 | `consequent` | `Speed_vertical_t = MPC_LAND_SPEED` | 垂直速度严格等于 PX4 着陆速度参数。 | `Speed_vertical_t`, `MPC_LAND_SPEED` |

问题与限制：

- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## PX.ALTITUDE1

- 英文原文：It is the same as A.ALT_HOLD2.
- 中文说明：继承 A.ALT_HOLD2，并把模式解释为 PX4 ALTITUDE。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.ALT_HOLD2.`
- 绑定用解释：`G(((Mode_t = ALTITUDE) & (Throttle_t = 1500)) -> (ALT_t = ALT_t-1))`
- PGFuzz 制品目录：`PX.ALTITUDE1`
- 继承来源：`A.ALT_HOLD2`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = ALTITUDE` | 当前 PX4 模式是高度控制模式。 | `Mode_t`, `ALTITUDE` |
| AP02 | `antecedent` | `Throttle_t = 1500` | 油门输入严格等于通道中值 1500。 | `Throttle_t` |
| AP03 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `MODE_SUBSTITUTION_REQUIRED`：继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## PX.POSITION1

- 英文原文：The vehicle must maintain a constant position.
- 中文说明：位置控制模式保持位置不变。
- 论文模板：`T3`
- 论文原式转录：`G((Mode_t = POSITION) -> (Pos_t = Pos_t-1))`
- 绑定用解释：`G((Mode_t = POSITION) -> (Pos_t = Pos_t-1))`
- PGFuzz 制品目录：`PX.POSITION1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = POSITION` | 当前 PX4 模式是位置控制模式。 | `Mode_t`, `POSITION` |
| AP02 | `consequent` | `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | `Pos_t`, `Pos_t-1` |

问题与限制：

- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## PX.HOLD1

- 英文原文：It is the same as A.LOITER1.
- 中文说明：继承 A.LOITER1，并把模式解释为 PX4 HOLD。
- 论文模板：`T3`
- 论文原式转录：`It is the same as A.LOITER1.`
- 绑定用解释：`G((Mode_t = HOLD) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))`
- PGFuzz 制品目录：`PX.HOLD1`
- 继承来源：`A.LOITER1`；论文没有打印完整替换式。

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = HOLD` | 当前 PX4 模式是保持模式。 | `Mode_t`, `HOLD` |
| AP02 | `consequent` | `Pos_t = Pos_t-1` | 当前位置与上一观测位置严格相等。 | `Pos_t`, `Pos_t-1` |
| AP03 | `consequent` | `Yaw_t = Yaw_t-1` | 当前偏航与上一观测严格相等。 | `Yaw_t`, `Yaw_t-1` |
| AP04 | `consequent` | `ALT_t-1 = ALT_t` | 当前高度与上一观测高度严格相等。 | `ALT_t-1`, `ALT_t` |

问题与限制：

- `INHERITANCE_NOT_PRINTED`：论文只写‘同某条性质’，没有打印替换后的系统专用公式。
- `MODE_SUBSTITUTION_REQUIRED`：继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。
- `STRICT_SAMPLE_EQUALITY`：用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。

## PX.HOLD2

- 英文原文：If MIS_LTRMIN_ALT is not -1 and current altitude is less than the parameter value, then the vehicle must ascend to this altitude.
- 中文说明：最小盘旋高度启用且当前高度低于它时爬升到该高度。
- 论文模板：`T3`
- 论文原式转录：`G(((Mode_t = HOLD) & (MIS_LTRMIN_ALT != -1)) -> (ALT_t > ALT_t-1))`
- 绑定用解释：`G(((Mode_t = HOLD) & (MIS_LTRMIN_ALT != -1)) -> (ALT_t > ALT_t-1))`
- PGFuzz 制品目录：`PX.HOLD2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Mode_t = HOLD` | 当前 PX4 模式是保持模式。 | `Mode_t`, `HOLD` |
| AP02 | `antecedent` | `MIS_LTRMIN_ALT != -1` | 最小盘旋高度参数没有使用禁用值负一。 | `MIS_LTRMIN_ALT` |
| AP03 | `antecedent_from_description` | `ALT_t < MIS_LTRMIN_ALT` | 当前高度低于最小盘旋高度参数；该前件来自论文自然语言但被印刷公式遗漏。 | `ALT_t`, `MIS_LTRMIN_ALT` |
| AP04 | `consequent` | `ALT_t-1 < ALT_t` | 当前观测高度高于上一观测高度。 | `ALT_t-1`, `ALT_t` |
| AP05 | `target_from_description` | `Target_ALT = MIS_LTRMIN_ALT` | 目标高度等于最小盘旋高度参数；该目标来自论文自然语言，印刷公式只保留了上升趋势。 | `Target_ALT`, `MIS_LTRMIN_ALT` |

问题与限制：

- `ANTECEDENT_MISSING_ALTITUDE_BOUND`：自然语言包含当前高度低于目标参数，公式前件遗漏该条件。
- `UNTIL_LOST`：自然语言包含‘直到达到目标’，论文公式只要求相邻观测朝目标变化。
- `PREVIOUS_SAMPLE_NOT_TIME`：t-1 仅是上一观测索引，论文没有给出固定采样周期。

## PX.TAKEOFF1

- 英文原文：When the vehicle conducts a taking off command, the target altitude must be the MIS_TAKEOFF_ALT parameter value.
- 中文说明：执行起飞命令时目标高度应等于 MIS_TAKEOFF_ALT。
- 论文模板：`T3`
- 论文原式转录：`G((Command_t = takeoff) -> (ALT_t <= MIS_TAKEOFF_ALT))`
- 绑定用解释：`G((Command_t = takeoff) -> (ALT_t <= MIS_TAKEOFF_ALT))`
- PGFuzz 制品目录：`PX.TAKEOFF1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Command_t = takeoff` | 当前处理的是起飞命令。 | `Command_t`, `takeoff` |
| AP02 | `consequent_as_printed` | `ALT_t <= MIS_TAKEOFF_ALT` | 当前高度不超过任务起飞高度参数。 | `ALT_t`, `MIS_TAKEOFF_ALT` |
| AP03 | `target_from_description` | `Target_ALT = MIS_TAKEOFF_ALT` | 起飞目标高度等于任务起飞高度参数；该等式来自论文自然语言。 | `Target_ALT`, `MIS_TAKEOFF_ALT` |

问题与限制：

- `TARGET_EQUALITY_WEAKENED`：自然语言要求目标等于参数，公式只要求不超过参数。

## PX.TAKEOFF2

- 英文原文：When the vehicle conducts a taking off command, the speed of ascent must be the MPC_TKO_SPEED parameter value.
- 中文说明：执行起飞命令时上升速度应等于 MPC_TKO_SPEED。
- 论文模板：`T3`
- 论文原式转录：`G((Command_t = takeoff) -> (Speed_vertical_t = MPC_TKO_SPEED))`
- 绑定用解释：`G((Command_t = takeoff) -> (Speed_vertical_t = MPC_TKO_SPEED))`
- PGFuzz 制品目录：`PX.TAKEOFF2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `Command_t = takeoff` | 当前处理的是起飞命令。 | `Command_t`, `takeoff` |
| AP02 | `consequent` | `Speed_vertical_t = MPC_TKO_SPEED` | 垂直速度严格等于 PX4 起飞速度参数。 | `Speed_vertical_t`, `MPC_TKO_SPEED` |

问题与限制：

- `EXACT_PHYSICAL_EQUALITY`：要求物理状态精确等于常量或参数，未给容差和采样语义。
- `DIRECTION_OR_SIGN_UNDEFINED`：速度或方向的正负号、坐标系和实际测量量没有定义。

## PX.GPS.FS1

- 英文原文：If time exceeds COM_POS_FS_DELAY seconds after GPS loss is detected, the GPS fail-safe must be triggered.
- 中文说明：检测到 GPS 丢失后，在 COM_POS_FS_DELAY 加调度余量内触发故障保护。
- 论文模板：`T1`
- 论文原式转录：`G((GPS_loss = on) -> F_[0,COM_POS_FS_DELAY+k](GPS_fail = on))`
- 绑定用解释：`G((GPS_loss = on) -> F_[0,COM_POS_FS_DELAY+k](GPS_fail = on))`
- PGFuzz 制品目录：`PX.GPS.FS1`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `GPS_loss = on` | 论文抽象的 GPS 丢失事件已经发生。 | `GPS_loss` |
| AP02 | `consequent` | `F_[0,COM_POS_FS_DELAY+k](GPS_fail = on)` | 在位置故障延迟参数加调度余量内触发 GPS 故障保护。 | `GPS_fail`, `COM_POS_FS_DELAY`, `k` |

问题与限制：

- `SCHEDULE_MARGIN_UNPUBLISHED`：调度余量 k 的操作数和具体数值没有公开。

## PX.GPS.FS2

- 英文原文：If the GPS fail-safe is triggered and a remote controller is available, the flight mode must be changed to ALTITUDE mode.
- 中文说明：GPS 故障保护触发且遥控可用时进入高度模式。
- 论文模板：`T3`
- 论文原式转录：`G(((GPS_fail = on) & (RC_t = on)) -> (Mode_t = ALTITUDE))`
- 绑定用解释：`G(((GPS_fail = on) & (RC_t = on)) -> (Mode_t = ALTITUDE))`
- PGFuzz 制品目录：`PX.GPS.FS2`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | `GPS_fail` |
| AP02 | `antecedent` | `RC_t = on` | 遥控器输入被论文抽象为可用。 | `RC_t` |
| AP03 | `consequent` | `Mode_t = ALTITUDE` | 当前 PX4 模式是高度控制模式。 | `Mode_t`, `ALTITUDE` |

问题与限制：当前只记录一般的版本漂移和源码绑定门禁，没有发现表内直接冲突。

## PX.GPS.FS3

- 英文原文：If the GPS fail-safe is triggered and a remote controller is not available, the flight mode must be changed to LAND mode.
- 中文说明：GPS 故障保护触发且遥控不可用时进入着陆模式。
- 论文模板：`T3`
- 论文原式转录：`G(((GPS_fail = on) & (RC_t = off)) -> (Mode_t = LAND))`
- 绑定用解释：`G(((GPS_fail = on) & (RC_t = off)) -> (Mode_t = LAND))`
- PGFuzz 制品目录：`PX.GPS.FS3`

| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |
|---|---|---|---|---|
| AP01 | `antecedent` | `GPS_fail = on` | 论文抽象的 GPS 故障保护状态开启。 | `GPS_fail` |
| AP02 | `antecedent` | `RC_t = off` | 遥控器输入被论文抽象为不可用。 | `RC_t` |
| AP03 | `consequent` | `Mode_t = LAND` | 当前飞行模式是着陆模式。 | `Mode_t`, `LAND` |

问题与限制：当前只记录一般的版本漂移和源码绑定门禁，没有发现表内直接冲突。
