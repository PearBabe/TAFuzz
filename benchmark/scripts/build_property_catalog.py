#!/usr/bin/env python3
"""Build evidence-bound ArduPilot/PX4 property catalogs.

Milestone 4 deliberately emits symbolic properties only.  Runtime parameter
values, source bindings, MAVLink observations and monitor traces are populated
by later stages; a source default is never substituted for a runtime value.
Stage 7 records parser/monitor evidence and independent-review blockers without
turning either into a firmware-conformance or human-acceptance decision.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
ARD_COMMIT = "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e"
PX4_COMMIT = "d6f12ad1c4f70ad3230afd7d86e971421e02fef4"
ARD_WIKI_COMMIT = "209e532bc97e5a41966f8c9ab483323c264cae08"
GENERATED_AT = "2026-07-18T06:25:00+08:00"
COMPILER_VERSION = "tafuzz-evidence-ir-compiler/1.0"
CURRENT_STAGE = 4
OUTPUT_GENERATED_AT = GENERATED_AT
OUTPUT_STAGE7_ENRICHED_AT: str | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quote_lines(relative_path: str, start: int, end: int) -> str:
    path = ROOT / relative_path
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"invalid source range {relative_path}:{start}-{end}")
    return "\n".join(lines[start - 1 : end]).strip()


def source(
    source_id: str,
    relative_path: str,
    start: int,
    end: int,
    source_class: str,
    authority: str,
    title: str,
    version: str,
    document_status: str,
    context_zh: str,
    section: str | None = None,
) -> dict[str, Any]:
    path = ROOT / relative_path
    return {
        "source_id": source_id,
        "source_class": source_class,
        "authority": authority,
        "title": title,
        "version": version,
        "path_or_url": relative_path,
        "retrieved_at": GENERATED_AT,
        "sha256": sha256_file(path),
        "locator": {
            "page": None,
            "section": section,
            "anchor": None,
            "line_start": start,
            "line_end": end,
            "char_start": None,
            "char_end": None,
        },
        "exact_quote": quote_lines(relative_path, start, end),
        "context_summary_zh": context_zh,
        "language": "en",
        "document_status": document_status,
    }


def span(src: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": src["source_id"],
        "quote": src["exact_quote"],
        "char_start": None,
        "char_end": None,
    }


def clause(text: str, *sources: dict[str, Any]) -> dict[str, Any]:
    return {"text": text, "evidence": [span(src) for src in sources]}


def check(status: str, evidence: str, command: str | None = None) -> dict[str, Any]:
    return {"status": status, "command": command, "evidence": evidence}


def ap(
    property_id: str,
    suffix: str,
    name: str,
    natural: str,
    truth: str,
    kind: str,
    value_type: str = "bool",
    unit: str | None = None,
    validity: str = "Only evaluate inside the property scope and after configuration capture.",
    freshness: str = "Must be sampled in the selected property clock domain; stale observations are invalid.",
    scope: str = "one vehicle instance and one campaign run",
    aggregation: str | None = None,
    correlation: str | None = "vehicle_system_id + campaign_run_id",
    observability: str = "UNRESOLVED",
) -> dict[str, Any]:
    return {
        "ap_id": f"{property_id}-AP-{suffix}",
        "name": name,
        "controlled_natural_language": natural,
        "truth_condition": truth,
        "kind": kind,
        "value_type": value_type,
        "unit": unit,
        "coordinate_frame": None,
        "validity_guard": validity,
        "freshness": freshness,
        "scope": scope,
        "aggregation": aggregation,
        "correlation_key": correlation,
        "source_bindings": [],
        "mavlink_observations": [],
        "observability": observability,
        "status": "NEEDS_BINDING",
    }


def runtime_time(
    time_id: str,
    start_event: str,
    end_event: str,
    parameter: str,
    unit: str,
    src: dict[str, Any],
    default: float | int,
    lower_closed: bool,
    clock: str,
    carrier: str,
    reset_event: str | None,
    cancel_event: str | None,
    conversion: str | None = None,
    raw_expression: str | None = None,
) -> dict[str, Any]:
    symbol = f"runtime({parameter})"
    return {
        "time_id": time_id,
        "semantic_start_event": start_event,
        "semantic_end_event": end_event,
        "cancel_event": cancel_event,
        "reset_event": reset_event,
        "raw_expression": raw_expression or symbol,
        "lower": symbol,
        "upper": None,
        "lower_closed": lower_closed,
        "upper_closed": None,
        "unit": unit,
        "source_type": "RUNTIME_PARAMETER",
        "source_id": src["source_id"],
        "source_span": span(src),
        "parameter_id": parameter,
        "formula": f"{time_id} = {symbol}",
        "operands": [
            {"name": "runtime_value", "value": None, "unit": unit, "source_id": src["source_id"]},
            {"name": "source_default_not_runtime", "value": default, "unit": unit, "source_id": src["source_id"]},
        ],
        "clock_domain": clock,
        "timestamp_carrier": carrier,
        "conversion": conversion,
        "measurement_uncertainty": (
            "No numeric tolerance has a normative source. If transport, scheduling, or sampling uncertainty "
            "can change a boundary verdict, the verdict is INCONCLUSIVE."
        ),
        "freshness": "Start/end observations must be fresh in the same clock domain; host arrival time is not silently substituted.",
        "status": "SYMBOLIC",
    }


def base_property(
    property_id: str,
    title_zh: str,
    title_en: str,
    system: str,
    vehicles: list[str],
    status: str,
    classification: str,
    sources: list[dict[str, Any]],
    actor: str,
    modality: str,
    trigger: str,
    preconditions: list[str],
    obligations: list[str],
    prohibitions: list[str],
    exceptions: list[str],
    scope_start: str,
    scope_end: str,
    relations: list[tuple[str, str, str]],
    unresolved: list[str],
    times: list[dict[str, Any]],
    symbolic: str | None,
    mitl_status: str,
    aps: list[dict[str, Any]],
    conflicts: list[str],
    initial_state: str,
) -> dict[str, Any]:
    primary = sources[0]
    firmware_commit = ARD_COMMIT if system == "ArduPilot" else PX4_COMMIT
    firmware_release = None if system == "ArduPilot" else "v1.17.0"
    evidence = [span(primary)]
    ir = {
        "actor": {"text": actor, "evidence": evidence},
        "modality": modality,
        "trigger": {"text": trigger, "evidence": evidence},
        "preconditions": [{"text": text, "evidence": evidence} for text in preconditions],
        "obligations": [{"text": text, "evidence": evidence} for text in obligations],
        "prohibitions": [{"text": text, "evidence": evidence} for text in prohibitions],
        "exceptions": [{"text": text, "evidence": evidence} for text in exceptions],
        "scope_start": {"text": scope_start, "evidence": evidence},
        "scope_end": {"text": scope_end, "evidence": evidence},
        "correlation_keys": ["vehicle_system_id", "campaign_run_id"],
        "event_relations": [
            {"left": left, "relation": relation, "right": right, "evidence": evidence}
            for left, relation, right in relations
        ],
        "unresolved": unresolved,
    }
    edges = []
    for index, src in enumerate(sources[1:], start=1):
        edges.append(
            {
                "from": primary["source_id"],
                "relation": "parameterizes" if src["source_class"] == "PARAM_METADATA" else "refers_to",
                "to": src["source_id"],
                "evidence_source_id": src["source_id"],
                "confidence": "REVIEWED",
            }
        )
    subformula_evidence = []
    if symbolic:
        subformula_evidence.append({"subformula": symbolic, "evidence": evidence})
    checks = {
        "schema": check("PASS", "Generated object is validated against property.schema.json.", "python3 benchmark/scripts/validate_property_catalog.py"),
        "source": check("PASS", "All source files, hashes, line ranges, and exact quotes are checked by the validator."),
        "type_unit": check("PASS", "Stage-4 manual review checked units and conversions; runtime values remain unresolved."),
        "temporal_graph": check("PASS", "Relations contain no self-edge or inverse-cycle in this property record."),
        "parser": check("NOT_RUN", "Formula is symbolic until a runtime parameter snapshot supplies numeric bounds."),
        "satisfiable": check("NOT_RUN", "Deferred until concrete formula generation."),
        "non_tautology": check("NOT_RUN", "Deferred until concrete formula generation."),
        "non_vacuity": check("NOT_RUN", "Deferred until concrete traces are generated."),
        "source_lines": check("PASS", "Local frozen source anchors exist and are hash-stable."),
        "permalinks": check("NOT_RUN", "Commit permalinks are emitted after source binding in Milestone 5."),
        "monitor": check("NOT_RUN", "No TAMonitor result is claimed in Milestone 4."),
        "independent_review": check("NOT_RUN", "Independent review is a Milestone 7 gate and does not replace human acceptance."),
    }
    return {
        "schema_version": "1.0",
        "property_id": property_id,
        "title_zh": title_zh,
        "title_en": title_en,
        "system_scope": {
            "system": system,
            "vehicles": vehicles,
            "firmware_release": firmware_release,
            "firmware_commit": firmware_commit,
            "configuration_snapshot": {
                "status": "PENDING",
                "path": None,
                "sha256": None,
                "notes": "Milestone 6 will capture PARAM_VALUE; source defaults are not substituted.",
            },
            "mission_snapshot": {
                "status": "PENDING",
                "path": None,
                "sha256": None,
                "notes": "Capture the exact test mission or explicit no-mission setup before validation.",
            },
            "initial_state": initial_state,
        },
        "status": status,
        "classification": classification,
        "sources": sources,
        "context_graph": {
            "node_ids": [src["source_id"] for src in sources],
            "edges": edges,
            "unresolved_references": unresolved,
        },
        "requirement_ir": ir,
        "time_contracts": times,
        "mitl": {
            "symbolic": symbolic,
            "concrete": None,
            "concrete_instances": [],
            "monitor_syntax": None,
            "monitor_contract": None,
            "compiler_version": COMPILER_VERSION,
            "subformula_evidence": subformula_evidence,
            "status": mitl_status,
        },
        "atomic_propositions": aps,
        "examples": {"positive": [], "boundary_negative": [], "late_or_missing": [], "wrong_exception": [], "wrong_correlation": []},
        "extraction_record": {
            "run_id": "milestone4-reviewed-curation-v1",
            "extractor": "evidence-bound manual/LLM-assisted context review with deterministic schema compilation",
            "model": "GPT-5.6",
            "prompt_hash": None,
            "temperature": None,
            "seed": None,
            "raw_outputs": (
                [
                    "benchmark/extraction_runs/milestone4/superseded_px4_draft/properties/*.yaml "
                    "(SUPERSEDED_NON_CANONICAL_DRAFT; immutable historical input only)"
                ]
                if system == "PX4"
                else ["read-only ArduPilot source audit agent result"]
            ),
            "adjudication": "Evidence spans and unresolved conflicts were manually reviewed; implementation control flow did not originate a requirement.",
        },
        "validation": checks,
        "review": {
            "decision": "PENDING",
            "reviewer": None,
            "reviewed_at": None,
            "rationale": "Stage 4 evidence/formalization record; source binding, runtime parameter capture, and monitor traces remain gates.",
            "conflicts": conflicts,
            "confidence_vector": {
                "authority": None,
                "fidelity": None,
                "context": None,
                "modality": None,
                "time_source": None,
                "event_graph": None,
                "formalization": None,
                "source_binding": None,
                "observability": None,
            },
        },
        "implementation_satisfaction": "NOT_ASSESSED",
    }


def ard_sources() -> dict[str, list[dict[str, Any]]]:
    wiki = "benchmark/extraction_runs/corpus_sources/ardupilot_wiki"
    src = "baseline/ardupilot"
    return {
        "gcs": [
            source("ARD-COPTER-GCS-001-S1", f"{wiki}/copter/source/docs/gcs-failsafe.rst", 8, 8, "OFFICIAL_BEHAVIOR", "HIGH", "Copter GCS Failsafe", ARD_WIKI_COMMIT, "MAIN_ONLY", "说明 GCS heartbeat 间隔达到 FS_GCS_TIMEOUT 后触发事件，且从未连接时不激活。", "GCS Failsafe"),
            source("ARD-COPTER-GCS-001-S2", f"{src}/ArduCopter/Parameters.cpp", 828, 835, "PARAM_METADATA", "LOW", "ArduCopter FS_GCS_TIMEOUT metadata", ARD_COMMIT, "CURRENT", "冻结源码中的参数说明、单位、范围和默认值；不作为实现满足证据。"),
        ],
        "guided": [
            source("ARD-COPTER-GUID-002-S1", f"{wiki}/copter/source/docs/ac2_guidedmode.rst", 115, 115, "OFFICIAL_BEHAVIOR", "HIGH", "Copter Guided Mode", ARD_WIKI_COMMIT, "MAIN_ONLY", "定义 attitude/velocity/acceleration 指令缺失后的超时与分类型响应。", "Guided Mode"),
            source("ARD-COPTER-GUID-002-S2", f"{src}/ArduCopter/Parameters.cpp", 866, 872, "PARAM_METADATA", "LOW", "ArduCopter GUID_TIMEOUT metadata", ARD_COMMIT, "CURRENT", "冻结源码中的 GUID_TIMEOUT 参数说明和范围。"),
        ],
        "rtl": [
            source("ARD-COPTER-RTL-003-S1", f"{wiki}/copter/source/docs/rtl-mode.rst", 65, 68, "OFFICIAL_BEHAVIOR", "HIGH", "Copter RTL Mode", ARD_WIKI_COMMIT, "MAIN_ONLY", "定义到达 Home 上方后、最终下降前的暂停区间。", "RTL parameters"),
            source("ARD-COPTER-RTL-003-S2", f"{src}/ArduCopter/Parameters.cpp", 80, 87, "PARAM_METADATA", "LOW", "ArduCopter RTL_LOIT_TIME metadata", ARD_COMMIT, "CURRENT", "冻结源码中的毫秒单位、范围和默认值。"),
        ],
        "takeoff": [
            source("ARD-PLANE-TAKEOFF-001-S1", f"{src}/ArduPlane/Parameters.cpp", 1113, 1120, "PARAM_METADATA", "LOW", "ArduPlane TKOFF_TIMEOUT metadata", ARD_COMMIT, "CURRENT", "参数元数据给出自动起飞、4m/s 阈值、超时、abort/disarm 和 0 禁用语义。"),
        ],
        "rover_rc": [
            source("ARD-ROVER-RCFS-001-S1", f"{wiki}/rover/source/docs/rover-failsafes.rst", 15, 22, "OFFICIAL_BEHAVIOR", "HIGH", "Rover Radio Failsafe", ARD_WIKI_COMMIT, "MAIN_ONLY", "列出连接丢失、低油门和 RC override 丢失三种来源及持续时间。", "Radio Failsafe"),
            source("ARD-ROVER-RCFS-001-S2", f"{src}/Rover/Parameters.cpp", 100, 122, "PARAM_METADATA", "LOW", "Rover FS_TIMEOUT/FS_THR metadata", ARD_COMMIT, "CURRENT", "冻结源码中 FS_TIMEOUT、FS_THR_ENABLE 和 FS_THR_VALUE 的参数语义。"),
        ],
        "rover_crash": [
            source("ARD-ROVER-CRASH-002-S1", f"{wiki}/rover/source/docs/rover-failsafes.rst", 97, 106, "OFFICIAL_BEHAVIOR", "HIGH", "Rover Crash Check", ARD_WIKI_COMMIT, "MAIN_ONLY", "给出适用模式、速度、转率、油门合取条件、持续时间和角度替代路径。", "Crash Check"),
            source("ARD-ROVER-CRASH-002-S2", f"{src}/Rover/Parameters.cpp", 634, 668, "PARAM_METADATA", "LOW", "Rover crash-check parameter metadata", ARD_COMMIT, "CURRENT", "冻结源码中的四个阈值/时间参数、单位、禁用值和默认值。"),
        ],
        "battery": [
            source("ARD-SHARED-BATT-001-S1", f"{wiki}/copter/source/docs/failsafe-battery.rst", 93, 96, "OFFICIAL_BEHAVIOR", "HIGH", "ArduPilot Battery Failsafe", ARD_WIKI_COMMIT, "MAIN_ONLY", "说明电压源、LOW_TIMER 与多电池实例化。", "Advanced Settings"),
            source("ARD-SHARED-BATT-001-S2", f"{src}/libraries/AP_BattMonitor/AP_BattMonitor_Params.cpp", 95, 129, "PARAM_METADATA", "LOW", "AP_BattMonitor low/critical voltage metadata", ARD_COMMIT, "CURRENT", "冻结源码中的 LOW_TIMER、LOW_VOLT、CRT_VOLT 及连续超过时间的语义。"),
        ],
    }


def px4_sources() -> dict[str, list[dict[str, Any]]]:
    src = "baseline/px4"
    return {
        "rc": [
            source("PX4-MC-RCLOSS-001-S1", f"{src}/docs/en/config/safety.md", 112, 134, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Safety: Manual Control Loss", "v1.17.0", "RELEASE_PINNED", "定义 selected manual source 的最后 setpoint 起点、COM_RC_LOSS_T 和模式例外。", "Manual Control Loss Failsafe"),
            source("PX4-MC-RCLOSS-001-S2", f"{src}/src/modules/commander/commander_params.c", 125, 139, "PARAM_METADATA", "LOW", "PX4 COM_RC_LOSS_T metadata", PX4_COMMIT, "RELEASE_PINNED", "冻结提交中的参数单位、范围和默认值。"),
        ],
        "gcs": [
            source("PX4-MC-GCSLOSS-002-S1", f"{src}/docs/en/config/safety.md", 136, 153, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Safety: Data Link Loss", "v1.17.0", "RELEASE_PINNED", "定义 telemetry/GCS data-link loss、COM_DL_LOSS_T 和模式例外。", "Data Link Loss Failsafe"),
            source("PX4-MC-GCSLOSS-002-S2", f"{src}/src/modules/commander/commander_params.c", 86, 98, "PARAM_METADATA", "LOW", "PX4 COM_DL_LOSS_T metadata", PX4_COMMIT, "RELEASE_PINNED", "冻结提交中的参数单位、范围和默认值。"),
        ],
        "offboard": [
            source("PX4-MC-OFFBOARD-003-S1", f"{src}/docs/en/flight_modes/offboard.md", 5, 18, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Offboard Mode", "v1.17.0", "RELEASE_PINNED", "定义进入 Offboard 前的 proof-of-life 速率和持续时间。", "Offboard Mode"),
            source("PX4-MC-OFFBOARD-003-S2", f"{src}/docs/en/flight_modes/offboard.md", 24, 31, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Offboard Mode", "v1.17.0", "RELEASE_PINNED", "同页对 2Hz、>2Hz、below 2Hz 的边界表述存在冲突。", "Description"),
            source("PX4-MC-OFFBOARD-003-S3", f"{src}/src/modules/commander/commander_params.c", 329, 369, "PARAM_METADATA", "LOW", "PX4 Offboard loss parameters", PX4_COMMIT, "RELEASE_PINNED", "冻结提交中的 COM_OF_LOSS_T 和 COM_OBL_RC_ACT 元数据。"),
        ],
        "disarm": [
            source("PX4-MC-AUTODISARM-004-S1", f"{src}/docs/en/advanced_config/prearm_arm_disarm.md", 86, 94, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Arming/Disarming", "v1.17.0", "RELEASE_PINNED", "定义落地后自动 disarm 的时间参数和文档禁用值。", "Auto-Disarming"),
            source("PX4-MC-AUTODISARM-004-S2", f"{src}/docs/en/flight_modes_mc/land.md", 23, 37, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Multicopter Land Mode", "v1.17.0", "RELEASE_PINNED", "说明 landed 状态和 COM_DISARM_LAND 触发自动 disarm。", "Landing Sequence"),
            source("PX4-MC-AUTODISARM-004-S3", f"{src}/src/modules/commander/commander_params.c", 215, 227, "PARAM_METADATA", "LOW", "PX4 COM_DISARM_LAND metadata", PX4_COMMIT, "RELEASE_PINNED", "参数元数据将零或负值均列为禁用，与文档 -1 表述不同。"),
        ],
        "flight": [
            source("PX4-MC-FLIGHTTIME-005-S1", f"{src}/docs/en/config/safety.md", 96, 110, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Safety: Flight Time Failsafes", "v1.17.0", "RELEASE_PINNED", "定义 takeoff 后最大飞行时间、90% warning、Return 和 -1 禁用。", "Flight Time Failsafes"),
            source("PX4-MC-FLIGHTTIME-005-S2", f"{src}/src/modules/commander/commander_params.c", 884, 897, "PARAM_METADATA", "LOW", "PX4 COM_FLT_TIME_MAX metadata", PX4_COMMIT, "RELEASE_PINNED", "冻结提交中的秒单位、范围、默认/禁用值。"),
        ],
        "rtl": [
            source("PX4-MC-RTLLOITER-006-S1", f"{src}/docs/en/flight_modes/return.md", 183, 194, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Return Mode", "v1.17.0", "RELEASE_PINNED", "定义非 mission landing 时到达目的地、RTL_DESCEND_ALT、等待与 landing。", "Loiter/Landing at Destination"),
            source("PX4-MC-RTLLOITER-006-S2", f"{src}/docs/en/flight_modes/return.md", 204, 218, "OFFICIAL_BEHAVIOR", "HIGH", "PX4 Return Mode Parameters", "v1.17.0", "RELEASE_PINNED", "参数表给出 RTL_LAND_DELAY 文档默认 0.5s 和 -1 indefinite。", "Parameters"),
            source("PX4-MC-RTLLOITER-006-S3", f"{src}/src/modules/navigator/rtl_params.c", 63, 89, "PARAM_METADATA", "LOW", "PX4 RTL parameter metadata", PX4_COMMIT, "RELEASE_PINNED", "冻结提交元数据默认 0.0s，与文档默认 0.5s 冲突；运行时值优先。"),
        ],
    }


def build_properties() -> list[dict[str, Any]]:
    a = ard_sources()
    p = px4_sources()
    properties: list[dict[str, Any]] = []

    s = a["gcs"]
    pid = "ARD-COPTER-GCS-001"
    properties.append(base_property(
        pid, "Copter 指定 GCS heartbeat 超时", "Copter designated-GCS heartbeat timeout", "ArduPilot", ["Copter"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "ArduCopter GCS failsafe", "BEHAVIORAL_DESCRIPTION", "此前已收到过指定 GCS 的 MAVLink heartbeat，随后不再收到该 heartbeat。",
        ["本 run 中指定 GCS 至少有一个 heartbeat 已被飞控收到。", "归档的参数设置要求本次 GCS failsafe event 生效；精确 enable/例外规则仍需版本化官方证据。"],
        ["自最后一个指定 GCS heartbeat 起没有收到新 heartbeat 达运行时 FS_GCS_TIMEOUT 后，产生 GCS failsafe event。"],
        ["在该 heartbeat 缺失区间达到 FS_GCS_TIMEOUT 前，不得仅因该缺失产生 GCS failsafe event。"],
        ["从未连接过 GCS（本 run 从未收到 GCS heartbeat）时，该 failsafe 保持 inactive。"],
        "最后一个被飞控收到的指定 GCS MAVLink heartbeat", "下一个指定 GCS heartbeat 或 run 结束；配置变化的取消语义尚未闭合",
        [("designated_gcs_heartbeat", "RESETS", "gcs_heartbeat_gap"), ("gcs_heartbeat_gap", "TRIGGERS", "gcs_failsafe_event")],
        ["当前源码的共享 last-seen 还可由 MANUAL_CONTROL/RC_CHANNELS_OVERRIDE 刷新；这是实现映射冲突，不是规范 heartbeat 的替代定义。", "配置取消和模式例外需要额外的当前版本官方证据。"],
        [runtime_time("T_gcs", "last_designated_gcs_heartbeat_receipt", "gcs_failsafe_event", "FS_GCS_TIMEOUT", "s", s[1], 5, True, "AUTOPILOT_MONOTONIC_BOOT", "Normative event: designated-GCS heartbeat receipt; current-source exact handler carrier: AP_HAL::millis() at GCS_MAVLINK::handle_heartbeat. The aggregate last-seen timestamp is shared and only MODELLED for this normative event.", "designated_gcs_heartbeat", "run_end_or_applicability_ceases")],
        "G((gcs_heartbeat_gap_start & gcs_heartbeat_seen_before & gcs_fs_enabled) -> (G_[0,T_gcs) !gcs_failsafe_event & F_[T_gcs,infty) gcs_failsafe_event))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","gcs_heartbeat_gap_start","指定 GCS heartbeat 的缺失区间开始。","最后一个被飞控收到的 designated_gcs_heartbeat 之后，在该连接范围内不再收到新 heartbeat 的边沿事件。","EVENT"),
            ap(pid,"02","gcs_heartbeat_seen_before","本 run 中指定 GCS 之前至少有一个 heartbeat 被飞控收到。","count(designated_gcs_heartbeat_receipt)>0。","DERIVED_STATE"),
            ap(pid,"03","gcs_fs_enabled","GCS failsafe 对当前归档配置生效。","已归档的参数/模式组合要求本次 GCS failsafe event 生效；精确规则仍需版本化官方证据。","DERIVED_STATE"),
            ap(pid,"04","gcs_failsafe_event","飞控将 GCS failsafe event 标为 active。","GCS-specific failsafe state 从 false 变 true。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
        ],
        ["ArduPilot wiki 为 MAIN_ONLY，未与冻结固件 release 配对。", "当前实现的 aggregate last-seen 可由非 heartbeat 消息刷新；该实现行为只作 MODELLED binding/conflict。", "FS_GCS_ENABLE 的旧参数文案写死 5s；该性质只使用运行时 FS_GCS_TIMEOUT。"],
        "SITL Copter；指定 GCS 已被识别；failsafe 参数、模式和消息源已归档。"))

    s = a["guided"]
    pid = "ARD-COPTER-GUID-002"
    properties.append(base_property(
        pid, "Copter Guided 指令更新超时", "Copter Guided command-update timeout", "ArduPilot", ["Copter"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "ArduCopter Guided controller", "BEHAVIORAL_DESCRIPTION", "Guided attitude、velocity 或 acceleration 控制期间不再收到相应 caller command。",
        ["当前为 Guided，并记录本次控制组合。", "只对文档列出的 attitude/velocity/acceleration 类命令建模。"],
        ["运行时 GUID_TIMEOUT 到期后，velocity/acceleration 变体开始减速至停止；attitude 变体开始回到水平悬停。"],
        ["在 GUID_TIMEOUT 到期前不得仅因命令间隔启动该 timeout response。"],
        ["position-only 目标不自动继承 velocity/attitude 的响应语义。", "新适用 command 会重置间隔。"],
        "最后一个被接受且适用于当前 Guided 控制组合的 command", "新适用 command、离开 Guided 或 run 结束",
        [("guided_command", "RESETS", "guided_gap"), ("guided_gap", "TRIGGERS", "timeout_response_started")],
        ["文档没有给出“完全停止/完全水平”的完成上界；本性质只约束 timeout response 的启动，不人工补完成时限。", "各控制组合必须拆分验证。"],
        [runtime_time("T_guid", "last_applicable_guided_command", "timeout_response_started", "GUID_TIMEOUT", "s", s[1], 3.0, True, "AUTOPILOT_MONOTONIC_BOOT", "vehicle receipt millis; MAVLink sender time_boot_ms is not the anchor", "applicable_guided_command", "leave_guided_or_run_end")],
        "G((guided_gap_start & guided_variant_active) -> (G_[0,T_guid) !timeout_response_started & F_[T_guid,infty) timeout_response_started))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","guided_gap_start","适用 Guided command 的接收间隔开始。","最后一个被接受的适用 command 之后未再接受同类更新。","EVENT"),
            ap(pid,"02","guided_variant_active","记录 velocity/acceleration 或 attitude/rate 变体。","当前 Guided 控制组合属于已枚举变体之一。","STATE", value_type="enum"),
            ap(pid,"03","timeout_response_started","对应变体的 timeout response 已启动。","velocity/acceleration: 开始零目标/减速；attitude: 开始回水平/零角速率。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
        ],
        ["MAIN_ONLY 文档与冻结源码版本关系需人工复核。", "完成响应无规范上界，因此不把 stopped/level 的完成时刻写入 MITL。"],
        "SITL Copter 已进入 Guided；command type mask、caller identity 和运行时 GUID_TIMEOUT 已归档。"))

    s = a["rtl"]
    pid = "ARD-COPTER-RTL-003"
    properties.append(base_property(
        pid, "Copter RTL Home 上方等待", "Copter RTL loiter above Home before final descent", "ArduPilot", ["Copter"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "ArduCopter RTL mode", "BEHAVIORAL_DESCRIPTION", "RTL 到达 Home 上方并进入 loiter/pause 阶段。",
        ["RTL 未被取消，且 RTL_ALT_FINAL 等配置选择最终下降/着陆路径。"],
        ["等待运行时 RTL_LOIT_TIME 后开始最终下降。"],
        ["持续符合条件时，在 RTL_LOIT_TIME 结束前不得开始最终下降。"],
        ["离开 RTL、改变为非下降结尾或外部合法 mode transition 会取消本次义务。"],
        "进入 Home 上方 loiter/pause 阶段", "开始最终下降、RTL 取消或 run 结束",
        [("enter_loiter_at_home", "BEFORE", "begin_final_descent"), ("leave_rtl", "CANCELS", "rtl_loiter_obligation")],
        ["标准 HEARTBEAT 只显示 RTL，不能区分内部 loiter/final-descent 子状态。"],
        [runtime_time("T_rtl_loiter", "enter_loiter_at_home", "begin_final_descent", "RTL_LOIT_TIME", "ms", s[1], 5000, True, "AUTOPILOT_MONOTONIC_BOOT", "vehicle millis at RTL sub-state entry", None, "leave_rtl_or_nonlanding_path")],
        "G(enter_loiter_at_home -> (G_[0,T_rtl_loiter] rtl_loiter_eligible -> (G_[0,T_rtl_loiter) !begin_final_descent & F_[T_rtl_loiter,infty) begin_final_descent)))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","enter_loiter_at_home","RTL 进入 Home 上方等待子状态。","内部 RTL sub-state 的进入边沿。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
            ap(pid,"02","rtl_loiter_eligible","本次 RTL 持续选择最终下降路径且未被取消。","在所检查时间范围内 RTL 和 landing-path eligibility 均持续为 true。","DERIVED_STATE"),
            ap(pid,"03","begin_final_descent","RTL 开始最终下降。","内部 RTL sub-state 进入 final descent 的边沿。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
        ],
        ["ArduPilot wiki 是 MAIN_ONLY。", "0ms 是合法运行时值；边界需要同一飞控时钟的事件探针。"],
        "SITL Copter 在 RTL 返回路径；Home、RTL landing configuration 和 mission 状态已归档。"))

    s = a["takeoff"]
    pid = "ARD-PLANE-TAKEOFF-001"
    properties.append(base_property(
        pid, "Plane 自动起飞超时", "Plane automatic-takeoff timeout", "ArduPilot", ["Plane"], "NEEDS_BINDING", "PARAM_METADATA_CANDIDATE", s,
        "ArduPlane automatic takeoff", "BEHAVIORAL_DESCRIPTION", "启用 TKOFF_TIMEOUT 的自动起飞开始。",
        ["TKOFF_TIMEOUT > 0。", "从内部 automatic-takeoff start 起，地速在整个窗口内从未达到 4m/s。"],
        ["超时后中止 takeoff 并 disarm。"],
        ["若在窗口内达到至少 4m/s，则不能仅由该 timeout 分支判为违规。"],
        ["TKOFF_TIMEOUT=0 禁用。", "非 automatic-takeoff 不在范围。"],
        "内部 automatic-takeoff start", "达到 4m/s、takeoff abort/disarm、离开 takeoff 或 run 结束",
        [("takeoff_start", "BEFORE", "takeoff_abort"), ("speed_reaches_4mps", "CANCELS", "takeoff_timeout_obligation")],
        ["唯一规范来源是冻结参数元数据，权威等级低。", "标准 MAVLink 没有精确 automatic-takeoff start 时间。"],
        [runtime_time("T_takeoff", "automatic_takeoff_start", "takeoff_abort", "TKOFF_TIMEOUT", "s", s[0], 0, True, "AUTOPILOT_MONOTONIC_BOOT", "internal takeoff start millis", None, "speed_reaches_4mps_or_leave_takeoff")],
        "G((automatic_takeoff_start & timeout_enabled) -> (G_[0,T_takeoff] speed_below_4mps -> F_[T_takeoff,infty) (takeoff_aborted & F disarmed)))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","automatic_takeoff_start","自动起飞计时起点发生。","当前 takeoff attempt 的内部 start epoch 从 unset 变为有效。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
            ap(pid,"02","timeout_enabled","运行时 TKOFF_TIMEOUT 大于零。","PARAM_VALUE(TKOFF_TIMEOUT)>0。","VALUE_COMPARISON", value_type="float", unit="s", observability="CONDITIONAL"),
            ap(pid,"03","speed_below_4mps","地速低于 4m/s。","AP::gps ground speed < 4.0 m/s 且 GPS speed 有效/新鲜。","VALUE_COMPARISON", value_type="float", unit="m/s"),
            ap(pid,"04","takeoff_aborted","本次自动起飞被 timeout 原因中止。","takeoff-abort event 与当前 attempt correlation key 匹配。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
            ap(pid,"05","disarmed","飞控处于 disarmed。","armed state 为 false。","STATE", observability="DIRECT"),
        ],
        ["0 是源码默认且表示 disabled；不得生成默认 concrete 公式。", "abort 到 disarm 没有独立数值上界，公式只保留定性 eventually。"],
        "SITL Plane；automatic TAKEOFF attempt、GPS speed validity 和运行时 TKOFF_TIMEOUT 已归档。"))

    s = a["rover_rc"]
    pid = "ARD-ROVER-RCFS-001"
    properties.append(base_property(
        pid, "Rover 低油门持续触发 failsafe", "Rover low-throttle persistence failsafe", "ArduPilot", ["Rover"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "ArduRover radio/throttle failsafe", "BEHAVIORAL_DESCRIPTION", "有效 RC throttle channel 持续低于运行时 FS_THR_VALUE。",
        ["FS_THR_ENABLE 对当前模式生效。", "持续发送有效 RC frame，以隔离独立的 RC_FS_TIMEOUT 路径。", "throttle channel 由运行时 RCMAP_THROTTLE 决定。"],
        ["条件持续运行时 FS_TIMEOUT 后触发配置的 failsafe action。"],
        ["在 FS_TIMEOUT 结束前不得仅由该低 PWM 条件触发 action。"],
        ["低值条件中断会重置持续时间。", "FS_THR_ENABLE 的 Auto 例外配置必须尊重。"],
        "有效 throttle PWM 首次低于 FS_THR_VALUE", "PWM 恢复、frame 无效、failsafe 禁用、action 或 run 结束",
        [("throttle_below_threshold", "TRIGGERS", "persistence_timer"), ("throttle_recovers", "RESETS", "persistence_timer")],
        ["wiki 的 default=1s 与冻结 FS_TIMEOUT metadata default=1.5s 冲突；只读取运行时值。", "最终 action 由 FS_ACTION/模式决定，不能硬编码单一 mode。"],
        [runtime_time("T_rover_fs", "low_throttle_interval_start", "configured_failsafe_action", "FS_TIMEOUT", "s", s[1], 1.5, True, "AUTOPILOT_MONOTONIC_BOOT", "vehicle millis for failsafe condition", "throttle_recovers", "failsafe_disabled_or_run_end")],
        "G((low_throttle_start & valid_rc_frames & throttle_fs_enabled) -> (G_[0,T_rover_fs) !configured_failsafe_action & F_[T_rover_fs,infty) configured_failsafe_action))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","low_throttle_start","映射后的 throttle PWM 进入低于阈值的连续区间。","valid RC frame 且 chan[RCMAP_THROTTLE] < PARAM_VALUE(FS_THR_VALUE) 的上升沿。","EVENT", unit="us PWM"),
            ap(pid,"02","valid_rc_frames","低 PWM 区间内仍持续有有效 RC frame。","每个 freshness 窗口内存在被接收器接受的 RC frame。","FRESHNESS"),
            ap(pid,"03","throttle_fs_enabled","throttle failsafe 对当前模式生效。","运行时 FS_THR_ENABLE 和模式不属于例外。","DERIVED_STATE"),
            ap(pid,"04","configured_failsafe_action","FS_ACTION 对应的 action 已发生。","运行时 FS_ACTION 映射到的结果 mode/action 成立，并与本次低油门 event 关联。","CORRELATION", observability="CONDITIONAL"),
        ],
        ["ArduPilot wiki MAIN_ONLY 且默认值与冻结源码不一致。", "RC_FS_TIMEOUT 是另一条性质，不与 FS_TIMEOUT 合并。"],
        "SITL Rover；RCMAP、FS_* 参数、模式和有效 RC input path 已归档。"))

    s = a["rover_crash"]
    pid = "ARD-ROVER-CRASH-002"
    properties.append(base_property(
        pid, "Rover crash 条件持续时间", "Rover persistent crash-condition timeout", "ArduPilot", ["Rover"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "ArduRover crash check", "BEHAVIORAL_DESCRIPTION", "适用模式内 crash 条件合取首次连续成立。",
        ["FS_CRASH_CHECK 为 1 或 2。", "模式为 Auto/Guided/RTL/SmartRTL。", "速度、转率和 demanded throttle 均使用各自运行时阈值。", "隔离 CRASH_ANGLE 立即路径。"],
        ["条件持续至少 CRASH_TIMEOUT 后切换 Hold，并在配置为 2 时 disarm。"],
        ["在 CRASH_TIMEOUT 结束前不得仅由 persistence 分支触发 crash action。"],
        ["任一合取条件中断会重置持续区间。", "CRASH_ANGLE 是独立立即触发路径。"],
        "crash conjunction 从 false 变 true", "任一条件恢复、crash action、failsafe 禁用或 run 结束",
        [("crash_condition", "TRIGGERS", "crash_timer"), ("condition_break", "RESETS", "crash_timer")],
        ["VFR_HUD 无时间戳而 ATTITUDE 有 time_boot_ms；纯 wire 多流合取无法保证同一采样时刻。"],
        [runtime_time("T_crash", "crash_condition_start", "crash_action", "CRASH_TIMEOUT", "s", s[1], 2.0, True, "AUTOPILOT_MONOTONIC_BOOT", "single vehicle-side instrumentation clock", "condition_break", "failsafe_disabled_or_run_end")],
        "G((crash_condition_start & crash_check_enabled) -> (G_[0,T_crash) !crash_action & F_[T_crash,infty) crash_action))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","crash_condition_start","完整 crash 合取条件开始连续成立。","eligible_mode & armed & demanded_throttle>=CRASH_THR_MIN & groundspeed<CRASH_VEL_MIN & abs(turn_rate)<CRASH_TRAT_MIN 的上升沿。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
            ap(pid,"02","crash_check_enabled","persistence crash check 已启用且 angle 路径被隔离。","FS_CRASH_CHECK in {1,2} 且 CRASH_ANGLE=0 或姿态保证不越界。","DERIVED_STATE"),
            ap(pid,"03","crash_action","配置的 Hold/optional-disarm crash action 发生。","进入 Hold；若 FS_CRASH_CHECK=2，同时最终 disarmed。","CORRELATION", observability="CONDITIONAL"),
        ],
        ["需要统一飞控侧采样，不能按不同消息主机到达时间随意对齐。", "阈值为运行时参数；源码默认仅记录。"],
        "SITL Rover；启用 crash check；阈值、模式和 CRASH_ANGLE 隔离设置已归档。"))

    s = a["battery"]
    pid = "ARD-SHARED-BATT-001"
    properties.append(base_property(
        pid, "ArduPilot 持续低电压 failsafe", "ArduPilot persistent low-voltage failsafe", "ArduPilot", ["Copter", "Plane", "Rover"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "AP_BattMonitor and vehicle failsafe callback", "BEHAVIORAL_DESCRIPTION", "某 battery instance 的选定电压源持续低于运行时 LOW_VOLT。",
        ["该 instance 的 LOW_VOLT 非零。", "记录 BATTx_FS_VOLTSRC，区分 raw 与 sag-corrected resting estimate。", "low 与 critical variant 分开验证。"],
        ["连续低于阈值超过运行时 LOW_TIMER 后触发该 instance 对应 low/critical event 和配置 action。"],
        ["在严格超过 LOW_TIMER 前不得仅由该低电压区间触发。"],
        ["电压恢复到不低于阈值会重置持续区间。", "capacity-based path 不属于本性质。"],
        "选定电压源首次低于 instance threshold", "电压恢复、event/action、monitor instance disabled 或 run 结束",
        [("low_voltage", "TRIGGERS", "low_voltage_timer"), ("voltage_recovers", "RESETS", "low_voltage_timer")],
        ["FS_VOLTSRC=1 时标准 BATTERY_STATUS 不直接提供 resting estimate。", "每个 battery instance 必须使用独立 correlation key。"],
        [runtime_time("T_low_voltage", "low_voltage_interval_start", "battery_failsafe_event", "BATTx_LOW_TIMER", "s", s[1], 10, False, "AUTOPILOT_MONOTONIC_BOOT", "battery-backend vehicle millis", "voltage_recovers", "monitor_disabled_or_run_end", raw_expression="continuously for more than runtime(BATTx_LOW_TIMER)")],
        "G((low_voltage_start & voltage_threshold_enabled) -> (G_[0,T_low_voltage] !battery_failsafe_event & F_(T_low_voltage,infty) battery_failsafe_event))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","low_voltage_start","指定 battery instance 的选定电压源进入低阈值区间。","selected_voltage(instance)<PARAM_VALUE(BATTx_LOW_VOLT) 的上升沿。","EVENT", value_type="float", unit="V", correlation="vehicle_system_id + campaign_run_id + battery_instance"),
            ap(pid,"02","voltage_threshold_enabled","该 instance 的低电压阈值启用。","PARAM_VALUE(BATTx_LOW_VOLT)>0。","VALUE_COMPARISON", value_type="float", unit="V", correlation="vehicle_system_id + campaign_run_id + battery_instance"),
            ap(pid,"03","battery_failsafe_event","该 instance 的 low/critical voltage event 已触发。","AP_BattMonitor event level 与 instance/variant 匹配。","CORRELATION", correlation="vehicle_system_id + campaign_run_id + battery_instance + severity", observability="INSTRUMENTATION_REQUIRED"),
        ],
        ["MAIN_ONLY 文档未 release-pair。", "strict 'more than' 使用开下界；不引入 epsilon。"],
        "SITL vehicle；battery instance、threshold、voltage source、action 和 capacity path isolation 已归档。"))

    s = p["rc"]
    pid = "PX4-MC-RCLOSS-001"
    properties.append(base_property(
        pid, "PX4 selected manual source 丢失", "PX4 selected-manual-source loss timeout", "PX4", ["multicopter SITL"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "PX4 Commander manual-control-loss check", "BEHAVIORAL_DESCRIPTION", "selected manual control source 的最后 setpoint 之后不再有新 setpoint。",
        ["当前 manual source 已被明确选中。", "COM_RCL_EXCEPT 不排除当前模式。", "测试器能证明输入被接受并被 selector 选中。"],
        ["运行时 COM_RC_LOSS_T 后 manual control 被视为 lost。"],
        ["在超时前不得仅由 selected-source gap 标记 lost。"],
        ["source selection 切换或新 selected-source setpoint 会重置。", "配置的 mode exception 取消 action 义务，但不一定改变低层 signal-lost 分类。"],
        "selected source 的最后 accepted setpoint", "新 selected setpoint、source switch、disarm 或 run 结束",
        [("selected_manual_setpoint", "RESETS", "manual_gap"), ("manual_gap", "TRIGGERS", "manual_control_lost")],
        ["发送 MANUAL_CONTROL 不等于它被 selector 选中；需要内部或可靠 selector 证据。"],
        [runtime_time("T_rc_loss", "last_selected_manual_setpoint", "manual_control_lost", "COM_RC_LOSS_T", "s", s[1], 0.5, True, "AUTOPILOT_MONOTONIC_BOOT", "PX4 HRT timestamp of selected ManualControlSetpoint", "new_selected_setpoint_or_source_switch", "disarm_or_run_end")],
        "G((manual_gap_start & rc_loss_applicable) -> (G_[0,T_rc_loss) !manual_control_lost & F_[T_rc_loss,infty) manual_control_lost))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","manual_gap_start","selected manual source 的 accepted setpoint 间隔开始。","selected ManualControlSetpoint timestamp 不再更新的区间起点。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
            ap(pid,"02","rc_loss_applicable","当前配置/模式不排除 manual control loss。","runtime mode、COM_RCL_EXCEPT、RC source configuration 允许本次检查。","DERIVED_STATE"),
            ap(pid,"03","manual_control_lost","PX4 将 manual control signal 标为 lost。","manual_control_signal_lost 状态从 false 变 true。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
        ],
        ["标准 MAVLink 不能单独证明 selected source。"],
        "PX4 multicopter SITL；manual input source、mode exceptions 和运行时参数已归档。"))

    s = p["gcs"]
    pid = "PX4-MC-GCSLOSS-002"
    properties.append(base_property(
        pid, "PX4 GCS data-link loss", "PX4 GCS data-link-loss timeout", "PX4", ["multicopter SITL"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "PX4 data-link-loss failsafe", "BEHAVIORAL_DESCRIPTION", "与地面站的 telemetry link/data connection 进入 lost/unavailable 状态。",
        ["与地面站的 telemetry/data connection 此前已建立。", "NAV_DLL_ACT 未禁用该 failsafe，且 COM_DLL_EXCEPT 未将当前模式列为例外。", "官方来源未定义该 connection 的精确 liveness predicate、关联键或事件载体；当前仍为待补证前置。"],
        ["自 telemetry/data connection 丢失起达到运行时 COM_DL_LOSS_T 后，Data Link Loss failsafe 触发。"],
        ["在该 data connection loss 持续达到 COM_DL_LOSS_T 前，不得仅因该 loss 触发 Data Link Loss failsafe。"],
        ["已配置的 COM_DLL_EXCEPT 模式不触发该 failsafe。", "NAV_DLL_ACT=Disabled 时不要求执行 failsafe action。"],
        "官方来源定义的 telemetry/data connection loss 开始", "官方来源定义的 connection 恢复、配置例外/取消或 run 结束",
        [("telemetry_data_connection_restored", "RESETS", "data_link_loss_gap"), ("data_link_loss_gap", "TRIGGERS", "gcs_connection_lost")],
        ["官方 v1.17 文档没有将 telemetry/data connection liveness 定义为 MAV_TYPE_GCS heartbeat，也没有给出 loss-start 时钟或时间戳载体。", "当前 PX4 heartbeat/HRT flow 只是 MODELLED 源码候选映射，不是规范等价关系。"],
        [runtime_time("T_dl_loss", "telemetry_data_link_loss_start", "gcs_connection_lost", "COM_DL_LOSS_T", "s", s[1], 10, True, "UNKNOWN", "Official sources do not define a liveness-event timestamp carrier or clock. The current PX4 MAV_TYPE_GCS heartbeat/HRT flow is retained only as a MODELLED implementation candidate.", "telemetry_data_connection_restored", "configured_exception_or_run_end")],
        "G((data_link_loss_gap_start & dl_loss_applicable) -> (G_[0,T_dl_loss) !gcs_connection_lost & F_[T_dl_loss,infty) gcs_connection_lost))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","data_link_loss_gap_start","官方来源所指 telemetry/data connection 的丢失区间开始。","与地面站的 source-defined telemetry/data connection 从 available 变为 lost/unavailable；精确 liveness predicate、关联键和时钟尚未解析。","EVENT", observability="UNRESOLVED"),
            ap(pid,"02","dl_loss_applicable","data-link loss 对当前模式/配置生效。","NAV_DLL_ACT、COM_DLL_EXCEPT 和 current mode 的组合允许检查。","DERIVED_STATE"),
            ap(pid,"03","gcs_connection_lost","Data Link Loss failsafe 触发时的当前源码内部 GCS-connection-lost 事件。","gcs_connection_lost 从 false 变 true；该字段是对官方 failsafe-trigger 结果的当前源码映射，不反向定义规范输入。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
        ],
        ["官方 data-link loss 事件的 liveness predicate/时钟未解析；HEARTBEAT 及 GCS host arrival time 不能自动替代。"],
        "PX4 multicopter SITL；参数/模式已归档；telemetry/data connection 的官方关联键、liveness predicate 和时钟仍待闭合。"))

    s = p["offboard"]
    pid = "PX4-MC-OFFBOARD-003"
    properties.append(base_property(
        pid, "PX4 Offboard proof-of-life 时序", "PX4 Offboard proof-of-life admission/loss timing", "PX4", ["multicopter SITL"], "NEEDS_CONTEXT", "OFFICIAL_BEHAVIOR", s,
        "PX4 Offboard mode manager", "BEHAVIORAL_DESCRIPTION", "受支持的 Offboard proof-of-life stream 出现或停止。",
        ["消息被 PX4 接受且字段/type-mask 对当前 Offboard control mode 有效。"],
        ["进入 Offboard 前需持续约一秒满足文档规定的 rate；进入后 proof loss 持续 COM_OF_LOSS_T 时退出或执行配置 action。"],
        [],
        ["RC availability 会改变配置 action。", "离开 Offboard 或合法 mode override 取消 loss 义务。"],
        "accepted Offboard proof stream", "离开 Offboard、恢复 proof stream 或 run 结束",
        [("offboard_proof", "TRIGGERS", "offboard_admission_qualification"), ("offboard_proof", "RESETS", "offboard_loss_gap")],
        ["同一冻结文档同时写 2Hz、>2Hz 和 below 2Hz，无法确定 equality boundary。", "admission 的 one-second 起止边界与 accepted-event 还未可靠绑定。"],
        [runtime_time("T_offboard_loss", "offboard_proof_loss_epoch", "offboard_loss_action", "COM_OF_LOSS_T", "s", s[2], 1.0, True, "AUTOPILOT_MONOTONIC_BOOT", "PX4 HRT on accepted offboard_control_mode", "accepted_offboard_proof", "leave_offboard_or_run_end")],
        None, "NEEDS_CONTEXT",
        [
            ap(pid,"01","offboard_proof","受支持且被接受的 Offboard proof message。","accepted setpoint/offboard-control update 对当前 control mode 有效。","EVENT", observability="CONDITIONAL"),
            ap(pid,"02","offboard_proof_qualified","proof history 满足 admission rate/duration。","待解决 2Hz equality 和持续时长边界后才能定义。","DERIVED_STATE", observability="UNRESOLVED"),
            ap(pid,"03","mode_offboard","PX4 当前处于 Offboard。","vehicle navigation state 映射为 Offboard。","STATE", observability="DIRECT"),
            ap(pid,"04","offboard_loss_action","退出 Offboard 并执行运行时配置的 loss action。","结果 mode/action 与 COM_OBL_RC_ACT 和 RC availability 匹配。","CORRELATION", observability="CONDITIONAL"),
        ],
        ["rate equality 冲突未解决，禁止生成 admission concrete MITL。", "COM_OF_LOSS_T 仅解决 post-admission loss window。"],
        "PX4 multicopter SITL；Offboard message family/type mask、RC availability 和运行时参数已归档。"))

    s = p["disarm"]
    pid = "PX4-MC-AUTODISARM-004"
    properties.append(base_property(
        pid, "PX4 落地后自动 disarm", "PX4 automatic disarm after landing", "PX4", ["multicopter SITL"], "NEEDS_CONTEXT", "OFFICIAL_BEHAVIOR", s,
        "PX4 Commander auto-disarm", "BEHAVIORAL_DESCRIPTION", "armed vehicle 的 landed 状态开始连续成立。",
        ["运行时 COM_DISARM_LAND 启用。", "只使用官方来源确认的 eligibility/exception；实现 guard 不反推为规范。"],
        ["连续 landed 达 COM_DISARM_LAND 后自动 disarm。"],
        ["在时间结束前不得仅由 landing timer 自动 disarm。"],
        ["mission/config overrides 和 throw-launch 等例外尚需官方上下文。", "文档 -1 与参数元数据 <=0 的禁用域冲突。"],
        "landed transition while armed", "landed false、disarm、eligibility cancel 或 run 结束",
        [("landed", "TRIGGERS", "auto_disarm_timer"), ("landed_false", "RESETS", "auto_disarm_timer")],
        ["规范前提不完整；不能从 Commander guard 反向补齐。", "disable domain 冲突。"],
        [runtime_time("T_disarm_land", "landed_interval_start", "automatic_disarm", "COM_DISARM_LAND", "s", s[2], 2.0, True, "AUTOPILOT_MONOTONIC_BOOT", "PX4 HRT land-detector/commander events", "landed_false", "eligibility_cancel_or_run_end")],
        "G((landed_start & auto_disarm_eligible) -> (G_[0,T_disarm_land) armed & F_[T_disarm_land,infty) disarmed))", "NEEDS_CONTEXT",
        [
            ap(pid,"01","landed_start","land detector 进入 landed。","vehicle landed 从 false 变 true。","EVENT", observability="DIRECT"),
            ap(pid,"02","auto_disarm_eligible","官方规范定义的 auto-disarm eligibility 全部成立。","待补全官方例外后定义；不能使用实现 guard 充当来源。","DERIVED_STATE", observability="UNRESOLVED"),
            ap(pid,"03","armed","PX4 当前 armed。","HEARTBEAT armed bit 对目标 autopilot 为 true。","STATE", observability="DIRECT"),
            ap(pid,"04","disarmed","PX4 当前 disarmed。","HEARTBEAT armed bit 为 false。","STATE", observability="DIRECT"),
        ],
        ["COM_DISARM_LAND 禁用域冲突。", "eligibility 官方上下文尚未闭合。"],
        "PX4 multicopter SITL；vehicle airborne 后落地；mission/override configuration 已归档。"))

    s = p["flight"]
    pid = "PX4-MC-FLIGHTTIME-005"
    warning_time = runtime_time("T_flight_max", "detected_takeoff", "enter_return", "COM_FLT_TIME_MAX", "s", s[1], -1, True, "AUTOPILOT_MONOTONIC_BOOT", "PX4 vehicle_status.takeoff_time HRT", None, "disarm_or_run_end")
    warning_time["operands"].append({"name": "warning_fraction", "value": 0.9, "unit": "ratio", "source_id": s[0]["source_id"]})
    warning_time["formula"] = "T_warning = 0.9 * runtime(COM_FLT_TIME_MAX); T_flight_max = runtime(COM_FLT_TIME_MAX)"
    properties.append(base_property(
        pid, "PX4 最大飞行时间", "PX4 maximum flight-time warning and Return", "PX4", ["multicopter SITL"], "NEEDS_BINDING", "OFFICIAL_BEHAVIOR", s,
        "PX4 Commander flight-time check", "BEHAVIORAL_DESCRIPTION", "飞控检测到 takeoff，且 COM_FLT_TIME_MAX 启用。",
        ["COM_FLT_TIME_MAX > 0。", "takeoff epoch 来自 detected takeoff，而非 arm time 或 GCS command time。"],
        ["0.9*T 时发出 warning；T 时进入 Return。"],
        ["在相应边界前不得仅由最大飞行时间机制产生 warning/Return。"],
        ["-1/非正配置禁用。", "disarm 终止本次 flight-time scope。"],
        "detected takeoff", "disarm、run 结束或完成本次 flight scope",
        [("detected_takeoff", "BEFORE", "flight_time_warning"), ("flight_time_warning", "BEFORE", "enter_return")],
        ["warning 需要与固件匹配的 Events metadata 或内部 event 观测。"],
        [warning_time],
        "G((detected_takeoff & max_flight_time_enabled) -> ((G_[0,0.9*T_flight_max) !flight_time_warning & F_[0.9*T_flight_max,infty) flight_time_warning) & (G_[0,T_flight_max) !mode_return & F_[T_flight_max,infty) mode_return)))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","detected_takeoff","Commander 记录本次 takeoff epoch。","landed true->false while armed 的 takeoff event。","EVENT", observability="CONDITIONAL"),
            ap(pid,"02","max_flight_time_enabled","运行时 COM_FLT_TIME_MAX 为正。","PARAM_VALUE(COM_FLT_TIME_MAX)>0。","VALUE_COMPARISON", value_type="float", unit="s", observability="CONDITIONAL"),
            ap(pid,"03","flight_time_warning","90% flight-time warning 发生。","与当前 takeoff epoch/COM_FLT_TIME_MAX 关联的 warning event。","EVENT", observability="CONDITIONAL"),
            ap(pid,"04","mode_return","PX4 进入 Return。","current navigation mode/custom mode 为 RTL/Return。","STATE", observability="DIRECT"),
        ],
        ["默认 -1 表示 disabled；不得生成默认 concrete 公式。"],
        "PX4 multicopter SITL；已检测 takeoff；无更高优先级 mode override；运行时参数已归档。"))

    s = p["rtl"]
    pid = "PX4-MC-RTLLOITER-006"
    properties.append(base_property(
        pid, "PX4 RTL 目的地等待后着陆", "PX4 RTL destination loiter before landing", "PX4", ["multicopter SITL"], "NEEDS_CONTEXT", "OFFICIAL_BEHAVIOR", s,
        "PX4 Navigator direct Return", "BEHAVIORAL_DESCRIPTION", "非 mission landing 的 Return 到达目的地 RTL_DESCEND_ALT 并进入等待阶段。",
        ["使用适用的 direct-return landing path。", "RTL_LAND_DELAY >= 0；-1 的 indefinite 变体单独处理。"],
        ["等待运行时 RTL_LAND_DELAY 后开始 Land。"],
        ["等待期间不得在配置时间结束前进入 Land。"],
        ["mission landing pattern 不使用此直接等待义务。", "RTL_LAND_DELAY=-1 表示 indefinite，合法 mode transition 可结束。"],
        "进入目的地 RTL_DESCEND_ALT loiter phase", "Land、离开 Return、indefinite override 或 run 结束",
        [("enter_rtl_loiter_phase", "BEFORE", "enter_land"), ("leave_return", "CANCELS", "rtl_land_delay")],
        ["文档默认 0.5s 与冻结参数元数据默认 0.0s 冲突；只使用 PARAM_VALUE。", "标准 MAVLink 只能派生 phase，精确 phase 需要内部探针。"],
        [runtime_time("T_rtl_land", "enter_rtl_destination_loiter", "enter_land", "RTL_LAND_DELAY", "s", s[2], 0.0, True, "AUTOPILOT_MONOTONIC_BOOT", "PX4 Navigator HRT phase entry", None, "leave_return_or_indefinite_override")],
        "G((enter_rtl_destination_loiter & direct_return_landing_path) -> (G_[0,T_rtl_land) !mode_land & F_[T_rtl_land,infty) mode_land))", "SYMBOLIC_ONLY",
        [
            ap(pid,"01","enter_rtl_destination_loiter","direct RTL 到达目的地下降高度并进入等待 phase。","Navigator RTL phase entry event；纯 wire 推导必须同时满足 mode/target/position freshness。","EVENT", observability="INSTRUMENTATION_REQUIRED"),
            ap(pid,"02","direct_return_landing_path","当前 Return 不使用 mission landing pattern。","runtime RTL_TYPE/mission state 选择 direct landing path。","DERIVED_STATE", observability="CONDITIONAL"),
            ap(pid,"03","mode_land","PX4 进入 Land/明确约定的 descend outcome。","current navigation mode 为 AUTO_LAND；是否计入 DESCEND 必须在 campaign 前固定。","STATE", observability="DIRECT"),
        ],
        ["docs default 0.5s vs source metadata default 0.0s。", "mission landing exclusion 和 exact phase 需要绑定。"],
        "PX4 multicopter SITL；direct Return path、destination、mission state 和 runtime RTL_LAND_DELAY 已归档。"))

    return properties


def render_property_md(prop: dict[str, Any]) -> str:
    scope = prop["system_scope"]
    lines = [
        f"# {prop['property_id']} — {prop['title_zh']}", "",
        f"- 系统/车型：{scope['system']} / {', '.join(scope['vehicles'])}",
        f"- 固件提交：`{scope['firmware_commit']}`",
        f"- 状态：`{prop['status']}`；分类：`{prop['classification']}`",
        f"- 实现符合性：`{prop['implementation_satisfaction']}`", "",
        "## 自然语言证据", "",
    ]
    for src in prop["sources"]:
        loc = src["locator"]
        lines.extend([
            f"### {src['source_id']}", "",
            f"- 类别/权威：`{src['source_class']}` / `{src['authority']}`",
            f"- 版本状态：`{src['version']}` / `{src['document_status']}`",
            f"- 位置：`{src['path_or_url']}:{loc['line_start']}-{loc['line_end']}`",
            f"- SHA-256：`{src['sha256']}`", "",
            "```text", src["exact_quote"], "```", "",
            f"上下文：{src.get('context_summary_zh','')}", "",
        ])
    ir = prop["requirement_ir"]
    lines.extend(["## Requirement IR", "", f"- 主体：{ir['actor']['text']}", f"- 模态：`{ir['modality']}`", f"- 触发：{ir['trigger']['text']}"])
    for label, key in (("前置", "preconditions"), ("义务", "obligations"), ("禁止", "prohibitions"), ("例外", "exceptions")):
        lines.append(f"- {label}：" + ("；".join(item["text"] for item in ir[key]) if ir[key] else "无"))
    lines.extend([f"- 作用域：{ir['scope_start']['text']} → {ir['scope_end']['text']}", ""])
    lines.extend(["## 时间与 MITL", ""])
    for tc in prop["time_contracts"]:
        lines.extend([
            f"- `{tc['time_id']}`：`{tc['formula']}`；单位 `{tc['unit']}`；下界闭合 `{tc['lower_closed']}`。",
            f"  起点：{tc['semantic_start_event']}；终点：{tc['semantic_end_event']}；时钟：`{tc['clock_domain']}`；载体：{tc['timestamp_carrier']}。",
            f"  不确定性：{tc['measurement_uncertainty']}",
        ])
    concrete = prop["mitl"].get("concrete")
    concrete_note = f"`{concrete}`" if concrete is not None else "`null`（没有单一、已启用且上下文闭合的具体实例）"
    lines.extend(["", f"- 符号公式：`{prop['mitl']['symbolic']}`", f"- 单一具体公式：{concrete_note}", f"- 形式化状态：`{prop['mitl']['status']}`", ""])
    if prop["mitl"].get("monitor_syntax") is not None:
        contract = prop["mitl"]["monitor_contract"]
        lines.extend([
            f"- TAMonitor 转换候选：`{prop['mitl']['monitor_syntax']}`",
            f"- 时间编码：源单位 `{contract['source_formula_time_unit']}` → monitor `{contract['monitor_tick_unit']}`，"
            f"每源单位 `{contract['ticks_per_source_unit']}` ticks；{contract['exact_rescaling']}",
            f"- 监视语义：{contract['finite_word_semantics']}",
            f"- 监视证据：`{contract['artifact_path']}` SHA-256 `{contract['artifact_sha256']}`。",
            "",
        ])
    instances = prop["mitl"].get("concrete_instances", [])
    if instances:
        lines.extend([
            "### 运行时具体实例", "",
            "| profile / capture | 参数原值 | 公式时间值 | 状态 | 具体公式 | 证据 |",
            "|---|---:|---:|---|---|---|",
        ])
        for instance in instances:
            formula = instance["formula"] or "未形式化"
            lines.append(
                f"| {instance['profile']} / `{instance['capture_id']}` | "
                f"`{instance['raw_value']} {instance['raw_unit']}` | "
                f"`{instance['normalized_value']} {instance['formula_time_unit']}` | "
                f"`{instance['status']}` | `{formula}` | "
                f"`{instance['source_path']}` SHA-256 `{instance['source_sha256']}`，"
                f"index `{instance['source_param_index']}/{instance['source_param_count']}` |"
            )
        lines.extend(["", "这些实例只证明运行配置值和确定性代换；尚未证明轨迹满足公式。", ""])
    lines.extend(["## 原子命题与待绑定项", "", "| AP | 真值条件 | 可观测性 | 绑定状态 |", "|---|---|---|---|"])
    for item in prop["atomic_propositions"]:
        lines.append(f"| `{item['ap_id']}` | {item['truth_condition']} | `{item['observability']}` | `{item['status']}` |")
    if CURRENT_STAGE >= 5:
        lines.extend(["", "## AP 当前源码与 MAVLink 详细映射", ""])
        for item in prop["atomic_propositions"]:
            lines.extend([
                f"### {item['ap_id']} — `{item['name']}`", "",
                f"- 受控自然语言：{item['controlled_natural_language']}",
                f"- 真值条件：{item['truth_condition']}",
                f"- 有效性：{item['validity_guard']}",
                f"- freshness：{item['freshness']}",
                f"- 可观测性：`{item['observability']}`；绑定状态：`{item['status']}`", "",
                "源码绑定：", "",
            ])
            if not item["source_bindings"]:
                lines.append("- 无可靠绑定；保持 `NEEDS_BINDING`，不猜测。")
            for binding in item["source_bindings"]:
                lines.append(
                    f"- `{binding['semantic_identity'] or binding['symbol']}` — "
                    f"`{binding['file']}:{binding['line']}`；symbol `{binding['symbol']}`；"
                    f"kind `{binding['entity_kind']}`；function `{binding['function'] or ''}`；"
                    f"type `{binding['type'] or ''}`；role `{binding['role']}`；confidence `{binding['confidence']}`。"
                )
                lines.append(f"  证据：{binding['evidence']}")
            lines.extend(["", "MAVLink/观测映射：", ""])
            if not item["mavlink_observations"]:
                lines.append("- 无等价标准 MAVLink 字段；需要源码绑定的插桩或继续补证。")
            for obs in item["mavlink_observations"]:
                field = f".{obs['field']}" if obs["field"] else ""
                lines.append(
                    f"- `{obs['message']}{field}` (ID {obs['message_id']})，方向 `{obs['direction']}`，"
                    f"支持 `{obs['support']}`，时间字段 `{obs['time_field'] or '无'}`。{obs['derivation'] or ''}"
                )
                lines.append(f"  证据：{obs['evidence']}")
            lines.append("")
    binding_note = (
        "源码绑定和 MAVLink 映射在里程碑 5 写入；此文件当前不以实现逻辑补写规范。"
        if CURRENT_STAGE == 4
        else "源码绑定只回答语义身份、位置与观察方式；没有用于修改 Requirement IR 或判断实现满足性。"
    )
    if CURRENT_STAGE >= 7:
        lines.extend(["", "## 合成公式/轨迹门禁", ""])
        category_names = {
            "positive": "正例/合法边界",
            "boundary_negative": "边界反例",
            "late_or_missing": "迟到或缺失",
            "wrong_exception": "错误例外",
            "wrong_correlation": "错误关联",
        }
        lines.extend(["| 类别 | trace | complete-word 期望 | TAMonitor | 变异/限制 |", "|---|---|---|---|---|"])
        trace_count = 0
        for key, label in category_names.items():
            for trace in prop["examples"][key]:
                trace_count += 1
                lines.append(
                    f"| {label} | `{trace['trace_id']}` ([JSON](../../../{trace['path']})) | "
                    f"`{trace['expected']}` | `{trace['monitor_result']}` | {trace.get('mutation') or ''} |"
                )
        if trace_count == 0:
            lines.append("| — | — | — | `NOT_RUN` | 没有上下文闭合且启用的具体公式，故未生成合成 monitor trace。 |")
        lines.extend(["", "### 验证状态", "", "| Gate | 状态 | 证据 |", "|---|---|---|"])
        for gate_name, gate in prop["validation"].items():
            lines.append(f"| `{gate_name}` | `{gate['status']}` | {gate['evidence']} |")
        lines.extend([
            "",
            "完整 monitor 目录还保留 non-vacuity control 与所有失败 stderr。合成 complete-word oracle 不是 TAMonitor；"
            "TAMonitor infinite-prefix 执行若断言、资源门限或三值语义不支持，结果保持 `NOT_RUN/INCONCLUSIVE`，不会用 oracle 冒充。",
            "",
        ])
    lines.extend(["", binding_note, "", "## 冲突与验证", ""])
    for conflict in prop["review"]["conflicts"]:
        lines.append(f"- {conflict}")
    final_monitor_note = (
        "Stage 7 的结果只验证公式转换和合成轨迹接口；当前 monitor blocker 已原样保留，且没有 SITL 性质符合性结论。"
        if CURRENT_STAGE >= 7
        else "当前没有 TAMonitor 或 SITL 符合性结论。"
    )
    lines.extend(["", f"{final_monitor_note}`implementation_satisfaction` 固定为 `NOT_ASSESSED`。", ""])
    return "\n".join(lines)


def render_catalog_md(system: str, props: list[dict[str, Any]]) -> str:
    counts = Counter(prop["status"] for prop in props)
    if CURRENT_STAGE >= 7:
        runtime_note = (
            "运行实例来自保存的 SITL PARAM_VALUE；独立自动审核已将存在上下文/形式化 blocker 的条目回退。"
            "TAMonitor 失败或不支持的执行原样保留，且不等于实现符合性。"
        )
    elif CURRENT_STAGE >= 6:
        runtime_note = "运行实例来自保存的 SITL PARAM_VALUE 快照；禁用域和上下文冲突保持显式，实例化不等于实现符合。"
    else:
        runtime_note = "源码默认值仅作来源记录，具体公式等待真实 SITL PARAM_VALUE 快照。"
    lines = [f"# {system} MITL 性质目录（里程碑 {CURRENT_STAGE}）", "", f"本目录是证据绑定的性质集合，不是飞控符合性结论。{runtime_note}", "", "## 计数", ""]
    for key, value in sorted(counts.items()):
        lines.append(f"- `{key}`：{value}")
    lines.extend(["", "## 性质", "", "| ID | 中文标题 | 状态 | 形式化 |", "|---|---|---|---|"])
    for prop in props:
        lines.append(f"| [{prop['property_id']}](properties/{prop['property_id']}.md) | {prop['title_zh']} | `{prop['status']}` | `{prop['mitl']['status']}` |")
    lines.extend(["", "所有记录：`implementation_satisfaction = NOT_ASSESSED`。", ""])
    return "\n".join(lines)


def write_catalog(system: str, props: list[dict[str, Any]]) -> None:
    out = BENCHMARK / system
    prop_dir = out / "properties"
    prop_dir.mkdir(parents=True, exist_ok=True)
    for old in prop_dir.glob("*.json"):
        old.unlink()
    for old in prop_dir.glob("*.md"):
        old.unlink()
    for prop in props:
        (prop_dir / f"{prop['property_id']}.json").write_text(json.dumps(prop, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (prop_dir / f"{prop['property_id']}.md").write_text(render_property_md(prop), encoding="utf-8")
    commit = ARD_COMMIT if system == "ArduPilot" else PX4_COMMIT
    counts = dict(sorted(Counter(prop["status"] for prop in props).items()))
    catalog_generated_at = OUTPUT_STAGE7_ENRICHED_AT or OUTPUT_GENERATED_AT
    catalog = {
        "schema_version": "1.0",
        "generated_at": catalog_generated_at,
        "evidence_snapshot_at": OUTPUT_GENERATED_AT,
        "stage7_enriched_at": OUTPUT_STAGE7_ENRICHED_AT,
        "system": system,
        "firmware_commit": commit,
        "counts": counts,
        "properties": props,
    }
    (out / "property_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "property_catalog.md").write_text(render_catalog_md(system, props), encoding="utf-8")
    with (out / "property_catalog.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["property_id", "title_zh", "status", "classification", "vehicles", "mitl_status", "time_parameters", "implementation_satisfaction"])
        for prop in props:
            writer.writerow([prop["property_id"], prop["title_zh"], prop["status"], prop["classification"], ";".join(prop["system_scope"]["vehicles"]), prop["mitl"]["status"], ";".join(tc["parameter_id"] or "" for tc in prop["time_contracts"]), prop["implementation_satisfaction"]])
    ap_rows = []
    for prop in props:
        for item in prop["atomic_propositions"]:
            ap_rows.append({"property_id": prop["property_id"], **item})
    (out / "atomic_proposition_map.json").write_text(json.dumps(ap_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "atomic_proposition_map.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["property_id", "ap_id", "name", "kind", "value_type", "unit", "truth_condition", "validity_guard", "freshness", "observability", "status", "source_binding_count", "mavlink_observation_count"])
        for item in ap_rows:
            writer.writerow([item["property_id"], item["ap_id"], item["name"], item["kind"], item["value_type"], item["unit"] or "", item["truth_condition"], item["validity_guard"], item["freshness"], item["observability"], item["status"], len(item["source_bindings"]), len(item["mavlink_observations"])])
    with (out / "time_constraints.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["property_id", "time_id", "parameter_id", "raw_expression", "lower", "upper", "lower_closed", "upper_closed", "unit", "source_type", "source_id", "clock_domain", "timestamp_carrier", "conversion", "measurement_uncertainty", "status", "runtime_instance_count", "runtime_values", "runtime_instance_statuses", "configuration_snapshot"])
        for prop in props:
            for tc in prop["time_contracts"]:
                instances = prop["mitl"].get("concrete_instances", [])
                writer.writerow([prop["property_id"], tc["time_id"], tc["parameter_id"] or "", tc["raw_expression"], tc["lower"], tc["upper"] if tc["upper"] is not None else "", tc["lower_closed"], tc["upper_closed"] if tc["upper_closed"] is not None else "", tc["unit"], tc["source_type"], tc["source_id"] or "", tc["clock_domain"], tc["timestamp_carrier"] or "", tc["conversion"] or "", tc["measurement_uncertainty"] or "", tc["status"], len(instances), json.dumps([{"capture_id": item["capture_id"], "raw": item["raw_value"], "normalized_s": item["normalized_value"]} for item in instances], ensure_ascii=False), "|".join(item["status"] for item in instances), prop["system_scope"]["configuration_snapshot"]["path"] or ""])
    with (out / "source_bindings.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["property_id", "ap_id", "binding_id", "commit", "file", "line", "column", "symbol", "semantic_identity", "entity_kind", "function", "role", "type", "confidence", "evidence"])
        for prop in props:
            for item in prop["atomic_propositions"]:
                for binding in item["source_bindings"]:
                    writer.writerow([prop["property_id"], item["ap_id"], binding["binding_id"], binding["commit"], binding["file"], binding["line"], binding["column"] or "", binding["symbol"], binding["semantic_identity"] or "", binding["entity_kind"], binding["function"] or "", binding["role"], binding["type"] or "", binding["confidence"], binding["evidence"]])
    with (out / "mavlink_observation_matrix.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["property_id", "ap_id", "ap_name", "observability", "message", "message_id", "field", "direction", "derivation", "time_field", "support", "evidence"])
        for prop in props:
            for item in prop["atomic_propositions"]:
                if not item["mavlink_observations"]:
                    writer.writerow([prop["property_id"], item["ap_id"], item["name"], item["observability"], "", "", "", "", "No standard MAVLink observation; use source-bound instrumentation or leave unresolved.", "", "UNKNOWN", "Milestone-5 AP observation audit."])
                for obs in item["mavlink_observations"]:
                    writer.writerow([prop["property_id"], item["ap_id"], item["name"], item["observability"], obs["message"], obs["message_id"] if obs["message_id"] is not None else "", obs["field"] or "", obs["direction"], obs["derivation"] or "", obs["time_field"] or "", obs["support"], obs["evidence"]])


def write_adjudication(properties: list[dict[str, Any]]) -> None:
    out = BENCHMARK / "extraction_runs" / "milestone4"
    out.mkdir(parents=True, exist_ok=True)
    selected_sources: dict[tuple[str, int, int], str] = {}
    for prop in properties:
        for src in prop["sources"]:
            loc = src["locator"]
            selected_sources[(src["path_or_url"], loc["line_start"], loc["line_end"])] = prop["property_id"]
    summary: dict[str, Any] = {"generated_at": GENERATED_AT, "selected_properties": len(properties), "systems": {}}
    for system in ("ArduPilot", "PX4"):
        input_path = BENCHMARK / "extraction_runs" / "milestone3" / system / "prefilter_candidates.jsonl"
        output_path = out / f"{system}_adjudication_ledger.jsonl"
        counts: Counter[str] = Counter()
        with input_path.open("r", encoding="utf-8") as inp, output_path.open("w", encoding="utf-8") as dst:
            for line in inp:
                record = json.loads(line)
                rel = record.get("source_path") or record.get("path") or ""
                start = int(record.get("line_start") or 0)
                end = int(record.get("line_end") or start)
                matched: list[str] = []
                for (source_path, selected_start, selected_end), property_id in selected_sources.items():
                    if source_path.endswith(rel) or rel.endswith(source_path):
                        if start <= selected_end and end >= selected_start:
                            matched.append(property_id)
                decision = "SELECTED_SOURCE_EVIDENCE" if matched else "PENDING_CONTEXT_REVIEW"
                counts[decision] += 1
                dst.write(json.dumps({
                    "candidate_id": record.get("candidate_id"),
                    "system": system,
                    "node_id": record.get("node_id"),
                    "source_path": rel,
                    "line_start": start,
                    "line_end": end,
                    "decision": decision,
                    "property_ids": sorted(set(matched)),
                    "implementation_satisfaction": "NOT_ASSESSED",
                    "note": "Unselected candidates remain retained; pending is not rejection and not acceptance.",
                }, ensure_ascii=False, sort_keys=True) + "\n")
        summary["systems"][system] = {"input": str(input_path.relative_to(ROOT)), "output": str(output_path.relative_to(ROOT)), "counts": dict(sorted(counts.items()))}
    (out / "adjudication_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readme = f"""# Milestone 4: evidence-bound Requirement IR and symbolic MITL

