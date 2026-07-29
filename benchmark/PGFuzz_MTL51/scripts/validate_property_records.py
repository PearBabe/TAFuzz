#!/usr/bin/env python3
"""Validate the 51 generated PGFuzz per-property audit records.

This validator checks lossless joins, per-property Markdown/JSON correspondence,
frozen-source ranges, catalog links, official-document context, and conservative
time semantics.  Passing it does not establish firmware conformance.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import jsonschema  # type: ignore[import-not-found]
except ImportError:
    jsonschema = None


DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = DATASET_ROOT / "validation" / "property_record_validation.json"
SCHEMA_PATH = DATASET_ROOT / "schemas" / "property_record.schema.json"
FIELD_DICTIONARY_JSON_PATH = DATASET_ROOT / "FIELD_DICTIONARY.json"
FIELD_DICTIONARY_MARKDOWN_PATH = DATASET_ROOT / "FIELD_DICTIONARY.md"

EXPECTED_PROPERTY_COUNTS = {"ArduPilot": 30, "PX4": 21}
EXPECTED_COMMITS = {
    "ArduPilot": "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
    "PX4": "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
}
MANIFEST_SOURCE_KEYS = {"ArduPilot": "ardupilot", "PX4": "px4"}
EXPECTED_TOTALS = {
    "properties": 51,
    "atomic_propositions": 178,
    "author_dependency_associations": 7569,
    "formula_parameters": 20,
    "term_binding_rows": 227,
    "official_documents": 23,
}
ALLOWED_OFFICIAL_HOSTS = {"ardupilot.org", "docs.px4.io", "mavlink.io"}
OFFICIAL_CONTEXT_ROLE = "CONTEXT_ONLY_NOT_CURRENT_REQUIREMENT_CONFIRMATION"

RECORD_KEYS = {
    "schema_version",
    "dataset_id",
    "system",
    "property_id",
    "paper_order",
    "artifact_policy_directory",
    "dataset_role",
    "implementation_satisfaction",
    "status_legend_zh",
    "frozen_current_source",
    "paper_evidence",
    "official_document_context",
    "official_context_limit_zh",
    "temporal_semantics",
    "property_binding_summary",
    "atomic_propositions",
    "formula_parameters",
    "parameter_value_contract_zh",
    "author_dependency_summary",
    "author_input_dependencies",
    "current_input_identities",
    "audit_boundary_zh",
}

CATALOG_FIELDS = (
    "paper_order",
    "system",
    "property_id",
    "template",
    "description_zh",
    "description_en",
    "paper_formula_transcription",
    "binding_formula_interpretation",
    "inherits_from",
    "issue_codes",
    "ap_count",
    "property_binding_status",
    "mavlink_observability",
    "selected_binding_count",
    "alternative_binding_count",
    "author_dependency_count",
    "unique_author_input_count",
    "formula_parameter_count",
    "official_document_count",
    "dataset_role",
    "implementation_satisfaction",
    "current_commit",
    "json_record",
    "markdown_record",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def csv_projection(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {key: "" if value is None else str(value) for key, value in row.items()}
        for row in rows
    ]


def git_head(path: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def aggregate_binding_status(rows: list[dict[str, Any]]) -> str:
    statuses = {row["binding_status"] for row in rows}
    if "UNRESOLVED" in statuses:
        return "UNRESOLVED"
    if "MODELLED" in statuses:
        return "MODELLED"
    return "EXACT"


def aggregate_observability(rows: list[dict[str, Any]]) -> str:
    order = {
        "DIRECT": 0,
        "DERIVED": 1,
        "CONDITIONAL": 2,
        "INSTRUMENTATION_REQUIRED": 3,
        "UNRESOLVED": 4,
    }
    return max((row["mavlink_observability"] for row in rows), key=order.__getitem__)


def counter_dict(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def catalog_row_from_record(record: dict[str, Any]) -> dict[str, Any]:
    paper = record["paper_evidence"]
    summary = record["property_binding_summary"]
    dependencies = record["author_dependency_summary"]
    return {
        "paper_order": record["paper_order"],
        "system": record["system"],
        "property_id": record["property_id"],
        "template": paper["template"],
        "description_zh": paper["description_zh"],
        "description_en": paper["description_en"],
        "paper_formula_transcription": paper["paper_formula_transcription"],
        "binding_formula_interpretation": paper["binding_formula_interpretation"],
        "inherits_from": paper["inherits_from"] or "",
        "issue_codes": ";".join(item["code"] for item in paper["issues"]),
        "ap_count": summary["ap_count"],
        "property_binding_status": summary["binding_status"],
        "mavlink_observability": summary["mavlink_observability"],
        "selected_binding_count": summary["selected_binding_count"],
        "alternative_binding_count": summary["alternative_binding_count"],
        "author_dependency_count": dependencies["association_count"],
        "unique_author_input_count": dependencies["unique_input_identity_count"],
        "formula_parameter_count": len(record["formula_parameters"]),
        "official_document_count": len(record["official_document_context"]),
        "dataset_role": record["dataset_role"],
        "implementation_satisfaction": record["implementation_satisfaction"],
        "current_commit": record["frozen_current_source"]["commit"],
        "json_record": f"properties/{record['property_id']}.json",
        "markdown_record": f"properties/{record['property_id']}.md",
    }


def collect_satisfaction_values(value: Any) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "implementation_satisfaction":
                found.append(child)
            found.extend(collect_satisfaction_values(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_satisfaction_values(child))
    return found


def collect_object_keys(value: Any, found: set[str]) -> None:
    """Recursively collect every object key used by a generated JSON record."""
    if isinstance(value, dict):
        found.update(str(key) for key in value)
        for child in value.values():
            collect_object_keys(child, found)
    elif isinstance(value, list):
        for child in value:
            collect_object_keys(child, found)


def main() -> None:
    formula_payload = load_json(DATASET_ROOT / "table_xii_formula_inventory.json")
    ap_payload = load_json(DATASET_ROOT / "atomic_proposition_bindings.json")
    term_payload = load_json(DATASET_ROOT / "term_source_bindings.json")
    dependency_payload = load_json(DATASET_ROOT / "author_input_dependencies.json")
    identity_payload = load_json(DATASET_ROOT / "current_input_identity_map.json")
    parameter_payload = load_json(DATASET_ROOT / "formula_parameter_coverage.json")
    document_payload = load_json(DATASET_ROOT / "official_document_context.json")
    manifest = load_json(DATASET_ROOT / "source_manifest.json")

    policies: list[dict[str, Any]] = formula_payload["policies"]
    ap_rows: list[dict[str, Any]] = ap_payload["rows"]
    term_rows: list[dict[str, Any]] = term_payload["rows"]
    dependency_rows: list[dict[str, Any]] = dependency_payload["association_rows"]
    identity_rows: list[dict[str, Any]] = identity_payload["rows"]
    parameter_rows: list[dict[str, Any]] = parameter_payload["rows"]
    documents: list[dict[str, Any]] = document_payload["documents"]

    checks = 0
    failures: list[str] = []
    schema_validated_records = 0
    schema_validation_engine = "BUILT_IN_STRUCTURAL_FALLBACK"

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    check(SCHEMA_PATH.is_file(), "缺少逐性质记录 JSON Schema 文件")
    property_schema: dict[str, Any] = {}
    if SCHEMA_PATH.is_file():
        try:
            property_schema = load_json(SCHEMA_PATH)
            check(isinstance(property_schema, dict), "逐性质记录 JSON Schema 顶层不是对象")
            check(property_schema.get("type") == "object", "逐性质记录 JSON Schema 顶层类型不是 object")
            check(isinstance(property_schema.get("required"), list), "逐性质记录 JSON Schema 缺少 required 数组")
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"逐性质记录 JSON Schema 无法解析：{type(error).__name__}:{error}")
    schema_validator: Any = None
    if property_schema and jsonschema is not None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                validator_class = jsonschema.validators.validator_for(property_schema)
            validator_class.check_schema(property_schema)
            schema_validator = validator_class(property_schema)
            schema_version = getattr(jsonschema, "__version__", "unknown")
            schema_validation_engine = f"jsonschema-{schema_version}:{validator_class.__name__}"
            check(True, "jsonschema 验证器初始化失败")
        except Exception as error:  # jsonschema exposes draft-specific exception classes.
            check(False, f"JSON Schema 自身不合法或验证器初始化失败：{type(error).__name__}:{error}")

    # Canonical input cardinalities and keys are checked again here so the
    # property-record gate cannot silently validate against an already damaged
    # upstream file.
    check(formula_payload.get("schema_version") == "1.0", "公式清单 schema_version 不是 1.0")
    check(ap_payload.get("schema_version") == "1.0", "原子命题清单 schema_version 不是 1.0")
    check(term_payload.get("schema_version") == "1.0", "源码绑定清单 schema_version 不是 1.0")
    check(dependency_payload.get("schema_version") == "1.0", "作者依赖清单 schema_version 不是 1.0")
    check(identity_payload.get("schema_version") == "1.0", "当前输入身份清单 schema_version 不是 1.0")
    check(parameter_payload.get("schema_version") == "1.0", "公式参数覆盖清单 schema_version 不是 1.0")
    check(document_payload.get("schema_version") == "1.0", "官方文档语境清单 schema_version 不是 1.0")
    check(manifest.get("schema_version") == "1.0", "来源清单 schema_version 不是 1.0")
    check(len(policies) == EXPECTED_TOTALS["properties"], "公式性质数量不是 51")
    check(len(ap_rows) == EXPECTED_TOTALS["atomic_propositions"], "原子命题数量不是 178")
    check(len(dependency_rows) == EXPECTED_TOTALS["author_dependency_associations"], "作者依赖关联数量不是 7,569")
    check(len(parameter_rows) == EXPECTED_TOTALS["formula_parameters"], "公式参数覆盖数量不是 20")
    check(len(term_rows) == EXPECTED_TOTALS["term_binding_rows"], "源码绑定数量不是 227")
    check(len(documents) == EXPECTED_TOTALS["official_documents"], "官方文档语境记录数量不是 23")

    property_keys = [(row["system"], row["policy_id"]) for row in policies]
    property_key_set = set(property_keys)
    check(len(property_key_set) == len(policies), "公式清单中的系统—性质编号不唯一")
    check(
        dict(Counter(system for system, _ in property_keys)) == EXPECTED_PROPERTY_COUNTS,
        "性质分布不是 ArduPilot 30、PX4 21",
    )
    check(len({row["ap_id"] for row in ap_rows}) == len(ap_rows), "原子命题编号不唯一")
    check(len({row["association_id"] for row in dependency_rows}) == len(dependency_rows), "作者依赖关联编号不唯一")
    parameter_keys = [(row["system"], row["policy_id"], row["formula_parameter"]) for row in parameter_rows]
    check(len(set(parameter_keys)) == len(parameter_rows), "公式参数覆盖键不唯一")
    check(len({row["binding_id"] for row in term_rows}) == len(term_rows), "源码绑定编号不唯一")

    default_evidence_fields = {
        "current_default_raw_catalog",
        "current_default_evidence_status",
        "current_default_evidence_source",
        "current_default_evidence_note_zh",
    }
    valid_default_evidence_statuses = {
        "CURATED_FROZEN_SOURCE_RESOLUTION",
        "SOURCE_METADATA_LITERAL_OR_EXPRESSION",
        "UNKNOWN",
    }
    for row in parameter_rows:
        key_label = f"{row['policy_id']}:{row['formula_parameter']}"
        check(default_evidence_fields <= set(row), f"公式参数覆盖缺少默认值证据字段：{key_label}")
        check(
            row.get("current_default_evidence_status") in valid_default_evidence_statuses,
            f"公式参数默认值证据状态未知：{key_label}",
        )
        check(bool(row.get("current_default_evidence_note_zh", "").strip()), f"公式参数默认值缺少中文证据说明：{key_label}")

    expected_ardupilot_curated_defaults = {
        ("A.RTL1", "RTL_ALT"): ("RTL_ALT_M_DEFAULT)", "15", "baseline/ardupilot/ArduCopter/config.h:428"),
        ("A.RTL2", "RTL_ALT"): ("RTL_ALT_M_DEFAULT)", "15", "baseline/ardupilot/ArduCopter/config.h:428"),
        ("A.RTL3", "RTL_ALT"): ("RTL_ALT_M_DEFAULT)", "15", "baseline/ardupilot/ArduCopter/config.h:428"),
        ("A.LAND1", "LAND_SPEED_HIGH"): ("0)", "0", "baseline/ardupilot/ArduCopter/mode_land.cpp:22"),
        ("A.LAND2", "LAND_SPEED"): ("LAND_SPD_MS_DEFAULT)", "0.5", "baseline/ardupilot/ArduCopter/config.h:331"),
        ("A.DRIFT1", "FS_EKF_ACTION"): ("", "1", "baseline/ardupilot/ArduCopter/config.h:112"),
        ("A.SPORT1", "PILOT_SPEED_UP"): ("", "2.5", "baseline/ardupilot/ArduCopter/config.h:523"),
        ("A.RC.FS1", "FS_THR_VALUE"): ("", "975", "baseline/ardupilot/ArduCopter/config.h:316"),
        ("A.RC.FS2", "FS_THR_VALUE"): ("", "975", "baseline/ardupilot/ArduCopter/config.h:316"),
        ("A.CHUTE1", "CHUTE_ALT_MIN"): ("AP_PARACHUTE_ALT_MIN_DEFAULT)", "10", "baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.h:24"),
    }
    actual_ardupilot_parameter_rows = {
        (row["policy_id"], row["formula_parameter"]): row
        for row in parameter_rows
        if row["system"] == "ArduPilot"
    }
    check(
        set(actual_ardupilot_parameter_rows) == set(expected_ardupilot_curated_defaults),
        "ArduPilot 公式直接参数不再是已审核的 10 行",
    )
    checked_default_evidence_locations: set[str] = set()
    for key, expected in expected_ardupilot_curated_defaults.items():
        row = actual_ardupilot_parameter_rows.get(key)
        check(row is not None, f"缺少 ArduPilot 公式直接参数默认值证据：{key}")
        if row is None:
            continue
        expected_raw, expected_value, expected_source = expected
        check(
            row["current_default_evidence_status"] == "CURATED_FROZEN_SOURCE_RESOLUTION",
            f"ArduPilot 公式直接参数未标为冻结源码人工核定默认值：{key}",
        )
        check(row["current_default_raw_catalog"] == expected_raw, f"ArduPilot 参数目录原始默认表达式改变：{key}")
        check(row["current_default"] == expected_value, f"ArduPilot 冻结源码求得默认值改变：{key}")
        check(row["current_default_evidence_source"] == expected_source, f"ArduPilot 默认值证据位置改变：{key}")
        raw_path, raw_line = expected_source.rsplit(":", 1)
        evidence_path = PROJECT_ROOT / raw_path
        check(evidence_path.is_file(), f"ArduPilot 默认值证据文件不存在：{key}:{raw_path}")
        if evidence_path.is_file():
            line_count = sum(1 for _ in evidence_path.open(encoding="utf-8", errors="replace"))
            check(1 <= int(raw_line) <= line_count, f"ArduPilot 默认值证据行越界：{key}:{expected_source}")
            checked_default_evidence_locations.add(expected_source)
    for row in parameter_rows:
        status = row["current_default_evidence_status"]
        key_label = f"{row['policy_id']}:{row['formula_parameter']}"
        if status == "SOURCE_METADATA_LITERAL_OR_EXPRESSION":
            check(bool(row["current_default_evidence_source"]), f"源码元数据默认值缺少证据位置：{key_label}")
            check(row["current_default"] == row["current_default_raw_catalog"], f"未声明求值步骤却改写源码元数据默认值：{key_label}")
        elif status == "UNKNOWN":
            check(not row["current_default"], f"未知默认值状态却保存了具体默认值：{key_label}")
            check(not row["current_default_evidence_source"], f"未知默认值状态却保存了证据位置：{key_label}")

    policy_by_key = {(row["system"], row["policy_id"]): row for row in policies}
    aps_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    dependencies_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    parameters_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    documents_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in ap_rows:
        aps_by_property[(row["system"], row["property_id"])].append(row)
    for row in dependency_rows:
        dependencies_by_property[(row["system"], row["policy_id"])].append(row)
    for row in parameter_rows:
        parameters_by_property[(row["system"], row["policy_id"])].append(row)
    for document in documents:
        for property_id in document["property_ids"]:
            documents_by_property[(document["system"], property_id)].append(document)
    identity_by_key = {
        (row["system"], row["input_class"], row["artifact_name"]): row
        for row in identity_rows
    }
    term_by_id = {row["binding_id"]: row for row in term_rows}

    # Official-document context must remain contextual evidence from an
    # allowlisted first-party host and must cover all 51 property records.
    document_ids = [row["document_id"] for row in documents]
    check(len(set(document_ids)) == len(document_ids), "官方文档编号不唯一")
    covered_property_keys: set[tuple[str, str]] = set()
    for document in documents:
        document_id = document["document_id"]
        parsed = urlparse(document["url"])
        check(parsed.scheme == "https", f"官方文档不是 HTTPS 地址：{document_id}")
        check(parsed.hostname in ALLOWED_OFFICIAL_HOSTS, f"官方文档域名不在允许集合：{document_id}:{parsed.hostname}")
        check(document["system"] in EXPECTED_PROPERTY_COUNTS, f"官方文档系统未知：{document_id}")
        check(document["evidence_role"] == OFFICIAL_CONTEXT_ROLE, f"官方文档被越界标为当前要求确认：{document_id}")
        check(bool(document["property_ids"]), f"官方文档没有关联性质：{document_id}")
        check(len(document["property_ids"]) == len(set(document["property_ids"])), f"官方文档内部性质编号重复：{document_id}")
        if document_id.startswith("PX4-DOC-"):
            check("v1.17" in document["version_scope"], f"PX4 官方页面缺少 v1.17 版本范围：{document_id}")
        for property_id in document["property_ids"]:
            key = (document["system"], property_id)
            covered_property_keys.add(key)
            check(key in property_key_set, f"官方文档关联未知或跨系统性质：{document_id}:{property_id}")
    check(covered_property_keys == property_key_set, "官方文档没有完整覆盖全部 51 条性质")
    for key in property_keys:
        check(bool(documents_by_property[key]), f"性质没有任何官方文档语境：{key[1]}")

    # Validate every canonical source range once.  Per-property embedded rows
    # are then compared byte-for-byte with these canonical dictionaries.
    source_prefixes = {
        system: manifest["sources"][source_key]["path"] + "/"
        for system, source_key in MANIFEST_SOURCE_KEYS.items()
    }
    line_count_cache: dict[Path, int] = {}
    validated_source_ranges: set[str] = set()
    for row in term_rows:
        binding_id = row["binding_id"]
        raw_path = row["source_path"]
        start = row["source_line"]
        end = row["source_end_line"]
        check(row["implementation_satisfaction"] == "NOT_ASSESSED", f"源码绑定实现符合性越界：{binding_id}")
        if not raw_path:
            check(start == 0 and end == 0, f"空源码路径必须同时使用 0 起止行：{binding_id}")
            continue
        relative_path = Path(raw_path)
        check(not relative_path.is_absolute(), f"源码路径不是工作区相对路径：{binding_id}")
        check(".." not in relative_path.parts, f"源码路径包含父目录跳转：{binding_id}")
        check(raw_path.startswith(source_prefixes[row["system"]]), f"源码路径不属于对应冻结源码树：{binding_id}")
        source_path = PROJECT_ROOT / relative_path
        check(source_path.is_file(), f"源码文件不存在：{binding_id}:{raw_path}")
        check(isinstance(start, int) and not isinstance(start, bool), f"源码起始行不是整数：{binding_id}")
        check(isinstance(end, int) and not isinstance(end, bool), f"源码结束行不是整数：{binding_id}")
        if source_path.is_file() and isinstance(start, int) and isinstance(end, int):
            if source_path not in line_count_cache:
                with source_path.open(encoding="utf-8", errors="replace") as handle:
                    line_count_cache[source_path] = sum(1 for _ in handle)
            in_range = 1 <= start <= end <= line_count_cache[source_path]
            check(in_range, f"源码起止行越界或倒置：{binding_id}:{raw_path}:{start}-{end}")
            if in_range:
                validated_source_ranges.add(f"{raw_path}:{start}-{end}")

    observed_commits: dict[str, str] = {}
    for system, expected_commit in EXPECTED_COMMITS.items():
        source = manifest["sources"][MANIFEST_SOURCE_KEYS[system]]
        check(source["commit"] == expected_commit, f"来源清单中的 {system} 固定提交改变")
        repository = PROJECT_ROOT / source["path"]
        check(repository.is_dir(), f"冻结源码目录不存在：{repository}")
        if repository.is_dir():
            observed_commits[system] = git_head(repository)
            check(observed_commits[system] == expected_commit, f"{system} 当前检出提交与冻结提交不一致")

    records: list[dict[str, Any]] = []
    records_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    markdown_by_key: dict[tuple[str, str], str] = {}
    expected_files_by_system: dict[str, set[str]] = defaultdict(set)
    for policy in policies:
        system = policy["system"]
        property_id = policy["policy_id"]
        key = (system, property_id)
        expected_files_by_system[system].add(property_id)
        json_path = DATASET_ROOT / system / "properties" / f"{property_id}.json"
        markdown_path = DATASET_ROOT / system / "properties" / f"{property_id}.md"
        check(json_path.is_file(), f"缺少逐性质 JSON 记录：{system}:{property_id}")
        check(markdown_path.is_file(), f"缺少逐性质 Markdown 记录：{system}:{property_id}")
        if not json_path.is_file() or not markdown_path.is_file():
            continue
        record = load_json(json_path)
        markdown = markdown_path.read_text(encoding="utf-8")
        records.append(record)
        records_by_key[key] = record
        markdown_by_key[key] = markdown

        if schema_validator is not None:
            schema_errors = sorted(
                schema_validator.iter_errors(record),
                key=lambda error: "/".join(map(str, error.path)),
            )
            check(
                not schema_errors,
                f"逐性质记录未通过 JSON Schema：{property_id}:"
                + "；".join(
                    f"{'/'.join(map(str, error.path)) or '<root>'}:{error.message}"
                    for error in schema_errors[:5]
                ),
            )
        else:
            # The explicit field/type/value checks below are the built-in
            # structural fallback when the optional jsonschema package is not
            # importable.  Count the record once it reaches this validation
            # path so the report states exactly how many records were checked.
            check(bool(property_schema), f"缺少可用结构约束，无法验证逐性质记录：{property_id}")
        schema_validated_records += 1

        check(set(record) == RECORD_KEYS, f"逐性质 JSON 顶层字段集合改变：{property_id}")
        check(record["schema_version"] == "1.0", f"逐性质 JSON schema_version 不是 1.0：{property_id}")
        check(record["dataset_id"] == manifest["dataset_id"], f"逐性质数据集编号与来源清单不一致：{property_id}")
        check(record["system"] == system, f"逐性质系统与目录不一致：{property_id}")
        check(record["property_id"] == property_id, f"逐性质编号与文件名不一致：{property_id}")
        check(record["paper_order"] == policy["paper_order"], f"论文顺序不一致：{property_id}")
        check(record["artifact_policy_directory"] == policy["artifact_policy_directory"], f"作者制品目录不一致：{property_id}")
        check(record["dataset_role"] == "HISTORICAL_PROPERTY_SEED", f"性质不再标为历史性质种子：{property_id}")
        check(record["implementation_satisfaction"] == "NOT_ASSESSED", f"逐性质实现符合性越界：{property_id}")
        satisfaction_values = collect_satisfaction_values(record)
        check(bool(satisfaction_values), f"逐性质记录没有实现符合性字段：{property_id}")
        check(all(value == "NOT_ASSESSED" for value in satisfaction_values), f"逐性质嵌套实现符合性出现非 NOT_ASSESSED：{property_id}")
        check(
            record["frozen_current_source"] == manifest["sources"][MANIFEST_SOURCE_KEYS[system]],
            f"逐性质冻结源码身份不一致：{property_id}",
        )

        paper = record["paper_evidence"]
        check(paper["paper"] == manifest["sources"]["pgfuzz_pdf"], f"论文文件证据不一致：{property_id}")
        check(paper["table"] == "Table XII" and paper["page_one_based"] == 18, f"论文表格或页码不一致：{property_id}")
        for field in (
            "description_en",
            "description_zh",
            "template",
            "paper_formula_transcription",
            "binding_formula_interpretation",
            "inherits_from",
        ):
            check(paper[field] == policy[field], f"论文字段与规范化清单不一致：{property_id}:{field}")
        expected_issues = [
            {"code": issue, "explanation_zh": formula_payload["issue_definitions"][issue]}
            for issue in policy["issues"]
        ]
        check(paper["issues"] == expected_issues, f"公式问题清单不一致：{property_id}")

        expected_aps = aps_by_property[key]
        embedded_aps = record["atomic_propositions"]
        check(len(embedded_aps) == len(expected_aps), f"逐性质原子命题数量不一致：{property_id}")
        check([row.get("ap_id") for row in embedded_aps] == [row["ap_id"] for row in expected_aps], f"逐性质原子命题顺序或编号不一致：{property_id}")
        for embedded, expected in zip(embedded_aps, expected_aps):
            for field, value in expected.items():
                check(embedded.get(field) == value, f"嵌入原子命题字段与规范清单不一致：{expected['ap_id']}:{field}")
            expected_selected = [term_by_id[item] for item in expected["selected_term_binding_ids"]]
            expected_alternatives = [term_by_id[item] for item in expected["alternative_term_binding_ids"]]
            check(embedded.get("selected_source_bindings") == expected_selected, f"主选源码绑定没有按编号完整嵌入：{expected['ap_id']}")
            check(embedded.get("alternative_source_bindings") == expected_alternatives, f"备选源码绑定没有按编号完整嵌入：{expected['ap_id']}")
            expected_extra_keys = {"selected_source_bindings", "alternative_source_bindings", "status_legend_zh"}
            check(set(embedded) == set(expected) | expected_extra_keys, f"嵌入原子命题字段集合改变：{expected['ap_id']}")

        expected_dependencies = dependencies_by_property[key]
        check(record["author_input_dependencies"] == expected_dependencies, f"作者依赖关联出现漏行、去重、改序或串性质：{property_id}")
        identity_keys = {
            (row["system"], row["input_class"], row["artifact_name"])
            for row in expected_dependencies
        }
        expected_identities = [
            row for row in identity_rows
            if (row["system"], row["input_class"], row["artifact_name"]) in identity_keys
        ]
        check(record["current_input_identities"] == expected_identities, f"当前输入身份子集与作者关联不一致：{property_id}")
        expected_parameters = parameters_by_property[key]
        check(record["formula_parameters"] == expected_parameters, f"公式参数覆盖出现漏行、改序或串性质：{property_id}")
        check(record["official_document_context"] == documents_by_property[key], f"官方文档语境嵌入不一致：{property_id}")

        binding_summary = record["property_binding_summary"]
        check(binding_summary["binding_status"] == aggregate_binding_status(expected_aps), f"性质总体绑定状态计算不一致：{property_id}")
        check(binding_summary["mavlink_observability"] == aggregate_observability(expected_aps), f"性质总体 MAVLink 可观测性计算不一致：{property_id}")
        check(binding_summary["ap_count"] == len(expected_aps), f"性质原子命题摘要计数不一致：{property_id}")
        check(binding_summary["selected_binding_count"] == sum(len(row["selected_term_binding_ids"]) for row in expected_aps), f"主选绑定摘要计数不一致：{property_id}")
        check(binding_summary["alternative_binding_count"] == sum(len(row["alternative_term_binding_ids"]) for row in expected_aps), f"备选绑定摘要计数不一致：{property_id}")
        check(binding_summary["binding_status_counts"] == counter_dict(expected_aps, "binding_status"), f"绑定状态摘要分布不一致：{property_id}")
        check(binding_summary["observability_counts"] == counter_dict(expected_aps, "mavlink_observability"), f"可观测性摘要分布不一致：{property_id}")

        dependency_summary = record["author_dependency_summary"]
        check(dependency_summary["association_count"] == len(expected_dependencies), f"作者关联摘要数量不一致：{property_id}")
        check(dependency_summary["unique_input_identity_count"] == len(expected_identities), f"作者输入身份摘要数量不一致：{property_id}")
        check(dependency_summary["by_input_class"] == counter_dict(expected_dependencies, "input_class"), f"作者输入类别摘要不一致：{property_id}")
        check(dependency_summary["by_dependency_strength"] == counter_dict(expected_dependencies, "dependency_strength"), f"作者依赖强度摘要不一致：{property_id}")
        check(dependency_summary["by_current_identity_status"] == counter_dict(expected_dependencies, "current_identity_status"), f"当前身份状态摘要不一致：{property_id}")

        # Time semantics are independently derived from the preserved formula.
        formula = policy["binding_formula_interpretation"]
        expected_windows = [match.group(0) for match in re.finditer(r"F_\[([^\]]+)\]", formula)]
        temporal = record["temporal_semantics"]
        windows = temporal["explicit_eventually_windows"]
        check([row["raw_fragment"] for row in windows] == expected_windows, f"时间窗口没有按公式逐个保存：{property_id}")
        for window in windows:
            check(window["operator"] == "F", f"时间窗口算子不是 F：{property_id}:{window['raw_fragment']}")
            match = re.fullmatch(r"F_\[([^,]+),([^\]]+)\]", window["raw_fragment"])
            check(match is not None, f"时间窗口原样片段无法解析：{property_id}:{window['raw_fragment']}")
            if match is None:
                continue
            lower_raw, upper_raw = match.group(1).strip(), match.group(2).strip()
            lower = window["lower_bound"]
            upper = window["upper_bound"]
            check(lower["raw"] == lower_raw, f"时间下界与公式不一致：{property_id}:{window['raw_fragment']}")
            check(upper["raw"] == upper_raw, f"时间上界与公式不一致：{property_id}:{window['raw_fragment']}")
            if lower_raw == "0":
                check(lower["source_type"] == "PAPER_LITERAL" and lower["value"] == 0, f"公式字面下界 0 没有原样保存：{property_id}")
            if upper_raw == "2.5":
                check(property_id == "A.FLIPGeneral", f"2.5 秒被迁移到非 A.FLIPGeneral 性质：{property_id}")
                check(upper["source_type"] == "PAPER_LITERAL", "A.FLIPGeneral 的 2.5 没有标为论文原文字面值")
                check(upper["concrete_value_status"] == "AVAILABLE", "A.FLIPGeneral 的 2.5 没有标为可用具体值")
                check(upper["value"] == 2.5 and upper["unit"] == "s", "A.FLIPGeneral 的字面时间不是 2.5 秒")
            elif "k" in upper_raw:
                check(upper["source_type"] == "SYMBOLIC_UNRESOLVED", f"含 k 上界被错误标成具体来源：{property_id}")
                check(upper["concrete_value_status"] == "UNKNOWN", f"含 k 上界被错误标成已知具体值：{property_id}")
                check(upper["value"] is None, f"含 k 上界被人工补写数值：{property_id}")
            else:
                check(False, f"出现验证器尚未登记来源规则的时间上界：{property_id}:{upper_raw}")
            check(window["clock_domain"] == "UNSPECIFIED_BY_PAPER", f"论文未说明的时钟域被人工确定：{property_id}")
        expected_previous = "t-1" in formula
        check(temporal["uses_previous_observation"] is expected_previous, f"t-1 使用标志与公式不一致：{property_id}")
        previous = temporal["previous_observation_contract"]
        if expected_previous:
            check(isinstance(previous, dict), f"t-1 性质缺少上一有效观测契约：{property_id}")
            if isinstance(previous, dict):
                check(previous["relation_type"] == "PREVIOUS_OBSERVATION", f"t-1 被误解释成固定时间：{property_id}")
                check(previous["clock_domain"] == "TRACE_ORDER", f"t-1 没有按轨迹次序解释：{property_id}")
                check(previous["elapsed_time_value"] is None, f"t-1 被人工赋予固定时长：{property_id}")
        else:
            check(previous is None, f"不含 t-1 的性质却生成上一观测契约：{property_id}")

        # Markdown must expose the same identifiers and evidence as JSON.  The
        # row-prefix checks also catch accidental table truncation.
        check(markdown.startswith(f"# {property_id} 逐性质审核记录\n"), f"Markdown 标题与性质编号不一致：{property_id}")
        check(f"> {paper['description_en']}" in markdown, f"Markdown 缺少英文自然语言原文：{property_id}")
        check(paper["paper_formula_transcription"] in markdown, f"Markdown 缺少论文原样公式：{property_id}")
        check(paper["binding_formula_interpretation"] in markdown, f"Markdown 缺少用于绑定的公式解释：{property_id}")
        check(f"`{record['frozen_current_source']['commit']}`" in markdown, f"Markdown 缺少固定源码提交：{property_id}")
        check("最终状态仍为 `NOT_ASSESSED`" in markdown, f"Markdown 缺少未评估符合性的最终边界：{property_id}")
        expected_ap_ids = [row["ap_id"] for row in expected_aps]
        actual_ap_ids = re.findall(r"^### ([^：\n]+)：", markdown, flags=re.MULTILINE)
        check(actual_ap_ids == expected_ap_ids, f"Markdown 原子命题章节与 JSON 不一致：{property_id}")
        expected_binding_ids = [
            binding_id
            for ap in expected_aps
            for binding_id in ap["selected_term_binding_ids"] + ap["alternative_term_binding_ids"]
        ]
        actual_binding_ids = re.findall(r"^\| `((?:ARD|PX4)-TB-\d{3})` \|", markdown, flags=re.MULTILINE)
        check(actual_binding_ids == expected_binding_ids, f"Markdown 源码绑定表与 JSON 不一致：{property_id}")
        expected_association_ids = [row["association_id"] for row in expected_dependencies]
        actual_association_ids = re.findall(
            r"^\| `((?:A|PX)\.[^`]+:(?:InputP|InputC|InputE|PRECONDITION):\d{4})` \|",
            markdown,
            flags=re.MULTILINE,
        )
        check(actual_association_ids == expected_association_ids, f"Markdown 作者依赖表出现漏行、去重或改序：{property_id}")
        parameter_section = markdown.split("## 七、公式直接参数与实际运行值", 1)[-1].split("## 八、", 1)[0]
        actual_formula_parameters = re.findall(r"^\| `([^`]+)` \|", parameter_section, flags=re.MULTILINE)
        check(actual_formula_parameters == [row["formula_parameter"] for row in expected_parameters], f"Markdown 公式参数表与 JSON 不一致：{property_id}")
        actual_official_urls = re.findall(r"\]\((https://[^)]+)\)", markdown)
        check(actual_official_urls == [row["url"] for row in documents_by_property[key]], f"Markdown 官方文档链接与 JSON 不一致：{property_id}")

    # No unlisted JSON or Markdown record may hide in a system directory.
    for system, expected_ids in expected_files_by_system.items():
        property_dir = DATASET_ROOT / system / "properties"
        actual_json_ids = {path.stem for path in property_dir.glob("*.json")} if property_dir.is_dir() else set()
        actual_markdown_ids = {path.stem for path in property_dir.glob("*.md")} if property_dir.is_dir() else set()
        check(actual_json_ids == expected_ids, f"{system} JSON 文件集合与 51 条公式范围不一致")
        check(actual_markdown_ids == expected_ids, f"{system} Markdown 文件集合与 51 条公式范围不一致")
        check(actual_json_ids == actual_markdown_ids, f"{system} JSON 与 Markdown 没有一一配对")
    check(len(records) == 51 and len(records_by_key) == 51, "没有成功读取全部 51 条逐性质记录")
    check(schema_validated_records == 51, "接受结构约束检查的逐性质记录数量不是 51")

    # Every machine-readable object key must have a Chinese explanation in
    # both dictionary formats.  This protects the user's terminology contract
    # when a generator later adds a field or a dynamic status/count key.
    generated_record_keys: set[str] = set()
    for record in records:
        collect_object_keys(record, generated_record_keys)
    check(FIELD_DICTIONARY_JSON_PATH.is_file(), "缺少机器可读字段字典 FIELD_DICTIONARY.json")
    check(FIELD_DICTIONARY_MARKDOWN_PATH.is_file(), "缺少人工可读字段字典 FIELD_DICTIONARY.md")
    dictionary_field_keys: set[str] = set()
    markdown_field_keys: set[str] = set()
    if FIELD_DICTIONARY_JSON_PATH.is_file():
        try:
            field_dictionary = load_json(FIELD_DICTIONARY_JSON_PATH)
            field_rows = field_dictionary.get("fields", [])
            check(field_dictionary.get("schema_version") == "1.0", "字段字典 schema_version 不是 1.0")
            check(isinstance(field_rows, list), "字段字典 fields 不是数组")
            if isinstance(field_rows, list):
                dictionary_field_keys = {
                    str(row.get("field", "")) for row in field_rows if isinstance(row, dict)
                }
                check("" not in dictionary_field_keys, "字段字典包含空字段名")
                check(len(dictionary_field_keys) == len(field_rows), "字段字典字段名重复")
                check(
                    field_dictionary.get("field_count") == len(dictionary_field_keys),
                    "字段字典 field_count 与实际字段数不一致",
                )
                for row in field_rows:
                    if not isinstance(row, dict):
                        check(False, "字段字典包含非对象行")
                        continue
                    field_name = str(row.get("field", ""))
                    for explanation_field in ("family_zh", "meaning_zh", "value_type_zh", "audit_effect_zh"):
                        check(
                            bool(str(row.get(explanation_field, "")).strip()),
                            f"字段字典缺少中文解释：{field_name}:{explanation_field}",
                        )
                check(
                    dictionary_field_keys == generated_record_keys,
                    "机器字段字典没有与 51 条性质记录的递归字段键精确对应",
                )
        except (OSError, json.JSONDecodeError) as error:
            check(False, f"机器字段字典无法解析：{type(error).__name__}:{error}")
    if FIELD_DICTIONARY_MARKDOWN_PATH.is_file():
        markdown_dictionary = FIELD_DICTIONARY_MARKDOWN_PATH.read_text(encoding="utf-8")
        markdown_field_keys = set(
            re.findall(r"^\| `([^`]+)` \|", markdown_dictionary, flags=re.MULTILINE)
        )
        check(
            markdown_field_keys == generated_record_keys,
            "人工可读字段字典没有与 51 条性质记录的递归字段键精确对应",
        )
        check("NOT_ASSESSED" in markdown_dictionary, "人工可读字段字典缺少未评估符合性边界")
    check(
        dictionary_field_keys == markdown_field_keys == generated_record_keys,
        "两个字段字典版本与实际性质记录的字段集合不一致",
    )

    # Lossless aggregate joins: project canonical fields out of enriched AP
    # records, then compare complete ordered streams with the canonical tables.
    flattened_aps: list[dict[str, Any]] = []
    flattened_dependencies: list[dict[str, Any]] = []
    flattened_parameters: list[dict[str, Any]] = []
    for key in property_keys:
        record = records_by_key.get(key)
        if record is None:
            continue
        for embedded in record["atomic_propositions"]:
            flattened_aps.append({field: embedded[field] for field in ap_rows[0]})
        flattened_dependencies.extend(record["author_input_dependencies"])
        flattened_parameters.extend(record["formula_parameters"])
    check(flattened_aps == ap_rows, "51 条记录合并后没有逐行还原 178 个原子命题")
    check(flattened_dependencies == dependency_rows, "51 条记录合并后没有逐行还原 7,569 条作者关联")
    check(flattened_parameters == parameter_rows, "51 条记录合并后没有逐行还原 20 条公式参数覆盖")
    check(len(flattened_aps) == 178, "逐性质连接后的原子命题数量不是 178")
    check(len(flattened_dependencies) == 7569, "逐性质连接后的作者关联数量不是 7,569")
    check(len(flattened_parameters) == 20, "逐性质连接后的公式参数覆盖数量不是 20")
    check(Counter(row["ap_id"] for row in flattened_aps) == Counter(row["ap_id"] for row in ap_rows), "原子命题连接出现重复或丢失")
    check(Counter(row["association_id"] for row in flattened_dependencies) == Counter(row["association_id"] for row in dependency_rows), "作者关联连接出现重复或丢失")
    check(Counter((row["system"], row["policy_id"], row["formula_parameter"]) for row in flattened_parameters) == Counter(parameter_keys), "公式参数连接出现重复或丢失")

    # Exactly one non-zero concrete elapsed-time upper bound is allowed: the
    # 2.5-second literal printed for A.FLIPGeneral.  All k bounds stay unknown.
    nonzero_concrete_uppers: list[tuple[str, Any, Any]] = []
    k_window_properties: set[str] = set()
    previous_properties: set[str] = set()
    for key in property_keys:
        record = records_by_key.get(key)
        if record is None:
            continue
        temporal = record["temporal_semantics"]
        if temporal["uses_previous_observation"]:
            previous_properties.add(key[1])
        for window in temporal["explicit_eventually_windows"]:
            upper = window["upper_bound"]
            if upper["value"] not in (None, 0):
                nonzero_concrete_uppers.append((key[1], upper["value"], upper["unit"]))
            if "k" in upper["raw"]:
                k_window_properties.add(key[1])
                check(upper["value"] is None, f"含 k 时间窗口出现具体值：{key[1]}")
    check(nonzero_concrete_uppers == [("A.FLIPGeneral", 2.5, "s")], "非零具体时间值不再仅有 A.FLIPGeneral 的论文原文 2.5 秒")
    check(k_window_properties == {"A.FLIP3", "A.BRAKE1", "A.DRIFT1", "PX.GPS.FS1"}, "含 k 性质集合改变或有 k 被遗漏")
    expected_previous_properties = {
        row["policy_id"] for row in policies
        if "t-1" in row["binding_formula_interpretation"]
    }
    check(previous_properties == expected_previous_properties, "t-1 性质集合与论文公式不一致")

    # Catalog JSON/CSV rows are rebuilt from records.  System catalogs use
    # paths relative to their system directory; root paths must be prefixed by
    # the system so that every published link resolves from its own catalog.
    all_system_catalog_rows: list[dict[str, Any]] = []
    for system in ("ArduPilot", "PX4"):
        system_records = [records_by_key[key] for key in property_keys if key[0] == system and key in records_by_key]
        expected_rows = [catalog_row_from_record(record) for record in system_records]
        catalog_json_path = DATASET_ROOT / system / "property_catalog.json"
        catalog_csv_path = DATASET_ROOT / system / "property_catalog.csv"
        catalog_markdown_path = DATASET_ROOT / system / "property_catalog.md"
        check(catalog_json_path.is_file(), f"缺少 {system} property_catalog.json")
        check(catalog_csv_path.is_file(), f"缺少 {system} property_catalog.csv")
        check(catalog_markdown_path.is_file(), f"缺少 {system} property_catalog.md")
        if not (catalog_json_path.is_file() and catalog_csv_path.is_file() and catalog_markdown_path.is_file()):
            continue
        catalog = load_json(catalog_json_path)
        header, csv_rows = load_csv(catalog_csv_path)
        markdown = catalog_markdown_path.read_text(encoding="utf-8")
        check(catalog["schema_version"] == "1.0", f"{system} 目录 schema_version 不是 1.0")
        check(catalog["system"] == system, f"{system} 目录系统字段错误")
        check(catalog["properties"] == expected_rows, f"{system} JSON 目录行与逐性质记录不一致")
        check(header == list(CATALOG_FIELDS), f"{system} CSV 目录表头不一致")
        check(csv_rows == csv_projection(expected_rows), f"{system} CSV 目录与 JSON 目录不一致")
        expected_counts = {
            "properties": len(expected_rows),
            "atomic_propositions": sum(row["ap_count"] for row in expected_rows),
            "author_dependency_associations": sum(row["author_dependency_count"] for row in expected_rows),
            "formula_parameters": sum(row["formula_parameter_count"] for row in expected_rows),
        }
        check(catalog["counts"] == expected_counts, f"{system} 目录汇总计数不一致")
        for row in expected_rows:
            json_target = DATASET_ROOT / system / row["json_record"]
            markdown_target = DATASET_ROOT / system / row["markdown_record"]
            check(json_target.is_file(), f"{system} 目录 JSON 链接目标不存在：{row['property_id']}")
            check(markdown_target.is_file(), f"{system} 目录 Markdown 链接目标不存在：{row['property_id']}")
            prefix = f"| {row['paper_order']} | `{row['property_id']}` |"
            check(markdown.count(prefix) == 1, f"{system} Markdown 目录行与 JSON 不一致：{row['property_id']}")
            check(f"]({row['json_record']})" in markdown, f"{system} Markdown 目录缺少 JSON 链接：{row['property_id']}")
            check(f"]({row['markdown_record']})" in markdown, f"{system} Markdown 目录缺少审核页链接：{row['property_id']}")
        check("NOT_ASSESSED" in markdown, f"{system} Markdown 目录缺少符合性边界说明")
        all_system_catalog_rows.extend(expected_rows)

    root_json_path = DATASET_ROOT / "property_catalog.json"
    root_csv_path = DATASET_ROOT / "property_catalog.csv"
    check(root_json_path.is_file(), "缺少根 property_catalog.json")
    check(root_csv_path.is_file(), "缺少根 property_catalog.csv")
    if root_json_path.is_file() and root_csv_path.is_file():
        root_catalog = load_json(root_json_path)
        root_header, root_csv_rows = load_csv(root_csv_path)
        check(root_catalog["schema_version"] == "1.0", "根目录 schema_version 不是 1.0")
        check(root_catalog["dataset_id"] == manifest["dataset_id"], "根目录数据集编号不一致")
        root_rows = root_catalog["properties"]
        check(len(root_rows) == 51, "根目录性质行数不是 51")
        check(root_header == list(CATALOG_FIELDS), "根 CSV 目录表头不一致")
        check(root_csv_rows == csv_projection(root_rows), "根 CSV 目录与根 JSON 目录不一致")
        check(
            [{key: row[key] for key in CATALOG_FIELDS if key not in {"json_record", "markdown_record"}} for row in root_rows]
            == [{key: row[key] for key in CATALOG_FIELDS if key not in {"json_record", "markdown_record"}} for row in all_system_catalog_rows],
            "根目录除路径外的字段与两个系统目录不一致",
        )
        for row in root_rows:
            expected_json = f"{row['system']}/properties/{row['property_id']}.json"
            expected_markdown = f"{row['system']}/properties/{row['property_id']}.md"
            check(row["json_record"] == expected_json, f"根目录 JSON 路径没有包含系统目录：{row['property_id']}")
            check(row["markdown_record"] == expected_markdown, f"根目录 Markdown 路径没有包含系统目录：{row['property_id']}")
            check((DATASET_ROOT / row["json_record"]).is_file(), f"根目录 JSON 链接目标不存在：{row['property_id']}")
            check((DATASET_ROOT / row["markdown_record"]).is_file(), f"根目录 Markdown 链接目标不存在：{row['property_id']}")
        expected_root_counts = {
            "properties": 51,
            "ArduPilot": 30,
            "PX4": 21,
            "atomic_propositions": 178,
            "author_dependency_associations": 7569,
            "formula_parameters": 20,
        }
        check(root_catalog["counts"] == expected_root_counts, "根目录汇总计数不一致")

    report = {
        "schema_version": "1.0",
        "validator": "validate_property_records.py",
        "result": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "counts": {
            "property_records": len(records),
            "property_records_by_system": dict(Counter(record["system"] for record in records)),
            "joined_atomic_propositions": len(flattened_aps),
            "joined_author_dependency_associations": len(flattened_dependencies),
            "joined_formula_parameter_rows": len(flattened_parameters),
            "canonical_term_binding_rows": len(term_rows),
            "validated_source_ranges": len(validated_source_ranges),
            "official_document_records": len(documents),
            "schema_validated_records": schema_validated_records,
            "curated_default_evidence_locations": len(checked_default_evidence_locations),
            "properties_with_previous_observation": len(previous_properties),
            "properties_with_symbolic_k": len(k_window_properties),
            "explained_unique_record_fields": len(generated_record_keys),
        },
        "frozen_source_commits": {
            system: {
                "expected": EXPECTED_COMMITS[system],
                "manifest": manifest["sources"][MANIFEST_SOURCE_KEYS[system]]["commit"],
                "checkout": observed_commits.get(system, ""),
            }
            for system in EXPECTED_COMMITS
        },
        "field_definitions_zh": {
            "schema_version": "验证报告结构版本；1.0 表示本验证器采用的首版报告接口。",
            "validator": "执行检查的验证器文件名。",
            "result": "总体结果；PASS 表示全部自动检查通过，FAIL 表示至少一项失败。",
            "checks": "实际执行的布尔检查总数。",
            "failures": "中文失败说明列表；为空才允许 result 为 PASS。",
            "counts": "本次从交付文件重新统计的数量，不是人工填写结论。",
            "frozen_source_commits": "固定源码提交的期望值、来源清单值和当前检出值三方对照。",
            "schema_validation_engine": "逐条检查 JSON 记录结构所用的 Python 库及验证器；无法导入库时使用本文件内置的显式结构检查。",
            "explained_unique_record_fields": "递归扫描 51 条性质记录后，在中英文对照字段字典中逐项解释的唯一机器字段数量。",
        },
        "status_definitions_zh": {
            "PASS": "通过；仅说明本验证器覆盖的数据结构、连接、路径和保守时间语义检查均成立。",
            "FAIL": "失败；至少一项交付一致性检查不成立，必须查看 failures。",
            "NOT_ASSESSED": "未评估；没有判断当前 ArduPilot 或 PX4 是否满足论文性质。",
        },
        "schema_validation_engine": schema_validation_engine,
        "scope_note_zh": (
            "通过只证明 51 条逐性质记录完整保留 178 个原子命题、7,569 条作者候选关联、"
            "20 条公式参数覆盖、当前源码绑定、官方文档语境和未虚构的时间说明；"
            "不证明 PGFuzz 公式是当前官方规范，不证明候选输入具有真实因果依赖，也不证明固件符合性质。"
        ),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_zh = "通过（PASS）" if not failures else "失败（FAIL）"
    print(
        f"逐性质记录验证：{result_zh}；检查 {checks} 项，失败 {len(failures)} 项；"
        f"性质 {len(records)}，原子命题 {len(flattened_aps)}，作者关联 {len(flattened_dependencies)}，"
        f"公式参数 {len(flattened_parameters)}。"
    )
    print(f"验证报告：{REPORT_PATH}")
    if failures:
        for failure in failures[:40]:
            print(f"- {failure}")
        if len(failures) > 40:
            print(f"- 其余 {len(failures) - 40} 项失败见验证报告。")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
