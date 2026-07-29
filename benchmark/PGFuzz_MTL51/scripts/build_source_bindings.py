#!/usr/bin/env python3
"""Build current-source and observation bindings for all PGFuzz-MTL51 AP terms.

The table is deliberately evidence-oriented: current implementation locations
identify state and observation paths, but never establish a requirement or a
firmware-conformance result.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
ROWS: list[dict[str, Any]] = []

CONFIDENCE_ZH = {
    "EXACT": "精确绑定：当前实体身份和该行所写的局部语义有直接源码证据。",
    "MODELLED": "建模绑定：需要坐标、单位、有效性、历史样本或上下文转换。",
    "UNRESOLVED": "尚未解决：当前证据不足，不能猜测等价实体或数值。",
}

OBSERVABILITY_ZH = {
    "DIRECT": "可由列出的 MAVLink 字段直接读取；仍须执行所写缩放或枚举解码。",
    "DERIVED": "需要组合多个字段、保存历史样本或执行数学换算。",
    "CONDITIONAL": "只有消息已启用且有效性、配置或运行阶段条件成立时可用。",
    "INSTRUMENTATION_REQUIRED": "标准 MAVLink 不提供等价字段，需要订阅内部状态或增加插桩。",
    "UNRESOLVED": "没有找到可靠的当前观测定义。",
}

BINDING_ROLE_ZH = {
    "PRIMARY_VALUE": "主真值来源；当前原子命题选定语义组中用于判真的核心实体。",
    "SUPPORTING_EVIDENCE": "辅助证据；用于证明主值的形成、发送、关联或消费路径，不是额外合取条件。",
    "ALTERNATIVE_SEMANTICS": "替代语义；与主组互斥的另一种论文词项解释，保留供人工切换，不同时判真。",
}

SELECTION_STATUS_ZH = {
    "PRIMARY_SELECTED": "已选定主语义组，没有其他互斥候选。",
    "PRIMARY_WITH_ALTERNATIVES": "已选定主语义组，同时保留一个或多个互斥替代组供人工审核。",
    "UNRESOLVED_PRIMARY": "主语义本身证据不足，补证前不计算真值。",
}


def add(
    system: str,
    terms: str | Iterable[str],
    binding_kind: str,
    symbol: str,
    source_path: str = "",
    source_line: int = 0,
    *,
    source_end_line: int = 0,
    function_context: str = "",
    data_type: str = "",
    unit_coordinate: str = "",
    truth_condition_zh: str,
    validity_freshness_zh: str = "",
    confidence: str,
    confidence_reason_zh: str,
    mavlink_observability: str,
    mavlink_message_fields: str = "",
    observation_conversion_zh: str = "",
    observation_limit_zh: str = "",
    current_parameter_name: str = "",
    historical_current_relation: str = "NOT_APPLICABLE",
    version_note_zh: str = "",
    binding_role: str = "",
    candidate_group: str = "",
    selection_note_zh: str = "",
) -> None:
    supporting_kinds = {
        "ASSIGNMENT",
        "ASSOCIATED_FIELD",
        "MAVLINK_ENCODER",
        "MAVLINK_SENDER",
        "PARAMETER_ACCESSOR",
        "PARAMETER_HANDLE",
        "PARAMETER_CONSUMER",
        "SELECTION_GUARD",
        "COMMAND_ACCEPTANCE",
        "COMMAND_ACK",
        "EXECUTION_STATE",
    }
    alternative_kinds = {"SEMANTIC_CANDIDATE", "NON_EQUIVALENT_CANDIDATE"}
    inferred_role = (
        "SUPPORTING_EVIDENCE"
        if binding_kind in supporting_kinds
        else "ALTERNATIVE_SEMANTICS"
        if binding_kind in alternative_kinds
        else "PRIMARY_VALUE"
    )
    if isinstance(terms, str):
        terms = [terms]
    for term in terms:
        row_role = binding_role or inferred_role
        row_group = candidate_group.format(term=term) if candidate_group else f"{term}:primary"
        ROWS.append(
            {
                "system": system,
                "term": term,
                "binding_role": row_role,
                "candidate_group": row_group,
                "selection_note_zh": selection_note_zh.format(term=term) if selection_note_zh else "",
                "binding_kind": binding_kind,
                "symbol": symbol.format(term=term),
                "source_path": source_path,
                "source_line": source_line,
                "source_end_line": source_end_line or source_line,
                "function_context": function_context,
                "data_type": data_type,
                "unit_coordinate": unit_coordinate,
                "truth_condition_zh": truth_condition_zh.format(term=term),
                "validity_freshness_zh": validity_freshness_zh,
                "confidence": confidence,
                "confidence_reason_zh": confidence_reason_zh,
                "mavlink_observability": mavlink_observability,
                "mavlink_message_fields": mavlink_message_fields,
                "observation_conversion_zh": observation_conversion_zh,
                "observation_limit_zh": observation_limit_zh,
                "current_parameter_name": current_parameter_name,
                "historical_current_relation": historical_current_relation,
                "version_note_zh": version_note_zh,
                "implementation_satisfaction": "NOT_ASSESSED",
            }
        )


def load_parameter_coverage() -> dict[tuple[str, str], dict[str, str]]:
    with (ROOT / "formula_parameter_coverage.csv").open(newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    result: dict[tuple[str, str], dict[str, str]] = {}
    for record in records:
        result.setdefault((record["system"], record["formula_parameter"]), record)
    return result


PARAMETERS = load_parameter_coverage()


def add_parameter(
    system: str,
    historical_term: str,
    symbol: str,
    source_path: str,
    source_line: int,
    *,
    data_type: str,
    unit: str,
    confidence: str = "EXACT",
    truth_note: str = "当前运行参数值等于 PARAM 协议读取值。",
    relation: str = "EXACT_SAME_NAME",
    version_note: str = "",
) -> None:
    record = PARAMETERS[(system, historical_term)]
    current_name = record["current_name"]
    runtime = record["current_runtime_value"] or "未取得运行值"
    default = record["current_default"] or "源码宏或元数据未解析为字面数值"
    add(
        system,
        historical_term,
        "PARAMETER_DEFINITION",
        symbol,
        source_path,
        source_line,
        data_type=data_type,
        unit_coordinate=unit,
        truth_condition_zh=truth_note,
        validity_freshness_zh="在测试开始及参数变更后重新读取实际值；不得把默认值当作不可变运行值。",
        confidence=confidence,
        confidence_reason_zh=(
            f"当前参数名为 {current_name}；源码/元数据默认字段为 {default}；冻结 SITL 快照值为 {runtime}。"
        ),
        mavlink_observability="DIRECT" if confidence != "UNRESOLVED" else "UNRESOLVED",
        mavlink_message_fields=("PARAM_VALUE.param_id,param_value" if confidence != "UNRESOLVED" else ""),
        observation_conversion_zh="按参数元数据单位解释 PARAM_VALUE.param_value；变更后重新读取确认。",
        observation_limit_zh=(
            "本任务只验证过读取身份，未执行运行时写入与生效测试；是否需要重启及何时生效必须逐参数验证。"
        ),
        current_parameter_name=current_name,
        historical_current_relation=relation,
        version_note_zh=version_note,
    )


def add_previous(
    system: str,
    term: str,
    base_symbol: str,
    source_path: str,
    source_line: int,
    *,
    data_type: str,
    unit: str,
    messages: str,
    note: str,
    candidate_group: str = "",
    binding_role: str = "",
    source_end_line: int = 0,
) -> None:
    add(
        system,
        term,
        "TRACE_PREVIOUS_SAMPLE",
        f"previous_accepted({base_symbol})",
        source_path,
        source_line,
        source_end_line=source_end_line,
        data_type=data_type,
        unit_coordinate=unit,
        truth_condition_zh="取同一数据源、同一坐标系的前一个已接受有效样本。",
        validity_freshness_zh=note,
        confidence="MODELLED",
        confidence_reason_zh="源码中不存在独立的 t-1 变量；必须由监视器保存历史。",
        mavlink_observability="DERIVED",
        mavlink_message_fields=messages,
        observation_conversion_zh="按发送端时间排序后保存前一有效样本；t-1 不是一秒前。",
        observation_limit_zh="采样周期、丢包、重排和估计器重置会改变相邻样本语义。",
        candidate_group=candidate_group,
        binding_role=binding_role,
    )


def build_ardupilot_rows() -> None:
    system = "ArduPilot"
    mode_lines = {
        "ACRO": 79,
        "ALT_HOLD": 80,
        "AUTO": 81,
        "GUIDED": 82,
        "LOITER": 83,
        "RTL": 84,
        "CIRCLE": 85,
        "LAND": 86,
        "DRIFT": 87,
        "SPORT": 88,
        "FLIP": 89,
        "BRAKE": 92,
    }
    add(
        system,
        "Mode_t",
        "STATE_FIELD",
        "Copter::flightmode->mode_number()",
        "baseline/ardupilot/ArduCopter/Copter.h",
        388,
        data_type="Mode::Number (uint8_t enum)",
        truth_condition_zh="读取当前 flightmode 指针指向模式的 mode_number()。",
        validity_freshness_zh="按 HEARTBEAT 产生时间或内部主循环采样时间读取；模式切换确认应使用切换后的状态。",
        confidence="EXACT",
        confidence_reason_zh="当前模式字段及 Mode::Number 枚举有直接源码定义。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.custom_mode",
        observation_conversion_zh="ArduCopter 直接把 Mode::Number 数值写入 custom_mode。",
        observation_limit_zh="消息到达时间不是模式实际切换时刻；应保存飞控发送时间序列和接收时间。",
    )
    add(
        system,
        "Mode_t",
        "MAVLINK_ENCODER",
        "GCS_Copter::custom_mode()",
        "baseline/ardupilot/ArduCopter/GCS_MAVLink_Copter.cpp",
        62,
        function_context="GCS_Copter::custom_mode() const",
        data_type="uint32_t",
        truth_condition_zh="返回当前 flightmode->mode_number() 的整数编码。",
        confidence="EXACT",
        confidence_reason_zh="编码函数直接读取当前模式。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.custom_mode",
        observation_conversion_zh="把 custom_mode 与当前 Mode::Number 枚举值比较。",
    )
    for mode, line in mode_lines.items():
        add(
            system,
            mode,
            "ENUM_CONSTANT",
            f"Mode::Number::{mode}",
            "baseline/ardupilot/ArduCopter/mode.h",
            line,
            data_type="uint8_t enum",
            truth_condition_zh=f"Mode_t == Mode::Number::{mode}。",
            confidence="EXACT",
            confidence_reason_zh="当前 Copter 模式枚举有直接定义。",
            mavlink_observability="DIRECT",
            mavlink_message_fields="HEARTBEAT.custom_mode",
            observation_conversion_zh="把消息值与该枚举整数比较。",
        )
    add_previous(
        system,
        "Mode_t-1",
        "Copter::flightmode->mode_number()",
        "baseline/ardupilot/ArduCopter/Copter.h",
        388,
        data_type="Mode::Number",
        unit="枚举",
        messages="HEARTBEAT.custom_mode",
        note="只接受同一 sysid/compid 的有序心跳；模式切换期间保留发送/到达时间。",
    )

    add(
        system,
        "ALT_t",
        "STATE_FIELD",
        "Copter::current_loc.alt",
        "baseline/ardupilot/ArduCopter/Copter.h",
        469,
        function_context="Copter::read_inertia()",
        data_type="Location altitude (int32 centimetres internally)",
        unit_coordinate="m above Home after conversion",
        truth_condition_zh="使用 current_loc 的 ABOVE_HOME 高度并换算为米。",
        validity_freshness_zh="要求 AHRS 高度估计有效、Home/原点转换成功且样本新鲜。",
        confidence="MODELLED",
        confidence_reason_zh="当前字段明确，但论文 ALT 未统一规定坐标基准。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.relative_alt,time_boot_ms",
        observation_conversion_zh="relative_alt 从毫米除以 1000 得到米。",
        observation_limit_zh="GLOBAL_POSITION_INT 不携带完整估计器有效性与重置计数。",
    )
    add(
        system,
        "ALT_t",
        "SELECTION_GUARD",
        "Copter::read_inertia() -> change_alt_frame(ABOVE_HOME) with ABOVE_HOME fallback",
        "baseline/ardupilot/ArduCopter/inertia.cpp",
        37,
        function_context="Copter::read_inertia()",
        data_type="Location altitude-frame conversion",
        unit_coordinate="m above Home after origin-to-Home conversion or explicit fallback",
        truth_condition_zh="第 27 行先写 ABOVE_ORIGIN；第 37--39 行再转换为 ABOVE_HOME，转换失败或尚无 Home 时显式回写 ABOVE_HOME。",
        validity_freshness_zh="get_relative_position_D_origin_float() 必须成功；还要记录 Home 是否已设置以及转换/回退分支。",
        confidence="EXACT",
        confidence_reason_zh="锚点位于 Home 帧转换与回退分支起点；没有把第 27 行的 ABOVE_ORIGIN 误写为 ABOVE_HOME。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.relative_alt",
    )
    add_previous(
        system,
        "ALT_t-1",
        "Copter::current_loc.alt",
        "baseline/ardupilot/ArduCopter/Copter.h",
        469,
        data_type="float after conversion",
        unit="m above same reference",
        messages="GLOBAL_POSITION_INT.relative_alt,time_boot_ms",
        note="前后样本必须采用相同 Home/原点和缩放；拒绝跨 Home 重设或时间倒序。",
    )
    add(
        system,
        "ALT_Baro",
        "STATE_FIELD",
        "Copter::baro_alt_m",
        "baseline/ardupilot/ArduCopter/Copter.h",
        461,
        function_context="Copter::read_barometer()",
        data_type="float",
        unit_coordinate="m above barometer reference/Home-oriented offset",
        truth_condition_zh="读取 barometer.get_altitude() 更新后的 baro_alt_m。",
        validity_freshness_zh="同时要求 AP_Baro::healthy() 且本周期已更新。",
        confidence="MODELLED",
        confidence_reason_zh="字段明确，但其参考面不保证与融合 ALT_t 完全相同。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准位置消息发送融合高度，不直接发送这个原始/前端气压计高度字段。",
    )
    add(
        system,
        "ALT_Baro",
        "ASSIGNMENT",
        "Copter::baro_alt_m = AP_Baro::get_altitude()",
        "baseline/ardupilot/ArduCopter/sensors.cpp",
        8,
        function_context="Copter::read_barometer()",
        data_type="float",
        unit_coordinate="m above barometer reference/Home-oriented offset",
        truth_condition_zh="每次读取气压计后，把 AP_Baro::get_altitude() 的结果写入 baro_alt_m。",
        validity_freshness_zh="必须与气压计更新周期和 healthy() 结果一起解释。",
        confidence="EXACT",
        confidence_reason_zh="当前赋值语句直接连接函数返回值与状态字段；高度基准仍由另一行建模说明。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 不直接发送 baro_alt_m。",
    )
    add(
        system,
        "ALT_GPS",
        "FUNCTION_RETURN",
        "AP_GPS::location().alt",
        "baseline/ardupilot/libraries/AP_GPS/AP_GPS.h",
        328,
        data_type="Location altitude (int32 centimetres)",
        unit_coordinate="GPS Location altitude frame",
        truth_condition_zh="读取主 GPS 最近定位的 Location.alt。",
        validity_freshness_zh="要求 GPS fix、时间戳和位置字段有效；必须统一到 ALT_t 的高度基准。",
        confidence="MODELLED",
        confidence_reason_zh="GPS 高度字段存在，但论文没有定义与融合高度的基准转换。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GPS_RAW_INT.alt,time_usec,fix_type",
        observation_conversion_zh="GPS_RAW_INT.alt 从毫米换算为米，并检查 fix_type。",
        observation_limit_zh="AP_GPS::location() 读取动态主实例，但 GPS_RAW_INT 当前发送实例 0；单 GPS 或主实例为 0 时才直接对应。",
    )
    add(
        system,
        "ALT_src",
        "STATE_FIELD",
        "AP_NavEKF3_core::activeHgtSource",
        "baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_core.h",
        1481,
        data_type="AP_NavEKF_Source::SourceZ enum",
        truth_condition_zh="读取当前 EKF3 核实际生效的高度源。",
        validity_freshness_zh="必须知道当前活动 EKF 核；参数配置源不等于运行时实际源。",
        confidence="MODELLED",
        confidence_reason_zh="运行字段明确，但当前活动估计器和多核选择需要上下文。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 没有直接发布 activeHgtSource。",
        candidate_group="ALT_src:runtime_active",
    )
    add(
        system,
        "ALT_src",
        "FUNCTION_RETURN",
        "AP_NavEKF_Source::getActiveSourceSet(core_index)",
        "baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.h",
        66,
        source_end_line=68,
        function_context="AP_NavEKF_Source::getActiveSourceSet(uint8_t) const",
        data_type="uint8_t source-set index",
        unit_coordinate="0..2 selecting EK3 source set 1..3",
        truth_condition_zh="根据当前 EKF 核索引读取正在使用的源集编号。",
        validity_freshness_zh="必须与同一 core_index 的 getPosZSource() 和 activeHgtSource 配对。",
        confidence="EXACT",
        confidence_reason_zh="当前内联访问器直接返回每个核的活动源集。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 不发布每个 EKF 核的活动源集。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="ALT_src:runtime_active",
    )
    add(
        system,
        "ALT_src",
        "FUNCTION_RETURN",
        "AP_NavEKF_Source::getPosZSource(core_index)",
        "baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp",
        239,
        source_end_line=247,
        function_context="AP_NavEKF_Source::getPosZSource(uint8_t) const",
        data_type="SourceZ enum",
        truth_condition_zh="从活动源集读取垂直位置配置，并在没有气压计实例时把 BARO 配置退化为 NONE。",
        validity_freshness_zh="返回的是活动源集的配置选择；selectHeightForFusion() 仍可能按新鲜度和回退规则形成实际 activeHgtSource。",
        confidence="EXACT",
        confidence_reason_zh="活动源集到垂直位置配置的访问路径直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="ALT_src:runtime_active",
    )
    add(
        system,
        "ALT_src",
        "PARAMETER_DEFINITION",
        "AP_NavEKF_Source::_source_set[0].posz / EK3_SRC1_POSZ",
        "baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp",
        46,
        data_type="AP_Int8 / SourceZ enum",
        unit_coordinate="0:none, 1:barometer, 2:rangefinder, 3:GPS, 4:beacon, 6:external navigation",
        truth_condition_zh="读取第一个 EKF3 源集配置的垂直位置源。",
        validity_freshness_zh="配置选择不等于当前运行核实际采用源；要与 activeHgtSource 联合解释。",
        confidence="MODELLED",
        confidence_reason_zh="配置参数身份和枚举直接可证，但论文 ALT_src 未区分配置源与实际源。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="PARAM_VALUE.param_id=EK3_SRC1_POSZ,param_value",
        observation_conversion_zh="按 SourceZ 枚举解码参数值。",
        observation_limit_zh="参数可读只证明配置，不证明实际生效的高度源。",
        current_parameter_name="EK3_SRC1_POSZ",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="ALT_src:configured_source_set_1",
        selection_note_zh="配置源只是实际源的候选，不能替代 activeHgtSource。",
    )
    for set_index, param_name, line in [(2, "EK3_SRC2_POSZ", 82), (3, "EK3_SRC3_POSZ", 119)]:
        add(
            system,
            "ALT_src",
            "PARAMETER_DEFINITION",
            f"AP_NavEKF_Source::_source_set[{set_index - 1}].posz / {param_name}",
            "baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp",
            line,
            data_type="AP_Int8 / SourceZ enum",
            truth_condition_zh=f"读取第 {set_index} 个 EKF3 源集配置的垂直位置源。",
            validity_freshness_zh="只有当该源集被选为 active source set 时才是配置候选；仍不等于 activeHgtSource。",
            confidence="MODELLED",
            confidence_reason_zh="当前配置定义可证，但它不是实际高度融合源。",
            mavlink_observability="DIRECT",
            mavlink_message_fields=f"PARAM_VALUE.param_id={param_name},param_value",
            observation_limit_zh="只证明配置值。",
            current_parameter_name=param_name,
            binding_role="ALTERNATIVE_SEMANTICS",
            candidate_group="ALT_src:configured_source_sets_2_3",
        )
    add(
        system,
        "ALT_src",
        "SELECTION_GUARD",
        "NavEKF3_core::selectHeightForFusion() -> activeHgtSource",
        "baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp",
        1268,
        function_context="NavEKF3_core::selectHeightForFusion()",
        data_type="SourceZ selection and fallback assignments",
        truth_condition_zh="根据当前源集、传感器新鲜度和有效性选择 activeHgtSource，失效时可回退到 BARO。",
        validity_freshness_zh="需要同时保留 core_index、源集和 500 ms 新鲜度分支；500 ms 是当前实现条件，不是论文规范时限。",
        confidence="MODELLED",
        confidence_reason_zh="它证明运行时实际源的形成路径，不用于从控制流反推新性质。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="ALT_src:runtime_active",
    )
    add(
        system,
        "Baro",
        "FUNCTION_RETURN",
        "AP_Baro::healthy()",
        "baseline/ardupilot/libraries/AP_Baro/AP_Baro.h",
        58,
        data_type="bool",
        truth_condition_zh="若把 Baro=on 解释为主气压计健康，则 healthy()==true。",
        validity_freshness_zh="该解释不等于气压计被 EKF 选为高度源。",
        confidence="MODELLED",
        confidence_reason_zh="论文没有说明 on 是健康、启用、存在数据还是被选中。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="SYS_STATUS.onboard_control_sensors_health",
        observation_limit_zh="健康位是汇总状态，无法证明当前高度源为气压计。",
        candidate_group="Baro:health",
    )
    add(
        system,
        "Baro",
        "MAVLINK_SENDER",
        "SYS_STATUS pressure health uses AP_Baro::all_healthy()",
        "baseline/ardupilot/libraries/GCS_MAVLink/GCS.cpp",
        491,
        function_context="GCS::update_sensor_status_flags()",
        data_type="aggregated sensor-health bit",
        truth_condition_zh="SYS_STATUS 的绝对压力健康位只有在所有气压计实例健康时置位。",
        validity_freshness_zh="主值 AP_Baro::healthy() 只检查主实例；所有实例健康与主实例健康不是同一个布尔条件。",
        confidence="EXACT",
        confidence_reason_zh="发送端明确调用 all_healthy()，因此只能作为主健康值的有条件外部代理。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="SYS_STATUS.onboard_control_sensors_health",
        observation_limit_zh="该位不能精确等价于 AP_Baro::healthy()，也不能证明气压计被选为高度源。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Baro:health",
    )
    add(
        system,
        "Baro",
        "ENUM_CONSTANT",
        "AP_NavEKF_Source::SourceZ::BARO",
        "baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.h",
        30,
        data_type="SourceZ enum",
        truth_condition_zh="若把 Baro=on 解释为当前高度源，则 activeHgtSource==BARO。",
        confidence="MODELLED",
        confidence_reason_zh="这是另一种合理解释，不能与传感器健康混为一谈。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Baro:source_enum",
    )
    add(
        system,
        "Baro",
        "ASSIGNMENT",
        "activeHgtSource = AP_NavEKF_Source::SourceZ::BARO",
        "baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp",
        1315,
        function_context="NavEKF3_core::selectHeightForFusion()",
        data_type="SourceZ assignment",
        truth_condition_zh="配置源为 BARO 或其他高度源失效回退时，运行字段可被赋为 BARO。",
        validity_freshness_zh="要区分直接选择分支与 fallback_to_baro 分支。",
        confidence="MODELLED",
        confidence_reason_zh="是枚举在运行选择函数中的形成证据，不代表传感器健康命题。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Baro:source_enum",
    )

    add(
        system,
        "Pos_t",
        "STATE_FIELD",
        "Copter::current_loc.lat,current_loc.lng",
        "baseline/ardupilot/ArduCopter/Copter.h",
        469,
        data_type="int32 latitude/longitude",
        unit_coordinate="degrees scaled by 1e7, WGS84",
        truth_condition_zh="当前位置由 current_loc 的纬度和经度组成。",
        validity_freshness_zh="要求 position_ok() 且 AHRS 位置样本新鲜；相等判断必须给距离容差。",
        confidence="MODELLED",
        confidence_reason_zh="位置字段明确，但论文严格相等未给坐标容差。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.lat,lon,time_boot_ms",
        observation_conversion_zh="lat/lon 按 1e7 缩放恢复为度，比较时计算地表距离。",
        observation_limit_zh="发送器忽略 get_location() 失败返回值并可能发送旧位置；消息不携带 position_ok() 或估计器重置状态。",
    )
    add_previous(
        system,
        "Pos_t-1",
        "Copter::current_loc.lat,lng",
        "baseline/ardupilot/ArduCopter/Copter.h",
        469,
        data_type="position tuple",
        unit="WGS84 degrees or derived metres",
        messages="GLOBAL_POSITION_INT.lat,lon,time_boot_ms",
        note="只比较同一坐标定义的连续有效样本；严格整数相等不能替代物理静止容差。",
    )
    add(
        system,
        "home_position",
        "FUNCTION_RETURN",
        "AP_AHRS::get_home()",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
        600,
        data_type="const Location&",
        unit_coordinate="WGS84 lat/lon and Location altitude",
        truth_condition_zh="Home 已设置时读取 AHRS 保存的 Home Location。",
        validity_freshness_zh="要求 home_is_set()；当前 RTL 目的地也可能是 rally point，不能自动把 return target 等同于 Home。",
        confidence="EXACT",
        confidence_reason_zh="Home 字段身份和发送函数有直接源码证据。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HOME_POSITION.latitude,longitude,altitude,time_usec",
        observation_conversion_zh="纬经度除以 1e7，高度毫米除以 1000。",
        observation_limit_zh="Home 是参考点，不保证是当前 RTL 选择的最终 return_target。",
        candidate_group="home_position:home",
    )
    add(
        system,
        "home_position",
        "STATE_FIELD",
        "AP_AHRS::_home, AP_AHRS::_home_is_set",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
        857,
        function_context="AP_AHRS::get_home(); AP_AHRS::home_is_set()",
        data_type="Location plus bool",
        unit_coordinate="absolute Location frame after set_home conversion",
        truth_condition_zh="只有 _home_is_set==true 时 _home 才是有效 Home。",
        validity_freshness_zh="Home 可被重设；比较轨迹时要保留设定事件和当前值。",
        confidence="EXACT",
        confidence_reason_zh="底层存储字段和有效位直接定义。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HOME_POSITION.latitude,longitude,altitude,time_usec",
        observation_limit_zh="HOME_POSITION.time_usec 是消息发送时间，不是 Home 设定时间。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="home_position:home",
    )
    add(
        system,
        "home_position",
        "ASSIGNMENT",
        "AP_AHRS::set_home(): _home = tmp; _home_is_set = true",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp",
        2027,
        function_context="AP_AHRS::set_home(const Location&)",
        data_type="Location assignment and validity latch",
        truth_condition_zh="输入位置校验并转成 ABSOLUTE 高度帧后写入 Home，再置有效位。",
        validity_freshness_zh="set_home() 失败时不得更新监视器中的 Home。",
        confidence="EXACT",
        confidence_reason_zh="当前赋值和帧转换路径直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="HOME_POSITION 更新序列",
        observation_limit_zh="外部仅能由值变化推断重设，没有精确设定时刻字段。",
        candidate_group="home_position:home",
    )
    add(
        system,
        "home_position",
        "MAVLINK_SENDER",
        "GCS_MAVLINK::send_home_position()",
        "baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp",
        3107,
        function_context="GCS_MAVLINK::send_home_position()",
        data_type="HOME_POSITION encoder",
        truth_condition_zh="home_is_set() 为真时发送 get_home() 的经纬度、高度和局部向量。",
        validity_freshness_zh="发送时间与 Home 设定时间分开保存。",
        confidence="EXACT",
        confidence_reason_zh="当前 MAVLink 编码函数直接读取 Home。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HOME_POSITION.latitude,longitude,altitude,x,y,z,time_usec",
        candidate_group="home_position:home",
    )
    add(
        system,
        "home_position",
        "STATE_FIELD",
        "ModeRTL::rtl_path.return_target",
        "baseline/ardupilot/ArduCopter/mode.h",
        1609,
        function_context="ModeRTL::compute_return_target()",
        data_type="Location",
        unit_coordinate="WGS84 position with explicit Location altitude frame",
        truth_condition_zh="若公式中 home_position 实际指 RTL 当前返航目标，则读取 rtl_path.return_target。",
        validity_freshness_zh="该目标由 Home 或 rally point 生成，高度帧还会被地形、围栏和最低返航高度调整。",
        confidence="MODELLED",
        confidence_reason_zh="它是当前 RTL 真正使用的返航目标，但论文词项名为 home_position，两者并非始终相等。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="HOME_POSITION 只发送 Home，不发送可能为 rally point 的 rtl_path.return_target。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="home_position:rtl_return_target",
    )
    add(
        system,
        "home_position",
        "ASSIGNMENT",
        "ModeRTL::compute_return_target(): rally-or-Home assignment",
        "baseline/ardupilot/ArduCopter/mode_rtl.cpp",
        467,
        source_end_line=475,
        function_context="ModeRTL::compute_return_target()",
        data_type="Location assignment",
        unit_coordinate="absolute WGS84 Location after frame conversion",
        truth_condition_zh="启用 Rally 时选择最近 rally point 或 Home；未启用时直接复制 Home。",
        validity_freshness_zh="该赋值只形成当前 RTL 目标，后续还会调整高度参考面和安全高度。",
        confidence="EXACT",
        confidence_reason_zh="Home/rally 分支及 return_target 赋值直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="home_position:rtl_return_target",
    )
    add(
        system,
        "GroundALT",
        "UNRESOLVED_ABSTRACTION",
        "no type-compatible numeric GroundALT definition",
        data_type="undefined paper abstraction",
        truth_condition_zh="论文没有给 GroundALT 的数值类型、坐标参考面或容差，不能把布尔 landed 直接代入数值等式。",
        validity_freshness_zh="补充官方定义或明确把性质重写为 landed 布尔命题前不判真。",
        confidence="UNRESOLVED",
        confidence_reason_zh="当前可找到着陆状态和相对 Home 高度候选，但都不是已证明等价的数值 GroundALT。",
        mavlink_observability="UNRESOLVED",
        candidate_group="GroundALT:untyped_unresolved",
    )
    add(
        system,
        "GroundALT",
        "STATE_FIELD",
        "Copter::ap.land_complete",
        "baseline/ardupilot/ArduCopter/Copter.h",
        361,
        data_type="bool",
        truth_condition_zh="若性质真实含义是触地，则使用 land_complete==true 作为语义代理，而不是高度精确相等。",
        validity_freshness_zh="这是着陆检测状态，不是数值高度。",
        confidence="MODELLED",
        confidence_reason_zh="论文 GroundALT 未定义；布尔着陆检测只可作为触地语义代理。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="EXTENDED_SYS_STATE.landed_state",
        observation_conversion_zh="判断 landed_state==MAV_LANDED_STATE_ON_GROUND。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GroundALT:landed_state",
    )
    add(
        system,
        "GroundALT",
        "DERIVED_EXPRESSION",
        "relative_altitude ~= 0",
        "baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp",
        6163,
        data_type="float after scaling",
        unit_coordinate="m above Home",
        truth_condition_zh="若把地面定义为 Home 高度，只能在有来源的容差内判断 relative_alt 接近零。",
        confidence="UNRESOLVED",
        confidence_reason_zh="一般地面不必等于 Home 高度，论文也未给容差。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="GLOBAL_POSITION_INT.relative_alt",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GroundALT:home_zero_height",
    )

    attitude = {
        "Roll_t": ("AP_AHRS::get_roll_rad()", 636, "ATTITUDE.roll"),
        "Pitch_t": ("AP_AHRS::get_pitch_rad()", 637, "ATTITUDE.pitch"),
        "Yaw_t": ("AP_AHRS::get_yaw_rad()", 638, "ATTITUDE.yaw"),
    }
    for term, (symbol, line, field) in attitude.items():
        add(
            system,
            term,
            "FUNCTION_RETURN",
            symbol,
            "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
            line,
            data_type="float",
            unit_coordinate="radians, body attitude in navigation frame",
            truth_condition_zh=f"读取 {symbol} 返回的当前欧拉角。",
            validity_freshness_zh="要求姿态估计有效；角度比较必须处理 ±π 环绕。",
            confidence="EXACT",
            confidence_reason_zh="当前姿态访问器和 MAVLink 编码函数直接对应。",
            mavlink_observability="DIRECT",
            mavlink_message_fields=field + ",time_boot_ms",
            observation_conversion_zh="ATTITUDE 角度单位已经是弧度。",
        )
    add_previous(
        system,
        "Yaw_t-1",
        "AP_AHRS::get_yaw_rad()",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
        638,
        data_type="float",
        unit="radians",
        messages="ATTITUDE.yaw,time_boot_ms",
        note="使用环形角差并拒绝时间倒序；t-1 是前一有效姿态样本。",
    )
    originals = {
        "Roll_original": "orig_attitude_euler_rad.x",
        "Pitch_original": "orig_attitude_euler_rad.y",
        "Yaw_original": "orig_attitude_euler_rad.z",
    }
    for term, member in originals.items():
        add(
            system,
            term,
            "CLASS_MEMBER",
            f"ModeFlip::{member}",
            "baseline/ardupilot/ArduCopter/mode.h",
            981,
            function_context="ModeFlip::init()",
            data_type="float component of Vector3f",
            unit_coordinate="radians",
            truth_condition_zh="读取 FLIP 初始化时保存的原始姿态对应分量。",
            validity_freshness_zh="只在同一次 FLIP 实例内有效；必须用 mode entry 关联键配对。",
            confidence="EXACT",
            confidence_reason_zh="保存成员和赋值位置均有当前源码证据。",
            mavlink_observability="INSTRUMENTATION_REQUIRED",
            observation_limit_zh="标准 MAVLink 不发布这三个保存的原始目标值。",
        )
    add(
        system,
        "Roll_rate",
        "CONTROL_SETPOINT",
        "FLIP_ROTATION_RATE_RADS",
        "baseline/ardupilot/ArduCopter/mode_flip.cpp",
        23,
        data_type="float macro constant",
        unit_coordinate="rad/s (400 deg/s)",
        truth_condition_zh="若论文指控制请求，则 FLIP Start/Roll 阶段请求值为该常量乘方向。",
        validity_freshness_zh="必须区分控制请求和实际测量角速度。",
        confidence="MODELLED",
        confidence_reason_zh="400 deg/s 在当前控制请求中存在，但论文未说明是目标还是实际值。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="ATTITUDE.rollspeed 是实际估计角速度，不是控制器请求。",
        candidate_group="Roll_rate:control_request",
    )
    add(
        system,
        "Roll_rate",
        "FUNCTION_RETURN",
        "AP_AHRS::get_gyro().x",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
        93,
        data_type="float",
        unit_coordinate="rad/s body x",
        truth_condition_zh="若论文指实际横滚角速度，则读取漂移校正后的机体系 x 轴角速度。",
        confidence="MODELLED",
        confidence_reason_zh="实际量可观测，但不应与 400 deg/s 控制请求混为一谈。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="ATTITUDE.rollspeed,time_boot_ms",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Roll_rate:actual_rate",
    )
    add(
        system,
        "Roll_direction",
        "CLASS_MEMBER",
        "ModeFlip::roll_dir",
        "baseline/ardupilot/ArduCopter/mode.h",
        995,
        data_type="int8_t (-1 left, +1 right)",
        truth_condition_zh="右翻滚当且仅当 roll_dir==1。",
        validity_freshness_zh="只在当前 FLIP 实例初始化后有效。",
        confidence="EXACT",
        confidence_reason_zh="成员注释和初始化分支直接定义方向。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="Roll_direction:commanded_direction",
    )
    add(
        system,
        "Roll_direction",
        "DERIVED_EXPRESSION",
        "sign(AP_AHRS::get_gyro().x)",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
        93,
        data_type="direction derived from float sign",
        unit_coordinate="body x angular-rate sign",
        truth_condition_zh="若论文指实际横滚方向，则由漂移校正后的 x 轴角速度符号判定。",
        validity_freshness_zh="必须使用机体坐标系约定，并与内部 roll_dir 的左/右标记区分。",
        confidence="MODELLED",
        confidence_reason_zh="实际角速度可观测，但论文没有说 Roll_direction 是指令方向还是实际方向。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="ATTITUDE.rollspeed,time_boot_ms",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Roll_direction:actual_direction",
    )
    add(
        system,
        "Roll_direction",
        "ASSIGNMENT",
        "ModeFlip::roll_dir = FLIP_ROLL_RIGHT or FLIP_ROLL_LEFT",
        "baseline/ardupilot/ArduCopter/mode_flip.cpp",
        71,
        function_context="ModeFlip::init(bool)",
        data_type="int8_t from RC roll control sign",
        truth_condition_zh="俯仰摇杆未选择翻转时，根据横滚 control_in 符号写入右翻或左翻常量。",
        validity_freshness_zh="只在 Flip 模式成功初始化后有效。",
        confidence="EXACT",
        confidence_reason_zh="方向常量和赋值分支直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Roll_direction:commanded_direction",
    )
    add(
        system,
        "Roll_direction",
        "CONTROL_SETPOINT",
        "FLIP_ROTATION_RATE_RADS * ModeFlip::roll_dir",
        "baseline/ardupilot/ArduCopter/mode_flip.cpp",
        118,
        function_context="ModeFlip::run()",
        data_type="float roll-rate setpoint",
        unit_coordinate="rad/s body roll setpoint",
        truth_condition_zh="Start/Roll 阶段把 roll_dir 乘以 400 deg/s 请求传给姿态控制器。",
        validity_freshness_zh="这是指令方向，不是实际角速度轨迹。",
        confidence="EXACT",
        confidence_reason_zh="控制器消费点直接使用 roll_dir。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Roll_direction:commanded_direction",
    )
    for term, state, line in [("FLIP1", "Start", 984), ("FLIP3", "Recover", 988)]:
        add(
            system,
            term,
            "PAPER_PHASE_MODEL",
            f"ModeFlip::_state == FlipState::{state}",
            "baseline/ardupilot/ArduCopter/mode.h",
            line,
            data_type="private FlipState enum",
            truth_condition_zh=f"把论文阶段标签近似解释为当前 FlipState::{state}。",
            validity_freshness_zh="该对应是版本建模，不是论文证明的同名源码实体。",
            confidence="MODELLED",
            confidence_reason_zh="当前状态机有相似阶段，但论文 FLIP1/FLIP3 的身份未公开绑定。",
            mavlink_observability="INSTRUMENTATION_REQUIRED",
        )

    add(
        system,
        "Circle_radius_t",
        "FUNCTION_RETURN",
        "AC_Circle::get_radius_m()",
        "baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h",
        58,
        data_type="float",
        unit_coordinate="m target radius",
        truth_condition_zh="读取当前圆周控制器半径目标；内部 _radius_m 非正时回退到参数半径。",
        validity_freshness_zh="只在当前 CIRCLE 控制器实例初始化并更新时有效。",
        confidence="EXACT",
        confidence_reason_zh="访问器和内部 _radius_m 字段有直接源码定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="当前 ArduPilot 没有标准 MAVLink 字段直接发布控制器目标半径。",
    )
    add_previous(
        system,
        "Circle_radius_t-1",
        "AC_Circle::get_radius_m()",
        "baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h",
        58,
        data_type="float",
        unit="m target radius",
        messages="内部插桩样本",
        note="只比较同一 CIRCLE 实例的有序插桩样本；t-1 不是固定时间间隔。",
    )
    add(
        system,
        "Circle_speed_t",
        "FUNCTION_RETURN",
        "AC_Circle::get_rate_current()",
        "baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h",
        73,
        data_type="float",
        unit_coordinate="deg/s signed angular target rate",
        truth_condition_zh="若论文 speed 指圆周角速度大小，则取 get_rate_current() 的绝对值。",
        validity_freshness_zh="必须明确它是控制目标角速度，不是由位置轨迹测得的实际线速度。",
        confidence="MODELLED",
        confidence_reason_zh="当前有符号目标角速度可定位，但论文没有说明 speed 的物理定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
    )
    add_previous(
        system,
        "Circle_speed_t-1",
        "AC_Circle::get_rate_current()",
        "baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h",
        73,
        data_type="float",
        unit="deg/s angular target magnitude",
        messages="内部插桩样本",
        note="前后样本必须都取相同的目标角速度定义及绝对值规则。",
    )
    add(
        system,
        "Circle_direction_t",
        "DERIVED_EXPRESSION",
        "sign(AC_Circle::get_rate_current())",
        "baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h",
        73,
        data_type="direction derived from float sign",
        truth_condition_zh="角速度大于零为顺时针，小于零为逆时针，等于零为停止。",
        validity_freshness_zh="只对当前 CIRCLE 控制目标成立。",
        confidence="EXACT",
        confidence_reason_zh="当前 set_rate_degs 注释直接定义正值顺时针、负值逆时针。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
    )
    add(
        system,
        "Circle_direction_t",
        "ASSOCIATED_FIELD",
        "AC_Circle::set_rate_degs() sign convention",
        "baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h",
        75,
        source_end_line=77,
        data_type="documented sign convention",
        truth_condition_zh="正目标角速度表示顺时针，负目标角速度表示逆时针。",
        validity_freshness_zh="该约定描述控制目标方向，不证明飞行器实际运动方向。",
        confidence="EXACT",
        confidence_reason_zh="当前接口注释直接写明正负号方向。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Circle_direction_t:primary",
    )

    rc_terms = {
        "Throttle_t": ("channel_throttle", 244, "油门"),
        "RC_throttle_t": ("channel_throttle", 244, "油门"),
        "RC_pitch": ("channel_pitch", 243, "俯仰"),
        "RC_pitch_t": ("channel_pitch", 243, "俯仰"),
        "RC_roll": ("channel_roll", 242, "横滚"),
        "RC_roll_t": ("channel_roll", 242, "横滚"),
        "RC_yaw_t": ("channel_yaw", 245, "偏航"),
    }
    for term, (channel, line, label) in rc_terms.items():
        add(
            system,
            term,
            "FUNCTION_RETURN",
            f"Copter::{channel}->get_radio_in()",
            "baseline/ardupilot/libraries/RC_Channel/RC_Channel.h",
            96,
            function_context="RC_Channel::get_radio_in() const",
            data_type="int16_t raw PWM",
            unit_coordinate="microseconds/PWM",
            truth_condition_zh=f"论文与 1500 比较时读取映射后的{label}通道原始 PWM。",
            validity_freshness_zh="要求 RC 输入有效；通道编号由 RC_MAP 配置确定，不能固定假设物理通道号。",
            confidence="EXACT",
            confidence_reason_zh="当前通道指针和 get_radio_in() 访问器有直接证据。",
            mavlink_observability="CONDITIONAL",
            mavlink_message_fields="RC_CHANNELS.chanN_raw,time_boot_ms",
            observation_conversion_zh="按当前 RC_MAP 找到 N；原始值无需与归一化 control_in 混用。",
            observation_limit_zh="消息流必须启用，且失效/覆盖输入可能改变来源。",
        )
    for terms, channel, line, label in [
        (("RC_roll", "RC_roll_t"), "roll", 23, "横滚"),
        (("RC_pitch", "RC_pitch_t"), "pitch", 24, "俯仰"),
        (("Throttle_t", "RC_throttle_t"), "throttle", 25, "油门"),
        (("RC_yaw_t",), "yaw", 26, "偏航"),
    ]:
        add(
            system,
            terms,
            "ASSIGNMENT",
            f"Copter::channel_{channel} = &rc().get_{channel}_channel()",
            "baseline/ardupilot/ArduCopter/radio.cpp",
            line,
            function_context="Copter::init_rc_in()",
            data_type="RC_Channel pointer assignment",
            truth_condition_zh=f"把逻辑{label}功能绑定到 RC_Channels 当前映射的通道对象，再由 get_radio_in() 读取原始值。",
            validity_freshness_zh="逻辑功能映射可由 RC_MAP 参数改变；必须在测试开始和参数更新后重新确认。",
            confidence="EXACT",
            confidence_reason_zh="当前逻辑通道指针形成赋值直接可证。",
            mavlink_observability="CONDITIONAL",
            mavlink_message_fields=f"PARAM_VALUE.param_id=RCMAP_{channel.upper()} 或当前 RC mapping; RC_CHANNELS.chanN_raw",
            observation_limit_zh="必须用当前参数确定 N，不能从指针声明猜测物理通道号。",
            binding_role="SUPPORTING_EVIDENCE",
            candidate_group="{term}:primary",
        )
    previous_rc = {
        "RC_throttle_t-1": "channel_throttle->get_radio_in()",
        "RC_pitch_t-1": "channel_pitch->get_radio_in()",
        "RC_roll_t-1": "channel_roll->get_radio_in()",
        "RC_yaw_t-1": "channel_yaw->get_radio_in()",
    }
    for term, symbol in previous_rc.items():
        add_previous(
            system,
            term,
            symbol,
            "baseline/ardupilot/libraries/RC_Channel/RC_Channel.h",
            96,
            data_type="int16_t",
            unit="raw PWM",
            messages="RC_CHANNELS.chanN_raw,time_boot_ms",
            note="前后样本必须来自同一映射通道和来源；RC failsafe 样本不得当作正常输入。",
        )

    add(
        system,
        "Armed",
        "FUNCTION_RETURN",
        "AP_Motors::armed()",
        "baseline/ardupilot/libraries/AP_Motors/AP_Motors_Class.h",
        117,
        data_type="bool",
        truth_condition_zh="Armed=true 当且仅当 motors->armed()==true。",
        confidence="EXACT",
        confidence_reason_zh="电机武装状态访问器直接返回内部 _armed。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.base_mode",
        observation_conversion_zh="检查 MAV_MODE_FLAG_SAFETY_ARMED 位是否存在。",
    )
    add(
        system,
        "Disarm",
        "DERIVED_EXPRESSION",
        "!AP_Motors::armed()",
        "baseline/ardupilot/libraries/AP_Motors/AP_Motors_Class.h",
        117,
        data_type="bool",
        truth_condition_zh="Disarm=on 当且仅当 motors->armed()==false。",
        confidence="EXACT",
        confidence_reason_zh="是武装布尔状态的直接否定。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.base_mode",
        observation_conversion_zh="检查 MAV_MODE_FLAG_SAFETY_ARMED 位不存在。",
    )
    add(
        system,
        "RC_fail",
        "STATE_FIELD",
        "Copter::failsafe.radio",
        "baseline/ardupilot/ArduCopter/Copter.h",
        402,
        data_type="1-bit boolean",
        truth_condition_zh="RC_fail=on 当且仅当 failsafe.radio==true。",
        validity_freshness_zh="低油门路径需连续三次低值；另有无输入超时路径。",
        confidence="EXACT",
        confidence_reason_zh="当前 Copter 的 radio failsafe 状态字段直接定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 没有一个稳定字段直接携带 failsafe.radio；文本告警只能条件性提示。",
    )
    add(
        system,
        "GPS_fail",
        "SEMANTIC_CANDIDATE",
        "Copter::failsafe.ekf",
        "baseline/ardupilot/ArduCopter/Copter.h",
        404,
        data_type="1-bit boolean",
        truth_condition_zh="只有把论文 GPS_fail 放宽为 EKF 位置估计故障时，才可候选使用 failsafe.ekf。",
        validity_freshness_zh="GPS 丢失不等于 EKF failsafe；其他定位源可继续提供位置。",
        confidence="UNRESOLVED",
        confidence_reason_zh="当前版本没有找到仅由 GPS 丢失定义的同等单一状态。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="需要内部状态订阅；不能用 GPS_RAW_INT 缺失直接等价替换。",
        binding_role="PRIMARY_VALUE",
        candidate_group="GPS_fail:unresolved_paper_semantics",
    )
    add(
        system,
        "GPS_fail",
        "ASSIGNMENT",
        "Copter::failsafe_ekf_event/off_event(): failsafe.ekf = true/false",
        "baseline/ardupilot/ArduCopter/ekf_check.cpp",
        169,
        source_end_line=226,
        function_context="Copter::failsafe_ekf_event(); Copter::failsafe_ekf_off_event()",
        data_type="bool state transitions",
        truth_condition_zh="EKF 方差/位置估计故障事件置位 failsafe.ekf，清除事件再复位。",
        validity_freshness_zh="该状态由 EKF 质量与模式要求形成，不是 GPS 消息丢失专用状态。",
        confidence="EXACT",
        confidence_reason_zh="置位和清除赋值直接可证，但只说明候选状态形成，不能解决论文 GPS_fail 语义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="GPS_fail:unresolved_paper_semantics",
    )
    add(
        system,
        "GPS_fail",
        "FUNCTION_RETURN",
        "AP_GPS::status()",
        "baseline/ardupilot/libraries/AP_GPS/AP_GPS.h",
        290,
        data_type="AP_GPS_FixType enum",
        truth_condition_zh="若论文把 GPS 故障定义为低于某个定位修复类型，则以 status() 与该最低枚举门限比较。",
        validity_freshness_zh="论文未给出最低 fix type 和持续时间；必须同时检查 GPS 实例与样本新鲜度。",
        confidence="MODELLED",
        confidence_reason_zh="传感器修复状态可精确定位，但 GPS_fail 的论文真值边界未定义。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GPS_RAW_INT.fix_type,time_usec,satellites_visible",
        observation_limit_zh="GPS 修复差不必然使融合位置无效；GPS_RAW_INT 当前发送实例 0，只有单 GPS 或主实例为 0 时才与 status() 一致。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GPS_fail:fix_type_threshold",
    )
    add(
        system,
        "GPS_fail",
        "ASSIGNMENT",
        "AP_GPS::update_instance(): message timeout clears state and sets NONE/NO_GPS",
        "baseline/ardupilot/libraries/AP_GPS/AP_GPS.cpp",
        887,
        source_end_line=905,
        function_context="AP_GPS::update_instance(uint8_t)",
        data_type="GPS state reset and fix-type assignment",
        unit_coordinate="GPS_TIMEOUT_MS uses AP_HAL::millis()",
        truth_condition_zh="当前实现超过 GPS_TIMEOUT_MS 未收到消息时清空该实例状态并设置 NONE 或 NO_GPS。",
        validity_freshness_zh="GPS_TIMEOUT_MS=4000 ms 是当前实现重检测条件，不是 PGFuzz 性质的官方时间要求；多实例分别计时。",
        confidence="EXACT",
        confidence_reason_zh="当前实例超时和状态赋值路径直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GPS_RAW_INT.time_usec,fix_type 到达序列",
        observation_limit_zh="观察端丢包与飞控内部未收到 GPS 不等价，不能只按 GCS 到达间隔复现内部超时。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="GPS_fail:fix_type_threshold",
    )
    add(
        system,
        "GPS_fail",
        "STATE_FIELD",
        "Copter::ap.gps_glitching",
        "baseline/ardupilot/ArduCopter/Copter.h",
        371,
        function_context="Copter::gpsglitch_check()",
        data_type="bool",
        truth_condition_zh="若论文所指是 GPS 异常已影响导航精度，则 ap.gps_glitching==true。",
        validity_freshness_zh="它表示影响导航的 glitch，不是“没有 GPS 消息”的同义词。",
        confidence="MODELLED",
        confidence_reason_zh="当前状态和赋值路径可证，但与论文 GPS_fail 的范围只是语义候选。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="STATUSTEXT.text='GPS Glitch or Compass error' 或 'Glitch cleared'",
        observation_limit_zh="文本事件只在状态转换时发送，且文本同时包含 Compass error，不能作为持续布尔值的精确直接观测。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GPS_fail:gps_glitching",
    )
    add(
        system,
        "GPS_fail",
        "ASSIGNMENT",
        "Copter::gpsglitch_check(): ap.gps_glitching = gps_glitching",
        "baseline/ardupilot/ArduCopter/events.cpp",
        310,
        source_end_line=323,
        function_context="Copter::gpsglitch_check()",
        data_type="bool transition plus log/text event",
        truth_condition_zh="AHRS GPS_GLITCHING 状态变化时更新 Copter 锁存字段并发出开始/清除事件。",
        validity_freshness_zh="文本同时可能描述罗盘问题，只能把内部布尔赋值作为该候选的真值来源。",
        confidence="EXACT",
        confidence_reason_zh="当前赋值和转换事件直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="STATUSTEXT 或 EVENT 转换消息",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="GPS_fail:gps_glitching",
    )
    add(
        system,
        "GPS_count",
        "FUNCTION_RETURN",
        "AP_GPS::num_sats()",
        "baseline/ardupilot/libraries/AP_GPS/AP_GPS.h",
        401,
        data_type="uint8_t",
        unit_coordinate="satellite count",
        truth_condition_zh="读取主 GPS 当前锁定卫星数量。",
        validity_freshness_zh="同时检查 GPS 实例、fix_type 和消息新鲜度。",
        confidence="EXACT",
        confidence_reason_zh="当前访问器直接返回 state[instance].num_sats。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GPS_RAW_INT.satellites_visible,time_usec,fix_type",
        observation_limit_zh="AP_GPS::num_sats() 读取动态主实例，GPS_RAW_INT 当前发送实例 0；单 GPS 或主实例为 0 时才能直接对应。",
    )
    add(
        system,
        "Speed_vertical_t",
        "FUNCTION_RETURN",
        "AP_AHRS::get_velocity_D(float&)",
        "baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h",
        308,
        data_type="float",
        unit_coordinate="m/s NED down-positive",
        truth_condition_zh="下降速度使用 +velD；上升速度使用 -velD，并要求返回 true。",
        validity_freshness_zh="要求速度估计有效；必须按性质阶段选择上升或下降符号。",
        confidence="MODELLED",
        confidence_reason_zh="速度字段明确，但论文没有定义正负方向和目标/实际量。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.vz,time_boot_ms",
        observation_conversion_zh="vz 从厘米/秒除以 100；NED 向下为正。",
        observation_limit_zh="GLOBAL_POSITION_INT.vz 的发送路径读取 get_velocity_NED().z，并在失败时置零；不是 get_velocity_D() 返回通道的无条件直接发送。",
    )
    add(
        system,
        "Parachute",
        "FUNCTION_RETURN",
        "AP_Parachute::released()",
        "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.h",
        60,
        data_type="bool",
        truth_condition_zh="若 Parachute=on 指实际释放状态，则 released()==true。",
        validity_freshness_zh="必须区分 release_initiated、release_in_progress 和 released。",
        confidence="EXACT",
        confidence_reason_zh="当前类分别保存发起、进行中和已释放三个状态。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 没有直接发布 AP_Parachute::_released。",
        candidate_group="Parachute:released_latched",
    )
    add(
        system,
        "Parachute",
        "FUNCTION_RETURN",
        "AP_Parachute::release_initiated()",
        "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.h",
        63,
        data_type="bool",
        truth_condition_zh="若 Parachute=on 指“释放序列已发起”，则 release_initiated()==true。",
        validity_freshness_zh="已发起可能仍在等待抑制引擎等条件，不等于降落伞已物理弹出。",
        confidence="MODELLED",
        confidence_reason_zh="论文只写 Parachute=on，未说是发起还是完成，因此与 released() 并列供人工选择。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 没有等价的 release_initiated 布尔字段。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Parachute:release_initiated_latched",
    )
    add(
        system,
        "Parachute",
        "ASSIGNMENT",
        "AP_Parachute::release(): _release_initiated = true",
        "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp",
        122,
        function_context="AP_Parachute::release()",
        data_type="bool latch",
        truth_condition_zh="调用 release() 且通过前置检查后，锁存“释放已发起”。",
        validity_freshness_zh="发起时刻早于执行器动作，延迟取决于 _delay_ms。",
        confidence="EXACT",
        confidence_reason_zh="当前赋值语句直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="Parachute:release_initiated_latched",
    )
    add(
        system,
        "Parachute",
        "ASSIGNMENT",
        "AP_Parachute::update(): servo release command",
        "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp",
        147,
        function_context="AP_Parachute::update()",
        data_type="servo PWM command",
        truth_condition_zh="释放类型为伺服且延迟满足后，向降落伞功能通道写入释放 PWM。",
        validity_freshness_zh="这是执行器命令，不等于伞具已经物理展开。",
        confidence="EXACT",
        confidence_reason_zh="锚点只声明该行实际执行的伺服命令，不再合并后续继电器和锁存赋值。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="Parachute:released_latched",
    )
    add(
        system,
        "Parachute",
        "ASSIGNMENT",
        "AP_Relay::set(PARACHUTE, true)",
        "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp",
        153,
        function_context="AP_Parachute::update()",
        data_type="relay command",
        truth_condition_zh="释放类型为继电器且实例存在时，向降落伞继电器功能写入 true。",
        validity_freshness_zh="这是继电器执行命令，不等于伞具已经物理展开。",
        confidence="EXACT",
        confidence_reason_zh="当前继电器调用位置直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Parachute:released_latched",
    )
    add(
        system,
        "Parachute",
        "ASSIGNMENT",
        "AP_Parachute::update(): _release_in_progress = true; _released = true",
        "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp",
        157,
        function_context="AP_Parachute::update()",
        data_type="two bool latches",
        truth_condition_zh="执行伺服或继电器分支后，把释放进行中和已释放锁存位置真。",
        validity_freshness_zh="_released 是进程生命周期内锁存的软件状态，仍不能证明物理伞具已经展开。",
        confidence="EXACT",
        confidence_reason_zh="第 157--158 行的两个直接赋值可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Parachute:released_latched",
    )
    add(
        system,
        "Waypoint",
        "UNRESOLVED_ABSTRACTION",
        "no exact current Guided 'waypoint empty' symbol",
        data_type="paper abstraction",
        truth_condition_zh="论文未定义是任务队列为空、Guided 目标不存在还是目标已经完成。",
        validity_freshness_zh="mission count 不能可靠表示 Guided 当前目标是否为空。",
        confidence="UNRESOLVED",
        confidence_reason_zh="当前 Guided 使用子模式、目标字段和更新时间，没有单一等价 empty 标志。",
        mavlink_observability="UNRESOLVED",
        candidate_group="Waypoint:guided_unresolved",
    )
    add(
        system,
        "Waypoint",
        "SEMANTIC_CANDIDATE",
        "AP_Mission::present() / AP_Mission::_cmd_total > 1",
        "baseline/ardupilot/libraries/AP_Mission/AP_Mission.h",
        538,
        data_type="bool derived from uint16 command count",
        truth_condition_zh="若论文 Waypoint=empty 专指任务列表没有 Home 以外命令，则 present()==false。",
        validity_freshness_zh="这只回答任务列表是否有命令，不回答 Guided 模式是否拥有当前目标。",
        confidence="MODELLED",
        confidence_reason_zh="是可定位的“任务空”语义，但不能证明就是论文 Guided/Waypoint 抽象。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="MISSION_COUNT.count",
        observation_conversion_zh="结合当前 mission type 解释 count；注意内部 _cmd_total 计入索引 0 的 Home。",
        observation_limit_zh="MISSION_COUNT 不描述 Guided 当前目标。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Waypoint:mission_list_empty",
    )
    add(
        system,
        "Waypoint",
        "SEMANTIC_CANDIDATE",
        "ModeGuided::guided_mode; ModeGuided::get_wp(Location&)",
        "baseline/ardupilot/ArduCopter/mode_guided.cpp",
        444,
        function_context="ModeGuided::get_wp(Location&) const",
        data_type="Guided SubMode plus bool return",
        truth_condition_zh="某些 Guided 子模式能返回当前位置目标；其他子模式返回 false。",
        validity_freshness_zh="false 可能表示子模式不使用 waypoint，不能统一解释为 Waypoint=empty。",
        confidence="MODELLED",
        confidence_reason_zh="比任务列表更接近 Guided 目标，但仍不是论文抽象的唯一定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="Waypoint:guided_submode_target",
    )
    add(
        system,
        "k",
        "UNRESOLVED_BOUND",
        "no current ArduPilot symbol",
        confidence="UNRESOLVED",
        truth_condition_zh="PGFuzz 论文经验上界或调度余量，当前没有可追溯数值。",
        confidence_reason_zh="论文没有公开该性质的完整测量操作数和数值；不得从循环次数猜秒数。",
        mavlink_observability="UNRESOLVED",
    )

    add_parameter(system, "RTL_ALT", "ModeRTL::altitude_m / RTL_ALT_M", "baseline/ardupilot/ArduCopter/mode_rtl.cpp", 8, data_type="AP_Float", unit="m above Home", relation="RENAMED_AND_SCALED_0.01", version_note="历史 RTL_ALT 厘米值迁移到 RTL_ALT_M 米值。")
    add_parameter(system, "LAND_SPEED_HIGH", "ModeLand::land_speed_high_ms / LAND_SPD_HIGH_MS", "baseline/ardupilot/ArduCopter/mode_land.cpp", 15, data_type="AP_Float", unit="m/s down-rate magnitude", relation="RENAMED_AND_SCALED_0.01", version_note="历史 LAND_SPEED_HIGH 厘米/秒迁移到 LAND_SPD_HIGH_MS 米/秒。")
    add_parameter(system, "LAND_SPEED", "ModeLand::land_speed_ms / LAND_SPD_MS", "baseline/ardupilot/ArduCopter/mode_land.cpp", 6, data_type="AP_Float", unit="m/s down-rate magnitude", relation="RENAMED_AND_SCALED_0.01", version_note="历史 LAND_SPEED 厘米/秒迁移到 LAND_SPD_MS 米/秒。")
    add_parameter(system, "FS_EKF_ACTION", "Parameters::fs_ekf_action / FS_EKF_ACTION", "baseline/ardupilot/ArduCopter/Parameters.cpp", 268, data_type="AP_Int8 enum", unit="action enum", truth_note="读取当前动作枚举；0 仅报告、1 着陆、2 定高、3 全模式着陆。")
    add_parameter(system, "PILOT_SPEED_UP", "ParametersG2::pilot_speed_up_ms / PILOT_SPD_UP", "baseline/ardupilot/ArduCopter/Parameters.cpp", 1142, data_type="AP_Float", unit="m/s up-rate magnitude", relation="RENAMED_AND_SCALED_0.01", version_note="历史 PILOT_SPEED_UP 迁移到 PILOT_SPD_UP。")
    add_parameter(system, "FS_THR_VALUE", "Parameters::failsafe_throttle_value / FS_THR_VALUE", "baseline/ardupilot/ArduCopter/Parameters.cpp", 132, data_type="AP_Int16", unit="raw PWM microseconds", truth_note="读取当前低油门故障保护阈值；实际触发还需启用配置及消抖。")
    add_parameter(system, "CHUTE_ALT_MIN", "AP_Parachute::_alt_min / CHUTE_ALT_MIN", "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp", 52, data_type="AP_Int16", unit="m above Home", truth_note="读取当前最低开伞高度；0 表示禁用高度检查。")


def build_px4_rows() -> None:
    system = "PX4"
    add(
        system,
        "Mode_t",
        "UORB_FIELD",
        "vehicle_status.nav_state",
        "baseline/px4/msg/versioned/VehicleStatus.msg",
        35,
        data_type="uint8 enum",
        truth_condition_zh="读取 Commander 发布的当前实际导航状态 nav_state。",
        validity_freshness_zh="使用 vehicle_status.timestamp 和 nav_state_timestamp；不要用用户意图字段替代当前状态。",
        confidence="EXACT",
        confidence_reason_zh="当前活动模式字段和枚举值有直接消息定义。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.custom_mode",
        observation_conversion_zh="按 px4_custom_mode 的 main_mode/sub_mode 打包表解码。",
        observation_limit_zh="PGFuzz 的小整数 Flight_Mode 不能直接作为当前 packed custom_mode。",
    )
    add(
        system,
        "Mode_t",
        "MAVLINK_ENCODER",
        "get_px4_custom_mode(vehicle_status.nav_state)",
        "baseline/px4/src/modules/commander/px4_custom_mode.h",
        102,
        function_context="get_px4_custom_mode(uint8_t nav_state)",
        data_type="uint32 packed custom_mode",
        truth_condition_zh="把 nav_state 转成 16 位保留、8 位主模式、8 位子模式的 32 位值。",
        confidence="EXACT",
        confidence_reason_zh="当前 HEARTBEAT 发送路径直接调用该转换函数。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.custom_mode",
    )
    modes = {
        "ALTITUDE": ("NAVIGATION_STATE_ALTCTL", 37),
        "POSITION": ("NAVIGATION_STATE_POSCTL", 38),
        "HOLD": ("NAVIGATION_STATE_AUTO_LOITER", 40),
        "RTL": ("NAVIGATION_STATE_AUTO_RTL", 41),
        "LAND": ("NAVIGATION_STATE_AUTO_LAND", 54),
        "ORBIT": ("NAVIGATION_STATE_ORBIT", 57),
    }
    for term, (enum_name, line) in modes.items():
        add(
            system,
            term,
            "ENUM_CONSTANT",
            f"vehicle_status_s::{enum_name}",
            "baseline/px4/msg/versioned/VehicleStatus.msg",
            line,
            data_type="uint8 enum",
            truth_condition_zh=f"Mode_t == {enum_name}。",
            confidence="EXACT",
            confidence_reason_zh="当前 VehicleStatus 导航状态枚举直接定义。",
            mavlink_observability="DIRECT",
            mavlink_message_fields="HEARTBEAT.custom_mode",
            observation_conversion_zh="解码当前 PX4 主/子模式后比较。",
        )

    add(
        system,
        "ALT_t",
        "UORB_FIELD",
        "vehicle_global_position.alt",
        "baseline/px4/msg/versioned/VehicleGlobalPosition.msg",
        15,
        data_type="float32",
        unit_coordinate="m AMSL",
        truth_condition_zh="读取 alt 且 alt_valid=true。",
        validity_freshness_zh="检查 timestamp、timestamp_sample、alt_valid 和 alt_reset_counter。",
        confidence="MODELLED",
        confidence_reason_zh="字段身份精确，但论文 ALT 没有统一说明 AMSL、相对 Home 或局部高度。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.alt,time_boot_ms",
        observation_conversion_zh="alt 从毫米除以 1000 得到 AMSL 米。",
        observation_limit_zh="GLOBAL_POSITION_INT 不携带 gpos.alt_valid 或 alt_reset_counter；外部数值存在不等于估计器样本有效。",
        candidate_group="ALT_t:global_amsl",
    )
    add(
        system,
        "ALT_t",
        "ASSIGNMENT",
        "EKF2::PublishGlobalPosition(): lla.altitude(), alt_valid, alt_reset_counter",
        "baseline/px4/src/modules/ekf2/EKF2.cpp",
        1200,
        source_end_line=1212,
        function_context="EKF2::PublishGlobalPosition(uint64_t)",
        data_type="vehicle_global_position altitude plus validity/reset metadata",
        unit_coordinate="m AMSL",
        truth_condition_zh="由 EKF 的 WGS84 高度形成 alt，并分别发布垂直有效位和重置计数。",
        validity_freshness_zh="判真必须同时订阅 alt_valid、alt_reset_counter、timestamp 和 timestamp_sample。",
        confidence="EXACT",
        confidence_reason_zh="当前 uORB 高度、有效位和重置元数据形成路径直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 GLOBAL_POSITION_INT 只发送数值，不发送这些有效性和重置字段。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="ALT_t:global_amsl",
    )
    add(
        system,
        "ALT_t",
        "MAVLINK_SENDER",
        "MavlinkStreamGlobalPositionInt::send(): msg.alt = gpos.alt * 1000",
        "baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp",
        87,
        function_context="MavlinkStreamGlobalPositionInt::send()",
        data_type="int32 millimetres",
        unit_coordinate="mm AMSL",
        truth_condition_zh="将 gpos.alt 编码到 GLOBAL_POSITION_INT.alt。",
        validity_freshness_zh="发送函数没有把 gpos.alt_valid 和 alt_reset_counter 一同编码。",
        confidence="EXACT",
        confidence_reason_zh="uORB 到 MAVLink 数值编码直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.alt,time_boot_ms",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="ALT_t:global_amsl",
    )
    add(
        system,
        "ALT_t",
        "DERIVED_EXPRESSION",
        "vehicle_global_position.alt - home_position.alt",
        "baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp",
        77,
        data_type="float32",
        unit_coordinate="m above Home",
        truth_condition_zh="当 Home 高度有效时，用全球高度减 Home 高度。",
        validity_freshness_zh="要求 gpos.alt_valid、home.valid_alt 和同一时间基准。",
        confidence="MODELLED",
        confidence_reason_zh="只适用于明确要求相对 Home 高度的公式解释。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="GLOBAL_POSITION_INT.relative_alt,time_boot_ms",
        observation_conversion_zh="relative_alt 从毫米除以 1000。",
        observation_limit_zh="Home 无效时发送器把绝对 AMSL 高度写入 relative_alt；消息还缺少 gpos.alt_valid 和重置计数。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="ALT_t:relative_home",
    )
    add(
        system,
        "ALT_t",
        "DERIVED_EXPRESSION",
        "vehicle_global_position.alt - selected RTL destination altitude",
        "baseline/px4/src/modules/navigator/rtl.cpp",
        477,
        source_end_line=530,
        function_context="RTL::findRtlDestination(); RTL::calculate_return_alt_from_cone_half_angle()",
        data_type="float derived from current AMSL and selected destination AMSL",
        unit_coordinate="m above Home, safe point, or mission landing destination",
        truth_condition_zh="RTL_RETURN_ALT 的参考面是当前选定目的地，不一定是 Home；用当前 AMSL 减该目的地 AMSL 才能与参数比较。",
        validity_freshness_zh="必须保存本次 RTL 选择的 destination type、目的地高度、锥角分支和同一有效全球高度样本。",
        confidence="MODELLED",
        confidence_reason_zh="当前参数文档和目的地选择源码直接证明参考面，但论文 ALT_t 没有公开此迁移定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="HOME_POSITION 不会发布 safe point 或 mission landing destination；需要内部订阅/插桩。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="ALT_t:relative_rtl_destination",
    )
    add(
        system,
        "ALT_t",
        "DERIVED_EXPRESSION",
        "vehicle_global_position.alt - takeoff-reference altitude captured at command/activation",
        "baseline/px4/src/modules/navigator/takeoff.cpp",
        188,
        source_end_line=199,
        function_context="Takeoff::set_takeoff_position()",
        data_type="trace-derived float",
        unit_coordinate="m above takeoff reference",
        truth_condition_zh="默认起飞目标由当前 AMSL 加 MIS_TAKEOFF_ALT 形成；监视时应在同一起飞实例捕获参考高度后计算相对高度。",
        validity_freshness_zh="必须关联同一 TAKEOFF 命令/模式实例；若命令已提供绝对目标高度，则默认参数路径不适用。",
        confidence="MODELLED",
        confidence_reason_zh="当前默认目标形成路径可证，但监视参考高度需要事件关联。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="GLOBAL_POSITION_INT.alt,time_boot_ms; COMMAND_LONG/COMMAND_INT 起飞事件",
        observation_limit_zh="需要保存起飞实例起点；不能直接把 AMSL 数值与相对高度参数比较。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="ALT_t:relative_takeoff_reference",
    )
    add(
        system,
        "ALT_t",
        "DERIVED_EXPRESSION",
        "-vehicle_local_position.z",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        17,
        data_type="float32",
        unit_coordinate="m above local NED origin",
        truth_condition_zh="若性质只要求局部高度变化，则由 NED 坐标向下为正的 z 取负得到向上高度。",
        validity_freshness_zh="要求 z_valid=true，timestamp 新鲜且 z_reset_counter 未变；局部原点不等于 Home 或海拔零点。",
        confidence="MODELLED",
        confidence_reason_zh="字段与符号换算精确，但论文 ALT_t 没有固定高度参考面。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="LOCAL_POSITION_NED.z,time_boot_ms",
        observation_conversion_zh="将 z 取负，并拒绝跨 z_reset_counter 的比较。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="ALT_t:local_ned",
    )
    add(
        system,
        "ALT_t",
        "UORB_FIELD",
        "vehicle_local_position.dist_bottom",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        61,
        data_type="float32",
        unit_coordinate="m distance above bottom/ground surface",
        truth_condition_zh="若 LAND 性质中 ALT_t 实际指离地高度，则读取 dist_bottom。",
        validity_freshness_zh="要求 dist_bottom_valid=true，timestamp 新鲜且 dist_bottom_reset_counter 未变；传感器来源由 bitfield 说明。",
        confidence="MODELLED",
        confidence_reason_zh="当前有明确离地距离字段，但论文 ALT_t 没有说明此处是融合高度还是离地高度。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="DISTANCE_SENSOR.current_distance,time_boot_ms 或 ALTITUDE.altitude_bottom,time_usec",
        observation_conversion_zh="DISTANCE_SENSOR.current_distance 从厘米除以 100；ALTITUDE.altitude_bottom 已为米。",
        observation_limit_zh="消息只在距离/地形估计有效且对应流已启用时可用。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="ALT_t:distance_to_ground",
    )
    for group, base, path, line, unit, messages, role in [
        ("ALT_t-1:global_amsl", "vehicle_global_position.alt", "baseline/px4/msg/versioned/VehicleGlobalPosition.msg", 15, "m AMSL", "GLOBAL_POSITION_INT.alt,time_boot_ms", "PRIMARY_VALUE"),
        ("ALT_t-1:relative_home", "vehicle_global_position.alt-home_position.alt", "baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp", 77, "m above Home", "GLOBAL_POSITION_INT.relative_alt,time_boot_ms", "ALTERNATIVE_SEMANTICS"),
        ("ALT_t-1:local_ned", "-vehicle_local_position.z", "baseline/px4/msg/versioned/VehicleLocalPosition.msg", 17, "m above local NED origin", "LOCAL_POSITION_NED.z,time_boot_ms", "ALTERNATIVE_SEMANTICS"),
        ("ALT_t-1:distance_to_ground", "vehicle_local_position.dist_bottom", "baseline/px4/msg/versioned/VehicleLocalPosition.msg", 61, "m distance to ground", "DISTANCE_SENSOR.current_distance 或 ALTITUDE.altitude_bottom", "ALTERNATIVE_SEMANTICS"),
        ("ALT_t-1:relative_rtl_destination", "current AMSL-selected RTL destination AMSL", "baseline/px4/src/modules/navigator/rtl.cpp", 477, "m above selected RTL destination", "内部目的地加 GLOBAL_POSITION_INT.alt", "ALTERNATIVE_SEMANTICS"),
        ("ALT_t-1:relative_takeoff_reference", "current AMSL-captured takeoff reference AMSL", "baseline/px4/src/modules/navigator/takeoff.cpp", 188, "m above takeoff reference", "轨迹捕获加 GLOBAL_POSITION_INT.alt", "ALTERNATIVE_SEMANTICS"),
    ]:
        add_previous(
            system,
            "ALT_t-1",
            base,
            path,
            line,
            data_type="float32 or trace-derived float",
            unit=unit,
            messages=messages,
            note="前后样本必须使用与当前 ALT_t 相同的候选组、参考面和运行实例，并拒绝跨高度重置的比较。",
            candidate_group=group,
            binding_role=role,
        )
    add(
        system,
        "Pos_t",
        "UORB_FIELD",
        "vehicle_global_position.lat,lon",
        "baseline/px4/msg/versioned/VehicleGlobalPosition.msg",
        13,
        data_type="float64 tuple",
        unit_coordinate="degrees WGS84",
        truth_condition_zh="读取 lat/lon 且 lat_lon_valid=true。",
        validity_freshness_zh="检查 timestamp、lat_lon_valid 和 lat_lon_reset_counter。",
        confidence="MODELLED",
        confidence_reason_zh="字段精确；论文位置严格相等需要距离容差和重置处理。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="GLOBAL_POSITION_INT.lat,lon,time_boot_ms",
        observation_conversion_zh="经纬度除以 1e7；比较时换算为地表距离。",
        candidate_group="Pos_t:global_wgs84",
    )
    add(
        system,
        "Pos_t",
        "UORB_FIELD",
        "vehicle_local_position.x,y",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        15,
        data_type="float32 tuple",
        unit_coordinate="m local NED",
        truth_condition_zh="读取 x/y 且 xy_valid=true。",
        validity_freshness_zh="前后比较必须保持同一局部原点且 xy_reset_counter 不变。",
        confidence="MODELLED",
        confidence_reason_zh="可用于局部位移，但局部原点不等于 Home。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="LOCAL_POSITION_NED.x,y,time_boot_ms",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Pos_t:local_ned",
    )
    for group, base, path, line, unit, messages, role in [
        ("Pos_t-1:global_wgs84", "vehicle_global_position.lat,lon", "baseline/px4/msg/versioned/VehicleGlobalPosition.msg", 13, "WGS84 degrees", "GLOBAL_POSITION_INT.lat,lon,time_boot_ms", "PRIMARY_VALUE"),
        ("Pos_t-1:local_ned", "vehicle_local_position.x,y", "baseline/px4/msg/versioned/VehicleLocalPosition.msg", 15, "m local NED", "LOCAL_POSITION_NED.x,y,time_boot_ms", "ALTERNATIVE_SEMANTICS"),
    ]:
        add_previous(
            system,
            "Pos_t-1",
            base,
            path,
            line,
            data_type="position tuple",
            unit=unit,
            messages=messages,
            note="必须与当前 Pos_t 使用同一候选组；拒绝跨 xy/lat_lon reset counter 的样本。",
            candidate_group=group,
            binding_role=role,
        )
    add(
        system,
        "home_position",
        "UORB_FIELD",
        "home_position.lat,lon",
        "baseline/px4/msg/versioned/HomePosition.msg",
        7,
        data_type="float64 tuple",
        unit_coordinate="degrees WGS84",
        truth_condition_zh="读取 Home 经纬度且 valid_hpos=true。",
        validity_freshness_zh="检查 timestamp、valid_hpos 和 update_count。",
        confidence="EXACT",
        confidence_reason_zh="Home 字段与 MAVLink HOME_POSITION 发送路径直接对应。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HOME_POSITION.latitude,longitude,time_usec",
        observation_conversion_zh="纬经度除以 1e7；Home 并非所有 RTL 配置下唯一目的地。",
    )
    add(
        system,
        "GroundALT",
        "UNRESOLVED_ABSTRACTION",
        "no type-compatible numeric GroundALT definition",
        data_type="undefined paper abstraction",
        truth_condition_zh="论文没有给 GroundALT 的数值类型、参考面或容差，不能把 vehicle_land_detected.landed 布尔量代入高度等式。",
        validity_freshness_zh="补充数值地面参考定义或明确改写为 landed 布尔性质前不判真。",
        confidence="UNRESOLVED",
        confidence_reason_zh="当前 landed、Home AMSL 和 terrain AMSL 是互斥候选，均未被论文确认。",
        mavlink_observability="UNRESOLVED",
        candidate_group="GroundALT:untyped_unresolved",
    )
    add(
        system,
        "GroundALT",
        "UORB_FIELD",
        "vehicle_land_detected.landed",
        "baseline/px4/msg/versioned/VehicleLandDetected.msg",
        8,
        data_type="bool",
        truth_condition_zh="若真实含义是触地，使用 landed==true 作为语义代理。",
        validity_freshness_zh="这是触地检测，不是数值高度。",
        confidence="MODELLED",
        confidence_reason_zh="论文 GroundALT 未定义；触地状态比高度严格等式更接近自然语言。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="EXTENDED_SYS_STATE.landed_state",
        observation_conversion_zh="判断 MAV_LANDED_STATE_ON_GROUND。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GroundALT:landed_state",
    )
    add(
        system,
        "GroundALT",
        "UORB_FIELD",
        "home_position.alt",
        "baseline/px4/msg/versioned/HomePosition.msg",
        9,
        data_type="float32",
        unit_coordinate="m AMSL",
        truth_condition_zh="若论文把 GroundALT 简化为 Home 点地面海拔，则读取 home_position.alt。",
        validity_freshness_zh="要求 valid_alt=true；Home 地面海拔不等于飞行器当前下方地形高度。",
        confidence="MODELLED",
        confidence_reason_zh="字段身份精确，但 GroundALT 的论文定义缺失，只能作为一种有条件的参考面解释。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HOME_POSITION.altitude,time_usec",
        observation_conversion_zh="altitude 从毫米除以 1000 得到 AMSL 米。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GroundALT:home_amsl",
    )
    add(
        system,
        "GroundALT",
        "UORB_FIELD",
        "vehicle_global_position.terrain_alt",
        "baseline/px4/msg/versioned/VehicleGlobalPosition.msg",
        30,
        data_type="float32",
        unit_coordinate="m WGS84 terrain altitude",
        truth_condition_zh="只有 terrain_alt_valid=true 时才可解释为飞行器下方地形高度。",
        confidence="UNRESOLVED",
        confidence_reason_zh="论文没有说明 GroundALT 是否是地形高度，标准消息也不直接携带该字段。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="GroundALT:terrain_amsl",
    )

    add(
        system,
        "Yaw_t",
        "UORB_FIELD",
        "vehicle_local_position.heading",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        42,
        data_type="float32",
        unit_coordinate="radians in NED tangent plane",
        truth_condition_zh="读取 heading，并要求 heading_good_for_control。",
        validity_freshness_zh="检查 timestamp 和 heading_reset_counter；使用环形角差。",
        confidence="EXACT",
        confidence_reason_zh="当前航向字段和 MAVLink 编码直接对应；它不是 yawspeed。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="GLOBAL_POSITION_INT.hdg,time_boot_ms",
        observation_conversion_zh="hdg 从百分之一度转为角度/弧度并处理 0/360 环绕。",
    )
    add_previous(
        system,
        "Yaw_t-1",
        "vehicle_local_position.heading",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        42,
        data_type="float32",
        unit="radians",
        messages="GLOBAL_POSITION_INT.hdg,time_boot_ms",
        note="只接受 heading_reset_counter 未变化的有序有效样本，并用环形角差。",
    )
    add(
        system,
        "Speed_vertical_t",
        "UORB_FIELD",
        "vehicle_local_position.vz",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        28,
        data_type="float32",
        unit_coordinate="m/s NED down-positive",
        truth_condition_zh="着陆下降速率取 +vz；起飞上升速率取 -vz；要求 v_z_valid。",
        validity_freshness_zh="检查 timestamp、v_z_valid 和 vz_reset_counter。",
        confidence="MODELLED",
        confidence_reason_zh="字段身份精确，但论文没有统一速度方向且参数是约束/目标而非实际值保证。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="GLOBAL_POSITION_INT.vz,time_boot_ms",
        observation_conversion_zh="MAVLink vz 从厘米/秒除以 100；上升时再取负号。",
    )

    add(
        system,
        "Circle_radius_t",
        "CLASS_MEMBER",
        "FlightTaskOrbit::_orbit_radius",
        "baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp",
        119,
        data_type="float",
        unit_coordinate="m target radius",
        truth_condition_zh="读取内部无符号目标半径。",
        validity_freshness_zh="只在当前 ORBIT 任务实例激活时有效。",
        confidence="EXACT",
        confidence_reason_zh="当前 Orbit 类成员直接定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="Circle_radius_t:target_radius",
    )
    add(
        system,
        "Circle_radius_t",
        "DERIVED_EXPRESSION",
        "fabs(orbit_status.radius)",
        "baseline/px4/msg/OrbitStatus.msg",
        10,
        data_type="float32",
        unit_coordinate="m",
        truth_condition_zh="取发布的带符号半径绝对值。",
        validity_freshness_zh="按 orbit_status.timestamp/ORBIT_EXECUTION_STATUS.time_usec 检查新鲜度。",
        confidence="EXACT",
        confidence_reason_zh="发送端明确用速度符号乘内部半径。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="ORBIT_EXECUTION_STATUS.radius,time_usec",
        observation_conversion_zh="半径取绝对值；符号另用于旋转方向。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Circle_radius_t:target_radius",
    )
    add_previous(
        system,
        "Circle_radius_t-1",
        "fabs(orbit_status.radius)",
        "baseline/px4/msg/OrbitStatus.msg",
        10,
        data_type="float32",
        unit="m",
        messages="ORBIT_EXECUTION_STATUS.radius,time_usec",
        note="只接受同一 ORBIT 实例且发送时间递增的样本。",
    )
    add(
        system,
        "Circle_direction_t",
        "DERIVED_EXPRESSION",
        "sign(orbit_status.radius)",
        "baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp",
        138,
        data_type="bool derived from float sign",
        truth_condition_zh="radius>0 表示顺时针，radius<0 表示逆时针。",
        validity_freshness_zh="消息必须属于当前 ORBIT 实例；发布端 signNoZero 在 _orbit_velocity==0 时仍编码正半径，因此正号只是目标/编码方向，不证明正在运动。",
        confidence="MODELLED",
        confidence_reason_zh="发布代码精确编码目标方向，但论文没有证明 direction 指目标编码而非实际运动方向。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="ORBIT_EXECUTION_STATUS.radius",
        candidate_group="Circle_direction_t:target_encoded_direction",
    )
    add(
        system,
        "Circle_direction_t",
        "DERIVED_EXPRESSION",
        "sign(FlightTaskOrbit::_orbit_velocity)",
        "baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp",
        118,
        data_type="direction derived from float sign",
        unit_coordinate="signed target tangential velocity",
        truth_condition_zh="内部目标圆周速度的符号决定旋转方向，并在发布 orbit_status.radius 时编码到半径符号。",
        validity_freshness_zh="只在当前 ORBIT 任务实例激活且 _orbit_velocity 非零时有方向意义。",
        confidence="EXACT",
        confidence_reason_zh="内部方向来源与对外带符号半径的编码路径直接可证。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="直接读内部成员需要插桩；对外可优先使用上一行 ORBIT_EXECUTION_STATUS.radius 的符号。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Circle_direction_t:target_encoded_direction",
    )
    add(
        system,
        "Circle_direction_t",
        "ASSIGNMENT",
        "FlightTaskOrbit::applyCommandParameters(): command.param1 sign -> _orbit_velocity",
        "baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp",
        68,
        function_context="FlightTaskOrbit::applyCommandParameters(const vehicle_command_s&, bool&)",
        data_type="signed float target velocity",
        unit_coordinate="param1 radius sign plus param2 m/s speed",
        truth_condition_zh="ORBIT 命令 param1 的符号选方向，param2 提供速度大小，最后写入带符号 _orbit_velocity。",
        validity_freshness_zh="参数必须为有限数并通过半径范围检查。",
        confidence="EXACT",
        confidence_reason_zh="命令参数到内部目标的赋值路径直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_LONG.command=MAV_CMD_DO_ORBIT,param1,param2; COMMAND_ACK",
        observation_limit_zh="发送值不等于飞控已接受，需关联 ACK 和后续 ORBIT_EXECUTION_STATUS。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Circle_direction_t:target_encoded_direction",
    )
    add(
        system,
        "Circle_direction_t",
        "MAVLINK_SENDER",
        "MavlinkStreamOrbitStatus::send()",
        "baseline/px4/src/modules/mavlink/streams/ORBIT_EXECUTION_STATUS.hpp",
        70,
        function_context="MavlinkStreamOrbitStatus::send()",
        data_type="signed radius encoder",
        truth_condition_zh="将 orbit_status.radius 保持符号发送为 ORBIT_EXECUTION_STATUS.radius。",
        validity_freshness_zh="按 orbit_status.timestamp 关联当前 ORBIT 实例。",
        confidence="EXACT",
        confidence_reason_zh="uORB 字段到 MAVLink 字段的编码直接可证。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="ORBIT_EXECUTION_STATUS.radius,time_usec",
        candidate_group="Circle_direction_t:target_encoded_direction",
    )
    add(
        system,
        "Circle_direction_t",
        "DERIVED_EXPRESSION",
        "sign(cross_2d(position - orbit_center, horizontal_velocity))",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        26,
        data_type="direction derived from position, center and velocity",
        unit_coordinate="one common local tangent frame",
        truth_condition_zh="若性质指实际飞行方向，则把位置到圆心的径向向量与水平速度做二维叉积，由符号判断旋转方向。",
        validity_freshness_zh="圆心、位置和速度必须转到同一坐标系，且速度大小高于有来源的噪声门限；论文未给门限。",
        confidence="MODELLED",
        confidence_reason_zh="这是实际运动方向的可观测派生定义，但论文不明确要目标还是实际方向。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="ORBIT_EXECUTION_STATUS.x,y; GLOBAL_POSITION_INT.lat,lon,vx,vy,time_boot_ms",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Circle_direction_t:actual_motion_direction",
    )
    add(
        system,
        "Circle_speed_t",
        "CLASS_MEMBER",
        "fabs(FlightTaskOrbit::_orbit_velocity)",
        "baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp",
        118,
        data_type="float",
        unit_coordinate="m/s target tangential speed magnitude",
        truth_condition_zh="若论文 speed 指内部目标圆周速度，则取 _orbit_velocity 绝对值。",
        validity_freshness_zh="只在 ORBIT 激活时有效，并保留方向符号供 direction 命题使用。",
        confidence="MODELLED",
        confidence_reason_zh="论文未区分目标速度和实际水平地速。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        candidate_group="Circle_speed_t:target_tangential_speed",
    )
    add(
        system,
        "Circle_speed_t",
        "DERIVED_EXPRESSION",
        "hypot(vehicle_local_position.vx, vehicle_local_position.vy)",
        "baseline/px4/msg/versioned/VehicleLocalPosition.msg",
        26,
        data_type="float32",
        unit_coordinate="m/s actual horizontal ground speed",
        truth_condition_zh="若论文指实际速度，则由 vx、vy 计算水平速度大小。",
        validity_freshness_zh="要求 v_xy_valid 且前后样本未跨速度重置。",
        confidence="MODELLED",
        confidence_reason_zh="实际速度可派生，但不等于内部目标 _orbit_velocity。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="GLOBAL_POSITION_INT.vx,vy,time_boot_ms",
        observation_conversion_zh="vx、vy 从厘米/秒除以 100 后计算平方和开方。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Circle_speed_t:actual_ground_speed",
    )
    for group, base, path, line, messages, role in [
        ("Circle_speed_t-1:target_tangential_speed", "fabs(FlightTaskOrbit::_orbit_velocity)", "baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp", 118, "内部插桩", "PRIMARY_VALUE"),
        ("Circle_speed_t-1:actual_ground_speed", "hypot(vehicle_local_position.vx,vehicle_local_position.vy)", "baseline/px4/msg/versioned/VehicleLocalPosition.msg", 26, "GLOBAL_POSITION_INT.vx,vy,time_boot_ms", "ALTERNATIVE_SEMANTICS"),
    ]:
        add_previous(
            system,
            "Circle_speed_t-1",
            base,
            path,
            line,
            data_type="float",
            unit="m/s",
            messages=messages,
            note="前后必须与当前 Circle_speed_t 使用同一候选组；不能混用目标速度和实际地速。",
            candidate_group=group,
            binding_role=role,
        )

    for term, field, line, raw_line, label in [
        ("RC_pitch", "pitch", 27, 195, "俯仰"),
        ("RC_roll", "roll", 26, 194, "横滚"),
        ("Throttle_t", "throttle", 29, 193, "油门"),
    ]:
        add(
            system,
            term,
            "UORB_FIELD",
            f"manual_control_setpoint.{field}",
            "baseline/px4/msg/versioned/ManualControlSetpoint.msg",
            line,
            data_type="float32 normalized [-1,1]",
            truth_condition_zh=f"读取有效的标准化{label}输入。",
            validity_freshness_zh="要求 valid=true、timestamp 新鲜，并保留 data_source。",
            confidence="MODELLED",
            confidence_reason_zh="当前控制使用标准化输入；论文 1500 是原始 PWM，二者需校准映射。",
            mavlink_observability="DIRECT",
            mavlink_message_fields="MANUAL_CONTROL 对应轴字段",
            observation_conversion_zh="不要把标准化零值直接写成原始 PWM 1500。",
            binding_role="ALTERNATIVE_SEMANTICS",
            candidate_group=f"{term}:normalized_manual_control",
        )
        add(
            system,
            term,
            "DERIVED_EXPRESSION",
            f"input_rc.values[RC_MAP_{field.upper()}-1]",
            "baseline/px4/src/modules/rc_update/rc_update.cpp",
            440,
            function_context="RCUpdate::Run() raw-channel scaling loop",
            data_type="uint16 raw PWM",
            unit_coordinate="microseconds/PWM",
            truth_condition_zh=f"论文与 1500 比较时使用当前 RC_MAP 选择的原始{label}通道。",
            validity_freshness_zh="RC_MAP 必须有效；检查 rc_lost、rc_failsafe、timestamp_last_signal。",
            confidence="MODELLED",
            confidence_reason_zh="原始值可定位，但物理通道号、反向、校准和死区均为配置。",
            mavlink_observability="CONDITIONAL",
            mavlink_message_fields="RC_CHANNELS.chanN_raw,time_boot_ms",
            observation_conversion_zh="N 由当前 RC_MAP 参数决定，不能固定假设 chan1/2/3。",
            candidate_group=f"{term}:raw_pwm",
        )
        add(
            system,
            term,
            "ASSIGNMENT",
            f"RCUpdate::_rc.function[FUNCTION_{field.upper()}] = RC_MAP_{field.upper()} - 1",
            "baseline/px4/src/modules/rc_update/rc_update.cpp",
            raw_line,
            function_context="RCUpdate::update_rc_functions()",
            data_type="int8 channel-index mapping",
            truth_condition_zh=f"当前 RC_MAP_{field.upper()} 参数减一得到{label}功能对应的 values[] 索引。",
            validity_freshness_zh="参数值必须在有效通道范围内，并与当前 channel_count 联合检查。",
            confidence="EXACT",
            confidence_reason_zh="通道功能到原始数组索引的赋值直接可证。",
            mavlink_observability="DIRECT",
            mavlink_message_fields=f"PARAM_VALUE.param_id=RC_MAP_{field.upper()},param_value",
            binding_role="SUPPORTING_EVIDENCE",
            candidate_group=f"{term}:raw_pwm",
        )

    add(
        system,
        ("RC_pitch", "RC_roll", "Throttle_t"),
        "ASSOCIATED_FIELD",
        "manual_control_setpoint.data_source == SOURCE_RC",
        "baseline/px4/msg/versioned/ManualControlSetpoint.msg",
        8,
        source_end_line=17,
        data_type="uint8 source enum and field",
        truth_condition_zh="只有 data_source==SOURCE_RC 时，标准化轴值才代表物理 RC，而不是 MAVLink 手动控制源。",
        validity_freshness_zh="与同一条 manual_control_setpoint 的 valid、timestamp_sample 和轴字段配对。",
        confidence="EXACT",
        confidence_reason_zh="SOURCE_RC 枚举和 data_source 字段在当前消息定义中直接给出。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MANUAL_CONTROL 消息不回传 PX4 内部 data_source 字段。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="{term}:normalized_manual_control",
    )

    add(
        system,
        "RC_t",
        "UORB_FIELD",
        "failsafe_flags.manual_control_signal_lost",
        "baseline/px4/msg/FailsafeFlags.msg",
        39,
        data_type="bool",
        truth_condition_zh="RC_t=off 当且仅当该标志为 true；RC_t=on 当且仅当为 false。",
        validity_freshness_zh="当前检查还依赖 manual_control_setpoint.valid、时间戳和 COM_RC_LOSS_T；若要表示物理 RC，还要求 data_source==SOURCE_RC。",
        confidence="EXACT",
        confidence_reason_zh="当前 failsafe 状态机使用的手动控制丢失字段直接定义。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="HIGH_LATENCY2.failure_flags & HL_FAILURE_FLAG_RC_RECEIVER",
        observation_limit_zh="只有 HIGH_LATENCY2 流已启用时才能读取；该位编码 manual_control_signal_lost，不证明丢失的一定是物理 RC。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="RC_t:manual_control_availability",
    )
    add(
        system,
        "RC_t",
        "ASSIGNMENT",
        "manual_control_setpoint.valid && age <= COM_RC_LOSS_T",
        "baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp",
        48,
        function_context="RcAndDataLinkChecks::checkAndReport()",
        data_type="derived bool",
        truth_condition_zh="有效且未超过实际 COM_RC_LOSS_T 时视为 RC 可用。",
        validity_freshness_zh="必须读取当前参数值和飞控单调时间，不能用观察端固定超时替代。",
        confidence="EXACT",
        confidence_reason_zh="当前赋值条件直接定义 manual_control_signal_lost。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="MANUAL_CONTROL或RC_CHANNELS到达序列，加 PARAM_VALUE(COM_RC_LOSS_T)",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="RC_t:manual_control_availability",
    )
    add(
        system,
        "RC_t",
        "MAVLINK_SENDER",
        "HIGH_LATENCY2.failure_flags |= HL_FAILURE_FLAG_RC_RECEIVER",
        "baseline/px4/src/modules/mavlink/streams/HIGH_LATENCY2.hpp",
        484,
        function_context="MavlinkStreamHighLatency2::write_failsafe_flags()",
        data_type="uint16 failure bitmask",
        truth_condition_zh="manual_control_signal_lost 为真时，把 RC_RECEIVER 故障位写入 HIGH_LATENCY2.failure_flags。",
        validity_freshness_zh="只有 HIGH_LATENCY2 流已发送且消息新鲜时可用。",
        confidence="EXACT",
        confidence_reason_zh="uORB failsafe 字段到 MAVLink 位的编码直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="HIGH_LATENCY2.failure_flags & HL_FAILURE_FLAG_RC_RECEIVER",
        observation_limit_zh="位名为 RC_RECEIVER，但源状态是更广义的 manual_control_signal_lost。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="RC_t:manual_control_availability",
    )
    add(
        system,
        "RC_t",
        "SEMANTIC_CANDIDATE",
        "!(input_rc.rc_lost || input_rc.rc_failsafe)",
        "baseline/px4/msg/InputRc.msg",
        29,
        data_type="bool derived from receiver flags",
        truth_condition_zh="若 RC_t 只指底层接收器链路，则 rc_lost 和 rc_failsafe 均为 false 时候选为 on。",
        validity_freshness_zh="同时检查 timestamp_last_signal 与 input_source；部分接收器在链路丢失后仍发帧，因此两个标志都可能不完整。",
        confidence="MODELLED",
        confidence_reason_zh="底层链路字段直接可证，但当前 failsafe 真正使用的是上层 manual_control_signal_lost。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="RC_CHANNELS.time_boot_ms,rssi,chanN_raw",
        observation_limit_zh="标准 RC_CHANNELS 没有完全等价发布 rc_lost 和 rc_failsafe 布尔位。",
        binding_role="PRIMARY_VALUE",
        candidate_group="RC_t:physical_receiver",
    )
    add(
        system,
        "RC_t",
        "ASSOCIATED_FIELD",
        "input_rc.timestamp_last_signal",
        "baseline/px4/msg/InputRc.msg",
        22,
        data_type="uint64 boot-time timestamp",
        unit_coordinate="microseconds since system start",
        truth_condition_zh="物理接收器候选必须确认最后一次有效信号时间仍新鲜。",
        validity_freshness_zh="阈值必须来自当前接收器/检查逻辑，不能用观察端任意秒数。",
        confidence="EXACT",
        confidence_reason_zh="当前消息直接定义最后有效接收时刻。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="RC_t:physical_receiver",
    )
    add(
        system,
        "RC_t",
        "ASSOCIATED_FIELD",
        "input_rc.input_source",
        "baseline/px4/msg/InputRc.msg",
        36,
        data_type="uint8 RC_INPUT_SOURCE enum",
        truth_condition_zh="确认 input_rc 来自哪一种物理接收器或 MAVLink 输入源。",
        validity_freshness_zh="物理 RC 解释需要排除 RC_INPUT_SOURCE_MAVLINK 等非接收器来源。",
        confidence="EXACT",
        confidence_reason_zh="输入来源字段和枚举直接定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="RC_t:physical_receiver",
    )
    add(
        system,
        "RC_t",
        "ASSOCIATED_FIELD",
        "input_rc.rc_lost",
        "baseline/px4/msg/InputRc.msg",
        30,
        data_type="bool receiver frame-loss state",
        truth_condition_zh="物理 RC 候选还要求 rc_lost==false；该位表示预期时间内未收到帧。",
        validity_freshness_zh="与 rc_failsafe、timestamp_last_signal 和 input_source 联合判定。",
        confidence="MODELLED",
        confidence_reason_zh="是物理接收器连接的直接字段，但不等于上层手动控制可用性。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="RC_CHANNELS 到达序列与 timestamp",
        observation_limit_zh="RC_CHANNELS 不直接携带 rc_lost 位。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="RC_t:physical_receiver",
    )

    add(
        system,
        "Disarm",
        "UORB_FIELD",
        "vehicle_status.arming_state == ARMING_STATE_DISARMED",
        "baseline/px4/msg/versioned/VehicleStatus.msg",
        10,
        data_type="uint8 enum comparison",
        truth_condition_zh="arming_state 等于 ARMING_STATE_DISARMED。",
        confidence="EXACT",
        confidence_reason_zh="状态及枚举常量在同一当前消息定义。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.base_mode",
        observation_conversion_zh="MAV_MODE_FLAG_SAFETY_ARMED 位不存在。",
        candidate_group="Disarm:vehicle_arming_state",
    )
    add(
        system,
        "Disarm",
        "ENUM_CONSTANT",
        "vehicle_status_s::ARMING_STATE_DISARMED",
        "baseline/px4/msg/versioned/VehicleStatus.msg",
        11,
        data_type="uint8 value 1",
        truth_condition_zh="Disarm 的主状态比较值为 ARMING_STATE_DISARMED。",
        confidence="EXACT",
        confidence_reason_zh="枚举常量在当前消息定义中直接给出。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.base_mode",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Disarm:vehicle_arming_state",
    )
    add(
        system,
        "Disarm",
        "UORB_FIELD",
        "actuator_armed.armed == false",
        "baseline/px4/msg/ActuatorArmed.msg",
        3,
        data_type="bool",
        truth_condition_zh="执行器武装字段为 false。",
        confidence="EXACT",
        confidence_reason_zh="直接电机/执行器武装状态字段。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.base_mode",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Disarm:vehicle_arming_state",
    )

    add(
        system,
        "Command_t",
        "UORB_FIELD",
        "vehicle_command.command",
        "baseline/px4/msg/versioned/VehicleCommand.msg",
        190,
        data_type="uint32 command ID",
        truth_condition_zh="读取当前 vehicle_command.command，并保存 timestamp、source_system 和 source_component。",
        validity_freshness_zh="收到命令不等于接受或执行；应关联 COMMAND_ACK 或后续模式状态。",
        confidence="MODELLED",
        confidence_reason_zh="命令字段身份精确，但论文 Command_t 没有说明是收到、接受还是开始执行；当前主组选择输入事件。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_LONG.command 或 COMMAND_INT.command",
        candidate_group="Command_t:input_event",
    )
    add(
        system,
        "Command_t",
        "ASSOCIATED_FIELD",
        "vehicle_command.param1..param7,source_system,source_component",
        "baseline/px4/msg/versioned/VehicleCommand.msg",
        183,
        source_end_line=196,
        data_type="command envelope fields",
        truth_condition_zh="对 Command_t 的完整关联需保留 param1–7 和发送端身份；特别是 NAV_TAKEOFF 的 param7 携带绝对目标高度。",
        validity_freshness_zh="该行是命令上下文，不是 command ID 本身；必须与同一 timestamp 和 source 关联。",
        confidence="EXACT",
        confidence_reason_zh="字段结构与类型在当前 vehicle_command 消息中直接定义。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_LONG.param1–param7,target_system,target_component 或 COMMAND_INT.x,y,z",
        observation_limit_zh="发出命令只证明输入；是否接受需另外关联 COMMAND_ACK。",
        candidate_group="Command_t:input_event",
    )
    add(
        system,
        "Command_t",
        "ASSIGNMENT",
        "MavlinkReceiver::handle_message_command_long(): COMMAND_LONG -> vehicle_command",
        "baseline/px4/src/modules/mavlink/mavlink_receiver.cpp",
        484,
        source_end_line=500,
        function_context="MavlinkReceiver::handle_message_command_long(mavlink_message_t*)",
        data_type="MAVLink command envelope to vehicle_command_s",
        truth_condition_zh="把外部 COMMAND_LONG 的 command、param1–7 和来源身份复制到 vehicle_command，再交给公共处理函数。",
        validity_freshness_zh="保留 from_external、source_system、source_component 和 timestamp；无效参数会在此前拒绝。",
        confidence="EXACT",
        confidence_reason_zh="COMMAND_LONG 的独立复制路径直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_LONG 输入记录",
        observation_limit_zh="这只是输入形成，不是接受或执行。",
        candidate_group="Command_t:input_event",
    )
    add(
        system,
        "Command_t",
        "ASSIGNMENT",
        "MavlinkReceiver::handle_message_command_int(): COMMAND_INT -> vehicle_command",
        "baseline/px4/src/modules/mavlink/mavlink_receiver.cpp",
        520,
        source_end_line=545,
        function_context="MavlinkReceiver::handle_message_command_int(mavlink_message_t*)",
        data_type="MAVLink command envelope to vehicle_command_s",
        truth_condition_zh="把 COMMAND_INT 参数、缩放后的 x/y、z、命令身份和来源复制到 vehicle_command。",
        validity_freshness_zh="INT32_MAX/NAN 特殊值和来源身份必须与原消息一起保存。",
        confidence="EXACT",
        confidence_reason_zh="COMMAND_INT 的独立复制路径直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_INT 输入记录",
        observation_limit_zh="这只是输入形成，不是接受或执行。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Command_t:input_event",
    )
    add(
        system,
        "Command_t",
        "ASSIGNMENT",
        "MavlinkReceiver::handle_message_command_both(): publish vehicle_command",
        "baseline/px4/src/modules/mavlink/mavlink_receiver.cpp",
        548,
        source_end_line=753,
        function_context="MavlinkReceiver::handle_message_command_both<T>(...) ",
        data_type="templated common command path",
        truth_condition_zh="公共路径处理本地 microservice 后，在无需立即 ACK 时发布 vehicle_command。",
        validity_freshness_zh="某些命令在 MAVLink 模块内处理并只返回 ACK，不会发布同一 uORB 输入事件。",
        confidence="EXACT",
        confidence_reason_zh="公共处理和发布点直接可证。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_LONG/COMMAND_INT 输入记录",
        observation_limit_zh="只有实际到达 publish 分支的命令才形成 vehicle_command 事件。",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Command_t:input_event",
    )
    add(
        system,
        "Command_t",
        "COMMAND_ACCEPTANCE",
        "Commander::handle_command(): VEHICLE_CMD_NAV_TAKEOFF acceptance",
        "baseline/px4/src/modules/commander/Commander.cpp",
        1064,
        function_context="Commander::handle_command(const vehicle_command_s&)",
        data_type="vehicle_command_ack result",
        truth_condition_zh="TAKEOFF 命令只有在用户模式意图成功切到 AUTO_TAKEOFF 时才标记 ACCEPTED，否则可临时拒绝。",
        validity_freshness_zh="按命令来源、command ID 和 ACK timestamp 与输入事件关联。",
        confidence="EXACT",
        confidence_reason_zh="当前接受/拒绝分支直接可证。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="COMMAND_ACK.command,result,target_system,target_component",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Command_t:accepted_event",
        selection_note_zh="只在公式把 Command_t 定义为“已接受命令”时选用。",
    )
    add(
        system,
        "Command_t",
        "COMMAND_ACK",
        "Commander::answer_command(): publish vehicle_command_ack",
        "baseline/px4/src/modules/commander/Commander.cpp",
        2673,
        function_context="Commander::answer_command(const vehicle_command_s&, result)",
        data_type="vehicle_command_ack_s",
        truth_condition_zh="把命令 ID、结果和原发送端身份发布到 vehicle_command_ack。",
        validity_freshness_zh="使用 command、target system/component 和 timestamp 关联。",
        confidence="EXACT",
        confidence_reason_zh="ACK 形成赋值路径直接可证。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="COMMAND_ACK.command,result,target_system,target_component",
        candidate_group="Command_t:accepted_event",
    )
    add(
        system,
        "Command_t",
        "EXECUTION_STATE",
        "vehicle_status.nav_state == NAVIGATION_STATE_AUTO_TAKEOFF",
        "baseline/px4/src/modules/navigator/navigator_main.cpp",
        799,
        function_context="Navigator::run()",
        data_type="uint8 navigation state",
        truth_condition_zh="Navigator 在 AUTO_TAKEOFF 状态选择 Takeoff 导航模块。",
        validity_freshness_zh="这是执行阶段状态，可能晚于命令接收和 ACK。",
        confidence="EXACT",
        confidence_reason_zh="导航模式分支直接可证。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="HEARTBEAT.custom_mode 解码为 AUTO_TAKEOFF",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Command_t:execution_state",
        selection_note_zh="只在公式把 Command_t 定义为“正在执行起飞”时选用。",
    )
    add(
        system,
        "takeoff",
        "ENUM_CONSTANT",
        "vehicle_command_s::VEHICLE_CMD_NAV_TAKEOFF",
        "baseline/px4/msg/versioned/VehicleCommand.msg",
        17,
        data_type="uint16 value 22",
        truth_condition_zh="Command_t == VEHICLE_CMD_NAV_TAKEOFF。",
        confidence="EXACT",
        confidence_reason_zh="当前命令枚举直接定义；Commander 有接收分支。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="COMMAND_LONG.command=22或COMMAND_INT.command=22",
        observation_limit_zh="若命题指开始执行，还应检查 COMMAND_ACK 和 AUTO_TAKEOFF 状态。",
    )
    add(
        system,
        "Target_ALT",
        "UORB_FIELD",
        "position_setpoint_triplet.current.alt",
        "baseline/px4/msg/PositionSetpoint.msg",
        24,
        data_type="float32",
        unit_coordinate="m AMSL",
        truth_condition_zh="current.valid=true 且 current.type 与 TAKEOFF/HOLD 上下文匹配时读取 alt。",
        validity_freshness_zh="必须保存 triplet.timestamp、current.timestamp、valid 和 type。",
        confidence="MODELLED",
        confidence_reason_zh="字段明确，但 Target_ALT 在 TAKEOFF 与 HOLD 的形成路径不同。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="POSITION_TARGET_GLOBAL_INT.alt,time_boot_ms",
        observation_limit_zh="发送要求位置控制启用、triplet/current 有效且经纬度有限；消息不携带 current.type 和内部 timestamp。",
        candidate_group="Target_ALT:amsl_navigator_setpoint",
    )
    add(
        system,
        "Target_ALT",
        "ASSOCIATED_FIELD",
        "position_setpoint_triplet.current",
        "baseline/px4/msg/PositionSetpointTriplet.msg",
        7,
        data_type="PositionSetpoint current container",
        truth_condition_zh="Target_ALT 属于 current 容器，必须同时保留 current.valid、type 和 timestamp。",
        validity_freshness_zh="不得只读 alt 而忽略容器有效位和任务类型。",
        confidence="EXACT",
        confidence_reason_zh="嵌套容器身份在当前 uORB 消息中直接定义。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="Target_ALT:amsl_navigator_setpoint",
    )
    add(
        system,
        "Target_ALT",
        "ASSIGNMENT",
        "rep->current.alt = cmd.param7",
        "baseline/px4/src/modules/navigator/navigator_main.cpp",
        636,
        function_context="Navigator::run()",
        data_type="float32",
        unit_coordinate="m AMSL",
        truth_condition_zh="在接受的 NAV_TAKEOFF 命令路径中，目标高度等于 param7。",
        validity_freshness_zh="要求命令参数有限、目标记录有效并与同一命令关联。",
        confidence="EXACT",
        confidence_reason_zh="当前赋值语句直接绑定起飞命令目标高度。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="COMMAND_LONG.param7或COMMAND_INT.z",
        observation_limit_zh="测试端知道发送值，但飞控内部接受后的 setpoint 仍建议插桩确认。",
        candidate_group="Target_ALT:amsl_navigator_setpoint",
    )
    add(
        system,
        "Target_ALT",
        "DERIVED_EXPRESSION",
        "position_setpoint_triplet.current.alt - home_position.alt",
        "baseline/px4/src/modules/mavlink/streams/POSITION_TARGET_GLOBAL_INT.hpp",
        75,
        source_end_line=84,
        function_context="MavlinkStreamPositionTargetGlobalInt::send()",
        data_type="float derived from two AMSL altitudes",
        unit_coordinate="m above Home",
        truth_condition_zh="HOLD 最小高度参数以 Home 为参考时，用当前目标 AMSL 减 Home AMSL 后与 NAV_MIN_LTR_ALT 比较。",
        validity_freshness_zh="要求 setpoint、Home 和消息有效且属于同一 HOLD 实例；还要记录多旋翼 braking 路径可能绕过最小高度逻辑。",
        confidence="MODELLED",
        confidence_reason_zh="当前参数元数据明确 Home 参考面，但历史性质和当前多旋翼路径不保证总使用该逻辑。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="POSITION_TARGET_GLOBAL_INT.alt,time_boot_ms; HOME_POSITION.altitude,time_usec",
        observation_conversion_zh="两字段统一为米 AMSL 后相减。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Target_ALT:relative_home",
    )
    add(
        system,
        "Target_ALT",
        "DERIVED_EXPRESSION",
        "position_setpoint_triplet.current.alt - captured takeoff-reference altitude",
        "baseline/px4/src/modules/navigator/takeoff.cpp",
        188,
        source_end_line=199,
        function_context="Takeoff::set_takeoff_position()",
        data_type="trace-derived float",
        unit_coordinate="m above takeoff reference",
        truth_condition_zh="默认起飞路径把当前 AMSL 加 MIS_TAKEOFF_ALT 作为目标；相对目标需减去同一起飞实例捕获的参考高度。",
        validity_freshness_zh="若输入命令已提供有限绝对目标高度，则默认参数等式不适用。",
        confidence="MODELLED",
        confidence_reason_zh="默认形成路径可证，但命令覆盖和事件关联使该等式不是无条件状态事实。",
        mavlink_observability="DERIVED",
        mavlink_message_fields="POSITION_TARGET_GLOBAL_INT.alt; GLOBAL_POSITION_INT.alt; TAKEOFF 关联事件",
        observation_limit_zh="必须捕获起飞参考高度并区分默认目标与命令显式目标。",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="Target_ALT:relative_takeoff_reference",
    )

    add(
        system,
        "GPS_loss",
        "UORB_FIELD",
        "sensor_gps.timestamp,fix_type",
        "baseline/px4/msg/SensorGps.msg",
        3,
        data_type="uint64 time plus uint8 enum",
        truth_condition_zh="只能在另有来源的 freshness 阈值或最低 fix_type 规则下判定丢失。",
        validity_freshness_zh="论文没有给出 loss 超时和最低 fix_type，不能人工补值。",
        confidence="MODELLED",
        confidence_reason_zh="原始 GPS 状态可观测，但论文事件边界未定义。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="GPS_RAW_INT.time_usec,fix_type,satellites_visible",
    )
    add(
        system,
        "GPS_loss",
        "ASSOCIATED_FIELD",
        "sensor_gps.fix_type",
        "baseline/px4/msg/SensorGps.msg",
        22,
        data_type="uint8 fix enum",
        truth_condition_zh="GPS_loss 候选定义需保留修复类型，不能只看时间戳。",
        validity_freshness_zh="最低可接受 fix_type 和超时均未由论文给出。",
        confidence="MODELLED",
        confidence_reason_zh="字段身份精确，事件门限未定义。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="GPS_RAW_INT.fix_type,time_usec",
        binding_role="SUPPORTING_EVIDENCE",
        candidate_group="GPS_loss:primary",
    )
    add(
        system,
        "GPS_fail",
        "UORB_FIELD",
        "failsafe_flags.global_position_invalid",
        "baseline/px4/msg/FailsafeFlags.msg",
        32,
        data_type="bool",
        truth_condition_zh="候选解释：当前全球位置估计无效标志为 true。",
        validity_freshness_zh="该状态可能由 GNSS、视觉、光流等定位链共同决定，不是 GPS 专用故障。",
        confidence="MODELLED",
        confidence_reason_zh="这是当前最接近的 failsafe 状态，但与论文旧 GPS_fail 非完全等价。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        observation_limit_zh="标准 MAVLink 没有直接携带该 failsafe_flags 位。",
        candidate_group="GPS_fail:global_position_invalid",
    )
    add(
        system,
        "GPS_fail",
        "ASSIGNMENT",
        "global_position_invalid = !checkPosVelValidity(...) ",
        "baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp",
        681,
        function_context="EstimatorChecks::setModeRequirementFlags()",
        data_type="bool",
        truth_condition_zh="按当前位置有效性、精度、新鲜度和迟滞逻辑计算。",
        confidence="MODELLED",
        confidence_reason_zh="说明当前标志的真实形成路径，但不能证明等价于 GPS 专用故障。",
        mavlink_observability="CONDITIONAL",
        mavlink_message_fields="STATUSTEXT/EVENTS 仅可能提供条件性提示",
        candidate_group="GPS_fail:global_position_invalid",
    )
    add(
        system,
        "k",
        "UNRESOLVED_BOUND",
        "no current PX4 symbol",
        confidence="UNRESOLVED",
        truth_condition_zh="PGFuzz 未公开调度余量操作数和具体数值。",
        confidence_reason_zh="不得把循环次数、3 秒 sleep 或 t-1 猜成 k。",
        mavlink_observability="UNRESOLVED",
    )

    add_parameter(system, "RTL_RETURN_ALT", "RTL_RETURN_ALT", "baseline/px4/src/modules/navigator/rtl_params.c", 59, data_type="float32", unit="m above selected RTL destination")
    add_parameter(system, "RTL_DESCEND_ALT", "RTL_DESCEND_ALT", "baseline/px4/src/modules/navigator/rtl_params.c", 75, data_type="float32", unit="m above selected RTL destination", version_note="当前合法最小值为 0；论文公式写 -1 是公式冲突，不是绑定失败。")
    add_parameter(system, "RTL_LAND_DELAY", "RTL_LAND_DELAY", "baseline/px4/src/modules/navigator/rtl_params.c", 89, data_type="float32", unit="s", truth_note="读取当前延迟；-1 明确定义为不着陆并在 RTL_DESCEND_ALT 盘旋。")
    add_parameter(system, "MPC_LAND_SPEED", "MPC_LAND_SPEED", "baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c", 111, data_type="float32", unit="m/s down-rate magnitude", truth_note="读取当前着陆下降速率配置；实际 setpoint 还会插值或使用 crawl 速率。")
    add_parameter(system, "MIS_LTRMIN_ALT", "NAV_MIN_LTR_ALT", "baseline/px4/src/modules/navigator/navigator_params.c", 192, data_type="float32", unit="m above Home", confidence="MODELLED", truth_note="读取当前语义后继 NAV_MIN_LTR_ALT；负值表示禁用。", relation="SEMANTIC_SUCCESSOR_NOT_PROVEN_RENAME", version_note="旧 MIS_LTRMIN_ALT 当前不存在；源码语义相近，但没有本地历史证明一对一迁移。")
    add_parameter(system, "MIS_TAKEOFF_ALT", "MIS_TAKEOFF_ALT", "baseline/px4/src/modules/navigator/mission_params.c", 58, data_type="float32", unit="m relative takeoff altitude", truth_note="读取未另行指定目标时使用的默认相对起飞高度。")
    add_parameter(system, "MPC_TKO_SPEED", "MPC_TKO_SPEED", "baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c", 57, data_type="float32", unit="m/s up-rate magnitude", truth_note="读取当前起飞速度约束；不等于每个实际物理样本必须严格相等。")
    for term, symbol, path, line, current_name, relation in [
        ("RTL_RETURN_ALT", "RTL::_param_rtl_return_alt", "baseline/px4/src/modules/navigator/rtl.h", 236, "RTL_RETURN_ALT", "EXACT_SAME_NAME"),
        ("RTL_DESCEND_ALT", "RtlDirect::_param_rtl_descend_alt", "baseline/px4/src/modules/navigator/rtl_direct.h", 176, "RTL_DESCEND_ALT", "EXACT_SAME_NAME"),
        ("RTL_LAND_DELAY", "RtlDirect::_param_rtl_land_delay", "baseline/px4/src/modules/navigator/rtl_direct.h", 177, "RTL_LAND_DELAY", "EXACT_SAME_NAME"),
        ("MPC_LAND_SPEED", "FlightTaskAuto::_param_mpc_land_speed", "baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp", 169, "MPC_LAND_SPEED", "EXACT_SAME_NAME"),
        ("MPC_TKO_SPEED", "FlightTaskAuto::_param_mpc_tko_speed", "baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp", 178, "MPC_TKO_SPEED", "EXACT_SAME_NAME"),
        ("MIS_LTRMIN_ALT", "Navigator::_param_min_ltr_alt", "baseline/px4/src/modules/navigator/navigator.h", 437, "NAV_MIN_LTR_ALT", "SEMANTIC_SUCCESSOR_NOT_PROVEN_RENAME"),
        ("MIS_TAKEOFF_ALT", "Navigator::_param_mis_takeoff_alt", "baseline/px4/src/modules/navigator/navigator.h", 442, "MIS_TAKEOFF_ALT", "EXACT_SAME_NAME"),
    ]:
        add(
            system,
            term,
            "PARAMETER_HANDLE",
            symbol,
            path,
            line,
            data_type="ParamFloat class member",
            truth_condition_zh="该成员是模块内的强类型参数句柄；定义行、句柄声明和真实 .get() 消费行分开保留。",
            validity_freshness_zh="参数更新后必须确认对应模块已处理 parameter_update；本任务未做写入生效实验。",
            confidence=("MODELLED" if term == "MIS_LTRMIN_ALT" else "EXACT"),
            confidence_reason_zh=(
                "当前成员身份可证，但旧 MIS_LTRMIN_ALT 到 NAV_MIN_LTR_ALT 仍只是语义后继候选。"
                if term == "MIS_LTRMIN_ALT"
                else "当前参数定义和模块成员为同一生成参数身份。"
            ),
            mavlink_observability="DIRECT",
            mavlink_message_fields=f"PARAM_VALUE.param_id={current_name},param_value",
            observation_limit_zh="PARAM_VALUE 显示当前存储/运行值，不单独证明该模块已在当前状态使用它。",
            current_parameter_name=current_name,
            historical_current_relation=relation,
        )
    for term, symbol, path, line, context, current_name, confidence in [
        ("RTL_RETURN_ALT", "_param_rtl_return_alt.get()", "baseline/px4/src/modules/navigator/rtl.cpp", 477, "RTL::findRtlDestination()", "RTL_RETURN_ALT", "EXACT"),
        ("RTL_RETURN_ALT", "_param_rtl_return_alt.get()", "baseline/px4/src/modules/navigator/rtl.cpp", 530, "RTL::calculate_return_alt_from_cone_half_angle()", "RTL_RETURN_ALT", "EXACT"),
        ("RTL_DESCEND_ALT", "_param_rtl_descend_alt.get()", "baseline/px4/src/modules/navigator/rtl_direct.cpp", 587, "RtlDirect::sanitizeLandApproach()", "RTL_DESCEND_ALT", "EXACT"),
        ("RTL_LAND_DELAY", "_param_rtl_land_delay.get()", "baseline/px4/src/modules/navigator/rtl_direct.cpp", 166, "RtlDirect::_updateRtlState()", "RTL_LAND_DELAY", "EXACT"),
        ("RTL_LAND_DELAY", "_param_rtl_land_delay.get()", "baseline/px4/src/modules/navigator/rtl_direct.cpp", 307, "RtlDirect::set_rtl_item()", "RTL_LAND_DELAY", "EXACT"),
        ("RTL_LAND_DELAY", "_param_rtl_land_delay.get() < -FLT_EPSILON", "baseline/px4/src/modules/navigator/rtl_direct.cpp", 309, "RtlDirect::set_rtl_item()", "RTL_LAND_DELAY", "EXACT"),
        ("MPC_LAND_SPEED", "_param_mpc_land_speed.get()", "baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp", 234, "FlightTaskAuto::_prepareLandSetpoints()", "MPC_LAND_SPEED", "EXACT"),
        ("MPC_LAND_SPEED", "_param_mpc_land_speed.get()", "baseline/px4/src/modules/flight_mode_manager/tasks/Descend/FlightTaskDescend.cpp", 52, "FlightTaskDescend::update()", "MPC_LAND_SPEED", "EXACT"),
        ("MPC_TKO_SPEED", "_param_mpc_tko_speed.get()", "baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp", 812, "FlightTaskAuto::_updateTrajConstraints()", "MPC_TKO_SPEED", "EXACT"),
        ("MIS_TAKEOFF_ALT", "Navigator::get_param_mis_takeoff_alt()", "baseline/px4/src/modules/navigator/takeoff.cpp", 188, "Takeoff::set_takeoff_position()", "MIS_TAKEOFF_ALT", "EXACT"),
        ("MIS_LTRMIN_ALT", "Navigator::get_loiter_min_alt()", "baseline/px4/src/modules/navigator/mission_block.cpp", 727, "MissionBlock::setLoiterItemFromCurrentPosition()", "NAV_MIN_LTR_ALT", "MODELLED"),
    ]:
        add(
            system,
            term,
            "PARAMETER_CONSUMER",
            symbol,
            path,
            line,
            function_context=context,
            data_type="runtime parameter value consumed by control/navigation logic",
            truth_condition_zh="该 .get() 或 getter 调用是当前参数值被使用的具体路径。",
            validity_freshness_zh="只在所列模式和分支执行时消费；不得由此控制流反推性质已满足。",
            confidence=confidence,
            confidence_reason_zh=(
                "当前消费路径可证，但旧 MIS_LTRMIN_ALT 到 NAV_MIN_LTR_ALT 的历史等价关系仍未证明。"
                if term == "MIS_LTRMIN_ALT"
                else "当前参数句柄的真实消费语句直接可证。"
            ),
            mavlink_observability="INSTRUMENTATION_REQUIRED",
            mavlink_message_fields=f"PARAM_VALUE.param_id={current_name},param_value",
            observation_limit_zh="PARAM_VALUE 只报告参数值；要证明当前运行确实进入该消费点，需要分支事件或内部插桩。",
            current_parameter_name=current_name,
            binding_role="SUPPORTING_EVIDENCE",
            candidate_group=f"{term}:primary",
        )
    add(
        system,
        "COM_POS_FS_DELAY",
        "REMOVED_PARAMETER",
        "COM_POS_FS_DELAY",
        "baseline/px4/docs/en/releases/1.16.md",
        58,
        data_type="removed seconds parameter",
        truth_condition_zh="当前没有可读取的同名运行参数值。",
        validity_freshness_zh="当前发行说明写明该位置丢失延迟参数已删除。",
        confidence="UNRESOLVED",
        confidence_reason_zh="没有可靠的一对一当前替代项，不能自动用 EKF2_NOAID_TOUT 等参数代替。",
        mavlink_observability="UNRESOLVED",
        current_parameter_name="COM_POS_FS_DELAY",
        historical_current_relation="REMOVED_NO_EQUIVALENT",
    )
    add(
        system,
        "COM_POS_FS_DELAY",
        "NON_EQUIVALENT_CANDIDATE",
        "EKF2_NOAID_TOUT",
        "baseline/px4/src/modules/ekf2/module.yaml",
        76,
        data_type="int32 microseconds parameter",
        unit_coordinate="us maximum inertial dead-reckoning time",
        truth_condition_zh="只记录一个当前相关但不等价的超时：最后一次约束速度漂移的测量融合后，允许的最大惯性航推时间。",
        validity_freshness_zh="它是 EKF 水平导航有效性门限，不是旧 COM_POS_FS_DELAY 的 Commander 位置丢失动作延迟。",
        confidence="UNRESOLVED",
        confidence_reason_zh="发行说明只证明旧参数已删除，没有一对一替代证据；本行不能用于改写公式。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="PARAM_VALUE.param_id=EKF2_NOAID_TOUT,param_value",
        observation_conversion_zh="微秒除以 1,000,000 可转为秒，但只能解释 EKF2_NOAID_TOUT 自身。",
        observation_limit_zh="禁止将它自动代入历史 COM_POS_FS_DELAY 公式。",
        current_parameter_name="EKF2_NOAID_TOUT",
        historical_current_relation="NON_EQUIVALENT_CANDIDATE",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="COM_POS_FS_DELAY:ekf2_noaid_tout_non_equivalent",
    )
    add(
        system,
        "COM_POS_FS_DELAY",
        "NON_EQUIVALENT_CANDIDATE",
        "COM_POS_FS_EPH",
        "baseline/px4/src/modules/commander/commander_params.c",
        538,
        data_type="float32 accuracy threshold",
        unit_coordinate="m horizontal position uncertainty",
        truth_condition_zh="当前多旋翼位置故障的另一种机制使用水平位置精度阈值；它不是时间延迟。",
        validity_freshness_zh="只在相应位置有效性检查和飞行阶段使用；负值禁用。",
        confidence="UNRESOLVED",
        confidence_reason_zh="它说明当前相关位置故障机制，但类型是距离阈值，不能用于改写历史 COM_POS_FS_DELAY 时间公式。",
        mavlink_observability="DIRECT",
        mavlink_message_fields="PARAM_VALUE.param_id=COM_POS_FS_EPH,param_value",
        observation_limit_zh="禁止将距离阈值自动代入历史秒数上界。",
        current_parameter_name="COM_POS_FS_EPH",
        historical_current_relation="NON_EQUIVALENT_CANDIDATE",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="COM_POS_FS_DELAY:com_pos_fs_eph_non_equivalent",
    )
    add(
        system,
        "COM_POS_FS_DELAY",
        "PARAMETER_CONSUMER",
        "EstimatorChecks::setModeRequirementFlags(): _param_com_pos_fs_eph.get()",
        "baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp",
        664,
        function_context="EstimatorChecks::setModeRequirementFlags()",
        data_type="float position-accuracy threshold comparison",
        unit_coordinate="m EPH threshold",
        truth_condition_zh="读取 COM_POS_FS_EPH 形成当前位置精度失效阈值。",
        validity_freshness_zh="这是精度阈值消费，不是旧 Commander 延迟计时器。",
        confidence="UNRESOLVED",
        confidence_reason_zh="真实消费点可证，但与历史时间参数非等价。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        mavlink_message_fields="PARAM_VALUE.param_id=COM_POS_FS_EPH,param_value",
        observation_limit_zh="禁止把当前分支消费解释成历史 COM_POS_FS_DELAY 的计时起止。",
        current_parameter_name="COM_POS_FS_EPH",
        historical_current_relation="NON_EQUIVALENT_CANDIDATE",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="COM_POS_FS_DELAY:com_pos_fs_eph_non_equivalent",
    )
    add(
        system,
        "COM_POS_FS_DELAY",
        "PARAMETER_CONSUMER",
        "Ekf::updateHorizontalDeadReckoningstatus(): _params.ekf2_noaid_tout",
        "baseline/px4/src/modules/ekf2/EKF/ekf_helper.cpp",
        880,
        function_context="Ekf::updateHorizontalDeadReckoningstatus()",
        data_type="uint64 timeout comparison",
        unit_coordinate="microseconds since last horizontal aiding",
        truth_condition_zh="EKF2_NOAID_TOUT 只用于判定水平惯性航推是否超时。",
        validity_freshness_zh="起点是 _time_last_horizontal_aiding，属于 EKF 内部单调时间；不是旧 Commander 故障动作延迟。",
        confidence="UNRESOLVED",
        confidence_reason_zh="实际消费路径可证，但这也进一步证明它与 COM_POS_FS_DELAY 非等价。",
        mavlink_observability="INSTRUMENTATION_REQUIRED",
        mavlink_message_fields="PARAM_VALUE.param_id=EKF2_NOAID_TOUT,param_value",
        observation_limit_zh="禁止代入历史 COM_POS_FS_DELAY 公式。",
        current_parameter_name="EKF2_NOAID_TOUT",
        historical_current_relation="NON_EQUIVALENT_CANDIDATE",
        binding_role="ALTERNATIVE_SEMANTICS",
        candidate_group="COM_POS_FS_DELAY:ekf2_noaid_tout_non_equivalent",
    )


def ap_status(expression: str, term_rows: list[dict[str, Any]], policy_issues: list[str]) -> tuple[str, str]:
    terms = {row["term"] for row in term_rows}
    core_by_term = {
        term: [row for row in term_rows if row["term"] == term and row["binding_role"] != "SUPPORTING_EVIDENCE"]
        for term in terms
    }
    if "GroundALT" in terms and "ALT_t" in terms:
        return "UNRESOLVED", "论文未定义 GroundALT 是数值高度、Home 高度、地形高度还是已落地状态；类型和参考面补证前不判真值。"
    if any(term in {"k", "Waypoint", "COM_POS_FS_DELAY"} for term in terms):
        return "UNRESOLVED", "包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。"
    if "GPS_fail" in terms and all(row["confidence"] != "EXACT" for row in core_by_term["GPS_fail"]):
        return "UNRESOLVED", "论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。"
    if any(all(r["confidence"] == "UNRESOLVED" for r in core_by_term[term]) for term in terms):
        return "UNRESOLVED", "至少一个公式词项只有尚未解决的绑定。"
    model_markers = (
        "t-1",
        "Pos_t",
        "ALT_t",
        "Speed_vertical_t",
        "Circle_speed_t",
        "Circle_radius_t",
        "Throttle_t",
        "RC_",
        "GroundALT",
        "ALT_src",
        "Baro",
        "Target_ALT",
        "GPS_loss",
    )
    if any(marker in expression for marker in model_markers) or any(row["confidence"] == "MODELLED" for row in term_rows):
        return "MODELLED", "需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。"
    if "TYPE_UNIT_MISMATCH" in policy_issues or "WRONG_PARAMETER_IN_FORMULA" in policy_issues:
        return "MODELLED", "命题实体可定位，但所在性质存在论文公式冲突，不能据此修复整条公式。"
    return "EXACT", "本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。"


def evaluation_plan(expression: str, status: str) -> str:
    if status == "UNRESOLVED":
        return "保留原式和全部候选绑定；缺失定义或数值补证前不得给真值。"
    if "t-1" in expression:
        return "选择一个有证据的状态定义，按发送端时间保存前一有效样本；保持坐标系、单位、来源和重置计数一致后再比较。"
    if "Mode_t" in expression:
        return "解码当前模式字段并与当前枚举比较；若还有其他词项，再按各自绑定条件合取。"
    if "Speed_vertical_t" in expression:
        return "读取实际垂直速度，执行厘米/秒到米/秒及 NED 符号转换；参数使用本次运行实际值而非默认值。"
    if "Pos_t" in expression or "home_position" in expression:
        return "统一 WGS84 或局部坐标，检查有效性和重置，再用人工审核后确定的距离容差判定；原论文严格相等保持原样记录。"
    if any(token in expression for token in ("RC_pitch", "RC_roll", "RC_throttle", "Throttle_t")):
        return "若阈值为 1500，使用当前 RC_MAP 对应的原始 PWM；同时保留校准、死区、输入来源和 failsafe 有效性。"
    if "RC_t" in expression:
        return "先选择物理接收器或上层手动控制可用性语义；物理接收器需联合 rc_lost、rc_failsafe、最后信号时间和 input_source。"
    if "Circle_" in expression:
        return "明确选择内部目标量或实际测量量，保持前后样本定义一致，并按半径符号解析方向。"
    if any(token in expression for token in ("RTL_", "MPC_", "MIS_", "FS_", "CHUTE_", "PILOT_")):
        return "从当前运行实例读取参数值并按元数据单位解释；不要硬编码作者历史默认值或源码默认值。"
    return "按所列源码实体、真值条件、有效性条件和观测换算判定。"


def preferred_candidate_group(atom: dict[str, Any], term: str, rows: list[dict[str, Any]]) -> str:
    """Choose one explicit semantic group without discarding alternatives."""
    system = atom["system"]
    property_id = atom["property_id"]
    expression = atom["expression"]
    if system == "ArduPilot":
        special = {
            "ALT_src": "ALT_src:runtime_active",
            "home_position": "home_position:home",
            "GroundALT": "GroundALT:untyped_unresolved",
            "Roll_rate": "Roll_rate:control_request",
            "Roll_direction": "Roll_direction:commanded_direction",
            "GPS_fail": "GPS_fail:unresolved_paper_semantics",
            "Parachute": "Parachute:released_latched",
            "Waypoint": "Waypoint:guided_unresolved",
        }
        if term == "Baro":
            return "Baro:source_enum" if "ALT_src" in expression else "Baro:health"
        if term in special:
            return special[term]
    if system == "PX4":
        if term in {"ALT_t", "ALT_t-1"}:
            prefix = term
            if property_id.startswith("PX.LAND"):
                return f"{prefix}:distance_to_ground"
            if property_id.startswith("PX.RTL"):
                return f"{prefix}:relative_rtl_destination"
            if "MIS_LTRMIN_ALT" in expression:
                return f"{prefix}:relative_home"
            if "MIS_TAKEOFF_ALT" in expression or property_id.startswith("PX.TAKEOFF"):
                return f"{prefix}:relative_takeoff_reference"
            return f"{prefix}:global_amsl"
        special = {
            "Pos_t": "Pos_t:global_wgs84",
            "Pos_t-1": "Pos_t-1:global_wgs84",
            "GroundALT": "GroundALT:untyped_unresolved",
            "Circle_radius_t": "Circle_radius_t:target_radius",
            "Circle_direction_t": "Circle_direction_t:target_encoded_direction",
            "Circle_speed_t": "Circle_speed_t:target_tangential_speed",
            "Circle_speed_t-1": "Circle_speed_t-1:target_tangential_speed",
            "RC_t": "RC_t:physical_receiver",
            "Disarm": "Disarm:vehicle_arming_state",
            "Command_t": "Command_t:input_event",
            "GPS_fail": "GPS_fail:global_position_invalid",
        }
        if term == "Target_ALT":
            if property_id == "PX.HOLD2":
                return "Target_ALT:relative_home"
            if property_id == "PX.TAKEOFF1":
                return "Target_ALT:relative_takeoff_reference"
            return "Target_ALT:amsl_navigator_setpoint"
        if term in special:
            return special[term]
        if term in {"RC_pitch", "RC_roll", "Throttle_t"}:
            return f"{term}:raw_pwm" if "1500" in expression else f"{term}:normalized_manual_control"
    default_group = f"{term}:primary"
    if any(row["candidate_group"] == default_group for row in rows):
        return default_group
    primary_groups = [row["candidate_group"] for row in rows if row["binding_role"] == "PRIMARY_VALUE"]
    if primary_groups:
        return primary_groups[0]
    return rows[0]["candidate_group"]


def selection_reason(atom: dict[str, Any], term: str, group: str) -> str:
    property_id = atom["property_id"]
    expression = atom["expression"]
    reasons = {
        "GroundALT:untyped_unresolved": "论文把 GroundALT 放进数值高度等式，却没有给类型和参考面；选择未解决组，landed/Home/terrain 只保留为替代。",
        "ALT_src:runtime_active": "性质询问实际高度来源，因此选择 EKF 运行时 activeHgtSource，而不是三套配置参数。",
        "Baro:source_enum": "该命题与 ALT_src 同时出现，选择“当前高度源为 BARO”的枚举解释；传感器健康保留为替代。",
        "Baro:health": "独立 Baro=on 没有来源等式约束，暂以主气压计健康解释，并保留高度源解释。",
        "GPS_fail:unresolved_paper_semantics": "当前没有 GPS 专用且与论文等价的单一故障状态，选择未解决主组。",
        "Waypoint:guided_unresolved": "论文未定义 Guided 的 waypoint empty，选择未解决主组而不拿任务列表替代。",
        "ALT_t:relative_rtl_destination": "RTL_RETURN_ALT 当前定义为选定 RTL 目的地以上高度，目的地可为 Home、安全点或任务着陆点。",
        "ALT_t-1:relative_rtl_destination": "上一样本必须与当前 RTL 高度使用同一目的地参考面。",
        "ALT_t:distance_to_ground": "LAND 语境中的地面比较优先使用有效离地距离；仍不解决 GroundALT 类型。",
        "ALT_t-1:distance_to_ground": "上一样本与当前 LAND 高度共同使用离地距离定义。",
        "ALT_t:relative_home": "NAV_MIN_LTR_ALT 当前元数据明确以 Home 为参考面。",
        "ALT_t-1:relative_home": "上一样本与当前高度共同使用 Home 参考面。",
        "ALT_t:relative_takeoff_reference": "MIS_TAKEOFF_ALT 是默认相对起飞高度，不能把 AMSL 高度直接与它比较。",
        "ALT_t-1:relative_takeoff_reference": "上一样本与当前高度共同使用同一次起飞捕获的参考面。",
        "Target_ALT:relative_home": "NAV_MIN_LTR_ALT 是 Home 以上高度，所以目标必须先由 AMSL 转为相对 Home。",
        "Target_ALT:relative_takeoff_reference": "MIS_TAKEOFF_ALT 是相对起飞参考高度，所以目标必须与同一起飞实例的参考高度关联。",
        "RC_t:physical_receiver": "论文写 RC on/off，当前先选择底层接收器链路解释；上层 manual-control 可用性保留为替代。",
        "Command_t:input_event": "印刷前件只写收到 takeoff 命令，没有写 ACK 或执行状态；选择输入事件，但语义仍标为建模。",
        "Circle_direction_t:target_encoded_direction": "作者候选输入改变 Orbit 目标方向，先选择 ORBIT_EXECUTION_STATUS 的目标编码方向；实际运动方向保留为替代。",
        "Circle_speed_t:target_tangential_speed": "论文与控制输入/参数关联，先选择目标切向速度；实际地速保留为替代。",
        "Circle_speed_t-1:target_tangential_speed": "上一速度样本必须与当前值共同使用目标切向速度。",
    }
    if group in reasons:
        return reasons[group]
    if group.endswith(":raw_pwm"):
        return "表达式使用 1500 阈值，必须选择映射后的原始 PWM，而不是 [-1,1] 标准化轴值。"
    if group.endswith(":normalized_manual_control"):
        return "表达式没有原始 1500 阈值，选择当前控制使用的标准化手动输入，并保留来源字段。"
    if group.endswith(":global_wgs84"):
        return "公式涉及 Home 或全球位置，选择 WGS84 全球位置；局部 NED 只保留为替代。"
    if group.endswith(":global_amsl"):
        return "没有出现相对高度参数或 LAND/RTL 专用参考面，选择当前全球 AMSL 高度并要求有效性。"
    if group.endswith(":primary"):
        return "该词项只有一个当前主语义组，按其真值、有效性和观测限制使用。"
    return f"性质 {property_id} 的表达式 {expression} 选择候选组 {group}；其他组保持互斥，不参与当前真值计算。"


def select_term_bindings(atom: dict[str, Any], by_term: dict[tuple[str, str], list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    selected: list[dict[str, Any]] = []
    alternatives: list[dict[str, Any]] = []
    summaries: list[str] = []
    reasons: list[str] = []
    for term in atom["terms"]:
        rows = by_term[(atom["system"], term)]
        preferred = preferred_candidate_group(atom, term, rows)
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[row["candidate_group"]].append(row)
        selected.extend(groups[preferred])
        reasons.append(f"{term}：{selection_reason(atom, term, preferred)}")
        for group, group_rows in groups.items():
            ids = ",".join(row["binding_id"] for row in group_rows)
            label = "SELECTED" if group == preferred else "ALTERNATIVE"
            summaries.append(f"{term}::{label}::{group}::{ids}")
            if group != preferred:
                alternatives.extend(group_rows)
    return selected, alternatives, summaries, reasons


def aggregate_observability(status: str, atom: dict[str, Any], selected: list[dict[str, Any]]) -> str:
    if status == "UNRESOLVED":
        return "UNRESOLVED"
    ranks = {"DIRECT": 0, "DERIVED": 1, "CONDITIONAL": 2, "INSTRUMENTATION_REQUIRED": 3, "UNRESOLVED": 4}
    by_term: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        by_term[row["term"]].append(row)
    term_required = []
    for term in atom["terms"]:
        # SUPPORTING_EVIDENCE can explain mapping, formation, consumption or
        # sending, but it cannot make the selected truth value easier to
        # observe.  For example, a directly readable RC_MAP parameter does not
        # turn a conditionally available raw RC sample into a direct sample.
        core_rows = [row for row in by_term[term] if row["binding_role"] != "SUPPORTING_EVIDENCE"]
        values = [row["mavlink_observability"] for row in (core_rows or by_term[term])]
        term_required.append(max(values, key=lambda value: ranks[value]))
    return max(term_required, key=lambda value: ranks[value])


def build_ap_bindings() -> list[dict[str, Any]]:
    ap_inventory = json.loads((ROOT / "atomic_proposition_inventory.json").read_text(encoding="utf-8"))["rows"]
    policies = json.loads((ROOT / "table_xii_formula_inventory.json").read_text(encoding="utf-8"))["policies"]
    issue_map = {p["policy_id"]: p["issues"] for p in policies}
    by_term: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in ROWS:
        by_term[(row["system"], row["term"])].append(row)
    result = []
    for atom in ap_inventory:
        bindings = [r for term in atom["terms"] for r in by_term[(atom["system"], term)]]
        selected, alternatives, group_summary, selection_reasons = select_term_bindings(atom, by_term)
        status, reason = ap_status(atom["expression"], selected, issue_map[atom["property_id"]])
        observation = aggregate_observability(status, atom, selected)
        selection_status = (
            "UNRESOLVED_PRIMARY"
            if status == "UNRESOLVED"
            else "PRIMARY_WITH_ALTERNATIVES"
            if alternatives
            else "PRIMARY_SELECTED"
        )
        result.append(
            {
                **atom,
                "term_binding_ids": [r["binding_id"] for r in bindings],
                "selected_term_binding_ids": [r["binding_id"] for r in selected],
                "alternative_term_binding_ids": [r["binding_id"] for r in alternatives],
                "binding_group_summary": group_summary,
                "binding_selection_status": selection_status,
                "binding_selection_reason_zh": (
                    "；".join(reason.rstrip("。") for reason in selection_reasons)
                    + ("；其余组保留为互斥替代解释，不作为合取条件" if alternatives else "")
                    + "。"
                ),
                "binding_status": status,
                "binding_status_reason_zh": reason,
                "evaluation_plan_zh": evaluation_plan(atom["expression"], status),
                "mavlink_observability": observation,
                "mavlink_observation_fields": sorted({f.strip() for r in selected for f in r["mavlink_message_fields"].split(";") if f.strip()}),
                "all_candidate_observation_fields": sorted({f.strip() for r in bindings for f in r["mavlink_message_fields"].split(";") if f.strip()}),
                "mavlink_observation_bindings": [
                    {
                        "binding_id": r["binding_id"],
                        "term": r["term"],
                        "binding_role": r["binding_role"],
                        "mavlink_observability": r["mavlink_observability"],
                        "message_fields_raw": r["mavlink_message_fields"],
                    }
                    for r in selected if r["mavlink_message_fields"]
                ],
                "property_issue_codes": issue_map[atom["property_id"]],
                "implementation_satisfaction": "NOT_ASSESSED",
            }
        )
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "|".join(map(str, v)) if isinstance(v, list) else v for k, v in row.items()})


def render_markdown(rows: list[dict[str, Any]], aps: list[dict[str, Any]]) -> str:
    lines = [
        "# PGFuzz-MTL51 当前源码词项与原子命题绑定",
        "",
        "## 一、状态图例",
        "",
    ]
    for key, value in CONFIDENCE_ZH.items():
        lines.append(f"- `{key}`：{value}")
    for key, value in OBSERVABILITY_ZH.items():
        lines.append(f"- `{key}`：{value}")
    for key, value in BINDING_ROLE_ZH.items():
        lines.append(f"- `{key}`：{value}")
    for key, value in SELECTION_STATUS_ZH.items():
        lines.append(f"- `{key}`：{value}")
    lines += [
        "- `NOT_ASSESSED`：未评估实现是否满足性质；源码只用于身份、位置和观测绑定。",
        "- `uORB`：PX4 内部发布—订阅消息总线；内部状态不一定直接出现在 MAVLink 中。",
        "- `TRACE_PREVIOUS_SAMPLE`：由监视器保存的前一有效样本；不是源码中的独立变量，也不是一秒前。",
        "- `data type` 中文为“数据类型”，说明源码如何存储该值；`unit/coordinate` 中文为“单位/坐标系”，说明尺度、正方向和参考面。下表保留精确源码表述；源码绑定的 100 种数据类型和 61 种单位/坐标原值，以及当前输入目录的 7 种类型和 28 种单位原值，均在 [类型与单位字典](TYPE_UNIT_DICTIONARY.md) 中逐项解释。",
        "",
        "## 二、总量",
        "",
        f"- 词项源码绑定行：{len(rows)}。",
        f"- 覆盖唯一系统—词项：{len({(r['system'], r['term']) for r in rows})}。",
        f"- 原子命题出现：{len(aps)}。",
        "- 所有行固定 `implementation_satisfaction=NOT_ASSESSED`。",
        "",
    ]
    for system in ("ArduPilot", "PX4"):
        subset = [r for r in rows if r["system"] == system]
        ap_subset = [r for r in aps if r["system"] == system]
        lines += [
            f"## 三、{system} 词项绑定",
            "",
            "| 论文词项 | 当前源码实体 | 绑定角色/候选组 | 类型/单位 | 置信度 | MAVLink 可观测性 | 证据位置 |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in subset:
            if row["source_path"]:
                suffix = f"-{row['source_end_line']}" if row["source_end_line"] != row["source_line"] else ""
                location = f"{row['source_path']}:{row['source_line']}{suffix}"
            else:
                location = "无当前位置"
            dtype = " / ".join(x for x in (row["data_type"], row["unit_coordinate"]) if x)
            lines.append(
                f"| `{row['term']}` | `{row['symbol']}` | `{row['binding_role']}` / `{row['candidate_group']}` | {dtype or '未定义'} | `{row['confidence']}` | `{row['mavlink_observability']}` | `{location}` |"
            )
        lines += [
            "",
            f"### {system} 原子命题绑定状态",
            "",
            "| 性质 | AP | 原子命题 | 语义组选择 | 状态 | 观测 | 判定说明 |",
            "|---|---|---|---|---|---|---|",
        ]
        for atom in ap_subset:
            lines.append(
                f"| `{atom['property_id']}` | `{atom['ap_id']}` | `{atom['expression']}` | `{atom['binding_selection_status']}` | `{atom['binding_status']}` | `{atom['mavlink_observability']}` | {atom['binding_status_reason_zh']} |"
            )
        lines.append("")
    lines += [
        "## 四、审核边界",
        "",
        "绑定为 `EXACT` 只说明该原子命题的局部字段或枚举身份可精确判定，不说明整条时序性质正确，也不说明固件满足它。参数默认值、当前运行值和作者历史值分别保存；运行中能否修改及何时生效尚未逐参数写入验证。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    build_ardupilot_rows()
    build_px4_rows()
    counters: dict[str, int] = defaultdict(int)
    for row in ROWS:
        if not row["selection_note_zh"]:
            row["selection_note_zh"] = {
                "PRIMARY_VALUE": "该行是其候选组的核心真值实体；只有该组被性质选择时才参与判真。",
                "SUPPORTING_EVIDENCE": "该行只说明形成、消费、关联或发送路径，不会单独改善主值的可观测性。",
                "ALTERNATIVE_SEMANTICS": "该行属于互斥替代解释；只有人工切换到本候选组后才参与判真。",
            }[row["binding_role"]]
        counters[row["system"]] += 1
        prefix = "ARD" if row["system"] == "ArduPilot" else "PX4"
        row["binding_id"] = f"{prefix}-TB-{counters[row['system']]:03d}"
    # Keep the identifier near the front in machine-readable output.
    ordered_rows = []
    for row in ROWS:
        ordered_rows.append({"binding_id": row.pop("binding_id"), **row})
    ROWS[:] = ordered_rows
    aps = build_ap_bindings()

    payload = {
        "schema_version": "1.0",
        "status_definitions_zh": {**CONFIDENCE_ZH, **OBSERVABILITY_ZH, **BINDING_ROLE_ZH, **SELECTION_STATUS_ZH, "NOT_ASSESSED": "未评估固件是否满足性质。"},
        "rows": ROWS,
    }
    (ROOT / "term_source_bindings.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(ROOT / "term_source_bindings.csv", ROWS)
    ap_payload = {"schema_version": "1.0", "rows": aps}
    (ROOT / "atomic_proposition_bindings.json").write_text(json.dumps(ap_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(ROOT / "atomic_proposition_bindings.csv", aps)
    (ROOT / "SOURCE_BINDING_GUIDE.md").write_text(render_markdown(ROWS, aps), encoding="utf-8")

    for system, directory in (("ArduPilot", "ArduPilot"), ("PX4", "PX4")):
        term_subset = [r for r in ROWS if r["system"] == system]
        ap_subset = [r for r in aps if r["system"] == system]
        out = ROOT / directory
        (out / "term_source_bindings.json").write_text(json.dumps({"schema_version": "1.0", "rows": term_subset}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(out / "term_source_bindings.csv", term_subset)
        (out / "atomic_proposition_bindings.json").write_text(json.dumps({"schema_version": "1.0", "rows": ap_subset}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(out / "atomic_proposition_bindings.csv", ap_subset)

    summary = {
        "schema_version": "1.0",
        "term_binding_rows": len(ROWS),
        "unique_system_terms": len({(r["system"], r["term"]) for r in ROWS}),
        "term_rows_by_system": Counter(r["system"] for r in ROWS),
        "term_confidence": Counter(r["confidence"] for r in ROWS),
        "term_observability": Counter(r["mavlink_observability"] for r in ROWS),
        "ap_occurrences": len(aps),
        "ap_status": Counter(r["binding_status"] for r in aps),
        "ap_observability": Counter(r["mavlink_observability"] for r in aps),
        "implementation_satisfaction": "NOT_ASSESSED",
    }
    (ROOT / "validation" / "source_binding_build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
