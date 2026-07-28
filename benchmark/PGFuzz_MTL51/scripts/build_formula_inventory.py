#!/usr/bin/env python3
"""Deterministically build the PGFuzz Table-XII formula/AP inventory."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ISSUE_DEFS = {
    "UNTIL_LOST": "自然语言包含‘直到达到目标’，论文公式只要求相邻观测朝目标变化。",
    "PREVIOUS_SAMPLE_NOT_TIME": "t-1 仅是上一观测索引，论文没有给出固定采样周期。",
    "STRICT_SAMPLE_EQUALITY": "用相邻样本严格相等表示保持状态，未定义坐标系、噪声和容差。",
    "SAME_SAMPLE_MODE_CONTRADICTION": "同一采样点的前件和后件要求互斥飞行模式。",
    "IMMEDIACY_UNBOUNDED": "自然语言写‘立即’，公式没有可追溯的时间界限。",
    "IFF_NOT_ENCODED": "自然语言使用‘当且仅当’，公式只编码单向蕴含。",
    "PRECEDENCE_AMBIGUOUS": "合取、析取和蕴含的括号不足，逻辑优先级不唯一。",
    "EXACT_PHYSICAL_EQUALITY": "要求物理状态精确等于常量或参数，未给容差和采样语义。",
    "MALFORMED_EVENTUAL_EQUALITY": "论文把等式与 eventually 运算符错误连接，不能按标准 MTL 直接解析。",
    "PHASE_SENTINEL_UNGROUNDED": "FLIP1/FLIP3 是论文阶段标签，不是已证明存在的飞行模式状态。",
    "RETURN_ORIGINAL_MODE_OMITTED": "自然语言要求恢复原飞行模式，公式只检查阶段标签变化。",
    "SOURCE_ABSTRACTION_UNDEFINED": "高度来源、Baro/GPS 高度的坐标系和融合语义没有定义。",
    "CONTROL_EFFECT_CONFUSED_WITH_INPUT": "自然语言描述输入应被忽略，公式却限制输入本身不变化。",
    "FORMULA_SYNTAX_EXTRA_CONJUNCTION": "论文公式在蕴含前出现多余合取符号。",
    "EMPIRICAL_K_NOT_NORMATIVE": "k 来自论文仿真经验或未公开测量，不是当前官方时间要求。",
    "SYMBOLIC_PARAMETER_AS_STATE": "把参数值直接当作飞行模式后件，缺少枚举和状态转换定义。",
    "EMPTY_WAYPOINT_UNDEFINED": "Waypoint=空 的任务范围、队列和完成事件没有定义。",
    "FAILSAFE_IMPLICATION_REVERSED": "自然语言是低卫星数触发故障保护，论文公式反向写成故障保护推出低卫星数。",
    "BARO_ON_UNDEFINED": "Baro=on 没有说明健康、启用、被选择或仅有数据中的哪一种。",
    "WRONG_PARAMETER_IN_FORMULA": "自然语言与论文公式使用了不同参数。",
    "INHERITANCE_NOT_PRINTED": "论文只写‘同某条性质’，没有打印替换后的系统专用公式。",
    "STRICT_MAX_BOUND": "自然语言的最大值通常允许等于边界，公式却使用严格小于。",
    "TYPE_UNIT_MISMATCH": "公式比较的变量类型与自然语言物理量或单位不一致。",
    "ANTECEDENT_MISSING_ALTITUDE_BOUND": "自然语言包含当前高度低于目标参数，公式前件遗漏该条件。",
    "TARGET_EQUALITY_WEAKENED": "自然语言要求目标等于参数，公式只要求不超过参数。",
    "SCHEDULE_MARGIN_UNPUBLISHED": "调度余量 k 的操作数和具体数值没有公开。",
    "MODE_SUBSTITUTION_REQUIRED": "继承 ArduPilot 性质时需要替换为 PX4 模式名，但论文未打印替换规则。",
    "DIRECTION_OR_SIGN_UNDEFINED": "速度或方向的正负号、坐标系和实际测量量没有定义。",
    "TAUTOLOGICAL_INPUT_CHANGE": "小于等于或大于等于上一值的析取对普通数值总成立，不能约束行为。",
    "RANGE_CONDITION_OMITTED": "自然语言包含范围或适用条件，公式未完整保留。",
    "DESCRIPTION_FORMULA_POLARITY_CONFLICT": "自然语言给出允许进入的正向条件，论文公式却混入其反向条件；不能把两者当作同一逻辑表达。",
    "ANTECEDENT_MISSING_ARMED": "自然语言要求飞行器已解锁，论文公式前件遗漏该条件。",
}

ROLE_DEFS = {
    "antecedent": "论文印刷公式的蕴含前件，即触发或前置条件。",
    "consequent": "论文印刷公式的蕴含后件，即作者要求出现或保持的结果。",
    "negated_consequent": "论文印刷公式后件中带否定的条件；不代表自然语言一定采用相同极性。",
    "consequent_disjunct": "论文印刷公式后件中的析取分支；其作用范围可能受括号歧义影响。",
    "antecedent_as_printed": "只来自论文印刷公式的前件，已知可能与自然语言冲突。",
    "consequent_as_printed": "只来自论文印刷公式的后件，已知可能弱化或误写自然语言要求。",
    "antecedent_from_description": "来自同一行英文自然语言、但被印刷公式遗漏的前件；不用于静默改写原式。",
    "condition_from_description": "来自同一行英文自然语言的条件，用于显示自然语言与公式的差异。",
    "target_from_description": "来自同一行英文自然语言的目标状态；印刷公式没有完整表达它。",
}


def ap(expression: str, role: str) -> dict[str, str]:
    return {"expression": expression, "role": role}


AP_DEFS: dict[str, dict[str, object]] = {
    "ALT_t < RTL_ALT": {"meaning_zh": "当前高度低于 ArduPilot 返航高度参数。", "terms": ["ALT_t", "RTL_ALT"]},
    "Mode_t = RTL": {"meaning_zh": "当前飞行模式是返航模式。", "terms": ["Mode_t", "RTL"]},
    "ALT_t-1 < ALT_t": {"meaning_zh": "当前观测高度高于上一观测高度。", "terms": ["ALT_t-1", "ALT_t"]},
    "ALT_t >= RTL_ALT": {"meaning_zh": "当前高度达到或超过 ArduPilot 返航高度参数。", "terms": ["ALT_t", "RTL_ALT"]},
    "Pos_t != home_position": {"meaning_zh": "当前位置不等于返航参考位置。", "terms": ["Pos_t", "home_position"]},
    "Pos_t-1 != Pos_t": {"meaning_zh": "当前位置与上一观测位置不同。", "terms": ["Pos_t-1", "Pos_t"]},
    "ALT_t-1 = ALT_t": {"meaning_zh": "当前高度与上一观测高度严格相等。", "terms": ["ALT_t-1", "ALT_t"]},
    "Pos_t = home_position": {"meaning_zh": "当前位置等于返航参考位置。", "terms": ["Pos_t", "home_position"]},
    "Mode_t = LAND": {"meaning_zh": "当前飞行模式是着陆模式。", "terms": ["Mode_t", "LAND"]},
    "ALT_t = GroundALT": {"meaning_zh": "当前高度严格等于论文所称地面高度。", "terms": ["ALT_t", "GroundALT"]},
    "Disarm = on": {"meaning_zh": "电机处于锁定状态。", "terms": ["Disarm"]},
    "Mode_t = FLIP": {"meaning_zh": "当前飞行模式是翻滚模式。", "terms": ["Mode_t", "FLIP"]},
    "Mode_t-1 in {ACRO,ALT_HOLD}": {"meaning_zh": "上一观测模式是特技或定高模式。", "terms": ["Mode_t-1", "ACRO", "ALT_HOLD"]},
    "Roll_t > 45deg": {"meaning_zh": "当前横滚角大于 45 度。", "terms": ["Roll_t"]},
    "Roll_t < 45deg": {"meaning_zh": "当前横滚角小于 45 度；该条件来自论文自然语言，不是印刷公式中的同向原子。", "terms": ["Roll_t"]},
    "Throttle_t <= 1500": {"meaning_zh": "当前油门通道值不超过 1500。", "terms": ["Throttle_t"]},
    "Throttle_t >= 1500": {"meaning_zh": "当前油门通道值达到或超过 1500；该条件来自论文自然语言。", "terms": ["Throttle_t"]},
    "ALT_t < 10m": {"meaning_zh": "当前高度低于 10 米。", "terms": ["ALT_t"]},
    "ALT_t > 10m": {"meaning_zh": "当前高度高于 10 米；该条件来自论文自然语言。", "terms": ["ALT_t"]},
    "-90deg <= Roll_t <= 45deg": {"meaning_zh": "当前横滚角位于负 90 度到 45 度之间。", "terms": ["Roll_t"]},
    "Roll_rate = 400deg/s": {"meaning_zh": "横滚角速度严格等于每秒 400 度。", "terms": ["Roll_rate"]},
    "Roll_direction = right": {"meaning_zh": "横滚方向为右。", "terms": ["Roll_direction"]},
    "Mode_t = FLIP3": {"meaning_zh": "论文内部的 FLIP3 恢复阶段标签成立。", "terms": ["Mode_t", "FLIP3"]},
    "F_[0,k](Roll_t = Roll_original)": {"meaning_zh": "在未知 k 时间内横滚恢复到原值。", "terms": ["Roll_t", "Roll_original", "k"]},
    "F_[0,k](Pitch_t = Pitch_original)": {"meaning_zh": "在未知 k 时间内俯仰恢复到原值。", "terms": ["Pitch_t", "Pitch_original", "k"]},
    "F_[0,k](Yaw_t = Yaw_original)": {"meaning_zh": "在未知 k 时间内偏航恢复到原值。", "terms": ["Yaw_t", "Yaw_original", "k"]},
    "Mode_t = FLIP1": {"meaning_zh": "论文内部的 FLIP1 开始阶段标签成立。", "terms": ["Mode_t", "FLIP1"]},
    "F_[0,2.5s](Mode_t = FLIP3)": {"meaning_zh": "2.5 秒内到达论文的 FLIP3 阶段。", "terms": ["Mode_t", "FLIP3"]},
    "ALT_src = Baro": {"meaning_zh": "论文抽象的高度来源被标记为气压计。", "terms": ["ALT_src", "Baro"]},
    "ALT_t = ALT_Baro": {"meaning_zh": "当前高度严格等于气压计高度。", "terms": ["ALT_t", "ALT_Baro"]},
    "ALT_t != ALT_GPS": {"meaning_zh": "当前高度不等于 GPS 高度。", "terms": ["ALT_t", "ALT_GPS"]},
    "Mode_t = ALT_HOLD": {"meaning_zh": "当前模式是 ArduPilot 定高模式。", "terms": ["Mode_t", "ALT_HOLD"]},
    "Throttle_t = 1500": {"meaning_zh": "油门输入严格等于通道中值 1500。", "terms": ["Throttle_t"]},
    "Mode_t = CIRCLE": {"meaning_zh": "当前模式是 ArduPilot 绕圈模式。", "terms": ["Mode_t", "CIRCLE"]},
    "RC_pitch < 1500": {"meaning_zh": "俯仰遥控输入小于通道中值。", "terms": ["RC_pitch"]},
    "RC_pitch > 1500": {"meaning_zh": "俯仰遥控输入大于通道中值。", "terms": ["RC_pitch"]},
    "Circle_radius_t > 0": {"meaning_zh": "当前绕圈半径为正数。", "terms": ["Circle_radius_t"]},
    "Circle_radius_t < Circle_radius_t-1": {"meaning_zh": "绕圈半径比上一观测减小。", "terms": ["Circle_radius_t", "Circle_radius_t-1"]},
    "Circle_radius_t > Circle_radius_t-1": {"meaning_zh": "绕圈半径比上一观测增大。", "terms": ["Circle_radius_t", "Circle_radius_t-1"]},
    "RC_roll > 1500": {"meaning_zh": "横滚遥控输入大于通道中值。", "terms": ["RC_roll"]},
    "RC_roll < 1500": {"meaning_zh": "横滚遥控输入小于通道中值。", "terms": ["RC_roll"]},
    "Circle_direction_t = clockwise": {"meaning_zh": "绕圈方向是顺时针。", "terms": ["Circle_direction_t"]},
    "Circle_direction_t = counterclockwise": {"meaning_zh": "绕圈方向是逆时针。", "terms": ["Circle_direction_t"]},
    "Circle_speed_t > Circle_speed_t-1": {"meaning_zh": "绕圈速度比上一观测增大。", "terms": ["Circle_speed_t", "Circle_speed_t-1"]},
    "Circle_speed_t < Circle_speed_t-1": {"meaning_zh": "绕圈速度比上一观测减小。", "terms": ["Circle_speed_t", "Circle_speed_t-1"]},
    "RC_roll_t = RC_roll_t-1": {"meaning_zh": "横滚输入与上一观测严格相等。", "terms": ["RC_roll_t", "RC_roll_t-1"]},
    "RC_pitch_t = RC_pitch_t-1": {"meaning_zh": "俯仰输入与上一观测严格相等。", "terms": ["RC_pitch_t", "RC_pitch_t-1"]},
    "RC_yaw_t = RC_yaw_t-1": {"meaning_zh": "偏航输入与上一观测严格相等。", "terms": ["RC_yaw_t", "RC_yaw_t-1"]},
    "RC_throttle_t <= RC_throttle_t-1 or RC_throttle_t >= RC_throttle_t-1": {"meaning_zh": "油门输入不大于或不小于上一值；对普通数值是恒真析取。", "terms": ["RC_throttle_t", "RC_throttle_t-1"]},
    "ALT_t >= 10m": {"meaning_zh": "当前高度达到或超过 10 米。", "terms": ["ALT_t"]},
    "Speed_vertical_t = LAND_SPEED_HIGH": {"meaning_zh": "垂直速度严格等于高空着陆速度参数。", "terms": ["Speed_vertical_t", "LAND_SPEED_HIGH"]},
    "Speed_vertical_t = LAND_SPEED": {"meaning_zh": "垂直速度严格等于低空着陆速度参数。", "terms": ["Speed_vertical_t", "LAND_SPEED"]},
    "Mode_t = AUTO": {"meaning_zh": "当前模式是自动任务模式。", "terms": ["Mode_t", "AUTO"]},
    "RC_throttle_t = RC_throttle_t-1": {"meaning_zh": "油门输入与上一观测严格相等。", "terms": ["RC_throttle_t", "RC_throttle_t-1"]},
    "RC_yaw_t <= RC_yaw_t-1 or RC_yaw_t >= RC_yaw_t-1": {"meaning_zh": "偏航输入不大于或不小于上一值；对普通数值是恒真析取。", "terms": ["RC_yaw_t", "RC_yaw_t-1"]},
    "Mode_t = BRAKE": {"meaning_zh": "当前模式是制动模式。", "terms": ["Mode_t", "BRAKE"]},
    "F_[0,k](Pos_t = Pos_t-1)": {"meaning_zh": "在未知 k 时间内当前位置与上一观测位置相同。", "terms": ["Pos_t", "Pos_t-1", "k"]},
    "GPS_fail = on": {"meaning_zh": "论文抽象的 GPS 故障保护状态开启。", "terms": ["GPS_fail"]},
    "Mode_t = DRIFT": {"meaning_zh": "当前模式是漂移模式。", "terms": ["Mode_t", "DRIFT"]},
    "F_[0,k](Mode_t = FS_EKF_ACTION)": {"meaning_zh": "在未知 k 时间内模式变成参数 FS_EKF_ACTION 指定的动作。", "terms": ["Mode_t", "FS_EKF_ACTION", "k"]},
    "Mode_t = LOITER": {"meaning_zh": "当前模式是定点盘旋模式。", "terms": ["Mode_t", "LOITER"]},
    "Pos_t = Pos_t-1": {"meaning_zh": "当前位置与上一观测位置严格相等。", "terms": ["Pos_t", "Pos_t-1"]},
    "Yaw_t = Yaw_t-1": {"meaning_zh": "当前偏航与上一观测严格相等。", "terms": ["Yaw_t", "Yaw_t-1"]},
    "Mode_t = GUIDED": {"meaning_zh": "当前模式是外部引导模式。", "terms": ["Mode_t", "GUIDED"]},
    "Waypoint = empty": {"meaning_zh": "论文抽象的航点集合为空。", "terms": ["Waypoint"]},
    "Mode_t = SPORT": {"meaning_zh": "当前模式是运动模式。", "terms": ["Mode_t", "SPORT"]},
    "Speed_vertical_t = PILOT_SPEED_UP": {"meaning_zh": "垂直速度严格等于飞手上升速度参数。", "terms": ["Speed_vertical_t", "PILOT_SPEED_UP"]},
    "Mode_t = ACRO": {"meaning_zh": "当前模式是特技模式。", "terms": ["Mode_t", "ACRO"]},
    "Throttle_t < FS_THR_VALUE": {"meaning_zh": "油门输入低于遥控故障保护阈值参数。", "terms": ["Throttle_t", "FS_THR_VALUE"]},
    "RC_fail = on": {"meaning_zh": "遥控故障保护状态开启。", "terms": ["RC_fail"]},
    "Parachute = on": {"meaning_zh": "降落伞已经释放。", "terms": ["Parachute"]},
    "Armed = true": {"meaning_zh": "飞行器电机已经解锁。", "terms": ["Armed"]},
    "Mode_t notin {FLIP,ACRO}": {"meaning_zh": "当前模式既不是翻滚也不是特技模式。", "terms": ["Mode_t", "FLIP", "ACRO"]},
    "ALT_t <= ALT_t-1": {"meaning_zh": "当前高度不高于上一观测高度，即论文所称不在爬升。", "terms": ["ALT_t", "ALT_t-1"]},
    "ALT_t > CHUTE_ALT_MIN": {"meaning_zh": "当前高度高于最低开伞高度参数。", "terms": ["ALT_t", "CHUTE_ALT_MIN"]},
    "GPS_count < 4": {"meaning_zh": "可见 GPS 卫星数量少于四。", "terms": ["GPS_count"]},
    "Baro = on": {"meaning_zh": "论文抽象的气压计可用状态开启。", "terms": ["Baro"]},
    "ALT_t < RTL_RETURN_ALT": {"meaning_zh": "PX4 当前高度低于返航高度参数。", "terms": ["ALT_t", "RTL_RETURN_ALT"]},
    "ALT_t >= RTL_RETURN_ALT": {"meaning_zh": "PX4 当前高度达到或超过返航高度参数。", "terms": ["ALT_t", "RTL_RETURN_ALT"]},
    "RTL_DESCEND_ALT = -1": {"meaning_zh": "论文公式错误地把返航下降高度参数与负一比较。", "terms": ["RTL_DESCEND_ALT"]},
    "RTL_LAND_DELAY = -1": {"meaning_zh": "PX4 返航着陆等待参数为负一，表示不着陆而保持盘旋。", "terms": ["RTL_LAND_DELAY"]},
    "Mode_t = ORBIT": {"meaning_zh": "当前 PX4 模式是绕点飞行模式。", "terms": ["Mode_t", "ORBIT"]},
    "Circle_radius_t < 100m": {"meaning_zh": "论文抽象的绕点半径严格小于 100 米。", "terms": ["Circle_radius_t"]},
    "Circle_speed_t < 2m/s^2": {"meaning_zh": "论文用速度变量与加速度单位阈值比较。", "terms": ["Circle_speed_t"]},
    "Speed_vertical_t = MPC_LAND_SPEED": {"meaning_zh": "垂直速度严格等于 PX4 着陆速度参数。", "terms": ["Speed_vertical_t", "MPC_LAND_SPEED"]},
    "Mode_t = ALTITUDE": {"meaning_zh": "当前 PX4 模式是高度控制模式。", "terms": ["Mode_t", "ALTITUDE"]},
    "Mode_t = POSITION": {"meaning_zh": "当前 PX4 模式是位置控制模式。", "terms": ["Mode_t", "POSITION"]},
    "Mode_t = HOLD": {"meaning_zh": "当前 PX4 模式是保持模式。", "terms": ["Mode_t", "HOLD"]},
    "MIS_LTRMIN_ALT != -1": {"meaning_zh": "最小盘旋高度参数没有使用禁用值负一。", "terms": ["MIS_LTRMIN_ALT"]},
    "ALT_t < MIS_LTRMIN_ALT": {"meaning_zh": "当前高度低于最小盘旋高度参数；该前件来自论文自然语言但被印刷公式遗漏。", "terms": ["ALT_t", "MIS_LTRMIN_ALT"]},
    "Target_ALT = MIS_LTRMIN_ALT": {"meaning_zh": "目标高度等于最小盘旋高度参数；该目标来自论文自然语言，印刷公式只保留了上升趋势。", "terms": ["Target_ALT", "MIS_LTRMIN_ALT"]},
    "Command_t = takeoff": {"meaning_zh": "当前处理的是起飞命令。", "terms": ["Command_t", "takeoff"]},
    "ALT_t <= MIS_TAKEOFF_ALT": {"meaning_zh": "当前高度不超过任务起飞高度参数。", "terms": ["ALT_t", "MIS_TAKEOFF_ALT"]},
    "Target_ALT = MIS_TAKEOFF_ALT": {"meaning_zh": "起飞目标高度等于任务起飞高度参数；该等式来自论文自然语言。", "terms": ["Target_ALT", "MIS_TAKEOFF_ALT"]},
    "Speed_vertical_t = MPC_TKO_SPEED": {"meaning_zh": "垂直速度严格等于 PX4 起飞速度参数。", "terms": ["Speed_vertical_t", "MPC_TKO_SPEED"]},
    "GPS_loss = on": {"meaning_zh": "论文抽象的 GPS 丢失事件已经发生。", "terms": ["GPS_loss"]},
    "F_[0,COM_POS_FS_DELAY+k](GPS_fail = on)": {"meaning_zh": "在位置故障延迟参数加调度余量内触发 GPS 故障保护。", "terms": ["GPS_fail", "COM_POS_FS_DELAY", "k"]},
    "RC_t = on": {"meaning_zh": "遥控器输入被论文抽象为可用。", "terms": ["RC_t"]},
    "RC_t = off": {"meaning_zh": "遥控器输入被论文抽象为不可用。", "terms": ["RC_t"]},
}


def policy(
    order: int,
    system: str,
    policy_id: str,
    artifact_dir: str,
    template: str,
    description_en: str,
    description_zh: str,
    printed_formula: str,
    propositions: list[dict[str, str]],
    issues: list[str],
    *,
    inherits_from: str | None = None,
    binding_formula: str | None = None,
) -> dict[str, object]:
    return {
        "paper_order": order,
        "system": system,
        "policy_id": policy_id,
        "artifact_policy_directory": artifact_dir,
        "template": template,
        "description_en": description_en,
        "description_zh": description_zh,
        "paper_formula_transcription": printed_formula,
        "binding_formula_interpretation": binding_formula or printed_formula,
        "inherits_from": inherits_from,
        "atomic_propositions": propositions,
        "issues": issues,
        "dataset_role": "HISTORICAL_PROPERTY_SEED",
        "implementation_satisfaction": "NOT_ASSESSED",
    }


P = []

# ArduPilot: 30 policies.
P += [
    policy(1, "ArduPilot", "A.RTL1", "A.RTL1", "T3", "If the current altitude is less than RTL_ALT, then altitude must be increased until the altitude is greater or equal to RTL_ALT.", "当前高度低于 RTL_ALT 时持续爬升，直到达到该高度。", "G(((ALT_t < RTL_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))", [ap("ALT_t < RTL_ALT", "antecedent"), ap("Mode_t = RTL", "antecedent"), ap("ALT_t-1 < ALT_t", "consequent")], ["UNTIL_LOST", "PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(2, "ArduPilot", "A.RTL2", "A.RTL2", "T3", "If the current altitude is greater or equal to RTL_ALT, current flight mode is RTL, and the current vehicle is not at home position, then the vehicle must move to the home position while maintaining the current altitude.", "达到返航高度且尚未到家时，保持高度并移动到返航参考位置。", "G(((Mode_t = RTL) & (ALT_t >= RTL_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))", [ap("Mode_t = RTL", "antecedent"), ap("ALT_t >= RTL_ALT", "antecedent"), ap("Pos_t != home_position", "antecedent"), ap("Pos_t-1 != Pos_t", "consequent"), ap("ALT_t-1 = ALT_t", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(3, "ArduPilot", "A.RTL3", "A.RTL3", "T3", "If current altitude is greater or equal to RTL_ALT and current position is the same as home position, then flight mode must be LAND.", "达到返航高度并到达返航参考位置后进入着陆模式。", "G(((Mode_t = RTL) & (ALT_t >= RTL_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))", [ap("Mode_t = RTL", "antecedent"), ap("ALT_t >= RTL_ALT", "antecedent"), ap("Pos_t = home_position", "antecedent"), ap("Mode_t = LAND", "consequent")], ["SAME_SAMPLE_MODE_CONTRADICTION"]),
    policy(4, "ArduPilot", "A.RTL4", "A.RTL4", "T3", "If current flight mode is LAND and the vehicle touches the ground, then the vehicle must disarm motors.", "着陆模式触地后锁定电机。", "G(((Mode_t = LAND) & (ALT_t = GroundALT)) -> (Disarm = on))", [ap("Mode_t = LAND", "antecedent"), ap("ALT_t = GroundALT", "antecedent"), ap("Disarm = on", "consequent")], ["IMMEDIACY_UNBOUNDED", "EXACT_PHYSICAL_EQUALITY"]),
    policy(5, "ArduPilot", "A.FLIP1", "A.FLIP1", "T2", "If and only if roll is less than 45 degree, throttle is greater or equal to 1,500, altitude is more than 10 meters, and the current flight mode is one of ACRO and ALT_HOLD, then the flight mode can be changed to FLIP.", "满足横滚、油门、高度和前一模式条件时才允许进入翻滚模式。", "G((Mode_t = FLIP) -> ((Mode_t-1 = ACRO/ALT_HOLD) & !(Roll_t > 45) | (Throttle_t <= 1500) | (ALT_t < 10)))", [ap("Mode_t = FLIP", "antecedent"), ap("Mode_t-1 in {ACRO,ALT_HOLD}", "consequent"), ap("Roll_t > 45deg", "negated_consequent"), ap("Throttle_t <= 1500", "consequent_disjunct"), ap("ALT_t < 10m", "consequent_disjunct"), ap("Roll_t < 45deg", "condition_from_description"), ap("Throttle_t >= 1500", "condition_from_description"), ap("ALT_t > 10m", "condition_from_description")], ["IFF_NOT_ENCODED", "PRECEDENCE_AMBIGUOUS", "PREVIOUS_SAMPLE_NOT_TIME", "DESCRIPTION_FORMULA_POLARITY_CONFLICT"]),
    policy(6, "ArduPilot", "A.FLIP2", "A.FLIP2", "T3", "If the current flight mode is FLIP and roll is between -90 and 45 degree, then rolling right at 400 degree per second.", "翻滚模式特定横滚角区间内向右以每秒 400 度滚转。", "G(((Mode_t = FLIP) & (-90 <= Roll_t <= 45)) -> ((Roll_rate = 400) & (Roll_direction = right)))", [ap("Mode_t = FLIP", "antecedent"), ap("-90deg <= Roll_t <= 45deg", "antecedent"), ap("Roll_rate = 400deg/s", "consequent"), ap("Roll_direction = right", "consequent")], ["EXACT_PHYSICAL_EQUALITY"]),
    policy(7, "ArduPilot", "A.FLIP3", "A.FLIP3", "T1&T3", "After the vehicle finishes A.FLIP2, the vehicle must recover the original attitude (i.e., roll, pitch, and yaw) within k seconds.", "完成翻滚阶段后在未知 k 时间内恢复原始姿态。", "G((Mode_t = FLIP3) -> ((Roll_t = F_[0,k] Roll_original) & (Pitch_t = F_[0,k] Pitch_original) & (Yaw_t = F_[0,k] Yaw_original)))", [ap("Mode_t = FLIP3", "antecedent"), ap("F_[0,k](Roll_t = Roll_original)", "consequent"), ap("F_[0,k](Pitch_t = Pitch_original)", "consequent"), ap("F_[0,k](Yaw_t = Yaw_original)", "consequent")], ["MALFORMED_EVENTUAL_EQUALITY", "PHASE_SENTINEL_UNGROUNDED", "EMPIRICAL_K_NOT_NORMATIVE"]),
    policy(8, "ArduPilot", "A.FLIPGeneral", "A.FLIP4", "T1", "The vehicle should complete the rolling (A.FLIP2) within 2.5 seconds and must return to the original flight mode.", "应在 2.5 秒内完成翻滚并恢复原飞行模式。", "G((Mode_t = FLIP1) -> F_[0,2.5](Mode_t = FLIP3))", [ap("Mode_t = FLIP1", "antecedent"), ap("F_[0,2.5s](Mode_t = FLIP3)", "consequent")], ["PHASE_SENTINEL_UNGROUNDED", "RETURN_ORIGINAL_MODE_OMITTED"]),
    policy(9, "ArduPilot", "A.ALT_HOLD1", "A.ALT_HOLD1", "T3", "If the altitude source is the barometer, the vehicle must follow the altitude computed by this source, rather than the GPS.", "高度来源为气压计时采用气压计高度而非 GPS 高度。", "G((ALT_src = Baro) -> ((ALT_t = ALT_Baro) & (ALT_t != ALT_GPS)))", [ap("ALT_src = Baro", "antecedent"), ap("ALT_t = ALT_Baro", "consequent"), ap("ALT_t != ALT_GPS", "consequent")], ["SOURCE_ABSTRACTION_UNDEFINED", "EXACT_PHYSICAL_EQUALITY"]),
    policy(10, "ArduPilot", "A.ALT_HOLD2", "A.ALT_HOLD2", "T3", "If the throttle stick is in the middle (i.e., 1,500) the vehicle must maintain the current altitude.", "定高模式中油门位于中值时保持高度。", "G(((Mode_t = ALT_HOLD) & (Throttle_t = 1500)) -> (ALT_t = ALT_t-1))", [ap("Mode_t = ALT_HOLD", "antecedent"), ap("Throttle_t = 1500", "antecedent"), ap("ALT_t-1 = ALT_t", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(11, "ArduPilot", "A.CIRCLE1", "A.CIRCLE1", "T3", "Pitch stick up must reduce the radius until it reaches zero.", "绕圈模式中俯仰杆向上使半径持续减小到零。", "G(((Mode_t = CIRCLE) & (RC_pitch < 1500) & (Circle_radius_t > 0)) -> (Circle_radius_t < Circle_radius_t-1))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_pitch < 1500", "antecedent"), ap("Circle_radius_t > 0", "antecedent"), ap("Circle_radius_t < Circle_radius_t-1", "consequent")], ["UNTIL_LOST", "PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(12, "ArduPilot", "A.CIRCLE2", "A.CIRCLE2", "T3", "Pitch stick down must increase the radius.", "绕圈模式中俯仰杆向下使半径增加。", "G(((Mode_t = CIRCLE) & (RC_pitch > 1500)) -> (Circle_radius_t > Circle_radius_t-1))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_pitch > 1500", "antecedent"), ap("Circle_radius_t > Circle_radius_t-1", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(13, "ArduPilot", "A.CIRCLE3", "A.CIRCLE3", "T3", "Roll stick right (think clockwise) must increase the speed while moving clockwise.", "顺时针绕圈时横滚杆向右使速度增加。", "G(((Mode_t = CIRCLE) & (RC_roll > 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t > Circle_speed_t-1))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_roll > 1500", "antecedent"), ap("Circle_direction_t = clockwise", "antecedent"), ap("Circle_speed_t > Circle_speed_t-1", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(14, "ArduPilot", "A.CIRCLE4", "A.CIRCLE4_6", "T3", "Roll stick right (think clockwise) must decrease the speed while moving counterclockwise.", "逆时针绕圈时横滚杆向右使速度减小。", "G(((Mode_t = CIRCLE) & (RC_roll > 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t < Circle_speed_t-1))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_roll > 1500", "antecedent"), ap("Circle_direction_t = counterclockwise", "antecedent"), ap("Circle_speed_t < Circle_speed_t-1", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(15, "ArduPilot", "A.CIRCLE5", "A.CIRCLE4_6", "T3", "Roll stick left (think counterclockwise) must increase the speed while moving counterclockwise.", "逆时针绕圈时横滚杆向左使速度增加。", "G(((Mode_t = CIRCLE) & (RC_roll < 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t > Circle_speed_t-1))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_roll < 1500", "antecedent"), ap("Circle_direction_t = counterclockwise", "antecedent"), ap("Circle_speed_t > Circle_speed_t-1", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(16, "ArduPilot", "A.CIRCLE6", "A.CIRCLE4_6", "T3", "Roll stick left (think counterclockwise) must decrease the speed while moving clockwise.", "顺时针绕圈时横滚杆向左使速度减小。", "G(((Mode_t = CIRCLE) & (RC_roll < 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t < Circle_speed_t-1))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_roll < 1500", "antecedent"), ap("Circle_direction_t = clockwise", "antecedent"), ap("Circle_speed_t < Circle_speed_t-1", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(17, "ArduPilot", "A.CIRCLE7", "A.CIRCLE7", "T3", "The users do not have any control over the roll, pitch, and yaw but can change the altitude with the throttle stick.", "绕圈模式忽略横滚、俯仰、偏航控制，但允许油门改变高度。", "G((Mode_t = CIRCLE) -> ((RC_roll_t/RC_pitch_t/RC_yaw_t = RC_roll_t-1/RC_pitch_t-1/RC_yaw_t-1) & ((RC_throttle_t <= RC_throttle_t-1) | (RC_throttle_t >= RC_throttle_t-1))))", [ap("Mode_t = CIRCLE", "antecedent"), ap("RC_roll_t = RC_roll_t-1", "consequent"), ap("RC_pitch_t = RC_pitch_t-1", "consequent"), ap("RC_yaw_t = RC_yaw_t-1", "consequent"), ap("RC_throttle_t <= RC_throttle_t-1 or RC_throttle_t >= RC_throttle_t-1", "consequent")], ["CONTROL_EFFECT_CONFUSED_WITH_INPUT", "TAUTOLOGICAL_INPUT_CHANGE", "PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(18, "ArduPilot", "A.LAND1", "A.LAND1", "T3", "Above 10 meters the vehicle must descend at the rate specified in the LAND_SPEED_HIGH parameter.", "着陆模式高于 10 米时按 LAND_SPEED_HIGH 参数下降。", "G(((Mode_t = LAND) & (ALT_t >= 10) &) -> (Speed_vertical_t = LAND_SPEED_HIGH))", [ap("Mode_t = LAND", "antecedent"), ap("ALT_t >= 10m", "antecedent"), ap("Speed_vertical_t = LAND_SPEED_HIGH", "consequent")], ["FORMULA_SYNTAX_EXTRA_CONJUNCTION", "EXACT_PHYSICAL_EQUALITY", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(19, "ArduPilot", "A.LAND2", "A.LAND2", "T3", "Below 10 meters the vehicle must descend at the rate specified in the LAND_SPEED parameter.", "着陆模式低于 10 米时按 LAND_SPEED 参数下降。", "G(((Mode_t = LAND) & (ALT_t < 10) &) -> (Speed_vertical_t = LAND_SPEED))", [ap("Mode_t = LAND", "antecedent"), ap("ALT_t < 10m", "antecedent"), ap("Speed_vertical_t = LAND_SPEED", "consequent")], ["FORMULA_SYNTAX_EXTRA_CONJUNCTION", "EXACT_PHYSICAL_EQUALITY", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(20, "ArduPilot", "A.AUTO1", "A.AUTO1", "T3", "The pilot's roll, pitch and throttle inputs must be ignored but the yaw can be overridden with the yaw stick.", "自动模式忽略横滚、俯仰和油门输入，但允许偏航覆盖。", "G((Mode_t = AUTO) -> ((RC_roll_t/RC_pitch_t/RC_throttle_t = RC_roll_t-1/RC_pitch_t-1/RC_throttle_t-1) & ((RC_yaw_t <= RC_yaw_t-1) | (RC_yaw_t >= RC_yaw_t-1))))", [ap("Mode_t = AUTO", "antecedent"), ap("RC_roll_t = RC_roll_t-1", "consequent"), ap("RC_pitch_t = RC_pitch_t-1", "consequent"), ap("RC_throttle_t = RC_throttle_t-1", "consequent"), ap("RC_yaw_t <= RC_yaw_t-1 or RC_yaw_t >= RC_yaw_t-1", "consequent")], ["CONTROL_EFFECT_CONFUSED_WITH_INPUT", "TAUTOLOGICAL_INPUT_CHANGE", "PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(21, "ArduPilot", "A.BRAKE1", "A.BRAKE1", "T1", "When the vehicle is in BRAKE mode, it must stop within k seconds.", "制动模式中应在未知 k 时间内停止。", "G((Mode_t = BRAKE) -> F_[0,k](Pos_t = Pos_t-1))", [ap("Mode_t = BRAKE", "antecedent"), ap("F_[0,k](Pos_t = Pos_t-1)", "consequent")], ["EMPIRICAL_K_NOT_NORMATIVE", "PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(22, "ArduPilot", "A.DRIFT1", "A.DRIFT1", "T1", "If the vehicle loses GPS signals in flight while in DRIFT mode, the vehicle must either LAND or enter ALT_HOLD mode based on FS_EKF_ACTION parameter.", "漂移模式中 GPS 丢失后按 FS_EKF_ACTION 进入着陆或定高模式。", "G(((GPS_fail = on) & (Mode_t = DRIFT)) -> F_[0,k](Mode_t = FS_EKF_ACTION))", [ap("GPS_fail = on", "antecedent"), ap("Mode_t = DRIFT", "antecedent"), ap("F_[0,k](Mode_t = FS_EKF_ACTION)", "consequent")], ["EMPIRICAL_K_NOT_NORMATIVE", "SYMBOLIC_PARAMETER_AS_STATE"]),
    policy(23, "ArduPilot", "A.LOITER1", "A.LOITER1", "T3", "The vehicle must maintain a constant location, heading, and altitude.", "定点盘旋模式保持位置、航向和高度。", "G((Mode_t = LOITER) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))", [ap("Mode_t = LOITER", "antecedent"), ap("Pos_t = Pos_t-1", "consequent"), ap("Yaw_t = Yaw_t-1", "consequent"), ap("ALT_t-1 = ALT_t", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(24, "ArduPilot", "A.GUIDED1", "A.GUIDED1", "T3", "If there is no more way point, the vehicle must stay at the same location, heading, and altitude.", "引导模式没有剩余航点时保持位置、航向和高度。", "G(((Mode_t = GUIDED) & (Waypoint = empty)) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))", [ap("Mode_t = GUIDED", "antecedent"), ap("Waypoint = empty", "antecedent"), ap("Pos_t = Pos_t-1", "consequent"), ap("Yaw_t = Yaw_t-1", "consequent"), ap("ALT_t-1 = ALT_t", "consequent")], ["EMPTY_WAYPOINT_UNDEFINED", "PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(25, "ArduPilot", "A.SPORT1", "A.SPORT1", "T3", "In SPORT mode, the vehicle must climb as indicated by the PILOT_SPEED_UP parameter.", "运动模式按 PILOT_SPEED_UP 参数爬升。", "G((Mode_t = SPORT) -> (Speed_vertical_t = PILOT_SPEED_UP))", [ap("Mode_t = SPORT", "antecedent"), ap("Speed_vertical_t = PILOT_SPEED_UP", "consequent")], ["EXACT_PHYSICAL_EQUALITY", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(26, "ArduPilot", "A.RC.FS1", "A.RC.FS1", "T3", "If and only if the vehicle is armed in ACRO mode and the throttle input is less than the minimum (FS_THR_VALUE parameter), the vehicle must immediately disarm.", "已解锁的特技模式中油门低于阈值时立即锁定。", "G(((Mode_t = ACRO) & (Throttle_t < FS_THR_VALUE)) -> (Disarm = on))", [ap("Mode_t = ACRO", "antecedent"), ap("Throttle_t < FS_THR_VALUE", "antecedent"), ap("Armed = true", "antecedent_from_description"), ap("Disarm = on", "consequent")], ["IFF_NOT_ENCODED", "IMMEDIACY_UNBOUNDED", "ANTECEDENT_MISSING_ARMED"]),
    policy(27, "ArduPilot", "A.RC.FS2", "A.RC.FS2", "T3", "If the throttle input is less than FS_THR_VALUE parameter, it must change the current mode to the RC fail-safe mode.", "油门低于 FS_THR_VALUE 时开启遥控故障保护。", "G((Throttle_t < FS_THR_VALUE) -> (RC_fail = on))", [ap("Throttle_t < FS_THR_VALUE", "antecedent"), ap("RC_fail = on", "consequent")], []),
    policy(28, "ArduPilot", "A.CHUTE1", "A.CHUTE", "T2", "Deploying a parachute requires following conditions: motors armed, mode not FLIP or ACRO, not climbing, and altitude above CHUTE_ALT_MIN.", "释放降落伞要求电机已解锁、模式允许、没有爬升且高于最低开伞高度。", "G((Parachute = on) -> ((Armed = true) & (Mode_t notin FLIP/ACRO) & (ALT_t <= ALT_t-1) & (ALT_t > CHUTE_ALT_MIN)))", [ap("Parachute = on", "antecedent"), ap("Armed = true", "consequent"), ap("Mode_t notin {FLIP,ACRO}", "consequent"), ap("ALT_t <= ALT_t-1", "consequent"), ap("ALT_t > CHUTE_ALT_MIN", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(29, "ArduPilot", "A.GPS.FS1", "A.GPS.FS1", "T3", "When the number of detected GPS satellites is less than four, the vehicle must trigger the GPS fail-safe mode.", "检测到的 GPS 卫星少于四颗时触发 GPS 故障保护。", "G((GPS_fail = on) -> (GPS_count < 4))", [ap("GPS_fail = on", "antecedent"), ap("GPS_count < 4", "consequent")], ["FAILSAFE_IMPLICATION_REVERSED"]),
    policy(30, "ArduPilot", "A.GPS.FS2", "A.GPS.FS2", "T3", "When the GPS fail-safe mode is triggered and there is a secondary altitude sensor, the vehicle must change the current primary altitude source to the secondary sensor.", "GPS 故障保护触发且气压计可用时改用气压计高度来源。", "G(((GPS_fail = on) & (Baro = on)) -> (ALT_src = Baro))", [ap("GPS_fail = on", "antecedent"), ap("Baro = on", "antecedent"), ap("ALT_src = Baro", "consequent")], ["BARO_ON_UNDEFINED", "SOURCE_ABSTRACTION_UNDEFINED"]),
]

# PX4: 21 policies. Inherited rows retain the paper's inheritance text and use
# an explicit, separately-labelled binding interpretation for current-source mapping.
P += [
    policy(31, "PX4", "PX.RTL1", "PX.RTL1", "T3", "If the current altitude is less than RTL_RETURN_ALT, then altitude must be increased until the altitude is greater or equal to RTL_RETURN_ALT.", "当前高度低于 RTL_RETURN_ALT 时持续爬升，直到达到该高度。", "G(((ALT_t < RTL_RETURN_ALT) & (Mode_t = RTL)) -> (ALT_t-1 < ALT_t))", [ap("ALT_t < RTL_RETURN_ALT", "antecedent"), ap("Mode_t = RTL", "antecedent"), ap("ALT_t-1 < ALT_t", "consequent")], ["UNTIL_LOST", "PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(32, "PX4", "PX.RTL2", "PX.RTL2", "T3", "If the current altitude is greater or equal to RTL_RETURN_ALT, current flight mode is RTL, and the current vehicle is not home position, then the vehicle must move to the home position while maintaining the current altitude.", "达到 PX4 返航高度且尚未到家时保持高度并移动到家。", "G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t != home_position)) -> ((Pos_t-1 != Pos_t) & (ALT_t-1 = ALT_t)))", [ap("Mode_t = RTL", "antecedent"), ap("ALT_t >= RTL_RETURN_ALT", "antecedent"), ap("Pos_t != home_position", "antecedent"), ap("Pos_t-1 != Pos_t", "consequent"), ap("ALT_t-1 = ALT_t", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(33, "PX4", "PX.RTL3", "PX.RTL3", "T3", "If current altitude is greater or equal to RTL_RETURN_ALT and current position is the same as home position, then flight mode must be LAND.", "达到返航高度并到家后进入着陆模式。", "G(((Mode_t = RTL) & (ALT_t >= RTL_RETURN_ALT) & (Pos_t = home_position)) -> (Mode_t = LAND))", [ap("Mode_t = RTL", "antecedent"), ap("ALT_t >= RTL_RETURN_ALT", "antecedent"), ap("Pos_t = home_position", "antecedent"), ap("Mode_t = LAND", "consequent")], ["SAME_SAMPLE_MODE_CONTRADICTION"]),
    policy(34, "PX4", "PX.RTL4", "PX.RTL4", "T3", "If RTL_LAND_DELAY parameter has -1, the vehicle must hover at RTL_DESCEND_ALT.", "RTL_LAND_DELAY 为负一时在 RTL_DESCEND_ALT 高度盘旋。", "G(((Mode_t = RTL) & (RTL_DESCEND_ALT = -1)) -> ((Pos_t = Pos_t-1) & (ALT_t = ALT_t-1)))", [ap("Mode_t = RTL", "antecedent"), ap("RTL_DESCEND_ALT = -1", "antecedent_as_printed"), ap("RTL_LAND_DELAY = -1", "antecedent_from_description"), ap("Pos_t = Pos_t-1", "consequent"), ap("ALT_t-1 = ALT_t", "consequent")], ["WRONG_PARAMETER_IN_FORMULA", "PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"], binding_formula="G(((Mode_t = RTL) & (RTL_LAND_DELAY = -1)) -> ((Pos_t = Pos_t-1) & (ALT_t = ALT_t-1)))"),
    policy(35, "PX4", "PX.RTL5", "PX.RTL5", "T3", "It is the same as A.RTL4.", "与 A.RTL4 相同：着陆触地后锁定电机。", "It is the same as A.RTL4.", [ap("Mode_t = LAND", "antecedent"), ap("ALT_t = GroundALT", "antecedent"), ap("Disarm = on", "consequent")], ["INHERITANCE_NOT_PRINTED", "IMMEDIACY_UNBOUNDED", "EXACT_PHYSICAL_EQUALITY"], inherits_from="A.RTL4", binding_formula="G(((Mode_t = LAND) & (ALT_t = GroundALT)) -> (Disarm = on))"),
    policy(36, "PX4", "PX.ORBIT1", "PX.ORBIT1", "T3", "It is the same as A.CIRCLE1.", "继承 A.CIRCLE1，并把绕圈模式解释为 PX4 ORBIT。", "It is the same as A.CIRCLE1.", [ap("Mode_t = ORBIT", "antecedent"), ap("RC_pitch < 1500", "antecedent"), ap("Circle_radius_t > 0", "antecedent"), ap("Circle_radius_t < Circle_radius_t-1", "consequent")], ["INHERITANCE_NOT_PRINTED", "MODE_SUBSTITUTION_REQUIRED", "UNTIL_LOST", "PREVIOUS_SAMPLE_NOT_TIME"], inherits_from="A.CIRCLE1", binding_formula="G(((Mode_t = ORBIT) & (RC_pitch < 1500) & (Circle_radius_t > 0)) -> (Circle_radius_t < Circle_radius_t-1))"),
    policy(37, "PX4", "PX.ORBIT2", "PX.ORBIT2", "T3", "It is the same as A.CIRCLE2.", "继承 A.CIRCLE2，并把绕圈模式解释为 PX4 ORBIT。", "It is the same as A.CIRCLE2.", [ap("Mode_t = ORBIT", "antecedent"), ap("RC_pitch > 1500", "antecedent"), ap("Circle_radius_t > Circle_radius_t-1", "consequent")], ["INHERITANCE_NOT_PRINTED", "MODE_SUBSTITUTION_REQUIRED", "PREVIOUS_SAMPLE_NOT_TIME"], inherits_from="A.CIRCLE2", binding_formula="G(((Mode_t = ORBIT) & (RC_pitch > 1500)) -> (Circle_radius_t > Circle_radius_t-1))"),
    policy(38, "PX4", "PX.ORBIT3", "PX.ORBIT3", "T3", "It is the same as A.CIRCLE3.", "继承 A.CIRCLE3，并把绕圈模式解释为 PX4 ORBIT。", "It is the same as A.CIRCLE3.", [ap("Mode_t = ORBIT", "antecedent"), ap("RC_roll > 1500", "antecedent"), ap("Circle_direction_t = clockwise", "antecedent"), ap("Circle_speed_t > Circle_speed_t-1", "consequent")], ["INHERITANCE_NOT_PRINTED", "MODE_SUBSTITUTION_REQUIRED", "PREVIOUS_SAMPLE_NOT_TIME", "DIRECTION_OR_SIGN_UNDEFINED"], inherits_from="A.CIRCLE3", binding_formula="G(((Mode_t = ORBIT) & (RC_roll > 1500) & (Circle_direction_t = clockwise)) -> (Circle_speed_t > Circle_speed_t-1))"),
    policy(39, "PX4", "PX.ORBIT4", "PX.ORBIT4_5", "T3", "It is the same as A.CIRCLE4.", "继承 A.CIRCLE4，并把绕圈模式解释为 PX4 ORBIT。", "It is the same as A.CIRCLE4.", [ap("Mode_t = ORBIT", "antecedent"), ap("RC_roll > 1500", "antecedent"), ap("Circle_direction_t = counterclockwise", "antecedent"), ap("Circle_speed_t < Circle_speed_t-1", "consequent")], ["INHERITANCE_NOT_PRINTED", "MODE_SUBSTITUTION_REQUIRED", "PREVIOUS_SAMPLE_NOT_TIME", "DIRECTION_OR_SIGN_UNDEFINED"], inherits_from="A.CIRCLE4", binding_formula="G(((Mode_t = ORBIT) & (RC_roll > 1500) & (Circle_direction_t = counterclockwise)) -> (Circle_speed_t < Circle_speed_t-1))"),
    policy(40, "PX4", "PX.ORBIT5", "PX.ORBIT4_5", "T3", "The maximum radius must be 100 meters.", "绕点飞行最大半径为 100 米。", "G((Mode_t = ORBIT) -> (Circle_radius_t < 100))", [ap("Mode_t = ORBIT", "antecedent"), ap("Circle_radius_t < 100m", "consequent")], ["STRICT_MAX_BOUND"]),
    policy(41, "PX4", "PX.ORBIT6", "PX.ORBIT6", "T3", "The maximum acceleration must be limited to 2m/s^2.", "绕点飞行最大加速度限制为每平方秒 2 米。", "G((Mode_t = ORBIT) -> (Circle_speed_t < 2m/s^2))", [ap("Mode_t = ORBIT", "antecedent"), ap("Circle_speed_t < 2m/s^2", "consequent")], ["TYPE_UNIT_MISMATCH", "STRICT_MAX_BOUND"]),
    policy(42, "PX4", "PX.LAND1", "PX.LAND1", "T3", "Descending speed must be the same as MPC_LAND_SPEED parameter.", "下降速度等于 MPC_LAND_SPEED 参数。", "G((Mode_t = LAND) -> (Speed_vertical_t = MPC_LAND_SPEED))", [ap("Mode_t = LAND", "antecedent"), ap("Speed_vertical_t = MPC_LAND_SPEED", "consequent")], ["EXACT_PHYSICAL_EQUALITY", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(43, "PX4", "PX.ALTITUDE1", "PX.ALTITUDE1", "T3", "It is the same as A.ALT_HOLD2.", "继承 A.ALT_HOLD2，并把模式解释为 PX4 ALTITUDE。", "It is the same as A.ALT_HOLD2.", [ap("Mode_t = ALTITUDE", "antecedent"), ap("Throttle_t = 1500", "antecedent"), ap("ALT_t-1 = ALT_t", "consequent")], ["INHERITANCE_NOT_PRINTED", "MODE_SUBSTITUTION_REQUIRED", "PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"], inherits_from="A.ALT_HOLD2", binding_formula="G(((Mode_t = ALTITUDE) & (Throttle_t = 1500)) -> (ALT_t = ALT_t-1))"),
    policy(44, "PX4", "PX.POSITION1", "PX.POSITION1", "T3", "The vehicle must maintain a constant position.", "位置控制模式保持位置不变。", "G((Mode_t = POSITION) -> (Pos_t = Pos_t-1))", [ap("Mode_t = POSITION", "antecedent"), ap("Pos_t = Pos_t-1", "consequent")], ["PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"]),
    policy(45, "PX4", "PX.HOLD1", "PX.HOLD1", "T3", "It is the same as A.LOITER1.", "继承 A.LOITER1，并把模式解释为 PX4 HOLD。", "It is the same as A.LOITER1.", [ap("Mode_t = HOLD", "antecedent"), ap("Pos_t = Pos_t-1", "consequent"), ap("Yaw_t = Yaw_t-1", "consequent"), ap("ALT_t-1 = ALT_t", "consequent")], ["INHERITANCE_NOT_PRINTED", "MODE_SUBSTITUTION_REQUIRED", "PREVIOUS_SAMPLE_NOT_TIME", "STRICT_SAMPLE_EQUALITY"], inherits_from="A.LOITER1", binding_formula="G((Mode_t = HOLD) -> ((Pos_t = Pos_t-1) & (Yaw_t = Yaw_t-1) & (ALT_t = ALT_t-1)))"),
    policy(46, "PX4", "PX.HOLD2", "PX.HOLD2", "T3", "If MIS_LTRMIN_ALT is not -1 and current altitude is less than the parameter value, then the vehicle must ascend to this altitude.", "最小盘旋高度启用且当前高度低于它时爬升到该高度。", "G(((Mode_t = HOLD) & (MIS_LTRMIN_ALT != -1)) -> (ALT_t > ALT_t-1))", [ap("Mode_t = HOLD", "antecedent"), ap("MIS_LTRMIN_ALT != -1", "antecedent"), ap("ALT_t < MIS_LTRMIN_ALT", "antecedent_from_description"), ap("ALT_t-1 < ALT_t", "consequent"), ap("Target_ALT = MIS_LTRMIN_ALT", "target_from_description")], ["ANTECEDENT_MISSING_ALTITUDE_BOUND", "UNTIL_LOST", "PREVIOUS_SAMPLE_NOT_TIME"]),
    policy(47, "PX4", "PX.TAKEOFF1", "PX.TAKEOFF1", "T3", "When the vehicle conducts a taking off command, the target altitude must be the MIS_TAKEOFF_ALT parameter value.", "执行起飞命令时目标高度应等于 MIS_TAKEOFF_ALT。", "G((Command_t = takeoff) -> (ALT_t <= MIS_TAKEOFF_ALT))", [ap("Command_t = takeoff", "antecedent"), ap("ALT_t <= MIS_TAKEOFF_ALT", "consequent_as_printed"), ap("Target_ALT = MIS_TAKEOFF_ALT", "target_from_description")], ["TARGET_EQUALITY_WEAKENED"]),
    policy(48, "PX4", "PX.TAKEOFF2", "PX.TAKEOFF2", "T3", "When the vehicle conducts a taking off command, the speed of ascent must be the MPC_TKO_SPEED parameter value.", "执行起飞命令时上升速度应等于 MPC_TKO_SPEED。", "G((Command_t = takeoff) -> (Speed_vertical_t = MPC_TKO_SPEED))", [ap("Command_t = takeoff", "antecedent"), ap("Speed_vertical_t = MPC_TKO_SPEED", "consequent")], ["EXACT_PHYSICAL_EQUALITY", "DIRECTION_OR_SIGN_UNDEFINED"]),
    policy(49, "PX4", "PX.GPS.FS1", "PX.GPS.FS1", "T1", "If time exceeds COM_POS_FS_DELAY seconds after GPS loss is detected, the GPS fail-safe must be triggered.", "检测到 GPS 丢失后，在 COM_POS_FS_DELAY 加调度余量内触发故障保护。", "G((GPS_loss = on) -> F_[0,COM_POS_FS_DELAY+k](GPS_fail = on))", [ap("GPS_loss = on", "antecedent"), ap("F_[0,COM_POS_FS_DELAY+k](GPS_fail = on)", "consequent")], ["SCHEDULE_MARGIN_UNPUBLISHED"]),
    policy(50, "PX4", "PX.GPS.FS2", "PX.GPS.FS2", "T3", "If the GPS fail-safe is triggered and a remote controller is available, the flight mode must be changed to ALTITUDE mode.", "GPS 故障保护触发且遥控可用时进入高度模式。", "G(((GPS_fail = on) & (RC_t = on)) -> (Mode_t = ALTITUDE))", [ap("GPS_fail = on", "antecedent"), ap("RC_t = on", "antecedent"), ap("Mode_t = ALTITUDE", "consequent")], []),
    policy(51, "PX4", "PX.GPS.FS3", "PX.GPS.FS3", "T3", "If the GPS fail-safe is triggered and a remote controller is not available, the flight mode must be changed to LAND mode.", "GPS 故障保护触发且遥控不可用时进入着陆模式。", "G(((GPS_fail = on) & (RC_t = off)) -> (Mode_t = LAND))", [ap("GPS_fail = on", "antecedent"), ap("RC_t = off", "antecedent"), ap("Mode_t = LAND", "consequent")], []),
]


def validate() -> None:
    assert len(P) == 51
    assert [p["paper_order"] for p in P] == list(range(1, 52))
    assert len({p["policy_id"] for p in P}) == 51
    assert sum(p["system"] == "ArduPilot" for p in P) == 30
    assert sum(p["system"] == "PX4" for p in P) == 21
    for item in P:
        assert item["atomic_propositions"], item["policy_id"]
        for issue in item["issues"]:
            assert issue in ISSUE_DEFS, (item["policy_id"], issue)
        for atom in item["atomic_propositions"]:
            assert atom["expression"] in AP_DEFS, (item["policy_id"], atom["expression"])
            assert atom["role"] in ROLE_DEFS, (item["policy_id"], atom["role"])


def render_markdown(items: list[dict[str, object]]) -> str:
    lines = [
        "# PGFuzz Table XII 公式与原子命题清单",
        "",
        "本文件忠实保存论文表十二转录，并把用于源码绑定的解释单独列出。所有条目均为历史性质种子；不表示当前官方规范已经确认，也不表示当前实现满足性质。",
        "",
        "## 状态说明",
        "",
        "- `AP`：`Atomic Proposition`，中文为“原子命题”；表示公式中能够单独判断真假的最小条件。",
        "- `HISTORICAL_PROPERTY_SEED`：历史性质种子；仅说明它来自 PGFuzz 论文，不确认它是当前官方规范。",
        "- `NOT_ASSESSED`：未评估；不判断当前固件是否满足该性质。",
        "",
        "角色说明：",
        "",
    ]
    for role, meaning in ROLE_DEFS.items():
        lines.append(f"- `{role}`：{meaning}")
    lines.extend(["", "## 总览", "", "| 顺序 | 系统 | 性质 | 模板 | 原子命题数 | 制品目录 | 问题数 |", "|---:|---|---|---|---:|---|---:|"])
    for item in items:
        lines.append(
            f"| {item['paper_order']} | {item['system']} | `{item['policy_id']}` | `{item['template']}` | "
            f"{len(item['atomic_propositions'])} | `{item['artifact_policy_directory']}` | {len(item['issues'])} |"
        )
    for item in items:
        lines.extend([
            "",
            f"## {item['policy_id']}",
            "",
            f"- 英文原文：{item['description_en']}",
            f"- 中文说明：{item['description_zh']}",
            f"- 论文模板：`{item['template']}`",
            f"- 论文原式转录：`{item['paper_formula_transcription']}`",
            f"- 绑定用解释：`{item['binding_formula_interpretation']}`",
            f"- PGFuzz 制品目录：`{item['artifact_policy_directory']}`",
        ])
        if item["inherits_from"]:
            lines.append(f"- 继承来源：`{item['inherits_from']}`；论文没有打印完整替换式。")
        lines.extend(["", "| AP | 角色 | 表达式 | 中文真值含义 | 涉及项 |", "|---|---|---|---|---|"])
        for index, atom in enumerate(item["atomic_propositions"], 1):
            definition = AP_DEFS[atom["expression"]]
            terms = ", ".join(f"`{term}`" for term in definition["terms"])
            lines.append(
                f"| AP{index:02d} | `{atom['role']}` | `{atom['expression']}` | "
                f"{definition['meaning_zh']} | {terms} |"
            )
        if item["issues"]:
            lines.extend(["", "问题与限制：", ""])
            for issue in item["issues"]:
                lines.append(f"- `{issue}`：{ISSUE_DEFS[issue]}")
        else:
            lines.extend(["", "问题与限制：当前只记录一般的版本漂移和源码绑定门禁，没有发现表内直接冲突。"])
    return "\n".join(lines) + "\n"


def main() -> None:
    validate()
    payload = {
        "schema_version": "1.0",
        "source": {
            "paper": "PGFuzz",
            "table": "Table XII",
            "page_one_based": 18,
            "pdf_sha256": "bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa94c90d7fcd",
        },
        "counts": {
            "total": len(P),
            "ArduPilot": sum(p["system"] == "ArduPilot" for p in P),
            "PX4": sum(p["system"] == "PX4" for p in P),
            "atomic_proposition_occurrences": sum(len(p["atomic_propositions"]) for p in P),
            "unique_atomic_expressions": len({a["expression"] for p in P for a in p["atomic_propositions"]}),
        },
        "issue_definitions": ISSUE_DEFS,
        "role_definitions": ROLE_DEFS,
        "policies": P,
    }
    (ROOT / "table_xii_formula_inventory.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "table_xii_formula_inventory.md").write_text(render_markdown(P), encoding="utf-8")

    with (ROOT / "table_xii_formula_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "paper_order", "system", "policy_id", "artifact_policy_directory", "template",
            "description_en", "description_zh", "paper_formula_transcription",
            "binding_formula_interpretation", "inherits_from", "ap_count", "issues",
            "dataset_role", "implementation_satisfaction",
        ])
        for item in P:
            writer.writerow([
                item["paper_order"], item["system"], item["policy_id"], item["artifact_policy_directory"],
                item["template"], item["description_en"], item["description_zh"],
                item["paper_formula_transcription"], item["binding_formula_interpretation"],
                item["inherits_from"] or "", len(item["atomic_propositions"]),
                "|".join(item["issues"]), item["dataset_role"], item["implementation_satisfaction"],
            ])

    ap_rows = []
    for item in P:
        for index, atom in enumerate(item["atomic_propositions"], 1):
            definition = AP_DEFS[atom["expression"]]
            ap_rows.append({
                "system": item["system"],
                "property_id": item["policy_id"],
                "ap_id": f"{item['policy_id']}-AP{index:02d}",
                "role": atom["role"],
                "expression": atom["expression"],
                "truth_meaning_zh": definition["meaning_zh"],
                "terms": definition["terms"],
                "binding_status": "PENDING_CURRENT_SOURCE_BINDING",
                "implementation_satisfaction": "NOT_ASSESSED",
            })
    (ROOT / "atomic_proposition_inventory.json").write_text(
        json.dumps({"schema_version": "1.0", "rows": ap_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (ROOT / "atomic_proposition_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "system", "property_id", "ap_id", "role", "expression", "truth_meaning_zh", "terms",
            "binding_status", "implementation_satisfaction",
        ])
        writer.writeheader()
        for row in ap_rows:
            writer.writerow({**row, "terms": "|".join(row["terms"])})

    for system in ("ArduPilot", "PX4"):
        system_items = [item for item in P if item["system"] == system]
        target = ROOT / system
        (target / "formula_inventory.json").write_text(
            json.dumps({"schema_version": "1.0", "policies": system_items}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (target / "formula_inventory.md").write_text(render_markdown(system_items), encoding="utf-8")

    print(json.dumps(payload["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
