#!/usr/bin/env python3
"""Read-only structural validation for the PX4 specification-candidate draft."""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

import yaml


PX4_DIR = Path(__file__).resolve().parents[1]
TAFUZZ_DIR = Path(__file__).resolve().parents[3]
FROZEN_DIR = TAFUZZ_DIR / "baseline" / "px4"
EXPECTED_COMMIT = "d6f12ad1c4f70ad3230afd7d86e971421e02fef4"


def fail(message: str) -> None:
    raise AssertionError(message)


def read_yaml(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def line_count(path: Path) -> int:
    with path.open("rb") as stream:
        return sum(1 for _ in stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_source_anchor(path_text: str, lines_text, context: str) -> None:
    source = FROZEN_DIR / path_text
    if not source.is_file():
        fail(f"{context}: missing frozen source {path_text}")
    match = re.fullmatch(r"(\d+)(?:-(\d+))?", str(lines_text))
    if not match:
        fail(f"{context}: invalid line anchor {lines_text!r}")
    start = int(match.group(1))
    end = int(match.group(2) or start)
    total = line_count(source)
    if start < 1 or end < start or end > total:
        fail(f"{context}: out-of-range {path_text}:{start}-{end} (file has {total})")


def main() -> int:
    property_paths = sorted((PX4_DIR / "properties").glob("*.yaml"))
    if len(property_paths) != 14:
        fail(f"expected 14 property files, found {len(property_paths)}")

    bindings_doc = read_yaml(PX4_DIR / "ap_bindings.yaml")
    ap_ids = {entry["ap_id"] for entry in bindings_doc["ap_bindings"]}
    if len(ap_ids) != len(bindings_doc["ap_bindings"]):
        fail("duplicate AP IDs")
    for entry in bindings_doc["ap_bindings"]:
        for location in entry.get("source_locations", []):
            check_source_anchor(location["path"], location["lines"], entry["ap_id"])

    with (PX4_DIR / "mavlink_observability_draft.csv").open("r", encoding="utf-8", newline="") as stream:
        observation_rows = list(csv.DictReader(stream))
    obs_ids = {row["observation_id"] for row in observation_rows}
    if not obs_ids:
        fail("empty MAVLink observation ledger")

    property_ids = set()
    for path in property_paths:
        doc = read_yaml(path)
        property_id = doc.get("property_id")
        if property_id in property_ids:
            fail(f"duplicate property ID {property_id}")
        property_ids.add(property_id)
        if path.stem != property_id:
            fail(f"filename/ID mismatch: {path.name} vs {property_id}")
        if doc.get("implementation_satisfaction") != "NOT_ASSESSED":
            fail(f"{property_id}: implementation satisfaction was changed")
        if doc.get("mitl", {}).get("status") != "NOT_VALIDATED":
            fail(f"{property_id}: MITL status was changed")
        for source in doc.get("normative_basis", []):
            check_source_anchor(source["path"], source["lines"], property_id)
        missing_aps = set(doc.get("atomic_propositions", [])) - ap_ids
        if missing_aps:
            fail(f"{property_id}: unknown AP refs {sorted(missing_aps)}")
        missing_obs = set(doc.get("mavlink_observation_refs", [])) - obs_ids
        if missing_obs:
            fail(f"{property_id}: unknown observation refs {sorted(missing_obs)}")

    with (PX4_DIR / "candidate_index.csv").open("r", encoding="utf-8", newline="") as stream:
        candidate_rows = list(csv.DictReader(stream))
    indexed_ids = {row["property_id"] for row in candidate_rows}
    if indexed_ids != property_ids:
        fail(f"candidate index mismatch: missing={property_ids-indexed_ids}, extra={indexed_ids-property_ids}")
    for row in candidate_rows:
        if not (PX4_DIR / row["file"]).is_file():
            fail(f"candidate index missing file {row['file']}")
        if row["formula_status"] != "NOT_VALIDATED":
            fail(f"{row['property_id']}: formula status was changed")

    with (PX4_DIR / "corpus_manifest.csv").open("r", encoding="utf-8", newline="") as stream:
        corpus_rows = list(csv.DictReader(stream))
    for row in corpus_rows:
        source = FROZEN_DIR / row["path"]
        if not source.is_file():
            fail(f"corpus manifest missing source {row['path']}")
        actual_lines = line_count(source)
        if actual_lines != int(row["line_count"]):
            fail(f"line-count drift {row['path']}: {actual_lines} != {row['line_count']}")
        actual_hash = sha256(source)
        if actual_hash != row["sha256"]:
            fail(f"SHA-256 drift {row['path']}: {actual_hash} != {row['sha256']}")

    for name in ("source_conflicts.yaml", "exclusions.yaml"):
        read_yaml(PX4_DIR / name)
    for name in ("coverage_ledger.csv", "mavlink_observability_draft.csv"):
        with (PX4_DIR / name).open("r", encoding="utf-8", newline="") as stream:
            if not list(csv.DictReader(stream)):
                fail(f"empty ledger {name}")

    print(
        f"OK: commit={EXPECTED_COMMIT} properties={len(property_ids)} "
        f"aps={len(ap_ids)} observations={len(obs_ids)} corpus_files={len(corpus_rows)}"
    )
    print("OK: all candidates remain NOT_ASSESSED and MITL NOT_VALIDATED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
