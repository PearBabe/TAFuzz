# TAFuzz MITL Front-end Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `PearBabe/TAFuzz` 的 `codex/tafuzz-20260712-004642` 分支上，实现可运行的 `RFC → typed MITL property → source dependency → selective instrumentation → TAMonitor trace` 闭环，并保留现有 TAMonitor/PTA 基线。

**Architecture:** Python 工具负责 RFC context graph、类型化性质 IR、符号时间解析和 trace assembly；Clang/LLVM C++ 工具负责代码语义索引、命题绑定、时序依赖图和源码级插桩；C 运行时负责低开销事件记录；现有 TAMonitor 作为不修改语义的监控后端。第一阶段以 RFC 7252 + libcoap + event propositions 为可交付闭环，第二阶段加入 state propositions、异步依赖、共享内存 per-thread ring 和论文实验。

**Tech Stack:** Python 3.11+、JSON Schema 2020-12、lxml、pytest、Clang/LLVM 18.1、C++17、C11、LLVM `json/yaml`、CMake、现有 MightyPPL/MoniTAal/TAMonitor、Clang sanitizers。

## Global Constraints

- 目标分支固定为 `codex/tafuzz-20260712-004642`；开始前记录 HEAD SHA。
- 不修改 `src/TAMonitor/PTA` 中的求解算法；第二阶段只读其 snapshot 输出。
- 未显式启用新前端时，现有 TAMonitor CLI、四个默认报告和 PTA 默认关闭行为不变。
- 任何 LLM 输出都只是 candidate；只有 schema、provenance、bound、formula、source binding 和 instrumentation gate 全部通过后才可执行。
- 任何 event drop、时间倒退、未知 event id、未解析 bound 或不完整 source binding 都强制输出 `INCONCLUSIVE`。
- 第一阶段禁止把合成的“5 秒 ACK”句子当成 RFC 7252 直接规范；真实实验使用 RFC 原文和符号参数。
- 所有源码位置使用 canonical path、USR、line/column 和 source hash；不得只保存行号。
- 所有时间先记录为 `uint64_t nanoseconds`，在 trace assembly 时转换为公式整数 tick。
- 新前端、bitcode 捕获、插桩后目标和论文实验统一使用 `clang-18`/`clang++-18`；启动时验证 major version 为 18，不得回退 GCC。每次构建在 manifest 中记录编译器绝对路径、`--version`、target triple 和完整命令。
- 新功能严格按 RED → GREEN → REFACTOR 实施；每个任务完成后运行本任务测试和 protected baseline。
- 生产代码不得依赖 `prototype/`；原型仅作为接口证据。

---

## Target File Map

```text
schema/
  mitl_property.schema.json
  source_binding.schema.json
  observation_plan.schema.json

tool/MITLFrontend/
  CMakeLists.txt
  README.md
  pyproject.toml
  src/tafuzz_specminer/
    __init__.py
    model.py
    rfc_xml.py
    context_graph.py
    candidate_provider.py
    template_compiler.py
    parameter_resolver.py
    validator.py
    trace_assembler.py
    cli.py
  analyzer/include/tafuzz/
    SemanticIndex.h
    PropertyBinding.h
    TPDG.h
    ObservationPlanner.h
    AsyncModel.h
  analyzer/lib/
    SemanticIndex.cpp
    PropertyBinding.cpp
    TPDG.cpp
    ObservationPlanner.cpp
    AsyncModel.cpp
  analyzer/tools/
    tafuzz-index.cpp
    tafuzz-slice.cpp
    tafuzz-instrument.cpp
  analyzer/passes/
    TemporalSlicePass.cpp
  runtime/include/tafuzz/
    EventRecord.h
    Runtime.h
  runtime/src/
    Runtime.c

scripts/mitl_frontend/
  fetch_rfc.py
  replay_compile_commands.py
  verify_protected_baseline.sh
  run_frontend_pipeline.py

test/MITLFrontend/
  fixtures/rfc/
  fixtures/c/
  fixtures/properties/
  unit/
  integration/
  gold/
  experiments/

docs/mitl_frontend/
  architecture.md
  annotation_guide.md
  artifact_guide.md
```

---

### Task 1: Freeze the Protected Baseline and Add the New Tool Skeleton

**Files:**

- Create: `scripts/mitl_frontend/verify_protected_baseline.sh`
- Create: `tool/MITLFrontend/README.md`
- Create: `tool/MITLFrontend/CMakeLists.txt`
- Create: `tool/MITLFrontend/pyproject.toml`
- Create: `docs/mitl_frontend/architecture.md`

**Interfaces:**

- Consumes: existing `tool/MightyPPL/build/TAMonitor` and PTA test targets.
- Produces: one command that proves the old monitor/PTA behavior is unchanged.

- [ ] **Step 1: Record repository state**

Run:

```bash
git status --short --branch
git rev-parse HEAD
```

Expected: current branch and a 40-character SHA are recorded in the implementation log. Do not reset or discard pre-existing changes.

- [ ] **Step 2: Write the baseline verification script**

Create `scripts/mitl_frontend/verify_protected_baseline.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

build_dir="${1:-tool/MightyPPL/build}"
cmake --build "$build_dir" --target TAMonitorPTATests TAMonitor -j2
ctest --test-dir "$build_dir" -R '^TAMonitorPTA' --output-on-failure

out_dir="$(mktemp -d)"
trap 'rm -rf "$out_dir"' EXIT
"$build_dir/TAMonitor" \
  --formula test/TARV/cases/smoke_f_01.mitl \
  --trace test/TARV/cases/smoke_f_01.trace \
  --word finite --build-mode flatten \
  --out "$out_dir"

test -f "$out_dir/steps.csv"
test -f "$out_dir/summary.csv"
test -f "$out_dir/metadata.json"
test -f "$out_dir/results.xlsx"
test ! -e "$out_dir/pta_analysis.json"
```

- [ ] **Step 3: Run the script before new implementation**

Run:

```bash
bash scripts/mitl_frontend/verify_protected_baseline.sh
```

Expected: all `^TAMonitorPTA` tests pass and the default run creates exactly the original non-PTA artifacts.

- [ ] **Step 4: Add build skeleton**

`tool/MITLFrontend/CMakeLists.txt` must begin with:

