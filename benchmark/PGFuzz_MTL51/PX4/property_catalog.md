# PX4 PGFuzz 历史性质目录

`MTL` 是度量时序逻辑；`AP` 是原子命题；`NOT_ASSESSED` 是未评估实现符合性。
`EXACT`、`MODELLED`、`UNRESOLVED` 分别表示精确绑定、建模绑定和未解决绑定；都不等于性质通过。

共 21 条性质、68 个 AP、1697 条作者依赖输入关联。

| 顺序 | 性质 | 中文说明 | 绑定/观测状态 | AP | 作者关联 | 公式参数 | 审核记录 |
|---:|---|---|---|---:|---:|---:|---|
| 31 | `PX.RTL1` | 当前高度低于 RTL_RETURN_ALT 时持续爬升，直到达到该高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 3 | 93 | 1 | [PX.RTL1.md](properties/PX.RTL1.md) / [PX.RTL1.json](properties/PX.RTL1.json) |
| 32 | `PX.RTL2` | 达到 PX4 返航高度且尚未到家时保持高度并移动到家。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 5 | 92 | 1 | [PX.RTL2.md](properties/PX.RTL2.md) / [PX.RTL2.json](properties/PX.RTL2.json) |
| 33 | `PX.RTL3` | 达到返航高度并到家后进入着陆模式。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 92 | 1 | [PX.RTL3.md](properties/PX.RTL3.md) / [PX.RTL3.json](properties/PX.RTL3.json) |
| 34 | `PX.RTL4` | RTL_LAND_DELAY 为负一时在 RTL_DESCEND_ALT 高度盘旋。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 5 | 92 | 2 | [PX.RTL4.md](properties/PX.RTL4.md) / [PX.RTL4.json](properties/PX.RTL4.json) |
| 35 | `PX.RTL5` | 与 A.RTL4 相同：着陆触地后锁定电机。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 3 | 92 | 0 | [PX.RTL5.md](properties/PX.RTL5.md) / [PX.RTL5.json](properties/PX.RTL5.json) |
| 36 | `PX.ORBIT1` | 继承 A.CIRCLE1，并把绕圈模式解释为 PX4 ORBIT。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 50 | 0 | [PX.ORBIT1.md](properties/PX.ORBIT1.md) / [PX.ORBIT1.json](properties/PX.ORBIT1.json) |
| 37 | `PX.ORBIT2` | 继承 A.CIRCLE2，并把绕圈模式解释为 PX4 ORBIT。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 3 | 50 | 0 | [PX.ORBIT2.md](properties/PX.ORBIT2.md) / [PX.ORBIT2.json](properties/PX.ORBIT2.json) |
| 38 | `PX.ORBIT3` | 继承 A.CIRCLE3，并把绕圈模式解释为 PX4 ORBIT。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 50 | 0 | [PX.ORBIT3.md](properties/PX.ORBIT3.md) / [PX.ORBIT3.json](properties/PX.ORBIT3.json) |
| 39 | `PX.ORBIT4` | 继承 A.CIRCLE4，并把绕圈模式解释为 PX4 ORBIT。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 4 | 50 | 0 | [PX.ORBIT4.md](properties/PX.ORBIT4.md) / [PX.ORBIT4.json](properties/PX.ORBIT4.json) |
| 40 | `PX.ORBIT5` | 绕点飞行最大半径为 100 米。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 2 | 50 | 0 | [PX.ORBIT5.md](properties/PX.ORBIT5.md) / [PX.ORBIT5.json](properties/PX.ORBIT5.json) |
| 41 | `PX.ORBIT6` | 绕点飞行最大加速度限制为每平方秒 2 米。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`INSTRUMENTATION_REQUIRED`（需要插桩；标准 MAVLink 没有等价字段） | 2 | 50 | 0 | [PX.ORBIT6.md](properties/PX.ORBIT6.md) / [PX.ORBIT6.json](properties/PX.ORBIT6.json) |
| 42 | `PX.LAND1` | 下降速度等于 MPC_LAND_SPEED 参数。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`DIRECT`（直接可观测；字段直接携带所需值，仍需解码和有效性检查） | 2 | 94 | 1 | [PX.LAND1.md](properties/PX.LAND1.md) / [PX.LAND1.json](properties/PX.LAND1.json) |
| 43 | `PX.ALTITUDE1` | 继承 A.ALT_HOLD2，并把模式解释为 PX4 ALTITUDE。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 3 | 93 | 0 | [PX.ALTITUDE1.md](properties/PX.ALTITUDE1.md) / [PX.ALTITUDE1.json](properties/PX.ALTITUDE1.json) |
| 44 | `PX.POSITION1` | 位置控制模式保持位置不变。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`DERIVED`（派生可观测；需要组合字段、保存历史或换算） | 2 | 93 | 0 | [PX.POSITION1.md](properties/PX.POSITION1.md) / [PX.POSITION1.json](properties/PX.POSITION1.json) |
| 45 | `PX.HOLD1` | 继承 A.LOITER1，并把模式解释为 PX4 HOLD。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 4 | 93 | 0 | [PX.HOLD1.md](properties/PX.HOLD1.md) / [PX.HOLD1.json](properties/PX.HOLD1.json) |
| 46 | `PX.HOLD2` | 最小盘旋高度启用且当前高度低于它时爬升到该高度。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 5 | 93 | 1 | [PX.HOLD2.md](properties/PX.HOLD2.md) / [PX.HOLD2.json](properties/PX.HOLD2.json) |
| 47 | `PX.TAKEOFF1` | 执行起飞命令时目标高度应等于 MIS_TAKEOFF_ALT。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 3 | 94 | 1 | [PX.TAKEOFF1.md](properties/PX.TAKEOFF1.md) / [PX.TAKEOFF1.json](properties/PX.TAKEOFF1.json) |
| 48 | `PX.TAKEOFF2` | 执行起飞命令时上升速度应等于 MPC_TKO_SPEED。 | `MODELLED`（建模绑定；需要单位、坐标、上下文或历史样本解释）<br>`CONDITIONAL`（有条件可观测；消息、实例、有效性或配置条件必须成立） | 2 | 94 | 1 | [PX.TAKEOFF2.md](properties/PX.TAKEOFF2.md) / [PX.TAKEOFF2.json](properties/PX.TAKEOFF2.json) |
| 49 | `PX.GPS.FS1` | 检测到 GPS 丢失后，在 COM_POS_FS_DELAY 加调度余量内触发故障保护。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 2 | 94 | 1 | [PX.GPS.FS1.md](properties/PX.GPS.FS1.md) / [PX.GPS.FS1.json](properties/PX.GPS.FS1.json) |
| 50 | `PX.GPS.FS2` | GPS 故障保护触发且遥控可用时进入高度模式。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 3 | 94 | 0 | [PX.GPS.FS2.md](properties/PX.GPS.FS2.md) / [PX.GPS.FS2.json](properties/PX.GPS.FS2.json) |
| 51 | `PX.GPS.FS3` | GPS 故障保护触发且遥控不可用时进入着陆模式。 | `UNRESOLVED`（未解决；证据不足，禁止猜测）<br>`UNRESOLVED`（未解决；证据不足，禁止猜测） | 3 | 94 | 0 | [PX.GPS.FS3.md](properties/PX.GPS.FS3.md) / [PX.GPS.FS3.json](properties/PX.GPS.FS3.json) |

所有 `implementation_satisfaction` 均为 `NOT_ASSESSED`，只表示尚未评估，不表示满足。
