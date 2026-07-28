# Milestone 7 link and catalog consistency audit

Audit state: `PRE_FINAL`. This is a read-only consistency and provenance gate. It does not accept a property, infer firmware conformance, or alter a formula boundary. The gate validates recorded evidence; it does not derive property semantics from source control flow, and it does not fetch GitHub during validation. In particular, this audit 不从源码控制流产生或修改性质。

## Aggregate property gate

The live catalogs contain 13 properties, 46 atomic propositions, 227 source bindings, 77 AP observations, 28 source-evidence records over 16 source files, 15 runtime instances, and 15 runtime property-parameter rows. The per-system split is:

| System | Properties | APs | Bindings | AP observations | Source evidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| ArduPilot | 7 | 25 | 107 | 43 | 13 |
| PX4 | 6 | 21 | 120 | 34 | 15 |

Each property is checked against `benchmark/schemas/property.schema.json`. Every standalone property JSON is required to equal the corresponding aggregate-catalog object. For each source-evidence record, the local file, SHA-256, line range, and exact quote are checked. Runtime instances are joined to `benchmark/extraction_runs/milestone6/runtime_evidence.json` by property and capture identity; parameter values, units, source paths, source hashes, and source indices must agree.

The PRE_FINAL boundary is explicit: property status `ACCEPTED` count is 0, all 13 implementation-satisfaction values are `NOT_ASSESSED`, and the formula epsilon count is 0. All review decisions remain pending. Formula/parser progress is counted exactly from the live catalog and is not converted into an implementation or conformance conclusion. Supplying `--final-review-status` only validates an explicit root-agent allowlist; this script never edits catalogs or creates an acceptance decision.

The final live status distributions are:

- Property status: 12 `NEEDS_CONTEXT`, 1 `CANDIDATE`.
- MITL status: 6 `MONITOR_VALIDATED`, 1 `MONITOR_VALIDATION_FAILED`, 1 `UNSUPPORTED_BY_MONITOR`, 4 `NEEDS_CONTEXT`, and 1 `SYMBOLIC_ONLY`.
- Runtime instance status: 8 `INSTANTIATED_FORMULA_VALIDATED`, 2 `INSTANTIATED_UNVALIDATED`, 2 `DISABLED_BY_RUNTIME_CONFIGURATION`, 2 `NEEDS_CONTEXT`, and 1 `NOT_FORMALIZED`.
- AP status: 43 `BOUND` and 3 `PARTIALLY_BOUND`; observability is 9 `DIRECT`, 6 `DERIVED`, 12 `CONDITIONAL`, 16 `INSTRUMENTATION_REQUIRED`, and 3 `UNRESOLVED`.

`MONITOR_VALIDATED` here records the Stage 7 synthetic formula/trace gate only. The retained 1 failed and 1 unsupported monitor result remain visible, and none of these states assesses firmware runtime conformance.

All 10 active concrete instances carry Stage 7 coverage notes, and the Stage 7 catalog validator asserts that those notes replaced the earlier Stage 6 unvalidated wording.

## Binding and fixed-commit permalink gate

The frozen firmware commits are:

