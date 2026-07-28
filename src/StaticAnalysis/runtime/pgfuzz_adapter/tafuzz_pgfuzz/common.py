from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any, Iterable, Mapping, Sequence


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(__file__).resolve().parents[5]
ARDUPILOT_ROOT = WORKSPACE / "baseline/ardupilot"
PGFUZZ_ROOT = WORKSPACE / "baseline/pgfuzz"
OUTPUT_ROOT = WORKSPACE / "output/pgfuzz_dynamic"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True,
                  allow_nan=False)
        handle.write("\n")
    temporary.replace(path)


def append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), allow_nan=False))
        handle.write("\n")
        handle.flush()


def write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = sorted({str(line).strip() for line in lines if str(line).strip()})
    path.write_text("".join(f"{line}\n" for line in unique), encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]],
              fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: scalar_csv(row.get(key)) for key in fieldnames})


def scalar_csv(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
    return "" if value is None else value


def run_text(command: Sequence[str], cwd: Path | None = None,
             check: bool = False) -> dict[str, Any]:
    completed = subprocess.run(
        list(command), cwd=str(cwd) if cwd else None, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    result = {
        "command": shlex.join(str(part) for part in command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {result['command']}\n"
            f"{completed.stderr}")
    return result


def git_head(root: Path) -> str:
    return run_text(["git", "-C", str(root), "rev-parse", "HEAD"],
                    check=True)["stdout"].strip()


def ensure_empty_new_directory(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"output directory already exists: {path}")
    path.mkdir(parents=True)


def isolated_environment(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
