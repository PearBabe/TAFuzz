#!/usr/bin/env python3
"""Generate an auditable MAVLink/parameter catalog from the frozen worktrees.

The generator deliberately keeps three evidence levels separate:

1. XML dialect definition closure (what headers can define),
2. heuristic production-source references (what the frozen source mentions), and
3. runtime observation (not performed by this generator).

It writes only next to this script.  No source worktree is modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


CATALOG_DIR = Path(__file__).resolve().parent
WORKSPACE = CATALOG_DIR.parents[1]
AP_ROOT = WORKSPACE / "baseline" / "ardupilot"
PX4_ROOT = WORKSPACE / "baseline" / "px4"
FREEZE_MANIFEST = WORKSPACE / "benchmark" / "source_freeze_manifest.json"

EXPECTED = {
    "ArduPilot": {
        "sut_commit": "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
        "mavlink_commit": "13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472",
    },
    "PX4": {
        "sut_commit": "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
        "mavlink_commit": "33af200d25ec6f0925b49b1ba82bbf1294ea5f72",
    },
}

SYSTEMS = {
    "ArduPilot": {
        "root": AP_ROOT,
        "mavlink_root": AP_ROOT / "modules" / "mavlink",
        "xml_dir": AP_ROOT / "modules" / "mavlink" / "message_definitions" / "v1.0",
        "entrypoints": [
            {
                "file": "all.xml",
                "role": "primary_build_entrypoint",
                "evidence": "baseline/ardupilot/wscript:781-783",
            }
        ],
        "vehicle_scopes": ["Copter", "Plane", "Rover"],
        "source_roots": ["ArduCopter", "ArduPlane", "Rover", "libraries"],
        "source_excludes": {"build", "modules", ".git", "tests", "test", "examples"},
    },
    "PX4": {
        "root": PX4_ROOT,
        "mavlink_root": PX4_ROOT / "src" / "modules" / "mavlink" / "mavlink",
        "xml_dir": PX4_ROOT
        / "src"
        / "modules"
        / "mavlink"
        / "mavlink"
        / "message_definitions"
        / "v1.0",
        "entrypoints": [
            {
                "file": "development.xml",
                "role": "primary_px4_sitl_default",
                "evidence": "baseline/px4/boards/px4/sitl/default.px4board:38; "
                "baseline/px4/src/modules/mavlink/CMakeLists.txt:61-77",
            },
            {
                "file": "uAvionix.xml",
                "role": "auxiliary_always_generated",
                "evidence": "baseline/px4/src/modules/mavlink/CMakeLists.txt:40-57",
            },
        ],
        "vehicle_scopes": ["multicopter_SITL"],
        "source_roots": ["src"],
        "source_excludes": {
            "build",
            ".git",
            "test",
            "tests",
            "examples",
        },
    },
}

SOURCE_EXTENSIONS = {".c", ".cc", ".cpp", ".h", ".hh", ".hpp"}
TYPE_SIZES = {
    "char": 1,
    "int8_t": 1,
    "uint8_t": 1,
    "uint8_t_mavlink_version": 1,
    "int16_t": 2,
    "uint16_t": 2,
    "int32_t": 4,
    "uint32_t": 4,
    "float": 4,
    "int64_t": 8,
    "uint64_t": 8,
    "double": 8,
}

OUTPUT_FILES = [
    "messages_and_fields.csv",
    "messages_and_fields.json",
    "commands.csv",
    "commands.json",
    "configuration_parameters.csv",
    "configuration_parameters.json",
    "static_support_matrix.csv",
    "time_fields.csv",
]


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, ET.Element):
        value = "".join(value.itertext())
    return " ".join(str(value).split())


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def assert_frozen_inputs() -> dict[str, Any]:
    freeze = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
    checks = {
        "ArduPilot": {
            "sut_commit": git_head(AP_ROOT),
            "mavlink_commit": git_head(AP_ROOT / "modules" / "mavlink"),
        },
        "PX4": {
            "sut_commit": git_head(PX4_ROOT),
            "mavlink_commit": git_head(
                PX4_ROOT / "src" / "modules" / "mavlink" / "mavlink"
            ),
        },
    }
    for system, observed in checks.items():
        for key, value in observed.items():
            expected = EXPECTED[system][key]
            if value != expected:
                raise RuntimeError(
                    f"Frozen input mismatch: {system} {key}: {value} != {expected}"
                )
    return freeze


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def xml_closure(xml_dir: Path, entrypoint: str) -> tuple[list[Path], dict[str, list[str]]]:
    ordered: list[Path] = []
    chains: dict[str, list[str]] = {}
    queue: list[tuple[Path, list[str]]] = [(xml_dir / entrypoint, [entrypoint])]
    seen: set[Path] = set()
    while queue:
        path, chain = queue.pop(0)
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"XML include missing: {path}")
        key = path.name
        if key not in chains or len(chain) < len(chains[key]):
            chains[key] = chain
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
        root = ET.parse(path).getroot()
        for include in root.findall("include"):
            include_name = norm_text(include)
            queue.append((path.parent / include_name, chain + [include_name]))
    return ordered, chains


def parse_type(raw_type: str) -> tuple[str, int]:
    match = re.fullmatch(r"([^\[]+)(?:\[(\d+)\])?", raw_type.strip())
    if not match:
        raise ValueError(f"Unsupported MAVLink XML type: {raw_type}")
    return match.group(1), int(match.group(2) or 0)


def element_status(element: ET.Element) -> dict[str, str]:
    deprecated = element.find("deprecated")
    superseded = element.find("superseded")
    wip = element.find("wip")
    return {
        "deprecated_since": deprecated.get("since", "") if deprecated is not None else "",
        "replaced_by": deprecated.get("replaced_by", "") if deprecated is not None else "",
        "deprecation_explanation": norm_text(deprecated),
        "superseded_since": superseded.get("since", "") if superseded is not None else "",
        "superseded_by": superseded.get("replaced_by", "") if superseded is not None else "",
        "supersession_explanation": norm_text(superseded),
        "wip": "true" if wip is not None else "false",
    }


def find_xml_line(path: Path, tag: str, name: str) -> int:
    pattern = re.compile(
        rf"<{re.escape(tag)}\b[^>]*\bname\s*=\s*(['\"]){re.escape(name)}\1"
    )
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if pattern.search(line):
            return number
    return 0


def find_field_line(path: Path, message_name: str, field_name: str) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_message = False
    message_pattern = re.compile(
        rf"<message\b[^>]*\bname\s*=\s*(['\"]){re.escape(message_name)}\1"
    )
    field_pattern = re.compile(
        rf"<field\b[^>]*\bname\s*=\s*(['\"]){re.escape(field_name)}\1"
    )
    for number, line in enumerate(lines, 1):
        if not in_message and message_pattern.search(line):
            in_message = True
        elif in_message and "</message>" in line:
            break
        elif in_message and field_pattern.search(line):
            return number
    return 0


def assign_wire_layout(fields: list[dict[str, Any]]) -> tuple[int, int]:
    base = [field for field in fields if not field["extension"]]
    extension = [field for field in fields if field["extension"]]
    # MAVLink C generators stably sort base fields by primitive size, descending.
    ordered = sorted(base, key=lambda item: item["primitive_size"], reverse=True)
    ordered.extend(extension)
    offset = 0
    for order, field in enumerate(ordered, 1):
        field["payload_wire_order"] = order
        field["payload_wire_offset"] = offset
        offset += field["payload_size"]
    min_length = sum(field["payload_size"] for field in base)
    return min_length, offset


def parse_system_xml(system: str, spec: dict[str, Any]) -> dict[str, Any]:
    entry_closures: dict[str, list[Path]] = {}
    include_chains: dict[str, dict[str, list[str]]] = {}
    file_roles: dict[Path, set[str]] = defaultdict(set)
    for entry in spec["entrypoints"]:
        files, chains = xml_closure(spec["xml_dir"], entry["file"])
        entry_closures[entry["file"]] = files
        include_chains[entry["file"]] = chains
        for path in files:
            file_roles[path].add(entry["file"])

    messages_by_id: dict[int, dict[str, Any]] = {}
    message_names: dict[str, int] = {}
    commands_by_id: dict[int, dict[str, Any]] = {}
    command_names: dict[str, int] = {}

    for path in sorted(file_roles, key=lambda item: item.name.lower()):
        root = ET.parse(path).getroot()
        origin = rel(path)
        entrypoints = sorted(file_roles[path])
        for message in root.findall("./messages/message"):
            message_id = int(message.get("id", ""))
            name = message.get("name", "")
            if message_id in messages_by_id or name in message_names:
                prior = messages_by_id.get(message_id)
                if prior and prior["name"] == name and prior["origin_xml"] == origin:
                    prior["dialect_entrypoints"] = sorted(
                        set(prior["dialect_entrypoints"]) | set(entrypoints)
                    )
                    continue
                raise RuntimeError(
                    f"Message definition collision in {system}: {message_id} {name}"
                )

            fields: list[dict[str, Any]] = []
            extension = False
            xml_order = 0
            for child in list(message):
                if child.tag == "extensions":
                    extension = True
                    continue
                if child.tag != "field":
                    continue
                xml_order += 1
                raw_type = child.get("type", "")
                primitive_type, array_length = parse_type(raw_type)
                if primitive_type not in TYPE_SIZES:
                    raise RuntimeError(
                        f"Unknown primitive type {primitive_type} in {origin}"
                    )
                primitive_size = TYPE_SIZES[primitive_type]
                field = {
                    "name": child.get("name", ""),
                    "type": raw_type,
                    "primitive_type": primitive_type,
                    "array_length": array_length,
                    "primitive_size": primitive_size,
                    "payload_size": primitive_size * (array_length or 1),
                    "xml_field_order": xml_order,
                    "payload_wire_order": 0,
                    "payload_wire_offset": 0,
                    "extension": extension,
                    "description": norm_text(child),
                    "enum": child.get("enum", ""),
                    "units": child.get("units", ""),
                    "display": child.get("display", ""),
                    "print_format": child.get("print_format", ""),
                    "default": child.get("default", ""),
                    "invalid": child.get("invalid", ""),
                    "instance": child.get("instance", ""),
                    "origin_xml": origin,
                    "origin_line": find_field_line(path, name, child.get("name", "")),
                    "xml_attributes": dict(sorted(child.attrib.items())),
                }
                fields.append(field)
            min_length, max_length = assign_wire_layout(fields)
            record = {
                "system": system,
                "message_id": message_id,
                "name": name,
                "description": norm_text(message.find("description")),
                "dialect_entrypoints": entrypoints,
                "origin_xml": origin,
                "origin_line": find_xml_line(path, "message", name),
                "payload_min_length": min_length,
                "payload_max_length": max_length,
                "fields": fields,
                **element_status(message),
            }
            messages_by_id[message_id] = record
            message_names[name] = message_id

        for enum in root.findall("./enums/enum"):
            if enum.get("name") != "MAV_CMD":
                continue
            for entry in enum.findall("entry"):
                command_id = int(entry.get("value", ""), 0)
                name = entry.get("name", "")
                if command_id in commands_by_id or name in command_names:
                    prior = commands_by_id.get(command_id)
                    if prior and prior["name"] == name and prior["origin_xml"] == origin:
                        prior["dialect_entrypoints"] = sorted(
                            set(prior["dialect_entrypoints"]) | set(entrypoints)
                        )
                        continue
                    raise RuntimeError(
                        f"MAV_CMD collision in {system}: {command_id} {name}"
                    )
                params_by_index: dict[int, list[ET.Element]] = defaultdict(list)
                for param in entry.findall("param"):
                    index = int(param.get("index", ""))
                    if index < 1 or index > 7:
                        raise RuntimeError(f"Invalid MAV_CMD param index: {name} {index}")
                    params_by_index[index].append(param)
                params: list[dict[str, Any]] = []
                for index in range(1, 8):
                    occurrences = params_by_index.get(index, [])
                    if not occurrences:
                        params.append(
                            {
                                "index": index,
                                "definition_status": "unspecified",
                                "xml_occurrence_count": 0,
                                "duplicate_details": [],
                                "label": "",
                                "description": "",
                                "units": "",
                                "enum": "",
                                "decimal_places": "",
                                "increment": "",
                                "min_value": "",
                                "max_value": "",
                                "default": "",
                                "reserved": "",
                            }
                        )
                        continue
                    param = occurrences[0]
                    reserved = param.get("reserved", "")
                    variants = [
                        {
                            "attributes": dict(sorted(item.attrib.items())),
                            "description": norm_text(item),
                        }
                        for item in occurrences
                    ]
                    if len(occurrences) > 1:
                        canonical = {
                            json.dumps(item, sort_keys=True, ensure_ascii=False)
                            for item in variants
                        }
                        status = (
                            "duplicate_identical_xml_entries"
                            if len(canonical) == 1
                            else "duplicate_conflicting_xml_entries"
                        )
                    else:
                        status = (
                            "reserved"
                            if reserved.lower() in {"true", "1", "yes"}
                            else "defined"
                        )
                    params.append(
                        {
                            "index": index,
                            "definition_status": status,
                            "xml_occurrence_count": len(occurrences),
                            "duplicate_details": variants if len(occurrences) > 1 else [],
                            "label": param.get("label", ""),
                            "description": norm_text(param),
                            "units": param.get("units", ""),
                            "enum": param.get("enum", ""),
                            "decimal_places": param.get("decimalPlaces", ""),
                            "increment": param.get("increment", ""),
                            "min_value": param.get("minValue", ""),
                            "max_value": param.get("maxValue", ""),
                            "default": param.get("default", ""),
                            "reserved": reserved,
                            "xml_attributes": dict(sorted(param.attrib.items())),
                        }
                    )
                record = {
                    "system": system,
                    "command_id": command_id,
                    "name": name,
                    "description": norm_text(entry.find("description")),
                    "has_location": entry.get("hasLocation", ""),
                    "is_destination": entry.get("isDestination", ""),
                    "mission_only": entry.get("missionOnly", ""),
                    "dialect_entrypoints": entrypoints,
                    "origin_xml": origin,
                    "origin_line": find_xml_line(path, "entry", name),
                    "params": params,
                    **element_status(entry),
                }
                commands_by_id[command_id] = record
                command_names[name] = command_id

    files = []
    for path in sorted(file_roles, key=lambda item: item.name.lower()):
        files.append(
            {
                "path": rel(path),
                "sha256": sha256(path),
                "reachable_from": sorted(file_roles[path]),
                "include_chains": {
                    entry: include_chains[entry].get(path.name, [])
                    for entry in sorted(include_chains)
                    if path.name in include_chains[entry]
                },
            }
        )

    return {
        "system": system,
        "sut_commit": EXPECTED[system]["sut_commit"],
        "mavlink_commit": EXPECTED[system]["mavlink_commit"],
        "definition_scope": "union_of_actual_build_entrypoint_include_closures",
        "dialect_entrypoints": spec["entrypoints"],
        "xml_files": files,
        "messages": [messages_by_id[key] for key in sorted(messages_by_id)],
        "commands": [commands_by_id[key] for key in sorted(commands_by_id)],
    }


def source_files_for(system: str, spec: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    root = spec["root"]
    for source_root in spec["source_roots"]:
        base = root / source_root
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            relative_parts = path.relative_to(root).parts
            if system == "PX4" and path.is_relative_to(spec["mavlink_root"]):
                continue
            if any(part in spec["source_excludes"] for part in relative_parts):
                continue
            files.append(path)
    return sorted(set(files))


def add_evidence(
    index: dict[str, dict[str, list[str]]], name: str, kind: str, location: str
) -> None:
    bucket = index[name][kind]
    if location not in bucket:
        bucket.append(location)


def scan_static_references(
    system: str, spec: dict[str, Any]
) -> tuple[dict[str, dict[str, list[str]]], dict[str, dict[str, list[str]]], int]:
    message_index: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    command_index: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    files = source_files_for(system, spec)
    macro_pattern = re.compile(r"\bMAVLINK_MSG_ID_([A-Z0-9_]+)\b")
    function_pattern = re.compile(
        r"\bmavlink_msg_([a-z0-9_]+)_"
        r"(send_struct|send_buf|send|pack_chan|pack|encode_chan|encode|decode)\b"
    )
    type_pattern = re.compile(r"\bmavlink_([a-z0-9_]+)_t\b")
    command_pattern = re.compile(r"\b(MAV_CMD_[A-Z0-9_]+)\b")

    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        path_rel = rel(path)
        is_px4_stream = system == "PX4" and "/mavlink/streams/" in path_rel
        is_receiver_file = "receiver" in path.name.lower() or "GCS_" in path.name
        for line_number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                # Comments are not implementation support evidence.
                continue
            location = f"{path_rel}:{line_number}"
            for match in macro_pattern.finditer(line):
                name = match.group(1)
                context = line.lower()
                if is_px4_stream:
                    kind = "tx"
                elif re.search(r"\bcase\s+MAVLINK_MSG_ID_", line) or (
                    is_receiver_file
                    and re.search(r"msgid|message|handle|decode", context)
                ):
                    kind = "rx"
                else:
                    kind = "other"
                add_evidence(message_index, name, kind, location)
            for match in function_pattern.finditer(line):
                name, operation = match.groups()
                upper_name = name.upper()
                kind = "rx" if operation == "decode" else "tx"
                add_evidence(message_index, upper_name, kind, location)
            for match in type_pattern.finditer(line):
                add_evidence(message_index, match.group(1).upper(), "other", location)
            for match in command_pattern.finditer(line):
                name = match.group(1)
                if re.search(rf"\bcase\s+{re.escape(name)}\b", line):
                    kind = "rx"
                elif re.search(r"\.command\s*=|command\s*=|send_command", line):
                    kind = "tx"
                else:
                    kind = "other"
                add_evidence(command_index, name, kind, location)
    return message_index, command_index, len(files)


AP_PARAM_START = re.compile(r"@Param(?:\{([^}]+)\})?:\s*([A-Za-z0-9_]+)")
AP_PARAM_FIELD = re.compile(r"@([A-Za-z][A-Za-z0-9_]*)(?:\{([^}]+)\})?:\s*(.*)")
PX4_PARAM_DEFINE = re.compile(
    r"\b(?:PX4_)?PARAM_DEFINE_([A-Z_][A-Z0-9_]*)\s*\(\s*([A-Z_][A-Z0-9_]*)"
    r"\s*(?:,\s*([^;]+?))?\s*\)\s*;"
)


def source_code_files(root: Path, extensions: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if any(part in {".git", "build"} for part in path.parts):
            continue
        yield path


def split_macro_arguments(text: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    depth = 0
    quote = ""
    escaped = False
    for char in text:
        if quote:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {'"', "'"}:
            quote = char
            current.append(char)
        elif char in "([{":
            depth += 1
            current.append(char)
        elif char in ")]}" and depth:
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    args.append("".join(current).strip())
    return args


def next_statement(lines: list[str], start: int) -> str:
    collected: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        collected.append(stripped)
        if ");" in stripped:
            break
        if len(collected) > 12:
            break
    return " ".join(collected)


def ap_default_from_statement(statement: str, local_name: str) -> str:
    match = re.search(r"\b([A-Z][A-Z0-9_]*)\s*\((.*)\)\s*;", statement)
    if not match:
        return ""
    macro, raw_args = match.groups()
    args = split_macro_arguments(raw_args)
    quoted_name_indices = [
        index
        for index, arg in enumerate(args)
        if arg.strip().strip('"') == local_name
    ]
    if not quoted_name_indices:
        return ""
    name_index = quoted_name_indices[0]
    if macro.startswith("GSCALAR") and len(args) > name_index + 1:
        return args[name_index + 1]
    if "GROUPINFO" in macro and len(args) >= 5:
        # Name, index, class, member, default, [flags...]
        return args[4]
    return ""


def index_ardupilot_param_sources() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    roots = [AP_ROOT / "ArduCopter", AP_ROOT / "ArduPlane", AP_ROOT / "Rover", AP_ROOT / "libraries"]
    for root in roots:
        for path in source_code_files(root, {".c", ".cc", ".cpp", ".h", ".hpp", ".lua"}):
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            for line_index, line in enumerate(lines):
                start = AP_PARAM_START.search(line)
                if not start:
                    continue
                local_name = start.group(2)
                tags: dict[str, list[str]] = defaultdict(list)
                for follow in lines[line_index + 1 : line_index + 40]:
                    if not follow.strip():
                        break
                    field = AP_PARAM_FIELD.search(follow)
                    if field:
                        tags[field.group(1)].append(norm_text(field.group(3)))
                    elif "@Param" in follow:
                        break
                    elif not re.match(r"\s*(?://|--|/\*|\*)", follow):
                        break
                statement = next_statement(lines, line_index + 1)
                index[local_name].append(
                    {
                        "path": rel(path),
                        "line": line_index + 1,
                        "location": f"{rel(path)}:{line_index + 1}",
                        "tags": dict(tags),
                        "default_expression": ap_default_from_statement(statement, local_name),
                        "statement": statement[:500],
                    }
                )
    return index


def score_ap_source(metadata: dict[str, Any], source: dict[str, Any]) -> int:
    mapping = {
        "DisplayName": "DisplayName",
        "Description": "Description",
        "Units": "Units",
        "Increment": "Increment",
        "User": "User",
    }
    score = 0
    for metadata_key, source_key in mapping.items():
        value = metadata.get(metadata_key)
        if value is None:
            continue
        candidates = source["tags"].get(source_key, [])
        if norm_text(value) in {norm_text(candidate) for candidate in candidates}:
            score += 4 if metadata_key == "Description" else 2
    return score


def select_ap_sources(
    name: str, metadata: dict[str, Any], source_index: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], str]:
    suffixes = sorted(
        [local for local in source_index if name == local or name.endswith("_" + local)],
        key=len,
        reverse=True,
    )
    if not suffixes:
        return [], "unresolved"
    longest = len(suffixes[0])
    candidates = [
        source
        for suffix in suffixes
        if len(suffix) == longest
        for source in source_index[suffix]
    ]
    scored = [(score_ap_source(metadata, source), source) for source in candidates]
    best_score = max((score for score, _ in scored), default=0)
    selected = [source for score, source in scored if score == best_score]
    if best_score > 0 and len(selected) == 1:
        confidence = "exact_metadata_unique"
    elif best_score > 0:
        confidence = "exact_metadata_multiple"
    elif len(selected) == 1:
        confidence = "unique_suffix_only"
    else:
        confidence = "ambiguous_suffix_only"
    return selected[:25], confidence


def run_ardupilot_parameter_parser(vehicle: str, work_dir: Path) -> dict[str, Any]:
    parser = AP_ROOT / "Tools" / "autotest" / "param_metadata" / "param_parse.py"
    subprocess.run(
        [sys.executable, str(parser), "--vehicle", vehicle, "--format", "json"],
        cwd=work_dir,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    return json.loads((work_dir / "apm.pdef.json").read_text(encoding="utf-8"))


def extract_ardupilot_parameters(temp_root: Path) -> list[dict[str, Any]]:
    source_index = index_ardupilot_param_sources()
    rows: list[dict[str, Any]] = []
    for vehicle in SYSTEMS["ArduPilot"]["vehicle_scopes"]:
        work_dir = temp_root / f"ardupilot_{vehicle.lower()}"
        work_dir.mkdir(parents=True)
        data = run_ardupilot_parameter_parser(vehicle, work_dir)
        for group, params in sorted(data.items()):
            if group == "json":
                continue
            for name, metadata in sorted(params.items()):
                sources, confidence = select_ap_sources(name, metadata, source_index)
                defaults = sorted(
                    {
                        source["default_expression"]
                        for source in sources
                        if source["default_expression"]
                    }
                )
                range_value = metadata.get("Range", {})
                rows.append(
                    {
                        "system": "ArduPilot",
                        "vehicle_scope": vehicle,
                        "name": name,
                        "group": group,
                        "type": "not_exposed_by_param_metadata_parser",
                        "default": " | ".join(defaults),
                        "default_provenance": (
                            "source_macro_expression_not_evaluated" if defaults else "not_extracted"
                        ),
                        "short_description": metadata.get("DisplayName", ""),
                        "long_description": metadata.get("Description", ""),
                        "units": metadata.get("Units", ""),
                        "minimum": range_value.get("low", "") if isinstance(range_value, dict) else "",
                        "maximum": range_value.get("high", "") if isinstance(range_value, dict) else "",
                        "increment": metadata.get("Increment", ""),
                        "values": metadata.get("Values", {}),
                        "bitmask": metadata.get("Bitmask", {}),
                        "reboot_required": metadata.get("RebootRequired", ""),
                        "volatile": "",
                        "user_level": metadata.get("User", ""),
                        "source_locations": [source["location"] for source in sources],
                        "source_location_confidence": confidence,
                        "catalog_scope": "official_vehicle_metadata_parser_output",
                        "build_inclusion_status": "not_compile_option_resolved",
                        "mavlink_parameter_transport": "protocol_capable_runtime_presence_not_observed",
                        "runtime_observation_status": "NOT_RUN_NO_CAPTURE",
                        "metadata": metadata,
                    }
                )
    return rows


def px4_parameter_source_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in source_code_files(PX4_ROOT / "src", {".c", ".h"}):
        if path.is_relative_to(SYSTEMS["PX4"]["mavlink_root"]):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in PX4_PARAM_DEFINE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            index[match.group(2)].append(
                {
                    "location": f"{rel(path)}:{line}",
                    "path": rel(path),
                    "line": line,
                    "type": match.group(1),
                    "default_expression": norm_text(match.group(3)),
                }
            )
    return index


def px4_metadata_directories() -> list[Path]:
    directories: set[Path] = set()
    source_root = PX4_ROOT / "src"
    for path in source_root.rglob("*"):
        if not path.is_dir():
            continue
        try:
            depth = len(path.relative_to(source_root).parts)
        except ValueError:
            continue
        if depth > 4 or path.is_relative_to(SYSTEMS["PX4"]["mavlink_root"]):
            continue
        directories.add(path)
    directories.add(source_root)
    return sorted(directories)


def run_px4_parameter_parser(work_dir: Path) -> dict[str, Any]:
    parser = PX4_ROOT / "src" / "lib" / "parameters" / "px_process_params.py"
    output = work_dir / "parameters.json"
    command = [sys.executable, str(parser), "--src-path"]
    command.extend(str(path) for path in px4_metadata_directories())
    command.extend(["--json", str(output)])
    subprocess.run(
        command,
        cwd=work_dir,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    return json.loads(output.read_text(encoding="utf-8"))


def extract_px4_parameters(temp_root: Path) -> list[dict[str, Any]]:
    work_dir = temp_root / "px4"
    work_dir.mkdir(parents=True)
    data = run_px4_parameter_parser(work_dir)
    source_index = px4_parameter_source_index()
    rows: list[dict[str, Any]] = []
    for param in data.get("parameters", []):
        name = param["name"]
        sources = source_index.get(name, [])
        rows.append(
            {
                "system": "PX4",
                "vehicle_scope": "full_static_metadata_universe_not_SITL_build_resolved",
                "name": name,
                "group": param.get("group", ""),
                "type": param.get("type", ""),
                "default": param.get("default", ""),
                "default_provenance": "source_literal_or_source_expression_parsed_by_px4_tool",
                "short_description": param.get("shortDesc", ""),
                "long_description": param.get("longDesc", ""),
                "units": param.get("units", ""),
                "minimum": param.get("min", ""),
                "maximum": param.get("max", ""),
                "increment": param.get("increment", ""),
                "values": param.get("values", []),
                "bitmask": param.get("bitmask", []),
                "reboot_required": param.get("rebootRequired", ""),
                "volatile": param.get("volatile", ""),
                "user_level": param.get("category", ""),
                "source_locations": [source["location"] for source in sources],
                "source_location_confidence": (
                    "exact_definition_unique"
                    if len(sources) == 1
                    else "exact_definition_multiple"
                    if sources
                    else "unresolved_or_yaml_generated"
                ),
                "catalog_scope": "px4_official_source_metadata_scan_maxdepth4",
                "build_inclusion_status": "not_px4_sitl_module_list_resolved",
                "mavlink_parameter_transport": "protocol_capable_runtime_presence_not_observed",
                "runtime_observation_status": "NOT_RUN_NO_CAPTURE",
                "metadata": param,
            }
        )
    return rows


def temporal_classification(
    name: str, description: str, units: str, *, entity_kind: str
) -> dict[str, str] | None:
    name_lower = name.lower()
    desc_lower = description.lower()
    units_lower = units.lower()
    temporal_unit = units_lower in {"s", "ms", "us", "ns", "min", "h", "d", "hz", "1/s"}
    keyword = re.search(
        r"(^|_)(time|timestamp|duration|timeout|interval|deadline|delay|latency|"
        r"period|uptime|elapsed|remaining|heartbeat|second|minute|hour|date|utc)(_|$)",
        name_lower,
    ) or re.search(
        r"\b(timestamp|time since|time of week|duration|timeout|interval|deadline|"
        r"delay|latency|elapsed|remaining time|uptime|unix epoch|gps epoch|utc time|"
        r"pulse width|frequency|rate in hz)\b",
        desc_lower,
    )
    if not temporal_unit and not keyword:
        return None

    if units_lower in {"hz", "1/s"} or "frequency" in desc_lower or "rate in hz" in desc_lower:
        temporal_kind = "frequency_or_rate"
    elif "pulse width" in desc_lower or re.search(r"\b(pwm|servo|rc channel)\b", desc_lower):
        temporal_kind = "pulse_width_or_channel_time_value"
    elif re.search(r"timestamp|time when|time of week|utc time|unix epoch|gps epoch", desc_lower):
        temporal_kind = "timestamp"
    elif re.search(r"duration|timeout|interval|delay|latency|elapsed|remaining|time since last", desc_lower):
        temporal_kind = "duration_or_interval"
    elif re.search(r"(^|_)(year|month|day|hour|minute|second)(_|$)", name_lower):
        temporal_kind = "calendar_component"
    elif temporal_unit:
        temporal_kind = "time_dimension_value_ambiguous_role"
    else:
        temporal_kind = "time_related_ambiguous"

    clock_domain = "not_applicable_duration_or_rate"
    explicit = "false"
    ambiguity = ""
    if temporal_kind in {"timestamp", "calendar_component"} or "timestamp" in name_lower:
        explicit = "true"
        has_unix = bool(
            re.search(r"unix epoch|unix time|since 01\.01\.1970|since 1\.1\.1970", desc_lower)
        )
        has_boot = bool(
            re.search(r"system boot|since boot|system startup|system start", desc_lower)
        )
        if has_unix:
            if has_boot:
                clock_domain = "ambiguous_unix_epoch_or_system_boot"
                ambiguity = "XML explicitly permits two clock domains"
            elif "camera clock" in desc_lower:
                clock_domain = "unix_epoch_camera_clock"
            elif "utc" in desc_lower:
                clock_domain = "unix_epoch_utc_as_described"
            else:
                clock_domain = "unix_epoch"
        elif "gps epoch" in desc_lower:
            clock_domain = "gps_epoch"
        elif "gps time of week" in desc_lower or "gps week" in desc_lower:
            clock_domain = "gps_time_of_week"
        elif "utc" in desc_lower:
            clock_domain = "utc_unspecified_timescale_details"
        elif re.search(r"receiver'?s time domain|receiver time domain", desc_lower):
            clock_domain = "receiver_boot_or_receiver_local_clock"
        elif re.search(r"vehicle boot", desc_lower):
            clock_domain = "vehicle_boot"
        elif re.search(r"system boot|since boot|system startup|system start", desc_lower):
            clock_domain = "system_boot"
        elif "camera clock" in desc_lower:
            clock_domain = "camera_clock_unspecified_epoch"
        elif "of obc" in desc_lower:
            clock_domain = "OBC_clock_unspecified_epoch"
        elif temporal_kind == "calendar_component":
            clock_domain = "calendar_scale_as_described_by_parent_message"
            ambiguity = "Inspect the full message description and validity fields"
        else:
            clock_domain = "ambiguous_not_defined_by_xml"
            explicit = "false"
            ambiguity = "XML gives a time-like field but no clock epoch/domain"

    if temporal_kind.startswith("time_dimension") or temporal_kind.endswith("ambiguous"):
        ambiguity = ambiguity or "Unit/name is temporal but semantic role is not explicit"

    return {
        "temporal_kind": temporal_kind,
        "clock_domain": clock_domain,
        "clock_semantics_explicit_in_definition": explicit,
        "ambiguity": ambiguity,
        "classification_basis": "XML/source metadata text and unit only; no runtime inference",
        "entity_kind": entity_kind,
    }


def build_messages_outputs(catalogs: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    csv_rows: list[dict[str, Any]] = []
    for catalog in catalogs:
        for message in catalog["messages"]:
            for field in message["fields"]:
                csv_rows.append(
                    {
                        "system": catalog["system"],
                        "sut_commit": catalog["sut_commit"],
                        "mavlink_commit": catalog["mavlink_commit"],
                        "dialect_entrypoints": "|".join(message["dialect_entrypoints"]),
                        "message_id": message["message_id"],
                        "message_name": message["name"],
                        "message_description": message["description"],
                        "message_origin_xml": message["origin_xml"],
                        "message_origin_line": message["origin_line"],
                        "message_payload_min_length": message["payload_min_length"],
                        "message_payload_max_length": message["payload_max_length"],
                        "message_deprecated_since": message["deprecated_since"],
                        "message_replaced_by": message["replaced_by"],
                        "message_superseded_since": message["superseded_since"],
                        "message_superseded_by": message["superseded_by"],
                        "message_wip": message["wip"],
                        "field_xml_order": field["xml_field_order"],
                        "field_payload_wire_order": field["payload_wire_order"],
                        "field_payload_wire_offset": field["payload_wire_offset"],
                        "field_payload_size": field["payload_size"],
                        "field_extension": str(field["extension"]).lower(),
                        "field_name": field["name"],
                        "field_type": field["type"],
                        "field_primitive_type": field["primitive_type"],
                        "field_array_length": field["array_length"],
                        "field_units": field["units"],
                        "field_enum": field["enum"],
                        "field_description": field["description"],
                        "field_default": field["default"],
                        "field_invalid": field["invalid"],
                        "field_display": field["display"],
                        "field_print_format": field["print_format"],
                        "field_origin_xml": field["origin_xml"],
                        "field_origin_line": field["origin_line"],
                    }
                )
    output = {
        "schema_version": "1.0",
        "definition_scope": "actual build XML entrypoint include closures; not runtime traffic",
        "systems": [
            {key: value for key, value in catalog.items() if key != "commands"}
            for catalog in catalogs
        ],
    }
    return output, csv_rows


def build_commands_outputs(catalogs: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    csv_rows: list[dict[str, Any]] = []
    for catalog in catalogs:
        for command in catalog["commands"]:
            for param in command["params"]:
                csv_rows.append(
                    {
                        "system": catalog["system"],
                        "sut_commit": catalog["sut_commit"],
                        "mavlink_commit": catalog["mavlink_commit"],
                        "dialect_entrypoints": "|".join(command["dialect_entrypoints"]),
                        "command_id": command["command_id"],
                        "command_name": command["name"],
                        "command_description": command["description"],
                        "has_location": command["has_location"],
                        "is_destination": command["is_destination"],
                        "mission_only": command["mission_only"],
                        "command_deprecated_since": command["deprecated_since"],
                        "command_replaced_by": command["replaced_by"],
                        "command_superseded_since": command["superseded_since"],
                        "command_superseded_by": command["superseded_by"],
                        "command_wip": command["wip"],
                        "origin_xml": command["origin_xml"],
                        "origin_line": command["origin_line"],
                        "param_index": param["index"],
                        "param_definition_status": param["definition_status"],
                        "param_xml_occurrence_count": param["xml_occurrence_count"],
                        "param_duplicate_details": json.dumps(
                            param["duplicate_details"], ensure_ascii=False, sort_keys=True
                        ),
                        "param_label": param["label"],
                        "param_description": param["description"],
                        "param_units": param["units"],
                        "param_enum": param["enum"],
                        "param_decimal_places": param["decimal_places"],
                        "param_increment": param["increment"],
                        "param_min_value": param["min_value"],
                        "param_max_value": param["max_value"],
                        "param_default": param["default"],
                        "param_reserved": param["reserved"],
                    }
                )
    output = {
        "schema_version": "1.0",
        "parameter_slots": "Each MAV_CMD has explicit rows for param1..param7; unspecified is not invented as reserved.",
        "systems": [
            {
                "system": catalog["system"],
                "sut_commit": catalog["sut_commit"],
                "mavlink_commit": catalog["mavlink_commit"],
                "definition_scope": catalog["definition_scope"],
                "dialect_entrypoints": catalog["dialect_entrypoints"],
                "commands": catalog["commands"],
            }
            for catalog in catalogs
        ],
    }
    return output, csv_rows


def flatten_parameter_rows(parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for param in parameters:
        rows.append(
            {
                **param,
                "values": json.dumps(param["values"], ensure_ascii=False, sort_keys=True),
                "bitmask": json.dumps(param["bitmask"], ensure_ascii=False, sort_keys=True),
                "source_locations": "|".join(param["source_locations"]),
                "metadata": json.dumps(param["metadata"], ensure_ascii=False, sort_keys=True),
            }
        )
    return rows


def evidence_summary(evidence: dict[str, list[str]]) -> tuple[int, int, int, str]:
    tx = evidence.get("tx", [])
    rx = evidence.get("rx", [])
    other = evidence.get("other", [])
    locations = sorted(set(tx + rx + other))
    return len(tx), len(rx), len(other), "|".join(locations[:40])


def build_support_matrix(
    catalogs: list[dict[str, Any]],
    scans: dict[str, tuple[dict[str, Any], dict[str, Any], int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for catalog in catalogs:
        system = catalog["system"]
        message_index, command_index, source_file_count = scans[system]
        scan_scope = (
            "ArduCopter|ArduPlane|Rover|libraries production-like C/C++ headers/sources; tests/examples excluded"
            if system == "ArduPilot"
            else "PX4 src production-like C/C++ headers/sources; embedded MAVLink submodule/tests/examples excluded"
        )
        for entity_kind, definitions, id_key, index in [
            ("message", catalog["messages"], "message_id", message_index),
            ("command", catalog["commands"], "command_id", command_index),
        ]:
            for definition in definitions:
                evidence = index.get(definition["name"], {})
                tx, rx, other, locations = evidence_summary(evidence)
                count = tx + rx + other
                rows.append(
                    {
                        "system": system,
                        "entity_kind": entity_kind,
                        "entity_id": definition[id_key],
                        "entity_name": definition["name"],
                        "dialect_entrypoints": "|".join(definition["dialect_entrypoints"]),
                        "origin_xml": definition["origin_xml"],
                        "dialect_definition_status": "DEFINED_IN_ENTRYPOINT_CLOSURE",
                        "static_source_reference_status": (
                            "STATIC_REFERENCE_FOUND"
                            if count
                            else "NO_REFERENCE_FOUND_BY_HEURISTIC_SCAN"
                        ),
                        "static_tx_evidence_count": tx,
                        "static_rx_or_handler_evidence_count": rx,
                        "static_other_evidence_count": other,
                        "static_evidence_locations": locations,
                        "static_scan_file_count": source_file_count,
                        "static_scan_scope": scan_scope,
                        "default_runtime_observation_status": "NOT_RUN_NO_CAPTURE",
                        "default_runtime_observation_evidence": "",
                        "interpretation_limit": (
                            "XML definition is not implementation support; static references are heuristic and do not prove reachability; "
                            "no default runtime MAVLink capture was performed."
                        ),
                    }
                )
    return rows


def build_time_rows(
    catalogs: list[dict[str, Any]], parameters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for catalog in catalogs:
        for message in catalog["messages"]:
            for field in message["fields"]:
                classification = temporal_classification(
                    field["name"], field["description"], field["units"], entity_kind="message_field"
                )
                if classification:
                    rows.append(
                        {
                            "system": catalog["system"],
                            "entity_kind": "message_field",
                            "container_id": message["message_id"],
                            "container_name": message["name"],
                            "item_position": field["xml_field_order"],
                            "item_name": field["name"],
                            "type": field["type"],
                            "units": field["units"],
                            "description": field["description"],
                            "origin": f"{field['origin_xml']}:{field['origin_line']}",
                            "dialect_entrypoints_or_scope": "|".join(message["dialect_entrypoints"]),
                            "mavlink_observability": "direct_field_if_message_is_emitted_or_received",
                            "runtime_observation_status": "NOT_RUN_NO_CAPTURE",
                            **classification,
                        }
                    )
        for command in catalog["commands"]:
            for param in command["params"]:
                classification = temporal_classification(
                    param["label"],
                    param["description"],
                    param["units"],
                    entity_kind="command_param",
                )
                if classification:
                    rows.append(
                        {
                            "system": catalog["system"],
                            "entity_kind": "command_param",
                            "container_id": command["command_id"],
                            "container_name": command["name"],
                            "item_position": param["index"],
                            "item_name": param["label"],
                            "type": "command_semantic_parameter_transport_dependent",
                            "units": param["units"],
                            "description": param["description"],
                            "origin": f"{command['origin_xml']}:{command['origin_line']}",
                            "dialect_entrypoints_or_scope": "|".join(command["dialect_entrypoints"]),
                            "mavlink_observability": "direct_command_parameter_if_command_is_transmitted",
                            "runtime_observation_status": "NOT_RUN_NO_CAPTURE",
                            **classification,
                        }
                    )
    for param in parameters:
        classification = temporal_classification(
            param["name"],
            " ".join([param["short_description"], param["long_description"]]),
            param["units"],
            entity_kind="configuration_parameter",
        )
        if classification:
            rows.append(
                {
                    "system": param["system"],
                    "entity_kind": "configuration_parameter",
                    "container_id": "",
                    "container_name": param["vehicle_scope"],
                    "item_position": "",
                    "item_name": param["name"],
                    "type": param["type"],
                    "units": param["units"],
                    "description": " ".join(
                        part for part in [param["short_description"], param["long_description"]] if part
                    ),
                    "origin": "|".join(param["source_locations"]),
                    "dialect_entrypoints_or_scope": param["catalog_scope"],
                    "mavlink_observability": "parameter_protocol_capable_runtime_presence_not_observed",
                    "runtime_observation_status": "NOT_RUN_NO_CAPTURE",
                    **classification,
                }
            )
    rows.sort(
        key=lambda row: (
            row["system"],
            row["entity_kind"],
            str(row["container_id"]),
            str(row["item_position"]),
            row["item_name"],
        )
    )
    return rows


MESSAGE_COLUMNS = [
    "system", "sut_commit", "mavlink_commit", "dialect_entrypoints",
    "message_id", "message_name", "message_description", "message_origin_xml",
    "message_origin_line", "message_payload_min_length", "message_payload_max_length",
    "message_deprecated_since", "message_replaced_by", "message_superseded_since",
    "message_superseded_by", "message_wip",
    "field_xml_order", "field_payload_wire_order", "field_payload_wire_offset",
    "field_payload_size", "field_extension", "field_name", "field_type",
    "field_primitive_type", "field_array_length", "field_units", "field_enum",
    "field_description", "field_default", "field_invalid", "field_display",
    "field_print_format", "field_origin_xml", "field_origin_line",
]

COMMAND_COLUMNS = [
    "system", "sut_commit", "mavlink_commit", "dialect_entrypoints",
    "command_id", "command_name", "command_description", "has_location",
    "is_destination", "mission_only", "command_deprecated_since",
    "command_replaced_by", "command_superseded_since", "command_superseded_by",
    "command_wip", "origin_xml", "origin_line",
    "param_index", "param_definition_status", "param_xml_occurrence_count",
    "param_duplicate_details", "param_label", "param_description",
    "param_units", "param_enum", "param_decimal_places", "param_increment",
    "param_min_value", "param_max_value", "param_default", "param_reserved",
]

PARAMETER_COLUMNS = [
    "system", "vehicle_scope", "name", "group", "type", "default",
    "default_provenance", "short_description", "long_description", "units",
    "minimum", "maximum", "increment", "values", "bitmask", "reboot_required",
    "volatile", "user_level", "source_locations", "source_location_confidence",
    "catalog_scope", "build_inclusion_status", "mavlink_parameter_transport",
    "runtime_observation_status", "metadata",
]

SUPPORT_COLUMNS = [
    "system", "entity_kind", "entity_id", "entity_name", "dialect_entrypoints",
    "origin_xml", "dialect_definition_status", "static_source_reference_status",
    "static_tx_evidence_count", "static_rx_or_handler_evidence_count",
    "static_other_evidence_count", "static_evidence_locations", "static_scan_file_count",
    "static_scan_scope", "default_runtime_observation_status",
    "default_runtime_observation_evidence", "interpretation_limit",
]

TIME_COLUMNS = [
    "system", "entity_kind", "container_id", "container_name", "item_position",
    "item_name", "type", "units", "temporal_kind", "clock_domain",
    "clock_semantics_explicit_in_definition", "description", "origin",
    "dialect_entrypoints_or_scope", "mavlink_observability",
    "runtime_observation_status", "ambiguity", "classification_basis",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-parameters",
        action="store_true",
        help="Developer-only fast path; normal catalog generation must not use this.",
    )
    args = parser.parse_args()

    freeze = assert_frozen_inputs()
    catalogs = [parse_system_xml(system, spec) for system, spec in SYSTEMS.items()]
    scans = {
        system: scan_static_references(system, spec) for system, spec in SYSTEMS.items()
    }

    with tempfile.TemporaryDirectory(prefix=".catalog-tmp-", dir=CATALOG_DIR) as temp:
        temp_root = Path(temp)
        parameters: list[dict[str, Any]] = []
        if not args.skip_parameters:
            parameters.extend(extract_ardupilot_parameters(temp_root))
            parameters.extend(extract_px4_parameters(temp_root))
        else:
            existing = CATALOG_DIR / "configuration_parameters.json"
            if not existing.is_file():
                raise RuntimeError("--skip-parameters requires an existing parameter JSON")
            parameters = json.loads(existing.read_text(encoding="utf-8"))["parameters"]

    messages_json, message_rows = build_messages_outputs(catalogs)
    commands_json, command_rows = build_commands_outputs(catalogs)
    parameter_json = {
        "schema_version": "1.0",
        "scope_note": (
            "ArduPilot rows are official vehicle metadata-parser outputs. PX4 rows are the official "
            "source metadata scan universe and are not resolved against the px4_sitl_default module list. "
            "Neither set is a runtime parameter-list capture."
        ),
        "parameters": parameters,
    }
    support_rows = build_support_matrix(catalogs, scans)
    time_rows = build_time_rows(catalogs, parameters)

    write_json(CATALOG_DIR / "messages_and_fields.json", messages_json)
    write_csv(CATALOG_DIR / "messages_and_fields.csv", message_rows, MESSAGE_COLUMNS)
    write_json(CATALOG_DIR / "commands.json", commands_json)
    write_csv(CATALOG_DIR / "commands.csv", command_rows, COMMAND_COLUMNS)
    write_json(CATALOG_DIR / "configuration_parameters.json", parameter_json)
    write_csv(
        CATALOG_DIR / "configuration_parameters.csv",
        flatten_parameter_rows(parameters),
        PARAMETER_COLUMNS,
    )
    write_csv(CATALOG_DIR / "static_support_matrix.csv", support_rows, SUPPORT_COLUMNS)
    write_csv(CATALOG_DIR / "time_fields.csv", time_rows, TIME_COLUMNS)

    counts: dict[str, Any] = {}
    for catalog in catalogs:
        system = catalog["system"]
        system_params = [param for param in parameters if param["system"] == system]
        system_support = [row for row in support_rows if row["system"] == system]
        system_time = [row for row in time_rows if row["system"] == system]
        counts[system] = {
            "xml_files_in_entrypoint_union": len(catalog["xml_files"]),
            "messages": len(catalog["messages"]),
            "message_fields": sum(len(message["fields"]) for message in catalog["messages"]),
            "commands": len(catalog["commands"]),
            "command_param_slots": sum(len(command["params"]) for command in catalog["commands"]),
            "configuration_parameter_rows": len(system_params),
            "static_referenced_entities": sum(
                row["static_source_reference_status"] == "STATIC_REFERENCE_FOUND"
                for row in system_support
            ),
            "static_referenced_entities_by_kind": dict(
                sorted(
                    Counter(
                        row["entity_kind"]
                        for row in system_support
                        if row["static_source_reference_status"] == "STATIC_REFERENCE_FOUND"
                    ).items()
                )
            ),
            "runtime_observed_entities": 0,
            "time_catalog_rows": len(system_time),
            "time_rows_by_entity_kind": dict(
                sorted(Counter(row["entity_kind"] for row in system_time).items())
            ),
            "time_rows_by_clock_domain": dict(
                sorted(Counter(row["clock_domain"] for row in system_time).items())
            ),
            "configuration_rows_by_scope": dict(
                sorted(Counter(param["vehicle_scope"] for param in system_params).items())
            ),
            "configuration_source_location_confidence": dict(
                sorted(
                    Counter(param["source_location_confidence"] for param in system_params).items()
                )
            ),
            "static_scan_files": scans[system][2],
        }

    manifest = {
        "schema_version": "1.0",
        "source_freeze_timestamp": freeze.get("frozen_at", ""),
        "generation_is_deterministic": True,
        "generator": {
            "path": rel(Path(__file__)),
            "sha256": sha256(Path(__file__)),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "validator": {
            "path": rel(CATALOG_DIR / "validate_catalog.py"),
            "sha256": sha256(CATALOG_DIR / "validate_catalog.py"),
        },
        "documentation": {
            "path": rel(CATALOG_DIR / "README.md"),
            "sha256": sha256(CATALOG_DIR / "README.md"),
        },
        "inputs": {
            system: {
                "sut_commit": EXPECTED[system]["sut_commit"],
                "mavlink_commit": EXPECTED[system]["mavlink_commit"],
                "dialect_entrypoints": spec["entrypoints"],
                "xml_files": catalog["xml_files"],
            }
            for (system, spec), catalog in zip(SYSTEMS.items(), catalogs)
        },
        "evidence_levels": {
            "dialect_definition": "XML entrypoint include closure",
            "static_support": "heuristic references in frozen production-like source scope",
            "default_runtime_observation": "NOT_RUN_NO_CAPTURE for every row",
        },
        "counts": counts,
        "output_sha256": {
            name: sha256(CATALOG_DIR / name) for name in OUTPUT_FILES
        },
        "known_limits": [
            "No SITL process or MAVLink capture was run; runtime observation is intentionally empty.",
            "Static source references are lexical evidence and do not prove reachability, direction, or support completeness.",
            "PX4 configuration parameters are not filtered by the px4_sitl_default resolved CMake module list and omit YAML-generated serial/module parameters.",
            "ArduPilot defaults are retained as unevaluated source macro expressions where mapping is possible.",
            "A MAVLink XML time-like unit does not by itself define an epoch; ambiguous clocks remain marked ambiguous.",
        ],
    }
    write_json(CATALOG_DIR / "manifest.json", manifest)
    print(json.dumps(counts, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
