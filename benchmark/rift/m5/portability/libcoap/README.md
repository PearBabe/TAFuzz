# libcoap RIFT-M5 portability probe

Status: **FAILED_IDENTITY_DRIFT_AND_RESOURCE_LIMIT**.

This directory tests the real 38-translation-unit libcoap build and the frozen
`COAP-TX-01` formula without adding libcoap names, paths, property IDs, or
answer edges to RIFT's generic core. It is an engineering portability probe,
not a real-project gold benchmark.

## Inputs and portability boundary

- `derive_property.py` preserves the frozen M4 MITL formula and selector
  groups, then adds 11 typed source occurrences needed by M5's predicate
  sidecar. `property_ir.json` is its deterministic output.
- `model_pack.json` is a property-independent project adapter for five public
  libcoap API arguments. Project knowledge stays outside the analyzer core.
- `executor_capabilities.json` deliberately marks every capability
  `UNKNOWN`. The probe contains no certified replay harness, so it does not
  turn a public API signature into an unsupported actionable claim.
- The generic POSIX LP64 model pack is also supplied unchanged.

All three local inputs pass their closed production schemas. The fixed build
still passes the M4 deep acceptance gate (`246` checks) and has compile-DB SHA
`3bf8dfee...f30bc3a` with 38 TUs.

## Observed final run

The `recipes` command launched from analyzer bytes with pre-run SHA
`a299c793...c72c76`, under a 1,800-second wall timeout and 12 GiB address-space
limit. It failed before atomic publication:

```text
exit=1
wall_seconds=417.76
peak_rss_kib=12211160
FAIL: std::bad_alloc
```

Consequently there is no trustworthy occurrence/frontier/recipe count and no
M5 certificate. The detached verifier was still invoked; it correctly failed
because `m5_analysis_certificate.json` did not exist. The analyzer's atomic
stager left no partial result bundle.

The live build path was also rebuilt concurrently: its post-run SHA is
`dbef650a...3370d97`, and no digest-named snapshot of the pre-run bytes was
made. This run therefore fails both the resource gate and exact physical
identity replay. A retry must first copy the analyzer to a digest-named path
and then invoke that immutable snapshot.

## Claim boundary

No accuracy, recall, actionable precision, mutation-direction accuracy, or
fuzz-effectiveness metric is reported. Real libcoap labels still require two
independent humans and arbitration. The only defensible conclusion is that
this analyzer build did **not** pass the M5 libcoap portability/performance
gate; it also misses the pre-registered `<=60 s / <=2 GiB` target by a wide
margin.

Exact commands, hashes, resource receipts, and the failed verifier report are
recorded in `result_manifest.json` and `final/`. The read-only localization in
`final/failure_localization.md` places the failure before the first semantic
index artifact publication, most likely in full JSON materialization.
