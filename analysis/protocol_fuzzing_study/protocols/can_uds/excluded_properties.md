# CAN/UDS 排除与待修候选

## 研究阶段排除：_staging/industrial_protocols/can_uds/excluded.md

# CAN/UDS excluded candidates

Scope: public AUTOSAR R24-11 CAN-TP/DCM obligations instantiated on locked open-source profiles. Paid ISO-only text is not used as a normative anchor.

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| UDS-S3-02 valid TesterPresent restarts 5100 ms window | `REJECT_OR_FIX` | `DUPLICATE_OBLIGATION_AND_UNSUPPORTED_MULTI_CONNECTION` | Current formula is a logical subset of UDS-S3-01 and does not test the cited owner/foreign DcmDslConnection rule; iso14229 has no multi-connection model. | Use a multi-connection SUT and test that foreign TesterPresent does not reset the owner's S3 generation. |
| Universal N_Bs/N_Cr=1000 ms | `KEEP_EXCLUDED` | `NO_NORMATIVE_DEFAULT` | AUTOSAR makes both parameters configurable; 1000 ms belongs only to python-can-isotp. | Instantiate the active configuration and label the implementation profile. |
| Universal S3=5100 ms | `KEEP_EXCLUDED` | `IMPLEMENTATION_PROFILE_ONLY` | AUTOSAR's unoverwritten default is 5000 ms; 5100 ms is the locked iso14229 configuration. | Keep explicit profile trigger; never claim an AUTOSAR universal default. |
| ISO 15765/14229-wide restatement | `KEEP_EXCLUDED` | `NO_PUBLIC_NORMATIVE_TEXT_USED` | This evidence package intentionally uses public AUTOSAR clauses, not paid ISO text or third-party excerpts. | Obtain and independently review authorized primary ISO text. |
| TesterPresent on foreign connection | `DEFER_TO_V2` | `SUT_CAPABILITY_MISSING` | The locked SUT cannot represent multiple DcmDslConnections. | Select a multi-connection DCM or implement an independently reviewable ownership adapter. |

The emitted catalogue contains five cards; rejected UDS-S3-02 is not retained to satisfy a property count.

