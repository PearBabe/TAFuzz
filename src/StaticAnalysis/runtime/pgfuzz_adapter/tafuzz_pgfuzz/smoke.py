from __future__ import annotations

import datetime as dt
from pathlib import Path
import time
from typing import Any, Mapping

from .catalog import build_catalog
from .common import (append_jsonl, ensure_empty_new_directory, load_json,
                     utc_now, write_csv, write_json)
from .compat import initialise_result_directories, regenerate_result_files
from .engine import EFFECT_CSV_FIELDS, TrialRunner, derive_battery_value
from .metrics import aggregate_effects, evaluate_trial
from .report import write_report
from .states import StateWindow, registry_document
from .vehicle import SITLSession


def start_case_session(case_dir: Path, udp_port: int,
                       warmup_seconds: float = 8.0) -> SITLSession:
    session = SITLSession(case_dir, udp_port=udp_port, source_system=255)
    session.start(startup_timeout=60.0)
    session.request_state_streams(rate_hz=10)
    session.collect_window(warmup_seconds, "SMOKE_WARMUP", send_heartbeat=True)
    return session


def wait_for_armed(session: SITLSession, expected: bool,
                   timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        heartbeat = session.current_heartbeat(timeout=0.8)
        if heartbeat is not None and bool(heartbeat["armed"]) == expected:
            return True
    return False


def wait_for_relative_altitude(session: SITLSession, minimum_m: float,
                               timeout: float = 30.0) -> tuple[bool, float | None]:
    deadline = time.monotonic() + timeout
    latest = None
    while time.monotonic() < deadline:
        session.send_gcs_heartbeat()
        message = session.receive(0.2, "TAKEOFF_WAIT")
        if message is None or int(message.get_srcSystem()) != session.sysid:
            continue
        if message.get_type() == "GLOBAL_POSITION_INT":
            latest = float(message.relative_alt) / 1000.0
            if latest >= minimum_m:
                return True, latest
    return False, latest


def arm_and_takeoff(session: SITLSession, target_altitude_m: float = 10.0) -> dict[str, Any]:
    mode = session.set_mode(4, timeout=8.0)  # GUIDED
    if not mode.get("verified"):
        raise RuntimeError(f"unable to enter GUIDED: {mode}")
    arm_attempts = []
    arm_deadline = time.monotonic() + 50.0
    while True:
        arm = session.command_long(session.dialect.MAV_CMD_COMPONENT_ARM_DISARM,
                                   [1.0], timeout=8.0)
        arm_attempts.append(arm)
        if arm.get("verified") and wait_for_armed(session, True):
            break
        if time.monotonic() >= arm_deadline:
            raise RuntimeError(
                "vehicle did not arm through the normal GCS command after "
                f"bounded estimator/home warmup: {arm_attempts}")
        # Fresh SITL can announce "ArduPilot Ready" before the accelerometer
        # consistency and AHRS home pre-arm checks have converged. Keep normal
        # checks enabled, collect their STATUSTEXT evidence, and retry.
        session.collect_window(5.0, "ARM_RETRY_WARMUP", send_heartbeat=True)
    takeoff = session.command_long(session.dialect.MAV_CMD_NAV_TAKEOFF,
                                   [0, 0, 0, 0, 0, 0, target_altitude_m],
                                   timeout=8.0)
    if not takeoff.get("verified"):
        raise RuntimeError(f"takeoff command not accepted: {takeoff}")
    reached, altitude = wait_for_relative_altitude(session, minimum_m=5.0)
    if not reached:
        raise RuntimeError(f"takeoff altitude was not observed; latest={altitude}")
    return {"mode": mode, "arm": arm, "arm_attempts": arm_attempts,
            "takeoff": takeoff,
            "observed_relative_altitude_m": altitude}


def land_and_disarm(session: SITLSession) -> dict[str, Any]:
    land = session.set_mode(9, timeout=8.0)
    deadline = time.monotonic() + 35.0
    disarmed = False
    while time.monotonic() < deadline:
        heartbeat = session.current_heartbeat(timeout=0.8)
        if heartbeat is not None and not heartbeat["armed"]:
            disarmed = True
            break
    if not disarmed:
        disarm = session.command_long(
            session.dialect.MAV_CMD_COMPONENT_ARM_DISARM, [0.0], timeout=8.0)
        disarmed = bool(disarm.get("verified")) and wait_for_armed(session, False)
    return {"land_mode_verified": bool(land.get("verified")),
            "disarmed_verified": disarmed}


def parameter_type(rows: Mapping[str, Mapping[str, Any]], name: str) -> str:
    row = rows.get(name)
    if row is None:
        raise KeyError(f"required runtime parameter not in catalog: {name}")
    return str(row["value_type"])


def environment_case(run_dir: Path, catalog_rows: list[dict[str, Any]],
                     udp_port: int) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = {str(row["name"]): row for row in catalog_rows}
    row = rows["SIM_BATT_VOLTAGE"]
    mutation = derive_battery_value(row, rows)
    if mutation is None:
        raise RuntimeError("unable to derive safe SIM_BATT_VOLTAGE mutation")
    case_dir = run_dir / "smoke_cases/environment"
    session = start_case_session(case_dir, udp_port)
    runner = TrialRunner(case_dir, repetitions=3, window_seconds=3.0,
                         udp_port=udp_port)
    runner.session = session
    repetitions = []
    try:
        for index in range(1, 4):
            repetitions.append(runner.parameter_repetition(row, mutation, index))
    finally:
        session.stop()
    effect = aggregate_effects(str(row["name"]), repetitions)
    effect.update({
        "work_id": "smoke-environment-sim-batt-voltage",
        "input_type": "INPUT_E", "transport": "PARAM_SET",
        "mutation_value": mutation, "execution_class": "READY_SAFE",
        "mode_context": "GROUND_DEFAULT", "error": "",
    })
    evidence = {
        "case": "environment", "input": "SIM_BATT_VOLTAGE",
        "original_value": row["current_value"], "mutation_value": mutation,
        "effect": effect, "repetitions": repetitions,
    }
    write_json(case_dir / "case_evidence.json", evidence)
    return effect, evidence


def command_case(run_dir: Path, catalog_rows: list[dict[str, Any]],
                 udp_port: int) -> tuple[dict[str, Any], dict[str, Any]]:
    row = next(row for row in catalog_rows
               if row["name"] == "RC1" and row["transport"] == "RC_CHANNELS_OVERRIDE")
    case_dir = run_dir / "smoke_cases/command"
    session = start_case_session(case_dir, udp_port)
    runner = TrialRunner(case_dir, repetitions=3, window_seconds=3.0,
                         udp_port=udp_port)
    runner.session = session
    repetitions = []
    setup: dict[str, Any] = {}
    teardown: dict[str, Any] = {}
    try:
        setup = arm_and_takeoff(session)
        alt_hold = session.set_mode(2, timeout=8.0)
        if not alt_hold.get("verified"):
            raise RuntimeError(f"unable to enter ALT_HOLD for RC smoke: {alt_hold}")
        session.collect_window(3.0, "RC_STABILISE", send_heartbeat=True)
        for index in range(1, 4):
            repetitions.append(runner.rc_repetition(row, 1700, index))
        teardown = land_and_disarm(session)
    finally:
        session.release_rc_overrides()
        session.stop()
    effect = aggregate_effects("RC1", repetitions)
    effect.update({
        "work_id": "smoke-command-rc1", "input_type": "INPUT_C",
        "protocol_field": row["protocol_field"],
        "transport": "RC_CHANNELS_OVERRIDE", "mutation_value": 1700,
        "execution_class": "READY_SAFE", "mode_context": "ALT_HOLD_AIRBORNE",
        "error": "",
    })
    evidence = {"case": "command", "input": "RC1",
                "protocol_field": row["protocol_field"], "setup": setup,
                "teardown": teardown, "effect": effect,
                "repetitions": repetitions}
    write_json(case_dir / "case_evidence.json", evidence)
    return effect, evidence


def observe_gcs_failsafe(session: SITLSession, configured_timeout: float,
                         label: str) -> dict[str, Any]:
    # A previous observation intentionally stopped GCS heartbeats. Resume them
    # for long enough to let the 3 Hz failsafe check clear before requesting
    # GUIDED again; otherwise a valid request can race the prior failsafe state.
    session.collect_window(1.0, f"{label}_CLEAR_PRIOR_FAILSAFE",
                           send_heartbeat=True)
    guided = session.set_mode(4, timeout=8.0)
    if not guided.get("verified"):
        raise RuntimeError(f"unable to restore GUIDED before {label}: {guided}")
    session.collect_window(2.0, f"{label}_GCS_SEEN", send_heartbeat=True)
    session.send_gcs_heartbeat()
    last_heartbeat_ns = time.monotonic_ns()
    window = StateWindow(label)
    deadline = time.monotonic() + configured_timeout + 3.0
    observed_ns = None
    evidence_kind = ""
    while time.monotonic() < deadline:
        message = session.receive(0.1, label)
        if message is None or int(message.get_srcSystem()) != session.sysid:
            continue
        window.ingest(message)
        if message.get_type() == "STATUSTEXT" and "GCS" in str(message.text):
            observed_ns = time.monotonic_ns()
            evidence_kind = "STATUSTEXT_CONTAINS_GCS"
            break
        if message.get_type() == "HEARTBEAT" and int(message.custom_mode) != 4:
            observed_ns = time.monotonic_ns()
            evidence_kind = "HEARTBEAT_MODE_LEFT_GUIDED"
            break
    session.send_gcs_heartbeat()
    if observed_ns is None:
        return {"observed": False, "configured_timeout": configured_timeout,
                "window": window.summary(), "last_gcs_heartbeat_host_monotonic_ns": last_heartbeat_ns}
    return {
        "observed": True, "configured_timeout": configured_timeout,
        "observed_transition_latency_seconds": (observed_ns - last_heartbeat_ns) / 1e9,
        "evidence_kind": evidence_kind,
        "last_gcs_heartbeat_host_monotonic_ns": last_heartbeat_ns,
        "observed_host_monotonic_ns": observed_ns,
        "clock_semantics": "harness-observed transition latency; not internal event time",
        "window": window.summary(),
    }


def temporal_summary(label: str, observation: Mapping[str, Any]) -> dict[str, Any]:
    values = ([float(observation["observed_transition_latency_seconds"])]
              if observation.get("observed") else [])
    return {
        "phase": label,
        "samples": {"event.gcs_failsafe_observed_latency": values},
        "legacy_vector": [0.0] * 34,
        "observation": dict(observation),
    }


def parameter_case(run_dir: Path, catalog_rows: list[dict[str, Any]],
                   udp_port: int) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = {str(row["name"]): row for row in catalog_rows}
    timeout_row = rows["FS_GCS_TIMEOUT"]
    originals = {name: rows[name]["current_value"]
                 for name in ["FS_GCS_TIMEOUT", "FS_GCS_ENABLE", "FS_OPTIONS"]}
    case_dir = run_dir / "smoke_cases/parameter"
    session = start_case_session(case_dir, udp_port)
    repetitions = []
    setup: dict[str, Any] = {}
    teardown: dict[str, Any] = {}
    preconditions: dict[str, Any] = {}
    try:
        preconditions["FS_GCS_ENABLE"] = session.set_parameter(
            "FS_GCS_ENABLE", 1.0, parameter_type(rows, "FS_GCS_ENABLE"))
        preconditions["FS_OPTIONS"] = session.set_parameter(
            "FS_OPTIONS", 0.0, parameter_type(rows, "FS_OPTIONS"))
        if not all(result.get("verified") for result in preconditions.values()):
            raise RuntimeError(f"GCS failsafe preconditions failed: {preconditions}")
        setup = arm_and_takeoff(session)
        original_timeout = float(originals["FS_GCS_TIMEOUT"])
        mutation_timeout = 2.0
        for index in range(1, 4):
            base_set = session.set_parameter(
                "FS_GCS_TIMEOUT", original_timeout,
                parameter_type(rows, "FS_GCS_TIMEOUT"))
            baseline_observation = observe_gcs_failsafe(
                session, original_timeout, f"R{index}_BASELINE_TIMEOUT")
            application = session.set_parameter(
                "FS_GCS_TIMEOUT", mutation_timeout,
                parameter_type(rows, "FS_GCS_TIMEOUT"))
            treatment_observation = observe_gcs_failsafe(
                session, mutation_timeout, f"R{index}_MUTATED_TIMEOUT")
            restoration = session.set_parameter(
                "FS_GCS_TIMEOUT", original_timeout,
                parameter_type(rows, "FS_GCS_TIMEOUT"))
            recovery_observation = observe_gcs_failsafe(
                session, original_timeout, f"R{index}_RECOVERY_TIMEOUT")
            baseline = temporal_summary("BASELINE", baseline_observation)
            treatment = temporal_summary("TREATMENT", treatment_observation)
            recovery = temporal_summary("RECOVERY", recovery_observation)
            feature_effects = evaluate_trial(
                baseline, treatment, recovery,
                bool(application.get("verified")),
                bool(restoration.get("verified")))
            repetitions.append({
                "repetition": index, "baseline": baseline,
                "treatment": treatment, "recovery": recovery,
                "base_set": base_set, "application": application,
                "restoration": restoration, "feature_effects": feature_effects,
            })
        restored_enable = session.set_parameter(
            "FS_GCS_ENABLE", float(originals["FS_GCS_ENABLE"]),
            parameter_type(rows, "FS_GCS_ENABLE"))
        restored_options = session.set_parameter(
            "FS_OPTIONS", float(originals["FS_OPTIONS"]),
            parameter_type(rows, "FS_OPTIONS"))
        teardown = land_and_disarm(session)
        teardown.update({"restored_FS_GCS_ENABLE": restored_enable,
                         "restored_FS_OPTIONS": restored_options})
    finally:
        session.stop()
    effect = aggregate_effects("FS_GCS_TIMEOUT", repetitions)
    effect.update({
        "work_id": "smoke-parameter-fs-gcs-timeout", "input_type": "INPUT_P",
        "transport": "PARAM_SET", "mutation_value": 2.0,
        "execution_class": "READY_SAFE", "mode_context": "GUIDED_AIRBORNE",
        "error": "",
    })
    evidence = {"case": "parameter", "input": "FS_GCS_TIMEOUT",
                "originals": originals, "preconditions": preconditions,
                "setup": setup, "teardown": teardown, "effect": effect,
                "repetitions": repetitions}
    write_json(case_dir / "case_evidence.json", evidence)
    return effect, evidence


def smoke_command(args: Any) -> int:
    run_id = args.run_id or (
        "smoke-" + dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S"))
    run_dir = args.output_root / run_id
    ensure_empty_new_directory(run_dir)
    build_catalog(run_dir, udp_port=args.udp_port, param_timeout=180.0)
    catalogue = load_json(run_dir / "input_catalog.json")
    rows = list(catalogue["inputs"])
    initialise_result_directories(run_dir)
    write_json(run_dir / "state_registry.json", registry_document())
    selected = args.case or ["environment", "command", "parameter"]
    handlers = {
        "environment": environment_case,
        "command": command_case,
        "parameter": parameter_case,
    }
    effects = []
    cases = []
    errors = []
    for offset, case in enumerate(selected, start=1):
        try:
            effect, evidence = handlers[case](
                run_dir, rows, args.udp_port + offset * 10)
            effects.append(effect)
            cases.append(evidence)
            for repetition in evidence.get("repetitions", []):
                append_jsonl(run_dir / "trials.jsonl", {
                    "case": case, "input_name": effect["input_name"],
                    "protocol_field": effect.get("protocol_field"),
                    "mutation_value": effect.get("mutation_value"),
                    **repetition,
                })
        except Exception as exc:
            errors.append({"case": case, "error": f"{type(exc).__name__}: {exc}"})
    write_json(run_dir / "input_state_effects.json", {
        "schema_version": "1.0", "effects": effects})
    write_csv(run_dir / "input_state_effects.csv", effects, EFFECT_CSV_FIELDS)
    regenerate_result_files(run_dir, effects)
    expected = {
        "environment": ("SIM_BATT_VOLTAGE", "status"),
        "command": ("RC1", "roll"),
        "parameter": ("FS_GCS_TIMEOUT", "status"),
    }
    checks = []
    effect_by_name = {effect["input_name"]: effect for effect in effects}
    for case in selected:
        name, group = expected[case]
        effect = effect_by_name.get(name)
        result_file = run_dir / "results" / f"{group}.txt"
        names = set(result_file.read_text(encoding="utf-8").splitlines())
        checks.append({
            "case": case, "input": name, "expected_group": group,
            "protocol_field": (effect.get("protocol_field") if effect else None),
            "effect_status": effect.get("status") if effect else "MISSING",
            "result_file_contains_exact_name": name in names,
            "passed": bool(effect and effect.get("status") == "CONFIRMED_EFFECT" and name in names),
        })
    passed = not errors and all(check["passed"] for check in checks)
    certificate = {
        "schema_version": "1.0", "generated_at": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "selected_cases": selected, "checks": checks, "errors": errors,
        "full_campaign_executed": False,
        "clock_boundary": "host-observed timing is not internal firmware event time",
    }
    write_json(run_dir / "smoke_certificate.json", certificate)
    write_json(run_dir / "checkpoint.json", {
        "schema_version": "1.0", "updated_at": utc_now(),
        "completed_cases": [check["case"] for check in checks if check["passed"]],
        "failed_cases": [check["case"] for check in checks if not check["passed"]],
        "total_planned_cases": len(selected),
    })
    manifest = load_json(run_dir / "manifest.json")
    manifest.update({
        "command": "smoke", "smoke_status": certificate["status"],
        "smoke_selected_cases": selected, "full_campaign_executed": False,
    })
    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "experiment_plan.json", {
        "schema_version": "1.0", "preset": "SMOKE_ONLY",
        "shard_index": 0, "shard_count": 1, "repetitions": 3,
        "window_seconds": 3.0, "work_item_count": len(selected),
        "work_items": selected,
    })
    write_report(run_dir)
    print(f"smoke {certificate['status']}: {run_dir}")
    for check in checks:
        print(f"{check['case']}: {check['effect_status']} "
              f"file={check['result_file_contains_exact_name']}")
    for error in errors:
        print(f"{error['case']}: {error['error']}")
    return 0 if passed else 1
