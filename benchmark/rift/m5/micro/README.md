# RIFT-M5 typed predicate enrichment

This directory contains a benchmark-only frontend that enriches the immutable
M4 micro-corpus Property IR with recursively typed C/C++ initializer
expressions. It is intentionally separate from the production analyzer and
does not modify M4 inputs.

The extractor's knowledge boundary is strict:

- inputs are the public frozen source, public AP id/source location, the
  compile command, and Clang 18 AST JSON;
- constants and operators come from AST nodes, never from AP descriptions;
- no mutation oracle or M2 gold file is opened;
- each `DeclRefExpr` and `MemberExpr` occurrence receives a unique
  source-location selector;
- comparison operand 0 is emitted as a structural `state` candidate and
  operand 1 as a structural `bound` candidate; this does **not** claim that
  either operand is semantically a temporal threshold;
- unsupported AST nodes become `node_kind: unknown`, retain converted
  children, and are reported in the bundle manifest.

Generate all 120 cases:

```bash
python3 benchmark/rift/m5/micro/enrich_property_ir.py \
  --summary-output benchmark/rift/m5/results/micro_property_enrichment.json
```

Run the positive, negative, dynamic-boundary, UNKNOWN, and deterministic-byte
tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s benchmark/rift/m5/micro/tests -p 'test_*.py' -v
```

Validate all generated properties against JSON Schema and the production C++
loader/validator/binder (the analyzer is explicit and digest-bound):

```bash
python3 benchmark/rift/m5/micro/validate_bundle.py \
  --analyzer /path/to/tafuzz-sa \
  --output benchmark/rift/m5/results/micro_property_enrichment_validation.json
```

Generated artifacts are under `bundle/`. The manifest binds every source,
compile database, original Property IR, enriched Property IR, Clang executable,
and extractor digest. It also records equal pre/post digests for the complete
frozen M4 tree.
