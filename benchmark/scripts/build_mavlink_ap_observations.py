#!/usr/bin/env python3
"""Create a static, source-backed MAVLink observation audit for selected APs.

This does not claim that any message was observed at runtime.  It validates
every referenced message/field against the frozen dialect catalogs and keeps
host arrival time distinct from embedded timestamps and vehicle clocks.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
OUT = BENCHMARK / "extraction_runs" / "milestone5" / "mavlink_ap_observation_audit.json"


def load_catalogs():
    rows = list(csv.DictReader((BENCHMARK / "mavlink_catalog" / "messages_and_fields.csv").open(encoding="utf-8")))
    # Milestone 6 deliberately split pure static support from the per-profile
    # runtime overlay.  AP observation identities must use the former; the
    # overlay has a different row schema and must never be treated as static
    # source evidence.
    support_rows = list(csv.DictReader((BENCHMARK / "mavlink_catalog" / "static_support_matrix.csv").open(encoding="utf-8")))
    fields: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["system"], row["message_name"])
        entry = fields.setdefault(key, {"id": int(row["message_id"]), "fields": set(), "origin": row["message_origin_xml"]})
        entry["fields"].add(row["field_name"])
    support = {}
    for row in support_rows:
        if row["entity_kind"] == "message":
            support[(row["system"], row["entity_name"])] = row
    return fields, support


FIELDS, SUPPORT = load_catalogs()


def observation(system: str, message: str, field: str | None, direction: str, derivation: str, time_field: str | None) -> dict[str, Any]:
    key = (system, message)
    if key not in FIELDS:
        raise KeyError(f"{system}: message {message} absent from frozen dialect")
    if field is not None and field not in FIELDS[key]["fields"]:
        raise KeyError(f"{system}: field {message}.{field} absent from frozen dialect")
    support_row = SUPPORT.get(key)
    static = bool(support_row and support_row["static_source_reference_status"] == "STATIC_REFERENCE_FOUND")
    support_status = "STATIC_SUPPORTED" if static else "DIALECT_ONLY"
    evidence = f"{FIELDS[key]['origin']}; static_support_matrix={support_row['static_source_reference_status'] if support_row else 'NO_ROW'}; static_catalog_runtime_column={support_row['default_runtime_observation_status'] if support_row else 'NOT_RUN_NO_CAPTURE'}"
    return {
        "message": message,
        "message_id": FIELDS[key]["id"],
        "field": field,
        "direction": direction,
        "derivation": derivation,
        "time_field": time_field,
        "support": support_status,
        "evidence": evidence,
    }


def param(system: str, parameter_names: str, derivation: str) -> dict[str, Any]:
    return observation(system, "PARAM_VALUE", "param_value", "OUTGOING", f"PARAM_VALUE.param_id selects {parameter_names}; {derivation}", None)


def heartbeat_mode(system: str, derivation: str) -> dict[str, Any]:
    return observation(system, "HEARTBEAT", "custom_mode", "OUTGOING", derivation + " HEARTBEAT has no embedded timestamp.", None)


def event_px4(derivation: str) -> dict[str, Any]:
    return observation("PX4", "EVENT", "id", "OUTGOING", derivation + " Requires firmware-matched component metadata to decode id/arguments.", "event_time_boot_ms (PX4 system boot clock)")


def make_rules() -> dict[str, dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {}

    def add(ap_id: str, classification: str, rationale: str, *observations: dict[str, Any]):
        rules[ap_id] = {"observability": classification, "rationale": rationale, "observations": list(observations)}

    # ArduPilot Copter GCS.
    hb_in_ard = observation("ArduPilot", "HEARTBEAT", None, "INCOMING", "Harness controls the normative designated-GCS heartbeat input, but HEARTBEAT has no embedded receipt timestamp. The current shared last-seen state is also refreshed by accepted MANUAL_CONTROL/RC_CHANNELS_OVERRIDE; those paths are an implementation conflict, not alternative normative heartbeat events.", None)
    add("ARD-COPTER-GCS-001-AP-01", "INSTRUMENTATION_REQUIRED", "The normative AP is the designated-GCS heartbeat-gap start. Exact vehicle-receipt timing requires instrumentation at GCS_MAVLINK::handle_heartbeat; the shared aggregate last-seen clock is not heartbeat-exclusive.", hb_in_ard)
    add("ARD-COPTER-GCS-001-AP-02", "CONDITIONAL", "Heartbeat history is derivable only from a complete controlled designated-GCS input trace or heartbeat-handler instrumentation; the aggregate current-source seen state is not heartbeat-exclusive.", hb_in_ard)
    add("ARD-COPTER-GCS-001-AP-03", "DERIVED", "Requires archived parameters plus current mode; no single MAVLink bit represents applicability.", param("ArduPilot", "FS_GCS_ENABLE, FS_OPTIONS, MAV_GCS_SYSID(_HI)", "combine with target HEARTBEAT mode/armed state"), heartbeat_mode("ArduPilot", "Decode current vehicle mode and system identity."))
    add("ARD-COPTER-GCS-001-AP-04", "INSTRUMENTATION_REQUIRED", "STATUSTEXT/system_status are lossy consequences and cannot identify the exact GCS-specific internal flag.", observation("ArduPilot", "STATUSTEXT", "text", "OUTGOING", "May contain a GCS failsafe notice; queueing/loss and no timestamp prevent exact event timing.", None), observation("ArduPilot", "HEARTBEAT", "system_status", "OUTGOING", "MAV_STATE_CRITICAL is not GCS-cause-specific and has no embedded timestamp.", None))

    # ArduPilot Guided.
    guided_inputs = [
        observation("ArduPilot", "SET_ATTITUDE_TARGET", "type_mask", "INCOMING", "Attitude/rate Guided input; time_boot_ms belongs to the sender and is not the vehicle receipt clock.", "time_boot_ms (sender boot clock)"),
        observation("ArduPilot", "SET_POSITION_TARGET_LOCAL_NED", "type_mask", "INCOMING", "Local position/velocity/acceleration input; acceptance depends on mask/frame/mode.", "time_boot_ms (sender boot clock)"),
        observation("ArduPilot", "SET_POSITION_TARGET_GLOBAL_INT", "type_mask", "INCOMING", "Global position/velocity/acceleration input; acceptance depends on mask/frame/mode.", "time_boot_ms (sender boot clock)"),
    ]
    add("ARD-COPTER-GUID-002-AP-01", "INSTRUMENTATION_REQUIRED", "Transmitted commands are direct inputs, but the timeout starts at accepted vehicle receipt.", *guided_inputs)
    add("ARD-COPTER-GUID-002-AP-02", "CONDITIONAL", "The command family/type_mask gives a candidate variant; exact active internal variant needs current mode/submode binding.", *guided_inputs)
    add("ARD-COPTER-GUID-002-AP-03", "INSTRUMENTATION_REQUIRED", "Target streams can show commanded response but not the exact timeout-response-start flag.", observation("ArduPilot", "ATTITUDE_TARGET", "type_mask", "OUTGOING", "Reports current commanded attitude/rates with vehicle boot timestamp; does not identify why targets changed.", "time_boot_ms (vehicle boot clock)"), observation("ArduPilot", "POSITION_TARGET_LOCAL_NED", "type_mask", "OUTGOING", "Reports current position/velocity/acceleration target when streamed; does not expose timeout flag.", "time_boot_ms (vehicle boot clock)"))

    # ArduPilot RTL.
    for suffix, rationale in (("01", "HEARTBEAT only identifies RTL, not LOITER_AT_HOME entry."), ("02", "Eligibility depends on internal RTL substate/path and cancellation history."), ("03", "Final-descent substate has no exact standard MAVLink field.")):
        add(f"ARD-COPTER-RTL-003-AP-{suffix}", "INSTRUMENTATION_REQUIRED", rationale, heartbeat_mode("ArduPilot", "Confirms coarse RTL mode only."))

    # ArduPilot Plane takeoff.
    add("ARD-PLANE-TAKEOFF-001-AP-01", "INSTRUMENTATION_REQUIRED", "No standard message carries the internal automatic-takeoff start epoch.", heartbeat_mode("ArduPilot", "Can confirm coarse TAKEOFF/AUTO mode, without the start epoch."))
    add("ARD-PLANE-TAKEOFF-001-AP-02", "DIRECT", "Runtime parameter is directly readable through the parameter protocol during setup, not an event stream.", param("ArduPilot", "TKOFF_TIMEOUT", "truth is param_value > 0; PARAM_VALUE has no timestamp"))
    add("ARD-PLANE-TAKEOFF-001-AP-03", "CONDITIONAL", "GPS_RAW_INT.vel is the closest raw-GPS speed observation; freshness/fix validity and cm/s scaling are required.", observation("ArduPilot", "GPS_RAW_INT", "vel", "OUTGOING", "Ground speed in cm/s; predicate is vel < 400 with valid fresh fix. time_usec may be UNIX epoch or system boot per XML.", "time_usec (ambiguous UNIX epoch or system boot; GPS fix time)"))
    add("ARD-PLANE-TAKEOFF-001-AP-04", "INSTRUMENTATION_REQUIRED", "STATUSTEXT can mention timeout but cannot uniquely timestamp/correlate the internal abort event.", observation("ArduPilot", "STATUSTEXT", "text", "OUTGOING", "May contain Takeoff timeout text; no timestamp and delivery may be delayed/lost.", None))
    add("ARD-PLANE-TAKEOFF-001-AP-05", "DIRECT", "Disarmed state is directly visible, but the message has no embedded event timestamp or disarm reason.", observation("ArduPilot", "HEARTBEAT", "base_mode", "OUTGOING", "MAV_MODE_FLAG_SAFETY_ARMED clear means disarmed for the target autopilot.", None))

    # ArduPilot Rover RC failsafe.
    rc_channels = observation("ArduPilot", "RC_CHANNELS", "chan3_raw", "OUTGOING", "Use chanN_raw where N=runtime(RCMAP_THROTTLE), not hard-coded channel 3; time_boot_ms is vehicle boot time.", "time_boot_ms (vehicle boot clock)")
    add("ARD-ROVER-RCFS-001-AP-01", "CONDITIONAL", "Direct PWM observation after runtime channel mapping; exact threshold crossing is derived from sampled output.", rc_channels, param("ArduPilot", "RCMAP_THROTTLE, FS_THR_VALUE", "select chanN_raw and threshold"))
    add("ARD-ROVER-RCFS-001-AP-02", "CONDITIONAL", "RC_CHANNELS freshness shows reported frames but exact receiver acceptance path may need instrumentation.", rc_channels)
    add("ARD-ROVER-RCFS-001-AP-03", "DERIVED", "Derive from runtime FS_THR_ENABLE and current mode.", param("ArduPilot", "FS_THR_ENABLE", "combine with mode exceptions"), heartbeat_mode("ArduPilot", "Current mode only."))
    add("ARD-ROVER-RCFS-001-AP-04", "CONDITIONAL", "Resulting mode/disarm can be observed after resolving FS_ACTION; exact failsafe.triggered cause needs instrumentation.", param("ArduPilot", "FS_ACTION", "maps expected action"), heartbeat_mode("ArduPilot", "Observe resulting mode."), observation("ArduPilot", "STATUSTEXT", "text", "OUTGOING", "May announce failsafe but has no timestamp/cause-complete guarantee.", None))

    # ArduPilot Rover crash.
    add("ARD-ROVER-CRASH-002-AP-01", "INSTRUMENTATION_REQUIRED", "The conjunction spans VFR_HUD without timestamp and ATTITUDE with boot timestamp; strict same-sample truth requires one vehicle-side probe.", observation("ArduPilot", "VFR_HUD", "groundspeed", "OUTGOING", "Groundspeed and throttle fields approximate two conjuncts; VFR_HUD has no timestamp.", None), observation("ArduPilot", "VFR_HUD", "throttle", "OUTGOING", "Demanded throttle for Rover; VFR_HUD has no timestamp.", None), observation("ArduPilot", "ATTITUDE", "yawspeed", "OUTGOING", "Yaw rate with vehicle boot timestamp; cannot be strictly aligned to VFR_HUD from embedded fields.", "time_boot_ms (vehicle boot clock)"), heartbeat_mode("ArduPilot", "Mode/armed are coarse state inputs."))
    add("ARD-ROVER-CRASH-002-AP-02", "DERIVED", "Derive from archived crash parameters and isolation setting.", param("ArduPilot", "FS_CRASH_CHECK, CRASH_ANGLE, CRASH_THR_MIN, CRASH_VEL_MIN, CRASH_TRAT_MIN", "configuration snapshot"))
    add("ARD-ROVER-CRASH-002-AP-03", "CONDITIONAL", "Hold/disarm outcome is visible; exact crash-cause correlation remains internal.", heartbeat_mode("ArduPilot", "Observe Hold custom_mode and armed bit."), observation("ArduPilot", "STATUSTEXT", "text", "OUTGOING", "May contain Crash: Going to HOLD; no timestamp.", None))

    # ArduPilot battery.
    add("ARD-SHARED-BATT-001-AP-01", "INSTRUMENTATION_REQUIRED", "BATTERY_STATUS can report raw cell/pack voltage, but not the sag-corrected resting estimate and has no event timestamp.", observation("ArduPilot", "BATTERY_STATUS", "voltages", "OUTGOING", "Per-instance voltage array; select by id and interpret invalid sentinel. No embedded timestamp.", None), observation("ArduPilot", "SYS_STATUS", "voltage_battery", "OUTGOING", "Aggregate voltage only; not per-instance and no timestamp.", None), param("ArduPilot", "BATTx_FS_VOLTSRC, BATTx_LOW_VOLT", "select voltage source and threshold"))
    add("ARD-SHARED-BATT-001-AP-02", "DIRECT", "Threshold enablement is directly derivable from the captured parameter value.", param("ArduPilot", "BATTx_LOW_VOLT", "enabled iff >0; correlate instance by param_id"))
    add("ARD-SHARED-BATT-001-AP-03", "INSTRUMENTATION_REQUIRED", "Standard telemetry lacks the exact AP_BattMonitor instance/severity transition with a unified timestamp.", observation("ArduPilot", "BATTERY_STATUS", "charge_state", "OUTGOING", "May expose a battery charge state per id, but does not prove the exact internal low-voltage path.", None), observation("ArduPilot", "STATUSTEXT", "text", "OUTGOING", "May report battery failsafe; no timestamp and lossy correlation.", None))

    # PX4 manual-control loss.
    manual = observation("PX4", "MANUAL_CONTROL", None, "INCOMING", "Directly controls a MAVLink manual input, but the message has no timestamp and does not prove selector acceptance/selection.", None)
    add("PX4-MC-RCLOSS-001-AP-01", "INSTRUMENTATION_REQUIRED", "Exact gap starts at the selected ManualControlSetpoint timestamp, not at host send/arrival time.", manual)
    add("PX4-MC-RCLOSS-001-AP-02", "DERIVED", "Combine archived parameters and current mode; some selector/arming history remains internal.", param("PX4", "COM_RCL_EXCEPT, COM_RC_IN_MODE, NAV_RCL_ACT", "derive configured applicability"), heartbeat_mode("PX4", "Current custom mode."))
    add("PX4-MC-RCLOSS-001-AP-03", "INSTRUMENTATION_REQUIRED", "EVENT can identify the classification only with matching component metadata; internal failsafe flag is authoritative.", event_px4("May carry manual-control-lost event with vehicle event timestamp."))

    # PX4 GCS link loss.
    hb_in_px4 = observation("PX4", "HEARTBEAT", "type", "INCOMING", "Harness can exercise the current PX4 MAV_TYPE_GCS-heartbeat realization, but the official v1.17 source does not equate that flow with the normative telemetry/data-connection liveness event. HEARTBEAT has no embedded receipt timestamp.", None)
    add("PX4-MC-GCSLOSS-002-AP-01", "UNRESOLVED", "The official data-link-loss predicate, correlation key, event carrier, and clock are unresolved. PX4 heartbeat/HRT locations remain MODELLED implementation candidates and cannot define this normative AP.", hb_in_px4)
    add("PX4-MC-GCSLOSS-002-AP-02", "DERIVED", "Combine data-link action/exception parameters with current mode.", param("PX4", "NAV_DLL_ACT, COM_DLL_EXCEPT", "derive configured applicability"), heartbeat_mode("PX4", "Current mode."))
    add("PX4-MC-GCSLOSS-002-AP-03", "INSTRUMENTATION_REQUIRED", "Standard HEARTBEAT does not expose gcs_connection_lost; Events are metadata-dependent.", event_px4("May carry GCS/data-link lost event."))

    # PX4 Offboard.
    proof = [
        observation("PX4", "SET_POSITION_TARGET_LOCAL_NED", "type_mask", "INCOMING", "Potential proof/setpoint; time_boot_ms is sender boot time and does not prove PX4 acceptance.", "time_boot_ms (sender boot clock)"),
        observation("PX4", "SET_ATTITUDE_TARGET", "type_mask", "INCOMING", "Potential attitude/rate proof; acceptance depends on supported fields and estimates.", "time_boot_ms (sender boot clock)"),
    ]
    add("PX4-MC-OFFBOARD-003-AP-01", "CONDITIONAL", "Messages are direct inputs, while accepted offboard_control_mode publication requires source validation.", *proof)
    add("PX4-MC-OFFBOARD-003-AP-02", "UNRESOLVED", "No standard field proves the one-second rate qualification, and the normative 2Hz equality boundary is unresolved.", *proof)
    add("PX4-MC-OFFBOARD-003-AP-03", "DIRECT", "Offboard current mode is directly encoded; HEARTBEAT/CURRENT_MODE timestamps are absent.", heartbeat_mode("PX4", "Decode PX4 custom OFFBOARD mode."), observation("PX4", "CURRENT_MODE", "custom_mode", "OUTGOING", "Direct current custom mode with no timestamp.", None))
    add("PX4-MC-OFFBOARD-003-AP-04", "CONDITIONAL", "Resulting mode is visible after resolving COM_OBL_RC_ACT and RC availability; exact cause remains internal.", param("PX4", "COM_OBL_RC_ACT, COM_OF_LOSS_T", "expected action and timeout"), heartbeat_mode("PX4", "Observe resulting mode."), event_px4("May identify Offboard-control-loss cause/action."))

    # PX4 landed auto-disarm.
    landed = observation("PX4", "EXTENDED_SYS_STATE", "landed_state", "OUTGOING", "MAV_LANDED_STATE_ON_GROUND directly reports state; message has no timestamp, so the transition epoch needs EVENT/internal HRT for strict timing.", None)
    armed = observation("PX4", "HEARTBEAT", "base_mode", "OUTGOING", "MAV_MODE_FLAG_SAFETY_ARMED reports state; no timestamp or disarm reason.", None)
    add("PX4-MC-AUTODISARM-004-AP-01", "CONDITIONAL", "Landed state is direct; exact transition timestamp is not.", landed)
    add("PX4-MC-AUTODISARM-004-AP-02", "UNRESOLVED", "Official exception/disable context is incomplete; parameters/mode alone cannot close eligibility.", param("PX4", "COM_DISARM_LAND", "capture value and disable-domain conflict"), heartbeat_mode("PX4", "Current mode only."))
    add("PX4-MC-AUTODISARM-004-AP-03", "DIRECT", "Armed state is directly visible, without event timestamp.", armed)
    add("PX4-MC-AUTODISARM-004-AP-04", "DIRECT", "Disarmed state is the clear armed bit; automatic reason needs event/internal evidence.", armed, event_px4("May carry automatic-disarm reason and event timestamp."))

    # PX4 flight time.
    add("PX4-MC-FLIGHTTIME-005-AP-01", "CONDITIONAL", "A landed->airborne transition is derivable but EXTENDED_SYS_STATE has no timestamp; exact takeoff_time is internal/Event.", landed, event_px4("May carry takeoff-detected event with vehicle boot timestamp."))
    add("PX4-MC-FLIGHTTIME-005-AP-02", "DIRECT", "Enablement is direct from setup parameter capture.", param("PX4", "COM_FLT_TIME_MAX", "enabled iff >0"))
    add("PX4-MC-FLIGHTTIME-005-AP-03", "CONDITIONAL", "PX4 EVENT provides a timestamp but requires exact firmware component metadata and matching warning ID.", event_px4("Carries maximum-flight-time warning when emitted."))
    add("PX4-MC-FLIGHTTIME-005-AP-04", "DIRECT", "Return mode is encoded in custom_mode; transition time requires observation clock or Event.", heartbeat_mode("PX4", "Decode AUTO_RTL/Return."), observation("PX4", "CURRENT_MODE", "custom_mode", "OUTGOING", "Direct current mode; no embedded timestamp.", None))

    # PX4 RTL landing delay.
    add("PX4-MC-RTLLOITER-006-AP-01", "INSTRUMENTATION_REQUIRED", "Mode/position/target can only model the phase; exact Navigator phase entry is not in standard MAVLink.", heartbeat_mode("PX4", "Confirms Return mode only."))
    add("PX4-MC-RTLLOITER-006-AP-02", "DERIVED", "Derive direct-return versus mission-landing path from archived parameters/mission and current mode; exact Navigator choice may need instrumentation.", param("PX4", "RTL_TYPE, RTL_LAND_DELAY", "combine with mission snapshot"), heartbeat_mode("PX4", "Current Return mode."))
    add("PX4-MC-RTLLOITER-006-AP-03", "DIRECT", "AUTO_LAND current mode is directly visible; campaign must decide whether DESCEND counts.", heartbeat_mode("PX4", "Decode AUTO_LAND; no timestamp."), observation("PX4", "CURRENT_MODE", "custom_mode", "OUTGOING", "Direct current mode; no timestamp.", None))
    return rules


def main() -> int:
    rules = make_rules()
    expected: dict[str, tuple[str, str]] = {}
    for system in ("ArduPilot", "PX4"):
        catalog = json.loads((BENCHMARK / system / "property_catalog.json").read_text(encoding="utf-8"))
        for prop in catalog["properties"]:
            for item in prop["atomic_propositions"]:
                expected[item["ap_id"]] = (system, item["name"])
    missing = set(expected) - set(rules)
    extra = set(rules) - set(expected)
    if missing or extra:
        raise ValueError(f"rule/AP mismatch missing={sorted(missing)} extra={sorted(extra)}")
    result = {
        "schema_version": "1.0",
        "scope": "Milestone-5 static observability audit; no runtime capture",
        "runtime_observation_status": "NOT_RUN_NO_CAPTURE",
        "clock_policy": "Embedded timestamps retain their documented sender/vehicle/GPS epoch; host arrival time is never substituted.",
        "counts": {},
        "atomic_propositions": [],
    }
    counts: dict[str, int] = {}
    for ap_id in sorted(expected):
        system, name = expected[ap_id]
        rule = rules[ap_id]
        counts[rule["observability"]] = counts.get(rule["observability"], 0) + 1
        result["atomic_propositions"].append({"ap_id": ap_id, "system": system, "name": name, **rule, "runtime_observation_status": "NOT_RUN_NO_CAPTURE"})
    result["counts"] = dict(sorted(counts.items()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(OUT.read_text(encoding="utf-8"))
    print(f"PASS: APs={len(expected)} counts={result['counts']} runtime=NOT_RUN_NO_CAPTURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
