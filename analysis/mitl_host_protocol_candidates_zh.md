# 可从规范提取 MITL 性质并直接在主机实验的协议候选

调研日期：2026-07-16

## 1. 选择标准

这里的“适合”同时要求：

1. 规范中存在带 `MUST/SHALL/SHOULD` 的定量时间约束，或由报文字段、协商参数和
   计数器确定的时间上界/下界；
2. 约束能在有限观测迹上转成 MITL，必要时允许先计算参数、计数器或 timer-expired
   原子命题；
3. 有开源客户端、服务器或多节点实现，可在 Linux 主机、容器或 network namespace
   中运行真实协议栈；
4. 能从 pcap、日志、API 状态或进程事件提取可重复的原子命题；
5. 不依赖 ECU、总线控制器、PLC、交换机、专用 NIC 或硬件时间戳才能得到有意义结果。

容器、`veth`、network namespace 和 `tc netem` 仍属于主机上的真实实现实验：协议状态
机和 timer 在真实进程/内核中执行，只是网络拓扑与故障由主机控制。这与在模型检查器或
协议模拟器中只执行抽象状态机不同。

## 2. 总体推荐

### 2.1 第一梯队：最适合作为“规范文本 → MITL → 主机实验”研究对象

| 协议 | 规范中的时间结构 | 主机实现建议 | 研究价值 | 主要难点 |
|---|---|---|---|---|
| SIP | Timer A–K、T1/T2/T4、指数重传、事务总超时、INVITE/non-INVITE 分支 | PJSIP + Kamailio/OpenSIPS，UDP loopback/netns | 时间规则密集、状态机明确、负响应/重复/丢包组合丰富 | proxy、UA、transaction/dialog 层次需分清 |
| DHCPv6 | IRT/MRT/MRC/MRD、随机化指数退避、租约 T1/T2、Renew/Rebind | Kea + Linux/其他 DHCPv6 client，两个 netns | 动态参数、重传、租约生命周期兼具 | 公式需按 exchange 类型和协商租约实例化 |
| BFD | 协商 TX/RX interval、75%–100% jitter、DetectMult×interval、Poll/Final | 两个 FRR/BIRD 实例 | MITL 时间窗口非常清晰，失效 oracle 明确 | 很短 interval 会受主机调度抖动影响 |
| VRRPv3 | Advertisement Interval、Skew Time、Active Down Interval、priority-zero 快速切换 | keepalived 或 FRR，两个 netns | 周期+超时+角色迁移，oracle 简洁 | 需要 multicast/raw socket 和 namespace 配置 |
| SOME/IP-SD | Initial Wait 随机窗口、指数 repetition、cyclic offer、TTL、request-response delay | COVESA vsomeip + someipy | 汽车以太网相关，时间状态机非常丰富，无需 ECU | AUTOSAR 参数多，版本和配置映射必须固定 |
| MQTT 5.0 | Keep Alive、1.5× server timeout、Session/Message/Will Delay Expiry | Mosquitto + Paho MQTT | 实现成熟、实验最容易、动态时间字段多 | QoS 重传时间部分留给实现，不能过度形式化 |
| OPC UA Subscription | publishing interval、sampling interval、keep-alive count、lifetime count、session timeout | open62541 + asyncua/第二个 open62541 实例 | 周期采样、无数据 keepalive、subscription 删除均可观测 | 规范允许 server 修订参数，必须使用 revised value |
| DDS / DDSI-RTPS | Deadline、Liveliness lease、Latency Budget、heartbeat/nack response/suppression timers | Fast DDS + Cyclone DDS | ROS 2/汽车中间件相关，多实现互操作，可做 QoS+wire timing | DDS QoS 层与 RTPS wire 层规则多且复杂 |
| mDNS/DNS-SD | 20–120 ms 随机响应、400–500 ms truncated-query 延迟、probe/announce/defend、TTL | Avahi + python-zeroconf/第二实现 | 小而时间密集，适合检验随机窗口和抑制规则 | multicast 去重、缓存和同机多 responder 隔离 |
| TFTP + timeout option | stop-and-wait、ACK/重传、1–255 s 协商 timeout、block 序号 | tftp-hpa + atftp/自制对端 | 最小可行 benchmark，状态和 oracle 极清楚 | 规则较少，单独做论文规模不足 |

### 2.2 第二梯队：价值高，但公式或实验工程更复杂

