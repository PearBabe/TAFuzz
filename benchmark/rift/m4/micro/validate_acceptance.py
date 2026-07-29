#!/usr/bin/env python3
"""Validate M4 micro inputs or a sealed production-artifact analyzer run."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from command_adapter import (
    DEFAULT_ADAPTER,
    OUTPUT_NAMES,
    argument_file_entries,
    load_adapter,
    render_commands,
    sandbox_command,
)
from common import (
    AcceptanceError,
    HERE,
    LOCAL_SCHEMA_DIR,
    PRODUCTION_SCHEMA_DIR,
    PRODUCTION_SCHEMA_FILES,
    SCHEMA_MIGRATION_LEDGER,
    WORKSPACE,
    assert_no_answer_tokens,
    build_property_ir,
    read_json,
    production_schema_tree_sha256,
    sha256_file,
    unique_by,
    validate_schema,
)


RUN_MANIFEST = "analysis_run_manifest.json"
ARTIFACT_SCHEMAS = {
    "semantic_index": "semantic_index.schema.json",
    "ap_bindings": "ap_bindings.schema.json",
    "contextual_influence_graph": "contextual_influence_graph.schema.json",
    "ap_influence_cones": "ap_influence_cones.schema.json",
}
FORBIDDEN_MANIFEST_KEYS = {
    "category",
    "case_relation",
    "relation",
    "relations",
    "source_anchors",
    "controllability",
    "fuzzable_frontier",
    "expected_edges",
    "ground_truth_file",
}
IDENTITY_SCHEME = "rift.identity/2.0.0"
PATH_MAP_SCHEME = "rift.path-map/1.0.0"
MIGRATABLE_SCHEMA_NAMES = {
    "semantic_index.schema.json",
    "contextual_influence_graph.schema.json",
    "analysis_certificate.schema.json",
    "typed_property_ir.schema.json",
    "ap_bindings.schema.json",
}
MIGRATION_REASONS = {
    "semantic_index.schema.json": "pre-formal-run lossless/provenance audit fix",
    "contextual_influence_graph.schema.json": "pre-formal-run lossless/provenance audit fix",
    "analysis_certificate.schema.json": "pre-formal-run lossless/provenance audit fix",
    "typed_property_ir.schema.json": "pre-final-run role-DNF binding audit fix",
    "ap_bindings.schema.json": "pre-final-run role-DNF binding audit fix",
}
LOGICAL_PATH_PATTERN = re.compile(
    r"^riftpath://v1/(?P<root>[a-z][a-z0-9._-]{0,63})/(?P<suffix>[^\s]*)$"
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parsed_timestamp(value: str, label: str) -> datetime.datetime:
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AcceptanceError(f"invalid {label} timestamp") from error
    if parsed.tzinfo is None:
        raise AcceptanceError(f"{label} timestamp lacks a timezone")
    return parsed


def _stable_id(prefix: str, material: str) -> str:
    return f"{prefix}:{_sha256_text(material)}"


def _length_prefixed(values: list[str]) -> bytes:
    material = bytearray()
    for value in values:
        payload = value.encode("utf-8")
        material.extend(len(payload).to_bytes(8, "big"))
        material.extend(payload)
    return bytes(material)


def _stable_id_bytes(prefix: str, material: bytes) -> str:
    return f"{prefix}:{hashlib.sha256(material).hexdigest()}"


def _active_schema_contract(
    frozen_schema_entries: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Validate the explicit, non-expanding pre-run schema migration ledger."""
    ledger = read_json(SCHEMA_MIGRATION_LEDGER)
    if set(ledger) != {"schema_version", "approved_at", "migrations"}:
        raise AcceptanceError("schema migration ledger has unexpected fields")
    if ledger["schema_version"] != "rift.m4.schema-migration-ledger.v1":
        raise AcceptanceError("unsupported schema migration ledger version")
    if not re.fullmatch(
        r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:Z|[+-][0-9]{2}:[0-9]{2})",
        str(ledger["approved_at"]),
    ):
        raise AcceptanceError("schema migration ledger approval time is invalid")
    migrations = unique_by(ledger["migrations"], "name", "schema migration")
    if not set(migrations) <= MIGRATABLE_SCHEMA_NAMES:
        raise AcceptanceError("schema migration ledger expands beyond its five audited schemas")
    for name, migration in migrations.items():
        if set(migration) != {"name", "old", "new", "reason"}:
            raise AcceptanceError(f"malformed schema migration ledger entry for {name}")
        if migration["reason"] != MIGRATION_REASONS[name]:
            raise AcceptanceError(f"schema migration reason changed for {name}")
        old_id = str(migration["old"].get("schema_id"))
        new_id = str(migration["new"].get("schema_id"))
        if not old_id.endswith("/1.0.0") or not new_id.endswith("/2.0.0"):
            raise AcceptanceError(
                f"schema migration is not the approved 1.0.0 to 2.0.0 transition: {name}"
            )
        current_path = PRODUCTION_SCHEMA_DIR / name
        current = {
            "schema_id": read_json(current_path).get("$id"),
            "sha256": sha256_file(current_path),
        }
        if migration["new"] != current:
            raise AcceptanceError(f"schema migration target is stale for {name}")

    active: dict[str, dict[str, Any]] = {}
    observed_drift: set[str] = set()
    for name, frozen in frozen_schema_entries.items():
        path = PRODUCTION_SCHEMA_DIR / name
        current = {
            "schema_id": read_json(path).get("$id"),
            "sha256": sha256_file(path),
        }
        active[name] = current
        frozen_identity = {
            "schema_id": frozen["schema_id"],
            "sha256": frozen["sha256"],
        }
        if current == frozen_identity:
            continue
        observed_drift.add(name)
        migration = migrations.get(name)
        if migration is None:
            raise AcceptanceError(f"unapproved production schema change: {name}")
        if migration["old"] != frozen_identity or migration["new"] != current:
            raise AcceptanceError(f"schema migration endpoint mismatch for {name}")
    if observed_drift and set(migrations) != observed_drift:
        raise AcceptanceError("schema migration ledger does not exactly match active schema drift")
    return active


def _safe_path(root: Path, relative: str, label: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise AcceptanceError(f"{label} must be a non-empty relative path")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise AcceptanceError(f"{label} escapes its artifact root: {relative}") from error
    if not path.is_file():
        raise AcceptanceError(f"missing {label}: {path}")
    return path


def _verify_digest(root: Path, artifact: dict[str, Any], label: str) -> Path:
    path = _safe_path(root, artifact["path"], label)
    observed = sha256_file(path)
    if observed != artifact["sha256"]:
        raise AcceptanceError(
            f"{label} digest mismatch: manifest={artifact['sha256']} observed={observed}"
        )
    return path


def _read_verified_json(
    root: Path, artifact: dict[str, Any], label: str
) -> tuple[Path, dict[str, Any]]:
    path = _safe_path(root, artifact["path"], label)
    payload = path.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    if observed != artifact["sha256"]:
        raise AcceptanceError(
            f"{label} digest mismatch: manifest={artifact['sha256']} observed={observed}"
        )
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} is not a JSON object")
    return path, value


