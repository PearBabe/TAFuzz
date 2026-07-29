# SIP 扩展提取交接

- 结论：新增 6 条 RFC 6026 候选（SIP-TX-21..26），覆盖 UAS 2xx 首次/倍增/T2 封顶/ACK 停止以及 Timer L/M。
- 证据：RFC 6026 §§7.1、7.2、8.1；RFC 3261 §17.1.1.1；Doubango 固定 commit `7604ae6761534d2efdc862bc9961623abc98b9a5`。
- 特别审计点：SIP-TX-23 的标准 oracle 与源码 `timerX.timeout <<= 1` 形成已知偏差检测点；不能写成“实现已符合”。
- 验证：由根生成器统一执行 finite/flatten symbolic+concrete 正反轨迹。
- 未决：所有条目人工状态仍为 `PENDING`；Timer M transport-error 例外需要适配器同 microstep 标记。
