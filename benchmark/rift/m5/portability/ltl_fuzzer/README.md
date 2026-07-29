# LTL-Fuzzer independent RIFT-M5 portability probe

Status: **FULL_13_TU_DETACHED_PASS**.

This directory checks the unchanged RIFT schema-3 binary on the frozen
LTL-Fuzzer ICSE 2022 artifact source itself.  It is deliberately labeled
`PORTABILITY_PROBE_NOT_REQUIREMENT`: the selected predicate is a real typed
source predicate, not a requirement from an external specification and not a
human-reviewed gold label.

## Frozen target and predicate

- repository: `benchmark/rift/external/ltl_fuzzer`;
- commit: `716ac301fa3a8ea39814bc80eeebba49c19c1378`;
- tree: `ee7f4a651abf3e7f6104be92751e4880385ead85`;
- predicate: `argc < 2` at `src/main.cc:10:8-15`;
- predicate type: `bool`;
- influenced value: `argc`, Clang type `int`, exact declaration USR
  `c:main.cc@156@F@main#I#**C#@argc`.

`derive_ast_evidence.py` derives the source ranges, types, compile entry and
frozen checkout identity from Clang 18 evidence.  The property intentionally
uses two complementary selectors: the declaration USR makes the influence
root an exact `argc` semantic node, while the source-range selector binds the
predicate occurrence.  This is property input data; no project, path, symbol,
or expected-answer literal is added to RIFT core code.

Only the generic model pack
`src/StaticAnalysis/model_packs/platform/posix_lp64_v1.json` is loaded.
`executor_capabilities.json` says only that the test runner can choose process
argument count.  It is not a model pack and contains no dependency edge.

## Result boundary

The final frozen analyzer completes all 13 project TUs in 20.64 seconds at
370,892 KiB peak RSS.  It emits one exact occurrence, one compatible modelled
`argc` witness, one actionable frontier action, and one conservative HEURISTIC
recipe.  The probe-specific semantic verifier passes 33/33 checks; independent
detached certificate reconstruction passes 65/65 and rehashes 2,161 files.

An earlier analyzer failed on `utils.cc`: it treated `ifs.end` and `ifs.beg` as
instance-field access-path components even though Clang resolves them as static
`std::ios_base::seekdir` constants.  That failure was minimized to one TU and
then fixed generically in core; `full_project_blocker.json` preserves the
failure and resolution evidence.  No LTL-Fuzzer-specific exception was added.

An intermediate detached verifier reported 18 paired differences for nine
rejected non-actionable candidates because it pruned a zero reverse state even
when reverse-cone enumeration was incomplete.  The producer prunes only when
`enumeration_complete && state == 0`.  After the verifier was aligned with that
production rule, the same immutable output bundle passes every compact-ledger,
candidate-evidence, projection, recipe and replay check.  The pre-fix mismatch
is retained only as historical diagnostic evidence.

No runtime AP flip was executed.  Z3 proves only that the selector-local
predicate can flip.  RIFT correctly withholds an external mutation direction
because `process_argument_count` is represented as a non-identity transfer;
therefore this probe does not claim direction accuracy, runtime usefulness, or
fuzzing gain.

## Reproduction

Configure a temporary Clang 18 compilation database without editing the frozen
checkout:

```bash
cmake \
  -S /home/lqq/project/TAFuzz/benchmark/rift/external/ltl_fuzzer \
  -B /tmp/rift-m5-ltl-fuzzer-clang18 \
  -G Ninja \
  -DCMAKE_C_COMPILER=/usr/bin/clang-18 \
  -DCMAKE_CXX_COMPILER=/usr/bin/clang++-18 \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo

python3 benchmark/rift/m5/portability/ltl_fuzzer/derive_ast_evidence.py \
  --compile-db /tmp/rift-m5-ltl-fuzzer-clang18/compile_commands.json \
  --single-tu-db /tmp/rift-m5-ltl-fuzzer-clang18/compile_commands.main.json \
  --output /tmp/rift-m5-ltl-fuzzer-clang18/ast_evidence.json
```

Run the sealed full-project probe:

```bash
/tmp/tafuzz-sa-m5-schema3-75cc7f4d74d8507dacd4e2919393406d15e867d8422efec2519c89a344327f0a \
  recipes \
  --compile-db /tmp/rift-m5-ltl-fuzzer-clang18/compile_commands.json \
  --property benchmark/rift/m5/portability/ltl_fuzzer/property_ir.json \
  --output-dir /tmp/rift-m5-ltl-fuzzer-schema3-full \
  --logical-root source=/home/lqq/project/TAFuzz/benchmark/rift/external/ltl_fuzzer \
  --logical-root build=/tmp/rift-m5-ltl-fuzzer-clang18 \
  --logical-root llvm=/usr/lib/llvm-18 \
  --model-pack src/StaticAnalysis/model_packs/platform/posix_lp64_v1.json \
  --executor-capabilities benchmark/rift/m5/portability/ltl_fuzzer/executor_capabilities.json \
  --solver-timeout-ms 1000 \
  --max-solver-queries 100
```

Verify the probe contract and detached certificate:

```bash
python3 benchmark/rift/m5/portability/ltl_fuzzer/verify_probe.py \
  --output-dir /tmp/rift-m5-ltl-fuzzer-schema3-full \
  --property benchmark/rift/m5/portability/ltl_fuzzer/property_ir.json \
  --executor benchmark/rift/m5/portability/ltl_fuzzer/executor_capabilities.json \
  --ast-evidence benchmark/rift/m5/portability/ltl_fuzzer/ast_evidence.json \
  --expected-translation-units 13 \
  --report /tmp/rift-m5-ltl-fuzzer-schema3-full/probe_verification.json

python3 src/StaticAnalysis/tests/verify_m5_certificate.py \
  /tmp/rift-m5-ltl-fuzzer-schema3-full \
  --schema-dir src/StaticAnalysis/schema \
  --report /tmp/rift-m5-ltl-fuzzer-schema3-full/detached_verification.json
```

Bulk analyzer outputs remain under `/tmp`; `result_manifest.json` seals their
sizes and hashes.  The external checkout and its existing untracked build
artifacts are not modified or removed.
