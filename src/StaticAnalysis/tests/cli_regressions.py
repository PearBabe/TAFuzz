#!/usr/bin/env python3
"""Black-box CLI regressions for the M3 baseline adapter.

The fixtures are generated in an isolated temporary directory so the tests do
not depend on, or expose, the mechanical gold answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


VALID_SOURCE = """\
#include "relative_expr.h"
int evaluate_fixture(void) {
int fixture_source = 7;
int fixture_ap = RELATIVE_EXPR;
return fixture_ap;
}
"""

INVALID_SOURCE = """\
#include "intentionally_missing_rift_header.h"
int fixture_source = 7;
int fixture_ap = fixture_source;
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_input(root: Path, *, invalid: bool = False) -> Path:
    source_rel = Path("cases") / "neutral" / "fixture.c"
    source = root / source_rel
    source.parent.mkdir(parents=True)
    source.write_text(INVALID_SOURCE if invalid else VALID_SOURCE, encoding="utf-8")

    include_dir = root / "includes"
    include_dir.mkdir()
    (include_dir / "relative_expr.h").write_text(
        "#define RELATIVE_EXPR fixture_source\n", encoding="utf-8"
    )

    source_line = 2 if invalid else 3
    ap_line = 3 if invalid else 4
    payload = {
        "schema_version": "rift.analyzer-input.v1",
        "evaluation_track": "PAIR_CLASSIFICATION_DIAGNOSTIC",
        "binding_mode": "GIVEN_CANDIDATE_ANCHORS_NOT_SCORED",
        "controllability_mode": "GIVEN_CONTROLLABILITY_NOT_SCORED",
        "cases": [
            {
                "case_id": "neutral_cli_fixture",
                "source": {"file": source_rel.as_posix(), "sha256": sha256(source)},
                "compile_command": {
                    "directory": ".",
                    "arguments": [
                        "clang-18",
                        "-std=c11",
                        "-I",
                        "includes",
                        "-c",
                        source_rel.as_posix(),
                        "-o",
                        "fixture.o",
                    ],
                },
                "source_anchors": [
                    {
                        "id": "source.fixture",
                        "symbol": "fixture_source",
                        "location": {
                            "file": source_rel.as_posix(),
                            "line": source_line,
                            "column": 5,
                        },
                    }
                ],
                "ap_anchors": [
                    {
                        "id": "ap.fixture",
                        "symbol": "fixture_ap",
                        "location": {
                            "file": source_rel.as_posix(),
                            "line": ap_line,
                            "column": 5,
                        },
                    }
                ],
                "controllability": [],
            }
        ],
    }
    input_path = root / "analyzer_input.json"
    input_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return input_path


def run(
    executable: str,
    input_path: Path,
    output_path: Path,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            executable,
            "baseline",
            "--method",
            "adgfuzz-assignment",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def load_result(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"analyzer did not write {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_success(result: dict[str, Any], process: subprocess.CompletedProcess[str]) -> None:
    if process.returncode != 0:
        raise AssertionError(
            f"expected exit 0, got {process.returncode}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    if result["analysis_status"] == "ERROR":
        raise AssertionError(f"unexpected analysis error: {result}")
    prediction = result["cases"][0]["predictions"][0]
    if prediction["status"] == "ERROR" or prediction["prediction"] == "UNKNOWN":
        raise AssertionError(f"relative include was not analyzed: {prediction}")


def test_compile_directory_invariance(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="rift-cli-cwd-") as temporary:
        root = Path(temporary)
        input_path = write_input(root)
        output_path = root / "result.json"
        cwd_a = root / "run-a"
        cwd_b = root / "run-b"
        cwd_a.mkdir()
        cwd_b.mkdir()

        first_process = run(str(binary), input_path, output_path, cwd_a)
        first = load_result(output_path)
        assert_success(first, first_process)

        second_process = run(str(binary), input_path, output_path, cwd_b)
        second = load_result(output_path)
        assert_success(second, second_process)

        # Runtime receipts are expected to vary; all analysis/configuration
        # content must be independent of the caller's current directory.
        first.pop("execution")
        second.pop("execution")
        if first != second:
            raise AssertionError("analysis result depends on invocation directory")


def test_path_invocation(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="rift-cli-path-") as temporary:
        root = Path(temporary)
        input_path = write_input(root)
        output_path = root / "result.json"
        caller = root / "caller"
        caller.mkdir()
        environment = os.environ.copy()
        environment["PATH"] = str(binary.parent) + os.pathsep + environment.get("PATH", "")

        process = run(binary.name, input_path, output_path, caller, env=environment)
        result = load_result(output_path)
        assert_success(result, process)
        if result["analyzer"]["command"][0] != binary.name:
            raise AssertionError("test did not exercise basename/PATH invocation")
        if result["analyzer"]["artifact_sha256"] != sha256(binary):
            raise AssertionError("PATH invocation resolved the wrong analyzer artifact")


def test_tool_error_mapping(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="rift-cli-error-") as temporary:
        root = Path(temporary)
        input_path = write_input(root, invalid=True)
        output_path = root / "result.json"
        process = run(str(binary), input_path, output_path, root)
        result = load_result(output_path)

        if process.returncode != 1:
            raise AssertionError(f"expected exit 1 for tool error, got {process.returncode}")
        if result["analysis_status"] != "ERROR":
            raise AssertionError("tool error did not set analysis_status=ERROR")
        if result["execution"]["exit_code"] != 1:
            raise AssertionError("tool error receipt did not record exit_code=1")
        if result["execution"]["analyzed_units"] != 0:
            raise AssertionError("failed unit was counted as analyzed")
        case = result["cases"][0]
        if case["status"] != "ERROR":
            raise AssertionError("tool error did not set case status=ERROR")
        for prediction in case["predictions"]:
            if prediction["status"] != "ERROR" or prediction["prediction"] != "UNKNOWN":
                raise AssertionError(f"invalid tool-error prediction mapping: {prediction}")


def test_repeated_method_last_wins(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="rift-cli-method-") as temporary:
        root = Path(temporary)
        input_path = write_input(root)
        output_path = root / "result.json"
        process = subprocess.run(
            [
                str(binary),
                "baseline",
                "--method",
                "plain-pdg",
                "--method",
                "adgfuzz-assignment",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        result = load_result(output_path)
        assert_success(result, process)
        if result["analyzer"]["id"] != "adgfuzz-style-assignment":
            raise AssertionError("repeated --method did not use the final value")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        required=True,
        choices=(
            "compile_directory_invariance",
            "path_invocation",
            "tool_error_mapping",
            "repeated_method_last_wins",
        ),
    )
    parser.add_argument("--binary", type=Path, required=True)
    arguments = parser.parse_args()
    binary = arguments.binary.resolve(strict=True)

    tests = {
        "compile_directory_invariance": test_compile_directory_invariance,
        "path_invocation": test_path_invocation,
        "tool_error_mapping": test_tool_error_mapping,
        "repeated_method_last_wins": test_repeated_method_last_wins,
    }
    tests[arguments.mode](binary)
    print(f"PASS cli-regression={arguments.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
