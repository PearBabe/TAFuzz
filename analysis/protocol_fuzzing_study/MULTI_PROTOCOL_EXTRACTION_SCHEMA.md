# 多协议 MITL 真实性质提取规范

## 范围

本轮覆盖此前候选表与 ProFuzzBench 实际目标中出现的 17 个协议：CoAP、MQTT、TCP、QUIC、DNS、TLS、DTLS、SSH、RTSP、FTP、SMTP、SIP、DICOM、Modbus/TCP、OPC UA、DDS/RTPS、CAN/UDS。

“全部好的性质”不是预设每个协议若干条，而是对所选正式规范版本中的定时器、超时、重传、保活、租约、会话关闭和定时状态迁移进行穷尽式筛查，并收录所有通过下列质量门的不同义务。单纯把同一条款换一个常数、角色名称或实现配置，不计为新性质。

## 收录门

每条主目录性质必须同时满足：

1. 正式标准或正式公开 profile 中存在可定位的规范义务，并记录版本、section、URL、规范强度和不超过 20 个英文词的短摘录。
2. 时间区间具有真实来源。优先规范默认值；只有规范明确允许配置但没有默认值时，才可固定到已锁定实现/profile 的默认值，并标为 `IMPLEMENTATION_PROFILE`，不得声称为协议普遍常数。
3. `mathematical_mitl` 使用普通 MITL 记号（外层普通 `G`）；`mightyppl_formula` 才使用 MightyPPL 的 finite-word weak `G*`。两者必须分别标注，不能把星号算子写成普通 MITL 的 strict 全局算子。整数毫秒、pointwise timed word、finite、`flatten`，不使用 `[a,a]` singleton，不擅自加 epsilon 或容差。
4. AP 是固定布尔字母表；动态 packet ID、stream ID、token、sequence number 只用于 correlation，不进入 AP 名称。
5. 明确黑盒/白盒观测点，并映射到固定 40 位 commit 的真实文件、符号、行号和 permalink。
6. 至少一条手工可解释正例和反例；两者在 symbolic/concrete 下分别得到 `POSITIVE`/`NEGATIVE`。同时含 no-early 与 eventual 分支的双边窗口还必须有 late/missing 反例。
7. 与其他条目不是同一规范义务的机械拆分；如果拆分，必须分别对应不同 MUST/SHALL 动作或不同可观测 oracle。
8. 每条 finite word 只包含一个已经 correlation 的事务/timer/lease generation，触发 AP 至多出现一次。并发或重启必须新建 monitor 实例，或用明确的 `superseded/cancelled` AP 结束旧 generation；原因和回归证据见 `semantic_exclusions.md`。
9. `source_url` 必须同时包含声明的 repository、40 位 commit 和 source path；源码主 hook 必须落在该符号范围内，辅助 hook 也使用固定 commit permalink。

不满足上述任一项的候选进入该协议的 `excluded_properties.md`，注明 `NO_PUBLIC_NORMATIVE_TEXT`、`NO_NUMERIC_BOUND`、`PUNCTUAL_ONLY`、`NO_FIXED_SOURCE_MAP`、`VERSION_MISMATCH`、`FORMULA_UNSUPPORTED`、`TRACE_NOT_DECISIVE` 或 `DUPLICATE_OBLIGATION`。

## Staging JSON

每个 `proposals.json` 是对象数组；每个对象应至少包含：

```json
{
  "id": "COAP-TX-01",
  "protocol": "CoAP",
  "protocol_extension": "RFC 7252 core",
  "title": "...",
  "category": "...",
  "natural_language": "...",
  "normative_strength": "MUST",
  "standard": "RFC 7252",
  "standard_version": "RFC 7252",
  "standard_section": "4.2",
  "standard_url": "https://...",
  "standard_excerpt": "short excerpt",
  "time_value_ms": "2000",
  "time_parameter": "ACK_TIMEOUT",
  "time_source": "RFC default",
  "instantiation_basis": "NORMATIVE_DEFAULT",
  "mathematical_mitl": "...",
  "mightyppl_formula": "...",
  "atomic_propositions": ["..."],
  "ap_definitions": {"ap": "precise event predicate"},
  "correlation_key": "...",
  "projection_rule": "correlate first, then project one transaction/session",
  "source_repository": "owner/repo",
  "source_commit": "40 hexadecimal characters",
  "source_path": "path/in/repo.c",
  "source_symbol": "symbol",
  "source_lines": "100-130",
  "source_url": "https://github.com/.../blob/<commit>/...#L100-L130",
  "instrumentation_timing": "...",
  "observability": "BLACKBOX|WHITEBOX|HYBRID",
  "oracle_value": "HIGH|MEDIUM",
  "triggerability": "HIGH|MEDIUM|LOW",
  "confidence": "HIGH|MEDIUM",
  "positive_trace": [{"time": 0, "props": ["..."]}],
  "negative_trace": [{"time": 0, "props": ["..."]}],
  "additional_negative_traces": {"negative_late_or_missing": [{"time": 0, "props": ["..."]}]},
  "monitor_instantiation": "one correlated obligation generation per timed word",
  "independent_audit_status": "APPROVE|FIXED_AFTER_AUDIT|APPROVE_WITH_CAVEAT|REJECT_OR_FIX",
  "review_question": "...",
  "limitations": "..."
}
```

## 输出目录

最终目录为 `protocols/<slug>/`。每个协议至少包含：

- `mitl_property_catalog.md`
- `mitl_property_catalog.csv`
- `mitl_property_catalog.json`
- `atomic_proposition_map.json` / `atomic_proposition_map.yaml`
- `instrumentation_hooks.csv`（逐 AP 的事件谓词、correlation、固定源码和插桩时机）
- `evidence_manifest.json` / `evidence_manifest.yaml`
- `excluded_properties.md`
- `formula_validation_summary.csv`
- `validation/<property-id>/...`

根目录另生成全部协议索引、合并 CSV/JSON、协议覆盖矩阵和可复现 manifest。
