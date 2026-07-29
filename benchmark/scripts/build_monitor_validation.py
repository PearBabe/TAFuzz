#!/usr/bin/env python3
"""Build and validate Milestone 7 synthetic monitor evidence.

This stage validates formula syntax and deliberately constructed timed words.
It does not consume flight-controller traces and does not assess firmware
conformance.  TAMonitor is invoked as the real monitor.  A small, explicitly
identified reference oracle supplies independent pointwise finite-word checks;
its results are never presented as TAMonitor results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
OUTPUT = BENCHMARK / "extraction_runs" / "milestone7" / "monitor_validation"
MAIN_OUTPUT = OUTPUT / "monitor_validation.json"
MANIFEST_OUTPUT = OUTPUT / "manifest.json"
COMMANDS_OUTPUT = OUTPUT / "commands.jsonl"
REPORT_OUTPUT = OUTPUT / "README.md"
TRACE_SCHEMA = BENCHMARK / "schemas" / "timed_trace.schema.json"
TAMONITOR = ROOT / "tool" / "MightyPPL" / "build" / "TAMonitor"
MITPPL = ROOT / "tool" / "MightyPPL" / "build" / "mitppl"
MONITAAL_BIN = (
    ROOT
    / "tool"
    / "MightyPPL"
    / "build"
    / "monitaal-prefix"
    / "src"
    / "monitaal-build"
    / "src"
    / "monitaal-bin"
    / "MoniTAal-bin"
)
MONITAAL_LIBRARY = (
    ROOT / "tool" / "MightyPPL" / "external" / "monitaal" / "lib" / "libMoniTAal.a"
)

SCHEMA_VERSION = "1.0"
GENERATOR_ID = "tafuzz-monitor-validation-builder/1.0"
ORACLE_ID = "TAFuzz deterministic pointwise finite-word reference oracle/1.0"
TICK_UNIT = "ms"
TICKS_PER_SECOND = 1000
TRIGGER_TIME_TICKS = 1000
NO_EPSILON_POLICY = (
    "No epsilon or tolerance is introduced. Source seconds are rescaled exactly "
    "to integer milliseconds. T-1 and T+1 are distinct synthetic clock ticks used "
    "only to exercise open/closed endpoints; they do not move a property boundary."
)

TOOL_SOURCE_PATHS = (
    ROOT / "tool" / "MightyPPL" / "README.md",
    ROOT / "tool" / "MightyPPL" / "Mitl.g4",
    ROOT / "src" / "TAMonitor" / "TAMonitorOptions.cpp",
    ROOT / "src" / "TAMonitor" / "TAMonitorMightyAdapter.cpp",
    ROOT / "src" / "TAMonitor" / "TraceParser.cpp",
    ROOT / "src" / "TAMonitor" / "MonitorRunner.cpp",
    ROOT / "src" / "TAMonitor" / "TAMonitorMain.cpp",
    ROOT / "tool" / "MoniTAal" / "README.md",
    ROOT / "tool" / "MoniTAal" / "src" / "monitaal-bin" / "main.cpp",
    ROOT / "tool" / "MoniTAal" / "src" / "monitaal" / "Parser.cpp",
    ROOT / "tool" / "MoniTAal" / "src" / "monitaal" / "EventParser.cpp",
    ROOT / "tool" / "MoniTAal" / "src" / "monitaal" / "Monitor.cpp",
    ROOT / "tool" / "MoniTAal" / "src" / "monitaal" / "Monitor.h",
    ROOT / "tool" / "MoniTAal" / "src" / "monitaal" / "state.cpp",
    ROOT / "tool" / "MightyPPL" / "CMakeLists.txt",
    ROOT / "tool" / "MightyPPL" / "build" / "CMakeFiles" / "TAMonitor.dir" / "link.txt",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def tree_hash_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


@dataclass(frozen=True)
class Interval:
    lower: int
    upper: int | None
    lower_closed: bool
    upper_closed: bool

    def contains(self, value: int) -> bool:
        lower_ok = value >= self.lower if self.lower_closed else value > self.lower
        if self.upper is None:
            upper_ok = True
        else:
            upper_ok = value <= self.upper if self.upper_closed else value < self.upper
        return lower_ok and upper_ok

    def as_json(self) -> dict[str, Any]:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "lower_closed": self.lower_closed,
            "upper_closed": self.upper_closed,
            "unit": TICK_UNIT,
        }


@dataclass(frozen=True)
class Node:
    op: str
    args: tuple["Node", ...] = ()
    name: str | None = None
    interval: Interval | None = None

    def as_json(self) -> dict[str, Any]:
        value: dict[str, Any] = {"op": self.op}
        if self.name is not None:
            value["name"] = self.name
        if self.interval is not None:
            value["interval"] = self.interval.as_json()
        if self.args:
            value["args"] = [arg.as_json() for arg in self.args]
        return value

    def names(self) -> set[str]:
        result = {self.name} if self.name is not None else set()
        for arg in self.args:
            result.update(arg.names())
        return result


TOKEN_RE = re.compile(r"\s*(<->|->|&&|\|\||!|\(|\)|\[|\]|,|G|F|infty|[0-9]+|[a-z][A-Za-z0-9_]*)")


class FormulaParser:
    """Parser for the exact G/F Boolean subset used by the eight properties."""

    def __init__(self, text: str):
        self.tokens: list[str] = []
        offset = 0
        while offset < len(text):
            match = TOKEN_RE.match(text, offset)
            if match is None:
                raise ValueError(f"reference oracle token error at offset {offset}: {text[offset:offset + 24]!r}")
            self.tokens.append(match.group(1))
            offset = match.end()
        self.index = 0

    def peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end of formula")
        if expected is not None and token != expected:
            raise ValueError(f"expected {expected!r}, got {token!r}")
        self.index += 1
        return token

    def parse(self) -> Node:
        result = self.parse_iff()
        if self.peek() is not None:
            raise ValueError(f"unexpected trailing token {self.peek()!r}")
        return result

    def parse_iff(self) -> Node:
        left = self.parse_implies()
        while self.peek() == "<->":
            self.take()
            left = Node("IFF", (left, self.parse_implies()))
        return left

    def parse_implies(self) -> Node:
        left = self.parse_or()
        if self.peek() == "->":
            self.take()
            return Node("IMPLIES", (left, self.parse_implies()))
        return left

    def parse_or(self) -> Node:
        left = self.parse_and()
        while self.peek() == "||":
            self.take()
            left = Node("OR", (left, self.parse_and()))
        return left

    def parse_and(self) -> Node:
        left = self.parse_unary()
        while self.peek() == "&&":
            self.take()
            left = Node("AND", (left, self.parse_unary()))
        return left

    def parse_interval(self) -> Interval | None:
        if self.peek() not in {"[", "("}:
            return None
        if self.peek() == "(" and (
            self.index + 2 >= len(self.tokens)
            or not self.tokens[self.index + 1].isdigit()
            or self.tokens[self.index + 2] != ","
        ):
            return None
        opener = self.take()
        lower_token = self.take()
        require(lower_token.isdigit(), f"invalid lower interval token {lower_token!r}")
        self.take(",")
        upper_token = self.take()
        require(upper_token == "infty" or upper_token.isdigit(), f"invalid upper interval token {upper_token!r}")
        closer = self.take()
        require(closer in {"]", ")"}, f"invalid interval close {closer!r}")
        return Interval(
            lower=int(lower_token),
            upper=None if upper_token == "infty" else int(upper_token),
            lower_closed=opener == "[",
            upper_closed=closer == "]",
        )

    def parse_unary(self) -> Node:
        token = self.peek()
        if token == "!":
            self.take()
            return Node("NOT", (self.parse_unary(),))
        if token in {"G", "F"}:
            op = self.take()
            interval = self.parse_interval() or Interval(0, None, True, False)
            return Node(op, (self.parse_unary(),), interval=interval)
        if token == "(":
            self.take()
            value = self.parse_iff()
            self.take(")")
            return value
        if token in {"true", "false"}:
            self.take()
            return Node(token.upper())
        if token is not None and re.fullmatch(r"[a-z][A-Za-z0-9_]*", token):
            return Node("ATOM", name=self.take())
        raise ValueError(f"unexpected formula token {token!r}")


def oracle_eval(node: Node, events: list[dict[str, Any]], index: int) -> bool:
    op = node.op
    if op == "ATOM":
        return bool(events[index]["values"].get(node.name, False))
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "NOT":
        return not oracle_eval(node.args[0], events, index)
    if op == "AND":
        return oracle_eval(node.args[0], events, index) and oracle_eval(node.args[1], events, index)
    if op == "OR":
        return oracle_eval(node.args[0], events, index) or oracle_eval(node.args[1], events, index)
    if op == "IMPLIES":
        return (not oracle_eval(node.args[0], events, index)) or oracle_eval(node.args[1], events, index)
    if op == "IFF":
        return oracle_eval(node.args[0], events, index) == oracle_eval(node.args[1], events, index)
    if op in {"G", "F"}:
        interval = node.interval
        require(interval is not None, f"{op} node lacks interval")
        start = events[index]["time"]
        selected = [
            position
            for position in range(index, len(events))
            if interval.contains(events[position]["time"] - start)
        ]
        if op == "G":
            return all(oracle_eval(node.args[0], events, position) for position in selected)
        return any(oracle_eval(node.args[0], events, position) for position in selected)
    raise ValueError(f"unsupported oracle AST operation {op}")


def source_to_monitor_formula(source: str) -> tuple[str, list[dict[str, Any]]]:
    """Translate presentation syntax to exact integer-millisecond MightyPPL syntax."""

    conversions: list[dict[str, Any]] = []

    def scale_interval(match: re.Match[str]) -> str:
        opener, lower_text, upper_text, closer = match.groups()

        def scale(value: str) -> str:
            if value == "infty":
                return value
            ticks = Decimal(value) * TICKS_PER_SECOND
            require(ticks == ticks.to_integral_value(), f"non-integral millisecond bound: {value}")
            converted = str(int(ticks))
            conversions.append({"source_seconds": value, "monitor_ticks": int(ticks)})
            return converted

        return f"{opener}{scale(lower_text)},{scale(upper_text)}{closer}"

    formula = re.sub(r"([\[(])(\d+(?:\.\d+)?),(\d+(?:\.\d+)?|infty)([\])])", scale_interval, source)
    formula = re.sub(r"\b([GFOH])_([\[(])", r"\1\2", formula)
    formula = re.sub(r"(?<!&)&(?!&)", "&&", formula)
    formula = re.sub(r"!([a-z][A-Za-z0-9_]*)", r"(!\1)", formula)
    return formula, conversions


def true_names(values: dict[str, bool], ap_order: list[str]) -> str:
    selected = [name for name in ap_order if values[name]]
    return "{" + " ".join(selected) + "}" if selected else "-"


def trace_document(
    property_id: str,
    trace_id: str,
    clock_domain: str,
    ap_order: list[str],
    rows: Iterable[tuple[int, set[str]]],
    notes: str,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for seq, (time, selected) in enumerate(sorted(rows)):
        values = {name: name in selected for name in ap_order}
        events.append(
            {
                "seq": seq,
                "time": time,
                "event_id": "synthetic_ap_valuation",
                "scope_id": property_id,
                "correlation_id": trace_id,
                "values": values,
                "source": "SYNTHETIC_MONITOR_VALIDATION_NOT_FIRMWARE_TRACE",
                "fresh": True,
            }
        )
    require(all(events[i]["time"] < events[i + 1]["time"] for i in range(len(events) - 1)), f"{trace_id}: times not strictly increasing")
    return {
        "schema_version": "1.0",
        "trace_id": trace_id,
        "property_id": property_id,
        "clock_domain": clock_domain,
        "epoch": "synthetic_zero_integer_milliseconds",
        "events": events,
        "dropped_event_count": 0,
        "notes": notes,
    }


def make_rows(
    ap_order: list[str],
    trigger: str,
    response: str,
    guards: list[str],
    threshold: int,
    response_delta: int | None,
    *,
    trigger_enabled: bool = True,
) -> list[tuple[int, set[str]]]:
    trigger_time = TRIGGER_TIME_TICKS
    boundary = trigger_time + threshold
    horizon = max(boundary + 1000, trigger_time + (response_delta or threshold) + 1000)
    times = {0, trigger_time, boundary, horizon}
    if threshold > 0:
        times.add(boundary - 1)
    if response_delta is not None:
        times.add(trigger_time + response_delta)

    rows: list[tuple[int, set[str]]] = []
    for time in sorted(times):
        selected: set[str] = set()
        if time >= trigger_time:
            selected.update(guards)
        if time == trigger_time and trigger_enabled:
            selected.add(trigger)
        if response_delta is not None and time == trigger_time + response_delta:
            selected.add(response)
        require(selected.issubset(set(ap_order)), f"unknown AP in trace for {trigger}")
        rows.append((time, selected))
    return rows


def case_specs(lower_closed: bool, threshold: int) -> list[dict[str, Any]]:
    specs = [
        {
            "case_kind": "positive_after_threshold",
            "boundary_region": "after",
            "response_delta": threshold + 1000,
            "expected": True,
            "reason": "Response occurs strictly after the lower threshold and no response occurs before it.",
        },
        {
            "case_kind": "too_early_one_tick",
            "boundary_region": "before",
            "response_delta": threshold - 1,
            "expected": False,
            "reason": "Response occurs one exact monitor tick before the threshold.",
        },
        {
            "case_kind": "late_response_unbounded_legal",
            "boundary_region": "after",
            "response_delta": threshold * 3,
            "expected": True,
            "reason": "The source formula has no finite upper response bound; a late response is legal, not a violation.",
        },
        {
            "case_kind": "missing_completed_trace",
            "boundary_region": "missing",
            "response_delta": None,
            "expected": False,
            "reason": "The independent oracle treats this synthetic finite word as complete and no required response occurs.",
        },
        {
            "case_kind": "vacuous_trigger_control",
            "boundary_region": "vacuous",
            "response_delta": threshold - 1,
            "expected": True,
            "trigger_enabled": False,
            "reason": "Control trace disables the trigger while retaining the early response; it is paired with the non-vacuous counterexample.",
        },
    ]
    if lower_closed:
        specs.insert(
            1,
            {
                "case_kind": "boundary_exact_legal",
                "boundary_region": "exact",
                "response_delta": threshold,
                "expected": True,
                "reason": "Closed eventual lower bound and open pre-threshold prohibition make the exact threshold legal.",
            },
        )
    else:
        specs[1:1] = [
            {
                "case_kind": "boundary_first_grid_point_legal",
                "boundary_region": "after",
                "response_delta": threshold + 1,
                "expected": True,
                "reason": "An open dense-time lower boundary has no least legal instant; T+1 ms is an exact grid witness, not epsilon.",
            },
            {
                "case_kind": "boundary_exact_excluded",
                "boundary_region": "exact",
                "response_delta": threshold,
                "expected": False,
                "reason": "The response is prohibited through the closed threshold and the eventual interval is open at that threshold.",
            },
        ]
    return specs


def run_command(
    commands: list[dict[str, Any]],
    command_id: str,
    purpose: str,
    argv: list[str],
    stdout_path: Path,
    stderr_path: Path,
    *,
    cwd: Path = ROOT,
    timeout: int = 60,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    exit_code: int
    timed_out = False

    def disable_core_dumps() -> None:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            preexec_fn=disable_core_dumps,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        stderr += f"\nTIMEOUT after {timeout} seconds\n"
        exit_code = 124
        timed_out = True

    write_text(stdout_path, stdout)
    write_text(stderr_path, stderr)
    executable = Path(argv[0])
    record = {
        "command_id": command_id,
        "purpose": purpose,
        "argv": argv,
        "cwd": str(cwd.resolve()),
        "environment_overrides": {"LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
        "resource_limits": {"wall_timeout_seconds": timeout, "core_dump_bytes": 0},
        "executable_sha256": sha256(executable) if executable.is_file() else None,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout": artifact(stdout_path),
        "stderr": artifact(stderr_path),
    }
    commands.append(record)
    return record


def load_properties() -> list[tuple[str, Path, dict[str, Any]]]:
    selected: list[tuple[str, Path, dict[str, Any]]] = []
    for system in ("ArduPilot", "PX4"):
        for path in sorted((BENCHMARK / system / "properties").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["mitl"]["status"] == "CONCRETE_UNVALIDATED":
                require(document["implementation_satisfaction"] == "NOT_ASSESSED", f"{path}: implementation status changed")
                selected.append((system, path, document))
    require(len(selected) == 8, f"expected 8 CONCRETE_UNVALIDATED properties, found {len(selected)}")
    return selected


def parser_status(record: dict[str, Any], stderr_path: Path) -> dict[str, Any]:
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    if record["exit_code"] == 0:
        status = "PASS"
    elif "parse failed" in stderr.lower() or "extraneous input" in stderr.lower() or "token recognition error" in stderr.lower():
        status = "UNSUPPORTED_SYNTAX"
    elif record["timed_out"]:
        status = "UNSUPPORTED_TIMEOUT"
    else:
        status = "FAILED"
    return {
        "status": status,
        "exit_code": record["exit_code"],
        "command_id": record["command_id"],
        "stdout": record["stdout"],
        "stderr": record["stderr"],
        "error_excerpt": stderr.strip()[:2000] or None,
    }


def classify_trace_execution(
    record: dict[str, Any], metadata: dict[str, Any], stderr_path: Path
) -> tuple[str, str, str | None]:
    """Classify unsupported runtime paths without converting them into verdicts."""

    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    excerpt = stderr.strip()[:4000] or None
    if record["exit_code"] == 0 and metadata:
        return "EXECUTED", "TAMonitor completed and emitted metadata.", excerpt
    if record["timed_out"]:
        return (
            "UNSUPPORTED_TAMONITOR_TIMEOUT",
            "TAMonitor exceeded the recorded command timeout; no monitor verdict is inferred.",
            excerpt,
        )
    if "Both are out" in stderr and "pos != OUT || neg != OUT" in stderr:
        return (
            "UNSUPPORTED_MONITAAL_POSITIVE_NEGATIVE_BOTH_OUT_ASSERTION",
            "The linked MoniTAal infinite-word runner aborted because both positive and negative automata were OUT.",
            excerpt,
        )
    if "BDD projection valuation limit exceeded" in stderr:
        return (
            "UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT",
            "TAMonitor rejected the trace because its BDD projection valuation limit was exceeded.",
            excerpt,
        )
    if record["exit_code"] == 0:
        return (
            "FAILED_TAMONITOR_MISSING_METADATA",
            "TAMonitor returned success without the required metadata artifact.",
            excerpt,
        )
    return (
        "FAILED_TAMONITOR_EXECUTION",
        "TAMonitor exited unsuccessfully through an unclassified runtime path.",
        excerpt,
    )


def monitor_comparison(expected_verdict: str, status: str, verdict: str | None) -> str:
    if status != "EXECUTED":
        return status
    if verdict == expected_verdict:
        return "PASS"
    if verdict == "INCONCLUSIVE":
        return "INCONCLUSIVE_TAMONITOR_PREFIX"
    return "FAILED_VERDICT_MISMATCH"


def audit_tools(commands: list[dict[str, Any]]) -> dict[str, Any]:
    audit_dir = OUTPUT / "tool_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    status_specs = (
        ("mighty_status_before", ROOT / "tool" / "MightyPPL", ["git", "status", "--short", "--", "."]),
        ("monitaal_status_before", ROOT / "tool" / "MoniTAal", ["git", "status", "--short", "--", "."]),
    )
    status_records: dict[str, Any] = {}
    for command_id, cwd, argv in status_specs:
        record = run_command(
            commands,
            command_id,
            "Preserve pre-run source status",
            argv,
            audit_dir / f"{command_id}.stdout.txt",
            audit_dir / f"{command_id}.stderr.txt",
            cwd=cwd,
        )
        require(record["exit_code"] == 0, f"{command_id} failed")
        status_records[command_id] = record

    tamonitor_tree_before_path = audit_dir / "tamonitor_tree_before.json"
    write_json(
        tamonitor_tree_before_path,
        {
            "root": relative(ROOT / "src" / "TAMonitor"),
            "files": tree_hash_manifest(ROOT / "src" / "TAMonitor"),
        },
    )

    help_specs = (
        ("tamonitor_help", TAMONITOR),
        ("mitppl_help", MITPPL),
        ("monitaal_help", MONITAAL_BIN),
    )
    help_records: dict[str, Any] = {}
    for command_id, executable in help_specs:
        require(executable.is_file(), f"missing executable {executable}")
        record = run_command(
            commands,
            command_id,
            "Capture the actual executable interface",
            [str(executable), "--help"],
            audit_dir / f"{command_id}.stdout.txt",
            audit_dir / f"{command_id}.stderr.txt",
        )
        help_records[command_id] = record

    ldd_record = run_command(
        commands,
        "tamonitor_ldd",
        "Capture runtime shared-library dependencies",
        ["ldd", str(TAMONITOR)],
        audit_dir / "tamonitor_ldd.stdout.txt",
        audit_dir / "tamonitor_ldd.stderr.txt",
    )
    require(ldd_record["exit_code"] == 0, "ldd TAMonitor failed")

    monitaal_model = ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b30.xml"
    monitaal_smoke_input = audit_dir / "monitaal_smoke.trace"
    write_text(monitaal_smoke_input, "@0 a @20 b @25 a @56 b\n")
    monitaal_smoke_record = run_command(
        commands,
        "monitaal_automata_smoke",
        "Run standalone MoniTAal with an existing positive/negative UPPAAL automata pair",
        [
            str(MONITAAL_BIN),
            "-p",
            "a_leadsto_b",
            str(monitaal_model),
            "-n",
            "not_a_leadsto_b",
            str(monitaal_model),
            "-i",
            str(monitaal_smoke_input),
        ],
        audit_dir / "monitaal_automata_smoke.stdout.txt",
        audit_dir / "monitaal_automata_smoke.stderr.txt",
    )
    monitaal_smoke_stdout = (audit_dir / "monitaal_automata_smoke.stdout.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    require(
        monitaal_smoke_record["exit_code"] == 0 and "verdict is: NEGATIVE" in monitaal_smoke_stdout,
        "standalone MoniTAal automata smoke failed",
    )

    probe_property = json.loads(
        (BENCHMARK / "ArduPilot" / "properties" / "ARD-COPTER-GCS-001.json").read_text(encoding="utf-8")
    )
    monitaal_formula_probe = audit_dir / "monitaal_formula_input_probe.mitl"
    monitaal_empty_input = audit_dir / "monitaal_empty.trace"
    write_text(monitaal_formula_probe, probe_property["mitl"]["concrete"] + "\n")
    write_text(monitaal_empty_input, "")
    monitaal_formula_probe_record = run_command(
        commands,
        "monitaal_formula_input_probe",
        "Confirm that standalone MoniTAal treats formula text as an invalid XML automaton, not as MITL",
        [
            str(MONITAAL_BIN),
            "-p",
            "property",
            str(monitaal_formula_probe),
            "-n",
            "negated_property",
            str(monitaal_formula_probe),
            "-i",
            str(monitaal_empty_input),
        ],
        audit_dir / "monitaal_formula_input_probe.stdout.txt",
        audit_dir / "monitaal_formula_input_probe.stderr.txt",
    )
    monitaal_formula_probe_stderr = (audit_dir / "monitaal_formula_input_probe.stderr.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    require(
        monitaal_formula_probe_record["exit_code"] != 0
        and "Failed to load model file" in monitaal_formula_probe_stderr,
        "standalone MoniTAal unexpectedly accepted MITL formula input",
    )

    source_artifacts = [artifact(path) for path in TOOL_SOURCE_PATHS if path.is_file()]
    return {
        "TAMonitor": {
            "status": "AVAILABLE",
            "executable": artifact(TAMONITOR),
            "help_command_id": help_records["tamonitor_help"]["command_id"],
            "runtime_contract": {
                "formula_input": "MightyPPL MITL text",
                "trace_input": "monotonic absolute global integer time or closed time interval plus full AP valuation",
                "trace_time_evidence": [
                    "src/TAMonitor/TraceParser.cpp parses each time token directly into TimedEvent.time",
                    "src/TAMonitor/MonitorRunner.cpp passes event.time to monitaal::timed_input_t",
                    "tool/MoniTAal/src/monitaal/state.cpp constrains symbolic global time to the supplied value and computes concrete delay as supplied value minus current global time",
                ],
                "required_build_mode": "flatten",
                "word_mode_used": "infinite",
                "verdicts": ["POSITIVE", "NEGATIVE", "INCONCLUSIVE"],
            },
        },
        "MightyPPL": {
            "status": "AVAILABLE",
            "executable": artifact(MITPPL),
            "grammar": artifact(ROOT / "tool" / "MightyPPL" / "Mitl.g4"),
            "help_command_id": help_records["mitppl_help"]["command_id"],
        },
        "MoniTAal": {
            "status": "AVAILABLE_REQUIRES_PREBUILT_POSITIVE_AND_NEGATIVE_AUTOMATA",
            "standalone_executable": artifact(MONITAAL_BIN),
            "embedded_static_library": artifact(MONITAAL_LIBRARY),
            "help_command_id": help_records["monitaal_help"]["command_id"],
            "used_directly_for_property_runs": False,
            "reason": "The standalone CLI accepts positive/negative UPPAAL XML automata, not an MITL formula. TAMonitor is the existing MightyPPL-to-MoniTAal integration used here.",
            "automata_smoke": {
                "status": "PASS",
                "command_id": monitaal_smoke_record["command_id"],
                "input": artifact(monitaal_smoke_input),
                "model": artifact(monitaal_model),
                "observed_verdict": "NEGATIVE",
            },
            "formula_input_probe": {
                "status": "UNSUPPORTED_XML_AUTOMATA_REQUIRED",
                "command_id": monitaal_formula_probe_record["command_id"],
                "exit_code": monitaal_formula_probe_record["exit_code"],
                "input": artifact(monitaal_formula_probe),
                "stdout": monitaal_formula_probe_record["stdout"],
                "stderr": monitaal_formula_probe_record["stderr"],
                "error_excerpt": monitaal_formula_probe_stderr.strip()[:2000],
            },
            "link_evidence": artifact(ROOT / "tool" / "MightyPPL" / "build" / "CMakeFiles" / "TAMonitor.dir" / "link.txt"),
        },
        "source_evidence": source_artifacts,
        "pre_run_status_command_ids": sorted(status_records),
        "tamonitor_tree_before": artifact(tamonitor_tree_before_path),
        "ldd_command_id": ldd_record["command_id"],
    }


def assert_status_unchanged(commands: list[dict[str, Any]], tool_inventory: dict[str, Any]) -> None:
    audit_dir = OUTPUT / "tool_audit"
    pairs = (
        ("mighty_status", ROOT / "tool" / "MightyPPL", ["git", "status", "--short", "--", "."]),
        ("monitaal_status", ROOT / "tool" / "MoniTAal", ["git", "status", "--short", "--", "."]),
    )
    results: dict[str, Any] = {}
    by_id = {record["command_id"]: record for record in commands}
    for prefix, cwd, argv in pairs:
        after = run_command(
            commands,
            f"{prefix}_after",
            "Confirm source status is unchanged after monitor runs",
            argv,
            audit_dir / f"{prefix}_after.stdout.txt",
            audit_dir / f"{prefix}_after.stderr.txt",
            cwd=cwd,
        )
        before = by_id[f"{prefix}_before"]
        before_text = (ROOT / before["stdout"]["path"]).read_text(encoding="utf-8")
        after_text = (ROOT / after["stdout"]["path"]).read_text(encoding="utf-8")
        require(after["exit_code"] == 0 and before_text == after_text, f"{prefix} status changed during monitor validation")
        results[prefix] = {
            "status": "UNCHANGED",
            "before_command_id": before["command_id"],
            "after_command_id": after["command_id"],
            "snapshot_sha256": before["stdout"]["sha256"],
        }
    before_path = ROOT / tool_inventory["tamonitor_tree_before"]["path"]
    before_tree = json.loads(before_path.read_text(encoding="utf-8"))
    after_tree = {
        "root": relative(ROOT / "src" / "TAMonitor"),
        "files": tree_hash_manifest(ROOT / "src" / "TAMonitor"),
    }
    after_path = audit_dir / "tamonitor_tree_after.json"
    write_json(after_path, after_tree)
    require(after_tree == before_tree, "src/TAMonitor file hashes changed during monitor validation")
    results["tamonitor_tree"] = {
        "status": "UNCHANGED",
        "before": artifact(before_path),
        "after": artifact(after_path),
        "file_count": len(after_tree["files"]),
    }
    tool_inventory["source_status_preservation"] = results


def build_property(
    system: str,
    live_source_path: Path,
    source_snapshot_path: Path,
    document: dict[str, Any],
    commands: list[dict[str, Any]],
    trace_validator: Draft7Validator,
) -> dict[str, Any]:
    property_id = document["property_id"]
    property_dir = OUTPUT / "properties" / property_id
    property_dir.mkdir(parents=True, exist_ok=True)
    source_formula = document["mitl"]["concrete"]
    instances = document["mitl"]["concrete_instances"]
    require(instances and all(instance["formula"] == source_formula for instance in instances), f"{property_id}: inconsistent concrete formulas")
    require(all(instance["formula_time_unit"] == "s" for instance in instances), f"{property_id}: expected seconds")
    values = {Decimal(str(instance["normalized_value"])) for instance in instances}
    require(len(values) == 1, f"{property_id}: profile bounds differ")
    threshold_seconds = values.pop()
    threshold_ticks_decimal = threshold_seconds * TICKS_PER_SECOND
    require(threshold_ticks_decimal == threshold_ticks_decimal.to_integral_value(), f"{property_id}: non-integral ms threshold")
    threshold_ticks = int(threshold_ticks_decimal)

    ap_order = [item["name"] for item in document["atomic_propositions"]]
    trigger = ap_order[0]
    response = ap_order[-1]
    guards = ap_order[1:-1]
    clock_domains = {item["clock_domain"] for item in document["time_contracts"]}
    require(len(clock_domains) == 1, f"{property_id}: multiple property clocks")
    clock_domain = clock_domains.pop()

    monitor_formula, conversions = source_to_monitor_formula(source_formula)
    ast = FormulaParser(monitor_formula).parse()
    require(ast.names() == set(ap_order), f"{property_id}: formula/AP identity mismatch")
    finite_nonzero_bounds = {
        item["monitor_ticks"]
        for item in conversions
        if item["source_seconds"] != "0"
    }
    require(finite_nonzero_bounds == {threshold_ticks}, f"{property_id}: formula bound differs from runtime value")

    source_formula_path = property_dir / "source_formula.mitl"
    monitor_formula_path = property_dir / "monitor_formula_ms.mitl"
    ast_path = property_dir / "formula_ast.json"
    write_text(source_formula_path, source_formula + "\n")
    write_text(monitor_formula_path, monitor_formula + "\n")
    write_json(
        ast_path,
        {
            "oracle_identity": ORACLE_ID,
            "semantics": "pointwise finite timed word; intervals use their recorded open/closed endpoints; the word is complete",
            "time_unit": TICK_UNIT,
            "ast": ast.as_json(),
        },
    )

    parser_dir = property_dir / "parser"
    source_parser_record = run_command(
        commands,
        f"{property_id}:source-parser",
        "Probe the source formula verbatim; do not silently normalize parser failures",
        [
            str(TAMONITOR),
            "--formula",
            str(source_formula_path),
            "--build-mode",
            "flatten",
            "--word",
            "infinite",
            "--state",
            "symbolic",
            "--out",
            str(parser_dir / "source-build"),
            "--build-only",
        ],
        parser_dir / "source_parser.stdout.txt",
        parser_dir / "source_parser.stderr.txt",
    )
    source_parser = parser_status(source_parser_record, parser_dir / "source_parser.stderr.txt")

    monitor_parser_record = run_command(
        commands,
        f"{property_id}:monitor-parser",
        "Build the exact integer-millisecond monitor encoding",
        [
            str(TAMONITOR),
            "--formula",
            str(monitor_formula_path),
            "--build-mode",
            "flatten",
            "--word",
            "infinite",
            "--state",
            "symbolic",
            "--out",
            str(parser_dir / "monitor-build"),
            "--build-only",
        ],
        parser_dir / "monitor_parser.stdout.txt",
        parser_dir / "monitor_parser.stderr.txt",
    )
    monitor_parser = parser_status(monitor_parser_record, parser_dir / "monitor_parser.stderr.txt")

    mitppl_record = run_command(
        commands,
        f"{property_id}:mitppl-sat",
        "Run MightyPPL infinite-word satisfiability on the adapted formula",
        [str(MITPPL), str(monitor_formula_path), "--inf"],
        parser_dir / "mitppl_sat.stdout.txt",
        parser_dir / "mitppl_sat.stderr.txt",
        timeout=120,
    )
    mitppl_stdout = (parser_dir / "mitppl_sat.stdout.txt").read_text(encoding="utf-8", errors="replace")
    mitppl_sat = "SATISFIABLE" if "SATISFIABLE" in mitppl_stdout and "UNSATISFIABLE" not in mitppl_stdout else "UNKNOWN"

    build_metadata_path = parser_dir / "monitor-build" / "metadata.json"
    build_metadata = json.loads(build_metadata_path.read_text(encoding="utf-8")) if build_metadata_path.is_file() else {}
    monitor_build = {
        "status": "PASS" if monitor_parser["status"] == "PASS" else "UNSUPPORTED",
        "word_mode": "infinite",
        "formula_satisfiable": build_metadata.get("formula_satisfiable"),
        "negative_formula_satisfiable": build_metadata.get("negative_formula_satisfiable"),
        "metadata": artifact(build_metadata_path) if build_metadata_path.is_file() else None,
        "mitppl_command_id": mitppl_record["command_id"],
        "mitppl_exit_code": mitppl_record["exit_code"],
        "mitppl_satisfiability": mitppl_sat,
        "mitppl_stdout": mitppl_record["stdout"],
        "mitppl_stderr": mitppl_record["stderr"],
    }

    lower_closed = "F_[" in source_formula
    require(lower_closed or "F_(" in source_formula, f"{property_id}: unknown eventual lower endpoint")
    trace_results: list[dict[str, Any]] = []
    trace_docs: dict[str, dict[str, Any]] = {}
    for spec in case_specs(lower_closed, threshold_ticks):
        case_kind = spec["case_kind"]
        trace_id = f"{property_id}--{case_kind}"
        rows = make_rows(
            ap_order,
            trigger,
            response,
            guards,
            threshold_ticks,
            spec["response_delta"],
            trigger_enabled=spec.get("trigger_enabled", True),
        )
        trace = trace_document(
            property_id,
            trace_id,
            clock_domain,
            ap_order,
            rows,
            f"{spec['reason']} {NO_EPSILON_POLICY}",
        )
        trace_errors = sorted(trace_validator.iter_errors(trace), key=lambda error: list(error.path))
        require(not trace_errors, f"{trace_id}: timed-trace schema failure: {trace_errors[0].message if trace_errors else ''}")
        oracle_value = oracle_eval(ast, trace["events"], 0)
        require(oracle_value == spec["expected"], f"{trace_id}: constructed trace does not match expected oracle verdict")

        trace_dir = property_dir / "traces" / case_kind
        trace_json_path = trace_dir / "trace.json"
        monitor_trace_path = trace_dir / "monitor_trace.csv"
        write_json(trace_json_path, trace)
        csv_lines = ["time,props"]
        for event in trace["events"]:
            csv_lines.append(f"{event['time']},{true_names(event['values'], ap_order)}")
        write_text(monitor_trace_path, "\n".join(csv_lines) + "\n")

        run_dir = trace_dir / "tamonitor"
        command_record = run_command(
            commands,
            f"{property_id}:trace:{case_kind}",
            f"Run real TAMonitor on synthetic case {case_kind}",
            [
                str(TAMONITOR),
                "--formula",
                str(monitor_formula_path),
                "--trace",
                str(monitor_trace_path),
                "--build-mode",
                "flatten",
                "--word",
                "infinite",
                "--state",
                "symbolic",
                "--out",
                str(run_dir),
                "--print-steps",
            ],
            trace_dir / "tamonitor.stdout.txt",
            trace_dir / "tamonitor.stderr.txt",
        )
        metadata_path = run_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
        steps_path = run_dir / "steps.csv"
        terminal_step: dict[str, Any] | None = None
        if steps_path.is_file():
            with steps_path.open(encoding="utf-8", newline="") as stream:
                step_rows = list(csv.DictReader(stream))
            if step_rows:
                last = step_rows[-1]
                terminal_step = {
                    "step": int(last["step"]),
                    "absolute_time_ticks": int(last["time"]),
                    "verdict": last["verdict"],
                    "positive_states": int(last["positive_states"]),
                    "negative_states": int(last["negative_states"]),
                    "monitor_advanced": last["monitor_advanced"] == "true",
                }
        execution_status, execution_reason, error_excerpt = classify_trace_execution(
            command_record, metadata, trace_dir / "tamonitor.stderr.txt"
        )
        final_verdict = metadata.get("final_verdict")
        expected_prefix_verdict = (
            "NEGATIVE"
            if case_kind in {"too_early_one_tick", "boundary_exact_excluded"}
            else "INCONCLUSIVE"
        )
        prefix_reason = (
            "The prefix contains an irreversible pre-threshold/open-boundary safety violation."
            if expected_prefix_verdict == "NEGATIVE"
            else "An outer unbounded G property cannot be proved positive from this finite prefix; a missing response can still occur in an extension."
        )
        comparison = monitor_comparison(expected_prefix_verdict, execution_status, final_verdict)
        if comparison == "PASS":
            classification_reason = "TAMonitor produced the expected infinite-extension prefix verdict."
        elif comparison == "INCONCLUSIVE_TAMONITOR_PREFIX":
            classification_reason = "TAMonitor retained a three-valued INCONCLUSIVE result; the independent oracle verdict is not substituted for it."
        elif comparison.startswith("UNSUPPORTED") or comparison.startswith("FAILED_TAMONITOR"):
            classification_reason = execution_reason
        else:
            classification_reason = "TAMonitor produced a verdict different from the expected infinite-extension prefix verdict."
        result = {
            "trace_id": trace_id,
            "case_kind": case_kind,
            "boundary_region": spec["boundary_region"],
            "clock": {
                "domain": clock_domain,
                "epoch": trace["epoch"],
                "tick_unit": TICK_UNIT,
                "trigger_time_ticks": TRIGGER_TIME_TICKS,
                "threshold_ticks": threshold_ticks,
                "response_delta_ticks": spec["response_delta"],
                "horizon_ticks": trace["events"][-1]["time"],
            },
            "expected": {
                "reference_oracle_complete_word_verdict": "POSITIVE" if spec["expected"] else "NEGATIVE",
                "reference_oracle_reason": spec["reason"],
                "tamonitor_infinite_prefix_verdict": expected_prefix_verdict,
                "tamonitor_prefix_reason": prefix_reason,
                "no_epsilon_policy": NO_EPSILON_POLICY,
            },
            "oracle": {
                "identity": ORACLE_ID,
                "verdict": "POSITIVE" if oracle_value else "NEGATIVE",
                "trigger_count": sum(event["values"][trigger] for event in trace["events"]),
                "response_count": sum(event["values"][response] for event in trace["events"]),
                "completed_finite_word": True,
            },
            "trace": artifact(trace_json_path),
            "monitor_trace": artifact(monitor_trace_path),
            "monitor_trace_time_encoding": {
                "kind": "ABSOLUTE_GLOBAL_CLOCK_TICKS",
                "unit": TICK_UNIT,
                "source_trace_kind": "ABSOLUTE_SYNTHETIC_CLOCK_TICKS",
                "conversion": "identity; each monitor time equals the corresponding JSON event absolute time",
            },
            "tamonitor": {
                "status": execution_status,
                "verdict": final_verdict,
                "exit_code": command_record["exit_code"],
                "termination_signal": -command_record["exit_code"] if command_record["exit_code"] < 0 else None,
                "timed_out": command_record["timed_out"],
                "runtime_classification_reason": execution_reason,
                "error_excerpt": error_excerpt,
                "command_id": command_record["command_id"],
                "stdout": command_record["stdout"],
                "stderr": command_record["stderr"],
                "metadata": artifact(metadata_path) if metadata_path.is_file() else None,
                "steps": artifact(steps_path) if steps_path.is_file() else None,
                "terminal_step": terminal_step,
            },
            "comparison_status": comparison,
            "comparison_kind": (
                "EXPECTED_INCONCLUSIVE_MATCH"
                if comparison == "PASS" and expected_prefix_verdict == "INCONCLUSIVE"
                else "EXPECTED_DECISIVE_MATCH"
                if comparison == "PASS"
                else comparison
            ),
            "classification_reason": classification_reason,
        }
        result_path = trace_dir / "result.json"
        write_json(result_path, result)
        result["result"] = artifact(result_path)
        trace_results.append(result)
        trace_docs[case_kind] = trace

    by_case = {item["case_kind"]: item for item in trace_results}
    runtime_diagnostics: dict[str, Any] | None = None
    if property_id == "ARD-COPTER-RTL-003":
        diagnostic_dir = property_dir / "diagnostics" / "runtime_limits"
        representative_kind = "too_early_one_tick"
        representative_trace_path = property_dir / "traces" / representative_kind / "monitor_trace.csv"
        diagnostic_attempts: list[dict[str, Any]] = []
        attempt_specs = (
            {
                "id": "symbolic_max_valuations_65536",
                "state": "symbolic",
                "max_valuations": 65536,
                "purpose": "Bounded diagnostic retry with an explicitly raised BDD projection valuation cap.",
            },
            {
                "id": "concrete_default_max_valuations",
                "state": "concrete",
                "max_valuations": None,
                "purpose": "Bounded diagnostic retry using concrete monitor state and the TAMonitor default valuation cap.",
            },
        )
        for attempt_spec in attempt_specs:
            attempt_id = attempt_spec["id"]
            attempt_dir = diagnostic_dir / attempt_id
            argv = [
                str(TAMONITOR),
                "--formula",
                str(monitor_formula_path),
                "--trace",
                str(representative_trace_path),
                "--build-mode",
                "flatten",
                "--word",
                "infinite",
                "--state",
                attempt_spec["state"],
            ]
            if attempt_spec["max_valuations"] is not None:
                argv.extend(["--max-valuations", str(attempt_spec["max_valuations"])])
            argv.extend(["--out", str(attempt_dir / "tamonitor"), "--print-steps"])
            attempt_record = run_command(
                commands,
                f"{property_id}:diagnostic:{attempt_id}",
                attempt_spec["purpose"],
                argv,
                attempt_dir / "tamonitor.stdout.txt",
                attempt_dir / "tamonitor.stderr.txt",
                timeout=60,
            )
            attempt_metadata_path = attempt_dir / "tamonitor" / "metadata.json"
            attempt_metadata = (
                json.loads(attempt_metadata_path.read_text(encoding="utf-8"))
                if attempt_metadata_path.is_file()
                else {}
            )
            attempt_status, attempt_reason, attempt_error = classify_trace_execution(
                attempt_record, attempt_metadata, attempt_dir / "tamonitor.stderr.txt"
            )
            diagnostic_expected_verdict = "NEGATIVE"
            diagnostic_verdict = attempt_metadata.get("final_verdict")
            diagnostic_comparison = monitor_comparison(
                diagnostic_expected_verdict, attempt_status, diagnostic_verdict
            )
            diagnostic_attempts.append(
                {
                    "attempt_id": attempt_id,
                    "purpose": attempt_spec["purpose"],
                    "state": attempt_spec["state"],
                    "word_mode": "infinite",
                    "max_valuations": attempt_spec["max_valuations"],
                    "uses_tamonitor_default_max_valuations": attempt_spec["max_valuations"] is None,
                    "wall_timeout_seconds": 60,
                    "core_dump_bytes": 0,
                    "status": attempt_status,
                    "classification_reason": attempt_reason,
                    "exit_code": attempt_record["exit_code"],
                    "termination_signal": -attempt_record["exit_code"] if attempt_record["exit_code"] < 0 else None,
                    "timed_out": attempt_record["timed_out"],
                    "expected_infinite_prefix_verdict": diagnostic_expected_verdict,
                    "verdict": diagnostic_verdict,
                    "comparison_status": diagnostic_comparison,
                    "error_excerpt": attempt_error,
                    "command_id": attempt_record["command_id"],
                    "stdout": attempt_record["stdout"],
                    "stderr": attempt_record["stderr"],
                    "metadata": artifact(attempt_metadata_path) if attempt_metadata_path.is_file() else None,
                }
            )
        diagnostic_document = {
            "property_id": property_id,
            "role": "BOUNDED_DIAGNOSTIC_ATTEMPTS_NOT_PRIMARY_VALIDATION",
            "primary_configuration_changed": False,
            "influences_primary_trace_comparisons": False,
            "representative_trace_id": by_case[representative_kind]["trace_id"],
            "expected_infinite_prefix_verdict": "NEGATIVE",
            "formula": artifact(monitor_formula_path),
            "monitor_trace": artifact(representative_trace_path),
            "attempts": diagnostic_attempts,
            "conclusion": "; ".join(
                f"{item['attempt_id']}={item['status']}/{item['verdict'] or 'NO_VERDICT'}/{item['comparison_status']}"
                for item in diagnostic_attempts
            ),
        }
        diagnostic_document_path = diagnostic_dir / "diagnostic_attempts.json"
        write_json(diagnostic_document_path, diagnostic_document)
        runtime_diagnostics = {
            "status": "RECORDED_BOUNDED_RUNTIME_DIAGNOSTICS",
            "artifact": artifact(diagnostic_document_path),
            "attempt_status_counts": dict(
                sorted(Counter(item["status"] for item in diagnostic_attempts).items())
            ),
            "attempt_comparison_counts": dict(
                sorted(Counter(item["comparison_status"] for item in diagnostic_attempts).items())
            ),
            "conclusion": diagnostic_document["conclusion"],
            "primary_configuration_changed": False,
        }
    positive_case = by_case["positive_after_threshold"]
    early_case = by_case["too_early_one_tick"]
    vacuous_case = by_case["vacuous_trigger_control"]
    reference_oracle = {
        "identity": ORACLE_ID,
        "tool_role": "Independent deterministic formula/trace oracle; not TAMonitor and not firmware evidence.",
        "semantics": "Pointwise finite timed words, complete-word interpretation, exact interval endpoints.",
        "ast": artifact(ast_path),
        "satisfiable_witness": {
            "status": "PASS" if positive_case["oracle"]["verdict"] == "POSITIVE" else "FAIL",
            "trace_id": positive_case["trace_id"],
        },
        "non_tautology_counterexample": {
            "status": "PASS" if early_case["oracle"]["verdict"] == "NEGATIVE" else "FAIL",
            "trace_id": early_case["trace_id"],
        },
        "non_vacuity_pair": {
            "status": "PASS"
            if early_case["oracle"]["verdict"] == "NEGATIVE"
            and early_case["oracle"]["trigger_count"] == 1
            and vacuous_case["oracle"]["verdict"] == "POSITIVE"
            and vacuous_case["oracle"]["trigger_count"] == 0
            else "FAIL",
            "triggered_counterexample": early_case["trace_id"],
            "trigger_disabled_control": vacuous_case["trace_id"],
        },
    }
    reference_pass = all(
        reference_oracle[key]["status"] == "PASS"
        for key in ("satisfiable_witness", "non_tautology_counterexample", "non_vacuity_pair")
    )
    comparisons = Counter(item["comparison_status"] for item in trace_results)
    if monitor_parser["status"] != "PASS":
        overall_status = "UNSUPPORTED_MONITOR_FORMULA_BUILD"
    elif any(key.startswith("FAILED") for key in comparisons):
        overall_status = "FAILED"
    elif any(key.startswith("UNSUPPORTED") for key in comparisons):
        overall_status = "UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME"
    elif "INCONCLUSIVE_TAMONITOR_PREFIX" in comparisons:
        overall_status = "INCONCLUSIVE_TAMONITOR_PREFIX"
    elif not reference_pass:
        overall_status = "FAILED_REFERENCE_ORACLE"
    else:
        overall_status = "PASS"

    return {
        "system": system,
        "property_id": property_id,
        "source_property_path": relative(source_snapshot_path),
        "source_property": artifact(source_snapshot_path),
        "source_property_snapshot": artifact(source_snapshot_path),
        "live_property_path": relative(live_source_path),
        "live_property_at_capture": artifact(live_source_path),
        "source_property_status": document["status"],
        "source_formula_status": document["mitl"]["status"],
        "implementation_satisfaction": document["implementation_satisfaction"],
        "source_formula": source_formula,
        "source_formula_artifact": artifact(source_formula_path),
        "source_formula_time_unit": "s",
        "clock_domain": clock_domain,
        "concrete_instances": [
            {
                "capture_id": instance["capture_id"],
                "profile": instance["profile"],
                "normalized_value": instance["normalized_value"],
                "status": instance["status"],
                "source_path": instance["source_path"],
                "source_sha256": instance["source_sha256"],
            }
            for instance in instances
        ],
        "ap_order": ap_order,
        "trigger_ap": trigger,
        "guard_aps": guards,
        "response_ap": response,
        "monitor_encoding": {
            "formula": monitor_formula,
            "artifact": artifact(monitor_formula_path),
            "tick_unit": TICK_UNIT,
            "ticks_per_source_second": TICKS_PER_SECOND,
            "threshold_ticks": threshold_ticks,
            "exact_rescaling": True,
            "interval_openness_preserved": True,
            "syntax_changes": [
                "single '&' rendered as MightyPPL '&&'",
                "presentation underscore between modality and interval removed",
                "seconds bounds exactly multiplied by 1000",
                "negated temporal operands parenthesized as MightyPPL atoms",
            ],
            "bound_conversions": conversions,
            "no_epsilon_policy": NO_EPSILON_POLICY,
        },
        "parser": {
            "source_syntax_probe": source_parser,
            "monitor_syntax_probe": monitor_parser,
        },
        "monitor_build": monitor_build,
        "reference_oracle": reference_oracle,
        "runtime_diagnostics": runtime_diagnostics,
        "trace_comparison_counts": dict(sorted(comparisons.items())),
        "traces": trace_results,
        "overall_status": overall_status,
    }


def build_report(main: dict[str, Any]) -> str:
    counts = main["counts"]
    lines = [
        "# Milestone 7 monitor validation",
        "",
        "This directory contains synthetic formula/trace validation only. It does not contain or evaluate flight-controller traces, and it does not change `implementation_satisfaction=NOT_ASSESSED`.",
        "",
        "## Result",
        "",
        f"- Properties: {main['property_count']}",
        f"- Synthetic timed traces: {main['trace_count']}",
        f"- Property results: `{json.dumps(counts['property_status_counts'], sort_keys=True)}`",
        f"- Trace comparisons: `{json.dumps(counts['trace_comparison_counts'], sort_keys=True)}`",
        f"- TAMonitor execution statuses: `{json.dumps(counts['trace_execution_status_counts'], sort_keys=True)}`",
        f"- Source syntax probes: `{json.dumps(counts['source_parser_status_counts'], sort_keys=True)}`",
        f"- Adapted monitor syntax probes: `{json.dumps(counts['monitor_parser_status_counts'], sort_keys=True)}`",
        f"- MightyPPL infinite-word satisfiability: `{json.dumps(counts['mitppl_satisfiability_counts'], sort_keys=True)}`",
        f"- Normalized pass/inconclusive/unsupported/failure counts: `{json.dumps(main['outcome_counts'], sort_keys=True)}`",
        "",
        "## Tool identity and syntax boundary",
        "",
        f"- TAMonitor: `{main['tool_inventory']['TAMonitor']['executable']['sha256']}`",
        f"- MightyPPL `mitppl`: `{main['tool_inventory']['MightyPPL']['executable']['sha256']}`",
        f"- Standalone MoniTAal: `{main['tool_inventory']['MoniTAal']['standalone_executable']['sha256']}`",
        "- Original catalog formulas are probed verbatim and their parser errors are retained. The monitor encoding is an exact seconds-to-integer-milliseconds rescaling with interval openness preserved.",
        "- Standalone MoniTAal consumes positive and negative UPPAAL automata, not formulas. Property runs therefore use the existing TAMonitor integration, which builds MightyPPL automata and runs the linked MoniTAal monitor.",
        "",
        "## Boundary policy",
        "",
        NO_EPSILON_POLICY,
        "",
        "Each trace begins with an all-false sentinel at 0 ms and places the actual trigger at 1000 ms. This is required because MightyPPL documents strict temporal semantics; it prevents a time-zero trigger from being silently outside an outer strict `G` observation.",
        "",
        "The schema-valid JSON traces and TAMonitor CSV use the same monotonically increasing absolute synthetic global clock. MoniTAal's symbolic state constrains its global clock to each supplied value; its concrete state computes the elapsed amount by subtracting the current global-clock valuation.",
        "",
        "The lower-only response formulas have no finite upper deadline. Therefore `late_response_unbounded_legal` is positive in the complete-word reference oracle. A missing finite prefix remains extendable and is expected `INCONCLUSIVE` from the infinite-extension monitor.",
        "",
        "## Runtime blockers",
        "",
        "All eight adapted formulas build and are satisfiable. Synthetic property outcomes: "
        f"pass={main['outcome_counts']['property_monitor_runs']['passed']}; "
        f"runtime-unsupported={main['outcome_counts']['property_monitor_runs']['unsupported']}; "
        f"retained-comparison-failure={main['outcome_counts']['property_monitor_runs']['failed']}. "
        "These formula/trace results do not assess firmware implementation satisfaction.",
        "",
    ]
    for blocker in main["runtime_blockers"]:
        exact_error = (blocker["exact_error_excerpt"] or "no stderr").splitlines()[0]
        lines.append(
            f"- `{blocker['status']}`: {blocker['trace_count']} traces; representative "
            f"`{blocker['representative_trace_id']}` (exit `{blocker['representative_exit_code']}`): "
            f"`{exact_error}`"
        )
    lines.extend(["", "## Retained verdict mismatches", ""])
    for mismatch in main["verdict_mismatches"]:
        lines.append(
            f"- `{mismatch['trace_id']}`: expected infinite-prefix "
            f"`{mismatch['expected_infinite_prefix_verdict']}`, observed TAMonitor "
            f"`{mismatch['observed_tamonitor_verdict']}`; the result, stdout, and step log remain linked in the machine-readable record."
        )
    rtl = next(prop for prop in main["properties"] if prop["property_id"] == "ARD-COPTER-RTL-003")
    lines.extend(
        [
            "",
            "The RTL bounded diagnostics do not change the primary configuration or trace comparisons. "
            f"Their execution statuses are `{json.dumps(rtl['runtime_diagnostics']['attempt_status_counts'], sort_keys=True)}` "
            f"and comparison statuses are `{json.dumps(rtl['runtime_diagnostics']['attempt_comparison_counts'], sort_keys=True)}`: "
            f"`{rtl['runtime_diagnostics']['conclusion']}`.",
            "",
        "## Per-property evidence",
        "",
        "| Property | Source parser | Monitor parser | SAT | Reference oracle | TAMonitor trace comparisons | Overall |",
        "|---|---|---|---|---|---|---|",
        ]
    )
    for prop in main["properties"]:
        oracle_status = "/".join(
            prop["reference_oracle"][key]["status"]
            for key in ("satisfiable_witness", "non_tautology_counterexample", "non_vacuity_pair")
        )
        lines.append(
            f"| `{prop['property_id']}` | `{prop['parser']['source_syntax_probe']['status']}` | "
            f"`{prop['parser']['monitor_syntax_probe']['status']}` | `{prop['monitor_build']['mitppl_satisfiability']}` | "
            f"`{oracle_status}` | `{json.dumps(prop['trace_comparison_counts'], sort_keys=True)}` | `{prop['overall_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Honest unresolved semantics",
            "",
            "- The primary TAMonitor runs use infinite-word mode. For an outer unbounded `G`, successful and vacuous finite prefixes are expected to remain `INCONCLUSIVE`; only irreversible prefix violations are expected `NEGATIVE`.",
            "- Every raw TAMonitor `INCONCLUSIVE` verdict remains explicit in the per-trace result. When it equals the expected infinite-prefix verdict, the separate comparison status is `PASS`; otherwise the mismatch/diagnostic status remains explicit. The complete-word oracle never replaces the monitor verdict.",
            "- The reference oracle uses complete finite-word pointwise semantics. TAMonitor's three-valued result concerns its positive/negative automata state estimates; disagreements remain visible per trace.",
            "- Synthetic AP valuations test formula structure and endpoints only. They provide no evidence that firmware AP instrumentation, timestamps, correlation, or runtime behavior satisfies a property.",
            "- No implementation-satisfaction field in the source property catalogs is modified.",
            "",
            "## Reproduction",
            "",
            "```console",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --force",
            "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def generate(force: bool) -> int:
    # Resolve and validate the Stage-6 inputs before replacing any prior output.
    # This makes a mistaken --force invocation fail closed instead of deleting
    # the last complete evidence directory.
    loaded_properties = load_properties()
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        if not force:
            raise RuntimeError(f"{relative(OUTPUT)} is nonempty; pass --force to replace only this generated directory")
        require(OUTPUT.resolve().parent == (BENCHMARK / "extraction_runs" / "milestone7").resolve(), "unsafe output path")
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    trace_schema = json.loads(TRACE_SCHEMA.read_text(encoding="utf-8"))
    trace_validator = Draft7Validator(trace_schema)
    commands: list[dict[str, Any]] = []
    tool_inventory = audit_tools(commands)
    captured_properties: list[tuple[str, Path, Path, dict[str, Any]]] = []
    for system, live_path, document in loaded_properties:
        snapshot_path = OUTPUT / "inputs" / "properties" / system / live_path.name
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(live_path.read_bytes())
        require(
            sha256(snapshot_path) == sha256(live_path),
            f"failed to capture immutable property snapshot {live_path}",
        )
        captured_properties.append((system, live_path, snapshot_path, document))
    properties = [
        build_property(system, live_path, snapshot_path, document, commands, trace_validator)
        for system, live_path, snapshot_path, document in captured_properties
    ]
    assert_status_unchanged(commands, tool_inventory)

    property_status_counts = Counter(item["overall_status"] for item in properties)
    trace_comparison_counts = Counter(
        trace["comparison_status"] for item in properties for trace in item["traces"]
    )
    trace_execution_status_counts = Counter(
        trace["tamonitor"]["status"] for item in properties for trace in item["traces"]
    )
    source_parser_counts = Counter(item["parser"]["source_syntax_probe"]["status"] for item in properties)
    monitor_parser_counts = Counter(item["parser"]["monitor_syntax_probe"]["status"] for item in properties)
    sat_counts = Counter(item["monitor_build"]["mitppl_satisfiability"] for item in properties)
    outcome_counts = {
        "source_formula_parser": {
            "passed": source_parser_counts.get("PASS", 0),
            "unsupported": source_parser_counts.get("UNSUPPORTED_SYNTAX", 0)
            + source_parser_counts.get("UNSUPPORTED_TIMEOUT", 0),
            "failed": source_parser_counts.get("FAILED", 0),
        },
        "monitor_formula_parser": {
            "passed": monitor_parser_counts.get("PASS", 0),
            "unsupported": sum(value for key, value in monitor_parser_counts.items() if key.startswith("UNSUPPORTED")),
            "failed": monitor_parser_counts.get("FAILED", 0),
        },
        "property_monitor_runs": {
            "passed": property_status_counts.get("PASS", 0),
            "inconclusive": property_status_counts.get("INCONCLUSIVE_TAMONITOR_PREFIX", 0),
            "unsupported": sum(
                value for key, value in property_status_counts.items() if key.startswith("UNSUPPORTED")
            ),
            "failed": sum(value for key, value in property_status_counts.items() if key.startswith("FAILED")),
        },
        "trace_comparisons": {
            "passed": trace_comparison_counts.get("PASS", 0),
            "inconclusive": trace_comparison_counts.get("INCONCLUSIVE_TAMONITOR_PREFIX", 0),
            "unsupported": sum(
                value for key, value in trace_comparison_counts.items() if key.startswith("UNSUPPORTED")
            ),
            "failed": sum(value for key, value in trace_comparison_counts.items() if key.startswith("FAILED")),
        },
        "trace_executions": {
            "executed": trace_execution_status_counts.get("EXECUTED", 0),
            "unsupported": sum(
                value for key, value in trace_execution_status_counts.items() if key.startswith("UNSUPPORTED")
            ),
            "failed": sum(
                value for key, value in trace_execution_status_counts.items() if key.startswith("FAILED")
            ),
        },
        "reference_oracle_properties": {
            "passed": sum(
                all(
                    item["reference_oracle"][key]["status"] == "PASS"
                    for key in ("satisfiable_witness", "non_tautology_counterexample", "non_vacuity_pair")
                )
                for item in properties
            ),
            "failed": sum(
                not all(
                    item["reference_oracle"][key]["status"] == "PASS"
                    for key in ("satisfiable_witness", "non_tautology_counterexample", "non_vacuity_pair")
                )
                for item in properties
            ),
        },
    }

    runtime_blockers: list[dict[str, Any]] = []
    for status, count in sorted(trace_execution_status_counts.items()):
        if not status.startswith("UNSUPPORTED"):
            continue
        representative = next(
            trace
            for item in properties
            for trace in item["traces"]
            if trace["tamonitor"]["status"] == status
        )
        runtime_blockers.append(
            {
                "status": status,
                "trace_count": count,
                "representative_trace_id": representative["trace_id"],
                "representative_exit_code": representative["tamonitor"]["exit_code"],
                "representative_termination_signal": representative["tamonitor"]["termination_signal"],
                "exact_error_excerpt": representative["tamonitor"]["error_excerpt"],
                "stderr": representative["tamonitor"]["stderr"],
                "effect": "No TAMonitor verdict is inferred for these executions.",
            }
        )
    verdict_mismatches = [
        {
            "trace_id": trace["trace_id"],
            "property_id": item["property_id"],
            "case_kind": trace["case_kind"],
            "expected_infinite_prefix_verdict": trace["expected"]["tamonitor_infinite_prefix_verdict"],
            "observed_tamonitor_verdict": trace["tamonitor"]["verdict"],
            "comparison_status": trace["comparison_status"],
            "result": trace["result"],
            "stdout": trace["tamonitor"]["stdout"],
            "steps": trace["tamonitor"]["steps"],
        }
        for item in properties
        for trace in item["traces"]
        if trace["comparison_status"] == "FAILED_VERDICT_MISMATCH"
    ]

    main = {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "milestone": 7,
            "kind": "SYNTHETIC_FORMULA_AND_TIMED_TRACE_VALIDATION",
            "firmware_trace_evaluation_performed": False,
            "implementation_satisfaction_assessed": False,
            "source_property_files_modified": False,
        },
        "generated_by": {
            "identity": GENERATOR_ID,
            "path": relative(Path(__file__)),
            "sha256": sha256(Path(__file__)),
        },
        "boundary_policy": {
            "tick_unit": TICK_UNIT,
            "ticks_per_source_second": TICKS_PER_SECOND,
            "trigger_time_ticks": TRIGGER_TIME_TICKS,
            "no_epsilon_policy": NO_EPSILON_POLICY,
            "strict_semantics_sentinel": "All traces start with an all-false valuation at 0 ms; the trigger is at 1000 ms.",
            "monitor_trace_transport": "Identity mapping: TAMonitor receives the same monotonically increasing absolute global ticks recorded in each JSON trace.",
        },
        "tool_inventory": tool_inventory,
        "property_count": len(properties),
        "trace_count": sum(len(item["traces"]) for item in properties),
        "counts": {
            "property_status_counts": dict(sorted(property_status_counts.items())),
            "trace_comparison_counts": dict(sorted(trace_comparison_counts.items())),
            "trace_execution_status_counts": dict(sorted(trace_execution_status_counts.items())),
            "source_parser_status_counts": dict(sorted(source_parser_counts.items())),
            "monitor_parser_status_counts": dict(sorted(monitor_parser_counts.items())),
            "mitppl_satisfiability_counts": dict(sorted(sat_counts.items())),
            "command_count": len(commands),
        },
        "outcome_counts": outcome_counts,
        "runtime_blockers": runtime_blockers,
        "verdict_mismatches": verdict_mismatches,
        "properties": properties,
        "artifacts": {
            "commands": relative(COMMANDS_OUTPUT),
            "manifest": relative(MANIFEST_OUTPUT),
            "report": relative(REPORT_OUTPUT),
            "timed_trace_schema": artifact(TRACE_SCHEMA),
        },
    }

    write_text(COMMANDS_OUTPUT, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in commands))
    write_json(MAIN_OUTPUT, main)
    write_text(REPORT_OUTPUT, build_report(main))

    system_summaries: list[Path] = []
    for system in ("ArduPilot", "PX4"):
        path = BENCHMARK / system / "validation" / "monitor_validation.json"
        summary_properties = [item for item in properties if item["system"] == system]
        write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "system": system,
                "scope": "SYNTHETIC_FORMULA_AND_TRACE_VALIDATION_NOT_FIRMWARE_CONFORMANCE",
                "main_result_path": relative(MAIN_OUTPUT),
                "source_properties_modified": False,
                "implementation_satisfaction": "NOT_ASSESSED",
                "property_count": len(summary_properties),
                "trace_count": sum(len(item["traces"]) for item in summary_properties),
                "properties": [
                    {
                        "property_id": item["property_id"],
                        "source_formula_status": item["source_formula_status"],
                        "implementation_satisfaction": item["implementation_satisfaction"],
                        "source_parser_status": item["parser"]["source_syntax_probe"]["status"],
                        "monitor_parser_status": item["parser"]["monitor_syntax_probe"]["status"],
                        "mitppl_satisfiability": item["monitor_build"]["mitppl_satisfiability"],
                        "trace_comparison_counts": item["trace_comparison_counts"],
                        "overall_status": item["overall_status"],
                    }
                    for item in summary_properties
                ],
            },
        )
        system_summaries.append(path)

    outputs = {
        relative(path): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(OUTPUT.rglob("*"))
        if path.is_file() and path != MANIFEST_OUTPUT
    }
    for path in system_summaries:
        outputs[relative(path)] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    input_paths = [snapshot_path for _, _, snapshot_path, _ in captured_properties] + [TRACE_SCHEMA]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator": artifact(Path(__file__)),
        "inputs": [artifact(path) for path in input_paths],
        "tools": {
            "TAMonitor": artifact(TAMONITOR),
            "mitppl": artifact(MITPPL),
            "MoniTAal-bin": artifact(MONITAAL_BIN),
            "libMoniTAal.a": artifact(MONITAAL_LIBRARY),
        },
        "property_count": len(properties),
        "trace_count": main["trace_count"],
        "command_count": len(commands),
        "outputs": dict(sorted(outputs.items())),
        "validation_command": "PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check",
    }
    write_json(MANIFEST_OUTPUT, manifest)
    print(
        "generated monitor validation: "
        f"properties={len(properties)} traces={main['trace_count']} "
        f"property_statuses={dict(property_status_counts)} "
        f"trace_comparisons={dict(trace_comparison_counts)}"
    )
    return 0


def check() -> int:
    failures: list[str] = []

    def audit(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    try:
        main = json.loads(MAIN_OUTPUT.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST_OUTPUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: cannot read monitor validation: {error}", file=sys.stderr)
        return 1

    audit(main.get("property_count") == 8, "main property_count is not 8")
    audit(main.get("scope", {}).get("firmware_trace_evaluation_performed") is False, "firmware trace scope changed")
    audit(main.get("scope", {}).get("implementation_satisfaction_assessed") is False, "implementation assessment scope changed")
    audit(main.get("generated_by", {}).get("sha256") == sha256(Path(__file__)), "generator hash drift")
    audit(manifest.get("generator", {}).get("sha256") == sha256(Path(__file__)), "manifest generator hash drift")
    audit(manifest.get("property_count") == 8, "manifest property count mismatch")
    audit(manifest.get("trace_count") == main.get("trace_count"), "manifest trace count mismatch")
    audit(
        main.get("tool_inventory", {}).get("MoniTAal", {}).get("automata_smoke", {}).get("status") == "PASS",
        "standalone MoniTAal automata smoke status changed",
    )
    audit(
        main.get("tool_inventory", {}).get("MoniTAal", {}).get("formula_input_probe", {}).get("status")
        == "UNSUPPORTED_XML_AUTOMATA_REQUIRED",
        "standalone MoniTAal formula-input boundary changed",
    )

    for path_text, expected in manifest.get("outputs", {}).items():
        path = ROOT / path_text
        audit(path.is_file(), f"missing output {path_text}")
        if path.is_file():
            audit(path.stat().st_size == expected["bytes"], f"byte count drift {path_text}")
            audit(sha256(path) == expected["sha256"], f"hash drift {path_text}")
    for item in manifest.get("inputs", []):
        path = ROOT / item["path"]
        audit(path.is_file() and sha256(path) == item["sha256"], f"input drift {item['path']}")
    for item in manifest.get("tools", {}).values():
        path = ROOT / item["path"]
        audit(path.is_file() and sha256(path) == item["sha256"], f"tool drift {item['path']}")

    trace_schema = json.loads(TRACE_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft7Validator(trace_schema)
    property_status_counts: Counter[str] = Counter()
    trace_counts: Counter[str] = Counter()
    trace_execution_counts: Counter[str] = Counter()
    trace_total = 0
    for prop in main.get("properties", []):
        property_id = prop.get("property_id", "unknown")
        source_path = ROOT / prop["source_property_path"]
        live_path = ROOT / prop["live_property_path"]
        if source_path.is_file():
            source = json.loads(source_path.read_text(encoding="utf-8"))
            audit(source["mitl"]["status"] == "CONCRETE_UNVALIDATED", f"{property_id}: captured source formula status changed")
            audit(source["implementation_satisfaction"] == "NOT_ASSESSED", f"{property_id}: captured implementation status changed")
            audit(source["property_id"] == property_id, f"{property_id}: captured identity changed")
            audit(source["mitl"]["concrete"] == prop["source_formula"], f"{property_id}: captured formula changed")
            if live_path.is_file():
                live = json.loads(live_path.read_text(encoding="utf-8"))
                audit(live["property_id"] == property_id, f"{property_id}: live identity drift")
                audit(live["mitl"]["concrete"] == source["mitl"]["concrete"], f"{property_id}: live formula drift")
                audit(live["implementation_satisfaction"] == "NOT_ASSESSED", f"{property_id}: live implementation status changed")
        ast = FormulaParser(prop["monitor_encoding"]["formula"]).parse()
        audit(ast.names() == set(prop["ap_order"]), f"{property_id}: AST/AP identity drift")
        property_status_counts[prop["overall_status"]] += 1
        runtime_diagnostics = prop.get("runtime_diagnostics")
        if property_id == "ARD-COPTER-RTL-003":
            audit(runtime_diagnostics is not None, f"{property_id}: missing bounded runtime diagnostics")
            if runtime_diagnostics is not None:
                audit(
                    runtime_diagnostics.get("primary_configuration_changed") is False,
                    f"{property_id}: diagnostic altered primary configuration",
                )
                diagnostic_path = ROOT / runtime_diagnostics["artifact"]["path"]
                try:
                    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    audit(False, f"{property_id}: diagnostic read failed: {error}")
                    diagnostic = {}
                attempts = {item["attempt_id"]: item for item in diagnostic.get("attempts", [])}
                audit(
                    set(attempts) == {"symbolic_max_valuations_65536", "concrete_default_max_valuations"},
                    f"{property_id}: diagnostic attempt set changed",
                )
                if "symbolic_max_valuations_65536" in attempts:
                    audit(
                        attempts["symbolic_max_valuations_65536"]["max_valuations"] == 65536
                        and attempts["symbolic_max_valuations_65536"]["state"] == "symbolic",
                        f"{property_id}: symbolic diagnostic parameters changed",
                    )
                if "concrete_default_max_valuations" in attempts:
                    audit(
                        attempts["concrete_default_max_valuations"]["max_valuations"] is None
                        and attempts["concrete_default_max_valuations"]["state"] == "concrete",
                        f"{property_id}: concrete diagnostic parameters changed",
                    )
                audit(
                    all(item.get("wall_timeout_seconds") == 60 for item in attempts.values()),
                    f"{property_id}: diagnostic timeout changed",
                )
                for attempt in attempts.values():
                    audit(
                        monitor_comparison(
                            attempt["expected_infinite_prefix_verdict"],
                            attempt["status"],
                            attempt["verdict"],
                        )
                        == attempt["comparison_status"],
                        f"{property_id}: diagnostic comparison drift for {attempt['attempt_id']}",
                    )
        else:
            audit(runtime_diagnostics is None, f"{property_id}: unexpected runtime diagnostics")
        for trace_result in prop.get("traces", []):
            trace_total += 1
            trace_path = ROOT / trace_result["trace"]["path"]
            try:
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                audit(False, f"{trace_result.get('trace_id')}: trace read failed: {error}")
                continue
            errors = list(validator.iter_errors(trace))
            audit(not errors, f"{trace_result['trace_id']}: trace schema failed")
            audit(trace["clock_domain"] == prop["clock_domain"], f"{trace_result['trace_id']}: clock mismatch")
            audit(trace["dropped_event_count"] == 0, f"{trace_result['trace_id']}: dropped events")
            audit(
                all(set(event["values"]) == set(prop["ap_order"]) for event in trace["events"]),
                f"{trace_result['trace_id']}: incomplete AP valuation",
            )
            audit(
                all(trace["events"][i]["time"] < trace["events"][i + 1]["time"] for i in range(len(trace["events"]) - 1)),
                f"{trace_result['trace_id']}: nonmonotonic time",
            )
            oracle_verdict = "POSITIVE" if oracle_eval(ast, trace["events"], 0) else "NEGATIVE"
            audit(oracle_verdict == trace_result["oracle"]["verdict"], f"{trace_result['trace_id']}: oracle drift")
            execution_status = trace_result["tamonitor"]["status"]
            trace_execution_counts[execution_status] += 1
            expected_prefix = (
                "NEGATIVE"
                if trace_result["case_kind"] in {"too_early_one_tick", "boundary_exact_excluded"}
                else "INCONCLUSIVE"
            )
            audit(
                trace_result["expected"]["tamonitor_infinite_prefix_verdict"] == expected_prefix,
                f"{trace_result['trace_id']}: expected infinite-prefix verdict drift",
            )
            audit(
                monitor_comparison(expected_prefix, execution_status, trace_result["tamonitor"]["verdict"])
                == trace_result["comparison_status"],
                f"{trace_result['trace_id']}: TAMonitor comparison drift",
            )
            stderr_path = ROOT / trace_result["tamonitor"]["stderr"]["path"]
            stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
            if execution_status == "EXECUTED":
                audit(
                    trace_result["tamonitor"]["exit_code"] == 0
                    and trace_result["tamonitor"]["metadata"] is not None,
                    f"{trace_result['trace_id']}: executed status lacks successful metadata",
                )
            elif execution_status == "UNSUPPORTED_MONITAAL_POSITIVE_NEGATIVE_BOTH_OUT_ASSERTION":
                audit(
                    "Both are out" in stderr_text and "pos != OUT || neg != OUT" in stderr_text,
                    f"{trace_result['trace_id']}: MoniTAal assertion evidence drift",
                )
            elif execution_status == "UNSUPPORTED_TAMONITOR_BDD_PROJECTION_VALUATION_LIMIT":
                audit(
                    "BDD projection valuation limit exceeded" in stderr_text,
                    f"{trace_result['trace_id']}: BDD limit evidence drift",
                )
            monitor_trace_path = ROOT / trace_result["monitor_trace"]["path"]
            try:
                with monitor_trace_path.open(encoding="utf-8", newline="") as stream:
                    monitor_rows = list(csv.DictReader(stream))
            except (OSError, csv.Error) as error:
                audit(False, f"{trace_result['trace_id']}: monitor trace read failed: {error}")
                monitor_rows = []
            audit(
                [int(row["time"]) for row in monitor_rows]
                == [event["time"] for event in trace["events"]]
                if monitor_rows
                else False,
                f"{trace_result['trace_id']}: TAMonitor absolute-time encoding drift",
            )
            audit(
                [row["props"] for row in monitor_rows]
                == [true_names(event["values"], prop["ap_order"]) for event in trace["events"]]
                if monitor_rows
                else False,
                f"{trace_result['trace_id']}: TAMonitor AP valuation encoding drift",
            )
            trace_counts[trace_result["comparison_status"]] += 1

    audit(trace_total == main.get("trace_count"), "trace total mismatch")
    audit(dict(sorted(property_status_counts.items())) == main["counts"]["property_status_counts"], "property status counts drift")
    audit(dict(sorted(trace_counts.items())) == main["counts"]["trace_comparison_counts"], "trace comparison counts drift")
    audit(
        dict(sorted(trace_execution_counts.items())) == main["counts"]["trace_execution_status_counts"],
        "trace execution status counts drift",
    )
    audit(
        len(main.get("verdict_mismatches", [])) == trace_counts.get("FAILED_VERDICT_MISMATCH", 0),
        "top-level verdict mismatch index drift",
    )
    audit(
        sum(item["trace_count"] for item in main.get("runtime_blockers", []))
        == sum(value for key, value in trace_execution_counts.items() if key.startswith("UNSUPPORTED")),
        "top-level runtime blocker index drift",
    )
    commands = [json.loads(line) for line in COMMANDS_OUTPUT.read_text(encoding="utf-8").splitlines() if line]
    audit(len(commands) == main["counts"]["command_count"] == manifest["command_count"], "command count mismatch")
    for command in commands:
        for stream in ("stdout", "stderr"):
            path = ROOT / command[stream]["path"]
            audit(path.is_file() and sha256(path) == command[stream]["sha256"], f"{command['command_id']}: {stream} drift")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"FAIL: monitor validation checks={len(failures)}", file=sys.stderr)
        return 1
    print(
        "PASS: monitor validation "
        f"properties={main['property_count']} traces={main['trace_count']} "
        f"property_statuses={main['counts']['property_status_counts']} "
        f"trace_comparisons={main['counts']['trace_comparison_counts']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace only the generated milestone7/monitor_validation directory after validating eight Stage-6 CONCRETE_UNVALIDATED inputs")
    parser.add_argument("--check", action="store_true", help="validate existing artifacts without rewriting them")
    args = parser.parse_args()
    if args.check and args.force:
        parser.error("--check and --force are mutually exclusive")
    return check() if args.check else generate(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
