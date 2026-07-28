# RIFT-M5 120-case evaluation gates

`evaluate_m5.py` separates a successful sealed analysis run from a successful
evaluation.  A run can be byte-complete and independently verified while the
evaluation is `GATE_FAIL`.

## Modes

- Default (`STANDARD`) validates the sealed run, opens the private oracle only
  after validation, and enforces the preregistered gates.
- `--formal` additionally requires an external `run_manifest.json` SHA-256 and
  a passing serial-versus-parallel determinism gate.  Thresholds are fixed and
  have no CLI override.
- `--development` performs the same validation and reports every metric plus
  every would-fail gate, but returns `DEVELOPMENT_ONLY` rather than claiming
  `PASS` or enforcing the thresholds.

Formal and development modes are mutually exclusive.  Formal `GATE_FAIL` is
written to the requested JSON output and returns process exit code 2.  Seal,
manifest, oracle, or verifier failures return process exit code 1.

## Fixed gates

| Gate | Threshold | UNKNOWN treatment |
|---|---:|---|
| Gold fuzzable-source recall | >= 0.95 | Separate count; remains in the gold denominator |
| Critical/MUST influencer recall | = 1.00 | Separate from FN and TP; remains in the gold denominator |
| Supported-expression mutation direction accuracy | >= 0.90 | Separate count; scored wrong end-to-end, so abstention cannot inflate accuracy |

The direction subset uses a frozen, deliberately narrow adapter from the
mechanical oracle's legacy free-text recipe kinds to the structured direction
enum.  Unsupported event-order and non-monotone expressions are excluded from
the denominator; supported expressions that produce `UNKNOWN` are not.

## Reporting-only structured metrics

Prerequisite sequence exact/F1 and joint-hyperedge exact/F1 are reported
separately.  Joint groups have structured source IDs and support exact set and
micro item F1.  The current v1 prerequisite oracle contains free text rather
than action IDs or DAGs, so prerequisite comparison is explicitly labelled
`STRICT_CANONICAL_FREE_TEXT_VS_OPERATION_SEQUENCE`; it must not be described as
semantic DAG accuracy.  A future structured oracle can turn that metric into a
hard gate without changing the analysis artifacts.

## Reproducible formal invocation

```text
python3 benchmark/rift/m5/micro/evaluate_m5.py \
  --result-root /path/to/sealed-run \
  --output /path/to/evaluation.json \
  --formal \
  --expected-run-manifest-sha256 <sha256>
```

The evaluator first checks the external run commitment, then all sealed input
and artifact descriptors, reruns the frozen detached verifier, and only then
loads `benchmark/rift/gold`.
