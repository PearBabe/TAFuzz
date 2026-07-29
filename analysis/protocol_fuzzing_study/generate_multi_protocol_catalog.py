#!/usr/bin/env python3
"""Normalize, source-check, machine-validate, and publish per-protocol catalogs.

Inputs are the isolated research proposals under _staging plus the already
validated SIP catalog. Outputs live under protocols/. No SUT is built or run.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
STAGING = BASE / "_staging"
OUT = BASE / "protocols"
TAMONITOR = ROOT / "tool/MightyPPL/build/TAMonitor"
ACCESS_DATE = "2026-07-13"

PROTOCOLS = [
    ("coap", "CoAP"),
    ("mqtt", "MQTT"),
    ("tcp", "TCP"),
    ("quic", "QUIC"),
    ("dns", "DNS"),
    ("tls", "TLS"),
    ("dtls", "DTLS"),
    ("ssh", "SSH"),
    ("rtsp", "RTSP"),
    ("ftp", "FTP"),
    ("smtp", "SMTP"),
    ("sip", "SIP"),
    ("dicom", "DICOM"),
    ("modbus_tcp", "Modbus/TCP"),
    ("opc_ua", "OPC UA"),
    ("dds_rtps", "DDS/RTPS"),
    ("can_uds", "CAN/UDS"),
]
DISPLAY_BY_SLUG = dict(PROTOCOLS)


# The original 20-property SIP catalog predates the per-AP definition field.
# Keep the audited catalog immutable and enrich it while normalizing into the
# multi-protocol output.  Each definition is an event predicate, not a label.
SIP_AP_DEFINITIONS = {
    "udp_invite_sent": "a client INVITE transaction on an unreliable transport completes its initial request send and enters Calling",
    "timer_a_fired": "the retransmit timer callback is dispatched as Timer A for the correlated INVITE client transaction",
    "invite_transaction_stopped": "the correlated INVITE client transaction leaves the retransmitting path after a response, transport error, or termination",
    "invite_retransmitted": "tsx_retransmit successfully passes the saved INVITE request to transport for the correlated client transaction",
    "timer_a_first_cycle_completed": "the first Timer A callback/retransmission completes and the next interval is rescheduled from T1 to 2*T1",
    "invite_client_calling_entered": "the INVITE client FSM enters Calling and its Timer B deadline is scheduled",
    "timer_b_fired": "the INVITE client timeout callback is dispatched as Timer B before a final response",
    "invite_final_response_received": "a 2xx--699 response matching the INVITE client transaction is accepted by its FSM",
    "invite_provisional_received": "a 1xx response matching the INVITE client transaction is accepted and INVITE retransmission is stopped",
    "udp_invite_client_completed": "an unreliable-transport INVITE client FSM enters Completed after a 300--699 response and schedules Timer D",
    "transaction_terminated": "the correlated SIP transaction FSM enters Terminated at the cited timer/state-transition hook",
    "udp_noninvite_sent": "a non-INVITE client transaction on an unreliable transport completes its initial request send and enters Trying",
    "timer_e_fired": "the retransmit timer callback is dispatched as Timer E for the correlated non-INVITE client transaction",
    "noninvite_final_response_received": "a 2xx--699 final response matching the non-INVITE client transaction is accepted by its FSM",
    "noninvite_retransmitted": "tsx_retransmit successfully passes the saved non-INVITE request to transport for the correlated transaction",
    "timer_e_first_cycle_completed": "the first Timer E callback/retransmission completes and its next interval is rescheduled to 2*T1",
    "noninvite_provisional_received": "a 1xx response matching the non-INVITE client transaction is accepted and Timer E is switched to T2",
    "noninvite_trying_entered": "the non-INVITE client FSM enters Trying and schedules the Timer F deadline",
    "timer_f_fired": "the non-INVITE client timeout callback is dispatched as Timer F before a final response",
    "udp_noninvite_client_completed": "an unreliable-transport non-INVITE client FSM enters Completed and schedules Timer K",
    "udp_invite_server_completed": "an unreliable-transport INVITE server FSM sends a 300--699 response, enters Completed, and schedules Timer G",
    "timer_g_fired": "the retransmit timer callback is dispatched as Timer G for the correlated INVITE server transaction",
    "ack_received": "an ACK satisfying SIP transaction matching rules is accepted by the correlated INVITE server transaction",
    "final_response_retransmitted": "the saved 300--699 final response is passed again to transport from the Timer G callback",
    "timer_g_first_cycle_completed": "the first Timer G callback/retransmission completes and the next interval is rescheduled to 2*T1",
    "invite_server_completed": "the INVITE server FSM enters Completed and schedules Timer H after a 300--699 response",
    "timer_h_fired": "the INVITE server timeout callback is dispatched as Timer H before a matching ACK",
    "udp_invite_server_confirmed": "an unreliable-transport INVITE server FSM accepts the matching ACK, enters Confirmed, and schedules Timer I",
    "udp_noninvite_server_completed": "an unreliable-transport non-INVITE server FSM enters Completed after sending a final response and schedules Timer J",
    "proxy_invite_forwarded": "a stateful proxy successfully forwards an INVITE downstream and starts or refreshes its Timer C supervision",
    "timer_c_fired": "the stateful proxy INVITE supervision callback is dispatched as Timer C",
}


def canonical_protocol(value: str) -> str | None:
    key = re.sub(r"[^a-z0-9]+", "", value.lower())
    aliases = {
        "coap": "coap", "mqtt": "mqtt", "tcp": "tcp", "quic": "quic",
        "dns": "dns", "tls": "tls", "dtls": "dtls", "ssh": "ssh",
        "rtsp": "rtsp", "ftp": "ftp", "smtp": "smtp", "sip": "sip",
        "dicom": "dicom", "modbus": "modbus_tcp", "modbustcp": "modbus_tcp",
        "opcua": "opc_ua", "dds": "dds_rtps", "rtps": "dds_rtps",
        "ddsrtps": "dds_rtps", "can": "can_uds", "uds": "can_uds",
        "canuds": "can_uds",
    }
    return aliases.get(key)


BASE_FIELDS = [
    "id", "protocol", "protocol_slug", "protocol_extension", "title", "category",
    "natural_language", "normative_strength", "standard", "standard_version",
    "standard_section", "standard_url", "standard_excerpt", "time_value_ms",
    "time_parameter", "time_source", "instantiation_basis", "mathematical_mitl",
    "mightyppl_formula", "interval_class", "pointwise_semantics",
    "finite_end_semantics", "atomic_propositions", "ap_definitions",
    "correlation_key", "projection_rule", "source_repository", "source_commit",
    "source_path", "source_symbol", "source_lines", "source_url",
    "primary_source_atomic_propositions",
    "auxiliary_source_mappings", "auxiliary_source_verification",
    "instrumentation_timing", "observability", "oracle_value", "triggerability",
    "confidence", "positive_trace", "negative_trace", "human_review_status",
    "additional_positive_traces", "additional_negative_traces", "monitor_instantiation",
    "allows_equal_timestamp_microsteps", "microstep_ordering",
    "independent_audit_status", "independent_audit_note",
    "sut_role", "benchmark_reachability", "scope", "review_question", "limitations", "standard_url_reachable",
    "source_file_verified", "source_line_verified", "source_symbol_verified",
    "source_verification_note",
]

VALIDATION_FIELDS = [
    "validation_build_ok", "validation_all_commands_ok", "validation_positive_symbolic",
    "validation_negative_symbolic", "validation_positive_concrete",
    "validation_negative_concrete", "validation_expected_oracle_ok",
    "validation_symbolic_concrete_consistent", "validation_additional_positive_results",
    "validation_additional_negative_results",
    "validation_ap_order", "validation_ap_order_ok",
    "validation_positive_locations", "validation_positive_edges",
    "validation_positive_clocks", "validation_negative_locations",
    "validation_negative_edges", "validation_negative_clocks",
    "validation_build_ms", "validation_monitor_ms_positive",
    "validation_monitor_ms_negative", "validation_status",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cooked = {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
            writer.writerow(cooked)


def normalize_trace(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError("trace must be a list")
    normalized = []
    for event in value:
        if not isinstance(event, dict):
            raise ValueError("trace event must be an object")
        time = int(event["time"])
        props = event.get("props", [])
        if isinstance(props, str):
            props = [x for x in re.split(r"[ ,]+", props.strip()) if x]
        normalized.append({"time": time, "props": [str(x) for x in props]})
    if not normalized or any(x["time"] < 0 for x in normalized):
        raise ValueError("trace must be non-empty with non-negative timestamps")
    if any(normalized[i]["time"] > normalized[i + 1]["time"] for i in range(len(normalized) - 1)):
        raise ValueError("trace timestamps must be nondecreasing")
    return normalized


def formula_atomic_propositions(formula: str) -> set[str]:
    """Return identifiers that are APs rather than MightyPPL syntax words."""
    reserved = {"G", "F", "U", "R", "S", "X", "true", "false", "infty"}
    return {
        token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula)
        if token not in reserved
    }


def mathematical_form(formula: str) -> str:
    """Translate only the documented MightyPPL weak-global spelling."""
    return re.sub(r"\bG\*", "G", formula)


def outer_trigger_ap(formula: str) -> str | None:
    """Accept the one-generation adapter shape used by this catalog."""
    match = re.match(
        r"^\s*G\*\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*->",
        formula,
    )
    return match.group(1) if match else None


def has_bounded_eventual(formula: str) -> bool:
    return bool(re.search(r"\bF\s*[\[(]\s*\d+\s*,\s*\d+\s*[\])]", formula))


def nested_http_urls(value: Any) -> set[str]:
    urls: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            urls.update(nested_http_urls(child))
    elif isinstance(value, list):
        for child in value:
            urls.update(nested_http_urls(child))
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        urls.add(value)
    return urls


def normalize_candidate(raw: dict[str, Any], fallback_protocol: str = "") -> dict[str, Any]:
    protocol = str(raw.get("protocol") or fallback_protocol)
    slug = canonical_protocol(protocol)
    if slug is None:
        raise ValueError(f"unknown protocol {protocol!r}")
    p = dict(raw)
    p["protocol"] = DISPLAY_BY_SLUG[slug]
    p["protocol_slug"] = slug
    p.setdefault("protocol_extension", p.get("standard", ""))
    p.setdefault("standard_version", p.get("standard", ""))
    p.setdefault("time_parameter", p.get("time_value_ms", ""))
    p.setdefault("instantiation_basis", "NORMATIVE_DEFAULT")
    p.setdefault("mathematical_mitl", p.get("mightyppl_formula", ""))
    # `G*` is MightyPPL's weak finite-word global operator, not standard
    # mathematical MITL notation.  Keep the executable formula unchanged but
    # publish an ordinary-G mathematical formula and state the finite bridge.
    p["mathematical_mitl"] = mathematical_form(str(p["mathematical_mitl"]))
    p.setdefault("interval_class", "NON_PUNCTUAL")
    p["pointwise_semantics"] = (
        "pointwise event positions with absolute integer milliseconds; mathematical_mitl uses standard MITL, "
        "while mightyppl_formula uses MightyPPL's weak finite-word G* operator"
    )
    p["finite_end_semantics"] = (
        "one correlated obligation generation per finite word; append a terminal position strictly beyond every "
        "bounded deadline so the supplied oracle is decisive; no overlapping trigger generations"
    )
    if not p.get("ap_definitions"):
        definitions = SIP_AP_DEFINITIONS if slug == "sip" else {}
        p["ap_definitions"] = {
            ap: definitions[ap]
            for ap in p.get("atomic_propositions", [])
            if ap in definitions
        }
    p.setdefault("projection_rule", "correlate first, then project one transaction/session; dynamic identifiers never enter AP names")
    p.setdefault("observability", "HYBRID")
    p.setdefault("oracle_value", "HIGH")
    p.setdefault("triggerability", "MEDIUM")
    p.setdefault("confidence", "MEDIUM")
    p.setdefault("additional_negative_traces", {})
    p.setdefault("additional_positive_traces", {})
    p.setdefault("auxiliary_source_mappings", [])
    p.setdefault("primary_source_atomic_propositions", [])
    p.setdefault("allows_equal_timestamp_microsteps", False)
    p.setdefault("microstep_ordering", "")
    p.setdefault(
        "monitor_instantiation",
        "one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation",
    )
    p.setdefault("independent_audit_status", "NOT_INDEPENDENTLY_AUDITED")
    p.setdefault("independent_audit_note", "")
    if slug == "sip" and p["independent_audit_status"] == "NOT_INDEPENDENTLY_AUDITED":
        match = re.fullmatch(r"SIP-TX-(\d+)", str(p.get("id", "")))
        if match and int(match.group(1)) <= 20:
            p["independent_audit_status"] = "PREVIOUSLY_ROOT_REVIEWED"
            p["independent_audit_note"] = (
                "RFC 3261 base card from the earlier root-reviewed research package; machine validation is rerun here, "
                "but user human signoff remains pending."
            )
        elif match:
            p["independent_audit_status"] = "ROOT_REVIEWED_EXTENSION"
            p["independent_audit_note"] = (
                "RFC 6026 extension card root-reviewed against the fixed Doubango source; human signoff remains pending."
            )
    p.setdefault("human_review_status", "PENDING")
    p.setdefault("review_question", "请确认规范角色、时间 profile、AP 和 correlation 映射。")
    p.setdefault("limitations", "")
    p["atomic_propositions"] = [str(x) for x in p.get("atomic_propositions", [])]
    p["positive_trace"] = normalize_trace(p.get("positive_trace"))
    p["negative_trace"] = normalize_trace(p.get("negative_trace"))
    extra_negatives = p.get("additional_negative_traces", {})
    if isinstance(extra_negatives, list):
        extra_negatives = {f"negative_{i + 2}": value for i, value in enumerate(extra_negatives)}
    if not isinstance(extra_negatives, dict):
        raise ValueError("additional_negative_traces must be an object or list")
    p["additional_negative_traces"] = {
        str(name): normalize_trace(value) for name, value in extra_negatives.items()
    }
    extra_positives = p.get("additional_positive_traces", {})
    if isinstance(extra_positives, list):
        extra_positives = {f"positive_{i + 2}": value for i, value in enumerate(extra_positives)}
    if not isinstance(extra_positives, dict):
        raise ValueError("additional_positive_traces must be an object or list")
    p["additional_positive_traces"] = {
        str(name): normalize_trace(value) for name, value in extra_positives.items()
    }
    # A no-early counterexample alone cannot detect accidental deletion of a
    # bounded liveness conjunct.  Always add the canonical missing-at-deadline
    # trace when one is absent; an unrelated extra counterexample is not a
    # substitute for this oracle.
    formula = str(p.get("mightyppl_formula", ""))
    trigger = outer_trigger_ap(formula)
    eventual_uppers = [
        int(value) for value in re.findall(r"F\s*[\[(]\s*\d+\s*,\s*(\d+)\s*[\])]", formula)
    ]
    if trigger and eventual_uppers:
        end = max(eventual_uppers) + 1
        # This reserved oracle is generator-owned.  Overwrite author input so
        # it cannot be made negative by an unrelated safety violation while
        # accidentally satisfying the bounded eventuality.
        p["additional_negative_traces"]["negative_late_or_missing"] = [
            {"time": 0, "props": [trigger]},
            {"time": end, "props": []},
        ]
        p["auto_generated_late_negative"] = True
    for field in BASE_FIELDS:
        p.setdefault(field, "")
    return p


def load_candidates() -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    load_errors: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    # Reuse the already audited SIP catalog as an input, then independently rerun it.
    sip_path = BASE / "mitl_property_catalog.json"
    if sip_path.exists():
        for raw in read_json(sip_path):
            try:
                p = normalize_candidate(raw, "SIP")
                p.setdefault("standard_version", "RFC 3261")
                p.setdefault("instantiation_basis", "NORMATIVE_DEFAULT")
                grouped["sip"].append(p)
                seen_ids.add(str(p["id"]))
            except Exception as exc:  # noqa: BLE001
                load_errors.append({"file": str(sip_path), "error": str(exc)})

    for path in sorted(STAGING.rglob("proposals.json")) if STAGING.exists() else []:
        try:
            doc = read_json(path)
            if isinstance(doc, dict):
                doc = doc.get("properties", doc.get("proposals", []))
            if not isinstance(doc, list):
                raise ValueError("top-level proposals must be an array")
            fallback = path.parent.name
            for raw in doc:
                p = normalize_candidate(raw, fallback)
                pid = str(p["id"])
                if pid in seen_ids:
                    raise ValueError(f"duplicate property id {pid}")
                seen_ids.add(pid)
                grouped[str(p["protocol_slug"])].append(p)
        except Exception as exc:  # noqa: BLE001
            load_errors.append({"file": str(path), "error": str(exc)})

    # Independent audits may correct an earlier immutable catalog without
    # rewriting that historical artifact.  Each override is a shallow,
    # explicit field replacement followed by full normalization and all normal
    # gates/source/formula checks.  Unknown or duplicate IDs fail closed.
    for path in sorted(STAGING.rglob("audit_overrides.json")) if STAGING.exists() else []:
        try:
            doc = read_json(path)
            if isinstance(doc, dict):
                doc = doc.get("overrides", [])
            if not isinstance(doc, list):
                raise ValueError("audit_overrides.json must contain an array or {overrides:[...]}")
            locations = {
                str(candidate["id"]): (slug, index, candidate)
                for slug, candidates in grouped.items()
                for index, candidate in enumerate(candidates)
            }
            override_ids: set[str] = set()
            for patch in doc:
                if not isinstance(patch, dict) or not patch.get("id"):
                    raise ValueError("every audit override must be an object with id")
                pid = str(patch["id"])
                if pid in override_ids:
                    raise ValueError(f"duplicate audit override id {pid}")
                override_ids.add(pid)
                if pid not in locations:
                    raise ValueError(f"audit override references unknown id {pid}")
                slug, index, prior = locations[pid]
                merged = dict(prior)
                merged.update(patch)
                if str(merged.get("id")) != pid or canonical_protocol(str(merged.get("protocol", ""))) != slug:
                    raise ValueError(f"audit override may not change id/protocol for {pid}")
                grouped[slug][index] = normalize_candidate(merged, slug)
        except Exception as exc:  # noqa: BLE001
            load_errors.append({"file": str(path), "error": str(exc)})
    return grouped, load_errors


def formula_has_singleton(formula: str) -> bool:
    for match in re.finditer(r"[\[(]\s*(\d+)\s*,\s*(\d+)\s*[\])]", formula):
        if match.group(1) == match.group(2):
            return True
    return False


def candidate_gate_errors(p: dict[str, Any]) -> list[str]:
    required = [
        "id", "protocol", "title", "natural_language", "normative_strength",
        "standard", "standard_version", "standard_section", "standard_url",
        "standard_excerpt", "time_value_ms", "time_source", "mightyppl_formula",
        "atomic_propositions", "correlation_key", "source_repository",
        "source_commit", "source_path", "source_symbol", "source_lines",
        "source_url", "instrumentation_timing", "positive_trace", "negative_trace",
    ]
    errors = [f"MISSING_{field.upper()}" for field in required if not p.get(field)]
    pid = str(p.get("id", ""))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", pid) or pid in {".", ".."}:
        errors.append("UNSAFE_PROPERTY_ID")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", str(p.get("source_commit", ""))):
        errors.append("SOURCE_COMMIT_NOT_40_HEX")
    source_url = urllib.parse.unquote(str(p.get("source_url", "")))
    source_commit = str(p.get("source_commit", ""))
    source_repository = str(p.get("source_repository", ""))
    source_path = str(p.get("source_path", ""))
    if source_commit and source_commit not in source_url:
        errors.append("SOURCE_URL_COMMIT_MISMATCH")
    if source_repository and f"github.com/{source_repository}/" not in source_url:
        errors.append("SOURCE_URL_REPOSITORY_MISMATCH")
    if source_path and source_path not in source_url:
        errors.append("SOURCE_URL_PATH_MISMATCH")
    primary_source_aps = p.get("primary_source_atomic_propositions", [])
    if not isinstance(primary_source_aps, list) or not primary_source_aps:
        errors.append("PRIMARY_SOURCE_APS_MISSING_OR_EMPTY")
        primary_source_aps = []
    primary_source_ap_set = {str(ap) for ap in primary_source_aps}
    auxiliary_mappings = p.get("auxiliary_source_mappings", [])
    if not isinstance(auxiliary_mappings, list):
        errors.append("AUXILIARY_SOURCE_MAPPINGS_NOT_LIST")
        auxiliary_mappings = []
    for index, mapping in enumerate(auxiliary_mappings):
        prefix = f"AUXILIARY_SOURCE_{index + 1}"
        if not isinstance(mapping, dict):
            errors.append(prefix + "_NOT_OBJECT")
            continue
        for field in ("role", "path", "symbol", "lines", "url"):
            if not str(mapping.get(field, "")).strip():
                errors.append(prefix + "_MISSING_" + field.upper())
        mapping_aps = mapping.get("atomic_propositions", [])
        if not isinstance(mapping_aps, list) or not mapping_aps:
            errors.append(prefix + "_APS_MISSING_OR_EMPTY")
        aux_repository = str(mapping.get("repository") or source_repository)
        aux_commit = str(mapping.get("commit") or source_commit)
        aux_path = str(mapping.get("path", ""))
        aux_url = urllib.parse.unquote(str(mapping.get("url", "")))
        if not re.fullmatch(r"[0-9a-fA-F]{40}", aux_commit):
            errors.append(prefix + "_COMMIT_NOT_40_HEX")
        if aux_repository and f"github.com/{aux_repository}/" not in aux_url:
            errors.append(prefix + "_URL_REPOSITORY_MISMATCH")
        if aux_commit and aux_commit not in aux_url:
            errors.append(prefix + "_URL_COMMIT_MISMATCH")
        if aux_path and aux_path not in aux_url:
            errors.append(prefix + "_URL_PATH_MISMATCH")
    legacy_source_urls: set[str] = set()
    for key, value in p.items():
        if key != "source_url" and (key.endswith("_source_url") or key.endswith("_source_urls")):
            legacy_source_urls.update(nested_http_urls(value))
    structured_source_urls = {str(p.get("source_url", ""))}
    structured_source_urls.update(str(mapping.get("url", "")) for mapping in auxiliary_mappings
                                  if isinstance(mapping, dict))
    unstructured = sorted(url for url in legacy_source_urls if url not in structured_source_urls)
    if unstructured:
        errors.append("UNSTRUCTURED_SOURCE_URLS:" + ",".join(unstructured))
    if formula_has_singleton(str(p.get("mightyppl_formula", ""))):
        errors.append("PUNCTUAL_SINGLETON")
    if str(p.get("interval_class")) == "PUNCTUAL":
        errors.append("PUNCTUAL_CLASS")
    ap_list = [str(ap) for ap in p.get("atomic_propositions", [])]
    aps = set(ap_list)
    if len(aps) != len(ap_list):
        errors.append("DUPLICATE_DECLARED_AP")
    invalid_aps = sorted(ap for ap in aps if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ap))
    if invalid_aps:
        errors.append("UNSAFE_AP_NAME:" + ",".join(invalid_aps))
    mapped_aps = set(primary_source_ap_set)
    for mapping in auxiliary_mappings:
        if isinstance(mapping, dict) and isinstance(mapping.get("atomic_propositions"), list):
            mapped_aps.update(str(ap) for ap in mapping["atomic_propositions"])
    if primary_source_ap_set - aps:
        errors.append("PRIMARY_SOURCE_UNKNOWN_AP:" + ",".join(sorted(primary_source_ap_set - aps)))
    if mapped_aps - aps:
        errors.append("SOURCE_MAPPING_UNKNOWN_AP:" + ",".join(sorted(mapped_aps - aps)))
    if aps - mapped_aps:
        errors.append("AP_WITHOUT_SOURCE_MAPPING:" + ",".join(sorted(aps - mapped_aps)))
    formula_aps = formula_atomic_propositions(str(p.get("mightyppl_formula", "")))
    if formula_aps != aps:
        errors.append(
            "FORMULA_AP_SET_MISMATCH:formula_only=" + ",".join(sorted(formula_aps - aps))
            + ";declared_only=" + ",".join(sorted(aps - formula_aps))
        )
    expected_mathematical = re.sub(r"\s+", "", mathematical_form(str(p.get("mightyppl_formula", ""))))
    observed_mathematical = re.sub(r"\s+", "", str(p.get("mathematical_mitl", "")))
    if observed_mathematical != expected_mathematical:
        errors.append("MATHEMATICAL_EXECUTABLE_FORMULA_MISMATCH")
    definitions = p.get("ap_definitions")
    if not isinstance(definitions, dict):
        errors.append("AP_DEFINITIONS_NOT_OBJECT")
    else:
        missing_definitions = sorted(ap for ap in aps if not str(definitions.get(ap, "")).strip())
        if missing_definitions:
            errors.append("AP_DEFINITION_MISSING:" + ",".join(missing_definitions))
        vague_definitions = sorted(
            ap for ap in aps
            if str(definitions.get(ap, "")).strip()
            and (len(str(definitions[ap]).strip()) < 12
                 or str(definitions[ap]).strip().lower() == ap.replace("_", " ").lower())
        )
        if vague_definitions:
            errors.append("AP_DEFINITION_TOO_VAGUE:" + ",".join(vague_definitions))
    extra_negatives = p.get("additional_negative_traces", {})
    extra_positives = p.get("additional_positive_traces", {})
    for kind, traces in (("NEGATIVE", extra_negatives), ("POSITIVE", extra_positives)):
        safe_extra_names: set[str] = set()
        for name in traces:
            text_name = str(name)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", text_name):
                errors.append(f"UNSAFE_ADDITIONAL_{kind}_NAME:" + text_name)
            if text_name in safe_extra_names:
                errors.append(f"DUPLICATE_ADDITIONAL_{kind}_NAME:" + text_name)
            safe_extra_names.add(text_name)
    trace_sets = {
        "positive_trace": p.get("positive_trace", []),
        "negative_trace": p.get("negative_trace", []),
        **{f"additional_positive:{name}": trace for name, trace in extra_positives.items()},
        **{f"additional_negative:{name}": trace for name, trace in extra_negatives.items()},
    }
    for side, trace in trace_sets.items():
        extras = {ap for event in trace for ap in event["props"] if ap not in aps}
        if extras:
            errors.append(f"{side.upper().replace(':', '_')}_UNKNOWN_AP:" + ",".join(sorted(extras)))
        equal_positions = any(
            trace[index]["time"] == trace[index + 1]["time"]
            for index in range(len(trace) - 1)
        )
        if equal_positions and p.get("allows_equal_timestamp_microsteps") is not True:
            errors.append(f"{side.upper().replace(':', '_')}_UNDECLARED_EQUAL_TIMESTAMP_MICROSTEP")
    if p.get("allows_equal_timestamp_microsteps") is True and len(str(p.get("microstep_ordering", "")).strip()) < 20:
        errors.append("MICROSTEP_ORDERING_MISSING_OR_VAGUE")
    # Current flatten monitors do not correctly preserve all overlapping G*
    # obligations.  Until that implementation is repaired, every validation
    # word must represent exactly one adapter-correlated obligation instance.
    trigger = outer_trigger_ap(str(p.get("mightyppl_formula", "")))
    if trigger is None:
        errors.append("UNSUPPORTED_OUTER_TRIGGER_SHAPE")
    else:
        for side, trace in trace_sets.items():
            trigger_count = sum(trigger in event["props"] for event in trace)
            if trigger_count != 1:
                errors.append(
                    f"{side.upper().replace(':', '_')}_TRIGGER_COUNT_{trigger_count}_EXPECTED_1:{trigger}"
                )
    if not str(p.get("monitor_instantiation", "")).strip():
        errors.append("MONITOR_INSTANTIATION_MISSING")
    if has_bounded_eventual(str(p.get("mightyppl_formula", ""))):
        eventual_uppers = [
            int(value) for value in re.findall(
                r"F\s*[\[(]\s*\d+\s*,\s*(\d+)\s*[\])]",
                str(p.get("mightyppl_formula", "")),
            )
        ]
        expected_late = [
            {"time": 0, "props": [trigger]} if trigger else {"time": 0, "props": []},
            {"time": max(eventual_uppers) + 1, "props": []},
        ] if eventual_uppers else []
        if extra_negatives.get("negative_late_or_missing") != expected_late:
            errors.append("BOUNDED_EVENTUAL_LATE_NEGATIVE_NOT_CANONICAL")
    if len(str(p.get("standard_excerpt", "")).split()) > 25:
        errors.append("STANDARD_EXCERPT_OVER_25_WORDS")
    audit_status = str(p.get("independent_audit_status", "")).upper()
    accepted_audit_status = (
        audit_status in {"APPROVE", "FIXED_AFTER_AUDIT", "PREVIOUSLY_ROOT_REVIEWED"}
        or audit_status.startswith("APPROVE_")
        or audit_status.startswith("ROOT_REVIEWED")
    )
    if not accepted_audit_status:
        errors.append("UNKNOWN_OR_UNAPPROVED_AUDIT_STATUS:" + audit_status)
    if audit_status in {"REJECT", "REJECT_OR_FIX", "FIX", "NEEDS_FIX"}:
        errors.append("INDEPENDENT_AUDIT_REJECT")
    return errors


def ap_definition_conflicts(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    conflicts: dict[str, list[str]] = defaultdict(list)
    rejected_statuses = {"REJECT", "REJECT_OR_FIX", "FIX", "NEEDS_FIX"}
    for slug, candidates in grouped.items():
        registry: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for candidate in candidates:
            if str(candidate.get("independent_audit_status")) in rejected_statuses:
                continue
            for ap, definition in candidate.get("ap_definitions", {}).items():
                canonical = re.sub(r"\s+", " ", str(definition)).strip()
                registry[str(ap)][canonical].append(str(candidate.get("id")))
        for ap, definitions in registry.items():
            if len(definitions) <= 1:
                continue
            affected = sorted({pid for ids in definitions.values() for pid in ids})
            for pid in affected:
                conflicts[pid].append(f"AP_DEFINITION_CONFLICT:{slug}:{ap}")
    return conflicts


_url_cache: dict[str, tuple[bool, str]] = {}
_source_cache: dict[tuple[str, str, str], tuple[str | None, str]] = {}


def verify_url(url: str) -> tuple[bool, str]:
    if url in _url_cache:
        return _url_cache[url]
    notes = []
    result = (False, "not attempted")
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "TAFuzz-research/1.0", "Range": "bytes=0-2047"})
            with urllib.request.urlopen(request, timeout=20) as response:
                result = (200 <= response.status < 400, f"HTTP {response.status}")
                break
        except Exception as exc:  # noqa: BLE001
            notes.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
            time.sleep(0.2 * (attempt + 1))
    if not result[0]:
        curl = subprocess.run(["curl", "-L", "--fail", "--silent", "--show-error",
                               "--max-time", "30", "--range", "0-2047", url],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        result = (curl.returncode == 0,
                  "curl fallback HTTP success" if curl.returncode == 0 else "; ".join(notes + [curl.stderr.strip()]))
        # A few formal-standard hosts serve a chain that the bundled CA store
        # cannot validate.  An insecure retry proves reachability only; the
        # caveat is retained verbatim and never used for source-code evidence.
        if not result[0] and "certificate" in result[1].lower():
            insecure = subprocess.run(["curl", "-k", "-L", "--fail", "--silent",
                                       "--show-error", "--max-time", "30", "--range",
                                       "0-2047", url], stdout=subprocess.DEVNULL,
                                      stderr=subprocess.PIPE, text=True)
            if insecure.returncode == 0:
                result = (True, "HTTP reachable only with curl -k; local CA-chain verification failed")
    _url_cache[url] = result
    return result


def fetch_source(repository: str, commit: str, source_path: str) -> tuple[str | None, str]:
    key = (repository, commit, source_path)
    if key in _source_cache:
        return _source_cache[key]
    if not re.fullmatch(r"[^/]+/[^/]+", repository):
        result = (None, "source_repository is not owner/repo")
    else:
        encoded_path = "/".join(urllib.parse.quote(part) for part in source_path.split("/"))
        url = f"https://raw.githubusercontent.com/{repository}/{commit}/{encoded_path}"
        notes = []
        result = (None, "not attempted")
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "TAFuzz-research/1.0"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    result = (response.read().decode("utf-8", "replace"), f"HTTP {response.status}: {url}")
                    break
            except Exception as exc:  # noqa: BLE001
                notes.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
                time.sleep(0.2 * (attempt + 1))
        if result[0] is None:
            curl = subprocess.run(["curl", "-L", "--fail", "--silent", "--show-error",
                                   "--max-time", "45", url], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
            result = ((curl.stdout if curl.returncode == 0 else None),
                      f"curl fallback: {url}" if curl.returncode == 0
                      else "; ".join(notes + [curl.stderr.strip(), url]))
    _source_cache[key] = result
    return result


def parse_source_ranges(value: str) -> list[tuple[int, int]]:
    ranges = []
    for match in re.finditer(r"(?<![A-Za-z0-9])([0-9]+)(?:\s*-\s*([0-9]+))?", value):
        lo = int(match.group(1))
        hi = int(match.group(2) or match.group(1))
        ranges.append((lo, hi))
    return ranges


def strip_c_comments_preserve_lines(text: str) -> str:
    """Remove C/C++ comments without changing line numbers."""
    def block(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    no_blocks = re.sub(r"/\*.*?\*/", block, text, flags=re.S)
    return re.sub(r"//[^\n]*", "", no_blocks)


def definition_spans(text: str, source_path: str, symbol: str) -> list[tuple[int, int]]:
    """Find executable definition/declaration spans, never comment mentions."""
    lines = text.splitlines()
    spans: list[tuple[int, int]] = []
    raw = symbol.strip()
    if source_path.endswith(".py"):
        name = raw.removeprefix("def ").strip().split(".")[-1]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            return spans
        for start, line in enumerate(lines):
            if not re.search(rf"^\s*(?:async\s+)?def\s+{re.escape(name)}\s*\(", line):
                continue
            indent = len(line) - len(line.lstrip())
            end = len(lines)
            for idx in range(start + 1, len(lines)):
                candidate = lines[idx]
                if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                    end = idx
                    break
            spans.append((start + 1, end))
        return spans

    # A source_symbol field is an identifier or a C++ qualified identifier;
    # free-form prose is not acceptable as fixed-source evidence.
    cleaned_symbol = raw.removeprefix("def ").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*", cleaned_symbol):
        return spans
    name = cleaned_symbol.split("::")[-1]
    cleaned = strip_c_comments_preserve_lines(text)
    clean_lines = cleaned.splitlines()

    # Preprocessor constants are legitimate symbols when the cited line is the
    # actual definition, not a later use or a comment.
    for idx, line in enumerate(clean_lines):
        if re.search(rf"^\s*#\s*define\s+{re.escape(name)}\b", line):
            spans.append((idx + 1, idx + 1))

    # Function/method definitions: an opening brace must precede any semicolon.
    for match in re.finditer(rf"\b{re.escape(name)}\s*\(", cleaned):
        tail = cleaned[match.end():match.end() + 2000]
        brace_rel = tail.find("{")
        semi_rel = tail.find(";")
        if brace_rel < 0 or (0 <= semi_rel < brace_rel):
            continue
        brace_pos = match.end() + brace_rel
        start_line = cleaned.count("\n", 0, match.start()) + 1
        depth = 0
        end_pos = brace_pos
        for pos in range(brace_pos, len(cleaned)):
            char = cleaned[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end_pos = pos
                    break
        if depth == 0:
            end_line = cleaned.count("\n", 0, end_pos) + 1
            spans.append((start_line, end_line))

    # Enum/static constants occasionally use assignment rather than #define;
    # accept only the defining line itself.
    for idx, line in enumerate(clean_lines):
        if re.search(rf"\b{re.escape(name)}\b\s*=", line):
            spans.append((idx + 1, idx + 1))
    return sorted(set(spans))


def verify_source(p: dict[str, Any]) -> dict[str, Any]:
    text, note = fetch_source(str(p["source_repository"]), str(p["source_commit"]), str(p["source_path"]))
    file_ok = text is not None
    line_ok = False
    symbol_ok = False
    symbol_note = ""
    if text is not None:
        lines = text.splitlines()
        ranges = parse_source_ranges(str(p["source_lines"]))
        line_ok = bool(ranges) and all(1 <= lo <= hi <= len(lines) for lo, hi in ranges)
        symbols = [x.strip() for x in re.split(r"[/;,]", str(p["source_symbol"])) if x.strip()]
        verified_symbols = []
        failed_symbols = []
        all_spans: list[tuple[int, int]] = []
        if line_ok and symbols:
            for symbol in symbols:
                spans = definition_spans(text, str(p["source_path"]), symbol)
                all_spans.extend(spans)
                intersects = any(
                    max(cited_lo, span_lo) <= min(cited_hi, span_hi)
                    for cited_lo, cited_hi in ranges
                    for span_lo, span_hi in spans
                )
                if intersects:
                    verified_symbols.append(symbol)
                else:
                    failed_symbols.append(symbol)
            uncovered_ranges = [
                (cited_lo, cited_hi) for cited_lo, cited_hi in ranges
                if not any(max(cited_lo, span_lo) <= min(cited_hi, span_hi)
                           for span_lo, span_hi in all_spans)
            ]
            symbol_ok = not failed_symbols and not uncovered_ranges
        else:
            uncovered_ranges = ranges
        symbol_note = (
            f"verified_symbols={verified_symbols}; failed_symbols={failed_symbols}; "
            f"cited_ranges={ranges}; uncovered_ranges={uncovered_ranges}"
        )
    return {
        "source_file_verified": file_ok,
        "source_line_verified": line_ok,
        "source_symbol_verified": symbol_ok,
        "source_verification_note": note + ("; " + symbol_note if symbol_note else ""),
    }


def verify_auxiliary_sources(p: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    results = []
    for index, mapping in enumerate(p.get("auxiliary_source_mappings", [])):
        probe = {
            "source_repository": mapping.get("repository") or p["source_repository"],
            "source_commit": mapping.get("commit") or p["source_commit"],
            "source_path": mapping.get("path", ""),
            "source_symbol": mapping.get("symbol", ""),
            "source_lines": mapping.get("lines", ""),
        }
        result = verify_source(probe)
        results.append({
            "index": index + 1,
            "role": mapping.get("role", ""),
            "atomic_propositions": mapping.get("atomic_propositions", []),
            "repository": probe["source_repository"],
            "commit": probe["source_commit"],
            "path": probe["source_path"],
            "symbol": probe["source_symbol"],
            "lines": probe["source_lines"],
            "url": mapping.get("url", ""),
            **result,
        })
    ok = all(
        item["source_file_verified"]
        and item["source_line_verified"]
        and item["source_symbol_verified"]
        for item in results
    )
    return ok, results


def trace_text(events: list[dict[str, Any]]) -> str:
    lines = ["# absolute integer milliseconds; omitted APs are false", "# time,props"]
    for event in events:
        props = ",".join(event["props"])
        lines.append(f'{event["time"]},{{{props}}}')
    return "\n".join(lines) + "\n"


def run_command(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=60)
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + "\nTIMEOUT"


def validate_property(p: dict[str, Any], protocol_dir: Path) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", str(p["id"])) or str(p["id"]) in {".", ".."}:
        raise ValueError(f"unsafe property id reached validator: {p['id']!r}")
    d = protocol_dir / "validation" / str(p["id"])
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "formula.mitl").write_text(str(p["mightyppl_formula"]) + "\n", encoding="utf-8")
    (d / "positive.trace").write_text(trace_text(p["positive_trace"]), encoding="utf-8")
    (d / "negative.trace").write_text(trace_text(p["negative_trace"]), encoding="utf-8")
    for name, trace in p.get("additional_negative_traces", {}).items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", str(name)):
            raise ValueError(f"unsafe additional-negative name reached validator: {name!r}")
        (d / f"negative_extra_{name}.trace").write_text(trace_text(trace), encoding="utf-8")
    for name, trace in p.get("additional_positive_traces", {}).items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", str(name)):
            raise ValueError(f"unsafe additional-positive name reached validator: {name!r}")
        (d / f"positive_extra_{name}.trace").write_text(trace_text(trace), encoding="utf-8")
    commands: list[str] = []
    outcomes: dict[str, dict[str, Any]] = {}
    cases = [
        ("build_only", None, "symbolic"),
        ("positive_symbolic", "positive.trace", "symbolic"),
        ("negative_symbolic", "negative.trace", "symbolic"),
        ("positive_concrete", "positive.trace", "concrete"),
        ("negative_concrete", "negative.trace", "concrete"),
    ]
    for name in sorted(p.get("additional_negative_traces", {})):
        cases += [
            (f"negative_extra_{name}_symbolic", f"negative_extra_{name}.trace", "symbolic"),
            (f"negative_extra_{name}_concrete", f"negative_extra_{name}.trace", "concrete"),
        ]
    for name in sorted(p.get("additional_positive_traces", {})):
        cases += [
            (f"positive_extra_{name}_symbolic", f"positive_extra_{name}.trace", "symbolic"),
            (f"positive_extra_{name}_concrete", f"positive_extra_{name}.trace", "concrete"),
        ]
    for name, trace, state in cases:
        result_dir = d / name
        cmd = [str(TAMONITOR), "--formula", str(d / "formula.mitl"), "--word", "finite",
               "--build-mode", "flatten", "--state", state, "--out", str(result_dir)]
        if trace:
            cmd[1:1] = ["--trace", str(d / trace)]
        else:
            cmd.append("--build-only")
        rc, output = run_command(cmd)
        commands.append("$ " + " ".join(cmd) + "\n" + output.rstrip())
        metadata_path = result_dir / "metadata.json"
        metadata = read_json(metadata_path) if metadata_path.exists() else {}
        outcomes[name] = {"return_code": rc, "metadata": metadata}
    (d / "commands.log").write_text("\n\n".join(commands) + "\n", encoding="utf-8")
    ps = outcomes["positive_symbolic"]["metadata"]
    ns = outcomes["negative_symbolic"]["metadata"]
    pc = outcomes["positive_concrete"]["metadata"]
    nc = outcomes["negative_concrete"]["metadata"]
    all_commands_ok = all(outcome["return_code"] == 0 for outcome in outcomes.values())
    build_ok = outcomes["build_only"]["return_code"] == 0 and all_commands_ok
    oracle_ok = ps.get("final_verdict") == "POSITIVE" and ns.get("final_verdict") == "NEGATIVE"
    consistent = (ps.get("final_verdict") == pc.get("final_verdict") and
                  ns.get("final_verdict") == nc.get("final_verdict"))
    extra_results = {}
    for name in sorted(p.get("additional_negative_traces", {})):
        symbolic = outcomes[f"negative_extra_{name}_symbolic"]["metadata"].get("final_verdict", "NO_OUTPUT")
        concrete = outcomes[f"negative_extra_{name}_concrete"]["metadata"].get("final_verdict", "NO_OUTPUT")
        extra_results[name] = {"symbolic": symbolic, "concrete": concrete}
        oracle_ok = oracle_ok and symbolic == "NEGATIVE"
        consistent = consistent and symbolic == concrete
    extra_positive_results = {}
    for name in sorted(p.get("additional_positive_traces", {})):
        symbolic = outcomes[f"positive_extra_{name}_symbolic"]["metadata"].get("final_verdict", "NO_OUTPUT")
        concrete = outcomes[f"positive_extra_{name}_concrete"]["metadata"].get("final_verdict", "NO_OUTPUT")
        extra_positive_results[name] = {"symbolic": symbolic, "concrete": concrete}
        oracle_ok = oracle_ok and symbolic == "POSITIVE"
        consistent = consistent and symbolic == concrete
    ap_order_ok = set(ps.get("proposition_order", [])) == set(p.get("atomic_propositions", []))
    oracle_ok = oracle_ok and ap_order_ok
    result = {
        "id": p["id"], "build_ok": build_ok,
        "all_commands_ok": all_commands_ok,
        "positive_symbolic": ps.get("final_verdict", "NO_OUTPUT"),
        "negative_symbolic": ns.get("final_verdict", "NO_OUTPUT"),
        "positive_concrete": pc.get("final_verdict", "NO_OUTPUT"),
        "negative_concrete": nc.get("final_verdict", "NO_OUTPUT"),
        "expected_oracle_ok": oracle_ok, "symbolic_concrete_consistent": consistent,
        "additional_positive_results": extra_positive_results,
        "additional_negative_results": extra_results,
        "ap_order": ps.get("proposition_order", []), "ap_order_ok": ap_order_ok,
        "positive_locations": ps.get("positive_stats", {}).get("locations"),
        "positive_edges": ps.get("positive_stats", {}).get("edges"),
        "positive_clocks": ps.get("positive_stats", {}).get("clocks"),
        "negative_locations": ps.get("negative_stats", {}).get("locations"),
        "negative_edges": ps.get("negative_stats", {}).get("edges"),
        "negative_clocks": ps.get("negative_stats", {}).get("clocks"),
        "build_ms": ps.get("build_ms"), "monitor_ms_positive": ps.get("monitor_ms"),
        "monitor_ms_negative": ns.get("monitor_ms"),
        "status": "PASS" if build_ok and oracle_ok and consistent else "FAIL",
    }
    write_json(d / "validation_result.json", result)
    return result


def attach_validation(p: dict[str, Any], result: dict[str, Any]) -> None:
    for key, value in result.items():
        if key != "id":
            p[f"validation_{key}"] = value


def verified_source_mappings_for_ap(p: dict[str, Any], ap: str) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    if ap in p.get("primary_source_atomic_propositions", []):
        mappings.append({
            "mapping": "primary", "role": "primary property hook",
            "event_predicate": p.get("ap_definitions", {}).get(ap, ""),
            "instrumentation_timing": p.get("instrumentation_timing", ""),
            "atomic_propositions": p.get("primary_source_atomic_propositions", []),
            "repository": p["source_repository"], "commit": p["source_commit"],
            "path": p["source_path"], "symbol": p["source_symbol"],
            "lines": p["source_lines"], "url": p["source_url"],
            "source_file_verified": p.get("source_file_verified"),
            "source_line_verified": p.get("source_line_verified"),
            "source_symbol_verified": p.get("source_symbol_verified"),
        })
    verification_by_index = {
        int(item.get("index", 0)): item
        for item in p.get("auxiliary_source_verification", [])
    }
    for index, mapping in enumerate(p.get("auxiliary_source_mappings", []), start=1):
        if ap not in mapping.get("atomic_propositions", []):
            continue
        verified = verification_by_index.get(index, {})
        mappings.append({
            "mapping": f"auxiliary:{index}", "role": mapping.get("role", ""),
            "event_predicate": p.get("ap_definitions", {}).get(ap, ""),
            "instrumentation_timing": mapping.get("instrumentation_timing") or p.get("instrumentation_timing", ""),
            "atomic_propositions": mapping.get("atomic_propositions", []),
            "repository": mapping.get("repository") or p["source_repository"],
            "commit": mapping.get("commit") or p["source_commit"],
            "path": mapping.get("path", ""), "symbol": mapping.get("symbol", ""),
            "lines": mapping.get("lines", ""), "url": mapping.get("url", ""),
            "source_file_verified": verified.get("source_file_verified"),
            "source_line_verified": verified.get("source_line_verified"),
            "source_symbol_verified": verified.get("source_symbol_verified"),
        })
    return mappings


def catalog_markdown(display: str, admitted: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> str:
    lines = [f"# {display} MITL 真实性质目录", "",
             "> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。", "",
             f"- 合格性质：{len(admitted)}", f"- 自动拒绝/待修：{len(rejected)}",
             "- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。", ""]
    if not admitted:
        lines += ["当前没有候选同时通过全部收录门。原因见 `excluded_properties.md`。", ""]
    for p in admitted:
        auxiliary_sources = {
            key: value for key, value in p.items()
            if (key.endswith("_source_url") or key.endswith("_source_urls"))
            and key != "source_url" and str(value).strip()
        }
        lines += [
            f'## {p["id"]} — {p["title"]}', "",
            f'- 性质：{p["natural_language"]}',
            f'- 规范：[{p["standard"]} {p["standard_version"]} §{p["standard_section"]}]({p["standard_url"]})；强度 `{p["normative_strength"]}`；时间 `{p["time_value_ms"]} ms`（`{p["instantiation_basis"]}`）。',
            f'- 规范短摘录：“{p["standard_excerpt"]}”',
            f'- 数学 MITL：`{p["mathematical_mitl"]}`',
            f'- MightyPPL（finite weak outer global）：`{p["mightyppl_formula"]}`',
            f'- AP：`{", ".join(p["atomic_propositions"])}`',
            f'- AP 定义：{json.dumps(p["ap_definitions"], ensure_ascii=False)}',
            f'- Correlation：{p["correlation_key"]}',
            f'- 投影：{p["projection_rule"]}',
            f'- 监控实例：{p["monitor_instantiation"]}',
            f'- 源码：[{p["source_repository"]}@{p["source_commit"][:12]} `{p["source_path"]}:{p["source_lines"]}`]({p["source_url"]})；符号 `{p["source_symbol"]}`。',
            f'- 主源码映射 AP：`{json.dumps(p.get("primary_source_atomic_propositions", []), ensure_ascii=False)}`',
            f'- 辅助源码锚点：`{json.dumps(auxiliary_sources, ensure_ascii=False)}`',
            f'- 结构化辅助映射：`{json.dumps(p.get("auxiliary_source_mappings", []), ensure_ascii=False)}`',
            f'- Hook：{p["instrumentation_timing"]}',
            f'- 正例 timed word：`{json.dumps(p["positive_trace"], ensure_ascii=False)}`',
            f'- 附加正例/合法 supersession：`{json.dumps(p.get("additional_positive_traces", {}), ensure_ascii=False)}`',
            f'- 反例 timed word：`{json.dumps(p["negative_trace"], ensure_ascii=False)}`',
            f'- 附加反例：`{json.dumps(p["additional_negative_traces"], ensure_ascii=False)}`',
            f'- 独立审计：`{p["independent_audit_status"]}`；{p["independent_audit_note"] or "尚无附加说明"}',
            f'- 被测角色/benchmark 可达性/范围：`{p.get("sut_role") or "未限定"}` / `{p.get("benchmark_reachability") or "未单独评估"}` / {p.get("scope") or "见性质与限制字段"}。',
            f'- 可观测性/价值/置信度：`{p["observability"]}` / `{p["oracle_value"]}` / `{p["confidence"]}`。',
            f'- 验证：build=`{p["validation_build_ok"]}`，positive=`{p["validation_positive_symbolic"]}`，negative=`{p["validation_negative_symbolic"]}`，symbolic/concrete=`{p["validation_symbolic_concrete_consistent"]}`。',
            f'- 限制/待审：{p["limitations"] or p["review_question"]}', "",
        ]
    return "\n".join(lines)


def collect_staging_exclusions(slug: str) -> list[str]:
    chunks = []
    if not STAGING.exists():
        return chunks
    for path in sorted(STAGING.rglob("excluded.md")):
        parent_slug = canonical_protocol(path.parent.name)
        text = path.read_text(encoding="utf-8")
        if parent_slug == slug or re.search(rf"\b{re.escape(DISPLAY_BY_SLUG[slug])}\b", text, re.I):
            chunks.append(f"## 研究阶段排除：{path.relative_to(BASE)}\n\n{text.strip()}\n")
    return chunks


def collect_staging_evidence(slug: str) -> list[dict[str, Any]]:
    records = []
    if slug == "sip" and (BASE / "evidence_manifest.yaml").exists():
        try:
            records.append({
                "file": "evidence_manifest.yaml",
                "record": read_json(BASE / "evidence_manifest.yaml"),
                "role": "previously audited RFC 3261 base-catalog evidence",
            })
        except Exception as exc:  # noqa: BLE001
            records.append({"file": "evidence_manifest.yaml", "read_error": str(exc)})
    if not STAGING.exists():
        return records
    for path in sorted(STAGING.rglob("evidence.json")):
        if canonical_protocol(path.parent.name) != slug:
            continue
        try:
            records.append({"file": str(path.relative_to(BASE)), "record": read_json(path)})
        except Exception as exc:  # noqa: BLE001
            records.append({"file": str(path.relative_to(BASE)), "read_error": str(exc)})
    return records


def screening_document_count(records: list[dict[str, Any]]) -> int:
    count = 0
    for item in records:
        record = item.get("record", {})
        if not isinstance(record, dict):
            continue
        for key in ("standards", "screened_documents", "sources"):
            value = record.get(key, [])
            if isinstance(value, list):
                count += len(value)
        if record.get("standard"):
            count += 1
    return count


def exclusion_candidate_count(chunks: list[str]) -> int:
    count = 0
    for chunk in chunks:
        for line in chunk.splitlines():
            stripped = line.strip()
            if stripped.startswith("- `"):
                count += 1
            elif stripped.startswith("|") and not stripped.startswith("|---") and "Candidate" not in stripped and "候选" not in stripped:
                count += 1
    return count


def incomplete_evidence_records(records: list[dict[str, Any]]) -> list[str]:
    incomplete = []
    if not records:
        return ["NO_EVIDENCE_RECORDS"]
    for item in records:
        if item.get("read_error"):
            incomplete.append(f'{item.get("file", "unknown")}:READ_ERROR:{item["read_error"]}')
            continue
        record = item.get("record", {})
        if not isinstance(record, dict) or not record:
            incomplete.append(f'{item.get("file", "unknown")}:EMPTY_OR_INVALID_RECORD')
            continue
        status = str(record.get("status", "")).upper()
        if status:
            completed = bool(re.fullmatch(
                r"(?:COMPLETE(?:_WITH_[A-Z0-9_]+)?|FIXED_AFTER_[A-Z0-9_]*COMPLETE|"
                r"SCREENED_NO_ADMITTED_MITL_AFTER_[A-Z0-9_]+)",
                status,
            ))
            if not completed:
                incomplete.append(f'{item.get("file", "unknown")}:{status}')
        elif item.get("file") == "evidence_manifest.yaml":
            if not isinstance(record.get("sources"), list) or not record.get("sources"):
                incomplete.append(f'{item.get("file", "unknown")}:BASE_MANIFEST_WITHOUT_SOURCES')
        else:
            incomplete.append(f'{item.get("file", "unknown")}:MISSING_STATUS')
    return incomplete


def main() -> int:
    if not TAMONITOR.exists():
        raise SystemExit(f"missing TAMonitor: {TAMONITOR}")
    grouped, load_errors = load_candidates()
    definition_conflicts = ap_definition_conflicts(grouped)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    aggregate: list[dict[str, Any]] = []
    protocol_summaries: list[dict[str, Any]] = []
    source_checks: list[dict[str, Any]] = []
    evidence_index: list[dict[str, Any]] = []
    all_hook_rows: list[dict[str, Any]] = []
    all_validation_rows: list[dict[str, Any]] = []
    all_rejected: list[dict[str, Any]] = []

    for slug, display in PROTOCOLS:
        pdir = OUT / slug
        pdir.mkdir(parents=True)
        research_evidence = collect_staging_evidence(slug)
        evidence_incomplete = incomplete_evidence_records(research_evidence)
        staging_exclusions = collect_staging_exclusions(slug)
        admitted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        validation_rows: list[dict[str, Any]] = []
        for p in sorted(grouped.get(slug, []), key=lambda x: str(x.get("id", ""))):
            errors = candidate_gate_errors(p)
            errors.extend(definition_conflicts.get(str(p.get("id")), []))
            if evidence_incomplete:
                errors.append("EVIDENCE_LEDGER_INCOMPLETE:" + ";".join(evidence_incomplete))
            url_ok, url_note = verify_url(str(p.get("standard_url", ""))) if p.get("standard_url") else (False, "missing")
            p.pop("standard_url_verified", None)
            p["standard_url_reachable"] = url_ok
            source = verify_source(p)
            p.update(source)
            source_checks.append({
                "id": p["id"], "protocol": display, "mapping": "primary",
                "role": "primary property hook", "repository": p.get("source_repository"),
                "atomic_propositions": p.get("primary_source_atomic_propositions", []),
                "commit": p.get("source_commit"), "path": p.get("source_path"),
                "symbol": p.get("source_symbol"), "lines": p.get("source_lines"), **source,
            })
            if not source["source_file_verified"]:
                errors.append("NO_FIXED_SOURCE_FILE")
            if not source["source_line_verified"]:
                errors.append("SOURCE_LINES_INVALID")
            if not source["source_symbol_verified"]:
                errors.append("SOURCE_SYMBOL_NOT_FOUND")
            auxiliary_ok, auxiliary_results = verify_auxiliary_sources(p)
            p["auxiliary_source_verification"] = auxiliary_results
            for item in auxiliary_results:
                source_checks.append({
                    "id": p["id"], "protocol": display,
                    "mapping": f'auxiliary:{item["index"]}', **item,
                })
            if p.get("auxiliary_source_mappings") and not auxiliary_ok:
                errors.append("AUXILIARY_SOURCE_VERIFICATION_FAILED")
            p["standard_url_verification_note"] = url_note
            if not url_ok:
                errors.append("STANDARD_URL_UNREACHABLE")
            if not errors:
                result = validate_property(p, pdir)
                attach_validation(p, result)
                validation_rows.append(result)
                all_validation_rows.append({"protocol": display, **result})
                if result["status"] != "PASS":
                    errors.append("FORMULA_OR_TRACE_VALIDATION_FAILED")
            if errors:
                p["rejection_reasons"] = sorted(set(errors))
                rejected.append(p)
                all_rejected.append(p)
            else:
                admitted.append(p)
                aggregate.append(p)
                evidence_index.append({
                    "property_id": p["id"], "protocol": display, "standard": p["standard"],
                    "standard_version": p["standard_version"], "section": p["standard_section"],
                    "standard_url": p["standard_url"], "source_repository": p["source_repository"],
                    "source_commit": p["source_commit"], "source_path": p["source_path"],
                    "source_lines": p["source_lines"], "source_url": p["source_url"],
                    "auxiliary_source_mappings": p.get("auxiliary_source_mappings", []),
                    "accessed": ACCESS_DATE,
                })

        write_json(pdir / "mitl_property_catalog.json", admitted)
        write_csv(pdir / "mitl_property_catalog.csv", admitted, BASE_FIELDS + VALIDATION_FIELDS)
        (pdir / "mitl_property_catalog.md").write_text(catalog_markdown(display, admitted, rejected), encoding="utf-8")
        write_json(pdir / "rejected_after_validation.json", rejected)
        write_csv(pdir / "formula_validation_summary.csv", validation_rows,
                  list(validation_rows[0].keys()) if validation_rows else ["id", "status"])
        aps: dict[str, dict[str, Any]] = {}
        hook_rows: list[dict[str, Any]] = []
        for p in admitted:
            for ap in p["atomic_propositions"]:
                ap_source_mappings = verified_source_mappings_for_ap(p, ap)
                item = aps.setdefault(ap, {
                    "definition": p["ap_definitions"].get(ap, ap.replace("_", " ")),
                    "properties": [], "source_mappings": [],
                })
                item["properties"].append(p["id"])
                item["source_mappings"].extend({"property_id": p["id"], **mapping}
                                                for mapping in ap_source_mappings)
                hook_rows.append({
                    "property_id": p["id"], "atomic_proposition": ap,
                    "event_predicate": p["ap_definitions"].get(ap, ""),
                    "correlation_key": p["correlation_key"],
                    "projection_rule": p["projection_rule"],
                    "monitor_instantiation": p["monitor_instantiation"],
                    "source_mappings": ap_source_mappings,
                    "auxiliary_source_urls": {
                        key: value for key, value in p.items()
                        if (key.endswith("_source_url") or key.endswith("_source_urls"))
                        and key != "source_url" and str(value).strip()
                    },
                    "instrumentation_timing": p["instrumentation_timing"],
                    "observability": p["observability"],
                })
        ap_document = {
            "protocol": display, "time_unit": "integer_millisecond", "missing_ap_value": False,
            "correlation_before_projection": True,
            "one_obligation_generation_per_monitor": True,
            "atomic_propositions": aps,
        }
        write_json(pdir / "atomic_proposition_map.json", ap_document)
        # JSON is valid YAML 1.2; retaining the identical serialization avoids
        # a non-standard runtime dependency while providing the planned name.
        write_json(pdir / "atomic_proposition_map.yaml", ap_document)
        write_csv(pdir / "instrumentation_hooks.csv", hook_rows,
                  list(hook_rows[0].keys()) if hook_rows else ["property_id", "atomic_proposition"])
        all_hook_rows.extend({"protocol": display, **row} for row in hook_rows)
        protocol_evidence = [x for x in evidence_index if x["protocol"] == display]
        evidence_document = {
            "protocol": display, "access_date": ACCESS_DATE,
            "standard_url_check_scope": "reachability only; section/excerpt/time semantics rely on the recorded review/audit and are not inferred from HTTP success",
            "screening_records": research_evidence,
            "admitted_property_sources": protocol_evidence,
        }
        write_json(pdir / "evidence_manifest.json", evidence_document)
        write_json(pdir / "evidence_manifest.yaml", evidence_document)
        excluded_lines = [f"# {display} 排除与待修候选", ""]
        excluded_lines.extend(staging_exclusions)
        if rejected:
            excluded_lines += ["## 自动质量门拒绝", ""]
            for p in rejected:
                excluded_lines += [f'- `{p.get("id", "NO_ID")}` {p.get("title", "")}: `{", ".join(p["rejection_reasons"])}`']
        if len(excluded_lines) == 2:
            excluded_lines.append("未记录额外排除项。")
        (pdir / "excluded_properties.md").write_text("\n".join(excluded_lines) + "\n", encoding="utf-8")
        protocol_summaries.append({
            "protocol": display, "slug": slug, "proposed": len(grouped.get(slug, [])),
            "admitted": len(admitted), "rejected": len(rejected),
            "build_pass": sum(r.get("build_ok") is True for r in validation_rows),
            "oracle_pass": sum(r.get("expected_oracle_ok") is True for r in validation_rows),
            "screening_records": len(research_evidence),
            "screened_documents": screening_document_count(research_evidence),
            "recorded_exclusions": exclusion_candidate_count(staging_exclusions) + len(rejected),
            "status": "PASS" if admitted and not rejected else ("PARTIAL" if admitted else "NO_ADMITTED_PROPERTY"),
        })

    write_json(OUT / "all_protocol_properties.json", aggregate)
    write_csv(OUT / "all_protocol_properties.csv", aggregate, BASE_FIELDS + VALIDATION_FIELDS)
    write_csv(OUT / "protocol_summary.csv", protocol_summaries, list(protocol_summaries[0].keys()))
    write_csv(OUT / "source_verification_summary.csv", source_checks,
              list(source_checks[0].keys()) if source_checks else ["id"])
    write_csv(OUT / "instrumentation_hooks.csv", all_hook_rows,
              list(all_hook_rows[0].keys()) if all_hook_rows else ["protocol", "property_id", "atomic_proposition"])
    write_csv(OUT / "formula_validation_summary.csv", all_validation_rows,
              list(all_validation_rows[0].keys()) if all_validation_rows else ["protocol", "id", "status"])
    root_evidence = {
        "access_date": ACCESS_DATE,
        "standard_url_check_scope": "reachability only; normative truth is supported by protocol evidence ledgers and review dispositions",
        "sources": evidence_index,
    }
    write_json(OUT / "evidence_manifest.json", root_evidence)
    write_json(OUT / "evidence_manifest.yaml", root_evidence)
    write_json(OUT / "load_errors.json", load_errors)

    index = ["# 多协议 MITL 真实性质索引", "",
             "主目录只统计同时通过正式规范、固定源码、非 punctual MightyPPL 构造和正反 trace oracle 的条目。", "",
             "| 协议 | 候选 | 收录 | 自动拒绝 | 已记录排除 | 状态 | 目录 |", "|---|---:|---:|---:|---:|---|---|"]
    for row in protocol_summaries:
        index.append(f'| {row["protocol"]} | {row["proposed"]} | {row["admitted"]} | {row["rejected"]} | {row["recorded_exclusions"]} | {row["status"]} | [{row["slug"]}](./{row["slug"]}/mitl_property_catalog.md) |')
    index += ["", f"合计收录：**{len(aggregate)}** 条。所有人工审核状态仍为 `PENDING`。", ""]
    (OUT / "protocol_catalog_index.md").write_text("\n".join(index), encoding="utf-8")

    completeness = [
        "# 多协议提取完整性审计", "",
        "本轮“全部”指：对锁定版本中可公开核验的数值定时器、超时、重传、保活、租约、会话和定时状态迁移进行筛查，并收录所有通过质量门的不同义务；不表示协议的所有非时间条款。", "",
        "| 协议 | 筛查记录 | 规范/文档数 | 初始候选 | 收录 | 质量门拒绝 | 已记录其他排除 |", "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in protocol_summaries:
        other_exclusions = max(0, int(row["recorded_exclusions"]) - int(row["rejected"]))
        completeness.append(
            f'| {row["protocol"]} | {row["screening_records"]} | {row["screened_documents"]} | {row["proposed"]} | {row["admitted"]} | {row["rejected"]} | {other_exclusions} |'
        )
    completeness += [
        "", "## 解释边界", "",
        "- 0 条收录也是有效结论：它表示该协议已筛查，但没有候选同时具备公开规范时间锚点、固定源码 hook、当前非 punctual 公式和决定性 trace。",
        "- 实现 profile 条目不会被提升为协议普适常数；软规范与 MUST/SHALL 分开标注。",
        "- 质量门拒绝和无数值/无源码/版本不匹配候选均保留在每个协议的 `excluded_properties.md`。",
        "- 当前重叠触发限制及一实例一 generation 契约见 `../semantic_exclusions.md`。",
        "- 所有主目录条目仍需用户人工审核，不能在审核前直接写成论文最终合规结论。", "",
    ]
    (OUT / "extraction_completeness_report.md").write_text("\n".join(completeness), encoding="utf-8")

    audit_counts = Counter(str(p.get("independent_audit_status", "UNSPECIFIED")) for p in aggregate)
    audit_lines = [
        "# 独立审计状态汇总", "",
        "该表描述最终准入卡片的审计状态；`PENDING` 人工签字仍是另一道门。", "",
        "| 状态 | 准入条数 |", "|---|---:|",
    ]
    for status, count in sorted(audit_counts.items()):
        audit_lines.append(f"| `{status}` | {count} |")
    audit_rejects = [p for p in all_rejected if "INDEPENDENT_AUDIT_REJECT" in p.get("rejection_reasons", [])]
    audit_lines += ["", "## 被独立审计否决的候选", ""]
    if audit_rejects:
        for p in audit_rejects:
            audit_lines.append(
                f'- `{p.get("id")}`（{p.get("protocol")}）：{p.get("independent_audit_note") or "见协议排除表"}'
            )
    else:
        audit_lines.append("无。")
    audit_lines += [
        "", "## 审计报告", "",
        "- `../_audit/transport_security_audit.md`",
        "- `../_audit/industrial_audit.md`",
        "- `../_audit/smtp_audit.md`",
        "- `../_audit/sip_catalog_audit.md`",
        "- `../semantic_exclusions.md`（重叠触发回归与接入契约）", "",
    ]
    (OUT / "independent_audit_summary.md").write_text("\n".join(audit_lines), encoding="utf-8")

    # Hash final non-validation deliverables for recovery/reproduction.
    hashes = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "reproducibility_manifest.json":
            hashes.append({"path": str(path.relative_to(OUT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    input_hashes = []
    input_candidates = [
        Path(__file__), BASE / "validate_multi_protocol_outputs.py",
        BASE / "verify_research_evidence.py", BASE / "mitl_property_catalog.json",
        BASE / "evidence_manifest.yaml",
    ]
    if STAGING.exists():
        input_candidates.extend(path for path in STAGING.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    for path in sorted(set(input_candidates)):
        if path.is_file():
            input_hashes.append({
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            })
    write_json(OUT / "reproducibility_manifest.json", {
        "generator": "generate_multi_protocol_catalog.py", "access_date": ACCESS_DATE,
        "protocol_count": len(PROTOCOLS), "admitted_property_count": len(aggregate),
        "semantics": "mathematical standard MITL plus MightyPPL weak finite outer G*; pointwise absolute integer milliseconds; flatten; missing AP=false; one obligation generation per monitor",
        "validation_modes": ["build-only symbolic", "positive symbolic", "negative symbolic", "positive concrete", "negative concrete", "all additional negative traces in symbolic and concrete"],
        "known_semantic_regression": "../semantic_regressions/overlapping_trigger; production adapter must never place overlapping trigger generations in one monitor word",
        "tamonitor": str(TAMONITOR.relative_to(ROOT)),
        "tamonitor_sha256": hashlib.sha256(TAMONITOR.read_bytes()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "load_errors": load_errors, "inputs": input_hashes, "artifacts": hashes,
    })
    print(f"protocols={len(PROTOCOLS)} proposed={sum(len(v) for v in grouped.values())} admitted={len(aggregate)} rejected={sum(x['rejected'] for x in protocol_summaries)} load_errors={len(load_errors)}")
    return 0 if not load_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
