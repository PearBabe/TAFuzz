#!/usr/bin/env python3
"""Truth-free production-schema fixture used only by acceptance self-tests."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


IDENTITY_SCHEME = "rift.identity/2.0.0"
PATH_MAP_SCHEME = "rift.path-map/1.0.0"
SEMANTIC_ENVIRONMENT_NAMES = (
    "CL",
    "COMPILER_PATH",
    "CPATH",
    "CPLUS_INCLUDE_PATH",
    "C_INCLUDE_PATH",
    "GCC_EXEC_PREFIX",
    "INCLUDE",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "MACOSX_DEPLOYMENT_TARGET",
    "OBJC_INCLUDE_PATH",
    "PATH",
    "SDKROOT",
    "SOURCE_DATE_EPOCH",
    "_CL_",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_id(prefix: str, material: str) -> str:
    return f"{prefix}:{hash_text(material)}"


def stable_id_bytes(prefix: str, material: bytes) -> str:
    return f"{prefix}:{hashlib.sha256(material).hexdigest()}"


def length_prefixed(values: list[str]) -> bytes:
    result = bytearray()
    for value in values:
        payload = value.encode("utf-8")
        result.extend(len(payload).to_bytes(8, "big"))
        result.extend(payload)
    return bytes(result)


def environment_capture() -> tuple[str, list[dict[str, Any]]]:
    material = bytearray()
    records: list[dict[str, Any]] = []
    for name in SEMANTIC_ENVIRONMENT_NAMES:
        present = name in os.environ
        value_digest = hash_text(os.environ[name]) if present else ""
        material.extend(length_prefixed([name]))
        material.append(1 if present else 0)
        material.extend(length_prefixed([value_digest]))
        records.append(
            {
                "name": name,
                "present": present,
                "value_sha256": value_digest if present else None,
            }
        )
    return hashlib.sha256(material).hexdigest(), records


def schema_tree_digest(root: Path) -> str:
    result = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        name = path.relative_to(root.parent).as_posix().encode("utf-8")
        payload = path.read_bytes()
        result.update(len(name).to_bytes(8, "big"))
        result.update(name)
        result.update(len(payload).to_bytes(8, "big"))
        result.update(payload)
    return result.hexdigest()


def logical_location(location: dict[str, Any], logical_source: str) -> dict[str, Any]:
    result = dict(location)
    result["file"] = logical_source
    return result


def portable_command(
    compile_database: Path,
    command: dict[str, Any],
) -> tuple[str, str, str, str, str, Path]:
    working = (compile_database.parent / command["directory"]).resolve()
    source = (working / command["file"]).resolve()
    relative = source.relative_to(working).as_posix()
    logical_working = "riftpath://v1/project/"
    logical_source = f"riftpath://v1/project/{relative}"
    arguments = command["arguments"]
    match = re.search(r"(?:^|[-_])([0-9]+)$", Path(arguments[0]).name)
    if match is None:
        raise ValueError("fixture compiler does not expose its major version")
    canonical = (
        f"{IDENTITY_SCHEME}\0{logical_working}\0{logical_source}\0"
        f"clang-major={int(match.group(1))}\0"
    )
    for index, raw in enumerate(arguments):
        argument = Path(raw).name if index == 0 else raw
        canonical += f"{len(argument.encode('utf-8'))}:{argument}\0"
    command_sha256 = hash_text(canonical)
    path_map_sha256 = hash_text(f"{IDENTITY_SCHEME}\0{PATH_MAP_SCHEME}\0project")
    canonical_database_sha256 = hash_text(
        f"{IDENTITY_SCHEME}\0{path_map_sha256}\0"
        f"{len(canonical.encode('utf-8'))}:{canonical}"
    )
    tu_id = stable_id(
        "tu", f"{IDENTITY_SCHEME}\0{logical_source}\0{command_sha256}"
    )
    return (
        logical_working,
        logical_source,
        command_sha256,
        canonical_database_sha256,
        tu_id,
        source,
    )


def value_type(ap: dict[str, Any]) -> dict[str, Any]:
    return ap["value_type"]


def evidence(identifier: str, location: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": identifier,
        "kind": "ast_semantics",
        "certainty": "must",
        "fact": "fixture maps the explicit public AP source selector",
        "producer": "rift-m4-fake-analyzer",
        "location": location,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["influence"])
    parser.add_argument("--compile-db", type=Path, required=True)
    parser.add_argument("--property", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--schema-dir", type=Path, required=True)
    args = parser.parse_args()
    compile_commands = read_json(args.compile_db)
    property_ir = read_json(args.property)
    output = args.output_dir.resolve()
    command = compile_commands[0]
    (
        logical_working,
        logical_source,
        command_digest,
        canonical_database_digest,
        tu_id,
        source_path,
    ) = portable_command(args.compile_db.resolve(), command)
    source_digest = digest(source_path)
    source_size = source_path.stat().st_size
    input_file_id = stable_id(
        "input-file",
        f"{IDENTITY_SCHEME}\0main\0{logical_source}\0{source_digest}",
    )
    input_manifest_material = (
        f"{IDENTITY_SCHEME}\0input-manifest/1.0.0\0main\0"
        f"{len(logical_source.encode('utf-8'))}:{logical_source}\0"
        f"{source_digest}\0{source_size}"
    )
    input_manifest_digest = hash_text(input_manifest_material)
    path_map_digest = hash_text(f"{IDENTITY_SCHEME}\0{PATH_MAP_SCHEME}\0project")
    location_selectors = {
        selector["selector_id"]: selector["location"]
        for selector in property_ir["selectors"]
        if selector["kind"] == "source_location"
    }
    entities = []
    semantic_nodes = []
    graph_nodes = []
    bindings = []
    cones = []
    for ap in property_ir["atomic_propositions"]:
        ap_id = ap["ap_id"]
        location_ref = next(ref for ref in ap["selector_refs"] if ref in location_selectors)
        location = logical_location(location_selectors[location_ref], logical_source)
        entity_id = f"entity.{ap_id}"
        semantic_id = f"semantic.{ap_id}"
        graph_id = f"graph.{ap_id}"
        entity = {
            "entity_id": entity_id,
            "entity_kind": "local",
            "identity_status": "exact",
            "usr": f"c:fixture@{ap_id}",
            "qualified_signature": f"main::{ap_id}",
            "canonical_type": ap["value_type"]["canonical"],
        }
        entities.append(
            {
                "entity": entity,
                "declarations": [location],
                "definitions": [location],
                "translation_unit_refs": [tu_id],
            }
        )
        semantic_nodes.append(
            {
                "node_id": semantic_id,
                "node_kind": "definition",
                "entity_ref": entity_id,
                "owner_function_id": None,
                "access_path": {
                    "root_entity_id": entity_id,
                    "dereference_depth": 0,
                    "fields": [],
                    "unknown_suffix": False,
                },
                "abstract_object_id": f"object.{ap_id}",
                "value_type": value_type(ap),
                "location": location,
                "ast_kind": "VarDecl",
            }
        )
        graph_nodes.append(
            {
                "node_id": graph_id,
                "semantic_node_ref": semantic_id,
                "node_kind": "predicate",
                "semantic_node_kind": "definition",
                "entity": entity,
                "abstract_object": {
                    "object_id": f"object.{ap_id}",
                    "abstraction": "stack",
                    "allocation_site": location,
                    "certainty": "must",
                },
                "field_path": [],
                "call_context": {
                    "policy": "root",
                    "callsite_ids": [],
                    "truncated": False,
                },
                "lifecycle_phase": "active",
                "task_context": {
                    "kind": "process",
                    "context_id": "main",
                    "certainty": "must",
                },
                "scope": {
                    "scope_id": f"scope.{ap_id}",
                    "key_node_ids": [],
                    "status": "exact",
                },
                "generation": {
                    "kind": "exact",
                    "identity": "process-0",
                    "reuse_possible": False,
                },
                "location": location,
                "value_type": value_type(ap),
                "evidence": [evidence(f"evidence.graph.{ap_id}", location)],
            }
        )
        role_candidates = []
        for role in ap["roles"]:
            binding_id = f"binding.{ap_id}.{role}"
            bindings.append(
                {
                    "ap_id": ap_id,
                    "role": role,
                    "resolution": "CONFIRMED",
                    "candidates": [
                        {
                            "binding_id": binding_id,
                            "status": "CONFIRMED",
                            "selector_refs": ap["selector_refs"],
                            "semantic_node_refs": [semantic_id],
                            "evidence": [evidence(f"evidence.binding.{ap_id}.{role}", location)],
                            "confidence": 1.0,
                            "uncertainty_reasons": [],
                        }
                    ],
                }
            )
            role_candidates.append(
                {
                    "binding_id": binding_id,
                    "disposition": "INCLUDED",
                    "root_node_ids": [graph_id],
                    "uncertainty_reasons": [],
                }
            )
        cones.append(
            {
                "cone_id": f"cone.{ap_id}",
                "ap_id": ap_id,
                "roles": ap["roles"],
                "candidate_accounting": role_candidates,
                "members": [
                    {
                        "node_id": graph_id,
                        "membership": "MUST_INFLUENCE",
                        "witness_edge_ids": [],
                        "uncertainty_reasons": [],
                    }
                ],
                "edge_ids": [],
                "status": "COMPLETE",
                "uncertainty_reasons": [],
            }
        )

    index = {
        "schema_version": "2.0.0",
        "artifact_id": stable_id(
            "index",
            f"{IDENTITY_SCHEME}\0{canonical_database_digest}\0"
            f"{path_map_digest}\0{input_manifest_digest}",
        ),
        "identity_scheme": IDENTITY_SCHEME,
        "canonical_compilation_database_sha256": canonical_database_digest,
        "path_map_sha256": path_map_digest,
        "input_manifest_sha256": input_manifest_digest,
        "logical_root_ids": ["project"],
        "source_identity_root": f"{IDENTITY_SCHEME}:{path_map_digest}",
        "translation_units": [
            {
                "tu_id": tu_id,
                "source_file": logical_source,
                "language": "c++" if logical_source.endswith(".cpp") else "c",
                "working_directory": logical_working,
                "command_sha256": command_digest,
                "status": "indexed",
                "input_file_ids": [input_file_id],
                "diagnostics": [],
            }
        ],
        "input_files": [
            {
                "input_file_id": input_file_id,
                "logical_path": logical_source,
                "sha256": source_digest,
                "role": "main",
                "byte_size": source_size,
            }
        ],
        "entities": entities,
        "abstract_objects": [node["abstract_object"] for node in graph_nodes],
        "semantic_nodes": semantic_nodes,
        "semantic_relations": [],
        "function_summaries": [],
        "callsites": [],
        "status": "COMPLETE",
        "diagnostics": [],
        "unsupported_constructs": [],
    }
    index_path = output / "semantic_index.json"
    write_json(index_path, index)
    binding_artifact = {
        "schema_version": "1.0.0",
        "artifact_id": "bindings.fixture",
        "property_ir_sha256": digest(args.property),
        "semantic_index_sha256": digest(index_path),
        "binding_policy": {
            "joint_role_binding": True,
            "similarity_is_confirmation": False,
        },
        "bindings": bindings,
        "unsupported_constructs": [],
    }
    binding_path = output / "ap_bindings.json"
    write_json(binding_path, binding_artifact)
    graph_artifact = {
        "schema_version": "2.0.0",
        "artifact_id": "graph.fixture",
        "semantic_index_sha256": digest(index_path),
        "context_policy": {
            "call_string_limit": 1,
            "object_sensitivity": "allocation_site",
            "field_sensitivity": "full",
            "unknowns_are_explicit": True,
        },
        "nodes": graph_nodes,
        "edges": [],
        "status": "COMPLETE",
        "diagnostics": [],
        "unsupported_constructs": [],
    }
    graph_path = output / "contextual_influence_graph.json"
    write_json(graph_path, graph_artifact)
    cones_path = output / "ap_influence_cones.json"
    write_json(
        cones_path,
        {
            "schema_version": "1.0.0",
            "artifact_id": "cones.fixture",
            "ap_bindings_sha256": digest(binding_path),
            "graph_sha256": digest(graph_path),
            "candidate_accounting_complete": True,
            "ranking_never_prunes": True,
            "cones": cones,
            "unsupported_constructs": [],
        },
    )
    timestamp = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    analyzer_digest = digest(Path(sys.executable).resolve())
    schema_digest = schema_tree_digest(args.schema_dir.resolve())
    core_digest = digest(Path(__file__).resolve())
    manifest_digest = hash_text(
        f"relative-path-and-content-v1\0{core_digest}\0{schema_digest}"
    )
    environment_digest, environment_variables = environment_capture()
    configuration_digest = hashlib.sha256(
        length_prefixed([manifest_digest, environment_digest, *sys.argv])
    ).hexdigest()
    output_entries = [
        ("semantic_index", index_path, index["artifact_id"]),
        ("ap_bindings", binding_path, binding_artifact["artifact_id"]),
        ("contextual_influence_graph", graph_path, graph_artifact["artifact_id"]),
        ("ap_influence_cones", cones_path, "cones.fixture"),
    ]
    analysis_id = stable_id_bytes(
        "analysis",
        length_prefixed(
            [
                digest(args.property),
                input_manifest_digest,
                canonical_database_digest,
                path_map_digest,
            ]
        ),
    )
    output_digests = [digest(path) for _, path, _ in output_entries]
    certificate_id = stable_id_bytes(
        "certificate",
        length_prefixed([analysis_id, configuration_digest, *output_digests]),
    )
    write_json(
        output / "analysis_certificate.json",
        {
            "schema_version": "2.0.0",
            "certificate_id": certificate_id,
            "analysis_id": analysis_id,
            "status": "COMPLETE",
            "analyzer": {
                "name": "tafuzz-sa",
                "version": "0.1.0",
                "binary_sha256": analyzer_digest,
                "configuration_sha256": configuration_digest,
                "environment_sha256": environment_digest,
            },
            "build_manifest": {
                "identity_policy": "relative-path-and-content-v1",
                "manifest_sha256": manifest_digest,
                "production_core_sha256": core_digest,
                "schema_bundle_sha256": schema_digest,
            },
            "core_tree_sha256": core_digest,
            "schema_bundle_sha256": schema_digest,
            "environment": {
                "digest": environment_digest,
                "variables": environment_variables,
            },
            "inputs": [
                {
                    "artifact_id": property_ir["artifact_id"],
                    "kind": "typed_property_ir",
                    "sha256": digest(args.property),
                    "path": str(args.property.resolve()),
                },
                {
                    "artifact_id": "compile.database",
                    "kind": "compile_commands",
                    "sha256": digest(args.compile_db),
                    "path": str(args.compile_db.resolve()),
                },
                {
                    "artifact_id": stable_id("input_manifest", input_manifest_digest),
                    "kind": "source_inputs",
                    "sha256": input_manifest_digest,
                },
            ],
            "source_input_provenance": {
                "manifest_sha256": input_manifest_digest,
                "files": [
                    {
                        "input_file_id": input_file_id,
                        "logical_path": logical_source,
                        "role": "main",
                        "sha256": source_digest,
                        "byte_size": source_size,
                        "observed_paths": [str(source_path.resolve())],
                    }
                ],
            },
            "toolchain": [
                {
                    "component_id": stable_id("tool", analyzer_digest),
                    "name": Path(sys.executable).name,
                    "version": sys.version.split()[0],
                    "component_kind": "executable",
                    "sha256": analyzer_digest,
                }
            ],
            "outputs": [
                {
                    "artifact_id": artifact_id,
                    "kind": kind,
                    "sha256": digest(path),
                    "path": str(path.resolve()),
                }
                for kind, path, artifact_id in output_entries
            ],
            "stages": [
                {
                    "stage_id": "stage.index",
                    "name": "index",
                    "status": "COMPLETE",
                    "input_sha256": [digest(args.compile_db), input_manifest_digest],
                    "output_sha256": [digest(index_path)],
                    "diagnostics": [],
                },
                {
                    "stage_id": "stage.bind",
                    "name": "bind",
                    "status": "COMPLETE",
                    "input_sha256": [digest(args.property), digest(index_path)],
                    "output_sha256": [digest(binding_path)],
                    "diagnostics": [],
                },
                {
                    "stage_id": "stage.influence",
                    "name": "influence",
                    "status": "COMPLETE",
                    "input_sha256": [digest(index_path), digest(binding_path)],
                    "output_sha256": [digest(graph_path)],
                    "diagnostics": [],
                },
                {
                    "stage_id": "stage.cone",
                    "name": "cone",
                    "status": "COMPLETE",
                    "input_sha256": [digest(binding_path), digest(graph_path)],
                    "output_sha256": [digest(cones_path)],
                    "diagnostics": [],
                },
                {
                    "stage_id": "stage.certificate",
                    "name": "certificate",
                    "status": "COMPLETE",
                    "input_sha256": [digest(path) for _, path, _ in output_entries],
                    "output_sha256": [],
                    "diagnostics": [],
                },
            ],
            "unsupported_constructs": [],
            "started_at": timestamp,
            "finished_at": timestamp,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
