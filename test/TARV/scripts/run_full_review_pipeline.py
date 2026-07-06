#!/usr/bin/env python3
"""Run the full TAMonitor paper-review pipeline.

This orchestrator does not reinterpret TAMonitor or MoniTAal results. It only
executes the established build, experiment, timeout-rerun, and packet-verifier
steps, then records enough command evidence for reproducibility review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TAMONITOR = REPO_ROOT / "tool" / "MightyPPL" / "build" / "TAMonitor"
PIPELINE_SCRIPT_PATHS = [
    SCRIPT_DIR / "run_paper_experiments.py",
    SCRIPT_DIR / "rerun_baseline_timeouts.py",
    SCRIPT_DIR / "verify_review_packet.py",
    SCRIPT_DIR / "verify_pipeline_artifact_manifest.py",
    SCRIPT_DIR / "compare_pipeline_results.py",
    SCRIPT_DIR / "analyze_benchmark_blockers.py",
    SCRIPT_DIR / "build_signoff_evidence_bundle.py",
    SCRIPT_DIR / "audit_signoff_import_roundtrip.py",
    SCRIPT_DIR / "run_monitaal_hardcoded_benchmarks.py",
    SCRIPT_DIR / "build_mitl_formula_catalog.py",
    SCRIPT_DIR / "import_review_signoff.py",
    SCRIPT_DIR / "rebuild_review_workbook.py",
    SCRIPT_DIR / "validate_review_signoff.py",
    SCRIPT_DIR / "run_full_review_pipeline.py",
    REPO_ROOT / "src" / "TAMonitor" / "make_tamonitor_xlsx.py",
]
FULL_RUN_ZERO_METRICS = [
    "semantic_fail",
    "semantic_error",
    "semantic_timeout",
    "semantic_prefix_oracle_mismatch",
    "semantic_prefix_oracle_missing_observed_step",
    "semantic_oracle_review_required",
    "semantic_oracle_prefix_mismatches",
    "syntax_coverage_missing",
    "formula_input_policy_fail",
    "formula_input_policy_assert_like_failures",
    "cli_contract_fail",
    "human_review_queue_fail",
    "manual_review_fail",
    "goal_completion_fail",
    "requirements_audit_fail",
    "paper_claim_audit_fail",
    "translation_candidate_timeouts",
    "translation_candidate_baseline_mismatches",
    "candidate_step_missing_or_incomplete",
]
CAVEAT_METRICS = [
    "baseline_timeouts",
    "baseline_skipped_no_input",
    "baseline_generated_empty_no_original_input",
    "translation_candidate_baseline_not_verified",
    "goal_completion_pass_with_caveat",
    "requirements_audit_pass_with_caveat",
    "manual_review_pass_with_caveat",
    "manual_review_review_required",
    "goal_completion_review_required",
]
STABILITY_PROFILES = [
    "manual-oracle-added",
    "stable",
    "verifier-signoff-added",
    "manual-oracle-independence-added",
    "manual-oracle-baseline-boundary-added",
    "benchmark-blocker-diagnostics-added",
    "pipeline-source-hashes-added",
    "formula-catalog-integrated",
    "timeout-rerun-workbook-added",
    "monitaal-eof-fix",
    "generated-empty-inputs-added",
    "hardcoded-benchmarks-added",
    "finite-syntax-oracles-added",
    "finite-syntax-oracles-and-three-valued-guard-added",
    "three-valued-verdict-guard-added",
    "signoff-policy-added",
    "signoff-evidence-resolution-added",
    "signoff-import-added",
    "signoff-source-resolution-added",
    "review-queue-source-resolution-added",
    "review-queue-evidence-resolution-added",
    "signoff-roundtrip-audit-added",
    "signoff-evidence-bundle-added",
    "evidence-consistency-guards-added",
    "xml-proof-obligations-added",
    "xml-trace-coverage-added",
    "xml-boundary-traces-added",
    "xml-three-valued-coverage-fixed",
    "xml-original-trace-gaps-added",
    "xml-original-trace-gap-signoff-added",
    "embedded-c-after10-original-trace-added",
    "embedded-c-after10-provenance-guard-added",
    "baseline-match-oracle-boundary-guard-added",
    "workbook-preview-manifest-guard-added",
    "workbook-source-coverage-guard-added",
    "workbook-xlsx-table-shape-guard-added",
    "correctness-audit-rowcount-guard-added",
    "workbook-rebuild-summary-guard-added",
    "candidate-prefix-observations-guard-added",
    "monitaal-xml-structural-ledger-guard-added",
    "manual-review-entrypoint-reference-guard-added",
    "gear-original-input-response-audit-added",
    "non-gear-original-input-search-audit-added",
    "cli-trace-header-contract-added",
]


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def render_command(args: list[str]) -> str:
    return " ".join(shlex.quote(str(arg)) for arg in args)


def tail(text: str, limit: int = 1600) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def path_for_summary(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def directory_has_entries(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def kill_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except PermissionError:
            proc.kill()


def run_command(
    step: str,
    args: list[str],
    cwd: Path,
    log_dir: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.Popen(
        [str(arg) for arg in args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds if timeout_seconds > 0 else None)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_group(proc)
        stdout, stderr = proc.communicate()
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    safe_step = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in step)
    stdout_path = log_dir / f"{safe_step}.stdout.txt"
    stderr_path = log_dir / f"{safe_step}.stderr.txt"
    stdout_path.write_text(stdout or "", encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")

    return {
        "step": step,
        "command": render_command([str(arg) for arg in args]),
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "timeout": timed_out,
        "timeout_seconds": timeout_seconds,
        "elapsed_ms": elapsed_ms,
        "stdout_log": path_for_summary(stdout_path),
        "stderr_log": path_for_summary(stderr_path),
        "stdout_tail": tail(stdout or ""),
        "stderr_tail": tail(stderr or ""),
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def int_value(data: dict[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pipeline_manifest_candidate_files(output_dir: Path, timeout_rerun_dir: Path | None) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    excluded_names = {
        "pipeline_artifact_manifest.csv",
        "pipeline_artifact_manifest.json",
        "pipeline_artifact_manifest.md",
        "pipeline_artifact_manifest_verification.csv",
        "pipeline_artifact_manifest_verification.json",
        "pipeline_artifact_manifest_verification.md",
    }

    if output_dir.exists():
        for path in sorted(output_dir.iterdir()):
            if path.is_file() and path.name not in excluded_names:
                candidates.append(("result_file", path))
        log_dir = output_dir / "pipeline_command_logs"
        if log_dir.exists():
            for path in sorted(log_dir.iterdir()):
                if path.is_file():
                    candidates.append(("command_log", path))

    if timeout_rerun_dir and timeout_rerun_dir.exists():
        for path in sorted(timeout_rerun_dir.iterdir()):
            if path.is_file():
                candidates.append(("timeout_rerun_file", path))

    return candidates


def write_pipeline_artifact_manifest(output_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
    timeout_value = str(summary.get("timeout_rerun_dir") or "")
    timeout_rerun_dir = Path(timeout_value) if timeout_value else None
    rows: list[dict[str, Any]] = []
    for category, path in pipeline_manifest_candidate_files(output_dir, timeout_rerun_dir):
        try:
            relative_key = path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            relative_key = str(path.resolve())
        rows.append({
            "category": category,
            "key": relative_key,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "evidence": "Final pipeline-level artifact hash after all configured review steps completed.",
        })

    csv_path = output_dir / "pipeline_artifact_manifest.csv"
    json_path = output_dir / "pipeline_artifact_manifest.json"
    md_path = output_dir / "pipeline_artifact_manifest.md"
    write_csv(csv_path, rows, ["category", "key", "sha256", "size_bytes", "evidence"])
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    lines = [
        "# Pipeline Artifact Manifest",
        "",
        "This manifest hashes final pipeline-level artifacts, command logs, and matching timeout-rerun files.",
        "It is written after the final pipeline summary, packet verifier, signoff validation, and optional stability audit.",
        "",
        "## Counts",
        "",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"- {category}: {count}")
    lines.extend([
        "",
        "## Hashes",
        "",
        "| category | key | sha256 | size_bytes |",
        "|---|---|---|---:|",
    ])
    for row in rows:
        lines.append(f"| `{row['category']}` | `{row['key']}` | `{row['sha256']}` | {row['size_bytes']} |")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "rows": len(rows),
        "categories": counts,
        "csv": str(csv_path),
        "json": str(json_path),
        "md": str(md_path),
    }


def flatten_for_csv(summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(key: str, value: Any, evidence: str) -> None:
        rows.append({"key": key, "value": str(value), "evidence": evidence})

    add("pipeline_status", summary["pipeline_status"], "pipeline_summary.json")
    add("pipeline_mode", summary["pipeline_mode"], "pipeline_summary.json")
    add("started_at", summary.get("started_at", ""), "pipeline_summary.json")
    add("finished_at", summary.get("finished_at", ""), "pipeline_summary.json")
    add("elapsed_ms", summary.get("elapsed_ms", ""), "pipeline_summary.json")
    add("output_dir", summary["output_dir"], "primary full experiment directory")
    add("timeout_rerun_dir", summary.get("timeout_rerun_dir", ""), "supplementary timeout rerun directory")
    add("workbook_path", summary.get("workbook_path", ""), "experiment_summary.json")
    add("failed_steps", ";".join(summary.get("failed_steps", [])), "pipeline command results")
    add("caveats", ";".join(summary.get("caveats", [])), "pipeline_summary.json")
    add("command_count", len(summary.get("commands", [])), "pipeline command results")

    experiment = summary.get("experiment_summary", {})
    for key in [
        "semantic_cases",
        "semantic_correctness_verified",
        "semantic_fail",
        "semantic_error",
        "semantic_timeout",
        "semantic_prefix_oracle_mismatch",
        "semantic_prefix_oracle_missing_observed_step",
        "semantic_oracle_review_required",
        "manual_oracle_guide_rows",
        "manual_oracle_guide_p0",
        "syntax_coverage_missing",
        "formula_input_policy_fail",
        "cli_contract_fail",
        "baseline_runs",
        "baseline_timeouts",
        "baseline_skipped_no_input",
        "baseline_generated_empty_no_original_input",
        "translation_candidate_success",
        "translation_candidate_baseline_matches",
        "translation_candidate_baseline_mismatches",
        "translation_candidate_baseline_not_verified",
        "candidate_step_missing_or_incomplete",
        "human_review_queue_fail",
        "manual_review_fail",
        "goal_completion_fail",
        "review_signoff_template_rows",
        "review_signoff_template_blank_decisions",
        "requirements_audit_fail",
        "paper_claim_audit_fail",
        "workbook_status",
    ]:
        add(f"experiment.{key}", experiment.get(key, ""), "experiment_summary.json")

    timeout_summary = summary.get("timeout_rerun_summary", {})
    for key in [
        "selected_timeout_rows",
        "rerun_completed",
        "rerun_ran",
        "rerun_timeouts",
        "rerun_skipped_no_binary",
    ]:
        add(f"timeout_rerun.{key}", timeout_summary.get(key, ""), "baseline_timeout_rerun_summary.json")

    hardcoded_summary = summary.get("monitaal_hardcoded_benchmarks", {})
    for key in [
        "row_count",
        "ran",
        "timeout",
        "error",
        "parse_failed",
        "binary_exists",
        "build_ok",
    ]:
        add(f"monitaal_hardcoded_benchmarks.{key}", hardcoded_summary.get(key, ""), "monitaal_hardcoded_benchmarks.json")

    verification = summary.get("review_packet_verification", {})
    for key in ["check_rows", "pass", "warn", "fail"]:
        add(f"verification.{key}", verification.get(key, ""), "review_packet_verification.json")

    signoff_evidence = summary.get("review_signoff_evidence_bundle", {})
    for key in ["row_count", "pass", "warn", "fail", "missing_queue_rows", "missing_source_rows", "unresolved_evidence_tokens", "generated_only", "human_signoff_claim"]:
        add(f"signoff_evidence.{key}", signoff_evidence.get(key, ""), "review_signoff_evidence_bundle.json")

    roundtrip = summary.get("signoff_import_roundtrip_audit", {})
    for key in ["row_count", "pass", "warn", "fail", "expected_signoff_rows", "imported_nonblank_decisions", "synthetic_only", "human_signoff_claim"]:
        add(f"signoff_import_roundtrip.{key}", roundtrip.get(key, ""), "signoff_import_roundtrip_audit.json")

    signoff_validation = summary.get("review_signoff_validation", {})
    for key in [
        "mode",
        "completion_state",
        "validation_rows",
        "pass",
        "fail",
        "signoff_rows",
        "blank_decisions",
        "nonblank_decisions",
        "policy_mismatch_rows",
        "forbidden_decision_rows",
        "unresolved_evidence_tokens",
        "missing_queue_evidence_rows",
        "unresolved_queue_evidence_tokens",
        "unresolved_source_sheet_tokens",
        "unresolved_source_rows",
        "unresolved_queue_source_sheet_tokens",
        "unresolved_queue_source_rows",
    ]:
        add(f"signoff_validation.{key}", signoff_validation.get(key, ""), "review_signoff_validation.json")

    stability = summary.get("result_stability_audit", {})
    for key in ["profile", "rows", "pass", "warn", "fail"]:
        add(f"stability_audit.{key}", stability.get(key, ""), "result_stability_audit.json")

    for artifact, artifact_path in summary.get("artifacts", {}).items():
        add(f"artifact.{artifact}", artifact_path, "pipeline_summary.json")

    return rows


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# TAMonitor Full Review Pipeline",
        "",
        "This file records a one-command execution of the TAMonitor paper-review pipeline.",
        "It is reproducibility evidence only; human mathematical signoff is still recorded separately in the review workbook.",
        "",
        "## Summary",
        "",
        f"- status: `{summary['pipeline_status']}`",
        f"- mode: `{summary['pipeline_mode']}`",
        f"- started: `{summary.get('started_at', '')}`",
        f"- finished: `{summary.get('finished_at', '')}`",
        f"- elapsed_ms: `{summary.get('elapsed_ms', '')}`",
        f"- output directory: `{summary['output_dir']}`",
        f"- timeout rerun directory: `{summary.get('timeout_rerun_dir', '')}`",
        f"- workbook: `{summary.get('workbook_path', '')}`",
        f"- failed steps: `{'; '.join(summary.get('failed_steps', []))}`",
        f"- caveats: `{'; '.join(summary.get('caveats', []))}`",
        "",
        "## Experiment Counts",
        "",
    ]
    experiment = summary.get("experiment_summary", {})
    for key in [
        "semantic_cases",
        "semantic_correctness_verified",
        "semantic_fail",
        "semantic_error",
        "semantic_timeout",
        "semantic_prefix_oracle_mismatch",
        "semantic_oracle_review_required",
        "manual_oracle_guide_rows",
        "manual_oracle_guide_p0",
        "syntax_coverage_missing",
        "cli_contract_fail",
        "baseline_runs",
        "baseline_timeouts",
        "baseline_generated_empty_no_original_input",
        "translation_candidate_baseline_matches",
        "translation_candidate_baseline_mismatches",
        "translation_candidate_baseline_not_verified",
        "human_review_queue_fail",
        "requirements_audit_fail",
        "workbook_status",
    ]:
        lines.append(f"- {key}: `{experiment.get(key, '')}`")

    timeout_summary = summary.get("timeout_rerun_summary", {})
    lines.extend([
        "",
        "## Timeout Rerun",
        "",
    ])
    for key in ["selected_timeout_rows", "rerun_completed", "rerun_ran", "rerun_timeouts"]:
        lines.append(f"- {key}: `{timeout_summary.get(key, '')}`")

    hardcoded_summary = summary.get("monitaal_hardcoded_benchmarks", {})
    lines.extend([
        "",
        "## MoniTAal Hard-Coded Benchmarks",
        "",
    ])
    for key in ["row_count", "ran", "timeout", "error", "parse_failed", "binary_exists", "build_ok"]:
        lines.append(f"- {key}: `{hardcoded_summary.get(key, '')}`")

    verification = summary.get("review_packet_verification", {})
    lines.extend([
        "",
        "## Packet Verification",
        "",
    ])
    for key in ["check_rows", "pass", "warn", "fail"]:
        lines.append(f"- {key}: `{verification.get(key, '')}`")

    signoff_evidence = summary.get("review_signoff_evidence_bundle", {})
    lines.extend([
        "",
        "## Signoff Evidence Bundle",
        "",
    ])
    for key in ["row_count", "pass", "warn", "fail", "missing_queue_rows", "missing_source_rows", "unresolved_evidence_tokens", "generated_only", "human_signoff_claim"]:
        lines.append(f"- {key}: `{signoff_evidence.get(key, '')}`")

    roundtrip = summary.get("signoff_import_roundtrip_audit", {})
    lines.extend([
        "",
        "## Signoff Import Roundtrip",
        "",
    ])
    for key in ["row_count", "pass", "warn", "fail", "expected_signoff_rows", "imported_nonblank_decisions", "synthetic_only", "human_signoff_claim"]:
        lines.append(f"- {key}: `{roundtrip.get(key, '')}`")

    signoff_validation = summary.get("review_signoff_validation", {})
    lines.extend([
        "",
        "## Signoff Validation",
        "",
    ])
    for key in [
        "mode",
        "completion_state",
        "validation_rows",
        "pass",
        "fail",
        "signoff_rows",
        "blank_decisions",
        "nonblank_decisions",
        "policy_mismatch_rows",
        "forbidden_decision_rows",
        "unresolved_evidence_tokens",
        "missing_queue_evidence_rows",
        "unresolved_queue_evidence_tokens",
        "unresolved_source_sheet_tokens",
        "unresolved_source_rows",
        "unresolved_queue_source_sheet_tokens",
        "unresolved_queue_source_rows",
    ]:
        lines.append(f"- {key}: `{signoff_validation.get(key, '')}`")

    stability = summary.get("result_stability_audit", {})
    lines.extend([
        "",
        "## Result Stability",
        "",
    ])
    for key in ["profile", "rows", "pass", "warn", "fail"]:
        lines.append(f"- {key}: `{stability.get(key, '')}`")

    lines.extend([
        "",
        "## Review Artifacts",
        "",
    ])
    for artifact, artifact_path in summary.get("artifacts", {}).items():
        lines.append(f"- {artifact}: `{artifact_path}`")

    lines.extend([
        "",
        "## Commands",
        "",
        "| step | returncode | timeout | elapsed_ms | stdout | stderr |",
        "|---|---:|---|---:|---|---|",
    ])
    for command in summary.get("commands", []):
        lines.append(
            f"| `{command['step']}` | {command['returncode']} | `{command['timeout']}` | "
            f"{command['elapsed_ms']} | `{command['stdout_log']}` | `{command['stderr_log']}` |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def fail_reasons(
    commands: list[dict[str, Any]],
    experiment_summary: dict[str, Any],
    timeout_summary: dict[str, Any],
    verification: dict[str, Any],
    signoff_validation: dict[str, Any],
    signoff_evidence: dict[str, Any],
    signoff_roundtrip: dict[str, Any],
    args: argparse.Namespace,
    stability_summary: dict[str, Any],
    stability_required: bool,
) -> list[str]:
    failed = [
        command["step"]
        for command in commands
        if command["timeout"] or command["returncode"] not in (0, None)
    ]
    if not args.no_run and not args.tamonitor.exists():
        failed.append("tamonitor_executable_missing")
    if not experiment_summary:
        failed.append("experiment_summary_missing")
    elif not args.no_run:
        for key in FULL_RUN_ZERO_METRICS:
            value = int_value(experiment_summary, key)
            if value != 0:
                failed.append(f"experiment_{key}_nonzero:{value}")
        if int_value(experiment_summary, "semantic_correctness_verified") <= 0:
            failed.append("experiment_semantic_correctness_verified_zero")
        if int_value(experiment_summary, "translation_candidate_success") != int_value(experiment_summary, "translation_candidate_runs"):
            failed.append(
                "experiment_translation_candidate_success_mismatch:"
                f"{int_value(experiment_summary, 'translation_candidate_success')}/"
                f"{int_value(experiment_summary, 'translation_candidate_runs')}"
            )
        if int_value(experiment_summary, "review_signoff_template_blank_decisions") != int_value(experiment_summary, "review_signoff_template_rows"):
            failed.append("experiment_review_signoff_not_blank_template")
        workbook_value = str(experiment_summary.get("workbook_path", ""))
        workbook_path = Path(workbook_value) if workbook_value else Path()
        workbook_exists = bool(workbook_value) and (
            workbook_path.exists() or (REPO_ROOT / workbook_value).exists()
        )
        if not args.no_workbook and not workbook_exists:
            failed.append("experiment_workbook_missing")
    if not args.skip_verify:
        if not verification:
            failed.append("review_packet_verification_summary_missing")
        try:
            verification_fail = int(verification.get("fail", 0))
        except (TypeError, ValueError):
            verification_fail = 0
        if verification_fail:
            failed.append("review_packet_verification_fail_count")
    if experiment_summary and not args.no_workbook and experiment_summary.get("workbook_status") != "ok":
        failed.append("experiment_workbook_status")
    if not args.skip_signoff_validation:
        if not signoff_validation:
            failed.append("review_signoff_validation_summary_missing")
        elif int_value(signoff_validation, "fail") != 0:
            failed.append(f"review_signoff_validation_fail_count:{int_value(signoff_validation, 'fail')}")
    if not args.skip_signoff_evidence_bundle:
        if not signoff_evidence:
            failed.append("review_signoff_evidence_bundle_summary_missing")
        elif int_value(signoff_evidence, "fail") != 0:
            failed.append(f"review_signoff_evidence_bundle_fail_count:{int_value(signoff_evidence, 'fail')}")
        elif int_value(signoff_evidence, "missing_source_rows") != 0:
            failed.append(f"review_signoff_evidence_bundle_missing_source_rows:{int_value(signoff_evidence, 'missing_source_rows')}")
        elif int_value(signoff_evidence, "unresolved_evidence_tokens") != 0:
            failed.append(f"review_signoff_evidence_bundle_unresolved_tokens:{int_value(signoff_evidence, 'unresolved_evidence_tokens')}")
    if not args.skip_signoff_roundtrip:
        if not signoff_roundtrip:
            failed.append("signoff_import_roundtrip_summary_missing")
        elif int_value(signoff_roundtrip, "fail") != 0:
            failed.append(f"signoff_import_roundtrip_fail_count:{int_value(signoff_roundtrip, 'fail')}")
    if (
        stability_required
        and args.stability_baseline
        and not args.skip_stability_audit
    ):
        if not stability_summary:
            failed.append("result_stability_audit_summary_missing")
        elif int_value(stability_summary, "fail") != 0:
            failed.append(f"result_stability_audit_fail_count:{int_value(stability_summary, 'fail')}")
    if not args.skip_timeout_rerun and not args.no_run:
        if not timeout_summary:
            failed.append("timeout_rerun_summary_missing")
        else:
            selected = int_value(timeout_summary, "selected_timeout_rows", -1)
            completed = int_value(timeout_summary, "rerun_completed", -1)
            main_timeouts = int_value(experiment_summary, "baseline_timeouts", -1)
            if selected != main_timeouts:
                failed.append(f"timeout_rerun_selected_mismatch:{selected}!={main_timeouts}")
            if completed != selected:
                failed.append(f"timeout_rerun_incomplete:{completed}!={selected}")
            skipped_no_binary = int_value(timeout_summary, "rerun_skipped_no_binary")
            if skipped_no_binary != 0:
                failed.append(f"timeout_rerun_skipped_no_binary:{skipped_no_binary}")
    return failed


def caveat_reasons(
    experiment_summary: dict[str, Any],
    timeout_summary: dict[str, Any],
    verification: dict[str, Any],
    stability_summary: dict[str, Any],
    args: argparse.Namespace,
) -> list[str]:
    caveats: list[str] = []
    for key in CAVEAT_METRICS:
        value = int_value(experiment_summary, key)
        if value:
            caveats.append(f"experiment_{key}:{value}")
    if timeout_summary:
        rerun_ran = int_value(timeout_summary, "rerun_ran")
        rerun_timeouts = int_value(timeout_summary, "rerun_timeouts")
        if rerun_ran:
            caveats.append(f"timeout_rerun_finished_with_verdict:{rerun_ran}")
        if rerun_timeouts:
            caveats.append(f"timeout_rerun_still_timeout:{rerun_timeouts}")
    warn_count = int_value(verification, "warn")
    if warn_count:
        caveats.append(f"review_packet_verification_warn:{warn_count}")
    stability_warn_count = int_value(stability_summary, "warn")
    if stability_warn_count:
        caveats.append(f"result_stability_audit_warn:{stability_warn_count}")
    if args.no_build:
        caveats.append("partial_no_build")
    if args.no_run:
        caveats.append("partial_no_run")
    if args.no_workbook:
        caveats.append("partial_no_workbook")
    if args.skip_timeout_rerun:
        caveats.append("partial_skip_timeout_rerun")
    if args.skip_verify:
        caveats.append("partial_skip_verify")
    if args.skip_signoff_validation:
        caveats.append("partial_skip_signoff_validation")
    if args.skip_signoff_evidence_bundle:
        caveats.append("partial_skip_signoff_evidence_bundle")
    if args.skip_signoff_roundtrip:
        caveats.append("partial_skip_signoff_roundtrip")
    if args.skip_benchmark_blocker_diagnostics:
        caveats.append("partial_skip_benchmark_blocker_diagnostics")
    if args.skip_monitaal_hardcoded_benchmarks:
        caveats.append("partial_skip_monitaal_hardcoded_benchmarks")
    if args.skip_formula_catalog:
        caveats.append("partial_skip_formula_catalog")
    if args.skip_stability_audit and args.stability_baseline:
        caveats.append("partial_skip_stability_audit")
    if args.timeout_rerun_limit:
        caveats.append(f"partial_timeout_rerun_limit:{args.timeout_rerun_limit}")
    return caveats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Primary full experiment output directory. Defaults to test/TARV/results/paper_pipeline_<timestamp>.",
    )
    parser.add_argument(
        "--timeout-rerun-out",
        type=Path,
        default=None,
        help="Supplementary baseline timeout rerun output directory.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Per-command timeout forwarded to run_paper_experiments.py.")
    parser.add_argument("--timeout-rerun-seconds", type=int, default=60, help="Per-row timeout for baseline timeout rerun.")
    parser.add_argument("--timeout-rerun-limit", type=int, default=0, help="Optional timeout-rerun row limit; 0 means all timeout rows.")
    parser.add_argument("--tamonitor", type=Path, default=DEFAULT_TAMONITOR, help="TAMonitor executable path.")
    parser.add_argument("--build-jobs", type=int, default=2, help="Parallel jobs for cmake build.")
    parser.add_argument("--build-timeout", type=int, default=600, help="Wall timeout for the build command; 0 disables.")
    parser.add_argument("--experiment-wall-timeout", type=int, default=7200, help="Wall timeout for the full experiment command; 0 disables.")
    parser.add_argument("--rerun-wall-timeout", type=int, default=7200, help="Wall timeout for the timeout-rerun command; 0 disables.")
    parser.add_argument("--verify-timeout", type=int, default=600, help="Wall timeout for the packet verifier; 0 disables.")
    parser.add_argument("--signoff-validation-timeout", type=int, default=120, help="Wall timeout for review signoff validation; 0 disables.")
    parser.add_argument("--signoff-evidence-timeout", type=int, default=120, help="Wall timeout for Review Signoff evidence bundle generation; 0 disables.")
    parser.add_argument("--signoff-roundtrip-timeout", type=int, default=300, help="Wall timeout for synthetic Review Signoff import roundtrip audit; 0 disables.")
    parser.add_argument("--blocker-diagnostics-timeout", type=int, default=120, help="Wall timeout for benchmark blocker diagnostics; 0 disables.")
    parser.add_argument("--blocker-probe-timeout", type=int, default=10, help="Per TAMonitor probe timeout for benchmark blocker diagnostics.")
    parser.add_argument("--hardcoded-benchmark-timeout", type=int, default=900, help="Wall timeout for MoniTAal hard-coded benchmark sidecar; 0 disables.")
    parser.add_argument("--hardcoded-benchmark-case-timeout", type=int, default=30, help="Per hard-coded benchmark entrypoint timeout; 0 disables.")
    parser.add_argument("--hardcoded-benchmark-build-timeout", type=int, default=600, help="Build timeout for MoniTAal hard-coded benchmark binary; 0 disables.")
    parser.add_argument("--hardcoded-benchmark-length", type=int, default=20, help="Bounded event length for hard-coded benchmark entrypoints.")
    parser.add_argument("--formula-catalog-timeout", type=int, default=120, help="Wall timeout for MITL formula catalog generation; 0 disables.")
    parser.add_argument("--workbook-rebuild-timeout", type=int, default=180, help="Wall timeout for the final workbook rebuild after late diagnostics; 0 disables.")
    parser.add_argument("--stability-timeout", type=int, default=600, help="Wall timeout for result stability audit; 0 disables.")
    parser.add_argument("--stability-baseline", type=Path, default=None, help="Optional baseline result directory for compare_pipeline_results.py.")
    parser.add_argument("--stability-profile", choices=STABILITY_PROFILES, default="stable", help="Expected relationship between stability baseline and this candidate packet.")
    parser.add_argument("--py-compile-timeout", type=int, default=120, help="Wall timeout for Python syntax preflight; 0 disables.")
    parser.add_argument("--no-py-compile", action="store_true", help="Skip Python syntax preflight.")
    parser.add_argument("--no-build", action="store_true", help="Skip cmake --build for TAMonitor.")
    parser.add_argument("--no-run", action="store_true", help="Forward --no-run to run_paper_experiments.py.")
    parser.add_argument("--no-workbook", action="store_true", help="Forward --no-workbook to run_paper_experiments.py.")
    parser.add_argument("--skip-timeout-rerun", action="store_true", help="Skip rerun_baseline_timeouts.py.")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verify_review_packet.py.")
    parser.add_argument("--skip-signoff-validation", action="store_true", help="Skip generated Review Signoff validation.")
    parser.add_argument("--skip-signoff-evidence-bundle", action="store_true", help="Skip generated Review Signoff evidence bundle.")
    parser.add_argument("--skip-signoff-roundtrip", action="store_true", help="Skip synthetic Review Signoff import roundtrip audit.")
    parser.add_argument("--skip-benchmark-blocker-diagnostics", action="store_true", help="Skip benchmark blocker diagnostics for non-proof-ready XML rows.")
    parser.add_argument("--skip-monitaal-hardcoded-benchmarks", action="store_true", help="Skip MoniTAal benchmark/main.cpp hard-coded benchmark evidence.")
    parser.add_argument("--skip-formula-catalog", action="store_true", help="Skip generated MITL formula catalog artifacts.")
    parser.add_argument("--skip-stability-audit", action="store_true", help="Skip compare_pipeline_results.py even when --stability-baseline is provided.")
    parser.add_argument("--force", action="store_true", help="Allow non-empty output directories.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    pipeline_started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    pipeline_started_monotonic = time.perf_counter()

    output_dir = (args.out or REPO_ROOT / "test" / "TARV" / "results" / f"paper_pipeline_{timestamp()}").resolve()
    timeout_rerun_dir = (
        args.timeout_rerun_out
        or output_dir.parent / f"baseline_timeout_rerun_{args.timeout_rerun_seconds}s_{output_dir.name}"
    ).resolve()

    if not args.force:
        occupied = [path for path in [output_dir, timeout_rerun_dir] if directory_has_entries(path)]
        if occupied:
            for path in occupied:
                print(f"Refusing to write into non-empty directory without --force: {path}", file=sys.stderr)
            return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir / "pipeline_command_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    commands: list[dict[str, Any]] = []

    if not args.no_py_compile:
        py_compile_cmd = [
            sys.executable,
            "-m",
            "py_compile",
            *[str(path) for path in PIPELINE_SCRIPT_PATHS if path.exists()],
        ]
        commands.append(run_command("py_compile_pipeline_scripts", py_compile_cmd, REPO_ROOT, log_dir, args.py_compile_timeout))
        if commands[-1]["returncode"] != 0 or commands[-1]["timeout"]:
            experiment_summary: dict[str, Any] = {}
            timeout_summary: dict[str, Any] = {}
            verification_summary: dict[str, Any] = {}
            signoff_validation_summary: dict[str, Any] = {}
            signoff_evidence_summary: dict[str, Any] = {}
            signoff_roundtrip_summary: dict[str, Any] = {}
            stability_summary: dict[str, Any] = {}
            summary = make_summary(
                output_dir,
                timeout_rerun_dir,
                args,
                commands,
                experiment_summary,
                timeout_summary,
                verification_summary,
                signoff_validation_summary,
                signoff_evidence_summary,
                signoff_roundtrip_summary,
                stability_summary,
                pipeline_started_at,
                pipeline_started_monotonic,
                stability_required=False,
            )
            write_pipeline_outputs(output_dir, summary)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 1

    if not args.no_build:
        build_cmd = [
            "cmake",
            "--build",
            str(REPO_ROOT / "tool" / "MightyPPL" / "build"),
            "--target",
            "TAMonitor",
            f"-j{args.build_jobs}",
        ]
        commands.append(run_command("build_tamonitor", build_cmd, REPO_ROOT, log_dir, args.build_timeout))
        if commands[-1]["returncode"] != 0 or commands[-1]["timeout"]:
            experiment_summary: dict[str, Any] = {}
            timeout_summary: dict[str, Any] = {}
            verification_summary: dict[str, Any] = {}
            signoff_validation_summary: dict[str, Any] = {}
            signoff_evidence_summary: dict[str, Any] = {}
            signoff_roundtrip_summary: dict[str, Any] = {}
            stability_summary: dict[str, Any] = {}
            summary = make_summary(
                output_dir,
                timeout_rerun_dir,
                args,
                commands,
                experiment_summary,
                timeout_summary,
                verification_summary,
                signoff_validation_summary,
                signoff_evidence_summary,
                signoff_roundtrip_summary,
                stability_summary,
                pipeline_started_at,
                pipeline_started_monotonic,
                stability_required=False,
            )
            write_pipeline_outputs(output_dir, summary)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 1

    experiment_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "run_paper_experiments.py"),
        "--timeout",
        str(args.timeout),
        "--out",
        str(output_dir),
        "--tamonitor",
        str(args.tamonitor),
    ]
    if args.no_run:
        experiment_cmd.append("--no-run")
    if args.no_workbook:
        experiment_cmd.append("--no-workbook")
    commands.append(run_command("run_paper_experiments", experiment_cmd, REPO_ROOT, log_dir, args.experiment_wall_timeout))
    experiment_summary = read_json(output_dir / "experiment_summary.json")

    signoff_validation_summary: dict[str, Any] = {}
    if not args.skip_signoff_validation:
        signoff_validation_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "validate_review_signoff.py"),
            "--output-dir",
            str(output_dir),
            "--mode",
            "pre-review",
        ]
        commands.append(run_command("validate_review_signoff", signoff_validation_cmd, REPO_ROOT, log_dir, args.signoff_validation_timeout))
        signoff_data = read_json(output_dir / "review_signoff_validation.json")
        signoff_validation_summary = signoff_data.get("summary", signoff_data) if isinstance(signoff_data, dict) else {}

    signoff_evidence_summary: dict[str, Any] = {}
    if not args.skip_signoff_evidence_bundle:
        signoff_evidence_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "build_signoff_evidence_bundle.py"),
            "--output-dir",
            str(output_dir),
        ]
        commands.append(run_command("build_signoff_evidence_bundle", signoff_evidence_cmd, REPO_ROOT, log_dir, args.signoff_evidence_timeout))
        signoff_evidence_data = read_json(output_dir / "review_signoff_evidence_bundle.json")
        signoff_evidence_summary = signoff_evidence_data.get("summary", signoff_evidence_data) if isinstance(signoff_evidence_data, dict) else {}

    timeout_summary: dict[str, Any] = {}
    if not args.skip_timeout_rerun:
        timeout_rerun_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "rerun_baseline_timeouts.py"),
            "--source",
            str(output_dir),
            "--timeout",
            str(args.timeout_rerun_seconds),
            "--out",
            str(timeout_rerun_dir),
        ]
        if args.timeout_rerun_limit:
            timeout_rerun_cmd.extend(["--limit", str(args.timeout_rerun_limit)])
        commands.append(run_command("rerun_baseline_timeouts", timeout_rerun_cmd, REPO_ROOT, log_dir, args.rerun_wall_timeout))
        timeout_summary = read_json(timeout_rerun_dir / "baseline_timeout_rerun_summary.json")

    signoff_roundtrip_summary: dict[str, Any] = {}
    if not args.skip_signoff_roundtrip:
        signoff_roundtrip_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "audit_signoff_import_roundtrip.py"),
            "--output-dir",
            str(output_dir),
        ]
        if not args.skip_timeout_rerun:
            signoff_roundtrip_cmd.extend(["--timeout-rerun", str(timeout_rerun_dir)])
        commands.append(run_command("audit_signoff_import_roundtrip", signoff_roundtrip_cmd, REPO_ROOT, log_dir, args.signoff_roundtrip_timeout))
        roundtrip_data = read_json(output_dir / "signoff_import_roundtrip_audit.json")
        signoff_roundtrip_summary = roundtrip_data.get("summary", roundtrip_data) if isinstance(roundtrip_data, dict) else {}

    if not args.skip_benchmark_blocker_diagnostics:
        blocker_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "analyze_benchmark_blockers.py"),
            "--output-dir",
            str(output_dir),
            "--tamonitor",
            str(args.tamonitor),
            "--timeout",
            str(args.blocker_probe_timeout),
        ]
        commands.append(run_command("analyze_benchmark_blockers", blocker_cmd, REPO_ROOT, log_dir, args.blocker_diagnostics_timeout))

    if not args.skip_monitaal_hardcoded_benchmarks:
        hardcoded_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "run_monitaal_hardcoded_benchmarks.py"),
            "--output-dir",
            str(output_dir),
            "--length",
            str(args.hardcoded_benchmark_length),
            "--case-timeout",
            str(args.hardcoded_benchmark_case_timeout),
            "--build-timeout",
            str(args.hardcoded_benchmark_build_timeout),
            "--build-jobs",
            str(args.build_jobs),
        ]
        commands.append(run_command("run_monitaal_hardcoded_benchmarks", hardcoded_cmd, REPO_ROOT, log_dir, args.hardcoded_benchmark_timeout))

    if not args.skip_formula_catalog and not args.no_run:
        formula_catalog_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "build_mitl_formula_catalog.py"),
            "--packet",
            str(output_dir),
            "--out-dir",
            str(output_dir),
        ]
        commands.append(run_command("build_mitl_formula_catalog", formula_catalog_cmd, REPO_ROOT, log_dir, args.formula_catalog_timeout))

    if not args.no_workbook:
        rebuild_workbook_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "rebuild_review_workbook.py"),
            "--output-dir",
            str(output_dir),
        ]
        if not args.skip_timeout_rerun:
            rebuild_workbook_cmd.extend(["--timeout-rerun-dir", str(timeout_rerun_dir)])
        commands.append(run_command("rebuild_review_workbook_after_late_sidecars", rebuild_workbook_cmd, REPO_ROOT, log_dir, args.workbook_rebuild_timeout))
        experiment_summary = read_json(output_dir / "experiment_summary.json")

    verification_summary: dict[str, Any] = {}
    if not args.skip_verify:
        verify_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "verify_review_packet.py"),
            "--output-dir",
            str(output_dir),
        ]
        if not args.skip_timeout_rerun:
            verify_cmd.extend(["--timeout-rerun", str(timeout_rerun_dir)])
        commands.append(run_command("verify_review_packet", verify_cmd, REPO_ROOT, log_dir, args.verify_timeout))
        verification_summary = read_json(output_dir / "review_packet_verification.json")

    stability_summary: dict[str, Any] = {}
    if args.stability_baseline and not args.skip_stability_audit:
        interim_summary = make_summary(
            output_dir,
            timeout_rerun_dir,
            args,
            commands,
            experiment_summary,
            timeout_summary,
            verification_summary,
            signoff_validation_summary,
            signoff_evidence_summary,
            signoff_roundtrip_summary,
            stability_summary,
            pipeline_started_at,
            pipeline_started_monotonic,
            stability_required=False,
        )
        write_pipeline_outputs(output_dir, interim_summary)
        stability_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "compare_pipeline_results.py"),
            "--profile",
            args.stability_profile,
            "--baseline",
            str(args.stability_baseline),
            "--candidate",
            str(output_dir),
            "--out-dir",
            str(output_dir),
        ]
        commands.append(run_command("compare_result_stability", stability_cmd, REPO_ROOT, log_dir, args.stability_timeout))
        stability_data = read_json(output_dir / "result_stability_audit.json")
        stability_summary = stability_data.get("summary", stability_data) if isinstance(stability_data, dict) else {}

    summary = make_summary(
        output_dir,
        timeout_rerun_dir,
        args,
        commands,
        experiment_summary,
        timeout_summary,
        verification_summary,
        signoff_validation_summary,
        signoff_evidence_summary,
        signoff_roundtrip_summary,
        stability_summary,
        pipeline_started_at,
        pipeline_started_monotonic,
        stability_required=True,
    )
    write_pipeline_outputs(output_dir, summary)
    manifest_postcheck_rc = 0
    if not args.no_run and not args.no_workbook and not args.skip_verify:
        manifest_postcheck_rc = run_pipeline_manifest_postcheck(output_dir, timeout_rerun_dir, args)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["failed_steps"] or manifest_postcheck_rc else 0


def make_summary(
    output_dir: Path,
    timeout_rerun_dir: Path,
    args: argparse.Namespace,
    commands: list[dict[str, Any]],
    experiment_summary: dict[str, Any],
    timeout_summary: dict[str, Any],
    verification_summary: dict[str, Any],
    signoff_validation_summary: dict[str, Any],
    signoff_evidence_summary: dict[str, Any],
    signoff_roundtrip_summary: dict[str, Any],
    stability_summary: dict[str, Any],
    pipeline_started_at: str,
    pipeline_started_monotonic: float,
    stability_required: bool,
) -> dict[str, Any]:
    failed = fail_reasons(
        commands,
        experiment_summary,
        timeout_summary,
        verification_summary,
        signoff_validation_summary,
        signoff_evidence_summary,
        signoff_roundtrip_summary,
        args,
        stability_summary,
        stability_required,
    )
    caveats = caveat_reasons(experiment_summary, timeout_summary, verification_summary, stability_summary, args)
    reduction_flags = []
    if args.no_build:
        reduction_flags.append("no_build")
    if args.no_py_compile:
        reduction_flags.append("no_py_compile")
    if args.no_run:
        reduction_flags.append("no_run")
    if args.no_workbook:
        reduction_flags.append("no_workbook")
    if args.skip_timeout_rerun:
        reduction_flags.append("skip_timeout_rerun")
    if args.skip_verify:
        reduction_flags.append("skip_verify")
    if args.skip_signoff_validation:
        reduction_flags.append("skip_signoff_validation")
    if args.skip_signoff_evidence_bundle:
        reduction_flags.append("skip_signoff_evidence_bundle")
    if args.skip_signoff_roundtrip:
        reduction_flags.append("skip_signoff_roundtrip")
    if args.skip_benchmark_blocker_diagnostics:
        reduction_flags.append("skip_benchmark_blocker_diagnostics")
    if args.skip_monitaal_hardcoded_benchmarks:
        reduction_flags.append("skip_monitaal_hardcoded_benchmarks")
    if args.skip_formula_catalog:
        reduction_flags.append("skip_formula_catalog")
    if args.skip_stability_audit and args.stability_baseline:
        reduction_flags.append("skip_stability_audit")
    if args.timeout_rerun_limit:
        reduction_flags.append("timeout_rerun_limit")
    pipeline_mode = "full" if not reduction_flags else "partial:" + ",".join(reduction_flags)
    pipeline_status = "FAIL" if failed else ("PARTIAL" if reduction_flags else "PASS")
    finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
    elapsed_ms = int((time.perf_counter() - pipeline_started_monotonic) * 1000)
    artifacts = {
        "workbook": str(output_dir / "paper_review_results.xlsx"),
        "review_guide": str(output_dir / "review_guide.md"),
        "manual_oracle_guide": str(output_dir / "manual_oracle_guide.md"),
        "review_queue": str(output_dir / "human_review_queue.md"),
        "review_signoff_template": str(output_dir / "review_signoff_template.md"),
        "review_signoff_evidence_bundle": str(output_dir / "review_signoff_evidence_bundle.md"),
        "review_signoff_validation": str(output_dir / "review_signoff_validation.md"),
        "xml_proof_obligations": str(output_dir / "xml_proof_obligations.md"),
        "xml_trace_coverage_obligations": str(output_dir / "xml_trace_coverage_obligations.md"),
        "xml_original_trace_gaps": str(output_dir / "xml_original_trace_gaps.md"),
        "signoff_import_roundtrip_audit": str(output_dir / "signoff_import_roundtrip_audit.md"),
        "reproducibility_manifest": str(output_dir / "reproducibility_manifest.md"),
        "review_packet_verification": str(output_dir / "review_packet_verification.md"),
        "benchmark_blocker_diagnostics": str(output_dir / "benchmark_blocker_diagnostics.md"),
        "workbook_rebuild_summary": str(output_dir / "workbook_rebuild_summary.md"),
        "pipeline_artifact_manifest": str(output_dir / "pipeline_artifact_manifest.md"),
        "pipeline_artifact_manifest_verification": str(output_dir / "pipeline_artifact_manifest_verification.md"),
        "pipeline_summary": str(output_dir / "pipeline_summary.md"),
    }
    hardcoded_summary = read_json(output_dir / "monitaal_hardcoded_benchmarks.json")
    if not args.skip_monitaal_hardcoded_benchmarks or hardcoded_summary:
        artifacts["monitaal_hardcoded_benchmarks"] = str(output_dir / "monitaal_hardcoded_benchmarks.md")
    if args.stability_baseline or (output_dir / "result_stability_audit.md").exists():
        artifacts["result_stability_audit"] = str(output_dir / "result_stability_audit.md")
    if not args.skip_timeout_rerun:
        artifacts["timeout_rerun"] = str(timeout_rerun_dir / "baseline_timeout_rerun.md")
    if not args.skip_formula_catalog and (not args.no_run or (output_dir / "mitl_formula_catalog_summary.json").exists()):
        artifacts["mitl_formula_catalog"] = str(output_dir / "mitl_formula_catalog_latest_official.md")
        artifacts["mitl_formula_catalog_summary"] = str(output_dir / "mitl_formula_catalog_summary.json")
    return {
        "created_at": finished_at,
        "started_at": pipeline_started_at,
        "finished_at": finished_at,
        "elapsed_ms": elapsed_ms,
        "pipeline_status": pipeline_status,
        "pipeline_mode": pipeline_mode,
        "failed_steps": failed,
        "caveats": caveats,
        "repo_root": str(REPO_ROOT),
        "output_dir": str(output_dir),
        "timeout_rerun_dir": "" if args.skip_timeout_rerun else str(timeout_rerun_dir),
        "workbook_path": str(output_dir / "paper_review_results.xlsx") if (output_dir / "paper_review_results.xlsx").exists() else "",
        "artifacts": artifacts,
        "options": {
            "timeout": args.timeout,
            "timeout_rerun_seconds": args.timeout_rerun_seconds,
            "timeout_rerun_limit": args.timeout_rerun_limit,
            "tamonitor": str(args.tamonitor),
            "py_compile_timeout": args.py_compile_timeout,
            "workbook_rebuild_timeout": args.workbook_rebuild_timeout,
            "no_build": args.no_build,
            "no_py_compile": args.no_py_compile,
            "no_run": args.no_run,
            "no_workbook": args.no_workbook,
            "skip_timeout_rerun": args.skip_timeout_rerun,
            "skip_verify": args.skip_verify,
            "skip_signoff_validation": args.skip_signoff_validation,
            "skip_signoff_evidence_bundle": args.skip_signoff_evidence_bundle,
            "skip_signoff_roundtrip": args.skip_signoff_roundtrip,
            "skip_benchmark_blocker_diagnostics": args.skip_benchmark_blocker_diagnostics,
            "skip_monitaal_hardcoded_benchmarks": args.skip_monitaal_hardcoded_benchmarks,
            "skip_formula_catalog": args.skip_formula_catalog,
            "formula_catalog_timeout": args.formula_catalog_timeout,
            "hardcoded_benchmark_length": args.hardcoded_benchmark_length,
            "hardcoded_benchmark_case_timeout": args.hardcoded_benchmark_case_timeout,
            "hardcoded_benchmark_build_timeout": args.hardcoded_benchmark_build_timeout,
            "hardcoded_benchmark_timeout": args.hardcoded_benchmark_timeout,
            "signoff_evidence_timeout": args.signoff_evidence_timeout,
            "signoff_roundtrip_timeout": args.signoff_roundtrip_timeout,
            "skip_stability_audit": args.skip_stability_audit,
            "stability_baseline": str(args.stability_baseline) if args.stability_baseline else "",
            "stability_profile": args.stability_profile,
            "stability_timeout": args.stability_timeout,
        },
        "commands": commands,
        "experiment_summary": experiment_summary,
        "timeout_rerun_summary": timeout_summary,
        "monitaal_hardcoded_benchmarks": hardcoded_summary,
        "review_packet_verification": verification_summary,
        "review_signoff_validation": signoff_validation_summary,
        "review_signoff_evidence_bundle": signoff_evidence_summary,
        "signoff_import_roundtrip_audit": signoff_roundtrip_summary,
        "result_stability_audit": stability_summary,
    }


def write_pipeline_outputs(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(output_dir / "pipeline_summary.csv", flatten_for_csv(summary), ["key", "value", "evidence"])
    write_markdown(output_dir / "pipeline_summary.md", summary)
    write_pipeline_artifact_manifest(output_dir, summary)


def run_pipeline_manifest_postcheck(output_dir: Path, timeout_rerun_dir: Path, args: argparse.Namespace) -> int:
    verify_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "verify_pipeline_artifact_manifest.py"),
        "--output-dir",
        str(output_dir),
    ]
    if not args.skip_timeout_rerun:
        verify_cmd.extend(["--timeout-rerun", str(timeout_rerun_dir)])
    try:
        completed = subprocess.run(
            verify_cmd,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"pipeline artifact manifest verification timed out after {exc.timeout}s", file=sys.stderr)
        return 1
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, file=sys.stderr)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
