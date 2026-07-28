# RFC7252 MITL Property Dataset

状态：RFC 审计版数据集草案。当前阶段只覆盖 RFC7252 到 MITL 性质库，不做 libcoap 函数级依赖分析、LLVM 插桩、fuzzing 或 runtime monitor。

## 扫描范围

- RFC：RFC7252 "The Constrained Application Protocol (CoAP)"
- 本地文本：`/home/lqq/project/TAFuzz/coap_rfc_dataset/rfc_dataset/rfc7252/rfc7252.txt`
- 重点章节：4.2、4.3、4.4、4.5、4.7、4.8、5.2.2、5.3.1、5.3.2
- 重点行为：CON/NON/ACK/RST、重传、timeout、Message ID、Token、request/response matching、duplicate detection、NSTART、endpoint state

## 产物概览

- RFC 规范词原始扫描段落：119
- 候选规则总数：31
- 主 MITL 性质：13
- SHOULD 软性质：2
- Rejected/deferred/merged 规则：16
- 有明确时间边界的主性质：12/13
- 无界但保留的核心顺序性质：1/13

## 时间参数原则

MITL 公式保留 RFC7252 符号参数，不把公式简化成固定秒数。默认值只用于审阅和后续实例化参考。

| 参数 | RFC 默认值 | 用途 |
|---|---:|---|
| `ACK_TIMEOUT` | 2 seconds | CON 初始 timeout、最小重传间隔、`PROCESSING_DELAY` |
| `ACK_RANDOM_FACTOR` | 1.5 | 初始 timeout 上界 |
| `MAX_RETRANSMIT` | 4 | CON 最大重传次数 |
| `NSTART` | 1 | 同一 server 的 outstanding interaction 上限 |
| `MAX_TRANSMIT_SPAN` | 45 seconds | CON 首次发送到最后一次重传的包络 |
| `MAX_TRANSMIT_WAIT` | 93 seconds | CON 首次发送到放弃 ACK/RST 的最大等待 |
| `EXCHANGE_LIFETIME` | 247 seconds | ACK/RST 期待、MID 复用、CON 去重窗口 |
| `NON_LIFETIME` | 145 seconds | NON 去重与 MID 复用窗口 |

## 性质分类表

| ID | RFC Section | Type | MITL | Future Mapping |
|---|---|---|---|---|
| RFC7252-MITL-001 | 4.2, 4.8 | timed_retry | 初始 CON timeout 与首次重传窗口 | timer, state, function event |
| RFC7252-MITL-002 | 4.2 | immediate_bounded | timeout 后重传、counter 递增、timeout doubled | timer, state, data structure |
| RFC7252-MITL-003 | 4.2, 4.8.2 | timed_forbidden | `MAX_TRANSMIT_SPAN` 后不得再重传 | timer, state, function event |
| RFC7252-MITL-004 | 4.2, 4.8.2 | timed_terminal | `MAX_TRANSMIT_WAIT` 内终止 CON 尝试 | timer, state, function event |
| RFC7252-MITL-005 | 4.4, 4.8.2 | lifetime_state | `EXCHANGE_LIFETIME` 内不得复用 MID | message field, state |
| RFC7252-MITL-006 | 4.4 | immediate_matching | ACK/RST 必须按 MID 和 endpoint 匹配 | message field, endpoint state |
| RFC7252-MITL-007 | 4.2 | immediate_forbidden | ACK/RST 不得引发 ACK/RST 响应 | message field, function event |
| RFC7252-MITL-008 | 4.3 | immediate_forbidden | NON 不得被 ACK | message field, function event |
| RFC7252-MITL-009 | 4.7 | immediate_state | outstanding interaction 不得超过 `NSTART` | internal state, data structure |
| RFC7252-MITL-010 | 4.7, 4.8.2 | timed_state | 未 ACK 的 CON request 在 `EXCHANGE_LIFETIME` 后停止期待响应 | timer, state |
| RFC7252-MITL-011 | 5.3.1, 5.3.2 | immediate_matching | response token echo 与 endpoint/MID 匹配 | message field, endpoint state |
| RFC7252-MITL-012 | 5.2.2 | unbounded_order_core | Empty ACK 后 separate response 保持 separate | state, function event |
| RFC7252-MITL-013 | 5.2.2 | immediate_terminal | matching ACK/RST 后停止重传 Confirmable response | message field, state, function event |

## 被拒绝或暂缓的规则

字段格式类规则、Max-Age/cache、proxy、multicast、DTLS/security、option/payload 规则不进入主库。它们记录在 `RFC7252_candidate_rules.md`，原因包括：不是时序性质、不是第一阶段核心范围、规范词为 `SHOULD/MAY`、或需要后续 libcoap/harness 选择后才能判定。

## 文件说明

- `properties/property_*.yaml`：主 MITL 性质，每条一个文件。
- `property_summary.csv`：主性质机器可读摘要。
- `RFC7252_candidate_rules.md`：accepted/soft/rejected/deferred 候选规则审计。
- `property_review.md`：逐条 RFC 真实性、MITL 正确性、可监控性、后续实现价值复核。
