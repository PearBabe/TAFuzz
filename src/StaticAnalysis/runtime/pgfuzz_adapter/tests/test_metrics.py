from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import sys


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADAPTER_ROOT))

from tafuzz_pgfuzz.compat import regenerate_result_files  # noqa: E402
from tafuzz_pgfuzz.metrics import aggregate_effects, legacy_groups  # noqa: E402
from tafuzz_pgfuzz.states import StateWindow  # noqa: E402


def repetition(base: list[float], treatment: list[float], recovery: list[float],
               status: str = "TRIAL_EFFECT", direction: str = "INCREASE"):
    vector = [0.0] * 34
    input_vector = [0.0] * 34
    input_vector[0] = 2.0
    return {
        "baseline": {"legacy_vector": vector},
        "treatment": {"legacy_vector": input_vector},
        "recovery": {"legacy_vector": vector},
        "feature_effects": [{
            "feature": "rc.chan1_raw", "result_group": "roll",
            "trial_status": status, "direction": direction,
        }],
    }


class MetricsTests(unittest.TestCase):
    def test_state_window_always_builds_34_legacy_values(self) -> None:
        window = StateWindow("EMPTY")
        self.assertEqual(len(window.legacy_vector()), 34)
        self.assertEqual(window.summary()["onboard_time_ranges"], {})

    def test_exact_legacy_rule(self) -> None:
        baseline = [[0.0] * 34]
        treatment = [[0.0] * 34]
        treatment[0][0] = 0.00002
        groups, details = legacy_groups(baseline, treatment)
        self.assertIn("roll", groups)
        self.assertTrue(details[0]["matched"])
        treatment[0][0] = 0.000001
        groups, _ = legacy_groups(baseline, treatment)
        self.assertNotIn("roll", groups)

    def test_two_consistent_repetitions_confirm_effect(self) -> None:
        effect = aggregate_effects("RC1", [repetition([], [], []), repetition([], [], [])])
        self.assertEqual(effect["status"], "CONFIRMED_EFFECT")
        self.assertEqual(effect["confirmed_groups"], ["roll"])

    def test_inconsistent_direction_is_not_confirmed(self) -> None:
        effect = aggregate_effects("RC1", [
            repetition([], [], [], direction="INCREASE"),
            repetition([], [], [], direction="DECREASE"),
            repetition([], [], [], status="NO_TRIAL_EFFECT"),
        ])
        self.assertNotIn("roll", effect["confirmed_groups"])

    def test_compatibility_writer_keeps_rc1_and_rc10(self) -> None:
        effects = [
            {"input_name": "RC1", "confirmed_groups": ["roll"], "legacy_groups": []},
            {"input_name": "RC10", "confirmed_groups": ["roll"], "legacy_groups": ["roll"]},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            regenerate_result_files(root, effects)
            self.assertEqual((root / "results/roll.txt").read_text(encoding="utf-8"),
                             "RC1\nRC10\n")
            self.assertEqual((root / "results_legacy/roll.txt").read_text(encoding="utf-8"),
                             "RC10\n")
            self.assertTrue((root / "results/GPS.txt").exists())


if __name__ == "__main__":
    unittest.main()
