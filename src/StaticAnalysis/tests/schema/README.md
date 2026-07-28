# RIFT production-schema tests

`validate_schemas.py` validates the versioned, project-neutral M4 interfaces
with Draft 7 JSON Schema. It checks each schema itself, canonical serialization,
positive fixtures, closed object boundaries, required context dimensions, and
negative invariants that prevent similarity-only binding confirmation,
uncertainty erasure, cone pruning, or forbidden model-rule classes.

The model-pack schema is only an input contract at this milestone. These tests
do not claim that a model execution engine exists. Cross-document identifier
referential integrity and identifier uniqueness remain loader responsibilities;
the JSON Schemas deliberately handle structural validation only.

Run directly with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  src/StaticAnalysis/tests/schema/validate_schemas.py \
  --schema-dir src/StaticAnalysis/schema
```
