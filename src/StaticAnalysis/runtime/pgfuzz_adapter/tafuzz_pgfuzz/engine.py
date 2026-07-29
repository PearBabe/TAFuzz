from __future__ import annotations

import hashlib
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping

from .common import append_jsonl, load_json, utc_now, write_csv, write_json
from .compat import initialise_result_directories, regenerate_result_files
from .metrics import aggregate_effects, evaluate_trial
from .states import registry_document
from .vehicle import SITLSession


EFFECT_CSV_FIELDS = [
    "work_id", "input_name", "protocol_field", "input_type", "transport", "mutation_value",
    "status", "confirmed_groups", "legacy_groups", "repetition_count",
    "execution_class", "mode_context", "error",
]


def stable_work_id(input_id: str, mutation: Any) -> str:
    identity = f"{input_id}|{mutation!r}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()[:16]


def derive_battery_value(row: Mapping[str, Any], rows_by_name: Mapping[str, Mapping[str, Any]]) -> float | None:
    current = float(row["current_value"])
    thresholds = []
    for name in ["BATT_LOW_VOLT", "BATT_CRT_VOLT"]:
        value = rows_by_name.get(name, {}).get("current_value")
        if isinstance(value, (int, float)) and value > 0:
            thresholds.append(float(value))
    floor = max(thresholds, default=0.0)
    if floor > 0 and floor < current:
        candidate = (floor + current) / 2.0
    else:
        candidate = current * 0.9
    return round(candidate, 3) if 0 < candidate < current else None


def plan_work_items(catalog: Mapping[str, Any], selected_names: set[str] | None = None,
                    shard_index: int = 0, shard_count: int = 1) -> list[dict[str, Any]]:
    rows = list(catalog["inputs"])
    rows_by_name = {str(row["name"]): row for row in rows}
    items: list[dict[str, Any]] = []
    for row in rows:
        if row.get("execution_class") != "READY_SAFE":
            continue
        name = str(row["name"])
        if selected_names is not None and name not in selected_names:
            continue
        mutations = list(row.get("mutation_values") or [])
        if row["input_type"] in {"INPUT_P", "INPUT_E"}:
            resolved = []
            for value in mutations:
                if value == "DERIVE_SAFE_LOWER_FROM_BATTERY_THRESHOLDS":
                    value = derive_battery_value(row, rows_by_name)
                if value is not None and value != row.get("current_value"):
                    resolved.append(value)
            mutations = resolved
        elif row.get("transport") in {"COMMAND_LONG", "COMMAND_INT"}:
            mutations = ["RECIPE_DEFAULT"]
        if not mutations:
            continue
        for mutation in mutations:
            item = {
                "work_id": stable_work_id(str(row["input_id"]), mutation),
                "input": row, "mutation_value": mutation,
            }
            items.append(item)
    items.sort(key=lambda item: (item["input"]["input_type"],
                                 item["input"]["name"], repr(item["mutation_value"])))
    if shard_count < 1 or shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard index/count must satisfy 0 <= index < count")
    return [item for index, item in enumerate(items) if index % shard_count == shard_index]


