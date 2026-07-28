#!/usr/bin/env python3
"""Build the 51 auditable PGFuzz per-property records and catalogs."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DATASET_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = DATASET_ROOT.parents[1]

FORMULA_PATH = DATASET_ROOT / "table_xii_formula_inventory.json"
AP_PATH = DATASET_ROOT / "atomic_proposition_bindings.json"
TERM_PATH = DATASET_ROOT / "term_source_bindings.json"
DEPENDENCY_PATH = DATASET_ROOT / "author_input_dependencies.json"
IDENTITY_PATH = DATASET_ROOT / "current_input_identity_map.json"
PARAMETER_PATH = DATASET_ROOT / "formula_parameter_coverage.json"
MANIFEST_PATH = DATASET_ROOT / "source_manifest.json"
DOCUMENT_PATH = DATASET_ROOT / "official_document_context.json"

STATUS_ZH = {
    "HISTORICAL_PROPERTY_SEED": "历史性质种子；来自论文，尚未被当前官方材料重新确认为规范",
    "NOT_ASSESSED": "未评估；不表示当前固件满足或违反该性质",
    "EXACT": "精确绑定；该绑定行的局部实体身份及该行所述局部含义有直接证据，不代表整条命题或性质正确",
    "MODELLED": "建模绑定；需要单位、坐标、上下文或历史样本解释",
    "UNRESOLVED": "未解决；证据不足，禁止猜测",
    "DIRECT": "直接可观测；字段直接携带所需值，仍需解码和有效性检查",
    "DERIVED": "派生可观测；需要组合字段、保存历史或换算",
    "CONDITIONAL": "有条件可观测；消息、实例、有效性或配置条件必须成立",
    "INSTRUMENTATION_REQUIRED": "需要插桩；标准 MAVLink 没有等价字段",
    "PRIMARY_VALUE": "主真值来源；当前选定语义组用于判真",
    "SUPPORTING_EVIDENCE": "辅助证据；说明形成、消费或发送路径，不增加合取条件",
    "ALTERNATIVE_SEMANTICS": "替代语义；与主组互斥，默认不参与判真",
    "PRIMARY_SELECTED": "已选定唯一主语义组",
    "PRIMARY_WITH_ALTERNATIVES": "已选主语义组，同时保留互斥替代解释",
    "UNRESOLVED_PRIMARY": "主语义未解决，补证前不能判真",
    "InputP": "配置参数输入",
    "InputC": "命令、模式或遥控输入",
    "InputE": "仿真环境或故障输入",
    "PRECONDITION": "作者制品明确保存的前置设置",
    "CANDIDATE_ASSOCIATION": "候选关联；作者列入输入文件，但未公开逐项因果证明",
    "EXPLICIT_PRECONDITION": "明确前置设置；只证明作者旧实验先设置该值",
    "EXACT_CURRENT_DEFINITION": "当前同名定义已找到",
    "RENAMED_CURRENT_DEFINITION": "当前更名或迁移后的定义已找到",
    "CURRENT_DEFINITION_NOT_FOUND": "当前定义未找到",
    "COMMAND_XML_DEFINITION_FOUND": "当前 MAVLink 命令 XML 定义已找到",
    "COMMAND_XML_DEFINITION_NOT_FOUND": "当前 MAVLink 命令 XML 定义未找到",
    "SPECIAL_CONTROL_INPUT": "特殊控制输入；不是普通配置参数",
    "NOT_TESTED": "未执行运行时写入与生效验证",
    "NOT_APPLICABLE": "不适用",
    "PAPER_LITERAL": "论文公式字面数值",
    "SYMBOLIC_UNRESOLVED": "符号边界未解析为当前具体数值",
    "PREVIOUS_OBSERVATION": "上一有效观测样本，不是固定秒数以前",
    "UNSPECIFIED_BY_PAPER": "论文未说明时钟域或时间戳载体",
    "AVAILABLE": "有可追溯具体值；本数据集只在论文明确给出数值时使用",
    "UNKNOWN": "具体值未知；不得自行补写数值",
    "TRACE_ORDER": "轨迹样本顺序；只表示上一有效样本，不等于固定经过时间",
    "CURATED_FROZEN_SOURCE_RESOLUTION": "依据冻结源码中的直接宏或枚举证据人工复核出的默认值",
    "SOURCE_METADATA_LITERAL_OR_EXPRESSION": "参数目录中的字面值或尚未求值的源码表达式；不能自动当作具体数值",
    "CONTEXT_ONLY_NOT_CURRENT_REQUIREMENT_CONFIRMATION": "只作行为语境解释，不确认当前规范",
}

BINDING_KIND_ZH = {
    "ASSIGNMENT": "赋值位置",
    "ASSOCIATED_FIELD": "关联字段",
    "CLASS_MEMBER": "类成员",
    "COMMAND_ACCEPTANCE": "命令接受阶段",
    "COMMAND_ACK": "命令确认阶段",
    "CONTROL_SETPOINT": "控制目标值",
    "DERIVED_EXPRESSION": "派生表达式",
    "ENUM_CONSTANT": "枚举常量",
    "EXECUTION_STATE": "执行状态",
    "FUNCTION_RETURN": "函数返回值",
    "MAVLINK_ENCODER": "MAVLink 编码器",
    "MAVLINK_SENDER": "MAVLink 发送函数",
    "NON_EQUIVALENT_CANDIDATE": "非等价候选",
    "PAPER_PHASE_MODEL": "论文阶段模型",
    "PARAMETER_CONSUMER": "参数真实消费位置",
    "PARAMETER_DEFINITION": "参数定义",
    "PARAMETER_HANDLE": "参数句柄",
    "REMOVED_PARAMETER": "当前已删除参数",
    "SELECTION_GUARD": "运行时选择条件",
    "SEMANTIC_CANDIDATE": "语义候选",
    "STATE_FIELD": "状态字段",
    "TRACE_PREVIOUS_SAMPLE": "轨迹上一有效样本",
    "UNRESOLVED_ABSTRACTION": "未解决的论文抽象",
    "UNRESOLVED_BOUND": "未解决时间边界",
    "UORB_FIELD": "PX4 uORB 消息字段",
}

TRANSPORT_ZH = {
    "observed_in_frozen_runtime_parameter_download": "已在冻结运行参数下载中出现",
    "protocol_capable_runtime_presence_not_observed": "参数协议具备传输能力，但未在冻结运行下载中确认出现",
    "": "没有可用传输证据",
}

REBOOT_METADATA_ZH = {
    "True": "是；当前参数元数据标记修改后需要重启，但本任务未执行写入与重启生效测试",
    "": "未提取到重启元数据；不能解释为不需要重启",
}

IDENTITY_CONFIDENCE_ZH = {
    "EXACT_NAME_DEFINITION": "当前同名定义直接匹配",
    "EXACT_NAME_XML_DEFINITION": "当前 XML 中同名命令定义直接匹配",
    "CURATED_RENAME_EXACT": "经人工证据确认的精确更名",
    "CURATED_MIGRATION_MODELLED": "人工整理的建模迁移，不能当作严格等价",
    "CURATED_INSTANCE1_MIGRATION_MODELLED": "只对实例一整理的建模迁移",
    "MODELLED_SPECIAL_INPUT": "特殊输入的建模身份",
    "UNRESOLVED": "身份未解决",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def md(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def code(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return f"`{str(value).replace('`', 'ˋ')}`"


def status(value: str) -> str:
    if not value:
        return "—"
    explanation = STATUS_ZH.get(value) or IDENTITY_CONFIDENCE_ZH.get(value) or TRANSPORT_ZH.get(value)
    return f"`{value}`（{explanation or '原始状态值；详见总术语表'}）"


def source_link(path: str, line: int | str, label: str, end_line: int | str | None = None) -> str:
    if not path or not line:
        return md(label or "无当前位置")
    absolute = WORKSPACE_ROOT / path
    range_label = label
    if end_line and str(end_line) != str(line) and f"{line}-{end_line}" not in label:
        range_label = f"{label}-{end_line}"
    return f"[{md(range_label)}]({absolute}:{line})"


def source_locations_links(raw: str) -> str:
    if not raw:
        return "—"
    links = []
    for location in re.split(r"[;|]", raw):
        location = location.strip()
        match = re.fullmatch(r"(.+):(\d+)", location)
        if not match:
            links.append(code(location))
            continue
        path, line = match.group(1), int(match.group(2))
        links.append(source_link(path, line, location))
    return "<br>".join(links)


def counter_dict(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


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
    return max((row["mavlink_observability"] for row in rows), key=lambda item: order[item])


def temporal_semantics(policy: dict[str, Any]) -> dict[str, Any]:
    formula = policy["binding_formula_interpretation"]
    windows = []
    for match in re.finditer(r"F_\[([^\]]+)\]", formula):
        raw = match.group(0)
        bounds = match.group(1)
        lower, upper = (part.strip() for part in bounds.split(",", 1))
        if upper == "2.5":
            upper_record = {
                "raw": upper,
                "source_type": "PAPER_LITERAL",
                "concrete_value_status": "AVAILABLE",
                "value": 2.5,
                "unit": "s",
                "provenance_zh": "数值 2.5 和秒单位直接来自 PGFuzz 表十二该行公式与描述；不是当前固件参数。",
            }
        else:
            upper_record = {
                "raw": upper,
                "source_type": "SYMBOLIC_UNRESOLVED",
                "concrete_value_status": "UNKNOWN",
                "value": None,
                "unit": "秒（仅在论文实验确实使用秒时；当前具体值不可得）",
                "provenance_zh": (
                    "上界包含 k。论文方法用 100 次仿真的最大观测延迟估计 k，但没有公开该性质的完整轨迹、"
                    "具体 k、时钟载体或采样误差；不得把循环计数或 A.BRAKE1 示例的 12.7 秒迁移到本性质。"
                    if "k" in upper
                    else "论文只给符号边界，当前记录没有可追溯具体值。"
                ),
            }
            if "COM_POS_FS_DELAY" in upper:
                upper_record["additional_limit_zh"] = (
                    "COM_POS_FS_DELAY 是历史 PX4 参数；当前冻结版本未找到等价定义。"
                    "即使保留加法表达式，也不能生成当前具体秒数。"
                )
        windows.append(
            {
                "raw_fragment": raw,
                "operator": "F",
                "operator_zh": "最终发生：要求后件在印刷区间内某次成立",
                "lower_bound": {
                    "raw": lower,
                    "source_type": "PAPER_LITERAL",
                    "value": 0 if lower == "0" else None,
                    "unit": "秒（按论文的经过时间轴解释时）",
                },
                "upper_bound": upper_record,
                "interval_brackets_zh": "论文印刷使用方括号；本数据集保留原样，尚未据此运行监视器语义转换。",
                "start_event_zh": "论文只给当前前件成立的采样点，没有更精细的触发关联事件。",
                "end_event_zh": "相应 eventually 后件第一次成立的观测点。",
                "cancel_reset_zh": "论文未说明取消、重置或重复触发语义。",
                "clock_domain": "UNSPECIFIED_BY_PAPER",
                "clock_carrier_zh": "论文未公开是仿真时钟、机载启动时钟还是观察端到达时钟。",
                "measurement_uncertainty_zh": "UNKNOWN；论文未公开采样周期、传输延迟和测量不确定度。",
            }
        )
    uses_previous = "_t-1" in formula or "t-1" in formula
    return {
        "explicit_eventually_windows": windows,
        "uses_previous_observation": uses_previous,
        "previous_observation_contract": (
            {
                "relation_type": "PREVIOUS_OBSERVATION",
                "meaning_zh": "t-1 表示监视轨迹中同一信号的上一有效样本，不表示一秒以前。",
                "clock_domain": "TRACE_ORDER",
                "elapsed_time_value": None,
                "freshness_requirement_zh": "两个样本必须属于同一运行、同一坐标系和同一有效性阶段；跨重置比较无结论。",
            }
            if uses_previous
            else None
        ),
        "concrete_time_policy_zh": (
            "仅保存论文明确写出的 2.5 秒；k、参数加 k 和 t-1 均不补人工秒数。"
        ),
    }


def enrich_ap(
    ap_row: dict[str, Any],
    term_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = dict(ap_row)
    result["selected_source_bindings"] = [term_by_id[item] for item in ap_row["selected_term_binding_ids"]]
    result["alternative_source_bindings"] = [term_by_id[item] for item in ap_row["alternative_term_binding_ids"]]
    result["status_legend_zh"] = {
        value: STATUS_ZH[value]
        for value in sorted(
            {
                ap_row["binding_status"],
                ap_row["binding_selection_status"],
                ap_row["mavlink_observability"],
                "NOT_ASSESSED",
            }
        )
        if value in STATUS_ZH
    }
    return result


def build_record(
    policy: dict[str, Any],
    aps: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    identities: list[dict[str, Any]],
    formula_parameters: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    term_by_id: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    issue_definitions: dict[str, str],
) -> dict[str, Any]:
    system_key = "ardupilot" if policy["system"] == "ArduPilot" else "px4"
    enriched_aps = [enrich_ap(row, term_by_id) for row in aps]
    binding_status = aggregate_binding_status(aps)
    observability = aggregate_observability(aps)
    identity_keys = {
        (row["system"], row["input_class"], row["artifact_name"])
        for row in dependencies
    }
    local_identities = [
        row for row in identities
        if (row["system"], row["input_class"], row["artifact_name"]) in identity_keys
    ]
    issue_rows = [
        {"code": issue, "explanation_zh": issue_definitions[issue]}
        for issue in policy["issues"]
    ]
    status_values = {
        policy["dataset_role"], "NOT_ASSESSED", binding_status, observability,
        *(row["input_class"] for row in dependencies),
        *(row["dependency_strength"] for row in dependencies),
        *(row["current_identity_status"] for row in dependencies),
    }
    return {
        "schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "system": policy["system"],
        "property_id": policy["policy_id"],
        "paper_order": policy["paper_order"],
        "artifact_policy_directory": policy["artifact_policy_directory"],
        "dataset_role": policy["dataset_role"],
        "implementation_satisfaction": "NOT_ASSESSED",
        "status_legend_zh": {
            value: STATUS_ZH[value]
            for value in sorted(status_values)
            if value in STATUS_ZH
        },
        "frozen_current_source": manifest["sources"][system_key],
        "paper_evidence": {
            "paper": manifest["sources"]["pgfuzz_pdf"],
            "table": "Table XII",
            "page_one_based": 18,
            "row_property_id": policy["policy_id"],
            "description_en": policy["description_en"],
            "description_zh": policy["description_zh"],
            "template": policy["template"],
            "paper_formula_transcription": policy["paper_formula_transcription"],
            "binding_formula_interpretation": policy["binding_formula_interpretation"],
            "inherits_from": policy["inherits_from"],
            "issues": issue_rows,
        },
        "official_document_context": documents,
        "official_context_limit_zh": (
            "官方页面只用于解释模式、参数或消息的当前语境；没有逐句重新提取并确认本论文公式，"
            "因此本条仍是历史性质种子。"
        ),
        "temporal_semantics": temporal_semantics(policy),
        "property_binding_summary": {
            "binding_status": binding_status,
            "mavlink_observability": observability,
            "ap_count": len(enriched_aps),
            "selected_binding_count": sum(len(row["selected_term_binding_ids"]) for row in aps),
            "alternative_binding_count": sum(len(row["alternative_term_binding_ids"]) for row in aps),
            "binding_status_counts": counter_dict(aps, "binding_status"),
            "observability_counts": counter_dict(aps, "mavlink_observability"),
            "conclusion_limit_zh": "绑定只回答实体位置与观测方法，不评估固件是否满足公式。",
        },
        "atomic_propositions": enriched_aps,
        "formula_parameters": formula_parameters,
        "parameter_value_contract_zh": {
            "artifact_default_raw": "作者旧制品保存的默认栏，不等于当前源码默认值。",
            "current_default_raw_catalog": "参数目录解析器的原始默认字段；部分 ArduPilot 行带有已知的额外右括号。",
            "current_default": "规范化或经冻结源码复核的当前默认值；其证据状态和源位置必须同时查看。",
            "current_runtime_value": "冻结 SITL 参数下载中的实际值，只代表该运行配置。",
            "runtime_mutability": (
                "默认值不是固定运行值。参数协议可传输只说明接口能力；是否允许飞行中修改、是否需要重启、"
                "何时被模块重新读取及修改后是否影响行为，必须逐参数实测。本数据集的写入验证均为 NOT_TESTED。"
            ),
        },
        "author_dependency_summary": {
            "association_count": len(dependencies),
            "unique_input_identity_count": len(local_identities),
            "by_input_class": counter_dict(dependencies, "input_class"),
            "by_dependency_strength": counter_dict(dependencies, "dependency_strength"),
            "by_current_identity_status": counter_dict(dependencies, "current_identity_status"),
            "claim_limit_zh": (
                "PGFuzz 输入文件是高召回候选关联。除明确前置设置外，公开制品没有给出每行到命题的完整数据流证明。"
            ),
        },
        "author_input_dependencies": dependencies,
        "current_input_identities": local_identities,
        "audit_boundary_zh": {
            "requirement_origin": "性质来自 PGFuzz 论文表十二，不由当前源码控制流反推。",
            "source_binding": "当前源码只用于身份、真值条件、有效性和观测方案。",
            "static_analysis": "尚未执行用户下一阶段要求的当前源码依赖静态分析。",
            "conformance": "没有执行完整轨迹监测、fuzz campaign 或实现符合性判断。",
        },
    }


def render_binding_table(bindings: list[dict[str, Any]], heading: str) -> list[str]:
    lines = [f"### {heading}", ""]
    if not bindings:
        lines += ["本原子命题没有该类绑定。", ""]
        return lines
    lines += [
        "| 绑定编号 | 词项/角色/候选组 | 当前源码实体与位置 | 类型与单位/坐标 | 真值和有效性 | 置信度 | MAVLink 观测 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in bindings:
        kind = f"{code(row['binding_kind'])}（{BINDING_KIND_ZH.get(row['binding_kind'], '绑定类型')}）"
        role = status(row["binding_role"])
        location = source_link(
            row["source_path"],
            row["source_line"],
            f"{row['symbol']} @ {row['source_path']}:{row['source_line']}",
            row["source_end_line"],
        )
        if row["function_context"]:
            location += f"<br>函数上下文：{code(row['function_context'])}"
        truth = f"{md(row['truth_condition_zh'])}<br>有效性：{md(row['validity_freshness_zh'])}"
        observation = (
            f"{status(row['mavlink_observability'])}<br>字段：{code(row['mavlink_message_fields'])}"
            f"<br>换算：{md(row['observation_conversion_zh'])}<br>限制：{md(row['observation_limit_zh'])}"
        )
        lines.append(
            "| " + " | ".join(
                [
                    code(row["binding_id"]),
                    f"{code(row['term'])}<br>{role}<br>组：{code(row['candidate_group'])}<br>{kind}",
                    location,
                    f"{md(row['data_type'])}<br>{md(row['unit_coordinate'])}",
                    truth,
                    f"{status(row['confidence'])}<br>{md(row['confidence_reason_zh'])}",
                    observation,
                ]
            ) + " |"
        )
    lines.append("")
    return lines


def render_record(record: dict[str, Any], issue_definitions: dict[str, str]) -> str:
    p = record["paper_evidence"]
    summary = record["property_binding_summary"]
    lines = [
        f"# {record['property_id']} 逐性质审核记录",
        "",
        "## 一、先解释本页术语",
        "",
        "- `MTL` 是 `Metric Temporal Logic`，中文为“度量时序逻辑”；这里严格保存 PGFuzz 论文印刷公式，不自动修正为当前规范。",
        "- `MITL` 是 `Metric Interval Temporal Logic`，中文为“度量区间时序逻辑”；它是使用时间区间的 MTL 限制形式。本数据集不能笼统声称 51 条印刷式都属于语法正确的严格 MITL。",
        "- `AP` 是 `Atomic Proposition`，中文为“原子命题”；它是公式中可分别判定真假的最小条件。",
        "- `G` 是 `Globally`，中文为“全局成立”；`F_[a,b]` 是 `Eventually within interval`，中文为“在区间内最终成立”；`t-1` 是上一有效样本而不是一秒前，`k` 是论文未公开具体值的经验上界。",
        "- `source binding` 中文为“源码绑定”；它把论文词项对应到当前提交中的变量、字段、函数、赋值、消息编码或参数消费位置。",
        "- `MAVLink` 是 `Micro Air Vehicle Link`，中文为“微型飞行器通信协议”；本页用它说明命题能否从飞控外部观测。",
        "- `InputP`、`InputC`、`InputE` 分别是 `Parameter Input`（配置参数输入）、`Command Input`（命令/遥控输入）和 `Environmental Input`（仿真环境输入）；`PRECONDITION` 是作者旧实验明确保存的前置设置。",
        "- 作者参数原值中的 `TRUE` 是旧制品的“需要重启”标记；`X` 是公开代码未进一步定义的占位符，不能解释为 0、假、任意范围或具体单位。覆盖表中的 `True/False` 只表示作者文件列出/未列出该参数。",
        "- `SITL` 是 `Software In The Loop`，中文为“软件在环仿真”；本页的运行参数值只属于所列冻结仿真实例。`SHA-256` 是 256 位散列校验，只用来检查证据文件是否改变。",
        "- `EXACT`、`MODELLED`、`UNRESOLVED` 分别表示精确绑定、需要语义建模和证据未解决；它们不表示性质通过。",
        "- `DIRECT`、`DERIVED`、`CONDITIONAL`、`INSTRUMENTATION_REQUIRED` 分别表示直接观测、派生观测、有条件观测和需要源码插桩。",
        "- `NOT_ASSESSED` 表示“未评估当前实现是否满足性质”；本页所有符合性字段固定为该值。",
        "- `data type` 中文为“数据类型”，说明值在源码中的存储种类；`unit/coordinate` 中文为“单位/坐标系”，说明数值尺度、方向和参考面。表中保留精确源码/元数据原值；源码绑定的 100 种数据类型和 61 种单位/坐标原值，以及当前输入目录的 7 种类型和 28 种单位原值，均在 [类型与单位字典](../../TYPE_UNIT_DICTIONARY.md) 中逐项解释。",
        "- 共同概念见 [总术语表](../../GLOSSARY.md)；本页结构化记录的全部机器字段逐项解释见 [字段字典](../../FIELD_DICTIONARY.md)。",
        "",
        "## 二、性质身份和证据边界",
        "",
        f"- 系统：{record['system']}；论文顺序：{record['paper_order']}；作者制品目录：{code(record['artifact_policy_directory'])}。",
        f"- 数据角色：{status(record['dataset_role'])}。",
        f"- 实现符合性：{status(record['implementation_satisfaction'])}。",
        f"- 当前源码提交：{code(record['frozen_current_source']['commit'])}；范围：{md(', '.join(record['frozen_current_source']['scope']))}。",
        f"- 论文证据：PGFuzz 表十二，第 18 页，PDF SHA-256 为 {code(p['paper']['sha256'])}。",
        "- 边界：当前源码只提供实体身份和观测路径；没有从现有 `if`、超时或控制逻辑反推出性质，也没有判断实现合规。",
        "",
        "## 三、论文原文、公式与问题",
        "",
        f"> {p['description_en']}",
        "",
        f"中文解释：{p['description_zh']}",
        "",
        f"模板：{code(p['template'])}。论文原样公式：",
        "",
        "```text",
        p["paper_formula_transcription"],
        "```",
        "",
        "用于绑定的解释（继承行会展开，但不覆盖论文原文）：",
        "",
        "```text",
        p["binding_formula_interpretation"],
        "```",
        "",
    ]
    if p["inherits_from"]:
        lines += [f"继承来源：{code(p['inherits_from'])}；论文没有打印完整替换式。", ""]
    lines += ["已记录的公式问题：", ""]
    if p["issues"]:
        for item in p["issues"]:
            lines.append(f"- {code(item['code'])}：{item['explanation_zh']}")
    else:
        lines.append("- 本行没有在清单中登记特定问题；这不等于公式已由当前官方要求确认。")
    lines += ["", "## 四、官方文档语境", ""]
    if record["official_document_context"]:
        for doc in record["official_document_context"]:
            lines.append(
                f"- [{doc['title_zh']}（{doc['title_en']}）]({doc['url']})：{doc['relevance_zh']} "
                f"证据角色为 {status(doc['evidence_role'])}。"
            )
    else:
        lines.append("- 当前尚未登记逐性质官方页面；因此不能声称论文性质被当前文档确认。")
    lines += ["", record["official_context_limit_zh"], "", "## 五、时间与相邻样本语义", ""]
    temporal = record["temporal_semantics"]
    if temporal["explicit_eventually_windows"]:
        for window in temporal["explicit_eventually_windows"]:
            upper = window["upper_bound"]
            lines += [
                f"- 原样时间片段：{code(window['raw_fragment'])}；上界来源：{status(upper['source_type'])}。",
                f"  - 上界原值：{code(upper['raw'])}；具体值状态：{status(upper['concrete_value_status'])}；值：{md(upper['value'])}；单位说明：{md(upper['unit'])}。",
                f"  - 来源说明：{upper['provenance_zh']}",
                f"  - 起点：{window['start_event_zh']} 终点：{window['end_event_zh']}",
                f"  - 时钟域：{status(window['clock_domain'])}；{window['clock_carrier_zh']}",
                f"  - 取消/重置：{window['cancel_reset_zh']} 测量不确定度：{window['measurement_uncertainty_zh']}",
            ]
            if upper.get("additional_limit_zh"):
                lines.append(f"  - 额外限制：{upper['additional_limit_zh']}")
    else:
        lines.append("- 论文公式没有印刷 `F_[...]` 时间窗口。")
    if temporal["uses_previous_observation"]:
        previous = temporal["previous_observation_contract"]
        lines.append(f"- {code('t-1')}：{previous['meaning_zh']} {previous['freshness_requirement_zh']}")
    else:
        lines.append("- 本公式不使用 `t-1` 相邻样本记号。")
    lines += ["", temporal["concrete_time_policy_zh"], "", "## 六、原子命题与源码绑定", ""]
    lines += [
        f"总体绑定状态：{status(summary['binding_status'])}；总体外部观测：{status(summary['mavlink_observability'])}。",
        "",
    ]
    for ap in record["atomic_propositions"]:
        lines += [
            f"### {ap['ap_id']}：{code(ap['expression'])}",
            "",
            f"- 公式角色：{code(ap['role'])}；中文真值含义：{ap['truth_meaning_zh']}",
            f"- 绑定状态：{status(ap['binding_status'])}；语义组选择：{status(ap['binding_selection_status'])}。",
            f"- 选择理由：{ap['binding_selection_reason_zh']}",
            f"- 判定方案：{ap['evaluation_plan_zh']}",
            f"- MAVLink 可观测性：{status(ap['mavlink_observability'])}；字段：{code(','.join(ap['mavlink_observation_fields']))}。",
            "",
        ]
        lines += render_binding_table(ap["selected_source_bindings"], "主选源码绑定")
        lines += render_binding_table(ap["alternative_source_bindings"], "互斥备选源码绑定")
    lines += ["## 七、公式直接参数与实际运行值", ""]
    if record["formula_parameters"]:
        lines += [
            "| 论文参数 | 作者输入文件是否列出 | 当前身份 | 当前默认/运行值/单位 | MAVLink 参数传输与写入验证 | 当前定义位置 |",
            "|---|---|---|---|---|---|",
        ]
        for row in record["formula_parameters"]:
            lines.append(
                "| " + " | ".join(
                    [
                        code(row["formula_parameter"]),
                        "是" if row["present_in_author_input_files"] else "否；这是必须保留的作者清单缺口",
                        f"{status(row['current_identity_status'])}<br>当前名：{code(row['current_name'])}",
                        f"默认：{code(row['current_default'])}<br>默认证据：{status(row['current_default_evidence_status'])}<br>默认源：{source_locations_links(row['current_default_evidence_source'])}<br>{md(row['current_default_evidence_note_zh'])}<br>目录原值：{code(row['current_default_raw_catalog'])}<br>冻结运行值：{code(row['current_runtime_value'])}<br>单位：{code(row['current_units'])}",
                        f"{md(TRANSPORT_ZH.get(row['current_mavlink_parameter_transport'], row['current_mavlink_parameter_transport']))}<br>写入验证：{status(row['runtime_write_change_verification'])}",
                        source_locations_links(row["current_source_locations"]),
                    ]
                ) + " |"
            )
    else:
        lines.append("本公式没有被参数覆盖表识别为直接配置参数的词项。")
    lines += [
        "",
        "重要：作者旧默认值、当前源码默认值和冻结 SITL 实际值是三件不同的事。默认值通常可被配置覆盖；但是否可在飞行中修改、是否要求重启、何时生效，当前均未逐参数写入验证。",
        "",
        "## 八、PGFuzz 作者为本性质列出的全部依赖输入",
        "",
        f"共 {record['author_dependency_summary']['association_count']} 条性质—输入关联、{record['author_dependency_summary']['unique_input_identity_count']} 个去重后的当前输入身份。",
        "这些条目是候选关联，不是已经证明的最小因果依赖集；共享作者目录的行仍按每个逻辑性质分别保留。",
        "",
        "| 关联编号 | 类别 | 作者原始输入及文件位置 | 当前身份与证据 | 作者值域 | 当前默认/运行值 | 传输、重启与写入验证 | 与公式关系 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in record["author_input_dependencies"]:
        artifact = source_link(
            row["artifact_source_path"], row["artifact_source_line"],
            f"{row['artifact_source_path']}:{row['artifact_source_line']}"
        )
        current_evidence = source_locations_links(row["current_source_locations"])
        if row["current_alias_evidence"]:
            alias_match = re.fullmatch(r"(.+):(\d+)", row["current_alias_evidence"])
            alias_link = (
                source_link(alias_match.group(1), int(alias_match.group(2)), row["current_alias_evidence"])
                if alias_match else code(row["current_alias_evidence"])
            )
            current_evidence += f"<br>迁移证据：{alias_link}<br>{md(row['current_alias_note_zh'])}"
        lines.append(
            "| " + " | ".join(
                [
                    code(row["association_id"]),
                    status(row["input_class"]),
                    f"名称：{code(row['artifact_name'])}<br>原始行：{code(row['artifact_raw'])}<br>{artifact}",
                    f"{status(row['current_identity_status'])}<br>当前名：{code(row['current_name'])}<br>匹配：{code(row['current_match_confidence'])}（{md(IDENTITY_CONFIDENCE_ZH.get(row['current_match_confidence'], '详见身份限制'))}）<br>{current_evidence}",
                    f"作者默认：{code(row['artifact_default_raw'])}<br>最小：{code(row['artifact_min_raw'])}<br>最大：{code(row['artifact_max_raw'])}<br>第六列：{code(row['artifact_column_6_raw'])}",
                    f"当前默认：{code(row['current_default'])}<br>默认证据：{status(row['current_default_evidence_status'])}<br>目录原值：{code(row['current_default_raw_catalog'])}<br>运行值：{code(row['current_runtime_value'])}<br>单位：{code(row['current_units'])}",
                    f"{md(TRANSPORT_ZH.get(row['current_mavlink_parameter_transport'], row['current_mavlink_parameter_transport']))}<br>重启元数据：{md(REBOOT_METADATA_ZH.get(row['current_reboot_required'], '未登记原值：' + row['current_reboot_required']))}<br>写入：{status(row['runtime_write_change_verification'])}",
                    f"{status(row['dependency_strength'])}<br>公式直接词项：{'是' if row['appears_as_exact_formula_term'] else '否'}<br>{md(row['dependency_claim_limit_zh'])}",
                ]
            ) + " |"
        )
    lines += [
        "",
        "## 九、人工审核结论边界",
        "",
        f"- 性质来源：{record['audit_boundary_zh']['requirement_origin']}",
        f"- 源码绑定：{record['audit_boundary_zh']['source_binding']}",
        f"- 下一阶段静态分析：{record['audit_boundary_zh']['static_analysis']}",
        f"- 实现符合性：{record['audit_boundary_zh']['conformance']}",
        "",
        f"最终状态仍为 {status(record['implementation_satisfaction'])}。",
        "",
    ]
    return "\n".join(lines)


def catalog_row(record: dict[str, Any]) -> dict[str, Any]:
    p = record["paper_evidence"]
    s = record["property_binding_summary"]
    d = record["author_dependency_summary"]
    return {
        "paper_order": record["paper_order"],
        "system": record["system"],
        "property_id": record["property_id"],
        "template": p["template"],
        "description_zh": p["description_zh"],
        "description_en": p["description_en"],
        "paper_formula_transcription": p["paper_formula_transcription"],
        "binding_formula_interpretation": p["binding_formula_interpretation"],
        "inherits_from": p["inherits_from"] or "",
        "issue_codes": ";".join(item["code"] for item in p["issues"]),
        "ap_count": s["ap_count"],
        "property_binding_status": s["binding_status"],
        "mavlink_observability": s["mavlink_observability"],
        "selected_binding_count": s["selected_binding_count"],
        "alternative_binding_count": s["alternative_binding_count"],
        "author_dependency_count": d["association_count"],
        "unique_author_input_count": d["unique_input_identity_count"],
        "formula_parameter_count": len(record["formula_parameters"]),
        "official_document_count": len(record["official_document_context"]),
        "dataset_role": record["dataset_role"],
        "implementation_satisfaction": record["implementation_satisfaction"],
        "current_commit": record["frozen_current_source"]["commit"],
        "json_record": f"properties/{record['property_id']}.json",
        "markdown_record": f"properties/{record['property_id']}.md",
    }


def write_catalog(system: str, rows: list[dict[str, Any]]) -> None:
    system_dir = DATASET_ROOT / system
    payload = {
        "schema_version": "1.0",
        "system": system,
        "counts": {
            "properties": len(rows),
            "atomic_propositions": sum(row["ap_count"] for row in rows),
            "author_dependency_associations": sum(row["author_dependency_count"] for row in rows),
            "formula_parameters": sum(row["formula_parameter_count"] for row in rows),
        },
        "status_definitions_zh": {
            key: STATUS_ZH[key]
            for key in ("EXACT", "MODELLED", "UNRESOLVED", "DIRECT", "DERIVED", "CONDITIONAL", "INSTRUMENTATION_REQUIRED", "NOT_ASSESSED")
        },
        "properties": rows,
    }
    write_json(system_dir / "property_catalog.json", payload)
    with (system_dir / "property_catalog.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        f"# {system} PGFuzz 历史性质目录",
        "",
        "`MTL` 是度量时序逻辑；`AP` 是原子命题；`NOT_ASSESSED` 是未评估实现符合性。",
        "`EXACT`、`MODELLED`、`UNRESOLVED` 分别表示精确绑定、建模绑定和未解决绑定；都不等于性质通过。",
        "",
        f"共 {len(rows)} 条性质、{payload['counts']['atomic_propositions']} 个 AP、"
        f"{payload['counts']['author_dependency_associations']} 条作者依赖输入关联。",
        "",
        "| 顺序 | 性质 | 中文说明 | 绑定/观测状态 | AP | 作者关联 | 公式参数 | 审核记录 |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['paper_order']} | {code(row['property_id'])} | {md(row['description_zh'])} | "
            f"{status(row['property_binding_status'])}<br>{status(row['mavlink_observability'])} | "
            f"{row['ap_count']} | {row['author_dependency_count']} | {row['formula_parameter_count']} | "
            f"[{row['property_id']}.md]({row['markdown_record']}) / [{row['property_id']}.json]({row['json_record']}) |"
        )
    lines += ["", "所有 `implementation_satisfaction` 均为 `NOT_ASSESSED`，只表示尚未评估，不表示满足。", ""]
    (system_dir / "property_catalog.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    formula_payload = load_json(FORMULA_PATH)
    policies = formula_payload["policies"]
    ap_rows = load_json(AP_PATH)["rows"]
    term_payload = load_json(TERM_PATH)
    term_rows = term_payload["rows"]
    dependencies = load_json(DEPENDENCY_PATH)["association_rows"]
    identities = load_json(IDENTITY_PATH)["rows"]
    formula_parameters = load_json(PARAMETER_PATH)["rows"]
    manifest = load_json(MANIFEST_PATH)
    document_payload = load_json(DOCUMENT_PATH) if DOCUMENT_PATH.exists() else {"documents": []}
    documents = document_payload["documents"]

    ap_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    dependency_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    parameter_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    document_by_property: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    term_by_id = {row["binding_id"]: row for row in term_rows}
    for row in ap_rows:
        ap_by_property[(row["system"], row["property_id"])].append(row)
    for row in dependencies:
        dependency_by_property[(row["system"], row["policy_id"])].append(row)
    for row in formula_parameters:
        parameter_by_property[(row["system"], row["policy_id"])].append(row)
    for doc in documents:
        for property_id in doc["property_ids"]:
            document_by_property[(doc["system"], property_id)].append(doc)

    records = []
    catalogs: dict[str, list[dict[str, Any]]] = {"ArduPilot": [], "PX4": []}
    for policy in policies:
        key = (policy["system"], policy["policy_id"])
        record = build_record(
            policy,
            ap_by_property[key],
            dependency_by_property[key],
            identities,
            parameter_by_property[key],
            document_by_property[key],
            term_by_id,
            manifest,
            formula_payload["issue_definitions"],
        )
        property_dir = DATASET_ROOT / policy["system"] / "properties"
        write_json(property_dir / f"{policy['policy_id']}.json", record)
        (property_dir / f"{policy['policy_id']}.md").write_text(
            render_record(record, formula_payload["issue_definitions"]), encoding="utf-8"
        )
        records.append(record)
        catalogs[policy["system"]].append(catalog_row(record))

    for system, rows in catalogs.items():
        write_catalog(system, rows)

    root_rows = []
    for system in ("ArduPilot", "PX4"):
        for row in catalogs[system]:
            root_rows.append(
                {
                    **row,
                    "json_record": f"{system}/{row['json_record']}",
                    "markdown_record": f"{system}/{row['markdown_record']}",
                }
            )
    root_catalog = {
        "schema_version": "1.0",
        "dataset_id": manifest["dataset_id"],
        "counts": {
            "properties": len(records),
            "ArduPilot": len(catalogs["ArduPilot"]),
            "PX4": len(catalogs["PX4"]),
            "atomic_propositions": sum(len(record["atomic_propositions"]) for record in records),
            "author_dependency_associations": sum(len(record["author_input_dependencies"]) for record in records),
            "formula_parameters": sum(len(record["formula_parameters"]) for record in records),
        },
        "properties": root_rows,
    }
    write_json(DATASET_ROOT / "property_catalog.json", root_catalog)
    with (DATASET_ROOT / "property_catalog.csv").open("w", newline="", encoding="utf-8") as handle:
        rows = root_catalog["properties"]
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "schema_version": "1.0",
        **root_catalog["counts"],
        "term_binding_rows": len(term_rows),
        "unique_current_input_identities": len(identities),
        "official_document_records": len(documents),
        "binding_status": counter_dict(
            [{"value": record["property_binding_summary"]["binding_status"]} for record in records], "value"
        ),
        "implementation_satisfaction": "NOT_ASSESSED",
    }
    write_json(DATASET_ROOT / "validation" / "property_record_build_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