| 协议 | 可提取性质 | 主机实验 | 降为第二梯队的原因 |
|---|---|---|---|
| AMQP 1.0 | `idle-time-out`、heartbeat/activity、link/connection close | Apache Qpid Proton、RabbitMQ AMQP 1.0 | 时间规则比 MQTT 少，部分动作是 SHOULD |
| DTLS 1.3/1.2 | handshake flight 重传、timer doubling、ACK、Finished 后保持响应窗口 | wolfSSL/mbedTLS/OpenSSL 的相应版本 | 不同库对 DTLS 版本和 timer test hook 支持不一致 |
| QUIC | PTO、loss timer、ACK delay、idle timeout、closing/draining ≥3 PTO | aioquic、quiche、ngtcp2 | 参数由 RTT/RTTVAR/ACK delay 动态计算，AP 和公式实例化较难 |
| ICE/STUN/TURN | Ta pacing、RTO、connectivity-check 重传、15–20 s keepalive、allocation lifetime/refresh | PJSIP/libnice + coturn | 角色和候选对很多，完整 ICE 状态机工程量大 |
| OSPF | HelloInterval、RouterDeadInterval、WaitTimer、RxmtInterval、LSA ageing | 两个 FRR/BIRD netns | 实现状态和 packet 种类多，初期 AP schema 较大 |
| BGP | ConnectRetryTimer、HoldTimer、KeepaliveTimer、DelayOpenTimer | FRR + BIRD/GoBGP | 默认 timer 很长，需合法缩短配置；许多规则为状态机条件式 |
| RIP/RIPng | 30 s±jitter update、180 s invalid、120 s garbage collection、triggered update delay | FRR/BIRD | 很容易实验，但默认运行时间较长，协议研究新颖性较弱 |
| Babel | Hello、IHU、Update interval、route expiry、sequenced state | babeld/FRR | 实现选择少于 BGP/OSPF，规范相对小众 |
| LwM2M | Registration Lifetime/Update、Observe pmin/pmax、Queue Mode、bootstrap/firmware-update 状态 | Eclipse Leshan + Wakaama/Anjay | 时间性质分散在 LwM2M、CoAP、Observe 和对象规范中 |
| DoIP | vehicle announcement、routing activation、alive check、diagnostic response timeout | python-doipclient + host DoIP entity | 很贴近汽车，但 ISO 13400 正文获取和许可不如 RFC/AUTOSAR 方便 |
| IEC 60870-5-104 | t0/t1/t2/t3、k/w 窗口、TESTFR/STARTDT/STOPDT | lib60870-C 两端 | MITL 非常合适，但 IEC 规范通常付费，数据集公开受限 |
| IEC 61850 GOOSE | 重传间隔序列、timeAllowedToLive、状态号/序列号 | libIEC61850 + Linux L2 multicast | 主机可跑，但二层 multicast、时间真实性和付费规范增加成本 |
| BACnet/IP | APDU timeout、segment timeout、重试次数、BBMD/foreign-device TTL | BACnet Stack、BACpypes | 标准获取受限，跨实现配置差异大 |
| Raft | randomized election timeout、heartbeat、leader election、lease/read timeout | etcd/HashiCorp Raft 多进程集群 | 主机实验极容易，但“规范”主要是论文/实现配置，不是互操作标准 |

### 2.3 不建议作为第一批对象

| 协议/方向 | 原因 |
|---|---|
| HTTP/1.1、HTTP/2、WebSocket | 有丰富顺序约束，但多数 timeout、PING 周期和响应 deadline 由实现或应用决定，规范中的定量 MITL 性质密度低 |
| 普通单播 DNS | 重试和 resolver timeout 多为本地策略；mDNS 的规范时间窗口更适合 |
| TLS 1.3 over TCP | 可靠传输下握手重传由 TCP 处理；直接研究 DTLS 更有时间逻辑价值 |
| Modbus TCP | 功能和报文约束丰富，但 response timeout 通常是实现/应用配置；若研究时间，IEC 104/OPC UA 更强 |
| Modbus RTU | t1.5/t3.5 字符间隔很适合时间逻辑，但伪终端上的主机调度无法忠实代表串口线速，需真实 UART 才有强外部有效性 |
| Classic CAN on `vcan` | 能测 UDS/应用层帧序列，却不能真实验证仲裁、bit stuffing、ACK/error frame、bus-off 和物理 bit timing |
| PTP/gPTP/TSN | Linux 软件时间戳可做功能实验，但亚毫秒/微秒性质容易被调度和时钟误差主导，严谨结果通常需要硬件时间戳 NIC |
| Kafka/Redis Sentinel/数据库心跳 | 主机实验容易，但时间规则主要来自产品配置和实现文档，难声称“从协议规范自动提取” |

