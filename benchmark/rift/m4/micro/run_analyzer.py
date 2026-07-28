#!/usr/bin/env python3
"""Run all four production stages, then seal a complete M4 micro run.

No evaluation module is imported and no private label file is opened here.
The final manifest is emitted only after every case has produced four valid,
hash-linked production artifacts with complete candidate accounting.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from command_adapter import (
    DEFAULT_ADAPTER,
    OUTPUT_NAMES,
    argument_file_entries,
    load_adapter,
    render_commands,
    sandbox_command,
)
from common import (
    AcceptanceError,
    DEFAULT_CORPUS,
    LOCAL_SCHEMA_DIR,
    SCHEMA_MIGRATION_LEDGER,
    artifact_entry,
    production_schema_tree_sha256,
    sha256_file,
    validate_schema,
    write_json,
)
from validate_acceptance import RUN_MANIFEST, validate_bundle, validate_case_artifacts, validate_run


def _write_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_all(
    *,
    bundle: Path,
    output: Path,
    analyzer: Path,
    adapter_path: Path,
    timeout: int,
    expected_cases: int,
    sandbox: Path = Path("/usr/bin/bwrap"),
    denied_read_roots: tuple[Path, ...] = (DEFAULT_CORPUS,),
) -> dict[str, Any]:
    bundle = bundle.resolve()
    output = output.resolve()
    analyzer = analyzer.resolve(strict=True)
    adapter_path = adapter_path.resolve(strict=True)
    sandbox = sandbox.resolve(strict=True)
    denied_read_roots = tuple(path.resolve(strict=True) for path in denied_read_roots)
    if not os.access(analyzer, os.X_OK):
        raise AcceptanceError(f"analyzer is not executable: {analyzer}")
    if output.exists():
        raise AcceptanceError(f"refusing to mix or overwrite an existing run: {output}")
    if timeout < 1:
        raise AcceptanceError("--timeout must be positive")
    input_manifest = validate_bundle(bundle, expected_cases=expected_cases)
    adapter = load_adapter(adapter_path)
    output.mkdir(parents=True)
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    case_records: list[dict[str, Any]] = []

    for input_case in input_manifest["cases"]:
        case_id = input_case["case_id"]
        case_directory = output / "cases" / case_id
        case_directory.mkdir(parents=True)
        commands = render_commands(
            adapter,
            analyzer,
            bundle / input_case["compile_database"]["path"],
            bundle / input_case["property_ir"]["path"],
            case_directory,
        )
        stage_records: list[dict[str, Any]] = []
        for command in commands:
            argument_files = argument_file_entries(command["argv"], bundle)
            execution_argv = sandbox_command(
                sandbox=sandbox,
                logical_argv=command["argv"],
                bundle=bundle,
                writable_result_directory=case_directory,
                denied_read_roots=list(denied_read_roots),
            )
            try:
                completed = subprocess.run(
                    execution_argv,
                    cwd=bundle,
                    env=environment,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise AcceptanceError(
                    f"{case_id}:{command['name']} timed out after {timeout}s; run remains unsealed"
                ) from error
            stdout_path = case_directory / "logs" / f"{command['name']}.stdout.txt"
            stderr_path = case_directory / "logs" / f"{command['name']}.stderr.txt"
            _write_log(stdout_path, completed.stdout)
            _write_log(stderr_path, completed.stderr)
            if completed.returncode != 0:
                raise AcceptanceError(
                    f"{case_id}:{command['name']} exited {completed.returncode}; "
                    f"see {stderr_path}; run remains unsealed"
                )
            for produced_name in command["outputs"]:
                produced = Path(produced_name)
                if not produced.is_file():
                    raise AcceptanceError(
                        f"{case_id}:{command['name']} did not produce {produced}; "
                        "run remains unsealed"
                    )
            stage_records.append(
                {
                    "name": command["name"],
                    "argv": command["argv"],
                    "execution_argv": execution_argv,
                    "argument_files": argument_files,
                    "exit_code": completed.returncode,
                    "stdout": artifact_entry(output, stdout_path.relative_to(output).as_posix()),
                    "stderr": artifact_entry(output, stderr_path.relative_to(output).as_posix()),
                }
            )

        artifacts = {
            key: artifact_entry(
                output,
                (case_directory / filename).relative_to(output).as_posix(),
            )
            for key, filename in OUTPUT_NAMES.items()
        }
        certificate_path = case_directory / "analysis_certificate.json"
        if not certificate_path.is_file():
            raise AcceptanceError(
                f"{case_id}: analyzer did not produce analysis_certificate.json; "
                "run remains unsealed"
            )
        artifacts["analysis_certificate"] = artifact_entry(
            output, certificate_path.relative_to(output).as_posix()
        )
        validate_case_artifacts(bundle, output, input_case, artifacts)
        case_records.append(
            {
                "case_id": case_id,
                "status": "COMPLETE",
                "input_hashes": {
                    "compile_database_sha256": input_case["compile_database"]["sha256"],
                    "property_ir_sha256": input_case["property_ir"]["sha256"],
                },
                "artifacts": artifacts,
                "stages": stage_records,
            }
        )
    run = {
        "schema_version": "rift.m4.micro-run.v2",
        "input_manifest_sha256": sha256_file(bundle / "manifest.json"),
        "schema_migration_ledger_sha256": sha256_file(SCHEMA_MIGRATION_LEDGER),
        "production_schema_tree_sha256": production_schema_tree_sha256(),
        "analyzer": {"path": str(analyzer), "sha256": sha256_file(analyzer)},
        "adapter_config_sha256": sha256_file(adapter_path),
        "sandbox": {
            "engine": {"path": str(sandbox), "sha256": sha256_file(sandbox)},
            "root_filesystem_read_only": True,
            "network_isolated": True,
            "private_process_namespace": True,
            "denied_read_roots": sorted(str(path) for path in set(denied_read_roots)),
        },
        "analysis_complete": True,
        "all_cases_completed_before_seal": True,
        "evaluation_not_started": True,
        "case_count": len(case_records),
        "cases": case_records,
    }
    validate_schema(
        run,
        LOCAL_SCHEMA_DIR / "analysis_run_manifest.schema.json",
        "sealed analyzer run",
    )
    write_json(output / RUN_MANIFEST, run)
    validate_run(
        bundle,
        output,
        adapter_path=adapter_path,
        expected_cases=expected_cases,
    )
    return run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--expected-cases", type=int, default=120)
    parser.add_argument("--sandbox", type=Path, default=Path("/usr/bin/bwrap"))
    parser.add_argument(
        "--deny-read-root",
        type=Path,
        action="append",
        default=[DEFAULT_CORPUS],
        help="directory hidden from analyzer; repeat for additional private corpora",
    )
    arguments = parser.parse_args()
    try:
        run = run_all(
            bundle=arguments.bundle,
            output=arguments.output,
            analyzer=arguments.analyzer,
            adapter_path=arguments.adapter,
            timeout=arguments.timeout,
            expected_cases=arguments.expected_cases,
            sandbox=arguments.sandbox,
            denied_read_roots=tuple(arguments.deny_read_root),
        )
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        AcceptanceError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "PASS",
        f"phase=sealed-run cases={run['case_count']}",
        f"manifest={arguments.output.resolve() / RUN_MANIFEST}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
