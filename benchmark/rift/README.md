# RIFT benchmark and portability contract

RIFT (Residual-Conditioned Influence Frontier for Temporal-Property Fuzzing)
maps typed MITL atomic propositions to conservative source-level influence
cones, externally controllable frontiers, and actionable mutation recipes.

## Benchmark-first gate

No RIFT algorithm implementation may be added under `src/StaticAnalysis`
until all of the following are recorded:

1. an original, high-quality published artifact executes successfully, or its
   failure is preserved and another original artifact passes;
2. the frozen libcoap checkout builds reproducibly with Clang/LLVM 18 and
   produces stable whole-program bitcode;
3. the ADGFuzz, PGFuzz, MoonShine, LTL-Fuzzer, plain LLVM/MemorySSA, SVF, and
   FGS comparison status is explicit, including unavailable source or images;
4. pre-implementation hypotheses and falsification thresholds are frozen.

An unavailable artifact is never replaced silently by a reimplementation.  A
faithful reimplementation may be evaluated, but its provenance must say so.

## Portability contract

The core analyzer accepts only versioned, project-neutral interfaces:

- typed property IR;
- a Clang compilation database;
- LLVM modules plus source/debug identities;
- external-source and lifecycle model packs;
- optional monitor residual information.

The core must not contain project names, repository-relative source paths,
MAVLink message names, ArduPilot parameter names, libcoap field names, or
project-specific call patterns.  Those belong in separately versioned model
packs and property inputs.

A model pack describes generic facts such as external input boundaries,
parameter registries, parser outputs, callback registration, timer lifecycle,
queue lifecycle, scheduler entry points, scope keys, and persistence.  It may
not contain per-property slices or hand-selected dependency paths.

Portability passes only if one analyzer binary and one output schema run on at
least three independent C/C++ projects without a core source change.  Per
project effort is reported as model lines, source-boundary rules, setup time,
unsupported constructs, and analysis outcomes.  A core patch needed only to
recognize one target is a portability failure and must first be generalized
and regression-tested on the earlier targets.

The frozen, machine-checkable version of this contract is
`portability_contract.json`.  Before implementation it is validated with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/validate_portability_contract.py --phase pre-core
```

The implementation phase additionally scans generic C/C++ core roots for
target literals.  The evaluation phase accepts only the sealed,
artifact-backed evidence format `3.0.0`; an old report containing three
handwritten `PASS` strings is not evidence.  The format is described by
`portability_tests/portability_evidence.schema.json` and each project record
points to a separately hashed `rift.sealed-portability-run/3.0.0` manifest.

For every sealed run the validator reopens and hashes, rather than trusting
reported values for:

- the executed analyzer and its complete runtime/build toolchain;
- the generated build manifest and every production-core file named by it;
- distinct pre-run and post-run core snapshots, plus the current actual core;
- the complete eight-file output-schema bundle;
- the repository source snapshot and a separately hashed repository identity;
- the Property IR, compilation database and versioned model pack;
- a source-input closure v2 whose physical file hashes reconstruct the
  semantic index's `input_manifest_sha256`;
- the semantic index, AP bindings, contextual influence graph, influence
  cones and analysis certificate.

The gate then checks the certificate's complete input/output/stage hash chain,
embedded build-manifest/core/schema identities, source-input provenance,
successful exit status, and `COMPLETE` or `CONSERVATIVE_INCOMPLETE` analysis
status.  `PASS`, `UNSUPPORTED`, `FAILED`, `NOT_RUN`, certificate v1, empty
placeholder outputs, a single schema file presented as a schema bundle, and
property-specific answer rules in a model pack are rejected.

Three records count as independent projects only when repository identities,
source-tree digests and compilation-database digests are all pairwise
different.  Conversely, the actual analyzer binary, generated build manifest,
production-core digest, complete schema-bundle digest and toolchain-semantics
digest must all be identical.  Project-specific model packs and examples stay
outside generic roots and are scanned for per-property answer leakage.

Run the adversarial synthetic gate tests with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/portability_tests/test_evaluation_gate.py -v
```

These synthetic fixtures verify the gate itself; they are deliberately not a
claim that RIFT has passed the final three-real-project portability evaluation.

## Result layers

Every subject uses the same three result layers:

1. a conservative AP influence cone;
2. a fuzzable influence frontier with controllability evidence;
3. ranked mutation recipes with prerequisites, direction, timing, scope, and
   confidence.

Ranking may never delete candidates from the conservative cone.  Missing
alias, framework, scope, or timing semantics must expand the result or produce
an explicit incomplete status.
