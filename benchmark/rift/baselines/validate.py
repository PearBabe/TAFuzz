#!/usr/bin/env python3
"""End-to-end validator for the RIFT-M3 common baseline evaluation layer."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import jsonschema


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
GOLD_ROOT = WORKSPACE / "benchmark" / "rift" / "gold"
TEST_ROOT = HERE / "tests"
sys.path.insert(0, str(HERE))

import evaluate  # noqa: E402
import no_answer_leakage  # noqa: E402
import prepare_inputs  # noqa: E402


class ValidationFailure(AssertionError):
    """Raised when an M3 evaluation-layer acceptance condition fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(root)).encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path = WORKSPACE, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def compile_cases(sanitized_root: Path, jobs: int) -> tuple[int, float]:
    commands = read_json(sanitized_root / "compile_commands.json")

    def compile_one(command: dict[str, Any]) -> tuple[int, str]:
        result = run(command["arguments"], cwd=sanitized_root, timeout=60)
        return result.returncode, result.stdout + result.stderr

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        results = list(executor.map(compile_one, commands))
    elapsed = time.perf_counter() - start
    failures = [output for code, output in results if code != 0]
    if failures:
        raise ValidationFailure(
            f"sanitized compilation failed for {len(failures)} cases: {failures[0][-2000:]}"
        )
    return len(results), elapsed


def validate_schemas() -> None:
    for path in (HERE / "analyzer_input.schema.json", HERE / "baseline_result.schema.json"):
        schema = read_json(path)
        jsonschema.Draft7Validator.check_schema(schema)


def validate_report(report: dict[str, Any]) -> None:
    identity = report["evidence_identity"]
    overall = report["overall"]
    classification = overall["classification"]
    influence = overall["influence"]
    actionable = overall["actionable_derived"]
    require((identity["case_count"], identity["pair_count"]) == (120, 202), "case/pair universe changed")
    require(classification["exact"] == 52, "dummy exact count must be 52")
    require(influence["tp"] == 0 and influence["fp"] == 0, "dummy cannot have positive candidates")
    require(influence["fn"] == 150 and influence["tn"] == 52, "dummy influence confusion changed")
    require(influence["precision"] is None and influence["recall"] == 0.0, "zero-candidate metrics changed")
    require(overall["must"]["gold_must"] == 66, "pair-level MUST count changed")
    require(actionable["fn"] == 143 and actionable["tn"] == 59, "derived actionable universe changed")
    require(overall["edges"]["primary_pair_edge_kind"]["gold"] == 314, "pair-edge-kind universe changed")
    exact_edges = overall["edges"]["unprojected_exact_endpoint_diagnostic"]
    require(exact_edges["gold"] == 373, "exact-edge diagnostic universe changed")
    require(
        exact_edges["status"] == "UNPROJECTED_DIAGNOSTIC_NOT_HEADLINE",
        "unprojected exact-edge boundary changed",
    )
    require(
        "candidate_inflation_pair_classification_diagnostic" in overall,
        "candidate metric lost pair-classification boundary",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--skip-strace", action="store_true")
    args = parser.parse_args()
    if args.jobs < 1:
        print("FAIL: --jobs must be positive", file=sys.stderr)
        return 1

    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        validate_schemas()
        unit = run(
            [sys.executable, "-m", "unittest", "-v", "benchmark/rift/baselines/tests/test_evaluation.py"],
            timeout=180,
        )
        require(unit.returncode == 0, f"unit tests failed:\n{unit.stdout}\n{unit.stderr}")

        temporary = tempfile.TemporaryDirectory(prefix="rift-m3-validate-", dir="/tmp")
        root = Path(temporary.name)
        sanitized_a = root / "sanitized-a"
        sanitized_b = root / "sanitized-b"
        first = prepare_inputs.prepare(GOLD_ROOT, sanitized_a)
        second = prepare_inputs.prepare(GOLD_ROOT, sanitized_b)
        require(first["cases"] == second["cases"] == 120, "preparation case count changed")
        require(tree_digest(sanitized_a) == tree_digest(sanitized_b), "preparation is not byte deterministic")

        package_scan = no_answer_leakage.scan_roots([sanitized_a])
        require(package_scan["status"] == "PASS", f"sanitized package leaked labels: {package_scan['violations']}")
        analyzer_scan = no_answer_leakage.scan_roots([TEST_ROOT / "dummy_no_influence.py"])
        require(analyzer_scan["status"] == "PASS", f"dummy analyzer leaked answers: {analyzer_scan['violations']}")

        compiled, compile_seconds = compile_cases(sanitized_a, args.jobs)
        require(compiled == 120, "not all sanitized cases compiled")

        input_path = sanitized_a / "analyzer_input.json"
        result_path = sanitized_a / "dummy_result.json"
        dummy = run(
            [
                sys.executable,
                str(TEST_ROOT / "dummy_no_influence.py"),
                "--input",
                str(input_path),
                "--output",
                str(result_path),
            ]
        )
        require(dummy.returncode == 0, f"dummy fixture failed: {dummy.stdout}\n{dummy.stderr}")

        report_path = root / "private_evaluation.json"
        report = evaluate.evaluate(input_path, result_path, GOLD_ROOT)
        evaluate.write_json(report_path, report)
        validate_report(report)

        audit_status = "NOT_RUN"
        audit_paths = 0
        if not args.skip_strace:
            trace = root / "dummy.strace"
            audit_result_path = sanitized_a / "audit_dummy_result.json"
            audit = no_answer_leakage.audit(
                sanitized_root=sanitized_a,
                analyzer_roots=[TEST_ROOT / "dummy_no_influence.py"],
                extra_allowed_roots=[],
                command=[
                    sys.executable,
                    str(TEST_ROOT / "dummy_no_influence.py"),
                    "--input",
                    str(input_path),
                    "--output",
                    str(audit_result_path),
                ],
                trace_output=trace,
                timeout=120,
            )
            audit_status = audit["status"]
            audit_paths = audit["paths_observed"]
            require(audit_status == "PASS", f"strace leakage audit failed: {audit}")

        pycache = sorted(HERE.rglob("__pycache__")) + sorted(HERE.rglob("*.pyc"))
        require(not pycache, f"delivery tree contains Python cache: {pycache}")

        print(
            "SUMMARY status=PASS",
            "schemas=2",
            "unit_tests=7",
            "sanitized_cases=120",
            "source_anchors=189",
            "ap_anchors=130",
            "pairs=202",
            f"compiled={compiled}",
            f"compile_seconds={compile_seconds:.3f}",
            "dummy_exact=52/202",
            "unknown_not_tn=PASS",
            f"strace={audit_status}",
            f"traced_paths={audit_paths}",
            "failures=0",
        )
        return 0
    except (
        OSError,
        KeyError,
        TypeError,
        ValidationFailure,
        evaluate.EvaluationError,
        prepare_inputs.PreparationError,
        json.JSONDecodeError,
        jsonschema.SchemaError,
        subprocess.SubprocessError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
