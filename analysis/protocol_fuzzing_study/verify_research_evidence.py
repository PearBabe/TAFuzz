#!/usr/bin/env python3
"""Probe every URL recorded by the multi-protocol evidence ledgers.

This is a reachability audit, not a claim that mutable web content is itself
version-pinned.  Source truth for admitted properties is separately checked by
raw GitHub commit/path retrieval in generate_multi_protocol_catalog.py.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
STAGING = BASE / "_staging"
OUT = BASE / "protocols"
ACCESS_DATE = "2026-07-13"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def collect_urls() -> dict[str, list[dict[str, str]]]:
    occurrences: dict[str, list[dict[str, str]]] = defaultdict(list)
    # Audit proposal-level standard/source/auxiliary URLs as well as evidence
    # ledgers and the generated admitted catalog.  Scanning only evidence.json
    # would leave most property claims outside the reachability audit.
    paths = sorted(STAGING.rglob("*.json"))
    for candidate in (
        BASE / "mitl_property_catalog.json",
        BASE / "evidence_manifest.json",
        BASE / "evidence_manifest.yaml",
        OUT / "all_protocol_properties.json",
        OUT / "evidence_manifest.json",
    ):
        if candidate.exists():
            paths.append(candidate)
    paths.extend(sorted(OUT.glob("*/evidence_manifest.json")) if OUT.exists() else [])
    # Keep deterministic first occurrence while avoiding duplicate reads.
    paths = list(dict.fromkeys(paths))
    for path in paths:
        doc = load(path)

        def walk(value: Any, key: str = "", pointer: str = "$") -> None:
            if isinstance(value, dict):
                for child_key, child in value.items():
                    walk(child, str(child_key), f"{pointer}.{child_key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, key, f"{pointer}[{index}]")
            elif isinstance(value, str) and value.startswith(("http://", "https://")):
                occurrences[value].append({
                    "file": str(path.relative_to(BASE)), "json_pointer": pointer, "field": key,
                })

        walk(doc)
    return occurrences


def probe(url: str) -> dict[str, Any]:
    notes: list[str] = []
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "TAFuzz-evidence-audit/1.0", "Range": "bytes=0-2047"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read(2048)
                return {"reachable": 200 <= response.status < 400,
                        "verification": "TLS_VERIFIED", "detail": f"HTTP {response.status}"}
        except Exception as exc:  # noqa: BLE001
            notes.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
            time.sleep(0.2 * (attempt + 1))

    curl = subprocess.run(
        ["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "45",
         "--range", "0-2047", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    if curl.returncode == 0:
        return {"reachable": True, "verification": "TLS_VERIFIED_CURL",
                "detail": "curl range request succeeded"}

    combined = " | ".join(notes + [curl.stderr.strip()])
    if any(token in combined.lower() for token in ("certificate", "ssl", "tls")):
        insecure = subprocess.run(
            ["curl", "-k", "-L", "--fail", "--silent", "--show-error", "--max-time", "45",
             "--range", "0-2047", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        if insecure.returncode == 0:
            return {"reachable": True, "verification": "REACHABLE_TLS_UNVERIFIED",
                    "detail": "reachable only with curl -k; local CA-chain validation failed"}
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() in {"doi.org", "dx.doi.org"} and parsed.path.strip("/"):
        doi = urllib.parse.unquote(parsed.path.strip("/"))
        registry_url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
        registry = subprocess.run(
            ["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "30",
             "--range", "0-4095", registry_url],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        if registry.returncode == 0:
            return {
                "reachable": True,
                "verification": "DOI_REGISTERED_RESOLVER_BLOCKED",
                "detail": f"doi.org automated request was blocked; Crossref registry confirmed {doi}",
            }
    return {"reachable": False, "verification": "FAILED", "detail": combined}


def main() -> int:
    occurrences = collect_urls()
    targets = {url: urllib.parse.urldefrag(url).url for url in occurrences}
    unique_targets = sorted(set(targets.values()))
    target_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(probe, url): url for url in unique_targets}
        for future in as_completed(futures):
            url = futures[future]
            try:
                target_results[url] = future.result()
            except Exception as exc:  # noqa: BLE001
                target_results[url] = {
                    "reachable": False, "verification": "AUDITOR_EXCEPTION",
                    "detail": f"{type(exc).__name__}: {exc}",
                }

    rows = []
    for url in sorted(occurrences):
        target = targets[url]
        result = target_results[target]
        rows.append({
            "url": url, "reachable": result["reachable"],
            "verification": result["verification"], "detail": result["detail"],
            "probe_target": target,
            "occurrence_count": len(occurrences[url]),
            "occurrences": occurrences[url],
        })
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "access_date": ACCESS_DATE,
        "unique_url_count": len(rows),
        "unique_probe_target_count": len(unique_targets),
        "reachable_count": sum(row["reachable"] is True for row in rows),
        "tls_verified_count": sum(str(row["verification"]).startswith("TLS_VERIFIED") for row in rows),
        "tls_unverified_reachable_count": sum(row["verification"] == "REACHABLE_TLS_UNVERIFIED" for row in rows),
        "failed_count": sum(row["reachable"] is not True for row in rows),
        "rows": rows,
    }
    (OUT / "evidence_link_audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (OUT / "evidence_link_audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "url", "probe_target", "reachable", "verification", "detail", "occurrence_count", "occurrences",
        ])
        writer.writeheader()
        for row in rows:
            cooked = dict(row)
            cooked["occurrences"] = json.dumps(row["occurrences"], ensure_ascii=False)
            writer.writerow(cooked)
    manifest_path = OUT / "reproducibility_manifest.json"
    if manifest_path.exists():
        manifest = load(manifest_path)
        audit_names = {"evidence_link_audit.json", "evidence_link_audit.csv"}
        artifacts = [item for item in manifest.get("artifacts", []) if item.get("path") not in audit_names]
        for name in sorted(audit_names):
            path = OUT / name
            artifacts.append({
                "path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            })
        manifest["artifacts"] = sorted(artifacts, key=lambda item: str(item.get("path", "")))
        manifest["evidence_link_audit"] = {
            key: value for key, value in summary.items() if key != "rows"
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, ensure_ascii=False))
    return 0 if summary["failed_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
