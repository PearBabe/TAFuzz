from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any

from .common import (ARDUPILOT_ROOT, append_jsonl, isolated_environment, utc_now,
                     write_json)
from .states import StateWindow, json_safe


class SITLSession:
    """Own one isolated ArduCopter SITL process and MAVLink connection."""

    INTEGER_PARAM_TYPES = {1, 2, 3, 4, 5, 6}

    def __init__(self, run_dir: Path, udp_port: int = 19401,
                 sysid: int = 151, speedup: int = 1,
                 source_system: int = 255) -> None:
        self.run_dir = run_dir
        self.udp_port = udp_port
        self.sysid = sysid
        self.speedup = speedup
        self.source_system = source_system
        self.runtime_dir = run_dir / "runtime"
        self.home_dir = run_dir / "home"
        self.logs_dir = run_dir / "logs"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.home_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.process: subprocess.Popen[str] | None = None
        self.stdout_handle: Any = None
        self.connection: Any = None
        self.dialect: Any = None
        self.target_component = 1
        self.outbound_records: list[dict[str, Any]] = []
        self.trace_path = self.logs_dir / "mavlink.jsonl"

    @property
    def binary(self) -> Path:
        return ARDUPILOT_ROOT / "build/sitl/bin/arducopter"

    def command(self) -> list[str]:
        offset = self.udp_port - 19401
        return [
            str(self.binary),
            "--wipe",
            "--model", "quad",
            "--home", "-35.363261,149.165230,584,353",
            "--speedup", str(self.speedup),
            "--base-port", str(20400 + offset * 10),
            "--rc-in-port", str(21401 + offset * 10),
            "--sim-port-in", str(22401 + offset * 10),
            "--sim-port-out", str(22402 + offset * 10),
            "--irlock-port", str(23401 + offset * 10),
            "--serial0", f"udpclient:127.0.0.1:{self.udp_port}",
            "--sysid", str(self.sysid),
            "--autotest-dir", str(ARDUPILOT_ROOT / "Tools/autotest"),
        ]

    def start(self, startup_timeout: float = 60.0) -> None:
        if not self.binary.is_file():
            raise FileNotFoundError(f"ArduCopter SITL binary not found: {self.binary}")
        from pymavlink import mavutil

        self.stdout_handle = (self.logs_dir / "arducopter.log").open(
            "w", encoding="utf-8")
        self.process = subprocess.Popen(
            self.command(), cwd=str(self.runtime_dir),
            env=isolated_environment(self.home_dir),
            stdout=self.stdout_handle, stderr=subprocess.STDOUT,
            text=True, start_new_session=True)
        self.connection = mavutil.mavlink_connection(
            f"udpin:127.0.0.1:{self.udp_port}", dialect="ardupilotmega",
            source_system=self.source_system, source_component=190)
        self.dialect = mavutil.mavlink
        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            self._ensure_alive("startup")
            message = self.connection.recv_match(type="HEARTBEAT", blocking=True,
                                                 timeout=0.5)
            if message is None or int(message.get_srcSystem()) != self.sysid:
                continue
            self.target_component = int(message.get_srcComponent())
            self.connection.target_system = self.sysid
            self.connection.target_component = self.target_component
            self.log_outbound("TARGET_HEARTBEAT", {
                "source_system": self.sysid,
                "source_component": self.target_component,
                "custom_mode": int(message.custom_mode),
            })
            return
        raise TimeoutError("ArduCopter target HEARTBEAT timeout")

    def _ensure_alive(self, phase: str) -> None:
        if self.process is None:
            raise RuntimeError("SITL process has not been started")
        code = self.process.poll()
        if code is not None:
            raise RuntimeError(f"SITL exited during {phase} with code {code}")

    def log_outbound(self, kind: str, fields: dict[str, Any]) -> None:
        self.outbound_records.append({
            "kind": kind,
            "host_monotonic_ns": time.monotonic_ns(),
            "host_wall_utc": utc_now(),
            "fields": fields,
        })

    def receive(self, timeout: float, phase: str) -> Any:
        self._ensure_alive(phase)
        message = self.connection.recv_match(blocking=True, timeout=timeout)
        if message is None:
            return None
        record = {
            "direction": "INBOUND", "phase": phase,
            "host_monotonic_ns": time.monotonic_ns(), "host_wall_utc": utc_now(),
            "source_system": int(message.get_srcSystem()),
            "source_component": int(message.get_srcComponent()),
            "message_type": message.get_type(), "fields": json_safe(message.to_dict()),
        }
        append_jsonl(self.trace_path, record)
        return message

    def send_gcs_heartbeat(self) -> None:
        mavlink = self.dialect
        self.connection.mav.heartbeat_send(
            mavlink.MAV_TYPE_GCS, mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, mavlink.MAV_STATE_ACTIVE)

    def request_state_streams(self, rate_hz: int = 10) -> None:
        for _ in range(3):
            self.connection.mav.request_data_stream_send(
                self.sysid, self.target_component,
                self.dialect.MAV_DATA_STREAM_ALL, rate_hz, 1)
        self.log_outbound("REQUEST_DATA_STREAM_ALL", {"rate_hz": rate_hz})

    def collect_window(self, seconds: float, phase: str,
                       send_heartbeat: bool = True,
                       periodic_action: Any = None) -> dict[str, Any]:
        window = StateWindow(phase)
        start_ns = time.monotonic_ns()
        deadline = time.monotonic() + seconds
        last_heartbeat = 0.0
        last_action = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if send_heartbeat and now - last_heartbeat >= 0.8:
                self.send_gcs_heartbeat()
                last_heartbeat = now
            if periodic_action is not None and now - last_action >= 0.2:
                periodic_action()
                last_action = now
            message = self.receive(min(0.05, max(0.0, deadline - now)), phase)
            if message is None or int(message.get_srcSystem()) != self.sysid:
                continue
            window.ingest(message)
        summary = window.summary()
        summary.update({
            "start_host_monotonic_ns": start_ns,
            "end_host_monotonic_ns": time.monotonic_ns(),
            "requested_duration_seconds": seconds,
            "host_clock": "CLOCK_MONOTONIC_NS",
        })
        return summary

    def set_parameter(self, name: str, value: float, param_type_name: str,
                      timeout: float = 5.0) -> dict[str, Any]:
        param_type = int(getattr(
            self.dialect, param_type_name, self.dialect.MAV_PARAM_TYPE_REAL32))
        self.connection.mav.param_set_send(
            self.sysid, self.target_component, name.encode("ascii"),
            float(value), param_type)
        sent_ns = time.monotonic_ns()
        self.log_outbound("PARAM_SET", {
            "name": name, "value": value, "param_type_name": param_type_name,
        })
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.send_gcs_heartbeat()
            message = self.receive(0.1, "PARAM_SET_READBACK")
            if message is None or message.get_type() != "PARAM_VALUE" or \
                    int(message.get_srcSystem()) != self.sysid:
                continue
            if self.parameter_name(message.param_id) != name:
                continue
            actual = float(message.param_value)
            tolerance = max(1e-5, abs(float(value)) * 1e-5)
            return {
                "verified": abs(actual - float(value)) <= tolerance,
                "requested_value": value, "readback_value": actual,
                "sent_host_monotonic_ns": sent_ns,
                "readback_host_monotonic_ns": time.monotonic_ns(),
            }
        return {"verified": False, "requested_value": value,
                "reason": "PARAM_VALUE readback timeout",
                "sent_host_monotonic_ns": sent_ns}

    def send_rc_override(self, channel: int, pwm: int) -> None:
        if not 1 <= channel <= 8:
            raise ValueError(f"only RC channels 1..8 are supported by this dialect: {channel}")
        values = [65535] * 8
        values[channel - 1] = int(pwm)
        self.connection.mav.rc_channels_override_send(
            self.sysid, self.target_component, *values)
        self.log_outbound("RC_CHANNELS_OVERRIDE", {"channel": channel, "pwm": pwm})

    def release_rc_overrides(self) -> None:
        self.connection.mav.rc_channels_override_send(
            self.sysid, self.target_component, *([0] * 8))
        self.log_outbound("RC_CHANNELS_OVERRIDE_RELEASE", {})

    def current_heartbeat(self, timeout: float = 3.0,
                          send_heartbeat: bool = True) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if send_heartbeat:
                self.send_gcs_heartbeat()
            message = self.receive(0.2, "HEARTBEAT_CONFIRM")
            if message is None or message.get_type() != "HEARTBEAT" or \
                    int(message.get_srcSystem()) != self.sysid:
                continue
            return {
                "custom_mode": int(message.custom_mode),
                "base_mode": int(message.base_mode),
                "system_status": int(message.system_status),
                "armed": bool(int(message.base_mode) &
                              self.dialect.MAV_MODE_FLAG_SAFETY_ARMED),
                "host_monotonic_ns": time.monotonic_ns(),
            }
        return None

    def set_mode(self, custom_mode: int, timeout: float = 5.0) -> dict[str, Any]:
        self.connection.mav.set_mode_send(
            self.sysid, self.dialect.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            int(custom_mode))
        sent_ns = time.monotonic_ns()
        self.log_outbound("SET_MODE", {"custom_mode": custom_mode})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            heartbeat = self.current_heartbeat(timeout=min(0.8, deadline - time.monotonic()))
            if heartbeat and heartbeat["custom_mode"] == int(custom_mode):
                return {"verified": True, "sent_host_monotonic_ns": sent_ns,
                        "heartbeat": heartbeat}
        return {"verified": False, "sent_host_monotonic_ns": sent_ns,
                "reason": "HEARTBEAT custom_mode confirmation timeout"}

    def command_long(self, command: int, params: list[float],
                     timeout: float = 5.0) -> dict[str, Any]:
        values = list(params[:7]) + [0.0] * max(0, 7 - len(params))
        self.connection.mav.command_long_send(
            self.sysid, self.target_component, int(command), 0, *values)
        sent_ns = time.monotonic_ns()
        self.log_outbound("COMMAND_LONG", {"command": command, "params": values})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.send_gcs_heartbeat()
            message = self.receive(0.1, "COMMAND_ACK_WAIT")
            if message is None or message.get_type() != "COMMAND_ACK" or \
                    int(message.get_srcSystem()) != self.sysid or \
                    int(message.command) != int(command):
                continue
            result = int(message.result)
            return {
                "verified": result in {
                    self.dialect.MAV_RESULT_ACCEPTED,
                    self.dialect.MAV_RESULT_IN_PROGRESS,
                },
                "command": command, "result": result,
                "result_name": self.dialect.enums["MAV_RESULT"].get(result).name,
                "sent_host_monotonic_ns": sent_ns,
                "ack_host_monotonic_ns": time.monotonic_ns(),
            }
        return {"verified": False, "command": command,
                "reason": "COMMAND_ACK timeout", "sent_host_monotonic_ns": sent_ns}

    @staticmethod
    def parameter_name(value: Any) -> str:
        if isinstance(value, bytes):
            return value.split(b"\0", 1)[0].decode("ascii", errors="replace")
        return str(value).split("\0", 1)[0]

    def download_parameters(self, timeout: float = 120.0) -> dict[str, Any]:
        self.send_gcs_heartbeat()
        self.connection.mav.param_request_list_send(self.sysid,
                                                    self.target_component)
        self.log_outbound("PARAM_REQUEST_LIST", {})
        records_by_index: dict[int, dict[str, Any]] = {}
        records_by_name: dict[str, dict[str, Any]] = {}
        expected_count: int | None = None
        deadline = time.monotonic() + timeout
        last_progress = time.monotonic()
        retry_count = 0
        last_heartbeat = 0.0

        while time.monotonic() < deadline:
            self._ensure_alive("parameter download")
            now = time.monotonic()
            if now - last_heartbeat >= 1.0:
                self.send_gcs_heartbeat()
                last_heartbeat = now
            message = self.connection.recv_match(blocking=True, timeout=0.1)
            if message is not None and message.get_type() == "PARAM_VALUE" and \
                    int(message.get_srcSystem()) == self.sysid:
                index = int(message.param_index)
                count = int(message.param_count)
                wire_value = float(message.param_value)
                param_type = int(message.param_type)
                name = self.parameter_name(message.param_id)
                record = {
                    "name": name,
                    "wire_value": wire_value,
                    "decoded_value": (int(round(wire_value))
                                      if param_type in self.INTEGER_PARAM_TYPES
                                      else wire_value),
                    "param_type": param_type,
                    "param_type_name": self.dialect.enums[
                        "MAV_PARAM_TYPE"].get(param_type).name,
                    "param_index": index,
                    "param_count": count,
                    "source_system": int(message.get_srcSystem()),
                    "source_component": int(message.get_srcComponent()),
                    "received_host_monotonic_ns": time.monotonic_ns(),
                    "received_host_wall_utc": utc_now(),
                }
                if index >= 0 and index not in records_by_index:
                    records_by_index[index] = record
                    records_by_name[name] = record
                    last_progress = now
                if count > 0:
                    expected_count = max(expected_count or 0, count)
                if expected_count and len(records_by_index) >= expected_count:
                    break
            if now - last_progress > 8.0 and retry_count < 2:
                self.connection.mav.param_request_list_send(
                    self.sysid, self.target_component)
                retry_count += 1
                last_progress = now

        missing = (sorted(set(range(expected_count)) - set(records_by_index))
                   if expected_count else [])
        if missing and len(missing) <= 200:
            for index in missing:
                self.connection.mav.param_request_read_send(
                    self.sysid, self.target_component, b"", index)
                repair_deadline = time.monotonic() + 0.1
                while time.monotonic() < repair_deadline:
                    message = self.connection.recv_match(type="PARAM_VALUE",
                                                         blocking=True,
                                                         timeout=0.02)
                    if message is None or int(message.get_srcSystem()) != self.sysid:
                        continue
                    record_index = int(message.param_index)
                    if record_index in records_by_index:
                        continue
                    param_type = int(message.param_type)
                    wire_value = float(message.param_value)
                    name = self.parameter_name(message.param_id)
                    record = {
                        "name": name,
                        "wire_value": wire_value,
                        "decoded_value": (int(round(wire_value))
                                          if param_type in self.INTEGER_PARAM_TYPES
                                          else wire_value),
                        "param_type": param_type,
                        "param_type_name": self.dialect.enums[
                            "MAV_PARAM_TYPE"].get(param_type).name,
                        "param_index": record_index,
                        "param_count": int(message.param_count),
                        "source_system": int(message.get_srcSystem()),
                        "source_component": int(message.get_srcComponent()),
                        "received_host_monotonic_ns": time.monotonic_ns(),
                        "received_host_wall_utc": utc_now(),
                    }
                    records_by_index[record_index] = record
                    records_by_name[name] = record

        final_missing = (sorted(set(range(expected_count)) - set(records_by_index))
                         if expected_count else [])
        status = ("COMPLETE" if expected_count and
                  len(records_by_index) == expected_count and not final_missing
                  else "PARTIAL" if records_by_index else "FAILED")
        snapshot = {
            "schema_version": "1.0",
            "status": status,
            "protocol": "PARAM_REQUEST_LIST/PARAM_VALUE",
            "expected_count": expected_count,
            "unique_parameter_count": len(records_by_index),
            "unique_parameter_name_count": len(records_by_name),
            "missing_indices": final_missing,
            "list_retries": retry_count,
            "parameters": [records_by_index[index]
                           for index in sorted(records_by_index)],
        }
        write_json(self.run_dir / "parameters_runtime.json", snapshot)
        if status != "COMPLETE":
            raise RuntimeError(
                f"incomplete parameter download: {len(records_by_index)}/"
                f"{expected_count}, missing={len(final_missing)}")
        return snapshot

    def mode_mapping(self) -> dict[str, int]:
        mapping = self.connection.mode_mapping() or {}
        return {str(name): int(number) for name, number in mapping.items()}

    def stop(self) -> None:
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        if self.process is not None:
            write_json(self.run_dir / "sitl_process.json", {
                "command": self.command(),
                "return_code": self.process.returncode,
                "outbound_records": self.outbound_records,
            })
        if self.stdout_handle is not None:
            self.stdout_handle.close()
            self.stdout_handle = None

    def __enter__(self) -> "SITLSession":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.stop()
