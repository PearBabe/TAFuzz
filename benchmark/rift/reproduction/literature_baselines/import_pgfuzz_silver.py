#!/usr/bin/env python3
"""Freeze PGFuzz's paper policy universe and public artifact input maps.

This is a silver standard, not a ground truth.  The paper has 56 logical
policies, while the repository stores some logical policies in grouped map
directories and omits Paparazzi.  Both facts are represented explicitly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ARDUPILOT_POLICIES = [
    *(f"A.RTL{i}" for i in range(1, 5)),
    "A.FLIP1",
    "A.FLIP2",
    "A.FLIP3",
    "A.FLIPGeneral",
    "A.ALT_HOLD1",
    "A.ALT_HOLD2",
    *(f"A.CIRCLE{i}" for i in range(1, 8)),
    "A.LAND1",
    "A.LAND2",
    "A.AUTO1",
    "A.BRAKE1",
    "A.DRIFT1",
    "A.LOITER1",
    "A.GUIDED1",
    "A.SPORT1",
    "A.RC.FS1",
    "A.RC.FS2",
    "A.CHUTE1",
    "A.GPS.FS1",
    "A.GPS.FS2",
]

PX4_POLICIES = [
    *(f"PX.RTL{i}" for i in range(1, 6)),
    *(f"PX.ORBIT{i}" for i in range(1, 7)),
    "PX.LAND1",
    "PX.ALTITUDE1",
    "PX.POSITION1",
    "PX.HOLD1",
    "PX.HOLD2",
    "PX.TAKEOFF1",
    "PX.TAKEOFF2",
    "PX.GPS.FS1",
    "PX.GPS.FS2",
    "PX.GPS.FS3",
]

PAPARAZZI_POLICIES = [
    "PP.Hover",
    "PP.HoverZ",
    "PP.HoverC",
    "PP.TAKEOFF1",
    "PP.HOME1",
]

ARTIFACT_ALIASES = {
    "A.FLIPGeneral": "A.FLIP4",
    "A.CIRCLE4": "A.CIRCLE4_6",
    "A.CIRCLE5": "A.CIRCLE4_6",
    "A.CIRCLE6": "A.CIRCLE4_6",
    "A.CHUTE1": "A.CHUTE",
    "PX.ORBIT4": "PX.ORBIT4_5",
    "PX.ORBIT5": "PX.ORBIT4_5",
}

FILES = ("parameters.txt", "cmds.txt", "envs.txt", "preconditions.txt")


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


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row for row in csv.reader(stream) if any(cell.strip() for cell in row)]


def parse_map_file(path: Path, kind: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    raw_rows = read_csv_rows(path) if kind != "preconditions" else []
    if kind == "parameters":
        for columns in raw_rows:
            rows.append({"name": columns[0].strip(), "columns": columns})
    elif kind == "commands":
        for columns in raw_rows:
            rows.append(
                {
                    "name": columns[0].strip(),
                    "command_value": columns[1].strip() if len(columns) > 1 else None,
                    "columns": columns,
                }
            )
    elif kind == "environment":
        for columns in raw_rows:
            rows.append({"name": columns[0].strip(), "columns": columns})
    else:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if not raw.strip():
                continue
            columns = raw.split()
            rows.append(
                {
                    "name": columns[0],
                    "value": " ".join(columns[1:]) if len(columns) > 1 else None,
                    "columns": columns,
                }
            )

    names = [row["name"] for row in rows]
    result = {
        "path": str(path),
        "sha256": sha256(path),
        "row_count": len(rows),
        "unique_name_count": len(set(names)),
        "duplicate_names": sorted({name for name in names if names.count(name) > 1}),
        "names": list(dict.fromkeys(names)),
    }
    if kind == "preconditions":
        result["entries"] = rows
    return result


def map_dir_record(workspace: Path, directory: Path) -> dict[str, Any]:
    relative = directory.relative_to(workspace)
    for file_name in FILES:
        if not (directory / file_name).is_file():
            raise ValueError(f"incomplete PGFuzz map directory: {relative}/{file_name}")
    return {
        "path": str(relative),
        "files": {
            "parameters": parse_map_file(directory / "parameters.txt", "parameters"),
            "commands": parse_map_file(directory / "cmds.txt", "commands"),
            "environment": parse_map_file(directory / "envs.txt", "environment"),
            "preconditions": parse_map_file(
                directory / "preconditions.txt", "preconditions"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    artifact = workspace / "baseline" / "pgfuzz"
    paper = artifact / "Kim 等 - 2021 - PGFUZZ Policy-guided fuzzing for robotic vehicles.pdf"

    if len(ARDUPILOT_POLICIES) != 30 or len(PX4_POLICIES) != 21 or len(PAPARAZZI_POLICIES) != 5:
        raise AssertionError("paper policy inventory no longer totals 56")

    map_roots = {
        "ArduPilot": artifact / "ArduPilot" / "policies",
        "PX4": artifact / "PX4" / "policies",
    }
    map_directories: dict[str, dict[str, Any]] = {}
    for system, root in map_roots.items():
        for directory in sorted(path for path in root.iterdir() if path.is_dir()):
            map_directories[directory.name] = {
                "system": system,
                **map_dir_record(workspace, directory),
            }

    records: list[dict[str, Any]] = []
    inventories = (
        ("ArduPilot", ARDUPILOT_POLICIES),
        ("PX4", PX4_POLICIES),
        ("Paparazzi", PAPARAZZI_POLICIES),
    )
    for system, policy_ids in inventories:
        for policy_id in policy_ids:
            artifact_id = ARTIFACT_ALIASES.get(policy_id, policy_id)
            available = artifact_id in map_directories
            records.append(
                {
                    "policy_id": policy_id,
                    "system": system,
                    "paper_source": {
                        "table": "Table XII",
                        "pdf_page": 18,
                    },
                    "artifact_map_id": artifact_id if available else None,
                    "artifact_map_path": (
                        map_directories[artifact_id]["path"] if available else None
                    ),
                    "artifact_map_status": (
                        "SILVER_MAP_AVAILABLE"
                        if available
                        else "NOT_PUBLISHED_IN_ARTIFACT"
                    ),
                    "alias_kind": (
                        "GROUPED_OR_RENAMED" if policy_id in ARTIFACT_ALIASES else "EXACT"
                    ),
                }
            )

    referenced = {
        record["artifact_map_id"] for record in records if record["artifact_map_id"]
    }
    unreferenced = sorted(set(map_directories) - referenced)
    missing = [record["policy_id"] for record in records if not record["artifact_map_id"]]

    result = {
        "schema_version": "rift.literature.pgfuzz-silver.v1",
        "classification": "SILVER_STANDARD_NOT_GROUND_TRUTH",
        "paper": {
            "title": "PGFUZZ: Policy-Guided Fuzzing for Robotic Vehicles",
            "venue": "NDSS 2021",
            "doi": "10.14722/ndss.2021.24096",
            "policy_source": "Table XII, PDF page 18",
            "sha256": sha256(paper),
        },
        "artifact": {
            "url": "https://github.com/purseclab/PGFUZZ",
            "commit": git_output(artifact, "rev-parse", "HEAD"),
            "tracked_tree_oid": git_output(artifact, "rev-parse", "HEAD^{tree}"),
            "read_only_during_import": True,
        },
        "summary": {
            "paper_policy_count": len(records),
            "paper_counts_by_system": {
                system: len(policy_ids) for system, policy_ids in inventories
            },
            "paper_policies_with_public_map": len(records) - len(missing),
            "paper_policies_without_public_map": len(missing),
            "artifact_map_directory_count": len(map_directories),
            "artifact_map_directories_by_system": {
                system: sum(
                    map_record["system"] == system
                    for map_record in map_directories.values()
                )
                for system in map_roots
            },
            "unreferenced_artifact_map_directories": unreferenced,
            "missing_policy_ids": missing,
        },
        "interpretation": {
            "valid_use": (
                "Compare RIFT's discovered controllable frontier with PGFuzz's "
                "published, policy-specific candidate input sets."
            ),
            "invalid_use": (
                "Treat the sets as complete causal ground truth or infer that every "
                "listed input can actually change the policy AP."
            ),
            "cross_project_general": [
                "three input classes: parameter, command, environment",
                "set-recall/precision comparison after identifier normalization",
                "explicit accounting for grouped policies and missing artifacts",
            ],
            "project_specific": [
                "ArduPilot/PX4 parameter and command identifiers",
                "MAVLink command values, simulator environment names, and flight modes",
                "policy aliases, preconditions, and repository-curated exclusions",
            ],
        },
        "policies": records,
        "map_directories": map_directories,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
