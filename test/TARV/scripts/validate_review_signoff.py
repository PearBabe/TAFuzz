#!/usr/bin/env python3
"""Validate TAMonitor review signoff state.

The default `pre-review` mode checks that the generated signoff template is
structurally complete and intentionally blank. `complete` mode is for a future
human-filled workbook/export and requires reviewer decisions.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[3]


ALLOWED_DECISIONS = {
    "APPROVE_AS_CLAIMED",
    "APPROVE_WITH_CAVEAT",
    "REJECT_OR_FIX",
    "DEFER_TO_V2",
    "KEEP_EXCLUDED",
}

REQUIRED_SIGNOFF_COLUMNS = [
    "signoff_id",
    "queue_id",
    "priority",
    "source_sheet",
    "source_id",
    "review_status",
    "signoff_required",
    "decision_allowed",
    "recommended_decision",
    "forbidden_decisions",
    "completion_requirements",
    "reviewer_decision",
    "reviewer",
    "review_date",
    "reviewer_notes",
    "evidence_artifacts",
    "review_focus",
    "blocking_claim",
    "must_not_claim",
    "next_action",
]

REQUIRED_QUEUE_COLUMNS = [
    "queue_id",
    "priority",
    "source_sheet",
    "source_id",
    "review_status",
    "human_decision_required",
    "review_focus",
    "evidence_summary",
    "evidence_artifacts",
    "blocking_claim",
    "must_not_claim",
    "next_action",
]

SOURCE_ROW_RULES = [
    ("GOAL_", [("goal_completion_audit.csv", "goal_id")]),
    ("MANUAL_", [("manual_review_checklist.csv", "review_id")]),
    ("XML_PROOF_", [("xml_proof_appendix.csv", "manifest_id"), ("xml_edge_guard_proofs.csv", "manifest_id")]),
    ("XML_ORIGINAL_TRACE_GAP_", [("xml_original_trace_gaps.csv", "gap_id")]),
    ("PAPER_CLAIM_", [("paper_claim_review.csv", "manifest_id"), ("paper_claim_consistency_audit.csv", "manifest_id")]),
    ("BENCHMARK_", [("benchmark_manifest.csv", "manifest_id")]),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_check(
    rows: list[dict[str, str]],
    check_id: str,
    category: str,
    status: str,
    expected: str,
    observed: str,
    evidence_artifacts: str,
    reviewer_action: str,
    completion_state: str,
) -> None:
    rows.append({
        "check_id": check_id,
        "category": category,
        "status": status,
        "expected": expected,
        "observed": observed,
        "evidence_artifacts": evidence_artifacts,
        "reviewer_action": reviewer_action,
        "completion_state": completion_state,
    })


def priority_requires_signoff(priority: str) -> bool:
    return priority.startswith("P0") or priority.startswith("P1") or priority.startswith("P2")


def blank(value: str | None) -> bool:
    return not (value or "").strip()


def split_allowed(decision_allowed: str) -> set[str]:
    return {part.strip() for part in decision_allowed.split("|") if part.strip()}


def split_evidence_artifacts(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def split_source_sheets(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def workbook_sheet_names(output_dir: Path) -> set[str]:
    workbook = output_dir / "paper_review_results.xlsx"
    if not workbook.exists():
        return set()
    try:
        with zipfile.ZipFile(workbook) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8", errors="replace")
        root = ET.fromstring(workbook_xml)
        return {
            element.attrib.get("name", "")
            for element in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
            if element.attrib.get("name")
        }
    except Exception:
        return set()


def evidence_token_resolves(output_dir: Path, workbook_sheets: set[str], token: str) -> bool:
    if not token:
        return False
    if token in workbook_sheets:
        return True
    if token.startswith("glob:"):
        pattern = token[len("glob:"):].strip()
        return bool(pattern) and any(output_dir.glob(pattern))

    candidates = [output_dir / token, REPO_ROOT / token]
    if "/" in token and not token.startswith("/"):
        candidates.append(REPO_ROOT / token)
    if token.startswith("/"):
        candidates.append(Path(token))
    return any(path.exists() for path in candidates)


def path_label(output_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(output_dir).as_posix()
    except ValueError:
        return str(path)


def source_row_specs(queue_id: str) -> list[tuple[str, str]]:
    for prefix, specs in SOURCE_ROW_RULES:
        if queue_id.startswith(prefix):
            return specs
    return []


def build_source_row_index(output_dir: Path) -> dict[tuple[str, str], set[str]]:
    index: dict[tuple[str, str], set[str]] = {}
    for _, specs in SOURCE_ROW_RULES:
        for file_name, column in specs:
            key = (file_name, column)
            if key in index:
                continue
            path = output_dir / file_name
            if not path.exists():
                index[key] = set()
                continue
            index[key] = {row.get(column, "") for row in read_csv(path) if row.get(column, "")}
    return index


def signoff_decision_policy(row: dict[str, str]) -> dict[str, str]:
    priority = row.get("priority", "")
    review_status = row.get("review_status", "")
    source_sheet = row.get("source_sheet", "")
    must_not_claim = row.get("must_not_claim", "").lower()

    if "Original Trace Gaps" in source_sheet or "generated review traces" in must_not_claim or "original benchmark evidence" in must_not_claim:
        return {
            "recommended_decision": "APPROVE_WITH_CAVEAT",
            "forbidden_decisions": "APPROVE_AS_CLAIMED",
            "completion_requirements": "Record reviewer, date, and notes confirming the exact original-input provenance caveat or the decisive original trace that closes this gap.",
        }
    if review_status == "V1_DEFERRED" or "DEFERRED" in priority:
        return {
            "recommended_decision": "DEFER_TO_V2",
            "forbidden_decisions": "APPROVE_AS_CLAIMED | APPROVE_WITH_CAVEAT",
            "completion_requirements": "Record reviewer, date, and notes explaining the v2 algorithm or oracle suite required before this can become a v1 claim.",
        }
    if (
        review_status == "PASS_WITH_CAVEAT"
        or "CAVEAT" in priority
        or "timeout" in must_not_claim
        or "inconclusive" in must_not_claim
        or "third-valued" in must_not_claim
        or "original-input benchmark coverage" in must_not_claim
        or "original trace gaps" in must_not_claim
    ):
        return {
            "recommended_decision": "APPROVE_WITH_CAVEAT",
            "forbidden_decisions": "APPROVE_AS_CLAIMED",
            "completion_requirements": "Record reviewer, date, and notes naming the exact caveat that must remain in paper text or appendix wording.",
        }
    if review_status in {"BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF", "PROOF_DRAFT_READY"}:
        return {
            "recommended_decision": "APPROVE_AS_CLAIMED",
            "forbidden_decisions": "",
            "completion_requirements": "Record reviewer, date, and notes confirming the linked proof/claim evidence and any caveat needed for the final wording.",
        }
    if review_status == "REVIEW_REQUIRED" or "XML" in source_sheet or "Claim" in source_sheet:
        return {
            "recommended_decision": "APPROVE_WITH_CAVEAT",
            "forbidden_decisions": "",
            "completion_requirements": "Record reviewer, date, and notes summarizing the manual evidence checked before promoting, caveating, rejecting, deferring, or excluding the row.",
        }
    return {
        "recommended_decision": "APPROVE_AS_CLAIMED",
        "forbidden_decisions": "",
        "completion_requirements": "Record reviewer, date, and notes tying the decision to the linked evidence artifacts.",
    }


def validate(output_dir: Path, mode: str, signoff_csv: Path | None = None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    queue_path = output_dir / "human_review_queue.csv"
    signoff_path = signoff_csv or output_dir / "review_signoff_template.csv"
    signoff_artifact = path_label(output_dir, signoff_path)
    rows: list[dict[str, str]] = []

    queue_rows = read_csv(queue_path) if queue_path.exists() else []
    signoff_rows = read_csv(signoff_path) if signoff_path.exists() else []
    completion_state = "READY_FOR_HUMAN_REVIEW_NOT_SIGNED"
    workbook_sheets = workbook_sheet_names(output_dir)
    source_index = build_source_row_index(output_dir)

    add_check(
        rows,
        "SIGNOFF_FILES_PRESENT",
        "artifact_presence",
        "PASS" if queue_path.exists() and signoff_path.exists() else "FAIL",
        "human_review_queue.csv and signoff CSV exist",
        f"queue_exists={queue_path.exists()}; signoff_exists={signoff_path.exists()}",
        f"human_review_queue.csv; {signoff_artifact}",
        "Regenerate the review packet if either file is missing.",
        completion_state,
    )

    signoff_columns = list(signoff_rows[0].keys()) if signoff_rows else []
    queue_columns = list(queue_rows[0].keys()) if queue_rows else []
    missing_signoff_columns = [column for column in REQUIRED_SIGNOFF_COLUMNS if column not in signoff_columns]
    missing_queue_columns = [column for column in REQUIRED_QUEUE_COLUMNS if column not in queue_columns]
    add_check(
        rows,
        "SIGNOFF_REQUIRED_COLUMNS",
        "schema",
        "PASS" if not missing_signoff_columns and not missing_queue_columns else "FAIL",
        "required queue and signoff columns are present",
        f"missing_signoff={';'.join(missing_signoff_columns)}; missing_queue={';'.join(missing_queue_columns)}",
        f"human_review_queue.csv; {signoff_artifact}",
        "Do not use a signoff sheet with missing review columns.",
        completion_state,
    )

    queue_by_id = {row.get("queue_id", ""): row for row in queue_rows}
    signoff_by_queue = {row.get("queue_id", ""): row for row in signoff_rows}
    expected_queue_ids = {row.get("queue_id", "") for row in queue_rows if priority_requires_signoff(row.get("priority", ""))}
    actual_queue_ids = set(signoff_by_queue)
    missing_queue_ids = sorted(expected_queue_ids - actual_queue_ids)
    extra_queue_ids = sorted(actual_queue_ids - expected_queue_ids)
    add_check(
        rows,
        "SIGNOFF_QUEUE_COVERAGE",
        "coverage",
        "PASS" if not missing_queue_ids and not extra_queue_ids and len(signoff_rows) == len(expected_queue_ids) else "FAIL",
        "signoff rows cover exactly all P0/P1/P2 review queue rows",
        f"expected={len(expected_queue_ids)}; actual={len(signoff_rows)}; missing={';'.join(missing_queue_ids)}; extra={';'.join(extra_queue_ids)}",
        f"human_review_queue.csv; {signoff_artifact}",
        "Fix queue/signoff generation before asking for human signoff.",
        completion_state,
    )

    bad_priorities = [row.get("signoff_id", "") for row in signoff_rows if not priority_requires_signoff(row.get("priority", ""))]
    missing_required_flag = [row.get("signoff_id", "") for row in signoff_rows if row.get("signoff_required") != "true"]
    add_check(
        rows,
        "SIGNOFF_PRIORITY_AND_REQUIRED_FLAGS",
        "schema",
        "PASS" if not bad_priorities and not missing_required_flag else "FAIL",
        "all signoff rows are P0/P1/P2 and signoff_required=true",
        f"bad_priority={';'.join(bad_priorities)}; missing_required={';'.join(missing_required_flag)}",
        signoff_artifact,
        "Only paper-facing P0/P1/P2 rows should require signoff.",
        completion_state,
    )

    bad_allowed_rows: list[str] = []
    invalid_decision_rows: list[str] = []
    nonblank_decision_rows: list[str] = []
    blank_decision_rows: list[str] = []
    missing_reviewer_rows: list[str] = []
    missing_notes_rows: list[str] = []
    missing_evidence_rows: list[str] = []
    missing_queue_evidence_rows: list[str] = []
    policy_mismatch_rows: list[str] = []
    forbidden_decision_rows: list[str] = []
    unresolved_evidence_tokens: list[str] = []
    unresolved_queue_evidence_tokens: list[str] = []
    unresolved_source_sheet_tokens: list[str] = []
    unresolved_source_rows: list[str] = []
    unresolved_queue_source_sheet_tokens: list[str] = []
    unresolved_queue_source_rows: list[str] = []
    queue_mismatch_rows: list[str] = []

    for row in signoff_rows:
        signoff_id = row.get("signoff_id", "")
        queue_row = queue_by_id.get(row.get("queue_id", ""))
        if queue_row and any(row.get(key, "") != queue_row.get(key, "") for key in [
            "priority",
            "source_sheet",
            "source_id",
            "review_status",
            "review_focus",
            "evidence_artifacts",
            "blocking_claim",
            "must_not_claim",
            "next_action",
        ]):
            queue_mismatch_rows.append(signoff_id)

        if split_allowed(row.get("decision_allowed", "")) != ALLOWED_DECISIONS:
            bad_allowed_rows.append(signoff_id)

        policy = signoff_decision_policy(row)
        policy_fields = ["recommended_decision", "forbidden_decisions", "completion_requirements"]
        if any(row.get(field, "") != policy[field] for field in policy_fields):
            policy_mismatch_rows.append(signoff_id)

        decision = row.get("reviewer_decision", "").strip()
        if decision:
            nonblank_decision_rows.append(signoff_id)
            if decision not in ALLOWED_DECISIONS:
                invalid_decision_rows.append(signoff_id)
            if decision in split_allowed(row.get("forbidden_decisions", "")):
                forbidden_decision_rows.append(signoff_id)
            if blank(row.get("reviewer")) or blank(row.get("review_date")):
                missing_reviewer_rows.append(signoff_id)
            if blank(row.get("reviewer_notes")):
                missing_notes_rows.append(signoff_id)
        else:
            blank_decision_rows.append(signoff_id)

        if blank(row.get("evidence_artifacts")) or blank(row.get("review_focus")) or blank(row.get("must_not_claim")) or blank(row.get("next_action")):
            missing_evidence_rows.append(signoff_id)
        for token in split_evidence_artifacts(row.get("evidence_artifacts", "")):
            if not evidence_token_resolves(output_dir, workbook_sheets, token):
                unresolved_evidence_tokens.append(f"{signoff_id}:{token}")
        for sheet_name in split_source_sheets(row.get("source_sheet", "")):
            if sheet_name not in workbook_sheets:
                unresolved_source_sheet_tokens.append(f"{signoff_id}:{sheet_name}")
        specs = source_row_specs(row.get("queue_id", ""))
        source_id = row.get("source_id", "")
        if not specs:
            unresolved_source_rows.append(f"{signoff_id}:no_rule:{row.get('queue_id', '')}")
        elif not any(source_id in source_index.get(spec, set()) for spec in specs):
            expected = "|".join(f"{file_name}:{column}" for file_name, column in specs)
            unresolved_source_rows.append(f"{signoff_id}:{source_id}:{expected}")

    for row in queue_rows:
        queue_id = row.get("queue_id", "") or "<missing-queue-id>"
        if (
            blank(row.get("evidence_artifacts"))
            or blank(row.get("evidence_summary"))
            or blank(row.get("review_focus"))
            or blank(row.get("must_not_claim"))
            or blank(row.get("next_action"))
        ):
            missing_queue_evidence_rows.append(queue_id)
        for token in split_evidence_artifacts(row.get("evidence_artifacts", "")):
            if not evidence_token_resolves(output_dir, workbook_sheets, token):
                unresolved_queue_evidence_tokens.append(f"{queue_id}:{token}")
        source_sheets = split_source_sheets(row.get("source_sheet", ""))
        if not source_sheets:
            unresolved_queue_source_sheet_tokens.append(f"{queue_id}:<blank>")
        for sheet_name in source_sheets:
            if sheet_name not in workbook_sheets:
                unresolved_queue_source_sheet_tokens.append(f"{queue_id}:{sheet_name}")
        specs = source_row_specs(queue_id)
        source_id = row.get("source_id", "")
        if not specs:
            unresolved_queue_source_rows.append(f"{queue_id}:no_rule:{queue_id}")
        elif not source_id:
            expected = "|".join(f"{file_name}:{column}" for file_name, column in specs)
            unresolved_queue_source_rows.append(f"{queue_id}:<blank>:{expected}")
        elif not any(source_id in source_index.get(spec, set()) for spec in specs):
            expected = "|".join(f"{file_name}:{column}" for file_name, column in specs)
            unresolved_queue_source_rows.append(f"{queue_id}:{source_id}:{expected}")

    add_check(
        rows,
        "SIGNOFF_QUEUE_FIELD_SYNC",
        "coverage",
        "PASS" if not queue_mismatch_rows else "FAIL",
        "signoff rows copy queue evidence fields exactly",
        "mismatched=" + ";".join(queue_mismatch_rows),
        f"human_review_queue.csv; {signoff_artifact}",
        "Regenerate signoff rows if they drift from the review queue.",
        completion_state,
    )

    add_check(
        rows,
        "SIGNOFF_ALLOWED_DECISIONS",
        "decision_policy",
        "PASS" if not bad_allowed_rows and not invalid_decision_rows else "FAIL",
        "decision_allowed is the canonical set and filled decisions use only allowed values",
        f"bad_allowed={';'.join(bad_allowed_rows)}; invalid_decisions={';'.join(invalid_decision_rows)}",
        signoff_artifact,
        "Use only the allowed signoff decisions.",
        completion_state,
    )

    add_check(
        rows,
        "SIGNOFF_DECISION_SCOPE_POLICY",
        "decision_policy",
        "PASS" if not policy_mismatch_rows and not forbidden_decision_rows else "FAIL",
        "generated signoff decision policy fields match validator policy and no filled decision is forbidden for its row",
        (
            f"policy_mismatch={';'.join(policy_mismatch_rows)}; "
            f"forbidden_decisions={';'.join(forbidden_decision_rows)}"
        ),
        signoff_artifact,
        "Use recommended_decision/completion_requirements as guidance; never approve rows whose policy forbids that decision.",
        completion_state,
    )

    add_check(
        rows,
        "SIGNOFF_EVIDENCE_FIELDS_PRESENT",
        "reviewability",
        "PASS" if not missing_evidence_rows else "FAIL",
        "each signoff row names evidence, focus, must-not-claim text, and next action",
        "missing_evidence_fields=" + ";".join(missing_evidence_rows),
        signoff_artifact,
        "Do not ask for signoff on rows without enough review context.",
        completion_state,
    )

    add_check(
        rows,
        "SIGNOFF_EVIDENCE_RESOLUTION",
        "reviewability",
        "PASS" if not unresolved_evidence_tokens else "FAIL",
        "each signoff evidence token resolves to an output artifact, repo file, workbook sheet, or explicit glob with at least one match",
        "unresolved=" + ";".join(unresolved_evidence_tokens[:20]),
        f"{signoff_artifact}; paper_review_results.xlsx; linked evidence artifacts",
        "Fix evidence_artifacts before asking for human signoff; use concrete files or explicit glob: patterns for generated run artifacts.",
        completion_state,
    )

    add_check(
        rows,
        "QUEUE_EVIDENCE_FIELDS_PRESENT",
        "reviewability",
        "PASS" if not missing_queue_evidence_rows else "FAIL",
        "each human review queue row names evidence, focus, summary, must-not-claim text, and next action",
        "missing_evidence_fields=" + ";".join(missing_queue_evidence_rows[:20]),
        "human_review_queue.csv",
        "Do not ask reviewers to use queue rows without enough review context.",
        completion_state,
    )

    add_check(
        rows,
        "QUEUE_EVIDENCE_RESOLUTION",
        "reviewability",
        "PASS" if not unresolved_queue_evidence_tokens else "FAIL",
        "each human review queue evidence token resolves to an output artifact, repo file, workbook sheet, or explicit glob with at least one match",
        "unresolved=" + ";".join(unresolved_queue_evidence_tokens[:20]),
        "human_review_queue.csv; paper_review_results.xlsx; linked evidence artifacts",
        "Fix queue evidence_artifacts before asking for manual review.",
        completion_state,
    )

    add_check(
        rows,
        "SIGNOFF_SOURCE_SHEET_RESOLUTION",
        "reviewability",
        "PASS" if not unresolved_source_sheet_tokens else "FAIL",
        "each signoff source_sheet token resolves to a workbook sheet",
        "unresolved=" + ";".join(unresolved_source_sheet_tokens[:20]),
        f"{signoff_artifact}; paper_review_results.xlsx",
        "Fix source_sheet names before asking reviewers to follow workbook references.",
        completion_state,
    )

    add_check(
        rows,
        "SIGNOFF_SOURCE_ROW_RESOLUTION",
        "reviewability",
        "PASS" if not unresolved_source_rows else "FAIL",
        "each signoff source_id resolves to the expected generated source CSV row for its queue type",
        "unresolved=" + ";".join(unresolved_source_rows[:20]),
        f"{signoff_artifact}; human_review_queue.csv; linked source CSV artifacts",
        "Fix dangling source_id values before using the signoff row for human review.",
        completion_state,
    )

    add_check(
        rows,
        "QUEUE_SOURCE_SHEET_RESOLUTION",
        "reviewability",
        "PASS" if not unresolved_queue_source_sheet_tokens else "FAIL",
        "each human review queue source_sheet token resolves to a workbook sheet",
        "unresolved=" + ";".join(unresolved_queue_source_sheet_tokens[:20]),
        "human_review_queue.csv; paper_review_results.xlsx",
        "Fix source_sheet names before using the queue for manual review.",
        completion_state,
    )

    add_check(
        rows,
        "QUEUE_SOURCE_ROW_RESOLUTION",
        "reviewability",
        "PASS" if not unresolved_queue_source_rows else "FAIL",
        "each human review queue source_id resolves to the expected generated source CSV row for its queue type",
        "unresolved=" + ";".join(unresolved_queue_source_rows[:20]),
        "human_review_queue.csv; linked source CSV artifacts",
        "Fix dangling source_id values before using the queue for manual review.",
        completion_state,
    )

    if mode == "pre-review":
        add_check(
            rows,
            "SIGNOFF_PRE_REVIEW_BLANK",
            "completion_boundary",
            "PASS" if len(blank_decision_rows) == len(signoff_rows) and not nonblank_decision_rows else "FAIL",
            "generated packet has blank reviewer-owned fields before human review",
            f"blank_decisions={len(blank_decision_rows)}; nonblank_decisions={len(nonblank_decision_rows)}",
            signoff_artifact,
            "Blank decisions mean ready for review, not approved.",
            completion_state,
        )
    else:
        completion_state = "HUMAN_SIGNOFF_COMPLETE" if not blank_decision_rows else "HUMAN_SIGNOFF_INCOMPLETE"
        add_check(
            rows,
            "SIGNOFF_COMPLETE_DECISIONS",
            "completion_boundary",
            "PASS" if not blank_decision_rows and not missing_reviewer_rows and not missing_notes_rows else "FAIL",
            "complete mode requires all decisions plus reviewer/date/notes for every human decision",
            (
                f"blank_decisions={len(blank_decision_rows)}; "
                f"missing_reviewer_or_date={';'.join(missing_reviewer_rows)}; "
                f"missing_required_notes={';'.join(missing_notes_rows)}"
            ),
            signoff_artifact,
            "Fill missing human-owned fields or keep the packet in pre-review mode.",
            completion_state,
        )
        for row in rows:
            row["completion_state"] = completion_state

    status_counts = Counter(row["status"] for row in rows)
    decision_counts = Counter(row.get("reviewer_decision", "").strip() or "<blank>" for row in signoff_rows)
    summary = {
        "output_dir": str(output_dir),
        "signoff_csv": str(signoff_path),
        "mode": mode,
        "completion_state": completion_state,
        "validation_rows": len(rows),
        "pass": status_counts.get("PASS", 0),
        "fail": status_counts.get("FAIL", 0),
        "signoff_rows": len(signoff_rows),
        "queue_rows": len(queue_rows),
        "expected_signoff_queue_rows": len(expected_queue_ids),
        "blank_decisions": len(blank_decision_rows),
        "nonblank_decisions": len(nonblank_decision_rows),
        "invalid_decisions": len(invalid_decision_rows),
        "policy_mismatch_rows": len(policy_mismatch_rows),
        "forbidden_decision_rows": len(forbidden_decision_rows),
        "unresolved_evidence_tokens": len(unresolved_evidence_tokens),
        "missing_queue_evidence_rows": len(missing_queue_evidence_rows),
        "unresolved_queue_evidence_tokens": len(unresolved_queue_evidence_tokens),
        "unresolved_source_sheet_tokens": len(unresolved_source_sheet_tokens),
        "unresolved_source_rows": len(unresolved_source_rows),
        "unresolved_queue_source_sheet_tokens": len(unresolved_queue_source_sheet_tokens),
        "unresolved_queue_source_rows": len(unresolved_queue_source_rows),
        "missing_reviewer_or_date_rows": len(missing_reviewer_rows),
        "missing_required_notes_rows": len(missing_notes_rows),
        "decision_counts": dict(sorted(decision_counts.items())),
    }
    return rows, summary


def write_markdown(path: Path, rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    lines = [
        "# Review Signoff Validation",
        "",
        "This validates the paper-review signoff state. It does not make human decisions.",
        "",
        "## Summary",
        "",
        f"- mode: `{summary['mode']}`",
        f"- completion_state: `{summary['completion_state']}`",
        f"- PASS: {summary['pass']}",
        f"- FAIL: {summary['fail']}",
        f"- signoff_rows: {summary['signoff_rows']}",
        f"- blank_decisions: {summary['blank_decisions']}",
        f"- nonblank_decisions: {summary['nonblank_decisions']}",
        f"- policy_mismatch_rows: {summary['policy_mismatch_rows']}",
        f"- forbidden_decision_rows: {summary['forbidden_decision_rows']}",
        f"- unresolved_evidence_tokens: {summary['unresolved_evidence_tokens']}",
        f"- missing_queue_evidence_rows: {summary['missing_queue_evidence_rows']}",
        f"- unresolved_queue_evidence_tokens: {summary['unresolved_queue_evidence_tokens']}",
        f"- unresolved_source_sheet_tokens: {summary['unresolved_source_sheet_tokens']}",
        f"- unresolved_source_rows: {summary['unresolved_source_rows']}",
        f"- unresolved_queue_source_sheet_tokens: {summary['unresolved_queue_source_sheet_tokens']}",
        f"- unresolved_queue_source_rows: {summary['unresolved_queue_source_rows']}",
        "",
        "## Checks",
        "",
        "| check_id | status | category | observed | reviewer_action |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        observed = row["observed"].replace("|", "\\|")
        action = row["reviewer_action"].replace("|", "\\|")
        lines.append(f"| `{row['check_id']}` | `{row['status']}` | `{row['category']}` | {observed} | {action} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="TAMonitor paper-review result directory.")
    parser.add_argument("--mode", choices=["pre-review", "complete"], default="pre-review")
    parser.add_argument("--signoff-csv", type=Path, default=None, help="Optional signoff CSV to validate instead of review_signoff_template.csv.")
    parser.add_argument("--output-prefix", default="review_signoff_validation", help="Output file prefix inside --output-dir.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    rows, summary = validate(output_dir, args.mode, args.signoff_csv.resolve() if args.signoff_csv else None)
    fieldnames = [
        "check_id",
        "category",
        "status",
        "expected",
        "observed",
        "evidence_artifacts",
        "reviewer_action",
        "completion_state",
    ]
    output_prefix = args.output_prefix
    write_csv(output_dir / f"{output_prefix}.csv", rows, fieldnames)
    (output_dir / f"{output_prefix}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown(output_dir / f"{output_prefix}.md", rows, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
