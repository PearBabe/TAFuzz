# PGFuzz 当前 ArduCopter 动态分析适配器用户手册

## 1. 交付范围

本目录把 PGFuzz 的“逐个输入，观测哪些飞控状态发生变化”工作流迁移到当前
ArduCopter 软件在环仿真版本。原 PGFuzz 制品位于
`baseline/pgfuzz/ArduPilot/Dynamic analysis`，适配器不会改写它。

当前冻结身份、上游文件摘要和兼容约束分别见：

- `data/upstream_manifest.json`：源码提交、二进制和上游文件身份；
- `UPSTREAM_COMPATIBILITY.md`：PGFuzz 文本输入输出兼容契约；
- `data/safety_policy.json`：允许执行、需要前置条件和禁止默认执行的分类规则。

本实现已经通过指定的三项冒烟测试，但**没有运行全量 `current_safe_full`**。
全量实验由用户按照第 6 节执行。

## 2. 术语与机器状态图例

- **PGFuzz**：`Policy-Guided Fuzzing`，策略引导模糊测试。本任务迁移的是它的
  动态输入—状态映射，不是其完整模糊测试调度器。
- **SITL**：`Software in the Loop`，软件在环仿真。当前 ArduCopter 飞控逻辑
  在主机进程内运行，传感器和飞行动力学由仿真模型提供。
- **MAVLink**：`Micro Air Vehicle Link`，微型飞行器通信协议。适配器用它下载
  参数、写入参数、发送命令、覆盖遥控通道并采集状态。
- **pymavlink**：MAVLink 的 Python 消息构造与解析库。本机已验收版本为
  `2.4.49`。
- **PWM**：`Pulse-Width Modulation`，脉宽调制。这里的微秒值用来表达遥控通道
  位置，例如 `RC1=1700`。
- **ACK**：`Acknowledgement`，确认消息。`COMMAND_ACK` 表示飞控是否接受命令；
  它不自动证明命令造成了预期状态效果。
- **JSON**：`JavaScript Object Notation`，层次化结构数据格式；适合保存完整证据。
- **CSV**：`Comma-Separated Values`，逗号分隔表格格式；适合表格工具读取摘要。
- **JSONL**：`JSON Lines`，每行一条 JSON 记录；适合追加保存试验和消息流。
- **主机单调时钟**：`CLOCK_MONOTONIC_NS`，只保证本机事件排序和持续时间不受
  系统时间回拨影响。它不是飞控内部事件的真实发生时刻。

三类输入保持 PGFuzz 语义：

- `INPUT_P`：`Parameter Input`，普通配置参数输入；
- `INPUT_C`：`Command Input`，命令、模式和遥控输入；
- `INPUT_E`：`Environmental Input`，当前以 `SIM_*` 命名的仿真环境参数。

效果状态：

- `CONFIRMED_EFFECT`：确认影响；至少三次中的两次方向一致，且应用和恢复均确认；
- `LEGACY_ONLY_CANDIDATE`：仅旧规则候选；只有原 PGFuzz 标准差规则命中；
- `NO_OBSERVED_EFFECT`：本次模式、值和窗口内没有观测到影响；不等于永远无影响；
- `INCONCLUSIVE`：无法判断；输入未确认、恢复失败、消息不足或执行异常。运行器
  遇到输入/恢复验证失败或异常会关闭当前 SITL，并为后续工作项启动新会话。

目录执行分类：

- `READY_SAFE`：具备当前实现支持的合法值和恢复方法，默认计划可以执行；
- `REQUIRES_PRECONDITION`：需要模式、设备或状态准备，默认不执行；
- `REQUIRES_RESTART`：需要重启才能可靠生效，默认不执行；
- `DISRUPTIVE_EXCLUDED`：擦除、关机、终止、格式化等输入，默认排除；
- `UNKNOWN_METADATA`：类型、范围或可写性证据不足，默认不执行。

旧名称迁移状态：

- `EXACT`：旧名称在当前构建仍精确存在；
- `RENAMED`：有明确的当前名称映射；
- `REMOVED`：当前运行参数或命令目录没有该名称；
- `AMBIGUOUS`：可能对应多个当前实例，不能自动选择。

## 3. 运行前检查

