#!/usr/bin/env python3
"""Validate expanded PGFuzz author-input associations and current identities."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = DATASET_ROOT / "validation" / "author_dependency_validation.json"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_location(location: str) -> tuple[Path, int] | None:
    if ":" not in location:
        return None
    raw_path, raw_line = location.rsplit(":", 1)
    if not raw_line.isdigit():
        return None
    return PROJECT_ROOT / raw_path, int(raw_line)


def main() -> None:
    payload = json.loads((DATASET_ROOT / "author_input_dependencies.json").read_text(encoding="utf-8"))
    rows = payload["association_rows"]
    csv_rows = load_csv(DATASET_ROOT / "author_input_dependencies.csv")
    identity_rows = load_csv(DATASET_ROOT / "current_input_identity_map.csv")
    coverage_rows = load_csv(DATASET_ROOT / "formula_parameter_coverage.csv")
    formula_payload = json.loads((DATASET_ROOT / "table_xii_formula_inventory.json").read_text(encoding="utf-8"))

    checks = 0
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    check(payload["schema_version"] == "1.0", "unexpected dependency schema version")
    check(len(rows) == 7569, "expanded association count is not 7569")
    check(len(csv_rows) == len(rows), "association CSV/JSON row count differs")
    check(len(identity_rows) == 356, "unique identity count is not 356")
    check(len(coverage_rows) == 20, "formula parameter coverage count is not 20")
    check(len({row["association_id"] for row in rows}) == len(rows), "association identifiers are not unique")
    check({row["policy_id"] for row in rows} == {p["policy_id"] for p in formula_payload["policies"]}, "association policy coverage differs from 51 formulas")
    check(sum(row["system"] == "ArduPilot" for row in rows) == 5872, "ArduPilot association count differs")
    check(sum(row["system"] == "PX4" for row in rows) == 1697, "PX4 association count differs")

    expected_class_counts = {
        ("ArduPilot", "InputP"): 1868,
        ("ArduPilot", "InputC"): 1246,
        ("ArduPilot", "InputE"): 2753,
        ("ArduPilot", "PRECONDITION"): 5,
        ("PX4", "InputP"): 633,
        ("PX4", "InputC"): 833,
        ("PX4", "InputE"): 231,
        ("PX4", "PRECONDITION"): 0,
    }
    for key, expected in expected_class_counts.items():
        check(sum((row["system"], row["input_class"]) == key for row in rows) == expected, f"class count differs: {key}")

    file_cache: dict[Path, tuple[str, list[str]]] = {}
    valid_statuses = set(payload["status_definitions"])
    valid_strengths = set(payload["dependency_strength_definitions"])
    valid_default_statuses = {
        "UNKNOWN",
        "SOURCE_METADATA_LITERAL_OR_EXPRESSION",
        "CURATED_FROZEN_SOURCE_RESOLUTION",
    }
    for row in rows:
        path = PROJECT_ROOT / row["artifact_source_path"]
        if path not in file_cache:
            file_cache[path] = (digest(path), path.read_text(encoding="utf-8").splitlines())
        file_digest, lines = file_cache[path]
        line_number = int(row["artifact_source_line"])
        check(path.is_file(), f"missing artifact source: {path}")
        check(file_digest == row["artifact_file_sha256"], f"artifact digest differs: {path}")
        check(1 <= line_number <= len(lines), f"artifact line out of range: {row['association_id']}")
        if 1 <= line_number <= len(lines):
            check(lines[line_number - 1] == row["artifact_raw"], f"artifact raw line differs: {row['association_id']}")
        check(row["current_identity_status"] in valid_statuses, f"unknown identity status: {row['association_id']}")
        check(row["dependency_strength"] in valid_strengths, f"unknown dependency strength: {row['association_id']}")
        check(row["implementation_satisfaction"] == "NOT_ASSESSED", f"satisfaction gate failed: {row['association_id']}")
        check(row["runtime_write_change_verification"] == "NOT_TESTED", f"write-test gate failed: {row['association_id']}")
        check(
            row["current_default_evidence_status"] in valid_default_statuses,
            f"unknown current-default evidence status: {row['association_id']}",
        )
        check(bool(row["current_default_evidence_note_zh"]), f"current-default evidence note missing: {row['association_id']}")
        check(row["dependency_strength"] == ("EXPLICIT_PRECONDITION" if row["input_class"] == "PRECONDITION" else "CANDIDATE_ASSOCIATION"), f"dependency strength/class mismatch: {row['association_id']}")
        if row["input_class"] == "InputP":
            check(row["artifact_column_6_interpretation"] == "AUTHOR_PARSER_CALLS_UNITS_BUT_ARTIFACT_VALUES_MAY_BE_INCREMENT", f"parameter sixth-column warning missing: {row['association_id']}")
        if row["current_identity_status"] in {"EXACT_CURRENT_DEFINITION", "RENAMED_CURRENT_DEFINITION"}:
            check(
                bool(row["current_source_locations"] or row["current_source_location_confidence"] == "unresolved"),
                f"current definition lacks source or explicit unresolved locator status: {row['association_id']}",
            )
        if row["current_runtime_value"]:
            check(bool(row["current_runtime_capture"] and row["current_runtime_profile"]), f"runtime value lacks capture/profile: {row['association_id']}")

    checked_locations: set[str] = set()
    for row in identity_rows:
        for location in row["current_source_locations"].split("|"):
            if not location or location in checked_locations:
                continue
            checked_locations.add(location)
            parsed = split_location(location)
            check(parsed is not None, f"malformed current source location: {location}")
            if parsed is None:
                continue
            path, line_number = parsed
            check(path.is_file(), f"missing current source path: {location}")
            if path.is_file():
                line_count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
                check(1 <= line_number <= line_count, f"current source line out of range: {location}")
        evidence = row["current_alias_evidence"]
        if evidence.startswith("baseline/"):
            parsed = split_location(evidence)
            check(parsed is not None, f"malformed alias evidence: {evidence}")
            if parsed is not None:
                path, line_number = parsed
                check(path.is_file(), f"missing alias evidence path: {evidence}")
                if path.is_file():
                    line_count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
                    check(1 <= line_number <= line_count, f"alias evidence line out of range: {evidence}")
        check(row["implementation_satisfaction"] == "NOT_ASSESSED", f"identity satisfaction gate failed: {row['system']}:{row['input_class']}:{row['artifact_name']}")

    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(row["system"], row["input_class"], row["artifact_name"])].append(row)
    identity_index = {(row["system"], row["input_class"], row["artifact_name"]): row for row in identity_rows}
    check(set(groups) == set(identity_index), "identity keys differ from association aggregation")
    for key, group in groups.items():
        if key not in identity_index:
            continue
        identity = identity_index[key]
        check(int(identity["association_occurrences"]) == len(group), f"identity occurrence count differs: {key}")
        check(identity["current_identity_status"] == group[0]["current_identity_status"], f"identity status differs: {key}")
        check(identity["current_name"] == group[0]["current_name"], f"current name differs: {key}")

    chute = [row for row in rows if row["input_class"] == "PRECONDITION"]
    check(len(chute) == 5, "explicit precondition count differs")
    check({row["policy_id"] for row in chute} == {"A.CHUTE1"}, "non-CHUTE explicit precondition found")
    check({row["artifact_name"] for row in chute} == {"CHUTE_ENABLED", "CHUTE_TYPE", "SERVO9_FUNCTION", "SIM_PARA_ENABLE", "SIM_PARA_PIN"}, "CHUTE precondition names differ")

    coverage_index = {(row["policy_id"], row["formula_parameter"]): row for row in coverage_rows}
    expected_missing = {
        ("A.CHUTE1", "CHUTE_ALT_MIN"),
        ("PX.RTL4", "RTL_LAND_DELAY"),
        ("PX.LAND1", "MPC_LAND_SPEED"),
        ("PX.TAKEOFF2", "MPC_TKO_SPEED"),
    }
    actual_missing = {key for key, row in coverage_index.items() if row["present_in_author_input_files"] == "False"}
    check(actual_missing == expected_missing, "formula parameters omitted from author input files differ")
    check(coverage_index[("PX.GPS.FS1", "COM_POS_FS_DELAY")]["current_identity_status"] == "CURRENT_DEFINITION_NOT_FOUND", "deleted COM_POS_FS_DELAY not unresolved")
    check(coverage_index[("A.RTL1", "RTL_ALT")]["current_name"] == "RTL_ALT_M", "RTL_ALT current rename differs")
    check(coverage_index[("PX.HOLD2", "MIS_LTRMIN_ALT")]["current_name"] == "NAV_MIN_LTR_ALT", "MIS_LTRMIN_ALT current rename differs")
    expected_curated_defaults = {
        ("A.RTL1", "RTL_ALT"): "15",
        ("A.RTL2", "RTL_ALT"): "15",
        ("A.RTL3", "RTL_ALT"): "15",
        ("A.LAND1", "LAND_SPEED_HIGH"): "0",
        ("A.LAND2", "LAND_SPEED"): "0.5",
        ("A.DRIFT1", "FS_EKF_ACTION"): "1",
        ("A.SPORT1", "PILOT_SPEED_UP"): "2.5",
        ("A.RC.FS1", "FS_THR_VALUE"): "975",
        ("A.RC.FS2", "FS_THR_VALUE"): "975",
        ("A.CHUTE1", "CHUTE_ALT_MIN"): "10",
    }
    for key, expected_default in expected_curated_defaults.items():
        row = coverage_index[key]
        check(row["current_default"] == expected_default, f"curated formula default differs: {key}")
        check(
            row["current_default_evidence_status"] == "CURATED_FROZEN_SOURCE_RESOLUTION",
            f"curated formula default evidence status differs: {key}",
        )
        parsed = split_location(row["current_default_evidence_source"])
        check(parsed is not None, f"curated formula default source malformed: {key}")
        if parsed is not None:
            source_path, line_number = parsed
            check(source_path.is_file(), f"curated formula default source missing: {key}")
            if source_path.is_file():
                line_count = sum(1 for _ in source_path.open(encoding="utf-8", errors="replace"))
                check(1 <= line_number <= line_count, f"curated formula default source line out of range: {key}")

    expected_unresolved_noncommands = {
        ("ArduPilot", "SIM_MAG_ERROR"), ("ArduPilot", "SIM_TEMP_FLIGHT"),
        ("ArduPilot", "SIM_VICON_HSTLEN"), ("ArduPilot", "SIM_WIND_DELAY"),
        ("ArduPilot", "RNGFND_GAIN"), ("PX4", "SIM_IGN_HOME_ALT"),
        ("PX4", "SIM_IGN_HOME_LAT"), ("PX4", "SIM_IGN_HOME_LON"),
        ("PX4", "COM_POS_FS_DELAY"), ("PX4", "GF_ALTMODE"),
        ("PX4", "LNDMC_ALT_MAX"),
    }
    actual_unresolved_noncommands = {
        (row["system"], row["artifact_name"])
        for row in identity_rows
        if row["input_class"] != "InputC" and row["current_identity_status"] == "CURRENT_DEFINITION_NOT_FOUND"
    }
    check(actual_unresolved_noncommands == expected_unresolved_noncommands, "unresolved parameter/environment identity set differs")

    status_counts = Counter(row["current_identity_status"] for row in identity_rows)
    report = {
        "schema_version": "1.0",
        "validator": "validate_author_dependencies.py",
        "result": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "counts": {
            "association_rows": len(rows),
            "unique_identity_rows": len(identity_rows),
            "formula_parameter_coverage_rows": len(coverage_rows),
            "unique_identity_statuses": dict(sorted(status_counts.items())),
            "validated_current_source_locations": len(checked_locations),
        },
        "scope_note_zh": "通过只证明作者输入文件逐行展开、当前身份目录和证据路径内部一致；不证明候选输入与性质存在真实数据依赖，也不证明固件满足性质。",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
