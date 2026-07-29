# Reproducibility Manifest

This generated manifest records runtime metadata, tool paths, git state, and SHA-256 hashes for source and result artifacts.
It is intended to make paper review and experiment reruns auditable even when the workspace is dirty.

## Counts

- environment: 3
- git: 6
- result_sha256: 71
- run: 6
- source_sha256: 30
- tool: 4

## Key Runtime Rows

| category | key | value |
|---|---|---|
| `run` | `argv` | `/home/lqq/project/TAFuzz/test/TARV/scripts/run_paper_experiments.py --timeout 30 --out /home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full --tamonitor /home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor` |
| `run` | `output_dir` | `/home/lqq/project/TAFuzz/test/TARV/results/paper_pipeline_formula_catalog_workbook_guard_full` |
| `run` | `timeout_seconds` | `30` |
| `run` | `no_run` | `False` |
| `run` | `no_workbook` | `False` |
| `run` | `workbook_status_at_manifest_write` | `not_built_yet` |
| `tool` | `tamonitor_path` | `/home/lqq/project/TAFuzz/tool/MightyPPL/build/TAMonitor` |
| `tool` | `tamonitor_exists` | `True` |
| `tool` | `monitaal_bin` | `/home/lqq/project/TAFuzz/tool/MightyPPL/build/monitaal-prefix/src/monitaal-build/src/monitaal-bin/MoniTAal-bin` |
| `tool` | `monitaal_bin_exists` | `True` |
| `git` | `mighty_or_workspace_root` | `/home/lqq/project/TAFuzz` |
| `git` | `mighty_or_workspace_head` | `3dde2a82aac2f22f716cb333fd5afb0160098289` |
| `git` | `mighty_or_workspace_status_short` | `M ../../.codex/PROJECT_STATE.md \|  M ../../.codex/SESSION_LOG.md \|  M CMakeLists.txt \|  M MightyPPL.cpp \|  M MightyPPL.h \|  M TAwithBDDEdges.cpp \|  M TAwithBDDEdges.h \|  M ../MoniTAal/benchmark/main.cpp \|  M ../MoniTAal/src/monitaal-bin/main.cpp \| ?? ../../.codex/archive/ \| ?? ../../analysis/tool_projects_deep_analysis.md \| ?? ../../src/ \| ?? ../../test/ \| ?? MightyPPLRuntimeOptions.cpp` |
| `git` | `monitaal_or_workspace_root` | `/home/lqq/project/TAFuzz` |
| `git` | `monitaal_or_workspace_head` | `3dde2a82aac2f22f716cb333fd5afb0160098289` |
| `git` | `monitaal_or_workspace_status_short` | `M ../../.codex/PROJECT_STATE.md \|  M ../../.codex/SESSION_LOG.md \|  M ../MightyPPL/CMakeLists.txt \|  M ../MightyPPL/MightyPPL.cpp \|  M ../MightyPPL/MightyPPL.h \|  M ../MightyPPL/TAwithBDDEdges.cpp \|  M ../MightyPPL/TAwithBDDEdges.h \|  M benchmark/main.cpp \|  M src/monitaal-bin/main.cpp \| ?? ../../.codex/archive/ \| ?? ../../analysis/tool_projects_deep_analysis.md \| ?? ../../src/ \| ?? ../../test/ \| ?? ../MightyPPL/MightyPPLRuntimeOptions.cpp` |
