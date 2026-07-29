# Milestone 6：MAVLink 官方语义与可观测性来源审计

- 审计日期：2026-07-18
- 审计对象：冻结的 ArduPilot、PX4 SUT 版本及其内嵌 MAVLink XML；MAVLink、ArduPilot、PX4 官方网页
- 下游用途：约束 `MAVLink_ArduPilot_PX4_observability.md` 的事实来源、字段解码、时间解释和可观测性分级
- 运行时状态：`NOT_RUN_NO_CAPTURE`
- 一致性判定：`NOT_PERFORMED`

## 1. 结论先行

1. **消息字段、`MAV_CMD` 的 `param1..7`、固件配置参数是三类不同对象。** 名字中都出现 “param” 不构成语义等价；不能把命令槽位当成持久配置，也不能把某个消息字段自动映射成配置参数。
2. **冻结 XML 只证明定义进入了该构建的方言闭包。** 它不证明 ArduPilot/PX4 接收、发送、默认发送、响应请求或在本次运行中实际出现该消息。最终文档必须分别记录 `DIALECT_DEFINED`、静态 RX、静态 TX、`REQUESTABLE` 与运行时观测。
3. **每个 SUT 必须使用自己的冻结 XML 解码。** 滚动的 `mavlink.io` 用于解释通用协议和发现规范漂移，不能覆盖冻结 XML 的字段、扩展、`invalid`、单位或描述。
4. **时间字段名不能决定时钟域。** `time_boot_ms`、`time_unix_usec`、每个具体消息中的 `time_usec`、`time_week_ms`、`TIMESYNC` 和主机到达时间必须分别处理。若属性所需事件没有共同且误差可控的时钟，则结论应为 `INCONCLUSIVE`，不能人工添加时间容差。
5. **本审计未证明任何消息的固件实际支持或运行时可观测性。** 所有此类结论仍需冻结源码的方向性证据或带方向的运行时抓包。

## 2. 权威边界

| 优先级 | 来源 | 在本 benchmark 中可支持的结论 | 不能支持的结论 |
|---|---|---|---|
| A | 对应 SUT 提交内的冻结 XML、构建入口、生成器头文件 | 该版本的线格式、类型、数组长度、扩展边界、单位、倍率、枚举、`invalid`、生命周期标记；方言闭包 | 固件实际 RX/TX、默认流、可请求、运行时出现 |
| B | 与版本配对的官方固件文档；PX4 仓库内冻结文档 | 该版本官方描述的实现路径和支持边界 | 某次构建/配置/运行必然启用 |
| C | ArduPilot Dev、PX4 版本站点等官方网页 | 官方实现说明和操作入口；网页是滚动内容时必须保留检索日期 | 覆盖冻结 XML；替代运行时证据 |
| D | `mavlink.io` 滚动网页 | 通用帧、序列化、微服务、XML schema 规则；发现漂移 | 将当前滚动定义无条件套到冻结版本 |
| E | 冻结固件源码中的显式 handler/stream/send/request 路径 | 静态 RX、静态 TX、静态可请求候选 | 运行时一定执行或消息一定到达 |
| F | 带方向、接口、来源身份和时间戳的抓包 | 该次运行中的入站/出站观测 | 其他构建、配置和运行的普遍支持 |

冲突处理规则：保留冻结值与滚动值两份记录，标记 `SPEC_DRIFT`；系统专属解码和命题绑定采用该系统冻结值，不做静默合并。

## 3. 冻结目标与方言入口

