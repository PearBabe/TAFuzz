# RFC7252 Candidate Rules

本文件记录 RFC7252 候选规则筛选结果。主库只保留适合 MITL runtime monitoring 的核心传输/匹配性质，并且以有明确时间边界的性质为主。

## 原始扫描

- 扫描文件：`/home/lqq/project/TAFuzz/coap_rfc_dataset/rfc_dataset/rfc7252/rfc7252.txt`
- 扫描范围：RFC7252 全文，重点复核 3、4、5、8、9 章中含 `MUST`、`MUST NOT`、`SHOULD`、`MAY` 且涉及 CoAP message/request/response/endpoint/token/timer/state 的段落。
- 原始命中段落：119
- 人工归并后候选：31
- 进入主 MITL：13
- 进入 SHOULD soft：2
- rejected/deferred/merged：16

## Accepted Main Properties

| ID | RFC section | keyword | decision | reason |
|---|---|---|---|---|
| RFC7252-MITL-001 | 4.2, 4.8 | MUST | accepted | CON 初始 timeout 有 RFC 参数边界，适合 timer/state 监控。 |
| RFC7252-MITL-002 | 4.2 | MUST | accepted | timeout 触发后的 counter、重传、timeout doubled 是同一步状态演化。 |
| RFC7252-MITL-003 | 4.2, 4.8.2 | MUST | accepted | `MAX_TRANSMIT_SPAN` 给出重传序列包络。 |
| RFC7252-MITL-004 | 4.2, 4.8.2 | MUST | accepted | `MAX_TRANSMIT_WAIT` 给出放弃 ACK/RST 的最大等待。 |
| RFC7252-MITL-005 | 4.4, 4.8.2 | MUST NOT | accepted | `EXCHANGE_LIFETIME` 内 MID 复用禁止是典型 bounded persistence。 |
| RFC7252-MITL-006 | 4.4 | MUST | accepted | ACK/RST matching 是即时字段/endpoint 匹配性质。 |
| RFC7252-MITL-007 | 4.2 | MUST NOT | accepted | ACK/RST closure 是即时 forbidden behavior。 |
| RFC7252-MITL-008 | 4.3 | MUST NOT | accepted | NON 不得被 ACK 是即时 forbidden behavior。 |
| RFC7252-MITL-009 | 4.7 | MUST | accepted | `NSTART` 是持续状态上限，可在 state-change 点即时检查。 |
| RFC7252-MITL-010 | 4.7, 4.8.2 | normative statement | accepted | `EXCHANGE_LIFETIME` 后停止期待 response，有明确 lifetime。 |
| RFC7252-MITL-011 | 5.3.1, 5.3.2 | MUST | accepted | token echo、endpoint 和 piggybacked MID 匹配是即时 matching。 |
| RFC7252-MITL-012 | 5.2.2 | MUST NOT/MUST | accepted | Empty ACK 后 separate response 保持 separate；无界但核心且可监控。 |
| RFC7252-MITL-013 | 5.2.2 | MUST | accepted | Confirmable separate response 收到 matching ACK/RST 后必须停止重传，是即时终止性质。 |

## SHOULD Soft Properties

| candidate | RFC section | keyword | decision | reason |
|---|---|---|---|---|
| duplicate CON handling | 4.5 | SHOULD/MAY relax | soft | 在 `EXCHANGE_LIFETIME` 内有时间窗口，但 RFC 明确可因幂等/应用语义放宽。 |
| duplicate NON handling | 4.5 | SHOULD/MAY relax | soft | 在 `NON_LIFETIME` 内有时间窗口，但 RFC 明确可根据 message semantics 放宽。 |

## Rejected Or Deferred

| candidate | RFC section | decision | reason |
|---|---|---|---|
| Version must be 1 / unknown ignored | 3 | rejected | 字段格式/解析规则，不强行转换成 MITL。 |
| TKL 9-15 reserved | 3 | rejected | 字段格式规则，不是核心时序性质。 |
| payload marker followed by zero-length payload | 3 | rejected | message format error，非 MITL 时序性质。 |
| Empty message field constraints | 4.1 | rejected | 字段格式规则。 |
| ICMP error give-up | 4.2 | deferred | RFC 使用 MAY/SHOULD，且依赖 UDP API 能否提供原始 datagram 信息。 |
| Message size fit | 4.6 | rejected | SHOULD 和传输环境相关，不是第一批核心 MITL。 |
| `PROBING_RATE` average data rate | 4.7 | deferred | 有参数但平均速率统计窗口和 stop-expecting 算法未由 RFC 固定。 |
| parameter configuration constraints | 4.8.1 | deferred | 配置层性质，需应用环境/harness 决策。 |
| responder retain ACK state despite separate response | 4.2 | merged/deferred | 与 duplicate CON/Empty ACK separate response 相关；需要 request terminal horizon，暂不独立进主库。 |
| unknown critical/elective options | 5.4.1 | rejected | option 解析/错误响应规则，非当前核心 MITL。 |
| non-repeatable options | 5.4.5 | rejected | 字段/option multiplicity 规则。 |
| payload not allowed for code | 5.5 | rejected | payload/code 规则，不是时序核心。 |
| Max-Age freshness/cache | 5.6, 5.10.5 | deferred | 有时间但属于 cache/proxy 语义，当前严格核心范围外。 |
| proxy Max-Age not extended | 5.7.1 | deferred | proxy/cache 算术性质，当前严格核心范围外。 |
| conditional request precondition failed | 5.10.8 | rejected | method/resource semantic，不是传输/匹配核心。 |
| multicast messaging/request-response | 8 | deferred | 当前严格核心范围外，且包含 leisure/DEFAULT_LEISURE 选择。 |
| DTLS session/epoch matching | 9.1 | deferred | security/DTLS 绑定，当前阶段排除。 |

## Candidate Count

- accepted main：13
- soft：2
- rejected/deferred/merged：16
- total：31
