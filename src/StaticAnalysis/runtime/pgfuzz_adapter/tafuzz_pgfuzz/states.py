from __future__ import annotations

import math
from typing import Any, Iterable, Mapping


RESULT_GROUPS = [
    "roll", "pitch", "throttle", "yaw", "speed", "altitude", "position",
    "status", "gyro", "accel", "baro", "GPS", "parachute", "pre_arm",
    "mission",
]

# This is the original PGFuzz 34-to-15 grouping, including its duplicate use of
# reference yaw at raw indices 14 and 20.
LEGACY_GROUP_BY_INDEX = {
    0: "roll", 12: "roll", 15: "roll", 18: "roll",
    1: "pitch", 13: "pitch", 16: "pitch", 19: "pitch",
    2: "throttle", 7: "throttle",
    3: "yaw", 6: "yaw", 14: "yaw", 17: "yaw", 20: "yaw",
    4: "speed", 5: "speed", 22: "speed",
    8: "altitude", 11: "altitude", 21: "altitude", 32: "altitude", 33: "altitude",
    9: "position", 10: "position",
    23: "status", 24: "gyro", 25: "accel", 26: "baro", 27: "GPS",
    28: "parachute", 29: "pre_arm", 30: "mission", 31: "GPS",
}

FEATURE_GROUP = {
    "rc.chan1_raw": "roll", "rc.chan2_raw": "pitch",
    "rc.chan3_raw": "throttle", "rc.chan4_raw": "yaw",
    "vfr.airspeed": "speed", "vfr.groundspeed": "speed",
    "vfr.heading": "yaw", "vfr.throttle": "throttle",
    "vfr.alt": "altitude", "vfr.climb": "altitude",
    "att.roll": "roll", "att.pitch": "pitch", "att.yaw": "yaw",
    "att.rollspeed": "roll", "att.pitchspeed": "pitch", "att.yawspeed": "yaw",
    "nav.nav_roll": "roll", "nav.nav_pitch": "pitch", "nav.nav_bearing": "yaw",
    "nav.reference_alt": "altitude", "nav.reference_airspeed": "speed",
    "global.lat": "position", "global.lon": "position",
    "global.vertical_speed": "altitude", "gps.satellites_visible": "GPS",
    "gps.alt": "altitude", "heartbeat.system_status": "status",
    "heartbeat.custom_mode": "status", "heartbeat.armed": "status",
    "mission.count": "mission", "battery.voltage": "status",
    "event.gcs_failsafe_observed_latency": "status",
}

FEATURE_TOLERANCE = {
    "rc.chan1_raw": 1.0, "rc.chan2_raw": 1.0, "rc.chan3_raw": 1.0,
    "rc.chan4_raw": 1.0, "vfr.airspeed": 0.01, "vfr.groundspeed": 0.01,
    "vfr.heading": 1.0, "vfr.throttle": 1.0, "vfr.alt": 0.01,
    "vfr.climb": 0.01, "att.roll": 0.0001, "att.pitch": 0.0001,
    "att.yaw": 0.0001, "att.rollspeed": 0.0001, "att.pitchspeed": 0.0001,
    "att.yawspeed": 0.0001, "nav.nav_roll": 0.01, "nav.nav_pitch": 0.01,
    "nav.nav_bearing": 1.0, "nav.reference_alt": 0.01,
    "nav.reference_airspeed": 0.01, "global.lat": 1.0, "global.lon": 1.0,
    "global.vertical_speed": 0.01, "gps.satellites_visible": 1.0,
    "gps.alt": 0.001, "heartbeat.system_status": 1.0,
    "heartbeat.custom_mode": 1.0, "heartbeat.armed": 1.0,
    "mission.count": 1.0, "battery.voltage": 0.001,
    # GCS failsafe is checked in ArduCopter's three_hz_loop. The 0.5-second
    # tolerance covers its 1/3-second scheduling granularity plus message
    # observation, and remains far below the 5s-versus-2s smoke separation.
    "event.gcs_failsafe_observed_latency": 0.5,
}

