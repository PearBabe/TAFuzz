"""Command-line interface for timed Buchi guidance analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .engine import analyze
from .model import GuidanceConfig, PrefixCost, RuntimePrefix


def _read_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> Iterable[Mapping[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def _write_outputs(output_dir: Path, result: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "guidance.jsonl").open("w", encoding="utf-8") as stream:
        for row in result["guidance"]:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MITL timed-Buchi accepting-lasso fuzz guidance prototype"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--runtime-prefixes", required=True, type=Path)
    parser.add_argument("--pta-prefix-costs", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = GuidanceConfig.from_json(_read_json(args.config))
    runtime = [
        RuntimePrefix.from_json(value, config.state_projection_fields)
        for value in _read_jsonl(args.runtime_prefixes)
    ]
    costs = []
    if args.pta_prefix_costs is not None:
        costs = [PrefixCost.from_json(value) for value in _read_jsonl(args.pta_prefix_costs)]
    result = analyze(config, runtime, costs)
    _write_outputs(args.output_dir, result)
    print(
        f"property={config.property_id} prefixes={len(result['guidance'])} "
        f"lassos={len(result['lasso_candidates'])} "
        f"seeds={len(result['seed_ranking'])}"
    )
    return 0
