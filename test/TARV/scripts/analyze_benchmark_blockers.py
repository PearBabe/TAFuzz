#!/usr/bin/env python3
"""Generate review diagnostics for XML benchmark rows that are not proof-ready."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TAMONITOR = REPO_ROOT / "tool" / "MightyPPL" / "build" / "TAMonitor"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_tamonitor_probe(
    tamonitor: Path,
    formula: str,
    trace: str,
    timeout: int,
) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="tamonitor_blocker_probe.") as tmp_name:
        tmp = Path(tmp_name)
        formula_path = tmp / "formula.mitl"
        trace_path = tmp / "trace.txt"
        out_dir = tmp / "out"
        formula_path.write_text(formula + "\n", encoding="utf-8")
        trace_path.write_text(trace, encoding="utf-8")
        cmd = [
            str(tamonitor),
            "--formula",
            str(formula_path),
            "--trace",
            str(trace_path),
            "--word",
            "infinite",
            "--state",
            "symbolic",
            "--build-mode",
            "flatten",
            "--max-valuations",
            "512",
            "--out",
            str(out_dir),
        ]
        try:
            result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "TIMEOUT", "TAMonitor probe timed out."
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "").replace("\n", " ")[:300]
            return "ERROR", message
        summary_path = out_dir / "summary.csv"
        steps_path = out_dir / "steps.csv"
        final_verdict = ""
        if summary_path.exists():
            for row in read_csv(summary_path):
                if row.get("metric") == "final_verdict":
                    final_verdict = row.get("value", "")
                    break
        step_verdicts: list[str] = []
        if steps_path.exists():
            step_verdicts = [row.get("verdict", "") for row in read_csv(steps_path)]
        return final_verdict or "UNKNOWN", "steps=" + "|".join(step_verdicts)


def never_b_probe_summary(tamonitor: Path, timeout: int) -> str:
    if not tamonitor.exists():
        return "TAMonitor executable not found; static XML blocker only."
    variants = [
        ("strict_G", "(G (!b)) && (a || !a)"),
        ("weak_G_star", "(G* (!b)) && (a || !a)"),
        ("not_eventually_b", "!(F [0,infty) b)"),
    ]
    traces = [
        ("b_at_first_event", "0,{b}\n"),
        ("b_after_prefix", "0,{}\n20,{b}\n"),
    ]
    observations: list[str] = []
    for variant_id, formula in variants:
        for trace_id, trace in traces:
            verdict, detail = run_tamonitor_probe(tamonitor, formula, trace, timeout)
            observations.append(f"{variant_id}/{trace_id}:{verdict}({detail})")
    return "; ".join(observations)


def classify_blocker(row: dict[str, str], tamonitor: Path, timeout: int) -> tuple[str, str, str]:
    xml_file = row.get("xml_file", "")
    proof_status = row.get("proof_status", "")
    candidate = row.get("candidate_mitl", "")
    if xml_file == "never_b.xml":
        evidence = never_b_probe_summary(tamonitor, timeout)
        return (
            "current_event_boundary_no_candidate",
            evidence,
            "Do not promote from the file name. A proof must show a MightyPPL formula with the same first-event and later-b verdict boundaries as the MoniTAal positive/negative TA.",
        )
    if xml_file == "time-must-pass.xml":
        return (
            "time_divergence_not_trace_formula",
            "MoniTAal unit tests use this XML with time-divergence automata and no ordinary repository input trace; generated empty probes, when present, are baseline-only evidence.",
            "Keep as XML baseline-only unless a paper theorem explicitly covers time-divergence automata rather than trace-level MITL RV.",
        )
    if proof_status == "NOT_PROOF_READY_APPROXIMATE" and candidate:
        return (
            "approximate_candidate_needs_edge_proof",
            "Candidate is intentionally approximate; edge/guard proof evidence is absent in xml_edge_guard_proofs.csv.",
            "Add a formal edge/guard/reset/acceptance proof or keep excluded from formal XML-to-MITL claims.",
        )
    if proof_status == "NOT_APPLICABLE_NO_CANDIDATE":
        return (
            "no_conservative_candidate",
            "No trustworthy automatic MITL translation rule matched this positive/negative XML pair.",
            "Add a candidate only after deriving the scope, event roles, clocks, guards, resets, and accepting locations from the TA.",
        )
    return (
        "unclassified_blocker",
        "Row is not proof-ready but did not match a known diagnostic class.",
        "Inspect XML manually before changing promotion status.",
    )


def build_rows(output_dir: Path, tamonitor: Path, timeout: int) -> list[dict[str, Any]]:
    proof_rows = read_csv(output_dir / "xml_edge_guard_proofs.csv")
    manifest_rows = {
        row.get("manifest_id", ""): row
        for row in read_csv(output_dir / "benchmark_manifest.csv")
    }
    rows: list[dict[str, Any]] = []
    for proof_row in proof_rows:
        if proof_row.get("proof_status") == "EDGE_GUARD_PROOF_READY":
            continue
        manifest_id = proof_row.get("manifest_id", "")
        manifest_row = manifest_rows.get(manifest_id, {})
        blocker_class, evidence, action = classify_blocker(proof_row, tamonitor, timeout)
        rows.append({
            "blocker_id": "BLOCKER_" + manifest_id,
            "manifest_id": manifest_id,
            "xml_file": proof_row.get("xml_file", ""),
            "source_kind": proof_row.get("source_kind", ""),
            "promotion_status": proof_row.get("promotion_status", ""),
            "proof_status": proof_row.get("proof_status", ""),
            "candidate_mitl": proof_row.get("candidate_mitl", ""),
            "blocker_class": blocker_class,
            "diagnostic_evidence": evidence,
            "current_packet_status": manifest_row.get("promotion_status", ""),
            "recommended_action": action,
            "must_not_claim": "Do not count this row as a proved XML-to-MITL translation or runtime correctness match until the blocker is resolved.",
        })
    return rows


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["blocker_class"] for row in rows)
    lines = [
        "# Benchmark Blocker Diagnostics",
        "",
        "This sidecar explains why non-proof-ready MoniTAal XML rows remain excluded from formal XML-to-MITL claims.",
        "It is diagnostic evidence for human review; it does not override the hashed pipeline artifact manifest.",
        "",
        "## Counts",
        "",
    ]
    for key, count in sorted(counts.items()):
        lines.append(f"- `{key}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| blocker_id | xml_file | blocker_class | promotion_status | recommended_action |",
        "|---|---|---|---|---|",
    ])
    for row in rows:
        action = str(row["recommended_action"]).replace("|", "\\|")
        lines.append(
            f"| `{row['blocker_id']}` | `{row['xml_file']}` | `{row['blocker_class']}` | "
            f"`{row['promotion_status']}` | {action} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated paper experiment output directory.")
    parser.add_argument("--tamonitor", type=Path, default=DEFAULT_TAMONITOR, help="TAMonitor executable for optional blocker probes.")
    parser.add_argument("--timeout", type=int, default=30, help="Per TAMonitor probe timeout.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    rows = build_rows(output_dir, args.tamonitor.resolve(), args.timeout)
    fieldnames = [
        "blocker_id",
        "manifest_id",
        "xml_file",
        "source_kind",
        "promotion_status",
        "proof_status",
        "candidate_mitl",
        "blocker_class",
        "diagnostic_evidence",
        "current_packet_status",
        "recommended_action",
        "must_not_claim",
    ]
    write_csv(output_dir / "benchmark_blocker_diagnostics.csv", rows, fieldnames)
    (output_dir / "benchmark_blocker_diagnostics.json").write_text(
        json.dumps({
            "output_dir": str(output_dir),
            "rows": rows,
            "row_count": len(rows),
            "blocker_class_counts": dict(Counter(row["blocker_class"] for row in rows)),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown(output_dir / "benchmark_blocker_diagnostics.md", rows)
    print(json.dumps({
        "output_dir": str(output_dir),
        "row_count": len(rows),
        "blocker_class_counts": dict(Counter(row["blocker_class"] for row in rows)),
        "csv": str(output_dir / "benchmark_blocker_diagnostics.csv"),
        "json": str(output_dir / "benchmark_blocker_diagnostics.json"),
        "md": str(output_dir / "benchmark_blocker_diagnostics.md"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
