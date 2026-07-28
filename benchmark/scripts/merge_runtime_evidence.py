#!/usr/bin/env python3
"""Merge per-profile Milestone-6 captures and build runtime support tables."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
M6 = BENCHMARK / "extraction_runs" / "milestone6"
CATALOG = BENCHMARK / "mavlink_catalog"
STATIC_SUPPORT_MATRIX = CATALOG / "static_support_matrix.csv"
LEGACY_SUPPORT_MATRIX = CATALOG / "actual_support_matrix.csv"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def manifest_candidates(explicit: list[Path]) -> list[Path]:
    if explicit:
        return sorted(path if path.is_absolute() else ROOT / path for path in explicit)
    return sorted({*M6.glob("ArduPilot/**/manifest.json"), *M6.glob("PX4/**/manifest.json")})


def capture_score(capture: dict[str, Any]) -> tuple[int, int, int, int]:
    status = {"FAILED": 0, "PARTIAL": 1, "COMPLETE": 2}.get(capture["runtime_status"], -1)
    return (
        status,
        int(capture["parameter_snapshot"].get("unique_parameter_count") or 0),
        int(capture["message_summary"].get("baseline_distinct_message_count") or 0),
        int(capture["request_sweep"].get("attempted") or 0),
    )


def normalized_property_rows(doc: dict[str, Any], capture_id: str) -> list[dict[str, Any]]:
    rows = []
    for raw in doc.get("property_parameters", []):
        if raw.get("capture_id") != capture_id or raw.get("value") is None:
            continue
        parameter_id = raw.get("runtime_parameter_name") or raw.get("parameter_id")
        value = raw["value"]
        status = raw.get("status", "RUNTIME_OBSERVED")
        if parameter_id == "TKOFF_TIMEOUT" and float(value) == 0:
            status = "RUNTIME_OBSERVED_DISABLED_DOMAIN"
        if parameter_id == "BATT_LOW_TIMER" and float(value) <= 0:
            status = "RUNTIME_OBSERVED_DISABLED_DOMAIN"
        rows.append({
            "property_id": raw["property_id"],
            "parameter_id": parameter_id,
            "capture_id": capture_id,
            "value": value,
            "unit": raw["unit"],
            "source_path": raw["source_path"],
            "source_sha256": raw["source_sha256"],
            "source_param_index": int(raw["source_param_index"]),
            "source_param_count": int(raw["source_param_count"]),
            "status": status,
        })
    return rows


def normalize_capture(raw: dict[str, Any], manifest_path: Path, doc: dict[str, Any]) -> dict[str, Any]:
    """Convert the richer ArduPilot manifest shape to the common evidence schema."""
    required = {
        "capture_id", "system", "vehicle", "profile", "firmware_commit", "mavlink_commit",
        "runtime_status", "launch_command", "connection", "phases", "parameter_snapshot",
        "message_summary", "request_sweep", "clock_domains", "process_cleanup", "artifacts", "limitations",
    }
    if raw["system"] == "PX4" and required <= set(raw):
        return {key: raw[key] for key in required}

    vehicle_dir = {"ArduCopter": "Copter", "ArduPlane": "Plane", "Rover": "Rover"}[raw["vehicle"]]
    run_dir = manifest_path.parent / "runs" / vehicle_dir
    params_path = run_dir / "parameters.json"
    inventory_path = run_dir / "message_summary.json"
    sweep_path = run_dir / "request_sweep.json"
    params = read_json(params_path)
    by_name = {item["name"]: item for item in params.get("parameters", [])}
    selected_names = {
        row.get("runtime_parameter_name") or row.get("parameter_id")
        for row in doc.get("property_parameters", [])
        if row.get("capture_id") == raw["capture_id"]
    }
    required_path = run_dir / "required_parameters.json"
    if required_path.is_file():
        required_doc = read_json(required_path)
        selected_names.update(
            item["name"] for item in required_doc.get("required_and_exception_parameters", [])
            if item.get("record") is not None
        )
        selected_names.update(
            item["name"] for item in required_doc.get("all_detected_battery_instance_parameters", [])
        )
    key_values = []
    for name in sorted(selected_names):
        item = by_name.get(name)
        if item is None:
            continue
        key_values.append({
            "name": name,
            "wire_value": item["wire_value"],
            "decoded_value": item["decoded_value"],
            "param_type": item["param_type"],
            "param_index": item["param_index"],
            "param_count": item["param_count"],
            "source_system": item["source_system"],
            "source_component": item["source_component"],
            "received_host_monotonic_ns": item["received_host_monotonic_ns"],
        })
    inventory = read_json(inventory_path)
    sweep = read_json(sweep_path) if sweep_path.is_file() else {}
    phase_map = {
        "STARTUP": "OTHER",
        "BASELINE": "BASELINE",
        "PARAMETER_DOWNLOAD": "PARAMETER_DOWNLOAD",
        "REQUEST_SWEEP": "REQUEST_SWEEP",
        "RELEVANT_STREAM_SAMPLE": "OTHER",
    }
    phases = [{
        "name": phase_map.get(phase["name"], "OTHER"),
        "start_host_monotonic_ns": phase["start_host_monotonic_ns"],
        "end_host_monotonic_ns": phase["end_host_monotonic_ns"],
        "traffic_origin": phase.get("traffic_origin", ""),
        "notes": phase.get("notes", ""),
    } for phase in raw.get("phases", [])]
    artifact_rows = []
    common_names = {"collect_runtime.py", "dialect_generated.py", "preflight.json", "postflight.json", "README.md"}
    for item in doc.get("artifact_inventory", []):
        path = Path(item["path"])
        if f"runs/{vehicle_dir}/" in item["path"] or path.name in common_names:
            artifact_rows.append({"path": item["path"], "sha256": item["sha256"], "role": item["role"]})
    cleanup = raw.get("process_cleanup", {})
    return {
        "capture_id": raw["capture_id"],
        "system": raw["system"],
        "vehicle": raw["vehicle"],
        "profile": raw["profile"],
        "firmware_commit": raw["firmware_commit"],
        "mavlink_commit": raw["mavlink_commit"],
        "runtime_status": raw["runtime_status"],
        "launch_command": raw["launch_command"],
        "connection": raw["connection"],
        "phases": phases,
        "parameter_snapshot": {
            "status": params.get("status", "FAILED"),
            "protocol": "PARAM" if params.get("protocol") in {None, "PARAM", "PARAM_REQUEST_LIST/PARAM_VALUE"} else params["protocol"],
            "path": rel(params_path),
            "sha256": sha256(params_path),
            "expected_count": params.get("expected_count"),
            "received_count": int(params.get("received_response_count") or 0),
            "unique_parameter_count": int(params.get("unique_parameter_count") or 0),
            "missing_indices": params.get("missing_indices") or [],
            "key_values": key_values,
        },
        "message_summary": {
            "path": rel(inventory_path),
            "sha256": sha256(inventory_path),
            "total_message_count": int(inventory.get("total_message_count") or 0),
            "distinct_message_count": int(inventory.get("distinct_message_key_count") or 0),
            "baseline_distinct_message_count": int(inventory.get("baseline_distinct_message_key_count") or 0),
            "host_clock": "CLOCK_MONOTONIC_NS",
        },
        "request_sweep": {
            "status": sweep.get("status", "NOT_RUN"),
            "path": rel(sweep_path) if sweep_path.is_file() else None,
            "sha256": sha256(sweep_path) if sweep_path.is_file() else None,
            "attempted": int(sweep.get("attempted") or 0),
            "message_observed": int(sweep.get("message_observed") or 0),
            "unsupported": int(sweep.get("unsupported") or 0),
            "no_response": int(sweep.get("no_response") or 0),
        },
        "clock_domains": ["CLOCK_MONOTONIC_NS", "HOST_UTC_WALL_FOR_TLOG_ONLY", "ARDUPILOT_BOOT_OR_PROTOCOL_SPECIFIC_ONBOARD_FIELDS_AS_NAMED"],
        "process_cleanup": json.dumps(cleanup, ensure_ascii=False, sort_keys=True),
        "artifacts": artifact_rows,
        "limitations": raw.get("limitations", []),
    }


def select_captures(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    candidates: dict[tuple[str, str], list[tuple[dict[str, Any], Path, dict[str, Any]]]] = defaultdict(list)
    for path in paths:
        doc = read_json(path)
        for raw_capture in doc.get("captures", []):
            capture = normalize_capture(raw_capture, path, doc)
            profile_key = (capture["system"], capture["vehicle"])
            entry = {
                "manifest_path": rel(path),
                "manifest_sha256": sha256(path),
                "capture_id": capture["capture_id"],
                "system": capture["system"],
                "vehicle": capture["vehicle"],
                "runtime_status": capture["runtime_status"],
                "score": list(capture_score(capture)),
                "selected": False,
            }
            attempts.append(entry)
            candidates[profile_key].append((capture, path, doc))
    selected: list[dict[str, Any]] = []
    property_rows: list[dict[str, Any]] = []
    for key, options in sorted(candidates.items()):
        capture, path, doc = max(options, key=lambda item: capture_score(item[0]))
        selected.append(capture)
        selected_id = capture["capture_id"]
        for attempt in attempts:
            if attempt["capture_id"] == selected_id and attempt["manifest_path"] == rel(path):
                attempt["selected"] = True
        property_rows.extend(normalized_property_rows(doc, selected_id))
    return selected, property_rows, attempts


def static_messages() -> tuple[dict[tuple[str, int], dict[str, Any]], list[dict[str, Any]]]:
    doc = read_json(CATALOG / "messages_and_fields.json")
    index: dict[tuple[str, int], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for system in doc["systems"]:
        for message in system["messages"]:
            index[(system["system"], int(message["message_id"]))] = message
            rows.append(message)
    return index, rows


def static_support_path() -> Path:
    """Resolve only a legacy-shaped static matrix, never the runtime overlay."""
    if STATIC_SUPPORT_MATRIX.is_file():
        return STATIC_SUPPORT_MATRIX
    if not LEGACY_SUPPORT_MATRIX.is_file():
        raise FileNotFoundError(
            f"missing static support matrix: {STATIC_SUPPORT_MATRIX}"
        )
    with LEGACY_SUPPORT_MATRIX.open(newline="", encoding="utf-8") as stream:
        fieldnames = csv.DictReader(stream).fieldnames or []
    required = {
        "system",
        "entity_kind",
        "entity_id",
        "static_source_reference_status",
        "static_tx_evidence_count",
        "static_rx_or_handler_evidence_count",
    }
    if "row_scope" in fieldnames or not required <= set(fieldnames):
        raise ValueError(
            "legacy actual_support_matrix.csv is a runtime/profile overlay, not a "
            "static support matrix; run generate_catalog.py first"
        )
    return LEGACY_SUPPORT_MATRIX


def static_support() -> dict[tuple[str, str, int], dict[str, str]]:
    path = static_support_path()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = set(reader.fieldnames or [])
        required = {
            "system",
            "entity_kind",
            "entity_id",
            "static_source_reference_status",
            "static_tx_evidence_count",
            "static_rx_or_handler_evidence_count",
        }
        if "row_scope" in fieldnames or not required <= fieldnames:
            raise ValueError(f"invalid static support matrix columns: {path}")
        rows = list(reader)
    index: dict[tuple[str, str, int], dict[str, str]] = {}
    for row in rows:
        key = (row["system"], row["entity_kind"], int(row["entity_id"]))
        if key in index:
            raise ValueError(f"duplicate static support row {key} in {path}")
        index[key] = row
    return index


def inventory_for(capture: dict[str, Any]) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    doc = read_json(workspace_path(capture["message_summary"]["path"]))
    return doc, {int(row["message_id"]): row for row in doc.get("messages", []) if row.get("message_id") is not None}


def sweep_for(capture: dict[str, Any]) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    path = capture["request_sweep"].get("path")
    if not path:
        return {}, {}
    doc = read_json(workspace_path(path))
    records = doc.get("records") or doc.get("results") or []
    normalized = {}
    for row in records:
        if "matching_frame_count" not in row:
            ack = None
            if row.get("command_ack_received"):
                ack = {
                    "result": row.get("command_ack_result"),
                    "result_name": row.get("command_ack_result_name"),
                    "correlation": "SEQUENTIAL_TEMPORAL_ONLY_COMMAND_ACK_HAS_NO_REQUESTED_MESSAGE_ID",
                }
            row = {
                **row,
                "ack": ack,
                "matching_frame_count": int(bool(row.get("requested_message_observed_in_window"))),
                "classification": row.get("observation_causality", ""),
            }
        normalized[int(row["message_id"])] = row
    return doc, normalized


def runtime_support_class(inventory: dict[str, Any] | None, sweep: dict[str, Any] | None) -> str:
    phases = (inventory or {}).get("count_by_phase") or (inventory or {}).get("phase_counts") or {}
    baseline = int(phases.get("BASELINE", 0))
    if baseline > 0:
        return "DEFAULT_STREAM_OBSERVED"
    matching = int((sweep or {}).get("matching_frame_count") or 0)
    if matching > 0:
        return "REQUEST_WINDOW_MESSAGE_OBSERVED"
    ack = (sweep or {}).get("ack")
    result_name = (ack or {}).get("result_name", "")
    if result_name == "MAV_RESULT_ACCEPTED":
        return "REQUEST_ACK_ACCEPTED_NO_MATCHING_FRAME"
    if result_name:
        return f"REQUEST_ACK_{result_name.removeprefix('MAV_RESULT_')}"
    if sweep is not None:
        return "REQUESTED_NO_ACK_NO_MATCHING_FRAME"
    return "NOT_IN_REQUEST_SWEEP_AND_NOT_OBSERVED"


def build_message_rows(captures: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    static_index, messages = static_messages()
    support_index = static_support()
    rows: list[dict[str, Any]] = []
    time_rows: list[dict[str, Any]] = []
    for capture in captures:
        inventory_doc, inventory = inventory_for(capture)
        sweep_doc, sweep = sweep_for(capture)
        system = capture["system"]
        for message in (item for item in messages if item["system"] == system):
            msgid = int(message["message_id"])
            inv = inventory.get(msgid)
            req = sweep.get(msgid)
            ack = (req or {}).get("ack") or {}
            static = support_index[(system, "message", msgid)]
            rows.append({
                "capture_id": capture["capture_id"],
                "system": system,
                "vehicle": capture["vehicle"],
                "profile": capture["profile"],
                "message_id": msgid,
                "message_name": message["name"],
                "origin_xml": message["origin_xml"],
                "dialect_entrypoints": "|".join(message["dialect_entrypoints"]),
                "static_reference_status": static["static_source_reference_status"],
                "static_tx_evidence_count": static["static_tx_evidence_count"],
                "static_rx_evidence_count": static["static_rx_or_handler_evidence_count"],
                "baseline_count": int(((inv or {}).get("count_by_phase") or (inv or {}).get("phase_counts") or {}).get("BASELINE", 0)),
                "parameter_phase_count": int(((inv or {}).get("count_by_phase") or (inv or {}).get("phase_counts") or {}).get("PARAMETER_DOWNLOAD", 0)),
                "request_phase_count": int(((inv or {}).get("count_by_phase") or (inv or {}).get("phase_counts") or {}).get("REQUEST_SWEEP", 0)),
                "total_observed_count": int((inv or {}).get("count_total", (inv or {}).get("count", 0))),
                "first_host_monotonic_ns": (inv or {}).get("first_host_monotonic_ns", ""),
                "last_host_monotonic_ns": (inv or {}).get("last_host_monotonic_ns", ""),
                "request_attempted": req is not None,
                "request_ack_result": ack.get("result_name", ""),
                "request_matching_frame_count": int((req or {}).get("matching_frame_count", 0)),
                "request_classification": (req or {}).get("classification", ""),
                "runtime_support_class": runtime_support_class(inv, req),
                "observation_evidence": capture["message_summary"]["path"],
                "request_evidence": capture["request_sweep"].get("path") or "",
                "interpretation_limit": "Baseline proves only this default SITL profile. Request-window matches may be conditional and are not causal when the message already streamed by default.",
            })
            if inv:
                observed_times = inv.get("onboard_time_fields") or inv.get("time_fields") or {}
                for field, samples in sorted(observed_times.items()):
                    field_def = next((item for item in message["fields"] if item["name"] == field), None)
                    time_rows.append({
                        "capture_id": capture["capture_id"],
                        "system": system,
                        "vehicle": capture["vehicle"],
                        "message_id": msgid,
                        "message_name": message["name"],
                        "field": field,
                        "xml_units": (field_def or {}).get("units", ""),
                        "xml_description": (field_def or {}).get("description", ""),
                        "first_value": json.dumps(samples.get("first", samples.get("first_value")), ensure_ascii=False),
                        "last_value": json.dumps(samples.get("last", samples.get("last_value")), ensure_ascii=False),
                        "sample_values": json.dumps(samples.get("samples", []), ensure_ascii=False),
                        "first_host_monotonic_ns": inv.get("first_host_monotonic_ns", ""),
                        "last_host_monotonic_ns": inv.get("last_host_monotonic_ns", ""),
                        "host_clock": "CLOCK_MONOTONIC_NS",
                        "clock_warning": "Field clock follows frozen XML semantics; host arrival is a separate observation clock and is not substituted for the field clock.",
                        "evidence": capture["message_summary"]["path"],
                    })
    rows.sort(key=lambda row: (row["system"], row["vehicle"], int(row["message_id"])))
    time_rows.sort(key=lambda row: (row["system"], row["vehicle"], int(row["message_id"]), row["field"]))
    return rows, time_rows


def build_parameter_rows(captures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for capture in captures:
        snapshot = capture["parameter_snapshot"]
        path = workspace_path(snapshot["path"])
        doc = read_json(path)
        parameters = doc.get("parameters") or doc.get("all_parameters") or []
        for item in parameters:
            rows.append({
                "capture_id": capture["capture_id"],
                "system": capture["system"],
                "vehicle": capture["vehicle"],
                "profile": capture["profile"],
                "name": item.get("name") or item.get("param_id"),
                "wire_value": item.get("wire_value", item.get("param_value")),
                "wire_value_float32_hex": item.get("wire_value_float32_hex", ""),
                "decoded_value": item.get("decoded_value", item.get("value")),
                "decode_policy": item.get("decode_policy", ""),
                "param_type": item.get("param_type", ""),
                "param_type_name": item.get("param_type_name", ""),
                "param_index": item.get("param_index", ""),
                "param_count": item.get("param_count", ""),
                "source_system": item.get("source_system", ""),
                "source_component": item.get("source_component", ""),
                "received_host_monotonic_ns": item.get("received_host_monotonic_ns", ""),
                "source_path": rel(path),
                "source_sha256": sha256(path),
                "snapshot_status": snapshot["status"],
                "implementation_satisfaction": "NOT_ASSESSED",
            })
    rows.sort(key=lambda row: (row["system"], row["vehicle"], str(row["name"])))
    return rows


MESSAGE_COLUMNS = [
    "capture_id", "system", "vehicle", "profile", "message_id", "message_name", "origin_xml",
    "dialect_entrypoints", "static_reference_status", "static_tx_evidence_count", "static_rx_evidence_count",
    "baseline_count", "parameter_phase_count", "request_phase_count", "total_observed_count",
    "first_host_monotonic_ns", "last_host_monotonic_ns", "request_attempted", "request_ack_result",
    "request_matching_frame_count", "request_classification", "runtime_support_class", "observation_evidence",
    "request_evidence", "interpretation_limit",
]
PARAMETER_COLUMNS = [
    "capture_id", "system", "vehicle", "profile", "name", "wire_value", "wire_value_float32_hex",
    "decoded_value", "decode_policy", "param_type", "param_type_name", "param_index", "param_count",
    "source_system", "source_component", "received_host_monotonic_ns", "source_path", "source_sha256",
    "snapshot_status", "implementation_satisfaction",
]
TIME_COLUMNS = [
    "capture_id", "system", "vehicle", "message_id", "message_name", "field", "xml_units",
    "xml_description", "first_value", "last_value", "sample_values", "first_host_monotonic_ns",
    "last_host_monotonic_ns", "host_clock", "clock_warning", "evidence",
]
PROPERTY_COLUMNS = [
    "property_id", "parameter_id", "capture_id", "value", "unit", "source_path", "source_sha256",
    "source_param_index", "source_param_count", "status",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    args = parser.parse_args()
    paths = manifest_candidates(args.manifest)
    if not paths:
        raise SystemExit("No Milestone-6 per-profile manifest found")
    captures, property_parameters, attempts = select_captures(paths)
    merged = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "captures": captures,
        "property_parameters": sorted(property_parameters, key=lambda row: (row["property_id"], row["capture_id"], row["parameter_id"])),
        "implementation_satisfaction": "NOT_ASSESSED",
    }
    schema = read_json(BENCHMARK / "schemas" / "runtime_capture.schema.json")
    errors = list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(merged))
    if errors:
        raise SystemExit("Merged runtime evidence schema failure:\n" + "\n".join(
            f"{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors
        ))
    write_json(M6 / "runtime_evidence.json", merged)
    write_json(M6 / "capture_attempts.json", {"schema_version": "1.0", "generated_at": utc_now(), "attempts": attempts})

    parameter_rows = build_parameter_rows(captures)
    message_rows, time_rows = build_message_rows(captures)
    support_path = static_support_path()
    write_csv(M6 / "runtime_parameter_snapshots.csv", parameter_rows, PARAMETER_COLUMNS)
    write_json(M6 / "runtime_parameter_snapshots.json", {"schema_version": "1.0", "rows": parameter_rows})
    write_csv(M6 / "runtime_message_support_matrix.csv", message_rows, MESSAGE_COLUMNS)
    write_json(
        M6 / "runtime_message_support_matrix.json",
        {
            "schema_version": "1.0",
            "static_support_source": {
                "path": rel(support_path),
                "sha256": sha256(support_path),
            },
            "rows": message_rows,
        },
    )
    write_csv(M6 / "runtime_time_field_observations.csv", time_rows, TIME_COLUMNS)
    write_csv(M6 / "property_runtime_parameters.csv", merged["property_parameters"], PROPERTY_COLUMNS)
    print(
        f"merged captures={len(captures)} attempts={len(attempts)} params={len(parameter_rows)} "
        f"message_profile_rows={len(message_rows)} time_observations={len(time_rows)} "
        f"property_parameters={len(property_parameters)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
