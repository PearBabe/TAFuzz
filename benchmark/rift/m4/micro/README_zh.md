# RIFT-M4 微基准生产验收包

本目录把 RIFT-GOLD-120 转成一个可给生产静态分析器使用、但不暴露 influence oracle 的验收工作流。它只检验 M4 的两项能力：typed AP 绑定与完整 influence cone；frontier、recipe 和真实项目结论不在此处提前评分。

## 隔离边界

工作流分成三个不可交换的阶段：

1. `prepare.py` 只读取 `compile_commands.json` 和 case 源码。它不读取 corpus manifest、`ground_truth/`、关系、类别、可控性、路径或 recipe。
2. `run_analyzer.py` 只读取冻结输入并运行分析器。120 个 case 全部完成、四类 production artifact 和必需的 `analysis_certificate.json` 通过 schema/哈希/候选记账检查后，才生成 `analysis_run_manifest.json`。
3. `evaluate.py` 先重新验证整个 sealed run；只有验证成功后才读取机械 truth 并评分。

分析器可见输入不含原始文件名中的 `must/may/negative`，也不含 source 候选数组。准备阶段先从原始源码提取 AP IR，随后从 analyzer-visible 副本中移除全部 `RIFT_SOURCE/RIFT_NODE/RIFT_AP` marker，并把被标记的 source/intermediate C/C++ 标识符确定性、等长度匿名化；行列位置和程序语义保持不变。

这是生成器构造的 synthetic corpus，truth 是 `MECHANICAL_TEMPLATE_ORACLE`，所以不需要两名真人标注。该结论只适用于这 120 个机械 case；真实项目仍需要独立标注与仲裁。

## 冻结输入

已生成的 `frozen/` 包含：

```text
frozen/
├── manifest.json
├── compile_commands.json
├── sources/case_NNN.c|cpp
└── cases/case_NNN/
    ├── compile_commands.json
    └── property_ir.json
```

每个 Property IR 均符合 `typed_property_ir.schema.json`。AP 的位置、C/C++ 类型和 RHS 表达式在 marker 擦除前只从源码声明提取；role 只按源码表达式形态推导为 `guard` 或 `state`。它不复用 mechanical truth 中的 AP role/expression 字段。冻结 manifest 只携带预注册 private-oracle SHA-256 commitment，不读取或暴露 truth 内容。

`frozen/manifest.json` 的字节和 SHA-256 始终不变。最终正式运行前的审计把 semantic index、CIG、certificate、typed Property IR compatibility envelope 和 AP bindings 从 1.0.0 升为 2.0.0；迁移只允许由 `schema_migration_ledger.json` 中五条精确 old-ID/hash → new-ID/hash 记录授权。Property IR 与 bindings 的 v2 schema 仍严格接受冻结的 legacy-v1 文档/输出，禁止字段混用。ledger 之外的 schema 改动直接失败。sealed run 同时封存 ledger 哈希与当前完整 production schema-tree 哈希。

`compile_commands.json` 是标准、可直接交给 Clang 的 raw compilation database。每 case DB 的 `directory="../.."` 相对 DB 所在目录解析到 bundle 根，因而不依赖 runner 当前工作目录；全局 DB 使用 `directory="."`。每 case 单独分析，避免 120 个独立程序的同名 `main` 被错误地跨 TU 合并；全局 compile DB 仍保留用于审计与批量构建。

重新生成（目标目录必须不存在）：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/m4/micro/prepare.py \
  --oracle-commitment-sha256 d1c4cb44094416d7ac814e80f5abce0f056cb3ec353ee0d60728fab584ee6452 \
  --output benchmark/rift/m4/micro/frozen

PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/m4/micro/validate_acceptance.py \
  --bundle benchmark/rift/m4/micro/frozen
```

## 分析器接口

默认采用当前生产 CLI 的单次内存流水线：

```text
tafuzz-sa influence \
  --compile-db <case compile_commands.json> \
  --property <property_ir.json> \
  --output-dir <case result directory>
```

必须生成：

```text
semantic_index.json
ap_bindings.json
contextual_influence_graph.json
ap_influence_cones.json
analysis_certificate.json
```

证书是必需产物而不是可选附加项。runner 验证其精确三输入（raw compile DB、typed Property IR、source-input manifest）、精确四输出、构建/schema 摘要、语义环境、实际 analyzer/toolchain 和逐文件 physical provenance。CLI 变化集中在 `default_adapter.json`/`command_adapter.py`；adapter 允许一至三个公开 `index|bind|influence` 阶段，但四个分析 artifact 必须各有且仅有一个 producer，不接受不存在的 `cone` 子命令。

运行分析器：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/m4/micro/run_analyzer.py \
  --bundle benchmark/rift/m4/micro/frozen \
  --analyzer /absolute/path/to/tafuzz-sa \
  --output /tmp/rift-m4-production-run \
  --timeout 1800
```

runner 拒绝覆盖已有输出。失败目录可保留诊断日志，但没有最终 `analysis_run_manifest.json` 的目录不能评分。

runner 默认用 `/usr/bin/bwrap` 把根文件系统设为只读、隔离 network/process namespace、只开放当前 case result 目录写入，并用空挂载遮蔽 `benchmark/rift/gold`。自定义 private corpus 必须额外传 `--deny-read-root /absolute/private/corpus`；evaluator 会确认实际评分 corpus 曾被遮蔽。adapter 强制 `{analyzer}` 位于 `argv[0]`，并封存所有 argv 直接引用的 executable/script/config/input 文件哈希。