class TrialRunner:
    def __init__(self, run_dir: Path, repetitions: int = 3,
                 window_seconds: float = 2.0, udp_port: int = 19501) -> None:
        self.run_dir = run_dir
        self.repetitions = repetitions
        self.window_seconds = window_seconds
        self.udp_port = udp_port
        self.session: SITLSession | None = None
        existing_numbers = []
        sessions_dir = self.run_dir / "sessions"
        if sessions_dir.is_dir():
            for path in sessions_dir.glob("session-[0-9][0-9][0-9][0-9]"):
                try:
                    existing_numbers.append(int(path.name.split("-")[-1]))
                except ValueError:
                    continue
        self.restart_count = max(existing_numbers, default=-1) + 1

    def start_session(self) -> None:
        self.stop_session()
        session_dir = self.run_dir / "sessions" / f"session-{self.restart_count:04d}"
        self.session = SITLSession(session_dir,
                                   udp_port=self.udp_port + self.restart_count)
        self.session.start(startup_timeout=60.0)
        self.session.request_state_streams(rate_hz=10)
        self.session.collect_window(5.0, "WARMUP", send_heartbeat=True)
        self.restart_count += 1

    def stop_session(self) -> None:
        if self.session is not None:
            self.session.stop()
            self.session = None

    def parameter_repetition(self, row: Mapping[str, Any], mutation: Any,
                             index: int) -> dict[str, Any]:
        session = self.session
        original = float(row["current_value"])
        baseline = session.collect_window(
            self.window_seconds, f"R{index}_BASELINE", send_heartbeat=True)
        application = session.set_parameter(
            str(row["name"]), float(mutation), str(row["value_type"]))
        treatment = session.collect_window(
            self.window_seconds, f"R{index}_TREATMENT", send_heartbeat=True)
        restoration = session.set_parameter(
            str(row["name"]), original, str(row["value_type"]))
        recovery = session.collect_window(
            self.window_seconds, f"R{index}_RECOVERY", send_heartbeat=True)
        effects = evaluate_trial(
            baseline, treatment, recovery, bool(application.get("verified")),
            bool(restoration.get("verified")))
        return {
            "repetition": index, "baseline": baseline, "treatment": treatment,
            "recovery": recovery, "application": application,
            "restoration": restoration, "feature_effects": effects,
        }

    def rc_repetition(self, row: Mapping[str, Any], mutation: Any,
                      index: int) -> dict[str, Any]:
        session = self.session
        channel = int(str(row["name"])[2:])
        baseline = session.collect_window(
            self.window_seconds, f"R{index}_BASELINE", send_heartbeat=True)

        def apply() -> None:
            session.send_rc_override(channel, int(mutation))

        apply()
        treatment = session.collect_window(
            self.window_seconds, f"R{index}_TREATMENT", send_heartbeat=True,
            periodic_action=apply)
        samples = treatment.get("samples", {}).get(f"rc.chan{channel}_raw", [])
        observed = statistics.median(samples) if samples else None
        verified = observed is not None and abs(float(observed) - float(mutation)) <= 5
        session.release_rc_overrides()
        recovery = session.collect_window(
            self.window_seconds, f"R{index}_RECOVERY", send_heartbeat=True)
        recovery_samples = recovery.get("samples", {}).get(
            f"rc.chan{channel}_raw", [])
        recovery_verified = bool(recovery_samples) and any(
            abs(float(value) - float(mutation)) > 5 for value in recovery_samples)
        application = {"verified": verified, "requested_pwm": mutation,
                       "observed_median_pwm": observed}
        restoration = {"verified": recovery_verified, "strategy": "RC_RELEASE"}
        effects = evaluate_trial(
            baseline, treatment, recovery, verified, recovery_verified)
        return {
            "repetition": index, "baseline": baseline, "treatment": treatment,
            "recovery": recovery, "application": application,
            "restoration": restoration, "feature_effects": effects,
        }

    def mode_repetition(self, row: Mapping[str, Any], mutation: Any,
                        index: int) -> dict[str, Any]:
        session = self.session
        before = session.current_heartbeat()
        if before is None:
            raise RuntimeError("no baseline HEARTBEAT before mode intervention")
        baseline_mode = int(before["custom_mode"])
        baseline = session.collect_window(
            self.window_seconds, f"R{index}_BASELINE", send_heartbeat=True)
        application = session.set_mode(int(mutation))
        treatment = session.collect_window(
            self.window_seconds, f"R{index}_TREATMENT", send_heartbeat=True)
        restoration = session.set_mode(baseline_mode)
        recovery = session.collect_window(
            self.window_seconds, f"R{index}_RECOVERY", send_heartbeat=True)
        effects = evaluate_trial(
            baseline, treatment, recovery, bool(application.get("verified")),
            bool(restoration.get("verified")))
        return {
            "repetition": index, "baseline": baseline, "treatment": treatment,
            "recovery": recovery, "application": application,
            "restoration": restoration, "feature_effects": effects,
        }

    def command_repetition(self, row: Mapping[str, Any], index: int) -> dict[str, Any]:
        session = self.session
        name = str(row["name"])
        baseline = session.collect_window(
            self.window_seconds, f"R{index}_BASELINE", send_heartbeat=True)
        if name == "MAV_CMD_COMPONENT_ARM_DISARM":
            heartbeat = session.current_heartbeat()
            was_armed = bool(heartbeat and heartbeat["armed"])
            application = session.command_long(
                int(row["numeric_id"]), [0.0 if was_armed else 1.0])
            treatment = session.collect_window(
                self.window_seconds, f"R{index}_TREATMENT", send_heartbeat=True)
            restoration = session.command_long(
                int(row["numeric_id"]), [1.0 if was_armed else 0.0])
        elif name == "MAV_CMD_DO_SEND_BANNER":
            application = session.command_long(int(row["numeric_id"]), [])
            treatment = session.collect_window(
                self.window_seconds, f"R{index}_TREATMENT", send_heartbeat=True)
            restoration = {"verified": True, "strategy": "NO_PERSISTENT_COMMAND_STATE"}
        else:
            raise RuntimeError(f"no runtime command recipe for {name}")
        recovery = session.collect_window(
            self.window_seconds, f"R{index}_RECOVERY", send_heartbeat=True)
        effects = evaluate_trial(
            baseline, treatment, recovery, bool(application.get("verified")),
            bool(restoration.get("verified")))
        return {
            "repetition": index, "baseline": baseline, "treatment": treatment,
            "recovery": recovery, "application": application,
            "restoration": restoration, "feature_effects": effects,
        }

    def run_item(self, item: Mapping[str, Any]) -> dict[str, Any]:
        row = item["input"]
        mutation = item["mutation_value"]
        repetitions: list[dict[str, Any]] = []
        error = ""
        for index in range(1, self.repetitions + 1):
            try:
                if row["input_type"] in {"INPUT_P", "INPUT_E"}:
                    repetition = self.parameter_repetition(row, mutation, index)
                elif row["transport"] == "RC_CHANNELS_OVERRIDE":
                    repetition = self.rc_repetition(row, mutation, index)
                elif row["transport"] == "SET_MODE":
                    repetition = self.mode_repetition(row, mutation, index)
                else:
                    repetition = self.command_repetition(row, index)
                repetitions.append(repetition)
                append_jsonl(self.run_dir / "trials.jsonl", {
                    "work_id": item["work_id"], "input_name": row["name"],
                    "mutation_value": mutation, **repetition,
                })
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                break
        effect = aggregate_effects(str(row["name"]), repetitions)
        effect.update({
            "work_id": item["work_id"], "input_type": row["input_type"],
            "protocol_field": row.get("protocol_field"),
            "transport": row["transport"], "mutation_value": mutation,
            "execution_class": row["execution_class"], "mode_context": "RUNTIME_OBSERVED",
            "error": error,
        })
        application_verified = bool(repetitions) and all(
            bool(repetition.get("application", {}).get("verified"))
            for repetition in repetitions)
        recovery_verified = bool(repetitions) and all(
            bool(repetition.get("restoration", {}).get("verified"))
            for repetition in repetitions)
        effect["application_verified_all_repetitions"] = application_verified
        effect["recovery_verified_all_repetitions"] = recovery_verified
        if not error and (not application_verified or not recovery_verified):
            error = ("INPUT_APPLICATION_VERIFICATION_FAILED" if not application_verified
                     else "INPUT_RECOVERY_VERIFICATION_FAILED")
            effect["error"] = error
        if error:
            effect["status"] = "INCONCLUSIVE"
        return effect

    def run(self, items: list[dict[str, Any]], resume: bool = False,
            global_work_item_count: int | None = None) -> list[dict[str, Any]]:
        initialise_result_directories(self.run_dir)
        write_json(self.run_dir / "state_registry.json", registry_document())
        checkpoint_path = self.run_dir / "checkpoint.json"
        effects_path = self.run_dir / "input_state_effects.json"
        completed: set[str] = set()
        effects: list[dict[str, Any]] = []
        if resume and checkpoint_path.exists():
            completed = set(load_json(checkpoint_path).get("completed_work_ids", []))
        if resume and effects_path.exists():
            effects = list(load_json(effects_path).get("effects", []))
        try:
            self.start_session()
            for item in items:
                if item["work_id"] in completed:
                    continue
                effect = self.run_item(item)
                effects.append(effect)
                completed.add(str(item["work_id"]))
                write_json(effects_path, {"schema_version": "1.0", "effects": effects})
                write_csv(self.run_dir / "input_state_effects.csv", effects,
                          EFFECT_CSV_FIELDS)
                regenerate_result_files(self.run_dir, effects)
                write_json(checkpoint_path, {
                    "schema_version": "1.0", "updated_at": utc_now(),
                    "completed_work_ids": sorted(completed),
                    "completed_work_item_count": len(completed),
                    "current_shard_planned_work_items": len(items),
                    "global_planned_work_items": (global_work_item_count
                                                  if global_work_item_count is not None
                                                  else len(items)),
                })
                if effect["status"] == "INCONCLUSIVE" and effect.get("error"):
                    self.start_session()
        finally:
            self.stop_session()
        return effects


