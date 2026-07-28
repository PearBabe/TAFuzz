# RIFT-M4：联合 AP 绑定与完整影响锥实施结果

## 结论

M4 已完成可执行的项目无关生产流水线：raw `compile_commands.json` 经 Clang 18
形成多 TU 语义索引，typed Property IR 经 role-DNF 联合绑定得到 AP roots，再生成
上下文敏感 CIG、保守影响锥和 Certificate v2。M4 的验收结论仅是“绑定与影响检测
达到当前门槛”；不包含 external frontier、mutation recipe、真人 real-project gold、
三项目可移植性或 fuzz 收益结论。

最终生产身份：

```text
tafuzz-sa SHA-256       6ae5b4fb5103e3a265c06ca6fb9e482818139d48a7aa7fbef1faa9a1afddabdf
production core         6472e17700ebede4b0112283d62f82d4d2b779dd950b52662a57c02732388ac0
embedded schema bundle  f960af4ea0cf4865e787dfbe01b0f812239ba7fe0d7d70e1923ebfa463c9dd8e
schema contract tree    35a8b6280474ab8f7970dd31d720e7a3144a678d1cd6b8f19ed9ac919f85e57e
```

完整机器可读记录见 `benchmark/rift/m4/results/execution_manifest.json`。

## 核心实现

1. **语义身份与物理证据**：Clang USR、canonical type、typed access path、source/
   expansion location、callsite-tagged context、logical roots 和内容哈希共同定义节点；
   系统头与生成位置进入保留的 content-addressed toolchain 域，不再输出 `<unknown>`。
2. **角色 DNF 绑定**：每个 AP role 拥有独立 selector-group ledger；group 内 `all_of`
   表示关系合取，同 role 多 group 表示有意备选。未解析 group 必须显式占位，不能由
   其他 role 的命中“补齐”。legacy v1 仍走冻结兼容分支。
3. **CIG**：当前覆盖 def-use、字段/对象、control、call/return、参数映射、caller storage
   side effect 和保守 unknown summary；call-string 上限为 1，递归有限展开。
4. **影响锥 certainty**：只有角色完整、所有活跃候选 confirmed 且唯一 contextual root
   才能以 MUST 起点传播。每个节点以四类 path mask 做单调固定点；UNKNOWN 不会抹除
   独立存在的 MAY 路径，而 `MUST + UNKNOWN/MODELLED` 会降为 MAY。root 固定，循环只
   增加 path bit。内部 validator 和独立 Python verifier 都从完整 CIG 重算固定点，
   不信任单条 witness 或 analyzer 自报 membership。
5. **可审计性**：四个分析产物、三项原始输入、16 项语义环境、19 个运行时组件、
   production/schema source tree 和五阶段摘要闭包均进入 Certificate v2。文件哈希使用
   自实现 64-bit streaming SHA-256，覆盖了 LLVM 旧 helper 在 512 MiB 处计数溢出的
   回归测试。

production core 与 CLI/schema 扫描没有 libcoap、ArduPilot、PX4、具体 AP/formula 或
答案常量；`model_pack.schema.json` 中 `expected_answer_edge` 与
`benchmark_case_id_branch` 是禁止规则类别，不是运行时知识。

## 120-case mechanical gold

最终 sealed run 位于 `/tmp/rift-m4-production-final-v6`，在读取 private mechanical
oracle 前通过全部证书/schema/引用闭包检查：

| 指标 | 结果 |
|---|---:|
| AP exact site Top-1 F1 | 1.000（130/130） |
| critical/MUST influencer detection | 66/66，recall 1.000 |
| influence precision | 0.9796 |
| influence recall | 0.9600 |
| influence F1 | 0.9697 |
| false positive / false negative | 3 / 6 |

这里必须区分 **MUST detection** 与 **exact MUST classification**：66 个 mechanical
MUST 全部进入影响锥，但当前都因 alias/control/call coverage 的保守边被分类为 MAY，
exact-MUST recall 为 0。M4 因而只通过“关键影响不能漏”的门槛，没有声称已完成
universal must-influence proof。120 个图和 130 个 cone 均保持
`CONSERVATIVE_INCOMPLETE`，55 个 pair 为 UNKNOWN；这些不是被静默删除的负例。

