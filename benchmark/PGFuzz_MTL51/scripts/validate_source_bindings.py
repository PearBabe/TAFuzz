#!/usr/bin/env python3
"""Validate PGFuzz-MTL51 current-source term and AP binding artifacts.

This gate checks deterministic serialization, cross-file references, frozen
source locations, and explicit unresolved/history semantics.  Passing it does
not establish that either firmware satisfies a historical PGFuzz property.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = DATASET_ROOT / "scripts" / "build_source_bindings.py"
REPORT_PATH = DATASET_ROOT / "validation" / "source_binding_validation.json"

EXPECTED_COMMITS = {
    "ArduPilot": "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
    "PX4": "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
}
MANIFEST_SOURCE_KEYS = {"ArduPilot": "ardupilot", "PX4": "px4"}
EXPECTED_TERM_BINDING_ROWS = {"ArduPilot": 110, "PX4": 117}
EXPECTED_SYSTEM_TERMS = {"ArduPilot": 67, "PX4": 40}
EXPECTED_AP_STATUS_COUNTS = {"EXACT": 57, "MODELLED": 107, "UNRESOLVED": 14}
EXPECTED_TYPE_UNIT_COUNTS = {
    "data_type": 100,
    "unit_coordinate": 61,
    "current_input_type": 7,
    "current_input_unit": 28,
}

# Avoid producing a cache artifact when the validator imports the deterministic
# builder solely for an in-memory comparison.
sys.dont_write_bytecode = True

VALID_CONFIDENCE = {"EXACT", "MODELLED", "UNRESOLVED"}
VALID_OBSERVABILITY = {
    "DIRECT",
    "DERIVED",
    "CONDITIONAL",
    "INSTRUMENTATION_REQUIRED",
    "UNRESOLVED",
}
VALID_AP_STATUS = {"EXACT", "MODELLED", "UNRESOLVED"}
VALID_BINDING_ROLES = {"PRIMARY_VALUE", "SUPPORTING_EVIDENCE", "ALTERNATIVE_SEMANTICS"}
VALID_SELECTION_STATUS = {"PRIMARY_SELECTED", "PRIMARY_WITH_ALTERNATIVES", "UNRESOLVED_PRIMARY"}
VALID_HISTORICAL_RELATIONS = {
    "NOT_APPLICABLE",
    "EXACT_SAME_NAME",
    "RENAMED_AND_SCALED_0.01",
    "SEMANTIC_SUCCESSOR_NOT_PROVEN_RENAME",
    "REMOVED_NO_EQUIVALENT",
    "NON_EQUIVALENT_CANDIDATE",
}

EXPECTED_PREVIOUS_TERMS = {
    "ArduPilot": {
        "Mode_t-1",
        "ALT_t-1",
        "Pos_t-1",
        "Yaw_t-1",
        "Circle_radius_t-1",
        "Circle_speed_t-1",
        "RC_throttle_t-1",
        "RC_pitch_t-1",
        "RC_roll_t-1",
        "RC_yaw_t-1",
    },
    "PX4": {
        "ALT_t-1",
        "Pos_t-1",
        "Yaw_t-1",
        "Circle_radius_t-1",
        "Circle_speed_t-1",
    },
}

EXPECTED_UNRESOLVED_TERM_ROWS = {
    ("ArduPilot", "GroundALT", "DERIVED_EXPRESSION"),
    ("ArduPilot", "GroundALT", "UNRESOLVED_ABSTRACTION"),
    ("ArduPilot", "GPS_fail", "SEMANTIC_CANDIDATE"),
    ("ArduPilot", "Waypoint", "UNRESOLVED_ABSTRACTION"),
    ("ArduPilot", "k", "UNRESOLVED_BOUND"),
    ("PX4", "GroundALT", "UORB_FIELD"),
    ("PX4", "GroundALT", "UNRESOLVED_ABSTRACTION"),
    ("PX4", "k", "UNRESOLVED_BOUND"),
    ("PX4", "COM_POS_FS_DELAY", "REMOVED_PARAMETER"),
    ("PX4", "COM_POS_FS_DELAY", "NON_EQUIVALENT_CANDIDATE"),
    ("PX4", "COM_POS_FS_DELAY", "PARAMETER_CONSUMER"),
}

EXPECTED_UNRESOLVED_APS = {
    "A.RTL4-AP02",
    "A.FLIP3-AP02",
    "A.FLIP3-AP03",
    "A.FLIP3-AP04",
    "A.BRAKE1-AP02",
    "A.DRIFT1-AP01",
    "A.DRIFT1-AP03",
    "A.GUIDED1-AP02",
    "A.GPS.FS1-AP01",
    "A.GPS.FS2-AP01",
    "PX.GPS.FS1-AP02",
    "PX.GPS.FS2-AP01",
    "PX.GPS.FS3-AP01",
    "PX.RTL5-AP02",
}

AP_BASE_FIELDS = (
    "system",
    "property_id",
    "ap_id",
    "role",
    "expression",
    "truth_meaning_zh",
    "terms",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def csv_projection(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    projected: list[dict[str, str]] = []
    for row in rows:
        projected.append(
            {
                key: "|".join(map(str, value))
                if isinstance(value, list)
                else ""
                if value is None
                else str(value)
                for key, value in row.items()
            }
        )
    return projected


def git_head(path: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_status(path: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.splitlines()


def reconstruct_builder_outputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    spec = importlib.util.spec_from_file_location("pgfuzz_source_binding_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load builder: {BUILDER_PATH}")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.build_ardupilot_rows()
    builder.build_px4_rows()
    counters: dict[str, int] = defaultdict(int)
    ordered_rows: list[dict[str, Any]] = []
    for row in builder.ROWS:
        if not row["selection_note_zh"]:
            row["selection_note_zh"] = {
                "PRIMARY_VALUE": "该行是其候选组的核心真值实体；只有该组被性质选择时才参与判真。",
                "SUPPORTING_EVIDENCE": "该行只说明形成、消费、关联或发送路径，不会单独改善主值的可观测性。",
                "ALTERNATIVE_SEMANTICS": "该行属于互斥替代解释；只有人工切换到本候选组后才参与判真。",
            }[row["binding_role"]]
        counters[row["system"]] += 1
        prefix = "ARD" if row["system"] == "ArduPilot" else "PX4"
        ordered_rows.append(
            {
                "binding_id": f"{prefix}-TB-{counters[row['system']]:03d}",
                **row,
            }
        )
    builder.ROWS[:] = ordered_rows
    ap_rows = builder.build_ap_bindings()
    status_definitions = {
        **builder.CONFIDENCE_ZH,
        **builder.OBSERVABILITY_ZH,
        **builder.BINDING_ROLE_ZH,
        **builder.SELECTION_STATUS_ZH,
        "NOT_ASSESSED": "未评估固件是否满足性质。",
    }
    return ordered_rows, ap_rows, status_definitions


def main() -> None:
    term_payload = load_json(DATASET_ROOT / "term_source_bindings.json")
    ap_payload = load_json(DATASET_ROOT / "atomic_proposition_bindings.json")
    manifest = load_json(DATASET_ROOT / "source_manifest.json")
    inventory_payload = load_json(DATASET_ROOT / "atomic_proposition_inventory.json")
    coverage_payload = load_json(DATASET_ROOT / "formula_parameter_coverage.json")
    identity_payload = load_json(DATASET_ROOT / "current_input_identity_map.json")
    type_unit_payload = load_json(DATASET_ROOT / "TYPE_UNIT_DICTIONARY.json")
    type_unit_markdown = (DATASET_ROOT / "TYPE_UNIT_DICTIONARY.md").read_text(encoding="utf-8")

    term_rows: list[dict[str, Any]] = term_payload["rows"]
    ap_rows: list[dict[str, Any]] = ap_payload["rows"]
    inventory_rows: list[dict[str, Any]] = inventory_payload["rows"]
    coverage_rows: list[dict[str, Any]] = coverage_payload["rows"]
    identity_rows: list[dict[str, Any]] = identity_payload["rows"]
    type_unit_rows: list[dict[str, Any]] = type_unit_payload["rows"]
    term_header, term_csv_rows = load_csv(DATASET_ROOT / "term_source_bindings.csv")
    ap_header, ap_csv_rows = load_csv(DATASET_ROOT / "atomic_proposition_bindings.csv")
    coverage_header, coverage_csv_rows = load_csv(DATASET_ROOT / "formula_parameter_coverage.csv")

    checks = 0
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    check(term_payload.get("schema_version") == "1.0", "词项绑定 JSON schema_version 不是 1.0")
    check(ap_payload.get("schema_version") == "1.0", "原子命题绑定 JSON schema_version 不是 1.0")
    check(coverage_payload.get("schema_version") == "1.0", "参数覆盖 JSON schema_version 不是 1.0")
    check(identity_payload.get("schema_version") == "1.0", "当前输入身份 JSON schema_version 不是 1.0")
    check(type_unit_payload.get("schema_version") == "1.1.0", "类型与单位字典 JSON schema_version 不是 1.1.0")
    check(bool(term_rows), "词项绑定为空")
    check(bool(ap_rows), "原子命题绑定为空")

    expected_type_unit_values = {
        "data_type": {row["data_type"] for row in term_rows},
        "unit_coordinate": {row["unit_coordinate"] for row in term_rows},
        "current_input_type": {row["current_type"] for row in identity_rows},
        "current_input_unit": {row["current_units"] for row in identity_rows},
    }
    check(
        type_unit_payload.get("source_record_counts")
        == {"term_source_bindings": len(term_rows), "current_input_identity_map": len(identity_rows)},
        "类型与单位字典的来源记录数不一致",
    )
    check(
        type_unit_payload.get("category_counts") == EXPECTED_TYPE_UNIT_COUNTS,
        "类型与单位字典的四类统计不一致",
    )
    check(len(type_unit_rows) == sum(EXPECTED_TYPE_UNIT_COUNTS.values()), "类型与单位字典不是 196 行")
    for category, expected_count in EXPECTED_TYPE_UNIT_COUNTS.items():
        check(
            type_unit_payload.get(f"{category}_count") == expected_count,
            f"类型与单位字典 {category}_count 不一致",
        )
    type_unit_pairs = [(row.get("category"), row.get("original")) for row in type_unit_rows]
    check(len(type_unit_pairs) == len(set(type_unit_pairs)), "类型与单位字典存在重复的类别—原值")
    category_order = {category: index for index, category in enumerate(EXPECTED_TYPE_UNIT_COUNTS)}
    check(
        type_unit_pairs
        == sorted(type_unit_pairs, key=lambda item: (category_order.get(str(item[0]), 99), str(item[1]))),
        "类型与单位字典未按类别和原值确定性排序",
    )
    actual_type_unit_values: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(type_unit_rows, start=1):
        category = row.get("category")
        original = row.get("original")
        check(category in EXPECTED_TYPE_UNIT_COUNTS, f"类型与单位字典第 {index} 行类别未知：{category}")
        check(isinstance(original, str), f"类型与单位字典第 {index} 行原值不是字符串")
        check(bool(str(row.get("explanation_zh", "")).strip()), f"类型与单位字典第 {index} 行缺少中文解释")
        check(bool(str(row.get("audit_effect_zh", "")).strip()), f"类型与单位字典第 {index} 行缺少审核作用")
        check(
            str(row.get("explanation_zh", "")) in type_unit_markdown,
            f"类型与单位字典第 {index} 行中文解释未进入 Markdown",
        )
        check(
            str(row.get("audit_effect_zh", "")) in type_unit_markdown,
            f"类型与单位字典第 {index} 行审核作用未进入 Markdown",
        )
        if category in EXPECTED_TYPE_UNIT_COUNTS and isinstance(original, str):
            actual_type_unit_values[category].add(original)
    for category, expected_values in expected_type_unit_values.items():
        check(
            actual_type_unit_values[category] == expected_values,
            f"类型与单位字典未精确覆盖来源字段：{category}",
        )
        check(
            len(expected_values) == EXPECTED_TYPE_UNIT_COUNTS[category],
            f"来源字段唯一值数量改变：{category}",
        )
        check(
            f"## {category} 完整表" in type_unit_markdown,
            f"类型与单位字典 Markdown 缺少完整表：{category}",
        )

    expected_term_header = list(term_rows[0]) if term_rows else []
    expected_ap_header = list(ap_rows[0]) if ap_rows else []
    expected_coverage_header = list(coverage_rows[0]) if coverage_rows else []
    check(term_header == expected_term_header, "词项绑定 CSV 表头与 JSON 字段不一致")
    check(term_csv_rows == csv_projection(term_rows), "词项绑定 CSV 与 JSON 内容不一致")
    check(ap_header == expected_ap_header, "原子命题绑定 CSV 表头与 JSON 字段不一致")
    check(ap_csv_rows == csv_projection(ap_rows), "原子命题绑定 CSV 与 JSON 内容不一致")
    check(coverage_header == expected_coverage_header, "参数覆盖 CSV 表头与 JSON 字段不一致")
    check(coverage_csv_rows == csv_projection(coverage_rows), "参数覆盖 CSV 与 JSON 内容不一致")

    expected_rows, expected_aps, expected_status_definitions = reconstruct_builder_outputs()
    check(term_rows == expected_rows, "词项绑定 JSON 与 build_source_bindings.py 的确定性记录不一致")
    check(ap_rows == expected_aps, "原子命题绑定 JSON 与 build_source_bindings.py 的确定性记录不一致")
    check(
        term_payload.get("status_definitions_zh") == expected_status_definitions,
        "词项绑定状态定义与构建器不一致",
    )

    system_terms = {(row["system"], row["term"]) for row in term_rows}
    term_row_counts = Counter(row["system"] for row in term_rows)
    system_term_counts = Counter(system for system, _ in system_terms)
    check(len(term_rows) == 227, "词项绑定行数不是 227")
    check(
        dict(term_row_counts) == EXPECTED_TERM_BINDING_ROWS,
        "词项绑定行分布不是 ArduPilot 110、PX4 117",
    )
    check(len(system_terms) == 107, "唯一系统—词项数量不是 107")
    check(
        dict(system_term_counts) == EXPECTED_SYSTEM_TERMS,
        "系统—词项分布不是 ArduPilot 67、PX4 40",
    )
    check(len(ap_rows) == 178, "原子命题出现数量不是 178")
    check(len(inventory_rows) == 178, "原子命题清单数量不是 178")
    check(
        dict(Counter(row["binding_status"] for row in ap_rows)) == EXPECTED_AP_STATUS_COUNTS,
        "原子命题绑定状态分布不是 EXACT 57、MODELLED 107、UNRESOLVED 14",
    )

    binding_ids = [row["binding_id"] for row in term_rows]
    ap_ids = [row["ap_id"] for row in ap_rows]
    check(len(binding_ids) == len(set(binding_ids)), "binding_id 不唯一")
    check(len(ap_ids) == len(set(ap_ids)), "ap_id 不唯一")
    for row in term_rows:
        expected_prefix = "ARD" if row["system"] == "ArduPilot" else "PX4"
        check(
            bool(re.fullmatch(r"(?:ARD|PX4)-TB-\d{3}", row["binding_id"])),
            f"binding_id 格式错误：{row['binding_id']}",
        )
        check(
            row["binding_id"].startswith(expected_prefix + "-TB-"),
            f"binding_id 与系统不匹配：{row['binding_id']}",
        )
    for row in ap_rows:
        check(
            bool(re.fullmatch(r".+-AP\d{2}", row["ap_id"])),
            f"ap_id 格式错误：{row['ap_id']}",
        )
        check(
            row["ap_id"].startswith(row["property_id"] + "-AP"),
            f"ap_id 与 property_id 不匹配：{row['ap_id']}",
        )

    expected_status_keys = (
        VALID_CONFIDENCE | VALID_OBSERVABILITY | VALID_BINDING_ROLES | VALID_SELECTION_STATUS | {"NOT_ASSESSED"}
    )
    check(
        set(term_payload.get("status_definitions_zh", {})) == expected_status_keys,
        "状态定义集合不在允许范围",
    )
    for row in term_rows:
        check(row["system"] in EXPECTED_SYSTEM_TERMS, f"未知系统：{row['binding_id']}")
        check(row["confidence"] in VALID_CONFIDENCE, f"未知 confidence：{row['binding_id']}")
        check(row["binding_role"] in VALID_BINDING_ROLES, f"未知 binding_role：{row['binding_id']}")
        check(bool(row["candidate_group"]), f"候选组为空：{row['binding_id']}")
        check(
            row["candidate_group"].startswith(row["term"] + ":"),
            f"候选组与词项不匹配：{row['binding_id']}",
        )
        check(
            row["mavlink_observability"] in VALID_OBSERVABILITY,
            f"未知 mavlink_observability：{row['binding_id']}",
        )
        check(
            row["historical_current_relation"] in VALID_HISTORICAL_RELATIONS,
            f"未知 historical_current_relation：{row['binding_id']}",
        )
        check(
            row["implementation_satisfaction"] == "NOT_ASSESSED",
            f"词项绑定实现满足性越界：{row['binding_id']}",
        )
        check(bool(row["selection_note_zh"].strip()), f"词项绑定缺少选择说明：{row['binding_id']}")
    for row in ap_rows:
        check(row["system"] in EXPECTED_SYSTEM_TERMS, f"未知原子命题系统：{row['ap_id']}")
        check(row["binding_status"] in VALID_AP_STATUS, f"未知 binding_status：{row['ap_id']}")
        check(
            row["binding_selection_status"] in VALID_SELECTION_STATUS,
            f"未知 binding_selection_status：{row['ap_id']}",
        )
        check(
            row["mavlink_observability"] in VALID_OBSERVABILITY,
            f"未知原子命题 mavlink_observability：{row['ap_id']}",
        )
        check(
            row["implementation_satisfaction"] == "NOT_ASSESSED",
            f"原子命题实现满足性越界：{row['ap_id']}",
        )
        check(
            bool(row["binding_selection_reason_zh"].strip()),
            f"原子命题缺少语义组选择理由：{row['ap_id']}",
        )
    check(
        manifest.get("implementation_satisfaction") == "NOT_ASSESSED",
        "source_manifest 实现满足性不是 NOT_ASSESSED",
    )
    for row in coverage_rows:
        check(
            row["implementation_satisfaction"] == "NOT_ASSESSED",
            f"参数覆盖实现满足性越界：{row['policy_id']}:{row['formula_parameter']}",
        )

    binding_by_id = {row["binding_id"]: row for row in term_rows}
    bindings_by_term: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in term_rows:
        bindings_by_term[(row["system"], row["term"])].append(row)

    inventory_by_id = {row["ap_id"]: row for row in inventory_rows}
    check(len(inventory_by_id) == len(inventory_rows), "原子命题清单 ap_id 不唯一")
    check(set(inventory_by_id) == set(ap_ids), "原子命题绑定与清单的 ap_id 集合不一致")
    for atom in ap_rows:
        inventory = inventory_by_id.get(atom["ap_id"])
        if inventory is not None:
            check(
                all(atom[field] == inventory[field] for field in AP_BASE_FIELDS),
                f"原子命题基础字段与清单不一致：{atom['ap_id']}",
            )
        expected_term_binding_ids: list[str] = []
        for term in atom["terms"]:
            rows = bindings_by_term.get((atom["system"], term), [])
            check(bool(rows), f"原子命题词项没有源码绑定：{atom['ap_id']}:{term}")
            expected_term_binding_ids.extend(row["binding_id"] for row in rows)
        check(
            atom["term_binding_ids"] == expected_term_binding_ids,
            f"原子命题 term_binding_ids 不完整或含无关引用：{atom['ap_id']}",
        )
        check(
            len(atom["term_binding_ids"]) == len(set(atom["term_binding_ids"])),
            f"原子命题 term_binding_ids 重复：{atom['ap_id']}",
        )
        selected_ids = atom["selected_term_binding_ids"]
        alternative_ids = atom["alternative_term_binding_ids"]
        check(bool(selected_ids), f"原子命题没有选定绑定：{atom['ap_id']}")
        check(len(selected_ids) == len(set(selected_ids)), f"选定绑定 ID 重复：{atom['ap_id']}")
        check(len(alternative_ids) == len(set(alternative_ids)), f"替代绑定 ID 重复：{atom['ap_id']}")
        check(not (set(selected_ids) & set(alternative_ids)), f"主组与替代组交叉：{atom['ap_id']}")
        check(
            set(selected_ids) | set(alternative_ids) == set(atom["term_binding_ids"]),
            f"主组和替代组未完整划分全部绑定：{atom['ap_id']}",
        )
        selected_groups_by_term: dict[str, set[str]] = defaultdict(set)
        for binding_id in selected_ids:
            selected_row = binding_by_id.get(binding_id)
            if selected_row is not None:
                selected_groups_by_term[selected_row["term"]].add(selected_row["candidate_group"])
        for term in atom["terms"]:
            check(
                len(selected_groups_by_term[term]) == 1,
                f"每个词项必须且只能选一个语义组：{atom['ap_id']}:{term}",
            )
        if atom["system"] == "PX4":
            for current_term, previous_term in (
                ("ALT_t", "ALT_t-1"),
                ("Pos_t", "Pos_t-1"),
                ("Circle_speed_t", "Circle_speed_t-1"),
            ):
                if current_term in atom["terms"] and previous_term in atom["terms"]:
                    current_groups = selected_groups_by_term[current_term]
                    previous_groups = selected_groups_by_term[previous_term]
                    if len(current_groups) == 1 and len(previous_groups) == 1:
                        current_suffix = next(iter(current_groups)).split(":", 1)[1]
                        previous_suffix = next(iter(previous_groups)).split(":", 1)[1]
                        check(
                            current_suffix == previous_suffix,
                            f"当前值与 t-1 样本选择了不同语义组：{atom['ap_id']}:{current_term}",
                        )
        expected_selection_status = (
            "UNRESOLVED_PRIMARY"
            if atom["binding_status"] == "UNRESOLVED"
            else "PRIMARY_WITH_ALTERNATIVES"
            if alternative_ids
            else "PRIMARY_SELECTED"
        )
        check(
            atom["binding_selection_status"] == expected_selection_status,
            f"语义组选择状态与绑定划分不一致：{atom['ap_id']}",
        )
        for binding_id in atom["term_binding_ids"]:
            check(binding_id in binding_by_id, f"原子命题引用未知 binding_id：{atom['ap_id']}:{binding_id}")
            if binding_id in binding_by_id:
                check(
                    binding_by_id[binding_id]["system"] == atom["system"],
                    f"原子命题跨系统引用 binding_id：{atom['ap_id']}:{binding_id}",
                )
        selected_rows_for_observation = [binding_by_id[item] for item in selected_ids if item in binding_by_id]
        expected_observation_bindings = [
            {
                "binding_id": row["binding_id"],
                "term": row["term"],
                "binding_role": row["binding_role"],
                "mavlink_observability": row["mavlink_observability"],
                "message_fields_raw": row["mavlink_message_fields"],
            }
            for row in selected_rows_for_observation
            if row["mavlink_message_fields"]
        ]
        check(
            atom["mavlink_observation_bindings"] == expected_observation_bindings,
            f"原子命题结构化 MAVLink 观测绑定与选定源码行不一致：{atom['ap_id']}",
        )
        expected_observation_fields = sorted(
            {
                field.strip()
                for row in selected_rows_for_observation
                for field in row["mavlink_message_fields"].split(";")
                if field.strip()
            }
        )
        check(
            atom["mavlink_observation_fields"] == expected_observation_fields,
            f"原子命题 MAVLink 观测字段集合与选定源码行不一致：{atom['ap_id']}",
        )

    validated_locations: set[str] = set()
    line_count_cache: dict[Path, int] = {}
    manifest_prefixes = {
        system: manifest["sources"][source_key]["path"] + "/"
        for system, source_key in MANIFEST_SOURCE_KEYS.items()
    }
    for row in term_rows:
        raw_path = row["source_path"]
        source_line = row["source_line"]
        source_end_line = row["source_end_line"]
        if not raw_path:
            check(source_line == 0, f"空源码路径却有非零行号：{row['binding_id']}")
            check(source_end_line == 0, f"空源码路径却有非零结束行号：{row['binding_id']}")
            continue
        relative_path = Path(raw_path)
        check(not relative_path.is_absolute(), f"源码路径不是工作区相对路径：{row['binding_id']}")
        check(".." not in relative_path.parts, f"源码路径包含父目录跳转：{row['binding_id']}")
        check(
            raw_path.startswith(manifest_prefixes[row["system"]]),
            f"源码路径不属于对应冻结源码树：{row['binding_id']}:{raw_path}",
        )
        source_path = PROJECT_ROOT / relative_path
        check(source_path.is_file(), f"源码路径不存在：{row['binding_id']}:{raw_path}")
        check(
            isinstance(source_line, int) and not isinstance(source_line, bool),
            f"源码起始行号不是整数：{row['binding_id']}",
        )
        check(
            isinstance(source_end_line, int) and not isinstance(source_end_line, bool),
            f"源码结束行号不是整数：{row['binding_id']}",
        )
        if (
            source_path.is_file()
            and isinstance(source_line, int)
            and not isinstance(source_line, bool)
            and isinstance(source_end_line, int)
            and not isinstance(source_end_line, bool)
        ):
            if source_path not in line_count_cache:
                with source_path.open(encoding="utf-8", errors="replace") as handle:
                    line_count_cache[source_path] = sum(1 for _ in handle)
            check(
                1 <= source_line <= source_end_line <= line_count_cache[source_path],
                f"源码行范围越界或倒置：{row['binding_id']}:{raw_path}:{source_line}-{source_end_line}",
            )
            if 1 <= source_line <= source_end_line <= line_count_cache[source_path]:
                validated_locations.add(f"{raw_path}:{source_line}-{source_end_line}")

    function_kinds = {
        "ASSIGNMENT",
        "COMMAND_ACCEPTANCE",
        "COMMAND_ACK",
        "EXECUTION_STATE",
        "MAVLINK_ENCODER",
        "MAVLINK_SENDER",
        "PARAMETER_CONSUMER",
        "SELECTION_GUARD",
    }
    for row in term_rows:
        if row["binding_kind"] in function_kinds:
            check(bool(row["function_context"]), f"函数路径绑定缺少 function_context：{row['binding_id']}")

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in term_rows:
        groups[(row["system"], row["term"], row["candidate_group"])].append(row)
    for key, rows in groups.items():
        check(
            any(row["binding_role"] != "SUPPORTING_EVIDENCE" for row in rows),
            f"候选组只有辅助证据而没有主值/替代语义：{key}",
        )

    def source_line_text(row: dict[str, Any]) -> str:
        source_path = PROJECT_ROOT / row["source_path"]
        return source_path.read_text(encoding="utf-8", errors="replace").splitlines()[row["source_line"] - 1]

    critical_fragments = [
        ("ArduPilot", "Baro", "ENUM_CONSTANT", "BARO = 1"),
        ("ArduPilot", "home_position", "ASSIGNMENT", "_home = tmp"),
        ("ArduPilot", "Parachute", "ASSIGNMENT", "set_output_pwm"),
        ("ArduPilot", "Roll_direction", "ASSIGNMENT", "roll_dir = FLIP_ROLL_RIGHT"),
        ("ArduPilot", "GPS_fail", "ASSIGNMENT", "failsafe.ekf = true"),
        ("PX4", "ALT_t", "DERIVED_EXPRESSION", "msg.relative_alt"),
        ("PX4", "Disarm", "ENUM_CONSTANT", "ARMING_STATE_DISARMED"),
        ("PX4", "Command_t", "COMMAND_ACCEPTANCE", "VEHICLE_CMD_NAV_TAKEOFF"),
        ("PX4", "Target_ALT", "ASSIGNMENT", "current.alt = cmd.param7"),
        ("PX4", "COM_POS_FS_DELAY", "PARAMETER_CONSUMER", "ekf2_noaid_tout"),
    ]
    for system, term, kind, fragment in critical_fragments:
        candidates = [
            row
            for row in term_rows
            if row["system"] == system and row["term"] == term and row["binding_kind"] == kind
        ]
        matching = [row for row in candidates if row["source_path"] and fragment in source_line_text(row)]
        check(bool(matching), f"关键源码行未包含预期实体：{system}:{term}:{kind}:{fragment}")
    raw_rc_rows = [
        row
        for row in term_rows
        if row["system"] == "PX4"
        and row["term"] in {"RC_pitch", "RC_roll", "Throttle_t"}
        and row["binding_kind"] == "DERIVED_EXPRESSION"
    ]
    check(len(raw_rc_rows) == 3, "PX4 原始 RC 读取绑定不是 3 行")
    for row in raw_rc_rows:
        check("input_rc.values" in source_line_text(row), f"原始 RC 行未指向 values[] 读取：{row['binding_id']}")
    parameter_consumers = [row for row in term_rows if row["binding_kind"] == "PARAMETER_CONSUMER"]
    for row in parameter_consumers:
        line_text = source_line_text(row)
        check(
            ".get()" in line_text or "get_" in line_text or "ekf2_noaid_tout" in line_text,
            f"参数消费行没有实际 getter/字段读取：{row['binding_id']}",
        )
    context_expectations = [
        ("PX4", "Circle_direction_t", "ASSIGNMENT", "FlightTaskOrbit::applyCommandParameters(const vehicle_command_s&, bool&)"),
        ("PX4", "Circle_direction_t", "MAVLINK_SENDER", "MavlinkStreamOrbitStatus::send()"),
        ("PX4", "RC_pitch", "ASSIGNMENT", "RCUpdate::update_rc_functions()"),
        ("PX4", "RC_roll", "ASSIGNMENT", "RCUpdate::update_rc_functions()"),
        ("PX4", "Throttle_t", "ASSIGNMENT", "RCUpdate::update_rc_functions()"),
        ("PX4", "Command_t", "EXECUTION_STATE", "Navigator::run()"),
        ("PX4", "Target_ALT", "ASSIGNMENT", "Navigator::run()"),
        ("PX4", "RTL_RETURN_ALT", "PARAMETER_CONSUMER", "RTL::findRtlDestination()"),
        ("PX4", "RTL_DESCEND_ALT", "PARAMETER_CONSUMER", "RtlDirect::sanitizeLandApproach()"),
        ("PX4", "MPC_LAND_SPEED", "PARAMETER_CONSUMER", "FlightTaskAuto::_prepareLandSetpoints()"),
        ("PX4", "MPC_TKO_SPEED", "PARAMETER_CONSUMER", "FlightTaskAuto::_updateTrajConstraints()"),
    ]
    for system, term, kind, expected_context in context_expectations:
        matches = [
            row
            for row in term_rows
            if row["system"] == system
            and row["term"] == term
            and row["binding_kind"] == kind
            and row["function_context"] == expected_context
        ]
        check(bool(matches), f"函数上下文身份漂移：{system}:{term}:{kind}:{expected_context}")

    # AP observability is controlled by each selected semantic group's core
    # truth value.  A directly observable helper row must not improve a
    # conditional or instrumented primary value.
    observability_rank = {
        "DIRECT": 0,
        "DERIVED": 1,
        "CONDITIONAL": 2,
        "INSTRUMENTATION_REQUIRED": 3,
        "UNRESOLVED": 4,
    }
    term_by_id = {row["binding_id"]: row for row in term_rows}
    for atom in ap_rows:
        if atom["binding_status"] == "UNRESOLVED":
            check(atom["mavlink_observability"] == "UNRESOLVED", f"未解决 AP 仍被标为可观测：{atom['ap_id']}")
            continue
        selected_rows = [term_by_id[item] for item in atom["selected_term_binding_ids"]]
        by_selected_term: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in selected_rows:
            by_selected_term[row["term"]].append(row)
        required = []
        for term in atom["terms"]:
            rows = by_selected_term[term]
            core = [row for row in rows if row["binding_role"] != "SUPPORTING_EVIDENCE"]
            check(bool(core), f"AP 已选词项组只有辅助行：{atom['ap_id']}:{term}")
            required.append(max((row["mavlink_observability"] for row in core), key=observability_rank.get))
        expected_observation = max(required, key=observability_rank.get)
        check(
            atom["mavlink_observability"] == expected_observation,
            f"AP 观测性被辅助证据错误提升或与主值不一致：{atom['ap_id']}",
        )

    observed_commits: dict[str, str] = {}
    observed_status: dict[str, list[str]] = {}
    for system, expected_commit in EXPECTED_COMMITS.items():
        source_key = MANIFEST_SOURCE_KEYS[system]
        source_record = manifest["sources"][source_key]
        check(
            source_record["commit"] == expected_commit,
            f"source_manifest 中 {system} 固定 commit 改变",
        )
        repository_path = PROJECT_ROOT / source_record["path"]
        check(repository_path.is_dir(), f"冻结源码目录不存在：{repository_path}")
        if repository_path.is_dir():
            observed_commits[system] = git_head(repository_path)
            check(
                observed_commits[system] == source_record["commit"],
                f"{system} 当前 checkout 与 source_manifest commit 不一致",
            )
            observed_status[system] = git_status(repository_path)
    check(observed_status.get("PX4", []) == [], "PX4 冻结源码工作树不再干净")
    check(
        observed_status.get("ArduPilot", []) == [" m modules/CrashDebug"],
        "ArduPilot 工作树不再是仅保留既存 CrashDebug 子模块状态",
    )

    for system, directory in (("ArduPilot", "ArduPilot"), ("PX4", "PX4")):
        expected_term_subset = [row for row in term_rows if row["system"] == system]
        expected_ap_subset = [row for row in ap_rows if row["system"] == system]
        split_root = DATASET_ROOT / directory
        split_term_payload = load_json(split_root / "term_source_bindings.json")
        split_ap_payload = load_json(split_root / "atomic_proposition_bindings.json")
        split_term_header, split_term_csv = load_csv(split_root / "term_source_bindings.csv")
        split_ap_header, split_ap_csv = load_csv(split_root / "atomic_proposition_bindings.csv")
        check(split_term_payload.get("schema_version") == "1.0", f"{system} 词项分拆 schema_version 错误")
        check(split_ap_payload.get("schema_version") == "1.0", f"{system} AP 分拆 schema_version 错误")
        check(split_term_payload.get("rows") == expected_term_subset, f"{system} 词项 JSON 分拆内容不一致")
        check(split_ap_payload.get("rows") == expected_ap_subset, f"{system} AP JSON 分拆内容不一致")
        check(split_term_header == expected_term_header, f"{system} 词项 CSV 分拆表头不一致")
        check(split_ap_header == expected_ap_header, f"{system} AP CSV 分拆表头不一致")
        check(split_term_csv == csv_projection(expected_term_subset), f"{system} 词项 CSV 分拆内容不一致")
        check(split_ap_csv == csv_projection(expected_ap_subset), f"{system} AP CSV 分拆内容不一致")

    previous_rows = [row for row in term_rows if row["binding_kind"] == "TRACE_PREVIOUS_SAMPLE"]
    for system, expected_terms in EXPECTED_PREVIOUS_TERMS.items():
        actual_terms = {row["term"] for row in previous_rows if row["system"] == system}
        check(actual_terms == expected_terms, f"{system} 前一有效样本词项集合改变")
        all_suffix_terms = {row["term"] for row in term_rows if row["system"] == system and row["term"].endswith("-1")}
        check(all_suffix_terms == expected_terms, f"{system} 的 t-1 词项未全部采用历史样本绑定")
    for row in previous_rows:
        check(row["confidence"] == "MODELLED", f"历史样本不是 MODELLED：{row['binding_id']}")
        check(row["mavlink_observability"] == "DERIVED", f"历史样本不是 DERIVED：{row['binding_id']}")
        check(row["symbol"].startswith("previous_accepted("), f"历史样本符号缺少 previous_accepted：{row['binding_id']}")
        check("t-1 不是" in row["observation_conversion_zh"], f"历史样本缺少 t-1 时钟警示：{row['binding_id']}")

    unresolved_term_rows = [row for row in term_rows if row["confidence"] == "UNRESOLVED"]
    unresolved_term_signature = {
        (row["system"], row["term"], row["binding_kind"])
        for row in unresolved_term_rows
    }
    check(
        unresolved_term_signature == EXPECTED_UNRESOLVED_TERM_ROWS,
        "UNRESOLVED 词项绑定集合改变",
    )
    actual_unresolved_aps = {row["ap_id"] for row in ap_rows if row["binding_status"] == "UNRESOLVED"}
    check(actual_unresolved_aps == EXPECTED_UNRESOLVED_APS, "UNRESOLVED 原子命题集合改变")
    for atom in ap_rows:
        if atom["binding_status"] == "UNRESOLVED":
            check(bool(atom["binding_status_reason_zh"]), f"UNRESOLVED 原子命题缺少理由：{atom['ap_id']}")
            check(bool(atom["evaluation_plan_zh"]), f"UNRESOLVED 原子命题缺少处理计划：{atom['ap_id']}")

    critical_unresolved: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in unresolved_term_rows:
        if row["term"] in {"k", "Waypoint", "COM_POS_FS_DELAY"}:
            critical_unresolved[(row["system"], row["term"])].append(row)
    for key in (("ArduPilot", "k"), ("PX4", "k")):
        rows = critical_unresolved.get(key, [])
        row = rows[0] if len(rows) == 1 else None
        check(row is not None, f"缺少关键未解决词项：{key}")
        if row is not None:
            check(row["mavlink_observability"] == "UNRESOLVED", f"关键未解决词项观测状态错误：{key}")
            check(not row["source_path"] and row["source_line"] == 0, f"关键未解决词项被伪造源码位置：{key}")
    waypoint_rows = critical_unresolved.get(("ArduPilot", "Waypoint"), [])
    check(len(waypoint_rows) == 1, "缺少且仅缺少一个 Waypoint 未解决抽象绑定")
    if len(waypoint_rows) == 1:
        check(waypoint_rows[0]["binding_kind"] == "UNRESOLVED_ABSTRACTION", "Waypoint 未保留为未解决抽象")
        check(waypoint_rows[0]["mavlink_observability"] == "UNRESOLVED", "Waypoint 被错误标为可直接判真")
        check(not waypoint_rows[0]["source_path"] and waypoint_rows[0]["source_line"] == 0, "Waypoint 未解决抽象被伪造源码位置")
    com_pos_rows = critical_unresolved.get(("PX4", "COM_POS_FS_DELAY"), [])
    check(len(com_pos_rows) == 5, "COM_POS_FS_DELAY 必须保留一行已删除项、两行非等价候选和两行候选消费路径")
    check(
        all(row["confidence"] == "UNRESOLVED" for row in com_pos_rows),
        "COM_POS_FS_DELAY 的整体置信状态不再是 UNRESOLVED",
    )
    removed_rows = [
        row
        for row in com_pos_rows
        if row["binding_kind"] == "REMOVED_PARAMETER"
    ]
    removed = removed_rows[0] if len(removed_rows) == 1 else None
    check(removed is not None, "缺少已删除参数 COM_POS_FS_DELAY 的未解决绑定")
    if removed is not None:
        check(removed["binding_kind"] == "REMOVED_PARAMETER", "COM_POS_FS_DELAY 未标为 REMOVED_PARAMETER")
        check(removed["current_parameter_name"] == "COM_POS_FS_DELAY", "已删除行没有保留历史参数名 COM_POS_FS_DELAY")
        check(removed["historical_current_relation"] == "REMOVED_NO_EQUIVALENT", "COM_POS_FS_DELAY 被错误关联到当前等价参数")
        check(removed["mavlink_observability"] == "UNRESOLVED", "COM_POS_FS_DELAY 被错误标为可观测")
    candidate_rows = [
        row
        for row in com_pos_rows
        if row["binding_kind"] == "NON_EQUIVALENT_CANDIDATE"
    ]
    check(len(candidate_rows) == 2, "COM_POS_FS_DELAY 没有且仅有两个 NON_EQUIVALENT_CANDIDATE")
    check(
        {row["current_parameter_name"] for row in candidate_rows} == {"EKF2_NOAID_TOUT", "COM_POS_FS_EPH"},
        "COM_POS_FS_DELAY 两个非等价候选身份改变",
    )
    for candidate in candidate_rows:
        check(candidate["historical_current_relation"] == "NON_EQUIVALENT_CANDIDATE", "非等价候选关系状态错误")
        check("不能用于改写" in candidate["confidence_reason_zh"], "非等价候选缺少禁止改写公式说明")
        check(
            "禁止" in candidate["observation_limit_zh"] and "代入" in candidate["observation_limit_zh"],
            "非等价候选缺少禁止代入说明",
        )
        check(candidate["mavlink_observability"] == "DIRECT", "非等价候选参数值未保持为可直接读取")
    candidate_consumer_rows = [
        row for row in com_pos_rows if row["binding_kind"] == "PARAMETER_CONSUMER"
    ]
    check(len(candidate_consumer_rows) == 2, "两个非等价候选没有各自保留唯一实际消费路径")
    check(
        {row["candidate_group"] for row in candidate_consumer_rows}
        == {
            "COM_POS_FS_DELAY:ekf2_noaid_tout_non_equivalent",
            "COM_POS_FS_DELAY:com_pos_fs_eph_non_equivalent",
        },
        "非等价候选消费路径被错放入历史参数主组或彼此混合",
    )
    check(
        all(row["mavlink_observability"] == "INSTRUMENTATION_REQUIRED" for row in candidate_consumer_rows),
        "候选参数消费点被错误标为可由 PARAM_VALUE 直接证明",
    )
    com_pos_aps = [atom for atom in ap_rows if "COM_POS_FS_DELAY" in atom["terms"]]
    check(len(com_pos_aps) == 1, "COM_POS_FS_DELAY 所在原子命题数量改变")
    check(
        all(atom["binding_status"] == "UNRESOLVED" for atom in com_pos_aps),
        "COM_POS_FS_DELAY 所在原子命题不再整体保持 UNRESOLVED",
    )

    check(len(coverage_rows) == 20, "公式参数覆盖行数不是 20")
    coverage_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in coverage_rows:
        coverage_by_key[(row["system"], row["formula_parameter"])].append(row)
        check(
            any(
                row["formula_parameter"] in atom["terms"]
                for atom in ap_rows
                if atom["system"] == row["system"] and atom["property_id"] == row["policy_id"]
            ),
            f"参数覆盖行未关联到对应性质 AP：{row['policy_id']}:{row['formula_parameter']}",
        )
    parameter_bindings = [
        row
        for row in term_rows
        if row["binding_kind"] in {"PARAMETER_DEFINITION", "REMOVED_PARAMETER"}
    ]
    parameter_binding_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in parameter_bindings:
        parameter_binding_by_key[(row["system"], row["term"])].append(row)
    check(len(coverage_by_key) == 15, "唯一公式参数数量不是 15")
    check(
        set(coverage_by_key) <= set(parameter_binding_by_key),
        "formula_parameter_coverage 中存在没有参数定义绑定的键",
    )
    for key, records in coverage_by_key.items():
        bindings = parameter_binding_by_key.get(key, [])
        check(len(bindings) == 1, f"公式参数没有且仅有一个定义绑定：{key}")
        current_names = {row["current_name"] for row in records}
        identity_statuses = {row["current_identity_status"] for row in records}
        check(len(current_names) == 1, f"同一公式参数的当前名称不一致：{key}")
        check(len(identity_statuses) == 1, f"同一公式参数的当前身份状态不一致：{key}")
        if len(bindings) != 1:
            continue
        binding = bindings[0]
        if len(current_names) == 1:
            check(
                binding["current_parameter_name"] == next(iter(current_names)),
                f"参数绑定的当前名称与覆盖表不一致：{key}",
            )
        if identity_statuses == {"CURRENT_DEFINITION_NOT_FOUND"}:
            check(binding["binding_kind"] == "REMOVED_PARAMETER", f"缺失参数未保留为 REMOVED_PARAMETER：{key}")
            check(binding["confidence"] == "UNRESOLVED", f"缺失参数未保留为 UNRESOLVED：{key}")
        else:
            check(binding["binding_kind"] == "PARAMETER_DEFINITION", f"当前参数未标为 PARAMETER_DEFINITION：{key}")
            location = f"{binding['source_path']}:{binding['source_line']}"
            for record in records:
                check(
                    location in record["current_source_locations"].split("|"),
                    f"参数绑定位置不在覆盖表当前位置中：{record['policy_id']}:{key[1]}",
                )

    ap_counts = Counter(row["system"] for row in ap_rows)
    report = {
        "schema_version": "1.0",
        "validator": "validate_source_bindings.py",
        "result": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "counts": {
            "term_binding_rows": len(term_rows),
            "term_binding_rows_by_system": dict(term_row_counts),
            "unique_system_terms": len(system_terms),
            "unique_system_terms_by_system": dict(system_term_counts),
            "atomic_proposition_occurrences": len(ap_rows),
            "atomic_proposition_occurrences_by_system": dict(ap_counts),
            "validated_source_locations": len(validated_locations),
            "trace_previous_sample_bindings": len(previous_rows),
            "unresolved_term_binding_rows": len(unresolved_term_rows),
            "unresolved_atomic_propositions": len(actual_unresolved_aps),
            "formula_parameter_coverage_rows": len(coverage_rows),
            "unique_formula_parameters": len(coverage_by_key),
            "explained_data_types": len(actual_type_unit_values["data_type"]),
            "explained_unit_coordinates": len(actual_type_unit_values["unit_coordinate"]),
            "explained_current_input_types": len(actual_type_unit_values["current_input_type"]),
            "explained_current_input_units": len(actual_type_unit_values["current_input_unit"]),
            "type_unit_dictionary_rows": len(type_unit_rows),
        },
        "status_counts": {
            "term_confidence": dict(Counter(row["confidence"] for row in term_rows)),
            "term_observability": dict(Counter(row["mavlink_observability"] for row in term_rows)),
            "term_binding_role": dict(Counter(row["binding_role"] for row in term_rows)),
            "ap_binding_status": dict(Counter(row["binding_status"] for row in ap_rows)),
            "ap_observability": dict(Counter(row["mavlink_observability"] for row in ap_rows)),
            "ap_binding_selection": dict(Counter(row["binding_selection_status"] for row in ap_rows)),
        },
        "frozen_source_commits": {
            system: {
                "expected": EXPECTED_COMMITS[system],
                "manifest": manifest["sources"][MANIFEST_SOURCE_KEYS[system]]["commit"],
                "checkout": observed_commits.get(system, ""),
            }
            for system in EXPECTED_COMMITS
        },
        "frozen_source_worktree_status": observed_status,
        "scope_note_zh": "通过只证明源码绑定、主/替代语义组选择、原子命题引用、分拆制品、固定版本、历史样本语义、参数关联以及类型/单位字典对来源原值的覆盖内部一致；不证明论文性质正确，也不证明当前固件满足性质。",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_zh = "通过（PASS）" if not failures else "失败（FAIL）"
    print(
        f"源码绑定验证：{result_zh}；检查 {checks} 项，失败 {len(failures)} 项；"
        f"系统—词项 {len(system_terms)}（ArduPilot {system_term_counts['ArduPilot']}，"
        f"PX4 {system_term_counts['PX4']}）；原子命题 {len(ap_rows)}；"
        f"历史样本 {len(previous_rows)}；未解决原子命题 {len(actual_unresolved_aps)}。"
    )
    print(f"验证报告：{REPORT_PATH}")
    if failures:
        for failure in failures[:25]:
            print(f"- {failure}")
        if len(failures) > 25:
            print(f"- 其余 {len(failures) - 25} 项失败见验证报告。")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
