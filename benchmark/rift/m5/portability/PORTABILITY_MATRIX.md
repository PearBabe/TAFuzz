# RIFT-M5 sealed portability matrix

This directory contains a fail-closed portability seal, not another
self-reported benchmark table.

`build_portability_matrix.py` consumes an input file shaped like
`candidate_inputs.template.json`. It reopens all inputs and emits a matrix only
when `seal_intent` is `FINAL_SEAL_REQUEST` and all three runs already satisfy
the gate. `validate_portability_matrix.py` then independently reopens the
matrix and every referenced byte. The JSON contract is
`portability_matrix.schema.json`.

The checked closure contains, per project:

- the full and analyzed compile databases, their semantic entry ledgers, and
  either `FULL_COMPILE_DB` equality or an exact `SELECTED_REAL_TU` subset;
- a clean tracked Git commit/tree and at least one analyzed real C/C++ TU below
  that repository;
- the typed Property IR, all five M4 artifacts, all seven M5 artifacts, both
  certificates, the executor capability manifest, every model pack, and the
  detached verification report;
- GNU `time -v` receipts for analyzer and detached-verifier performance;
- model-pack raw and executable-semantic digests, layer, rule/selector counts,
  non-comment lines, UNKNOWN accounting, and human adaptation effort.

Across projects it requires different repository/commit/tree/compile-DB/
Property identities but the exact same analyzer bytes, embedded build
manifest, production-core digest, schema digest, detached-verifier identity,
M4 toolchain, M5 runtime toolchain, and generic platform pack. Every runtime
component named by either certificate must have live bytes in the physical
toolchain closure. The build manifest's actual production files are rescanned
for both the frozen contract literals and subject-derived project/property/
adapter literals.

The checked-in candidate template is intentionally inert. It records where the
temporary 75cc libcoap/SVF/LTL-Fuzzer probes were located, but it is not a
portability claim: recipe semantics may still change the core, the current LTL
detached report is not an all-PASS final report, and several final GNU-time
paths/effort measurements are placeholders. The generator rejects the template
before reading those placeholders.

Final use:

```text
cp benchmark/rift/m5/portability/candidate_inputs.template.json /tmp/rift-final-input.json
# replace every candidate path/placeholder, measured effort, and seal_intent
python3 benchmark/rift/m5/portability/build_portability_matrix.py \
  --input /tmp/rift-final-input.json \
  --output benchmark/rift/m5/portability/sealed_portability_matrix.json
python3 benchmark/rift/m5/portability/validate_portability_matrix.py \
  benchmark/rift/m5/portability/sealed_portability_matrix.json \
  --report benchmark/rift/m5/portability/sealed_portability_validation.json
```

Large analyzer artifacts may remain under `/tmp`; that is content-addressed
evidence only while the files still exist. Missing or changed files make the
gate fail. Small checked-in receipts never replace those files and are not
trusted for their declared hashes.
