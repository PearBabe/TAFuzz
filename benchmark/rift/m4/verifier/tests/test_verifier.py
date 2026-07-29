from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable


VERIFIER_PATH = Path(__file__).resolve().parents[1] / "verify.py"
TAFUZZ_ROOT = VERIFIER_PATH.parents[4]
SPEC = importlib.util.spec_from_file_location("rift_m4_verifier", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact_digest(path: Path) -> str:
    return digest(path.read_bytes())


class Bundle:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.inputs = root / "inputs"
        self.analysis = root / "analysis"
        self.analysis.mkdir(parents=True)
        self.binary = root / "tafuzz-sa"
        self.binary.write_bytes(b"independent analyzer fixture\n")
        self.argv = root / "argv.json"
        self.argv_value = [str(self.binary), "influence", "--fixture"]
        write_json(self.argv, self.argv_value)

        self.property_path = self.inputs / "property_ir.json"
        self.compile_path = self.inputs / "compile_commands.json"
        write_json(
            self.property_path,
            {
                "schema_version": "1.0.0",
                "artifact_id": "artifact.property.fixture",
                "property_id": "property.fixture",
                "atomic_propositions": [{"ap_id": "ap.fixture"}],
            },
        )
        write_json(self.compile_path, [])

        zero = "0" * 64
        identity_scheme = "rift.identity/2.0.0"
        main_path = "riftpath://v1/source/fixture.c"
        main_sha = digest(b"int fixture;\n")
        predefines_sha = digest(b"#define FIXTURE 1\n")
        predefines_path = f"riftpath://v1/toolchain/predefines/{predefines_sha}"
        manifest_files = [
            {
                "input_file_id": verifier.input_file_id(
                    identity_scheme, "main", main_path, main_sha
                ),
                "logical_path": main_path,
                "sha256": main_sha,
                "role": "main",
                "byte_size": len(b"int fixture;\n"),
            },
            {
                "input_file_id": verifier.input_file_id(
                    identity_scheme, "toolchain", predefines_path, predefines_sha
                ),
                "logical_path": predefines_path,
                "sha256": predefines_sha,
                "role": "toolchain",
                "byte_size": len(b"#define FIXTURE 1\n"),
            },
        ]
        manifest_sha = verifier.input_manifest_sha256(identity_scheme, manifest_files)
        index_identity = {
            "identity_scheme": identity_scheme,
            "canonical_compilation_database_sha256": zero,
            "path_map_sha256": "1" * 64,
            "input_manifest_sha256": manifest_sha,
        }
        self.documents: dict[str, dict[str, Any]] = {
            "semantic_index": {
                "schema_version": "2.0.0",
                "artifact_id": verifier.semantic_index_artifact_id(index_identity),
                "identity_scheme": identity_scheme,
                "compilation_database_sha256": artifact_digest(self.compile_path),
                "canonical_compilation_database_sha256": zero,
                "path_map_sha256": "1" * 64,
                "input_manifest_sha256": manifest_sha,
                "logical_root_ids": ["source"],
                "source_identity_root": f"rift.identity/2.0.0:{'1' * 64}",
                "translation_units": [
                    {
                        "tu_id": "tu:fixture",
                        "source_file": main_path,
                        "language": "c",
                        "working_directory": "riftpath://v1/source",
                        "command_sha256": "5" * 64,
                        "status": "indexed",
                        "input_file_ids": sorted(
                            item["input_file_id"] for item in manifest_files
                        ),
                        "diagnostics": [],
                    }
                ],
                "input_files": manifest_files,
                "entities": [],
                "abstract_objects": [],
                "semantic_nodes": [],
                "semantic_relations": [],
                "function_summaries": [],
                "callsites": [],
                "status": "COMPLETE",
                "diagnostics": [],
                "unsupported_constructs": [],
            },
            "ap_bindings": {
                "schema_version": "1.0.0",
                "artifact_id": "bindings:fixture",
                "property_ir_sha256": artifact_digest(self.property_path),
                "semantic_index_sha256": zero,
                "binding_policy": {
                    "joint_role_binding": True,
                    "similarity_is_confirmation": False,
                },
                "bindings": [
                    {
                        "ap_id": "ap.fixture",
                        "role": "guard",
                        "resolution": "CONFIRMED",
                        "candidates": [
                            {
                                "binding_id": "binding:fixture",
                                "status": "CONFIRMED",
                                "selector_refs": ["selector:fixture"],
                                "semantic_node_refs": ["semantic:root"],
                                "evidence": [],
                                "confidence": 1.0,
                                "uncertainty_reasons": [],
                            }
                        ],
                    }
                ],
                "unsupported_constructs": [],
            },
            "contextual_influence_graph": {
                "schema_version": "2.0.0",
                "artifact_id": "graph:fixture",
                "semantic_index_sha256": zero,
                "context_policy": {
                    "call_string_limit": 1,
                    "object_sensitivity": "hybrid",
                    "field_sensitivity": "full",
                    "unknowns_are_explicit": True,
                },
                "nodes": [
                    {"node_id": "node:source", "semantic_node_ref": "semantic:source"},
                    {"node_id": "node:middle", "semantic_node_ref": "semantic:middle"},
                    {"node_id": "node:root", "semantic_node_ref": "semantic:root"},
                ],
                "edges": [
                    {
                        "edge_id": "edge:first",
                        "source_node_id": "node:source",
                        "target_node_id": "node:middle",
                        "certainty": "must",
                        "condition_node_ids": [],
                    },
                    {
                        "edge_id": "edge:second",
                        "source_node_id": "node:middle",
                        "target_node_id": "node:root",
                        "certainty": "must",
                        "condition_node_ids": [],
                    },
                ],
                "status": "COMPLETE",
                "diagnostics": [],
                "unsupported_constructs": [],
            },
            "ap_influence_cones": {
                "schema_version": "1.0.0",
                "artifact_id": "cones:fixture",
                "ap_bindings_sha256": zero,
                "graph_sha256": zero,
                "candidate_accounting_complete": True,
                "ranking_never_prunes": True,
                "cones": [
                    {
                        "cone_id": "cone:fixture",
                        "ap_id": "ap.fixture",
                        "roles": ["guard"],
                        "candidate_accounting": [
                            {
                                "binding_id": "binding:fixture",
                                "disposition": "INCLUDED",
                                "root_node_ids": ["node:root"],
                                "uncertainty_reasons": [],
                            }
                        ],
                        "members": [
                            {
                                "node_id": "node:source",
                                "membership": "MUST_INFLUENCE",
                                "witness_edge_ids": ["edge:first", "edge:second"],
                                "uncertainty_reasons": [],
                            },
                            {
                                "node_id": "node:middle",
                                "membership": "MUST_INFLUENCE",
                                "witness_edge_ids": ["edge:second"],
                                "uncertainty_reasons": [],
                            },
                            {
                                "node_id": "node:root",
                                "membership": "MUST_INFLUENCE",
                                "witness_edge_ids": [],
                                "uncertainty_reasons": [],
                            },
                        ],
                        "edge_ids": ["edge:first", "edge:second"],
                        "status": "COMPLETE",
                        "uncertainty_reasons": [],
                    }
                ],
                "unsupported_constructs": [],
            },
        }
        self.certificate: dict[str, Any] = {}
        self.sync()

    def sync(self, *, preserve_stages: bool = False) -> None:
        names = verifier.OUTPUT_FILE_BY_KIND
        index_path = self.analysis / names["semantic_index"]
        write_json(index_path, self.documents["semantic_index"])
        index_sha = artifact_digest(index_path)
        self.documents["ap_bindings"]["semantic_index_sha256"] = index_sha
        self.documents["contextual_influence_graph"]["semantic_index_sha256"] = index_sha

        bindings_path = self.analysis / names["ap_bindings"]
        graph_path = self.analysis / names["contextual_influence_graph"]
        write_json(bindings_path, self.documents["ap_bindings"])
        write_json(graph_path, self.documents["contextual_influence_graph"])
        bindings_sha = artifact_digest(bindings_path)
        graph_sha = artifact_digest(graph_path)
        self.documents["ap_influence_cones"]["ap_bindings_sha256"] = bindings_sha
        self.documents["ap_influence_cones"]["graph_sha256"] = graph_sha

        cones_path = self.analysis / names["ap_influence_cones"]
        write_json(cones_path, self.documents["ap_influence_cones"])
        cones_sha = artifact_digest(cones_path)
        outputs = [
            {
                "artifact_id": self.documents[kind]["artifact_id"],
                "kind": kind,
                "sha256": artifact_digest(self.analysis / filename),
                "path": str(self.analysis / filename),
            }
            for kind, filename in names.items()
        ]
        output_sha = {item["kind"]: item["sha256"] for item in outputs}
        inputs = [
            {
                "artifact_id": "artifact.property.fixture",
                "kind": "typed_property_ir",
                "sha256": artifact_digest(self.property_path),
                "path": str(self.property_path),
            },
            {
                "artifact_id": "compile.database",
                "kind": "compile_commands",
                "sha256": artifact_digest(self.compile_path),
                "path": str(self.compile_path),
            },
        ]
        source_manifest = self.documents["semantic_index"].get("input_manifest_sha256")
        if verifier._is_sha256(source_manifest):
            inputs.append(
                {
                    "artifact_id": verifier.stable_id("input_manifest", source_manifest),
                    "kind": "source_inputs",
                    "sha256": source_manifest,
                }
            )
        index_inputs = [inputs[1]["sha256"]]
        if len(inputs) == 3:
            index_inputs.append(inputs[2]["sha256"])
        stages = [
            self._stage("index", index_inputs, [index_sha]),
            self._stage("bind", [inputs[0]["sha256"], index_sha], [bindings_sha]),
            self._stage("influence", [index_sha, bindings_sha], [graph_sha]),
            self._stage("cone", [bindings_sha, graph_sha], [cones_sha]),
            self._stage(
                "certificate",
                [
                    output_sha["semantic_index"],
                    output_sha["ap_bindings"],
                    output_sha["contextual_influence_graph"],
                    output_sha["ap_influence_cones"],
                ],
                [],
            ),
        ]
        union: dict[str, dict[str, Any]] = {}
        for document in self.documents.values():
            for gap in document.get("unsupported_constructs", []):
                union[gap["construct_id"]] = copy.deepcopy(gap)
        old_stages = self.certificate.get("stages")
        analysis_material = (
            ":".join(
                (
                    inputs[0]["sha256"],
                    source_manifest,
                    self.documents["semantic_index"][
                        "canonical_compilation_database_sha256"
                    ],
                    self.documents["semantic_index"]["path_map_sha256"],
                )
            )
            if verifier._is_sha256(source_manifest)
            else "legacy-fixture"
        )
        self.certificate = {
            "schema_version": "1.0.0",
            "certificate_id": "certificate:fixture",
            "analysis_id": verifier.stable_id("analysis", analysis_material),
            "status": "COMPLETE",
            "analyzer": {
                "name": "tafuzz-sa",
                "version": "0.1.0",
                "binary_sha256": artifact_digest(self.binary),
                "configuration_sha256": verifier.configuration_sha256(self.argv_value),
            },
            "core_tree_sha256": "3" * 64,
            "schema_bundle_sha256": "4" * 64,
            "inputs": inputs,
            "toolchain": [
                {
                    "component_id": "tool:fixture",
                    "name": "tafuzz-sa executable",
                    "version": "0.1.0",
                    "executable_sha256": artifact_digest(self.binary),
                }
            ],
            "outputs": outputs,
            "stages": old_stages if preserve_stages and old_stages else stages,
            "unsupported_constructs": list(union.values()),
            "started_at": "2026-07-18T00:00:00Z",
            "finished_at": "2026-07-18T00:00:01Z",
        }
        write_json(self.analysis / "analysis_certificate.json", self.certificate)

    @staticmethod
    def _stage(name: str, inputs: list[str], outputs: list[str]) -> dict[str, Any]:
        return {
            "stage_id": f"stage.{name}",
            "name": name,
            "status": "COMPLETE",
            "input_sha256": inputs,
            "output_sha256": outputs,
            "diagnostics": [],
        }

    def refresh_input_manifest(self) -> None:
        index = self.documents["semantic_index"]
        index["input_files"].sort(
            key=lambda item: (
                item["logical_path"],
                verifier.INPUT_ROLE_ORDER[item["role"]],
                item["sha256"],
                item["input_file_id"],
            )
        )
        index["input_manifest_sha256"] = verifier.input_manifest_sha256(
            index["identity_scheme"], index["input_files"]
        )
        index["artifact_id"] = verifier.semantic_index_artifact_id(index)

    def upgrade_bindings_to_role_dnf(self) -> None:
        property_document = {
            "schema_version": "2.0.0",
            "artifact_id": "artifact.property.fixture",
            "property_id": "property.fixture",
            "selectors": [
                {"selector_id": "selector:fixture"},
                {"selector_id": "selector:fallback"},
            ],
            "atomic_propositions": [
                {
                    "ap_id": "ap.fixture",
                    "roles": ["guard"],
                    "role_selector_groups": [
                        {
                            "group_id": "selector-group:primary",
                            "role": "guard",
                            "all_of": ["selector:fixture"],
                        },
                        {
                            "group_id": "selector-group:fallback",
                            "role": "guard",
                            "all_of": ["selector:fallback"],
                        },
                    ],
                }
            ],
        }
        write_json(self.property_path, property_document)

        bindings = self.documents["ap_bindings"]
        bindings["schema_version"] = "2.0.0"
        bindings["property_ir_sha256"] = artifact_digest(self.property_path)
        bindings["binding_policy"] = {
            "role_selector_logic": "role-dnf/1",
            "cross_role_consistency": "NOT_EVALUATED",
            "similarity_is_confirmation": False,
        }
        role_binding = bindings["bindings"][0]
        primary = role_binding["candidates"][0]
        primary["selector_group_id"] = "selector-group:primary"
        role_binding["candidates"].append(
            {
                "binding_id": "binding:fallback",
                "status": "CONFIRMED",
                "selector_group_id": "selector-group:fallback",
                "selector_refs": ["selector:fallback"],
                "semantic_node_refs": ["semantic:root"],
                "evidence": [],
                "confidence": 1.0,
                "uncertainty_reasons": [],
            }
        )
        cone = self.documents["ap_influence_cones"]["cones"][0]
        cone["candidate_accounting"].append(
            {
                "binding_id": "binding:fallback",
                "disposition": "INCLUDED",
                "root_node_ids": ["node:root"],
                "uncertainty_reasons": [],
            }
        )
        self.sync()

    def install_path_mask_fixture(self) -> None:
        node_ids = (
            "node:root",
            "node:must",
            "node:may",
            "node:modelled-middle",
            "node:modelled-source",
            "node:unknown",
            "node:mixed-modelled",
            "node:mixed-unknown",
            "node:cycle-a",
            "node:cycle-b",
        )
        graph = self.documents["contextual_influence_graph"]
        graph["nodes"] = [
            {"node_id": node_id, "semantic_node_ref": f"semantic:{node_id[5:]}"}
            for node_id in node_ids
        ]

        def edge(edge_id: str, source: str, target: str, certainty: str) -> dict[str, Any]:
            return {
                "edge_id": edge_id,
                "source_node_id": source,
                "target_node_id": target,
                "certainty": certainty,
                "condition_node_ids": [],
            }

        graph["edges"] = [
            edge("edge:must", "node:must", "node:root", "must"),
            edge("edge:may-must", "node:may", "node:root", "must"),
            edge("edge:may-weak", "node:may", "node:root", "may"),
            edge(
                "edge:modelled-middle",
                "node:modelled-middle",
                "node:root",
                "modelled",
            ),
            edge(
                "edge:modelled-source",
                "node:modelled-source",
                "node:modelled-middle",
                "must",
            ),
            edge("edge:unknown", "node:unknown", "node:root", "unknown"),
            edge(
                "edge:mixed-modelled-must",
                "node:mixed-modelled",
                "node:root",
                "must",
            ),
            edge(
                "edge:mixed-modelled-weak",
                "node:mixed-modelled",
                "node:root",
                "modelled",
            ),
            edge(
                "edge:mixed-unknown-must",
                "node:mixed-unknown",
                "node:root",
                "must",
            ),
            edge(
                "edge:mixed-unknown-weak",
                "node:mixed-unknown",
                "node:root",
                "unknown",
            ),
            edge("edge:cycle-root", "node:cycle-a", "node:root", "must"),
            edge("edge:cycle-forward", "node:cycle-b", "node:cycle-a", "must"),
            edge("edge:cycle-back", "node:cycle-a", "node:cycle-b", "may"),
            # This alternate cycle points back into the observation root.  The
            # fixed-point contract keeps roots fixed instead of weakening them.
            edge("edge:root-fixed", "node:root", "node:must", "unknown"),
        ]

        cone = self.documents["ap_influence_cones"]["cones"][0]
        cone["status"] = "CONSERVATIVE_INCOMPLETE"
        cone["uncertainty_reasons"] = ["path masks retain unknown provenance"]
        cone["candidate_accounting"][0]["root_node_ids"] = ["node:root"]
        cone["members"] = [
            {
                "node_id": "node:root",
                "membership": "MUST_INFLUENCE",
                "witness_edge_ids": [],
                "uncertainty_reasons": [],
            },
            {
                "node_id": "node:must",
                "membership": "MUST_INFLUENCE",
                "witness_edge_ids": ["edge:must"],
                "uncertainty_reasons": [],
            },
            {
                "node_id": "node:may",
                "membership": "MAY_INFLUENCE",
                "witness_edge_ids": ["edge:may-must"],
                "uncertainty_reasons": [],
            },
            {
                "node_id": "node:modelled-middle",
                "membership": "MODELLED_INFLUENCE",
                "witness_edge_ids": ["edge:modelled-middle"],
                "uncertainty_reasons": [],
            },
            {
                "node_id": "node:modelled-source",
                "membership": "MODELLED_INFLUENCE",
                "witness_edge_ids": [
                    "edge:modelled-source",
                    "edge:modelled-middle",
                ],
                "uncertainty_reasons": [],
            },
            {
                "node_id": "node:unknown",
                "membership": "UNKNOWN_INFLUENCE",
                "witness_edge_ids": ["edge:unknown"],
                "uncertainty_reasons": ["only path certainty is unknown"],
            },
            {
                "node_id": "node:mixed-modelled",
                "membership": "MAY_INFLUENCE",
                "witness_edge_ids": ["edge:mixed-modelled-must"],
                "uncertainty_reasons": [],
            },
            {
                "node_id": "node:mixed-unknown",
                "membership": "MAY_INFLUENCE",
                "witness_edge_ids": ["edge:mixed-unknown-must"],
                "uncertainty_reasons": ["alternate path certainty is unknown"],
            },
            {
                "node_id": "node:cycle-a",
                "membership": "MAY_INFLUENCE",
                "witness_edge_ids": ["edge:cycle-root"],
                "uncertainty_reasons": ["alternate influence path contains a cycle"],
            },
            {
                "node_id": "node:cycle-b",
                "membership": "MAY_INFLUENCE",
                "witness_edge_ids": ["edge:cycle-forward", "edge:cycle-root"],
                "uncertainty_reasons": ["alternate influence path contains a cycle"],
            },
        ]
        cone["edge_ids"] = sorted(
            {
                edge_id
                for member in cone["members"]
                for edge_id in member["witness_edge_ids"]
            }
        )
        self.sync()
        self.mark_conservative("cone")

    def mark_conservative(self, *stage_names: str) -> None:
        for stage in self.certificate["stages"]:
            if stage["name"] in set(stage_names):
                stage["status"] = "CONSERVATIVE_INCOMPLETE"
        self.certificate["stages"][-1]["status"] = "CONSERVATIVE_INCOMPLETE"
        self.certificate["status"] = "CONSERVATIVE_INCOMPLETE"
        self.write_certificate()

    def write_certificate(self) -> None:
        write_json(self.analysis / "analysis_certificate.json", self.certificate)

    def verify(self, strict: bool = False) -> dict[str, Any]:
        return verifier.verify_analysis(
            self.analysis,
            binary=self.binary,
            argv_json=self.argv,
            strict_provenance=strict,
        )


class V2Bundle(Bundle):
    """Self-contained Certificate v2 fixture with independently hashable bytes."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.implementation = root / "implementation"
        self.build_manifest = root / "rift_build_manifest.json"
        self.environment = root / "environment.json"
        self.main_source = root / "source" / "fixture.c"
        self.main_source.parent.mkdir(parents=True)
        self.main_source.write_bytes(b"int fixture;\n")
        self._create_implementation_snapshot()
        self._upgrade_certificate()

    @staticmethod
    def _tree_digest(root: Path, paths: list[Path]) -> tuple[str, list[dict[str, str]]]:
        aggregate = hashlib.sha256()
        records: list[dict[str, str]] = []
        for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
            relative = path.relative_to(root).as_posix()
            relative_bytes = relative.encode("utf-8")
            payload = path.read_bytes()
            aggregate.update(len(relative_bytes).to_bytes(8, "big"))
            aggregate.update(relative_bytes)
            aggregate.update(len(payload).to_bytes(8, "big"))
            aggregate.update(payload)
            records.append({"path": relative, "sha256": digest(payload)})
        return aggregate.hexdigest(), records

    def _create_implementation_snapshot(self) -> None:
        core_paths: list[Path] = []
        for relative in verifier.BUILD_MANIFEST_CORE_FILES:
            path = self.implementation / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture production input: {relative}\n", encoding="utf-8")
            core_paths.append(path)
        include = self.implementation / "include" / "rift" / "core" / "fixture.h"
        include.parent.mkdir(parents=True, exist_ok=True)
        include.write_text("#pragma once\n", encoding="utf-8")
        core_paths.append(include)

        source_schema = (
            TAFUZZ_ROOT
            / "src"
            / "StaticAnalysis"
            / "schema"
            / "analysis_certificate.schema.json"
        )
        schema = self.implementation / "schema" / source_schema.name
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_bytes(source_schema.read_bytes())
        if artifact_digest(schema) != verifier.EXPECTED_CERTIFICATE_V2_SCHEMA_SHA256:
            raise AssertionError("workspace Certificate v2 schema is no longer frozen")

        core_digest, core_records = self._tree_digest(self.implementation, core_paths)
        schema_digest, schema_records = self._tree_digest(self.implementation, [schema])
        manifest = {
            "schema_version": "rift.build-manifest.v1",
            "identity_policy": "relative-path-and-content-v1",
            "production_core_sha256": core_digest,
            "schema_bundle_sha256": schema_digest,
            "production_core_files": core_records,
            "schema_files": schema_records,
        }
        write_json(self.build_manifest, manifest)
        self.manifest = manifest
        self.manifest_sha256 = artifact_digest(self.build_manifest)

        base_binary = Path("/bin/true")
        if not base_binary.is_file():
            raise unittest.SkipTest("/bin/true is required for the runtime-map fixture")
        commitments = (
            manifest["identity_policy"],
            core_digest,
            schema_digest,
            self.manifest_sha256,
        )
        self.binary.write_bytes(
            base_binary.read_bytes()
            + b"\0RIFT-CERT-V2-FIXTURE\0"
            + b"\0".join(value.encode("ascii") for value in commitments)
        )
        self.binary.chmod(0o755)

    def _toolchain(self) -> list[dict[str, str]]:
        physical = [self.binary.resolve(), *verifier._ldd_runtime_files(self.binary)]
        unique: list[Path] = []
        identities: set[tuple[int, int]] = set()
        for path in physical:
            metadata = path.stat()
            identity = (metadata.st_dev, metadata.st_ino)
            if identity not in identities:
                identities.add(identity)
                unique.append(path)
        result: list[dict[str, str]] = []
        for path in unique:
            is_analyzer = path == self.binary.resolve()
            kind = "executable" if is_analyzer else "shared_object"
            name = "tafuzz-sa executable" if is_analyzer else path.name
            version = "0.1.0; fixture" if is_analyzer else path.name
            content_digest = artifact_digest(path)
            result.append(
                {
                    "component_id": verifier.stable_id(
                        "tool",
                        verifier.length_prefixed_material(
                            [kind, name, version, content_digest]
                        ),
                    ),
                    "component_kind": kind,
                    "name": name,
                    "version": version,
                    "sha256": content_digest,
                }
            )
        return sorted(
            result,
            key=lambda item: (
                item["component_kind"],
                item["name"],
                item["version"],
                item["sha256"],
            ),
        )

    def _upgrade_certificate(self) -> None:
        raw_environment = {name: None for name in verifier.SEMANTIC_ENVIRONMENT_VARIABLES}
        write_json(self.environment, raw_environment)
        environment_variables = [
            {"name": name, "present": False, "value_sha256": None}
            for name in verifier.SEMANTIC_ENVIRONMENT_VARIABLES
        ]
        environment_digest = verifier.environment_sha256(environment_variables)
        self.argv_value = [str(self.binary), "influence", "--fixture"]
        write_json(self.argv, self.argv_value)

        index = self.documents["semantic_index"]
        source_manifest = index["input_manifest_sha256"]
        provenance_files = []
        for item in index["input_files"]:
            record = copy.deepcopy(item)
            record["observed_paths"] = (
                [str(self.main_source.resolve())] if item["role"] == "main" else []
            )
            provenance_files.append(record)

        inputs = copy.deepcopy(self.certificate["inputs"])
        outputs = copy.deepcopy(self.certificate["outputs"])
        stages = copy.deepcopy(self.certificate["stages"])
        property_digest = inputs[0]["sha256"]
        analysis_id = verifier.stable_id(
            "analysis",
            verifier.length_prefixed_material(
                [
                    property_digest,
                    source_manifest,
                    index["canonical_compilation_database_sha256"],
                    index["path_map_sha256"],
                ]
            ),
        )
        configuration_digest = verifier.configuration_v2_sha256(
            self.manifest_sha256, environment_digest, self.argv_value
        )
        output_digests = [item["sha256"] for item in outputs]
        certificate_id = verifier.stable_id(
            "certificate",
            verifier.length_prefixed_material(
                [analysis_id, configuration_digest, *output_digests]
            ),
        )
        self.certificate = {
            "schema_version": "2.0.0",
            "certificate_id": certificate_id,
            "analysis_id": analysis_id,
            "status": "COMPLETE",
            "analyzer": {
                "name": "tafuzz-sa",
                "version": "0.1.0",
                "binary_sha256": artifact_digest(self.binary),
                "configuration_sha256": configuration_digest,
                "environment_sha256": environment_digest,
            },
            "build_manifest": {
                "identity_policy": self.manifest["identity_policy"],
                "manifest_sha256": self.manifest_sha256,
                "production_core_sha256": self.manifest["production_core_sha256"],
                "schema_bundle_sha256": self.manifest["schema_bundle_sha256"],
            },
            "core_tree_sha256": self.manifest["production_core_sha256"],
            "schema_bundle_sha256": self.manifest["schema_bundle_sha256"],
            "environment": {
                "digest": environment_digest,
                "variables": environment_variables,
            },
            "inputs": inputs,
            "source_input_provenance": {
                "manifest_sha256": source_manifest,
                "files": provenance_files,
            },
            "toolchain": self._toolchain(),
            "outputs": outputs,
            "stages": stages,
            "unsupported_constructs": [],
            "started_at": "2026-07-18T00:00:00Z",
            "finished_at": "2026-07-18T00:00:01Z",
        }
        self.write_certificate()

    def verify(self, strict: bool = True) -> dict[str, Any]:
        return verifier.verify_analysis(
            self.analysis,
            binary=self.binary,
            argv_json=self.argv,
            implementation_root=self.implementation,
            build_manifest_path=self.build_manifest,
            environment_json=self.environment,
            strict_provenance=strict,
        )


class VerifierTests(unittest.TestCase):
    def with_bundle(self, action: Callable[[Bundle], None]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-test-") as directory:
            bundle = Bundle(Path(directory))
            action(bundle)
            return bundle.verify()

    def with_v2_bundle(self, action: Callable[[V2Bundle], None]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-v2-test-") as directory:
            bundle = V2Bundle(Path(directory))
            action(bundle)
            return bundle.verify()

    def with_role_dnf_bundle(self, action: Callable[[Bundle], None]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-dnf-test-") as directory:
            bundle = Bundle(Path(directory))
            bundle.upgrade_bindings_to_role_dnf()
            action(bundle)
            return bundle.verify()

    @staticmethod
    def failure_ids(report: dict[str, Any]) -> set[str]:
        return {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "FAIL"
        }

    def test_v1_certificate_with_v2_artifacts_passes_compatibility_audit(self) -> None:
        report = self.with_bundle(lambda bundle: None)
        self.assertEqual(report["overall_status"], "PASS_WITH_UNSUPPORTED_ASSURANCE")
        self.assertEqual(report["failure_count"], 0)
        unsupported = {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "UNSUPPORTED"
        }
        self.assertIn("source.build_time_binding", unsupported)

    def test_role_dnf_bindings_pass_strict_certificate_v2_chain(self) -> None:
        def upgrade(bundle: V2Bundle) -> None:
            bundle.upgrade_bindings_to_role_dnf()
            bundle._upgrade_certificate()

        report = self.with_v2_bundle(upgrade)
        self.assertEqual(report["overall_status"], "PASS")
        passed = {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "PASS"
        }
        self.assertTrue(
            {
                "formats.bindings",
                "bindings.group_closure",
                "bindings.candidate_groups",
                "soundness.binding_resolution",
                "artifacts.internal_chain",
                "stages.closure",
                "certificate.identity_v2",
            }.issubset(passed)
        )

    def test_role_dnf_missing_group_accounting_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            binding["candidates"] = binding["candidates"][:1]
            cone = bundle.documents["ap_influence_cones"]["cones"][0]
            cone["candidate_accounting"] = cone["candidate_accounting"][:1]
            bundle.sync()

        report = self.with_role_dnf_bundle(mutate)
        self.assertIn("bindings.group_closure", self.failure_ids(report))

    def test_role_dnf_candidate_group_id_must_resolve_in_same_ap_role(self) -> None:
        def mutate(bundle: Bundle) -> None:
            candidate = bundle.documents["ap_bindings"]["bindings"][0][
                "candidates"
            ][1]
            candidate["selector_group_id"] = "selector-group:absent"
            bundle.sync()

        report = self.with_role_dnf_bundle(mutate)
        failures = self.failure_ids(report)
        self.assertIn("bindings.group_closure", failures)
        self.assertIn("bindings.candidate_groups", failures)

    def test_role_dnf_candidate_selectors_must_equal_group_all_of(self) -> None:
        def mutate(bundle: Bundle) -> None:
            candidate = bundle.documents["ap_bindings"]["bindings"][0][
                "candidates"
            ][1]
            candidate["selector_refs"] = ["selector:fixture"]
            bundle.sync()

        report = self.with_role_dnf_bundle(mutate)
        self.assertIn("bindings.candidate_groups", self.failure_ids(report))

    def test_role_dnf_resolution_is_derived_from_group_states(self) -> None:
        def mutate(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            binding["resolution"] = "PARTIAL"
            bundle.sync()
            bundle.mark_conservative("bind")

        report = self.with_role_dnf_bundle(mutate)
        self.assertIn("soundness.binding_resolution", self.failure_ids(report))

    def test_role_dnf_partial_resolution_is_conservative_and_valid(self) -> None:
        def mutate(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            binding["resolution"] = "PARTIAL"
            fallback = binding["candidates"][1]
            fallback["status"] = "UNRESOLVED"
            fallback["semantic_node_refs"] = []
            cone_document = bundle.documents["ap_influence_cones"]
            cone_document["cones"][0]["status"] = "CONSERVATIVE_INCOMPLETE"
            for member in cone_document["cones"][0]["members"]:
                member["membership"] = "MAY_INFLUENCE"
            account = cone_document["cones"][0]["candidate_accounting"][1]
            account["disposition"] = "UNRESOLVED"
            account["root_node_ids"] = []
            bundle.sync()
            bundle.mark_conservative("bind", "cone")

        report = self.with_role_dnf_bundle(mutate)
        self.assertEqual(report["failure_count"], 0)

    def test_role_dnf_ambiguous_and_unresolved_resolutions_are_valid(self) -> None:
        def ambiguous(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            primary = binding["candidates"][0]
            primary["status"] = "CANDIDATE"
            alternate = copy.deepcopy(primary)
            alternate["binding_id"] = "binding:primary-alternate"
            binding["candidates"].append(alternate)
            fallback = binding["candidates"][1]
            fallback["status"] = "UNRESOLVED"
            fallback["semantic_node_refs"] = []
            binding["resolution"] = "AMBIGUOUS"
            cone_document = bundle.documents["ap_influence_cones"]
            cone = cone_document["cones"][0]
            cone["status"] = "CONSERVATIVE_INCOMPLETE"
            for member in cone["members"]:
                member["membership"] = "MAY_INFLUENCE"
            cone["candidate_accounting"].append(
                {
                    "binding_id": "binding:primary-alternate",
                    "disposition": "INCLUDED",
                    "root_node_ids": ["node:root"],
                    "uncertainty_reasons": [],
                }
            )
            fallback_account = cone["candidate_accounting"][1]
            fallback_account["disposition"] = "UNRESOLVED"
            fallback_account["root_node_ids"] = []
            bundle.sync()
            bundle.mark_conservative("bind", "cone")

        ambiguous_report = self.with_role_dnf_bundle(ambiguous)
        self.assertEqual(ambiguous_report["failure_count"], 0)

        def unresolved(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            binding["resolution"] = "UNRESOLVED"
            for candidate in binding["candidates"]:
                candidate["status"] = "UNRESOLVED"
                candidate["semantic_node_refs"] = []
            cone_document = bundle.documents["ap_influence_cones"]
            cone = cone_document["cones"][0]
            cone["status"] = "CONSERVATIVE_INCOMPLETE"
            cone["members"] = []
            cone["edge_ids"] = []
            for account in cone["candidate_accounting"]:
                account["disposition"] = "UNRESOLVED"
                account["root_node_ids"] = []
            bundle.sync()
            bundle.mark_conservative("bind", "cone")

        unresolved_report = self.with_role_dnf_bundle(unresolved)
        self.assertEqual(unresolved_report["failure_count"], 0)

    def test_role_dnf_single_candidate_status_is_not_ambiguous(self) -> None:
        def mutate(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            primary = binding["candidates"][0]
            primary["status"] = "CANDIDATE"
            fallback = binding["candidates"][1]
            fallback["status"] = "UNRESOLVED"
            fallback["semantic_node_refs"] = []
            binding["resolution"] = "AMBIGUOUS"
            bundle.sync()
            bundle.mark_conservative("bind")

        report = self.with_role_dnf_bundle(mutate)
        self.assertIn("soundness.binding_resolution", self.failure_ids(report))

    def test_role_dnf_binding_to_cone_digest_chain_rejects_relabelled_bytes(self) -> None:
        def mutate(bundle: Bundle) -> None:
            cones_path = bundle.analysis / "ap_influence_cones.json"
            cones = copy.deepcopy(bundle.documents["ap_influence_cones"])
            cones["ap_bindings_sha256"] = "f" * 64
            write_json(cones_path, cones)
            cones_sha = artifact_digest(cones_path)
            descriptor = next(
                item
                for item in bundle.certificate["outputs"]
                if item["kind"] == "ap_influence_cones"
            )
            descriptor["sha256"] = cones_sha
            bundle.certificate["stages"][3]["output_sha256"] = [cones_sha]
            bundle.certificate["stages"][4]["input_sha256"][3] = cones_sha
            bundle.write_certificate()

        report = self.with_role_dnf_bundle(mutate)
        self.assertIn("artifacts.internal_chain", self.failure_ids(report))

    def test_cone_four_class_path_mask_fixed_point_passes(self) -> None:
        report = self.with_bundle(lambda bundle: bundle.install_path_mask_fixture())
        self.assertEqual(report["failure_count"], 0)
        passed = {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "PASS"
        }
        self.assertIn("cones.membership_fixed_point", passed)

    def test_cone_fixed_point_rejects_tampered_membership(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.install_path_mask_fixture()
            cone = bundle.documents["ap_influence_cones"]["cones"][0]
            member = next(
                item for item in cone["members"] if item["node_id"] == "node:modelled-source"
            )
            member["membership"] = "MUST_INFLUENCE"
            bundle.sync()
            bundle.mark_conservative("cone")

        report = self.with_bundle(mutate)
        self.assertIn("cones.membership_fixed_point", self.failure_ids(report))

    def test_cone_fixed_point_rejects_missing_reachable_member(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.install_path_mask_fixture()
            cone = bundle.documents["ap_influence_cones"]["cones"][0]
            cone["members"] = [
                item
                for item in cone["members"]
                if item["node_id"] != "node:mixed-unknown"
            ]
            cone["edge_ids"].remove("edge:mixed-unknown-must")
            bundle.sync()
            bundle.mark_conservative("cone")

        report = self.with_bundle(mutate)
        self.assertIn("cones.membership_fixed_point", self.failure_ids(report))

    def test_cone_fixed_point_rejects_graph_certainty_tampering(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.install_path_mask_fixture()
            edge = next(
                item
                for item in bundle.documents["contextual_influence_graph"]["edges"]
                if item["edge_id"] == "edge:modelled-middle"
            )
            edge["certainty"] = "must"
            bundle.sync()
            bundle.mark_conservative("cone")

        report = self.with_bundle(mutate)
        self.assertIn("cones.membership_fixed_point", self.failure_ids(report))

    def test_cone_fixed_point_rejects_unknown_mask_without_reason(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.install_path_mask_fixture()
            cone = bundle.documents["ap_influence_cones"]["cones"][0]
            member = next(
                item for item in cone["members"] if item["node_id"] == "node:unknown"
            )
            member["uncertainty_reasons"] = []
            bundle.sync()
            bundle.mark_conservative("cone")

        report = self.with_bundle(mutate)
        self.assertIn("cones.membership_fixed_point", self.failure_ids(report))

    def test_cone_root_is_must_only_when_fully_confirmed(self) -> None:
        def mutate(bundle: Bundle) -> None:
            binding = bundle.documents["ap_bindings"]["bindings"][0]
            binding["resolution"] = "AMBIGUOUS"
            binding["candidates"][0]["status"] = "CANDIDATE"
            alternate = copy.deepcopy(binding["candidates"][0])
            alternate["binding_id"] = "binding:alternate-root"
            binding["candidates"].append(alternate)
            cone = bundle.documents["ap_influence_cones"]["cones"][0]
            cone["status"] = "CONSERVATIVE_INCOMPLETE"
            cone["uncertainty_reasons"] = ["root is not uniquely fully confirmed"]
            cone["candidate_accounting"].append(
                {
                    "binding_id": "binding:alternate-root",
                    "disposition": "INCLUDED",
                    "root_node_ids": ["node:root"],
                    "uncertainty_reasons": [],
                }
            )
            bundle.sync()
            bundle.mark_conservative("bind", "cone")

        report = self.with_bundle(mutate)
        failures = self.failure_ids(report)
        self.assertIn("cones.membership_fixed_point", failures)
        self.assertNotIn("soundness.binding_resolution", failures)
        passed = {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "PASS"
        }
        self.assertIn("source.input_manifest", passed)

    def test_certificate_v2_strict_physical_replay_passes(self) -> None:
        report = self.with_v2_bundle(lambda bundle: None)
        self.assertEqual(report["overall_status"], "PASS")
        self.assertEqual(report["failure_count"], 0)
        self.assertEqual(report["unsupported_count"], 0)
        passed = {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "PASS"
        }
        self.assertTrue(
            {
                "build_manifest.source_tree",
                "build_manifest.binary_embedding",
                "environment.raw_values",
                "toolchain.physical_files",
                "source.physical_provenance",
                "certificate.identity_v2",
            }.issubset(passed)
        )

    def test_certificate_v2_rejects_changed_build_source(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            path = bundle.implementation / verifier.BUILD_MANIFEST_CORE_FILES[0]
            path.write_bytes(path.read_bytes() + b"changed\n")

        report = self.with_v2_bundle(mutate)
        self.assertIn("build_manifest.source_tree", self.failure_ids(report))

    def test_certificate_v2_rejects_changed_frozen_schema_bytes(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            path = (
                bundle.implementation
                / "schema"
                / "analysis_certificate.schema.json"
            )
            path.write_bytes(path.read_bytes() + b" ")

        report = self.with_v2_bundle(mutate)
        self.assertIn("build_manifest.source_tree", self.failure_ids(report))

    def test_certificate_v2_rejects_changed_generated_manifest_bytes(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            bundle.build_manifest.write_bytes(bundle.build_manifest.read_bytes() + b" ")

        report = self.with_v2_bundle(mutate)
        self.assertIn("build_manifest.file", self.failure_ids(report))

    def test_certificate_v2_rejects_unembedded_build_commitment(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            old = bundle.manifest_sha256.encode("ascii")
            payload = bundle.binary.read_bytes()
            self.assertIn(old, payload)
            bundle.binary.write_bytes(payload.replace(old, b"f" * 64, 1))
            binary_digest = artifact_digest(bundle.binary)
            bundle.certificate["analyzer"]["binary_sha256"] = binary_digest
            component = next(
                item
                for item in bundle.certificate["toolchain"]
                if item["name"] == "tafuzz-sa executable"
            )
            component["sha256"] = binary_digest
            component["component_id"] = verifier.stable_id(
                "tool",
                verifier.length_prefixed_material(
                    [
                        component["component_kind"],
                        component["name"],
                        component["version"],
                        component["sha256"],
                    ]
                ),
            )
            bundle.write_certificate()

        report = self.with_v2_bundle(mutate)
        self.assertIn("build_manifest.binary_embedding", self.failure_ids(report))

    def test_certificate_v2_rejects_wrong_raw_environment(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            values = json.loads(bundle.environment.read_text(encoding="utf-8"))
            values["PATH"] = "/different/toolchain"
            write_json(bundle.environment, values)

        report = self.with_v2_bundle(mutate)
        self.assertIn("environment.raw_values", self.failure_ids(report))

    def test_certificate_v2_rejects_wrong_exact_argv(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            write_json(bundle.argv, [*bundle.argv_value, "--different"])

        report = self.with_v2_bundle(mutate)
        self.assertIn(
            "analyzer.configuration_reconstruction", self.failure_ids(report)
        )

    def test_certificate_v2_rejects_relabelled_runtime_file(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            component = next(
                item
                for item in bundle.certificate["toolchain"]
                if item["name"] != "tafuzz-sa executable"
            )
            component["name"] = "not-the-mapped-file.so"
            component["version"] = component["name"]
            component["component_id"] = verifier.stable_id(
                "tool",
                verifier.length_prefixed_material(
                    [
                        component["component_kind"],
                        component["name"],
                        component["version"],
                        component["sha256"],
                    ]
                ),
            )
            bundle.write_certificate()

        report = self.with_v2_bundle(mutate)
        self.assertIn("toolchain.physical_files", self.failure_ids(report))

    def test_certificate_v2_rejects_changed_source_bytes(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            bundle.main_source.write_bytes(b"int changed;\n")

        report = self.with_v2_bundle(mutate)
        self.assertIn("source.physical_provenance", self.failure_ids(report))

    def test_certificate_v2_rejects_source_provenance_projection_change(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            bundle.certificate["source_input_provenance"]["files"].reverse()
            bundle.write_certificate()

        report = self.with_v2_bundle(mutate)
        self.assertIn("source.physical_provenance", self.failure_ids(report))

    def test_certificate_v2_rejects_certificate_id_change(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            bundle.certificate["certificate_id"] = "certificate:" + "f" * 64
            bundle.write_certificate()

        report = self.with_v2_bundle(mutate)
        self.assertIn("certificate.identity_v2", self.failure_ids(report))

    def test_certificate_v2_rejects_input_and_output_reordering(self) -> None:
        def mutate(bundle: V2Bundle) -> None:
            bundle.certificate["inputs"][0], bundle.certificate["inputs"][1] = (
                bundle.certificate["inputs"][1],
                bundle.certificate["inputs"][0],
            )
            bundle.certificate["outputs"][0], bundle.certificate["outputs"][1] = (
                bundle.certificate["outputs"][1],
                bundle.certificate["outputs"][0],
            )
            bundle.write_certificate()

        report = self.with_v2_bundle(mutate)
        failures = self.failure_ids(report)
        self.assertIn("artifacts.inputs", failures)
        self.assertIn("artifacts.outputs", failures)

    def test_canonical_v2_index_needs_no_raw_compile_db_field(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.documents["semantic_index"].pop("compilation_database_sha256")
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertEqual(report["failure_count"], 0)

    def test_input_byte_tampering_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.compile_path.write_bytes(b"tampered\n")

        report = self.with_bundle(mutate)
        self.assertIn("artifacts.input_bytes", self.failure_ids(report))

    def test_output_byte_tampering_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            path = bundle.analysis / "semantic_index.json"
            path.write_bytes(path.read_bytes() + b" ")

        report = self.with_bundle(mutate)
        self.assertIn("artifacts.output_bytes", self.failure_ids(report))

    def test_missing_stage_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.certificate["stages"] = bundle.certificate["stages"][:-1]
            bundle.write_certificate()

        report = self.with_bundle(mutate)
        self.assertIn("stages.topology", self.failure_ids(report))

    def test_missing_certificate_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-test-") as directory:
            analysis = Path(directory) / "analysis"
            analysis.mkdir()
            report = verifier.verify_analysis(analysis)
        self.assertEqual(report["overall_status"], "FAIL")
        self.assertIn("certificate.exists", self.failure_ids(report))

    def test_empty_global_outputs_fail(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.certificate["outputs"] = []
            bundle.write_certificate()

        report = self.with_bundle(mutate)
        self.assertIn("artifacts.outputs", self.failure_ids(report))

    def test_non_certificate_stage_empty_output_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.certificate["stages"][0]["output_sha256"] = []
            bundle.write_certificate()

        report = self.with_bundle(mutate)
        failures = self.failure_ids(report)
        self.assertTrue({"stages.closure", "stages.nonempty_outputs"} & failures)

    def test_stage_digest_closure_tampering_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.certificate["stages"][2]["input_sha256"].reverse()
            bundle.write_certificate()

        report = self.with_bundle(mutate)
        self.assertIn("stages.closure", self.failure_ids(report))

    def test_fake_complete_with_soundness_gap_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.documents["contextual_influence_graph"]["unsupported_constructs"] = [
                {
                    "construct_id": "gap:fixture",
                    "kind": "unknown_callback",
                    "effect": "soundness_risk",
                    "detail": "callback target unresolved",
                    "locations": [],
                }
            ]
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("soundness.status", self.failure_ids(report))

    def test_fake_confirmed_binding_without_confirmed_candidate_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            candidate = bundle.documents["ap_bindings"]["bindings"][0]["candidates"][0]
            candidate["status"] = "UNRESOLVED"
            candidate["semantic_node_refs"] = []
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("soundness.binding_resolution", self.failure_ids(report))

    def test_changed_header_digest_must_change_manifest(self) -> None:
        def mutate(bundle: Bundle) -> None:
            index = bundle.documents["semantic_index"]
            header = index["input_files"][0]
            old_id = header["input_file_id"]
            header["sha256"] = digest(b"changed input bytes\n")
            header["byte_size"] = len(b"changed input bytes\n")
            header["input_file_id"] = verifier.input_file_id(
                index["identity_scheme"],
                header["role"],
                header["logical_path"],
                header["sha256"],
            )
            unit = index["translation_units"][0]
            unit["input_file_ids"] = sorted(
                header["input_file_id"] if item == old_id else item
                for item in unit["input_file_ids"]
            )
            # Deliberately retain input_manifest_sha256/artifact_id: this is the
            # forbidden "changed header, unchanged manifest" claim.
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("source.input_manifest", self.failure_ids(report))

    def test_same_logical_path_same_digest_different_role_is_allowed(self) -> None:
        def mutate(bundle: Bundle) -> None:
            index = bundle.documents["semantic_index"]
            main = index["input_files"][0]
            alias = copy.deepcopy(main)
            alias["role"] = "user_header"
            alias["input_file_id"] = verifier.input_file_id(
                index["identity_scheme"],
                alias["role"],
                alias["logical_path"],
                alias["sha256"],
            )
            index["input_files"].append(alias)
            index["translation_units"][0]["input_file_ids"].append(alias["input_file_id"])
            index["translation_units"][0]["input_file_ids"].sort()
            bundle.refresh_input_manifest()
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertEqual(report["failure_count"], 0)

    def test_same_logical_path_different_digest_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            index = bundle.documents["semantic_index"]
            main = index["input_files"][0]
            conflict = copy.deepcopy(main)
            conflict["role"] = "user_header"
            conflict["sha256"] = digest(b"different bytes\n")
            conflict["byte_size"] = len(b"different bytes\n")
            conflict["input_file_id"] = verifier.input_file_id(
                index["identity_scheme"],
                conflict["role"],
                conflict["logical_path"],
                conflict["sha256"],
            )
            index["input_files"].append(conflict)
            index["translation_units"][0]["input_file_ids"].append(
                conflict["input_file_id"]
            )
            index["translation_units"][0]["input_file_ids"].sort()
            bundle.refresh_input_manifest()
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("source.input_manifest", self.failure_ids(report))

    def test_missing_tu_input_reference_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            unit = bundle.documents["semantic_index"]["translation_units"][0]
            unit["input_file_ids"] = ["input-file:" + "f" * 64]
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("source.input_manifest", self.failure_ids(report))

    def test_strict_missing_manifest_is_explicit_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-test-") as directory:
            bundle = Bundle(Path(directory))
            bundle.documents["semantic_index"].pop("input_manifest_sha256")
            bundle.documents["semantic_index"].pop("input_files")
            for unit in bundle.documents["semantic_index"]["translation_units"]:
                unit.pop("input_file_ids")
            bundle.sync()
            report = bundle.verify(strict=True)
        manifest_findings = [
            item
            for item in report["findings"]
            if item["check_id"] == "source.input_manifest"
        ]
        self.assertTrue(any(item["status"] == "FAIL" for item in manifest_findings))

    def test_analysis_id_source_commitment_tampering_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.certificate["analysis_id"] = "analysis:" + "f" * 64
            bundle.write_certificate()

        report = self.with_bundle(mutate)
        self.assertIn("source.certificate_commitment", self.failure_ids(report))

    def test_strict_missing_certificate_source_commitment_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-test-") as directory:
            bundle = Bundle(Path(directory))
            bundle.certificate["inputs"] = [
                item for item in bundle.certificate["inputs"] if item["kind"] != "source_inputs"
            ]
            bundle.certificate["stages"][0]["input_sha256"] = bundle.certificate[
                "stages"
            ][0]["input_sha256"][:1]
            bundle.write_certificate()
            report = bundle.verify(strict=True)
        manifest_findings = [
            item
            for item in report["findings"]
            if item["check_id"] == "source.input_manifest"
        ]
        self.assertTrue(any(item["status"] == "FAIL" for item in manifest_findings))

    def test_scrambled_witness_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            members = bundle.documents["ap_influence_cones"]["cones"][0]["members"]
            members[0]["witness_edge_ids"] = ["edge:second", "edge:first"]
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("cones.witness", self.failure_ids(report))

    def test_absent_witness_edge_fails(self) -> None:
        def mutate(bundle: Bundle) -> None:
            members = bundle.documents["ap_influence_cones"]["cones"][0]["members"]
            members[0]["witness_edge_ids"] = ["edge:absent"]
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("cones.witness", self.failure_ids(report))

    def test_unreachable_member_fails_independent_reachability(self) -> None:
        def mutate(bundle: Bundle) -> None:
            graph = bundle.documents["contextual_influence_graph"]
            graph["nodes"].append(
                {"node_id": "node:isolated", "semantic_node_ref": "semantic:isolated"}
            )
            cone = bundle.documents["ap_influence_cones"]["cones"][0]
            cone["members"].append(
                {
                    "node_id": "node:isolated",
                    "membership": "MAY_INFLUENCE",
                    "witness_edge_ids": [],
                    "uncertainty_reasons": [],
                }
            )
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertIn("cones.reachability", self.failure_ids(report))

    def test_v1_artifacts_are_detected_but_losslessness_is_unsupported(self) -> None:
        def mutate(bundle: Bundle) -> None:
            index = bundle.documents["semantic_index"]
            index["schema_version"] = "1.0.0"
            for field in (
                "identity_scheme",
                "canonical_compilation_database_sha256",
                "path_map_sha256",
                "logical_root_ids",
                "source_identity_root",
                "input_manifest_sha256",
                "input_files",
                "abstract_objects",
                "function_summaries",
                "callsites",
            ):
                index.pop(field, None)
            for unit in index["translation_units"]:
                unit.pop("input_file_ids", None)
            graph = bundle.documents["contextual_influence_graph"]
            graph["schema_version"] = "1.0.0"
            for node in graph["nodes"]:
                node.pop("semantic_node_ref", None)
            for edge in graph["edges"]:
                edge.pop("condition_node_ids", None)
            bundle.sync()

        report = self.with_bundle(mutate)
        self.assertEqual(report["failure_count"], 0)
        unsupported = {
            item["check_id"]
            for item in report["findings"]
            if item["status"] == "UNSUPPORTED"
        }
        self.assertIn("formats.semantic_index_losslessness", unsupported)
        self.assertIn("formats.contextual_graph_losslessness", unsupported)

    def test_missing_analyzer_configuration_and_toolchain_fail(self) -> None:
        def mutate(bundle: Bundle) -> None:
            bundle.certificate["analyzer"].pop("configuration_sha256")
            bundle.certificate["toolchain"] = []
            bundle.write_certificate()

        report = self.with_bundle(mutate)
        failures = self.failure_ids(report)
        self.assertIn("certificate.analyzer", failures)
        self.assertIn("certificate.toolchain", failures)

    def test_strict_provenance_rejects_unprovable_build_binding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-verifier-test-") as directory:
            bundle = Bundle(Path(directory))
            report = bundle.verify(strict=True)
        self.assertEqual(report["overall_status"], "FAIL")
        self.assertGreater(report["unsupported_count"], 0)


if __name__ == "__main__":
    unittest.main()
