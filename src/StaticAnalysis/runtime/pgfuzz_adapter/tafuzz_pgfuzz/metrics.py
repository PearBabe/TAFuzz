from __future__ import annotations

import math
import statistics
from typing import Any, Iterable, Mapping

from .states import FEATURE_GROUP, FEATURE_TOLERANCE, LEGACY_GROUP_BY_INDEX, RESULT_GROUPS


def median(values: Iterable[float]) -> float | None:
    sequence = list(values)
    return float(statistics.median(sequence)) if sequence else None


def median_absolute_deviation(values: Iterable[float]) -> float:
    sequence = list(values)
    if not sequence:
        return 0.0
    center = statistics.median(sequence)
    return float(statistics.median(abs(value - center) for value in sequence))


def legacy_groups(baseline_vectors: list[list[float]],
                  treatment_vectors: list[list[float]],
                  minimum_sd: float = 0.00001) -> tuple[list[str], list[dict[str, Any]]]:
    if not baseline_vectors or len(baseline_vectors) != len(treatment_vectors):
        return [], []
    baseline = [sum(vector[index] for vector in baseline_vectors) / len(baseline_vectors)
                for index in range(34)]
    treatment = [sum(vector[index] for vector in treatment_vectors) / len(treatment_vectors)
                 for index in range(34)]
    details: list[dict[str, Any]] = []
    groups: set[str] = set()
    for index, (base_sd, input_sd) in enumerate(zip(baseline, treatment)):
        matched = input_sd > minimum_sd and abs(base_sd - input_sd) > base_sd
        group = LEGACY_GROUP_BY_INDEX[index]
        details.append({
            "raw_state_index": index, "result_group": group,
            "baseline_sd": base_sd, "input_sd": input_sd, "matched": matched,
        })
        if matched:
            groups.add(group)
    return [group for group in RESULT_GROUPS if group in groups], details


def evaluate_feature(feature: str, baseline: list[float], treatment: list[float],
                     recovery: list[float], input_verified: bool,
                     recovery_verified: bool) -> dict[str, Any]:
    base_median, input_median, recovery_median = (
        median(baseline), median(treatment), median(recovery))
    tolerance = float(FEATURE_TOLERANCE.get(feature, 0.0))
    baseline_mad = median_absolute_deviation(baseline)
    threshold = max(tolerance, 3.0 * baseline_mad)
    if base_median is None or input_median is None:
        status = "INCONCLUSIVE"
        reason = "baseline or intervention window has no samples"
        direction = "UNKNOWN"
        changed = False
        recovered = False
    else:
        difference = input_median - base_median
        changed = abs(difference) > threshold
        direction = "INCREASE" if difference > 0 else "DECREASE" if difference < 0 else "UNCHANGED"
        recovered = (recovery_median is not None and
                     abs(recovery_median - base_median) <= threshold)
        if not input_verified:
            status, reason = "INCONCLUSIVE", "input application was not verified"
        elif changed and recovery_verified and recovered:
            status, reason = "TRIAL_EFFECT", "paired median changed beyond baseline noise and recovered"
        elif changed and not recovery_verified:
            status, reason = "INCONCLUSIVE", "state changed but input recovery was not verified"
        elif changed and not recovered:
            status, reason = "INCONCLUSIVE", "state changed but recovery window did not return to baseline"
        else:
            status, reason = "NO_TRIAL_EFFECT", "paired median stayed within baseline-derived tolerance"
    return {
        "feature": feature, "result_group": FEATURE_GROUP.get(feature),
        "baseline_sample_count": len(baseline),
        "treatment_sample_count": len(treatment),
        "recovery_sample_count": len(recovery),
        "baseline_median": base_median, "treatment_median": input_median,
        "recovery_median": recovery_median, "baseline_mad": baseline_mad,
        "absolute_tolerance": tolerance, "decision_threshold": threshold,
        "direction": direction, "changed": changed, "recovered": recovered,
        "trial_status": status, "reason": reason,
    }


def evaluate_trial(baseline: Mapping[str, Any], treatment: Mapping[str, Any],
                   recovery: Mapping[str, Any], input_verified: bool,
                   recovery_verified: bool) -> list[dict[str, Any]]:
    keys = sorted(set(baseline.get("samples", {})) |
                  set(treatment.get("samples", {})) |
                  set(recovery.get("samples", {})))
    return [
        evaluate_feature(
            key, list(baseline.get("samples", {}).get(key, [])),
            list(treatment.get("samples", {}).get(key, [])),
            list(recovery.get("samples", {}).get(key, [])),
            input_verified, recovery_verified)
        for key in keys if key in FEATURE_GROUP
    ]


def aggregate_effects(input_name: str, repetitions: list[Mapping[str, Any]]) -> dict[str, Any]:
    baseline_vectors = [list(rep["baseline"]["legacy_vector"]) for rep in repetitions]
    treatment_vectors = [list(rep["treatment"]["legacy_vector"]) for rep in repetitions]
    legacy, legacy_details = legacy_groups(baseline_vectors, treatment_vectors)
    feature_trials: dict[str, list[Mapping[str, Any]]] = {}
    for repetition in repetitions:
        for effect in repetition.get("feature_effects", []):
            feature_trials.setdefault(str(effect["feature"]), []).append(effect)
    feature_results: list[dict[str, Any]] = []
    confirmed_groups: set[str] = set()
    inconclusive = False
    for feature, trials in sorted(feature_trials.items()):
        positive = [trial for trial in trials if trial["trial_status"] == "TRIAL_EFFECT"]
        directions = [trial["direction"] for trial in positive]
        consistent_direction = (max((directions.count(value) for value in set(directions)),
                                    default=0) >= 2)
        if len(positive) >= 2 and consistent_direction:
            status = "CONFIRMED_EFFECT"
            group = str(positive[0]["result_group"])
            confirmed_groups.add(group)
        elif any(trial["trial_status"] == "INCONCLUSIVE" for trial in trials):
            status = "INCONCLUSIVE"
            inconclusive = True
        else:
            status = "NO_OBSERVED_EFFECT"
        feature_results.append({
            "feature": feature, "result_group": trials[0].get("result_group"),
            "status": status, "trial_count": len(trials),
            "positive_trial_count": len(positive),
            "directions": directions, "trials": trials,
        })
    groups = [group for group in RESULT_GROUPS if group in confirmed_groups]
    if groups:
        overall = "CONFIRMED_EFFECT"
    elif legacy:
        overall = "LEGACY_ONLY_CANDIDATE"
    elif inconclusive or not repetitions:
        overall = "INCONCLUSIVE"
    else:
        overall = "NO_OBSERVED_EFFECT"
    return {
        "input_name": input_name, "status": overall,
        "confirmed_groups": groups, "legacy_groups": legacy,
        "feature_results": feature_results, "legacy_details": legacy_details,
        "repetition_count": len(repetitions),
    }
