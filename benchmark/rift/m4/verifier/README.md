# RIFT M4 independent Certificate v2 verifier

`verify.py` is a standard-library-only, read-only auditor for a completed RIFT
analysis bundle. It neither imports analyzer code nor accepts self-reported
stable IDs as evidence. Certificate v2 is replayed from independently supplied
bytes; Certificate v1 is compatibility-only and necessarily reports
unsupported assurance.

The verifier is project-neutral. Its identity, graph, provenance, environment,
and build-manifest rules contain no ArduPilot, libcoap, benchmark-case, source
directory, or AP-name special case. The same command can therefore audit an
analysis after the analyzer and target project have both been relocated.

## Certificate v2 checks

The strict v2 path verifies all of the following:

- exact certificate, input, output, stage, analyzer, environment, build, and
  toolchain record shapes and canonical orders;
- the frozen `analysis_certificate.schema.json` digest
  `b47322815a208056aab5e47d77a9495407f8dd3d66f93f414d61ba1b7e995dac`;
- raw generated-build-manifest bytes, its exact production/schema file sets,
  every source-file digest, and both length-prefixed aggregate tree digests;
- the analyzer binary bytes and the four manifest commitments physically
  embedded in that binary;
- the fixed ordered 16-variable semantic-environment vector, its aggregate,
  and every supplied raw value or absence marker;
- the v2 configuration digest over build-manifest digest, environment digest,
  and exact ordered analyzer `argv`, including `argv[0]`;
- the executable plus `ldd`-resolved loader/shared objects, with optional
  additional mapped files, against the exact certified name/kind/digest set;
- property IR, compilation database, and all four output byte digests;
- exact five-stage digest closure:
  `index -> bind -> influence -> cone -> certificate`;
- semantic-index input-file IDs, canonical manifest order, repeated-path
  consistency, manifest aggregate, TU closure, and index artifact ID;
- every file-backed source/header provenance path by race-checked physical
  rehash; only content-addressed toolchain predefines may be pathless;
- `source_inputs`, length-prefixed `analysis_id`, and length-prefixed
  `certificate_id` reconstruction;
- exact coverage-gap union and conservative stage/aggregate status;
- graph endpoint/condition closure, AP-role candidate accounting, continuous
  witness paths, and an independent directed reachability traversal for every
  cone member.

Stable regular files are checked before, during, and after reading, including
device, inode, size, modification time, and change time. A source or runtime
file changed concurrently with verification is rejected instead of being
silently hashed at an indeterminate point.

## Usage

From the TAFuzz root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/rift/m4/verifier/verify.py \
  --analysis-dir /path/to/rift-output \
  --path-root /path/to/target-workspace \
  --binary /path/to/tafuzz-sa \
  --argv-json /path/to/exact-argv.json \
  --implementation-root /path/to/TAFuzz/src/StaticAnalysis \
  --build-manifest /path/to/build/generated/rift_build_manifest.json \
  --environment-json /path/to/raw-semantic-environment.json \
  --strict-provenance \
  --report /tmp/rift-verification-report.json
```

`--argv-json` is a JSON array of the exact strings received by the analyzer.
For example:

```json
[
  "/path/to/tafuzz-sa",
  "influence",
  "--compile-db",
  "project/compile_commands.json",
  "--property",
  "project/property_ir.json",
  "--output-dir",
  "/tmp/rift-output"
]
```

`--environment-json` is an object whose keys are exactly the fixed 16 names.
Each value is the raw string or `null` when absent. Raw values are used only
for local rehashing and are not copied into the report. When verification is
performed in the original analyzer environment, use
`--verify-current-environment` instead; the two options are mutually exclusive.

The analyzer records all regular mapped files from `/proc/self/maps`. The
independent verifier resolves ordinary ELF dependencies with `ldd`. Pass each
additional runtime-mapped file that was loaded outside the ELF dependency
closure as another `--runtime-file /absolute/path`. Omitting one makes the
physical digest multiset differ and fails strict verification.

Relative property/compilation-database paths are searched below every repeated
`--path-root`, the current directory, and certificate-adjacent directories.
Outputs are always read from `--analysis-dir`; this permits relocating a whole
result bundle while preserving its certified bytes.

Exit code is zero for `PASS` and, in non-strict v1 compatibility mode,
`PASS_WITH_UNSUPPORTED_ASSURANCE`. It is one for `FAIL`. Under
`--strict-provenance`, every unsupported claim also makes the result fail.

## Trust boundary and v1 behavior

Certificate v2 can bind a supplied binary to a supplied generated manifest and
the exact committed production/schema source snapshot. This proves consistency
of those artifacts; it does not claim that an unobserved compiler process was
honest.

Certificate v1 has no embedded build manifest, semantic-environment vector,
runtime-file provenance, or physical source-path projection. Non-strict mode
still checks its available artifact bytes, stage closure, and cone evidence,
but marks the missing assurances `UNSUPPORTED`. Strict mode rejects it. The
verifier never upgrades a v1 tree hash or analyzer-reported source digest into
a v2 provenance claim.

## Self-tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s benchmark/rift/m4/verifier/tests -v
```

The suite constructs both compatibility and fully physical Certificate v2
bundles from scratch. Negative cases cover source/build/schema commitments,
binary embedding, raw environment, exact argv, runtime-file relabeling,
physical source mutation, provenance projection, input/output ordering,
certificate identity, byte tampering, stage closure, soundness overclaim,
candidate accounting, and witness/reachability corruption.