单独检查 sealed run：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/m4/micro/validate_acceptance.py \
  --bundle benchmark/rift/m4/micro/frozen \
  --run /tmp/rift-m4-production-run
```

## 验收条件

`validate_acceptance.py` 强制检查：

- production JSON Schema；
- 原冻结 schema snapshot、精确五项 migration ledger、当前完整 schema-tree 的双重哈希封存；
- typed Property IR 的 artifact/property/AP/selector/formula-node 稳定 ID 全域互异；
- `certificate(raw compile DB/Property IR/source files) → semantic index → AP bindings/CIG → cones` 的 SHA-256 链；
- 独立复算 identity-v2 path map、canonical compile DB、TU ID、input-file ID、input manifest 和 semantic-index artifact ID；
- 每个 TU 的 input-file 引用闭包、main source 物理字节、所有 lossless entity/object/node/relation/function/callsite 引用闭包与逻辑路径；
- Property IR 中每个 AP-role 都有 binding 记录；
- binding candidate 按 confidence 降序，所有 selector/node 引用存在；
- 每个 binding candidate 在对应 cone 中恰好有一条 disposition；
- 所有 graph/cone/member/edge/witness 引用闭合；
- `candidate_accounting_complete=true`、`ranking_never_prunes=true`；
- `INCLUDED` roots 全部属于 cone members，cone edge 两端属于 members；每条非 root witness 必须是无重复、方向连续、终止于 included root 的 source→root 路径，且 cone edge set 必须等于全部 witness 的并集；
- `COMPLETE` cone 不得包含 `UNKNOWN_INFLUENCE`；
- 相关 binding 未 CONFIRMED、没有 INCLUDED root、存在 soundness/stage gap 时，缺席不能推导为 NO；
- analyzer sandbox、实际 execution argv、wrapper/helper/config 哈希与 private-oracle commitment；
- 120 个 case 全部完成后才允许 seal。

这些检查禁止“只输出命中的候选”“把未分析的候选静默当成 NO”或在评分前修改产物。

## 评分

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/m4/micro/evaluate.py \
  --bundle benchmark/rift/m4/micro/frozen \
  --run /tmp/rift-m4-production-run \
  --output /tmp/rift-m4-evaluation.json
```

报告给出：

- AP exact site Top-1 binding precision/recall/F1；
- gold MUST influencer 是否进入 cone，以及 exact MUST precision/recall；
- exact MAY precision/recall；
- MUST/MAY 合并后的 influence precision/recall/F1；
- 12 类逐类结果；
- UNKNOWN pair、unresolved binding、unknown member、unsupported construct/effect/status 统计；
- 逐 pair 和 binding 的失败诊断。

`NO` 只在 source location 已被 semantic index 覆盖、相关 AP-role binding 均 `CONFIRMED` 且至少一个确认候选为 `INCLUDED` root、TU/CIG/cone 均 `COMPLETE`、并且没有 soundness-risk/stage-failure 时由缺席推导。其他缺席一律是 `UNKNOWN`；UNKNOWN 在正例上计作漏报，在负例上也不会获得 true-negative credit。

Top-1 AP 和 source projection 都要求 exact token 起点（同文件、行、列）；函数级或全文件 source range 不算 exact 命中。所有 result JSON 在 truth 解封前以单次 byte read 完成 digest 校验和 parse，evaluator 后续只使用内存 snapshot，不重新打开 artifact。

Cone 内部中间节点不会被当作 false positive。evaluator 仅在评分阶段把 cone 私有投影到机械 truth 标记的 source locations，从而衡量 source→AP pair，同时报告完整 cone 与 unsupported 状态。

## 自测

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s benchmark/rift/m4/micro/tests -p 'test_*.py' -v
```

自测覆盖：两次准备逐字节一致、marker/语义名/答案字段擦除、120 条 C/C++ raw compile DB 全量编译、cwd-independent per-case DB、单流水线 adapter、私有 corpus 读取被 sandbox 阻断、helper 改写被哈希拒绝、缺失证书拒绝、identity/input-manifest 篡改拒绝、Property IR 跨域 ID 碰撞拒绝、缺失 candidate/root/member/edge/witness 和反向/断裂 witness 拒绝、UNKNOWN/NO 计分、exact-site range 负例、私有 truth 阶段隔离，以及一个不读取 truth 的 v2 production-schema fake analyzer 从运行到 sealed manifest 的完整路径。

## Synthetic preparer 与通用契约的边界

`prepare.py` 和当前 `load_private_truth()` 是 RIFT-GOLD-120 专用 fixture：它们理解 `cases/`、生成器 header、marker 和机械 truth schema，不能直接拿来准备任意真实项目。

项目无关、可迁移的部分是 production typed Property IR/semantic index/bindings/CIG/cones schema、单流水线 adapter、sealed-run 哈希与 sandbox 契约、完整候选记账以及 UNKNOWN/NO 语义。迁移到 ArduPilot、libcoap 或其他 C/C++ 源码时，应由独立的通用前端提供 raw compile DB 和 typed Property IR，并为真实项目实现单独的双人标签 evaluator adapter；不得调用 synthetic marker preparer。核心 Clang/LLVM 分析器及上述产物契约无需项目专用规则。
