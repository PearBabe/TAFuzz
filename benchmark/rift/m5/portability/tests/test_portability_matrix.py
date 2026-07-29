#!/usr/bin/env python3
"""Adversarial tests for the RIFT-M5 sealed portability matrix."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PORTABILITY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORTABILITY_ROOT))

import validate_portability_matrix as matrix  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def digest_record(kind: str, path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        "artifact_id": value.get("artifact_id", f"artifact:{kind}") if isinstance(value, dict) else f"artifact:{kind}",
        "kind": kind,
        "path": str(path),
        "sha256": matrix.sha256_file(path),
    }


def selected_digest(root: Path, relatives: list[str]) -> tuple[str, list[dict[str, str]]]:
    digest = hashlib.sha256()
    records: list[dict[str, str]] = []
    for relative in sorted(relatives):
        payload = (root / relative).read_bytes()
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        records.append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest()})
    return digest.hexdigest(), records


def time_receipt(path: Path, command: str, elapsed: str, rss_kib: int) -> None:
    path.write_text(
        f'\tCommand being timed: "{command}"\n'
        "\tUser time (seconds): 0.01\n"
        "\tSystem time (seconds): 0.00\n"
        f"\tElapsed (wall clock) time (h:mm:ss or m:ss): {elapsed}\n"
        f"\tMaximum resident set size (kbytes): {rss_kib}\n"
        "\tExit status: 0\n",
        encoding="utf-8",
    )


def model_pack(path: Path, *, layer: str, pack_id: str, private: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "2.0.0",
        "model_pack_id": pack_id,
        "model_pack_version": "1.0.0",
        "layer": layer,
        "property_independent": True,
        "observed_sha256": "0" * 64,
        "target": {
            "target_version": "fixture-1",
            "target_abi": "posix-lp64",
            "evidence_id": "evidence:fixture",
            "digest_policy": "freeze_before_property"
        },
        "resource_limits": {
            "max_selector_matches": 16,
            "max_capture_values": 16,
            "max_join_assignments": 16,
            "max_emitted_facts": 16
        },
        "selectors": [{
            "selector_id": f"selector:{pack_id}",
            "kind": "exact_qualified_signature",
            "exact_value": "int fixture(int)",
            "application_private": private
        }],
        "rules": [{
            "rule_id": f"rule:{pack_id}",
            "evidence_note": "fixture evidence",
            "matches": [{
                "match_id": f"match:{pack_id}",
                "selector_ref": f"selector:{pack_id}"
            }],
            "captures": [{
                "capture_id": f"capture:{pack_id}",
                "match_ref": f"match:{pack_id}",
                "projection": "matched_node"
            }],
            "joins": [],
            "emits": [{
                "emit_id": f"emit:{pack_id}",
                "fact_kind": "external_boundary",
                "source_capture_ref": f"capture:{pack_id}",
                "certainty": "modelled",
                "transfer_relation": "identity"
            }]
        }]
    }
    write_json(path, value)
    return value


class PortabilityFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="rift-m5-portability-matrix-")
        self.root = Path(self.temporary.name)
        self.core = self.root / "StaticAnalysis"
        (self.core / "core").mkdir(parents=True)
        (self.core / "schema").mkdir()
        (self.core / "core" / "engine.cpp").write_text(
            "int portable_engine(int value) { return value; }\n", encoding="utf-8"
        )
        write_json(self.core / "schema" / "artifact.json", {"type": "object"})
        core_sha, core_records = selected_digest(self.core, ["core/engine.cpp"])
        schema_sha, schema_records = selected_digest(self.core, ["schema/artifact.json"])
        self.build_manifest = self.root / "rift_build_manifest.json"
        write_json(self.build_manifest, {
            "schema_version": "rift.build-manifest.v1",
            "identity_policy": "relative-path-and-content-v1",
            "production_core_sha256": core_sha,
            "schema_bundle_sha256": schema_sha,
            "production_core_files": core_records,
            "schema_files": schema_records,
        })
        self.analyzer = self.root / "tafuzz-sa"
        self.analyzer.write_bytes(b"portable analyzer fixture\n")
        self.analyzer.chmod(0o755)
        self.z3 = self.root / "libz3-fixture.so"
        self.z3.write_bytes(b"z3 fixture bytes\n")
        self.verifier = self.root / "verify_m5_certificate.py"
        self.verifier.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        self.contract = self.root / "portability_contract.json"
        write_json(self.contract, {
            "contract_id": matrix.CONTRACT_ID,
            "core_forbidden_literals": ["libcoap", "ArduPilot", "expected_answer_edge"],
        })
        self.platform_pack = self.root / "posix_pack.json"
        model_pack(self.platform_pack, layer="platform", pack_id="pack.platform.fixture")
        self.project_specs: list[dict[str, object]] = []
        for index in range(3):
            self.project_specs.append(self.make_project(index))
        self.spec_path = self.root / "input.json"
        write_json(self.spec_path, {
            "schema_version": matrix.INPUT_SCHEMA_VERSION,
            "seal_intent": "FINAL_SEAL_REQUEST",
            "contract_path": str(self.contract),
            "core_root_path": str(self.core),
            "schema_root_path": str(self.core / "schema"),
            "analyzer_binary_path": str(self.analyzer),
            "build_manifest_path": str(self.build_manifest),
            "verifier_path": str(self.verifier),
            "python_interpreter_path": str(Path(sys.executable).resolve()),
            "toolchain_component_paths": [str(self.z3)],
            "projects": self.project_specs,
        })
        self.matrix = matrix.build_matrix_from_spec(matrix.load_json(self.spec_path), self.spec_path)
        self.matrix_path = self.root / "matrix.json"
        matrix.write_json_atomic(self.matrix_path, self.matrix)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_git(self, root: Path, *args: str) -> None:
        completed = subprocess.run(
            ["git", "-C", str(root), *args], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)

    def make_project(self, index: int) -> dict[str, object]:
        repository = self.root / f"repository-{index}"
        repository.mkdir()
        self.run_git(repository, "init", "-q")
        sources: list[Path] = []
        for source_index in range(2):
            source = repository / f"subject_{index}_{source_index}.c"
            source.write_text(
                f"int subject_{index}_{source_index}(int value) {{ return value + {index + source_index + 1}; }}\n",
                encoding="utf-8",
            )
            sources.append(source)
        self.run_git(repository, "add", ".")
        self.run_git(
            repository, "-c", "user.name=RIFT Fixture", "-c",
            "user.email=rift@example.invalid", "commit", "-q", "-m", f"fixture {index}",
        )
        project_root = self.root / f"project-{index}"
        project_root.mkdir()
        full_compile = project_root / "compile_commands.full.json"
        full_entries = [{
            "directory": str(repository),
            "file": str(source),
            "arguments": ["clang-18", "-c", str(source)],
        } for source in sources]
        write_json(full_compile, full_entries)
        analyzed_compile = full_compile
        analyzed_entries = full_entries
        scope = "FULL_COMPILE_DB"
        if index == 1:
            analyzed_compile = project_root / "compile_commands.selected.json"
            analyzed_entries = full_entries[:1]
            write_json(analyzed_compile, analyzed_entries)
            scope = "SELECTED_REAL_TU"
        property_path = project_root / "property_ir.json"
        write_json(property_path, {
            "schema_version": "2.0.0",
            "artifact_id": f"artifact.property.fixture.{index}",
            "property_id": f"property.fixture.{index}",
        })
        executor = project_root / "executor.json"
        write_json(executor, {
            "schema_version": "1.0.0",
            "artifact_id": f"executor.fixture.{index}",
            "executor_id": f"executor.fixture.{index}",
        })
        packs = [self.platform_pack]
        if index == 0:
            adapter = project_root / "adapter.json"
            model_pack(adapter, layer="project_adapter", pack_id="pack.adapter.fixture-zero", private=True)
            packs.append(adapter)
        result = project_root / "result"
        result.mkdir()
        sidecars = {
            "semantic_index": {
                "schema_version": "2.0.0", "artifact_id": f"index:{index}",
                "translation_units": [{"tu_id": f"tu:{index}:{n}"} for n in range(len(analyzed_entries))],
            },
            "ap_bindings": {"schema_version": "1.0.0", "artifact_id": f"bindings:{index}"},
            "contextual_influence_graph": {"schema_version": "2.0.0", "artifact_id": f"graph:{index}"},
            "ap_influence_cones": {"schema_version": "1.0.0", "artifact_id": f"cones:{index}"},
            "model_fact_overlay": {
                "schema_version": "1.0.0", "artifact_id": f"overlay:{index}",
                "unknown_outcomes": [{"reason": "fixture unknown"}], "coverage_gaps": [],
            },
            "predicate_occurrence_bindings": {"schema_version": "1.0.0", "artifact_id": f"occurrences:{index}"},
            "frontier_candidates": {
                "schema_version": "3.0.0", "artifact_id": f"candidates:{index}",
                "candidates": [{"candidate_id": f"candidate:{index}", "disposition": "ACTIONABLE", "uncertainty_reasons": ["fixture"]}],
            },
            "fuzzable_frontier": {"schema_version": "2.0.0", "artifact_id": f"frontier:{index}"},
            "mutation_recipes": {
                "schema_version": "1.0.0", "artifact_id": f"recipes:{index}",
                "recipes": [{"recipe_id": f"recipe:{index}", "status": "UNKNOWN"}],
            },
            "recipe_replay_obligations": {"schema_version": "1.0.0", "artifact_id": f"replay:{index}"},
        }
        for kind, value in sidecars.items():
            write_json(result / matrix.REQUIRED_ARTIFACT_NAMES[kind], value)
        analyzer_sha = matrix.sha256_file(self.analyzer)
        z3_sha = matrix.sha256_file(self.z3)
        build_sha = matrix.sha256_file(self.build_manifest)
        build_json = matrix.load_json(self.build_manifest)
        toolchain = [{
            "component_id": "tool:analyzer",
            "component_kind": "executable",
            "name": "tafuzz-sa executable",
            "version": "fixture-1",
            "sha256": analyzer_sha,
        }, {
            "component_id": "tool:z3",
            "component_kind": "shared_object",
            "name": "libz3-fixture.so",
            "version": "fixture-1",
            "sha256": z3_sha,
        }]
        m4_outputs = [
            digest_record(kind, result / matrix.REQUIRED_ARTIFACT_NAMES[kind])
            for kind in ("semantic_index", "ap_bindings", "contextual_influence_graph", "ap_influence_cones")
        ]
        source = sources[0]
        m4_path = result / "analysis_certificate.json"
        write_json(m4_path, {
            "schema_version": "2.0.0",
            "certificate_id": f"certificate:m4:{index}",
            "status": "CONSERVATIVE_INCOMPLETE",
            "analyzer": {"binary_sha256": analyzer_sha},
            "build_manifest": {
                "manifest_sha256": build_sha,
                "production_core_sha256": build_json["production_core_sha256"],
                "schema_bundle_sha256": build_json["schema_bundle_sha256"],
            },
            "core_tree_sha256": build_json["production_core_sha256"],
            "schema_bundle_sha256": build_json["schema_bundle_sha256"],
            "inputs": [
                digest_record("typed_property_ir", property_path),
                digest_record("compile_commands", analyzed_compile),
            ],
            "outputs": m4_outputs,
            "toolchain": toolchain,
            "source_input_provenance": {"files": [{
                "logical_path": f"fixture://subject/{source.name}",
                "sha256": matrix.sha256_file(source),
                "byte_size": source.stat().st_size,
                "observed_paths": [str(source)],
            }]},
            "unsupported_constructs": [],
        })
        m5_outputs = [
            digest_record(kind, result / matrix.REQUIRED_ARTIFACT_NAMES[kind])
            for kind in (
                "model_fact_overlay", "predicate_occurrence_bindings", "frontier_candidates",
                "fuzzable_frontier", "mutation_recipes", "recipe_replay_obligations",
            )
        ]
        commitments = {
            "analysis_certificate": digest_record("m4_analysis_certificate", m4_path),
            "typed_property_ir": digest_record("typed_property_ir", property_path),
        }
        commitments.update({item["kind"]: item for item in m4_outputs})
        pack_descriptors = []
        for pack_path in packs:
            facts = matrix.model_pack_facts(pack_path)
            pack_descriptors.append({
                "model_pack_id": facts["model_pack_id"],
                "model_pack_version": facts["model_pack_version"],
                "layer": facts["layer"],
                "path": str(pack_path),
                "sha256": facts["raw_sha256"],
                "semantic_sha256": facts["semantic_sha256"],
            })
        m5_path = result / "m5_analysis_certificate.json"
        write_json(m5_path, {
            "schema_version": "1.0.0",
            "certificate_id": f"certificate:m5:{index}",
            "status": "CONSERVATIVE_INCOMPLETE",
            "analyzer": {"binary_sha256": analyzer_sha},
            "build_manifest": {
                "manifest_sha256": build_sha,
                "production_core_sha256": build_json["production_core_sha256"],
                "schema_bundle_sha256": build_json["schema_bundle_sha256"],
            },
            "m4_commitments": commitments,
            "outputs": m5_outputs,
            "model_packs": pack_descriptors,
            "executor_manifest": {
                "artifact_id": f"executor.fixture.{index}",
                "path": str(executor), "sha256": matrix.sha256_file(executor),
            },
            "runtime_components": [
                {**toolchain[0], "path": str(self.analyzer)},
                {**toolchain[1], "path": str(self.z3)},
            ],
            "solver": {"queries": index, "timeouts": 0, "unsupported": 0},
            "diagnostics": [],
        })
        detached = project_root / "detached.json"
        write_json(detached, {
            "schema_version": "rift-m5-detached-verifier/1.0.0",
            "certificate_path": str(m5_path),
            "certificate_sha256": matrix.sha256_file(m5_path),
            "checks": 1,
            "failures": 0,
            "findings": [{"check_id": "fixture", "detail": "fixture", "status": "PASS"}],
            "physical_files_rehashed": 16,
            "verdict": "PASS",
        })
        analysis_time = project_root / "analysis.time"
        detached_time = project_root / "detached.time"
        time_receipt(analysis_time, f"{self.analyzer} recipes fixture-{index}", f"0:0{index + 1}.00", 100 + index)
        time_receipt(detached_time, f"python3 {self.verifier} {m5_path}", f"0:0{index + 2}.00", 200 + index)
        return {
            "project_id": f"fixture-project-{index}",
            "repository_id": f"fixture://repository/{index}",
            "repository_root_path": str(repository),
            "result_root_path": str(result),
            "detached_report_path": str(detached),
            "full_compile_database_path": str(full_compile),
            "analysis_scope": scope,
            "selection_reason": "Exact full database" if scope == "FULL_COMPILE_DB" else "One exact real TU selected from full database",
            "analysis_time_receipt_path": str(analysis_time),
            "detached_time_receipt_path": str(detached_time),
            "adaptation_effort": {
                "setup_minutes": index + 1,
                "property_binding_minutes": 2,
                "adapter_authoring_minutes": 1 if index == 0 else 0,
                "model_validation_minutes": 3,
                "notes": "fixture human-effort ledger",
            },
            "additional_core_forbidden_literals": [f"subject_{index}"],
        }

    @staticmethod
    def reseal(value: dict[str, object]) -> None:
        value.pop("matrix_id", None)
        value["matrix_id"] = "portability-matrix:" + matrix.canonical_sha256(value)

    def assert_fails(self, value: dict[str, object], needle: str) -> None:
        with self.assertRaisesRegex(matrix.MatrixError, needle):
            matrix.validate_matrix(value, self.matrix_path)

    def test_valid_three_project_matrix_passes(self) -> None:
        summary = matrix.validate_matrix(self.matrix, self.matrix_path)
        self.assertEqual(summary["verdict"], "PASS")
        self.assertEqual(summary["projects"], 3)
        try:
            import jsonschema
        except ImportError:
            return
        schema = json.loads((PORTABILITY_ROOT / "portability_matrix.schema.json").read_text(encoding="utf-8"))
        errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(self.matrix), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])

    def test_binary_identity_drift_fails(self) -> None:
        value = copy.deepcopy(self.matrix)
        value["projects"][1]["observed_identities"]["binary_sha256"] = "f" * 64
        self.reseal(value)
        self.assert_fails(value, "observed_identities drift")

    def test_duplicate_project_fails(self) -> None:
        value = copy.deepcopy(self.matrix)
        value["projects"][2]["repository"]["repository_id"] = value["projects"][0]["repository"]["repository_id"]
        self.reseal(value)
        self.assert_fails(value, "duplicate repository_id")

    def test_artifact_hash_tamper_fails(self) -> None:
        value = copy.deepcopy(self.matrix)
        value["projects"][0]["artifacts"]["frontier_candidates"]["sha256"] = "e" * 64
        self.reseal(value)
        self.assert_fails(value, "frontier_candidates.sha256 mismatch")

    def test_selected_single_tu_cannot_claim_full_fails(self) -> None:
        value = copy.deepcopy(self.matrix)
        value["projects"][1]["scope"]["kind"] = "FULL_COMPILE_DB"
        self.reseal(value)
        self.assert_fails(value, "claims FULL_COMPILE_DB")

    def test_project_adapter_cannot_masquerade_as_platform_fails(self) -> None:
        value = copy.deepcopy(self.matrix)
        value["projects"][0]["model_packs"][1]["layer"] = "platform"
        self.reseal(value)
        self.assert_fails(value, "differs from physical pack facts")

    def test_missing_large_artifact_fails(self) -> None:
        path = Path(self.matrix["projects"][0]["artifacts"]["contextual_influence_graph"]["path"])
        path.unlink()
        self.assert_fails(self.matrix, "does not exist")

    def test_verifier_drift_fails(self) -> None:
        self.verifier.write_text("#!/usr/bin/env python3\n# drift\n", encoding="utf-8")
        self.assert_fails(self.matrix, "detached_verifier.script.(size|sha256) mismatch")


if __name__ == "__main__":
    unittest.main()
