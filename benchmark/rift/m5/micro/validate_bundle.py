#!/usr/bin/env python3
"""Validate the M5 enrichment bundle, including the C++ loader/binder gate."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from typing import Any, Mapping, Sequence


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: pathlib.Path) -> str:
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]
    payload = (json.dumps(entries, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def write_result(path: pathlib.Path, value: Any) -> None:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def json_schema_validator(schema_root: pathlib.Path):
    try:
        from jsonschema import Draft7Validator, RefResolver
    except ImportError as error:
        raise RuntimeError(f"jsonschema is required: {error}") from error
    common_path = schema_root / "common.schema.json"
    property_path = schema_root / "typed_property_ir.schema.json"
    common = json.loads(common_path.read_text(encoding="utf-8"))
    schema = json.loads(property_path.read_text(encoding="utf-8"))
    resolver = RefResolver.from_schema(
        schema, store={common["$id"]: common, schema["$id"]: schema}
    )
    return (
        Draft7Validator(schema, resolver=resolver),
        {
            "common.schema.json": sha256_file(common_path),
            "typed_property_ir.schema.json": sha256_file(property_path),
        },
    )


def bind_one(
    analyzer: pathlib.Path,
    frozen_root: pathlib.Path,
    bundle_root: pathlib.Path,
    case: Mapping[str, Any],
    temporary_root: pathlib.Path,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    output = temporary_root / case_id / "ap_bindings.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(analyzer),
        "bind",
        "--compile-db",
        str(frozen_root / case["compile_database"]["path"]),
        "--property",
        str(bundle_root / case["enriched_property_ir"]["path"]),
        "--output",
        str(output),
        "--source-root",
        str(frozen_root),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    record: dict[str, Any] = {
        "case_id": case_id,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "status": "FAILED",
        "role_binding_count": 0,
        "resolution_distribution": {},
    }
    if completed.returncode != 0 or not output.is_file():
        return record
    try:
        bindings = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        record["stderr"] += f"; invalid bindings JSON: {error}"
        return record
    raw_bindings = bindings.get("bindings", [])
    resolutions = Counter(
        item.get("resolution", "MISSING") for item in raw_bindings if isinstance(item, Mapping)
    )
    record.update(
        status="PASS",
        role_binding_count=len(raw_bindings),
        resolution_distribution=dict(sorted(resolutions.items())),
        property_ir_sha256=bindings.get("property_ir_sha256"),
        binding_artifact_status=(
            "CONSERVATIVE_INCOMPLETE" if "status=CONSERVATIVE_INCOMPLETE" in completed.stdout else "COMPLETE"
        ),
    )
    return record


def validate(
    bundle_root: pathlib.Path,
    frozen_root: pathlib.Path,
    schema_root: pathlib.Path,
    analyzer_path: pathlib.Path,
    jobs: int,
) -> dict[str, Any]:
    bundle_root = bundle_root.resolve()
    frozen_root = frozen_root.resolve()
    manifest_path = bundle_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validator, schema_digests = json_schema_validator(schema_root.resolve())
    failures: list[dict[str, Any]] = []
    validated = 0
    for case in manifest.get("cases", []):
        property_path = bundle_root / case["enriched_property_ir"]["path"]
        observed_digest = sha256_file(property_path)
        if observed_digest != case["enriched_property_ir"]["sha256"]:
            failures.append(
                {"case_id": case["case_id"], "stage": "digest", "detail": observed_digest}
            )
            continue
        instance = json.loads(property_path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            failures.append(
                {
                    "case_id": case["case_id"],
                    "stage": "json_schema",
                    "detail": [f"{list(error.path)}: {error.message}" for error in errors],
                }
            )
        else:
            validated += 1

    generator = manifest.get("generator", {})
    generator_path = pathlib.Path(__file__).resolve().parent / str(generator.get("tool", ""))
    generator_digest_matches = generator_path.is_file() and sha256_file(generator_path) == generator.get("tool_sha256")
    observed_frozen_tree = tree_digest(frozen_root)
    frozen_matches = (
        observed_frozen_tree == manifest.get("source_bundle", {}).get("tree_sha256_before")
        == manifest.get("source_bundle", {}).get("tree_sha256_after")
    )

    analyzer_path = analyzer_path.resolve()
    analyzer_digest = sha256_file(analyzer_path)
    frozen_analyzer = pathlib.Path(tempfile.gettempdir()) / f"rift-enrichment-validator-{analyzer_digest}"
    if not frozen_analyzer.exists():
        shutil.copy2(analyzer_path, frozen_analyzer)
        frozen_analyzer.chmod(0o755)
    if sha256_file(frozen_analyzer) != analyzer_digest:
        raise RuntimeError("copied analyzer digest mismatch")

    with tempfile.TemporaryDirectory(prefix="rift-m5-cpp-bindings-") as temporary:
        temporary_root = pathlib.Path(temporary)
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [
                pool.submit(
                    bind_one,
                    frozen_analyzer,
                    frozen_root,
                    bundle_root,
                    case,
                    temporary_root,
                )
                for case in manifest.get("cases", [])
            ]
            bind_records = [future.result() for future in futures]
    bind_records.sort(key=lambda item: item["case_id"])
    bind_failures = [record for record in bind_records if record["status"] != "PASS"]
    resolution_distribution = Counter()
    artifact_status_distribution = Counter()
    role_binding_count = 0
    for record in bind_records:
        role_binding_count += record["role_binding_count"]
        resolution_distribution.update(record["resolution_distribution"])
        if record["status"] == "PASS":
            artifact_status_distribution[record["binding_artifact_status"]] += 1

    passed = (
        validated == len(manifest.get("cases", []))
        and not failures
        and not bind_failures
        and generator_digest_matches
        and frozen_matches
    )
    return {
        "schema_version": "1.0.0",
        "artifact_id": "rift.m5.micro.typed_predicate_enrichment.validation",
        "status": "PASS" if passed else "FAIL",
        "bundle_manifest": {"path": str(manifest_path), "sha256": sha256_file(manifest_path)},
        "schema_digests": schema_digests,
        "generator_digest_matches_manifest": generator_digest_matches,
        "frozen_tree": {
            "observed_sha256": observed_frozen_tree,
            "matches_manifest_before_and_after": frozen_matches,
        },
        "json_schema": {
            "case_count": len(manifest.get("cases", [])),
            "validated_case_count": validated,
            "failures": failures,
        },
        "cpp_loader_and_binder": {
            "analyzer_path": str(analyzer_path),
            "analyzer_sha256": analyzer_digest,
            "copied_analyzer_path": str(frozen_analyzer),
            "case_count": len(bind_records),
            "passed_case_count": len(bind_records) - len(bind_failures),
            "failed_cases": bind_failures,
            "role_binding_count": role_binding_count,
            "resolution_distribution": dict(sorted(resolution_distribution.items())),
            "artifact_status_distribution": dict(sorted(artifact_status_distribution.items())),
        },
        "extraction_summary": manifest.get("summary"),
        "claim_boundary": {
            "cpp_gate": "load_typed_property_ir + validate_typed_property_ir + bind_atomic_propositions",
            "binding_completeness_required": False,
            "semantic_threshold_confirmation": "NOT_CLAIMED",
            "gold_mutation_answers_used": False,
        },
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    micro_root = pathlib.Path(__file__).resolve().parent
    workspace = micro_root.parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=pathlib.Path, default=micro_root / "bundle")
    parser.add_argument(
        "--frozen-root", type=pathlib.Path, default=workspace / "benchmark/rift/m4/micro/frozen"
    )
    parser.add_argument(
        "--schema-root", type=pathlib.Path, default=workspace / "src/StaticAnalysis/schema"
    )
    parser.add_argument("--analyzer", type=pathlib.Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if options.jobs <= 0:
            raise RuntimeError("--jobs must be positive")
        result = validate(
            options.bundle,
            options.frozen_root,
            options.schema_root,
            options.analyzer,
            options.jobs,
        )
        write_result(options.output.resolve(), result)
        print(
            f"{result['status']} typed-predicate-enrichment-validation "
            f"schema={result['json_schema']['validated_case_count']}/{result['json_schema']['case_count']} "
            f"cpp={result['cpp_loader_and_binder']['passed_case_count']}/{result['cpp_loader_and_binder']['case_count']} "
            f"output={options.output.resolve()}"
        )
        return 0 if result["status"] == "PASS" else 1
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL typed-predicate-enrichment-validation: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
