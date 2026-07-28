#!/usr/bin/env python3
"""Verify one emitted LTL-Fuzzer portability-probe bundle.

This verifier checks exact bytes and the probe-specific semantic contract.  It
does not substitute for the independent RIFT M5 certificate verifier and does
not claim runtime AP-flip evidence or human-reviewed gold accuracy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


EXPECTED_ANALYZER = (
    "75cc7f4d74d8507dacd4e2919393406d15e867d8422efec2519c89a344327f0a"
)
EXPECTED_CORE = "be454d86de57170968a9758ab349620685e2b69ef4f467c05e3df6026c41a6d8"
EXPECTED_SCHEMA = "4e170722f4b981faf54c7bc561cd6ac710856808d95c0c5c4f0549f53c15f9aa"
EXPECTED_MODEL_PACK_FILE = (
    "c532d54ab0e3e2cb62d82393164aa5497be8e6a39cc9c1e60c516a8a39266da0"
)
EXPECTED_MODEL_PACK_SEMANTIC = (
    "d042fbbfeec0d2a50eb5f447a0ca7b684b31fb305447ff858dc8c09e159e132d"
)
EXPECTED_ARGC_USR = "c:main.cc@156@F@main#I#**C#@argc"
EXPECTED_AP = "ap_ltl_fuzzer_argc_lt_two"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--property", type=pathlib.Path, required=True)
    parser.add_argument("--executor", type=pathlib.Path, required=True)
    parser.add_argument("--ast-evidence", type=pathlib.Path, required=True)
    parser.add_argument("--expected-translation-units", type=int, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    options = parser.parse_args()

    root = options.output_dir.resolve(strict=True)
    documents = {
        name: load(root / name)
        for name in [
            "semantic_index.json",
            "ap_bindings.json",
            "ap_influence_cones.json",
            "contextual_influence_graph.json",
            "model_fact_overlay.json",
            "predicate_occurrence_bindings.json",
            "frontier_candidates.json",
            "fuzzable_frontier.json",
            "mutation_recipes.json",
            "recipe_replay_obligations.json",
            "m5_analysis_certificate.json",
        ]
    }
    index = documents["semantic_index.json"]
    bindings = documents["ap_bindings.json"]
    overlay = documents["model_fact_overlay.json"]
    occurrences = documents["predicate_occurrence_bindings.json"]
    candidates = documents["frontier_candidates.json"]
    frontier = documents["fuzzable_frontier.json"]
    recipes = documents["mutation_recipes.json"]
    obligations = documents["recipe_replay_obligations.json"]
    certificate = documents["m5_analysis_certificate.json"]
    property_ir = load(options.property.resolve(strict=True))
    executor = load(options.executor.resolve(strict=True))
    ast_evidence = load(options.ast_evidence.resolve(strict=True))

    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, observed: Any) -> None:
        checks.append(
            {"check_id": check_id, "passed": bool(passed), "observed": observed}
        )

    check(
        "translation-unit-count",
        len(index["translation_units"]) == options.expected_translation_units,
        len(index["translation_units"]),
    )
    check(
        "analyzer-identity",
        certificate["analyzer"]["binary_sha256"] == EXPECTED_ANALYZER,
        certificate["analyzer"]["binary_sha256"],
    )
    check(
        "core-identity",
        certificate["build_manifest"]["production_core_sha256"] == EXPECTED_CORE,
        certificate["build_manifest"]["production_core_sha256"],
    )
    check(
        "schema-identity",
        certificate["build_manifest"]["schema_bundle_sha256"] == EXPECTED_SCHEMA,
        certificate["build_manifest"]["schema_bundle_sha256"],
    )
    packs = certificate["model_packs"]
    check(
        "generic-posix-pack-only",
        len(packs) == 1
        and packs[0]["model_pack_id"] == "pack.platform.posix-lp64"
        and packs[0]["sha256"] == EXPECTED_MODEL_PACK_FILE
        and packs[0]["semantic_sha256"] == EXPECTED_MODEL_PACK_SEMANTIC,
        [
            {
                "model_pack_id": pack["model_pack_id"],
                "sha256": pack["sha256"],
                "semantic_sha256": pack["semantic_sha256"],
            }
            for pack in packs
        ],
    )
    check(
        "property-bytes-bound",
        certificate["m4_commitments"]["typed_property_ir"]["sha256"]
        == sha256_file(options.property),
        certificate["m4_commitments"]["typed_property_ir"]["sha256"],
    )
    check(
        "executor-bytes-bound",
        certificate["executor_manifest"]["sha256"]
        == sha256_file(options.executor),
        certificate["executor_manifest"]["sha256"],
    )
    check(
        "probe-label",
        property_ir["formula_text"].startswith("PORTABILITY_PROBE_NOT_REQUIREMENT:")
        and ast_evidence["status"] == "PORTABILITY_PROBE_NOT_REQUIREMENT",
        property_ir["formula_text"],
    )
    check(
        "executor-only-argc",
        [capability["action_schema_id"] for capability in executor["capabilities"]]
        == ["action.posix.argc"],
        [capability["action_schema_id"] for capability in executor["capabilities"]],
    )

    exact_occurrences = [
        occurrence
        for occurrence in occurrences["occurrences"]
        if occurrence["ap_id"] == EXPECTED_AP
        and occurrence["selector_id"] == "sel.ltl-fuzzer.main.argc-occurrence"
        and occurrence["resolution"] == "EXACT"
        and occurrence["certainty"] == "must"
    ]
    check("one-exact-argc-occurrence", len(exact_occurrences) == 1, len(exact_occurrences))
    if exact_occurrences:
        occurrence = exact_occurrences[0]
        check(
            "occurrence-clang-usr",
            occurrence["referenced_usr"] == EXPECTED_ARGC_USR,
            occurrence["referenced_usr"],
        )
        check(
            "occurrence-type",
            occurrence["value_type"]
            == {"kind": "integer", "canonical": "int", "bit_width": 32, "signed": True},
            occurrence["value_type"],
        )
        check(
            "ast-to-index-usr-closure",
            ast_evidence["property_selector_usr"]["expected"]
            == occurrence["referenced_usr"],
            ast_evidence["property_selector_usr"]["expected"],
        )

    state_bindings = [
        binding
        for binding in bindings["bindings"]
        if binding["ap_id"] == EXPECTED_AP and binding["role"] == "state"
    ]
    state_nodes = {
        node_id
        for binding in state_bindings
        for candidate in binding["candidates"]
        if candidate["status"] == "CONFIRMED"
        for node_id in candidate["semantic_node_refs"]
    }
    argc_attachments = [
        attachment
        for attachment in overlay["boundary_attachments"]
        if next(
            action
            for action in overlay["external_actions"]
            if action["external_action_id"] == attachment["external_action_id"]
        )["action_schema_id"]
        == "action.posix.argc"
    ]
    check("one-argc-boundary", len(argc_attachments) == 1, len(argc_attachments))
    if argc_attachments:
        check(
            "binding-boundary-identity",
            argc_attachments[0]["semantic_node_id"] in state_nodes,
            {
                "boundary": argc_attachments[0]["semantic_node_id"],
                "state_nodes": sorted(state_nodes),
            },
        )

    argc_candidates = [
        candidate
        for candidate in candidates["candidates"]
        if candidate["ap_id"] == EXPECTED_AP
        and candidate["action"]["action_schema_id"] == "action.posix.argc"
    ]
    check("one-argc-candidate", len(argc_candidates) == 1, len(argc_candidates))
    if argc_candidates:
        candidate = argc_candidates[0]
        check(
            "argc-actionable-modelled-witness",
            candidate["disposition"] == "ACTIONABLE"
            and candidate["evidence"]["reachability"] == "MODELLED_WITNESS"
            and len(candidate["witnesses"]) == 1
            and candidate["witnesses"][0]["compatibility"] == "COMPATIBLE",
            {
                "disposition": candidate["disposition"],
                "reachability": candidate["evidence"]["reachability"],
                "witnesses": len(candidate["witnesses"]),
            },
        )
    check(
        "frontier-exact-projection",
        len(frontier["actions"]) == 1
        and frontier["actions"][0]["action"]["action_schema_id"]
        == "action.posix.argc",
        [action["action"]["action_schema_id"] for action in frontier["actions"]],
    )

    probe_recipes = [recipe for recipe in recipes["recipes"] if recipe["ap_id"] == EXPECTED_AP]
    check("one-probe-recipe", len(probe_recipes) == 1, len(probe_recipes))
    if probe_recipes:
        recipe = probe_recipes[0]
        mutation = recipe["action_mutations"][0]
        check(
            "local-flip-sat-external-direction-withheld",
            recipe["status"] == "HEURISTIC"
            and recipe["solver_query"]["outcome"] == "SAT"
            and mutation["mutation_kind"] == "UNKNOWN"
            and mutation["direction"] == "UNKNOWN"
            and mutation["suggested_values"] == []
            and any(
                "non-identity transfer" in reason
                for reason in mutation["unknown_reasons"]
            ),
            {
                "status": recipe["status"],
                "solver_outcome": recipe["solver_query"]["outcome"],
                "mutation_kind": mutation["mutation_kind"],
                "direction": mutation["direction"],
                "suggested_values": mutation["suggested_values"],
            },
        )
    check(
        "one-replay-obligation",
        len(obligations["obligations"]) == 1,
        len(obligations["obligations"]),
    )

    byte_checks = 0
    for commitment in certificate["m4_commitments"].values():
        path = pathlib.Path(commitment["path"])
        check_id = f"m4-byte-closure:{commitment['kind']}"
        check(check_id, path.is_file() and sha256_file(path) == commitment["sha256"], commitment["sha256"])
        byte_checks += 1
    for output in certificate["outputs"]:
        path = pathlib.Path(output["path"])
        check_id = f"m5-byte-closure:{output['kind']}"
        check(check_id, path.is_file() and sha256_file(path) == output["sha256"], output["sha256"])
        byte_checks += 1

    failures = [item for item in checks if not item["passed"]]
    report = {
        "schema_version": "rift.portability.ltl-fuzzer.verification.v1",
        "status": "PASS" if not failures else "FAIL",
        "claim": "PORTABILITY_PROBE_NOT_REQUIREMENT",
        "output_dir": str(root),
        "expected_translation_units": options.expected_translation_units,
        "checks": len(checks),
        "byte_closure_checks": byte_checks,
        "failures": len(failures),
        "check_results": checks,
        "claim_boundary": {
            "supported": [
                "The frozen analyzer consumed this compile-database projection and emitted a byte-closed M5 bundle.",
                "The exact argc predicate occurrence and generic POSIX argc boundary meet in one compatible modelled witness.",
                "The external direction remains withheld despite a selector-local SAT flip, preserving the non-identity-transfer boundary."
            ],
            "not_supported": [
                "Human-reviewed binding or influence accuracy.",
                "Observed runtime AP flip or recipe replay.",
                "Full-project portability when any translation unit was omitted.",
                "Mutation-direction correctness or fuzzing gain."
            ]
        }
    }
    options.report.parent.mkdir(parents=True, exist_ok=True)
    options.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"{report['status']} checks={report['checks']} failures={report['failures']} "
        f"output={options.report}"
    )
    if failures:
        for failure in failures:
            print(f"FAIL {failure['check_id']}: {failure['observed']!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
