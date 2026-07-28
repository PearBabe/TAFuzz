from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import sys

from .catalog import build_catalog
from .common import OUTPUT_ROOT, ensure_empty_new_directory
from .engine import run_experiment


def default_run_id(prefix: str) -> str:
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="pgfuzz_dynamic.py",
        description="PGFuzz-compatible current-ArduCopter dynamic input profiler")
    subparsers = result.add_subparsers(dest="command", required=True)

    catalog = subparsers.add_parser(
        "catalog", help="discover current parameters, commands, modes, and RC inputs")
    catalog.add_argument("--run-id", default=None)
    catalog.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    catalog.add_argument("--parameter-snapshot", type=Path)
    catalog.add_argument("--metadata-json", type=Path)
    catalog.add_argument("--udp-port", type=int, default=19401)
    catalog.add_argument("--param-timeout", type=float, default=120.0)

    run = subparsers.add_parser("run", help="execute or preview current-safe work items")
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--preset", choices=["current_safe_full"],
                     default="current_safe_full")
    run.add_argument("--input", action="append", default=[])
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--shard-index", type=int, default=0)
    run.add_argument("--shard-count", type=int, default=1)
    run.add_argument("--repetitions", type=int, default=3)
    run.add_argument("--window-seconds", type=float, default=2.0)
    run.add_argument("--udp-port", type=int, default=19501)

    smoke = subparsers.add_parser("smoke", help="run the three gated smoke cases")
    smoke.add_argument("--run-id", default=None)
    smoke.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    smoke.add_argument("--udp-port", type=int, default=19601)
    smoke.add_argument("--case", action="append",
                       choices=["parameter", "command", "environment"],
                       default=[])

    report = subparsers.add_parser("report", help="regenerate the human-readable report")
    report.add_argument("--run-dir", type=Path, required=True)
    return result


def catalog_command(args: argparse.Namespace) -> int:
    run_id = args.run_id or default_run_id("catalog")
    run_dir = args.output_root / run_id
    ensure_empty_new_directory(run_dir)
    result = build_catalog(
        run_dir, parameter_snapshot=args.parameter_snapshot,
        metadata_json=args.metadata_json, udp_port=args.udp_port,
        param_timeout=args.param_timeout)
    counts = result["manifest"]["counts"]
    print(f"catalog COMPLETE: {run_dir}")
    print(f"INPUT_P={counts['input_p']} INPUT_C={counts['input_c']} "
          f"INPUT_E={counts['input_e']} READY_SAFE={counts['ready_safe']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "catalog":
        return catalog_command(args)
    if args.command == "run":
        selected = set(args.input) if args.input else None
        result = run_experiment(
            args.run_dir, selected, args.shard_index, args.shard_count,
            args.repetitions, args.window_seconds, args.dry_run, args.resume,
            udp_port=args.udp_port)
        print(f"experiment plan: {result['plan']['work_item_count']} work items")
        print("DRY_RUN: no input was executed" if result["dry_run"]
              else f"completed effects: {len(result['effects'])}")
        return 0
    if args.command == "smoke":
        from .smoke import smoke_command
        return smoke_command(args)
    if args.command == "report":
        from .report import write_report
        write_report(args.run_dir)
        print(f"report generated: {args.run_dir / 'report.md'}")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
