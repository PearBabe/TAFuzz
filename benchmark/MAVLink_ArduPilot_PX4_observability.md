# ArduPilot / PX4 MAVLink 传输对象与性质可观测性审计指南

> 审计日期：2026-07-18。本文只描述冻结版本的 MAVLink 定义、源码静态证据和四套 SITL profile 的运行时观测，不作“实现满足规范”或“MITL 性质成立/违反”的判断。

## 1. 先看结论：同一条消息有五个不能混写的层次

对性质驱动 fuzz，XML 中“有这条消息”、源码中“出现过标识符”、SITL 默认“发过这条消息”、显式请求后“看到了同 ID 帧”、以及“某个原子命题可由该字段判真”是五件不同的事。本文采用下面的证据链：

| 层次 | 本文含义 | 最低证据 | 允许的结论 | 不允许的结论 |
|---|---|---|---|---|
| XML 方言全集 | 消息、字段或 `MAV_CMD` 位于冻结构建入口的递归 include 闭包 | 冻结 XML、构建入口、文件哈希 | 生成器知道该定义及其 wire layout | 飞控会收、会发、默认发或可请求 |
| 源码静态支持候选 | 冻结飞控源码中找到 send/pack/decode/handler/command 引用 | 静态位置与方向启发式 | 存在可复核的 TX、RX/handler 或其他候选引用 | 路径可达、构建条件满足、默认 rate 非零 |
| 默认 SITL 基线 | 指定 profile、端口和 12 秒无消息请求窗口内真实收到 | 有方向、SYSID/COMPID、host monotonic time 的 capture | 该 profile 在该次窗口发出了该帧 | 所有 profile 都默认发送；未出现的状态没有发生 |
| 显式请求窗口 | 串行发送 `MAV_CMD_REQUEST_MESSAGE (512)` 后记录 ACK 与同 ID 帧 | 请求动作、ACK、时间窗口和 baseline 对照 | 该次请求结果及窗口内观测事实 | `FAILED`/`DENIED` 等同全局不支持；同 ID 帧必由请求造成 |
| 原子命题可观测性 | 字段的来源、方向、实例、有效值和时间域足以支持某个 AP | AP 到消息/字段/参数的逐项绑定 | 在明确假设下可直接或间接观测该 AP | 消息出现即性质满足；候选消息缺失即 AP 为假 |

因此，审核一条 MITL 性质时必须沿这条链逐层查证，不能从 XML 定义直接跳到性质判定。完整运行时汇总见 [runtime_evidence.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_evidence.json)，逐消息叠加矩阵见 [runtime_message_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_message_support_matrix.csv)。

## 2. 冻结对象、方言入口与完整数据表

### 2.1 版本与规模

