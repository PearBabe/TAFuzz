# ArduPilot 候选与排除台账

## 已规范化候选

- `ARD-COPTER-GCS-001`：`NEEDS_CONTEXT`；Copter 指定 GCS heartbeat 超时。
- `ARD-COPTER-GUID-002`：`NEEDS_CONTEXT`；Copter Guided 指令更新超时。
- `ARD-COPTER-RTL-003`：`NEEDS_CONTEXT`；Copter RTL Home 上方等待。
- `ARD-PLANE-TAKEOFF-001`：`CANDIDATE`；Plane 自动起飞超时。
- `ARD-ROVER-RCFS-001`：`NEEDS_CONTEXT`；Rover 低油门持续触发 failsafe。
- `ARD-ROVER-CRASH-002`：`NEEDS_CONTEXT`；Rover crash 条件持续时间。
- `ARD-SHARED-BATT-001`：`NEEDS_CONTEXT`；ArduPilot 持续低电压 failsafe。

## 仍待上下文审查

- 全量逐条状态见 `benchmark/extraction_runs/milestone4/ArduPilot_adjudication_ledger.jsonl`。
- 原始专项审计输入：`read-only ArduPilot source audit result retained in the task record`。
- `PENDING_CONTEXT_REVIEW` 不是拒绝，也不表示已经提取完毕。

## 明确排除类别

- 普通控制流 timeout/guard、watchdog 和计数器，若无独立规范来源，不产生性质。
- 控制器 time constant、filter cutoff、stream rate、sensor delay compensation 和调参建议，不当作离散 deadline。
- SITL-only delay、logger/peripheral housekeeping timeout 不进入飞控行为性质。
- PGFuzz 历史性质和 ADGFuzz ground/deviation/silence oracle 不自动继承；后者仅保留为 `AUXILIARY_ORACLE`。
- 无数值的 immediately/promptly 不补人工阈值；未解决项保留候选。
- 任何已有实现 guard 只能用于 AP 绑定，不能回填 Requirement IR。
