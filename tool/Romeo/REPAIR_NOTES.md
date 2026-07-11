# Roméo 3.10.12 backward-cost repair

## Scope

This tree is the official Roméo 3.10.12 source archive plus a local repair of
the zone-based backward minimum-cost implementation associated with Parrot and
Lime, *Backward Symbolic Optimal Reachability in Weighted Timed Automata*
(FORMATS 2020).  It also includes fixes for memory-safety faults exercised by
the forward oracle used to compare forward and backward results.

This is not the unpublished source revision used to produce the 2020 paper's
tables, and it is not a claim that every unrelated Roméo property engine has
been audited.

## Main corrections

- Route `check[zones] mincost` to `BVZone`; keep priced control on `BCVZone`
  and ordinary zone properties on `VZone`.  The active path no longer relies
  on invalid downcasts.
- Treat an initial state satisfying the goal as minimum cost zero.
- Seed goals additively even when exploration converges on an existing graph
  node, propagate the complete winning value, and reschedule affected
  predecessors.
- Disable reverse inclusion for priced graph nodes.  The old merge discarded
  pending reachability deltas or game caches, so this optimization was not
  semantics-preserving for either priced mode.
- Repair the affine CostDBM predecessor calculation:
  - retain the zero-delay component when the target slope dominates the
    location rate;
  - preserve strict rectangular and diagonal constraints while constructing
    facet pieces;
  - remove a spurious strict epsilon from affine cost evaluation;
  - correct equal-slope offsets and assignment/cache/dimension invariants.
- Use checked arithmetic at the expression-to-DBM boundary and reject costs
  outside the finite DBM representation instead of narrowing or wrapping.
- Poll `SIGINT` in the forward/backward fixed-point loops and return an
  inexact/unknown result after interruption.
- Initialize copied BVZone heuristic rates and repair BCVZone winning-set and
  cache invalidation paths.
- Replace unsafe state hashing loads and the `CVSClassSp` undersized
  projection array found by ASan/UBSan.
- Give the priced backward graph an explicit owner: dynamic BV/BCV payloads,
  states, result wrappers, and pairing-heap nodes are released without
  confusing the two incompatible `WSET_CDBM` edge layouts.

## Tests

From `romeo-cli/`, with PPL/GMP include and library paths configured:

```sh
make check
make check-sanitize
```

`make check` runs focused CostDBM tests plus CLI tests for forward/backward
agreement, initial goals, zero and negative costs, checked overflow, verbose
dispatch, and interrupting a zero-time negative cycle.  The sanitizer target
uses ASan and UBSan with LeakSanitizer disabled because the 3.10.12 parser/CTS
AST is retained for process lifetime; leak auditing is a
separate concern from the memory-safety target.

The repaired optimized binary was also run on the fixed FORMATS 2020 quick
suite archive (SHA-256 `6045841f...d9a29`).  It produced matching
forward/backward values for all four quick oracles:

| Model | Forward | Backward |
| --- | ---: | ---: |
| `aircraft3` | -1140 | -1140 |
| `aircraft4` | -4140 | -4140 |
| `scheduling2` | -1760 | -1760 |
| `scheduling3` | -2560 | -2560 |

Roméo 3.10.12 prints these as bare numeric lines, unlike the archived binary's
`= value` format.  An older artifact-output parser that accepts only the latter
will report missing costs even though the numeric results above are present.

A focused LeakSanitizer comparison reduced the backward-only model from
2600 bytes in 46 allocations to the parser/CTS baseline of 768 bytes in 18
allocations.  The remaining report contains no `GraphNode`, `BVZone`,
`BCVZone`, `PairingHeap`, `ControlResult`, or `CostDBMUnion` allocation stack.

## Remaining mathematical boundary

The signed-cost option does not contain a symbolic negative-cycle certificate
procedure.  Roméo now warns that the model is assumed to have a lower-bounded
optimal value, and a non-terminating fixed point can be interrupted safely,
but a user must not interpret a partial interrupted value as an exact optimum.
The optimal-control `BCVZone` engine is a related timed-game algorithm and is
not Algorithm 1 of the FORMATS 2020 paper.
