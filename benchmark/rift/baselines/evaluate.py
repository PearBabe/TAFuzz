#!/usr/bin/env python3
"""Evaluate a complete weak-baseline prediction matrix against private gold.

The baseline analyzer must never read the gold tree.  This trusted evaluator is
the only post-analysis component that joins opaque case_NNN identifiers back to
mechanical truth and reports category/edge/frontier metrics.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from prepare_inputs import build_sanitized_case, load_source_records


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
DEFAULT_GOLD = WORKSPACE / "benchmark" / "rift" / "gold"
INPUT_SCHEMA = HERE / "analyzer_input.schema.json"
RESULT_SCHEMA = HERE / "baseline_result.schema.json"

GOLD_TO_PREDICTION = {
    "MUST_INFLUENCE": "MUST",
    "MAY_INFLUENCE": "MAY",
    "NO_INFLUENCE": "NO",
}
POSITIVE_PREDICTIONS = {"MUST", "MAY"}
CLASS_LABELS = ("MUST", "MAY", "NO")
PREDICTION_LABELS = ("MUST", "MAY", "NO", "UNKNOWN")
EDGE_KINDS = (
    "data",
    "control",
    "call",
    "return",
    "alias",
    "field",
    "parse",
    "state_commit",
    "timer",
    "callback",
    "enqueue",
    "dequeue",
    "setup",
    "timing",
    "event_order",
)


class EvaluationError(ValueError):
    """Raised for malformed, incomplete, or input-mismatched baseline output."""


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_gold_records(gold_root: Path) -> list[dict[str, Any]]:
    """Private join: this is the only analysis-stage reader of relation truth."""
    records = load_source_records(gold_root)
    manifest = read_json(gold_root / "manifest.json")
    entries = {
        entry["source_file"]: entry for entry in manifest.get("entries", [])
    }
    if len(entries) != len(records):
        raise EvaluationError(
            f"gold manifest/source count mismatch: {len(entries)} != {len(records)}"
        )
    for record in records:
        relative = str(record["source_path"].relative_to(gold_root))
        entry = entries.get(relative)
        if entry is None:
            raise EvaluationError(f"private truth entry missing for {relative}")
        if entry["source_sha256"] != record["source_sha256"]:
            raise EvaluationError(f"private source hash mismatch for {relative}")
        truth = read_json(gold_root / entry["ground_truth_file"])
        if truth["source_file"] != relative:
            raise EvaluationError(f"private truth source identity mismatch for {relative}")
        record["entry"] = entry
        record["truth"] = truth
    return records


def validate_schema(instance: Any, schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    try:
        jsonschema.Draft7Validator.check_schema(schema)
        jsonschema.Draft7Validator(schema).validate(instance)
    except jsonschema.ValidationError as error:
        location = "/".join(str(item) for item in error.absolute_path)
        raise EvaluationError(f"{label} schema error at {location or '<root>'}: {error.message}") from error
    except jsonschema.SchemaError as error:
        raise EvaluationError(f"invalid {label} schema: {error.message}") from error


def unique_by(items: Iterable[dict[str, Any]], key, label: str) -> dict[Any, dict[str, Any]]:
    result: dict[Any, dict[str, Any]] = {}
    for item in items:
        identity = key(item)
        if identity in result:
            raise EvaluationError(f"duplicate {label}: {identity!r}")
        result[identity] = item
    return result


def expected_case_status(predictions: list[dict[str, Any]]) -> str:
    statuses = [prediction["status"] for prediction in predictions]
    if "ERROR" in statuses:
        return "ERROR"
    if statuses and all(status == "UNSUPPORTED" for status in statuses):
        return "UNSUPPORTED"
    if "UNSUPPORTED" in statuses:
        return "PARTIAL"
    return "COMPLETE"


def expected_analysis_status(cases: list[dict[str, Any]]) -> str:
    statuses = [case["status"] for case in cases]
    if "ERROR" in statuses:
        return "ERROR"
    if statuses and all(status == "UNSUPPORTED" for status in statuses):
        return "UNSUPPORTED"
    if any(status in {"PARTIAL", "UNSUPPORTED"} for status in statuses):
        return "PARTIAL"
    return "COMPLETE"


def validate_pair_semantics(prediction: dict[str, Any], case_id: str) -> None:
    label = f"{case_id}:{prediction['source_id']}->{prediction['ap_id']}"
    relation = prediction["prediction"]
    status = prediction["status"]
    edges = prediction["edges"]

    if relation == "UNKNOWN":
        if status not in {"UNSUPPORTED", "ERROR"}:
            raise EvaluationError(f"{label}: UNKNOWN must be UNSUPPORTED or ERROR")
        if edges:
            raise EvaluationError(f"{label}: UNKNOWN must have no edges")
    else:
        if status != "ANALYZED":
            raise EvaluationError(f"{label}: a concrete prediction must have status ANALYZED")
    if relation == "NO" and edges:
        raise EvaluationError(f"{label}: NO must have no positive-path edges")
    if relation in POSITIVE_PREDICTIONS and not edges:
        raise EvaluationError(f"{label}: positive predictions require at least one evidenced edge")

    edge_keys: set[tuple[str, str, str]] = set()
    for edge in edges:
        identity = (edge["from"], edge["to"], edge["kind"])
        if identity in edge_keys:
            raise EvaluationError(f"{label}: duplicate edge identity {identity!r}")
        edge_keys.add(identity)


def validate_contracts(
    *,
    input_path: Path,
    input_manifest: dict[str, Any],
    result: dict[str, Any],
    records: list[dict[str, Any]],
    gold_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    validate_schema(input_manifest, INPUT_SCHEMA, "analyzer input")
    validate_schema(result, RESULT_SCHEMA, "baseline result")
    if result["input_manifest_sha256"] != sha256_file(input_path):
        raise EvaluationError("result input_manifest_sha256 does not match analyzer input")

    input_cases = unique_by(input_manifest["cases"], lambda item: item["case_id"], "input case")
    expected_ids = {record["opaque_case_id"] for record in records}
    if set(input_cases) != expected_ids:
        raise EvaluationError(
            f"input case set differs from private mapping: expected {len(expected_ids)}, "
            f"got {len(input_cases)}"
        )
    for record in records:
        case_id = record["opaque_case_id"]
        expected_case, _ = build_sanitized_case(record, gold_root)
        if input_cases[case_id] != expected_case:
            raise EvaluationError(f"sanitized input contract changed for {case_id}")

    result_cases = unique_by(result["cases"], lambda item: item["case_id"], "result case")
    if set(result_cases) != set(input_cases):
        missing = sorted(set(input_cases) - set(result_cases))
        extra = sorted(set(result_cases) - set(input_cases))
        raise EvaluationError(f"result case set is incomplete: missing={missing}, extra={extra}")

    for case_id, input_case in input_cases.items():
        source_ids = {item["id"] for item in input_case["source_anchors"]}
        ap_ids = {item["id"] for item in input_case["ap_anchors"]}
        expected_pairs = {(source_id, ap_id) for source_id in source_ids for ap_id in ap_ids}
        predictions = result_cases[case_id]["predictions"]
        by_pair = unique_by(
            predictions,
            lambda item: (item["source_id"], item["ap_id"]),
            f"prediction pair in {case_id}",
        )
        if set(by_pair) != expected_pairs:
            missing = sorted(expected_pairs - set(by_pair))
            extra = sorted(set(by_pair) - expected_pairs)
            raise EvaluationError(
                f"{case_id}: prediction matrix must be the full source×AP cross product; "
                f"missing={missing}, extra={extra}"
            )
        for prediction in predictions:
            validate_pair_semantics(prediction, case_id)
        derived = expected_case_status(predictions)
        if result_cases[case_id]["status"] != derived:
            raise EvaluationError(
                f"{case_id}: case status {result_cases[case_id]['status']} != derived {derived}"
            )

    derived_analysis = expected_analysis_status(list(result_cases.values()))
    if result["analysis_status"] != derived_analysis:
        raise EvaluationError(
            f"analysis_status {result['analysis_status']} != derived {derived_analysis}"
        )
    execution = result["execution"]
    if derived_analysis in {"COMPLETE", "PARTIAL"} and execution["exit_code"] != 0:
        raise EvaluationError("successful/partial analysis requires execution exit_code 0")
    if execution["analyzed_units"] > len(input_cases):
        raise EvaluationError("execution analyzed_units exceeds input case count")
    if derived_analysis == "COMPLETE" and execution["analyzed_units"] != len(input_cases):
        raise EvaluationError("COMPLETE analysis must report all cases as analyzed_units")
    return input_cases, result_cases


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def binary_metrics(states: Iterable[tuple[bool, str]]) -> dict[str, Any]:
    """Compute binary metrics where prediction state is YES, NO, or UNKNOWN."""
    counts = collections.Counter(states)
    tp = counts[(True, "YES")]
    fp = counts[(False, "YES")]
    fn = counts[(True, "NO")] + counts[(True, "UNKNOWN")]
    tn = counts[(False, "NO")]
    abstain_negative = counts[(False, "UNKNOWN")]
    total = tp + fp + fn + tn + abstain_negative
    precision = safe_ratio(tp, tp + fp)
    recall = safe_ratio(tp, tp + fn)
    f1 = safe_ratio(2 * tp, 2 * tp + fp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "unknown_on_negative": abstain_negative,
        "total": total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy_unknown_is_wrong": safe_ratio(tp + tn, total),
    }


def classification_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    confusion = {
        gold: {prediction: 0 for prediction in PREDICTION_LABELS}
        for gold in CLASS_LABELS
    }
    for row in rows:
        confusion[row["gold"]][row["prediction"]] += 1

    per_class: dict[str, Any] = {}
    for label in CLASS_LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in CLASS_LABELS if other != label)
        fn = sum(confusion[label][prediction] for prediction in PREDICTION_LABELS if prediction != label)
        per_class[label] = {
            "support": sum(confusion[label].values()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": safe_ratio(tp, tp + fp),
            "recall": safe_ratio(tp, tp + fn),
            "f1": safe_ratio(2 * tp, 2 * tp + fp + fn),
        }
    exact = sum(confusion[label][label] for label in CLASS_LABELS)
    macro_f1_values = [per_class[label]["f1"] or 0.0 for label in CLASS_LABELS]
    return {
        "total": len(rows),
        "exact": exact,
        "exact_accuracy_unknown_is_wrong": safe_ratio(exact, len(rows)),
        "unknown": sum(confusion[label]["UNKNOWN"] for label in CLASS_LABELS),
        "confusion_matrix_gold_rows": confusion,
        "per_class": per_class,
        "macro_f1_undefined_as_zero": sum(macro_f1_values) / len(CLASS_LABELS),
    }


def influence_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    states = []
    for row in rows:
        gold_positive = row["gold"] in POSITIVE_PREDICTIONS
        prediction = row["prediction"]
        predicted_state = (
            "YES" if prediction in POSITIVE_PREDICTIONS else "NO" if prediction == "NO" else "UNKNOWN"
        )
        states.append((gold_positive, predicted_state))
    return binary_metrics(states)


def actionable_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derived diagnostic; controllability is supplied and is not discovered/scored."""
    return binary_metrics(
        (row["gold_actionable"], "YES" if row["predicted_actionable"] else "NO")
        for row in rows
    )


