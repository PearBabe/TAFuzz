# 独立审计状态汇总

该表描述最终准入卡片的审计状态；`PENDING` 人工签字仍是另一道门。

| 状态 | 准入条数 |
|---|---:|
| `APPROVE` | 8 |
| `APPROVE_WITH_CAVEAT` | 1 |
| `FIXED_AFTER_AUDIT` | 58 |
| `ROOT_REVIEWED` | 9 |
| `ROOT_REVIEWED_PROFILE` | 2 |
| `ROOT_REVIEWED_WITH_ADAPTER_CAVEAT` | 1 |
| `ROOT_REVIEWED_WITH_CAVEAT` | 1 |

## 被独立审计否决的候选

- `TLS13-TICKET-01`（TLS）：Rejected and deliberately left without fabricated AP mappings: the fixed source observes PSK eligibility but does not expose a transition proving seven-day cache removal/non-use; tls13_ticket_became_unusable was adapter-derived and self-fulfilling, and tls13_ticket_removed lacks a fixed cache-eviction hook.
- `DTLS12-FINAL-01`（DTLS）：Rejected and deliberately left without fabricated AP mappings: rec_layer_d1.c proves a repeated-Finished retransmission path, but the locked implementation source does not prove that the final-flight buffer is retained for 240000 ms, and the same-position formula invented an unsupported zero-delay response bound.
- `SIP-TX-02`（SIP）：Duplicates SIP-TX-01 and invents an unsupported exact callback-to-send latency.
- `SIP-TX-08`（SIP）：Duplicates SIP-TX-07 and invents an unsupported exact callback-to-send latency.
- `SIP-TX-14`（SIP）：Duplicates SIP-TX-13 and invents an unsupported exact callback-to-send latency.

## 审计报告

- `../_audit/transport_security_audit.md`
- `../_audit/industrial_audit.md`
- `../_audit/smtp_audit.md`
- `../_audit/sip_catalog_audit.md`
- `../semantic_exclusions.md`（重叠触发回归与接入契约）
