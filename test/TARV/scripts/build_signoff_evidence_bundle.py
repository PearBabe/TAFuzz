#!/usr/bin/env python3
"""Build a reviewer-facing evidence bundle for Review Signoff rows.

The bundle is generated evidence only. It joins each signoff row to its
human-review queue row, generated source row, and evidence artifacts so a
reviewer can inspect the packet without manually chasing every cross-reference.
It never fills reviewer decisions and never claims human mathematical approval.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]

SOURCE_ROW_RULES = [
    ("GOAL_", [("goal_completion_audit.csv", "goal_id")]),
    ("MANUAL_", [("manual_review_checklist.csv", "review_id")]),
    ("XML_PROOF_", [("xml_proof_appendix.csv", "manifest_id"), ("xml_edge_guard_proofs.csv", "manifest_id")]),
    ("XML_ORIGINAL_TRACE_GAP_", [("xml_original_trace_gaps.csv", "gap_id")]),
    ("PAPER_CLAIM_", [("paper_claim_review.csv", "manifest_id"), ("paper_claim_consistency_audit.csv", "manifest_id")]),
    ("BENCHMARK_", [("benchmark_manifest.csv", "manifest_id")]),
]

KNOWN_WORKBOOK_SHEETS = {
    "Summary",
    "Review Guide",
    "Review Queue",
    "Review Signoff",
    "Signoff Validation",
    "Signoff Roundtrip",
    "Signoff Evidence",
    "Goal Audit",
    "Manual Review",
    "Correctness Audit",
    "Prefix Oracle",
    "Oracle Derivations",
    "Manual Oracle Guide",
    "Semantic Results",
    "Semantic Cases",
    "Semantic Exclusions",
    "Syntax Coverage",
    "Input Policy",
    "CLI Contract",
    "XML Inventory",
    "Translation Review",
    "Benchmark Manifest",
    "XML Edge Proofs",
    "XML Proof Appendix",
    "XML Obligations",
    "XML Trace Coverage",
    "Original Trace Gaps",
    "Paper Claim Review",
    "Claim Audit",
    "Requirements Audit",
    "Repro Manifest",
    "Transition Details",
    "Candidate Results",
    "Candidate Step Audit",
    "Baseline Results",
    "Timeout Rerun Summary",
    "Timeout Rerun",
    "Embedded Benchmarks",
    "Hardcoded Benchmarks",
    "Benchmark Blockers",
}

SUMMARY_COLUMNS = [
    "status",
    "automatic_status",
    "review_status",
    "claim_status",
    "claim_strength",
    "appendix_status",
    "proof_status",
    "audit_status",
    "translation_status",
    "pass_status",
    "correctness_status",
    "baseline_comparison_status",
    "priority",
    "formula",
    "mitl_formula",
    "candidate_formula",
    "xml_file",
    "positive_id",
    "negative_id",
    "matched_verdicts",
    "evidence_summary",
    "gap_or_risk",
    "review_action",
    "next_action",
    "must_not_claim",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def split_semicolon_tokens(value: str) -> list[str]:
    return [token.strip() for token in value.split(";") if token.strip()]


def truncate(value: Any, limit: int = 500) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def source_row_specs(queue_id: str) -> list[tuple[str, str]]:
    for prefix, specs in SOURCE_ROW_RULES:
        if queue_id.startswith(prefix):
            return specs
    return []


def evidence_token_resolves(output_dir: Path, token: str) -> bool:
    if not token:
        return False
    if token in KNOWN_WORKBOOK_SHEETS:
        return True
    if token.startswith("glob:"):
        pattern = token[len("glob:"):].strip()
        return bool(pattern) and any(output_dir.glob(pattern))
    candidates = [output_dir / token, REPO_ROOT / token]
    if token.startswith("/"):
        candidates.append(Path(token))
    return any(path.exists() for path in candidates)


def load_source_rows(output_dir: Path, queue_id: str, source_id: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for file_name, column in source_row_specs(queue_id):
        path = output_dir / file_name
        if not path.exists():
            continue
        for row in read_csv(path):
            if row.get(column, "") == source_id:
                summary = {
                    key: truncate(row.get(key, ""), 240)
                    for key in SUMMARY_COLUMNS
                    if row.get(key, "")
                }
                matches.append({
                    "file": file_name,
                    "id_column": column,
                    "source_id": source_id,
                    "summary": summary,
                })
    return matches


def source_excerpt(source_rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in source_rows:
        parts.append(
            f"{item['file']}:{item['id_column']}="
            + json.dumps(item["summary"], ensure_ascii=False, sort_keys=True)
        )
    return truncate(" | ".join(parts), 1600)


def build_bundle(output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signoff_rows = read_csv(output_dir / "review_signoff_template.csv")
    queue_rows = {
        row.get("queue_id", ""): row
        for row in read_csv(output_dir / "human_review_queue.csv")
        if row.get("queue_id", "")
    }
    bundle_rows: list[dict[str, Any]] = []

    for signoff in signoff_rows:
        queue_id = signoff.get("queue_id", "")
        queue = queue_rows.get(queue_id, {})
        source_id = signoff.get("source_id", "")
        source_rows = load_source_rows(output_dir, queue_id, source_id)
        evidence_tokens = split_semicolon_tokens(signoff.get("evidence_artifacts", ""))
        unresolved_tokens = [
            token for token in evidence_tokens
            if not evidence_token_resolves(output_dir, token)
        ]
        required_context_missing = [
            field for field in ["review_focus", "blocking_claim", "must_not_claim", "next_action"]
            if not signoff.get(field, "").strip()
        ]
        issues: list[str] = []
        if not queue:
            issues.append("missing_queue_row")
        if not source_rows:
            issues.append("missing_source_row")
        if unresolved_tokens:
            issues.append("unresolved_evidence_tokens")
        if required_context_missing:
            issues.append("missing_required_context")

        reviewer_decision = signoff.get("reviewer_decision", "")
        bundle_rows.append({
            "signoff_id": signoff.get("signoff_id", ""),
            "queue_id": queue_id,
            "priority": signoff.get("priority", ""),
            "review_status": signoff.get("review_status", ""),
            "recommended_decision": signoff.get("recommended_decision", ""),
            "decision_allowed": signoff.get("decision_allowed", ""),
            "reviewer_decision_state": "blank" if not reviewer_decision.strip() else "filled",
            "bundle_status": "PASS" if not issues else "FAIL",
            "issues": ";".join(issues),
            "source_sheet": signoff.get("source_sheet", ""),
            "source_id": source_id,
            "source_row_count": len(source_rows),
            "source_files": ";".join(item["file"] for item in source_rows),
            "source_excerpt": source_excerpt(source_rows),
            "evidence_token_count": len(evidence_tokens),
            "unresolved_evidence_tokens": ";".join(unresolved_tokens),
            "evidence_artifacts": signoff.get("evidence_artifacts", ""),
            "review_focus": signoff.get("review_focus", "") or queue.get("review_focus", ""),
            "evidence_summary": queue.get("evidence_summary", ""),
            "blocking_claim": signoff.get("blocking_claim", ""),
            "must_not_claim": signoff.get("must_not_claim", ""),
            "next_action": signoff.get("next_action", ""),
            "reviewer_boundary": "Generated evidence bundle only; reviewer_decision remains human-owned.",
        })

    counts = Counter(row["bundle_status"] for row in bundle_rows)
    blank_decisions = sum(1 for row in bundle_rows if row["reviewer_decision_state"] == "blank")
    nonblank_decisions = len(bundle_rows) - blank_decisions
    summary = {
        "output_dir": str(output_dir),
        "row_count": len(bundle_rows),
        "pass": counts.get("PASS", 0),
        "fail": counts.get("FAIL", 0),
        "warn": counts.get("WARN", 0),
        "signoff_rows": len(signoff_rows),
        "queue_rows": len(queue_rows),
        "blank_decisions": blank_decisions,
        "nonblank_decisions": nonblank_decisions,
        "missing_queue_rows": sum(1 for row in bundle_rows if "missing_queue_row" in row["issues"].split(";")),
        "missing_source_rows": sum(1 for row in bundle_rows if "missing_source_row" in row["issues"].split(";")),
        "unresolved_evidence_tokens": sum(1 for row in bundle_rows if row["unresolved_evidence_tokens"]),
        "generated_only": True,
        "human_signoff_claim": "not_claimed",
    }
    return bundle_rows, summary


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# Review Signoff Evidence Bundle",
        "",
        "This generated bundle joins Review Signoff rows with their queue row, source row, and evidence references.",
        "It is designed for human review convenience and does not record human approval.",
        "",
        "## Summary",
        "",
        f"- rows: {summary['row_count']}",
        f"- PASS: {summary['pass']}",
        f"- FAIL: {summary['fail']}",
        f"- blank_decisions: {summary['blank_decisions']}",
        f"- generated_only: `{summary['generated_only']}`",
        f"- human_signoff_claim: `{summary['human_signoff_claim']}`",
        "",
        "## Rows",
        "",
        "| signoff_id | status | decision | source | issue | focus |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        focus = truncate(row["review_focus"], 180).replace("|", "\\|")
        source = f"{row['source_id']} ({row['source_row_count']} rows)".replace("|", "\\|")
        issues = row["issues"] or "none"
        lines.append(
            f"| `{row['signoff_id']}` | `{row['bundle_status']}` | `{row['recommended_decision']}` | "
            f"{source} | {issues} | {focus} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated review packet directory.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    rows, summary = build_bundle(output_dir)
    fieldnames = [
        "signoff_id",
        "queue_id",
        "priority",
        "review_status",
        "recommended_decision",
        "decision_allowed",
        "reviewer_decision_state",
        "bundle_status",
        "issues",
        "source_sheet",
        "source_id",
        "source_row_count",
        "source_files",
        "source_excerpt",
        "evidence_token_count",
        "unresolved_evidence_tokens",
        "evidence_artifacts",
        "review_focus",
        "evidence_summary",
        "blocking_claim",
        "must_not_claim",
        "next_action",
        "reviewer_boundary",
    ]
    write_csv(output_dir / "review_signoff_evidence_bundle.csv", rows, fieldnames)
    write_json(output_dir / "review_signoff_evidence_bundle.json", {"summary": summary, "rows": rows})
    write_markdown(output_dir / "review_signoff_evidence_bundle.md", rows, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
