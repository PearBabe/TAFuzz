# TAFuzz Agent Operating Guide

This workspace uses lightweight handoff files so Codex can recover cleanly
after context compaction, model changes, thread changes, or long pauses.

## Start Of Work

- Before starting a non-trivial task, read `.codex/PROJECT_STATE.md` and
  `.codex/SESSION_LOG.md`.
- Treat `.codex/PROJECT_STATE.md` as the current handoff source of truth.
- Do not restart broad exploration when the state file points to specific files
  or commands. Inspect the referenced files first.
- Use `rg` or `rg --files` for search whenever possible.
- Protect user work. Never revert existing changes unless the user explicitly
  asks for that operation.
- This top-level workspace is not currently a valid Git repository. Do not run
  root-level Git commands as if it were one.

## Workspace Boundaries

- `tool/MightyPPL` and `tool/MoniTAal` are independent nested Git repositories.
- Handoff files live at the TAFuzz root and should not be mixed into the nested
  tool repositories unless the user asks for that explicitly.
- Before changing either nested repository, check its own `git status --short`
  and preserve unrelated local changes.

## Long Task Continuity

- After each meaningful milestone, update `.codex/PROJECT_STATE.md` with the
  current status, changed files, verification results, blockers, and at most
  three next steps.
- Append a short entry to `.codex/SESSION_LOG.md` when meaningful progress is
  made. Include the command/result summary, not full logs.
- If `.codex/PROJECT_STATE.md` grows beyond roughly 250 lines, move stale
  details to `.codex/archive/` and keep only the active handoff.
- The handoff files are a workflow contract. Codex does not automatically log
  every conversation or command unless an agent deliberately updates them.

## Handoff On Request

When the user says something like "按交接机制整理当前任务状态", update the handoff
files using `.codex/HANDOFF_TEMPLATE.md` and provide a copy-ready recovery
prompt for the next thread/model.

## Subagent Use

- Use subagents only when the user explicitly asks for subagents, delegation, or
  parallel agent work, or when the task materially benefits from isolated
  read-heavy exploration.
- Do not assign overlapping write scopes to multiple workers.
- Every delegated result should include: conclusion, evidence files, changed
  files if any, verification commands, and unresolved questions.

## Verification Expectations

- Report skipped verification explicitly.
- Prefer concrete commands and observed results over broad claims.
- For this workspace setup, useful state checks include:
  - `find AGENTS.md .codex -maxdepth 3 -type f | sort`
  - `git -C tool/MightyPPL status --short`
  - `git -C tool/MoniTAal status --short`
