#!/usr/bin/env python3
"""Evaluate a sealed M5 run against the private mechanical oracle.

The phase boundary is intentional: every public input and result digest is
validated before the private corpus manifest or any relation label is opened.
UNKNOWN is an abstention and is never credited as a negative prediction.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence


HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
M4_SUPPORT = WORKSPACE / "benchmark/rift/m4/micro"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(M4_SUPPORT))

from common import AcceptanceError, read_json, sha256_file  # noqa: E402
from run_m5_all import (  # noqa: E402
    ARTIFACT_NAMES,
    RunError,
    sha256_tree,
    validate_public_inputs,
    write_json_atomic,
)


DEFAULT_FROZEN = WORKSPACE / "benchmark/rift/m4/micro/frozen"
DEFAULT_GOLD = WORKSPACE / "benchmark/rift/gold"
POSITIVE_RELATIONS = {"MUST_INFLUENCE", "MAY_INFLUENCE"}
NON_UNKNOWN_RECIPE = {"SUPPORTED", "HEURISTIC"}

# These thresholds are the M5 preregistration, not CLI tuning knobs.  Formal
# evaluation cannot replace them with weaker values after seeing the oracle.
PREREGISTERED_GATE_THRESHOLDS = {
    "gold_fuzzable_source_recall": 0.95,
    "critical_must_influencer_recall": 1.0,
    "supported_mutation_direction_accuracy": 0.90,
}

# The mechanical oracle predates the structured direction enum and stores a
# human-readable direction.  This deliberately narrow adapter labels only the
# expression forms whose truth direction is fixed by the generated template.
# Event timing/order recipes and non-monotone multi-AP expressions remain out
# of the supported-expression denominator rather than being guessed.
SUPPORTED_DIRECTION_BY_RECIPE_KIND = {
    "affine_boundary": "MONOTONE_UP",
    "alias_selection": "BOUNDARY_SET",
    "async_payload_boundary": "MONOTONE_UP",
    "boolean_toggle": "TOGGLE",
    "boundary_crossing": "MONOTONE_UP",
    "configuration_enable": "TOGGLE",
    "dynamic_threshold": "MONOTONE_DOWN",
    "field_boundary": "BOUNDARY_SET",
    "guard_flip": "MONOTONE_UP",
    "internal_path_enable": "TOGGLE",
    "joint_enable": "TOGGLE",
    "message_field_boundary": "MONOTONE_UP",
    "message_kind_selection": "BOUNDARY_SET",
    "multi_ap_enable": "TOGGLE",
    "observation_boundary": "MONOTONE_UP",
    "sequence_enable": "TOGGLE",
    "setup_sequence": "BOUNDARY_SET",
    "state_value": "BOUNDARY_SET",
    "timer_fire": "TOGGLE",
}


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": safe_ratio(tp, tp + fp),
        "recall": safe_ratio(tp, tp + fn),
        "f1": safe_ratio(2 * tp, 2 * tp + fp + fn),
    }


def load_json_object(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RunError(f"top-level JSON is not an object: {path}")
    return value


def strict_result_path(
    result_root: pathlib.Path, relative_value: Any, expected: pathlib.PurePosixPath | None = None
) -> pathlib.Path:
    relative = pathlib.PurePosixPath(str(relative_value))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise RunError(f"unsafe result-relative path: {relative_value!r}")
    if expected is not None and relative != expected:
        raise RunError(f"unexpected result path: expected {expected}, observed {relative}")
    root = result_root.resolve(strict=True)
    path = (root / pathlib.Path(*relative.parts)).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise RunError(f"result path escapes root: {relative}") from error
    return path


def validate_file_descriptor(
    result_root: pathlib.Path,
    descriptor: Mapping[str, Any],
    *,
    expected: pathlib.PurePosixPath | None = None,
) -> pathlib.Path:
    path = strict_result_path(result_root, descriptor.get("path"), expected)
    if not path.is_file():
        raise RunError(f"descriptor is not a regular file: {path}")
    if "byte_size" not in descriptor or path.stat().st_size != descriptor["byte_size"]:
        raise RunError(f"descriptor byte size differs: {path}")
    if sha256_file(path) != descriptor.get("sha256"):
        raise RunError(f"descriptor digest differs: {path}")
    return path


def validate_directory_descriptor(
    result_root: pathlib.Path,
    descriptor: Mapping[str, Any],
    *,
    expected: pathlib.PurePosixPath,
) -> pathlib.Path:
    path = strict_result_path(result_root, descriptor.get("path"), expected)
    if not path.is_dir():
        raise RunError(f"descriptor is not a directory: {path}")
    digest, count = sha256_tree(path)
    if digest != descriptor.get("tree_sha256") or count != descriptor.get("file_count"):
        raise RunError(f"directory descriptor differs: {path}")
    return path


def certificate_input_closure(
    *,
    case_id: str,
    artifacts: Mapping[str, Any],
    public: Mapping[str, Any],
    analyzer: pathlib.Path,
    model_pack: pathlib.Path,
    executor: pathlib.Path,
    result_root: pathlib.Path,
) -> None:
    m5 = artifacts["m5_analysis_certificate"]
    m4 = artifacts["analysis_certificate"]
    expected_property = str(public["property_ir_sha256"])
    expected_compile = str(public["compile_database_sha256"])
    expected_source = str(public["source_sha256"])
    if m5.get("analyzer", {}).get("binary_sha256") != sha256_file(analyzer):
        raise RunError(f"{case_id}: M5 certificate analyzer differs from frozen analyzer")
    if pathlib.Path(str(m5.get("analyzer", {}).get("binary_path"))).resolve() != analyzer:
        raise RunError(f"{case_id}: M5 certificate analyzer path is not the frozen analyzer")
    typed = m5.get("m4_commitments", {}).get("typed_property_ir", {})
    if typed.get("sha256") != expected_property:
        raise RunError(f"{case_id}: M5 certificate property digest differs from public case")
    packs = m5.get("model_packs", [])
    if len(packs) != 1 or packs[0].get("sha256") != sha256_file(model_pack):
        raise RunError(f"{case_id}: M5 certificate model pack differs from frozen pack")
    executor_record = m5.get("executor_manifest")
    if not isinstance(executor_record, Mapping) or executor_record.get("sha256") != sha256_file(
        executor
    ):
        raise RunError(f"{case_id}: M5 certificate executor differs from frozen executor")

    m4_inputs = {item.get("kind"): item for item in m4.get("inputs", [])}
    if m4_inputs.get("typed_property_ir", {}).get("sha256") != expected_property:
        raise RunError(f"{case_id}: M4 certificate property differs from public case")
    if m4_inputs.get("compile_commands", {}).get("sha256") != expected_compile:
        raise RunError(f"{case_id}: M4 certificate compile database differs from public case")
    expected_case_root = result_root / "case_inputs" / case_id
    expected_compile_path = (
        expected_case_root / "frozen" / str(public["compile_database_relative"])
    ).resolve()
    expected_property_path = (
        expected_case_root / "enriched" / str(public["property_ir_relative"])
    ).resolve()
    expected_source_path = (
        expected_case_root / "frozen" / str(public["source_relative"])
    ).resolve()
    if pathlib.Path(str(m4_inputs["compile_commands"].get("path"))).resolve() != expected_compile_path:
        raise RunError(f"{case_id}: M4 certificate compile path differs from staged case")
    if pathlib.Path(str(m4_inputs["typed_property_ir"].get("path"))).resolve() != expected_property_path:
        raise RunError(f"{case_id}: M4 certificate property path differs from staged case")
    source_records = [
        item
        for item in m4.get("source_input_provenance", {}).get("files", [])
        if item.get("role") == "main"
    ]
    if len(source_records) != 1 or source_records[0].get("sha256") != expected_source:
        raise RunError(f"{case_id}: M4 certificate main source differs from public case")
    observed = {pathlib.Path(str(value)).resolve() for value in source_records[0].get("observed_paths", [])}
    if expected_source_path not in observed:
        raise RunError(f"{case_id}: M4 certificate main source path differs from staged case")


def rerun_detached_verifier(
    *,
    case_id: str,
    verifier: pathlib.Path,
    schema_dir: pathlib.Path,
    certificate: pathlib.Path,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"rift-m5-reverify-{case_id}-") as directory:
        report_path = pathlib.Path(directory) / "report.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(verifier),
                str(certificate),
                "--schema-dir",
                str(schema_dir),
                "--report",
                str(report_path),
            ],
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0 or not report_path.is_file():
            raise RunError(
                f"{case_id}: frozen detached verifier failed: exit={completed.returncode} "
                f"stderr={completed.stderr.strip()}"
            )
        report = load_json_object(report_path)
        if report.get("verdict") != "PASS" or report.get("failures") not in (0, []):
            raise RunError(f"{case_id}: frozen detached verifier did not return clean PASS")
        return report


def validate_sealed_run(
    result_root: pathlib.Path,
    frozen_root: pathlib.Path,
    enriched_root: pathlib.Path,
    expected_cases: int,
    expected_run_manifest_sha256: str | None = None,
    require_determinism_gate: bool = False,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = result_root / "run_manifest.json"
    observed_run_sha256 = sha256_file(manifest_path)
    if (
        expected_run_manifest_sha256 is not None
        and observed_run_sha256 != expected_run_manifest_sha256
    ):
        raise RunError(
            "run manifest differs from external commitment: "
            f"expected {expected_run_manifest_sha256}, observed {observed_run_sha256}"
        )
    run = load_json_object(manifest_path)
    if run.get("schema_version") != "rift.m5.micro-run.v2" or run.get("status") != "PASS":
        raise RunError("M5 run is not a sealed PASS manifest")
    determinism = run.get("determinism_gate", {})
    if require_determinism_gate and determinism.get("status") != "PASS":
        raise RunError("formal evaluation requires a PASS serial-vs-parallel determinism gate")
    if run.get("expected_case_count") != expected_cases or run.get(
        "completed_case_count"
    ) != expected_cases:
        raise RunError("M5 run case-count closure failed")
    boundary = run.get("knowledge_boundary", {})
    if boundary.get("analysis_opened_private_gold") is not False or boundary.get(
        "private_gold_hidden_from_analyzer"
    ) is not True:
        raise RunError("analysis-phase knowledge boundary is not closed")
    self_test = run.get("sandbox_self_test", {})
    if self_test.get("status") != "PASS" or self_test.get("contract") != (
        "EMPTY_ROOT_EXACT_CASE_BINDINGS_PRIVATE_TMP_V1"
    ):
        raise RunError("sandbox isolation self-test is absent or failed")
    frozen_inputs = run.get("frozen_inputs")
    expected_frozen_inputs = {
        "analyzer",
        "model_pack",
        "executor_capabilities",
        "frozen_manifest",
        "enrichment_manifest",
        "verifier",
        "sandbox",
        "schema_bundle",
    }
    if not isinstance(frozen_inputs, Mapping) or set(frozen_inputs) != expected_frozen_inputs:
        raise RunError("frozen input inventory is not exact")
    file_paths = {
        label: validate_file_descriptor(
            result_root,
            frozen_inputs[label],
            expected=pathlib.PurePosixPath("frozen_inputs") / {
                "analyzer": "tafuzz-sa",
                "model_pack": "model_pack.json",
                "executor_capabilities": "executor_capabilities.json",
                "frozen_manifest": "frozen_manifest.json",
                "enrichment_manifest": "enrichment_manifest.json",
                "verifier": "verify_m5_certificate.py",
                "sandbox": "bwrap",
            }[label],
        )
        for label in expected_frozen_inputs - {"schema_bundle"}
    }
    schema_dir = validate_directory_descriptor(
        result_root,
        frozen_inputs["schema_bundle"],
        expected=pathlib.PurePosixPath("frozen_inputs/schema"),
    )
    if sha256_file(frozen_root / "manifest.json") != sha256_file(
        file_paths["frozen_manifest"]
    ):
        raise RunError("authoritative frozen manifest differs from run snapshot")
    if sha256_file(enriched_root / "manifest.json") != sha256_file(
        file_paths["enrichment_manifest"]
    ):
        raise RunError("authoritative enrichment manifest differs from run snapshot")
    public_records = {
        str(item["case_id"]): item
        for item in validate_public_inputs(frozen_root, enriched_root, expected_cases)
    }
    cases = run.get("cases")
    if not isinstance(cases, list) or len(cases) != expected_cases:
        raise RunError("sealed case ledger is incomplete")
    loaded: dict[str, dict[str, Any]] = {}
    for record in cases:
        case_id = str(record.get("case_id"))
        if case_id in loaded or record.get("status") != "PASS":
            raise RunError(f"duplicate or failed sealed case: {case_id}")
        public = public_records.get(case_id)
        if public is None:
            raise RunError(f"sealed case is absent from public manifests: {case_id}")
        expected_input_sha256 = {
            "compile_database": public["compile_database_sha256"],
            "property_ir": public["property_ir_sha256"],
            "source": public["source_sha256"],
        }
        if record.get("input_sha256") != expected_input_sha256:
            raise RunError(f"{case_id}: sealed input ledger differs from public manifests")
        artifacts = record.get("artifacts", {})
        if set(artifacts) != set(ARTIFACT_NAMES):
            raise RunError(f"{case_id}: artifact inventory is not exact")
        case_artifacts: dict[str, Any] = {}
        for name in ARTIFACT_NAMES:
            descriptor = artifacts[name]
            path = validate_file_descriptor(
                result_root,
                descriptor,
                expected=pathlib.PurePosixPath("cases") / case_id / name,
            )
            if name.endswith(".json"):
                case_artifacts[name.removesuffix(".json")] = load_json_object(path)
        verification_path = strict_result_path(
            result_root,
            pathlib.PurePosixPath("cases") / case_id / "detached_verification.json",
            pathlib.PurePosixPath("cases") / case_id / "detached_verification.json",
        )
        verification = load_json_object(verification_path)
        expected_report_sha = record["detached_verification"]["report_sha256"]
        if sha256_file(verification_path) != expected_report_sha or verification.get(
            "verdict"
        ) != "PASS":
            raise RunError(f"{case_id}: detached verification is not sealed PASS")
        rerun_detached_verifier(
            case_id=case_id,
            verifier=file_paths["verifier"],
            schema_dir=schema_dir,
            certificate=strict_result_path(
                result_root,
                pathlib.PurePosixPath("cases") / case_id / "m5_analysis_certificate.json",
                pathlib.PurePosixPath("cases") / case_id / "m5_analysis_certificate.json",
            ),
        )
        certificate_input_closure(
            case_id=case_id,
            artifacts=case_artifacts,
            public=public,
            analyzer=file_paths["analyzer"],
            model_pack=file_paths["model_pack"],
            executor=file_paths["executor_capabilities"],
            result_root=result_root,
        )
        loaded[case_id] = case_artifacts
    frozen_manifest = read_json(frozen_root / "manifest.json")
    if not isinstance(frozen_manifest, dict):
        raise RunError("frozen manifest is not an object")
    expected_frozen_sha = frozen_inputs["frozen_manifest"]["sha256"]
    if sha256_file(frozen_root / "manifest.json") != expected_frozen_sha:
        raise RunError("frozen public manifest differs from sealed run")
    return frozen_manifest, loaded


def public_location(input_case: Mapping[str, Any], private: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "file": str(input_case["source"]["path"]),
        "line": int(private["line"]),
        "column": int(private["column"]),
    }


def same_public_file(actual_value: Any, expected_value: Any) -> bool:
    actual_file = str(actual_value or "").replace("\\", "/")
    expected_file = str(expected_value or "").replace("\\", "/")
    return actual_file == expected_file or actual_file.endswith("/" + expected_file)


def same_public_line(location: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    actual_file = str(location.get("file", "")).replace("\\", "/")
    expected_file = str(expected["file"]).replace("\\", "/")
    return (
        int(location.get("line", 0)) == int(expected["line"])
        and (actual_file == expected_file or actual_file.endswith("/" + expected_file))
    )


def source_action_matches(
    artifacts: Mapping[str, Any], expected: Mapping[str, Any]
) -> dict[str, Any]:
    """Join a public source anchor to model actions, preferring semantic identity.

    Exact source columns identify declaration/value nodes. A direct CIG edge from
    an attached boundary node to that anchor is stable across relocation. Only
    when no such public semantic evidence exists do we retain line matching as an
    explicit coarse fallback.
    """
    nodes = {
        node["node_id"]: node
        for node in artifacts["semantic_index"].get("semantic_nodes", [])
    }
    exact_semantic_ids = {
        node_id
        for node_id, node in nodes.items()
        if same_public_file(node.get("location", {}).get("file"), expected["file"])
        and int(node.get("location", {}).get("line", 0)) == int(expected["line"])
        and int(node.get("location", {}).get("column", 0)) == int(expected["column"])
    }
    graph = artifacts["contextual_influence_graph"]
    contextual_by_semantic: dict[str, set[str]] = collections.defaultdict(set)
    for node in graph.get("nodes", []):
        contextual_by_semantic[str(node.get("semantic_node_ref"))].add(
            str(node.get("node_id"))
        )
    anchor_contextual = {
        contextual
        for semantic in exact_semantic_ids
        for contextual in contextual_by_semantic.get(semantic, set())
    }
    adjacent: set[tuple[str, str]] = set()
    for edge in graph.get("edges", []):
        left = str(edge.get("source_node_id"))
        right = str(edge.get("target_node_id"))
        adjacent.add((left, right))
        adjacent.add((right, left))

    match_priority = {
        "EXACT_SEMANTIC_ANCHOR": 0,
        "SEMANTIC_EDGE_TO_ANCHOR": 1,
        "SOURCE_RANGE_CONTAINS_ANCHOR": 2,
        "COARSE_LINE_FALLBACK": 3,
    }
    by_action: dict[str, tuple[int, str]] = {}
    for attachment in artifacts["model_fact_overlay"].get("boundary_attachments", []):
        semantic_id = str(attachment.get("semantic_node_id"))
        node = nodes.get(semantic_id)
        if node is None:
            continue
        location = node.get("location", {})
        kind: str | None = None
        if semantic_id in exact_semantic_ids:
            kind = "EXACT_SEMANTIC_ANCHOR"
        else:
            attachment_contextual = contextual_by_semantic.get(semantic_id, set())
            if any(
                (boundary, anchor) in adjacent
                for boundary in attachment_contextual
                for anchor in anchor_contextual
            ):
                kind = "SEMANTIC_EDGE_TO_ANCHOR"
            elif (
                same_public_file(location.get("file"), expected["file"])
                and int(location.get("line", 0)) <= int(expected["line"])
                <= int(location.get("end_line", location.get("line", 0)))
                and (
                    int(location.get("line", 0)) != int(expected["line"])
                    or int(location.get("column", 0)) <= int(expected["column"])
                )
                and (
                    int(location.get("end_line", location.get("line", 0)))
                    != int(expected["line"])
                    or int(expected["column"])
                    <= int(location.get("end_column", location.get("column", 0)))
                )
            ):
                kind = "SOURCE_RANGE_CONTAINS_ANCHOR"
            elif same_public_line(location, expected):
                kind = "COARSE_LINE_FALLBACK"
        if kind is None:
            continue
        action_id = str(attachment["external_action_id"])
        value = (match_priority[kind], kind)
        if action_id not in by_action or value < by_action[action_id]:
            by_action[action_id] = value
    stable = {action: value for action, value in by_action.items() if value[0] < 3}
    selected = stable if stable else by_action
    return {
        "action_ids": set(selected),
        "join_kinds": sorted({value[1] for value in selected.values()}),
        "used_coarse_fallback": bool(selected)
        and all(value[0] == 3 for value in selected.values()),
        "exact_semantic_anchor_count": len(exact_semantic_ids),
    }


def source_candidates(
    artifacts: Mapping[str, Any],
    input_case: Mapping[str, Any],
    source: Mapping[str, Any],
    ap_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = public_location(input_case, source["location"])
    matched = source_action_matches(artifacts, expected)
    candidates = [
        candidate
        for candidate in artifacts["frontier_candidates"].get("candidates", [])
        if candidate.get("ap_id") == ap_id
        and candidate.get("action", {}).get("external_action_id")
        in matched["action_ids"]
    ]
    return candidates, {
        "join_kinds": matched["join_kinds"],
        "used_coarse_fallback": matched["used_coarse_fallback"],
        "exact_semantic_anchor_count": matched["exact_semantic_anchor_count"],
        "matched_action_count": len(matched["action_ids"]),
    }


def source_influence_prediction(
    artifacts: Mapping[str, Any],
    input_case: Mapping[str, Any],
    source: Mapping[str, Any],
    ap_id: str,
) -> dict[str, Any]:
    """Classify source membership in the complete influence cone.

    This is intentionally independent of frontier actions: an INTERNAL source
    can be a critical MUST influencer even though it has no fuzzable action.
    UNKNOWN remains an abstention whenever absence cannot be proved from a
    complete index/binding/graph/cone chain.
    """
    expected = public_location(input_case, source["location"])
    index = artifacts["semantic_index"]
    graph = artifacts["contextual_influence_graph"]
    cones = artifacts["ap_influence_cones"]
    graph_nodes = {str(node["node_id"]): node for node in graph.get("nodes", [])}
    exact_graph_nodes = {
        node_id
        for node_id, node in graph_nodes.items()
        if same_public_file(node.get("location", {}).get("file"), expected["file"])
        and int(node.get("location", {}).get("line", 0)) == int(expected["line"])
        and int(node.get("location", {}).get("column", 0)) == int(expected["column"])
    }
    semantic_location_present = any(
        same_public_file(node.get("location", {}).get("file"), expected["file"])
        and int(node.get("location", {}).get("line", 0)) == int(expected["line"])
        and int(node.get("location", {}).get("column", 0)) == int(expected["column"])
        for node in index.get("semantic_nodes", [])
    )
    cone = next(
        (item for item in cones.get("cones", []) if item.get("ap_id") == ap_id),
        None,
    )
    if cone is None:
        return {
            "prediction": "UNKNOWN",
            "memberships": [],
            "matching_graph_node_count": len(exact_graph_nodes),
            "semantic_location_present": semantic_location_present,
            "reason": "no influence cone exists for the AP",
        }
    membership_by_node = {
        str(member.get("node_id")): str(member.get("membership"))
        for member in cone.get("members", [])
    }
    memberships = {
        membership_by_node[node_id]
        for node_id in exact_graph_nodes
        if node_id in membership_by_node
    }
    if memberships & {"MUST_INFLUENCE", "MAY_INFLUENCE", "MODELLED_INFLUENCE"}:
        prediction = "INFLUENCE"
        reason = "the exact source anchor is a positive influence-cone member"
    elif "UNKNOWN_INFLUENCE" in memberships:
        prediction = "UNKNOWN"
        reason = "the exact source anchor has only UNKNOWN cone membership"
    else:
        bindings = [
            binding
            for binding in artifacts["ap_bindings"].get("bindings", [])
            if binding.get("ap_id") == ap_id
        ]
        accounts = {
            str(account.get("binding_id")): account
            for account in cone.get("candidate_accounting", [])
        }
        binding_complete = bool(bindings) and all(
            binding.get("resolution") == "CONFIRMED"
            and any(
                candidate.get("status") == "CONFIRMED"
                and accounts.get(str(candidate.get("binding_id")), {}).get(
                    "disposition"
                )
                == "INCLUDED"
                for candidate in binding.get("candidates", [])
            )
            for binding in bindings
        )
        soundness_risk = any(
            gap.get("effect") in {"soundness_risk", "stage_failure"}
            for artifact_name in (
                "semantic_index",
                "ap_bindings",
                "contextual_influence_graph",
                "ap_influence_cones",
            )
            for gap in artifacts[artifact_name].get("unsupported_constructs", [])
        )
        complete = (
            semantic_location_present
            and all(
                unit.get("status") == "indexed"
                for unit in index.get("translation_units", [])
            )
            and graph.get("status") == "COMPLETE"
            and cone.get("status") == "COMPLETE"
            and binding_complete
            and not soundness_risk
        )
        prediction = "NO_INFLUENCE" if complete else "UNKNOWN"
        reason = (
            "a complete index/binding/graph/cone chain excludes the exact source anchor"
            if complete
            else "absence is not provable from the incomplete analysis chain"
        )
    return {
        "prediction": prediction,
        "memberships": sorted(memberships),
        "matching_graph_node_count": len(exact_graph_nodes),
        "semantic_location_present": semantic_location_present,
        "reason": reason,
    }


def frontier_prediction(candidates: Sequence[Mapping[str, Any]]) -> str:
    dispositions = {str(candidate.get("disposition")) for candidate in candidates}
    if "ACTIONABLE" in dispositions:
        return "ACTIONABLE"
    if dispositions and dispositions <= {"REJECTED"}:
        complete = all(
            all(
                candidate.get("evidence", {})
                .get("completeness", {})
                .get(field)
                is True
                for field in (
                    "model_vm_complete",
                    "attachment_enumeration_complete",
                    "forward_enumeration_complete",
                    "cone_complete",
                    "compatibility_complete",
                )
            )
            for candidate in candidates
        )
        if complete:
            return "NOT_ACTIONABLE"
    return "UNKNOWN"


def action_mutations_for_id(
    recipe: Mapping[str, Any] | None, action_id: str | None
) -> list[Mapping[str, Any]]:
    if recipe is None or action_id is None:
        return []
    return [
        mutation
        for mutation in recipe.get("action_mutations", [])
        if isinstance(mutation, Mapping)
        and str(mutation.get("action_id")) == action_id
    ]


def flatten_suggested_values(
    mutations: Iterable[Mapping[str, Any]],
) -> set[str]:
    return {
        str(value["canonical"])
        for mutation in mutations
        for value in mutation.get("suggested_values", [])
        if isinstance(value, Mapping) and "canonical" in value
    }


def canonical_label(value: Any) -> str:
    text = str(value).strip().casefold()
    return "_".join(part for part in "".join(
        character if character.isalnum() else " " for character in text
    ).split() if part)


def effective_recipe(recipe: Mapping[str, Any] | None) -> tuple[bool, str]:
    if recipe is None:
        return False, "MISSING"
    if recipe.get("status") not in NON_UNKNOWN_RECIPE:
        return False, "ABSTAIN_RECIPE_STATUS_UNKNOWN"
    outcome = recipe.get("solver_query", {}).get("outcome")
    if outcome != "SAT":
        return False, f"ABSTAIN_SOLVER_{outcome or 'MISSING'}"
    return True, "PREDICTED"


def categorical_recipe_metric(
    *, expected: Any, predicted: Iterable[Any], effective: bool, free_text: bool
) -> dict[str, Any]:
    if expected is None:
        return {
            "label_status": "NOT_LABELLED",
            "prediction_status": "INAPPLICABLE",
            "gold": None,
            "predicted": [],
            "exact": None,
        }
    expected_value = canonical_label(expected)
    predicted_values = sorted(
        {
            canonical_label(value)
            for value in predicted
            if value is not None and canonical_label(value) not in {"", "unknown"}
        }
    )
    prediction_status = "PREDICTED" if effective and predicted_values else "ABSTAIN"
    return {
        "label_status": (
            "LABELLED_FREE_TEXT_CANONICAL_EXACT" if free_text else "LABELLED"
        ),
        "prediction_status": prediction_status,
        "gold": expected_value,
        "predicted": predicted_values if effective else [],
        "exact": (
            predicted_values == [expected_value]
            if prediction_status == "PREDICTED"
            else False
        ),
    }


def suggested_value_metric(
    expected: set[str], predicted: set[str], labelled: bool, effective: bool
) -> dict[str, Any]:
    if not labelled:
        return {
            "label_status": "NOT_LABELLED",
            "prediction_status": "INAPPLICABLE",
            "gold": [],
            "predicted": [],
            "intersection": [],
            "missing": [],
            "extra": [],
            "precision": None,
            "recall": None,
            "exact": None,
            "overgenerated": False,
        }
    material = predicted if effective else set()
    intersection = expected & material
    extra = material - expected
    missing = expected - material
    return {
        "label_status": "LABELLED",
        "prediction_status": "PREDICTED" if effective else "ABSTAIN",
        "gold": sorted(expected),
        "predicted": sorted(material),
        "intersection": sorted(intersection),
        "missing": sorted(missing),
        "extra": sorted(extra),
        "precision": safe_ratio(len(intersection), len(material)),
        "recall": safe_ratio(len(intersection), len(expected)),
        "exact": material == expected if effective else False,
        "overgenerated": bool(extra),
    }


def predicted_selector_record(
    artifacts: Mapping[str, Any], ap_id: str
) -> dict[str, Any]:
    accounts = [
        item
        for item in artifacts["predicate_occurrence_bindings"].get(
            "selector_accounts", []
        )
        if item.get("ap_id") == ap_id
    ]
    return {
        "label_status": "NOT_LABELLED",
        "prediction_status": "PREDICTED" if accounts else "ABSTAIN",
        "gold": None,
        "predicted_selector_ids": sorted(
            str(item["selector_id"]) for item in accounts
        ),
        "predicted_resolutions": sorted(
            {str(item.get("resolution")) for item in accounts}
        ),
        "exact": None,
    }


def external_coordinate_record(
    action_ids: Sequence[str], actions: Mapping[str, Mapping[str, Any]], effective: bool
) -> dict[str, Any]:
    coordinates = [
        {
            "external_action_id": action_id,
            "channel": actions[action_id].get("channel"),
            "operation": actions[action_id].get("operation"),
            "payload_slot": actions[action_id].get("payload_slot"),
            "scope_schema": actions[action_id].get("scope_schema"),
            "generation_schema": actions[action_id].get("generation_schema"),
        }
        for action_id in action_ids
        if action_id in actions
    ]
    return {
        "label_status": "NOT_LABELLED",
        "prediction_status": "PREDICTED" if effective and coordinates else "ABSTAIN",
        "gold": None,
        "predicted": coordinates if effective else [],
        "exact": None,
    }


def prerequisite_record(
    relation: Mapping[str, Any], recipe: Mapping[str, Any] | None, effective: bool
) -> dict[str, Any]:
    choices = [] if recipe is None else recipe.get("prerequisite_choices", [])
    alternative_statuses = [
        str(alternative.get("status"))
        for choice in choices
        for alternative in choice.get("alternatives", [])
    ]
    if not effective:
        state = "ABSTAIN_RECIPE"
    elif not choices:
        state = "NO_PREREQUISITE"
    elif "PARTIAL_ORDER_UNKNOWN" in alternative_statuses:
        state = "ABSTAIN_PARTIAL_ORDER_UNKNOWN"
    else:
        state = "COMPLETE"
    return {
        "presence_label_status": "LABELLED",
        "gold_presence": bool(relation.get("preconditions")),
        "prediction_state": state,
        "predicted_presence": state == "COMPLETE",
        "gold_free_text_count": len(relation.get("preconditions", [])),
        "dag_node_metric": {"status": "NOT_LABELLED"},
        "dag_edge_metric": {"status": "NOT_LABELLED"},
        "alternative_exact_metric": {"status": "NOT_LABELLED"},
    }


def _topological_prerequisite_operations(
    alternative: Mapping[str, Any], target_action_ids: set[str]
) -> list[str] | None:
    if alternative.get("status") != "COMPLETE":
        return None
    steps = {
        str(step.get("step_id")): step for step in alternative.get("steps", [])
    }
    if len(steps) != len(alternative.get("steps", [])):
        return None
    indegree = {step_id: 0 for step_id in steps}
    successors: dict[str, list[str]] = collections.defaultdict(list)
    for step_id, step in steps.items():
        for predecessor in step.get("predecessor_step_ids", []):
            predecessor_id = str(predecessor)
            if predecessor_id not in steps:
                return None
            indegree[step_id] += 1
            successors[predecessor_id].append(step_id)
    ready = sorted(step_id for step_id, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        step_id = ready.pop(0)
        ordered.append(step_id)
        for successor in sorted(successors.get(step_id, [])):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort()
    if len(ordered) != len(steps):
        return None
    return [
        canonical_label(steps[step_id].get("operation", ""))
        for step_id in ordered
        if str(steps[step_id].get("action_id")) not in target_action_ids
        and canonical_label(steps[step_id].get("operation", ""))
    ]


def prerequisite_sequence_record(
    relation: Mapping[str, Any],
    recipe: Mapping[str, Any] | None,
    effective: bool,
) -> dict[str, Any]:
    """Lexically compare the current free-text oracle to complete operation DAGs.

    The v1 oracle has no structured prerequisite action IDs.  The contract is
    therefore explicitly labelled FREE_TEXT_SEQUENCE; it is useful as a strict
    exact/F1 diagnostic but must not be misrepresented as semantic DAG gold.
    """
    gold_items = [canonical_label(value) for value in relation.get("preconditions", [])]
    if not effective or recipe is None:
        return {
            "label_status": "LABELLED_FREE_TEXT_SEQUENCE",
            "prediction_status": "ABSTAIN_RECIPE",
            "gold_items": gold_items,
            "predicted_items": [],
            "exact": False,
            "alternative_count": 0,
        }
    target_actions = {
        str(value)
        for value in recipe.get("action_hyperedge", {}).get("action_ids", [])
    }
    alternatives = [
        alternative
        for choice in recipe.get("prerequisite_choices", [])
        for alternative in choice.get("alternatives", [])
    ]
    complete_sequences: list[list[str]] = []
    for alternative in alternatives:
        sequence = _topological_prerequisite_operations(alternative, target_actions)
        if sequence is not None:
            complete_sequences.append(sequence)
    if alternatives and len(complete_sequences) != len(alternatives):
        prediction_status = "ABSTAIN_PARTIAL_ORDER_UNKNOWN"
        predicted_items: list[str] = []
    else:
        prediction_status = "PREDICTED"
        predicted_items = sorted(
            {
                item
                for sequence in complete_sequences
                for item in sequence
            }
        )
    exact = (
        prediction_status == "PREDICTED"
        and len(complete_sequences) <= 1
        and (complete_sequences[0] if complete_sequences else []) == gold_items
    )
    return {
        "label_status": "LABELLED_FREE_TEXT_SEQUENCE",
        "prediction_status": prediction_status,
        "gold_items": gold_items,
        "predicted_items": predicted_items,
        "exact": exact,
        "alternative_count": len(alternatives),
    }


def supported_direction_record(
    relation: Mapping[str, Any],
    recipe: Mapping[str, Any] | None,
    effective: bool,
    selected_action_id: str | None,
) -> dict[str, Any]:
    gold_recipe = relation.get("mutation_recipe")
    kind = None if gold_recipe is None else str(gold_recipe.get("kind"))
    expected = SUPPORTED_DIRECTION_BY_RECIPE_KIND.get(kind or "")
    # A shared affine value feeds both a monotone threshold and a non-monotone
    # parity/presence AP.  Only the former belongs to this direction contract.
    if kind == "multi_ap_shared_input" and relation.get("ap_id") == "ap_primary":
        expected = "MONOTONE_UP"
    if kind == "joint_boundary":
        expected = {
            "source_left": "MONOTONE_UP",
            "source_right": "MONOTONE_DOWN",
        }.get(str(relation.get("source_id")))
    if expected is None:
        return {
            "label_status": "OUT_OF_SUPPORTED_EXPRESSION_SUBSET",
            "prediction_status": "INAPPLICABLE",
            "gold": None,
            "predicted": [],
            "exact": None,
        }
    predicted = sorted(
        {
            str(mutation.get("direction"))
            for mutation in action_mutations_for_id(recipe, selected_action_id)
            if mutation.get("direction") not in (None, "UNKNOWN")
        }
    )
    if not effective or not predicted:
        status = "ABSTAIN_UNKNOWN_DIRECTION"
        material: list[str] = []
    else:
        status = "PREDICTED"
        material = predicted
    return {
        "label_status": "SUPPORTED_EXPRESSION",
        "prediction_status": status,
        "gold": expected,
        "predicted": material,
        "exact": status == "PREDICTED" and material == [expected],
    }


def timing_record(
    gold_recipe: Mapping[str, Any] | None,
    recipe: Mapping[str, Any] | None,
    effective: bool,
) -> dict[str, Any]:
    raw_status = "MISSING" if recipe is None else str(
        recipe.get("timing", {}).get("status", "UNKNOWN")
    )
    if not effective:
        state = "ABSTAIN_RECIPE"
    elif raw_status == "EXACT":
        state = "EXACT"
    elif raw_status == "WIDENED_UNKNOWN":
        state = "ABSTAIN_WIDENED_UNKNOWN"
    else:
        state = "ABSTAIN_UNKNOWN"
    labelled_presence = gold_recipe is not None
    return {
        "presence_label_status": "LABELLED" if labelled_presence else "INAPPLICABLE",
        "gold_presence": bool(
            gold_recipe is not None
            and gold_recipe.get("relative_time_window") is not None
        ),
        "prediction_state": state,
        "predicted_exact_presence": state == "EXACT",
        "raw_status": raw_status,
        "gold_relative_time_window": (
            None if gold_recipe is None else gold_recipe.get("relative_time_window")
        ),
        "structured_fields_metric": {"status": "NOT_LABELLED"},
        "bounds_metric": {"status": "NOT_LABELLED"},
        "endpoint_metric": {"status": "NOT_LABELLED"},
        "actions_metric": {"status": "NOT_LABELLED"},
    }


def joint_action_set_record(
    *,
    gold_joint_group: set[str],
    action_ids: Sequence[str],
    action_sources: Mapping[str, set[str]],
    claim: str,
    effective: bool,
) -> dict[str, Any]:
    predicted_joint_sources: set[str] = set()
    mapping_complete = bool(action_ids)
    for action_id in action_ids:
        mapped = action_sources.get(action_id, set())
        if len(mapped) != 1:
            mapping_complete = False
        else:
            predicted_joint_sources.update(mapped)
    if not gold_joint_group:
        state = "INAPPLICABLE"
    elif not effective:
        state = "ABSTAIN_RECIPE"
    elif claim == "JOINT_UNKNOWN":
        state = "ABSTAIN_JOINT_UNKNOWN"
    elif not mapping_complete:
        state = "ABSTAIN_UNRESOLVED_ACTION_COORDINATE"
    else:
        state = "PREDICTED"
    return {
        "label_status": "LABELLED" if gold_joint_group else "INAPPLICABLE",
        "prediction_state": state,
        "claim": claim,
        "gold_source_ids": sorted(gold_joint_group),
        "predicted_source_ids": (
            sorted(predicted_joint_sources) if state == "PREDICTED" else []
        ),
        "exact": (
            predicted_joint_sources == gold_joint_group
            if state == "PREDICTED"
            else (False if gold_joint_group else None)
        ),
        "missing_source_ids": (
            sorted(gold_joint_group - predicted_joint_sources)
            if state == "PREDICTED"
            else []
        ),
        "extra_source_ids": (
            sorted(predicted_joint_sources - gold_joint_group)
            if state == "PREDICTED"
            else []
        ),
    }


def relation_rows(
    private: Mapping[str, Any], artifacts: Mapping[str, Any]
) -> list[dict[str, Any]]:
    truth = private["truth"]
    input_case = private["input_case"]
    sources = {item["id"]: item for item in truth["sources"]}
    recipes_by_candidate = {
        item["frontier_candidate_id"]: item
        for item in artifacts["mutation_recipes"].get("recipes", [])
    }
    actions = {
        str(candidate.get("action", {}).get("external_action_id")): candidate.get(
            "action", {}
        )
        for candidate in artifacts["frontier_candidates"].get("candidates", [])
    }
    source_action_ids: dict[str, set[str]] = {}
    for source_id, source in sources.items():
        expected = public_location(input_case, source["location"])
        source_action_ids[source_id] = set(
            source_action_matches(artifacts, expected)["action_ids"]
        )
    action_sources: dict[str, set[str]] = collections.defaultdict(set)
    for source_id, action_ids in source_action_ids.items():
        for action_id in action_ids:
            action_sources[action_id].add(source_id)
    rows: list[dict[str, Any]] = []
    for relation in truth["relations"]:
        source = sources[relation["source_id"]]
        influence = source_influence_prediction(
            artifacts, input_case, source, relation["ap_id"]
        )
        candidates, join = source_candidates(
            artifacts, input_case, source, relation["ap_id"]
        )
        prediction = frontier_prediction(candidates)
        candidate_recipes = [
            (item, recipes_by_candidate[item["candidate_id"]])
            for item in candidates
            if item["candidate_id"] in recipes_by_candidate
        ]
        candidate_recipes.sort(
            key=lambda pair: (
                int(pair[0].get("rank_tier", 999)),
                str(pair[0].get("candidate_id", "")),
                str(pair[1].get("recipe_id", "")),
            )
        )
        selected_candidate, recipe = (
            candidate_recipes[0] if candidate_recipes else (None, None)
        )
        selected_action_value = (
            None
            if selected_candidate is None
            else selected_candidate.get("action", {}).get("external_action_id")
        )
        selected_action_id = (
            str(selected_action_value) if selected_action_value not in (None, "") else None
        )
        gold_actionable = (
            relation["relation"] in POSITIVE_RELATIONS
            and source["fuzzable_frontier"] is True
        )
        gold_recipe = relation.get("mutation_recipe")
        is_effective, recipe_prediction_state = effective_recipe(recipe)
        mutations = action_mutations_for_id(recipe, selected_action_id)
        predicted_values = (
            flatten_suggested_values(mutations) if is_effective else set()
        )
        expected_values = (
            set()
            if gold_recipe is None
            else {str(value) for value in gold_recipe.get("suggested_values", [])}
        )
        mutation_kind = categorical_recipe_metric(
            expected=None if gold_recipe is None else gold_recipe.get("kind"),
            predicted=(item.get("mutation_kind") for item in mutations),
            effective=is_effective,
            free_text=True,
        )
        mutation_direction = categorical_recipe_metric(
            expected=None if gold_recipe is None else gold_recipe.get("direction"),
            predicted=(item.get("direction") for item in mutations),
            effective=is_effective,
            free_text=True,
        )
        value_metric = suggested_value_metric(
            expected_values, predicted_values, gold_recipe is not None, is_effective
        )
        hyperedge_action_ids = (
            []
            if recipe is None
            else [
                str(value)
                for value in recipe.get("action_hyperedge", {}).get("action_ids", [])
            ]
        )
        gold_joint_group = set(str(value) for value in relation.get("joint_group", []))
        joint_claim = (
            "MISSING"
            if recipe is None
            else str(recipe.get("action_hyperedge", {}).get("claim", "MISSING"))
        )
        joint_metric = joint_action_set_record(
            gold_joint_group=gold_joint_group,
            action_ids=hyperedge_action_ids,
            action_sources=action_sources,
            claim=joint_claim,
            effective=is_effective,
        )
        joint_state = joint_metric["prediction_state"]
        prerequisite = prerequisite_record(relation, recipe, is_effective)
        prerequisite_sequence = prerequisite_sequence_record(
            relation, recipe, is_effective
        )
        supported_direction = supported_direction_record(
            relation, recipe, is_effective, selected_action_id
        )
        timing = timing_record(gold_recipe, recipe, is_effective)
        rows.append(
            {
                "case_id": private["case_id"],
                "category": private["category"],
                "source_id": relation["source_id"],
                "ap_id": relation["ap_id"],
                "gold_relation": relation["relation"],
                "influence_prediction": influence["prediction"],
                "influence_evidence": influence,
                "gold_actionable": gold_actionable,
                "prediction": prediction,
                "source_join": join,
                "candidate_ids": [item["candidate_id"] for item in candidates],
                "recipe_id": None if recipe is None else recipe["recipe_id"],
                "recipe_status": "MISSING" if recipe is None else recipe["status"],
                "recipe_prediction_state": recipe_prediction_state,
                "recipe_effective": is_effective,
                "solver_outcome": (
                    "MISSING" if recipe is None else recipe["solver_query"]["outcome"]
                ),
                "predicted_values": sorted(predicted_values),
                "gold_values": sorted(expected_values),
                "gold_values_covered": bool(expected_values)
                and is_effective
                and expected_values <= predicted_values,
                "gold_has_preconditions": bool(relation.get("preconditions")),
                "predicted_has_prerequisites": prerequisite["predicted_presence"],
                "gold_has_timing_window": bool(
                    gold_recipe is not None
                    and gold_recipe.get("relative_time_window") is not None
                ),
                "predicted_has_timing_contract": timing["predicted_exact_presence"],
                "gold_joint": bool(relation.get("joint_group")),
                "predicted_joint": joint_state == "PREDICTED",
                "mutation_kind": mutation_kind,
                "mutation_direction": mutation_direction,
                "supported_direction": supported_direction,
                "suggested_value_metric": value_metric,
                "target_predicate_selector": predicted_selector_record(
                    artifacts, relation["ap_id"]
                ),
                "external_action_coordinate": external_coordinate_record(
                    [] if selected_action_id is None else [selected_action_id],
                    actions,
                    is_effective,
                ),
                "prerequisite": prerequisite,
                "prerequisite_sequence": prerequisite_sequence,
                "timing_metric": timing,
                "joint_action_set": joint_metric,
            }
        )
    return rows


def binary_feature_metrics(
    rows: Iterable[Mapping[str, Any]], gold_key: str, prediction_key: str
) -> dict[str, Any]:
    material = list(rows)
    tp = sum(bool(row[gold_key]) and bool(row[prediction_key]) for row in material)
    fp = sum(not bool(row[gold_key]) and bool(row[prediction_key]) for row in material)
    fn = sum(bool(row[gold_key]) and not bool(row[prediction_key]) for row in material)
    return prf(tp, fp, fn)


def categorical_metric_summary(
    rows: Iterable[Mapping[str, Any]], field: str
) -> dict[str, Any]:
    metrics = [row[field] for row in rows]
    labelled = [
        metric
        for metric in metrics
        if str(metric.get("label_status", "")).startswith("LABELLED")
    ]
    predicted = [
        metric for metric in labelled if metric.get("prediction_status") == "PREDICTED"
    ]
    correct = sum(metric.get("exact") is True for metric in predicted)
    return {
        "labelled_count": len(labelled),
        "prediction_count": len(predicted),
        "abstention_count": len(labelled) - len(predicted),
        "coverage": safe_ratio(len(predicted), len(labelled)),
        "conditional_accuracy": safe_ratio(correct, len(predicted)),
        "end_to_end_accuracy_abstention_is_wrong": safe_ratio(correct, len(labelled)),
        "correct_count": correct,
        "label_contracts": dict(
            sorted(collections.Counter(metric["label_status"] for metric in labelled).items())
        ),
    }


def fuzzable_source_recall_summary(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    gold = [row for row in rows if row.get("gold_actionable") is True]
    tp = sum(row.get("prediction") == "ACTIONABLE" for row in gold)
    fn = sum(row.get("prediction") == "NOT_ACTIONABLE" for row in gold)
    unknown = sum(row.get("prediction") == "UNKNOWN" for row in gold)
    unexpected = len(gold) - tp - fn - unknown
    return {
        "gold_count": len(gold),
        "tp": tp,
        "fn": fn,
        "unknown": unknown,
        "unexpected_prediction_count": unexpected,
        "recall_unknown_is_miss": safe_ratio(tp, len(gold)),
        "conditional_recall_on_decided": safe_ratio(tp, tp + fn),
    }


def must_influencer_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    gold = [row for row in rows if row.get("gold_relation") == "MUST_INFLUENCE"]
    tp = sum(row.get("influence_prediction") == "INFLUENCE" for row in gold)
    fn = sum(row.get("influence_prediction") == "NO_INFLUENCE" for row in gold)
    unknown = sum(row.get("influence_prediction") == "UNKNOWN" for row in gold)
    unexpected = len(gold) - tp - fn - unknown
    return {
        "gold_count": len(gold),
        "tp": tp,
        "fn": fn,
        "unknown": unknown,
        "unexpected_prediction_count": unexpected,
        "recall_unknown_is_miss": safe_ratio(tp, len(gold)),
        "conditional_recall_on_decided": safe_ratio(tp, tp + fn),
        "unknown_is_neither_tp_nor_fn": True,
    }


def supported_direction_summary(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    metrics = [
        row["supported_direction"]
        for row in rows
        if row["supported_direction"].get("label_status")
        == "SUPPORTED_EXPRESSION"
    ]
    predicted = [
        metric
        for metric in metrics
        if metric.get("prediction_status") == "PREDICTED"
    ]
    correct = sum(metric.get("exact") is True for metric in predicted)
    unknown = len(metrics) - len(predicted)
    return {
        "supported_count": len(metrics),
        "prediction_count": len(predicted),
        "correct_count": correct,
        "incorrect_count": len(predicted) - correct,
        "unknown_count": unknown,
        "coverage": safe_ratio(len(predicted), len(metrics)),
        "conditional_accuracy": safe_ratio(correct, len(predicted)),
        "end_to_end_accuracy_unknown_is_wrong": safe_ratio(correct, len(metrics)),
        "numerator": correct,
        "denominator": len(metrics),
        "unknown_states": dict(
            sorted(
                collections.Counter(
                    str(metric.get("prediction_status"))
                    for metric in metrics
                    if metric.get("prediction_status") != "PREDICTED"
                ).items()
            )
        ),
    }


def prerequisite_sequence_summary(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    metrics = [
        row["prerequisite_sequence"]
        for row in rows
        if row["prerequisite_sequence"].get("label_status")
        == "LABELLED_FREE_TEXT_SEQUENCE"
    ]
    predicted = [
        metric
        for metric in metrics
        if metric.get("prediction_status") == "PREDICTED"
    ]
    item_tp = item_fp = item_fn = 0
    for metric in metrics:
        gold = set(str(value) for value in metric.get("gold_items", []))
        material = (
            set(str(value) for value in metric.get("predicted_items", []))
            if metric.get("prediction_status") == "PREDICTED"
            else set()
        )
        item_tp += len(gold & material)
        item_fp += len(material - gold)
        item_fn += len(gold - material)
    exact = sum(metric.get("exact") is True for metric in predicted)
    return {
        "label_contract": "STRICT_CANONICAL_FREE_TEXT_VS_OPERATION_SEQUENCE",
        "structured_action_or_dag_gold_available": False,
        "labelled_count": len(metrics),
        "prediction_count": len(predicted),
        "abstention_count": len(metrics) - len(predicted),
        "coverage": safe_ratio(len(predicted), len(metrics)),
        "exact_count": exact,
        "conditional_exact_accuracy": safe_ratio(exact, len(predicted)),
        "end_to_end_exact_accuracy_abstention_is_wrong": safe_ratio(
            exact, len(metrics)
        ),
        "micro_item_tp": item_tp,
        "micro_item_fp": item_fp,
        "micro_item_fn": item_fn,
        "micro_item_precision": safe_ratio(item_tp, item_tp + item_fp),
        "micro_item_recall": safe_ratio(item_tp, item_tp + item_fn),
        "micro_item_f1": safe_ratio(2 * item_tp, 2 * item_tp + item_fp + item_fn),
        "abstention_states": dict(
            sorted(
                collections.Counter(
                    str(metric.get("prediction_status"))
                    for metric in metrics
                    if metric.get("prediction_status") != "PREDICTED"
                ).items()
            )
        ),
    }


def suggested_value_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    metrics = [
        row["suggested_value_metric"]
        for row in rows
        if row["suggested_value_metric"]["label_status"] == "LABELLED"
    ]
    predicted = [
        metric for metric in metrics if metric["prediction_status"] == "PREDICTED"
    ]
    intersection = sum(len(metric["intersection"]) for metric in metrics)
    predicted_items = sum(len(metric["predicted"]) for metric in metrics)
    gold_items = sum(len(metric["gold"]) for metric in metrics)
    exact = sum(metric["exact"] is True for metric in predicted)
    return {
        "labelled_count": len(metrics),
        "prediction_count": len(predicted),
        "abstention_count": len(metrics) - len(predicted),
        "coverage": safe_ratio(len(predicted), len(metrics)),
        "micro_item_precision": safe_ratio(intersection, predicted_items),
        "micro_item_recall_abstention_is_miss": safe_ratio(intersection, gold_items),
        "conditional_exact_accuracy": safe_ratio(exact, len(predicted)),
        "end_to_end_exact_accuracy_abstention_is_wrong": safe_ratio(exact, len(metrics)),
        "exact_count": exact,
        "overgenerated_prediction_count": sum(
            metric["overgenerated"] for metric in predicted
        ),
        "extra_item_count": sum(len(metric["extra"]) for metric in predicted),
        "missing_item_count": sum(len(metric["missing"]) for metric in metrics),
    }


def selective_presence_summary(
    rows: Iterable[Mapping[str, Any]], field: str, true_state: str, false_state: str
) -> dict[str, Any]:
    records = [
        row[field]
        for row in rows
        if row[field].get("presence_label_status") == "LABELLED"
    ]
    predicted = [
        record
        for record in records
        if record.get("prediction_state") in {true_state, false_state}
    ]
    tp = sum(
        record["gold_presence"] is True
        and record["prediction_state"] == true_state
        for record in predicted
    )
    fp = sum(
        record["gold_presence"] is False
        and record["prediction_state"] == true_state
        for record in predicted
    )
    tn = sum(
        record["gold_presence"] is False
        and record["prediction_state"] == false_state
        for record in predicted
    )
    fn = sum(
        record["gold_presence"] is True
        and record["prediction_state"] == false_state
        for record in predicted
    )
    gold_positive = sum(record["gold_presence"] is True for record in records)
    gold_negative = len(records) - gold_positive
    correct = tp + tn
    return {
        "labelled_count": len(records),
        "prediction_count": len(predicted),
        "abstention_count": len(records) - len(predicted),
        "coverage": safe_ratio(len(predicted), len(records)),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn_on_concrete_predictions": fn,
        "positive_recall_abstention_is_miss": safe_ratio(tp, gold_positive),
        "negative_specificity_abstention_is_miss": safe_ratio(tn, gold_negative),
        "conditional_accuracy": safe_ratio(correct, len(predicted)),
        "end_to_end_accuracy_abstention_is_wrong": safe_ratio(correct, len(records)),
        "abstention_states": dict(
            sorted(
                collections.Counter(
                    record["prediction_state"]
                    for record in records
                    if record not in predicted
                ).items()
            )
        ),
    }


def joint_metric_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    metrics = [
        row["joint_action_set"]
        for row in rows
        if row["joint_action_set"]["label_status"] == "LABELLED"
    ]
    predicted = [metric for metric in metrics if metric["prediction_state"] == "PREDICTED"]
    exact = sum(metric["exact"] is True for metric in predicted)
    item_tp = item_fp = item_fn = 0
    for metric in metrics:
        gold = set(str(value) for value in metric.get("gold_source_ids", []))
        material = (
            set(str(value) for value in metric.get("predicted_source_ids", []))
            if metric.get("prediction_state") == "PREDICTED"
            else set()
        )
        item_tp += len(gold & material)
        item_fp += len(material - gold)
        item_fn += len(gold - material)
    return {
        "labelled_count": len(metrics),
        "prediction_count": len(predicted),
        "abstention_count": len(metrics) - len(predicted),
        "coverage": safe_ratio(len(predicted), len(metrics)),
        "conditional_exact_accuracy": safe_ratio(exact, len(predicted)),
        "end_to_end_exact_accuracy_abstention_is_wrong": safe_ratio(exact, len(metrics)),
        "exact_count": exact,
        "micro_item_tp": item_tp,
        "micro_item_fp": item_fp,
        "micro_item_fn": item_fn,
        "micro_item_precision": safe_ratio(item_tp, item_tp + item_fp),
        "micro_item_recall": safe_ratio(item_tp, item_tp + item_fn),
        "micro_item_f1": safe_ratio(
            2 * item_tp, 2 * item_tp + item_fp + item_fn
        ),
        "incomplete_prediction_count": sum(
            bool(metric["missing_source_ids"]) for metric in predicted
        ),
        "extra_prediction_count": sum(
            bool(metric["extra_source_ids"]) for metric in predicted
        ),
        "abstention_states": dict(
            sorted(
                collections.Counter(
                    metric["prediction_state"]
                    for metric in metrics
                    if metric["prediction_state"] != "PREDICTED"
                ).items()
            )
        ),
    }


def ranking_rows(
    private: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    relation_material: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_candidate: dict[str, set[str]] = collections.defaultdict(set)
    for row in relation_material:
        for candidate_id in row["candidate_ids"]:
            by_candidate[str(candidate_id)].add(str(row["source_id"]))
    candidates = sorted(
        (
            candidate
            for candidate in artifacts["frontier_candidates"].get("candidates", [])
            if candidate.get("disposition") == "ACTIONABLE"
        ),
        key=lambda item: (int(item.get("rank_tier", 999)), str(item.get("candidate_id"))),
    )
    ap_ids = sorted({str(row["ap_id"]) for row in relation_material})
    output: list[dict[str, Any]] = []
    for ap_id in ap_ids:
        relevant = {
            str(row["source_id"])
            for row in relation_material
            if row["ap_id"] == ap_id and row["gold_actionable"]
        }
        if not relevant:
            output.append(
                {
                    "case_id": private["case_id"],
                    "ap_id": ap_id,
                    "label_status": "INAPPLICABLE_NO_GOLD_ACTIONABLE_SOURCE",
                }
            )
            continue
        ranked_sources: list[str] = []
        ambiguous_candidates = 0
        for candidate in candidates:
            if candidate.get("ap_id") != ap_id:
                continue
            mapped = by_candidate.get(str(candidate.get("candidate_id")), set())
            if len(mapped) != 1:
                ambiguous_candidates += 1
                continue
            source_id = next(iter(mapped))
            if source_id not in ranked_sources:
                ranked_sources.append(source_id)
        first_relevant_rank = next(
            (
                index
                for index, source_id in enumerate(ranked_sources, start=1)
                if source_id in relevant
            ),
            None,
        )
        top_five = ranked_sources[:5]
        output.append(
            {
                "case_id": private["case_id"],
                "ap_id": ap_id,
                "label_status": "LABELLED_BY_ACTIONABLE_SOURCE_RELATIONS",
                "gold_relevant_source_ids": sorted(relevant),
                "ranked_source_ids": ranked_sources,
                "ambiguous_candidate_count": ambiguous_candidates,
                "top1_hit": bool(ranked_sources and ranked_sources[0] in relevant),
                "top5_hit": any(source_id in relevant for source_id in top_five),
                "precision_at_1": (
                    1.0 if ranked_sources and ranked_sources[0] in relevant else 0.0
                ),
                "precision_at_5_fixed_denominator": sum(
                    source_id in relevant for source_id in top_five
                )
                / 5.0,
                "reciprocal_rank": (
                    None if first_relevant_rank is None else 1.0 / first_relevant_rank
                ),
            }
        )
    return output


def ranking_summary(rankings: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    labelled = [
        row
        for row in rankings
        if row.get("label_status") == "LABELLED_BY_ACTIONABLE_SOURCE_RELATIONS"
    ]
    return {
        "labelled_query_count": len(labelled),
        "top1_hit_rate": safe_ratio(sum(row["top1_hit"] for row in labelled), len(labelled)),
        "top5_hit_rate": safe_ratio(sum(row["top5_hit"] for row in labelled), len(labelled)),
        "mean_precision_at_1": safe_ratio(
            sum(row["precision_at_1"] for row in labelled), len(labelled)
        ),
        "mean_precision_at_5_fixed_denominator": safe_ratio(
            sum(row["precision_at_5_fixed_denominator"] for row in labelled),
            len(labelled),
        ),
        "mrr_missing_relevant_is_zero": safe_ratio(
            sum((row["reciprocal_rank"] or 0.0) for row in labelled), len(labelled)
        ),
        "unranked_relevant_query_count": sum(
            row["reciprocal_rank"] is None for row in labelled
        ),
    }


def resolve_evaluation_mode(*, formal: bool, development: bool) -> tuple[str, bool]:
    if formal and development:
        raise RunError("--formal and --development are mutually exclusive")
    if formal:
        return "FORMAL", True
    if development:
        return "DEVELOPMENT", False
    return "STANDARD", True


def evaluate_preregistered_gates(
    summary: Mapping[str, Any], *, enforce: bool
) -> dict[str, Any]:
    specifications = (
        (
            "gold_fuzzable_source_recall",
            PREREGISTERED_GATE_THRESHOLDS["gold_fuzzable_source_recall"],
            summary.get("gold_fuzzable_source_recall", {}).get(
                "recall_unknown_is_miss"
            ),
            summary.get("gold_fuzzable_source_recall", {}),
        ),
        (
            "critical_must_influencer_recall",
            PREREGISTERED_GATE_THRESHOLDS[
                "critical_must_influencer_recall"
            ],
            summary.get("critical_must_influencer_recall", {}).get(
                "recall_unknown_is_miss"
            ),
            summary.get("critical_must_influencer_recall", {}),
        ),
        (
            "supported_mutation_direction_accuracy",
            PREREGISTERED_GATE_THRESHOLDS[
                "supported_mutation_direction_accuracy"
            ],
            summary.get("supported_mutation_direction", {}).get(
                "end_to_end_accuracy_unknown_is_wrong"
            ),
            summary.get("supported_mutation_direction", {}),
        ),
    )
    gates: list[dict[str, Any]] = []
    for gate_id, threshold, observed, evidence in specifications:
        numeric = isinstance(observed, (int, float)) and not isinstance(observed, bool)
        passed = bool(numeric and math.isfinite(float(observed)) and observed >= threshold)
        gates.append(
            {
                "gate_id": gate_id,
                "comparison": "GREATER_THAN_OR_EQUAL",
                "threshold": threshold,
                "observed": observed,
                "passed": passed,
                "missing_or_non_finite_is_failure": True,
                "evidence": dict(evidence),
            }
        )
    failure_count = sum(not item["passed"] for item in gates)
    return {
        "policy": "RIFT_M5_PREREGISTERED_THRESHOLDS_V1",
        "thresholds_are_fixed_and_not_cli_overridable": True,
        "enforced": enforce,
        "status": (
            "NOT_ENFORCED"
            if not enforce
            else ("PASS" if failure_count == 0 else "GATE_FAIL")
        ),
        "gate_count": len(gates),
        "failure_count": failure_count if enforce else 0,
        "would_fail_count": failure_count,
        "gates": gates,
        "reporting_only_metrics": [
            "prerequisite_sequence_exact_and_f1",
            "joint_hyperedge_exact_and_f1",
        ],
    }


def evaluation_status(
    gates: Mapping[str, Any], *, development: bool
) -> str:
    if development:
        return "DEVELOPMENT_ONLY"
    return "PASS" if gates.get("status") == "PASS" else "GATE_FAIL"


def summarize(
    rows: list[dict[str, Any]],
    artifacts: Iterable[Mapping[str, Any]],
    rankings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tp = sum(row["gold_actionable"] and row["prediction"] == "ACTIONABLE" for row in rows)
    fp = sum(not row["gold_actionable"] and row["prediction"] == "ACTIONABLE" for row in rows)
    fn = sum(row["gold_actionable"] and row["prediction"] != "ACTIONABLE" for row in rows)
    negatives = [row for row in rows if not row["gold_actionable"]]
    positives = [row for row in rows if row["gold_actionable"]]
    recipe_status = collections.Counter(row["recipe_status"] for row in positives)
    solver_outcomes = collections.Counter(row["solver_outcome"] for row in positives)
    artifact_status = collections.Counter(
        value["mutation_recipes"].get("status", "MISSING") for value in artifacts
    )
    return {
        "relation_count": len(rows),
        "gold_actionable_count": len(positives),
        "gold_non_actionable_count": len(negatives),
        "frontier": {
            **prf(tp, fp, fn),
            "unknown_on_positive": sum(
                row["prediction"] == "UNKNOWN" for row in positives
            ),
            "unknown_on_negative": sum(
                row["prediction"] == "UNKNOWN" for row in negatives
            ),
            "negative_false_positive_rate": safe_ratio(fp, len(negatives)),
        },
        "gold_fuzzable_source_recall": fuzzable_source_recall_summary(rows),
        "critical_must_influencer_recall": must_influencer_summary(rows),
        "positive_recipe_status": dict(sorted(recipe_status.items())),
        "positive_solver_outcomes": dict(sorted(solver_outcomes.items())),
        "recipe_effectiveness": {
            "gold_actionable_count": len(positives),
            "effective_sat_recipe_count": sum(row["recipe_effective"] for row in positives),
            "abstention_count": sum(not row["recipe_effective"] for row in positives),
            "coverage": safe_ratio(
                sum(row["recipe_effective"] for row in positives), len(positives)
            ),
            "abstention_states": dict(
                sorted(
                    collections.Counter(
                        row["recipe_prediction_state"]
                        for row in positives
                        if not row["recipe_effective"]
                    ).items()
                )
            ),
        },
        "supported_subset": {
            "non_unknown_status_count_diagnostic_only": sum(
                row["recipe_status"] in NON_UNKNOWN_RECIPE for row in positives
            ),
            "effective_sat_recipe_count": sum(
                row["recipe_effective"] for row in positives
            ),
            "gold_suggested_values_fully_covered": sum(
                row["recipe_effective"]
                and row["gold_values_covered"]
                for row in positives
            ),
        },
        "mutation_kind": categorical_metric_summary(positives, "mutation_kind"),
        "mutation_direction": categorical_metric_summary(
            positives, "mutation_direction"
        ),
        "supported_mutation_direction": supported_direction_summary(positives),
        "suggested_values": suggested_value_summary(positives),
        "prerequisite_presence": selective_presence_summary(
            positives,
            "prerequisite",
            "COMPLETE",
            "NO_PREREQUISITE",
        ),
        "prerequisite_sequence": prerequisite_sequence_summary(positives),
        "timing_presence": selective_presence_summary(
            positives,
            "timing_metric",
            "EXACT",
            "NO_TIMING_CONTRACT",
        ),
        "joint_action_set": joint_metric_summary(positives),
        "source_join": {
            "row_count": len(rows),
            "coarse_fallback_count": sum(
                row["source_join"]["used_coarse_fallback"] for row in rows
            ),
            "no_exact_semantic_anchor_count": sum(
                row["source_join"]["exact_semantic_anchor_count"] == 0 for row in rows
            ),
            "join_kind_distribution": dict(
                sorted(
                    collections.Counter(
                        kind
                        for row in rows
                        for kind in (row["source_join"]["join_kinds"] or ["NO_MATCH"])
                    ).items()
                )
            ),
        },
        "ranking": ranking_summary(rankings),
        "unlabelled_structured_metrics": {
            "target_predicate_selector": "NOT_LABELLED",
            "external_action_coordinate": "NOT_LABELLED",
            "prerequisite_dag_nodes": "NOT_LABELLED",
            "prerequisite_dag_edges": "NOT_LABELLED",
            "prerequisite_alternatives": "NOT_LABELLED",
            "timing_structured_fields": "NOT_LABELLED",
            "timing_bounds": "NOT_LABELLED",
            "timing_endpoints": "NOT_LABELLED",
            "timing_actions": "NOT_LABELLED",
        },
        "artifact_status_distribution": dict(sorted(artifact_status.items())),
    }


def evaluate(
    result_root: pathlib.Path,
    frozen_root: pathlib.Path,
    enriched_root: pathlib.Path,
    gold_root: pathlib.Path,
    expected_cases: int,
    expected_run_manifest_sha256: str | None = None,
    formal: bool = False,
    development: bool = False,
) -> dict[str, Any]:
    mode, enforce_gates = resolve_evaluation_mode(
        formal=formal, development=development
    )
    if formal and expected_run_manifest_sha256 is None:
        raise RunError("formal evaluation requires --expected-run-manifest-sha256")
    frozen_manifest, artifacts_by_case = validate_sealed_run(
        result_root,
        frozen_root,
        enriched_root,
        expected_cases,
        expected_run_manifest_sha256,
        formal,
    )
    # Private phase begins only after validate_sealed_run returns.
    from evaluate import load_private_truth

    private_cases = load_private_truth(
        gold_root.resolve(strict=True), frozen_root, frozen_manifest
    )
    if len(private_cases) != expected_cases:
        raise RunError("private/public case inventories do not close")
    rows: list[dict[str, Any]] = []
    rankings: list[dict[str, Any]] = []
    for private in private_cases:
        case_id = str(private["case_id"])
        artifacts = artifacts_by_case.get(case_id)
        if artifacts is None:
            raise RunError(f"sealed run lacks private join case {case_id}")
        case_rows = relation_rows(private, artifacts)
        rows.extend(case_rows)
        rankings.extend(ranking_rows(private, artifacts, case_rows))
    rows.sort(key=lambda item: (item["case_id"], item["source_id"], item["ap_id"]))
    rankings.sort(key=lambda item: (item["case_id"], item["ap_id"]))
    summary = summarize(rows, artifacts_by_case.values(), rankings)
    gates = evaluate_preregistered_gates(summary, enforce=enforce_gates)
    return {
        "schema_version": "rift.m5.micro-evaluation.v3",
        "status": evaluation_status(gates, development=development),
        "evaluation_mode": mode,
        "oracle": {
            "kind": "MECHANICAL_TEMPLATE_ORACLE",
            "real_project_human_labels": "PENDING_TWO_ANNOTATORS_AND_ARBITRATION",
            "results_must_not_be_extrapolated_to_real_projects": True,
        },
        "phase_boundary": {
            "sealed_run_validated_before_private_gold_load": True,
            "unknown_is_never_credited_as_negative": True,
            "formal_mode": formal,
            "development_mode": development,
            "external_run_commitment_verified": expected_run_manifest_sha256
            is not None,
            "serial_parallel_determinism_verified": formal,
            "preregistered_gates_enforced": enforce_gates,
        },
        "run_manifest_sha256": sha256_file(result_root / "run_manifest.json"),
        "preregistered_gates": gates,
        "summary": summary,
        "rows": rows,
        "ranking_rows": rankings,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--frozen-root", type=pathlib.Path, default=DEFAULT_FROZEN)
    parser.add_argument(
        "--enriched-bundle",
        type=pathlib.Path,
        default=HERE / "bundle",
    )
    parser.add_argument("--gold-root", type=pathlib.Path, default=DEFAULT_GOLD)
    parser.add_argument("--expected-cases", type=int, default=120)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--formal", action="store_true")
    mode.add_argument(
        "--development",
        action="store_true",
        help="compute every metric and would-fail gate without enforcing thresholds",
    )
    parser.add_argument("--expected-run-manifest-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    arguments = parse_args(argv)
    try:
        result = evaluate(
            arguments.result_root.resolve(strict=True),
            arguments.frozen_root.resolve(strict=True),
            arguments.enriched_bundle.resolve(strict=True),
            arguments.gold_root,
            arguments.expected_cases,
            arguments.expected_run_manifest_sha256,
            arguments.formal,
            arguments.development,
        )
        write_json_atomic(arguments.output.resolve(), result)
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        AcceptanceError,
        RunError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        result["status"],
        f"relations={summary['relation_count']}",
        f"frontier_f1={summary['frontier']['f1']}",
        f"effective_sat_recipes={summary['supported_subset']['effective_sat_recipe_count']}",
        f"gate_failures={result['preregistered_gates']['would_fail_count']}",
    )
    return 2 if result["status"] == "GATE_FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
