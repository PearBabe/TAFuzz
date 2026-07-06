#!/usr/bin/env python3
"""Rerun MoniTAal baseline timeout rows with a longer per-case timeout."""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import sys
import time
from pathlib import Path
from typing import Any

from run_paper_experiments import find_monitaal_bin, parse_monitaal_verdict, run_command, write_csv


def load_timeout_rows(source: Path) -> list[dict[str, Any]]:
    baseline_csv = source / "monitaal_baseline_results.csv" if source.is_dir() else source
    with baseline_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row.get("status") == "timeout"]


def render_command(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def write_markdown(output_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    if summary["selected_timeout_rows"]:
        context = "This file records a longer-timeout rerun of MoniTAal baseline rows that timed out in the main experiment."
    else:
        context = "The source experiment currently has no MoniTAal baseline timeout rows; this empty rerun is the expected evidence."
    lines = [
        "# Baseline Timeout Rerun",
        "",
        context,
        "It is supplementary evidence only; the main TAMonitor candidate results are not modified by this rerun.",
        "",
        "## Summary",
        "",
        f"- source output: `{summary['source']}`",
        f"- retry timeout seconds: {summary['retry_timeout_seconds']}",
        f"- timeout rows selected: {summary['selected_timeout_rows']}",
        f"- rerun completed: {summary['rerun_completed']}",
        f"- rerun finished with verdict: {summary['rerun_ran']}",
        f"- rerun still timed out: {summary['rerun_timeouts']}",
        f"- MoniTAal binary: `{summary['monitaal_bin']}`",
        "",
        "## Rows",
        "",
        "| xml | templates | input | status | verdict | elapsed_ms | note |",
        "|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        templates = f"{row['positive_template']} / {row['negative_template']}"
        note = row.get("stderr_excerpt", "").replace("\n", " ").strip()
        lines.append(
            f"| `{Path(row['xml_path']).name}` | `{templates}` | `{row['input_path']}` | "
            f"`{row['status']}` | `{row['verdict']}` | {row['elapsed_ms'] or 0} | {note} |"
        )
    lines.append("")
    (output_dir / "baseline_timeout_rerun.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Experiment output directory or monitaal_baseline_results.csv.")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for rerun evidence.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-row rerun timeout in seconds.")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for quick probes; 0 means all timeout rows.")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    timeout_rows = load_timeout_rows(args.source)
    selected_rows = timeout_rows[: args.limit] if args.limit else timeout_rows
    monitaal_bin = find_monitaal_bin()

    rerun_rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for row in selected_rows:
        command: list[str] = []
        if monitaal_bin is not None:
            command = [
                str(monitaal_bin),
                "--pos", row["positive_template"], row["xml_path"],
                "--neg", row["negative_template"], row["xml_path"],
                "--input", row["input_path"],
                "--type", "concrete",
            ]
            result = run_command(command, args.timeout)
            status = "timeout" if result["timeout"] else "ran"
            verdict = parse_monitaal_verdict(result["stdout"])
        else:
            result = {"returncode": "", "stdout": "", "stderr": "MoniTAal binary unavailable.", "elapsed_ms": "", "timeout": False}
            status = "skipped_no_binary"
            verdict = ""

        rerun_rows.append({
            "xml_path": row["xml_path"],
            "positive_template": row["positive_template"],
            "negative_template": row["negative_template"],
            "input_path": row["input_path"],
            "original_timeout_stderr": row.get("stderr_excerpt", ""),
            "retry_timeout_seconds": args.timeout,
            "status": status,
            "verdict": verdict,
            "returncode": result["returncode"],
            "elapsed_ms": result["elapsed_ms"],
            "stdout_excerpt": result["stdout"][:500].replace("\n", " "),
            "stderr_excerpt": result["stderr"][:500].replace("\n", " "),
            "command": render_command(command),
        })

    summary = {
        "source": str(args.source),
        "output_dir": str(args.out),
        "retry_timeout_seconds": args.timeout,
        "available_timeout_rows": len(timeout_rows),
        "selected_timeout_rows": len(selected_rows),
        "rerun_completed": len(rerun_rows),
        "rerun_ran": sum(1 for row in rerun_rows if row["status"] == "ran"),
        "rerun_timeouts": sum(1 for row in rerun_rows if row["status"] == "timeout"),
        "rerun_skipped_no_binary": sum(1 for row in rerun_rows if row["status"] == "skipped_no_binary"),
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "monitaal_bin": str(monitaal_bin or ""),
    }

    write_csv(args.out / "baseline_timeout_rerun.csv", rerun_rows, [
        "xml_path", "positive_template", "negative_template", "input_path",
        "original_timeout_stderr", "retry_timeout_seconds", "status", "verdict",
        "returncode", "elapsed_ms", "stdout_excerpt", "stderr_excerpt", "command",
    ])
    (args.out / "baseline_timeout_rerun_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_markdown(args.out, rerun_rows, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
