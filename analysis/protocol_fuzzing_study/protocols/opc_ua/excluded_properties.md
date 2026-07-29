# OPC UA 排除与待修候选

## 研究阶段排除：_staging/industrial_protocols/opc_ua/excluded.md

# OPC UA excluded candidates

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| Renewal exactly at 75% | `REJECT_OR_FIX` | `OVERSTRONG_EXACT_BOUNDARY` | OPC 10000-4 says request after 75%; it does not require the request at the exact 75% instant. | Use the repaired [75%,100%) profile interval and preserve SHOULD strength. |
| Requested timeout/count treated as revised | `KEEP_EXCLUDED` | `NEGOTIATION_IGNORED` | Server may revise Session and Subscription parameters. | Trigger only on the returned revised value, as the repaired cards do. |
| Session cleanup callback exactly at timeout | `KEEP_EXCLUDED` | `DEADLINE_CALLBACK_CONFLATION` | The normative maximum and periodic cleanup callback are different observations. | Preserve the deadline oracle and record callback latency separately without invented epsilon. |
| Subscription generation without queue/close/reset cancellation | `KEEP_EXCLUDED` | `MISSING_PROTOCOL_EXCEPTION` | Queue loss, normal close, re-enable, transfer/deletion, or setting change can end a generation. | Use explicit cancellation APs and one trigger per projected word. |
| Disabled keep-alive timing as a duplicate standalone card | `KEEP_EXCLUDED` | `DUPLICATE_OBLIGATION` | Its timing half shares SUB-02; the distinct retained value is no notifications while disabled. | Keep disabled safety explicit and state the shared counter semantics. |
| timeoutHint exact cancellation at 5000 ms | `KEEP_EXCLUDED` | `HINT_NOT_DEADLINE` | timeoutHint permits cancellation only after waiting at least the hint; it does not require eventual cancellation. | Retain only OPCUA-PUB-01 no-early safety. |

Eight cards are emitted: two independently approved with caveats and six `FIXED_AFTER_AUDIT` cards awaiting human review.

