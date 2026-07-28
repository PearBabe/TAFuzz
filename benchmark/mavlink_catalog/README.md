# 冻结 MAVLink 目录与 Milestone 6 分层运行证据

本目录把冻结 MAVLink 定义、冻结飞控源码中的启发式静态引用，以及
Milestone 6 默认 SITL 运行观测并列保存。`actual_support_matrix.csv` 和
`actual_support_matrix.json` 是按固件 profile 展开的消息矩阵；它们不输出
“全局支持/不支持”布尔值，也不判定任何性质是否满足。

## 冻结输入与方言入口

| 系统 | 飞控提交 | MAVLink 提交 | 静态入口 |
|---|---|---|---|
| ArduPilot | `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` | `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472` | 主入口 `all.xml` |
| PX4 | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` | `33af200d25ec6f0925b49b1ba82bbf1294ea5f72` | 主入口 `development.xml`；辅助入口 `uAvionix.xml` |

静态消息定义来自 `messages_and_fields.json`，静态引用证据只写入
`static_support_matrix.csv`。运行层来自当前
`benchmark/extraction_runs/milestone6/runtime_evidence.json` 和
`runtime_message_support_matrix.json`；生成 JSON 还记录所有直接输入及其
SHA-256。

## 分层矩阵粒度

主粒度是“一条 selected firmware profile × 一条该系统冻结静态消息定义”：

| Profile | 静态定义行 | 主请求方言行 | 辅助方言行 | baseline observed | request-window matching | 任意阶段 observed 静态定义 | ACK 分布 | 非 catalog 观测 |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| ArduCopter `quad` | 352 | 352 | 0 | 2 | 45 | 50 | 80 ACCEPTED / 272 FAILED | 1 |
| ArduPlane `plane` | 352 | 352 | 0 | 33 | 46 | 51 | 82 ACCEPTED / 270 FAILED | 1 |
| Rover `rover` | 352 | 352 | 0 | 26 | 40 | 45 | 81 ACCEPTED / 271 FAILED | 1 |
| PX4 `sihsim_quadx` | 251 | 243 | 8 | 33 | 47 | 54 | 47 ACCEPTED / 196 DENIED / 8 NOT_ATTEMPTED | 0 |

主行共 1,307 条。另有 3 条
`row_scope=RUNTIME_NON_CATALOG_OBSERVATION` 的补充行，分别保留三个
ArduPilot 解码 inventory 中的 `message_id=-1, message_name=BAD_DATA`。
它们是解析记录而不是 MAVLink 静态消息定义，不产生消息支持结论。CSV 和 JSON
总行数均为 1,310。

PX4 的 8 条辅助行只在 `uAvionix.xml` 中定义。当前 PX4 请求 sweep 使用
`development.xml` 的 243 个唯一消息 ID，因此这些行明确保留为：

- `request_dialect_definition_status=DEFINED_ONLY_IN_AUXILIARY_DIALECT`；
- `request_sweep_membership_status=AUXILIARY_DIALECT_NOT_IN_REQUEST_SWEEP`；
- `request_ack_result` 为空。

“未进入 sweep”不能改写为 timeout、DENIED 或 unsupported。

## 各证据层语义

| 层 | 关键列 | 含义与边界 |
|---|---|---|
| 方言定义 | `catalog_definition_status`, `catalog_dialect_entrypoints`, `request_dialect_definition_status` | 只说明 XML entrypoint include closure 是否定义该消息；定义不等于实现支持。 |
| 静态引用 | `static_supported_evidence_status` | 原样复用现有 `STATIC_REFERENCE_FOUND` / `NO_REFERENCE_FOUND_BY_HEURISTIC_SCAN`；两者都不是支持结论。 |
| 静态方向 | `static_direction_evidence_status`, TX/RX count | 只按现有 TX 与 RX/handler 计数机械分组；不证明路径可达、默认启用或方向完整。 |
| 静态 requestable | `static_requestable_evidence_status` | 现有静态 catalog 没有专门 requestability 字段，因此所有静态定义均为 `UNKNOWN_NO_EXPLICIT_REQUESTABILITY_FIELD_IN_STATIC_CATALOG`，不从 TX 引用猜测。 |
| baseline | `baseline_observed`, `baseline_count` | 只证明该 selected 默认 SITL profile 在该时间窗观测到消息；零观测不等于不支持。 |
| 请求时间窗 | `request_attempted`, `requested_window_observed`, `request_matching_frame_count` | 记录串行 `MAV_CMD_REQUEST_MESSAGE` 后时间窗内的匹配帧；已有周期流时因果关系仍不确定。 |
| ACK | `request_ack_result`, `request_ack_interpretation` | 原样保存 ACK。`DENIED` 和 `FAILED` 不转换为 `UNSUPPORTED`。 |
| 汇总观测 | `runtime_observation_class` | 复用 merged runtime matrix 的分类，但不提升为全局支持状态。 |

`COMMAND_ACK` 对命令 512 只标识 `MAV_CMD_REQUEST_MESSAGE`，不携带本次请求的
message ID。采集采用串行请求与时间窗相关，因此 ACK 关联是时序证据。即使 ACK
为 ACCEPTED，若没有匹配帧，也不能声称消息已观测；若有匹配帧但该消息已在
baseline 周期发送，也不能声称匹配帧由请求触发。

## 输出文件

| 文件 | 粒度和用途 |
|---|---|
| `static_support_matrix.csv` | 纯静态 995 行实体矩阵：603 条消息定义与 392 条命令定义；由静态 manifest 哈希登记 |
| `actual_support_matrix.csv` | 扁平 profile/message 分层矩阵，附 3 条显式非 catalog 观测行 |
| `actual_support_matrix.json` | 同一行集，并包含输入哈希、层语义和逐 profile 状态分布 |
| `runtime_catalog_manifest.json` | 确定性记录 runtime overlay 生成器、全部直接输入、CSV/JSON 哈希、行数与状态分布 |
| `manifest.json` | 只登记冻结静态 catalog 输出，不登记 `actual_support_matrix.*` |
| `messages_and_fields.{json,csv}` | 冻结方言消息和字段定义；JSON 是本矩阵的静态定义输入 |
| `commands.{json,csv}` | `MAV_CMD` 静态目录；不进入本消息运行矩阵 |
| `configuration_parameters.{json,csv}` | 静态配置参数目录；不被本脚本修改 |
| `time_fields.csv` | 静态时间/频率候选目录 |
| `generate_catalog.py` | 原始冻结静态目录生成器 |
| `benchmark/scripts/apply_runtime_catalog.py` | 当前分层运行矩阵生成器与无写入自检器 |

## 可复现生成与自检

在 TAFuzz 根目录运行：

```bash
python3 -B benchmark/scripts/apply_runtime_catalog.py
python3 -B benchmark/scripts/apply_runtime_catalog.py --check
```

`--check` 在内存中重新构建 CSV/JSON/runtime manifest 并逐字节比较现有文件，
不写文件。生成器还
检查：

- 四个 capture 的固件/MAVLink commit 与静态 catalog 一致；
- 每个 profile 与该系统静态消息定义的笛卡尔积无缺失、无多余、无重复；
- 同系统同消息的静态引用证据在多个 profile 间一致，并与
  `static_support_matrix.csv` 及 merge 记录的输入哈希一致；
- 方言 entrypoint、消息 ID/name 和 origin XML 与静态定义一致；
- baseline、参数阶段、请求阶段和其他阶段计数能还原总数；
- request-attempt 数与 capture sweep 汇总一致；
- 主静态观测行加非 catalog 补充行能逐 profile 精确还原 distinct/total inventory；
- 输出使用严格 JSON，不允许裸 `NaN`/`Infinity`。

若从头重建完整 Milestone 6 链，顺序固定为静态 catalog、runtime merge、runtime
overlay、Stage 6 property 重建，最后分别验证 runtime/property/catalog：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/mavlink_catalog/generate_catalog.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/merge_runtime_evidence.py
python3 -B benchmark/scripts/apply_runtime_catalog.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/build_property_catalog.py --stage 6
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_runtime_capture.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/scripts/validate_property_catalog.py --stage 6
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/mavlink_catalog/validate_catalog.py
python3 -B benchmark/scripts/apply_runtime_catalog.py --check
```

