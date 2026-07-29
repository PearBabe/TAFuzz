#!/usr/bin/env python3
"""Validate the frozen ArduPilot RIFT-M1 build evidence."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).rstrip("\n")


def check_database(label: str, record: dict, errors: list[str]) -> None:
    snapshot = HERE / record["snapshot_path"]
    if not snapshot.is_file():
        errors.append(f"{label}: missing snapshot {snapshot}")
        return
    actual_snapshot_hash = sha256_file(snapshot)
    if actual_snapshot_hash != record["snapshot_sha256"]:
        errors.append(
            f"{label}: snapshot hash {actual_snapshot_hash} != "
            f"{record['snapshot_sha256']}"
        )
        return

    raw = gzip.decompress(snapshot.read_bytes())
    actual_raw_hash = sha256_bytes(raw)
    if actual_raw_hash != record["raw_sha256"]:
        errors.append(
            f"{label}: decompressed hash {actual_raw_hash} != {record['raw_sha256']}"
        )
    if len(raw) != record["raw_size_bytes"]:
        errors.append(
            f"{label}: decompressed size {len(raw)} != {record['raw_size_bytes']}"
        )

    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON: {exc}")
        return
    if not isinstance(entries, list):
        errors.append(f"{label}: top-level compile database is not a list")
        return
    if len(entries) != record["entries"]:
        errors.append(f"{label}: entries {len(entries)} != {record['entries']}")

    compilers = Counter()
    unique = set()
    arguments_entries = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry {index} is not an object")
            continue
        if not {"directory", "file"}.issubset(entry):
            errors.append(f"{label}: entry {index} lacks directory/file")
            continue
        arguments = entry.get("arguments")
        if isinstance(arguments, list):
            arguments_entries += 1
            if arguments:
                compilers[arguments[0]] += 1
        else:
            errors.append(f"{label}: entry {index} has no arguments array")
        unique.add((entry["directory"], entry["file"]))

    if arguments_entries != record["arguments_entries"]:
        errors.append(
            f"{label}: arguments entries {arguments_entries} != "
            f"{record['arguments_entries']}"
        )
    if len(unique) != record["unique_files"]:
        errors.append(f"{label}: unique entries {len(unique)} != {record['unique_files']}")
    if dict(compilers) != record["compilers"]:
        errors.append(
            f"{label}: compiler counts {dict(compilers)!r} != {record['compilers']!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=WORKSPACE / "baseline" / "ardupilot",
        help="ArduPilot checkout to validate against the frozen source facts",
    )
    parser.add_argument(
        "--skip-live-source",
        action="store_true",
        help="validate stored evidence without requiring a live checkout",
    )
    parser.add_argument(
        "--require-temp-build",
        action="store_true",
        help="also require the ephemeral /tmp Clang binary and verify its hash",
    )
    args = parser.parse_args()

    manifest = read_json(HERE / "build_manifest.json")
    facts = read_json(HERE / "gcs_failsafe_source_facts.json")
    errors: list[str] = []
    notes: list[str] = []

    check_database(
        "gcc-existing", manifest["existing_gcc_compile_database"], errors
    )
    check_database(
        "clang18-isolated",
        manifest["clang18_isolated_build"]["compile_database"],
        errors,
    )

    for name in (
        "clang18-configure.exitcode",
        "clang18-configure-isolated.exitcode",
        "clang18-copter.exitcode",
        "clang18-arducopter-help.exitcode",
    ):
        path = HERE / "raw" / name
        if not path.is_file() or path.read_text(encoding="utf-8").strip() != "0":
            errors.append(f"stored successful exit code missing or invalid: {path}")

    if manifest["result"]["ap_binding_analysis"] != "NOT_RUN":
        errors.append("manifest must not claim an AP binding analysis")
    if manifest["result"]["fuzz_experiment"] != "NOT_RUN":
        errors.append("manifest must not claim a fuzz experiment")
    if facts["status"] != "READ_ONLY_SOURCE_FACTS_NOT_RIFT_ANALYSIS":
        errors.append("source-facts status overstates the evidence")

    if not args.skip_live_source:
        repo = args.repo.resolve()
        if not (repo / ".git").exists():
            errors.append(f"live repository not found: {repo}")
        else:
            actual_commit = git(repo, "rev-parse", "HEAD")
            if actual_commit != manifest["source"]["commit"]:
                errors.append(
                    f"source commit {actual_commit} != {manifest['source']['commit']}"
                )
            actual_tree = git(repo, "rev-parse", "HEAD^{tree}")
            if actual_tree != manifest["source"]["tree"]:
                errors.append(f"source tree {actual_tree} != {manifest['source']['tree']}")
            actual_status = git(repo, "status", "--short")
            if actual_status != manifest["source"]["post_build_status"]:
                errors.append(
                    f"source status {actual_status!r} != frozen "
                    f"{manifest['source']['post_build_status']!r}"
                )
            lock = repo / ".lock-waf_linux_build"
            if (
                not lock.is_file()
                or sha256_file(lock)
                != manifest["source"]["standard_waf_lock_sha256_after"]
            ):
                errors.append("standard source Waf lock differs from the preserved baseline")

            for source in facts["source_files"]:
                path = repo / source["path"]
                if not path.is_file():
                    errors.append(f"missing source-fact file: {path}")
                elif sha256_file(path) != source["sha256"]:
                    errors.append(f"source-fact file hash differs: {path}")

    binary_record = manifest["clang18_isolated_build"]["binary"]
    binary = Path(binary_record["path"])
    if binary.is_file():
        actual = sha256_file(binary)
        if actual != binary_record["sha256"]:
            errors.append(f"ephemeral binary hash {actual} != {binary_record['sha256']}")
        else:
            notes.append("ephemeral Clang binary hash verified")
    elif args.require_temp_build:
        errors.append(f"ephemeral Clang binary is absent: {binary}")
    else:
        notes.append("ephemeral Clang binary absent; stored build evidence only")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    print("- both compressed compile databases match their raw hashes and counts")
    print("- stored configure/build/help exit codes are zero")
    if not args.skip_live_source:
        print("- source commit, tree, status, Waf lock, and GCS evidence files match")
    for note in notes:
        print(f"- {note}")
    print("- no AP binding, SITL scenario, or fuzz result is claimed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
