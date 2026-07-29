# PX4 候选与排除台账

## 已规范化候选

- `PX4-MC-RCLOSS-001`：`NEEDS_CONTEXT`；PX4 selected manual source 丢失。
- `PX4-MC-GCSLOSS-002`：`NEEDS_CONTEXT`；PX4 GCS data-link loss。
- `PX4-MC-OFFBOARD-003`：`NEEDS_CONTEXT`；PX4 Offboard proof-of-life 时序。
- `PX4-MC-AUTODISARM-004`：`NEEDS_CONTEXT`；PX4 落地后自动 disarm。
- `PX4-MC-FLIGHTTIME-005`：`NEEDS_CONTEXT`；PX4 最大飞行时间。
- `PX4-MC-RTLLOITER-006`：`NEEDS_CONTEXT`；PX4 RTL 目的地等待后着陆。

## 仍待上下文审查

- 全量逐条状态见 `benchmark/extraction_runs/milestone4/PX4_adjudication_ledger.jsonl`。
- 原始专项审计输入：`benchmark/extraction_runs/milestone4/superseded_px4_draft/ (SUPERSEDED_NON_CANONICAL_DRAFT; retained only as immutable historical input)`。
- `PENDING_CONTEXT_REVIEW` 不是拒绝，也不表示已经提取完毕。

## 明确排除类别

- 普通控制流 timeout/guard、watchdog 和计数器，若无独立规范来源，不产生性质。
- 控制器 time constant、filter cutoff、stream rate、sensor delay compensation 和调参建议，不当作离散 deadline。
- SITL-only delay、logger/peripheral housekeeping timeout 不进入飞控行为性质。
- PGFuzz 历史性质和 ADGFuzz ground/deviation/silence oracle 不自动继承；后者仅保留为 `AUXILIARY_ORACLE`。
- 无数值的 immediately/promptly 不补人工阈值；未解决项保留候选。
- 任何已有实现 guard 只能用于 AP 绑定，不能回填 Requirement IR。