ONBOARD_TIME_FIELDS = {
    "ATTITUDE": ["time_boot_ms"], "GLOBAL_POSITION_INT": ["time_boot_ms"],
    "GPS_RAW_INT": ["time_usec"], "SYSTEM_TIME": ["time_unix_usec", "time_boot_ms"],
    "BATTERY_STATUS": ["time_remaining"],
}


def json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.split(b"\0", 1)[0].decode("utf-8", errors="replace")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class StateWindow:
    def __init__(self, phase: str) -> None:
        self.phase = phase
        self.samples: dict[str, list[float]] = {}
        self.text_events: list[str] = []
        self.message_counts: dict[str, int] = {}
        self.onboard_time_samples: dict[str, list[float]] = {}
        self.last_vfr_alt = 0.0
        self.last_vfr_airspeed = 0.0
        self.status_flags = {
            "gyro": 1.0, "accel": 1.0, "baro": 1.0, "GPS": 1.0,
            "parachute": 0.0, "pre_arm": 0.0,
        }

    def add(self, key: str, value: Any) -> None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        if math.isfinite(number):
            self.samples.setdefault(key, []).append(number)

    def ingest(self, message: Any) -> dict[str, Any]:
        message_type = message.get_type()
        data = json_safe(message.to_dict())
        self.message_counts[message_type] = self.message_counts.get(message_type, 0) + 1
        if message_type == "RC_CHANNELS":
            for channel in range(1, 5):
                self.add(f"rc.chan{channel}_raw", data.get(f"chan{channel}_raw"))
        elif message_type == "VFR_HUD":
            for field in ["airspeed", "groundspeed", "heading", "throttle", "alt", "climb"]:
                self.add(f"vfr.{field}", data.get(field))
            self.last_vfr_alt = float(data.get("alt") or 0.0)
            self.last_vfr_airspeed = float(data.get("airspeed") or 0.0)
        elif message_type == "ATTITUDE":
            for field in ["roll", "pitch", "yaw", "rollspeed", "pitchspeed", "yawspeed"]:
                self.add(f"att.{field}", data.get(field))
        elif message_type == "NAV_CONTROLLER_OUTPUT":
            for field in ["nav_roll", "nav_pitch", "nav_bearing"]:
                self.add(f"nav.{field}", data.get(field))
            self.add("nav.reference_alt", self.last_vfr_alt + float(data.get("alt_error") or 0.0))
            self.add("nav.reference_airspeed", self.last_vfr_airspeed + float(data.get("aspd_error") or 0.0))
        elif message_type == "GLOBAL_POSITION_INT":
            self.add("global.lat", data.get("lat"))
            self.add("global.lon", data.get("lon"))
            self.add("global.vertical_speed", float(data.get("vz") or 0.0) / 100.0)
        elif message_type == "GPS_RAW_INT":
            self.add("gps.satellites_visible", data.get("satellites_visible"))
            self.add("gps.alt", float(data.get("alt") or 0.0) / 1000.0)
        elif message_type == "HEARTBEAT":
            self.add("heartbeat.system_status", data.get("system_status"))
            self.add("heartbeat.custom_mode", data.get("custom_mode"))
            base_mode = int(data.get("base_mode") or 0)
            self.add("heartbeat.armed", 1 if base_mode & 128 else 0)
        elif message_type == "MISSION_COUNT":
            self.add("mission.count", data.get("count"))
        elif message_type == "BATTERY_STATUS":
            voltages = data.get("voltages") or []
            valid = [float(value) / 1000.0 for value in voltages
                     if isinstance(value, (int, float)) and 0 < value < 65535]
            if valid:
                self.add("battery.voltage", valid[0])
        elif message_type == "SYS_STATUS":
            voltage = data.get("voltage_battery")
            if isinstance(voltage, (int, float)) and 0 < voltage < 65535:
                self.add("battery.voltage", float(voltage) / 1000.0)
        elif message_type == "STATUSTEXT":
            text = str(data.get("text") or "")
            self.text_events.append(text)
            if "Parachute: Released" in text:
                self.status_flags["parachute"] = 1.0
            elif "NavEKF" in text and "lane switch" in text:
                self.status_flags["GPS"] = 0.0
            elif "Vibration compensation ON" in text:
                self.status_flags["gyro"] = 0.0
            elif "EKF primary changed" in text:
                self.status_flags["accel"] = 0.0
            elif "PreArm: Waiting for Nav Checks" in text:
                self.status_flags["baro"] = 0.0
            elif "PreArm: Check" in text:
                self.status_flags["pre_arm"] = 1.0
        onboard = {field: data.get(field)
                   for field in ONBOARD_TIME_FIELDS.get(message_type, [])
                   if field in data}
        for field, value in onboard.items():
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                self.onboard_time_samples.setdefault(
                    f"{message_type}.{field}", []).append(float(value))
        return {"message_type": message_type, "fields": data,
                "onboard_time_fields": onboard}

    def legacy_vector(self) -> list[float]:
        std_keys = [
            "rc.chan1_raw", "rc.chan2_raw", "rc.chan3_raw", "rc.chan4_raw",
            "vfr.airspeed", "vfr.groundspeed", "vfr.heading", "vfr.throttle",
            "vfr.alt", "global.lat", "global.lon", "vfr.climb",
            "att.roll", "att.pitch", "nav.nav_bearing", "att.rollspeed",
            "att.pitchspeed", "att.yawspeed", "nav.nav_roll", "nav.nav_pitch",
            "nav.nav_bearing", "nav.reference_alt", "nav.reference_airspeed",
        ]
        vector = [population_std(self.samples.get(key, [])) for key in std_keys]
        vector.extend([
            last(self.samples.get("heartbeat.system_status", []), 0.0),
            self.status_flags["gyro"], self.status_flags["accel"],
            self.status_flags["baro"], self.status_flags["GPS"],
            self.status_flags["parachute"], self.status_flags["pre_arm"],
            last(self.samples.get("mission.count", []), 0.0),
            population_std(self.samples.get("gps.satellites_visible", [])),
            population_std(self.samples.get("gps.alt", [])),
            population_std(self.samples.get("global.vertical_speed", [])),
        ])
        if len(vector) != 34:
            raise AssertionError(f"legacy vector length is {len(vector)}, expected 34")
        return vector

    def summary(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "samples": self.samples,
            "message_counts": self.message_counts,
            "onboard_time_ranges": {
                field: {"count": len(values), "minimum": min(values),
                        "maximum": max(values)}
                for field, values in sorted(self.onboard_time_samples.items())
                if values
            },
            "text_events": self.text_events,
            "status_flags": self.status_flags,
            "legacy_vector": self.legacy_vector(),
        }


def last(values: Iterable[float], default: float) -> float:
    sequence = list(values)
    return sequence[-1] if sequence else default


def population_std(values: Iterable[float]) -> float:
    sequence = list(values)
    if not sequence:
        return 0.0
    mean = sum(sequence) / len(sequence)
    return math.sqrt(sum((value - mean) ** 2 for value in sequence) / len(sequence))


def registry_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "legacy_raw_state_count": 34,
        "legacy_result_groups": RESULT_GROUPS,
        "legacy_group_by_index": {str(key): value
                                  for key, value in LEGACY_GROUP_BY_INDEX.items()},
        "features": [
            {
                "feature": feature,
                "result_group": group,
                "absolute_tolerance": FEATURE_TOLERANCE.get(feature),
                "tolerance_source": "MAVLink field resolution or explicit state registry",
            }
            for feature, group in sorted(FEATURE_GROUP.items())
        ],
        "clock_semantics": {
            "host_clock": "CLOCK_MONOTONIC_NS",
            "host_clock_meaning": "harness ordering and observation-window boundaries only",
            "onboard_time_fields": ONBOARD_TIME_FIELDS,
            "boundary": "host receive time is not an internal firmware event timestamp",
        },
    }
