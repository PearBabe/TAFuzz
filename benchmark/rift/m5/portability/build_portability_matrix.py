#!/usr/bin/env python3
"""Generate and immediately validate one sealed RIFT-M5 portability matrix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validate_portability_matrix import (
    MatrixError,
    build_matrix_from_spec,
    load_json,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        input_path = args.input.resolve(strict=True)
        matrix = build_matrix_from_spec(load_json(input_path), input_path)
        write_json_atomic(args.output, matrix)
    except (MatrixError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "PASS",
        f"output={args.output.resolve()}",
        f"projects={len(matrix['projects'])}",
        f"matrix_id={matrix['matrix_id']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
