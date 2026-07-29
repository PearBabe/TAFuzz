#!/usr/bin/env python3
"""Build the deterministic, answer-free RIFT-M4 micro analyzer bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import AcceptanceError, DEFAULT_CORPUS, prepare_bundle, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oracle-commitment-sha256", required=True)
    arguments = parser.parse_args()
    try:
        manifest = prepare_bundle(
            arguments.corpus,
            arguments.output,
            arguments.oracle_commitment_sha256,
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError, AcceptanceError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    output = arguments.output.resolve()
    print(
        "PASS",
        f"cases={manifest['case_count']}",
        f"aps={manifest['ap_count']}",
        f"manifest_sha256={sha256_file(output / 'manifest.json')}",
        f"output={output}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
