#!/usr/bin/env python3
"""Validate consolidated Milestone-6 runtime evidence without assessing the SUT."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
DEFAULT_EVIDENCE = BENCHMARK / "extraction_runs" / "milestone6" / "runtime_evidence.json"
EXPECTED_HEADS = {
    "ArduPilot": "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
    "PX4": "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
}
EXPECTED_MAVLINK = {
    "ArduPilot": "13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472",
    "PX4": "33af200d25ec6f0925b49b1ba82bbf1294ea5f72",
}
EXPECTED_PROFILES = {
    ("ArduPilot", "ArduCopter"),
    ("ArduPilot", "ArduPlane"),
    ("ArduPilot", "Rover"),
    ("PX4", "multicopter"),
}
PROPERTY_INSTANCES = {
    "ARD-COPTER-GCS-001": [("ArduPilot", "ArduCopter", "FS_GCS_TIMEOUT")],
    "ARD-COPTER-GUID-002": [("ArduPilot", "ArduCopter", "GUID_TIMEOUT")],
    "ARD-COPTER-RTL-003": [("ArduPilot", "ArduCopter", "RTL_LOIT_TIME")],
    "ARD-PLANE-TAKEOFF-001": [("ArduPilot", "ArduPlane", "TKOFF_TIMEOUT")],
    "ARD-ROVER-RCFS-001": [("ArduPilot", "Rover", "FS_TIMEOUT")],
    "ARD-ROVER-CRASH-002": [("ArduPilot", "Rover", "CRASH_TIMEOUT")],
    "ARD-SHARED-BATT-001": [
        ("ArduPilot", "ArduCopter", "BATT_LOW_TIMER"),
        ("ArduPilot", "ArduPlane", "BATT_LOW_TIMER"),
        ("ArduPilot", "Rover", "BATT_LOW_TIMER"),
    ],
    "PX4-MC-RCLOSS-001": [("PX4", "multicopter", "COM_RC_LOSS_T")],
    "PX4-MC-GCSLOSS-002": [("PX4", "multicopter", "COM_DL_LOSS_T")],
    "PX4-MC-OFFBOARD-003": [("PX4", "multicopter", "COM_OF_LOSS_T")],
    "PX4-MC-AUTODISARM-004": [("PX4", "multicopter", "COM_DISARM_LAND")],
    "PX4-MC-FLIGHTTIME-005": [("PX4", "multicopter", "COM_FLT_TIME_MAX")],
    "PX4-MC-RTLLOITER-006": [("PX4", "multicopter", "RTL_LAND_DELAY")],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def validate_capture(capture: dict[str, Any], failures: list[str]) -> None:
    capture_id = capture["capture_id"]
    system = capture["system"]
    fail(failures, capture["firmware_commit"] == EXPECTED_HEADS[system], f"{capture_id}: firmware commit mismatch")
    fail(failures, capture["mavlink_commit"] == EXPECTED_MAVLINK[system], f"{capture_id}: MAVLink commit mismatch")

    phases = capture["phases"]
    names = [phase["name"] for phase in phases]
    required = ["BASELINE", "PARAMETER_DOWNLOAD", "REQUEST_SWEEP"]
    if capture["runtime_status"] == "COMPLETE":
        fail(failures, all(name in names for name in required), f"{capture_id}: COMPLETE capture lacks a required phase")
    for phase in phases:
        fail(
            failures,
            phase["end_host_monotonic_ns"] >= phase["start_host_monotonic_ns"],
            f"{capture_id}: phase {phase['name']} has reversed monotonic interval",
        )
    ordered = [names.index(name) for name in required if name in names]
    fail(failures, ordered == sorted(ordered), f"{capture_id}: baseline/parameter/request phases are out of order")

    snapshot = capture["parameter_snapshot"]
    if snapshot["path"] is not None:
        path = workspace_path(snapshot["path"])
        fail(failures, path.is_file(), f"{capture_id}: missing parameter snapshot {path}")
        if path.is_file():
            fail(failures, sha256(path) == snapshot["sha256"], f"{capture_id}: parameter snapshot hash mismatch")
    names_seen = [item["name"] for item in snapshot["key_values"]]
    fail(failures, len(names_seen) == len(set(names_seen)), f"{capture_id}: duplicate key property parameter values")
    if snapshot["status"] == "COMPLETE":
        fail(failures, snapshot["expected_count"] is not None, f"{capture_id}: complete snapshot has no expected count")
        fail(failures, not snapshot["missing_indices"], f"{capture_id}: complete snapshot has missing indices")
        fail(
            failures,
            snapshot["unique_parameter_count"] >= snapshot["expected_count"],
            f"{capture_id}: complete snapshot has fewer unique names than indexed parameters",
        )

    for key in ("message_summary", "request_sweep"):
        record = capture[key]
        path_value = record.get("path")
        if path_value is None:
            continue
        path = workspace_path(path_value)
        fail(failures, path.is_file(), f"{capture_id}: missing {key} file {path}")
        if path.is_file():
            fail(failures, sha256(path) == record["sha256"], f"{capture_id}: {key} hash mismatch")
    sweep = capture["request_sweep"]
    if sweep["status"] == "COMPLETE":
        fail(failures, sweep["attempted"] > 0, f"{capture_id}: complete request sweep attempted zero messages")

    artifact_paths: set[str] = set()
    for artifact in capture["artifacts"]:
        fail(failures, artifact["path"] not in artifact_paths, f"{capture_id}: duplicate artifact path {artifact['path']}")
        artifact_paths.add(artifact["path"])
        path = workspace_path(artifact["path"])
        fail(failures, path.is_file(), f"{capture_id}: missing artifact {path}")
        if path.is_file():
            fail(failures, sha256(path) == artifact["sha256"], f"{capture_id}: artifact hash mismatch {path}")


def validate_property_parameters(doc: dict[str, Any], failures: list[str]) -> None:
    captures = {capture["capture_id"]: capture for capture in doc["captures"]}
    rows = doc["property_parameters"]
    expected = {
        (property_id, system, vehicle, parameter_id)
        for property_id, instances in PROPERTY_INSTANCES.items()
        for system, vehicle, parameter_id in instances
    }
    observed: list[tuple[str, str, str, str]] = []
    for row in rows:
        prop = row["property_id"]
        if prop not in PROPERTY_INSTANCES:
            failures.append(f"unknown property-parameter row {prop}")
            continue
        capture = captures.get(row["capture_id"])
        if capture is None:
            failures.append(f"{prop}: unknown capture {row['capture_id']}")
            continue
        key = (prop, capture["system"], capture["vehicle"], row["parameter_id"])
        observed.append(key)
        fail(failures, key in expected, f"{prop}: unexpected system/vehicle/parameter instance {key[1:]}")
        source = workspace_path(row["source_path"])
        fail(failures, source.is_file(), f"{prop}: missing source PARAM_VALUE file")
        if source.is_file():
            fail(failures, sha256(source) == row["source_sha256"], f"{prop}: source PARAM_VALUE hash mismatch")
        candidates = [
            item for item in capture["parameter_snapshot"]["key_values"]
            if item["name"] == row["parameter_id"]
        ]
        fail(failures, len(candidates) == 1, f"{prop}: selected parameter missing/duplicated in capture key_values")
        if len(candidates) == 1:
            item = candidates[0]
            fail(failures, float(item["decoded_value"]) == float(row["value"]), f"{prop}: selected value differs from captured value")
            fail(failures, item["param_index"] == row["source_param_index"], f"{prop}: param_index mismatch")
            fail(failures, item["param_count"] == row["source_param_count"], f"{prop}: param_count mismatch")
    fail(failures, len(observed) == len(set(observed)), "duplicate property/system/vehicle/parameter runtime instance")
    fail(
        failures,
        set(observed) == expected,
        f"property-parameter instances mismatch: missing={sorted(expected-set(observed))} extra={sorted(set(observed)-expected)}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    doc = json.loads(evidence_path.read_text(encoding="utf-8"))
    schema = json.loads((BENCHMARK / "schemas" / "runtime_capture.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    failures = [f"schema:{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in validator.iter_errors(doc)]
    if failures:
        raise SystemExit("FAIL\n" + "\n".join(failures))

    capture_ids = [capture["capture_id"] for capture in doc["captures"]]
    fail(failures, len(capture_ids) == len(set(capture_ids)), "duplicate capture_id")
    profiles = {(capture["system"], capture["vehicle"]) for capture in doc["captures"]}
    fail(failures, profiles == EXPECTED_PROFILES, f"capture profile set mismatch: {sorted(profiles)}")
    for capture in doc["captures"]:
        validate_capture(capture, failures)
    validate_property_parameters(doc, failures)

    fail(failures, git_head(ROOT / "baseline" / "ardupilot") == EXPECTED_HEADS["ArduPilot"], "current ArduPilot HEAD moved")
    fail(failures, git_head(ROOT / "baseline" / "px4") == EXPECTED_HEADS["PX4"], "current PX4 HEAD moved")
    fail(failures, doc["implementation_satisfaction"] == "NOT_ASSESSED", "implementation satisfaction was assessed")
    if failures:
        raise SystemExit("FAIL\n" + "\n".join(failures))

    statuses = Counter(capture["runtime_status"] for capture in doc["captures"])
    print(
        f"PASS: captures={len(doc['captures'])} statuses={dict(statuses)} "
        f"property_parameters={len(doc['property_parameters'])} implementation=NOT_ASSESSED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
