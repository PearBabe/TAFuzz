#!/usr/bin/env python3
"""文件功能：下载、校验并运行 FORMATS 2020 Romeo 基准，解析前/后向成本与资源数据。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


ARCHIVE_URL = (
    "https://web.archive.org/web/20220214052637id_/"
    "http://romeo.rts-software.org/releases/FORMATS2020.tgz"
)
ARCHIVE_SHA256 = "6045841f964a5e37fcb6354eae6999355f8e308292406ff5a09412bccd2d9a29"

QUICK_MODELS = ("aircraft3", "aircraft4", "scheduling2", "scheduling3")
FULL_MODELS = (
    "aircraft3",
    "aircraft4",
    "aircraft5",
    "aircraft6",
    "scheduling2",
    "scheduling3",
    "scheduling4",
    "scheduling5",
    "scheduling_original",
)
QUICK_ORACLES = {
    "aircraft3": "-1140",
    "aircraft4": "-4140",
    "scheduling2": "-1760",
    "scheduling3": "-2560",
}

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
COST_RE = re.compile(r"^\s*=\s*([^\s]+)\s*$")
TIME_RE = re.compile(
    r"Time:\s*([0-9]+(?:\.[0-9]+)?)s\s*\(total\)\s*=\s*"
    r"([0-9]+(?:\.[0-9]+)?)s\s*\(user\)\s*\+\s*"
    r"([0-9]+(?:\.[0-9]+)?)s\s*\(system\)"
)
MEMORY_RE = re.compile(r"Max memory used:\s*([0-9]+(?:\.[0-9]+)?)([A-Za-z]+)")


class HarnessError(RuntimeError):
    """表示下载、归档或运行环境不满足复现实验的前置条件。"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def cache_directory(argument: str | None) -> Path:
    if argument:
        return Path(argument).expanduser().resolve()
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".cache"
    return (root / "tafuzz" / "formats2020").resolve()


