#!/usr/bin/env python3
"""Validate Milestone-5 source identities, compile DB coverage and observations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark"
SYSTEMS = {
    "ArduPilot": {
        "commit": "8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e",
        "repo": ROOT / "baseline" / "ardupilot",
        "prefix": "baseline/ardupilot/",
        "compile_db": ROOT / "baseline" / "ardupilot" / "build" / "sitl" / "compile_commands.json",
        "permalink": "https://github.com/ArduPilot/ardupilot/blob/",
    },
    "PX4": {
        "commit": "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
        "repo": ROOT / "baseline" / "px4",
        "prefix": "baseline/px4/",
        "compile_db": ROOT / "baseline" / "px4" / "build" / "px4_sitl_default" / "compile_commands.json",
        "permalink": "https://github.com/PX4/PX4-Autopilot/blob/",
    },
}


def fail(message: str) -> None:
    raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_files(path: Path) -> set[Path]:
    result = set()
    for entry in json.loads(path.read_text(encoding="utf-8")):
        file_path = Path(entry["file"])
        if not file_path.is_absolute():
            file_path = Path(entry["directory"]) / file_path
        result.add(file_path.resolve())
    return result


def symbol_tokens(symbol: str) -> list[str]:
    ignored = {"true", "false", "return", "const", "auto", "void", "float", "double", "uint32_t", "int"}
    return [token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", symbol) if token not in ignored and len(token) > 1]


def run_clangd(files: list[Path], compile_dir: Path) -> list[dict]:
    clangd = Path("/usr/lib/llvm-14/bin/clangd")
    if not clangd.is_file():
        return [{"file": str(path), "status": "NOT_RUN", "reason": "clangd unavailable"} for path in files]
    rows = []
    for path in files:
        process = subprocess.run(
            [str(clangd), f"--check={path}", f"--compile-commands-dir={compile_dir}", "--log=error"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
        )
        diagnostics = [line for line in process.stdout.splitlines() if line.strip()]
        tweak_only = bool(diagnostics) and all("tweak:" in line and "==> FAIL:" in line for line in diagnostics)
        check_status = "PASS" if process.returncode == 0 else ("PASS_WITH_TWEAK_DIAGNOSTICS" if tweak_only else "FAIL")
        rows.append({"file": str(path.relative_to(ROOT)), "status": check_status, "exit_code": process.returncode, "diagnostic_tail": "\n".join(diagnostics[-8:])})
        if check_status == "FAIL":
            fail(f"clangd parse failed for {path}: {process.stdout[-1000:]}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-clangd", action="store_true")
    args = parser.parse_args()
    property_schema = json.loads((BENCHMARK / "schemas" / "property.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(property_schema, format_checker=FormatChecker())
    message_rows = list(csv.DictReader((BENCHMARK / "mavlink_catalog" / "messages_and_fields.csv").open(encoding="utf-8")))
    message_fields = {(r["system"], r["message_name"], r["field_name"]): int(r["message_id"]) for r in message_rows}
    message_ids = {(r["system"], r["message_name"]): int(r["message_id"]) for r in message_rows}
    summary = {"schema_version": "1.0", "systems": {}, "total_properties": 0, "total_aps": 0, "total_bindings": 0, "total_observations": 0}
    for system, config in SYSTEMS.items():
        actual_commit = subprocess.check_output(["git", "-C", str(config["repo"]), "rev-parse", "HEAD"], text=True).strip()
        if actual_commit != config["commit"]:
            fail(f"{system}: HEAD drift")
        compile_db = config["compile_db"]
        if not compile_db.is_file():
            fail(f"{system}: compile database missing")
        compiled = compile_files(compile_db)
        catalog = json.loads((BENCHMARK / system / "property_catalog.json").read_text(encoding="utf-8"))
        binding_ids = set()
        selected_tus: set[Path] = set()
        uncovered_source_units: set[Path] = set()
        ap_statuses = {}
        binding_count = 0
        observation_count = 0
        for prop in catalog["properties"]:
            errors = list(validator.iter_errors(prop))
            if errors:
                fail(f"{prop.get('property_id')}: schema: {errors[0].message}")
            if prop["implementation_satisfaction"] != "NOT_ASSESSED" or prop["status"] == "ACCEPTED":
                fail(f"{prop['property_id']}: premature conformance/acceptance")
            for item in prop["atomic_propositions"]:
                ap_statuses[item["status"]] = ap_statuses.get(item["status"], 0) + 1
                for binding in item["source_bindings"]:
                    binding_count += 1
                    if binding["binding_id"] in binding_ids:
                        fail(f"duplicate binding id {binding['binding_id']}")
                    binding_ids.add(binding["binding_id"])
                    if binding["commit"] != config["commit"]:
                        fail(f"{binding['binding_id']}: commit mismatch")
                    if not binding["file"].startswith(config["prefix"]):
                        fail(f"{binding['binding_id']}: wrong source prefix")
                    path = ROOT / binding["file"]
                    if not path.is_file():
                        fail(f"{binding['binding_id']}: missing file")
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                    line = binding["line"]
                    if line < 1 or line > len(lines):
                        fail(f"{binding['binding_id']}: invalid line {line}")
                    window = "\n".join(lines[max(0, line - 5) : min(len(lines), line + 4)])
                    tokens = symbol_tokens(binding["symbol"])
                    if tokens and not any(token in window for token in tokens):
                        fail(f"{binding['binding_id']}: no symbol token near {binding['file']}:{line}: {tokens}")
                    expected_link = f"{config['permalink']}{config['commit']}/{binding['file'][len(config['prefix']):]}#L{line}"
                    if expected_link not in binding["evidence"]:
                        fail(f"{binding['binding_id']}: fixed permalink missing")
                    if path.suffix in {".c", ".cc", ".cpp", ".cxx"}:
                        if path.resolve() in compiled:
                            selected_tus.add(path.resolve())
                        else:
                            # PX4 parameter metadata .c files and a few generated-input
                            # sources are consumed by build generators rather than compiled
                            # as ordinary translation units.  Preserve this distinction.
                            uncovered_source_units.add(path.resolve())
                for obs in item["mavlink_observations"]:
                    observation_count += 1
                    key = (system, obs["message"])
                    if key not in message_ids or message_ids[key] != obs["message_id"]:
                        fail(f"{item['ap_id']}: invalid message identity {obs['message']}")
                    if obs["field"] is not None and (system, obs["message"], obs["field"]) not in message_fields:
                        fail(f"{item['ap_id']}: invalid field {obs['message']}.{obs['field']}")
                    if obs["support"] == "RUNTIME_OBSERVED":
                        fail(f"{item['ap_id']}: runtime observation was fabricated")
        clangd_rows = run_clangd(sorted(selected_tus), compile_db.parent) if args.run_clangd else []
        result = {
            "firmware_commit": config["commit"],
            "compile_database": str(compile_db.relative_to(ROOT)),
            "compile_database_sha256": sha256(compile_db),
            "compile_database_entries": len(json.loads(compile_db.read_text(encoding="utf-8"))),
            "selected_translation_units": len(selected_tus),
            "source_units_not_direct_compile_entries": [str(path.relative_to(ROOT)) for path in sorted(uncovered_source_units)],
            "properties": len(catalog["properties"]),
            "atomic_propositions": sum(len(p["atomic_propositions"]) for p in catalog["properties"]),
            "ap_statuses": dict(sorted(ap_statuses.items())),
            "source_bindings": binding_count,
            "mavlink_observations": observation_count,
            "clangd_checks": clangd_rows,
        }
        out = BENCHMARK / system / "validation" / "source_binding_validation.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary["systems"][system] = result
        summary["total_properties"] += result["properties"]
        summary["total_aps"] += result["atomic_propositions"]
        summary["total_bindings"] += binding_count
        summary["total_observations"] += observation_count
    summary_path = BENCHMARK / "extraction_runs" / "milestone5" / "source_binding_validation_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: properties={summary['total_properties']} APs={summary['total_aps']} bindings={summary['total_bindings']} observations={summary['total_observations']} clangd={args.run_clangd}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
