# LTL-Fuzzer portability-probe result

## Outcome

Status: **FULL_13_TU_DETACHED_PASS**.

The final immutable RIFT analyzer consumes all 13 real LTL-Fuzzer translation
units with the generic POSIX LP64 model.  No LTL-Fuzzer-specific model fact,
core branch, source patch, or answer edge was introduced.  The full core
pipeline, probe-specific semantic verifier, and independent detached
certificate reconstruction all pass.

## Sealed identities

| Item | SHA-256 |
|---|---|
| Analyzer binary | `75cc7f4d74d8507dacd4e2919393406d15e867d8422efec2519c89a344327f0a` |
| Production core | `be454d86de57170968a9758ab349620685e2b69ef4f467c05e3df6026c41a6d8` |
| Schema bundle | `4e170722f4b981faf54c7bc561cd6ac710856808d95c0c5c4f0549f53c15f9aa` |
| POSIX LP64 pack bytes | `c532d54ab0e3e2cb62d82393164aa5497be8e6a39cc9c1e60c516a8a39266da0` |
| Property IR | `d83010d052b58a3950b7da0e618b7050109ff7ff48c381641f3ef809a6a9f8fe` |
| Executor manifest | `6606cdb79d0102a4c96fe1cf57ec230a3bde1323f00fe05fbd8dd9e1bf38c14e` |
| Full 13-TU compile database | `acee244a4817ab8a29d907372c07f4a0502dfbfca666857ce7043f5337bd9b04` |
| Single-main TU projection | `b555404ed35a28fd8a6378db1b99ea2fe340ec8fb5b3dcc5b74e854646ba2fa2` |

Frozen source identity is commit
`716ac301fa3a8ea39814bc80eeebba49c19c1378`, tree
`ee7f4a651abf3e7f6104be92751e4880385ead85`.  Tracked files are clean;
pre-existing untracked build products are intentionally ignored and preserved.

## Full 13-TU result

The full frozen project run completed with exit 0 in 20.64 seconds at 370,892
KiB peak RSS:

| Artifact fact | Observed |
|---|---:|
| Translation units | 13 |
| Semantic entities | 2,969 |
| Function summaries | 201 |
| Callsites | 1,170 |
| Semantic/graph nodes | 2,961 / 4,036 |
| Graph edges | 7,196 |
| Predicate occurrences | 1, `EXACT` |
| Influence cones | 1 |
| External actions / boundary attachments | 12 / 12 |
| Frontier candidates | 12 |
| Actionable projection | 1 (`action.posix.argc`) |
| Recipes / replay obligations | 1 / 1 |

The actionable candidate has one compatible `MODELLED_WITNESS`; its boundary
semantic node is the same exact node selected by the `argc` USR binding.  The
`argv` action is retained but rejected because the executor manifest does not
claim that capability for this predicate probe.

Z3 makes two query decisions: the local truth-change pair is SAT, while the
monotonicity counterexample query is UNSAT.  The final recipe remains
`HEURISTIC` with `mutation_kind=UNKNOWN`, `direction=UNKNOWN`, and no suggested
values because the compatible external-to-selector value path contains the
non-identity relation `process_argument_count`.  This is the intended
soundness boundary: selector-local monotonicity is not projected onto an
external action without an explicit identity transfer.

The local verifier passes 33/33 checks.  The final independent detached
verifier passes 65/65 checks: schema and byte closure, source provenance, model
semantics, occurrence type/USR closure, compact frontier reconstruction over
4,036 nodes and 7,196 graph/model arcs, exact actionable projection, solver
accounting and replay reconstruction.  All 2,161 physical-file rehashes remain
stable.

An intermediate verifier build reported 18 paired differences for nine
rejected environment candidates.  Root cause was verifier-only: it pruned a
zero reverse state while reverse-cone enumeration was incomplete, whereas the
producer requires `enumeration_complete && state == 0`.  Aligning that
condition restores exact evidence and uncertainty-reason reconstruction on the
unchanged analyzer bundle.  The failed report remains historical evidence, not
the final verdict.

## Historical core failure, minimization and resolution

The pre-fix all-13-TU command failed before writing an output bundle:

```text
semantic index validation failed;
semantic node access path references unknown field entity: std::ios_base::end;
semantic node access path references unknown field entity: std::ios_base::beg
```

Observed resource receipt: exit 1, 12.74 seconds, 345,624 KiB peak RSS.  A
one-entry database containing only `src/utils.cc` reproduces the identical
failure in 0.77 seconds at 181,164 KiB.  Clang 18 identifies:

- `utils.cc:82:26-30`, `ifs.end`: `MemberExpr`, `const seekdir` lvalue,
  `non_odr_use_constant`;
- `utils.cc:84:25-29`, `ifs.beg`: the same AST category.

Both names denote static `std::ios_base` constants even though the source uses
member syntax.  The old indexer built field-style access paths and then
required field entities that were correctly absent.  This generic C++ AST
classification/validation bug was fixed in the parent core implementation;
the probe task itself added no core or verifier edits.  The final 13-TU rerun
above demonstrates that the original minimal reproducer no longer blocks the
project.

The earlier 12-TU omission run remains only localization history; the final
result no longer excludes `utils.cc`.

## Supported and unsupported claims

Supported:

- the final unchanged binary/schema/core consumes all 13 genuine C/C++ TUs
  from a third independent project using only a generic model pack;
- exact typed predicate occurrence, external boundary, contextual meet and
  conservative recipe survive both local and detached verification;
- the historical complete-project blocker was reproducible, minimized to a
  specific standard C++ AST construct, fixed generically, and removed on rerun.
- the final full-project bundle passes independent detached reconstruction of
  every candidate ledger and certificate commitment.

Not supported:

- human-gold binding, influence precision or recall;
- external mutation-direction accuracy;
- observed AP flip, replay success, fuzzing gain, or property satisfaction;
- a global three-project portability claim until the parent M5 gate combines
  all targets under one final immutable identity and resolves registered
  blockers.

Both the core full-project and detached certificate gates pass.  Remaining
claims still require separate human gold and runtime experiments; this probe
alone does not establish accuracy or fuzzing effectiveness.
