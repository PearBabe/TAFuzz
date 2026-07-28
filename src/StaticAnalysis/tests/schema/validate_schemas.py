#!/usr/bin/env python3
"""Deterministic positive and negative checks for the RIFT production schemas."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import sys
import tempfile
from typing import Any

import jsonschema


SCHEMA_FILES = (
    "common.schema.json",
    "typed_property_ir.schema.json",
    "semantic_index.schema.json",
    "ap_bindings.schema.json",
    "contextual_influence_graph.schema.json",
    "ap_influence_cones.schema.json",
    "analysis_certificate.schema.json",
    "model_pack.schema.json",
    "model_pack_v2.schema.json",
    "model_fact_overlay.schema.json",
    "predicate_occurrence_bindings.schema.json",
    "executor_capabilities.schema.json",
    "frontier_candidates.schema.json",
    "fuzzable_frontier.schema.json",
    "mutation_recipes.schema.json",
    "recipe_replay_obligations.schema.json",
    "m5_analysis_certificate.schema.json",
)

EXPECTED_IDS = {
    "common.schema.json": "https://tafuzz.dev/rift/schema/common/1.0.0",
    "typed_property_ir.schema.json": "https://tafuzz.dev/rift/schema/typed-property-ir/2.0.0",
    "semantic_index.schema.json": "https://tafuzz.dev/rift/schema/semantic-index/2.0.0",
    "ap_bindings.schema.json": "https://tafuzz.dev/rift/schema/ap-bindings/2.0.0",
    "contextual_influence_graph.schema.json": "https://tafuzz.dev/rift/schema/contextual-influence-graph/2.0.0",
    "ap_influence_cones.schema.json": "https://tafuzz.dev/rift/schema/ap-influence-cones/1.0.0",
    "analysis_certificate.schema.json": "https://tafuzz.dev/rift/schema/analysis-certificate/2.0.0",
    "model_pack.schema.json": "https://tafuzz.dev/rift/schema/model-pack/1.0.0",
    "model_pack_v2.schema.json": "https://tafuzz.dev/rift/schema/model-pack/2.0.0",
    "model_fact_overlay.schema.json": "https://tafuzz.dev/rift/schema/model-fact-overlay/1.0.0",
    "predicate_occurrence_bindings.schema.json": "https://tafuzz.dev/rift/schema/predicate-occurrence-bindings/1.0.0",
    "executor_capabilities.schema.json": "https://tafuzz.dev/rift/schema/executor-capabilities/1.0.0",
    "frontier_candidates.schema.json": "https://tafuzz.dev/rift/schema/frontier-candidates/3.0.0",
    "fuzzable_frontier.schema.json": "https://tafuzz.dev/rift/schema/fuzzable-frontier/2.0.0",
    "mutation_recipes.schema.json": "https://tafuzz.dev/rift/schema/mutation-recipes/1.0.0",
    "recipe_replay_obligations.schema.json": "https://tafuzz.dev/rift/schema/recipe-replay-obligations/1.0.0",
    "m5_analysis_certificate.schema.json": "https://tafuzz.dev/rift/schema/m5-analysis-certificate/1.0.0",
}

SHA = "0" * 64

SEMANTIC_ENVIRONMENT_VARIABLES = (
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


def append_length_prefixed(material: bytearray, value: str) -> None:
    encoded = value.encode("utf-8")
    material.extend(len(encoded).to_bytes(8, "big"))
    material.extend(encoded)


def length_prefixed_material(values: list[str]) -> bytes:
    material = bytearray()
    for value in values:
        append_length_prefixed(material, value)
    return bytes(material)


def stable_id(prefix: str, material: bytes) -> str:
    return f"{prefix}:{hashlib.sha256(material).hexdigest()}"


def environment_digest(variables: list[dict[str, Any]]) -> str:
    material = bytearray()
    for variable in variables:
        append_length_prefixed(material, variable["name"])
        material.append(1 if variable["present"] else 0)
        append_length_prefixed(material, variable["value_sha256"] or "")
    return hashlib.sha256(material).hexdigest()


def source_input_id(item: dict[str, Any]) -> str:
    material = (
        b"rift.identity/2.0.0\0"
        + item["role"].encode("utf-8")
        + b"\0"
        + item["logical_path"].encode("utf-8")
        + b"\0"
        + item["sha256"].encode("ascii")
    )
    return stable_id("input-file", material)


def source_manifest_digest(files: list[dict[str, Any]]) -> str:
    material = bytearray(b"rift.identity/2.0.0\0input-manifest/1.0.0")
    for item in files:
        logical = item["logical_path"].encode("utf-8")
        material.extend(b"\0")
        material.extend(item["role"].encode("utf-8"))
        material.extend(b"\0")
        material.extend(str(len(logical)).encode("ascii"))
        material.extend(b":")
        material.extend(logical)
        material.extend(b"\0")
        material.extend(item["sha256"].encode("ascii"))
        material.extend(b"\0")
        material.extend(str(item["byte_size"]).encode("ascii"))
    return hashlib.sha256(material).hexdigest()


def rehash_observed_path(path: pathlib.Path) -> tuple[str, int]:
    before = path.stat()
    digest = hashlib.sha256()
    byte_size = 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError(f"path changed before rehash: {path}")
        while block := stream.read(1024 * 1024):
            digest.update(block)
            byte_size += len(block)
        opened_after = os.fstat(stream.fileno())
    after = path.stat()
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    if before_identity != (
        opened_after.st_dev,
        opened_after.st_ino,
        opened_after.st_size,
        opened_after.st_mtime_ns,
        opened_after.st_ctime_ns,
    ) or (opened_after.st_dev, opened_after.st_ino) != (
        after.st_dev,
        after.st_ino,
    ):
        raise OSError(f"path changed during rehash: {path}")
    return digest.hexdigest(), byte_size


def certificate_contract_errors(instance: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest = instance["build_manifest"]
    if manifest["production_core_sha256"] != instance["core_tree_sha256"]:
        errors.append("build-manifest/core digest mismatch")
    if manifest["schema_bundle_sha256"] != instance["schema_bundle_sha256"]:
        errors.append("build-manifest/schema digest mismatch")

    environment = instance["environment"]
    variables = environment["variables"]
    if tuple(variable["name"] for variable in variables) != SEMANTIC_ENVIRONMENT_VARIABLES:
        errors.append("environment whitelist/order mismatch")
    if environment_digest(variables) != environment["digest"]:
        errors.append("environment aggregate digest mismatch")
    if instance["analyzer"]["environment_sha256"] != environment["digest"]:
        errors.append("analyzer/environment digest mismatch")

    analyzer_tool_matches = 0
    component_ids: set[str] = set()
    for component in instance["toolchain"]:
        expected_component_id = stable_id(
            "tool",
            length_prefixed_material(
                [
                    component["component_kind"],
                    component["name"],
                    component["version"],
                    component["sha256"],
                ]
            ),
        )
        if component["component_id"] != expected_component_id:
            errors.append(f"toolchain component ID mismatch: {component['name']}")
        if component["component_id"] in component_ids:
            errors.append(f"duplicate toolchain component ID: {component['component_id']}")
        component_ids.add(component["component_id"])
        if (
            component["component_kind"] == "executable"
            and component["sha256"] == instance["analyzer"]["binary_sha256"]
        ):
            analyzer_tool_matches += 1
    if analyzer_tool_matches != 1:
        errors.append("toolchain must contain exactly one analyzer executable digest")

    inputs = instance["inputs"]
    outputs = instance["outputs"]
    provenance = instance["source_input_provenance"]
    if provenance["manifest_sha256"] != inputs[2]["sha256"]:
        errors.append("source-input manifest descriptor mismatch")
    provenance_files = provenance["files"]
    if source_manifest_digest(provenance_files) != provenance["manifest_sha256"]:
        errors.append("source-input manifest content mismatch")
    input_ids: set[str] = set()
    logical_digests: dict[str, str] = {}
    for item in provenance_files:
        if item["input_file_id"] != source_input_id(item):
            errors.append(f"source-input ID mismatch: {item['input_file_id']}")
        if item["input_file_id"] in input_ids:
            errors.append(f"duplicate source-input ID: {item['input_file_id']}")
        input_ids.add(item["input_file_id"])
        previous = logical_digests.setdefault(item["logical_path"], item["sha256"])
        if previous != item["sha256"]:
            errors.append(f"conflicting logical source input: {item['logical_path']}")
        if not item["observed_paths"] and not (
            item["role"] == "toolchain"
            and item["logical_path"].startswith("riftpath://v1/toolchain/predefines/")
        ):
            errors.append(f"missing physical source provenance: {item['input_file_id']}")
        for observed_path in item["observed_paths"]:
            try:
                digest, byte_size = rehash_observed_path(pathlib.Path(observed_path))
            except OSError as error:
                errors.append(f"cannot rehash source input {observed_path}: {error}")
                continue
            if (digest, byte_size) != (item["sha256"], item["byte_size"]):
                errors.append(f"source input content changed: {observed_path}")

    stages = instance["stages"]
    stage_statuses = [stage["status"] for stage in stages[:4]]
    if "FAILED" in stage_statuses:
        expected_status = "FAILED"
    elif any(value != "COMPLETE" for value in stage_statuses):
        expected_status = "CONSERVATIVE_INCOMPLETE"
    else:
        expected_status = "COMPLETE"
    if instance["status"] != expected_status:
        errors.append("top-level status does not aggregate analysis stages")
    if stages[4]["status"] != expected_status:
        errors.append("certificate stage status does not aggregate analysis stages")

    expected_stage_io = (
        ([inputs[1]["sha256"], inputs[2]["sha256"]], [outputs[0]["sha256"]]),
        ([inputs[0]["sha256"], outputs[0]["sha256"]], [outputs[1]["sha256"]]),
        ([outputs[0]["sha256"], outputs[1]["sha256"]], [outputs[2]["sha256"]]),
        ([outputs[1]["sha256"], outputs[2]["sha256"]], [outputs[3]["sha256"]]),
        ([output["sha256"] for output in outputs], []),
    )
    for stage, (expected_inputs, expected_outputs) in zip(stages, expected_stage_io):
        if stage["input_sha256"] != expected_inputs:
            errors.append(f"stage input chain mismatch: {stage['name']}")
        if stage["output_sha256"] != expected_outputs:
            errors.append(f"stage output chain mismatch: {stage['name']}")

    expected_certificate_id = stable_id(
        "certificate",
        length_prefixed_material(
            [
                instance["analysis_id"],
                instance["analyzer"]["configuration_sha256"],
                *[output["sha256"] for output in outputs],
            ]
        ),
    )
    if instance["certificate_id"] != expected_certificate_id:
        errors.append("certificate ID does not bind analysis/configuration/outputs")
    return errors


def canonical_artifact_digest(instance: dict[str, Any]) -> str:
    encoded = json.dumps(instance, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def replace_path(instance: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    current: Any = instance
    for component in path[:-1]:
        current = current[component]
    current[path[-1]] = value


def location() -> dict[str, Any]:
    return {
        "file": "riftpath://v1/source/src/neutral.cc",
        "line": 7,
        "column": 3,
        "location_kind": "spelling",
    }


def value_type(kind: str = "bool", canonical: str = "bool") -> dict[str, Any]:
    return {"kind": kind, "canonical": canonical}


def expression() -> dict[str, Any]:
    return {
        "node_kind": "reference",
        "operator": None,
        "value_type": value_type(),
        "referenced_selector_id": "selector.state",
        "operands": [],
    }


def entity() -> dict[str, Any]:
    return {
        "entity_id": "entity.state",
        "entity_kind": "field",
        "identity_status": "exact",
        "usr": "c:@S@State@FI@ready",
        "qualified_signature": "State::ready",
        "canonical_type": "bool",
    }


def evidence(kind: str = "usr_match", certainty: str = "must") -> dict[str, Any]:
    result: dict[str, Any] = {
        "evidence_id": f"evidence.{kind}",
        "kind": kind,
        "certainty": certainty,
        "fact": "machine-readable semantic fact",
        "producer": "fixture",
    }
    if kind in {"name_similarity", "llm_similarity"}:
        result["score"] = 0.99
    if kind == "model_rule":
        result["model_rule_id"] = "rule.source"
    return result


def selector() -> dict[str, Any]:
    return {"selector_id": "selector.state", "kind": "usr", "usr": "c:@S@State@FI@ready"}


def property_ir_v2_fixture(legacy: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the fixture shape without changing the legacy fixture."""
    instance = copy.deepcopy(legacy)
    instance["schema_version"] = "2.0.0"
    proposition = instance["atomic_propositions"][0]
    proposition.pop("selector_refs")
    proposition["role_selector_groups"] = [
        {
            "group_id": "selector-group.response",
            "role": "response",
            "all_of": ["selector.state"],
        },
        {
            "group_id": "selector-group.state",
            "role": "state",
            "all_of": ["selector.state"],
        },
    ]
    return instance


