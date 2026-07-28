#!/usr/bin/env python3
"""Read-only aggregate acceptance checks for Milestone 6 runtime evidence.

This validator intentionally does not rebuild captures, merge products, property
catalogs, or the static MAVLink catalog.  It checks the artifacts already on
disk and invokes only existing validators that are themselves read-only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shlex
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
M6 = BENCHMARK / "extraction_runs" / "milestone6"
ARDU_DIR = M6 / "ArduPilot"
PX4_DIR = M6 / "PX4"
FAILED_PX4_DIR = PX4_DIR / "attempt_1_none_iris_failed"
STATIC_MAVLINK_DIR = BENCHMARK / "mavlink_catalog"
STATIC_SUPPORT_MATRIX = STATIC_MAVLINK_DIR / "static_support_matrix.csv"
RUNTIME_SUPPORT_CSV = STATIC_MAVLINK_DIR / "actual_support_matrix.csv"
RUNTIME_SUPPORT_JSON = STATIC_MAVLINK_DIR / "actual_support_matrix.json"
RUNTIME_CATALOG_MANIFEST = STATIC_MAVLINK_DIR / "runtime_catalog_manifest.json"

ARDU_MANIFEST = ARDU_DIR / "manifest.json"
PX4_MANIFEST = PX4_DIR / "manifest.json"
FAILED_PX4_MANIFEST = FAILED_PX4_DIR / "manifest.json"
RUNTIME_EVIDENCE = M6 / "runtime_evidence.json"
CAPTURE_ATTEMPTS = M6 / "capture_attempts.json"

EXPECTED_PROFILES = {
    "ardupilot-copter-m6": ("ArduPilot", "ArduCopter", "quad"),
    "ardupilot-plane-m6": ("ArduPilot", "ArduPlane", "plane"),
    "ardupilot-rover-m6": ("ArduPilot", "Rover", "rover"),
    "PX4-M6-MC-SIHSIM-QUADX-I42-20260718": (
        "PX4",
        "multicopter",
        "px4_sitl_default sihsim_quadx internal headless SIH instance 42",
    ),
}
EXPECTED_COMMITS = {
    "ArduPilot": (
        "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
        "13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472",
    ),
    "PX4": (
        "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
        "33af200d25ec6f0925b49b1ba82bbf1294ea5f72",
    ),
}
FAILED_CAPTURE_ID = "PX4-M6-MC-NONE-IRIS-I42-20260718"

MERGE_OUTPUTS = (
    "runtime_evidence.json",
    "capture_attempts.json",
    "runtime_parameter_snapshots.csv",
    "runtime_parameter_snapshots.json",
    "runtime_message_support_matrix.csv",
    "runtime_message_support_matrix.json",
    "runtime_time_field_observations.csv",
    "property_runtime_parameters.csv",
)

SUBVALIDATORS = (
    ("python3", "benchmark/scripts/validate_runtime_capture.py"),
    # The live catalogs are enriched by Milestone 7; the stage-7 validator
    # rechecks every Milestone-6 runtime-instance invariant before its added gates.
    ("python3", "benchmark/scripts/validate_property_catalog.py", "--stage", "7"),
    ("python3", "-B", "benchmark/scripts/apply_runtime_catalog.py", "--check"),
)
SIDE_EFFECTING_STATIC_VALIDATOR = (
    "python3",
    "benchmark/mavlink_catalog/validate_catalog.py",
)


@dataclass
class Audit:
    checks: int = 0
    failures: list[str] = field(default_factory=list)
    metrics: Counter[str] = field(default_factory=Counter)

    def require(self, condition: bool, label: str) -> bool:
        self.checks += 1
        if not condition:
            self.failures.append(label)
        return condition


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_json(audit: Audit, path: Path, *, label: str | None = None) -> Any | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        audit.require(False, f"{label or path}: JSON parse failed: {error}")
        return None
    audit.require(True, f"{label or path}: JSON parses")
    return value


def read_csv(audit: Audit, path: Path) -> list[dict[str, str]] | None:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            fields = reader.fieldnames
    except (OSError, UnicodeError, csv.Error) as error:
        audit.require(False, f"{path}: CSV parse failed: {error}")
        return None
    audit.require(bool(fields), f"{path}: CSV has a header")
    audit.require(all(None not in row for row in rows), f"{path}: CSV rows match the header")
    audit.metrics["csv_files"] += 1
    audit.metrics["csv_rows"] += len(rows)
    return rows


def parse_all_json_and_jsonl(audit: Audit) -> dict[Path, Any]:
    documents: dict[Path, Any] = {}
    json_paths = sorted(M6.rglob("*.json"))
    jsonl_paths = sorted(M6.rglob("*.jsonl"))
    audit.require(bool(json_paths), "Milestone-6 JSON inventory is nonempty")
    audit.require(bool(jsonl_paths), "Milestone-6 JSONL inventory is nonempty")
    for path in json_paths:
        value = read_json(audit, path)
        if value is not None:
            documents[path] = value
            audit.metrics["json_files"] += 1

    allowed_empty = {FAILED_PX4_DIR / "mavlink_messages.jsonl"}
    for path in jsonl_paths:
        line_count = 0
        error_text: str | None = None
        try:
            with path.open(encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        error_text = f"blank record at line {line_number}"
                        break
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as error:
                        error_text = f"line {line_number}: {error}"
                        break
                    line_count += 1
        except (OSError, UnicodeError) as error:
            error_text = str(error)
        audit.require(error_text is None, f"{path}: JSONL parse failed: {error_text}")
        if path in allowed_empty:
            audit.require(line_count == 0, f"{path}: failed pre-heartbeat attempt must remain empty")
        else:
            audit.require(line_count > 0, f"{path}: successful evidence JSONL is empty")
        audit.metrics["jsonl_files"] += 1
        audit.metrics["jsonl_records"] += line_count
    return documents


def recursively_named_values(value: Any, name: str) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == name:
                yield item
            yield from recursively_named_values(item, name)
    elif isinstance(value, list):
        for item in value:
            yield from recursively_named_values(item, name)


def validate_artifacts(
    audit: Audit,
    manifest_path: Path,
    document: dict[str, Any],
) -> None:
    if "artifact_inventory" in document:
        artifacts = document["artifact_inventory"]
    else:
        artifacts = [
            artifact
            for capture in document.get("captures", [])
            for artifact in capture.get("artifacts", [])
        ]
    paths = [artifact.get("path") for artifact in artifacts]
    audit.require(bool(artifacts), f"{manifest_path}: artifact inventory is nonempty")
    audit.require(len(paths) == len(set(paths)), f"{manifest_path}: duplicate artifact path")
    for artifact in artifacts:
        value = artifact.get("path")
        audit.require(isinstance(value, str) and bool(value), f"{manifest_path}: artifact path is valid")
        if not isinstance(value, str) or not value:
            continue
        path = workspace_path(value)
        try:
            path.resolve().relative_to(ROOT.resolve())
            inside_workspace = True
        except ValueError:
            inside_workspace = False
        audit.require(inside_workspace, f"{manifest_path}: artifact escapes workspace: {value}")
        exists = audit.require(path.is_file(), f"{manifest_path}: missing artifact {value}")
        if not exists:
            continue
        if "bytes" in artifact:
            audit.require(
                path.stat().st_size == artifact["bytes"],
                f"{manifest_path}: byte count drift for {value}",
            )
        expected_hash = artifact.get("sha256")
        audit.require(
            isinstance(expected_hash, str) and sha256(path) == expected_hash,
            f"{manifest_path}: SHA-256 drift for {value}",
        )
        audit.metrics["artifact_references"] += 1


def phase_name(phase: dict[str, Any]) -> str:
    name = phase.get("name", "")
    return "OTHER" if name in {"STARTUP", "RELEVANT_STREAM_SAMPLE"} else name


def validate_success_profiles(
    audit: Audit,
    ardu_manifest: dict[str, Any],
    px4_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    captures = list(ardu_manifest.get("captures", [])) + list(px4_manifest.get("captures", []))
    by_id = {capture.get("capture_id"): capture for capture in captures}
    audit.require(len(captures) == 4, "exactly four successful profile records exist")
    audit.require(len(by_id) == 4, "successful capture IDs are unique")
    audit.require(set(by_id) == set(EXPECTED_PROFILES), "successful capture ID set matches the M6 contract")

    for capture_id, expected in EXPECTED_PROFILES.items():
        capture = by_id.get(capture_id)
        if capture is None:
            continue
        actual = (capture.get("system"), capture.get("vehicle"), capture.get("profile"))
        audit.require(actual == expected, f"{capture_id}: profile identity drift")
        audit.require(capture.get("runtime_status") == "COMPLETE", f"{capture_id}: capture is not COMPLETE")
        firmware, mavlink = EXPECTED_COMMITS[expected[0]]
        audit.require(capture.get("firmware_commit") == firmware, f"{capture_id}: firmware commit drift")
        audit.require(capture.get("mavlink_commit") == mavlink, f"{capture_id}: MAVLink commit drift")

        phases = capture.get("phases", [])
        normalized_names = [phase_name(item) for item in phases]
        for required in ("BASELINE", "PARAMETER_DOWNLOAD", "REQUEST_SWEEP"):
            audit.require(required in normalized_names, f"{capture_id}: missing phase {required}")
        ordered = [normalized_names.index(name) for name in ("BASELINE", "PARAMETER_DOWNLOAD", "REQUEST_SWEEP") if name in normalized_names]
        audit.require(ordered == sorted(ordered), f"{capture_id}: phase order drift")
        for phase in phases:
            start = phase.get("start_host_monotonic_ns")
            end = phase.get("end_host_monotonic_ns")
            audit.require(
                isinstance(start, int) and isinstance(end, int) and end >= start,
                f"{capture_id}: invalid monotonic interval for {phase.get('name')}",
            )
        baseline = next((item for item in phases if item.get("name") == "BASELINE"), None)
        audit.require(
            baseline is not None
            and baseline["end_host_monotonic_ns"] - baseline["start_host_monotonic_ns"] >= 10_000_000_000,
            f"{capture_id}: baseline is shorter than 10 seconds",
        )

        snapshot = capture.get("parameter_snapshot", {})
        expected_count = snapshot.get("expected_count")
        received_count = snapshot.get("received_count", snapshot.get("received_response_count"))
        audit.require(snapshot.get("status") == "COMPLETE", f"{capture_id}: parameter snapshot is not COMPLETE")
        audit.require(isinstance(expected_count, int) and expected_count > 0, f"{capture_id}: invalid expected parameter count")
        audit.require(snapshot.get("missing_indices") == [], f"{capture_id}: parameter indices are missing")
        audit.require(
            isinstance(received_count, int) and received_count >= expected_count,
            f"{capture_id}: too few PARAM_VALUE responses",
        )
        audit.require(
            isinstance(snapshot.get("unique_parameter_count"), int)
            and snapshot["unique_parameter_count"] >= expected_count,
            f"{capture_id}: unique parameter set is incomplete",
        )

        summary = capture.get("message_summary", {})
        audit.require(summary.get("total_message_count", 0) > 0, f"{capture_id}: message trace is empty")
        audit.require(summary.get("distinct_message_count", summary.get("distinct_message_key_count", 0)) > 0, f"{capture_id}: no distinct messages")
        sweep = capture.get("request_sweep", {})
        audit.require(sweep.get("status") == "COMPLETE", f"{capture_id}: request sweep is not COMPLETE")
        audit.require(sweep.get("attempted", 0) > 0, f"{capture_id}: request sweep attempted zero messages")
        audit.require(sweep.get("no_response") == 0, f"{capture_id}: request sweep has a response timeout")
        audit.require(sweep.get("unsupported") == 0, f"{capture_id}: unsupported counter drift")
    return captures


def validate_authoritative_traffic(
    audit: Audit,
    ardu_manifest: dict[str, Any],
    px4_manifest: dict[str, Any],
) -> None:
    for capture in ardu_manifest["captures"]:
        capture_id = capture["capture_id"]
        traffic = capture["traffic_capture"]
        decoded = traffic["authoritative_decoded_capture"]
        jsonl_path = workspace_path(decoded["path"])
        line_count = sum(1 for _ in jsonl_path.open(encoding="utf-8"))
        audit.require(jsonl_path.stat().st_size > 0, f"{capture_id}: authoritative messages.jsonl is empty")
        audit.require(line_count == decoded["jsonl_records"], f"{capture_id}: messages.jsonl line-count drift")
        audit.require(line_count == capture["message_summary"]["total_message_count"], f"{capture_id}: trace/summary count mismatch")
        for key in ("auxiliary_tlog_capture", "auxiliary_raw_capture"):
            auxiliary = traffic[key]
            path = workspace_path(auxiliary["path"])
            audit.require(path.stat().st_size == 0, f"{capture_id}: documented empty {path.name} changed")
            audit.require(
                auxiliary["status"] == "EMPTY_LOGGING_ATTEMPT_NO_EVIDENCE",
                f"{capture_id}: empty auxiliary capture is mislabeled as evidence",
            )

        run_dir = jsonl_path.parent
        outbound_rows = []
        with (run_dir / "outbound_actions.jsonl").open(encoding="utf-8") as stream:
            outbound_rows = [json.loads(line) for line in stream]
        audit.require(
            not any(row.get("phase") == "BASELINE" for row in outbound_rows),
            f"{capture_id}: explicit protocol action occurred during BASELINE",
        )

        sweep = read_json(audit, run_dir / "request_sweep.json", label=f"{capture_id} request sweep")
        if not isinstance(sweep, dict):
            continue
        results = sweep.get("results", [])
        ack_counts = Counter(row.get("command_ack_result_name") for row in results)
        audit.require(len(results) == sweep.get("attempted"), f"{capture_id}: request record count drift")
        audit.require(sum(ack_counts.values()) == sweep.get("attempted"), f"{capture_id}: not every request has an ACK")
        audit.require(set(ack_counts) <= {"MAV_RESULT_ACCEPTED", "MAV_RESULT_FAILED"}, f"{capture_id}: unexpected ACK class")
        audit.require(ack_counts.get("MAV_RESULT_FAILED", 0) > 0, f"{capture_id}: FAILED ACK boundary evidence disappeared")
        audit.require(dict(ack_counts) == sweep.get("ack_result_counts"), f"{capture_id}: ACK aggregate drift")
        audit.require(
            "COMMAND_ACK has no request sequence or requested message ID" in sweep.get("limitation", ""),
            f"{capture_id}: ACK correlation limitation is missing",
        )

    px4_capture = px4_manifest["captures"][0]
    px4_jsonl = PX4_DIR / "mavlink_messages.jsonl"
    px4_tlog = PX4_DIR / "mavlink_capture.tlog"
    px4_line_count = sum(1 for _ in px4_jsonl.open(encoding="utf-8"))
    audit.require(px4_jsonl.stat().st_size > 0, "PX4 authoritative decoded JSONL is empty")
    audit.require(px4_tlog.stat().st_size > 0, "PX4 authoritative tlog is empty")
    audit.require(px4_line_count == px4_capture["message_summary"]["total_message_count"], "PX4 trace/summary count mismatch")
    sweep = read_json(audit, PX4_DIR / "message_request_sweep.json", label="PX4 request sweep")
    if isinstance(sweep, dict):
        records = sweep.get("records", [])
        ack_counts = Counter((row.get("ack") or {}).get("result_name") for row in records)
        audit.require(len(records) == sweep.get("attempted"), "PX4 request record count drift")
        audit.require(sum(ack_counts.values()) == sweep.get("attempted"), "PX4 request lacks ACK evidence")
        audit.require(set(ack_counts) <= {"MAV_RESULT_ACCEPTED", "MAV_RESULT_DENIED"}, "PX4 unexpected ACK class")
        audit.require(ack_counts.get("MAV_RESULT_DENIED", 0) > 0, "PX4 DENIED ACK boundary evidence disappeared")
        audit.require(dict(ack_counts) == sweep.get("ack_result_counts"), "PX4 ACK aggregate drift")
        audit.require(sweep.get("no_ack_no_matching_frame") == 0, "PX4 request-level no-response drift")
        audit.require(sweep.get("unsupported") == 0, "PX4 DENIED ACK was incorrectly counted as unsupported")


def validate_cleanup_and_failed_attempt(
    audit: Audit,
    ardu_manifest: dict[str, Any],
    failed_manifest: dict[str, Any],
    attempts: dict[str, Any],
) -> None:
    for capture in ardu_manifest["captures"]:
        cleanup = capture["process_cleanup"]
        capture_id = capture["capture_id"]
        audit.require(cleanup.get("cleaned_only_owned_process_group") is True, f"{capture_id}: cleanup scope drift")
        audit.require(cleanup.get("pid_exists_after_wait") is False, f"{capture_id}: owned PID survived cleanup")
        audit.require(cleanup.get("return_code") == -2, f"{capture_id}: expected SIGINT return code changed")
        audit.require(
            [row.get("signal") for row in cleanup.get("signals", [])] == ["SIGINT"],
            f"{capture_id}: cleanup signal sequence drift",
        )
        post = cleanup.get("post_cleanup_process_tree", {})
        audit.require(post.get("exit_code") == 1 and not post.get("stdout"), f"{capture_id}: residual process tree")

    failed_captures = failed_manifest.get("captures", [])
    audit.require(len(failed_captures) == 1, "exactly one preserved failed PX4 capture exists")
    if failed_captures:
        capture = failed_captures[0]
        audit.require(capture.get("capture_id") == FAILED_CAPTURE_ID, "failed PX4 capture ID drift")
        audit.require(capture.get("runtime_status") == "FAILED", "preserved PX4 attempt is not FAILED")
        audit.require(capture.get("parameter_snapshot", {}).get("status") == "FAILED", "failed attempt parameter state drift")
        audit.require(capture.get("request_sweep", {}).get("status") == "FAILED", "failed attempt sweep state drift")

    details = read_json(audit, FAILED_PX4_DIR / "capture_details.json", label="failed PX4 capture details")
    lifecycle = read_json(audit, FAILED_PX4_DIR / "process_lifecycle.json", label="failed PX4 cleanup")
    if isinstance(details, dict):
        error = details.get("runtime_error") or ""
        audit.require("TimeoutError" in error and "HEARTBEAT" in error, "failed attempt timeout evidence drift")
        audit.require(details.get("message_count") == 0, "failed pre-heartbeat attempt unexpectedly has messages")
        audit.require(details.get("implementation_satisfaction") == "NOT_ASSESSED", "failed attempt assessed implementation")
    if isinstance(lifecycle, dict):
        audit.require(lifecycle.get("cleanup_complete") is True, "failed PX4 attempt cleanup is incomplete")
        audit.require(lifecycle.get("post_shutdown_identity", {}).get("exists") is False, "failed PX4 PID survived cleanup")
        audit.require(lifecycle.get("process_group_members_after_shutdown") == [], "failed PX4 process group survived cleanup")
        audit.require(
            all(item.get("available") is True for item in lifecycle.get("post_cleanup_ports", {}).values()),
            "failed PX4 attempt left a bound UDP port",
        )

    success_lifecycle = read_json(audit, PX4_DIR / "process_lifecycle.json", label="successful PX4 cleanup")
    if isinstance(success_lifecycle, dict):
        audit.require(success_lifecycle.get("cleanup_complete") is True, "successful PX4 cleanup is incomplete")
        audit.require(success_lifecycle.get("post_shutdown_identity", {}).get("exists") is False, "successful PX4 PID survived cleanup")
        audit.require(success_lifecycle.get("process_group_members_after_shutdown") == [], "successful PX4 process group survived cleanup")
        audit.require(
            all(item.get("available") is True for item in success_lifecycle.get("post_cleanup_ports", {}).values()),
            "successful PX4 capture left a bound UDP port",
        )

    attempt_rows = attempts.get("attempts", [])
    audit.require(len(attempt_rows) == 5, "capture_attempts must retain four selected and one failed attempt")
    selected = [row for row in attempt_rows if row.get("selected")]
    rejected = [row for row in attempt_rows if not row.get("selected")]
    audit.require({row.get("capture_id") for row in selected} == set(EXPECTED_PROFILES), "selected attempt set drift")
    audit.require(len(rejected) == 1 and rejected[0].get("capture_id") == FAILED_CAPTURE_ID, "failed attempt is not retained as unselected")
    for row in attempt_rows:
        manifest_path = workspace_path(row.get("manifest_path", ""))
        audit.require(manifest_path.is_file(), f"attempt manifest missing: {row.get('manifest_path')}")
        if manifest_path.is_file():
            audit.require(sha256(manifest_path) == row.get("manifest_sha256"), f"attempt manifest hash drift: {row.get('capture_id')}")


def validate_schema_and_merge(
    audit: Audit,
    documents: dict[Path, Any],
) -> dict[str, Any] | None:
    for name in MERGE_OUTPUTS:
        audit.require((M6 / name).is_file(), f"missing merge output: {name}")

    schema = read_json(audit, BENCHMARK / "schemas" / "runtime_capture.schema.json", label="runtime_capture schema")
    evidence = documents.get(RUNTIME_EVIDENCE) or read_json(audit, RUNTIME_EVIDENCE)
    px4_manifest = documents.get(PX4_MANIFEST) or read_json(audit, PX4_MANIFEST)
    failed_manifest = documents.get(FAILED_PX4_MANIFEST) or read_json(audit, FAILED_PX4_MANIFEST)
    if not isinstance(schema, dict):
        return evidence if isinstance(evidence, dict) else None
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    for path, document in (
        (RUNTIME_EVIDENCE, evidence),
        (PX4_MANIFEST, px4_manifest),
        (FAILED_PX4_MANIFEST, failed_manifest),
    ):
        if not isinstance(document, dict):
            audit.require(False, f"{path}: no document available for schema validation")
            continue
        errors = sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path))
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors[:5]
        )
        audit.require(not errors, f"{path}: runtime_capture schema errors: {detail}")

    if not isinstance(evidence, dict):
        return None
    captures = evidence.get("captures", [])
    audit.require(len(captures) == 4, "merged runtime evidence must contain four captures")
    audit.require({item.get("capture_id") for item in captures} == set(EXPECTED_PROFILES), "merged profile set drift")
    audit.require(all(item.get("runtime_status") == "COMPLETE" for item in captures), "merged capture is not COMPLETE")
    audit.require(len(evidence.get("property_parameters", [])) == 15, "merged property-parameter row count drift")
    audit.require(evidence.get("implementation_satisfaction") == "NOT_ASSESSED", "merged evidence assessed implementation")

    parameter_csv = read_csv(audit, M6 / "runtime_parameter_snapshots.csv")
    message_csv = read_csv(audit, M6 / "runtime_message_support_matrix.csv")
    time_csv = read_csv(audit, M6 / "runtime_time_field_observations.csv")
    property_csv = read_csv(audit, M6 / "property_runtime_parameters.csv")
    parameter_json = documents.get(M6 / "runtime_parameter_snapshots.json")
    message_json = documents.get(M6 / "runtime_message_support_matrix.json")

    if parameter_csv is not None and isinstance(parameter_json, dict):
        json_rows = parameter_json.get("rows", [])
        audit.require(len(parameter_csv) == len(json_rows), "runtime parameter CSV/JSON row count drift")
        csv_keys = {(row["capture_id"], row["name"], row["param_index"]) for row in parameter_csv}
        json_keys = {(str(row["capture_id"]), str(row["name"]), str(row["param_index"])) for row in json_rows}
        audit.require(csv_keys == json_keys, "runtime parameter CSV/JSON identity drift")
        audit.require(
            all(row.get("implementation_satisfaction") == "NOT_ASSESSED" for row in json_rows),
            "runtime parameter JSON contains an implementation verdict",
        )
        audit.require(
            all(row.get("implementation_satisfaction") == "NOT_ASSESSED" for row in parameter_csv),
            "runtime parameter CSV contains an implementation verdict",
        )
        expected_parameter_rows = sum(item["parameter_snapshot"]["unique_parameter_count"] for item in captures)
        audit.require(len(json_rows) == expected_parameter_rows, "runtime parameter matrix does not cover all unique parameters")

    if message_csv is not None and isinstance(message_json, dict):
        json_rows = message_json.get("rows", [])
        audit.require(len(message_csv) == len(json_rows), "runtime message CSV/JSON row count drift")
        csv_keys = {(row["capture_id"], row["message_id"]) for row in message_csv}
        json_keys = {(str(row["capture_id"]), str(row["message_id"])) for row in json_rows}
        audit.require(csv_keys == json_keys, "runtime message CSV/JSON identity drift")
        audit.require(len(csv_keys) == len(message_csv), "runtime message matrix has duplicate profile/message rows")
        allowed_classes = {
            "DEFAULT_STREAM_OBSERVED",
            "REQUEST_WINDOW_MESSAGE_OBSERVED",
            "REQUEST_ACK_ACCEPTED_NO_MATCHING_FRAME",
            "REQUEST_ACK_FAILED",
            "REQUEST_ACK_DENIED",
            "REQUESTED_NO_ACK_NO_MATCHING_FRAME",
            "NOT_IN_REQUEST_SWEEP_AND_NOT_OBSERVED",
        }
        audit.require(
            {row.get("runtime_support_class") for row in json_rows} <= allowed_classes,
            "runtime support matrix contains an unknown support class",
        )
        audit.require(
            all("conformance" not in row.get("interpretation_limit", "").lower() or "not" in row.get("interpretation_limit", "").lower() for row in json_rows),
            "runtime support row makes a conformance claim",
        )

    if time_csv is not None:
        audit.require(bool(time_csv), "runtime time-field observations are empty")
        audit.require(all(row.get("host_clock") == "CLOCK_MONOTONIC_NS" for row in time_csv), "time rows use an unexpected host clock")
        audit.require(
            all("not substituted" in row.get("clock_warning", "") for row in time_csv),
            "time rows omit the host/onboard clock separation warning",
        )
    if property_csv is not None:
        audit.require(len(property_csv) == 15, "property runtime parameter CSV row count drift")
        csv_keys = {(row["property_id"], row["capture_id"], row["parameter_id"]) for row in property_csv}
        json_keys = {
            (str(row["property_id"]), str(row["capture_id"]), str(row["parameter_id"]))
            for row in evidence.get("property_parameters", [])
        }
        audit.require(csv_keys == json_keys, "property runtime parameter CSV/merge identity drift")
    return evidence


def validate_static_and_runtime_catalogs(
    audit: Audit,
    evidence: dict[str, Any] | None,
) -> None:
    audit.require(STATIC_MAVLINK_DIR.is_dir(), "static MAVLink catalog directory is missing")
    audit.require(M6.is_dir(), "runtime MAVLink evidence directory is missing")
    manifest = read_json(audit, STATIC_MAVLINK_DIR / "manifest.json", label="static MAVLink manifest")
    if isinstance(manifest, dict):
        outputs = manifest.get("output_sha256", {})
        audit.require(bool(outputs), "static MAVLink manifest has no outputs")
        audit.require("static_support_matrix.csv" in outputs, "static manifest does not own static_support_matrix.csv")
        audit.require(
            not ({"actual_support_matrix.csv", "actual_support_matrix.json"} & set(outputs)),
            "static manifest incorrectly owns the runtime overlay",
        )
        for name, expected_hash in outputs.items():
            path = STATIC_MAVLINK_DIR / name
            exists = audit.require(path.is_file(), f"static MAVLink output missing: {name}")
            if exists:
                audit.require(sha256(path) == expected_hash, f"static MAVLink output hash drift: {name}")
        for role in ("generator", "validator", "documentation"):
            record = manifest.get(role, {})
            path = workspace_path(record.get("path", ""))
            exists = audit.require(path.is_file(), f"static MAVLink {role} is missing")
            if exists:
                audit.require(sha256(path) == record.get("sha256"), f"static MAVLink {role} hash drift")
        for system, inputs in manifest.get("inputs", {}).items():
            firmware, mavlink = EXPECTED_COMMITS[system]
            audit.require(inputs.get("sut_commit") == firmware, f"{system}: static catalog firmware commit drift")
            audit.require(inputs.get("mavlink_commit") == mavlink, f"{system}: static catalog MAVLink commit drift")
            for xml_file in inputs.get("xml_files", []):
                path = workspace_path(xml_file.get("path", ""))
                exists = audit.require(path.is_file(), f"static XML input missing: {xml_file.get('path')}")
                if exists:
                    audit.require(sha256(path) == xml_file.get("sha256"), f"static XML input hash drift: {xml_file.get('path')}")

    support_rows = read_csv(audit, STATIC_SUPPORT_MATRIX)
    if support_rows is not None:
        audit.require(bool(support_rows), "static support matrix is empty")
        required = {
            "system",
            "entity_kind",
            "entity_id",
            "dialect_definition_status",
            "static_source_reference_status",
        }
        fields = set(support_rows[0]) if support_rows else set()
        audit.require(required <= fields, "static support matrix lost layered definition/static columns")
        audit.require(
            all(row.get("default_runtime_observation_status") == "NOT_RUN_NO_CAPTURE" for row in support_rows),
            "static support matrix absorbed runtime observation status",
        )
        audit.require(
            all(not row.get("default_runtime_observation_evidence") for row in support_rows),
            "static support matrix absorbed runtime evidence paths",
        )
        static_keys = [(row["system"], row["entity_kind"], row["entity_id"]) for row in support_rows]
        audit.require(len(static_keys) == len(set(static_keys)), "static support matrix has duplicate entity rows")

    messages = read_json(audit, STATIC_MAVLINK_DIR / "messages_and_fields.json", label="static MAVLink messages")
    commands = read_json(audit, STATIC_MAVLINK_DIR / "commands.json", label="static MAVLink commands")
    message_rows = read_csv(audit, M6 / "runtime_message_support_matrix.csv")
    if isinstance(messages, dict) and isinstance(commands, dict) and support_rows is not None:
        message_count = sum(len(system.get("messages", [])) for system in messages.get("systems", []))
        command_count = sum(len(system.get("commands", [])) for system in commands.get("systems", []))
        audit.require(len(support_rows) == message_count + command_count, "static support matrix row-count drift")
    if isinstance(messages, dict) and message_rows is not None and evidence is not None:
        counts = {
            system["system"]: len(system.get("messages", []))
            for system in messages.get("systems", [])
        }
        profile_counts = Counter(item["system"] for item in evidence.get("captures", []))
        expected_rows = sum(counts[system] * profile_counts[system] for system in profile_counts)
        audit.require(len(message_rows) == expected_rows, "runtime message matrix does not cover every static message/profile pair")

    runtime_manifest = read_json(audit, RUNTIME_CATALOG_MANIFEST, label="runtime MAVLink catalog manifest")
    runtime_json = read_json(audit, RUNTIME_SUPPORT_JSON, label="runtime MAVLink support JSON")
    runtime_csv = read_csv(audit, RUNTIME_SUPPORT_CSV)
    if not isinstance(runtime_manifest, dict) or not isinstance(runtime_json, dict) or runtime_csv is None:
        return

    audit.require(runtime_manifest.get("generation_deterministic") is True, "runtime catalog is not deterministic")
    audit.require(runtime_manifest.get("implementation_satisfaction") == "NOT_ASSESSED", "runtime catalog manifest assessed implementation")
    audit.require(runtime_json.get("implementation_satisfaction") == "NOT_ASSESSED", "runtime catalog JSON assessed implementation")
    audit.require(
        runtime_manifest.get("validation_command")
        == "python3 -B benchmark/scripts/apply_runtime_catalog.py --check",
        "runtime catalog validation command drift",
    )
    generator = runtime_manifest.get("generator", {})
    generator_path = workspace_path(generator.get("path", ""))
    generator_exists = audit.require(generator_path.is_file(), "runtime catalog generator is missing")
    if generator_exists:
        audit.require(sha256(generator_path) == generator.get("sha256"), "runtime catalog generator hash drift")
    for item in runtime_manifest.get("inputs", []):
        path = workspace_path(item.get("path", ""))
        exists = audit.require(path.is_file(), f"runtime catalog input missing: {item.get('path')}")
        if exists:
            audit.require(sha256(path) == item.get("sha256"), f"runtime catalog input hash drift: {item.get('path')}")
    for value, item in runtime_manifest.get("outputs", {}).items():
        path = workspace_path(value)
        exists = audit.require(path.is_file(), f"runtime catalog output missing: {value}")
        if exists:
            audit.require(sha256(path) == item.get("sha256"), f"runtime catalog output hash drift: {value}")

    json_rows = runtime_json.get("rows", [])
    audit.require(len(runtime_csv) == len(json_rows), "runtime overlay CSV/JSON row-count drift")
    csv_keys = {
        (row["row_scope"], row["capture_id"], row["system"], row["message_id"], row["message_name"])
        for row in runtime_csv
    }
    json_keys = {
        (str(row["row_scope"]), str(row["capture_id"]), str(row["system"]), str(row["message_id"]), str(row["message_name"]))
        for row in json_rows
    }
    audit.require(csv_keys == json_keys, "runtime overlay CSV/JSON identity drift")
    audit.require(len(csv_keys) == len(runtime_csv), "runtime overlay contains duplicate rows")
    primary_rows = [row for row in json_rows if row.get("row_scope") == "PROFILE_STATIC_MESSAGE_DEFINITION"]
    supplemental_rows = [row for row in json_rows if row.get("row_scope") == "RUNTIME_NON_CATALOG_OBSERVATION"]
    unknown_scope_rows = [row for row in json_rows if row.get("row_scope") not in {"PROFILE_STATIC_MESSAGE_DEFINITION", "RUNTIME_NON_CATALOG_OBSERVATION"}]
    audit.require(not unknown_scope_rows, "runtime overlay contains an unknown row_scope")

    expected_counts = {
        "profile_count": 4,
        "primary_static_definition_row_count": 1307,
        "supplemental_non_catalog_observation_row_count": 3,
        "total_row_count": 1310,
    }
    for name, expected_count in expected_counts.items():
        audit.require(runtime_manifest.get(name) == expected_count, f"runtime catalog manifest count drift: {name}")
        audit.require(runtime_json.get(name) == expected_count, f"runtime catalog JSON count drift: {name}")
    audit.require(len(primary_rows) == 1307, "runtime overlay primary row-count drift")
    audit.require(len(supplemental_rows) == 3, "runtime overlay supplemental row-count drift")
    audit.require(len(json_rows) == 1310, "runtime overlay total row-count drift")
    audit.require(
        {row.get("capture_id") for row in primary_rows} == set(EXPECTED_PROFILES),
        "runtime overlay profile set drift",
    )
    audit.require(len(runtime_json.get("profile_summaries", [])) == 4, "runtime overlay profile-summary count drift")
    audit.require(
        all(
            row.get("static_requestable_evidence_status")
            == "UNKNOWN_NO_EXPLICIT_REQUESTABILITY_FIELD_IN_STATIC_CATALOG"
            for row in primary_rows
        ),
        "runtime overlay invented static requestability evidence",
    )
    audit.require(
        all(row.get("support_inference") == "NO_GLOBAL_SUPPORT_OR_UNSUPPORTED_INFERENCE" for row in primary_rows),
        "runtime overlay emitted a global support inference",
    )
    audit.require(
        all(
            row.get("system") == "ArduPilot"
            and row.get("message_id") == -1
            and row.get("message_name") == "BAD_DATA"
            and row.get("support_inference") == "NOT_A_STATIC_MESSAGE_SUPPORT_ROW"
            for row in supplemental_rows
        ),
        "runtime supplemental BAD_DATA boundary drift",
    )
    auxiliary_rows = [
        row
        for row in primary_rows
        if row.get("system") == "PX4"
        and row.get("request_dialect_definition_status") == "DEFINED_ONLY_IN_AUXILIARY_DIALECT"
    ]
    audit.require(len(auxiliary_rows) == 8, "PX4 auxiliary uAvionix-only row count drift")
    audit.require(
        all(
            row.get("request_sweep_membership_status") == "AUXILIARY_DIALECT_NOT_IN_REQUEST_SWEEP"
            and row.get("request_attempted") is False
            and not row.get("request_ack_result")
            for row in auxiliary_rows
        ),
        "PX4 auxiliary rows were misclassified as requested/timeout",
    )
    failed_ack_rows = [row for row in primary_rows if row.get("request_ack_result") == "MAV_RESULT_FAILED"]
    denied_ack_rows = [row for row in primary_rows if row.get("request_ack_result") == "MAV_RESULT_DENIED"]
    unsupported_ack_rows = [row for row in primary_rows if row.get("request_ack_result") == "MAV_RESULT_UNSUPPORTED"]
    audit.require(bool(failed_ack_rows) and bool(denied_ack_rows), "runtime overlay lost FAILED/DENIED ACK evidence")
    audit.require(not unsupported_ack_rows, "runtime overlay fabricated UNSUPPORTED ACK evidence")
    audit.require(
        all(row.get("request_ack_interpretation") == "FAILED_RESULT_ONLY_NOT_UNSUPPORTED_EVIDENCE" for row in failed_ack_rows),
        "FAILED ACK was converted to unsupported evidence",
    )
    audit.require(
        all(row.get("request_ack_interpretation") == "DENIED_RESULT_ONLY_NOT_UNSUPPORTED_EVIDENCE" for row in denied_ack_rows),
        "DENIED ACK was converted to unsupported evidence",
    )

    distributions = runtime_manifest.get("status_distributions", {})
    recomputed = {
        "row_scope_counts": Counter(str(row["row_scope"]) for row in json_rows),
        "catalog_definition_status_counts": Counter(str(row["catalog_definition_status"]) for row in json_rows),
        "request_dialect_definition_status_counts": Counter(str(row["request_dialect_definition_status"]) for row in primary_rows),
        "request_sweep_membership_status_counts": Counter(str(row["request_sweep_membership_status"]) for row in primary_rows),
        "static_supported_evidence_status_counts": Counter(str(row["static_supported_evidence_status"]) for row in primary_rows),
        "static_direction_evidence_status_counts": Counter(str(row["static_direction_evidence_status"]) for row in primary_rows),
        "request_ack_result_counts": Counter(str(row.get("request_ack_result") or "NOT_ATTEMPTED") for row in primary_rows),
        "runtime_observation_class_counts": Counter(str(row["runtime_observation_class"]) for row in primary_rows),
    }
    for name, counts in recomputed.items():
        audit.require(dict(sorted(counts.items())) == distributions.get(name), f"runtime catalog distribution drift: {name}")


def validate_not_assessed(
    audit: Audit,
    documents: dict[Path, Any],
) -> None:
    m6_values = [
        value
        for document in documents.values()
        for value in recursively_named_values(document, "implementation_satisfaction")
    ]
    audit.require(bool(m6_values), "Milestone-6 evidence has no explicit implementation_satisfaction markers")
    audit.require(set(m6_values) == {"NOT_ASSESSED"}, "Milestone-6 evidence contains an implementation verdict")

    total_properties = 0
    for system in ("ArduPilot", "PX4"):
        path = BENCHMARK / system / "property_catalog.json"
        catalog = read_json(audit, path, label=f"{system} live property catalog (includes Stage-7 formula gates)")
        if not isinstance(catalog, dict):
            continue
        properties = catalog.get("properties", [])
        total_properties += len(properties)
        audit.require(bool(properties), f"{system}: property catalog is empty")
        audit.require(
            all(item.get("implementation_satisfaction") == "NOT_ASSESSED" for item in properties),
            f"{system}: property catalog contains an implementation verdict",
        )
        audit.require(
            all(item.get("review", {}).get("decision") == "PENDING" for item in properties),
            f"{system}: property review was prematurely closed",
        )
        audit.require(
            all(
                item.get("validation", {}).get("parser", {}).get("status") in {"PASS", "NOT_APPLICABLE"}
                for item in properties
            ),
            f"{system}: live parser gate has an unexpected status",
        )
        instance_statuses = {
            instance.get("status")
            for item in properties
            for instance in item.get("mitl", {}).get("concrete_instances", [])
        }
        audit.require(
            instance_statuses <= {
                "INSTANTIATED_UNVALIDATED",
                "INSTANTIATED_FORMULA_VALIDATED",
                "DISABLED_BY_RUNTIME_CONFIGURATION",
                "NEEDS_CONTEXT",
                "NOT_FORMALIZED",
            },
            f"{system}: live instance contains an unknown lifecycle status",
        )
    audit.require(total_properties == 13, "Stage-6 property catalog count drift")


def validate_no_flight_or_conformance_scenario(
    audit: Audit,
    ardu_manifest: dict[str, Any],
    px4_manifest: dict[str, Any],
) -> None:
    for capture in ardu_manifest.get("captures", []):
        limits = " ".join(capture.get("limitations", [])).lower()
        audit.require(
            "no flight or property-conformance scenario was executed" in limits,
            f"{capture.get('capture_id')}: no-scenario limitation missing",
        )
    px4_capture = px4_manifest.get("captures", [{}])[0]
    limits = " ".join(px4_capture.get("limitations", [])).lower()
    audit.require("no external graphical simulator" in limits, "PX4 no-flight-scenario limitation missing")
    audit.require("not_assessed" in limits, "PX4 implementation-status limitation missing")
    commands = read_json(audit, PX4_DIR / "commands.json", label="PX4 protocol command ledger")
    if isinstance(commands, dict):
        audit.require(commands.get("persistent_parameter_writes") == [], "PX4 capture performed a persistent parameter write")
        allowed = {
            "GCS HEARTBEAT",
            "PARAM_REQUEST_LIST",
            "PARAM_REQUEST_READ",
            "MAV_CMD_REQUEST_MESSAGE (512)",
        }
        audit.require(set(commands.get("read_only_protocol_actions", [])) == allowed, "PX4 capture action set drift")


def run_subvalidators(audit: Audit) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for command in SUBVALIDATORS:
        command_text = shlex.join(command)
        print(f"SUBVALIDATOR command={command_text}")
        print(f"SUBVALIDATOR cwd={ROOT}")
        print("SUBVALIDATOR env=PYTHONDONTWRITEBYTECODE=1")
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as error:
            audit.require(False, f"subvalidator could not start: {command_text}: {error}")
            continue
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip())
        audit.require(result.returncode == 0, f"subvalidator failed ({result.returncode}): {command_text}")
        audit.metrics["subvalidators"] += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-subvalidators",
        action="store_true",
        help="run only the aggregate read-only checks (diagnostic use)",
    )
    args = parser.parse_args()
    audit = Audit()

    audit.require(ROOT == Path("/home/lqq/project/TAFuzz"), f"unexpected workspace root: {ROOT}")
    documents = parse_all_json_and_jsonl(audit)

    ardu_manifest = documents.get(ARDU_MANIFEST)
    px4_manifest = documents.get(PX4_MANIFEST)
    failed_manifest = documents.get(FAILED_PX4_MANIFEST)
    attempts = documents.get(CAPTURE_ATTEMPTS)
    for path, document in (
        (ARDU_MANIFEST, ardu_manifest),
        (PX4_MANIFEST, px4_manifest),
        (FAILED_PX4_MANIFEST, failed_manifest),
        (CAPTURE_ATTEMPTS, attempts),
    ):
        audit.require(isinstance(document, dict), f"required document is missing or invalid: {path}")

    if isinstance(ardu_manifest, dict) and isinstance(px4_manifest, dict):
        validate_success_profiles(audit, ardu_manifest, px4_manifest)
        validate_authoritative_traffic(audit, ardu_manifest, px4_manifest)
        validate_no_flight_or_conformance_scenario(audit, ardu_manifest, px4_manifest)
    if isinstance(ardu_manifest, dict):
        validate_artifacts(audit, ARDU_MANIFEST, ardu_manifest)
    if isinstance(px4_manifest, dict):
        validate_artifacts(audit, PX4_MANIFEST, px4_manifest)
    if isinstance(failed_manifest, dict):
        validate_artifacts(audit, FAILED_PX4_MANIFEST, failed_manifest)
    if isinstance(ardu_manifest, dict) and isinstance(failed_manifest, dict) and isinstance(attempts, dict):
        validate_cleanup_and_failed_attempt(audit, ardu_manifest, failed_manifest, attempts)

    evidence = validate_schema_and_merge(audit, documents)
    validate_static_and_runtime_catalogs(audit, evidence)
    validate_not_assessed(audit, documents)

    skipped_command = shlex.join(SIDE_EFFECTING_STATIC_VALIDATOR)
    print(
        "NOT_RUN side_effecting_subvalidator="
        f"{skipped_command} reason=rewrites benchmark/mavlink_catalog/validation_report.json"
    )
    if not args.skip_subvalidators:
        run_subvalidators(audit)

    print(
        "SUMMARY "
        f"checks={audit.checks} failures={len(audit.failures)} "
        f"artifacts={audit.metrics['artifact_references']} "
        f"json_files={audit.metrics['json_files']} "
        f"jsonl_files={audit.metrics['jsonl_files']} "
        f"jsonl_records={audit.metrics['jsonl_records']} "
        f"csv_files={audit.metrics['csv_files']} "
        f"csv_rows={audit.metrics['csv_rows']} "
        f"subvalidators={audit.metrics['subvalidators']}"
    )
    if audit.failures:
        print("FAIL: Milestone-6 aggregate validation")
        for index, failure in enumerate(audit.failures, 1):
            print(f"  {index}. {failure}")
        return 1
    print(f"PASS: Milestone-6 aggregate validation checks={audit.checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