| 系统 | SUT 提交 | MAVLink 提交（提交时间） | 实际构建入口 | `common.xml` SHA-256 |
|---|---|---|---|---|
| ArduPilot | `8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e` | `13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472`（2026-07-01T15:20:12+10:00） | `baseline/ardupilot/wscript:778-784` → `modules/mavlink/message_definitions/v1.0/all.xml`，生成 v2.0 头文件 | `aead2b840e503bd30f0d175d0659b07fcecf11644e7abb826590a582aff4c850` |
| PX4 SITL | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`（v1.17.0） | `33af200d25ec6f0925b49b1ba82bbf1294ea5f72`（2025-09-25T16:32:07+10:00） | `default.px4board:37-38` 启用 MAVLink 并选择 `development`；`CMakeLists.txt:40-80` 用 wire protocol 2.0 生成主方言及 uAvionix | `bbc1c382a217209f2cb3922416539da3226878dd19c7549f928913a6f72b1498` |

两套冻结 `pymavlink/generator/C/include_v2.0/mavlink_types.h` 的 SHA-256 均为 `407273090067c0da447a0b94646cae2fe580c1fa4c2accddb13efb7270f06962`；其中第 22–35 行给出 payload 255、v2 core header 9、含 STX 的 header 10、checksum 2、可选块 13 及最大包长公式。

冻结版本的官方 immutable permalinks（均于 2026-07-18 复核）：

- ArduPilot build entry：<https://github.com/ArduPilot/ardupilot/blob/8f2e5db2efd69e4753b0bacb4d87fbe51566ba6e/wscript#L778-L784>
- ArduPilot dialect entry：<https://github.com/ArduPilot/mavlink/blob/13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472/message_definitions/v1.0/all.xml#L3-L30>
- ArduPilot frozen `common.xml`：<https://github.com/ArduPilot/mavlink/blob/13f2f7351a9bdf5292a2c243eb9a2c19ff4b6472/message_definitions/v1.0/common.xml>
- PX4 SITL dialect selection：<https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/boards/px4/sitl/default.px4board#L37-L38>
- PX4 generator entry：<https://github.com/PX4/PX4-Autopilot/blob/d6f12ad1c4f70ad3230afd7d86e971421e02fef4/src/modules/mavlink/CMakeLists.txt#L40-L80>
- PX4 frozen `development.xml`：<https://github.com/mavlink/mavlink/blob/33af200d25ec6f0925b49b1ba82bbf1294ea5f72/message_definitions/v1.0/development.xml#L3-L6>
- PX4 frozen `common.xml`：<https://github.com/mavlink/mavlink/blob/33af200d25ec6f0925b49b1ba82bbf1294ea5f72/message_definitions/v1.0/common.xml>

边界说明：

- ArduPilot 的 `all.xml:3-30` 同时包含 `ardupilotmega.xml`、`common.xml`、`development.xml`、`python_array_test.xml`、`test.xml` 等。该宽集合是**生成宇宙**，不能当作固件支持清单。
- PX4 SITL 的主方言 `development.xml:3-6` 包含 `common.xml`；官方 schema 明确指出 `development.xml` 中定义默认视为 WIP。CMake 还生成 uAvionix 头文件，同样不等于运行时处理。

## 4. 三类 “parameter” 对象必须分离

| 对象类 | 权威定义位置 | 线上的承载 | 持久性/状态含义 | benchmark 绑定要求 |
|---|---|---|---|---|
| MAVLink 消息字段 | `<message><field>` | 由 `msgid` 选择的 payload 成员 | 由该消息和字段描述决定，可为测量、状态、目标、事件或控制输入 | 记录方言、消息、字段、类型、单位、倍率、枚举、有效性、实例字段、时钟域和方向 |
| `MAV_CMD` 参数 | `enum name="MAV_CMD"` 的具体 `<entry><param index="1..7">` | `COMMAND_LONG`、`COMMAND_INT`，也可由 Mission Protocol 消息承载 | 是某条命令的语义槽位；不是通用配置参数。是否产生长期状态由该命令定义和实现决定 | 必须以具体 `MAV_CMD_*` entry 解释 label、units、enum、范围、倍率、reserved/default；不能只引用 `COMMAND_LONG.paramN` |
| 固件配置参数 | 固件参数注册/元数据及运行时参数表；可经 Parameter 微服务交换 | `PARAM_*` 或 `PARAM_EXT_*`，也可能通过本地工具/文件 | 配置状态；默认值、保存、重启要求、范围和可见性由固件版本/机型/构建决定 | 记录系统、固件版本、参数名、原生类型、元数据来源、运行时返回值和所用协议；不得由同名消息字段或命令槽位推定 |

官方依据：XML schema 的 “MAVLink Commands (enum MAV_CMD)” 规定命令最多七个参数并由具体 command entry 定义；“Messages vs Commands” 说明消息结构相对自由，而命令通过固定承载消息编码。PX4 v1.17 文档则将配置定义为 `float`/`int32_t` 的 param 子系统以及元数据/代码两部分。

## 5. MAVLink 1 / 2 帧与 payload 语义

### 5.1 帧结构

| 项 | MAVLink 1 | MAVLink 2 | 解释约束 |
|---|---|---|---|
| STX | `0xFE` | `0xFD` | 仅表示协议帧起始 |
| 含 STX 的 header | 6 bytes | 10 bytes | v2 增加 incompat/compat flags，`msgid` 扩为 24 bit |
| payload | 0–255 bytes | 0–255 bytes | payload 本身没有逐字段标签；双方必须共享兼容的方言定义 |
| checksum | 2 bytes | 2 bytes | 含 `CRC_EXTRA`；不含 STX 与可选 13-byte block |
| 可选 13-byte block | 无 | 有 | 由 v2 incompat flag 指示 |
| 最小/最大总长 | 8 / 263 bytes | 12 / 280 bytes（含可选块且满 payload） | v2 无可选块且满 payload 时为 267 bytes |
| `seq` | `uint8_t` | `uint8_t` | 发送者包序号，只能辅助识别丢包/重排；不是事件时间，模 256 回绕 |
| `sysid`,`compid` | 发送源 | 发送源 | 标识帧来源，不是目标；目标若存在位于具体 payload 字段中 |

逐字节 header 解释：

| 协议 | byte offset | 字段 | 含义 |
|---|---:|---|---|
| v1 | 0 | `magic` | `0xFE` 起始标记 |
| v1 | 1 | `len` | 随后的 payload 字节数 |
| v1 | 2 | `seq` | 发送组件递增的 8-bit 包序号 |
| v1 | 3 | `sysid` | 发送系统 ID |
| v1 | 4 | `compid` | 发送组件 ID |
| v1 | 5 | `msgid` | 8-bit 消息 ID，用于选择 payload 定义 |
| v2 | 0 | `magic` | `0xFD` 起始标记 |
| v2 | 1 | `len` | 线上的 payload 字节数；可能受尾零裁剪影响 |
| v2 | 2 | `incompat_flags` | 接收实现必须理解的格式能力；有未知置位时不能按已知格式处理该帧 |
| v2 | 3 | `compat_flags` | 不理解时仍可处理帧的兼容提示位 |
| v2 | 4 | `seq` | 发送组件递增的 8-bit 包序号 |
| v2 | 5 | `sysid` | 发送系统 ID |
| v2 | 6 | `compid` | 发送组件 ID |
| v2 | 7–9 | `msgid` | little-endian 24-bit 消息 ID，用于选择 payload 定义 |
| v1/v2 | header 后 | `payload` | 由 `msgid` 和冻结方言共同解释的消息内容；不携带逐字段名字/类型 |
| v1/v2 | payload 后 2 bytes | `checksum` | CRC-16/MCRF4XX 加该消息的 `CRC_EXTRA`；不含 STX 和 v2 可选块 |
| v2 | checksum 后 13 bytes（可选） | optional block | 由 incompat flag 表明是否存在；计入 280-byte 最大包长 |

### 5.2 排序、扩展和截断

- 多字节字段按 little-endian 序列化。
- 非扩展字段按原生元素大小稳定排序：8、4、2、1 byte；同大小保持 XML 相对顺序。数组按**元素类型**而非数组总字节数排序。
- `<extensions/>` 后字段仅由 MAVLink 2 发送，保持 XML 声明顺序，不参与 `CRC_EXTRA`。旧发送端没有这些字段时，新接收端会看到零值；因此“零”可能是缺失扩展的解码结果，除非字段定义明确，否则不能直接解释成观测值零。
- MAVLink 2 必须裁掉 payload 尾部连续零字节；第一 payload byte 不裁。短于结构最大长度的 v2 payload 仍可能完全合规，解码器补零不能被误判为线上的显式测量。
- MAVLink 1 不发送 extension fields，且发送定义的全部 payload bytes。

### 5.3 字段元数据的使用规则

| XML 元数据 | 审计规则 |
|---|---|
| `type` / 数组长度 | 固定线类型和元素数。`char[N]` 只有在字段描述明确规定终止方式时才按字符串处理；例如 `param_id` 恰为 16 字符时没有 NUL，接收端需 17-byte 存储才能作为 C 字符串使用 |
| `units` | 表示物理单位或编码单位。线载荷仍是原始 primitive；不得仅凭单位名重复缩放 |
| `multiplier` | 按冻结 XML 恰好应用一次。例如 `multiplier="1E-2"` 或 `360/255`；若缩放已编码进 `degE7`、`cdeg` 等 unit token，则遵循该 token，不再叠加人工倍率 |
| `enum` | 原始整数映射为命名值。未知值保留为 `UNKNOWN(raw)`，不能创造标签 |
| `bitmask="true"` / `display="bitmask"` | 按位解释允许组合；不能当作互斥单值 enum |
| `invalid` | 仅在具体冻结字段声明时使用。支持 scalar、`[value]`、`[value:]` 和逐位置数组语法；浮点 NaN 用 `isnan` 判定。字段没有 `invalid` 不等于“永远有效”，也不能人工指定 sentinel |
| `instance="true"` | 需要把实例字段纳入观测键，避免把多个传感器/电池/端口混成一条轨迹 |
| `wip` / `superseded` / `deprecated` | 单独保存生命周期状态；存在定义不代表稳定、已采用或已移除 |

## 6. Parameter Protocol 与 Extended Parameter Protocol

| 维度 | Parameter Protocol (`PARAM_*`) | Extended Parameter Protocol (`PARAM_EXT_*`) |
|---|---|---|
| 值容器 | `param_value: float`，IEEE754 single，4 bytes | `param_value: char[128]` |
| 类型标签 | `MAV_PARAM_TYPE` | `MAV_PARAM_EXT_TYPE` |
| 编码 | byte-wise 或 C-cast，由 capability/先验确定 | byte-wise typed value；可包含 8/16/32/64-bit integer、REAL32/64、CUSTOM |
| 整数精度 | C-cast 的 float 对整数只有 24 bits 精确度；byte-wise 对 32-bit carrier 内值可保留位模式 | 容器足以承载列出的固定宽度类型 |
| 宽类型边界 | 滚动文档和 enum 列出 64-bit 类型，但载体只有 4 bytes，且官方同时说明并非所有类型均受实现支持；不得据此宣称宽于 carrier 的值可无损交换 | `char[128]` 与类型标签共同解码 |
| 写入回应 | 当前值通过 `PARAM_VALUE` 广播；协议超时数值不是 XML 固定常量 | `PARAM_EXT_ACK` 显式区分 accepted、failed、in-progress、unsupported |
| 参数名 | `char[16]`，不足 16 字符 NUL 终止，正好 16 字符无 NUL | 相同 |
| 缓存 | 可缓存，但官方明确缓存同步不保证；可能漏掉其他组件的更新 | 继承类似限制 |

实现边界：

- ArduPilot 官方页面说明机型和版本的参数集合不同，应从运行中的飞控读取；隐藏子系统参数会使 `param_count` 和 `param_index` 改变。索引不是稳定身份，优先使用 `param_id`。
- PX4 v1.17 官方页面把原生参数表限定为 `float` 与 `int32_t`，元数据与代码共同定义；不能由 MAVLink 的宽类型 enum 反推 PX4 原生参数类型。
- `PARAM_EXT_*` 出现在冻结 `common.xml` 只证明定义存在。MAVLink 官方页说明该扩展最初用于 Camera Protocol；PX4 v1.17 仅声明以某种形式用于相机定义字符串。这里没有证据证明两个飞控通过 PARAM_EXT 暴露其飞控配置表。

## 7. 支持与可观测性状态机

最终表格必须采用下列非等价状态；一个较低层事实不能自动提升到更高层：

| 状态 | 最低证据要求 | 精确含义 |
|---|---|---|
| `DIALECT_DEFINED` | 消息/命令进入冻结构建入口的 XML include closure | 生成器知道定义 |
| `GENERATED` | 对应生成头/元数据存在 | 构建生成了编码/解码 API |
| `STATIC_RX_HANDLER` | 冻结固件中显式 dispatch + decode/handler，且构建条件满足 | 该方向存在静态入站处理路径 |
| `STATIC_TX_STREAM` | 冻结固件中显式 stream/pack/send 路径，且构建条件满足 | 该方向存在静态出站候选路径 |
| `REQUESTABLE` | 除通用请求机制外，还存在该具体消息的 stream registration/request handler，或受控试验得到明确响应 | 可请求发送候选；不等于默认发送或已观测 |
| `CONFIGURED_DEFAULT_STREAM` | 已解析当前构建/机型/端口/profile/参数下的默认流配置 | 该配置意图默认发送；仍不等于捕获到 |
| `RUNTIME_OBSERVED_INBOUND` | 抓包含方向、接口/channel、host timestamp、`sysid/compid`、消息和字段 | 本次运行确实进入观察点 |
| `RUNTIME_OBSERVED_OUTBOUND` | 同上，方向为飞控侧出站，且处理转发来源 | 本次运行确实离开观察点 |
| `PROPERTY_DIRECT_OBSERVABLE` | 运行时观测 + 字段语义/有效性/实例/时钟域满足该命题 | 可直接作为该 MITL 原子命题的观测证据 |

系统官方边界：

- PX4 v1.17 文档要求消息有 `MavlinkStream` 派生类且进入 stream list 后才可流式发送/按请求发送；接收则需显式 handler、decode 及 dispatch case。因此“XML 中有”不等于 RX 或 TX。
- ArduPilot 官方页面提供 SRx、`REQUEST_DATA_STREAM`、`MAV_CMD_SET_MESSAGE_INTERVAL`、`MAV_CMD_REQUEST_MESSAGE` 等机制，但也给出不发送的消息条目会被忽略的例子。通用请求命令可用不证明任意 `msgid` 可请求。
- ArduPilot routing 与 PX4 forwarding 都可能让观察点看见由其他组件生成的帧。必须用源 `sysid/compid`、方向和 channel 区分“飞控生成”与“飞控转发”。
- 运行时请求应记录请求命令、目标、期望间隔、ACK/response、实际首帧和后续速率；`REQUESTABLE` 与 `RUNTIME_OBSERVED_*` 仍分别保存。

## 8. 时间语义审计

### 8.1 字段与时钟域

| 字段/来源 | 冻结定义支持的含义 | 不允许的推断 | MITL 使用规则 |
|---|---|---|---|
| `time_boot_ms: uint32_t` | 自系统启动以来的毫秒；需绑定发送源/会话 | 不能当 Unix 时间；不能跨重启直接比较 | 同一 `sysid/compid`、同一启动会话内使用；处理回绕；重启或未知回绕时切分 trace |
| `SYSTEM_TIME.time_unix_usec` | 发送者 master clock 的 Unix epoch microseconds | XML 未声明 0 为 invalid，不能自行把 0 定为无效；也不能假设其精度 | 与同一消息中的 `time_boot_ms` 可形成一次映射样本，但精确同步应使用 TIMESYNC，映射误差需实测 |
| `SYSTEM_TIME.time_boot_ms` | 与该 `SYSTEM_TIME` 发送者同源的 boot milliseconds | 不是接收主机 boot time | 只有保留源身份和同一消息配对时，才用于 boot↔Unix 关联 |
| `time_usec` | **逐消息定义**。有的为 Unix-or-boot（以 magnitude 推断），有的明确 boot，有的明确同步 Unix-or-boot | 不能按字段名统一设为某个时钟域；XML 没给 magnitude threshold 时不能人工补阈值 | 每个 `message.field` 单独登记 `clock_domain`；模糊定义标 `AMBIGUOUS_SPEC` |
| `GPS_INPUT.time_week_ms` | GPS week 起点以来的 milliseconds；与 `time_week` 组合 | 不能单独当单调全局时间；不能在无 time-scale/leap-second policy 时直接转 Unix | 同时采集 `time_week`；周边界作为正常分段；转换策略需外部、版本化证据 |
| `GPS_INPUT.time_week` | GPS week number (`uint16_t`) | 冻结 XML 未声明接收端 rollover 规则，不能人工套入其他位宽 rollover | 保留原始值和来源；只按明确转换策略合成 |
| `TIMESYNC.ts1/tc1` | nanoseconds；请求 `tc1=0`，响应 mirror `ts1` 并在 `tc1` 放 responder time；多次估计/过滤 offset | 一次往返不证明时钟已同步；不能把这些值当其他消息的事件时间 | 保存 request/response 配对、RTT、offset 样本、过滤策略及不确定度 |
| 主机 arrival timestamp | 帧抵达抓包/解析观察点的本地主机时钟 | 不是发送/生成时间；不能忽略传输、调度、路由、队列与解析延迟 | 只用于该观察点的排序/超时时，声明 clock API、capture point、方向和误差预算 |
| MAVLink frame `seq` | 发送组件的 8-bit packet sequence | 不是时间，也不是消息级全局序号 | 只作丢包/重排线索；按发送源和链路状态解释回绕 |

冻结 XML 的反例直接证明 `time_usec` 不能全局解释：

- ArduPilot `common.xml:5320-5323` 的 `SERVO_OUTPUT_RAW.time_usec` 是 **`uint32_t`**，描述却允许 Unix epoch 或 boot 并要求按 magnitude 区分；该类型每 `2^32 us = 4,294.967296 s = 71 min 34.967296 s` 回绕，不能可靠容纳当代 Unix microseconds。此字段必须标记 `AMBIGUOUS_SPEC`，不能自动转 epoch。
- ArduPilot `common.xml:7389-7393` 的 `ACTUATOR_OUTPUT_STATUS.time_usec` 明确是 boot time。
- `WHEEL_DISTANCE`、`WINCH_STATUS` 的 `time_usec` 描述为 synchronized Unix time 或 boot time。

### 8.2 可复核的回绕计算

`time_boot_ms` 的回绕值来自冻结 XML 的 `uint32_t` 类型与 `ms` 单位，不是经验常量：

```text
modulus = 2^32 ms
        = 4,294,967,296 ms
        = 49 days 17:02:47.296
        ≈ 49.7102696 days