## 3. 最有代表性的性质模板

以下公式是结构示意。`ε` 是主机实验允许的测量/调度容差；协商字段需要先绑定成常数。

### 3.1 有界响应

```text
G(request -> F_[L,U] response)
```

适用：SOME/IP request-response delay、mDNS response、SIP 临时/最终响应、OPC UA
Publish response。若规范没有给 response 的硬上界，就不能擅自生成 `U`。

### 3.2 周期发送与最大静默

```text
G(active -> F_(0,P+ε] heartbeat)
```

适用：BFD、VRRP、OSPF Hello、BGP KEEPALIVE、RIP update、SOME/IP cyclic offer、DDS
liveliness。若允许 jitter，应把 interval 写成 `[Pmin,Pmax]`，不能只检查平均周期。

### 3.3 超时导致状态迁移

```text
G(timer_expired_D & state_up -> F_[0,ε] state_down)
```

适用：BFD Detection Time、VRRP Active Down、OSPF Dead Interval、BGP Hold Timer、MQTT
Keep Alive、OPC UA subscription lifetime。`timer_expired_D` 最好由 trace adapter 使用最后
一次有效消息和协商参数生成，否则“连续 D 时间没有消息”会使公式和 AP 过于复杂。

### 3.4 指数退避

```text
G(retry_i & pending -> F_[RT_i-ε,RT_i+ε] (reply | retry_i+1))
```

适用：SIP Timer A/E、DHCPv6 retransmission、CoAP CON、DTLS flight。MITL 本身不做
`RT_i = min(2*RT_i-1, MRT)` 的算术；property compiler 应先按当前阶段计算每个 `RT_i`，
再生成有限组公式，或让 adapter 发出 `retry_deadline_i`。

### 3.5 租约与到期

```text
G(lease_started -> (lease_valid U_[T-ε,T+ε] lease_expired_or_renewed))
```

适用：DHCP lease、MQTT Session/Message/Will Delay、SOME/IP TTL、TURN allocation、DDS
liveliness lease。续租会重置 clock，因此 AP 必须携带 lease/session identity。

### 3.6 最小间隔/抑制窗口

```text
G(send -> G_(0,L) !send_same_class)
```

适用：BFD minimum receive/transmit interval、ICE pacing、mDNS known-answer suppression、
RTPS nack suppression。此类性质很适合由 timing mutation 主动尝试提前发送。

## 4. 推荐的主机实验 benchmark

| benchmark | 真实执行对象 | 推荐拓扑 | fuzz/扰动空间 | MITL oracle 来源 |
|---|---|---|---|---|
| SIP-Timers | PJSIP UA + Kamailio proxy/server | 3 netns：UAC、proxy、UAS；UDP | INVITE/non-INVITE、丢响应、重复、乱序、延迟、transport 切换 | RFC 3261 transaction state+pcap |
| DHCPv6-Timers | Kea server + 两种 client | client/server/relay netns | 丢 Advertise/Reply、延迟、重复、租约参数、Renew/Rebind 边界 | RFC 8415 exchange 参数+lease state |
| Routing-Timers | FRR/BIRD 的 BFD+VRRP+RIP/OSPF | 2–4 router netns | 丢 heartbeat、timer 重协商、接口 flap、进程暂停、priority 变化 | RFC timer/state machine+daemon JSON/log |
| SOMEIP-SD-Timers | vsomeip + someipy/第二 vsomeip | 两个容器/netns multicast | Find/Offer/Subscribe、TTL、initial/repetition/cyclic timing、重启 | AUTOSAR SD 状态和配置参数 |
| MQTT5-Lifecycle | Mosquitto + Paho/第二 broker | broker+2 clients | KeepAlive、disconnect 类型、Session Expiry、Will Delay、Message Expiry、QoS 序列 | OASIS normative rule+broker/client state |
| OPCUA-Subscriptions | open62541 server + asyncua/client | 两进程或两容器 | sampling/publishing 参数、缺 PublishRequest、暂停通知、session reconnect | revised interval/count+subscription state |
| DDS-RTPS-QoS | Fast DDS ↔ Cyclone DDS | publisher/subscriber 两容器 | deadline、liveliness、reliability、heartbeat/nack、writer restart、loss/delay | DDS status callbacks+RTPS pcap |
| mDNS-Timers | Avahi + python-zeroconf | 两 netns 同 multicast segment | shared/unique query、probe conflict、TC、known answers、TTL/goodbye | RFC 6762 response windows+cache state |
| TFTP-Calibration | tftp-hpa + atftp | 两 netns UDP | block loss/duplicate/reorder、timeout option、unknown TID、last block | RFC 1350/2349 block and timeout state |
| QUIC-Loss-Timers | aioquic + quiche/ngtcp2 | 两容器+netem | ACK delay、packet loss/reorder、idle、path migration、close | negotiated transport params+RFC 9000/9002 timer state |

