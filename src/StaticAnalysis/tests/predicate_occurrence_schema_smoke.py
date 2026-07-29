#!/usr/bin/env python3
"""Validate the emitted predicate-occurrence sidecar and a fail-closed case."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import subprocess
import tempfile

import jsonschema


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=pathlib.Path)
    parser.add_argument("--schema-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()

    common = json.loads((args.schema_dir / "common.schema.json").read_text())
    schema = json.loads(
        (args.schema_dir / "predicate_occurrence_bindings.schema.json").read_text()
    )
    jsonschema.Draft7Validator.check_schema(schema)
    resolver = jsonschema.RefResolver.from_schema(  # type: ignore[attr-defined]
        schema, store={common["$id"]: common, schema["$id"]: schema}
    )
    validator = jsonschema.Draft7Validator(schema, resolver=resolver)

    with tempfile.TemporaryDirectory(prefix="rift-occurrence-schema-") as directory:
        artifact_path = pathlib.Path(directory) / "occurrences.json"
        completed = subprocess.run(
            [str(args.binary), "--emit", str(artifact_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"smoke binary failed ({completed.returncode}):\n"
                f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
        artifact = json.loads(artifact_path.read_text())
        validator.validate(artifact)

        invalid = copy.deepcopy(artifact)
        invalid["occurrences"][0]["undeclared_project_hint"] = "forbidden"
        errors = list(validator.iter_errors(invalid))
        if not errors:
            raise RuntimeError("schema accepted an undeclared occurrence property")

    print("PASS predicate_occurrence_schema_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