def run_experiment(run_dir: Path, selected_names: set[str] | None,
                   shard_index: int, shard_count: int, repetitions: int,
                   window_seconds: float, dry_run: bool, resume: bool,
                   udp_port: int = 19501) -> dict[str, Any]:
    catalog = load_json(run_dir / "input_catalog.json")
    global_items = plan_work_items(catalog, selected_names, 0, 1)
    items = plan_work_items(catalog, selected_names, shard_index, shard_count)
    plan = {
        "schema_version": "1.0", "generated_at": utc_now(),
        "preset": "current_safe_full", "shard_index": shard_index,
        "shard_count": shard_count, "repetitions": repetitions,
        "window_seconds": window_seconds, "work_item_count": len(items),
        "global_work_item_count": len(global_items),
        "work_items": [{
            "work_id": item["work_id"], "input_name": item["input"]["name"],
            "protocol_field": item["input"].get("protocol_field"),
            "input_type": item["input"]["input_type"],
            "transport": item["input"]["transport"],
            "mutation_value": item["mutation_value"],
        } for item in items],
    }
    write_json(run_dir / "experiment_plan.json", plan)
    append_jsonl(run_dir / "experiment_plans.jsonl", plan)
    initialise_result_directories(run_dir)
    write_json(run_dir / "state_registry.json", registry_document())
    if dry_run:
        manifest = load_json(run_dir / "manifest.json")
        manifest.update({"command": "run-dry-run", "dynamic_inputs_executed": False,
                         "full_campaign_complete": False})
        write_json(run_dir / "manifest.json", manifest)
        return {"plan": plan, "effects": [], "dry_run": True}
    runner = TrialRunner(run_dir, repetitions=repetitions,
                         window_seconds=window_seconds, udp_port=udp_port)
    effects = runner.run(items, resume=resume,
                         global_work_item_count=len(global_items))
    manifest = load_json(run_dir / "manifest.json")
    completed_ids = {str(effect.get("work_id")) for effect in effects
                     if effect.get("work_id")}
    manifest.update({
        "command": "run", "dynamic_inputs_executed": True,
        "full_campaign_complete": len(completed_ids) >= len(global_items),
        "global_work_item_count": len(global_items),
        "completed_work_item_count": len(completed_ids),
    })
    write_json(run_dir / "manifest.json", manifest)
    return {"plan": plan, "effects": effects, "dry_run": False}
