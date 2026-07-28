# SMTP 排除与待修候选

## 研究阶段排除：_staging/ietf_app_protocols/smtp/excluded.md

# SMTP excluded candidates

The seven distinct numeric phase minima in RFC 5321 §4.5.3.2 are admitted as lower-bound properties. They are not mechanically duplicated constants: each has a separate protocol phase and source hook.

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Exact timeout at the RFC minimum | `OVERSTRONG_FORMULA` | RFC 5321 says the values SHOULD be minimums; a client may wait longer. Main formulas therefore prohibit early timeout only. |
| Whole-message transaction timeout | `NO_NUMERIC_BOUND` | RFC requires per-command and per-buffer timers and intentionally makes total duration proportional to message size. |
| Retry schedule after temporary failure | `CONTEXT_DEPENDENT_SOFT_GUIDANCE` | RFC 5321 §4.5.4.1 gives an “in general” SHOULD-level retry interval of at least 30 minutes and a looser 4–5 day give-up recommendation, but explicitly permits reason-aware variable strategies. Exim 4.89's default rule begins at 15 minutes. Without an adapter predicate proving the generic-policy context, 1800000 ms is not an unconditional protocol oracle. |
| Exim connect_timeout as SMTP property | `DUPLICATE_OBLIGATION` | TCP connection establishment belongs to the TCP catalog, not an SMTP response phase. |

## Role and benchmark boundary

- `SMTP-TIMEOUT-01`–`06` describe Exim's outbound SMTP-client transport. The pinned ProFuzzBench Exim campaign starts an inbound TCP/25 server, so those six properties are protocol-catalog entries but are not reachable in that server harness without a separate outbound-client harness.
- `SMTP-TIMEOUT-07` is limited to the pinned plaintext Exim-server profile. STARTTLS requires separate fixed-source timer hooks.
- The real bounds are 2–10 minutes. They remain valid offline/long-trace or virtual-time oracles, but their wall-clock triggerability is `LOW`; the RFC constants are not scaled down for throughput.

