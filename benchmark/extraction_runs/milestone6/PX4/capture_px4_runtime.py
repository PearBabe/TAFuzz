#!/usr/bin/env python3
"""Capture PX4 v1.17 SITL runtime MAVLink and parameter evidence.

All durable outputs are written next to this script. The only external
filesystem objects PX4 itself requires are its hard-coded per-instance
/tmp lock and daemon socket; this driver records and removes only the exact
instance-42 objects when they did not pre-exist.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shlex
import signal
import socket
import stat as statlib
import struct
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["MAVLINK20"] = "1"
# Import a pre-generated system dialect first. A frozen PX4 development
# dialect is generated into the evidence directory and installed below.
os.environ["MAVLINK_DIALECT"] = "common"

from pymavlink import mavutil  # noqa: E402
from pymavlink.generator import mavgen  # noqa: E402


WORKSPACE = Path("/home/lqq/project/TAFuzz")
PX4_REPO = WORKSPACE / "baseline/px4"
BUILD = PX4_REPO / "build/px4_sitl_default"
PX4_BIN = BUILD / "bin/px4"
PX4_ROOTFS = BUILD / "etc"
MAVLINK_REPO = PX4_REPO / "src/modules/mavlink/mavlink"
DIALECT_XML = MAVLINK_REPO / "message_definitions/v1.0/development.xml"
OUT = Path(__file__).resolve().parent
RUNTIME_STATE = OUT / "runtime_state"

FIRMWARE_COMMIT = "d6f12ad1c4f70ad3230afd7d86e971421e02fef4"
MAVLINK_COMMIT = "33af200d25ec6f0925b49b1ba82bbf1294ea5f72"
INSTANCE = 42
TARGET_EXPECTED_SYSID = INSTANCE + 1
GCS_SOURCE_SYSID = 250
GCS_SOURCE_COMPID = 190
GCS_UDP_PORT = 18570 + INSTANCE

BASELINE_SECONDS = 12.0
PARAMETER_TIMEOUT_SECONDS = 60.0
PARAMETER_COMPLETE_QUIET_SECONDS = 2.0
PARAMETER_INCOMPLETE_QUIET_SECONDS = 5.0
REQUEST_TIMEOUT_SECONDS = 0.60
REQUEST_UNSUPPORTED_GRACE_SECONDS = 0.03

REQUIRED_PARAMETERS = {
    "COM_RC_LOSS_T": {"unit": "s", "properties": ["PX4-MC-RCLOSS-001"]},
    "COM_RC_IN_MODE": {"unit": "enum", "properties": ["PX4-MC-RCLOSS-001"]},
    "COM_RCL_EXCEPT": {"unit": "bitmask", "properties": ["PX4-MC-RCLOSS-001"]},
    "NAV_RCL_ACT": {"unit": "enum", "properties": ["PX4-MC-RCLOSS-001", "PX4-MC-OFFBOARD-003"]},
    "COM_DL_LOSS_T": {"unit": "s", "properties": ["PX4-MC-GCSLOSS-002"]},
    "COM_DLL_EXCEPT": {"unit": "bitmask", "properties": ["PX4-MC-GCSLOSS-002"]},
    "NAV_DLL_ACT": {"unit": "enum", "properties": ["PX4-MC-GCSLOSS-002"]},
    "COM_OF_LOSS_T": {"unit": "s", "properties": ["PX4-MC-OFFBOARD-003"]},
    "COM_OBL_RC_ACT": {"unit": "enum", "properties": ["PX4-MC-OFFBOARD-003"]},
    "COM_DISARM_LAND": {"unit": "s", "properties": ["PX4-MC-AUTODISARM-004"]},
    "COM_DISARM_PRFLT": {"unit": "s", "properties": ["PX4-MC-AUTODISARM-004"]},
    "COM_FLT_TIME_MAX": {"unit": "s", "properties": ["PX4-MC-FLIGHTTIME-005"]},
    "RTL_LAND_DELAY": {"unit": "s", "properties": ["PX4-MC-RTLLOITER-006"]},
    "RTL_TYPE": {"unit": "enum", "properties": ["PX4-MC-RTLLOITER-006"]},
    "RTL_DESCEND_ALT": {"unit": "m", "properties": ["PX4-MC-RTLLOITER-006"]},
    "MAV_SYS_ID": {"unit": "id", "properties": []},
    "MAV_TYPE": {"unit": "enum", "properties": []},
    "SYS_AUTOSTART": {"unit": "id", "properties": []},
}

TIME_CONTRACT_PARAMETERS = {
    "COM_RC_LOSS_T": "PX4-MC-RCLOSS-001",
    "COM_DL_LOSS_T": "PX4-MC-GCSLOSS-002",
    "COM_OF_LOSS_T": "PX4-MC-OFFBOARD-003",
    "COM_DISARM_LAND": "PX4-MC-AUTODISARM-004",
    "COM_FLT_TIME_MAX": "PX4-MC-FLIGHTTIME-005",
    "RTL_LAND_DELAY": "PX4-MC-RTLLOITER-006",
}

LOCAL_PORTS = {
    "gcs_local": GCS_UDP_PORT,
    "offboard_local": 14580 + INSTANCE,
    "onboard_payload_local": 14280 + INSTANCE,
    "onboard_gimbal_local": 13030 + INSTANCE,
    "sih_mavlink_local": 19450 + INSTANCE,
}

PHASE_STARTUP = "STARTUP"
PHASE_BASELINE = "BASELINE"
PHASE_PARAMETER = "PARAMETER_DOWNLOAD"
PHASE_SWEEP = "REQUEST_SWEEP"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def safe_json(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "base64", "data": base64.b64encode(value).decode("ascii")}
    if isinstance(value, bytearray):
        return {"encoding": "base64", "data": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def shell_result(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return {
        "command": shlex.join(args),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def git_snapshot() -> dict[str, Any]:
    return {
        "head": shell_result(["git", "-C", str(PX4_REPO), "rev-parse", "HEAD"]),
        "status": shell_result(["git", "-C", str(PX4_REPO), "status", "--short", "--untracked-files=all"]),
        "submodules": shell_result(["git", "-C", str(PX4_REPO), "submodule", "status", "--recursive"]),
    }


def check_udp_port(port: int) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
        return {"port": port, "available": True, "error": None}
    except OSError as exc:
        return {"port": port, "available": False, "error": repr(exc)}
    finally:
        sock.close()


def proc_identity(pid: int) -> dict[str, Any]:
    stat_path = Path(f"/proc/{pid}/stat")
    if not stat_path.exists():
        return {"pid": pid, "exists": False}
    text = stat_path.read_text(encoding="utf-8", errors="replace")
    right = text.rsplit(")", 1)[-1].strip().split()
    # Fields after comm begin at process-state field 3. starttime is field 22.
    return {
        "pid": pid,
        "exists": True,
        "process_group": int(right[2]),
        "session": int(right[3]),
        "starttime_clock_ticks": int(right[19]),
        "cmdline": Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip(),
    }


def process_group_members(pgid: int) -> list[dict[str, Any]]:
    members = []
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            pid = int(stat_path.parent.name)
            ident = proc_identity(pid)
            if ident.get("exists") and ident.get("process_group") == pgid:
                members.append(ident)
        except (OSError, ValueError, IndexError):
            continue
    return sorted(members, key=lambda item: item["pid"])


def param_name(raw: Any) -> str:
    if isinstance(raw, bytes):
        return raw.split(b"\0", 1)[0].decode("ascii", "replace")
    return str(raw).split("\0", 1)[0]


def enum_name(module: Any, enum_group: str, value: int) -> str | None:
    try:
        entry = module.enums[enum_group][value]
        return getattr(entry, "name", None)
    except (KeyError, TypeError, AttributeError):
        return None


def decode_px4_param(wire_float: float, param_type: int, module: Any) -> tuple[int | float, str]:
    """Decode PX4's bytewise PARAM_VALUE integer encoding."""
    real32 = getattr(module, "MAV_PARAM_TYPE_REAL32", 9)
    int32 = getattr(module, "MAV_PARAM_TYPE_INT32", 6)
    uint32 = getattr(module, "MAV_PARAM_TYPE_UINT32", 5)
    int16 = getattr(module, "MAV_PARAM_TYPE_INT16", 4)
    uint16 = getattr(module, "MAV_PARAM_TYPE_UINT16", 3)
    int8 = getattr(module, "MAV_PARAM_TYPE_INT8", 2)
    uint8 = getattr(module, "MAV_PARAM_TYPE_UINT8", 1)
    packed = struct.pack("<f", wire_float)
    if param_type == real32:
        return float(wire_float), "REAL32_DIRECT"
    if param_type == int32:
        return struct.unpack("<i", packed)[0], "PX4_BYTEWISE_INT32"
    if param_type == uint32:
        return struct.unpack("<I", packed)[0], "PX4_BYTEWISE_UINT32"
    if param_type == int16:
        return struct.unpack("<h", packed[:2])[0], "PX4_BYTEWISE_INT16"
    if param_type == uint16:
        return struct.unpack("<H", packed[:2])[0], "PX4_BYTEWISE_UINT16"
    if param_type == int8:
        return struct.unpack("<b", packed[:1])[0], "PX4_BYTEWISE_INT8"
    if param_type == uint8:
        return packed[0], "PX4_BYTEWISE_UINT8"
    return float(wire_float), "UNHANDLED_TYPE_WIRE_FLOAT"