“两种实现”很重要：同一个库同时充当 client/server 只能发现其内部一致性问题；跨实现
组合能发现对规范边界、timer rounding、重传停止条件和参数协商的不同解释。

## 5. 从规范到实验的建议流水线

1. **规范段落筛选**：抽取包含时间单位、timer、interval、lifetime、expiry、delay、
   retransmit、periodic、within、no later than、at least/at most 的规范段落，并保留
   MUST/SHALL/SHOULD 强度和适用角色。
2. **规则规范化**：拆出 trigger、precondition、clock start/reset、lower/upper bound、
   expected event、exception、角色、报文/会话 identity。
3. **参数绑定**：把报文字段、协商值和配置项绑定为一次实验的常量；例如 MQTT `K`、
   BFD negotiated interval、DHCPv6 `IRT/MRT`、OPC UA revised PublishingInterval。
4. **AP adapter**：pcap parser 提供 `send/recv/type/id`，API/log adapter 提供内部
   `state/error/timeout`，进程监控提供 crash/restart/hang。
5. **公式生成**：优先使用 bounded response、periodicity、timeout transition、backoff、
   lease、suppression 六类模板；保留原始规范引用和参数来源。
6. **测试输入**：除报文字段 fuzz 外，重点变异 delay、drop、duplicate、reorder、burst、
   pause/resume、restart、并发 session、协商 timer 和跨状态操作序列。
7. **oracle**：MITL violation 是规范时间 oracle；同时记录 crash、timeout、进程状态、
   协议 error、日志和跨实现差分，避免把监控器/AP 解析错误当成协议问题。
8. **复现与最小化**：固定实现 commit、配置、容器镜像、seed、网络 schedule 和 monotonic
   timestamp；最小化报文字段与故障/时间序列。

## 6. MITL 表达边界

- **精确等时约束**：MITL 通常不使用单点区间。规范写“at time T”时，主机实验应根据
  时钟和调度精度使用 `[T-ε,T+ε]`，或者明确改用允许 punctual interval 的 MTL。
- **动态参数**：MQTT Keep Alive、BFD interval、DHCP retransmission 和 QUIC PTO 不是
  全局常数。必须按连接/会话实例化公式，或扩展成 parametric MTL。
- **计数和标识**：MAX_RETRANSMIT、LifetimeCount、block number、packet number、session
  identity 不能只靠无数据 MITL。应由 adapter 维护有限计数器和关联关系，再产生 AP。
- **概率要求**：mDNS/BFD 的“随机/均匀 jitter”可用 MITL 检查每个样本是否落在允许
  窗口，但不能证明分布均匀；分布性质需要额外统计 oracle。
- **SHOULD/MAY**：不应与 MUST violation 混为一类。数据集至少标 `mandatory`、
  `recommended`、`optional`，实验结果分别统计。
- **不可观测内部事件**：若只能从 pcap 看到结果，不能声称检查了“timer was reset”这类
  内部动作；应改写为外部可观测后果，或接入 API/eBPF/日志插桩。

## 7. 最推荐的研究组合

### 组合 A：最快形成稳定数据集

CoAP + TFTP + MQTT 5 + mDNS + SIP。

覆盖重传、指数退避、keepalive、expiry、随机响应窗口和事务超时；实现安装容易，pcap
即可提取大部分 AP。缺点是网络层角色迁移和复杂多节点状态不足。

### 组合 B：汽车/实时中间件方向

SOME/IP-SD + DDS/RTPS + DoIP + MQTT 5/OPC UA。