def must_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    must = [row for row in rows if row["gold"] == "MUST"]
    detected = sum(row["prediction"] in POSITIVE_PREDICTIONS for row in must)
    exact = sum(row["prediction"] == "MUST" for row in must)
    predicted_must = sum(row["prediction"] == "MUST" for row in rows)
    downgraded = sum(row["prediction"] == "MAY" for row in must)
    unresolved = sum(row["prediction"] == "UNKNOWN" for row in must)
    return {
        "gold_must": len(must),
        "predicted_must": predicted_must,
        "detected_as_influence": detected,
        "exact_must": exact,
        "exact_precision": safe_ratio(exact, predicted_must),
        "detection_recall": safe_ratio(detected, len(must)),
        "exact_recall": safe_ratio(exact, len(must)),
        "downgraded_to_may": downgraded,
        "downgrade_rate": safe_ratio(downgraded, len(must)),
        "unresolved": unresolved,
        "unresolved_rate": safe_ratio(unresolved, len(must)),
    }


def candidate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold_positive = sum(row["gold"] in POSITIVE_PREDICTIONS for row in rows)
    predicted_positive = sum(row["prediction"] in POSITIVE_PREDICTIONS for row in rows)
    true_candidates = sum(
        row["gold"] in POSITIVE_PREDICTIONS
        and row["prediction"] in POSITIVE_PREDICTIONS
        for row in rows
    )
    false_candidates = sum(
        row["gold"] == "NO" and row["prediction"] in POSITIVE_PREDICTIONS
        for row in rows
    )
    return {
        "gold_positive_pairs": gold_positive,
        "predicted_candidate_pairs": predicted_positive,
        "true_candidate_pairs": true_candidates,
        "false_candidate_pairs": false_candidates,
        "candidate_set_size_ratio": safe_ratio(predicted_positive, gold_positive),
        "false_candidate_inflation_per_gold_positive": safe_ratio(false_candidates, gold_positive),
        "candidate_precision": safe_ratio(true_candidates, predicted_positive),
    }


