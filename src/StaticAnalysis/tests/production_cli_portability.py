#!/usr/bin/env python3
"""Black-box checks for the production CLI logical path-map contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def write_fixture(root: Path) -> tuple[Path, Path, Path]:
    source = root / "source"
    build = root / "build"
    generated = build / "generated"
    source.mkdir(parents=True)
    generated.mkdir(parents=True)
    (generated / "generated.h").write_text(
        "#define PORTABLE_BIAS 3\n", encoding="utf-8"
    )
    main = source / "main.c"
    main.write_text(
        '#include "generated.h"\n'
        "int portable_value(int input) { return input + PORTABLE_BIAS; }\n",
        encoding="utf-8",
    )
    database = build / "compile_commands.json"
    database.write_text(
        json.dumps(
            [
                {
                    "directory": str(build),
                    "file": str(main),
                    "arguments": [
                        "clang-18",
                        "-std=c11",
                        f"-ffile-prefix-map={source}=..",
                        "-I",
                        str(generated),
                        "-c",
                        str(main),
                        "-o",
                        str(build / "main.o"),
                    ],
                }
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return source, build, database


def write_global_initializer_fixture(root: Path) -> tuple[Path, Path, Path]:
    source = root / "global-source"
    build = root / "global-build"
    source.mkdir(parents=True)
    build.mkdir(parents=True)
    main = source / "global.cpp"
    main.write_text(
        "int produce(int value) { return value + 1; }\n"
        "int configured = produce(41);\n"
        "struct Box { int method(int value) { return produce(value); } };\n"
        "int normal(int value) { return produce(value); }\n",
        encoding="utf-8",
    )
    database = build / "compile_commands.json"
    database.write_text(
        json.dumps(
            [
                {
                    "directory": str(build),
                    "file": str(main),
                    "arguments": [
                        "clang++-18",
                        "-std=c++20",
                        "-c",
                        str(main),
                        "-o",
                        str(build / "global.o"),
                    ],
                }
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return source, build, database


def write_cross_tu_initializer_fixture(root: Path) -> tuple[Path, Path, Path]:
    source = root / "cross-tu-source"
    build = root / "cross-tu-build"
    source.mkdir(parents=True)
    build.mkdir(parents=True)
    header = source / "shared.hpp"
    header.write_text(
        "int make_value(int value);\n"
        "inline int shared_value = make_value(1);\n"
        "static int local_value = make_value(2);\n",
        encoding="utf-8",
    )
    first = source / "a.cpp"
    first.write_text(
        '#include "shared.hpp"\n'
        "int make_value(int value) { return value; }\n"
        "int read_a() { return shared_value + local_value; }\n",
        encoding="utf-8",
    )
    second = source / "b.cpp"
    second.write_text(
        '#include "shared.hpp"\n'
        "int read_b() { return shared_value + local_value; }\n",
        encoding="utf-8",
    )
    commands = []
    for unit in (first, second):
        commands.append(
            {
                "directory": str(build),
                "file": str(unit),
                "arguments": [
                    "clang++-18",
                    "-std=c++20",
                    "-I",
                    str(source),
                    "-c",
                    str(unit),
                    "-o",
                    str(build / f"{unit.stem}.o"),
                ],
            }
        )
    database = build / "compile_commands.json"
    database.write_text(
        json.dumps(commands, indent=2) + "\n", encoding="utf-8"
    )
    return source, build, database


def invoke(
    binary: Path,
    database: Path,
    output: Path,
    roots: list[tuple[str, Path]],
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(binary),
        "index",
        "--compile-db",
        str(database),
        "--output",
        str(output),
    ]
    for root_id, physical in roots:
        command.extend(["--logical-root", f"{root_id}={physical}"])
    command.extend(extra)
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_failure(completed: subprocess.CompletedProcess[str], needle: str) -> None:
    if completed.returncode == 0 or needle not in completed.stderr:
        raise AssertionError(
            f"expected failure containing {needle!r}; "
            f"rc={completed.returncode} stderr={completed.stderr!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    arguments = parser.parse_args()
    binary = arguments.binary.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="rift-portability-a-") as first_name, \
            tempfile.TemporaryDirectory(prefix="rift-portability-b-") as second_name:
        first = Path(first_name)
        second = Path(second_name)
        source_a, build_a, database_a = write_fixture(first)
        source_b, build_b, database_b = write_fixture(second)
        output_a = first / "index.json"
        output_b = second / "index.json"

        run_a = invoke(
            binary,
            database_a,
            output_a,
            [("source", source_a), ("build", build_a)],
        )
        run_b = invoke(
            binary,
            database_b,
            output_b,
            [("build", build_b), ("source", source_b)],
        )
        if run_a.returncode != 0 or run_b.returncode != 0:
            raise AssertionError(
                f"relocation runs failed: A={run_a.stderr!r} B={run_b.stderr!r}"
            )
        bytes_a = output_a.read_bytes()
        bytes_b = output_b.read_bytes()
        if bytes_a != bytes_b:
            raise AssertionError("canonical semantic index changed after relocation")
        text = bytes_a.decode("utf-8")
        if "riftpath://v1/source/main.c" not in text:
            raise AssertionError("source logical URI is missing")
        if "riftpath://v1/build/generated/generated.h" not in text:
            raise AssertionError("generated-header logical URI is missing")
        for physical in (first, second):
            if str(physical) in text:
                raise AssertionError("canonical index leaks a physical fixture path")

        conflict = invoke(
            binary,
            database_a,
            first / "conflict.json",
            [("source", source_a), ("build", build_a)],
            "--source-root",
            str(source_a),
        )
        require_failure(conflict, "mutually exclusive")

        relative = invoke(
            binary,
            database_a,
            first / "relative.json",
            [("source", Path("relative"))],
        )
        require_failure(relative, "must be absolute")

        duplicate = invoke(
            binary,
            database_a,
            first / "duplicate.json",
            [("source", source_a), ("source", build_a)],
        )
        require_failure(duplicate, "invalid or duplicate root ID")

        global_source, global_build, global_database = (
            write_global_initializer_fixture(first)
        )
        global_output = first / "global-index.json"
        global_run = invoke(
            binary,
            global_database,
            global_output,
            [("source", global_source), ("build", global_build)],
        )
        if global_run.returncode != 0:
            raise AssertionError(
                "global-initializer call indexing failed: "
                f"rc={global_run.returncode} stderr={global_run.stderr!r}"
            )
        global_index = json.loads(global_output.read_text(encoding="utf-8"))
        entities = {
            item["entity"]["entity_id"]: item["entity"]
            for item in global_index["entities"]
        }
        summaries = {
            item["function_entity_id"]: item
            for item in global_index["function_summaries"]
        }
        calls_by_line = {
            item["location"]["line"]: item for item in global_index["callsites"]
        }
        if set(calls_by_line) != {2, 3, 4}:
            raise AssertionError(
                "expected global/method/normal calls at lines 2/3/4, got "
                f"{sorted(calls_by_line)}"
            )
        global_call = calls_by_line[2]
        method_call = calls_by_line[3]
        normal_call = calls_by_line[4]
        global_owner = global_call["caller_function_id"]
        if not global_owner or global_owner not in entities or global_owner not in summaries:
            raise AssertionError(
                "global initializer call lacks an entity- and summary-backed owner"
            )
        if entities[global_owner]["entity_kind"] != "function":
            raise AssertionError("global initializer owner is not function-like")
        if global_call["callsite_id"] not in summaries[global_owner]["callsite_ids"]:
            raise AssertionError("global initializer summary omits its callsite")
        if normal_call["caller_function_id"] == global_owner:
            raise AssertionError("normal function call was conflated with global init")
        method_owner = entities.get(method_call["caller_function_id"])
        if method_owner is None or method_owner["entity_kind"] != "method":
            raise AssertionError(
                "C++ method call was not owned by its method entity"
            )
        if method_call["caller_function_id"] == global_owner:
            raise AssertionError("C++ method call was conflated with global init")
        configured_entities = {
            entity_id
            for entity_id, entity in entities.items()
            if str(entity.get("qualified_signature", "")).startswith(
                "configured:"
            )
        }
        configured_nodes = {
            node["node_id"]
            for node in global_index["semantic_nodes"]
            if node["entity_ref"] in configured_entities
        }
        if not any(
            relation["source_node_id"] == global_call["result_node_id"]
            and relation["target_node_id"] in configured_nodes
            for relation in global_index["semantic_relations"]
        ):
            raise AssertionError(
                "global initializer call result no longer reaches its storage"
            )

        cross_source, cross_build, cross_database = (
            write_cross_tu_initializer_fixture(first)
        )
        cross_output = first / "cross-tu-index.json"
        cross_run = invoke(
            binary,
            cross_database,
            cross_output,
            [("source", cross_source), ("build", cross_build)],
        )
        if cross_run.returncode != 0:
            raise AssertionError(
                "cross-TU initializer indexing failed: "
                f"rc={cross_run.returncode} stderr={cross_run.stderr!r}"
            )
        cross_index = json.loads(cross_output.read_text(encoding="utf-8"))
        cross_entity_records = {
            item["entity"]["entity_id"]: item
            for item in cross_index["entities"]
        }
        cross_entities = {
            entity_id: item["entity"]
            for entity_id, item in cross_entity_records.items()
        }
        shared_entities = [
            item
            for item in cross_entities.values()
            if str(item.get("qualified_signature", "")).startswith(
                "shared_value:"
            )
        ]
        local_entities = [
            item
            for item in cross_entities.values()
            if str(item.get("qualified_signature", "")).startswith(
                "local_value:"
            )
        ]
        if len(shared_entities) != 1:
            raise AssertionError(
                "external inline object did not retain one logical identity"
            )
        if len(
            cross_entity_records[shared_entities[0]["entity_id"]][
                "translation_unit_refs"
            ]
        ) != 2:
            raise AssertionError(
                "external inline object does not record both translation units"
            )
        if len(local_entities) != 2 or any(
            len(
                cross_entity_records[item["entity_id"]][
                    "translation_unit_refs"
                ]
            )
            != 1
            for item in local_entities
        ):
            raise AssertionError(
                "internal-linkage objects were conflated across translation units"
            )
        local_entity_ids = {item["entity_id"] for item in local_entities}
        local_objects = {
            node["abstract_object_id"]
            for node in cross_index["semantic_nodes"]
            if node["entity_ref"] in local_entity_ids
            and node.get("abstract_object_id")
        }
        if len(local_objects) != 2:
            raise AssertionError(
                "internal-linkage objects do not have distinct abstractions"
            )
        initializer_calls = [
            item
            for item in cross_index["callsites"]
            if item["location"]["file"] == "riftpath://v1/source/shared.hpp"
            and item["location"]["line"] in {2, 3}
        ]
        shared_calls = [
            item for item in initializer_calls if item["location"]["line"] == 2
        ]
        local_calls = [
            item for item in initializer_calls if item["location"]["line"] == 3
        ]
        if len(shared_calls) != 1 or len(local_calls) != 2:
            raise AssertionError(
                "initializer owner identity must deduplicate one external ODR "
                "definition and retain two internal definitions"
            )
        for call in initializer_calls:
            owner = cross_entities[call["caller_function_id"]]
            if "\x00" in owner["qualified_signature"]:
                raise AssertionError(
                    "synthetic initializer owner leaks a NUL-delimited signature"
                )
        for call in local_calls:
            reached = {
                relation["target_node_id"]
                for relation in cross_index["semantic_relations"]
                if relation["source_node_id"] == call["result_node_id"]
            }
            reached_entities = {
                node["entity_ref"]
                for node in cross_index["semantic_nodes"]
                if node["node_id"] in reached
            }
            if len(reached_entities & local_entity_ids) != 1:
                raise AssertionError(
                    "an internal initializer path did not reach exactly one "
                    "TU-local object"
                )

    print("PASS production CLI logical-root relocation and fail-closed checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
