# SVF 3.2 independent RIFT-M5 portability probe

Status: **PORTABILITY_PROBE_NOT_REQUIREMENT**.

This directory tests whether the unchanged RIFT binary, schema bundle, core,
Clang 18 indexing pipeline, and generic POSIX LP64 model pack can analyze a
real translation unit from the frozen SVF 3.2 source tree.  It is not a
software requirement, a gold-accuracy benchmark, or a claim about SVF's
runtime behavior.

The probe targets two real AST fragments in
`svf-llvm/tools/AE/ae.cpp`:

- the loop predicate `arg_num < argc` at line 848;
- the argv copy assignment `arg_value[arg_num] = argv[arg_num]` at line 850.

`property_ir.json` is deliberately labeled as a probe.  Exact ranges and
canonical types are derived by `derive_ast_evidence.py` from the frozen
compile-database entry and Clang 18 AST, not from symbol-name guesses.  The
second AP exercises pointer/index/assignment preservation; a total-analysis
result may correctly retain it as `UNKNOWN_DIRECTION` rather than inventing a
mutation direction.

Only the existing project-neutral model pack
`src/StaticAnalysis/model_packs/platform/posix_lp64_v1.json` is supplied.
`executor_capabilities.json` independently states that a process runner can
choose `argc` and `argv`; it is not a model pack and contains no SVF symbol or
answer edge.

The probe never edits the SVF checkout or build tree.  `result_manifest.json`
records the frozen commit, hashes, exact commands, exit codes, resource use,
semantic counts, and limitations.  Analyzer bulk outputs are written outside
the source tree and are referenced by hash to avoid treating generated graphs
as source files.
