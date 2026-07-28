#!/usr/bin/env python3
"""Build the auditable ArduPilot/PX4 document corpus and high-recall candidates.

This script does not accept properties and does not infer conformance.  It records
versioned document/source blocks, keyword prefilter hits, and a per-file coverage
ledger.  Subsequent review must recover context and construct Requirement IR.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence


KEYWORDS = {
    "normative": [
        r"\bmust\b", r"\bmust not\b", r"\bshall\b", r"\brequired\b",
        r"\bshould\b", r"\brecommended\b", r"\bonly\b", r"\bnever\b",
        r"\bcannot\b", r"\bwill not\b", r"\bneeds? to\b",
    ],
    "temporal": [
        r"\bwithin\b", r"\bno later than\b", r"\bat least\b", r"\bat most\b",
        r"\bafter\b", r"\bbefore\b", r"\buntil\b", r"\bonce\b",
        r"\bimmediately\b", r"\btimeout\b", r"\btime[- ]?out\b", r"\bdelay\b",
        r"\bhold\b", r"\bdebounce\b", r"\bdwell\b", r"\bretry\b",
        r"\bheartbeat\b", r"\blost for\b", r"\belapsed\b", r"\bdeadline\b",
        r"\bgrace period\b", r"\bmilliseconds?\b", r"\bseconds?\b",
        r"\bminutes?\b", r"\bhz\b", r"\bms\b", r"\bcycles?\b",
    ],
    "state": [
        r"\barmed\b", r"\bdisarmed\b", r"\blanded\b", r"\bin air\b",
        r"\bmode\b", r"\bfailsafe\b", r"\bfail-safe\b", r"\bhealthy\b",
        r"\bvalid\b", r"\blink lost\b", r"\bgps\b", r"\bbattery\b",
        r"\bmission\b", r"\bwaypoint\b", r"\brecover\b", r"\breset\b",
        r"\btakeoff\b", r"\bland\b", r"\brtl\b", r"\boffboard\b",
        r"\bposition\b", r"\baltitude\b", r"\bvehicle\b",
    ],
    "condition": [
        r"\bif\b", r"\bwhen\b", r"\bunless\b", r"\bexcept\b",
        r"\bprovided\b", r"\botherwise\b", r"\bthen\b", r"\bonly when\b",
        r"\bwhile\b", r"\bas long as\b",
    ],
}
COMPILED_KEYWORDS = {
    name: [(pattern, re.compile(pattern, re.IGNORECASE)) for pattern in patterns]
    for name, patterns in KEYWORDS.items()
}
PARAM_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,15}(?:_[A-Z0-9]{1,16})+\b")
RST_ANCHOR_RE = re.compile(r"^\.\.\s+_([^:]+):\s*$")
MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
RST_HEADING_CHARS = set("=-~^\"'`:+*#<>_")
SOURCE_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}


@dataclass(frozen=True)
class Block:
    node_type: str
    section_path: tuple[str, ...]
    anchor: str | None
    line_start: int
    line_end: int
    text: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def safe_text(path: Path) -> tuple[str, bytes]:
    raw = path.read_bytes()
    return raw.decode("utf-8", errors="replace"), raw


def keyword_hits(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for category, patterns in COMPILED_KEYWORDS.items():
        hits = [raw for raw, regex in patterns if regex.search(text)]
        result[category] = hits
    result["parameter"] = sorted(set(PARAM_ID_RE.findall(text)))
    return result


def hit_counts(hits: dict[str, list[str]]) -> dict[str, int]:
    return {key: len(value) for key, value in hits.items()}


def candidate_score(hits: dict[str, list[str]], source_class: str) -> int:
    counts = hit_counts(hits)
    score = (
        4 * counts["normative"]
        + 5 * counts["temporal"]
        + 2 * counts["state"]
        + 2 * counts["condition"]
        + min(4, counts["parameter"])
    )
    if source_class == "OFFICIAL_BEHAVIOR":
        score += 3
    elif source_class == "PARAM_METADATA":
        score += 1
    return score


def is_prefilter_candidate(hits: dict[str, list[str]], source_class: str) -> bool:
    counts = hit_counts(hits)
    if source_class in {"PARAM_METADATA", "SOURCE_COMMENT"}:
        return counts["temporal"] > 0 or counts["normative"] > 0
    return (
        counts["temporal"] > 0
        or counts["normative"] > 0
        or (counts["state"] > 0 and counts["condition"] > 0)
    )


def clean_rst_text(lines: Sequence[str]) -> str:
    text = "\n".join(lines).strip()
    return re.sub(r"\s+", " ", text)


def parse_markup(path: Path) -> list[Block]:
    text, _ = safe_text(path)
    lines = text.splitlines()
    is_rst = path.suffix.lower() == ".rst"
    sections: list[str] = []
    anchor: str | None = None
    blocks: list[Block] = []
    buffer: list[str] = []
    start_line = 1

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line
        cleaned = clean_rst_text(buffer)
        if cleaned:
            stripped = cleaned.lstrip()
            node_type = "list_item" if re.match(r"^(?:[-*+] |\d+[.)] )", stripped) else "paragraph"
            blocks.append(Block(node_type, tuple(sections), anchor, start_line, end_line, cleaned))
        buffer = []

    i = 0
    while i < len(lines):
        line = lines[i]
        line_no = i + 1
        if is_rst:
            match_anchor = RST_ANCHOR_RE.match(line.strip())
            if match_anchor:
                flush(line_no - 1)
                anchor = match_anchor.group(1)
                i += 1
                start_line = i + 1
                continue
            if i + 1 < len(lines):
                underline = lines[i + 1].strip()
                title = line.strip()
                if title and underline and len(underline) >= len(title) and set(underline) <= RST_HEADING_CHARS and len(set(underline)) == 1:
                    flush(line_no - 1)
                    ch = underline[0]
                    level_order = {"=": 1, "-": 2, "~": 3, "^": 4, '"': 5, "'": 5}
                    level = level_order.get(ch, min(6, len(sections) + 1))
                    sections[:] = sections[: level - 1]
                    sections.append(title)
                    blocks.append(Block("section", tuple(sections), anchor, line_no, line_no + 1, title))
                    i += 2
                    start_line = i + 1
                    continue
        else:
            match_heading = MD_HEADING_RE.match(line)
            if match_heading:
                flush(line_no - 1)
                level = len(match_heading.group(1))
                title = match_heading.group(2).strip()
                sections[:] = sections[: level - 1]
                sections.append(title)
                blocks.append(Block("section", tuple(sections), anchor, line_no, line_no, title))
                anchor = re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")
                i += 1
                start_line = i + 1
                continue
        if not line.strip():
            flush(line_no - 1)
            start_line = line_no + 1
        else:
            if not buffer:
                start_line = line_no
            buffer.append(line)
        i += 1
    flush(len(lines))
    return blocks


def comment_blocks(path: Path, system: str) -> list[Block]:
    text, _ = safe_text(path)
    lines = text.splitlines()
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        if stripped.startswith("//"):
            start = i
            chunk: list[str] = []
            while i < len(lines) and lines[i].lstrip().startswith("//"):
                chunk.append(re.sub(r"^\s*//[/!]?\s?", "", lines[i]))
                i += 1
            cleaned = clean_rst_text(chunk)
            if cleaned:
                node_type = "parameter_record" if "@Param" in cleaned else "source_comment"
                blocks.append(Block(node_type, tuple(), None, start + 1, i, cleaned))
            continue
        if stripped.startswith("/*"):
            start = i
            chunk = []
            while i < len(lines):
                chunk.append(lines[i])
                if "*/" in lines[i]:
                    i += 1
                    break
                i += 1
            cleaned = clean_rst_text([
                re.sub(r"^\s*(?:/\*+|\*+/?|//!?)\s?", "", x) for x in chunk
            ])
            if cleaned:
                following = lines[i] if i < len(lines) else ""
                node_type = "parameter_record" if (
                    "@Param" in cleaned or (system == "PX4" and "PARAM_DEFINE_" in following)
                ) else "source_comment"
                if node_type == "parameter_record" and following.strip():
                    cleaned = f"{cleaned} {following.strip()}"
                blocks.append(Block(node_type, tuple(), None, start + 1, max(start + 1, i), cleaned))
            continue
        i += 1
    return blocks


def yaml_parameter_blocks(path: Path) -> list[Block]:
    text, _ = safe_text(path)
    lines = text.splitlines()
    blocks: list[Block] = []
    start = 0
    chunk: list[str] = []
    for i, line in enumerate(lines):
        if not line.strip() and chunk:
            cleaned = clean_rst_text(chunk)
            if re.search(r"(?i)(parameter|short_desc|long_desc|default|unit|timeout|delay)", cleaned):
                blocks.append(Block("parameter_record", tuple(), None, start + 1, i, cleaned))
            chunk = []
        else:
            if not chunk:
                start = i
            chunk.append(line)
    if chunk:
        cleaned = clean_rst_text(chunk)
        if re.search(r"(?i)(parameter|short_desc|long_desc|default|unit|timeout|delay)", cleaned):
            blocks.append(Block("parameter_record", tuple(), None, start + 1, len(lines), cleaned))
    return blocks


def iter_files(roots: Sequence[Path], suffixes: set[str]) -> Iterator[Path]:
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if any(part in {".git", "build", "__pycache__"} for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield resolved


def make_node_id(system: str, path: Path, line_start: int, text: str) -> str:
    digest = sha256_text(f"{system}\0{path}\0{line_start}\0{text}")[:16]
    return f"{system.lower()}-node-{digest}"


def make_candidate_id(system: str, node_id: str) -> str:
    return f"{system.lower()}-candidate-{sha256_text(node_id)[:16]}"


def source_url(system: str, path: Path, workspace: Path, commits: dict[str, str]) -> str:
    if system == "ArduPilot" and "ardupilot_wiki" in path.parts:
        repo = workspace / "benchmark/extraction_runs/corpus_sources/ardupilot_wiki"
        rel = path.relative_to(repo)
        return f"https://github.com/ArduPilot/ardupilot_wiki/blob/{commits['ardupilot_wiki']}/{rel.as_posix()}"
    if system == "ArduPilot":
        repo = workspace / "baseline/ardupilot"
        rel = path.relative_to(repo)
        return f"https://github.com/ArduPilot/ardupilot/blob/{commits['ArduPilot']}/{rel.as_posix()}"
    repo = workspace / "baseline/px4"
    rel = path.relative_to(repo)
    return f"https://github.com/PX4/PX4-Autopilot/blob/{commits['PX4']}/{rel.as_posix()}"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def process_system(
    system: str,
    workspace: Path,
    output_root: Path,
    doc_files: Sequence[Path],
    source_files: Sequence[Path],
    yaml_files: Sequence[Path],
    commits: dict[str, str],
    generated_at: str,
) -> dict[str, object]:
    system_dir = workspace / "benchmark" / system
    run_dir = output_root / system
    run_dir.mkdir(parents=True, exist_ok=True)
    system_dir.mkdir(parents=True, exist_ok=True)

    graph_path = run_dir / "docgraph.jsonl"
    candidate_path = run_dir / "prefilter_candidates.jsonl"
    coverage_rows: list[dict[str, object]] = []
    aggregate = Counter()
    document_records: list[dict[str, object]] = []

    with graph_path.open("w", encoding="utf-8") as graph, candidate_path.open("w", encoding="utf-8") as candidates:
        for path, source_class, parser in [
            *[(p, "OFFICIAL_BEHAVIOR", parse_markup) for p in doc_files],
            *[(p, "SOURCE_COMMENT", lambda q, s=system: comment_blocks(q, s)) for p in source_files],
            *[(p, "PARAM_METADATA", yaml_parameter_blocks) for p in yaml_files],
        ]:
            text, raw = safe_text(path)
            file_hash = sha256_bytes(raw)
            blocks = parser(path)
            file_counts = Counter()
            candidate_count = 0
            previous_node: str | None = None
            root_id = make_node_id(system, path, 1, str(path))
            document_id = f"{system.lower()}-doc-{file_hash[:16]}"
            root_record = {
                "record_type": "node",
                "node_id": root_id,
                "system": system,
                "source_class": source_class,
                "document_id": document_id,
                "path": str(path),
                "file_sha256": file_hash,
                "node_type": "document",
                "section_path": [],
                "anchor": None,
                "line_start": 1,
                "line_end": max(1, len(text.splitlines())),
                "text": path.name,
                "text_sha256": sha256_text(path.name),
            }
            graph.write(json.dumps(root_record, ensure_ascii=False) + "\n")
            for block in blocks:
                if block.node_type == "section" or len(block.text) < 8:
                    include_candidate = False
                else:
                    include_candidate = True
                actual_class = source_class
                if block.node_type == "parameter_record":
                    actual_class = "PARAM_METADATA"
                node_id = make_node_id(system, path, block.line_start, block.text)
                node = {
                    "record_type": "node",
                    "node_id": node_id,
                    "system": system,
                    "source_class": actual_class,
                    "document_id": document_id,
                    "path": str(path),
                    "file_sha256": file_hash,
                    "node_type": block.node_type,
                    "section_path": list(block.section_path),
                    "anchor": block.anchor,
                    "line_start": block.line_start,
                    "line_end": block.line_end,
                    "text": block.text,
                    "text_sha256": sha256_text(block.text),
                }
                graph.write(json.dumps(node, ensure_ascii=False) + "\n")
                parent_edge = {
                    "record_type": "edge",
                    "edge_id": f"edge-{sha256_text(root_id + node_id + 'parent')[:16]}",
                    "system": system,
                    "from": root_id,
                    "relation": "parent_of",
                    "to": node_id,
                    "confidence": "EXACT",
                    "evidence": "file containment",
                }
                graph.write(json.dumps(parent_edge, ensure_ascii=False) + "\n")
                if previous_node:
                    next_edge = {
                        "record_type": "edge",
                        "edge_id": f"edge-{sha256_text(previous_node + node_id + 'next')[:16]}",
                        "system": system,
                        "from": previous_node,
                        "relation": "next",
                        "to": node_id,
                        "confidence": "EXACT",
                        "evidence": "document order",
                    }
                    graph.write(json.dumps(next_edge, ensure_ascii=False) + "\n")
                previous_node = node_id

                hits = keyword_hits(block.text)
                counts = hit_counts(hits)
                for key, count in counts.items():
                    file_counts[key] += count
                if include_candidate and is_prefilter_candidate(hits, actual_class):
                    candidate_count += 1
                    record = {
                        "candidate_id": make_candidate_id(system, node_id),
                        "system": system,
                        "source_class": actual_class,
                        "authority": "MEDIUM" if actual_class == "OFFICIAL_BEHAVIOR" else "LOW",
                        "document_id": document_id,
                        "node_id": node_id,
                        "path": str(path),
                        "url": source_url(system, path, workspace, commits),
                        "commit": commits["ardupilot_wiki"] if "ardupilot_wiki" in path.parts else commits[system],
                        "file_sha256": file_hash,
                        "section_path": list(block.section_path),
                        "anchor": block.anchor,
                        "line_start": block.line_start,
                        "line_end": block.line_end,
                        "exact_text": block.text,
                        "text_sha256": sha256_text(block.text),
                        "keyword_hits": hits,
                        "prefilter_score": candidate_score(hits, actual_class),
                        "scan_decision": "PREFILTER_HIT",
                        "review_status": "PENDING_CONTEXT_REVIEW",
                        "implementation_satisfaction": "NOT_ASSESSED",
                    }
                    candidates.write(json.dumps(record, ensure_ascii=False) + "\n")
            coverage = {
                "system": system,
                "source_class": source_class,
                "path": str(path),
                "source_url": source_url(system, path, workspace, commits),
                "commit": commits["ardupilot_wiki"] if "ardupilot_wiki" in path.parts else commits[system],
                "file_sha256": file_hash,
                "bytes": len(raw),
                "lines": len(text.splitlines()),
                "nodes": len(blocks),
                "candidate_count": candidate_count,
                "normative_hits": file_counts["normative"],
                "temporal_hits": file_counts["temporal"],
                "state_hits": file_counts["state"],
                "condition_hits": file_counts["condition"],
                "parameter_hits": file_counts["parameter"],
                "scan_status": "SCREENED_BY_DETERMINISTIC_PREFILTER",
                "human_review_status": "PENDING" if candidate_count else "NOT_REQUIRED_NO_PREFILTER_HIT",
                "excluded_reason": "" if candidate_count else "NO_PREFILTER_HIT",
            }
            coverage_rows.append(coverage)
            aggregate.update({
                "files": 1,
                "bytes": len(raw),
                "nodes": len(blocks) + 1,
                "candidates": candidate_count,
                "normative_hits": file_counts["normative"],
                "temporal_hits": file_counts["temporal"],
                "state_hits": file_counts["state"],
                "condition_hits": file_counts["condition"],
                "parameter_hits": file_counts["parameter"],
            })
            document_records.append({
                "document_id": document_id,
                "source_class": source_class,
                "path": str(path),
                "url": coverage["source_url"],
                "commit": coverage["commit"],
                "sha256": file_hash,
                "bytes": len(raw),
                "lines": len(text.splitlines()),
                "scan_status": coverage["scan_status"],
            })

    coverage_path = system_dir / "coverage_ledger.csv"
    fieldnames = list(coverage_rows[0]) if coverage_rows else []
    with coverage_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(coverage_rows)

    manifest = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "system": system,
        "firmware_commit": commits[system],
        "document_status_policy": {
            "official_behavior_docs": "MAIN_ONLY" if system == "ArduPilot" else "RELEASE_PINNED",
            "source_comments_and_parameter_metadata": "FIRMWARE_COMMIT_PINNED",
            "control_flow_may_originate_property": False,
            "implementation_satisfaction": "NOT_ASSESSED",
        },
        "sources": document_records,
        "aggregate": dict(sorted(aggregate.items())),
        "artifacts": {
            "docgraph_jsonl": str(graph_path),
            "prefilter_candidates_jsonl": str(candidate_path),
            "coverage_ledger_csv": str(coverage_path),
        },
        "screening_method": {
            "version": "build_corpus.py/1.0",
            "keyword_categories": KEYWORDS,
            "parameter_id_regex": PARAM_ID_RE.pattern,
            "notes": [
                "Keyword hits are recall-oriented candidates, never accepted properties.",
                "Source comments and parameter metadata have low authority and require independent review.",
                "Ordinary executable control flow is not parsed as a property source.",
                "Human review status is tracked separately from deterministic screening status.",
            ],
        },
    }
    manifest_path = system_dir / "source_and_corpus_manifest.json"
    write_json(manifest_path, manifest)
    write_json(run_dir / "run_summary.json", {
        "system": system,
        "generated_at": generated_at,
        "aggregate": manifest["aggregate"],
        "manifest": str(manifest_path),
        "coverage": str(coverage_path),
        "docgraph": str(graph_path),
        "candidates": str(candidate_path),
    })
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    output = (args.output or workspace / "benchmark/extraction_runs/milestone3").resolve()
    output.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    ardupilot = workspace / "baseline/ardupilot"
    px4 = workspace / "baseline/px4"
    ardupilot_wiki = workspace / "benchmark/extraction_runs/corpus_sources/ardupilot_wiki"
    commits = {
        "ArduPilot": git_output(ardupilot, "rev-parse", "HEAD"),
        "PX4": git_output(px4, "rev-parse", "HEAD"),
        "ardupilot_wiki": git_output(ardupilot_wiki, "rev-parse", "HEAD"),
    }

    ardu_doc_roots = [ardupilot_wiki / name / "source/docs" for name in ("common", "copter", "plane", "rover")]
    ardu_docs = list(iter_files(ardu_doc_roots, {".rst"}))
    px4_docs = list(iter_files([px4 / "docs/en"], {".md", ".rst"}))

    ardu_source_roots = [
        ardupilot / "ArduCopter", ardupilot / "ArduPlane", ardupilot / "Rover", ardupilot / "libraries"
    ]
    px4_source_roots = [px4 / "src", px4 / "platforms", px4 / "boards"]
    ardu_sources = list(iter_files(ardu_source_roots, SOURCE_EXTENSIONS))
    px4_sources = list(iter_files(px4_source_roots, SOURCE_EXTENSIONS))
    px4_yaml = [
        path for path in iter_files([px4 / "src", px4 / "ROMFS"], {".yaml", ".yml"})
        if any(token in path.name.lower() for token in ("param", "module")) or "module.yaml" in path.name.lower()
    ]

    ardu_manifest = process_system(
        "ArduPilot", workspace, output, ardu_docs, ardu_sources, [], commits, generated_at
    )
    px4_manifest = process_system(
        "PX4", workspace, output, px4_docs, px4_sources, px4_yaml, commits, generated_at
    )
    combined = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "commits": commits,
        "systems": {
            "ArduPilot": ardu_manifest["aggregate"],
            "PX4": px4_manifest["aggregate"],
        },
    }
    write_json(output / "combined_summary.json", combined)
    print(json.dumps(combined, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
