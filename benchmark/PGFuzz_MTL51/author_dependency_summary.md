# PGFuzz 作者依赖输入清单

本清单把论文制品中的每一行配置参数、命令、环境输入和前置条件展开到 51 条逻辑性质。它保存作者关联，但不把关联升级为已证明的数据依赖。

## 术语与状态

- `InputP`：Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。
- `InputC`：Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。
- `InputE`：Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。
- `PRECONDITION`：前置条件；作者要求先设置该值，再执行目标测试输入。
- `CANDIDATE_ASSOCIATION`：作者 policy 文件中的高召回候选关联；没有逐项公开真实数据依赖证明。
- `EXPLICIT_PRECONDITION`：作者制品明确要求先设置的值；只对旧制品实验流程成立。
- `EXACT_CURRENT_DEFINITION`：当前冻结源码的参数定义目录中存在同名定义。
- `RENAMED_CURRENT_DEFINITION`：有当前源码位置支持的历史名到当前名映射；不是字符串猜测。
- `CURRENT_DEFINITION_NOT_FOUND`：当前冻结参数定义目录中没有找到同名或已审计重命名目标。
- `COMMAND_XML_DEFINITION_FOUND`：当前固定 MAVLink XML 中存在同名命令定义；不等于飞控一定处理该命令。
- `COMMAND_XML_DEFINITION_NOT_FOUND`：当前固定 MAVLink XML 中没有找到同名命令定义。
- `SPECIAL_CONTROL_INPUT`：PGFuzz 自定义的模式或遥控伪输入，不是配置参数或 MAV_CMD 枚举。
- `NOT_TESTED`：未测试；这里专指没有通过当前仿真执行参数写入并验证行为变化。
- `NOT_ASSESSED`：未评估；没有判断当前固件是否满足论文性质。

## 规模

- 展开后的性质—输入关联共 7569 行。
- ArduPilot 为 5872 行，PX4 为 1697 行。
- 去重后的系统—输入身份共 356 行。
- 同一个制品目录可能服务多条论文性质；清单保留共享目录和原始行号，因此不会把复制列表误当成独立分析结果。

## 参数第六列警告

PGFuzz 的 `read_inputs.py` 把第六列命名为 `param_units`，中文意为“参数单位”；但文件中大量值为 `0.1`、`1`、`10`，而 XML 解析说明又提到 increment（参数增量）。本数据集只保存 `artifact_column_6_raw` 原值，不把它擅自解释为物理单位。当前单位和增量分别取自当前冻结源码参数元数据。
作者参数原值中的 `TRUE` 是第二列的旧制品“需要重启”标记；`X` 是公开读取代码未进一步定义的占位符，不能解释为 0、假、任意范围或具体单位。覆盖表中的 `True/False` 只表示作者参数文件列出/未列出公式词项。

## 各系统与输入类别计数

| 系统 | 类别 | 关联行数 | 去重输入数 |
|---|---|---:|---:|
| ArduPilot | `InputP` | 1868 | 57 |
| ArduPilot | `InputC` | 1246 | 59 |
| ArduPilot | `InputE` | 2753 | 143 |
| ArduPilot | `PRECONDITION` | 5 | 5 |
| PX4 | `InputP` | 633 | 30 |
| PX4 | `InputC` | 833 | 51 |
| PX4 | `InputE` | 231 | 11 |
| PX4 | `PRECONDITION` | 0 | 0 |

## 公式直接参数是否出现在作者依赖文件

