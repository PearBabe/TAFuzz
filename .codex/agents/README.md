# TAFuzz Agent Notes

This directory is reserved for optional Codex agent guidance.

No custom subagent configuration is required by default. Use parallel or
delegated work only when it materially helps the task, such as read-heavy code
exploration, independent test-failure triage, or clearly separated
implementation slices.

Every delegated result should include:

- conclusion
- evidence files
- changed files, if any
- verification commands
- unresolved questions

Do not assign overlapping write scopes to multiple workers, and do not let
delegated work modify `tool/MightyPPL` or `tool/MoniTAal` without first checking
and preserving their current local changes.