def onboard_time_fields(fields: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in fields.items():
        lower = key.lower()
        if (
            "timestamp" in lower
            or lower.startswith("time_")
            or lower.endswith("_time")
            or lower.endswith("_time_us")
            or lower.endswith("_time_ms")
            or lower in {"time_usec", "time_boot_ms", "event_time_boot_ms", "tc1", "ts1"}
        ):
            result[key] = safe_json(value)
    return result


class Capture:
    def __init__(self, module: Any, jsonl_path: Path, tlog_path: Path, driver_log: Path):
        self.module = module
        self.jsonl = jsonl_path.open("w", encoding="utf-8")
        self.tlog = tlog_path.open("wb")
        self.driver = driver_log.open("w", encoding="utf-8")
        self.capture_start_mono_ns = time.monotonic_ns()
        self.capture_start_wall = utc_now()
        self.phase = PHASE_STARTUP
        self.inventory: dict[tuple[int, str], dict[str, Any]] = {}
        self.total_messages = 0
        self.bad_data_records = 0
        self.phase_counts = Counter()
        self.syscomp_counts = Counter()
        self.parameters_by_name: dict[str, dict[str, Any]] = {}
        self.parameter_indices: set[int] = set()
        self.parameter_expected_count: int | None = None
        self.parameter_received_count = 0
        self.last_parameter_mono_ns: int | None = None
        self.phase_ranges: list[dict[str, Any]] = []
        self.current_phase_start_ns = self.capture_start_mono_ns
        self.current_phase_origin = "PX4 startup and GCS discovery traffic"
        self.current_phase_notes = "Pre-contract startup phase."
        self.request_windows: list[dict[str, Any]] = []

    def report(self, text: str) -> None:
        line = f"{utc_now()} {text}"
        print(line, flush=True)
        self.driver.write(line + "\n")
        self.driver.flush()

    def switch_phase(self, phase: str, traffic_origin: str, notes: str = "") -> None:
        now = time.monotonic_ns()
        self.phase_ranges.append({
            "name": self.phase,
            "start_host_monotonic_ns": self.current_phase_start_ns,
            "end_host_monotonic_ns": now,
            "traffic_origin": self.current_phase_origin,
            "notes": self.current_phase_notes,
        })
        self.phase = phase
        self.current_phase_start_ns = now
        self.current_phase_origin = traffic_origin
        self.current_phase_notes = notes
        self.report(f"PHASE {phase} START monotonic_ns={now} origin={traffic_origin} notes={notes}")

    def close_phase(self, traffic_origin: str, notes: str = "") -> None:
        now = time.monotonic_ns()
        self.phase_ranges.append({
            "name": self.phase,
            "start_host_monotonic_ns": self.current_phase_start_ns,
            "end_host_monotonic_ns": now,
            "traffic_origin": traffic_origin,
            "notes": notes,
        })

    def record_message(self, msg: Any) -> dict[str, Any]:
        mono_ns = time.monotonic_ns()
        wall = utc_now()
        name = msg.get_type()
        raw = bytes(msg.get_msgbuf()) if hasattr(msg, "get_msgbuf") else b""
        if name == "BAD_DATA":
            self.bad_data_records += 1
            fields = safe_json(msg.to_dict()) if hasattr(msg, "to_dict") else {}
            record = {
                "host_monotonic_ns": mono_ns,
                "host_monotonic_since_capture_ns": mono_ns - self.capture_start_mono_ns,
                "host_wall_time_utc": wall,
                "phase": self.phase,
                "message_id": None,
                "message_name": name,
                "source_system": None,
                "source_component": None,
                "sequence": None,
                "fields": fields,
                "onboard_time_fields": {},
                "raw_length": len(raw),
                "raw_hex": raw.hex(),
            }
            self.jsonl.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            return record

        msgid = int(msg.get_msgId())
        sysid = int(msg.get_srcSystem())
        compid = int(msg.get_srcComponent())
        fields = msg.to_dict()
        fields.pop("mavpackettype", None)
        fields_safe = safe_json(fields)
        time_fields = onboard_time_fields(fields)
        try:
            seq = int(msg.get_seq())
        except (AttributeError, TypeError, ValueError):
            seq = None
        record = {
            "host_monotonic_ns": mono_ns,
            "host_monotonic_since_capture_ns": mono_ns - self.capture_start_mono_ns,
            "host_wall_time_utc": wall,
            "phase": self.phase,
            "message_id": msgid,
            "message_name": name,
            "source_system": sysid,
            "source_component": compid,
            "sequence": seq,
            "fields": fields_safe,
            "onboard_time_fields": time_fields,
            "raw_length": len(raw),
            "raw_hex": raw.hex(),
        }
        self.jsonl.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        # Standard pymavlink tlog timestamp prefix: wall-clock microseconds,
        # low two bits reserved for link number (zero here).
        wall_us = int(time.time() * 1_000_000) & ~0x3
        self.tlog.write(struct.pack(">Q", wall_us) + raw)

        key = (msgid, name)
        inv = self.inventory.get(key)
        if inv is None:
            inv = {
                "message_id": msgid,
                "message_name": name,
                "count_total": 0,
                "count_by_phase": Counter(),
                "field_names": set(),
                "sysid_compid_counts": Counter(),
                "first_host_monotonic_ns": mono_ns,
                "last_host_monotonic_ns": mono_ns,
                "first_host_wall_time_utc": wall,
                "last_host_wall_time_utc": wall,
                "onboard_time_fields": {},
            }
            self.inventory[key] = inv
        inv["count_total"] += 1
        inv["count_by_phase"][self.phase] += 1
        inv["field_names"].update(fields.keys())
        inv["sysid_compid_counts"][f"{sysid}:{compid}"] += 1
        inv["last_host_monotonic_ns"] = mono_ns
        inv["last_host_wall_time_utc"] = wall
        for field, value in time_fields.items():
            summary = inv["onboard_time_fields"].setdefault(field, {
                "first": value,
                "last": value,
                "samples": [],
            })
            summary["last"] = value
            if len(summary["samples"]) < 3 and value not in summary["samples"]:
                summary["samples"].append(value)

        self.total_messages += 1
        self.phase_counts[self.phase] += 1
        self.syscomp_counts[f"{sysid}:{compid}"] += 1
        if name == "PARAM_VALUE":
            self.record_parameter(record, fields, msg)
        if self.total_messages % 100 == 0:
            self.jsonl.flush()
            self.tlog.flush()
        return record

    def record_parameter(self, record: dict[str, Any], fields: dict[str, Any], msg: Any) -> None:
        name = param_name(fields["param_id"])
        ptype = int(fields["param_type"])
        wire = float(fields["param_value"])
        decoded, encoding = decode_px4_param(wire, ptype, self.module)
        index = int(fields["param_index"])
        count = int(fields["param_count"])
        item = {
            "name": name,
            # PX4 bytewise integer encoding may use a non-finite float32 bit
            # pattern as the transport carrier (for example UINT32_MAX). Keep
            # JSON strict and preserve the exact carrier separately as hex.
            "wire_value": wire if math.isfinite(wire) else str(wire),
            "wire_value_float32_hex": struct.pack("<f", wire).hex(),
            "decoded_value": decoded,
            "decode_policy": encoding,
            "param_type": ptype,
            "param_type_name": enum_name(self.module, "MAV_PARAM_TYPE", ptype),
            "param_index": index,
            "param_count": count,
            "source_system": int(msg.get_srcSystem()),
            "source_component": int(msg.get_srcComponent()),
            "received_host_monotonic_ns": record["host_monotonic_ns"],
            "received_host_wall_time_utc": record["host_wall_time_utc"],
            "phase": record["phase"],
        }
        self.parameters_by_name[name] = item
        self.parameter_received_count += 1
        if 0 <= index < count:
            self.parameter_indices.add(index)
        if count >= 0:
            self.parameter_expected_count = max(self.parameter_expected_count or 0, count)
        self.last_parameter_mono_ns = record["host_monotonic_ns"]

    def inventory_json(self) -> dict[str, Any]:
        rows = []
        for key in sorted(self.inventory):
            inv = self.inventory[key]
            rows.append({
                "message_id": inv["message_id"],
                "message_name": inv["message_name"],
                "count_total": inv["count_total"],
                "count_by_phase": dict(sorted(inv["count_by_phase"].items())),
                "field_names": sorted(inv["field_names"]),
                "sysid_compid_counts": dict(sorted(inv["sysid_compid_counts"].items())),
                "first_host_monotonic_ns": inv["first_host_monotonic_ns"],
                "last_host_monotonic_ns": inv["last_host_monotonic_ns"],
                "first_host_wall_time_utc": inv["first_host_wall_time_utc"],
                "last_host_wall_time_utc": inv["last_host_wall_time_utc"],
                "onboard_time_fields": inv["onboard_time_fields"],
            })
        return {
            "schema_version": "1.0",
            "generated_at": utc_now(),
            "host_clock": "CLOCK_MONOTONIC_NS",
            "capture_start_host_monotonic_ns": self.capture_start_mono_ns,
            "capture_start_host_wall_time_utc": self.capture_start_wall,
            "total_message_count": self.total_messages,
            "bad_data_record_count": self.bad_data_records,
            "distinct_message_count": len(rows),
            "baseline_distinct_message_count": sum(1 for row in rows if row["count_by_phase"].get(PHASE_BASELINE, 0) > 0),
            "phase_message_counts": dict(sorted(self.phase_counts.items())),
            "source_sysid_compid_counts": dict(sorted(self.syscomp_counts.items())),
            "messages": rows,
        }

    def close(self) -> None:
        self.jsonl.flush()
        self.tlog.flush()
        self.driver.flush()
        self.jsonl.close()
        self.tlog.close()
        self.driver.close()


def generate_frozen_dialect(output: Path, generation_log: Path) -> Any:
    opts = mavgen.Opts(
        output=str(output),
        wire_protocol="2.0",
        language="Python",
        validate=False,
        strict_units=False,
    )
    with generation_log.open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            success = mavgen.mavgen(opts, [str(DIALECT_XML)])
    if not success or not output.is_file():
        raise RuntimeError(f"PX4 development dialect generation failed; see {generation_log}")
    spec = importlib.util.spec_from_file_location("tafuzz_px4_development_v20", output)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to create generated dialect import spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def send_gcs_heartbeat(connection: Any, module: Any) -> None:
    connection.mav.heartbeat_send(
        module.MAV_TYPE_GCS,
        module.MAV_AUTOPILOT_INVALID,
        0,
        0,
        module.MAV_STATE_ACTIVE,
    )


def drain(
    connection: Any,
    capture: Capture,
    module: Any,
    seconds: float,
    last_heartbeat: float,
    inspect_callback: Any | None = None,
) -> tuple[float, list[dict[str, Any]]]:
    deadline = time.monotonic() + seconds
    records = []
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_heartbeat >= 0.8:
            send_gcs_heartbeat(connection, module)
            last_heartbeat = now
        got_any = False
        while True:
            msg = connection.recv_match(blocking=False)
            if msg is None:
                break
            got_any = True
            record = capture.record_message(msg)
            records.append(record)
            if inspect_callback is not None:
                inspect_callback(msg, record)
        if not got_any:
            time.sleep(0.005)
    return last_heartbeat, records


def wait_for_autopilot(
    connection: Any,
    capture: Capture,
    module: Any,
    process: subprocess.Popen[Any],
) -> tuple[int, int, float]:
    deadline = time.monotonic() + 30.0
    last_heartbeat = 0.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"PX4 exited before heartbeat with code {process.returncode}")
        now = time.monotonic()
        if now - last_heartbeat >= 0.5:
            send_gcs_heartbeat(connection, module)
            last_heartbeat = now
        msg = connection.recv_match(blocking=False)
        if msg is None:
            time.sleep(0.01)
            continue
        capture.record_message(msg)
        if (
            msg.get_type() == "HEARTBEAT"
            and int(msg.get_srcSystem()) != GCS_SOURCE_SYSID
            and int(msg.autopilot) != module.MAV_AUTOPILOT_INVALID
        ):
            return int(msg.get_srcSystem()), int(msg.get_srcComponent()), last_heartbeat
    raise TimeoutError("No autopilot HEARTBEAT received within 30 seconds")


