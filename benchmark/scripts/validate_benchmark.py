#!/usr/bin/env python3
"""Read-only Milestone-7 consistency, permalink, catalog, and local-link gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
M6 = BENCHMARK / "extraction_runs" / "milestone6"
M7 = BENCHMARK / "extraction_runs" / "milestone7"
AUDIT_JSON = M7 / "link_and_catalog_audit.json"
AUDIT_MD = M7 / "link_and_catalog_audit.md"
CATALOG_DIR = BENCHMARK / "mavlink_catalog"
PX4_CANONICAL_DIR = BENCHMARK / "PX4"
PX4_SUPERSEDED_DRAFT_DIR = BENCHMARK / "extraction_runs" / "milestone4" / "superseded_px4_draft"

SYSTEMS = {
    "ArduPilot": {
        "commit": "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
        "mavlink_commit": "13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472",
        "repo": ROOT / "baseline" / "ardupilot",
        "workspace_prefix": "baseline/ardupilot/",
        "github_prefix": "https://github.com/ArduPilot/ardupilot/blob/",
    },
    "PX4": {
        "commit": "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
        "mavlink_commit": "33af200d25ec6f0925b49b1ba82bbf1294ea5f72",
        "repo": ROOT / "baseline" / "px4",
        "workspace_prefix": "baseline/px4/",
        "github_prefix": "https://github.com/PX4/PX4-Autopilot/blob/",
    },
}

EXPECTED_COUNTS = {
    "properties": 13,
    "atomic_propositions": 46,
    "source_bindings": 227,
    "ap_observations": 77,
    "source_evidence": 28,
    "runtime_instances": 15,
    "runtime_property_parameters": 15,
}

LINK_GLOBS = (
    "README.md",
    "METHOD.md",
    "RESULTS.md",
    "MAVLink_ArduPilot_PX4_observability.md",
    "paper_audits/*.md",
    "mavlink_catalog/README.md",
    "extraction_runs/milestone*/*.md",
    "extraction_runs/milestone*/*/README.md",
    "ArduPilot/README.md",
    "ArduPilot/property_catalog.md",
    "ArduPilot/properties/*.md",
    "PX4/README.md",
    "PX4/property_catalog.md",
    "PX4/properties/*.md",
)

PX4_LEGACY_CANONICAL_PATHS = (
    "HIGH_CONFIDENCE_SUBSET.md",
    "ap_bindings.yaml",
    "candidate_index.csv",
    "corpus_manifest.csv",
    "exclusions.yaml",
    "mavlink_observability_draft.csv",
    "source_conflicts.yaml",
    "validation/README.md",
    "validation/validate_px4_artifacts.py",
)
PX4_CANONICAL_TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt", ".yaml", ".yml"}

SUBVALIDATORS = (("python3", "benchmark/scripts/validate_milestone6.py"),)
SIDE_EFFECTING_VALIDATORS = (
    (
        "python3 benchmark/scripts/validate_source_bindings.py",
        "writes Milestone-5 validation JSON files",
    ),
    (
        "python3 benchmark/mavlink_catalog/validate_catalog.py",
        "rewrites benchmark/mavlink_catalog/validation_report.json",
    ),
)

FORMULA_EPSILON = re.compile(r"(?:\bEPS(?:ILON)?\b|ε)", re.IGNORECASE)
SYMBOL_IGNORED = {
    "true", "false", "return", "const", "auto", "void", "float", "double",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t", "int", "if", "for", "while",
    "switch", "case", "new", "event", "branch", "predicate", "producer", "consumer",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_LINK = re.compile(r"<(?:a|img)\b[^>]*(?:href|src)=[\"']([^\"']+)[\"']", re.IGNORECASE)
LINE_FRAGMENT = re.compile(r"^L(\d+)(?:-L(\d+))?$")
PATH_LINE_SUFFIX = re.compile(r"^(.*):(\d+)(?:-(\d+))?$")


@dataclass
class Gate:
    checks: int = 0
    failures: list[str] = field(default_factory=list)
    metrics: Counter[str] = field(default_factory=Counter)

    def require(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_json(gate: Gate, path: Path, label: str | None = None) -> Any | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        gate.require(False, f"{label or path}: JSON parse failure: {error}")
        return None
    gate.require(True, f"{label or path}: JSON parses")
    gate.metrics["json_documents"] += 1
    return value


def read_csv(gate: Gate, path: Path, label: str | None = None) -> list[dict[str, str]] | None:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            fields = reader.fieldnames
    except (OSError, UnicodeError, csv.Error) as error:
        gate.require(False, f"{label or path}: CSV parse failure: {error}")
        return None
    gate.require(bool(fields), f"{label or path}: CSV header is missing")
    gate.require(all(None not in row for row in rows), f"{label or path}: CSV/header width mismatch")
    gate.metrics["csv_documents"] += 1
    gate.metrics["csv_rows"] += len(rows)
    return rows


def recursively_named(value: Any, name: str) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == name:
                yield item
            yield from recursively_named(item, name)
    elif isinstance(value, list):
        for item in value:
            yield from recursively_named(item, name)


def symbol_tokens(symbol: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", symbol)
    return [token for token in tokens if token.lower() not in SYMBOL_IGNORED and len(token) > 1]


def csv_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def load_final_review(gate: Gate, path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "review_state": "PRE_FINAL",
            "allowed_accepted_property_ids": [],
            "allowed_epsilon_property_ids": [],
            "allowed_conformance_property_ids": [],
        }
    document = read_json(gate, path, "explicit final-review status")
    if not isinstance(document, dict):
        return {
            "review_state": "INVALID_FINAL_REVIEW_STATUS",
            "allowed_accepted_property_ids": [],
            "allowed_epsilon_property_ids": [],
            "allowed_conformance_property_ids": [],
        }
    gate.require(document.get("review_state") == "FINAL_REVIEW_COMPLETE", "final-review state is not complete")
    gate.require(document.get("root_agent_explicit") is True, "final-review state lacks explicit root-agent marker")
    for key in (
        "allowed_accepted_property_ids",
        "allowed_epsilon_property_ids",
        "allowed_conformance_property_ids",
    ):
        value = document.get(key)
        valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
        gate.require(valid, f"final-review state lacks string list {key}")
        if not valid:
            document[key] = []
    return document


def validate_source_evidence(gate: Gate, property_id: str, source: dict[str, Any]) -> None:
    path = workspace_path(source.get("path_or_url", ""))
    exists = gate.require(path.is_file(), f"{property_id}/{source.get('source_id')}: source file missing")
    if not exists:
        return
    gate.require(sha256(path) == source.get("sha256"), f"{property_id}/{source.get('source_id')}: source hash drift")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    locator = source.get("locator", {})
    start = locator.get("line_start")
    end = locator.get("line_end")
    valid = isinstance(start, int) and isinstance(end, int) and 1 <= start <= end <= len(lines)
    gate.require(valid, f"{property_id}/{source.get('source_id')}: invalid source line range")
    if valid:
        quote = "\n".join(lines[start - 1 : end]).strip()
        gate.require(quote == source.get("exact_quote"), f"{property_id}/{source.get('source_id')}: exact quote drift")


def validate_location_string(
    gate: Gate,
    value: str,
    label: str,
    line_cache: dict[Path, list[str]],
    repo: Path | None = None,
) -> None:
    match = re.match(r"^(.*):(\d+)$", value)
    gate.require(match is not None, f"{label}: invalid path:line location {value}")
    if match is None:
        return
    location_path = Path(match.group(1))
    # Most records use workspace-relative paths; compiler-style macro
    # locations may instead be relative to the owning frozen repository.
    path = workspace_path(match.group(1))
    if not path.is_file() and repo is not None and not location_path.is_absolute():
        path = repo / location_path
    exists = gate.require(path.is_file(), f"{label}: missing location file {match.group(1)}")
    if not exists:
        return
    if path not in line_cache:
        line_cache[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
    line = int(match.group(2))
    gate.require(1 <= line <= len(line_cache[path]), f"{label}: line {line} outside {match.group(1)}")


def validate_binding(
    gate: Gate,
    system: str,
    property_id: str,
    ap_id: str,
    binding: dict[str, Any],
    line_cache: dict[Path, list[str]],
    frozen_blob_cache: dict[tuple[str, str], bytes],
) -> tuple[str, str]:
    config = SYSTEMS[system]
    binding_id = str(binding.get("binding_id"))
    gate.require(binding.get("commit") == config["commit"], f"{binding_id}: frozen commit mismatch")
    source_file = str(binding.get("file", ""))
    prefix = str(config["workspace_prefix"])
    gate.require(source_file.startswith(prefix), f"{binding_id}: source path has wrong repository prefix")
    path = workspace_path(source_file)
    exists = gate.require(path.is_file(), f"{binding_id}: source file is missing")
    if not exists:
        return binding_id, ""

    repo_relative = source_file[len(prefix) :]
    cache_key = (system, repo_relative)
    if cache_key not in frozen_blob_cache:
        process = subprocess.run(
            ["git", "-C", str(config["repo"]), "show", f"{config['commit']}:{repo_relative}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        gate.require(process.returncode == 0, f"{binding_id}: file absent from frozen commit: {process.stderr.decode(errors='replace').strip()}")
        frozen_blob_cache[cache_key] = process.stdout if process.returncode == 0 else b""
    gate.require(path.read_bytes() == frozen_blob_cache[cache_key], f"{binding_id}: worktree file differs from frozen blob")

    if path not in line_cache:
        line_cache[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = line_cache[path]
    line = binding.get("line")
    valid_line = isinstance(line, int) and 1 <= line <= len(lines)
    gate.require(valid_line, f"{binding_id}: invalid source line {line}")
    column = binding.get("column")
    gate.require(
        column is None or (valid_line and isinstance(column, int) and 1 <= column <= len(lines[line - 1]) + 1),
        f"{binding_id}: invalid source column {column}",
    )
    if valid_line:
        window = "\n".join(lines[max(0, line - 6) : min(len(lines), line + 5)])
        tokens = symbol_tokens(str(binding.get("symbol", "")))
        gate.require(bool(tokens), f"{binding_id}: symbol has no checkable token")
        gate.require(any(token in window for token in tokens), f"{binding_id}: symbol tokens absent near source line: {tokens}")

    permalink = f"{config['github_prefix']}{config['commit']}/{repo_relative}#L{line}"
    parsed = urllib.parse.urlparse(permalink)
    gate.require(parsed.scheme == "https" and parsed.netloc == "github.com", f"{binding_id}: invalid permalink host/scheme")
    gate.require(parsed.fragment == f"L{line}", f"{binding_id}: permalink line fragment drift")
    gate.require(permalink in str(binding.get("evidence", "")), f"{binding_id}: exact fixed-commit permalink missing from evidence")

    for key in ("macro_spelling_location", "macro_expansion_location"):
        value = binding.get(key)
        if value:
            validate_location_string(
                gate,
                str(value),
                f"{binding_id}/{key}",
                line_cache,
                Path(config["repo"]),
            )
    gate.metrics["bindings_validated"] += 1
    return binding_id, permalink


def validate_review_boundaries(
    gate: Gate,
    prop: dict[str, Any],
    final_review: dict[str, Any],
) -> bool:
    property_id = prop["property_id"]
    accepted_allowed = set(final_review.get("allowed_accepted_property_ids", []))
    epsilon_allowed = set(final_review.get("allowed_epsilon_property_ids", []))
    conformance_allowed = set(final_review.get("allowed_conformance_property_ids", []))
    is_pre_final = final_review.get("review_state") == "PRE_FINAL"

    if is_pre_final:
        gate.require(prop.get("status") != "ACCEPTED", f"{property_id}: ACCEPTED before explicit final review")
        gate.require(prop.get("review", {}).get("decision") == "PENDING", f"{property_id}: review closed before final review")
    elif prop.get("status") == "ACCEPTED":
        gate.require(property_id in accepted_allowed, f"{property_id}: ACCEPTED not authorized by final-review state")

    satisfaction = prop.get("implementation_satisfaction")
    if property_id not in conformance_allowed:
        gate.require(satisfaction == "NOT_ASSESSED", f"{property_id}: implementation/conformance verdict present")

    formulas = [
        prop.get("mitl", {}).get("symbolic"),
        prop.get("mitl", {}).get("concrete"),
        prop.get("mitl", {}).get("monitor_syntax"),
        *[item.get("formula") for item in prop.get("mitl", {}).get("concrete_instances", [])],
    ]
    has_epsilon = any(FORMULA_EPSILON.search(value) for value in formulas if isinstance(value, str))
    if property_id not in epsilon_allowed:
        gate.require(not has_epsilon, f"{property_id}: unapproved epsilon symbol in formula")
    return has_epsilon


def validate_runtime_instances(
    gate: Gate,
    prop: dict[str, Any],
    runtime_evidence: dict[str, Any],
) -> Counter[str]:
    property_id = prop["property_id"]
    captures = {item["capture_id"]: item for item in runtime_evidence.get("captures", [])}
    rows = {
        (item["property_id"], item["capture_id"]): item
        for item in runtime_evidence.get("property_parameters", [])
    }
    snapshot = prop.get("system_scope", {}).get("configuration_snapshot", {})
    runtime_path = relative(M6 / "runtime_evidence.json")
    gate.require(snapshot.get("status") == "CAPTURED", f"{property_id}: runtime configuration snapshot absent")
    gate.require(snapshot.get("path") == runtime_path, f"{property_id}: runtime snapshot path drift")
    gate.require(snapshot.get("sha256") == sha256(M6 / "runtime_evidence.json"), f"{property_id}: runtime snapshot hash drift")

    statuses: Counter[str] = Counter()
    for instance in prop.get("mitl", {}).get("concrete_instances", []):
        capture_id = instance.get("capture_id")
        gate.require(capture_id in captures, f"{property_id}: unknown runtime capture {capture_id}")
        row = rows.get((property_id, capture_id))
        gate.require(row is not None, f"{property_id}/{capture_id}: missing runtime property row")
        source = workspace_path(str(instance.get("source_path", "")))
        exists = gate.require(source.is_file(), f"{property_id}/{capture_id}: runtime source missing")
        if exists:
            gate.require(sha256(source) == instance.get("source_sha256"), f"{property_id}/{capture_id}: runtime source hash drift")
        if row is not None:
            for instance_key, row_key in (
                ("parameter_id", "parameter_id"),
                ("raw_value", "value"),
                ("raw_unit", "unit"),
                ("source_path", "source_path"),
                ("source_sha256", "source_sha256"),
                ("source_param_index", "source_param_index"),
                ("source_param_count", "source_param_count"),
            ):
                gate.require(instance.get(instance_key) == row.get(row_key), f"{property_id}/{capture_id}: {instance_key} drift")
        statuses[str(instance.get("status"))] += 1
        gate.metrics["runtime_instances"] += 1
    return statuses


def validate_properties(
    gate: Gate,
    final_review: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = read_json(gate, BENCHMARK / "schemas" / "property.schema.json", "property schema")
    runtime_evidence = read_json(gate, M6 / "runtime_evidence.json", "merged runtime evidence")
    if not isinstance(schema, dict) or not isinstance(runtime_evidence, dict):
        return {}, {}
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    all_property_ids: set[str] = set()
    all_ap_ids: set[str] = set()
    all_binding_ids: set[str] = set()
    all_source_ids: set[str] = set()
    all_source_paths: set[str] = set()
    flattened_bindings: dict[str, tuple[str, str, dict[str, Any]]] = {}
    flattened_observations: list[tuple[str, str, dict[str, Any]]] = []
    ap_observation_metadata: dict[str, dict[str, str]] = {}
    permalink_rows: list[tuple[str, str]] = []
    system_counts: dict[str, dict[str, Any]] = {}
    line_cache: dict[Path, list[str]] = {}
    frozen_blob_cache: dict[tuple[str, str], bytes] = {}
    aggregate_instance_statuses: Counter[str] = Counter()
    property_statuses: Counter[str] = Counter()
    mitl_statuses: Counter[str] = Counter()
    implementation_satisfaction: Counter[str] = Counter()
    ap_statuses: Counter[str] = Counter()
    observation_classes: Counter[str] = Counter()
    concrete_properties = 0
    epsilon_formula_properties = 0

    for system, config in SYSTEMS.items():
        repo = Path(config["repo"])
        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        gate.require(head == config["commit"], f"{system}: repository HEAD drift")
        catalog_path = BENCHMARK / system / "property_catalog.json"
        catalog = read_json(gate, catalog_path, f"{system} property catalog")
        if not isinstance(catalog, dict):
            continue
        gate.require(catalog.get("system") == system, f"{system}: catalog system mismatch")
        gate.require(catalog.get("firmware_commit") == config["commit"], f"{system}: catalog firmware commit drift")
        properties = catalog.get("properties", [])
        system_binding_count = 0
        system_observation_count = 0
        system_ap_count = 0
        source_count = 0
        atomic_map_expected: list[dict[str, Any]] = []
        for prop in properties:
            property_id = str(prop.get("property_id"))
            errors = sorted(validator.iter_errors(prop), key=lambda item: list(item.absolute_path))
            detail = "; ".join(f"{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors[:5])
            gate.require(not errors, f"{property_id}: property schema failure: {detail}")
            gate.require(property_id not in all_property_ids, f"duplicate property ID: {property_id}")
            all_property_ids.add(property_id)
            property_statuses[str(prop.get("status"))] += 1
            mitl_statuses[str(prop.get("mitl", {}).get("status"))] += 1
            implementation_satisfaction[str(prop.get("implementation_satisfaction"))] += 1
            if validate_review_boundaries(gate, prop, final_review):
                epsilon_formula_properties += 1

            property_file = BENCHMARK / system / "properties" / f"{property_id}.json"
            property_doc = read_json(gate, property_file, f"{property_id} standalone JSON")
            gate.require(property_doc == prop, f"{property_id}: standalone/catalog JSON drift")
            for source in prop.get("sources", []):
                source_id = str(source.get("source_id"))
                gate.require(source_id not in all_source_ids, f"duplicate source evidence ID: {source_id}")
                all_source_ids.add(source_id)
                all_source_paths.add(str(source.get("path_or_url", "")))
                validate_source_evidence(gate, property_id, source)
                source_count += 1

            instance_statuses = validate_runtime_instances(gate, prop, runtime_evidence)
            aggregate_instance_statuses.update(instance_statuses)
            if prop.get("mitl", {}).get("concrete") is not None:
                concrete_properties += 1

            for ap in prop.get("atomic_propositions", []):
                ap_id = str(ap.get("ap_id"))
                gate.require(ap_id not in all_ap_ids, f"duplicate AP ID: {ap_id}")
                all_ap_ids.add(ap_id)
                ap_statuses[str(ap.get("status"))] += 1
                observation_classes[str(ap.get("observability"))] += 1
                ap_observation_metadata[ap_id] = {
                    "ap_name": str(ap.get("name", "")),
                    "observability": str(ap.get("observability", "")),
                }
                system_ap_count += 1
                atomic_map_expected.append({"property_id": property_id, **ap})
                for binding in ap.get("source_bindings", []):
                    binding_id = str(binding.get("binding_id"))
                    gate.require(binding_id not in all_binding_ids, f"duplicate binding ID: {binding_id}")
                    all_binding_ids.add(binding_id)
                    key, permalink = validate_binding(
                        gate, system, property_id, ap_id, binding, line_cache, frozen_blob_cache
                    )
                    flattened_bindings[key] = (property_id, ap_id, binding)
                    permalink_rows.append((key, permalink))
                    system_binding_count += 1
                for observation in ap.get("mavlink_observations", []):
                    flattened_observations.append((property_id, ap_id, observation))
                    system_observation_count += 1

        atomic_map = read_json(gate, BENCHMARK / system / "atomic_proposition_map.json", f"{system} AP map")
        gate.require(atomic_map == atomic_map_expected, f"{system}: AP map/catalog drift")
        property_csv = read_csv(gate, BENCHMARK / system / "property_catalog.csv", f"{system} property catalog CSV")
        if property_csv is not None:
            expected_property_rows = [
                {
                    "property_id": prop["property_id"],
                    "title_zh": prop["title_zh"],
                    "status": prop["status"],
                    "classification": prop["classification"],
                    "vehicles": ";".join(prop["system_scope"]["vehicles"]),
                    "mitl_status": prop["mitl"]["status"],
                    "time_parameters": ";".join(contract.get("parameter_id") or "" for contract in prop["time_contracts"]),
                    "implementation_satisfaction": prop["implementation_satisfaction"],
                }
                for prop in properties
            ]
            gate.require(property_csv == expected_property_rows, f"{system}: property catalog CSV/catalog drift")
        ap_csv = read_csv(gate, BENCHMARK / system / "atomic_proposition_map.csv", f"{system} AP CSV")
        if ap_csv is not None:
            gate.require(len(ap_csv) == system_ap_count, f"{system}: AP CSV row-count drift")
            expected_ap_rows = [
                {
                    "property_id": row["property_id"],
                    "ap_id": row["ap_id"],
                    "name": row["name"],
                    "kind": row["kind"],
                    "value_type": row["value_type"],
                    "unit": csv_scalar(row.get("unit")),
                    "truth_condition": row["truth_condition"],
                    "validity_guard": row["validity_guard"],
                    "freshness": row["freshness"],
                    "observability": row["observability"],
                    "status": row["status"],
                    "source_binding_count": str(len(row["source_bindings"])),
                    "mavlink_observation_count": str(len(row["mavlink_observations"])),
                }
                for row in atomic_map_expected
            ]
            gate.require(ap_csv == expected_ap_rows, f"{system}: AP CSV/catalog drift")

        binding_csv = read_csv(gate, BENCHMARK / system / "source_bindings.csv", f"{system} binding CSV")
        if binding_csv is not None:
            gate.require(len(binding_csv) == system_binding_count, f"{system}: binding CSV row-count drift")
            for row in binding_csv:
                binding_id = row.get("binding_id", "")
                record = flattened_bindings.get(binding_id)
                gate.require(record is not None, f"{system}: binding CSV has unknown ID {binding_id}")
                if record is None:
                    continue
                property_id, ap_id, binding = record
                gate.require(row.get("property_id") == property_id and row.get("ap_id") == ap_id, f"{binding_id}: CSV ownership drift")
                for key in row:
                    if key in {"property_id", "ap_id"}:
                        continue
                    gate.require(row[key] == csv_scalar(binding.get(key)), f"{binding_id}: CSV field drift: {key}")

        observation_csv = read_csv(gate, BENCHMARK / system / "mavlink_observation_matrix.csv", f"{system} observation CSV")
        if observation_csv is not None:
            expected_rows = [
                {
                    "property_id": property_id,
                    "ap_id": ap_id,
                    **ap_observation_metadata[ap_id],
                    **observation,
                }
                for property_id, ap_id, observation in flattened_observations
                if (
                    (system == "ArduPilot" and property_id.startswith("ARD-"))
                    or (system == "PX4" and property_id.startswith("PX4-"))
                )
            ]
            gate.require(len(observation_csv) == len(expected_rows), f"{system}: observation CSV row-count drift")
            columns = tuple(observation_csv[0]) if observation_csv else ()
            normalized_expected = {
                tuple(csv_scalar(row.get(key)) for key in columns)
                for row in expected_rows
            }
            normalized_csv = {
                tuple(row.get(key, "") for key in columns)
                for row in observation_csv
            }
            gate.require(normalized_csv == normalized_expected, f"{system}: observation CSV/catalog drift")

        system_counts[system] = {
            "properties": len(properties),
            "atomic_propositions": system_ap_count,
            "source_bindings": system_binding_count,
            "ap_observations": system_observation_count,
            "source_evidence": source_count,
        }

    message_catalog = read_json(gate, CATALOG_DIR / "messages_and_fields.json", "MAVLink message catalog for AP observations")
    message_ids: dict[tuple[str, str], int] = {}
    message_fields: set[tuple[str, str, str]] = set()
    if isinstance(message_catalog, dict):
        for system_doc in message_catalog.get("systems", []):
            for message in system_doc.get("messages", []):
                key = (system_doc["system"], message["name"])
                message_ids[key] = int(message["message_id"])
                for field_doc in message.get("fields", []):
                    message_fields.add((system_doc["system"], message["name"], field_doc["name"]))
    for property_id, ap_id, observation in flattened_observations:
        system = "ArduPilot" if property_id.startswith("ARD-") else "PX4"
        key = (system, observation.get("message"))
        gate.require(message_ids.get(key) == observation.get("message_id"), f"{ap_id}: observation message identity drift")
        field_name = observation.get("field")
        gate.require(field_name is None or (system, observation.get("message"), field_name) in message_fields, f"{ap_id}: observation field identity drift")
        gate.require(observation.get("support") == "STATIC_SUPPORTED", f"{ap_id}: AP observation changed evidence layer")

    canonical_permalinks = "".join(f"{binding_id}\t{url}\n" for binding_id, url in sorted(permalink_rows)).encode()
    counts = {
        "properties": len(all_property_ids),
        "atomic_propositions": len(all_ap_ids),
        "source_bindings": len(all_binding_ids),
        "ap_observations": len(flattened_observations),
        "source_evidence": len(all_source_ids),
        "runtime_instances": gate.metrics["runtime_instances"],
        "runtime_property_parameters": len(runtime_evidence.get("property_parameters", [])),
    }
    for name, expected in EXPECTED_COUNTS.items():
        gate.require(counts[name] == expected, f"aggregate {name} count {counts[name]} != {expected}")
    for field in (
        "allowed_accepted_property_ids",
        "allowed_epsilon_property_ids",
        "allowed_conformance_property_ids",
    ):
        allowed = set(final_review.get(field, []))
        gate.require(allowed <= all_property_ids, f"final-review state contains unknown property IDs in {field}: {sorted(allowed - all_property_ids)}")
    gate.require(
        sum(aggregate_instance_statuses.values()) == counts["runtime_instances"]
        and "None" not in aggregate_instance_statuses,
        f"runtime instance status accounting drift: {dict(aggregate_instance_statuses)}",
    )
    gate.require(concrete_properties == 8, f"concrete-property count drift: {concrete_properties}")
    gate.require(ap_statuses == Counter({"BOUND": 43, "PARTIALLY_BOUND": 3}), f"AP status distribution drift: {dict(ap_statuses)}")

    facts = {
        "counts": counts,
        "system_counts": system_counts,
        "property_statuses": dict(sorted(property_statuses.items())),
        "mitl_statuses": dict(sorted(mitl_statuses.items())),
        "implementation_satisfaction": dict(sorted(implementation_satisfaction.items())),
        "accepted_property_count": property_statuses.get("ACCEPTED", 0),
        "epsilon_formula_properties": epsilon_formula_properties,
        "source_evidence_file_count": len(all_source_paths),
        "ap_statuses": dict(sorted(ap_statuses.items())),
        "ap_observability": dict(sorted(observation_classes.items())),
        "runtime_instance_statuses": dict(sorted(aggregate_instance_statuses.items())),
        "concrete_properties": concrete_properties,
        "binding_permalink_set_sha256": sha256_bytes(canonical_permalinks),
        "binding_permalink_count": len(permalink_rows),
        "binding_source_file_count": len(frozen_blob_cache),
    }
    return facts, {
        "runtime_evidence": runtime_evidence,
        "message_catalog": message_catalog,
    }


def validate_xml_catalog_lines(
    gate: Gate,
    messages: dict[str, Any],
    commands: dict[str, Any],
) -> None:
    line_cache: dict[Path, list[str]] = {}
    for system_doc in messages.get("systems", []):
        for message in system_doc.get("messages", []):
            path = workspace_path(message["origin_xml"])
            if path not in line_cache:
                line_cache[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
            line = int(message["origin_line"])
            valid = 1 <= line <= len(line_cache[path])
            gate.require(valid, f"{system_doc['system']} message {message['name']}: XML line invalid")
            if valid:
                text = line_cache[path][line - 1]
                gate.require(message["name"] in text and str(message["message_id"]) in text, f"{system_doc['system']} message {message['name']}: XML identity drift")
            for field_doc in message.get("fields", []):
                field_path = workspace_path(field_doc["origin_xml"])
                if field_path not in line_cache:
                    line_cache[field_path] = field_path.read_text(encoding="utf-8", errors="replace").splitlines()
                field_line = int(field_doc["origin_line"])
                field_valid = 1 <= field_line <= len(line_cache[field_path])
                gate.require(field_valid, f"{system_doc['system']} {message['name']}.{field_doc['name']}: XML line invalid")
                if field_valid:
                    gate.require(
                        f'name="{field_doc["name"]}"' in line_cache[field_path][field_line - 1],
                        f"{system_doc['system']} {message['name']}.{field_doc['name']}: XML field identity drift",
                    )
    for system_doc in commands.get("systems", []):
        for command in system_doc.get("commands", []):
            path = workspace_path(command["origin_xml"])
            if path not in line_cache:
                line_cache[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
            line = int(command["origin_line"])
            valid = 1 <= line <= len(line_cache[path])
            gate.require(valid, f"{system_doc['system']} command {command['name']}: XML line invalid")
            if valid:
                text = line_cache[path][line - 1]
                gate.require(command["name"] in text and str(command["command_id"]) in text, f"{system_doc['system']} command {command['name']}: XML identity drift")


def validate_catalogs(gate: Gate) -> dict[str, Any]:
    manifest = read_json(gate, CATALOG_DIR / "manifest.json", "static MAVLink manifest")
    runtime_manifest = read_json(gate, CATALOG_DIR / "runtime_catalog_manifest.json", "runtime overlay manifest")
    report = read_json(gate, CATALOG_DIR / "validation_report.json", "saved static/runtime catalog validation report")
    messages = read_json(gate, CATALOG_DIR / "messages_and_fields.json", "MAVLink messages/fields JSON")
    commands = read_json(gate, CATALOG_DIR / "commands.json", "MAVLink commands JSON")
    configuration = read_json(gate, CATALOG_DIR / "configuration_parameters.json", "configuration parameter JSON")
    overlay = read_json(gate, CATALOG_DIR / "actual_support_matrix.json", "runtime overlay JSON")
    if not all(isinstance(item, dict) for item in (manifest, runtime_manifest, report, messages, commands, configuration, overlay)):
        return {}

    gate.require(report.get("status") == "PASS" and report.get("failures") == [], "saved catalog validation report is not PASS")
    gate.require(report.get("saved_runtime_overlay_validated") is True, "saved catalog report did not validate runtime overlay")
    for name, expected_hash in manifest.get("output_sha256", {}).items():
        path = CATALOG_DIR / name
        exists = gate.require(path.is_file(), f"static catalog output missing: {name}")
        if exists:
            gate.require(sha256(path) == expected_hash, f"static catalog output hash drift: {name}")
    gate.require("static_support_matrix.csv" in manifest.get("output_sha256", {}), "static manifest does not own static support matrix")
    gate.require("actual_support_matrix.csv" not in manifest.get("output_sha256", {}), "static manifest incorrectly owns runtime overlay")
    for role in ("generator", "validator", "documentation"):
        item = manifest.get(role, {})
        path = workspace_path(item.get("path", ""))
        exists = gate.require(path.is_file(), f"static catalog {role} missing")
        if exists:
            gate.require(sha256(path) == item.get("sha256"), f"static catalog {role} hash drift")
    for system, inputs in manifest.get("inputs", {}).items():
        gate.require(inputs.get("sut_commit") == SYSTEMS[system]["commit"], f"{system}: catalog SUT commit drift")
        gate.require(inputs.get("mavlink_commit") == SYSTEMS[system]["mavlink_commit"], f"{system}: catalog MAVLink commit drift")
        for xml_file in inputs.get("xml_files", []):
            path = workspace_path(xml_file["path"])
            exists = gate.require(path.is_file(), f"catalog XML missing: {xml_file['path']}")
            if exists:
                gate.require(sha256(path) == xml_file["sha256"], f"catalog XML hash drift: {xml_file['path']}")
    for item in runtime_manifest.get("inputs", []):
        path = workspace_path(item["path"])
        exists = gate.require(path.is_file(), f"runtime overlay input missing: {item['path']}")
        if exists:
            gate.require(sha256(path) == item["sha256"], f"runtime overlay input hash drift: {item['path']}")
    for path_value, item in runtime_manifest.get("outputs", {}).items():
        path = workspace_path(path_value)
        exists = gate.require(path.is_file(), f"runtime overlay output missing: {path_value}")
        if exists:
            gate.require(sha256(path) == item["sha256"], f"runtime overlay output hash drift: {path_value}")

    message_csv = read_csv(gate, CATALOG_DIR / "messages_and_fields.csv", "MAVLink message/field CSV")
    command_csv = read_csv(gate, CATALOG_DIR / "commands.csv", "MAVLink command CSV")
    config_csv = read_csv(gate, CATALOG_DIR / "configuration_parameters.csv", "configuration parameter CSV")
    time_csv = read_csv(gate, CATALOG_DIR / "time_fields.csv", "time field CSV")
    static_csv = read_csv(gate, CATALOG_DIR / "static_support_matrix.csv", "static support CSV")
    overlay_csv = read_csv(gate, CATALOG_DIR / "actual_support_matrix.csv", "runtime overlay CSV")
    if any(item is None for item in (message_csv, command_csv, config_csv, time_csv, static_csv, overlay_csv)):
        return {}

    system_counts: dict[str, dict[str, int]] = {}
    message_keys: set[tuple[str, str, str]] = set()
    command_keys: set[tuple[str, str, str]] = set()
    config_keys: set[tuple[str, str, str]] = set()
    for system_doc in messages["systems"]:
        system = system_doc["system"]
        system_messages = system_doc["messages"]
        system_fields = sum(len(item["fields"]) for item in system_messages)
        command_doc = next(item for item in commands["systems"] if item["system"] == system)
        system_commands = command_doc["commands"]
        config_rows = [item for item in configuration["parameters"] if item["system"] == system]
        time_rows = [item for item in time_csv if item["system"] == system]
        system_counts[system] = {
            "messages": len(system_messages),
            "message_fields": system_fields,
            "commands": len(system_commands),
            "command_param_slots": sum(len(item["params"]) for item in system_commands),
            "configuration_parameters": len(config_rows),
            "time_rows": len(time_rows),
        }
        for message in system_messages:
            for item in message["fields"]:
                message_keys.add((system, message["name"], item["name"]))
        for command in system_commands:
            gate.require([item["index"] for item in command["params"]] == list(range(1, 8)), f"{system}/{command['name']}: command slots are not 1..7")
            for item in command["params"]:
                command_keys.add((system, command["name"], str(item["index"])))
        for item in config_rows:
            config_keys.add((system, item["vehicle_scope"], item["name"]))

    total_messages = sum(item["messages"] for item in system_counts.values())
    total_fields = sum(item["message_fields"] for item in system_counts.values())
    total_commands = sum(item["commands"] for item in system_counts.values())
    total_command_slots = sum(item["command_param_slots"] for item in system_counts.values())
    total_config = sum(item["configuration_parameters"] for item in system_counts.values())
    total_time = sum(item["time_rows"] for item in system_counts.values())
    gate.require(len(message_csv) == total_fields, "message field CSV/JSON count drift")
    gate.require(len(command_csv) == total_command_slots, "command slot CSV/JSON count drift")
    gate.require(len(config_csv) == total_config, "configuration CSV/JSON count drift")
    gate.require(len(time_csv) == total_time, "time CSV recount drift")
    gate.require(len(static_csv) == total_messages + total_commands, "static support row-count drift")

    for row in time_csv:
        kind = row["entity_kind"]
        if kind == "message_field":
            target = (row["system"], row["container_name"], row["item_name"])
            gate.require(target in message_keys, f"orphan time message field: {target}")
        elif kind == "command_param":
            target = (row["system"], row["container_name"], row["item_position"])
            gate.require(target in command_keys, f"orphan time command parameter: {target}")
        elif kind == "configuration_parameter":
            target = (row["system"], row["container_name"], row["item_name"])
            gate.require(target in config_keys, f"orphan time configuration parameter: {target}")
        else:
            gate.require(False, f"unknown time entity kind: {kind}")

    config_line_cache: dict[Path, list[str]] = {}
    for item in configuration["parameters"]:
        for location in item.get("source_locations", []):
            validate_location_string(gate, str(location), f"config {item['system']}/{item['name']}", config_line_cache)

    validate_xml_catalog_lines(gate, messages, commands)

    overlay_rows = overlay.get("rows", [])
    primary = [row for row in overlay_rows if row.get("row_scope") == "PROFILE_STATIC_MESSAGE_DEFINITION"]
    supplemental = [row for row in overlay_rows if row.get("row_scope") == "RUNTIME_NON_CATALOG_OBSERVATION"]
    gate.require(runtime_manifest.get("profile_count") == overlay.get("profile_count") == 4, "runtime overlay profile count drift")
    gate.require(len(primary) == runtime_manifest.get("primary_static_definition_row_count") == 1307, "runtime overlay primary row-count drift")
    gate.require(len(supplemental) == runtime_manifest.get("supplemental_non_catalog_observation_row_count") == 3, "runtime overlay supplemental row-count drift")
    gate.require(len(overlay_rows) == len(overlay_csv) == runtime_manifest.get("total_row_count") == 1310, "runtime overlay total row-count drift")
    gate.require(runtime_manifest.get("implementation_satisfaction") == overlay.get("implementation_satisfaction") == "NOT_ASSESSED", "runtime overlay assessed implementation")
    gate.require(all(row.get("support_inference") == "NO_GLOBAL_SUPPORT_OR_UNSUPPORTED_INFERENCE" for row in primary), "runtime overlay contains global support inference")
    gate.require(all(row.get("message_name") == "BAD_DATA" and row.get("support_inference") == "NOT_A_STATIC_MESSAGE_SUPPORT_ROW" for row in supplemental), "runtime supplemental rows drift")

    return {
        "system_counts": system_counts,
        "totals": {
            "messages": total_messages,
            "message_fields": total_fields,
            "commands": total_commands,
            "command_param_slots": total_command_slots,
            "configuration_parameters": total_config,
            "time_rows": total_time,
            "static_support_rows": len(static_csv),
            "runtime_overlay_primary_rows": len(primary),
            "runtime_overlay_supplemental_rows": len(supplemental),
            "runtime_overlay_total_rows": len(overlay_rows),
        },
        "hashes": {
            "static_manifest_sha256": sha256(CATALOG_DIR / "manifest.json"),
            "static_validation_report_sha256": sha256(CATALOG_DIR / "validation_report.json"),
            "runtime_catalog_manifest_sha256": sha256(CATALOG_DIR / "runtime_catalog_manifest.json"),
            "runtime_overlay_csv_sha256": sha256(CATALOG_DIR / "actual_support_matrix.csv"),
            "runtime_overlay_json_sha256": sha256(CATALOG_DIR / "actual_support_matrix.json"),
        },
    }


def markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    used: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for match in re.finditer(r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']", line, re.IGNORECASE):
            anchors.add(match.group(1))
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not heading:
            continue
        text = re.sub(r"<[^>]+>", "", heading.group(1)).strip().lower()
        text = re.sub(r"[^\w\-\s]", "", text, flags=re.UNICODE)
        base = re.sub(r"\s+", "-", text).strip("-")
        suffix = used[base]
        used[base] += 1
        anchors.add(base if suffix == 0 else f"{base}-{suffix}")
    return anchors


def parse_markdown_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    title = re.match(r"^(\S+)(?:\s+[\"'].*[\"'])$", value)
    return title.group(1) if title else value


def validate_local_links(gate: Gate) -> dict[str, Any]:
    markdown_files: set[Path] = set()
    for pattern in LINK_GLOBS:
        markdown_files.update(BENCHMARK.glob(pattern))
    records: list[tuple[str, int, str]] = []
    anchor_cache: dict[Path, set[str]] = {}
    line_cache: dict[Path, int] = {}
    for source in sorted(markdown_files):
        text = source.read_text(encoding="utf-8", errors="replace")
        fence_marker: str | None = None
        for line_number, line in enumerate(text.splitlines(), 1):
            fence = re.match(r"^\s*(`{3,}|~{3,})", line)
            if fence:
                marker = fence.group(1)[0]
                if fence_marker is None:
                    fence_marker = marker
                elif fence_marker == marker:
                    fence_marker = None
                continue
            if fence_marker is not None:
                # Literal source quotes and command examples are not rendered links.
                continue
            targets = [match.group(1) for match in MARKDOWN_LINK.finditer(line)]
            targets.extend(match.group(1) for match in HTML_LINK.finditer(line))
            for raw_target in targets:
                target = parse_markdown_target(raw_target)
                parsed = urllib.parse.urlparse(target)
                if parsed.scheme or target.startswith("//"):
                    continue
                decoded_path = urllib.parse.unquote(parsed.path)
                resolved = source if not decoded_path else (Path(decoded_path) if Path(decoded_path).is_absolute() else source.parent / decoded_path)
                suffix_lines: tuple[int, int] | None = None
                if not resolved.exists():
                    suffix_match = PATH_LINE_SUFFIX.match(decoded_path)
                    if suffix_match:
                        unsuffixed = suffix_match.group(1)
                        candidate = Path(unsuffixed) if Path(unsuffixed).is_absolute() else source.parent / unsuffixed
                        if candidate.exists():
                            resolved = candidate
                            suffix_start = int(suffix_match.group(2))
                            suffix_lines = (suffix_start, int(suffix_match.group(3) or suffix_start))
                records.append((relative(source), line_number, target))
                exists = gate.require(resolved.exists(), f"broken local link {relative(source)}:{line_number}: {target}")
                if exists and suffix_lines is not None and resolved.is_file():
                    if resolved not in line_cache:
                        line_cache[resolved] = len(resolved.read_text(encoding="utf-8", errors="replace").splitlines())
                    start, end = suffix_lines
                    gate.require(1 <= start <= end <= line_cache[resolved], f"invalid path:line target {target} from {relative(source)}:{line_number}")
                if not exists or not parsed.fragment or not resolved.is_file():
                    continue
                fragment = urllib.parse.unquote(parsed.fragment)
                line_match = LINE_FRAGMENT.match(fragment)
                if line_match:
                    if resolved not in line_cache:
                        line_cache[resolved] = len(resolved.read_text(encoding="utf-8", errors="replace").splitlines())
                    start = int(line_match.group(1))
                    end = int(line_match.group(2) or start)
                    gate.require(1 <= start <= end <= line_cache[resolved], f"invalid line fragment {target} from {relative(source)}:{line_number}")
                elif resolved.suffix.lower() in {".md", ".markdown"}:
                    if resolved not in anchor_cache:
                        anchor_cache[resolved] = markdown_anchors(resolved)
                    gate.require(fragment in anchor_cache[resolved], f"missing Markdown anchor {target} from {relative(source)}:{line_number}")
    canonical = "".join(f"{path}:{line}\t{target}\n" for path, line, target in sorted(records)).encode()
    return {
        "markdown_files": len(markdown_files),
        "local_links": len(records),
        "local_link_set_sha256": sha256_bytes(canonical),
        "scope_globs": list(LINK_GLOBS),
    }


def validate_px4_draft_isolation(gate: Gate) -> None:
    """Keep the historical 14-candidate draft immutable and out of canonical inputs."""
    gate.require(PX4_CANONICAL_DIR.is_dir(), "canonical PX4 directory is missing")
    for relative_path in PX4_LEGACY_CANONICAL_PATHS:
        gate.require(
            not (PX4_CANONICAL_DIR / relative_path).exists(),
            f"legacy PX4 draft path remains in canonical directory: {relative_path}",
        )
    legacy_candidate_yamls = sorted(PX4_CANONICAL_DIR.glob("properties/PX4-MC-CAND-*.yaml"))
    gate.require(
        not legacy_candidate_yamls,
        "legacy PX4 candidate YAML remains canonical: "
        + ", ".join(relative(path) for path in legacy_candidate_yamls),
    )
    canonical_yamls = sorted(
        path for path in PX4_CANONICAL_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
    )
    gate.require(
        not canonical_yamls,
        "unexpected YAML remains in canonical PX4 tree: "
        + ", ".join(relative(path) for path in canonical_yamls),
    )

    readme_path = PX4_CANONICAL_DIR / "README.md"
    readme_exists = gate.require(readme_path.is_file(), "canonical PX4 README is missing")
    readme_text = readme_path.read_text(encoding="utf-8") if readme_exists else ""
    for marker in ("CANONICAL_STAGE7_CATALOG", "SUPERSEDED_NON_CANONICAL_DRAFT"):
        gate.require(marker in readme_text, f"canonical PX4 README missing isolation marker: {marker}")

    for path in sorted(PX4_CANONICAL_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in PX4_CANONICAL_TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            gate.require(False, f"cannot read canonical PX4 text file {relative(path)}: {error}")
            continue
        gate.require("EPS_OBS" not in text, f"historical EPS_OBS token leaked into canonical PX4 file: {relative(path)}")
        gate.require(
            "benchmark/PX4/properties/*.yaml" not in text,
            f"canonical PX4 file points to superseded in-place YAML glob: {relative(path)}",
        )

    manifest_path = PX4_SUPERSEDED_DRAFT_DIR / "archive_manifest.json"
    manifest = read_json(gate, manifest_path, "superseded PX4 draft manifest")
    if not isinstance(manifest, dict):
        return
    gate.require(manifest.get("schema_version") == "1.0", "superseded PX4 draft manifest schema drift")
    gate.require(
        manifest.get("status") == "SUPERSEDED_NON_CANONICAL_DRAFT",
        "superseded PX4 draft status drift",
    )
    gate.require(manifest.get("canonical_input") is False, "superseded PX4 draft became a canonical input")
    gate.require(
        manifest.get("implementation_satisfaction") == "NOT_ASSESSED",
        "superseded PX4 draft asserts implementation satisfaction",
    )
    entries = manifest.get("files")
    entries_are_list = gate.require(isinstance(entries, list), "superseded PX4 draft file manifest is not a list")
    if not entries_are_list:
        return
    gate.require(len(entries) == 24, f"superseded PX4 draft manifest must contain 24 files, got {len(entries)}")

    manifested_paths: list[str] = []
    archive_root = PX4_SUPERSEDED_DRAFT_DIR.resolve()
    for index, entry in enumerate(entries):
        valid_entry = gate.require(
            isinstance(entry, dict) and set(entry) == {"path", "sha256", "bytes"},
            f"superseded PX4 draft file entry {index} has invalid shape",
        )
        if not valid_entry:
            continue
        raw_path = entry.get("path")
        relative_path = Path(raw_path) if isinstance(raw_path, str) else Path()
        safe_path = (
            isinstance(raw_path, str)
            and bool(raw_path)
            and not relative_path.is_absolute()
            and all(part not in {"", ".", ".."} for part in relative_path.parts)
        )
        gate.require(safe_path, f"unsafe superseded PX4 draft path at entry {index}: {raw_path!r}")
        if not safe_path:
            continue
        candidate = PX4_SUPERSEDED_DRAFT_DIR / relative_path
        try:
            candidate.resolve().relative_to(archive_root)
            confined = True
        except ValueError:
            confined = False
        gate.require(confined, f"superseded PX4 draft path escapes archive: {raw_path}")
        manifested_paths.append(relative_path.as_posix())
        exists = gate.require(candidate.is_file(), f"superseded PX4 draft file missing: {raw_path}")
        gate.require(not candidate.is_symlink(), f"superseded PX4 draft file is a symlink: {raw_path}")
        expected_hash = entry.get("sha256")
        gate.require(
            isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None,
            f"superseded PX4 draft hash is invalid: {raw_path}",
        )
        expected_bytes = entry.get("bytes")
        gate.require(
            isinstance(expected_bytes, int) and not isinstance(expected_bytes, bool) and expected_bytes >= 0,
            f"superseded PX4 draft byte count is invalid: {raw_path}",
        )
        if exists:
            gate.require(candidate.stat().st_size == expected_bytes, f"superseded PX4 draft byte-size drift: {raw_path}")
            gate.require(sha256(candidate) == expected_hash, f"superseded PX4 draft hash drift: {raw_path}")

    gate.require(len(manifested_paths) == len(set(manifested_paths)), "superseded PX4 draft manifest has duplicate paths")
    actual_paths = {
        path.relative_to(PX4_SUPERSEDED_DRAFT_DIR).as_posix()
        for path in PX4_SUPERSEDED_DRAFT_DIR.rglob("*")
        if path.is_file() and path.name not in {"ARCHIVE_NOTICE.md", "archive_manifest.json"}
    }
    gate.require(
        actual_paths == set(manifested_paths),
        "superseded PX4 draft archive/manifest membership drift: "
        f"missing={sorted(set(manifested_paths) - actual_paths)} extra={sorted(actual_paths - set(manifested_paths))}",
    )
    notice_path = PX4_SUPERSEDED_DRAFT_DIR / "ARCHIVE_NOTICE.md"
    notice_exists = gate.require(notice_path.is_file(), "superseded PX4 draft archive notice is missing")
    if notice_exists:
        notice_text = notice_path.read_text(encoding="utf-8")
        gate.require(
            "SUPERSEDED_NON_CANONICAL_DRAFT" in notice_text and "不是最终 benchmark 输入" in notice_text,
            "superseded PX4 draft archive notice marker drift",
        )


def validate_audit_contract(
    gate: Gate,
    review_state: str,
    facts: dict[str, Any],
) -> None:
    audit = read_json(gate, AUDIT_JSON, "Milestone-7 machine audit")
    if not isinstance(audit, dict):
        return
    expected_keys = {
        "schema_version", "audit_id", "generated_on", "review_state", "scope",
        "frozen_commits", "counts", "property_gate", "binding_permalink_gate",
        "catalog_gate", "local_link_gate", "subvalidators", "report_markdown",
        "limitations", "unresolved",
    }
    gate.require(set(audit) == expected_keys, "Milestone-7 audit JSON top-level key drift")
    gate.require(audit.get("schema_version") == "1.0", "Milestone-7 audit schema version drift")
    gate.require(audit.get("review_state") == review_state, "Milestone-7 audit review-state drift")
    scope = audit.get("scope", {})
    gate.require(scope.get("source_control_flow_property_inference") is False, "audit permits source-control-flow property inference")
    gate.require(scope.get("network_permalink_fetch") is False, "audit unexpectedly claims network permalink fetch")
    expected_commits = {
        system: {
            "firmware_commit": config["commit"],
            "mavlink_commit": config["mavlink_commit"],
        }
        for system, config in SYSTEMS.items()
    }
    gate.require(audit.get("frozen_commits") == expected_commits, "Milestone-7 audit frozen-commit drift")
    gate.require(audit.get("counts") == facts.get("counts"), "Milestone-7 audit aggregate count drift")
    property_gate = audit.get("property_gate", {})
    for field in (
        "property_statuses",
        "mitl_statuses",
        "implementation_satisfaction",
        "accepted_property_count",
        "epsilon_formula_properties",
        "source_evidence_file_count",
        "ap_statuses",
        "ap_observability",
        "runtime_instance_statuses",
        "concrete_properties",
    ):
        gate.require(property_gate.get(field) == facts.get(field), f"audit property-gate drift: {field}")
    permalink = audit.get("binding_permalink_gate", {})
    gate.require(permalink.get("count") == facts.get("binding_permalink_count"), "audit permalink count drift")
    gate.require(permalink.get("source_file_count") == facts.get("binding_source_file_count"), "audit permalink source-file count drift")
    gate.require(permalink.get("set_sha256") == facts.get("binding_permalink_set_sha256"), "audit permalink digest drift")
    gate.require(permalink.get("network_fetch_performed") is False, "audit unexpectedly claims network permalink fetch")
    catalog = audit.get("catalog_gate", {})
    gate.require(catalog.get("system_counts") == facts.get("catalog", {}).get("system_counts"), "audit catalog system count drift")
    gate.require(catalog.get("totals") == facts.get("catalog", {}).get("totals"), "audit catalog total drift")
    gate.require(catalog.get("hashes") == facts.get("catalog", {}).get("hashes"), "audit catalog hash drift")
    links = audit.get("local_link_gate", {})
    gate.require(links.get("markdown_files") == facts.get("local_links", {}).get("markdown_files"), "audit Markdown-file count drift")
    gate.require(links.get("local_links") == facts.get("local_links", {}).get("local_links"), "audit local-link count drift")
    gate.require(links.get("set_sha256") == facts.get("local_links", {}).get("local_link_set_sha256"), "audit local-link digest drift")
    gate.require(links.get("scope_globs") == facts.get("local_links", {}).get("scope_globs"), "audit local-link scope drift")
    gate.require(links.get("broken") == 0, "audit local-link broken count is nonzero")
    gate.require(isinstance(audit.get("limitations"), list) and bool(audit.get("limitations")), "audit limitations are missing")
    gate.require(isinstance(audit.get("unresolved"), list) and bool(audit.get("unresolved")), "audit unresolved list is missing")
    report = audit.get("report_markdown", {})
    gate.require(report.get("path") == relative(AUDIT_MD), "audit Markdown path drift")
    exists = gate.require(AUDIT_MD.is_file(), "Milestone-7 Markdown audit missing")
    if exists:
        gate.require(report.get("sha256") == sha256(AUDIT_MD), "Milestone-7 Markdown audit hash drift")
        text = AUDIT_MD.read_text(encoding="utf-8")
        for required in (
            review_state, "13", "46", "227", "77", "NOT_ASSESSED",
            "fixed-commit permalink", "不从源码控制流产生或修改性质",
        ):
            gate.require(required in text, f"Milestone-7 Markdown audit missing token: {required}")
        gate.require(not re.search(r"\b(?:TODO|TBD|FIXME)\b", text), "Milestone-7 Markdown audit retains placeholder marker")


def run_subvalidators(gate: Gate) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for command in SUBVALIDATORS:
        command_text = shlex.join(command)
        print(f"SUBVALIDATOR command={command_text}", file=sys.stderr)
        print(f"SUBVALIDATOR cwd={ROOT}", file=sys.stderr)
        print("SUBVALIDATOR env=PYTHONDONTWRITEBYTECODE=1", file=sys.stderr)
        process = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.stdout:
            print(process.stdout.rstrip(), file=sys.stderr)
        if process.stderr:
            print(process.stderr.rstrip(), file=sys.stderr)
        gate.require(process.returncode == 0, f"subvalidator failed ({process.returncode}): {command_text}")
        results.append({"command": command_text, "return_code": process.returncode})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts-only", action="store_true", help="validate live inputs and print facts without requiring M7 audit artifacts")
    parser.add_argument("--skip-subvalidators", action="store_true", help="skip read-only child validators")
    parser.add_argument(
        "--final-review-status",
        type=Path,
        help="explicit root-agent FINAL_REVIEW_COMPLETE status file; absent means PRE_FINAL",
    )
    args = parser.parse_args()
    gate = Gate()
    gate.require(ROOT == Path("/home/lqq/project/TAFuzz"), f"unexpected workspace root: {ROOT}")
    final_path = args.final_review_status
    if final_path is not None and not final_path.is_absolute():
        final_path = ROOT / final_path
    final_review = load_final_review(gate, final_path)
    review_state = str(final_review.get("review_state"))

    property_facts, _ = validate_properties(gate, final_review)
    catalog_facts = validate_catalogs(gate)
    validate_px4_draft_isolation(gate)
    local_link_facts = validate_local_links(gate)
    facts = {
        **property_facts,
        "catalog": catalog_facts,
        "local_links": local_link_facts,
    }
    if not args.facts_only:
        validate_audit_contract(gate, review_state, facts)

    for command, reason in SIDE_EFFECTING_VALIDATORS:
        print(f"NOT_RUN side_effecting_validator={command} reason={reason}", file=sys.stderr)
    subvalidators: list[dict[str, Any]] = []
    if not args.skip_subvalidators and not args.facts_only:
        subvalidators = run_subvalidators(gate)

    result = {
        "schema_version": "1.0",
        "status": "PASS" if not gate.failures else "FAIL",
        "review_state": review_state,
        "checks": gate.checks,
        "failure_count": len(gate.failures),
        "failures": gate.failures,
        "counts": facts.get("counts", {}),
        "system_counts": facts.get("system_counts", {}),
        "property_statuses": facts.get("property_statuses", {}),
        "mitl_statuses": facts.get("mitl_statuses", {}),
        "implementation_satisfaction": facts.get("implementation_satisfaction", {}),
        "accepted_property_count": facts.get("accepted_property_count"),
        "epsilon_formula_properties": facts.get("epsilon_formula_properties"),
        "source_evidence_file_count": facts.get("source_evidence_file_count"),
        "ap_statuses": facts.get("ap_statuses", {}),
        "ap_observability": facts.get("ap_observability", {}),
        "runtime_instance_statuses": facts.get("runtime_instance_statuses", {}),
        "concrete_properties": facts.get("concrete_properties"),
        "binding_permalink_count": facts.get("binding_permalink_count"),
        "binding_permalink_set_sha256": facts.get("binding_permalink_set_sha256"),
        "binding_source_file_count": facts.get("binding_source_file_count"),
        "catalog": catalog_facts,
        "local_links": local_link_facts,
        "subvalidators": subvalidators,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not gate.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
