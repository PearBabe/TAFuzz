#!/usr/bin/env python3
"""验证 MightyPPL 实际 TA 上的 exact mixed CLI、非零 cost 与离线图契约。"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


BASE_FILES = {"metadata.json", "results.xlsx", "steps.csv", "summary.csv"}
MIXED_FILES = {
    "pta_analysis.json",
    "pta_pieces.jsonl",
    "pta_reachable_nodes.jsonl",
    "pta_reachable_arcs.jsonl",
}
FORMULA = "!(F [5,10] p1)"
SEMANTIC_FORMULAS = {
    "future": "F [0,2] p1",
    "globally": "G [0,2] p1",
    "until": "p1 U [1,3] p2",
    "once": "O [0,2] p1",
    "historically": "H [0,2] p1",
    "since": "p1 S [0,3] p2",
}


def run(command: list[str], expected_code: int) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != expected_code:
        raise AssertionError(
            f"exit={completed.returncode}, expected={expected_code}\n"
            f"command={command!r}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def runtime_base_command(binary: Path, repo_root: Path, output: Path) -> list[str]:
    return [
        str(binary),
        "--formula-inline",
        FORMULA,
        "--trace",
        str(repo_root / "test/TARV/cases/smoke_f_01.trace"),
        "--word",
        "finite",
        "--state",
        "symbolic",
        "--build-mode",
        "flatten",
        "--out",
        str(output),
    ]


def command(binary: Path, repo_root: Path, output: Path, mode: str) -> list[str]:
    return runtime_base_command(binary, repo_root, output) + [
        "--pta-analysis",
        mode,
        "--pta-verify-geometry",
        "--pta-timeout-ms",
        "30000",
    ]


def semantic_command(binary: Path, formula: str, output: Path) -> list[str]:
    return [
        str(binary),
        "--formula-inline",
        formula,
        "--word",
        "finite",
        "--state",
        "symbolic",
        "--build-mode",
        "flatten",
        "--build-only",
        "--pta-analysis",
        "mixed",
        "--pta-verify-geometry",
        "--pta-timeout-ms",
        "30000",
        "--out",
        str(output),
    ]


def final_verdict(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("Final verdict: "):
            return line.removeprefix("Final verdict: ")
    raise AssertionError("TAMonitor stdout omitted Final verdict")


def require_files(directory: Path, expected: set[str]) -> None:
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    if actual != expected:
        raise AssertionError(f"unexpected files: actual={actual}, expected={expected}")


def json_lines(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def workbook_sheets(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [node.attrib["name"] for node in workbook.findall("m:sheets/m:sheet", namespace)]


def validate_exact_mixed(output: Path) -> dict:
    summary = json.loads((output / "pta_analysis.json").read_text(encoding="utf-8"))
    if summary["schema_version"] != 2 or summary["algorithm"] != (
        "Romeo-style-exact-mixed-forward-backward-weighted-zones"
    ):
        raise AssertionError("mixed schema/algorithm identifier mismatch")
    if summary["goal_semantics"] != "first_hit_terminal":
        raise AssertionError("mixed output did not declare Goal cutoff semantics")
    if summary["target_automaton"] != "negative":
        raise AssertionError("mixed default target is not the negative TA")
    if summary["status"] != "complete" or summary["snapshot_exact"] is not True:
        raise AssertionError(f"mixed analysis was not exact: {summary['status']}")
    if summary["forward"]["status"] != "complete" or not summary["forward"]["exact"]:
        raise AssertionError("exact forward graph was not completed")
    if summary["backward"]["status"] != "complete" or not summary["backward"]["exact"]:
        raise AssertionError("priced backward fixed point was not completed")
    if summary["geometric_oracle"] != {"checked": True, "equal": True}:
        raise AssertionError("mixed support != Reach intersect MoniTAal Pre*(Goal)")
    if summary["observer_oracle"] != {
        "checked": True,
        "strict_bound_unreachable": True,
        "bound_reachable": True,
    }:
        raise AssertionError("MightyPPL nonzero observer-clock oracle failed")
    initial = summary["initial_cost"]
    if initial["reachable_domain"] != "reachable" or initial["kind"] != "finite":
        raise AssertionError("mixed initial state did not get a finite reachable cost")
    if initial["value"] != "5" or not initial["attained"] or not initial["exact"]:
        raise AssertionError(f"expected exact attained initial cost 5, got {initial}")
    if initial["reachable_node_id"] is None or initial["next_arc_id"] is None:
        raise AssertionError("initial mixed query lost graph-node/arc guidance")

    nodes = json_lines(output / "pta_reachable_nodes.jsonl")
    arcs = json_lines(output / "pta_reachable_arcs.jsonl")
    pieces = json_lines(output / "pta_pieces.jsonl")
    if len(nodes) != summary["forward"]["nodes"] or len(arcs) != summary["forward"]["arcs"]:
        raise AssertionError("reachable JSONL counts disagree with summary")
    if not nodes or not arcs or not pieces:
        raise AssertionError("mixed analysis omitted nodes/arcs/priced pieces")
    node_ids = {node["node_id"] for node in nodes}
    arc_ids = {arc["arc_id"] for arc in arcs}
    arcs_by_id = {arc["arc_id"]: arc for arc in arcs}
    if len(node_ids) != len(nodes) or len(arc_ids) != len(arcs):
        raise AssertionError("reachable NodeId/ArcId values are not unique")
    goal_nodes = {node["node_id"] for node in nodes if node["goal"]}
    if any(arc["source_node"] in goal_nodes for arc in arcs):
        raise AssertionError("Goal cutoff node unexpectedly has an outgoing arc")
    for arc in arcs:
        if arc["source_node"] not in node_ids or arc["target_node"] not in node_ids:
            raise AssertionError("arc references an unknown graph node")
        for field in ("fire_zone", "entry_zone", "post_zone"):
            if not isinstance(arc[field]["bounds"], list):
                raise AssertionError(f"arc omitted exact {field}")
    piece_ids = {piece["piece_id"] for piece in pieces if piece["kind"] == "finite"}
    region_ids = {
        piece["region_id"] for piece in pieces if piece["kind"] == "negative_infinity"
    }
    for piece in pieces:
        if piece["reachable_node_id"] not in node_ids:
            raise AssertionError("priced piece references an unknown graph node")
        witness = piece["witness"]
        next_arc = witness["next_arc"]
        if next_arc is not None and next_arc not in arc_ids:
            raise AssertionError("priced witness references an unknown graph arc")
        successor_node = witness["successor_node"]
        if successor_node is not None and successor_node not in node_ids:
            raise AssertionError("priced witness references an unknown successor node")
        if next_arc is not None:
            arc = arcs_by_id[next_arc]
            if arc["source_node"] != piece["reachable_node_id"]:
                raise AssertionError("next arc does not leave the piece graph node")
            if successor_node is not None and arc["target_node"] != successor_node:
                raise AssertionError("next arc target disagrees with successor node")
        successor_piece = witness["successor_piece"]
        if successor_piece is not None and successor_piece not in piece_ids:
            raise AssertionError("witness references an unknown successor piece")
        successor_region = witness["successor_unbounded_region"]
        if successor_region is not None and successor_region not in region_ids:
            raise AssertionError("witness references an unknown successor region")
    return summary


def write_all_initial_edge_costs(summary: dict, path: Path) -> list[tuple[int, int]]:
    initial_location = summary["automaton"]["initial_location"]
    initial_edges = [
        (edge["id"]["source"], edge["id"]["ordinal"])
        for edge in summary["automaton"]["edges"]
        if edge["source"] == initial_location
    ]
    if not initial_edges:
        raise AssertionError("MightyPPL generated TA has no initial outgoing edge")
    if len(initial_edges) != 2:
        raise AssertionError(
            "runtime MightyPPL oracle expected two initial valuation-labelled edges"
        )
    lines = [
        '<pta-cost-model version="1" target="negative">',
        '  <defaults location-rate="1" edge-cost="0"/>',
    ]
    lines.extend(
        f'  <edge source="{source}" ordinal="{ordinal}" cost="3"/>'
        for source, ordinal in initial_edges
    )
    lines.append("</pta-cost-model>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return initial_edges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tamonitor", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    arguments = parser.parse_args()
    binary = arguments.tamonitor.resolve()
    repo_root = arguments.repo_root.resolve()

    with tempfile.TemporaryDirectory(prefix="tamonitor-pta-mixed-") as temporary:
        root = Path(temporary)

        default_output = root / "default"
        default_run = run(
            runtime_base_command(binary, repo_root, default_output), 0
        )
        require_files(default_output, BASE_FILES)
        if workbook_sheets(default_output / "results.xlsx") != [
            "Steps",
            "Summary",
            "Metadata",
        ]:
            raise AssertionError("default workbook sheet contract changed")

        mixed_output = root / "mixed"
        mixed_run = run(command(binary, repo_root, mixed_output, "mixed"), 0)
        require_files(mixed_output, BASE_FILES | MIXED_FILES)
        summary = validate_exact_mixed(mixed_output)
        if workbook_sheets(mixed_output / "results.xlsx") != [
            "Steps",
            "Summary",
            "Metadata",
        ]:
            raise AssertionError("mixed analysis modified the original workbook")

        pure_output = root / "pure"
        pure_run = run(command(binary, repo_root, pure_output, "backward"), 0)
        require_files(
            pure_output,
            BASE_FILES | {"pta_analysis.json", "pta_pieces.jsonl"},
        )
        pure = json.loads((pure_output / "pta_analysis.json").read_text(encoding="utf-8"))
        if pure["schema_version"] != 1 or pure["initial_cost"]["value"] != "5":
            raise AssertionError("pure backward compatibility/nonzero comparison failed")
        if not (
            final_verdict(default_run.stdout)
            == final_verdict(pure_run.stdout)
            == final_verdict(mixed_run.stdout)
        ):
            raise AssertionError("optional PTA mode changed the online verdict")

        for case_name, formula in SEMANTIC_FORMULAS.items():
            semantic_output = root / f"semantic-{case_name}"
            run(semantic_command(binary, formula, semantic_output), 0)
            require_files(semantic_output, BASE_FILES | MIXED_FILES)
            semantic = json.loads(
                (semantic_output / "pta_analysis.json").read_text(encoding="utf-8")
            )
            if not semantic["snapshot_exact"] or semantic["geometric_oracle"] != {
                "checked": True,
                "equal": True,
            }:
                raise AssertionError(
                    f"MightyPPL mixed {case_name} Reach/intersect/Pre oracle failed"
                )

        cost_model = root / "initial-edge-costs.xml"
        initial_edges = write_all_initial_edge_costs(summary, cost_model)
        cost_output = root / "mixed-cost-three"
        cost_command = command(binary, repo_root, cost_output, "mixed")
        cost_command.extend(["--pta-cost-model", str(cost_model)])
        run(cost_command, 0)
        cost_summary = json.loads(
            (cost_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if cost_summary["initial_cost"]["value"] != "8":
            raise AssertionError(
                "adding cost 3 to every initial outgoing edge did not change 5 to 8"
            )
        serialized_edges = {
            (entry["source"], entry["ordinal"], entry["cost"])
            for entry in cost_summary["edge_cost_overrides"]
        }
        if serialized_edges != {(source, ordinal, "3") for source, ordinal in initial_edges}:
            raise AssertionError("stable initial EdgeId cost overrides were not preserved")
        if cost_summary["observer_oracle"]["checked"]:
            raise AssertionError("observer-only time oracle must skip nonzero edge costs")

        forward_limited_output = root / "forward-limited"
        forward_limited = command(
            binary, repo_root, forward_limited_output, "mixed"
        )
        forward_limited.extend(["--pta-max-reach-nodes", "1"])
        run(forward_limited, 2)
        limited_summary = json.loads(
            (forward_limited_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if limited_summary["status"] != "incomplete_forward_resource_limit":
            raise AssertionError("forward node limit was not phase-labelled")
        if (
            limited_summary["snapshot_exact"]
            or limited_summary["backward"]["started"]
            or limited_summary["backward"]["status"] != "not_run_incomplete_forward"
            or limited_summary["backward"]["accepted"] != 0
        ):
            raise AssertionError("incomplete forward unexpectedly started exact backward")
        if limited_summary["initial_cost"]["kind"] != "unknown":
            raise AssertionError("partial forward graph emitted a pseudo-optimal cost")

        backward_limited_output = root / "backward-limited"
        backward_limited = command(
            binary, repo_root, backward_limited_output, "mixed"
        )
        backward_limited.extend(["--pta-max-pieces", "1"])
        run(backward_limited, 2)
        backward_summary = json.loads(
            (backward_limited_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if backward_summary["status"] != "incomplete_backward_resource_limit":
            raise AssertionError("backward piece limit was not phase-labelled")
        if (
            not backward_summary["backward"]["started"]
            or backward_summary["backward"]["status"] != "incomplete_resource_limit"
            or backward_summary["backward"]["exact"]
        ):
            raise AssertionError("backward phase completeness metadata is inconsistent")
        if backward_summary["initial_cost"]["kind"] != "unknown":
            raise AssertionError("partial backward fixed point emitted a pseudo-optimal cost")

        timeout_output = root / "timeout-limited"
        timeout_command = command(binary, repo_root, timeout_output, "mixed")
        timeout_index = timeout_command.index("30000")
        timeout_command[timeout_index] = "1"
        run(timeout_command, 2)
        timeout_summary = json.loads(
            (timeout_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if timeout_summary["status"] not in {
            "incomplete_forward_resource_limit",
            "incomplete_backward_resource_limit",
        }:
            raise AssertionError("mixed timeout was not reported as a phased limit")
        if timeout_summary["snapshot_exact"] or timeout_summary["initial_cost"][
            "kind"
        ] != "unknown":
            raise AssertionError("mixed timeout emitted a pseudo-optimal result")

        negative_model = root / "negative-rate.xml"
        negative_model.write_text(
            '<pta-cost-model version="1" target="negative">\n'
            '  <defaults location-rate="-1" edge-cost="0"/>\n'
            '</pta-cost-model>\n',
            encoding="utf-8",
        )
        assumption_output = root / "assumption-required"
        assumption_command = command(binary, repo_root, assumption_output, "mixed")
        assumption_command.extend(["--pta-cost-model", str(negative_model)])
        run(assumption_command, 2)
        assumption = json.loads(
            (assumption_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if (
            assumption["status"] != "assumption_required"
            or assumption["snapshot_exact"]
            or assumption["backward"]["started"]
            or assumption["backward"]["status"] != "not_run_assumption_required"
            or assumption["initial_cost"]["kind"] != "unknown"
        ):
            raise AssertionError("mixed signed-cost lower-bound contract was violated")

        invalid_output = root / "pure-with-reach-limit"
        invalid = command(binary, repo_root, invalid_output, "backward")
        invalid.extend(["--pta-max-reach-nodes", "10"])
        rejected = run(invalid, 1)
        if "require --pta-analysis mixed" not in rejected.stderr:
            raise AssertionError("mixed-only reachability limit was accepted by pure backward")

        infinite_output = root / "invalid-infinite"
        infinite = command(binary, repo_root, infinite_output, "mixed")
        infinite[infinite.index("finite")] = "infinite"
        rejected_infinite = run(infinite, 1)
        if "--pta-analysis mixed requires --word finite" not in rejected_infinite.stderr:
            raise AssertionError("mixed infinite-word rejection lost its diagnostic")

    print("TAMonitor mixed PTA integration tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
