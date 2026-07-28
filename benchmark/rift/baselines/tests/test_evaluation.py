#!/usr/bin/env python3
"""Regression tests for the M3 sanitized-input and private-evaluation contracts."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

TEST_ROOT = Path(__file__).resolve().parent
BASELINE_ROOT = TEST_ROOT.parent
WORKSPACE = BASELINE_ROOT.parents[2]
GOLD_ROOT = WORKSPACE / "benchmark" / "rift" / "gold"
sys.path.insert(0, str(BASELINE_ROOT))

import evaluate  # noqa: E402
import no_answer_leakage  # noqa: E402
import prepare_inputs  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class EvaluationContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rift-m3-tests-", dir="/tmp")
        cls.root = Path(cls.temporary.name)
        cls.sanitized = cls.root / "sanitized-a"
        cls.sanitized_b = cls.root / "sanitized-b"
        prepare_inputs.prepare(GOLD_ROOT, cls.sanitized)
        prepare_inputs.prepare(GOLD_ROOT, cls.sanitized_b)
        cls.input_path = cls.sanitized / "analyzer_input.json"
        cls.result_path = cls.sanitized / "dummy_result.json"
        cls.report_path = cls.root / "dummy_evaluation.json"
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            [
                sys.executable,
                str(TEST_ROOT / "dummy_no_influence.py"),
                "--input",
                str(cls.input_path),
                "--output",
                str(cls.result_path),
            ],
            cwd=WORKSPACE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cls.report = evaluate.evaluate(cls.input_path, cls.result_path, GOLD_ROOT)
        write_json(cls.report_path, cls.report)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_schema_and_track_boundary(self) -> None:
        analyzer_input = read_json(self.input_path)
        result = read_json(self.result_path)
        evaluate.validate_schema(
            analyzer_input, BASELINE_ROOT / "analyzer_input.schema.json", "input"
        )
        evaluate.validate_schema(
            result, BASELINE_ROOT / "baseline_result.schema.json", "result"
        )
        self.assertEqual(analyzer_input["evaluation_track"], "PAIR_CLASSIFICATION_DIAGNOSTIC")
        self.assertEqual(
            analyzer_input["binding_mode"], "GIVEN_CANDIDATE_ANCHORS_NOT_SCORED"
        )
        self.assertEqual(
            analyzer_input["controllability_mode"],
            "GIVEN_CONTROLLABILITY_NOT_SCORED",
        )

    def test_preparation_is_byte_deterministic_across_output_roots(self) -> None:
        def snapshot(root: Path) -> dict[str, bytes]:
            return {
                str(path.relative_to(root)): path.read_bytes()
                for path in sorted(root.rglob("*"))
                if path.is_file() and path.name != "dummy_result.json"
            }

        self.assertEqual(snapshot(self.sanitized), snapshot(self.sanitized_b))

    def test_sanitized_tree_is_opaque_and_markers_remain(self) -> None:
        scan = no_answer_leakage.scan_roots([self.sanitized_b])
        self.assertEqual(scan["status"], "PASS", scan["violations"])
        manifest = read_json(self.sanitized_b / "analyzer_input.json")
        self.assertEqual(len(manifest["cases"]), 120)
        self.assertEqual(
            sum(len(case["source_anchors"]) for case in manifest["cases"]), 189
        )
        self.assertEqual(sum(len(case["ap_anchors"]) for case in manifest["cases"]), 130)
        for case in manifest["cases"]:
            self.assertRegex(case["case_id"], r"^case_[0-9]{3}$")
            text = (self.sanitized_b / case["source"]["file"]).read_text(encoding="utf-8")
            self.assertIn("RIFT_SOURCE:", text)
            self.assertIn("RIFT_AP:", text)

    def test_dummy_no_influence_metrics(self) -> None:
        overall = self.report["overall"]
        classification = overall["classification"]
        influence = overall["influence"]
        actionable = overall["actionable_derived"]
        self.assertEqual(self.report["evidence_identity"]["pair_count"], 202)
        self.assertEqual(classification["exact"], 52)
        self.assertAlmostEqual(classification["exact_accuracy_unknown_is_wrong"], 52 / 202)
        self.assertEqual(
            (influence["tp"], influence["fp"], influence["fn"], influence["tn"]),
            (0, 0, 150, 52),
        )
        self.assertIsNone(influence["precision"])
        self.assertEqual(influence["recall"], 0.0)
        self.assertEqual(overall["must"]["gold_must"], 66)
        self.assertEqual(overall["must"]["detection_recall"], 0.0)
        self.assertEqual(
            (actionable["tp"], actionable["fp"], actionable["fn"], actionable["tn"]),
            (0, 0, 143, 59),
        )
        self.assertEqual(overall["edges"]["primary_pair_edge_kind"]["gold"], 314)
        exact_edges = overall["edges"]["unprojected_exact_endpoint_diagnostic"]
        self.assertEqual(exact_edges["status"], "UNPROJECTED_DIAGNOSTIC_NOT_HEADLINE")
        self.assertEqual(exact_edges["gold"], 373)
        self.assertEqual(overall["edges"]["by_kind"]["return"]["gold"], 0)
        self.assertEqual(
            overall["edges"]["by_kind"]["return"]["status"],
            "NOT_PRESENT_IN_GOLD",
        )

    def test_unknown_is_not_no_or_true_negative(self) -> None:
        unknown = copy.deepcopy(read_json(self.result_path))
        unknown["analysis_status"] = "UNSUPPORTED"
        unknown["execution"]["analyzed_units"] = 0
        for case in unknown["cases"]:
            case["status"] = "UNSUPPORTED"
            for prediction in case["predictions"]:
                prediction["prediction"] = "UNKNOWN"
                prediction["status"] = "UNSUPPORTED"
                prediction["edges"] = []
        path = self.root / "all_unknown.json"
        write_json(path, unknown)
        report = evaluate.evaluate(self.input_path, path, GOLD_ROOT)
        influence = report["overall"]["influence"]
        self.assertEqual((influence["tp"], influence["fp"], influence["fn"]), (0, 0, 150))
        self.assertEqual(influence["tn"], 0)
        self.assertEqual(influence["unknown_on_negative"], 52)
        self.assertEqual(report["overall"]["classification"]["exact"], 0)
        self.assertEqual(report["overall"]["unsupported"]["unknown_pairs"], 202)

    def test_missing_matrix_pair_is_rejected(self) -> None:
        incomplete = copy.deepcopy(read_json(self.result_path))
        incomplete["cases"][0]["predictions"].pop()
        path = self.root / "incomplete.json"
        write_json(path, incomplete)
        with self.assertRaisesRegex(evaluate.EvaluationError, "full source×AP cross product"):
            evaluate.evaluate(self.input_path, path, GOLD_ROOT)

    def test_static_leakage_scan_rejects_private_literals(self) -> None:
        bad = self.root / "bad_analyzer.py"
        bad.write_text(
            "PRIVATE = 'RIFT-GOLD-001 benchmark/rift/gold/ground_truth'\n",
            encoding="utf-8",
        )
        report = no_answer_leakage.scan_roots([bad])
        self.assertEqual(report["status"], "FAIL")
        self.assertGreaterEqual(len(report["violations"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