def request_named_parameter(
    connection: Any,
    capture: Capture,
    module: Any,
    target_sys: int,
    target_comp: int,
    name: str,
    last_heartbeat: float,
) -> tuple[float, dict[str, Any]]:
    sent_ns = time.monotonic_ns()
    connection.mav.param_request_read_send(target_sys, target_comp, name.encode("ascii"), -1)
    response: dict[str, Any] | None = None

    def inspect(msg: Any, record: dict[str, Any]) -> None:
        nonlocal response
        if msg.get_type() == "PARAM_VALUE" and param_name(msg.param_id) == name and response is None:
            response = {
                "received_host_monotonic_ns": record["host_monotonic_ns"],
                "latency_ns": record["host_monotonic_ns"] - sent_ns,
            }

    last_heartbeat, _ = drain(connection, capture, module, 0.75, last_heartbeat, inspect)
    return last_heartbeat, {
        "name": name,
        "sent_host_monotonic_ns": sent_ns,
        "response": response,
        "status": "OBSERVED" if response is not None else "NO_RESPONSE_WITHIN_750MS",
    }


def result_name(module: Any, result: int) -> str:
    return enum_name(module, "MAV_RESULT", result) or f"MAV_RESULT_{result}"


def request_message_once(
    connection: Any,
    capture: Capture,
    module: Any,
    target_sys: int,
    target_comp: int,
    msgid: int,
    name: str,
    baseline_count: int,
    last_heartbeat: float,
) -> tuple[float, dict[str, Any]]:
    sent_ns = time.monotonic_ns()
    connection.mav.command_long_send(
        target_sys,
        target_comp,
        module.MAV_CMD_REQUEST_MESSAGE,
        0,
        float(msgid),
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )
    ack: dict[str, Any] | None = None
    observed: list[dict[str, Any]] = []
    deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    unsupported_seen_at: float | None = None
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_heartbeat >= 0.8:
            send_gcs_heartbeat(connection, module)
            last_heartbeat = now
        got_any = False
        while True:
            message = connection.recv_match(blocking=False)
            if message is None:
                break
            got_any = True
            record = capture.record_message(message)
            if int(record["message_id"] or -1) == msgid:
                observed.append({
                    "received_host_monotonic_ns": record["host_monotonic_ns"],
                    "latency_ns": record["host_monotonic_ns"] - sent_ns,
                    "source_system": record["source_system"],
                    "source_component": record["source_component"],
                })
            if (
                message.get_type() == "COMMAND_ACK"
                and int(message.command) == module.MAV_CMD_REQUEST_MESSAGE
                and ack is None
            ):
                ack = {
                    "received_host_monotonic_ns": record["host_monotonic_ns"],
                    "latency_ns": record["host_monotonic_ns"] - sent_ns,
                    "result": int(message.result),
                    "result_name": result_name(module, int(message.result)),
                    "source_system": int(message.get_srcSystem()),
                    "source_component": int(message.get_srcComponent()),
                    "fields": safe_json(message.to_dict()),
                    "correlation": "SEQUENTIAL_TEMPORAL_ONLY_COMMAND_ACK_HAS_NO_REQUESTED_MESSAGE_ID",
                }
                if int(message.result) != module.MAV_RESULT_ACCEPTED:
                    unsupported_seen_at = time.monotonic()
        if ack is not None and ack["result"] == module.MAV_RESULT_ACCEPTED and observed:
            break
        if unsupported_seen_at is not None and time.monotonic() - unsupported_seen_at >= REQUEST_UNSUPPORTED_GRACE_SECONDS:
            break
        if not got_any:
            time.sleep(0.003)

    if ack is not None and ack["result"] == module.MAV_RESULT_ACCEPTED and observed:
        classification = "ACK_ACCEPTED_AND_MATCHING_ID_OBSERVED"
    elif ack is not None and ack["result"] == module.MAV_RESULT_ACCEPTED:
        classification = "ACK_ACCEPTED_NO_MATCHING_ID_WITHIN_WINDOW"
    elif ack is not None:
        classification = f"ACK_{ack['result_name']}"
    elif observed:
        classification = "NO_ACK_MATCHING_ID_OBSERVED"
    else:
        classification = "NO_ACK_NO_MATCHING_ID_WITHIN_WINDOW"
    return last_heartbeat, {
        "message_id": msgid,
        "message_name": name,
        "command": "MAV_CMD_REQUEST_MESSAGE",
        "command_id": int(module.MAV_CMD_REQUEST_MESSAGE),
        "sent_host_monotonic_ns": sent_ns,
        "window_timeout_ms": int(REQUEST_TIMEOUT_SECONDS * 1000),
        "ack": ack,
        "matching_frames_in_window": observed,
        "matching_frame_count": len(observed),
        "first_matching_latency_ns": observed[0]["latency_ns"] if observed else None,
        "baseline_count": baseline_count,
        "matching_frame_causal_attribution": (
            "AMBIGUOUS_DEFAULT_STREAM_PRESENT"
            if baseline_count > 0 and observed
            else "TEMPORAL_AFTER_REQUEST_ONLY"
            if observed
            else "NOT_OBSERVED"
        ),
        "classification": classification,
    }


