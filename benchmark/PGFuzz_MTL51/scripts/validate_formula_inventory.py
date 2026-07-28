#!/usr/bin/env python3
"""Validate the deterministic PGFuzz Table-XII formula inventory."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = DATASET_ROOT / "scripts" / "build_formula_inventory.py"
PGFUZZ_ROOT = PROJECT_ROOT / "baseline" / "pgfuzz"
REPORT_PATH = DATASET_ROOT / "validation" / "formula_inventory_validation.json"


def load_builder():
    spec = importlib.util.spec_from_file_location("pgfuzz_formula_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load builder: {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    builder = load_builder()
    failures: list[str] = []
    checks = 0

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    builder.validate()
    payload = json.loads((DATASET_ROOT / "table_xii_formula_inventory.json").read_text(encoding="utf-8"))
    policies = payload["policies"]
    check(policies == builder.P, "generated JSON differs from deterministic builder records")
    check(payload["issue_definitions"] == builder.ISSUE_DEFS, "issue definitions differ")
    check(payload["role_definitions"] == builder.ROLE_DEFS, "role definitions differ")
    check(payload["source"]["pdf_sha256"] == "bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa94c90d7fcd", "PGFuzz PDF identity differs")
    check(len(policies) == 51, "policy count is not 51")
    check(sum(p["system"] == "ArduPilot" for p in policies) == 30, "ArduPilot policy count is not 30")
    check(sum(p["system"] == "PX4" for p in policies) == 21, "PX4 policy count is not 21")
    check([p["paper_order"] for p in policies] == list(range(1, 52)), "paper order is not contiguous")
    check(len({p["policy_id"] for p in policies}) == 51, "policy identifiers are not unique")
    check(all(p["dataset_role"] == "HISTORICAL_PROPERTY_SEED" for p in policies), "dataset role gate failed")
    check(all(p["implementation_satisfaction"] == "NOT_ASSESSED" for p in policies), "implementation satisfaction gate failed")

    expected_shared = {
        "A.CIRCLE4": "A.CIRCLE4_6",
        "A.CIRCLE5": "A.CIRCLE4_6",
        "A.CIRCLE6": "A.CIRCLE4_6",
        "A.FLIPGeneral": "A.FLIP4",
        "A.CHUTE1": "A.CHUTE",
        "PX.ORBIT4": "PX.ORBIT4_5",
        "PX.ORBIT5": "PX.ORBIT4_5",
    }
    for policy in policies:
        system_dir = "ArduPilot" if policy["system"] == "ArduPilot" else "PX4"
        policy_dir = PGFUZZ_ROOT / system_dir / "policies" / policy["artifact_policy_directory"]
        check(policy_dir.is_dir(), f"missing artifact directory: {policy_dir}")
        for filename in ("parameters.txt", "cmds.txt", "envs.txt", "preconditions.txt"):
            check((policy_dir / filename).is_file(), f"missing artifact input file: {policy_dir / filename}")
        if policy["policy_id"] in expected_shared:
            check(policy["artifact_policy_directory"] == expected_shared[policy["policy_id"]], f"shared-directory mapping differs: {policy['policy_id']}")

    check(not any(p["policy_id"] == "PX.CHUTE" for p in policies), "artifact-only PX.CHUTE leaked into Table-XII scope")
    check(sum(1 for path in PGFUZZ_ROOT.glob("*/policies/*/preconditions.txt") if path.stat().st_size > 0) == 1, "non-empty precondition-file count differs")

    by_id = {p["policy_id"]: p for p in policies}
    expected_conflict_atoms = {
        "A.FLIP1": {"Roll_t < 45deg", "Throttle_t >= 1500", "ALT_t > 10m"},
        "A.RC.FS1": {"Armed = true"},
        "PX.HOLD2": {"ALT_t < MIS_LTRMIN_ALT", "Target_ALT = MIS_LTRMIN_ALT"},
        "PX.TAKEOFF1": {"Target_ALT = MIS_TAKEOFF_ALT"},
    }
    for policy_id, expected_atoms in expected_conflict_atoms.items():
        actual = {a["expression"] for a in by_id[policy_id]["atomic_propositions"]}
        check(expected_atoms <= actual, f"description/formula conflict atoms incomplete: {policy_id}")
    check("FAILSAFE_IMPLICATION_REVERSED" in by_id["A.GPS.FS1"]["issues"], "reversed failsafe implication not marked")
    check("WRONG_PARAMETER_IN_FORMULA" in by_id["PX.RTL4"]["issues"], "PX.RTL4 parameter conflict not marked")
    check("TYPE_UNIT_MISMATCH" in by_id["PX.ORBIT6"]["issues"], "PX.ORBIT6 unit conflict not marked")

    ap_payload = json.loads((DATASET_ROOT / "atomic_proposition_inventory.json").read_text(encoding="utf-8"))
    ap_rows = ap_payload["rows"]
    expected_ap_count = sum(len(p["atomic_propositions"]) for p in policies)
    check(len(ap_rows) == expected_ap_count, "atomic-proposition JSON count differs")
    check(len({row["ap_id"] for row in ap_rows}) == expected_ap_count, "atomic-proposition identifiers are not unique")
    check(all(row["binding_status"] == "PENDING_CURRENT_SOURCE_BINDING" for row in ap_rows), "premature AP binding status found")
    check(all(row["implementation_satisfaction"] == "NOT_ASSESSED" for row in ap_rows), "AP satisfaction gate failed")

    with (DATASET_ROOT / "table_xii_formula_inventory.csv").open(newline="", encoding="utf-8") as handle:
        formula_csv_rows = list(csv.DictReader(handle))
    with (DATASET_ROOT / "atomic_proposition_inventory.csv").open(newline="", encoding="utf-8") as handle:
        ap_csv_rows = list(csv.DictReader(handle))
    check(len(formula_csv_rows) == 51, "formula CSV row count differs")
    check(len(ap_csv_rows) == expected_ap_count, "AP CSV row count differs")

    for system, expected_count in (("ArduPilot", 30), ("PX4", 21)):
        system_payload = json.loads((DATASET_ROOT / system / "formula_inventory.json").read_text(encoding="utf-8"))
        check(len(system_payload["policies"]) == expected_count, f"{system} split count differs")
        check(all(p["system"] == system for p in system_payload["policies"]), f"{system} split contains another system")

    report = {
        "schema_version": "1.0",
        "validator": "validate_formula_inventory.py",
        "result": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "counts": payload["counts"],
        "scope_note_zh": "验证只证明转录制品内部一致、目录存在和冲突标记完整，不证明论文公式正确，也不证明当前固件满足性质。",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
