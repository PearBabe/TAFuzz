# PX4 MITL benchmark（canonical Stage 7）

`CANONICAL_STAGE7_CATALOG`：本目录的正式性质入口是
[`property_catalog.md`](property_catalog.md)、[`property_catalog.json`](property_catalog.json)
以及 `properties/` 下六条同 ID 的 `.md/.json`。它们固定到 PX4 v1.17.0
提交 `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`；所有性质均为
`implementation_satisfaction=NOT_ASSESSED`，没有 `ACCEPTED` 性质。

## 人工审核入口

- [`property_catalog.md`](property_catalog.md)：性质状态与公式门禁总表。
- [`atomic_proposition_map.csv`](atomic_proposition_map.csv)：AP 真值、状态和可观测性。
- [`source_bindings.csv`](source_bindings.csv)：当前冻结源码的多对多位置、语义身份和置信类型。
- [`mavlink_observation_matrix.csv`](mavlink_observation_matrix.csv)：MAVLink 直接、派生、条件、插桩和未解析观测。
- [`time_constraints.csv`](time_constraints.csv)：时间起止、参数值、时钟域、载体与不确定度。
- [`source_and_corpus_manifest.json`](source_and_corpus_manifest.json) 与
  [`coverage_ledger.csv`](coverage_ledger.csv)：冻结语料及逐文件筛查覆盖。
- [`candidates_and_exclusions.md`](candidates_and_exclusions.md)：规范化候选、待审项和排除纪律。

## 遗留草案隔离

`SUPERSEDED_NON_CANONICAL_DRAFT`：早期 14-candidate YAML 专项草案已经移到
[`extraction_runs/milestone4/superseded_px4_draft/`](../extraction_runs/milestone4/superseded_px4_draft/ARCHIVE_NOTICE.md)。
该草案含未验证、无数值来源的 epsilon 占位符，以及把当前 heartbeat/HRT 实现当作 data-link
候选起点的旧表述；它不属于最终性质目录、MITL 计数、AP 绑定输入或监视器输入，不能用于
性质审核或 fuzz 判定。归档只为保留审计历史；同目录 manifest 固定归档隔离后的当前字节快照，但没有归档前外部锚定收据，不能单独证明更早的历史身份。

最终 canonical 文件禁止该历史 epsilon 占位符，也禁止由当前实现控制流反向定义 telemetry/data-connection
liveness。`PX4-MC-GCSLOSS-002` 的该事件与时钟保持 `UNRESOLVED/UNKNOWN`；heartbeat/HRT
位置仅为 `MODELLED` 映射候选。
