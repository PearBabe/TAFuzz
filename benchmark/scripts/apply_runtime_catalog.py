#!/usr/bin/env python3
"""Build the profile-layered MAVLink message support evidence matrix.

The output deliberately reports independent evidence layers.  It does not
collapse XML definition, heuristic static references, baseline observation,
request-window observation, or COMMAND_ACK into a global support boolean.

Inputs are the frozen static message catalog and the merged Milestone-6
runtime evidence.  Output is deterministic: no current wall-clock value is
embedded, input hashes are recorded, rows have a stable order, and ``--check``
compares the expected bytes without modifying files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "benchmark" / "mavlink_catalog"
MILESTONE6_DIR = ROOT / "benchmark" / "extraction_runs" / "milestone6"

STATIC_MESSAGES_PATH = CATALOG_DIR / "messages_and_fields.json"
STATIC_SUPPORT_PATH = CATALOG_DIR / "static_support_matrix.csv"
STATIC_MANIFEST_PATH = CATALOG_DIR / "manifest.json"
RUNTIME_EVIDENCE_PATH = MILESTONE6_DIR / "runtime_evidence.json"
RUNTIME_MATRIX_PATH = MILESTONE6_DIR / "runtime_message_support_matrix.json"
OUTPUT_CSV_PATH = CATALOG_DIR / "actual_support_matrix.csv"
OUTPUT_JSON_PATH = CATALOG_DIR / "actual_support_matrix.json"
OUTPUT_MANIFEST_PATH = CATALOG_DIR / "runtime_catalog_manifest.json"

PRIMARY_REQUEST_ENTRYPOINT = {
    "ArduPilot": "all.xml",
    "PX4": "development.xml",
}

STATIC_MESSAGES_EVIDENCE = "benchmark/mavlink_catalog/messages_and_fields.json"
CSV_COLUMNS = [
    "row_scope",
    "capture_id",
    "system",
    "vehicle",
    "profile",
    "firmware_commit",
    "mavlink_commit",
    "message_id",
    "message_name",
    "origin_xml",
    "catalog_dialect_entrypoints",
    "catalog_definition_status",
    "request_dialect_definition_status",
    "request_sweep_membership_status",
    "static_supported_evidence_status",
    "static_direction_evidence_status",
    "static_requestable_evidence_status",
    "static_tx_evidence_count",
    "static_rx_or_handler_evidence_count",
    "baseline_observed",
    "baseline_count",
    "parameter_phase_count",
    "request_phase_count",
    "other_phase_count",
    "total_observed_count",
    "first_host_monotonic_ns",
    "last_host_monotonic_ns",
    "request_attempted",
    "requested_window_observed",
    "request_matching_frame_count",
    "request_ack_result",
    "request_ack_interpretation",
    "request_classification",
    "runtime_observation_class",
    "zero_baseline_interpretation",
    "support_inference",
    "static_definition_evidence",
    "runtime_observation_evidence",
    "request_evidence",
    "interpretation_limit",
]


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"), parse_constant=reject_json_constant
    )


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def integer(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not an integer: {value!r}") from exc


def optional_integer(value: Any, label: str) -> int | None:
    if value in (None, ""):
        return None
    return integer(value, label)


def static_direction(
    reference_status: str, tx_count: int, rx_count: int
) -> str:
    if tx_count and rx_count:
        return "TX_AND_RX_OR_HANDLER_REFERENCES"
    if tx_count:
        return "TX_REFERENCES_ONLY"
    if rx_count:
        return "RX_OR_HANDLER_REFERENCES_ONLY"
    if reference_status == "STATIC_REFERENCE_FOUND":
        return "OTHER_STATIC_REFERENCES_ONLY"
    return "NO_TX_OR_RX_REFERENCE_FOUND_BY_HEURISTIC_SCAN"


def ack_interpretation(result: str, attempted: bool) -> str:
    if not attempted:
        return "NOT_REQUESTED_NO_ACK_INTERPRETATION"
    if not result:
        return "NO_ACK_OBSERVED_NOT_UNSUPPORTED_EVIDENCE"
    if result == "MAV_RESULT_ACCEPTED":
        return "ACCEPTED_ACK_ONLY_MESSAGE_CAUSALITY_REQUIRES_WINDOW_EVIDENCE"
    if result == "MAV_RESULT_UNSUPPORTED":
        return "EXPLICIT_UNSUPPORTED_ACK_FOR_THIS_PROFILE_REQUEST_CONTEXT_ONLY"
    if result == "MAV_RESULT_DENIED":
        return "DENIED_RESULT_ONLY_NOT_UNSUPPORTED_EVIDENCE"
    if result == "MAV_RESULT_FAILED":
        return "FAILED_RESULT_ONLY_NOT_UNSUPPORTED_EVIDENCE"
    return "ACK_RESULT_RECORDED_WITHOUT_GLOBAL_SUPPORT_INFERENCE"


def count_by_phase(inventory_row: dict[str, Any]) -> dict[str, int]:
    raw = inventory_row.get("count_by_phase") or inventory_row.get("phase_counts") or {}
    return {str(name): integer(count, f"phase count {name}") for name, count in raw.items()}


def inventory_total(inventory_row: dict[str, Any]) -> int:
    return integer(
        inventory_row.get("count_total", inventory_row.get("count", 0)),
        "inventory total",
    )


def build_static_catalog(
    document: dict[str, Any],
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, dict[str, Any]]]:
    by_system: dict[str, dict[int, dict[str, Any]]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for system_doc in document["systems"]:
        system = system_doc["system"]
        require(system not in by_system, f"duplicate static system: {system}")
        messages: dict[int, dict[str, Any]] = {}
        names: set[str] = set()
        for message in system_doc["messages"]:
            message_id = integer(message["message_id"], "static message_id")
            require(message_id not in messages, f"duplicate {system} message ID {message_id}")
            require(message["name"] not in names, f"duplicate {system} message name {message['name']}")
            messages[message_id] = message
            names.add(message["name"])
        primary = PRIMARY_REQUEST_ENTRYPOINT[system]
        system_entrypoints = {
            item["file"] if isinstance(item, dict) else str(item)
            for item in system_doc["dialect_entrypoints"]
        }
        require(
            primary in system_entrypoints,
            f"{system} primary request entrypoint {primary} absent from static catalog",
        )
        by_system[system] = messages
        metadata[system] = system_doc
    require(set(by_system) == set(PRIMARY_REQUEST_ENTRYPOINT), "unexpected static systems")
    return by_system, metadata


def build_static_support() -> dict[tuple[str, int], dict[str, str]]:
    fieldnames, rows = read_csv(STATIC_SUPPORT_PATH)
    required = {
        "system",
        "entity_kind",
        "entity_id",
        "static_source_reference_status",
        "static_tx_evidence_count",
        "static_rx_or_handler_evidence_count",
    }
    require("row_scope" not in fieldnames, "static support matrix is a runtime overlay")
    require(required <= set(fieldnames), "static support matrix lacks required columns")
    index: dict[tuple[str, int], dict[str, str]] = {}
    for row in rows:
        if row["entity_kind"] != "message":
            continue
        key = (row["system"], integer(row["entity_id"], "static support entity_id"))
        require(key not in index, f"duplicate static support message row: {key}")
        index[key] = row
    return index


def primary_row(
    source: dict[str, Any],
    capture: dict[str, Any],
    message: dict[str, Any],
) -> dict[str, Any]:
    message_id = integer(message["message_id"], "message_id")
    entrypoints = list(message["dialect_entrypoints"])
    primary_entrypoint = PRIMARY_REQUEST_ENTRYPOINT[capture["system"]]
    request_dialect_defined = primary_entrypoint in entrypoints

    tx_count = integer(source["static_tx_evidence_count"], "static tx count")
    rx_count = integer(source["static_rx_evidence_count"], "static rx count")
    reference_status = source["static_reference_status"]
    require(
        reference_status
        in {"STATIC_REFERENCE_FOUND", "NO_REFERENCE_FOUND_BY_HEURISTIC_SCAN"},
        f"unexpected static reference status: {reference_status}",
    )

    baseline_count = integer(source["baseline_count"], "baseline_count")
    parameter_count = integer(source["parameter_phase_count"], "parameter_phase_count")
    request_count = integer(source["request_phase_count"], "request_phase_count")
    total_count = integer(source["total_observed_count"], "total_observed_count")
    other_count = total_count - baseline_count - parameter_count - request_count
    require(other_count >= 0, f"negative other-phase count for {capture['capture_id']}:{message_id}")

    request_attempted = bool(source["request_attempted"])
    matching_count = integer(
        source["request_matching_frame_count"], "request_matching_frame_count"
    )
    ack_result = str(source.get("request_ack_result") or "")
    if request_attempted:
        sweep_membership = "REQUEST_ATTEMPTED"
    elif request_dialect_defined:
        sweep_membership = "DEFINED_IN_REQUEST_DIALECT_BUT_NOT_ATTEMPTED"
    else:
        sweep_membership = "AUXILIARY_DIALECT_NOT_IN_REQUEST_SWEEP"

    return {
        "row_scope": "PROFILE_STATIC_MESSAGE_DEFINITION",
        "capture_id": capture["capture_id"],
        "system": capture["system"],
        "vehicle": capture["vehicle"],
        "profile": capture["profile"],
        "firmware_commit": capture["firmware_commit"],
        "mavlink_commit": capture["mavlink_commit"],
        "message_id": message_id,
        "message_name": message["name"],
        "origin_xml": message["origin_xml"],
        "catalog_dialect_entrypoints": "|".join(entrypoints),
        "catalog_definition_status": "DEFINED_IN_STATIC_ENTRYPOINT_CLOSURE",
        "request_dialect_definition_status": (
            "DEFINED_IN_PRIMARY_REQUEST_DIALECT"
            if request_dialect_defined
            else "DEFINED_ONLY_IN_AUXILIARY_DIALECT"
        ),
        "request_sweep_membership_status": sweep_membership,
        "static_supported_evidence_status": reference_status,
        "static_direction_evidence_status": static_direction(
            reference_status, tx_count, rx_count
        ),
        "static_requestable_evidence_status": (
            "UNKNOWN_NO_EXPLICIT_REQUESTABILITY_FIELD_IN_STATIC_CATALOG"
        ),
        "static_tx_evidence_count": tx_count,
        "static_rx_or_handler_evidence_count": rx_count,
        "baseline_observed": baseline_count > 0,
        "baseline_count": baseline_count,
        "parameter_phase_count": parameter_count,
        "request_phase_count": request_count,
        "other_phase_count": other_count,
        "total_observed_count": total_count,
        "first_host_monotonic_ns": optional_integer(
            source.get("first_host_monotonic_ns"), "first_host_monotonic_ns"
        ),
        "last_host_monotonic_ns": optional_integer(
            source.get("last_host_monotonic_ns"), "last_host_monotonic_ns"
        ),
        "request_attempted": request_attempted,
        "requested_window_observed": matching_count > 0,
        "request_matching_frame_count": matching_count,
        "request_ack_result": ack_result,
        "request_ack_interpretation": ack_interpretation(
            ack_result, request_attempted
        ),
        "request_classification": str(source.get("request_classification") or ""),
        "runtime_observation_class": source["runtime_support_class"],
        "zero_baseline_interpretation": (
            "OBSERVED_IN_THIS_PROFILE_BASELINE"
            if baseline_count > 0
            else "NOT_OBSERVED_IN_BASELINE_NOT_UNSUPPORTED_EVIDENCE"
        ),
        "support_inference": "NO_GLOBAL_SUPPORT_OR_UNSUPPORTED_INFERENCE",
        "static_definition_evidence": STATIC_MESSAGES_EVIDENCE,
        "runtime_observation_evidence": source["observation_evidence"],
        "request_evidence": source["request_evidence"],
        "interpretation_limit": source["interpretation_limit"],
    }


def supplemental_runtime_rows(
    captures: list[dict[str, Any]],
    static_by_system: dict[str, dict[int, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[Path]]:
    rows: list[dict[str, Any]] = []
    inventory_paths: list[Path] = []
    for capture in captures:
        path = workspace_path(capture["message_summary"]["path"])
        inventory_paths.append(path)
        document = read_json(path)
        for inventory in document.get("messages", []):
            raw_id = inventory.get("message_id")
            message_id = optional_integer(raw_id, "inventory message_id")
            message_name = str(inventory.get("message_name") or "")
            static_message = static_by_system[capture["system"]].get(message_id)
            if static_message is not None and static_message["name"] == message_name:
                continue

            phases = count_by_phase(inventory)
            baseline_count = phases.get("BASELINE", 0)
            parameter_count = phases.get("PARAMETER_DOWNLOAD", 0)
            request_count = phases.get("REQUEST_SWEEP", 0)
            total_count = inventory_total(inventory)
            other_count = total_count - baseline_count - parameter_count - request_count
            require(
                other_count >= 0,
                f"negative supplemental other count for {capture['capture_id']}:{message_id}",
            )
            if message_id == -1 and message_name == "BAD_DATA":
                observation_class = "DECODE_PARSER_BAD_DATA_NOT_A_MAVLINK_MESSAGE"
            elif static_message is not None:
                observation_class = "RUNTIME_MESSAGE_NAME_DIFFERS_FROM_STATIC_CATALOG"
            else:
                observation_class = "RUNTIME_ID_NOT_DEFINED_IN_STATIC_CATALOG"

            rows.append({
                "row_scope": "RUNTIME_NON_CATALOG_OBSERVATION",
                "capture_id": capture["capture_id"],
                "system": capture["system"],
                "vehicle": capture["vehicle"],
                "profile": capture["profile"],
                "firmware_commit": capture["firmware_commit"],
                "mavlink_commit": capture["mavlink_commit"],
                "message_id": message_id,
                "message_name": message_name,
                "origin_xml": "",
                "catalog_dialect_entrypoints": "",
                "catalog_definition_status": "NOT_DEFINED_IN_STATIC_CATALOG",
                "request_dialect_definition_status": (
                    "NOT_APPLICABLE_NON_CATALOG_OBSERVATION"
                ),
                "request_sweep_membership_status": (
                    "NOT_APPLICABLE_NON_CATALOG_OBSERVATION"
                ),
                "static_supported_evidence_status": "NOT_APPLICABLE",
                "static_direction_evidence_status": "NOT_APPLICABLE",
                "static_requestable_evidence_status": "NOT_APPLICABLE",
                "static_tx_evidence_count": 0,
                "static_rx_or_handler_evidence_count": 0,
                "baseline_observed": baseline_count > 0,
                "baseline_count": baseline_count,
                "parameter_phase_count": parameter_count,
                "request_phase_count": request_count,
                "other_phase_count": other_count,
                "total_observed_count": total_count,
                "first_host_monotonic_ns": optional_integer(
                    inventory.get("first_host_monotonic_ns"),
                    "supplemental first_host_monotonic_ns",
                ),
                "last_host_monotonic_ns": optional_integer(
                    inventory.get("last_host_monotonic_ns"),
                    "supplemental last_host_monotonic_ns",
                ),
                "request_attempted": False,
                "requested_window_observed": False,
                "request_matching_frame_count": 0,
                "request_ack_result": "",
                "request_ack_interpretation": (
                    "NOT_APPLICABLE_NON_CATALOG_OBSERVATION"
                ),
                "request_classification": "",
                "runtime_observation_class": observation_class,
                "zero_baseline_interpretation": (
                    "OBSERVED_IN_THIS_PROFILE_BASELINE"
                    if baseline_count > 0
                    else "NOT_OBSERVED_IN_BASELINE_NOT_UNSUPPORTED_EVIDENCE"
                ),
                "support_inference": "NOT_A_STATIC_MESSAGE_SUPPORT_ROW",
                "static_definition_evidence": STATIC_MESSAGES_EVIDENCE,
                "runtime_observation_evidence": capture["message_summary"]["path"],
                "request_evidence": "",
                "interpretation_limit": (
                    "Preserved because it occurred in the runtime inventory, but it is not "
                    "a static MAVLink message definition and carries no message-support inference."
                ),
            })
    return rows, inventory_paths


def counter_dict(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def profile_summary(
    capture: dict[str, Any], primary: list[dict[str, Any]], supplemental: list[dict[str, Any]]
) -> dict[str, Any]:
    ack_labels = [
        row["request_ack_result"]
        or ("NO_ACK_OBSERVED" if row["request_attempted"] else "NOT_ATTEMPTED")
        for row in primary
    ]
    attempted = sum(row["request_attempted"] for row in primary)
    require(
        attempted == integer(capture["request_sweep"]["attempted"], "capture sweep attempted"),
        f"request-attempt count mismatch for {capture['capture_id']}",
    )
    baseline_distinct = sum(row["baseline_observed"] for row in primary)
    require(
        baseline_distinct
        == integer(
            capture["message_summary"]["baseline_distinct_message_count"],
            "capture baseline distinct",
        ),
        f"baseline distinct mismatch for {capture['capture_id']}",
    )
    observed_primary = sum(row["total_observed_count"] > 0 for row in primary)
    require(
        observed_primary + len(supplemental)
        == integer(
            capture["message_summary"]["distinct_message_count"],
            "capture distinct message count",
        ),
        f"distinct inventory mismatch for {capture['capture_id']}",
    )
    require(
        sum(row["total_observed_count"] for row in primary + supplemental)
        == integer(
            capture["message_summary"]["total_message_count"],
            "capture total message count",
        ),
        f"total inventory mismatch for {capture['capture_id']}",
    )
    return {
        "capture_id": capture["capture_id"],
        "system": capture["system"],
        "vehicle": capture["vehicle"],
        "profile": capture["profile"],
        "runtime_status": capture["runtime_status"],
        "static_definition_rows": len(primary),
        "supplemental_non_catalog_rows": len(supplemental),
        "baseline_observed_rows": baseline_distinct,
        "requested_window_observed_rows": sum(
            row["requested_window_observed"] for row in primary
        ),
        "total_observed_static_definition_rows": observed_primary,
        "request_attempted_rows": attempted,
        "catalog_definition_status_counts": counter_dict(
            row["catalog_definition_status"] for row in primary
        ),
        "request_dialect_definition_status_counts": counter_dict(
            row["request_dialect_definition_status"] for row in primary
        ),
        "request_sweep_membership_status_counts": counter_dict(
            row["request_sweep_membership_status"] for row in primary
        ),
        "static_supported_evidence_status_counts": counter_dict(
            row["static_supported_evidence_status"] for row in primary
        ),
        "static_direction_evidence_status_counts": counter_dict(
            row["static_direction_evidence_status"] for row in primary
        ),
        "static_requestable_evidence_status_counts": counter_dict(
            row["static_requestable_evidence_status"] for row in primary
        ),
        "request_ack_result_counts": counter_dict(ack_labels),
        "runtime_observation_class_counts": counter_dict(
            row["runtime_observation_class"] for row in primary
        ),
    }


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def render_csv(rows: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream, fieldnames=CSV_COLUMNS, extrasaction="raise", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        require(set(row) == set(CSV_COLUMNS), "row columns differ from CSV schema")
        writer.writerow({column: csv_value(row[column]) for column in CSV_COLUMNS})
    return stream.getvalue().encode("utf-8")


def render_json(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def build() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    static_doc = read_json(STATIC_MESSAGES_PATH)
    static_manifest = read_json(STATIC_MANIFEST_PATH)
    static_support_index = build_static_support()
    runtime_evidence = read_json(RUNTIME_EVIDENCE_PATH)
    runtime_matrix = read_json(RUNTIME_MATRIX_PATH)
    static_by_system, static_metadata = build_static_catalog(static_doc)
    expected_static_support_keys = {
        (system, message_id)
        for system, messages in static_by_system.items()
        for message_id in messages
    }
    require(
        set(static_support_index) == expected_static_support_keys,
        "static support message coverage differs from static message catalog",
    )

    require(
        static_manifest["output_sha256"].get(STATIC_MESSAGES_PATH.name)
        == sha256(STATIC_MESSAGES_PATH),
        "static manifest message-catalog hash mismatch",
    )
    require(
        static_manifest["output_sha256"].get(STATIC_SUPPORT_PATH.name)
        == sha256(STATIC_SUPPORT_PATH),
        "static manifest support-matrix hash mismatch",
    )
    require(
        "actual_support_matrix.csv" not in static_manifest["output_sha256"],
        "static manifest must not claim the runtime overlay as a static output",
    )
    runtime_static_source = runtime_matrix.get("static_support_source") or {}
    require(
        runtime_static_source.get("path") == relative(STATIC_SUPPORT_PATH),
        "runtime matrix does not identify static_support_matrix.csv",
    )
    require(
        runtime_static_source.get("sha256") == sha256(STATIC_SUPPORT_PATH),
        "runtime matrix static-support input hash mismatch",
    )

    captures = list(runtime_evidence["captures"])
    capture_by_id = {capture["capture_id"]: capture for capture in captures}
    require(len(capture_by_id) == len(captures), "duplicate runtime capture_id")
    require(
        runtime_evidence["implementation_satisfaction"] == "NOT_ASSESSED",
        "runtime evidence unexpectedly assesses implementation satisfaction",
    )
    for capture in captures:
        system_doc = static_metadata[capture["system"]]
        require(
            capture["firmware_commit"] == system_doc["sut_commit"],
            f"firmware commit mismatch for {capture['capture_id']}",
        )
        require(
            capture["mavlink_commit"] == system_doc["mavlink_commit"],
            f"MAVLink commit mismatch for {capture['capture_id']}",
        )

    source_rows = runtime_matrix["rows"]
    source_index: dict[tuple[str, int], dict[str, Any]] = {}
    static_evidence_signatures: dict[tuple[str, int], tuple[Any, ...]] = {}
    for source in source_rows:
        key = (source["capture_id"], integer(source["message_id"], "source message_id"))
        require(key not in source_index, f"duplicate runtime matrix row: {key}")
        require(source["capture_id"] in capture_by_id, f"unknown capture in runtime matrix: {key}")
        source_index[key] = source
        evidence_key = (source["system"], key[1])
        signature = (
            source["static_reference_status"],
            integer(source["static_tx_evidence_count"], "static tx signature"),
            integer(source["static_rx_evidence_count"], "static rx signature"),
        )
        previous = static_evidence_signatures.setdefault(evidence_key, signature)
        require(
            previous == signature,
            f"static evidence differs across profiles for {evidence_key}",
        )
        static_support = static_support_index.get(evidence_key)
        require(static_support is not None, f"static support row missing for {evidence_key}")
        static_signature = (
            static_support["static_source_reference_status"],
            integer(static_support["static_tx_evidence_count"], "direct static tx"),
            integer(
                static_support["static_rx_or_handler_evidence_count"],
                "direct static rx",
            ),
        )
        require(
            signature == static_signature,
            f"runtime matrix static evidence drift for {evidence_key}",
        )

    expected_keys = {
        (capture["capture_id"], message_id)
        for capture in captures
        for message_id in static_by_system[capture["system"]]
    }
    require(
        set(source_index) == expected_keys,
        f"runtime matrix Cartesian coverage mismatch: missing={len(expected_keys-set(source_index))} "
        f"extra={len(set(source_index)-expected_keys)}",
    )

    primary_rows: list[dict[str, Any]] = []
    for capture in captures:
        system = capture["system"]
        for message_id, message in static_by_system[system].items():
            source = source_index[(capture["capture_id"], message_id)]
            require(source["system"] == system, "runtime matrix system mismatch")
            require(source["vehicle"] == capture["vehicle"], "runtime matrix vehicle mismatch")
            require(source["profile"] == capture["profile"], "runtime matrix profile mismatch")
            require(source["message_name"] == message["name"], "message name mismatch")
            require(source["origin_xml"] == message["origin_xml"], "origin XML mismatch")
            require(
                source["dialect_entrypoints"] == "|".join(message["dialect_entrypoints"]),
                "dialect entrypoint mismatch",
            )
            primary_rows.append(primary_row(source, capture, message))

    supplemental_rows, inventory_paths = supplemental_runtime_rows(
        captures, static_by_system
    )
    all_rows = primary_rows + supplemental_rows
    all_rows.sort(
        key=lambda row: (
            row["system"],
            row["vehicle"],
            row["profile"],
            0 if row["row_scope"] == "PROFILE_STATIC_MESSAGE_DEFINITION" else 1,
            -1 if row["message_id"] is None else int(row["message_id"]),
            row["message_name"],
        )
    )

    summaries = []
    for capture in sorted(
        captures,
        key=lambda item: (item["system"], item["vehicle"], item["profile"]),
    ):
        capture_primary = [
            row for row in primary_rows if row["capture_id"] == capture["capture_id"]
        ]
        capture_supplemental = [
            row for row in supplemental_rows if row["capture_id"] == capture["capture_id"]
        ]
        summaries.append(profile_summary(capture, capture_primary, capture_supplemental))

    input_paths = [
        (STATIC_MANIFEST_PATH, "Frozen static catalog manifest"),
        (STATIC_MESSAGES_PATH, "Frozen static MAVLink message definitions"),
        (STATIC_SUPPORT_PATH, "Frozen heuristic static support evidence"),
        (RUNTIME_EVIDENCE_PATH, "Merged selected runtime captures"),
        (RUNTIME_MATRIX_PATH, "Merged profile/message runtime observations and static evidence"),
    ]
    input_paths.extend(
        (path, "Per-profile runtime message inventory used to retain non-catalog observations")
        for path in sorted(set(inventory_paths))
    )
    inputs = [
        {"path": relative(path), "sha256": sha256(path), "role": role}
        for path, role in input_paths
    ]

    document = {
        "schema_version": "1.0",
        "generation_deterministic": True,
        "primary_grain": "one selected firmware profile x one frozen static MAVLink message definition",
        "profile_count": len(captures),
        "primary_static_definition_row_count": len(primary_rows),
        "supplemental_non_catalog_observation_row_count": len(supplemental_rows),
        "total_row_count": len(all_rows),
        "implementation_satisfaction": "NOT_ASSESSED",
        "inputs": inputs,
        "semantics": {
            "dialect_defined": (
                "XML entrypoint-closure membership only; primary request dialect and auxiliary-only definitions remain separate."
            ),
            "static_supported": (
                "Exact heuristic reference status from the merged static evidence; neither presence nor absence is a support proof."
            ),
            "static_direction": (
                "Mechanical grouping of existing TX and RX/handler reference counts; it is not path reachability."
            ),
            "static_requestable": (
                "UNKNOWN for every static definition because the existing static catalog has no explicit requestability field."
            ),
            "baseline_observed": (
                "Observed in this selected default SITL profile only; zero is not unsupported evidence."
            ),
            "requested_window_observed": (
                "A matching frame occurred in the sequential request window; periodic baseline traffic can make causality ambiguous."
            ),
            "request_ack": (
                "Exact ACK result only. DENIED and FAILED are not rewritten as UNSUPPORTED; ACK 512 lacks the requested message ID."
            ),
            "support_inference": "No global support/conformance boolean is produced.",
        },
        "profile_summaries": summaries,
        "rows": all_rows,
    }
    check_summary = {
        "status": "PASS",
        "profiles": len(captures),
        "primary_rows": len(primary_rows),
        "supplemental_rows": len(supplemental_rows),
        "total_rows": len(all_rows),
        "row_scope_counts": counter_dict(row["row_scope"] for row in all_rows),
        "catalog_definition_status_counts": counter_dict(
            row["catalog_definition_status"] for row in all_rows
        ),
        "request_dialect_definition_status_counts": counter_dict(
            row["request_dialect_definition_status"] for row in primary_rows
        ),
        "request_sweep_membership_status_counts": counter_dict(
            row["request_sweep_membership_status"] for row in primary_rows
        ),
        "static_supported_evidence_status_counts": counter_dict(
            row["static_supported_evidence_status"] for row in primary_rows
        ),
        "static_direction_evidence_status_counts": counter_dict(
            row["static_direction_evidence_status"] for row in primary_rows
        ),
        "request_ack_result_counts": counter_dict(
            row["request_ack_result"]
            or ("NO_ACK_OBSERVED" if row["request_attempted"] else "NOT_ATTEMPTED")
            for row in primary_rows
        ),
        "runtime_observation_class_counts": counter_dict(
            row["runtime_observation_class"] for row in primary_rows
        ),
    }
    return document, all_rows, check_summary


def build_runtime_manifest(
    document: dict[str, Any],
    summary: dict[str, Any],
    csv_bytes: bytes,
    json_bytes: bytes,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generation_deterministic": True,
        "generator": {
            "path": relative(Path(__file__)),
            "sha256": sha256(Path(__file__)),
        },
        "inputs": document["inputs"],
        "outputs": {
            relative(OUTPUT_CSV_PATH): {
                "sha256": sha256_bytes(csv_bytes),
                "data_rows": document["total_row_count"],
            },
            relative(OUTPUT_JSON_PATH): {
                "sha256": sha256_bytes(json_bytes),
                "data_rows": document["total_row_count"],
            },
        },
        "profile_count": document["profile_count"],
        "primary_static_definition_row_count": document[
            "primary_static_definition_row_count"
        ],
        "supplemental_non_catalog_observation_row_count": document[
            "supplemental_non_catalog_observation_row_count"
        ],
        "total_row_count": document["total_row_count"],
        "implementation_satisfaction": document["implementation_satisfaction"],
        "status_distributions": {
            key: value
            for key, value in summary.items()
            if key.endswith("_counts")
        },
        "validation_command": (
            "python3 -B benchmark/scripts/apply_runtime_catalog.py --check"
        ),
    }


def write_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Rebuild in memory and verify existing CSV/JSON/manifest bytes without writing.",
    )
    args = parser.parse_args()

    try:
        document, rows, summary = build()
        expected_csv = render_csv(rows)
        expected_json = render_json(document)
        expected_manifest = render_json(
            build_runtime_manifest(document, summary, expected_csv, expected_json)
        )
        if args.check:
            mismatches = []
            for path, expected in [
                (OUTPUT_CSV_PATH, expected_csv),
                (OUTPUT_JSON_PATH, expected_json),
                (OUTPUT_MANIFEST_PATH, expected_manifest),
            ]:
                if not path.is_file():
                    mismatches.append(f"missing {relative(path)}")
                elif path.read_bytes() != expected:
                    mismatches.append(f"content differs: {relative(path)}")
            if mismatches:
                summary["status"] = "FAIL"
                summary["output_mismatches"] = mismatches
                print(json.dumps(summary, indent=2, sort_keys=True))
                return 1
        else:
            write_atomic(OUTPUT_CSV_PATH, expected_csv)
            write_atomic(OUTPUT_JSON_PATH, expected_json)
            write_atomic(OUTPUT_MANIFEST_PATH, expected_manifest)
            summary["output_csv"] = relative(OUTPUT_CSV_PATH)
            summary["output_csv_sha256"] = sha256(OUTPUT_CSV_PATH)
            summary["output_json"] = relative(OUTPUT_JSON_PATH)
            summary["output_json_sha256"] = sha256(OUTPUT_JSON_PATH)
            summary["output_manifest"] = relative(OUTPUT_MANIFEST_PATH)
            summary["output_manifest_sha256"] = sha256(OUTPUT_MANIFEST_PATH)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(f"apply_runtime_catalog: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
