# Candidate 431540b8 resource-failure localization

This diagnostic run was externally terminated after it had definitively
failed the registered libcoap resource gate. It did **not** exit on its own.

The immutable analyzer completed index, model-overlay, predicate-occurrence,
graph, and cone staging. RSS was 1,479,780 KiB at `cones-staged`; it then grew
monotonically during frontier computation to a measured peak of 11,848,420
KiB without emitting `frontier-staged`. At 417.05 seconds it received SIGTERM
to avoid a system-level out-of-memory event.

The defensible localization is therefore:

```text
last completed: cones-staged
resource-growth phase: frontier computation/materialization
terminal label: TERMINATED_AFTER_DEFINITIVE_RESOURCE_GATE_FAILURE
```

This is a performance diagnostic, not an analyzer-crash claim and not a final
M5 seal. The detached verifier was invoked and failed because no atomic M5
certificate existed. No semantic or actionable-accuracy claim is made.
