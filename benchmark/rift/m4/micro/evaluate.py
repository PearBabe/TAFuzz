#!/usr/bin/env python3
"""Trusted post-analysis evaluator for RIFT-M4 production artifacts.

The public bundle and sealed run are fully validated before this module opens
the synthetic corpus manifest or any private truth file.  UNKNOWN remains an
abstention and is never credited as a negative prediction.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from command_adapter import DEFAULT_ADAPTER
from common import (
    AcceptanceError,
    DEFAULT_CORPUS,
    LOCAL_SCHEMA_DIR,
    discover_source_records,
    location_matches,
    read_json,
    sanitize_source,
    sha256_bytes,
    sha256_file,
    unique_by,
    validate_schema,
    write_json,
)
from common import strip_ap_markers
from validate_acceptance import RUN_MANIFEST, validate_run


GOLD_LABEL = {
    "MUST_INFLUENCE": "MUST",
    "MAY_INFLUENCE": "MAY",
    "NO_INFLUENCE": "NO",
}
PREDICTION_LABELS = ("MUST", "MAY", "NO", "UNKNOWN")
CLASS_LABELS = ("MUST", "MAY", "NO")
POSITIVE = {"MUST", "MAY"}


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def prf(tp: int, fp: int, fn: int, **extra: Any) -> dict[str, Any]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": safe_ratio(tp, tp + fp),
        "recall": safe_ratio(tp, tp + fn),
        "f1": safe_ratio(2 * tp, 2 * tp + fp + fn),
        **extra,
    }


def class_metrics(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    tp = sum(row["gold"] == label and row["prediction"] == label for row in rows)
    fp = sum(row["gold"] != label and row["prediction"] == label for row in rows)
    fn = sum(row["gold"] == label and row["prediction"] != label for row in rows)
    return prf(tp, fp, fn, support=sum(row["gold"] == label for row in rows))


def influence_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(row["gold"] in POSITIVE and row["prediction"] in POSITIVE for row in rows)
    fp = sum(row["gold"] == "NO" and row["prediction"] in POSITIVE for row in rows)
    fn = sum(row["gold"] in POSITIVE and row["prediction"] not in POSITIVE for row in rows)
    tn = sum(row["gold"] == "NO" and row["prediction"] == "NO" for row in rows)
    unknown_negative = sum(
        row["gold"] == "NO" and row["prediction"] == "UNKNOWN" for row in rows
    )
    return prf(
        tp,
        fp,
        fn,
        tn=tn,
        unknown_on_negative=unknown_negative,
        total=len(rows),
        accuracy_unknown_is_wrong=safe_ratio(tp + tn, len(rows)),
    )


def must_detection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold = [row for row in rows if row["gold"] == "MUST"]
    detected = sum(row["prediction"] in POSITIVE for row in gold)
    return {
        "gold_must": len(gold),
        "detected_in_cone": detected,
        "detection_recall": safe_ratio(detected, len(gold)),
        "exact_must": sum(row["prediction"] == "MUST" for row in gold),
        "downgraded_to_may": sum(row["prediction"] == "MAY" for row in gold),
        "absent_as_no": sum(row["prediction"] == "NO" for row in gold),
        "unknown_or_unsupported": sum(row["prediction"] == "UNKNOWN" for row in gold),
    }


def classification(rows: list[dict[str, Any]]) -> dict[str, Any]:
    confusion = {
        gold: {prediction: 0 for prediction in PREDICTION_LABELS}
        for gold in CLASS_LABELS
    }
    for row in rows:
        confusion[row["gold"]][row["prediction"]] += 1
    exact = sum(confusion[label][label] for label in CLASS_LABELS)
    return {
        "total": len(rows),
        "exact": exact,
        "exact_accuracy_unknown_is_wrong": safe_ratio(exact, len(rows)),
        "unknown": sum(confusion[label]["UNKNOWN"] for label in CLASS_LABELS),
        "confusion_matrix_gold_rows": confusion,
    }


def binding_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(row["correct"] for row in rows)
    predicted = sum(row["predicted"] for row in rows)
    fp = predicted - tp
    fn = len(rows) - tp
    return prf(
        tp,
        fp,
        fn,
        gold=len(rows),
        predicted=predicted,
        unresolved=sum(not row["predicted"] for row in rows),
    )


def metric_block(
    relation_rows: list[dict[str, Any]], binding_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "pairs": len(relation_rows),
        "influence": influence_metrics(relation_rows),
        "must_exact": class_metrics(relation_rows, "MUST"),
        "may_exact": class_metrics(relation_rows, "MAY"),
        "must_detection": must_detection(relation_rows),
        "classification": classification(relation_rows),
        "binding_top1": binding_metrics(binding_rows),
    }


def _validate_private_schema(instance: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    try:
        jsonschema.Draft7Validator(schema).validate(instance)
    except jsonschema.ValidationError as error:
        location = "/".join(str(item) for item in error.absolute_path)
        raise AcceptanceError(
            f"{label} schema error at {location or '<root>'}: {error.message}"
        ) from error


def load_private_truth(
    corpus_root: Path,
    bundle: Path,
    input_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """Private join, called only after validate_run has returned successfully."""
    corpus_root = corpus_root.resolve()
    records = discover_source_records(corpus_root)
    private_manifest_path = corpus_root / "manifest.json"
    if (
        sha256_file(private_manifest_path)
        != input_manifest["private_oracle_commitment_sha256"]
    ):
        raise AcceptanceError("private oracle manifest differs from frozen commitment")
    private_manifest = read_json(private_manifest_path)
    truth_schema = corpus_root / "ground_truth.schema.json"
    entries_by_hash = unique_by(private_manifest["entries"], "source_sha256", "private source")
    input_cases = unique_by(input_manifest["cases"], "case_id", "input case")
    if len(records) != len(input_cases) or len(entries_by_hash) != len(records):
        raise AcceptanceError("private/public case count mismatch")
    loaded: list[dict[str, Any]] = []
    for record in records:
        case_id = record["case_id"]
        input_case = input_cases[case_id]
        expected_public = strip_ap_markers(
            sanitize_source(record["source_text"], case_id)
        ).encode("utf-8")
        if sha256_bytes(expected_public) != input_case["source"]["sha256"]:
            raise AcceptanceError(f"{case_id}: opaque source no longer maps to private source")
        entry = entries_by_hash.get(record["original_sha256"])
        if entry is None:
            raise AcceptanceError(f"{case_id}: no private entry for source digest")
        truth_path = corpus_root / entry["ground_truth_file"]
        if sha256_file(truth_path) != entry["ground_truth_sha256"]:
            raise AcceptanceError(f"{case_id}: private truth digest mismatch")
        truth = read_json(truth_path)
        _validate_private_schema(truth, truth_schema, f"private truth {case_id}")
        if truth["source_sha256"] != record["original_sha256"]:
            raise AcceptanceError(f"{case_id}: private truth source mismatch")
        loaded.append(
            {
                "case_id": case_id,
                "category": truth["category"],
                "truth": truth,
                "input_case": input_case,
            }
        )
    return loaded


def _public_location(input_case: dict[str, Any], private_location: dict[str, Any]) -> dict[str, Any]:
    return {
        "file": input_case["source"]["path"],
        "line": private_location["line"],
        "column": private_location["column"],
    }


def top1_binding_rows(
    private: dict[str, Any],
    artifacts: dict[str, Any],
) -> list[dict[str, Any]]:
    truth = private["truth"]
    input_case = private["input_case"]
    semantic_nodes = {
        node["node_id"]: node for node in artifacts["semantic_index"]["semantic_nodes"]
    }
    by_ap: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for binding in artifacts["ap_bindings"]["bindings"]:
        by_ap[binding["ap_id"]].append(binding)
    rows: list[dict[str, Any]] = []
    for ap in truth["aps"]:
        records = by_ap.get(ap["id"], [])
        candidates = [
            candidate
            for record in records
            for candidate in record["candidates"]
            if candidate["status"] in {"CANDIDATE", "CONFIRMED"}
        ]
        # Candidate arrays are already acceptance-checked as descending by
        # confidence.  Joint-role ties are deterministically broken by ID.
        candidates.sort(key=lambda item: (-item["confidence"], item["binding_id"]))
        top = candidates[0] if candidates else None
        expected = _public_location(input_case, ap["location"])
        locations = [] if top is None else [
            semantic_nodes[node_id]["location"]
            for node_id in top["semantic_node_refs"]
            if node_id in semantic_nodes
        ]
        correct = any(location_matches(location, expected) for location in locations)
        rows.append(
            {
                "case_id": private["case_id"],
                "category": private["category"],
                "ap_id": ap["id"],
                "predicted": top is not None and bool(top["semantic_node_refs"]),
                "correct": correct,
                "top_binding_id": None if top is None else top["binding_id"],
                "resolution": "MISSING" if not records else records[0]["resolution"],
            }
        )
    return rows


def _membership_prediction(memberships: set[str]) -> str | None:
    if "MUST_INFLUENCE" in memberships:
        return "MUST"
    if memberships & {"MAY_INFLUENCE", "MODELLED_INFLUENCE"}:
        return "MAY"
    if "UNKNOWN_INFLUENCE" in memberships:
        return "UNKNOWN"
    return None


def relation_rows(private: dict[str, Any], artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    truth = private["truth"]
    input_case = private["input_case"]
    index = artifacts["semantic_index"]
    graph = artifacts["contextual_influence_graph"]
    cones = artifacts["ap_influence_cones"]
    cone_by_ap = {cone["ap_id"]: cone for cone in cones["cones"]}
    graph_nodes = {node["node_id"]: node for node in graph["nodes"]}
    source_by_id = {source["id"]: source for source in truth["sources"]}
    rows: list[dict[str, Any]] = []
    all_tus_indexed = all(tu["status"] == "indexed" for tu in index["translation_units"])
    for relation in truth["relations"]:
        source = source_by_id[relation["source_id"]]
        expected = _public_location(input_case, source["location"])
        semantic_location_present = any(
            location_matches(node["location"], expected) for node in index["semantic_nodes"]
        )
        candidate_graph_nodes = {
            node_id
            for node_id, node in graph_nodes.items()
            if location_matches(node["location"], expected)
        }
        cone = cone_by_ap[relation["ap_id"]]
        ap_bindings = [
            binding
            for binding in artifacts["ap_bindings"]["bindings"]
            if binding["ap_id"] == relation["ap_id"]
        ]
        accounts = {
            account["binding_id"]: account
            for account in cone["candidate_accounting"]
        }
        binding_is_complete = bool(ap_bindings) and all(
            binding["resolution"] == "CONFIRMED"
            and any(
                candidate["status"] == "CONFIRMED"
                and accounts.get(candidate["binding_id"], {}).get("disposition")
                == "INCLUDED"
                for candidate in binding["candidates"]
            )
            for binding in ap_bindings
        )
        soundness_risk = any(
            item["effect"] in {"soundness_risk", "stage_failure"}
            for artifact_name in (
                "semantic_index",
                "ap_bindings",
                "contextual_influence_graph",
                "ap_influence_cones",
            )
            for item in artifacts[artifact_name]["unsupported_constructs"]
        )
        member_by_node = {member["node_id"]: member for member in cone["members"]}
        memberships = {
            member_by_node[node_id]["membership"]
            for node_id in candidate_graph_nodes
            if node_id in member_by_node
        }
        prediction = _membership_prediction(memberships)
        reason = "matching source node is a cone member"
        if prediction is None:
            complete = (
                semantic_location_present
                and all_tus_indexed
                and graph["status"] == "COMPLETE"
                and cone["status"] == "COMPLETE"
                and binding_is_complete
                and not soundness_risk
            )
            prediction = "NO" if complete else "UNKNOWN"
            reason = (
                "complete index/graph/cone excludes the indexed source location"
                if complete
                else "index/binding/cone completeness or soundness evidence is insufficient"
            )
        rows.append(
            {
                "case_id": private["case_id"],
                "category": private["category"],
                "source_id": relation["source_id"],
                "ap_id": relation["ap_id"],
                "gold": GOLD_LABEL[relation["relation"]],
                "prediction": prediction,
                "reason": reason,
                "memberships": sorted(memberships),
                "semantic_location_present": semantic_location_present,
                "graph_location_nodes": len(candidate_graph_nodes),
            }
        )
    return rows


def unsupported_summary(
    all_artifacts: list[dict[str, Any]],
    relation_predictions: list[dict[str, Any]],
    binding_predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    kinds: collections.Counter[str] = collections.Counter()
    effects: collections.Counter[str] = collections.Counter()
    cone_status: collections.Counter[str] = collections.Counter()
    graph_status: collections.Counter[str] = collections.Counter()
    unknown_members = 0
    unresolved_candidates = 0
    for artifacts in all_artifacts:
        for name in ("semantic_index", "ap_bindings", "contextual_influence_graph", "ap_influence_cones"):
            for item in artifacts[name]["unsupported_constructs"]:
                kinds[item["kind"]] += 1
                effects[item["effect"]] += 1
        graph_status[artifacts["contextual_influence_graph"]["status"]] += 1
        for binding in artifacts["ap_bindings"]["bindings"]:
            unresolved_candidates += sum(
                candidate["status"] == "UNRESOLVED" for candidate in binding["candidates"]
            )
        for cone in artifacts["ap_influence_cones"]["cones"]:
            cone_status[cone["status"]] += 1
            unknown_members += sum(
                member["membership"] == "UNKNOWN_INFLUENCE" for member in cone["members"]
            )
    return {
        "construct_kind_counts": dict(sorted(kinds.items())),
        "construct_effect_counts": dict(sorted(effects.items())),
        "graph_status_counts": dict(sorted(graph_status.items())),
        "cone_status_counts": dict(sorted(cone_status.items())),
        "unknown_cone_members": unknown_members,
        "unresolved_binding_candidates": unresolved_candidates,
        "unknown_pair_predictions": sum(
            row["prediction"] == "UNKNOWN" for row in relation_predictions
        ),
        "unresolved_top1_bindings": sum(
            not row["predicted"] for row in binding_predictions
        ),
    }


def evaluate(
    bundle: Path,
    result_root: Path,
    corpus_root: Path,
    adapter_path: Path,
    expected_cases: int = 120,
) -> dict[str, Any]:
    bundle = bundle.resolve()
    result_root = result_root.resolve()

    # Hard phase boundary: this call validates all production schemas, every
    # hash link, all case coverage, and candidate accounting.  No private
    # manifest or truth path is touched before it returns.
    input_manifest, run, verified_artifacts = validate_run(
        bundle,
        result_root,
        adapter_path=adapter_path,
        expected_cases=expected_cases,
    )
    validated_input_manifest_sha256 = sha256_file(bundle / "manifest.json")
    validated_run_manifest_sha256 = sha256_file(result_root / RUN_MANIFEST)
    if str(corpus_root.resolve()) not in run["sandbox"]["denied_read_roots"]:
        raise AcceptanceError("private corpus was not hidden from the analyzer sandbox")

    private_records = load_private_truth(corpus_root, bundle, input_manifest)
    all_relations: list[dict[str, Any]] = []
    all_bindings: list[dict[str, Any]] = []
    all_artifacts: list[dict[str, Any]] = []
    for private in private_records:
        artifacts = verified_artifacts[private["case_id"]]
        all_artifacts.append(artifacts)
        all_relations.extend(relation_rows(private, artifacts))
        all_bindings.extend(top1_binding_rows(private, artifacts))

    categories = sorted({record["category"] for record in private_records})
    by_category = {
        category: metric_block(
            [row for row in all_relations if row["category"] == category],
            [row for row in all_bindings if row["category"] == category],
        )
        for category in categories
    }
    return {
        "schema_version": "rift.m4.micro-evaluation.v1",
        "synthetic_corpus_status": {
            "oracle": "MECHANICAL_TEMPLATE_ORACLE",
            "human_labels_required": False,
            "real_project_claim": "NOT_APPLICABLE",
        },
        "evidence_identity": {
            "input_manifest_sha256": validated_input_manifest_sha256,
            "run_manifest_sha256": validated_run_manifest_sha256,
            "private_manifest_sha256": sha256_file(corpus_root / "manifest.json"),
            "private_oracle_commitment_sha256": input_manifest[
                "private_oracle_commitment_sha256"
            ],
            "case_count": len(private_records),
            "ap_count": len(all_bindings),
            "pair_count": len(all_relations),
            "sealed_run_validated_before_private_truth_read": True,
        },
        "metric_definitions": {
            "binding_top1": "First highest-confidence binding candidate; exact AP source token/range match. A wrong candidate contributes FP and FN.",
            "influence": "Gold/predicted MUST or MAY are positive. UNKNOWN is an abstention and is a false negative on positive gold, never a true negative.",
            "must_detection": "Gold MUST source location appears in the cone as MUST, MAY, or MODELLED influence.",
            "must_exact": "Gold MUST versus exact MUST membership classification.",
            "may_exact": "Gold MAY versus exact MAY or MODELLED membership classification.",
            "no_from_absence": "NO is inferred only when source location is indexed and TU, graph, and cone are all COMPLETE; otherwise absence is UNKNOWN.",
            "projection": "Cone membership is projected privately onto marked source locations. Intermediate cone nodes are not false positives.",
        },
        "overall": metric_block(all_relations, all_bindings),
        "by_category": by_category,
        "unsupported": unsupported_summary(
            all_artifacts, all_relations, all_bindings
        ),
        "diagnostics": {
            "misclassified_pairs": [
                row for row in all_relations if row["gold"] != row["prediction"]
            ],
            "binding_misses": [row for row in all_bindings if not row["correct"]],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--expected-cases", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        output = arguments.output.resolve()
        run_root = arguments.run.resolve()
        try:
            output.relative_to(run_root)
        except ValueError:
            pass
        else:
            raise AcceptanceError("evaluation output must not modify the sealed run tree")
        if output.exists():
            raise AcceptanceError(f"refusing to overwrite evaluation report: {output}")
        report = evaluate(
            arguments.bundle,
            arguments.run,
            arguments.corpus.resolve(),
            arguments.adapter.resolve(),
            arguments.expected_cases,
        )
        validate_schema(
            report,
            LOCAL_SCHEMA_DIR / "evaluation_report.schema.json",
            "M4 micro evaluation report",
        )
        write_json(output, report)
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        jsonschema.SchemaError,
        AcceptanceError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    overall = report["overall"]
    print(
        "PASS",
        f"cases={report['evidence_identity']['case_count']}",
        f"pairs={report['evidence_identity']['pair_count']}",
        f"binding_top1_f1={overall['binding_top1']['f1']}",
        f"must_detection_recall={overall['must_detection']['detection_recall']}",
        f"influence_f1={overall['influence']['f1']}",
        f"output={arguments.output.resolve()}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
