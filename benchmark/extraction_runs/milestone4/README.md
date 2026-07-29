# Milestone 4: evidence-bound Requirement IR and symbolic MITL

Generated: `2026-07-18T06:25:00+08:00`.

- Curated records: 13 (7 ArduPilot, 6 PX4).
- Every Milestone-3 prefilter candidate is represented in a per-system adjudication ledger.
- `PENDING_CONTEXT_REVIEW` means retained and unresolved; it is neither rejection nor acceptance.
- Concrete MITL is intentionally null until Milestone 6 captures actual runtime parameters.
- No epsilon, conformance result, or source-control-derived requirement was added.

Reproduce:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 4
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_property_catalog.py --stage 4
```