| 系统 | 冻结飞控提交 | 冻结 MAVLink 提交 | 实际构建入口 | XML 文件 | 消息 / 字段 | `MAV_CMD` / 槽位 | 静态配置参数行 |
|---|---|---|---|---:|---:|---:|---:|
| ArduPilot | `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` | `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472` | `all.xml` | 17 | 352 / 2708 | 216 / 1512 | 16904 |
| PX4 v1.17.0 SITL | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` | `33af200d25ec6f0925b49b1ba82bbf1294ea5f72` | 主入口 `development.xml`，辅助生成 `uAvionix.xml` | 5 | 251 / 2018 | 176 / 1232 | 1418 |

两系统合计是 603 个“系统版本内的消息定义记录”，不是 603 个互不重复的全局消息；`common.xml` 中同一消息会分别按两个冻结版本保存。ArduPilot 352 条中，206 条源于 `common.xml`、73 条源于 `ardupilotmega.xml`，其余来自 ASLUAV、storm32、uAvionix、development、测试等方言。PX4 251 条中，226 条源于 `common.xml`、13 条源于 `development.xml`、8 条源于 `uAvionix.xml`，其余 4 条来自 minimal/standard。

这里有两个关键边界：

- ArduPilot 的 `all.xml` 确实是该冻结构建脚本的输入，但它也包含 development、test、python array test 和其他项目方言；这是**生成全集**，不是 ArduPilot 运行支持表。
- PX4 `px4_sitl_default` 选择 `development`，构建脚本还生成 `uAvionix` 头；生成头文件同样不证明当前实例收发其中每条消息。

冻结入口、递归 include、XML 哈希和输出哈希均在 [manifest.json](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/manifest.json)；目录内部一致性检查在 [validation_report.json](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/validation_report.json)。验证状态 `PASS` 只表示目录、哈希、字段 offset、计数等彼此一致，不表示协议实现或性质通过。

### 2.2 “所有消息能传什么”应查哪一张完整表

正文不手工重抄 4726 个字段，避免丢字段、错单位或把两个冻结版本静默合并。逐条事实由以下完整数据集给出：

| 审核目标 | 完整表 | 一行/对象记录的内容 |
|---|---|---|
| 所有消息与字段 | [messages_and_fields.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/messages_and_fields.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/messages_and_fields.json) | 系统/提交、入口方言、msgid/name/描述、来源 XML/行、min/max payload、WIP/deprecated/superseded、XML 顺序、wire 顺序/offset/大小、extension、类型/数组、单位、枚举、default/invalid、字段说明 |
| 所有命令与 `param1..7` | [commands.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/commands.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/commands.json) | 每个命令固定七行；命令语义、carrier 相关属性、location/destination/mission-only、每槽 label/单位/枚举/范围/步长/default/reserved、来源与重复定义 |
| 所有静态配置参数 | [configuration_parameters.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/configuration_parameters.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/configuration_parameters.json) | 系统/vehicle scope、参数名、类型、静态 default 及来源、说明、单位、范围、枚举/bitmask、重启/volatile、源码位置置信度、目录边界 |
| 静态 TX/RX 候选 | [static_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/static_support_matrix.csv) | 603 条消息与 392 条命令的纯静态矩阵：方言定义、源码静态引用状态、TX/RX/other 计数与位置、扫描范围和解释限制 |
| 四 profile 运行 overlay | [actual_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/actual_support_matrix.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/actual_support_matrix.json) | 每个 selected profile × 该系统静态消息定义的 1307 个主行，另加 3 个 `BAD_DATA` 非 catalog 观测行；分列 baseline、请求、ACK、静态方向和解释限制 |
| 所有时间候选 | [time_fields.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/time_fields.csv) | 消息字段、命令槽和配置参数中的 timestamp/duration/rate 等候选、单位、时间角色、clock domain、歧义与分类依据 |

静态目录生成时尚未运行 SITL，所以 `static_support_matrix.csv` 中的 `default_runtime_observation_status=NOT_RUN_NO_CAPTURE` 是历史上正确、但不应覆盖 Milestone 6 的列。`actual_support_matrix.*` 是独立的运行 overlay；其输入/输出 hash、1307+3 行和状态分布由 [runtime_catalog_manifest.json](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/runtime_catalog_manifest.json) 复核。两张矩阵分层保存，不能把运行值回写成“纯静态目录已经证明运行支持”。

## 3. 三类“参数”必须严格分开

### 3.1 消息字段（message field）

消息字段是在某个特定 `msgid` payload 中传输的定长 typed member，例如 `ATTITUDE.time_boot_ms`、`HEARTBEAT.base_mode`、`GPS_RAW_INT.vel`。绑定至少要保留：系统与 MAVLink 提交、message/field、primitive type、数组长度、extension、单位/multiplier、enum/bitmask、invalid、实例键、生产者 SYSID/COMPID、方向和 clock domain。

仅写 `time_usec` 或 `custom_mode` 不够，因为同名字段在不同消息中可能有不同语义。payload 本身也不是 self-describing：必须由 `msgid` 选择与冻结方言兼容的 decoder。

### 3.2 `MAV_CMD` 的 `param1..param7`

`MAV_CMD` 是一个具体命令枚举项；它的七个语义槽由该命令定义解释，并通过 `COMMAND_LONG`、`COMMAND_INT` 或 Mission Protocol carrier 传输。`param1` 在命令 A 中的含义不能复制到命令 B，更不能当成飞控配置参数。

完整命令表对每条命令固定输出七个槽。XML 未声明的槽标为 `unspecified`；只有明确 `reserved` 的证据才标 reserved。PX4 冻结 `development.xml` 中 `MAV_CMD_ODID_SET_EMERGENCY` 的 `param5` 有两个相同 XML 条目，目录显式保存 `duplicate_identical_xml_entries`，没有擅自猜成其他槽位。

命令 carrier 还会影响位置参数的编码和 frame 解释，应按具体命令及 [MAVLink Command Protocol](https://mavlink.io/en/services/command.html#use-command-int-or-command-long) 审核。特别是 `COMMAND_ACK.command=512` 只说明 ACK 对应 `MAV_CMD_REQUEST_MESSAGE`，ACK payload 不携带被请求的 msgid。

### 3.3 飞控配置参数（firmware configuration parameter）

这类对象是 `FS_GCS_TIMEOUT`、`COM_RC_LOSS_T` 等版本化配置状态。参数名、native type、静态 metadata、当前运行值、传输协议、持久化或重启语义是独立维度。它与 `MAV_CMD paramN` 没有通用对应关系，也不等于任意消息字段。

- ArduPilot 静态表按 Copter 5702、Plane 5747、Rover 5455 行保存；同名参数在多个 vehicle scope 出现时保留多行。静态 default 只在源码宏可机械对应时保留未求值表达式，不能代替运行值。
- PX4 1418 行是最大深度四层的官方源码 metadata 扫描全集，其中 913 个 Float、505 个 Int32；它不是经 CMake/Kconfig 解析后的精确 `px4_sitl_default` 参数集合，也不包含所有临时生成项。

## 4. MAVLink 帧、payload、数组和 metadata

### 4.1 帧结构

| 项 | MAVLink 1 | MAVLink 2 |
|---|---|---|
| STX | `0xFE` | `0xFD` |
| 含 STX header | 6 bytes | 10 bytes |
| msgid | 8 bit | little-endian 24 bit |
| payload | 0..255 bytes | 0..255 bytes，允许尾部零截断 |
| checksum | 2 bytes | 2 bytes |
| 可选签名块 | 无 | 13 bytes |
| 最大帧长 | 263 bytes | 未签名 267 bytes；带可选块 280 bytes |
| extension 字段 | 不传输 | 可传输 |

MAVLink 1 header 依次含 `magic,len,seq,sysid,compid,msgid`。MAVLink 2 header 还含 `incompat_flags`、`compat_flags`，并把 msgid 扩为 3 bytes。`sysid/compid` 标识**发送者**；目标通常位于 payload 的 target 字段中。`seq` 是每发送者 uint8 包序号，只能辅助判断丢包/重排，模 256 回绕，不是时间戳或全局事件序号。规范细节见 [Packet Serialization](https://mavlink.io/en/guide/serialization.html#packet_format)。

### 4.2 字段顺序与 extension

基础字段按 primitive element size 8、4、2、1 bytes 稳定降序排列；同尺寸保持 XML 声明顺序。数组按**元素类型尺寸**排序，不按数组总字节数排序。`<extensions/>` 后字段只属于 MAVLink 2，保持 XML 顺序追加，且不计入 CRC_EXTRA。

MAVLink 2 可省略 payload 尾部连续零 bytes，decoder 恢复为零；第一个 payload byte 不会被截掉。因此短于 `message_payload_max_length` 的合法帧不应被判 malformed。旧 sender 不认识新 extension 时，receiver 解码得到零；这个零不能证明 sender 显式测得/发送了零。详见 [Message Extensions](https://mavlink.io/en/guide/define_xml_element.html#message-extensions-mavlink-2)。

完整 CSV 同时保留 `field_xml_order` 与计算后的 `field_payload_wire_order/offset`。ArduPilot 现有生成头对 352 条消息、2708 个字段的 length/offset 交叉检查为 0 个不一致。

### 4.3 字段解释规则

- `units` 是物理或编码单位；`multiplier` 只应用一次，禁止再叠加经验缩放。
- 数组必须保留元素 primitive type 和长度。`char[N]` 只有在字段定义说明终止规则时才能当字符串；其他数组是逐元素值。
- enum 未知值保留为 `UNKNOWN(raw)`；bitmask 是可组合位，不能按互斥枚举解码。
- `invalid` 只采用冻结 XML 的精确定义，包括 scalar、数组位置、`[value]`、`[value:]` 和 NaN；NaN 用 `isnan` 判断。没有 invalid 属性不能人工发明 sentinel。
- 有 `instance` 语义的字段必须把实例值纳入 observation key，避免把多个传感器/电池/执行器流合并。
- WIP、deprecated、superseded 是 lifecycle metadata，与是否支持、是否观测分开保存。

两个冻结版本不能静默套用同一滚动页面。例如 ArduPilot 冻结 `COMMAND_INT/LONG` 参数字段没有 field-level invalid 属性，而 PX4 冻结版本给 float 参数 NaN、`COMMAND_INT.x/y` 给 `INT32_MAX`；应按系统各自 XML 解码。ArduPilot 冻结 `TIMESYNC` 没有 target extension，PX4 冻结版本有 `target_system/target_component`。完整冲突规则见 [mavlink_official_source_audit.md](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/mavlink_official_source_audit.md)。

## 5. 消息族、微服务与方向

MAVLink “微服务”是多条消息、命令、状态机和重试规则组成的协议族，不是单一消息，也不是该族所有操作均被任一飞控实现的保证。

| 协议族 | 典型传输对象 | 对性质观测的用途 | 必须保留的限制 |
|---|---|---|---|
| Heartbeat / discovery | `HEARTBEAT`、SYSID/COMPID、type/autopilot/base_mode/custom_mode/system_status | 活跃来源、armed 位、模式候选 | 无嵌入事件时间；包间隙不等于飞控内部 accepted-update 计时 |
| Command | `COMMAND_LONG/INT`、特定 `MAV_CMD param1..7`、`COMMAND_ACK` | 注入动作、记录接受/拒绝/进行中 | ACK 的 command/result/progress/result_param2 按命令解释；accepted 不一定等于动作完成 |
| Regular Parameter | `PARAM_REQUEST_LIST/READ`、`PARAM_VALUE`、`PARAM_SET` | 读取运行配置和性质时间阈值 | 4-byte float carrier，有 byte-wise/C-cast 差异；缓存同步不保证 |
| Extended Parameter | `PARAM_EXT_*`、`PARAM_EXT_ACK` | 128-byte typed/custom 参数交换 | 方言有定义不证明飞控主配置表通过此协议暴露 |
| Message streaming | `SET_MESSAGE_INTERVAL`、`REQUEST_MESSAGE`/command 512、默认 stream 配置 | 区分默认周期流和按需 one-shot | 通用命令路径不证明每个 msgid 可请求；总带宽会影响 rate |
| Time synchronization | `SYSTEM_TIME`、`TIMESYNC` | boot/Unix 映射和时钟 offset 候选 | 单次交换不证明同步；消息自己的 event time 不能由 TIMESYNC 字段直接替代 |
| Mission | mission item/current/reached/ack 等 | 路径、任务索引和任务事件候选 | 角色、方向、mission type、frame 与 ACK 状态必须一起解释 |
| Telemetry / setpoint | position、attitude、sensor、battery、RC、target/setpoint 等 | 直接值、派生状态或受控输入 | 报告值、目标值、命令输入不能混成同一 proposition |
| Event / text | `EVENT`、`STATUSTEXT` | 带 metadata 的事件候选或人读后果 | 文本可能丢失、聚合或缺时间；EVENT 需要匹配固件 component metadata/ID |

PX4 v1.17 的 [Supported Microservices](https://docs.px4.io/v1.17/en/mavlink/protocols.html#supported-microservices) 只表示某些服务“以某种形式”受支持，不能推出族内每条消息、每个角色或每项操作。PX4 TX 需要 stream list/`MavlinkStream` 证据，RX 需要 handler、decode、publication、dispatch 证据，分别见 [Streaming Messages](https://docs.px4.io/v1.17/en/mavlink/streaming_messages.html#streaming-on-request) 和 [Receiving Messages](https://docs.px4.io/v1.17/en/mavlink/receiving_messages.html#steps)。ArduPilot 的多种 rate/request 路径见 [Requesting Data](https://ardupilot.org/dev/docs/mavlink-requesting-data.html#using-request-message)。

静态扫描结果也必须按方向读：

| 系统 | 消息定义 | 有 TX 候选 | 有 RX/handler 候选 | 消息静态引用实体 | 命令静态引用实体 |
|---|---:|---:|---:|---:|---:|
| ArduPilot | 352 | 130 | 99 | 197 | 129 |
| PX4 | 251 | 111 | 80 | 150 | 60 |

这些数字来自排除 submodule/build/test/example 后的词法扫描。宏、生成代码、内部 ID 映射或构建条件可能造成漏报；`NO_REFERENCE_FOUND_BY_HEURISTIC_SCAN` 不等于不支持。相反，找到引用也不等于路径在当前 profile 可达。

还要防止路由误归因：在飞控链路上抓到的帧可能是转发帧；只有 source SYSID/COMPID、接口、方向和 routing context 一致时，才能归因给飞控组件。ArduPilot 官方路由语义见 [MAVLink Routing](https://ardupilot.org/dev/docs/mavlink-routing-in-ardupilot.html#detailed-theory-of-mavlink-routing)。

## 6. 四套默认 SITL profile 与显式请求结果

### 6.1 采集阶段

四套被选 capture 均为 `COMPLETE`，但都是 idle SITL 能力观测而非飞行性质测试：

1. startup/warmup：等待目标 `HEARTBEAT` 并分离启动流量；
2. baseline：约 12 秒，不发送参数请求或消息请求；ArduPilot baseline 没有 harness heartbeat，PX4 为保持 GCS discovery 发送 collector heartbeat；
3. parameter download：`PARAM_REQUEST_LIST`，必要时只读修复缺失 index/命名参数；没有 `PARAM_SET`；
4. request sweep：逐条串行发送 command 512，ACK 与同 ID 窗口观测分别记录；
5. ArduPilot 另有 selected、nonpersistent message-interval sample；PX4 没有改 stream interval、arming、mode 或 actuator。

### 6.2 逐 profile 事实

| Capture / profile | 收到的记录 | 汇总去重 | 进入消息矩阵的 MAVLink ID | baseline 去重 | 运行参数完整性 | 请求范围 | 请求窗见同 ID | ACK 结果 |
|---|---:|---:|---:|---:|---|---:|---:|---|
| `ardupilot-copter-m6` / ArduCopter `quad`, SYSID 151:1 | 2733 | 51 | 50 | 2 | 1387/1387，missing 0 | 352/352 | 45 | Accepted 80；Failed 272 |
| `ardupilot-plane-m6` / ArduPlane `plane`, SYSID 152:1 | 4326 | 52 | 51 | 33 | 1440/1440，missing 0 | 352/352 | 46 | Accepted 82；Failed 270 |
| `ardupilot-rover-m6` / Rover `rover`, SYSID 153:1 | 3754 | 46 | 45 | 26 | 1271/1271，missing 0 | 352/352 | 40 | Accepted 81；Failed 271 |
| `PX4-M6-MC-SIHSIM-QUADX-I42-20260718` / `px4_sitl_default sihsim_quadx`, SYSID 43:1 | 14748 | 54 | 54 | 33 | index 0..899 完整；941 `PARAM_VALUE`；901 个唯一名 | 243/243 primary | 47 | Accepted 47；Denied 196 |

ArduPilot 的“汇总去重”比消息矩阵多 1，是 MAVLink framing 前的 plain-text boot banner 被 pymavlink 记为 `BAD_DATA`；它不是方言消息。PX4 的 901 个参数名比 `param_count=900` 多 1，是 index 65535 的 `_HASH_CHECK`，不是缺失或重复 index。

PX4 方言全集有 251 条消息，request sweep 只覆盖 `development.xml` 主入口生成的 243 个唯一 msgid；8 条 `uAvionix`-only 定义明确标为 `NOT_IN_SWEEP`，不是 timeout。第一次 `none_iris` 启动尝试因等待外部 simulator、30 秒内没有 autopilot heartbeat 而保留为 failed attempt；进程已清理，它不是消息级 timeout，也不是飞控性质结果。证据见 [capture_attempts.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/capture_attempts.json)。

### 6.3 baseline、request window 与 ACK 的正确解释

逐消息矩阵的 profile 分类为：

| Profile | `DEFAULT_STREAM` | `REQUEST_WINDOW` | `ACCEPTED_NO_MATCH` | `FAILED`/`REQUEST_ACK_DENIED` | `NOT_IN_SWEEP` |
|---|---:|---:|---:|---:|---:|
| Copter | 2 | 44 | 36 | 270 | 0 |
| Plane | 33 | 16 | 36 | 267 | 0 |
| Rover | 26 | 16 | 42 | 268 | 0 |
| PX4 SIH | 33 | 21 | 0 | 189 | 8 |

这里的分类不是支持等级排序。必须应用以下规则：

- 四次 sweep 的命令级 `unsupported=0`、`no_response=0`。ArduPilot 对大量未在当前请求窗形成 one-shot 返回的 msgid 给出 `MAV_RESULT_FAILED`；PX4 给出 `MAV_RESULT_DENIED`。二者都只是该 profile、该时刻、该 command 512 请求的 ACK 结果，**不能重命名为“消息不支持”**。
- `COMMAND_ACK` 不含 requested msgid。采集器用串行请求与时间窗口相关联，降低但不能消除 late ACK 歧义。
- request 后看到同 ID 只是一项时间相关事实。若该消息 baseline 已周期出现，不能认定请求导致返回；因此矩阵保留 `AMBIGUOUS_BASELINE_PERIODIC`。
- PX4 请求 msgid 77 `COMMAND_ACK` 时得到 Denied，但窗口内又看到一帧 `COMMAND_ACK`，因为每个 command 512 自己都会产生 ACK；这是“同 ID 不等于因果响应”的直接例子。
- PX4 `HEARTBEAT` 请求 Accepted，却在该请求窗口没有 matching frame，而 baseline 中存在；不能因窗口短就改成不支持。
- Copter baseline 只有 `HEARTBEAT`、`TIMESYNC`，Plane/Rover baseline 更丰富。这是 vehicle/profile/channel/configuration 的实际差异，不是方言定义差异。

底层 merged runtime 表的 1307 行可在 [runtime_message_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_message_support_matrix.csv) 或 [JSON](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_message_support_matrix.json) 中按 `capture_id,message_id` 审核。字段同时保存 static TX/RX 计数、baseline/parameter/request phase count、ACK、matching count、classification、首末 host monotonic time 和解释限制。

面向人工审核的最终 profile overlay 是 [actual_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/actual_support_matrix.csv) 与 [JSON](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/actual_support_matrix.json)：1307 个 `PROFILE_STATIC_MESSAGE_DEFINITION` 主行完整覆盖四个 profile 与各自静态消息定义的笛卡尔积；另有 3 个 `RUNTIME_NON_CATALOG_OBSERVATION` 行保存 ArduPilot `BAD_DATA`。它还显式区分 PX4 的 8 个 auxiliary-dialect 未请求行，且 `static_requestable_evidence_status` 保持 `UNKNOWN_NO_EXPLICIT_REQUESTABILITY_FIELD_IN_STATIC_CATALOG`，没有从 TX token 猜 requestability。

### 6.4 原始运行时证据

- ArduPilot 总说明与 artifact hash：[README](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/README.md)、[manifest](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/manifest.json)。逐车权威流是 [Copter messages.jsonl](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/messages.jsonl)、[Plane messages.jsonl](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Plane/messages.jsonl)、[Rover messages.jsonl](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Rover/messages.jsonl)。三车 `.tlog/.raw` 均为 0 bytes，只是保留的失败辅助产物，不能作为 traffic 证据。
- PX4 总说明与 artifact hash：[README](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/README.md)、[manifest](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/manifest.json)。权威逐帧数据为 [mavlink_messages.jsonl](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/mavlink_messages.jsonl)，非空 raw capture 为 [mavlink_capture.tlog](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/mavlink_capture.tlog)。
- 各请求原始记录：[Copter](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/request_sweep.json)、[Plane](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Plane/request_sweep.json)、[Rover](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Rover/request_sweep.json)、[PX4](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/message_request_sweep.json)。

## 7. PARAM、PARAM_EXT 与完整运行参数快照

### 7.1 两种协议的 wire 差异

| 项 | Regular PARAM | PARAM_EXT |
|---|---|---|
| 消息 | `PARAM_REQUEST_READ/LIST`、`PARAM_VALUE`、`PARAM_SET` | `PARAM_EXT_REQUEST_READ/LIST`、`PARAM_EXT_VALUE`、`PARAM_EXT_SET`、`PARAM_EXT_ACK` |
| value carrier | `float`，4 bytes | `char[128]` |
| ID | `char[16]`；不足 16 个可读字符时 NUL，正好 16 时无 NUL | 对应扩展消息定义 |
| 类型 | `MAV_PARAM_TYPE`，实现不必支持枚举列出的全部类型 | UINT/INT 8..64、REAL32/64、CUSTOM 等 typed bytes |
| 编码风险 | byte-wise 或 C-style cast；后者 float 只有 24 bit integer precision | byte-wise typed/custom；仍要按类型和实现解释 |
| 写入结果 | `PARAM_VALUE` 广播当前值，没有 XML 提供的通用 benchmark timeout | `PARAM_EXT_ACK` 可区分 accepted/failed/in-progress/unsupported |

官方编码说明见 [Parameter Protocol](https://mavlink.io/en/services/parameter.html#parameter-encoding) 与 [Extended Parameter Protocol](https://mavlink.io/en/services/parameter_ext.html#parameter-encoding)。方言定义 PARAM_EXT 不证明 ArduPilot/PX4 的飞控配置表通过 PARAM_EXT 暴露；本次完整快照使用 regular PARAM，没有执行写入。

PX4 使用 byte-wise integer encoding 时，`PARAM_VALUE.param_value` 在通用浮点显示上可能极小或非有限。例如本次 `COM_DL_LOSS_T` 的 wire float 表面值为 `1.401298464324817e-44`，按 exact float32 bits 和 `param_type=INT32` 解码才是整数 `10`。审核必须使用快照中的 `wire_value_float32_hex`、`decode_policy`、`param_type` 和 `decoded_value`，不能把显示浮点直接当配置值。

### 7.2 四个完整快照

完整 4999 行归一化表见 [runtime_parameter_snapshots.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_parameter_snapshots.csv) 与 [JSON](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_parameter_snapshots.json)。每行保存 wire value/float32 hex、decoded value、decode policy、类型、index/count、source SYSID/COMPID、host monotonic time、源文件与源 hash。

| Profile | 完整性证据 | 逐 profile 原件 |
|---|---|---|
| ArduCopter | expected=received=unique=1387，missing 0 | [parameters.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Copter/parameters.json) |
| ArduPlane | expected=received=unique=1440，missing 0 | [parameters.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Plane/parameters.json) |
| Rover | expected=received=unique=1271，missing 0 | [parameters.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/ArduPilot/runs/Rover/parameters.json) |
| PX4 SIH | index 0..899 无缺失；941 帧；901 名含 `_HASH_CHECK` | [parameters_runtime.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/PX4/parameters_runtime.json) |

`param_count/index` 只在同一运行参数表和快照语境内解释。ArduPilot hidden parameters 会改变 count/index；参数集合也随 vehicle/release 变化，见 [ArduPilot Get/Set Parameters](https://ardupilot.org/dev/docs/mavlink-get-set-params.html#hidden-parameters)。PX4 参数定义和 flat Float/Int32 table 见 [PX4 Parameters & Configurations](https://docs.px4.io/v1.17/en/advanced/parameters_and_configurations.html#creatingdefining-parameters)。

### 7.3 与当前性质相关的实测时间参数

下列数值只说明这四套 profile 的运行值及其 domain 状态，不是从论文、源码 default 或人工经验补出来的规范阈值：

| 性质 | Profile / 参数 | 实测值 | 解释 |
|---|---|---:|---|
| `ARD-COPTER-GCS-001` | `FS_GCS_TIMEOUT` | 5.0 s | 运行时观测 |
| `ARD-COPTER-GUID-002` | `GUID_TIMEOUT` | 3.0 s | 运行时观测 |
| `ARD-COPTER-RTL-003` | `RTL_LOIT_TIME` | 5000 ms | 单位保留为参数 metadata 的 ms |
| `ARD-PLANE-TAKEOFF-001` | `TKOFF_TIMEOUT` | 0 s | `RUNTIME_OBSERVED_DISABLED_DOMAIN`，不能当有效正时限 |
| `ARD-ROVER-CRASH-002` | `CRASH_TIMEOUT` | 2.0 s | 运行时观测 |
| `ARD-ROVER-RCFS-001` | `FS_TIMEOUT` | 1.5 s | 运行时观测 |
| `ARD-SHARED-BATT-001` | 三车 `BATT_LOW_TIMER` | 均 10 s | 三个独立快照行，不是跨 vehicle 假定 |
| `PX4-MC-AUTODISARM-004` | `COM_DISARM_LAND` | 2.0 s | 运行时观测 |
| `PX4-MC-FLIGHTTIME-005` | `COM_FLT_TIME_MAX` | -1 s | `RUNTIME_OBSERVED_DISABLED_DOMAIN` |
| `PX4-MC-GCSLOSS-002` | `COM_DL_LOSS_T` | 10 s | INT32 byte-wise 解码值 |
| `PX4-MC-OFFBOARD-003` | `COM_OF_LOSS_T` | 1.0 s | 运行时观测 |
| `PX4-MC-RCLOSS-001` | `COM_RC_LOSS_T` | 0.5 s | 运行时观测 |
| `PX4-MC-RTLLOITER-006` | `RTL_LAND_DELAY` | 0.0 s | 当前值为零；其 enable/disable 语义仍按参数定义审核 |

15 个 property/profile 行及 source hash/index/count 在 [property_runtime_parameters.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/property_runtime_parameters.csv)。性质提取时仍须记录“阈值来自哪个参数、哪次运行、什么单位、disabled sentinel 如何定义”；不能仅把表中数字塞入公式。

## 8. 时间字段、时钟域、回绕与到达延迟

### 8.1 静态时间目录不是“时间戳列表”

| 系统 | 时间目录行 | 消息字段 | 命令槽 | 配置参数 | duration/rate 等无 epoch 行 |
|---|---:|---:|---:|---:|---:|
| ArduPilot | 2628 | 281 | 37 | 2310 | 2468 |
| PX4 | 463 | 256 | 33 | 174 | 328 |

目录采用高召回策略：timestamp、timeout、interval、frequency、pulse width、calendar component 都会进入。PWM 的 `us` 是脉宽，不是 clock timestamp；timeout/duration 没有 epoch。必须结合 `temporal_kind`、描述和 `clock_domain` 筛选。

### 8.2 必须登记的时间域

| 时间对象 | wire / 单位 | 正确语义 | 监控规则与禁止推断 |
|---|---|---|---|
| `time_boot_ms` | uint32 / ms | sender/component 的本次 boot domain | 只在同 source、同 boot session 比较；检测重启和回绕；不是 Unix 或 host boot |
| `SYSTEM_TIME.time_unix_usec` | uint64 / us | 发送者 master clock 的 Unix epoch 候选 | 与同帧 `time_boot_ms` 和 source identity 成对保存；XML 无 invalid 属性时不能擅自把 0 声明为协议 invalid；不保证精度或同步质量 |
| 任意 `time_usec` | 逐字段 | 可能是 Unix-or-boot、boot-only、synchronized Unix-or-boot 等 | 必须登记 `message.field`；不能因名字相同设成全局 clock |
| `SERVO_OUTPUT_RAW.time_usec` | uint32 / us | 冻结说明写 Unix-or-boot、由 magnitude 推断，但 width 与说明冲突 | 标 `AMBIGUOUS_SPEC`；不自动转 epoch；需要实现证据和运行校准 |
| `GPS_INPUT.time_week_ms + time_week` | uint32 ms + uint16 week | GPS 周内毫秒 + 周号 | 两字段一起采；周界正常；转 Unix 必须指定 time scale/leap-second policy |
| `TIMESYNC.ts1/tc1` | int64 / ns | request: `tc1=0,ts1=requester time`；response 镜像 ts1 并把 responder time 放 tc1 | 保存成对消息、RTT、offset、filter 和残差；单次帧或单向 request 不证明同步 |
| host arrival | `CLOCK_MONOTONIC_NS` | 采集主机到达/解析观察时钟，不是 payload 字段 | 用于本 capture 内 duration；记录 capture point/方向；没有误差预算时不能替代 source event time |
| PX4 tlog prefix | host UTC wall | 文件记录/回放时间 | 可用于 wall ordering，不替代 onboard field；还可能受 wall-clock 调整 |
| frame `seq` | uint8，无时间单位 | 每发送者丢包/重排线索 | 模 256；禁止当时间戳或事件编号 |

`time_boot_ms` 回绕值来自 wire type 与单位的审计计算，而不是 XML 常量：

- 模数：`2^32 × 1 ms = 4,294,967,296 ms = 49 days 17:02:47.296 ≈ 49.7102696 days`；
- 使用模比较时的半范围：`2^31 ms = 24 days 20:31:23.648 ≈ 24.8551348 days`；跨越更长间隔时仅凭两个样本不能唯一判定顺序。

`SERVO_OUTPUT_RAW.time_usec` 的 uint32 回绕为 `2^32 us = 4,294.967296 s = 71 min 34.967296 s`。现代 Unix epoch us 无法可靠装入该字段，且冻结 XML 没给 magnitude threshold，所以仍然是规格歧义，不能用经验阈值补齐。

GPS 周长 `604,800,000 ms` 是 `7×24×60×60×1000` 的审计算术；它不提供 GPS-to-Unix 的 leap-second/time-scale policy。`FLIGHT_INFORMATION.arming_time_utc` 和 `takeoff_time_utc` 虽然名字含 UTC，冻结说明明确是 since system boot，且注明字段误命名；应按说明而非名字绑定。

### 8.3 本次运行观察了什么时间

[runtime_time_field_observations.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_time_field_observations.csv) 共 128 个 capture/message/field 汇总：Copter 30、Plane 30、Rover 29、PX4 39。每行保留 XML 单位/描述、首末值、样本、首末 `CLOCK_MONOTONIC_NS` 和源 artifact。

可验证的例子包括：

- 四套 profile 都观察到 `SYSTEM_TIME.time_boot_ms/time_unix_usec`；但 Plane/Rover 启动早期的 Unix 字段可为 0。原值应保留，跨 clock 监控前仍要建立有效映射与不确定度。
- `GPS_RAW_INT.time_usec`、`HIGHRES_IMU.time_usec`、`SERVO_OUTPUT_RAW.time_usec` 的冻结说明都是 Unix-or-boot 候选；本次样本的量级可作为 profile 校准证据，但不能生成通用 magnitude 规则。
- PX4 `EVENT.event_time_boot_ms` 是明确的事件发生 boot time；`EVENT.id` 仍需对应冻结固件 metadata，不能只凭有事件帧就映射成某个 failsafe AP。
- 四套都观察到 `TIMESYNC` 字段；样本中 `tc1=0` 是发出的 sync request 形态，不是已经形成 request/response offset 样本集。
- PX4 `OPEN_DRONE_ID_LOCATION.timestamp=65535` 的 frozen field 定义给出 unknown sentinel；只有这种字段级证据才能把 65535 判 invalid/unknown。

### 8.4 MITL 到达时间误差

host arrival 发生在 firmware scheduling、序列化、传输/UDP 队列、routing、host socket queue、parser queue 之后。官方文档还指出 ArduPilot 参数/航点传输可能临时显著降低 stream rate，PX4 `MAV_X_RATE` 是总带宽上限并可压低各消息 rate，TIMESYNC RTT 会随拥塞和处理变化。

本次没有测出 scheduler/link/queue/capture delay 分布，也没有统一 embedded clock 映射的残差，因此没有事实依据给所有 MITL 性质写一个固定 epsilon。若 AP 的边界依赖不同 clock domain、或只以 host arrival 近似 source event time，应输出 `INCONCLUSIVE` 并记录缺少的 error budget，而不是自行采用 10 ms 等经验数值。ArduPilot 文档中的 MAVROS 10 ms RTT cutoff 是工具配置，不是 MAVLink 全局或本 benchmark 的 epsilon，见 [Clock/Time Synchronisation](https://ardupilot.org/dev/docs/ros-timesync.html#ardupilot-configuration)。

## 9. 原子命题（AP）可观测性

### 9.1 五类判定

Milestone 5 对 46 个 AP 做了静态审计；Milestone 6 只增加消息/参数 runtime 事实，没有自动改变 AP 结论：

| 类别 | 严格含义 | 全部 | ArduPilot | PX4 |
|---|---|---:|---:|---:|
| `DIRECT` | 在来源、方向、实例、有效性和时间要求均满足时，单个字段/运行参数可给出 AP 真值 | 9 | 3 | 6 |
| `DERIVED` | 要组合多字段、参数快照、模式或历史，且推导规则明确 | 6 | 3 | 3 |
| `CONDITIONAL` | 只有在 source isolation、配置、freshness、事件 metadata、受控历史等前提下可观测 | 13 | 7 | 6 |
| `INSTRUMENTATION_REQUIRED` | 标准 telemetry 只能看到后果，无法取得精确内部事件/计时起点/状态标志 | 16 | 12 | 4 |
| `UNRESOLVED` | 规范边界或 mapping 尚不足以唯一决定 | 2 | 0 | 2 |

完整 AP 审计见 [mavlink_ap_observation_audit.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone5/mavlink_ap_observation_audit.json)，逐性质候选字段见 [ArduPilot matrix](/home/lqq/project/TAFuzz/benchmark/ArduPilot/mavlink_observation_matrix.csv) 与 [PX4 matrix](/home/lqq/project/TAFuzz/benchmark/PX4/mavlink_observation_matrix.csv)。矩阵可能为同一 AP 给多条候选 observation，所以行级类别计数不等于 46 个 AP 的唯一类别计数。

### 9.2 典型边界

- `HEARTBEAT.base_mode` 可直接给 armed 位，但没有 disarm event time 或原因；“已 disarm”可 direct，“因某超时自动 disarm”不能只凭该位 direct。
- `EXTENDED_SYS_STATE.landed_state` 可给 landed state，landed transition 的精确起点仍需要 embedded timestamp 或 instrumentation。
- GCS/Guided/RC 输入包的 host send/arrival time 不等于飞控内部“accepted update”时间；精确 gap start 常为 `INSTRUMENTATION_REQUIRED`。
- `PARAM_VALUE + HEARTBEAT.custom_mode` 可派生 failsafe applicability，但必须保存参数快照时间、模式解释和 exception/selector 状态。
- `GPS_RAW_INT.vel` 可条件性支持速度命题，前提包括 cm/s scaling、fix/freshness 和所需速度定义一致。
- `STATUSTEXT` 是人读后果，可能缺失、聚合、语言变化且无精确 event time；不能单独代表内部 GCS-failsafe/crash flag。
- PX4 `EVENT` 有 `event_time_boot_ms`，但 AP 绑定还需要该冻结固件的 component metadata 和精确 event ID；仅观察到 `EVENT` 消息不够。
- PX4 Offboard 的“速率资格已经持续一段时间”等内部历史没有标准单字段，且等号边界若规范仍有歧义，应保持 `UNRESOLVED`。

### 9.3 M6 对候选消息的覆盖只是一层 overlay

按消息名称与 M5 候选集合做机械交集：

| 系统/profile | 候选消息名 | 本次任意阶段见到 | baseline 见到 | 主要缺口 |
|---|---:|---:|---:|---|
| ArduPilot Copter | 14 | 10 | 1 | 三类 inbound setpoint 未注入；`POSITION_TARGET_LOCAL_NED` 未见 |
| ArduPilot Plane | 14 | 9 | 8 | inbound setpoint 未注入；`ATTITUDE_TARGET`、`POSITION_TARGET_LOCAL_NED` 未见 |
| ArduPilot Rover | 14 | 9 | 8 | 同上 |
| PX4 SIH | 8 | 6 | 5 | `SET_ATTITUDE_TARGET`、`SET_POSITION_TARGET_LOCAL_NED` 未注入/未见 |

这只是**名称覆盖**，不证明候选方向、字段、source component、有效值、实例或 clock 均满足。尤其本次是 idle support capture，没有执行各性质的 input/state sequence；未发送 setpoint、arming、mode、actuator 等 campaign 动作。`PARAM_VALUE` 在 parameter phase 出现只能证明当前值被读到，不能证明阈值事件或 response path 已触发。

### 9.4 从帧升级到 `PROPERTY_DIRECT_OBSERVABLE` 的条件

只有以下条件全部成立，才可把一项 runtime frame evidence 用作 direct AP：

1. 使用正确系统的冻结 decoder，message/field/extension layout 与 hash 对应；
2. source SYSID/COMPID、接口与方向符合 AP，且不是未识别的转发帧；
3. enum/bitmask、单位/multiplier、invalid、array 和 instance 已按冻结 XML 解释；
4. 字段表达的对象与 AP 相同，例如 measured state、target、commanded input 没有互换；
5. AP 若含时间边界，使用的 event timestamp/clock/wrap/mapping 有依据，arrival-time error budget 足够；
6. 需要的参数、模式、exception、source isolation 或 history 均已同时观测并归档；
7. observation 不只是 message name matching，也不是 request window 的偶然周期帧。

任何一项不成立，就保持 `DERIVED`、`CONDITIONAL`、`INSTRUMENTATION_REQUIRED` 或 `INCONCLUSIVE`；不能为了让 MITL monitor 可运行而人工补值。

## 10. 每条性质的人工审核流程

建议按以下顺序审核 ArduPilot/PX4 的每条 MITL 性质：

1. **冻结身份**：记录 SUT commit、MAVLink commit、vehicle/profile、dialect entry、XML path/hash。
2. **确定对象类别**：逐个 AP 判断它对应消息字段、具体 `MAV_CMD paramN`、运行配置参数、函数内部状态，还是多对象组合。三类参数禁止混写。
3. **读取自然语义**：从完整 CSV/JSON 取 field/slot/parameter 的原文、单位、范围、enum/bitmask、invalid、lifecycle、source line；滚动网页只作解释或 drift 检查。
4. **分开静态方向**：查 TX、RX/handler、request path 和默认 stream 配置；静态 token 只作候选，不能当运行事实。
5. **叠加 runtime profile**：先看 baseline，再看 parameter phase，再看 request/interval phase；记录 SYSID/COMPID、方向、phase 和 capture id。ACK 与 matching frame 分列。
6. **建立时间注册表**：为每个 AP 写 `message.field`、wire type/unit、clock domain、wrap、zero/invalid、boot/reboot 分段、跨 clock mapping 和误差预算来源。
7. **写 AP 绑定**：列出 direct/derived/conditional/instrumentation/unresolved、推导表达式、所需历史、source isolation、候选函数/源码位置及 MAVLink 可见部分。
8. **最后才构造 MITL monitor**：数值阈值必须回指论文/官方文档/运行参数/实验配置中的一种明确来源；disabled domain 不生成虚假的正时限；无 epsilon 时不作跨时钟 PASS/FAIL。

这套流程的目标是提取“被测系统是否满足仍未知、可以被 fuzz 触发和监控”的外部性质，不是从源码中挑选已经实现的分支再把它改写成性质。源码位置用于解释 AP 与实现状态/变量的对应和决定是否需要 instrumentation，不作为性质已满足的证明。

## 11. 证据索引与官方来源

### 11.1 本地可复核证据

- 静态目录说明：[benchmark/mavlink_catalog/README.md](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/README.md)
- 纯静态支持候选：[static_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/static_support_matrix.csv)
- 四 profile 运行 overlay：[actual_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/actual_support_matrix.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/actual_support_matrix.json)、[runtime_catalog_manifest.json](/home/lqq/project/TAFuzz/benchmark/mavlink_catalog/runtime_catalog_manifest.json)
- 官方语义审计：[mavlink_official_source_audit.md](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/mavlink_official_source_audit.md) 与 [source_audit.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/source_audit.json)
- 四套 capture 汇总：[runtime_evidence.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_evidence.json)
- 逐消息 runtime overlay：[runtime_message_support_matrix.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_message_support_matrix.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_message_support_matrix.json)
- 完整运行参数：[runtime_parameter_snapshots.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_parameter_snapshots.csv)、[JSON](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_parameter_snapshots.json)
- 实测时间字段：[runtime_time_field_observations.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/runtime_time_field_observations.csv)
- 性质参数切片：[property_runtime_parameters.csv](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/property_runtime_parameters.csv)
- capture attempt 与失败边界：[capture_attempts.json](/home/lqq/project/TAFuzz/benchmark/extraction_runs/milestone6/capture_attempts.json)

### 11.2 官方协议与实现文档

所有网页于 2026-07-18 检索；系统特定 wire layout 仍以冻结 XML 为最高依据。

- MAVLink：[Serialization](https://mavlink.io/en/guide/serialization.html)、[XML Schema](https://mavlink.io/en/guide/xml_schema.html)、[Messages vs Commands](https://mavlink.io/en/guide/define_xml_element.html#messages-vs-commands)、[Command Protocol](https://mavlink.io/en/services/command.html)、[Parameter Protocol](https://mavlink.io/en/services/parameter.html)、[Extended Parameter Protocol](https://mavlink.io/en/services/parameter_ext.html)、[Time Synchronization](https://mavlink.io/en/services/timesync.html#sequences)、[SYSTEM_TIME](https://mavlink.io/en/messages/common.html#SYSTEM_TIME)、[TIMESYNC](https://mavlink.io/en/messages/common.html#TIMESYNC)、[GPS_INPUT](https://mavlink.io/en/messages/common.html#GPS_INPUT)。
- ArduPilot：[Requesting Data](https://ardupilot.org/dev/docs/mavlink-requesting-data.html)、[Get/Set Parameters](https://ardupilot.org/dev/docs/mavlink-get-set-params.html)、[Clock/Time Synchronisation](https://ardupilot.org/dev/docs/ros-timesync.html)、[MAVLink Routing](https://ardupilot.org/dev/docs/mavlink-routing-in-ardupilot.html)。这些 Dev pages 是 rolling 文档，不能覆盖冻结 XML 差异。
- PX4 v1.17：[Streaming Messages](https://docs.px4.io/v1.17/en/mavlink/streaming_messages.html)、[Receiving Messages](https://docs.px4.io/v1.17/en/mavlink/receiving_messages.html)、[Supported Microservices](https://docs.px4.io/v1.17/en/mavlink/protocols.html#supported-microservices)、[Parameters & Configurations](https://docs.px4.io/v1.17/en/advanced/parameters_and_configurations.html)、[MAVLink Instances](https://docs.px4.io/v1.17/en/peripherals/mavlink_peripherals.html#mavlink-instances)。

## 12. 尚未解决、审核时必须显式保留的限制

- 只有 ArduPilot Copter/Plane/Rover 三套 idle profile 和 PX4 单一 internal SIH multicopter profile；没有覆盖其他 airframe、board、MAVLink instance、port profile、外部 simulator、flight state 或 campaign action sequence。
- 当前 capture 证明采集点收到的 SUT outbound 帧以及 harness 已发送的动作；它不自动证明每个 inbound frame 已被飞控接受并更新了内部状态。
- 请求 sweep 是 one-shot runtime experiment；`FAILED`/`DENIED`、未匹配、baseline matching 均保留原义，没有据此生成全局 unsupported 表。
- PARAM 快照完整性只针对本次 regular PARAM 表；未证明每个参数可写、持久化方式、重启生效方式，也未证明主配置表可由 PARAM_EXT 枚举。
- 没有统一的 Unix/GPS/boot mapping 残差、link/queue delay 分布或通用 MITL epsilon。跨 clock 或 arrival-time 近似不足时应判 `INCONCLUSIVE`。
- `SERVO_OUTPUT_RAW.time_usec` 仍是冻结规格级 `AMBIGUOUS_SPEC`；滚动页面或样本量级不能替代版本实现证据。
- M5 AP audit 的 `NOT_RUN_NO_CAPTURE` 字样描述其当时静态阶段；M6 runtime overlay 只补充消息/参数/时间观察，没有执行每条性质，不作任何合规、满足或违反判定。
