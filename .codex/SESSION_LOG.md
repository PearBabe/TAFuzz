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

## 2026-06-26 09:30 CST

- Goal: publish the full TAFuzz source workspace, including handoff files, to
  `PearBabe/TAFuzz` on `main`.
- Work completed: created `/home/lqq/download/TAFuzz_publish_main` as a clean
  clone of the remote, synced `AGENTS.md`, `.codex/`, `tool/MightyPPL/`, and
  `tool/MoniTAal/`, excluded nested Git metadata and build artifacts, committed
  the snapshot, and pushed it to GitHub.
- Files changed: no source files were edited; `.codex/PROJECT_STATE.md` and
  `.codex/SESSION_LOG.md` were updated after publishing to record the result.
- Verification: the initial source snapshot commit was
  `2b6594ceb41c9429a2327b7989f723067063943e`; the publish clone had no nested
  `.git` paths and no `160000` gitlink entries; key paths such as `AGENTS.md`,
  `.codex/PROJECT_STATE.md`, `tool/MightyPPL/CMakeLists.txt`, and
  `tool/MoniTAal/CMakeLists.txt` existed in the published commit.
- Blockers / skipped checks: HTTPS push could not prompt for credentials, so
  the publish clone was switched to SSH remote `git@github.com:PearBabe/TAFuzz.git`;
  no rebuild was run during publishing.
- Next: for future publishes, use `/home/lqq/download/TAFuzz_publish_main` and
  re-run the nested `.git` plus gitlink checks before pushing.

## 2026-06-26 09:45 CST

- Goal: create a reusable Codex skill for one-command TAFuzz publishing after
  source edits.
- Work completed: created local skill `publish-tafuzz` under
  `/mnt/c/Users/lqq27/.codex/skills/publish-tafuzz`; added
  `scripts/publish_tafuzz.sh` to sync `/home/lqq/download/TAFuzz` into
  `/home/lqq/download/TAFuzz_publish_main`, remove nested Git metadata, force-add
  required ignored external dependency files, verify no gitlinks, commit, and
  push to `git@github.com:PearBabe/TAFuzz.git`.
- Files changed: skill files under `/mnt/c/Users/lqq27/.codex/skills/publish-tafuzz`;
  this handoff entry in `.codex/SESSION_LOG.md`; matching state update in
  `.codex/PROJECT_STATE.md`.
- Verification: `bash -n` passed for the publish script; skill validation
  reported `Skill is valid!`; a dry run from `/home/lqq/download/TAFuzz` updated
  the publish clone and reported no changes when already in sync.
- Blockers / skipped checks: no source rebuild was run because this change only
  added publish automation and handoff notes.
- Next: after editing TAFuzz, run
  `/mnt/c/Users/lqq27/.codex/skills/publish-tafuzz/scripts/publish_tafuzz.sh -m
  "Update TAFuzz workspace"` from anywhere under the source tree.
