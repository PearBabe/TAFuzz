#!/usr/bin/env python3
"""Build-time independent validator for the sealed RIFT-M5 portability matrix.

The matrix is deliberately only an index.  This validator reopens and hashes
every referenced file, reconstructs the identities embedded in both RIFT
certificates, checks Git and compile-database scope, and derives model-pack and
UNKNOWN metrics from the semantic artifacts.  A copied JSON receipt is never
accepted as a substitute for the referenced bytes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


MATRIX_SCHEMA_VERSION = "rift.sealed-portability-matrix/1.0.0"
INPUT_SCHEMA_VERSION = "rift.portability-matrix-input/1.0.0"
EVIDENCE_KIND = "rift.m5.sealed-portability-evidence"
CLAIM_STATUS = "SEALED_PORTABILITY_EVIDENCE"
CONTRACT_ID = "RIFT-PORTABILITY-1"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
PROJECT_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}\Z")
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".m", ".mm"}

M4_ARTIFACT_NAMES = {
    "semantic_index": "semantic_index.json",
    "ap_bindings": "ap_bindings.json",
    "contextual_influence_graph": "contextual_influence_graph.json",
    "ap_influence_cones": "ap_influence_cones.json",
    "analysis_certificate": "analysis_certificate.json",
}
M5_ARTIFACT_NAMES = {
    "model_fact_overlay": "model_fact_overlay.json",
    "predicate_occurrence_bindings": "predicate_occurrence_bindings.json",
    "frontier_candidates": "frontier_candidates.json",
    "fuzzable_frontier": "fuzzable_frontier.json",
    "mutation_recipes": "mutation_recipes.json",
    "recipe_replay_obligations": "recipe_replay_obligations.json",
    "m5_analysis_certificate": "m5_analysis_certificate.json",
}
REQUIRED_ARTIFACT_NAMES = {**M4_ARTIFACT_NAMES, **M5_ARTIFACT_NAMES}
REQUIRED_SCHEMA_VERSIONS = {
    "semantic_index": "2.0.0",
    "ap_bindings": "1.0.0",
    "contextual_influence_graph": "2.0.0",
    "ap_influence_cones": "1.0.0",
    "analysis_certificate": "2.0.0",
    "model_fact_overlay": "1.0.0",
    "predicate_occurrence_bindings": "1.0.0",
    "frontier_candidates": "3.0.0",
    "fuzzable_frontier": "2.0.0",
    "mutation_recipes": "1.0.0",
    "recipe_replay_obligations": "1.0.0",
    "m5_analysis_certificate": "1.0.0",
}
ALLOWED_STATUS = {"COMPLETE", "CONSERVATIVE_INCOMPLETE"}
ALLOWED_SCOPE = {"FULL_COMPILE_DB", "SELECTED_REAL_TU"}


class MatrixError(ValueError):
    """A fail-closed portability validation error."""


class DuplicateKeyError(MatrixError):
    pass


def fail(message: str) -> None:
    raise MatrixError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read strict JSON {path}: {error}")


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        fail(f"value is not canonical JSON: {error}")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def json_exact_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's ``True == 1`` coercion."""
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        fail(f"cannot hash {path}: {error}")
    return digest.hexdigest()


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    return value


def require_list(value: Any, field: str, *, nonempty: bool = True) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        fail(f"{field} must be {'a non-empty' if nonempty else 'an'} array")
    return value


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{field} must be a non-empty string")
    return value


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        fail(f"{field} must be a boolean")
    return value


def require_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        fail(f"{field} must be an integer >= {minimum}")
    return value


def require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{field} must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        fail(f"{field} must be a finite non-negative number")
    return result


def require_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        fail(f"{field} must be a lowercase SHA-256")
    return value


def require_exact_keys(value: Mapping[str, Any], keys: Iterable[str], field: str) -> None:
    expected = set(keys)
    observed = set(value)
    if observed != expected:
        fail(
            f"{field} keys differ: missing={sorted(expected-observed)}, "
            f"unexpected={sorted(observed-expected)}"
        )


def resolve_path(raw: Any, field: str, base: Path, *, directory: bool = False) -> Path:
    text = require_string(raw, field)
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        result = candidate.resolve(strict=True)
    except FileNotFoundError:
        fail(f"{field} does not exist: {candidate}")
    if directory and not result.is_dir():
        fail(f"{field} is not a directory: {result}")
    if not directory and not result.is_file():
        fail(f"{field} is not a regular file: {result}")
    return result