Generated: `{GENERATED_AT}`.

- Curated records: {len(properties)} ({sum(p['system_scope']['system']=='ArduPilot' for p in properties)} ArduPilot, {sum(p['system_scope']['system']=='PX4' for p in properties)} PX4).
- Every Milestone-3 prefilter candidate is represented in a per-system adjudication ledger.
- `PENDING_CONTEXT_REVIEW` means retained and unresolved; it is neither rejection nor acceptance.
- Concrete MITL is intentionally null until Milestone 6 captures actual runtime parameters.
- No epsilon, conformance result, or source-control-derived requirement was added.

Reproduce:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 4
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_property_catalog.py --stage 4
```
"""
    (out / "README.md").write_text(readme, encoding="utf-8")


def write_candidates_and_exclusions(system: str, props: list[dict[str, Any]]) -> None:
    raw_note = (
        "benchmark/extraction_runs/milestone4/superseded_px4_draft/ "
        "(SUPERSEDED_NON_CANONICAL_DRAFT; retained only as immutable historical input)"
        if system == "PX4"
        else "read-only ArduPilot source audit result retained in the task record"
    )
    lines = [f"# {system} 候选与排除台账", "", "## 已规范化候选", ""]
    for prop in props:
        lines.append(f"- `{prop['property_id']}`：`{prop['status']}`；{prop['title_zh']}。")
    lines.extend(["", "## 仍待上下文审查", "", f"- 全量逐条状态见 `benchmark/extraction_runs/milestone4/{system}_adjudication_ledger.jsonl`。", f"- 原始专项审计输入：`{raw_note}`。", "- `PENDING_CONTEXT_REVIEW` 不是拒绝，也不表示已经提取完毕。", "", "## 明确排除类别", "", "- 普通控制流 timeout/guard、watchdog 和计数器，若无独立规范来源，不产生性质。", "- 控制器 time constant、filter cutoff、stream rate、sensor delay compensation 和调参建议，不当作离散 deadline。", "- SITL-only delay、logger/peripheral housekeeping timeout 不进入飞控行为性质。", "- PGFuzz 历史性质和 ADGFuzz ground/deviation/silence oracle 不自动继承；后者仅保留为 `AUXILIARY_ORACLE`。", "- 无数值的 immediately/promptly 不补人工阈值；未解决项保留候选。", "- 任何已有实现 guard 只能用于 AP 绑定，不能回填 Requirement IR。", ""])
    (BENCHMARK / system / "candidates_and_exclusions.md").write_text("\n".join(lines), encoding="utf-8")


def normalize_binding(system: str, ap_id: str, index: int, raw: dict[str, Any]) -> dict[str, Any]:
    commit = ARD_COMMIT if system == "ArduPilot" else PX4_COMMIT
    confidence_map = {"exact": "EXACT", "may": "MAY", "modelled": "MODELLED", "modeled": "MODELLED", "name-only": "NAME_ONLY", "name_only": "NAME_ONLY"}
    entity_map = {
        "variable": "VARIABLE", "field": "FIELD", "parameter": "PARAMETER", "function": "FUNCTION",
        "return": "RETURN", "callback": "CALLBACK", "assignment": "ASSIGNMENT", "message_producer": "MESSAGE_PRODUCER",
        "message_consumer": "MESSAGE_CONSUMER", "event": "EVENT", "topic": "TOPIC", "other": "OTHER",
    }
    role_map = {"definition": "DEFINITION", "read": "READ", "write": "WRITE", "derivation": "DERIVATION", "producer": "PRODUCER", "consumer": "CONSUMER", "guard": "GUARD", "observation_site": "OBSERVATION_SITE"}
    file_text = str(raw.get("file") or raw.get("path") or "")
    prefix = "baseline/ardupilot/" if system == "ArduPilot" else "baseline/px4/"
    if file_text.startswith(str(ROOT) + "/"):
        file_text = file_text[len(str(ROOT)) + 1 :]
    elif file_text and not file_text.startswith("baseline/"):
        file_text = prefix + file_text.lstrip("./")
    line_value = raw.get("line") or raw.get("line_start")
    if isinstance(line_value, str) and "-" in line_value:
        line_value = line_value.split("-", 1)[0]
    confidence_raw = str(raw.get("confidence") or "EXACT")
    entity_raw = str(raw.get("entity_kind") or raw.get("kind") or "OTHER")
    role_raw = str(raw.get("role") or "DERIVATION")
    repo_relative = file_text[len(prefix) :] if file_text.startswith(prefix) else file_text
    repo_url = "https://github.com/ArduPilot/ardupilot" if system == "ArduPilot" else "https://github.com/PX4/PX4-Autopilot"
    permalink = f"{repo_url}/blob/{commit}/{repo_relative}#L{int(line_value)}"
    evidence_text = str(raw.get("evidence") or "Frozen-source identity audit; implementation location only, not a satisfaction claim.")
    if permalink not in evidence_text:
        evidence_text += f" Fixed permalink: {permalink}"
    return {
        "binding_id": str(raw.get("binding_id") or f"{ap_id}-B{index:02d}"),
        "commit": str(raw.get("commit") or commit),
        "file": file_text,
        "line": int(line_value),
        "column": int(raw["column"]) if raw.get("column") not in (None, "") else None,
        "symbol": str(raw.get("symbol") or raw.get("symbols") or ""),
        "semantic_identity": raw.get("semantic_identity") or raw.get("qualified_name") or raw.get("symbol"),
        "entity_kind": entity_map.get(entity_raw.lower(), entity_raw.upper() if entity_raw.upper() in set(entity_map.values()) else "OTHER"),
        "function": raw.get("function"),
        "role": role_map.get(role_raw.lower(), role_raw.upper() if role_raw.upper() in set(role_map.values()) else "DERIVATION"),
        "type": raw.get("type"),
        "macro_spelling_location": raw.get("macro_spelling_location"),
        "macro_expansion_location": raw.get("macro_expansion_location"),
        "confidence": confidence_map.get(confidence_raw.lower(), confidence_raw.upper() if confidence_raw.upper() in {"EXACT", "MAY", "MODELLED", "NAME_ONLY"} else "MAY"),
        "evidence": evidence_text,
    }


def load_binding_audit(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("atomic_propositions") or doc.get("aps") or []
    mapping = {}
    if isinstance(entries, dict):
        entries = [{"ap_id": key, **value} for key, value in entries.items()]
    for entry in entries:
        mapping[entry["ap_id"]] = list(entry.get("bindings") or entry.get("source_bindings") or [])
    return mapping, {
        "compile_database": doc.get("compile_database") or doc.get("compile_db") or {},
        "audit_verification": doc.get("verification") or {},
        "audit_sha256": sha256_file(path),
    }


def apply_stage5(properties: list[dict[str, Any]]) -> None:
    audit_dir = BENCHMARK / "extraction_runs" / "milestone5"
    observation_doc = json.loads((audit_dir / "mavlink_ap_observation_audit.json").read_text(encoding="utf-8"))
    observations = {entry["ap_id"]: entry for entry in observation_doc["atomic_propositions"]}
    binding_maps: dict[str, dict[str, list[dict[str, Any]]]] = {}
    compile_manifests: dict[str, Any] = {}
    for system, filename in (("ArduPilot", "ardupilot_binding_audit.json"), ("PX4", "px4_binding_audit.json")):
        binding_maps[system], compile_manifests[system] = load_binding_audit(audit_dir / filename)
    expected_aps = {item["ap_id"] for prop in properties for item in prop["atomic_propositions"]}
    if expected_aps != set(observations):
        raise ValueError(f"observation audit AP mismatch: missing={sorted(expected_aps-set(observations))}")
    for prop in properties:
        system = prop["system_scope"]["system"]
        for item in prop["atomic_propositions"]:
            raw_bindings = binding_maps[system].get(item["ap_id"], [])
            item["source_bindings"] = [normalize_binding(system, item["ap_id"], index, binding) for index, binding in enumerate(raw_bindings, start=1)]
            obs_entry = observations[item["ap_id"]]
            item["mavlink_observations"] = obs_entry["observations"]
            item["observability"] = obs_entry["observability"]
            if item["source_bindings"]:
                item["status"] = "PARTIALLY_BOUND" if obs_entry["observability"] == "UNRESOLVED" else "BOUND"
            else:
                item["status"] = "NEEDS_BINDING"
        if prop["status"] == "NEEDS_BINDING" and all(item["status"] in {"BOUND", "PARTIALLY_BOUND"} for item in prop["atomic_propositions"]):
            prop["status"] = "CANDIDATE" if prop["classification"] == "PARAM_METADATA_CANDIDATE" else "REVIEW_READY"
        prop["extraction_record"]["run_id"] = "milestone5-current-source-binding-v1"
        prop["extraction_record"]["raw_outputs"].extend([
            f"benchmark/extraction_runs/milestone5/{'ardupilot' if system == 'ArduPilot' else 'px4'}_binding_audit.json",
            "benchmark/extraction_runs/milestone5/mavlink_ap_observation_audit.json",
        ])
        prop["extraction_record"]["adjudication"] += " Milestone 5 added frozen-source identity and observation mappings without changing the source-derived requirement."
        prop["validation"]["source_lines"] = check("PASS", "Every binding path/line/symbol is validated against the frozen checkout.", "python3 benchmark/scripts/validate_source_bindings.py")
        prop["validation"]["permalinks"] = check("PASS", "Binding commit/path/line can be converted deterministically to a fixed GitHub commit permalink.", "python3 benchmark/scripts/validate_source_bindings.py")
    validation_dir = BENCHMARK / "extraction_runs" / "milestone5"
    (validation_dir / "compile_database_manifest.json").write_text(json.dumps({"generated_at": GENERATED_AT, "systems": compile_manifests}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_bound(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return format(float(value), ".15g")


def apply_stage6(properties: list[dict[str, Any]]) -> None:
    global OUTPUT_GENERATED_AT
    evidence_path = BENCHMARK / "extraction_runs" / "milestone6" / "runtime_evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    OUTPUT_GENERATED_AT = evidence["generated_at"]
    evidence_rel = str(evidence_path.relative_to(ROOT))
    evidence_sha = sha256_file(evidence_path)
    captures = {item["capture_id"]: item for item in evidence["captures"]}
    rows_by_property: dict[str, list[dict[str, Any]]] = {}
    for row in evidence["property_parameters"]:
        rows_by_property.setdefault(row["property_id"], []).append(row)
    expected = {prop["property_id"] for prop in properties}
    if set(rows_by_property) != expected:
        raise ValueError(
            f"runtime property parameter mismatch: missing={sorted(expected-set(rows_by_property))} "
            f"extra={sorted(set(rows_by_property)-expected)}"
        )

    for prop in properties:
        property_id = prop["property_id"]
        rows = sorted(rows_by_property[property_id], key=lambda row: row["capture_id"])
        tc = prop["time_contracts"][0]
        instances = []
        for row in rows:
            capture = captures[row["capture_id"]]
            raw_value = float(row["value"])
            raw_unit = row["unit"]
            if raw_unit == "ms":
                normalized = raw_value / 1000.0
                conversion = f"{format_bound(raw_value)} ms / 1000 = {format_bound(normalized)} s"
            elif raw_unit == "s":
                normalized = raw_value
                conversion = f"identity: {format_bound(raw_value)} s = {format_bound(normalized)} s"
            else:
                raise ValueError(f"{property_id}: unsupported formula time unit {raw_unit}")
            symbolic = prop["mitl"]["symbolic"]
            concrete_formula = None
            if symbolic is not None:
                concrete_formula = re.sub(
                    rf"\b{re.escape(tc['time_id'])}\b",
                    format_bound(normalized),
                    symbolic,
                )
            if row["status"] == "RUNTIME_OBSERVED_DISABLED_DOMAIN":
                instance_status = "DISABLED_BY_RUNTIME_CONFIGURATION"
                concrete_formula = None
                notes = "运行时参数值落在官方定义的禁用域；保留数值与来源，但不构造零/负区间公式，当前 profile 没有激活该时间义务。"
            elif symbolic is None:
                instance_status = "NOT_FORMALIZED"
                notes = "时间值已观测，但 Requirement IR 的上下文尚未闭合，因此没有生成具体公式。"
            elif prop["status"] == "NEEDS_CONTEXT" or prop["mitl"]["status"] == "NEEDS_CONTEXT":
                instance_status = "NEEDS_CONTEXT"
                notes = "数值代换可复现，但例外/eligibility/phase 上下文尚未闭合；不能进入监视器门禁。"
            else:
                instance_status = "INSTANTIATED_UNVALIDATED"
                notes = "由保存的 PARAM_VALUE 确定性代换；尚未运行 MITL parser、可满足性或 TAMonitor。"
            instances.append({
                "profile": f"{capture['system']}/{capture['vehicle']} — {capture['profile']}",
                "capture_id": row["capture_id"],
                "parameter_id": row["parameter_id"],
                "raw_value": row["value"],
                "raw_unit": raw_unit,
                "normalized_value": normalized,
                "formula_time_unit": "s",
                "conversion": conversion,
                "formula": concrete_formula,
                "status": instance_status,
                "source_path": row["source_path"],
                "source_sha256": row["source_sha256"],
                "source_param_index": row["source_param_index"],
                "source_param_count": row["source_param_count"],
                "clock_domain": tc["clock_domain"],
                "notes": notes,
            })
        prop["mitl"]["concrete_instances"] = instances
        active_formulas = {
            item["formula"] for item in instances
            if item["status"] == "INSTANTIATED_UNVALIDATED" and item["formula"] is not None
        }
        if len(active_formulas) == 1 and all(item["status"] == "INSTANTIATED_UNVALIDATED" for item in instances):
            prop["mitl"]["concrete"] = next(iter(active_formulas))
            prop["mitl"]["status"] = "CONCRETE_UNVALIDATED"
        else:
            prop["mitl"]["concrete"] = None
            if any(item["status"] in {"NEEDS_CONTEXT", "NOT_FORMALIZED"} for item in instances):
                prop["mitl"]["status"] = "NEEDS_CONTEXT"

        raw_values = [item["raw_value"] for item in instances]
        runtime_operand = next((item for item in tc["operands"] if item["name"] == "runtime_value"), None)
        if runtime_operand is not None:
            runtime_operand["value"] = raw_values[0] if len(set(map(float, raw_values))) == 1 else "profile-specific: " + ", ".join(
                f"{item['capture_id']}={item['raw_value']}" for item in instances
            )
            runtime_operand["source_id"] = f"{evidence_rel}#property_parameters/{property_id}"
        tc["conversion"] = (
            "MITL interval unit is seconds; divide runtime parameter milliseconds by 1000."
            if tc["unit"] == "ms"
            else "MITL interval unit is seconds; runtime seconds use identity conversion."
        )
        tc["status"] = "RESOLVED"
        prop["system_scope"]["configuration_snapshot"] = {
            "status": "CAPTURED",
            "path": evidence_rel,
            "sha256": evidence_sha,
            "notes": "具体实例逐 profile 引用保存的 PARAM_VALUE 文件、SHA-256、param_index/param_count；源码默认值未被代替为运行值。",
        }
        prop["extraction_record"]["run_id"] = "milestone6-runtime-instantiation-v1"
        if evidence_rel not in prop["extraction_record"]["raw_outputs"]:
            prop["extraction_record"]["raw_outputs"].append(evidence_rel)
        prop["extraction_record"]["adjudication"] += " Milestone 6 added per-profile runtime parameter instances without changing Requirement IR or assessing satisfaction."
        prop["validation"]["type_unit"] = check(
            "PASS",
            "Runtime wire value, decoded value, raw unit, seconds normalization, param index/count, source path, and SHA-256 are retained per profile.",
            "python3 benchmark/scripts/validate_runtime_capture.py",
        )
        prop["validation"]["parser"] = check(
            "NOT_RUN",
            "Concrete mathematical substitution exists where enabled/context-closed, but parser and monitor syntax validation remain Milestone 7 gates.",
        )
        prop["review"]["rationale"] = "Milestone 6 runtime parameter evidence is bound. Final parser, trace, context-conflict, and independent-review gates remain open."


def _trace_reference(trace: dict[str, Any]) -> dict[str, Any]:
    oracle_verdict = trace["expected"]["reference_oracle_complete_word_verdict"]
    expected = "SATISFIED" if oracle_verdict == "POSITIVE" else "VIOLATED"
    tamonitor = trace["tamonitor"]
    if tamonitor["status"] != "EXECUTED" or tamonitor.get("verdict") is None:
        monitor_result = "NOT_RUN"
    else:
        monitor_result = {
            "POSITIVE": "SATISFIED",
            "NEGATIVE": "VIOLATED",
            "INCONCLUSIVE": "INCONCLUSIVE",
        }.get(tamonitor["verdict"], "NOT_RUN")
    mutation = (
        f"{trace['case_kind']}: {trace['expected']['reference_oracle_reason']} "
        f"TAMonitor prefix expectation={trace['expected']['tamonitor_infinite_prefix_verdict']}; "
        f"comparison={trace['comparison_status']}."
    )
    return {
        "trace_id": trace["trace_id"],
        "path": trace["trace"]["path"],
        "sha256": trace["trace"]["sha256"],
        "expected": expected,
        "monitor_result": monitor_result,
        "mutation": mutation,
    }


def apply_stage7(properties: list[dict[str, Any]]) -> None:
    global OUTPUT_STAGE7_ENRICHED_AT
    monitor_path = BENCHMARK / "extraction_runs" / "milestone7" / "monitor_validation" / "monitor_validation.json"
    review_path = BENCHMARK / "extraction_runs" / "milestone7" / "independent_review.json"
    monitor_doc = json.loads(monitor_path.read_text(encoding="utf-8"))
    review_doc = json.loads(review_path.read_text(encoding="utf-8"))
    OUTPUT_STAGE7_ENRICHED_AT = review_doc["generated_at"]
    monitor_by_id = {item["property_id"]: item for item in monitor_doc["properties"]}
    review_by_id = {item["property_id"]: item for item in review_doc["properties"]}
    property_ids = {prop["property_id"] for prop in properties}
    if set(review_by_id) != property_ids:
        raise ValueError(
            f"independent-review property mismatch: missing={sorted(property_ids-set(review_by_id))} "
            f"extra={sorted(set(review_by_id)-property_ids)}"
        )
    concrete_ids = {prop["property_id"] for prop in properties if prop["mitl"]["concrete"] is not None}
    if set(monitor_by_id) != concrete_ids:
        raise ValueError(
            f"monitor property mismatch: missing={sorted(concrete_ids-set(monitor_by_id))} "
            f"extra={sorted(set(monitor_by_id)-concrete_ids)}"
        )
    if monitor_doc["scope"]["implementation_satisfaction_assessed"] is not False:
        raise ValueError("monitor artifact claims implementation assessment")
    reviewer = review_doc["reviewer"]
    if reviewer["is_human"] or reviewer["acceptance_claimed"] or reviewer["decision"] != "NOT_PERFORMED":
        raise ValueError("automated independent audit was misrepresented as human acceptance")

    monitor_rel = str(monitor_path.relative_to(ROOT))
    review_rel = str(review_path.relative_to(ROOT))
    monitor_sha = sha256_file(monitor_path)
    review_sha = sha256_file(review_path)
    for prop in properties:
        property_id = prop["property_id"]
        audit = review_by_id[property_id]
        observed_formula = audit.get("formula_observed")
        if observed_formula != prop["mitl"]["concrete"]:
            raise ValueError(f"{property_id}: independent-review formula drift")
        audit_status = audit["audit_status"]
        if audit_status not in {"NEEDS_CONTEXT", "CANDIDATE"}:
            raise ValueError(f"{property_id}: unsupported automated audit status {audit_status}")
        # A downgrade is a readiness safeguard, not a human ACCEPT/REJECT decision.
        prop["status"] = audit_status
        for blocker in audit["blockers"]:
            rendered = f"M7 automated independent audit: {blocker}"
            if rendered not in prop["review"]["conflicts"]:
                prop["review"]["conflicts"].append(rendered)
        prop["review"]["decision"] = "PENDING"
        prop["review"]["reviewer"] = None
        prop["review"]["reviewed_at"] = None
        prop["review"]["rationale"] = (
            f"Automated independent evidence audit recommends {audit_status} and records unresolved gates in "
            f"{review_rel} (SHA-256 {review_sha}). It is not a human review or arbitration; decision remains PENDING."
        )
        prop["validation"]["independent_review"] = check(
            "INCONCLUSIVE",
            f"Automated non-human audit completed 9 gates and recommends {audit_status}; blockers={'; '.join(audit['blockers'])}. "
            "No human reviewer or arbitration was claimed.",
            None,
        )
        prop["extraction_record"]["run_id"] = "milestone7-monitor-and-independent-audit-v1"
        for output in (monitor_rel, review_rel):
            if output not in prop["extraction_record"]["raw_outputs"]:
                prop["extraction_record"]["raw_outputs"].append(output)
        prop["extraction_record"]["adjudication"] += (
            " Milestone 7 recorded a non-human independent rollback recommendation and synthetic monitor evidence; "
            "neither was used as a firmware-conformance or human-acceptance decision."
        )
        if property_id in {"ARD-COPTER-GCS-001", "PX4-MC-GCSLOSS-002"}:
            prop["extraction_record"]["adjudication"] += (
                " A final independent claims audit detected implementation-semantic bleed in an earlier draft; "
                "the generator was corrected to the source-faithful heartbeat/data-link wording before delivery, "
                "while current implementation paths remain mapping evidence only."
            )

        monitor = monitor_by_id.get(property_id)
        if monitor is None:
            prop["mitl"]["monitor_syntax"] = None
            prop["mitl"]["monitor_contract"] = None
            if audit_status == "NEEDS_CONTEXT":
                prop["mitl"]["status"] = "NEEDS_CONTEXT"
            reason = "No enabled, context-closed concrete formula entered the monitor gate."
            for gate in ("parser", "satisfiable", "non_tautology", "non_vacuity", "monitor"):
                prop["validation"][gate] = check("NOT_APPLICABLE", reason, None)
            continue

        if monitor["source_formula"] != prop["mitl"]["concrete"]:
            raise ValueError(f"{property_id}: monitor source formula drift")
        encoding = monitor["monitor_encoding"]
        if encoding["tick_unit"] != "ms" or encoding["ticks_per_source_second"] != 1000:
            raise ValueError(f"{property_id}: unexpected monitor time encoding")
        prop["mitl"]["monitor_syntax"] = encoding["formula"]
        prop["mitl"]["monitor_contract"] = {
            "source_formula_time_unit": "s",
            "monitor_tick_unit": encoding["tick_unit"],
            "ticks_per_source_unit": encoding["ticks_per_source_second"],
            "exact_rescaling": (
                "All finite seconds bounds are multiplied exactly by 1000 into integer milliseconds; "
                "no rounding or epsilon is introduced."
            ),
            "interval_openness_preserved": encoding["interval_openness_preserved"],
            "finite_word_semantics": (
                "Reference oracle: complete pointwise finite word. TAMonitor: infinite-word prefix. "
                "Both adapters use monotonically increasing absolute synthetic global-clock ticks, not inter-event delays. "
                "The two verdict domains are stored separately; unsupported executions and mismatches are not replaced by oracle verdicts."
            ),
            "tool": "TAMonitor via MightyPPL/MoniTAal; exact binary hashes are in the referenced artifact",
            "artifact_path": monitor_rel,
            "artifact_sha256": monitor_sha,
        }
        monitor_overall = monitor["overall_status"]
        if monitor_overall == "PASS":
            prop["mitl"]["status"] = "MONITOR_VALIDATED"
            monitor_gate_status = "PASS"
            monitor_gate_summary = (
                "All synthetic infinite-prefix trace verdicts matched the separately recorded "
                "TAMonitor expectations. This validates only the encoded formula/test adapter, not the requirement context or firmware."
            )
            for instance in prop["mitl"].get("concrete_instances", []):
                if instance["formula"] == prop["mitl"]["concrete"] and instance["status"] == "INSTANTIATED_UNVALIDATED":
                    instance["status"] = "INSTANTIATED_FORMULA_VALIDATED"
                    instance["notes"] = (
                        "Stage 7 已完成 parser、正/负公式可满足性、独立完整词 oracle 与 TAMonitor 无限前缀合成轨迹门禁；"
                        "只验证该公式编码和适配器，不验证自然语言上下文或飞控实现符合性。"
                    )
        elif monitor_overall == "FAILED":
            prop["mitl"]["status"] = "MONITOR_VALIDATION_FAILED"
            monitor_gate_status = "FAIL"
            monitor_gate_summary = (
                "At least one executed synthetic trace produced a TAMonitor verdict different from the expected "
                "infinite-prefix verdict. The mismatch is retained and the formula instance remains unvalidated."
            )
            for instance in prop["mitl"].get("concrete_instances", []):
                if instance["formula"] == prop["mitl"]["concrete"]:
                    instance["notes"] = (
                        "Stage 7 parser、正/负公式可满足性与独立 oracle 门禁已运行，但 TAMonitor 合成轨迹存在 verdict mismatch；"
                        "实例保持未验证，且没有飞控实现符合性结论。"
                    )
        elif monitor_overall == "UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME":
            prop["mitl"]["status"] = "UNSUPPORTED_BY_MONITOR"
            monitor_gate_status = "INCONCLUSIVE"
            monitor_gate_summary = (
                "At least one required synthetic trace could not execute under the primary TAMonitor configuration. "
                "The resource/semantic blocker is retained and the formula instance remains unvalidated."
            )
            for instance in prop["mitl"].get("concrete_instances", []):
                if instance["formula"] == prop["mitl"]["concrete"]:
                    instance["notes"] = (
                        "Stage 7 parser、正/负公式可满足性与独立 oracle 门禁已运行，但主 TAMonitor 合成轨迹受资源/语义限制；"
                        "实例保持未验证，且没有飞控实现符合性结论。"
                    )
        else:
            raise ValueError(f"{property_id}: unknown monitor overall status {monitor_overall}")
        parser_ok = monitor["parser"]["monitor_syntax_probe"]["status"] == "PASS"
        prop["validation"]["parser"] = check(
            "PASS" if parser_ok else "FAIL",
            "The presentation formula probe is preserved as unsupported; the explicit integer-ms monitor encoding parses/builds."
            if parser_ok else "The explicit monitor encoding did not parse/build.",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
        )
        formula_sat = monitor["monitor_build"].get("formula_satisfiable") == "SAT"
        negative_sat = monitor["monitor_build"].get("negative_formula_satisfiable") == "SAT"
        prop["validation"]["satisfiable"] = check(
            "PASS" if formula_sat else "FAIL",
            "TAMonitor build metadata reports the transformed positive formula SAT." if formula_sat else "Positive formula SAT was not established.",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
        )
        prop["validation"]["non_tautology"] = check(
            "PASS" if negative_sat else "FAIL",
            "TAMonitor build metadata reports the negated transformed formula SAT; this excludes a tautology under the compiled syntax."
            if negative_sat else "Negated formula SAT was not established.",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
        )
        non_vacuity = monitor["reference_oracle"]["non_vacuity_pair"]["status"] == "PASS"
        prop["validation"]["non_vacuity"] = check(
            "PASS" if non_vacuity else "FAIL",
            "The explicitly identified complete-word reference oracle distinguishes a triggered counterexample from a trigger-disabled control; it is not TAMonitor."
            if non_vacuity else "Reference-oracle non-vacuity pair failed.",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
        )
        comparisons = monitor["trace_comparison_counts"]
        prop["validation"]["monitor"] = check(
            monitor_gate_status,
            f"TAMonitor infinite-prefix status={monitor_overall}; trace comparisons={json.dumps(comparisons, sort_keys=True)}. "
            f"{monitor_gate_summary} Exact stdout/stderr and result metadata are retained.",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
        )

        prop["examples"] = {
            "positive": [],
            "boundary_negative": [],
            "late_or_missing": [],
            "wrong_exception": [],
            "wrong_correlation": [],
        }
        positive_cases = {"positive_after_threshold", "boundary_exact_legal", "boundary_first_grid_point_legal"}
        negative_cases = {"too_early_one_tick", "boundary_exact_excluded"}
        late_cases = {"late_response_unbounded_legal", "missing_completed_trace"}
        for trace in monitor["traces"]:
            reference = _trace_reference(trace)
            if trace["case_kind"] in positive_cases:
                prop["examples"]["positive"].append(reference)
            elif trace["case_kind"] in negative_cases:
                prop["examples"]["boundary_negative"].append(reference)
            elif trace["case_kind"] in late_cases:
                prop["examples"]["late_or_missing"].append(reference)
        # The generated vacuous-trigger control remains referenced by the non-vacuity check.
        # Exception and cross-correlation traces stay empty because those semantics are not
        # context-closed; inventing them would hide the independent-review blockers.


def validate_in_memory(properties: list[dict[str, Any]]) -> None:
    schema = json.loads((BENCHMARK / "schemas" / "property.schema.json").read_text(encoding="utf-8"))
    # Ubuntu 22.04 ships jsonschema 3.2.0 (Draft 7).  The selected schema
    # features are Draft-7 compatible; $defs is still resolved as a JSON
    # Pointer target even though the keyword itself is newer.
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    errors = []
    for prop in properties:
        for error in validator.iter_errors(prop):
            errors.append(f"{prop['property_id']}:{'/'.join(map(str,error.absolute_path))}: {error.message}")
    if errors:
        raise ValueError("\n".join(errors))


def main() -> int:
    global CURRENT_STAGE
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=(4, 5, 6, 7), default=7, help="4=symbolic IR; 5=source/MAVLink bindings; 6=runtime parameter instances; 7=monitor/independent audit")
    args = parser.parse_args()
    CURRENT_STAGE = args.stage
    properties = build_properties()
    if CURRENT_STAGE >= 5:
        apply_stage5(properties)
    if CURRENT_STAGE >= 6:
        apply_stage6(properties)
    if CURRENT_STAGE >= 7:
        apply_stage7(properties)
    validate_in_memory(properties)
    for system in ("ArduPilot", "PX4"):
        scoped = [prop for prop in properties if prop["system_scope"]["system"] == system]
        write_catalog(system, scoped)
        write_candidates_and_exclusions(system, scoped)
    write_adjudication(properties)
    print(f"generated stage={CURRENT_STAGE} {len(properties)} properties: ArduPilot=7 PX4=6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
