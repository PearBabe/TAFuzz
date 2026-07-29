#!/usr/bin/env python3
"""Validate the frozen SVF 3.2 build and rerun the minimal WPA smoke."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
RIFT_ROOT = HERE.parents[1]
SOURCE = RIFT_ROOT / "external" / "svf"
MANIFEST_PATH = HERE / "artifact_manifest.json"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
MEMORY_LIMIT_KIB = 12 * 1024 * 1024


def fail(message: str) -> None:
    raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        fail(f"{label} failed with {result.returncode}:\n{result.stdout}\n{result.stderr}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def peak_rss(log: str) -> int:
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", log)
    if not match:
        fail("missing peak RSS metric")
    return int(match.group(1))


def main() -> int:
    manifest = json.loads(read(MANIFEST_PATH))
    if manifest["status"] != "REPRODUCED_MINIMAL_WPA_SVFG_SMOKE":
        fail("unexpected reproduction status")

    artifact = manifest["artifact"]
    git_head = run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"])
    require_success(git_head, "git rev-parse HEAD")
    if git_head.stdout.strip() != artifact["commit"]:
        fail("SVF commit mismatch")

    git_tree = run(["git", "-C", str(SOURCE), "rev-parse", "HEAD^{tree}"])
    require_success(git_tree, "git rev-parse tree")
    if git_tree.stdout.strip() != artifact["tree"]:
        fail("SVF tree mismatch")

    git_tag = run(["git", "-C", str(SOURCE), "describe", "--tags", "--exact-match"])
    require_success(git_tag, "git exact tag")
    if git_tag.stdout.strip() != artifact["tag"]:
        fail("SVF tag mismatch")

    git_status = run(["git", "-C", str(SOURCE), "status", "--porcelain", "--untracked-files=all"])
    require_success(git_status, "git status")
    if git_status.stdout.strip():
        fail(f"official SVF source is dirty:\n{git_status.stdout}")

    for relative, metadata in manifest["files"].items():
        path = (HERE / relative).resolve()
        if not path.is_file():
            fail(f"missing frozen file: {relative}")
        observed = sha256(path)
        if observed != metadata["sha256"]:
            fail(f"hash mismatch for {relative}: {observed}")
        if "size" in metadata and path.stat().st_size != metadata["size"]:
            fail(f"size mismatch for {relative}")

    configure_log = read(HERE / "raw" / "configure.log")
    build_log = read(HERE / "raw" / "build.log")
    ctest_log = read(HERE / "raw" / "ctest-list.log")
    smoke_log = ANSI.sub("", read(HERE / "raw" / "wpa-smoke.log"))

    for needle in (
        "C compiler identification is Clang 18.1.8",
        "CXX compiler identification is Clang 18.1.8",
        "LLVM major version:         18",
        "LLVM version string:        18.1.8",
        "Z3 version string:    4.8.12.0",
        "Exit status: 0",
    ):
        if needle not in configure_log:
            fail(f"configure evidence missing: {needle}")

    if "[124/124] Linking CXX executable bin/ae" not in build_log:
        fail("build did not record completion of all 124 targets")
    if "Exit status: 0" not in build_log:
        fail("build exit status is not zero")
    if "Total Tests: 0" not in ctest_log:
        fail("upstream Test-Suite availability evidence changed")
    if (SOURCE / "Test-Suite").exists():
        fail("Test-Suite now exists; refresh the manifest and run it")

    for log in (configure_log, build_log, smoke_log):
        if peak_rss(log) > MEMORY_LIMIT_KIB:
            fail("recorded execution exceeded the 12 GiB RSS limit")

    for oracle in ("MAYALIAS", "NOALIAS"):
        if f"SUCCESS :{oracle}" not in smoke_log:
            fail(f"missing {oracle} success oracle")
    if "FAILURE :" in smoke_log or "test case failed" in smoke_log:
        fail("recorded WPA smoke contains a failed oracle")
    if not re.search(r"Memory SSA Statistics.*?MemRegions\s+8", smoke_log, re.S):
        fail("recorded MemorySSA evidence changed")
    if not re.search(r"SVFG Statistics.*?TotalEdge\s+75.*?TotalNode\s+78", smoke_log, re.S):
        fail("recorded SVFG evidence changed")
    if "Exit status: 0" not in smoke_log:
        fail("recorded WPA exit status is not zero")

    bitcode = HERE / "results" / "alias_valueflow_smoke.bc"
    verify = run(["/usr/bin/opt-18", "-passes=verify", "-disable-output", str(bitcode)])
    require_success(verify, "LLVM bitcode verifier")

    wpa = HERE / "build" / "bin" / "wpa"
    linked = run(["ldd", str(wpa)])
    require_success(linked, "ldd wpa")
    if "not found" in linked.stdout:
        fail(f"wpa has unresolved shared libraries:\n{linked.stdout}")

    rerun = run(
        [str(wpa), "-ander", "-alias-check", "-svfg", "-stat", bitcode.name],
        cwd=bitcode.parent,
        timeout=60,
    )
    require_success(rerun, "live WPA smoke")
    live = ANSI.sub("", rerun.stdout + rerun.stderr)
    for oracle in ("MAYALIAS", "NOALIAS"):
        if f"SUCCESS :{oracle}" not in live:
            fail(f"live WPA smoke missed {oracle}")
    if not re.search(r"SVFG Statistics.*?TotalEdge\s+75.*?TotalNode\s+78", live, re.S):
        fail("live WPA smoke produced unexpected SVFG size")

    api_binary = HERE / "api-build" / "svf_api_smoke"
    if not api_binary.is_file() or not api_binary.stat().st_mode & 0o111:
        fail("external CMake consumer was not compiled and linked")
    if "Linking CXX executable svf_api_smoke" not in read(HERE / "raw" / "api-build.log"):
        fail("external consumer link evidence missing")

    print(
        "PASS: SVF-3.2 commit/tag/tree clean; LLVM18 build 124/124; "
        "WPA MAYALIAS+NOALIAS; MemorySSA=8 regions; SVFG=78 nodes/75 edges; "
        "RSS within 12 GiB"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
