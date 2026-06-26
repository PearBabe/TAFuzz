# TAFuzz Handoff Template

Use this template when the user asks to update or prepare a Codex handoff.

## Update Checklist

1. Read `AGENTS.md`, `.codex/PROJECT_STATE.md`, and `.codex/SESSION_LOG.md`.
2. Check current local state narrowly:
   - relevant files for the active task
   - `git -C tool/MightyPPL status --short` if MightyPPL is involved
   - `git -C tool/MoniTAal status --short` if MoniTAal is involved
3. Update `.codex/PROJECT_STATE.md` with:
   - current goal
   - current status
   - changed files
   - key decisions
   - verification commands and results
   - blockers or skipped checks
   - up to three next steps
   - a copy-ready recovery prompt
4. Append a concise milestone entry to `.codex/SESSION_LOG.md`.
5. Tell the user what was updated and include the recovery prompt.

## Session Log Entry Shape

```markdown
## YYYY-MM-DD HH:MM CST

- Goal:
- Work completed:
- Files changed:
- Verification:
- Blockers / skipped checks:
- Next:
```

## Project State Sections

Keep `.codex/PROJECT_STATE.md` compact. Prefer these sections:

- `Current Goal`
- `Current Workspace Shape`
- `Known Local Changes To Preserve`
- `Key Decisions`
- `Verification Status`
- `Active Risks / Known Limits`
- `Next Steps`
- `Recovery Prompt`

## Standard Recovery Prompt

```text
请先读 /home/lqq/download/TAFuzz/AGENTS.md、/home/lqq/download/TAFuzz/.codex/PROJECT_STATE.md 和 /home/lqq/download/TAFuzz/.codex/SESSION_LOG.md，然后从当前状态继续，不要重新从头探索，不要回滚用户改动。
```
