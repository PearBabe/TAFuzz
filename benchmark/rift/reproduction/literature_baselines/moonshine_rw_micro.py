#!/usr/bin/env python3
"""Reproduce MoonShine's W ∩ R_cond rule on its mlockall/msync example.

The paper's Smatch hooks are not present in the public repository.  This script
therefore uses Clang's JSON AST to implement the published rule on a faithful
micro example, and separately checks the dependency against the official
precomputed implicit-dependency JSON shipped by MoonShine.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable


def children(node: dict[str, Any]) -> list[dict[str, Any]]:
    return [child for child in node.get("inner", []) if isinstance(child, dict)]


def walk(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield node
    for child in children(node):
        yield from walk(child)


def member_key(node: dict[str, Any]) -> str | None:
    if node.get("kind") != "MemberExpr":
        return None
    name = node.get("name")
    if not name:
        return None
    # The micro example has a single named record type.  Keeping the record in
    # the key mirrors MoonShine's struct-and-field summaries.
    return f"vm_area_struct.{name}"


def called_function(node: dict[str, Any]) -> str | None:
    if node.get("kind") != "CallExpr":
        return None
    for descendant in walk(node):
        referenced = descendant.get("referencedDecl")
        if isinstance(referenced, dict) and referenced.get("kind") == "FunctionDecl":
            return referenced.get("name")
    return None


def own_summary(function: dict[str, Any]) -> dict[str, set[str]]:
    writes: set[str] = set()
    conditional_reads: set[str] = set()
    calls: set[str] = set()

    for node in walk(function):
        if node.get("kind") == "BinaryOperator" and node.get("opcode") == "=":
            operands = children(node)
            if operands:
                for lhs_node in walk(operands[0]):
                    key = member_key(lhs_node)
                    if key:
                        writes.add(key)
        elif node.get("kind") == "UnaryOperator" and node.get("opcode") in {
            "++",
            "--",
        }:
            for target in walk(node):
                key = member_key(target)
                if key:
                    writes.add(key)
        elif node.get("kind") == "IfStmt":
            parts = children(node)
            if parts:
                for condition_node in walk(parts[0]):
                    key = member_key(condition_node)
                    if key:
                        conditional_reads.add(key)

        callee = called_function(node)
        if callee:
            calls.add(callee)

    return {
        "writes": writes,
        "conditional_reads": conditional_reads,
        "calls": calls,
    }


def closure(
    name: str,
    summaries: dict[str, dict[str, set[str]]],
    field: str,
    active: set[str] | None = None,
) -> set[str]:
    active = set() if active is None else set(active)
    if name in active or name not in summaries:
        return set()
    active.add(name)
    result = set(summaries[name][field])
    for callee in summaries[name]["calls"]:
        result.update(closure(callee, summaries, field, active))
    return result


def clang_ast(clang: str, source: Path) -> dict[str, Any]:
    command = [
        clang,
        "-std=c11",
        "-fsyntax-only",
        "-Xclang",
        "-ast-dump=json",
        str(source),
    ]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clang", default="clang-18")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--official-map", required=True, type=Path)
    args = parser.parse_args()

    ast = clang_ast(args.clang, args.source.resolve())
    functions = {
        node["name"]: node
        for node in children(ast)
        if node.get("kind") == "FunctionDecl" and node.get("name")
    }
    summaries = {name: own_summary(node) for name, node in functions.items()}

    writer = "mlockall"
    reader = "msync"
    write_set = closure(writer, summaries, "writes")
    conditional_read_set = closure(reader, summaries, "conditional_reads")
    intersection = write_set & conditional_read_set

    official = json.loads(args.official_map.read_text(encoding="utf-8"))
    official_confirms = writer in official.get(reader, [])
    pass_status = bool(intersection) and official_confirms
    result = {
        "schema_version": "rift.literature.moonshine-rw-micro.v1",
        "reproduction_kind": (
            "FAITHFUL_CLANG_MICRO_REPRODUCTION_NOT_ORIGINAL_SMATCH_EXTRACTOR"
        ),
        "rule": "W(upstream_call) ∩ R_cond(target_call) != ∅",
        "writer": writer,
        "reader": reader,
        "writer_transitive_calls": sorted(summaries[writer]["calls"]),
        "write_set": sorted(write_set),
        "conditional_read_set": sorted(conditional_read_set),
        "intersection": sorted(intersection),
        "dependency_edge": f"{writer} -> {reader}" if intersection else None,
        "official_precomputed_map_confirms_edge": official_confirms,
        "official_reader_dependency_count": len(official.get(reader, [])),
        "negative_control": {
            "writer": "unrelated_call",
            "write_set": sorted(closure("unrelated_call", summaries, "writes")),
            "intersection": sorted(
                closure("unrelated_call", summaries, "writes")
                & conditional_read_set
            ),
        },
        "cross_project_general": [
            "conditional-read/write-set intersection",
            "interprocedural summary closure before set intersection",
            "retain upstream call order when materializing dependencies",
        ],
        "project_specific": [
            "Linux syscall entry points and call graph",
            "vm_area_struct.vm_flags and VM_LOCKED semantics",
            "Smatch hook implementation and the shipped Linux dependency table",
        ],
        "status": "PASS" if pass_status else "FAIL",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if pass_status else 1


if __name__ == "__main__":
    raise SystemExit(main())
