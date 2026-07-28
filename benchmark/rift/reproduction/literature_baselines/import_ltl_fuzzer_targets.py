#!/usr/bin/env python3
"""Import the source-location tuples shipped by the ICSE'22 LTL-Fuzzer artifact.

The importer is deliberately strict.  It resolves every RERS target against the
frozen source line and maps the printed numeric output to the artifact's atomic
proposition name.  The Telnet targets are retained even when their source
gitlink cannot be resolved, so an incomplete upstream artifact cannot silently
look complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


PRINTF_RE = re.compile(r'printf\("%d\\n",\s*(\d+)\)')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def parse_mapping(path: Path) -> tuple[dict[int, str], dict[int, str]]:
    value_to_symbol: dict[int, str] = {}
    symbol_to_event: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        symbol, value_text = raw.split()
        value = int(value_text)
        value_to_symbol[value] = symbol
        prefix = "i" if value <= 10 else "o"
        symbol_to_event[value] = prefix + symbol
    return value_to_symbol, symbol_to_event


def parse_rers(repo: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    subject = repo / "experiment" / "Problem1"
    source = subject / "src" / "Problem1.c"
    targets = subject / "target" / "targets.txt"
    mapping = subject / "event_map_dir" / "event_mapping.txt"
    all_events = subject / "all_event_dir" / "all_events.txt"
    formula_file = subject / "ltl_dir" / "ltl.txt"

    _, value_to_event = parse_mapping(mapping)
    declared_events = {
        line.strip() for line in all_events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    source_lines = source.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, object]] = []

    for ordinal, raw in enumerate(
        targets.read_text(encoding="utf-8").splitlines(), start=1
    ):
        file_name, line_text, target_value_text = raw.split(":", 2)
        line = int(line_text)
        if file_name != source.name:
            raise ValueError(f"unexpected RERS source name: {raw}")
        if not (1 <= line <= len(source_lines)):
            raise ValueError(f"out-of-range target: {raw}")
        source_text = source_lines[line - 1]
        match = PRINTF_RE.search(source_text)
        if match is None:
            raise ValueError(f"target is not an integer output site: {raw}")
        output_value = int(match.group(1))
        target_value = int(target_value_text)
        if target_value != output_value:
            raise ValueError(
                f"target event {target_value} disagrees with source output "
                f"{output_value} at {raw}"
            )
        proposition = value_to_event.get(output_value)
        if proposition is None or proposition not in declared_events:
            raise ValueError(f"unmapped output {output_value} at {raw}")
        records.append(
            {
                "benchmark": "LTL-Fuzzer/Problem1",
                "ordinal": ordinal,
                "source_file": "experiment/Problem1/src/Problem1.c",
                "line": line,
                "column": int(source_text.index("printf")) + 1,
                "source_text": source_text.strip(),
                "numeric_event": output_value,
                "atomic_proposition": proposition,
                "target_kind": "output_event",
                "resolution": "EXACT_ARTIFACT_SOURCE",
            }
        )

    formula_record, event_list = formula_file.read_text(encoding="utf-8").strip().split(
        ":", 1
    )
    return records, {
        "property": formula_record,
        "formula_event_list": event_list.split(","),
        "declared_events": sorted(declared_events),
        "source_sha256": sha256(source),
        "targets_sha256": sha256(targets),
        "event_mapping_sha256": sha256(mapping),
        "formula_sha256": sha256(formula_file),
    }


def parse_telnet(repo: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    subject = repo / "experiment" / "testTelnet"
    targets = subject / "targets" / "targets.txt"
    all_events = subject / "all_event_dir" / "all_events.txt"
    formula_file = subject / "ltl_dir" / "ltl.txt"
    contiki = subject / "contiki"
    records: list[dict[str, object]] = []

    gitlink = git_output(repo, "ls-tree", "HEAD", "experiment/testTelnet/contiki")
    gitlink_commit = gitlink.split()[2]
    source = contiki / "examples" / "telnet-server" / "telnetd.c"
    source_available = source.is_file()
    source_lines = source.read_text(encoding="utf-8").splitlines() if source_available else []

    for ordinal, raw in enumerate(
        targets.read_text(encoding="utf-8").splitlines(), start=1
    ):
        file_name, line_text, proposition = raw.split(":", 2)
        line = int(line_text)
        exact = source_available and 1 <= line <= len(source_lines)
        records.append(
            {
                "benchmark": "LTL-Fuzzer/testTelnet",
                "ordinal": ordinal,
                "source_file": f"experiment/testTelnet/contiki/**/{file_name}",
                "line": line,
                "column": None,
                "source_text": source_lines[line - 1].strip() if exact else None,
                "numeric_event": None,
                "atomic_proposition": proposition,
                "target_kind": "protocol_event",
                "resolution": (
                    "EXACT_ARTIFACT_SOURCE"
                    if exact
                    else "SOURCE_UNAVAILABLE_UNCONFIGURED_GITLINK"
                ),
            }
        )

    formula_record, formula_event_list = formula_file.read_text(
        encoding="utf-8"
    ).strip().split(":", 1)
    declared_events = [
        line.strip() for line in all_events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target_events = [record["atomic_proposition"] for record in records]
    formula_events = formula_event_list.split(",")
    return records, {
        "property": formula_record,
        "formula_event_list": formula_events,
        "declared_events": declared_events,
        "target_events": target_events,
        "gitlink_commit": gitlink_commit,
        "gitmodules_present": (repo / ".gitmodules").is_file(),
        "source_available": source_available,
        "targets_sha256": sha256(targets),
        "formula_sha256": sha256(formula_file),
        "identifier_inconsistencies": sorted(
            set(formula_events).symmetric_difference(set(declared_events))
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    repo = args.artifact.resolve()

    rers_targets, rers_meta = parse_rers(repo)
    telnet_targets, telnet_meta = parse_telnet(repo)
    records = rers_targets + telnet_targets
    result = {
        "schema_version": "rift.literature.ltl-targets.v1",
        "artifact": {
            "name": "LTL-Fuzzer",
            "venue": "ICSE 2022",
            "url": "https://github.com/ltlfuzzer/LTL-Fuzzer",
            "commit": git_output(repo, "rev-parse", "HEAD"),
            "license": "Apache-2.0",
        },
        "summary": {
            "total_target_tuples": len(records),
            "resolved_exactly": sum(
                record["resolution"] == "EXACT_ARTIFACT_SOURCE" for record in records
            ),
            "unresolved": sum(
                record["resolution"] != "EXACT_ARTIFACT_SOURCE" for record in records
            ),
            "rers_output_targets": len(rers_targets),
            "telnet_protocol_targets": len(telnet_targets),
        },
        "rers": rers_meta,
        "telnet": telnet_meta,
        "targets": records,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
