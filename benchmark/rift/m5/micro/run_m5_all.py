#!/usr/bin/env python3
"""Run the property-independent RIFT M5 pipeline over the frozen 120 cases.

This is the untrusted analysis phase.  It validates only public/frozen inputs,
never imports an evaluator, and hides the private mechanical oracle from every
analyzer process.  A run manifest is sealed only after each detached M5
certificate verifies against the production schemas.
"""

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
import time
from typing import Any, Iterable, Mapping, Sequence


HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
DEFAULT_FROZEN = WORKSPACE / "benchmark/rift/m4/micro/frozen"
DEFAULT_ENRICHED = HERE / "bundle"
DEFAULT_MODEL_PACK = WORKSPACE / "benchmark/rift/m5/model_packs/neutral_read_arg_v1.json"
DEFAULT_EXECUTOR = WORKSPACE / "benchmark/rift/m5/model_packs/neutral_executor_capabilities.json"
DEFAULT_SCHEMA_DIR = WORKSPACE / "src/StaticAnalysis/schema"
DEFAULT_VERIFIER = WORKSPACE / "src/StaticAnalysis/tests/verify_m5_certificate.py"

ARTIFACT_NAMES = (
    "semantic_index.json",
    "ap_bindings.json",
    "contextual_influence_graph.json",
    "ap_influence_cones.json",
    "analysis_certificate.json",
    "model_fact_overlay.json",
    "predicate_occurrence_bindings.json",
    "frontier_candidates.json",
    "fuzzable_frontier.json",
    "mutation_recipes.json",
    "recipe_replay_obligations.json",
    "m5_analysis_certificate.json",
)
SEMANTIC_ARTIFACT_NAMES = tuple(
    name
    for name in ARTIFACT_NAMES
    if name not in {"analysis_certificate.json", "m5_analysis_certificate.json"}
)


class RunError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_tree(root: pathlib.Path) -> tuple[str, int]:
    """Hash a directory with length-prefixed relative names and file bytes."""
    digest = hashlib.sha256()
    files = sorted(item for item in root.rglob("*") if item.is_file())
    for path in files:
        name = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest(), len(files)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RunError(f"top-level JSON is not an object: {path}")
    return value


def write_json_atomic(path: pathlib.Path, value: Mapping[str, Any]) -> None:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
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


def checked_file(path: pathlib.Path, expected: str | None = None) -> pathlib.Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise RunError(f"not a regular file: {resolved}")
    observed = sha256_file(resolved)
    if expected is not None and observed != expected:
        raise RunError(
            f"digest mismatch for {resolved}: expected {expected}, observed {observed}"
        )
    return resolved


def checked_beneath(
    root: pathlib.Path, relative: str, expected: str | None = None
) -> pathlib.Path:
    resolved_root = root.resolve(strict=True)
    resolved = checked_file(resolved_root / relative, expected)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise RunError(f"manifest path escapes root {resolved_root}: {relative}") from error
    return resolved