def unsupported_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unknown = sum(row["prediction"] == "UNKNOWN" for row in rows)
    errors = sum(row["status"] == "ERROR" for row in rows)
    unsupported = sum(row["status"] == "UNSUPPORTED" for row in rows)
    queries: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        queries[(row["case_id"], row["ap_id"])].append(row)
    fully_resolved_queries = sum(
        all(row["prediction"] != "UNKNOWN" for row in query_rows)
        for query_rows in queries.values()
    )
    fully_unknown_queries = sum(
        all(row["prediction"] == "UNKNOWN" for row in query_rows)
        for query_rows in queries.values()
    )
    partially_resolved_queries = len(queries) - fully_resolved_queries - fully_unknown_queries
    return {
        "unknown_pairs": unknown,
        "unsupported_pairs": unsupported,
        "error_pairs": errors,
        "unknown_rate": safe_ratio(unknown, len(rows)),
        "ap_queries": len(queries),
        "fully_resolved_ap_queries": fully_resolved_queries,
        "partially_resolved_ap_queries": partially_resolved_queries,
        "fully_unknown_ap_queries": fully_unknown_queries,
        "fully_resolved_ap_query_coverage": safe_ratio(fully_resolved_queries, len(queries)),
    }


def set_metrics(gold: set[Any], predicted: set[Any]) -> dict[str, Any]:
    tp = len(gold & predicted)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    return {
        "gold": len(gold),
        "predicted": len(predicted),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": safe_ratio(tp, tp + fp),
        "recall": safe_ratio(tp, tp + fn),
        "f1": safe_ratio(2 * tp, 2 * tp + fp + fn),
    }