无需 CAN/ECU 即可在主机运行真实实现，且比随机 CAN 帧更适合研究服务发现、liveliness、
deadline、subscription 和诊断会话。SOME/IP-SD 和 DDS/RTPS 是最值得扩展的两个对象。

### 组合 C：时间逻辑和系统状态最强

SIP + DHCPv6 + BFD + VRRP + OSPF/BGP。

覆盖协商 timer、随机退避、周期、失效检测、角色迁移和多节点状态；规范文本非常适合
提取 MITL。实验工程比应用层协议高，但不需要专用硬件。

### 建议的首批六协议

如果目标是兼顾论文新颖性、数据集多样性和可执行性，建议：

1. 保留 CoAP 作为已有基线；
2. SIP：最丰富的标准 timer 状态机；
3. DHCPv6：动态重传参数和租约；
4. BFD/VRRP：周期、失效检测和角色迁移；
5. SOME/IP-SD：汽车场景且可纯主机实验；
6. DDS/RTPS 或 OPC UA：分别代表实时 QoS 或工业 subscription 生命周期。

TFTP 可作为公式/AP/故障注入框架的 calibration target，但不建议独立作为最终研究主体。

## 8. 主要规范与实现入口

- SIP：[RFC 3261](https://www.rfc-editor.org/rfc/rfc3261.html)，
  [PJSIP](https://github.com/pjsip/pjproject)，
  [Kamailio](https://github.com/kamailio/kamailio)
- DHCPv6：[RFC 8415](https://www.rfc-editor.org/rfc/rfc8415.html)，
  [Kea](https://gitlab.isc.org/isc-projects/kea)
- BFD：[RFC 5880](https://www.rfc-editor.org/rfc/rfc5880.html)；
  VRRP：[RFC 9568](https://www.rfc-editor.org/rfc/rfc9568.html)；
  RIP：[RFC 2453](https://www.rfc-editor.org/rfc/rfc2453.html)；
  OSPF：[RFC 2328](https://www.rfc-editor.org/rfc/rfc2328.html)；
  BGP：[RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html)；
  [FRRouting](https://github.com/FRRouting/frr)
- CoAP：[RFC 7252](https://www.rfc-editor.org/rfc/rfc7252.html)，
  [libcoap](https://github.com/obgm/libcoap)，
  [aiocoap](https://github.com/chrysn/aiocoap)
- SOME/IP-SD：[AUTOSAR R24-11](https://www.autosar.org/fileadmin/standards/R24-11/FO/AUTOSAR_FO_PRS_SOMEIPServiceDiscoveryProtocol.pdf)，
  [vsomeip](https://github.com/COVESA/vsomeip)，
  [someipy](https://github.com/afflux/pysomeip)
- MQTT 5：[OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)，
  [Mosquitto](https://github.com/eclipse-mosquitto/mosquitto)，
  [Paho MQTT C](https://github.com/eclipse-paho/paho.mqtt.c)
- OPC UA：[OPC UA Part 4](https://reference.opcfoundation.org/Core/Part4/)，
  [open62541](https://github.com/open62541/open62541)，
  [asyncua](https://github.com/FreeOpcUa/opcua-asyncio)
- DDSI-RTPS：[OMG DDSI-RTPS 2.5](https://www.omg.org/spec/DDSI-RTPS/2.5/About-DDSI-RTPS/)，
  [Fast DDS](https://github.com/eProsima/Fast-DDS)，
  [Cyclone DDS](https://github.com/eclipse-cyclonedds/cyclonedds)
- mDNS：[RFC 6762](https://www.rfc-editor.org/rfc/rfc6762.html)，
  [Avahi](https://github.com/avahi/avahi)，
  [python-zeroconf](https://github.com/python-zeroconf/python-zeroconf)
- TFTP：[RFC 1350](https://www.rfc-editor.org/rfc/rfc1350.html)、
  [RFC 2349](https://www.rfc-editor.org/rfc/rfc2349.html)
- DTLS：[RFC 9147](https://www.rfc-editor.org/rfc/rfc9147.html)；
  QUIC：[RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html)、
  [RFC 9002](https://www.rfc-editor.org/rfc/rfc9002.html)
- ICE：[RFC 8445](https://www.rfc-editor.org/rfc/rfc8445.html)，
  [PJSIP/PJNATH](https://github.com/pjsip/pjproject)，
  [libnice](https://gitlab.freedesktop.org/libnice/libnice)

