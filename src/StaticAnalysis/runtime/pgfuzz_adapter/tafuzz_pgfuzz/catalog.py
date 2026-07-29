from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping

from .common import (
    ADAPTER_ROOT,
    ARDUPILOT_ROOT,
    PGFUZZ_ROOT,
    WORKSPACE,
    git_head,
    load_json,
    run_text,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
    write_lines,
)
from .vehicle import SITLSession


INPUT_CATALOG_FIELDS = [
    "input_id", "input_type", "name", "protocol_field", "transport", "numeric_id",
    "value_type", "current_value", "units", "range_low", "range_high",
    "values", "mutation_values", "execution_class", "execution_reason",
    "reboot_required", "read_only", "metadata_status", "source_evidence",
    "recovery_strategy",
]

MIGRATION_FIELDS = [
    "legacy_kind", "legacy_name", "legacy_value", "migration_status",
    "current_names", "reason",
]


def truthy_metadata(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "required"}


def flatten_parameter_metadata(document: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    for group_name, group in document.items():
        if not isinstance(group, Mapping):
            continue
        for name, metadata in group.items():
            if not isinstance(metadata, Mapping):
                continue
            candidate = dict(metadata)
            candidate["MetadataGroup"] = str(group_name)
            previous = flattened.get(str(name))
            if previous is None or len(candidate) > len(previous):
                flattened[str(name)] = candidate
    return flattened


def metadata_range(metadata: Mapping[str, Any]) -> tuple[Any, Any]:
    value = metadata.get("Range")
    if isinstance(value, Mapping):
        return value.get("low"), value.get("high")
    return None, None


def numeric(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def mutation_values(name: str, current: Any, metadata: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    enum_values = metadata.get("Values")
    if isinstance(enum_values, Mapping):
        values.extend(numeric(key) for key in enum_values)
    low, high = metadata_range(metadata)
    low_number, high_number = numeric(low), numeric(high)
    increment = numeric(metadata.get("Increment"))
    current_number = numeric(current)
    values.extend([low_number, high_number])
    if current_number is not None and increment is not None:
        values.extend([current_number - increment, current_number + increment])
    if name == "SIM_BATT_VOLTAGE":
        # The runtime recipe derives a lower value from current battery failsafe
        # thresholds; this marker prevents an arbitrary voltage constant here.
        return ["DERIVE_SAFE_LOWER_FROM_BATTERY_THRESHOLDS"]
    result: list[Any] = []
    for value in values:
        if value is None or value == current_number or value in result:
            continue
        if low_number is not None and isinstance(value, (int, float)) and value < low_number:
            continue
        if high_number is not None and isinstance(value, (int, float)) and value > high_number:
            continue
        result.append(value)
    return result


def parameter_execution_class(name: str, metadata: Mapping[str, Any],
                              mutations: list[Any], policy: Mapping[str, Any]) -> tuple[str, str]:
    if truthy_metadata(metadata.get("ReadOnly")):
        return "DISRUPTIVE_EXCLUDED", "current source metadata marks the parameter read-only"
    if truthy_metadata(metadata.get("RebootRequired")):
        return "REQUIRES_RESTART", "current source metadata requires reboot"
    if any(name == prefix or name.startswith(prefix)
           for prefix in policy["continuity_critical_parameter_prefixes"]):
        return "REQUIRES_RESTART", "parameter may change link, identity, board, or storage continuity"
    if not metadata:
        return "UNKNOWN_METADATA", "runtime parameter has no matching current source metadata"
    if not mutations:
        return "UNKNOWN_METADATA", "no bounded mutation value can be derived from current metadata"
    return "READY_SAFE", "bounded current-source mutation and direct parameter rollback are available"


def merge_parameters(snapshot: Mapping[str, Any], metadata_doc: Mapping[str, Any],
                     policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    if snapshot.get("status") != "COMPLETE":
        raise ValueError("runtime parameter snapshot is not COMPLETE")
    parameters = list(snapshot.get("parameters", []))
    expected = snapshot.get("expected_count")
    indices = {int(row["param_index"]) for row in parameters}
    names = {str(row["name"]) for row in parameters}
    if expected != len(indices) or len(names) != len(parameters):
        raise ValueError(
            f"runtime parameter completeness mismatch: expected={expected}, "
            f"indices={len(indices)}, names={len(names)}, rows={len(parameters)}")
    metadata = flatten_parameter_metadata(metadata_doc)
    rows: list[dict[str, Any]] = []
    for parameter in sorted(parameters, key=lambda row: str(row["name"])):
        name = str(parameter["name"])
        info = metadata.get(name, {})
        low, high = metadata_range(info)
        mutations = mutation_values(name, parameter.get("decoded_value"), info)
        execution_class, reason = parameter_execution_class(
            name, info, mutations, policy)
        input_type = "INPUT_E" if name.startswith("SIM_") else "INPUT_P"
        rows.append({
            "input_id": f"{input_type}:{name}",
            "input_type": input_type,
            "name": name,
            "transport": "PARAM_SET",
            "numeric_id": None,
            "value_type": parameter.get("param_type_name"),
            "current_value": parameter.get("decoded_value"),
            "units": info.get("Units"),
            "range_low": low,
            "range_high": high,
            "values": info.get("Values") or info.get("Bitmask") or {},
            "mutation_values": mutations,
            "execution_class": execution_class,
            "execution_reason": reason,
            "reboot_required": truthy_metadata(info.get("RebootRequired")),
            "read_only": truthy_metadata(info.get("ReadOnly")),
            "metadata_status": "CURRENT_SOURCE_METADATA" if info else "NO_CURRENT_METADATA",
            "source_evidence": {
                "runtime_param_index": parameter.get("param_index"),
                "runtime_param_count": parameter.get("param_count"),
                "metadata_group": info.get("MetadataGroup"),
                "display_name": info.get("DisplayName"),
                "description": info.get("Description"),
            },
            "recovery_strategy": "PARAM_SET_ORIGINAL_VALUE_AND_READBACK",
        })
    return rows


def extract_source_command_names(ardupilot_root: Path = ARDUPILOT_ROOT) -> dict[str, list[str]]:
    roots = [ardupilot_root / "ArduCopter", ardupilot_root / "libraries/GCS_MAVLink"]
    command_re = re.compile(r"\bcase\s+(MAV_CMD_[A-Z0-9_]+)\s*:")
    evidence: dict[str, list[str]] = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".cpp", ".h"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in command_re.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                relative = path.relative_to(ardupilot_root).as_posix()
                evidence.setdefault(match.group(1), []).append(f"{relative}:{line}")
    return {name: sorted(set(locations)) for name, locations in evidence.items()}


def load_mavlink_commands(path: Path) -> dict[str, dict[str, Any]]:
    document = load_json(path)
    result: dict[str, dict[str, Any]] = {}
    for system in document.get("systems", []):
        for command in system.get("commands", []):
            if command.get("system") != "ArduPilot":
                continue
            result[str(command["name"])] = dict(command)
    return result


def command_rows(mode_mapping: Mapping[str, int], parameter_rows: Iterable[Mapping[str, Any]],
                 policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    definition_path = WORKSPACE / "benchmark/mavlink_catalog/commands.json"
    definitions = load_mavlink_commands(definition_path)
    evidence = extract_source_command_names()
    names = sorted(set(definitions) & set(evidence))
    blocked = set(policy["disruptive_commands"])
    ready = set(policy["ready_command_recipes"])
    rows: list[dict[str, Any]] = []
    for name in names:
        definition = definitions[name]
        if name in blocked:
            execution_class = "DISRUPTIVE_EXCLUDED"
            reason = "command is process-, storage-, boot-, or flight-continuity disruptive"
        elif name in ready:
            execution_class = "READY_SAFE"
            reason = "typed current-version command recipe is implemented"
        else:
            execution_class = "REQUIRES_PRECONDITION"
            reason = "source handler exists but a safe typed runtime recipe or device precondition is required"
        rows.append({
            "input_id": f"INPUT_C:{name}",
            "input_type": "INPUT_C",
            "name": name,
            "transport": "COMMAND_INT" if str(definition.get("has_location", "")).lower() == "true" else "COMMAND_LONG",
            "numeric_id": int(definition["command_id"]),
            "value_type": "MAV_CMD",
            "current_value": None,
            "units": None,
            "range_low": None,
            "range_high": None,
            "values": definition.get("params", []),
            "mutation_values": [],
            "execution_class": execution_class,
            "execution_reason": reason,
            "reboot_required": False,
            "read_only": False,
            "metadata_status": "CURRENT_XML_AND_SOURCE_HANDLER",
            "source_evidence": evidence[name],
            "recovery_strategy": "RECIPE_SPECIFIC_STATE_RESTORE_OR_RESTART",
        })

    parameter_map = {str(row["name"]): row for row in parameter_rows}
    active_channels = {1, 2, 3, 4}
    for parameter_name in ["RCMAP_ROLL", "RCMAP_PITCH", "RCMAP_THROTTLE", "RCMAP_YAW"]:
        value = numeric(parameter_map.get(parameter_name, {}).get("current_value"))
        if isinstance(value, int) and 1 <= value <= 18:
            active_channels.add(value)
    for channel in sorted(active_channels):
        name = f"RC{channel}"
        rows.append({
            "input_id": f"INPUT_C:{name}", "input_type": "INPUT_C",
            # Keep PGFuzz's RC1-style compatibility name in text files while
            # retaining the exact current MAVLink message field identity here.
            "name": name,
            "protocol_field": f"RC_CHANNELS_OVERRIDE.chan{channel}_raw",
            "transport": "RC_CHANNELS_OVERRIDE", "numeric_id": 0,
            "value_type": "PWM_US", "current_value": 1500, "units": "us",
            "range_low": 1000, "range_high": 2000, "values": {},
            "mutation_values": [1000, 1500, 2000], "execution_class": "READY_SAFE",
            "execution_reason": "active pilot-control channel derived from current RCMAP parameters",
            "reboot_required": False, "read_only": False,
            "metadata_status": "CURRENT_RUNTIME_RCMAP",
            "source_evidence": ["MAVLink RC_CHANNELS_OVERRIDE", *sorted(
                name for name in parameter_map if name.startswith("RCMAP_"))],
            "recovery_strategy": "RC_CHANNEL_OVERRIDE_RELEASE",
        })
    for mode_name, mode_number in sorted(mode_mapping.items(), key=lambda item: item[1]):
        name = f"Flight_Mode_{mode_name}"
        rows.append({
            "input_id": f"INPUT_C:{name}", "input_type": "INPUT_C",
            "name": name, "transport": "SET_MODE", "numeric_id": int(mode_number),
            "value_type": "CUSTOM_MODE", "current_value": None, "units": None,
            "range_low": None, "range_high": None, "values": {},
            "mutation_values": [int(mode_number)], "execution_class": "READY_SAFE",
            "execution_reason": "mode is advertised by the current ArduCopter mode mapping",
            "reboot_required": False, "read_only": False,
            "metadata_status": "CURRENT_RUNTIME_MODE_MAPPING",
            "source_evidence": ["HEARTBEAT vehicle type and pymavlink mode mapping"],
            "recovery_strategy": "SET_MODE_PREVIOUS_AND_CONFIRM_HEARTBEAT",
        })
    return sorted(rows, key=lambda row: (str(row["name"]), str(row["transport"])))


def parse_legacy_inputs(pg_root: Path = PGFUZZ_ROOT) -> list[dict[str, Any]]:
    root = pg_root / "ArduPilot/Dynamic analysis"
    rows: list[dict[str, Any]] = []
    for line in (root / "cmds.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        name, value = line.split(",", 1)
        rows.append({"legacy_kind": "COMMAND", "legacy_name": name.strip(),
                     "legacy_value": value.strip()})
    for line in (root / "envs.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append({"legacy_kind": "ENVIRONMENT", "legacy_name": line.strip(),
                         "legacy_value": ""})
    for line in (root / "preconditions.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            name, value = line.split(None, 1)
            rows.append({"legacy_kind": "PRECONDITION", "legacy_name": name,
                         "legacy_value": value})
    return rows


def migration_rows(legacy: Iterable[Mapping[str, Any]], current_rows: Iterable[Mapping[str, Any]],
                   policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    current_names = {str(row["name"]) for row in current_rows}
    aliases = policy.get("legacy_parameter_aliases", {})
    rows: list[dict[str, Any]] = []
    for item in legacy:
        name = str(item["legacy_name"])
        if name in current_names:
            status, candidates, reason = "EXACT", [name], "same identifier exists in the current catalog"
        else:
            candidates = [candidate for candidate in aliases.get(name, [])
                          if candidate in current_names]
            if not candidates and name.startswith("SIM_GPS_"):
                suffix = name[len("SIM_GPS_"):]
                candidates = sorted(candidate for candidate in current_names
                                    if candidate.startswith("SIM_GPS") and candidate.endswith(suffix))
            if len(candidates) == 1:
                status, reason = "RENAMED", "one explicit current-version identity is available"
            elif len(candidates) > 1:
                status, reason = "AMBIGUOUS", "multiple current instance-specific identities match"
            else:
                status, reason = "REMOVED", "no current runtime/source identity was found"
        rows.append({
            "legacy_kind": item["legacy_kind"], "legacy_name": name,
            "legacy_value": item.get("legacy_value", ""),
            "migration_status": status, "current_names": candidates,
            "reason": reason,
        })
    return rows


def generate_metadata(output_dir: Path) -> Path:
    metadata_dir = output_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    script = ARDUPILOT_ROOT / "Tools/autotest/param_metadata/param_parse.py"
    result = run_text([
        sys.executable, str(script), "--vehicle", "Copter", "--format", "json",
        "--no-legacy-params",
    ], cwd=metadata_dir)
    write_json(metadata_dir / "generation_command.json", result)
    if result["exit_code"] != 0:
        raise RuntimeError(f"parameter metadata generation failed: {result['stderr']}")
    path = metadata_dir / "apm.pdef.json"
    if not path.is_file():
        raise RuntimeError("parameter metadata generator did not create apm.pdef.json")
    return path


def offline_mode_mapping() -> dict[str, int]:
    text = (ARDUPILOT_ROOT / "ArduCopter/mode.h").read_text(
        encoding="utf-8", errors="replace")
    match = re.search(r"enum\s+class\s+Number[^\{]*\{(?P<body>.*?)\};", text, re.S)
    if not match:
        raise RuntimeError("unable to parse ArduCopter Mode::Number")
    result: dict[str, int] = {}
    for name, value in re.findall(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*,", match.group("body"), re.M):
        result[name] = int(value)
    return result


def write_compatibility_inputs(run_dir: Path, rows: list[dict[str, Any]],
                               migrations: list[dict[str, Any]]) -> None:
    commands = [row for row in rows if row["input_type"] == "INPUT_C"]
    parameters = [row for row in rows if row["input_type"] == "INPUT_P"]
    environments = [row for row in rows if row["input_type"] == "INPUT_E"]
    write_lines(run_dir / "cmds.txt", [f"{row['name']},{row['numeric_id'] or 0}"
                                       for row in commands])
    write_lines(run_dir / "params.txt", [str(row["name"]) for row in parameters])
    write_lines(run_dir / "envs.txt", [str(row["name"]) for row in environments])
    precondition_lines = []
    for migration in migrations:
        if migration["legacy_kind"] != "PRECONDITION" or \
                migration["migration_status"] not in {"EXACT", "RENAMED"}:
            continue
        for current_name in migration["current_names"]:
            precondition_lines.append(f"{current_name} {migration['legacy_value']}")
    write_lines(run_dir / "preconditions.txt", precondition_lines)


def build_catalog(run_dir: Path, parameter_snapshot: Path | None = None,
                  metadata_json: Path | None = None, udp_port: int = 19401,
                  param_timeout: float = 120.0) -> dict[str, Any]:
    policy = load_json(ADAPTER_ROOT / "data/safety_policy.json")
    live = parameter_snapshot is None
    session: SITLSession | None = None
    if live:
        session = SITLSession(run_dir, udp_port=udp_port)
        try:
            session.start()
            snapshot = session.download_parameters(timeout=param_timeout)
            modes = session.mode_mapping()
        finally:
            session.stop()
    else:
        snapshot = load_json(parameter_snapshot)
        modes = offline_mode_mapping()
        write_json(run_dir / "parameters_runtime.json", snapshot)
    metadata_path = metadata_json or generate_metadata(run_dir)
    metadata = load_json(metadata_path)
    parameters = merge_parameters(snapshot, metadata, policy)
    commands = command_rows(modes, parameters, policy)
    rows = sorted([*parameters, *commands],
                  key=lambda row: (row["input_type"], row["name"], row["transport"]))
    legacy = parse_legacy_inputs()
    migrations = migration_rows(legacy, rows, policy)
    write_json(run_dir / "input_catalog.json", {
        "schema_version": "1.0", "generated_at": utc_now(),
        "catalog_status": "COMPLETE", "inputs": rows,
    })
    write_csv(run_dir / "input_catalog.csv", rows, INPUT_CATALOG_FIELDS)
    write_json(run_dir / "migration_report.json", {
        "schema_version": "1.0", "rows": migrations,
    })
    write_csv(run_dir / "migration_report.csv", migrations, MIGRATION_FIELDS)
    write_compatibility_inputs(run_dir, rows, migrations)
    manifest = {
        "schema_version": "1.0", "generated_at": utc_now(),
        "command": "catalog", "live_parameter_download": live,
        "target": {
            "ardupilot_commit": git_head(ARDUPILOT_ROOT),
            "mavlink_commit": git_head(ARDUPILOT_ROOT / "modules/mavlink"),
            "binary": str(ARDUPILOT_ROOT / "build/sitl/bin/arducopter"),
            "binary_sha256": sha256_file(ARDUPILOT_ROOT / "build/sitl/bin/arducopter"),
        },
        "sources": {
            "parameter_snapshot": str(parameter_snapshot) if parameter_snapshot else "LIVE_SITL",
            "parameter_metadata": str(metadata_path),
            "command_definitions": str(WORKSPACE / "benchmark/mavlink_catalog/commands.json"),
            "legacy_pg_fuzz": str(PGFUZZ_ROOT / "ArduPilot/Dynamic analysis"),
        },
        "counts": {
            "runtime_parameters": len(parameters),
            "input_p": sum(row["input_type"] == "INPUT_P" for row in rows),
            "input_c": sum(row["input_type"] == "INPUT_C" for row in rows),
            "input_e": sum(row["input_type"] == "INPUT_E" for row in rows),
            "ready_safe": sum(row["execution_class"] == "READY_SAFE" for row in rows),
            "migration_rows": len(migrations),
        },
    }
    write_json(run_dir / "manifest.json", manifest)
    return {"manifest": manifest, "inputs": rows, "migrations": migrations}
