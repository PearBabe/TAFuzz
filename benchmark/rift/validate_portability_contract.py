#!/usr/bin/env python3
"""Validate the frozen RIFT portability contract and evidence artifacts.

The evaluation gate deliberately does not trust a report's hashes.  Every
reported digest is checked against the referenced artifact, and the generic
core/toolchain identities are derived again from their contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name("portability_contract.json")
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".inc", ".ipp", ".tpp", ".td", ".py", ".pyi", ".json",
    ".jsonc", ".cmake", ".sh", ".bash", ".zsh", ".md", ".markdown",
    ".rst", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".config", ".txt", ".in",
}
SOURCE_NAMES = {
    "cmakelists.txt", "makefile", "meson.build", "meson_options.txt",
    "configure", "configure.ac",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    return value


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{field} must be a non-empty string")
    return value


def require_unique_strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        fail(f"{field} must be {'a' if allow_empty else 'a non-empty'} string list")
    if not all(isinstance(item, str) and item for item in value):
        fail(f"{field} must be {'a' if allow_empty else 'a non-empty'} string list")
    if len(value) != len(set(value)):
        fail(f"{field} contains duplicates")
    return value


def require_number(value: Any, field: str, *, integer: bool = False) -> int | float:
    expected = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, expected):
        fail(f"{field} must be a {'non-negative integer' if integer else 'finite non-negative number'}")
    if value < 0 or (isinstance(value, float) and not math.isfinite(value)):
        fail(f"{field} must be a {'non-negative integer' if integer else 'finite non-negative number'}")
    return value


def require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        fail(f"{field} is not a lowercase hexadecimal SHA-256")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != "1.0.0":
        fail("unsupported contract schema_version")
    if contract.get("contract_id") != "RIFT-PORTABILITY-1":
        fail("unexpected contract_id")
    if contract.get("status") != "FROZEN_BEFORE_CORE_IMPLEMENTATION":
        fail("contract was not frozen before core implementation")

    interface = contract.get("core_interface", {})
    for field in ("required_inputs", "optional_inputs", "required_outputs", "allowed_generic_concepts"):
        require_unique_strings(interface.get(field), f"core_interface.{field}")

    required_inputs = set(interface["required_inputs"])
    if required_inputs != {"typed_property_ir", "compile_commands", "clang_llvm_facts", "versioned_model_pack"}:
        fail("core required-input boundary changed")

    layout = contract.get("source_layout", {})
    if layout.get("implementation_root") != "src/StaticAnalysis":
        fail("implementation root changed")
    generic_roots = require_unique_strings(layout.get("generic_core_roots"), "source_layout.generic_core_roots")
    knowledge_roots = require_unique_strings(
        layout.get("project_knowledge_roots"), "source_layout.project_knowledge_roots"
    )
    if set(generic_roots) & set(knowledge_roots):
        fail("generic and project-knowledge roots overlap")
    implementation_root = PurePosixPath(layout["implementation_root"])
    for root in generic_roots:
        try:
            PurePosixPath(root).relative_to(implementation_root)
        except ValueError:
            fail(f"generic core root is outside implementation root: {root}")

    require_unique_strings(contract.get("core_forbidden_literals"), "core_forbidden_literals")

    model_rules = contract.get("model_pack_rules", {})
    if model_rules.get("must_be_versioned") is not True:
        fail("model packs must be versioned")
    if model_rules.get("must_be_property_independent") is not True:
        fail("model packs must be property independent")
    require_unique_strings(model_rules.get("allowed_rule_classes"), "model_pack_rules.allowed_rule_classes")
    forbidden_rules = set(
        require_unique_strings(model_rules.get("forbidden_rule_classes"), "model_pack_rules.forbidden_rule_classes")
    )
    if "per_property_slice" not in forbidden_rules or "hand_selected_dependency_path" not in forbidden_rules:
        fail("property-specific model rules are not forbidden")

    gate = contract.get("evaluation_gate", {})
    if gate.get("minimum_independent_projects") != 3:
        fail("minimum independent-project gate must remain three")
    for field in (
        "same_analyzer_binary_sha256",
        "same_output_schema_sha256",
        "same_core_tree_sha256",
        "zero_core_source_changes_between_projects",
    ):
        if gate.get(field) is not True:
            fail(f"evaluation_gate.{field} must be true")
    require_unique_strings(gate.get("report_per_project"), "evaluation_gate.report_per_project")
    require_unique_strings(gate.get("failure_conditions"), "evaluation_gate.failure_conditions")


def is_source_file(path: Path) -> bool:
    return path.name.casefold() in SOURCE_NAMES or path.suffix.casefold() in SOURCE_SUFFIXES


def generic_relative_roots(contract: dict[str, Any]) -> list[Path]:
    implementation = PurePosixPath(contract["source_layout"]["implementation_root"])
    return [Path(PurePosixPath(root).relative_to(implementation)) for root in contract["source_layout"]["generic_core_roots"]]


def collect_generic_files(
    contract: dict[str, Any], implementation_root: Path, *, require_core: bool,
    source_only: bool = True,
) -> list[tuple[str, Path]]:
    files: dict[str, Path] = {}
    for relative_root in generic_relative_roots(contract):
        root = implementation_root / relative_root
        if not root.exists():
            continue
        if not root.is_dir():
            fail(f"generic core root is not a directory: {root}")
        for path in root.rglob("*"):
            if path.is_file() and (not source_only or is_source_file(path)):
                relative = path.relative_to(implementation_root).as_posix()
                if relative in files:
                    fail(f"duplicate generic-core relative path: {relative}")
                files[relative] = path
    ordered = sorted(files.items())
    if require_core and not ordered:
        fail(f"no generic core source files under {implementation_root}")
    return ordered


def forbidden_violations(
    files: list[tuple[str, Path]], forbidden_literals: list[str], prefix: str
) -> list[str]:
    forbidden = [(literal, literal.casefold()) for literal in forbidden_literals]
    violations: list[str] = []
    for relative, path in files:
        folded = path.read_text(encoding="utf-8", errors="replace").casefold()
        for literal, needle in forbidden:
            if needle in folded:
                violations.append(f"{prefix}{relative}: forbidden literal {literal!r}")
    return violations


def canonical_generic_core_sha256(
    contract: dict[str, Any], implementation_root: Path
) -> tuple[str, int, list[str]]:
    # The identity covers every file in the generic roots; the literal scan is
    # intentionally limited to source/configuration formats plus the final
    # analyzer binary (checked separately).
    files = collect_generic_files(
        contract, implementation_root, require_core=True, source_only=False
    )
    digest = hashlib.sha256()
    for relative, path in files:
        relative_bytes = relative.encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    source_files = [(relative, path) for relative, path in files if is_source_file(path)]
    violations = forbidden_violations(source_files, contract["core_forbidden_literals"], "")
    return digest.hexdigest(), len(files), violations


def scan_generic_core(contract: dict[str, Any], require_core: bool) -> tuple[int, list[str]]:
    implementation_root = WORKSPACE / contract["source_layout"]["implementation_root"]
    files = collect_generic_files(contract, implementation_root, require_core=require_core)
    return len(files), forbidden_violations(files, contract["core_forbidden_literals"], "")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        fail(f"artifact directory has no files: {path}")
    digest = hashlib.sha256()
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        payload = item.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def resolve_path(value: Any, field: str, evidence_directory: Path, *, directory: bool = False) -> Path:
    raw = require_string(value, field)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = evidence_directory / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        fail(f"{field} does not exist: {candidate}")
    if directory and not resolved.is_dir():
        fail(f"{field} is not a directory: {resolved}")
    if not directory and not resolved.is_file():
        fail(f"{field} is not a regular file: {resolved}")
    return resolved


def resolve_file_or_directory(value: Any, field: str, evidence_directory: Path) -> Path:
    raw = require_string(value, field)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = evidence_directory / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        fail(f"{field} does not exist: {candidate}")
    if not resolved.is_file() and not resolved.is_dir():
        fail(f"{field} is neither a regular file nor a directory: {resolved}")
    return resolved


def verify_file_artifact(
    container: dict[str, Any], path_field: str, hash_field: str, prefix: str,
    evidence_directory: Path,
) -> tuple[Path, str]:
    path = resolve_path(container.get(path_field), f"{prefix}.{path_field}", evidence_directory)
    reported = require_sha256(container.get(hash_field), f"{prefix}.{hash_field}")
    actual = sha256_file(path)
    if reported != actual:
        fail(f"{prefix}.{hash_field} mismatch: reported {reported}, actual {actual}")
    return path, actual


def scan_binary(path: Path, forbidden_literals: list[str], prefix: str) -> list[str]:
    payload = path.read_bytes().lower()
    return [
        f"{prefix}: final analyzer binary contains forbidden literal {literal!r}"
        for literal in forbidden_literals
        if literal.encode("utf-8").lower() in payload
    ]


def validate_compile_database(path: Path, prefix: str) -> None:
    database = load_json(path)
    if not isinstance(database, list) or not database:
        fail(f"{prefix} must contain a non-empty JSON list")
    for index, entry in enumerate(database):
        record = require_object(entry, f"{prefix}[{index}]")
        require_string(record.get("directory"), f"{prefix}[{index}].directory")
        require_string(record.get("file"), f"{prefix}[{index}].file")
        command = record.get("command")
        arguments = record.get("arguments")
        valid_command = isinstance(command, str) and bool(command)
        valid_arguments = isinstance(arguments, list) and bool(arguments) and all(
            isinstance(item, str) and item for item in arguments
        )
        if not valid_command and not valid_arguments:
            fail(f"{prefix}[{index}] needs a non-empty command string or argument string list")


PORTABILITY_EVIDENCE_VERSION = "3.0.0"
SEALED_RUN_VERSION = "3.0.0"
ALLOWED_ANALYSIS_STATUS = {"COMPLETE", "CONSERVATIVE_INCOMPLETE"}
REQUIRED_OUTPUTS = {
    "semantic_index": "semantic_index.json",
    "ap_bindings": "ap_bindings.json",
    "contextual_influence_graph": "contextual_influence_graph.json",
    "ap_influence_cones": "ap_influence_cones.json",
}
REQUIRED_SCHEMA_FILES = {
    "common.schema.json", "typed_property_ir.schema.json",
    "model_pack.schema.json", "semantic_index.schema.json",
    "ap_bindings.schema.json", "contextual_influence_graph.schema.json",
    "ap_influence_cones.schema.json", "analysis_certificate.schema.json",
}
EXPECTED_SCHEMA_IDS = {
    "common.schema.json": "https://tafuzz.dev/rift/schema/common/1.0.0",
    "typed_property_ir.schema.json": "https://tafuzz.dev/rift/schema/typed-property-ir/1.0.0",
    "model_pack.schema.json": "https://tafuzz.dev/rift/schema/model-pack/1.0.0",
    "semantic_index.schema.json": "https://tafuzz.dev/rift/schema/semantic-index/2.0.0",
    "ap_bindings.schema.json": "https://tafuzz.dev/rift/schema/ap-bindings/1.0.0",
    "contextual_influence_graph.schema.json": "https://tafuzz.dev/rift/schema/contextual-influence-graph/2.0.0",
    "ap_influence_cones.schema.json": "https://tafuzz.dev/rift/schema/ap-influence-cones/1.0.0",
    "analysis_certificate.schema.json": "https://tafuzz.dev/rift/schema/analysis-certificate/2.0.0",
}
REQUIRED_TOOLCHAIN_ROLES = {
    "analyzer", "clang", "opt", "llvm", "libclang", "svf_core",
    "svf_llvm", "svf_extapi", "z3",
}
RUNTIME_TOOLCHAIN_ROLES = {
    "analyzer", "llvm", "libclang", "svf_core", "svf_llvm", "z3",
}
MODEL_LEAKAGE_TOKENS = {
    "per_property_slice", "hand_selected_dependency_path",
    "expected_answer_edge", "benchmark_case_id_branch", "property_id",
    "target_property", "target_ap", "expected_influencer", "gold_answer",
    "oracle_answer", "dependency_path", "influence_path",
}


def verify_artifact_ref(
    value: Any, prefix: str, base: Path, *, directory: bool = False,
) -> tuple[Path, str]:
    record = require_object(value, prefix)
    path = resolve_path(record.get("path"), f"{prefix}.path", base, directory=directory)
    reported = require_sha256(record.get("sha256"), f"{prefix}.sha256")
    actual = sha256_tree(path) if directory else sha256_file(path)
    if actual != reported:
        fail(f"{prefix}.sha256 mismatch: reported {reported}, actual {actual}")
    return path, actual


def non_comment_lines(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "//")):
            count += 1
    return count


def recursively_scan_model(value: Any, prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            folded = str(key).casefold()
            if folded in MODEL_LEAKAGE_TOKENS:
                fail(f"{prefix} contains forbidden per-property answer key {key!r}")
            recursively_scan_model(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            recursively_scan_model(child, f"{prefix}[{index}]")
    elif (isinstance(value, str) and value.casefold() in MODEL_LEAKAGE_TOKENS
          and ".rule_policy.forbidden_rule_classes[" not in prefix):
        fail(f"{prefix} contains forbidden per-property answer token {value!r}")


def validate_model_pack(
    path: Path, record: dict[str, Any], contract: dict[str, Any], prefix: str,
) -> None:
    if path.is_dir():
        fail(f"{prefix} must reference one versioned model-pack JSON file")
    model = require_object(load_json(path), prefix)
    require_string(model.get("schema_version"), f"{prefix}.schema_version")
    require_string(model.get("model_pack_id"), f"{prefix}.model_pack_id")
    version = require_string(model.get("model_pack_version"), f"{prefix}.model_pack_version")
    if re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)([-+][0-9A-Za-z.-]+)?", version) is None:
        fail(f"{prefix}.model_pack_version must be semantic-versioned")
    if model.get("property_independent") is not True:
        fail(f"{prefix}.property_independent must be true")
    policy = require_object(model.get("rule_policy"), f"{prefix}.rule_policy")
    if policy.get("contract_id") != contract["contract_id"]:
        fail(f"{prefix}.rule_policy.contract_id mismatch")
    allowed = set(contract["model_pack_rules"]["allowed_rule_classes"])
    forbidden = set(contract["model_pack_rules"]["forbidden_rule_classes"])
    if not forbidden.issubset(set(require_unique_strings(
        policy.get("forbidden_rule_classes"), f"{prefix}.rule_policy.forbidden_rule_classes"
    ))):
        fail(f"{prefix} does not preserve all forbidden model rule classes")
    rules = model.get("rules")
    if not isinstance(rules, list):
        fail(f"{prefix}.rules must be an array")
    for index, value in enumerate(rules):
        rule = require_object(value, f"{prefix}.rules[{index}]")
        rule_class = require_string(rule.get("rule_class"), f"{prefix}.rules[{index}].rule_class")
        if rule_class in forbidden or rule_class not in allowed:
            fail(f"{prefix}.rules[{index}] uses forbidden/unknown rule class {rule_class!r}")
    recursively_scan_model(model, prefix)
    reported_lines = require_number(
        record.get("non_comment_lines"), f"{prefix}.non_comment_lines", integer=True
    )
    actual_lines = non_comment_lines(path)
    if reported_lines != actual_lines:
        fail(f"{prefix}.non_comment_lines mismatch: reported {reported_lines}, actual {actual_lines}")


def validate_schema_bundle(path: Path, prefix: str) -> None:
    present = {item.name for item in path.iterdir() if item.is_file()}
    missing = REQUIRED_SCHEMA_FILES - present
    if missing:
        fail(f"{prefix} is not a complete schema bundle; missing {sorted(missing)}")
    ids: set[str] = set()
    for item in sorted(path.rglob("*.schema.json")):
        schema = require_object(load_json(item), f"{prefix}/{item.relative_to(path)}")
        schema_id = require_string(schema.get("$id"), f"{prefix}/{item.name}.$id")
        expected_id = EXPECTED_SCHEMA_IDS.get(item.name)
        if expected_id is not None and schema_id != expected_id:
            fail(f"{prefix}/{item.name} has unexpected $id {schema_id!r}")
        if schema_id in ids:
            fail(f"{prefix} has duplicate schema $id {schema_id!r}")
        ids.add(schema_id)


def canonical_toolchain_semantics(
    toolchain: dict[str, Any], prefix: str, base: Path,
) -> tuple[str, list[dict[str, Any]]]:
    configuration = sorted(require_unique_strings(
        toolchain.get("semantic_configuration"), f"{prefix}.semantic_configuration"
    ))
    values = toolchain.get("components")
    if not isinstance(values, list) or not values:
        fail(f"{prefix}.components must be a non-empty array")
    components: list[dict[str, Any]] = []
    roles: set[str] = set()
    for index, value in enumerate(values):
        item_prefix = f"{prefix}.components[{index}]"
        record = require_object(value, item_prefix)
        path, digest = verify_artifact_ref(record, item_prefix, base)
        role = require_string(record.get("role"), f"{item_prefix}.role")
        name = require_string(record.get("logical_name"), f"{item_prefix}.logical_name")
        version = require_string(record.get("version"), f"{item_prefix}.version")
        runtime_attested = record.get("runtime_attested")
        if type(runtime_attested) is not bool:
            fail(f"{item_prefix}.runtime_attested must be boolean")
        if role in roles:
            fail(f"{prefix}.components has duplicate role {role!r}")
        roles.add(role)
        components.append({
            "role": role, "logical_name": name, "version": version,
            "sha256": digest, "runtime_attested": runtime_attested,
        })
        del path
    missing = REQUIRED_TOOLCHAIN_ROLES - roles
    if missing:
        fail(f"{prefix} is incomplete; missing toolchain roles {sorted(missing)}")
    by_role = {item["role"]: item for item in components}
    if "18" not in by_role["clang"]["version"] or "18" not in by_role["opt"]["version"]:
        fail(f"{prefix} must record Clang/LLVM 18 semantics")
    descriptor = {
        "semantic_configuration": configuration,
        "components": sorted(components, key=lambda item: item["role"]),
    }
    digest = hashlib.sha256(json.dumps(
        descriptor, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    reported = require_sha256(toolchain.get("semantics_sha256"), f"{prefix}.semantics_sha256")
    if digest != reported:
        fail(f"{prefix}.semantics_sha256 mismatch: reported {reported}, actual {digest}")
    return digest, components


def manifest_tree_digest(
    root: Path, values: Any, prefix: str, *, strip_prefix: str | None = None,
) -> str:
    if not isinstance(values, list) or not values:
        fail(f"{prefix} must be a non-empty build-manifest file list")
    digest = hashlib.sha256()
    seen: set[str] = set()
    ordered: list[str] = []
    for index, value in enumerate(values):
        record = require_object(value, f"{prefix}[{index}]")
        relative = require_string(record.get("path"), f"{prefix}[{index}].path")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or relative in seen:
            fail(f"{prefix}[{index}].path is unsafe or duplicated")
        seen.add(relative)
        ordered.append(relative)
        disk_relative = relative
        if strip_prefix is not None:
            expected = strip_prefix.rstrip("/") + "/"
            if not relative.startswith(expected):
                fail(f"{prefix}[{index}].path is outside {strip_prefix}")
            disk_relative = relative[len(expected):]
        path = (root / Path(disk_relative)).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            fail(f"{prefix}[{index}].path escapes its artifact root")
        if not path.is_file():
            fail(f"{prefix}[{index}] does not exist in the verified tree: {path}")
        payload = path.read_bytes()
        actual_file = hashlib.sha256(payload).hexdigest()
        reported_file = require_sha256(record.get("sha256"), f"{prefix}[{index}].sha256")
        if actual_file != reported_file:
            fail(f"{prefix}[{index}].sha256 mismatch")
        relative_bytes = relative.encode("utf-8")
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    if ordered != sorted(ordered):
        fail(f"{prefix} must be in canonical path order")
    return digest.hexdigest()


def validate_build_manifest(
    path: Path, actual_core: Path, prefix: str,
) -> tuple[dict[str, Any], str, str]:
    build = require_object(load_json(path), prefix)
    if build.get("schema_version") != "rift.build-manifest.v1":
        fail(f"{prefix} must be rift.build-manifest.v1")
    if build.get("identity_policy") != "relative-path-and-content-v1":
        fail(f"{prefix}.identity_policy mismatch")
    core_digest = manifest_tree_digest(
        actual_core, build.get("production_core_files"),
        f"{prefix}.production_core_files",
    )
    schema_digest = manifest_tree_digest(
        actual_core, build.get("schema_files"), f"{prefix}.schema_files"
    )
    if build.get("production_core_sha256") != core_digest:
        fail(f"{prefix}.production_core_sha256 mismatch")
    if build.get("schema_bundle_sha256") != schema_digest:
        fail(f"{prefix}.schema_bundle_sha256 mismatch")
    return build, core_digest, schema_digest


def artifact_by_kind(
    values: Any, field: str, required_kinds: set[str], *, exact: bool,
) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        fail(f"{field} must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(values):
        record = require_object(value, f"{field}[{index}]")
        kind = require_string(record.get("kind"), f"{field}[{index}].kind")
        if kind in result:
            fail(f"{field} contains duplicate kind {kind!r}")
        require_sha256(record.get("sha256"), f"{field}[{index}].sha256")
        result[kind] = record
    missing = required_kinds - set(result)
    if missing:
        fail(f"{field} missing kinds {sorted(missing)}")
    if exact and set(result) != required_kinds:
        fail(f"{field} has unexpected kinds {sorted(set(result) - required_kinds)}")
    return result


def compute_input_manifest_digest(index: dict[str, Any], prefix: str) -> str:
    identity = require_string(index.get("identity_scheme"), f"{prefix}.identity_scheme")
    if identity != "rift.identity/2.0.0":
        fail(f"{prefix}.identity_scheme must be rift.identity/2.0.0")
    inputs = index.get("input_files")
    if not isinstance(inputs, list) or not inputs:
        fail(f"{prefix}.input_files must be non-empty")
    payload = bytearray(identity.encode("utf-8") + b"\0input-manifest/1.0.0")
    keys: list[tuple[str, str, str, int]] = []
    for item_index, value in enumerate(inputs):
        record = require_object(value, f"{prefix}.input_files[{item_index}]")
        logical = require_string(record.get("logical_path"), f"{prefix}.input_files[{item_index}].logical_path")
        role = require_string(record.get("role"), f"{prefix}.input_files[{item_index}].role")
        digest = require_sha256(record.get("sha256"), f"{prefix}.input_files[{item_index}].sha256")
        size = require_number(record.get("byte_size"), f"{prefix}.input_files[{item_index}].byte_size", integer=True)
        keys.append((logical, role, digest, int(size)))
    if keys != sorted(keys, key=lambda value: (value[0], value[1], value[2])):
        fail(f"{prefix}.input_files are not in canonical order")
    if len({item[0] for item in keys}) != len(keys):
        fail(f"{prefix}.input_files contains duplicate logical paths")
    for logical, role, digest, size in keys:
        logical_bytes = logical.encode("utf-8")
        payload.extend(b"\0" + role.encode("utf-8") + b"\0")
        payload.extend(str(len(logical_bytes)).encode("ascii") + b":" + logical_bytes)
        payload.extend(b"\0" + digest.encode("ascii") + b"\0" + str(size).encode("ascii"))
    return hashlib.sha256(payload).hexdigest()


def validate_source_input_closure(
    path: Path, index: dict[str, Any], source_root: Path, prefix: str,
) -> str:
    closure = require_object(load_json(path), prefix)
    if closure.get("schema_version") != "2.0.0" or closure.get("manifest_kind") != "rift.source-input-closure":
        fail(f"{prefix} must be a rift.source-input-closure v2 manifest")
    semantic_entries = index.get("input_files")
    entries = closure.get("entries")
    if not isinstance(entries, list) or len(entries) != len(semantic_entries):
        fail(f"{prefix}.entries must close every semantic-index input exactly once")
    semantic_by_path = {item["logical_path"]: item for item in semantic_entries}
    observed: set[str] = set()
    source_member = False
    for item_index, value in enumerate(entries):
        item_prefix = f"{prefix}.entries[{item_index}]"
        record = require_object(value, item_prefix)
        logical = require_string(record.get("logical_path"), f"{item_prefix}.logical_path")
        if logical in observed or logical not in semantic_by_path:
            fail(f"{item_prefix}.logical_path is duplicate or absent from semantic index")
        observed.add(logical)
        physical = resolve_path(record.get("physical_path"), f"{item_prefix}.physical_path", path.parent)
        digest = sha256_file(physical)
        size = physical.stat().st_size
        semantic = semantic_by_path[logical]
        if (record.get("input_file_id") != semantic.get("input_file_id") or
                record.get("role") != semantic.get("role") or
                record.get("sha256") != digest or
                record.get("byte_size") != size or
                digest != semantic.get("sha256") or
                size != semantic.get("byte_size")):
            fail(f"{item_prefix} does not match semantic-index role/hash/size")
        try:
            physical.relative_to(source_root)
            source_member = True
        except ValueError:
            pass
    if not source_member:
        fail(f"{prefix} has no physical input inside the declared source snapshot")
    digest = compute_input_manifest_digest(index, f"{prefix}.semantic_index")
    reported = require_sha256(closure.get("input_manifest_sha256"), f"{prefix}.input_manifest_sha256")
    if digest != reported or digest != index.get("input_manifest_sha256"):
        fail(f"{prefix}.input_manifest_sha256 does not close the semantic index")
    return digest


def validate_output_shapes(
    index: dict[str, Any], bindings: dict[str, Any], graph: dict[str, Any],
    cones: dict[str, Any], prefix: str,
) -> None:
    for name, artifact in (
        ("semantic_index", index), ("ap_bindings", bindings),
        ("contextual_influence_graph", graph), ("ap_influence_cones", cones),
    ):
        require_string(artifact.get("schema_version"), f"{prefix}.{name}.schema_version")
        require_string(artifact.get("artifact_id"), f"{prefix}.{name}.artifact_id")
    for field, artifact in (
        ("translation_units", index), ("semantic_nodes", index),
        ("bindings", bindings), ("nodes", graph), ("cones", cones),
    ):
        if not isinstance(artifact.get(field), list) or not artifact[field]:
            fail(f"{prefix}.{field} must be non-empty; empty placeholder outputs are not evidence")
    def reject_failed_status(value: Any, field: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if (key in {"status", "analysis_status", "resolution"}
                        and isinstance(child, str)
                        and child.upper() in {"FAILED", "UNSUPPORTED", "NOT_RUN"}):
                    fail(f"{field}.{key} contains disallowed status {child!r}")
                reject_failed_status(child, f"{field}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                reject_failed_status(child, f"{field}[{index}]")
    for name, artifact in (
        ("semantic_index", index), ("ap_bindings", bindings),
        ("contextual_influence_graph", graph), ("ap_influence_cones", cones),
    ):
        reject_failed_status(artifact, f"{prefix}.{name}")


def validate_certificate(
    certificate: dict[str, Any], paths: dict[str, Path], digests: dict[str, str],
    property_digest: str, compile_digest: str,
    source_inputs_digest: str, binary_digest: str, core_digest: str,
    schema_digest: str, build_manifest_digest: str,
    toolchain_components: list[dict[str, Any]], analysis_status: str,
    closure: dict[str, Any], prefix: str,
) -> None:
    if certificate.get("schema_version") != "2.0.0":
        fail(f"{prefix}.schema_version must be the artifact-backed analysis-certificate 2.0.0; v1 is rejected")
    status = require_string(certificate.get("status"), f"{prefix}.status")
    if status not in ALLOWED_ANALYSIS_STATUS or status != analysis_status:
        fail(f"{prefix}.status must match successful run status COMPLETE/CONSERVATIVE_INCOMPLETE")
    analyzer = require_object(certificate.get("analyzer"), f"{prefix}.analyzer")
    if analyzer.get("binary_sha256") != binary_digest:
        fail(f"{prefix}.analyzer.binary_sha256 does not bind the actual analyzer")
    if certificate.get("core_tree_sha256") != core_digest:
        fail(f"{prefix}.core_tree_sha256 does not bind the verified core tree")
    if certificate.get("schema_bundle_sha256") != schema_digest:
        fail(f"{prefix}.schema_bundle_sha256 does not bind the complete schema tree")
    require_sha256(analyzer.get("configuration_sha256"), f"{prefix}.analyzer.configuration_sha256")
    environment_digest = require_sha256(
        analyzer.get("environment_sha256"), f"{prefix}.analyzer.environment_sha256"
    )
    environment = require_object(certificate.get("environment"), f"{prefix}.environment")
    if environment.get("digest") != environment_digest:
        fail(f"{prefix}.environment.digest does not match analyzer.environment_sha256")
    expected_environment_names = {
        "CL", "COMPILER_PATH", "CPATH", "CPLUS_INCLUDE_PATH", "C_INCLUDE_PATH",
        "GCC_EXEC_PREFIX", "INCLUDE", "LANG", "LC_ALL", "LC_CTYPE",
        "MACOSX_DEPLOYMENT_TARGET", "OBJC_INCLUDE_PATH", "PATH", "SDKROOT",
        "SOURCE_DATE_EPOCH", "_CL_",
    }
    variables = environment.get("variables")
    if not isinstance(variables, list) or len(variables) != len(expected_environment_names):
        fail(f"{prefix}.environment.variables must cover the 16 analysis-relevant variables")
    names: set[str] = set()
    for index, value in enumerate(variables):
        variable = require_object(value, f"{prefix}.environment.variables[{index}]")
        name = require_string(variable.get("name"), f"{prefix}.environment.variables[{index}].name")
        if name in names:
            fail(f"{prefix}.environment.variables contains duplicate {name!r}")
        names.add(name)
        if type(variable.get("present")) is not bool:
            fail(f"{prefix}.environment.variables[{index}].present must be boolean")
        value_digest = variable.get("value_sha256")
        if variable["present"]:
            require_sha256(value_digest, f"{prefix}.environment.variables[{index}].value_sha256")
        elif value_digest is not None:
            fail(f"{prefix}.environment.variables[{index}].value_sha256 must be null when absent")
    if names != expected_environment_names:
        fail(f"{prefix}.environment.variables has incomplete names")
    embedded_build = require_object(certificate.get("build_manifest"), f"{prefix}.build_manifest")
    expected_build = {
        "identity_policy": "relative-path-and-content-v1",
        "manifest_sha256": build_manifest_digest,
        "production_core_sha256": core_digest,
        "schema_bundle_sha256": schema_digest,
    }
    for field, expected in expected_build.items():
        if embedded_build.get(field) != expected:
            fail(f"{prefix}.build_manifest.{field} mismatch")

    inputs = artifact_by_kind(
        certificate.get("inputs"), f"{prefix}.inputs",
        {"typed_property_ir", "compile_commands", "source_inputs"}, exact=True,
    )
    expected_inputs = {
        "typed_property_ir": property_digest, "compile_commands": compile_digest,
        "source_inputs": source_inputs_digest,
    }
    for kind, expected in expected_inputs.items():
        if inputs[kind].get("sha256") != expected:
            fail(f"{prefix}.inputs[{kind}] digest mismatch")

    outputs = artifact_by_kind(
        certificate.get("outputs"), f"{prefix}.outputs", set(REQUIRED_OUTPUTS), exact=True
    )
    for kind, digest in digests.items():
        if outputs[kind].get("sha256") != digest:
            fail(f"{prefix}.outputs[{kind}] digest mismatch")
        artifact = require_object(load_json(paths[kind]), f"{prefix}.{kind}")
        if outputs[kind].get("artifact_id") != artifact.get("artifact_id"):
            fail(f"{prefix}.outputs[{kind}].artifact_id mismatch")

    runtime = certificate.get("toolchain")
    if not isinstance(runtime, list) or not runtime:
        fail(f"{prefix}.toolchain must be non-empty")
    runtime_hashes: set[str] = set()
    for index, value in enumerate(runtime):
        component = require_object(value, f"{prefix}.toolchain[{index}]")
        runtime_hashes.add(require_sha256(
            component.get("sha256"), f"{prefix}.toolchain[{index}].sha256"
        ))
        require_string(component.get("name"), f"{prefix}.toolchain[{index}].name")
        require_string(component.get("version"), f"{prefix}.toolchain[{index}].version")
    declared_runtime = {
        item["sha256"] for item in toolchain_components if item["runtime_attested"]
    }
    required_runtime = {
        item["sha256"] for item in toolchain_components
        if item["role"] in RUNTIME_TOOLCHAIN_ROLES
    }
    if not required_runtime.issubset(declared_runtime):
        fail(f"{prefix} required analyzer libraries are not marked runtime-attested")
    if declared_runtime != runtime_hashes:
        fail(
            f"{prefix}.toolchain and sealed toolchain manifest differ; "
            "all runtime components must be artifact-backed"
        )

    provenance = require_object(
        certificate.get("source_input_provenance"),
        f"{prefix}.source_input_provenance",
    )
    if provenance.get("manifest_sha256") != source_inputs_digest:
        fail(f"{prefix}.source_input_provenance.manifest_sha256 mismatch")
    provenance_files = provenance.get("files")
    closure_entries = closure.get("entries")
    if not isinstance(provenance_files, list) or not isinstance(closure_entries, list):
        fail(f"{prefix}.source_input_provenance.files must be an array")
    provenance_by_path: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(provenance_files):
        item = require_object(value, f"{prefix}.source_input_provenance.files[{index}]")
        logical = require_string(item.get("logical_path"), f"{prefix}.source_input_provenance.files[{index}].logical_path")
        if logical in provenance_by_path:
            fail(f"{prefix}.source_input_provenance has duplicate logical path")
        provenance_by_path[logical] = item
    if set(provenance_by_path) != {item["logical_path"] for item in closure_entries}:
        fail(f"{prefix}.source_input_provenance does not close the v2 input manifest")
    for item in closure_entries:
        provenance_item = provenance_by_path[item["logical_path"]]
        physical = str(Path(item["physical_path"]).resolve())
        expected = {
            "logical_path": item["logical_path"], "role": item["role"],
            "sha256": item["sha256"], "byte_size": item["byte_size"],
        }
        for field, value in expected.items():
            if provenance_item.get(field) != value:
                fail(f"{prefix}.source_input_provenance {field} mismatch")
        observed = provenance_item.get("observed_paths")
        if not isinstance(observed, list) or physical not in {str(Path(path).resolve()) for path in observed}:
            fail(f"{prefix}.source_input_provenance omits observed physical path")

    stages_value = certificate.get("stages")
    if not isinstance(stages_value, list):
        fail(f"{prefix}.stages must be an array")
    stages: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(stages_value):
        stage = require_object(value, f"{prefix}.stages[{index}]")
        name = require_string(stage.get("name"), f"{prefix}.stages[{index}].name")
        if name in stages:
            fail(f"{prefix}.stages contains duplicate stage {name!r}")
        stage_status = require_string(stage.get("status"), f"{prefix}.stages[{index}].status")
        if stage_status not in ALLOWED_ANALYSIS_STATUS:
            fail(f"{prefix}.stages[{index}] is FAILED, NOT_RUN, or UNSUPPORTED")
        stages[name] = stage
    expected_stages = {
        "index": ({compile_digest, source_inputs_digest}, {digests["semantic_index"]}),
        "bind": ({property_digest, digests["semantic_index"]}, {digests["ap_bindings"]}),
        "influence": ({digests["semantic_index"], digests["ap_bindings"]}, {digests["contextual_influence_graph"]}),
        "cone": ({digests["ap_bindings"], digests["contextual_influence_graph"]}, {digests["ap_influence_cones"]}),
        "certificate": (set(digests.values()), set()),
    }
    if set(stages) != set(expected_stages):
        fail(f"{prefix}.stages must contain exactly {sorted(expected_stages)}")
    for name, (expected_in, expected_out) in expected_stages.items():
        stage = stages[name]
        actual_in = set(require_unique_strings(stage.get("input_sha256"), f"{prefix}.stages[{name}].input_sha256", allow_empty=True))
        actual_out = set(require_unique_strings(stage.get("output_sha256"), f"{prefix}.stages[{name}].output_sha256", allow_empty=True))
        if actual_in != expected_in or actual_out != expected_out:
            fail(f"{prefix}.stages[{name}] does not close the artifact hash chain")
    aggregate = "COMPLETE" if all(stage["status"] == "COMPLETE" for stage in stages.values()) else "CONSERVATIVE_INCOMPLETE"
    if status != aggregate:
        fail(f"{prefix}.status does not equal aggregate stage status {aggregate}")


def validate_sealed_run(
    contract: dict[str, Any], manifest_path: Path, manifest: dict[str, Any],
    actual_core: Path, project_index: int,
) -> dict[str, str]:
    prefix = f"project[{project_index}].sealed_run"
    if manifest.get("schema_version") != SEALED_RUN_VERSION:
        fail(f"{prefix} must use sealed-run schema {SEALED_RUN_VERSION}; v1/v2 reports are not evidence")
    if manifest.get("manifest_kind") != "rift.sealed-portability-run":
        fail(f"{prefix}.manifest_kind mismatch")
    require_string(manifest.get("run_id"), f"{prefix}.run_id")
    base = manifest_path.parent
    project = require_object(manifest.get("project"), f"{prefix}.project")
    execution = require_object(manifest.get("execution"), f"{prefix}.execution")
    artifacts = require_object(manifest.get("artifacts"), f"{prefix}.artifacts")
    embedded = require_object(manifest.get("embedded_identities"), f"{prefix}.embedded_identities")

    project_id = require_string(project.get("project_id"), f"{prefix}.project.project_id")
    repository_id = require_string(project.get("repository_id"), f"{prefix}.project.repository_id")
    source_revision = require_string(project.get("source_revision"), f"{prefix}.project.source_revision")
    source_root, source_tree_digest = verify_artifact_ref(
        project.get("source_snapshot"), f"{prefix}.project.source_snapshot", base, directory=True
    )
    repository_manifest_path, _ = verify_artifact_ref(
        project.get("source_repository_manifest"),
        f"{prefix}.project.source_repository_manifest", base,
    )
    repository_manifest = require_object(
        load_json(repository_manifest_path), f"{prefix}.project.source_repository_manifest"
    )
    if repository_manifest.get("schema_version") != "1.0.0":
        fail(f"{prefix}.project.source_repository_manifest must use schema 1.0.0")
    if (repository_manifest.get("repository_id") != repository_id or
            repository_manifest.get("source_revision") != source_revision or
            repository_manifest.get("source_tree_sha256") != source_tree_digest):
        fail(f"{prefix}.project.source_repository_manifest identity/tree mismatch")

    property_path, property_digest = verify_artifact_ref(
        project.get("typed_property_ir"), f"{prefix}.project.typed_property_ir", base
    )
    property_ir = require_object(load_json(property_path), f"{prefix}.project.typed_property_ir")
    if property_ir.get("schema_version") != "1.0.0":
        fail(f"{prefix}.project.typed_property_ir must use schema 1.0.0")
    require_string(property_ir.get("artifact_id"), f"{prefix}.project.typed_property_ir.artifact_id")

    compile_path, compile_digest = verify_artifact_ref(
        project.get("compile_database"), f"{prefix}.project.compile_database", base
    )
    validate_compile_database(compile_path, f"{prefix}.project.compile_database")

    model_record = require_object(project.get("model_pack"), f"{prefix}.project.model_pack")
    model_path, model_digest = verify_artifact_ref(
        model_record, f"{prefix}.project.model_pack", base
    )
    validate_model_pack(model_path, model_record, contract, f"{prefix}.project.model_pack")
    require_number(project.get("setup_minutes"), f"{prefix}.project.setup_minutes")
    require_unique_strings(
        project.get("unsupported_constructs"),
        f"{prefix}.project.unsupported_constructs", allow_empty=True,
    )

    if execution.get("exit_code") != 0:
        fail(f"{prefix}.execution.exit_code must be zero")
    analysis_status = require_string(execution.get("analysis_status"), f"{prefix}.execution.analysis_status")
    if analysis_status not in ALLOWED_ANALYSIS_STATUS:
        fail(f"{prefix}.execution.analysis_status cannot be v1 PASS, UNSUPPORTED, or FAILED")
    require_number(execution.get("wall_seconds"), f"{prefix}.execution.wall_seconds")
    require_number(execution.get("peak_rss_bytes"), f"{prefix}.execution.peak_rss_bytes", integer=True)

    binary_path, binary_digest = verify_artifact_ref(
        execution.get("analyzer_binary"), f"{prefix}.execution.analyzer_binary", base
    )
    violations = scan_binary(binary_path, contract["core_forbidden_literals"], f"{prefix}.analyzer_binary")
    if violations:
        fail("generic-core portability violations:\n" + "\n".join(violations))
    build_path, build_digest = verify_artifact_ref(
        execution.get("build_manifest"), f"{prefix}.execution.build_manifest", base
    )
    build, core_digest, schema_digest = validate_build_manifest(
        build_path, actual_core, f"{prefix}.execution.build_manifest"
    )
    schema_record = require_object(
        execution.get("schema_bundle"), f"{prefix}.execution.schema_bundle"
    )
    schema_path = resolve_path(
        schema_record.get("path"), f"{prefix}.execution.schema_bundle.path",
        base, directory=True,
    )
    reported_schema = require_sha256(
        schema_record.get("sha256"), f"{prefix}.execution.schema_bundle.sha256"
    )
    schema_from_bundle = manifest_tree_digest(
        schema_path, build.get("schema_files"),
        f"{prefix}.execution.schema_bundle.files", strip_prefix="schema",
    )
    if reported_schema != schema_digest or schema_from_bundle != schema_digest:
        fail(f"{prefix}.execution.schema_bundle does not match the embedded complete schema tree")
    validate_schema_bundle(schema_path, f"{prefix}.execution.schema_bundle")

    before_record = require_object(execution.get("core_before"), f"{prefix}.execution.core_before")
    after_record = require_object(execution.get("core_after"), f"{prefix}.execution.core_after")
    before_path = resolve_path(
        before_record.get("path"), f"{prefix}.execution.core_before.path", base, directory=True
    )
    after_path = resolve_path(
        after_record.get("path"), f"{prefix}.execution.core_after.path", base, directory=True
    )
    if before_path == after_path:
        fail(f"{prefix} must record distinct before/after core snapshots")
    before_digest = manifest_tree_digest(
        before_path, build.get("production_core_files"),
        f"{prefix}.execution.core_before.files",
    )
    after_digest = manifest_tree_digest(
        after_path, build.get("production_core_files"),
        f"{prefix}.execution.core_after.files",
    )
    before_reported = require_sha256(before_record.get("sha256"), f"{prefix}.execution.core_before.sha256")
    after_reported = require_sha256(after_record.get("sha256"), f"{prefix}.execution.core_after.sha256")
    if before_digest != before_reported or after_digest != after_reported:
        fail(f"{prefix} core snapshot uses the wrong production-core digest")
    if before_digest != after_digest or before_digest != core_digest:
        fail(f"{prefix} core tree changed before/after the run or differs from the actual core")

    toolchain_digest, toolchain_components = canonical_toolchain_semantics(
        require_object(manifest.get("toolchain"), f"{prefix}.toolchain"),
        f"{prefix}.toolchain", base,
    )
    analyzer_component = next(
        item for item in toolchain_components if item["role"] == "analyzer"
    )
    if analyzer_component["sha256"] != binary_digest:
        fail(f"{prefix}.toolchain analyzer role does not match the executed binary")
    expected_embedded = {
        "analyzer_binary_sha256": binary_digest,
        "build_manifest_sha256": build_digest,
        "core_tree_sha256": core_digest,
        "schema_bundle_sha256": schema_digest,
        "toolchain_semantics_sha256": toolchain_digest,
    }
    for field, expected in expected_embedded.items():
        if require_sha256(embedded.get(field), f"{prefix}.embedded_identities.{field}") != expected:
            fail(f"{prefix}.embedded_identities.{field} mismatch")

    output_paths: dict[str, Path] = {}
    output_digests: dict[str, str] = {}
    output_json: dict[str, dict[str, Any]] = {}
    for kind in REQUIRED_OUTPUTS:
        path, digest = verify_artifact_ref(
            artifacts.get(kind), f"{prefix}.artifacts.{kind}", base
        )
        output_paths[kind] = path
        output_digests[kind] = digest
        output_json[kind] = require_object(load_json(path), f"{prefix}.artifacts.{kind}")
    validate_output_shapes(
        output_json["semantic_index"], output_json["ap_bindings"],
        output_json["contextual_influence_graph"], output_json["ap_influence_cones"],
        f"{prefix}.artifacts",
    )
    index = output_json["semantic_index"]
    bindings = output_json["ap_bindings"]
    graph = output_json["contextual_influence_graph"]
    cones = output_json["ap_influence_cones"]
    if bindings.get("property_ir_sha256") != property_digest or bindings.get("semantic_index_sha256") != output_digests["semantic_index"]:
        fail(f"{prefix}.artifacts.ap_bindings breaks the property/index hash chain")
    if graph.get("semantic_index_sha256") != output_digests["semantic_index"]:
        fail(f"{prefix}.artifacts.contextual_influence_graph breaks the index hash chain")
    if (cones.get("ap_bindings_sha256") != output_digests["ap_bindings"] or
            cones.get("graph_sha256") != output_digests["contextual_influence_graph"]):
        fail(f"{prefix}.artifacts.ap_influence_cones breaks the binding/graph hash chain")
    for artifact_name in ("semantic_index", "contextual_influence_graph"):
        status = output_json[artifact_name].get("status")
        if status not in ALLOWED_ANALYSIS_STATUS:
            fail(f"{prefix}.artifacts.{artifact_name}.status is FAILED/UNSUPPORTED")
    if any(item.get("status") not in ALLOWED_ANALYSIS_STATUS for item in cones["cones"]):
        fail(f"{prefix}.artifacts.ap_influence_cones contains FAILED/UNSUPPORTED cone")

    closure_path, _ = verify_artifact_ref(
        artifacts.get("source_input_manifest"),
        f"{prefix}.artifacts.source_input_manifest", base,
    )
    closure = require_object(
        load_json(closure_path), f"{prefix}.artifacts.source_input_manifest"
    )
    source_inputs_digest = validate_source_input_closure(
        closure_path, index, source_root, f"{prefix}.artifacts.source_input_manifest"
    )

    certificate_path, _ = verify_artifact_ref(
        artifacts.get("analysis_certificate"),
        f"{prefix}.artifacts.analysis_certificate", base,
    )
    certificate = require_object(load_json(certificate_path), f"{prefix}.artifacts.analysis_certificate")
    validate_certificate(
        certificate, output_paths, output_digests, property_digest,
        compile_digest, source_inputs_digest, binary_digest,
        core_digest, schema_digest, build_digest, toolchain_components,
        analysis_status, closure,
        f"{prefix}.artifacts.analysis_certificate",
    )
    return {
        "project_id": project_id, "repository_id": repository_id,
        "source_tree_sha256": source_tree_digest,
        "compile_database_sha256": compile_digest,
        "binary_sha256": binary_digest, "schema_sha256": schema_digest,
        "core_sha256": core_digest, "build_manifest_sha256": build_digest,
        "toolchain_semantics_sha256": toolchain_digest,
    }


def validate_evidence(contract: dict[str, Any], evidence_path: Path) -> int:
    evidence = require_object(load_json(evidence_path), "evidence")
    if evidence.get("schema_version") != PORTABILITY_EVIDENCE_VERSION:
        fail("evaluation evidence must use artifact-backed schema 3.0.0; handwritten v1/v2 PASS reports are rejected")
    if evidence.get("evidence_kind") != "rift.portability-evaluation":
        fail("evidence_kind must be rift.portability-evaluation")
    if evidence.get("contract_id") != contract["contract_id"]:
        fail("evidence contract_id mismatch")
    projects = evidence.get("projects")
    minimum = contract["evaluation_gate"]["minimum_independent_projects"]
    if not isinstance(projects, list) or len(projects) < minimum:
        fail(f"portability evidence needs at least {minimum} projects")
    evidence_directory = evidence_path.resolve().parent
    actual_core = resolve_path(
        evidence.get("actual_core_root_path"), "evidence.actual_core_root_path",
        evidence_directory, directory=True,
    )
    _, _, violations = canonical_generic_core_sha256(contract, actual_core)
    if violations:
        fail("actual generic core contains forbidden project literals:\n" + "\n".join(violations))

    summaries: list[dict[str, str]] = []
    sealed_hashes: set[str] = set()
    for index, value in enumerate(projects):
        prefix = f"project[{index}]"
        record = require_object(value, prefix)
        manifest_path, manifest_digest = verify_file_artifact(
            record, "sealed_run_manifest_path", "sealed_run_manifest_sha256",
            prefix, evidence_directory,
        )
        if manifest_digest in sealed_hashes:
            fail("sealed run manifests must be distinct artifacts")
        sealed_hashes.add(manifest_digest)
        manifest = require_object(load_json(manifest_path), f"{prefix}.sealed_run")
        summaries.append(validate_sealed_run(
            contract, manifest_path, manifest, actual_core, index
        ))

    for field in (
        "project_id", "repository_id", "source_tree_sha256",
        "compile_database_sha256",
    ):
        values = {summary[field] for summary in summaries}
        if len(values) != len(summaries):
            fail(f"projects are not independent: duplicate {field}")
    for field in (
        "binary_sha256", "schema_sha256", "core_sha256",
        "build_manifest_sha256", "toolchain_semantics_sha256",
    ):
        values = {summary[field] for summary in summaries}
        if len(values) != 1:
            fail(f"verified {field} differs across projects")
    return len(projects)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("pre-core", "implementation", "evaluation"), default="pre-core")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()

    contract = require_object(load_json(CONTRACT_PATH), "contract")
    validate_contract(contract)
    file_count, violations = scan_generic_core(contract, require_core=args.phase != "pre-core")
    if violations:
        fail("generic-core portability violations:\n" + "\n".join(violations))

    project_count = 0
    if args.phase == "evaluation":
        if args.evidence is None:
            fail("--evidence is required during evaluation")
        project_count = validate_evidence(contract, args.evidence)
    elif args.evidence is not None:
        fail("--evidence is only valid during evaluation")

    contract_sha = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
    print(
        "PASS",
        f"contract={contract['contract_id']}",
        f"phase={args.phase}",
        f"generic_core_files={file_count}",
        f"projects={project_count}",
        f"sha256={contract_sha}",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
