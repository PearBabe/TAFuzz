#!/usr/bin/env python3
"""Run MoniTAal's hard-coded C++ benchmark entrypoints.

This sidecar is intentionally separate from XML-file MoniTAal-bin baselines.
It records executable benchmark evidence for MoniTAal's benchmark/main.cpp
paths, but it does not claim any XML-to-MITL equivalence.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUILD_DIR = REPO_ROOT / "tool" / "MightyPPL" / "build" / "monitaal-prefix" / "src" / "monitaal-build"
SOURCE_DIR = REPO_ROOT / "tool" / "MoniTAal"
BOUNDARY = (
    "Hard-coded MoniTAal C++ benchmark evidence; keep separate from XML-file "
    "MoniTAal-bin baselines and do not cite as XML-to-MITL equivalence proof."
)


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    family: str
    entrypoint: str
    extra_args: tuple[str, ...] = ()
    seed: int | None = None


CASES = [
    BenchmarkCase("b_live_a_freq_concrete", "b_live_a_freq", "--b-live-a-freq-con"),
    BenchmarkCase("b_live_a_freq_interval", "b_live_a_freq", "--b-live-a-freq-int"),
    BenchmarkCase("b_live_a_freq_testing", "b_live_a_freq", "--b-live-a-freq-test", seed=1),
    BenchmarkCase("gear_controller_bundle", "gear_controller", "--gear-controller"),
    BenchmarkCase("gear_controller_input_testing", "gear_controller", "--gear-controller-input", seed=1),
    BenchmarkCase("gear_controller_output_delay", "gear_controller", "--gear-controller-output", seed=1),
    BenchmarkCase("gear_controller_sim_bench", "gear_controller", "--gear-controller-sim-bench", seed=1),
]


def kill_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()


def run_command(args: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout if timeout > 0 else None)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_group(proc)
        stdout, stderr = proc.communicate()
    return {
        "args": args,
        "returncode": proc.returncode,
        "timeout": timed_out,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "stdout": stdout or "",
        "stderr": stderr or "",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def excerpt(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def parse_stdout(stdout: str) -> dict[str, str]:
    data: dict[str, str] = {}
    seed = re.search(r"Seed:\s*(\d+)", stdout)
    if seed:
        data["observed_seed"] = seed.group(1)

    monitored = re.search(r"Monitored\s+(\d+)\s+events(?:\s+in\s+(\d+)ns)?", stdout)
    if monitored:
        data["monitored_events"] = monitored.group(1)
        if monitored.group(2):
            data["total_time_ns"] = monitored.group(2)

    total = re.search(r"Time total:\s*(\d+)\s*ns", stdout)
    if total:
        data["total_time_ns"] = total.group(1)
    max_response = re.search(r"Max response time:\s*(\d+)\s*ns", stdout, re.IGNORECASE)
    if not max_response:
        max_response = re.search(r"max response:\s*(\d+)ns", stdout, re.IGNORECASE)
    if max_response:
        data["max_response_time_ns"] = max_response.group(1)
    max_states = re.search(r"Max states:\s*(\d+)", stdout, re.IGNORECASE)
    if max_states:
        data["max_states"] = max_states.group(1)
    time_horizon = re.search(r"Time Horizon:\s*(\d+)", stdout)
    if time_horizon:
        data["time_horizon"] = time_horizon.group(1)
    memory = re.search(r"Memory:\s*(\d+)", stdout)
    if memory:
        data["memory_bytes"] = memory.group(1)
    verdict_line = re.search(r"Monitor verdicts are\s*\n([A-Z_,\s]+)", stdout)
    if verdict_line:
        verdicts = [part.strip() for part in verdict_line.group(1).split(",") if part.strip()]
        data["verdicts"] = ";".join(verdicts)

    lines = [line.strip() for line in stdout.splitlines() if line.strip() and not line.startswith("Seed:")]
    if lines:
        last = lines[-1]
        parts = [part.strip() for part in last.split(",")]
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            data["monitored_events"] = parts[0]
            data["max_response_time_ns"] = parts[1]
            data["max_states"] = parts[2]
        elif len(parts) == 5 and all(part.isdigit() for part in parts[:4]):
            data["monitored_events"] = parts[0]
            data["total_time_ns"] = parts[1]
            data["max_response_time_ns"] = parts[2]
            data["max_states"] = parts[3]
            data["verdicts"] = parts[4]
    return data


def benchmark_binary(build_dir: Path) -> Path:
    return build_dir / "benchmark" / "monitaal-benchmark"


def ensure_binary(build_dir: Path, jobs: int, timeout: int, force: bool) -> tuple[Path, list[dict[str, Any]]]:
    binary = benchmark_binary(build_dir)
    commands: list[dict[str, Any]] = []
    if binary.exists() and not force:
        return binary, commands
    configure = [
        "cmake",
        "-S",
        str(SOURCE_DIR),
        "-B",
        str(build_dir),
        "-DMONITAAL_BUILD_BIN=ON",
        "-DMONITAAL_BUILD_BENCH=ON",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    commands.append(run_command(configure, REPO_ROOT, timeout))
    if commands[-1]["returncode"] != 0 or commands[-1]["timeout"]:
        return binary, commands
    build = ["cmake", "--build", str(build_dir), "--target", "monitaal-benchmark", f"-j{jobs}"]
    commands.append(run_command(build, REPO_ROOT, timeout))
    return binary, commands


def run_case(binary: Path, case: BenchmarkCase, length: int, timeout: int) -> dict[str, Any]:
    args = [str(binary), case.entrypoint, "--length", str(length), *case.extra_args]
    if case.seed is not None:
        args.extend(["--seed", str(case.seed)])
    result = run_command(args, REPO_ROOT, timeout)
    parsed = parse_stdout(result["stdout"])
    status = "timeout" if result["timeout"] else ("ran" if result["returncode"] == 0 else "error")
    parse_status = "parsed" if parsed.get("monitored_events") else "missing_metrics"
    return {
        "case_id": case.case_id,
        "benchmark_family": case.family,
        "entrypoint": case.entrypoint,
        "source_kind": "monitaal_hardcoded_cpp",
        "run_policy": "bounded_hardcoded_benchmark_entrypoint",
        "length": length,
        "seed": case.seed if case.seed is not None else "",
        "status": status,
        "parse_status": parse_status,
        "returncode": result["returncode"],
        "timeout": result["timeout"],
        "elapsed_ms": result["elapsed_ms"],
        "monitored_events": parsed.get("monitored_events", ""),
        "total_time_ns": parsed.get("total_time_ns", ""),
        "max_response_time_ns": parsed.get("max_response_time_ns", ""),
        "max_states": parsed.get("max_states", ""),
        "time_horizon": parsed.get("time_horizon", ""),
        "memory_bytes": parsed.get("memory_bytes", ""),
        "verdicts": parsed.get("verdicts", ""),
        "observed_seed": parsed.get("observed_seed", ""),
        "command": " ".join(args),
        "stdout_excerpt": excerpt(result["stdout"]),
        "stderr_excerpt": excerpt(result["stderr"]),
        "evidence_boundary": BOUNDARY,
    }


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# MoniTAal Hard-Coded Benchmarks",
        "",
        BOUNDARY,
        "",
        "## Summary",
        "",
        f"- row_count: {summary['row_count']}",
        f"- ran: {summary['ran']}",
        f"- timeout: {summary['timeout']}",
        f"- error: {summary['error']}",
        f"- parse_failed: {summary['parse_failed']}",
        "",
        "## Rows",
        "",
        "| case_id | entrypoint | status | monitored_events | max_states | verdicts |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['case_id']}` | `{row['entrypoint']}` | `{row['status']}` | "
            f"{row['monitored_events']} | {row['max_states']} | `{row['verdicts']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--length", type=int, default=20)
    parser.add_argument("--case-timeout", type=int, default=30)
    parser.add_argument("--build-timeout", type=int, default=600)
    parser.add_argument("--build-jobs", type=int, default=2)
    parser.add_argument("--force-build", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    build_dir = args.build_dir.resolve()
    binary, build_commands = ensure_binary(build_dir, args.build_jobs, args.build_timeout, args.force_build)

    rows: list[dict[str, Any]] = []
    build_ok = binary.exists() and all(not cmd["timeout"] and cmd["returncode"] == 0 for cmd in build_commands)
    if build_ok:
        for case in CASES:
            rows.append(run_case(binary, case, args.length, args.case_timeout))

    fieldnames = [
        "case_id", "benchmark_family", "entrypoint", "source_kind", "run_policy",
        "length", "seed", "status", "parse_status", "returncode", "timeout",
        "elapsed_ms", "monitored_events", "total_time_ns", "max_response_time_ns",
        "max_states", "time_horizon", "memory_bytes", "verdicts", "observed_seed",
        "command", "stdout_excerpt", "stderr_excerpt", "evidence_boundary",
    ]
    write_csv(output_dir / "monitaal_hardcoded_benchmarks.csv", rows, fieldnames)

    summary = {
        "output_dir": str(output_dir),
        "build_dir": str(build_dir),
        "benchmark_binary": str(binary),
        "binary_exists": binary.exists(),
        "build_ok": build_ok,
        "build_commands": [
            {
                "args": command["args"],
                "returncode": command["returncode"],
                "timeout": command["timeout"],
                "elapsed_ms": command["elapsed_ms"],
                "stdout_excerpt": excerpt(command["stdout"]),
                "stderr_excerpt": excerpt(command["stderr"]),
            }
            for command in build_commands
        ],
        "row_count": len(rows),
        "ran": sum(1 for row in rows if row["status"] == "ran"),
        "timeout": sum(1 for row in rows if row["status"] == "timeout"),
        "error": sum(1 for row in rows if row["status"] == "error"),
        "parse_failed": sum(1 for row in rows if row["parse_status"] != "parsed"),
        "families": sorted({row["benchmark_family"] for row in rows}),
        "entrypoints": [case.entrypoint for case in CASES],
        "evidence_boundary": BOUNDARY,
    }
    (output_dir / "monitaal_hardcoded_benchmarks.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown(output_dir / "monitaal_hardcoded_benchmarks.md", rows, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if build_ok and summary["row_count"] == len(CASES) and summary["error"] == 0 and summary["timeout"] == 0 and summary["parse_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