def artifact_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        fail(f"artifact is not a regular file: {resolved}")
    return {
        "path": str(resolved),
        "size": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def verify_artifact(record_value: Any, field: str, base: Path) -> Path:
    record = require_object(record_value, field)
    require_exact_keys(record, ("path", "size", "sha256"), field)
    path = resolve_path(record.get("path"), f"{field}.path", base)
    expected_size = require_int(record.get("size"), f"{field}.size")
    observed_size = path.stat().st_size
    if observed_size != expected_size:
        fail(f"{field}.size mismatch: declared={expected_size}, observed={observed_size}")
    expected_sha = require_sha(record.get("sha256"), f"{field}.sha256")
    observed_sha = sha256_file(path)
    if observed_sha != expected_sha:
        fail(f"{field}.sha256 mismatch: declared={expected_sha}, observed={observed_sha}")
    return path


def descriptor_by_kind(values: Any, field: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, item_value in enumerate(require_list(values, field)):
        item = require_object(item_value, f"{field}[{index}]")
        kind = require_string(item.get("kind"), f"{field}[{index}].kind")
        if kind in result:
            fail(f"{field} contains duplicate kind {kind!r}")
        result[kind] = item
    return result


def descriptor_path_matches(
    descriptor: Mapping[str, Any], expected: Path, field: str,
) -> None:
    path = Path(require_string(descriptor.get("path"), f"{field}.path"))
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError:
        fail(f"{field}.path does not exist: {path}")
    if not os.path.samefile(resolved, expected):
        fail(f"{field}.path does not name the sealed artifact")


def canonical_component_identity(values: Any, field: str) -> tuple[str, set[str]]:
    components: list[dict[str, str]] = []
    shas: set[str] = set()
    seen_ids: set[str] = set()
    for index, item_value in enumerate(require_list(values, field)):
        item = require_object(item_value, f"{field}[{index}]")
        component_id = require_string(item.get("component_id"), f"{field}[{index}].component_id")
        if component_id in seen_ids:
            fail(f"{field} contains duplicate component_id {component_id!r}")
        seen_ids.add(component_id)
        component = {
            "component_kind": require_string(item.get("component_kind"), f"{field}[{index}].component_kind"),
            "name": require_string(item.get("name"), f"{field}[{index}].name"),
            "version": require_string(item.get("version"), f"{field}[{index}].version"),
            "sha256": require_sha(item.get("sha256"), f"{field}[{index}].sha256"),
        }
        components.append(component)
        shas.add(component["sha256"])
    components.sort(key=lambda item: tuple(item[key] for key in sorted(item)))
    return canonical_sha256(components), shas


def selected_tree_digest(root: Path, records_value: Any, field: str) -> tuple[str, int]:
    records = require_list(records_value, field)
    material = hashlib.sha256()
    previous = ""
    for index, item_value in enumerate(records):
        item = require_object(item_value, f"{field}[{index}]")
        require_exact_keys(item, ("path", "sha256"), f"{field}[{index}]")
        relative = require_string(item.get("path"), f"{field}[{index}].path")
        if relative <= previous:
            fail(f"{field} paths must be strictly sorted and unique")
        previous = relative
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            fail(f"{field}[{index}].path escapes its root")
        if not candidate.is_file():
            fail(f"{field}[{index}] is missing from the live tree: {candidate}")
        payload = candidate.read_bytes()
        observed_sha = hashlib.sha256(payload).hexdigest()
        if observed_sha != require_sha(item.get("sha256"), f"{field}[{index}].sha256"):
            fail(f"{field}[{index}] content differs from build manifest")
        relative_bytes = relative.encode("utf-8")
        material.update(len(relative_bytes).to_bytes(8, "big"))
        material.update(relative_bytes)
        material.update(len(payload).to_bytes(8, "big"))
        material.update(payload)
    return material.hexdigest(), len(records)


def compile_database_facts(path: Path) -> dict[str, Any]:
    value = load_json(path)
    entries = require_list(value, f"compile database {path}")
    canonical_entries: list[bytes] = []
    source_files: list[str] = []
    for index, item_value in enumerate(entries):
        item = require_object(item_value, f"compile database {path}[{index}]")
        require_string(item.get("directory"), f"compile database {path}[{index}].directory")
        source = require_string(item.get("file"), f"compile database {path}[{index}].file")
        if Path(source).suffix.casefold() not in SOURCE_SUFFIXES:
            fail(f"compile database {path}[{index}] is not a C/C++ translation unit")
        has_command = isinstance(item.get("command"), str) and bool(item.get("command"))
        has_arguments = isinstance(item.get("arguments"), list) and bool(item.get("arguments"))
        if has_command == has_arguments:
            fail(f"compile database {path}[{index}] must have exactly one of command/arguments")
        if has_arguments and not all(isinstance(arg, str) and arg for arg in item["arguments"]):
            fail(f"compile database {path}[{index}].arguments is invalid")
        canonical_entries.append(canonical_json_bytes(item))
        source_files.append(str(Path(source).resolve()))
    if len(canonical_entries) != len(set(canonical_entries)):
        fail(f"compile database {path} contains exact duplicate entries")
    digest = hashlib.sha256()
    for encoded in sorted(canonical_entries):
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return {
        "entry_count": len(entries),
        "semantic_sha256": digest.hexdigest(),
        "entry_set": set(canonical_entries),
        "source_files": source_files,
    }


def parse_elapsed_seconds(raw: str) -> float:
    parts = raw.strip().split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) * 60.0 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
    except ValueError:
        pass
    fail(f"invalid GNU time elapsed value: {raw!r}")


def parse_gnu_time_receipt(path: Path, expected_token: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="strict")
    patterns = {
        "command": r'^\s*Command being timed:\s*"(.*)"\s*$',
        "elapsed": r"^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)\s*$",
        "rss": r"^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$",
        "exit": r"^\s*Exit status:\s*(-?\d+)\s*$",
    }
    found: dict[str, str] = {}
    for line in text.splitlines():
        for key, pattern in patterns.items():
            match = re.match(pattern, line)
            if match:
                if key in found:
                    fail(f"GNU time receipt {path} repeats field {key}")
                found[key] = match.group(1)
    if set(found) != set(patterns):
        fail(f"GNU time receipt {path} lacks fields {sorted(set(patterns)-set(found))}")
    if int(found["exit"]) != 0:
        fail(f"GNU time receipt {path} records non-zero exit status")
    if expected_token not in found["command"]:
        fail(f"GNU time receipt {path} command does not contain {expected_token!r}")
    return {
        "command": found["command"],
        "wall_seconds": parse_elapsed_seconds(found["elapsed"]),
        "peak_rss_bytes": int(found["rss"]) * 1024,
        "exit_status": 0,
    }


MODEL_LAYER = {"platform": 0, "framework": 1, "project_adapter": 2}
MODEL_SELECTOR_KIND = {"exact_qualified_signature": 0, "exact_usr": 1, "typed_field": 2}
MODEL_PROJECTION = {
    "matched_node": 0, "formal_parameter": 1, "call_argument": 2,
    "call_result": 3, "receiver": 4,
}
MODEL_JOIN = {
    "same_object": 0, "same_scope": 1, "same_generation": 2,
    "same_handle": 3, "same_callsite": 4, "same_task": 5,
}
MODEL_FACT_KIND = {
    "external_boundary": 0, "semantic_transfer": 1, "event_link": 2,
    "timer_transition": 3, "queue_transition": 4, "lifecycle_transition": 5,
    "scope_key": 6, "clock_relation": 7, "persistence_transition": 8,
}
MODEL_CERTAINTY = {"must": 0, "may": 1, "modelled": 2, "unknown": 3}
MODEL_VALUE_KIND = {
    "bool": 0, "integer": 1, "floating": 2, "enum": 3, "bitvector": 4,
    "timestamp": 5, "duration": 6, "pointer": 7, "record": 8,
    "array": 9, "unknown": 10,
}


def model_pack_semantic_sha256(pack: Mapping[str, Any]) -> str:
    """Reproduce the executable model-pack/2.0.0 byte contract."""
    material = bytearray()

    def append(value: Any) -> None:
        material.extend(str(value).encode("utf-8"))

    def nul() -> None:
        material.append(0)

    def append_value_type(value_type: Mapping[str, Any]) -> None:
        append(MODEL_VALUE_KIND[value_type["kind"]]); nul()
        append(value_type["canonical"]); nul()
        if "bit_width" in value_type: append(value_type["bit_width"])
        nul()
        if "signed" in value_type: append("1" if value_type["signed"] else "0")
        nul()
        if "unit" in value_type: append(value_type["unit"])

    append("model-pack-semantic/2.0.0")
    append(pack["schema_version"]); nul()
    append(pack["model_pack_id"]); nul()
    append(pack["model_pack_version"]); nul()
    append(MODEL_LAYER[pack["layer"]]); nul()
    append("1" if pack["property_independent"] else "0"); nul()
    target = pack["target"]
    for key in ("target_version", "target_abi", "evidence_id", "digest_policy"):
        append(target[key]); nul()
    limits = pack["resource_limits"]
    limit_keys = (
        "max_selector_matches", "max_capture_values", "max_join_assignments",
        "max_emitted_facts",
    )
    for index, key in enumerate(limit_keys):
        append(limits[key])
        if index + 1 != len(limit_keys): nul()
    for selector in sorted(pack["selectors"], key=lambda item: item["selector_id"]):
        append(selector["selector_id"]); nul()
        append(MODEL_SELECTOR_KIND[selector["kind"]]); nul()
        if "exact_value" in selector: append(selector["exact_value"])
        nul()
        if "owner_selector_ref" in selector: append(selector["owner_selector_ref"])
        for field_name in selector.get("field_path", []): nul(); append(field_name)
        if "canonical_type" in selector: append(selector["canonical_type"])
        nul(); append("1" if selector.get("application_private", False) else "0")
    for rule in sorted(pack["rules"], key=lambda item: item["rule_id"]):
        append(rule["rule_id"]); nul(); append(rule["evidence_note"])
        for match in sorted(rule["matches"], key=lambda item: item["match_id"]):
            append(match["match_id"]); nul(); append(match["selector_ref"])
        for capture in sorted(rule["captures"], key=lambda item: item["capture_id"]):
            append(capture["capture_id"]); nul(); append(capture["match_ref"]); nul()
            append(MODEL_PROJECTION[capture["projection"]]); nul()
            if "index" in capture: append(capture["index"])
        for join in sorted(rule["joins"], key=lambda item: item["join_id"]):
            append(join["join_id"]); nul(); append(MODEL_JOIN[join["kind"]]); nul()
            append(join["left_capture_ref"]); nul(); append(join["right_capture_ref"])
        for emit in sorted(rule["emits"], key=lambda item: item["emit_id"]):
            append(emit["emit_id"]); nul(); append(MODEL_FACT_KIND[emit["fact_kind"]]); nul()
            append(emit["source_capture_ref"]); nul()
            if "target_capture_ref" in emit: append(emit["target_capture_ref"])
            nul(); append(MODEL_CERTAINTY[emit["certainty"]]); nul()
            append(emit["transfer_relation"])
            action = emit.get("external_action")
            if action is not None:
                append(action["action_schema_id"]); nul(); append(action["action_class"]); nul()
                append(action["channel"]); nul(); append(action["operation"]); nul()
                append_value_type(action["payload_type"]); nul(); append(action["payload_slot"]); nul()
                append(action["scope_schema"]); nul(); append(action["generation_schema"]); nul()
                append(action["timing_capability"]); nul(); append(action["required_capability"])
    return hashlib.sha256(bytes(material)).hexdigest()


def count_non_comment_lines(path: Path) -> int:
    count = 0
    in_block = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if in_block:
            if "*/" in line:
                in_block = False
                line = line.split("*/", 1)[1].strip()
            else:
                continue
        if line.startswith("/*"):
            if "*/" not in line[2:]:
                in_block = True
            continue
        if line and not line.startswith(("//", "#")):
            count += 1
    return count


def model_pack_facts(path: Path) -> dict[str, Any]:
    pack = require_object(load_json(path), f"model pack {path}")
    if pack.get("schema_version") != "2.0.0":
        fail(f"model pack {path} is not executable schema 2.0.0")
    layer = require_string(pack.get("layer"), f"model pack {path}.layer")
    if layer not in MODEL_LAYER:
        fail(f"model pack {path}.layer is unsupported")
    if pack.get("property_independent") is not True:
        fail(f"model pack {path} is not property-independent")
    rules = require_list(pack.get("rules"), f"model pack {path}.rules")
    selectors = require_list(pack.get("selectors"), f"model pack {path}.selectors")
    if layer != "project_adapter" and any(item.get("application_private") is True for item in selectors):
        fail(f"generic {layer} pack {path} marks an application-private selector")
    return {
        "model_pack_id": require_string(pack.get("model_pack_id"), f"model pack {path}.model_pack_id"),
        "model_pack_version": require_string(pack.get("model_pack_version"), f"model pack {path}.model_pack_version"),
        "layer": layer,
        "property_independent": True,
        "raw_sha256": sha256_file(path),
        "semantic_sha256": model_pack_semantic_sha256(pack),
        "rule_count": len(rules),
        "selector_count": len(selectors),
        "non_comment_lines": count_non_comment_lines(path),
    }


def unknown_metrics(artifacts: Mapping[str, Path]) -> dict[str, Any]:
    frontier = require_object(load_json(artifacts["frontier_candidates"]), "frontier_candidates")
    recipes = require_object(load_json(artifacts["mutation_recipes"]), "mutation_recipes")
    overlay = require_object(load_json(artifacts["model_fact_overlay"]), "model_fact_overlay")
    m4 = require_object(load_json(artifacts["analysis_certificate"]), "analysis_certificate")
    m5 = require_object(load_json(artifacts["m5_analysis_certificate"]), "m5_analysis_certificate")
    candidates = require_list(frontier.get("candidates"), "frontier_candidates.candidates", nonempty=False)
    recipe_values = require_list(recipes.get("recipes"), "mutation_recipes.recipes", nonempty=False)
    candidate_counts = Counter(require_string(item.get("disposition"), "candidate.disposition") for item in candidates)
    recipe_counts = Counter(require_string(item.get("status"), "recipe.status") for item in recipe_values)
    solver = require_object(m5.get("solver"), "m5_analysis_certificate.solver")
    return {
        "analysis_status": require_string(m5.get("status"), "m5_analysis_certificate.status"),
        "candidate_dispositions": dict(sorted(candidate_counts.items())),
        "candidate_with_uncertainty_count": sum(bool(item.get("uncertainty_reasons")) for item in candidates),
        "recipe_statuses": dict(sorted(recipe_counts.items())),
        "model_unknown_outcome_count": len(require_list(overlay.get("unknown_outcomes"), "model_fact_overlay.unknown_outcomes", nonempty=False)),
        "model_coverage_gap_count": len(require_list(overlay.get("coverage_gaps"), "model_fact_overlay.coverage_gaps", nonempty=False)),
        "m4_unsupported_construct_count": len(require_list(m4.get("unsupported_constructs"), "analysis_certificate.unsupported_constructs", nonempty=False)),
        "m5_diagnostic_count": len(require_list(m5.get("diagnostics"), "m5_analysis_certificate.diagnostics", nonempty=False)),
        "solver_queries": require_int(solver.get("queries"), "solver.queries"),
        "solver_timeouts": require_int(solver.get("timeouts"), "solver.timeouts"),
        "solver_unsupported": require_int(solver.get("unsupported"), "solver.unsupported"),
    }


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        fail(f"git {' '.join(args)} failed for {root}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def git_repository_facts(root: Path) -> dict[str, Any]:
    top = Path(git_output(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root.resolve(strict=True):
        fail(f"repository root is not the Git toplevel: {root} -> {top}")
    commit = git_output(root, "rev-parse", "HEAD")
    tree = git_output(root, "rev-parse", "HEAD^{tree}")
    if re.fullmatch(r"[0-9a-f]{40,64}", commit) is None or re.fullmatch(r"[0-9a-f]{40,64}", tree) is None:
        fail(f"repository {root} returned invalid commit/tree identities")
    tracked = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=no", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if tracked.returncode != 0:
        fail(f"cannot inspect tracked worktree state for {root}")
    if tracked.stdout:
        fail(f"repository {root} has tracked worktree changes; commit/tree is not the analyzed snapshot")
    return {
        "root_path": str(root.resolve(strict=True)),
        "head_commit": commit,
        "head_tree": tree,
        "tracked_worktree_clean": True,
        "tracked_status_sha256": hashlib.sha256(tracked.stdout).hexdigest(),
    }


def derive_dynamic_literals(projects: Sequence[Mapping[str, Any]]) -> list[str]:
    values: set[str] = set()
    generic_tokens = {"artifact", "property", "project", "portability", "probe", "https", "github", "com", "git"}
    for project in projects:
        for raw in (
            project.get("project_id"),
            require_object(project.get("repository"), "project.repository").get("repository_id"),
            require_object(project.get("property"), "project.property").get("property_id"),
            require_object(project.get("property"), "project.property").get("artifact_id"),
        ):
            if isinstance(raw, str) and len(raw) >= 4:
                values.add(raw)
                for variant in {raw.replace("-", "_"), raw.replace("_", "-"), raw.replace("-", " ")}:
                    if len(variant) >= 4:
                        values.add(variant)
                for token in re.findall(r"[A-Za-z][A-Za-z0-9]+", raw):
                    if len(token) >= 3 and token.casefold() not in generic_tokens:
                        values.add(token)
        for pack in require_list(project.get("model_packs"), "project.model_packs"):
            raw = pack.get("model_pack_id")
            if isinstance(raw, str) and len(raw) >= 4:
                values.add(raw)
        for raw in require_list(project.get("additional_core_forbidden_literals"), "project.additional_core_forbidden_literals", nonempty=False):
            values.add(require_string(raw, "additional_core_forbidden_literal"))
    return sorted(values, key=lambda value: (value.casefold(), value))


def scan_core_literals(
    root: Path, build_manifest: Mapping[str, Any], literals: Sequence[str],
    frozen_literals: Sequence[str], binary: Path,
) -> dict[str, Any]:
    records = require_list(build_manifest.get("production_core_files"), "build_manifest.production_core_files")
    scanned: list[dict[str, str]] = []
    violations: list[str] = []
    folded_literals = [(value, value.casefold()) for value in literals]
    for index, record_value in enumerate(records):
        record = require_object(record_value, f"production_core_files[{index}]")
        relative = require_string(record.get("path"), f"production_core_files[{index}].path")
        path = (root / relative).resolve()
        text = path.read_text(encoding="utf-8", errors="replace").casefold()
        for original, needle in folded_literals:
            if needle in text:
                violations.append(f"{relative}: {original}")
        scanned.append({"path": relative, "sha256": sha256_file(path)})
    # The binary scan is limited to the frozen contract literals; dynamic
    # subject names can legitimately occur in linked tool version metadata.
    binary_folded = binary.read_bytes().lower()
    for original in frozen_literals:
        needle = original.casefold()
        try:
            encoded = needle.encode("ascii")
        except UnicodeEncodeError:
            continue
        if encoded in binary_folded:
            violations.append(f"analyzer_binary: {original}")
    if violations:
        fail("project literal found in generic core: " + "; ".join(violations[:20]))
    return {
        "scanned_file_count": len(scanned),
        "scan_input_sha256": canonical_sha256({"files": scanned, "literals": list(literals)}),
        "violation_count": 0,
        "verdict": "PASS",
    }


def verify_compile_record(value: Any, field: str, base: Path) -> tuple[Path, dict[str, Any]]:
    record = require_object(value, field)
    require_exact_keys(
        record, ("path", "size", "sha256", "semantic_sha256", "entry_count"), field,
    )
    path = verify_artifact(
        {key: record[key] for key in ("path", "size", "sha256")}, field, base,
    )
    facts = compile_database_facts(path)
    if facts["semantic_sha256"] != require_sha(record.get("semantic_sha256"), f"{field}.semantic_sha256"):
        fail(f"{field}.semantic_sha256 mismatch")
    if facts["entry_count"] != require_int(record.get("entry_count"), f"{field}.entry_count", minimum=1):
        fail(f"{field}.entry_count mismatch")
    return path, facts


def compile_record(path: Path) -> dict[str, Any]:
    result = artifact_record(path)
    facts = compile_database_facts(path)
    result.update({
        "semantic_sha256": facts["semantic_sha256"],
        "entry_count": facts["entry_count"],
    })
    return result


def verify_descriptor(
    descriptor: Mapping[str, Any], path: Path, field: str,
    *, expected_kind: str | None = None,
) -> None:
    if expected_kind is not None and descriptor.get("kind") != expected_kind:
        fail(f"{field}.kind mismatch")
    descriptor_path_matches(descriptor, path, field)
    if require_sha(descriptor.get("sha256"), f"{field}.sha256") != sha256_file(path):
        fail(f"{field}.sha256 does not bind the physical artifact")


def validate_detached_report(path: Path, certificate_path: Path, field: str) -> None:
    report = require_object(load_json(path), field)
    if report.get("schema_version") != "rift-m5-detached-verifier/1.0.0":
        fail(f"{field}.schema_version mismatch")
    if report.get("verdict") != "PASS" or require_int(report.get("failures"), f"{field}.failures") != 0:
        fail(f"{field} is not a detached PASS")
    checks = require_int(report.get("checks"), f"{field}.checks", minimum=1)
    findings = require_list(report.get("findings"), f"{field}.findings")
    if checks != len(findings) or any(item.get("status") != "PASS" for item in findings):
        fail(f"{field} findings are not an exact all-PASS ledger")
    if require_sha(report.get("certificate_sha256"), f"{field}.certificate_sha256") != sha256_file(certificate_path):
        fail(f"{field} does not bind the sealed M5 certificate bytes")
    report_certificate = resolve_path(report.get("certificate_path"), f"{field}.certificate_path", path.parent)
    if not os.path.samefile(report_certificate, certificate_path):
        fail(f"{field}.certificate_path differs from the sealed certificate")
    require_int(report.get("physical_files_rehashed"), f"{field}.physical_files_rehashed", minimum=1)


def validate_m4_source_provenance(certificate: Mapping[str, Any], field: str) -> None:
    provenance = require_object(certificate.get("source_input_provenance"), f"{field}.source_input_provenance")
    files = require_list(provenance.get("files"), f"{field}.source_input_provenance.files")
    for index, item_value in enumerate(files):
        item = require_object(item_value, f"{field}.source_input_provenance.files[{index}]")
        expected_sha = require_sha(item.get("sha256"), f"{field}.source_input_provenance.files[{index}].sha256")
        expected_size = require_int(item.get("byte_size"), f"{field}.source_input_provenance.files[{index}].byte_size")
        observed_paths = require_list(item.get("observed_paths"), f"{field}.source_input_provenance.files[{index}].observed_paths")
        found = False
        for raw in observed_paths:
            path = Path(require_string(raw, "observed source path"))
            if path.is_file() and path.stat().st_size == expected_size and sha256_file(path) == expected_sha:
                found = True
                break
        if not found:
            fail(f"{field}.source_input_provenance.files[{index}] has no live matching physical source")


def validate_certificate_chain(
    project: Mapping[str, Any], artifact_paths: Mapping[str, Path],
    shared: Mapping[str, Any], base: Path, field: str,
) -> tuple[str, str, set[str]]:
    m4 = require_object(load_json(artifact_paths["analysis_certificate"]), f"{field}.M4 certificate")
    m5 = require_object(load_json(artifact_paths["m5_analysis_certificate"]), f"{field}.M5 certificate")
    if m4.get("schema_version") != "2.0.0" or m5.get("schema_version") != "1.0.0":
        fail(f"{field} does not contain M4/2.0.0 and M5/1.0.0 certificates")
    if m4.get("status") not in ALLOWED_STATUS or m5.get("status") not in ALLOWED_STATUS:
        fail(f"{field} certificate status is failed or unsupported")

    shared_binary = require_object(shared.get("analyzer_binary"), "shared_identity.analyzer_binary")
    binary_sha = require_sha(shared_binary.get("sha256"), "shared_identity.analyzer_binary.sha256")
    shared_build = require_object(shared.get("build_manifest"), "shared_identity.build_manifest")
    build_sha = require_sha(shared_build.get("sha256"), "shared_identity.build_manifest.sha256")
    core_sha = require_sha(require_object(shared.get("production_core"), "shared_identity.production_core").get("sha256"), "shared_identity.production_core.sha256")
    schema_sha = require_sha(require_object(shared.get("schema_bundle"), "shared_identity.schema_bundle").get("sha256"), "shared_identity.schema_bundle.sha256")

    for certificate, label in ((m4, "M4"), (m5, "M5")):
        analyzer = require_object(certificate.get("analyzer"), f"{field}.{label}.analyzer")
        if analyzer.get("binary_sha256") != binary_sha:
            fail(f"{field}.{label} analyzer binary identity drift")
        build = require_object(certificate.get("build_manifest"), f"{field}.{label}.build_manifest")
        expected = {
            "manifest_sha256": build_sha,
            "production_core_sha256": core_sha,
            "schema_bundle_sha256": schema_sha,
        }
        for key, value in expected.items():
            if build.get(key) != value:
                fail(f"{field}.{label} build identity drift at {key}")
    if m4.get("core_tree_sha256") != core_sha or m4.get("schema_bundle_sha256") != schema_sha:
        fail(f"{field}.M4 top-level core/schema identity drift")

    m4_inputs = descriptor_by_kind(m4.get("inputs"), f"{field}.M4.inputs")
    property_path = verify_artifact(require_object(project.get("property"), f"{field}.property").get("artifact"), f"{field}.property.artifact", base)
    scope = require_object(project.get("scope"), f"{field}.scope")
    analyzed_compile_path, _ = verify_compile_record(scope.get("analyzed_compile_database"), f"{field}.scope.analyzed_compile_database", base)
    verify_descriptor(m4_inputs.get("typed_property_ir", {}), property_path, f"{field}.M4.inputs.typed_property_ir", expected_kind="typed_property_ir")
    verify_descriptor(m4_inputs.get("compile_commands", {}), analyzed_compile_path, f"{field}.M4.inputs.compile_commands", expected_kind="compile_commands")

    m4_outputs = descriptor_by_kind(m4.get("outputs"), f"{field}.M4.outputs")
    for kind in ("semantic_index", "ap_bindings", "contextual_influence_graph", "ap_influence_cones"):
        verify_descriptor(m4_outputs.get(kind, {}), artifact_paths[kind], f"{field}.M4.outputs.{kind}", expected_kind=kind)

    commitments = require_object(m5.get("m4_commitments"), f"{field}.M5.m4_commitments")
    commitment_paths = {
        "analysis_certificate": artifact_paths["analysis_certificate"],
        "typed_property_ir": property_path,
        "semantic_index": artifact_paths["semantic_index"],
        "ap_bindings": artifact_paths["ap_bindings"],
        "contextual_influence_graph": artifact_paths["contextual_influence_graph"],
        "ap_influence_cones": artifact_paths["ap_influence_cones"],
    }
    require_exact_keys(commitments, commitment_paths, f"{field}.M5.m4_commitments")
    for kind, path in commitment_paths.items():
        verify_descriptor(require_object(commitments[kind], f"{field}.M5.m4_commitments.{kind}"), path, f"{field}.M5.m4_commitments.{kind}")

    m5_outputs = descriptor_by_kind(m5.get("outputs"), f"{field}.M5.outputs")
    for kind in (
        "model_fact_overlay", "predicate_occurrence_bindings", "frontier_candidates",
        "fuzzable_frontier", "mutation_recipes", "recipe_replay_obligations",
    ):
        verify_descriptor(m5_outputs.get(kind, {}), artifact_paths[kind], f"{field}.M5.outputs.{kind}", expected_kind=kind)

    executor_path = verify_artifact(project.get("executor_manifest"), f"{field}.executor_manifest", base)
    executor = require_object(m5.get("executor_manifest"), f"{field}.M5.executor_manifest")
    descriptor_path_matches(executor, executor_path, f"{field}.M5.executor_manifest")
    if executor.get("sha256") != sha256_file(executor_path):
        fail(f"{field}.M5.executor_manifest hash mismatch")

    pack_records = require_list(project.get("model_packs"), f"{field}.model_packs")
    certificate_packs = require_list(m5.get("model_packs"), f"{field}.M5.model_packs")
    if len(pack_records) != len(certificate_packs):
        fail(f"{field} model-pack count differs from M5 certificate")
    for index, (record_value, cert_value) in enumerate(zip(pack_records, certificate_packs)):
        record = require_object(record_value, f"{field}.model_packs[{index}]")
        cert = require_object(cert_value, f"{field}.M5.model_packs[{index}]")
        pack_path = verify_artifact(record.get("artifact"), f"{field}.model_packs[{index}].artifact", base)
        descriptor_path_matches(cert, pack_path, f"{field}.M5.model_packs[{index}]")
        facts = model_pack_facts(pack_path)
        expected_record = {**facts, "artifact": record.get("artifact")}
        if not json_exact_equal(record, expected_record):
            fail(f"{field}.model_packs[{index}] differs from physical pack facts")
        for key in ("model_pack_id", "model_pack_version", "layer"):
            if cert.get(key) != facts[key]:
                fail(f"{field}.M5.model_packs[{index}].{key} mismatch")
        if cert.get("sha256") != facts["raw_sha256"] or cert.get("semantic_sha256") != facts["semantic_sha256"]:
            fail(f"{field}.M5.model_packs[{index}] raw/semantic digest mismatch")

    m4_toolchain_sha, m4_component_shas = canonical_component_identity(m4.get("toolchain"), f"{field}.M4.toolchain")
    m5_toolchain_sha, m5_component_shas = canonical_component_identity(m5.get("runtime_components"), f"{field}.M5.runtime_components")
    validate_m4_source_provenance(m4, f"{field}.M4")
    return m4_toolchain_sha, m5_toolchain_sha, m4_component_shas | m5_component_shas


def validate_project(
    project_value: Any, shared: Mapping[str, Any], base: Path, index: int,
) -> dict[str, Any]:
    field = f"projects[{index}]"
    project = require_object(project_value, field)
    require_exact_keys(project, (
        "project_id", "repository", "scope", "property", "result_root",
        "artifacts", "executor_manifest", "model_packs", "observed_identities",
        "performance", "uncertainty", "adaptation_effort",
        "additional_core_forbidden_literals",
    ), field)
    project_id = require_string(project.get("project_id"), f"{field}.project_id")
    if PROJECT_ID_RE.fullmatch(project_id) is None:
        fail(f"{field}.project_id is not a stable lowercase slug")

    repository = require_object(project.get("repository"), f"{field}.repository")
    require_exact_keys(repository, (
        "repository_id", "root_path", "head_commit", "head_tree",
        "tracked_worktree_clean", "tracked_status_sha256",
    ), f"{field}.repository")
    repository_id = require_string(repository.get("repository_id"), f"{field}.repository.repository_id")
    root = resolve_path(repository.get("root_path"), f"{field}.repository.root_path", base, directory=True)
    git_facts = git_repository_facts(root)
    expected_git = {**git_facts, "repository_id": repository_id}
    if not json_exact_equal(repository, expected_git):
        fail(f"{field}.repository differs from live Git commit/tree state")

    result_root = resolve_path(project.get("result_root"), f"{field}.result_root", base, directory=True)
    artifact_records = require_object(project.get("artifacts"), f"{field}.artifacts")
    require_exact_keys(
        artifact_records, set(REQUIRED_ARTIFACT_NAMES) | {"detached_report"},
        f"{field}.artifacts",
    )
    artifact_paths: dict[str, Path] = {}
    for kind, filename in REQUIRED_ARTIFACT_NAMES.items():
        path = verify_artifact(artifact_records[kind], f"{field}.artifacts.{kind}", base)
        if path.parent != result_root or path.name != filename:
            fail(f"{field}.artifacts.{kind} is not {filename} directly under result_root")
        value = require_object(load_json(path), f"{field}.artifacts.{kind}")
        if value.get("schema_version") != REQUIRED_SCHEMA_VERSIONS[kind]:
            fail(f"{field}.artifacts.{kind} schema version mismatch")
        artifact_paths[kind] = path
    detached_path = verify_artifact(
        artifact_records["detached_report"], f"{field}.artifacts.detached_report", base,
    )
    validate_detached_report(detached_path, artifact_paths["m5_analysis_certificate"], f"{field}.detached_report")

    property_value = require_object(project.get("property"), f"{field}.property")
    require_exact_keys(property_value, ("artifact_id", "property_id", "artifact"), f"{field}.property")
    property_path = verify_artifact(property_value.get("artifact"), f"{field}.property.artifact", base)
    property_json = require_object(load_json(property_path), f"{field}.property")
    for key in ("artifact_id", "property_id"):
        if property_value.get(key) != require_string(property_json.get(key), f"{field}.property.{key}"):
            fail(f"{field}.property.{key} differs from physical Property IR")

    scope = require_object(project.get("scope"), f"{field}.scope")
    require_exact_keys(scope, (
        "kind", "full_compile_database", "analyzed_compile_database",
        "analyzed_tu_count", "indexed_tu_count", "selection_reason",
    ), f"{field}.scope")
    scope_kind = require_string(scope.get("kind"), f"{field}.scope.kind")
    if scope_kind not in ALLOWED_SCOPE:
        fail(f"{field}.scope.kind is unsupported")
    full_path, full_facts = verify_compile_record(scope.get("full_compile_database"), f"{field}.scope.full_compile_database", base)
    analyzed_path, analyzed_facts = verify_compile_record(scope.get("analyzed_compile_database"), f"{field}.scope.analyzed_compile_database", base)
    if require_int(scope.get("analyzed_tu_count"), f"{field}.scope.analyzed_tu_count", minimum=1) != analyzed_facts["entry_count"]:
        fail(f"{field}.scope.analyzed_tu_count mismatch")
    semantic_index = require_object(load_json(artifact_paths["semantic_index"]), f"{field}.semantic_index")
    indexed = len(require_list(semantic_index.get("translation_units"), f"{field}.semantic_index.translation_units"))
    if require_int(scope.get("indexed_tu_count"), f"{field}.scope.indexed_tu_count", minimum=1) != indexed:
        fail(f"{field}.scope.indexed_tu_count mismatch")
    if indexed != analyzed_facts["entry_count"]:
        fail(f"{field} did not index every analyzed compile-database entry")
    require_string(scope.get("selection_reason"), f"{field}.scope.selection_reason")
    if scope_kind == "FULL_COMPILE_DB":
        if not os.path.samefile(full_path, analyzed_path) or full_facts["semantic_sha256"] != analyzed_facts["semantic_sha256"]:
            fail(f"{field} claims FULL_COMPILE_DB but analyzed DB is a projection")
    else:
        if analyzed_facts["entry_count"] >= full_facts["entry_count"]:
            fail(f"{field} claims SELECTED_REAL_TU without a strict projection")
        if not analyzed_facts["entry_set"].issubset(full_facts["entry_set"]):
            fail(f"{field} selected compile entries are not an exact subset of the real full DB")
    repository_sources = 0
    for raw in analyzed_facts["source_files"]:
        try:
            Path(raw).resolve().relative_to(root)
            repository_sources += 1
        except ValueError:
            pass
    if repository_sources == 0:
        fail(f"{field} compile database contains no real TU under the declared repository")

    m4_toolchain_sha, m5_toolchain_sha, component_shas = validate_certificate_chain(
        project, artifact_paths, shared, base, field,
    )
    observed = require_object(project.get("observed_identities"), f"{field}.observed_identities")
    require_exact_keys(observed, (
        "binary_sha256", "build_manifest_sha256", "core_sha256", "schema_sha256",
        "m4_toolchain_sha256", "m5_toolchain_sha256", "verifier_identity_sha256",
    ), f"{field}.observed_identities")
    expected_observed = {
        "binary_sha256": shared["analyzer_binary"]["sha256"],
        "build_manifest_sha256": shared["build_manifest"]["sha256"],
        "core_sha256": shared["production_core"]["sha256"],
        "schema_sha256": shared["schema_bundle"]["sha256"],
        "m4_toolchain_sha256": m4_toolchain_sha,
        "m5_toolchain_sha256": m5_toolchain_sha,
        "verifier_identity_sha256": shared["detached_verifier"]["identity_sha256"],
    }
    if not json_exact_equal(observed, expected_observed):
        fail(f"{field}.observed_identities drift from physical certificates/shared tools")

    performance = require_object(project.get("performance"), f"{field}.performance")
    require_exact_keys(performance, (
        "analysis_receipt", "analysis_wall_seconds", "analysis_peak_rss_bytes",
        "detached_receipt", "detached_wall_seconds", "detached_peak_rss_bytes",
    ), f"{field}.performance")
    analysis_receipt = verify_artifact(performance.get("analysis_receipt"), f"{field}.performance.analysis_receipt", base)
    detached_receipt = verify_artifact(performance.get("detached_receipt"), f"{field}.performance.detached_receipt", base)
    analyzer_path = verify_artifact(shared.get("analyzer_binary"), "shared_identity.analyzer_binary", base)
    verifier_script = verify_artifact(shared["detached_verifier"]["script"], "shared_identity.detached_verifier.script", base)
    observed_analysis_time = parse_gnu_time_receipt(analysis_receipt, analyzer_path.name)
    observed_detached_time = parse_gnu_time_receipt(detached_receipt, verifier_script.name)
    if abs(require_number(performance.get("analysis_wall_seconds"), f"{field}.performance.analysis_wall_seconds") - observed_analysis_time["wall_seconds"]) > 1e-9:
        fail(f"{field}.performance.analysis_wall_seconds mismatch")
    if require_int(performance.get("analysis_peak_rss_bytes"), f"{field}.performance.analysis_peak_rss_bytes") != observed_analysis_time["peak_rss_bytes"]:
        fail(f"{field}.performance.analysis_peak_rss_bytes mismatch")
    if abs(require_number(performance.get("detached_wall_seconds"), f"{field}.performance.detached_wall_seconds") - observed_detached_time["wall_seconds"]) > 1e-9:
        fail(f"{field}.performance.detached_wall_seconds mismatch")
    if require_int(performance.get("detached_peak_rss_bytes"), f"{field}.performance.detached_peak_rss_bytes") != observed_detached_time["peak_rss_bytes"]:
        fail(f"{field}.performance.detached_peak_rss_bytes mismatch")

    derived_unknown = unknown_metrics(artifact_paths)
    if not json_exact_equal(project.get("uncertainty"), derived_unknown):
        fail(f"{field}.uncertainty differs from semantic artifacts")

    effort = require_object(project.get("adaptation_effort"), f"{field}.adaptation_effort")
    require_exact_keys(effort, (
        "setup_minutes", "property_binding_minutes", "adapter_authoring_minutes",
        "model_validation_minutes", "total_human_minutes", "changed_core_files",
        "core_patch_required", "platform_rule_count", "project_adapter_rule_count",
        "platform_non_comment_lines", "project_adapter_non_comment_lines", "notes",
    ), f"{field}.adaptation_effort")
    minute_fields = (
        "setup_minutes", "property_binding_minutes", "adapter_authoring_minutes",
        "model_validation_minutes",
    )
    minute_values = [require_number(effort.get(key), f"{field}.adaptation_effort.{key}") for key in minute_fields]
    if abs(require_number(effort.get("total_human_minutes"), f"{field}.adaptation_effort.total_human_minutes") - sum(minute_values)) > 1e-9:
        fail(f"{field}.adaptation_effort.total_human_minutes is not the component sum")
    if require_int(effort.get("changed_core_files"), f"{field}.adaptation_effort.changed_core_files") != 0:
        fail(f"{field} required a core patch")
    if require_bool(effort.get("core_patch_required"), f"{field}.adaptation_effort.core_patch_required"):
        fail(f"{field} required a core patch")
    require_string(effort.get("notes"), f"{field}.adaptation_effort.notes")
    packs = require_list(project.get("model_packs"), f"{field}.model_packs")
    for layer in ("platform", "project_adapter"):
        selected = [item for item in packs if item["layer"] == layer]
        expected_rules = sum(item["rule_count"] for item in selected)
        expected_lines = sum(item["non_comment_lines"] for item in selected)
        if require_int(
            effort.get(f"{layer}_rule_count"),
            f"{field}.adaptation_effort.{layer}_rule_count",
        ) != expected_rules:
            fail(f"{field}.adaptation_effort.{layer}_rule_count mismatch")
        if require_int(
            effort.get(f"{layer}_non_comment_lines"),
            f"{field}.adaptation_effort.{layer}_non_comment_lines",
        ) != expected_lines:
            fail(f"{field}.adaptation_effort.{layer}_non_comment_lines mismatch")

    extra = require_list(project.get("additional_core_forbidden_literals"), f"{field}.additional_core_forbidden_literals", nonempty=False)
    if len(extra) != len(set(extra)) or not all(isinstance(item, str) and item for item in extra):
        fail(f"{field}.additional_core_forbidden_literals must be unique strings")
    return {
        "project_id": project_id,
        "repository_id": repository_id,
        "repository_root": str(root),
        "commit": repository["head_commit"],
        "tree": repository["head_tree"],
        "full_compile_sha": scope["full_compile_database"]["sha256"],
        "analyzed_compile_sha": scope["analyzed_compile_database"]["sha256"],
        "property_sha": property_value["artifact"]["sha256"],
        "property_id": property_value["property_id"],
        "platform_pack_identity": sorted(
            (item["model_pack_id"], item["model_pack_version"], item["raw_sha256"],
             item["semantic_sha256"], item["rule_count"])
            for item in packs if item["layer"] == "platform"
        ),
        "m4_toolchain_sha": m4_toolchain_sha,
        "m5_toolchain_sha": m5_toolchain_sha,
        "component_shas": component_shas,
    }


def validate_matrix(matrix_value: Any, matrix_path: Path | None = None) -> dict[str, Any]:
    matrix = require_object(matrix_value, "matrix")
    require_exact_keys(matrix, (
        "schema_version", "evidence_kind", "contract_id", "claim_status",
        "matrix_id", "minimum_independent_projects", "shared_identity", "projects",
    ), "matrix")
    if matrix.get("schema_version") != MATRIX_SCHEMA_VERSION:
        fail("unsupported matrix schema_version")
    if matrix.get("evidence_kind") != EVIDENCE_KIND or matrix.get("contract_id") != CONTRACT_ID:
        fail("matrix evidence/contract identity mismatch")
    if matrix.get("claim_status") != CLAIM_STATUS:
        fail("candidate/template matrix cannot satisfy the final portability gate")
    minimum = require_int(matrix.get("minimum_independent_projects"), "minimum_independent_projects", minimum=3)
    if minimum != 3:
        fail("minimum_independent_projects must remain exactly three")
    expected_id_material = copy.deepcopy(matrix)
    expected_id_material.pop("matrix_id")
    expected_id = "portability-matrix:" + canonical_sha256(expected_id_material)
    if matrix.get("matrix_id") != expected_id:
        fail("matrix_id does not bind every other matrix field")
    base = (matrix_path.parent if matrix_path is not None else Path.cwd()).resolve()

    shared = require_object(matrix.get("shared_identity"), "shared_identity")
    require_exact_keys(shared, (
        "analyzer_binary", "build_manifest", "production_core", "schema_bundle",
        "detached_verifier", "toolchain", "core_literal_scan",
    ), "shared_identity")
    analyzer_path = verify_artifact(shared.get("analyzer_binary"), "shared_identity.analyzer_binary", base)
    build_path = verify_artifact(shared.get("build_manifest"), "shared_identity.build_manifest", base)
    build = require_object(load_json(build_path), "build_manifest")
    if build.get("schema_version") != "rift.build-manifest.v1" or build.get("identity_policy") != "relative-path-and-content-v1":
        fail("shared build manifest uses an unsupported identity policy")
    core = require_object(shared.get("production_core"), "shared_identity.production_core")
    require_exact_keys(core, ("root_path", "sha256", "file_count"), "shared_identity.production_core")
    core_root = resolve_path(core.get("root_path"), "shared_identity.production_core.root_path", base, directory=True)
    core_sha, core_count = selected_tree_digest(core_root, build.get("production_core_files"), "build_manifest.production_core_files")
    if core_sha != require_sha(core.get("sha256"), "shared_identity.production_core.sha256") or core_count != require_int(core.get("file_count"), "shared_identity.production_core.file_count", minimum=1):
        fail("shared production-core identity differs from live source")
    if build.get("production_core_sha256") != core_sha:
        fail("build manifest production_core_sha256 mismatch")
    schema = require_object(shared.get("schema_bundle"), "shared_identity.schema_bundle")
    require_exact_keys(schema, ("root_path", "sha256", "file_count"), "shared_identity.schema_bundle")
    schema_root = resolve_path(schema.get("root_path"), "shared_identity.schema_bundle.root_path", base, directory=True)
    schema_sha, schema_count = selected_tree_digest(core_root, build.get("schema_files"), "build_manifest.schema_files")
    if schema_root != core_root / "schema":
        fail("shared schema root is not the schema tree named by the build manifest")
    if schema_sha != require_sha(schema.get("sha256"), "shared_identity.schema_bundle.sha256") or schema_count != require_int(schema.get("file_count"), "shared_identity.schema_bundle.file_count", minimum=1):
        fail("shared schema identity differs from live schemas")
    if build.get("schema_bundle_sha256") != schema_sha:
        fail("build manifest schema_bundle_sha256 mismatch")

    verifier = require_object(shared.get("detached_verifier"), "shared_identity.detached_verifier")
    require_exact_keys(verifier, ("script", "interpreter", "python_version", "identity_sha256"), "shared_identity.detached_verifier")
    script_path = verify_artifact(verifier.get("script"), "shared_identity.detached_verifier.script", base)
    interpreter_path = verify_artifact(verifier.get("interpreter"), "shared_identity.detached_verifier.interpreter", base)
    completed = subprocess.run(
        [str(interpreter_path), "--version"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    observed_version = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0 or observed_version != verifier.get("python_version"):
        fail("detached verifier Python interpreter/version drift")
    verifier_identity = canonical_sha256({
        "script_sha256": sha256_file(script_path),
        "interpreter_sha256": sha256_file(interpreter_path),
        "python_version": observed_version,
    })
    if verifier.get("identity_sha256") != verifier_identity:
        fail("detached verifier identity drift")

    projects = require_list(matrix.get("projects"), "projects")
    if len(projects) < minimum:
        fail(f"sealed portability matrix needs at least {minimum} projects")
    summaries = [validate_project(project, shared, base, index) for index, project in enumerate(projects)]

    distinct_fields = {
        "project_id": [item["project_id"] for item in summaries],
        "repository_id": [item["repository_id"] for item in summaries],
        "repository_root": [item["repository_root"] for item in summaries],
        "commit": [item["commit"] for item in summaries],
        "tree": [item["tree"] for item in summaries],
        "full compile database": [item["full_compile_sha"] for item in summaries],
        "analyzed compile database": [item["analyzed_compile_sha"] for item in summaries],
        "property bytes": [item["property_sha"] for item in summaries],
        "property_id": [item["property_id"] for item in summaries],
    }
    for label, values in distinct_fields.items():
        if len(values) != len(set(values)):
            fail(f"projects are not independent: duplicate {label}")
    platform_identity = summaries[0]["platform_pack_identity"]
    if not platform_identity:
        fail("every project must use a generic platform model pack")
    if any(item["platform_pack_identity"] != platform_identity for item in summaries[1:]):
        fail("generic platform model-pack identity differs between projects")
    if len({item["m4_toolchain_sha"] for item in summaries}) != 1 or len({item["m5_toolchain_sha"] for item in summaries}) != 1:
        fail("toolchain identity differs between projects")

    toolchain = require_object(shared.get("toolchain"), "shared_identity.toolchain")
    require_exact_keys(toolchain, (
        "m4_identity_sha256", "m5_identity_sha256", "combined_identity_sha256",
        "physical_components",
    ), "shared_identity.toolchain")
    if toolchain.get("m4_identity_sha256") != summaries[0]["m4_toolchain_sha"] or toolchain.get("m5_identity_sha256") != summaries[0]["m5_toolchain_sha"]:
        fail("shared toolchain semantic identities differ from certificates")
    expected_combined = canonical_sha256({
        "m4": summaries[0]["m4_toolchain_sha"],
        "m5": summaries[0]["m5_toolchain_sha"],
    })
    if toolchain.get("combined_identity_sha256") != expected_combined:
        fail("shared toolchain combined identity mismatch")
    physical_shas: set[str] = set()
    for index, value in enumerate(require_list(toolchain.get("physical_components"), "shared_identity.toolchain.physical_components")):
        path = verify_artifact(value, f"shared_identity.toolchain.physical_components[{index}]", base)
        digest = sha256_file(path)
        if digest in physical_shas:
            fail("shared toolchain has duplicate physical component bytes")
        physical_shas.add(digest)
    needed_shas = set().union(*(item["component_shas"] for item in summaries))
    if not needed_shas.issubset(physical_shas):
        fail(f"shared toolchain lacks physical components {sorted(needed_shas-physical_shas)}")

    scan = require_object(shared.get("core_literal_scan"), "shared_identity.core_literal_scan")
    require_exact_keys(scan, (
        "contract", "frozen_literals", "dynamic_literals", "scanned_file_count",
        "scan_input_sha256", "violation_count", "verdict",
    ), "shared_identity.core_literal_scan")
    contract_path = verify_artifact(scan.get("contract"), "shared_identity.core_literal_scan.contract", base)
    contract = require_object(load_json(contract_path), "portability contract")
    if contract.get("contract_id") != CONTRACT_ID:
        fail("core literal scan uses the wrong portability contract")
    frozen_literals = require_list(contract.get("core_forbidden_literals"), "contract.core_forbidden_literals")
    if scan.get("frozen_literals") != frozen_literals:
        fail("core literal scan frozen literals differ from contract")
    dynamic_literals = derive_dynamic_literals(projects)
    if scan.get("dynamic_literals") != dynamic_literals:
        fail("core literal scan dynamic subject literals are incomplete")
    observed_scan = scan_core_literals(
        core_root, build, list(frozen_literals) + dynamic_literals,
        frozen_literals, analyzer_path,
    )
    expected_scan = {**observed_scan, "contract": scan.get("contract"), "frozen_literals": frozen_literals, "dynamic_literals": dynamic_literals}
    if not json_exact_equal(scan, expected_scan):
        fail("core literal scan receipt differs from independent live scan")

    return {
        "verdict": "PASS",
        "projects": len(projects),
        "binary_sha256": shared["analyzer_binary"]["sha256"],
        "core_sha256": core_sha,
        "schema_sha256": schema_sha,
        "verifier_identity_sha256": verifier_identity,
        "scope_counts": dict(sorted(Counter(project["scope"]["kind"] for project in projects).items())),
    }


def _ldd_paths(binary: Path) -> list[Path]:
    completed = subprocess.run(
        ["ldd", str(binary)], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        return []
    result: list[Path] = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        candidate: str | None = None
        if "=>" in stripped:
            rhs = stripped.split("=>", 1)[1].strip()
            if rhs and rhs != "not found":
                candidate = rhs.split(" (", 1)[0].strip()
        elif stripped.startswith("/"):
            candidate = stripped.split(" (", 1)[0].strip()
        if candidate and Path(candidate).is_file():
            result.append(Path(candidate).resolve(strict=True))
    return result


def _spec_path(value: Any, field: str, spec_base: Path, *, directory: bool = False) -> Path:
    return resolve_path(value, field, spec_base, directory=directory)


def build_matrix_from_spec(spec_value: Any, spec_path: Path) -> dict[str, Any]:
    spec = require_object(spec_value, "input spec")
    require_exact_keys(spec, (
        "schema_version", "seal_intent", "contract_path", "core_root_path",
        "schema_root_path", "analyzer_binary_path", "build_manifest_path",
        "verifier_path", "python_interpreter_path", "toolchain_component_paths",
        "projects",
    ), "input spec")
    if spec.get("schema_version") != INPUT_SCHEMA_VERSION:
        fail("unsupported portability-matrix input schema")
    if spec.get("seal_intent") != "FINAL_SEAL_REQUEST":
        fail("only FINAL_SEAL_REQUEST can generate sealed evidence; candidate templates are inert")
    spec_base = spec_path.parent.resolve()
    contract_path = _spec_path(spec.get("contract_path"), "contract_path", spec_base)
    contract = require_object(load_json(contract_path), "portability contract")
    if contract.get("contract_id") != CONTRACT_ID:
        fail("input spec references the wrong portability contract")
    frozen_literals = require_list(contract.get("core_forbidden_literals"), "contract.core_forbidden_literals")
    core_root = _spec_path(spec.get("core_root_path"), "core_root_path", spec_base, directory=True)
    schema_root = _spec_path(spec.get("schema_root_path"), "schema_root_path", spec_base, directory=True)
    analyzer_path = _spec_path(spec.get("analyzer_binary_path"), "analyzer_binary_path", spec_base)
    build_path = _spec_path(spec.get("build_manifest_path"), "build_manifest_path", spec_base)
    verifier_path = _spec_path(spec.get("verifier_path"), "verifier_path", spec_base)
    interpreter_path = _spec_path(spec.get("python_interpreter_path"), "python_interpreter_path", spec_base)
    build = require_object(load_json(build_path), "build manifest")
    core_sha, core_count = selected_tree_digest(core_root, build.get("production_core_files"), "build_manifest.production_core_files")
    schema_sha, schema_count = selected_tree_digest(core_root, build.get("schema_files"), "build_manifest.schema_files")
    if schema_root != core_root / "schema":
        fail("schema_root_path must be the schema tree below core_root_path")
    if build.get("production_core_sha256") != core_sha or build.get("schema_bundle_sha256") != schema_sha:
        fail("build manifest no longer matches the live production core/schema")
    version_run = subprocess.run(
        [str(interpreter_path), "--version"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    python_version = (version_run.stdout or version_run.stderr).strip()
    if version_run.returncode != 0 or not python_version:
        fail("cannot identify the detached verifier Python interpreter")
    verifier_identity = canonical_sha256({
        "script_sha256": sha256_file(verifier_path),
        "interpreter_sha256": sha256_file(interpreter_path),
        "python_version": python_version,
    })
    shared: dict[str, Any] = {
        "analyzer_binary": artifact_record(analyzer_path),
        "build_manifest": artifact_record(build_path),
        "production_core": {
            "root_path": str(core_root), "sha256": core_sha, "file_count": core_count,
        },
        "schema_bundle": {
            "root_path": str(schema_root), "sha256": schema_sha, "file_count": schema_count,
        },
        "detached_verifier": {
            "script": artifact_record(verifier_path),
            "interpreter": artifact_record(interpreter_path),
            "python_version": python_version,
            "identity_sha256": verifier_identity,
        },
    }

    project_specs = require_list(spec.get("projects"), "input spec.projects")
    if len(project_specs) < 3:
        fail("input spec must name at least three real projects")
    projects: list[dict[str, Any]] = []
    all_component_shas: set[str] = set()
    component_paths: set[Path] = {analyzer_path}
    m4_identities: list[str] = []
    m5_identities: list[str] = []
    for index, value in enumerate(project_specs):
        field = f"input spec.projects[{index}]"
        item = require_object(value, field)
        require_exact_keys(item, (
            "project_id", "repository_id", "repository_root_path", "result_root_path",
            "detached_report_path", "full_compile_database_path", "analysis_scope",
            "selection_reason", "analysis_time_receipt_path", "detached_time_receipt_path",
            "adaptation_effort", "additional_core_forbidden_literals",
        ), field)
        project_id = require_string(item.get("project_id"), f"{field}.project_id")
        repository_id = require_string(item.get("repository_id"), f"{field}.repository_id")
        repository_root = _spec_path(item.get("repository_root_path"), f"{field}.repository_root_path", spec_base, directory=True)
        result_root = _spec_path(item.get("result_root_path"), f"{field}.result_root_path", spec_base, directory=True)
        detached_path = _spec_path(item.get("detached_report_path"), f"{field}.detached_report_path", spec_base)
        full_compile_path = _spec_path(item.get("full_compile_database_path"), f"{field}.full_compile_database_path", spec_base)
        analysis_receipt_path = _spec_path(item.get("analysis_time_receipt_path"), f"{field}.analysis_time_receipt_path", spec_base)
        detached_receipt_path = _spec_path(item.get("detached_time_receipt_path"), f"{field}.detached_time_receipt_path", spec_base)

        artifact_paths = {kind: result_root / filename for kind, filename in REQUIRED_ARTIFACT_NAMES.items()}
        for kind, path in artifact_paths.items():
            if not path.is_file():
                fail(f"{field} lacks required {kind}: {path}")
        artifacts = {kind: artifact_record(path) for kind, path in artifact_paths.items()}
        artifacts["detached_report"] = artifact_record(detached_path)
        m4 = require_object(load_json(artifact_paths["analysis_certificate"]), f"{field}.M4")
        m5 = require_object(load_json(artifact_paths["m5_analysis_certificate"]), f"{field}.M5")
        validate_detached_report(detached_path, artifact_paths["m5_analysis_certificate"], f"{field}.detached_report")
        m4_inputs = descriptor_by_kind(m4.get("inputs"), f"{field}.M4.inputs")
        property_descriptor = require_object(m4_inputs.get("typed_property_ir"), f"{field}.M4 property")
        compile_descriptor = require_object(m4_inputs.get("compile_commands"), f"{field}.M4 compile DB")
        property_path = resolve_path(property_descriptor.get("path"), f"{field}.M4 property path", artifact_paths["analysis_certificate"].parent)
        analyzed_compile_path = resolve_path(compile_descriptor.get("path"), f"{field}.M4 compile DB path", artifact_paths["analysis_certificate"].parent)
        property_json = require_object(load_json(property_path), f"{field}.property")
        semantic_index = require_object(load_json(artifact_paths["semantic_index"]), f"{field}.semantic_index")
        analyzed_facts = compile_database_facts(analyzed_compile_path)
        scope_kind = require_string(item.get("analysis_scope"), f"{field}.analysis_scope")
        if scope_kind not in ALLOWED_SCOPE:
            fail(f"{field}.analysis_scope is unsupported")
        scope = {
            "kind": scope_kind,
            "full_compile_database": compile_record(full_compile_path),
            "analyzed_compile_database": compile_record(analyzed_compile_path),
            "analyzed_tu_count": analyzed_facts["entry_count"],
            "indexed_tu_count": len(require_list(semantic_index.get("translation_units"), f"{field}.semantic_index.translation_units")),
            "selection_reason": require_string(item.get("selection_reason"), f"{field}.selection_reason"),
        }

        pack_records: list[dict[str, Any]] = []
        for pack_index, pack_value in enumerate(require_list(m5.get("model_packs"), f"{field}.M5.model_packs")):
            descriptor = require_object(pack_value, f"{field}.M5.model_packs[{pack_index}]")
            pack_path = resolve_path(descriptor.get("path"), f"{field}.M5.model_packs[{pack_index}].path", artifact_paths["m5_analysis_certificate"].parent)
            pack_records.append({**model_pack_facts(pack_path), "artifact": artifact_record(pack_path)})
        executor_descriptor = require_object(m5.get("executor_manifest"), f"{field}.M5.executor_manifest")
        executor_path = resolve_path(executor_descriptor.get("path"), f"{field}.M5.executor_manifest.path", artifact_paths["m5_analysis_certificate"].parent)
        m4_toolchain_sha, m4_shas = canonical_component_identity(m4.get("toolchain"), f"{field}.M4.toolchain")
        m5_toolchain_sha, m5_shas = canonical_component_identity(m5.get("runtime_components"), f"{field}.M5.runtime_components")
        m4_identities.append(m4_toolchain_sha)
        m5_identities.append(m5_toolchain_sha)
        all_component_shas.update(m4_shas | m5_shas)
        for runtime in require_list(m5.get("runtime_components"), f"{field}.M5.runtime_components"):
            raw = runtime.get("path")
            if isinstance(raw, str) and Path(raw).is_file():
                component_paths.add(Path(raw).resolve(strict=True))

        analysis_time = parse_gnu_time_receipt(analysis_receipt_path, analyzer_path.name)
        detached_time = parse_gnu_time_receipt(detached_receipt_path, verifier_path.name)
        manual_effort = require_object(item.get("adaptation_effort"), f"{field}.adaptation_effort")
        require_exact_keys(manual_effort, (
            "setup_minutes", "property_binding_minutes", "adapter_authoring_minutes",
            "model_validation_minutes", "notes",
        ), f"{field}.adaptation_effort")
        minute_keys = (
            "setup_minutes", "property_binding_minutes", "adapter_authoring_minutes",
            "model_validation_minutes",
        )
        minutes = {key: require_number(manual_effort.get(key), f"{field}.adaptation_effort.{key}") for key in minute_keys}
        platform = [pack for pack in pack_records if pack["layer"] == "platform"]
        adapter = [pack for pack in pack_records if pack["layer"] == "project_adapter"]
        effort = {
            **minutes,
            "total_human_minutes": sum(minutes.values()),
            "changed_core_files": 0,
            "core_patch_required": False,
            "platform_rule_count": sum(pack["rule_count"] for pack in platform),
            "project_adapter_rule_count": sum(pack["rule_count"] for pack in adapter),
            "platform_non_comment_lines": sum(pack["non_comment_lines"] for pack in platform),
            "project_adapter_non_comment_lines": sum(pack["non_comment_lines"] for pack in adapter),
            "notes": require_string(manual_effort.get("notes"), f"{field}.adaptation_effort.notes"),
        }
        extra = require_list(item.get("additional_core_forbidden_literals"), f"{field}.additional_core_forbidden_literals", nonempty=False)
        project = {
            "project_id": project_id,
            "repository": {"repository_id": repository_id, **git_repository_facts(repository_root)},
            "scope": scope,
            "property": {
                "artifact_id": require_string(property_json.get("artifact_id"), f"{field}.property.artifact_id"),
                "property_id": require_string(property_json.get("property_id"), f"{field}.property.property_id"),
                "artifact": artifact_record(property_path),
            },
            "result_root": str(result_root),
            "artifacts": artifacts,
            "executor_manifest": artifact_record(executor_path),
            "model_packs": pack_records,
            "observed_identities": {
                "binary_sha256": require_object(m5.get("analyzer"), f"{field}.M5.analyzer").get("binary_sha256"),
                "build_manifest_sha256": require_object(m5.get("build_manifest"), f"{field}.M5.build_manifest").get("manifest_sha256"),
                "core_sha256": require_object(m5.get("build_manifest"), f"{field}.M5.build_manifest").get("production_core_sha256"),
                "schema_sha256": require_object(m5.get("build_manifest"), f"{field}.M5.build_manifest").get("schema_bundle_sha256"),
                "m4_toolchain_sha256": m4_toolchain_sha,
                "m5_toolchain_sha256": m5_toolchain_sha,
                "verifier_identity_sha256": verifier_identity,
            },
            "performance": {
                "analysis_receipt": artifact_record(analysis_receipt_path),
                "analysis_wall_seconds": analysis_time["wall_seconds"],
                "analysis_peak_rss_bytes": analysis_time["peak_rss_bytes"],
                "detached_receipt": artifact_record(detached_receipt_path),
                "detached_wall_seconds": detached_time["wall_seconds"],
                "detached_peak_rss_bytes": detached_time["peak_rss_bytes"],
            },
            "uncertainty": unknown_metrics(artifact_paths),
            "adaptation_effort": effort,
            "additional_core_forbidden_literals": [require_string(raw, f"{field}.additional literal") for raw in extra],
        }
        projects.append(project)

    if len(set(m4_identities)) != 1 or len(set(m5_identities)) != 1:
        fail("input runs do not share one exact M4/M5 toolchain identity")
    for raw in require_list(spec.get("toolchain_component_paths"), "toolchain_component_paths", nonempty=False):
        component_paths.add(_spec_path(raw, "toolchain_component_path", spec_base))
    component_paths.update(_ldd_paths(analyzer_path))
    paths_by_sha: dict[str, Path] = {}
    for path in component_paths:
        paths_by_sha.setdefault(sha256_file(path), path)
    missing_components = all_component_shas - set(paths_by_sha)
    if missing_components:
        fail(f"cannot physically close toolchain components: {sorted(missing_components)}")
    shared["toolchain"] = {
        "m4_identity_sha256": m4_identities[0],
        "m5_identity_sha256": m5_identities[0],
        "combined_identity_sha256": canonical_sha256({"m4": m4_identities[0], "m5": m5_identities[0]}),
        "physical_components": [artifact_record(paths_by_sha[digest]) for digest in sorted(all_component_shas)],
    }
    dynamic_literals = derive_dynamic_literals(projects)
    scan = scan_core_literals(
        core_root, build, list(frozen_literals) + dynamic_literals,
        frozen_literals, analyzer_path,
    )
    shared["core_literal_scan"] = {
        "contract": artifact_record(contract_path),
        "frozen_literals": frozen_literals,
        "dynamic_literals": dynamic_literals,
        **scan,
    }
    matrix: dict[str, Any] = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "evidence_kind": EVIDENCE_KIND,
        "contract_id": CONTRACT_ID,
        "claim_status": CLAIM_STATUS,
        "minimum_independent_projects": 3,
        "shared_identity": shared,
        "projects": projects,
    }
    matrix["matrix_id"] = "portability-matrix:" + canonical_sha256(matrix)
    validate_matrix(matrix, spec_path)
    return matrix


def write_json_atomic(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        path = args.matrix.resolve(strict=True)
        summary = validate_matrix(load_json(path), path)
    except (MatrixError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    report = {
        "schema_version": "rift.portability-matrix-validation/1.0.0",
        **summary,
        "matrix_path": str(path),
        "matrix_sha256": sha256_file(path),
    }
    if args.report is not None:
        write_json_atomic(args.report, report)
    print(
        "PASS",
        f"projects={summary['projects']}",
        f"binary={summary['binary_sha256']}",
        f"core={summary['core_sha256']}",
        f"schema={summary['schema_sha256']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
