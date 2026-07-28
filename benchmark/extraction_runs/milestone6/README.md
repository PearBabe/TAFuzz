# Milestone 6 运行证据与聚合验收

本目录保存冻结 ArduPilot/PX4 SITL 的 MAVLink 运行观测、参数快照、请求时间窗记录、
进程清理证据和合并产物。选中的四个 profile 是：

- ArduPilot/ArduCopter：`quad`，capture `ardupilot-copter-m6`；
- ArduPilot/ArduPlane：`plane`，capture `ardupilot-plane-m6`；
- ArduPilot/Rover：`rover`，capture `ardupilot-rover-m6`；
- PX4/multicopter：`px4_sitl_default sihsim_quadx internal headless SIH instance 42`，
  capture `PX4-M6-MC-SIHSIM-QUADX-I42-20260718`。

四个选中 capture 都是 `COMPLETE`。PX4 的首个 `none_iris` 尝试因 30 秒内没有收到
autopilot `HEARTBEAT` 而标为 `FAILED`；该尝试没有被覆盖或删除，其 manifest、日志、
异常和 cleanup 证据保存在 `PX4/attempt_1_none_iris_failed/`。

这里没有执行飞行、解锁、起飞、模式切换、执行器操作或性质符合性场景。
所有 evidence/catalog/property 中的实现结论仍是
`implementation_satisfaction = NOT_ASSESSED`。

## 权威证据流

ArduPilot 三个 profile 的权威接收流分别是
`ArduPilot/runs/{Copter,Plane,Rover}/messages.jsonl`。每行保存一条解码记录、阶段和
host monotonic arrival。`message_summary.json`、`parameters.json`、
`request_sweep.json` 和 `process_cleanup.json` 是相应的索引与汇总证据。

ArduPilot 采集同时调用了 pymavlink 的 tlog/raw logging hook，但三个 profile 的
`messages.tlog` 和 `messages.raw` 都是零字节。它们被保留并哈希为失败/空的辅助产物，
不能作为流量证据，也不能代替非空的 `messages.jsonl`。

PX4 的权威流由两种互补产物组成：

- `PX4/mavlink_capture.tlog`：带标准 wall-clock 前缀的非空 MAVLink frame 流；
- `PX4/mavlink_messages.jsonl`：带 raw frame hex、阶段、host monotonic/wall arrival、
  SYSID/COMPID、字段和机载时间字段的非空解码流。

`PX4/message_inventory.json`、`parameters_runtime.json`、
`message_request_sweep.json` 和 `process_lifecycle.json` 提供索引、完整参数快照、请求
记录和 cleanup 证据。

Host arrival 使用 `CLOCK_MONOTONIC_NS`。消息内的 `time_boot_ms`、Unix/GPS 时间或
其他机载时间字段保留冻结 XML 所定义的时钟语义；聚合过程不会用 host arrival
替换机载时钟。

## 合并产物与 MAVLink 分层目录

`runtime_evidence.json` 是四个选中 profile 的 schema 化合并入口；
`capture_attempts.json` 同时保留四个选中 capture 和一个未选中的失败尝试。参数、
消息和时间字段的派生表是：

- `runtime_parameter_snapshots.{json,csv}`；
- `runtime_message_support_matrix.{json,csv}`；
- `runtime_time_field_observations.csv`；
- `property_runtime_parameters.csv`。

`benchmark/mavlink_catalog/` 同时保存冻结静态目录和 profile-layered runtime overlay。
静态定义/静态启发式引用、baseline 观测、请求时间窗、ACK 和支持推断是独立层；
XML 定义、静态引用、零观测或单次 ACK 都不会被折叠成全局“支持/不支持”布尔值。

## Request/ACK 语义边界

采集使用串行 `MAV_CMD_REQUEST_MESSAGE (512)`。`COMMAND_ACK` 标识 command 512，
但不携带本次请求的 requested message ID，所以关联依据是串行次序和时间窗，仍保留
late-ACK 歧义。边界如下：

