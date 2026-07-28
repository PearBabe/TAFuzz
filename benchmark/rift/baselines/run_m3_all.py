#!/usr/bin/env python3
"""Run and freeze all six RIFT-M3 weak-baseline diagnostics.

All analyzer processes finish before the trusted evaluator reads the gold
corpus.  The output directory is append-free and must not already exist, so a
published run cannot be silently mixed with earlier binaries or results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[3]
EVALUATOR = Path(__file__).with_name("evaluate.py")
RESULT_SCHEMA = Path(__file__).with_name("baseline_result.schema.json")
INPUT_SCHEMA = Path(__file__).with_name("analyzer_input.schema.json")
METHODS = (
    "adgfuzz-assignment",
    "moonshine-rw",
    "plain-pdg",
    "llvm-def-use",
    "memoryssa-aa",
    "svf-value-flow",
)
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for relative in ("core", "include", "cli", "schema")
        for path in (root / relative).rglob("*")
        if path.is_file()
    )
    if not files:
        raise ValueError(f"no generic core files under {root}")
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def performance_from_time(path: Path) -> dict[str, Any]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    required = {"wall_seconds", "peak_rss_kib", "user_seconds", "system_seconds", "exit_code"}
    missing = required - set(fields)
    if missing:
        raise ValueError(f"{path} is missing GNU time fields {sorted(missing)}")
    return {
        "wall_seconds": float(fields["wall_seconds"]),
        "peak_rss_bytes": int(fields["peak_rss_kib"]) * 1024,
        "user_seconds": float(fields["user_seconds"]),
        "system_seconds": float(fields["system_seconds"]),
        "exit_code": int(fields["exit_code"]),
        "measurement_scope": "EXTERNAL_COMPLETE_PROCESS_TREE_GNU_TIME",
    }


def analyzer_command(
    time_binary: Path,
    analyzer: Path,
    method: str,
    input_path: Path,
    result_path: Path,
    time_path: Path,
) -> list[str]:
    return [
        str(time_binary),
        "-f",
        "wall_seconds=%e\npeak_rss_kib=%M\nuser_seconds=%U\nsystem_seconds=%S\nexit_code=%x",
        "-o",
        str(time_path),
        str(analyzer),
        "baseline",
        "--method",
        method,
        "--input",
        str(input_path),
        "--output",
        str(result_path),
    ]


def evaluate(input_path: Path, result_path: Path, output_path: Path) -> None:
    command = [
        sys.executable,
        str(EVALUATOR),
        "--input",
        str(input_path),
        "--result",
        str(result_path),
        "--output",
        str(output_path),
    ]
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=WORKSPACE,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"evaluator failed for {result_path.name}:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )


def summary_row(
    method: str,
    result: dict[str, Any],
    evaluation: dict[str, Any],
    performance: dict[str, Any],
) -> dict[str, Any]:
    overall = evaluation["overall"]
    influence = overall["influence"]
    must = overall["must"]
    actionable = overall["actionable_derived"]
    unsupported = overall["unsupported"]
    classification = overall["classification"]
    return {
        "method": method,
        "analysis_status": result["analysis_status"],
        "tp": influence["tp"],
        "fp": influence["fp"],
        "fn": influence["fn"],
        "tn": influence["tn"],
        "precision": influence["precision"],
        "recall": influence["recall"],
        "f1": influence["f1"],
        "must_detection_recall": must["detection_recall"],
        "exact_class_accuracy": classification["exact_accuracy_unknown_is_wrong"],
        "actionable_precision": actionable["precision"],
        "actionable_recall": actionable["recall"],
        "actionable_f1": actionable["f1"],
        "unknown_pairs": unsupported["unknown_pairs"],
        "wall_seconds_external": performance["wall_seconds"],
        "peak_rss_bytes_external": performance["peak_rss_bytes"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    arguments = parser.parse_args()

    analyzer = arguments.analyzer.resolve(strict=True)
    input_path = arguments.input.resolve(strict=True)
    output_dir = arguments.output_dir.resolve(strict=False)
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite existing output directory: {output_dir}")
    if arguments.timeout < 1:
        raise ValueError("--timeout must be positive")
    time_binary = Path("/usr/bin/time").resolve(strict=True)
    output_dir.mkdir(parents=True)

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    commands: dict[str, list[str]] = {}
    run_records: dict[str, dict[str, Any]] = {}

    # Analyzer stage: no gold/evaluator access occurs until every method has
    # finished and all six raw result files are present.
    for method in METHODS:
        result_path = output_dir / f"{method}.result.json"
        time_path = output_dir / f"{method}.time.txt"
        command = analyzer_command(
            time_binary, analyzer, method, input_path, result_path, time_path
        )
        commands[method] = command
        try:
            completed = subprocess.run(
                command,
                cwd=input_path.parent,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=arguments.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"{method} timed out after {arguments.timeout}s") from error
        if completed.returncode != 0 or not result_path.is_file():
            raise RuntimeError(
                f"{method} failed with exit {completed.returncode}:\n"
                f"{completed.stdout[-4000:]}\n{completed.stderr[-4000:]}"
            )
        performance = performance_from_time(time_path)
        if performance["exit_code"] != 0:
            raise RuntimeError(f"GNU time recorded non-zero exit for {method}")
        run_records[method] = {
            "command": command,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "performance": performance,
            "result_sha256": sha256(result_path),
            "time_sha256": sha256(time_path),
        }

    rows: list[dict[str, Any]] = []
    for method in METHODS:
        result_path = output_dir / f"{method}.result.json"
        evaluation_path = output_dir / f"{method}.evaluation.json"
        evaluate(input_path, result_path, evaluation_path)
        result = load_json(result_path)
        evaluation = load_json(evaluation_path)
        if result.get("analysis_status") == "ERROR":
            raise RuntimeError(f"{method} produced analysis_status=ERROR")
        rows.append(
            summary_row(
                method,
                result,
                evaluation,
                run_records[method]["performance"],
            )
        )
        run_records[method]["evaluation_sha256"] = sha256(evaluation_path)

    summary_path = output_dir / "summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    core_root = WORKSPACE / "src" / "StaticAnalysis"
    manifest = {
        "schema_version": "rift.m3-run.v1",
        "evaluation_track": "PAIR_CLASSIFICATION_DIAGNOSTIC",
        "candidate_binding_mode": "GIVEN_CANDIDATE_ANCHORS_NOT_SCORED",
        "controllability_mode": "GIVEN_CONTROLLABILITY_NOT_SCORED",
        "analyzer_binary": str(analyzer),
        "analyzer_binary_sha256": sha256(analyzer),
        "input_manifest": str(input_path),
        "input_manifest_sha256": sha256(input_path),
        "input_schema_sha256": sha256(INPUT_SCHEMA),
        "result_schema_sha256": sha256(RESULT_SCHEMA),
        "core_tree_sha256": core_tree_sha256(core_root),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "analyzer_stage_completed_before_evaluation": True,
        "methods": run_records,
        "summary_sha256": sha256(summary_path),
    }
    write_json(output_dir / "manifest.json", manifest)
    print(
        "PASS",
        f"methods={len(METHODS)}",
        f"binary_sha256={manifest['analyzer_binary_sha256']}",
        f"core_tree_sha256={manifest['core_tree_sha256']}",
        f"output={output_dir}",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
