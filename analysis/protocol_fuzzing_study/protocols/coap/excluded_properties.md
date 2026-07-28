# CoAP 排除与待修候选

## 研究阶段排除：_staging/ietf_app_protocols/coap/excluded.md

# CoAP excluded candidates

筛查范围为 RFC 7252 的消息层、请求/响应层及其默认传输参数。下列候选至少缺少一个主目录收录条件；原因码沿用 `MULTI_PROTOCOL_EXTRACTION_SCHEMA.md`。

| 候选 | 规范定位 | 原因码 | 排除依据 |
|---|---|---|---|
| 收到 CON 后发送 ACK 或 RST | RFC 7252 §4.2 | `NO_NUMERIC_BOUND` | 规范规定接收方动作，但没有给出从 CON 到 ACK/RST 的数值截止时间；`PROCESSING_DELAY` 也不是该动作的硬性期限。 |
| Empty CON “CoAP ping” 的 RST 响应 | RFC 7252 §1.2、§4.2--4.3 | `NO_NUMERIC_BOUND` | RST 义务可定位，但 RFC 7252 未规定响应 ping 的数值时间窗。 |
| 以 2 s `PROCESSING_DELAY` 作为 ACK 截止时间 | RFC 7252 §4.8.2 | `TRACE_NOT_DECISIVE` | 2 s 是派生计算使用的保守假设；原文没有把它规定为逐报文 MUST/SHOULD 截止时间。 |
| `MAX_TRANSMIT_WAIT=93 s` 的整体失败期限 | RFC 7252 §4.8.2 | `DUPLICATE_OBLIGATION` | 它是默认重传计数、随机初值和翻倍规则的整体派生上界；终止动作已经由 `COAP-TX-03` 的最后等待/失败 oracle 覆盖。 |
| 后续第三、第四重传周期分别实例化为 8--12 s、16--24 s | RFC 7252 §4.2 | `DUPLICATE_OBLIGATION` | 只是 `COAP-TX-02` 同一翻倍义务的机械周期展开，不产生新的规范动作。 |
| Confirmable 交换信息在 247 s 后清除 | RFC 7252 §4.8.2 | `NO_FIXED_SOURCE_MAP` | RFC 定义可清除信息的时间；锁定的 libcoap 路径中未找到以 `COAP_EXCHANGE_LIFETIME` 驱动该清除动作的固定运行时符号。 |
| Confirmable 重复报文在 247 s 内只处理一次并重复 ACK | RFC 7252 §4.5 | `NO_FIXED_SOURCE_MAP` | 规范允许针对幂等语义放宽；锁定源码仅保存最近 MID 的相关路径，不提供可证明覆盖完整 247 s 的通用去重状态映射。 |
| Non-confirmable 重复报文的 `NON_LIFETIME=145 s` 处理 | RFC 7252 §4.5、§4.8.2 | `NO_FIXED_SOURCE_MAP` | 去重规则可以按消息语义放宽，且锁定源码没有通用 145 s NON 去重生命周期的固定观测路径。 |
| 可选重复发送 NON 消息 | RFC 7252 §4.3 | `NO_NUMERIC_BOUND` | 发送方 MAY 发送多个副本，但规范没有要求必须发生或规定各副本之间的固定时间窗。 |
| `PROBING_RATE=1 byte/s` | RFC 7252 §4.7--4.8 | `FORMULA_UNSUPPORTED` | 这是对未响应端点的平均数据率约束；RFC 未给出固定平均窗口，不能直接化为当前有限 pointwise MITL 的单一真实区间。 |
| `NSTART=1` 并发限制 | RFC 7252 §4.7--4.8 | `FORMULA_UNSUPPORTED` | 它是同时在途交互数量约束，不是计时、截止或定时状态迁移。 |
| 应用计算的 multicast Leisure | RFC 7252 §8.2 | `NO_NUMERIC_BOUND` | 一般 Leisure 依赖群组大小、响应大小和目标速率；仅缺少这些数据时采用 5 s 默认值的固定路径进入 `COAP-MCAST-01`。 |
| `Max-Age` 默认 60 s 的通用响应缓存淘汰 | RFC 7252 §5.6.1 | `NO_FIXED_SOURCE_MAP` | 数值可定位，但锁定 libcoap 核心中未找到可作为通用透明响应缓存淘汰 oracle 的固定实现路径。 |
| libcoap `ping_timeout` 对下一重传间隔的截断 | libcoap `src/coap_net.c:1921-1929` | `VERSION_MISMATCH` | 这是实现配置扩展，不是 RFC 7252 的独立规范定时义务；默认未启用，也不能替代 RFC 的传输参数性质。 |

没有把同一参数的其他配置值、角色改名或边界常数复制成新性质。所有主目录候选均保留明确的默认/profile 前提；不满足这些前提的运行不由对应公式判定。

