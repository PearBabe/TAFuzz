# PX4 MITL 性质目录（里程碑 7）

本目录是证据绑定的性质集合，不是飞控符合性结论。运行实例来自保存的 SITL PARAM_VALUE；独立自动审核已将存在上下文/形式化 blocker 的条目回退。TAMonitor 失败或不支持的执行原样保留，且不等于实现符合性。

## 计数

- `NEEDS_CONTEXT`：6

## 性质

| ID | 中文标题 | 状态 | 形式化 |
|---|---|---|---|
| [PX4-MC-RCLOSS-001](properties/PX4-MC-RCLOSS-001.md) | PX4 selected manual source 丢失 | `NEEDS_CONTEXT` | `MONITOR_VALIDATION_FAILED` |
| [PX4-MC-GCSLOSS-002](properties/PX4-MC-GCSLOSS-002.md) | PX4 GCS data-link loss | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` |
| [PX4-MC-OFFBOARD-003](properties/PX4-MC-OFFBOARD-003.md) | PX4 Offboard proof-of-life 时序 | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` |
| [PX4-MC-AUTODISARM-004](properties/PX4-MC-AUTODISARM-004.md) | PX4 落地后自动 disarm | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` |
| [PX4-MC-FLIGHTTIME-005](properties/PX4-MC-FLIGHTTIME-005.md) | PX4 最大飞行时间 | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` |
| [PX4-MC-RTLLOITER-006](properties/PX4-MC-RTLLOITER-006.md) | PX4 RTL 目的地等待后着陆 | `NEEDS_CONTEXT` | `NEEDS_CONTEXT` |

所有记录：`implementation_satisfaction = NOT_ASSESSED`。