```cmake
cmake_minimum_required(VERSION 3.20)
project(TAFuzzMITLFrontend LANGUAGES C CXX)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(LLVM 18 REQUIRED CONFIG)
find_package(Clang 18 REQUIRED CONFIG)
include(CTest)
```

Configure it with the Clang 18 toolchain explicitly:

```bash
CC=clang-18 CXX=clang++-18 cmake \
  -S tool/MITLFrontend -B tool/MITLFrontend/build \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm \
  -DClang_DIR=/usr/lib/llvm-18/lib/cmake/clang
```

The configure step must fail if either compiler is absent or does not report
major version 18. Do not accept a CMake-selected GCC compiler.

Do not link the new tool into TAMonitor in this task.

- [ ] **Step 5: Commit**

```bash
git add scripts/mitl_frontend tool/MITLFrontend docs/mitl_frontend
git commit -m "chore: establish MITL frontend protected baseline"
```

---

### Task 2: Define Versioned Property, Binding, and Observation Schemas

**Files:**

- Create: `schema/mitl_property.schema.json`
- Create: `schema/source_binding.schema.json`
- Create: `schema/observation_plan.schema.json`
- Create: `tool/MITLFrontend/src/tafuzz_specminer/model.py`
- Test: `test/MITLFrontend/unit/test_model_schema.py`
- Fixture: `test/MITLFrontend/fixtures/properties/rfc7252_retransmit_span.json`

**Interfaces:**

- Produces: `PropertySpec.load(path)`, `PropertySpec.validate_executable()` and three JSON contracts used by every later task.

- [ ] **Step 1: Write failing schema tests**

```python
def test_real_property_round_trips():
    spec = PropertySpec.load(FIXTURES / "rfc7252_retransmit_span.json")
    assert spec.property_id == "rfc7252.s4.2.retransmit_span"
    assert spec.bound_symbols["MAX_TRANSMIT_SPAN"].unit == "second"
    assert spec.formula_template == (
        "G (retransmit -> O [0,MAX_TRANSMIT_SPAN] first_con_send)"
    )

def test_direct_requirement_cannot_invent_a_numeric_bound():
    data = valid_property_dict()
    data["derivation_kind"] = "direct"
    data["formula_template"] = "G (con_sent -> F [0,5000] ack_received)"
    data["provenance"] = []
    with pytest.raises(PropertyValidationError, match="numeric bound lacks evidence"):
        PropertySpec.model_validate(data).validate_executable()
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m pytest test/MITLFrontend/unit/test_model_schema.py -v
```

Expected: import or class-not-found failure.

- [ ] **Step 3: Implement immutable models**

`model.py` must define these enums and models with no untyped dictionary fields:

```python
class NormativeStrength(str, Enum):
    MUST = "MUST"
    MUST_NOT = "MUST_NOT"
    SHOULD = "SHOULD"
    SHOULD_NOT = "SHOULD_NOT"
    MAY = "MAY"
    ASSUMPTION = "ASSUMPTION"

class PropositionKind(str, Enum):
    EVENT = "event"
    STATE = "state"
    DERIVED = "derived"

class AtomicProposition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ap_id: str
    kind: PropositionKind
    predicate_ast: dict[str, JsonValue]
    scope_fields: tuple[str, ...]
    required_entities: tuple[str, ...]
    lifecycle: Literal["instant", "persistent", "derived_at_site"]

class PropertySpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["tafuzz-property-ir/1.0"]
    property_id: str
    normative_strength: NormativeStrength
    derivation_kind: Literal["direct", "direct_with_derived_bound", "assumption"]
    scope_key: tuple[str, ...]
    semantics: Literal["event_clock", "state_signal_projection"]
    pattern: str
    formula_template: str
    bound_symbols: dict[str, BoundSymbol]
    atomic_propositions: tuple[AtomicProposition, ...]
    exceptions: tuple[ExceptionClause, ...]
    assumptions: tuple[AssumptionClause, ...]
    provenance: tuple[EvidenceSpan, ...]
```

- [ ] **Step 4: Validate with both Pydantic and JSON Schema**

Run:

```bash
python3 -m pytest test/MITLFrontend/unit/test_model_schema.py -v
python3 -m tafuzz_specminer.cli validate-property \
  test/MITLFrontend/fixtures/properties/rfc7252_retransmit_span.json
```

Expected: tests pass and CLI prints `status=SCHEMA_VALID`.

- [ ] **Step 5: Commit**

```bash
git add schema tool/MITLFrontend/src/tafuzz_specminer/model.py test/MITLFrontend
git commit -m "feat: define auditable MITL property contracts"
```

---

### Task 3: Parse RFC XML and Build the Metric Requirement Context Graph

**Files:**

- Create: `tool/MITLFrontend/src/tafuzz_specminer/rfc_xml.py`
- Create: `tool/MITLFrontend/src/tafuzz_specminer/context_graph.py`
- Create: `scripts/mitl_frontend/fetch_rfc.py`
- Test: `test/MITLFrontend/unit/test_context_graph.py`
- Fixture: `test/MITLFrontend/fixtures/rfc/rfc7252_s4_2_s4_8.xml`

**Interfaces:**

- Consumes: RFC XML.
- Produces: `MetricContextGraph` with stable node IDs and provenance spans.

- [ ] **Step 1: Write failing context tests**

```python
def test_retransmission_clause_reaches_parameter_formula():
    graph = build_context_graph(parse_rfc_xml(FIXTURE))
    clause = graph.node("rfc7252.s4.2.p.retransmit_envelope")
    reachable = graph.expand(clause.node_id, edge_kinds={
        "cross_ref", "uses_symbol", "defines", "derives_bound"
    })
    assert "MAX_TRANSMIT_SPAN" in {node.label for node in reachable}
    assert "ACK_TIMEOUT" in {node.label for node in reachable}
    assert graph.node("rfc7252.s4.8.2.eq.max_transmit_span").kind == "parameter_expression"
```

- [ ] **Step 2: Verify RED**

```bash
python3 -m pytest test/MITLFrontend/unit/test_context_graph.py -v
```

- [ ] **Step 3: Implement stable node and edge types**

