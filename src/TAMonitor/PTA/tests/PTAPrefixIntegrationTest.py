#!/usr/bin/env python3
"""验证 MightyPPL finite monitor 的逐前缀 cost、witness、计时与 CLI 契约。"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


FORMULA = "!(F [5,10] p1)"
EXPECTED_COSTS = ["5", "5", "4", "2", "0"]
EXPECTED_DELAYS = ["0", "5", "4", "2", "0"]
BASE_FILES = {"metadata.json", "results.xlsx", "steps.csv", "summary.csv"}
MIXED_FILES = {
    "pta_analysis.json",
    "pta_pieces.jsonl",
    "pta_reachable_nodes.jsonl",
    "pta_reachable_arcs.jsonl",
}
PREFIX_FILES = {"pta_prefix_costs.jsonl", "pta_prefix_regions.jsonl"}


def run(command: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != expected:
        raise AssertionError(
            f"exit={completed.returncode}, expected={expected}\n"
            f"command={command!r}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def command(
    binary: Path,
    root: Path,
    output: Path,
    state: str,
    trace: Path | None = None,
) -> list[str]:
    trace = trace or root / "src/TAMonitor/PTA/tests/data/prefix_mighty.trace"
    return [
        str(binary),
        "--formula-inline", FORMULA,
        "--trace", str(trace),
        "--word", "finite",
        "--state", state,
        "--build-mode", "flatten",
        "--pta-analysis", "mixed",
        "--pta-prefix-cost",
        "--pta-prefix-query-timeout-ms", "0",
        "--pta-timeout-ms", "30000",
        "--out", str(output),
    ]


def validate(output: Path, expected_costs: list[str]) -> None:
    actual_files = {path.name for path in output.iterdir() if path.is_file()}
    expected_files = BASE_FILES | MIXED_FILES | PREFIX_FILES
    if actual_files != expected_files:
        raise AssertionError(f"prefix output set changed: {actual_files}")

    records = read_jsonl(output / "pta_prefix_costs.jsonl")
    if len(records) != 5:
        raise AssertionError("prefix0 plus four inputs were not all recorded")
    if [row["prefix_index"] for row in records] != list(range(5)):
        raise AssertionError("prefix indexes are not stable and 0-based")
    costs = [row["aggregate"]["value"] for row in records]
    if costs != expected_costs:
        raise AssertionError(f"remaining costs {costs} != {expected_costs}")
    delays = [row["delay_value_or_limit"] for row in records]
    if delays != EXPECTED_DELAYS:
        raise AssertionError(f"delay witnesses {delays} != {EXPECTED_DELAYS}")
    if any(row["domain_status"] != "complete" for row in records):
        raise AssertionError("complete trace produced an incomplete prefix query")
    if any(row["timing_and_counts"]["core_query_us"] < 0 for row in records):
        raise AssertionError("invalid per-prefix timing")
    if records[0]["next_edge"] != {"source": 0, "ordinal": 0}:
        raise AssertionError("empty prefix did not preserve its optimal initial edge")
    for row in records[1:4]:
        if row["next_edge"] != {"source": 1, "ordinal": 5}:
            raise AssertionError("runtime prefix selected the wrong Goal edge")
        if row["next_arc"] != 6 or not row["delay_attained"]:
            raise AssertionError("runtime prefix lost attained arc/delay witness")
    if records[4]["next_edge"] is not None or records[4]["next_arc"] is not None:
        raise AssertionError("first-hit Goal must not expose a next transition")
    final_locations = {state["location"] for state in records[4]["live_states"]}
    if final_locations != {3, 4}:
        raise AssertionError("Goal prefix did not preserve Goal/non-Goal live states")
    final_regions = [
        row for row in read_jsonl(output / "pta_prefix_regions.jsonl")
        if row["prefix_index"] == 4
    ]
    if len(final_regions) != 2:
        raise AssertionError("Goal prefix did not preserve all priced candidates")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tamonitor", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    binary = args.tamonitor.resolve()
    root = args.repo_root.resolve()

    with tempfile.TemporaryDirectory(prefix="tamonitor-pta-prefix-") as temp:
        temporary = Path(temp)
        symbolic = temporary / "symbolic"
        run(command(binary, root, symbolic, "symbolic"))
        validate(symbolic, EXPECTED_COSTS)

        concrete = temporary / "concrete"
        run(command(binary, root, concrete, "concrete"))
        validate(concrete, EXPECTED_COSTS)

        for backend in ("romeo-dbm", "crosscheck"):
            backend_output = temporary / backend
            backend_command = command(binary, root, backend_output, "symbolic")
            backend_command.extend(["--pta-prefix-optimizer", backend])
            run(backend_command)
            validate(backend_output, EXPECTED_COSTS)

        cost3 = temporary / "cost3"
        cost3_command = command(binary, root, cost3, "symbolic")
        cost3_command.extend([
            "--pta-cost-model",
            str(root / "src/TAMonitor/PTA/tests/data/prefix_mighty_initial_cost3.xml"),
        ])
        run(cost3_command)
        validate(cost3, ["8", "5", "4", "2", "0"])

        after_terminal_trace = temporary / "after_terminal.trace"
        after_terminal_trace.write_text(
            "0,{}\n1,{p1}\n3,{}\n5,{p1}\n6,{}\n", encoding="utf-8"
        )
        after_terminal = temporary / "after-terminal"
        run(command(
            binary, root, after_terminal, "symbolic", after_terminal_trace
        ))
        terminal_records = read_jsonl(
            after_terminal / "pta_prefix_costs.jsonl"
        )
        if (
            terminal_records[-1]["evaluation_status"]
            != "not_evaluated_monitor_terminal"
            or terminal_records[-1]["terminal_source_prefix"] != 4
        ):
            raise AssertionError("terminal trace row incorrectly repeated an old query")

        rejected = run([
            str(binary), "--formula-inline", "p1", "--word", "finite",
            "--build-mode", "flatten", "--build-only",
            "--pta-analysis", "mixed", "--pta-prefix-cost",
        ], expected=1)
        if "cannot be combined with --build-only" not in rejected.stderr:
            raise AssertionError("build-only prefix mode was not rejected explicitly")

    print("PTAPrefixIntegrationTest: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
