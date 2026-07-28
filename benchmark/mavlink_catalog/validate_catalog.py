#!/usr/bin/env python3
"""Validate cross-file consistency and frozen-input provenance for the catalog."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


CATALOG_DIR = Path(__file__).resolve().parent
WORKSPACE = CATALOG_DIR.parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(name: str) -> dict[str, Any]:
    return json.loads((CATALOG_DIR / name).read_text(encoding="utf-8"))


def read_csv(name: str) -> list[dict[str, str]]:
    with (CATALOG_DIR / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    checks: list[str] = []

    manifest = read_json("manifest.json")
    messages_json = read_json("messages_and_fields.json")
    commands_json = read_json("commands.json")
    parameters_json = read_json("configuration_parameters.json")
    message_rows = read_csv("messages_and_fields.csv")
    command_rows = read_csv("commands.csv")
    parameter_rows = read_csv("configuration_parameters.csv")
    support_rows = read_csv("static_support_matrix.csv")
    time_rows = read_csv("time_fields.csv")
    checks.append("all JSON and CSV files parse")

    for name, expected_hash in manifest["output_sha256"].items():
        path = CATALOG_DIR / name
        require(path.is_file(), f"missing output {name}", failures)
        if path.is_file():
            require(sha256(path) == expected_hash, f"SHA-256 mismatch: {name}", failures)
    checks.append("all manifest-listed output SHA-256 values match")
    for section in ("validator", "documentation"):
        path = WORKSPACE / manifest[section]["path"]
        require(path.is_file(), f"missing {section} file: {path}", failures)
        if path.is_file():
            require(
                sha256(path) == manifest[section]["sha256"],
                f"SHA-256 mismatch: {section}",
                failures,
            )
    checks.append("validator and documentation SHA-256 values match")

    system_paths = {
        "ArduPilot": (
            WORKSPACE / "baseline" / "ardupilot",
            WORKSPACE / "baseline" / "ardupilot" / "modules" / "mavlink",
        ),
        "PX4": (
            WORKSPACE / "baseline" / "px4",
            WORKSPACE
            / "baseline"
            / "px4"
            / "src"
            / "modules"
            / "mavlink"
            / "mavlink",
        ),
    }
    for system, (sut, mavlink) in system_paths.items():
        require(
            git_head(sut) == manifest["inputs"][system]["sut_commit"],
            f"{system} SUT commit changed",
            failures,
        )
        require(
            git_head(mavlink) == manifest["inputs"][system]["mavlink_commit"],
            f"{system} MAVLink commit changed",
            failures,
        )
        for xml_file in manifest["inputs"][system]["xml_files"]:
            path = WORKSPACE / xml_file["path"]
            require(path.is_file(), f"missing XML input: {xml_file['path']}", failures)
            if path.is_file():
                require(
                    sha256(path) == xml_file["sha256"],
                    f"XML hash changed: {xml_file['path']}",
                    failures,
                )
    checks.append("SUT/MAVLink commits and every XML input hash match")

    json_messages: list[dict[str, Any]] = []
    for system in messages_json["systems"]:
        json_messages.extend(system["messages"])
    json_commands: list[dict[str, Any]] = []
    for system in commands_json["systems"]:
        json_commands.extend(system["commands"])
    json_parameters = parameters_json["parameters"]

    message_keys = [(row["system"], row["message_id"]) for row in json_messages]
    message_name_keys = [(row["system"], row["name"]) for row in json_messages]
    require(len(message_keys) == len(set(message_keys)), "duplicate message ID per system", failures)
    require(
        len(message_name_keys) == len(set(message_name_keys)),
        "duplicate message name per system",
        failures,
    )
    expected_field_rows = sum(len(message["fields"]) for message in json_messages)
    require(
        len(message_rows) == expected_field_rows,
        f"message CSV field rows {len(message_rows)} != JSON {expected_field_rows}",
        failures,
    )
    for message in json_messages:
        offsets = [field["payload_wire_offset"] for field in message["fields"]]
        require(len(offsets) == len(set(offsets)), f"duplicate payload offset: {message['name']}", failures)
        max_end = max(
            (field["payload_wire_offset"] + field["payload_size"] for field in message["fields"]),
            default=0,
        )
        require(
            max_end == message["payload_max_length"],
            f"payload size mismatch: {message['system']} {message['name']}",
            failures,
        )
    checks.append("message IDs/names unique; CSV/JSON field counts and payload offsets agree")

    generated_header_check: dict[str, Any] = {
        "status": "SKIPPED_NO_BUILD_HEADERS",
        "messages_checked": 0,
        "field_offsets_checked": 0,
    }
    header_root = (
        WORKSPACE
        / "baseline"
        / "ardupilot"
        / "build"
        / "sitl"
        / "libraries"
        / "GCS_MAVLink"
        / "include"
        / "mavlink"
        / "v2.0"
    )
    if header_root.is_dir():
        header_failures: list[str] = []
        messages_checked = 0
        offsets_checked = 0
        for message in [row for row in json_messages if row["system"] == "ArduPilot"]:
            dialect = Path(message["origin_xml"]).stem
            header = header_root / dialect / f"mavlink_msg_{message['name'].lower()}.h"
            if not header.is_file():
                header_failures.append(f"generated header missing: {message['name']}")
                continue
            text = header.read_text(encoding="utf-8", errors="replace")
            max_match = re.search(
                rf"^#define MAVLINK_MSG_ID_{re.escape(message['name'])}_LEN (\d+)$",
                text,
                re.MULTILINE,
            )
            min_match = re.search(
                rf"^#define MAVLINK_MSG_ID_{re.escape(message['name'])}_MIN_LEN (\d+)$",
                text,
                re.MULTILINE,
            )
            if (
                not max_match
                or not min_match
                or int(max_match.group(1)) != message["payload_max_length"]
                or int(min_match.group(1)) != message["payload_min_length"]
            ):
                header_failures.append(f"generated length mismatch: {message['name']}")
            messages_checked += 1
            for field in message["fields"]:
                function = re.search(
                    rf"static inline [^\n]+\bmavlink_msg_{re.escape(message['name'].lower())}"
                    rf"_get_{re.escape(field['name'])}\([^)]*\)\s*\{{(.*?)\n\}}",
                    text,
                    re.DOTALL,
                )
                call = (
                    re.search(r"_MAV_RETURN_[A-Za-z0-9_]+\((.*?)\);", function.group(1), re.DOTALL)
                    if function
                    else None
                )
                numeric_args = re.findall(r"\b\d+\b", call.group(1)) if call else []
                if not numeric_args:
                    header_failures.append(
                        f"generated getter offset missing: {message['name']}.{field['name']}"
                    )
                    continue
                offsets_checked += 1
                if int(numeric_args[-1]) != field["payload_wire_offset"]:
                    header_failures.append(
                        f"generated getter offset mismatch: {message['name']}.{field['name']}"
                    )
        failures.extend(header_failures)
        generated_header_check = {
            "status": "PASS" if not header_failures else "FAIL",
            "messages_checked": messages_checked,
            "field_offsets_checked": offsets_checked,
            "failure_count": len(header_failures),
        }
        checks.append(
            "ArduPilot generated SITL headers corroborate every message length and field offset"
        )

    command_keys = [(row["system"], row["command_id"]) for row in json_commands]
    command_name_keys = [(row["system"], row["name"]) for row in json_commands]
    require(len(command_keys) == len(set(command_keys)), "duplicate MAV_CMD ID per system", failures)
    require(
        len(command_name_keys) == len(set(command_name_keys)),
        "duplicate MAV_CMD name per system",
        failures,
    )
    for command in json_commands:
        require(
            [param["index"] for param in command["params"]] == list(range(1, 8)),
            f"MAV_CMD does not have explicit param1..7: {command['name']}",
            failures,
        )
    require(
        len(command_rows) == len(json_commands) * 7,
        "command CSV is not exactly seven rows per MAV_CMD",
        failures,
    )
    checks.append("MAV_CMD IDs/names unique and every command has param1..param7")

    parameter_keys = [
        (row["system"], row["vehicle_scope"], row["name"]) for row in json_parameters
    ]
    duplicates = [key for key, count in Counter(parameter_keys).items() if count > 1]
    require(not duplicates, f"duplicate configuration parameter rows: {duplicates[:10]}", failures)
    require(
        len(parameter_rows) == len(json_parameters),
        "configuration parameter CSV/JSON row count differs",
        failures,
    )
    checks.append("configuration parameter keys unique within system/scope and CSV/JSON agree")

    expected_matrix = len(json_messages) + len(json_commands)
    require(
        len(support_rows) == expected_matrix,
        f"support matrix rows {len(support_rows)} != definition entities {expected_matrix}",
        failures,
    )
    allowed_static = {
        "STATIC_REFERENCE_FOUND",
        "NO_REFERENCE_FOUND_BY_HEURISTIC_SCAN",
    }
    for row in support_rows:
        require(
            row["dialect_definition_status"] == "DEFINED_IN_ENTRYPOINT_CLOSURE",
            f"invalid dialect status for {row['entity_name']}",
            failures,
        )
        require(
            row["static_source_reference_status"] in allowed_static,
            f"invalid static status for {row['entity_name']}",
            failures,
        )
        require(
            row["default_runtime_observation_status"] == "NOT_RUN_NO_CAPTURE",
            f"unsupported runtime claim for {row['entity_name']}",
            failures,
        )
        require(
            not row["default_runtime_observation_evidence"],
            f"runtime evidence unexpectedly populated for {row['entity_name']}",
            failures,
        )
    checks.append("static support matrix separates definition/static evidence and makes no runtime claim")

    runtime_overlay_summary: dict[str, Any] = {}
    runtime_overlay_failure_start = len(failures)
    apply_script = WORKSPACE / "benchmark" / "scripts" / "apply_runtime_catalog.py"
    apply_env = os.environ.copy()
    apply_env["PYTHONDONTWRITEBYTECODE"] = "1"
    overlay_check = subprocess.run(
        [sys.executable, "-B", str(apply_script), "--check"],
        cwd=WORKSPACE,
        env=apply_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        overlay_check.returncode == 0,
        "runtime overlay --check failed: "
        + (overlay_check.stderr.strip() or overlay_check.stdout.strip()),
        failures,
    )
    if overlay_check.returncode == 0:
        try:
            runtime_overlay_summary = json.loads(overlay_check.stdout)
        except json.JSONDecodeError as error:
            failures.append(f"runtime overlay --check did not emit JSON: {error}")

    runtime_rows = read_csv("actual_support_matrix.csv")
    runtime_json = read_json("actual_support_matrix.json")
    runtime_manifest = read_json("runtime_catalog_manifest.json")
    require(len(runtime_rows) == 1310, "runtime overlay CSV must contain 1310 data rows", failures)
    require(
        runtime_json.get("profile_count") == 4
        and runtime_json.get("primary_static_definition_row_count") == 1307
        and runtime_json.get("supplemental_non_catalog_observation_row_count") == 3
        and runtime_json.get("total_row_count") == 1310,
        "runtime overlay JSON count contract differs from 4 profiles / 1307+3 rows",
        failures,
    )
    require(
        runtime_json.get("implementation_satisfaction") == "NOT_ASSESSED",
        "runtime overlay contains an implementation-satisfaction conclusion",
        failures,
    )
    runtime_json_rows = runtime_json.get("rows", [])
    require(
        len(runtime_json_rows) == len(runtime_rows) == runtime_json.get("total_row_count"),
        "runtime overlay CSV/JSON row counts differ",
        failures,
    )
    scopes = Counter(row.get("row_scope") for row in runtime_json_rows)
    require(
        scopes
        == Counter(
            {
                "PROFILE_STATIC_MESSAGE_DEFINITION": 1307,
                "RUNTIME_NON_CATALOG_OBSERVATION": 3,
            }
        ),
        f"runtime overlay row_scope distribution mismatch: {dict(scopes)}",
        failures,
    )
    primary_runtime_rows = [
        row
        for row in runtime_json_rows
        if row.get("row_scope") == "PROFILE_STATIC_MESSAGE_DEFINITION"
    ]
    supplemental_runtime_rows = [
        row
        for row in runtime_json_rows
        if row.get("row_scope") == "RUNTIME_NON_CATALOG_OBSERVATION"
    ]
    require(
        len({row.get("capture_id") for row in primary_runtime_rows}) == 4,
        "runtime overlay does not contain exactly four profiles",
        failures,
    )
    require(
        all(
            row.get("static_requestable_evidence_status")
            == "UNKNOWN_NO_EXPLICIT_REQUESTABILITY_FIELD_IN_STATIC_CATALOG"
            for row in primary_runtime_rows
        ),
        "runtime overlay inferred static requestability",
        failures,
    )
    auxiliary_rows = [
        row
        for row in primary_runtime_rows
        if row.get("request_dialect_definition_status")
        == "DEFINED_ONLY_IN_AUXILIARY_DIALECT"
    ]
    require(
        len(auxiliary_rows) == 8
        and all(
            row.get("catalog_dialect_entrypoints") == "uAvionix.xml"
            and not row.get("request_attempted")
            and row.get("request_sweep_membership_status")
            == "AUXILIARY_DIALECT_NOT_IN_REQUEST_SWEEP"
            for row in auxiliary_rows
        ),
        "PX4 auxiliary-dialect preservation mismatch",
        failures,
    )
    require(
        len(supplemental_runtime_rows) == 3
        and all(
            row.get("message_id") == -1 and row.get("message_name") == "BAD_DATA"
            for row in supplemental_runtime_rows
        ),
        "non-catalog BAD_DATA preservation mismatch",
        failures,
    )
    require(
        all(
            "NOT_UNSUPPORTED_EVIDENCE" in row.get("request_ack_interpretation", "")
            for row in primary_runtime_rows
            if row.get("request_ack_result")
            in {"MAV_RESULT_DENIED", "MAV_RESULT_FAILED"}
        ),
        "DENIED/FAILED ACK was converted into unsupported evidence",
        failures,
    )
    require(
        all(
            row.get("zero_baseline_interpretation")
            == "NOT_OBSERVED_IN_BASELINE_NOT_UNSUPPORTED_EVIDENCE"
            for row in primary_runtime_rows
            if int(row.get("baseline_count", 0)) == 0
        ),
        "zero baseline was converted into unsupported evidence",
        failures,
    )

    require(
        runtime_manifest.get("profile_count") == 4
        and runtime_manifest.get("primary_static_definition_row_count") == 1307
        and runtime_manifest.get("supplemental_non_catalog_observation_row_count") == 3
        and runtime_manifest.get("total_row_count") == 1310
        and runtime_manifest.get("implementation_satisfaction") == "NOT_ASSESSED",
        "runtime catalog manifest count/status contract mismatch",
        failures,
    )
    generator = runtime_manifest.get("generator", {})
    require(
        generator.get("path") == "benchmark/scripts/apply_runtime_catalog.py"
        and generator.get("sha256") == sha256(apply_script),
        "runtime catalog generator provenance mismatch",
        failures,
    )
    for item in runtime_manifest.get("inputs", []):
        path = WORKSPACE / item["path"]
        require(path.is_file(), f"missing runtime catalog input {item['path']}", failures)
        if path.is_file():
            require(
                sha256(path) == item["sha256"],
                f"runtime catalog input hash mismatch: {item['path']}",
                failures,
            )
    for path_value, item in runtime_manifest.get("outputs", {}).items():
        path = WORKSPACE / path_value
        require(path.is_file(), f"missing runtime catalog output {path_value}", failures)
        if path.is_file():
            require(
                sha256(path) == item["sha256"],
                f"runtime catalog output hash mismatch: {path_value}",
                failures,
            )
            require(
                item.get("data_rows") == 1310,
                f"runtime catalog output row metadata mismatch: {path_value}",
                failures,
            )
    checks.append(
        "runtime overlay rebuilds byte-identically and validates 4 profiles, 1307+3 rows, provenance, auxiliary dialects, and NOT_ASSESSED"
    )
    saved_runtime_overlay_validated = len(failures) == runtime_overlay_failure_start

    message_field_keys = {
        (row["system"], row["message_name"], row["field_name"]) for row in message_rows
    }
    command_param_keys = {
        (row["system"], row["command_name"], row["param_index"]) for row in command_rows
    }
    parameter_time_keys = {
        (row["system"], row["vehicle_scope"], row["name"]) for row in parameter_rows
    }
    allowed_clock_explicit = {"true", "false"}
    for row in time_rows:
        require(
            row["runtime_observation_status"] == "NOT_RUN_NO_CAPTURE",
            f"time row makes runtime claim: {row['item_name']}",
            failures,
        )
        require(
            row["clock_semantics_explicit_in_definition"] in allowed_clock_explicit,
            f"invalid explicit-clock flag: {row['item_name']}",
            failures,
        )
        if row["entity_kind"] == "message_field":
            require(
                (row["system"], row["container_name"], row["item_name"])
                in message_field_keys,
                f"orphan time message field: {row['container_name']}.{row['item_name']}",
                failures,
            )
        elif row["entity_kind"] == "command_param":
            require(
                (row["system"], row["container_name"], row["item_position"])
                in command_param_keys,
                f"orphan time command param: {row['container_name']}[{row['item_position']}]",
                failures,
            )
        elif row["entity_kind"] == "configuration_parameter":
            require(
                (row["system"], row["container_name"], row["item_name"])
                in parameter_time_keys,
                f"orphan time configuration parameter: {row['item_name']}",
                failures,
            )
        else:
            failures.append(f"unknown time entity kind: {row['entity_kind']}")
        if row["clock_domain"].startswith("ambiguous"):
            require(bool(row["ambiguity"]), f"ambiguous clock lacks reason: {row['item_name']}", failures)
    checks.append("every time row resolves to a catalog row and ambiguous clocks carry a reason")

    observed_counts: dict[str, Any] = {}
    for system in ("ArduPilot", "PX4"):
        observed_counts[system] = {
            "messages": sum(row["system"] == system for row in json_messages),
            "message_fields": sum(
                len(row["fields"]) for row in json_messages if row["system"] == system
            ),
            "commands": sum(row["system"] == system for row in json_commands),
            "command_param_slots": sum(
                len(row["params"]) for row in json_commands if row["system"] == system
            ),
            "configuration_parameter_rows": sum(
                row["system"] == system for row in json_parameters
            ),
            "time_catalog_rows": sum(row["system"] == system for row in time_rows),
            "runtime_observed_entities": 0,
        }
        for key, value in observed_counts[system].items():
            require(
                manifest["counts"][system][key] == value,
                f"manifest count mismatch: {system} {key}",
                failures,
            )
    checks.append("manifest entity counts recompute from output files")

    report = {
        "schema_version": "1.0",
        "status": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "recomputed_counts": observed_counts,
        "runtime_execution_or_capture_performed": False,
        "saved_runtime_overlay_validated": saved_runtime_overlay_validated,
        "runtime_overlay_summary": runtime_overlay_summary,
        "generated_header_crosscheck": generated_header_check,
    }
    (CATALOG_DIR / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
