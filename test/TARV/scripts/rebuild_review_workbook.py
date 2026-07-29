#!/usr/bin/env python3
"""Rebuild the review workbook after late pipeline sidecars are generated."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from run_paper_experiments import build_workbook, write_experiment_summary_files


def write_csv(path: Path, row: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def write_markdown(path: Path, row: dict[str, Any]) -> None:
    lines = [
        "# Workbook Rebuild Summary",
        "",
        "This sidecar records the final review-workbook rebuild after late pipeline diagnostics are available.",
        "",
        "| key | value |",
        "|---|---|",
    ]
    for key, value in row.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_key_value_csv(path: Path, data: dict[str, Any]) -> None:
    rows = [{"key": key, "value": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)} for key, value in data.items()]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "value"])
        writer.writeheader()
        writer.writerows(rows)


def prepare_timeout_rerun_evidence(output_dir: Path, timeout_rerun_dir: Path | None) -> dict[str, Any]:
    if not timeout_rerun_dir:
        return {
            "timeout_rerun_dir": "",
            "timeout_rerun_summary_present": False,
            "timeout_rerun_details_present": False,
        }
    summary_path = timeout_rerun_dir / "baseline_timeout_rerun_summary.json"
    details_path = timeout_rerun_dir / "baseline_timeout_rerun.csv"
    summary_present = summary_path.exists()
    details_present = details_path.exists()
    if summary_present:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        write_key_value_csv(output_dir / "timeout_rerun_summary.csv", data)
    if details_present:
        shutil.copyfile(details_path, output_dir / "timeout_rerun_details.csv")
    return {
        "timeout_rerun_dir": str(timeout_rerun_dir),
        "timeout_rerun_summary_present": summary_present,
        "timeout_rerun_details_present": details_present,
    }


def update_experiment_workbook_status(output_dir: Path, status: str, workbook: Path) -> None:
    summary_path = output_dir / "experiment_summary.json"
    if not summary_path.exists():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        return
    summary["workbook_status"] = status
    summary["workbook_path"] = str(workbook) if status == "ok" else ""
    write_experiment_summary_files(output_dir, summary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated paper experiment output directory.")
    parser.add_argument("--timeout-rerun-dir", type=Path, default=None, help="Optional timeout-rerun result directory to include in the workbook.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    timeout_rerun_status = prepare_timeout_rerun_evidence(
        output_dir,
        args.timeout_rerun_dir.resolve() if args.timeout_rerun_dir else None,
    )
    workbook = output_dir / "paper_review_results.xlsx"
    update_experiment_workbook_status(output_dir, "ok", workbook)
    status = build_workbook(output_dir, no_workbook=False)
    update_experiment_workbook_status(output_dir, status, workbook)
    blocker_csv = output_dir / "benchmark_blocker_diagnostics.csv"
    hardcoded_csv = output_dir / "monitaal_hardcoded_benchmarks.csv"
    row = {
        "output_dir": str(output_dir),
        "status": status,
        "workbook_path": str(workbook) if workbook.exists() else "",
        "benchmark_blocker_diagnostics_present": blocker_csv.exists(),
        "benchmark_blocker_sheet_expected": blocker_csv.exists(),
        "monitaal_hardcoded_benchmarks_present": hardcoded_csv.exists(),
        "monitaal_hardcoded_benchmarks_sheet_expected": hardcoded_csv.exists(),
        **timeout_rerun_status,
    }
    (output_dir / "workbook_rebuild_summary.json").write_text(
        json.dumps(row, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(output_dir / "workbook_rebuild_summary.csv", row)
    write_markdown(output_dir / "workbook_rebuild_summary.md", row)
    print(json.dumps(row, indent=2, ensure_ascii=False))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
