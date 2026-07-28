# RIFT-M4 libcoap / COAP-TX-01 验收目标

本目录把 M4 的 libcoap 验收对象固定为一个可审计但**尚非真人仲裁 gold**
的开发门槛。它不修改 libcoap，不向 RIFT generic core 或 model pack 注入
`COAP-TX-01` 专属依赖边。

## 冻结身份

- 被分析源码：`benchmark/coap/libcoap@94bacc8939dd6711169cd2332a002a361ec62531`。
- M1 固定构建目录：`/tmp/tafuzz-rift-libcoap-fixed`。
- compile DB：38 TU，SHA-256 `3bf8dfee452381ad99363c17420d7e26e51ddf3755eda2c1109b10de8f30bc3a`。
- linked LLVM 18 bitcode：2,743,756 bytes，SHA-256
  `08ead6a83ce230fab63eb028c9eec21fb0b2e23e79dd6270c8ee78e43b12c61d`。
- 原 COAP-TX-01 属性/源码映射来自其祖先提交
  `7cf7465b784baded4de183290c547d582becfd28`。本目录重新定位到了冻结提交，
  但后续提交增加了 token-aware queue matching，因此仍需两名真人独立复核与仲裁。

## 文件

- `typed_property_ir.json`：实际 analyzer 输入；通过
  `src/StaticAnalysis/schema/typed_property_ir.schema.json` 2.0.0 role-DNF 校验，包含完整
  MITL AST、typed selectors 和逐 role 的合取/析取绑定组。
- `property_ir.json`：补充 default profile、logical-deadline、scope 与 commit-port 说明；
  它明确标为 companion draft，不冒充 production schema。
- `provisional_influence_labels.json`：19 个候选 MUST、8 个 MAY、scope-only、
  async/model-required 关系及逐条源码理由。
- `acceptance_manifest.json`：commit/tree、源文件/输入/构建哈希、当前提交的精确
  `<site, phase, scope>` 目标、外部输入候选及未解决人工标注项。
- `validate_acceptance.py`：重新计算以上身份和源码锚点；`--deep` 还会让 LLVM 18
  在 linked bitcode 上构造 MemorySSA。
- `evaluate_provisional.py`：把已认证 cone 投影到开发期 source-range 标签；强制输出
  `DEVELOPMENT_DIAGNOSTIC_NOT_GOLD`，不计算 precision/recall/F1，也不越过真人仲裁边界。

## 关键语义

`coap_first_retransmit_deadline_reached` 不是“event-loop callback 被调度”的时间。
libcoap 用 `sendqueue_basetime + delta queue` 表示逻辑 deadline；如果 event loop
晚运行，callback timestamp 只能作为诊断值。正确绑定必须联合：

1. 成功发送 CON、计算初始 timeout、插入 queue 的提交阶段；
2. `ack_timeout`、`ack_random_factor`、PRNG byte 和 tick scaling；
3. delta-queue 中该 allocation generation 的逻辑 deadline；
4. 后续 scheduler 对 monotonic `now` 的 due comparison；
5. 匹配 ACK/RST 或显式本地取消对同一 generation 的移除。

固定 `2000/3000 ms` 公式只适用于 runtime 值仍为 `2.000/1.500` 的默认 profile。
如果 setter 改了参数，应重新实例化 property bound，不能继续拿默认公式判错。

## 验证

若固定 `/tmp` 构建不存在，先精确重建三次：

```bash
python3 benchmark/rift/reproduction/libcoap/reproduce_clang18.py \
  --build-dir /tmp/tafuzz-rift-libcoap-fixed --runs 3 --jobs 8
```

然后执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/m4/libcoap/validate_acceptance.py \
  --build-dir /tmp/tafuzz-rift-libcoap-fixed --deep

PYTHONDONTWRITEBYTECODE=1 python3 \
  benchmark/rift/m4/libcoap/evaluate_provisional.py \
  --analysis-dir /path/to/rift-output \
  --output /tmp/rift-m4-libcoap-provisional-evaluation.json
```

通过只说明 artifact identity、Property IR 一致性、源码 locator 和候选标签包完整。
它不等于真人 gold 通过，也不允许将候选标签用于论文 headline precision/recall。

## 人工阻塞项

需要两名独立真人分别标注，然后记录原始分歧、Cohen's κ 与仲裁结果：

1. `94bacc89` 的 token-aware ACK/OSCORE matching 是否进入 monitor correlation key；
2. logical deadline synthetic event 的 exact phase，而非 callback time；
3. 每条 MUST/MAY/SCOPE/NO 关系；
4. 哪些非 ACK/RST queue removal 属于合法 `coap_attempt_cancelled`；
5. 默认 profile 的 runtime setter 前置条件。

在这些工作完成前，M4 可以把 19 个候选 MUST 作为“全部找到或显式报告
unsupported/model-required”的开发 gate，但不能宣布真实项目 recall=100%。
