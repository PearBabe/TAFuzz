#!/usr/bin/env python3
"""Deterministic fixture analyzer: classify every supplied pair as NO."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

LIMITATION = "Dummy fixture performs no program analysis and predicts NO for every supplied pair."


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def build_result(input_path: Path) -> dict[str, Any]:
    manifest = read_json(input_path)
    cases = []
    for case in manifest["cases"]:
        predictions = []
        for source in sorted(case["source_anchors"], key=lambda item: item["id"]):
            for ap in sorted(case["ap_anchors"], key=lambda item: item["id"]):
                predictions.append(
                    {
                        "source_id": source["id"],
                        "ap_id": ap["id"],
                        "prediction": "NO",
                        "status": "ANALYZED",
                        "edges": [],
                        "evidence": [
                            {
                                "kind": "SUMMARY",
                                "detail": "The deterministic fixture applies its constant NO policy.",
                                "locations": [],
                            }
                        ],
                        "limitations": [LIMITATION],
                    }
                )
        cases.append(
            {
                "case_id": case["case_id"],
                "status": "COMPLETE",
                "predictions": predictions,
                "limitations": [LIMITATION],
            }
        )

    return {
        "schema_version": "rift.baseline-result.v1",
        "analyzer": {
            "id": "dummy.no-influence",
            "version": "1.0.0",
            "implementation": "Deterministic contract fixture; not a static-analysis baseline.",
            "configuration": {"constant_prediction": "NO"},
            "command": [
                "dummy_no_influence.py",
                "--input",
                "analyzer_input.json",
                "--output",
                "dummy_result.json",
            ],
            "artifact_sha256": sha256_file(Path(__file__).resolve()),
        },
        "input_manifest_sha256": sha256_file(input_path),
        "analysis_status": "COMPLETE",
        "execution": {
            "exit_code": 0,
            "wall_seconds": 0.0,
            "peak_rss_bytes": null_peak_rss(),
            "toolchain": [
                {"name": "python", "version": platform.python_version()}
            ],
            "analyzed_units": len(cases),
        },
        "cases": cases,
        "limitations": [LIMITATION],
    }


def null_peak_rss() -> None:
    """The fixture does not self-measure RSS; wrappers may replace this null."""
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_result(args.input.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"PASS cases={len(result['cases'])} output={args.output.resolve()} "
        "policy=NO"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