从工作区根目录 `/home/lqq/project/TAFuzz` 执行：

```bash
test -x baseline/ardupilot/build/sitl/bin/arducopter
python3 -c "import pymavlink; print(pymavlink.__version__)"
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py --help
```

验收环境使用 Python 3.10.12、pymavlink 2.4.49 和冻结的 ArduCopter 二进制。
若二进制摘要或源码提交改变，应重新生成目录和冒烟证据，不能沿用本次结果。
`requirements.txt` 固定了已验收的 pymavlink 版本；本实现除 Python 标准库外不再
依赖其他 Python 包。

## 4. 生成当前输入目录

下面命令会启动一个隔离 SITL，通过 `PARAM_REQUEST_LIST` 请求全部参数，并以
`PARAM_VALUE` 响应中声明的总数检查是否完整：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py catalog \
  --run-id current-full-catalog
```

输出位于：

```text
output/pgfuzz_dynamic/current-full-catalog/
```

先审核：

```bash
python3 -m json.tool output/pgfuzz_dynamic/current-full-catalog/manifest.json
python3 -m json.tool output/pgfuzz_dynamic/current-full-catalog/migration_report.json
wc -l output/pgfuzz_dynamic/current-full-catalog/params.txt \
      output/pgfuzz_dynamic/current-full-catalog/envs.txt \
      output/pgfuzz_dynamic/current-full-catalog/cmds.txt
```

只有 `parameters_runtime.json.status` 为 `COMPLETE`，且唯一索引数等于飞控声明
总数时，目录构建才成功。当前最终冒烟下载结果是 1387/1387，零缺失。

## 5. 先预览，不执行输入

`--dry-run` 表示只生成计划，不写参数、不发命令、不覆盖遥控：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py run \
  --run-dir output/pgfuzz_dynamic/current-full-catalog \
  --preset current_safe_full \
  --dry-run \
  --shard-index 0 \
  --shard-count 8
```

审核 `experiment_plan.json` 的当前分片工作项和 `global_work_item_count` 全局工作项
总数。每次计划还会追加到 `experiment_plans.jsonl`，不会因下一分片而丢失。

需要先调试单一输入时，`--input` 可重复使用，且采用完整名称相等匹配：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py run \
  --run-dir output/pgfuzz_dynamic/current-full-catalog \
  --input SIM_BATT_VOLTAGE \
  --dry-run
```

## 6. 用户执行全量实验

推荐在**同一运行目录内顺序执行**八个分片。这样结果、断点和兼容文件会累计，
同时避免多个进程并发改写同一 JSON/CSV 文件。第一个分片可以不带 `--resume`；
后续分片必须带 `--resume`：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py run \
  --run-dir output/pgfuzz_dynamic/current-full-catalog \
  --preset current_safe_full --shard-index 0 --shard-count 8

python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py run \
  --run-dir output/pgfuzz_dynamic/current-full-catalog \
  --preset current_safe_full --shard-index 1 --shard-count 8 --resume
```

按同一形式继续索引 2 到 7。中断后重跑当前分片时也加 `--resume`；
`checkpoint.json.completed_work_ids` 中已有的工作项会跳过。会话目录编号跨命令持续
递增，因此先前 `sessions/session-NNNN/` 内的日志不会被覆盖。

同一运行目录不支持并发分片写入。若要并行运行，必须复制成彼此独立的运行目录
并分配不同 `--udp-port`；当前版本不会自动合并这些独立目录，因此最终需要单一
累计结果时应使用上面的顺序分片方式。

全量结束后：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py report \
  --run-dir output/pgfuzz_dynamic/current-full-catalog
python3 -m json.tool output/pgfuzz_dynamic/current-full-catalog/checkpoint.json
python3 -m json.tool output/pgfuzz_dynamic/current-full-catalog/manifest.json
```

只有 `manifest.json.full_campaign_complete=true` 才表示全局计划中的工作标识符都已
产生结果；该值不表示每项都是确认影响，也不表示飞控性质符合要求。

## 7. 冒烟测试

运行全部三项：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py smoke \
  --run-id my-smoke
```

只运行一项时可选择 `parameter`、`command` 或 `environment`：

