# Milestone 3 corpus and deterministic prefilter

Run timestamp: `2026-07-18T06:11:50+08:00`.

Frozen inputs:

- ArduPilot source: `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e`.
- ArduPilot official wiki: `209e532bc97e5a41966f8c9ab483323c264cae08`; sparse checkout of `common`, `copter`, `plane`, and `rover`.
- PX4 source and English documentation: v1.17.0 commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`.

Results:

| System | Screened files | DocGraph nodes | Edges | Prefilter candidates | Official docs | Parameter metadata | Source comments |
|---|---:|---:|---:|---:|---:|---:|---:|
| ArduPilot | 4,225 | 112,821 | 213,227 | 19,003 | 7,095 | 839 | 11,069 |
| PX4 | 5,547 | 102,029 | 187,470 | 17,148 | 6,005 | 361 | 10,782 |

Interpretation:

- `SCREENED_BY_DETERMINISTIC_PREFILTER` means that a file was parsed and its keyword/parameter hits were recorded. It does not mean a human accepted its contents as requirements.
- Every candidate begins as `PENDING_CONTEXT_REVIEW`; normal source control flow is never a property source.
- Source comments and parameter metadata are deliberately retained at low authority. They may produce candidates but require independent context review and cannot establish implementation conformance.
- Generated message/topic pages, setup instructions, hardware guidance, historical pages, examples, prose mentioning units incidentally, and duplicated vehicle/common pages are expected false positives; they remain in the ledger so screening coverage is auditable.

Artifacts:

- `ArduPilot/docgraph.jsonl` and `PX4/docgraph.jsonl`: ordered document/source nodes plus containment/order edges.
- `*/prefilter_candidates.jsonl`: exact text, file hash, line range, section path, commit permalink, keyword hits and prefilter score.
- `*/run_summary.json` and `combined_summary.json`: aggregate counts.
- `../../ArduPilot/coverage_ledger.csv` and `../../PX4/coverage_ledger.csv`: one row per screened file.
- `../../ArduPilot/source_and_corpus_manifest.json` and PX4 counterpart: complete file/hash manifest.

Reproduction and validation:

```bash
python3 benchmark/scripts/build_corpus.py
python3 benchmark/scripts/validate_corpus.py
```

The validation command passed with all 9,772 source files present and hash-stable, all 36,151 candidates linked to existing DocGraph nodes, and all fixed repository HEADs unchanged.
