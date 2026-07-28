# Kamailio baseline comparison plan

Primary comparable target: ProfuzzBench SIP/Kamailio at commit `8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074`, which pins Kamailio `2648eb3`.

## Two required experiment profiles

### PFB-COMPAT

Use the original ProfuzzBench subject without restoring timer children.  This profile is for coverage/throughput comparison with public artifacts only.  It must not be used to claim RFC timer-expiry conformance because `kamailio.patch` disables the main and slow timer processes and the fuzzer run kills the SUT after short testcases.

### MITL-VALID

Keep the same Kamailio commit but use a reference profile that restores timer behavior, fixes the route script/peer behavior needed by the selected properties, and records the same ProtocolEvent stream for every fuzzer.  This profile is for MITL violation/time-to-first-violation claims.

## Baselines

1. AFLNet through ProfuzzBench SIP/Kamailio.  Subject README runs 4 AFLNet instances for 3600 s and 5 repeats with `-P SIP -l 5061 -D 50000 -q 3 -s 3 -E -K`.
2. AFLnwe through the same ProfuzzBench subject as the no-state-feedback control.
3. StateAFL through `Dockerfile-stateafl` in the same subject.  It is a same-SUT public state-feedback baseline, but its original Kamailio state signal is weak and should not be described as a strong protocol-state oracle.
4. NSFuzz is the preferred third advanced baseline if the official artifact can be audited locally: it reports the same Kamailio `2648eb3` line and has public Kamailio scripts/images, but the large image must be downloaded and hashed before being promoted from `CONDITIONAL`.
5. ChatAFL is a backup/appendix baseline: it has Kamailio scripts but uses a different Kamailio commit, depends on external LLM behavior, and also disables timers in its compatibility setup.
6. SGFuzz should be excluded from the main comparison unless a new adapter is built and disclosed; its public setup does not provide a Kamailio/SIP UDP/fork-compatible path.

## Common experiment contract

- Same Kamailio commit, ProfuzzBench patch, seeds, reset script, UDP endpoint, timeout, hardware, and coverage collector.
- For MITL-VALID, the same reference timer patch/profile, route script, peer, reset, and ProtocolEvent collector must be used by all tools.
- Metrics: edge/branch coverage, protocol state/transition coverage, automaton state/edge coverage, unique MITL violation, unique crash, sanitizer finding, time-to-first, exec/s, monitor overhead.
- Ablations: no MITL, boolean verdict only, automaton coverage, PTA cost-to-go only, full TAFuzz.
- Pilot: 10% of full campaign time, 3 repeats, debugging only.  Full budget should follow the newest complete artifact using this same SUT.
- Statistics: median, IQR, bootstrap 95% CI, Mann-Whitney U with Holm correction, Vargha-Delaney A12.

## Fairness caveats

- Run the MITL oracle offline for all tools, not only TAFuzz, otherwise inputs that violate a property but do not increase ordinary coverage will be undercounted for baselines.
- AFLNet's SIP framing in the public fork recognizes only a small method subset; MITL-VALID should use a unified SIP start-line/header/Content-Length framer for every tool.
- StateAFL/NSFuzz state counts are not directly comparable to MITL automaton-state coverage; report them in separate columns.
