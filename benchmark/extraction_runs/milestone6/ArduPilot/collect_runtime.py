#!/usr/bin/env python3
"""Collect read-only ArduPilot SITL runtime evidence for TAFuzz Milestone 6.

The collector deliberately separates passive startup/baseline traffic from
PARAM_REQUEST_LIST traffic and MAV_CMD_REQUEST_MESSAGE traffic.  It never
writes a persistent firmware parameter.  Every vehicle is launched directly
from the frozen build in its own working directory, HOME, port set, process
group, and output tree.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import errno
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shlex
import signal
import struct
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple


sys.dont_write_bytecode = True

WORKSPACE = Path("/home/lqq/project/TAFuzz")
FIRMWARE = WORKSPACE / "baseline/ardupilot"
OUT_ROOT = WORKSPACE / "benchmark/extraction_runs/milestone6/ArduPilot"
RUNS_ROOT = OUT_ROOT / "runs"
FROZEN_DIALECT = OUT_ROOT / "dialect_generated.py"
MESSAGE_CATALOG = WORKSPACE / "benchmark/mavlink_catalog/messages_and_fields.json"
TIME_FIELDS_CSV = WORKSPACE / "benchmark/mavlink_catalog/time_fields.csv"
PROPERTY_CATALOG = WORKSPACE / "benchmark/ArduPilot/property_catalog.json"
EXPECTED_FIRMWARE_COMMIT = "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e"
EXPECTED_MAVLINK_COMMIT = "13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472"
HARNESS_SYSID = 250
HARNESS_COMPID = 190  # MAV_COMP_ID_MISSIONPLANNER
HOME_LOCATION = "-35.363261,149.165230,584,353"


PROFILES: List[Dict[str, Any]] = [
    {
        "key": "Copter",
        "vehicle": "ArduCopter",
        "binary": "arducopter",
        "model": "quad",
        "sysid": 151,
        "udp_port": 19101,
        "base_port": 20100,
        "rc_in_port": 21101,
        "sim_port_in": 22101,
        "sim_port_out": 22102,
        "irlock_port": 23101,
        "time_parameters": [
            ("ARD-COPTER-GCS-001", "FS_GCS_TIMEOUT", "s"),
            ("ARD-COPTER-GUID-002", "GUID_TIMEOUT", "s"),
            ("ARD-COPTER-RTL-003", "RTL_LOIT_TIME", "ms"),
            ("ARD-SHARED-BATT-001", "BATT_LOW_TIMER", "s"),
        ],
        "required_parameters": [
            "FS_GCS_TIMEOUT", "FS_GCS_ENABLE", "FS_OPTIONS",
            "MAV_GCS_SYSID", "MAV_GCS_SYSID_HI", "GUID_TIMEOUT",
            "RTL_LOIT_TIME", "RTL_ALT", "RTL_ALT_FINAL", "RTL_CONE_SLOPE",
            "RTL_OPTIONS", "LAND_SPEED", "LAND_SPEED_HIGH",
            "SYSID_THISMAV", "SERIAL0_PROTOCOL", "SR0_PARAMS",
        ],
    },
    {
        "key": "Plane",
        "vehicle": "ArduPlane",
        "binary": "arduplane",
        "model": "plane",
        "sysid": 152,
        "udp_port": 19102,
        "base_port": 20200,
        "rc_in_port": 21201,
        "sim_port_in": 22201,
        "sim_port_out": 22202,
        "irlock_port": 23201,
        "time_parameters": [
            ("ARD-PLANE-TAKEOFF-001", "TKOFF_TIMEOUT", "s"),
            ("ARD-SHARED-BATT-001", "BATT_LOW_TIMER", "s"),
        ],
        "required_parameters": [
            "TKOFF_TIMEOUT", "TKOFF_THR_MINACC", "TKOFF_THR_MINSPD",
            "TKOFF_THR_DELAY", "TKOFF_THR_MAX", "TKOFF_THR_MAX_T",
            "TKOFF_LVL_ALT", "TKOFF_ROTATE_SPD", "TKOFF_ALT",
            "ARMING_CHECK", "MAV_GCS_SYSID", "MAV_GCS_SYSID_HI",
            "SYSID_THISMAV", "SERIAL0_PROTOCOL", "SR0_PARAMS",
        ],
    },
    {
        "key": "Rover",
        "vehicle": "Rover",
        "binary": "ardurover",
        "model": "rover",
        "sysid": 153,
        "udp_port": 19103,
        "base_port": 20300,
        "rc_in_port": 21301,
        "sim_port_in": 22301,
        "sim_port_out": 22302,
        "irlock_port": 23301,
        "time_parameters": [
            ("ARD-ROVER-RCFS-001", "FS_TIMEOUT", "s"),
            ("ARD-ROVER-CRASH-002", "CRASH_TIMEOUT", "s"),
            ("ARD-SHARED-BATT-001", "BATT_LOW_TIMER", "s"),
        ],
        "required_parameters": [
            "FS_TIMEOUT", "FS_THR_ENABLE", "FS_THR_VALUE", "FS_ACTION",
            "FS_OPTIONS", "RC_FS_TIMEOUT", "RCMAP_THROTTLE",
            "FS_GCS_ENABLE", "FS_GCS_TIMEOUT", "MAV_GCS_SYSID",
            "MAV_GCS_SYSID_HI", "FS_CRASH_CHECK", "CRASH_THR_MIN",
            "CRASH_VEL_MIN", "CRASH_TRAT_MIN", "CRASH_TIMEOUT",
            "CRASH_ANGLE", "FRAME_CLASS", "FRAME_TYPE", "SYSID_THISMAV",
            "SERIAL0_PROTOCOL", "SR0_PARAMS",
        ],
    },
]


BATTERY_PARAMETERS = [
    "BATT_MONITOR", "BATT_CAPACITY", "BATT_LOW_TIMER", "BATT_FS_VOLTSRC",
    "BATT_LOW_VOLT", "BATT_LOW_MAH", "BATT_CRT_VOLT", "BATT_CRT_MAH",
    "BATT_FS_LOW_ACT", "BATT_FS_CRT_ACT",
]


RELEVANT_STREAM_IDS = [
    0,    # HEARTBEAT
    1,    # SYS_STATUS
    2,    # SYSTEM_TIME
    24,   # GPS_RAW_INT
    30,   # ATTITUDE
    32,   # LOCAL_POSITION_NED
    33,   # GLOBAL_POSITION_INT
    36,   # SERVO_OUTPUT_RAW
    65,   # RC_CHANNELS
    74,   # VFR_HUD
    83,   # ATTITUDE_TARGET
    85,   # POSITION_TARGET_LOCAL_NED
    147,  # BATTERY_STATUS
    148,  # AUTOPILOT_VERSION
    242,  # HOME_POSITION
    245,  # EXTENDED_SYS_STATE
    253,  # STATUSTEXT (event-driven; interval request may be unsupported)
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, bytearray):
        return {"encoding": "hex", "value": bytes(value).hex()}
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        return {"non_finite_float": repr(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(json_safe(value), f, ensure_ascii=False, indent=2, sort_keys=True,
                  allow_nan=False)
        f.write("\n")


def append_jsonl(handle: Any, value: Any) -> None:
    handle.write(json.dumps(json_safe(value), ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False))
    handle.write("\n")
    handle.flush()


def run_text(command: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    p = subprocess.run(command, cwd=str(cwd) if cwd else None, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "command": shlex.join(command),
        "exit_code": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def git_state() -> Dict[str, Any]:
    head = run_text(["git", "-C", str(FIRMWARE), "rev-parse", "HEAD"])
    status = run_text(["git", "-C", str(FIRMWARE), "status", "--short"])
    mav_head = run_text(["git", "-C", str(FIRMWARE / "modules/mavlink"),
                         "rev-parse", "HEAD"])
    return {
        "firmware_head": head["stdout"].strip(),
        "firmware_head_exit_code": head["exit_code"],
        "firmware_status_short": status["stdout"].splitlines(),
        "firmware_status_exit_code": status["exit_code"],
        "mavlink_head": mav_head["stdout"].strip(),
        "mavlink_head_exit_code": mav_head["exit_code"],
        "captured_at": utc_now(),
    }


def matching_processes() -> List[Dict[str, Any]]:
    binaries = {str((FIRMWARE / "build/sitl/bin" / p["binary"]).resolve())
                for p in PROFILES}
    found: List[Dict[str, Any]] = []
    proc = Path("/proc")
    for d in proc.iterdir():
        if not d.name.isdigit():
            continue
        try:
            raw = (d / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if not raw:
            continue
        argv = [x.decode("utf-8", errors="replace") for x in raw.split(b"\0") if x]
        if not argv:
            continue
        if any(str(Path(arg).resolve()) in binaries for arg in argv if "/" in arg):
            found.append({"pid": int(d.name), "argv": argv})
    return sorted(found, key=lambda x: x["pid"])


def load_generated_dialect() -> Any:
    spec = importlib.util.spec_from_file_location("tafuzz_frozen_mavlink_all",
                                                  FROZEN_DIALECT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generated dialect: {FROZEN_DIALECT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate_dialect_if_needed() -> Dict[str, Any]:
    if FROZEN_DIALECT.is_file():
        return {
            "status": "REUSED",
            "path": str(FROZEN_DIALECT.relative_to(WORKSPACE)),
            "sha256": sha256_file(FROZEN_DIALECT),
        }
    command = [
        sys.executable,
        "-m", "pymavlink.tools.mavgen",
        "--lang", "Python3",
        "--wire-protocol", "2.0",
        "--output", str(OUT_ROOT / "dialect_generated"),
        str(FIRMWARE / "modules/mavlink/message_definitions/v1.0/all.xml"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(FIRMWARE / "modules/mavlink")
    p = subprocess.run(command, cwd=str(WORKSPACE), env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    generated = OUT_ROOT / "dialect_generated.py"
    if p.returncode != 0 or not generated.is_file():
        raise RuntimeError(f"mavgen failed: exit={p.returncode}\n{p.stdout}\n{p.stderr}")
    return {
        "status": "GENERATED",
        "command": shlex.join(command),
        "exit_code": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
        "path": str(generated.relative_to(WORKSPACE)),
        "sha256": sha256_file(generated),
    }


def load_message_specs() -> List[Dict[str, Any]]:
    catalog = json.loads(MESSAGE_CATALOG.read_text(encoding="utf-8"))
    system = next(s for s in catalog["systems"] if s["system"] == "ArduPilot")
    messages = sorted(system["messages"], key=lambda m: int(m["message_id"]))
    ids = [int(m["message_id"]) for m in messages]
    if len(ids) != 352 or len(ids) != len(set(ids)):
        raise RuntimeError(f"unexpected frozen ArduPilot message set: {len(ids)}")
    return messages


def load_time_field_specs() -> Dict[int, List[Dict[str, str]]]:
    result: Dict[int, List[Dict[str, str]]] = {}
    with TIME_FIELDS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row["system"] != "ArduPilot" or
                    row["entity_kind"] != "message_field" or
                    row["temporal_kind"] != "timestamp"):
                continue
            result.setdefault(int(row["container_id"]), []).append({
                "field": row["item_name"],
                "units": row["units"],
                "clock_domain": row["clock_domain"],
                "clock_semantics_explicit_in_definition":
                    row["clock_semantics_explicit_in_definition"],
            })
    return result


def enum_name(dialect: Any, enum: str, value: int) -> str:
    try:
        return dialect.enums[enum][int(value)].name
    except Exception:
        return f"UNKNOWN_{value}"


def message_name_by_id(dialect: Any, message_id: int, fallback: str = "") -> str:
    try:
        return dialect.mavlink_map[int(message_id)].name
    except Exception:
        return fallback or f"MSG_{message_id}"


class MessageRecorder:
    def __init__(self, run_dir: Path, time_fields: Dict[int, List[Dict[str, str]]],
                 capture_start_ns: int):
        self.run_dir = run_dir
        self.time_fields = time_fields
        self.capture_start_ns = capture_start_ns
        self.phase = "STARTUP"
        self.total = 0
        self.stats: Dict[Tuple[int, str], Dict[str, Any]] = {}
        self.jsonl_path = run_dir / "messages.jsonl"
        self.jsonl = self.jsonl_path.open("w", encoding="utf-8")

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def record(self, msg: Any) -> Dict[str, Any]:
        now_ns = time.monotonic_ns()
        wall = utc_now()
        msg_type = msg.get_type()
        try:
            msg_id = int(msg.get_msgId())
        except Exception:
            msg_id = -1
        try:
            src_system = int(msg.get_srcSystem())
            src_component = int(msg.get_srcComponent())
        except Exception:
            src_system = -1
            src_component = -1
        try:
            fields = msg.to_dict()
        except Exception as exc:
            fields = {"decode_error": repr(exc), "repr": repr(msg)}
        fields = json_safe(fields)
        rec = {
            "host_monotonic_ns": now_ns,
            "host_monotonic_since_capture_start_ns": now_ns - self.capture_start_ns,
            "host_wall_utc": wall,
            "phase": self.phase,
            "message_id": msg_id,
            "message_name": msg_type,
            "source_system": src_system,
            "source_component": src_component,
            "fields": fields,
        }
        append_jsonl(self.jsonl, rec)
        self.total += 1

        key = (msg_id, msg_type)
        stat = self.stats.setdefault(key, {
            "message_id": msg_id,
            "message_name": msg_type,
            "count": 0,
            "fields": set(),
            "source_identities": {},
            "phase_counts": {},
            "first_host_monotonic_ns": now_ns,
            "last_host_monotonic_ns": now_ns,
            "first_host_wall_utc": wall,
            "last_host_wall_utc": wall,
            "time_fields": {},
        })
        stat["count"] += 1
        stat["last_host_monotonic_ns"] = now_ns
        stat["last_host_wall_utc"] = wall
        if isinstance(fields, dict):
            stat["fields"].update(k for k in fields if k != "mavpackettype")
        ident = f"{src_system}:{src_component}"
        stat["source_identities"][ident] = stat["source_identities"].get(ident, 0) + 1
        stat["phase_counts"][self.phase] = stat["phase_counts"].get(self.phase, 0) + 1

        if isinstance(fields, dict):
            for tf in self.time_fields.get(msg_id, []):
                name = tf["field"]
                if name not in fields:
                    continue
                ts = stat["time_fields"].setdefault(name, {
                    "units": tf["units"],
                    "clock_domain": tf["clock_domain"],
                    "clock_semantics_explicit_in_definition":
                        tf["clock_semantics_explicit_in_definition"],
                    "sample_count": 0,
                    "first_value": fields[name],
                    "last_value": fields[name],
                    "samples": [],
                })
                ts["sample_count"] += 1
                ts["last_value"] = fields[name]
                if len(ts["samples"]) < 5:
                    ts["samples"].append({
                        "value": fields[name],
                        "host_monotonic_ns": now_ns,
                        "phase": self.phase,
                    })
        return rec

    def count_for_id_in_phase(self, message_id: int, phase: str) -> int:
        return sum(s["phase_counts"].get(phase, 0)
                   for (mid, _), s in self.stats.items() if mid == message_id)

    def summary(self) -> Dict[str, Any]:
        rows = []
        for _, stat in sorted(self.stats.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            row = dict(stat)
            row["fields"] = sorted(row["fields"])
            row["source_identities"] = [
                {"system_component": k, "count": v}
                for k, v in sorted(row["source_identities"].items())
            ]
            rows.append(row)
        return {
            "schema_version": "1.0",
            "host_clock": "CLOCK_MONOTONIC_NS",
            "capture_start_host_monotonic_ns": self.capture_start_ns,
            "total_message_count": self.total,
            "distinct_message_key_count": len(rows),
            "baseline_distinct_message_key_count": sum(
                1 for r in rows if r["phase_counts"].get("BASELINE", 0) > 0),
            "messages": rows,
        }

    def close(self) -> None:
        self.jsonl.close()


class ParameterRecorder:
    INTEGER_TYPES = {1, 2, 3, 4, 5, 6}

    def __init__(self, run_dir: Path, dialect: Any, target_system: int):
        self.dialect = dialect
        self.target_system = target_system
        self.path = run_dir / "parameters.jsonl"
        self.handle = self.path.open("w", encoding="utf-8")
        self.records_by_index: Dict[int, Dict[str, Any]] = {}
        self.records_by_name: Dict[str, Dict[str, Any]] = {}
        self.received_response_count = 0
        self.expected_count: Optional[int] = None

    @staticmethod
    def parameter_name(value: Any) -> str:
        if isinstance(value, bytes):
            return value.split(b"\0", 1)[0].decode("ascii", errors="replace")
        return str(value).split("\0", 1)[0]

    def record(self, msg: Any, phase: str, host_monotonic_ns: int,
               host_wall_utc: str) -> None:
        if msg.get_type() != "PARAM_VALUE" or int(msg.get_srcSystem()) != self.target_system:
            return
        name = self.parameter_name(msg.param_id)
        wire_value = float(msg.param_value)
        ptype = int(msg.param_type)
        decoded: Any = int(round(wire_value)) if ptype in self.INTEGER_TYPES else wire_value
        index = int(msg.param_index)
        count = int(msg.param_count)
        rec = {
            "name": name,
            "wire_value": wire_value,
            "decoded_value": decoded,
            "param_type": ptype,
            "param_type_name": enum_name(self.dialect, "MAV_PARAM_TYPE", ptype),
            "param_index": index,
            "param_count": count,
            "source_system": int(msg.get_srcSystem()),
            "source_component": int(msg.get_srcComponent()),
            "received_host_monotonic_ns": host_monotonic_ns,
            "received_host_wall_utc": host_wall_utc,
            "phase": phase,
        }
        append_jsonl(self.handle, rec)
        self.received_response_count += 1
        if count >= 0:
            self.expected_count = max(self.expected_count or 0, count)
        if index >= 0:
            if index not in self.records_by_index:
                self.records_by_index[index] = rec
            self.records_by_name[name] = self.records_by_index[index]

    def complete(self) -> bool:
        return (self.expected_count is not None and self.expected_count > 0 and
                len(self.records_by_index) >= self.expected_count)

    def missing_indices(self) -> List[int]:
        if self.expected_count is None:
            return []
        return sorted(set(range(self.expected_count)) - set(self.records_by_index))

    def snapshot(self) -> Dict[str, Any]:
        missing = self.missing_indices()
        status = "COMPLETE" if self.complete() and not missing else (
            "PARTIAL" if self.records_by_index else "FAILED")
        return {
            "schema_version": "1.0",
            "status": status,
            "protocol": "PARAM_REQUEST_LIST/PARAM_VALUE",
            "wire_encoding_note": (
                "ArduPilot emits AP_Param::cast_to_float() as PARAM_VALUE.param_value; "
                "integer decoded_value is numeric rounding according to param_type, "
                "not reinterpretation of source defaults."
            ),
            "expected_count": self.expected_count,
            "received_response_count": self.received_response_count,
            "unique_parameter_count": len(self.records_by_index),
            "unique_parameter_name_count": len(self.records_by_name),
            "missing_indices": missing,
            "parameters": [self.records_by_index[i]
                           for i in sorted(self.records_by_index)],
        }

    def close(self) -> None:
        self.handle.close()


class VehicleCapture:
    def __init__(self, profile: Dict[str, Any], args: argparse.Namespace,
                 dialect: Any, message_specs: List[Dict[str, Any]],
                 time_fields: Dict[int, List[Dict[str, str]]]):
        self.profile = profile
        self.args = args
        self.dialect = dialect
        self.message_specs = message_specs
        self.time_fields = time_fields
        self.run_dir = RUNS_ROOT / profile["key"]
        self.runtime_dir = self.run_dir / "runtime"
        self.home_dir = self.run_dir / "home"
        self.tmp_dir = self.run_dir / "tmp"
        self.phases: List[Dict[str, Any]] = []
        self.outbound_path = self.run_dir / "outbound_actions.jsonl"
        self.outbound: Any = None
        self.process: Optional[subprocess.Popen[Any]] = None
        self.process_stdout: Any = None
        self.process_stderr: Any = None
        self.conn: Any = None
        self.recorder: Optional[MessageRecorder] = None
        self.params: Optional[ParameterRecorder] = None
        self.target_component: Optional[int] = None
        self.capture_start_ns = 0
        self.cleanup: Dict[str, Any] = {}
        self.failures: List[str] = []
        self.last_gcs_heartbeat_ns = 0

    def begin_phase(self, name: str, traffic_origin: str, notes: str = "") -> Dict[str, Any]:
        phase = {
            "name": name,
            "start_host_monotonic_ns": time.monotonic_ns(),
            "start_host_wall_utc": utc_now(),
            "end_host_monotonic_ns": None,
            "end_host_wall_utc": None,
            "traffic_origin": traffic_origin,
            "notes": notes,
        }
        self.phases.append(phase)
        if self.recorder:
            self.recorder.set_phase(name)
        print(f"[{self.profile['key']}] phase {name} started", flush=True)
        return phase

    def end_phase(self, phase: Dict[str, Any]) -> None:
        phase["end_host_monotonic_ns"] = time.monotonic_ns()
        phase["end_host_wall_utc"] = utc_now()
        phase["duration_seconds"] = (
            phase["end_host_monotonic_ns"] - phase["start_host_monotonic_ns"]
        ) / 1e9
        print(f"[{self.profile['key']}] phase {phase['name']} ended "
              f"({phase['duration_seconds']:.3f}s)", flush=True)

    def launch_command(self) -> List[str]:
        p = self.profile
        return [
            str((FIRMWARE / "build/sitl/bin" / p["binary"]).resolve()),
            "--wipe",
            "--model", p["model"],
            "--home", HOME_LOCATION,
            "--speedup", "1",
            "--base-port", str(p["base_port"]),
            "--rc-in-port", str(p["rc_in_port"]),
            "--sim-port-in", str(p["sim_port_in"]),
            "--sim-port-out", str(p["sim_port_out"]),
            "--irlock-port", str(p["irlock_port"]),
            "--serial0", f"udpclient:127.0.0.1:{p['udp_port']}",
            "--sysid", str(p["sysid"]),
            "--autotest-dir", str((FIRMWARE / "Tools/autotest").resolve()),
        ]

    def prepare(self) -> None:
        if self.run_dir.exists():
            raise RuntimeError(f"refusing to overwrite existing capture: {self.run_dir}")
        self.runtime_dir.mkdir(parents=True)
        self.home_dir.mkdir()
        self.tmp_dir.mkdir()
        (self.home_dir / ".config").mkdir()
        (self.home_dir / ".cache").mkdir()
        self.outbound = self.outbound_path.open("w", encoding="utf-8")

    def open_connection(self) -> None:
        from pymavlink import mavutil
        mavutil.mavlink = self.dialect
        self.conn = mavutil.mavlink_connection(
            f"udpin:127.0.0.1:{self.profile['udp_port']}",
            source_system=HARNESS_SYSID,
            source_component=HARNESS_COMPID,
            robust_parsing=True,
            use_native=False,
            dialect=None,
        )
        self.conn.setup_logfile(str(self.run_dir / "messages.tlog"))
        self.conn.setup_logfile_raw(str(self.run_dir / "messages.raw"))

    def start_process(self) -> None:
        command = self.launch_command()
        env = os.environ.copy()
        env.update({
            "HOME": str(self.home_dir),
            "XDG_CONFIG_HOME": str(self.home_dir / ".config"),
            "XDG_CACHE_HOME": str(self.home_dir / ".cache"),
            "TMPDIR": str(self.tmp_dir),
        })
        write_json(self.run_dir / "launch.json", {
            "argv": command,
            "shell_command": shlex.join(command),
            "working_directory": str(self.runtime_dir),
            "environment_overrides": {k: env[k] for k in
                                      ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "TMPDIR")},
            "binary_sha256": sha256_file(Path(command[0])),
            "started_at_utc": utc_now(),
            "started_host_monotonic_ns": time.monotonic_ns(),
        })
        (self.run_dir / "command.txt").write_text(shlex.join(command) + "\n",
                                                   encoding="utf-8")
        self.process_stdout = (self.run_dir / "stdout.log").open("w", encoding="utf-8")
        self.process_stderr = (self.run_dir / "stderr.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            command,
            cwd=str(self.runtime_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self.process_stdout,
            stderr=self.process_stderr,
            text=True,
            start_new_session=True,
        )
        self.capture_start_ns = time.monotonic_ns()
        self.recorder = MessageRecorder(self.run_dir, self.time_fields,
                                        self.capture_start_ns)
        self.params = ParameterRecorder(self.run_dir, self.dialect,
                                        self.profile["sysid"])
        print(f"[{self.profile['key']}] started PID {self.process.pid}", flush=True)

    def log_outbound(self, kind: str, fields: Dict[str, Any]) -> None:
        append_jsonl(self.outbound, {
            "host_monotonic_ns": time.monotonic_ns(),
            "host_wall_utc": utc_now(),
            "phase": self.recorder.phase if self.recorder else "UNKNOWN",
            "kind": kind,
            "source_system": HARNESS_SYSID,
            "source_component": HARNESS_COMPID,
            "target_system": self.profile["sysid"],
            "target_component": self.target_component,
            "fields": fields,
        })

    def receive(self, timeout: float = 0.1) -> Any:
        msg = self.conn.recv_match(blocking=True, timeout=timeout)
        if msg is None:
            return None
        rec = self.recorder.record(msg)
        self.params.record(msg, rec["phase"], rec["host_monotonic_ns"],
                           rec["host_wall_utc"])
        return msg

    def send_gcs_heartbeat_if_due(self, interval_s: float = 1.0) -> None:
        now = time.monotonic_ns()
        if now - self.last_gcs_heartbeat_ns < int(interval_s * 1e9):
            return
        self.conn.mav.heartbeat_send(
            self.dialect.MAV_TYPE_GCS,
            self.dialect.MAV_AUTOPILOT_INVALID,
            0,
            0,
            self.dialect.MAV_STATE_ACTIVE,
        )
        self.last_gcs_heartbeat_ns = now
        self.log_outbound("GCS_HEARTBEAT", {
            "type": "MAV_TYPE_GCS",
            "autopilot": "MAV_AUTOPILOT_INVALID",
            "system_status": "MAV_STATE_ACTIVE",
        })

    def receive_for(self, seconds: float, send_heartbeat: bool) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"SITL exited early with {self.process.returncode}")
            if send_heartbeat:
                self.send_gcs_heartbeat_if_due()
            self.receive(min(0.1, max(0.0, deadline - time.monotonic())))

    def wait_for_target(self) -> None:
        phase = self.begin_phase(
            "STARTUP",
            "Passive UDP receive only; no PARAM or MAV_CMD request was sent.",
            "Stable target is defined by receiving the expected vehicle HEARTBEAT, "
            "then observing a three-second passive warmup.",
        )
        deadline = time.monotonic() + self.args.startup_timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"SITL exited during startup: {self.process.returncode}")
            msg = self.receive(0.2)
            if (msg is not None and msg.get_type() == "HEARTBEAT" and
                    int(msg.get_srcSystem()) == self.profile["sysid"]):
                self.target_component = int(msg.get_srcComponent())
                self.conn.target_system = self.profile["sysid"]
                self.conn.target_component = self.target_component
                break
        else:
            raise RuntimeError("target HEARTBEAT timeout")
        self.receive_for(self.args.warmup_seconds, send_heartbeat=False)
        self.end_phase(phase)

    def baseline(self) -> None:
        phase = self.begin_phase(
            "BASELINE",
            "Passive firmware-default stream only; no outbound request and no harness heartbeat.",
            "This phase is measured after target HEARTBEAT and passive warmup. It is "
            "kept separate so later request responses are not classified as default streams.",
        )
        self.receive_for(self.args.baseline_seconds, send_heartbeat=False)
        self.end_phase(phase)
        if phase["duration_seconds"] < 10.0:
            raise RuntimeError("baseline phase shorter than ten seconds")

    def request_parameter_list(self) -> None:
        self.conn.mav.param_request_list_send(self.profile["sysid"],
                                              self.target_component)
        self.log_outbound("PARAM_REQUEST_LIST", {})

    def parameter_download(self) -> Dict[str, Any]:
        phase = self.begin_phase(
            "PARAMETER_DOWNLOAD",
            "Harness GCS HEARTBEAT plus PARAM_REQUEST_LIST/PARAM_REQUEST_READ; no PARAM_SET.",
            "Full runtime parameter enumeration. Source defaults are never substituted.",
        )
        self.send_gcs_heartbeat_if_due(interval_s=0)
        self.request_parameter_list()
        deadline = time.monotonic() + self.args.param_timeout
        last_progress = time.monotonic()
        previous_count = 0
        list_retries = 0
        while time.monotonic() < deadline and not self.params.complete():
            if self.process.poll() is not None:
                raise RuntimeError(f"SITL exited during parameter download: {self.process.returncode}")
            self.send_gcs_heartbeat_if_due()
            self.receive(0.1)
            current = len(self.params.records_by_index)
            if current != previous_count:
                previous_count = current
                last_progress = time.monotonic()
            elif time.monotonic() - last_progress > 8.0 and list_retries < 2:
                self.request_parameter_list()
                list_retries += 1
                last_progress = time.monotonic()

        # A bounded, read-only repair pass for any dropped list responses.
        missing_before_repair = self.params.missing_indices()
        if missing_before_repair and len(missing_before_repair) <= 200:
            for index in missing_before_repair:
                self.conn.mav.param_request_read_send(
                    self.profile["sysid"], self.target_component, b"", index)
                self.log_outbound("PARAM_REQUEST_READ", {"param_index": index})
                repair_deadline = time.monotonic() + 0.08
                while time.monotonic() < repair_deadline:
                    self.send_gcs_heartbeat_if_due()
                    self.receive(0.02)
            final_deadline = time.monotonic() + min(10.0, self.args.param_timeout / 4)
            while time.monotonic() < final_deadline and not self.params.complete():
                self.send_gcs_heartbeat_if_due()
                self.receive(0.1)

        self.end_phase(phase)
        snapshot = self.params.snapshot()
        snapshot["list_retries"] = list_retries
        snapshot["missing_before_read_repair"] = missing_before_repair
        write_json(self.run_dir / "parameters.json", snapshot)
        print(f"[{self.profile['key']}] parameters: {snapshot['status']} "
              f"{snapshot['unique_parameter_count']}/{snapshot['expected_count']}",
              flush=True)
        return snapshot

    def wait_for_ack_and_message(self, command: int, requested_message_id: int,
                                 max_wait: float) -> Tuple[Any, Any, Optional[int]]:
        ack = None
        response = None
        response_ns: Optional[int] = None
        deadline = time.monotonic() + max_wait
        ack_received_at: Optional[float] = None
        while time.monotonic() < deadline:
            self.send_gcs_heartbeat_if_due()
            msg = self.receive(min(0.04, max(0.0, deadline - time.monotonic())))
            if msg is None:
                continue
            mid = int(msg.get_msgId()) if hasattr(msg, "get_msgId") else -1
            if (response is None and mid == requested_message_id and
                    int(msg.get_srcSystem()) == self.profile["sysid"]):
                response = msg
                response_ns = time.monotonic_ns()
            if (msg.get_type() == "COMMAND_ACK" and int(msg.command) == command and
                    int(msg.get_srcSystem()) == self.profile["sysid"] and ack is None):
                ack = msg
                ack_received_at = time.monotonic()
            if ack is not None:
                result = int(ack.result)
                if result in {
                    self.dialect.MAV_RESULT_UNSUPPORTED,
                    self.dialect.MAV_RESULT_DENIED,
                    self.dialect.MAV_RESULT_FAILED,
                }:
                    break
                if response is not None:
                    break
                if ack_received_at is not None and time.monotonic() - ack_received_at > 0.18:
                    break
            elif response is not None:
                # Some implementations can emit the requested packet without an ACK.
                if response_ns is not None and time.monotonic_ns() - response_ns > 50_000_000:
                    break
        return ack, response, response_ns

    def request_sweep(self) -> Dict[str, Any]:
        phase = self.begin_phase(
            "REQUEST_SWEEP",
            "One serial MAV_CMD_REQUEST_MESSAGE (command 512) per frozen all.xml message ID.",
            "ACK and message observation are recorded independently. A message seen in "
            "the request window is not claimed causal when it was already a baseline stream.",
        )
        results_path = self.run_dir / "request_sweep.jsonl"
        results_handle = results_path.open("w", encoding="utf-8")
        results: List[Dict[str, Any]] = []
        try:
            total = len(self.message_specs)
            for ordinal, spec in enumerate(self.message_specs, 1):
                message_id = int(spec["message_id"])
                message_name = spec["name"]
                sent_ns = time.monotonic_ns()
                self.conn.mav.command_long_send(
                    self.profile["sysid"], self.target_component,
                    self.dialect.MAV_CMD_REQUEST_MESSAGE, 0,
                    float(message_id), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                )
                self.log_outbound("MAV_CMD_REQUEST_MESSAGE", {
                    "command": int(self.dialect.MAV_CMD_REQUEST_MESSAGE),
                    "requested_message_id": message_id,
                    "requested_message_name": message_name,
                    "ordinal": ordinal,
                    "total": total,
                })
                ack, response, response_ns = self.wait_for_ack_and_message(
                    self.dialect.MAV_CMD_REQUEST_MESSAGE,
                    message_id,
                    self.args.sweep_timeout,
                )
                ack_result = int(ack.result) if ack is not None else None
                record = {
                    "ordinal": ordinal,
                    "message_id": message_id,
                    "message_name": message_name,
                    "sent_host_monotonic_ns": sent_ns,
                    "baseline_count": self.recorder.count_for_id_in_phase(
                        message_id, "BASELINE"),
                    "baseline_present": self.recorder.count_for_id_in_phase(
                        message_id, "BASELINE") > 0,
                    "command_ack_received": ack is not None,
                    "command_ack_result": ack_result,
                    "command_ack_result_name": (
                        enum_name(self.dialect, "MAV_RESULT", ack_result)
                        if ack_result is not None else None),
                    "command_ack_fields": ack.to_dict() if ack is not None else None,
                    "requested_message_observed_in_window": response is not None,
                    "observed_message_name": response.get_type() if response is not None else None,
                    "observed_latency_ns": (
                        response_ns - sent_ns if response_ns is not None else None),
                    "observation_causality": (
                        "AMBIGUOUS_BASELINE_PERIODIC"
                        if response is not None and self.recorder.count_for_id_in_phase(
                            message_id, "BASELINE") > 0
                        else ("POST_REQUEST_WINDOW_OBSERVATION" if response is not None
                              else "NOT_OBSERVED")
                    ),
                }
                append_jsonl(results_handle, record)
                results.append(record)
                if ordinal % 50 == 0 or ordinal == total:
                    print(f"[{self.profile['key']}] request sweep {ordinal}/{total}",
                          flush=True)
        finally:
            results_handle.close()
        self.end_phase(phase)
        ack_counts: Dict[str, int] = {}
        for r in results:
            name = r["command_ack_result_name"] or "NO_ACK"
            ack_counts[name] = ack_counts.get(name, 0) + 1
        summary = {
            "schema_version": "1.0",
            "status": "COMPLETE" if len(results) == len(self.message_specs) else "PARTIAL",
            "frozen_catalog_path": str(MESSAGE_CATALOG.relative_to(WORKSPACE)),
            "frozen_unique_message_ids": len(self.message_specs),
            "attempted": len(results),
            "command": "MAV_CMD_REQUEST_MESSAGE (512)",
            "per_request_max_wait_seconds": self.args.sweep_timeout,
            "ack_result_counts": ack_counts,
            "message_observed": sum(r["requested_message_observed_in_window"] for r in results),
            "unsupported": sum(r["command_ack_result"] == self.dialect.MAV_RESULT_UNSUPPORTED
                               for r in results),
            "no_response": sum(not r["command_ack_received"] and
                               not r["requested_message_observed_in_window"]
                               for r in results),
            "accepted_without_observed_message": sum(
                r["command_ack_result"] == self.dialect.MAV_RESULT_ACCEPTED and
                not r["requested_message_observed_in_window"] for r in results),
            "results": results,
            "limitation": (
                "COMMAND_ACK has no request sequence or requested message ID. Because "
                "requests are serialized, the first target ACK for command 512 is paired; "
                "late ACKs remain a possible ambiguity. Baseline-present messages are not "
                "claimed to have been caused by the request."
            ),
        }
        write_json(self.run_dir / "request_sweep.json", summary)
        return summary

    def interval_request(self, message_id: int, interval_us: int) -> Dict[str, Any]:
        sent_ns = time.monotonic_ns()
        self.conn.mav.command_long_send(
            self.profile["sysid"], self.target_component,
            self.dialect.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
            float(message_id), float(interval_us), 0.0, 0.0, 0.0, 0.0, 0.0,
        )
        self.log_outbound("MAV_CMD_SET_MESSAGE_INTERVAL", {
            "command": int(self.dialect.MAV_CMD_SET_MESSAGE_INTERVAL),
            "message_id": message_id,
            "message_name": message_name_by_id(self.dialect, message_id),
            "interval_us": interval_us,
        })
        ack, _, _ = self.wait_for_ack_and_message(
            self.dialect.MAV_CMD_SET_MESSAGE_INTERVAL, -999999,
            self.args.interval_ack_timeout,
        )
        result = int(ack.result) if ack is not None else None
        return {
            "message_id": message_id,
            "message_name": message_name_by_id(self.dialect, message_id),
            "interval_us": interval_us,
            "sent_host_monotonic_ns": sent_ns,
            "ack_received": ack is not None,
            "ack_result": result,
            "ack_result_name": enum_name(self.dialect, "MAV_RESULT", result)
            if result is not None else None,
        }

    def relevant_stream_sample(self) -> Dict[str, Any]:
        phase = self.begin_phase(
            "RELEVANT_STREAM_SAMPLE",
            "MAV_CMD_SET_MESSAGE_INTERVAL for selected AP-observation messages, then timed receive.",
            "This phase follows and is excluded from the passive baseline and request sweep.",
        )
        interval_results = [self.interval_request(mid, 200_000)
                            for mid in RELEVANT_STREAM_IDS]
        self.receive_for(self.args.post_seconds, send_heartbeat=True)
        self.end_phase(phase)
        result = {
            "requested_interval_us": 200_000,
            "sample_duration_seconds": self.args.post_seconds,
            "requests": interval_results,
        }
        write_json(self.run_dir / "interval_requests.json", result)
        return result

    def required_parameters(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        by_name = {p["name"]: p for p in snapshot["parameters"]}
        requested = list(dict.fromkeys(self.profile["required_parameters"] +
                                       BATTERY_PARAMETERS))
        records = []
        for name in requested:
            p = by_name.get(name)
            records.append({
                "name": name,
                "status": "RUNTIME_OBSERVED" if p is not None else "NOT_PRESENT",
                "record": p,
            })
        battery_instances = sorted(
            name for name in by_name
            if (name.startswith("BATT") and any(
                name.endswith(suffix) for suffix in (
                    "_LOW_TIMER", "_FS_VOLTSRC", "_LOW_VOLT", "_LOW_MAH",
                    "_CRT_VOLT", "_CRT_MAH", "_FS_LOW_ACT", "_FS_CRT_ACT",
                    "_MONITOR", "_CAPACITY"))))
        result = {
            "source": "PARAM_REQUEST_LIST runtime snapshot",
            "source_defaults_used": False,
            "required_and_exception_parameters": records,
            "all_detected_battery_instance_parameters": [by_name[n]
                                                         for n in battery_instances],
        }
        write_json(self.run_dir / "required_parameters.json", result)
        return result

    def process_tree(self) -> Dict[str, Any]:
        if self.process is None:
            return {"exit_code": None, "stdout": "", "stderr": ""}
        return run_text([
            "ps", "-o", "pid=,ppid=,pgid=,sid=,stat=,comm=,args=",
            "--sid", str(self.process.pid),
        ])

    def cleanup_process(self) -> Dict[str, Any]:
        cleanup: Dict[str, Any] = {
            "pid": self.process.pid if self.process else None,
            "process_group": None,
            "signals": [],
            "pre_cleanup_process_tree": self.process_tree(),
            "post_cleanup_process_tree": None,
            "return_code": None,
            "pid_exists_after_wait": None,
            "cleaned_only_owned_process_group": True,
        }
        if self.process is None:
            return cleanup
        try:
            pgid = os.getpgid(self.process.pid)
            cleanup["process_group"] = pgid
        except ProcessLookupError:
            pgid = None
        if self.process.poll() is None and pgid is not None:
            os.killpg(pgid, signal.SIGINT)
            cleanup["signals"].append({"signal": "SIGINT", "sent_at": utc_now()})
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGTERM)
                cleanup["signals"].append({"signal": "SIGTERM", "sent_at": utc_now()})
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(pgid, signal.SIGKILL)
                    cleanup["signals"].append({"signal": "SIGKILL", "sent_at": utc_now()})
                    self.process.wait(timeout=5)
        else:
            self.process.wait(timeout=1)
        cleanup["return_code"] = self.process.returncode
        try:
            os.kill(self.process.pid, 0)
            cleanup["pid_exists_after_wait"] = True
        except OSError as exc:
            cleanup["pid_exists_after_wait"] = exc.errno != errno.ESRCH
        cleanup["post_cleanup_process_tree"] = self.process_tree()
        cleanup["completed_at"] = utc_now()
        write_json(self.run_dir / "process_cleanup.json", cleanup)
        return cleanup

    def close_files(self) -> None:
        if self.recorder:
            self.recorder.close()
        if self.params:
            self.params.close()
        if self.conn is not None:
            for attr in ("logfile", "logfile_raw"):
                handle = getattr(self.conn, attr, None)
                if handle is not None:
                    try:
                        handle.close()
                    except Exception:
                        pass
            try:
                self.conn.close()
            except Exception:
                pass
        if self.outbound:
            self.outbound.close()
        if self.process_stdout:
            self.process_stdout.close()
        if self.process_stderr:
            self.process_stderr.close()

    def run(self) -> Dict[str, Any]:
        self.prepare()
        self.open_connection()
        snapshot: Dict[str, Any] = {
            "status": "FAILED", "expected_count": None,
            "unique_parameter_count": 0, "parameters": [],
        }
        sweep: Dict[str, Any] = {"status": "NOT_RUN", "attempted": 0}
        interval: Dict[str, Any] = {"requests": []}
        required: Dict[str, Any] = {}
        runtime_status = "FAILED"
        try:
            self.start_process()
            self.wait_for_target()
            self.baseline()
            snapshot = self.parameter_download()
            required = self.required_parameters(snapshot)
            sweep = self.request_sweep()
            interval = self.relevant_stream_sample()
            runtime_status = "COMPLETE" if snapshot["status"] == "COMPLETE" else "PARTIAL"
        except Exception as exc:
            self.failures.append(repr(exc))
            runtime_status = "PARTIAL" if self.recorder and self.recorder.total else "FAILED"
            print(f"[{self.profile['key']}] ERROR: {exc!r}", file=sys.stderr, flush=True)
        finally:
            # Capture summary before closing the JSONL, then terminate only this
            # direct child process group and close all evidence handles.
            message_summary = self.recorder.summary() if self.recorder else {
                "total_message_count": 0, "messages": []}
            write_json(self.run_dir / "message_summary.json", message_summary)
            write_json(self.run_dir / "phase_timeline.json", self.phases)
            self.cleanup = self.cleanup_process()
            self.close_files()

        result = {
            "capture_id": f"ardupilot-{self.profile['key'].lower()}-m6",
            "system": "ArduPilot",
            "vehicle": self.profile["vehicle"],
            "profile": self.profile["model"],
            "firmware_commit": EXPECTED_FIRMWARE_COMMIT,
            "mavlink_commit": EXPECTED_MAVLINK_COMMIT,
            "runtime_status": runtime_status,
            "implementation_satisfaction": "NOT_ASSESSED",
            "launch_command": shlex.join(self.launch_command()),
            "connection": f"udpin:127.0.0.1:{self.profile['udp_port']}",
            "vehicle_expected_sysid": self.profile["sysid"],
            "vehicle_observed_compid": self.target_component,
            "harness_sysid": HARNESS_SYSID,
            "harness_compid": HARNESS_COMPID,
            "phases": self.phases,
            "parameter_snapshot": {
                k: snapshot.get(k) for k in (
                    "status", "protocol", "expected_count", "received_response_count",
                    "unique_parameter_count", "missing_indices", "list_retries")
            },
            "required_parameters": required,
            "request_sweep": {
                k: sweep.get(k) for k in (
                    "status", "attempted", "message_observed", "unsupported",
                    "no_response", "ack_result_counts",
                    "accepted_without_observed_message")
            },
            "interval_sample": interval,
            "message_summary": {
                "total_message_count": message_summary.get("total_message_count", 0),
                "distinct_message_key_count": message_summary.get(
                    "distinct_message_key_count", 0),
                "baseline_distinct_message_key_count": message_summary.get(
                    "baseline_distinct_message_key_count", 0),
            },
            "process_cleanup": self.cleanup,
            "failures": self.failures,
            "limitations": [
                "Host arrival uses CLOCK_MONOTONIC_NS; it is not silently substituted for vehicle time.",
                "Only message fields classified as timestamps by the frozen static catalog are sampled as onboard time carriers.",
                "Request-window observation can be periodic/default traffic; baseline_present and observation_causality retain this ambiguity.",
                "No flight or property-conformance scenario was executed; this is runtime support and parameter evidence only.",
            ],
        }
        write_json(self.run_dir / "run_result.json", result)
        return result


def artifact_role(path: Path) -> str:
    name = path.name
    if name == "messages.tlog":
        return "timestamped MAVLink byte capture"
    if name == "messages.raw":
        return "raw MAVLink byte capture"
    if name == "messages.jsonl":
        return "decoded per-message host-monotonic trace"
    if name in {"parameters.json", "parameters.jsonl", "required_parameters.json"}:
        return "runtime parameter evidence"
    if name.startswith("request_sweep") or name == "interval_requests.json":
        return "message request/response evidence"
    if name in {"stdout.log", "stderr.log"}:
        return "SITL process output"
    if name == "process_cleanup.json":
        return "owned-process cleanup evidence"
    if name == "dialect_generated.py":
        return "generated parser for frozen all.xml dialect"
    if name == "collect_runtime.py":
        return "reproduction script"
    if "runtime" in path.parts:
        return "isolated SITL runtime state/log"
    return "capture metadata or supporting artifact"


def inventory_artifacts(exclude: Iterable[Path] = ()) -> List[Dict[str, Any]]:
    excluded = {p.resolve() for p in exclude}
    records = []
    for path in sorted(p for p in OUT_ROOT.rglob("*") if p.is_file()):
        if path.resolve() in excluded:
            continue
        records.append({
            "path": str(path.relative_to(WORKSPACE)),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "role": artifact_role(path),
        })
    return records


def property_parameter_records(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key = {p["key"]: p for p in PROFILES}
    output = []
    for result in results:
        key = result["vehicle"].replace("Ardu", "") if result["vehicle"] != "Rover" else "Rover"
        if key not in by_key:
            key = result["capture_id"].split("-")[1].capitalize()
        profile = by_key[key]
        params_path = RUNS_ROOT / key / "parameters.json"
        if not params_path.is_file():
            continue
        snapshot = json.loads(params_path.read_text(encoding="utf-8"))
        by_name = {p["name"]: p for p in snapshot.get("parameters", [])}
        source_sha = sha256_file(params_path)
        for property_id, actual_name, unit in profile["time_parameters"]:
            p = by_name.get(actual_name)
            output.append({
                "property_id": property_id,
                "catalog_parameter_id": (
                    "BATTx_LOW_TIMER" if actual_name == "BATT_LOW_TIMER" else actual_name),
                "runtime_parameter_name": actual_name,
                "capture_id": result["capture_id"],
                "status": "RUNTIME_OBSERVED" if p is not None else "UNRESOLVED",
                "value": p["decoded_value"] if p is not None else None,
                "wire_value": p["wire_value"] if p is not None else None,
                "unit": unit,
                "source_path": str(params_path.relative_to(WORKSPACE)),
                "source_sha256": source_sha,
                "source_param_index": p["param_index"] if p is not None else None,
                "source_param_count": p["param_count"] if p is not None else None,
                "source_system": p["source_system"] if p is not None else None,
                "source_component": p["source_component"] if p is not None else None,
                "received_host_monotonic_ns": (
                    p["received_host_monotonic_ns"] if p is not None else None),
                "source_default_substituted": False,
            })
    return output


def build_readme(results: List[Dict[str, Any]], preflight: Dict[str, Any],
                 postflight: Dict[str, Any]) -> None:
    lines = [
        "# ArduPilot Milestone 6 runtime capture",
        "",
        "This directory contains read-only runtime evidence from the frozen ArduPilot ",
        f"commit `{EXPECTED_FIRMWARE_COMMIT}` and MAVLink commit `{EXPECTED_MAVLINK_COMMIT}`.",
        "It does **not** contain a property-satisfaction or conformance conclusion.",
        "Source defaults were not substituted for runtime parameter values.",
        "",
        "## Capture phases",
        "",
        "Each vehicle was run in an isolated working directory, HOME, port set, and process group:",
        "",
        "1. `STARTUP`: passive receive until the expected HEARTBEAT, plus passive warmup.",
        f"2. `BASELINE`: at least {max(10.0, min(r['phases'][1]['duration_seconds'] for r in results if len(r['phases']) > 1)):.1f}s passive traffic with no request.",
        "3. `PARAMETER_DOWNLOAD`: `PARAM_REQUEST_LIST`, with bounded read-only repair requests for missing indices.",
        "4. `REQUEST_SWEEP`: one serialized `MAV_CMD_REQUEST_MESSAGE` (512) for each of the 352 frozen `all.xml` message IDs.",
        "5. `RELEVANT_STREAM_SAMPLE`: selected nonpersistent stream-interval requests followed by timed observation.",
        "",
        "Baseline counts are retained separately so a packet seen after a request is not automatically classified as request-caused.",
        "",
        "## Results",
        "",
        "| Vehicle | Status | Parameters | Baseline message kinds | Request sweep | Observed in window | Unsupported | No response | Cleanup |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        ps = r["parameter_snapshot"]
        rs = r["request_sweep"]
        cleanup = r["process_cleanup"]
        lines.append(
            f"| {r['vehicle']} | {r['runtime_status']} | "
            f"{ps.get('unique_parameter_count')}/{ps.get('expected_count')} | "
            f"{r['message_summary'].get('baseline_distinct_message_key_count')} | "
            f"{rs.get('attempted')} | {rs.get('message_observed')} | "
            f"{rs.get('unsupported')} | {rs.get('no_response')} | "
            f"PID gone={not cleanup.get('pid_exists_after_wait', True)} |"
        )
    lines.extend([
        "",
        "## Evidence layout",
        "",
        "For each vehicle under `runs/<Vehicle>/`:",
        "",
        "- `command.txt`, `launch.json`, `stdout.log`, `stderr.log`: exact launch and process output.",
        "- `messages.tlog`, `messages.raw`, `messages.jsonl`: timestamped bytes, raw bytes, and decoded host-monotonic records.",
        "- `message_summary.json`: names/IDs/fields/counts, first/last host monotonic arrival, source SYSID/COMPID, phase counts, and vehicle timestamp samples.",
        "- `parameters.jsonl`, `parameters.json`, `required_parameters.json`: complete wire observations and selected property/exception parameters.",
        "- `request_sweep.jsonl`, `request_sweep.json`: per-ID command ACK, window observation, latency, and baseline ambiguity.",
        "- `process_cleanup.json`: exact owned PID/process-group signals, return code, and post-wait absence.",
        "- `runtime/`: isolated EEPROM/DataFlash/SITL state produced by that run.",
        "",
        "`manifest.json` inventories every other file with SHA-256. The manifest cannot include its own hash without recursion; hash it externally when consuming it.",
        "",
        "## Preservation checks",
        "",
        f"- Firmware HEAD before: `{preflight['git']['firmware_head']}`",
        f"- Firmware HEAD after: `{postflight['git']['firmware_head']}`",
        f"- Firmware status before: `{preflight['git']['firmware_status_short']}`",
        f"- Firmware status after: `{postflight['git']['firmware_status_short']}`",
        f"- Matching SITL processes before: `{preflight['matching_processes']}`",
        f"- Matching SITL processes after: `{postflight['matching_processes']}`",
        "",
        "The only pre-existing firmware worktree status was ` m modules/CrashDebug`; it was not modified or cleaned.",
        "",
        "## Limits",
        "",
        "- Host monotonic arrival time and onboard timestamps remain separate clock domains.",
        "- `COMMAND_ACK` for command 512 has no request sequence; serialized pairing reduces but does not eliminate late-ACK ambiguity.",
        "- Unsupported, unobserved, and conditionally emitted messages are retained as results rather than treated as errors.",
        "- These are idle-SITL support observations, not flight-scenario property verdicts.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "cd /home/lqq/project/TAFuzz",
        "python3 benchmark/extraction_runs/milestone6/ArduPilot/collect_runtime.py",
        "```",
        "",
        "The collector refuses to overwrite existing `runs/<Vehicle>` directories.",
    ])
    (OUT_ROOT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vehicles", default="Copter,Plane,Rover",
                        help="comma-separated profile keys")
    parser.add_argument("--startup-timeout", type=float, default=45.0)
    parser.add_argument("--warmup-seconds", type=float, default=3.0)
    parser.add_argument("--baseline-seconds", type=float, default=12.0)
    parser.add_argument("--param-timeout", type=float, default=120.0)
    parser.add_argument("--sweep-timeout", type=float, default=0.45)
    parser.add_argument("--interval-ack-timeout", type=float, default=0.35)
    parser.add_argument("--post-seconds", type=float, default=12.0)
    args = parser.parse_args()
    if args.baseline_seconds < 10.0:
        parser.error("--baseline-seconds must be at least 10")
    return args


def main() -> int:
    args = parse_args()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    dialect_generation = generate_dialect_if_needed()
    preflight = {
        "captured_at": utc_now(),
        "git": git_state(),
        "matching_processes": matching_processes(),
        "collector_python": sys.executable,
        "collector_python_version": sys.version,
        "dialect_generation": dialect_generation,
    }
    write_json(OUT_ROOT / "preflight.json", preflight)
    if preflight["git"]["firmware_head"] != EXPECTED_FIRMWARE_COMMIT:
        raise RuntimeError("firmware HEAD does not match frozen commit")
    if preflight["git"]["mavlink_head"] != EXPECTED_MAVLINK_COMMIT:
        raise RuntimeError("MAVLink HEAD does not match frozen commit")

    dialect = load_generated_dialect()
    if len(dialect.mavlink_map) != 352:
        raise RuntimeError(f"generated dialect has {len(dialect.mavlink_map)} messages")
    message_specs = load_message_specs()
    if set(dialect.mavlink_map) != {int(x["message_id"]) for x in message_specs}:
        raise RuntimeError("generated dialect IDs do not match frozen message catalog")
    time_fields = load_time_field_specs()
    selected = [x.strip() for x in args.vehicles.split(",") if x.strip()]
    profiles = [p for p in PROFILES if p["key"] in selected]
    if {p["key"] for p in profiles} != set(selected):
        raise RuntimeError(f"unknown vehicle selection: {selected}")

    results = []
    for profile in profiles:
        result = VehicleCapture(profile, args, dialect, message_specs, time_fields).run()
        results.append(result)

    postflight = {
        "captured_at": utc_now(),
        "git": git_state(),
        "matching_processes": matching_processes(),
    }
    write_json(OUT_ROOT / "postflight.json", postflight)
    build_readme(results, preflight, postflight)
    property_parameters = property_parameter_records(results)
    manifest_path = OUT_ROOT / "manifest.json"
    artifacts = inventory_artifacts(exclude=[manifest_path])
    manifest = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "system": "ArduPilot",
        "firmware_commit": EXPECTED_FIRMWARE_COMMIT,
        "mavlink_commit": EXPECTED_MAVLINK_COMMIT,
        "implementation_satisfaction": "NOT_ASSESSED",
        "scope": "Runtime parameter and MAVLink support observation only; no property verdict.",
        "phase_contract": ["STARTUP", "BASELINE", "PARAMETER_DOWNLOAD",
                           "REQUEST_SWEEP", "RELEVANT_STREAM_SAMPLE"],
        "preflight": preflight,
        "postflight": postflight,
        "captures": results,
        "property_parameters": property_parameters,
        "artifact_inventory": artifacts,
        "manifest_self_hash_note": "manifest.json intentionally excludes itself from artifact_inventory",
    }
    write_json(manifest_path, manifest)
    print(f"manifest: {manifest_path}", flush=True)
    return 0 if all(r["runtime_status"] != "FAILED" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
