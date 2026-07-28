#!/usr/bin/env python3
"""Detached verifier for the RIFT M5 physical provenance certificate.

The verifier deliberately starts from files, not from digest fields embedded in
semantic artifacts.  It rehashes every physical path available from the M5
certificate and its referenced M4 certificate, validates the closed schemas,
and then reconstructs both certificate stage DAGs from independently observed
file digests.

Exit status is 0 only when every check passes, 1 for a verification failure and
2 for invocation/setup errors.  The JSON report is suitable for archiving as a
test receipt.
"""

from __future__ import annotations

import argparse
import collections
import copy
import datetime as dt
import hashlib
import json
import os
import pathlib
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import jsonschema


SCHEMA_VERSION = "1.0.0"
SOLVER_ENCODING_VERSION = "rift-local-truth-change/1.0.0"
SOLVER_BUDGET_DOMAIN = "rift-m5-solver-budget/1.0.0"
SOLVER_BUDGET_REGRESSION_SHA256 = (
    "498eb4bd64c378e5d6c2b22140f523f45aa4e427c3a96b8db08b6ea33bec37bc"
)
# Frozen output of the production C++ v2 canonicalizer for
# benchmark/rift/m5/model_packs/neutral_read_arg_v1.json.
MODEL_PACK_CPP_REGRESSION_SHA256 = (
    "e5c004b4baf0b9d45d6c732874ff0c69752cca477d259d2a423090e1213d3c7d"
)
STAGE_ORDER = (
    "model",
    "occurrence",
    "contextualize",
    "frontier",
    "recipe",
    "certificate",
)
M4_OUTPUT_ORDER = (
    "semantic_index",
    "ap_bindings",
    "contextual_influence_graph",
    "ap_influence_cones",
)
M5_OUTPUT_ORDER = (
    "model_fact_overlay",
    "predicate_occurrence_bindings",
    "frontier_candidates",
    "fuzzable_frontier",
    "mutation_recipes",
    "recipe_replay_obligations",
)
M5_OUTPUT_SCHEMAS = {
    "model_fact_overlay": "model_fact_overlay.schema.json",
    "predicate_occurrence_bindings": "predicate_occurrence_bindings.schema.json",
    "frontier_candidates": "frontier_candidates.schema.json",
    "fuzzable_frontier": "fuzzable_frontier.schema.json",
    "mutation_recipes": "mutation_recipes.schema.json",
    "recipe_replay_obligations": "recipe_replay_obligations.schema.json",
}
M4_ARTIFACT_SCHEMAS = {
    "typed_property_ir": "typed_property_ir.schema.json",
    "semantic_index": "semantic_index.schema.json",
    "ap_bindings": "ap_bindings.schema.json",
    "contextual_influence_graph": "contextual_influence_graph.schema.json",
    "ap_influence_cones": "ap_influence_cones.schema.json",
}
STATUS_RANK = {"COMPLETE": 0, "CONSERVATIVE_INCOMPLETE": 1, "FAILED": 2}
INTEGER_ALIAS_KINDS = {"integer", "bitvector", "timestamp", "duration"}

# Frontier/3.0.0 is intentionally specified as a small, independently
# replayable fixed point.  Keep these values explicit instead of importing the
# analyzer: a detached verifier must not trust the implementation whose claims
# it is checking.
FRONTIER_STATIC = 1
FRONTIER_MODELLED = 2
FRONTIER_UNKNOWN = 4
FRONTIER_PATH_CLASSES = (FRONTIER_STATIC, FRONTIER_MODELLED, FRONTIER_UNKNOWN)
FRONTIER_PATH_NAMES = {
    FRONTIER_STATIC: "STATIC",
    FRONTIER_MODELLED: "MODELLED",
    FRONTIER_UNKNOWN: "UNKNOWN",
}
FRONTIER_RELATION = {
    "defines": 0,
    "uses": 1,
    "loads": 2,
    "stores": 3,
    "data": 4,
    "controls": 5,
    "calls": 6,
    "returns": 7,
    "object": 8,
    "field": 9,
    "aliases": 10,
    "contains": 11,
    "maps_to": 12,
    "unknown": 13,
}
FRONTIER_CERTAINTY = {"must": 0, "may": 1, "modelled": 2, "unknown": 3}
FRONTIER_COMPATIBILITY = {"COMPATIBLE": 0, "UNKNOWN": 1, "INCOMPATIBLE": 2}
FRONTIER_VALUE_KIND = {
    "bool": 0,
    "integer": 1,
    "floating": 2,
    "enum": 3,
    "bitvector": 4,
    "timestamp": 5,
    "duration": 6,
    "pointer": 7,
    "record": 8,
    "array": 9,
    "unknown": 10,
}
FRONTIER_TRAVERSAL_DEFAULTS = {
    "algorithm": "ordinal-path-class-fixed-point",
    "algorithm_version": "3.0.0",
    "node_order": "node-id-utf8-lexicographic",
    "edge_order": "arc-kind-id-source-target-utf8-lexicographic",
    "path_class_encoding": "STATIC=1,MODELLED=2,UNKNOWN=4",
    "meet_ledger": "rift-meet-ledger/lp-u64le/1.0.0",
    "reach_ledger": "rift-reach-ledger/lp-u64le/1.0.0",
    "transition_ledger": "rift-transition-ledger/lp-u64le/1.0.0",
    "compatibility": "rift-context-compatibility/1.0.0",
    "model_arc_policy": "semantic-context-expansion/1.0.0",
    "exemplar_policy": "one-per-effective-class/lexicographic-first",
    "maximum_path_exemplars": 3,
}


