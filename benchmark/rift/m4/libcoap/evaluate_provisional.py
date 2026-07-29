#!/usr/bin/env python3
"""Project provisional libcoap labels onto a certified RIFT cone bundle.

This is a development diagnostic, not a real-project gold evaluator. It keeps
the two-human/arbitration boundary in the output and deliberately emits no
precision, recall, F1, or headline acceptance decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter


HERE = pathlib.Path(__file__).resolve().parent
LOCATOR = re.compile(r"^(?P<path>.+):(?P<start>[0-9]+)-(?P<end>[0-9]+)$")
ARTIFACTS = {
    "semantic_index": "semantic_index.json",
    "ap_bindings": "ap_bindings.json",
    "contextual_influence_graph": "contextual_influence_graph.json",
    "ap_influence_cones": "ap_influence_cones.json",
}


def load_json(path: pathlib.Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def target_aps(target: str, all_aps: set[str]) -> set[str]:
    if target == "scheduled_initial_delay":
        return {"coap_first_retransmit_deadline_reached"}
    if target == "all_atomic_propositions":
        return set(all_aps)
    return {target}


def location_matches(
    location: dict[str, object], path: str, start: int, end: int
) -> bool:
    logical_file = location.get("file")
    line = location.get("line")
    end_line = location.get("end_line", line)
    return (
        isinstance(logical_file, str)
        and (logical_file == path or logical_file.endswith("/" + path))
        and isinstance(line, int)
        and isinstance(end_line, int)
        and line <= end
        and end_line >= start
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    analysis_dir = args.analysis_dir.resolve()
    output = args.output.resolve()
    if output.exists():
        print(f"FAIL output already exists: {output}", file=sys.stderr)
        return 1

    required = [analysis_dir / name for name in ARTIFACTS.values()]
    required.append(analysis_dir / "analysis_certificate.json")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("FAIL missing artifacts: " + ", ".join(missing), file=sys.stderr)
        return 1

    labels = load_json(HERE / "provisional_influence_labels.json")
    certificate = load_json(analysis_dir / "analysis_certificate.json")
    graph = load_json(analysis_dir / ARTIFACTS["contextual_influence_graph"])
    cones = load_json(analysis_dir / ARTIFACTS["ap_influence_cones"])
    if not all(
        isinstance(value, dict) for value in (labels, certificate, graph, cones)
    ):
        print("FAIL malformed JSON root", file=sys.stderr)
        return 1

    review = labels.get("review_contract", {})
    if (
        labels.get("status") != "PROVISIONAL_EXPERT_DRAFT_NOT_GOLD"
        or review.get("completed_independent_human_reviewers") != 0
        or review.get("arbitration_status") != "PENDING"
        or review.get("headline_metric_allowed") is not False
    ):
        print("FAIL provisional review boundary changed", file=sys.stderr)
        return 1

    certified_outputs = {
        item.get("kind"): item.get("sha256")
        for item in certificate.get("outputs", [])
        if isinstance(item, dict)
    }
    artifact_sha256: dict[str, str] = {}
    for kind, filename in ARTIFACTS.items():
        observed = digest(analysis_dir / filename)
        artifact_sha256[kind] = observed
        if certified_outputs.get(kind) != observed:
            print(f"FAIL certificate digest mismatch: {kind}", file=sys.stderr)
            return 1

    graph_nodes = graph.get("nodes", [])
    graph_by_id = {
        node["node_id"]: node
        for node in graph_nodes
        if isinstance(node, dict) and isinstance(node.get("node_id"), str)
    }
    cone_by_ap = {
        cone["ap_id"]: cone
        for cone in cones.get("cones", [])
        if isinstance(cone, dict) and isinstance(cone.get("ap_id"), str)
    }
    all_aps = set(cone_by_ap)
    cone_members: dict[str, dict[str, str]] = {}
    for ap_id, cone in cone_by_ap.items():
        cone_members[ap_id] = {
            member["node_id"]: member["membership"]
            for member in cone.get("members", [])
            if isinstance(member, dict)
            and isinstance(member.get("node_id"), str)
            and isinstance(member.get("membership"), str)
        }

    label_groups = (
        "must_influencers",
        "may_influencers",
        "scope_only_influencers",
        "model_required_relationships",
        "candidate_negative_controls",
    )
    results: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    for group in label_groups:
        for label in labels.get(group, []):
            targets = target_aps(label["target"], all_aps)
            unknown_targets = sorted(targets - all_aps)
            locators: list[tuple[str, int, int]] = []
            invalid_locators: list[str] = []
            for evidence in label.get("evidence", []):
                match = LOCATOR.fullmatch(evidence)
                if match is None:
                    invalid_locators.append(evidence)
                    continue
                locators.append(
                    (
                        match.group("path"),
                        int(match.group("start")),
                        int(match.group("end")),
                    )
                )

            indexed_nodes: set[str] = set()
            for node_id, node in graph_by_id.items():
                location = node.get("location")
                if not isinstance(location, dict):
                    continue
                if any(
                    location_matches(location, *locator) for locator in locators
                ):
                    indexed_nodes.add(node_id)

            recovered: list[dict[str, object]] = []
            for ap_id in sorted(targets & all_aps):
                for node_id in sorted(indexed_nodes & set(cone_members[ap_id])):
                    node = graph_by_id[node_id]
                    recovered.append(
                        {
                            "ap_id": ap_id,
                            "node_id": node_id,
                            "membership": cone_members[ap_id][node_id],
                            "file": node["location"]["file"],
                            "line": node["location"]["line"],
                        }
                    )

            memberships = Counter(item["membership"] for item in recovered)
            if recovered and set(memberships) == {"UNKNOWN_INFLUENCE"}:
                status = "RECOVERED_UNKNOWN_ONLY"
            elif recovered:
                status = "RECOVERED_KNOWN_PATH"
            elif unknown_targets:
                status = "TARGET_NOT_IN_ANALYZED_PROPERTY"
            elif not indexed_nodes:
                status = "EVIDENCE_LOCATION_NOT_INDEXED"
            elif label.get("classification") == "MODEL_REQUIRED":
                status = "NOT_RECOVERED_MODEL_REQUIRED"
            else:
                status = "NOT_RECOVERED_FROM_CURRENT_CONES"
            status_counts[status] += 1
            results.append(
                {
                    "id": label["id"],
                    "group": group,
                    "classification": label["classification"],
                    "target": label["target"],
                    "mapped_ap_ids": sorted(targets),
                    "status": status,
                    "invalid_evidence_locators": invalid_locators,
                    "indexed_location_node_count": len(indexed_nodes),
                    "recovered_membership_counts": dict(sorted(memberships.items())),
                    "recovered_examples": recovered[:20],
                }
            )

    report = {
        "schema_version": "rift.m4.libcoap-provisional-evaluation/1.0.0",
        "status": "DEVELOPMENT_DIAGNOSTIC_NOT_GOLD",
        "property_id": labels["property_id"],
        "review_contract": review,
        "metric_policy": {
            "precision_recall_f1_emitted": False,
            "headline_acceptance_decision_emitted": False,
            "reason": (
                "real-project labels require two independent humans and arbitration"
            ),
        },
        "analysis": {
            "analysis_id": certificate.get("analysis_id"),
            "certificate_id": certificate.get("certificate_id"),
            "artifact_sha256": artifact_sha256,
        },
        "projection_semantics": (
            "A label is recovered when at least one graph node overlapping one of its "
            "provisional source ranges is a member of a mapped AP cone. This is a "
            "source-range diagnostic, not an adjudicated entity-level correctness claim."
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "labels": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "PASS status=DEVELOPMENT_DIAGNOSTIC_NOT_GOLD "
        f"labels={len(results)} counts={dict(sorted(status_counts.items()))} "
        f"output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
