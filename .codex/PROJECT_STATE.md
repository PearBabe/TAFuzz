# TAFuzz Project State

Last updated: 2026-06-26 09:30 CST

## Current Goal

Maintain a lightweight Codex handoff system for `/home/lqq/download/TAFuzz`
and keep the published GitHub snapshot recoverable: the full source workspace,
including handoff files, has been published to `PearBabe/TAFuzz` on `main`.

## Current Workspace Shape

- TAFuzz root: `/home/lqq/download/TAFuzz`
- Top-level handoff files:
  - `AGENTS.md`
  - `.codex/PROJECT_STATE.md`
  - `.codex/SESSION_LOG.md`
  - `.codex/HANDOFF_TEMPLATE.md`
  - `.codex/agents/README.md`
- The top-level `.git/` directory was an empty, invalid Git directory. It has
  been moved to `.git.EMPTY_DIR_DO_NOT_USE_20260626` to prevent accidental
  root-level Git confusion.
- No top-level Git repository has been initialized.
- Nested tool repositories:
  - `tool/MightyPPL`
  - `tool/MoniTAal`
- Clean publish clone:
  - `/home/lqq/download/TAFuzz_publish_main`
  - remote: `git@github.com:PearBabe/TAFuzz.git`
  - branch: `main`
- Required relative layout for the current build wiring:

```text
TAFuzz/
  tool/
    MightyPPL/
    MoniTAal/
```

## Known Local Changes To Preserve

Treat these as active project work unless the user explicitly asks to change,
commit, or revert them.

`tool/MightyPPL`:

```text
 M CMakeLists.txt
 M TAwithBDDEdges.cpp
A  external/buddy
 M main.cpp
```

Meaning:

- `CMakeLists.txt` uses `SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../MoniTAal`
  for the `monitaal` ExternalProject, with empty download/update steps.
- `main.cpp` and `TAwithBDDEdges.cpp` are adapted to the current MoniTAal API:
  `symbolic_state_t(location, clocks)`,
  `symbolic_state_map_t<symbolic_state_t>`, and
  `Fixpoint<symbolic_state_t>`.
- `external/buddy` was already an added local state before this handoff update.

`tool/MoniTAal`:

```text
 M CMakeLists.txt
 M src/monitaal/CMakeLists.txt
 M src/monitaal/state.h
```

Meaning:

- `CMakeLists.txt` uses HTTPS URLs for `pugixml` and `PARDIBAAL`.
- `src/monitaal/CMakeLists.txt` adds `pugixml` as a dependency of `MoniTAal`.
- `src/monitaal/state.h` adds required `typename` qualifiers for dependent
  iterator types used by external includers such as MightyPPL.

## Key Decisions

- Keep the handoff system at the TAFuzz root.
- Keep `MightyPPL` and `MoniTAal` under `tool/` as sibling nested repositories.
- MightyPPL no longer clones a pinned MoniTAal commit. It builds the adjacent
  MoniTAal working tree directly through a relative path.
- Do not create a top-level Git repository yet. If versioning the entire
  workspace becomes necessary, plan that separately to avoid accidentally
  committing nested repositories as ordinary directories or gitlinks.
- The handoff files are maintained deliberately by Codex during milestones; they
  are not an automatic full-session recorder.
- Publishing the top-level workspace should continue through the clean publish
  clone, with nested `.git` metadata excluded and `external/buddy` flattened as
  ordinary source files.

## Verification Status

Latest verification completed on 2026-06-26 09:30 CST:

- Published `/home/lqq/download/TAFuzz` to `PearBabe/TAFuzz` `main` via the
  clean clone `/home/lqq/download/TAFuzz_publish_main`.
- Commit `2b6594c` imported the local TAFuzz workspace, including `AGENTS.md`,
  `.codex/`, `tool/MightyPPL/`, and `tool/MoniTAal/`.
- The publish clone excluded nested `.git` metadata, the root
  `.git.EMPTY_DIR_DO_NOT_USE_20260626`, `.agents/`, `tool/MightyPPL/build/`,
  object/static library outputs, and CMake cache/generated files.
- `find /home/lqq/download/TAFuzz_publish_main -mindepth 2 -name .git -print`
  produced no nested Git metadata paths.
- `git -C /home/lqq/download/TAFuzz_publish_main ls-files -s | awk
  '$1 == 160000 {print}'` produced no gitlink/submodule entries.
- The initial source snapshot commit was
  `2b6594ceb41c9429a2327b7989f723067063943e`
  (`Import local TAFuzz workspace`); later handoff-only commits may advance
  remote `main`.

Earlier build verification completed on 2026-06-26 09:05 CST:

- `git -C tool/MightyPPL status --short` showed the MightyPPL changes listed
  above.
- `git -C tool/MoniTAal status --short` showed the MoniTAal changes listed
  above.
- From `/home/lqq/download/TAFuzz/tool/MightyPPL/build`,
  `cmake --build . -j2` completed successfully and generated `mitppl`.
- `/home/lqq/download/TAFuzz/tool/MightyPPL/build/mitppl --help` printed usage
  text and exited `1` because no spec file was supplied; this is expected.
- Earlier full clean configure/build in the moved path also confirmed
  `ExternalProject_add(monitaal)` reports `No download step`, `No update step`,
  and `No patch step`, so MightyPPL is using the local MoniTAal working tree.

## Active Risks / Known Limits

- The top-level workspace is still not a normal Git repository; publishing is
  done from `/home/lqq/download/TAFuzz_publish_main`.
- The nested tool repositories contain local changes. Future work must check
  and preserve those changes before editing.
- MoniTAal still downloads `pugixml` and `PARDIBAAL` via GitHub during clean
  external builds; transient HTTPS clone failures have occurred but succeeded
  on retry.
- This file can drift if future agents do not update it at meaningful
  milestones.

## Next Steps

1. When starting a new non-trivial task, read `AGENTS.md`, this file, and
   `.codex/SESSION_LOG.md` first.
2. To rebuild after MoniTAal edits, run:

```bash
cd /home/lqq/download/TAFuzz/tool/MightyPPL/build
cmake --build . -j2
```

3. Before publishing again, sync through `/home/lqq/download/TAFuzz_publish_main`
   and verify there are no nested `.git` paths or `160000` gitlink entries.

## Recovery Prompt

请先读 /home/lqq/download/TAFuzz/AGENTS.md、/home/lqq/download/TAFuzz/.codex/PROJECT_STATE.md 和 /home/lqq/download/TAFuzz/.codex/SESSION_LOG.md，然后从当前状态继续：MightyPPL 和 MoniTAal 已移动到 /home/lqq/download/TAFuzz/tool/ 下，MightyPPL 直接使用相邻 MoniTAal 工作树构建；完整源码和交接文件已通过 /home/lqq/download/TAFuzz_publish_main 发布到 PearBabe/TAFuzz 的 main 分支；不要重新从头探索，不要回滚用户改动。
