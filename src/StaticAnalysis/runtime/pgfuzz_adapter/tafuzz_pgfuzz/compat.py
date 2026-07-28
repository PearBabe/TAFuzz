from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from .common import write_lines
from .states import RESULT_GROUPS


def initialise_result_directories(run_dir: Path) -> None:
    for directory_name in ["results", "results_legacy"]:
        directory = run_dir / directory_name
        directory.mkdir(parents=True, exist_ok=True)
        for group in RESULT_GROUPS:
            path = directory / f"{group}.txt"
            if not path.exists():
                path.write_text("", encoding="utf-8")


def regenerate_result_files(run_dir: Path,
                            effects: Iterable[Mapping[str, object]]) -> None:
    initialise_result_directories(run_dir)
    confirmed: dict[str, set[str]] = {group: set() for group in RESULT_GROUPS}
    legacy: dict[str, set[str]] = {group: set() for group in RESULT_GROUPS}
    for effect in effects:
        input_name = str(effect["input_name"])
        for group in effect.get("confirmed_groups", []):
            if str(group) in confirmed:
                confirmed[str(group)].add(input_name)
        for group in effect.get("legacy_groups", []):
            if str(group) in legacy:
                legacy[str(group)].add(input_name)
    for group in RESULT_GROUPS:
        write_lines(run_dir / "results" / f"{group}.txt", confirmed[group])
        write_lines(run_dir / "results_legacy" / f"{group}.txt", legacy[group])