runtime merge 只读 `static_support_matrix.csv`。兼容回退仅接受具备旧静态列的
legacy CSV；若 `actual_support_matrix.csv` 含 `row_scope` 等 40 列 runtime schema，
merge 会拒绝误读。若 `runtime_evidence.json` 因重新 merge 改变 SHA-256，必须在
验证 property 前重新执行 Stage 6 builder，否则 property configuration snapshot
仍会引用旧 runtime hash。

## 双 manifest 与统一验证

`manifest.json` 只负责静态生成闭环：冻结提交/XML、静态生成器/validator/README、
`static_support_matrix.csv` 和其他静态输出。它不包含 runtime overlay 哈希。

`runtime_catalog_manifest.json` 只负责运行 overlay：确定性生成器哈希、静态
manifest/消息/支持矩阵、merged runtime 输入与逐 profile inventory，以及
`actual_support_matrix.csv/json` 的哈希与 1,307+3 行计数。它不包含自身哈希，
避免循环依赖。

`validate_catalog.py` 先对 `static_support_matrix.csv` 执行原 995 行静态检查，再以
只读子进程运行 `apply_runtime_catalog.py --check`，复核 runtime manifest 输入/输出
哈希、四 profiles、1,307+3 行、8 条 PX4 辅助方言、3 条 `BAD_DATA` 补充记录和
`NOT_ASSESSED`。validator 本身不启动 SITL，也不重新采集运行数据；它只验证保存的
runtime overlay，并将结果写入 `validation_report.json`。

## 明确不做的推断

- 不把 XML 定义当作飞控实现支持；
- 不把静态引用存在当作路径可达，也不把扫描零引用当作不支持；
- 不从 TX 引用猜测 `MAV_CMD_REQUEST_MESSAGE` requestability；
- 不把 baseline 零观测当作不支持；
- 不把 ACK DENIED/FAILED 当作 unsupported；
- 不把请求窗匹配帧自动归因于请求；
- 不进行性质或实现 conformance 判定，`implementation_satisfaction` 保持
  `NOT_ASSESSED`。
