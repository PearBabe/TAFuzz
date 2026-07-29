#!/usr/bin/env python3

import argparse
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
MODELS = Path(__file__).resolve().parent / "cli_models"


def clean_output(output: str) -> str:
    return ANSI_ESCAPE.sub("", output).replace("\r\n", "\n")


def result_lines(output: str) -> List[str]:
    return [line.strip() for line in clean_output(output).splitlines() if line.strip()]


def run_cli(binary: Path, model: str, mode: str, timeout: float) -> str:
    model_path = MODELS / model
    if not model_path.is_file():
        raise AssertionError(f"missing CLI model: {model_path}")

    try:
        completed = subprocess.run(
            [str(binary), mode, str(model_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"CLI timed out after {timeout:g}s for {model_path.name}"
        ) from error
    except OSError as error:
        raise AssertionError(f"could not execute {binary}: {error}") from error

    stdout = clean_output(completed.stdout)
    stderr = clean_output(completed.stderr)
    if completed.returncode != 0:
        raise AssertionError(
            f"CLI exited with {completed.returncode} for {model_path.name}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )

    return stdout


def expect_results(binary: Path, model: str, expected: List[str], timeout: float) -> None:
    output = run_cli(binary, model, "-q", timeout)
    actual = result_lines(output)
    if actual != expected:
        raise AssertionError(
            f"unexpected results for {model}: expected {expected}, got {actual}\n"
            f"output:\n{output}"
        )


def expect_rejected(binary: Path, model: str, message: str, timeout: float) -> None:
    model_path = MODELS / model
    completed = subprocess.run(
        [str(binary), "-m", str(model_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = clean_output(completed.stdout + completed.stderr)
    if completed.returncode == 0 or message not in output:
        raise AssertionError(
            f"{model} should be rejected with {message!r}; exit={completed.returncode}\n"
            f"output:\n{output}"
        )


def test_interrupt_returns_unknown(binary: Path, timeout: float) -> None:
    model_path = MODELS / "backward_negative_cycle.cts"
    process = subprocess.Popen(
        [str(binary), "-m", str(model_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(min(0.25, timeout / 4))
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise AssertionError(
            "negative-cycle test exited before SIGINT\n"
            f"stdout:\n{clean_output(stdout)}\nstderr:\n{clean_output(stderr)}"
        )

    process.send_signal(signal.SIGINT)
    try:
        stdout, stderr = process.communicate(timeout=max(1.0, timeout))
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.communicate()
        raise AssertionError("backward mincost did not stop after SIGINT") from error

    output = clean_output(stdout + stderr)
    if process.returncode != 0 or "(Possible approximation)" not in output:
        raise AssertionError(
            "interrupted backward mincost must return a non-exact result\n"
            f"exit={process.returncode}\noutput:\n{output}"
        )


def test_verbose_routing(binary: Path, timeout: float) -> None:
    output = run_cli(binary, "backward_cost_five.cts", "-v", timeout)
    required = [
        "Computing zones (for backward mincost).",
        "Computing zones (for optimal control).",
    ]
    missing = [message for message in required if message not in output]
    if missing:
        raise AssertionError(
            f"verbose routing messages missing: {missing}\noutput:\n{output}"
        )

    values = [line for line in result_lines(output) if line == "5"]
    if len(values) != 3:
        raise AssertionError(
            f"verbose cost model should report three values of 5, got {len(values)}\n"
            f"output:\n{output}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regression tests for Roméo's backward mincost CLI routing."
    )
    parser.add_argument(
        "--binary",
        required=True,
        type=Path,
        help="path to the romeo-cli binary to test",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="per-process timeout in seconds (default: 10)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    binary = args.binary.expanduser().resolve()

    if not binary.is_file():
        print(f"error: binary does not exist: {binary}", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("error: --timeout must be positive", file=sys.stderr)
        return 2

    try:
        # A one-transition state has old_size == 2.  This exercises the
        # CVSClassSp projection arrays through the forward min-cost oracle.
        expect_results(
            binary,
            "forward_single_transition_cost.cts",
            ["5"],
            args.timeout,
        )
        expect_results(binary, "backward_cost_five.cts", ["5", "5", "5"], args.timeout)
        expect_results(binary, "backward_initial_goal.cts", ["0"], args.timeout)
        expect_results(binary, "backward_zero_cost.cts", ["0"], args.timeout)
        expect_results(binary, "backward_negative_cost.cts", ["-5"], args.timeout)
        expect_rejected(
            binary,
            "backward_cost_overflow.cts",
            "outside the finite DBM range",
            args.timeout,
        )
        test_interrupt_returns_unknown(binary, args.timeout)
        test_verbose_routing(binary, args.timeout)
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("PASS: backward mincost CLI regressions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
