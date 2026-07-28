#!/usr/bin/env python3
"""Fail-closed structural and semantic QA for generated protocol catalogs."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "protocols"
EXPECTED = {
    "coap", "mqtt", "tcp", "quic", "dns", "tls", "dtls", "ssh",
    "rtsp", "ftp", "smtp", "sip", "dicom", "modbus_tcp", "opc_ua",
    "dds_rtps", "can_uds",
}
REQUIRED_FILES = {
    "mitl_property_catalog.md", "mitl_property_catalog.csv",
    "mitl_property_catalog.json", "atomic_proposition_map.json",
    "atomic_proposition_map.yaml", "instrumentation_hooks.csv",
    "evidence_manifest.json", "evidence_manifest.yaml", "excluded_properties.md",
    "formula_validation_summary.csv", "rejected_after_validation.json",
}


def formula_atomic_propositions(formula: str) -> set[str]:
    reserved = {"G", "F", "U", "R", "S", "X", "true", "false", "infty"}
    return {
        token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula)
        if token not in reserved
    }


def mathematical_form(formula: str) -> str:
    return re.sub(r"\bG\*", "G", formula)


def outer_trigger_ap(formula: str) -> str | None:
    match = re.match(r"^\s*G\*\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*->", formula)
    return match.group(1) if match else None


def urls_in(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from urls_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from urls_in(child)
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        yield value


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    errors: list[str] = []
    root_required = {
        "all_protocol_properties.json", "all_protocol_properties.csv",
        "protocol_summary.csv", "protocol_catalog_index.md",
        "extraction_completeness_report.md", "independent_audit_summary.md",
        "instrumentation_hooks.csv", "source_verification_summary.csv",
        "formula_validation_summary.csv", "evidence_manifest.json",
        "evidence_manifest.yaml", "evidence_link_audit.json", "evidence_link_audit.csv",
        "reproducibility_manifest.json", "load_errors.json",
    }
    missing_root = sorted(name for name in root_required if not (OUT / name).exists())
    if missing_root:
        errors.append(f"missing root artifacts: {missing_root}")
    actual = {p.name for p in OUT.iterdir() if p.is_dir()}
    if actual != EXPECTED:
        errors.append(f"protocol directory mismatch: missing={sorted(EXPECTED-actual)} extra={sorted(actual-EXPECTED)}")

    all_ids: set[str] = set()
    canonical_ap_definitions: dict[tuple[str, str], tuple[str, str]] = {}
    per_protocol_records_by_id: dict[str, dict] = {}
    total = 0
    expected_hook_rows = 0
    expected_hook_pairs: set[tuple[str, str, str]] = set()
    expected_protocol_counts: dict[str, int] = {}
    for slug in sorted(EXPECTED):
        pdir = OUT / slug
        missing = sorted(name for name in REQUIRED_FILES if not (pdir / name).exists())
        if missing:
            errors.append(f"{slug}: missing files {missing}")
            continue
        catalog = load(pdir / "mitl_property_catalog.json")
        rejected = load(pdir / "rejected_after_validation.json")
        ap_map = load(pdir / "atomic_proposition_map.json")["atomic_propositions"]
        ap_map_yaml = load(pdir / "atomic_proposition_map.yaml")["atomic_propositions"]
        evidence = load(pdir / "evidence_manifest.json")
        evidence_yaml = load(pdir / "evidence_manifest.yaml")
        if ap_map_yaml != ap_map:
            errors.append(f"{slug}: JSON/YAML AP map mismatch")
        if evidence_yaml != evidence:
            errors.append(f"{slug}: JSON/YAML evidence manifest mismatch")
        screening_records = evidence.get("screening_records", [])
        if not screening_records:
            errors.append(f"{slug}: no screening evidence records")
        for record_item in screening_records:
            if record_item.get("read_error"):
                errors.append(f"{slug}: screening evidence read error")
                continue
            record = record_item.get("record", {})
            if not isinstance(record, dict) or not record:
                errors.append(f"{slug}: empty/invalid screening evidence")
                continue
            status = str(record.get("status", "")).upper()
            if status:
                completed = bool(re.fullmatch(
                    r"(?:COMPLETE(?:_WITH_[A-Z0-9_]+)?|FIXED_AFTER_[A-Z0-9_]*COMPLETE|"
                    r"SCREENED_NO_ADMITTED_MITL_AFTER_[A-Z0-9_]+)",
                    status,
                ))
                if not completed:
                    errors.append(f"{slug}: incomplete screening evidence status {status}")
            elif record_item.get("file") != "evidence_manifest.yaml":
                errors.append(f"{slug}: screening evidence missing completion status")
        with (pdir / "instrumentation_hooks.csv").open(encoding="utf-8-sig", newline="") as handle:
            hook_rows = list(csv.DictReader(handle))
        with (pdir / "mitl_property_catalog.csv").open(encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        if len(csv_rows) != len(catalog):
            errors.append(f"{slug}: CSV/JSON count mismatch {len(csv_rows)} != {len(catalog)}")
        catalog_ids = [str(item.get("id", "")) for item in catalog]
        if [str(row.get("id", "")) for row in csv_rows] != catalog_ids:
            errors.append(f"{slug}: CSV/JSON property ID/order mismatch")
        for record, row in zip(catalog, csv_rows):
            for field in ("protocol", "standard_section", "mightyppl_formula", "source_commit",
                          "source_path", "source_lines", "validation_status"):
                if str(row.get(field, "")) != str(record.get(field, "")):
                    errors.append(f"{slug}/{record.get('id')}: CSV/JSON mismatch in {field}")
        rejected_ids = {str(item.get("id", "")) for item in rejected}
        if rejected_ids & set(catalog_ids):
            errors.append(f"{slug}: an ID appears in both admitted and rejected catalogs")
        expected_protocol_counts[slug] = len(catalog)
        if not catalog and not (rejected or evidence.get("screening_records") or
                                (pdir / "excluded_properties.md").stat().st_size > 80):
            errors.append(f"{slug}: zero admitted properties without documented screening/exclusion")
        for prop in catalog:
            pid = str(prop.get("id", ""))
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", pid) or pid in {".", ".."}:
                errors.append(f"{slug}: unsafe property id {pid!r}")
            if pid in all_ids:
                errors.append(f"duplicate property id {pid}")
            all_ids.add(pid)
            per_protocol_records_by_id[pid] = prop
            total += 1
            if prop.get("validation_status") != "PASS":
                errors.append(f"{pid}: validation_status != PASS")
            audit_status = str(prop.get("independent_audit_status", "")).upper()
            accepted_audit_status = (
                audit_status in {"APPROVE", "FIXED_AFTER_AUDIT", "PREVIOUSLY_ROOT_REVIEWED"}
                or audit_status.startswith("APPROVE_")
                or audit_status.startswith("ROOT_REVIEWED")
            )
            if not accepted_audit_status:
                errors.append(f"{pid}: unknown/unapproved audit status {audit_status}")
            if audit_status in {"REJECT", "REJECT_OR_FIX", "FIX", "NEEDS_FIX"}:
                errors.append(f"{pid}: independently rejected property was admitted")
            if not str(prop.get("monitor_instantiation", "")).strip():
                errors.append(f"{pid}: missing per-obligation monitor-instantiation contract")
            if not all(prop.get(key) is True for key in (
                    "source_file_verified", "source_line_verified",
                    "source_symbol_verified", "standard_url_reachable")):
                errors.append(f"{pid}: evidence verification flag is not true")
            auxiliary_mappings = prop.get("auxiliary_source_mappings", [])
            legacy_source_urls = set()
            for key, value in prop.items():
                if key != "source_url" and (key.endswith("_source_url") or key.endswith("_source_urls")):
                    legacy_source_urls.update(urls_in(value))
            structured_source_urls = {str(prop.get("source_url", ""))}
            structured_source_urls.update(str(item.get("url", "")) for item in auxiliary_mappings)
            if legacy_source_urls - structured_source_urls:
                errors.append(f"{pid}: unstructured source URLs remain")
            auxiliary_results = prop.get("auxiliary_source_verification", [])
            if auxiliary_mappings:
                if len(auxiliary_results) != len(auxiliary_mappings):
                    errors.append(f"{pid}: auxiliary-source verification count mismatch")
                for result in auxiliary_results:
                    if not all(result.get(key) is True for key in (
                            "source_file_verified", "source_line_verified", "source_symbol_verified")):
                        errors.append(f"{pid}: auxiliary source verification failed")
            if not re.fullmatch(r"[0-9a-f]{40}", str(prop.get("source_commit", "")), re.I):
                errors.append(f"{pid}: source commit is not 40 hex")
            source_url = str(prop.get("source_url", ""))
            if str(prop.get("source_commit", "")) not in source_url:
                errors.append(f"{pid}: source URL does not contain fixed commit")
            if str(prop.get("source_path", "")) not in source_url:
                errors.append(f"{pid}: source URL does not contain source path")
            formula = str(prop.get("mightyppl_formula", ""))
            aps = [str(ap) for ap in prop.get("atomic_propositions", [])]
            if len(set(aps)) != len(aps):
                errors.append(f"{pid}: duplicate declared AP")
            if formula_atomic_propositions(formula) != set(aps):
                errors.append(f"{pid}: formula/declaration AP-set mismatch")
            primary_source_aps = prop.get("primary_source_atomic_propositions", [])
            mapped_aps = set(primary_source_aps)
            for mapping in auxiliary_mappings:
                mapped_aps.update(mapping.get("atomic_propositions", []))
            if mapped_aps != set(aps):
                errors.append(f"{pid}: AP/source-mapping coverage mismatch")
            if (re.sub(r"\s+", "", str(prop.get("mathematical_mitl", ""))) !=
                    re.sub(r"\s+", "", mathematical_form(formula))):
                errors.append(f"{pid}: mathematical/executable formula mismatch")
            if any(a == b for a, b in re.findall(r"[\[(]\s*(\d+)\s*,\s*(\d+)\s*[\])]", formula)):
                errors.append(f"{pid}: punctual singleton interval")
            if "G*" in str(prop.get("mathematical_mitl", "")):
                errors.append(f"{pid}: mathematical MITL field contains MightyPPL weak G* notation")
            if "weak finite-word G*" not in str(prop.get("pointwise_semantics", "")):
                errors.append(f"{pid}: missing explicit mathematical/tool finite-semantics distinction")
            expected_hook_rows += len(aps)
            expected_hook_pairs.update((slug, pid, ap) for ap in aps)
            definitions = prop.get("ap_definitions", {})
            if any(not str(definitions.get(ap, "")).strip() for ap in aps):
                errors.append(f"{pid}: missing AP definition")
            if any(len(str(definitions.get(ap, "")).strip()) < 12 or
                   str(definitions.get(ap, "")).strip().lower() == ap.replace("_", " ").lower()
                   for ap in aps):
                errors.append(f"{pid}: vague AP definition")
            for ap in aps:
                canonical_definition = re.sub(r"\s+", " ", str(definitions.get(ap, ""))).strip()
                definition_key = (slug, ap)
                if definition_key in canonical_ap_definitions:
                    prior_definition, prior_pid = canonical_ap_definitions[definition_key]
                    if prior_definition != canonical_definition:
                        errors.append(f"{pid}/{ap}: definition conflicts with {prior_pid}")
                else:
                    canonical_ap_definitions[definition_key] = (canonical_definition, pid)
                entry = ap_map.get(ap, {})
                mappings = [x for x in entry.get("source_mappings", []) if x.get("property_id") == pid]
                if not mappings:
                    errors.append(f"{pid}/{ap}: no reverse source mapping")
                for mapping in mappings:
                    if ap not in mapping.get("atomic_propositions", []):
                        errors.append(f"{pid}/{ap}: unrelated source mapping attached")
                    if not all(mapping.get(key) is True for key in (
                            "source_file_verified", "source_line_verified", "source_symbol_verified")):
                        errors.append(f"{pid}/{ap}: unverified source mapping attached")
                hook_matches = [row for row in hook_rows
                                if row.get("property_id") == pid and row.get("atomic_proposition") == ap]
                if len(hook_matches) != 1 or not hook_matches[0].get("event_predicate"):
                    errors.append(f"{pid}/{ap}: missing or duplicate instrumentation-hook row")
                elif hook_matches:
                    try:
                        hook_mappings = json.loads(hook_matches[0].get("source_mappings", "[]"))
                    except json.JSONDecodeError:
                        hook_mappings = []
                    if not hook_mappings or any(ap not in item.get("atomic_propositions", [])
                                                for item in hook_mappings):
                        errors.append(f"{pid}/{ap}: hook row lacks AP-specific mappings")
            vpath = pdir / "validation" / pid / "validation_result.json"
            validation = load(vpath) if vpath.exists() else {}
            if validation.get("status") != "PASS":
                errors.append(f"{pid}: missing/passing validation result")
            if validation.get("all_commands_ok") is not True:
                errors.append(f"{pid}: a TAMonitor validation command failed")
            if validation.get("ap_order_ok") is not True:
                errors.append(f"{pid}: TAMonitor proposition order/set mismatch")
            for name, result in validation.get("additional_negative_results", {}).items():
                if result.get("symbolic") != "NEGATIVE" or result.get("concrete") != "NEGATIVE":
                    errors.append(f"{pid}/{name}: additional negative did not produce NEGATIVE in both modes")
            for name, result in validation.get("additional_positive_results", {}).items():
                if result.get("symbolic") != "POSITIVE" or result.get("concrete") != "POSITIVE":
                    errors.append(f"{pid}/{name}: additional positive did not produce POSITIVE in both modes")
            extra_negatives = prop.get("additional_negative_traces", {})
            extra_positives = prop.get("additional_positive_traces", {})
            if set(validation.get("additional_negative_results", {})) != set(extra_negatives):
                errors.append(f"{pid}: additional-negative validation inventory mismatch")
            if set(validation.get("additional_positive_results", {})) != set(extra_positives):
                errors.append(f"{pid}: additional-positive validation inventory mismatch")
            for kind, traces in (("negative", extra_negatives), ("positive", extra_positives)):
                for name in traces:
                    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", str(name)):
                        errors.append(f"{pid}: unsafe additional-{kind} name {name!r}")
            trigger = outer_trigger_ap(formula)
            if trigger is None:
                errors.append(f"{pid}: unsupported outer trigger shape")
            else:
                eventual_uppers = [
                    int(value) for value in re.findall(
                        r"F\s*[\[(]\s*\d+\s*,\s*(\d+)\s*[\])]", formula
                    )
                ]
                if eventual_uppers:
                    expected_late = [
                        {"time": 0, "props": [trigger]},
                        {"time": max(eventual_uppers) + 1, "props": []},
                    ]
                    if extra_negatives.get("negative_late_or_missing") != expected_late:
                        errors.append(f"{pid}: bounded eventual late/missing trace is not canonical")
                traces = {
                    "positive": prop.get("positive_trace", []),
                    "negative": prop.get("negative_trace", []),
                    **{f"positive-extra:{name}": trace for name, trace in extra_positives.items()},
                    **{f"extra:{name}": trace for name, trace in extra_negatives.items()},
                }
                for trace_name, trace in traces.items():
                    count = sum(trigger in event.get("props", []) for event in trace)
                    if count != 1:
                        errors.append(f"{pid}/{trace_name}: trigger {trigger} count {count}, expected 1")
                    has_equal_positions = any(
                        trace[index].get("time") == trace[index + 1].get("time")
                        for index in range(len(trace) - 1)
                    )
                    if has_equal_positions and prop.get("allows_equal_timestamp_microsteps") is not True:
                        errors.append(f"{pid}/{trace_name}: undeclared equal-timestamp microstep")
                if prop.get("allows_equal_timestamp_microsteps") is True and len(
                        str(prop.get("microstep_ordering", "")).strip()) < 20:
                    errors.append(f"{pid}: missing/vague microstep ordering")

    aggregate = load(OUT / "all_protocol_properties.json")
    if len(aggregate) != total:
        errors.append(f"aggregate count mismatch {len(aggregate)} != {total}")
    aggregate_ids = [str(item.get("id", "")) for item in aggregate]
    if set(aggregate_ids) != all_ids or len(aggregate_ids) != len(all_ids):
        errors.append("aggregate property ID inventory differs from per-protocol catalogs")
    for record in aggregate:
        pid = str(record.get("id", ""))
        expected_record = per_protocol_records_by_id.get(pid)
        if expected_record is None:
            continue
        for field in ("protocol", "standard_section", "mightyppl_formula", "atomic_propositions",
                      "source_commit", "source_path", "source_lines", "validation_status"):
            if record.get(field) != expected_record.get(field):
                errors.append(f"aggregate/per-protocol mismatch for {pid}.{field}")
    with (OUT / "all_protocol_properties.csv").open(encoding="utf-8-sig", newline="") as handle:
        aggregate_csv = list(csv.DictReader(handle))
    if [str(row.get("id", "")) for row in aggregate_csv] != aggregate_ids:
        errors.append("aggregate CSV/JSON property ID/order mismatch")
    load_errors = load(OUT / "load_errors.json")
    if load_errors:
        errors.append(f"load errors present: {load_errors}")
    with (OUT / "instrumentation_hooks.csv").open(encoding="utf-8-sig", newline="") as handle:
        root_hooks = list(csv.DictReader(handle))
    if len(root_hooks) != expected_hook_rows:
        errors.append(f"root instrumentation hook count mismatch {len(root_hooks)} != {expected_hook_rows}")
    observed_hook_pairs = {
        (str(row.get("protocol", "")), str(row.get("property_id", "")), str(row.get("atomic_proposition", "")))
        for row in root_hooks
    }
    display_to_slug = {
        "CoAP": "coap", "MQTT": "mqtt", "TCP": "tcp", "QUIC": "quic", "DNS": "dns",
        "TLS": "tls", "DTLS": "dtls", "SSH": "ssh", "RTSP": "rtsp", "FTP": "ftp",
        "SMTP": "smtp", "SIP": "sip", "DICOM": "dicom", "Modbus/TCP": "modbus_tcp",
        "OPC UA": "opc_ua", "DDS/RTPS": "dds_rtps", "CAN/UDS": "can_uds",
    }
    normalized_hook_pairs = {
        (display_to_slug.get(protocol, protocol), pid, ap) for protocol, pid, ap in observed_hook_pairs
    }
    if normalized_hook_pairs != expected_hook_pairs:
        errors.append("root instrumentation hook ID/AP inventory mismatch")
    with (OUT / "formula_validation_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        root_validations = list(csv.DictReader(handle))
    if len(root_validations) != total:
        errors.append(f"root validation count mismatch {len(root_validations)} != {total}")
    if {str(row.get("id", "")) for row in root_validations} != set(aggregate_ids):
        errors.append("root validation property ID inventory mismatch")
    with (OUT / "protocol_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    observed_protocol_counts = {str(row.get("slug")): int(row.get("admitted", -1)) for row in summary_rows}
    if observed_protocol_counts != expected_protocol_counts:
        errors.append("protocol summary admitted-count mapping mismatch")
    if load(OUT / "evidence_manifest.json") != load(OUT / "evidence_manifest.yaml"):
        errors.append("root JSON/YAML evidence manifest mismatch")
    root_evidence = load(OUT / "evidence_manifest.json")
    if {str(item.get("property_id", "")) for item in root_evidence.get("sources", [])} != set(aggregate_ids):
        errors.append("root evidence property ID inventory mismatch")
    link_audit = load(OUT / "evidence_link_audit.json")
    if link_audit.get("failed_count") != 0:
        errors.append(f'evidence link audit has {link_audit.get("failed_count")} failures')
    audited_urls = {str(row.get("url")) for row in link_audit.get("rows", [])}
    aggregate_urls = set(urls_in(aggregate))
    missing_audit_urls = sorted(aggregate_urls - audited_urls)
    if missing_audit_urls:
        errors.append(f"admitted-property URLs missing from link audit: {missing_audit_urls}")
    reproducibility = load(OUT / "reproducibility_manifest.json")
    if reproducibility.get("admitted_property_count") != total:
        errors.append("reproducibility manifest admitted count mismatch")
    artifact_records = reproducibility.get("artifacts", [])
    recorded_artifacts = {str(item.get("path", "")) for item in artifact_records}
    actual_artifacts = {
        str(path.relative_to(OUT)) for path in OUT.rglob("*")
        if path.is_file() and path.name != "reproducibility_manifest.json"
    }
    if recorded_artifacts != actual_artifacts:
        errors.append(
            "reproducibility artifact inventory mismatch: missing="
            f"{sorted(actual_artifacts-recorded_artifacts)} extra={sorted(recorded_artifacts-actual_artifacts)}"
        )
    for artifact in artifact_records:
        artifact_path = OUT / str(artifact.get("path", ""))
        if not artifact_path.is_file():
            errors.append(f"reproducibility artifact missing: {artifact.get('path')}")
            continue
        observed = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if observed != artifact.get("sha256"):
            errors.append(f"reproducibility hash mismatch: {artifact.get('path')}")
    input_records = reproducibility.get("inputs", [])
    recorded_inputs = {str(item.get("path", "")) for item in input_records}
    input_candidates = {
        BASE / "generate_multi_protocol_catalog.py",
        BASE / "validate_multi_protocol_outputs.py",
        BASE / "verify_research_evidence.py",
        BASE / "mitl_property_catalog.json",
        BASE / "evidence_manifest.yaml",
    }
    staging = BASE / "_staging"
    if staging.exists():
        input_candidates.update(
            path for path in staging.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    actual_inputs = {str(path.relative_to(ROOT)) for path in input_candidates if path.is_file()}
    if recorded_inputs != actual_inputs:
        errors.append(
            "reproducibility input inventory mismatch: missing="
            f"{sorted(actual_inputs-recorded_inputs)} extra={sorted(recorded_inputs-actual_inputs)}"
        )
    for input_item in input_records:
        input_path = ROOT / str(input_item.get("path", ""))
        if not input_path.is_file():
            errors.append(f"reproducibility input missing: {input_item.get('path')}")
            continue
        observed = hashlib.sha256(input_path.read_bytes()).hexdigest()
        if observed != input_item.get("sha256"):
            errors.append(f"reproducibility input hash mismatch: {input_item.get('path')}")
    tamonitor = ROOT / str(reproducibility.get("tamonitor", ""))
    if not tamonitor.is_file():
        errors.append("recorded TAMonitor binary is missing")
    elif hashlib.sha256(tamonitor.read_bytes()).hexdigest() != reproducibility.get("tamonitor_sha256"):
        errors.append("TAMonitor SHA-256 mismatch")

    print(json.dumps({
        "status": "PASS" if not errors else "FAIL",
        "protocol_count": len(actual),
        "admitted_property_count": total,
        "error_count": len(errors),
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