```python
@dataclass(frozen=True)
class ContextNode:
    node_id: str
    kind: Literal[
        "section", "paragraph", "sentence", "normative_clause",
        "definition", "parameter", "parameter_expression", "exception"
    ]
    label: str
    text: str
    source_span: SourceSpan

@dataclass(frozen=True)
class ContextEdge:
    source: str
    target: str
    kind: Literal[
        "contains", "cross_ref", "defines", "uses_symbol",
        "derives_bound", "exception_of", "alternative_to"
    ]
```

- [ ] **Step 4: Implement graph expansion, not fixed windows**

`expand()` must be deterministic, bounded by `max_nodes`, and sort neighbors by `(section_order, node_id)`. It must return `truncated=true` rather than silently dropping context.

- [ ] **Step 5: Run tests and inspect one serialized graph**

```bash
python3 -m pytest test/MITLFrontend/unit/test_context_graph.py -v
python3 -m tafuzz_specminer.cli build-context \
  test/MITLFrontend/fixtures/rfc/rfc7252_s4_2_s4_8.xml \
  --out /tmp/rfc7252-context.json
```

Expected: tests pass; JSON contains the retransmission clause, `MAX_TRANSMIT_SPAN`, its formula, and original source spans.

- [ ] **Step 6: Commit**

```bash
git add tool/MITLFrontend/src/tafuzz_specminer scripts/mitl_frontend test/MITLFrontend
git commit -m "feat: build metric RFC context graph"
```

---

### Task 4: Add Candidate Generation Boundary and Deterministic MITL Compilation

**Files:**

- Create: `tool/MITLFrontend/src/tafuzz_specminer/candidate_provider.py`
- Create: `tool/MITLFrontend/src/tafuzz_specminer/template_compiler.py`
- Create: `tool/MITLFrontend/src/tafuzz_specminer/parameter_resolver.py`
- Test: `test/MITLFrontend/unit/test_template_compiler.py`
- Fixture: `test/MITLFrontend/fixtures/properties/candidate_retransmit_span.json`

**Interfaces:**

- Produces: `CandidateProvider.generate(context) -> Sequence[PropertyCandidate]` and `compile_property(spec, resolved_bounds) -> CompiledProperty`.

- [ ] **Step 1: Write RED tests for abstention and symbolic bounds**

```python
def test_bounded_history_compiles_after_parameter_resolution():
    resolved = resolve_bounds(spec, {
        "ACK_TIMEOUT": Decimal("2"),
        "ACK_RANDOM_FACTOR": Decimal("1.5"),
        "MAX_RETRANSMIT": 4,
    })
    compiled = compile_property(spec, resolved, tick_unit="millisecond")
    assert resolved["MAX_TRANSMIT_SPAN"] == Decimal("45")
    assert compiled.formula == "G (retransmit -> O [0,45000] first_con_send)"

def test_unknown_pattern_abstains():
    with pytest.raises(UnsupportedPattern, match="pattern=unbounded_fairness"):
        compile_property(spec.model_copy(update={"pattern": "unbounded_fairness"}), {})
```

- [ ] **Step 2: Implement a provider protocol**

```python
class CandidateProvider(Protocol):
    def generate(self, context: MetricContext) -> Sequence[PropertyCandidate]: ...

class FileCandidateProvider:
    def __init__(self, candidate_path: Path): ...
    def generate(self, context: MetricContext) -> Sequence[PropertyCandidate]: ...
```

The reproducible pipeline must work with `FileCandidateProvider`; a model-specific provider is a separate adapter and cannot bypass validation.

- [ ] **Step 3: Implement the six template compilers**

Create exact compiler functions for:

```python
compile_bounded_response
compile_bounded_absence
compile_minimum_separation
compile_bounded_retention
compile_bounded_history
compile_state_transition_deadline
```

