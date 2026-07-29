# ArduPilot MITL 性质目录（里程碑 7）

本目录是证据绑定的性质集合，不是飞控符合性结论。运行实例来自保存的 SITL PARAM_VALUE；独立自动审核已将存在上下文/形式化 blocker 的条目回退。TAMonitor 失败或不支持的执行原样保留，且不等于实现符合性。

## 计数

- `CANDIDATE`：1
- `NEEDS_CONTEXT`：6

## 性质

| ID | 中文标题 | 状态 | 形式化 |
|---|---|---|---|
| [ARD-COPTER-GCS-001](properties/ARD-COPTER-GCS-001.md) | Copter 指定 GCS heartbeat 超时 | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` |
| [ARD-COPTER-GUID-002](properties/ARD-COPTER-GUID-002.md) | Copter Guided 指令更新超时 | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` |
| [ARD-COPTER-RTL-003](properties/ARD-COPTER-RTL-003.md) | Copter RTL Home 上方等待 | `NEEDS_CONTEXT` | `UNSUPPORTED_BY_MONITOR` |
| [ARD-PLANE-TAKEOFF-001](properties/ARD-PLANE-TAKEOFF-001.md) | Plane 自动起飞超时 | `CANDIDATE` | `SYMBOLIC_ONLY` |
| [ARD-ROVER-RCFS-001](properties/ARD-ROVER-RCFS-001.md) | Rover 低油门持续触发 failsafe | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` |
| [ARD-ROVER-CRASH-002](properties/ARD-ROVER-CRASH-002.md) | Rover crash 条件持续时间 | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` |
| [ARD-SHARED-BATT-001](properties/ARD-SHARED-BATT-001.md) | ArduPilot 持续低电压 failsafe | `NEEDS_CONTEXT` | `MONITOR_VALIDATED` |

所有记录：`implementation_satisfaction = NOT_ASSESSED`。