实现中实际发现并修复了两个相反错误：

- 非 confirmed/multi-root AP 曾被无条件初始化为 MUST，造成 false-MUST；
- 简单“所有路径取最弱”又让 `direct MAY + unrelated external-call UNKNOWN` 变成
  UNKNOWN，使 8 个 MUST influencer 漏检。四类 path-mask 半格同时保留了 soundness
  和 actionable detection，且反转 graph edge 顺序仍产生相同证书。

## libcoap / COAP-TX-01

同一个最终二进制在冻结的 libcoap 38 TU 上运行两次：

| 运行 | 墙钟 | 峰值 RSS | 结果 |
|---|---:|---:|---|
| v6a | 57.55 s | 1,806,560 KiB | PASS / conservative incomplete |
| v6b | 58.49 s | 1,806,728 KiB | PASS / conservative incomplete |

两次的 semantic index、bindings、CIG 和 cones 逐字节相同；共 121,868 个 contextual
nodes，四个 AP cones，没有 `<unknown>` source location。独立 verifier v0.4.0 对
v6a 完成严格物理回放，`failures=0, unsupported=0`。

role-DNF 绑定结果中，wait trigger、deadline response/bound/clock、ACK/RST 的
cancel/guard 均确认；scope 以及 local-cancel token 分支保持 unresolved/partial，明确
留给 M6 的 queue/generation model，不用项目特例补边。

对 36 条开发期 source-range 标签的投影是：32 `RECOVERED_KNOWN_PATH`、1
`RECOVERED_UNKNOWN_ONLY`、2 `NOT_RECOVERED_FROM_CURRENT_CONES`、1
`NOT_RECOVERED_MODEL_REQUIRED`。19 条候选 MUST 都出现于 known path；两个 runtime
setter、token cancellation 和 PRNG callback 暴露了 M5/M6 的真实缺口。该投影不是
entity-level gold：两条候选 negative 的源码范围也与 cone 重叠，恰好说明只有真人
仲裁前不能用 source-range 结果计算真实项目 precision/recall。

## 性能修正

四类固定点的首版把同一 CIG 重算三次，使 libcoap 增至 62.95 s，超过预注册门槛。
最终版保留独立 validator 复算，删除生成器冗余遍历，并把内部 lookup 从有序树改为
哈希表、最终产物再按 stable ID 排序。结果降到 57.55/58.49 s，确定性不变，没有
放宽 60 s/2 GiB 门槛。

## 可移植性边界与 M5 输入

M4 已证明 generic-core **结构上**无项目知识，并在 synthetic corpus 与 libcoap 上
运行；它尚未满足“同 binary/schema/core 在三个独立真实 C/C++ 项目零核心改动”的
最终 portability contract。因此当前不能写“RIFT 已证明可移植”。已核验的后续对象：

- SVF 3.2：111 个 Clang++ 18 TU；
- ArduPilot Copter：1,336 个 Clang 18 TU（含 177 个 build-generated TU）；
- PX4 v1.17.0：826 unique TU，可作额外异构对象。

M5 必须先实现 versioned declarative model-pack 的实际加载/证书绑定、external source
classification、双向确认和可解释 frontier，再生成 SMT/path summary 与 mutation
direction。项目知识只允许进入 model pack；同一生产二进制必须先跑 SVF，再在 M7
跑 ArduPilot，三项目 gate 通过前继续标记 `NOT_VALIDATED`。

## 复验入口

```bash
ctest --test-dir /tmp/tafuzz-sa-m4-clang18 --output-on-failure
python3 src/StaticAnalysis/tests/schema/validate_schemas.py \
  --schema-dir src/StaticAnalysis/schema
python3 benchmark/rift/m4/micro/validate_acceptance.py \
  --bundle benchmark/rift/m4/micro/frozen \
  --run /tmp/rift-m4-production-final-v6
python3 benchmark/rift/m4/verifier/verify.py --help
python3 benchmark/rift/m4/libcoap/evaluate_provisional.py --help
```

最终验证：Clang 18 CTest 13/13、schema 375 checks、micro contract 21/21、
独立 verifier 51/51、libcoap frozen checks 246、one-case 与 full-libcoap strict
certificate 均 PASS。
