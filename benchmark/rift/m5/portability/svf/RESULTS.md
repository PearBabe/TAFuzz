# SVF 3.2 portability-probe result

## Outcome

Status: **SINGLE_TU_SCHEMA2_UNION_SEALED_FULL_111_TU_TIME_GATE_PENDING**.

The current schema-2/union-witness snapshot successfully analyzed the frozen
SVF AE translation unit and emitted a detached-verifiable certificate.  The
unchanged generic POSIX model pack was used; no SVF-specific model or source
patch was added.  Certificate replay over the exact emitted bytes passed
62/62 checks and rehashed 665 physical files.

The full-project portability gate is not yet passed.  A preceding traversal
snapshot removed the former 12 GiB synthetic-owner explosion, but its bounded
111-TU `index` run timed out at 600 seconds without an output artifact.  The
schema-2 snapshot has intentionally not been rerun on all 111 TUs pending
throughput work.  Therefore this result seals the real-project **single-TU
pipeline**, not full SVF portability and not a three-project portability
claim.

The probe has no human gold labels and no runtime fuzz execution.  Its two
recipes remain `UNKNOWN`; no binding-accuracy, mutation-direction, AP-flip, or
fuzzing-gain claim follows from this result.

## Frozen source, inputs, and current analyzer

- SVF 3.2 commit: `197a6590bd9c695a9c3daf52622dea912ef9a002`
- SVF tree: `dab507aca71987a0988ac9deef45b6da9e14e4b2` (clean)
- compile database: 111 unique Clang++ 18 translation units
- single-TU database: exact one-entry projection; compile command unchanged
- property label: `PORTABILITY_PROBE_NOT_REQUIREMENT`
- current snapshot: `13ad31bea45259236199462613066d5c15e0d34ee821bfb10527d00543fb4e6b`
- production core: `c61e38afb3408767a01916f6100091f670ec64cd0fb997677aa36ebc6d14dd8b`
- schema bundle: `84c56cc3bb808024d6ad691668ac00d7d03793d69c9a8027faa428b8ba4f59e7`
- build manifest: `ed674c9c8ec3279f2d1f875672235901a473982b5dd6e2495fac7a88e8c75999`
- M5 certificate: `04d59472c06de0847262bcfec440d36cad5278a8be19f5e66010c277e8aa9194`
- model pack: `src/StaticAnalysis/model_packs/platform/posix_lp64_v1.json`

The binary was supplied as a digest-named immutable snapshot.  Its embedded
core/schema/manifest identities are read from the certificate emitted by
those exact bytes, never inferred from a concurrently changing live path.

## Exact AST target evidence

Clang 18 AST replay completed in 4.36 seconds at 599,512 KiB peak RSS and
confirmed the following source facts in `svf-llvm/tools/AE/ae.cpp`:

| AST fact | Exact range | Clang type |
|---|---:|---|
| `arg_num < argc` | 848:12-25 | `bool` |
| guard `arg_num` | 848:12-18 | `int` |
| guard `argc` | 848:22-25 | `int` |
| copy assignment | 850:9-42 | `char *` lvalue |
| LHS `arg_value` | 850:9-17 | `char **` |
| LHS index `arg_num` | 850:19-25 | `int` |
| RHS `argv` | 850:30-33 | `char **` |
| RHS index `arg_num` | 850:35-41 | `int` |

These selectors come from typed source evidence, not symbol-name similarity.

## Validation history

Each row is tied to an immutable binary identity; results are not transferred
between snapshots.

| Snapshot/run | Exit | Wall | Peak RSS | Result |
|---|---:|---:|---:|---|
| `97caa794` before-fix, AE `bind` | 1 | 7.76 s | 655,912 KiB | 6,619 empty-caller diagnostics |
| `97caa794` before-fix, 111-TU `index` | 1 | 396.69 s | 1,048,192 KiB | 32,625 empty-caller diagnostics |
| `bc926729` owner fix, AE `recipes` | 0 | 27.64 s | 1,222,184 KiB | pipeline PASS, 2 UNKNOWN recipes |
| `bc926729` owner fix, 111-TU `index` | 1 | 559.87 s | 11,747,472 KiB | `std::bad_alloc`, no artifact |
| `dbef650a` generic traversal, AE `index` | 0 | 14.51 s | 1,366,948 KiB | fallback owner explosion removed |
| `dbef650a` generic traversal, AE `recipes` | 0 | 32.78 s | 1,365,660 KiB | pipeline PASS |
| `dbef650a` generic traversal, 111-TU `index` | 124 | 614.49 s | 1,679,452 KiB | 600 s timeout, no artifact |
| `f4b6f21b` union diagnostic, AE `recipes` | 0 | 32.56 s | 1,365,964 KiB | union shape/performance diagnostic |
| `13ad31be` schema-2 union, AE `recipes` | 0 | 31.87 s | 1,366,464 KiB | pipeline PASS |
| `13ad31be` detached certificate replay | 0 | 26.26 s | 788,832 KiB | 62 checks, 0 failures |

