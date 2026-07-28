#!/usr/bin/env python3
"""Expand PGFuzz policy input files and bind their identities to frozen catalogs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PGFUZZ_ROOT = PROJECT_ROOT / "baseline" / "pgfuzz"
PARAM_CATALOG = PROJECT_ROOT / "benchmark" / "mavlink_catalog" / "configuration_parameters.csv"
COMMAND_CATALOG = PROJECT_ROOT / "benchmark" / "mavlink_catalog" / "commands.csv"
RUNTIME_CATALOG = PROJECT_ROOT / "benchmark" / "extraction_runs" / "milestone6" / "runtime_parameter_snapshots.csv"


CLASS_DEFS = {
    "InputP": "Parameter Input，配置参数输入；作者把该参数列为性质的候选变异输入。",
    "InputC": "Command Input，命令输入；包括 MAVLink 命令、模式切换或遥控通道输入。",
    "InputE": "Environmental Input，环境输入；通常由 SITL 仿真参数构造传感器或环境变化。",
    "PRECONDITION": "前置条件；作者要求先设置该值，再执行目标测试输入。",
}

STATUS_DEFS = {
    "EXACT_CURRENT_DEFINITION": "当前冻结源码的参数定义目录中存在同名定义。",
    "RENAMED_CURRENT_DEFINITION": "有当前源码位置支持的历史名到当前名映射；不是字符串猜测。",
    "CURRENT_DEFINITION_NOT_FOUND": "当前冻结参数定义目录中没有找到同名或已审计重命名目标。",
    "COMMAND_XML_DEFINITION_FOUND": "当前固定 MAVLink XML 中存在同名命令定义；不等于飞控一定处理该命令。",
    "COMMAND_XML_DEFINITION_NOT_FOUND": "当前固定 MAVLink XML 中没有找到同名命令定义。",
    "SPECIAL_CONTROL_INPUT": "PGFuzz 自定义的模式或遥控伪输入，不是配置参数或 MAV_CMD 枚举。",
}

DEPENDENCY_STRENGTH_DEFS = {
    "CANDIDATE_ASSOCIATION": "作者 policy 文件中的高召回候选关联；没有逐项公开真实数据依赖证明。",
    "EXPLICIT_PRECONDITION": "作者制品明确要求先设置的值；只对旧制品实验流程成立。",
}

# Every rename has a concrete current-source audit location.  These entries do
# not assert semantic equivalence beyond the note and confidence recorded here.
ALIASES: dict[tuple[str, str], dict[str, str]] = {
    ("ArduPilot", "ACRO_RP_P"): {"current_name": "ACRO_RP_RATE", "evidence": "baseline/ardupilot/ArduCopter/Parameters.cpp:1387", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前参数元数据使用 ACRO_RP_RATE。"},
    ("ArduPilot", "ATC_ACCEL_R_MAX"): {"current_name": "ATC_ACC_R_MAX", "evidence": "baseline/ardupilot/libraries/AC_AttitudeControl/AC_AttitudeControl.cpp:49", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前姿态控制参数缩写为 ACC。"},
    ("ArduPilot", "EK3_ALT_SOURCE"): {"current_name": "EK3_SRC1_POSZ", "evidence": "baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3.cpp:1841", "confidence": "CURATED_MIGRATION_MODELLED", "note_zh": "旧单一高度源参数迁移为 EKF3 第一源位置 Z 选择；语义范围发生变化。"},
    ("ArduPilot", "GND_ALT_OFFSET"): {"current_name": "BARO_ALT_OFFSET", "evidence": "baseline/ardupilot/libraries/AP_Baro/AP_Baro.cpp:115", "confidence": "CURATED_MIGRATION_MODELLED", "note_zh": "当前气压计参数组采用 BARO 前缀；未发现完整单项迁移证明。"},
    ("ArduPilot", "GND_PRIMARY"): {"current_name": "BARO_PRIMARY", "evidence": "baseline/ardupilot/libraries/AP_Baro/AP_Baro.cpp:123", "confidence": "CURATED_MIGRATION_MODELLED", "note_zh": "当前主气压计参数采用 BARO 前缀。"},
    ("ArduPilot", "GND_TEMP"): {"current_name": "BARO_GND_TEMP", "evidence": "baseline/ardupilot/libraries/AP_Baro/AP_Baro.cpp:103", "confidence": "CURATED_MIGRATION_MODELLED", "note_zh": "当前地面温度参数位于 BARO 参数组。"},
    ("ArduPilot", "GPS_POS1_Z"): {"current_name": "GPS1_POS_Z", "evidence": "baseline/ardupilot/libraries/AP_GPS/AP_GPS.cpp:206", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前第一 GPS 天线 Z 偏移参数名调整。"},
    ("ArduPilot", "GPS_POS2_Z"): {"current_name": "GPS2_POS_Z", "evidence": "baseline/ardupilot/libraries/AP_GPS/AP_GPS.cpp:271", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前第二 GPS 天线 Z 偏移参数名调整。"},
    ("ArduPilot", "LAND_ALT_LOW"): {"current_name": "LAND_ALT_LOW_M", "evidence": "baseline/ardupilot/ArduCopter/mode_land.cpp:53", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前名称增加米单位后缀。"},
    ("ArduPilot", "PILOT_ACCEL_Z"): {"current_name": "PILOT_ACC_Z", "evidence": "baseline/ardupilot/ArduCopter/Parameters.cpp:1344", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前参数缩写为 ACC。"},
    ("ArduPilot", "PILOT_TKOFF_ALT"): {"current_name": "PILOT_TKO_ALT_M", "evidence": "baseline/ardupilot/ArduCopter/Parameters.cpp:1344", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前名称增加米单位并调整起飞缩写。"},
    ("ArduPilot", "PSC_POSZ_P"): {"current_name": "PSC_D_POS_P", "evidence": "baseline/ardupilot/libraries/AC_AttitudeControl/AC_PosControl.cpp:96", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前源码注释明确记录以前名称为 POSZ_P。"},
    ("ArduPilot", "RTL_ALT"): {"current_name": "RTL_ALT_M", "evidence": "baseline/ardupilot/ArduCopter/mode_rtl.cpp:54", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前名称增加米单位后缀；旧值常用厘米，不能直接沿用数值。"},
    ("ArduPilot", "RTL_ALT_FINAL"): {"current_name": "RTL_ALT_FINAL_M", "evidence": "baseline/ardupilot/ArduCopter/mode_rtl.cpp:54", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前名称增加米单位后缀；旧值常用厘米。"},
    ("ArduPilot", "LAND_SPEED_HIGH"): {"current_name": "LAND_SPD_HIGH_MS", "evidence": "baseline/ardupilot/ArduCopter/mode_land.cpp:15", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前名称明确为米每秒的高空着陆速度。"},
    ("ArduPilot", "LAND_SPEED"): {"current_name": "LAND_SPD_MS", "evidence": "baseline/ardupilot/ArduCopter/mode_land.cpp:6", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前名称明确为米每秒的着陆速度。"},
    ("ArduPilot", "PILOT_SPEED_UP"): {"current_name": "PILOT_SPD_UP", "evidence": "baseline/ardupilot/ArduCopter/Parameters.cpp:1142", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前参数缩短 SPEED 为 SPD。"},
    ("ArduPilot", "SIM_GPS_NUMSATS"): {"current_name": "SIM_GPS1_NUMSATS", "evidence": "baseline/ardupilot/libraries/SITL/SIM_GPS.cpp:65", "confidence": "CURATED_RENAME_EXACT", "note_zh": "当前仿真参数显式区分第一 GPS 实例。"},
    ("PX4", "MIS_LTRMIN_ALT"): {"current_name": "NAV_MIN_LTR_ALT", "evidence": "baseline/px4/src/modules/navigator/navigator_params.c:178", "confidence": "CURATED_MIGRATION_MODELLED", "note_zh": "当前 Navigator 有语义相近的最小盘旋高度参数；冻结仓库没有本地历史证明它是一对一重命名，因此只保留为建模迁移。"},
}

ARDUPILOT_INSTANCE1_ALIASES = {
    "SIM_ACCEL_FAIL": "SIM_ACCEL1_FAIL",
    "SIM_ACC_BIAS_X": "SIM_ACC1_BIAS_X",
    "SIM_ACC_BIAS_Y": "SIM_ACC1_BIAS_Y",
    "SIM_ACC_BIAS_Z": "SIM_ACC1_BIAS_Z",
    "SIM_ACC_RND": "SIM_ACC1_RND",
    "SIM_ARSPD_FAIL_P": "SIM_ARSPD_FAILP",
    "SIM_GPS_ALT_OFS": "SIM_GPS1_ALT_OFS",
    "SIM_GPS_BYTELOSS": "SIM_GPS1_BYTELOS",
    "SIM_GPS_DRIFTALT": "SIM_GPS1_DRFTALT",
    "SIM_GPS_GLITCH_Z": "SIM_GPS1_GLTCH_Z",
    "SIM_GPS_HDG": "SIM_GPS1_HDG",
    "SIM_GPS_LOCKTIME": "SIM_GPS1_LCKTIME",
    "SIM_GPS_NOISE": "SIM_GPS1_NOISE",
    "SIM_GPS_POS_X": "SIM_GPS1_POS_X",
    "SIM_GPS_POS_Y": "SIM_GPS1_POS_Y",
    "SIM_GPS_POS_Z": "SIM_GPS1_POS_Z",
    "SIM_GPS_TYPE": "SIM_GPS1_TYPE",
    "SIM_GYR_RND": "SIM_GYR1_RND",
    "SIM_GYR_SCALE_X": "SIM_GYR1_SCALE_X",
    "SIM_GYR_SCALE_Y": "SIM_GYR1_SCALE_Y",
    "SIM_GYR_SCALE_Z": "SIM_GYR1_SCALE_Z",
    "SIM_MAG_DIA_X": "SIM_MAG1_DIA_X",
    "SIM_MAG_DIA_Y": "SIM_MAG1_DIA_Y",
    "SIM_MAG_DIA_Z": "SIM_MAG1_DIA_Z",
    "SIM_MAG_ODI_X": "SIM_MAG1_ODI_X",
    "SIM_MAG_ODI_Y": "SIM_MAG1_ODI_Y",
    "SIM_MAG_ODI_Z": "SIM_MAG1_ODI_Z",
    "SIM_MAG_OFS_X": "SIM_MAG1_OFS_X",
    "SIM_MAG_OFS_Y": "SIM_MAG1_OFS_Y",
    "SIM_MAG_OFS_Z": "SIM_MAG1_OFS_Z",
    "SIM_MAG_ORIENT": "SIM_MAG1_ORIENT",
    "SIM_MAG_SCALING": "SIM_MAG1_SCALING",
}
for historical_name, current_name in ARDUPILOT_INSTANCE1_ALIASES.items():
    ALIASES[("ArduPilot", historical_name)] = {
        "current_name": current_name,
        "evidence": "current instance-qualified SITL parameter family",
        "confidence": "CURATED_INSTANCE1_MIGRATION_MODELLED",
        "note_zh": "当前参数显式区分传感器实例；映射到第一实例有名称和参数族证据，但未发现逐项历史迁移记录。",
    }


def extra_definition(
    source: str,
    parameter_type: str,
    default: str,
    minimum: str = "",
    maximum: str = "",
    units: str = "",
) -> dict[str, str]:
    return {
        "source_locations": source,
        "type": parameter_type,
        "default": default,
        "minimum": minimum,
        "maximum": maximum,
        "increment": "",
        "units": units,
        "reboot_required": "",
        "build_inclusion_status": "confirmed_by_frozen_runtime_snapshot",
        "mavlink_parameter_transport": "observed_in_frozen_runtime_parameter_download",
        "source_location_confidence": "exact_definition_curated",
    }


# The broad parameter catalog intentionally missed YAML/template-generated PX4
# definitions.  These six additions are grounded in the frozen source and the
# complete runtime parameter download rather than inferred from name similarity.
EXTRA_PARAM_DEFINITIONS: dict[tuple[str, str], dict[str, str]] = {
    ("PX4", "COM_FLTMODE1"): extra_definition("baseline/px4/src/modules/commander/module.yaml:18", "enum", "-1"),
    ("PX4", "EKF2_BARO_NOISE"): extra_definition("baseline/px4/src/modules/ekf2/params_barometer.yaml:33", "float", "3.5", "0.01", "15.0", "m"),
    ("PX4", "EKF2_GPS_CTRL"): extra_definition("baseline/px4/src/modules/ekf2/params_gnss.yaml:5", "bitmask", "7", "0", "15"),
    ("PX4", "EKF2_RNG_A_HMAX"): extra_definition("baseline/px4/src/modules/ekf2/params_range_finder.yaml:75", "float", "5.0", "1.0", "10.0", "m"),
    ("PX4", "EKF2_RNG_CTRL"): extra_definition("baseline/px4/src/modules/ekf2/params_range_finder.yaml:5", "enum", "1"),
    ("PX4", "EKF2_TERR_NOISE"): extra_definition("baseline/px4/src/modules/ekf2/params_terrain.yaml:5", "float", "5.0", "0.5", "", "m/s"),
}

REMOVED_NOTES = {
    ("ArduPilot", "RNGFND_GAIN"): "当前只发现弃用槽位，没有可证明等价的现行参数。",
    ("PX4", "COM_POS_FS_DELAY"): "该参数在 PX4 1.16 发行说明中已删除，不能自动用其他估计器超时参数替代。",
}

FORMULA_PARAMETERS = {
    "A.RTL1": ["RTL_ALT"],
    "A.RTL2": ["RTL_ALT"],
    "A.RTL3": ["RTL_ALT"],
    "A.LAND1": ["LAND_SPEED_HIGH"],
    "A.LAND2": ["LAND_SPEED"],
    "A.DRIFT1": ["FS_EKF_ACTION"],
    "A.SPORT1": ["PILOT_SPEED_UP"],
    "A.RC.FS1": ["FS_THR_VALUE"],
    "A.RC.FS2": ["FS_THR_VALUE"],
    "A.CHUTE1": ["CHUTE_ALT_MIN"],
    "PX.RTL1": ["RTL_RETURN_ALT"],
    "PX.RTL2": ["RTL_RETURN_ALT"],
    "PX.RTL3": ["RTL_RETURN_ALT"],
    "PX.RTL4": ["RTL_DESCEND_ALT", "RTL_LAND_DELAY"],
    "PX.LAND1": ["MPC_LAND_SPEED"],
    "PX.HOLD2": ["MIS_LTRMIN_ALT"],
    "PX.TAKEOFF1": ["MIS_TAKEOFF_ALT"],
    "PX.TAKEOFF2": ["MPC_TKO_SPEED"],
    "PX.GPS.FS1": ["COM_POS_FS_DELAY"],
}


# Formula-direct ArduPilot defaults are resolved only where the frozen source
# contains a direct literal macro or enum definition.  The broad legacy
# catalog sometimes retains one macro-call closing parenthesis; both the raw
# catalog expression and this curated evidence are kept in output.
CURATED_CURRENT_DEFAULTS: dict[tuple[str, str], dict[str, str]] = {
    ("ArduPilot", "RTL_ALT_M"): {
        "value": "15",
        "source": "baseline/ardupilot/ArduCopter/config.h:428",
        "note_zh": "RTL_ALT_M_DEFAULT 在冻结源码中直接定义为 15 米。",
    },
    ("ArduPilot", "LAND_SPD_HIGH_MS"): {
        "value": "0",
        "source": "baseline/ardupilot/ArduCopter/mode_land.cpp:22",
        "note_zh": "参数定义调用中的默认实参直接为 0 米/秒。",
    },
    ("ArduPilot", "LAND_SPD_MS"): {
        "value": "0.5",
        "source": "baseline/ardupilot/ArduCopter/config.h:331",
        "note_zh": "LAND_SPD_MS_DEFAULT 在冻结源码中直接定义为 0.5 米/秒。",
    },
    ("ArduPilot", "FS_EKF_ACTION"): {
        "value": "1",
        "source": "baseline/ardupilot/ArduCopter/config.h:112",
        "note_zh": "默认宏为 FS_EKF_Action::LAND；该冻结枚举值对应 1，运行快照也为 1。",
    },
    ("ArduPilot", "PILOT_SPD_UP"): {
        "value": "2.5",
        "source": "baseline/ardupilot/ArduCopter/config.h:523",
        "note_zh": "PILOT_SPD_UP_DEFAULT 在冻结源码中直接定义为 2.5 米/秒。",
    },
    ("ArduPilot", "FS_THR_VALUE"): {
        "value": "975",
        "source": "baseline/ardupilot/ArduCopter/config.h:316",
        "note_zh": "FS_THR_VALUE_DEFAULT 在冻结源码中直接定义为 975 微秒 PWM。",
    },
    ("ArduPilot", "CHUTE_ALT_MIN"): {
        "value": "10",
        "source": "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.h:24",
        "note_zh": "AP_PARACHUTE_ALT_MIN_DEFAULT 在冻结源码中直接定义为 10 米。",
    },
}


def normalize_catalog_default(system: str, value: str) -> str:
    """Remove only the known extra outer macro parenthesis from ArduPilot rows."""
    if system == "ArduPilot" and value.endswith(")"):
        return value[:-1].rstrip()
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def unique_join(values, separator: str = "|") -> str:
    return separator.join(sorted({str(value) for value in values if value not in (None, "")}))


def choose_param_rows(rows: list[dict[str, str]], system: str, name: str) -> list[dict[str, str]]:
    matches = [row for row in rows if row["system"] == system and row["name"] == name]
    if system == "ArduPilot":
        matches = [row for row in matches if row["vehicle_scope"] == "Copter"]
    return matches


def choose_runtime_rows(rows: list[dict[str, str]], system: str, name: str) -> list[dict[str, str]]:
    matches = [row for row in rows if row["system"] == system and row["name"] == name]
    if system == "ArduPilot":
        matches = [row for row in matches if row["vehicle"] == "ArduCopter"]
    elif system == "PX4":
        matches = [row for row in matches if row["vehicle"] == "multicopter"]
    return matches


def parse_line(input_class: str, raw: str) -> dict[str, str]:
    base = {
        "artifact_name": "",
        "artifact_reboot_raw": "",
        "artifact_default_raw": "",
        "artifact_min_raw": "",
        "artifact_max_raw": "",
        "artifact_column_6_raw": "",
        "artifact_numeric_id_raw": "",
        "artifact_precondition_value_raw": "",
    }
    if input_class == "InputP":
        fields = next(csv.reader([raw]))
        if len(fields) != 6:
            raise ValueError(f"expected six parameter columns: {raw!r}")
        base.update({
            "artifact_name": fields[0],
            "artifact_reboot_raw": fields[1],
            "artifact_default_raw": fields[2],
            "artifact_min_raw": fields[3],
            "artifact_max_raw": fields[4],
            "artifact_column_6_raw": fields[5],
        })
    elif input_class == "InputC":
        fields = next(csv.reader([raw]))
        if len(fields) != 2:
            raise ValueError(f"expected two command columns: {raw!r}")
        base.update({"artifact_name": fields[0], "artifact_numeric_id_raw": fields[1]})
    elif input_class == "InputE":
        base["artifact_name"] = raw
    else:
        fields = raw.split(None, 1)
        if len(fields) != 2:
            raise ValueError(f"expected precondition name and value: {raw!r}")
        base.update({"artifact_name": fields[0], "artifact_precondition_value_raw": fields[1]})
    return base


def bind_identity(
    system: str,
    input_class: str,
    name: str,
    artifact_numeric_id: str,
    param_rows: list[dict[str, str]],
    command_rows: list[dict[str, str]],
    runtime_rows: list[dict[str, str]],
) -> dict[str, str]:
    result = {
        "current_identity_status": "",
        "current_name": name,
        "current_match_confidence": "",
        "current_alias_evidence": "",
        "current_alias_note_zh": "",
        "current_source_locations": "",
        "current_source_location_confidence": "",
        "current_type": "",
        "current_default_raw_catalog": "",
        "current_default": "",
        "current_default_evidence_status": "UNKNOWN",
        "current_default_evidence_source": "",
        "current_default_evidence_note_zh": "当前目录没有可用默认值证据。",
        "current_minimum": "",
        "current_maximum": "",
        "current_increment": "",
        "current_units": "",
        "current_reboot_required": "",
        "current_build_inclusion_status": "",
        "current_mavlink_parameter_transport": "",
        "current_runtime_value": "",
        "current_runtime_profile": "",
        "current_runtime_capture": "",
        "runtime_write_change_verification": "NOT_TESTED",
        "current_command_id": "",
        "command_id_consistency": "NOT_APPLICABLE",
        "current_command_description": "",
        "current_command_origin": "",
        "identity_limit_zh": "",
    }
    if input_class == "InputC":
        if name == "Flight_Mode" or (name.startswith("RC") and name[2:].isdigit()):
            result.update({
                "current_identity_status": "SPECIAL_CONTROL_INPUT",
                "current_match_confidence": "MODELLED_SPECIAL_INPUT",
                "identity_limit_zh": "这是 PGFuzz 自定义输入编码；后续必须绑定到当前模式或遥控接收路径，不能把数字直接当当前枚举。",
            })
            return result
        matches = [row for row in command_rows if row["system"] == system and row["command_name"] == name]
        if not matches:
            result.update({
                "current_identity_status": "COMMAND_XML_DEFINITION_NOT_FOUND",
                "current_match_confidence": "UNRESOLVED",
                "identity_limit_zh": "当前固定 MAVLink XML 未找到同名命令；没有据此猜测替代命令。",
            })
            return result
        ids = unique_join(row["command_id"] for row in matches)
        result.update({
            "current_identity_status": "COMMAND_XML_DEFINITION_FOUND",
            "current_match_confidence": "EXACT_NAME_XML_DEFINITION",
            "current_command_id": ids,
            "command_id_consistency": "MATCH" if ids == artifact_numeric_id else "MISMATCH_OR_MULTIPLE",
            "current_command_description": unique_join((row["command_description"] for row in matches), " || "),
            "current_command_origin": unique_join(f"{row['origin_xml']}:{row['origin_line']}" for row in matches),
            "identity_limit_zh": "只确认协议 XML 定义；未由此证明当前飞控构建接受、执行或影响该性质。",
        })
        return result

    alias = ALIASES.get((system, name))
    lookup_name = alias["current_name"] if alias else name
    matches = choose_param_rows(param_rows, system, lookup_name)
    if not matches and (system, lookup_name) in EXTRA_PARAM_DEFINITIONS:
        matches = [EXTRA_PARAM_DEFINITIONS[(system, lookup_name)]]
    runtime = choose_runtime_rows(runtime_rows, system, lookup_name)
    result["current_name"] = lookup_name
    if matches:
        raw_source_locations = unique_join(row["source_locations"] for row in matches)
        alias_evidence = alias["evidence"] if alias else ""
        alias_evidence_path = alias_evidence.rsplit(":", 1)[0] if alias_evidence.startswith("baseline/") else ""
        matched_source_paths = {
            location.rsplit(":", 1)[0]
            for row in matches
            for location in row["source_locations"].split("|")
            if ":" in location
        }
        metadata_trusted = not alias_evidence_path or alias_evidence_path in matched_source_paths
        effective_matches = matches if metadata_trusted else []
        effective_source_locations = (
            unique_join([raw_source_locations, alias_evidence])
            if metadata_trusted and alias_evidence.startswith("baseline/")
            else alias_evidence
            if alias_evidence.startswith("baseline/")
            else raw_source_locations
        )
        raw_defaults = unique_join(row["default"] for row in effective_matches)
        normalized_defaults = unique_join(
            normalize_catalog_default(system, row["default"]) for row in effective_matches
        )
        curated_default = CURATED_CURRENT_DEFAULTS.get((system, lookup_name))
        if curated_default:
            current_default = curated_default["value"]
            default_status = "CURATED_FROZEN_SOURCE_RESOLUTION"
            default_source = curated_default["source"]
            default_note = curated_default["note_zh"]
        else:
            current_default = normalized_defaults
            default_status = "SOURCE_METADATA_LITERAL_OR_EXPRESSION" if normalized_defaults else "UNKNOWN"
            default_source = unique_join(row["source_locations"] for row in effective_matches)
            default_note = (
                "保存参数目录解析出的字面值或未求值源码表达式；它不是运行值，宏表达式不能冒充已求值数值。"
                if normalized_defaults
                else "当前目录没有可用默认值证据。"
            )
        result.update({
            "current_identity_status": "RENAMED_CURRENT_DEFINITION" if alias else "EXACT_CURRENT_DEFINITION",
            "current_match_confidence": alias["confidence"] if alias else "EXACT_NAME_DEFINITION",
            "current_alias_evidence": alias["evidence"] if alias else "",
            "current_alias_note_zh": alias["note_zh"] if alias else "",
            "current_source_locations": effective_source_locations,
            "current_source_location_confidence": (
                "curated_alias_evidence"
                if alias_evidence.startswith("baseline/")
                else unique_join(row["source_location_confidence"] for row in effective_matches)
            ),
            "current_type": unique_join(row["type"] for row in effective_matches),
            "current_default_raw_catalog": raw_defaults,
            "current_default": current_default,
            "current_default_evidence_status": default_status,
            "current_default_evidence_source": default_source,
            "current_default_evidence_note_zh": default_note,
            "current_minimum": unique_join(row["minimum"] for row in effective_matches),
            "current_maximum": unique_join(row["maximum"] for row in effective_matches),
            "current_increment": unique_join(row["increment"] for row in effective_matches),
            "current_units": unique_join(row["units"] for row in effective_matches),
            "current_reboot_required": unique_join(row["reboot_required"] for row in effective_matches),
            "current_build_inclusion_status": (
                "confirmed_by_frozen_runtime_snapshot"
                if runtime
                else unique_join(row["build_inclusion_status"] for row in effective_matches)
            ),
            "current_mavlink_parameter_transport": (
                "observed_in_frozen_runtime_parameter_download"
                if runtime
                else unique_join(row["mavlink_parameter_transport"] for row in effective_matches)
            ),
            "current_runtime_value": unique_join(row["decoded_value"] for row in runtime),
            "current_runtime_profile": unique_join(row["profile"] for row in runtime),
            "current_runtime_capture": unique_join(row["capture_id"] for row in runtime),
            "identity_limit_zh": (
                "参数更名证据已找到，但参数目录匹配位置与更名证据不在同一源码文件；为避免同后缀误配，默认值、范围、类型和单位留空。运行快照值仍单独保留。"
                if not metadata_trusted
                else "参数身份和定义位置已找到；这不证明它与该性质存在真实数据依赖，也未执行写入变更测试。"
            ),
        })
    else:
        result.update({
            "current_identity_status": "CURRENT_DEFINITION_NOT_FOUND",
            "current_match_confidence": "UNRESOLVED",
            "current_alias_evidence": alias["evidence"] if alias else "",
            "current_alias_note_zh": alias["note_zh"] if alias else "",
            "identity_limit_zh": REMOVED_NOTES.get((system, name), "当前冻结参数目录中没有找到可信同名或重命名定义；没有使用字符串相似度猜测。"),
        })
    return result


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_summary(payload: dict[str, object], coverage_rows: list[dict[str, object]]) -> str:
    counts = payload["counts"]
    lines = [
        "# PGFuzz 作者依赖输入清单",
        "",
        "本清单把论文制品中的每一行配置参数、命令、环境输入和前置条件展开到 51 条逻辑性质。它保存作者关联，但不把关联升级为已证明的数据依赖。",
        "",
        "## 术语与状态",
        "",
    ]
    for name, meaning in CLASS_DEFS.items():
        lines.append(f"- `{name}`：{meaning}")
    for name, meaning in DEPENDENCY_STRENGTH_DEFS.items():
        lines.append(f"- `{name}`：{meaning}")
    for name, meaning in STATUS_DEFS.items():
        lines.append(f"- `{name}`：{meaning}")
    lines.extend([
        "- `NOT_TESTED`：未测试；这里专指没有通过当前仿真执行参数写入并验证行为变化。",
        "- `NOT_ASSESSED`：未评估；没有判断当前固件是否满足论文性质。",
        "",
        "## 规模",
        "",
        f"- 展开后的性质—输入关联共 {counts['association_rows']} 行。",
        f"- ArduPilot 为 {counts['ArduPilot']['association_rows']} 行，PX4 为 {counts['PX4']['association_rows']} 行。",
        f"- 去重后的系统—输入身份共 {counts['unique_identity_rows']} 行。",
        "- 同一个制品目录可能服务多条论文性质；清单保留共享目录和原始行号，因此不会把复制列表误当成独立分析结果。",
        "",
        "## 参数第六列警告",
        "",
        "PGFuzz 的 `read_inputs.py` 把第六列命名为 `param_units`，中文意为“参数单位”；但文件中大量值为 `0.1`、`1`、`10`，而 XML 解析说明又提到 increment（参数增量）。本数据集只保存 `artifact_column_6_raw` 原值，不把它擅自解释为物理单位。当前单位和增量分别取自当前冻结源码参数元数据。",
        "作者参数原值中的 `TRUE` 是第二列的旧制品“需要重启”标记；`X` 是公开读取代码未进一步定义的占位符，不能解释为 0、假、任意范围或具体单位。覆盖表中的 `True/False` 只表示作者参数文件列出/未列出公式词项。",
        "",
        "## 各系统与输入类别计数",
        "",
        "| 系统 | 类别 | 关联行数 | 去重输入数 |",
        "|---|---|---:|---:|",
    ])
    for system in ("ArduPilot", "PX4"):
        for input_class in ("InputP", "InputC", "InputE", "PRECONDITION"):
            row = counts[system][input_class]
            lines.append(f"| {system} | `{input_class}` | {row['rows']} | {row['unique_names']} |")
    lines.extend([
        "",
        "## 公式直接参数是否出现在作者依赖文件",
        "",
        "| 系统 | 性质 | 公式参数 | 作者参数文件包含 | 当前身份状态 | 当前名称 | 当前实际仿真值 |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in coverage_rows:
        lines.append(
            f"| {row['system']} | `{row['policy_id']}` | `{row['formula_parameter']}` | "
            f"{row['present_in_author_input_files']} | `{row['current_identity_status']}` | "
            f"`{row['current_name']}` | `{row['current_runtime_value'] or '未观测'}` |"
        )
    lines.extend([
        "",
        "## 判断边界",
        "",
        "- 参数定义存在，只回答“当前源码里叫什么、在哪里定义、默认/范围是什么”；不回答它是否影响某条性质。",
        "- 当前仿真值只来自冻结参数快照；参数一般可经协议读取，是否可在飞行中修改、是否需重启以及修改后何时生效，必须逐参数依据元数据和运行测试判断。",
        "- 命令存在于协议 XML，只证明协议定义存在；不证明当前构建处理该命令。",
        "- `preconditions.txt` 为空，只说明公开制品没有写前置设置；不说明真实模式、传感器、坐标或数据新鲜度前置条件不存在。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    formula_payload = json.loads((DATASET_ROOT / "table_xii_formula_inventory.json").read_text(encoding="utf-8"))
    policies = formula_payload["policies"]
    param_rows = load_csv(PARAM_CATALOG)
    command_rows = load_csv(COMMAND_CATALOG)
    runtime_rows = load_csv(RUNTIME_CATALOG)

    artifact_dir_counts = Counter((p["system"], p["artifact_policy_directory"]) for p in policies)
    rows: list[dict[str, object]] = []
    file_groups: dict[str, set[str]] = defaultdict(set)
    for policy in policies:
        system = policy["system"]
        system_dir = "ArduPilot" if system == "ArduPilot" else "PX4"
        formula_terms = {term for atom in policy["atomic_propositions"] for term in formula_payload_term_lookup(atom["expression"], formula_payload)}
        for input_class, filename in (("InputP", "parameters.txt"), ("InputC", "cmds.txt"), ("InputE", "envs.txt"), ("PRECONDITION", "preconditions.txt")):
            path = PGFUZZ_ROOT / system_dir / "policies" / policy["artifact_policy_directory"] / filename
            digest = sha256(path)
            file_groups[f"{system}:{input_class}:{digest[:16]}"].add(policy["policy_id"])
            for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not raw.strip():
                    continue
                parsed = parse_line(input_class, raw)
                identity = bind_identity(
                    system, input_class, parsed["artifact_name"], parsed["artifact_numeric_id_raw"],
                    param_rows, command_rows, runtime_rows,
                )
                row = {
                    "association_id": f"{policy['policy_id']}:{input_class}:{line_number:04d}",
                    "system": system,
                    "policy_id": policy["policy_id"],
                    "artifact_policy_directory": policy["artifact_policy_directory"],
                    "shared_artifact_directory_policy_count": artifact_dir_counts[(system, policy["artifact_policy_directory"])],
                    "input_class": input_class,
                    "input_class_zh": CLASS_DEFS[input_class],
                    "artifact_source_path": rel(path),
                    "artifact_source_line": line_number,
                    "artifact_file_sha256": digest,
                    "artifact_raw": raw,
                    **parsed,
                    "artifact_column_6_interpretation": "AUTHOR_PARSER_CALLS_UNITS_BUT_ARTIFACT_VALUES_MAY_BE_INCREMENT",
                    "appears_as_exact_formula_term": parsed["artifact_name"] in formula_terms,
                    "dependency_evidence": "PGFUZZ_ARTIFACT_ASSOCIATION",
                    "dependency_strength": "EXPLICIT_PRECONDITION" if input_class == "PRECONDITION" else "CANDIDATE_ASSOCIATION",
                    "dependency_claim_limit_zh": DEPENDENCY_STRENGTH_DEFS["EXPLICIT_PRECONDITION" if input_class == "PRECONDITION" else "CANDIDATE_ASSOCIATION"],
                    **identity,
                    "implementation_satisfaction": "NOT_ASSESSED",
                }
                rows.append(row)

    identity_groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        identity_groups[(str(row["system"]), str(row["input_class"]), str(row["artifact_name"]))].append(row)
    identity_rows: list[dict[str, object]] = []
    for (system, input_class, name), group in sorted(identity_groups.items()):
        first = group[0]
        identity_rows.append({
            "system": system,
            "input_class": input_class,
            "artifact_name": name,
            "association_occurrences": len(group),
            "policies": unique_join(row["policy_id"] for row in group),
            "artifact_raw_variants": unique_join((row["artifact_raw"] for row in group), " || "),
            "artifact_source_files": unique_join(row["artifact_source_path"] for row in group),
            "current_identity_status": first["current_identity_status"],
            "current_name": first["current_name"],
            "current_match_confidence": first["current_match_confidence"],
            "current_alias_evidence": first["current_alias_evidence"],
            "current_alias_note_zh": first["current_alias_note_zh"],
            "current_source_locations": first["current_source_locations"],
            "current_source_location_confidence": first["current_source_location_confidence"],
            "current_type": first["current_type"],
            "current_default_raw_catalog": first["current_default_raw_catalog"],
            "current_default": first["current_default"],
            "current_default_evidence_status": first["current_default_evidence_status"],
            "current_default_evidence_source": first["current_default_evidence_source"],
            "current_default_evidence_note_zh": first["current_default_evidence_note_zh"],
            "current_minimum": first["current_minimum"],
            "current_maximum": first["current_maximum"],
            "current_increment": first["current_increment"],
            "current_units": first["current_units"],
            "current_reboot_required": first["current_reboot_required"],
            "current_build_inclusion_status": first["current_build_inclusion_status"],
            "current_mavlink_parameter_transport": first["current_mavlink_parameter_transport"],
            "current_runtime_value": first["current_runtime_value"],
            "current_runtime_profile": first["current_runtime_profile"],
            "current_runtime_capture": first["current_runtime_capture"],
            "runtime_write_change_verification": "NOT_TESTED",
            "current_command_id": first["current_command_id"],
            "command_id_consistency": first["command_id_consistency"],
            "current_command_origin": first["current_command_origin"],
            "identity_limit_zh": first["identity_limit_zh"],
            "implementation_satisfaction": "NOT_ASSESSED",
        })

    coverage_rows: list[dict[str, object]] = []
    for policy_id, names in FORMULA_PARAMETERS.items():
        policy = next(p for p in policies if p["policy_id"] == policy_id)
        for name in names:
            group = [row for row in rows if row["policy_id"] == policy_id and row["artifact_name"] == name]
            identity = bind_identity(policy["system"], "InputP", name, "", param_rows, command_rows, runtime_rows)
            coverage_rows.append({
                "system": policy["system"],
                "policy_id": policy_id,
                "formula_parameter": name,
                "present_in_author_input_files": bool(group),
                "author_input_classes": unique_join(row["input_class"] for row in group),
                **identity,
                "implementation_satisfaction": "NOT_ASSESSED",
            })

    counts: dict[str, object] = {
        "association_rows": len(rows),
        "unique_identity_rows": len(identity_rows),
        "formula_parameter_coverage_rows": len(coverage_rows),
    }
    for system in ("ArduPilot", "PX4"):
        system_rows = [row for row in rows if row["system"] == system]
        system_counts: dict[str, object] = {"association_rows": len(system_rows)}
        for input_class in ("InputP", "InputC", "InputE", "PRECONDITION"):
            class_rows = [row for row in system_rows if row["input_class"] == input_class]
            system_counts[input_class] = {"rows": len(class_rows), "unique_names": len({row["artifact_name"] for row in class_rows})}
        system_counts["association_identity_statuses"] = dict(sorted(Counter(row["current_identity_status"] for row in system_rows).items()))
        system_counts["unique_identity_statuses"] = dict(sorted(Counter(row["current_identity_status"] for row in identity_rows if row["system"] == system).items()))
        counts[system] = system_counts

    payload = {
        "schema_version": "1.0",
        "scope": "PGFuzz Table XII ArduPilot 30 plus PX4 21 logical policies",
        "class_definitions": CLASS_DEFS,
        "status_definitions": STATUS_DEFS,
        "dependency_strength_definitions": DEPENDENCY_STRENGTH_DEFS,
        "counts": counts,
        "source_catalogs": {
            "formula_inventory": "benchmark/PGFuzz_MTL51/table_xii_formula_inventory.json",
            "current_parameters": rel(PARAM_CATALOG),
            "current_commands": rel(COMMAND_CATALOG),
            "runtime_parameters": rel(RUNTIME_CATALOG),
        },
        "association_rows": rows,
    }

    write_csv(DATASET_ROOT / "author_input_dependencies.csv", rows)
    (DATASET_ROOT / "author_input_dependencies.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(DATASET_ROOT / "current_input_identity_map.csv", identity_rows)
    (DATASET_ROOT / "current_input_identity_map.json").write_text(json.dumps({"schema_version": "1.0", "rows": identity_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(DATASET_ROOT / "formula_parameter_coverage.csv", coverage_rows)
    (DATASET_ROOT / "formula_parameter_coverage.json").write_text(json.dumps({"schema_version": "1.0", "rows": coverage_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATASET_ROOT / "author_dependency_summary.md").write_text(render_summary(payload, coverage_rows), encoding="utf-8")

    for system in ("ArduPilot", "PX4"):
        system_rows = [row for row in rows if row["system"] == system]
        system_identity = [row for row in identity_rows if row["system"] == system]
        write_csv(DATASET_ROOT / system / "author_input_dependencies.csv", system_rows)
        (DATASET_ROOT / system / "author_input_dependencies.json").write_text(json.dumps({"schema_version": "1.0", "rows": system_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(DATASET_ROOT / system / "current_input_identity_map.csv", system_identity)
        (DATASET_ROOT / system / "current_input_identity_map.json").write_text(json.dumps({"schema_version": "1.0", "rows": system_identity}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


def formula_payload_term_lookup(expression: str, formula_payload: dict[str, object]) -> list[str]:
    # AP definitions are stored in the deterministic builder rather than the
    # generated JSON.  The expression token check below retains exact parameter
    # names and deliberately avoids fuzzy matching.
    known = {name for names in FORMULA_PARAMETERS.values() for name in names}
    return [name for name in known if name in expression]


if __name__ == "__main__":
    main()
