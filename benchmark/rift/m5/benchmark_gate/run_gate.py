#!/usr/bin/env python3
"""Execute the independent RIFT-M5 benchmark-first gate.

This runner is an artifact harness, not part of the analyzer.  It intentionally
uses no RIFT output and has no access to M5 predictions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[4]
CFPO = ROOT / "benchmark/rift/external/cfpofuzz"
SV = ROOT / "benchmark/rift/external/sv-benchmarks"
EXPECTED_CFPO_COMMIT = "62ee6abf14e0698af15743676ea56ee4db845d0c"
EXPECTED_SV_COMMIT = "7efe28dd29576b46927b7a34e8f742bd90966a75"

BITVECTOR_TASKS = {
    "implicitfloatconversion": False,
    "implicitunsignedconversion-1": False,
    "implicitunsignedconversion-2": True,
    "integerpromotion-2": True,
    "integerpromotion-3": False,
    "signextension-1": False,
    "signextension-2": True,
    "signextension2-1": True,
    "signextension2-2": False,
}


def run(command: list[str], *, cwd: pathlib.Path | None = None,
        timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": command,
            "exit_code": None,
            "stdout": (error.stdout or "")[-4000:],
            "stderr": (error.stderr or "")[-4000:],
            "timed_out": True,
        }


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(path: pathlib.Path) -> str:
    result = run(["git", "rev-parse", "HEAD"], cwd=path)
    if result["exit_code"] != 0:
        raise RuntimeError(f"cannot resolve git commit for {path}")
    return result["stdout"].strip()


def yaml_property_verdict(path: pathlib.Path, property_name: str) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if f"/{property_name}" in line or line.strip().endswith(property_name):
            for following in lines[index + 1:index + 5]:
                match = re.search(r"expected_verdict:\s*(true|false)", following)
                if match:
                    return match.group(1) == "true"
    raise ValueError(f"missing {property_name} verdict in {path}")


def yaml_input(path: pathlib.Path) -> pathlib.Path:
    match = re.search(
        r"^input_files:\s*['\"]?([^'\"\n]+)['\"]?\s*$",
        path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if not match:
        raise ValueError(f"missing input_files in {path}")
    return path.parent / match.group(1).strip()


def compile_and_run_bitvectors(build: pathlib.Path) -> list[dict[str, Any]]:
    source_dir = SV / "c/bitvector-regression"
    results: list[dict[str, Any]] = []
    for stem, expected_safe in sorted(BITVECTOR_TASKS.items()):
        source = source_dir / f"{stem}.c"
        task = source_dir / f"{stem}.yml"
        yaml_expected = yaml_property_verdict(task, "unreach-call.prp")
        binary = build / f"bitvector-{stem}"
        compile_result = run([
            "clang-18", "-std=c11", "-O0", "-g0", str(source),
            "-o", str(binary),
        ])
        execution = (
            run([str(binary)], timeout=5)
            if compile_result["exit_code"] == 0
            else None
        )
        observed_safe = execution is not None and execution["exit_code"] == 0
        results.append({
            "task": stem,
            "source": str(source.relative_to(ROOT)),
            "source_sha256": sha256(source),
            "yaml": str(task.relative_to(ROOT)),
            "yaml_sha256": sha256(task),
            "expected_unreach_call": expected_safe,
            "yaml_expected_unreach_call": yaml_expected,
            "compile": compile_result,
            "execute": execution,
            "observed_unreach_call": observed_safe,
            "status": "PASS" if (
                expected_safe == yaml_expected
                and compile_result["exit_code"] == 0
                and observed_safe == expected_safe
            ) else "FAIL",
        })
    return results


def compile_and_run_overflow(build: pathlib.Path) -> list[dict[str, Any]]:
    task_dir = SV / "c/signedintegeroverflow-regression"
    results: list[dict[str, Any]] = []
    for task in sorted(task_dir.glob("*.yml")):
        exact_input = yaml_input(task)
        expected_safe = yaml_property_verdict(task, "no-overflow.prp")
        binary = build / f"overflow-{task.stem}"
        compile_result = run([
            "clang-18", "-x", "c", "-O0", "-g0",
            "-fsanitize=signed-integer-overflow,integer-divide-by-zero",
            "-fno-sanitize-recover=all", str(exact_input),
            "-o", str(binary),
        ])
        execution = (
            run([str(binary)], timeout=5)
            if compile_result["exit_code"] == 0
            else None
        )
        observed_safe = execution is not None and execution["exit_code"] == 0
        results.append({
            "task": task.stem,
            "source": str(exact_input.relative_to(ROOT)),
            "source_sha256": sha256(exact_input),
            "yaml": str(task.relative_to(ROOT)),
            "yaml_sha256": sha256(task),
            "expected_no_overflow": expected_safe,
            "compile": compile_result,
            "execute": execution,
            "observed_no_overflow_under_clang18_ubsan": observed_safe,
            "status": "PASS" if (
                compile_result["exit_code"] == 0
                and observed_safe == expected_safe
            ) else "FAIL",
            "claim_boundary": (
                "Concrete UBSan execution agrees with the official task; "
                "this is not a universal verification proof."
            ),
        })
    return results


def compile_control_challenges(build: pathlib.Path) -> list[dict[str, Any]]:
    task_dir = SV / "c/infeasible-control-flow"
    results: list[dict[str, Any]] = []
    for task in sorted(task_dir.glob("*.yml")):
        source = yaml_input(task)
        expected_safe = yaml_property_verdict(task, "unreach-call.prp")
        ir = build / f"control-{task.stem}.ll"
        compile_result = run([
            "clang-18", "-std=c11", "-O0", "-emit-llvm", "-S", "-c",
            str(source), "-o", str(ir),
        ])
        results.append({
            "task": task.stem,
            "source": str(source.relative_to(ROOT)),
            "source_sha256": sha256(source),
            "yaml": str(task.relative_to(ROOT)),
            "yaml_sha256": sha256(task),
            "official_expected_unreach_call": expected_safe,
            "compile_to_llvm_ir": compile_result,
            "status": "CHALLENGE_READY" if compile_result["exit_code"] == 0
                      else "FAIL",
            "verdict_reproduction": "NOT_RUN_NO_REFERENCE_VERIFIER",
            "claim_boundary": (
                "The official verdict is imported as a challenge label; "
                "successful compilation is not reported as proof."
            ),
        })
    return results


def cfpofuzz_probe() -> dict[str, Any]:
    readme = CFPO / "README.md"
    docker = shutil.which("docker")
    if docker is None:
        return {
            "status": "BLOCKED_ENVIRONMENT",
            "reason": "docker command is unavailable",
            "documented_prerequisite": "Docker and 500+ GB free disk",
        }
    probe = run([docker, "version", "--format", "{{json .Server.Version}}"])
    if probe["exit_code"] != 0:
        return {
            "status": "BLOCKED_ENVIRONMENT",
            "reason": "Docker client exists but the WSL daemon/integration is unavailable",
            "probe": probe,
            "documented_prerequisite": "Docker and 500+ GB free disk",
        }
    return {
        "status": "RUNNABLE_NOT_PULLED",
        "reason": "daemon is available; the large image was not silently pulled by this gate",
        "probe": probe,
        "readme_sha256": sha256(readme),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit(f"refusing to overwrite {arguments.output}")

    cfpo_commit = git_commit(CFPO)
    sv_commit = git_commit(SV)
    if cfpo_commit != EXPECTED_CFPO_COMMIT:
        raise SystemExit(f"unexpected CFPOFuzz commit: {cfpo_commit}")
    if sv_commit != EXPECTED_SV_COMMIT:
        raise SystemExit(f"unexpected sv-benchmarks commit: {sv_commit}")

    with tempfile.TemporaryDirectory(prefix="rift-m5-benchmark-") as temp:
        build = pathlib.Path(temp)
        bitvectors = compile_and_run_bitvectors(build)
        overflow = compile_and_run_overflow(build)
        control = compile_control_challenges(build)

    clang_version = run(["clang-18", "--version"])
    result = {
        "schema_version": "rift.m5.benchmark-gate.v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "independence": (
            "This harness consumes only upstream source/YAML and compiler "
            "outcomes; it does not read RIFT predictions."
        ),
        "upstream": {
            "cfpofuzz": {
                "commit": cfpo_commit,
                "expected_commit": EXPECTED_CFPO_COMMIT,
                "probe": cfpofuzz_probe(),
                "readme_sha256": sha256(CFPO / "README.md"),
            },
            "sv_benchmarks": {
                "tag": "svcomp26",
                "commit": sv_commit,
                "expected_commit": EXPECTED_SV_COMMIT,
            },
        },
        "toolchain": {"clang18": clang_version},
        "bitvector_execution": bitvectors,
        "signed_overflow_execution": overflow,
        "infeasible_control_flow_challenges": control,
        "summary": {
            "bitvector_pass": sum(item["status"] == "PASS" for item in bitvectors),
            "bitvector_total": len(bitvectors),
            "overflow_pass": sum(item["status"] == "PASS" for item in overflow),
            "overflow_total": len(overflow),
            "control_ready": sum(item["status"] == "CHALLENGE_READY" for item in control),
            "control_total": len(control),
            "cfpofuzz_status": cfpofuzz_probe()["status"],
        },
        "gate_status": "PASS" if (
            all(item["status"] == "PASS" for item in bitvectors)
            and all(item["status"] == "PASS" for item in overflow)
            and all(item["status"] == "CHALLENGE_READY" for item in control)
        ) else "FAIL",
        "claim_boundary": [
            "CFPOFuzz is not reproduced when its Docker prerequisite is unavailable.",
            "Concrete UBSan runs are not universal verification proofs.",
            "Control-flow YAML verdicts remain external challenge labels until a reference verifier is run.",
            "Passing this gate tests benchmark readiness, not RIFT correctness or superiority.",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], sort_keys=True))
    print(f"gate_status={result['gate_status']} output={arguments.output}")
    return 0 if result["gate_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
