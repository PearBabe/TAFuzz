# TAFuzz State Archive: Pre-ADGFuzz Deep Read

Archived on 2026-07-17 before compacting the active handoff after the complete
ADGFuzz paper/code review. Detailed command chronology remains in
`.codex/SESSION_LOG.md`; this file preserves the prior active direction.

## Prior Immediate Focus

- Treat specification-derived MITL conformance properties as TAFuzz's primary
  oracle layer.
- Use PGFuzz as a policy/MTL robotic-vehicle baseline and ADGFuzz as a
  complementary implementation-derived input-grouping baseline.
- Prepare a minimal PGFuzz/ArduPilot SITL smoke test after stabilizing its old
  Python/GUI environment.

## Stable Decisions

- A retained high-quality property requires a mandatory normative source,
  ordered timed workflow, fuzzer controllability, external/internal
  observability, meaningful consequence, and stable reproducibility.
- Correlation IDs and dynamic timers require scoped monitor instances and
  per-run parameter instantiation.
- Random-window conformance and distributional randomness are separate
  questions.
- A formula violation alone is weak evidence; retained results should show a
  reproducible protocol/system consequence where possible.
- The existing TAMonitor/PTA backend is protected and should be reused, not
  reimplemented.

## Prior Benchmark Ranking

- Strong candidates: CoAP, SIP, SOME/IP-SD, DDS/RTPS, OPC UA Subscription,
  DHCPv6, and TFTP.
- Conditional candidates: MQTT QoS 2, QUIC, BFD/VRRP, and selected mDNS rules.
- RFC 7252/libcoap remains the preferred first front-end closure target.

## Existing Artifacts

- `analysis/zotero_fuzz_literature_analysis_zh.md`
- `analysis/mitl_host_protocol_candidates_zh.md`
- `analysis/pgfuzz_paper_code_deployment_zh.md`
- `analysis/protocol_fuzzing_study/rfc7252_libcoap_mitl_review/`
- `documents/TAFuzz_MITL_CCFA_design.md`
- `documents/TAFuzz_MITL_implementation_plan.md`

## Environment Notes

- `baseline/pgfuzz` is an independent Git repository at commit `7eaebf2`.
- `baseline/ADGFuzz` is an independent Git repository.
- Conda environment `/home/lqq/anaconda3/envs/adg` uses Python 3.8.20 after
  installing wxPython and imports the pinned ADGFuzz dependencies.
- WSLg and the system-Python MAVProxy/wx path were verified, but an existing
  pre-fix SITL session needed restart to use the corrected interpreter.

## Prior Risks

- The 13 RFC 7252 properties had structural validation but still required a
  stricter consequence/provenance re-audit.
- PGFuzz has substantial reproducibility debt: Python 2 assumptions, old
  simulator stack, GUI terminal use, fixed sleeps, and incomplete artifact
  components.
- ADGFuzz's PGFuzz comparison is based on published reports rather than a
  controlled same-version rerun.

## Why The Active State Changed

The new deep review established that ADGFuzz has no compiler-grade static
analysis, source instrumentation, automatic property extraction, seed corpus,
or online coverage/state feedback. Its transferable contribution is the
organization of implementation-derived dependency groups into structured
input subspaces. The active work therefore moves from a flight-control
baseline smoke toward closing TAFuzz's RFC property → scoped AP → Clang/LLVM
binding → selective instrumentation → TAMonitor loop before adding scheduling.