def file_descriptor(result_root: pathlib.Path, path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(result_root.resolve(strict=True))
    except ValueError as error:
        raise RunError(f"frozen input is outside result root: {resolved}") from error
    return {
        "path": relative.as_posix(),
        "sha256": sha256_file(resolved),
        "byte_size": resolved.stat().st_size,
    }


def directory_descriptor(
    result_root: pathlib.Path, path: pathlib.Path
) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(result_root.resolve(strict=True))
    except ValueError as error:
        raise RunError(f"frozen directory is outside result root: {resolved}") from error
    digest, count = sha256_tree(resolved)
    return {"path": relative.as_posix(), "tree_sha256": digest, "file_count": count}


def copy_frozen(source: pathlib.Path, destination: pathlib.Path, executable: bool = False) -> pathlib.Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if executable:
        destination.chmod(0o755)
    if sha256_file(destination) != sha256_file(source):
        raise RunError(f"frozen copy digest mismatch: {source} -> {destination}")
    return destination.resolve(strict=True)


def _mount_parent_directories(paths: Iterable[pathlib.Path]) -> list[str]:
    protected = {"/usr", "/lib", "/lib64", "/bin", "/sbin", "/dev", "/proc", "/tmp"}
    result: set[str] = set()
    for item in paths:
        parent = item if item.is_dir() else item.parent
        for candidate in [parent, *parent.parents]:
            text = str(candidate)
            if text == "/" or text in protected or any(
                text.startswith(prefix + "/") for prefix in protected
            ):
                continue
            result.add(text)
    return sorted(result, key=lambda value: (value.count("/"), value))


def sandbox_argv(
    sandbox: pathlib.Path,
    logical: list[str],
    working_directory: pathlib.Path,
    writable_directory: pathlib.Path,
    readonly_files: Sequence[pathlib.Path],
) -> list[str]:
    """Build an empty-root sandbox exposing only system runtime and exact case files."""
    working_directory = working_directory.resolve(strict=True)
    writable_directory = writable_directory.resolve(strict=True)
    readonly = tuple(path.resolve(strict=True) for path in readonly_files)
    command = [
        str(sandbox),
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--clearenv",
        "--ro-bind", "/usr", "/usr",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs", "/tmp",
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "LANG", "C.UTF-8",
        "--setenv", "LC_ALL", "C.UTF-8",
        "--setenv", "LC_CTYPE", "C.UTF-8",
        "--setenv", "HOME", "/tmp",
        "--setenv", "TMPDIR", "/tmp",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
    ]
    for system_root in ("/lib", "/lib64"):
        if pathlib.Path(system_root).exists():
            command.extend(["--ro-bind", system_root, system_root])
    if pathlib.Path("/etc").exists():
        command.extend(["--dir", "/etc"])
    for system_file in ("/etc/ld.so.cache", "/etc/ld.so.conf"):
        if pathlib.Path(system_file).is_file():
            command.extend(["--ro-bind", system_file, system_file])
    if pathlib.Path("/etc/ld.so.conf.d").is_dir():
        command.extend(["--ro-bind", "/etc/ld.so.conf.d", "/etc/ld.so.conf.d"])
    for directory in _mount_parent_directories(
        [working_directory, writable_directory, *readonly]
    ):
        command.extend(["--dir", directory])
    for path in sorted(set(readonly), key=str):
        command.extend(["--ro-bind", str(path), str(path)])
    command.extend(
        [
            "--bind",
            str(writable_directory),
            str(writable_directory),
            "--chdir",
            str(working_directory),
            "--",
            *logical,
        ]
    )
    return command


def validate_public_inputs(
    frozen: pathlib.Path, enriched: pathlib.Path, expected_cases: int
) -> list[dict[str, Any]]:
    frozen_manifest = read_json(frozen / "manifest.json")
    enriched_manifest = read_json(enriched / "manifest.json")
    raw_frozen = frozen_manifest.get("cases", [])
    raw_enriched = enriched_manifest.get("cases", [])
    if not isinstance(raw_frozen, list) or not isinstance(raw_enriched, list):
        raise RunError("frozen/enriched cases must be arrays")
    frozen_cases = {str(item["case_id"]): item for item in raw_frozen}
    enriched_cases = {str(item["case_id"]): item for item in raw_enriched}
    if len(frozen_cases) != len(raw_frozen) or len(enriched_cases) != len(raw_enriched):
        raise RunError("frozen/enriched manifests contain duplicate case IDs")
    if len(frozen_cases) != expected_cases or set(frozen_cases) != set(enriched_cases):
        raise RunError("frozen/enriched case inventories differ or have the wrong size")
    if enriched_manifest.get("source_bundle", {}).get("manifest_sha256") != sha256_file(
        frozen / "manifest.json"
    ):
        raise RunError("enrichment bundle does not commit to the selected frozen manifest")
    if enriched_manifest.get("knowledge_boundary", {}).get(
        "gold_mutation_answers_used"
    ) is not False:
        raise RunError("enrichment manifest does not assert answer independence")
    records: list[dict[str, Any]] = []
    for case_id in sorted(frozen_cases):
        source = frozen_cases[case_id]
        predicate = enriched_cases[case_id]
        if predicate.get("compile_database") != source.get("compile_database"):
            raise RunError(f"{case_id}: enrichment compile-database cross-link differs")
        if predicate.get("source") != source.get("source"):
            raise RunError(f"{case_id}: enrichment source cross-link differs")
        if predicate.get("original_property_ir") != source.get("property_ir"):
            raise RunError(f"{case_id}: enrichment original-property cross-link differs")
        compile_database = checked_beneath(
            frozen, source["compile_database"]["path"],
            source["compile_database"]["sha256"],
        )
        source_file = checked_beneath(
            frozen, source["source"]["path"], source["source"]["sha256"]
        )
        property_ir = checked_beneath(
            enriched, predicate["enriched_property_ir"]["path"],
            predicate["enriched_property_ir"]["sha256"],
        )
        records.append(
            {
                "case_id": case_id,
                "compile_database": compile_database,
                "property_ir": property_ir,
                "source": source_file,
                "compile_database_relative": source["compile_database"]["path"],
                "property_ir_relative": predicate["enriched_property_ir"]["path"],
                "source_relative": source["source"]["path"],
                "compile_database_sha256": source["compile_database"]["sha256"],
                "property_ir_sha256": predicate["enriched_property_ir"]["sha256"],
                "source_sha256": source["source"]["sha256"],
            }
        )
    return records


def run_sandbox_self_test(
    *,
    sandbox: pathlib.Path,
    analyzer: pathlib.Path,
    first_record: Mapping[str, Any],
    other_record: Mapping[str, Any] | None,
    result_root: pathlib.Path,
    oracle_root: pathlib.Path,
) -> dict[str, Any]:
    """Prove that exact bindings work while host/oracle/result aliases stay hidden."""
    test_directory = result_root / "sandbox_self_test"
    test_directory.mkdir()
    result_canary = result_root / "runner_forbidden_canary.txt"
    result_canary.write_text("must not be visible in analyzer sandbox\n", encoding="utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix="rift-host-tmp-canary-")
    os.write(descriptor, b"must not be visible in analyzer sandbox\n")
    os.close(descriptor)
    host_tmp_canary = pathlib.Path(temporary_name)
    allowed_case_source = pathlib.Path(str(first_record["source"])).resolve(strict=True)
    prior_evaluation = WORKSPACE / "benchmark/rift/m4/results/micro_final_evaluation.json"
    denied = [
        oracle_root / "manifest.json",
        prior_evaluation,
        host_tmp_canary,
        result_canary,
    ]
    if other_record is not None:
        denied.append(pathlib.Path(str(other_record["source"])))
    script = """
import pathlib, sys
allowed = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
denied = [pathlib.Path(value) for value in sys.argv[3:]]
if not allowed.is_file() or not allowed.open('rb').read(1):
    raise SystemExit('allowed frozen input is not readable')
visible = [str(path) for path in denied if path.exists()]
if visible:
    raise SystemExit('forbidden host paths visible: ' + repr(visible))
output.write_text('PASS\\n', encoding='utf-8')
"""
    marker = test_directory / "sandbox_marker.txt"
    logical = [
        "/usr/bin/python3",
        "-I",
        "-c",
        script,
        str(allowed_case_source),
        str(marker),
        *(str(path) for path in denied),
    ]
    command = sandbox_argv(
        sandbox,
        logical,
        test_directory,
        test_directory,
        (analyzer, allowed_case_source),
    )
    try:
        completed = subprocess.run(
            command,
            cwd=test_directory,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0 or marker.read_text(encoding="utf-8") != "PASS\n":
            raise RunError(
                "sandbox deny self-test failed: "
                f"exit={completed.returncode} stderr={completed.stderr.strip()}"
            )
        return {
            "status": "PASS",
            "contract": "EMPTY_ROOT_EXACT_CASE_BINDINGS_PRIVATE_TMP_V1",
            "allowed_exact_file_read": True,
            "writable_exact_directory": True,
            "denied_path_classes": [
                "private_oracle",
                "prior_evaluation",
                "host_tmp",
                "unbound_result",
                "other_case_input",
            ][: len(denied)],
            "checked_denied_path_count": len(denied),
        }
    finally:
        host_tmp_canary.unlink(missing_ok=True)
        result_canary.unlink(missing_ok=True)


def compare_semantic_artifact_runs(
    reference_root: pathlib.Path,
    current_root: pathlib.Path,
    case_ids: Sequence[str],
) -> dict[str, Any]:
    """Compare deterministic semantic bytes across, e.g., jobs=1 and jobs=N runs."""
    reference = reference_root.resolve(strict=True)
    current = current_root.resolve(strict=True)
    reference_manifest = reference / "run_manifest.json"
    current_manifest = current / "run_manifest.json"

    # Byte-for-byte determinism is meaningful only when both executions used
    # the same frozen analyzer and support inputs.  In particular, recipe IDs
    # intentionally contain analyzer-core identity, so comparing two builds
    # would turn a provenance difference into a false nondeterminism report.
    if current_manifest.is_file() and not reference_manifest.is_file():
        return {
            "status": "INCOMPARABLE_MANIFEST_MISSING",
            "contract": "SEMANTIC_ARTIFACT_BYTES_EXCLUDING_CERTIFICATES_V1",
            "reference_root": str(reference),
            "reference_run_manifest_sha256": (
                sha256_file(reference_manifest) if reference_manifest.is_file() else None
            ),
            "reference_jobs": None,
            "compared_artifact_count": 0,
            "mismatch_count": 0,
            "mismatches": [],
            "identity_mismatches": [],
        }
    reference_value: dict[str, Any] | None = None
    current_value: dict[str, Any] | None = None
    identity_evidence = "NO_MANIFESTS_RAW_ARTIFACT_TEST"
    if reference_manifest.is_file():
        reference_value = read_json(reference_manifest)
        current_value = read_json(current_manifest) if current_manifest.is_file() else None

        def identity(descriptor: Any) -> tuple[str | None, int | None]:
            if not isinstance(descriptor, Mapping):
                return None, None
            digest = descriptor.get("sha256", descriptor.get("tree_sha256"))
            count = descriptor.get("file_count")
            return (None if digest is None else str(digest), count)

        reference_inputs = reference_value.get("frozen_inputs", {})
        if current_value is not None:
            current_inputs = current_value.get("frozen_inputs", {})
            identity_evidence = "BOTH_RUN_MANIFESTS"
        else:
            # execute() invokes this gate before committing the current run
            # manifest. Reconstruct the current identity from the already
            # frozen, read-only copies using the reference descriptor paths.
            current_inputs = {}
            if isinstance(reference_inputs, Mapping):
                for name, descriptor in reference_inputs.items():
                    if not isinstance(descriptor, Mapping):
                        current_inputs[name] = None
                        continue
                    relative = pathlib.PurePosixPath(str(descriptor.get("path", "")))
                    if relative.is_absolute() or ".." in relative.parts:
                        raise RunError(
                            f"invalid frozen identity path in reference manifest: {relative}"
                        )
                    candidate = (current / pathlib.Path(*relative.parts)).resolve(
                        strict=True
                    )
                    try:
                        candidate.relative_to(current)
                    except ValueError as error:
                        raise RunError(
                            f"frozen identity path escapes current run: {candidate}"
                        ) from error
                    if "tree_sha256" in descriptor:
                        digest, count = sha256_tree(candidate)
                        current_inputs[name] = {
                            "tree_sha256": digest,
                            "file_count": count,
                        }
                    else:
                        current_inputs[name] = {"sha256": sha256_file(candidate)}
            identity_evidence = "REFERENCE_MANIFEST_AND_CURRENT_FROZEN_FILES"
        identity_mismatches: list[dict[str, Any]] = []
        if not isinstance(reference_inputs, Mapping) or not isinstance(
            current_inputs, Mapping
        ):
            identity_mismatches.append(
                {
                    "input": "__frozen_inputs__",
                    "reference_identity": "VALID_MAPPING"
                    if isinstance(reference_inputs, Mapping)
                    else "MISSING_OR_INVALID",
                    "current_identity": "VALID_MAPPING"
                    if isinstance(current_inputs, Mapping)
                    else "MISSING_OR_INVALID",
                }
            )
            reference_inputs = reference_inputs if isinstance(reference_inputs, Mapping) else {}
            current_inputs = current_inputs if isinstance(current_inputs, Mapping) else {}
        if not reference_inputs or not current_inputs:
            identity_mismatches.append(
                {
                    "input": "__frozen_inputs_inventory__",
                    "reference_identity": len(reference_inputs),
                    "current_identity": len(current_inputs),
                }
            )
        for name in sorted(set(reference_inputs) | set(current_inputs)):
            reference_identity = identity(reference_inputs.get(name))
            current_identity = identity(current_inputs.get(name))
            if reference_identity != current_identity:
                identity_mismatches.append(
                    {
                        "input": name,
                        "reference_identity": reference_identity,
                        "current_identity": current_identity,
                    }
                )
        if identity_mismatches:
            return {
                "status": "INCOMPARABLE_IDENTITY_MISMATCH",
                "contract": "SEMANTIC_ARTIFACT_BYTES_EXCLUDING_CERTIFICATES_V1",
                "reference_root": str(reference),
                "reference_run_manifest_sha256": sha256_file(reference_manifest),
                "reference_jobs": reference_value.get("execution", {}).get("jobs"),
                "compared_artifact_count": 0,
                "mismatch_count": 0,
                "mismatches": [],
                "identity_mismatches": identity_mismatches,
                "identity_evidence": identity_evidence,
            }
    mismatches: list[dict[str, str]] = []
    compared = 0
    for case_id in sorted(case_ids):
        for name in SEMANTIC_ARTIFACT_NAMES:
            relative = pathlib.Path("cases") / case_id / name
            paths: list[pathlib.Path] = []
            for root in (reference, current):
                path = (root / relative).resolve(strict=True)
                try:
                    path.relative_to(root)
                except ValueError as error:
                    raise RunError(f"semantic artifact escapes run root: {path}") from error
                if not path.is_file():
                    raise RunError(f"semantic artifact is not a file: {path}")
                paths.append(path)
            reference_sha = sha256_file(paths[0])
            current_sha = sha256_file(paths[1])
            compared += 1
            if reference_sha != current_sha:
                mismatches.append(
                    {
                        "case_id": case_id,
                        "artifact": name,
                        "reference_sha256": reference_sha,
                        "current_sha256": current_sha,
                    }
                )
    reference_jobs = None
    if reference_value is not None:
        reference_jobs = reference_value.get("execution", {}).get("jobs")
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "contract": "SEMANTIC_ARTIFACT_BYTES_EXCLUDING_CERTIFICATES_V1",
        "reference_root": str(reference),
        "reference_run_manifest_sha256": (
            sha256_file(reference_manifest) if reference_manifest.is_file() else None
        ),
        "reference_jobs": reference_jobs,
        "compared_artifact_count": compared,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "identity_mismatches": [],
        "identity_evidence": identity_evidence,
    }


def run_case(
    *,
    record: Mapping[str, Any],
    analyzer: pathlib.Path,
    model_pack: pathlib.Path,
    executor: pathlib.Path,
    schema_dir: pathlib.Path,
    verifier: pathlib.Path,
    sandbox: pathlib.Path,
    result_root: pathlib.Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    case_id = str(record["case_id"])
    case_directory = result_root / "cases" / case_id
    case_directory.mkdir(parents=True, exist_ok=False)
    logical = [
        str(analyzer),
        "recipes",
        "--compile-db",
        str(record["compile_database"]),
        "--property",
        str(record["property_ir"]),
        "--model-pack",
        str(model_pack),
        "--executor-capabilities",
        str(executor),
        "--source-root",
        str(record["source_root"]),
        "--output-dir",
        str(case_directory),
    ]
    executed = sandbox_argv(
        sandbox,
        logical,
        pathlib.Path(str(record["source_root"])),
        case_directory,
        (
            analyzer,
            pathlib.Path(str(record["compile_database"])),
            pathlib.Path(str(record["property_ir"])),
            pathlib.Path(str(record["source"])),
            model_pack,
            executor,
        ),
    )
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    started = time.monotonic()
    try:
        completed = subprocess.run(
            executed,
            cwd=record["source_root"],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "case_id": case_id,
            "status": "FAIL",
            "failure": f"analyzer timeout after {timeout_seconds}s: {error}",
        }
    elapsed = time.monotonic() - started
    (case_directory / "analyzer.stdout.txt").write_text(
        completed.stdout, encoding="utf-8"
    )
    (case_directory / "analyzer.stderr.txt").write_text(
        completed.stderr, encoding="utf-8"
    )
    if completed.returncode != 0:
        return {
            "case_id": case_id,
            "status": "FAIL",
            "failure": f"analyzer exit {completed.returncode}",
            "elapsed_seconds": elapsed,
        }
    missing = [name for name in ARTIFACT_NAMES if not (case_directory / name).is_file()]
    if missing:
        return {
            "case_id": case_id,
            "status": "FAIL",
            "failure": f"missing artifacts: {missing}",
            "elapsed_seconds": elapsed,
        }
    verification_report = case_directory / "detached_verification.json"
    verification = subprocess.run(
        [
            sys.executable,
            str(verifier),
            str(case_directory / "m5_analysis_certificate.json"),
            "--schema-dir",
            str(schema_dir),
            "--report",
            str(verification_report),
        ],
        cwd=WORKSPACE,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    (case_directory / "verifier.stdout.txt").write_text(
        verification.stdout, encoding="utf-8"
    )
    (case_directory / "verifier.stderr.txt").write_text(
        verification.stderr, encoding="utf-8"
    )
    if verification.returncode != 0:
        return {
            "case_id": case_id,
            "status": "FAIL",
            "failure": f"detached verifier exit {verification.returncode}",
            "elapsed_seconds": elapsed,
        }
    report = read_json(verification_report)
    if report.get("verdict") != "PASS":
        return {
            "case_id": case_id,
            "status": "FAIL",
            "failure": "detached verifier report is not PASS",
            "elapsed_seconds": elapsed,
        }
    artifacts = {
        name: {
            "path": str((pathlib.Path("cases") / case_id / name).as_posix()),
            "sha256": sha256_file(case_directory / name),
            "byte_size": (case_directory / name).stat().st_size,
        }
        for name in ARTIFACT_NAMES
    }
    return {
        "case_id": case_id,
        "status": "PASS",
        "elapsed_seconds": elapsed,
        "input_sha256": {
            "compile_database": record["compile_database_sha256"],
            "property_ir": record["property_ir_sha256"],
            "source": record["source_sha256"],
        },
        "analyzer_exit_code": completed.returncode,
        "detached_verification": {
            "checks": report.get("checks"),
            "failures": report.get("failures"),
            "physical_files_rehashed": report.get("physical_files_rehashed"),
            "report_sha256": sha256_file(verification_report),
        },
        "artifacts": artifacts,
    }


def execute(arguments: argparse.Namespace) -> dict[str, Any]:
    output = arguments.output.resolve()
    if output.exists():
        raise RunError(f"refusing to overwrite existing output: {output}")
    if arguments.jobs < 1 or arguments.timeout < 1 or arguments.expected_cases < 1:
        raise RunError("--jobs, --timeout, and --expected-cases must be positive")
    frozen = arguments.frozen_root.resolve(strict=True)
    enriched = arguments.enriched_bundle.resolve(strict=True)
    schema_source = arguments.schema_dir.resolve(strict=True)
    if not schema_source.is_dir():
        raise RunError(f"schema directory is not a directory: {schema_source}")
    analyzer_source = checked_file(arguments.analyzer)
    model_source = checked_file(arguments.model_pack)
    executor_source = checked_file(arguments.executor_capabilities)
    verifier_source = checked_file(arguments.verifier)
    sandbox_source = checked_file(arguments.sandbox)
    records = validate_public_inputs(frozen, enriched, arguments.expected_cases)

    output.mkdir(parents=True)
    input_directory = output / "frozen_inputs"
    input_directory.mkdir()
    analyzer = copy_frozen(analyzer_source, input_directory / "tafuzz-sa", executable=True)
    model_pack = copy_frozen(model_source, input_directory / "model_pack.json")
    executor = copy_frozen(
        executor_source, input_directory / "executor_capabilities.json"
    )
    verifier = copy_frozen(
        verifier_source, input_directory / "verify_m5_certificate.py", executable=True
    )
    sandbox = copy_frozen(sandbox_source, input_directory / "bwrap", executable=True)
    schema_dir = input_directory / "schema"
    shutil.copytree(schema_source, schema_dir, copy_function=shutil.copy2)
    schema_dir = schema_dir.resolve(strict=True)
    frozen_manifest_copy = copy_frozen(
        frozen / "manifest.json", input_directory / "frozen_manifest.json"
    )
    enrichment_manifest_copy = copy_frozen(
        enriched / "manifest.json", input_directory / "enrichment_manifest.json"
    )

    staged_records: list[dict[str, Any]] = []
    for record in records:
        staged_root = output / "case_inputs" / str(record["case_id"])
        staged_frozen = staged_root / "frozen"
        staged_enriched = staged_root / "enriched"
        compile_database = copy_frozen(
            pathlib.Path(record["compile_database"]),
            staged_frozen / str(record["compile_database_relative"]),
        )
        source_file = copy_frozen(
            pathlib.Path(record["source"]),
            staged_frozen / str(record["source_relative"]),
        )
        property_ir = copy_frozen(
            pathlib.Path(record["property_ir"]),
            staged_enriched / str(record["property_ir_relative"]),
        )
        staged_records.append(
            {
                **record,
                "compile_database": compile_database,
                "source": source_file,
                "property_ir": property_ir,
                "source_root": staged_frozen.resolve(strict=True),
            }
        )
    records = staged_records

    frozen_inputs = {
        "analyzer": file_descriptor(output, analyzer),
        "model_pack": file_descriptor(output, model_pack),
        "executor_capabilities": file_descriptor(output, executor),
        "frozen_manifest": file_descriptor(output, frozen_manifest_copy),
        "enrichment_manifest": file_descriptor(output, enrichment_manifest_copy),
        "verifier": file_descriptor(output, verifier),
        "sandbox": file_descriptor(output, sandbox),
        "schema_bundle": directory_descriptor(output, schema_dir),
    }

    sandbox_self_test = run_sandbox_self_test(
        sandbox=sandbox,
        analyzer=analyzer,
        first_record=records[0],
        other_record=records[1] if len(records) > 1 else None,
        result_root=output,
        oracle_root=frozen.parent.parent.parent / "gold",
    )
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.jobs) as pool:
        futures = [
            pool.submit(
                run_case,
                record=record,
                analyzer=analyzer,
                model_pack=model_pack,
                executor=executor,
                schema_dir=schema_dir,
                verifier=verifier,
                sandbox=sandbox,
                result_root=output,
                timeout_seconds=arguments.timeout,
            )
            for record in records
        ]
        case_results = [future.result() for future in futures]
    case_results.sort(key=lambda item: item["case_id"])
    failures = [item for item in case_results if item["status"] != "PASS"]
    determinism_gate: dict[str, Any] = {
        "status": "NOT_RUN",
        "contract": "SEMANTIC_ARTIFACT_BYTES_EXCLUDING_CERTIFICATES_V1",
    }
    if not failures and arguments.determinism_reference is not None:
        determinism_gate = compare_semantic_artifact_runs(
            arguments.determinism_reference,
            output,
            [str(item["case_id"]) for item in case_results],
        )
    determinism_failed = (
        arguments.determinism_reference is not None
        and determinism_gate["status"] != "PASS"
    )
    run = {
        "schema_version": "rift.m5.micro-run.v2",
        "status": "PASS" if not failures and not determinism_failed else "FAIL",
        "knowledge_boundary": {
            "analysis_opened_private_gold": False,
            "private_gold_hidden_from_analyzer": sandbox_self_test["status"] == "PASS",
            "isolation": "EMPTY_ROOT_EXACT_CASE_BINDINGS_PRIVATE_TMP_V1",
            "model_pack_property_independent": True,
        },
        "frozen_inputs": frozen_inputs,
        "sandbox_self_test": sandbox_self_test,
        "execution": {"jobs": arguments.jobs, "timeout_seconds": arguments.timeout},
        "determinism_gate": determinism_gate,
        "expected_case_count": arguments.expected_cases,
        "completed_case_count": sum(item["status"] == "PASS" for item in case_results),
        "elapsed_seconds": time.monotonic() - started,
        "cases": case_results,
    }
    write_json_atomic(output / "run_manifest.json", run)
    if failures or determinism_failed:
        raise RunError(
            f"{len(failures)} cases failed; determinism={determinism_gate['status']}; "
            f"inspect {output / 'run_manifest.json'}"
        )
    return run


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyzer", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--frozen-root", type=pathlib.Path, default=DEFAULT_FROZEN)
    parser.add_argument("--enriched-bundle", type=pathlib.Path, default=DEFAULT_ENRICHED)
    parser.add_argument("--model-pack", type=pathlib.Path, default=DEFAULT_MODEL_PACK)
    parser.add_argument(
        "--executor-capabilities", type=pathlib.Path, default=DEFAULT_EXECUTOR
    )
    parser.add_argument("--schema-dir", type=pathlib.Path, default=DEFAULT_SCHEMA_DIR)
    parser.add_argument("--verifier", type=pathlib.Path, default=DEFAULT_VERIFIER)
    parser.add_argument("--sandbox", type=pathlib.Path, default=pathlib.Path("/usr/bin/bwrap"))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--expected-cases", type=int, default=120)
    parser.add_argument(
        "--determinism-reference",
        type=pathlib.Path,
        help="prior jobs=1 run root whose semantic artifact bytes must match",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    try:
        run = execute(parse_args(argv))
    except (OSError, KeyError, TypeError, json.JSONDecodeError, RunError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "PASS",
        f"cases={run['completed_case_count']}",
        f"elapsed_seconds={run['elapsed_seconds']:.3f}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
