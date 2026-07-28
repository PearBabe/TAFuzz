# RIFT-M4 micro acceptance validation record

Date: 2026-07-18 (Asia/Shanghai)

## Frozen public input

```text
prepare: PASS cases=120 aps=130
manifest_sha256=8853dada1dcb25d5e63595b453d302b7b90317a659c4a3f81dffdf6bdb62be8f
validate prepared: PASS cases=120 aps=130
files=362
size=2.0 MiB
```

Static leakage scans found no generator marker, generator-semantic source/node identifier, original case ID, category, MUST/MAY/NO relation label, structured source-anchor list, controllability field, or frontier label in `frozen/`. All 120 typed Property IR files use disjoint artifact, property, AP, selector, and formula-node ID domains; in particular, `artifact.property.case_NNN` and `property.case_NNN` cannot collide.

## Build and schema checks

All 120 sanitized raw compile commands were executed with eight workers and temporary object outputs:

```text
SUMMARY cases=120 passed=120 failed=0
```

The production schema suite check reported:

```text
PASS schemas=8 checks=356
schema_tree_sha256=0303b48c3f7eea247dc64bde13e3af31b6f6cd27fe26a97a9b417d519367bbb0
```

The frozen input manifest remains byte-identical (`8853dada...e8f`), while
`schema_migration_ledger.json` records the five authorized pre-final-run
1.0.0 → 2.0.0 transitions. Semantic index, CIG, and certificate close
lossless/provenance gaps; typed Property IR and AP bindings add role-DNF while
retaining strict legacy-v1 compatibility. Every old/new schema ID and byte
hash is exact; a sixth migration or any unlisted schema drift is rejected.
Sealed micro-run v2 manifests bind both the ledger and the active schema tree.

```text
schema_migration_ledger_sha256=93ebcaa806eda1b8cc58a8187d58f2915b03c614f0826d7d7d708ebb75a06c61
active_build_schema_tree_sha256=5bfce26adf3c4b6f0430130559206eac9f4aeec8da0d095fd013a2f34414963d
```

## Deterministic self-tests

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s benchmark/rift/m4/micro/tests -p 'test_*.py' -v
```

Observed result:

```text
Ran 21 tests
OK
```

The tests additionally reject a missing certificate, stale input-file identity,
and reversed/discontinuous source-to-root witness paths. The v2 fake analyzer
exercises build/schema/environment/source-provenance attestation without
reading private truth.

## Full 120-case harness smoke

The truth-free v2 `tests/fake_analyzer.py` was run through the actual runner for all 120 cases. It produced and sealed all four analysis artifacts plus a required certificate, and the trusted evaluator completed 202 source/AP pair projections:

```text
sealed run: PASS cases=120
evaluation: PASS cases=120 pairs=202
```

The fake fixture intentionally indexes only public AP declarations, not influence sources. Its observed `binding_top1_f1=1.0`, `must_detection_recall=0.0`, and `influence_f1=0.0` are harness smoke expectations, **not RIFT method results**. They confirm that missing source coverage remains UNKNOWN instead of being rewarded as NO.

A real production analyzer case (`case_001`) was also checked directly against
the same v2 acceptance path. The validator independently reproduced its
path-map, canonical compile DB, TU ID, source-input/file IDs, input manifest,
semantic-index ID, lossless cross-references, physical file provenance, and
directed cone witnesses; the result passed with certificate schema 2.0.0.
The final calibrated binary SHA-256 was
`756b62398eec78aa20e33ccfbec10554bd400268bc11a64182cc0440997a1ed1`;
the same binary also completed a one-case sandboxed micro-run v2 seal through
`run_analyzer.py` and a second independent `validate_run()` pass.

## Remaining production evidence

This delegated package did not run the real analyzer over all 120 cases. Therefore this record makes no RIFT precision/recall claim. The main integration task must run its frozen production binary through `run_analyzer.py`, pass `validate_acceptance.py --run`, and only then score it with `evaluate.py`.

The delivery tree was checked after tests and contains no `__pycache__` directory or `.pyc` file.