```bash
python3 src/StaticAnalysis/runtime/pgfuzz_adapter/pgfuzz_dynamic.py smoke \
  --run-id my-environment-smoke --case environment
```

冒烟会新建目录；同名目录已存在时拒绝覆盖。验收标准见
`smoke_certificate.json`，状态必须为 `PASS`，且 `full_campaign_executed=false`。

## 8. 输出说明

每个运行目录的核心文件：

- `cmds.txt`、`envs.txt`、`params.txt`、`preconditions.txt`：PGFuzz 兼容输入；
- `results/*.txt`：仅确认影响，每行一个无类型前缀的兼容输入名；
- `results_legacy/*.txt`：仅原 PGFuzz 标准差规则的命中结果；
- `input_catalog.json/csv`：类型、当前值、范围、枚举、来源、恢复方法和执行分类；
- `input_state_effects.json/csv`：输入值、状态组、每轮方向、确认和恢复结果；
- `trials.jsonl`：每一轮基线、干预、恢复以及主机/飞控时间证据；
- `checkpoint.json`：累计完成标识符，供断点续跑；
- `manifest.json`：当前目标身份、目录规模、是否执行输入和是否完成全量；
- `report.md`：中文汇总报告；
- `logs/`、`sessions/` 或 `smoke_cases/*/logs/`：原始 MAVLink 与 SITL 日志。

PGFuzz 文本消费者仍看到 `RC1`；结构化字段 `protocol_field` 同时保存精确身份
`RC_CHANNELS_OVERRIDE.chan1_raw`。这样既不破坏旧输入输出，又不会把协议字段
语义压扁成一个模糊名称。

## 9. 从性质相关输入到结果文件的完整实例

以“地面站失联后进入失效保护”的性质相关状态为例：

1. 当前目录从飞控实际参数响应确认 `FS_GCS_TIMEOUT`、`FS_GCS_ENABLE` 和
   `FS_OPTIONS` 存在，并取得类型和原值。
2. 冒烟把 `FS_GCS_ENABLE` 设为 1、`FS_OPTIONS` 设为 0，正常解锁并进入
   `GUIDED` 引导模式；没有使用强制解锁。
3. 每一轮先把 `FS_GCS_TIMEOUT` 设为原值 5 秒，持续发送地面站心跳，然后停止
   发送，记录飞控离开引导模式或产生地面站失联文本消息的主机观测延迟。
4. 干预阶段把超时改为 2 秒并重复同样序列；恢复阶段写回 5 秒并再次观测。
5. 三轮基线/干预/恢复延迟约为
   `5.25/2.31/5.30`、`5.29/2.31/5.30`、`5.30/2.31/5.30` 秒。三次方向均为
   `DECREASE`，即延迟下降；恢复均回到容差内。
6. 聚合结果为 `CONFIRMED_EFFECT`，确认状态组为 `status`，因此兼容输出
   `results/status.txt` 出现一行 `FS_GCS_TIMEOUT`。
7. 最后恢复 `FS_GCS_TIMEOUT`、`FS_GCS_ENABLE`、`FS_OPTIONS`，切换着陆模式并
   确认解除锁定。证据在最终验收目录的
   `smoke_cases/parameter/case_evidence.json` 和原始 MAVLink 日志中。

这里证明的是：在记录的 SITL 模型、模式、前置条件和观察方式下，该输入能改变
性质相关状态的**观测触发延迟**。它不是 MITL 性质符合性结论，也不能把主机接收
时刻解释成飞控内部事件时刻。

## 10. 当前限制

- `current_safe_full` 的通用执行器不会自动为每个参数构造飞行中前置状态；需要
  专门状态准备的输入会被排除或在当前上下文得到 `NO_OBSERVED_EFFECT`。
- 当前只为两个普通 MAVLink 命令提供通用合法参数配方；其他已识别命令保留在
  目录中，但默认标为需要前置条件，不发送随机参数。
- 改进判定覆盖数值状态、数值编码的模式/解锁/系统状态以及显式实现的地面站
  失联事件延迟；文本事件仍完整记录，但没有对任意文本自动推断因果关系。
- 结果只适用于清单中冻结的提交、二进制、`quad` SITL 模型、模式、输入值和
  观测窗口。真实硬件、其他机型和其他提交必须重新建目录和验证。