| 系统 | 性质 | 公式参数 | 作者参数文件包含 | 当前身份状态 | 当前名称 | 当前实际仿真值 |
|---|---|---|---|---|---|---|
| ArduPilot | `A.RTL1` | `RTL_ALT` | True | `RENAMED_CURRENT_DEFINITION` | `RTL_ALT_M` | `15.0` |
| ArduPilot | `A.RTL2` | `RTL_ALT` | True | `RENAMED_CURRENT_DEFINITION` | `RTL_ALT_M` | `15.0` |
| ArduPilot | `A.RTL3` | `RTL_ALT` | True | `RENAMED_CURRENT_DEFINITION` | `RTL_ALT_M` | `15.0` |
| ArduPilot | `A.LAND1` | `LAND_SPEED_HIGH` | True | `RENAMED_CURRENT_DEFINITION` | `LAND_SPD_HIGH_MS` | `0.0` |
| ArduPilot | `A.LAND2` | `LAND_SPEED` | True | `RENAMED_CURRENT_DEFINITION` | `LAND_SPD_MS` | `0.5` |
| ArduPilot | `A.DRIFT1` | `FS_EKF_ACTION` | True | `EXACT_CURRENT_DEFINITION` | `FS_EKF_ACTION` | `1` |
| ArduPilot | `A.SPORT1` | `PILOT_SPEED_UP` | True | `RENAMED_CURRENT_DEFINITION` | `PILOT_SPD_UP` | `2.5` |
| ArduPilot | `A.RC.FS1` | `FS_THR_VALUE` | True | `EXACT_CURRENT_DEFINITION` | `FS_THR_VALUE` | `975` |
| ArduPilot | `A.RC.FS2` | `FS_THR_VALUE` | True | `EXACT_CURRENT_DEFINITION` | `FS_THR_VALUE` | `975` |
| ArduPilot | `A.CHUTE1` | `CHUTE_ALT_MIN` | False | `EXACT_CURRENT_DEFINITION` | `CHUTE_ALT_MIN` | `未观测` |
| PX4 | `PX.RTL1` | `RTL_RETURN_ALT` | True | `EXACT_CURRENT_DEFINITION` | `RTL_RETURN_ALT` | `30.0` |
| PX4 | `PX.RTL2` | `RTL_RETURN_ALT` | True | `EXACT_CURRENT_DEFINITION` | `RTL_RETURN_ALT` | `30.0` |
| PX4 | `PX.RTL3` | `RTL_RETURN_ALT` | True | `EXACT_CURRENT_DEFINITION` | `RTL_RETURN_ALT` | `30.0` |
| PX4 | `PX.RTL4` | `RTL_DESCEND_ALT` | True | `EXACT_CURRENT_DEFINITION` | `RTL_DESCEND_ALT` | `10.0` |
| PX4 | `PX.RTL4` | `RTL_LAND_DELAY` | False | `EXACT_CURRENT_DEFINITION` | `RTL_LAND_DELAY` | `0.0` |
| PX4 | `PX.LAND1` | `MPC_LAND_SPEED` | False | `EXACT_CURRENT_DEFINITION` | `MPC_LAND_SPEED` | `0.699999988079071` |
| PX4 | `PX.HOLD2` | `MIS_LTRMIN_ALT` | True | `RENAMED_CURRENT_DEFINITION` | `NAV_MIN_LTR_ALT` | `-1.0` |
| PX4 | `PX.TAKEOFF1` | `MIS_TAKEOFF_ALT` | True | `EXACT_CURRENT_DEFINITION` | `MIS_TAKEOFF_ALT` | `2.5` |
| PX4 | `PX.TAKEOFF2` | `MPC_TKO_SPEED` | False | `EXACT_CURRENT_DEFINITION` | `MPC_TKO_SPEED` | `1.5` |
| PX4 | `PX.GPS.FS1` | `COM_POS_FS_DELAY` | True | `CURRENT_DEFINITION_NOT_FOUND` | `COM_POS_FS_DELAY` | `未观测` |

## 判断边界

- 参数定义存在，只回答“当前源码里叫什么、在哪里定义、默认/范围是什么”；不回答它是否影响某条性质。
- 当前仿真值只来自冻结参数快照；参数一般可经协议读取，是否可在飞行中修改、是否需重启以及修改后何时生效，必须逐参数依据元数据和运行测试判断。
- 命令存在于协议 XML，只证明协议定义存在；不证明当前构建处理该命令。
- `preconditions.txt` 为空，只说明公开制品没有写前置设置；不说明真实模式、传感器、坐标或数据新鲜度前置条件不存在。
