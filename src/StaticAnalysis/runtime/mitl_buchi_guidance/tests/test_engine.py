from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

MODULE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(MODULE_ROOT))

from tafuzz_buchi_guidance.engine import analyze  # noqa: E402
from tafuzz_buchi_guidance.model import (  # noqa: E402
    GuidanceConfig,
    GuidanceInputError,
    PrefixCost,
    RuntimePrefix,
)


def config(kind: str = "UNBOUNDED_LIVENESS", confirmations: int = 2):
    return GuidanceConfig.from_json(
        {
            "property_id": "TEST.P1",
            "property_kind": kind,
            "zone_signature_contract": "PROPERTY_CLOCKS_ONLY",
            "state_projection_fields": ["mode", "armed", "altitude_bucket"],
            "min_cycle_time_us": 1_000,
            "cycle_time_quantum_us": 100,
            "replay_confirmations": confirmations,
            "edge_mutations": {
                "0:0": [
                    {
                        "input_id": "INPUT_C:Flight_Mode_RTL",
                        "static_relevance": 1.0,
                        "dynamic_effect": 0.8,
                        "dynamic_status": "CONFIRMED_EFFECT",
                        "direction_match": True,
                        "reversible": True,
                    },
                    {
                        "input_id": "INPUT_P:UNRELATED",
                        "static_relevance": 0.2,
                        "dynamic_effect": 0.9,
                        "dynamic_status": "NO_OBSERVED_EFFECT",
                        "direction_match": False,
                        "reversible": True,
                    },
                ]
            },
        }
    )


def row(
    run: str,
    prefix: int,
    time_us: int,
    location: int,
    zone: str,
    mode: str,
    accepting: bool = False,
    verdict: str = "INCONCLUSIVE",
):
    return RuntimePrefix.from_json(
        {
            "run_id": run,
            "seed_id": "seed-a",
            "prefix_index": prefix,
            "time_us": time_us,
            "automaton_location": location,
            "zone_signature": zone,
            "accepting": accepting,
            "accepting_fixpoint": True,
            "property_state": {
                "mode": mode,
                "armed": True,
                "altitude_bucket": 10,
                "ignored_absolute_clock": time_us,
            },
            "event_label": f"e{prefix}",
            "transition_id": f"t{prefix}",
            "monitor_verdict": verdict,
        },
        ["mode", "armed", "altitude_bucket"],
    )


def lasso_run(run: str):
    return [
        row(run, 0, 0, 0, "z0", "LOITER"),
        row(run, 1, 1_000, 1, "z1", "RTL", accepting=True),
        row(run, 2, 3_000, 0, "z0", "LOITER"),
    ]


def cost(prefix: int, value: str, edge=(0, 0)):
    return PrefixCost.from_json(
        {
            "prefix_index": prefix,
            "domain_status": "complete",
            "aggregate": {
                "kind": "finite",
                "value": value,
                "exact": True,
                "next_edge": (
                    {"source": edge[0], "ordinal": edge[1]}
                    if edge is not None
                    else None
                ),
            },
        }
    )


