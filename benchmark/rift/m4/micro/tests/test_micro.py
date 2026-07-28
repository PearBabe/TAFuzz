#!/usr/bin/env python3
"""Deterministic self-tests for the RIFT-M4 micro acceptance boundary."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import evaluate as trusted_evaluator
from command_adapter import DEFAULT_ADAPTER, load_adapter, render_commands
from common import (
    AcceptanceError,
    DEFAULT_CORPUS,
    PRODUCTION_SCHEMA_DIR,
    location_matches,
    prepare_bundle,
    read_json,
    sha256_bytes,
    sha256_file,
)
from validate_acceptance import (
    assert_candidate_accounting,
    assert_lossless_index_identity,
    assert_property_id_domains_disjoint,
    validate_bundle,
)
from run_analyzer import run_all
from validate_acceptance import validate_run


def tree_digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def build_mini_corpus(root: Path) -> Path:
    corpus = root / "corpus"
    source_dir = corpus / "cases"
    source_dir.mkdir(parents=True)
    original = sorted((DEFAULT_CORPUS / "cases").glob("*.c"))[0]
    source = source_dir / "fixture.c"
    shutil.copyfile(original, source)
    (corpus / "build").mkdir()
    compile_command = {
        "directory": str(corpus),
        "file": str(source),
        "arguments": [
            "clang-18",
            "-std=c11",
            "-O0",
            "-g",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-c",
            str(source),
            "-o",
            str(corpus / "build" / "fixture.o"),
        ],
    }
    (corpus / "compile_commands.json").write_text(
        json.dumps([compile_command], indent=2) + "\n", encoding="utf-8"
    )
    return corpus


def write_test_adapter(path: Path, analyzer_script: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "rift.m4.command-adapter.v1",
                "stages": [
                    {
                        "name": "influence",
                        "produces": [
                            "semantic_index",
                            "ap_bindings",
                            "contextual_influence_graph",
                            "ap_influence_cones",
                        ],
                        "argv": [
                            "{analyzer}",
                            str(analyzer_script),
                            "influence",
                            "--compile-db",
                            "{compile_database}",
                            "--property",
                            "{property_ir}",
                            "--output-dir",
                            "{output_directory}",
                            "--schema-dir",
                            str(PRODUCTION_SCHEMA_DIR),
                        ],
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class PreparedBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="rift-m4-micro-tests-")
        cls.root = Path(cls.temporary.name)
        cls.first = cls.root / "first"
        cls.second = cls.root / "second"
        commitment = sha256_file(DEFAULT_CORPUS / "manifest.json")
        prepare_bundle(DEFAULT_CORPUS, cls.first, commitment)
        prepare_bundle(DEFAULT_CORPUS, cls.second, commitment)
        cls.manifest = validate_bundle(cls.first, expected_cases=120)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_preparation_is_byte_deterministic(self) -> None:
        self.assertEqual(tree_digests(self.first), tree_digests(self.second))

    def test_fixed_public_population(self) -> None:
        self.assertEqual(self.manifest["case_count"], 120)
        self.assertEqual(self.manifest["ap_count"], 130)
        self.assertFalse(self.manifest["human_labels_required"])
        self.assertEqual(
            self.manifest["answer_access_policy"],
            "PRE_ANALYSIS_SOURCE_AND_BUILD_METADATA_ONLY",
        )
        self.assertEqual(
            self.manifest["private_oracle_commitment_sha256"],
            sha256_file(DEFAULT_CORPUS / "manifest.json"),
        )

    def test_private_oracle_commitment_mismatch_is_rejected(self) -> None:
        changed = dict(self.manifest)
        changed["private_oracle_commitment_sha256"] = "0" * 64
        with self.assertRaisesRegex(AcceptanceError, "differs from frozen commitment"):
            trusted_evaluator.load_private_truth(DEFAULT_CORPUS, self.first, changed)

    def test_analyzer_manifest_has_no_source_candidate_or_relation_oracle(self) -> None:
        forbidden_keys = {
            "category",
            "case_relation",
            "relation",
            "relations",
            "source_anchors",
            "controllability",
            "fuzzable_frontier",
        }

        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys & set(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.manifest)
        visible = "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.first.rglob("*")
            if path.is_file()
        )
        for answer in ("MUST_INFLUENCE", "MAY_INFLUENCE", "NO_INFLUENCE"):
            self.assertNotIn(answer, visible)
        self.assertNotIn("RIFT_SOURCE:", visible)
        self.assertNotIn("RIFT_NODE:", visible)
        self.assertNotIn("RIFT_AP:", visible)
        source_visible = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (self.first / "sources").iterdir()
            if path.is_file()
        )
        self.assertNotRegex(source_visible, r"\b(?:source|node)_[a-z0-9_]+\b")

    def test_all_120_raw_compile_commands_build(self) -> None:
        commands = read_json(self.first / "compile_commands.json")
        self.assertEqual(len(commands), 120)
        with tempfile.TemporaryDirectory(prefix="rift-m4-objects-") as temporary:
            object_root = Path(temporary)

            def compile_one(index_and_command):
                index, command = index_and_command
                arguments = list(command["arguments"])
                output_index = arguments.index("-o") + 1
                arguments[output_index] = str(object_root / f"{index:03d}.o")
                directory = (
                    (self.first / "compile_commands.json").parent
                    / command["directory"]
                ).resolve()
                return subprocess.run(
                    arguments,
                    cwd=directory,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(compile_one, enumerate(commands, 1)))
        failures = [result.stderr for result in results if result.returncode != 0]
        self.assertFalse(failures, "\n".join(failures[:3]))


class ContractUnitTests(unittest.TestCase):
    def test_property_ir_id_domains_must_be_disjoint(self) -> None:
        property_ir = {
            "artifact_id": "property.case_001",
            "property_id": "property.case_001",
            "atomic_propositions": [{"ap_id": "ap_primary"}],
            "selectors": [{"selector_id": "selector.primary"}],
            "formula": {"node_id": "formula.root", "operands": []},
        }
        with self.assertRaisesRegex(AcceptanceError, "stable-ID domains collide"):
            assert_property_id_domains_disjoint(property_ir, "case_001")

    def test_single_pipeline_runner_seals_schema_valid_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m4-runner-test-") as temporary:
            root = Path(temporary)
            corpus = build_mini_corpus(root)
            bundle = root / "bundle"
            prepare_bundle(
                corpus,
                bundle,
                sha256_bytes(b"fixture-private-oracle"),
            )
            adapter = root / "adapter.json"
            fake = root / "fake_analyzer.py"
            shutil.copyfile(HERE / "tests" / "fake_analyzer.py", fake)
            write_test_adapter(adapter, fake)
            result = root / "result"
            run = run_all(
                bundle=bundle,
                output=result,
                analyzer=Path(sys.executable),
                adapter_path=adapter,
                timeout=30,
                expected_cases=1,
            )
            self.assertTrue(run["analysis_complete"])
            self.assertEqual(run["case_count"], 1)
            _, _, snapshots = validate_run(bundle, result, adapter, expected_cases=1)
            tampered_index = copy.deepcopy(snapshots["case_001"]["semantic_index"])
            tampered_index["input_files"][0]["input_file_id"] = "input-file:" + "0" * 64
            with self.assertRaisesRegex(AcceptanceError, "input-file ID"):
                assert_lossless_index_identity(
                    case_id="case_001",
                    bundle=bundle,
                    compile_path=bundle / "cases" / "case_001" / "compile_commands.json",
                    input_case=read_json(bundle / "manifest.json")["cases"][0],
                    index=tampered_index,
                    graph=snapshots["case_001"]["contextual_influence_graph"],
                )
            semantic_path = result / "cases" / "case_001" / "semantic_index.json"
            semantic_bytes = semantic_path.read_bytes()
            semantic_path.write_text("{}\n", encoding="utf-8")
            self.assertRegex(
                snapshots["case_001"]["semantic_index"]["artifact_id"],
                r"^index:[0-9a-f]{64}$",
            )
            with self.assertRaisesRegex(AcceptanceError, "digest mismatch"):
                validate_run(bundle, result, adapter, expected_cases=1)
            semantic_path.write_bytes(semantic_bytes)
            fake.write_text(fake.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
            with self.assertRaisesRegex(AcceptanceError, "helper/input file changed"):
                validate_run(bundle, result, adapter, expected_cases=1)

    def test_runner_refuses_to_seal_without_certificate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m4-no-certificate-") as temporary:
            root = Path(temporary)
            corpus = build_mini_corpus(root)
            bundle = root / "bundle"
            prepare_bundle(corpus, bundle, sha256_bytes(b"fixture-private-oracle"))
            fake = root / "fake_analyzer.py"
            source = (HERE / "tests" / "fake_analyzer.py").read_text(encoding="utf-8")
            needle = 'output / "analysis_certificate.json",'
            self.assertIn(needle, source)
            fake.write_text(
                source.replace(needle, 'output / "not_a_certificate.json",', 1),
                encoding="utf-8",
            )
            adapter = root / "adapter.json"
            write_test_adapter(adapter, fake)
            result = root / "result"
            with self.assertRaisesRegex(AcceptanceError, "did not produce analysis_certificate"):
                run_all(
                    bundle=bundle,
                    output=result,
                    analyzer=Path(sys.executable),
                    adapter_path=adapter,
                    timeout=30,
                    expected_cases=1,
                )
            self.assertFalse((result / "analysis_run_manifest.json").exists())

    def test_private_corpus_read_is_blocked_before_seal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m4-leak-test-") as temporary:
            root = Path(temporary)
            corpus = build_mini_corpus(root)
            bundle = root / "bundle"
            prepare_bundle(
                corpus,
                bundle,
                sha256_bytes(b"fixture-private-oracle"),
            )
            adapter = root / "adapter.json"
            write_test_adapter(adapter, HERE / "tests" / "leaky_analyzer.py")
            result = root / "result"
            with self.assertRaisesRegex(AcceptanceError, "exited"):
                run_all(
                    bundle=bundle,
                    output=result,
                    analyzer=Path(sys.executable),
                    adapter_path=adapter,
                    timeout=30,
                    expected_cases=1,
                )
            self.assertFalse((result / "analysis_run_manifest.json").exists())

    def test_default_adapter_is_single_in_memory_pipeline(self) -> None:
        adapter = load_adapter(DEFAULT_ADAPTER)
        commands = render_commands(
            adapter,
            Path("/bin/true"),
            Path("/tmp/compile_commands.json"),
            Path("/tmp/property_ir.json"),
            Path("/tmp/results"),
        )
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["name"], "influence")
        self.assertIn("--compile-db", commands[0]["argv"])
        self.assertIn("--output-dir", commands[0]["argv"])
        self.assertEqual(len(commands[0]["produces"]), 4)

    def test_missing_binding_candidate_is_rejected(self) -> None:
        property_ir = {
            "atomic_propositions": [
                {"ap_id": "ap_primary", "roles": ["guard"]}
            ]
        }
        cones = {
            "cones": [
                {
                    "ap_id": "ap_primary",
                    "roles": ["guard"],
                    "candidate_accounting": [],
                    "members": [],
                    "edge_ids": [],
                    "status": "COMPLETE",
                }
            ]
        }
        with self.assertRaisesRegex(AcceptanceError, "incomplete candidate accounting"):
            assert_candidate_accounting(
                case_id="case_001",
                property_ir=property_ir,
                candidates_by_ap={"ap_primary": {"binding.primary"}},
                candidate_status_by_id={"binding.primary": "CONFIRMED"},
                graph_nodes={},
                graph_edges={},
                cones=cones,
            )

    def test_included_root_must_be_a_cone_member(self) -> None:
        with self.assertRaisesRegex(AcceptanceError, "root is absent"):
            assert_candidate_accounting(
                case_id="case_001",
                property_ir={
                    "atomic_propositions": [
                        {"ap_id": "ap_primary", "roles": ["guard"]}
                    ]
                },
                candidates_by_ap={"ap_primary": {"binding.primary"}},
                candidate_status_by_id={"binding.primary": "CONFIRMED"},
                graph_nodes={"graph.ap": {"node_id": "graph.ap"}},
                graph_edges={},
                cones={
                    "cones": [
                        {
                            "ap_id": "ap_primary",
                            "roles": ["guard"],
                            "candidate_accounting": [
                                {
                                    "binding_id": "binding.primary",
                                    "disposition": "INCLUDED",
                                    "root_node_ids": ["graph.ap"],
                                }
                            ],
                            "members": [],
                            "edge_ids": [],
                            "status": "COMPLETE",
                        }
                    ]
                },
            )

    def test_non_root_member_requires_witness(self) -> None:
        with self.assertRaisesRegex(AcceptanceError, "non-root cone member"):
            assert_candidate_accounting(
                case_id="case_001",
                property_ir={
                    "atomic_propositions": [
                        {"ap_id": "ap_primary", "roles": ["guard"]}
                    ]
                },
                candidates_by_ap={"ap_primary": {"binding.primary"}},
                candidate_status_by_id={"binding.primary": "CONFIRMED"},
                graph_nodes={
                    "graph.ap": {"node_id": "graph.ap"},
                    "graph.source": {"node_id": "graph.source"},
                },
                graph_edges={},
                cones={
                    "cones": [
                        {
                            "ap_id": "ap_primary",
                            "roles": ["guard"],
                            "candidate_accounting": [
                                {
                                    "binding_id": "binding.primary",
                                    "disposition": "INCLUDED",
                                    "root_node_ids": ["graph.ap"],
                                }
                            ],
                            "members": [
                                {
                                    "node_id": "graph.ap",
                                    "witness_edge_ids": [],
                                    "membership": "MUST_INFLUENCE",
                                },
                                {
                                    "node_id": "graph.source",
                                    "witness_edge_ids": [],
                                    "membership": "MAY_INFLUENCE",
                                },
                            ],
                            "edge_ids": [],
                            "status": "COMPLETE",
                        }
                    ]
                },
            )

    def test_witness_must_be_a_directed_continuous_path_to_root(self) -> None:
        with self.assertRaisesRegex(AcceptanceError, "directed continuous path"):
            assert_candidate_accounting(
                case_id="case_001",
                property_ir={
                    "atomic_propositions": [
                        {"ap_id": "ap_primary", "roles": ["guard"]}
                    ]
                },
                candidates_by_ap={"ap_primary": {"binding.primary"}},
                candidate_status_by_id={"binding.primary": "CONFIRMED"},
                graph_nodes={
                    "graph.source": {"node_id": "graph.source"},
                    "graph.middle": {"node_id": "graph.middle"},
                    "graph.ap": {"node_id": "graph.ap"},
                },
                graph_edges={
                    "edge.source-middle": {
                        "edge_id": "edge.source-middle",
                        "source_node_id": "graph.source",
                        "target_node_id": "graph.middle",
                    },
                    "edge.middle-ap": {
                        "edge_id": "edge.middle-ap",
                        "source_node_id": "graph.middle",
                        "target_node_id": "graph.ap",
                    },
                },
                cones={
                    "cones": [
                        {
                            "ap_id": "ap_primary",
                            "roles": ["guard"],
                            "candidate_accounting": [
                                {
                                    "binding_id": "binding.primary",
                                    "disposition": "INCLUDED",
                                    "root_node_ids": ["graph.ap"],
                                }
                            ],
                            "members": [
                                {
                                    "node_id": "graph.source",
                                    "witness_edge_ids": [
                                        "edge.middle-ap",
                                        "edge.source-middle",
                                    ],
                                    "membership": "MAY_INFLUENCE",
                                },
                                {
                                    "node_id": "graph.middle",
                                    "witness_edge_ids": ["edge.middle-ap"],
                                    "membership": "MAY_INFLUENCE",
                                },
                                {
                                    "node_id": "graph.ap",
                                    "witness_edge_ids": [],
                                    "membership": "MUST_INFLUENCE",
                                },
                            ],
                            "edge_ids": ["edge.source-middle", "edge.middle-ap"],
                            "status": "COMPLETE",
                        }
                    ]
                },
            )

    def test_cone_edge_endpoints_must_be_members(self) -> None:
        with self.assertRaisesRegex(AcceptanceError, "edge endpoint is absent"):
            assert_candidate_accounting(
                case_id="case_001",
                property_ir={
                    "atomic_propositions": [
                        {"ap_id": "ap_primary", "roles": ["guard"]}
                    ]
                },
                candidates_by_ap={"ap_primary": {"binding.primary"}},
                candidate_status_by_id={"binding.primary": "CONFIRMED"},
                graph_nodes={
                    "graph.ap": {"node_id": "graph.ap"},
                    "graph.outside": {"node_id": "graph.outside"},
                },
                graph_edges={
                    "edge.escape": {
                        "edge_id": "edge.escape",
                        "source_node_id": "graph.ap",
                        "target_node_id": "graph.outside",
                    }
                },
                cones={
                    "cones": [
                        {
                            "ap_id": "ap_primary",
                            "roles": ["guard"],
                            "candidate_accounting": [
                                {
                                    "binding_id": "binding.primary",
                                    "disposition": "INCLUDED",
                                    "root_node_ids": ["graph.ap"],
                                }
                            ],
                            "members": [
                                {
                                    "node_id": "graph.ap",
                                    "witness_edge_ids": [],
                                    "membership": "MUST_INFLUENCE",
                                }
                            ],
                            "edge_ids": ["edge.escape"],
                            "status": "COMPLETE",
                        }
                    ]
                },
            )

    def test_exact_location_rejects_whole_file_range(self) -> None:
        self.assertFalse(
            location_matches(
                {
                    "file": "sources/case_001.c",
                    "line": 1,
                    "column": 1,
                    "end_line": 999,
                    "end_column": 999,
                },
                {"file": "sources/case_001.c", "line": 29, "column": 9},
            )
        )

    def test_unknown_is_not_credited_as_no(self) -> None:
        rows = [
            {"gold": "MUST", "prediction": "UNKNOWN"},
            {"gold": "NO", "prediction": "UNKNOWN"},
        ]
        metrics = trusted_evaluator.influence_metrics(rows)
        self.assertEqual(metrics["fn"], 1)
        self.assertEqual(metrics["tn"], 0)
        self.assertEqual(metrics["unknown_on_negative"], 1)

    def test_unresolved_binding_prevents_absence_from_becoming_no(self) -> None:
        location = {
            "file": "sources/case_001.c",
            "line": 20,
            "column": 9,
            "location_kind": "spelling",
        }
        private = {
            "case_id": "case_001",
            "category": "fixture",
            "input_case": {"source": {"path": "sources/case_001.c"}},
            "truth": {
                "sources": [{"id": "source_primary", "location": location}],
                "relations": [
                    {
                        "source_id": "source_primary",
                        "ap_id": "ap_primary",
                        "relation": "NO_INFLUENCE",
                    }
                ],
            },
        }
        artifacts = {
            "semantic_index": {
                "translation_units": [{"status": "indexed"}],
                "semantic_nodes": [{"node_id": "semantic.source", "location": location}],
                "unsupported_constructs": [],
            },
            "ap_bindings": {
                "bindings": [
                    {
                        "ap_id": "ap_primary",
                        "resolution": "UNRESOLVED",
                        "candidates": [
                            {
                                "binding_id": "binding.ap",
                                "status": "UNRESOLVED",
                            }
                        ],
                    }
                ],
                "unsupported_constructs": [],
            },
            "contextual_influence_graph": {
                "nodes": [],
                "status": "COMPLETE",
                "unsupported_constructs": [],
            },
            "ap_influence_cones": {
                "cones": [
                    {
                        "ap_id": "ap_primary",
                        "candidate_accounting": [
                            {
                                "binding_id": "binding.ap",
                                "disposition": "UNRESOLVED",
                            }
                        ],
                        "members": [],
                        "status": "COMPLETE",
                    }
                ],
                "unsupported_constructs": [],
            },
        }
        rows = trusted_evaluator.relation_rows(private, artifacts)
        self.assertEqual(rows[0]["prediction"], "UNKNOWN")

    def test_soundness_gap_prevents_absence_from_becoming_no(self) -> None:
        location = {
            "file": "sources/case_001.c",
            "line": 20,
            "column": 9,
            "location_kind": "spelling",
        }
        private = {
            "case_id": "case_001",
            "category": "fixture",
            "input_case": {"source": {"path": "sources/case_001.c"}},
            "truth": {
                "sources": [{"id": "source_primary", "location": location}],
                "relations": [
                    {
                        "source_id": "source_primary",
                        "ap_id": "ap_primary",
                        "relation": "NO_INFLUENCE",
                    }
                ],
            },
        }
        artifacts = {
            "semantic_index": {
                "translation_units": [{"status": "indexed"}],
                "semantic_nodes": [{"node_id": "semantic.source", "location": location}],
                "unsupported_constructs": [
                    {"effect": "soundness_risk", "kind": "fixture-gap"}
                ],
            },
            "ap_bindings": {
                "bindings": [
                    {
                        "ap_id": "ap_primary",
                        "resolution": "CONFIRMED",
                        "candidates": [
                            {
                                "binding_id": "binding.ap",
                                "status": "CONFIRMED",
                            }
                        ],
                    }
                ],
                "unsupported_constructs": [],
            },
            "contextual_influence_graph": {
                "nodes": [],
                "status": "COMPLETE",
                "unsupported_constructs": [],
            },
            "ap_influence_cones": {
                "cones": [
                    {
                        "ap_id": "ap_primary",
                        "candidate_accounting": [
                            {
                                "binding_id": "binding.ap",
                                "disposition": "INCLUDED",
                            }
                        ],
                        "members": [],
                        "status": "COMPLETE",
                    }
                ],
                "unsupported_constructs": [],
            },
        }
        self.assertEqual(
            trusted_evaluator.relation_rows(private, artifacts)[0]["prediction"],
            "UNKNOWN",
        )

    def test_unsupported_summary_is_total_and_deterministic(self) -> None:
        artifacts = {
            "semantic_index": {"unsupported_constructs": []},
            "ap_bindings": {"unsupported_constructs": [], "bindings": []},
            "contextual_influence_graph": {
                "unsupported_constructs": [
                    {
                        "kind": "indirect-call",
                        "effect": "precision_loss",
                    }
                ],
                "status": "CONSERVATIVE_INCOMPLETE",
            },
            "ap_influence_cones": {
                "unsupported_constructs": [],
                "cones": [],
            },
        }
        summary = trusted_evaluator.unsupported_summary(
            [artifacts],
            [{"prediction": "UNKNOWN"}],
            [{"predicted": False}],
        )
        self.assertEqual(summary["construct_kind_counts"], {"indirect-call": 1})
        self.assertEqual(summary["unknown_pair_predictions"], 1)
        self.assertEqual(summary["unresolved_top1_bindings"], 1)

    def test_private_reader_is_not_called_when_run_validation_fails(self) -> None:
        private_reader = mock.Mock()
        with mock.patch.object(
            trusted_evaluator,
            "validate_run",
            side_effect=AcceptanceError("unsealed"),
        ), mock.patch.object(
            trusted_evaluator, "load_private_truth", private_reader
        ):
            with self.assertRaisesRegex(AcceptanceError, "unsealed"):
                trusted_evaluator.evaluate(
                    Path("/tmp/bundle"),
                    Path("/tmp/run"),
                    Path("/tmp/corpus"),
                    DEFAULT_ADAPTER,
                    expected_cases=1,
                )
        private_reader.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
