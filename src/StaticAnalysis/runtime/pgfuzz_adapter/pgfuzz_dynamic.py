#!/usr/bin/env python3
"""Stable command-line entry point for the PGFuzz dynamic adapter."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tafuzz_pgfuzz.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