def _forbidden_keys(value: Any, path: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key in FORBIDDEN_MANIFEST_KEYS:
                matches.append(child_path)
            matches.extend(_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(_forbidden_keys(child, f"{path}/{index}"))
    return matches


def validate_bundle(bundle: Path, expected_cases: int | None = 120) -> dict[str, Any]:
    bundle = bundle.resolve()
    manifest_path = bundle / "manifest.json"
    manifest = read_json(manifest_path)
    validate_schema(
        manifest,
        LOCAL_SCHEMA_DIR / "analyzer_input_manifest.schema.json",
        "M4 micro input manifest",
    )
    forbidden = _forbidden_keys(manifest)
    if forbidden:
        raise AcceptanceError(f"answer-bearing manifest fields found: {forbidden}")
    if expected_cases is not None and manifest["case_count"] != expected_cases:
        raise AcceptanceError(
            f"expected {expected_cases} cases, got {manifest['case_count']}"
        )
    cases = unique_by(manifest["cases"], "case_id", "input case")
    if len(cases) != manifest["case_count"]:
        raise AcceptanceError("case_count does not match unique manifest cases")
    expected_case_ids = {
        f"case_{index:03d}" for index in range(1, manifest["case_count"] + 1)
    }
    if set(cases) != expected_case_ids:
        raise AcceptanceError("opaque case IDs are not contiguous")

    schema_entries = unique_by(manifest["production_schemas"], "name", "production schema")
    if set(schema_entries) != set(PRODUCTION_SCHEMA_FILES):
        raise AcceptanceError("production schema set differs from the frozen contract")
    for name, entry in schema_entries.items():
        expected_path = PRODUCTION_SCHEMA_DIR / name
        if entry["path"] != expected_path.relative_to(WORKSPACE).as_posix():
            raise AcceptanceError(f"production schema path mismatch for {name}")
    _active_schema_contract(schema_entries)
    production_schema_tree_sha256()

    global_compile_path = _verify_digest(
        bundle, manifest["global_compile_database"], "global compile database"
    )
    global_commands = read_json(global_compile_path)
    if not isinstance(global_commands, list) or len(global_commands) != len(cases):
        raise AcceptanceError("global compile database does not cover every case exactly once")
    global_by_file = unique_by(global_commands, "file", "global compile command")

    counted_aps = 0
    language_counts: Counter[str] = Counter()
    for case_id, case in cases.items():
        source_path = _verify_digest(bundle, case["source"], f"{case_id} source")
        compile_path = _verify_digest(
            bundle, case["compile_database"], f"{case_id} compile database"
        )
        property_path = _verify_digest(bundle, case["property_ir"], f"{case_id} property IR")
        source_text = source_path.read_text(encoding="utf-8")
        assert_no_answer_tokens(source_text, f"{case_id} source")
        if re.search(r"RIFT_(?:SOURCE|NODE|AP):", source_text):
            raise AcceptanceError(f"{case_id} leaks generator markers")
        if re.search(r"\b(?:source|node)_[a-z0-9_]+\b", source_text):
            raise AcceptanceError(f"{case_id} leaks generator-semantic identifiers")
        commands = read_json(compile_path)
        if not isinstance(commands, list) or len(commands) != 1:
            raise AcceptanceError(f"{case_id} requires one raw compile command")
        command = commands[0]
        if command.get("directory") != "../.." or command.get("file") != case["source"]["path"]:
            raise AcceptanceError(f"{case_id} compile command is not relocatable")
        expected_global = {**command, "directory": "."}
        if global_by_file.get(command["file"]) != expected_global:
            raise AcceptanceError(f"{case_id} command differs from global compile database")
        assert_no_answer_tokens(json.dumps(command), f"{case_id} compile command")

        property_ir = read_json(property_path)
        validate_schema(
            property_ir,
            PRODUCTION_SCHEMA_DIR / "typed_property_ir.schema.json",
            f"{case_id} property IR",
        )
        assert_property_id_domains_disjoint(property_ir, case_id)
        expected_property = build_property_ir(
            case_id,
            source_text,
            case["source"]["path"],
            [ap["ap_id"] for ap in property_ir["atomic_propositions"]],
        )
        if property_ir != expected_property:
            raise AcceptanceError(
                f"{case_id} Property IR is not a deterministic projection of public source"
            )
        if len(property_ir["atomic_propositions"]) != case["ap_count"]:
            raise AcceptanceError(f"{case_id} ap_count mismatch")
        counted_aps += case["ap_count"]
        language_counts[case["language"]] += 1
    if counted_aps != manifest["ap_count"]:
        raise AcceptanceError("manifest ap_count mismatch")
    if expected_cases == 120 and language_counts != Counter({"c": 60, "c++": 60}):
        raise AcceptanceError(f"unexpected language distribution: {dict(language_counts)}")
    assert_no_answer_tokens(manifest_path.read_text(encoding="utf-8"), "manifest")
    assert_no_answer_tokens(global_compile_path.read_text(encoding="utf-8"), "compile database")
    return manifest


def assert_property_id_domains_disjoint(property_ir: dict[str, Any], case_id: str) -> None:
    identifiers = [property_ir["artifact_id"], property_ir["property_id"]]
    identifiers.extend(ap["ap_id"] for ap in property_ir["atomic_propositions"])
    identifiers.extend(selector["selector_id"] for selector in property_ir["selectors"])

    def visit_formula(node: dict[str, Any]) -> None:
        identifiers.append(node["node_id"])
        for operand in node["operands"]:
            visit_formula(operand)

    visit_formula(property_ir["formula"])
    duplicates = sorted(
        identifier
        for identifier, count in Counter(identifiers).items()
        if count > 1
    )
    if duplicates:
        raise AcceptanceError(
            f"{case_id}: typed Property IR stable-ID domains collide: {duplicates}"
        )


def _logical_path_root(path: str, declared_roots: set[str], label: str) -> str:
    match = LOGICAL_PATH_PATTERN.fullmatch(path)
    if match is None:
        raise AcceptanceError(f"{label} is not a logical identity path: {path}")
    root = match.group("root")
    if root != "toolchain" and root not in declared_roots:
        raise AcceptanceError(f"{label} uses undeclared logical root {root}")
    return root


def _assert_logical_location(
    location: dict[str, Any] | None,
    declared_roots: set[str],
    label: str,
) -> None:
    if location is None:
        return
    _logical_path_root(str(location["file"]), declared_roots, f"{label} file")
    for index, item in enumerate(location.get("macro_stack", [])):
        _logical_path_root(str(item), declared_roots, f"{label} macro_stack[{index}]")


def _micro_canonical_command(
    bundle: Path,
    compile_path: Path,
    input_case: dict[str, Any],
) -> tuple[str, str, str, str, str]:
    """Independently mirror identity-v2 for the deliberately simple micro DB."""
    commands = read_json(compile_path)
    if not isinstance(commands, list) or len(commands) != 1:
        raise AcceptanceError(f"{input_case['case_id']}: expected one compile command")
    command = commands[0]
    arguments = command.get("arguments")
    if not isinstance(arguments, list) or not arguments or not all(
        isinstance(item, str) and item for item in arguments
    ):
        raise AcceptanceError(f"{input_case['case_id']}: raw arguments are unavailable")
    working = (compile_path.parent / str(command["directory"])).resolve()
    source = (working / str(command["file"])).resolve()
    if working != bundle.resolve():
        raise AcceptanceError(f"{input_case['case_id']}: unexpected identity root")
    expected_source_path = (bundle / input_case["source"]["path"]).resolve()
    if source != expected_source_path:
        raise AcceptanceError(f"{input_case['case_id']}: compile command source mismatch")
    logical_working = "riftpath://v1/project/"
    logical_source = f"riftpath://v1/project/{input_case['source']['path']}"
    compiler_match = re.search(r"(?:^|[-_])([0-9]+)$", Path(arguments[0]).name)
    if compiler_match is None:
        raise AcceptanceError(f"{input_case['case_id']}: compiler major is not explicit")
    clang_major = int(compiler_match.group(1))
    if clang_major != 18:
        raise AcceptanceError(f"{input_case['case_id']}: frozen micro compiler is not Clang 18")
    canonical = (
        f"{IDENTITY_SCHEME}\0{logical_working}\0{logical_source}\0"
        f"clang-major={clang_major}\0"
    )
    for index, raw_argument in enumerate(arguments):
        argument = Path(raw_argument).name if index == 0 else raw_argument
        if index > 0 and (Path(argument).is_absolute() or argument.startswith("@")):
            raise AcceptanceError(
                f"{input_case['case_id']}: micro canonical command has an unsupported path"
            )
        canonical += f"{len(argument.encode('utf-8'))}:{argument}\0"
    command_sha256 = _sha256_text(canonical)
    path_map_sha256 = _sha256_text(
        f"{IDENTITY_SCHEME}\0{PATH_MAP_SCHEME}\0project"
    )
    canonical_database = _sha256_text(
        f"{IDENTITY_SCHEME}\0{path_map_sha256}\0"
        f"{len(canonical.encode('utf-8'))}:{canonical}"
    )
    tu_id = _stable_id(
        "tu", f"{IDENTITY_SCHEME}\0{logical_source}\0{command_sha256}"
    )
    return logical_working, logical_source, command_sha256, canonical_database, tu_id


def assert_lossless_index_identity(
    *,
    case_id: str,
    bundle: Path,
    compile_path: Path,
    input_case: dict[str, Any],
    index: dict[str, Any],
    graph: dict[str, Any],
) -> None:
    """Recompute portable identities and all analysis-critical v2 references."""
    if index["identity_scheme"] != IDENTITY_SCHEME:
        raise AcceptanceError(f"{case_id}: unsupported semantic identity scheme")
    if index["logical_root_ids"] != ["project"]:
        raise AcceptanceError(f"{case_id}: micro index must use the inferred project root")
    roots = {"project"}
    expected_path_map = _sha256_text(
        f"{IDENTITY_SCHEME}\0{PATH_MAP_SCHEME}\0project"
    )
    if index["path_map_sha256"] != expected_path_map:
        raise AcceptanceError(f"{case_id}: path-map digest is not independently reproducible")
    if index["source_identity_root"] != f"{IDENTITY_SCHEME}:{expected_path_map}":
        raise AcceptanceError(f"{case_id}: source identity root is stale")
    (
        logical_working,
        logical_source,
        command_sha256,
        canonical_database_sha256,
        expected_tu_id,
    ) = _micro_canonical_command(bundle, compile_path, input_case)
    if index["canonical_compilation_database_sha256"] != canonical_database_sha256:
        raise AcceptanceError(f"{case_id}: canonical compilation database digest mismatch")

    translation_units = unique_by(index["translation_units"], "tu_id", f"{case_id} TU")
    if set(translation_units) != {expected_tu_id}:
        raise AcceptanceError(f"{case_id}: translation-unit identity is not reproducible")
    unit = translation_units[expected_tu_id]
    if (
        unit["source_file"] != logical_source
        or unit["working_directory"] != logical_working
        or unit["command_sha256"] != command_sha256
    ):
        raise AcceptanceError(f"{case_id}: translation-unit logical command mismatch")

    ordered_inputs = sorted(
        index["input_files"],
        key=lambda item: (
            item["logical_path"], item["role"], item["sha256"], item["input_file_id"]
        ),
    )
    if index["input_files"] != ordered_inputs:
        raise AcceptanceError(f"{case_id}: input manifest is not deterministically ordered")
    inputs = unique_by(ordered_inputs, "input_file_id", f"{case_id} input file")
    path_digests: dict[str, str] = {}
    manifest_material = f"{IDENTITY_SCHEME}\0input-manifest/1.0.0"
    for item in ordered_inputs:
        logical_path = str(item["logical_path"])
        root = _logical_path_root(logical_path, roots, f"{case_id} input file")
        expected_id = _stable_id(
            "input-file",
            f"{IDENTITY_SCHEME}\0{item['role']}\0{logical_path}\0{item['sha256']}",
        )
        if item["input_file_id"] != expected_id:
            raise AcceptanceError(f"{case_id}: input-file ID is not content/path/role bound")
        previous = path_digests.setdefault(logical_path, item["sha256"])
        if previous != item["sha256"]:
            raise AcceptanceError(f"{case_id}: logical input path has conflicting content")
        if root == "toolchain":
            components = logical_path.split("/")
            if item["role"] == "toolchain":
                if len(components) < 6 or components[-2] != "predefines" or components[-1] != item["sha256"]:
                    raise AcceptanceError(f"{case_id}: toolchain predefines path is not content bound")
            elif item["role"] == "system":
                if len(components) < 7 or components[-3] != "system" or components[-2] != item["sha256"]:
                    raise AcceptanceError(f"{case_id}: system header path is not content bound")
            else:
                raise AcceptanceError(f"{case_id}: unexpected role under toolchain root")
        manifest_material += (
            f"\0{item['role']}\0{len(logical_path.encode('utf-8'))}:"
            f"{logical_path}\0{item['sha256']}\0{item['byte_size']}"
        )
    expected_manifest = _sha256_text(manifest_material)
    if index["input_manifest_sha256"] != expected_manifest:
        raise AcceptanceError(f"{case_id}: semantic input manifest digest mismatch")
    expected_index_id = _stable_id(
        "index",
        f"{IDENTITY_SCHEME}\0{canonical_database_sha256}\0"
        f"{expected_path_map}\0{expected_manifest}",
    )
    if index["artifact_id"] != expected_index_id:
        raise AcceptanceError(f"{case_id}: semantic index artifact ID is stale")

    input_refs = unit["input_file_ids"]
    if len(input_refs) != len(set(input_refs)) or set(input_refs) != set(inputs):
        raise AcceptanceError(f"{case_id}: TU input-file references are not total")
    main_inputs = [item for item in ordered_inputs if item["role"] == "main"]
    if len(main_inputs) != 1:
        raise AcceptanceError(f"{case_id}: per-case index must have exactly one main input")
    main = main_inputs[0]
    source_path = bundle / input_case["source"]["path"]
    if (
        main["logical_path"] != logical_source
        or main["sha256"] != sha256_file(source_path)
        or main["byte_size"] != source_path.stat().st_size
    ):
        raise AcceptanceError(f"{case_id}: main input digest does not bind public source bytes")

    entity_ids: set[str] = set()
    for record in index["entities"]:
        entity_id = record["entity"]["entity_id"]
        if entity_id in entity_ids:
            raise AcceptanceError(f"{case_id}: duplicate indexed entity {entity_id}")
        entity_ids.add(entity_id)
        refs = record["translation_unit_refs"]
        if len(refs) != len(set(refs)) or not set(refs) <= set(translation_units):
            raise AcceptanceError(f"{case_id}: entity has invalid TU references")
        for location in record["declarations"] + record["definitions"]:
            _assert_logical_location(location, roots, f"{case_id} entity")
    objects = unique_by(index["abstract_objects"], "object_id", f"{case_id} object")
    for item in objects.values():
        _assert_logical_location(item["allocation_site"], roots, f"{case_id} object")
    semantic_nodes = unique_by(index["semantic_nodes"], "node_id", f"{case_id} semantic node")
    for node in semantic_nodes.values():
        if node["entity_ref"] not in entity_ids:
            raise AcceptanceError(f"{case_id}: semantic node has missing entity_ref")
        if node["owner_function_id"] is not None and node["owner_function_id"] not in entity_ids:
            raise AcceptanceError(f"{case_id}: semantic node has missing owner function")
        if node["abstract_object_id"] is not None and node["abstract_object_id"] not in objects:
            raise AcceptanceError(f"{case_id}: semantic node has missing abstract object")
        if node["access_path"] is not None and node["access_path"]["root_entity_id"] not in entity_ids:
            raise AcceptanceError(f"{case_id}: semantic node access path has missing root")
        _assert_logical_location(node["location"], roots, f"{case_id} semantic node")
    relations = unique_by(index["semantic_relations"], "relation_id", f"{case_id} semantic relation")
    callsites = unique_by(index["callsites"], "callsite_id", f"{case_id} callsite")
    for relation in relations.values():
        if not {relation["source_node_id"], relation["target_node_id"]} <= set(semantic_nodes):
            raise AcceptanceError(f"{case_id}: semantic relation has missing endpoint")
        if relation["callsite_id"] is not None and relation["callsite_id"] not in callsites:
            raise AcceptanceError(f"{case_id}: semantic relation has missing callsite")
        if not set(relation["condition_node_ids"]) <= set(semantic_nodes):
            raise AcceptanceError(f"{case_id}: semantic relation has missing condition node")
        for item in relation["evidence"]:
            _assert_logical_location(item.get("location"), roots, f"{case_id} relation evidence")
    summary_functions: set[str] = set()
    for summary in index["function_summaries"]:
        function_id = summary["function_entity_id"]
        if function_id in summary_functions or function_id not in entity_ids:
            raise AcceptanceError(f"{case_id}: invalid function summary identity")
        summary_functions.add(function_id)
        node_refs = (
            summary["parameter_node_ids"]
            + summary["owned_node_ids"]
            + ([summary["receiver_node_id"]] if summary["receiver_node_id"] else [])
            + ([summary["return_node_id"]] if summary["return_node_id"] else [])
        )
        if not set(node_refs) <= set(semantic_nodes):
            raise AcceptanceError(f"{case_id}: function summary has missing semantic node")
        if not set(summary["relation_ids"]) <= set(relations):
            raise AcceptanceError(f"{case_id}: function summary has missing relation")
        if not set(summary["callsite_ids"]) <= set(callsites):
            raise AcceptanceError(f"{case_id}: function summary has missing callsite")
    for callsite in callsites.values():
        if callsite["caller_function_id"] not in entity_ids:
            raise AcceptanceError(f"{case_id}: callsite has missing caller")
        if not set(callsite["candidate_callee_ids"]) <= entity_ids:
            raise AcceptanceError(f"{case_id}: callsite has missing callee entity")
        node_refs = list(callsite["argument_node_ids"])
        node_refs.extend(node for group in callsite["argument_node_groups"] for node in group)
        node_refs.extend(
            node for node in (callsite["receiver_node_id"], callsite["result_node_id"]) if node
        )
        if not set(node_refs) <= set(semantic_nodes):
            raise AcceptanceError(f"{case_id}: callsite has missing semantic node")
        if len(callsite["argument_node_groups"]) != len(callsite["argument_is_address"]):
            raise AcceptanceError(f"{case_id}: callsite positional argument facts are misaligned")
        _assert_logical_location(callsite["location"], roots, f"{case_id} callsite")

    graph_nodes = unique_by(graph["nodes"], "node_id", f"{case_id} graph node")
    for node in graph_nodes.values():
        semantic_ref = node["semantic_node_ref"]
        if semantic_ref not in semantic_nodes:
            raise AcceptanceError(f"{case_id}: graph node has missing semantic provenance")
        if node["semantic_node_kind"] != semantic_nodes[semantic_ref]["node_kind"]:
            raise AcceptanceError(f"{case_id}: graph semantic-node kind is stale")
        _assert_logical_location(node["location"], roots, f"{case_id} graph node")
        _assert_logical_location(
            node["abstract_object"]["allocation_site"], roots, f"{case_id} graph object"
        )
        for item in node["evidence"]:
            _assert_logical_location(item.get("location"), roots, f"{case_id} graph evidence")
    graph_edges = unique_by(graph["edges"], "edge_id", f"{case_id} graph edge")
    for edge in graph_edges.values():
        if not {edge["source_node_id"], edge["target_node_id"]} <= set(graph_nodes):
            raise AcceptanceError(f"{case_id}: graph edge has missing endpoint")
        if not set(edge["condition_node_ids"]) <= set(graph_nodes):
            raise AcceptanceError(f"{case_id}: graph edge has missing condition node")
        for item in edge["evidence"]:
            _assert_logical_location(item.get("location"), roots, f"{case_id} edge evidence")


def assert_certificate_provenance(
    *,
    case_id: str,
    certificate: dict[str, Any],
    index: dict[str, Any],
    compile_path: Path,
    property_path: Path,
    source_path: Path,
    result_root: Path,
    artifacts: dict[str, dict[str, str]],
) -> None:
    build = certificate["build_manifest"]
    if build["identity_policy"] != "relative-path-and-content-v1":
        raise AcceptanceError(f"{case_id}: unsupported build identity policy")
    if build["production_core_sha256"] != certificate["core_tree_sha256"]:
        raise AcceptanceError(f"{case_id}: certificate core digest aliases disagree")
    active_schema_digest = production_schema_tree_sha256()
    if (
        build["schema_bundle_sha256"] != certificate["schema_bundle_sha256"]
        or certificate["schema_bundle_sha256"] != active_schema_digest
    ):
        raise AcceptanceError(f"{case_id}: certificate schema bundle is not the active tree")

    expected_environment_names = (
        "CL", "COMPILER_PATH", "CPATH", "CPLUS_INCLUDE_PATH",
        "C_INCLUDE_PATH", "GCC_EXEC_PREFIX", "INCLUDE", "LANG",
        "LC_ALL", "LC_CTYPE", "MACOSX_DEPLOYMENT_TARGET",
        "OBJC_INCLUDE_PATH", "PATH", "SDKROOT", "SOURCE_DATE_EPOCH", "_CL_",
    )
    variables = certificate["environment"]["variables"]
    if tuple(item["name"] for item in variables) != expected_environment_names:
        raise AcceptanceError(f"{case_id}: semantic environment whitelist/order changed")
    environment_material = bytearray()
    for item in variables:
        name = item["name"].encode("utf-8")
        value_digest = (item["value_sha256"] or "").encode("utf-8")
        environment_material.extend(len(name).to_bytes(8, "big"))
        environment_material.extend(name)
        environment_material.append(1 if item["present"] else 0)
        environment_material.extend(len(value_digest).to_bytes(8, "big"))
        environment_material.extend(value_digest)
    expected_environment_digest = hashlib.sha256(environment_material).hexdigest()
    if (
        certificate["environment"]["digest"] != expected_environment_digest
        or certificate["analyzer"]["environment_sha256"] != expected_environment_digest
    ):
        raise AcceptanceError(f"{case_id}: semantic environment digest is stale")

    inputs = unique_by(certificate["inputs"], "kind", f"{case_id} certificate input")
    expected_input_paths = {
        "compile_commands": compile_path.resolve(),
        "typed_property_ir": property_path.resolve(),
    }
    for kind, expected in expected_input_paths.items():
        if Path(inputs[kind]["path"]).resolve() != expected:
            raise AcceptanceError(f"{case_id}: certificate input path mismatch for {kind}")
    output_by_kind = unique_by(
        certificate["outputs"], "kind", f"{case_id} certificate output"
    )
    for kind, entry in artifacts.items():
        if kind == "analysis_certificate":
            continue
        expected = (result_root / entry["path"]).resolve()
        if Path(output_by_kind[kind]["path"]).resolve() != expected:
            raise AcceptanceError(f"{case_id}: certificate output path mismatch for {kind}")

    expected_analysis_id = _stable_id_bytes(
        "analysis",
        _length_prefixed(
            [
                sha256_file(property_path),
                index["input_manifest_sha256"],
                index["canonical_compilation_database_sha256"],
                index["path_map_sha256"],
            ]
        ),
    )
    if certificate["analysis_id"] != expected_analysis_id:
        raise AcceptanceError(f"{case_id}: certificate analysis identity is stale")
    output_digests = [
        artifacts["semantic_index"]["sha256"],
        artifacts["ap_bindings"]["sha256"],
        artifacts["contextual_influence_graph"]["sha256"],
        artifacts["ap_influence_cones"]["sha256"],
    ]
    expected_certificate_id = _stable_id_bytes(
        "certificate",
        _length_prefixed(
            [
                expected_analysis_id,
                certificate["analyzer"]["configuration_sha256"],
                *output_digests,
            ]
        ),
    )
    if certificate["certificate_id"] != expected_certificate_id:
        raise AcceptanceError(f"{case_id}: certificate identity is stale")
    expected_stages = [
        (
            "stage.index",
            "index",
            [sha256_file(compile_path), index["input_manifest_sha256"]],
            [output_digests[0]],
        ),
        (
            "stage.bind",
            "bind",
            [sha256_file(property_path), output_digests[0]],
            [output_digests[1]],
        ),
        (
            "stage.influence",
            "influence",
            [output_digests[0], output_digests[1]],
            [output_digests[2]],
        ),
        (
            "stage.cone",
            "cone",
            [output_digests[1], output_digests[2]],
            [output_digests[3]],
        ),
        (
            "stage.certificate",
            "certificate",
            output_digests,
            [],
        ),
    ]
    for stage, (stage_id, name, input_hashes, output_hashes) in zip(
        certificate["stages"], expected_stages
    ):
        if (
            stage["stage_id"] != stage_id
            or stage["name"] != name
            or stage["input_sha256"] != input_hashes
            or stage["output_sha256"] != output_hashes
        ):
            raise AcceptanceError(f"{case_id}: certificate stage chain is stale at {name}")

    provenance = certificate["source_input_provenance"]
    if provenance["manifest_sha256"] != index["input_manifest_sha256"]:
        raise AcceptanceError(f"{case_id}: source provenance manifest is stale")
    provenance_files = unique_by(
        provenance["files"], "input_file_id", f"{case_id} source provenance"
    )
    index_files = unique_by(index["input_files"], "input_file_id", f"{case_id} index input")
    if set(provenance_files) != set(index_files):
        raise AcceptanceError(f"{case_id}: source provenance does not cover every indexed input")
    for input_file_id, indexed in index_files.items():
        record = provenance_files[input_file_id]
        for field in ("logical_path", "role", "sha256", "byte_size"):
            if record[field] != indexed[field]:
                raise AcceptanceError(
                    f"{case_id}: source provenance differs from index for {input_file_id}"
                )
        if indexed["role"] != "toolchain" and not record["observed_paths"]:
            raise AcceptanceError(f"{case_id}: file-backed input has no observed path")
        for raw_path in record["observed_paths"]:
            observed = Path(raw_path)
            if not observed.is_absolute() or not observed.is_file():
                raise AcceptanceError(f"{case_id}: source provenance path is unavailable")
            if sha256_file(observed) != indexed["sha256"] or observed.stat().st_size != indexed["byte_size"]:
                raise AcceptanceError(f"{case_id}: source provenance bytes changed")
    main_records = [item for item in provenance["files"] if item["role"] == "main"]
    if len(main_records) != 1 or source_path.resolve() not in {
        Path(path).resolve() for path in main_records[0]["observed_paths"]
    }:
        raise AcceptanceError(f"{case_id}: main-source physical provenance mismatch")
    if not any(
        item["component_kind"] == "executable"
        and item["sha256"] == certificate["analyzer"]["binary_sha256"]
        for item in certificate["toolchain"]
    ):
        raise AcceptanceError(f"{case_id}: toolchain omits the analyzer executable")


def assert_candidate_accounting(
    *,
    case_id: str,
    property_ir: dict[str, Any],
    candidates_by_ap: dict[str, set[str]],
    candidate_status_by_id: dict[str, str],
    graph_nodes: dict[str, dict[str, Any]],
    graph_edges: dict[str, dict[str, Any]],
    cones: dict[str, Any],
) -> None:
    """Check that no binding candidate or conservative cone member disappears."""
    cone_by_ap = unique_by(cones["cones"], "ap_id", f"{case_id} AP cone")
    expected_aps = {ap["ap_id"] for ap in property_ir["atomic_propositions"]}
    if set(cone_by_ap) != expected_aps:
        raise AcceptanceError(f"{case_id}: cone set does not cover every AP exactly once")
    for ap in property_ir["atomic_propositions"]:
        cone = cone_by_ap[ap["ap_id"]]
        if set(cone["roles"]) != set(ap["roles"]):
            raise AcceptanceError(f"{case_id}:{ap['ap_id']}: cone role mismatch")
        accounts = unique_by(
            cone["candidate_accounting"],
            "binding_id",
            f"{case_id}:{ap['ap_id']} candidate account",
        )
        expected_candidates = candidates_by_ap[ap["ap_id"]]
        if set(accounts) != expected_candidates:
            raise AcceptanceError(
                f"{case_id}:{ap['ap_id']}: incomplete candidate accounting; "
                f"missing={sorted(expected_candidates - set(accounts))} "
                f"extra={sorted(set(accounts) - expected_candidates)}"
            )
        members = unique_by(
            cone["members"], "node_id", f"{case_id}:{ap['ap_id']} cone member"
        )
        for account in accounts.values():
            candidate_status = candidate_status_by_id[account["binding_id"]]
            if candidate_status == "REJECTED" and account["disposition"] != "REJECTED":
                raise AcceptanceError(
                    f"{case_id}: rejected binding candidate has {account['disposition']} disposition"
                )
            if candidate_status == "UNRESOLVED" and account["disposition"] != "UNRESOLVED":
                raise AcceptanceError(
                    f"{case_id}: unresolved binding candidate has {account['disposition']} disposition"
                )
            if not set(account["root_node_ids"]) <= set(graph_nodes):
                raise AcceptanceError(f"{case_id}: account references unknown graph root")
            if account["disposition"] == "INCLUDED" and not account["root_node_ids"]:
                raise AcceptanceError(f"{case_id}: INCLUDED candidate has no root node")
            if account["disposition"] == "INCLUDED" and not set(
                account["root_node_ids"]
            ) <= set(members):
                raise AcceptanceError(
                    f"{case_id}: INCLUDED candidate root is absent from cone members"
                )
            if account["disposition"] in {"REJECTED", "UNRESOLVED"} and account["root_node_ids"]:
                raise AcceptanceError(
                    f"{case_id}: {account['disposition']} candidate unexpectedly has root nodes"
                )
        if not set(members) <= set(graph_nodes):
            raise AcceptanceError(f"{case_id}:{ap['ap_id']}: cone has unknown member")
        if not set(cone["edge_ids"]) <= set(graph_edges):
            raise AcceptanceError(f"{case_id}:{ap['ap_id']}: cone has unknown edge")
        included_roots = {
            node_id
            for account in accounts.values()
            if account["disposition"] == "INCLUDED"
            for node_id in account["root_node_ids"]
        }
        for edge_id in cone["edge_ids"]:
            edge = graph_edges[edge_id]
            if not {edge["source_node_id"], edge["target_node_id"]} <= set(members):
                raise AcceptanceError(
                    f"{case_id}:{ap['ap_id']}: cone edge endpoint is absent from members"
                )
        witnessed_edges: set[str] = set()
        for member in members.values():
            if not set(member["witness_edge_ids"]) <= set(cone["edge_ids"]):
                raise AcceptanceError(
                    f"{case_id}:{ap['ap_id']}: witness edge is outside cone"
                )
            if member["node_id"] in included_roots:
                if member["witness_edge_ids"]:
                    raise AcceptanceError(
                        f"{case_id}:{ap['ap_id']}: cone root has a non-empty witness"
                    )
                continue
            if not member["witness_edge_ids"]:
                raise AcceptanceError(
                    f"{case_id}:{ap['ap_id']}: non-root cone member has no witness edge"
                )
            cursor = member["node_id"]
            local_edges: set[str] = set()
            for edge_id in member["witness_edge_ids"]:
                if edge_id in local_edges:
                    raise AcceptanceError(
                        f"{case_id}:{ap['ap_id']}: witness repeats an edge"
                    )
                local_edges.add(edge_id)
                witnessed_edges.add(edge_id)
                edge = graph_edges[edge_id]
                if edge["source_node_id"] != cursor:
                    raise AcceptanceError(
                        f"{case_id}:{ap['ap_id']}: witness is not a directed continuous path"
                    )
                cursor = edge["target_node_id"]
            if cursor not in included_roots:
                raise AcceptanceError(
                    f"{case_id}:{ap['ap_id']}: witness does not terminate at an included root"
                )
            if (
                member["membership"] == "UNKNOWN_INFLUENCE"
                and cone["status"] == "COMPLETE"
            ):
                raise AcceptanceError(
                    f"{case_id}:{ap['ap_id']}: COMPLETE cone contains UNKNOWN member"
                )
        if witnessed_edges != set(cone["edge_ids"]):
            raise AcceptanceError(
                f"{case_id}:{ap['ap_id']}: cone edge set is not the exact witness union"
            )


def validate_case_artifacts(
    bundle: Path,
    result_root: Path,
    input_case: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    case_id = input_case["case_id"]
    property_path = bundle / input_case["property_ir"]["path"]
    compile_path = bundle / input_case["compile_database"]["path"]
    property_ir = read_json(property_path)
    loaded: dict[str, Any] = {}
    expected_artifact_kinds = set(ARTIFACT_SCHEMAS) | {"analysis_certificate"}
    if set(artifacts) != expected_artifact_kinds:
        raise AcceptanceError(
            f"{case_id}: artifact set is incomplete; "
            f"missing={sorted(expected_artifact_kinds - set(artifacts))} "
            f"extra={sorted(set(artifacts) - expected_artifact_kinds)}"
        )
    for kind, schema_name in ARTIFACT_SCHEMAS.items():
        _, value = _read_verified_json(
            result_root, artifacts[kind], f"{case_id} {kind}"
        )
        validate_schema(value, PRODUCTION_SCHEMA_DIR / schema_name, f"{case_id} {kind}")
        loaded[kind] = value
    _, certificate = _read_verified_json(
        result_root, artifacts["analysis_certificate"], f"{case_id} analysis certificate"
    )
    validate_schema(
        certificate,
        PRODUCTION_SCHEMA_DIR / "analysis_certificate.schema.json",
        f"{case_id} analysis certificate",
    )
    loaded["analysis_certificate"] = certificate

    index = loaded["semantic_index"]
    bindings = loaded["ap_bindings"]
    graph = loaded["contextual_influence_graph"]
    cones = loaded["ap_influence_cones"]
    if bindings["property_ir_sha256"] != sha256_file(property_path):
        raise AcceptanceError(f"{case_id}: bindings are not bound to Property IR")
    if bindings["semantic_index_sha256"] != artifacts["semantic_index"]["sha256"]:
        raise AcceptanceError(f"{case_id}: bindings are not bound to semantic index")
    if graph["semantic_index_sha256"] != artifacts["semantic_index"]["sha256"]:
        raise AcceptanceError(f"{case_id}: graph is not bound to semantic index")
    if cones["ap_bindings_sha256"] != artifacts["ap_bindings"]["sha256"]:
        raise AcceptanceError(f"{case_id}: cones are not bound to bindings")
    if cones["graph_sha256"] != artifacts["contextual_influence_graph"]["sha256"]:
        raise AcceptanceError(f"{case_id}: cones are not bound to graph")
    certificate_inputs = unique_by(certificate["inputs"], "kind", f"{case_id} certificate input")
    expected_input_kinds = {"compile_commands", "typed_property_ir", "source_inputs"}
    if set(certificate_inputs) != expected_input_kinds:
        raise AcceptanceError(f"{case_id}: certificate input set is not the exact M4 contract")
    if certificate_inputs["compile_commands"]["sha256"] != sha256_file(compile_path):
        raise AcceptanceError(f"{case_id}: certificate does not bind raw compile DB")
    if certificate_inputs["typed_property_ir"]["sha256"] != sha256_file(property_path):
        raise AcceptanceError(f"{case_id}: certificate does not bind Property IR")
    if certificate_inputs["source_inputs"]["sha256"] != index["input_manifest_sha256"]:
        raise AcceptanceError(f"{case_id}: certificate does not bind source input manifest")
    expected_source_input_id = _stable_id("input_manifest", index["input_manifest_sha256"])
    if certificate_inputs["source_inputs"]["artifact_id"] != expected_source_input_id:
        raise AcceptanceError(f"{case_id}: source-input certificate identity is stale")
    certificate_outputs = unique_by(certificate["outputs"], "kind", f"{case_id} certificate output")
    expected_output_hashes = {
        "semantic_index": artifacts["semantic_index"]["sha256"],
        "ap_bindings": artifacts["ap_bindings"]["sha256"],
        "contextual_influence_graph": artifacts["contextual_influence_graph"]["sha256"],
        "ap_influence_cones": artifacts["ap_influence_cones"]["sha256"],
    }
    if set(certificate_outputs) != set(expected_output_hashes):
        raise AcceptanceError(f"{case_id}: certificate output set is not exact")
    for kind, digest in expected_output_hashes.items():
        if certificate_outputs[kind]["sha256"] != digest:
            raise AcceptanceError(f"{case_id}: certificate output digest mismatch for {kind}")

    assert_lossless_index_identity(
        case_id=case_id,
        bundle=bundle,
        compile_path=compile_path,
        input_case=input_case,
        index=index,
        graph=graph,
    )
    assert_certificate_provenance(
        case_id=case_id,
        certificate=certificate,
        index=index,
        compile_path=compile_path,
        property_path=property_path,
        source_path=bundle / input_case["source"]["path"],
        result_root=result_root,
        artifacts=artifacts,
    )
    semantic_nodes = unique_by(index["semantic_nodes"], "node_id", f"{case_id} semantic node")

    selector_ids = {item["selector_id"] for item in property_ir["selectors"]}
    expected_bindings = {
        (ap["ap_id"], role)
        for ap in property_ir["atomic_propositions"]
        for role in ap["roles"]
    }
    actual_binding_records: dict[tuple[str, str], dict[str, Any]] = {}
    candidate_ids: set[str] = set()
    candidate_status_by_id: dict[str, str] = {}
    candidates_by_ap: dict[str, set[str]] = {ap["ap_id"]: set() for ap in property_ir["atomic_propositions"]}
    for binding in bindings["bindings"]:
        key = (binding["ap_id"], binding["role"])
        if key in actual_binding_records:
            raise AcceptanceError(f"{case_id}: duplicate AP-role binding {key}")
        actual_binding_records[key] = binding
        if binding["ap_id"] not in candidates_by_ap:
            raise AcceptanceError(f"{case_id}: binding references unknown AP {binding['ap_id']}")
        confidences = [candidate["confidence"] for candidate in binding["candidates"]]
        if confidences != sorted(confidences, reverse=True):
            raise AcceptanceError(f"{case_id}: binding candidates are not Top-1 ranked")
        for candidate in binding["candidates"]:
            candidate_id = candidate["binding_id"]
            if candidate_id in candidate_ids:
                raise AcceptanceError(f"{case_id}: duplicate binding_id {candidate_id}")
            candidate_ids.add(candidate_id)
            candidate_status_by_id[candidate_id] = candidate["status"]
            candidates_by_ap[binding["ap_id"]].add(candidate_id)
            if not set(candidate["selector_refs"]) <= selector_ids:
                raise AcceptanceError(f"{case_id}: binding references unknown selector")
            if not set(candidate["semantic_node_refs"]) <= set(semantic_nodes):
                raise AcceptanceError(f"{case_id}: binding references unknown semantic node")
    if set(actual_binding_records) != expected_bindings:
        raise AcceptanceError(
            f"{case_id}: AP-role binding coverage mismatch; "
            f"missing={sorted(expected_bindings - set(actual_binding_records))} "
            f"extra={sorted(set(actual_binding_records) - expected_bindings)}"
        )

    graph_nodes = unique_by(graph["nodes"], "node_id", f"{case_id} graph node")
    graph_edges = unique_by(graph["edges"], "edge_id", f"{case_id} graph edge")
    for edge in graph_edges.values():
        if edge["source_node_id"] not in graph_nodes or edge["target_node_id"] not in graph_nodes:
            raise AcceptanceError(f"{case_id}: graph edge has missing endpoint")
    assert_candidate_accounting(
        case_id=case_id,
        property_ir=property_ir,
        candidates_by_ap=candidates_by_ap,
        candidate_status_by_id=candidate_status_by_id,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        cones=cones,
    )
    return loaded


def validate_run(
    bundle: Path,
    result_root: Path,
    adapter_path: Path = DEFAULT_ADAPTER,
    expected_cases: int | None = 120,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    bundle = bundle.resolve()
    result_root = result_root.resolve()
    input_manifest = validate_bundle(bundle, expected_cases=expected_cases)
    run_path = result_root / RUN_MANIFEST
    run = read_json(run_path)
    validate_schema(
        run,
        LOCAL_SCHEMA_DIR / "analysis_run_manifest.schema.json",
        "sealed analyzer run",
    )
    if run["input_manifest_sha256"] != sha256_file(bundle / "manifest.json"):
        raise AcceptanceError("run is not bound to frozen input manifest")
    if run["schema_migration_ledger_sha256"] != sha256_file(SCHEMA_MIGRATION_LEDGER):
        raise AcceptanceError("run is not bound to the audited schema migration ledger")
    if run["production_schema_tree_sha256"] != production_schema_tree_sha256():
        raise AcceptanceError("active production schema tree changed after run seal")
    if run["adapter_config_sha256"] != sha256_file(adapter_path):
        raise AcceptanceError("run adapter digest differs from evaluation adapter")
    analyzer_path = Path(run["analyzer"]["path"])
    if not analyzer_path.is_file() or sha256_file(analyzer_path) != run["analyzer"]["sha256"]:
        raise AcceptanceError("analyzer binary is absent or has changed since the run")
    sandbox_path = Path(run["sandbox"]["engine"]["path"])
    if (
        not sandbox_path.is_file()
        or sha256_file(sandbox_path) != run["sandbox"]["engine"]["sha256"]
    ):
        raise AcceptanceError("sandbox engine is absent or has changed since the run")
    denied_read_roots = [
        Path(path).resolve() for path in run["sandbox"]["denied_read_roots"]
    ]
    input_cases = unique_by(input_manifest["cases"], "case_id", "input case")
    run_cases = unique_by(run["cases"], "case_id", "run case")
    if run["case_count"] != len(run_cases) or set(run_cases) != set(input_cases):
        raise AcceptanceError("sealed run does not cover every input case exactly once")
    adapter = load_adapter(adapter_path)
    migration_approved_at = _parsed_timestamp(
        read_json(SCHEMA_MIGRATION_LEDGER)["approved_at"],
        "schema migration approval",
    )
    verified_artifacts: dict[str, dict[str, Any]] = {}
    for case_id in sorted(input_cases):
        input_case = input_cases[case_id]
        case_run = run_cases[case_id]
        if case_run["input_hashes"] != {
            "compile_database_sha256": input_case["compile_database"]["sha256"],
            "property_ir_sha256": input_case["property_ir"]["sha256"],
        }:
            raise AcceptanceError(f"{case_id}: run input hashes differ from bundle")
        expected_commands = render_commands(
            adapter,
            analyzer_path,
            bundle / input_case["compile_database"]["path"],
            bundle / input_case["property_ir"]["path"],
            result_root / "cases" / case_id,
        )
        expected_artifact_paths = {
            name: (Path("cases") / case_id / filename).as_posix()
            for name, filename in OUTPUT_NAMES.items()
        }
        for name, expected_path in expected_artifact_paths.items():
            if case_run["artifacts"][name]["path"] != expected_path:
                raise AcceptanceError(f"{case_id}: {name} artifact path changed")
        expected_certificate = (
            Path("cases") / case_id / "analysis_certificate.json"
        ).as_posix()
        if case_run["artifacts"]["analysis_certificate"]["path"] != expected_certificate:
            raise AcceptanceError(f"{case_id}: analysis certificate path changed")
        if [stage["name"] for stage in case_run["stages"]] != [
            command["name"] for command in expected_commands
        ]:
            raise AcceptanceError(f"{case_id}: run stage order changed")
        for recorded, expected in zip(case_run["stages"], expected_commands):
            if recorded["argv"] != expected["argv"]:
                raise AcceptanceError(f"{case_id}:{recorded['name']}: recorded command changed")
            expected_execution = sandbox_command(
                sandbox=sandbox_path,
                logical_argv=expected["argv"],
                bundle=bundle,
                writable_result_directory=result_root / "cases" / case_id,
                denied_read_roots=denied_read_roots,
            )
            if recorded["execution_argv"] != expected_execution:
                raise AcceptanceError(
                    f"{case_id}:{recorded['name']}: sandbox execution command changed"
                )
            expected_argument_files = argument_file_entries(expected["argv"], bundle)
            if recorded["argument_files"] != expected_argument_files:
                raise AcceptanceError(
                    f"{case_id}:{recorded['name']}: executed helper/input file changed"
                )
            _verify_digest(result_root, recorded["stdout"], f"{case_id} stdout")
            _verify_digest(result_root, recorded["stderr"], f"{case_id} stderr")
        loaded = validate_case_artifacts(
            bundle, result_root, input_case, case_run["artifacts"]
        )
        if (
            loaded["analysis_certificate"]["analyzer"]["binary_sha256"]
            != run["analyzer"]["sha256"]
        ):
            raise AcceptanceError(f"{case_id}: certificate analyzer digest mismatch")
        certificate_started = _parsed_timestamp(
            loaded["analysis_certificate"]["started_at"],
            f"{case_id} certificate start",
        )
        certificate_finished = _parsed_timestamp(
            loaded["analysis_certificate"]["finished_at"],
            f"{case_id} certificate finish",
        )
        if migration_approved_at > certificate_started:
            raise AcceptanceError(f"{case_id}: schema migration was not approved before analysis")
        if certificate_finished < certificate_started:
            raise AcceptanceError(f"{case_id}: certificate finish precedes start")
        verified_artifacts[case_id] = loaded
    return input_manifest, run, verified_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--expected-cases", type=int, default=120)
    arguments = parser.parse_args()
    try:
        if arguments.run is None:
            manifest = validate_bundle(arguments.bundle, arguments.expected_cases)
            print(
                "PASS",
                "phase=prepared",
                f"cases={manifest['case_count']}",
                f"aps={manifest['ap_count']}",
                f"bundle={arguments.bundle.resolve()}",
            )
        else:
            _, run, _ = validate_run(
                arguments.bundle,
                arguments.run,
                arguments.adapter,
                arguments.expected_cases,
            )
            print(
                "PASS",
                "phase=sealed-run",
                f"cases={run['case_count']}",
                f"run={arguments.run.resolve()}",
            )
    except (OSError, KeyError, TypeError, json.JSONDecodeError, AcceptanceError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
