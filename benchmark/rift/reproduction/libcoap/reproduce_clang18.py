#!/usr/bin/env python3
"""Reproduce the frozen libcoap Clang/LLVM 18 whole-program IR baseline.

The build directory is intentionally fixed between repetitions so debug paths do
not introduce artificial bitcode differences.  For safety, the script only
removes build directories below /tmp whose basename starts with the dedicated
TAFuzz prefix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import resource
import shlex
import shutil
import subprocess
import time


DEFAULT_SOURCE = pathlib.Path(
    "/home/lqq/project/TAFuzz/benchmark/coap/libcoap"
)
DEFAULT_BUILD = pathlib.Path("/tmp/tafuzz-rift-libcoap-fixed")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_build_dir(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    if resolved.parent != pathlib.Path("/tmp"):
        raise ValueError(f"build directory must be a direct child of /tmp: {resolved}")
    if not resolved.name.startswith("tafuzz-rift-libcoap-"):
        raise ValueError(f"unsafe build-directory name: {resolved.name}")
    return resolved


def run_once(source: pathlib.Path, build: pathlib.Path, jobs: int, run: int) -> dict:
    if build.exists():
        shutil.rmtree(build)

    started = time.monotonic()
    subprocess.run(
        [
            "cmake",
            "-S",
            str(source),
            "-B",
            str(build),
            "-G",
            "Ninja",
            "-DCMAKE_C_COMPILER=/usr/bin/clang-18",
            "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DENABLE_DTLS=OFF",
            "-DENABLE_TESTS=OFF",
            "-DENABLE_DOCS=OFF",
            "-DENABLE_EXAMPLES=OFF",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["cmake", "--build", str(build), "--parallel", str(jobs)],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    compile_db_path = build / "compile_commands.json"
    compile_db = json.loads(compile_db_path.read_text(encoding="utf-8"))
    bitcode_dir = build / "rift-bc"
    bitcode_dir.mkdir()
    modules: list[str] = []

    for index, entry in enumerate(sorted(compile_db, key=lambda item: item["file"])):
        arguments = shlex.split(entry["command"])
        output = bitcode_dir / f"{index:03d}.bc"
        output_index = arguments.index("-o")
        arguments[output_index + 1] = str(output)
        arguments.insert(1, "-emit-llvm")
        subprocess.run(
            arguments,
            cwd=entry["directory"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        modules.append(str(output))

    linked = build / "libcoap-all.bc"
    subprocess.run(
        ["/usr/bin/llvm-link-18", *modules, "-o", str(linked)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "/usr/bin/opt-18",
            "-passes=mem2reg,print<memoryssa>",
            "-disable-output",
            str(linked),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return {
        "run": run,
        "translation_units": len(compile_db),
        "compile_database_sha256": sha256(compile_db_path),
        "static_archive_sha256": sha256(build / "libcoap-3.a"),
        "linked_bitcode_sha256": sha256(linked),
        "linked_bitcode_bytes": linked.stat().st_size,
        "memoryssa_check": "PASS",
        "wall_seconds": round(time.monotonic() - started, 3),
        "child_maxrss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--build-dir", type=pathlib.Path, default=DEFAULT_BUILD)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    source = args.source.resolve()
    build = checked_build_dir(args.build_dir)
    if args.runs < 1:
        parser.error("--runs must be positive")

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    runs = [run_once(source, build, args.jobs, index) for index in range(1, args.runs + 1)]
    stable_fields = (
        "translation_units",
        "compile_database_sha256",
        "static_archive_sha256",
        "linked_bitcode_sha256",
        "linked_bitcode_bytes",
    )
    deterministic = all(len({item[field] for item in runs}) == 1 for field in stable_fields)
    result = {
        "schema_version": 1,
        "source": str(source),
        "source_commit": head,
        "clang_version": subprocess.run(
            ["/usr/bin/clang-18", "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.splitlines()[0],
        "llvm_version": subprocess.run(
            ["/usr/bin/llvm-config-18", "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip(),
        "cmake_options": {
            "build_type": "RelWithDebInfo",
            "build_shared_libs": False,
            "enable_dtls": False,
            "enable_tests": False,
            "enable_docs": False,
            "enable_examples": False,
        },
        "runs": runs,
        "deterministic": deterministic,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if deterministic else 1


if __name__ == "__main__":
    raise SystemExit(main())