Each accepts typed fields and returns a formula; none accepts raw formula text from the provider.

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest test/MITLFrontend/unit/test_template_compiler.py -v
```

Expected: all symbolic-bound, unit-conversion, interval-openness and abstention cases pass.

- [ ] **Step 5: Commit**

```bash
git add tool/MITLFrontend/src/tafuzz_specminer test/MITLFrontend
git commit -m "feat: compile grounded RFC candidates into MITL"
```

---

### Task 5: Validate Formulas Against the Existing TAMonitor Backend

**Files:**

- Create: `tool/MITLFrontend/src/tafuzz_specminer/validator.py`
- Modify: `tool/MITLFrontend/src/tafuzz_specminer/cli.py`
- Test: `test/MITLFrontend/integration/test_tamonitor_validation.py`
- Fixtures: `test/MITLFrontend/fixtures/properties/traces/*.trace`

**Interfaces:**

- Consumes: `CompiledProperty` and TAMonitor binary path.
- Produces: `ValidationReport` with parse, SAT, positive witness, negative witness and status.

- [ ] **Step 1: Write a failing integration test**

```python
def test_retransmit_span_has_positive_and_negative_witnesses(tamonitor):
    report = validate_with_tamonitor(
        compiled_property(),
        tamonitor=tamonitor,
        positive_trace=FIXTURES / "retransmit_within_45s.trace",
        negative_trace=FIXTURES / "retransmit_after_45s.trace",
    )
    assert report.formula_status == "VALID"
    assert report.positive_verdict == "POSITIVE"
    assert report.negative_verdict == "NEGATIVE"
    assert report.status == "FORMULA_VALID"
```

- [ ] **Step 2: Implement subprocess calls without shell interpolation**

```python
command = [
    str(tamonitor), "--formula-inline", compiled.formula,
    "--trace", str(trace_path), "--word", "finite",
    "--build-mode", "flatten", "--out", str(output_dir),
]
completed = subprocess.run(command, text=True, capture_output=True, check=False)
```

Store command arguments, return code, stderr digest and output metadata in the report. Do not store secrets or environment variables.

- [ ] **Step 3: Run formula validation and protected baseline**

```bash
python3 -m pytest test/MITLFrontend/integration/test_tamonitor_validation.py -v
bash scripts/mitl_frontend/verify_protected_baseline.sh
```

Expected: property witness test passes; original baseline remains unchanged.

- [ ] **Step 4: Commit**

```bash
git add tool/MITLFrontend/src/tafuzz_specminer test/MITLFrontend
git commit -m "feat: gate extracted properties with TAMonitor"
```

---

### Task 6: Build the Clang Semantic Index and Multi-Evidence Binder

**Files:**

- Create: `tool/MITLFrontend/analyzer/include/tafuzz/SemanticIndex.h`
- Create: `tool/MITLFrontend/analyzer/include/tafuzz/PropertyBinding.h`
- Create: `tool/MITLFrontend/analyzer/lib/SemanticIndex.cpp`
- Create: `tool/MITLFrontend/analyzer/lib/PropertyBinding.cpp`
- Create: `tool/MITLFrontend/analyzer/tools/tafuzz-index.cpp`
- Test: `test/MITLFrontend/unit/SemanticIndexTests.cpp`
- Fixture: `test/MITLFrontend/fixtures/c/coap_exchange.c`

**Interfaces:**

- Produces: `semantic_index.json` and `source_binding.json`.

- [ ] **Step 1: Write failing C++ tests**

```cpp
TEST(PropertyBinding, MatchesAckByTypeConstantFieldAndControlPredicate) {
    auto index = indexFixture("coap_exchange.c");
    auto candidates = bindAtomicProposition(index, ackReceivedProperty());
    ASSERT_FALSE(candidates.empty());
    EXPECT_EQ(candidates.front().functionQualifiedName, "receive_packet");
    EXPECT_TRUE(candidates.front().evidence.hasTypeEvidence);
    EXPECT_TRUE(candidates.front().evidence.hasConstantEvidence);
    EXPECT_TRUE(candidates.front().evidence.hasControlEvidence);
}

TEST(PropertyBinding, NameSimilarityAloneCannotApprove) {
    auto candidate = candidateWithNameEvidenceOnly();
    EXPECT_EQ(classifyBinding(candidate), BindingStatus::NeedsReview);
}
```

- [ ] **Step 2: Define stable structs**

```cpp
struct SourceAnchor {
    std::string canonicalPath;
    std::string usr;
    uint32_t beginLine;
    uint32_t beginColumn;
    uint32_t endLine;
    uint32_t endColumn;
    std::string sourceSha256;
};

struct BindingEvidence {
    double nameScore;
    bool hasTypeEvidence;
    bool hasConstantEvidence;
    bool hasControlEvidence;
    bool hasDataflowEvidence;
    bool hasDynamicEvidence;
};
```

- [ ] **Step 3: Implement a `FrontendAction` and `RecursiveASTVisitor`**

Index declarations, enum constants, field comparisons, function calls, string literals and source ranges using the real `compile_commands.json`. Skip system headers unless a property explicitly references an external API.

- [ ] **Step 4: Implement deterministic scoring**

```cpp
double score = 0.15 * nameScore
             + 0.20 * typeScore
             + 0.20 * constantScore
             + 0.15 * contextScore
             + 0.20 * dataflowScore
             + 0.10 * dynamicScore;
```

Approval requires `score >= 0.75` and at least one of type, constant, control, dataflow or dynamic structural evidence.

- [ ] **Step 5: Build and test**

```bash
cmake -S tool/MITLFrontend -B tool/MITLFrontend/build \
  -DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm \
  -DClang_DIR=/usr/lib/llvm-18/lib/cmake/clang
cmake --build tool/MITLFrontend/build --target TafuzzSemanticIndexTests tafuzz-index -j2
ctest --test-dir tool/MITLFrontend/build -R '^TafuzzSemanticIndex' --output-on-failure
```

- [ ] **Step 6: Commit**

```bash
git add tool/MITLFrontend/analyzer test/MITLFrontend tool/MITLFrontend/CMakeLists.txt
git commit -m "feat: bind MITL propositions to C and C++ semantics"
```

---

### Task 7: Capture Whole-Program Bitcode and Build the Initial TPDG

**Files:**

- Create: `scripts/mitl_frontend/replay_compile_commands.py`
- Create: `tool/MITLFrontend/analyzer/include/tafuzz/TPDG.h`
- Create: `tool/MITLFrontend/analyzer/lib/TPDG.cpp`
- Create: `tool/MITLFrontend/analyzer/passes/TemporalSlicePass.cpp`
- Create: `tool/MITLFrontend/analyzer/tools/tafuzz-slice.cpp`
- Test: `test/MITLFrontend/unit/TPDGTests.cpp`

**Interfaces:**

- Consumes: `compile_commands.json`, linked LLVM bitcode, `source_binding.json`.
- Produces: `tpdg.json` with typed nodes, edges, evidence and analysis completeness.

- [ ] **Step 1: Write RED tests for data, control, input and timer edges**

```cpp
TEST(TPDG, ConnectsInputBytesToMatchingAck) {
    auto graph = analyzeFixtureBitcode("coap_exchange.bc", ackBinding());
    EXPECT_TRUE(graph.hasPath("input:buf[0]", "ap:ack_received"));
    EXPECT_TRUE(graph.hasPath("input:buf[2]", "ap:ack_received"));
    EXPECT_TRUE(graph.hasPath("input:buf[3]", "ap:ack_received"));
    EXPECT_TRUE(graph.hasEdgeKind(EdgeKind::Control));
    EXPECT_TRUE(graph.hasEdgeKind(EdgeKind::Decode));
}
```

- [ ] **Step 2: Implement compile-command replay**

For every non-link compile action, replace the compiler with `clang-18` or `clang++-18`, preserve include/define flags, remove the original `-o`, and add:

```text
-g -O0 -fno-discard-value-names -emit-llvm -c \
  -o tool/MITLFrontend/build/bitcode/${relative_object_path}.bc
```

Then invoke `llvm-link-18` on the selected target object set. Store the exact source command and output digest in `bitcode_manifest.json`.

- [ ] **Step 3: Register the LLVM pass with New Pass Manager**

```cpp
extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
    return {LLVM_PLUGIN_API_VERSION, "TafuzzTemporalSlice", "1.0",
        [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](StringRef Name, ModulePassManager &MPM,
                   ArrayRef<PassBuilder::PipelineElement>) {
                    if (Name != "tafuzz-temporal-slice") return false;
                    MPM.addPass(TemporalSlicePass());
                    return true;
                });
        }};
}
```

- [ ] **Step 4: Construct typed edges using built-in analyses**

Use `AAManager`, `MemorySSAAnalysis`, `DominatorTreeAnalysis`, `PostDominatorTreeAnalysis` and `LazyCallGraphAnalysis`. Every conservative alias edge must carry `precision="may"`; definite def-use edges carry `precision="must"`.

- [ ] **Step 5: Run pass tests**

```bash
cmake --build tool/MITLFrontend/build --target TafuzzTPDGTests TafuzzTemporalSlice tafuzz-slice -j2
ctest --test-dir tool/MITLFrontend/build -R '^TafuzzTPDG' --output-on-failure
opt-18 -load-pass-plugin tool/MITLFrontend/build/libTafuzzTemporalSlice.so \
  -passes=tafuzz-temporal-slice \
  test/MITLFrontend/fixtures/c/coap_exchange.bc -disable-output
```

- [ ] **Step 6: Commit**

```bash
git add scripts/mitl_frontend tool/MITLFrontend/analyzer test/MITLFrontend
git commit -m "feat: construct temporal property dependency graph"
```

---

### Task 8: Add Timer, Callback, and Async Framework Models

**Files:**

- Create: `tool/MITLFrontend/analyzer/include/tafuzz/AsyncModel.h`
- Create: `tool/MITLFrontend/analyzer/lib/AsyncModel.cpp`
- Create: `tool/MITLFrontend/models/coap_async_models.yaml`
- Test: `test/MITLFrontend/unit/AsyncModelTests.cpp`
- Fixture: `test/MITLFrontend/fixtures/c/coap_timer_callback.c`

**Interfaces:**

- Consumes: versioned YAML models.
- Produces: `TIMER_START`, `TIMER_CANCEL`, `CALLBACK_REGISTER`, `CALLBACK_FIRE` and `HAPPENS_BEFORE` edges.

- [ ] **Step 1: Write RED tests**

```cpp
TEST(AsyncModel, ConnectsTimerScheduleToCallbackFire) {
    auto graph = analyzeWithModels("coap_timer_callback.bc", modelPath());
    EXPECT_TRUE(graph.hasEdge("call:schedule_retry", "timer:retry", EdgeKind::TimerStart));
    EXPECT_TRUE(graph.hasEdge("timer:retry", "function:on_retry", EdgeKind::CallbackFire));
}

TEST(AsyncModel, UnknownTimerApiMakesAnalysisIncomplete) {
    auto result = analyzeUnknownTimerFixture();
    EXPECT_EQ(result.completeness, AnalysisCompleteness::ModelRequired);
}
```

- [ ] **Step 2: Define strict YAML schema**

```yaml
schema_version: tafuzz-async-model/1.0
models:
  - function: coap_io_prepare_io
    kind: timer_schedule
    timer_arg: 1
    callback_arg: 2
    context_arg: 3
  - function: coap_cancel_session_messages
    kind: timer_cancel
    key_args: [0, 1]
```

Unknown keys are fatal. Missing model is not silently treated as an ordinary call.

- [ ] **Step 3: Build and run tests**

```bash
cmake --build tool/MITLFrontend/build --target TafuzzAsyncModelTests -j2
ctest --test-dir tool/MITLFrontend/build -R '^TafuzzAsyncModel' --output-on-failure
```

- [ ] **Step 4: Commit**

```bash
git add tool/MITLFrontend/analyzer tool/MITLFrontend/models test/MITLFrontend
git commit -m "feat: model temporal callback dependencies"
```

---

### Task 9: Select Lifecycle-Correct Observation Points

**Files:**

- Create: `tool/MITLFrontend/analyzer/include/tafuzz/ObservationPlanner.h`
- Create: `tool/MITLFrontend/analyzer/lib/ObservationPlanner.cpp`
- Test: `test/MITLFrontend/unit/ObservationPlannerTests.cpp`

**Interfaces:**

- Consumes: `PropertySpec`, `source_binding.json`, `tpdg.json`, optional profile counts.
- Produces: schema-valid `observation_plan.json`.

- [ ] **Step 1: Write RED lifecycle tests**

```cpp
TEST(ObservationPlanner, TriggerIsAfterStateAndDeadlineUpdates) {
    auto plan = planFixture("coap_exchange");
    auto point = plan.pointFor("con_sent");
    EXPECT_EQ(point.placement, Placement::AfterStatement);
    EXPECT_TRUE(point.mustFollow.count("write:awaiting_mid"));
    EXPECT_TRUE(point.mustFollow.count("write:deadline_ms"));
}

TEST(ObservationPlanner, ResponseIsBeforeCorrelationStateClear) {
    auto point = planFixture("coap_exchange").pointFor("ack_received");
    EXPECT_EQ(point.placement, Placement::BeforeStatement);
    EXPECT_TRUE(point.mustPrecede.count("write:awaiting_mid=-1"));
}
```

- [ ] **Step 2: Implement deterministic weighted set cover**

```cpp
while (!uncovered.empty()) {
    const Candidate *best = argmin(candidates, [&](const Candidate &c) {
        const auto newlyCovered = intersectionSize(c.covers, uncovered);
        return newlyCovered == 0
            ? std::numeric_limits<double>::infinity()
            : c.cost / static_cast<double>(newlyCovered);
    });
    select(*best);
    subtract(uncovered, best->covers);
}
```

Tie-break by canonical source anchor. Reject a selected set if dominance/lifecycle checks fail.

- [ ] **Step 3: Add plan completeness states**

```text
COMPLETE
NEEDS_REVIEW
UNINSTRUMENTABLE_MACRO
MODEL_REQUIRED
AMBIGUOUS_LIFECYCLE
```

Only `COMPLETE` plans can be passed to the instrumenter.

- [ ] **Step 4: Run tests**

```bash
cmake --build tool/MITLFrontend/build --target TafuzzObservationPlannerTests -j2
ctest --test-dir tool/MITLFrontend/build -R '^TafuzzObservationPlanner' --output-on-failure
```

- [ ] **Step 5: Commit**

```bash
git add tool/MITLFrontend/analyzer test/MITLFrontend
git commit -m "feat: plan lifecycle-correct selective instrumentation"
```

---

### Task 10: Generate an Isolated Instrumented Source Tree

**Files:**

- Create: `tool/MITLFrontend/analyzer/tools/tafuzz-instrument.cpp`
- Test: `test/MITLFrontend/integration/test_instrumenter.py`
- Expected fixture: `test/MITLFrontend/fixtures/c/coap_exchange.instrumented.expected.c`

**Interfaces:**

- Consumes: compile database and `observation_plan.json` with `status=COMPLETE`.
- Produces: independent instrumented tree and `instrumentation_manifest.json`.

- [ ] **Step 1: Write a failing golden test**

```python
def test_instrumenter_respects_lifecycle_and_does_not_edit_original(tool):
    original_hash = sha256(FIXTURE)
    result = run_instrumenter(tool, FIXTURE, PLAN)
    text = result.instrumented_source.read_text()
    assert text.index("deadline_ms =") < text.index("tafuzz_emit(1,")
    receive = text.index("receive_packet")
    assert text.index("tafuzz_emit(2,", receive) < text.index("awaiting_mid = -1", receive)
    assert sha256(FIXTURE) == original_hash
```

- [ ] **Step 2: Implement `Rewriter` insertions using validated source ranges**

Before editing, verify source SHA-256 and exact token text at the anchor. If either differs, return `STALE_SOURCE_ANCHOR` and write no output.

- [ ] **Step 3: Emit a runtime declaration once per translation unit**

```c
#include <tafuzz/Runtime.h>
```

Insert calls in the form:

```c
tafuzz_emit(event_id, scope_id, value_mask);
```

Do not serialize strings in the producer path.

- [ ] **Step 4: Build, run golden test, and compile instrumented fixture**

```bash
cmake --build tool/MITLFrontend/build --target tafuzz-instrument -j2
python3 -m pytest test/MITLFrontend/integration/test_instrumenter.py -v
clang-18 -std=c11 -Wall -Wextra -Werror \
  -Itool/MITLFrontend/runtime/include \
  /tmp/tafuzz-instrumented/coap_exchange.c -fsyntax-only
```

- [ ] **Step 5: Commit**

```bash
git add tool/MITLFrontend/analyzer/tools test/MITLFrontend
git commit -m "feat: rewrite property-relevant observation sites"
```

---

### Task 11: Implement the Fixed-Record Buffered Runtime

**Files:**

- Create: `tool/MITLFrontend/runtime/include/tafuzz/EventRecord.h`
- Create: `tool/MITLFrontend/runtime/include/tafuzz/Runtime.h`
- Create: `tool/MITLFrontend/runtime/src/Runtime.c`
- Test: `test/MITLFrontend/unit/EventBufferTests.c`

**Interfaces:**

- Produces: `tafuzz_runtime_init`, `tafuzz_emit`, `tafuzz_runtime_flush`, drop and ordering metadata.

- [ ] **Step 1: Write RED tests for layout, ordering and overflow**

```c
_Static_assert(sizeof(TafuzzEventRecord) == 32, "record must remain fixed-size");

static void test_monotonic_sequence(void) {
    tafuzz_emit(1, 7, 0x1);
    tafuzz_emit(2, 7, 0x2);
    const TafuzzEventRecord *records = tafuzz_test_records();
    assert(records[0].global_seq < records[1].global_seq);
    assert(records[0].timestamp_ns <= records[1].timestamp_ns);
}

static void test_overflow_sets_drop_count(void) {
    for (size_t i = 0; i < tafuzz_test_capacity() + 1; ++i)
        tafuzz_emit(1, 1, 0);
    assert(tafuzz_runtime_drop_count() == 1);
}
```

- [ ] **Step 2: Define exact record layout**

```c
typedef struct {
    uint64_t timestamp_ns;
    uint64_t global_seq;
    uint32_t event_id;
    uint32_t scope_id;
    uint64_t value_mask;
} TafuzzEventRecord;
```

- [ ] **Step 3: Implement producer path**

Use `clock_gettime(CLOCK_MONOTONIC_RAW, ...)`, `_Atomic uint64_t` with `memory_order_relaxed` for global sequence, and one SPSC ring per registered thread. Disk I/O is forbidden inside `tafuzz_emit`.

- [ ] **Step 4: Run correctness, warning and sanitizer builds**

```bash
cmake --build tool/MITLFrontend/build --target TafuzzEventBufferTests -j2
ctest --test-dir tool/MITLFrontend/build -R '^TafuzzEventBuffer' --output-on-failure
cmake -S tool/MITLFrontend -B tool/MITLFrontend/build-asan \
  -DCMAKE_C_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build tool/MITLFrontend/build-asan --target TafuzzEventBufferTests -j2
ctest --test-dir tool/MITLFrontend/build-asan -R '^TafuzzEventBuffer' --output-on-failure
```

- [ ] **Step 5: Commit**

```bash
git add tool/MITLFrontend/runtime test/MITLFrontend tool/MITLFrontend/CMakeLists.txt
git commit -m "feat: buffer timestamped property events"
```

---

### Task 12: Assemble Event and State Records into TAMonitor Timed Words

**Files:**

- Create: `tool/MITLFrontend/src/tafuzz_specminer/trace_assembler.py`
- Modify: `tool/MITLFrontend/src/tafuzz_specminer/cli.py`
- Test: `test/MITLFrontend/unit/test_trace_assembler.py`

**Interfaces:**

- Consumes: binary `TafuzzEventRecord[]`, property IR, observation plan and parameter snapshot.
- Produces: `trace.csv` and `trace_metadata.json`.

- [ ] **Step 1: Write RED tests**

```python
def test_event_is_impulse_but_state_persists():
    trace = assemble(records=[
        rec(0, "waiting_ack_on"),
        rec(10, "retransmit"),
        rec(20, "waiting_ack_off"),
    ], manifest=manifest())
    assert trace.rows == [
        row(0, {"waiting_ack"}),
        row(10, {"waiting_ack", "retransmit"}),
        row(20, set()),
    ]

def test_drop_forces_inconclusive_metadata():
    result = assemble(records=[], manifest=manifest(), drop_count=1)
    assert result.metadata.complete is False
    assert result.metadata.forced_verdict == "INCONCLUSIVE"

def test_active_deadline_generates_tick():
    trace = assemble([rec(0, "con_sent")], manifest=bounded_response_manifest(5000))
    assert any(row.synthetic and row.time_tick > 5000 for row in trace.rows)
```

- [ ] **Step 2: Parse the fixed binary record safely**

```python
RECORD = struct.Struct("<QQIIQ")
if event_file_size % RECORD.size != 0:
    raise TraceAssemblyError("truncated event record")
```

- [ ] **Step 3: Implement scoped state and synthetic boundary queues**

Use a heap ordered by `(deadline_ns, scope_id, property_id)`. Cancel pending deadlines on matching response/cancel events. Convert nanoseconds to integer ticks only after sorting.

- [ ] **Step 4: Run tests and compare with TAMonitor TraceParser format**

```bash
python3 -m pytest test/MITLFrontend/unit/test_trace_assembler.py -v
python3 -m tafuzz_specminer.cli assemble-trace \
  --events test/MITLFrontend/fixtures/events/retransmit.bin \
  --property test/MITLFrontend/fixtures/properties/rfc7252_retransmit_span.json \
  --plan test/MITLFrontend/fixtures/properties/retransmit_plan.json \
  --out /tmp/retransmit.trace
```

Expected: CSV header is `time,props`; timestamps are nondecreasing; metadata is `complete=true`.

- [ ] **Step 5: Commit**

```bash
git add tool/MITLFrontend/src/tafuzz_specminer test/MITLFrontend
git commit -m "feat: project runtime events into timed valuations"
```

---

### Task 13: Run the First Real End-to-End Pipeline on libcoap

**Files:**

- Create: `scripts/mitl_frontend/run_frontend_pipeline.py`
- Create: `test/MITLFrontend/integration/test_libcoap_end_to_end.py`
- Create: `test/MITLFrontend/fixtures/properties/rfc7252_initial_timeout.json`
- Create: `test/MITLFrontend/fixtures/properties/rfc7252_retransmit_span.json`
- Create: `test/MITLFrontend/fixtures/properties/rfc7252_matching_ack.json`
- Create: `docs/mitl_frontend/artifact_guide.md`

**Interfaces:**

- Produces one immutable run directory with every stage's input, output, hash, command and completeness state.

- [ ] **Step 1: Pin the target revision**

Clone `libcoap` to the fixed experiment location and generate its manifest from the checked-out commit:

```bash
mkdir -p /tmp/tafuzz-targets
git clone https://github.com/obgm/libcoap.git /tmp/tafuzz-targets/libcoap
git -C /tmp/tafuzz-targets/libcoap switch --detach develop
python3 scripts/mitl_frontend/run_frontend_pipeline.py \
  --write-target-manifest \
  --target /tmp/tafuzz-targets/libcoap \
  --repository https://github.com/obgm/libcoap.git \
  --build-profile linux-udp-no-dtls \
  --manifest test/MITLFrontend/fixtures/targets/libcoap.json
```

The command reads `git rev-parse HEAD` and writes the exact 40-character SHA. The pipeline rejects a dirty target checkout and any manifest whose SHA differs from the checkout.

- [ ] **Step 2: Write a failing end-to-end test**

```python
def test_libcoap_property_reaches_tamonitor(libcoap_checkout, tamonitor):
    run = run_frontend_pipeline(
        target=libcoap_checkout,
        property_path=FIXTURES / "rfc7252_retransmit_span.json",
        tamonitor=tamonitor,
    )
    assert run.stage("property").status == "FORMULA_VALID"
    assert run.stage("binding").status in {"SOURCE_BOUND", "APPROVED"}
    assert run.stage("instrumentation").status == "COMPLETE"
    assert run.stage("trace").status == "COMPLETE"
    assert run.stage("monitor").verdict in {"POSITIVE", "NEGATIVE", "INCONCLUSIVE"}
```

- [ ] **Step 3: Implement immutable stage manifests**

Each stage serializes this typed structure:

```python
@dataclass(frozen=True)
class ArtifactDigest:
    path: str
    sha256: str

@dataclass(frozen=True)
class StageManifest:
    stage: Literal["property", "binding", "slice", "instrumentation", "trace", "monitor"]
    status: str
    inputs: tuple[ArtifactDigest, ...]
    outputs: tuple[ArtifactDigest, ...]
    command: tuple[str, ...]
    tool_version: str
    started_at: str
    duration_ms: int
```

- [ ] **Step 4: Run the pipeline on one valid and one intentionally late trace**

```bash
python3 scripts/mitl_frontend/run_frontend_pipeline.py \
  --target /tmp/tafuzz-targets/libcoap \
  --property test/MITLFrontend/fixtures/properties/rfc7252_retransmit_span.json \
  --tamonitor tool/MightyPPL/build/TAMonitor \
  --out /tmp/tafuzz-mitl-valid

python3 -m pytest test/MITLFrontend/integration/test_libcoap_end_to_end.py -v
bash scripts/mitl_frontend/verify_protected_baseline.sh
```

Expected: every stage has a manifest; valid test is not `NEGATIVE`; injected late retransmission produces a replayable `NEGATIVE`; protected baseline passes.

- [ ] **Step 5: Commit**

```bash
git add scripts/mitl_frontend test/MITLFrontend docs/mitl_frontend
git commit -m "feat: run RFC property pipeline on libcoap"
```

---

### Task 14: Add Oracle, Overhead, Gold-Set, and Ablation Harnesses

**Files:**

- Create: `test/MITLFrontend/experiments/run_experiments.py`
- Create: `test/MITLFrontend/experiments/compare_full_selective.py`
- Create: `test/MITLFrontend/experiments/measure_overhead.py`
- Create: `test/MITLFrontend/gold/annotation_schema.json`
- Create: `docs/mitl_frontend/annotation_guide.md`

**Interfaces:**

- Produces: CSV/JSON with extraction, binding, slice, instrumentation and runtime metrics.

- [ ] **Step 1: Define experiment rows before running experiments**

```python
@dataclass(frozen=True)
class RunRow:
    target: str
    target_commit: str
    property_id: str
    mode: Literal["full", "selective", "no_async", "no_lifecycle"]
    verdict: str
    complete: bool
    instrumentation_points: int
    events: int
    dropped_events: int
    execs_per_second: float
    p50_latency_us: float
    p95_latency_us: float
    p99_latency_us: float
```

- [ ] **Step 2: Implement full-vs-selective verdict oracle**

For identical inputs and parameter snapshots:

```python
assert full.complete and selective.complete
assert full.trace_semantic_projection == selective.trace_semantic_projection
assert full.verdict == selective.verdict
```

Any mismatch writes the smallest disagreeing prefix and marks the property `SEMANTIC_MISMATCH`.

- [ ] **Step 3: Measure overhead with warmup and repeated trials**

Use 5 warmup runs and 30 measured runs per configuration. Report median and bootstrap 95% confidence intervals. Never mix monitor time into target execution overhead.

- [ ] **Step 4: Run the first experiment packet**

```bash
python3 test/MITLFrontend/experiments/run_experiments.py \
  --manifest test/MITLFrontend/experiments/smoke_manifest.json \
  --out test/MITLFrontend/results/smoke
python3 test/MITLFrontend/experiments/compare_full_selective.py \
  test/MITLFrontend/results/smoke
```

Expected: every row has target SHA, property ID, completeness, verdict and timing metrics; no semantic mismatch in the smoke packet.

- [ ] **Step 5: Commit**

```bash
git add test/MITLFrontend docs/mitl_frontend
git commit -m "test: add MITL frontend paper experiment harness"
```

---

### Task 15: Expose Read-Only Inputs for Later PTA-Guided Fuzzing

**Files:**

- Create: `schema/fuzz_guidance.schema.json`
- Create: `tool/MITLFrontend/src/tafuzz_specminer/fuzz_guidance.py`
- Test: `test/MITLFrontend/unit/test_fuzz_guidance.py`
- Do not modify: `src/TAMonitor/PTA/*Solver*`

**Interfaces:**

- Consumes: `tpdg.json`, `observation_plan.json`, `pta_analysis.json`, `pta_reachable_nodes.jsonl`, `pta_reachable_arcs.jsonl`, `pta_pieces.jsonl`.
- Produces: immutable `fuzz_guidance.json` with input regions, target APs, state prerequisites and PTA lookup keys.

- [ ] **Step 1: Write a RED test that rejects scalar-only PTA guidance**

```python
def test_guidance_requires_location_zone_and_piece_identity():
    with pytest.raises(GuidanceError, match="scalar edge cost is insufficient"):
        build_guidance(tpdg(), pta={"edge_cost": 5})

def test_guidance_keeps_input_masks_and_pta_query_key():
    guidance = build_guidance(tpdg(), pta_snapshot())
    assert guidance.targets[0].input_regions[0].bit_mask == 0xC0
    assert guidance.targets[0].pta_query.requires == (
        "automaton", "location", "clock_valuation", "reachable_node"
    )
```

- [ ] **Step 2: Implement only the read-only adapter**

Do not implement queue scheduling in this task. Validate PTA snapshot completeness and refuse `incomplete_*` or `assumption_required` snapshots.

- [ ] **Step 3: Run tests and protected baseline**

```bash
python3 -m pytest test/MITLFrontend/unit/test_fuzz_guidance.py -v
bash scripts/mitl_frontend/verify_protected_baseline.sh
```

- [ ] **Step 4: Commit**

```bash
git add schema/fuzz_guidance.schema.json tool/MITLFrontend/src/tafuzz_specminer/fuzz_guidance.py test/MITLFrontend
git commit -m "feat: export temporal fuzz guidance contract"
```

---

## Milestone Gates

### Gate M1: Real Property Closed Loop

All must hold:

```text
5 manually approved RFC 7252 properties
1 pinned libcoap revision
property -> binding -> instrumentation -> trace -> TAMonitor
0 dropped events in correctness runs
all protected baseline tests pass
```

If M1 fails, do not start PTA-guided Fuzzing.

### Gate M2: Temporal Dependency and Instrumentation Correctness

All must hold:

```text
timer/callback models cover every selected property
full-vs-selective verdict equivalence = 100% on the oracle corpus
AP binding Top-3 >= 80%
accepted property precision >= 85%
P99 target latency overhead <= 10%
```

If state-signal projection disagrees with the full oracle, restrict the first paper to event-based properties and report that boundary.

### Gate M3: Paper Evaluation Readiness

All must hold:

```text
3 RFC documents annotated
at least 15 executable temporal properties
3 C/C++ CoAP implementations or a justified 2+1 configuration
all baselines and ablations reproducible from manifests
every claimed violation has a replay artifact and manual confirmation
```

---

## Final Verification Commands

Run these from the TAFuzz repository root immediately before claiming completion:

```bash
clang-18 --version
clang++-18 --version

python3 -m pytest test/MITLFrontend/unit test/MITLFrontend/integration -v

cmake --build tool/MITLFrontend/build --target \
  TafuzzSemanticIndexTests \
  TafuzzTPDGTests \
  TafuzzAsyncModelTests \
  TafuzzObservationPlannerTests \
  TafuzzEventBufferTests \
  tafuzz-index tafuzz-slice tafuzz-instrument -j2

ctest --test-dir tool/MITLFrontend/build --output-on-failure

bash scripts/mitl_frontend/verify_protected_baseline.sh

python3 test/MITLFrontend/experiments/run_experiments.py \
  --manifest test/MITLFrontend/experiments/smoke_manifest.json \
  --out /tmp/tafuzz-mitl-final-smoke
```

Completion evidence must state the exact pass/fail counts, target SHAs, Clang/LLVM version, TAMonitor build SHA and any remaining `INCONCLUSIVE`/`MODEL_REQUIRED` items.

---

## Execution Order and Stop Rules

1. Execute Tasks 1–5 and review property semantics before touching target code.
2. Execute Tasks 6–10 and review source binding/observation plans before compiling instrumented real targets.
3. Execute Tasks 11–13 to close the first real loop.
4. Execute Task 14 only after full-vs-selective correctness exists.
5. Execute Task 15 only after M1 and M2 pass.
6. Stop immediately on protected baseline regression, stale source anchor, trace drop in correctness mode, or formula provenance mismatch.

This ordering is intentional：规范语义错误无法通过更复杂的静态分析修复，错误的 AP 绑定也无法通过更轻量的插桩修复。
