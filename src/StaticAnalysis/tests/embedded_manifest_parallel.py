#!/usr/bin/env python3
"""Regression for concurrent embedded-manifest generation.

The build graph must expose one producer, and the generator itself must remain
atomic when independent verification processes happen to invoke it together.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", type=pathlib.Path, required=True)
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    options = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="rift-manifest-parallel-") as raw:
        output = pathlib.Path(raw)
        header = output / "rift_build_manifest.h"
        manifest = output / "rift_build_manifest.json"
        command = [
            sys.executable,
            str(options.generator),
            "--source-root",
            str(options.source_root),
            "--output-header",
            str(header),
            "--output-json",
            str(manifest),
        ]
        processes = [
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(12)
        ]
        failures: list[str] = []
        for index, process in enumerate(processes):
            stdout, stderr = process.communicate(timeout=45)
            if process.returncode != 0:
                failures.append(
                    f"worker {index} exit={process.returncode} "
                    f"stdout={stdout!r} stderr={stderr!r}"
                )
        if failures:
            raise SystemExit("\n".join(failures))

        document = json.loads(manifest.read_text(encoding="utf-8"))
        if document.get("schema_version") != "rift.build-manifest.v1":
            raise SystemExit("concurrent output has the wrong schema version")
        manifest_sha256 = hashlib.sha256(manifest.read_bytes()).hexdigest()
        header_text = header.read_text(encoding="utf-8")
        if manifest_sha256 not in header_text:
            raise SystemExit("header does not bind the final manifest bytes")
        leftovers = sorted(output.glob("*.tmp"))
        if leftovers:
            raise SystemExit(
                "temporary files survived concurrent generation: "
                + ", ".join(path.name for path in leftovers)
            )

    print("PASS concurrent embedded-manifest generation workers=12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
