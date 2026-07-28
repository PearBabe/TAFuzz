# MQTT 排除与待修候选

## 研究阶段排除：_staging/ietf_app_protocols/mqtt/excluded.md

# MQTT excluded candidates

筛查范围为 OASIS MQTT 5.0 的连接、Keep Alive、QoS 交付、会话及消息生命周期。下列候选至少缺少一个主目录收录条件；原因码沿用 `MULTI_PROTOCOL_EXTRACTION_SCHEMA.md`。

| 候选 | 规范定位 | 原因码 | 排除依据 |
|---|---|---|---|
| Server 收到 PINGREQ 后发送 PINGRESP | MQTT 5.0 §3.12.4 | `NO_NUMERIC_BOUND` | 规范规定 MUST 发送 PINGRESP，但没有给出从 PINGREQ 到 PINGRESP 的数值截止时间。 |
| Client 未在“合理时间”收到 PINGRESP 后关闭连接 | MQTT 5.0 §3.1.2.10 | `NO_NUMERIC_BOUND` | “reasonable amount of time” 没有标准默认数值，不能无依据固定为某个毫秒区间。 |
| CONNECT 后等待 CONNACK 的超时 | MQTT 5.0 §3.1.4、§3.2 | `NO_NUMERIC_BOUND` | 协议描述包序和错误处理，但没有规定客户端等待 CONNACK 的统一数值期限。 |
| QoS 1/2 等待 PUBACK、PUBREC、PUBREL 或 PUBCOMP 的超时 | MQTT 5.0 §4.3--4.4 | `NO_NUMERIC_BOUND` | 交付流程规定必需报文和状态迁移；MQTT 5.0 不提供在活动连接上的确认重传定时器数值。 |
| 重连且 Session Present 时重发未确认 PUBLISH/PUBREL | MQTT 5.0 §4.4 | `NO_NUMERIC_BOUND` | 规范要求重连后的重发动作，但没有规定重新建立连接或重发动作的数值截止时间。 |
| 活动连接中除规范例外外不得重传 PUBLISH | MQTT 5.0 §4.4 | `NO_FIXED_SOURCE_MAP` | 该全局规则跨消息队列、断线恢复和 session generation；锁定源码中没有单一固定符号可在不混淆新发布/重连恢复的情况下提供完整 oracle。负确认后的明确终止动作单列为 `MQTT-RTX-01`。 |
| Server Keep Alive 属性覆盖 CONNECT 值 | MQTT 5.0 §3.2.2.3.14 | `DUPLICATE_OBLIGATION` | 这是有效参数的选择规则，不是新的定时动作；`MQTT-KA-01`/`MQTT-KA-02` 已要求 adapter 先解析覆盖并选择固定 profile。 |
| Keep Alive=0 | MQTT 5.0 §3.1.2.10 | `FORMULA_UNSUPPORTED` | 值为 0 明确关闭 Keep Alive 机制，因此不存在周期发送或关闭截止义务。 |
| Session Expiry Interval | MQTT 5.0 §3.1.2.11.2、§3.14.2.2.2 | `NO_NUMERIC_BOUND`, `PUNCTUAL_ONLY` | 非零值由报文配置且没有协议默认常数；属性缺省时默认 0，直接实例化会形成不允许的 punctual 边界。 |
| Will Delay Interval | MQTT 5.0 §3.1.3.2.2 | `NO_NUMERIC_BOUND`, `PUNCTUAL_ONLY` | 非零延迟由客户端提供；缺省值为 0，标准没有适合主目录的固定非零默认 profile。 |
| Message Expiry Interval | MQTT 5.0 §3.3.2.3.3 | `NO_NUMERIC_BOUND` | 属性值逐消息配置；属性缺省表示消息不因该机制过期，没有统一有限截止时间。 |
| Retained Message 到期删除 | MQTT 5.0 §3.3.1、§3.3.2.3.3 | `NO_NUMERIC_BOUND` | 删除时间取决于逐消息 Message Expiry，没有标准默认的非零有限值。 |
| Mosquitto `WITH_OLD_KEEPALIVE` 五秒扫描周期 | Mosquitto `src/keepalive.c:146-175` | `VERSION_MISMATCH` | 五秒是可选实现扫描粒度，不是 MQTT 5.0 的连接关闭期限，也不是默认时间轮路径的独立规范性质。 |
| Mosquitto 自动重连退避 | Mosquitto client library | `VERSION_MISMATCH` | 重连间隔是库策略；MQTT 5.0 未把该实现退避规定为协议定时义务。 |

没有为任意 CONNECT 属性值机械复制 Keep Alive 公式。收录的 60000/90000 ms 只适用于显式固定且未被 Server Keep Alive 改写的有效 60 s profile。

