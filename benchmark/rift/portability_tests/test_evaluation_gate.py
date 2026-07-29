#!/usr/bin/env python3
"""Adversarial, artifact-backed tests for the RIFT portability v3 gate."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


WORKSPACE = Path(__file__).resolve().parents[3]
VALIDATOR = WORKSPACE / "benchmark" / "rift" / "validate_portability_contract.py"
FORBIDDEN_RULES = [
    "per_property_slice", "hand_selected_dependency_path",
    "expected_answer_edge", "benchmark_case_id_branch",
]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def selected_tree(root: Path, relatives: list[str]) -> tuple[str, list[dict[str, str]]]:
    digest = hashlib.sha256()
    records = []
    for relative in sorted(relatives):
        path = root / relative
        relative_bytes = relative.encode()
        payload = path.read_bytes()
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        records.append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest()})
    return digest.hexdigest(), records


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact(path: Path, *, directory: bool = False, **extra: object) -> dict[str, object]:
    result: dict[str, object] = {
        "path": str(path),
        "sha256": tree_sha256(path) if directory else file_sha256(path),
    }
    result.update(extra)
    return result


def input_manifest_sha256(index: dict[str, object]) -> str:
    identity = index["identity_scheme"]
    payload = bytearray(identity.encode() + b"\0input-manifest/1.0.0")
    for item in index["input_files"]:
        logical = item["logical_path"].encode()
        payload.extend(b"\0" + item["role"].encode() + b"\0")
        payload.extend(str(len(logical)).encode() + b":" + logical)
        payload.extend(b"\0" + item["sha256"].encode() + b"\0")
        payload.extend(str(item["byte_size"]).encode())
    return hashlib.sha256(payload).hexdigest()


def toolchain_semantics(toolchain: dict[str, object]) -> str:
    components = [{
        "role": item["role"], "logical_name": item["logical_name"],
        "version": item["version"], "sha256": item["sha256"],
        "runtime_attested": item["runtime_attested"],
    } for item in toolchain["components"]]
    descriptor = {
        "semantic_configuration": sorted(toolchain["semantic_configuration"]),
        "components": sorted(components, key=lambda item: item["role"]),
    }
    return hashlib.sha256(json.dumps(
        descriptor, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


class EvaluationGateV3Test(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="rift-portability-v3-")
        self.root = Path(self.temporary.name)
        self.actual_core = self.root / "actual-core"
        core_files = {
            "core/engine.cpp": "int portable_engine() { return 1; }\n",
            "include/engine.hpp": "int portable_engine();\n",
            "cli/driver.py": "# project-neutral analyzer driver\n",
        }
        for relative, payload in core_files.items():
            path = self.actual_core / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")

        self.analyzer = self.root / "tafuzz-sa"
        self.analyzer.write_bytes(b"portable analyzer fixture\0")
        self.analyzer.chmod(0o755)
        self.schema_bundle = self.root / "schemas"
        self.schema_bundle.mkdir()
        schema_ids = {
            "common.schema.json": "https://tafuzz.dev/rift/schema/common/1.0.0",
            "typed_property_ir.schema.json": "https://tafuzz.dev/rift/schema/typed-property-ir/1.0.0",
            "model_pack.schema.json": "https://tafuzz.dev/rift/schema/model-pack/1.0.0",
            "semantic_index.schema.json": "https://tafuzz.dev/rift/schema/semantic-index/2.0.0",
            "ap_bindings.schema.json": "https://tafuzz.dev/rift/schema/ap-bindings/1.0.0",
            "contextual_influence_graph.schema.json": "https://tafuzz.dev/rift/schema/contextual-influence-graph/2.0.0",
            "ap_influence_cones.schema.json": "https://tafuzz.dev/rift/schema/ap-influence-cones/1.0.0",
            "analysis_certificate.schema.json": "https://tafuzz.dev/rift/schema/analysis-certificate/2.0.0",
        }
        for name, schema_id in schema_ids.items():
            write_json(self.schema_bundle / name, {
                "$id": schema_id,
                "type": "object",
            })
        shutil.copytree(self.schema_bundle, self.actual_core / "schema")

        self.toolchain = self.make_toolchain()
        self.toolchain_digest = toolchain_semantics(self.toolchain)
        self.toolchain["semantics_sha256"] = self.toolchain_digest
        self.core_digest, core_records = selected_tree(
            self.actual_core, sorted(core_files)
        )
        schema_relatives = [f"schema/{name}" for name in schema_ids]
        self.schema_digest, schema_records = selected_tree(
            self.actual_core, schema_relatives
        )
        self.build_manifest = self.root / "build_manifest.json"
        write_json(self.build_manifest, {
            "schema_version": "rift.build-manifest.v1",
            "identity_policy": "relative-path-and-content-v1",
            "production_core_files": core_records,
            "production_core_sha256": self.core_digest,
            "schema_files": schema_records,
            "schema_bundle_sha256": self.schema_digest,
        })
        self.evidence, self.manifest_paths = self.make_evidence()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_toolchain(self) -> dict[str, object]:
        tool_root = self.root / "toolchain"
        tool_root.mkdir()
        roles = {
            "analyzer": (self.analyzer, "tafuzz-sa", "0.1.0"),
            "clang": (tool_root / "clang-18", "clang", "clang version 18.1.8"),
            "opt": (tool_root / "opt-18", "opt", "LLVM opt version 18.1.8"),
            "llvm": (tool_root / "libLLVM.so", "libLLVM", "LLVM 18.1.8"),
            "libclang": (tool_root / "libclang-cpp.so", "libclang-cpp", "clang 18.1.8"),
            "svf_core": (tool_root / "libSvfCore.so", "libSvfCore", "SVF 3.2"),
            "svf_llvm": (tool_root / "libSvfLLVM.so", "libSvfLLVM", "SVF 3.2"),
            "svf_extapi": (tool_root / "svf-extapi.bc", "svf-extapi", "SVF 3.2"),
            "z3": (tool_root / "libz3.so", "libz3", "Z3 4.13"),
        }
        components = []
        for role, (path, name, version) in roles.items():
            if not path.exists():
                path.write_bytes(f"fixture {role} {version}".encode())
            components.append({
                "role": role, "logical_name": name, "version": version,
                "runtime_attested": True,
                **artifact(path),
            })
        return {
            "semantic_configuration": [
                "clang-major=18", "llvm-major=18", "svf-version=3.2",
                "z3-enabled=true", "path-identity=rift.identity/2.0.0",
            ],
            "components": components,
        }

    def make_evidence(self) -> tuple[dict[str, object], list[Path]]:
        projects = []
        manifests = []
        for index in range(3):
            run_root = self.root / f"run-{index}"
            run_root.mkdir()
            source_root = run_root / "source"
            source_root.mkdir()
            source_file = source_root / f"subject_{index}.c"
            source_file.write_text(
                f"int subject_{index}(int value) {{ return value + {index + 1}; }}\n",
                encoding="utf-8",
            )
            source_digest = tree_sha256(source_root)
            repository_manifest = run_root / "repository.json"
            write_json(repository_manifest, {
                "schema_version": "1.0.0",
                "repository_id": f"fixture://repository/{index}",
                "source_revision": f"revision-{index}",
                "source_tree_sha256": source_digest,
            })
            compile_database = run_root / "compile_commands.json"
            write_json(compile_database, [{
                "directory": str(source_root), "file": str(source_file),
                "arguments": ["clang-18", "-c", str(source_file), f"-DPROJECT={index}"],
            }])
            property_ir = run_root / "property_ir.json"
            write_json(property_ir, {
                "schema_version": "1.0.0", "artifact_id": f"property:{index}",
                "property_id": f"portable_property_{index}",
            })
            model_pack = run_root / "model_pack.json"
            write_json(model_pack, {
                "schema_version": "1.0.0", "model_pack_id": f"model:{index}",
                "model_pack_version": "1.0.0", "property_independent": True,
                "rule_policy": {
                    "contract_id": "RIFT-PORTABILITY-1",
                    "allowed_rule_classes": ["external_input_boundary"],
                    "forbidden_rule_classes": FORBIDDEN_RULES,
                },
                "selectors": [],
                "rules": [{
                    "rule_id": f"external:{index}",
                    "rule_class": "external_input_boundary",
                }],
            })

            before = run_root / "core-before"
            after = run_root / "core-after"
            shutil.copytree(self.actual_core, before)
            shutil.copytree(self.actual_core, after)
            outputs = run_root / "outputs"
            outputs.mkdir()
            logical = f"riftpath://v1/project/subject_{index}.c"
            semantic_index = {
                "schema_version": "2.0.0", "artifact_id": f"index:{index}",
                "identity_scheme": "rift.identity/2.0.0",
                "translation_units": [{"tu_id": f"tu:{index}"}],
                "semantic_nodes": [{"node_id": f"node:{index}"}],
                "input_files": [{
                    "input_file_id": f"input:{index}",
                    "logical_path": logical, "role": "main",
                    "sha256": file_sha256(source_file),
                    "byte_size": source_file.stat().st_size,
                }],
                "status": "CONSERVATIVE_INCOMPLETE",
            }
            semantic_index["input_manifest_sha256"] = input_manifest_sha256(semantic_index)
            semantic_path = outputs / "semantic_index.json"
            write_json(semantic_path, semantic_index)
            bindings = {
                "schema_version": "1.0.0", "artifact_id": f"bindings:{index}",
                "property_ir_sha256": file_sha256(property_ir),
                "semantic_index_sha256": file_sha256(semantic_path),
                "bindings": [{"ap_id": f"ap:{index}"}],
            }
            bindings_path = outputs / "ap_bindings.json"
            write_json(bindings_path, bindings)
            graph = {
                "schema_version": "2.0.0", "artifact_id": f"graph:{index}",
                "semantic_index_sha256": file_sha256(semantic_path),
                "nodes": [{"node_id": f"cig:{index}"}], "edges": [],
                "status": "CONSERVATIVE_INCOMPLETE",
            }
            graph_path = outputs / "contextual_influence_graph.json"
            write_json(graph_path, graph)
            cones = {
                "schema_version": "1.0.0", "artifact_id": f"cones:{index}",
                "ap_bindings_sha256": file_sha256(bindings_path),
                "graph_sha256": file_sha256(graph_path),
                "cones": [{
                    "cone_id": f"cone:{index}",
                    "status": "CONSERVATIVE_INCOMPLETE",
                }],
            }
            cones_path = outputs / "ap_influence_cones.json"
            write_json(cones_path, cones)
            closure_path = outputs / "source_input_manifest.json"
            write_json(closure_path, {
                "schema_version": "2.0.0",
                "manifest_kind": "rift.source-input-closure",
                "input_manifest_sha256": semantic_index["input_manifest_sha256"],
                "entries": [{
                    "input_file_id": f"input:{index}",
                    "logical_path": logical, "physical_path": str(source_file),
                    "role": "main",
                    "sha256": file_sha256(source_file),
                    "byte_size": source_file.stat().st_size,
                }],
            })
            output_paths = {
                "semantic_index": semantic_path,
                "ap_bindings": bindings_path,
                "contextual_influence_graph": graph_path,
                "ap_influence_cones": cones_path,
            }
            output_digests = {kind: file_sha256(path) for kind, path in output_paths.items()}
            model_digest = file_sha256(model_pack)
            property_digest = file_sha256(property_ir)
            compile_digest = file_sha256(compile_database)
            source_inputs_digest = semantic_index["input_manifest_sha256"]
            stages = [
                self.stage("index", [compile_digest, source_inputs_digest], [output_digests["semantic_index"]]),
                self.stage("bind", [property_digest, output_digests["semantic_index"]], [output_digests["ap_bindings"]]),
                self.stage("influence", [output_digests["semantic_index"], output_digests["ap_bindings"]], [output_digests["contextual_influence_graph"]]),
                self.stage("cone", [output_digests["ap_bindings"], output_digests["contextual_influence_graph"]], [output_digests["ap_influence_cones"]]),
                self.stage("certificate", list(output_digests.values()), []),
            ]
            certificate_path = outputs / "analysis_certificate.json"
            certificate = {
                "schema_version": "2.0.0", "certificate_id": f"certificate:{index}",
                "analysis_id": f"analysis:{index}",
                "status": "CONSERVATIVE_INCOMPLETE",
                "analyzer": {
                    "name": "tafuzz-sa", "version": "0.1.0",
                    "binary_sha256": file_sha256(self.analyzer),
                    "configuration_sha256": "0" * 64,
                    "environment_sha256": "1" * 64,
                },
                "build_manifest": {
                    "identity_policy": "relative-path-and-content-v1",
                    "manifest_sha256": file_sha256(self.build_manifest),
                    "production_core_sha256": self.core_digest,
                    "schema_bundle_sha256": self.schema_digest,
                },
                "core_tree_sha256": self.core_digest,
                "schema_bundle_sha256": self.schema_digest,
                "environment": {
                    "digest": "1" * 64,
                    "variables": [{
                        "name": name, "present": False, "value_sha256": None,
                    } for name in (
                        "CL", "COMPILER_PATH", "CPATH", "CPLUS_INCLUDE_PATH",
                        "C_INCLUDE_PATH", "GCC_EXEC_PREFIX", "INCLUDE", "LANG",
                        "LC_ALL", "LC_CTYPE", "MACOSX_DEPLOYMENT_TARGET",
                        "OBJC_INCLUDE_PATH", "PATH", "SDKROOT",
                        "SOURCE_DATE_EPOCH", "_CL_",
                    )],
                },
                "inputs": [
                    self.digest_record("typed_property_ir", property_digest, property_ir, f"property:{index}"),
                    self.digest_record("compile_commands", compile_digest, compile_database, f"compile:{index}"),
                    self.digest_record("source_inputs", source_inputs_digest, None, f"inputs:{index}"),
                ],
                "outputs": [
                    self.digest_record(kind, digest, output_paths[kind],
                                       json.loads(output_paths[kind].read_text())["artifact_id"])
                    for kind, digest in output_digests.items()
                ],
                "stages": stages,
                "source_input_provenance": {
                    "manifest_sha256": source_inputs_digest,
                    "files": [{
                        "input_file_id": f"input:{index}",
                        "logical_path": logical, "role": "main",
                        "sha256": file_sha256(source_file),
                        "byte_size": source_file.stat().st_size,
                        "observed_paths": [str(source_file.resolve())],
                    }],
                },
                "toolchain": [{
                    "component_id": f"tool:{item['role']}",
                    "name": item["logical_name"], "version": item["version"],
                    "component_kind": "executable" if item["role"] in {"analyzer", "clang", "opt"} else "shared_object",
                    "sha256": item["sha256"],
                } for item in self.toolchain["components"]],
                "unsupported_constructs": [],
                "started_at": "2026-07-18T00:00:00Z",
                "finished_at": "2026-07-18T00:00:01Z",
            }
            write_json(certificate_path, certificate)
            manifest_path = run_root / "sealed_run.json"
            manifest = {
                "schema_version": "3.0.0",
                "manifest_kind": "rift.sealed-portability-run",
                "run_id": f"sealed-run-{index}",
                "project": {
                    "project_id": f"project-{index}",
                    "repository_id": f"fixture://repository/{index}",
                    "source_revision": f"revision-{index}",
                    "source_snapshot": artifact(source_root, directory=True),
                    "source_repository_manifest": artifact(repository_manifest),
                    "typed_property_ir": artifact(property_ir),
                    "compile_database": artifact(compile_database),
                    "model_pack": artifact(
                        model_pack,
                        non_comment_lines=sum(
                            1 for line in model_pack.read_text().splitlines()
                            if line.strip() and not line.lstrip().startswith(("#", "//"))
                        ),
                    ),
                    "setup_minutes": 0.25 + index,
                    "unsupported_constructs": [],
                },
                "execution": {
                    "exit_code": 0,
                    "analysis_status": "CONSERVATIVE_INCOMPLETE",
                    "wall_seconds": 0.5 + index,
                    "peak_rss_bytes": 4096 + index,
                    "analyzer_binary": artifact(self.analyzer),
                    "build_manifest": artifact(self.build_manifest),
                    "schema_bundle": {"path": str(self.schema_bundle), "sha256": self.schema_digest},
                    "core_before": {"path": str(before), "sha256": self.core_digest},
                    "core_after": {"path": str(after), "sha256": self.core_digest},
                },
                "artifacts": {
                    **{kind: artifact(path) for kind, path in output_paths.items()},
                    "source_input_manifest": artifact(closure_path),
                    "analysis_certificate": artifact(certificate_path),
                },
                "toolchain": copy.deepcopy(self.toolchain),
                "embedded_identities": {
                    "analyzer_binary_sha256": file_sha256(self.analyzer),
                    "build_manifest_sha256": file_sha256(self.build_manifest),
                    "core_tree_sha256": self.core_digest,
                    "schema_bundle_sha256": self.schema_digest,
                    "toolchain_semantics_sha256": self.toolchain_digest,
                },
            }
            write_json(manifest_path, manifest)
            projects.append({
                "sealed_run_manifest_path": str(manifest_path),
                "sealed_run_manifest_sha256": file_sha256(manifest_path),
            })
            manifests.append(manifest_path)
        return ({
            "schema_version": "3.0.0",
            "evidence_kind": "rift.portability-evaluation",
            "contract_id": "RIFT-PORTABILITY-1",
            "actual_core_root_path": str(self.actual_core),
            "projects": projects,
        }, manifests)

    @staticmethod
    def stage(name: str, inputs: list[str], outputs: list[str]) -> dict[str, object]:
        return {
            "stage_id": f"stage.{name}", "name": name,
            "status": "CONSERVATIVE_INCOMPLETE",
            "input_sha256": inputs, "output_sha256": outputs,
            "diagnostics": [],
        }

    @staticmethod
    def digest_record(
        kind: str, digest: str, path: Path | None, artifact_id: str,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "artifact_id": artifact_id, "kind": kind, "sha256": digest,
        }
        if path is not None:
            result["path"] = str(path)
        return result

    def reseal(self, index: int, manifest: dict[str, object]) -> None:
        path = self.manifest_paths[index]
        write_json(path, manifest)
        self.evidence["projects"][index]["sealed_run_manifest_sha256"] = file_sha256(path)

    def load_manifest(self, index: int) -> dict[str, object]:
        return json.loads(self.manifest_paths[index].read_text(encoding="utf-8"))

    def run_gate(self, evidence: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        evidence_path = self.root / "evidence.json"
        write_json(evidence_path, self.evidence if evidence is None else evidence)
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--phase", "evaluation", "--evidence", str(evidence_path)],
            cwd=WORKSPACE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, env={**dict(), "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def assert_gate_fails(self, needle: str, evidence: dict[str, object] | None = None) -> None:
        completed = self.run_gate(evidence)
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn(needle, completed.stderr)

    def test_synthetic_three_independent_project_fixture_passes(self) -> None:
        completed = self.run_gate()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("projects=3", completed.stdout)

    def test_handwritten_pass_v1_report_is_rejected(self) -> None:
        old = {
            "contract_id": "RIFT-PORTABILITY-1",
            "projects": [{"project_id": str(i), "analysis_status": "PASS"} for i in range(3)],
        }
        self.assert_gate_fails("artifact-backed schema 3.0.0", old)

    def test_swapped_analysis_certificate_is_rejected(self) -> None:
        manifest = self.load_manifest(0)
        other = self.load_manifest(1)["artifacts"]["analysis_certificate"]
        manifest["artifacts"]["analysis_certificate"] = copy.deepcopy(other)
        self.reseal(0, manifest)
        self.assert_gate_fails("inputs[typed_property_ir] digest mismatch")

    def test_empty_output_placeholder_is_rejected(self) -> None:
        manifest = self.load_manifest(0)
        path = Path(manifest["artifacts"]["ap_bindings"]["path"])
        value = json.loads(path.read_text())
        value["bindings"] = []
        write_json(path, value)
        manifest["artifacts"]["ap_bindings"]["sha256"] = file_sha256(path)
        self.reseal(0, manifest)
        self.assert_gate_fails("bindings must be non-empty")

    def test_same_repository_cannot_masquerade_as_three_projects(self) -> None:
        manifest = self.load_manifest(2)
        manifest["project"]["repository_id"] = "fixture://repository/0"
        repo_path = Path(manifest["project"]["source_repository_manifest"]["path"])
        repo = json.loads(repo_path.read_text())
        repo["repository_id"] = "fixture://repository/0"
        write_json(repo_path, repo)
        manifest["project"]["source_repository_manifest"]["sha256"] = file_sha256(repo_path)
        self.reseal(2, manifest)
        self.assert_gate_fails("duplicate repository_id")

    def test_hashing_one_schema_file_is_not_a_schema_bundle(self) -> None:
        manifest = self.load_manifest(0)
        tiny = self.root / "one-schema"
        tiny.mkdir()
        shutil.copy2(self.schema_bundle / "common.schema.json", tiny / "common.schema.json")
        manifest["execution"]["schema_bundle"] = artifact(tiny, directory=True)
        self.reseal(0, manifest)
        self.assert_gate_fails("does not exist in the verified tree")

    def test_core_change_between_before_and_after_is_rejected(self) -> None:
        manifest = self.load_manifest(0)
        after = Path(manifest["execution"]["core_after"]["path"])
        (after / "core" / "engine.cpp").write_text("int portable_engine() { return 2; }\n")
        self.reseal(0, manifest)
        self.assert_gate_fails("core_after.files")

    def test_missing_toolchain_component_is_rejected(self) -> None:
        manifest = self.load_manifest(0)
        manifest["toolchain"]["components"] = [
            item for item in manifest["toolchain"]["components"] if item["role"] != "z3"
        ]
        self.reseal(0, manifest)
        self.assert_gate_fails("missing toolchain roles")

    def test_fake_reported_hash_is_rejected(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["projects"][0]["sealed_run_manifest_sha256"] = "a" * 64
        self.assert_gate_fails("sealed_run_manifest_sha256 mismatch", evidence)


if __name__ == "__main__":
    unittest.main()
