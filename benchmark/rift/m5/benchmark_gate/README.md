# RIFT-M5 benchmark-first gate

This gate is deliberately separate from the RIFT implementation.  It freezes
the upstream inputs used to challenge M5 path and C/C++ expression semantics
before the frontier/recipe engine is compiled.

Inputs:

- `CFPOFuzz` official ICSE 2026 artifact repository, commit
  `62ee6abf14e0698af15743676ea56ee4db845d0c`;
- `sv-benchmarks` official `svcomp26` tag, peeled commit
  `7efe28dd29576b46927b7a34e8f742bd90966a75`;
- the already frozen M2 120-case mechanical corpus and M4 results.

The runner performs three different checks and keeps them distinct:

1. nine deterministic bit-vector programs are compiled and executed, with
   `reach_error` outcomes compared to the official YAML verdicts;
2. sixteen signed-overflow programs are compiled from the exact `.i` input
   named by the official YAML and executed with Clang 18 UBSan;
3. ten infeasible-control-flow programs are compiled to LLVM IR and their
   official reachability verdicts are imported as challenge labels.  A normal
   compiler run is not a proof of those unbounded tasks, so the runner never
   reports them as dynamically reproduced.

CFPOFuzz's demo is attempted only through its documented Docker prerequisite.
If Docker is unavailable, the result is `BLOCKED_ENVIRONMENT`, not `PASS`.

Run:

```bash
python3 benchmark/rift/m5/benchmark_gate/run_gate.py \
  --output benchmark/rift/m5/results/benchmark_gate.json
```

The output records commands, exit codes, tool versions, upstream commits,
input SHA-256 values, and the exact boundary of every conclusion.
