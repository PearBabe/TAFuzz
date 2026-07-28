# Modbus/TCP excluded candidates

The official V1.0b guide states in §4.4.1.4 that no required transaction response time is specified. Therefore this protocol contributes zero normative numeric MITL cards after independent audit.

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| MODBUS-TCP-01 full confirmation within 500 ms | `REJECT_OR_FIX` | `NO_PROTOCOL_BOUND_AND_INCORRECT_IMPLEMENTATION_ORACLE` | 500 ms is a libmodbus default, not a protocol value; response_timeout governs the initial read and byte_timeout is reloaded for remaining chunks, so full confirmation may exceed 500 ms. | Split into initial-response and per-byte implementation profiles and keep them outside the normative main catalogue. |
| Universal MODBUS/TCP response deadline | `KEEP_EXCLUDED` | `NO_NUMERIC_BOUND` | §4.4.1.4 deliberately defines none. | A deployment-specific profile may be studied but cannot be generalized. |
| Universal retry deadline | `KEEP_EXCLUDED` | `NO_NUMERIC_BOUND` | The guide only requires a reasonable timeout based on expected transport delay. | Provide a locked deployment profile and mark it non-normative. |
| 500 ms byte-to-byte protocol timeout | `KEEP_EXCLUDED` | `IMPLEMENTATION_PROFILE_ONLY` | `_BYTE_TIMEOUT` is a libmodbus default with no Modbus/TCP normative requirement. | Keep only as a libmodbus appendix property. |
| 75 s TCP connect/keepalive/RTO properties | `KEEP_EXCLUDED` | `DUPLICATE_TRANSPORT_OBLIGATION` | These are TCP behavior, not Modbus application semantics. | Compare in the TCP catalogue, not here. |
| Server indication timeout | `KEEP_EXCLUDED` | `NO_FINITE_DEFAULT` | libmodbus leaves it unset and the guide provides no number. | Supply an explicit application profile. |

`MODBUS-TCP-01` is not emitted in `proposals.json` and is not counted toward catalogue size.