class DuplicateKeyError(ValueError):
    """Raised when JSON contains duplicate object member names."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream, object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"top-level JSON value is not an object: {path}")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_semantic_id(prefix: str, semantic_material: str) -> str:
    """Reproduce ``rift::core::stable_id`` for detached reconstruction."""

    return f"{prefix}:{sha256_bytes(semantic_material.encode('utf-8'))}"


def _append_length_prefixed(material: bytearray, value: str) -> None:
    encoded = value.encode("utf-8")
    material.extend(len(encoded).to_bytes(8, "big"))
    material.extend(encoded)


def runtime_component_id(component: Mapping[str, Any]) -> str:
    material = bytearray()
    for key in ("component_kind", "name", "version", "sha256"):
        _append_length_prefixed(material, str(component[key]))
    return "tool:" + sha256_bytes(bytes(material))


def solver_budget_sha256(solver: Mapping[str, Any]) -> str:
    """Digest the exact solver identity, encoding and finite recipe budget."""

    material = bytearray()
    for value in (
        SOLVER_BUDGET_DOMAIN,
        solver["name"],
        solver["actual_version"],
        SOLVER_ENCODING_VERSION,
        str(solver["timeout_ms"]),
        str(solver["max_queries"]),
    ):
        _append_length_prefixed(material, str(value))
    return sha256_bytes(bytes(material))


MODEL_LAYER = {"platform": 0, "framework": 1, "project_adapter": 2}
MODEL_SELECTOR_KIND = {
    "exact_qualified_signature": 0,
    "exact_usr": 1,
    "typed_field": 2,
}
MODEL_PROJECTION = {
    "matched_node": 0,
    "formal_parameter": 1,
    "call_argument": 2,
    "call_result": 3,
    "receiver": 4,
}
MODEL_JOIN = {
    "same_object": 0,
    "same_scope": 1,
    "same_generation": 2,
    "same_handle": 3,
    "same_callsite": 4,
    "same_task": 5,
}
MODEL_FACT_KIND = {
    "external_boundary": 0,
    "semantic_transfer": 1,
    "event_link": 2,
    "timer_transition": 3,
    "queue_transition": 4,
    "lifecycle_transition": 5,
    "scope_key": 6,
    "clock_relation": 7,
    "persistence_transition": 8,
    "joint_action_relation": 9,
}
MODEL_CERTAINTY = {"must": 0, "may": 1, "modelled": 2, "unknown": 3}
MODEL_STAGE_STATUS = {
    "COMPLETE": 0,
    "CONSERVATIVE_INCOMPLETE": 1,
    "FAILED": 2,
}
MODEL_CLOCK_UNIT = {"ns": 0, "us": 1, "ms": 2, "s": 3, "ticks": 4}
MODEL_CLOCK_WRAP = {"none": 0, "modulo": 1, "saturating": 2, "unknown": 3}
MODEL_CLOCK_ENDPOINT = {"open": 0, "closed": 1, "mixed": 2, "unknown": 3}
MODEL_JOINT_OPERATOR = {"all_required": 0, "any_sufficient": 1, "unknown": 2}
MODEL_VALUE_TRANSFER_KIND = {
    "identity": 0,
    "affine": 1,
    "parse_identity_with_precondition": 2,
    "unknown": 3,
}
MODEL_VALUE_PRECONDITION = {
    "none": 0,
    "canonical_decimal_integer_in_range": 1,
    "unknown": 2,
}
MODEL_VALUE_KIND = {
    "bool": 0,
    "integer": 1,
    "floating": 2,
    "enum": 3,
    "bitvector": 4,
    "timestamp": 5,
    "duration": 6,
    "pointer": 7,
    "record": 8,
    "array": 9,
    "unknown": 10,
}


def model_pack_semantic_sha256(pack: Mapping[str, Any]) -> str:
    """Independently reproduce model.cpp:model_pack_semantic_sha256.

    The current C++ v2 format streams labels such as ``"\0selector\0"`` via
    ``operator<<(const char *)``.  Because those labels begin with NUL, they
    contribute zero bytes.  This function intentionally reproduces that exact
    byte contract; changing the C++ canonicalizer will therefore fail the
    detached regression instead of silently creating two specifications.
    """

    material = bytearray()

    def append(value: Any) -> None:
        material.extend(str(value).encode("utf-8"))

    def nul() -> None:
        material.append(0)

    def append_value_type(value_type: Mapping[str, Any]) -> None:
        append(MODEL_VALUE_KIND[value_type["kind"]])
        nul()
        append(value_type["canonical"])
        nul()
        if "bit_width" in value_type:
            append(value_type["bit_width"])
        nul()
        if "signed" in value_type:
            append("1" if value_type["signed"] else "0")
        nul()
        if "unit" in value_type:
            append(value_type["unit"])

    def append_clock_relation(clock: Mapping[str, Any]) -> None:
        append(clock["clock_source"])
        nul()
        append(MODEL_CLOCK_UNIT[clock["unit"]])
        nul()
        append(clock["epoch"])
        nul()
        # llvm::formatv("{0}", double) is the C++ contract here: fixed,
        # two decimal places, including trailing zeroes.
        append(format(float(clock["quantum"]), ".2f"))
        nul()
        append(format(float(clock["jitter"]), ".2f"))
        nul()
        append(MODEL_CLOCK_WRAP[clock["wrap"]])
        nul()
        if "wrap_value" in clock:
            append(clock["wrap_value"])
        nul()
        append(clock["start_event"])
        nul()
        append(clock["end_event"])
        nul()
        append(MODEL_CLOCK_ENDPOINT[clock["endpoint"]])
        nul()
        append(clock["scope_schema"])
        nul()
        append(clock["generation_schema"])

    def append_joint_relation(joint: Mapping[str, Any]) -> None:
        append(joint["group_schema_id"])
        nul()
        append(MODEL_JOINT_OPERATOR[joint["combination"]])
        nul()
        append("1" if joint["participant_set_complete"] else "0")
        nul()
        append(joint["scope_schema"])
        nul()
        append(joint["generation_schema"])
        for participant in sorted(joint["participant_capture_refs"]):
            nul()
            append(participant)

    def append_value_transfer(transfer: Mapping[str, Any]) -> None:
        append(MODEL_VALUE_TRANSFER_KIND[transfer["kind"]])
        nul()
        if "affine_scale" in transfer:
            append(transfer["affine_scale"])
        nul()
        if "affine_offset" in transfer:
            append(transfer["affine_offset"])
        nul()
        append(MODEL_VALUE_PRECONDITION[transfer["precondition"]])
        nul()
        append("1" if transfer["executor_enforces_precondition"] else "0")
        nul()
        append("1" if transfer["failure_branch_unknown"] else "0")

    # The trailing NUL in this C++ string literal is not inserted by ostream.
    append("model-pack-semantic/2.0.0")
    append(pack["schema_version"])
    nul()
    append(pack["model_pack_id"])
    nul()
    append(pack["model_pack_version"])
    nul()
    append(MODEL_LAYER[pack["layer"]])
    nul()
    append("1" if pack["property_independent"] else "0")
    nul()
    target = pack["target"]
    for key in ("target_version", "target_abi", "evidence_id", "digest_policy"):
        append(target[key])
        nul()
    limits = pack["resource_limits"]
    limit_keys = (
        "max_selector_matches",
        "max_capture_values",
        "max_join_assignments",
        "max_emitted_facts",
    )
    for index, key in enumerate(limit_keys):
        append(limits[key])
        if index + 1 != len(limit_keys):
            nul()

    for selector in sorted(pack["selectors"], key=lambda item: item["selector_id"]):
        append(selector["selector_id"])
        nul()
        append(MODEL_SELECTOR_KIND[selector["kind"]])
        nul()
        if "exact_value" in selector:
            append(selector["exact_value"])
        nul()
        if "owner_selector_ref" in selector:
            append(selector["owner_selector_ref"])
        for field_name in selector.get("field_path", []):
            nul()
            append(field_name)
        if "canonical_type" in selector:
            append(selector["canonical_type"])
        nul()
        append("1" if selector.get("application_private", False) else "0")

    for rule in sorted(pack["rules"], key=lambda item: item["rule_id"]):
        append(rule["rule_id"])
        nul()
        append(rule["evidence_note"])
        for match in sorted(rule["matches"], key=lambda item: item["match_id"]):
            append(match["match_id"])
            nul()
            append(match["selector_ref"])
        for capture in sorted(rule["captures"], key=lambda item: item["capture_id"]):
            append(capture["capture_id"])
            nul()
            append(capture["match_ref"])
            nul()
            append(MODEL_PROJECTION[capture["projection"]])
            nul()
            if "index" in capture:
                append(capture["index"])
        for join in sorted(rule["joins"], key=lambda item: item["join_id"]):
            append(join["join_id"])
            nul()
            append(MODEL_JOIN[join["kind"]])
            nul()
            append(join["left_capture_ref"])
            nul()
            append(join["right_capture_ref"])
        for emit in sorted(rule["emits"], key=lambda item: item["emit_id"]):
            append(emit["emit_id"])
            nul()
            append(MODEL_FACT_KIND[emit["fact_kind"]])
            nul()
            append(emit["source_capture_ref"])
            nul()
            if "target_capture_ref" in emit:
                append(emit["target_capture_ref"])
            nul()
            append(MODEL_CERTAINTY[emit["certainty"]])
            nul()
            append(emit["transfer_relation"])
            action = emit.get("external_action")
            if action is not None:
                append(action["action_schema_id"])
                nul()
                append(action["action_class"])
                nul()
                append(action["channel"])
                nul()
                append(action["operation"])
                nul()
                append_value_type(action["payload_type"])
                nul()
                append(action["payload_slot"])
                nul()
                append(action["scope_schema"])
                nul()
                append(action["generation_schema"])
                nul()
                append(action["timing_capability"])
                nul()
                append(action["required_capability"])
            # The leading-NUL labels in the C++ ostream add no bytes.  The
            # typed payload materials that follow them are nevertheless part
            # of the semantic digest and must be replayed here.
            if emit.get("clock_relation") is not None:
                append_clock_relation(emit["clock_relation"])
            if emit.get("joint_action_relation") is not None:
                append_joint_relation(emit["joint_action_relation"])
            if emit.get("value_transfer") is not None:
                append_value_transfer(emit["value_transfer"])
    return sha256_bytes(bytes(material))


def m4_source_manifest_digest(files: Sequence[Mapping[str, Any]]) -> str:
    material = bytearray(b"rift.identity/2.0.0\0input-manifest/1.0.0")
    for item in files:
        logical = str(item["logical_path"]).encode("utf-8")
        material.extend(b"\0")
        material.extend(str(item["role"]).encode("utf-8"))
        material.extend(b"\0")
        material.extend(str(len(logical)).encode("ascii"))
        material.extend(b":")
        material.extend(logical)
        material.extend(b"\0")
        material.extend(str(item["sha256"]).encode("ascii"))
        material.extend(b"\0")
        material.extend(str(item["byte_size"]).encode("ascii"))
    return sha256_bytes(bytes(material))


def m5_certificate_id(certificate: Mapping[str, Any]) -> str:
    material = copy.deepcopy(dict(certificate))
    material.pop("certificate_id", None)
    material.pop("started_at", None)
    material.pop("finished_at", None)
    return "m5-certificate:" + sha256_bytes(canonical_json_bytes(material))


@dataclass
class Finding:
    check_id: str
    status: str
    detail: str

    def as_json(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class Audit:
    certificate_path: pathlib.Path
    findings: list[Finding] = field(default_factory=list)
    checked_paths: set[str] = field(default_factory=set)

    def passed(self, check_id: str, detail: str) -> None:
        self.findings.append(Finding(check_id, "PASS", detail))

    def failed(self, check_id: str, detail: str) -> None:
        self.findings.append(Finding(check_id, "FAIL", detail))

    @property
    def failures(self) -> int:
        return sum(item.status == "FAIL" for item in self.findings)

    def report(self, certificate_sha256: str | None) -> dict[str, Any]:
        return {
            "schema_version": "rift-m5-detached-verifier/1.0.0",
            "verdict": "PASS" if self.failures == 0 else "FAIL",
            "certificate_path": str(self.certificate_path),
            "certificate_sha256": certificate_sha256,
            "checks": len(self.findings),
            "failures": self.failures,
            "physical_files_rehashed": len(self.checked_paths),
            "findings": [item.as_json() for item in self.findings],
        }


class SchemaSet:
    def __init__(self, schema_dir: pathlib.Path) -> None:
        self.schema_dir = schema_dir
        self.schemas: dict[str, dict[str, Any]] = {}
        self.validators: dict[str, jsonschema.Draft7Validator] = {}

    def load(self) -> None:
        paths = sorted(self.schema_dir.glob("*.schema.json"))
        if not paths:
            raise FileNotFoundError(f"no schemas below {self.schema_dir}")
        for path in paths:
            schema = load_json_strict(path)
            jsonschema.Draft7Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise ValueError(f"schema lacks $id: {path}")
            if schema_id in (item.get("$id") for item in self.schemas.values()):
                raise ValueError(f"duplicate schema $id: {schema_id}")
            self.schemas[path.name] = schema
        store = {schema["$id"]: schema for schema in self.schemas.values()}
        for name, schema in self.schemas.items():
            resolver = jsonschema.RefResolver.from_schema(schema, store=store)
            self.validators[name] = jsonschema.Draft7Validator(
                schema,
                resolver=resolver,
                format_checker=jsonschema.FormatChecker(),
            )

    def validate(self, name: str, value: Mapping[str, Any], audit: Audit, label: str) -> bool:
        validator = self.validators.get(name)
        if validator is None:
            audit.failed("schema.inventory", f"missing schema {name} for {label}")
            return False
        errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
        if errors:
            rendered = "; ".join(
                f"{list(error.path)}: {error.message}" for error in errors[:6]
            )
            audit.failed("schema.validation", f"{label}: {rendered}")
            return False
        audit.passed("schema.validation", f"{label} satisfies {name}")
        return True


class PhysicalHasher:
    def __init__(self, audit: Audit) -> None:
        self.audit = audit
        self.cache: dict[str, tuple[str, int]] = {}
        self.identities: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}

    def rehash(self, raw_path: str, label: str) -> tuple[str, int] | None:
        path = pathlib.Path(raw_path)
        if not path.is_absolute():
            self.audit.failed("physical.absolute_path", f"{label}: path is not absolute: {path}")
            return None
        key = str(path)
        if key in self.cache:
            return self.cache[key]
        try:
            before_link = path.lstat()
            with path.open("rb") as stream:
                opened_before = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened_before.st_mode):
                    raise OSError("opened object is not a regular file")
                digest = hashlib.sha256()
                byte_size = 0
                while block := stream.read(1024 * 1024):
                    digest.update(block)
                    byte_size += len(block)
                opened_after = os.fstat(stream.fileno())
            after_link = path.lstat()
            after_target = path.stat()
            opened_identity = (
                opened_before.st_dev,
                opened_before.st_ino,
                opened_before.st_size,
                opened_before.st_mtime_ns,
                opened_before.st_ctime_ns,
            )
            if opened_identity != (
                opened_after.st_dev,
                opened_after.st_ino,
                opened_after.st_size,
                opened_after.st_mtime_ns,
                opened_after.st_ctime_ns,
            ):
                raise OSError("file changed while being hashed")
            if (opened_after.st_dev, opened_after.st_ino) != (
                after_target.st_dev,
                after_target.st_ino,
            ):
                raise OSError("path target changed while being hashed")
            if (
                before_link.st_dev,
                before_link.st_ino,
                before_link.st_size,
                before_link.st_mtime_ns,
                before_link.st_ctime_ns,
            ) != (
                after_link.st_dev,
                after_link.st_ino,
                after_link.st_size,
                after_link.st_mtime_ns,
                after_link.st_ctime_ns,
            ):
                raise OSError("path entry changed while being hashed")
        except OSError as error:
            self.audit.failed("physical.rehash", f"{label}: {path}: {error}")
            return None
        result = (digest.hexdigest(), byte_size)
        self.cache[key] = result
        self.identities[key] = (
            (
                after_link.st_dev,
                after_link.st_ino,
                after_link.st_size,
                after_link.st_mtime_ns,
                after_link.st_ctime_ns,
            ),
            (
                after_target.st_dev,
                after_target.st_ino,
                after_target.st_size,
                after_target.st_mtime_ns,
                after_target.st_ctime_ns,
            ),
        )
        self.audit.checked_paths.add(key)
        return result

    def unchanged(self, raw_path: str, label: str) -> bool:
        path = pathlib.Path(raw_path)
        key = str(path)
        expected = self.identities.get(key)
        if expected is None:
            self.audit.failed("physical.stability", f"{label}: path was not previously hashed")
            return False
        try:
            link = path.lstat()
            target = path.stat()
        except OSError as error:
            self.audit.failed("physical.stability", f"{label}: {error}")
            return False
        observed = (
            (link.st_dev, link.st_ino, link.st_size, link.st_mtime_ns, link.st_ctime_ns),
            (target.st_dev, target.st_ino, target.st_size, target.st_mtime_ns, target.st_ctime_ns),
        )
        if observed != expected:
            self.audit.failed("physical.stability", f"{label}: path changed between hashing and consumption")
            return False
        return True

    def descriptor(self, descriptor: Mapping[str, Any], label: str) -> bool:
        path = descriptor.get("path")
        expected = descriptor.get("sha256")
        if not isinstance(path, str) or not isinstance(expected, str):
            self.audit.failed("physical.descriptor", f"{label}: missing path/SHA-256")
            return False
        observed = self.rehash(path, label)
        if observed is None:
            return False
        if observed[0] != expected:
            self.audit.failed(
                "physical.digest",
                f"{label}: expected {expected}, observed {observed[0]}",
            )
            return False
        self.audit.passed("physical.digest", f"{label}: exact bytes match {expected}")
        return True

    def verify_all_unchanged(self) -> None:
        stable = True
        for raw_path in sorted(self.identities):
            if not self.unchanged(raw_path, f"final physical audit {raw_path}"):
                stable = False
        if stable:
            self.audit.passed(
                "physical.final_stability",
                f"all {len(self.identities)} rehashed paths remained byte-source stable",
            )


def _unique_map(
    values: Any,
    key: str,
    audit: Audit,
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(values, list):
        audit.failed("identity.unique", f"{label} is not an array")
        return result
    for index, raw in enumerate(values):
        if not isinstance(raw, dict) or not isinstance(raw.get(key), str):
            audit.failed("identity.unique", f"{label}[{index}] lacks string {key}")
            continue
        value = raw[key]
        if value in result:
            audit.failed("identity.unique", f"{label} has duplicate {key}={value}")
        else:
            result[value] = raw
    return result


def _load_bound_json(
    descriptor: Mapping[str, Any],
    label: str,
    hasher: PhysicalHasher,
    audit: Audit,
) -> dict[str, Any] | None:
    if not hasher.descriptor(descriptor, label):
        return None
    try:
        value = load_json_strict(pathlib.Path(str(descriptor["path"])))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        audit.failed("json.strict", f"{label}: {error}")
        return None
    if not hasher.unchanged(str(descriptor["path"]), label):
        return None
    return value


def _verify_m4_stage_topology(certificate: Mapping[str, Any], audit: Audit) -> None:
    inputs = _unique_map(certificate.get("inputs"), "kind", audit, "M4 inputs")
    outputs = _unique_map(certificate.get("outputs"), "kind", audit, "M4 outputs")
    stages = certificate.get("stages")
    if not isinstance(stages, list) or [item.get("name") for item in stages if isinstance(item, dict)] != [
        "index", "bind", "influence", "cone", "certificate"
    ]:
        audit.failed("m4.stages", "M4 certificate does not have the fixed ordered five-stage topology")
        return
    required = {
        "typed_property_ir",
        "compile_commands",
        "source_inputs",
    }
    if set(inputs) != required or set(outputs) != set(M4_OUTPUT_ORDER):
        audit.failed("m4.stages", "M4 certificate input/output kinds are not exact")
        return
    expected = (
        ([inputs["compile_commands"]["sha256"], inputs["source_inputs"]["sha256"]], [outputs["semantic_index"]["sha256"]]),
        ([inputs["typed_property_ir"]["sha256"], outputs["semantic_index"]["sha256"]], [outputs["ap_bindings"]["sha256"]]),
        ([outputs["semantic_index"]["sha256"], outputs["ap_bindings"]["sha256"]], [outputs["contextual_influence_graph"]["sha256"]]),
        ([outputs["ap_bindings"]["sha256"], outputs["contextual_influence_graph"]["sha256"]], [outputs["ap_influence_cones"]["sha256"]]),
        ([outputs[name]["sha256"] for name in M4_OUTPUT_ORDER], []),
    )
    good = True
    for stage, (stage_inputs, stage_outputs) in zip(stages, expected):
        if stage.get("input_sha256") != stage_inputs or stage.get("output_sha256") != stage_outputs:
            good = False
            audit.failed("m4.stages", f"M4 {stage.get('name')} digest closure differs from its artifacts")
    if good:
        audit.passed("m4.stages", "M4 fixed stage DAG closes over physical artifact digests")


def _verify_m4(
    m5: Mapping[str, Any],
    schemas: SchemaSet,
    hasher: PhysicalHasher,
    audit: Audit,
    validate_semantic_schemas: bool,
) -> dict[str, dict[str, Any]]:
    commitments = m5["m4_commitments"]
    m4_descriptor = commitments["analysis_certificate"]
    m4 = _load_bound_json(m4_descriptor, "M4 analysis certificate", hasher, audit)
    if m4 is None:
        return {}
    if validate_semantic_schemas:
        schemas.validate("analysis_certificate.schema.json", m4, audit, "M4 analysis certificate")
    if m4.get("schema_version") != "2.0.0":
        audit.failed("m4.version", "M5 accepts only the physically verifiable M4 certificate/2.0.0")
    else:
        audit.passed("m4.version", "M4 certificate/2.0.0 is referenced")
    if m4_descriptor.get("artifact_id") != m4.get("certificate_id"):
        audit.failed("m4.commitment", "M4 certificate descriptor ID differs from its certificate_id")
    if m5.get("analysis_id") != m4.get("analysis_id"):
        audit.failed("m4.commitment", "M5 analysis_id differs from immutable M4 analysis_id")

    m4_inputs = _unique_map(m4.get("inputs"), "kind", audit, "M4 inputs")
    m4_outputs = _unique_map(m4.get("outputs"), "kind", audit, "M4 outputs")
    pairs = {
        "typed_property_ir": m4_inputs.get("typed_property_ir"),
        **{name: m4_outputs.get(name) for name in M4_OUTPUT_ORDER},
    }
    loaded: dict[str, dict[str, Any]] = {}
    for kind, m4_item in pairs.items():
        commitment = commitments.get(kind)
        if not isinstance(m4_item, dict) or not isinstance(commitment, dict):
            audit.failed("m4.commitment", f"missing M4 commitment for {kind}")
            continue
        if commitment != m4_item:
            audit.failed("m4.commitment", f"M5 {kind} descriptor does not exactly equal M4 descriptor")
            continue
        audit.passed("m4.commitment", f"{kind} descriptor exactly matches M4 certificate")
        value = _load_bound_json(commitment, f"M4 {kind}", hasher, audit)
        if value is not None:
            loaded[kind] = value
            if validate_semantic_schemas:
                schemas.validate(M4_ARTIFACT_SCHEMAS[kind], value, audit, f"M4 {kind}")
            if kind != "typed_property_ir" and value.get("artifact_id") != commitment.get("artifact_id"):
                audit.failed("artifact.identity", f"M4 {kind} artifact_id differs from descriptor")

    # Rehash every additional M4 path that is physically available, including
    # the compilation database and the complete source provenance manifest.
    for item in m4.get("inputs", []):
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            hasher.descriptor(item, f"M4 input {item.get('kind')}")
    for item in m4.get("outputs", []):
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            hasher.descriptor(item, f"M4 output {item.get('kind')}")
    provenance = m4.get("source_input_provenance")
    source_descriptor = m4_inputs.get("source_inputs", {})
    if isinstance(provenance, dict):
        if provenance.get("manifest_sha256") != source_descriptor.get("sha256"):
            audit.failed("m4.source_provenance", "M4 source manifest digest differs from source_inputs descriptor")
        source_files = provenance.get("files", [])
        if not isinstance(source_files, list):
            audit.failed("m4.source_provenance", "M4 source provenance files is not an array")
            source_files = []
        elif all(isinstance(item, dict) for item in source_files):
            try:
                recomputed_manifest = m4_source_manifest_digest(source_files)
            except (KeyError, TypeError, ValueError) as error:
                audit.failed("m4.source_provenance", f"cannot recompute M4 source manifest: {error}")
            else:
                if recomputed_manifest != provenance.get("manifest_sha256"):
                    audit.failed("m4.source_provenance", "M4 source manifest content digest is not reproducible")
                else:
                    audit.passed("m4.source_provenance", "M4 source manifest is independently recomputed")
        for item in source_files:
            if not isinstance(item, dict):
                continue
            for raw_path in item.get("observed_paths", []):
                observed = hasher.rehash(str(raw_path), f"M4 source {item.get('logical_path')}")
                if observed is not None and observed != (item.get("sha256"), item.get("byte_size")):
                    audit.failed("m4.source_provenance", f"M4 source bytes changed: {raw_path}")
    _verify_m4_stage_topology(m4, audit)
    # Keep the physically loaded stage ledger available to later detached
    # semantic replay.  The AP-cone JSON carries per-cone status, while the M4
    # certificate is the authoritative source of the aggregate cones.status
    # consumed by the in-memory M5 implementation.
    loaded["analysis_certificate"] = m4
    return loaded


def _verify_model_packs(
    m5: Mapping[str, Any],
    schemas: SchemaSet,
    hasher: PhysicalHasher,
    audit: Audit,
    validate_semantic_schemas: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = list(m5["model_packs"])
    order = sorted(
        records,
        key=lambda item: (
            item["model_pack_id"],
            item["model_pack_version"],
            item["semantic_sha256"],
            item["sha256"],
        ),
    )
    if records != order:
        audit.failed("model_packs.order", "model packs are not in VM canonical identity order")
    else:
        audit.passed("model_packs.order", "model packs use VM canonical identity order")
    identities: set[tuple[str, str]] = set()
    loaded: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        identity = (record["model_pack_id"], record["model_pack_version"])
        if identity in identities:
            audit.failed("model_packs.identity", f"duplicate model pack identity {identity[0]}@{identity[1]}")
        identities.add(identity)
        value = _load_bound_json(record, f"model pack[{index}]", hasher, audit)
        if value is None:
            continue
        loaded.append(value)
        if validate_semantic_schemas:
            schemas.validate("model_pack_v2.schema.json", value, audit, f"model pack[{index}]")
        for key in ("model_pack_id", "model_pack_version", "layer"):
            if value.get(key) != record.get(key):
                audit.failed("model_packs.metadata", f"model pack[{index}] {key} differs from exact input bytes")
        try:
            observed_semantic = model_pack_semantic_sha256(value)
        except (KeyError, TypeError, ValueError) as error:
            audit.failed(
                "model_packs.semantic_digest",
                f"model pack[{index}] semantic digest cannot be independently recomputed: {error}",
            )
        else:
            if observed_semantic != record.get("semantic_sha256"):
                audit.failed(
                    "model_packs.semantic_digest",
                    f"model pack[{index}] semantic digest differs from physical pack semantics",
                )
            else:
                audit.passed(
                    "model_packs.semantic_digest",
                    f"model pack[{index}] semantic SHA independently recomputes to {observed_semantic}",
                )
    return records, loaded


def _verify_executor(
    m5: Mapping[str, Any],
    schemas: SchemaSet,
    hasher: PhysicalHasher,
    audit: Audit,
    validate_semantic_schemas: bool,
) -> dict[str, Any] | None:
    record = m5["executor_manifest"]
    if record is None:
        audit.passed("executor.optional", "no executor capability manifest was asserted")
        return None
    value = _load_bound_json(record, "executor capability manifest", hasher, audit)
    if value is None:
        return None
    if validate_semantic_schemas:
        schemas.validate("executor_capabilities.schema.json", value, audit, "executor capability manifest")
    for key in ("executor_id", "executor_version", "artifact_id"):
        if value.get(key) != record.get(key):
            audit.failed("executor.metadata", f"executor {key} differs from exact manifest bytes")
    return value


def _verify_runtime(m5: Mapping[str, Any], hasher: PhysicalHasher, audit: Audit) -> None:
    components = m5["runtime_components"]
    by_id = _unique_map(components, "component_id", audit, "M5 runtime components")
    for index, component in enumerate(components):
        hasher.descriptor(component, f"runtime component[{index}] {component.get('name')}")
        if component.get("component_id") != runtime_component_id(component):
            audit.failed("runtime.identity", f"runtime component[{index}] stable ID is not digest-derived")
    analyzer = m5["analyzer"]
    analyzer_component = by_id.get(analyzer["runtime_component_id"])
    if analyzer_component is None:
        audit.failed("runtime.analyzer", "analyzer runtime_component_id is absent")
    elif (
        analyzer_component.get("component_kind") != "executable"
        or analyzer_component.get("sha256") != analyzer.get("binary_sha256")
        or analyzer_component.get("path") != analyzer.get("binary_path")
    ):
        audit.failed("runtime.analyzer", "analyzer identity/path/SHA does not match its runtime component")
    else:
        audit.passed("runtime.analyzer", "analyzer bytes are bound by one executable runtime component")
    solver = m5["solver"]
    solver_component = by_id.get(solver["runtime_component_id"])
    if solver_component is None:
        audit.failed("runtime.solver", "solver runtime_component_id is absent")
    elif (
        solver_component.get("sha256") != solver.get("component_sha256")
        or solver_component.get("version") != solver.get("actual_version")
        or (
            solver_component.get("component_id") != analyzer.get("runtime_component_id")
            and "z3" not in (str(solver_component.get("name")) + str(solver_component.get("path"))).lower()
        )
    ):
        audit.failed("runtime.solver", "Z3 actual version/component SHA does not match its named runtime component")
    else:
        audit.passed("runtime.solver", "Z3 actual version and exact component bytes are runtime-bound")
    expected_budget = solver_budget_sha256(solver)
    if solver.get("budget_sha256") != expected_budget:
        audit.failed(
            "runtime.solver_budget",
            "solver budget digest does not independently bind identity, encoding, timeout and query limit",
        )
    else:
        audit.passed(
            "runtime.solver_budget",
            f"solver timeout={solver['timeout_ms']}ms and max_queries={solver['max_queries']} are digest-bound",
        )


def _verify_outputs(
    m5: Mapping[str, Any],
    schemas: SchemaSet,
    hasher: PhysicalHasher,
    audit: Audit,
    validate_semantic_schemas: bool,
) -> dict[str, dict[str, Any]]:
    outputs = m5["outputs"]
    observed_order = [item.get("kind") for item in outputs]
    if tuple(observed_order) != M5_OUTPUT_ORDER:
        audit.failed("outputs.order", f"M5 output order is not {list(M5_OUTPUT_ORDER)}")
    by_kind = _unique_map(outputs, "kind", audit, "M5 outputs")
    if set(by_kind) != set(M5_OUTPUT_ORDER):
        audit.failed("outputs.identity", "M5 output kinds are not exact and unique")
    loaded: dict[str, dict[str, Any]] = {}
    for kind in M5_OUTPUT_ORDER:
        descriptor = by_kind.get(kind)
        if descriptor is None:
            continue
        value = _load_bound_json(descriptor, f"M5 {kind}", hasher, audit)
        if value is None:
            continue
        loaded[kind] = value
        if validate_semantic_schemas:
            schemas.validate(M5_OUTPUT_SCHEMAS[kind], value, audit, f"M5 {kind}")
        if value.get("artifact_id") != descriptor.get("artifact_id"):
            audit.failed("artifact.identity", f"M5 {kind} artifact_id differs from descriptor")
    return loaded


def _expected_m5_stages(m5: Mapping[str, Any]) -> dict[str, tuple[list[str], list[str]]]:
    m4 = m5["m4_commitments"]
    packs = m5["model_packs"]
    outputs = {item["kind"]: item["sha256"] for item in m5["outputs"]}
    executor = m5["executor_manifest"]
    contextual_inputs = [
        outputs["model_fact_overlay"],
        m4["contextual_influence_graph"]["sha256"],
        m4["ap_influence_cones"]["sha256"],
    ]
    if executor is not None:
        contextual_inputs.append(executor["sha256"])
    certificate_inputs = [
        m4["analysis_certificate"]["sha256"],
        m4["typed_property_ir"]["sha256"],
        m4["semantic_index"]["sha256"],
        m4["ap_bindings"]["sha256"],
        m4["contextual_influence_graph"]["sha256"],
        m4["ap_influence_cones"]["sha256"],
    ]
    for pack in packs:
        certificate_inputs.extend([pack["sha256"], pack["semantic_sha256"]])
    if executor is not None:
        certificate_inputs.append(executor["sha256"])
    certificate_inputs.extend(
        [
            m5["analyzer"]["configuration_sha256"],
            m5["build_manifest"]["manifest_sha256"],
            m5["build_manifest"]["production_core_sha256"],
            m5["build_manifest"]["schema_bundle_sha256"],
        ]
    )
    certificate_inputs.extend(item["sha256"] for item in m5["runtime_components"])
    certificate_inputs.extend(outputs[name] for name in M5_OUTPUT_ORDER)
    return {
        "model": (
            [m4["semantic_index"]["sha256"]] + [item["sha256"] for item in packs],
            [outputs["model_fact_overlay"]],
        ),
        "occurrence": (
            [
                m4["typed_property_ir"]["sha256"],
                m4["semantic_index"]["sha256"],
            ],
            [outputs["predicate_occurrence_bindings"]],
        ),
        "contextualize": (contextual_inputs, [outputs["frontier_candidates"]]),
        "frontier": ([outputs["frontier_candidates"]], [outputs["fuzzable_frontier"]]),
        "recipe": (
            [
                m4["typed_property_ir"]["sha256"],
                m4["ap_bindings"]["sha256"],
                m4["contextual_influence_graph"]["sha256"],
                m4["ap_influence_cones"]["sha256"],
                outputs["frontier_candidates"],
                outputs["model_fact_overlay"],
                outputs["predicate_occurrence_bindings"],
                m5["build_manifest"]["production_core_sha256"],
                m5["solver"]["component_sha256"],
                m5["solver"]["budget_sha256"],
            ],
            [outputs["mutation_recipes"], outputs["recipe_replay_obligations"]],
        ),
        "certificate": (certificate_inputs, []),
    }


def _verify_m5_stages(m5: Mapping[str, Any], audit: Audit) -> None:
    stages = m5["stages"]
    observed_order = [item.get("name") for item in stages]
    if tuple(observed_order) != STAGE_ORDER:
        audit.failed("m5.stages", f"expected {list(STAGE_ORDER)}, observed {observed_order}")
        return
    expected = _expected_m5_stages(m5)
    good = True
    for stage in stages:
        stage_expected = expected[stage["name"]]
        if stage["input_sha256"] != stage_expected[0] or stage["output_sha256"] != stage_expected[1]:
            good = False
            audit.failed("m5.stages", f"{stage['name']} digest closure/order differs from fixed topology")
    if good:
        audit.passed(
            "m5.stages",
            "model→occurrence→contextualize→frontier→recipe→certificate digest DAG is exact",
        )
    analysis_statuses = [stage["status"] for stage in stages[:5]]
    aggregate = max(analysis_statuses, key=lambda item: STATUS_RANK[item])
    if m5["status"] != aggregate or stages[5]["status"] != aggregate:
        audit.failed(
            "m5.status",
            "top-level/certificate status does not conservatively aggregate five semantic stages",
        )
    else:
        audit.passed("m5.status", f"stage status aggregates to {aggregate}")
    if (m5["solver"]["timeouts"] or m5["solver"]["unsupported"]) and aggregate == "COMPLETE":
        audit.failed("m5.status", "solver timeout/unsupported accounting cannot aggregate to COMPLETE")


def _iter_provenance(overlay: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for collection in (
        "external_actions",
        "boundary_attachments",
        "semantic_facts",
        "joint_action_constraints",
    ):
        for item in overlay.get(collection, []):
            if isinstance(item, dict):
                for provenance in item.get("provenance", []):
                    if isinstance(provenance, dict):
                        yield provenance


def _typed_value_transfer_material(transfer: Mapping[str, Any]) -> str:
    scale = transfer.get("affine_scale")
    offset = transfer.get("affine_offset")
    return "\0".join(
        (
            str(MODEL_VALUE_TRANSFER_KIND[transfer["kind"]]),
            "" if scale is None else str(scale),
            "" if offset is None else str(offset),
            str(MODEL_VALUE_PRECONDITION[transfer["precondition"]]),
            "1" if transfer["executor_enforces_precondition"] else "0",
            "1" if transfer["failure_branch_unknown"] else "0",
        )
    )


def _typed_value_transfer_valid(transfer: Any) -> bool:
    if not isinstance(transfer, Mapping):
        return False
    if set(transfer) != {
        "kind",
        "affine_scale",
        "affine_offset",
        "precondition",
        "executor_enforces_precondition",
        "failure_branch_unknown",
    }:
        return False
    kind = transfer.get("kind")
    scale = transfer.get("affine_scale")
    offset = transfer.get("affine_offset")
    precondition = transfer.get("precondition")
    enforced = transfer.get("executor_enforces_precondition")
    failure_unknown = transfer.get("failure_branch_unknown")
    if not isinstance(enforced, bool) or not isinstance(failure_unknown, bool):
        return False
    if kind == "identity":
        return (
            scale is None
            and offset is None
            and precondition == "none"
            and not enforced
            and not failure_unknown
        )
    if kind == "affine":
        return (
            isinstance(scale, int)
            and not isinstance(scale, bool)
            and isinstance(offset, int)
            and not isinstance(offset, bool)
            and precondition == "none"
            and not enforced
            and not failure_unknown
        )
    if kind == "parse_identity_with_precondition":
        return (
            scale is None
            and offset is None
            and precondition == "canonical_decimal_integer_in_range"
            and enforced
            and failure_unknown
        )
    if kind == "unknown":
        return (
            scale is None
            and offset is None
            and precondition == "unknown"
            and not enforced
            and failure_unknown
        )
    return False


def _typed_identity_transfer(transfer: Any) -> bool:
    if not _typed_value_transfer_valid(transfer):
        return False
    assert isinstance(transfer, Mapping)
    if transfer["kind"] == "identity":
        return True
    if transfer["kind"] == "affine":
        return transfer["affine_scale"] == 1 and transfer["affine_offset"] == 0
    return transfer["kind"] == "parse_identity_with_precondition"


def _typed_clock_relation_valid(clock: Any) -> bool:
    if not isinstance(clock, Mapping):
        return False
    if set(clock) != {
        "clock_source",
        "unit",
        "epoch",
        "quantum",
        "jitter",
        "wrap",
        "wrap_value",
        "start_event",
        "end_event",
        "endpoint",
        "scope_schema",
        "generation_schema",
    }:
        return False
    if any(
        not isinstance(clock.get(key), str) or not clock.get(key)
        for key in (
            "clock_source",
            "epoch",
            "start_event",
            "end_event",
            "scope_schema",
            "generation_schema",
        )
    ):
        return False
    if (
        clock.get("unit") not in MODEL_CLOCK_UNIT
        or clock.get("wrap") not in MODEL_CLOCK_WRAP
        or clock.get("endpoint") not in MODEL_CLOCK_ENDPOINT
    ):
        return False
    quantum = clock.get("quantum")
    jitter = clock.get("jitter")
    if (
        not isinstance(quantum, (int, float))
        or isinstance(quantum, bool)
        or not isinstance(jitter, (int, float))
        or isinstance(jitter, bool)
        or not (float("-inf") < float(quantum) < float("inf"))
        or not (float("-inf") < float(jitter) < float("inf"))
        or float(quantum) <= 0
        or float(jitter) < 0
    ):
        return False
    wrap_value = clock.get("wrap_value")
    if clock["wrap"] in {"modulo", "saturating"}:
        return (
            isinstance(wrap_value, int)
            and not isinstance(wrap_value, bool)
            and wrap_value > 0
        )
    return wrap_value is None


def _typed_clock_relation_material(clock: Mapping[str, Any]) -> str:
    wrap_value = clock.get("wrap_value")
    return "\0".join(
        (
            str(clock["clock_source"]),
            str(MODEL_CLOCK_UNIT[clock["unit"]]),
            str(clock["epoch"]),
            format(float(clock["quantum"]), ".2f"),
            format(float(clock["jitter"]), ".2f"),
            str(MODEL_CLOCK_WRAP[clock["wrap"]]),
            "" if wrap_value is None else str(wrap_value),
            str(clock["start_event"]),
            str(clock["end_event"]),
            str(MODEL_CLOCK_ENDPOINT[clock["endpoint"]]),
            str(clock["scope_schema"]),
            str(clock["generation_schema"]),
        )
    )


def _model_fact_material(fact: Mapping[str, Any]) -> str:
    clock = fact.get("clock_relation")
    transfer = fact.get("value_transfer")
    return "\0".join(
        (
            str(fact["kind"]),
            str(fact["source_semantic_node_id"]),
            str(fact["target_semantic_node_id"]),
            str(fact["transfer_relation"]),
            "" if clock is None else _typed_clock_relation_material(clock),
            "" if transfer is None else _typed_value_transfer_material(transfer),
        )
    )


def _overlay_identity_material(overlay: Mapping[str, Any]) -> str:
    material = (
        str(overlay["semantic_index_identity"])
        + "\0"
        + str(MODEL_STAGE_STATUS[overlay["status"]])
    )
    for digest in overlay["model_pack_sha256s"]:
        material += "\0" + str(digest)
    for action in overlay["external_actions"]:
        material += "\0" + str(action["external_action_id"])
    for attachment in overlay["boundary_attachments"]:
        material += (
            "\0"
            + str(attachment["attachment_id"])
            + "\0"
            + str(MODEL_CERTAINTY[attachment["certainty"]])
        )
    for fact in overlay["semantic_facts"]:
        material += (
            "\0"
            + str(fact["fact_id"])
            + "\0"
            + str(MODEL_CERTAINTY[fact["certainty"]])
        )
    for constraint in overlay["joint_action_constraints"]:
        material += (
            "\0"
            + str(constraint["constraint_id"])
            + "\0"
            + str(MODEL_CERTAINTY[constraint["certainty"]])
        )
    for unknown in overlay["unknown_outcomes"]:
        material += "\0" + str(unknown["unknown_id"])
    for ledger in overlay["resource_ledger"]:
        material += (
            "\0"
            + str(ledger["ledger_id"])
            + "\0"
            + str(ledger["observed"])
            + "\0"
            + ("1" if ledger["complete"] else "0")
        )
    return material


def _verify_model_overlay_semantics(
    overlay: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    audit: Audit,
) -> None:
    """Replay the typed VM output identities without trusting the VM.

    The external-action ID contains a callsite/node instance choice that is not
    fully serialized in the overlay, so that one ID is treated as an opaque
    root.  Every newly introduced typed object below it is content-addressed
    and independently reconstructed.
    """

    starting_failures = audit.failures
    required = {
        "schema_version",
        "artifact_id",
        "semantic_index_artifact_id",
        "semantic_index_identity",
        "status",
        "model_pack_sha256s",
        "external_actions",
        "boundary_attachments",
        "semantic_facts",
        "joint_action_constraints",
        "unknown_outcomes",
        "resource_ledger",
        "coverage_gaps",
        "diagnostics",
    }
    missing = sorted(required - set(overlay))
    if missing:
        audit.failed(
            "model_overlay.canonical_fields",
            f"overlay omits C++ canonical fields {missing}",
        )
        return
    collections = (
        ("external_actions", "external_action_id"),
        ("boundary_attachments", "attachment_id"),
        ("semantic_facts", "fact_id"),
        ("joint_action_constraints", "constraint_id"),
        ("unknown_outcomes", "unknown_id"),
        ("resource_ledger", "ledger_id"),
    )
    global_ids: set[str] = {str(overlay.get("artifact_id"))}
    for collection, key in collections:
        values = overlay.get(collection)
        if not isinstance(values, list) or any(
            not isinstance(item, Mapping) or not isinstance(item.get(key), str)
            for item in values
        ):
            audit.failed(
                "model_overlay.canonical_order",
                f"{collection} is not a typed object ledger",
            )
            return
        ids = [str(item[key]) for item in values]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            audit.failed(
                "model_overlay.canonical_order",
                f"{collection} is not unique and UTF-8 ID sorted",
            )
        overlap = global_ids.intersection(ids)
        if overlap:
            audit.failed(
                "model_overlay.identity",
                f"overlay stable IDs collide: {sorted(overlap)}",
            )
        global_ids.update(ids)
    pack_digests = overlay.get("model_pack_sha256s")
    if (
        not isinstance(pack_digests, list)
        or pack_digests != sorted(set(pack_digests))
    ):
        audit.failed(
            "model_overlay.canonical_order",
            "model_pack_sha256s is not unique and sorted",
        )
    semantic_nodes = {
        item.get("node_id")
        for item in semantic_index.get("semantic_nodes", [])
        if isinstance(item, Mapping) and isinstance(item.get("node_id"), str)
    }
    actions = {
        item["external_action_id"]: item
        for item in overlay["external_actions"]
        if isinstance(item, Mapping)
    }
    attachments = overlay["boundary_attachments"]
    for attachment in attachments:
        if "value_transfer" not in attachment:
            audit.failed(
                "model_overlay.value_transfer",
                f"attachment {attachment['attachment_id']} omits canonical value_transfer",
            )
            continue
        transfer = attachment.get("value_transfer")
        if transfer is not None and not _typed_value_transfer_valid(transfer):
            audit.failed(
                "model_overlay.value_transfer",
                f"attachment {attachment['attachment_id']} has an inconsistent typed transfer",
            )
            continue
        if attachment.get("external_action_id") not in actions:
            audit.failed(
                "model_overlay.references",
                f"attachment {attachment['attachment_id']} references an unknown action",
            )
        if semantic_nodes and attachment.get("semantic_node_id") not in semantic_nodes:
            audit.failed(
                "model_overlay.references",
                f"attachment {attachment['attachment_id']} references an unknown semantic node",
            )
        transfer_material = (
            "" if transfer is None else _typed_value_transfer_material(transfer)
        )
        expected = stable_semantic_id(
            "boundary-attachment",
            "\0".join(
                (
                    str(attachment.get("external_action_id")),
                    str(attachment.get("semantic_node_id")),
                    str(attachment.get("transfer_relation")),
                    transfer_material,
                )
            ),
        )
        if attachment.get("attachment_id") != expected:
            audit.failed(
                "model_overlay.content_id",
                f"attachment {attachment.get('attachment_id')} does not bind typed transfer content",
            )
    for fact in overlay["semantic_facts"]:
        if "clock_relation" not in fact or "value_transfer" not in fact:
            audit.failed(
                "model_overlay.canonical_fields",
                f"fact {fact['fact_id']} omits canonical typed payload fields",
            )
            continue
        clock = fact.get("clock_relation")
        transfer = fact.get("value_transfer")
        if (fact.get("kind") == "clock_relation") != (clock is not None):
            audit.failed(
                "model_overlay.clock_relation",
                f"fact {fact['fact_id']} kind/payload contract is inconsistent",
            )
            continue
        if clock is not None and not _typed_clock_relation_valid(clock):
            audit.failed(
                "model_overlay.clock_relation",
                f"fact {fact['fact_id']} has an incomplete clock relation",
            )
            continue
        if transfer is not None and not _typed_value_transfer_valid(transfer):
            audit.failed(
                "model_overlay.value_transfer",
                f"fact {fact['fact_id']} has an inconsistent typed transfer",
            )
            continue
        if semantic_nodes and (
            fact.get("source_semantic_node_id") not in semantic_nodes
            or fact.get("target_semantic_node_id") not in semantic_nodes
        ):
            audit.failed(
                "model_overlay.references",
                f"fact {fact['fact_id']} references an unknown semantic node",
            )
        try:
            expected = stable_semantic_id(
                "model-fact", _model_fact_material(fact)
            )
        except (KeyError, TypeError, ValueError) as error:
            audit.failed(
                "model_overlay.content_id",
                f"fact {fact['fact_id']} material cannot be reconstructed: {error}",
            )
        else:
            if fact.get("fact_id") != expected:
                audit.failed(
                    "model_overlay.content_id",
                    f"fact {fact.get('fact_id')} does not bind typed content",
                )
    for constraint in overlay["joint_action_constraints"]:
        participants = constraint.get("participant_semantic_node_ids")
        if (
            not isinstance(participants, list)
            or len(participants) < 2
            or participants != sorted(set(participants))
        ):
            audit.failed(
                "model_overlay.joint_constraint",
                f"constraint {constraint['constraint_id']} participants are not a closed canonical set",
            )
            continue
        if semantic_nodes and any(item not in semantic_nodes for item in participants):
            audit.failed(
                "model_overlay.references",
                f"constraint {constraint['constraint_id']} references an unknown semantic node",
            )
        if constraint.get("combination") not in MODEL_JOINT_OPERATOR:
            audit.failed(
                "model_overlay.joint_constraint",
                f"constraint {constraint['constraint_id']} has an unknown operator",
            )
            continue
        provenance = [
            item for item in constraint.get("provenance", [])
            if isinstance(item, Mapping)
        ]
        possible_group_ids = {
            stable_semantic_id(
                "joint-action-group",
                "\0".join(
                    (
                        str(item.get("model_pack_sha256")),
                        str(item.get("rule_id")),
                        str(constraint.get("group_schema_id")),
                        *[str(value) for value in participants],
                    )
                ),
            )
            for item in provenance
        }
        if not possible_group_ids or constraint.get("group_instance_id") not in possible_group_ids:
            audit.failed(
                "model_overlay.content_id",
                f"constraint {constraint['constraint_id']} group ID is not provenance/participant bound",
            )
        expected = stable_semantic_id(
            "joint-action-constraint",
            "\0".join(
                (
                    str(constraint.get("group_instance_id")),
                    str(MODEL_JOINT_OPERATOR[constraint["combination"]]),
                    "1" if constraint.get("participant_set_complete") else "0",
                    str(constraint.get("scope_schema")),
                    str(constraint.get("generation_schema")),
                )
            ),
        )
        if constraint.get("constraint_id") != expected:
            audit.failed(
                "model_overlay.content_id",
                f"constraint {constraint.get('constraint_id')} is not content-bound",
            )
    try:
        expected_overlay_id = stable_semantic_id(
            "model-overlay", _overlay_identity_material(overlay)
        )
    except (KeyError, TypeError, ValueError) as error:
        audit.failed(
            "model_overlay.artifact_id",
            f"overlay artifact material cannot be reconstructed: {error}",
        )
    else:
        if overlay.get("artifact_id") != expected_overlay_id:
            audit.failed(
                "model_overlay.artifact_id",
                "overlay artifact ID does not close over typed child identities",
            )
    if audit.failures == starting_failures:
        audit.passed(
            "model_overlay.typed_closure",
            "typed clock/value/joint ledgers and overlay artifact ID independently close",
        )


def _solver_counters_for_recipes(
    recipes: Mapping[str, Any],
) -> tuple[int, int, int]:
    queries = 0
    timeouts = 0
    unsupported = 0
    for recipe in recipes.get("recipes", []):
        if not isinstance(recipe, dict):
            continue
        query_objects = [recipe.get("solver_query")]
        if recipe.get("direction_query") is not None:
            query_objects.append(recipe.get("direction_query"))
        for query in query_objects:
            if not isinstance(query, dict):
                continue
            outcome = query.get("outcome")
            if outcome in {"SAT", "UNSAT", "UNKNOWN", "TIMEOUT"}:
                queries += 1
            if outcome == "TIMEOUT":
                timeouts += 1
            if outcome == "UNSUPPORTED":
                unsupported += 1
    return queries, timeouts, unsupported


def _verify_recipe_solver_contract(
    recipes: Mapping[str, Any],
    solver: Mapping[str, Any],
    audit: Audit,
) -> None:
    """Check truth-change and direction-counterexample evidence separately.

    A truth-change SAT pair supports a recipe.  A direction query asks the
    opposite question: UNSAT proves that no opposite-direction counterexample
    exists, while every other outcome leaves mutation direction unproved.  In
    particular, direction SAT is a counterexample and must never license a
    MONOTONE_UP/MONOTONE_DOWN claim.
    """

    for recipe in recipes.get("recipes", []):
        if not isinstance(recipe, dict):
            continue
        recipe_id = recipe.get("recipe_id")
        truth = recipe.get("solver_query")
        if not isinstance(truth, dict):
            continue
        truth_outcome = truth.get("outcome")
        recipe_status = recipe.get("status")
        for query_name, query in (
            ("truth-change", truth),
            ("direction", recipe.get("direction_query")),
        ):
            if query is None or not isinstance(query, dict):
                continue
            if (
                query.get("solver") != solver.get("name")
                or query.get("solver_version") != solver.get("actual_version")
                or query.get("encoding_version") != SOLVER_ENCODING_VERSION
                or query.get("timeout_ms") != solver.get("timeout_ms")
            ):
                audit.failed(
                    "runtime.solver_query_contract",
                    f"recipe {recipe_id} {query_name} query differs from the bound solver contract",
                )
        direction = recipe.get("direction_query")
        direction_outcome = (
            direction.get("outcome") if isinstance(direction, dict) else None
        )
        direction_incomplete = direction_outcome in {
            "UNKNOWN", "TIMEOUT", "UNSUPPORTED", "NOT_RUN"
        }
        if truth_outcome == "SAT":
            if direction_incomplete:
                mutations = [
                    item for item in recipe.get("action_mutations", [])
                    if isinstance(item, dict)
                ]
                if recipe_status != "UNKNOWN" or any(
                    item.get("mutation_kind") not in {None, "UNKNOWN"}
                    or item.get("direction") not in {None, "UNKNOWN"}
                    for item in mutations
                ):
                    audit.failed(
                        "runtime.truth_change_semantics",
                        f"recipe {recipe_id} does not fail closed after incomplete direction outcome {direction_outcome}",
                    )
            elif recipe_status not in {"SUPPORTED", "HEURISTIC"}:
                audit.failed(
                    "runtime.truth_change_semantics",
                    f"recipe {recipe_id} hides a SAT truth-change pair as {recipe_status}",
                )
        elif recipe_status != "UNKNOWN":
            audit.failed(
                "runtime.truth_change_semantics",
                f"recipe {recipe_id} reports {recipe_status} without a SAT truth-change pair",
            )

        monotone_claims = [
            mutation.get("direction")
            for mutation in recipe.get("action_mutations", [])
            if isinstance(mutation, dict)
            and mutation.get("direction") in {"MONOTONE_UP", "MONOTONE_DOWN"}
        ]
        if direction is None:
            if monotone_claims:
                audit.failed(
                    "runtime.direction_semantics",
                    f"recipe {recipe_id} claims monotonicity without a direction counterexample query",
                )
            continue
        if not isinstance(direction, dict):
            continue
        direction_outcome = direction.get("outcome")
        if truth_outcome != "SAT":
            audit.failed(
                "runtime.direction_semantics",
                f"recipe {recipe_id} has a direction query without a SAT truth-change premise",
            )
        if direction_outcome != "UNSAT" and monotone_claims:
            audit.failed(
                "runtime.direction_semantics",
                f"recipe {recipe_id} claims {monotone_claims} although direction counterexample outcome is {direction_outcome}",
            )

    observed = _solver_counters_for_recipes(recipes)
    declared = (
        solver["queries"],
        solver["timeouts"],
        solver["unsupported"],
    )
    if declared != observed:
        audit.failed(
            "runtime.solver_accounting",
            "certificate solver counters differ from mutation-recipe query outcomes",
        )
    else:
        audit.passed(
            "runtime.solver_accounting",
            f"solver accounting closes: queries={observed[0]}, timeouts={observed[1]}, unsupported={observed[2]}",
        )
    if observed[0] > solver["max_queries"]:
        audit.failed(
            "runtime.solver_budget",
            f"observed {observed[0]} solver invocations exceed max_queries={solver['max_queries']}",
        )


def _collect_predicate_references(expression: Any) -> set[str]:
    if not isinstance(expression, Mapping):
        return set()
    result: set[str] = set()
    selector = expression.get("referenced_selector_id")
    if isinstance(selector, str):
        result.add(selector)
    for operand in expression.get("operands", []):
        result.update(_collect_predicate_references(operand))
    return result


def _predicate_action_branches(expression: Any) -> list[tuple[set[str], bool]]:
    if not isinstance(expression, Mapping):
        return [(set(), False)]
    operator = expression.get("operator")
    operands = expression.get("operands", [])
    is_or = expression.get("node_kind") == "boolean" and operator in {"||", "or"}
    is_and = expression.get("node_kind") == "boolean" and operator in {"&&", "and"}
    if is_or:
        result: list[tuple[set[str], bool]] = []
        for operand in operands:
            result.extend(_predicate_action_branches(operand))
        return result
    if is_and:
        result: list[tuple[set[str], bool]] = [(set(), False)]
        for operand in operands:
            nested = _predicate_action_branches(operand)
            product: list[tuple[set[str], bool]] = []
            for left, _ in result:
                for right, _ in nested:
                    product.append((set(left).union(right), True))
            result = product
        return result
    return [(_collect_predicate_references(expression), False)]


def _candidate_closed(candidate: Mapping[str, Any]) -> bool:
    evidence = candidate.get("evidence")
    completeness = evidence.get("completeness") if isinstance(evidence, Mapping) else None
    return isinstance(completeness, Mapping) and all(
        completeness.get(key) is True
        for key in (
            "model_vm_complete",
            "attachment_enumeration_complete",
            "forward_enumeration_complete",
            "cone_complete",
            "compatibility_complete",
        )
    ) and completeness.get("gap_reasons") == []


def _candidate_has_identity_boundary_witness(
    candidate: Mapping[str, Any],
    overlay_attachments: Mapping[str, Mapping[str, Any]],
) -> bool:
    action = candidate.get("action")
    if not isinstance(action, Mapping):
        return False
    action_id = action.get("external_action_id")
    for witness in candidate.get("witnesses", []):
        if not isinstance(witness, Mapping) or witness.get("compatibility") != "COMPATIBLE":
            continue
        attachment = overlay_attachments.get(str(witness.get("attachment_id")))
        if (
            isinstance(attachment, Mapping)
            and attachment.get("external_action_id") == action_id
            and attachment.get("certainty") == "modelled"
            and _typed_identity_transfer(attachment.get("value_transfer"))
        ):
            return True
    return False


def _expected_model_prerequisites(
    candidate: Mapping[str, Any],
    facts: Mapping[str, Mapping[str, Any]],
    attachments: Sequence[Mapping[str, Any]],
    actions: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    candidate_id = str(candidate.get("candidate_id"))
    target_action = candidate.get("action", {})
    target_action_id = str(target_action.get("external_action_id"))
    witness_fact_ids = {
        str(fact_id)
        for witness in candidate.get("witnesses", [])
        if isinstance(witness, Mapping)
        for fact_id in witness.get("model_fact_ids", [])
    }
    result: dict[str, dict[str, Any]] = {}
    prerequisite_kinds = {
        "event_link",
        "timer_transition",
        "queue_transition",
        "lifecycle_transition",
        "persistence_transition",
    }
    for fact_id in sorted(witness_fact_ids):
        fact = facts.get(fact_id)
        if not isinstance(fact, Mapping) or fact.get("kind") not in prerequisite_kinds:
            continue
        prerequisite_action_ids = sorted(
            {
                str(item.get("external_action_id"))
                for item in attachments
                if item.get("semantic_node_id") == fact.get("source_semantic_node_id")
                and item.get("external_action_id") in actions
            }
        )
        if not prerequisite_action_ids:
            continue
        choice_id = stable_semantic_id(
            "prerequisite-choice", candidate_id + "\0" + fact_id
        )
        alternatives: list[dict[str, Any]] = []
        for action_id in prerequisite_action_ids:
            dag_id = stable_semantic_id(
                "prerequisite-dag", choice_id + "\0" + action_id
            )
            if action_id == target_action_id:
                alternatives.append(
                    {
                        "dag_id": dag_id,
                        "status": "PARTIAL_ORDER_UNKNOWN",
                        "steps": [],
                        "uncertainty_reasons": [
                            "lifecycle prerequisite aliases the target action and forms a cycle"
                        ],
                    }
                )
                continue
            before_id = stable_semantic_id(
                "prerequisite-step", dag_id + "\0" + action_id
            )
            target_id = stable_semantic_id(
                "prerequisite-step", dag_id + "\0" + target_action_id
            )
            complete = fact.get("certainty") == "modelled"
            alternatives.append(
                {
                    "dag_id": dag_id,
                    "status": "COMPLETE" if complete else "PARTIAL_ORDER_UNKNOWN",
                    "steps": [
                        {
                            "step_id": before_id,
                            "action_id": action_id,
                            "operation": actions[action_id].get("operation"),
                            "predecessor_step_ids": [],
                        },
                        {
                            "step_id": target_id,
                            "action_id": target_action_id,
                            "operation": target_action.get("operation"),
                            "predecessor_step_ids": [before_id],
                        },
                    ],
                    "uncertainty_reasons": []
                    if complete
                    else [
                        "prerequisite model fact is UNKNOWN rather than MODELLED"
                    ],
                }
            )
        alternatives.sort(key=lambda item: str(item["dag_id"]))
        result[choice_id] = {
            "choice_id": choice_id,
            "alternatives": alternatives,
        }
    return result


def _control_prerequisite_candidates(
    target: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    graph: Mapping[str, Any],
    actions: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    edges = {
        item.get("edge_id"): item
        for item in graph.get("edges", [])
        if isinstance(item, Mapping) and isinstance(item.get("edge_id"), str)
    }
    target_nodes: set[str] = set()
    for witness in target.get("witnesses", []):
        if not isinstance(witness, Mapping) or witness.get("compatibility") != "COMPATIBLE":
            continue
        if isinstance(witness.get("boundary_node_id"), str):
            target_nodes.add(witness["boundary_node_id"])
        for path in witness.get("path_exemplars", []):
            if not isinstance(path, Mapping) or path.get("compatibility") != "COMPATIBLE":
                continue
            for key in ("meet_node_id", "root_node_id"):
                if isinstance(path.get(key), str):
                    target_nodes.add(path[key])
            for step in list(path.get("forward_steps", [])) + list(path.get("root_steps", [])):
                if isinstance(step, Mapping):
                    if isinstance(step.get("source_node_id"), str):
                        target_nodes.add(step["source_node_id"])
                    if isinstance(step.get("target_node_id"), str):
                        target_nodes.add(step["target_node_id"])
    target_action = target.get("action", {})
    result: dict[str, dict[str, Any]] = {}
    for guard in candidates:
        guard_action = guard.get("action", {})
        if (
            guard.get("candidate_id") == target.get("candidate_id")
            or guard.get("ap_id") != target.get("ap_id")
            or guard.get("disposition") != "ACTIONABLE"
            or not isinstance(guard_action, Mapping)
            or guard_action.get("external_action_id")
            == target_action.get("external_action_id")
            or guard_action.get("scope_schema") != target_action.get("scope_schema")
            or guard_action.get("generation_schema")
            != target_action.get("generation_schema")
        ):
            continue
        control_edges: set[str] = set()
        all_must = True
        for witness in guard.get("witnesses", []):
            if not isinstance(witness, Mapping) or witness.get("compatibility") != "COMPATIBLE":
                continue
            for path in witness.get("path_exemplars", []):
                if not isinstance(path, Mapping) or path.get("compatibility") != "COMPATIBLE":
                    continue
                for step in path.get("forward_steps", []):
                    if not isinstance(step, Mapping) or step.get("kind") != "GRAPH_EDGE":
                        continue
                    edge = edges.get(step.get("graph_edge_id"))
                    if (
                        isinstance(edge, Mapping)
                        and edge.get("relation_kind") == "controls"
                        and edge.get("target_node_id") in target_nodes
                    ):
                        control_edges.add(str(edge["edge_id"]))
                        all_must = all_must and edge.get("certainty") == "must"
        if not control_edges:
            continue
        material = str(target.get("candidate_id")) + "\0" + str(guard.get("candidate_id"))
        for edge_id in sorted(control_edges):
            material += "\0" + edge_id
        choice_id = stable_semantic_id("prerequisite-control-choice", material)
        dag_id = stable_semantic_id("prerequisite-control-dag", material)
        before_action_id = str(guard_action.get("external_action_id"))
        target_action_id = str(target_action.get("external_action_id"))
        before_id = stable_semantic_id(
            "prerequisite-control-step", dag_id + "\0" + before_action_id
        )
        target_id = stable_semantic_id(
            "prerequisite-control-step", dag_id + "\0" + target_action_id
        )
        reasons = [
            "static control dependence does not close external-action temporal order or persistence"
        ]
        if not all_must:
            reasons.append(
                "control dependence reaching the value path is MAY rather than MUST"
            )
        result[choice_id] = {
            "choice_id": choice_id,
            "alternatives": [
                {
                    "dag_id": dag_id,
                    "status": "PARTIAL_ORDER_UNKNOWN",
                    "steps": [
                        {
                            "step_id": before_id,
                            "action_id": before_action_id,
                            "operation": actions.get(before_action_id, {}).get("operation"),
                            "predecessor_step_ids": [],
                        },
                        {
                            "step_id": target_id,
                            "action_id": target_action_id,
                            "operation": actions.get(target_action_id, {}).get("operation"),
                            "predecessor_step_ids": [before_id],
                        },
                    ],
                    "uncertainty_reasons": sorted(reasons),
                }
            ],
        }
    return result


def _joint_requirement_candidates(
    group_recipes: Sequence[Mapping[str, Any]],
    candidates_by_id: Mapping[str, Mapping[str, Any]],
    property_ir: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> list[tuple[str, list[str], bool]]:
    """Return (requirement_id, model_fact_ids, evidence_complete) matches."""

    if not group_recipes:
        return []
    first = group_recipes[0]
    hyperedge = first.get("action_hyperedge", {})
    action_ids = sorted(hyperedge.get("action_ids", []))
    ap_id = first.get("ap_id")
    if any(recipe.get("ap_id") != ap_id for recipe in group_recipes):
        return []
    members = [
        candidates_by_id.get(str(recipe.get("frontier_candidate_id")))
        for recipe in group_recipes
    ]
    members = [item for item in members if isinstance(item, Mapping)]
    if len(members) != len(group_recipes):
        return []
    scopes = {item.get("action", {}).get("scope_schema") for item in members}
    generations = {
        item.get("action", {}).get("generation_schema") for item in members
    }
    attachments = {
        item.get("attachment_id"): item
        for item in overlay.get("boundary_attachments", [])
        if isinstance(item, Mapping)
    }
    base_closed = (
        len(scopes) == 1
        and len(generations) == 1
        and all(_candidate_closed(item) for item in members)
        and all(
            _candidate_has_identity_boundary_witness(item, attachments)
            for item in members
        )
    )
    matches: list[tuple[str, list[str], bool]] = []
    aps = {
        item.get("ap_id"): item
        for item in property_ir.get("atomic_propositions", [])
        if isinstance(item, Mapping)
    }
    ap = aps.get(ap_id)
    if isinstance(ap, Mapping):
        for selectors, explicit_conjunction in _predicate_action_branches(
            ap.get("predicate")
        ):
            if not explicit_conjunction or len(selectors) < 2:
                continue
            observed_selectors = {
                recipe.get("target_predicate_selector_id")
                for recipe in group_recipes
                if isinstance(recipe.get("target_predicate_selector_id"), str)
            }
            action_for_selector = {
                recipe.get("target_predicate_selector_id"): candidates_by_id[
                    str(recipe.get("frontier_candidate_id"))
                ].get("action", {}).get("external_action_id")
                for recipe in group_recipes
                if isinstance(recipe.get("target_predicate_selector_id"), str)
            }
            material = "typed-source-conjunction\0" + str(ap_id)
            for selector in sorted(selectors):
                material += "\0" + selector
            for action_id in action_ids:
                material += "\0" + str(action_id)
            requirement_id = stable_semantic_id("joint-source", material)
            complete = (
                base_closed
                and observed_selectors == selectors
                and len(action_for_selector) == len(selectors)
                and len(set(action_for_selector.values())) == len(selectors)
                and set(action_for_selector.values()) == set(action_ids)
            )
            matches.append((requirement_id, [], complete))
    for constraint in overlay.get("joint_action_constraints", []):
        if not isinstance(constraint, Mapping) or constraint.get("combination") == "any_sufficient":
            continue
        participants = set(constraint.get("participant_semantic_node_ids", []))
        covered: set[str] = set()
        member_actions: set[str] = set()
        member_selectors: set[str] = set()
        for recipe, member in zip(group_recipes, members):
            member_actions.add(str(member.get("action", {}).get("external_action_id")))
            selector = recipe.get("target_predicate_selector_id")
            if isinstance(selector, str):
                member_selectors.add(selector)
            for witness in member.get("witnesses", []):
                if not isinstance(witness, Mapping) or witness.get("compatibility") != "COMPATIBLE":
                    continue
                attachment = attachments.get(witness.get("attachment_id"))
                if isinstance(attachment, Mapping) and attachment.get("semantic_node_id") in participants:
                    covered.add(str(attachment["semantic_node_id"]))
        if member_actions != set(action_ids) or covered != participants:
            continue
        requirement_id = stable_semantic_id(
            "joint-model", str(constraint.get("constraint_id")) + "\0" + str(ap_id)
        )
        complete = (
            base_closed
            and constraint.get("combination") == "all_required"
            and constraint.get("participant_set_complete") is True
            and constraint.get("certainty") == "modelled"
            and scopes == {constraint.get("scope_schema")}
            and generations == {constraint.get("generation_schema")}
            and len(member_selectors) == len(action_ids)
        )
        matches.append(
            (requirement_id, [str(constraint.get("constraint_id"))], complete)
        )
    return matches


def _verify_recipe_semantic_closure(
    recipes: Mapping[str, Any],
    property_ir: Mapping[str, Any],
    graph: Mapping[str, Any],
    candidates_document: Mapping[str, Any],
    overlay: Mapping[str, Any],
    audit: Audit,
) -> None:
    starting_failures = audit.failures
    candidates = [
        item for item in candidates_document.get("candidates", [])
        if isinstance(item, Mapping)
    ]
    candidates_by_id = {
        str(item.get("candidate_id")): item for item in candidates
    }
    actions = {
        str(item.get("external_action_id")): item
        for item in overlay.get("external_actions", [])
        if isinstance(item, Mapping)
    }
    attachments = [
        item for item in overlay.get("boundary_attachments", [])
        if isinstance(item, Mapping)
    ]
    facts = {
        str(item.get("fact_id")): item
        for item in overlay.get("semantic_facts", [])
        if isinstance(item, Mapping)
    }
    recipe_items = [
        item for item in recipes.get("recipes", []) if isinstance(item, Mapping)
    ]
    groups: dict[str, list[Mapping[str, Any]]] = collections.defaultdict(list)
    for recipe in recipe_items:
        candidate = candidates_by_id.get(str(recipe.get("frontier_candidate_id")))
        if not isinstance(candidate, Mapping):
            audit.failed(
                "recipe.semantic_closure",
                f"recipe {recipe.get('recipe_id')} has no frontier candidate",
            )
            continue
        hyperedge = recipe.get("action_hyperedge")
        if not isinstance(hyperedge, Mapping):
            audit.failed("recipe.hyperedge", f"recipe {recipe.get('recipe_id')} has no hyperedge")
            continue
        action_ids = hyperedge.get("action_ids")
        if (
            not isinstance(action_ids, list)
            or not action_ids
            or action_ids != sorted(set(action_ids))
            or hyperedge.get("indivisible") is not True
            or any(action_id not in actions for action_id in action_ids)
        ):
            audit.failed(
                "recipe.hyperedge",
                f"recipe {recipe.get('recipe_id')} has an unclosed action hyperedge",
            )
            continue
        mutation_ids = [
            item.get("action_id")
            for item in recipe.get("action_mutations", [])
            if isinstance(item, Mapping)
        ]
        if sorted(mutation_ids) != action_ids or len(mutation_ids) != len(set(mutation_ids)):
            audit.failed(
                "recipe.hyperedge",
                f"recipe {recipe.get('recipe_id')} mutation ledger differs from its indivisible hyperedge",
            )
        query = recipe.get("solver_query")
        query_sha = query.get("query_sha256") if isinstance(query, Mapping) else None
        material = "\0".join(
            (
                str(candidate.get("candidate_id")),
                str(candidate.get("cone_id")),
                str(candidate.get("ap_id")),
                str(query_sha),
                *[str(action_id) for action_id in action_ids],
            )
        )
        expected_recipe_id = stable_semantic_id("recipe", material)
        if (
            recipe.get("recipe_id") != expected_recipe_id
            or recipe.get("cone_id") != candidate.get("cone_id")
            or recipe.get("ap_id") != candidate.get("ap_id")
        ):
            audit.failed(
                "recipe.content_id",
                f"recipe {recipe.get('recipe_id')} ID is not candidate/query/hyperedge bound",
            )
        claim = hyperedge.get("claim")
        if claim == "SINGLE_ACTION":
            expected_hyperedge = stable_semantic_id("action-hyperedge", str(action_ids[0]))
            if len(action_ids) != 1 or hyperedge.get("hyperedge_id") != expected_hyperedge:
                audit.failed(
                    "recipe.hyperedge",
                    f"single-action recipe {recipe.get('recipe_id')} has a noncanonical hyperedge ID",
                )
        elif claim in {"JOINT_REQUIRED", "JOINT_UNKNOWN"}:
            if len(action_ids) < 2:
                audit.failed(
                    "recipe.hyperedge",
                    f"joint recipe {recipe.get('recipe_id')} is not n-ary",
                )
            groups[str(hyperedge.get("hyperedge_id"))].append(recipe)
        else:
            audit.failed(
                "recipe.hyperedge",
                f"recipe {recipe.get('recipe_id')} has an unknown joint claim",
            )
        expected_model = _expected_model_prerequisites(
            candidate, facts, attachments, actions
        )
        expected_control = _control_prerequisite_candidates(
            candidate, candidates, graph, actions
        )
        expected_choices = {**expected_model, **expected_control}
        actual_choices = {
            str(item.get("choice_id")): item
            for item in recipe.get("prerequisite_choices", [])
            if isinstance(item, Mapping)
        }
        if actual_choices != expected_choices:
            audit.failed(
                "recipe.prerequisite_closure",
                f"recipe {recipe.get('recipe_id')} prerequisite DAG differs from model/control evidence",
            )
        timing = recipe.get("timing")
        if isinstance(timing, Mapping) and timing.get("status") == "EXACT":
            evidence = candidate.get("evidence", {})
            model_provenance = evidence.get("model_provenance", {}) if isinstance(evidence, Mapping) else {}
            candidate_fact_ids = set(model_provenance.get("model_fact_ids", [])) if isinstance(model_provenance, Mapping) else set()
            witnessed_clock_ids: set[str] = set()
            graph_nodes = {
                item.get("node_id"): item
                for item in graph.get("nodes", [])
                if isinstance(item, Mapping)
            }
            for witness in candidate.get("witnesses", []):
                if not isinstance(witness, Mapping) or witness.get("compatibility") != "COMPATIBLE":
                    continue
                witness_ids = set(witness.get("model_fact_ids", []))
                for path in witness.get("path_exemplars", []):
                    if not isinstance(path, Mapping) or path.get("compatibility") != "COMPATIBLE":
                        continue
                    for step in path.get("forward_steps", []):
                        if not isinstance(step, Mapping) or step.get("kind") != "MODEL_ARC":
                            continue
                        fact_id = step.get("model_fact_id")
                        fact = facts.get(str(fact_id))
                        source = graph_nodes.get(step.get("source_node_id"))
                        target = graph_nodes.get(step.get("target_node_id"))
                        if (
                            fact_id in witness_ids
                            and fact_id in candidate_fact_ids
                            and isinstance(fact, Mapping)
                            and fact.get("kind") == "clock_relation"
                            and isinstance(source, Mapping)
                            and isinstance(target, Mapping)
                            and source.get("semantic_node_ref") == fact.get("source_semantic_node_id")
                            and target.get("semantic_node_ref") == fact.get("target_semantic_node_id")
                        ):
                            witnessed_clock_ids.add(str(fact_id))
            if len(witnessed_clock_ids) != 1:
                audit.failed(
                    "recipe.timing_closure",
                    f"recipe {recipe.get('recipe_id')} EXACT timing lacks a unique witness-bound clock fact",
                )
            else:
                fact = facts[next(iter(witnessed_clock_ids))]
                clock = fact.get("clock_relation")
                action = candidate.get("action", {})
                expected_timing = {
                    "clock_source": clock.get("clock_source"),
                    "unit": clock.get("unit"),
                    "epoch": clock.get("epoch"),
                    "quantum": clock.get("quantum"),
                    "jitter": clock.get("jitter"),
                    "wrap": clock.get("wrap")
                    + (":" + str(clock.get("wrap_value")) if clock.get("wrap_value") is not None else ""),
                    "comparison_endpoint": str(clock.get("endpoint")).upper(),
                    "start_event": clock.get("start_event"),
                    "end_event": clock.get("end_event"),
                    "scope_schema": clock.get("scope_schema"),
                    "generation_schema": clock.get("generation_schema"),
                }
                if (
                    fact.get("certainty") != "modelled"
                    or any(timing.get(key) != value for key, value in expected_timing.items())
                    or clock.get("scope_schema") != action.get("scope_schema")
                    or clock.get("generation_schema") != action.get("generation_schema")
                    or timing.get("uncertainty_reasons") != []
                ):
                    audit.failed(
                        "recipe.timing_closure",
                        f"recipe {recipe.get('recipe_id')} EXACT timing differs from its typed clock witness",
                    )
        for mutation in recipe.get("action_mutations", []):
            if (
                isinstance(mutation, Mapping)
                and mutation.get("mutation_kind") != "UNKNOWN"
                and not _candidate_has_identity_boundary_witness(candidate, {
                    str(item.get("attachment_id")): item for item in attachments
                })
            ):
                audit.failed(
                    "recipe.value_transfer_closure",
                    f"recipe {recipe.get('recipe_id')} claims an external value mutation without a typed identity boundary witness",
                )
                break

    joint_requirements: list[tuple[str, bool, list[str], list[str], list[str]]] = []
    for hyperedge_id, group in sorted(groups.items()):
        claims = {item.get("action_hyperedge", {}).get("claim") for item in group}
        action_sets = {
            tuple(item.get("action_hyperedge", {}).get("action_ids", []))
            for item in group
        }
        if len(claims) != 1 or len(action_sets) != 1:
            audit.failed(
                "recipe.joint_closure",
                f"joint hyperedge {hyperedge_id} is inconsistent across member recipes",
            )
            continue
        claim = next(iter(claims))
        action_ids = list(next(iter(action_sets)))
        candidate_ids = sorted(
            str(item.get("frontier_candidate_id")) for item in group
        )
        if set(candidate_ids) != {
            candidate_id
            for candidate_id, candidate in candidates_by_id.items()
            if candidate.get("disposition") == "ACTIONABLE"
            and candidate.get("action", {}).get("external_action_id") in action_ids
            and candidate.get("ap_id") == group[0].get("ap_id")
        }:
            audit.failed(
                "recipe.joint_closure",
                f"joint hyperedge {hyperedge_id} does not account for every participating actionable candidate",
            )
        matches = _joint_requirement_candidates(
            group, candidates_by_id, property_ir, overlay
        )
        matched: tuple[str, list[str], bool] | None = None
        for requirement_id, fact_ids, complete in matches:
            material = requirement_id
            for action_id in action_ids:
                material += "\0" + str(action_id)
            if stable_semantic_id("action-hyperedge", material) == hyperedge_id:
                matched = (requirement_id, fact_ids, complete)
                break
        if matched is None:
            audit.failed(
                "recipe.joint_closure",
                f"joint hyperedge {hyperedge_id} has no source-AND or typed ALL_REQUIRED derivation",
            )
            continue
        requirement_id, fact_ids, complete = matched
        if (claim == "JOINT_REQUIRED") != complete:
            audit.failed(
                "recipe.joint_closure",
                f"joint hyperedge {hyperedge_id} overclaims or hides evidence completeness",
            )
        if claim == "JOINT_REQUIRED" and (
            any(item.get("solver_query", {}).get("outcome") != "SAT" for item in group)
            or len({item.get("solver_query", {}).get("query_sha256") for item in group}) != 1
        ):
            audit.failed(
                "recipe.joint_closure",
                f"joint hyperedge {hyperedge_id} lacks one shared SAT multi-input certificate",
            )
        if claim == "JOINT_UNKNOWN" and any(item.get("status") != "UNKNOWN" for item in group):
            audit.failed(
                "recipe.joint_closure",
                f"unknown joint hyperedge {hyperedge_id} is exposed as actionable",
            )
        joint_requirements.append(
            (requirement_id, complete, candidate_ids, action_ids, fact_ids)
        )

    # Recompute every *closed* source-visible AND independently of the emitted
    # hyperedges.  This is what catches a coherent split where a tamperer also
    # rewrites both mutation ledgers and the recipe artifact ID.
    aps = {
        item.get("ap_id"): item
        for item in property_ir.get("atomic_propositions", [])
        if isinstance(item, Mapping)
    }
    attachment_map = {
        str(item.get("attachment_id")): item for item in attachments
    }
    for ap_id, ap in aps.items():
        for selectors, explicit_conjunction in _predicate_action_branches(
            ap.get("predicate")
        ):
            if not explicit_conjunction or len(selectors) < 2:
                continue
            branch_recipes = [
                item
                for item in recipe_items
                if item.get("ap_id") == ap_id
                and item.get("target_predicate_selector_id") in selectors
            ]
            if {
                item.get("target_predicate_selector_id")
                for item in branch_recipes
            } != selectors:
                continue
            branch_candidates = [
                candidates_by_id.get(str(item.get("frontier_candidate_id")))
                for item in branch_recipes
            ]
            if any(not isinstance(item, Mapping) for item in branch_candidates):
                continue
            typed_candidates = [
                item for item in branch_candidates if isinstance(item, Mapping)
            ]
            action_for_selector = {
                recipe.get("target_predicate_selector_id"): candidate.get(
                    "action", {}
                ).get("external_action_id")
                for recipe, candidate in zip(branch_recipes, typed_candidates)
            }
            action_ids = sorted(set(action_for_selector.values()))
            closed = (
                len(action_for_selector) == len(selectors)
                and len(action_ids) == len(selectors)
                and all(_candidate_closed(item) for item in typed_candidates)
                and all(
                    _candidate_has_identity_boundary_witness(
                        item, attachment_map
                    )
                    for item in typed_candidates
                )
                and len(
                    {
                        item.get("action", {}).get("scope_schema")
                        for item in typed_candidates
                    }
                )
                == 1
                and len(
                    {
                        item.get("action", {}).get("generation_schema")
                        for item in typed_candidates
                    }
                )
                == 1
            )
            if not closed:
                continue
            material = "typed-source-conjunction\0" + str(ap_id)
            for selector in sorted(selectors):
                material += "\0" + str(selector)
            for action_id in action_ids:
                material += "\0" + str(action_id)
            requirement_id = stable_semantic_id("joint-source", material)
            hyperedge_material = requirement_id
            for action_id in action_ids:
                hyperedge_material += "\0" + str(action_id)
            expected_hyperedge_id = stable_semantic_id(
                "action-hyperedge", hyperedge_material
            )
            for recipe in branch_recipes:
                hyperedge = recipe.get("action_hyperedge", {})
                if (
                    hyperedge.get("hyperedge_id") != expected_hyperedge_id
                    or hyperedge.get("action_ids") != action_ids
                    or hyperedge.get("claim") != "JOINT_REQUIRED"
                ):
                    audit.failed(
                        "recipe.joint_closure",
                        f"closed source AND {ap_id} was split or downgraded",
                    )
                    break
            joint_requirements.append(
                (
                    requirement_id,
                    True,
                    sorted(
                        str(item.get("candidate_id"))
                        for item in typed_candidates
                    ),
                    action_ids,
                    [],
                )
            )
    recipes_by_candidate = {
        str(item.get("frontier_candidate_id")): item
        for item in recipe_items
    }
    for constraint in overlay.get("joint_action_constraints", []):
        if (
            not isinstance(constraint, Mapping)
            or constraint.get("combination") != "all_required"
            or constraint.get("participant_set_complete") is not True
            or constraint.get("certainty") != "modelled"
        ):
            continue
        participants = set(
            constraint.get("participant_semantic_node_ids", [])
        )
        for ap_id in aps:
            member_pairs: list[
                tuple[Mapping[str, Any], Mapping[str, Any]]
            ] = []
            covered: set[str] = set()
            for candidate_id, candidate in candidates_by_id.items():
                if (
                    candidate.get("disposition") != "ACTIONABLE"
                    or candidate.get("ap_id") != ap_id
                    or candidate_id not in recipes_by_candidate
                ):
                    continue
                candidate_participants: set[str] = set()
                for witness in candidate.get("witnesses", []):
                    if (
                        not isinstance(witness, Mapping)
                        or witness.get("compatibility") != "COMPATIBLE"
                    ):
                        continue
                    attachment = attachment_map.get(
                        str(witness.get("attachment_id"))
                    )
                    if (
                        isinstance(attachment, Mapping)
                        and attachment.get("semantic_node_id")
                        in participants
                    ):
                        candidate_participants.add(
                            str(attachment["semantic_node_id"])
                        )
                if candidate_participants:
                    covered.update(candidate_participants)
                    member_pairs.append(
                        (candidate, recipes_by_candidate[candidate_id])
                    )
            action_ids = sorted(
                {
                    candidate.get("action", {}).get("external_action_id")
                    for candidate, _ in member_pairs
                }
            )
            selectors = {
                recipe.get("target_predicate_selector_id")
                for _, recipe in member_pairs
                if isinstance(
                    recipe.get("target_predicate_selector_id"), str
                )
            }
            closed = (
                covered == participants
                and len(action_ids) >= 2
                and len(selectors) == len(action_ids)
                and all(
                    _candidate_closed(candidate)
                    and _candidate_has_identity_boundary_witness(
                        candidate, attachment_map
                    )
                    and candidate.get("action", {}).get("scope_schema")
                    == constraint.get("scope_schema")
                    and candidate.get("action", {}).get(
                        "generation_schema"
                    )
                    == constraint.get("generation_schema")
                    for candidate, _ in member_pairs
                )
            )
            if not closed:
                continue
            requirement_id = stable_semantic_id(
                "joint-model",
                str(constraint.get("constraint_id"))
                + "\0"
                + str(ap_id),
            )
            hyperedge_material = requirement_id
            for action_id in action_ids:
                hyperedge_material += "\0" + str(action_id)
            expected_hyperedge_id = stable_semantic_id(
                "action-hyperedge", hyperedge_material
            )
            for _, recipe in member_pairs:
                hyperedge = recipe.get("action_hyperedge", {})
                if (
                    hyperedge.get("hyperedge_id")
                    != expected_hyperedge_id
                    or hyperedge.get("action_ids") != action_ids
                    or hyperedge.get("claim") != "JOINT_REQUIRED"
                ):
                    audit.failed(
                        "recipe.joint_closure",
                        f"closed typed ALL_REQUIRED {constraint.get('constraint_id')} was split or downgraded for {ap_id}",
                    )
                    break
            joint_requirements.append(
                (
                    requirement_id,
                    True,
                    sorted(
                        str(candidate.get("candidate_id"))
                        for candidate, _ in member_pairs
                    ),
                    action_ids,
                    [str(constraint.get("constraint_id"))],
                )
            )

    contract = recipes.get("solver_contract")
    if isinstance(contract, Mapping):
        material = "\0".join(
            (
                str(recipes.get("property_ir_sha256")),
                str(recipes.get("ap_bindings_sha256")),
                str(recipes.get("graph_sha256")),
                str(recipes.get("cones_sha256")),
                str(recipes.get("frontier_candidates_sha256")),
                str(recipes.get("model_fact_overlay_sha256")),
                str(recipes.get("predicate_occurrence_bindings_sha256")),
                str(recipes.get("analyzer_core_sha256")),
                str(contract.get("solver_version")),
                str(contract.get("timeout_ms")),
                str(contract.get("max_queries")),
            )
        )
        unique_requirements = {
            item[0]: item for item in joint_requirements
        }
        for requirement_id, complete, candidate_ids, action_ids, fact_ids in sorted(
            unique_requirements.values(),
            key=lambda item: (item[0], item[3], item[2]),
        ):
            material += "\0" + requirement_id
            material += "\0complete" if complete else "\0unknown"
            for candidate_id in sorted(set(candidate_ids)):
                material += "\0" + candidate_id
            for action_id in sorted(set(action_ids)):
                material += "\0" + action_id
            for fact_id in sorted(set(fact_ids)):
                material += "\0" + fact_id
        expected_artifact_id = stable_semantic_id("mutation-recipes", material)
        if recipes.get("artifact_id") != expected_artifact_id:
            audit.failed(
                "recipe.artifact_id",
                "mutation recipe artifact ID does not bind inputs and automatic joint requirements",
            )
    if audit.failures == starting_failures:
        audit.passed(
            "recipe.semantic_closure",
            "recipe IDs, typed hyperedges, prerequisites and timing independently close",
        )


def _equivalent_occurrence_value_type(left: Any, right: Any) -> bool:
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return False
    if any(
        left.get(key) != right.get(key)
        for key in ("kind", "bit_width", "signed", "unit")
    ):
        return False
    if left.get("canonical") == right.get("canonical"):
        return True
    return (
        left.get("kind") in INTEGER_ALIAS_KINDS
        and isinstance(left.get("bit_width"), int)
        and isinstance(left.get("signed"), bool)
    )


def _predicate_reference_evidence(
    expression: Any,
    path: str,
    output: dict[str, dict[str, list[Any]]],
) -> None:
    if not isinstance(expression, Mapping):
        return
    selector_id = expression.get("referenced_selector_id")
    if expression.get("node_kind") == "reference" and isinstance(selector_id, str):
        evidence = output.setdefault(
            selector_id, {"paths": [], "types": [], "operators": []}
        )
        evidence["paths"].append(path)
        value_type = expression.get("value_type")
        if value_type not in evidence["types"]:
            evidence["types"].append(value_type)
        operator = expression.get("operator")
        if isinstance(operator, str) and operator not in evidence["operators"]:
            evidence["operators"].append(operator)
    operands = expression.get("operands", [])
    if not isinstance(operands, list):
        return
    for index, operand in enumerate(operands):
        _predicate_reference_evidence(
            operand, f"{path}.operands[{index}]", output
        )


def _verify_occurrence_type_closure(
    property_ir: Mapping[str, Any],
    bindings: Mapping[str, Any],
    audit: Audit,
) -> None:
    """Independently close Property selector/reference/Clang occurrence types."""

    starting_failures = audit.failures
    selectors = {
        item.get("selector_id"): item
        for item in property_ir.get("selectors", [])
        if isinstance(item, Mapping) and isinstance(item.get("selector_id"), str)
    }
    expected: dict[tuple[str, str], tuple[Any, bool]] = {}
    for ap in property_ir.get("atomic_propositions", []):
        if not isinstance(ap, Mapping) or not isinstance(ap.get("ap_id"), str):
            continue
        references: dict[str, dict[str, list[Any]]] = {}
        _predicate_reference_evidence(
            ap.get("predicate"), "predicate", references
        )
        for selector_id, evidence in references.items():
            selector = selectors.get(selector_id)
            if (
                not isinstance(selector, Mapping)
                or selector.get("kind") != "source_location"
                or not isinstance(selector.get("location"), Mapping)
            ):
                continue
            selector_type = selector.get("value_type")
            reference_types = evidence["types"]
            expected_type = (
                selector_type
                if isinstance(selector_type, Mapping)
                else reference_types[0]
                if reference_types
                else {"kind": "unknown", "canonical": "unknown"}
            )
            closed = (
                isinstance(selector_type, Mapping)
                and bool(reference_types)
                and selector_type.get("kind") != "unknown"
                and selector_type.get("canonical") not in (None, "", "unknown")
                and all(
                    _equivalent_occurrence_value_type(
                        reference_types[0], candidate
                    )
                    for candidate in reference_types
                )
                and _equivalent_occurrence_value_type(
                    selector_type, reference_types[0]
                )
            )
            expected[(str(ap["ap_id"]), selector_id)] = (
                expected_type,
                closed,
            )

    accounts: dict[tuple[str, str], Mapping[str, Any]] = {}
    for account in bindings.get("selector_accounts", []):
        if not isinstance(account, Mapping):
            continue
        key = (account.get("ap_id"), account.get("selector_id"))
        if not all(isinstance(item, str) for item in key):
            continue
        if key in accounts:
            audit.failed(
                "occurrence.type_closure", f"duplicate selector account {key}"
            )
            continue
        accounts[key] = account
        evidence = expected.get(key)
        if evidence is None:
            audit.failed(
                "occurrence.type_closure",
                f"selector account {key} has no source-location predicate reference",
            )
            continue
        expected_type, closed = evidence
        if account.get("expected_value_type") != expected_type:
            audit.failed(
                "occurrence.type_closure",
                f"selector account {key} expected type differs from Property IR",
            )
        if account.get("resolution") == "EXACT" and not closed:
            audit.failed(
                "occurrence.type_closure",
                f"selector account {key} claims EXACT with an unclosed Property type",
            )
    for key in sorted(set(expected) - set(accounts)):
        audit.failed(
            "occurrence.type_closure",
            f"source-location predicate reference {key} has no selector account",
        )

    occurrence_by_id: dict[str, Mapping[str, Any]] = {}
    occurrence_ids_by_account: dict[tuple[Any, Any], list[str]] = {}
    for occurrence in bindings.get("occurrences", []):
        if not isinstance(occurrence, Mapping):
            continue
        key = (occurrence.get("ap_id"), occurrence.get("selector_id"))
        occurrence_id = occurrence.get("occurrence_id")
        if isinstance(occurrence_id, str):
            if occurrence_id in occurrence_by_id:
                audit.failed(
                    "occurrence.type_closure",
                    f"duplicate predicate occurrence ID {occurrence_id}",
                )
            occurrence_by_id[occurrence_id] = occurrence
            occurrence_ids_by_account.setdefault(key, []).append(occurrence_id)
        account = accounts.get(key)
        if occurrence.get("resolution") != "EXACT":
            continue
        if account is None or account.get("resolution") != "EXACT":
            audit.failed(
                "occurrence.type_closure",
                f"EXACT occurrence {occurrence.get('occurrence_id')} lacks an EXACT account",
            )
        elif not _equivalent_occurrence_value_type(
            account.get("expected_value_type"), occurrence.get("value_type")
        ):
            audit.failed(
                "occurrence.type_closure",
                f"EXACT occurrence {occurrence.get('occurrence_id')} violates its expected type",
            )
    for key, account in accounts.items():
        declared_ids = account.get("occurrence_ids", [])
        observed_ids = occurrence_ids_by_account.get(key, [])
        if not isinstance(declared_ids, list) or sorted(declared_ids) != sorted(
            observed_ids
        ):
            audit.failed(
                "occurrence.type_closure",
                f"selector account {key} occurrence ledger does not match observed occurrences",
            )
            continue
        linked = [occurrence_by_id.get(item) for item in declared_ids]
        if any(item is None for item in linked):
            audit.failed(
                "occurrence.type_closure",
                f"selector account {key} references an absent occurrence",
            )
        if account.get("resolution") == "EXACT" and (
            len(linked) != 1
            or linked[0] is None
            or linked[0].get("resolution") != "EXACT"
        ):
            audit.failed(
                "occurrence.type_closure",
                f"EXACT selector account {key} is not backed by one EXACT occurrence",
            )
    if audit.failures == starting_failures:
        audit.passed(
            "occurrence.type_closure",
            f"Property/selector/Clang type closure holds for {len(expected)} predicate references",
        )


def _normalized_source_file(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    result = value.replace("\\", "/")
    while result.startswith("./"):
        result = result[2:]
    while len(result) > 1 and result.endswith("/"):
        result = result[:-1]
    return result


def _path_suffix_match(left: Any, right: Any) -> bool:
    normalized_left = _normalized_source_file(left)
    normalized_right = _normalized_source_file(right)
    if normalized_left is None or normalized_right is None:
        return False
    return normalized_left == normalized_right or (
        bool(normalized_right)
        and len(normalized_left) > len(normalized_right)
        and normalized_left.endswith("/" + normalized_right)
    )


def _canonical_requested_location(location: Any) -> tuple[Any, ...] | None:
    if not isinstance(location, Mapping):
        return None
    return (
        _normalized_source_file(location.get("file")),
        location.get("line"),
        location.get("column"),
        location.get("end_line", 0),
        location.get("end_column", 0),
        location.get("location_kind"),
        tuple(location.get("macro_stack", [])),
    )


def _location_material(location: Mapping[str, Any]) -> str:
    return (
        f"{_normalized_source_file(location.get('file'))}:"
        f"{location.get('line')}:{location.get('column')}:"
        f"{location.get('location_kind')}"
    )


def _location_contains(range_location: Any, point_location: Any) -> bool:
    if not isinstance(range_location, Mapping) or not isinstance(
        point_location, Mapping
    ):
        return False
    if _normalized_source_file(range_location.get("file")) != (
        _normalized_source_file(point_location.get("file"))
    ):
        return False
    line = range_location.get("line")
    column = range_location.get("column")
    point_line = point_location.get("line")
    point_column = point_location.get("column")
    if not all(
        isinstance(value, int)
        for value in (line, column, point_line, point_column)
    ):
        return False
    end_line = range_location.get("end_line", 0) or line
    end_column = range_location.get("end_column", 0) or column
    return (line, column) <= (point_line, point_column) <= (
        end_line,
        end_column,
    )


def _access_path_material(access_path: Any) -> str:
    if not isinstance(access_path, Mapping):
        return "no-access-path"
    material = (
        f"{access_path.get('root_entity_id')}|d="
        f"{access_path.get('dereference_depth')}"
    )
    for field_id in access_path.get("fields", []):
        material += f"|f={field_id}"
    material += f"|u={int(access_path.get('unknown_suffix') is True)}"
    return material


def _predicate_occurrence_id(occurrence: Mapping[str, Any]) -> str | None:
    spelling = occurrence.get("spelling_location")
    expansion = occurrence.get("expansion_location")
    if not isinstance(spelling, Mapping) or not isinstance(expansion, Mapping):
        return None
    required = (
        occurrence.get("ap_id"),
        occurrence.get("selector_id"),
        occurrence.get("translation_unit_id"),
        occurrence.get("kind"),
    )
    if not all(isinstance(value, str) for value in required):
        return None
    material = "\0".join(
        (
            *required,
            _location_material(spelling),
            _location_material(expansion),
            occurrence.get("referenced_usr") or "unknown",
            _access_path_material(occurrence.get("access_path")),
            occurrence.get("member_abstract_object_id") or "no-object",
        )
    )
    return stable_semantic_id("predicate-occurrence", material)


def _roles_for_property_selector(
    atomic_proposition: Mapping[str, Any], selector_id: str
) -> list[str]:
    groups = atomic_proposition.get("role_selector_groups", [])
    roles: set[str] = set()
    if isinstance(groups, list) and groups:
        for group in groups:
            if not isinstance(group, Mapping):
                continue
            selectors = group.get("all_of", [])
            role = group.get("role")
            if (
                isinstance(selectors, list)
                and selector_id in selectors
                and isinstance(role, str)
            ):
                roles.add(role)
    elif selector_id in atomic_proposition.get("selector_refs", []):
        roles.update(
            role
            for role in atomic_proposition.get("roles", [])
            if isinstance(role, str)
        )
    return sorted(roles)


def _verify_occurrence_semantic_closure(
    property_ir: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    bindings: Mapping[str, Any],
    audit: Audit,
) -> None:
    """Close occurrence claims against Property IR and the immutable M4 index."""

    starting_failures = audit.failures
    selectors = {
        item.get("selector_id"): item
        for item in property_ir.get("selectors", [])
        if isinstance(item, Mapping) and isinstance(item.get("selector_id"), str)
    }
    expected_accounts: dict[tuple[str, str], dict[str, Any]] = {}
    for ap in property_ir.get("atomic_propositions", []):
        if not isinstance(ap, Mapping) or not isinstance(ap.get("ap_id"), str):
            continue
        references: dict[str, dict[str, list[Any]]] = {}
        _predicate_reference_evidence(ap.get("predicate"), "predicate", references)
        for selector_id, evidence in references.items():
            selector = selectors.get(selector_id)
            if (
                not isinstance(selector, Mapping)
                or selector.get("kind") != "source_location"
                or not isinstance(selector.get("location"), Mapping)
            ):
                continue
            expected_accounts[(str(ap["ap_id"]), selector_id)] = {
                "roles": _roles_for_property_selector(ap, selector_id),
                "predicate_paths": sorted(set(evidence["paths"])),
                "operators": sorted(set(evidence["operators"])),
                "requested_location": selector["location"],
            }

    entities: dict[str, Mapping[str, Any]] = {}
    entities_by_usr: dict[str, list[str]] = {}
    for wrapper in semantic_index.get("entities", []):
        if not isinstance(wrapper, Mapping):
            continue
        entity = wrapper.get("entity")
        if not isinstance(entity, Mapping) or not isinstance(
            entity.get("entity_id"), str
        ):
            continue
        entity_id = str(entity["entity_id"])
        if entity_id in entities:
            audit.failed(
                "occurrence.semantic_closure",
                f"duplicate semantic entity ID {entity_id}",
            )
            continue
        entities[entity_id] = wrapper
        usr = entity.get("usr")
        if isinstance(usr, str):
            entities_by_usr.setdefault(usr, []).append(entity_id)
    for entity_ids in entities_by_usr.values():
        entity_ids.sort()

    nodes: dict[str, Mapping[str, Any]] = {}
    for node in semantic_index.get("semantic_nodes", []):
        if not isinstance(node, Mapping) or not isinstance(node.get("node_id"), str):
            continue
        node_id = str(node["node_id"])
        if node_id in nodes:
            audit.failed(
                "occurrence.semantic_closure",
                f"duplicate semantic node ID {node_id}",
            )
        else:
            nodes[node_id] = node
    abstract_objects = {
        item.get("object_id")
        for item in semantic_index.get("abstract_objects", [])
        if isinstance(item, Mapping) and isinstance(item.get("object_id"), str)
    }
    translation_units = {
        item.get("tu_id")
        for item in semantic_index.get("translation_units", [])
        if isinstance(item, Mapping) and isinstance(item.get("tu_id"), str)
    }

    accounts: dict[tuple[str, str], Mapping[str, Any]] = {}
    eligible_union: set[str] = set()
    parsed_union: set[str] = set()
    for account in bindings.get("selector_accounts", []):
        if not isinstance(account, Mapping):
            continue
        key = (account.get("ap_id"), account.get("selector_id"))
        if not all(isinstance(value, str) for value in key):
            continue
        typed_key = (str(key[0]), str(key[1]))
        accounts[typed_key] = account
        expected = expected_accounts.get(typed_key)
        if expected is None:
            continue
        for field in ("roles", "predicate_paths"):
            actual = account.get(field, [])
            if not isinstance(actual, list) or sorted(actual) != expected[field]:
                audit.failed(
                    "occurrence.semantic_closure",
                    f"selector account {typed_key} {field} differs from Property IR structure",
                )
        if _canonical_requested_location(account.get("requested_location")) != (
            _canonical_requested_location(expected["requested_location"])
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"selector account {typed_key} requested location differs from Property IR",
            )
        eligible = account.get("eligible_translation_unit_ids", [])
        parsed = account.get("parsed_translation_unit_ids", [])
        if not isinstance(eligible, list) or not isinstance(parsed, list):
            continue
        eligible_set = {item for item in eligible if isinstance(item, str)}
        parsed_set = {item for item in parsed if isinstance(item, str)}
        eligible_union.update(eligible_set)
        parsed_union.update(parsed_set)
        if not parsed_set <= eligible_set:
            audit.failed(
                "occurrence.semantic_closure",
                f"selector account {typed_key} parsed a non-eligible translation unit",
            )
        if any(item not in translation_units for item in eligible_set):
            audit.failed(
                "occurrence.semantic_closure",
                f"selector account {typed_key} references an absent translation unit",
            )
        if account.get("resolution") == "EXACT" and (
            not expected["roles"] or account.get("uncertainty_reasons") != []
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"EXACT selector account {typed_key} lacks closed role/evidence state",
            )

    if bindings.get("eligible_translation_units") != len(eligible_union):
        audit.failed(
            "occurrence.semantic_closure",
            "eligible translation-unit counter does not match selector accounts",
        )
    if bindings.get("parsed_translation_units") != len(parsed_union):
        audit.failed(
            "occurrence.semantic_closure",
            "parsed translation-unit counter does not match selector accounts",
        )
    if bindings.get("skipped_translation_units") != len(
        eligible_union - parsed_union
    ):
        audit.failed(
            "occurrence.semantic_closure",
            "skipped translation-unit counter does not match selector accounts",
        )
    occurrences = [
        item for item in bindings.get("occurrences", []) if isinstance(item, Mapping)
    ]
    if bindings.get("observed_occurrences") != len(occurrences):
        audit.failed(
            "occurrence.semantic_closure",
            "observed occurrence counter does not match the occurrence ledger",
        )

    for occurrence in occurrences:
        occurrence_id = occurrence.get("occurrence_id")
        key = (occurrence.get("ap_id"), occurrence.get("selector_id"))
        account = accounts.get(key) if all(isinstance(x, str) for x in key) else None
        expected = (
            expected_accounts.get((str(key[0]), str(key[1])))
            if all(isinstance(x, str) for x in key)
            else None
        )
        if not isinstance(account, Mapping) or expected is None:
            continue
        for field in ("roles", "predicate_paths"):
            actual = occurrence.get(field, [])
            if not isinstance(actual, list) or sorted(actual) != sorted(
                account.get(field, [])
            ):
                audit.failed(
                    "occurrence.semantic_closure",
                    f"occurrence {occurrence_id} {field} differs from its selector account",
                )
        operators = expected["operators"]
        occurrence_kind = occurrence.get("kind")
        def operator_accepts(operator: Any) -> bool:
            if operator == "decl_ref_or_member":
                return occurrence_kind in {"decl_ref", "member_expr"}
            return operator == occurrence_kind

        if operators and not any(operator_accepts(operator) for operator in operators):
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} AST kind differs from Property IR reference",
            )
        recomputed_id = _predicate_occurrence_id(occurrence)
        if recomputed_id != occurrence_id:
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} identity is not derived from its semantic fields",
            )

        requested = account.get("requested_location", {})
        location_kind = (
            requested.get("location_kind")
            if isinstance(requested, Mapping)
            else None
        )
        selected = occurrence.get(
            "expansion_location"
            if location_kind == "expansion"
            else "spelling_location"
        )
        spelling = occurrence.get("spelling_location")
        expansion = occurrence.get("expansion_location")
        if (
            not isinstance(spelling, Mapping)
            or spelling.get("location_kind") != "spelling"
            or not isinstance(expansion, Mapping)
            or expansion.get("location_kind") != "expansion"
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} spelling/expansion location kinds are invalid",
            )
        if not isinstance(selected, Mapping) or not (
            _path_suffix_match(selected.get("file"), requested.get("file"))
            and selected.get("line") == requested.get("line")
            and selected.get("column") == requested.get("column")
            and selected.get("location_kind") == location_kind
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} source location does not satisfy its selector",
            )
        if occurrence.get("resolution") == "EXACT" and (
            not isinstance(spelling, Mapping)
            or not isinstance(expansion, Mapping)
            or spelling.get("macro_stack", []) != []
            or expansion.get("macro_stack", []) != []
            or (
                _normalized_source_file(spelling.get("file")),
                spelling.get("line"),
                spelling.get("column"),
                spelling.get("end_line", 0),
                spelling.get("end_column", 0),
            )
            != (
                _normalized_source_file(expansion.get("file")),
                expansion.get("line"),
                expansion.get("column"),
                expansion.get("end_line", 0),
                expansion.get("end_column", 0),
            )
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"EXACT occurrence {occurrence_id} carries unresolved macro location evidence",
            )

        translation_unit_id = occurrence.get("translation_unit_id")
        if translation_unit_id not in translation_units:
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} references an absent translation unit",
            )
        if translation_unit_id not in account.get(
            "parsed_translation_unit_ids", []
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} was not emitted by an accounted parsed translation unit",
            )

        usr = occurrence.get("referenced_usr")
        entity_id = occurrence.get("referenced_entity_id")
        matching_entities = entities_by_usr.get(usr, []) if isinstance(usr, str) else []
        expected_entity = matching_entities[0] if len(matching_entities) == 1 else None
        if entity_id != expected_entity:
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} entity does not uniquely follow from its USR",
            )
        entity_wrapper = entities.get(entity_id) if isinstance(entity_id, str) else None
        if isinstance(entity_wrapper, Mapping) and translation_unit_id not in (
            entity_wrapper.get("translation_unit_refs", [])
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} entity is not present in its translation unit",
            )

        occurrence_kind = occurrence.get("kind")
        access_path = occurrence.get("access_path")
        candidate_nodes: list[str] = []
        if occurrence_kind == "decl_ref" and isinstance(entity_id, str):
            if access_path is not None or any(
                occurrence.get(field) is not None
                for field in ("member_base_entity_id", "member_abstract_object_id")
            ):
                audit.failed(
                    "occurrence.semantic_closure",
                    f"DeclRef occurrence {occurrence_id} carries member-only identity",
                )
            for node_id, node in nodes.items():
                node_path = node.get("access_path")
                empty_root_path = (
                    isinstance(node_path, Mapping)
                    and node_path.get("root_entity_id") == entity_id
                    and node_path.get("fields") == []
                )
                if node.get("entity_ref") == entity_id and (
                    node_path is None or empty_root_path
                ):
                    candidate_nodes.append(node_id)
        elif occurrence_kind == "member_expr" and isinstance(access_path, Mapping):
            root_entity_id = access_path.get("root_entity_id")
            fields = access_path.get("fields", [])
            if (
                occurrence.get("member_base_entity_id") != root_entity_id
                or not isinstance(fields, list)
                or not fields
                or fields[-1] != entity_id
                or any(
                    path_entity not in entities
                    for path_entity in [root_entity_id, *fields]
                )
            ):
                audit.failed(
                    "occurrence.semantic_closure",
                    f"MemberExpr occurrence {occurrence_id} has an unclosed access path",
                )
            for node_id, node in nodes.items():
                if node.get("access_path") == access_path and _location_contains(
                    node.get("location"), selected
                ):
                    candidate_nodes.append(node_id)
            member_object = occurrence.get("member_abstract_object_id")
            if member_object is not None and member_object not in abstract_objects:
                audit.failed(
                    "occurrence.semantic_closure",
                    f"MemberExpr occurrence {occurrence_id} references an absent abstract object",
                )
        candidate_nodes.sort()
        reported_nodes = occurrence.get("semantic_node_ids", [])
        if not isinstance(reported_nodes, list) or sorted(reported_nodes) != candidate_nodes:
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} semantic-node ledger is not the M4 match set",
            )
        matching_node_types = 0
        for node_id in reported_nodes if isinstance(reported_nodes, list) else []:
            node = nodes.get(node_id)
            if not isinstance(node, Mapping):
                continue
            if _equivalent_occurrence_value_type(
                node.get("value_type"), occurrence.get("value_type")
            ):
                matching_node_types += 1
            elif occurrence.get("resolution") == "EXACT":
                audit.failed(
                    "occurrence.semantic_closure",
                    f"EXACT occurrence {occurrence_id} type differs from semantic node {node_id}",
                )
            if occurrence_kind == "member_expr" and (
                node.get("entity_ref") != access_path.get("root_entity_id")
                or (
                    occurrence.get("member_abstract_object_id") is not None
                    and node.get("abstract_object_id")
                    != occurrence.get("member_abstract_object_id")
                )
            ):
                audit.failed(
                    "occurrence.semantic_closure",
                    f"MemberExpr occurrence {occurrence_id} disagrees with semantic node {node_id}",
                )
        # For UNKNOWN/ambiguous mappings, semantic_node_ids is the complete
        # M4 candidate ledger, not a claim that every use of the referenced
        # entity has the selected AST expression's type.  At least one
        # candidate must still close over the Clang occurrence type; EXACT
        # mappings continue to require their sole candidate to agree.
        if (
            isinstance(reported_nodes, list)
            and reported_nodes
            and matching_node_types == 0
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"occurrence {occurrence_id} has no semantic-node candidate with its Clang value type",
            )
        if occurrence.get("resolution") == "EXACT" and (
            occurrence.get("certainty") != "must"
            or occurrence.get("uncertainty_reasons") != []
            or len(candidate_nodes) != 1
            or expected_entity is None
        ):
            audit.failed(
                "occurrence.semantic_closure",
                f"EXACT occurrence {occurrence_id} lacks unique closed semantic evidence",
            )

    if audit.failures == starting_failures:
        audit.passed(
            "occurrence.semantic_closure",
            f"{len(occurrences)} predicate occurrences close against Property IR and the immutable M4 index",
        )


def _topological_recipe_steps(
    recipe: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    steps: dict[str, Mapping[str, Any]] = {}
    action_ids: set[str] = set()
    for choice in recipe.get("prerequisite_choices", []):
        if not isinstance(choice, Mapping):
            return False, []
        alternatives = choice.get("alternatives", [])
        if not isinstance(alternatives, list) or len(alternatives) != 1:
            return False, []
        dag = alternatives[0]
        if not isinstance(dag, Mapping):
            return False, []
        dag_steps = dag.get("steps", [])
        if (
            dag.get("status") != "COMPLETE"
            or dag.get("uncertainty_reasons") != []
            or not isinstance(dag_steps, list)
            or not dag_steps
        ):
            return False, []
        for step in dag_steps:
            if not isinstance(step, Mapping):
                return False, []
            step_id = step.get("step_id")
            action_id = step.get("action_id")
            if (
                not isinstance(step_id, str)
                or not step_id
                or not isinstance(action_id, str)
                or not action_id
                or not isinstance(step.get("operation"), str)
                or not step.get("operation")
                or step_id in steps
                or action_id in action_ids
            ):
                return False, []
            steps[step_id] = step
            action_ids.add(action_id)
    indegree = {step_id: 0 for step_id in steps}
    successors: dict[str, list[str]] = {step_id: [] for step_id in steps}
    for step_id, step in steps.items():
        predecessors = step.get("predecessor_step_ids", [])
        if not isinstance(predecessors, list):
            return False, []
        for predecessor in predecessors:
            if predecessor not in steps:
                return False, []
            successors[predecessor].append(step_id)
            indegree[step_id] += 1
    ready = sorted(step_id for step_id, degree in indegree.items() if degree == 0)
    result: list[str] = []
    while ready:
        current = ready.pop(0)
        result.append(current)
        for successor in successors[current]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort()
    return (len(result) == len(steps), result if len(result) == len(steps) else [])


def _recipe_actions_executable(recipe: Mapping[str, Any]) -> bool:
    hyperedge = recipe.get("action_hyperedge", {})
    expected = hyperedge.get("action_ids", []) if isinstance(hyperedge, Mapping) else []
    mutations = recipe.get("action_mutations", [])
    if not isinstance(expected, list) or not isinstance(mutations, list):
        return False
    if len(mutations) != len(expected):
        return False
    observed: set[str] = set()
    for mutation in mutations:
        if not isinstance(mutation, Mapping):
            return False
        action_id = mutation.get("action_id")
        if isinstance(action_id, str):
            observed.add(action_id)
        if (
            mutation.get("mutation_kind") in (None, "UNKNOWN")
            or mutation.get("direction") in (None, "UNKNOWN")
            or not mutation.get("suggested_values")
            or mutation.get("unknown_reasons") != []
        ):
            return False
    return observed == set(expected)


def _expected_replay_obligation(
    recipe: Mapping[str, Any], mutation_recipes_sha256: str
) -> dict[str, Any]:
    prerequisites_closed, ordered_steps = _topological_recipe_steps(recipe)
    timing = recipe.get("timing", {})
    timing = timing if isinstance(timing, Mapping) else {}
    timing_status = timing.get("status", "UNKNOWN")
    observations = {
        "ACTION_ACCEPTED",
        "AP_BEFORE",
        "AP_AFTER",
        "GENERATION_IDENTITY",
        "SCOPE_IDENTITY",
    }
    if timing_status != "UNKNOWN":
        observations.add("RELATIVE_TIME")
    solver_query = recipe.get("solver_query", {})
    solver_query = solver_query if isinstance(solver_query, Mapping) else {}
    truth_change_proven = solver_query.get("outcome") == "SAT"
    recipe_supported = recipe.get("status") == "SUPPORTED"
    actions_executable = _recipe_actions_executable(recipe)
    timing_closed = timing_status == "EXACT"
    reasons: list[str] = []
    if truth_change_proven and recipe.get("status") != "UNKNOWN":
        expected_relation = "AP_TRUTH_CHANGE"
        status = (
            "READY"
            if recipe_supported
            and actions_executable
            and prerequisites_closed
            and timing_closed
            else "PARTIAL"
        )
        if not recipe_supported:
            reasons.append("mutation recipe is HEURISTIC rather than SUPPORTED")
        if not actions_executable:
            reasons.append(
                "one or more atomic actions lack a closed executable mutation"
            )
        if not prerequisites_closed:
            reasons.append(
                "prerequisite DAG is ambiguous, incomplete, or not totally replayable"
            )
        if not timing_closed:
            reasons.append("timing contract is widened or unknown")
    else:
        expected_relation = "UNKNOWN"
        status = "UNKNOWN"
        reasons.append(
            "local truth-change query is not SAT"
            if not truth_change_proven
            else "recipe remains UNKNOWN despite a local SAT pair"
        )
    hyperedge = recipe.get("action_hyperedge", {})
    action_ids = (
        list(hyperedge.get("action_ids", []))
        if isinstance(hyperedge, Mapping)
        else []
    )
    recipe_id = recipe.get("recipe_id")
    return {
        "obligation_id": stable_semantic_id(
            "replay-obligation", f"{recipe_id}\0{mutation_recipes_sha256}"
        ),
        "recipe_id": recipe_id,
        "frontier_candidate_id": recipe.get("frontier_candidate_id"),
        "status": status,
        "atomic_action_ids": action_ids,
        "indivisible_hyperedge": True,
        "ordered_step_ids": ordered_steps,
        "required_observations": sorted(observations),
        "expected_relation": expected_relation,
        "solver_query_sha256": solver_query.get("query_sha256"),
        "scope_schema": timing.get("scope_schema"),
        "generation_schema": timing.get("generation_schema"),
        "timing_status": timing_status,
        "uncertainty_reasons": sorted(set(reasons)),
    }


def _expected_replay_document(
    recipes: Mapping[str, Any], mutation_recipes_sha256: str
) -> dict[str, Any]:
    obligations = [
        _expected_replay_obligation(recipe, mutation_recipes_sha256)
        for recipe in recipes.get("recipes", [])
        if isinstance(recipe, Mapping)
    ]
    obligations.sort(key=lambda item: str(item["obligation_id"]))
    return {
        "schema_version": "1.0.0",
        "artifact_id": stable_semantic_id(
            "recipe-replay-obligations", mutation_recipes_sha256
        ),
        "mutation_recipes_sha256": mutation_recipes_sha256,
        "candidate_accounting_complete": recipes.get(
            "candidate_accounting_complete", True
        ),
        "obligations": obligations,
    }


def _verify_replay_reconstruction(
    recipes: Mapping[str, Any],
    replay: Mapping[str, Any],
    mutation_recipes_sha256: str,
    audit: Audit,
) -> None:
    starting_failures = audit.failures
    recipe_ids = [
        item.get("recipe_id")
        for item in recipes.get("recipes", [])
        if isinstance(item, Mapping)
    ]
    if len(recipe_ids) != len(set(recipe_ids)):
        audit.failed(
            "replay.reconstruction", "mutation recipe IDs are not unique"
        )
    expected = _expected_replay_document(recipes, mutation_recipes_sha256)
    for field in (
        "schema_version",
        "artifact_id",
        "mutation_recipes_sha256",
        "candidate_accounting_complete",
    ):
        if replay.get(field) != expected[field]:
            audit.failed(
                "replay.reconstruction",
                f"replay {field} is not reconstructed from mutation recipes",
            )
    actual_obligations = replay.get("obligations", [])
    if not isinstance(actual_obligations, list):
        audit.failed("replay.reconstruction", "replay obligations are not a list")
        return
    actual_by_recipe = {
        item.get("recipe_id"): item
        for item in actual_obligations
        if isinstance(item, Mapping) and isinstance(item.get("recipe_id"), str)
    }
    expected_by_recipe = {
        item["recipe_id"]: item for item in expected["obligations"]
    }
    if len(actual_by_recipe) != len(actual_obligations):
        audit.failed(
            "replay.reconstruction",
            "replay obligations have duplicate or invalid recipe identities",
        )
    if set(actual_by_recipe) != set(expected_by_recipe):
        audit.failed(
            "replay.reconstruction",
            "replay obligation recipe ledger differs from mutation recipes",
        )
    obligation_fields = (
        "obligation_id",
        "recipe_id",
        "frontier_candidate_id",
        "status",
        "atomic_action_ids",
        "indivisible_hyperedge",
        "ordered_step_ids",
        "required_observations",
        "expected_relation",
        "solver_query_sha256",
        "scope_schema",
        "generation_schema",
        "timing_status",
        "uncertainty_reasons",
    )
    for recipe_id, wanted in expected_by_recipe.items():
        actual = actual_by_recipe.get(recipe_id)
        if not isinstance(actual, Mapping):
            continue
        for field in obligation_fields:
            if actual.get(field) != wanted[field]:
                audit.failed(
                    "replay.reconstruction",
                    f"replay obligation {recipe_id} {field} differs from recipe reconstruction",
                )
    actual_order = [
        item.get("obligation_id")
        for item in actual_obligations
        if isinstance(item, Mapping)
    ]
    expected_order = [item["obligation_id"] for item in expected["obligations"]]
    if actual_order != expected_order:
        audit.failed(
            "replay.reconstruction",
            "replay obligations are not in deterministic obligation-ID order",
        )
    if audit.failures == starting_failures:
        ready = sum(
            item["status"] == "READY" for item in expected["obligations"]
        )
        audit.passed(
            "replay.reconstruction",
            f"all {len(expected['obligations'])} replay obligations reconstruct exactly ({ready} READY)",
        )


def _frontier_u64(value: int) -> bytes:
    return int(value).to_bytes(8, "little", signed=False)


def _frontier_lp(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return _frontier_u64(len(encoded)) + encoded


def _frontier_contract_digest(contract: Mapping[str, Any]) -> str:
    material = bytearray(_frontier_lp("rift-frontier-traversal-contract/1.0.0"))
    for name in (
        "algorithm",
        "algorithm_version",
        "node_order",
        "edge_order",
        "path_class_encoding",
        "meet_ledger",
        "reach_ledger",
        "transition_ledger",
        "compatibility",
        "model_arc_policy",
        "exemplar_policy",
    ):
        material.extend(_frontier_lp(str(contract[name])))
    for name in (
        "maximum_path_exemplars",
        "max_materialized_model_edges",
        "max_forward_states_per_attachment",
    ):
        material.extend(_frontier_u64(int(contract[name])))
    return sha256_bytes(bytes(material))


def _frontier_value_type_material(value_type: Mapping[str, Any]) -> str:
    # Matches frontier.cpp:value_type_material, including the textual
    # signed/unsigned optional rather than JSON's boolean representation.
    fields = [
        str(FRONTIER_VALUE_KIND[str(value_type["kind"])]),
        str(value_type["canonical"]),
        "" if "bit_width" not in value_type else str(value_type["bit_width"]),
        (
            ""
            if "signed" not in value_type
            else "signed" if value_type["signed"] else "unsigned"
        ),
        "" if "unit" not in value_type else str(value_type["unit"]),
    ]
    return "\0".join(fields)


def _frontier_action_identity_material(action: Mapping[str, Any]) -> str:
    return "\0".join(
        (
            str(action["action_schema_id"]),
            str(action["action_class"]),
            str(action["channel"]),
            str(action["operation"]),
            _frontier_value_type_material(action["payload_type"]),
            str(action["payload_slot"]),
            str(action["scope_schema"]),
            str(action["generation_schema"]),
            str(action["timing_capability"]),
            str(action["required_capability"]),
        )
    )


def _frontier_normalized_action(action: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(action))
    normalized: list[dict[str, Any]] = []
    for raw in result.get("provenance", []):
        item = dict(raw)
        for field_name in (
            "selector_ids",
            "capture_ids",
            "matched_semantic_node_ids",
        ):
            item[field_name] = sorted(set(item.get(field_name, [])))
        normalized.append(item)
    layer_order = {"platform": 0, "framework": 1, "project_adapter": 2}
    normalized.sort(
        key=lambda item: (
            item["model_pack_sha256"],
            item["model_pack_id"],
            item["model_pack_version"],
            layer_order[item["layer"]],
            item["rule_id"],
            item["emit_id"],
            item["selector_ids"],
            item["capture_ids"],
            item["matched_semantic_node_ids"],
        )
    )
    result["provenance"] = normalized
    return result


def _frontier_certainty_mask(certainty: str) -> int:
    if certainty in {"must", "may"}:
        return FRONTIER_STATIC
    if certainty == "modelled":
        return FRONTIER_MODELLED
    return FRONTIER_UNKNOWN


def _frontier_cone_membership_mask(membership: str) -> int:
    if membership in {"MUST_INFLUENCE", "MAY_INFLUENCE"}:
        return FRONTIER_STATIC
    if membership == "MODELLED_INFLUENCE":
        return FRONTIER_MODELLED
    return FRONTIER_UNKNOWN


def _frontier_compose_classes(left: int, right: int) -> int:
    if left == FRONTIER_UNKNOWN or right == FRONTIER_UNKNOWN:
        return FRONTIER_UNKNOWN
    if left == FRONTIER_MODELLED or right == FRONTIER_MODELLED:
        return FRONTIER_MODELLED
    return FRONTIER_STATIC


def _frontier_product_mask(forward: int, reverse: int) -> int:
    result = 0
    for left in FRONTIER_PATH_CLASSES:
        if not forward & left:
            continue
        for right in FRONTIER_PATH_CLASSES:
            if reverse & right:
                result |= _frontier_compose_classes(left, right)
    return result


@dataclass(slots=True)
class _FrontierArc:
    edge_id: str
    source: int
    target: int
    relation: int
    certainty: int
    compatibility: int
    compatibility_reasons: tuple[str, ...]
    graph_uncertainty_reasons: tuple[str, ...]
    graph_edge_id: str | None
    model_fact_id: str | None


@dataclass(slots=True)
class _FrontierTraversal:
    nodes: list[Mapping[str, Any]]
    node_ids: list[str]
    node_ordinals: dict[str, int]
    semantic_instances: dict[str, list[int]]
    arcs: list[_FrontierArc]
    outgoing: list[list[int]]
    incoming: list[list[int]]
    complete: bool
    gap_reasons: tuple[str, ...]


@dataclass(slots=True)
class _FrontierReach:
    states: bytearray
    complete: bool
    compatibility_complete: bool
    gap_reasons: tuple[str, ...]
    summary: dict[str, Any]


@dataclass(slots=True)
class _FrontierReverse:
    states: bytearray
    root_states: bytearray
    complete: bool
    compatibility_complete: bool
    gap_reasons: tuple[str, ...]


def _frontier_context_compatibility(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    relation_name: str,
) -> tuple[int, tuple[str, ...]]:
    verdict = FRONTIER_COMPATIBILITY["COMPATIBLE"]
    reasons: set[str] = set()

    def unknown(reason: str) -> None:
        nonlocal verdict
        if verdict != FRONTIER_COMPATIBILITY["INCOMPATIBLE"]:
            verdict = FRONTIER_COMPATIBILITY["UNKNOWN"]
        reasons.add(reason)

    source_call = source["call_context"]
    target_call = target["call_context"]
    if source_call["truncated"] or target_call["truncated"]:
        unknown("call context is truncated")
    elif source_call["callsite_ids"] != target_call["callsite_ids"]:
        source_ids = source_call["callsite_ids"]
        target_ids = target_call["callsite_ids"]
        balanced = False
        if relation_name == "calls":
            balanced = len(target_ids) == len(source_ids) + 1 and target_ids[:-1] == source_ids
        elif relation_name == "returns":
            balanced = len(source_ids) == len(target_ids) + 1 and source_ids[:-1] == target_ids
        global_transfer = (
            source["abstract_object"]["abstraction"] == "global"
            or target["abstract_object"]["abstraction"] == "global"
        )
        if not balanced and not global_transfer:
            unknown("call contexts are not proven concatenable")

    source_scope = source["scope"]
    target_scope = target["scope"]
    if (
        source_scope["status"] == "exact"
        and target_scope["status"] == "exact"
        and source_scope["scope_id"] != target_scope["scope_id"]
    ):
        unknown("exact scope identities differ across transfer")
    source_generation = source["generation"]
    target_generation = target["generation"]
    if (
        source_generation["kind"] == "exact"
        and target_generation["kind"] == "exact"
        and source_generation["identity"] is not None
        and target_generation["identity"] is not None
        and source_generation["identity"] != target_generation["identity"]
    ):
        unknown("exact generation identities differ across transfer")
    source_task = source["task_context"]
    target_task = target["task_context"]
    if (
        source_task["certainty"] == "must"
        and target_task["certainty"] == "must"
        and source_task["context_id"] is not None
        and target_task["context_id"] is not None
        and source_task["context_id"] != target_task["context_id"]
        and relation_name not in {"calls", "returns"}
    ):
        unknown("task contexts differ without a proven event transfer")
    if (
        source["lifecycle_phase"] in {"cancelled", "destroyed"}
        and target["lifecycle_phase"] in {"active", "committed"}
        and relation_name not in {"calls", "returns"}
    ):
        unknown("terminal-to-active lifecycle transfer is not proven")
    if (
        relation_name in {"object", "field", "aliases"}
        and source["abstract_object"]["certainty"] == "must"
        and target["abstract_object"]["certainty"] == "must"
        and source["abstract_object"]["object_id"]
        != target["abstract_object"]["object_id"]
    ):
        verdict = FRONTIER_COMPATIBILITY["INCOMPATIBLE"]
        reasons.add("object-preserving relation joins distinct exact objects")
    return verdict, tuple(sorted(reasons))


def _frontier_compose_one(path_class: int, arc: _FrontierArc) -> int:
    if arc.compatibility == FRONTIER_COMPATIBILITY["INCOMPATIBLE"]:
        return 0
    if (
        path_class == FRONTIER_UNKNOWN
        or arc.compatibility == FRONTIER_COMPATIBILITY["UNKNOWN"]
        or arc.certainty == FRONTIER_CERTAINTY["unknown"]
    ):
        return FRONTIER_UNKNOWN
    if (
        path_class == FRONTIER_MODELLED
        or arc.certainty == FRONTIER_CERTAINTY["modelled"]
    ):
        return FRONTIER_MODELLED
    return FRONTIER_STATIC


def _frontier_compose_mask(mask: int, arc: _FrontierArc) -> int:
    result = 0
    for path_class in FRONTIER_PATH_CLASSES:
        if mask & path_class:
            result |= _frontier_compose_one(path_class, arc)
    return result


def _build_frontier_traversal(
    overlay: Mapping[str, Any],
    graph: Mapping[str, Any],
    max_model_edges: int,
    audit: Audit,
) -> _FrontierTraversal | None:
    raw_nodes = graph.get("nodes", [])
    if not isinstance(raw_nodes, list) or not all(isinstance(node, Mapping) for node in raw_nodes):
        audit.failed("frontier.recompute", "contextual graph nodes are not replayable objects")
        return None
    nodes = sorted(raw_nodes, key=lambda node: str(node["node_id"]))
    node_ids = [str(node["node_id"]) for node in nodes]
    if len(set(node_ids)) != len(node_ids):
        audit.failed("frontier.recompute", "contextual graph has duplicate node identities")
        return None
    ordinals = {node_id: index for index, node_id in enumerate(node_ids)}
    semantic_instances: dict[str, list[int]] = {}
    for index, node in enumerate(nodes):
        semantic_instances.setdefault(str(node["semantic_node_ref"]), []).append(index)

    arcs: list[_FrontierArc] = []
    complete = True
    gaps: set[str] = set()
    raw_edges = graph.get("edges", [])
    if not isinstance(raw_edges, list):
        audit.failed("frontier.recompute", "contextual graph edges are not an array")
        return None
    graph_edge_ids: set[str] = set()
    for raw in sorted(raw_edges, key=lambda edge: str(edge["edge_id"])):
        edge_id = str(raw["edge_id"])
        if edge_id in graph_edge_ids:
            audit.failed("frontier.recompute", f"duplicate graph edge identity {edge_id}")
            return None
        graph_edge_ids.add(edge_id)
        source = ordinals.get(str(raw["source_node_id"]))
        target = ordinals.get(str(raw["target_node_id"]))
        if source is None or target is None:
            complete = False
            gaps.add("contextual graph edge has an unresolved endpoint")
            continue
        relation_name = str(raw["relation_kind"])
        compatibility, compatibility_reasons = _frontier_context_compatibility(
            nodes[source], nodes[target], relation_name
        )
        arcs.append(
            _FrontierArc(
                edge_id=edge_id,
                source=source,
                target=target,
                relation=FRONTIER_RELATION[relation_name],
                certainty=FRONTIER_CERTAINTY[str(raw["certainty"])],
                compatibility=compatibility,
                compatibility_reasons=compatibility_reasons,
                graph_uncertainty_reasons=tuple(sorted(set(raw.get("uncertainty_reasons", [])))),
                graph_edge_id=edge_id,
                model_fact_id=None,
            )
        )

    materialized = 0
    exhausted = False
    facts = [
        fact
        for fact in overlay.get("semantic_facts", [])
        if isinstance(fact, Mapping) and fact.get("target_semantic_node_id") is not None
    ]
    fact_ids: set[str] = set()
    for fact in sorted(facts, key=lambda item: str(item["fact_id"])):
        fact_id = str(fact["fact_id"])
        if fact_id in fact_ids:
            audit.failed("frontier.recompute", f"duplicate model fact identity {fact_id}")
            return None
        fact_ids.add(fact_id)
        sources = semantic_instances.get(str(fact["source_semantic_node_id"]))
        targets = semantic_instances.get(str(fact["target_semantic_node_id"]))
        if not sources or not targets:
            complete = False
            gaps.add("model fact has no contextual instance for an endpoint")
            continue
        for source in sources:
            for target in targets:
                if materialized >= max_model_edges:
                    complete = False
                    exhausted = True
                    gaps.add("model-edge materialization resource limit reached")
                    break
                edge_id = stable_semantic_id(
                    "frontier-edge",
                    fact_id + "\0" + node_ids[source] + "\0" + node_ids[target],
                )
                compatibility, compatibility_reasons = _frontier_context_compatibility(
                    nodes[source], nodes[target], "unknown"
                )
                arcs.append(
                    _FrontierArc(
                        edge_id=edge_id,
                        source=source,
                        target=target,
                        relation=FRONTIER_RELATION["unknown"],
                        certainty=FRONTIER_CERTAINTY[str(fact["certainty"])],
                        compatibility=compatibility,
                        compatibility_reasons=compatibility_reasons,
                        graph_uncertainty_reasons=(),
                        graph_edge_id=None,
                        model_fact_id=fact_id,
                    )
                )
                materialized += 1
            if exhausted:
                break
        if exhausted:
            break
    arcs.sort(
        key=lambda arc: (
            0 if arc.model_fact_id is None else 1,
            arc.edge_id,
            arc.source,
            arc.target,
        )
    )
    outgoing: list[list[int]] = [[] for _ in nodes]
    incoming: list[list[int]] = [[] for _ in nodes]
    for index, arc in enumerate(arcs):
        outgoing[arc.source].append(index)
        incoming[arc.target].append(index)
    return _FrontierTraversal(
        nodes=nodes,
        node_ids=node_ids,
        node_ordinals=ordinals,
        semantic_instances=semantic_instances,
        arcs=arcs,
        outgoing=outgoing,
        incoming=incoming,
        complete=complete,
        gap_reasons=tuple(sorted(gaps)),
    )


def _frontier_arc_record(arc: _FrontierArc, traversal: _FrontierTraversal, mask: int) -> bytes:
    material = bytearray()
    material.extend(_frontier_lp("GRAPH_EDGE" if arc.model_fact_id is None else "MODEL_ARC"))
    material.extend(_frontier_lp(arc.edge_id))
    material.extend(_frontier_lp(traversal.node_ids[arc.source]))
    material.extend(_frontier_lp(traversal.node_ids[arc.target]))
    material.extend(_frontier_u64(mask))
    material.extend(_frontier_u64(arc.relation))
    material.extend(_frontier_u64(arc.certainty))
    material.extend(_frontier_u64(arc.compatibility))
    material.extend(_frontier_lp("" if arc.model_fact_id is None else arc.model_fact_id))
    reasons = sorted(set(arc.compatibility_reasons) | set(arc.graph_uncertainty_reasons))
    material.extend(_frontier_u64(len(reasons)))
    for reason in reasons:
        material.extend(_frontier_lp(reason))
    return bytes(material)


def _frontier_forward_reach(
    boundary_node_id: str,
    attachment_certainty: str,
    traversal: _FrontierTraversal,
    max_states: int,
) -> _FrontierReach:
    states = bytearray(len(traversal.nodes))
    boundary = traversal.node_ordinals.get(boundary_node_id)
    if boundary is None:
        return _FrontierReach(
            states,
            False,
            True,
            ("boundary contextual node is absent from traversal graph",),
            {
                "reached_node_count": 0,
                "reachable_transition_count": 0,
                "enumeration_complete": False,
                "reached_state_ledger_sha256": sha256_bytes(b""),
                "reachable_transition_ledger_sha256": sha256_bytes(b""),
            },
        )
    states[boundary] = _frontier_certainty_mask(attachment_certainty)
    queue: collections.deque[int] = collections.deque([boundary])
    changes = 1
    complete = True
    gaps: set[str] = set()
    while queue:
        source = queue.popleft()
        source_state = states[source]
        stop = False
        for arc_index in traversal.outgoing[source]:
            arc = traversal.arcs[arc_index]
            if arc.compatibility == FRONTIER_COMPATIBILITY["UNKNOWN"]:
                gaps.update(arc.compatibility_reasons)
            candidate = _frontier_compose_mask(source_state, arc)
            if not candidate:
                continue
            prior = states[arc.target]
            merged = prior | candidate
            if merged == prior:
                continue
            if changes >= max_states:
                complete = False
                gaps.add("forward-state resource limit reached")
                queue.clear()
                stop = True
                break
            states[arc.target] = merged
            changes += 1
            queue.append(arc.target)
        if stop:
            break
    state_records = bytearray()
    reached = 0
    for index, state in enumerate(states):
        if not state:
            continue
        reached += 1
        state_records.extend(_frontier_lp(traversal.node_ids[index]))
        state_records.extend(_frontier_u64(state))
    state_ledger = (
        _frontier_lp("rift-reach-ledger/lp-u64le/1.0.0")
        + _frontier_u64(reached)
        + bytes(state_records)
    )
    transition_records = bytearray()
    transitions = 0
    for arc in traversal.arcs:
        contribution = _frontier_compose_mask(states[arc.source], arc) & states[arc.target]
        if not contribution:
            continue
        transitions += 1
        transition_records.extend(_frontier_arc_record(arc, traversal, contribution))
    transition_ledger = (
        _frontier_lp("rift-transition-ledger/lp-u64le/1.0.0")
        + _frontier_u64(transitions)
        + bytes(transition_records)
    )
    enumeration_complete = complete and traversal.complete
    return _FrontierReach(
        states=states,
        complete=complete,
        compatibility_complete=True,
        gap_reasons=tuple(sorted(gaps)),
        summary={
            "reached_node_count": reached,
            "reachable_transition_count": transitions,
            "enumeration_complete": enumeration_complete,
            "reached_state_ledger_sha256": sha256_bytes(state_ledger),
            "reachable_transition_ledger_sha256": sha256_bytes(transition_ledger),
        },
    )


def _frontier_reverse_reach(
    cone: Mapping[str, Any],
    traversal: _FrontierTraversal,
    max_states: int,
) -> _FrontierReverse:
    states = bytearray(len(traversal.nodes))
    roots = bytearray(len(traversal.nodes))
    memberships = {
        str(member["node_id"]): str(member["membership"])
        for member in cone.get("members", [])
    }
    root_ids = sorted(
        {
            str(node_id)
            for account in cone.get("candidate_accounting", [])
            if account.get("disposition") == "INCLUDED"
            for node_id in account.get("root_node_ids", [])
        }
    )
    if not root_ids:
        root_ids = sorted(
            str(member["node_id"])
            for member in cone.get("members", [])
            if not member.get("witness_edge_ids", [])
        )
    queue: collections.deque[int] = collections.deque()
    gaps: set[str] = set()
    complete = True
    changes = 0
    for root_id in root_ids:
        ordinal = traversal.node_ordinals.get(root_id)
        membership = memberships.get(root_id)
        if ordinal is None or membership is None:
            complete = False
            gaps.add("cone root is absent from traversal graph or member ledger")
            continue
        mask = _frontier_cone_membership_mask(membership)
        roots[ordinal] |= mask
        merged = states[ordinal] | mask
        if merged != states[ordinal]:
            states[ordinal] = merged
            queue.append(ordinal)
            changes += 1
    if not root_ids:
        complete = False
        gaps.add("cone has no included contextual root")
    while queue:
        target = queue.popleft()
        target_state = states[target]
        stop = False
        for arc_index in traversal.incoming[target]:
            arc = traversal.arcs[arc_index]
            if arc.compatibility == FRONTIER_COMPATIBILITY["INCOMPATIBLE"]:
                continue
            if arc.compatibility == FRONTIER_COMPATIBILITY["UNKNOWN"]:
                gaps.update(arc.compatibility_reasons)
            candidate = _frontier_compose_mask(target_state, arc)
            if not candidate:
                continue
            prior = states[arc.source]
            merged = prior | candidate
            if merged == prior:
                continue
            if changes >= max_states:
                complete = False
                gaps.add("reverse-cone state resource limit reached")
                queue.clear()
                stop = True
                break
            states[arc.source] = merged
            changes += 1
            queue.append(arc.source)
        if stop:
            break
    if not traversal.complete:
        complete = False
        gaps.add("traversal graph materialization is conservative-incomplete")
    if cone.get("status") != "COMPLETE":
        complete = False
        gaps.add("influence cone is conservative-incomplete")
    return _FrontierReverse(
        states=states,
        root_states=roots,
        complete=complete,
        compatibility_complete=True,
        gap_reasons=tuple(sorted(gaps)),
    )


def _frontier_choose_product_classes(forward: int, reverse: int, effective: int) -> tuple[int, int] | None:
    for forward_class in FRONTIER_PATH_CLASSES:
        if not forward & forward_class:
            continue
        for root_class in FRONTIER_PATH_CLASSES:
            if reverse & root_class and _frontier_compose_classes(forward_class, root_class) == effective:
                return forward_class, root_class
    return None


def _frontier_witness_summary(
    attachment: Mapping[str, Any],
    boundary_node_id: str,
    cone: Mapping[str, Any],
    forward: _FrontierReach,
    reverse: _FrontierReverse,
    traversal: _FrontierTraversal,
) -> dict[str, Any]:
    meet_records = bytearray()
    meet_count = 0
    class_counts = {path_class: 0 for path_class in FRONTIER_PATH_CLASSES}
    histogram = [0] * 8
    first_meet: dict[int, tuple[int, int, int]] = {}
    for ordinal, (forward_mask, root_mask) in enumerate(zip(forward.states, reverse.states)):
        meet_mask = _frontier_product_mask(forward_mask, root_mask)
        if not meet_mask:
            continue
        meet_count += 1
        for path_class in FRONTIER_PATH_CLASSES:
            if meet_mask & path_class:
                class_counts[path_class] += 1
                first_meet.setdefault(path_class, (ordinal, forward_mask, root_mask))
        histogram[meet_mask] += 1
        meet_records.extend(_frontier_lp(traversal.node_ids[ordinal]))
        meet_records.extend(_frontier_u64(forward_mask))
        meet_records.extend(_frontier_u64(root_mask))
        meet_records.extend(_frontier_u64(meet_mask))
    meet_ledger = bytearray()
    meet_ledger.extend(_frontier_lp("rift-meet-ledger/lp-u64le/1.0.0"))
    meet_ledger.extend(_frontier_lp(str(attachment["attachment_id"])))
    meet_ledger.extend(_frontier_lp(boundary_node_id))
    meet_ledger.extend(_frontier_lp(str(cone["cone_id"])))
    meet_ledger.extend(_frontier_u64(meet_count))
    meet_ledger.extend(meet_records)
    enumeration_complete = (
        forward.complete
        and reverse.complete
        and traversal.complete
        and cone.get("status") == "COMPLETE"
    )
    meet_summary = {
        "meet_count": meet_count,
        "static_path_meet_count": class_counts[FRONTIER_STATIC],
        "modelled_path_meet_count": class_counts[FRONTIER_MODELLED],
        "unknown_path_meet_count": class_counts[FRONTIER_UNKNOWN],
        "effective_mask_histogram": histogram[1:],
        "enumeration_complete": enumeration_complete,
        "ledger_sha256": sha256_bytes(bytes(meet_ledger)),
    }

    support_records = bytearray()
    support_count = 0
    model_fact_ids: set[str] = set()
    for arc in traversal.arcs:
        supported_mask = 0
        for forward_class in FRONTIER_PATH_CLASSES:
            if not forward.states[arc.source] & forward_class:
                continue
            after_edge = _frontier_compose_one(forward_class, arc)
            if not after_edge:
                continue
            for root_class in FRONTIER_PATH_CLASSES:
                if reverse.states[arc.target] & root_class:
                    supported_mask |= _frontier_compose_classes(after_edge, root_class)
        if not supported_mask:
            continue
        support_count += 1
        support_records.extend(_frontier_arc_record(arc, traversal, supported_mask))
        if arc.model_fact_id is not None:
            model_fact_ids.add(arc.model_fact_id)
    support_ledger = (
        _frontier_lp("rift-product-support/lp-u64le/1.0.0")
        + _frontier_u64(support_count)
        + bytes(support_records)
    )
    ordered_facts = sorted(model_fact_ids)
    fact_ledger = bytearray(_frontier_lp("rift-product-model-facts/lp-u64le/1.0.0"))
    fact_ledger.extend(_frontier_u64(len(ordered_facts)))
    for fact_id in ordered_facts:
        fact_ledger.extend(_frontier_lp(fact_id))
    support_summary = {
        "supporting_transition_count": support_count,
        "supporting_model_fact_count": len(ordered_facts),
        "enumeration_complete": enumeration_complete,
        "supporting_transition_ledger_sha256": sha256_bytes(support_ledger),
        "supporting_model_fact_ledger_sha256": sha256_bytes(bytes(fact_ledger)),
    }
    reachability = (
        "STATIC_WITNESS"
        if class_counts[FRONTIER_STATIC]
        else "MODELLED_WITNESS"
        if class_counts[FRONTIER_MODELLED]
        else "UNKNOWN"
    )
    compatibility = (
        "COMPATIBLE"
        if class_counts[FRONTIER_STATIC] or class_counts[FRONTIER_MODELLED]
        else "UNKNOWN"
    )
    witness_id = stable_semantic_id(
        "frontier-witness",
        str(attachment["attachment_id"])
        + "\0"
        + boundary_node_id
        + "\0"
        + str(cone["cone_id"])
        + "\0"
        + meet_summary["ledger_sha256"]
        + "\0"
        + str(meet_count),
    )
    uncertainty: list[str] = []
    if class_counts[FRONTIER_UNKNOWN]:
        uncertainty.append("alternate or only witness retains UNKNOWN provenance")
    if not enumeration_complete:
        uncertainty.append("meet ledger is conservative-incomplete")
    return {
        "witness_id": witness_id,
        "forward_summary": forward.summary,
        "meet_summary": meet_summary,
        "support_summary": support_summary,
        "first_meet": first_meet,
        "compatibility": compatibility,
        "reachability": reachability,
        "model_fact_ids": ordered_facts,
        "uncertainty_reasons": sorted(uncertainty),
    }


def _frontier_resolve_step(
    step: Mapping[str, Any],
    traversal: _FrontierTraversal,
    graph_arcs: Mapping[str, _FrontierArc],
    model_arcs: Mapping[tuple[str, str, str], _FrontierArc],
) -> _FrontierArc | None:
    source = str(step.get("source_node_id"))
    target = str(step.get("target_node_id"))
    if step.get("kind") == "GRAPH_EDGE":
        edge_id = step.get("graph_edge_id")
        if not isinstance(edge_id, str) or step.get("model_fact_id") is not None:
            return None
        arc = graph_arcs.get(edge_id)
    elif step.get("kind") == "MODEL_ARC":
        fact_id = step.get("model_fact_id")
        if not isinstance(fact_id, str) or step.get("graph_edge_id") is not None:
            return None
        arc = model_arcs.get((fact_id, source, target))
    else:
        return None
    if arc is None:
        return None
    if traversal.node_ids[arc.source] != source or traversal.node_ids[arc.target] != target:
        return None
    return arc


def _verify_frontier_exemplars(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    attachment: Mapping[str, Any],
    boundary_node_id: str,
    forward: _FrontierReach,
    reverse: _FrontierReverse,
    traversal: _FrontierTraversal,
    audit: Audit,
) -> None:
    exemplars = actual.get("path_exemplars", [])
    expected_classes = [
        path_class
        for path_class in FRONTIER_PATH_CLASSES
        if expected["meet_summary"][
            "static_path_meet_count"
            if path_class == FRONTIER_STATIC
            else "modelled_path_meet_count"
            if path_class == FRONTIER_MODELLED
            else "unknown_path_meet_count"
        ]
    ]
    if not isinstance(exemplars, list) or [item.get("effective_path_class") for item in exemplars] != [
        FRONTIER_PATH_NAMES[path_class] for path_class in expected_classes
    ]:
        audit.failed(
            "frontier.exemplar",
            f"witness {actual.get('witness_id')} does not retain exactly one ordered exemplar per effective path class",
        )
        return
    graph_arcs: dict[str, _FrontierArc] = {}
    model_arcs: dict[tuple[str, str, str], _FrontierArc] = {}
    for arc in traversal.arcs:
        if arc.graph_edge_id is not None:
            graph_arcs[arc.graph_edge_id] = arc
        elif arc.model_fact_id is not None:
            model_arcs[(arc.model_fact_id, traversal.node_ids[arc.source], traversal.node_ids[arc.target])] = arc
    for exemplar, effective in zip(exemplars, expected_classes):
        ordinal, forward_mask, root_mask = expected["first_meet"][effective]
        meet_id = traversal.node_ids[ordinal]
        chosen = _frontier_choose_product_classes(forward_mask, root_mask, effective)
        if chosen is None:
            audit.failed("frontier.exemplar", f"witness {actual.get('witness_id')} has no replayable product class")
            continue
        forward_class, root_class = chosen
        expected_reachability = (
            "STATIC_WITNESS"
            if effective == FRONTIER_STATIC
            else "MODELLED_WITNESS"
            if effective == FRONTIER_MODELLED
            else "UNKNOWN"
        )
        expected_compatibility = "UNKNOWN" if effective == FRONTIER_UNKNOWN else "COMPATIBLE"
        header = {
            "effective_path_class": FRONTIER_PATH_NAMES[effective],
            "raw_forward_path_class": FRONTIER_PATH_NAMES[forward_class],
            "raw_root_path_class": FRONTIER_PATH_NAMES[root_class],
            "meet_node_id": meet_id,
            "compatibility": expected_compatibility,
            "reachability": expected_reachability,
            "representative_only": True,
        }
        for field_name, wanted in header.items():
            if exemplar.get(field_name) != wanted:
                audit.failed(
                    "frontier.exemplar",
                    f"witness {actual.get('witness_id')} exemplar {field_name} differs from deterministic first-meet replay",
                )
        uncertainty: set[str] = set()
        cursor = boundary_node_id
        current_class = _frontier_certainty_mask(str(attachment["certainty"]))
        valid_forward = True
        for step in exemplar.get("forward_steps", []):
            if not isinstance(step, Mapping) or str(step.get("source_node_id")) != cursor:
                valid_forward = False
                break
            arc = _frontier_resolve_step(step, traversal, graph_arcs, model_arcs)
            if arc is None:
                valid_forward = False
                break
            current_class = _frontier_compose_one(current_class, arc)
            if not current_class:
                valid_forward = False
                break
            if arc.compatibility == FRONTIER_COMPATIBILITY["UNKNOWN"] or arc.certainty == FRONTIER_CERTAINTY["unknown"]:
                uncertainty.update(arc.compatibility_reasons)
                uncertainty.update(arc.graph_uncertainty_reasons)
            cursor = str(step["target_node_id"])
        if cursor != meet_id or current_class != forward_class:
            valid_forward = False
        if not valid_forward:
            audit.failed(
                "frontier.exemplar",
                f"witness {actual.get('witness_id')} forward exemplar is not a class-preserving boundary-to-meet path",
            )

        cursor = meet_id
        possible = {root_class}
        valid_root = True
        for step in exemplar.get("root_steps", []):
            if not isinstance(step, Mapping) or str(step.get("source_node_id")) != cursor:
                valid_root = False
                break
            arc = _frontier_resolve_step(step, traversal, graph_arcs, model_arcs)
            if arc is None:
                valid_root = False
                break
            next_possible: set[int] = set()
            for source_class in possible:
                for target_class in FRONTIER_PATH_CLASSES:
                    if (
                        reverse.states[arc.target] & target_class
                        and _frontier_compose_one(target_class, arc) == source_class
                    ):
                        next_possible.add(target_class)
            possible = next_possible
            if not possible:
                valid_root = False
                break
            if arc.compatibility == FRONTIER_COMPATIBILITY["UNKNOWN"] or arc.certainty == FRONTIER_CERTAINTY["unknown"]:
                uncertainty.update(arc.compatibility_reasons)
                uncertainty.update(arc.graph_uncertainty_reasons)
            cursor = str(step["target_node_id"])
        root_ordinal = traversal.node_ordinals.get(cursor)
        if (
            root_ordinal is None
            or not any(reverse.root_states[root_ordinal] & path_class for path_class in possible)
            or exemplar.get("root_node_id") != cursor
        ):
            valid_root = False
        if not valid_root:
            audit.failed(
                "frontier.exemplar",
                f"witness {actual.get('witness_id')} root exemplar is not a class-preserving meet-to-root path",
            )
        if effective == FRONTIER_UNKNOWN:
            uncertainty.add("alternate or only witness retains UNKNOWN provenance")
        if exemplar.get("uncertainty_reasons") != sorted(uncertainty):
            audit.failed(
                "frontier.exemplar",
                f"witness {actual.get('witness_id')} exemplar uncertainty ledger is not reconstructed from its path",
            )


def _frontier_controllability(action: Mapping[str, Any], executor: Mapping[str, Any] | None) -> str:
    if executor is None or executor.get("status") == "FAILED":
        return "UNKNOWN"
    matches = {
        str(entry["controllability"])
        for entry in executor.get("capabilities", [])
        if entry.get("required_capability") == action.get("required_capability")
        and (
            entry.get("action_schema_id") is None
            or entry.get("action_schema_id") == action.get("action_schema_id")
        )
    }
    if not matches:
        return "UNAVAILABLE" if executor.get("status") == "COMPLETE" else "UNKNOWN"
    return next(iter(matches)) if len(matches) == 1 else "UNKNOWN"


def _frontier_status_join(left: str, right: str) -> str:
    return left if STATUS_RANK[left] >= STATUS_RANK[right] else right


def _frontier_cones_status(cones: Mapping[str, Any]) -> str:
    status = "COMPLETE"
    for cone in cones.get("cones", []):
        status = _frontier_status_join(status, str(cone.get("status", "FAILED")))
    return status


def _frontier_vm_complete(overlay: Mapping[str, Any]) -> bool:
    return (
        overlay.get("status") == "COMPLETE"
        and not overlay.get("unknown_outcomes", [])
        and all(entry.get("complete") is True for entry in overlay.get("resource_ledger", []))
    )


def _verify_frontier_semantics(
    candidates: Mapping[str, Any],
    frontier: Mapping[str, Any],
    overlay: Mapping[str, Any],
    graph: Mapping[str, Any],
    cones: Mapping[str, Any],
    executor: Mapping[str, Any] | None,
    frontier_candidates_sha256: str,
    audit: Audit,
    m4_cone_status: str | None = None,
) -> None:
    # The legacy skeletal certificate self-test deliberately disables semantic
    # schema validation.  Production artifacts are closed to exactly 3.0.0.
    if candidates.get("schema_version") != "3.0.0":
        return
    contract = candidates.get("traversal_contract")
    if not isinstance(contract, Mapping):
        audit.failed("frontier.contract", "frontier traversal contract is absent")
        return
    expected_contract = {
        **FRONTIER_TRAVERSAL_DEFAULTS,
        "max_materialized_model_edges": contract.get("max_materialized_model_edges"),
        "max_forward_states_per_attachment": contract.get("max_forward_states_per_attachment"),
    }
    if dict(contract) != expected_contract:
        audit.failed("frontier.contract", "frontier traversal contract differs from the frozen 3.0.0 algorithm")
        return
    contract_digest = _frontier_contract_digest(contract)
    if candidates.get("traversal_contract_sha256") != contract_digest:
        audit.failed("frontier.contract", "frontier traversal contract SHA-256 does not recompute")
    else:
        audit.passed("frontier.contract", f"frontier traversal contract independently recomputes to {contract_digest}")
    inputs = candidates["input_digests"]
    executor_digest = inputs["executor_manifest_sha256"] if inputs["executor_manifest_sha256"] is not None else "none"
    artifact_id = stable_semantic_id(
        "frontier-candidates",
        inputs["model_fact_overlay_sha256"]
        + "\0"
        + inputs["graph_sha256"]
        + "\0"
        + inputs["cones_sha256"]
        + "\0"
        + executor_digest
        + "\0"
        + contract_digest,
    )
    if candidates.get("artifact_id") != artifact_id:
        audit.failed("frontier.contract", "frontier artifact ID does not bind its inputs and traversal contract")

    traversal = _build_frontier_traversal(
        overlay,
        graph,
        int(contract["max_materialized_model_edges"]),
        audit,
    )
    if traversal is None:
        return
    max_states = int(contract["max_forward_states_per_attachment"])
    raw_actions = overlay.get("external_actions", [])
    actions_by_id: dict[str, Mapping[str, Any]] = {}
    for action in raw_actions:
        action_id = str(action["external_action_id"])
        if action_id in actions_by_id:
            audit.failed("frontier.accounting", f"duplicate external action {action_id}")
            return
        actions_by_id[action_id] = action
    attachments_by_action: dict[str, list[Mapping[str, Any]]] = {}
    for attachment in overlay.get("boundary_attachments", []):
        attachments_by_action.setdefault(str(attachment["external_action_id"]), []).append(attachment)
    for values in attachments_by_action.values():
        values.sort(key=lambda item: str(item["attachment_id"]))
    cones_by_id: dict[str, Mapping[str, Any]] = {}
    for cone in cones.get("cones", []):
        cone_id = str(cone["cone_id"])
        if cone_id in cones_by_id:
            audit.failed("frontier.accounting", f"duplicate cone {cone_id}")
            return
        cones_by_id[cone_id] = cone
    expected_ids: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for action in actions_by_id.values():
        for cone in cones_by_id.values():
            candidate_id = stable_semantic_id(
                "frontier-candidate",
                str(action["external_action_id"])
                + "\0"
                + _frontier_action_identity_material(action)
                + "\0"
                + str(cone["cone_id"]),
            )
            expected_ids[candidate_id] = (action, cone)
    actual_candidates = _unique_map(candidates.get("candidates"), "candidate_id", audit, "frontier semantic candidates")
    if set(actual_candidates) != set(expected_ids):
        audit.failed(
            "frontier.accounting",
            f"candidate cross product differs from actions×cones: expected {len(expected_ids)}, observed {len(actual_candidates)}",
        )
        return
    observed_order = [item.get("candidate_id") for item in candidates.get("candidates", [])]
    if observed_order != sorted(expected_ids):
        audit.failed("frontier.accounting", "frontier candidates are not in deterministic candidate-ID order")

    vm_complete = _frontier_vm_complete(overlay)
    cone_status = m4_cone_status or _frontier_cones_status(cones)
    expected_status = _frontier_status_join(
        str(overlay.get("status", "FAILED")),
        _frontier_status_join(str(graph.get("status", "FAILED")), cone_status),
    )
    if executor is not None:
        expected_status = _frontier_status_join(expected_status, str(executor.get("status", "FAILED")))
    reverse_cache = {
        cone_id: _frontier_reverse_reach(cone, traversal, max_states)
        for cone_id, cone in cones_by_id.items()
    }
    forward_cache: dict[tuple[str, str], _FrontierReach] = {}
    semantic_instances = traversal.semantic_instances
    semantic_failures_before = audit.failures
    for candidate_id in sorted(expected_ids):
        action, cone = expected_ids[candidate_id]
        actual = actual_candidates[candidate_id]
        cone_id = str(cone["cone_id"])
        reverse = reverse_cache[cone_id]
        if actual.get("action") != _frontier_normalized_action(action):
            audit.failed("frontier.candidate", f"candidate {candidate_id} action is not the normalized model action")
        if actual.get("cone_id") != cone_id or actual.get("ap_id") != cone.get("ap_id"):
            audit.failed("frontier.candidate", f"candidate {candidate_id} cone/AP identity differs from the cross product")
        controllability = _frontier_controllability(action, executor)
        completeness = {
            "model_vm_complete": vm_complete,
            "attachment_enumeration_complete": vm_complete,
            "forward_enumeration_complete": (
                traversal.complete
                and graph.get("status") == "COMPLETE"
                and reverse.complete
            ),
            "cone_complete": cone.get("status") == "COMPLETE",
            "compatibility_complete": reverse.compatibility_complete,
            "gap_reasons": list(traversal.gap_reasons),
        }
        gap_reasons = set(completeness["gap_reasons"])
        if not vm_complete:
            gap_reasons.add("model VM or resource ledger is incomplete")
        if graph.get("status") != "COMPLETE":
            gap_reasons.add("contextual graph is conservative-incomplete")
        if cone.get("status") != "COMPLETE":
            gap_reasons.add("influence cone is conservative-incomplete")
        gap_reasons.update(reverse.gap_reasons)
        attachments = attachments_by_action.get(str(action["external_action_id"]), [])
        accounts: list[dict[str, Any]] = []
        witnesses: list[dict[str, Any]] = []
        has_compatible = False
        has_unknown = False
        model_fact_ids: set[str] = set()
        attachment_ids: list[str] = []
        claimed_witnesses = _unique_map(actual.get("witnesses"), "witness_id", audit, f"candidate {candidate_id} witnesses")
        for attachment in attachments:
            attachment_id = str(attachment["attachment_id"])
            attachment_ids.append(attachment_id)
            account = {
                "attachment_id": attachment_id,
                "semantic_node_id": str(attachment["semantic_node_id"]),
                "disposition": "UNRESOLVED",
                "contextual_node_ids": [],
                "witness_ids": [],
                "uncertainty_reasons": [],
            }
            instances = semantic_instances.get(str(attachment["semantic_node_id"]), [])
            if not instances:
                account["uncertainty_reasons"] = ["attachment semantic node has no contextual instance"]
                completeness["attachment_enumeration_complete"] = False
                has_unknown = True
                accounts.append(account)
                continue
            account_compatible = False
            account_unknown = False
            for ordinal in instances:
                boundary = traversal.node_ids[ordinal]
                account["contextual_node_ids"].append(boundary)
                # A zero reverse state proves that this boundary cannot meet
                # the cone only when the reverse fixed point is complete.  If
                # the cone/traversal ledger is incomplete, production keeps
                # the conservative candidate alive and still runs the forward
                # fixed point so that action-local compatibility gaps are
                # accounted (for example, a truncated call context).
                if reverse.complete and not reverse.states[ordinal]:
                    continue
                cache_key = (boundary, str(attachment["certainty"]))
                forward = forward_cache.get(cache_key)
                if forward is None:
                    forward = _frontier_forward_reach(boundary, str(attachment["certainty"]), traversal, max_states)
                    forward_cache[cache_key] = forward
                if not forward.complete:
                    completeness["forward_enumeration_complete"] = False
                if not forward.compatibility_complete:
                    completeness["compatibility_complete"] = False
                gap_reasons.update(forward.gap_reasons)
                if not _frontier_product_mask(forward.states[ordinal], reverse.states[ordinal]):
                    continue
                expected_witness = _frontier_witness_summary(
                    attachment, boundary, cone, forward, reverse, traversal
                )
                witness_id = expected_witness["witness_id"]
                account["witness_ids"].append(witness_id)
                witnesses.append(expected_witness)
                model_fact_ids.update(expected_witness["model_fact_ids"])
                if expected_witness["compatibility"] == "COMPATIBLE":
                    account_compatible = True
                    has_compatible = True
                if expected_witness["meet_summary"]["unknown_path_meet_count"]:
                    account_unknown = True
                    has_unknown = True
                claimed = claimed_witnesses.get(witness_id)
                if claimed is None:
                    audit.failed("frontier.witness", f"candidate {candidate_id} omits recomputed witness {witness_id}")
                    continue
                scalar_fields = {
                    "attachment_id": attachment_id,
                    "boundary_node_id": boundary,
                    "forward_summary": expected_witness["forward_summary"],
                    "meet_summary": expected_witness["meet_summary"],
                    "support_summary": expected_witness["support_summary"],
                    "compatibility": expected_witness["compatibility"],
                    "reachability": expected_witness["reachability"],
                    "model_fact_ids": expected_witness["model_fact_ids"],
                    "uncertainty_reasons": expected_witness["uncertainty_reasons"],
                }
                for field_name, wanted in scalar_fields.items():
                    if claimed.get(field_name) != wanted:
                        audit.failed(
                            "frontier.witness",
                            f"witness {witness_id} {field_name} differs from detached fixed-point reconstruction",
                        )
                _verify_frontier_exemplars(
                    claimed,
                    expected_witness,
                    attachment,
                    boundary,
                    forward,
                    reverse,
                    traversal,
                    audit,
                )
            account["contextual_node_ids"] = sorted(set(account["contextual_node_ids"]))
            account["witness_ids"] = sorted(set(account["witness_ids"]))
            if not account["witness_ids"]:
                if (
                    completeness["forward_enumeration_complete"]
                    and completeness["cone_complete"]
                    and completeness["compatibility_complete"]
                ):
                    account["disposition"] = "NO_MEET"
                else:
                    account["disposition"] = "UNKNOWN"
                    account["uncertainty_reasons"].append("empty meet under an incomplete ledger")
                    account_unknown = True
                    has_unknown = True
            elif account_compatible:
                account["disposition"] = "WITNESSED"
            else:
                account["disposition"] = "UNKNOWN"
            if account_unknown:
                account["uncertainty_reasons"].append(
                    "attachment retains UNKNOWN-compatible witness provenance"
                )
            account["uncertainty_reasons"] = sorted(set(account["uncertainty_reasons"]))
            accounts.append(account)
        if not attachments and not vm_complete:
            has_unknown = True
        completeness["gap_reasons"] = sorted(gap_reasons)
        expected_witness_ids = {item["witness_id"] for item in witnesses}
        if set(claimed_witnesses) != expected_witness_ids:
            audit.failed("frontier.witness", f"candidate {candidate_id} witness ledger is not exact")
        if [
            item.get("witness_id") for item in actual.get("witnesses", [])
        ] != sorted(expected_witness_ids):
            audit.failed(
                "frontier.witness",
                f"candidate {candidate_id} witnesses are not in deterministic witness-ID order",
            )
        if actual.get("attachment_accounting") != accounts:
            audit.failed("frontier.accounting", f"candidate {candidate_id} attachment accounting differs from detached replay")
        strongest = "UNKNOWN"
        for witness in witnesses:
            if witness["reachability"] == "STATIC_WITNESS":
                strongest = "STATIC_WITNESS"
                break
            if witness["reachability"] == "MODELLED_WITNESS":
                strongest = "MODELLED_WITNESS"
        closed = all(
            completeness[field_name]
            for field_name in (
                "model_vm_complete",
                "attachment_enumeration_complete",
                "forward_enumeration_complete",
                "cone_complete",
                "compatibility_complete",
            )
        )
        reachability = strongest if has_compatible else "UNKNOWN" if has_unknown or not closed else "NO_STATIC_WITNESS"
        if reachability == "NO_STATIC_WITNESS" or controllability == "UNAVAILABLE":
            disposition = "REJECTED"
            rank_tier = 4
            rank_reasons = [
                "closed static analysis found no witness"
                if reachability == "NO_STATIC_WITNESS"
                else "executor manifest marks the action unavailable"
            ]
        elif reachability in {"STATIC_WITNESS", "MODELLED_WITNESS"} and controllability in {
            "DIRECT",
            "SEQUENCE",
            "TIMING",
            "ENVIRONMENT",
        }:
            disposition = "ACTIONABLE"
            rank_tier = 0 if reachability == "STATIC_WITNESS" else 1
            rank_reasons = ["static/modelled witness and executor capability intersect"]
        else:
            disposition = "PENDING"
            rank_tier = 3 if reachability == "UNKNOWN" else 2
            rank_reasons = [
                "static witness remains unknown"
                if reachability == "UNKNOWN"
                else "executor controllability remains unknown"
            ]
        uncertainty: set[str] = set()
        if not attachments and not vm_complete:
            uncertainty.add("action has no attachment under an incomplete model ledger")
        if reachability == "UNKNOWN":
            uncertainty.update(completeness["gap_reasons"])
            if not uncertainty:
                uncertainty.add("only UNKNOWN-compatible witnesses were found")
            expected_status = _frontier_status_join(expected_status, "CONSERVATIVE_INCOMPLETE")
        evidence = {
            "reachability": reachability,
            "controllability": controllability,
            "path_feasibility": "NOT_EVALUATED",
            "mutation_semantics": "NOT_EVALUATED",
            "runtime_evidence": "NOT_EVALUATED",
            "model_provenance": {
                "model_pack_sha256s": sorted(set(overlay.get("model_pack_sha256s", []))),
                "attachment_ids": sorted(set(attachment_ids)),
                "model_fact_ids": sorted(model_fact_ids),
            },
            "completeness": completeness,
        }
        expected_candidate_fields = {
            "disposition": disposition,
            "evidence": evidence,
            "rank_tier": rank_tier,
            "rank_reasons": sorted(set(rank_reasons)),
            "uncertainty_reasons": sorted(uncertainty),
        }
        for field_name, wanted in expected_candidate_fields.items():
            if actual.get(field_name) != wanted:
                observed_json = canonical_json_bytes(
                    actual.get(field_name)
                ).decode("utf-8")
                expected_json = canonical_json_bytes(wanted).decode("utf-8")
                audit.failed(
                    "frontier.candidate",
                    f"candidate {candidate_id} {field_name} differs from detached reconstruction; "
                    f"observed={observed_json}; expected={expected_json}",
                )
    if candidates.get("status") != expected_status:
        audit.failed("frontier.candidate", "frontier aggregate status differs from detached candidate replay")

    def gap_collection(document: Mapping[str, Any], field_name: str) -> list[Mapping[str, Any]]:
        value = document.get(field_name, [])
        return list(value) if isinstance(value, list) else []

    gap_by_id: dict[str, Mapping[str, Any]] = {}
    conflicting_gap_ids: set[str] = set()
    def normalized_gap(raw_gap: Mapping[str, Any]) -> dict[str, Any]:
        locations: list[dict[str, Any]] = []
        for raw_location in raw_gap.get("locations", []):
            location = dict(raw_location)
            # The M4 LLVM JSON writer elides an empty macro stack; the compact
            # frontier writer emits the deserialized default explicitly.
            location.setdefault("macro_stack", [])
            locations.append(location)
        return {
            "construct_id": raw_gap.get("construct_id"),
            "kind": raw_gap.get("kind"),
            "effect": raw_gap.get("effect"),
            "detail": raw_gap.get("detail"),
            "locations": locations,
            "affected_ids": list(raw_gap.get("affected_ids", [])),
        }
    for gap in (
        gap_collection(overlay, "coverage_gaps")
        + gap_collection(graph, "unsupported_constructs")
        + gap_collection(cones, "unsupported_constructs")
        + ([] if executor is None else gap_collection(executor, "unsupported_constructs"))
    ):
        gap = normalized_gap(gap)
        gap_id = str(gap.get("construct_id"))
        prior = gap_by_id.get(gap_id)
        if prior is not None and prior != gap:
            conflicting_gap_ids.add(gap_id)
        else:
            gap_by_id[gap_id] = gap
    expected_gaps = sorted(
        gap_by_id.values(),
        key=lambda gap: (str(gap.get("construct_id")), str(gap.get("kind")), str(gap.get("detail"))),
    )
    if candidates.get("unsupported_constructs") != expected_gaps:
        audit.failed("frontier.accounting", "frontier coverage-gap union is not exact")
    expected_diagnostics = sorted(
        f"conflicting coverage-gap payload for stable ID {gap_id}"
        for gap_id in conflicting_gap_ids
    )
    if candidates.get("diagnostics") != expected_diagnostics:
        audit.failed("frontier.accounting", "frontier coverage-gap conflict diagnostics are not exact")
    if audit.failures == semantic_failures_before:
        audit.passed(
            "frontier.recompute",
            f"recomputed {len(traversal.nodes)} nodes, {len(traversal.arcs)} graph/model arcs, {len(expected_ids)} candidates and every compact ledger",
        )

    expected_projection_actions: list[dict[str, Any]] = []
    for candidate in candidates.get("candidates", []):
        if candidate.get("disposition") != "ACTIONABLE":
            continue
        witness_ids = sorted(
            witness["witness_id"]
            for witness in candidate.get("witnesses", [])
            if witness.get("compatibility") == "COMPATIBLE"
        )
        expected_projection_actions.append(
            {
                "candidate_id": candidate["candidate_id"],
                "action": candidate["action"],
                "cone_id": candidate["cone_id"],
                "ap_id": candidate["ap_id"],
                "evidence": candidate["evidence"],
                "witness_ids": witness_ids,
                "rank_tier": candidate["rank_tier"],
                "rank_reasons": candidate["rank_reasons"],
            }
        )
    expected_projection_actions.sort(key=lambda item: (item["rank_tier"], item["candidate_id"]))
    expected_projection = {
        "schema_version": "2.0.0",
        "artifact_id": stable_semantic_id("fuzzable-frontier", frontier_candidates_sha256),
        "frontier_candidates_sha256": frontier_candidates_sha256,
        "actionable_projection_only": True,
        "ranking_never_prunes": True,
        "status": candidates.get("status"),
        "actions": expected_projection_actions,
        "diagnostics": [],
    }
    if frontier != expected_projection:
        audit.failed("frontier.projection", "fuzzable frontier is not the exact deterministic ACTIONABLE projection")
    else:
        audit.passed("frontier.projection", f"exactly projected {len(expected_projection_actions)} ACTIONABLE candidates")


def _verify_artifact_chain(
    m5: Mapping[str, Any],
    m4_artifacts: Mapping[str, Mapping[str, Any]],
    outputs: Mapping[str, Mapping[str, Any]],
    executor_manifest: Mapping[str, Any] | None,
    audit: Audit,
) -> None:
    if set(outputs) != set(M5_OUTPUT_ORDER):
        return
    descriptors = {item["kind"]: item for item in m5["outputs"]}
    m4 = m5["m4_commitments"]
    overlay = outputs["model_fact_overlay"]
    occurrences = outputs["predicate_occurrence_bindings"]
    candidates = outputs["frontier_candidates"]
    frontier = outputs["fuzzable_frontier"]
    recipes = outputs["mutation_recipes"]
    replay = outputs["recipe_replay_obligations"]
    stage_status = {item["name"]: item["status"] for item in m5["stages"]}
    for stage_name, artifact in (
        ("model", overlay),
        ("occurrence", occurrences),
        ("contextualize", candidates),
        ("frontier", frontier),
        ("recipe", recipes),
    ):
        if artifact.get("status") is not None and artifact.get("status") != stage_status[stage_name]:
            audit.failed(
                "artifacts.status",
                f"{stage_name} stage status differs from its semantic output",
            )
    semantic_index = m4_artifacts.get("semantic_index", {})
    expected_occurrence_links = {
        "property_ir_sha256": m4["typed_property_ir"]["sha256"],
        "semantic_index_sha256": m4["semantic_index"]["sha256"],
        "canonical_compilation_database_sha256": semantic_index.get(
            "canonical_compilation_database_sha256"
        ),
        "path_map_sha256": semantic_index.get("path_map_sha256"),
    }
    occurrence_links_good = True
    for key, expected in expected_occurrence_links.items():
        if not isinstance(expected, str) or occurrences.get(key) != expected:
            occurrence_links_good = False
            audit.failed(
                "occurrence.m4_links",
                f"predicate occurrence {key} differs from the physically rehashed M4 artifacts",
            )
    if occurrences.get("m4_index_immutable") is not True:
        occurrence_links_good = False
        audit.failed(
            "occurrence.m4_links",
            "predicate occurrence sidecar does not assert immutable M4 index consumption",
        )
    if occurrence_links_good:
        audit.passed(
            "occurrence.m4_links",
            "predicate occurrence sidecar binds the physical immutable M4 property/index identities",
        )
    _verify_occurrence_type_closure(
        m4_artifacts.get("typed_property_ir", {}), occurrences, audit
    )
    _verify_occurrence_semantic_closure(
        m4_artifacts.get("typed_property_ir", {}),
        semantic_index,
        occurrences,
        audit,
    )
    pack_semantics = sorted(item["semantic_sha256"] for item in m5["model_packs"])
    if overlay.get("semantic_index_identity") != m4["semantic_index"]["sha256"]:
        audit.failed("artifacts.chain", "overlay does not bind physical M4 semantic index SHA")
    if overlay.get("semantic_index_artifact_id") != m4["semantic_index"]["artifact_id"]:
        audit.failed("artifacts.chain", "overlay semantic index artifact ID differs from M4")
    if sorted(overlay.get("model_pack_sha256s", [])) != pack_semantics:
        audit.failed("artifacts.chain", "overlay semantic pack digest set differs from certificate packs")
    _verify_model_overlay_semantics(overlay, semantic_index, audit)
    pack_keys = {
        (item["model_pack_id"], item["model_pack_version"], item["layer"], item["semantic_sha256"])
        for item in m5["model_packs"]
    }
    for provenance in _iter_provenance(overlay):
        key = (
            provenance.get("model_pack_id"),
            provenance.get("model_pack_version"),
            provenance.get("layer"),
            provenance.get("model_pack_sha256"),
        )
        if key not in pack_keys:
            audit.failed("artifacts.chain", f"overlay provenance references undeclared pack identity {key}")
            break
    for candidate in candidates.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        action = candidate.get("action", {})
        for provenance in action.get("provenance", []) if isinstance(action, dict) else []:
            key = (
                provenance.get("model_pack_id"),
                provenance.get("model_pack_version"),
                provenance.get("layer"),
                provenance.get("model_pack_sha256"),
            )
            if key not in pack_keys:
                audit.failed(
                    "artifacts.chain",
                    f"frontier provenance references undeclared pack identity {key}",
                )
                break
        evidence = candidate.get("evidence", {})
        model_provenance = evidence.get("model_provenance", {}) if isinstance(evidence, dict) else {}
        reported = model_provenance.get("model_pack_sha256s", []) if isinstance(model_provenance, dict) else []
        if any(value not in pack_semantics for value in reported):
            audit.failed("artifacts.chain", "frontier evidence references undeclared semantic pack SHA")
    executor_sha = None if m5["executor_manifest"] is None else m5["executor_manifest"]["sha256"]
    expected_candidate_inputs = {
        "model_fact_overlay_sha256": descriptors["model_fact_overlay"]["sha256"],
        "graph_sha256": m4["contextual_influence_graph"]["sha256"],
        "cones_sha256": m4["ap_influence_cones"]["sha256"],
        "executor_manifest_sha256": executor_sha,
    }
    if candidates.get("input_digests") != expected_candidate_inputs:
        audit.failed("artifacts.chain", "frontier candidates self-reported input links differ from physical DAG")
    if frontier.get("frontier_candidates_sha256") != descriptors["frontier_candidates"]["sha256"]:
        audit.failed("artifacts.chain", "fuzzable frontier does not bind physical candidate ledger")
    expected_recipe_links = {
        "property_ir_sha256": m4["typed_property_ir"]["sha256"],
        "ap_bindings_sha256": m4["ap_bindings"]["sha256"],
        "graph_sha256": m4["contextual_influence_graph"]["sha256"],
        "cones_sha256": m4["ap_influence_cones"]["sha256"],
        "frontier_candidates_sha256": descriptors["frontier_candidates"]["sha256"],
        "model_fact_overlay_sha256": descriptors["model_fact_overlay"]["sha256"],
        "predicate_occurrence_bindings_sha256": descriptors[
            "predicate_occurrence_bindings"
        ]["sha256"],
        "analyzer_core_sha256": m5["build_manifest"]["production_core_sha256"],
    }
    for key, expected in expected_recipe_links.items():
        if recipes.get(key) != expected:
            audit.failed("artifacts.chain", f"mutation recipes {key} differs from physical DAG")
    solver_contract = recipes.get("solver_contract", {})
    if (
        solver_contract.get("solver") != "Z3"
        or solver_contract.get("solver_version") != m5["solver"]["actual_version"]
        or solver_contract.get("encoding_version") != SOLVER_ENCODING_VERSION
        or solver_contract.get("timeout_ms") != m5["solver"]["timeout_ms"]
        or solver_contract.get("max_queries") != m5["solver"]["max_queries"]
    ):
        audit.failed(
            "artifacts.chain",
            "mutation recipes solver identity/encoding/budget differs from the certificate contract",
        )
    if replay.get("mutation_recipes_sha256") != descriptors["mutation_recipes"]["sha256"]:
        audit.failed("artifacts.chain", "replay obligations do not bind physical mutation recipes")
    else:
        audit.passed("artifacts.chain", "all M4/model/frontier/recipe physical digest links close")

    candidates_by_id = _unique_map(candidates.get("candidates"), "candidate_id", audit, "frontier candidates")
    recipes_by_candidate = _unique_map(recipes.get("recipes"), "frontier_candidate_id", audit, "mutation recipes")
    actionable = {
        candidate_id
        for candidate_id, candidate in candidates_by_id.items()
        if candidate.get("disposition") == "ACTIONABLE"
    }
    if actionable != set(recipes_by_candidate):
        audit.failed(
            "unknown.totality",
            "ACTIONABLE candidate ledger and recipe ledger do not have exact one-to-one accounting",
        )
    else:
        audit.passed(
            "unknown.totality",
            "every ACTIONABLE candidate has one recipe even when its mutation semantics remain UNKNOWN",
        )
    frontier_ids = set(_unique_map(frontier.get("actions"), "candidate_id", audit, "fuzzable actions"))
    if frontier_ids != actionable:
        audit.failed("frontier.projection", "fuzzable frontier is not the exact ACTIONABLE projection")
    m4_certificate = m4_artifacts.get("analysis_certificate", {})
    m4_cone_status = next(
        (
            str(stage.get("status"))
            for stage in m4_certificate.get("stages", [])
            if isinstance(stage, Mapping) and stage.get("name") == "cone"
        ),
        None,
    )
    _verify_frontier_semantics(
        candidates,
        frontier,
        overlay,
        m4_artifacts.get("contextual_influence_graph", {}),
        m4_artifacts.get("ap_influence_cones", {}),
        executor_manifest,
        descriptors["frontier_candidates"]["sha256"],
        audit,
        m4_cone_status,
    )
    _verify_recipe_solver_contract(recipes, m5["solver"], audit)
    _verify_recipe_semantic_closure(
        recipes,
        m4_artifacts.get("typed_property_ir", {}),
        m4_artifacts.get("contextual_influence_graph", {}),
        candidates,
        overlay,
        audit,
    )
    _verify_replay_reconstruction(
        recipes,
        replay,
        descriptors["mutation_recipes"]["sha256"],
        audit,
    )
    obligations = _unique_map(replay.get("obligations"), "recipe_id", audit, "replay obligations")
    recipes_by_id = _unique_map(recipes.get("recipes"), "recipe_id", audit, "recipe identities")
    if set(obligations) != set(recipes_by_id):
        audit.failed("unknown.totality", "replay obligations do not account for every recipe exactly once")
    for recipe_id, recipe in recipes_by_id.items():
        obligation = obligations.get(recipe_id)
        if not isinstance(obligation, dict):
            continue
        if recipe.get("status") == "UNKNOWN" and (
            obligation.get("status") != "UNKNOWN"
            or obligation.get("expected_relation") != "UNKNOWN"
        ):
            audit.failed(
                "unknown.replay",
                f"UNKNOWN recipe {recipe_id} has an actionable replay claim",
            )


def _verify_certificate_identity_and_time(m5: Mapping[str, Any], audit: Audit) -> None:
    expected = m5_certificate_id(m5)
    if m5.get("certificate_id") != expected:
        audit.failed("certificate.identity", f"certificate_id does not match canonical contract digest {expected}")
    else:
        audit.passed("certificate.identity", "certificate ID binds every non-time contract field")
    try:
        started = dt.datetime.fromisoformat(str(m5["started_at"]).replace("Z", "+00:00"))
        finished = dt.datetime.fromisoformat(str(m5["finished_at"]).replace("Z", "+00:00"))
        if started.tzinfo is None or finished.tzinfo is None or finished < started:
            raise ValueError("timestamps are naive or reversed")
    except ValueError as error:
        audit.failed("certificate.time", str(error))
    else:
        audit.passed("certificate.time", "certificate timestamps are ordered timezone-aware instants")


def verify_certificate(
    certificate_path: pathlib.Path,
    schema_dir: pathlib.Path,
    *,
    validate_semantic_schemas: bool = True,
) -> dict[str, Any]:
    certificate_path = certificate_path.resolve()
    audit = Audit(certificate_path)
    hasher = PhysicalHasher(audit)
    schemas = SchemaSet(schema_dir.resolve())
    try:
        schemas.load()
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as error:
        audit.failed("schema.load", str(error))
        return audit.report(None)
    certificate_sha: str | None = None
    try:
        observed = hasher.rehash(str(certificate_path), "M5 certificate")
        if observed is not None:
            certificate_sha = observed[0]
        m5 = load_json_strict(certificate_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        audit.failed("certificate.load", str(error))
        return audit.report(certificate_sha)
    if not hasher.unchanged(str(certificate_path), "M5 certificate"):
        return audit.report(certificate_sha)
    if not schemas.validate("m5_analysis_certificate.schema.json", m5, audit, "M5 certificate"):
        return audit.report(certificate_sha)
    _verify_certificate_identity_and_time(m5, audit)
    m4_artifacts = _verify_m4(
        m5,
        schemas,
        hasher,
        audit,
        validate_semantic_schemas,
    )
    _verify_model_packs(m5, schemas, hasher, audit, validate_semantic_schemas)
    executor_manifest = _verify_executor(
        m5, schemas, hasher, audit, validate_semantic_schemas
    )
    _verify_runtime(m5, hasher, audit)
    outputs = _verify_outputs(m5, schemas, hasher, audit, validate_semantic_schemas)
    _verify_m5_stages(m5, audit)
    _verify_artifact_chain(
        m5, m4_artifacts, outputs, executor_manifest, audit
    )
    hasher.verify_all_unchanged()
    return audit.report(certificate_sha)


def _write_json(path: pathlib.Path, value: Mapping[str, Any]) -> str:
    path.write_bytes(canonical_json_bytes(value) + b"\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_test(schema_dir: pathlib.Path) -> tuple[int, dict[str, Any]]:
    """Run focused positive/negative certificate-contract regressions.

    The generated semantic artifacts are intentionally skeletal, so this test
    disables their separate production schemas.  It still exercises the closed
    M5 certificate schema, strict JSON loader, every physical hash, both stage
    DAGs, M4 cross-commitments, runtime/solver binding, total candidate/recipe
    accounting and canonical certificate identity.  Production verification
    never disables semantic-schema validation.
    """

    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="rift-m5-cert-selftest-") as raw:
        root = pathlib.Path(raw)

        def save(name: str, value: Mapping[str, Any]) -> dict[str, Any]:
            path = root / name
            digest = _write_json(path, value)
            return {"path": str(path), "sha256": digest}

        integer_type = {
            "kind": "integer",
            "canonical": "int",
            "bit_width": 32,
            "signed": True,
        }
        fixture_tu_id = "tu:" + "1" * 64
        fixture_entity_id = "entity:" + "2" * 64
        fixture_node_id = "node:" + "3" * 64
        fixture_usr = "c:@fixture_value"
        fixture_selector_id = "selector.typed"
        fixture_ap_id = "ap.typed"
        property_value = {
            "selectors": [
                {
                    "selector_id": fixture_selector_id,
                    "kind": "source_location",
                    "location": {
                        "file": "source.c",
                        "line": 1,
                        "column": 5,
                        "end_line": 1,
                        "end_column": 17,
                        "location_kind": "spelling",
                    },
                    "value_type": integer_type,
                }
            ],
            "atomic_propositions": [
                {
                    "ap_id": fixture_ap_id,
                    "roles": ["state"],
                    "value_type": integer_type,
                    "predicate": {
                        "node_kind": "reference",
                        "operator": "decl_ref",
                        "referenced_selector_id": fixture_selector_id,
                        "value_type": integer_type,
                        "operands": [],
                    },
                    "role_selector_groups": [
                        {
                            "group_id": "group.typed",
                            "role": "state",
                            "all_of": [fixture_selector_id],
                        }
                    ],
                }
            ],
        }
        index_value = {
            "artifact_id": "index.neutral",
            "canonical_compilation_database_sha256": "5" * 64,
            "path_map_sha256": "6" * 64,
            "entities": [
                {
                    "entity": {
                        "entity_id": fixture_entity_id,
                        "usr": fixture_usr,
                    },
                    "declarations": [],
                    "definitions": [],
                    "translation_unit_refs": [fixture_tu_id],
                }
            ],
            "semantic_nodes": [
                {
                    "node_id": fixture_node_id,
                    "node_kind": "declaration",
                    "entity_ref": fixture_entity_id,
                    "owner_function_id": None,
                    "access_path": {
                        "root_entity_id": fixture_entity_id,
                        "dereference_depth": 0,
                        "fields": [],
                        "unknown_suffix": False,
                    },
                    "abstract_object_id": None,
                    "value_type": integer_type,
                    "location": {
                        "file": "riftpath://v1/neutral/source.c",
                        "line": 1,
                        "column": 1,
                        "location_kind": "spelling",
                    },
                    "ast_kind": "Var",
                }
            ],
            "abstract_objects": [],
            "translation_units": [{"tu_id": fixture_tu_id}],
        }
        bindings_value = {"artifact_id": "bindings.neutral"}
        graph_value = {"artifact_id": "graph.neutral"}
        cones_value = {"artifact_id": "cones.neutral"}
        compile_value: dict[str, Any] = {}
        source_value = b"int main(void) { return 0; }\n"
        source_path = root / "source.c"
        source_path.write_bytes(source_value)
        files = {
            "typed_property_ir": save("property.json", property_value),
            "compile_commands": save("compile_commands.json", compile_value),
            "semantic_index": save("index.json", index_value),
            "ap_bindings": save("bindings.json", bindings_value),
            "contextual_influence_graph": save("graph.json", graph_value),
            "ap_influence_cones": save("cones.json", cones_value),
        }
        source_sha = sha256_bytes(source_value)
        source_record = {
            "logical_path": "riftpath://v1/neutral/source.c",
            "role": "main",
            "sha256": source_sha,
            "byte_size": len(source_value),
            "observed_paths": [str(source_path)],
        }
        source_manifest_sha = m4_source_manifest_digest([source_record])
        m4_inputs = [
            {"artifact_id": "property.input", "kind": "typed_property_ir", **files["typed_property_ir"]},
            {"artifact_id": "compile.input", "kind": "compile_commands", **files["compile_commands"]},
            {"artifact_id": "source.manifest", "kind": "source_inputs", "sha256": source_manifest_sha},
        ]
        m4_outputs = [
            {"artifact_id": f"{kind}.neutral", "kind": kind, **files[kind]}
            for kind in M4_OUTPUT_ORDER
        ]
        # Keep descriptor IDs equal to the skeletal artifacts.
        for item, kind in zip(m4_outputs, M4_OUTPUT_ORDER):
            item["artifact_id"] = {
                "semantic_index": "index.neutral",
                "ap_bindings": "bindings.neutral",
                "contextual_influence_graph": "graph.neutral",
                "ap_influence_cones": "cones.neutral",
            }[kind]
        m4_stages = [
            {"stage_id": "stage.index", "name": "index", "status": "COMPLETE", "input_sha256": [files["compile_commands"]["sha256"], source_manifest_sha], "output_sha256": [files["semantic_index"]["sha256"]], "diagnostics": []},
            {"stage_id": "stage.bind", "name": "bind", "status": "COMPLETE", "input_sha256": [files["typed_property_ir"]["sha256"], files["semantic_index"]["sha256"]], "output_sha256": [files["ap_bindings"]["sha256"]], "diagnostics": []},
            {"stage_id": "stage.influence", "name": "influence", "status": "COMPLETE", "input_sha256": [files["semantic_index"]["sha256"], files["ap_bindings"]["sha256"]], "output_sha256": [files["contextual_influence_graph"]["sha256"]], "diagnostics": []},
            {"stage_id": "stage.cone", "name": "cone", "status": "COMPLETE", "input_sha256": [files["ap_bindings"]["sha256"], files["contextual_influence_graph"]["sha256"]], "output_sha256": [files["ap_influence_cones"]["sha256"]], "diagnostics": []},
            {"stage_id": "stage.certificate", "name": "certificate", "status": "COMPLETE", "input_sha256": [files[name]["sha256"] for name in M4_OUTPUT_ORDER], "output_sha256": [], "diagnostics": []},
        ]
        m4 = {
            "schema_version": "2.0.0",
            "certificate_id": "m4.certificate",
            "analysis_id": "analysis.neutral",
            "inputs": m4_inputs,
            "outputs": m4_outputs,
            "stages": m4_stages,
            "source_input_provenance": {
                "manifest_sha256": source_manifest_sha,
                "files": [source_record],
            },
        }
        m4_file = save("analysis_certificate.json", m4)

        pack = {
            "schema_version": "2.0.0",
            "model_pack_id": "model.neutral",
            "model_pack_version": "1.0.0",
            "layer": "platform",
            "property_independent": True,
            "target": {
                "target_version": "fixture-1",
                "target_abi": "fixture-abi",
                "evidence_id": "evidence.fixture",
                "digest_policy": "freeze_before_property",
            },
            "resource_limits": {
                "max_selector_matches": 8,
                "max_capture_values": 8,
                "max_join_assignments": 8,
                "max_emitted_facts": 8,
            },
            "selectors": [
                {
                    "selector_id": "selector.fixture",
                    "kind": "exact_qualified_signature",
                    "exact_value": "fixture:int ()",
                }
            ],
            "rules": [
                {
                    "rule_id": "rule.fixture",
                    "matches": [
                        {
                            "match_id": "match.fixture",
                            "selector_ref": "selector.fixture",
                        }
                    ],
                    "captures": [
                        {
                            "capture_id": "capture.fixture",
                            "match_ref": "match.fixture",
                            "projection": "call_result",
                        }
                    ],
                    "joins": [],
                    "emits": [
                        {
                            "emit_id": "emit.fixture",
                            "fact_kind": "external_boundary",
                            "source_capture_ref": "capture.fixture",
                            "certainty": "modelled",
                            "transfer_relation": "fixture_transfer",
                            "external_action": {
                                "action_schema_id": "action.fixture",
                                "action_class": "fixture",
                                "channel": "fixture",
                                "operation": "supply",
                                "payload_type": {
                                    "kind": "integer",
                                    "canonical": "int",
                                    "bit_width": 32,
                                    "signed": True,
                                },
                                "payload_slot": "value",
                                "scope_schema": "process",
                                "generation_schema": "process",
                                "timing_capability": "none",
                                "required_capability": "environment",
                            },
                        }
                    ],
                    "evidence_note": "Generic fixture boundary.",
                }
            ],
        }
        pack_file = save("pack.json", pack)
        semantic_pack_sha = model_pack_semantic_sha256(pack)
        executor = {"artifact_id": "executor.manifest", "executor_id": "executor.neutral", "executor_version": "1.0.0"}
        executor_file = save("executor.json", executor)
        fixture_action = {
            "external_action_id": "action.fixture",
            "action_schema_id": "action.fixture.schema",
            "action_class": "fixture",
            "channel": "fixture",
            "operation": "supply",
            "payload_type": integer_type,
            "payload_slot": "value",
            "scope_schema": "process_epoch",
            "generation_schema": "process_epoch",
            "timing_capability": "none",
            "required_capability": "environment",
            "provenance": [],
        }
        fixture_transfer = {
            "kind": "identity",
            "affine_scale": None,
            "affine_offset": None,
            "precondition": "none",
            "executor_enforces_precondition": False,
            "failure_branch_unknown": False,
        }
        fixture_attachment = {
            "attachment_id": "pending",
            "external_action_id": fixture_action["external_action_id"],
            "semantic_node_id": fixture_node_id,
            "transfer_relation": "fixture_transfer",
            "certainty": "modelled",
            "value_transfer": fixture_transfer,
            "provenance": [],
        }
        fixture_attachment["attachment_id"] = stable_semantic_id(
            "boundary-attachment",
            "\0".join(
                (
                    fixture_attachment["external_action_id"],
                    fixture_attachment["semantic_node_id"],
                    fixture_attachment["transfer_relation"],
                    _typed_value_transfer_material(fixture_transfer),
                )
            ),
        )
        overlay = {
            "schema_version": "1.0.0",
            "artifact_id": "pending",
            "semantic_index_artifact_id": "index.neutral",
            "semantic_index_identity": files["semantic_index"]["sha256"],
            "status": "COMPLETE",
            "model_pack_sha256s": [semantic_pack_sha],
            "external_actions": [fixture_action],
            "boundary_attachments": [fixture_attachment],
            "semantic_facts": [],
            "joint_action_constraints": [],
            "unknown_outcomes": [],
            "resource_ledger": [],
            "coverage_gaps": [],
            "diagnostics": [],
        }
        overlay["artifact_id"] = stable_semantic_id(
            "model-overlay", _overlay_identity_material(overlay)
        )
        overlay_file = save("model_fact_overlay.json", overlay)
        spelling_location = {
            "file": "riftpath://v1/neutral/source.c",
            "line": 1,
            "column": 5,
            "end_line": 1,
            "end_column": 18,
            "location_kind": "spelling",
            "macro_stack": [],
        }
        expansion_location = {
            **spelling_location,
            "location_kind": "expansion",
        }
        occurrence_material = "\0".join(
            (
                fixture_ap_id,
                fixture_selector_id,
                fixture_tu_id,
                "decl_ref",
                "riftpath://v1/neutral/source.c:1:5:spelling",
                "riftpath://v1/neutral/source.c:1:5:expansion",
                fixture_usr,
                "no-access-path",
                "no-object",
            )
        )
        fixture_occurrence_id = stable_semantic_id(
            "predicate-occurrence", occurrence_material
        )
        occurrences = {
            "schema_version": "1.0.0",
            "artifact_id": "occurrences.neutral",
            "property_ir_sha256": files["typed_property_ir"]["sha256"],
            "semantic_index_sha256": files["semantic_index"]["sha256"],
            "canonical_compilation_database_sha256": index_value[
                "canonical_compilation_database_sha256"
            ],
            "path_map_sha256": index_value["path_map_sha256"],
            "m4_index_immutable": True,
            "candidate_accounting_complete": True,
            "options": {
                "maximum_translation_units": 1,
                "maximum_occurrences": 1,
                "retain_macro_stack": True,
            },
            "eligible_translation_units": 1,
            "parsed_translation_units": 1,
            "skipped_translation_units": 0,
            "observed_occurrences": 1,
            "status": "COMPLETE",
            "selector_accounts": [
                {
                    "ap_id": fixture_ap_id,
                    "selector_id": fixture_selector_id,
                    "roles": ["state"],
                    "predicate_paths": ["predicate"],
                    "expected_value_type": integer_type,
                    "requested_location": {
                        **property_value["selectors"][0]["location"],
                        "macro_stack": [],
                    },
                    "eligible_translation_unit_ids": [fixture_tu_id],
                    "parsed_translation_unit_ids": [fixture_tu_id],
                    "occurrence_ids": [fixture_occurrence_id],
                    "resolution": "EXACT",
                    "uncertainty_reasons": [],
                }
            ],
            "occurrences": [
                {
                    "occurrence_id": fixture_occurrence_id,
                    "ap_id": fixture_ap_id,
                    "selector_id": fixture_selector_id,
                    "roles": ["state"],
                    "predicate_paths": ["predicate"],
                    "translation_unit_id": fixture_tu_id,
                    "kind": "decl_ref",
                    "spelling_location": spelling_location,
                    "expansion_location": expansion_location,
                    "referenced_usr": fixture_usr,
                    "referenced_entity_id": fixture_entity_id,
                    "semantic_node_ids": [fixture_node_id],
                    "value_type": integer_type,
                    "access_path": None,
                    "member_base_entity_id": None,
                    "member_abstract_object_id": None,
                    "certainty": "must",
                    "resolution": "EXACT",
                    "uncertainty_reasons": [],
                }
            ],
            "coverage_gaps": [],
            "diagnostics": [],
        }
        occurrences_file = save(
            "predicate_occurrence_bindings.json", occurrences
        )
        candidates = {
            "artifact_id": "candidates.neutral",
            "input_digests": {
                "model_fact_overlay_sha256": overlay_file["sha256"],
                "graph_sha256": files["contextual_influence_graph"]["sha256"],
                "cones_sha256": files["ap_influence_cones"]["sha256"],
                "executor_manifest_sha256": executor_file["sha256"],
            },
            "candidates": [
                {
                    "candidate_id": "candidate.fixture",
                    "cone_id": "cone.fixture",
                    "ap_id": fixture_ap_id,
                    "disposition": "ACTIONABLE",
                    "action": fixture_action,
                    "witnesses": [
                        {
                            "attachment_id": fixture_attachment[
                                "attachment_id"
                            ],
                            "compatibility": "COMPATIBLE",
                            "model_fact_ids": [],
                            "path_exemplars": [],
                        }
                    ],
                }
            ],
        }
        candidates_file = save("frontier_candidates.json", candidates)
        frontier = {
            "artifact_id": "frontier.neutral",
            "frontier_candidates_sha256": candidates_file["sha256"],
            "actions": [{"candidate_id": "candidate.fixture"}],
        }
        frontier_file = save("fuzzable_frontier.json", frontier)
        fixture_query_sha256 = "7" * 64
        fixture_hyperedge_id = stable_semantic_id(
            "action-hyperedge", fixture_action["external_action_id"]
        )
        fixture_recipe_id = stable_semantic_id(
            "recipe",
            "\0".join(
                (
                    "candidate.fixture",
                    "cone.fixture",
                    fixture_ap_id,
                    fixture_query_sha256,
                    fixture_action["external_action_id"],
                )
            ),
        )
        recipes = {
            "artifact_id": "pending",
            "property_ir_sha256": files["typed_property_ir"]["sha256"],
            "ap_bindings_sha256": files["ap_bindings"]["sha256"],
            "graph_sha256": files["contextual_influence_graph"]["sha256"],
            "cones_sha256": files["ap_influence_cones"]["sha256"],
            "frontier_candidates_sha256": candidates_file["sha256"],
            "model_fact_overlay_sha256": overlay_file["sha256"],
            "predicate_occurrence_bindings_sha256": occurrences_file["sha256"],
            "analyzer_core_sha256": "3" * 64,
            "solver_contract": {
                "solver": "Z3",
                "solver_version": "4.8.12",
                "encoding_version": SOLVER_ENCODING_VERSION,
                "timeout_ms": 100,
                "max_queries": 10000,
            },
            "candidate_accounting_complete": True,
            "recipes": [
                {
                    "recipe_id": fixture_recipe_id,
                    "frontier_candidate_id": "candidate.fixture",
                    "cone_id": "cone.fixture",
                    "ap_id": fixture_ap_id,
                    "target_predicate_selector_id": fixture_selector_id,
                    "status": "HEURISTIC",
                    "action_hyperedge": {
                        "hyperedge_id": fixture_hyperedge_id,
                        "action_ids": ["action.fixture"],
                        "indivisible": True,
                        "claim": "SINGLE_ACTION",
                    },
                    "action_mutations": [
                        {
                            "action_id": "action.fixture",
                            "mutation_kind": "BOUNDARY_SET",
                            "direction": "BOUNDARY_SET",
                            "suggested_values": [
                                {"canonical": "1", "value_type": integer_type}
                            ],
                            "unknown_reasons": [],
                        }
                    ],
                    "prerequisite_choices": [],
                    "timing": {
                        "status": "UNKNOWN",
                        "scope_schema": "process_epoch",
                        "generation_schema": "process_epoch",
                    },
                    "solver_query": {
                        "query_sha256": fixture_query_sha256,
                        "solver": "Z3",
                        "solver_version": "4.8.12",
                        "encoding_version": SOLVER_ENCODING_VERSION,
                        "timeout_ms": 100,
                        "outcome": "SAT",
                    },
                    "direction_query": None,
                }
            ],
        }
        recipes["artifact_id"] = stable_semantic_id(
            "mutation-recipes",
            "\0".join(
                (
                    recipes["property_ir_sha256"],
                    recipes["ap_bindings_sha256"],
                    recipes["graph_sha256"],
                    recipes["cones_sha256"],
                    recipes["frontier_candidates_sha256"],
                    recipes["model_fact_overlay_sha256"],
                    recipes["predicate_occurrence_bindings_sha256"],
                    recipes["analyzer_core_sha256"],
                    recipes["solver_contract"]["solver_version"],
                    str(recipes["solver_contract"]["timeout_ms"]),
                    str(recipes["solver_contract"]["max_queries"]),
                )
            ),
        )
        recipes_file = save("mutation_recipes.json", recipes)
        replay = {
            "schema_version": "1.0.0",
            "artifact_id": stable_semantic_id(
                "recipe-replay-obligations", recipes_file["sha256"]
            ),
            "mutation_recipes_sha256": recipes_file["sha256"],
            "candidate_accounting_complete": True,
            "obligations": [
                {
                    "obligation_id": stable_semantic_id(
                        "replay-obligation",
                        fixture_recipe_id + "\0" + recipes_file["sha256"],
                    ),
                    "recipe_id": fixture_recipe_id,
                    "frontier_candidate_id": "candidate.fixture",
                    "status": "PARTIAL",
                    "atomic_action_ids": ["action.fixture"],
                    "indivisible_hyperedge": True,
                    "ordered_step_ids": [],
                    "required_observations": [
                        "ACTION_ACCEPTED",
                        "AP_AFTER",
                        "AP_BEFORE",
                        "GENERATION_IDENTITY",
                        "SCOPE_IDENTITY",
                    ],
                    "expected_relation": "AP_TRUTH_CHANGE",
                    "solver_query_sha256": "7" * 64,
                    "scope_schema": "process_epoch",
                    "generation_schema": "process_epoch",
                    "timing_status": "UNKNOWN",
                    "uncertainty_reasons": [
                        "mutation recipe is HEURISTIC rather than SUPPORTED",
                        "timing contract is widened or unknown",
                    ],
                }
            ],
        }
        replay_file = save("recipe_replay_obligations.json", replay)

        analyzer_path = root / "tafuzz-sa"
        analyzer_path.write_bytes(b"analyzer\n")
        solver_path = root / "libz3.so"
        solver_path.write_bytes(b"z3\n")
        analyzer_component = {
            "name": "tafuzz-sa executable", "version": "0.2.0", "component_kind": "executable",
            "sha256": sha256_bytes(analyzer_path.read_bytes()), "path": str(analyzer_path),
        }
        analyzer_component["component_id"] = runtime_component_id(analyzer_component)
        solver_component = {
            "name": "libz3.so", "version": "4.8.12", "component_kind": "shared_object",
            "sha256": sha256_bytes(solver_path.read_bytes()), "path": str(solver_path),
        }
        solver_component["component_id"] = runtime_component_id(solver_component)
        solver_record = {
            "name": "Z3",
            "actual_version": "4.8.12",
            "runtime_component_id": solver_component["component_id"],
            "component_sha256": solver_component["sha256"],
            "timeout_ms": 100,
            "max_queries": 10000,
            "queries": 1,
            "timeouts": 0,
            "unsupported": 0,
        }
        solver_record["budget_sha256"] = solver_budget_sha256(solver_record)
        checks.append(
            {
                "name": "solver_budget_digest_regression",
                "verdict": (
                    "PASS"
                    if solver_record["budget_sha256"]
                    == SOLVER_BUDGET_REGRESSION_SHA256
                    else "FAIL"
                ),
                "failures": int(
                    solver_record["budget_sha256"]
                    != SOLVER_BUDGET_REGRESSION_SHA256
                ),
                "expected": "PASS",
                "observed_sha256": solver_record["budget_sha256"],
            }
        )
        m5_outputs = [
            {
                "artifact_id": overlay["artifact_id"],
                "kind": "model_fact_overlay",
                **overlay_file,
            },
            {
                "artifact_id": "occurrences.neutral",
                "kind": "predicate_occurrence_bindings",
                **occurrences_file,
            },
            {"artifact_id": "candidates.neutral", "kind": "frontier_candidates", **candidates_file},
            {"artifact_id": "frontier.neutral", "kind": "fuzzable_frontier", **frontier_file},
            {
                "artifact_id": recipes["artifact_id"],
                "kind": "mutation_recipes",
                **recipes_file,
            },
            {
                "artifact_id": replay["artifact_id"],
                "kind": "recipe_replay_obligations",
                **replay_file,
            },
        ]
        m5 = {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "m5-certificate:" + "0" * 64,
            "analysis_id": "analysis.neutral",
            "status": "COMPLETE",
            "analyzer": {
                "name": "tafuzz-sa", "version": "0.2.0",
                "binary_sha256": analyzer_component["sha256"], "binary_path": str(analyzer_path),
                "runtime_component_id": analyzer_component["component_id"], "configuration_sha256": "2" * 64,
            },
            "build_manifest": {
                "identity_policy": "relative-path-and-content-v1", "manifest_sha256": "1" * 64,
                "production_core_sha256": "3" * 64, "schema_bundle_sha256": "4" * 64,
            },
            "m4_commitments": {
                "analysis_certificate": {"artifact_id": "m4.certificate", "kind": "m4_analysis_certificate", **m4_file},
                "typed_property_ir": m4_outputs[0] if False else m4_inputs[0],
                "semantic_index": m4_outputs[0], "ap_bindings": m4_outputs[1],
                "contextual_influence_graph": m4_outputs[2], "ap_influence_cones": m4_outputs[3],
            },
            "model_packs": [{
                "model_pack_id": "model.neutral", "model_pack_version": "1.0.0", "layer": "platform",
                "sha256": pack_file["sha256"], "semantic_sha256": semantic_pack_sha, "path": pack_file["path"],
            }],
            "executor_manifest": {
                "executor_id": "executor.neutral", "executor_version": "1.0.0", "artifact_id": "executor.manifest",
                "sha256": executor_file["sha256"], "path": executor_file["path"],
            },
            "runtime_components": [analyzer_component, solver_component],
            "solver": solver_record,
            "outputs": m5_outputs,
            "stages": [],
            "invariants": {
                "model_vm_executed_before_property_load": True, "m4_cone_immutable": True,
                "ranking_never_prunes": True, "unknown_never_means_unsat": True,
                "unknown_candidates_retained": True, "unknown_recipe_emitted": True,
                "unsupported_or_timeout_preserved_as_unknown": True,
                "pack_cannot_assert_must": True, "executor_capability_independent": True,
            },
            "diagnostics": [],
            "started_at": "2026-07-18T00:00:00Z", "finished_at": "2026-07-18T00:00:01Z",
        }
        expected_stages = _expected_m5_stages(m5)
        m5["stages"] = [
            {"stage_id": f"stage.{name}", "name": name, "status": "COMPLETE", "input_sha256": expected_stages[name][0], "output_sha256": expected_stages[name][1], "diagnostics": []}
            for name in STAGE_ORDER
        ]
        m5["certificate_id"] = m5_certificate_id(m5)
        certificate_path = root / "m5_analysis_certificate.json"
        _write_json(certificate_path, m5)

        positive = verify_certificate(certificate_path, schema_dir, validate_semantic_schemas=False)
        checks.append(
            {
                "name": "positive",
                "verdict": positive["verdict"],
                "failures": positive["failures"],
                "failure_details": [
                    item["detail"]
                    for item in positive["findings"]
                    if item["status"] == "FAIL"
                ],
                "verifier_checks": positive["checks"],
                "physical_files_rehashed": positive["physical_files_rehashed"],
            }
        )

        # A complete, tiny frontier/3 fixture exercises the detached fixed
        # point itself.  Unlike the older certificate fixture above, these
        # claims are reconstructed from graph/model/cone bytes before being
        # accepted.  The negative cases coherently mutate semantic claims, so
        # merely rehashing downstream files would not make them pass.
        def frontier_node(node_id: str, semantic_id: str) -> dict[str, Any]:
            return {
                "node_id": node_id,
                "semantic_node_ref": semantic_id,
                "call_context": {
                    "policy": "root",
                    "callsite_ids": [],
                    "truncated": False,
                },
                "abstract_object": {
                    "object_id": "object.shared",
                    "abstraction": "global",
                    "certainty": "must",
                },
                "scope": {
                    "scope_id": "scope.shared",
                    "key_node_ids": [],
                    "status": "exact",
                },
                "generation": {
                    "kind": "exact",
                    "identity": "generation.shared",
                    "reuse_possible": False,
                },
                "task_context": {
                    "kind": "process",
                    "context_id": "task.shared",
                    "certainty": "must",
                },
                "lifecycle_phase": "active",
            }

        frontier_graph = {
            "status": "COMPLETE",
            "nodes": [
                frontier_node("cig:a", "semantic:a"),
                frontier_node("cig:b", "semantic:b"),
                frontier_node("cig:c", "semantic:c"),
            ],
            "edges": [
                {
                    "edge_id": "edge:ab",
                    "source_node_id": "cig:a",
                    "target_node_id": "cig:b",
                    "relation_kind": "data",
                    "certainty": "must",
                    "uncertainty_reasons": [],
                },
            ],
            "unsupported_constructs": [],
        }
        frontier_provenance = {
            "model_pack_id": "pack.fixture",
            "model_pack_version": "1.0.0",
            "model_pack_sha256": "a" * 64,
            "layer": "framework",
            "rule_id": "rule.fixture",
            "emit_id": "emit.fixture",
            "selector_ids": ["selector.fixture"],
            "capture_ids": [],
            "matched_semantic_node_ids": ["semantic:a"],
        }
        frontier_action = {
            "external_action_id": "external-action:fixture",
            "action_schema_id": "action-schema:fixture",
            "action_class": "parameter",
            "channel": "fixture",
            "operation": "set",
            "payload_type": integer_type,
            "payload_slot": "value",
            "scope_schema": "scope.shared",
            "generation_schema": "generation.shared",
            "timing_capability": "none",
            "required_capability": "fixture.set",
            "provenance": [frontier_provenance],
        }
        frontier_attachment = {
            "attachment_id": "attachment:fixture",
            "external_action_id": frontier_action["external_action_id"],
            "semantic_node_id": "semantic:a",
            "transfer_relation": "argument",
            "certainty": "modelled",
            "provenance": [frontier_provenance],
        }
        frontier_overlay = {
            "status": "COMPLETE",
            "model_pack_sha256s": ["a" * 64],
            "external_actions": [frontier_action],
            "boundary_attachments": [frontier_attachment],
            "semantic_facts": [
                {
                    "fact_id": "model-fact:bc",
                    "kind": "semantic_transfer",
                    "source_semantic_node_id": "semantic:b",
                    "target_semantic_node_id": "semantic:c",
                    "transfer_relation": "fixture-transfer",
                    "certainty": "modelled",
                    "provenance": [frontier_provenance],
                }
            ],
            "unknown_outcomes": [],
            "resource_ledger": [],
            "coverage_gaps": [],
        }
        frontier_cone = {
            "cone_id": "cone:fixture",
            "ap_id": "ap:fixture",
            "candidate_accounting": [
                {
                    "binding_id": "binding:fixture",
                    "disposition": "INCLUDED",
                    "root_node_ids": ["cig:c"],
                }
            ],
            "members": [
                {
                    "node_id": "cig:c",
                    "membership": "MUST_INFLUENCE",
                    "witness_edge_ids": [],
                }
            ],
            "status": "COMPLETE",
        }
        frontier_cones = {
            "cones": [frontier_cone],
            "unsupported_constructs": [],
        }
        frontier_executor = {
            "status": "COMPLETE",
            "capabilities": [
                {
                    "required_capability": "fixture.set",
                    "action_schema_id": "action-schema:fixture",
                    "controllability": "DIRECT",
                }
            ],
            "unsupported_constructs": [],
        }
        frontier_contract = {
            **FRONTIER_TRAVERSAL_DEFAULTS,
            "max_materialized_model_edges": 100,
            "max_forward_states_per_attachment": 100,
        }
        frontier_contract_sha = _frontier_contract_digest(frontier_contract)
        frontier_inputs = {
            "model_fact_overlay_sha256": "1" * 64,
            "graph_sha256": "2" * 64,
            "cones_sha256": "3" * 64,
            "executor_manifest_sha256": "4" * 64,
        }
        frontier_traversal = _build_frontier_traversal(
            frontier_overlay, frontier_graph, 100, Audit(root / "frontier-build")
        )
        assert frontier_traversal is not None
        frontier_reverse = _frontier_reverse_reach(
            frontier_cone, frontier_traversal, 100
        )
        frontier_forward = _frontier_forward_reach(
            "cig:a", "modelled", frontier_traversal, 100
        )
        frontier_witness_expected = _frontier_witness_summary(
            frontier_attachment,
            "cig:a",
            frontier_cone,
            frontier_forward,
            frontier_reverse,
            frontier_traversal,
        )
        frontier_exemplar = {
            "effective_path_class": "MODELLED",
            "raw_forward_path_class": "MODELLED",
            "raw_root_path_class": "MODELLED",
            "meet_node_id": "cig:a",
            "root_node_id": "cig:c",
            "compatibility": "COMPATIBLE",
            "reachability": "MODELLED_WITNESS",
            "forward_steps": [],
            "root_steps": [
                {
                    "kind": "GRAPH_EDGE",
                    "source_node_id": "cig:a",
                    "target_node_id": "cig:b",
                    "graph_edge_id": "edge:ab",
                    "model_fact_id": None,
                },
                {
                    "kind": "MODEL_ARC",
                    "source_node_id": "cig:b",
                    "target_node_id": "cig:c",
                    "graph_edge_id": None,
                    "model_fact_id": "model-fact:bc",
                },
            ],
            "representative_only": True,
            "uncertainty_reasons": [],
        }
        frontier_witness = {
            "witness_id": frontier_witness_expected["witness_id"],
            "attachment_id": frontier_attachment["attachment_id"],
            "boundary_node_id": "cig:a",
            "forward_summary": frontier_witness_expected["forward_summary"],
            "meet_summary": frontier_witness_expected["meet_summary"],
            "support_summary": frontier_witness_expected["support_summary"],
            "path_exemplars": [frontier_exemplar],
            "compatibility": "COMPATIBLE",
            "reachability": "MODELLED_WITNESS",
            "model_fact_ids": ["model-fact:bc"],
            "uncertainty_reasons": [],
        }
        frontier_candidate_id = stable_semantic_id(
            "frontier-candidate",
            frontier_action["external_action_id"]
            + "\0"
            + _frontier_action_identity_material(frontier_action)
            + "\0"
            + frontier_cone["cone_id"],
        )
        frontier_evidence = {
            "reachability": "MODELLED_WITNESS",
            "controllability": "DIRECT",
            "path_feasibility": "NOT_EVALUATED",
            "mutation_semantics": "NOT_EVALUATED",
            "runtime_evidence": "NOT_EVALUATED",
            "model_provenance": {
                "model_pack_sha256s": ["a" * 64],
                "attachment_ids": [frontier_attachment["attachment_id"]],
                "model_fact_ids": ["model-fact:bc"],
            },
            "completeness": {
                "model_vm_complete": True,
                "attachment_enumeration_complete": True,
                "forward_enumeration_complete": True,
                "cone_complete": True,
                "compatibility_complete": True,
                "gap_reasons": [],
            },
        }
        frontier_candidate = {
            "candidate_id": frontier_candidate_id,
            "action": frontier_action,
            "cone_id": frontier_cone["cone_id"],
            "ap_id": frontier_cone["ap_id"],
            "disposition": "ACTIONABLE",
            "evidence": frontier_evidence,
            "attachment_accounting": [
                {
                    "attachment_id": frontier_attachment["attachment_id"],
                    "semantic_node_id": "semantic:a",
                    "disposition": "WITNESSED",
                    "contextual_node_ids": ["cig:a"],
                    "witness_ids": [frontier_witness["witness_id"]],
                    "uncertainty_reasons": [],
                }
            ],
            "witnesses": [frontier_witness],
            "rank_tier": 1,
            "rank_reasons": [
                "static/modelled witness and executor capability intersect"
            ],
            "uncertainty_reasons": [],
        }
        frontier_candidate_artifact = {
            "schema_version": "3.0.0",
            "artifact_id": stable_semantic_id(
                "frontier-candidates",
                frontier_inputs["model_fact_overlay_sha256"]
                + "\0"
                + frontier_inputs["graph_sha256"]
                + "\0"
                + frontier_inputs["cones_sha256"]
                + "\0"
                + frontier_inputs["executor_manifest_sha256"]
                + "\0"
                + frontier_contract_sha,
            ),
            "input_digests": frontier_inputs,
            "traversal_contract": frontier_contract,
            "traversal_contract_sha256": frontier_contract_sha,
            "candidate_accounting_complete": True,
            "ranking_never_prunes": True,
            "status": "COMPLETE",
            "candidates": [frontier_candidate],
            "unsupported_constructs": [],
            "diagnostics": [],
        }
        frontier_fixture_digest = "5" * 64
        frontier_projection = {
            "schema_version": "2.0.0",
            "artifact_id": stable_semantic_id(
                "fuzzable-frontier", frontier_fixture_digest
            ),
            "frontier_candidates_sha256": frontier_fixture_digest,
            "actionable_projection_only": True,
            "ranking_never_prunes": True,
            "status": "COMPLETE",
            "actions": [
                {
                    "candidate_id": frontier_candidate_id,
                    "action": frontier_action,
                    "cone_id": frontier_cone["cone_id"],
                    "ap_id": frontier_cone["ap_id"],
                    "evidence": frontier_evidence,
                    "witness_ids": [frontier_witness["witness_id"]],
                    "rank_tier": 1,
                    "rank_reasons": [
                        "static/modelled witness and executor capability intersect"
                    ],
                }
            ],
            "diagnostics": [],
        }

        def frontier_semantic_case(
            name: str,
            candidate_document: Mapping[str, Any],
            projection_document: Mapping[str, Any],
            expected_verdict: str,
        ) -> None:
            case_audit = Audit(root / f"{name}.json")
            _verify_frontier_semantics(
                candidate_document,
                projection_document,
                frontier_overlay,
                frontier_graph,
                frontier_cones,
                frontier_executor,
                frontier_fixture_digest,
                case_audit,
            )
            result = case_audit.report(None)
            checks.append(
                {
                    "name": name,
                    "verdict": result["verdict"],
                    "failures": result["failures"],
                    "expected": expected_verdict,
                }
            )

        frontier_semantic_case(
            "frontier_schema3_detached_positive",
            frontier_candidate_artifact,
            frontier_projection,
            "PASS",
        )
        for name, mutate in (
            (
                "frontier_schema3_contract_digest_negative",
                lambda value: value.__setitem__(
                    "traversal_contract_sha256", "f" * 64
                ),
            ),
            (
                "frontier_schema3_meet_count_negative",
                lambda value: value["candidates"][0]["witnesses"][0][
                    "meet_summary"
                ].__setitem__("meet_count", 99),
            ),
            (
                "frontier_schema3_meet_digest_negative",
                lambda value: value["candidates"][0]["witnesses"][0][
                    "meet_summary"
                ].__setitem__("ledger_sha256", "e" * 64),
            ),
            (
                "frontier_schema3_reach_digest_negative",
                lambda value: value["candidates"][0]["witnesses"][0][
                    "forward_summary"
                ].__setitem__("reached_state_ledger_sha256", "d" * 64),
            ),
            (
                "frontier_schema3_support_count_negative",
                lambda value: value["candidates"][0]["witnesses"][0][
                    "support_summary"
                ].__setitem__("supporting_transition_count", 0),
            ),
            (
                "frontier_schema3_support_digest_negative",
                lambda value: value["candidates"][0]["witnesses"][0][
                    "support_summary"
                ].__setitem__("supporting_transition_ledger_sha256", "c" * 64),
            ),
            (
                "frontier_schema3_exemplar_edge_negative",
                lambda value: value["candidates"][0]["witnesses"][0][
                    "path_exemplars"
                ][0]["root_steps"][0].__setitem__("graph_edge_id", "edge:wrong"),
            ),
        ):
            changed_candidates = copy.deepcopy(frontier_candidate_artifact)
            mutate(changed_candidates)
            frontier_semantic_case(
                name, changed_candidates, frontier_projection, "FAIL"
            )

        # Coherent rehash regressions: an author controlling the M5 sidecars
        # may update every downstream digest and certificate identity.  The
        # detached verifier must still reject claims that do not follow from
        # the immutable M4 semantic index or from the mutation recipe.
        absent_node_occurrences = copy.deepcopy(occurrences)
        absent_node_occurrences["occurrences"][0]["semantic_node_ids"] = [
            "node:" + "f" * 64
        ]
        absent_node_file = save(
            "coherent_absent_node_occurrences.json", absent_node_occurrences
        )
        absent_node_recipes = copy.deepcopy(recipes)
        absent_node_recipes["predicate_occurrence_bindings_sha256"] = (
            absent_node_file["sha256"]
        )
        absent_node_recipes_file = save(
            "coherent_absent_node_recipes.json", absent_node_recipes
        )
        absent_node_replay = copy.deepcopy(replay)
        absent_node_replay["mutation_recipes_sha256"] = (
            absent_node_recipes_file["sha256"]
        )
        absent_node_replay["artifact_id"] = stable_semantic_id(
            "recipe-replay-obligations", absent_node_recipes_file["sha256"]
        )
        absent_node_replay["obligations"][0]["obligation_id"] = (
            stable_semantic_id(
                "replay-obligation",
                fixture_recipe_id + "\0" + absent_node_recipes_file["sha256"],
            )
        )
        absent_node_replay_file = save(
            "coherent_absent_node_replay.json", absent_node_replay
        )
        absent_node_certificate = copy.deepcopy(m5)
        for index, (document, replacement) in enumerate(
            (
                (absent_node_occurrences, absent_node_file),
                (absent_node_recipes, absent_node_recipes_file),
                (absent_node_replay, absent_node_replay_file),
            ),
            start=1,
        ):
            output_index = index if index == 1 else index + 2
            absent_node_certificate["outputs"][output_index].update(
                artifact_id=document["artifact_id"], **replacement
            )
        absent_node_expected = _expected_m5_stages(absent_node_certificate)
        for stage in absent_node_certificate["stages"]:
            stage["input_sha256"], stage["output_sha256"] = (
                absent_node_expected[stage["name"]]
            )
        absent_node_certificate["certificate_id"] = m5_certificate_id(
            absent_node_certificate
        )
        absent_node_certificate_path = root / "coherent_absent_node_m5.json"
        _write_json(absent_node_certificate_path, absent_node_certificate)
        absent_node_result = verify_certificate(
            absent_node_certificate_path,
            schema_dir,
            validate_semantic_schemas=False,
        )
        checks.append(
            {
                "name": "coherent_absent_occurrence_node",
                "verdict": absent_node_result["verdict"],
                "failures": absent_node_result["failures"],
                "expected": "FAIL",
            }
        )

        ready_replay = copy.deepcopy(replay)
        ready_replay["obligations"][0]["status"] = "READY"
        ready_replay["obligations"][0]["uncertainty_reasons"] = []
        ready_replay_file = save("coherent_false_ready_replay.json", ready_replay)
        ready_certificate = copy.deepcopy(m5)
        ready_certificate["outputs"][5].update(
            artifact_id=ready_replay["artifact_id"], **ready_replay_file
        )
        ready_expected = _expected_m5_stages(ready_certificate)
        for stage in ready_certificate["stages"]:
            stage["input_sha256"], stage["output_sha256"] = ready_expected[
                stage["name"]
            ]
        ready_certificate["certificate_id"] = m5_certificate_id(
            ready_certificate
        )
        ready_certificate_path = root / "coherent_false_ready_m5.json"
        _write_json(ready_certificate_path, ready_certificate)
        ready_result = verify_certificate(
            ready_certificate_path,
            schema_dir,
            validate_semantic_schemas=False,
        )
        checks.append(
            {
                "name": "coherent_false_ready_replay",
                "verdict": ready_result["verdict"],
                "failures": ready_result["failures"],
                "expected": "FAIL",
            }
        )

        replay_field_mutations: dict[str, Any] = {
            "obligation_id": "replay-obligation:" + "f" * 64,
            "recipe_id": "recipe.changed",
            "frontier_candidate_id": "candidate.changed",
            "status": "READY",
            "atomic_action_ids": ["action.changed"],
            "indivisible_hyperedge": False,
            "ordered_step_ids": ["step.changed"],
            "required_observations": [
                "ACTION_ACCEPTED",
                "AP_AFTER",
                "AP_BEFORE",
                "GENERATION_IDENTITY",
                "MONITOR_SUCCESSOR",
                "SCOPE_IDENTITY",
            ],
            "expected_relation": "UNKNOWN",
            "solver_query_sha256": "8" * 64,
            "scope_schema": "changed_scope",
            "generation_schema": "changed_generation",
            "timing_status": "EXACT",
            "uncertainty_reasons": ["tampered replay reason"],
        }
        for field, changed_value in replay_field_mutations.items():
            changed_replay = copy.deepcopy(replay)
            changed_replay["obligations"][0][field] = changed_value
            changed_audit = Audit(root / f"replay_{field}.json")
            _verify_replay_reconstruction(
                recipes, changed_replay, recipes_file["sha256"], changed_audit
            )
            changed_result = changed_audit.report(None)
            checks.append(
                {
                    "name": f"replay_reconstruct_{field}_negative",
                    "verdict": changed_result["verdict"],
                    "failures": changed_result["failures"],
                    "expected": "FAIL",
                }
            )
        for field, changed_value in (
            ("schema_version", "9.9.9"),
            ("artifact_id", "recipe-replay-obligations:" + "e" * 64),
            ("mutation_recipes_sha256", "d" * 64),
            ("candidate_accounting_complete", False),
        ):
            changed_replay = copy.deepcopy(replay)
            changed_replay[field] = changed_value
            changed_audit = Audit(root / f"replay_top_{field}.json")
            _verify_replay_reconstruction(
                recipes, changed_replay, recipes_file["sha256"], changed_audit
            )
            changed_result = changed_audit.report(None)
            checks.append(
                {
                    "name": f"replay_reconstruct_top_{field}_negative",
                    "verdict": changed_result["verdict"],
                    "failures": changed_result["failures"],
                    "expected": "FAIL",
                }
            )
        ready_recipes = copy.deepcopy(recipes)
        ready_recipe = ready_recipes["recipes"][0]
        ready_recipe["recipe_id"] = "recipe.ready"
        ready_recipe["status"] = "SUPPORTED"
        ready_recipe["timing"]["status"] = "EXACT"
        ready_recipe["prerequisite_choices"] = [
            {
                "alternatives": [
                    {
                        "status": "COMPLETE",
                        "uncertainty_reasons": [],
                        "steps": [
                            {
                                "step_id": "step.prepare",
                                "action_id": "action.prepare",
                                "operation": "prepare",
                                "predecessor_step_ids": [],
                            },
                            {
                                "step_id": "step.target",
                                "action_id": "action.fixture",
                                "operation": "mutate",
                                "predecessor_step_ids": ["step.prepare"],
                            },
                        ],
                    }
                ]
            }
        ]
        ready_digest = "c" * 64
        reconstructed_ready = _expected_replay_document(
            ready_recipes, ready_digest
        )
        ready_reconstruction_audit = Audit(root / "replay_ready_positive.json")
        _verify_replay_reconstruction(
            ready_recipes,
            reconstructed_ready,
            ready_digest,
            ready_reconstruction_audit,
        )
        ready_reconstruction_result = ready_reconstruction_audit.report(None)
        checks.append(
            {
                "name": "replay_ready_topological_reconstruction_positive",
                "verdict": ready_reconstruction_result["verdict"],
                "failures": ready_reconstruction_result["failures"],
                "expected": "PASS",
            }
        )
        reversed_ready = copy.deepcopy(reconstructed_ready)
        reversed_ready["obligations"][0]["ordered_step_ids"].reverse()
        reversed_ready_audit = Audit(root / "replay_ready_reversed.json")
        _verify_replay_reconstruction(
            ready_recipes, reversed_ready, ready_digest, reversed_ready_audit
        )
        reversed_ready_result = reversed_ready_audit.report(None)
        checks.append(
            {
                "name": "replay_ready_topological_order_negative",
                "verdict": reversed_ready_result["verdict"],
                "failures": reversed_ready_result["failures"],
                "expected": "FAIL",
            }
        )
        ambiguous_recipes = copy.deepcopy(ready_recipes)
        alternatives = ambiguous_recipes["recipes"][0][
            "prerequisite_choices"
        ][0]["alternatives"]
        alternatives.append(copy.deepcopy(alternatives[0]))
        ambiguous_replay = _expected_replay_document(
            ambiguous_recipes, ready_digest
        )
        ambiguous_obligation = ambiguous_replay["obligations"][0]
        ambiguous_ok = (
            ambiguous_obligation["status"] == "PARTIAL"
            and "prerequisite DAG is ambiguous, incomplete, or not totally replayable"
            in ambiguous_obligation["uncertainty_reasons"]
        )
        checks.append(
            {
                "name": "replay_ambiguous_prerequisite_forces_partial",
                "verdict": "PASS" if ambiguous_ok else "FAIL",
                "failures": int(not ambiguous_ok),
                "expected": "PASS",
            }
        )

        # Exercise the nullable executor branch with a separately closed set of
        # downstream artifacts.  Absence means UNKNOWN controllability; it is
        # not permission to reuse the previous executor digest.
        noexec_candidates = copy.deepcopy(candidates)
        noexec_candidates["input_digests"]["executor_manifest_sha256"] = None
        noexec_candidates_file = save("noexec_frontier_candidates.json", noexec_candidates)
        noexec_frontier = copy.deepcopy(frontier)
        noexec_frontier["frontier_candidates_sha256"] = noexec_candidates_file["sha256"]
        noexec_frontier_file = save("noexec_fuzzable_frontier.json", noexec_frontier)
        noexec_recipes = copy.deepcopy(recipes)
        noexec_recipes["frontier_candidates_sha256"] = noexec_candidates_file["sha256"]
        noexec_recipes["artifact_id"] = stable_semantic_id(
            "mutation-recipes",
            "\0".join(
                (
                    noexec_recipes["property_ir_sha256"],
                    noexec_recipes["ap_bindings_sha256"],
                    noexec_recipes["graph_sha256"],
                    noexec_recipes["cones_sha256"],
                    noexec_recipes["frontier_candidates_sha256"],
                    noexec_recipes["model_fact_overlay_sha256"],
                    noexec_recipes[
                        "predicate_occurrence_bindings_sha256"
                    ],
                    noexec_recipes["analyzer_core_sha256"],
                    noexec_recipes["solver_contract"]["solver_version"],
                    str(noexec_recipes["solver_contract"]["timeout_ms"]),
                    str(noexec_recipes["solver_contract"]["max_queries"]),
                )
            ),
        )
        noexec_recipes_file = save("noexec_mutation_recipes.json", noexec_recipes)
        noexec_replay = _expected_replay_document(
            noexec_recipes, noexec_recipes_file["sha256"]
        )
        noexec_replay_file = save("noexec_recipe_replay_obligations.json", noexec_replay)
        noexec = copy.deepcopy(m5)
        noexec["executor_manifest"] = None
        for index, replacement in enumerate(
            (
                overlay_file,
                occurrences_file,
                noexec_candidates_file,
                noexec_frontier_file,
                noexec_recipes_file,
                noexec_replay_file,
            )
        ):
            noexec["outputs"][index]["sha256"] = replacement["sha256"]
            noexec["outputs"][index]["path"] = replacement["path"]
        noexec["outputs"][5]["artifact_id"] = noexec_replay["artifact_id"]
        noexec["outputs"][4]["artifact_id"] = noexec_recipes["artifact_id"]
        noexec_expected = _expected_m5_stages(noexec)
        noexec["stages"] = [
            {
                "stage_id": f"stage.{name}",
                "name": name,
                "status": "COMPLETE",
                "input_sha256": noexec_expected[name][0],
                "output_sha256": noexec_expected[name][1],
                "diagnostics": [],
            }
            for name in STAGE_ORDER
        ]
        noexec["certificate_id"] = m5_certificate_id(noexec)
        noexec_path = root / "noexec_m5_analysis_certificate.json"
        _write_json(noexec_path, noexec)
        noexec_result = verify_certificate(
            noexec_path, schema_dir, validate_semantic_schemas=False
        )
        checks.append(
            {
                "name": "positive_without_executor",
                "verdict": noexec_result["verdict"],
                "failures": noexec_result["failures"],
                "failure_details": [
                    item["detail"]
                    for item in noexec_result["findings"]
                    if item["status"] == "FAIL"
                ],
                "verifier_checks": noexec_result["checks"],
                "physical_files_rehashed": noexec_result["physical_files_rehashed"],
            }
        )

        # The direction query is a counterexample query, not a second
        # truth-change query.  Exercise every outcome explicitly so UNSAT is
        # the only outcome that may justify a monotonicity claim, while a SAT
        # truth-change pair can still support the recipe itself.
        def query_evidence(outcome: str) -> dict[str, Any]:
            return {
                "solver": "Z3",
                "solver_version": "4.8.12",
                "encoding_version": SOLVER_ENCODING_VERSION,
                "timeout_ms": 100,
                "outcome": outcome,
            }

        def direction_case(
            name: str,
            truth_outcome: str,
            direction_outcome: str | None,
            mutation_direction: str,
            recipe_status: str,
            expected: str,
            *,
            max_queries: int = 8,
        ) -> None:
            recipe = {
                "recipe_id": f"recipe.{name}",
                "status": recipe_status,
                "solver_query": query_evidence(truth_outcome),
                "direction_query": (
                    None
                    if direction_outcome is None
                    else query_evidence(direction_outcome)
                ),
                "action_mutations": [{"direction": mutation_direction}],
            }
            document = {"recipes": [recipe]}
            query_counts = _solver_counters_for_recipes(document)
            case_solver = {
                "name": "Z3",
                "actual_version": "4.8.12",
                "timeout_ms": 100,
                "max_queries": max_queries,
                "queries": query_counts[0],
                "timeouts": query_counts[1],
                "unsupported": query_counts[2],
            }
            case_audit = Audit(root / f"{name}.json")
            _verify_recipe_solver_contract(document, case_solver, case_audit)
            result = case_audit.report(None)
            checks.append(
                {
                    "name": name,
                    "verdict": result["verdict"],
                    "failures": result["failures"],
                    "expected": expected,
                }
            )

        direction_case(
            "direction_unsat_proves_monotone",
            "SAT", "UNSAT", "MONOTONE_UP", "SUPPORTED", "PASS",
        )
        direction_case(
            "direction_sat_keeps_recipe",
            "SAT", "SAT", "BOUNDARY_SET", "HEURISTIC", "PASS",
        )
        for outcome in ("UNKNOWN", "TIMEOUT", "UNSUPPORTED", "NOT_RUN"):
            direction_case(
                f"direction_{outcome.lower()}_forces_unknown",
                "SAT", outcome, "UNKNOWN", "UNKNOWN", "PASS",
            )
            direction_case(
                f"direction_{outcome.lower()}_rejects_nonunknown",
                "SAT", outcome, "BOUNDARY_SET", "HEURISTIC", "FAIL",
            )
            direction_case(
                f"direction_{outcome.lower()}_rejects_monotone",
                "SAT", outcome, "MONOTONE_DOWN", "SUPPORTED", "FAIL",
            )
        direction_case(
            "truth_sat_without_direction",
            "SAT", None, "BOUNDARY_SET", "SUPPORTED", "PASS",
        )
        direction_case(
            "truth_non_sat_remains_unknown",
            "UNSAT", None, "UNKNOWN_DIRECTION", "UNKNOWN", "PASS",
        )
        direction_case(
            "truth_non_sat_rejects_supported",
            "UNSAT", None, "BOUNDARY_SET", "SUPPORTED", "FAIL",
        )
        direction_case(
            "direction_requires_truth_sat",
            "UNSAT", "UNSAT", "MONOTONE_UP", "UNKNOWN", "FAIL",
        )
        direction_case(
            "monotone_requires_direction_query",
            "SAT", None, "MONOTONE_UP", "SUPPORTED", "FAIL",
        )
        direction_case(
            "solver_budget_is_finite",
            "SAT", None, "BOUNDARY_SET", "SUPPORTED", "FAIL",
            max_queries=0,
        )

        # A raw pack with a certificate-authored semantic SHA must be rejected
        # even when its physical SHA and metadata are unchanged.
        semantic_schemas = SchemaSet(schema_dir.resolve())
        semantic_schemas.load()
        occurrence_schema_audit = Audit(root / "occurrence_schema.json")
        semantic_schemas.validate(
            "predicate_occurrence_bindings.schema.json",
            occurrences,
            occurrence_schema_audit,
            "predicate occurrence fixture",
        )
        occurrence_schema_result = occurrence_schema_audit.report(None)
        checks.append(
            {
                "name": "occurrence_closed_schema_positive",
                "verdict": occurrence_schema_result["verdict"],
                "failures": occurrence_schema_result["failures"],
                "expected": "PASS",
            }
        )
        invalid_occurrence_schema = copy.deepcopy(occurrences)
        invalid_occurrence_schema["unexpected"] = True
        invalid_occurrence_schema_audit = Audit(
            root / "occurrence_closed_schema.json"
        )
        semantic_schemas.validate(
            "predicate_occurrence_bindings.schema.json",
            invalid_occurrence_schema,
            invalid_occurrence_schema_audit,
            "tampered predicate occurrence fixture",
        )
        invalid_occurrence_schema_result = (
            invalid_occurrence_schema_audit.report(None)
        )
        checks.append(
            {
                "name": "occurrence_closed_schema_negative",
                "verdict": invalid_occurrence_schema_result["verdict"],
                "failures": invalid_occurrence_schema_result["failures"],
                "expected": "FAIL",
            }
        )
        integer_type = {
            "kind": "integer",
            "canonical": "int",
            "bit_width": 32,
            "signed": True,
        }
        typed_property = {
            "selectors": [
                {
                    "selector_id": "selector.typed",
                    "kind": "source_location",
                    "location": {
                        "file": "source.c",
                        "line": 1,
                        "column": 1,
                        "location_kind": "spelling",
                    },
                    "value_type": integer_type,
                }
            ],
            "atomic_propositions": [
                {
                    "ap_id": "ap.typed",
                    "predicate": {
                        "node_kind": "reference",
                        "referenced_selector_id": "selector.typed",
                        "value_type": integer_type,
                        "operands": [],
                    },
                }
            ],
        }
        typed_occurrences = {
            "selector_accounts": [
                {
                    "ap_id": "ap.typed",
                    "selector_id": "selector.typed",
                    "expected_value_type": integer_type,
                    "occurrence_ids": ["occurrence.typed"],
                    "resolution": "EXACT",
                }
            ],
            "occurrences": [
                {
                    "occurrence_id": "occurrence.typed",
                    "ap_id": "ap.typed",
                    "selector_id": "selector.typed",
                    "value_type": integer_type,
                    "resolution": "EXACT",
                }
            ],
        }
        typed_closure_audit = Audit(root / "occurrence_type_closure.json")
        _verify_occurrence_type_closure(
            typed_property, typed_occurrences, typed_closure_audit
        )
        typed_closure_result = typed_closure_audit.report(None)
        checks.append(
            {
                "name": "occurrence_type_closure_positive",
                "verdict": typed_closure_result["verdict"],
                "failures": typed_closure_result["failures"],
                "expected": "PASS",
            }
        )
        mismatched_occurrences = copy.deepcopy(typed_occurrences)
        mismatched_occurrences["occurrences"][0]["value_type"] = {
            "kind": "floating",
            "canonical": "float",
            "bit_width": 32,
        }
        mismatched_closure_audit = Audit(
            root / "occurrence_type_mismatch.json"
        )
        _verify_occurrence_type_closure(
            typed_property, mismatched_occurrences, mismatched_closure_audit
        )
        mismatched_closure_result = mismatched_closure_audit.report(None)
        checks.append(
            {
                "name": "occurrence_type_closure_negative",
                "verdict": mismatched_closure_result["verdict"],
                "failures": mismatched_closure_result["failures"],
                "expected": "FAIL",
            }
        )
        mismatched_unit_occurrences = copy.deepcopy(typed_occurrences)
        mismatched_unit_occurrences["occurrences"][0]["value_type"] = {
            **integer_type,
            "unit": "ms",
        }
        mismatched_unit_audit = Audit(root / "occurrence_unit_mismatch.json")
        _verify_occurrence_type_closure(
            typed_property, mismatched_unit_occurrences, mismatched_unit_audit
        )
        mismatched_unit_result = mismatched_unit_audit.report(None)
        checks.append(
            {
                "name": "occurrence_unit_closure_negative",
                "verdict": mismatched_unit_result["verdict"],
                "failures": mismatched_unit_result["failures"],
                "expected": "FAIL",
            }
        )
        ledger_mismatch = copy.deepcopy(typed_occurrences)
        ledger_mismatch["occurrences"][0]["resolution"] = "UNKNOWN"
        ledger_closure_audit = Audit(root / "occurrence_ledger_mismatch.json")
        _verify_occurrence_type_closure(
            typed_property, ledger_mismatch, ledger_closure_audit
        )
        ledger_closure_result = ledger_closure_audit.report(None)
        checks.append(
            {
                "name": "occurrence_exact_account_ledger_negative",
                "verdict": ledger_closure_result["verdict"],
                "failures": ledger_closure_result["failures"],
                "expected": "FAIL",
            }
        )

        semantic_closure_audit = Audit(root / "occurrence_semantic_closure.json")
        _verify_occurrence_semantic_closure(
            property_value, index_value, occurrences, semantic_closure_audit
        )
        semantic_closure_result = semantic_closure_audit.report(None)
        checks.append(
            {
                "name": "occurrence_semantic_closure_positive",
                "verdict": semantic_closure_result["verdict"],
                "failures": semantic_closure_result["failures"],
                "expected": "PASS",
            }
        )
        ambiguous_type_index = copy.deepcopy(index_value)
        ambiguous_type_node_id = "node:" + "d" * 64
        ambiguous_type_index["semantic_nodes"].append(
            {
                "node_id": ambiguous_type_node_id,
                "node_kind": "memory",
                "entity_ref": fixture_entity_id,
                "owner_function_id": None,
                "access_path": {
                    "root_entity_id": fixture_entity_id,
                    "dereference_depth": 0,
                    "fields": [],
                    "unknown_suffix": False,
                },
                "abstract_object_id": None,
                "value_type": {
                    "kind": "pointer",
                    "canonical": "int *",
                    "bit_width": 64,
                },
                "location": {
                    "file": "riftpath://v1/neutral/source.c",
                    "line": 2,
                    "column": 1,
                    "location_kind": "spelling",
                },
                "ast_kind": "ArraySubscriptExpr",
            }
        )
        ambiguous_type_occurrences = copy.deepcopy(occurrences)
        ambiguous_type_occurrences["selector_accounts"][0]["resolution"] = (
            "UNKNOWN"
        )
        ambiguous_type_occurrences["selector_accounts"][0][
            "uncertainty_reasons"
        ] = ["m4_semantic_node_ambiguous"]
        ambiguous_type_occurrences["occurrences"][0]["semantic_node_ids"] = (
            sorted([fixture_node_id, ambiguous_type_node_id])
        )
        ambiguous_type_occurrences["occurrences"][0]["certainty"] = "unknown"
        ambiguous_type_occurrences["occurrences"][0]["resolution"] = "UNKNOWN"
        ambiguous_type_occurrences["occurrences"][0][
            "uncertainty_reasons"
        ] = ["m4_semantic_node_ambiguous", "selector_account_not_exact"]
        ambiguous_type_audit = Audit(root / "occurrence_ambiguous_type_set.json")
        _verify_occurrence_semantic_closure(
            property_value,
            ambiguous_type_index,
            ambiguous_type_occurrences,
            ambiguous_type_audit,
        )
        ambiguous_type_result = ambiguous_type_audit.report(None)
        checks.append(
            {
                "name": "occurrence_unknown_candidate_type_set_positive",
                "verdict": ambiguous_type_result["verdict"],
                "failures": ambiguous_type_result["failures"],
                "expected": "PASS",
            }
        )
        no_matching_type_index = copy.deepcopy(ambiguous_type_index)
        no_matching_type_index["semantic_nodes"][0]["value_type"] = {
            "kind": "pointer",
            "canonical": "long *",
            "bit_width": 64,
        }
        no_matching_type_audit = Audit(
            root / "occurrence_no_matching_candidate_type.json"
        )
        _verify_occurrence_semantic_closure(
            property_value,
            no_matching_type_index,
            ambiguous_type_occurrences,
            no_matching_type_audit,
        )
        no_matching_type_result = no_matching_type_audit.report(None)
        checks.append(
            {
                "name": "occurrence_unknown_candidate_type_set_negative",
                "verdict": no_matching_type_result["verdict"],
                "failures": no_matching_type_result["failures"],
                "expected": "FAIL",
            }
        )
        semantic_occurrence_mutations: list[tuple[str, dict[str, Any]]] = []
        bad_roles = copy.deepcopy(occurrences)
        bad_roles["selector_accounts"][0]["roles"] = ["bound"]
        bad_roles["occurrences"][0]["roles"] = ["bound"]
        semantic_occurrence_mutations.append(("property_roles", bad_roles))
        bad_predicate_path = copy.deepcopy(occurrences)
        bad_predicate_path["selector_accounts"][0]["predicate_paths"] = [
            "predicate.operands[0]"
        ]
        bad_predicate_path["occurrences"][0]["predicate_paths"] = [
            "predicate.operands[0]"
        ]
        semantic_occurrence_mutations.append(
            ("property_predicate_path", bad_predicate_path)
        )
        bad_location = copy.deepcopy(occurrences)
        bad_location["occurrences"][0]["spelling_location"]["column"] = 6
        bad_location["occurrences"][0]["occurrence_id"] = (
            _predicate_occurrence_id(bad_location["occurrences"][0])
        )
        bad_location["selector_accounts"][0]["occurrence_ids"] = [
            bad_location["occurrences"][0]["occurrence_id"]
        ]
        semantic_occurrence_mutations.append(("selector_location", bad_location))
        bad_usr = copy.deepcopy(occurrences)
        bad_usr["occurrences"][0]["referenced_usr"] = "c:@absent"
        bad_usr["occurrences"][0]["occurrence_id"] = _predicate_occurrence_id(
            bad_usr["occurrences"][0]
        )
        bad_usr["selector_accounts"][0]["occurrence_ids"] = [
            bad_usr["occurrences"][0]["occurrence_id"]
        ]
        semantic_occurrence_mutations.append(("referenced_usr", bad_usr))
        bad_declref_path = copy.deepcopy(occurrences)
        bad_declref_path["occurrences"][0]["access_path"] = {
            "root_entity_id": fixture_entity_id,
            "dereference_depth": 0,
            "fields": [],
            "unknown_suffix": False,
        }
        bad_declref_path["occurrences"][0]["occurrence_id"] = (
            _predicate_occurrence_id(bad_declref_path["occurrences"][0])
        )
        bad_declref_path["selector_accounts"][0]["occurrence_ids"] = [
            bad_declref_path["occurrences"][0]["occurrence_id"]
        ]
        semantic_occurrence_mutations.append(
            ("declref_member_access_path", bad_declref_path)
        )
        for mutation_name, mutation in semantic_occurrence_mutations:
            mutation_audit = Audit(root / f"{mutation_name}.json")
            _verify_occurrence_semantic_closure(
                property_value, index_value, mutation, mutation_audit
            )
            mutation_result = mutation_audit.report(None)
            checks.append(
                {
                    "name": f"occurrence_semantic_{mutation_name}_negative",
                    "verdict": mutation_result["verdict"],
                    "failures": mutation_result["failures"],
                    "expected": "FAIL",
                }
            )
        ambiguous_usr_index = copy.deepcopy(index_value)
        ambiguous_usr_index["entities"].append(
            {
                "entity": {
                    "entity_id": "entity:" + "c" * 64,
                    "usr": fixture_usr,
                },
                "translation_unit_refs": [fixture_tu_id],
            }
        )
        ambiguous_usr_audit = Audit(root / "occurrence_ambiguous_usr.json")
        _verify_occurrence_semantic_closure(
            property_value,
            ambiguous_usr_index,
            occurrences,
            ambiguous_usr_audit,
        )
        ambiguous_usr_result = ambiguous_usr_audit.report(None)
        checks.append(
            {
                "name": "occurrence_ambiguous_usr_negative",
                "verdict": ambiguous_usr_result["verdict"],
                "failures": ambiguous_usr_result["failures"],
                "expected": "FAIL",
            }
        )

        member_root_id = "entity:" + "8" * 64
        member_field_id = "entity:" + "9" * 64
        member_node_id = "node:" + "a" * 64
        member_object_id = "object:" + "b" * 64
        member_selector_id = "selector.member"
        member_ap_id = "ap.member"
        member_usr = "c:@S@FI@member"
        member_property = copy.deepcopy(property_value)
        member_property["selectors"][0]["selector_id"] = member_selector_id
        member_property["atomic_propositions"][0]["ap_id"] = member_ap_id
        member_property["atomic_propositions"][0]["predicate"][
            "referenced_selector_id"
        ] = member_selector_id
        member_property["atomic_propositions"][0]["predicate"]["operator"] = (
            "member_expr"
        )
        member_property["atomic_propositions"][0]["role_selector_groups"][0][
            "all_of"
        ] = [member_selector_id]
        member_index = copy.deepcopy(index_value)
        member_index["entities"] = [
            {
                "entity": {"entity_id": member_root_id, "usr": "c:@root"},
                "translation_unit_refs": [fixture_tu_id],
            },
            {
                "entity": {"entity_id": member_field_id, "usr": member_usr},
                "translation_unit_refs": [fixture_tu_id],
            },
        ]
        member_path = {
            "root_entity_id": member_root_id,
            "dereference_depth": 0,
            "fields": [member_field_id],
            "unknown_suffix": False,
        }
        member_index["semantic_nodes"] = [
            {
                "node_id": member_node_id,
                "entity_ref": member_root_id,
                "access_path": member_path,
                "abstract_object_id": member_object_id,
                "value_type": integer_type,
                "location": {
                    "file": "riftpath://v1/neutral/source.c",
                    "line": 1,
                    "column": 1,
                    "end_line": 1,
                    "end_column": 30,
                    "location_kind": "spelling",
                },
            }
        ]
        member_index["abstract_objects"] = [{"object_id": member_object_id}]
        member_occurrences = copy.deepcopy(occurrences)
        member_occurrences["selector_accounts"][0].update(
            ap_id=member_ap_id,
            selector_id=member_selector_id,
        )
        member_occurrence = member_occurrences["occurrences"][0]
        member_occurrence.update(
            ap_id=member_ap_id,
            selector_id=member_selector_id,
            kind="member_expr",
            referenced_usr=member_usr,
            referenced_entity_id=member_field_id,
            semantic_node_ids=[member_node_id],
            access_path=member_path,
            member_base_entity_id=member_root_id,
            member_abstract_object_id=member_object_id,
        )
        member_occurrence["occurrence_id"] = _predicate_occurrence_id(
            member_occurrence
        )
        member_occurrences["selector_accounts"][0]["occurrence_ids"] = [
            member_occurrence["occurrence_id"]
        ]
        member_audit = Audit(root / "member_occurrence_semantic_closure.json")
        _verify_occurrence_semantic_closure(
            member_property, member_index, member_occurrences, member_audit
        )
        member_result = member_audit.report(None)
        checks.append(
            {
                "name": "occurrence_member_access_path_positive",
                "verdict": member_result["verdict"],
                "failures": member_result["failures"],
                "expected": "PASS",
            }
        )
        bad_member_path = copy.deepcopy(member_occurrences)
        bad_member_path["occurrences"][0]["access_path"]["fields"] = [
            fixture_entity_id
        ]
        bad_member_path["occurrences"][0]["occurrence_id"] = (
            _predicate_occurrence_id(bad_member_path["occurrences"][0])
        )
        bad_member_path["selector_accounts"][0]["occurrence_ids"] = [
            bad_member_path["occurrences"][0]["occurrence_id"]
        ]
        bad_member_audit = Audit(root / "member_occurrence_bad_path.json")
        _verify_occurrence_semantic_closure(
            member_property, member_index, bad_member_path, bad_member_audit
        )
        bad_member_result = bad_member_audit.report(None)
        checks.append(
            {
                "name": "occurrence_member_access_path_negative",
                "verdict": bad_member_result["verdict"],
                "failures": bad_member_result["failures"],
                "expected": "FAIL",
            }
        )
        bad_semantic_record = copy.deepcopy(m5["model_packs"][0])
        bad_semantic_record["semantic_sha256"] = "f" * 64
        semantic_audit = Audit(root / "model_pack_semantic_digest.json")
        _verify_model_packs(
            {"model_packs": [bad_semantic_record]},
            semantic_schemas,
            PhysicalHasher(semantic_audit),
            semantic_audit,
            False,
        )
        semantic_result = semantic_audit.report(None)
        checks.append(
            {
                "name": "model_pack_semantic_digest",
                "verdict": semantic_result["verdict"],
                "failures": semantic_result["failures"],
                "expected": "FAIL",
            }
        )
        reference_pack_path = (
            pathlib.Path(__file__).resolve().parents[3]
            / "benchmark/rift/m5/model_packs/neutral_read_arg_v1.json"
        )
        reference_pack = load_json_strict(reference_pack_path)
        reference_semantic_sha = model_pack_semantic_sha256(reference_pack)
        checks.append(
            {
                "name": "model_pack_cpp_digest_regression",
                "verdict": (
                    "PASS"
                    if reference_semantic_sha == MODEL_PACK_CPP_REGRESSION_SHA256
                    else "FAIL"
                ),
                "failures": int(
                    reference_semantic_sha != MODEL_PACK_CPP_REGRESSION_SHA256
                ),
                "expected": "PASS",
                "observed_sha256": reference_semantic_sha,
            }
        )

        # The original verifier only hashed the legacy emit fields.  Exercise
        # all three typed model-pack payloads directly so a future omission
        # cannot preserve the semantic digest by accident.
        typed_pack_digest_cases: list[tuple[str, dict[str, Any], Any]] = []
        value_pack_changed = copy.deepcopy(reference_pack)
        value_pack_changed["rules"][0]["emits"][0]["value_transfer"][
            "failure_branch_unknown"
        ] = False
        typed_pack_digest_cases.append(
            ("value_transfer", reference_pack, value_pack_changed)
        )
        clock_pack = copy.deepcopy(pack)
        clock_emit = clock_pack["rules"][0]["emits"][0]
        clock_emit["fact_kind"] = "clock_relation"
        clock_emit["target_capture_ref"] = "capture.fixture"
        clock_emit.pop("external_action", None)
        clock_emit["clock_relation"] = {
            "clock_source": "clock.fixture",
            "unit": "ms",
            "epoch": "epoch.fixture",
            "quantum": 1.0,
            "jitter": 0.0,
            "wrap": "none",
            "start_event": "event.start",
            "end_event": "event.end",
            "endpoint": "closed",
            "scope_schema": "scope.fixture",
            "generation_schema": "generation.fixture",
        }
        clock_pack_changed = copy.deepcopy(clock_pack)
        clock_pack_changed["rules"][0]["emits"][0]["clock_relation"][
            "jitter"
        ] = 0.25
        typed_pack_digest_cases.append(
            ("clock_relation", clock_pack, clock_pack_changed)
        )
        joint_pack = copy.deepcopy(pack)
        joint_pack["rules"][0]["captures"].append(
            {
                "capture_id": "capture.second",
                "match_ref": "match.fixture",
                "projection": "receiver",
            }
        )
        joint_emit = joint_pack["rules"][0]["emits"][0]
        joint_emit["fact_kind"] = "joint_action_relation"
        joint_emit.pop("external_action", None)
        joint_emit["joint_action_relation"] = {
            "group_schema_id": "joint.fixture",
            "combination": "all_required",
            "participant_set_complete": True,
            "participant_capture_refs": [
                "capture.fixture",
                "capture.second",
            ],
            "scope_schema": "scope.fixture",
            "generation_schema": "generation.fixture",
        }
        joint_pack_changed = copy.deepcopy(joint_pack)
        joint_pack_changed["rules"][0]["emits"][0][
            "joint_action_relation"
        ]["combination"] = "any_sufficient"
        typed_pack_digest_cases.append(
            ("joint_action_relation", joint_pack, joint_pack_changed)
        )
        for name, before, after in typed_pack_digest_cases:
            changed = model_pack_semantic_sha256(before) != model_pack_semantic_sha256(after)
            checks.append(
                {
                    "name": f"model_pack_{name}_semantic_tamper",
                    "verdict": "PASS" if changed else "FAIL",
                    "failures": int(not changed),
                    "expected": "PASS",
                }
            )

        # A fully content-addressed typed overlay plus a closed source-AND
        # recipe fixture drives the new detached semantic replay.  All
        # negative cases are coherent JSON objects; they fail because typed
        # meaning no longer agrees with its content IDs/evidence.
        typed_node_b = "node:" + "4" * 64
        typed_node_setup = "node:" + "7" * 64
        typed_index = copy.deepcopy(index_value)
        for node_id in (typed_node_b, typed_node_setup):
            node = copy.deepcopy(index_value["semantic_nodes"][0])
            node["node_id"] = node_id
            typed_index["semantic_nodes"].append(node)
        typed_provenance = {
            "model_pack_id": pack["model_pack_id"],
            "model_pack_version": pack["model_pack_version"],
            "model_pack_sha256": semantic_pack_sha,
            "layer": pack["layer"],
            "rule_id": "rule.fixture",
            "emit_id": "emit.fixture",
            "selector_ids": ["selector.fixture"],
            "capture_ids": ["capture.fixture"],
            "matched_semantic_node_ids": [fixture_node_id],
        }

        def typed_action(action_id: str, operation: str) -> dict[str, Any]:
            return {
                **fixture_action,
                "external_action_id": action_id,
                "action_schema_id": action_id + ".schema",
                "operation": operation,
                "provenance": [typed_provenance],
            }

        typed_actions = [
            typed_action("action.a", "set-a"),
            typed_action("action.b", "set-b"),
            typed_action("action.setup", "prepare"),
        ]

        def typed_attachment(
            action_id: str, semantic_node_id: str
        ) -> dict[str, Any]:
            attachment = {
                "attachment_id": "pending",
                "external_action_id": action_id,
                "semantic_node_id": semantic_node_id,
                "transfer_relation": "typed_identity",
                "certainty": "modelled",
                "value_transfer": copy.deepcopy(fixture_transfer),
                "provenance": [typed_provenance],
            }
            attachment["attachment_id"] = stable_semantic_id(
                "boundary-attachment",
                "\0".join(
                    (
                        action_id,
                        semantic_node_id,
                        attachment["transfer_relation"],
                        _typed_value_transfer_material(
                            attachment["value_transfer"]
                        ),
                    )
                ),
            )
            return attachment

        typed_attachments = [
            typed_attachment("action.a", fixture_node_id),
            typed_attachment("action.b", typed_node_b),
            typed_attachment("action.setup", typed_node_setup),
        ]
        clock_relation = {
            "clock_source": "clock.fixture",
            "unit": "ms",
            "epoch": "epoch.fixture",
            "quantum": 1.0,
            "jitter": 0.0,
            "wrap": "none",
            "wrap_value": None,
            "start_event": "event.start",
            "end_event": "event.end",
            "endpoint": "closed",
            "scope_schema": "process_epoch",
            "generation_schema": "process_epoch",
        }
        clock_fact = {
            "fact_id": "pending",
            "kind": "clock_relation",
            "source_semantic_node_id": fixture_node_id,
            "target_semantic_node_id": typed_node_b,
            "transfer_relation": "relative_clock",
            "certainty": "modelled",
            "provenance": [typed_provenance],
            "clock_relation": clock_relation,
            "value_transfer": None,
        }
        clock_fact["fact_id"] = stable_semantic_id(
            "model-fact", _model_fact_material(clock_fact)
        )
        lifecycle_fact = {
            "fact_id": "pending",
            "kind": "lifecycle_transition",
            "source_semantic_node_id": typed_node_setup,
            "target_semantic_node_id": fixture_node_id,
            "transfer_relation": "setup_before_value",
            "certainty": "modelled",
            "provenance": [typed_provenance],
            "clock_relation": None,
            "value_transfer": None,
        }
        lifecycle_fact["fact_id"] = stable_semantic_id(
            "model-fact", _model_fact_material(lifecycle_fact)
        )
        participants = sorted([fixture_node_id, typed_node_b])
        group_schema_id = "joint.schema.fixture"
        group_instance_id = stable_semantic_id(
            "joint-action-group",
            "\0".join(
                (
                    semantic_pack_sha,
                    typed_provenance["rule_id"],
                    group_schema_id,
                    *participants,
                )
            ),
        )
        joint_constraint = {
            "constraint_id": "pending",
            "group_instance_id": group_instance_id,
            "group_schema_id": group_schema_id,
            "combination": "all_required",
            "participant_set_complete": True,
            "participant_semantic_node_ids": participants,
            "scope_schema": "process_epoch",
            "generation_schema": "process_epoch",
            "certainty": "modelled",
            "provenance": [typed_provenance],
        }
        joint_constraint["constraint_id"] = stable_semantic_id(
            "joint-action-constraint",
            "\0".join(
                (
                    group_instance_id,
                    str(MODEL_JOINT_OPERATOR["all_required"]),
                    "1",
                    "process_epoch",
                    "process_epoch",
                )
            ),
        )
        typed_overlay = {
            "schema_version": "1.0.0",
            "artifact_id": "pending",
            "semantic_index_artifact_id": index_value["artifact_id"],
            "semantic_index_identity": files["semantic_index"]["sha256"],
            "status": "COMPLETE",
            "model_pack_sha256s": [semantic_pack_sha],
            "external_actions": sorted(
                typed_actions, key=lambda item: item["external_action_id"]
            ),
            "boundary_attachments": sorted(
                typed_attachments, key=lambda item: item["attachment_id"]
            ),
            "semantic_facts": sorted(
                [clock_fact, lifecycle_fact],
                key=lambda item: item["fact_id"],
            ),
            "joint_action_constraints": [joint_constraint],
            "unknown_outcomes": [],
            "resource_ledger": [],
            "coverage_gaps": [],
            "diagnostics": [],
        }
        typed_overlay["artifact_id"] = stable_semantic_id(
            "model-overlay", _overlay_identity_material(typed_overlay)
        )

        def typed_overlay_case(
            name: str, value: Mapping[str, Any], expected: str
        ) -> None:
            case_audit = Audit(root / f"{name}.json")
            _verify_model_overlay_semantics(value, typed_index, case_audit)
            result = case_audit.report(None)
            checks.append(
                {
                    "name": name,
                    "verdict": result["verdict"],
                    "failures": result["failures"],
                    "expected": expected,
                }
            )

        typed_overlay_case(
            "typed_overlay_detached_positive", typed_overlay, "PASS"
        )
        overlay_tampers: list[tuple[str, Any]] = []
        changed_clock = copy.deepcopy(typed_overlay)
        next(
            item
            for item in changed_clock["semantic_facts"]
            if item["kind"] == "clock_relation"
        )["clock_relation"]["jitter"] = 0.5
        overlay_tampers.append(("clock_content", changed_clock))
        changed_transfer = copy.deepcopy(typed_overlay)
        changed_transfer["boundary_attachments"][0]["value_transfer"][
            "kind"
        ] = "unknown"
        overlay_tampers.append(("value_transfer_content", changed_transfer))
        changed_joint = copy.deepcopy(typed_overlay)
        changed_joint["joint_action_constraints"][0][
            "combination"
        ] = "any_sufficient"
        overlay_tampers.append(("joint_constraint_content", changed_joint))
        missing_joint_ledger = copy.deepcopy(typed_overlay)
        missing_joint_ledger.pop("joint_action_constraints")
        overlay_tampers.append(("joint_ledger_missing", missing_joint_ledger))
        changed_overlay_id = copy.deepcopy(typed_overlay)
        changed_overlay_id["artifact_id"] = "model-overlay:" + "f" * 64
        overlay_tampers.append(("artifact_id", changed_overlay_id))
        changed_order = copy.deepcopy(typed_overlay)
        changed_order["boundary_attachments"].reverse()
        overlay_tampers.append(("canonical_order", changed_order))
        for name, value in overlay_tampers:
            typed_overlay_case(
                f"typed_overlay_{name}_tamper", value, "FAIL"
            )

        typed_graph = {
            "nodes": [
                {
                    "node_id": "ctx.a",
                    "semantic_node_ref": fixture_node_id,
                },
                {
                    "node_id": "ctx.b",
                    "semantic_node_ref": typed_node_b,
                },
                {
                    "node_id": "ctx.setup",
                    "semantic_node_ref": typed_node_setup,
                },
            ],
            "edges": [
                {
                    "edge_id": "edge.control.fixture",
                    "source_node_id": "ctx.setup",
                    "target_node_id": "ctx.a",
                    "relation_kind": "controls",
                    "certainty": "may",
                }
            ],
        }
        typed_property = {
            "atomic_propositions": [
                {
                    "ap_id": "ap.joint.fixture",
                    "predicate": {
                        "node_kind": "boolean",
                        "operator": "&&",
                        "operands": [
                            {
                                "node_kind": "reference",
                                "referenced_selector_id": "selector.a",
                                "operands": [],
                            },
                            {
                                "node_kind": "reference",
                                "referenced_selector_id": "selector.b",
                                "operands": [],
                            },
                        ],
                    },
                }
            ]
        }
        action_by_id = {
            item["external_action_id"]: item for item in typed_actions
        }
        attachment_by_action = {
            item["external_action_id"]: item
            for item in typed_attachments
        }

        def closed_candidate(
            candidate_id: str,
            action_id: str,
            selector: str | None,
        ) -> dict[str, Any]:
            witness = {
                "attachment_id": attachment_by_action[action_id][
                    "attachment_id"
                ],
                "boundary_node_id": {
                    "action.a": "ctx.a",
                    "action.b": "ctx.b",
                    "action.setup": "ctx.setup",
                }[action_id],
                "compatibility": "COMPATIBLE",
                "model_fact_ids": [],
                "path_exemplars": [],
            }
            return {
                "candidate_id": candidate_id,
                "cone_id": "cone.joint.fixture",
                "ap_id": "ap.joint.fixture",
                "disposition": "ACTIONABLE",
                "action": action_by_id[action_id],
                "evidence": {
                    "model_provenance": {"model_fact_ids": []},
                    "completeness": {
                        "model_vm_complete": True,
                        "attachment_enumeration_complete": True,
                        "forward_enumeration_complete": True,
                        "cone_complete": True,
                        "compatibility_complete": True,
                        "gap_reasons": [],
                    },
                },
                "witnesses": [witness],
                "selector": selector,
            }

        candidate_a = closed_candidate(
            "candidate.a", "action.a", "selector.a"
        )
        candidate_b = closed_candidate(
            "candidate.b", "action.b", "selector.b"
        )
        guard_candidate = closed_candidate(
            "candidate.setup", "action.setup", None
        )
        candidate_a["witnesses"][0]["model_fact_ids"] = [
            clock_fact["fact_id"],
            lifecycle_fact["fact_id"],
        ]
        candidate_a["witnesses"][0]["path_exemplars"] = [
            {
                "compatibility": "COMPATIBLE",
                "meet_node_id": "ctx.b",
                "root_node_id": "ctx.a",
                "forward_steps": [
                    {
                        "kind": "MODEL_ARC",
                        "source_node_id": "ctx.a",
                        "target_node_id": "ctx.b",
                        "graph_edge_id": None,
                        "model_fact_id": clock_fact["fact_id"],
                    }
                ],
                "root_steps": [],
            }
        ]
        candidate_a["evidence"]["model_provenance"]["model_fact_ids"] = [
            clock_fact["fact_id"],
            lifecycle_fact["fact_id"],
        ]
        guard_candidate["witnesses"][0]["path_exemplars"] = [
            {
                "compatibility": "COMPATIBLE",
                "meet_node_id": "ctx.a",
                "root_node_id": "ctx.a",
                "forward_steps": [
                    {
                        "kind": "GRAPH_EDGE",
                        "source_node_id": "ctx.setup",
                        "target_node_id": "ctx.a",
                        "graph_edge_id": "edge.control.fixture",
                        "model_fact_id": None,
                    }
                ],
                "root_steps": [],
            }
        ]
        typed_candidates = {
            "candidates": [candidate_a, candidate_b, guard_candidate]
        }
        joint_actions = ["action.a", "action.b"]
        source_material = "typed-source-conjunction\0ap.joint.fixture"
        for selector in ("selector.a", "selector.b"):
            source_material += "\0" + selector
        for action_id in joint_actions:
            source_material += "\0" + action_id
        source_requirement_id = stable_semantic_id(
            "joint-source", source_material
        )
        source_hyperedge_id = stable_semantic_id(
            "action-hyperedge",
            source_requirement_id + "\0" + "\0".join(joint_actions),
        )
        shared_query_sha = "9" * 64
        typed_recipe_items: list[dict[str, Any]] = []
        candidates_by_name = {
            "candidate.a": candidate_a,
            "candidate.b": candidate_b,
        }
        selector_by_candidate = {
            "candidate.a": "selector.a",
            "candidate.b": "selector.b",
        }
        for candidate_id in ("candidate.a", "candidate.b"):
            candidate = candidates_by_name[candidate_id]
            recipe_id = stable_semantic_id(
                "recipe",
                "\0".join(
                    (
                        candidate_id,
                        candidate["cone_id"],
                        candidate["ap_id"],
                        shared_query_sha,
                        *joint_actions,
                    )
                ),
            )
            typed_recipe_items.append(
                {
                    "recipe_id": recipe_id,
                    "frontier_candidate_id": candidate_id,
                    "cone_id": candidate["cone_id"],
                    "ap_id": candidate["ap_id"],
                    "target_predicate_selector_id": selector_by_candidate[
                        candidate_id
                    ],
                    "status": "SUPPORTED",
                    "action_hyperedge": {
                        "hyperedge_id": source_hyperedge_id,
                        "action_ids": joint_actions,
                        "indivisible": True,
                        "claim": "JOINT_REQUIRED",
                    },
                    "action_mutations": [
                        {
                            "action_id": action_id,
                            "mutation_kind": "BOUNDARY_SET",
                            "direction": "BOUNDARY_SET",
                        }
                        for action_id in joint_actions
                    ],
                    "prerequisite_choices": [],
                    "timing": {
                        "status": "UNKNOWN",
                        "uncertainty_reasons": ["no temporal interval"],
                    },
                    "solver_query": {
                        "query_sha256": shared_query_sha,
                        "outcome": "SAT",
                    },
                }
            )
        expected_model_choices = _expected_model_prerequisites(
            candidate_a,
            {
                item["fact_id"]: item
                for item in typed_overlay["semantic_facts"]
            },
            typed_overlay["boundary_attachments"],
            action_by_id,
        )
        expected_control_choices = _control_prerequisite_candidates(
            candidate_a,
            typed_candidates["candidates"],
            typed_graph,
            action_by_id,
        )
        typed_recipe_items[0]["prerequisite_choices"] = sorted(
            [*expected_model_choices.values(), *expected_control_choices.values()],
            key=lambda item: item["choice_id"],
        )
        typed_recipe_items[0]["timing"] = {
            "status": "EXACT",
            "clock_source": clock_relation["clock_source"],
            "unit": clock_relation["unit"],
            "epoch": clock_relation["epoch"],
            "quantum": clock_relation["quantum"],
            "jitter": clock_relation["jitter"],
            "wrap": clock_relation["wrap"],
            "comparison_endpoint": "CLOSED",
            "start_event": clock_relation["start_event"],
            "end_event": clock_relation["end_event"],
            "scope_schema": clock_relation["scope_schema"],
            "generation_schema": clock_relation["generation_schema"],
            "uncertainty_reasons": [],
        }
        typed_recipe_inputs = {
            "property_ir_sha256": "1" * 64,
            "ap_bindings_sha256": "2" * 64,
            "graph_sha256": "3" * 64,
            "cones_sha256": "4" * 64,
            "frontier_candidates_sha256": "5" * 64,
            "model_fact_overlay_sha256": "6" * 64,
            "predicate_occurrence_bindings_sha256": "7" * 64,
            "analyzer_core_sha256": "8" * 64,
        }
        typed_recipes = {
            **typed_recipe_inputs,
            "artifact_id": "pending",
            "solver_contract": {
                "solver_version": "4.13.3.0",
                "timeout_ms": 100,
                "max_queries": 1000,
            },
            "recipes": sorted(
                typed_recipe_items, key=lambda item: item["recipe_id"]
            ),
        }
        typed_recipe_material = "\0".join(
            (
                *typed_recipe_inputs.values(),
                typed_recipes["solver_contract"]["solver_version"],
                str(typed_recipes["solver_contract"]["timeout_ms"]),
                str(typed_recipes["solver_contract"]["max_queries"]),
            )
        )
        typed_recipe_material += "\0" + source_requirement_id
        typed_recipe_material += "\0complete"
        for candidate_id in ("candidate.a", "candidate.b"):
            typed_recipe_material += "\0" + candidate_id
        for action_id in joint_actions:
            typed_recipe_material += "\0" + action_id
        typed_recipes["artifact_id"] = stable_semantic_id(
            "mutation-recipes", typed_recipe_material
        )
        source_recipe_overlay = copy.deepcopy(typed_overlay)
        source_recipe_overlay["joint_action_constraints"] = []

        def typed_recipe_case(
            name: str, value: Mapping[str, Any], expected: str
        ) -> None:
            case_audit = Audit(root / f"{name}.json")
            _verify_recipe_semantic_closure(
                value,
                typed_property,
                typed_graph,
                typed_candidates,
                source_recipe_overlay,
                case_audit,
            )
            result = case_audit.report(None)
            checks.append(
                {
                    "name": name,
                    "verdict": result["verdict"],
                    "failures": result["failures"],
                    "expected": expected,
                }
            )

        typed_recipe_case(
            "typed_recipe_joint_prerequisite_timing_positive",
            typed_recipes,
            "PASS",
        )
        split_recipes = copy.deepcopy(typed_recipes)
        for recipe in split_recipes["recipes"]:
            candidate = candidates_by_name[recipe["frontier_candidate_id"]]
            action_id = candidate["action"]["external_action_id"]
            recipe["action_hyperedge"] = {
                "hyperedge_id": stable_semantic_id(
                    "action-hyperedge", action_id
                ),
                "action_ids": [action_id],
                "indivisible": True,
                "claim": "SINGLE_ACTION",
            }
            recipe["action_mutations"] = [
                item
                for item in recipe["action_mutations"]
                if item["action_id"] == action_id
            ]
            recipe["recipe_id"] = stable_semantic_id(
                "recipe",
                "\0".join(
                    (
                        candidate["candidate_id"],
                        candidate["cone_id"],
                        candidate["ap_id"],
                        recipe["solver_query"]["query_sha256"],
                        action_id,
                    )
                ),
            )
        split_recipes["artifact_id"] = stable_semantic_id(
            "mutation-recipes",
            "\0".join(
                (
                    *typed_recipe_inputs.values(),
                    typed_recipes["solver_contract"]["solver_version"],
                    str(typed_recipes["solver_contract"]["timeout_ms"]),
                    str(typed_recipes["solver_contract"]["max_queries"]),
                )
            ),
        )
        typed_recipe_case(
            "typed_recipe_coherent_joint_split_tamper",
            split_recipes,
            "FAIL",
        )
        timing_tamper = copy.deepcopy(typed_recipes)
        next(
            item
            for item in timing_tamper["recipes"]
            if item["frontier_candidate_id"] == "candidate.a"
        )["timing"]["clock_source"] = "clock.changed"
        typed_recipe_case(
            "typed_recipe_exact_timing_tamper", timing_tamper, "FAIL"
        )
        prerequisite_tamper = copy.deepcopy(typed_recipes)
        first_recipe = next(
            item
            for item in prerequisite_tamper["recipes"]
            if item["frontier_candidate_id"] == "candidate.a"
        )
        control_choice = next(
            item
            for item in first_recipe["prerequisite_choices"]
            if item["choice_id"].startswith(
                "prerequisite-control-choice:"
            )
        )
        control_choice["alternatives"][0]["status"] = "COMPLETE"
        control_choice["alternatives"][0]["uncertainty_reasons"] = []
        typed_recipe_case(
            "typed_recipe_control_prerequisite_overclaim_tamper",
            prerequisite_tamper,
            "FAIL",
        )
        query_tamper = copy.deepcopy(typed_recipes)
        query_tamper["recipes"][0]["solver_query"]["query_sha256"] = "a" * 64
        changed_recipe = query_tamper["recipes"][0]
        changed_recipe["recipe_id"] = stable_semantic_id(
            "recipe",
            "\0".join(
                (
                    str(changed_recipe["frontier_candidate_id"]),
                    str(changed_recipe["cone_id"]),
                    str(changed_recipe["ap_id"]),
                    str(changed_recipe["solver_query"]["query_sha256"]),
                    *joint_actions,
                )
            ),
        )
        typed_recipe_case(
            "typed_recipe_joint_query_divergence_tamper",
            query_tamper,
            "FAIL",
        )
        model_property = copy.deepcopy(typed_property)
        model_property["atomic_propositions"][0]["predicate"][
            "operator"
        ] = "||"
        model_requirement_id = stable_semantic_id(
            "joint-model",
            joint_constraint["constraint_id"]
            + "\0"
            + "ap.joint.fixture",
        )
        model_hyperedge_id = stable_semantic_id(
            "action-hyperedge",
            model_requirement_id + "\0" + "\0".join(joint_actions),
        )
        model_recipes = copy.deepcopy(typed_recipes)
        for recipe in model_recipes["recipes"]:
            recipe["action_hyperedge"]["hyperedge_id"] = (
                model_hyperedge_id
            )
        model_material = "\0".join(
            (
                *typed_recipe_inputs.values(),
                model_recipes["solver_contract"]["solver_version"],
                str(model_recipes["solver_contract"]["timeout_ms"]),
                str(model_recipes["solver_contract"]["max_queries"]),
            )
        )
        model_material += "\0" + model_requirement_id + "\0complete"
        for candidate_id in ("candidate.a", "candidate.b"):
            model_material += "\0" + candidate_id
        for action_id in joint_actions:
            model_material += "\0" + action_id
        model_material += "\0" + joint_constraint["constraint_id"]
        model_recipes["artifact_id"] = stable_semantic_id(
            "mutation-recipes", model_material
        )

        def typed_model_recipe_case(
            name: str, value: Mapping[str, Any], expected: str
        ) -> None:
            case_audit = Audit(root / f"{name}.json")
            _verify_recipe_semantic_closure(
                value,
                model_property,
                typed_graph,
                typed_candidates,
                typed_overlay,
                case_audit,
            )
            result = case_audit.report(None)
            checks.append(
                {
                    "name": name,
                    "verdict": result["verdict"],
                    "failures": result["failures"],
                    "expected": expected,
                }
            )

        typed_model_recipe_case(
            "typed_recipe_model_all_required_positive",
            model_recipes,
            "PASS",
        )
        split_model_recipes = copy.deepcopy(model_recipes)
        for recipe in split_model_recipes["recipes"]:
            candidate = candidates_by_name[recipe["frontier_candidate_id"]]
            action_id = candidate["action"]["external_action_id"]
            recipe["action_hyperedge"] = {
                "hyperedge_id": stable_semantic_id(
                    "action-hyperedge", action_id
                ),
                "action_ids": [action_id],
                "indivisible": True,
                "claim": "SINGLE_ACTION",
            }
            recipe["action_mutations"] = [
                item
                for item in recipe["action_mutations"]
                if item["action_id"] == action_id
            ]
            recipe["recipe_id"] = stable_semantic_id(
                "recipe",
                "\0".join(
                    (
                        candidate["candidate_id"],
                        candidate["cone_id"],
                        candidate["ap_id"],
                        recipe["solver_query"]["query_sha256"],
                        action_id,
                    )
                ),
            )
        split_model_recipes["artifact_id"] = stable_semantic_id(
            "mutation-recipes",
            "\0".join(
                (
                    *typed_recipe_inputs.values(),
                    split_model_recipes["solver_contract"][
                        "solver_version"
                    ],
                    str(
                        split_model_recipes["solver_contract"][
                            "timeout_ms"
                        ]
                    ),
                    str(
                        split_model_recipes["solver_contract"][
                            "max_queries"
                        ]
                    ),
                )
            ),
        )
        typed_model_recipe_case(
            "typed_recipe_model_all_required_split_tamper",
            split_model_recipes,
            "FAIL",
        )

        mutations: list[tuple[str, Any]] = []
        extra = copy.deepcopy(m5)
        extra["unexpected"] = True
        mutations.append(("closed_schema", extra))
        bad_stage = copy.deepcopy(m5)
        bad_stage["stages"][1]["input_sha256"].reverse()
        bad_stage["certificate_id"] = m5_certificate_id(bad_stage)
        mutations.append(("stage_order", bad_stage))
        bad_output_order = copy.deepcopy(m5)
        bad_output_order["outputs"][1], bad_output_order["outputs"][2] = (
            bad_output_order["outputs"][2],
            bad_output_order["outputs"][1],
        )
        bad_output_order["certificate_id"] = m5_certificate_id(bad_output_order)
        mutations.append(("occurrence_output_order", bad_output_order))
        bad_occurrence_stage_order = copy.deepcopy(m5)
        (
            bad_occurrence_stage_order["stages"][1],
            bad_occurrence_stage_order["stages"][2],
        ) = (
            bad_occurrence_stage_order["stages"][2],
            bad_occurrence_stage_order["stages"][1],
        )
        bad_occurrence_stage_order["certificate_id"] = m5_certificate_id(
            bad_occurrence_stage_order
        )
        mutations.append(
            ("occurrence_stage_order", bad_occurrence_stage_order)
        )
        bad_occurrence_aggregate = copy.deepcopy(m5)
        bad_occurrence_aggregate["stages"][1]["status"] = (
            "CONSERVATIVE_INCOMPLETE"
        )
        bad_occurrence_aggregate["certificate_id"] = m5_certificate_id(
            bad_occurrence_aggregate
        )
        mutations.append(
            ("occurrence_status_aggregate", bad_occurrence_aggregate)
        )
        for case_name, key in (
            ("occurrence_property_link", "property_ir_sha256"),
            ("occurrence_semantic_index_link", "semantic_index_sha256"),
            (
                "occurrence_index_context_link",
                "canonical_compilation_database_sha256",
            ),
            ("occurrence_path_map_link", "path_map_sha256"),
        ):
            bad_occurrence_value = copy.deepcopy(occurrences)
            bad_occurrence_value[key] = "f" * 64
            bad_occurrence_file = save(
                f"{case_name}.json", bad_occurrence_value
            )
            bad_occurrence = copy.deepcopy(m5)
            bad_occurrence["outputs"][1]["path"] = bad_occurrence_file["path"]
            bad_occurrence["outputs"][1]["sha256"] = bad_occurrence_file[
                "sha256"
            ]
            bad_occurrence_recipes_value = copy.deepcopy(recipes)
            bad_occurrence_recipes_value[
                "predicate_occurrence_bindings_sha256"
            ] = bad_occurrence_file["sha256"]
            bad_occurrence_recipes_file = save(
                f"{case_name}_mutation_recipes.json",
                bad_occurrence_recipes_value,
            )
            bad_occurrence["outputs"][4]["path"] = (
                bad_occurrence_recipes_file["path"]
            )
            bad_occurrence["outputs"][4]["sha256"] = (
                bad_occurrence_recipes_file["sha256"]
            )
            bad_occurrence_replay_value = copy.deepcopy(replay)
            bad_occurrence_replay_value["mutation_recipes_sha256"] = (
                bad_occurrence_recipes_file["sha256"]
            )
            bad_occurrence_replay_file = save(
                f"{case_name}_recipe_replay_obligations.json",
                bad_occurrence_replay_value,
            )
            bad_occurrence["outputs"][5]["path"] = (
                bad_occurrence_replay_file["path"]
            )
            bad_occurrence["outputs"][5]["sha256"] = (
                bad_occurrence_replay_file["sha256"]
            )
            bad_occurrence_expected = _expected_m5_stages(bad_occurrence)
            for stage in bad_occurrence["stages"]:
                expected_inputs, expected_outputs = bad_occurrence_expected[
                    stage["name"]
                ]
                stage["input_sha256"] = expected_inputs
                stage["output_sha256"] = expected_outputs
            bad_occurrence["certificate_id"] = m5_certificate_id(
                bad_occurrence
            )
            mutations.append((case_name, bad_occurrence))
        bad_recipe_occurrence_value = copy.deepcopy(recipes)
        bad_recipe_occurrence_value[
            "predicate_occurrence_bindings_sha256"
        ] = "f" * 64
        bad_recipe_occurrence_file = save(
            "occurrence_recipe_link_mutation_recipes.json",
            bad_recipe_occurrence_value,
        )
        bad_recipe_occurrence_replay_value = copy.deepcopy(replay)
        bad_recipe_occurrence_replay_value["mutation_recipes_sha256"] = (
            bad_recipe_occurrence_file["sha256"]
        )
        bad_recipe_occurrence_replay_file = save(
            "occurrence_recipe_link_replay.json",
            bad_recipe_occurrence_replay_value,
        )
        bad_recipe_occurrence = copy.deepcopy(m5)
        bad_recipe_occurrence["outputs"][4].update(
            path=bad_recipe_occurrence_file["path"],
            sha256=bad_recipe_occurrence_file["sha256"],
        )
        bad_recipe_occurrence["outputs"][5].update(
            path=bad_recipe_occurrence_replay_file["path"],
            sha256=bad_recipe_occurrence_replay_file["sha256"],
        )
        bad_recipe_occurrence_expected = _expected_m5_stages(
            bad_recipe_occurrence
        )
        for stage in bad_recipe_occurrence["stages"]:
            expected_inputs, expected_outputs = (
                bad_recipe_occurrence_expected[stage["name"]]
            )
            stage["input_sha256"] = expected_inputs
            stage["output_sha256"] = expected_outputs
        bad_recipe_occurrence["certificate_id"] = m5_certificate_id(
            bad_recipe_occurrence
        )
        mutations.append(("occurrence_recipe_link", bad_recipe_occurrence))
        bad_m4 = copy.deepcopy(m5)
        bad_m4["m4_commitments"]["ap_bindings"]["sha256"] = "a" * 64
        bad_m4["certificate_id"] = m5_certificate_id(bad_m4)
        mutations.append(("m4_commitment", bad_m4))
        bad_solver = copy.deepcopy(m5)
        bad_solver["solver"]["component_sha256"] = "b" * 64
        bad_solver["certificate_id"] = m5_certificate_id(bad_solver)
        mutations.append(("solver_component", bad_solver))
        bad_unknown = copy.deepcopy(m5)
        bad_unknown["invariants"]["unknown_recipe_emitted"] = False
        bad_unknown["certificate_id"] = m5_certificate_id(bad_unknown)
        mutations.append(("unknown_invariant", bad_unknown))
        bad_id = copy.deepcopy(m5)
        bad_id["certificate_id"] = "m5-certificate:" + "f" * 64
        mutations.append(("certificate_identity", bad_id))
        bad_kind = copy.deepcopy(m5)
        bad_kind["outputs"][1]["kind"] = "model_fact_overlay"
        bad_kind["certificate_id"] = m5_certificate_id(bad_kind)
        mutations.append(("artifact_kind_uniqueness", bad_kind))
        bad_pack_metadata = copy.deepcopy(m5)
        bad_pack_metadata["model_packs"][0]["model_pack_id"] = "model.changed"
        bad_pack_metadata["certificate_id"] = m5_certificate_id(bad_pack_metadata)
        mutations.append(("pack_metadata", bad_pack_metadata))
        bad_executor_metadata = copy.deepcopy(m5)
        bad_executor_metadata["executor_manifest"]["executor_version"] = "2.0.0"
        bad_executor_metadata["certificate_id"] = m5_certificate_id(bad_executor_metadata)
        mutations.append(("executor_metadata", bad_executor_metadata))
        bad_runtime_identity = copy.deepcopy(m5)
        bad_runtime_identity["runtime_components"][0]["component_id"] = "tool.changed"
        bad_runtime_identity["analyzer"]["runtime_component_id"] = "tool.changed"
        bad_runtime_identity["certificate_id"] = m5_certificate_id(bad_runtime_identity)
        mutations.append(("runtime_identity", bad_runtime_identity))
        bad_timeout_status = copy.deepcopy(m5)
        bad_timeout_status["solver"]["timeouts"] = 1
        bad_timeout_status["certificate_id"] = m5_certificate_id(bad_timeout_status)
        mutations.append(("timeout_complete_status", bad_timeout_status))
        bad_solver_count = copy.deepcopy(m5)
        bad_solver_count["solver"]["queries"] = 0
        bad_solver_count["certificate_id"] = m5_certificate_id(bad_solver_count)
        mutations.append(("solver_query_accounting", bad_solver_count))
        bad_budget_digest = copy.deepcopy(m5)
        bad_budget_digest["solver"]["max_queries"] = 9999
        bad_budget_digest["certificate_id"] = m5_certificate_id(bad_budget_digest)
        mutations.append(("solver_budget_digest", bad_budget_digest))
        bad_budget_stage = copy.deepcopy(m5)
        bad_budget_stage["solver"]["max_queries"] = 9999
        bad_budget_stage["solver"]["budget_sha256"] = solver_budget_sha256(
            bad_budget_stage["solver"]
        )
        bad_budget_stage["certificate_id"] = m5_certificate_id(bad_budget_stage)
        mutations.append(("solver_budget_stage", bad_budget_stage))
        for name, value in mutations:
            _write_json(certificate_path, value)
            result = verify_certificate(certificate_path, schema_dir, validate_semantic_schemas=False)
            checks.append({"name": name, "verdict": result["verdict"], "failures": result["failures"]})

        # Restore the valid certificate and tamper the new sidecar bytes before
        # separately exercising the existing model-pack byte check.
        _write_json(certificate_path, m5)
        pathlib.Path(occurrences_file["path"]).write_bytes(b"tampered\n")
        occurrence_tamper = verify_certificate(
            certificate_path, schema_dir, validate_semantic_schemas=False
        )
        checks.append(
            {
                "name": "occurrence_physical_tamper",
                "verdict": occurrence_tamper["verdict"],
                "failures": occurrence_tamper["failures"],
            }
        )
        _write_json(pathlib.Path(occurrences_file["path"]), occurrences)
        pathlib.Path(pack_file["path"]).write_bytes(b"tampered\n")
        tamper = verify_certificate(certificate_path, schema_dir, validate_semantic_schemas=False)
        checks.append({"name": "physical_tamper", "verdict": tamper["verdict"], "failures": tamper["failures"]})

        certificate_path.write_text(
            '{"schema_version":"1.0.0","schema_version":"1.0.0"}\n',
            encoding="utf-8",
        )
        duplicate_json = verify_certificate(
            certificate_path, schema_dir, validate_semantic_schemas=False
        )
        checks.append(
            {
                "name": "duplicate_json_key",
                "verdict": duplicate_json["verdict"],
                "failures": duplicate_json["failures"],
            }
        )

    positive_names = {"positive", "positive_without_executor"}
    passed = all(
        item["verdict"]
        == item.get(
            "expected", "PASS" if item["name"] in positive_names else "FAIL"
        )
        for item in checks
    )
    summary = {
        "schema_version": "rift-m5-certificate-selftest/1.0.0",
        "verdict": "PASS" if passed else "FAIL",
        "checks": len(checks),
        "cases": checks,
    }
    return (0 if passed else 1), summary


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    default_schema_dir = pathlib.Path(__file__).resolve().parents[1] / "schema"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", nargs="?", type=pathlib.Path, help="M5 certificate JSON or its analysis directory")
    parser.add_argument("--schema-dir", type=pathlib.Path, default=default_schema_dir)
    parser.add_argument("--report", type=pathlib.Path, help="also write the JSON verification receipt here")
    parser.add_argument("--self-test", action="store_true", help="run deterministic positive/negative regressions")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_args(sys.argv[1:] if argv is None else argv)
    if options.self_test:
        code, report = _self_test(options.schema_dir)
    else:
        if options.certificate is None:
            print("certificate path is required unless --self-test is used", file=sys.stderr)
            return 2
        certificate = options.certificate
        if certificate.is_dir():
            certificate = certificate / "m5_analysis_certificate.json"
        report = verify_certificate(certificate, options.schema_dir)
        code = 0 if report["verdict"] == "PASS" else 1
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if options.report is not None:
        options.report.parent.mkdir(parents=True, exist_ok=True)
        options.report.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
