#!/usr/bin/env python3
"""Validate the frozen RIFT-M1 literature-baseline evidence.

The validator is intentionally read-only outside a temporary directory.  It
re-runs the deterministic importers and smoke examples, checks the frozen Git
revisions, and verifies that known upstream/environment failures remain
explicit rather than being converted into false PASS results.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
LTL = WORKSPACE / "benchmark" / "rift" / "external" / "ltl_fuzzer"
MOONSHINE = WORKSPACE / "benchmark" / "rift" / "external" / "moonshine"
PGFUZZ = WORKSPACE / "baseline" / "pgfuzz"
RESULTS = HERE / "results"

EXPECTED = {
    "ltl_commit": "716ac301fa3a8ea39814bc80eeebba49c19c1378",
    "moonshine_commit": "95e5f6dfd2760a9d763fc2bc90623c9e1e74e804",
    "pgfuzz_commit": "7eaebf21116087249b8329d4ba7337a24a34ecb9",
    "pgfuzz_tree": "a8a8f4af20c6ea92f6e518ff8619e24acc571c44",
    "ltl_targets_sha256": "389ade92bb8a268da4ef466664411d3f66b4c6892547de41b068aee8f03e90a5",
    "pgfuzz_silver_sha256": "98918c3f421e11b11a635c254a96eaef8a219beb3dc4d28e64370b93cac09970",
    "moonshine_map_sha256": "9410603d383da0ddbbbf277be0e7e4b8a6c24771db82119e94788a7393db8f06",
    "moonshine_result_sha256": "fbd2dba3b3ab0dc8c0c7257104f8a5b88951dd035a0dc56e1db1582cab4edf30",
    "ltl_property_pdf_sha256": "a1dc7ec43ce08f177538429f0a03a074e4bca3d99c820805a95061bb70d06fb7",
    "pgfuzz_pdf_sha256": "bb057be0069e9e764c8fb4bf963b09311cc914f3fb60da0b121afa94c90d7fcd",
    "moonshine_pdf_sha256": "b7705ad1f69b29d65ab42d875c001acda32d328b8bc08e2a9e6ba76093a2ae12",
    "problem1_stdout_sha256": "c36b41a3c5084091e8ec091a5e3bf24dc16f3833f6214984564ba8bf152c342b",
    "problem1_stderr_sha256": "a09af258a5afb4752bc8e92b98ed5552135b2be8dcf259854685b3ce4b22d840",
    "automata_output_sha256": "c4360800972379af4d5ed3482929520bf702036981f799631a9a8229c41888ae",
    "automata_binary_sha256": "5c4fd18734fa25c9fcd14ad8df2d8f97f5f732072bf7d9725fc25c971fc6ae62",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        list(args),
        cwd=cwd or WORKSPACE,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git(repo: Path, *args: str) -> str:
    return run("git", "-C", str(repo), *args).stdout.decode().strip()


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []
    skips: list[str] = []

    def expect(condition: bool, label: str, detail: str = "") -> None:
        if condition:
            passes.append(label)
        else:
            failures.append(f"{label}: {detail or 'condition was false'}")

    def expect_hash(path: Path, expected: str, label: str) -> None:
        if not path.is_file():
            failures.append(f"{label}: missing {path}")
            return
        actual = sha256(path)
        expect(actual == expected, label, f"expected {expected}, got {actual}")

    try:
        json.loads((HERE / "reproduction_manifest.json").read_text(encoding="utf-8"))
        passes.append("reproduction manifest parses")
    except Exception as error:  # pragma: no cover - diagnostic path
        failures.append(f"reproduction manifest parses: {error}")

    revisions = (
        (LTL, "ltl_commit", "LTL-Fuzzer frozen commit"),
        (MOONSHINE, "moonshine_commit", "MoonShine frozen commit"),
        (PGFUZZ, "pgfuzz_commit", "PGFuzz frozen commit"),
    )
    for repo, key, label in revisions:
        try:
            expect(git(repo, "rev-parse", "HEAD") == EXPECTED[key], label)
            expect(
                git(repo, "diff", "--name-only", "HEAD", "--") == "",
                f"{label} tracked files unchanged",
                "tracked diff is non-empty",
            )
        except Exception as error:
            failures.append(f"{label}: {error}")
    try:
        expect(
            git(PGFUZZ, "rev-parse", "HEAD^{tree}") == EXPECTED["pgfuzz_tree"],
            "PGFuzz frozen tree",
        )
    except Exception as error:
        failures.append(f"PGFuzz frozen tree: {error}")

    expect_hash(
        HERE / "ltl_fuzzer_ap_targets.json",
        EXPECTED["ltl_targets_sha256"],
        "LTL target manifest hash",
    )
    expect_hash(
        HERE / "pgfuzz_56_policy_silver.json",
        EXPECTED["pgfuzz_silver_sha256"],
        "PGFuzz silver manifest hash",
    )
    expect_hash(
        MOONSHINE / "implicit-dependencies" / "implicit_dependencies.json",
        EXPECTED["moonshine_map_sha256"],
        "MoonShine official dependency map hash",
    )
    expect_hash(
        RESULTS / "moonshine" / "moonshine_rw_result.json",
        EXPECTED["moonshine_result_sha256"],
        "MoonShine micro result hash",
    )
    expect_hash(
        LTL / "ltl-property" / "LTL-Properties.pdf",
        EXPECTED["ltl_property_pdf_sha256"],
        "LTL artifact property PDF hash",
    )
    expect_hash(
        PGFUZZ / "Kim 等 - 2021 - PGFUZZ Policy-guided fuzzing for robotic vehicles.pdf",
        EXPECTED["pgfuzz_pdf_sha256"],
        "PGFuzz paper PDF hash",
    )
    moonshine_pdf = Path(
        "/mnt/c/Users/PC-123/Zotero/storage/3JQHSKMJ/"
        "Pailoor 等 - 2018 - {MoonShine} Optimizing {OS} fuzzer seed selection "
        "with trace distillation.pdf"
    )
    if moonshine_pdf.is_file():
        expect_hash(
            moonshine_pdf,
            EXPECTED["moonshine_pdf_sha256"],
            "MoonShine paper PDF hash",
        )
    else:
        skips.append("MoonShine Zotero PDF is outside the workspace and unavailable")

    ltl_manifest = load(HERE / "ltl_fuzzer_ap_targets.json")
    expect(
        ltl_manifest["summary"]
        == {
            "rers_output_targets": 46,
            "resolved_exactly": 46,
            "telnet_protocol_targets": 3,
            "total_target_tuples": 49,
            "unresolved": 3,
        },
        "LTL target counts",
        repr(ltl_manifest.get("summary")),
    )
    expect(
        ltl_manifest["telnet"]["gitmodules_present"] is False
        and ltl_manifest["telnet"]["source_available"] is False,
        "LTL Telnet incompleteness retained",
    )
    expect(
        set(ltl_manifest["telnet"]["identifier_inconsistencies"])
        == {"WILLDISABLED", "WILL_DISABLED"},
        "LTL Telnet identifier mismatch retained",
    )

    pg_manifest = load(HERE / "pgfuzz_56_policy_silver.json")
    pg_summary = pg_manifest["summary"]
    expect(pg_manifest["classification"] == "SILVER_STANDARD_NOT_GROUND_TRUTH", "PGFuzz silver label")
    expect(pg_summary["paper_policy_count"] == 56, "PGFuzz paper policy count")
    expect(pg_summary["paper_policies_with_public_map"] == 51, "PGFuzz public-map coverage")
    expect(pg_summary["paper_policies_without_public_map"] == 5, "PGFuzz missing-map count")
    expect(pg_summary["artifact_map_directory_count"] == 49, "PGFuzz physical map count")
    expect(
        pg_summary["missing_policy_ids"]
        == ["PP.Hover", "PP.HoverZ", "PP.HoverC", "PP.TAKEOFF1", "PP.HOME1"],
        "PGFuzz missing policy identities",
    )
    expect(
        pg_summary["unreferenced_artifact_map_directories"] == ["PX.CHUTE"],
        "PGFuzz unreferenced map retained",
    )

    official_map = load(
        MOONSHINE / "implicit-dependencies" / "implicit_dependencies.json"
    )
    unique_edges = {(reader, writer) for reader, writers in official_map.items() for writer in writers}
    expect(len(official_map) == 228, "MoonShine official reader count")
    expect(len(unique_edges) == 9891, "MoonShine official unique edge count")
    expect(len(official_map.get("msync", [])) == 13, "MoonShine msync dependency count")
    expect("mlockall" in official_map.get("msync", []), "MoonShine official mlockall-to-msync edge")

    moon_result = load(RESULTS / "moonshine" / "moonshine_rw_result.json")
    expect(moon_result["status"] == "PASS", "MoonShine saved micro result")
    expect(
        moon_result["reproduction_kind"]
        == "FAITHFUL_CLANG_MICRO_REPRODUCTION_NOT_ORIGINAL_SMATCH_EXTRACTOR",
        "MoonShine micro non-impersonation label",
    )
    expect(
        moon_result["intersection"] == ["vm_area_struct.vm_flags"],
        "MoonShine saved intersection",
    )
    expect(moon_result["negative_control"]["intersection"] == [], "MoonShine saved negative control")

    expect(
        (RESULTS / "ltl_fuzzer" / "llvm14_instrumentation_build.exit_code")
        .read_text(encoding="utf-8")
        .strip()
        == "2",
        "LTL LLVM14 failure exit code retained",
    )
    llvm_failure = (RESULTS / "ltl_fuzzer" / "llvm14_instrumentation_build.log").read_text(
        encoding="utf-8"
    )
    expect(
        "F_None" in llvm_failure and "CreateConstGEP2_64" in llvm_failure,
        "LTL LLVM14 failure diagnostics retained",
    )
    expect(
        (RESULTS / "moonshine" / "official_build.exit_code").read_text().strip()
        == "2",
        "MoonShine build failure exit code retained",
    )
    expect(
        "ragel: No such file or directory"
        in (RESULTS / "moonshine" / "official_build.log").read_text(encoding="utf-8"),
        "MoonShine build blocker retained",
    )

    expect_hash(
        RESULTS / "ltl_fuzzer" / "problem1.stdout",
        EXPECTED["problem1_stdout_sha256"],
        "saved Problem1 stdout hash",
    )
    expect_hash(
        RESULTS / "ltl_fuzzer" / "problem1.stderr",
        EXPECTED["problem1_stderr_sha256"],
        "saved Problem1 stderr hash",
    )
    expect_hash(
        RESULTS / "ltl_fuzzer" / "automata_smoke.tsv",
        EXPECTED["automata_output_sha256"],
        "saved automata smoke hash",
    )
    expect_hash(
        RESULTS / "ltl_fuzzer" / "ltl-automata-smoke",
        EXPECTED["automata_binary_sha256"],
        "saved automata smoke binary hash",
    )
    automata_receipt = (
        RESULTS / "ltl_fuzzer" / "automata_smoke_receipt.txt"
    ).read_text(encoding="utf-8")
    expect(
        "claim=ORIGINAL_LTL_FUZZER_AUTOMATA_COMPONENT_ON_PUBLIC_PROBLEM1_NOT_END_TO_END_CAMPAIGN"
        in automata_receipt,
        "automata claim boundary retained",
    )
    expect(
        "compile_exit_code=0" in automata_receipt
        and "run_exit_code=0" in automata_receipt,
        "automata exact-command exit codes retained",
    )

    with tempfile.TemporaryDirectory(prefix="rift-literature-", dir="/tmp") as temporary:
        temp = Path(temporary)
        try:
            regenerated_ltl = run(
                "python3",
                str(HERE / "import_ltl_fuzzer_targets.py"),
                str(LTL),
            ).stdout
            expect(
                regenerated_ltl == (HERE / "ltl_fuzzer_ap_targets.json").read_bytes(),
                "LTL importer byte reproducibility",
            )
        except Exception as error:
            failures.append(f"LTL importer byte reproducibility: {error}")

        try:
            regenerated_pg = run(
                "python3",
                str(HERE / "import_pgfuzz_silver.py"),
                str(WORKSPACE),
            ).stdout
            expect(
                regenerated_pg == (HERE / "pgfuzz_56_policy_silver.json").read_bytes(),
                "PGFuzz importer byte reproducibility",
            )
        except Exception as error:
            failures.append(f"PGFuzz importer byte reproducibility: {error}")

        try:
            regenerated_moon = run(
                "python3",
                str(HERE / "moonshine_rw_micro.py"),
                "--clang",
                "clang-18",
                "--source",
                str(HERE / "moonshine_mlockall_msync.c"),
                "--official-map",
                str(MOONSHINE / "implicit-dependencies" / "implicit_dependencies.json"),
            ).stdout
            expect(
                regenerated_moon
                == (RESULTS / "moonshine" / "moonshine_rw_result.json").read_bytes(),
                "MoonShine micro byte reproducibility",
            )
        except Exception as error:
            failures.append(f"MoonShine micro byte reproducibility: {error}")

        problem1_binary = temp / "Problem1"
        try:
            run(
                "clang-18",
                "-std=c11",
                "-O0",
                "-g",
                "-I",
                str(LTL / "include"),
                str(LTL / "experiment" / "Problem1" / "src" / "Problem1.c"),
                "-o",
                str(problem1_binary),
            )
            execution = run(
                str(problem1_binary),
                str(LTL / "experiment" / "Problem1" / "input_folder" / "input"),
            )
            expect(
                execution.stdout
                == (RESULTS / "ltl_fuzzer" / "problem1.stdout").read_bytes(),
                "Problem1 stdout replay",
            )
            expect(
                execution.stderr
                == (RESULTS / "ltl_fuzzer" / "problem1.stderr").read_bytes(),
                "Problem1 stderr replay",
            )
            event_counts = collections.Counter(execution.stdout.decode().splitlines())
            expect(
                event_counts
                == {
                    "16": 2,
                    "17": 1,
                    "18": 3,
                    "19": 1,
                    "20": 2,
                    "21": 1,
                    "24": 1,
                    "25": 90,
                    "26": 6,
                },
                "Problem1 event counts",
                repr(event_counts),
            )
        except Exception as error:
            failures.append(f"Problem1 replay: {error}")

        automata_binary = temp / "ltl-automata-smoke"
        try:
            run(
                "g++",
                "-std=c++17",
                "-O2",
                "-I",
                str(LTL / "include"),
                str(HERE / "ltl_automata_smoke.cc"),
                str(LTL / "build" / "src" / "automata" / "libautomata.a"),
                "-lspot",
                "-lbddx",
                "-o",
                str(automata_binary),
            )
            automata = run(
                str(automata_binary),
                str(LTL / "experiment" / "Problem1" / "ltl_dir" / "ltl.txt"),
                str(HERE / "rers_smoke_events.txt"),
            )
            expect(
                automata.stdout
                == (RESULTS / "ltl_fuzzer" / "automata_smoke.tsv").read_bytes(),
                "LTL Automata output replay",
            )
            expect(automata.stderr == b"", "LTL Automata replay stderr empty")
        except Exception as error:
            failures.append(f"LTL Automata replay: {error}")

    pycache_entries = sorted(HERE.rglob("__pycache__")) + sorted(HERE.rglob("*.pyc"))
    expect(
        not pycache_entries,
        "delivery tree contains no Python bytecode cache",
        ", ".join(str(path) for path in pycache_entries),
    )

    for label in passes:
        print(f"PASS  {label}")
    for label in skips:
        print(f"SKIP  {label}")
    for label in failures:
        print(f"FAIL  {label}")
    print(
        f"SUMMARY pass={len(passes)} skip={len(skips)} fail={len(failures)} "
        f"status={'PASS' if not failures else 'FAIL'}"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
