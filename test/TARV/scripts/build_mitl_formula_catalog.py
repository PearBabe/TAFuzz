#!/usr/bin/env python3
"""Build a reviewable MITL formula catalog from a TAMonitor result packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"No rows to write for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def md_escape(value: Any) -> str:
    text = str(value or "")
    return text.replace("\n", "<br>").replace("|", "\\|")


def build_catalog(packet: Path, output_dir: Path) -> dict[str, Any]:
    required = [
        "semantic_cases.csv",
        "semantic_regression_results.csv",
        "benchmark_manifest.csv",
        "translation_candidate_results.csv",
        "experiment_summary.json",
    ]
    missing = [name for name in required if not (packet / name).exists()]
    if missing:
        raise RuntimeError(f"Result packet is missing required catalog inputs: {', '.join(missing)}")

    semantic_cases = {row["case_id"]: row for row in read_csv(packet / "semantic_cases.csv")}
    semantic_rows = read_csv(packet / "semantic_regression_results.csv")
    benchmark_rows = read_csv(packet / "benchmark_manifest.csv")
    candidate_rows = read_csv(packet / "translation_candidate_results.csv")
    summary = read_json(packet / "experiment_summary.json")

    semantic_catalog: list[dict[str, Any]] = []
    for row in semantic_rows:
        case = semantic_cases.get(row["case_id"], {})
        metadata_path = Path(row.get("run_dir", "")) / "metadata.json" if row.get("run_dir") else None
        metadata = read_json(metadata_path) if metadata_path and metadata_path.exists() else {}
        semantic_catalog.append({
            "group": "mighty_semantics_regression",
            "case_id": row.get("case_id", ""),
            "suite": row.get("suite", ""),
            "category": row.get("category", ""),
            "formula": case.get("formula", ""),
            "normalized_formula": metadata.get("normalized_formula", ""),
            "positive_nnf": metadata.get("positive_nnf", ""),
            "word": row.get("word", ""),
            "build_mode": row.get("build_mode", ""),
            "state": row.get("state", ""),
            "expected_final": row.get("expected_final", ""),
            "actual_final": row.get("actual_final", ""),
            "formula_satisfiable": row.get("actual_sat", ""),
            "correctness_status": row.get("correctness_status", ""),
            "oracle_type": row.get("oracle_type", ""),
            "trace_path": case.get("trace_path", ""),
            "run_dir": row.get("run_dir", ""),
        })

    xml_catalog: list[dict[str, Any]] = []
    for row in benchmark_rows:
        xml_catalog.append({
            "group": "monitaal_xml_benchmark_candidate",
            "manifest_id": row.get("manifest_id", ""),
            "xml_file": row.get("xml_file", ""),
            "xml_path": row.get("xml_path", ""),
            "positive_template": row.get("positive_template", ""),
            "negative_template": row.get("negative_template", ""),
            "candidate_mitl": row.get("candidate_mitl", "") or "<not claimed>",
            "mitl_equivalence_status": row.get("mitl_equivalence_status", ""),
            "promotion_status": row.get("promotion_status", ""),
            "candidate_confidence": row.get("candidate_confidence", ""),
            "trace_match_count": row.get("trace_match_count", ""),
            "trace_mismatch_count": row.get("trace_mismatch_count", ""),
            "baseline_timeout_count": row.get("baseline_timeout_count", ""),
            "matched_input_paths": row.get("matched_input_paths", ""),
            "blocker_or_next_step": row.get("blocker_or_next_step", ""),
            "translation_reason": row.get("translation_reason", ""),
        })

    runtime_catalog: list[dict[str, Any]] = []
    for row in semantic_catalog:
        runtime_catalog.append({
            "run_group": "semantic_regression_runtime",
            "run_id": row["case_id"],
            "formula": row["formula"],
            "source": "MightyPPL syntax/semantic regression",
            "input_or_trace": row["trace_path"],
            "word": row["word"],
            "actual_final": row["actual_final"],
            "actual_sat": row["formula_satisfiable"],
            "oracle_or_baseline": row["expected_final"],
            "comparison_status": row["correctness_status"],
            "run_dir": row["run_dir"],
        })

    for row in candidate_rows:
        runtime_catalog.append({
            "run_group": "monitaal_xml_candidate_runtime",
            "run_id": row.get("candidate_id", ""),
            "formula": row.get("candidate_mitl", ""),
            "source": (
                f"MoniTAal XML candidate {row.get('xml_file', '')}::"
                f"{row.get('positive_template', '')}/{row.get('negative_template', '')}"
            ),
            "input_or_trace": row.get("input_path", ""),
            "word": "infinite",
            "actual_final": row.get("actual_final", ""),
            "actual_sat": row.get("actual_sat", ""),
            "oracle_or_baseline": row.get("baseline_verdict", ""),
            "comparison_status": row.get("baseline_comparison_status", ""),
            "run_dir": row.get("run_dir", ""),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    semantic_csv = output_dir / "mitl_formula_catalog_semantic_regression.csv"
    xml_csv = output_dir / "mitl_formula_catalog_monitaal_xml_candidates.csv"
    runtime_csv = output_dir / "mitl_formula_catalog_runtime_runs.csv"
    markdown = output_dir / "mitl_formula_catalog_latest_official.md"

    write_csv(semantic_csv, semantic_catalog)
    write_csv(xml_csv, xml_catalog)
    write_csv(runtime_csv, runtime_catalog)

    nonempty_xml = [row for row in xml_catalog if row["candidate_mitl"] and row["candidate_mitl"] != "<not claimed>"]
    unique_semantic = sorted({row["formula"] for row in semantic_catalog if row["formula"]})
    unique_xml = sorted({row["candidate_mitl"] for row in nonempty_xml})

    lines = [
        "# MITL Formula Catalog - Latest Official TAMonitor Packet",
        "",
        f"Source packet: `{packet}`",
        "",
        "This catalog excludes internal MightyPPL compiler forms such as CFn/CGn because they are not user-level MITL formulas; those are only checked by input-policy rejection tests.",
        "",
        "## Summary",
        "",
        f"- Semantic regression runtime cases: {len(semantic_catalog)}",
        f"- Unique semantic-regression formula strings: {len(unique_semantic)}",
        f"- MoniTAal XML benchmark manifest entries: {len(xml_catalog)}",
        f"- MoniTAal XML entries with non-empty MITL candidates: {len(nonempty_xml)}",
        f"- Unique non-empty XML candidate MITL formulas: {len(unique_xml)}",
        f"- Runtime rows total: {len(runtime_catalog)} = {len(semantic_catalog)} semantic + {len(candidate_rows)} XML candidate trace runs",
        f"- CLI contract rows in source packet: {summary.get('cli_contract_rows', '')}",
        "",
        "## Generated CSV Catalogs",
        "",
        f"- `{semantic_csv}`",
        f"- `{xml_csv}`",
        f"- `{runtime_csv}`",
        "",
        "## Semantic Regression Formulas",
        "",
        "| # | case_id | category | word | formula | actual_final | correctness |",
        "|---:|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(semantic_catalog, 1):
        lines.append(
            f"| {index} | {md_escape(row['case_id'])} | {md_escape(row['category'])} | "
            f"{md_escape(row['word'])} | {md_escape(row['formula'])} | "
            f"{md_escape(row['actual_final'])} | {md_escape(row['correctness_status'])} |"
        )

    lines.extend([
        "",
        "## MoniTAal XML Benchmark MITL Candidates",
        "",
        "| # | manifest_id | xml_file | candidate_mitl | status | promotion | matches |",
        "|---:|---|---|---|---|---|---:|",
    ])
    for index, row in enumerate(xml_catalog, 1):
        lines.append(
            f"| {index} | {md_escape(row['manifest_id'])} | {md_escape(row['xml_file'])} | "
            f"{md_escape(row['candidate_mitl'])} | {md_escape(row['mitl_equivalence_status'])} | "
            f"{md_escape(row['promotion_status'])} | {md_escape(row['trace_match_count'])} |"
        )

    lines.extend([
        "",
        "## Runtime Run Catalog",
        "",
        "| # | group | run_id | formula | actual_final | oracle/baseline | comparison |",
        "|---:|---|---|---|---|---|---|",
    ])
    for index, row in enumerate(runtime_catalog, 1):
        lines.append(
            f"| {index} | {md_escape(row['run_group'])} | {md_escape(row['run_id'])} | "
            f"{md_escape(row['formula'])} | {md_escape(row['actual_final'])} | "
            f"{md_escape(row['oracle_or_baseline'])} | {md_escape(row['comparison_status'])} |"
        )
    lines.append("")
    markdown.write_text("\n".join(lines), encoding="utf-8")

    return {
        "packet": str(packet),
        "output_dir": str(output_dir),
        "semantic_rows": len(semantic_catalog),
        "semantic_unique_formulas": len(unique_semantic),
        "xml_rows": len(xml_catalog),
        "xml_nonempty_candidates": len(nonempty_xml),
        "xml_unique_candidate_formulas": len(unique_xml),
        "runtime_rows": len(runtime_catalog),
        "cli_contract_rows": summary.get("cli_contract_rows", ""),
        "files": {
            "markdown": str(markdown),
            "semantic_csv": str(semantic_csv),
            "xml_csv": str(xml_csv),
            "runtime_csv": str(runtime_csv),
        },
    }


def copy_latest(summary: dict[str, Any], latest_dir: Path) -> None:
    files = summary["files"]
    for source_key, target_name in [
        ("markdown", "mitl_formula_catalog_latest_official.md"),
        ("semantic_csv", "mitl_formula_catalog_semantic_regression.csv"),
        ("xml_csv", "mitl_formula_catalog_monitaal_xml_candidates.csv"),
        ("runtime_csv", "mitl_formula_catalog_runtime_runs.csv"),
    ]:
        source = Path(files[source_key])
        target = latest_dir / target_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True, help="TAMonitor result packet directory.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Catalog output directory. Defaults to the packet directory.")
    parser.add_argument(
        "--sync-latest",
        action="store_true",
        help="Also copy the generated catalog files to test/TARV/results as latest-official review entrypoints.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    packet = args.packet.resolve()
    output_dir = (args.out_dir or packet).resolve()
    summary = build_catalog(packet, output_dir)
    if args.sync_latest:
        latest_dir = REPO_ROOT / "test" / "TARV" / "results"
        copy_latest(summary, latest_dir)
        summary["latest_synced_to"] = str(latest_dir)
    (output_dir / "mitl_formula_catalog_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