def download_archive(target: Path, timeout: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.part-{os.getpid()}")
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "TAFuzz-FORMATS2020-reproduction/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise HarnessError(f"下载返回 HTTP {response.status}: {ARCHIVE_URL}")
            with temporary.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
        actual = sha256_file(temporary)
        if actual != ARCHIVE_SHA256:
            raise HarnessError(
                f"下载归档 SHA-256 不匹配：expected={ARCHIVE_SHA256}, actual={actual}"
            )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def obtain_archive(args: argparse.Namespace) -> Path:
    if args.archive:
        archive = Path(args.archive).expanduser().resolve()
        if not archive.is_file():
            raise HarnessError(f"指定归档不存在：{archive}")
    else:
        cache = cache_directory(args.cache_dir)
        archive = cache / f"FORMATS2020-{ARCHIVE_SHA256[:12]}.tgz"
        if args.force_download:
            archive.unlink(missing_ok=True)
        if not archive.exists():
            print(f"[download] {ARCHIVE_URL}", file=sys.stderr, flush=True)
            download_archive(archive, args.download_timeout)

    actual = sha256_file(archive)
    if actual != ARCHIVE_SHA256:
        raise HarnessError(
            f"归档 SHA-256 不匹配：expected={ARCHIVE_SHA256}, actual={actual}, file={archive}"
        )
    return archive


def validate_archive_members(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        member_path = (destination / member.name).resolve()
        try:
            member_path.relative_to(root)
        except ValueError as error:
            raise HarnessError(f"归档包含越界路径：{member.name}") from error
        if member.issym() or member.islnk() or member.isdev():
            raise HarnessError(f"归档包含不允许的特殊成员：{member.name}")
        if not (member.isdir() or member.isfile()):
            raise HarnessError(f"归档包含未知成员类型：{member.name}")


def extract_archive(archive_path: Path, extraction_root: Path) -> Path:
    marker = extraction_root / ".archive.sha256"
    model_root = extraction_root / "FORMATS2020"
    if extraction_root.exists() and any(extraction_root.iterdir()):
        if marker.is_file() and marker.read_text(encoding="ascii").strip() == ARCHIVE_SHA256:
            if model_root.is_dir():
                return model_root
        raise HarnessError(
            f"解包目录非空且不是同一归档的完整缓存，拒绝覆盖：{extraction_root}"
        )

    extraction_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        validate_archive_members(archive, extraction_root)
        archive.extractall(extraction_root)
    atomic_write_text(marker, f"{ARCHIVE_SHA256}\n")
    if not model_root.is_dir():
        raise HarnessError("归档中缺少 FORMATS2020 目录")
    return model_root


def decimal_cost(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    aliases = {
        "+infinity": "Infinity",
        "infinity": "Infinity",
        "+inf": "Infinity",
        "inf": "Infinity",
        "-infinity": "-Infinity",
        "-inf": "-Infinity",
    }
    try:
        return Decimal(aliases.get(normalized, value))
    except InvalidOperation:
        return None


def memory_to_mb(value: float, unit: str) -> float | None:
    factors = {
        "o": 1.0 / 1_000_000,
        "ko": 1.0 / 1_000,
        "mo": 1.0,
        "go": 1_000.0,
        "b": 1.0 / 1_000_000,
        "kb": 1.0 / 1_000,
        "mb": 1.0,
        "gb": 1_000.0,
        "kib": 1024.0 / 1_000_000,
        "mib": 1024.0 * 1024.0 / 1_000_000,
        "gib": 1024.0 * 1024.0 * 1024.0 / 1_000_000,
    }
    factor = factors.get(unit.lower())
    return None if factor is None else value * factor


def empty_mode_metrics() -> dict[str, Any]:
    return {
        "cost": None,
        "total_seconds": None,
        "user_seconds": None,
        "system_seconds": None,
        "max_memory_value": None,
        "max_memory_unit": None,
        "max_memory_mb": None,
    }


def parse_romeo_output(stdout: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    clean = ANSI_RE.sub("", stdout).replace("\r", "")
    modes = {"forward": empty_mode_metrics(), "backward": empty_mode_metrics()}
    current: str | None = None
    errors: list[str] = []

    for line in clean.splitlines():
        if "Checking backward mincost" in line:
            current = "backward"
            continue
        if "Checking mincost" in line:
            current = "forward"
            continue
        if current is None:
            continue

        cost_match = COST_RE.match(line)
        if cost_match:
            modes[current]["cost"] = cost_match.group(1)
            continue

        time_match = TIME_RE.search(line)
        if time_match:
            modes[current]["total_seconds"] = float(time_match.group(1))
            modes[current]["user_seconds"] = float(time_match.group(2))
            modes[current]["system_seconds"] = float(time_match.group(3))
            continue

        memory_match = MEMORY_RE.search(line)
        if memory_match:
            value = float(memory_match.group(1))
            unit = memory_match.group(2)
            modes[current]["max_memory_value"] = value
            modes[current]["max_memory_unit"] = unit
            modes[current]["max_memory_mb"] = memory_to_mb(value, unit)

    for name, metrics in modes.items():
        for field in ("cost", "total_seconds", "user_seconds", "system_seconds"):
            if metrics[field] is None:
                errors.append(f"{name} 缺少 {field}")
        if metrics["max_memory_value"] is None:
            errors.append(f"{name} 缺少 max_memory")
        elif metrics["max_memory_mb"] is None:
            errors.append(f"{name} 的 memory unit 无法识别：{metrics['max_memory_unit']}")
        if metrics["cost"] is not None and decimal_cost(metrics["cost"]) is None:
            errors.append(f"{name} cost 无法精确解析：{metrics['cost']}")
    return modes, errors


def decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def execute_with_timeout(
    command: list[str], timeout: float
) -> tuple[int | None, bool, str, str, float]:
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=None if timeout == 0 else timeout)
        return process.returncode, False, stdout, stderr, time.monotonic() - started
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            tail_out, tail_err = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            tail_out, tail_err = process.communicate()
        # 第二次 communicate 在 Python 中返回完整已收集输出；仅在实现未返回时
        # 才退回 TimeoutExpired 携带的前缀，避免把前缀重复写入审计日志。
        stdout = decode_output(tail_out) or decode_output(error.stdout)
        stderr = decode_output(tail_err) or decode_output(error.stderr)
        return process.returncode, True, stdout, stderr, time.monotonic() - started


def run_model(
    model: str,
    model_root: Path,
    romeo_binary: Path,
    timeout: float,
    raw_directory: Path,
) -> dict[str, Any]:
    model_file = model_root / f"{model}.cts"
    if not model_file.is_file():
        raise HarnessError(f"归档中缺少模型：{model_file}")

    command = [str(romeo_binary), "-v", str(model_file)]
    print(f"[run] {model}", file=sys.stderr, flush=True)
    returncode, timed_out, stdout, stderr, wall_seconds = execute_with_timeout(
        command, timeout
    )
    atomic_write_text(raw_directory / f"{model}.stdout.txt", stdout)
    atomic_write_text(raw_directory / f"{model}.stderr.txt", stderr)

    modes, parse_errors = parse_romeo_output(f"{stdout}\n{stderr}")
    forward_cost = decimal_cost(modes["forward"]["cost"])
    backward_cost = decimal_cost(modes["backward"]["cost"])
    costs_equal = (
        forward_cost is not None
        and backward_cost is not None
        and forward_cost == backward_cost
    )
    expected = QUICK_ORACLES.get(model)
    expected_cost = decimal_cost(expected)
    expected_match = (
        expected is None
        or (
            forward_cost is not None
            and backward_cost is not None
            and forward_cost == expected_cost
            and backward_cost == expected_cost
        )
    )

    failures: list[str] = list(parse_errors)
    if timed_out:
        failures.append(f"超过单模型 timeout={timeout}s")
    if returncode != 0:
        failures.append(f"Romeo 返回码为 {returncode}")
    if not costs_equal:
        failures.append("forward/backward cost 不一致或不可解析")
    if not expected_match:
        failures.append(f"不符合 quick oracle {expected}")

    return {
        "model": model,
        "model_file": model_file.name,
        "command": [romeo_binary.name, "-v", model_file.name],
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_seconds": round(wall_seconds, 6),
        "expected_cost": expected,
        "forward": modes["forward"],
        "backward": modes["backward"],
        "costs_equal": costs_equal,
        "expected_match": expected_match,
        "passed": not failures,
        "failures": failures,
        "raw_stdout": f"raw/{model}.stdout.txt",
        "raw_stderr": f"raw/{model}.stderr.txt",
    }


def csv_rows(results: Iterable[dict[str, Any]], suite: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        forward = result["forward"]
        backward = result["backward"]
        rows.append(
            {
                "suite": suite,
                "model": result["model"],
                "passed": result["passed"],
                "returncode": result["returncode"],
                "timed_out": result["timed_out"],
                "expected_cost": result["expected_cost"],
                "forward_cost": forward["cost"],
                "backward_cost": backward["cost"],
                "costs_equal": result["costs_equal"],
                "expected_match": result["expected_match"],
                "wall_seconds": result["wall_seconds"],
                "forward_total_seconds": forward["total_seconds"],
                "forward_user_seconds": forward["user_seconds"],
                "forward_system_seconds": forward["system_seconds"],
                "forward_max_memory_mb": forward["max_memory_mb"],
                "backward_total_seconds": backward["total_seconds"],
                "backward_user_seconds": backward["user_seconds"],
                "backward_system_seconds": backward["system_seconds"],
                "backward_max_memory_mb": backward["max_memory_mb"],
                "failures": " | ".join(result["failures"]),
            }
        )
    return rows


def write_reports(
    output_directory: Path,
    suite: str,
    archive: Path,
    romeo_binary: Path,
    timeout: float,
    results: list[dict[str, Any]],
) -> tuple[Path, Path]:
    passed = sum(1 for result in results if result["passed"])
    report = {
        "schema_version": 1,
        "artifact": {
            "source_url": ARCHIVE_URL,
            "sha256": ARCHIVE_SHA256,
            "archive": str(archive),
            "romeo_binary": str(romeo_binary),
        },
        "environment": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "suite": suite,
        "timeout_seconds_per_model": timeout,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "all_passed": passed == len(results),
        },
        "results": results,
        "interpretation": (
            "该报告复现原版 Romeo artifact 的 forward/backward 对照；"
            "它不替代新 MoniTAal Priced-DBM 实现自身的正确性测试。"
        ),
    }

    json_path = output_directory / "romeo_benchmarks.json"
    csv_path = output_directory / "romeo_benchmarks.csv"
    atomic_write_text(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    rows = csv_rows(results, suite)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(csv_path, buffer.getvalue())
    return json_path, csv_path


def positive_or_zero_float(text: str) -> float:
    value = float(text)
    if value < 0:
        raise argparse.ArgumentTypeError("必须大于等于 0")
    return value


def positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="复现 FORMATS 2020 Romeo forward/backward 最优成本实验"
    )
    parser.add_argument("--suite", choices=("quick", "full"), default="quick")
    parser.add_argument(
        "--archive",
        help="使用已下载的 FORMATS2020.tgz；仍会强制校验固定 SHA-256",
    )
    parser.add_argument(
        "--cache-dir",
        help="下载缓存目录；默认 $XDG_CACHE_HOME/tafuzz/formats2020",
    )
    parser.add_argument(
        "--extract-dir",
        help="持久解包目录；未指定时使用运行期临时目录并在结束后删除",
    )
    parser.add_argument("--romeo-binary", help="覆盖归档内 Linux romeo-cli 路径")
    parser.add_argument("--output-dir", default="romeo-results", help="JSON/CSV/raw 输出目录")
    parser.add_argument(
        "--timeout",
        type=positive_or_zero_float,
        default=1200.0,
        help="每个模型 timeout 秒数；0 表示不限制（默认 1200）",
    )
    parser.add_argument(
        "--download-timeout",
        type=positive_float,
        default=60.0,
        help="归档下载连接 timeout 秒数（默认 60）",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="忽略下载缓存并重新下载（与 --archive 互斥）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.archive and args.force_download:
        parser.error("--archive 与 --force-download 不能同时使用")
    if args.romeo_binary and not args.extract_dir and not args.archive:
        # 合法但通常是误配置；不阻止用户使用系统安装的兼容 binary。
        pass

    output_directory = Path(args.output_dir).expanduser().resolve()
    raw_directory = output_directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)

    try:
        archive = obtain_archive(args)
        with ExitStack() as stack:
            if args.extract_dir:
                extraction_root = (
                    Path(args.extract_dir).expanduser().resolve()
                    / f"formats2020-{ARCHIVE_SHA256[:12]}"
                )
            else:
                temporary = stack.enter_context(
                    tempfile.TemporaryDirectory(prefix="tafuzz-formats2020-")
                )
                extraction_root = Path(temporary)

            model_root = extract_archive(archive, extraction_root)
            romeo_binary = (
                Path(args.romeo_binary).expanduser().resolve()
                if args.romeo_binary
                else model_root / "romeo-cli"
            )
            if not romeo_binary.is_file():
                raise HarnessError(f"Romeo binary 不存在：{romeo_binary}")
            romeo_binary.chmod(romeo_binary.stat().st_mode | 0o100)

            models = QUICK_MODELS if args.suite == "quick" else FULL_MODELS
            results = [
                run_model(
                    model,
                    model_root,
                    romeo_binary,
                    args.timeout,
                    raw_directory,
                )
                for model in models
            ]
            json_path, csv_path = write_reports(
                output_directory,
                args.suite,
                archive,
                romeo_binary,
                args.timeout,
                results,
            )
    except (HarnessError, OSError, tarfile.TarError) as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2

    passed = sum(1 for result in results if result["passed"])
    print(
        f"[summary] {passed}/{len(results)} passed; JSON={json_path}; CSV={csv_path}",
        file=sys.stderr,
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