def ap_bindings_v2_fixture(legacy: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the binding fixture to the role-DNF output contract."""
    instance = copy.deepcopy(legacy)
    instance["schema_version"] = "2.0.0"
    instance["binding_policy"] = {
        "role_selector_logic": "role-dnf/1",
        "cross_role_consistency": "NOT_EVALUATED",
        "similarity_is_confirmation": False,
    }
    instance["bindings"][0]["candidates"][0]["selector_group_id"] = (
        "selector-group.state"
    )
    return instance


def fixtures() -> dict[str, dict[str, Any]]:
    property_ir = {
        "schema_version": "1.0.0",
        "artifact_id": "property.artifact",
        "property_id": "property.response",
        "logic": "MITL",
        "time_domain": "dense",
        "formula_text": "F_[0,1] state",
        "formula": {
            "node_id": "formula.root",
            "operator": "eventually",
            "interval": {
                "lower": 0,
                "upper": 1,
                "lower_closed": True,
                "upper_closed": True,
                "unit": "s",
                "bound_ap_refs": [],
            },
            "operands": [
                {"node_id": "formula.atom", "operator": "atom", "ap_ref": "ap.state", "operands": []}
            ],
        },
        "atomic_propositions": [
            {
                "ap_id": "ap.state",
                "roles": ["response", "state"],
                "value_type": value_type(),
                "predicate": expression(),
                "selector_refs": ["selector.state"],
            }
        ],
        "selectors": [selector()],
    }

    function = {
        "entity_id": "entity.function",
        "entity_kind": "function",
        "identity_status": "exact",
        "usr": "c:@F@step#",
        "qualified_signature": "step()",
        "canonical_type": "void ()",
    }
    semantic_index = {
        "schema_version": "2.0.0",
        "artifact_id": "index.artifact",
        "identity_scheme": "rift.identity/2.0.0",
        "canonical_compilation_database_sha256": SHA,
        "path_map_sha256": SHA,
        "input_manifest_sha256": SHA,
        "logical_root_ids": ["source"],
        "source_identity_root": f"rift.identity/2.0.0:{SHA}",
        "translation_units": [
            {
                "tu_id": "tu.neutral",
                "source_file": "riftpath://v1/source/src/neutral.cc",
                "language": "c++",
                "working_directory": "riftpath://v1/build/neutral",
                "command_sha256": SHA,
                "status": "indexed",
                "input_file_ids": ["input.file"],
                "diagnostics": [],
            }
        ],
        "input_files": [
            {
                "input_file_id": "input.file",
                "logical_path": "riftpath://v1/source/src/neutral.cc",
                "sha256": SHA,
                "role": "main",
                "byte_size": 128,
            }
        ],
        "entities": [
            {
                "entity": entity(),
                "declarations": [location()],
                "definitions": [location()],
                "translation_unit_refs": ["tu.neutral"],
            },
            {
                "entity": function,
                "declarations": [location()],
                "definitions": [location()],
                "translation_unit_refs": ["tu.neutral"],
            },
        ],
        "abstract_objects": [
            {
                "object_id": "object.state",
                "abstraction": "stack",
                "allocation_site": location(),
                "certainty": "must",
            }
        ],
        "semantic_nodes": [
            {
                "node_id": "semantic.state",
                "node_kind": "value",
                "entity_ref": "entity.state",
                "owner_function_id": "entity.function",
                "access_path": {
                    "root_entity_id": "entity.state",
                    "dereference_depth": 0,
                    "fields": ["ready"],
                    "unknown_suffix": False,
                },
                "abstract_object_id": "object.state",
                "value_type": value_type(),
                "location": location(),
                "ast_kind": "MemberExpr",
            }
        ],
        "semantic_relations": [
            {
                "relation_id": "relation.state",
                "source_node_id": "semantic.state",
                "target_node_id": "semantic.state",
                "kind": "uses",
                "certainty": "must",
                "evidence": [evidence("ast_semantics")],
                "callsite_id": "call.site",
                "condition_node_ids": ["semantic.state"],
                "uncertainty_reasons": [],
            }
        ],
        "function_summaries": [
            {
                "function_entity_id": "entity.function",
                "parameter_node_ids": [],
                "receiver_node_id": None,
                "return_node_id": None,
                "owned_node_ids": ["semantic.state"],
                "relation_ids": ["relation.state"],
                "callsite_ids": ["call.site"],
                "status": "COMPLETE",
                "uncertainty_reasons": [],
            }
        ],
        "callsites": [
            {
                "callsite_id": "call.site",
                "caller_function_id": "entity.function",
                "candidate_callee_ids": [],
                "argument_node_ids": [],
                "argument_node_groups": [],
                "argument_is_address": [],
                "receiver_node_id": None,
                "result_node_id": "semantic.state",
                "location": location(),
                "direct": False,
                "status": "CONSERVATIVE_INCOMPLETE",
                "uncertainty_reasons": ["indirect target set is open"],
            }
        ],
        "status": "COMPLETE",
        "diagnostics": [],
        "unsupported_constructs": [],
    }

    bindings = {
        "schema_version": "1.0.0",
        "artifact_id": "bindings.artifact",
        "property_ir_sha256": SHA,
        "semantic_index_sha256": SHA,
        "binding_policy": {"joint_role_binding": True, "similarity_is_confirmation": False},
        "bindings": [
            {
                "ap_id": "ap.state",
                "role": "state",
                "resolution": "CONFIRMED",
                "candidates": [
                    {
                        "binding_id": "binding.state",
                        "status": "CONFIRMED",
                        "selector_refs": ["selector.state"],
                        "semantic_node_refs": ["semantic.state"],
                        "evidence": [evidence()],
                        "confidence": 1.0,
                        "uncertainty_reasons": [],
                    }
                ],
            }
        ],
        "unsupported_constructs": [],
    }

    graph_node = {
        "node_id": "cig.state",
        "semantic_node_ref": "semantic.state",
        "node_kind": "value",
        "semantic_node_kind": "value",
        "entity": entity(),
        "abstract_object": {
            "object_id": "object.state",
            "abstraction": "receiver",
            "allocation_site": location(),
            "certainty": "must",
        },
        "field_path": ["ready"],
        "call_context": {"policy": "call_string", "callsite_ids": ["call.site"], "truncated": False},
        "lifecycle_phase": "active",
        "task_context": {"kind": "task", "context_id": "task.main", "certainty": "must"},
        "scope": {"scope_id": "scope.session", "key_node_ids": [], "status": "exact"},
        "generation": {"kind": "symbolic", "identity": "epoch", "reuse_possible": True},
        "location": location(),
        "value_type": value_type(),
        "evidence": [evidence("ast_semantics")],
    }
    graph = {
        "schema_version": "2.0.0",
        "artifact_id": "graph.artifact",
        "semantic_index_sha256": SHA,
        "context_policy": {
            "call_string_limit": 2,
            "object_sensitivity": "receiver",
            "field_sensitivity": "full",
            "unknowns_are_explicit": True,
        },
        "nodes": [graph_node],
        "edges": [
            {
                "edge_id": "edge.self",
                "source_node_id": "cig.state",
                "target_node_id": "cig.state",
                "kind": "value_flow",
                "relation_kind": "data",
                "certainty": "must",
                "evidence": [evidence("llvm_value_flow")],
                "condition_node_ids": ["cig.state"],
                "conditions": [
                    {
                        "node_kind": "reference",
                        "operator": None,
                        "value_type": value_type("unknown", "unknown"),
                        "referenced_selector_id": "cig.state",
                        "operands": [],
                    }
                ],
                "uncertainty_reasons": [],
            }
        ],
        "status": "COMPLETE",
        "diagnostics": [],
        "unsupported_constructs": [],
    }

    cones = {
        "schema_version": "1.0.0",
        "artifact_id": "cones.artifact",
        "ap_bindings_sha256": SHA,
        "graph_sha256": SHA,
        "candidate_accounting_complete": True,
        "ranking_never_prunes": True,
        "cones": [
            {
                "cone_id": "cone.state",
                "ap_id": "ap.state",
                "roles": ["state"],
                "candidate_accounting": [
                    {
                        "binding_id": "binding.state",
                        "disposition": "INCLUDED",
                        "root_node_ids": ["cig.state"],
                        "uncertainty_reasons": [],
                    }
                ],
                "members": [
                    {
                        "node_id": "cig.state",
                        "membership": "MUST_INFLUENCE",
                        "witness_edge_ids": ["edge.self"],
                        "uncertainty_reasons": [],
                    }
                ],
                "edge_ids": ["edge.self"],
                "status": "COMPLETE",
                "uncertainty_reasons": [],
            }
        ],
        "unsupported_constructs": [],
    }

    environment_variables = [
        {"name": name, "present": False, "value_sha256": None}
        for name in SEMANTIC_ENVIRONMENT_VARIABLES
    ]
    captured_environment_digest = environment_digest(environment_variables)
    provenance_files = [
        {
            "input_file_id": "",
            "logical_path": f"riftpath://v1/toolchain/predefines/{SHA}",
            "role": "toolchain",
            "sha256": SHA,
            "byte_size": 0,
            "observed_paths": [],
        }
    ]
    provenance_files[0]["input_file_id"] = source_input_id(provenance_files[0])
    source_manifest_sha256 = source_manifest_digest(provenance_files)
    tool_name = "compiler"
    tool_version = "18.0"
    tool_kind = "executable"
    tool_component_id = stable_id(
        "tool",
        length_prefixed_material([tool_kind, tool_name, tool_version, SHA]),
    )
    analysis_id = stable_id("analysis", b"fixture-analysis")
    configuration_sha256 = hashlib.sha256(b"fixture-configuration").hexdigest()
    output_digests = [SHA, SHA, SHA, SHA]
    certificate_id = stable_id(
        "certificate",
        length_prefixed_material(
            [analysis_id, configuration_sha256, *output_digests]
        ),
    )
    certificate = {
        "schema_version": "2.0.0",
        "certificate_id": certificate_id,
        "analysis_id": analysis_id,
        "status": "COMPLETE",
        "analyzer": {
            "name": "tafuzz-sa",
            "version": "0.1.0",
            "binary_sha256": SHA,
            "configuration_sha256": configuration_sha256,
            "environment_sha256": captured_environment_digest,
        },
        "build_manifest": {
            "identity_policy": "relative-path-and-content-v1",
            "manifest_sha256": SHA,
            "production_core_sha256": SHA,
            "schema_bundle_sha256": SHA,
        },
        "core_tree_sha256": SHA,
        "schema_bundle_sha256": SHA,
        "environment": {
            "digest": captured_environment_digest,
            "variables": environment_variables,
        },
        "inputs": [
            {
                "artifact_id": "property.artifact",
                "kind": "typed_property_ir",
                "sha256": SHA,
                "path": "/fixture/property.json",
            },
            {
                "artifact_id": "compile.database",
                "kind": "compile_commands",
                "sha256": SHA,
                "path": "/fixture/compile_commands.json",
            },
            {
                "artifact_id": "input.manifest",
                "kind": "source_inputs",
                "sha256": source_manifest_sha256,
            },
        ],
        "source_input_provenance": {
            "manifest_sha256": source_manifest_sha256,
            "files": provenance_files,
        },
        "toolchain": [
            {
                "component_id": tool_component_id,
                "name": tool_name,
                "version": tool_version,
                "component_kind": tool_kind,
                "sha256": SHA,
            }
        ],
        "outputs": [
            {
                "artifact_id": "index.artifact",
                "kind": "semantic_index",
                "sha256": output_digests[0],
                "path": "/fixture/semantic_index.json",
            },
            {
                "artifact_id": "bindings.artifact",
                "kind": "ap_bindings",
                "sha256": output_digests[1],
                "path": "/fixture/ap_bindings.json",
            },
            {
                "artifact_id": "graph.artifact",
                "kind": "contextual_influence_graph",
                "sha256": output_digests[2],
                "path": "/fixture/contextual_influence_graph.json",
            },
            {
                "artifact_id": "cones.artifact",
                "kind": "ap_influence_cones",
                "sha256": output_digests[3],
                "path": "/fixture/ap_influence_cones.json",
            },
        ],
        "stages": [
            {
                "stage_id": "stage.index",
                "name": "index",
                "status": "COMPLETE",
                "input_sha256": [SHA, source_manifest_sha256],
                "output_sha256": [output_digests[0]],
                "diagnostics": [],
            },
            {
                "stage_id": "stage.bind",
                "name": "bind",
                "status": "COMPLETE",
                "input_sha256": [SHA, output_digests[0]],
                "output_sha256": [output_digests[1]],
                "diagnostics": [],
            },
            {
                "stage_id": "stage.influence",
                "name": "influence",
                "status": "COMPLETE",
                "input_sha256": [output_digests[0], output_digests[1]],
                "output_sha256": [output_digests[2]],
                "diagnostics": [],
            },
            {
                "stage_id": "stage.cone",
                "name": "cone",
                "status": "COMPLETE",
                "input_sha256": [output_digests[1], output_digests[2]],
                "output_sha256": [output_digests[3]],
                "diagnostics": [],
            },
            {
                "stage_id": "stage.certificate",
                "name": "certificate",
                "status": "COMPLETE",
                "input_sha256": output_digests,
                "output_sha256": [],
                "diagnostics": [],
            },
        ],
        "unsupported_constructs": [],
        "started_at": "2026-07-18T00:00:00Z",
        "finished_at": "2026-07-18T00:00:01Z",
    }

    model_pack = {
        "schema_version": "1.0.0",
        "model_pack_id": "model.neutral",
        "model_pack_version": "1.0.0",
        "property_independent": True,
        "rule_policy": {
            "contract_id": "RIFT-PORTABILITY-1",
            "allowed_rule_classes": [
                "external_input_boundary", "parameter_registry", "protocol_parser_output",
                "callback_registration", "timer_lifecycle", "queue_lifecycle",
                "scheduler_entry", "scope_key", "persistence_boundary",
            ],
            "forbidden_rule_classes": [
                "per_property_slice", "hand_selected_dependency_path",
                "expected_answer_edge", "benchmark_case_id_branch",
            ],
        },
        "selectors": [selector()],
        "rules": [
            {
                "rule_id": "rule.source",
                "rule_class": "external_input_boundary",
                "match_selector_refs": ["selector.state"],
                "captures": [
                    {"capture_id": "capture.value", "semantic_role": "value", "selector_ref": "selector.state"}
                ],
                "semantics": {"operation": "source", "certainty": "modelled", "controllability": "direct"},
                "evidence_note": "Generic boundary semantics",
            }
        ],
    }

    return {
        "typed_property_ir.schema.json": property_ir,
        "semantic_index.schema.json": semantic_index,
        "ap_bindings.schema.json": bindings,
        "contextual_influence_graph.schema.json": graph,
        "ap_influence_cones.schema.json": cones,
        "analysis_certificate.schema.json": certificate,
        "model_pack.schema.json": model_pack,
    }


class Suite:
    def __init__(self, schema_dir: pathlib.Path) -> None:
        self.schema_dir = schema_dir
        self.schemas: dict[str, dict[str, Any]] = {}
        self.validators: dict[str, jsonschema.Draft7Validator] = {}
        self.checks = 0

    def load(self) -> None:
        for name in SCHEMA_FILES:
            path = self.schema_dir / name
            first = path.read_bytes()
            second = path.read_bytes()
            if first != second:
                raise AssertionError(f"non-deterministic read: {name}")
            schema = json.loads(first)
            jsonschema.Draft7Validator.check_schema(schema)
            if schema["$id"] != EXPECTED_IDS[name]:
                raise AssertionError(f"unstable $id for {name}: {schema['$id']}")
            canonical = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
            if json.loads(canonical) != schema:
                raise AssertionError(f"canonical JSON round trip changed {name}")
            self.schemas[name] = schema
            self.checks += 4

        ids = [schema["$id"] for schema in self.schemas.values()]
        if len(ids) != len(set(ids)):
            raise AssertionError("schema $id collision")
        self.checks += 1

        store = {schema["$id"]: schema for schema in self.schemas.values()}
        for name, schema in self.schemas.items():
            resolver = jsonschema.RefResolver.from_schema(schema, store=store)
            self.validators[name] = jsonschema.Draft7Validator(
                schema, resolver=resolver, format_checker=jsonschema.FormatChecker()
            )

    def valid(self, schema_name: str, instance: dict[str, Any], label: str) -> None:
        errors = sorted(self.validators[schema_name].iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            details = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:4])
            raise AssertionError(f"expected valid {label}: {details}")
        if schema_name == "analysis_certificate.schema.json":
            contract_errors = certificate_contract_errors(instance)
            if contract_errors:
                raise AssertionError(
                    f"expected valid {label}: " + "; ".join(contract_errors[:4])
                )
        self.checks += 1

    def invalid(self, schema_name: str, instance: dict[str, Any], label: str) -> None:
        schema_errors = list(self.validators[schema_name].iter_errors(instance))
        contract_errors = (
            certificate_contract_errors(instance)
            if schema_name == "analysis_certificate.schema.json" and not schema_errors
            else []
        )
        if not schema_errors and not contract_errors:
            raise AssertionError(f"expected invalid {label}")
        self.checks += 1

    def digest_sensitive(
        self,
        schema_name: str,
        instance: dict[str, Any],
        path: tuple[Any, ...],
        value: Any,
        label: str,
    ) -> None:
        mutated = copy.deepcopy(instance)
        replace_path(mutated, path, value)
        self.valid(schema_name, mutated, f"digest mutation {label}")
        if canonical_artifact_digest(mutated) == canonical_artifact_digest(instance):
            raise AssertionError(f"consumer field is not digest-sensitive: {label}")
        self.checks += 1

    def serializer_inventory(self) -> None:
        source_path = self.schema_dir.parent / "cli" / "production_main.cpp"
        source = source_path.read_text(encoding="utf-8")
        semantic_start = source.index("llvm::json::Object semantic_index_json")
        semantic_end = source.index("std::string binding_resolution", semantic_start)
        semantic_serializer = source[semantic_start:semantic_end]
        graph_start = source.index("llvm::json::Object contextual_node_json")
        graph_end = source.index("std::string cone_membership", graph_start)
        graph_serializer = source[graph_start:graph_end]
        certificate_start = source.index("llvm::json::Object certificate_json")
        certificate_end = source.index("std::uint32_t parse_u32", certificate_start)
        certificate_serializer = source[certificate_start:certificate_end]
        semantic_fields = (
            "identity_scheme", "canonical_compilation_database_sha256", "path_map_sha256",
            "input_manifest_sha256", "logical_root_ids", "source_identity_root",
            "translation_units", "input_files", "input_file_ids", "input_file_id",
            "logical_path", "sha256", "role", "byte_size",
            "entities", "abstract_objects", "semantic_nodes", "semantic_relations",
            "function_summaries", "callsites", "status", "diagnostics",
            "owner_function_id", "access_path", "abstract_object_id", "ast_kind",
            "callsite_id", "condition_node_ids", "uncertainty_reasons",
            "parameter_node_ids", "receiver_node_id", "return_node_id",
            "owned_node_ids", "relation_ids", "argument_node_ids",
            "argument_node_groups", "argument_is_address", "result_node_id",
        )
        graph_fields = (
            "semantic_node_ref", "semantic_node_kind", "relation_kind",
            "condition_node_ids", "conditions", "uncertainty_reasons", "diagnostics",
        )
        for field in semantic_fields:
            if f'{{"{field}",' not in semantic_serializer:
                raise AssertionError(f"semantic serializer omits required field {field}")
            self.checks += 1
        for field in graph_fields:
            if (
                f'{{"{field}",' not in graph_serializer
                and f'("{field}",' not in graph_serializer
            ):
                raise AssertionError(f"CIG serializer omits required field {field}")
            self.checks += 1
        certificate_fields = (
            "schema_version", "certificate_id", "analysis_id", "status",
            "analyzer", "environment_sha256", "build_manifest",
            "identity_policy", "manifest_sha256", "production_core_sha256",
            "schema_bundle_sha256", "core_tree_sha256", "environment",
            "digest", "variables", "inputs", "source_input_provenance",
            "toolchain", "outputs", "stages", "unsupported_constructs",
            "started_at", "finished_at",
        )
        for field in certificate_fields:
            if f'{{"{field}",' not in certificate_serializer:
                raise AssertionError(f"certificate serializer omits required field {field}")
            self.checks += 1
        required_source_fragments = (
            "capture_semantic_environment()",
            "{build_manifest_digest, environment.digest}",
            "append_length_prefixed(configuration, argument)",
            "{property.artifact_sha256, index.input_manifest_sha256,",
            "{analysis_id, configuration_digest, index_digest, bindings_digest,",
            "source_input_provenance_json(index)",
            "runtime_toolchain_json(binary)",
            '"cannot attest deleted mapped runtime object: "',
            '"component_kind"',
            '"sha256"',
        )
        for fragment in required_source_fragments:
            if fragment not in source:
                raise AssertionError(
                    f"certificate implementation omits contract fragment {fragment}"
                )
            self.checks += 1
        if "executable_sha256" in source:
            raise AssertionError("certificate serializer retains v1 toolchain digest name")
        self.checks += 1

    def run(self) -> None:
        self.load()
        self.serializer_inventory()
        positive = fixtures()
        for name, instance in positive.items():
            self.valid(name, instance, f"positive fixture {name}")

        # The 2.0.0 schema files are compatibility envelopes: their legacy
        # branches accept the unchanged 1.0.0 document shapes, while their v2
        # branches expose role-specific selector DNF and binding provenance.
        property_v2 = property_ir_v2_fixture(
            positive["typed_property_ir.schema.json"]
        )
        self.valid(
            "typed_property_ir.schema.json",
            property_v2,
            "role-DNF property v2",
        )
        bindings_v2 = ap_bindings_v2_fixture(
            positive["ap_bindings.schema.json"]
        )
        self.valid(
            "ap_bindings.schema.json",
            bindings_v2,
            "role-DNF bindings v2",
        )

        mutated = copy.deepcopy(positive["typed_property_ir.schema.json"])
        mutated["atomic_propositions"][0]["role_selector_groups"] = [
            {
                "group_id": "selector-group.state",
                "role": "state",
                "all_of": ["selector.state"],
            }
        ]
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "legacy property forbids v2 role selector groups",
        )
        mutated = copy.deepcopy(property_v2)
        mutated["atomic_propositions"][0]["selector_refs"] = ["selector.state"]
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "property v2 forbids legacy selector refs",
        )
        mutated = copy.deepcopy(property_v2)
        del mutated["atomic_propositions"][0]["role_selector_groups"]
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "property v2 requires role selector groups",
        )
        mutated = copy.deepcopy(property_v2)
        mutated["atomic_propositions"][0]["role_selector_groups"] = []
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "property v2 requires at least one role selector group",
        )
        mutated = copy.deepcopy(property_v2)
        mutated["atomic_propositions"][0]["role_selector_groups"][0]["all_of"] = []
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "role selector conjunction is nonempty",
        )
        mutated = copy.deepcopy(property_v2)
        mutated["atomic_propositions"][0]["role_selector_groups"][0]["all_of"] = [
            "selector.state",
            "selector.state",
        ]
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "role selector conjunction contains unique selector refs",
        )
        mutated = copy.deepcopy(property_v2)
        del mutated["atomic_propositions"][0]["role_selector_groups"][0]["group_id"]
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "role selector group has stable identity",
        )
        mutated = copy.deepcopy(property_v2)
        mutated["atomic_propositions"][0]["role_selector_groups"][0]["unexpected"] = True
        self.invalid(
            "typed_property_ir.schema.json",
            mutated,
            "role selector group is closed",
        )

        # Cross-reference closure is deliberately a C++ semantic-validation
        # responsibility.  JSON Schema only establishes the typed envelope.
        semantic_deferred = copy.deepcopy(property_v2)
        semantic_deferred["atomic_propositions"][0]["role_selector_groups"][0][
            "role"
        ] = "trigger"
        semantic_deferred["atomic_propositions"][0]["role_selector_groups"][0][
            "all_of"
        ] = ["selector.not-declared"]
        self.valid(
            "typed_property_ir.schema.json",
            semantic_deferred,
            "role closure and selector references are deferred to semantic validation",
        )

        mutated = copy.deepcopy(positive["ap_bindings.schema.json"])
        mutated["bindings"][0]["candidates"][0]["selector_group_id"] = (
            "selector-group.state"
        )
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "legacy bindings forbid v2 selector group provenance",
        )
        mutated = copy.deepcopy(bindings_v2)
        del mutated["bindings"][0]["candidates"][0]["selector_group_id"]
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "bindings v2 require selector group provenance",
        )
        mutated = copy.deepcopy(bindings_v2)
        mutated["binding_policy"]["role_selector_logic"] = "flat-union/1"
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "bindings v2 fix role selector logic",
        )
        mutated = copy.deepcopy(bindings_v2)
        mutated["binding_policy"]["cross_role_consistency"] = "CONFIRMED"
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "bindings v2 do not overclaim cross-role consistency",
        )
        mutated = copy.deepcopy(bindings_v2)
        mutated["binding_policy"]["similarity_is_confirmation"] = True
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "bindings v2 similarity cannot confirm",
        )
        mutated = copy.deepcopy(bindings_v2)
        mutated["binding_policy"]["joint_role_binding"] = True
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "bindings v2 rejects legacy policy fields",
        )
        mutated = copy.deepcopy(positive["ap_bindings.schema.json"])
        mutated["bindings"][0]["resolution"] = "PARTIAL"
        self.invalid(
            "ap_bindings.schema.json",
            mutated,
            "legacy bindings reject v2 partial resolution",
        )
        partial = copy.deepcopy(bindings_v2)
        partial["bindings"][0]["resolution"] = "PARTIAL"
        partial["bindings"][0]["candidates"][0]["status"] = "CANDIDATE"
        self.valid(
            "ap_bindings.schema.json",
            partial,
            "bindings v2 partial resolution",
        )

        # Every artifact root is closed to accidental or answer-bearing fields.
        for name, instance in positive.items():
            mutated = copy.deepcopy(instance)
            mutated["unexpected_field"] = True
            self.invalid(name, mutated, f"closed root {name}")

        prop = copy.deepcopy(positive["typed_property_ir.schema.json"])
        prop["atomic_propositions"][0]["roles"] = ["unsupported_role"]
        self.invalid("typed_property_ir.schema.json", prop, "closed AP role vocabulary")
        prop = copy.deepcopy(positive["typed_property_ir.schema.json"])
        prop["selectors"][0]["kind"] = "untyped_name"
        self.invalid("typed_property_ir.schema.json", prop, "selector must be typed")

        semantic = positive["semantic_index.schema.json"]
        for field in (
            "identity_scheme", "canonical_compilation_database_sha256",
            "path_map_sha256", "input_manifest_sha256", "logical_root_ids",
            "source_identity_root", "input_files", "abstract_objects",
            "function_summaries", "callsites", "status", "diagnostics",
        ):
            mutated = copy.deepcopy(semantic)
            del mutated[field]
            self.invalid("semantic_index.schema.json", mutated, f"lossless index field {field}")
        for collection, nested in (
            ("input_files", 0),
            ("abstract_objects", 0),
            ("semantic_nodes", 0),
            ("semantic_relations", 0),
            ("function_summaries", 0),
            ("callsites", 0),
        ):
            mutated = copy.deepcopy(semantic)
            mutated[collection][nested]["unexpected_field"] = True
            self.invalid("semantic_index.schema.json", mutated, f"closed index {collection}")
        mutated = copy.deepcopy(semantic)
        mutated["identity_scheme"] = "physical-path/1"
        self.invalid("semantic_index.schema.json", mutated, "fixed logical identity scheme")
        mutated = copy.deepcopy(semantic)
        mutated["logical_root_ids"] = ["Source"]
        self.invalid("semantic_index.schema.json", mutated, "portable logical root ID")
        mutated = copy.deepcopy(semantic)
        mutated["source_identity_root"] = "/physical/source"
        self.invalid("semantic_index.schema.json", mutated, "no physical identity root")
        mutated = copy.deepcopy(semantic)
        mutated["translation_units"][0]["source_file"] = "/physical/source.cc"
        self.invalid("semantic_index.schema.json", mutated, "no physical TU source path")
        mutated = copy.deepcopy(semantic)
        del mutated["translation_units"][0]["input_file_ids"]
        self.invalid("semantic_index.schema.json", mutated, "TU input-file refs are explicit")
        mutated = copy.deepcopy(semantic)
        mutated["input_files"][0]["logical_path"] = "/physical/source.cc"
        self.invalid("semantic_index.schema.json", mutated, "no physical loaded-input path")
        mutated = copy.deepcopy(semantic)
        mutated["input_files"][0]["role"] = "unknown"
        self.invalid("semantic_index.schema.json", mutated, "closed input-file role")
        mutated = copy.deepcopy(semantic)
        mutated["input_files"][0]["byte_size"] = -1
        self.invalid("semantic_index.schema.json", mutated, "nonnegative input-file size")
        mutated = copy.deepcopy(semantic)
        mutated["semantic_nodes"][0]["location"]["file"] = "/physical/source.cc"
        self.invalid("semantic_index.schema.json", mutated, "no physical semantic location")
        mutated = copy.deepcopy(semantic)
        mutated["semantic_relations"][0]["evidence"][0]["location"] = {
            "file": "/physical/source.cc",
            "line": 1,
            "column": 1,
            "location_kind": "spelling",
        }
        self.invalid("semantic_index.schema.json", mutated, "no physical evidence location")
        relocated = copy.deepcopy(semantic)
        first_raw_database_sha256 = "1" * 64
        second_raw_database_sha256 = "2" * 64
        if first_raw_database_sha256 == second_raw_database_sha256:
            raise AssertionError("raw database relocation fixture did not change")
        if canonical_artifact_digest(relocated) != canonical_artifact_digest(semantic):
            raise AssertionError("raw database relocation polluted semantic index bytes")
        self.checks += 1
        mutated = copy.deepcopy(semantic)
        mutated["compilation_database_sha256"] = first_raw_database_sha256
        self.invalid("semantic_index.schema.json", mutated, "raw database digest is provenance-only")
        mutated = copy.deepcopy(semantic)
        del mutated["semantic_nodes"][0]["owner_function_id"]
        self.invalid("semantic_index.schema.json", mutated, "node owner is explicit")
        mutated = copy.deepcopy(semantic)
        del mutated["semantic_nodes"][0]["access_path"]
        self.invalid("semantic_index.schema.json", mutated, "node access path is explicit")
        mutated = copy.deepcopy(semantic)
        del mutated["semantic_nodes"][0]["abstract_object_id"]
        self.invalid("semantic_index.schema.json", mutated, "node object is explicit")
        mutated = copy.deepcopy(semantic)
        del mutated["semantic_nodes"][0]["ast_kind"]
        self.invalid("semantic_index.schema.json", mutated, "node AST kind is explicit")
        mutated = copy.deepcopy(semantic)
        del mutated["semantic_relations"][0]["callsite_id"]
        self.invalid("semantic_index.schema.json", mutated, "relation callsite is explicit")
        mutated = copy.deepcopy(semantic)
        del mutated["semantic_relations"][0]["condition_node_ids"]
        self.invalid("semantic_index.schema.json", mutated, "relation conditions are replayable")
        mutated = copy.deepcopy(semantic)
        mutated["semantic_relations"][0]["condition_node_ids"] = ["semantic.state", "semantic.state"]
        self.invalid("semantic_index.schema.json", mutated, "relation conditions are unique")
        mutated = copy.deepcopy(semantic)
        mutated["semantic_relations"][0]["certainty"] = "unknown"
        self.invalid("semantic_index.schema.json", mutated, "unknown relation has reason")
        semantic_node_kinds = (
            "declaration", "definition", "expression", "value", "memory",
            "callsite", "returnsite", "control", "synthetic", "unknown",
        )
        relation_kinds = (
            "defines", "uses", "loads", "stores", "data", "controls", "calls",
            "returns", "object", "field", "aliases", "contains", "maps_to", "unknown",
        )
        input_file_roles = (
            "main", "user_header", "generated", "system", "toolchain",
        )
        if len(semantic_node_kinds) != len(set(semantic_node_kinds)):
            raise AssertionError("semantic-node kind strings collide")
        if len(relation_kinds) != len(set(relation_kinds)):
            raise AssertionError("semantic-relation kind strings collide")
        if len(input_file_roles) != len(set(input_file_roles)):
            raise AssertionError("input-file role strings collide")
        for kind in semantic_node_kinds:
            mutated = copy.deepcopy(semantic)
            mutated["semantic_nodes"][0]["node_kind"] = kind
            self.valid("semantic_index.schema.json", mutated, f"semantic node kind {kind}")
        for kind in relation_kinds:
            mutated = copy.deepcopy(semantic)
            mutated["semantic_relations"][0]["kind"] = kind
            self.valid("semantic_index.schema.json", mutated, f"semantic relation kind {kind}")
        for role in input_file_roles:
            mutated = copy.deepcopy(semantic)
            mutated["input_files"][0]["role"] = role
            self.valid("semantic_index.schema.json", mutated, f"input-file role {role}")
        for path, value, label in (
            (("canonical_compilation_database_sha256",), "2" * 64, "canonical compile DB digest"),
            (("path_map_sha256",), "3" * 64, "path-map digest"),
            (("input_manifest_sha256",), "5" * 64, "input manifest digest"),
            (("logical_root_ids",), ["build", "source"], "logical root descriptors"),
            (("translation_units", 0, "command_sha256"), "4" * 64, "canonical command digest"),
            (("translation_units", 0, "input_file_ids"), [], "TU input-file closure"),
            (("input_files", 0, "sha256"), "6" * 64, "loaded input content"),
            (("input_files", 0, "role"), "user_header", "loaded input role"),
            (("input_files", 0, "byte_size"), 129, "loaded input byte size"),
            (("abstract_objects", 0, "abstraction"), "summary", "object abstraction"),
            (("semantic_nodes", 0, "owner_function_id"), None, "node owner"),
            (("semantic_nodes", 0, "access_path", "dereference_depth"), 1, "node access path"),
            (("semantic_nodes", 0, "abstract_object_id"), None, "node object"),
            (("semantic_nodes", 0, "ast_kind"), "DeclRefExpr", "node AST kind"),
            (("semantic_relations", 0, "callsite_id"), None, "relation callsite"),
            (("semantic_relations", 0, "condition_node_ids"), [], "relation conditions"),
            (("semantic_relations", 0, "uncertainty_reasons"), ["conservative"], "relation uncertainty"),
            (("function_summaries", 0, "return_node_id"), "semantic.state", "function return"),
            (("function_summaries", 0, "status"), "CONSERVATIVE_INCOMPLETE", "function status"),
            (("callsites", 0, "receiver_node_id"), "semantic.state", "callsite receiver"),
            (("callsites", 0, "direct"), True, "callsite dispatch class"),
            (("status",), "CONSERVATIVE_INCOMPLETE", "index status"),
            (("diagnostics",), ["diagnostic"], "index diagnostics"),
        ):
            self.digest_sensitive(
                "semantic_index.schema.json", semantic, path, value, label
            )

        bindings = copy.deepcopy(positive["ap_bindings.schema.json"])
        candidate = bindings["bindings"][0]["candidates"][0]
        candidate["evidence"] = [evidence("name_similarity", "may"), evidence("llm_similarity", "may")]
        self.invalid("ap_bindings.schema.json", bindings, "similarity-only confirmation")
        candidate["status"] = "CANDIDATE"
        bindings["bindings"][0]["resolution"] = "AMBIGUOUS"
        bindings["bindings"][0]["candidates"].append(copy.deepcopy(candidate))
        bindings["bindings"][0]["candidates"][1]["binding_id"] = "binding.state.alternate"
        self.valid("ap_bindings.schema.json", bindings, "similarity may recall a candidate")
        bindings = copy.deepcopy(positive["ap_bindings.schema.json"])
        bindings["bindings"][0]["candidates"][0]["semantic_node_refs"] = []
        self.invalid("ap_bindings.schema.json", bindings, "confirmed site is concrete")

        graph = positive["contextual_influence_graph.schema.json"]
        required_dimensions = (
            "entity", "abstract_object", "field_path", "call_context", "lifecycle_phase",
            "task_context", "scope", "generation", "location",
        )
        for dimension in required_dimensions:
            mutated = copy.deepcopy(graph)
            del mutated["nodes"][0][dimension]
            self.invalid("contextual_influence_graph.schema.json", mutated, f"node dimension {dimension}")
        mutated = copy.deepcopy(graph)
        mutated["edges"][0]["certainty"] = "modelled"
        self.invalid("contextual_influence_graph.schema.json", mutated, "modelled edge without model evidence")
        mutated["edges"][0]["evidence"].append(evidence("model_rule", "modelled"))
        self.valid("contextual_influence_graph.schema.json", mutated, "modelled edge with rule evidence")
        mutated = copy.deepcopy(graph)
        mutated["edges"][0]["certainty"] = "unknown"
        self.invalid("contextual_influence_graph.schema.json", mutated, "unknown edge without reason")
        mutated = copy.deepcopy(graph)
        del mutated["nodes"][0]["semantic_node_ref"]
        self.invalid("contextual_influence_graph.schema.json", mutated, "CIG node traces to semantic node")
        mutated = copy.deepcopy(graph)
        del mutated["nodes"][0]["semantic_node_kind"]
        self.invalid("contextual_influence_graph.schema.json", mutated, "CIG preserves semantic node kind")
        mutated = copy.deepcopy(graph)
        del mutated["edges"][0]["condition_node_ids"]
        self.invalid("contextual_influence_graph.schema.json", mutated, "CIG edge conditions are replayable")
        mutated = copy.deepcopy(graph)
        mutated["edges"][0]["condition_node_ids"] = ["cig.state", "cig.state"]
        self.invalid("contextual_influence_graph.schema.json", mutated, "CIG condition IDs are unique")
        mutated = copy.deepcopy(graph)
        mutated["nodes"][0]["unexpected_field"] = True
        self.invalid("contextual_influence_graph.schema.json", mutated, "closed CIG node")
        mutated = copy.deepcopy(graph)
        mutated["nodes"][0]["location"]["file"] = "/physical/source.cc"
        self.invalid("contextual_influence_graph.schema.json", mutated, "no physical CIG location")
        mutated = copy.deepcopy(graph)
        mutated["edges"][0]["unexpected_field"] = True
        self.invalid("contextual_influence_graph.schema.json", mutated, "closed CIG edge")
        mutated = copy.deepcopy(graph)
        del mutated["diagnostics"]
        self.invalid("contextual_influence_graph.schema.json", mutated, "CIG diagnostics are explicit")
        mutated = copy.deepcopy(graph)
        mutated["schema_version"] = "1.0.0"
        self.invalid("contextual_influence_graph.schema.json", mutated, "lossy CIG v1 is rejected")
        for kind in semantic_node_kinds:
            mutated = copy.deepcopy(graph)
            mutated["nodes"][0]["semantic_node_kind"] = kind
            self.valid("contextual_influence_graph.schema.json", mutated, f"CIG semantic node kind {kind}")
        for kind in relation_kinds:
            mutated = copy.deepcopy(graph)
            mutated["edges"][0]["relation_kind"] = kind
            self.valid("contextual_influence_graph.schema.json", mutated, f"CIG relation kind {kind}")
        for path, value, label in (
            (("nodes", 0, "semantic_node_ref"), "semantic.alternate", "semantic provenance"),
            (("nodes", 0, "semantic_node_kind"), "control", "exact semantic kind"),
            (("nodes", 0, "node_kind"), "predicate", "projected node kind"),
            (("nodes", 0, "field_path"), ["ready", "nested"], "field path"),
            (("nodes", 0, "lifecycle_phase"), "committed", "lifecycle phase"),
            (("nodes", 0, "call_context", "truncated"), True, "call context"),
            (("nodes", 0, "scope", "status"), "summary", "scope identity"),
            (("nodes", 0, "generation", "reuse_possible"), False, "generation"),
            (("edges", 0, "relation_kind"), "field", "exact relation kind"),
            (("edges", 0, "kind"), "memory_flow", "projected edge kind"),
            (("edges", 0, "condition_node_ids"), [], "replay conditions"),
            (("edges", 0, "conditions"), [], "compatibility condition projection"),
            (("edges", 0, "uncertainty_reasons"), ["conservative"], "edge uncertainty"),
            (("status",), "CONSERVATIVE_INCOMPLETE", "graph status"),
            (("diagnostics",), ["diagnostic"], "graph diagnostics"),
        ):
            self.digest_sensitive(
                "contextual_influence_graph.schema.json", graph, path, value, label
            )

        cones = copy.deepcopy(positive["ap_influence_cones.schema.json"])
        cones["ranking_never_prunes"] = False
        self.invalid("ap_influence_cones.schema.json", cones, "ranking cannot prune cone")
        cones = copy.deepcopy(positive["ap_influence_cones.schema.json"])
        account = cones["cones"][0]["candidate_accounting"][0]
        account["disposition"] = "UNRESOLVED"
        account["uncertainty_reasons"] = []
        self.invalid("ap_influence_cones.schema.json", cones, "unresolved candidate has reason")

        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        del certificate["unsupported_constructs"]
        self.invalid("analysis_certificate.schema.json", certificate, "certificate reports unsupported constructs")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["core_tree_sha256"] = "not-a-digest"
        self.invalid("analysis_certificate.schema.json", certificate, "certificate hashes core")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["status"] = "CONSERVATIVE_INCOMPLETE"
        certificate["stages"][1]["status"] = "CONSERVATIVE_INCOMPLETE"
        certificate["stages"][4]["status"] = "CONSERVATIVE_INCOMPLETE"
        self.valid("analysis_certificate.schema.json", certificate, "honest incomplete certificate")
        certificate["status"] = "COMPLETE"
        self.invalid("analysis_certificate.schema.json", certificate, "fake COMPLETE certificate")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["outputs"] = []
        self.invalid("analysis_certificate.schema.json", certificate, "certificate has exactly four outputs")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        changed_output = "1" * 64
        certificate["outputs"][0]["sha256"] = changed_output
        certificate["stages"][0]["output_sha256"] = [changed_output]
        certificate["stages"][1]["input_sha256"][1] = changed_output
        certificate["stages"][2]["input_sha256"][0] = changed_output
        certificate["stages"][4]["input_sha256"][0] = changed_output
        self.invalid("analysis_certificate.schema.json", certificate, "certificate ID binds all output digests")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["stages"].pop()
        self.invalid("analysis_certificate.schema.json", certificate, "certificate has all five stages")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        del certificate["build_manifest"]
        self.invalid("analysis_certificate.schema.json", certificate, "certificate requires build manifest")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["build_manifest"]["production_core_sha256"] = "1" * 64
        self.invalid("analysis_certificate.schema.json", certificate, "build manifest matches top-level core")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["build_manifest"]["schema_bundle_sha256"] = "1" * 64
        self.invalid("analysis_certificate.schema.json", certificate, "build manifest matches top-level schemas")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        del certificate["toolchain"][0]["component_kind"]
        self.invalid("analysis_certificate.schema.json", certificate, "toolchain component kind is explicit")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["toolchain"][0]["executable_sha256"] = certificate["toolchain"][0].pop("sha256")
        self.invalid("analysis_certificate.schema.json", certificate, "v1 executable-only toolchain digest is rejected")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["environment"]["variables"][0]["value"] = "plaintext"
        self.invalid("analysis_certificate.schema.json", certificate, "environment never exposes plaintext")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["environment"]["variables"][0]["name"] = "AWS_SECRET_ACCESS_KEY"
        self.invalid("analysis_certificate.schema.json", certificate, "environment whitelist excludes secrets")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["environment"]["variables"][0]["value_sha256"] = SHA
        self.invalid("analysis_certificate.schema.json", certificate, "absent environment value has null digest")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["environment"]["variables"][0]["present"] = True
        self.invalid("analysis_certificate.schema.json", certificate, "present environment value has a digest")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["environment"]["variables"][0], certificate["environment"]["variables"][1] = (
            certificate["environment"]["variables"][1],
            certificate["environment"]["variables"][0],
        )
        self.invalid("analysis_certificate.schema.json", certificate, "environment order is deterministic")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["environment"]["digest"] = "1" * 64
        self.invalid("analysis_certificate.schema.json", certificate, "environment aggregate is verified")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["analyzer"]["environment_sha256"] = "1" * 64
        self.invalid("analysis_certificate.schema.json", certificate, "analyzer binds environment aggregate")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["inputs"][2]["path"] = "/not/a/real/artifact"
        self.invalid("analysis_certificate.schema.json", certificate, "source-input manifest has no fake path")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["inputs"][0].pop("path")
        self.invalid("analysis_certificate.schema.json", certificate, "file artifact records its real path")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["outputs"][0].pop("path")
        self.invalid("analysis_certificate.schema.json", certificate, "output artifact records its real path")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["source_input_provenance"]["manifest_sha256"] = "1" * 64
        self.invalid("analysis_certificate.schema.json", certificate, "source provenance binds source-input descriptor")
        certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
        certificate["source_input_provenance"]["files"][0]["logical_path"] = (
            "riftpath://v1/toolchain/system/header.h"
        )
        certificate["source_input_provenance"]["files"][0]["input_file_id"] = source_input_id(
            certificate["source_input_provenance"]["files"][0]
        )
        replacement_manifest = source_manifest_digest(
            certificate["source_input_provenance"]["files"]
        )
        certificate["source_input_provenance"]["manifest_sha256"] = replacement_manifest
        certificate["inputs"][2]["sha256"] = replacement_manifest
        certificate["stages"][0]["input_sha256"][1] = replacement_manifest
        self.invalid("analysis_certificate.schema.json", certificate, "only toolchain predefines may lack a path")

        with tempfile.TemporaryDirectory(prefix="rift-certificate-source-") as directory:
            source_path = pathlib.Path(directory) / "input.cc"
            payload = b"int value = 1;\n"
            source_path.write_bytes(payload)
            source_file = {
                "input_file_id": "",
                "logical_path": "riftpath://v1/source/input.cc",
                "role": "main",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "byte_size": len(payload),
                "observed_paths": [str(source_path)],
            }
            source_file["input_file_id"] = source_input_id(source_file)
            source_manifest = source_manifest_digest([source_file])
            file_certificate = copy.deepcopy(positive["analysis_certificate.schema.json"])
            file_certificate["inputs"][2]["sha256"] = source_manifest
            file_certificate["source_input_provenance"] = {
                "manifest_sha256": source_manifest,
                "files": [source_file],
            }
            file_certificate["stages"][0]["input_sha256"][1] = source_manifest
            self.valid("analysis_certificate.schema.json", file_certificate, "rehashable source provenance")

            missing = copy.deepcopy(file_certificate)
            missing["source_input_provenance"]["files"][0]["observed_paths"] = [
                str(pathlib.Path(directory) / "missing.cc")
            ]
            self.invalid("analysis_certificate.schema.json", missing, "missing source provenance path")

            relative = copy.deepcopy(file_certificate)
            relative["source_input_provenance"]["files"][0]["observed_paths"] = ["input.cc"]
            self.invalid("analysis_certificate.schema.json", relative, "source provenance path must be absolute")

            source_path.write_bytes(b"int value = 2;\n")
            self.invalid("analysis_certificate.schema.json", file_certificate, "changed source input bytes")

        model = positive["model_pack.schema.json"]
        for forbidden in (
            "per_property_slice", "hand_selected_dependency_path",
            "expected_answer_edge", "benchmark_case_id_branch",
        ):
            mutated = copy.deepcopy(model)
            mutated["rules"][0]["rule_class"] = forbidden
            self.invalid("model_pack.schema.json", mutated, f"forbidden model rule {forbidden}")
        mutated = copy.deepcopy(model)
        mutated["property_independent"] = False
        self.invalid("model_pack.schema.json", mutated, "model pack must be property-independent")
        mutated = copy.deepcopy(model)
        mutated["rules"][0]["property_id"] = "property.response"
        self.invalid("model_pack.schema.json", mutated, "rule cannot select a property")
        mutated = copy.deepcopy(model)
        mutated["rules"][0]["rule_class"] = "timer_lifecycle"
        self.invalid("model_pack.schema.json", mutated, "rule class constrains operation semantics")

        # Match the byte-level tree identity emitted by the production
        # analysis certificate. The shipped bytes, including reference-file
        # formatting, are part of the schema contract.
        digest = hashlib.sha256()
        for name in sorted(self.schemas):
            relative = name.encode("utf-8")
            payload = (self.schema_dir / name).read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
        print(
            f"PASS schemas={len(self.schemas)} checks={self.checks} "
            f"schema_tree_sha256={digest.hexdigest()}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        Suite(args.schema_dir.resolve()).run()
    except (AssertionError, OSError, ValueError, jsonschema.SchemaError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
