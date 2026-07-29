"""Timed accepting-lasso feedback and mutation ranking."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any, Iterable, Mapping

from .model import (
    GuidanceConfig,
    GuidanceInputError,
    LassoCandidate,
    PrefixCost,
    RuntimePrefix,
    stable_digest,
)


def _cycle_signature(segment: list[RuntimePrefix], time_quantum_us: int) -> str:
    start_time = segment[0].time_us
    material = [
        {
            "location": row.automaton_location,
            "zone": row.zone_signature,
            "property_state": row.property_state_digest,
            "event": row.event_label,
            "transition": row.transition_id,
            "accepting": row.accepting,
            "relative_time_bucket":
                (row.time_us - start_time) // time_quantum_us,
        }
        for row in segment
    ]
    return stable_digest(material)


def _find_lassos(
    rows: list[RuntimePrefix], minimum_time_us: int, time_quantum_us: int
) -> list[LassoCandidate]:
    seen: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    candidates: list[LassoCandidate] = []
    for end, row in enumerate(rows):
        previous = seen[row.recurrence_key]
        for start in reversed(previous):
            segment = rows[start : end + 1]
            duration = row.time_us - rows[start].time_us
            accepting_visits = sum(item.accepting for item in segment)
            if duration < minimum_time_us:
                continue
            if accepting_visits == 0:
                continue
            if not all(item.accepting_fixpoint for item in segment):
                continue
            if end == start:
                continue
            candidates.append(
                LassoCandidate(
                    run_id=row.run_id,
                    seed_id=row.seed_id,
                    start_prefix=rows[start].prefix_index,
                    end_prefix=row.prefix_index,
                    duration_us=duration,
                    signature=_cycle_signature(segment, time_quantum_us),
                    accepting_visits=accepting_visits,
                )
            )
            # Prefer the shortest witnessed recurrence ending at this prefix.
            break
        previous.append(end)
    return candidates


def _mutation_score(candidate: Mapping[str, Any]) -> float:
    try:
        static = float(candidate.get("static_relevance", 0.0))
        dynamic = float(candidate.get("dynamic_effect", 0.0))
    except (TypeError, ValueError) as error:
        raise GuidanceInputError(
            "mutation static_relevance and dynamic_effect must be numeric"
        ) from error
    if not 0.0 <= static <= 1.0 or not 0.0 <= dynamic <= 1.0:
        raise GuidanceInputError("mutation scores must be within [0, 1]")
    direction = 1.0 if candidate.get("direction_match") is True else 0.0
    reversible = 1.0 if candidate.get("reversible") is True else 0.0
    status = str(candidate.get("dynamic_status", "INCONCLUSIVE"))
    status_factor = {
        "CONFIRMED_EFFECT": 1.0,
        "INCONCLUSIVE": 0.35,
        "NO_OBSERVED_EFFECT": 0.0,
    }.get(status, 0.0)
    return round(
        0.40 * static
        + 0.35 * dynamic * status_factor
        + 0.15 * direction
        + 0.10 * reversible,
        6,
    )


def _rank_mutations(
    edge_key: str | None, config: GuidanceConfig
) -> list[dict[str, Any]]:
    if edge_key is None:
        return []
    raw = config.edge_mutations.get(edge_key, [])
    if not isinstance(raw, list):
        raise GuidanceInputError(f"edge_mutations[{edge_key!r}] must be a list")
    ranked = []
    for candidate in raw:
        if not isinstance(candidate, Mapping):
            raise GuidanceInputError("each mutation candidate must be an object")
        if not isinstance(candidate.get("input_id"), str):
            raise GuidanceInputError("mutation input_id must be a string")
        item = dict(candidate)
        item["ranking_score"] = _mutation_score(candidate)
        ranked.append(item)
    ranked.sort(key=lambda item: (-item["ranking_score"], item["input_id"]))
    return ranked


def _fraction_string(value: Fraction | None) -> str | None:
    if value is None:
        return None
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _validate_runtime_order(groups: Mapping[tuple[str, str], list[RuntimePrefix]]) -> None:
    for key, rows in groups.items():
        rows.sort(key=lambda row: row.prefix_index)
        indices = [row.prefix_index for row in rows]
        if len(indices) != len(set(indices)):
            raise GuidanceInputError(f"duplicate prefix_index in run/seed {key}")
        times = [row.time_us for row in rows]
        if times != sorted(times):
            raise GuidanceInputError(f"time_us is not monotonic in run/seed {key}")


def analyze(
    config: GuidanceConfig,
    runtime_rows: Iterable[RuntimePrefix],
    prefix_costs: Iterable[PrefixCost] = (),
) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[RuntimePrefix]] = defaultdict(list)
    for row in runtime_rows:
        groups[(row.run_id, row.seed_id)].append(row)
    if not groups:
        raise GuidanceInputError("runtime trace is empty")
    _validate_runtime_order(groups)

    costs = {row.prefix_index: row for row in prefix_costs}
    all_lassos: list[LassoCandidate] = []
    for rows in groups.values():
        all_lassos.extend(
            _find_lassos(
                rows, config.min_cycle_time_us, config.cycle_time_quantum_us
            )
        )

    replay_runs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for candidate in all_lassos:
        replay_runs[(candidate.seed_id, candidate.signature)].add(candidate.run_id)
    confirmed = {
        key
        for key, run_ids in replay_runs.items()
        if len(run_ids) >= config.replay_confirmations
    }

    lasso_by_end = {
        (candidate.run_id, candidate.seed_id, candidate.end_prefix): candidate
        for candidate in all_lassos
    }
    guidance: list[dict[str, Any]] = []
    seed_best: dict[str, dict[str, Any]] = {}

    for (run_id, seed_id), rows in sorted(groups.items()):
        previous_cost: Fraction | None = None
        for row in rows:
            raw_cost = costs.get(row.prefix_index)
            cost = (
                raw_cost
                if raw_cost is not None
                and raw_cost.status == "complete"
                and raw_cost.exact
                else None
            )
            progress = None
            if (
                cost is not None
                and cost.kind == "finite"
                and cost.value is not None
                and previous_cost is not None
            ):
                progress = previous_cost - cost.value
            if cost is not None and cost.kind == "finite" and cost.value is not None:
                previous_cost = cost.value

            candidate = lasso_by_end.get((run_id, seed_id, row.prefix_index))
            replay_confirmed = bool(
                candidate
                and (candidate.seed_id, candidate.signature) in confirmed
            )
            accepting_frontier = row.accepting or bool(
                cost and cost.kind == "finite" and cost.value == 0
            )

            if replay_confirmed:
                stage = "REPLAY_CONFIRMED_LASSO"
            elif candidate:
                stage = "LASSO_CANDIDATE"
            elif accepting_frontier:
                stage = "ACCEPTING_FRONTIER"
            elif progress is not None and progress > 0:
                stage = "PREFIX_PROGRESS"
            else:
                stage = "NO_PROGRESS"

            if (
                config.property_kind == "FINITE_PREFIX"
                and row.monitor_verdict in {"NEGATIVE", "VIOLATED"}
            ):
                evidence_status = "FINITE_VIOLATION"
            elif replay_confirmed:
                evidence_status = "REPLAY_CONFIRMED_LASSO"
            elif candidate:
                evidence_status = "LASSO_CANDIDATE"
            elif accepting_frontier:
                evidence_status = "ACCEPTING_FRONTIER_ONLY"
            else:
                evidence_status = "INCONCLUSIVE"

            score = 0.0
            if progress is not None and progress > 0:
                score += 20.0 + min(20.0, float(progress))
            if cost is not None and cost.value is not None and cost.value >= 0:
                score += 10.0 / (1.0 + float(cost.value))
            if accepting_frontier:
                score += 30.0
            if candidate:
                score += 50.0
            if replay_confirmed:
                score += 30.0

            mutations = _rank_mutations(
                cost.next_edge_key if cost is not None else None, config
            )
            record = {
                "schema_version": 1,
                "property_id": config.property_id,
                "property_kind": config.property_kind,
                "run_id": run_id,
                "seed_id": seed_id,
                "prefix_index": row.prefix_index,
                "time_us": row.time_us,
                "stage": stage,
                "evidence_status": evidence_status,
                "accepting": row.accepting,
                "accepting_fixpoint": row.accepting_fixpoint,
                "cost_to_accepting_frontier": _fraction_string(
                    cost.value if cost is not None else None
                ),
                "cost_exact": cost.exact if cost is not None else False,
                "cost_progress": _fraction_string(progress),
                "next_edge_key": cost.next_edge_key if cost is not None else None,
                "priority_score": round(score, 6),
                "mutation_recommendations": mutations,
                "lasso": None,
            }
            if candidate:
                record["lasso"] = {
                    "start_prefix": candidate.start_prefix,
                    "end_prefix": candidate.end_prefix,
                    "duration_us": candidate.duration_us,
                    "accepting_visits": candidate.accepting_visits,
                    "cycle_signature": candidate.signature,
                    "distinct_replay_runs": len(
                        replay_runs[(candidate.seed_id, candidate.signature)]
                    ),
                }
            guidance.append(record)
            best = seed_best.get(seed_id)
            if best is None or record["priority_score"] > best["priority_score"]:
                seed_best[seed_id] = {
                    "seed_id": seed_id,
                    "priority_score": record["priority_score"],
                    "best_stage": stage,
                    "best_run_id": run_id,
                    "best_prefix_index": row.prefix_index,
                    "evidence_status": evidence_status,
                }

    seed_ranking = sorted(
        seed_best.values(), key=lambda item: (-item["priority_score"], item["seed_id"])
    )
    return {
        "schema_version": 1,
        "property_id": config.property_id,
        "property_kind": config.property_kind,
        "guidance": guidance,
        "lasso_candidates": [
            {
                "run_id": item.run_id,
                "seed_id": item.seed_id,
                "start_prefix": item.start_prefix,
                "end_prefix": item.end_prefix,
                "duration_us": item.duration_us,
                "accepting_visits": item.accepting_visits,
                "cycle_signature": item.signature,
                "distinct_replay_runs": len(
                    replay_runs[(item.seed_id, item.signature)]
                ),
                "replay_confirmed": (
                    item.seed_id,
                    item.signature,
                ) in confirmed,
            }
            for item in all_lassos
        ],
        "seed_ranking": seed_ranking,
        "claim_limit": (
            "FINITE_PREFIX may emit FINITE_VIOLATION from a terminal monitor verdict; "
            "UNBOUNDED_LIVENESS emits only finite lasso evidence for fuzz guidance."
        ),
    }
