from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADAPTER_ROOT))

from tafuzz_pgfuzz.engine import TrialRunner, plan_work_items, run_experiment  # noqa: E402


class EnginePlanningTests(unittest.TestCase):
    def test_only_ready_safe_inputs_are_planned(self) -> None:
        catalog = {"inputs": [
            {"input_id": "INPUT_P:P", "input_type": "INPUT_P", "name": "P",
             "execution_class": "READY_SAFE", "mutation_values": [0, 2],
             "current_value": 1, "transport": "PARAM_SET"},
            {"input_id": "INPUT_P:X", "input_type": "INPUT_P", "name": "X",
             "execution_class": "UNKNOWN_METADATA", "mutation_values": [2],
             "current_value": 1, "transport": "PARAM_SET"},
        ]}
        items = plan_work_items(catalog)
        self.assertEqual([item["mutation_value"] for item in items], [0, 2])
        self.assertTrue(all(item["input"]["name"] == "P" for item in items))

    def test_shards_are_disjoint_and_complete(self) -> None:
        catalog = {"inputs": [{
            "input_id": "INPUT_P:P", "input_type": "INPUT_P", "name": "P",
            "execution_class": "READY_SAFE", "mutation_values": list(range(7)),
            "current_value": 99, "transport": "PARAM_SET",
        }]}
        all_items = plan_work_items(catalog)
        left = plan_work_items(catalog, shard_index=0, shard_count=2)
        right = plan_work_items(catalog, shard_index=1, shard_count=2)
        self.assertFalse({x["work_id"] for x in left} & {x["work_id"] for x in right})
        self.assertEqual({x["work_id"] for x in all_items},
                         {x["work_id"] for x in left + right})

    def test_name_filter_is_exact(self) -> None:
        catalog = {"inputs": [
            {"input_id": f"INPUT_C:{name}", "input_type": "INPUT_C", "name": name,
             "execution_class": "READY_SAFE", "mutation_values": [1000],
             "current_value": 1500, "transport": "RC_CHANNELS_OVERRIDE"}
            for name in ["RC1", "RC10"]
        ]}
        items = plan_work_items(catalog, {"RC1"})
        self.assertEqual([item["input"]["name"] for item in items], ["RC1"])

    def test_unverified_recovery_fails_closed(self) -> None:
        class Runner(TrialRunner):
            def parameter_repetition(self, row, mutation, index):
                return {
                    "baseline": {"legacy_vector": [0.0] * 34},
                    "treatment": {"legacy_vector": [0.0] * 34},
                    "recovery": {"legacy_vector": [0.0] * 34},
                    "application": {"verified": True},
                    "restoration": {"verified": False},
                    "feature_effects": [],
                }

        item = {"work_id": "x", "mutation_value": 2, "input": {
            "input_type": "INPUT_P", "name": "P", "transport": "PARAM_SET",
            "execution_class": "READY_SAFE",
        }}
        result = Runner(Path("."), repetitions=1).run_item(item)
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["error"], "INPUT_RECOVERY_VERIFICATION_FAILED")
        self.assertFalse(result["recovery_verified_all_repetitions"])

    def test_dry_run_records_global_and_shard_counts_without_claiming_execution(self) -> None:
        catalog = {"inputs": [{
            "input_id": "INPUT_P:P", "input_type": "INPUT_P", "name": "P",
            "execution_class": "READY_SAFE", "mutation_values": [0, 2, 3],
            "current_value": 1, "transport": "PARAM_SET",
        }]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input_catalog.json").write_text(
                json.dumps(catalog), encoding="utf-8")
            (root / "manifest.json").write_text(
                json.dumps({"schema_version": "1.0"}), encoding="utf-8")
            result = run_experiment(root, None, 0, 2, 3, 2.0, True, False)
            self.assertEqual(result["plan"]["global_work_item_count"], 3)
            self.assertEqual(result["plan"]["work_item_count"], 2)
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertFalse(manifest["dynamic_inputs_executed"])
            self.assertFalse(manifest["full_campaign_complete"])
            self.assertEqual(len((root / "experiment_plans.jsonl").read_text().splitlines()), 1)

    def test_runner_continues_session_number_across_resume_invocations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sessions/session-0000").mkdir(parents=True)
            (root / "sessions/session-0004").mkdir()
            self.assertEqual(TrialRunner(root).restart_count, 5)


if __name__ == "__main__":
    unittest.main()
