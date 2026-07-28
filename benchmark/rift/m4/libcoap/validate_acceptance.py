#!/usr/bin/env python3
"""Audit the frozen COAP-TX-01 M4 acceptance bundle.

This validates artifact identity and internal consistency.  It deliberately
does not promote the provisional labels to human-arbitrated real-project gold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

import jsonschema


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: pathlib.Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def run_text(arguments: list[str], cwd: pathlib.Path | None = None) -> str:
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def predicate_selector_refs(node: object) -> set[str]:
    """Return every selector referenced by a typed predicate tree."""

    if not isinstance(node, dict):
        return set()
    refs: set[str] = set()
    selector_id = node.get("referenced_selector_id")
    if isinstance(selector_id, str):
        refs.add(selector_id)
    for operand in node.get("operands", []):
        refs.update(predicate_selector_refs(operand))
    return refs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=pathlib.Path,
        default=pathlib.Path("/tmp/tafuzz-rift-libcoap-fixed"),
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="also ask LLVM 18 to construct MemorySSA on the linked module",
    )
    args = parser.parse_args()

    failures: list[str] = []
    checks = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(message)

    manifest = load_json(HERE / "acceptance_manifest.json")
    typed_property_ir = load_json(HERE / "typed_property_ir.json")
    property_profile = load_json(HERE / "property_ir.json")
    labels = load_json(HERE / "provisional_influence_labels.json")
    assert isinstance(manifest, dict)
    assert isinstance(typed_property_ir, dict)
    assert isinstance(property_profile, dict)
    assert isinstance(labels, dict)

    schema_path = ROOT / manifest["inputs"]["typed_property_ir"]["schema_path"]
    common_schema_path = ROOT / "src/StaticAnalysis/schema/common.schema.json"
    typed_schema = load_json(schema_path)
    common_schema = load_json(common_schema_path)
    assert isinstance(typed_schema, dict)
    assert isinstance(common_schema, dict)
    resolver = jsonschema.RefResolver.from_schema(
        typed_schema,
        store={
            typed_schema["$id"]: typed_schema,
            common_schema["$id"]: common_schema,
        },
    )
    schema_errors = sorted(
        jsonschema.Draft7Validator(typed_schema, resolver=resolver).iter_errors(typed_property_ir),
        key=lambda error: list(error.absolute_path),
    )
    check(not schema_errors, "typed_property_ir.json fails production schema: " + "; ".join(error.message for error in schema_errors))
    check(
        digest(schema_path) == manifest["inputs"]["typed_property_ir"]["schema_sha256"],
        "production typed Property IR schema hash mismatch",
    )

    property_id = manifest["manifest_id"].split("LIBCOAP-", 1)[1]
    check(property_id == "COAP-TX-01", "manifest ID does not freeze COAP-TX-01")
    check(typed_property_ir.get("property_id") == property_id, "typed Property IR ID mismatch")
    check(property_profile.get("property_id") == property_id, "property profile companion ID mismatch")
    check(labels.get("property_id") == property_id, "label property ID mismatch")
    check(
        typed_property_ir.get("schema_version") == "2.0.0",
        "analyzer input does not use production typed Property IR role-DNF 2.0.0",
    )
    check(
        property_profile.get("schema_status") == "BENCHMARK_DRAFT_NOT_PRODUCTION_CORE_SCHEMA",
        "profile companion must not impersonate the production schema",
    )
    check(
        labels.get("status") == "PROVISIONAL_EXPERT_DRAFT_NOT_GOLD",
        "labels must remain explicitly provisional",
    )
    review = labels.get("review_contract", {})
    check(review.get("required_independent_human_reviewers") == 2, "two reviewers not required")
    check(review.get("completed_independent_human_reviewers") == 0, "human review was claimed without evidence")
    check(review.get("arbitration_status") == "PENDING", "arbitration must remain pending")
    check(review.get("codex_output_counts_as_human_review") is False, "Codex must not count as a human reviewer")
    check(review.get("headline_metric_allowed") is False, "provisional labels must not allow headline metrics")

    ap_ids = {item["ap_id"] for item in typed_property_ir.get("atomic_propositions", [])}
    check(
        ap_ids
        == {
            "coap_con_wait_started",
            "coap_first_retransmit_deadline_reached",
            "coap_matching_ack_or_reset_received",
            "coap_attempt_cancelled",
        },
        "typed AP set differs from the validated formula AP set",
    )
    check(property_profile.get("logic", {}).get("time_unit") == "millisecond", "time unit mismatch")
    check(property_profile.get("logic", {}).get("clock_domain") == "monotonic", "clock domain mismatch")
    check(property_profile.get("profile", {}).get("lower_bound_ms") == 2000, "lower default bound mismatch")
    check(property_profile.get("profile", {}).get("upper_bound_ms") == 3000, "upper default bound mismatch")
    check(property_profile.get("binding_policy", {}).get("joint_binding_required") is True, "joint binding is not required")
    selector_ids = {item["selector_id"] for item in typed_property_ir.get("selectors", [])}
    check(len(selector_ids) == len(typed_property_ir.get("selectors", [])), "duplicate production selector IDs")
    group_ids: list[str] = []
    for ap in typed_property_ir.get("atomic_propositions", []):
        declared_roles = set(ap.get("roles", []))
        groups = ap.get("role_selector_groups", [])
        group_roles: set[str] = set()
        covered_selectors: set[str] = set()
        for group in groups:
            group_ids.append(group.get("group_id"))
            role = group.get("role")
            all_of = group.get("all_of", [])
            check(role in declared_roles, f"{ap.get('ap_id')} group declares an absent AP role: {role}")
            if isinstance(role, str):
                group_roles.add(role)
            check(bool(all_of), f"{ap.get('ap_id')} contains an empty role-DNF conjunction")
            check(len(all_of) == len(set(all_of)), f"{ap.get('ap_id')} repeats a selector inside one conjunction")
            check(set(all_of).issubset(selector_ids), f"{ap.get('ap_id')} group references an absent production selector")
            covered_selectors.update(all_of)
        check(group_roles == declared_roles, f"{ap.get('ap_id')} role-DNF groups do not cover exactly its declared roles")
        check(
            predicate_selector_refs(ap.get("predicate")).issubset(covered_selectors),
            f"{ap.get('ap_id')} predicate selector is not covered by a role-DNF group",
        )
    check(len(group_ids) == len(set(group_ids)), "duplicate production role-DNF group IDs")

    must_labels = labels.get("must_influencers", [])
    must_ids = [item["id"] for item in must_labels]
    check(len(must_labels) == 19, f"expected 19 provisional MUST labels, got {len(must_labels)}")
    check(len(set(must_ids)) == len(must_ids), "duplicate provisional MUST label IDs")
    check(
        all(item.get("classification") == "MUST_INFLUENCE" for item in must_labels),
        "non-MUST classification in must_influencers",
    )
    binding_targets = manifest.get("joint_binding_targets", [])
    check(len(binding_targets) == 8, f"expected eight joint-binding targets, got {len(binding_targets)}")
    check(
        len({item["id"] for item in binding_targets}) == len(binding_targets),
        "duplicate joint-binding target IDs",
    )
    label_targets = {
        item["target"]
        for group in (
            "must_influencers",
            "may_influencers",
            "scope_only_influencers",
            "model_required_relationships",
        )
        for item in labels.get(group, [])
    }
    check(ap_ids.issubset(label_targets | {"all_atomic_propositions"}), "one or more APs have no influence expectations")

    source_root = ROOT / manifest["source_subject"]["repository_path"]
    expected_commit = manifest["source_subject"]["commit"]
    try:
        actual_commit = run_text(["git", "rev-parse", "HEAD"], source_root)
        actual_tree = run_text(["git", "rev-parse", "HEAD^{tree}"], source_root)
        ancestor = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                manifest["source_subject"]["legacy_evidence_commit"],
                expected_commit,
            ],
            cwd=source_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError) as error:
        failures.append(f"git identity check failed: {error}")
        actual_commit = ""
        actual_tree = ""
        ancestor = False
    check(actual_commit == expected_commit, f"source commit mismatch: {actual_commit}")
    check(actual_tree == manifest["source_subject"]["tree"], f"source tree mismatch: {actual_tree}")
    check(ancestor, "legacy evidence commit is not an ancestor of the frozen subject")

    for item in manifest.get("source_files", []):
        path = source_root / item["path"]
        check(path.is_file(), f"missing source file: {path}")
        if path.is_file():
            check(digest(path) == item["sha256"], f"source hash mismatch: {item['path']}")

    for item in manifest.get("source_locators", []):
        path = source_root / item["path"]
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        start = item["start"]
        end = item["end"]
        check(1 <= start <= end <= len(lines), f"invalid line range: {item['id']}")
        if 1 <= start <= end <= len(lines):
            excerpt = "\n".join(lines[start - 1 : end])
            for token in item["required_tokens"]:
                check(token in excerpt, f"{item['id']} no longer contains token {token!r}")

    for key, value in manifest.get("inputs", {}).items():
        if not isinstance(value, dict) or "sha256" not in value:
            continue
        path = ROOT / value["path"]
        check(path.is_file(), f"missing frozen input {key}: {path}")
        if path.is_file():
            check(digest(path) == value["sha256"], f"frozen input hash mismatch: {key}")

    legacy_catalog = load_json(ROOT / manifest["inputs"]["legacy_property_catalog"]["path"])
    legacy_items = [item for item in legacy_catalog if item.get("id") == property_id]
    check(len(legacy_items) == 1, "legacy catalog must contain exactly one COAP-TX-01")
    if legacy_items:
        legacy = legacy_items[0]
        check(set(legacy["atomic_propositions"]) == ap_ids, "legacy AP set differs from Property IR")
        check(legacy["mathematical_mitl"] == typed_property_ir["formula_text"], "production formula text changed")
        check(legacy["mathematical_mitl"] == property_profile["logic"]["mathematical_formula"], "companion mathematical formula changed")
        check(legacy["mightyppl_formula"] == property_profile["logic"]["finite_word_formula"], "finite formula changed")
        check(legacy["human_review_status"] == "PENDING", "legacy evidence unexpectedly claims human review")

    validation = load_json(ROOT / manifest["inputs"]["formula_validation"]["path"])
    check(validation.get("status") == "PASS", "stored formula validation did not pass")
    check(set(validation.get("ap_order", [])) == ap_ids, "formula validation AP set mismatch")
    check(validation.get("symbolic_concrete_consistent") is True, "symbolic/concrete monitor results differ")

    observed = load_json(ROOT / manifest["inputs"]["reproduction_results"]["path"])
    check(observed.get("source_commit") == expected_commit, "M1 reproduction commit mismatch")
    check(observed.get("deterministic") is True, "M1 reproduction was not deterministic")
    observed_runs = observed.get("runs", [])
    check(len(observed_runs) == 3, "M1 evidence does not contain three runs")
    for field, expected in (
        ("compile_database_sha256", manifest["build"]["compile_database"]["sha256"]),
        ("linked_bitcode_sha256", manifest["build"]["linked_bitcode"]["sha256"]),
        ("static_archive_sha256", manifest["build"]["static_archive"]["sha256"]),
    ):
        check({run.get(field) for run in observed_runs} == {expected}, f"M1 {field} identity mismatch")

    build_dir = args.build_dir.resolve()
    artifact_specs = (
        ("compile database", build_dir / "compile_commands.json", manifest["build"]["compile_database"]),
        ("linked bitcode", build_dir / "libcoap-all.bc", manifest["build"]["linked_bitcode"]),
        ("static archive", build_dir / "libcoap-3.a", manifest["build"]["static_archive"]),
        ("generated config", build_dir / "coap_config.h", manifest["build"]["generated_config"]),
    )
    for name, path, spec in artifact_specs:
        check(path.is_file(), f"missing {name}: {path}")
        if path.is_file():
            check(digest(path) == spec["sha256"], f"{name} hash mismatch")
            if "bytes" in spec:
                check(path.stat().st_size == spec["bytes"], f"{name} byte count mismatch")

    compile_db_path = build_dir / "compile_commands.json"
    if compile_db_path.is_file():
        compile_db = load_json(compile_db_path)
        check(len(compile_db) == manifest["build"]["compile_database"]["translation_units"], "translation-unit count mismatch")
        files = {pathlib.Path(item["file"]).resolve() for item in compile_db}
        for relative in manifest["build"]["required_translation_units"]:
            check((source_root / relative).resolve() in files, f"required TU absent from compile DB: {relative}")
        check(
            all("/usr/bin/clang-18" in item.get("command", "") for item in compile_db),
            "a compile command does not use the frozen Clang 18 driver",
        )

    if args.deep and (build_dir / "libcoap-all.bc").is_file():
        try:
            subprocess.run(
                [
                    "/usr/bin/opt-18",
                    "-passes=mem2reg,print<memoryssa>",
                    "-disable-output",
                    str(build_dir / "libcoap-all.bc"),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            checks += 1
        except (OSError, subprocess.CalledProcessError) as error:
            failures.append(f"LLVM MemorySSA construction failed: {error}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"SUMMARY status=FAIL checks={checks} failures={len(failures)}", file=sys.stderr)
        return 1

    print(
        "SUMMARY status=PASS "
        f"checks={checks} sources={len(manifest['source_files'])} "
        f"locators={len(manifest['source_locators'])} "
        f"must_labels={len(must_labels)} bindings={len(binding_targets)} "
        f"deep={'PASS' if args.deep else 'SKIPPED'} "
        "gold_status=PENDING_TWO_HUMANS_AND_ARBITRATION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
