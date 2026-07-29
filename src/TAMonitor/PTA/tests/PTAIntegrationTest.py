#!/usr/bin/env python3
"""验证 PTA 分析为默认关闭的 TAMonitor 旁路，并检查状态/JSON 契约。"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


BASE_FILES = {"metadata.json", "results.xlsx", "steps.csv", "summary.csv"}
PTA_FILES = {"pta_analysis.json", "pta_pieces.jsonl"}
SEMANTIC_FORMULAS = {
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


def workbook_sheets(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [node.attrib["name"] for node in workbook.findall("m:sheets/m:sheet", namespace)]


def common_command(binary: Path, repo_root: Path, output: Path) -> list[str]:
    return [
        str(binary),
        "--formula",
        str(repo_root / "test/TARV/cases/smoke_f_01.mitl"),
        "--word",
        "finite",
        "--state",
        "symbolic",
        "--build-mode",
        "flatten",
        "--build-only",
        "--out",
        str(output),
    ]


def inline_analysis_command(binary: Path, formula: str, output: Path) -> list[str]:
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
        "backward",
        "--pta-verify-geometry",
        "--pta-timeout-ms",
        "30000",
        "--out",
        str(output),
    ]


def require_files(directory: Path, expected: set[str]) -> None:
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    if actual != expected:
        raise AssertionError(f"unexpected output files: actual={actual}, expected={expected}")


def validate_complete_analysis(output: Path) -> None:
    summary = json.loads((output / "pta_analysis.json").read_text(encoding="utf-8"))
    if summary["algorithm"] != "Parrot-Lime-2020-backward-weighted-zones":
        raise AssertionError("analysis algorithm identifier changed")
    if summary["target_automaton"] != "negative":
        raise AssertionError("default PTA target must be the negative automaton")
    if summary["default_location_rate"] != "1" or summary["default_edge_cost"] != "0":
        raise AssertionError("default PTA cost model must be rate=1 and edge=0")
    if summary["status"] not in {"complete", "unreachable"} or not summary["snapshot_exact"]:
        raise AssertionError(f"unexpected complete-analysis status: {summary['status']}")
    if summary["geometric_oracle"] != {"checked": True, "equal": True}:
        raise AssertionError("priced support disagrees with MoniTAal Pre*(Goal)")
    initial = summary["initial_cost"]
    if initial["kind"] == "finite" and not isinstance(initial["value"], str):
        raise AssertionError("exact finite cost must be serialized as a string")
    if initial["kind"] == "finite" and (
        initial["piece_id"] is None or initial["witness"] is None
    ):
        raise AssertionError("initial finite query lost its piece/witness guidance")

    automaton = summary["automaton"]
    if not automaton["locations"] or not automaton["edges"]:
        raise AssertionError("offline output omitted the WTA location/edge catalog")
    edge_ids = {
        (edge["id"]["source"], edge["id"]["ordinal"])
        for edge in automaton["edges"]
    }
    if len(edge_ids) != len(automaton["edges"]):
        raise AssertionError("offline EdgeId catalog is not unique")
    if any(not isinstance(edge["cost"], str) for edge in automaton["edges"]):
        raise AssertionError("exact edge costs must be serialized as strings")

    rows = [
        json.loads(line)
        for line in (output / "pta_pieces.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise AssertionError("complete analysis emitted no priced pieces")
    piece_ids = {row["piece_id"] for row in rows if row["kind"] == "finite"}
    region_ids = {
        row["region_id"] for row in rows if row["kind"] == "negative_infinity"
    }
    for row in rows:
        if row["analysis_status"] != summary["status"]:
            raise AssertionError("piece completeness metadata disagrees with summary")
        if row["snapshot_exact"] is not True:
            raise AssertionError("complete snapshot piece is not marked exact")
        for bound in row["zone"]["bounds"]:
            if not isinstance(bound["value"], str):
                raise AssertionError("exact DBM bound must be serialized as a string")
        witness = row["witness"]
        next_edge = witness["next_edge"]
        if next_edge is not None and (
            next_edge["source"], next_edge["ordinal"]
        ) not in edge_ids:
            raise AssertionError("piece witness references an unknown EdgeId")
        successor_piece = witness["successor_piece"]
        if successor_piece is not None and successor_piece not in piece_ids:
            raise AssertionError("piece witness references an unknown successor piece")
        successor_region = witness["successor_unbounded_region"]
        if successor_region is not None and successor_region not in region_ids:
            raise AssertionError("piece witness references an unknown successor region")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tamonitor", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    arguments = parser.parse_args()
    binary = arguments.tamonitor.resolve()
    repo_root = arguments.repo_root.resolve()

    with tempfile.TemporaryDirectory(prefix="tamonitor-pta-integration-") as temporary:
        root = Path(temporary)

        default_output = root / "default"
        default = run(common_command(binary, repo_root, default_output), 0)
        require_files(default_output, BASE_FILES)
        if "PTA analysis status:" in default.stdout:
            raise AssertionError("default TAMonitor unexpectedly ran PTA analysis")
        if workbook_sheets(default_output / "results.xlsx") != ["Steps", "Summary", "Metadata"]:
            raise AssertionError("default workbook sheet contract changed")

        analysis_output = root / "analysis"
        analysis_command = common_command(binary, repo_root, analysis_output)
        analysis_command.extend(
            [
                "--pta-analysis",
                "backward",
                "--pta-verify-geometry",
                "--pta-timeout-ms",
                "30000",
            ]
        )
        analysis = run(analysis_command, 0)
        require_files(analysis_output, BASE_FILES | PTA_FILES)
        if "PTA analysis status:" not in analysis.stdout:
            raise AssertionError("explicit analysis omitted its terminal status")
        validate_complete_analysis(analysis_output)
        if workbook_sheets(analysis_output / "results.xlsx") != ["Steps", "Summary", "Metadata"]:
            raise AssertionError("PTA analysis modified the original workbook")

        # 在 MightyPPL 实际生成的 future/past/binary TA 上逐一交叉检查 priced
        # support 与 MoniTAal 原生 Federation Pre*(Goal)。
        for case_name, formula in SEMANTIC_FORMULAS.items():
            semantic_output = root / f"semantic-{case_name}"
            run(inline_analysis_command(binary, formula, semantic_output), 0)
            semantic = json.loads(
                (semantic_output / "pta_analysis.json").read_text(encoding="utf-8")
            )
            if not semantic["snapshot_exact"] or semantic["geometric_oracle"] != {
                "checked": True,
                "equal": True,
            }:
                raise AssertionError(
                    f"MightyPPL {case_name} priced/geometric oracle mismatch"
                )

        analyzed = json.loads(
            (analysis_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        location_id = analyzed["automaton"]["locations"][0]["id"]
        edge_id = analyzed["automaton"]["edges"][0]["id"]
        override_model = root / "override-cost.xml"
        override_model.write_text(
            '<pta-cost-model version="1" target="negative">\n'
            '  <defaults location-rate="1" edge-cost="0"/>\n'
            f'  <location id="{location_id}" rate="2"/>\n'
            f'  <edge source="{edge_id["source"]}" ordinal="{edge_id["ordinal"]}" cost="3"/>\n'
            '</pta-cost-model>\n',
            encoding="utf-8",
        )
        override_output = root / "override-analysis"
        override_command = common_command(binary, repo_root, override_output)
        override_command.extend(
            ["--pta-analysis", "backward", "--pta-cost-model", str(override_model)]
        )
        run(override_command, 0)
        overridden = json.loads(
            (override_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if overridden["location_rate_overrides"] != [
            {"location": location_id, "rate": "2"}
        ]:
            raise AssertionError("location rate override was not preserved exactly")
        if overridden["edge_cost_overrides"] != [
            {"source": edge_id["source"], "ordinal": edge_id["ordinal"], "cost": "3"}
        ]:
            raise AssertionError("stable EdgeId cost override was not preserved exactly")

        # 负权未声明 lower-bounded 时必须落盘 ASSUMPTION_REQUIRED，并使用退出码 2。
        negative_model = root / "negative-cost.xml"
        negative_model.write_text(
            '<pta-cost-model version="1" target="negative">\n'
            '  <defaults location-rate="-1" edge-cost="0"/>\n'
            '</pta-cost-model>\n',
            encoding="utf-8",
        )
        assumption_output = root / "assumption-required"
        assumption_command = common_command(binary, repo_root, assumption_output)
        assumption_command.extend(
            ["--pta-analysis", "backward", "--pta-cost-model", str(negative_model)]
        )
        run(assumption_command, 2)
        assumption = json.loads(
            (assumption_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if assumption["status"] != "assumption_required" or assumption["snapshot_exact"]:
            raise AssertionError("negative-weight contract was reported as an exact optimum")
        if assumption["initial_cost"]["lower_bound_declared"]:
            raise AssertionError("rejected signed model falsely recorded a lower-bound declaration")

        limited_output = root / "resource-limit"
        limited_command = common_command(binary, repo_root, limited_output)
        limited_command.extend(
            ["--pta-analysis", "backward", "--pta-max-pieces", "1"]
        )
        run(limited_command, 2)
        limited = json.loads(
            (limited_output / "pta_analysis.json").read_text(encoding="utf-8")
        )
        if limited["status"] != "incomplete_resource_limit" or limited["snapshot_exact"]:
            raise AssertionError("piece limit was falsely reported as a complete optimum")

        invalid_output = root / "invalid-infinite"
        invalid_command = common_command(binary, repo_root, invalid_output)
        word_index = invalid_command.index("finite")
        invalid_command[word_index] = "infinite"
        invalid_command.extend(["--pta-analysis", "backward"])
        invalid = run(invalid_command, 1)
        if "requires --word finite" not in invalid.stderr:
            raise AssertionError("infinite-word PTA rejection lost its diagnostic")

        for invalid_value in ("-1", "10junk"):
            invalid_size = common_command(binary, repo_root, root / f"invalid-size-{invalid_value}")
            invalid_size.extend(
                ["--pta-analysis", "backward", "--pta-max-pieces", invalid_value]
            )
            malformed = run(invalid_size, 1)
            if "--pta-max-pieces" not in malformed.stderr:
                raise AssertionError("malformed PTA resource limit lost its diagnostic")

        inactive_option = common_command(binary, repo_root, root / "inactive-option")
        inactive_option.extend(["--pta-timeout-ms", "1"])
        inactive = run(inactive_option, 1)
        if "require --pta-analysis backward" not in inactive.stderr:
            raise AssertionError("inactive PTA option was silently ignored")

        typo_model = root / "typo-cost.xml"
        typo_model.write_text(
            '<pta-cost-model version="1" target="negative">\n'
            '  <defaults location-rtae="1" edge-cost="0"/>\n'
            '</pta-cost-model>\n',
            encoding="utf-8",
        )
        typo_command = common_command(binary, repo_root, root / "typo-model")
        typo_command.extend(
            ["--pta-analysis", "backward", "--pta-cost-model", str(typo_model)]
        )
        typo = run(typo_command, 1)
        if "Unknown PTA cost model attribute" not in typo.stderr:
            raise AssertionError("cost-model attribute typo was silently ignored")

    print("TAMonitor PTA integration tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
