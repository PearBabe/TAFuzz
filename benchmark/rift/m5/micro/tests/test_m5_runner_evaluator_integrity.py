#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr


MICRO = pathlib.Path(__file__).resolve().parents[1]
WORKSPACE = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(MICRO))


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_module("run_m5_all", MICRO / "run_m5_all.py")
EVALUATOR = load_module("rift_m5_integrity_evaluator", MICRO / "evaluate_m5.py")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunnerIsolationTests(unittest.TestCase):
    def test_fixed_artifact_inventory_includes_occurrence_bindings(self) -> None:
        self.assertIn("predicate_occurrence_bindings.json", RUNNER.ARTIFACT_NAMES)

    def test_empty_root_hides_host_oracle_results_other_cases_tmp_and_environment(self) -> None:
        sandbox = pathlib.Path("/usr/bin/bwrap")
        self.assertTrue(sandbox.is_file())
        with tempfile.TemporaryDirectory(prefix="rift-m5-sandbox-negative-") as directory:
            root = pathlib.Path(directory)
            allowed = root / "case_001.c"
            other_case = root / "case_002.c"
            sibling_result = root / "other_case_result.json"
            output = root / "current_case"
            allowed.write_text("allowed\n", encoding="utf-8")
            other_case.write_text("forbidden\n", encoding="utf-8")
            sibling_result.write_text("forbidden\n", encoding="utf-8")
            output.mkdir()
            descriptor, temporary_name = tempfile.mkstemp(prefix="rift-m5-host-tmp-")
            os.write(descriptor, b"forbidden\n")
            os.close(descriptor)
            host_tmp = pathlib.Path(temporary_name)
            marker = output / "marker.txt"
            prior_evaluation = (
                WORKSPACE / "benchmark/rift/m4/results/micro_final_evaluation.json"
            )
            script = """
import os, pathlib, sys
allowed = pathlib.Path(sys.argv[1])
marker = pathlib.Path(sys.argv[2])
denied = [pathlib.Path(value) for value in sys.argv[3:]]
assert allowed.read_text() == 'allowed\\n'
assert 'RIFT_ORACLE_CANARY' not in os.environ
assert not any(path.exists() for path in denied), denied
marker.write_text('PASS\\n')
"""
            command = RUNNER.sandbox_argv(
                sandbox,
                [
                    "/usr/bin/python3",
                    "-I",
                    "-c",
                    script,
                    str(allowed),
                    str(marker),
                    str(other_case),
                    str(sibling_result),
                    str(host_tmp),
                    str(prior_evaluation),
                    str(WORKSPACE / "benchmark/rift/gold/manifest.json"),
                ],
                output,
                output,
                (allowed,),
            )
            try:
                completed = subprocess.run(
                    command,
                    env={
                        "PATH": "/usr/bin:/bin",
                        "LANG": "C.UTF-8",
                        "LC_ALL": "C.UTF-8",
                        "RIFT_ORACLE_CANARY": "must-be-scrubbed",
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                )
            finally:
                host_tmp.unlink(missing_ok=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("PASS\n", marker.read_text(encoding="utf-8"))

    def test_runner_canary_self_test_passes_with_exact_mounts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-self-test-") as directory:
            root = pathlib.Path(directory)
            analyzer = root / "tafuzz-sa"
            first_source = root / "case_001.c"
            other_source = root / "case_002.c"
            analyzer.write_bytes(b"analyzer snapshot\n")
            first_source.write_text("first\n", encoding="utf-8")
            other_source.write_text("other\n", encoding="utf-8")
            result = root / "result"
            result.mkdir()
            report = RUNNER.run_sandbox_self_test(
                sandbox=pathlib.Path("/usr/bin/bwrap"),
                analyzer=analyzer,
                first_record={"source": first_source},
                other_record={"source": other_source},
                result_root=result,
                oracle_root=WORKSPACE / "benchmark/rift/gold",
            )
            self.assertEqual("PASS", report["status"])
            self.assertEqual(5, report["checked_denied_path_count"])


class EvaluatorSealTests(unittest.TestCase):
    def test_absolute_parent_and_symlink_escape_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-path-negative-") as directory:
            root = pathlib.Path(directory)
            result = root / "result"
            outside = root / "outside.json"
            result.mkdir()
            outside.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(RUNNER.RunError):
                EVALUATOR.strict_result_path(result, str(outside))
            with self.assertRaises(RUNNER.RunError):
                EVALUATOR.strict_result_path(result, "../outside.json")
            (result / "link.json").symlink_to(outside)
            with self.assertRaises(RUNNER.RunError):
                EVALUATOR.strict_result_path(result, "link.json")

    def test_formal_evaluation_requires_external_manifest_commitment_before_gold(self) -> None:
        absent = pathlib.Path("/definitely/not/opened/private-gold")
        with self.assertRaisesRegex(RUNNER.RunError, "requires"):
            EVALUATOR.evaluate(
                pathlib.Path("/not/read/result"),
                pathlib.Path("/not/read/frozen"),
                pathlib.Path("/not/read/enriched"),
                absent,
                120,
                None,
                True,
            )

    def test_external_manifest_digest_is_checked_before_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-external-seal-") as directory:
            root = pathlib.Path(directory)
            result = root / "result"
            frozen = root / "frozen"
            enriched = root / "enriched"
            result.mkdir()
            frozen.mkdir()
            enriched.mkdir()
            (result / "run_manifest.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunError, "external commitment"):
                EVALUATOR.validate_sealed_run(
                    result, frozen, enriched, 1, "0" * 64
                )

    def test_frozen_verifier_is_rerun_and_fake_saved_pass_cannot_substitute(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-fake-pass-") as directory:
            root = pathlib.Path(directory)
            verifier = root / "verifier.py"
            schema = root / "schema"
            certificate = root / "certificate.json"
            schema.mkdir()
            certificate.write_text('{"not":"valid"}\n', encoding="utf-8")
            verifier.write_text(
                "import sys\nprint('trusted verifier rejects')\nsys.exit(7)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RUNNER.RunError, "frozen detached verifier failed"):
                EVALUATOR.rerun_detached_verifier(
                    case_id="case_001",
                    verifier=verifier,
                    schema_dir=schema,
                    certificate=certificate,
                    timeout_seconds=10,
                )

    def test_case_swap_property_digest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-case-swap-") as directory:
            root = pathlib.Path(directory)
            analyzer = root / "tafuzz-sa"
            model = root / "model.json"
            executor = root / "executor.json"
            for path, payload in (
                (analyzer, b"analyzer"),
                (model, b"model"),
                (executor, b"executor"),
            ):
                path.write_bytes(payload)
            public = {
                "property_ir_sha256": "a" * 64,
                "compile_database_sha256": "b" * 64,
                "source_sha256": "c" * 64,
                "compile_database_relative": "cases/case_001/compile_commands.json",
                "property_ir_relative": "cases/case_001/property_ir.json",
                "source_relative": "sources/case_001.c",
            }
            artifacts = {
                "m5_analysis_certificate": {
                    "analyzer": {
                        "binary_sha256": digest(analyzer),
                        "binary_path": str(analyzer.resolve()),
                    },
                    "m4_commitments": {
                        "typed_property_ir": {"sha256": "d" * 64}
                    },
                    "model_packs": [{"sha256": digest(model)}],
                    "executor_manifest": {"sha256": digest(executor)},
                },
                "analysis_certificate": {},
            }
            with self.assertRaisesRegex(RUNNER.RunError, "property digest"):
                EVALUATOR.certificate_input_closure(
                    case_id="case_001",
                    artifacts=artifacts,
                    public=public,
                    analyzer=analyzer.resolve(),
                    model_pack=model.resolve(),
                    executor=executor.resolve(),
                    result_root=root,
                )

    def test_descriptor_hash_and_size_are_both_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-descriptor-") as directory:
            root = pathlib.Path(directory)
            path = root / "cases/case_001/value.json"
            path.parent.mkdir(parents=True)
            path.write_text("{}\n", encoding="utf-8")
            descriptor = {
                "path": "cases/case_001/value.json",
                "sha256": digest(path),
                "byte_size": path.stat().st_size + 1,
            }
            with self.assertRaisesRegex(RUNNER.RunError, "byte size"):
                EVALUATOR.validate_file_descriptor(root, descriptor)


class PublicManifestClosureTests(unittest.TestCase):
    def test_current_frozen_and_enriched_manifests_close_for_all_cases(self) -> None:
        records = RUNNER.validate_public_inputs(
            WORKSPACE / "benchmark/rift/m4/micro/frozen",
            MICRO / "bundle",
            120,
        )
        self.assertEqual(120, len(records))
        self.assertEqual("case_001", records[0]["case_id"])
        self.assertEqual("case_120", records[-1]["case_id"])


class MetricCorrectnessTests(unittest.TestCase):
    def test_preregistered_gate_thresholds_are_inclusive_and_fail_below_boundary(self) -> None:
        at_boundary = {
            "gold_fuzzable_source_recall": {
                "recall_unknown_is_miss": 0.95,
                "tp": 95,
                "fn": 0,
                "unknown": 5,
                "gold_count": 100,
            },
            "critical_must_influencer_recall": {
                "recall_unknown_is_miss": 1.0,
                "tp": 48,
                "fn": 0,
                "unknown": 0,
                "gold_count": 48,
            },
            "supported_mutation_direction": {
                "end_to_end_accuracy_unknown_is_wrong": 0.90,
                "correct_count": 90,
                "supported_count": 100,
                "unknown_count": 10,
            },
        }
        passed = EVALUATOR.evaluate_preregistered_gates(at_boundary, enforce=True)
        self.assertEqual("PASS", passed["status"])
        below = json.loads(json.dumps(at_boundary))
        below["gold_fuzzable_source_recall"]["recall_unknown_is_miss"] = 0.949999
        failed = EVALUATOR.evaluate_preregistered_gates(below, enforce=True)
        self.assertEqual("GATE_FAIL", failed["status"])
        self.assertEqual(
            ["gold_fuzzable_source_recall"],
            [item["gate_id"] for item in failed["gates"] if not item["passed"]],
        )

    def test_unknown_directions_cannot_inflate_formal_accuracy(self) -> None:
        rows = [
            {
                "supported_direction": {
                    "label_status": "SUPPORTED_EXPRESSION",
                    "prediction_status": "PREDICTED",
                    "exact": True,
                }
            }
        ] + [
            {
                "supported_direction": {
                    "label_status": "SUPPORTED_EXPRESSION",
                    "prediction_status": "ABSTAIN_UNKNOWN_DIRECTION",
                    "exact": False,
                }
            }
            for _ in range(9)
        ]
        metric = EVALUATOR.supported_direction_summary(rows)
        self.assertEqual(1.0, metric["conditional_accuracy"])
        self.assertEqual(0.1, metric["coverage"])
        self.assertEqual(0.1, metric["end_to_end_accuracy_unknown_is_wrong"])
        self.assertEqual(1, metric["correct_count"])
        self.assertEqual(10, metric["supported_count"])
        self.assertEqual(9, metric["unknown_count"])

    def test_must_influencer_omission_and_unknown_are_separate_not_true_positive(self) -> None:
        rows = [
            {"gold_relation": "MUST_INFLUENCE", "influence_prediction": "INFLUENCE"},
            {"gold_relation": "MUST_INFLUENCE", "influence_prediction": "NO_INFLUENCE"},
            {"gold_relation": "MUST_INFLUENCE", "influence_prediction": "UNKNOWN"},
            {"gold_relation": "NO_INFLUENCE", "influence_prediction": "UNKNOWN"},
        ]
        metric = EVALUATOR.must_influencer_summary(rows)
        self.assertEqual(1, metric["tp"])
        self.assertEqual(1, metric["fn"])
        self.assertEqual(1, metric["unknown"])
        self.assertEqual(3, metric["gold_count"])
        self.assertEqual(1 / 3, metric["recall_unknown_is_miss"])
        self.assertEqual(0.5, metric["conditional_recall_on_decided"])

    def test_fuzzable_recall_keeps_unknown_out_of_fn_but_in_recall_denominator(self) -> None:
        rows = [
            {"gold_actionable": True, "prediction": "ACTIONABLE"},
            {"gold_actionable": True, "prediction": "NOT_ACTIONABLE"},
            {"gold_actionable": True, "prediction": "UNKNOWN"},
            {"gold_actionable": False, "prediction": "ACTIONABLE"},
        ]
        metric = EVALUATOR.fuzzable_source_recall_summary(rows)
        self.assertEqual(1, metric["tp"])
        self.assertEqual(1, metric["fn"])
        self.assertEqual(1, metric["unknown"])
        self.assertEqual(1 / 3, metric["recall_unknown_is_miss"])

    def test_development_mode_reports_failures_without_claiming_pass(self) -> None:
        failing = {
            "gold_fuzzable_source_recall": {"recall_unknown_is_miss": 0.0},
            "critical_must_influencer_recall": {"recall_unknown_is_miss": None},
            "supported_mutation_direction": {
                "end_to_end_accuracy_unknown_is_wrong": None
            },
        }
        gates = EVALUATOR.evaluate_preregistered_gates(failing, enforce=False)
        self.assertEqual("NOT_ENFORCED", gates["status"])
        self.assertEqual(3, gates["would_fail_count"])
        self.assertTrue(all(item["passed"] is False for item in gates["gates"]))
        self.assertEqual(
            "DEVELOPMENT_ONLY",
            EVALUATOR.evaluation_status(gates, development=True),
        )

    def test_formal_and_development_modes_cannot_be_combined(self) -> None:
        with self.assertRaisesRegex(RUNNER.RunError, "mutually exclusive"):
            EVALUATOR.resolve_evaluation_mode(formal=True, development=True)
        self.assertEqual(
            ("FORMAL", True),
            EVALUATOR.resolve_evaluation_mode(formal=True, development=False),
        )
        self.assertEqual(
            ("DEVELOPMENT", False),
            EVALUATOR.resolve_evaluation_mode(formal=False, development=True),
        )

    def test_cli_has_no_post_oracle_threshold_relaxation_switch(self) -> None:
        argv = [
            "--result-root",
            "/tmp/result",
            "--output",
            "/tmp/evaluation.json",
            "--formal",
            "--gold-fuzzable-source-recall-threshold",
            "0.0",
        ]
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            EVALUATOR.parse_args(argv)

    def test_joint_hyperedge_summary_reports_micro_f1_and_exact_separately(self) -> None:
        rows = [
            {
                "joint_action_set": {
                    "label_status": "LABELLED",
                    "prediction_state": "PREDICTED",
                    "gold_source_ids": ["left", "right"],
                    "predicted_source_ids": ["left", "extra"],
                    "exact": False,
                    "missing_source_ids": ["right"],
                    "extra_source_ids": ["extra"],
                }
            }
        ]
        metric = EVALUATOR.joint_metric_summary(rows)
        self.assertEqual(1, metric["micro_item_tp"])
        self.assertEqual(1, metric["micro_item_fp"])
        self.assertEqual(1, metric["micro_item_fn"])
        self.assertEqual(0.5, metric["micro_item_f1"])
        self.assertEqual(0.0, metric["end_to_end_exact_accuracy_abstention_is_wrong"])

    def test_prerequisite_sequence_summary_reports_exact_and_f1_not_only_presence(self) -> None:
        rows = [
            {
                "prerequisite_sequence": {
                    "label_status": "LABELLED_FREE_TEXT_SEQUENCE",
                    "prediction_status": "PREDICTED",
                    "gold_items": ["setup", "mode"],
                    "predicted_items": ["setup", "commit"],
                    "exact": False,
                }
            }
        ]
        metric = EVALUATOR.prerequisite_sequence_summary(rows)
        self.assertEqual(1, metric["micro_item_tp"])
        self.assertEqual(1, metric["micro_item_fp"])
        self.assertEqual(1, metric["micro_item_fn"])
        self.assertEqual(0.5, metric["micro_item_f1"])
        self.assertEqual(0, metric["exact_count"])

    def test_unknown_and_non_sat_recipes_are_abstentions(self) -> None:
        unknown = {"status": "UNKNOWN", "solver_query": {"outcome": "SAT"}}
        unsat = {"status": "SUPPORTED", "solver_query": {"outcome": "UNSAT"}}
        supported = {"status": "HEURISTIC", "solver_query": {"outcome": "SAT"}}
        self.assertEqual(
            (False, "ABSTAIN_RECIPE_STATUS_UNKNOWN"),
            EVALUATOR.effective_recipe(unknown),
        )
        self.assertEqual(
            (False, "ABSTAIN_SOLVER_UNSAT"), EVALUATOR.effective_recipe(unsat)
        )
        self.assertEqual((True, "PREDICTED"), EVALUATOR.effective_recipe(supported))

    def test_wrong_direction_is_not_exact(self) -> None:
        metric = EVALUATOR.categorical_recipe_metric(
            expected="monotone up",
            predicted=["MONOTONE_DOWN"],
            effective=True,
            free_text=True,
        )
        self.assertEqual("PREDICTED", metric["prediction_status"])
        self.assertFalse(metric["exact"])

    def test_overgenerated_values_lose_precision_and_exactness(self) -> None:
        metric = EVALUATOR.suggested_value_metric(
            {"0", "1"}, {"0", "1", "999"}, True, True
        )
        self.assertEqual(2 / 3, metric["precision"])
        self.assertEqual(1.0, metric["recall"])
        self.assertEqual(["999"], metric["extra"])
        self.assertTrue(metric["overgenerated"])
        self.assertFalse(metric["exact"])

    def test_widened_timing_is_abstention_and_wrong_structured_fields_are_not_scored(self) -> None:
        gold = {
            "relative_time_window": "labelled only as free text",
        }
        widened = {"timing": {"status": "WIDENED_UNKNOWN"}}
        widened_metric = EVALUATOR.timing_record(gold, widened, True)
        self.assertEqual("ABSTAIN_WIDENED_UNKNOWN", widened_metric["prediction_state"])
        exact_but_unlabelled = {
            "timing": {
                "status": "EXACT",
                "unit": "deliberately-wrong-unit",
                "lower": 999,
                "upper": 1000,
            }
        }
        exact_metric = EVALUATOR.timing_record(gold, exact_but_unlabelled, True)
        self.assertEqual("EXACT", exact_metric["prediction_state"])
        self.assertEqual("NOT_LABELLED", exact_metric["bounds_metric"]["status"])
        self.assertEqual(
            "NOT_LABELLED", exact_metric["structured_fields_metric"]["status"]
        )

    def test_reversed_prerequisite_dag_is_not_given_unlabelled_exact_credit(self) -> None:
        relation = {"preconditions": ["free text setup requirement"]}
        recipe = {
            "prerequisite_choices": [
                {
                    "alternatives": [
                        {
                            "status": "COMPLETE",
                            "steps": [
                                {
                                    "step_id": "second",
                                    "predecessor_step_ids": [],
                                },
                                {
                                    "step_id": "first",
                                    "predecessor_step_ids": ["second"],
                                },
                            ],
                        }
                    ]
                }
            ]
        }
        metric = EVALUATOR.prerequisite_record(relation, recipe, True)
        self.assertTrue(metric["predicted_presence"])
        self.assertEqual("NOT_LABELLED", metric["dag_edge_metric"]["status"])
        self.assertEqual("NOT_LABELLED", metric["alternative_exact_metric"]["status"])

    def test_wrong_payload_slot_is_reported_but_not_scored_without_gold(self) -> None:
        record = EVALUATOR.external_coordinate_record(
            ["action.a"],
            {
                "action.a": {
                    "channel": "process_argument",
                    "operation": "supply_integer",
                    "payload_slot": "wrong-slot",
                    "scope_schema": "process",
                    "generation_schema": "process",
                }
            },
            True,
        )
        self.assertEqual("NOT_LABELLED", record["label_status"])
        self.assertEqual("wrong-slot", record["predicted"][0]["payload_slot"])
        self.assertIsNone(record["exact"])

    def test_incomplete_extra_and_unknown_joint_predictions_are_not_exact(self) -> None:
        mapping = {
            "left": {"source_left"},
            "right": {"source_right"},
            "extra": {"source_extra"},
        }
        incomplete = EVALUATOR.joint_action_set_record(
            gold_joint_group={"source_left", "source_right"},
            action_ids=["left"],
            action_sources=mapping,
            claim="JOINT_REQUIRED",
            effective=True,
        )
        self.assertFalse(incomplete["exact"])
        self.assertEqual(["source_right"], incomplete["missing_source_ids"])
        extra = EVALUATOR.joint_action_set_record(
            gold_joint_group={"source_left", "source_right"},
            action_ids=["left", "right", "extra"],
            action_sources=mapping,
            claim="JOINT_REQUIRED",
            effective=True,
        )
        self.assertFalse(extra["exact"])
        self.assertEqual(["source_extra"], extra["extra_source_ids"])
        unknown = EVALUATOR.joint_action_set_record(
            gold_joint_group={"source_left", "source_right"},
            action_ids=["left", "right"],
            action_sources=mapping,
            claim="JOINT_UNKNOWN",
            effective=True,
        )
        self.assertEqual("ABSTAIN_JOINT_UNKNOWN", unknown["prediction_state"])
        self.assertFalse(unknown["exact"])

    def test_joint_recipe_scores_only_the_selected_candidates_mutation(self) -> None:
        private = {
            "case_id": "case_joint_action_filter",
            "category": "joint",
            "input_case": {"source": {"path": "sources/joint.c"}},
            "truth": {
                "sources": [
                    {
                        "id": "source_left",
                        "location": {"line": 10, "column": 9},
                        "fuzzable_frontier": True,
                    },
                    {
                        "id": "source_right",
                        "location": {"line": 20, "column": 9},
                        "fuzzable_frontier": True,
                    },
                ],
                "relations": [
                    {
                        "source_id": "source_left",
                        "ap_id": "ap_joint",
                        "relation": "MUST_INFLUENCE",
                        "joint_group": ["source_left", "source_right"],
                        "preconditions": [],
                        "mutation_recipe": {
                            "kind": "joint_boundary",
                            "direction": "monotone up",
                            "suggested_values": ["1"],
                        },
                    }
                ],
            },
        }
        artifacts = {
            "semantic_index": {
                "semantic_nodes": [
                    {
                        "node_id": "semantic-source-left",
                        "location": {
                            "file": "sources/joint.c",
                            "line": 10,
                            "column": 9,
                        },
                    },
                    {
                        "node_id": "semantic-boundary-left",
                        "location": {
                            "file": "sources/joint.c",
                            "line": 10,
                            "column": 20,
                        },
                    },
                    {
                        "node_id": "semantic-source-right",
                        "location": {
                            "file": "sources/joint.c",
                            "line": 20,
                            "column": 9,
                        },
                    },
                    {
                        "node_id": "semantic-boundary-right",
                        "location": {
                            "file": "sources/joint.c",
                            "line": 20,
                            "column": 20,
                        },
                    },
                ],
                "translation_units": [],
                "unsupported_constructs": [],
            },
            "contextual_influence_graph": {
                "nodes": [
                    {
                        "node_id": "ctx-source-left",
                        "semantic_node_ref": "semantic-source-left",
                        "location": {
                            "file": "sources/joint.c",
                            "line": 10,
                            "column": 9,
                        },
                    },
                    {
                        "node_id": "ctx-boundary-left",
                        "semantic_node_ref": "semantic-boundary-left",
                    },
                    {
                        "node_id": "ctx-source-right",
                        "semantic_node_ref": "semantic-source-right",
                        "location": {
                            "file": "sources/joint.c",
                            "line": 20,
                            "column": 9,
                        },
                    },
                    {
                        "node_id": "ctx-boundary-right",
                        "semantic_node_ref": "semantic-boundary-right",
                    },
                ],
                "edges": [
                    {
                        "source_node_id": "ctx-boundary-left",
                        "target_node_id": "ctx-source-left",
                    },
                    {
                        "source_node_id": "ctx-boundary-right",
                        "target_node_id": "ctx-source-right",
                    },
                ],
                "status": "COMPLETE",
                "unsupported_constructs": [],
            },
            "ap_bindings": {"bindings": [], "unsupported_constructs": []},
            "ap_influence_cones": {
                "cones": [
                    {
                        "ap_id": "ap_joint",
                        "status": "COMPLETE",
                        "members": [
                            {
                                "node_id": "ctx-source-left",
                                "membership": "MUST_INFLUENCE",
                            }
                        ],
                        "candidate_accounting": [],
                    }
                ],
                "unsupported_constructs": [],
            },
            "model_fact_overlay": {
                "boundary_attachments": [
                    {
                        "external_action_id": "action.left",
                        "semantic_node_id": "semantic-boundary-left",
                    },
                    {
                        "external_action_id": "action.right",
                        "semantic_node_id": "semantic-boundary-right",
                    },
                ]
            },
            "frontier_candidates": {
                "candidates": [
                    {
                        "candidate_id": "candidate.left",
                        "ap_id": "ap_joint",
                        "rank_tier": 1,
                        "disposition": "ACTIONABLE",
                        "action": {
                            "external_action_id": "action.left",
                            "channel": "process_argument",
                            "operation": "set_left",
                            "payload_slot": "left",
                            "scope_schema": "process",
                            "generation_schema": "process",
                        },
                    },
                    {
                        "candidate_id": "candidate.right",
                        "ap_id": "ap_joint",
                        "rank_tier": 1,
                        "disposition": "ACTIONABLE",
                        "action": {
                            "external_action_id": "action.right",
                            "channel": "process_argument",
                            "operation": "set_right",
                            "payload_slot": "right",
                            "scope_schema": "process",
                            "generation_schema": "process",
                        },
                    },
                ]
            },
            "mutation_recipes": {
                "recipes": [
                    {
                        "recipe_id": "recipe.joint",
                        "frontier_candidate_id": "candidate.left",
                        "status": "SUPPORTED",
                        "solver_query": {"outcome": "SAT"},
                        "action_hyperedge": {
                            "claim": "JOINT_REQUIRED",
                            "action_ids": ["action.left", "action.right"],
                        },
                        "action_mutations": [
                            {
                                "action_id": "action.left",
                                "mutation_kind": "THRESHOLD_CROSSING",
                                "direction": "MONOTONE_UP",
                                "suggested_values": [{"canonical": "1"}],
                            },
                            {
                                "action_id": "action.right",
                                "mutation_kind": "BOOLEAN_TOGGLE",
                                "direction": "MONOTONE_DOWN",
                                "suggested_values": [{"canonical": "999"}],
                            },
                        ],
                        "prerequisite_choices": [],
                        "timing": {"status": "UNKNOWN"},
                    }
                ]
            },
            "predicate_occurrence_bindings": {"selector_accounts": []},
        }

        row = EVALUATOR.relation_rows(private, artifacts)[0]

        self.assertEqual(["threshold_crossing"], row["mutation_kind"]["predicted"])
        self.assertEqual(["monotone_up"], row["mutation_direction"]["predicted"])
        self.assertEqual(["MONOTONE_UP"], row["supported_direction"]["predicted"])
        self.assertTrue(row["supported_direction"]["exact"])
        self.assertEqual(["1"], row["predicted_values"])
        self.assertEqual(["1"], row["suggested_value_metric"]["predicted"])
        self.assertTrue(row["suggested_value_metric"]["exact"])
        self.assertEqual(
            ["action.left"],
            [
                item["external_action_id"]
                for item in row["external_action_coordinate"]["predicted"]
            ],
        )
        self.assertEqual(
            ["source_left", "source_right"],
            row["joint_action_set"]["predicted_source_ids"],
        )
        self.assertTrue(row["joint_action_set"]["exact"])

    def test_abstention_is_not_true_positive_or_true_negative(self) -> None:
        rows = [
            {
                "feature": {
                    "presence_label_status": "LABELLED",
                    "gold_presence": True,
                    "prediction_state": "ABSTAIN_WIDENED_UNKNOWN",
                }
            },
            {
                "feature": {
                    "presence_label_status": "LABELLED",
                    "gold_presence": False,
                    "prediction_state": "ABSTAIN_UNKNOWN",
                }
            },
        ]
        summary = EVALUATOR.selective_presence_summary(
            rows, "feature", "EXACT", "NO_CONTRACT"
        )
        self.assertEqual(0, summary["tp"])
        self.assertEqual(0, summary["tn"])
        self.assertEqual(2, summary["abstention_count"])
        self.assertEqual(0.0, summary["coverage"])

    def test_semantic_anchor_join_beats_line_fallback(self) -> None:
        artifacts = {
            "semantic_index": {
                "semantic_nodes": [
                    {
                        "node_id": "source-node",
                        "location": {"file": "sources/case.c", "line": 10, "column": 9},
                    },
                    {
                        "node_id": "boundary-node",
                        "location": {
                            "file": "sources/case.c",
                            "line": 10,
                            "column": 25,
                            "end_line": 10,
                            "end_column": 40,
                        },
                    },
                    {
                        "node_id": "unrelated-boundary",
                        "location": {
                            "file": "sources/case.c",
                            "line": 10,
                            "column": 50,
                        },
                    },
                ]
            },
            "contextual_influence_graph": {
                "nodes": [
                    {"node_id": "ctx-source", "semantic_node_ref": "source-node"},
                    {"node_id": "ctx-boundary", "semantic_node_ref": "boundary-node"},
                    {"node_id": "ctx-other", "semantic_node_ref": "unrelated-boundary"},
                ],
                "edges": [
                    {"source_node_id": "ctx-boundary", "target_node_id": "ctx-source"}
                ],
            },
            "model_fact_overlay": {
                "boundary_attachments": [
                    {
                        "external_action_id": "correct-action",
                        "semantic_node_id": "boundary-node",
                    },
                    {
                        "external_action_id": "line-only-action",
                        "semantic_node_id": "unrelated-boundary",
                    },
                ]
            },
        }
        match = EVALUATOR.source_action_matches(
            artifacts, {"file": "sources/case.c", "line": 10, "column": 9}
        )
        self.assertEqual({"correct-action"}, match["action_ids"])
        self.assertEqual(["SEMANTIC_EDGE_TO_ANCHOR"], match["join_kinds"])
        self.assertFalse(match["used_coarse_fallback"])

    def test_semantic_artifact_determinism_comparison_detects_difference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-determinism-") as directory:
            root = pathlib.Path(directory)
            reference = root / "serial"
            current = root / "parallel"
            for run in (reference, current):
                case = run / "cases/case_001"
                case.mkdir(parents=True)
                for name in RUNNER.SEMANTIC_ARTIFACT_NAMES:
                    (case / name).write_text(f"{name}\n", encoding="utf-8")
            passed = RUNNER.compare_semantic_artifact_runs(
                reference, current, ["case_001"]
            )
            self.assertEqual("PASS", passed["status"])
            (current / "cases/case_001/mutation_recipes.json").write_text(
                "changed\n", encoding="utf-8"
            )
            failed = RUNNER.compare_semantic_artifact_runs(
                reference, current, ["case_001"]
            )
            self.assertEqual("FAIL", failed["status"])
            self.assertEqual(1, failed["mismatch_count"])

    def test_semantic_artifact_comparison_rejects_different_frozen_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-identity-") as directory:
            root = pathlib.Path(directory)
            reference = root / "serial"
            current = root / "parallel"
            for run, analyzer_sha in ((reference, "a" * 64), (current, "b" * 64)):
                case = run / "cases/case_001"
                case.mkdir(parents=True)
                for name in RUNNER.SEMANTIC_ARTIFACT_NAMES:
                    (case / name).write_text(f"{name}\n", encoding="utf-8")
                (run / "run_manifest.json").write_text(
                    json.dumps(
                        {
                            "execution": {"jobs": 1 if run == reference else 2},
                            "frozen_inputs": {
                                "analyzer": {
                                    "path": "frozen_inputs/tafuzz-sa",
                                    "sha256": analyzer_sha,
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )
            result = RUNNER.compare_semantic_artifact_runs(
                reference, current, ["case_001"]
            )
            self.assertEqual("INCOMPARABLE_IDENTITY_MISMATCH", result["status"])
            self.assertEqual(0, result["compared_artifact_count"])
            self.assertEqual("analyzer", result["identity_mismatches"][0]["input"])

    def test_determinism_gate_uses_current_frozen_files_before_manifest_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-precommit-") as directory:
            root = pathlib.Path(directory)
            reference = root / "serial"
            current = root / "parallel"
            for run in (reference, current):
                case = run / "cases/case_001"
                case.mkdir(parents=True)
                for name in RUNNER.SEMANTIC_ARTIFACT_NAMES:
                    (case / name).write_text(f"{name}\n", encoding="utf-8")
                frozen_analyzer = run / "frozen_inputs/tafuzz-sa"
                frozen_analyzer.parent.mkdir()
                frozen_analyzer.write_bytes(b"same frozen analyzer\n")
            (reference / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "execution": {"jobs": 1},
                        "frozen_inputs": {
                            "analyzer": {
                                "path": "frozen_inputs/tafuzz-sa",
                                "sha256": digest(reference / "frozen_inputs/tafuzz-sa"),
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = RUNNER.compare_semantic_artifact_runs(
                reference, current, ["case_001"]
            )
            self.assertEqual("PASS", result["status"])
            self.assertEqual(
                "REFERENCE_MANIFEST_AND_CURRENT_FROZEN_FILES",
                result["identity_evidence"],
            )

    def test_ranking_metrics_use_only_gold_actionable_sources(self) -> None:
        private = {"case_id": "case_001"}
        relation_material = [
            {
                "ap_id": "ap.target",
                "source_id": "source.gold",
                "gold_actionable": True,
                "candidate_ids": ["candidate.gold"],
            },
            {
                "ap_id": "ap.target",
                "source_id": "source.decoy",
                "gold_actionable": False,
                "candidate_ids": ["candidate.decoy"],
            },
        ]
        artifacts = {
            "frontier_candidates": {
                "candidates": [
                    {
                        "candidate_id": "candidate.decoy",
                        "ap_id": "ap.target",
                        "disposition": "ACTIONABLE",
                        "rank_tier": 1,
                    },
                    {
                        "candidate_id": "candidate.gold",
                        "ap_id": "ap.target",
                        "disposition": "ACTIONABLE",
                        "rank_tier": 2,
                    },
                ]
            }
        }
        rows = EVALUATOR.ranking_rows(private, artifacts, relation_material)
        self.assertEqual(1, len(rows))
        self.assertFalse(rows[0]["top1_hit"])
        self.assertTrue(rows[0]["top5_hit"])
        self.assertEqual(0.5, rows[0]["reciprocal_rank"])
        summary = EVALUATOR.ranking_summary(rows)
        self.assertEqual(0.0, summary["top1_hit_rate"])
        self.assertEqual(1.0, summary["top5_hit_rate"])
        self.assertEqual(0.5, summary["mrr_missing_relevant_is_zero"])


if __name__ == "__main__":
    unittest.main()
