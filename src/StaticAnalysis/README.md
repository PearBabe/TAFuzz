# TAFuzz Static Analysis

This directory contains the project-neutral C++20/Clang implementation used by
RIFT and its weak baselines. Project and framework knowledge belongs under
`model_packs/`; generic code under `core/`, `include/`, and `cli/` must not
contain subject-specific symbols or paths.

## Build all M3 weak baselines

The current machine has the Clang/LLVM 18 runtime and LLVM development files,
but not the installed `libclang-18-dev` headers. A pinned, non-root bootstrap is
provided so the build does not silently depend on an ad-hoc `/tmp` tree:

```bash
src/StaticAnalysis/scripts/bootstrap_clang18_headers.sh \
  /tmp/tafuzz-libclang-18-dev

cmake -S src/StaticAnalysis -B /tmp/tafuzz-sa-build -G Ninja \
  -DCMAKE_CXX_COMPILER=clang++-18 \
  -DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm \
  -DSVF_DIR=/home/lqq/project/TAFuzz/benchmark/rift/reproduction/svf/install/lib/cmake/SVF \
  -DRIFT_CLANG_INCLUDE_DIR=/tmp/tafuzz-libclang-18-dev/usr/lib/llvm-18/include \
  -DRIFT_CLANG_CPP_LIBRARY=/usr/lib/llvm-18/lib/libclang-cpp.so.18.1
cmake --build /tmp/tafuzz-sa-build -j2
ctest --test-dir /tmp/tafuzz-sa-build --output-on-failure
```

`SVF_DIR` must point to the CMake package for the frozen SVF 3.2 build. If
`libclang-18-dev` is installed normally, omit `RIFT_CLANG_INCLUDE_DIR`. The
bootstrap otherwise downloads the pinned
`libclang-18-dev` version
`1:18.1.8~++20240731024944+3b5b5c1ec4a3-1~exp1~20240731145000.144`, verifies
SHA-256
`c1e3eb5c7c930062457f91eb10542a9d6a3eecc39cc198bc4facb712cc0927d0`, and
extracts it without modifying the system package database.

## Run the M4 production pipeline

`tafuzz-sa influence` consumes a raw Clang compilation database and a typed
Property IR. Repeat `--logical-root <id>=<absolute-path>` for every relocatable
source/build root whose identity must survive moving the workspace:

```bash
/tmp/tafuzz-sa-build/tafuzz-sa influence \
  --compile-db /absolute/build/compile_commands.json \
  --property /absolute/property/typed_property_ir.json \
  --logical-root source=/absolute/project/source \
  --logical-root build=/absolute/project/build \
  --output-dir /new/nonexistent/result-directory
```

The output directory must not already exist. The command stages artifacts and
publishes them only after validation succeeds:

```text
semantic_index.json
ap_bindings.json
contextual_influence_graph.json
ap_influence_cones.json
analysis_certificate.json
```

Property IR 2.0 uses `role_selector_groups`: selectors inside one `all_of` are
a relational conjunction; multiple groups for the same role are intentional
alternatives. Unresolved groups remain explicit. Legacy Property IR 1.0 and
bindings 1.0 are accepted only through their closed compatibility branches.

The model-pack schema is an input contract in M4; no production model-pack
execution engine, controllable frontier, or mutation recipe is claimed yet.
Use the independent Certificate v2 verifier for artifact/provenance replay:

```bash
python3 benchmark/rift/m4/verifier/verify.py --help
```

M4 implementation/evaluation details are in
`analysis/rift_m4_results_zh.md` and
`benchmark/rift/m4/results/execution_manifest.json`.

## Run the fair M3 diagnostic

Prepare an opaque input outside the workspace, run one baseline, then let the
trusted evaluator join predictions to private mechanical truth:

```bash
python3 benchmark/rift/baselines/prepare_inputs.py \
  --output /tmp/rift-m3-input

/tmp/tafuzz-sa-build/tafuzz-sa baseline \
  --method plain-pdg \
  --input /tmp/rift-m3-input/analyzer_input.json \
  --output /tmp/plain-pdg-result.json

python3 benchmark/rift/baselines/evaluate.py \
  --input /tmp/rift-m3-input/analyzer_input.json \
  --result /tmp/plain-pdg-result.json \
  --output /tmp/plain-pdg-evaluation.json
```

The six M3 methods are:

- `adgfuzz-assignment`: assignment-only Clang AST dependency;
- `moonshine-rw`: MoonShine-style call read/write intersection;
- `plain-pdg`: context-insensitive AST data/control/call dependency;
- `llvm-def-use`: LLVM SSA backward def-use traversal;
- `memoryssa-aa`: LLVM MemorySSA plus alias analysis;
- `svf-value-flow`: SVF 3.2 backward value-flow traversal.

This M3 track is deliberately a `PAIR_CLASSIFICATION_DIAGNOSTIC`: candidate
source/AP anchors and controllability labels are supplied to every method and
are not scored as source discovery, AP binding, or fuzzable-frontier discovery.
`UNKNOWN` is not treated as a true negative. Exact endpoint metrics remain
unprojected diagnostics rather than headline results.

The JSON receipt samples only the analyzer process through preflight result
serialization (`RUSAGE_SELF`); compiler child processes and the final result
write are outside that self measurement. Publication/headline wall time and
peak RSS must therefore be captured around the whole command, for example:

```bash
/usr/bin/time -v /tmp/tafuzz-sa-build/tafuzz-sa baseline \
  --method memoryssa-aa \
  --input /tmp/rift-m3-input/analyzer_input.json \
  --output /tmp/memoryssa-aa-result.json
```