class GuidanceTests(unittest.TestCase):
    def test_accepting_state_alone_is_not_a_lasso(self) -> None:
        result = analyze(config(), lasso_run("run-1")[:2])
        self.assertEqual(result["lasso_candidates"], [])
        self.assertEqual(
            result["guidance"][-1]["evidence_status"],
            "ACCEPTING_FRONTIER_ONLY",
        )

    def test_positive_time_accepting_recurrence_is_lasso_candidate(self) -> None:
        result = analyze(config(confirmations=2), lasso_run("run-1"))
        self.assertEqual(len(result["lasso_candidates"]), 1)
        candidate = result["lasso_candidates"][0]
        self.assertEqual(candidate["duration_us"], 3_000)
        self.assertFalse(candidate["replay_confirmed"])
        self.assertEqual(result["guidance"][-1]["stage"], "LASSO_CANDIDATE")

    def test_zero_time_recurrence_is_rejected(self) -> None:
        rows = [
            row("run-1", 0, 0, 0, "z0", "LOITER", accepting=True),
            row("run-1", 1, 0, 0, "z0", "LOITER", accepting=True),
        ]
        result = analyze(config(), rows)
        self.assertEqual(result["lasso_candidates"], [])

    def test_distinct_clean_replays_confirm_same_lasso_signature(self) -> None:
        result = analyze(config(confirmations=2), lasso_run("run-1") + lasso_run("run-2"))
        self.assertEqual(len(result["lasso_candidates"]), 2)
        self.assertTrue(all(item["replay_confirmed"] for item in result["lasso_candidates"]))
        confirmed = [
            item for item in result["guidance"]
            if item["stage"] == "REPLAY_CONFIRMED_LASSO"
        ]
        self.assertEqual(len(confirmed), 2)

    def test_different_timed_schedule_is_not_replay_confirmation(self) -> None:
        second = [
            row("run-2", 0, 0, 0, "z0", "LOITER"),
            row("run-2", 1, 1_000, 1, "z1", "RTL", accepting=True),
            row("run-2", 2, 3_200, 0, "z0", "LOITER"),
        ]
        result = analyze(config(confirmations=2), lasso_run("run-1") + second)
        self.assertTrue(
            all(not item["replay_confirmed"] for item in result["lasso_candidates"])
        )

    def test_unbounded_negative_prefix_is_not_promoted_to_finite_violation(self) -> None:
        runtime = [row("run-1", 0, 0, 0, "z0", "LOITER", verdict="NEGATIVE")]
        result = analyze(config("UNBOUNDED_LIVENESS"), runtime)
        self.assertEqual(result["guidance"][0]["evidence_status"], "INCONCLUSIVE")

    def test_finite_monitor_terminal_verdict_is_a_finite_violation(self) -> None:
        runtime = [row("run-1", 0, 0, 0, "z0", "LOITER", verdict="NEGATIVE")]
        result = analyze(config("FINITE_PREFIX"), runtime)
        self.assertEqual(result["guidance"][0]["evidence_status"], "FINITE_VIOLATION")

    def test_cost_progress_and_mutation_ranking(self) -> None:
        result = analyze(
            config(),
            lasso_run("run-1"),
            [cost(0, "5"), cost(1, "2", edge=(1, 1)), cost(2, "0", edge=None)],
        )
        first = result["guidance"][0]
        second = result["guidance"][1]
        self.assertEqual(first["mutation_recommendations"][0]["input_id"], "INPUT_C:Flight_Mode_RTL")
        self.assertEqual(second["cost_progress"], "3")

    def test_incomplete_or_inexact_cost_never_guides(self) -> None:
        untrusted = PrefixCost.from_json(
            {
                "prefix_index": 0,
                "domain_status": "incomplete_timeout",
                "aggregate": {
                    "kind": "finite",
                    "value": "0",
                    "exact": False,
                    "next_edge": {"source": 0, "ordinal": 0},
                },
            }
        )
        result = analyze(config(), lasso_run("run-1")[:1], [untrusted])
        item = result["guidance"][0]
        self.assertEqual(item["stage"], "NO_PROGRESS")
        self.assertIsNone(item["cost_to_accepting_frontier"])
        self.assertEqual(item["mutation_recommendations"], [])

    def test_projection_ignores_absolute_clock(self) -> None:
        first = row("run-1", 0, 0, 0, "z0", "LOITER")
        second = row("run-1", 1, 3_000, 0, "z0", "LOITER", accepting=True)
        self.assertEqual(first.property_state_digest, second.property_state_digest)

    def test_wrong_zone_contract_fails_closed(self) -> None:
        with self.assertRaises(GuidanceInputError):
            GuidanceConfig.from_json(
                {
                    "property_id": "P",
                    "property_kind": "UNBOUNDED_LIVENESS",
                    "zone_signature_contract": "INCLUDES_GLOBAL_CLOCK",
                    "state_projection_fields": ["mode"],
                    "min_cycle_time_us": 1,
                    "cycle_time_quantum_us": 1,
                    "replay_confirmations": 2,
                }
            )

    def test_current_pta_prefix_output_is_consumed_without_rewrite(self) -> None:
        path = PROJECT_ROOT / (
            "test/TARV/results/pta_prefix_mighty_cost3_z3_20260712-042251/"
            "pta_prefix_costs.jsonl"
        )
        parsed = [
            PrefixCost.from_json(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual([item.value for item in parsed[:5]], [8, 5, 4, 2, 0])
        result = analyze(config(), lasso_run("run-1"), parsed)
        self.assertEqual(result["guidance"][1]["cost_progress"], "3")


if __name__ == "__main__":
    unittest.main()
