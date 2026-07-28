#!/usr/bin/env python3
"""Static and strace-based answer-leakage gates for RIFT analyzers."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


sys.dont_write_bytecode = True

TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cmake",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".inc",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".td",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
CATEGORIES = (
    "direct_data",
    "indirect_data",
    "control_only",
    "alias_object_field",
    "config_threshold",
    "message_parser_state",
    "async_timer_callback_queue",
    "setup_mode_prerequisite",
    "timing_drop_repeat_reorder",
    "uncontrollable_false_correlation",
    "one_input_multi_ap",
    "joint_inputs",
)
FORBIDDEN_RULES = (
    ("gold_path", re.compile(r"(?:benchmark[/\\]rift[/\\]gold|[/\\]rift[/\\]gold)(?:[/\\]|$)", re.I)),
    ("ground_truth_path", re.compile(r"\bground_truth(?:[/\\]|\b)", re.I)),
    ("gold_case_id", re.compile(r"\bRIFT-GOLD-[0-9]{3}\b", re.I)),
    (
        "original_gold_filename",
        re.compile(
            rf"\b[0-9]{{3}}_(?:{'|'.join(CATEGORIES)})_(?:must|may|negative)_v[0-9]+\.(?:c|cpp|json)\b",
            re.I,
        ),
    ),
    ("gold_relation_field", re.compile(r"\bcase_relation\b", re.I)),
    ("gold_expected_field", re.compile(r"\bexpected_(?:edge|relation|frontier|path|label)s?\b", re.I)),
    ("gold_relation_label", re.compile(r"\b(?:MUST_INFLUENCE|MAY_INFLUENCE|NO_INFLUENCE)\b")),
    ("benchmark_category_literal", re.compile(rf"\b(?:{'|'.join(CATEGORIES)})\b", re.I)),
)
QUOTED = re.compile(r'"((?:\\.|[^"\\])*)"')


class LeakageError(ValueError):
    """Raised when audit arguments themselves expose private benchmark data."""


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


def text_files(root: Path) -> list[Path]:
    root = root.resolve()
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise LeakageError(f"analyzer root does not exist: {root}")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if path.is_file() and (path.suffix.lower() in TEXT_SUFFIXES or path.name == "CMakeLists.txt"):
            files.append(path)
    return files


def find_violations(text: str, path: Path) -> list[dict[str, Any]]:
    violations = []
    for rule, pattern in FORBIDDEN_RULES:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            column = match.start() - text.rfind("\n", 0, match.start())
            violations.append(
                {
                    "rule": rule,
                    "path": str(path),
                    "line": line,
                    "column": column,
                    "token": match.group(0),
                }
            )
    return violations


def scan_roots(roots: Iterable[Path]) -> dict[str, Any]:
    files: list[Path] = []
    for root in roots:
        files.extend(text_files(root))
    unique_files = sorted(set(files))
    violations: list[dict[str, Any]] = []
    for path in unique_files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        violations.extend(find_violations(text, path))
    return {
        "status": "PASS" if not violations else "FAIL",
        "files_scanned": len(unique_files),
        "violations": violations,
    }


def decode_quoted(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return raw.replace(r"\"", '"').replace(r"\\", "\\")


def traced_paths(trace: str, cwd: Path) -> set[Path]:
    paths: set[Path] = set()
    for line in trace.splitlines():
        for raw in QUOTED.findall(line):
            value = decode_quoted(raw)
            if "/" not in value and not value.startswith("."):
                continue
            value = value.removesuffix(" (deleted)")
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = cwd / candidate
            try:
                paths.add(candidate.resolve(strict=False))
            except OSError:
                paths.add(candidate.absolute())
    return paths


def is_within(path: Path, root: Path) -> bool:
    if path == root:
        return True
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def default_runtime_roots() -> set[Path]:
    roots = {
        Path("/usr"),
        Path("/lib"),
        Path("/lib64"),
        Path("/etc"),
        Path("/proc"),
        Path("/dev"),
        Path("/sys"),
    }
    for value in sys.path:
        if value:
            path = Path(value).resolve(strict=False)
            is_system = any(
                is_within(path, root)
                for root in (Path("/usr"), Path("/lib"), Path("/lib64"))
            )
            is_installed_package_tree = any(
                part in {"site-packages", "dist-packages"} for part in path.parts
            )
            if path.exists() and (is_system or is_installed_package_tree):
                roots.add(path)
    roots.add(Path(sys.executable).resolve())
    return {root.resolve(strict=False) for root in roots if root.exists()}


def validate_no_private_text(values: Iterable[str], label: str) -> None:
    joined = "\n".join(values)
    violations = find_violations(joined, Path(f"<{label}>"))
    if violations:
        raise LeakageError(f"{label} contains private benchmark token: {violations[0]['token']!r}")


def audit(
    *,
    sanitized_root: Path,
    analyzer_roots: list[Path],
    extra_allowed_roots: list[Path],
    command: list[str],
    trace_output: Path | None,
    timeout: int,
) -> dict[str, Any]:
    strace = shutil.which("strace")
    if strace is None:
        return {
            "status": "NOT_RUN",
            "reason": "strace is unavailable",
            "command_exit_code": None,
            "files_scanned": 0,
            "paths_observed": 0,
            "violations": [],
        }
    sanitized_root = sanitized_root.resolve()
    if not (sanitized_root / "analyzer_input.json").is_file():
        raise LeakageError("sanitized root has no analyzer_input.json")
    if not (sanitized_root / "compile_commands.json").is_file():
        raise LeakageError("sanitized root has no compile_commands.json")
    if not command:
        raise LeakageError("audit command is empty")

    static = scan_roots(analyzer_roots)
    sanitized_scan = scan_roots([sanitized_root])
    if static["status"] != "PASS" or sanitized_scan["status"] != "PASS":
        return {
            "status": "FAIL",
            "reason": "static analyzer or sanitized-package answer-leakage scan failed",
            "command_exit_code": None,
            "files_scanned": static["files_scanned"] + sanitized_scan["files_scanned"],
            "paths_observed": 0,
            "violations": static["violations"] + sanitized_scan["violations"],
        }
    validate_no_private_text(command, "command")
    validate_no_private_text(
        [f"{name}={value}" for name, value in os.environ.items()], "environment"
    )

    if trace_output is None:
        handle = tempfile.NamedTemporaryFile(
            prefix="rift-m3-strace-", suffix=".log", dir="/tmp", delete=False
        )
        handle.close()
        trace_output = Path(handle.name)
    else:
        trace_output = trace_output.resolve()
        if trace_output.exists():
            raise LeakageError(f"refusing to overwrite trace output: {trace_output}")

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    traced_command = [
        strace,
        "-f",
        "-qq",
        "-s",
        "4096",
        "-e",
        "trace=%file",
        "-o",
        str(trace_output),
        *command,
    ]
    try:
        result = subprocess.run(
            traced_command,
            cwd=sanitized_root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "status": "FAIL",
            "reason": f"analyzer timed out after {timeout}s",
            "command_exit_code": None,
            "files_scanned": static["files_scanned"] + sanitized_scan["files_scanned"],
            "paths_observed": 0,
            "violations": [],
            "stdout": (error.stdout or "")[-2000:],
            "stderr": (error.stderr or "")[-2000:],
            "trace_output": str(trace_output),
        }

    observed = traced_paths(trace_output.read_text(encoding="utf-8", errors="replace"), sanitized_root)
    allowed_roots = {sanitized_root, *default_runtime_roots()}
    allowed_roots.update(root.resolve(strict=False) for root in analyzer_roots)
    allowed_roots.update(root.resolve(strict=False) for root in extra_allowed_roots)

    workspace = Path(__file__).resolve().parents[3]
    hard_forbidden = [
        workspace / "benchmark" / "rift" / "gold",
        workspace / ".codex",
    ]
    violations = []
    for path in sorted(observed):
        if any(is_within(path, forbidden.resolve()) for forbidden in hard_forbidden):
            violations.append(
                {"rule": "private_runtime_read", "path": str(path)}
            )
            continue
        # Path resolution commonly stats each ancestor of an allowed file/root.
        if not any(
            is_within(path, root) or is_within(root, path) for root in allowed_roots
        ):
            violations.append(
                {"rule": "outside_sanitized_or_runtime_allowlist", "path": str(path)}
            )

    status = "PASS" if result.returncode == 0 and not violations else "FAIL"
    reason = (
        "analyzer read only sanitized/analyzer/toolchain-runtime roots"
        if status == "PASS"
        else "analyzer failed or accessed a path outside the read allowlist"
    )
    return {
        "status": status,
        "reason": reason,
        "command": command,
        "command_exit_code": result.returncode,
        "files_scanned": static["files_scanned"] + sanitized_scan["files_scanned"],
        "paths_observed": len(observed),
        "allowed_roots": sorted(str(path) for path in allowed_roots),
        "violations": violations,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
        "trace_output": str(trace_output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    scan_parser = subparsers.add_parser("scan", help="scan analyzer source/config for answer literals")
    scan_parser.add_argument("--analyzer-root", type=Path, action="append", required=True)
    scan_parser.add_argument("--report", type=Path)

    audit_parser = subparsers.add_parser("audit", help="static scan, then audit file access with strace")
    audit_parser.add_argument("--sanitized-root", type=Path, required=True)
    audit_parser.add_argument("--analyzer-root", type=Path, action="append", required=True)
    audit_parser.add_argument("--allow-read-root", type=Path, action="append", default=[])
    audit_parser.add_argument("--trace-output", type=Path)
    audit_parser.add_argument("--report", type=Path)
    audit_parser.add_argument("--timeout", type=int, default=120)
    audit_parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    try:
        if args.subcommand == "scan":
            report = {"schema_version": "rift.no-answer-leakage.v1", **scan_roots(args.analyzer_root)}
        else:
            command = args.command[1:] if args.command and args.command[0] == "--" else args.command
            report = {
                "schema_version": "rift.no-answer-leakage.v1",
                **audit(
                    sanitized_root=args.sanitized_root,
                    analyzer_roots=args.analyzer_root,
                    extra_allowed_roots=args.allow_read_root,
                    command=command,
                    trace_output=args.trace_output,
                    timeout=args.timeout,
                ),
            }
        write_report(args.report, report)
    except (OSError, LeakageError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0 if report["status"] == "PASS" else 2 if report["status"] == "NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
