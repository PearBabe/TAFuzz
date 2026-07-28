#!/usr/bin/env python3
"""Negative fixture: a run must fail if analyzer tries to read private corpus."""

from pathlib import Path


Path("/home/lqq/project/TAFuzz/benchmark/rift/gold/manifest.json").read_text(
    encoding="utf-8"
)
raise SystemExit("private corpus unexpectedly readable")
