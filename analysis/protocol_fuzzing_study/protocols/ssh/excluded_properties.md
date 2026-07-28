# SSH 排除与待修候选

## 研究阶段排除：_staging/transport_security_protocols/ssh/excluded.md

# SSH excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Rekey after 1 GB | `FORMULA_UNSUPPORTED` | RFC 4253's alternative threshold is byte-count based, not elapsed time. |
| Key-exchange completion timeout | `NO_NUMERIC_BOUND` | RFC 4253 does not assign a numeric KEX completion deadline. |
| ServerAliveInterval/ClientAliveInterval | `NO_PUBLIC_NORMATIVE_TEXT` | These are OpenSSH implementation options, not SSH transport protocol constants. |
| Identification-string exchange timeout | `NO_NUMERIC_BOUND` | RFC 4253 specifies order/format but not a numeric timeout. |
| Authentication timeout | `NO_PUBLIC_NORMATIVE_TEXT` | LoginGraceTime is an OpenSSH server policy, not a transport-layer RFC 4253 timer. |

