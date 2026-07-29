#!/usr/bin/env python3
"""Detached integrity and claim-boundary checks for the SVF portability probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

import jsonschema


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def workspace_root(script: pathlib.Path) -> pathlib.Path:
    for candidate in [script.parent, *script.parents]:
        if (candidate / "AGENTS.md").is_file() and (
            candidate / "src/StaticAnalysis"
        ).is_dir():
            return candidate
    raise RuntimeError("cannot locate TAFuzz workspace root")


def git(source: pathlib.Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def validate_schema(root: pathlib.Path, schema_name: str, artifact: pathlib.Path) -> None:
    schema_root = root / "src/StaticAnalysis/schema"
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in schema_root.glob("*.schema.json")
    }
    store = {value["$id"]: value for value in schemas.values() if "$id" in value}
    schema = schemas[schema_name]
    validator = jsonschema.Draft7Validator(
        schema,
        resolver=jsonschema.RefResolver.from_schema(schema, store=store),
    )
    errors = sorted(
        validator.iter_errors(json.loads(artifact.read_text(encoding="utf-8"))),
        key=lambda error: list(error.path),
    )
    if errors:
        raise AssertionError(
            f"{artifact} violates {schema_name}: "
            + "; ".join(error.message for error in errors)
        )


def require_ast_node(nodes: list[dict[str, Any]], expected: dict[str, Any]) -> None:
    if not any(
        all(node.get(key) == value for key, value in expected.items())
        for node in nodes
    ):
        raise AssertionError(f"missing exact AST evidence node: {expected}")


def parse_time(path: pathlib.Path) -> dict[str, float | int]:
    fields: dict[str, float | int] = {}
    for name, value in re.findall(
        r"([a-z_]+)=([0-9.]+)", path.read_text(encoding="utf-8")
    ):
        fields[name] = float(value) if "." in value else int(value)
    return fields


def read_text(root: pathlib.Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="replace")


def witness_groups(document: dict[str, Any], union_shape: bool) -> dict[tuple[str, ...], dict[str, set[str]]]:
    groups: dict[tuple[str, ...], dict[str, set[str]]] = {}
    for candidate in document["candidates"]:
        candidate_key = (
            candidate["ap_id"],
            candidate["action"]["action_schema_id"],
        )
        for witness in candidate["witnesses"]:
            key = candidate_key + (
                witness["attachment_id"],
                witness["boundary_node_id"],
            )
            account = groups.setdefault(
                key,
                {
                    "meets": set(),
                    "forward_nodes": set(),
                    "forward_edges": set(),
                    "cone_edges": set(),
                    "model_facts": set(),
                },
            )
            if union_shape:
                account["meets"].update(
                    meet["meet_node_id"] for meet in witness["meets"]
                )
            else:
                account["meets"].add(witness["meet_node_id"])
            account["forward_nodes"].update(witness["forward_node_ids"])
            account["forward_edges"].update(witness["forward_edge_ids"])
            account["cone_edges"].update(witness["cone_edge_ids"])
            account["model_facts"].update(witness["model_fact_ids"])
    return groups


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=pathlib.Path(__file__).with_name("result_manifest.json"),
    )
    parser.add_argument("--output", type=pathlib.Path)
    options = parser.parse_args()
    script = pathlib.Path(__file__).resolve()
    root = workspace_root(script)
    manifest_path = options.manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[str] = []
    warnings: list[str] = []

    expected_status = "SINGLE_TU_SCHEMA2_UNION_SEALED_FULL_111_TU_TIME_GATE_PENDING"
    if manifest["status"] != expected_status:
        raise AssertionError("manifest overstates or changes the registered claim boundary")
    checks.append("single-TU seal/full-time-gate claim boundary")

    for relative, receipt in manifest["evidence_files"].items():
        path = root / relative
        if not path.is_file():
            raise AssertionError(f"missing evidence file: {relative}")
        if path.stat().st_size != receipt["size"]:
            raise AssertionError(f"size mismatch: {relative}")
        if sha256_file(path) != receipt["sha256"]:
            raise AssertionError(f"SHA-256 mismatch: {relative}")
    checks.append(f"{len(manifest['evidence_files'])} persistent evidence receipts")

    source = root / manifest["source"]["checkout"]
    if git(source, "rev-parse", "HEAD") != manifest["source"]["commit"]:
        raise AssertionError("SVF commit drift")
    if git(source, "rev-parse", "HEAD^{tree}") != manifest["source"]["tree"]:
        raise AssertionError("SVF tree drift")
    if git(source, "status", "--porcelain"):
        raise AssertionError("SVF checkout is not clean")
    checks.append("SVF commit/tree/clean checkout")

    compile_database = root / manifest["inputs"]["compile_database"]["path"]
    entries = json.loads(compile_database.read_text(encoding="utf-8"))
    if len(entries) != 111 or len({entry["file"] for entry in entries}) != 111:
        raise AssertionError("full SVF compile database is not the frozen 111-TU set")
    checks.append("111 unique frozen translation units")

    property_path = root / manifest["inputs"]["property_ir"]["path"]
    executor_path = root / manifest["inputs"]["executor_capabilities"]["path"]
    validate_schema(root, "typed_property_ir.schema.json", property_path)
    validate_schema(root, "executor_capabilities.schema.json", executor_path)
    property_ir = json.loads(property_path.read_text(encoding="utf-8"))
    if "PORTABILITY_PROBE_NOT_REQUIREMENT" not in property_ir["formula_text"]:
        raise AssertionError("probe/non-requirement label was removed")
    checks.append("property and executor schema validation")

    model_path = root / manifest["inputs"]["model_pack"]["path"]
    model_text = model_path.read_text(encoding="utf-8")
    model = json.loads(model_text)
    if model["layer"] != "platform" or not model["property_independent"]:
        raise AssertionError("configured model is not the generic platform pack")
    if "SVF" in model_text:
        raise AssertionError("generic POSIX pack contains an SVF literal")
    checks.append("generic POSIX pack with no SVF-specific literal")

    ast = json.loads(
        (root / manifest["inputs"]["ast_evidence"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    nodes = ast["nodes"]
    require_ast_node(
        nodes,
        {
            "kind": "BinaryOperator",
            "opcode": "<",
            "canonical_type": "bool",
            "begin": {"line": 848, "column": 12},
            "end": {"line": 848, "column": 25},
        },
    )
    require_ast_node(
        nodes,
        {
            "kind": "BinaryOperator",
            "opcode": "=",
            "canonical_type": "char *",
            "begin": {"line": 850, "column": 9},
            "end": {"line": 850, "column": 42},
        },
    )
    checks.append("exact Clang AST target evidence")

    before = manifest["runs"]["before_fix"]
    for name, expected in before.items():
        observed = read_text(root, expected["stderr"]).count(
            "callsite references unknown caller:"
        )
        if observed != expected["empty_caller_diagnostics"]:
            raise AssertionError(f"before-fix signature drift: {name}")
        if int(parse_time(root / expected["time_receipt"])["exit"]) != 1:
            raise AssertionError(f"before-fix exit drift: {name}")
    checks.append("four before-fix empty-caller failure signatures")

    owner_full = manifest["runs"]["owner_fix_full"]
    if read_text(root, owner_full["stderr"]) != "FAIL: std::bad_alloc\n":
        raise AssertionError("owner-fix full-run failure signature drift")
    if int(parse_time(root / owner_full["time_receipt"])["exit"]) != 1:
        raise AssertionError("owner-fix full-run exit drift")
    checks.append("historical owner-fix 12-GiB allocation failure")

    traversal = manifest["runs"]["traversal_fix"]
    for name in ("single_index", "single_recipes"):
        run = traversal[name]
        if not read_text(root, run["stdout"]).startswith("PASS command="):
            raise AssertionError(f"traversal {name} did not pass")
        if read_text(root, run["stderr"]):
            raise AssertionError(f"traversal {name} has unexpected stderr")
        if int(parse_time(root / run["time_receipt"])["exit"]) != 0:
            raise AssertionError(f"traversal {name} receipt is nonzero")
    full = traversal["full_index"]
    if read_text(root, full["stdout"]) or read_text(root, full["stderr"]):
        raise AssertionError("traversal full timeout unexpectedly emitted output")
    full_time = parse_time(root / full["time_receipt"])
    if int(full_time["exit"]) != 124 or int(full_time["peak_kib"]) != 1679452:
        raise AssertionError("traversal full timeout/resource receipt drift")
    checks.append("traversal single-TU passes and 111-TU time-budget failure")

    union_run = manifest["runs"]["union_diagnostic"]
    if not read_text(root, union_run["stdout"]).startswith("PASS command=recipes"):
        raise AssertionError("union diagnostic did not pass recipes")
    if int(parse_time(root / union_run["time_receipt"])["exit"]) != 0:
        raise AssertionError("union diagnostic receipt is nonzero")
    checks.append("union diagnostic run signature")

    sealed = manifest["runs"]["schema2_union"]
    if not read_text(root, sealed["recipes"]["stdout"]).startswith(
        "PASS command=recipes"
    ):
        raise AssertionError("schema-2 union recipes did not pass")
    if read_text(root, sealed["recipes"]["stderr"]):
        raise AssertionError("schema-2 union recipes has unexpected stderr")
    if int(parse_time(root / sealed["recipes"]["time_receipt"])["exit"]) != 0:
        raise AssertionError("schema-2 union recipes receipt is nonzero")
    pre_contract = json.loads(
        read_text(root, sealed["certificate_pre_contract_report"])
    )
    post_contract = json.loads(read_text(root, sealed["certificate_report"]))
    if (pre_contract["verdict"], pre_contract["failures"]) != ("FAIL", 4):
        raise AssertionError("pre-contract occurrence closure evidence drift")
    if (
        post_contract["verdict"],
        post_contract["checks"],
        post_contract["failures"],
        post_contract["physical_files_rehashed"],
    ) != ("PASS", 62, 0, 665):
        raise AssertionError("detached certificate seal did not pass exactly")
    if post_contract["certificate_sha256"] != sealed["certificate_sha256"]:
        raise AssertionError("sealed certificate digest drift")
    checks.append("schema-2 union recipes plus 62/62 detached certificate seal")

    for summary_name, descriptor in manifest["summaries"].items():
        summary = json.loads((root / descriptor["path"]).read_text(encoding="utf-8"))
        if summary["status"] != descriptor["status"]:
            raise AssertionError(f"summary status drift: {summary_name}")
    checks.append("phase summaries preserve explicit statuses")

    for name, analyzer in manifest["analyzers"].items():
        snapshot = pathlib.Path(analyzer["snapshot_path"])
        if snapshot.is_file():
            if sha256_file(snapshot) != analyzer["binary_sha256"]:
                raise AssertionError(f"analyzer snapshot digest drift: {name}")
        else:
            warnings.append(f"external analyzer snapshot absent: {name}")
    checks.append("available immutable analyzer snapshots rehashed")

    current_root = pathlib.Path(manifest["bulk_artifacts"]["schema2_output_root"])
    if current_root.is_dir():
        for filename, receipt in manifest["bulk_artifacts"]["schema2"].items():
            path = current_root / filename
            if path.stat().st_size != receipt["size"] or sha256_file(path) != receipt["sha256"]:
                raise AssertionError(f"schema-2 bulk artifact drift: {filename}")
        semantic = json.loads((current_root / "semantic_index.json").read_text())
        expected_counts = {
            "entities": 22989,
            "function_summaries": 3432,
            "callsites": 7430,
            "semantic_nodes": 22417,
            "semantic_relations": 10819,
            "unsupported_constructs": 7288,
        }
        if {key: len(semantic[key]) for key in expected_counts} != expected_counts:
            raise AssertionError("schema-2 semantic counts drift")
        if any(not callsite["caller_function_id"] for callsite in semantic["callsites"]):
            raise AssertionError("schema-2 semantic index contains an empty caller")
        entities = {
            item["entity"]["entity_id"]: item["entity"]
            for item in semantic["entities"]
        }
        fallback_ids = {
            entity_id
            for entity_id, entity in entities.items()
            if str(entity.get("qualified_signature", "")).startswith(
                "translation-unit-nonfunction:"
            )
        }
        global_ids = {
            entity_id
            for entity_id, entity in entities.items()
            if str(entity.get("qualified_signature", "")).startswith(
                "global-initializer:"
            )
        }
        if len(fallback_ids) != 12 or global_ids:
            raise AssertionError("schema-2 synthetic-owner accounting drift")
        frontier = json.loads((current_root / "frontier_candidates.json").read_text())
        fuzzable = json.loads((current_root / "fuzzable_frontier.json").read_text())
        if frontier["schema_version"] != "2.0.0" or fuzzable["schema_version"] != "1.1.0":
            raise AssertionError("normative union schema version drift")
        witnesses = [
            witness
            for candidate in frontier["candidates"]
            for witness in candidate["witnesses"]
        ]
        if len(witnesses) != 2 or sum(len(w["meets"]) for w in witnesses) != 5:
            raise AssertionError("union witness/meet accounting drift")
        for witness in witnesses:
            meet_ids = [meet["meet_node_id"] for meet in witness["meets"]]
            if len(meet_ids) != len(set(meet_ids)):
                raise AssertionError("duplicate meet in a union witness")
            for key in ("forward_node_ids", "forward_edge_ids", "cone_edge_ids", "model_fact_ids"):
                if len(witness[key]) != len(set(witness[key])):
                    raise AssertionError(f"non-set union ledger: {key}")
        recipes = json.loads((current_root / "mutation_recipes.json").read_text())
        if len(recipes["recipes"]) != 2 or any(
            recipe["status"] != "UNKNOWN" for recipe in recipes["recipes"]
        ):
            raise AssertionError("recipe claim boundary drift")
        checks.append("schema-2 bulk hashes, semantic closure, union shape, UNKNOWN recipes")
    else:
        warnings.append("external schema-2 bulk output is absent; persistent receipts only")

    old_root = pathlib.Path(manifest["bulk_artifacts"]["pre_union_output_root"])
    if current_root.is_dir() and old_root.is_dir():
        old_frontier = json.loads((old_root / "frontier_candidates.json").read_text())
        new_frontier = json.loads((current_root / "frontier_candidates.json").read_text())
        if witness_groups(old_frontier, False) != witness_groups(new_frontier, True):
            raise AssertionError("union witness lost or invented meet/path evidence")
        checks.append("old witnesses equal new per-group meet/path set unions")
    else:
        warnings.append("pre-union bulk output absent; union equivalence not replayed")

    report = {
        "schema_version": "rift.portability.svf.verification.v2",
        "status": "PASS_SINGLE_TU_SEALED_FULL_TIME_GATE_PENDING",
        "checks": checks,
        "warnings": warnings,
        "manifest_sha256": sha256_file(manifest_path),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if options.output:
        options.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