```

若采用常见的 modular signed-difference 比较，为避免前后方向歧义，需要额外保证真实间隔小于半模：

```text
half_range = 2^31 ms
           = 24 days 20:31:23.648
           ≈ 24.8551348 days
```

该半模规则是本审计从有限宽度计数器推导出的监测算法前提，不是 MAVLink XML 的原文规则；实现时必须显式记录此前提。计数下降可能是回绕、重启或乱序，不能只凭下降作唯一判断。

`GPS_INPUT.time_week_ms` 的一周长度由时间单位算得：`7×24×60×60×1000 = 604,800,000 ms`。冻结 XML只写“from start of GPS week”，未给 Unix 转换或 leap-second 规则，因此该算式只能用于周内语义和边界检查。

### 8.3 TIMESYNC 与时间容差

官方 TIMESYNC 流程允许估计 RTT 和两时钟 offset；官方同时明确链路拥塞和处理时间会使入/出站延迟随时间变化，因此需多次采样并过滤。由此得到：

- offset 必须带估计时段、样本数量、RTT 分布、过滤方法和残余误差；不能只保存一个裸 offset。
- ArduPilot 文档中的 MAVROS `10 ms` RTT 丢弃阈值是该工具配置/实现行为，不是 MAVLink 协议容差，也不能成为 benchmark 的通用 `epsilon`。
- 本 benchmark 目前没有抓包、RTT 分布或端到端校准，故不存在可证明的数值 `epsilon`。涉及跨时钟或 arrival time 的时间约束应标 `INCONCLUSIVE`，直到获得测量证据。

### 8.4 发送调度、队列与到达时间

官方实现文档给出了不能忽略的延迟来源：

- ArduPilot 在传输参数和航点期间，消息流速率可能暂时比请求值慢四倍或更多。
- PX4 `MAV_X_RATE` 是所有 streams 的合计上限；超限时会降低各消息速率。
- 同一链路可能存在 stream 请求冲突、串口/UDP 队列、固件调度、routing/forwarding、主机 socket 和 parser 队列。

这些资料只证明延迟会变化，没有给出适用于本 benchmark 的普遍上界。最终属性监测器必须：

1. 优先使用同一发送时钟域的嵌入时间；
2. 若只能用 arrival time，记录主机时钟（持续时间优先 monotonic clock）、capture point、方向和每次运行实测延迟预算；
3. 缺少误差预算时不给出 PASS/FAIL，只给 `INCONCLUSIVE`；
4. 不以期望 stream period 代替事件时间，也不把缺帧直接解释为状态未发生。

## 9. 官方网页来源登记（检索日均为 2026-07-18）

| ID | 精确 URL | DOM/section | 本审计采用的结论 |
|---|---|---|---|
| WEB-MAV-01 | https://mavlink.io/en/guide/serialization.html | `Packet Format`；`MAVLink 2 Packet Format`；`MAVLink 1 Packet Format`；`Payload Format`；`Field Reordering`；`Empty-Byte Payload Truncation (MAVLink 2)`；`CRC_EXTRA Calculation` | 帧长、字段、little-endian、稳定排序、扩展例外、v2 尾零裁剪、payload 无逐字段标签 |
| WEB-MAV-02 | https://mavlink.io/en/guide/xml_schema.html | `MAVLink Commands (enum MAV_CMD)`；`<param> element`；`Message Definition (messages)`；`<field> element`；`Lifecycle Elements` | 命令参数元数据、field 属性、数组 invalid 语法、生命周期 |
| WEB-MAV-03 | https://mavlink.io/en/guide/define_xml_element.html | `Messages vs Commands`；`Message Extensions (MAVLink 2)`；`Enums`；`Commands` | 消息/命令边界；extension 的 v1/v2、补零、排序和 CRC 规则；bitmask；具体命令 param 语义 |
| WEB-MAV-04 | https://mavlink.io/en/services/command.html | `Message/Enum Summary`；`Use COMMAND_INT or COMMAND_LONG?`；`Sequences`；`Long Running Commands` | COMMAND_INT/LONG 槽位和 frame 差异；封装支持由 flight stack 决定；ACK 接受不等于完成 |
| WEB-MAV-05 | https://mavlink.io/en/services/parameter.html | `Message/Enum Summary`；`Protocol Discovery`；`Parameter Names`；`Parameter Encoding`；`Parameter Types`；`Parameter Metadata`；`Parameter Caching` | 4-byte float carrier、byte-wise/C-cast、24-bit integer precision、16-char ID、类型/缓存限制 |
| WEB-MAV-06 | https://mavlink.io/en/services/parameter_ext.html | `Extended Parameter Protocol`；`Message/Enum Summary`；`Parameter Encoding`；`Parameter Caching` | `char[128]`、扩展类型、PARAM_EXT_ACK 与原协议差异、相机来源与支持边界 |
| WEB-MAV-07 | https://mavlink.io/en/services/timesync.html | `Time Synchronization Protocol v2`；`Sequences` | TIMESYNC request/response、RTT/offset、重复过滤、链路/处理延迟变化 |
| WEB-MAV-08 | https://mavlink.io/en/messages/common.html#SYSTEM_TIME | `SYSTEM_TIME (2)` | 当前滚动 SYSTEM_TIME 的字段与 sender master-clock 描述；仅作滚动参考 |
| WEB-MAV-09 | https://mavlink.io/en/messages/common.html#TIMESYNC | `TIMESYNC (111)` | 当前滚动 TIMESYNC 定义；仅作滚动参考 |
| WEB-MAV-10 | https://mavlink.io/en/messages/common.html#GPS_INPUT | `GPS_INPUT (232)` | 当前滚动 GPS 周字段定义；仅作滚动参考 |
| WEB-MAV-11 | https://mavlink.io/en/messages/common.html#COMMAND_INT | `COMMAND_INT (75)` | 当前滚动命令承载定义；不覆盖冻结 `invalid` |
| WEB-MAV-12 | https://mavlink.io/en/messages/common.html#COMMAND_LONG | `COMMAND_LONG (76)` | 当前滚动命令承载定义；不覆盖冻结 `invalid` |
| WEB-AP-01 | https://ardupilot.org/dev/docs/mavlink-requesting-data.html | `Requesting Data From The Autopilot`；`Using SRx Parameters`；`Using SET_MESSAGE_INTERVAL`；`Using REQUEST_MESSAGE`；`Specifying Message Rates in a File` | 多种流请求方式、参数/航点期间速率下降、某些不发送消息请求被忽略；请求机制不等于任意消息可请求 |
| WEB-AP-02 | https://ardupilot.org/dev/docs/mavlink-get-set-params.html | `Retrieving All Parameters`；`Retrieving a Parameter`；`Setting a Parameter`；`Hidden Parameters` | 机型/版本参数集合变化、PARAM 流程、隐藏参数改变 count/index |
| WEB-AP-03 | https://ardupilot.org/dev/docs/ros-timesync.html | `Clock/Time Synchronisation`；`Mavros Configuration`；`ArduPilot Configuration` | SYSTEM_TIME/TIMESYNC 可用于同步；时间源可配置；MAVROS 10 ms 仅实现阈值 |
| WEB-AP-04 | https://ardupilot.org/dev/docs/mavlink-routing-in-ardupilot.html | `MAVLink Routing in ArduPilot`；`Detailed theory of MAVLink routing` | 端口间转发、source/target 和 channel 路由；观察到的帧未必由飞控生成 |
| WEB-PX4-01 | https://docs.px4.io/v1.17/en/mavlink/streaming_messages.html | `Overview`；`Streaming on Request` | stream class + stream list 是 TX/request 路径；SET_MESSAGE_INTERVAL/REQUEST_MESSAGE 请求入口 |
| WEB-PX4-02 | https://docs.px4.io/v1.17/en/mavlink/receiving_messages.html | `Overview`；`Steps` | RX 需要 handler、decode、publish 和 dispatch；XML 定义不是 RX 支持 |
| WEB-PX4-03 | https://docs.px4.io/v1.17/en/mavlink/protocols.html | `Supported Microservices` | v1.17 “in some form” 的微服务列表；不能扩张为每个消息或每种角色均支持 |
| WEB-PX4-04 | https://docs.px4.io/v1.17/en/advanced/parameters_and_configurations.html | `Parameters & Configurations`；`Creating/Defining Parameters` | PX4 param 表类型、元数据与代码、固件内元数据；配置参数与 MAV_CMD 分离 |
| WEB-PX4-05 | https://docs.px4.io/v1.17/en/peripherals/mavlink_peripherals.html | `MAVLink Instances` | profile、默认流、可请求覆盖、合计 rate cap、forwarding，解释队列/速率不确定性 |

PX4 上述版本页在冻结仓库中还有配对 Markdown，可作为发布站点变动后的可复核副本：

- `baseline/px4/docs/en/mavlink/streaming_messages.md:7-12,190-211,250-256`
- `baseline/px4/docs/en/mavlink/receiving_messages.md:1-9,41-84`
- `baseline/px4/docs/en/mavlink/protocols.md:1-12,36-42`
- `baseline/px4/docs/en/advanced/parameters_and_configurations.md:1-6,85-105`

## 10. 冻结证据登记

| ID | 文件与行 | 结论 |
|---|---|---|
| FRZ-AP-BUILD-01 | `baseline/ardupilot/wscript:778-784` | ArduPilot MAVLink 生成入口是 `all.xml`，输出 v2.0 |
| FRZ-AP-DIALECT-01 | `baseline/ardupilot/modules/mavlink/message_definitions/v1.0/all.xml:3-30` | include closure 很宽，含 development/test；不能等同实现支持 |
| FRZ-PX4-BUILD-01 | `baseline/px4/boards/px4/sitl/default.px4board:37-38`；`baseline/px4/src/modules/mavlink/CMakeLists.txt:40-80` | SITL 选择 development，生成 wire protocol 2.0 主方言和 uAvionix |
| FRZ-PX4-DIALECT-01 | `baseline/px4/src/modules/mavlink/mavlink/message_definitions/v1.0/development.xml:3-6` | development include common；其定义属于 WIP 管理域 |
| FRZ-FRAME-01 | 两套 `pymavlink/generator/C/include_v2.0/mavlink_types.h:22-35` | payload/header/checksum/13-byte block/max packet 常量一致 |
| FRZ-AP-TIME-01 | ArduPilot `common.xml:5109-5117,6044-6057,6545-6551,7389-7402,7465-7474` | SYSTEM_TIME、TIMESYNC、GPS week、明确 boot 与同步/boot 时间字段 |
| FRZ-PX4-TIME-01 | PX4 `common.xml:5273-5280,6254-6270,6757-6763` | PX4 冻结 SYSTEM_TIME、带 extension target 的 TIMESYNC、GPS week 字段 |
| FRZ-AP-PARAM-01 | ArduPilot `common.xml:5151-5180,7190-7223,2718-2809` | PARAM/PARAM_EXT 消息、4/128-byte carrier 与类型 enum |
| FRZ-PX4-PARAM-01 | PX4 `common.xml:5331-5360,7454-7487` | PX4 冻结 PARAM/PARAM_EXT 线定义 |
| FRZ-AP-CMD-01 | ArduPilot `common.xml:5671-5700` | 冻结 COMMAND_INT/LONG 无字段级 `invalid` 属性 |
| FRZ-PX4-CMD-01 | PX4 `common.xml:5871-5900` | 冻结 COMMAND_INT/LONG 对 float 指定 NaN、对 x/y 指定 INT32_MAX invalid |
| FRZ-META-01 | ArduPilot `common.xml:5104-5107,5189-5208,5279-5280,5519,6305,6430` | extension、multiplier、数组、bitmask、scalar/array invalid 的真实例子 |

## 11. 已确认的规范漂移/不一致

| 项 | ArduPilot 冻结 MAVLink | PX4 冻结 MAVLink | 审计处置 |
|---|---|---|---|
| `COMMAND_INT` / `COMMAND_LONG` invalid | `param*`、`x/y/z` 无字段级 `invalid` | float params 为 `NaN`，x/y 为 `INT32_MAX` | 两系统分别解码；不得把 PX4 sentinel 规则复制到 ArduPilot |
| `TIMESYNC` target extensions | `common.xml:6044-6057` 无 `target_system/target_component` extension | `common.xml:6268-6270` 有这两个 extension | 保留每套布局；滚动 TIMESYNC 页不能覆盖冻结字段集合 |
| `SYSTEM_TIME` 描述 | “sender's master clock” | 较旧文本为 “master clock”，且含 `SYSTEM_TYPE` 文字 | 字段类型/单位相同；来源身份仍由 frame `sysid/compid` 确定，不从文字差异推实现行为 |
| PING 生命周期 | `superseded` | `deprecated` | 保存冻结生命周期，不据此推断两固件是否处理 PING |
| `SERVO_OUTPUT_RAW.time_usec` | `uint32_t` + Unix-or-boot 描述 | 同类历史定义 | 标 `AMBIGUOUS_SPEC`，不用 magnitude 自动判域 |

## 12. 对最终可观测性文档的强制规则

每个消息/字段条目至少包含：

1. `system`、SUT commit、MAVLink commit、dialect entrypoint、XML path/hash；
2. `message_id/name`、field、type/array、extension、units、multiplier、enum/bitmask、invalid、instance、lifecycle；
3. `direction_evidence`：RX、TX、requestable、default stream 分栏，附冻结源码或版本文档位置；
4. `runtime_evidence`：capture id、方向、接口/channel、host clock、`sysid/compid`、请求上下文；没有抓包写 `NOT_RUN_NO_CAPTURE`；
5. `producer_identity`：飞控本体、其他组件或未知；forwarded frame 不冒充飞控生成；
6. `clock_domain`、单位、宽度、回绕、同步方法、映射误差；`time_usec` 按 `message.field` 逐项定义；
7. `property_observability`：`DIRECT`、`DERIVED_WITH_ASSUMPTIONS`、`NOT_DIRECT` 或 `INCONCLUSIVE`，列出全部假设；
8. 当前页与冻结 XML 不同时，保存 `SPEC_DRIFT`，并指出最终采用冻结值。

## 13. 本次未做出的结论与遗留问题

- 未运行 ArduPilot/PX4，未抓取任何 MAVLink 帧；所有 runtime 状态均为 `NOT_RUN_NO_CAPTURE`。
- 未逐消息完成 ArduPilot/PX4 静态 RX/TX/requestable 扫描；本报告只规定证据标准。
- 未证明 ArduPilot 或 PX4 的飞控配置表可由 `PARAM_EXT_*` 读取。
- 未建立 Unix、GPS 与 boot clock 的实测映射，也没有 leap-second/time-scale policy。
- 未获得链路、调度、queue、routing 和主机 capture 的延迟分布，因此没有数值 `epsilon`。
- 未解决 `SERVO_OUTPUT_RAW.time_usec` 的冻结定义歧义；使用该字段的时间属性保持 `INCONCLUSIVE`，除非有实现版本证据与运行时校准。
- ArduPilot Dev 文档是滚动页面；若需发布级复现，应再固定页面内容哈希或与该 SUT 提交配对的文档提交。
