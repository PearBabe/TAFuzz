#!/usr/bin/env python3
"""Single adaptation point between the M4 acceptance harness and ``tafuzz-sa``.

The acceptance and evaluation code never constructs CLI arguments itself.
If the public CLI changes, only ``default_adapter.json`` (or an explicitly
supplied compatible adapter file) needs to change.
"""

from __future__ import annotations

import argparse
import json
import string
import sys
from pathlib import Path
from typing import Any

from common import AcceptanceError, HERE, read_json, sha256_file


DEFAULT_ADAPTER = HERE / "default_adapter.json"
ALLOWED_STAGE_NAMES = {"index", "bind", "influence"}
OUTPUT_NAMES = {
    "semantic_index": "semantic_index.json",
    "ap_bindings": "ap_bindings.json",
    "contextual_influence_graph": "contextual_influence_graph.json",
    "ap_influence_cones": "ap_influence_cones.json",
}
ALLOWED_PLACEHOLDERS = {
    "analyzer",
    "compile_database",
    "property_ir",
    "output_directory",
    *OUTPUT_NAMES,
}


def load_adapter(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise AcceptanceError("adapter config is not an object")
    if value.get("schema_version") != "rift.m4.command-adapter.v1":
        raise AcceptanceError("unsupported adapter schema_version")
    stages = value.get("stages")
    if not isinstance(stages, list) or not 1 <= len(stages) <= 3:
        raise AcceptanceError("adapter must define one to three public CLI stages")
    seen_outputs: set[str] = set()
    seen_names: set[str] = set()
    formatter = string.Formatter()
    for stage in stages:
        if not isinstance(stage, dict) or set(stage) != {"name", "argv", "produces"}:
            raise AcceptanceError("malformed adapter stage")
        name = stage["name"]
        if name not in ALLOWED_STAGE_NAMES or name in seen_names:
            raise AcceptanceError(f"invalid or duplicate public CLI stage {name}")
        seen_names.add(name)
        produces = stage["produces"]
        if not isinstance(produces, list) or not produces:
            raise AcceptanceError(f"adapter stage {name} has no declared outputs")
        if len(produces) != len(set(produces)) or not set(produces) <= set(OUTPUT_NAMES):
            raise AcceptanceError(f"adapter stage {name} has invalid outputs")
        overlap = seen_outputs & set(produces)
        if overlap:
            raise AcceptanceError(f"duplicate adapter outputs {sorted(overlap)}")
        seen_outputs.update(produces)
        argv = stage["argv"]
        if not isinstance(argv, list) or len(argv) < 2 or not all(
            isinstance(item, str) and item for item in argv
        ):
            raise AcceptanceError(f"adapter stage {name} has invalid argv")
        if argv[0] != "{analyzer}":
            raise AcceptanceError(
                f"adapter stage {name} must execute the frozen analyzer as argv[0]"
            )
        fields = {
            field_name
            for argument in argv
            for _, field_name, _, _ in formatter.parse(argument)
            if field_name is not None
        }
        unknown = fields - ALLOWED_PLACEHOLDERS
        if unknown:
            raise AcceptanceError(f"adapter stage {name} has unknown fields {sorted(unknown)}")
        if "analyzer" not in fields:
            raise AcceptanceError(f"adapter stage {name} does not invoke analyzer")
        if not fields & (set(OUTPUT_NAMES) | {"output_directory"}):
            raise AcceptanceError(f"adapter stage {name} does not name an output location")
    if seen_outputs != set(OUTPUT_NAMES):
        raise AcceptanceError("adapter does not produce the four required artifacts")
    return value


def render_commands(
    adapter: dict[str, Any],
    analyzer: Path,
    compile_database: Path,
    property_ir: Path,
    output_directory: Path,
) -> list[dict[str, Any]]:
    values = {
        "analyzer": str(analyzer.resolve()),
        "compile_database": str(compile_database.resolve()),
        "property_ir": str(property_ir.resolve()),
        "output_directory": str(output_directory.resolve()),
    }
    for key, filename in OUTPUT_NAMES.items():
        values[key] = str((output_directory / filename).resolve())
    rendered = []
    for stage in adapter["stages"]:
        rendered.append(
            {
                "name": stage["name"],
                "produces": stage["produces"],
                "outputs": [values[name] for name in stage["produces"]],
                "argv": [argument.format_map(values) for argument in stage["argv"]],
            }
        )
    return rendered


def argument_file_entries(argv: list[str], cwd: Path) -> list[dict[str, str]]:
    """Hash every regular file named directly by the executed argv."""
    discovered: dict[str, Path] = {}
    for argument in argv:
        candidates = [argument]
        if "=" in argument:
            candidates.append(argument.split("=", 1)[1])
        for candidate in candidates:
            path = Path(candidate)
            if not path.is_absolute():
                path = cwd / path
            try:
                resolved = path.resolve(strict=True)
            except OSError:
                continue
            if resolved.is_file():
                discovered[str(resolved)] = resolved
    return [
        {"path": path, "sha256": sha256_file(resolved)}
        for path, resolved in sorted(discovered.items())
    ]


def sandbox_command(
    *,
    sandbox: Path,
    logical_argv: list[str],
    bundle: Path,
    writable_result_directory: Path,
    denied_read_roots: list[Path],
) -> list[str]:
    command = [
        str(sandbox.resolve()),
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--bind",
        "/tmp",
        "/tmp",
    ]
    for root in sorted({path.resolve() for path in denied_read_roots}, key=str):
        command.extend(["--tmpfs", str(root)])
    result = writable_result_directory.resolve()
    command.extend(
        [
            "--bind",
            str(result),
            str(result),
            "--chdir",
            str(bundle.resolve()),
            "--",
            *logical_argv,
        ]
    )
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--compile-database", type=Path, required=True)
    parser.add_argument("--property-ir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        adapter = load_adapter(arguments.adapter)
        commands = render_commands(
            adapter,
            arguments.analyzer,
            arguments.compile_database,
            arguments.property_ir,
            arguments.output_dir,
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError, AcceptanceError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(json.dumps(commands, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