def clean_owned_tmp(pre_tmp: dict[str, Any], lifecycle: dict[str, Any]) -> None:
    removals = []
    for label, path_text in {
        "lock": f"/tmp/px4_lock-{INSTANCE}",
        "daemon_socket": f"/tmp/px4-sock-{INSTANCE}",
    }.items():
        path = Path(path_text)
        before = pre_tmp[label]
        action = {"label": label, "path": path_text, "preexisting": before["exists"], "removed": False}
        if not before["exists"] and path.exists():
            try:
                stat_result = path.lstat()
                if stat_result.st_uid != os.getuid():
                    action["error"] = "post-run object is not owned by capture uid"
                elif label == "lock" and (not path.is_file() or stat_result.st_size != 0):
                    action["error"] = "lock object is not an empty regular file"
                elif label == "daemon_socket" and not statlib.S_ISSOCK(stat_result.st_mode):
                    action["error"] = "unexpected socket object"
                else:
                    path.unlink()
                    action["removed"] = True
            except OSError as exc:
                action["error"] = repr(exc)
        action["exists_after_cleanup"] = path.exists()
        removals.append(action)
    lifecycle["external_tmp_cleanup"] = removals


def relative_artifact(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def artifact(path: Path, role: str) -> dict[str, str]:
    return {"path": relative_artifact(path), "sha256": sha256_file(path), "role": role}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-id", default="PX4-M6-MC-SIHSIM-QUADX-I42-20260718")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "manifest.json").exists():
        raise RuntimeError("manifest.json already exists; refusing to overwrite a prior capture")
    RUNTIME_STATE.mkdir(parents=True, exist_ok=False)

    driver_log_path = OUT / "capture_driver.log"
    jsonl_path = OUT / "mavlink_messages.jsonl"
    tlog_path = OUT / "mavlink_capture.tlog"
    dialect_path = OUT / "px4_development_v20.py"
    dialect_log_path = OUT / "dialect_generation.log"
    stdout_path = OUT / "px4.stdout.log"
    stderr_path = OUT / "px4.stderr.log"
    lifecycle_path = OUT / "process_lifecycle.json"
    inventory_path = OUT / "message_inventory.json"
    parameters_path = OUT / "parameters_runtime.json"
    requests_path = OUT / "message_request_sweep.json"
    command_path = OUT / "commands.json"
    source_integrity_path = OUT / "source_integrity.json"
    details_path = OUT / "capture_details.json"
    readme_path = OUT / "README.md"
    manifest_path = OUT / "manifest.json"

    before_git = git_snapshot()
    before_ports = {name: check_udp_port(port) for name, port in LOCAL_PORTS.items()}
    if not all(item["available"] for item in before_ports.values()):
        raise RuntimeError(f"One or more isolated PX4 UDP ports are unavailable: {before_ports}")

    pre_tmp = {}
    for label, path in {
        "lock": Path(f"/tmp/px4_lock-{INSTANCE}"),
        "daemon_socket": Path(f"/tmp/px4-sock-{INSTANCE}"),
    }.items():
        pre_tmp[label] = {
            "path": str(path),
            "exists": path.exists(),
            "stat": str(path.lstat()) if path.exists() else None,
        }
    if any(item["exists"] for item in pre_tmp.values()):
        raise RuntimeError(f"PX4 instance-{INSTANCE} temporary object already exists: {pre_tmp}")

    module = generate_frozen_dialect(dialect_path, dialect_log_path)
    mavutil.mavlink = module
    mavutil.current_dialect = "tafuzz_px4_development_v20"
    dialect_messages = []
    for msgid, cls in sorted(module.mavlink_map.items()):
        name = getattr(cls, "msgname", None)
        if name is None:
            name = getattr(cls, "name", f"MSG_{msgid}")
        dialect_messages.append({"message_id": int(msgid), "message_name": str(name)})

    capture = Capture(module, jsonl_path, tlog_path, driver_log_path)
    capture.report(
        f"Frozen dialect generated from {DIALECT_XML}; unique_message_ids={len(dialect_messages)}"
    )

    px4_command = [
        str(PX4_BIN),
        "-i",
        str(INSTANCE),
        "-d",
        str(PX4_ROOTFS),
    ]
    invocation = [sys.executable, str(Path(__file__).resolve()), "--capture-id", args.capture_id]
    environment_overrides = {
        "PX4_SIM_MODEL": "sihsim_quadx",
        "PX4_SIMULATOR": "sihsim",
        "PX4_SIM_HOST_ADDR": "127.0.0.1",
        "PX4_SIM_HOSTNAME": "127.0.0.1",
    }
    launch_env = os.environ.copy()
    launch_env.update(environment_overrides)
    launch_env.pop("PX4_SIM_SPEED_FACTOR", None)

    commands = {
        "capture_invocation": shlex.join(invocation),
        "px4_command_argv": px4_command,
        "px4_command_shell": shlex.join(px4_command),
        "px4_cwd": str(RUNTIME_STATE),
        "px4_environment_overrides": environment_overrides,
        "mavlink_connection": f"udpout:127.0.0.1:{GCS_UDP_PORT}",
        "source_system": GCS_SOURCE_SYSID,
        "source_component": GCS_SOURCE_COMPID,
        "read_only_protocol_actions": [
            "GCS HEARTBEAT",
            "PARAM_REQUEST_LIST",
            "PARAM_REQUEST_READ",
            "MAV_CMD_REQUEST_MESSAGE (512)",
        ],
        "persistent_parameter_writes": [],
    }
    write_json(command_path, commands)

    lifecycle: dict[str, Any] = {
        "capture_id": args.capture_id,
        "spawn_requested_at_utc": utc_now(),
        "spawn_requested_host_monotonic_ns": time.monotonic_ns(),
        "command": shlex.join(px4_command),
        "cwd": str(RUNTIME_STATE),
        "environment_overrides": environment_overrides,
        "preexisting_px4_processes": shell_result(["pgrep", "-a", "-x", "px4"]),
        "preexisting_instance_tmp": pre_tmp,
        "signals": [],
    }

    process: subprocess.Popen[Any] | None = None
    connection: Any | None = None
    stdout_file = stdout_path.open("wb")
    stderr_file = stderr_path.open("wb")
    runtime_error: str | None = None
    target_sys: int | None = None
    target_comp: int | None = None
    last_heartbeat = 0.0
    parameter_request_records = []
    sweep_records = []
    try:
        capture.report(f"Starting PX4 command={shlex.join(px4_command)} cwd={RUNTIME_STATE}")
        process = subprocess.Popen(
            px4_command,
            cwd=RUNTIME_STATE,
            env=launch_env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )
        lifecycle["pid"] = process.pid
        lifecycle["pgid"] = os.getpgid(process.pid)
        lifecycle["spawned_identity"] = proc_identity(process.pid)
        lifecycle["process_group_members_after_spawn"] = process_group_members(lifecycle["pgid"])
        if lifecycle["pid"] != lifecycle["pgid"]:
            raise RuntimeError("PX4 process group is not capture-owned")

        connection = mavutil.mavlink_connection(
            f"udpout:127.0.0.1:{GCS_UDP_PORT}",
            source_system=GCS_SOURCE_SYSID,
            source_component=GCS_SOURCE_COMPID,
            input=True,
            autoreconnect=False,
            force_connected=True,
            robust_parsing=True,
            use_native=False,
        )
        try:
            lifecycle["collector_udp_local"] = list(connection.port.getsockname())
        except Exception:
            lifecycle["collector_udp_local"] = None

        target_sys, target_comp, last_heartbeat = wait_for_autopilot(
            connection, capture, module, process
        )
        capture.report(
            f"Autopilot heartbeat acquired target={target_sys}:{target_comp} "
            f"expected_sysid={TARGET_EXPECTED_SYSID}"
        )

        capture.switch_phase(
            PHASE_BASELINE,
            "Default PX4 streams after GCS discovery; no PARAM or message request sent.",
            f"Duration {BASELINE_SECONDS:.1f}s.",
        )
        baseline_start_ns = time.monotonic_ns()
        last_heartbeat, _ = drain(
            connection, capture, module, BASELINE_SECONDS, last_heartbeat
        )
        baseline_end_ns = time.monotonic_ns()
        capture.report(
            f"BASELINE complete duration_ns={baseline_end_ns-baseline_start_ns} "
            f"messages={capture.phase_counts[PHASE_BASELINE]}"
        )

        capture.switch_phase(
            PHASE_PARAMETER,
            "PARAM_REQUEST_LIST followed by explicit PARAM_REQUEST_READ for key parameters.",
            "Runtime values only; no PARAM_SET is sent.",
        )
        param_list_sent_ns = time.monotonic_ns()
        connection.mav.param_request_list_send(target_sys, target_comp)
        capture.report(
            f"PARAM_REQUEST_LIST sent target={target_sys}:{target_comp} monotonic_ns={param_list_sent_ns}"
        )
        parameter_deadline = time.monotonic() + PARAMETER_TIMEOUT_SECONDS
        while time.monotonic() < parameter_deadline:
            last_heartbeat, _ = drain(connection, capture, module, 0.1, last_heartbeat)
            expected = capture.parameter_expected_count
            now_ns = time.monotonic_ns()
            quiet_s = (
                (now_ns - capture.last_parameter_mono_ns) / 1e9
                if capture.last_parameter_mono_ns is not None
                else 0.0
            )
            if expected is not None and len(capture.parameter_indices) >= expected and quiet_s >= PARAMETER_COMPLETE_QUIET_SECONDS:
                break
            if (
                expected is not None
                and capture.parameter_received_count > 0
                and quiet_s >= PARAMETER_INCOMPLETE_QUIET_SECONDS
            ):
                break
        capture.report(
            f"PARAM list receive total={capture.parameter_received_count} "
            f"unique_names={len(capture.parameters_by_name)} "
            f"indices={len(capture.parameter_indices)} expected={capture.parameter_expected_count}"
        )
        for name in REQUIRED_PARAMETERS:
            last_heartbeat, request_record = request_named_parameter(
                connection,
                capture,
                module,
                target_sys,
                target_comp,
                name,
                last_heartbeat,
            )
            parameter_request_records.append(request_record)
        capture.report(
            "Explicit key PARAM requests complete observed="
            f"{sum(r['status']=='OBSERVED' for r in parameter_request_records)}/"
            f"{len(parameter_request_records)}"
        )

        capture.switch_phase(
            PHASE_SWEEP,
            "Sequential MAV_CMD_REQUEST_MESSAGE (512), one frozen dialect message ID per window.",
            f"Timeout {int(REQUEST_TIMEOUT_SECONDS*1000)}ms; no stream-interval or persistent parameter change.",
        )
        baseline_counts = {
            row["message_id"]: row["count_by_phase"].get(PHASE_BASELINE, 0)
            for row in capture.inventory_json()["messages"]
        }
        total_ids = len(dialect_messages)
        for offset, item in enumerate(dialect_messages, start=1):
            last_heartbeat, record = request_message_once(
                connection,
                capture,
                module,
                target_sys,
                target_comp,
                item["message_id"],
                item["message_name"],
                baseline_counts.get(item["message_id"], 0),
                last_heartbeat,
            )
            sweep_records.append(record)
            if offset % 25 == 0 or offset == total_ids:
                capture.report(
                    f"REQUEST_SWEEP progress={offset}/{total_ids} "
                    f"observed={sum(r['matching_frame_count']>0 for r in sweep_records)} "
                    f"acks={sum(r['ack'] is not None for r in sweep_records)}"
                )
        capture.close_phase(
            "Sequential MAV_CMD_REQUEST_MESSAGE (512) plus default traffic that continued during windows.",
            "Matching frames are temporal observations; default-stream presence is marked as causal ambiguity.",
        )
        capture.report("Runtime protocol capture phases complete")
    except Exception:
        runtime_error = traceback.format_exc()
        capture.report("CAPTURE ERROR\n" + runtime_error)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception as exc:
                lifecycle["connection_close_error"] = repr(exc)
        if process is not None:
            lifecycle["pre_shutdown_poll"] = process.poll()
            if process.poll() is None:
                pgid = lifecycle["pgid"]
                sent_ns = time.monotonic_ns()
                os.killpg(pgid, signal.SIGINT)
                lifecycle["signals"].append({"signal": "SIGINT", "sent_host_monotonic_ns": sent_ns})
                try:
                    process.wait(timeout=8.0)
                except subprocess.TimeoutExpired:
                    sent_ns = time.monotonic_ns()
                    os.killpg(pgid, signal.SIGTERM)
                    lifecycle["signals"].append({"signal": "SIGTERM", "sent_host_monotonic_ns": sent_ns})
                    try:
                        process.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        sent_ns = time.monotonic_ns()
                        os.killpg(pgid, signal.SIGKILL)
                        lifecycle["signals"].append({"signal": "SIGKILL", "sent_host_monotonic_ns": sent_ns})
                        process.wait(timeout=5.0)
            lifecycle["exit_code"] = process.returncode
            lifecycle["post_shutdown_identity"] = proc_identity(process.pid)
            lifecycle["process_group_members_after_shutdown"] = process_group_members(lifecycle["pgid"])
        stdout_file.close()
        stderr_file.close()
        clean_owned_tmp(pre_tmp, lifecycle)
        lifecycle["post_cleanup_ports"] = {
            name: check_udp_port(port) for name, port in LOCAL_PORTS.items()
        }
        lifecycle["cleanup_complete"] = bool(
            process is not None
            and not proc_identity(process.pid).get("exists", False)
            and not lifecycle.get("process_group_members_after_shutdown")
            and all(item["available"] for item in lifecycle["post_cleanup_ports"].values())
            and all(not item["exists_after_cleanup"] for item in lifecycle["external_tmp_cleanup"])
        )
        lifecycle["finished_at_utc"] = utc_now()
        lifecycle["finished_host_monotonic_ns"] = time.monotonic_ns()
        write_json(lifecycle_path, lifecycle)
        capture.close()

    inventory = capture.inventory_json()
    write_json(inventory_path, inventory)
    expected = capture.parameter_expected_count
    missing_indices = (
        sorted(set(range(expected)) - capture.parameter_indices)
        if expected is not None
        else []
    )
    parameter_status = (
        "COMPLETE"
        if expected is not None and not missing_indices and len(capture.parameter_indices) == expected
        else "PARTIAL"
        if capture.parameter_received_count > 0
        else "FAILED"
    )
    parameter_json = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "protocol": "PARAM",
        "decode_policy": "PX4 bytewise integer encoding decoded from PARAM_VALUE.param_value raw float32 bits; REAL32 is direct.",
        "status": parameter_status,
        "request_list_sent_host_monotonic_ns": locals().get("param_list_sent_ns"),
        "expected_count": expected,
        "received_count": capture.parameter_received_count,
        "unique_parameter_count": len(capture.parameters_by_name),
        "received_unique_indices": len(capture.parameter_indices),
        "missing_indices": missing_indices,
        "explicit_key_requests": parameter_request_records,
        "required_parameters": {
            name: {
                "status": "RUNTIME_OBSERVED" if name in capture.parameters_by_name else "NOT_OBSERVED",
                "record": capture.parameters_by_name.get(name),
                "unit": metadata["unit"],
                "properties": metadata["properties"],
            }
            for name, metadata in REQUIRED_PARAMETERS.items()
        },
        "parameters": [
            capture.parameters_by_name[name]
            for name in sorted(capture.parameters_by_name)
        ],
    }
    write_json(parameters_path, parameter_json)

    ack_counts = Counter(
        record["ack"]["result_name"] if record["ack"] else "NO_ACK"
        for record in sweep_records
    )
    classification_counts = Counter(record["classification"] for record in sweep_records)
    sweep_status = (
        "COMPLETE"
        if len(sweep_records) == len(dialect_messages) and len(dialect_messages) > 0
        else "PARTIAL"
        if sweep_records
        else "FAILED"
    )
    request_json = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "dialect": "development",
        "dialect_xml": str(DIALECT_XML),
        "dialect_xml_sha256": sha256_file(DIALECT_XML),
        "dialect_unique_message_id_count": len(dialect_messages),
        "command": "MAV_CMD_REQUEST_MESSAGE",
        "command_id": int(getattr(module, "MAV_CMD_REQUEST_MESSAGE", 512)),
        "read_only": True,
        "status": sweep_status,
        "attempted": len(sweep_records),
        "message_observed": sum(record["matching_frame_count"] > 0 for record in sweep_records),
        "ack_observed": sum(record["ack"] is not None for record in sweep_records),
        "unsupported": sum(
            record["ack"] is not None
            and record["ack"]["result_name"] == "MAV_RESULT_UNSUPPORTED"
            for record in sweep_records
        ),
        "no_ack_no_matching_frame": sum(
            record["ack"] is None and record["matching_frame_count"] == 0
            for record in sweep_records
        ),
        "ack_result_counts": dict(sorted(ack_counts.items())),
        "classification_counts": dict(sorted(classification_counts.items())),
        "records": sweep_records,
    }
    write_json(requests_path, request_json)

    after_git = git_snapshot()
    source_integrity = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "expected_firmware_commit": FIRMWARE_COMMIT,
        "expected_mavlink_commit": MAVLINK_COMMIT,
        "before": before_git,
        "after": after_git,
        "head_unchanged": before_git["head"]["stdout"].strip() == after_git["head"]["stdout"].strip() == FIRMWARE_COMMIT,
        "worktree_before_clean": before_git["status"]["stdout"] == "",
        "worktree_after_clean": after_git["status"]["stdout"] == "",
        "submodules_unchanged": before_git["submodules"]["stdout"] == after_git["submodules"]["stdout"],
        "mavlink_head": shell_result(["git", "-C", str(MAVLINK_REPO), "rev-parse", "HEAD"]),
    }
    write_json(source_integrity_path, source_integrity)

    required_missing = [
        name for name in REQUIRED_PARAMETERS if name not in capture.parameters_by_name
    ]
    runtime_status = (
        "COMPLETE"
        if runtime_error is None
        and lifecycle.get("cleanup_complete")
        and parameter_status == "COMPLETE"
        and not required_missing
        and sweep_status == "COMPLETE"
        and source_integrity["head_unchanged"]
        and source_integrity["worktree_before_clean"]
        and source_integrity["worktree_after_clean"]
        and source_integrity["submodules_unchanged"]
        else "PARTIAL"
        if capture.total_messages > 0
        else "FAILED"
    )
    details = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "capture_id": args.capture_id,
        "runtime_status": runtime_status,
        "runtime_error": runtime_error,
        "firmware_commit": FIRMWARE_COMMIT,
        "mavlink_commit": MAVLINK_COMMIT,
        "px4_instance": INSTANCE,
        "expected_target_sysid": TARGET_EXPECTED_SYSID,
        "observed_target_system": target_sys,
        "observed_target_component": target_comp,
        "gcs_source_system": GCS_SOURCE_SYSID,
        "gcs_source_component": GCS_SOURCE_COMPID,
        "ports_before_launch": before_ports,
        "phases": capture.phase_ranges,
        "baseline_contract": {
            "minimum_seconds": 10,
            "configured_seconds": BASELINE_SECONDS,
            "explicit_message_or_parameter_requests_sent": False,
            "gcs_heartbeat_sent_for_dynamic_peer_and_link_liveness": True,
        },
        "parameter_status": parameter_status,
        "required_parameters_missing": required_missing,
        "request_sweep_status": sweep_status,
        "request_sweep_attempted": len(sweep_records),
        "message_count": inventory["total_message_count"],
        "distinct_message_count": inventory["distinct_message_count"],
        "baseline_distinct_message_count": inventory["baseline_distinct_message_count"],
        "implementation_satisfaction": "NOT_ASSESSED",
    }
    write_json(details_path, details)

    parameter_hash = sha256_file(parameters_path)
    inventory_hash = sha256_file(inventory_path)
    requests_hash = sha256_file(requests_path)
    key_values = []
    property_parameters = []
    for name, metadata in REQUIRED_PARAMETERS.items():
        record = capture.parameters_by_name.get(name)
        if record is None:
            continue
        key_values.append({
            "name": name,
            # runtime_capture.schema.json requires a JSON number here. When
            # PX4's bytewise integer carrier is non-finite, the decoded numeric
            # value is the honest finite representation; parameters_runtime.json
            # retains the non-finite sentinel and exact float32 transport bits.
            "wire_value": (
                record["wire_value"]
                if isinstance(record["wire_value"], (int, float))
                else record["decoded_value"]
            ),
            "decoded_value": record["decoded_value"],
            "param_type": record["param_type"],
            "param_index": record["param_index"],
            "param_count": record["param_count"],
            "source_system": record["source_system"],
            "source_component": record["source_component"],
            "received_host_monotonic_ns": record["received_host_monotonic_ns"],
        })
        if name in TIME_CONTRACT_PARAMETERS:
            property_id = TIME_CONTRACT_PARAMETERS[name]
            value = float(record["decoded_value"])
            disabled = (
                (name == "COM_DISARM_LAND" and value <= 0)
                or (name == "COM_FLT_TIME_MAX" and value < 0)
                or (name == "RTL_LAND_DELAY" and value < 0)
            )
            property_parameters.append({
                "property_id": property_id,
                "parameter_id": name,
                "capture_id": args.capture_id,
                "value": record["decoded_value"],
                "unit": metadata["unit"],
                "source_path": relative_artifact(parameters_path),
                "source_sha256": parameter_hash,
                "source_param_index": record["param_index"],
                "source_param_count": record["param_count"],
                "status": "RUNTIME_OBSERVED_DISABLED_DOMAIN" if disabled else "RUNTIME_OBSERVED",
            })

    limitations = [
        "This is runtime acquisition only; implementation/property satisfaction is NOT_ASSESSED.",
        "PX4 used the internal headless SIH multicopter airframe sihsim_quadx; no external graphical simulator, arming, takeoff command, or campaign flight path was used.",
        "Host CLOCK_MONOTONIC_NS arrival time is not substituted for PX4 onboard time fields.",
        "MAV_CMD_REQUEST_MESSAGE COMMAND_ACK identifies command 512 but not the requested message ID; correlation is sequential and temporal.",
        "A matching frame after a request is not asserted causal when that message was already present in BASELINE.",
        "No PARAM_SET, stream-interval change, arming command, mode command, or actuator command was sent.",
        "For non-finite float32 carriers produced by PX4 bytewise integer PARAM encoding, parameters_runtime.json stores a string sentinel plus exact float32 hex; the manifest's numeric wire_value falls back to the decoded integer value.",
        "PX4 emitted the special _HASH_CHECK record at index 65535 in addition to the complete indexed set 0 through param_count-1; it explains why unique parameter names exceed expected_count by one.",
    ]
    if runtime_error is not None:
        limitations.append("Capture encountered an exception recorded in capture_details.json and capture_driver.log.")
    if parameter_status != "COMPLETE":
        limitations.append(
            f"PARAM download was {parameter_status}; expected={expected}, missing_indices={len(missing_indices)}."
        )
    if required_missing:
        limitations.append("Required runtime parameters not observed: " + ", ".join(required_missing))

    readme = f"""# PX4 v1.17 Milestone-6 runtime capture

Status: **{runtime_status}**. This is an observation artifact only; implementation satisfaction is **NOT_ASSESSED**.

## Frozen target and launch

- PX4 commit: `{FIRMWARE_COMMIT}`
- MAVLink commit: `{MAVLINK_COMMIT}`
- Vehicle/profile: `px4_sitl_default`, internal headless multicopter `sihsim_quadx`, instance {INSTANCE}
- PX4 command: `{shlex.join(px4_command)}`
- PX4 working directory: `{RUNTIME_STATE}`
- MAVLink connection: `udpout:127.0.0.1:{GCS_UDP_PORT}`, collector SYSID/COMPID `{GCS_SOURCE_SYSID}:{GCS_SOURCE_COMPID}`
- Observed autopilot SYSID/COMPID: `{target_sys}:{target_comp}`

## Phase separation

1. **BASELINE**: {BASELINE_SECONDS:.1f} seconds after the first autopilot heartbeat, with only the collector GCS heartbeat and no parameter/message request.
2. **PARAMETER_DOWNLOAD**: one `PARAM_REQUEST_LIST`, followed by named `PARAM_REQUEST_READ` probes for the required property/selector/action/exception parameters.
3. **REQUEST_SWEEP**: `MAV_CMD_REQUEST_MESSAGE (512)` sent serially for all {len(dialect_messages)} unique message IDs generated from frozen `development.xml`.

Startup traffic before the first autopilot heartbeat is labelled `STARTUP` and is not counted as baseline.

## Observed result

- MAVLink messages: {inventory['total_message_count']} across {inventory['distinct_message_count']} distinct ID/name pairs.
- Baseline distinct messages: {inventory['baseline_distinct_message_count']}.
- PARAM snapshot: {parameter_status}; expected {expected}, unique indices {len(capture.parameter_indices)}, unique names {len(capture.parameters_by_name)}, missing indices {len(missing_indices)}.
- Required named parameters observed: {len(REQUIRED_PARAMETERS)-len(required_missing)}/{len(REQUIRED_PARAMETERS)}.
- Request sweep: {sweep_status}; attempted {len(sweep_records)}/{len(dialect_messages)}, matching message observed for {request_json['message_observed']}, unsupported ACK for {request_json['unsupported']}, no ACK/no matching frame for {request_json['no_ack_no_matching_frame']}.
- PX4 exit code: {lifecycle.get('exit_code')}; isolated process cleanup: {lifecycle.get('cleanup_complete')}.
- PX4 source HEAD unchanged and worktree clean after run: {source_integrity['head_unchanged'] and source_integrity['worktree_after_clean']}.

## Primary evidence

- `manifest.json`: schema-oriented capture manifest and artifact hashes.
- `mavlink_messages.jsonl`: every decoded frame with raw hex, phase, host monotonic/wall arrival time, SYSID/COMPID, fields, and onboard-time fields.
- `mavlink_capture.tlog`: MAVLink frames with standard wall-clock tlog prefixes.
- `message_inventory.json`: per ID/name/phase counts, field names, first/last host arrival, onboard-time samples, and SYSID/COMPID counts.
- `parameters_runtime.json`: full observed runtime PARAM snapshot, raw wire float bits, PX4 bytewise decoded values, type/index/count, source IDs, and key named-request results.
- `message_request_sweep.json`: one record per frozen dialect message ID with ACK, matching-frame window, latency, baseline count, and causal-attribution caveat.
- `px4.stdout.log` / `px4.stderr.log`: exact PX4 process output.
- `process_lifecycle.json`: spawned PID/PGID identity, signals, exit code, process-group cleanup, port release, and exact instance temp-object cleanup.
- `source_integrity.json`: HEAD, worktree, and recursive submodule snapshots before/after.
- `attempt_1_none_iris_failed/`: preserved first attempt showing that `none_iris` blocked waiting for an external simulator; its own manifest, logs, hashes, and cleanup evidence remain intact.

## Limitations

""" + "\n".join(f"- {item}" for item in limitations) + "\n"
    readme_path.write_text(readme, encoding="utf-8")

    primary_artifacts = [
        artifact(jsonl_path, "Decoded MAVLink JSONL with raw frame hex and phase/timing metadata"),
        artifact(tlog_path, "Raw MAVLink tlog"),
        artifact(inventory_path, "Message inventory and three-layer counts"),
        artifact(parameters_path, "Runtime parameter snapshot"),
        artifact(requests_path, "Full dialect request sweep"),
        artifact(stdout_path, "PX4 stdout"),
        artifact(stderr_path, "PX4 stderr"),
        artifact(lifecycle_path, "Process exit and cleanup evidence"),
        artifact(source_integrity_path, "Frozen source/worktree verification"),
        artifact(command_path, "Exact commands and protocol actions"),
        artifact(details_path, "Extended capture facts"),
        artifact(driver_log_path, "Capture-driver progress and errors"),
        artifact(dialect_path, "Generated frozen PX4 development dialect decoder"),
        artifact(dialect_log_path, "Dialect generation log"),
        artifact(readme_path, "Human-readable capture report"),
        artifact(Path(__file__).resolve(), "Reproduction script"),
    ]
    for path in sorted(RUNTIME_STATE.rglob("*")):
        if path.is_file():
            primary_artifacts.append(artifact(path, "PX4 isolated runtime-state artifact"))
    prior_attempt = OUT / "attempt_1_none_iris_failed"
    for name, role in [
        ("manifest.json", "Preserved failed none_iris attempt manifest"),
        ("px4.stdout.log", "Preserved failed none_iris startup stdout"),
        ("process_lifecycle.json", "Preserved failed-attempt cleanup evidence"),
    ]:
        path = prior_attempt / name
        if path.is_file():
            primary_artifacts.append(artifact(path, role))

    manifest = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "captures": [{
            "capture_id": args.capture_id,
            "system": "PX4",
            "vehicle": "multicopter",
            "profile": f"px4_sitl_default sihsim_quadx internal headless SIH instance {INSTANCE}",
            "firmware_commit": FIRMWARE_COMMIT,
            "mavlink_commit": MAVLINK_COMMIT,
            "runtime_status": runtime_status,
            "launch_command": shlex.join(px4_command),
            "connection": f"udpout:127.0.0.1:{GCS_UDP_PORT} source={GCS_SOURCE_SYSID}:{GCS_SOURCE_COMPID} target={target_sys}:{target_comp}",
            "phases": [
                {
                    "name": "OTHER" if phase["name"] == PHASE_STARTUP else phase["name"],
                    "start_host_monotonic_ns": phase["start_host_monotonic_ns"],
                    "end_host_monotonic_ns": phase["end_host_monotonic_ns"],
                    "traffic_origin": phase["traffic_origin"],
                    "notes": phase["notes"],
                }
                for phase in capture.phase_ranges
            ],
            "parameter_snapshot": {
                "status": parameter_status,
                "protocol": "PARAM",
                "path": relative_artifact(parameters_path),
                "sha256": parameter_hash,
                "expected_count": expected,
                "received_count": capture.parameter_received_count,
                "unique_parameter_count": len(capture.parameters_by_name),
                "missing_indices": missing_indices,
                "key_values": key_values,
            },
            "message_summary": {
                "path": relative_artifact(inventory_path),
                "sha256": inventory_hash,
                "total_message_count": inventory["total_message_count"],
                "distinct_message_count": inventory["distinct_message_count"],
                "baseline_distinct_message_count": inventory["baseline_distinct_message_count"],
                "host_clock": "CLOCK_MONOTONIC_NS",
            },
            "request_sweep": {
                "status": sweep_status,
                "path": relative_artifact(requests_path),
                "sha256": requests_hash,
                "attempted": len(sweep_records),
                "message_observed": request_json["message_observed"],
                "unsupported": request_json["unsupported"],
                "no_response": request_json["no_ack_no_matching_frame"],
            },
            "clock_domains": [
                "CLOCK_MONOTONIC_NS",
                "HOST_UTC_WALL_FOR_TLOG_ONLY",
                "PX4_BOOT_OR_UNIX_OR_PROTOCOL_SPECIFIC_ONBOARD_FIELDS_AS_NAMED",
            ],
            "process_cleanup": (
                f"pid={lifecycle.get('pid')} pgid={lifecycle.get('pgid')} "
                f"exit_code={lifecycle.get('exit_code')} cleanup_complete={lifecycle.get('cleanup_complete')}"
            ),
            "artifacts": primary_artifacts,
            "limitations": limitations,
        }],
        "property_parameters": property_parameters,
        "implementation_satisfaction": "NOT_ASSESSED",
    }
    write_json(manifest_path, manifest)
    print(
        f"FINAL status={runtime_status} manifest={manifest_path} "
        f"messages={inventory['total_message_count']} params={len(capture.parameters_by_name)} "
        f"sweep={len(sweep_records)}/{len(dialect_messages)}",
        flush=True,
    )
    return 0 if runtime_status in {"COMPLETE", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