The `dbef650a` full run had empty stdout/stderr and no artifact.  Its timeout
result proves neither structural full-project closure nor failure of a
specific TU.  It does establish that the earlier memory-failure trajectory is
gone: peak RSS fell from 11,747,472 to 1,679,452 KiB, while the remaining
registered-budget blocker became throughput.

## Current single-TU semantic result

The `13ad31be` run emitted a `CONSERVATIVE_INCOMPLETE` result:

- semantic index: 22,989 entities, 3,432 function summaries, 7,430
  callsites, 22,417 nodes, 10,819 relations, and 7,288 explicit gaps;
- contextual graph: 38,603 nodes and 46,424 edges;
- two conservative-incomplete cones;
- six predicate occurrences: four `EXACT`, two `UNKNOWN`;
- four frontier candidates: two internal `ACTIONABLE` projections for the
  copy AP and two `PENDING` projections for the guard AP;
- two union witnesses containing five individually accounted meets;
- two recipes and two replay obligations, all `UNKNOWN`;
- solver accounting: zero Z3 queries, zero timeouts, two unsupported local
  truth-change encodings.

`ACTIONABLE` is a static model/executor-frontier disposition.  It is not an
observed AP change.  Both recipes retain `UNKNOWN_DIRECTION`, no suggested
values, and the explicit reason that exact predicate-occurrence accounts do
not have a compatible value path.

## Generic traversal and owner diagnosis

The initial owner fix assigned 6,619 formerly ownerless calls to 5,137
`translation-unit-nonfunction` owners in the AE TU.  Because those identities
contained the TU ID and widely included header locations, a naive 111x density
projection reached 570,207 owners and 7.55 GB of semantic-index JSON before
in-memory overhead.  This was evidence consistent with, but not by itself
proof of, the later 12 GiB allocation failure.

The generic `FunctionDecl` traversal snapshot changed the same AE TU to:

| Nonfunction phase fact | Before traversal fix | After traversal fix |
|---|---:|---:|
| fallback owners/summaries | 5,137 | 12 |
| fallback-owned callsites | 6,619 | 18 |
| fallback-owned nodes | 12,757 | 21 |

The AE TU contains no classifiable real global-initializer call, so its real
global-initializer owner/callsite/node counts are all zero.  The remaining 12
fallback owners occur only in `Util/iterator.h`, `Graphs/GenericGraph.h`, and
`Util/SVFUtil.h`.  Empty `caller_function_id` count is zero.  These results,
together with the 1.68 GiB full-run peak, support the conclusion that generic
method/function traversal removed the header-amplified fallback-owner bug.

## Union-witness audit

The union design was checked both in source and mechanically against the
pre-union AE artifact:

- one witness is emitted per attachment/boundary/cone group;
- `meets[]` keeps each meet's compatibility, reachability, and uncertainty;
- forward nodes/edges, cone edges, and model facts are set unions;
- recipe truth-change analysis iterates each compatible meet independently;
- deterministic sorting binds the meet and edge ledger into witness identity.

For the two reached groups, group keys were unchanged, all five meet IDs were
preserved, and the forward-node, forward-edge, cone-edge, and model-fact unions
were exactly equal.  Witnesses fell from five to two; repeated forward-node
references fell from nine to five and forward-edge references from ten to
seven.

This does **not** establish an end-to-end performance improvement.  The
frontier artifact shrank only 1,554 bytes (0.013%), wall time changed from
32.78 to 32.56 seconds, and RSS was effectively unchanged.  Compact JSON
accounting shows why: the repeated `unsupported_constructs` ledger occupies
11,998,527 of 12,012,764 bytes (99.881%); witnesses occupy only 3,293 bytes
(0.027%) in this probe.

## Occurrence closure and certificate seal

The `arg_value` occurrence is deliberately conservative:

- resolution/certainty: `UNKNOWN` / `unknown`;
- Clang occurrence type: `char **`;
- candidate ledger: one matching declaration node (`char **`) and four
  array-subscript memory nodes (`char *`);
- reasons: M4 node ambiguity, occurrence type mismatch, and a non-exact
  selector account.

The detached verifier contract now distinguishes candidate ledgers from exact
claims: an `UNKNOWN` occurrence must retain at least one type-compatible
candidate, while every node of an `EXACT` occurrence must match.  The same
unchanged `13ad31be` artifact first exposed that contract mismatch, then passed
62/62 checks after the verifier rule was corrected and independently tested.
Both pre-fix FAIL and post-fix PASS reports are retained.

## Claim boundary

- Supported: the generic pipeline and schema-2 union format consume one real
  SVF C++ TU, emit conservative artifacts, and pass detached certificate
  replay using a project-neutral model pack.
- Supported: generic function/method traversal removes the observed fallback
  owner explosion and the prior full-run 12 GiB memory trajectory.
- Not supported: the full 111-TU index has not passed the 600-second gate and
  has no structural output/certificate.
- Not supported: gold binding accuracy, influence precision/recall, recipe
  direction correctness, AP flips, fuzzing gain, or runtime usefulness.
- Next retest: after throughput optimization, rerun the frozen 111-TU index
  and only then attempt a full-project certificate-bearing stage.