| System | Firmware commit | MAVLink commit |
| --- | --- | --- |
| ArduPilot | `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` | `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472` |
| PX4 | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` | `33af200d25ec6f0925b49b1ba82bbf1294ea5f72` |

For all 227 bindings, the validator checks the recorded commit, repository prefix, file existence, local file bytes against `git show <commit>:<path>`, source line and optional column, and a symbol token in the nearby source window. There are 58 distinct frozen source files. It reconstructs the canonical GitHub fixed-commit permalink from repository, commit, file, and line, then requires that exact URL in the binding evidence. The canonical set digest is computed from sorted `binding_id<TAB>url<LF>` records. No network fetch is performed; provenance comes from the local frozen Git objects and recorded exact URL.

The 227-row permalink-set SHA-256 is `edf87a79286ac21554ab974cd4c8a100d02fe4a354b0e32d669cc71bda6fd2ae`.

Macro spelling and expansion locations are also checked when present. Workspace-relative locations and compiler-style repository-relative locations are both supported.

## Static and runtime catalog recount

The static MAVLink catalog is independently recounted from JSON, CSV, and frozen XML locators:

| System | Messages | Fields | Commands | Command slots | Configuration parameters | Time rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ArduPilot | 352 | 2,708 | 216 | 1,512 | 16,904 | 2,628 |
| PX4 | 251 | 2,018 | 176 | 1,232 | 1,418 | 463 |
| Total | 603 | 4,726 | 392 | 2,744 | 18,322 | 3,091 |

Every command has slots 1 through 7. Message, field, and command XML origin lines are checked against the frozen XML files. Configuration source locations are range-checked, and every time row must resolve to a message field, command slot, or configuration parameter. The static support matrix has 995 rows.

The runtime overlay remains a separate evidence layer: 4 profiles, 1,307 primary static-definition rows, 3 supplemental `BAD_DATA` rows, and 1,310 total rows. Its implementation-satisfaction marker is `NOT_ASSESSED`; it does not convert observed traffic into a global supported/unsupported verdict. The saved static validation report is read and required to be `PASS` with no failures. The static validator itself is not invoked because it rewrites `benchmark/mavlink_catalog/validation_report.json`.

## Superseded PX4 draft isolation

The early 14-candidate PX4 YAML draft is retained only under `benchmark/extraction_runs/milestone4/superseded_px4_draft/` with status `SUPERSEDED_NON_CANONICAL_DRAFT`. It is not a property, AP-binding, or monitor input. The aggregate validator forbids its former files, candidate YAMLs, historical epsilon token, and former in-place YAML glob from the canonical `benchmark/PX4/` tree. It independently checks that the archive manifest has 24 unique confined paths and that every saved byte count and SHA-256 still matches. This proves post-isolation snapshot integrity, not pre-archive historical identity because no externally anchored pre-move receipt exists; it still prevents the implementation-derived heartbeat/HRT draft semantics from bypassing the canonical data-link-loss definition.

## Local-link scope

The gate scans 34 curated benchmark Markdown files and validates 250 local link targets, Markdown anchors, line fragments, and explicit `path:line` targets. The local-link-set SHA-256 is `bc4166cbcfaca514777e949427fef6578050f0c2e428b9d8bd78b7262e36c4fc`. The scope includes `benchmark/README.md`, `benchmark/METHOD.md`, `benchmark/RESULTS.md`, the observability note, paper audits, catalog documentation, milestone top-level reports and one-level nested READMEs, both catalog entry pages, and all 13 generated per-property reports.

Vendored documentation under `benchmark/profuzzbench` and `benchmark/rift/external` is outside this authored benchmark-document scope. Fenced exact-quote blocks in the generated property reports are deliberately skipped by the Markdown link parser so source text that merely resembles Markdown is not treated as an authored link. Links outside those fences are checked normally. Property JSON source paths, hashes, line ranges, and quotes are validated separately by the property gate.

## Reproduction and output

The deterministic Stage 7 rebuild preserves and validates the Stage 6 catalog first, then recreates monitor evidence, then emits the Stage 7 catalog:

```console
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 6
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --force
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_monitor_validation.py --check
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 7
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_property_catalog.py --stage 7
```

Default aggregate validation, including the read-only Milestone 6 aggregate child validator:

```console
python3 -B benchmark/scripts/validate_benchmark.py
```

Live-fact validation without requiring these two audit artifacts:

```console
python3 -B benchmark/scripts/validate_benchmark.py --facts-only --skip-subvalidators
```

An explicit final-review file, if later produced by the root agent, is passed with:

```console
python3 -B benchmark/scripts/validate_benchmark.py --final-review-status <path>
```

Machine-readable JSON is written to stdout; child-validator diagnostics and explicit non-run reasons are written to stderr. `validate_source_bindings.py` is not invoked because it rewrites Milestone 5 reports. `validate_catalog.py` is not invoked because it rewrites the static validation report; the saved report is read and its owned artifacts are independently recounted and hash-checked.

## Limitations and unresolved items

- This gate establishes internal consistency, provenance, link integrity, and catalog recounts. It is not an implementation-conformance result.
- The superseded 14-candidate PX4 draft remains available only as an immutable historical archive; its manifest and canonical-directory isolation are validated, but its contents are not accepted as requirements.
- Three APs remain `PARTIALLY_BOUND`; their limitations remain visible in the property catalogs. The additional PX4 data-link-loss AP is intentionally unresolved because official telemetry/data-connection liveness is not equated to the current heartbeat implementation.
- Hardware behavior and AP instrumentation fidelity are not assessed here.
- Six synthetic monitor suites passed, one has an endpoint-verdict mismatch, and one remains unsupported under the primary runtime limit; these results retain their own verdict semantics and do not close property review automatically.
- A final independent review state has not been supplied; the audit therefore remains `PRE_FINAL`.
