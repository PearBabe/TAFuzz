# Superseded PX4 14-candidate draft

Status: `SUPERSEDED_NON_CANONICAL_DRAFT`.

这些文件是里程碑 4 早期专项审计的隔离快照，不是最终 benchmark 输入。它们可能包含：

- 没有数值来源的符号占位 `EPS_OBS`；
- 将当前 `MAV_TYPE_GCS` heartbeat/HRT 实现候选写入 data-link 触发语义的旧草案；
- `NOT_VALIDATED` 的候选公式和已被后续证据门禁回退或重写的 AP 身份。

不得从本目录选择性质、时间值、公式、AP 或源码 binding；不得把这里的 14 条草案计入最终
accepted/candidate/auxiliary/rejected 数量。最终 canonical 入口是
`benchmark/PX4/property_catalog.{md,json,csv}` 与 `benchmark/PX4/properties/*.json`。

本次隔离操作未为“修好历史”而有意改写这 24 个文件；归档时的内容哈希和字节数保存在
`archive_manifest.json`。该 manifest 可检测此后漂移，但因没有归档前的外部锚定收据，不能独立证明
更早历史身份。这样既保留可核验的当前审计快照，也防止旧 epsilon 或实现语义从正式 PX4 目录旁路进入人工审核。
