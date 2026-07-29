# AST weak baselines

This directory implements three intentionally limited, project-neutral Clang
AST baselines behind `rift/baselines/ast/ast_baselines.h`:

- `AdgAssignment`: semantic assignment and initializer reachability, flattened
  by symbol name within one function.
- `MoonShineRw`: record-field `W(producer) ∩ R_cond(consumer)` with transitive
  direct-call summaries and a same-caller producer-before-consumer filter.
- `PlainPdg`: an ordinary AST PDG approximation with data, lexical control,
  direct call/return, field, and shallow flow-insensitive alias edges.

They do not read benchmark labels or infer anchors from property metadata.
Every analysis receives stable caller-owned source/property anchor IDs plus
exact symbol locations. A missing anchor or a relation outside the method's
declared semantic scope produces `UnknownUnsupported`; it is never silently
reported as `NoInfluence`. Positive graph reachability is always `MayInfluence`.

## Compile argument contract

`CaseInput::compile_arguments` is passed directly to
`clang::tooling::buildASTFromCodeWithArgs`. It therefore contains flags only,
such as `-std=c++20`, `-I...`, and `-D...`. Do not include the compiler
executable, `-c`, `-o`, output paths, or the input source path. A future
compilation-database adapter is responsible for normalizing full commands.

## Clang 18 smoke verification

Prerequisites are Clang/LLVM 18 C++ headers, Clang Tooling headers (normally
from `libclang-18-dev`), `libclang-cpp.so.18`, and `libLLVM-18`. The following
shape builds the library objects and each independent fixture; set
`CLANG18_INCLUDE` to the directory containing both `clang/` and `llvm/` when
the distribution splits development headers:

```sh
clang++-18 -std=c++20 -O0 -g -Wall -Wextra -Werror \
  -I /home/lqq/project/TAFuzz/src/StaticAnalysis/include \
  -isystem "$CLANG18_INCLUDE" \
  -isystem /usr/include/llvm-18 \
  -isystem /usr/include/llvm-c-18 \
  /home/lqq/project/TAFuzz/src/StaticAnalysis/core/baselines/ast/ast_baselines.cpp \
  /home/lqq/project/TAFuzz/src/StaticAnalysis/core/baselines/ast/moonshine_rw.cpp \
  /home/lqq/project/TAFuzz/src/StaticAnalysis/core/baselines/ast/plain_pdg.cpp \
  /home/lqq/project/TAFuzz/src/StaticAnalysis/core/baselines/ast/assignment_smoke.cpp \
  /usr/lib/llvm-18/lib/libclang-cpp.so.18.1 -lLLVM-18 \
  -o /tmp/rift-assignment-smoke
```

Replace the final smoke source/output pair with `moonshine_smoke.cpp` and
`/tmp/rift-moonshine-smoke`, then `plain_pdg_smoke.cpp` and
`/tmp/rift-plain-pdg-smoke`. Expected results are:

```text
PASS assignment semantic-init graph
PASS MoonShine W-intersect-Rcond with call closure
PASS plain PDG data/control/call/return/field/alias
```

The fixtures are in-memory neutral programs and do not use RIFT gold labels.
They test method semantics and evidence-path shape, including resolved
negatives and explicit unknowns at capability boundaries.
