#!/usr/bin/env python3
"""Independent verifier for RIFT M4 certificates and influence artifacts.

This verifier intentionally uses only the Python standard library.  It audits
bytes and graph claims already present in an analysis bundle; it does not trust
the analyzer implementation and it never attempts to infer missing evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


VERIFIER_VERSION = "0.4.0"
EXPECTED_CERTIFICATE_V2_SCHEMA_SHA256 = (
    "b47322815a208056aab5e47d77a9495407f8dd3d66f93f414d61ba1b7e995dac"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STATUSES = {
    "COMPLETE": 0,
    "CONSERVATIVE_INCOMPLETE": 1,
    "FAILED": 2,
}
STAGE_ORDER = ("index", "bind", "influence", "cone", "certificate")
OUTPUT_FILE_BY_KIND = {
    "semantic_index": "semantic_index.json",
    "ap_bindings": "ap_bindings.json",
    "contextual_influence_graph": "contextual_influence_graph.json",
    "ap_influence_cones": "ap_influence_cones.json",
}
INPUT_MANIFEST_VERSION = "input-manifest/1.0.0"
INPUT_ROLE_ORDER = {
    "main": 0,
    "user_header": 1,
    "generated": 2,
    "system": 3,
    "toolchain": 4,
}
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
BUILD_MANIFEST_CORE_FILES = (
    "cli/production_entry.cpp",
    "cli/production_main.cpp",
    "cli/production_main.h",
    "core/production/artifact_loader.cpp",
    "core/production/binding.cpp",
    "core/production/clang_indexer.cpp",
    "core/production/compilation_plan.cpp",
    "core/production/identity.cpp",
    "core/production/influence.cpp",
    "scripts/generate_embedded_manifest.py",
)
BUILD_MANIFEST_FIELDS = {
    "schema_version",
    "identity_policy",
    "production_core_sha256",
    "schema_bundle_sha256",
    "production_core_files",
    "schema_files",
}
CERTIFICATE_V2_FIELDS = {
    "schema_version",
    "certificate_id",
    "analysis_id",
    "status",
    "analyzer",
    "build_manifest",
    "core_tree_sha256",
    "schema_bundle_sha256",
    "environment",
    "inputs",
    "source_input_provenance",
    "toolchain",
    "outputs",
    "stages",
    "unsupported_constructs",
    "started_at",
    "finished_at",
}
CERTIFICATE_V2_INPUT_ORDER = (
    "typed_property_ir",
    "compile_commands",
    "source_inputs",
)
CERTIFICATE_V2_OUTPUT_ORDER = tuple(OUTPUT_FILE_BY_KIND)


class VerificationDataError(ValueError):
    """Raised when an artifact cannot be consumed safely."""


@dataclass(frozen=True)
class Finding:
    check_id: str
    status: str
    detail: str

    def to_json(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class Audit:
    findings: list[Finding] = field(default_factory=list)

    def passed(self, check_id: str, detail: str) -> None:
        self.findings.append(Finding(check_id, "PASS", detail))

    def failed(self, check_id: str, detail: str) -> None:
        self.findings.append(Finding(check_id, "FAIL", detail))

    def unsupported(self, check_id: str, detail: str) -> None:
        self.findings.append(Finding(check_id, "UNSUPPORTED", detail))

    @property
    def failures(self) -> list[Finding]:
        return [item for item in self.findings if item.status == "FAIL"]

    @property
    def unsupported_findings(self) -> list[Finding]:
        return [item for item in self.findings if item.status == "UNSUPPORTED"]

    def report(self, certificate: Path, strict_provenance: bool) -> dict[str, Any]:
        strict_failure = strict_provenance and bool(self.unsupported_findings)
        if self.failures or strict_failure:
            overall = "FAIL"
        elif self.unsupported_findings:
            overall = "PASS_WITH_UNSUPPORTED_ASSURANCE"
        else:
            overall = "PASS"
        return {
            "schema_version": "rift.verification-report/1.0.0",
            "verifier_version": VERIFIER_VERSION,
            "certificate_path": str(certificate.resolve()),
            "overall_status": overall,
            "strict_provenance": strict_provenance,
            "failure_count": len(self.failures),
            "unsupported_count": len(self.unsupported_findings),
            "findings": [item.to_json() for item in self.findings],
        }


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_regular_file(path: Path) -> tuple[bytes, str]:
    """Read stable regular-file bytes while rejecting replacement or writes."""
    before = path.stat()
    if not path.is_file():
        raise OSError(f"not a regular file: {path}")
    with path.open("rb") as stream:
        opened_before = os.fstat(stream.fileno())
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        opened_before_identity = (
            opened_before.st_dev,
            opened_before.st_ino,
            opened_before.st_size,
            opened_before.st_mtime_ns,
            opened_before.st_ctime_ns,
        )
        if before_identity != opened_before_identity:
            raise OSError(f"path changed before rehash: {path}")
        payload = stream.read()
        opened_after = os.fstat(stream.fileno())
    after = path.stat()
    opened_after_identity = (
        opened_after.st_dev,
        opened_after.st_ino,
        opened_after.st_size,
        opened_after.st_mtime_ns,
        opened_after.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if opened_before_identity != opened_after_identity or (
        opened_after_identity != after_identity
    ):
        raise OSError(f"path changed during rehash: {path}")
    if len(payload) != opened_after.st_size:
        raise OSError(f"short/expansive read while rehashing: {path}")
    return payload, _sha256_bytes(payload)


def _rehash_regular_file(path: Path) -> tuple[str, int]:
    before = path.stat()
    if not path.is_file():
        raise OSError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    byte_size = 0
    with path.open("rb") as stream:
        opened_before = os.fstat(stream.fileno())
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        opened_before_identity = (
            opened_before.st_dev,
            opened_before.st_ino,
            opened_before.st_size,
            opened_before.st_mtime_ns,
            opened_before.st_ctime_ns,
        )
        if before_identity != opened_before_identity:
            raise OSError(f"path changed before rehash: {path}")
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
            byte_size += len(block)
        opened_after = os.fstat(stream.fileno())
    after = path.stat()
    opened_after_identity = (
        opened_after.st_dev,
        opened_after.st_ino,
        opened_after.st_size,
        opened_after.st_mtime_ns,
        opened_after.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if opened_before_identity != opened_after_identity or (
        opened_after_identity != after_identity
    ):
        raise OSError(f"path changed during rehash: {path}")
    if byte_size != opened_after.st_size:
        raise OSError(f"short/expansive read while rehashing: {path}")
    return digest.hexdigest(), byte_size


def _load_json(path: Path) -> Any:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise VerificationDataError(f"cannot read {path}: {error}") from error
    if not payload:
        raise VerificationDataError(f"artifact is empty: {path}")
    try:
        return json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationDataError(f"invalid JSON in {path}: {error}") from error


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _as_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VerificationDataError(f"{label} must be a JSON object")
    return value


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerificationDataError(f"{label} must be a JSON array")
    return value


def _status_rank(value: Any) -> int | None:
    return STATUSES.get(value) if isinstance(value, str) else None


def _worst_status(values: Iterable[str]) -> str:
    materialized = [
        item if isinstance(item, str) and item in STATUSES else "FAILED"
        for item in values
    ]
    if not materialized:
        return "COMPLETE"
    return max(materialized, key=lambda item: STATUSES[item])


def _unique_nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_is_nonempty_string(item) for item in value)
        and len(value) == len(set(value))
    )


def _gap_lower_bound(gaps: Sequence[Any]) -> str:
    rank = 0
    for raw in gaps:
        if not isinstance(raw, dict):
            return "FAILED"
        effect = raw.get("effect")
        if effect == "stage_failure":
            rank = max(rank, 2)
        elif effect == "soundness_risk":
            rank = max(rank, 1)
        elif effect != "precision_loss":
            rank = max(rank, 2)
    return next(name for name, value in STATUSES.items() if value == rank)


def _u64(value: int) -> bytes:
    return value.to_bytes(8, byteorder="big", signed=False)


def length_prefixed_material(values: Sequence[str]) -> bytes:
    material = bytearray()
    for value in values:
        encoded = value.encode("utf-8")
        material.extend(_u64(len(encoded)))
        material.extend(encoded)
    return bytes(material)


def configuration_sha256(argv: Sequence[str]) -> str:
    return _sha256_bytes(length_prefixed_material(argv))


def configuration_v2_sha256(
    build_manifest_sha256: str, environment_sha256: str, argv: Sequence[str]
) -> str:
    return _sha256_bytes(
        length_prefixed_material(
            [build_manifest_sha256, environment_sha256, *argv]
        )
    )


def environment_sha256(variables: Sequence[Mapping[str, Any]]) -> str:
    material = bytearray()
    for variable in variables:
        name = variable["name"].encode("utf-8")
        material.extend(_u64(len(name)))
        material.extend(name)
        material.append(1 if variable["present"] else 0)
        digest = (variable["value_sha256"] or "").encode("ascii")
        material.extend(_u64(len(digest)))
        material.extend(digest)
    return _sha256_bytes(bytes(material))


def input_file_id(
    identity_scheme: str, role: str, logical_path: str, content_sha256: str
) -> str:
    material = (
        identity_scheme.encode("utf-8")
        + b"\0"
        + role.encode("utf-8")
        + b"\0"
        + logical_path.encode("utf-8")
        + b"\0"
        + content_sha256.encode("ascii")
    )
    return "input-file:" + _sha256_bytes(material)


def input_manifest_sha256(identity_scheme: str, input_files: Sequence[Mapping[str, Any]]) -> str:
    material = bytearray(
        identity_scheme.encode("utf-8") + b"\0" + INPUT_MANIFEST_VERSION.encode("ascii")
    )
    for item in input_files:
        role = item["role"]
        logical_path = item["logical_path"]
        content_sha256 = item["sha256"]
        byte_size = item["byte_size"]
        encoded_path = logical_path.encode("utf-8")
        material.extend(b"\0")
        material.extend(role.encode("ascii"))
        material.extend(b"\0")
        material.extend(str(len(encoded_path)).encode("ascii"))
        material.extend(b":")
        material.extend(encoded_path)
        material.extend(b"\0")
        material.extend(content_sha256.encode("ascii"))
        material.extend(b"\0")
        material.extend(str(byte_size).encode("ascii"))
    return _sha256_bytes(bytes(material))


def semantic_index_artifact_id(index: Mapping[str, Any]) -> str:
    material = (
        index["identity_scheme"].encode("utf-8")
        + b"\0"
        + index["canonical_compilation_database_sha256"].encode("ascii")
        + b"\0"
        + index["path_map_sha256"].encode("ascii")
        + b"\0"
        + index["input_manifest_sha256"].encode("ascii")
    )
    return "index:" + _sha256_bytes(material)


def stable_id(prefix: str, semantic_material: str | bytes) -> str:
    encoded = (
        semantic_material.encode("utf-8")
        if isinstance(semantic_material, str)
        else semantic_material
    )
    return prefix + ":" + _sha256_bytes(encoded)


def canonical_tree_sha256(root: Path, relative_roots: Sequence[str]) -> str:
    normalized = root.resolve(strict=True)
    files: set[Path] = set()
    for relative in relative_roots:
        directory = (normalized / relative).resolve(strict=False)
        if not directory.exists():
            continue
        if not directory.is_dir():
            raise VerificationDataError(f"tree member is not a directory: {directory}")
        files.update(path.resolve() for path in directory.rglob("*") if path.is_file())
    if not files:
        raise VerificationDataError(f"canonical tree is empty below {normalized}")
    ordered = sorted(files, key=lambda path: path.relative_to(normalized).as_posix())
    digest = hashlib.sha256()
    for path in ordered:
        relative = path.relative_to(normalized).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(_u64(len(relative)))
        digest.update(relative)
        digest.update(_u64(len(payload)))
        digest.update(payload)
    return digest.hexdigest()


def _strict_or_unsupported(
    audit: Audit, strict: bool, check_id: str, detail: str
) -> None:
    if strict:
        audit.failed(check_id, detail)
    else:
        audit.unsupported(check_id, detail)


def _manifest_tree_digest(
    root: Path, records: Sequence[Mapping[str, Any]], label: str
) -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    paths: list[str] = []
    normalized_root = root.resolve(strict=True)
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise VerificationDataError(f"{label}[{index}] is not an object")
        if set(record) != {"path", "sha256"}:
            raise VerificationDataError(
                f"{label}[{index}] has missing or unexpected fields"
            )
        relative = record.get("path")
        expected = record.get("sha256")
        if not _is_nonempty_string(relative) or not _is_sha256(expected):
            raise VerificationDataError(f"{label}[{index}] has malformed path/digest")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise VerificationDataError(f"{label} contains unsafe path: {relative}")
        physical = (normalized_root / relative_path).resolve(strict=True)
        try:
            physical.relative_to(normalized_root)
        except ValueError as error:
            raise VerificationDataError(f"{label} escapes source root: {relative}") from error
        payload, actual = _read_regular_file(physical)
        if actual != expected:
            raise VerificationDataError(f"{label} source bytes differ: {relative}")
        relative_bytes = relative.encode("utf-8")
        digest.update(_u64(len(relative_bytes)))
        digest.update(relative_bytes)
        digest.update(_u64(len(payload)))
        digest.update(payload)
        paths.append(relative)
    if not paths or paths != sorted(paths) or len(paths) != len(set(paths)):
        raise VerificationDataError(f"{label} must be non-empty, unique, canonical order")
    return digest.hexdigest(), paths


def _verify_build_manifest(
    certificate: Mapping[str, Any],
    audit: Audit,
    *,
    build_manifest_path: Path | None,
    implementation_root: Path | None,
    binary: Path | None,
    strict_provenance: bool,
) -> None:
    if certificate.get("schema_version") != "2.0.0":
        audit.unsupported(
            "build_manifest.v2",
            "certificate v1 has no independently replayable embedded build manifest",
        )
        return
    embedded = certificate.get("build_manifest")
    if not isinstance(embedded, dict):
        audit.failed("build_manifest.v2", "certificate v2 build_manifest is missing")
        return
    if set(embedded) != {
        "identity_policy",
        "manifest_sha256",
        "production_core_sha256",
        "schema_bundle_sha256",
    }:
        audit.failed(
            "build_manifest.contract",
            "certificate build_manifest has missing or unexpected fields",
        )
    if build_manifest_path is None:
        _strict_or_unsupported(
            audit,
            strict_provenance,
            "build_manifest.file",
            "generated rift_build_manifest.json was not supplied",
        )
        return
    if not build_manifest_path.is_file():
        audit.failed("build_manifest.file", f"build manifest is absent: {build_manifest_path}")
        return
    try:
        manifest_payload, raw_digest = _read_regular_file(build_manifest_path)
        manifest = _as_object(json.loads(manifest_payload), "build manifest")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, VerificationDataError) as error:
        audit.failed("build_manifest.file", str(error))
        return
    if raw_digest != embedded.get("manifest_sha256"):
        audit.failed("build_manifest.file", "generated build-manifest byte digest differs")
        return
    if manifest.get("schema_version") != "rift.build-manifest.v1" or (
        manifest.get("identity_policy") != "relative-path-and-content-v1"
    ):
        audit.failed("build_manifest.contract", "unsupported generated manifest contract")
        return
    if set(manifest) != BUILD_MANIFEST_FIELDS:
        audit.failed(
            "build_manifest.contract",
            "generated manifest has missing or unexpected top-level fields",
        )
    for field_name in ("production_core_sha256", "schema_bundle_sha256"):
        if manifest.get(field_name) != embedded.get(field_name):
            audit.failed(
                "build_manifest.contract", f"certificate and generated manifest differ: {field_name}"
            )
    if embedded.get("identity_policy") != manifest.get("identity_policy"):
        audit.failed("build_manifest.contract", "identity policy differs")
    if embedded.get("production_core_sha256") != certificate.get("core_tree_sha256"):
        audit.failed("build_manifest.contract", "top-level core digest differs")
    if embedded.get("schema_bundle_sha256") != certificate.get("schema_bundle_sha256"):
        audit.failed("build_manifest.contract", "top-level schema digest differs")

    if implementation_root is None:
        _strict_or_unsupported(
            audit,
            strict_provenance,
            "build_manifest.source_tree",
            "implementation root was not supplied for build-manifest replay",
        )
    else:
        try:
            root = implementation_root.resolve(strict=True)
            raw_core_records = manifest.get("production_core_files")
            raw_schema_records = manifest.get("schema_files")
            if not isinstance(raw_core_records, list) or not isinstance(
                raw_schema_records, list
            ):
                raise VerificationDataError("manifest file-record arrays are missing")
            core_digest, core_paths = _manifest_tree_digest(
                root, raw_core_records, "production_core_files"
            )
            schema_digest, schema_paths = _manifest_tree_digest(
                root, raw_schema_records, "schema_files"
            )
            expected_core = set(BUILD_MANIFEST_CORE_FILES)
            include_root = root / "include" / "rift" / "core"
            expected_core.update(
                path.relative_to(root).as_posix()
                for path in include_root.rglob("*")
                if path.is_file()
            )
            expected_schema = {
                path.relative_to(root).as_posix()
                for path in (root / "schema").rglob("*")
                if path.is_file()
            }
            if set(core_paths) != expected_core:
                raise VerificationDataError("production-core file set is incomplete or expansive")
            if set(schema_paths) != expected_schema:
                raise VerificationDataError("schema file set is incomplete or expansive")
            if core_digest != manifest.get("production_core_sha256"):
                raise VerificationDataError("production-core aggregate digest differs")
            if schema_digest != manifest.get("schema_bundle_sha256"):
                raise VerificationDataError("schema aggregate digest differs")
            schema_record = next(
                (
                    item
                    for item in raw_schema_records
                    if item.get("path") == "schema/analysis_certificate.schema.json"
                ),
                None,
            )
            if schema_record is None or schema_record.get("sha256") != (
                EXPECTED_CERTIFICATE_V2_SCHEMA_SHA256
            ):
                raise VerificationDataError("certificate-v2 schema digest is not the frozen value")
            audit.passed(
                "build_manifest.source_tree",
                f"replayed {len(core_paths)} production and {len(schema_paths)} schema files",
            )
        except (OSError, VerificationDataError, ValueError) as error:
            audit.failed("build_manifest.source_tree", str(error))

    if binary is None:
        _strict_or_unsupported(
            audit,
            strict_provenance,
            "build_manifest.binary_embedding",
            "analyzer binary was not supplied for embedded-manifest inspection",
        )
    elif not binary.is_file():
        audit.failed("build_manifest.binary_embedding", f"binary is absent: {binary}")
    else:
        try:
            payload, _ = _read_regular_file(binary)
            values = (
                embedded.get("identity_policy"),
                embedded.get("production_core_sha256"),
                embedded.get("schema_bundle_sha256"),
                embedded.get("manifest_sha256"),
            )
            missing = [
                value
                for value in values
                if not _is_nonempty_string(value)
                or value.encode("ascii") not in payload
            ]
            if missing:
                audit.failed(
                    "build_manifest.binary_embedding",
                    "binary does not embed every certified build-manifest commitment",
                )
            else:
                audit.passed(
                    "build_manifest.binary_embedding",
                    "binary embeds policy, manifest, production-core, and schema commitments",
                )
        except (OSError, UnicodeEncodeError) as error:
            audit.failed("build_manifest.binary_embedding", str(error))
    if not any(
        item.status == "FAIL" and item.check_id.startswith("build_manifest.")
        for item in audit.findings
    ):
        audit.passed("build_manifest.contract", "generated and certified build manifests agree")


def _verify_environment(
    certificate: Mapping[str, Any],
    audit: Audit,
    *,
    environment_json: Path | None,
    verify_current_environment: bool,
    strict_provenance: bool,
) -> None:
    if certificate.get("schema_version") != "2.0.0":
        audit.unsupported("environment.v2", "certificate v1 has no semantic environment")
        return
    environment = certificate.get("environment")
    analyzer = certificate.get("analyzer")
    if not isinstance(environment, dict) or not isinstance(analyzer, dict):
        audit.failed("environment.v2", "certificate v2 environment/analyzer is missing")
        return
    if set(environment) != {"digest", "variables"}:
        audit.failed("environment.v2", "environment has missing or unexpected fields")
        return
    variables = environment.get("variables")
    if not isinstance(variables, list) or len(variables) != 16:
        audit.failed("environment.v2", "environment must contain exactly 16 variables")
        return
    names = tuple(
        item.get("name") if isinstance(item, dict) else None for item in variables
    )
    if names != SEMANTIC_ENVIRONMENT_VARIABLES:
        audit.failed("environment.v2", "environment whitelist or canonical order differs")
        return
    shape_ok = True
    for item in variables:
        if not isinstance(item, dict) or set(item) != {
            "name",
            "present",
            "value_sha256",
        }:
            audit.failed("environment.v2", "environment variable record shape differs")
            shape_ok = False
            continue
        present = item.get("present")
        value_digest = item.get("value_sha256")
        if not isinstance(present, bool) or (
            present and not _is_sha256(value_digest)
        ) or (not present and value_digest is not None):
            audit.failed("environment.v2", f"invalid environment record: {item.get('name')}")
            shape_ok = False
    if not shape_ok:
        return
    aggregate = environment_sha256(variables)
    if aggregate != environment.get("digest") or aggregate != analyzer.get(
        "environment_sha256"
    ):
        audit.failed("environment.v2", "environment aggregate/analyzer digest differs")
        return
    audit.passed("environment.v2", "exact 16-variable hash vector and aggregate agree")

    raw_values: Mapping[str, Any] | None = None
    if environment_json is not None and verify_current_environment:
        audit.failed(
            "environment.raw_values",
            "choose either --environment-json or --verify-current-environment",
        )
        return
    if environment_json is not None:
        try:
            loaded = _as_object(_load_json(environment_json), "environment values")
            raw_values = loaded
        except VerificationDataError as error:
            audit.failed("environment.raw_values", str(error))
            return
    elif verify_current_environment:
        raw_values = {
            name: os.environ[name] if name in os.environ else None
            for name in SEMANTIC_ENVIRONMENT_VARIABLES
        }
    if raw_values is None:
        _strict_or_unsupported(
            audit,
            strict_provenance,
            "environment.raw_values",
            "no raw 16-variable environment snapshot was supplied for rehashing",
        )
        return
    if set(raw_values) != set(SEMANTIC_ENVIRONMENT_VARIABLES):
        audit.failed("environment.raw_values", "raw environment keys are not the exact whitelist")
        return
    for item in variables:
        value = raw_values[item["name"]]
        if value is not None and not isinstance(value, str):
            audit.failed("environment.raw_values", f"non-string value: {item['name']}")
            return
        if (value is not None) != item["present"]:
            audit.failed("environment.raw_values", f"presence differs: {item['name']}")
            return
        actual = _sha256_bytes(value.encode("utf-8")) if value is not None else None
        if actual != item["value_sha256"]:
            audit.failed("environment.raw_values", f"value digest differs: {item['name']}")
            return
    audit.passed("environment.raw_values", "all 16 supplied raw environment values rehash exactly")


def _ldd_runtime_files(binary: Path) -> list[Path]:
    ldd = shutil.which("ldd")
    if ldd is None:
        raise VerificationDataError("ldd is unavailable")
    process = subprocess.run(
        [ldd, str(binary)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    if process.returncode != 0:
        raise VerificationDataError(f"ldd failed: {process.stderr.strip()}")
    result: list[Path] = []
    for raw_line in process.stdout.splitlines():
        line = raw_line.strip()
        if not line or "not found" in line:
            if "not found" in line:
                raise VerificationDataError(f"unresolved runtime dependency: {line}")
            continue
        candidate: str | None = None
        if "=>" in line:
            right = line.split("=>", 1)[1].strip()
            if right.startswith("/"):
                candidate = right.split(" (", 1)[0]
        elif line.startswith("/"):
            candidate = line.split(" (", 1)[0]
        if candidate is not None:
            result.append(Path(candidate).resolve(strict=True))
    return result


def _verify_runtime_toolchain(
    certificate: Mapping[str, Any],
    audit: Audit,
    *,
    binary: Path | None,
    runtime_files: Sequence[Path],
    strict_provenance: bool,
) -> None:
    if certificate.get("schema_version") != "2.0.0":
        audit.unsupported("toolchain.physical_files", "certificate v1 toolchain is not replayable")
        return
    if binary is None:
        _strict_or_unsupported(
            audit,
            strict_provenance,
            "toolchain.physical_files",
            "analyzer binary is required to resolve its runtime dependencies",
        )
        return
    try:
        physical = [binary.resolve(strict=True), *_ldd_runtime_files(binary)]
        physical.extend(path.resolve(strict=True) for path in runtime_files)
        unique: list[Path] = []
        identities: set[tuple[int, int]] = set()
        for path in physical:
            metadata = path.stat()
            identity = (metadata.st_dev, metadata.st_ino)
            if identity not in identities:
                identities.add(identity)
                unique.append(path)
        physical_records = [
            {"path": path, "sha256": _rehash_regular_file(path)[0]}
            for path in unique
        ]
        physical_digests = Counter(item["sha256"] for item in physical_records)
    except (OSError, VerificationDataError, subprocess.SubprocessError) as error:
        audit.failed("toolchain.physical_files", str(error))
        return
    raw_components = certificate.get("toolchain")
    if not isinstance(raw_components, list):
        audit.failed("toolchain.physical_files", "toolchain is not an array")
        return
    certified_digests = Counter(
        item.get("sha256") for item in raw_components if isinstance(item, dict)
    )
    if physical_digests != certified_digests:
        missing = certified_digests - physical_digests
        extra = physical_digests - certified_digests
        audit.failed(
            "toolchain.physical_files",
            f"runtime file digest multiset differs; missing={dict(missing)} extra={dict(extra)}",
        )
        return
    unmatched = list(range(len(raw_components)))
    for physical_record in physical_records:
        path = physical_record["path"]
        digest = physical_record["sha256"]
        is_analyzer = path == binary.resolve(strict=True)
        candidates = [
            position
            for position in unmatched
            if isinstance(raw_components[position], dict)
            and raw_components[position].get("sha256") == digest
            and (
                (
                    is_analyzer
                    and raw_components[position].get("component_kind") == "executable"
                    and raw_components[position].get("name") == "tafuzz-sa executable"
                )
                or (
                    not is_analyzer
                    and raw_components[position].get("name") == path.name
                    and (
                        ".so" not in path.name
                        or raw_components[position].get("component_kind")
                        == "shared_object"
                    )
                )
            )
        ]
        if not candidates:
            audit.failed(
                "toolchain.physical_files",
                f"no certified name/kind/digest record matches mapped file: {path}",
            )
            return
        unmatched.remove(candidates[0])
    if unmatched:
        audit.failed(
            "toolchain.physical_files",
            "certified runtime components remain unmatched to physical mapped files",
        )
        return
    audit.passed(
        "toolchain.physical_files",
        f"{len(unique)} analyzer/loader/shared-object files rehash and identify the exact toolchain set",
    )


def _declared_input_candidates(
    declared: str, certificate: Path, path_roots: Sequence[Path]
) -> list[Path]:
    raw = Path(declared)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend(root / raw for root in path_roots)
        candidates.extend(
            (
                Path.cwd() / raw,
                certificate.parent / raw,
                certificate.parent.parent / raw,
            )
        )
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False))
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _resolve_and_verify_input(
    descriptor: Mapping[str, Any],
    certificate: Path,
    path_roots: Sequence[Path],
) -> tuple[Path | None, str | None]:
    declared = descriptor.get("path")
    expected = descriptor.get("sha256")
    if not _is_nonempty_string(declared):
        return None, "input artifact has no non-empty path"
    if not _is_sha256(expected):
        return None, "input artifact has no valid SHA-256"
    existing = [
        candidate
        for candidate in _declared_input_candidates(declared, certificate, path_roots)
        if candidate.is_file()
    ]
    if not existing:
        return None, f"declared input cannot be resolved: {declared}"
    matching: list[Path] = []
    for candidate in existing:
        try:
            actual, _ = _rehash_regular_file(candidate)
        except OSError as error:
            return None, f"cannot stably rehash {candidate}: {error}"
        if actual == expected:
            matching.append(candidate)
    if not matching:
        return None, f"no resolved input has declared bytes: {declared}"
    return matching[0].resolve(), None


def _unique_map(
    items: Sequence[Any], key: str, audit: Audit, check_id: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(items):
        if not isinstance(raw, dict) or not _is_nonempty_string(raw.get(key)):
            audit.failed(check_id, f"item {index} has no non-empty {key}")
            continue
        value = raw[key]
        if value in result:
            audit.failed(check_id, f"duplicate {key}: {value}")
            continue
        result[value] = raw
    return result


def _verify_certificate_basics(
    certificate: dict[str, Any],
    audit: Audit,
    binary: Path | None,
    argv_json: Path | None,
    strict_provenance: bool,
) -> None:
    required_strings = ("certificate_id", "analysis_id", "started_at", "finished_at")
    for name in required_strings:
        if not _is_nonempty_string(certificate.get(name)):
            audit.failed("certificate.required_fields", f"missing/non-empty field: {name}")
    schema_version = certificate.get("schema_version")
    if schema_version not in {"1.0.0", "2.0.0"}:
        audit.failed(
            "certificate.schema_version",
            f"unsupported certificate schema: {schema_version!r}",
        )
    else:
        audit.passed("certificate.schema_version", f"analysis certificate schema {schema_version}")
    if schema_version == "2.0.0" and set(certificate) != CERTIFICATE_V2_FIELDS:
        audit.failed(
            "certificate.required_fields",
            "certificate v2 has missing or unexpected top-level fields",
        )

    status = certificate.get("status")
    if _status_rank(status) is None:
        audit.failed("certificate.status", f"invalid certificate status: {status!r}")

    analyzer = certificate.get("analyzer")
    if not isinstance(analyzer, dict):
        audit.failed("certificate.analyzer", "analyzer object is missing")
        analyzer = {}
    if schema_version == "2.0.0" and set(analyzer) != {
        "name",
        "version",
        "binary_sha256",
        "configuration_sha256",
        "environment_sha256",
    }:
        audit.failed(
            "certificate.analyzer", "analyzer has missing or unexpected fields"
        )
    for field_name in ("name", "version"):
        if not _is_nonempty_string(analyzer.get(field_name)):
            audit.failed("certificate.analyzer", f"analyzer.{field_name} is missing")
    analyzer_digest_fields = ["binary_sha256", "configuration_sha256"]
    if schema_version == "2.0.0":
        analyzer_digest_fields.append("environment_sha256")
    for field_name in analyzer_digest_fields:
        if not _is_sha256(analyzer.get(field_name)):
            audit.failed("certificate.analyzer", f"analyzer.{field_name} is not SHA-256")
    if analyzer.get("name") != "tafuzz-sa":
        audit.failed("certificate.analyzer", "analyzer.name is not tafuzz-sa")

    for field_name in ("core_tree_sha256", "schema_bundle_sha256"):
        if not _is_sha256(certificate.get(field_name)):
            audit.failed("certificate.tree_digests", f"{field_name} is not SHA-256")

    toolchain = certificate.get("toolchain")
    if not isinstance(toolchain, list) or not toolchain:
        audit.failed("certificate.toolchain", "toolchain must be a non-empty array")
        toolchain = []
    valid_components = 0
    analyzer_digest_matches = 0
    component_ids: set[str] = set()
    for index, raw in enumerate(toolchain):
        if not isinstance(raw, dict):
            audit.failed("certificate.toolchain", f"toolchain[{index}] is not an object")
            continue
        if schema_version == "2.0.0" and set(raw) != {
            "component_id",
            "name",
            "version",
            "component_kind",
            "sha256",
        }:
            audit.failed(
                "certificate.toolchain",
                f"toolchain[{index}] has missing or unexpected fields",
            )
        digest_field = "sha256" if schema_version == "2.0.0" else "executable_sha256"
        valid = all(
            _is_nonempty_string(raw.get(name))
            for name in ("component_id", "name", "version")
        ) and _is_sha256(raw.get(digest_field))
        if schema_version == "2.0.0":
            valid = valid and raw.get("component_kind") in {
                "executable",
                "shared_object",
                "data",
            }
        if not valid:
            audit.failed("certificate.toolchain", f"toolchain[{index}] lacks identity/digest")
            continue
        valid_components += 1
        if raw["component_id"] in component_ids:
            audit.failed("certificate.toolchain", f"duplicate component ID: {raw['component_id']}")
        component_ids.add(raw["component_id"])
        if schema_version == "2.0.0":
            expected_id = stable_id(
                "tool",
                length_prefixed_material(
                    [
                        raw["component_kind"],
                        raw["name"],
                        raw["version"],
                        raw[digest_field],
                    ]
                ),
            )
            if raw["component_id"] != expected_id:
                audit.failed(
                    "certificate.toolchain", f"component ID mismatch: {raw['name']}"
                )
        if raw.get(digest_field) == analyzer.get("binary_sha256") and (
            schema_version != "2.0.0" or raw.get("component_kind") == "executable"
        ):
            analyzer_digest_matches += 1
    if valid_components and analyzer_digest_matches == 1:
        audit.passed(
            "certificate.toolchain",
            f"{valid_components} digest-bound runtime components include analyzer bytes",
        )
    elif valid_components and analyzer_digest_matches == 0:
        audit.failed(
            "certificate.toolchain", "analyzer binary digest is absent from toolchain"
        )
    elif valid_components:
        audit.failed(
            "certificate.toolchain",
            "analyzer binary digest occurs in multiple toolchain components",
        )

    if binary is None:
        _strict_or_unsupported(
            audit,
            strict_provenance and schema_version == "2.0.0",
            "analyzer.binary_bytes",
            "certificate records a digest but no independently supplied analyzer binary was provided",
        )
    elif not binary.is_file():
        audit.failed("analyzer.binary_bytes", f"binary does not exist: {binary}")
    else:
        try:
            binary_digest, _ = _rehash_regular_file(binary)
            if binary_digest != analyzer.get("binary_sha256"):
                audit.failed(
                    "analyzer.binary_bytes",
                    "supplied analyzer bytes do not match certificate",
                )
            else:
                audit.passed(
                    "analyzer.binary_bytes", "supplied analyzer bytes match certificate"
                )
        except OSError as error:
            audit.failed("analyzer.binary_bytes", str(error))

    if argv_json is None:
        _strict_or_unsupported(
            audit,
            strict_provenance and schema_version == "2.0.0",
            "analyzer.configuration_reconstruction",
            "certificate stores only a digest and does not embed the analyzer argv",
        )
    else:
        try:
            argv = _load_json(argv_json)
            if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
                raise VerificationDataError("argv JSON must be an array of strings")
            if schema_version == "2.0.0":
                build_manifest = certificate.get("build_manifest")
                environment = certificate.get("environment")
                if not isinstance(build_manifest, dict) or not isinstance(environment, dict):
                    raise VerificationDataError(
                        "certificate v2 build/environment commitment is missing"
                    )
                actual = configuration_v2_sha256(
                    build_manifest.get("manifest_sha256", ""),
                    environment.get("digest", ""),
                    argv,
                )
            else:
                actual = configuration_sha256(argv)
            if actual != analyzer.get("configuration_sha256"):
                audit.failed(
                    "analyzer.configuration_reconstruction",
                    "supplied argv does not match configuration digest",
                )
            else:
                audit.passed(
                    "analyzer.configuration_reconstruction",
                    "supplied argv matches configuration digest",
                )
        except VerificationDataError as error:
            audit.failed("analyzer.configuration_reconstruction", str(error))
    if schema_version == "1.0.0":
        audit.unsupported(
            "source.build_time_binding",
            "certificate 1.0.0 cannot bind analyzer bytes to source/build dependencies",
        )


def _verify_artifact_bytes(
    certificate: dict[str, Any],
    certificate_path: Path,
    analysis_directory: Path,
    path_roots: Sequence[Path],
    audit: Audit,
) -> tuple[dict[str, dict[str, Any]], dict[str, Path], dict[str, dict[str, Any]]]:
    raw_inputs = certificate.get("inputs")
    raw_outputs = certificate.get("outputs")
    if not isinstance(raw_inputs, list):
        audit.failed("artifacts.inputs", "certificate inputs are missing/not an array")
        raw_inputs = []
    if not isinstance(raw_outputs, list):
        audit.failed("artifacts.outputs", "certificate outputs are missing/not an array")
        raw_outputs = []

    input_by_kind = _unique_map(raw_inputs, "kind", audit, "artifacts.inputs")
    certificate_v2 = certificate.get("schema_version") == "2.0.0"
    observed_input_order = [
        item.get("kind") if isinstance(item, dict) else None for item in raw_inputs
    ]
    if certificate_v2 and tuple(observed_input_order) != CERTIFICATE_V2_INPUT_ORDER:
        audit.failed(
            "artifacts.inputs",
            f"certificate v2 input order differs: {observed_input_order}",
        )
    base_input_kinds = {"typed_property_ir", "compile_commands"}
    expected_input_kinds = (
        set(CERTIFICATE_V2_INPUT_ORDER)
        if certificate_v2
        else base_input_kinds
        | ({"source_inputs"} if "source_inputs" in input_by_kind else set())
    )
    if set(input_by_kind) != expected_input_kinds:
        audit.failed(
            "artifacts.inputs",
            f"expected exactly {sorted(expected_input_kinds)}, got {sorted(input_by_kind)}",
        )
    else:
        audit.passed("artifacts.inputs", "required input kinds are present exactly once")
    for kind, descriptor in input_by_kind.items():
        if not _is_nonempty_string(descriptor.get("artifact_id")):
            audit.failed("artifacts.inputs", f"{kind} has no artifact_id")
        if certificate_v2:
            expected_fields = (
                {"artifact_id", "kind", "sha256"}
                if kind == "source_inputs"
                else {"artifact_id", "kind", "sha256", "path"}
            )
            if set(descriptor) != expected_fields:
                audit.failed(
                    "artifacts.inputs",
                    f"{kind} has missing or unexpected descriptor fields",
                )

    input_paths: dict[str, Path] = {}
    for kind, descriptor in input_by_kind.items():
        if kind == "source_inputs":
            if not _is_sha256(descriptor.get("sha256")):
                audit.failed("artifacts.source_input_commitment", "source_inputs has invalid digest")
            if "path" in descriptor:
                audit.failed(
                    "artifacts.source_input_commitment",
                    "source_inputs is an aggregate commitment and must not masquerade as a byte path",
                )
            continue
        path, error = _resolve_and_verify_input(descriptor, certificate_path, path_roots)
        if error:
            audit.failed("artifacts.input_bytes", f"{kind}: {error}")
        else:
            assert path is not None
            input_paths[kind] = path
    if len(input_paths) == len(base_input_kinds):
        audit.passed("artifacts.input_bytes", "all declared input byte digests match")

    output_by_kind = _unique_map(raw_outputs, "kind", audit, "artifacts.outputs")
    observed_output_order = [
        item.get("kind") if isinstance(item, dict) else None for item in raw_outputs
    ]
    if certificate_v2 and tuple(observed_output_order) != CERTIFICATE_V2_OUTPUT_ORDER:
        audit.failed(
            "artifacts.outputs",
            f"certificate v2 output order differs: {observed_output_order}",
        )
    if set(output_by_kind) != set(OUTPUT_FILE_BY_KIND):
        audit.failed(
            "artifacts.outputs",
            f"expected exactly {sorted(OUTPUT_FILE_BY_KIND)}, got {sorted(output_by_kind)}",
        )
    else:
        audit.passed("artifacts.outputs", "four required output kinds are present exactly once")
    for kind, descriptor in output_by_kind.items():
        if not _is_nonempty_string(descriptor.get("artifact_id")):
            audit.failed("artifacts.outputs", f"{kind} has no artifact_id")
        if certificate_v2 and set(descriptor) != {
            "artifact_id",
            "kind",
            "sha256",
            "path",
        }:
            audit.failed(
                "artifacts.outputs",
                f"{kind} has missing or unexpected descriptor fields",
            )

    loaded_outputs: dict[str, dict[str, Any]] = {}
    for kind, filename in OUTPUT_FILE_BY_KIND.items():
        descriptor = output_by_kind.get(kind)
        if descriptor is None:
            continue
        expected_digest = descriptor.get("sha256")
        declared_path = descriptor.get("path")
        if not _is_sha256(expected_digest):
            audit.failed("artifacts.output_bytes", f"{kind} has invalid SHA-256")
            continue
        if not _is_nonempty_string(declared_path) or Path(declared_path).name != filename:
            audit.failed(
                "artifacts.output_paths",
                f"{kind} declared path must end in {filename}",
            )
        actual_path = analysis_directory / filename
        if not actual_path.is_file():
            audit.failed("artifacts.output_bytes", f"missing output file: {actual_path}")
            continue
        if actual_path.stat().st_size == 0:
            audit.failed("artifacts.output_bytes", f"empty output file: {actual_path}")
            continue
        try:
            actual_digest, _ = _rehash_regular_file(actual_path)
        except OSError as error:
            audit.failed("artifacts.output_bytes", f"{kind}: {error}")
            continue
        if actual_digest != expected_digest:
            audit.failed("artifacts.output_bytes", f"{kind} byte digest mismatch")
            continue
        try:
            loaded_outputs[kind] = _as_object(_load_json(actual_path), kind)
        except VerificationDataError as error:
            audit.failed("artifacts.output_json", str(error))
    if len(loaded_outputs) == len(OUTPUT_FILE_BY_KIND):
        audit.passed("artifacts.output_bytes", "all four output byte digests match")

    for kind, document in loaded_outputs.items():
        descriptor = output_by_kind[kind]
        if not _is_nonempty_string(document.get("artifact_id")) or (
            document.get("artifact_id") != descriptor.get("artifact_id")
        ):
            audit.failed(
                "artifacts.output_identity",
                f"{kind} artifact_id differs from certificate descriptor",
            )
    if loaded_outputs and not any(
        finding.check_id == "artifacts.output_identity" and finding.status == "FAIL"
        for finding in audit.findings
    ):
        audit.passed("artifacts.output_identity", "output artifact identities match descriptors")
    return input_by_kind, input_paths, loaded_outputs


def _verify_stage_topology(
    certificate: dict[str, Any],
    input_by_kind: Mapping[str, Mapping[str, Any]],
    output_by_kind: Mapping[str, Mapping[str, Any]],
    audit: Audit,
) -> dict[str, dict[str, Any]]:
    stages = certificate.get("stages")
    if not isinstance(stages, list):
        audit.failed("stages.topology", "stages are missing/not an array")
        return {}
    stage_by_name = _unique_map(stages, "name", audit, "stages.topology")
    observed_order = [item.get("name") for item in stages if isinstance(item, dict)]
    if tuple(observed_order) != STAGE_ORDER or set(stage_by_name) != set(STAGE_ORDER):
        audit.failed(
            "stages.topology",
            f"expected ordered stages {list(STAGE_ORDER)}, got {observed_order}",
        )
    else:
        audit.passed("stages.topology", "fixed five-stage topology is complete and ordered")

    stage_ids = [stage.get("stage_id") for stage in stage_by_name.values()]
    if not all(_is_nonempty_string(item) for item in stage_ids) or len(set(stage_ids)) != len(
        stage_ids
    ):
        audit.failed("stages.identity", "stage_id values are not unique")

    def digest(source: Mapping[str, Mapping[str, Any]], kind: str) -> str | None:
        value = source.get(kind, {}).get("sha256")
        return value if _is_sha256(value) else None

    compile_digest = digest(input_by_kind, "compile_commands")
    property_digest = digest(input_by_kind, "typed_property_ir")
    source_inputs_digest = digest(input_by_kind, "source_inputs")
    index_digest = digest(output_by_kind, "semantic_index")
    bindings_digest = digest(output_by_kind, "ap_bindings")
    graph_digest = digest(output_by_kind, "contextual_influence_graph")
    cones_digest = digest(output_by_kind, "ap_influence_cones")
    expected = {
        "index": (
            [compile_digest, source_inputs_digest]
            if source_inputs_digest is not None
            else [compile_digest],
            [index_digest],
        ),
        "bind": ([property_digest, index_digest], [bindings_digest]),
        "influence": ([index_digest, bindings_digest], [graph_digest]),
        "cone": ([bindings_digest, graph_digest], [cones_digest]),
        "certificate": (
            [index_digest, bindings_digest, graph_digest, cones_digest],
            [],
        ),
    }
    closure_ok = True
    for name in STAGE_ORDER:
        stage = stage_by_name.get(name)
        if stage is None:
            closure_ok = False
            continue
        if certificate.get("schema_version") == "2.0.0" and set(stage) != {
            "stage_id",
            "name",
            "status",
            "input_sha256",
            "output_sha256",
            "diagnostics",
        }:
            audit.failed(
                "stages.topology",
                f"{name} has missing or unexpected stage fields",
            )
            closure_ok = False
        inputs = stage.get("input_sha256")
        outputs = stage.get("output_sha256")
        if not isinstance(inputs, list) or not isinstance(outputs, list):
            audit.failed("stages.closure", f"{name} inputs/outputs are not arrays")
            closure_ok = False
            continue
        if any(value is None for value in expected[name][0] + expected[name][1]):
            audit.failed("stages.closure", f"{name} cannot close over missing artifact digest")
            closure_ok = False
            continue
        if inputs != expected[name][0] or outputs != expected[name][1]:
            audit.failed(
                "stages.closure",
                f"{name} digest closure/order differs from declared artifact graph",
            )
            closure_ok = False
        if name != "certificate" and not outputs:
            audit.failed("stages.nonempty_outputs", f"{name} stage has no output")
            closure_ok = False
        if name == "certificate" and outputs:
            audit.failed(
                "stages.nonempty_outputs",
                "certificate stage must not claim a recursive self-digest output",
            )
            closure_ok = False
        if _status_rank(stage.get("status")) is None:
            audit.failed("stages.status", f"{name} has invalid status")
            closure_ok = False
        if not isinstance(stage.get("diagnostics"), list):
            audit.failed("stages.topology", f"{name} diagnostics are not an array")
            closure_ok = False
    if closure_ok:
        audit.passed(
            "stages.closure",
            "each stage consumes exactly predecessor/input bytes and produces its declared artifact",
        )
    return stage_by_name


def _manifest_missing(audit: Audit, strict_provenance: bool, detail: str) -> None:
    if strict_provenance:
        audit.failed("source.input_manifest", detail)
    else:
        audit.unsupported("source.input_manifest", detail)


def _verify_semantic_input_manifest(
    index: Mapping[str, Any], audit: Audit, strict_provenance: bool
) -> None:
    if index.get("schema_version") != "2.0.0":
        _manifest_missing(
            audit,
            strict_provenance,
            "legacy semantic-index has no complete source input manifest",
        )
        return
    required = ("input_manifest_sha256", "input_files", "translation_units")
    missing = [name for name in required if name not in index]
    translation_units = index.get("translation_units")
    if isinstance(translation_units, list) and any(
        isinstance(unit, dict) and "input_file_ids" not in unit
        for unit in translation_units
    ):
        missing.append("translation_units[].input_file_ids")
    if missing:
        _manifest_missing(
            audit,
            strict_provenance,
            f"semantic-index v2 has no complete source input manifest: {sorted(set(missing))}",
        )
        return

    raw_files = index.get("input_files")
    if not isinstance(raw_files, list) or not isinstance(translation_units, list):
        audit.failed("source.input_manifest", "input_files/translation_units are not arrays")
        return
    identity_scheme = index.get("identity_scheme")
    manifest_digest = index.get("input_manifest_sha256")
    if not _is_nonempty_string(identity_scheme) or not _is_sha256(manifest_digest):
        audit.failed("source.input_manifest", "manifest identity/digest is malformed")
        return

    files = _unique_map(raw_files, "input_file_id", audit, "source.input_manifest")
    digest_by_logical_path: dict[str, str] = {}
    valid_files: list[dict[str, Any]] = []
    shape_ok = len(files) == len(raw_files)
    raw_roots = index.get("logical_root_ids")
    roots = (
        {item for item in raw_roots if _is_nonempty_string(item)}
        if isinstance(raw_roots, list)
        else set()
    )
    if not _unique_nonempty_strings(raw_roots):
        audit.failed("source.input_manifest", "logical_root_ids are malformed")
        shape_ok = False
    for file_id, item in files.items():
        logical_path = item.get("logical_path")
        content_digest = item.get("sha256")
        role = item.get("role")
        byte_size = item.get("byte_size")
        if (
            not _is_nonempty_string(logical_path)
            or not _is_sha256(content_digest)
            or role not in INPUT_ROLE_ORDER
            or not isinstance(byte_size, int)
            or isinstance(byte_size, bool)
            or byte_size < 0
        ):
            audit.failed("source.input_manifest", f"malformed input-file entry: {file_id}")
            shape_ok = False
            continue
        known_digest = digest_by_logical_path.setdefault(logical_path, content_digest)
        if known_digest != content_digest:
            audit.failed(
                "source.input_manifest",
                f"logical path maps to different content digests: {logical_path}",
            )
            shape_ok = False
        prefix = "riftpath://v1/"
        root_id = ""
        if not logical_path.startswith(prefix) or "/" not in logical_path[len(prefix) :]:
            audit.failed("source.input_manifest", f"non-logical input path: {logical_path}")
            shape_ok = False
        else:
            root_id = logical_path[len(prefix) :].split("/", 1)[0]
            if root_id != "toolchain" and root_id not in roots:
                audit.failed(
                    "source.input_manifest",
                    f"input path uses undeclared logical root {root_id}: {logical_path}",
                )
                shape_ok = False
        expected_id = input_file_id(identity_scheme, role, logical_path, content_digest)
        if file_id != expected_id:
            audit.failed(
                "source.input_manifest", f"input_file_id is not bound to path/content: {file_id}"
            )
            shape_ok = False
        if root_id == "toolchain" and content_digest not in logical_path:
            audit.failed(
                "source.input_manifest",
                f"toolchain logical path is not content-addressed: {logical_path}",
            )
            shape_ok = False
        valid_files.append(item)

    expected_order = sorted(
        valid_files,
        key=lambda item: (
            item["logical_path"],
            INPUT_ROLE_ORDER[item["role"]],
            item["sha256"],
            item["input_file_id"],
        ),
    )
    if valid_files != expected_order:
        audit.failed("source.input_manifest", "input_files are not in canonical order")
        shape_ok = False
    if shape_ok:
        actual_manifest = input_manifest_sha256(identity_scheme, valid_files)
        if actual_manifest != manifest_digest:
            audit.failed(
                "source.input_manifest",
                "input_manifest_sha256 does not aggregate logical paths/content digests",
            )
            shape_ok = False
        try:
            expected_artifact = semantic_index_artifact_id(index)
            if index.get("artifact_id") != expected_artifact:
                audit.failed(
                    "source.input_manifest",
                    "semantic-index artifact_id does not bind canonical DB, path map, and input manifest",
                )
                shape_ok = False
        except (KeyError, AttributeError, UnicodeEncodeError):
            audit.failed("source.input_manifest", "semantic-index identity inputs are malformed")
            shape_ok = False

    referenced: set[str] = set()
    tu_ok = True
    for index_number, raw_unit in enumerate(translation_units):
        if not isinstance(raw_unit, dict):
            audit.failed("source.input_manifest", f"translation unit {index_number} is malformed")
            tu_ok = False
            continue
        tu_id = raw_unit.get("tu_id")
        ids = raw_unit.get("input_file_ids")
        if not _is_nonempty_string(tu_id) or not _unique_nonempty_strings(ids) or not ids:
            audit.failed(
                "source.input_manifest", f"translation unit {tu_id!r} has malformed/empty input refs"
            )
            tu_ok = False
            continue
        if ids != sorted(ids):
            audit.failed(
                "source.input_manifest", f"translation unit {tu_id} input refs are not canonical"
            )
            tu_ok = False
        missing_ids = [file_id for file_id in ids if file_id not in files]
        if missing_ids:
            audit.failed(
                "source.input_manifest", f"translation unit {tu_id} references absent inputs: {missing_ids}"
            )
            tu_ok = False
        referenced.update(file_id for file_id in ids if file_id in files)
        main_matches = [
            file_id
            for file_id in ids
            if file_id in files
            and files[file_id].get("role") == "main"
            and files[file_id].get("logical_path") == raw_unit.get("source_file")
        ]
        if not main_matches:
            audit.failed(
                "source.input_manifest",
                f"translation unit {tu_id} does not reference a matching main file",
            )
            tu_ok = False
    orphaned = set(files) - referenced
    if orphaned:
        audit.failed(
            "source.input_manifest", f"manifest inputs are not referenced by any TU: {sorted(orphaned)}"
        )
        tu_ok = False
    if shape_ok and tu_ok:
        audit.passed(
            "source.input_manifest",
            f"{len(files)} logical content digests aggregate correctly and close over {len(translation_units)} TUs",
        )


def _summarize_errors(errors: Sequence[str], *, limit: int = 8) -> str:
    visible = list(errors[:limit])
    if len(errors) > limit:
        visible.append(f"... and {len(errors) - limit} more")
    return "; ".join(visible)


def _verify_ap_bindings(
    bindings: Mapping[str, Any],
    property_doc: Mapping[str, Any] | None,
    audit: Audit,
) -> None:
    """Audit both legacy flat bindings and v2 role-DNF group semantics."""
    version = bindings.get("schema_version")
    expected_policy: dict[str, Any]
    if version == "1.0.0":
        expected_policy = {
            "joint_role_binding": True,
            "similarity_is_confirmation": False,
        }
    elif version == "2.0.0":
        expected_policy = {
            "role_selector_logic": "role-dnf/1",
            "cross_role_consistency": "NOT_EVALUATED",
            "similarity_is_confirmation": False,
        }
    else:
        audit.failed("formats.bindings", f"unsupported ap-bindings schema {version!r}")
        return

    raw_policy = bindings.get("binding_policy")
    if not isinstance(raw_policy, dict) or raw_policy != expected_policy:
        audit.failed(
            "formats.bindings",
            f"ap-bindings {version} policy is not the closed compatibility contract",
        )
    else:
        audit.passed("formats.bindings", f"ap-bindings schema {version} policy is valid")

    raw_bindings = bindings.get("bindings")
    if not isinstance(raw_bindings, list):
        audit.failed("bindings.group_closure", "bindings is not an array")
        audit.failed("soundness.binding_resolution", "bindings is not an array")
        return
    binding_documents = [item for item in raw_bindings if isinstance(item, dict)]
    if len(binding_documents) != len(raw_bindings):
        audit.failed("bindings.group_closure", "bindings contains a non-object entry")

    property_version = property_doc.get("schema_version") if property_doc else None
    if property_doc is None:
        audit.failed(
            "bindings.group_closure",
            "typed Property IR is unavailable for independent binding closure",
        )
        return
    if property_version != version:
        audit.failed(
            "bindings.group_closure",
            f"ap-bindings schema {version} does not match Property IR {property_version!r}",
        )
        return

    candidate_statuses = {"CANDIDATE", "CONFIRMED", "REJECTED", "UNRESOLVED"}
    resolutions = (
        {"CONFIRMED", "AMBIGUOUS", "UNRESOLVED", "FAILED"}
        if version == "1.0.0"
        else {"CONFIRMED", "PARTIAL", "AMBIGUOUS", "UNRESOLVED", "FAILED"}
    )
    candidate_ids: set[str] = set()

    if version == "1.0.0":
        resolution_errors: list[str] = []
        candidate_errors: list[str] = []
        seen_roles: set[tuple[str, str]] = set()
        for binding in binding_documents:
            ap_id = binding.get("ap_id")
            role = binding.get("role")
            key = (ap_id, role)
            if not _is_nonempty_string(ap_id) or not _is_nonempty_string(role):
                candidate_errors.append("legacy binding lacks AP/role identity")
            elif key in seen_roles:
                candidate_errors.append(f"duplicate legacy AP-role binding {ap_id}/{role}")
            else:
                seen_roles.add(key)
            candidates = binding.get("candidates")
            if not isinstance(candidates, list):
                candidate_errors.append(f"{ap_id}/{role} candidates is not an array")
                continue
            confirmed = 0
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    candidate_errors.append(f"{ap_id}/{role} has a non-object candidate")
                    continue
                binding_id = candidate.get("binding_id")
                if not _is_nonempty_string(binding_id) or binding_id in candidate_ids:
                    candidate_errors.append(f"duplicate/malformed binding_id {binding_id!r}")
                else:
                    candidate_ids.add(binding_id)
                if "selector_group_id" in candidate:
                    candidate_errors.append(
                        f"legacy candidate {binding_id!r} contains selector_group_id"
                    )
                if candidate.get("status") not in candidate_statuses:
                    candidate_errors.append(f"candidate {binding_id!r} has invalid status")
                if candidate.get("status") == "CONFIRMED" and _unique_nonempty_strings(
                    candidate.get("semantic_node_refs")
                ):
                    confirmed += 1
            resolution = binding.get("resolution")
            if resolution not in resolutions:
                resolution_errors.append(f"{ap_id}/{role} has invalid resolution {resolution!r}")
            elif resolution == "CONFIRMED" and confirmed != 1:
                resolution_errors.append(
                    f"{ap_id}/{role} CONFIRMED requires exactly one confirmed semantic candidate"
                )
            elif resolution == "AMBIGUOUS" and len(candidates) < 2:
                resolution_errors.append(
                    f"{ap_id}/{role} AMBIGUOUS requires at least two candidates"
                )
        if candidate_errors:
            audit.failed("bindings.candidate_groups", _summarize_errors(candidate_errors))
        else:
            audit.passed(
                "bindings.candidate_groups",
                f"{len(candidate_ids)} legacy candidates preserve flat-selector provenance",
            )
        if resolution_errors:
            audit.failed(
                "soundness.binding_resolution", _summarize_errors(resolution_errors)
            )
        else:
            audit.passed(
                "soundness.binding_resolution",
                f"{len(binding_documents)} legacy AP-role resolutions are internally consistent",
            )
        return

    group_errors: list[str] = []
    candidate_errors = []
    resolution_errors = []
    raw_selectors = property_doc.get("selectors")
    selector_ids: set[str] = set()
    if not isinstance(raw_selectors, list):
        group_errors.append("Property IR v2 selectors is not an array")
    else:
        for selector in raw_selectors:
            selector_id = selector.get("selector_id") if isinstance(selector, dict) else None
            if not _is_nonempty_string(selector_id) or selector_id in selector_ids:
                group_errors.append(f"duplicate/malformed selector ID {selector_id!r}")
            else:
                selector_ids.add(selector_id)

    role_groups: dict[tuple[str, str], dict[str, frozenset[str]]] = defaultdict(dict)
    expected_roles: set[tuple[str, str]] = set()
    global_ids = set(selector_ids)
    raw_aps = property_doc.get("atomic_propositions")
    if not isinstance(raw_aps, list):
        group_errors.append("Property IR v2 atomic_propositions is not an array")
    else:
        for ap in raw_aps:
            if not isinstance(ap, dict):
                group_errors.append("Property IR v2 has a non-object AP")
                continue
            ap_id = ap.get("ap_id")
            raw_roles = ap.get("roles")
            roles = (
                {item for item in raw_roles if _is_nonempty_string(item)}
                if isinstance(raw_roles, list)
                else set()
            )
            if not _is_nonempty_string(ap_id) or ap_id in global_ids:
                group_errors.append(f"duplicate/malformed AP ID {ap_id!r}")
                continue
            global_ids.add(ap_id)
            if not _unique_nonempty_strings(raw_roles) or not roles:
                group_errors.append(f"{ap_id} has malformed/empty roles")
            expected_roles.update((ap_id, role) for role in roles)
            raw_groups = ap.get("role_selector_groups")
            if not isinstance(raw_groups, list) or not raw_groups:
                group_errors.append(f"{ap_id} has no role selector groups")
                continue
            for group in raw_groups:
                if not isinstance(group, dict):
                    group_errors.append(f"{ap_id} contains a non-object selector group")
                    continue
                group_id = group.get("group_id")
                role = group.get("role")
                all_of = group.get("all_of")
                if not _is_nonempty_string(group_id) or group_id in global_ids:
                    group_errors.append(f"duplicate/malformed selector group ID {group_id!r}")
                    continue
                global_ids.add(group_id)
                if role not in roles:
                    group_errors.append(f"{group_id} uses undeclared role {role!r}")
                    continue
                if not _unique_nonempty_strings(all_of) or not all_of:
                    group_errors.append(f"{group_id} has malformed/empty all_of")
                    continue
                unknown = sorted(set(all_of) - selector_ids)
                if unknown:
                    group_errors.append(f"{group_id} references unknown selectors {unknown}")
                role_groups[(ap_id, role)][group_id] = frozenset(all_of)
            for role in roles:
                if not role_groups.get((ap_id, role)):
                    group_errors.append(f"{ap_id}/{role} has no selector group")

    bindings_by_role: dict[tuple[str, str], Mapping[str, Any]] = {}
    accounted_by_role: dict[tuple[str, str], set[str]] = defaultdict(set)
    counts_by_role: dict[
        tuple[str, str], dict[str, Counter[str]]
    ] = defaultdict(lambda: defaultdict(Counter))
    for binding in binding_documents:
        ap_id = binding.get("ap_id")
        role = binding.get("role")
        key = (ap_id, role)
        if not _is_nonempty_string(ap_id) or not _is_nonempty_string(role):
            group_errors.append("binding lacks AP/role identity")
            continue
        if key in bindings_by_role:
            group_errors.append(f"duplicate AP-role binding {ap_id}/{role}")
        else:
            bindings_by_role[key] = binding
        candidates = binding.get("candidates")
        if not isinstance(candidates, list):
            candidate_errors.append(f"{ap_id}/{role} candidates is not an array")
            continue
        known_groups = role_groups.get(key, {})
        for candidate in candidates:
            if not isinstance(candidate, dict):
                candidate_errors.append(f"{ap_id}/{role} has a non-object candidate")
                continue
            binding_id = candidate.get("binding_id")
            if not _is_nonempty_string(binding_id) or binding_id in candidate_ids:
                candidate_errors.append(f"duplicate/malformed binding_id {binding_id!r}")
            else:
                candidate_ids.add(binding_id)
            group_id = candidate.get("selector_group_id")
            if not _is_nonempty_string(group_id) or group_id not in known_groups:
                candidate_errors.append(
                    f"candidate {binding_id!r} references unknown selector group {group_id!r}"
                )
                continue
            accounted_by_role[key].add(group_id)
            selector_refs = candidate.get("selector_refs")
            if not _unique_nonempty_strings(selector_refs) or frozenset(selector_refs) != known_groups[
                group_id
            ]:
                candidate_errors.append(
                    f"candidate {binding_id!r} selector_refs do not equal {group_id}.all_of"
                )
            status = candidate.get("status")
            if status not in candidate_statuses:
                candidate_errors.append(f"candidate {binding_id!r} has invalid status {status!r}")
                continue
            counts_by_role[key][group_id][status] += 1
            if status == "CONFIRMED" and not _unique_nonempty_strings(
                candidate.get("semantic_node_refs")
            ):
                candidate_errors.append(
                    f"confirmed candidate {binding_id!r} has no semantic nodes"
                )

    observed_roles = set(bindings_by_role)
    if observed_roles != expected_roles:
        missing = sorted(expected_roles - observed_roles)
        extra = sorted(observed_roles - expected_roles)
        group_errors.append(f"AP-role binding closure differs; missing={missing}, extra={extra}")
    for key, groups in role_groups.items():
        accounted = accounted_by_role.get(key, set())
        if accounted != set(groups):
            group_errors.append(
                f"{key[0]}/{key[1]} group accounting differs; "
                f"missing={sorted(set(groups) - accounted)}, extra={sorted(accounted - set(groups))}"
            )

    for key, binding in bindings_by_role.items():
        resolution = binding.get("resolution")
        if resolution not in resolutions:
            resolution_errors.append(
                f"{key[0]}/{key[1]} has invalid resolution {resolution!r}"
            )
            continue
        groups = role_groups.get(key, {})
        exact_groups = 0
        ambiguous_group = False
        malformed_group = False
        for group_id in groups:
            counts = counts_by_role[key][group_id]
            confirmed = counts["CONFIRMED"]
            candidates = counts["CANDIDATE"]
            if confirmed == 1 and candidates == 0:
                exact_groups += 1
            elif confirmed > 1 or (confirmed > 0 and candidates > 0) or candidates == 1:
                malformed_group = True
            elif candidates > 1:
                ambiguous_group = True
        if malformed_group:
            resolution_errors.append(
                f"{key[0]}/{key[1]} has an invalid confirmed/candidate group combination"
            )
            continue
        if groups and exact_groups == len(groups):
            expected_resolution = "CONFIRMED"
        elif exact_groups > 0:
            expected_resolution = "PARTIAL"
        elif ambiguous_group:
            expected_resolution = "AMBIGUOUS"
        else:
            expected_resolution = "UNRESOLVED"
        if resolution != expected_resolution:
            resolution_errors.append(
                f"{key[0]}/{key[1]} claims {resolution!r}, expected {expected_resolution}"
            )

    if group_errors:
        audit.failed("bindings.group_closure", _summarize_errors(group_errors))
    else:
        audit.passed(
            "bindings.group_closure",
            f"{len(expected_roles)} AP roles close over {sum(map(len, role_groups.values()))} role-DNF groups",
        )
    if candidate_errors:
        audit.failed("bindings.candidate_groups", _summarize_errors(candidate_errors))
    else:
        audit.passed(
            "bindings.candidate_groups",
            f"{len(candidate_ids)} candidates bind exact selector_group_id/all_of provenance",
        )
    if resolution_errors:
        audit.failed("soundness.binding_resolution", _summarize_errors(resolution_errors))
    else:
        audit.passed(
            "soundness.binding_resolution",
            f"{len(bindings_by_role)} role-DNF resolutions agree with per-group accounting",
        )


def _verify_formats_and_references(
    input_by_kind: Mapping[str, Mapping[str, Any]],
    inputs: Mapping[str, Path],
    outputs: Mapping[str, dict[str, Any]],
    audit: Audit,
    strict_provenance: bool,
) -> None:
    if set(outputs) != set(OUTPUT_FILE_BY_KIND):
        return
    index = outputs["semantic_index"]
    bindings = outputs["ap_bindings"]
    graph = outputs["contextual_influence_graph"]
    cones = outputs["ap_influence_cones"]

    semantic_version = index.get("schema_version")
    graph_version = graph.get("schema_version")
    if semantic_version not in {"1.0.0", "2.0.0"}:
        audit.failed("formats.semantic_index", f"unsupported semantic index {semantic_version!r}")
    elif semantic_version == "1.0.0":
        audit.unsupported(
            "formats.semantic_index_losslessness",
            "semantic-index 1.0.0 omitted analysis-critical facts; byte integrity is checked but replay is not provable",
        )
    else:
        required = (
            "identity_scheme",
            "canonical_compilation_database_sha256",
            "path_map_sha256",
            "logical_root_ids",
            "abstract_objects",
            "function_summaries",
            "callsites",
        )
        missing = [name for name in required if name not in index]
        if missing:
            audit.failed("formats.semantic_index", f"v2 fields missing: {missing}")
        else:
            audit.passed("formats.semantic_index", "semantic-index v2 lossless fields detected")
    _verify_semantic_input_manifest(index, audit, strict_provenance)

    if graph_version not in {"1.0.0", "2.0.0"}:
        audit.failed("formats.contextual_graph", f"unsupported graph {graph_version!r}")
    elif graph_version == "1.0.0":
        audit.unsupported(
            "formats.contextual_graph_losslessness",
            "contextual graph 1.0.0 lacks canonical semantic/condition references",
        )
    else:
        missing_node_ref = any(
            not isinstance(node, dict) or not _is_nonempty_string(node.get("semantic_node_ref"))
            for node in graph.get("nodes", [])
        )
        missing_conditions = any(
            not isinstance(edge, dict) or not isinstance(edge.get("condition_node_ids"), list)
            for edge in graph.get("edges", [])
        )
        if missing_node_ref or missing_conditions:
            audit.failed(
                "formats.contextual_graph",
                "v2 graph omits semantic_node_ref or condition_node_ids",
            )
        else:
            audit.passed("formats.contextual_graph", "contextual-graph v2 canonical fields detected")

    if cones.get("schema_version") != "1.0.0":
        audit.failed("formats.cones", "unsupported influence-cones schema")

    property_descriptor = input_by_kind.get("typed_property_ir", {})
    compile_descriptor = input_by_kind.get("compile_commands", {})
    expected = {
        "bindings.property_ir_sha256": (
            bindings.get("property_ir_sha256"),
            property_descriptor.get("sha256"),
        ),
    }
    if semantic_version == "1.0.0" or "compilation_database_sha256" in index:
        expected["semantic_index.compilation_database_sha256"] = (
            index.get("compilation_database_sha256"),
            compile_descriptor.get("sha256"),
        )
    # Remaining expectations are filled by the caller through descriptor hashes
    # stored in the documents themselves and checked in _verify_internal_chain.
    for label, (actual, wanted) in expected.items():
        if actual != wanted:
            audit.failed("artifacts.internal_chain", f"{label} does not match input bytes")

    property_doc: dict[str, Any] | None = None
    if inputs.get("typed_property_ir"):
        try:
            property_doc = _as_object(_load_json(inputs["typed_property_ir"]), "property IR")
            if property_doc.get("artifact_id") != property_descriptor.get("artifact_id"):
                audit.failed(
                    "artifacts.input_identity",
                    "property IR artifact_id differs from certificate descriptor",
                )
            else:
                audit.passed("artifacts.input_identity", "property IR identity matches certificate")
        except VerificationDataError as error:
            audit.failed("artifacts.input_identity", str(error))
    _verify_ap_bindings(bindings, property_doc, audit)


def _verify_internal_chain(
    input_by_kind: Mapping[str, Mapping[str, Any]],
    output_by_kind: Mapping[str, Mapping[str, Any]],
    outputs: Mapping[str, dict[str, Any]],
    audit: Audit,
) -> None:
    if set(outputs) != set(OUTPUT_FILE_BY_KIND):
        return
    index = outputs["semantic_index"]
    bindings = outputs["ap_bindings"]
    graph = outputs["contextual_influence_graph"]
    cones = outputs["ap_influence_cones"]
    expectations = {
        "ap_bindings.property_ir_sha256": (
            bindings.get("property_ir_sha256"),
            input_by_kind.get("typed_property_ir", {}).get("sha256"),
        ),
        "ap_bindings.semantic_index_sha256": (
            bindings.get("semantic_index_sha256"),
            output_by_kind.get("semantic_index", {}).get("sha256"),
        ),
        "graph.semantic_index_sha256": (
            graph.get("semantic_index_sha256"),
            output_by_kind.get("semantic_index", {}).get("sha256"),
        ),
        "cones.ap_bindings_sha256": (
            cones.get("ap_bindings_sha256"),
            output_by_kind.get("ap_bindings", {}).get("sha256"),
        ),
        "cones.graph_sha256": (
            cones.get("graph_sha256"),
            output_by_kind.get("contextual_influence_graph", {}).get("sha256"),
        ),
    }
    if index.get("schema_version") == "1.0.0" or "compilation_database_sha256" in index:
        expectations["semantic_index.compilation_database_sha256"] = (
            index.get("compilation_database_sha256"),
            input_by_kind.get("compile_commands", {}).get("sha256"),
        )
    failures = [label for label, pair in expectations.items() if pair[0] != pair[1]]
    if failures:
        audit.failed("artifacts.internal_chain", f"digest references disagree: {failures}")
    else:
        audit.passed("artifacts.internal_chain", "all embedded input/output digest references close")


def _verify_certificate_source_commitment(
    certificate: Mapping[str, Any],
    input_by_kind: Mapping[str, Mapping[str, Any]],
    outputs: Mapping[str, dict[str, Any]],
    audit: Audit,
    strict_provenance: bool,
) -> None:
    index = outputs.get("semantic_index")
    if not isinstance(index, dict) or index.get("schema_version") != "2.0.0":
        return
    manifest_digest = index.get("input_manifest_sha256")
    if not _is_sha256(manifest_digest):
        return
    source_descriptor = input_by_kind.get("source_inputs")
    if source_descriptor is None:
        _manifest_missing(
            audit,
            strict_provenance,
            "certificate inputs do not bind semantic-index input_manifest_sha256",
        )
        return
    expected_source_id = stable_id("input_manifest", manifest_digest)
    if source_descriptor.get("sha256") != manifest_digest or (
        source_descriptor.get("artifact_id") != expected_source_id
    ):
        audit.failed(
            "source.certificate_commitment",
            "source_inputs descriptor does not bind the semantic-index manifest",
        )
        return
    property_digest = input_by_kind.get("typed_property_ir", {}).get("sha256")
    canonical_db = index.get("canonical_compilation_database_sha256")
    path_map = index.get("path_map_sha256")
    if not all(_is_sha256(item) for item in (property_digest, canonical_db, path_map)):
        audit.failed(
            "source.certificate_commitment",
            "analysis identity inputs are missing or malformed",
        )
        return
    values = [property_digest, manifest_digest, canonical_db, path_map]
    material: str | bytes = (
        length_prefixed_material(values)
        if certificate.get("schema_version") == "2.0.0"
        else ":".join(values)
    )
    expected_analysis_id = stable_id("analysis", material)
    if certificate.get("analysis_id") != expected_analysis_id:
        audit.failed(
            "source.certificate_commitment",
            "analysis_id does not bind property, source manifest, canonical DB, and path map",
        )
        return
    audit.passed(
        "source.certificate_commitment",
        "certificate source_inputs and analysis_id bind the verified source manifest",
    )


def _verify_certificate_id(
    certificate: Mapping[str, Any],
    output_by_kind: Mapping[str, Mapping[str, Any]],
    audit: Audit,
) -> None:
    if certificate.get("schema_version") != "2.0.0":
        audit.unsupported(
            "certificate.identity_v2", "certificate v1 identity did not bind all output bytes"
        )
        return
    analyzer = certificate.get("analyzer")
    if not isinstance(analyzer, dict) or set(output_by_kind) != set(OUTPUT_FILE_BY_KIND):
        return
    values = [
        certificate.get("analysis_id"),
        analyzer.get("configuration_sha256"),
        *[output_by_kind[kind].get("sha256") for kind in OUTPUT_FILE_BY_KIND],
    ]
    if not all(_is_nonempty_string(value) for value in values):
        audit.failed("certificate.identity_v2", "certificate identity inputs are malformed")
        return
    expected = stable_id("certificate", length_prefixed_material(values))
    if certificate.get("certificate_id") != expected:
        audit.failed(
            "certificate.identity_v2",
            "certificate_id does not bind analysis, configuration, and four outputs",
        )
    else:
        audit.passed(
            "certificate.identity_v2",
            "certificate_id binds analysis, configuration, and four output digests",
        )


def _verify_source_input_provenance(
    certificate: Mapping[str, Any],
    input_by_kind: Mapping[str, Mapping[str, Any]],
    outputs: Mapping[str, dict[str, Any]],
    audit: Audit,
    strict_provenance: bool,
) -> None:
    if certificate.get("schema_version") != "2.0.0":
        audit.unsupported(
            "source.physical_provenance",
            "certificate v1 has no source_input_provenance paths",
        )
        return
    index = outputs.get("semantic_index")
    provenance = certificate.get("source_input_provenance")
    if not isinstance(index, dict) or not isinstance(provenance, dict):
        audit.failed("source.physical_provenance", "index/provenance object is missing")
        return
    if set(provenance) != {"manifest_sha256", "files"}:
        audit.failed(
            "source.physical_provenance",
            "source provenance has missing or unexpected fields",
        )
        return
    raw_files = provenance.get("files")
    index_files = index.get("input_files")
    if not isinstance(raw_files, list) or not raw_files or not isinstance(index_files, list):
        audit.failed("source.physical_provenance", "source provenance files are missing")
        return
    manifest = index.get("input_manifest_sha256")
    if provenance.get("manifest_sha256") != manifest or input_by_kind.get(
        "source_inputs", {}
    ).get("sha256") != manifest:
        audit.failed("source.physical_provenance", "source manifest commitments differ")
        return
    projected: list[dict[str, Any]] = []
    physical_count = 0
    shape_ok = True
    seen_paths: dict[str, tuple[Any, Any]] = {}
    for position, item in enumerate(raw_files):
        if not isinstance(item, dict):
            audit.failed("source.physical_provenance", f"file {position} is malformed")
            shape_ok = False
            continue
        if set(item) != {
            "input_file_id",
            "logical_path",
            "role",
            "sha256",
            "byte_size",
            "observed_paths",
        }:
            audit.failed(
                "source.physical_provenance",
                f"file {position} has missing or unexpected fields",
            )
            shape_ok = False
        projection = {
            key: item.get(key)
            for key in ("input_file_id", "logical_path", "sha256", "role", "byte_size")
        }
        projected.append(projection)
        observed = item.get("observed_paths")
        if not _unique_nonempty_strings(observed):
            if observed != []:
                audit.failed(
                    "source.physical_provenance",
                    f"observed paths malformed: {item.get('input_file_id')}",
                )
                shape_ok = False
                continue
        elif observed != sorted(observed):
            audit.failed(
                "source.physical_provenance",
                f"observed paths are not canonical: {item.get('input_file_id')}",
            )
            shape_ok = False
        predefines = item.get("role") == "toolchain" and str(
            item.get("logical_path", "")
        ).startswith("riftpath://v1/toolchain/predefines/")
        if not observed and not predefines:
            audit.failed(
                "source.physical_provenance",
                f"file-backed input has no observed path: {item.get('input_file_id')}",
            )
            shape_ok = False
            continue
        for path_text in observed:
            commitment = (item.get("sha256"), item.get("byte_size"))
            if not Path(path_text).is_absolute():
                audit.failed(
                    "source.physical_provenance", f"non-absolute observed path: {path_text}"
                )
                shape_ok = False
                continue
            prior = seen_paths.setdefault(path_text, commitment)
            if prior != commitment:
                audit.failed(
                    "source.physical_provenance",
                    f"one observed path has conflicting byte commitments: {path_text}",
                )
                shape_ok = False
                continue
            try:
                digest, byte_size = _rehash_regular_file(Path(path_text))
            except OSError as error:
                audit.failed(
                    "source.physical_provenance", f"cannot rehash {path_text}: {error}"
                )
                shape_ok = False
                continue
            if digest != item.get("sha256") or byte_size != item.get("byte_size"):
                audit.failed(
                    "source.physical_provenance", f"source bytes changed: {path_text}"
                )
                shape_ok = False
            physical_count += 1
    if projected != index_files:
        audit.failed(
            "source.physical_provenance",
            "certificate provenance is not the exact ordered projection of semantic-index inputs",
        )
        shape_ok = False
    if shape_ok:
        audit.passed(
            "source.physical_provenance",
            f"rehash verified {physical_count} physical paths; only content-addressed predefines are pathless",
        )


def _validate_gaps(raw: Any, label: str, audit: Audit) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list):
        audit.failed("soundness.gap_shape", f"{label} unsupported_constructs is not an array")
        return {}
    gaps = _unique_map(raw, "construct_id", audit, "soundness.gap_shape")
    for gap_id, gap in gaps.items():
        if gap.get("effect") not in {"precision_loss", "soundness_risk", "stage_failure"}:
            audit.failed("soundness.gap_shape", f"{label}:{gap_id} has invalid effect")
        if not _is_nonempty_string(gap.get("kind")) or not _is_nonempty_string(
            gap.get("detail")
        ):
            audit.failed("soundness.gap_shape", f"{label}:{gap_id} lacks kind/detail")
    return gaps


def _verify_status_and_gaps(
    certificate: dict[str, Any],
    stages: Mapping[str, Mapping[str, Any]],
    outputs: Mapping[str, dict[str, Any]],
    audit: Audit,
) -> None:
    if set(outputs) != set(OUTPUT_FILE_BY_KIND) or set(stages) != set(STAGE_ORDER):
        return
    index = outputs["semantic_index"]
    bindings = outputs["ap_bindings"]
    graph = outputs["contextual_influence_graph"]
    cones = outputs["ap_influence_cones"]

    artifact_gaps: dict[str, dict[str, dict[str, Any]]] = {}
    for name, document in (
        ("index", index),
        ("bind", bindings),
        ("influence", graph),
        ("cone", cones),
    ):
        artifact_gaps[name] = _validate_gaps(
            document.get("unsupported_constructs"), name, audit
        )
    certificate_gaps = _validate_gaps(
        certificate.get("unsupported_constructs"), "certificate", audit
    )
    union: dict[str, dict[str, Any]] = {}
    inconsistent: list[str] = []
    for gaps in artifact_gaps.values():
        for gap_id, gap in gaps.items():
            if gap_id in union and union[gap_id] != gap:
                inconsistent.append(gap_id)
            union[gap_id] = gap
    if inconsistent:
        audit.failed("soundness.gap_closure", f"gap definitions disagree: {inconsistent}")
    if set(union) != set(certificate_gaps):
        audit.failed(
            "soundness.gap_closure",
            "certificate unsupported_constructs is not the exact union of output gaps",
        )
    else:
        mismatched = [gap_id for gap_id in union if union[gap_id] != certificate_gaps[gap_id]]
        if mismatched:
            audit.failed("soundness.gap_closure", f"certificate gap bodies differ: {mismatched}")
        else:
            audit.passed("soundness.gap_closure", "certificate gaps exactly close over outputs")

    lower: dict[str, str] = {
        name: _gap_lower_bound(list(gaps.values())) for name, gaps in artifact_gaps.items()
    }
    index_status = index.get("status")
    if _status_rank(index_status) is None:
        if index.get("schema_version") == "1.0.0" and index_status is None:
            audit.unsupported(
                "formats.semantic_index_stage_status",
                "legacy semantic-index 1.0.0 omitted top-level stage status; certificate stage and gaps were audited instead",
            )
        else:
            audit.failed("soundness.status", "semantic index has invalid status")
            lower["index"] = "FAILED"
    else:
        if stages["index"].get("status") != index_status:
            audit.failed("soundness.status", "index stage status differs from semantic index")
        lower["index"] = _worst_status((lower["index"], index_status))

    if _status_rank(graph.get("status")) is None:
        audit.failed("soundness.status", "contextual graph has invalid status")
    elif stages["influence"].get("status") != graph.get("status"):
        audit.failed("soundness.status", "influence stage status differs from graph")
    if _status_rank(graph.get("status")) is None:
        lower["influence"] = "FAILED"
    else:
        lower["influence"] = _worst_status((lower["influence"], graph["status"]))

    raw_bindings = bindings.get("bindings")
    binding_documents = (
        [item for item in raw_bindings if isinstance(item, dict)]
        if isinstance(raw_bindings, list)
        else []
    )
    resolutions = [item.get("resolution") for item in binding_documents]
    if not resolutions:
        lower["bind"] = "FAILED"
    elif any(value == "FAILED" for value in resolutions):
        lower["bind"] = "FAILED"
    elif any(value in {"PARTIAL", "AMBIGUOUS", "UNRESOLVED"} for value in resolutions):
        lower["bind"] = _worst_status((lower["bind"], "CONSERVATIVE_INCOMPLETE"))
    elif any(value != "CONFIRMED" for value in resolutions):
        lower["bind"] = "FAILED"
    for binding in binding_documents:
        candidates = binding.get("candidates")
        if not isinstance(candidates, list):
            audit.failed("soundness.binding_resolution", "binding candidates are malformed")
            lower["bind"] = "FAILED"
            continue
        confirmed = [
            candidate
            for candidate in candidates
            if isinstance(candidate, dict)
            and candidate.get("status") == "CONFIRMED"
            and _unique_nonempty_strings(candidate.get("semantic_node_refs"))
        ]
        resolution = binding.get("resolution")
        if resolution == "CONFIRMED" and not confirmed:
            audit.failed(
                "soundness.binding_resolution",
                "CONFIRMED binding has no confirmed candidate with semantic nodes",
            )
            lower["bind"] = "FAILED"
        if resolution == "AMBIGUOUS" and len(candidates) < 2:
            audit.failed(
                "soundness.binding_resolution", "AMBIGUOUS binding has fewer than two candidates"
            )
            lower["bind"] = "FAILED"

    cone_documents = [item for item in cones.get("cones", []) if isinstance(item, dict)]
    if not cone_documents:
        lower["cone"] = "FAILED"
    else:
        cone_statuses = [item.get("status") for item in cone_documents]
        if any(_status_rank(value) is None for value in cone_statuses):
            audit.failed("soundness.status", "cone has invalid status")
            lower["cone"] = "FAILED"
        else:
            lower["cone"] = _worst_status((lower["cone"], *cone_statuses))
        if any(
            account.get("disposition") == "UNRESOLVED"
            for cone in cone_documents
            for account in (
                cone.get("candidate_accounting")
                if isinstance(cone.get("candidate_accounting"), list)
                else []
            )
            if isinstance(account, dict)
        ):
            lower["cone"] = _worst_status((lower["cone"], "CONSERVATIVE_INCOMPLETE"))

    status_ok = True
    for name in ("index", "bind", "influence", "cone"):
        stage_status = stages[name].get("status")
        if _status_rank(stage_status) is None:
            status_ok = False
            continue
        if STATUSES[stage_status] < STATUSES[lower[name]]:
            audit.failed(
                "soundness.status",
                f"{name} claims {stage_status} but evidence requires at least {lower[name]}",
            )
            status_ok = False
    aggregate = _worst_status(stages[name].get("status", "FAILED") for name in STAGE_ORDER[:-1])
    if stages["certificate"].get("status") != aggregate:
        audit.failed("soundness.aggregate", "certificate stage is not worst predecessor status")
        status_ok = False
    if certificate.get("status") != aggregate:
        audit.failed("soundness.aggregate", "top-level status is not worst stage status")
        status_ok = False
    gap_lower = _gap_lower_bound(list(certificate_gaps.values()))
    if _status_rank(certificate.get("status")) is not None and (
        STATUSES[certificate["status"]] < STATUSES[gap_lower]
    ):
        audit.failed(
            "soundness.aggregate",
            f"top-level status overclaims certificate gaps ({gap_lower} required)",
        )
        status_ok = False
    if status_ok:
        audit.passed("soundness.status", "stage, artifact, gap, and aggregate statuses are conservative")


_PATH_CLASS_BITS = {
    "MUST_INFLUENCE": 1 << 0,
    "MAY_INFLUENCE": 1 << 1,
    "MODELLED_INFLUENCE": 1 << 2,
    "UNKNOWN_INFLUENCE": 1 << 3,
}
_EDGE_PATH_CLASS = {
    "must": "MUST_INFLUENCE",
    "may": "MAY_INFLUENCE",
    "modelled": "MODELLED_INFLUENCE",
    "unknown": "UNKNOWN_INFLUENCE",
}


def _compose_path_class(downstream: str, certainty: str) -> str:
    current = _EDGE_PATH_CLASS[certainty]
    if downstream == "UNKNOWN_INFLUENCE" or current == "UNKNOWN_INFLUENCE":
        return "UNKNOWN_INFLUENCE"
    if downstream == "MODELLED_INFLUENCE" or current == "MODELLED_INFLUENCE":
        return "MODELLED_INFLUENCE"
    if downstream == "MAY_INFLUENCE" or current == "MAY_INFLUENCE":
        return "MAY_INFLUENCE"
    return "MUST_INFLUENCE"


def _compose_path_mask(downstream_mask: int, certainty: str) -> int:
    result = 0
    for membership, bit in _PATH_CLASS_BITS.items():
        if downstream_mask & bit:
            result |= _PATH_CLASS_BITS[_compose_path_class(membership, certainty)]
    return result


def _summarize_path_mask(mask: int) -> str:
    has_must = bool(mask & _PATH_CLASS_BITS["MUST_INFLUENCE"])
    has_may = bool(mask & _PATH_CLASS_BITS["MAY_INFLUENCE"])
    has_modelled = bool(mask & _PATH_CLASS_BITS["MODELLED_INFLUENCE"])
    has_unknown = bool(mask & _PATH_CLASS_BITS["UNKNOWN_INFLUENCE"])
    if has_may or (has_must and (has_modelled or has_unknown)):
        return "MAY_INFLUENCE"
    if has_must:
        return "MUST_INFLUENCE"
    if has_modelled:
        return "MODELLED_INFLUENCE"
    return "UNKNOWN_INFLUENCE"


def _compute_path_membership_masks(
    roots: Iterable[str],
    root_membership: str,
    incoming: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, int]:
    """Recompute the production four-class backwards fixed point."""
    root_set = set(roots)
    masks = {root: _PATH_CLASS_BITS[root_membership] for root in sorted(root_set)}
    worklist: deque[str] = deque(sorted(root_set))
    while worklist:
        target = worklist.popleft()
        for edge in incoming.get(target, ()):
            source = edge["source_node_id"]
            if source in root_set:
                # Roots are fixed observation points; cycles cannot weaken them.
                continue
            candidate = _compose_path_mask(masks[target], edge["certainty"])
            current = masks.get(source, 0)
            merged = current | candidate
            if merged != current:
                masks[source] = merged
                worklist.append(source)
    return masks


def _empty_binding_candidate_id(ap_id: str, role: str) -> str:
    return stable_id("binding", ap_id + "\0" + role + "\0empty")


def _verify_graph_and_cones(outputs: Mapping[str, dict[str, Any]], audit: Audit) -> None:
    if "contextual_influence_graph" not in outputs or "ap_influence_cones" not in outputs:
        return
    graph = outputs["contextual_influence_graph"]
    cones_doc = outputs["ap_influence_cones"]
    bindings_doc = outputs.get("ap_bindings", {})
    raw_nodes = graph.get("nodes")
    raw_edges = graph.get("edges")
    raw_cones = cones_doc.get("cones")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        audit.failed("graph.shape", "graph nodes/edges are not arrays")
        return
    if not isinstance(raw_cones, list):
        audit.failed("cones.shape", "cones is not an array")
        return
    nodes = _unique_map(raw_nodes, "node_id", audit, "graph.identity")
    edges = _unique_map(raw_edges, "edge_id", audit, "graph.identity")
    endpoint_ok = True
    for edge_id, edge in edges.items():
        source_node_id = edge.get("source_node_id")
        target_node_id = edge.get("target_node_id")
        if (
            not _is_nonempty_string(source_node_id)
            or not _is_nonempty_string(target_node_id)
            or source_node_id not in nodes
            or target_node_id not in nodes
        ):
            audit.failed("graph.endpoints", f"{edge_id} references absent endpoint")
            endpoint_ok = False
        if graph.get("schema_version") == "2.0.0":
            conditions = edge.get("condition_node_ids")
            if not _unique_nonempty_strings(conditions) or any(
                item not in nodes for item in conditions
            ):
                audit.failed("graph.conditions", f"{edge_id} has absent/invalid condition node")
                endpoint_ok = False
    if endpoint_ok:
        audit.passed("graph.endpoints", "all graph endpoints and available v2 conditions exist")

    candidates_by_ap: dict[str, set[str]] = defaultdict(set)
    bindings_by_ap: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    bindings = bindings_doc.get("bindings", [])
    if isinstance(bindings, list):
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            ap_id = binding.get("ap_id")
            role = binding.get("role")
            if not _is_nonempty_string(ap_id) or not _is_nonempty_string(role):
                continue
            bindings_by_ap[ap_id].append(binding)
            candidates = binding.get("candidates")
            candidate_documents = candidates if isinstance(candidates, list) else []
            for candidate in candidate_documents:
                if isinstance(candidate, dict) and _is_nonempty_string(candidate.get("binding_id")):
                    candidates_by_ap[ap_id].add(candidate["binding_id"])
            if isinstance(candidates, list) and not candidates:
                candidates_by_ap[ap_id].add(_empty_binding_candidate_id(ap_id, role))

    fixed_point_edges_ok = True
    incoming_edges: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for edge_id, edge in edges.items():
        certainty = edge.get("certainty")
        if certainty not in _EDGE_PATH_CLASS:
            audit.failed(
                "cones.membership_fixed_point",
                f"{edge_id} has invalid path certainty {certainty!r}",
            )
            fixed_point_edges_ok = False
            continue
        if edge.get("source_node_id") in nodes and edge.get("target_node_id") in nodes:
            incoming_edges[edge["target_node_id"]].append(edge)
    for target in incoming_edges:
        incoming_edges[target].sort(key=lambda item: item.get("edge_id", ""))

    cones = _unique_map(raw_cones, "cone_id", audit, "cones.identity")
    all_ok = True
    for cone_id, cone in cones.items():
        cone_ap_id = cone.get("ap_id")
        if not _is_nonempty_string(cone_ap_id):
            audit.failed("cones.shape", f"{cone_id} has no non-empty ap_id")
            all_ok = False
            continue
        raw_members = cone.get("members")
        raw_accounts = cone.get("candidate_accounting")
        raw_edge_ids = cone.get("edge_ids")
        roles = cone.get("roles")
        if not all(isinstance(value, list) for value in (raw_members, raw_accounts, raw_edge_ids, roles)):
            audit.failed("cones.shape", f"{cone_id} members/accounts/edges/roles malformed")
            all_ok = False
            continue
        members = _unique_map(raw_members, "node_id", audit, "cones.identity")
        accounts = _unique_map(raw_accounts, "binding_id", audit, "cones.identity")
        if not _unique_nonempty_strings(raw_edge_ids):
            audit.failed("cones.identity", f"{cone_id} duplicates edge IDs")
            all_ok = False
        cone_edges: dict[str, dict[str, Any]] = {}
        for edge_id in raw_edge_ids:
            if not _is_nonempty_string(edge_id):
                continue
            if edge_id not in edges:
                audit.failed("cones.edge_closure", f"{cone_id} references absent edge {edge_id}")
                all_ok = False
            else:
                cone_edges[edge_id] = edges[edge_id]
                edge = edges[edge_id]
                source = edge.get("source_node_id")
                target = edge.get("target_node_id")
                if source not in members or target not in members:
                    audit.failed(
                        "cones.edge_closure",
                        f"{cone_id}:{edge_id} endpoint is outside cone members",
                    )
                    all_ok = False

        if not _unique_nonempty_strings(roles):
            audit.failed("cones.candidate_accounting", f"{cone_id} roles are malformed")
            all_ok = False
        expected_candidates = candidates_by_ap.get(cone_ap_id, set())
        if set(accounts) != expected_candidates:
            audit.failed(
                "cones.candidate_accounting",
                f"{cone_id} does not account exactly for AP-role binding candidates",
            )
            all_ok = False
        if cones_doc.get("candidate_accounting_complete") is not True:
            audit.failed("cones.candidate_accounting", "candidate_accounting_complete is not true")
            all_ok = False
        if cones_doc.get("ranking_never_prunes") is not True:
            audit.failed("cones.candidate_accounting", "ranking_never_prunes is not true")
            all_ok = False

        roots: set[str] = set()
        for binding_id, account in accounts.items():
            disposition = account.get("disposition")
            account_roots = account.get("root_node_ids")
            if not _unique_nonempty_strings(account_roots):
                audit.failed("cones.roots", f"{cone_id}:{binding_id} roots malformed")
                all_ok = False
                continue
            if disposition == "INCLUDED":
                if not account_roots:
                    audit.failed("cones.roots", f"{cone_id}:{binding_id} INCLUDED has no root")
                    all_ok = False
                roots.update(account_roots)
            elif account_roots:
                audit.failed("cones.roots", f"{cone_id}:{binding_id} non-INCLUDED exposes roots")
                all_ok = False
        if any(root not in nodes or root not in members for root in roots):
            audit.failed("cones.roots", f"{cone_id} root is absent from graph/cone members")
            all_ok = False
        if members and not roots:
            audit.failed("cones.roots", f"{cone_id} has members but no INCLUDED root")
            all_ok = False
            continue

        fully_confirmed_root = len(roots) == 1
        observed_binding_roles: set[str] = set()
        saw_binding = False
        for binding in bindings_by_ap.get(cone_ap_id, []):
            saw_binding = True
            role = binding.get("role")
            if _is_nonempty_string(role):
                observed_binding_roles.add(role)
            candidates = binding.get("candidates")
            if binding.get("resolution") != "CONFIRMED" or not isinstance(
                candidates, list
            ) or not candidates:
                fully_confirmed_root = False
            for candidate in candidates if isinstance(candidates, list) else []:
                if not isinstance(candidate, dict) or candidate.get("status") == "REJECTED":
                    continue
                binding_id = candidate.get("binding_id")
                account = accounts.get(binding_id) if _is_nonempty_string(binding_id) else None
                if (
                    candidate.get("status") != "CONFIRMED"
                    or account is None
                    or account.get("disposition") != "INCLUDED"
                ):
                    fully_confirmed_root = False
        declared_cone_roles = {
            role for role in roles if _is_nonempty_string(role)
        }
        if not saw_binding or observed_binding_roles != declared_cone_roles:
            fully_confirmed_root = False

        root_membership = (
            "MUST_INFLUENCE" if fully_confirmed_root else "MAY_INFLUENCE"
        )
        expected_masks = _compute_path_membership_masks(
            roots, root_membership, incoming_edges
        )
        if set(members) != set(expected_masks):
            missing_members = sorted(set(expected_masks) - set(members))
            extra_members = sorted(set(members) - set(expected_masks))
            audit.failed(
                "cones.membership_fixed_point",
                f"{cone_id} member closure differs from graph fixed point; "
                f"missing={missing_members}, extra={extra_members}",
            )
            all_ok = False
        for member_id, mask in expected_masks.items():
            member = members.get(member_id)
            if member is None:
                continue
            expected_membership = _summarize_path_mask(mask)
            if member.get("membership") != expected_membership:
                audit.failed(
                    "cones.membership_fixed_point",
                    f"{cone_id}:{member_id} membership is {member.get('membership')!r}, "
                    f"expected {expected_membership} from mask 0x{mask:02x}",
                )
                all_ok = False
            if (
                mask & _PATH_CLASS_BITS["UNKNOWN_INFLUENCE"]
                and (
                    not _unique_nonempty_strings(member.get("uncertainty_reasons"))
                    or not member.get("uncertainty_reasons")
                )
            ):
                audit.failed(
                    "cones.membership_fixed_point",
                    f"{cone_id}:{member_id} retains UNKNOWN path provenance without a reason",
                )
                all_ok = False

        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in cone_edges.values():
            source = edge.get("source_node_id")
            target = edge.get("target_node_id")
            if _is_nonempty_string(source) and _is_nonempty_string(target):
                adjacency[source].append(target)

        for member_id, member in members.items():
            witness = member.get("witness_edge_ids")
            if not _unique_nonempty_strings(witness):
                audit.failed("cones.witness", f"{cone_id}:{member_id} witness malformed")
                all_ok = False
                continue
            if member_id in roots:
                if witness:
                    audit.failed("cones.witness", f"{cone_id}:{member_id} root witness is non-empty")
                    all_ok = False
            else:
                current = member_id
                if not witness:
                    audit.failed("cones.witness", f"{cone_id}:{member_id} has empty witness")
                    all_ok = False
                for edge_id in witness:
                    edge = cone_edges.get(edge_id)
                    if edge is None:
                        audit.failed(
                            "cones.witness",
                            f"{cone_id}:{member_id} witness edge {edge_id} is outside cone/graph",
                        )
                        all_ok = False
                        break
                    if edge.get("source_node_id") != current:
                        audit.failed(
                            "cones.witness",
                            f"{cone_id}:{member_id} witness is not a continuous directed path",
                        )
                        all_ok = False
                        break
                    current = edge.get("target_node_id")
                else:
                    if current not in roots:
                        audit.failed(
                            "cones.witness",
                            f"{cone_id}:{member_id} witness does not terminate at a root",
                        )
                        all_ok = False

            # Independent reachability check: do not merely trust witness order.
            queue: deque[str] = deque([member_id])
            seen = {member_id}
            reachable = member_id in roots
            while queue and not reachable:
                current = queue.popleft()
                for target in adjacency.get(current, []):
                    if target in roots:
                        reachable = True
                        break
                    if target not in seen:
                        seen.add(target)
                        queue.append(target)
            if not reachable:
                audit.failed(
                    "cones.reachability",
                    f"{cone_id}:{member_id} cannot reach any root over directed cone edges",
                )
                all_ok = False
    if all_ok and fixed_point_edges_ok:
        audit.passed(
            "cones.membership_fixed_point",
            f"{len(cones)} cones exactly match the four-class path-mask fixed point",
        )
        audit.passed(
            "cones.witness_reachability",
            f"{len(cones)} cones have closed witnesses, complete fixed-point members, and independently derived memberships",
        )


def verify_analysis(
    analysis_directory: Path,
    *,
    certificate_path: Path | None = None,
    path_roots: Sequence[Path] = (),
    binary: Path | None = None,
    argv_json: Path | None = None,
    implementation_root: Path | None = None,
    build_manifest_path: Path | None = None,
    environment_json: Path | None = None,
    verify_current_environment: bool = False,
    runtime_files: Sequence[Path] = (),
    strict_provenance: bool = False,
) -> dict[str, Any]:
    analysis_directory = analysis_directory.resolve()
    certificate_path = (
        certificate_path.resolve()
        if certificate_path is not None
        else analysis_directory / "analysis_certificate.json"
    )
    audit = Audit()
    if not certificate_path.is_file():
        audit.failed("certificate.exists", f"missing certificate: {certificate_path}")
        return audit.report(certificate_path, strict_provenance)
    if certificate_path.stat().st_size == 0:
        audit.failed("certificate.exists", f"empty certificate: {certificate_path}")
        return audit.report(certificate_path, strict_provenance)
    audit.passed("certificate.exists", "non-empty analysis_certificate.json exists")
    try:
        certificate = _as_object(_load_json(certificate_path), "certificate")
    except VerificationDataError as error:
        audit.failed("certificate.json", str(error))
        return audit.report(certificate_path, strict_provenance)

    _verify_certificate_basics(
        certificate,
        audit,
        binary,
        argv_json,
        strict_provenance,
    )
    _verify_build_manifest(
        certificate,
        audit,
        build_manifest_path=build_manifest_path,
        implementation_root=implementation_root,
        binary=binary,
        strict_provenance=strict_provenance,
    )
    _verify_environment(
        certificate,
        audit,
        environment_json=environment_json,
        verify_current_environment=verify_current_environment,
        strict_provenance=strict_provenance,
    )
    _verify_runtime_toolchain(
        certificate,
        audit,
        binary=binary,
        runtime_files=runtime_files,
        strict_provenance=strict_provenance,
    )
    input_by_kind, input_paths, outputs = _verify_artifact_bytes(
        certificate,
        certificate_path,
        analysis_directory,
        tuple(path.resolve() for path in path_roots),
        audit,
    )
    raw_outputs = certificate.get("outputs")
    output_by_kind = (
        _unique_map(raw_outputs, "kind", audit, "artifacts.outputs")
        if isinstance(raw_outputs, list)
        else {}
    )
    stages = _verify_stage_topology(
        certificate, input_by_kind, output_by_kind, audit
    )
    _verify_formats_and_references(
        input_by_kind, input_paths, outputs, audit, strict_provenance
    )
    _verify_internal_chain(input_by_kind, output_by_kind, outputs, audit)
    _verify_certificate_id(certificate, output_by_kind, audit)
    _verify_certificate_source_commitment(
        certificate, input_by_kind, outputs, audit, strict_provenance
    )
    _verify_source_input_provenance(
        certificate, input_by_kind, outputs, audit, strict_provenance
    )
    _verify_status_and_gaps(certificate, stages, outputs, audit)
    _verify_graph_and_cones(outputs, audit)
    return audit.report(certificate_path, strict_provenance)


def _parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a RIFT M4 analysis certificate and artifact chain"
    )
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--certificate", type=Path)
    parser.add_argument(
        "--path-root",
        action="append",
        default=[],
        type=Path,
        help="additional root for resolving relative input artifact paths",
    )
    parser.add_argument("--binary", type=Path, help="independently supplied tafuzz-sa binary")
    parser.add_argument(
        "--argv-json", type=Path, help="JSON array containing the exact analyzer argv"
    )
    parser.add_argument("--implementation-root", type=Path)
    parser.add_argument("--build-manifest", type=Path)
    parser.add_argument("--environment-json", type=Path)
    parser.add_argument("--verify-current-environment", action="store_true")
    parser.add_argument(
        "--runtime-file",
        action="append",
        default=[],
        type=Path,
        help="additional mapped runtime file not discoverable through ldd",
    )
    parser.add_argument(
        "--strict-provenance",
        action="store_true",
        help="treat every unsupported assurance (including build/source binding) as failure",
    )
    parser.add_argument("--report", type=Path, help="write full JSON report")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    options = _parse_arguments(sys.argv[1:] if argv is None else argv)
    report = verify_analysis(
        options.analysis_dir,
        certificate_path=options.certificate,
        path_roots=options.path_root,
        binary=options.binary,
        argv_json=options.argv_json,
        implementation_root=options.implementation_root,
        build_manifest_path=options.build_manifest,
        environment_json=options.environment_json,
        verify_current_environment=options.verify_current_environment,
        runtime_files=options.runtime_file,
        strict_provenance=options.strict_provenance,
    )
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if options.report is not None:
        options.report.parent.mkdir(parents=True, exist_ok=True)
        options.report.write_text(encoded, encoding="utf-8")
    print(
        f"{report['overall_status']} failures={report['failure_count']} "
        f"unsupported={report['unsupported_count']}"
    )
    if report["overall_status"] == "FAIL":
        for finding in report["findings"]:
            if finding["status"] == "FAIL":
                print(f"FAIL {finding['check_id']}: {finding['detail']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
