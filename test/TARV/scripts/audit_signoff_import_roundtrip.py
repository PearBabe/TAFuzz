#!/usr/bin/env python3
"""Audit the safe Review Signoff import roundtrip on an isolated packet copy.

This script is a synthetic regression check. It proves the generated packet can
accept reviewer-owned fields through the supported import path and then pass
complete-mode validation. It does not create or imply real human signoff.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
REVIEWER = "synthetic-roundtrip-regression"
REVIEW_DATE = "2026-07-05"
REVIEW_NOTES = "Synthetic import roundtrip regression only; not a human mathematical approval."


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


def sync_copied_packet_summary_paths(work_dir: Path) -> None:
    summary_path = work_dir / "experiment_summary.json"
    if not summary_path.exists():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        return
    summary["output_dir"] = str(work_dir)
    if summary.get("workbook_status") == "ok":
        summary["workbook_path"] = str(work_dir / "paper_review_results.xlsx")
    write_json(summary_path, summary)
    write_csv(
        work_dir / "experiment_summary.csv",
        [{"metric": key, "value": value} for key, value in summary.items()],
        ["metric", "value"],
    )


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str, dict[str, Any]]:
    proc = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    data: dict[str, Any] = {}
    try:
        parsed = json.loads(proc.stdout)
        if isinstance(parsed, dict):
            data = parsed
    except json.JSONDecodeError:
        data = {}
    return proc.returncode, proc.stdout, proc.stderr, data


def add_check(
    rows: list[dict[str, str]],
    check_id: str,
    category: str,
    ok: bool,
    expected: str,
    observed: str,
    evidence: str,
    reviewer_boundary: str,
) -> None:
    rows.append({
        "check_id": check_id,
        "category": category,
        "status": "PASS" if ok else "FAIL",
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
        "reviewer_boundary": reviewer_boundary,
    })


def make_filled_csv(work_dir: Path) -> tuple[Path, int]:
    template = work_dir / "review_signoff_template.csv"
    rows = read_csv(template)
    if not rows:
        raise ValueError(f"{template} has no rows")
    expected_rows = len(rows)
    fieldnames = list(rows[0])
    for row in rows:
        row["reviewer_decision"] = row.get("recommended_decision") or "APPROVE_WITH_CAVEAT"
        row["reviewer"] = REVIEWER
        row["review_date"] = REVIEW_DATE
        row["reviewer_notes"] = REVIEW_NOTES
    filled = work_dir / "synthetic_filled_review_signoff.csv"
    write_csv(filled, rows, fieldnames)
    stale = work_dir / "synthetic_stale_review_signoff.csv"
    stale_rows = [dict(row) for row in rows]
    stale_rows[0]["source_id"] = "STALE_GENERATED_SOURCE_ID_SHOULD_FAIL"
    write_csv(stale, stale_rows, fieldnames)
    return filled, expected_rows


def failed_packet_verification_ids(work_dir: Path) -> list[str]:
    path = work_dir / "review_packet_verification.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["<invalid review_packet_verification.json>"]
    rows = data.get("rows", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return ["<missing rows>"]
    return [
        str(row.get("check_id", ""))
        for row in rows
        if isinstance(row, dict) and row.get("status") == "FAIL"
    ]


def audit(output_dir: Path, timeout_rerun: Path | None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows: list[dict[str, str]] = []
    temp_parent = Path("/tmp") if Path("/tmp").is_dir() else output_dir.parent
    with tempfile.TemporaryDirectory(prefix="tamonitor_signoff_roundtrip_", dir=str(temp_parent)) as tmp:
        work_dir = Path(tmp) / "packet"
        shutil.copytree(output_dir, work_dir)
        sync_copied_packet_summary_paths(work_dir)
        for stale_audit in work_dir.glob("signoff_import_roundtrip_audit.*"):
            stale_audit.unlink()
        filled_csv, expected_signoff_rows = make_filled_csv(work_dir)
        stale_csv = work_dir / "synthetic_stale_review_signoff.csv"

        dry_code, _, dry_stderr, dry_data = run_command([
            sys.executable,
            str(SCRIPT_DIR / "import_review_signoff.py"),
            "--output-dir",
            str(work_dir),
            "--from-csv",
            str(filled_csv),
            "--out",
            str(work_dir / "synthetic_dry_imported.csv"),
        ], REPO_ROOT)
        add_check(
            rows,
            "ROUNDTRIP_CSV_DRY_RUN",
            "import_roundtrip",
            dry_code == 0
            and dry_data.get("status") == "PASS"
            and dry_data.get("applied") is False
            and dry_data.get("imported_nonblank_decisions") == expected_signoff_rows
            and not dry_data.get("errors"),
            "filled CSV dry-run imports reviewer-owned fields without applying",
            (
                f"returncode={dry_code}; status={dry_data.get('status', '')}; "
                f"applied={dry_data.get('applied', '')}; "
                f"imported_nonblank_decisions={dry_data.get('imported_nonblank_decisions', '')}; "
                f"expected_signoff_rows={expected_signoff_rows}; "
                f"errors={';'.join(dry_data.get('errors', []))}; stderr={dry_stderr[:160]}"
            ),
            "synthetic_filled_review_signoff.csv; import_review_signoff.py",
            "Synthetic decisions are not human approval.",
        )

        xlsx_code, _, xlsx_stderr, xlsx_data = run_command([
            sys.executable,
            str(SCRIPT_DIR / "import_review_signoff.py"),
            "--output-dir",
            str(work_dir),
            "--from-xlsx",
            str(work_dir / "paper_review_results.xlsx"),
            "--out",
            str(work_dir / "synthetic_xlsx_imported.csv"),
        ], REPO_ROOT)
        add_check(
            rows,
            "ROUNDTRIP_XLSX_BLANK_EXTRACTION",
            "import_roundtrip",
            xlsx_code == 0
            and xlsx_data.get("status") == "PASS"
            and xlsx_data.get("applied") is False
            and xlsx_data.get("import_rows") == expected_signoff_rows
            and xlsx_data.get("imported_nonblank_decisions") == 0
            and not xlsx_data.get("errors"),
            "blank Review Signoff workbook sheet can be extracted without applying",
            (
                f"returncode={xlsx_code}; status={xlsx_data.get('status', '')}; "
                f"import_rows={xlsx_data.get('import_rows', '')}; "
                f"expected_signoff_rows={expected_signoff_rows}; "
                f"imported_nonblank_decisions={xlsx_data.get('imported_nonblank_decisions', '')}; "
                f"errors={';'.join(xlsx_data.get('errors', []))}; stderr={xlsx_stderr[:160]}"
            ),
            "paper_review_results.xlsx; import_review_signoff.py",
            "Blank workbook extraction means ready for review, not signed off.",
        )

        apply_code, _, apply_stderr, apply_data = run_command([
            sys.executable,
            str(SCRIPT_DIR / "import_review_signoff.py"),
            "--output-dir",
            str(work_dir),
            "--from-csv",
            str(filled_csv),
            "--apply",
            "--out",
            str(work_dir / "synthetic_apply_imported.csv"),
        ], REPO_ROOT)
        add_check(
            rows,
            "ROUNDTRIP_CSV_APPLY",
            "import_roundtrip",
            apply_code == 0
            and apply_data.get("status") == "PASS"
            and apply_data.get("applied") is True
            and apply_data.get("imported_nonblank_decisions") == expected_signoff_rows
            and not apply_data.get("errors"),
            "filled CSV applies cleanly to the isolated packet copy",
            (
                f"returncode={apply_code}; status={apply_data.get('status', '')}; "
                f"applied={apply_data.get('applied', '')}; "
                f"imported_nonblank_decisions={apply_data.get('imported_nonblank_decisions', '')}; "
                f"expected_signoff_rows={expected_signoff_rows}; "
                f"errors={';'.join(apply_data.get('errors', []))}; stderr={apply_stderr[:160]}"
            ),
            "synthetic_filled_review_signoff.csv; import_review_signoff.py",
            "Apply happened only in a temporary packet copy.",
        )

        complete_code, _, complete_stderr, complete_data = run_command([
            sys.executable,
            str(SCRIPT_DIR / "validate_review_signoff.py"),
            "--output-dir",
            str(work_dir),
            "--mode",
            "complete",
        ], REPO_ROOT)
        add_check(
            rows,
            "ROUNDTRIP_COMPLETE_VALIDATION",
            "complete_mode",
            complete_code == 0
            and complete_data.get("completion_state") == "HUMAN_SIGNOFF_COMPLETE"
            and complete_data.get("fail") == 0
            and complete_data.get("nonblank_decisions") == expected_signoff_rows
            and complete_data.get("unresolved_queue_evidence_tokens") == 0
            and complete_data.get("unresolved_queue_source_rows") == 0,
            "complete-mode signoff validation passes after synthetic import",
            (
                f"returncode={complete_code}; completion_state={complete_data.get('completion_state', '')}; "
                f"pass={complete_data.get('pass', '')}; fail={complete_data.get('fail', '')}; "
                f"nonblank_decisions={complete_data.get('nonblank_decisions', '')}; "
                f"expected_signoff_rows={expected_signoff_rows}; stderr={complete_stderr[:160]}"
            ),
            "validate_review_signoff.py --mode complete",
            "Synthetic complete mode proves command behavior, not human math approval.",
        )

        rebuild_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "rebuild_review_workbook.py"),
            "--output-dir",
            str(work_dir),
        ]
        if timeout_rerun:
            rebuild_cmd.extend(["--timeout-rerun-dir", str(timeout_rerun)])
        rebuild_code, _, rebuild_stderr, rebuild_data = run_command(rebuild_cmd, REPO_ROOT)
        add_check(
            rows,
            "ROUNDTRIP_COMPLETE_WORKBOOK_REBUILD",
            "complete_mode",
            rebuild_code == 0
            and rebuild_data.get("status") == "ok"
            and Path(str(rebuild_data.get("workbook_path", ""))).exists()
            and (not timeout_rerun or rebuild_data.get("timeout_rerun_summary_present") is True)
            and (not timeout_rerun or rebuild_data.get("timeout_rerun_details_present") is True),
            "temporary complete-review packet workbook rebuild succeeds before complete-mode packet verification",
            (
                f"returncode={rebuild_code}; status={rebuild_data.get('status', '')}; "
                f"workbook_path={rebuild_data.get('workbook_path', '')}; "
                f"timeout_summary={rebuild_data.get('timeout_rerun_summary_present', '')}; "
                f"timeout_details={rebuild_data.get('timeout_rerun_details_present', '')}; "
                f"stderr={rebuild_stderr[:160]}"
            ),
            "rebuild_review_workbook.py",
            "Workbook rebuild happened only in the temporary packet copy.",
        )

        verify_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "verify_review_packet.py"),
            "--output-dir",
            str(work_dir),
            "--signoff-mode",
            "complete",
        ]
        if timeout_rerun:
            verify_cmd.extend(["--timeout-rerun", str(timeout_rerun)])
        verify_code, _, verify_stderr, verify_data = run_command(verify_cmd, REPO_ROOT)
        verify_failed_ids = failed_packet_verification_ids(work_dir)
        add_check(
            rows,
            "ROUNDTRIP_COMPLETE_PACKET_VERIFICATION",
            "complete_mode",
            verify_code == 0
            and verify_data.get("fail") == 0
            and verify_data.get("pass") == verify_data.get("check_rows"),
            "complete-mode packet verifier passes after synthetic import",
            (
                f"returncode={verify_code}; pass={verify_data.get('pass', '')}; "
                f"fail={verify_data.get('fail', '')}; check_rows={verify_data.get('check_rows', '')}; "
                f"failed_checks={';'.join(verify_failed_ids[:12])}; "
                f"stderr={verify_stderr[:160]}"
            ),
            "verify_review_packet.py --signoff-mode complete",
            "Synthetic complete packet is a regression fixture only.",
        )

        stale_code, _, stale_stderr, stale_data = run_command([
            sys.executable,
            str(SCRIPT_DIR / "import_review_signoff.py"),
            "--output-dir",
            str(work_dir),
            "--from-csv",
            str(stale_csv),
            "--out",
            str(work_dir / "synthetic_stale_imported.csv"),
        ], REPO_ROOT)
        add_check(
            rows,
            "ROUNDTRIP_STALE_GENERATED_FIELD_REJECTED",
            "negative_import",
            stale_code == 1
            and stale_data.get("status") == "FAIL"
            and stale_data.get("immutable_field_mismatches") == 1
            and stale_data.get("applied") is False,
            "stale generated source_id import fails and does not apply",
            (
                f"returncode={stale_code}; status={stale_data.get('status', '')}; "
                f"immutable_field_mismatches={stale_data.get('immutable_field_mismatches', '')}; "
                f"applied={stale_data.get('applied', '')}; stderr={stale_stderr[:160]}"
            ),
            "synthetic_stale_review_signoff.csv; import_review_signoff.py",
            "Generated fields remain owned by the packet generator.",
        )

    counts = Counter(row["status"] for row in rows)
    summary = {
        "output_dir": str(output_dir),
        "timeout_rerun": str(timeout_rerun) if timeout_rerun else "",
        "row_count": len(rows),
        "pass": counts.get("PASS", 0),
        "fail": counts.get("FAIL", 0),
        "warn": counts.get("WARN", 0),
        "synthetic_only": True,
        "expected_signoff_rows": expected_signoff_rows,
        "imported_nonblank_decisions": expected_signoff_rows if counts.get("FAIL", 0) == 0 else 0,
        "human_signoff_claim": "not_claimed",
    }
    return rows, summary


def write_markdown(path: Path, rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    lines = [
        "# Signoff Import Roundtrip Audit",
        "",
        "This is a synthetic regression check for the supported Review Signoff import workflow.",
        "It does not record human mathematical approval.",
        "",
        "## Summary",
        "",
        f"- PASS: {summary['pass']}",
        f"- FAIL: {summary['fail']}",
        f"- synthetic_only: `{summary['synthetic_only']}`",
        f"- human_signoff_claim: `{summary['human_signoff_claim']}`",
        "",
        "## Checks",
        "",
        "| check_id | status | category | observed | reviewer_boundary |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        observed = row["observed"].replace("|", "\\|")
        boundary = row["reviewer_boundary"].replace("|", "\\|")
        lines.append(f"| `{row['check_id']}` | `{row['status']}` | `{row['category']}` | {observed} | {boundary} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated review packet directory.")
    parser.add_argument("--timeout-rerun", type=Path, default=None, help="Optional timeout-rerun directory used by complete-mode packet verification.")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    timeout_rerun = args.timeout_rerun.resolve() if args.timeout_rerun else None
    rows, summary = audit(output_dir, timeout_rerun)
    fieldnames = ["check_id", "category", "status", "expected", "observed", "evidence", "reviewer_boundary"]
    write_csv(output_dir / "signoff_import_roundtrip_audit.csv", rows, fieldnames)
    write_json(output_dir / "signoff_import_roundtrip_audit.json", {"summary": summary, "rows": rows})
    write_markdown(output_dir / "signoff_import_roundtrip_audit.md", rows, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
