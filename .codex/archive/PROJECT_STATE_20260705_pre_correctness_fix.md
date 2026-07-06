# Archived Project State Before Correctness-Fix Milestone

Archived: 2026-07-05 01:47 CST

This archive keeps the older long-form handoff details that were condensed out
of `.codex/PROJECT_STATE.md` after it grew past the lightweight handoff size.

## Historical Milestones Preserved

- TAMonitor v1 was added under `/home/lqq/project/TAFuzz/src/TAMonitor` and
  built through `/home/lqq/project/TAFuzz/tool/MightyPPL/CMakeLists.txt`.
- TAMonitor v1 builds positive and negative MightyPPL automata, projects BDD
  labels to canonical `bits:<...>` labels, runs MoniTAal-based monitoring, and
  writes CSV/JSON/XLSX results.
- `compflatten` runtime remains explicitly unsupported in v1 rather than
  producing fake verdicts.
- `CFn/COn/CGn/CHn` are treated as MightyPPL internal Count construction forms,
  not ordinary user-level MITL formulas.
- Earlier real bug fixes included:
  - rejecting raw Count forms cleanly instead of crashing,
  - avoiding product-bound normalization SIGFPE when `gcd == 0`,
  - fixing old projection clock-map copying used by Pnueli/intersection paths,
  - adding `normalized_formula` reporting,
  - disabling product-bound gcd scaling for TAMonitor to keep MoniTAal trace
    times in the original absolute scale.
- The previous primary output before this archive was
  `/home/lqq/project/TAFuzz/test/TARV/results/paper_experiments_scale_fix`.
  Its summary was: 52 semantic cases, 21 PASS, 14 REVIEW, 6 BUILD_STATS,
  7 RESOURCE_LIMIT, 4 TIMEOUT, 0 FAIL, 0 ERROR; 60 XML templates; 23 XML
  pairs; 19 XML-to-MITL candidates; 15/15 TAMonitor candidate runs succeeded;
  8 MoniTAal baselines ran, 8 timed out, and 7 were skipped for no input.

For the active state after this archive, read
`/home/lqq/project/TAFuzz/.codex/PROJECT_STATE.md`.
