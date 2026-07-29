#!/usr/bin/env python3
"""Validate property catalogs and retained Milestone-4 evidence ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
EXPECTED = {
    "ArduPilot": ("8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e", 7, 19003),
    "PX4": ("d6f12ad1c4f70ad3230afd7d86e971421e02fef4", 6, 17148),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_source(prop: dict, src: dict) -> None:
    path = ROOT / src["path_or_url"]
    if not path.is_file():
        fail(f"{prop['property_id']}: missing source {src['path_or_url']}")
    if sha256_file(path) != src["sha256"]:
        fail(f"{prop['property_id']}: source hash drift {src['path_or_url']}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    loc = src["locator"]
    start, end = loc["line_start"], loc["line_end"]
    if start is None or end is None or start < 1 or end < start or end > len(lines):
        fail(f"{prop['property_id']}: invalid source locator {src['source_id']}")
    quote = "\n".join(lines[start - 1 : end]).strip()
    if quote != src["exact_quote"]:
        fail(f"{prop['property_id']}: exact quote drift {src['source_id']}")


def check_git(path: Path, expected: str) -> None:
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if actual != expected:
        fail(f"HEAD drift {path}: {actual} != {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=(4, 5, 6, 7), default=7)
    args = parser.parse_args()
    schema = json.loads((BENCHMARK / "schemas" / "property.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    all_ids: set[str] = set()
    total_properties = 0
    total_aps = 0
    total_times = 0
    total_instances = 0
    concrete_properties = 0
    instance_statuses: Counter[str] = Counter()
    runtime_evidence_path = BENCHMARK / "extraction_runs" / "milestone6" / "runtime_evidence.json"
    runtime_rows: dict[tuple[str, str], dict] = {}
    runtime_captures: dict[str, dict] = {}
    runtime_evidence_rel = str(runtime_evidence_path.relative_to(ROOT))
    runtime_evidence_sha = None
    if args.stage >= 6:
        runtime_evidence = json.loads(runtime_evidence_path.read_text(encoding="utf-8"))
        if runtime_evidence["implementation_satisfaction"] != "NOT_ASSESSED":
            fail("runtime evidence contains a conformance conclusion")
        runtime_captures = {row["capture_id"]: row for row in runtime_evidence["captures"]}
        if len(runtime_captures) != 4 or any(row["runtime_status"] != "COMPLETE" for row in runtime_captures.values()):
            fail("Milestone-6 requires four COMPLETE captures")
        for row in runtime_evidence["property_parameters"]:
            key = (row["property_id"], row["capture_id"])
            if key in runtime_rows:
                fail(f"duplicate runtime property/profile row {key}")
            runtime_rows[key] = row
        if len(runtime_rows) != 15:
            fail(f"expected 15 runtime property/profile rows, found {len(runtime_rows)}")
        runtime_evidence_sha = sha256_file(runtime_evidence_path)
    monitor_rows: dict[str, dict] = {}
    independent_rows: dict[str, dict] = {}
    monitor_path = BENCHMARK / "extraction_runs" / "milestone7" / "monitor_validation" / "monitor_validation.json"
    independent_path = BENCHMARK / "extraction_runs" / "milestone7" / "independent_review.json"
    monitor_sha = None
    independent_sha = None
    if args.stage >= 7:
        monitor_doc = json.loads(monitor_path.read_text(encoding="utf-8"))
        independent_doc = json.loads(independent_path.read_text(encoding="utf-8"))
        if monitor_doc["scope"]["implementation_satisfaction_assessed"] is not False:
            fail("Milestone-7 monitor artifact claims implementation assessment")
        reviewer = independent_doc["reviewer"]
        if reviewer["is_human"] or reviewer["acceptance_claimed"] or reviewer["decision"] != "NOT_PERFORMED":
            fail("independent automated audit was misrepresented as human acceptance")
        monitor_rows = {row["property_id"]: row for row in monitor_doc["properties"]}
        independent_rows = {row["property_id"]: row for row in independent_doc["properties"]}
        if len(monitor_rows) != 8 or len(independent_rows) != 13:
            fail("Milestone-7 monitor/review property count mismatch")
        monitor_sha = sha256_file(monitor_path)
        independent_sha = sha256_file(independent_path)
    for system, (commit, expected_properties, _) in EXPECTED.items():
        directory = BENCHMARK / system
        catalog = json.loads((directory / "property_catalog.json").read_text(encoding="utf-8"))
        if catalog["firmware_commit"] != commit or catalog["system"] != system:
            fail(f"{system}: catalog identity mismatch")
        if len(catalog["properties"]) != expected_properties:
            fail(f"{system}: expected {expected_properties} properties, found {len(catalog['properties'])}")
        expected_counts = dict(sorted(Counter(p["status"] for p in catalog["properties"]).items()))
        if catalog["counts"] != expected_counts:
            fail(f"{system}: status count mismatch")
        for prop in catalog["properties"]:
            errors = sorted(validator.iter_errors(prop), key=lambda e: list(e.absolute_path))
            if errors:
                detail = "; ".join(f"{'/'.join(map(str,e.absolute_path))}: {e.message}" for e in errors[:10])
                fail(f"{prop.get('property_id')}: schema failure: {detail}")
            pid = prop["property_id"]
            if pid in all_ids:
                fail(f"duplicate property id {pid}")
            all_ids.add(pid)
            if prop["implementation_satisfaction"] != "NOT_ASSESSED":
                fail(f"{pid}: implementation satisfaction changed")
            if args.stage < 7 and prop["mitl"]["monitor_syntax"] is not None:
                fail(f"{pid}: monitor syntax present before Milestone-7 parser validation")
            if args.stage < 6 and (prop["mitl"]["concrete"] is not None or prop["mitl"].get("concrete_instances")):
                fail(f"{pid}: concrete runtime evidence present before Milestone 6")
            formula = prop["mitl"]["symbolic"] or ""
            if "EPS" in formula.upper() or "EPSILON" in formula.upper():
                fail(f"{pid}: invented epsilon placeholder remains")
            if prop["review"]["decision"] != "PENDING":
                fail(f"{pid}: property prematurely reviewed/accepted")
            for src in prop["sources"]:
                validate_source(prop, src)
            for tc in prop["time_contracts"]:
                total_times += 1
                if tc["source_type"] == "RUNTIME_PARAMETER" and args.stage < 6:
                    runtime_operands = [x for x in tc["operands"] if x["name"] == "runtime_value"]
                    if len(runtime_operands) != 1 or runtime_operands[0]["value"] is not None:
                        fail(f"{pid}: runtime parameter was fabricated")
                uncertainty = (tc["measurement_uncertainty"] or "").upper()
                if "INCONCLUSIVE" not in uncertainty:
                    fail(f"{pid}: boundary uncertainty policy missing")
            for item in prop["atomic_propositions"]:
                total_aps += 1
                if args.stage == 4:
                    if item["source_bindings"] or item["mavlink_observations"]:
                        fail(f"{pid}: Milestone-4 AP unexpectedly contains later-stage bindings")
                    if item["status"] != "NEEDS_BINDING":
                        fail(f"{pid}: AP prematurely marked bound")
                else:
                    if not item["source_bindings"]:
                        fail(f"{pid}: Milestone-5 AP lacks current-source bindings")
                    if item["status"] not in {"BOUND", "PARTIALLY_BOUND"}:
                        fail(f"{pid}: invalid Milestone-5 AP status {item['status']}")
            if args.stage >= 6:
                snapshot = prop["system_scope"]["configuration_snapshot"]
                if (
                    snapshot["status"] != "CAPTURED"
                    or snapshot["path"] != runtime_evidence_rel
                    or snapshot["sha256"] != runtime_evidence_sha
                ):
                    fail(f"{pid}: runtime configuration snapshot identity mismatch")
                instances = prop["mitl"].get("concrete_instances", [])
                expected_for_property = {
                    key: row for key, row in runtime_rows.items() if key[0] == pid
                }
                if len(instances) != len(expected_for_property):
                    fail(f"{pid}: runtime instance count {len(instances)} != {len(expected_for_property)}")
                seen_capture_ids: set[str] = set()
                for instance in instances:
                    capture_id = instance["capture_id"]
                    if capture_id in seen_capture_ids:
                        fail(f"{pid}: duplicate concrete instance {capture_id}")
                    seen_capture_ids.add(capture_id)
                    row = expected_for_property.get((pid, capture_id))
                    if row is None:
                        fail(f"{pid}: unexpected concrete instance {capture_id}")
                    capture = runtime_captures[capture_id]
                    expected_profile = f"{capture['system']}/{capture['vehicle']} — {capture['profile']}"
                    if instance["profile"] != expected_profile:
                        fail(f"{pid}/{capture_id}: profile identity mismatch")
                    for key in (
                        "parameter_id", "raw_unit", "source_path", "source_sha256",
                        "source_param_index", "source_param_count",
                    ):
                        expected_key = "unit" if key == "raw_unit" else key
                        if instance[key] != row[expected_key]:
                            fail(f"{pid}/{capture_id}: {key} drift")
                    if not math.isclose(float(instance["raw_value"]), float(row["value"]), rel_tol=0.0, abs_tol=0.0):
                        fail(f"{pid}/{capture_id}: raw value drift")
                    expected_normalized = float(row["value"]) / 1000.0 if row["unit"] == "ms" else float(row["value"])
                    if not math.isclose(float(instance["normalized_value"]), expected_normalized, rel_tol=0.0, abs_tol=0.0):
                        fail(f"{pid}/{capture_id}: time normalization drift")
                    source_path = ROOT / instance["source_path"]
                    if not source_path.is_file() or sha256_file(source_path) != instance["source_sha256"]:
                        fail(f"{pid}/{capture_id}: runtime parameter source missing/hash drift")
                    expected_disabled = row["status"] == "RUNTIME_OBSERVED_DISABLED_DOMAIN"
                    if expected_disabled:
                        if instance["status"] != "DISABLED_BY_RUNTIME_CONFIGURATION" or instance["formula"] is not None:
                            fail(f"{pid}/{capture_id}: disabled domain must not emit a concrete formula")
                    elif prop["mitl"]["symbolic"] is None:
                        if instance["status"] != "NOT_FORMALIZED" or instance["formula"] is not None:
                            fail(f"{pid}/{capture_id}: unformalized property emitted a formula")
                    elif args.stage >= 7:
                        if prop["mitl"]["concrete"] is not None:
                            expected_instance_status = (
                                "INSTANTIATED_FORMULA_VALIDATED"
                                if prop["mitl"]["status"] == "MONITOR_VALIDATED"
                                else "INSTANTIATED_UNVALIDATED"
                            )
                            if instance["status"] != expected_instance_status or instance["formula"] is None:
                                fail(f"{pid}/{capture_id}: monitored candidate instance status drift")
                            if "尚未运行 MITL parser" in instance["notes"] or "Stage 7" not in instance["notes"]:
                                fail(f"{pid}/{capture_id}: stale Stage-6 monitor note survived Stage 7")
                        elif instance["formula"] is not None:
                            if instance["status"] != "NEEDS_CONTEXT":
                                fail(f"{pid}/{capture_id}: context-open instance status drift")
                        else:
                            fail(f"{pid}/{capture_id}: unexpected active runtime instance without formula")
                    elif prop["status"] == "NEEDS_CONTEXT" or prop["mitl"]["status"] == "NEEDS_CONTEXT":
                        if instance["status"] != "NEEDS_CONTEXT":
                            fail(f"{pid}/{capture_id}: context-open instance status drift")
                    else:
                        if instance["status"] != "INSTANTIATED_UNVALIDATED" or instance["formula"] is None:
                            fail(f"{pid}/{capture_id}: active instance missing unvalidated formula")
                    instance_statuses[instance["status"]] += 1
                    total_instances += 1
                active_statuses = {"INSTANTIATED_UNVALIDATED", "INSTANTIATED_FORMULA_VALIDATED"}
                active_formulas = {
                    row["formula"] for row in instances
                    if row["status"] in active_statuses and row["formula"] is not None
                }
                should_have_single = len(active_formulas) == 1 and all(
                    row["status"] in active_statuses for row in instances
                )
                if should_have_single:
                    if args.stage >= 7:
                        monitor_overall = monitor_rows[pid]["overall_status"]
                        expected_mitl_status = {
                            "PASS": "MONITOR_VALIDATED",
                            "FAILED": "MONITOR_VALIDATION_FAILED",
                            "UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME": "UNSUPPORTED_BY_MONITOR",
                        }.get(monitor_overall)
                        if expected_mitl_status is None:
                            fail(f"{pid}: unknown monitor overall status {monitor_overall}")
                    else:
                        expected_mitl_status = "CONCRETE_UNVALIDATED"
                    if (
                        prop["mitl"]["concrete"] != next(iter(active_formulas))
                        or prop["mitl"]["status"] != expected_mitl_status
                    ):
                        fail(f"{pid}: single concrete formula/status mismatch")
                    concrete_properties += 1
                elif prop["mitl"]["concrete"] is not None:
                    fail(f"{pid}: emitted a single concrete formula across disabled/context-specific instances")
                tc = prop["time_contracts"][0]
                runtime_operands = [x for x in tc["operands"] if x["name"] == "runtime_value"]
                if len(runtime_operands) != 1 or runtime_operands[0]["value"] is None or tc["status"] != "RESOLVED":
                    fail(f"{pid}: runtime TimeContract provenance is not resolved")
                expected_source = f"{runtime_evidence_rel}#property_parameters/{pid}"
                if runtime_operands[0]["source_id"] != expected_source:
                    fail(f"{pid}: runtime operand source drift")
                if args.stage < 7 and prop["validation"]["parser"]["status"] != "NOT_RUN":
                    fail(f"{pid}: parser/monitor gate was claimed before Milestone 7")
            if args.stage >= 7:
                audit = independent_rows.get(pid)
                if audit is None or prop["status"] != audit["audit_status"]:
                    fail(f"{pid}: independent-review rollback status mismatch")
                if prop["review"]["decision"] != "PENDING" or prop["review"]["reviewer"] is not None:
                    fail(f"{pid}: automated audit was represented as a human decision")
                if prop["validation"]["independent_review"]["status"] != "INCONCLUSIVE":
                    fail(f"{pid}: independent audit blockers were not preserved")
                if sha256_file(independent_path) != independent_sha:
                    fail("independent-review artifact drifted during validation")
                monitor = monitor_rows.get(pid)
                if monitor is None:
                    if prop["mitl"]["monitor_syntax"] is not None or prop["mitl"]["monitor_contract"] is not None:
                        fail(f"{pid}: monitor encoding fabricated without concrete formula")
                    if any(prop["examples"][key] for key in prop["examples"]):
                        fail(f"{pid}: monitor traces fabricated without concrete formula")
                    if prop["validation"]["monitor"]["status"] != "NOT_APPLICABLE":
                        fail(f"{pid}: non-concrete monitor gate must be NOT_APPLICABLE")
                else:
                    if monitor["source_formula"] != prop["mitl"]["concrete"]:
                        fail(f"{pid}: monitor source formula mismatch")
                    if prop["mitl"]["monitor_syntax"] != monitor["monitor_encoding"]["formula"]:
                        fail(f"{pid}: monitor syntax mismatch")
                    contract = prop["mitl"]["monitor_contract"]
                    if (
                        contract is None
                        or contract["monitor_tick_unit"] != "ms"
                        or contract["ticks_per_source_unit"] != 1000
                        or contract["interval_openness_preserved"] is not True
                        or contract["artifact_path"] != str(monitor_path.relative_to(ROOT))
                        or contract["artifact_sha256"] != monitor_sha
                    ):
                        fail(f"{pid}: monitor contract mismatch")
                    if prop["validation"]["parser"]["status"] != "PASS":
                        fail(f"{pid}: transformed monitor parser gate did not pass")
                    if prop["validation"]["satisfiable"]["status"] != "PASS":
                        fail(f"{pid}: satisfiable gate did not pass")
                    if prop["validation"]["non_tautology"]["status"] != "PASS":
                        fail(f"{pid}: non-tautology gate did not pass")
                    if prop["validation"]["non_vacuity"]["status"] != "PASS":
                        fail(f"{pid}: reference-oracle non-vacuity gate did not pass")
                    expected_monitor_gate = {
                        "PASS": "PASS",
                        "FAILED": "FAIL",
                        "UNSUPPORTED_TAMONITOR_INFINITE_RUNTIME": "INCONCLUSIVE",
                    }.get(monitor["overall_status"])
                    if expected_monitor_gate is None or prop["validation"]["monitor"]["status"] != expected_monitor_gate:
                        fail(f"{pid}: TAMonitor property result was hidden or misclassified")
                    trace_by_id = {row["trace_id"]: row for row in monitor["traces"]}
                    seen_trace_ids: set[str] = set()
                    for category, refs in prop["examples"].items():
                        if category in {"wrong_exception", "wrong_correlation"} and refs:
                            fail(f"{pid}: unresolved {category} trace was fabricated")
                        for ref in refs:
                            trace = trace_by_id.get(ref["trace_id"])
                            if trace is None:
                                fail(f"{pid}: unknown trace reference {ref['trace_id']}")
                            seen_trace_ids.add(ref["trace_id"])
                            path = ROOT / ref["path"]
                            if not path.is_file() or sha256_file(path) != ref["sha256"]:
                                fail(f"{pid}: trace reference path/hash drift {ref['trace_id']}")
                    expected_referenced = {
                        row["trace_id"] for row in monitor["traces"]
                        if row["case_kind"] != "vacuous_trigger_control"
                    }
                    if seen_trace_ids != expected_referenced:
                        fail(f"{pid}: trace reference coverage mismatch")
            json_path = directory / "properties" / f"{pid}.json"
            md_path = directory / "properties" / f"{pid}.md"
            if not json_path.is_file() or not md_path.is_file():
                fail(f"{pid}: missing per-property files")
            if json.loads(json_path.read_text(encoding="utf-8")) != prop:
                fail(f"{pid}: catalog/per-property JSON mismatch")
        total_properties += len(catalog["properties"])

    summary = json.loads((BENCHMARK / "extraction_runs" / "milestone4" / "adjudication_summary.json").read_text(encoding="utf-8"))
    for system, (_, _, expected_candidates) in EXPECTED.items():
        ledger = BENCHMARK / "extraction_runs" / "milestone4" / f"{system}_adjudication_ledger.jsonl"
        counts: Counter[str] = Counter()
        rows = 0
        with ledger.open("r", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                rows += 1
                counts[row["decision"]] += 1
                if row["implementation_satisfaction"] != "NOT_ASSESSED":
                    fail(f"{system}: adjudication row changed implementation status")
        if rows != expected_candidates:
            fail(f"{system}: ledger row count {rows} != {expected_candidates}")
        if dict(sorted(counts.items())) != summary["systems"][system]["counts"]:
            fail(f"{system}: adjudication summary mismatch")

    check_git(ROOT / "baseline" / "ardupilot", EXPECTED["ArduPilot"][0])
    check_git(ROOT / "baseline" / "px4", EXPECTED["PX4"][0])
    if args.stage >= 6:
        expected_statuses = Counter({
            "INSTANTIATED_UNVALIDATED": 2 if args.stage >= 7 else 10,
            "DISABLED_BY_RUNTIME_CONFIGURATION": 2,
            "NEEDS_CONTEXT": 2,
            "NOT_FORMALIZED": 1,
        })
        if args.stage >= 7:
            expected_statuses["INSTANTIATED_FORMULA_VALIDATED"] = 8
        if total_instances != 15 or concrete_properties != 8 or instance_statuses != expected_statuses:
            fail(
                f"stage-6 aggregate mismatch: instances={total_instances}, concrete={concrete_properties}, "
                f"statuses={dict(instance_statuses)}"
            )
        rtl = next(
            row
            for system in EXPECTED
            for row in json.loads(
                (BENCHMARK / system / "property_catalog.json").read_text(encoding="utf-8")
            )["properties"]
            if row["property_id"] == "ARD-COPTER-RTL-003"
        )
        rtl_instance = rtl["mitl"]["concrete_instances"][0]
        if (
            rtl_instance["raw_value"] != 5000
            or rtl_instance["raw_unit"] != "ms"
            or rtl_instance["normalized_value"] != 5.0
        ):
            fail("RTL_LOIT_TIME 5000 ms was not normalized exactly to 5 s")
    if args.stage >= 7:
        expected_property_statuses = {
            "ArduPilot": Counter({"NEEDS_CONTEXT": 6, "CANDIDATE": 1}),
            "PX4": Counter({"NEEDS_CONTEXT": 6}),
        }
        for system in EXPECTED:
            catalog = json.loads((BENCHMARK / system / "property_catalog.json").read_text(encoding="utf-8"))
            actual = Counter(row["status"] for row in catalog["properties"])
            if actual != expected_property_statuses[system]:
                fail(f"{system}: final independent-review status distribution mismatch {dict(actual)}")
        if sha256_file(monitor_path) != monitor_sha:
            fail("monitor validation artifact drifted during catalog validation")
    print(f"PASS: stage={args.stage} properties={total_properties} atomic_propositions={total_aps} time_contracts={total_times}")
    if args.stage >= 6:
        print(
            f"PASS: runtime concrete instances={total_instances}, single concrete properties={concrete_properties}, "
            f"statuses={dict(sorted(instance_statuses.items()))}"
        )
    if args.stage >= 7:
        print("PASS: stage-7 automated audit rollback=12 NEEDS_CONTEXT/1 CANDIDATE; monitor formulas=6 PASS/1 FAIL/1 UNSUPPORTED")
    print("PASS: source hashes/quotes, staged concrete rule, no epsilon, NOT_ASSESSED, and all adjudication rows verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
