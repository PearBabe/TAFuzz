#!/usr/bin/env python3
"""Create an explicitly scoped compile database for a selected-TU probe.

The output is never evidence for a full-project run.  A receipt records the
input digest, requested suffixes, selected entry indices, and omitted count so
that a selected probe cannot later be presented as complete-project evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--source-suffix", action="append", required=True)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    raw = options.input.read_bytes()
    document = json.loads(raw)
    if not isinstance(document, list) or not all(isinstance(item, dict) for item in document):
        raise SystemExit("compile database must be a JSON array of objects")

    requested = sorted(set(normalized_path(item) for item in options.source_suffix))
    selected: list[dict[str, Any]] = []
    selected_indices: list[int] = []
    matches: dict[str, list[int]] = {item: [] for item in requested}
    for index, entry in enumerate(document):
        source = entry.get("file")
        if not isinstance(source, str) or not source:
            raise SystemExit(f"compile database entry {index} has no file")
        source = normalized_path(source)
        hit = [suffix for suffix in requested if source == suffix or source.endswith("/" + suffix)]
        if not hit:
            continue
        selected.append(entry)
        selected_indices.append(index)
        for suffix in hit:
            matches[suffix].append(index)

    missing = [suffix for suffix, indices in matches.items() if not indices]
    if missing:
        raise SystemExit("requested source suffixes were not found: " + ", ".join(missing))

    rendered = json.dumps(selected, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(rendered, encoding="utf-8")
    receipt = {
        "schema_version": "rift-selected-compile-db-receipt/1.0.0",
        "scope_claim": "SELECTED_TRANSLATION_UNITS_ONLY",
        "input_path": str(options.input.resolve()),
        "input_sha256": digest_bytes(raw),
        "input_entries": len(document),
        "requested_source_suffixes": requested,
        "matching_entry_indices": matches,
        "selected_entry_indices": selected_indices,
        "selected_entries": len(selected),
        "omitted_entries": len(document) - len(selected),
        "output_path": str(options.output.resolve()),
        "output_sha256": digest_bytes(rendered.encode("utf-8")),
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"SELECTED_ONLY input={len(document)} selected={len(selected)} "
        f"omitted={len(document) - len(selected)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