- `MAV_RESULT_ACCEPTED` 只证明命令被接受；没有 matching frame 时不能声称消息已观测；
- ArduPilot 的 `MAV_RESULT_FAILED` 和 PX4 的 `MAV_RESULT_DENIED` 原样保留，不能改写成
  `MAV_RESULT_UNSUPPORTED` 或静态“不支持”；
- request 后出现 matching frame，但同一消息已在 baseline 周期发送时，不能把该帧
  自动归因于 request；
- 未进入请求方言 sweep 的消息不是 timeout；PX4 `uAvionix.xml` 辅助方言行保持
  `NOT_ATTEMPTED`；
- 保留的 `none_iris` 失败是 startup `HEARTBEAT` timeout，不是某条消息请求的 timeout。

## 复现命令

以下命令会生成或刷新采集/派生产物，不属于只读验收。ArduPilot collector 会拒绝
覆盖已有 `runs/<Vehicle>`；需要重采时应在保留当前证据的独立工作副本中执行。

```bash
cd /home/lqq/project/TAFuzz

python3 benchmark/extraction_runs/milestone6/ArduPilot/collect_runtime.py
python3 benchmark/extraction_runs/milestone6/PX4/capture_px4_runtime.py \
  --capture-id PX4-M6-MC-SIHSIM-QUADX-I42-20260718

python3 benchmark/scripts/merge_runtime_evidence.py
python3 benchmark/scripts/build_property_catalog.py --stage 6
python3 -B benchmark/scripts/apply_runtime_catalog.py
```

重建顺序必须保持为“采集 manifest → merge runtime evidence → Stage 6 property catalog →
runtime MAVLink overlay”。聚合验收不会自动执行这些写入命令。

## 只读验证命令

从工作区根目录运行完整聚合验收：

```bash
python3 benchmark/scripts/validate_milestone6.py
```

聚合器会打印实际调用的精确子命令、cwd、退出码相关输出和总 checks 数。默认调用：

```bash
python3 benchmark/scripts/validate_runtime_capture.py
python3 benchmark/scripts/validate_property_catalog.py --stage 6
python3 -B benchmark/scripts/apply_runtime_catalog.py --check
```

仅调试聚合逻辑、暂不调用子验证器时可运行：

```bash
python3 benchmark/scripts/validate_milestone6.py --skip-subvalidators
```

独立静态命令的精确路径是：

```bash
python3 benchmark/mavlink_catalog/validate_catalog.py
```

该独立 validator 会刷新 `benchmark/mavlink_catalog/validation_report.json`，因此为了
遵守本验收的只读范围，聚合器不把它作为子进程调用。聚合器直接只读复核静态
manifest/hash/层语义；runtime overlay 则由 `apply_runtime_catalog.py --check` 在内存中
重建并逐字节比较，不写文件。

## 最终验收结果

在 `/home/lqq/project/TAFuzz` 执行：

```bash
python3 benchmark/scripts/validate_milestone6.py
```

最终结果为 `PASS`，共 `1035` checks、`0` failures。聚合器复核了：

- `111` 个 manifest artifact 引用的存在性和 SHA-256；ArduPilot 清单同时复核 byte count；
- `53` 个 JSON 文件；
- `14` 个 JSONL 文件、共 `31951` 条记录；其中唯一允许为空的是保留的 PX4
  pre-heartbeat 失败尝试流；
- `7` 个 CSV 读取，共 `10061` 行；
- `4` 个 `COMPLETE` profile 和 `15` 条 property/runtime-parameter 绑定；
- 静态 support matrix `995` 行，以及 runtime overlay `1307` 条 profile/static-definition
  主行和 `3` 条 ArduPilot `BAD_DATA` 补充行；
- `3` 个只读子验证器，全部返回 `0`。

Stage 6 property 子验证结果为：`13` 个 properties、`46` 个 atomic propositions、
`13` 个 time contracts、`15` 个 concrete instances。实例状态只包含
`INSTANTIATED_UNVALIDATED`、`DISABLED_BY_RUNTIME_CONFIGURATION`、`NEEDS_CONTEXT` 和
`NOT_FORMALIZED`，没有实现符合性 verdict。