def edge_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold_edges: set[tuple[Any, ...]] = set()
    predicted_edges: set[tuple[Any, ...]] = set()
    gold_kinds: set[tuple[Any, ...]] = set()
    predicted_kinds: set[tuple[Any, ...]] = set()
    all_kinds: set[str] = set()
    for row in rows:
        prefix = (row["case_id"], row["source_id"], row["ap_id"])
        for edge in row["gold_edges"]:
            gold_edges.add(prefix + (edge["from"], edge["to"], edge["kind"]))
            gold_kinds.add(prefix + (edge["kind"],))
            all_kinds.add(edge["kind"])
        for edge in row["predicted_edges"]:
            predicted_edges.add(prefix + (edge["from"], edge["to"], edge["kind"]))
            predicted_kinds.add(prefix + (edge["kind"],))
            all_kinds.add(edge["kind"])

    by_kind = {}
    for kind in sorted(set(EDGE_KINDS) | all_kinds):
        metrics = set_metrics(
            {edge for edge in gold_kinds if edge[-1] == kind},
            {edge for edge in predicted_kinds if edge[-1] == kind},
        )
        metrics["status"] = "PRESENT" if metrics["gold"] else "NOT_PRESENT_IN_GOLD"
        by_kind[kind] = metrics
    return {
        "primary_pair_edge_kind": set_metrics(gold_kinds, predicted_kinds),
        "unprojected_exact_endpoint_diagnostic": {
            "status": "UNPROJECTED_DIAGNOSTIC_NOT_HEADLINE",
            **set_metrics(gold_edges, predicted_edges),
        },
        "by_kind": by_kind,
    }


def metric_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "classification": classification_metrics(rows),
        "influence": influence_metrics(rows),
        "must": must_metrics(rows),
        "actionable_derived": actionable_metrics(rows),
        "edges": edge_metrics(rows),
        "unsupported": unsupported_metrics(rows),
        "candidate_inflation_pair_classification_diagnostic": candidate_metrics(rows),
    }


