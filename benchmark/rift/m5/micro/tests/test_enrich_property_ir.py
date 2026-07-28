#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "enrich_property_ir.py"
SPEC = importlib.util.spec_from_file_location("rift_m5_enrich_property_ir", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

WORKSPACE = pathlib.Path(__file__).resolve().parents[5]
FROZEN = WORKSPACE / "benchmark/rift/m4/micro/frozen"
SCHEMAS = WORKSPACE / "src/StaticAnalysis/schema"


def expression_refs(expression: dict) -> list[str]:
    result: list[str] = []
    reference = expression.get("referenced_selector_id")
    if isinstance(reference, str):
        result.append(reference)
    for operand in expression.get("operands", []):
        result.extend(expression_refs(operand))
    return result


class TypedPredicateEnrichmentTests(unittest.TestCase):
    def build(self, output: pathlib.Path, *cases: str) -> dict:
        return MODULE.build_bundle(FROZEN, output, "clang-18", set(cases))

    def validate_schema(self, instance: dict) -> None:
        try:
            from jsonschema import Draft7Validator, RefResolver
        except ImportError as error:  # pragma: no cover - CI image provides jsonschema
            self.fail(f"jsonschema is required for this test: {error}")
        common = json.loads((SCHEMAS / "common.schema.json").read_text(encoding="utf-8"))
        schema = json.loads((SCHEMAS / "typed_property_ir.schema.json").read_text(encoding="utf-8"))
        resolver = RefResolver.from_schema(
            schema, store={common["$id"]: common, schema["$id"]: schema}
        )
        errors = sorted(
            Draft7Validator(schema, resolver=resolver).iter_errors(instance),
            key=lambda error: list(error.path),
        )
        self.assertEqual([], [f"{list(error.path)}: {error.message}" for error in errors])

    def test_positive_ast_literal_cast_reference_and_schema(self) -> None:
        before = MODULE.tree_digest(FROZEN)
        with tempfile.TemporaryDirectory(prefix="rift-m5-enrich-positive-") as directory:
            output = pathlib.Path(directory) / "bundle"
            bundle = self.build(output, "case_001")
            property_ir = json.loads(
                (output / "cases/case_001/property_ir.json").read_text(encoding="utf-8")
            )
            self.validate_schema(property_ir)
            ap = property_ir["atomic_propositions"][0]
            self.assertEqual("2.0.0", property_ir["schema_version"])
            self.assertEqual("comparison", ap["predicate"]["node_kind"])
            self.assertEqual(">", ap["predicate"]["operator"])
            self.assertEqual("cast", ap["predicate"]["operands"][0]["node_kind"])
            self.assertEqual(
                "reference", ap["predicate"]["operands"][0]["operands"][0]["node_kind"]
            )
            self.assertEqual("literal", ap["predicate"]["operands"][1]["node_kind"])
            self.assertEqual(11, ap["predicate"]["operands"][1]["literal"])
            self.assertEqual(32, ap["value_type"]["bit_width"])
            self.assertTrue(ap["value_type"]["signed"])
            self.assertEqual(1, bundle["summary"]["fully_supported_ap_count"])
            self.assertFalse(bundle["knowledge_boundary"]["description_text_used_for_predicate_extraction"])
            self.assertFalse(bundle["knowledge_boundary"]["gold_mutation_answers_used"])
        self.assertEqual(before, MODULE.tree_digest(FROZEN))

    def test_dynamic_comparison_operands_remain_distinct(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-enrich-dynamic-") as directory:
            output = pathlib.Path(directory) / "bundle"
            bundle = self.build(output, "case_011")
            property_ir = json.loads(
                (output / "cases/case_011/property_ir.json").read_text(encoding="utf-8")
            )
            ap = property_ir["atomic_propositions"][0]
            refs = expression_refs(ap["predicate"])
            self.assertEqual(2, len(refs))
            self.assertEqual(2, len(set(refs)))
            roles = {
                ref["selector_id"]: ref["role"] for ref in bundle["cases"][0]["aps"][0]["references"]
            }
            self.assertEqual("state", roles[refs[0]])
            self.assertEqual("bound", roles[refs[1]])
            self.assertEqual("NOT_CLAIMED", bundle["knowledge_boundary"]["semantic_threshold_confirmation"])

    def test_unknown_ast_kind_is_explicit_and_children_survive(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-enrich-unknown-") as directory:
            root = pathlib.Path(directory)
            source_path = root / "fixture.c"
            source_path.write_text("int value;\n", encoding="utf-8")
            source = MODULE.SourceBuffer.load(root, "fixture.c")
            facts = MODULE.TargetTypeFacts(widths={"int": 32, "pointer": 64})
            context = MODULE.ConversionContext("case_test", "ap_test", source, facts)
            node = {
                "kind": "ImaginaryUnsupportedExpr",
                "range": {"begin": {"offset": 0, "tokLen": 3}, "end": {"offset": 0, "tokLen": 3}},
                "type": {"qualType": "int"},
                "inner": [
                    {
                        "kind": "IntegerLiteral",
                        "range": {"begin": {"offset": 0, "tokLen": 1}, "end": {"offset": 0, "tokLen": 1}},
                        "type": {"qualType": "int"},
                        "value": "7",
                    }
                ],
            }
            expression = MODULE.expression_from_ast(node, context, "guard")
            self.assertEqual("unknown", expression["node_kind"])
            self.assertEqual("ImaginaryUnsupportedExpr", expression["operator"])
            self.assertEqual(7, expression["operands"][0]["literal"])
            self.assertEqual(1, context.unsupported["ast_kind:ImaginaryUnsupportedExpr"])

    def test_negative_missing_case_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-enrich-negative-") as directory:
            with self.assertRaisesRegex(MODULE.EnrichmentError, "absent from frozen manifest"):
                self.build(pathlib.Path(directory) / "bundle", "case_does_not_exist")

    def test_deterministic_bundle_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rift-m5-enrich-determinism-") as directory:
            root = pathlib.Path(directory)
            first = root / "first"
            second = root / "second"
            self.build(first, "case_001", "case_011")
            self.build(second, "case_001", "case_011")
            first_files = {
                path.relative_to(first): path.read_bytes()
                for path in sorted(item for item in first.rglob("*") if item.is_file())
            }
            second_files = {
                path.relative_to(second): path.read_bytes()
                for path in sorted(item for item in second.rglob("*") if item.is_file())
            }
            self.assertEqual(first_files, second_files)


if __name__ == "__main__":
    unittest.main()
