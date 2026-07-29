#!/usr/bin/env python3
"""Validate, compile, and execute the complete RIFT-GOLD-120 corpus."""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
TRUTH = ROOT / "ground_truth"
RELATION_COUNTS = {
    "MUST_INFLUENCE": 4,
    "MAY_INFLUENCE": 3,
    "NO_INFLUENCE": 3,
}
BANNED_PROJECT_IDENTIFIERS = (
    "ardupilot",
    "libcoap",
    "mavlink",
    "px4",
    "paparazzi",
    "mosquitto",
    "tinymqtt",
    "gcs_failsafe",
)
OUTPUT_PATTERN = re.compile(r"^AP_primary=[01]( AP_secondary=[01])?\n$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def run(
    arguments: list[str],
    *,
    cwd: Path = ROOT,
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def compare_generated_tree(expected: Path, actual: Path) -> list[str]:
    failures: list[str] = []
    relative_files = [
        Path("compile_commands.json"),
        Path("manifest.json"),
        *(
            path.relative_to(expected)
            for directory in ("cases", "ground_truth")
            for path in sorted((expected / directory).glob("*"))
            if path.is_file()
        ),
    ]
    for relative in relative_files:
        expected_file = expected / relative
        actual_file = actual / relative
        if not actual_file.is_file():
            failures.append(f"deterministic generation missing {relative}")
        elif expected_file.read_bytes() != actual_file.read_bytes():
            failures.append(f"deterministic generation differs at {relative}")
    unexpected = {
        path.relative_to(actual)
        for directory in ("cases", "ground_truth")
        for path in (actual / directory).glob("*")
        if path.is_file()
    } - set(relative_files)
    for relative in sorted(unexpected):
        failures.append(f"deterministic generation added unexpected {relative}")
    return failures


def verify_location(
    source_lines: list[str],
    anchor_id: str,
    anchor: dict[str, Any],
    source_file: str,
) -> str | None:
    location = anchor["location"]
    if location["file"] != source_file:
        return f"{anchor_id}: location file disagrees with case source"
    line_number = location["line"]
    column = location["column"]
    if not (1 <= line_number <= len(source_lines)):
        return f"{anchor_id}: line {line_number} is out of range"
    line = source_lines[line_number - 1]
    if line[column - 1 : column - 1 + len(anchor_id)] != anchor_id:
        return f"{anchor_id}: token does not start at recorded line/column"
    if line_number < 2:
        return f"{anchor_id}: no preceding marker line"
    marker = f"/* RIFT_{anchor['kind']}:{anchor_id} */"
    if marker not in source_lines[line_number - 2]:
        return f"{anchor_id}: preceding marker is not {marker}"
    return None


def compile_and_run(
    entry: dict[str, Any],
    compile_entry: dict[str, Any],
    temporary: Path,
) -> list[str]:
    failures: list[str] = []
    case_id = entry["case_id"]
    source_path = ROOT / entry["source_file"]

    object_path = temporary / f"{case_id}.o"
    object_arguments = list(compile_entry["arguments"])
    try:
        output_index = object_arguments.index("-o") + 1
        object_arguments[output_index] = str(object_path)
    except (ValueError, IndexError):
        return [f"{case_id}: compile command has no valid -o argument"]
    compiled = run(object_arguments)
    if compiled.returncode != 0:
        return [
            f"{case_id}: compile_commands object build failed rc={compiled.returncode}\n"
            f"{compiled.stdout}{compiled.stderr}"
        ]
    if not object_path.is_file():
        failures.append(f"{case_id}: object build produced no output")

    compiler = "clang-18" if entry["language"] == "c11" else "clang++-18"
    standard = "-std=c11" if entry["language"] == "c11" else "-std=c++20"
    executable = temporary / case_id
    linked = run(
        [
            compiler,
            standard,
            "-O0",
            "-g",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source_path),
            "-o",
            str(executable),
        ]
    )
    if linked.returncode != 0:
        return [
            f"{case_id}: executable build failed rc={linked.returncode}\n"
            f"{linked.stdout}{linked.stderr}"
        ]
    executed = run([str(executable), "7", "1", "9", "3"])
    if executed.returncode != 0:
        failures.append(
            f"{case_id}: execution failed rc={executed.returncode}\n"
            f"{executed.stdout}{executed.stderr}"
        )
    elif not OUTPUT_PATTERN.fullmatch(executed.stdout):
        failures.append(f"{case_id}: unexpected stdout {executed.stdout!r}")
    if executed.stderr:
        failures.append(f"{case_id}: unexpected stderr {executed.stderr!r}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    failures: list[str] = []
    passes: list[str] = []

    def expect(condition: bool, label: str, detail: str = "") -> None:
        if condition:
            if not label.startswith("RIFT-GOLD-"):
                passes.append(label)
        else:
            failures.append(f"{label}: {detail or 'condition was false'}")

    schema = load(ROOT / "ground_truth.schema.json")
    validator = jsonschema.Draft7Validator(schema)
    manifest = load(ROOT / "manifest.json")
    compile_commands = load(ROOT / "compile_commands.json")
    entries = manifest.get("entries", [])

    expect(manifest.get("case_count") == 120, "manifest case_count is 120")
    expect(len(entries) == 120, "manifest has 120 entries", str(len(entries)))
    expect(len(list(CASES.glob("*.c"))) == 60, "corpus has 60 C files")
    expect(len(list(CASES.glob("*.cpp"))) == 60, "corpus has 60 C++ files")
    expect(len(list(TRUTH.glob("*.json"))) == 120, "corpus has 120 ground-truth files")
    expect(len(compile_commands) == 120, "compile_commands has 120 entries")
    expect(len({item["case_id"] for item in entries}) == 120, "case IDs are unique")
    expect(len({item["source_file"] for item in entries}) == 120, "source paths are unique")
    expect(
        sha256(ROOT / "generate_gold.py") == manifest.get("generator_sha256"),
        "generator hash matches manifest",
    )
    expect(
        sha256(ROOT / "ground_truth.schema.json")
        == manifest.get("ground_truth_schema_sha256"),
        "schema hash matches manifest",
    )
    expect(
        sha256(ROOT / "compile_commands.json")
        == manifest.get("compile_commands_sha256"),
        "compile_commands hash matches manifest",
    )
    expect(
        manifest.get("real_project_human_annotation")
        == {
            "status": "PENDING",
            "required_annotators": 2,
            "arbitration_required": True,
        },
        "real-project human annotation remains PENDING",
    )

    category_counts = collections.Counter(item["category"] for item in entries)
    expect(
        set(category_counts) == set(manifest.get("categories", []))
        and all(count == 10 for count in category_counts.values())
        and len(category_counts) == 12,
        "12 categories each contain 10 cases",
        repr(category_counts),
    )
    language_counts = collections.Counter(item["language"] for item in entries)
    expect(language_counts == {"c11": 60, "c++20": 60}, "language split is 60/60", repr(language_counts))
    global_relations = collections.Counter(item["case_relation"] for item in entries)
    expect(
        global_relations
        == {"MUST_INFLUENCE": 48, "MAY_INFLUENCE": 36, "NO_INFLUENCE": 36},
        "global case-relation split is 48/36/36",
        repr(global_relations),
    )
    for category in sorted(category_counts):
        category_entries = [item for item in entries if item["category"] == category]
        relation_counts = collections.Counter(item["case_relation"] for item in category_entries)
        language_split = collections.Counter(item["language"] for item in category_entries)
        expect(relation_counts == RELATION_COUNTS, f"{category} relation split is 4/3/3", repr(relation_counts))
        expect(language_split == {"c11": 5, "c++20": 5}, f"{category} language split is 5/5", repr(language_split))

    compile_by_file = {Path(item["file"]).name: item for item in compile_commands}
    expect(len(compile_by_file) == 120, "compile_commands files are unique")

    schema_valid = 0
    location_valid = 0
    relation_complete = 0
    project_neutral = 0
    controllability_valid = 0
    for entry in entries:
        source_path = ROOT / entry["source_file"]
        truth_path = ROOT / entry["ground_truth_file"]
        if not source_path.is_file() or not truth_path.is_file():
            failures.append(f"{entry['case_id']}: source or truth file is missing")
            continue
        expect(sha256(source_path) == entry["source_sha256"], f"{entry['case_id']} source hash")
        expect(sha256(truth_path) == entry["ground_truth_sha256"], f"{entry['case_id']} truth hash")
        truth = load(truth_path)
        errors = sorted(validator.iter_errors(truth), key=lambda error: list(error.path))
        if errors:
            failures.append(
                f"{entry['case_id']}: schema validation failed: "
                + "; ".join(f"{list(error.path)} {error.message}" for error in errors)
            )
        else:
            schema_valid += 1
        expect(truth["case_id"] == entry["case_id"], f"{entry['case_id']} truth identity")
        expect(truth["category"] == entry["category"], f"{entry['case_id']} truth category")
        expect(truth["language"] == entry["language"], f"{entry['case_id']} truth language")
        expect(truth["case_relation"] == entry["case_relation"], f"{entry['case_id']} truth relation")
        expect(sha256(source_path) == truth["source_sha256"], f"{entry['case_id']} source/truth hash")

        source_lines = source_path.read_text(encoding="utf-8").splitlines()
        location_errors = [
            error
            for anchor_id, anchor in truth["anchors"].items()
            if (error := verify_location(source_lines, anchor_id, anchor, truth["source_file"]))
        ]
        if location_errors:
            failures.extend(f"{entry['case_id']}: {error}" for error in location_errors)
        else:
            location_valid += 1

        source_ids = {item["id"] for item in truth["sources"]}
        ap_ids = {item["id"] for item in truth["aps"]}
        expected_pairs = {(source_id, ap_id) for source_id in source_ids for ap_id in ap_ids}
        actual_pairs = {(item["source_id"], item["ap_id"]) for item in truth["relations"]}
        relation_errors: list[str] = []
        if expected_pairs != actual_pairs:
            relation_errors.append(
                f"relation pairs are not complete: missing={expected_pairs - actual_pairs}, extra={actual_pairs - expected_pairs}"
            )
        if not any(item["relation"] == truth["case_relation"] for item in truth["relations"]):
            relation_errors.append("no relation represents the case_relation")
        for item in truth["relations"]:
            relation_name = item["relation"]
            nodes = item["path"]["nodes"]
            edges = item["path"]["edges"]
            if any(node not in truth["anchors"] for node in nodes):
                relation_errors.append(f"{item['source_id']}->{item['ap_id']} uses unknown anchor")
            if relation_name == "NO_INFLUENCE":
                if nodes or edges or item["mutation_recipe"] is not None or not item["negative_reason"]:
                    relation_errors.append(f"{item['source_id']}->{item['ap_id']} malformed negative relation")
            else:
                if len(nodes) < 2 or len(edges) != len(nodes) - 1 or item["negative_reason"] is not None:
                    relation_errors.append(f"{item['source_id']}->{item['ap_id']} malformed positive relation")
                expected_certainty = "must" if relation_name == "MUST_INFLUENCE" else "may"
                if any(edge["certainty"] != expected_certainty for edge in edges):
                    relation_errors.append(f"{item['source_id']}->{item['ap_id']} certainty mismatch")
        if relation_errors:
            failures.extend(f"{entry['case_id']}: {error}" for error in relation_errors)
        else:
            relation_complete += 1

        source_by_id = {item["id"]: item for item in truth["sources"]}
        control_errors: list[str] = []
        for source_item in truth["sources"]:
            expected_frontier = source_item["controllability"] != "INTERNAL"
            if source_item["fuzzable_frontier"] != expected_frontier:
                control_errors.append(f"{source_item['id']} frontier/control mismatch")
        for relation_item in truth["relations"]:
            source_item = source_by_id[relation_item["source_id"]]
            if source_item["controllability"] == "INTERNAL" and relation_item["mutation_recipe"] is not None:
                control_errors.append(f"{source_item['id']} internal source has an external mutation recipe")
            if (
                source_item["fuzzable_frontier"]
                and relation_item["relation"] != "NO_INFLUENCE"
                and relation_item["mutation_recipe"] is None
            ):
                control_errors.append(f"{source_item['id']} actionable positive relation lacks recipe")
        if control_errors:
            failures.extend(f"{entry['case_id']}: {error}" for error in control_errors)
        else:
            controllability_valid += 1

        neutral_text = source_path.read_text(encoding="utf-8").lower()
        symbols = "\n".join(
            [item["symbol"] for item in truth["sources"]]
            + [item["symbol"] + " " + item["expression"] for item in truth["aps"]]
            + list(truth["anchors"])
        ).lower()
        banned = [word for word in BANNED_PROJECT_IDENTIFIERS if word in neutral_text or word in symbols]
        if banned:
            failures.append(f"{entry['case_id']}: project-specific identifiers found {banned}")
        else:
            project_neutral += 1

        command = compile_by_file.get(source_path.name)
        if command is None:
            failures.append(f"{entry['case_id']}: no compile_commands entry")
        else:
            expected_compiler = "clang-18" if entry["language"] == "c11" else "clang++-18"
            expected_standard = "-std=c11" if entry["language"] == "c11" else "-std=c++20"
            expect(command["arguments"][0] == expected_compiler, f"{entry['case_id']} compiler is Clang 18")
            expect(expected_standard in command["arguments"], f"{entry['case_id']} language standard")
            expect("-Wall" in command["arguments"] and "-Wextra" in command["arguments"] and "-Werror" in command["arguments"], f"{entry['case_id']} strict warnings")

    expect(schema_valid == 120, "JSON Schema validates 120/120", str(schema_valid))
    expect(location_valid == 120, "anchor locations validate 120/120", str(location_valid))
    expect(relation_complete == 120, "relation matrices validate 120/120", str(relation_complete))
    expect(controllability_valid == 120, "influence/control/frontier separation validates 120/120", str(controllability_valid))
    expect(project_neutral == 120, "project-neutral identifiers validate 120/120", str(project_neutral))

    case_091 = load(TRUTH / "091_uncontrollable_false_correlation_must_v0.json")
    source_091 = {item["id"]: item for item in case_091["sources"]}
    relation_091 = {(item["source_id"], item["ap_id"]): item for item in case_091["relations"]}
    expect(
        source_091["source_internal"]["controllability"] == "INTERNAL"
        and source_091["source_internal"]["fuzzable_frontier"] is False
        and relation_091[("source_internal", "ap_primary")]["relation"] == "MUST_INFLUENCE",
        "091 internal MUST influencer is excluded from fuzzable frontier",
    )
    expect(
        source_091["source_external_similar"]["fuzzable_frontier"] is True
        and relation_091[("source_external_similar", "ap_primary")]["relation"] == "NO_INFLUENCE",
        "091 controllable false correlation remains negative",
    )

    with tempfile.TemporaryDirectory(prefix="rift-gold-regenerate.", dir="/tmp") as temporary_name:
        regenerated = Path(temporary_name)
        generation = run(
            [
                "python3",
                str(ROOT / "generate_gold.py"),
                "--output",
                str(regenerated),
                "--command-root",
                str(ROOT),
            ]
        )
        if generation.returncode != 0:
            failures.append(
                f"deterministic regeneration failed rc={generation.returncode}\n"
                f"{generation.stdout}{generation.stderr}"
            )
        else:
            failures.extend(compare_generated_tree(ROOT, regenerated))
            if not failures:
                passes.append("deterministic regeneration is byte-identical")

    compile_failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="rift-gold-build.", dir="/tmp") as temporary_name:
        temporary = Path(temporary_name)
        work: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for entry in entries:
            command = compile_by_file.get(Path(entry["source_file"]).name)
            if command is not None:
                work.append((entry, command))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
            futures = [
                executor.submit(compile_and_run, entry, command, temporary)
                for entry, command in work
            ]
            for future in concurrent.futures.as_completed(futures):
                compile_failures.extend(future.result())
    failures.extend(compile_failures)
    expect(not compile_failures and len(entries) == 120, "Clang 18 object compile + link + run passes 120/120")

    bytecode = sorted(ROOT.rglob("__pycache__")) + sorted(ROOT.rglob("*.pyc"))
    expect(not bytecode, "delivery tree has no Python bytecode cache", ", ".join(str(path) for path in bytecode))

    clang_c = run(["clang-18", "--version"]).stdout.splitlines()[0]
    clang_cpp = run(["clang++-18", "--version"]).stdout.splitlines()[0]
    print(f"TOOLCHAIN_C={clang_c}")
    print(f"TOOLCHAIN_CPP={clang_cpp}")
    for label in passes:
        print(f"PASS {label}")
    for label in failures:
        print(f"FAIL {label}")
    print(
        f"SUMMARY status={'PASS' if not failures else 'FAIL'} "
        f"cases={len(entries)} schema={schema_valid} locations={location_valid} "
        f"relations={relation_complete} controllability={controllability_valid} "
        f"project_neutral={project_neutral} failures={len(failures)}"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