def build_rows(
    records: list[dict[str, Any]],
    input_cases: dict[str, dict[str, Any]],
    result_cases: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        case_id = record["opaque_case_id"]
        truth = record["truth"]
        source_map = {source["id"]: source for source in truth["sources"]}
        supplied_controllability = {
            item["source_id"]: item["classification"]
            for item in input_cases[case_id]["controllability"]
        }
        predictions = {
            (item["source_id"], item["ap_id"]): item
            for item in result_cases[case_id]["predictions"]
        }
        for relation in truth["relations"]:
            pair = (relation["source_id"], relation["ap_id"])
            prediction = predictions[pair]
            source = source_map[relation["source_id"]]
            rows.append(
                {
                    "case_id": case_id,
                    "category": truth["category"],
                    "source_id": relation["source_id"],
                    "ap_id": relation["ap_id"],
                    "gold": GOLD_TO_PREDICTION[relation["relation"]],
                    "prediction": prediction["prediction"],
                    "status": prediction["status"],
                    "gold_actionable": relation["relation"] != "NO_INFLUENCE"
                    and source["fuzzable_frontier"] is True,
                    "predicted_actionable": prediction["prediction"] in POSITIVE_PREDICTIONS
                    and supplied_controllability[relation["source_id"]]
                    in {"EXTERNAL", "MODELLED"},
                    "gold_edges": relation["path"]["edges"],
                    "predicted_edges": prediction["edges"],
                    "limitations": prediction["limitations"],
                }
            )
    return rows


def limitation_counts(result: dict[str, Any]) -> dict[str, int]:
    values: list[str] = list(result["limitations"])
    for case in result["cases"]:
        values.extend(case["limitations"])
        for prediction in case["predictions"]:
            values.extend(prediction["limitations"])
            for edge in prediction["edges"]:
                values.extend(edge["limitations"])
    return dict(sorted(collections.Counter(values).items()))


def diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    misclassified = [
        {
            "case_id": row["case_id"],
            "source_id": row["source_id"],
            "ap_id": row["ap_id"],
            "gold": row["gold"],
            "prediction": row["prediction"],
        }
        for row in rows
        if row["gold"] != row["prediction"]
    ]
    actionable_errors = [
        {
            "case_id": row["case_id"],
            "source_id": row["source_id"],
            "ap_id": row["ap_id"],
            "gold": "YES" if row["gold_actionable"] else "NO",
            "prediction": "YES" if row["predicted_actionable"] else "NO",
        }
        for row in rows
        if row["gold_actionable"] != row["predicted_actionable"]
    ]
    return {
        "misclassified_pairs": misclassified,
        "actionable_derived_errors": actionable_errors,
    }


def evaluate(input_path: Path, result_path: Path, gold_root: Path) -> dict[str, Any]:
    input_path = input_path.resolve()
    result_path = result_path.resolve()
    gold_root = gold_root.resolve()
    input_manifest = read_json(input_path)
    result = read_json(result_path)
    records = load_gold_records(gold_root)
    input_cases, result_cases = validate_contracts(
        input_path=input_path,
        input_manifest=input_manifest,
        result=result,
        records=records,
        gold_root=gold_root,
    )
    rows = build_rows(records, input_cases, result_cases)
    by_category = {
        category: metric_block([row for row in rows if row["category"] == category])
        for category in sorted({row["category"] for row in rows})
    }
    return {
        "schema_version": "rift.baseline-evaluation.v1",
        "analyzer": result["analyzer"],
        "execution": result["execution"],
        "analysis_status": result["analysis_status"],
        "evidence_identity": {
            "gold_manifest_sha256": sha256_file(gold_root / "manifest.json"),
            "input_manifest_sha256": sha256_file(input_path),
            "result_sha256": sha256_file(result_path),
            "case_count": len(records),
            "pair_count": len(rows),
        },
        "metric_definitions": {
            "positive_influence": "gold/predicted MUST or MAY",
            "unknown": "UNKNOWN is an abstention: it is never counted as NO or as a true negative; on positive gold it is a false negative",
            "must_detection_recall": "gold MUST predicted as MUST or MAY",
            "must_exact_recall": "gold MUST predicted exactly as MUST",
            "actionable_derived": "predicted positive relation AND provided controllability is EXTERNAL/MODELLED; this is a pair-classification diagnostic, not frontier discovery",
            "edge_kind": "headline cross-method edge metric is set membership of (opaque case, given source, given AP, edge kind)",
            "exact_edge_boundary": "raw AST/LLVM/SVF entities are not projected to gold node IDs; exact endpoints are UNPROJECTED_DIAGNOSTIC and never headline",
            "candidate_set_size_ratio": "within the supplied source×AP universe, predicted MUST/MAY pair count divided by gold MUST/MAY pair count; this is not open source-discovery candidate burden",
            "false_candidate_inflation": "within the supplied source×AP universe, predicted-positive/gold-NO pairs divided by gold-positive pairs",
        },
        "overall": metric_block(rows),
        "by_category": by_category,
        "limitation_counts": limitation_counts(result),
        "diagnostics": diagnostics(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate(args.input, args.result, args.gold)
        write_json(args.output, report)
    except (
        OSError,
        KeyError,
        TypeError,
        EvaluationError,
        json.JSONDecodeError,
        jsonschema.SchemaError,
    ) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    overall = report["overall"]
    print(
        "PASS",
        f"cases={report['evidence_identity']['case_count']}",
        f"pairs={report['evidence_identity']['pair_count']}",
        f"influence_f1={overall['influence']['f1']}",
        f"must_recall={overall['must']['detection_recall']}",
        f"exact_accuracy={overall['classification']['exact_accuracy_unknown_is_wrong']}",
        f"actionable_f1={overall['actionable_derived']['f1']}",
        f"output={args.output.resolve()}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
