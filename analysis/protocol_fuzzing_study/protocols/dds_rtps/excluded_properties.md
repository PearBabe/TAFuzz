# DDS/RTPS 排除与待修候选

## 研究阶段排除：_staging/industrial_protocols/dds_rtps/excluded.md

# DDS/RTPS excluded candidates

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| Exact physical participant deletion at 100 s | `REJECT_OR_FIX` | `NO_EXACT_REMOVAL_DEADLINE` | RTPS permits considering a participant gone after its lease and requires reconfiguration after that conclusion; it does not bound physical cleanup callback latency. | Use the retained no-early safety card, or supply a separate implementation scanner bound. |
| Stock Fast-DDS 200/500 ms response delays | `KEEP_EXCLUDED` | `PROFILE_MISMATCH` | Fast-DDS v3.3.0 stock delays are 5 ms; 200/500 ms are RTPS reference defaults selected by the harness. | Record explicit QoS/timing configuration in the experiment manifest. |
| Stock Fast-DDS 30 s SPDP period | `KEEP_EXCLUDED` | `PROFILE_MISMATCH` | Stock period is 3 s, not the RTPS 30 s reference setting. | Configure 30 s and verify the revised runtime attribute before trigger. |
| Infinite/default DDS QoS durations | `KEEP_EXCLUDED` | `NO_FINITE_BOUND` | Many DDS QoS durations are infinite or application-configured, so they do not yield a finite numeric MITL interval without a profile. | Supply a normative finite profile and observable source hooks. |
| Per-ReaderProxy Fast-DDS writer nack timer | `KEEP_EXCLUDED` | `IMPLEMENTATION_MODEL_MISMATCH` | Fast-DDS uses a writer-wide timer affected by multiple readers. | Use writer GUID + timer generation + pending reader set, as in the repaired card. |
| Dependent CycloneDDS participant exact expiry | `KEEP_EXCLUDED` | `NORMATIVE_EXCEPTION` | Privileged-participant dependency may postpone handling by 200 ms. | Exclude dependency cases or model the dependency as a separate property. |

All five emitted cards are `FIXED_AFTER_AUDIT` and still require human review; none is silently upgraded to independently approved.

