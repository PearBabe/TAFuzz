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

## 中文术语解释契约（Chinese Terminology And Explanation Contract）

- 默认用户要求中文优先的技术交流。回答、分析、实施报告、里程碑交接或最终结果中只要新出现英文技术术语、英文缩写、英文状态值、英文字段名、英文工具名或英文文件格式名，必须先解释清楚或在首次出现处同步解释，解释完成后才能继续依赖该术语陈述结论。
- 首次解释在适用时必须同时包括：英文原词；缩写对应的完整英文；准确的中文翻译；它在当前 TAFuzz 任务中具体指什么；它会怎样影响对结果的理解或判断。只给一个中文直译，或者只在括号内标注中文名称，不算充分解释。
- 对必须保持原样的机器可读标识符，例如 `NEEDS_CONTEXT`、`PARTIALLY_BOUND`、`implementation_satisfaction`、数据结构字段、命令行选项、源码符号和公式，不得在代码或数据中擅自翻译、改名；必须在相邻正文、表格图例或术语表中逐项说明中文含义和判断作用。
- 一段结果中出现多个英文术语时，必须先提供逐项术语图例，再使用这些术语总结结果。不得假设用户会永久记住之前会话中的解释；后续回答必须能够独立阅读，必要时重复简洁解释。
- `benchmark`（基准数据集及其验证材料）交付必须维护中文术语表，使用户无需猜测英文状态即可审核报告。如果同一个术语在不同工具或论文中的含义不同，必须说明本次采用哪一种定义，并保留英文原文作为证据。
- 如果附件图片或 Windows 临时路径不能直接读取，在能够安全确定对应路径时，应检查 `/mnt/c/...` 形式的 WSL 路径。这里的 WSL 是 `Windows Subsystem for Linux`，中文为“适用于 Linux 的 Windows 子系统”，该路径用于从 Linux 工作区访问 Windows 文件。如果仍无法读取，必须说明限制并请用户重新附加文件，不能猜测图片里的英文内容。

## Disabled Skills

- Never use or reinstall `academic-research-suite` or any `superpowers:*` skill.
- These packages were explicitly uninstalled at the user's request on
  2026-07-14. Keep this prohibition in force unless the user explicitly reverses
  it in a later request.
- If a task would normally match one of these skills, continue with ordinary
  reasoning and the remaining tools without loading or citing the disabled skill.

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
