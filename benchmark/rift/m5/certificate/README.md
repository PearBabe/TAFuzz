# RIFT-M5 detached certificate contract

`m5_analysis_certificate.json` is a physical-provenance sidecar over an
immutable M4 `analysis_certificate.json`.  It is intentionally separate from
the six semantic M5 outputs: the certificate describes their exact bytes but
does not put its own digest into its stage graph.

The normative schema is:

```text
src/StaticAnalysis/schema/m5_analysis_certificate.schema.json
```

The independent verifier is:

```bash
python3 src/StaticAnalysis/tests/verify_m5_certificate.py \
  /absolute/path/to/analysis-directory
```

It exits zero only after it has:

1. validated the closed M5 schema and all referenced production schemas;
2. rehashed every absolute physical path available from the M5 and M4
   certificates, including M4 source provenance;
3. required the five M4 commitments to exactly equal the descriptors in the
   physically rehashed M4 certificate;
4. bound both the raw bytes and canonical semantic digest of every model pack;
5. schema-validated the additive predicate-occurrence sidecar and required its
   property, index, canonical compilation-database and path-map identities to
   equal the physically rehashed immutable M4 inputs;
6. bound an optional, independent executor capability manifest;
7. rehashed the analyzer and Z3 runtime component and cross-checked the actual
   solver version used by `mutation_recipes.json`;
8. independently recomputed the solver-budget digest from Z3 identity,
   encoding version, per-query timeout, and maximum query count;
9. reconstructed both fixed stage DAGs and checked artifact-internal links
   against independently observed file hashes; and
10. reconstructed the typed model overlay identities: boundary
    `value_transfer`, clock/value model facts, joint-action groups and
    constraints, canonical ledger order, and the overlay artifact ID;
11. reconstructed recipe IDs, single/joint hyperedge IDs, closed source-AND
    and typed `ALL_REQUIRED` requirements, mutation-ledger membership,
    prerequisite DAGs, and witness-bound `EXACT` timing fields; and
12. checked the complete candidate ledger, exact ACTIONABLE→recipe→replay
    accounting, and UNKNOWN mutation recipes so unsupported solver results
    cannot disappear.

## Fixed M5 topology

Array order is part of the contract. `P` is the ordered model-pack record list
and `E` is present only when an executor manifest was supplied.

```text
model:
  [M4.index, P[*].raw_sha] -> [model_fact_overlay]

occurrence:
  [M4.property, M4.index] -> [predicate_occurrence_bindings]

contextualize:
  [overlay, M4.graph, M4.cones, E?] -> [frontier_candidates]

frontier:
  [frontier_candidates] -> [fuzzable_frontier]

recipe:
  [M4.property, M4.bindings, M4.graph, M4.cones,
   frontier_candidates, overlay, predicate_occurrence_bindings,
   core, Z3 component, solver budget]
    -> [mutation_recipes, replay_obligations]

certificate:
  [M4 certificate + five M4 commitments,
   each P raw+semantic digest, E?, configuration + build identities,
   all runtime components, all six M5 outputs] -> []
```

The occurrence sidecar is additive: it consumes M4 property/index bytes but
does not replace, rewrite, or add an output to the M4 certificate. Its four
identity fields must equal:

```text
property_ir_sha256                       = physical M4 Property IR SHA
semantic_index_sha256                    = physical M4 Semantic Index SHA
canonical_compilation_database_sha256    = value in that M4 Semantic Index
path_map_sha256                          = value in that M4 Semantic Index
```

`m4_index_immutable` must be true. The top-level M5 status and certificate
stage conservatively aggregate the five semantic stages `model`, `occurrence`,
`contextualize`, `frontier`, and `recipe`.

## Producer and runner integration contract

The CLI must publish descriptors in this exact order:

```text
model_fact_overlay
predicate_occurrence_bindings
frontier_candidates
fuzzable_frontier
mutation_recipes
recipe_replay_obligations
```

It must publish stages in the exact topology above. In particular,
`stage.occurrence` consumes only the physical M4 Property IR and Semantic Index
SHA values. `stage.recipe` places the occurrence sidecar SHA after the overlay
SHA and before the analyzer-core, Z3-component, and solver-budget SHA values.
`mutation_recipes.predicate_occurrence_bindings_sha256` must equal the physical
sidecar descriptor SHA. The certificate-stage input list must include all six
M5 output digests in descriptor order.

The benchmark runner must require and archive
`predicate_occurrence_bindings.json` immediately after
`model_fact_overlay.json` in its artifact inventory. It must hash the file as
produced, invoke the detached verifier over the completed directory, and seal
the run manifest only when the verifier exits zero and reports `PASS`; the
runner must not synthesize, normalize, or rewrite the sidecar.

The certificate stage has no output digest because including the certificate's
own digest would be recursive.  Instead, `certificate_id` is:

```text
m5-certificate:SHA256(canonical-json(certificate without
                                     certificate_id/started_at/finished_at))
```

Canonical JSON means UTF-8, recursively sorted object keys, no insignificant
whitespace, and no NaN/Infinity. Timestamps are excluded only so replayed runs
with identical semantic and physical commitments retain the same identity.

`solver.budget_sha256` is SHA-256 over six ordered UTF-8 tokens:

```text
rift-m5-solver-budget/1.0.0
solver name
actual solver version
rift-local-truth-change/1.0.0
decimal timeout_ms
decimal max_queries
```

