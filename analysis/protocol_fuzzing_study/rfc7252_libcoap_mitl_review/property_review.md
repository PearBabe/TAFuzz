# RFC7252 MITL Property Review

## 审核结论

- 主性质 13 条，其中 12 条具有明确 metric interval 或 `[0,0]` 即时边界。
- 无界性质 1 条：`RFC7252-MITL-012`，保留原因是 Empty ACK 后 separate response 保持 separate 是 RFC7252 request/response 核心顺序义务。
- duplicate CON/NON 保留为 SHOULD 软性质，不进入主 verdict 库。
- Max-Age/proxy/cache/multicast/DTLS/security/纯字段格式规则全部 rejected/deferred。

## 逐条审查

| ID | RFC 真实性 | MITL 正确性 | 可监控性 | 后续实现价值 |
|---|---|---|---|---|
| RFC7252-MITL-001 | 4.2/4.8 行号明确；timeout 参数来自 RFC 表 | 用符号参数表达初始窗口；不写固定秒数 | 需要 timer schedule/fire 与 CON queue AP | 高 |
| RFC7252-MITL-002 | 4.2 明确 counter、重传、timeout doubled | timeout 后状态转移为 `[0,0]` 即时检查 | 需要 counter、timeout、queue node AP | 高 |
| RFC7252-MITL-003 | 4.2/4.8.2 明确 `MAX_TRANSMIT_SPAN` | after span 禁止同一 exchange 重传 | 需要 retransmit event 与 exchange key | 高 |
| RFC7252-MITL-004 | 4.2/4.8.2 明确 `MAX_TRANSMIT_WAIT` | 终止事件包含 ACK/RST/cancel/failure | 需区分 application cancel 与 failure | 中 |
| RFC7252-MITL-005 | 4.4 明确 MID 复用禁止 | bounded persistence 使用 `EXCHANGE_LIFETIME` | 需要 outgoing MID history | 高 |
| RFC7252-MITL-006 | 4.4 明确 ACK/RST matching 条件 | `[0,0]` 字段/endpoint 匹配 | 需要 inbound ACK/RST 与 prior sent message table | 高 |
| RFC7252-MITL-007 | 4.2 明确 ACK/RST closure | forbidden response 用 `[0,0]` | 需要 recv/send event 关联 | 高 |
| RFC7252-MITL-008 | 4.3 明确 NON 不被 ACK | forbidden ACK 用 `[0,0]` | 需要 inbound NON 与 outgoing ACK AP | 高 |
| RFC7252-MITL-009 | 4.7 明确 `NSTART` 上限 | state-change 点即时检查 `<= NSTART` | 需要 outstanding counter AP | 高 |
| RFC7252-MITL-010 | 4.7 明确 `EXCHANGE_LIFETIME` 后停止期待 | timed state persistence | 需要 client expectation state AP | 中 |
| RFC7252-MITL-011 | 5.3.1/5.3.2 明确 token/endpoint/MID matching | response step 即时匹配 | 需要 request table 与 response attrs | 高 |
| RFC7252-MITL-012 | 5.2.2 明确 Empty ACK 后禁止 piggyback | 无界顺序，非主体但核心 | 需要 same-request correlation | 中 |
| RFC7252-MITL-013 | 5.2.2 明确 matching ACK/RST 后停止重传 | `[0,0]` 终止 confirmable response retransmission | 需要 response retransmit state 与 ACK/RST matching | 高 |

## 审核检查项

### RFC 真实性

- 每条主性质均记录 RFC7252 本地文件路径、section 和行号。
- 本轮从 RFC7252 全文重新扫描到 119 个相关规范词段落，再人工归并为 candidate/soft/rejected/deferred。
- `original_requirement` 不复制长段落；完整 RFC 原文由行号回查。
- 时间参数均来自 RFC7252 4.8/4.8.2。

### MITL 正确性

- 有界公式不使用自造常数。
- `ACK_TIMEOUT`、`ACK_RANDOM_FACTOR`、`MAX_RETRANSMIT`、`MAX_TRANSMIT_SPAN`、`MAX_TRANSMIT_WAIT`、`EXCHANGE_LIFETIME`、`NON_LIFETIME`、`NSTART` 保持符号形式。
- `[0,0]` 只用于同一接收/发送/状态更新步骤的即时约束。

### 可监控性

- AP 均包含语义、字段/状态依赖和未来映射类别。
- correlation key 避免“最近一个 CON”这种不可靠关联。
- 需要后续实现保存 per-session/per-peer history。

### 后续实现价值

- 主性质覆盖 CON/NON/ACK/RST、重传、MID、Token、NSTART、separate response。
- 这些性质可自然进入下一阶段：MITL -> libcoap dependency mapping。
- 当前文件不绑定具体 libcoap 函数，避免过早实现假设。
