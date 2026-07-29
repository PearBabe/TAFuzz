#!/usr/bin/env python3
"""Validate the frozen RIFT-M1 benchmark-first, pre-core gate.

The default validation is intentionally read-only.  It verifies all aggregate
claims and anchored evidence, then invokes the small/read-only child validators.
It does not download artifacts or rebuild libcoap, ArduPilot, or SVF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
MANIFEST_PATH = HERE / "m1_manifest.json"
STATIC_ANALYSIS_ROOT = WORKSPACE / "src" / "StaticAnalysis"

STATUS_VOCABULARY = {"PASS", "PARTIAL", "BLOCKED", "NOT_RUN"}
EXPECTED_STEP_STATUSES = {
    "ltl_original_automata_component": "PASS",
    "ltl_public_problem1": "PASS",
    "ltl_full_instrumented_campaign": "NOT_RUN",
    "ltl_ap_target_import": "PARTIAL",
    "pgfuzz_policy_maps": "PARTIAL",
    "moonshine_rw_dependency": "PARTIAL",
    "fgs_original_artifact": "BLOCKED",
    "libcoap_clang18_three_run": "PASS",
    "ardupilot_clang18_build": "PASS",
    "svf_official_wpa_smoke": "PASS",
    "portability_contract_pre_core": "PASS",
    "static_analysis_empty": "PASS",
    "m2_gold_benchmark": "NOT_RUN",
}
EXPECTED_REQUIRED_STEPS = {
    "ltl_original_automata_component",
    "ltl_public_problem1",
    "libcoap_clang18_three_run",
    "ardupilot_clang18_build",
    "svf_official_wpa_smoke",
    "portability_contract_pre_core",
    "static_analysis_empty",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class ChildCommand:
    label: str
    command: tuple[str, ...]
    cwd: Path


class Checks:
    def __init__(self) -> None:
        self.passes: list[str] = []
        self.failures: list[str] = []
        self.child_output: list[tuple[str, str, str]] = []

    def expect(self, condition: bool, label: str, detail: str = "") -> None:
        if condition:
            self.passes.append(label)
        else:
            suffix = f": {detail}" if detail else ""
            self.failures.append(f"{label}{suffix}")

    def run_child(self, child: ChildCommand, timeout: int) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            result = subprocess.run(
                list(child.command),
                cwd=child.cwd,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            self.failures.append(f"child validator {child.label}: {error}")
            return

        self.child_output.append((child.label, result.stdout, result.stderr))
        self.expect(
            result.returncode == 0,
            f"child validator {child.label}",
            f"exit={result.returncode}; stdout={result.stdout[-1200:]!r}; "
            f"stderr={result.stderr[-1200:]!r}",
        )


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_workspace_path(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    try:
        path.relative_to(WORKSPACE)
    except ValueError as error:
        raise ValueError(f"path escapes workspace: {relative}") from error
    return path


def step_map(manifest: dict[str, Any], checks: Checks) -> dict[str, dict[str, Any]]:
    steps = manifest.get("steps")
    checks.expect(isinstance(steps, list), "manifest steps is a list")
    if not isinstance(steps, list):
        return {}

    mapped: dict[str, dict[str, Any]] = {}
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            checks.failures.append(f"step[{index}] is not an object")
            continue
        identifier = step.get("id")
        if not isinstance(identifier, str) or not identifier:
            checks.failures.append(f"step[{index}] has no id")
            continue
        if identifier in mapped:
            checks.failures.append(f"duplicate step id: {identifier}")
            continue
        mapped[identifier] = step
        checks.expect(
            step.get("status") in STATUS_VOCABULARY,
            f"step {identifier} uses normalized status",
            repr(step.get("status")),
        )
        checks.expect(
            isinstance(step.get("claim_boundary"), str)
            and bool(step["claim_boundary"].strip()),
            f"step {identifier} has an exact claim boundary",
        )
        evidence = step.get("evidence")
        checks.expect(
            isinstance(evidence, list)
            and all(isinstance(item, str) and item for item in evidence),
            f"step {identifier} evidence list is well formed",
        )
        if isinstance(evidence, list):
            for relative in evidence:
                if not isinstance(relative, str) or not relative:
                    continue
                try:
                    path = resolve_workspace_path(HERE, relative)
                    checks.expect(path.exists(), f"step evidence exists: {relative}")
                except ValueError as error:
                    checks.failures.append(str(error))
    return mapped


def validate_manifest_and_anchors(
    manifest: dict[str, Any], checks: Checks
) -> dict[str, dict[str, Any]]:
    checks.expect(
        manifest.get("schema_version") == "rift.m1.aggregate-manifest.v1",
        "aggregate schema version",
        repr(manifest.get("schema_version")),
    )
    checks.expect(manifest.get("milestone") == "RIFT-M1", "milestone identity")
    checks.expect(
        set(manifest.get("status_vocabulary", {})) == STATUS_VOCABULARY,
        "status vocabulary is exactly PASS/PARTIAL/BLOCKED/NOT_RUN",
    )

    steps = step_map(manifest, checks)
    checks.expect(
        set(steps) == set(EXPECTED_STEP_STATUSES),
        "aggregate step identity set",
        f"expected={sorted(EXPECTED_STEP_STATUSES)}, got={sorted(steps)}",
    )
    for identifier, expected in EXPECTED_STEP_STATUSES.items():
        if identifier in steps:
            checks.expect(
                steps[identifier].get("status") == expected,
                f"step {identifier} status={expected}",
                repr(steps[identifier].get("status")),
            )

    gate = manifest.get("gate_policy", {})
    required = set(gate.get("required_pass_steps", []))
    checks.expect(
        required == EXPECTED_REQUIRED_STEPS,
        "required gate step set",
        f"expected={sorted(EXPECTED_REQUIRED_STEPS)}, got={sorted(required)}",
    )
    checks.expect(gate.get("overall_status") == "PASS", "declared gate status PASS")
    checks.expect(
        all(steps.get(item, {}).get("status") == "PASS" for item in required),
        "all required steps are declared PASS",
    )
    checks.expect(
        steps.get("fgs_original_artifact", {}).get("status") == "BLOCKED",
        "FGS remains BLOCKED",
    )
    checks.expect(
        steps.get("moonshine_rw_dependency", {}).get("status") == "PARTIAL"
        and steps.get("pgfuzz_policy_maps", {}).get("status") == "PARTIAL",
        "MoonShine and PGFuzz remain PARTIAL",
    )
    checks.expect(
        steps.get("ltl_full_instrumented_campaign", {}).get("status")
        == "NOT_RUN",
        "complete LTL-Fuzzer campaign remains NOT_RUN",
    )

    anchors = manifest.get("integrity_anchors")
    checks.expect(isinstance(anchors, list) and bool(anchors), "integrity anchors exist")
    seen_paths: set[str] = set()
    if isinstance(anchors, list):
        for index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict):
                checks.failures.append(f"integrity anchor[{index}] is not an object")
                continue
            relative = anchor.get("path")
            expected = anchor.get("sha256")
            if not isinstance(relative, str) or not relative:
                checks.failures.append(f"integrity anchor[{index}] path is invalid")
                continue
            checks.expect(relative not in seen_paths, f"unique integrity anchor: {relative}")
            seen_paths.add(relative)
            checks.expect(
                isinstance(expected, str) and SHA256_PATTERN.fullmatch(expected) is not None,
                f"integrity anchor digest format: {relative}",
            )
            try:
                path = resolve_workspace_path(HERE, relative)
            except ValueError as error:
                checks.failures.append(str(error))
                continue
            if not path.is_file():
                checks.failures.append(f"integrity anchor missing: {relative}")
                continue
            if isinstance(expected, str):
                checks.expect(
                    sha256(path) == expected,
                    f"integrity anchor hash: {relative}",
                    f"expected={expected}, got={sha256(path)}",
                )
    return steps


def validate_literature(checks: Checks) -> None:
    manifest = load_json(HERE / "literature_baselines" / "reproduction_manifest.json")
    gate = manifest["gate_assessment"]
    checks.expect(
        gate["original_ccf_a_artifact_component_successfully_executed"] is True,
        "literature original component gate",
    )
    checks.expect(
        gate["complete_original_end_to_end_fuzz_campaign_executed"] is False,
        "literature complete campaign non-claim",
    )

    ltl = manifest["artifacts"]["ltl_fuzzer"]
    named_steps = {step["name"]: step for step in ltl["steps"]}
    automata = named_steps["official_automata_component_on_public_property"]
    problem = named_steps["public_rers_problem1_execution"]
    complete = named_steps["complete_instrumented_fuzz_campaign"]
    checks.expect(
        automata["status"] == "PASS"
        and automata["compile_exit_code"] == 0
        and automata["run_exit_code"] == 0,
        "LTL original Automata component oracle",
    )
    checks.expect(
        "not an end-to-end" in automata["claim_boundary"],
        "LTL Automata non-E2E boundary",
    )
    checks.expect(
        problem["status"] == "PASS" and problem["observed"]["exit_code"] == 0,
        "LTL public Problem1 oracle",
    )
    checks.expect(
        complete["status"] == "BLOCKED_RECORDED",
        "LTL instrumentation blocker retained",
    )
    target_import = ltl["target_tuple_import"]
    checks.expect(
        (target_import["total"], target_import["exact"], target_import["unresolved"])
        == (49, 46, 3),
        "LTL AP tuple counts",
    )

    pgfuzz = manifest["artifacts"]["pgfuzz"]["import"]
    checks.expect(pgfuzz["status"] == "SILVER_ONLY", "PGFuzz silver-only boundary")
    checks.expect(
        (
            pgfuzz["paper_policy_count"],
            pgfuzz["policies_with_public_map"],
            pgfuzz["policies_without_public_map"],
        )
        == (56, 51, 5),
        "PGFuzz policy/map counts",
    )

    moonshine = manifest["artifacts"]["moonshine"]
    checks.expect(moonshine["overall_status"] == "PARTIAL", "MoonShine partial boundary")
    checks.expect(
        moonshine["official_precomputed_map"]["status"] == "PASS"
        and moonshine["official_precomputed_map"]["contains_mlockall_to_msync"] is True,
        "MoonShine official map edge",
    )
    reproduction = moonshine["published_rule_reproduction"]
    checks.expect(
        reproduction["status"] == "PASS"
        and reproduction["kind"]
        == "FAITHFUL_CLANG_MICRO_REPRODUCTION_NOT_ORIGINAL_SMATCH_EXTRACTOR"
        and reproduction["intersection"] == ["vm_area_struct.vm_flags"]
        and reproduction["negative_control_intersection"] == [],
        "MoonShine bounded read/write reproduction",
    )


def validate_fgs(checks: Checks) -> None:
    manifest = load_json(HERE / "fgs" / "artifact_manifest.json")
    result = manifest["result"]
    checks.expect(
        result["status"] == "BLOCKED_UPSTREAM_ARTIFACT_UNAVAILABLE",
        "FGS child status remains upstream-blocked",
    )
    checks.expect(
        all(
            result[field] is False
            for field in (
                "artifact_reproduced",
                "smoke_reproduced",
                "nist_reproduced",
                "implementation_recreated",
            )
        ),
        "FGS contains no fabricated success",
    )


def validate_libcoap(checks: Checks) -> None:
    result = load_json(HERE / "libcoap" / "observed_results.json")
    runs = result.get("runs", [])
    checks.expect(result.get("deterministic") is True, "libcoap deterministic flag")
    checks.expect(len(runs) == 3, "libcoap has exactly three runs")
    if len(runs) == 3:
        checks.expect(
            {run["translation_units"] for run in runs} == {38},
            "libcoap translation-unit count is stable",
        )
        checks.expect(
            {run["compile_database_sha256"] for run in runs}
            == {"3bf8dfee452381ad99363c17420d7e26e51ddf3755eda2c1109b10de8f30bc3a"},
            "libcoap compilation-database hash is stable",
        )
        checks.expect(
            {run["static_archive_sha256"] for run in runs}
            == {"efc44ed2ab109029494a2c56fb99cb5f6374cf05a3a8e7b4c5e5c52dbfe676c2"},
            "libcoap archive hash is stable",
        )
        checks.expect(
            {run["linked_bitcode_sha256"] for run in runs}
            == {"08ead6a83ce230fab63eb028c9eec21fb0b2e23e79dd6270c8ee78e43b12c61d"},
            "libcoap linked-bitcode hash is stable",
        )
    checks.expect(
        result.get("verification", {}).get("memoryssa") == "PASS"
        and result["verification"].get("memoryssa_printed_lines") == 117955,
        "libcoap MemorySSA stored oracle",
    )
    options = result.get("cmake_options", {})
    checks.expect(
        options.get("enable_dtls") is False
        and options.get("enable_examples") is False
        and options.get("enable_tests") is False,
        "libcoap compilation-only boundary",
    )


def validate_ardupilot(checks: Checks) -> None:
    manifest = load_json(HERE / "ardupilot" / "build_manifest.json")
    result = manifest["result"]
    checks.expect(result["status"] == "BUILD_BASELINE_SUCCESS", "ArduPilot build status")
    checks.expect(
        result["source_modified"] is False
        and result["clang18_configure"] == "PASS"
        and result["clang18_copter_build"] == "PASS"
        and result["clang18_binary_help_smoke"] == "PASS",
        "ArduPilot Clang 18 build oracles",
    )
    checks.expect(
        result["ap_binding_analysis"] == "NOT_RUN"
        and result["fuzz_experiment"] == "NOT_RUN"
        and result["sitl_scenario"] == "NOT_RUN",
        "ArduPilot analysis/SITL/fuzz non-claims",
    )
    compilation = manifest["clang18_isolated_build"]["compile_database"]
    checks.expect(
        compilation["entries"] == 1336
        and compilation["raw_sha256"]
        == "e3bde40c679fb01db8b16b22f75e225c50804fcf8ddf9b05b132fc159e0d9083",
        "ArduPilot Clang compilation database",
    )


def validate_svf(checks: Checks) -> None:
    manifest = load_json(HERE / "svf" / "artifact_manifest.json")
    checks.expect(
        manifest["status"] == "REPRODUCED_MINIMAL_WPA_SVFG_SMOKE",
        "SVF bounded reproduction status",
    )
    checks.expect(
        manifest["artifact"]["commit"]
        == "197a6590bd9c695a9c3daf52622dea912ef9a002"
        and manifest["artifact"]["source_patches"] == [],
        "SVF official source identity and no-patch boundary",
    )
    checks.expect(
        manifest["build"]["targets_completed"] == 124
        and manifest["build"]["llvm18_compatibility"] == "PASS_WITHOUT_SOURCE_PATCHES",
        "SVF LLVM 18 build oracle",
    )
    smoke = manifest["tests"]["wpa_smoke"]
    checks.expect(
        smoke["exit_code"] == 0
        and smoke["oracles"] == {"MAYALIAS": "PASS", "NOALIAS": "PASS"},
        "SVF WPA alias oracles",
    )
    checks.expect(
        smoke["memory_ssa"]["memory_regions"] == 8
        and smoke["svfg"]["nodes"] == 78
        and smoke["svfg"]["edges"] == 75,
        "SVF MemorySSA/SVFG counters",
    )
    checks.expect(
        manifest["tests"]["upstream_ctest"]["discovered_tests"] == 0,
        "SVF absent Test-Suite remains explicit",
    )
    checks.expect(
        manifest["tests"]["external_cmake_consumer"]["status"]
        == "COMPILE_LINK_PASS_AD_HOC_RUNTIME_DIAGNOSTIC_EXCLUDED",
        "SVF ad-hoc API diagnostic excluded from acceptance",
    )


def validate_portability_and_empty_core(checks: Checks) -> None:
    contract = load_json(WORKSPACE / "benchmark" / "rift" / "portability_contract.json")
    checks.expect(contract["contract_id"] == "RIFT-PORTABILITY-1", "portability contract identity")
    checks.expect(
        contract["status"] == "FROZEN_BEFORE_CORE_IMPLEMENTATION",
        "portability contract frozen pre-core",
    )
    checks.expect(
        contract["evaluation_gate"]["minimum_independent_projects"] == 3,
        "portability evaluation still requires three projects",
    )
    checks.expect(STATIC_ANALYSIS_ROOT.is_dir(), "src/StaticAnalysis directory exists")
    entries = sorted(STATIC_ANALYSIS_ROOT.rglob("*")) if STATIC_ANALYSIS_ROOT.is_dir() else []
    checks.expect(
        not entries,
        "src/StaticAnalysis is empty at the M1 pre-core gate",
        ", ".join(str(path.relative_to(WORKSPACE)) for path in entries[:20]),
    )


def child_commands() -> list[ChildCommand]:
    return [
        ChildCommand(
            "literature_baselines",
            (sys.executable, str(HERE / "literature_baselines" / "validate_literature_baselines.py")),
            WORKSPACE,
        ),
        ChildCommand(
            "fgs_checksums",
            ("sha256sum", "-c", "SHA256SUMS"),
            HERE / "fgs",
        ),
        ChildCommand(
            "ardupilot",
            (sys.executable, str(HERE / "ardupilot" / "validate.py")),
            WORKSPACE,
        ),
        ChildCommand(
            "svf",
            (sys.executable, str(HERE / "svf" / "validate_reproduction.py")),
            WORKSPACE,
        ),
        ChildCommand(
            "portability_pre_core",
            (
                sys.executable,
                str(WORKSPACE / "benchmark" / "rift" / "validate_portability_contract.py"),
                "--phase",
                "pre-core",
            ),
            WORKSPACE,
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the read-only RIFT-M1 aggregate reproduction gate."
    )
    parser.add_argument(
        "--stored-only",
        action="store_true",
        help="check manifests and frozen hashes without executing child validators; cannot certify a fresh TOTAL PASS",
    )
    parser.add_argument(
        "--child-timeout",
        type=int,
        default=180,
        help="timeout in seconds for each small/read-only child validator",
    )
    parser.add_argument(
        "--verbose-child-output",
        action="store_true",
        help="print captured stdout/stderr from successful child validators",
    )
    args = parser.parse_args()

    checks = Checks()
    try:
        manifest = load_json(MANIFEST_PATH)
        steps = validate_manifest_and_anchors(manifest, checks)
        validate_literature(checks)
        validate_fgs(checks)
        validate_libcoap(checks)
        validate_ardupilot(checks)
        validate_svf(checks)
        validate_portability_and_empty_core(checks)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        checks.failures.append(f"aggregate validation exception: {error}")
        steps = {}

    if not args.stored_only:
        for child in child_commands():
            checks.run_child(child, args.child_timeout)

    for identifier in EXPECTED_STEP_STATUSES:
        step = steps.get(identifier, {})
        print(
            f"STEP  {step.get('status', 'MISSING'):<8} {identifier}"
            f" gate_required={str(bool(step.get('gate_required'))).lower()}"
        )

    for child in child_commands():
        if args.stored_only:
            print(f"CHILD NOT_RUN  {child.label} (--stored-only)")
        else:
            passed = any(label == f"child validator {child.label}" for label in checks.passes)
            print(f"CHILD {'PASS' if passed else 'FAIL':<8} {child.label}")

    if args.verbose_child_output:
        for label, stdout, stderr in checks.child_output:
            print(f"--- child:{label}:stdout ---")
            print(stdout.rstrip())
            if stderr:
                print(f"--- child:{label}:stderr ---")
                print(stderr.rstrip())

    for failure in checks.failures:
        print(f"CHECK FAIL     {failure}")

    if args.stored_only and not checks.failures:
        print(
            f"TOTAL PARTIAL checks={len(checks.passes)} failures=0 "
            "reason=child_validators_NOT_RUN"
        )
        return 0

    if checks.failures:
        print(
            f"TOTAL FAIL checks={len(checks.passes)} "
            f"failures={len(checks.failures)}"
        )
        return 1

    print(
        f"TOTAL PASS required_steps={len(EXPECTED_REQUIRED_STEPS)}/"
        f"{len(EXPECTED_REQUIRED_STEPS)} checks={len(checks.passes)} failures=0"
    )
    print(
        "BOUNDARY RIFT is not implemented; FGS=BLOCKED; "
        "PGFuzz/MoonShine=PARTIAL; no fuzz-effectiveness claim."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