Each token is preceded by its unsigned 64-bit big-endian byte length. The
detached verifier recomputes this digest, checks it against the recipe solver
contract, and requires it as the final recipe-stage input after the Z3
component digest.

## Regression gate

```bash
python3 src/StaticAnalysis/tests/verify_m5_certificate.py --self-test
```

The self-test creates neutral temporary certificates with and without an
executor manifest and requires both to pass. It then requires closed-schema,
stage-order, M4-commitment, solver-component, artifact-kind, model/executor
metadata, runtime identity, UNKNOWN-invariant, timeout-status, duplicate-key,
solver-accounting, solver-budget, semantic-pack-digest and physical-byte
tamper cases to fail. Predicate-occurrence tests additionally reject sidecar
schema extensions, physical-byte changes, M4-link changes, output reordering,
and stage reordering. Focused cases cover every direction-query outcome.
Production use never disables validation of the referenced semantic artifact
schemas.

The truth-change query and direction query have deliberately different
meanings. A truth-change `SAT` pair is required for a `SUPPORTED` or
`HEURISTIC` recipe. The direction query asks for an opposite-direction
counterexample: only `UNSAT` proves `MONOTONE_UP` or `MONOTONE_DOWN`; `SAT`,
`UNKNOWN`, `TIMEOUT`, `UNSUPPORTED`, and `NOT_RUN` leave direction unproved
without invalidating an otherwise supported truth-changing recipe. A direction
query is invalid unless its truth-change premise is `SAT`.

This certificate proves byte identity and contract closure. It does not turn a
MODELLED or UNKNOWN semantic result into MUST, prove a model pack complete, or
substitute for replay evidence.

Both the raw pack digest and `model-pack-semantic/2.0.0` digest are
independently recomputed by this Python verifier. The semantic implementation
reproduces the frozen C++ byte contract exactly, including its current
NUL-prefixed-label behavior; positive and semantic-tamper regressions make
canonicalizer drift fail closed. The recomputed digest is then cross-checked
against the certificate, overlay, and every model provenance record.

The semantic digest replay includes the complete typed materials for
`clock_relation`, `joint_action_relation`, and `value_transfer`. In
particular, it mirrors the current LLVM 18 `formatv("{0}", double)` contract
used by the C++ clock material (fixed two decimal places). Changing any typed
field therefore changes the semantic pack digest even when legacy
`transfer_relation` text is unchanged.

## Typed fail-closed semantics

The verifier deliberately enforces the producer's canonical output contract
in addition to the JSON schemas. A production overlay must contain
`joint_action_constraints`; every attachment must contain `value_transfer`
(object or null), and every model fact must contain both `clock_relation` and
`value_transfer` (object or null). This closes schema-optional fields that the
C++ canonical writer always emits.

For the overlay, the verifier independently reconstructs:

```text
boundary-attachment ID = H(action, semantic node, legacy relation,
                           typed value-transfer material)
model-fact ID          = H(kind, source, target, legacy relation,
                           typed clock material, typed value material)
joint group ID         = H(pack semantic SHA, rule, group schema,
                           sorted participant semantic nodes)
joint constraint ID    = H(group instance, AND/OR/UNKNOWN,
                           participant completeness, scope, generation)
model-overlay ID       = H(index identity, status, sorted child IDs/certainty,
                           UNKNOWN/resource ledger state)
```

For recipes, `JOINT_REQUIRED` is accepted only when the physical artifacts
close one of two derivations:

- an explicit source predicate AND whose complete selector set maps one-to-one
  to typed identity boundary witnesses with common scope/generation; or
- a MODELLED, participant-complete `all_required` model constraint whose
  participant nodes are exactly covered by compatible candidate witnesses.

All recipes sharing such a hyperedge must carry the same ordered action set
and the same SAT multi-input query digest. The verifier independently
recomputes closed source ANDs, so coherently rewriting every member recipe as
single-action recipes and resealing downstream SHA values still fails.
`any_sufficient` is never interpreted as AND. Incomplete evidence may remain
`JOINT_UNKNOWN`, but it cannot be exposed as a supported joint flip.

Prerequisite choices are reconstructed from witness-bound event, timer,
queue, lifecycle and persistence facts. A control-path-derived before edge is
accepted only as `PARTIAL_ORDER_UNKNOWN`; static control dependence cannot
close external-action ordering or persistence. `EXACT` timing requires one
MODELLED clock fact on a compatible candidate path, with matching endpoints,
scope, generation, clock fields, and canonical timing projection.

Current self-test coverage is 115 deterministic cases, including coherent
tampering of typed pack semantics, clock facts, value transfers, joint
constraints, canonical overlay order, automatic joint splitting, shared SMT
query identity, control-prerequisite status, and exact timing.

## Explicit limits

- An external-action ID contains a callsite-versus-node instance choice that
  is not fully serialized in `model_fact_overlay.json`. The verifier therefore
  treats that ID as an opaque content-addressed root and reconstructs every
  typed child identity below it.
- Manual in-memory `RecipeOptions.joint_action_requirements` are not serialized
  by the production certificate. The detached verifier can validate automatic
  source/model requirements only; an otherwise unexplained joint hyperedge
  fails closed.
- Exact timing is checked against its unique typed clock witness and action
  context. The verifier does not independently recompile the complete MITL
  monitor or re-prove temporal-interval uniqueness.
- Typed boundary identity is necessary for a concrete external value mutation,
  but the verifier does not rerun Clang/LLVM value-flow construction. It relies
  on the separately reconstructed frontier path ledger and never upgrades a
  generic `data` edge to identity.
