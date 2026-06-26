# TAFuzz Session Log

## 2026-06-26 CST

- Created the top-level Codex handoff system for `/home/lqq/download/TAFuzz`.
- Added `AGENTS.md`, `.codex/PROJECT_STATE.md`, `.codex/SESSION_LOG.md`,
  `.codex/HANDOFF_TEMPLATE.md`, and `.codex/agents/README.md`.
- Confirmed the top-level `.git/` directory was empty and not a valid Git
  repository, then moved it to `.git.EMPTY_DIR_DO_NOT_USE_20260626` to avoid
  future root-level Git confusion.
- Recorded existing nested repository changes in `tool/MightyPPL` and
  `tool/MoniTAal`.
- Verified the handoff files exist and are readable, both nested repository
  statuses are preserved, and the empty `.git/` directory has been safely
  isolated.
- Did not modify source files inside `tool/MightyPPL` or `tool/MoniTAal`.
- Next: use the recovery prompt in `.codex/PROJECT_STATE.md` when continuing in
  a new thread/model or after context compaction.

## 2026-06-26 09:05 CST

- Goal: move MightyPPL and MoniTAal under `TAFuzz/tool/` and make MightyPPL
  build directly against the adjacent MoniTAal working tree.
- Work completed: moved the repositories to `tool/MightyPPL` and `tool/MoniTAal`;
  changed MightyPPL's `monitaal` ExternalProject to use `SOURCE_DIR
  ${CMAKE_CURRENT_SOURCE_DIR}/../MoniTAal`; removed pinned MoniTAal clone/patch
  behavior; adapted MightyPPL calls to the current MoniTAal API; fixed MoniTAal
  CMake dependency ordering and template header qualifiers needed by MightyPPL.
- Files changed: `tool/MightyPPL/CMakeLists.txt`,
  `tool/MightyPPL/main.cpp`, `tool/MightyPPL/TAwithBDDEdges.cpp`,
  `tool/MoniTAal/CMakeLists.txt`,
  `tool/MoniTAal/src/monitaal/CMakeLists.txt`,
  `tool/MoniTAal/src/monitaal/state.h`.
- Verification: `cmake --build . -j2` from
  `/home/lqq/download/TAFuzz/tool/MightyPPL/build` completed successfully;
  `build/mitppl --help` printed usage and exited `1` as expected when no spec
  file is supplied.
- Blockers / skipped checks: no full spec-based semantic test was run; clean
  external builds may still hit transient GitHub HTTPS clone failures for
  MoniTAal's external dependencies, but retry succeeded during this session.
- Next: continue using `tool/MoniTAal` as the editable MoniTAal working tree and
  rebuild with `cmake --build . -j2` from `tool/MightyPPL/build`.
