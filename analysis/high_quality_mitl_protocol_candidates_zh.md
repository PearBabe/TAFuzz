# 面向状态及时序 Fuzz 的高质量 MITL 协议候选重筛选

调研日期：2026-07-16

## 1. 目标不是“找有时间词的协议”

本报告重新回答：哪些协议既能从规范中提取高质量 MITL 性质，又能在普通主机上运行
真实实现并由 fuzzer 触发有意义的规范违反？

高质量性质必须形成闭环：

```text
MUST/SHALL 规范
  -> 可关联的事件顺序、时间、状态、禁止行为
  -> fuzzer 能建立前置状态并操纵完整流程
  -> pcap/API/log 能可靠判定违反
  -> 违反至少造成 Level-B 协议后果
  -> 输入和时间/故障调度可重放、最小化
```

后果等级：

- Level A：只有公式/规范违反，未证明协议后果；不能作为主要成果。
- Level B：可复现的状态分歧、事务卡死、错误失效检测、重复/丢失/乱序处理、过期状态、
  恢复失败或跨实现互操作失败；高质量性质的最低门槛。
- Level C：进一步造成数据/功能/服务错误、长期不可用或持续资源异常；最强证据。

## 2. 重筛选方法

不采用“timer 越多分越高”的加法排名。每个候选先通过七项门槛：

| 门槛 | 通过条件 | 典型淘汰原因 |
|---|---|---|
| N：规范强度 | MUST/MUST NOT/SHALL/SHALL NOT 或强制状态机 | 只有 SHOULD、MAY、建议值或本地策略 |
| W：工作流完整性 | 至少包含触发、顺序、状态/禁止行为和规范时间语义 | 只有周期，没有流程；只有顺序却人为补 deadline |
| F：可控性 | fuzzer 能控制消息、ID、顺序、delay/drop/duplicate/restart | 前置状态无法建立或 timer 不能改变 |
| O：可观测性 | pcap、API、日志或第二实现能给出明确 verdict | 只能猜测内部 timer 是否 reset |
| C：后果 | 至少能设计 Level-B 后果 oracle | 只偏离几毫秒且无状态/功能影响 |
| H：主机可执行 | 真实 client/server/peer 可在 Linux/容器/netns 执行 | 必须依赖物理控制器、PLC、专用 NIC |
| R：可复现 | 可固定版本、配置、时钟容差和故障序列 | 高度人工、商业黑盒或不可稳定 reset |

规范是否公开是额外的复现/数据发布门槛。ISO/IEC/IEEE 付费规范并不使性质本身变差，
但会降低自动抽取数据集的可公开验证性。

### 2.1 “可提取成 MITL”还需要一层事件投影

规范原文通常不是直接可监控的原子命题。benchmark 必须先把报文、API 和日志投影成
带关联键的事件，例如 `invite_tx(call_id, branch, cseq)`、`cookie_ack(assoc_id)`、
`subscription_deleted(sub_id)`。然后按每个 transaction/session/association 分 trace，
否则两个并发流程会互相错误匹配。

适合本项目的性质模板不是单纯周期，而是：

```text
触发后限时响应： A_i -> F_[0,D] B_i
响应前禁止越序： A_i -> (!C_i U_[0,D] B_i)
寿命到期后禁用： expire_i -> (!use_i W renew_i)
确认后停止重传： ack_i -> G_(0,H] !retransmit_i
失败检测闭环：   no_heartbeat_i for D -> F_(0,E] down_i -> F_(0,R] recovery_i
```

这里的下标 `i` 是 trace adapter 处理的动态关联键，不是把无限 ID 域直接塞进普通
命题 MITL。协商值或配置值在每次 run 开始时实例化为 `D/H/E/R`；指数退避、动态
RTO/PTO 和计数上限应由 adapter 计算每一轮期望窗口，再生成有限组公式。MITL 避免
零宽的精确等式窗口，实验时记录容差，但容差不能大到掩盖状态转换错误。

最后，MITL monitor 只判“协议轨迹是否违反”；Level-B/C 后果需要独立的应用状态、
交付 ledger、路由/邻居表、subscription/session 数据或跨实现结果来证明。

## 3. 最终分层

### 3.1 P0：最建议立即构建 benchmark

| 协议 | 高价值强制工作流 | 主机真实实现 | 可触发违反 | Level-B/C 后果 | 结论 |
|---|---|---|---|---|---|
| SIP | INVITE/non-INVITE transaction、Timer A–K、response/ACK/CANCEL/BYE 顺序与终止 | PJSIP + Kamailio/OpenSIPS | 丢/延迟/重复 response/ACK，提前 BYE，错误 branch/CSeq | 事务不终止、重复会话动作、错误 dialog、互操作失败 | **首选：规范开放、timer 与状态机最完整** |
| SCTP | INIT→INIT ACK→COOKIE ECHO→COOKIE ACK；T1-init/T1-cookie；DATA/SACK/T3；SHUTDOWN 序列 | usrsctp 或 Linux SCTP，两 netns/tun | 丢/乱序 setup chunk、过期 cookie、错误 Verification Tag、暂停 ACK | 半开/重复 association、数据停滞、关闭卡死、状态分歧 | **新发现的强候选：纯协议工作流非常完整** |
| SOME/IP-SD | Initial Wait→Repetition→Main；Find→Offer→Subscribe→Ack/Nack；TTL/StopOffer | vsomeip + pysomeip/第二 vsomeip | delay/drop/reorder Find/Offer/Subscribe、TTL 边界、server restart | stale service、错误 availability、丢失/僵尸订阅、client/server 状态分歧 | **汽车方向首选，无需 ECU** |
| CoAP + Observe | CON→ACK/RST→停止重传；Message ID 去重；Observe sequence/Max-Age/cancel | libcoap + aiocoap/Californium | 丢 ACK、错 MID/Token、duplicate CON、乱序通知、过期 Max-Age | 重复操作、重传不停止、观察状态过期或两端状态分歧 | **已有基线，应先按新质量门重审现有 13 条** |
| OPC UA Subscription | CreateSubscription→PublishRequest→Notification/KeepAlive→Ack/Republish→Lifetime deletion | open62541 + asyncua/第二实现 | 缺 PublishRequest、丢/重排 notification、错误 sequence、暂停 client | 丢失/重复更新、subscription 僵死或错误删除、client/server 状态分歧 | **工业应用后果强，规范公开** |
| DDS/DDSI-RTPS | HEARTBEAT→ACKNACK→DATA/GAP；sequence；Deadline；Liveliness lease | Fast DDS + Cyclone DDS | 丢/乱序 HEARTBEAT/ACKNACK/DATA、writer restart、lease/deadline 边界 | 数据永久缺失/重复、writer 活性判断错误、可靠性状态分歧 | **最丰富但 AP/状态工程量最大** |
| IPv6 ND/NUD | NS→NA；INCOMPLETE→REACHABLE→STALE→DELAY→PROBE；RetransTimer/ReachableTime/router lifetime | Linux kernel + radvd/Scapy | 丢/延迟/重放 NS/NA/RA、改 flags/lifetime、peer restart | 错误邻居/路由存活判断、队列不失败、长期不可达或使用过期路由 | **被低估的主机内核强候选，RFC 开放** |

### 3.2 P1：很强，适合第二批

| 协议 | 高质量闭环 | 主机实现 | 为什么不是首批 |
|---|---|---|---|
| DHCPv4/v6 | DISCOVER/SOLICIT→OFFER/ADVERTISE→REQUEST→ACK/REPLY→RENEW(T1)→REBIND(T2)→EXPIRE；重传 | Kea + dhcpcd/systemd-networkd/另一 client | v4 更易起步，v6 的多 IA、relay、DUID 使 adapter 较复杂，但后果明确 |
| MQTT 5 | CONNECT/CONNACK；QoS2 四步；Keep Alive/1.5K close；Session/Message/Will Expiry | Mosquitto + Paho/EMQX | QoS 顺序本身没有统一 deadline；必须选择与 expiry/keepalive 结合的规则，不能人为补时限 |
| TURN | Allocate→permission/channel→relay→Refresh/Delete/Expiry；Permission 固定 300 s | coturn + PJSIP/libnice/自制 TURN client | 默认 lifetime 较长，需合法协商缩短 allocation；NAT/relay 拓扑多一层 |
| DoIP + UDS | routing activation→alive check→inactivity close；UDS request→P2 response/NRC 0x78→P2*→S3 session | python-doipclient + udsoncan + host DoIP entity | 客户端实现成熟，第二个完整 server 较弱；ISO 正文付费，但 AUTOSAR 强制条款公开 |
| LwM2M | Bootstrap/Registration→Update→Deregister/expiry；Observe pmin/pmax；firmware-update state | Leshan + Wakaama/Anjay | 规则跨 LwM2M Core、Transport、CoAP/Observe 和 Object 规范，归因需分层 |
| QUIC | Initial/Handshake/Application packet spaces；ACK→loss/PTO；anti-deadlock；idle/close | aioquic + ngtcp2/quiche/quic-go | 动态 RTT/PTO、加密 packet space 和实现内部状态使 black-box oracle 很难 |
| TCP | SYN 状态机；DATA→ACK→RTO 重传/双倍退避；FIN/TIME-WAIT | Linux kernel + FreeBSD/userland stack | 动态 RTO 需从 `TCP_INFO`/eBPF 投影，内核状态和 offload 会污染纯 pcap 判定 |
| ISO-TP/J1939-TP | FF→FC→CF、BS/STmin/WAIT/timeout；RTS→CTS→DT→EOMA/Abort | Linux SocketCAN ISO-TP/J1939 + can-utils | 可在 vcan 测传输层，但 ISO/SAE 正文付费，且不能声称覆盖物理 CAN 行为 |
| IEC 60870-5-104 | STARTDT/STOPDT/TESTFR；I/S/U frame sequence；k/w；t0/t1/t2/t3 | lib60870 client+server | 工作流和后果都强，但 IEC 规范付费，数据集公开引用与分发受限 |
| TFTP | RRQ/WRQ→DATA(n)→ACK(n)→DATA(n+1)，timeout 重传和 final block | tftp-hpa + atftp | 极易实验且后果明确，但规则数量和状态复杂度太小；适合作 calibration |

产品级分布式协议也能形成高质量 benchmark，但应单列为 **P1\***：ZooKeeper 的
session negotiation→heartbeat loss→session expiry→ephemeral znode 删除，以及 Kafka
consumer group 的 join/heartbeat→session timeout→member removal→rebalance→partition
reassignment。二者都能在单机多进程/容器运行，且后果分别是协调状态残留/误删、分区
重复所有权或无人处理；不足是约束来自版本化产品契约/KIP，而不是独立跨实现标准，实验
必须固定版本和协议代际。

### 3.3 P2：只保留特定高后果性质

| 协议 | 可保留性质 | 降级原因 |
|---|---|---|
| BFD | Poll→Final 后才切换 timer；Detection Time→Down；jitter/min interval | 只抽“每隔多久发包”价值低；必须绑定错误 Up/Down 或错误协商后果 |
| VRRPv3 | Advertisement、priority-zero、Active Down、Backup→Active | 后果明确但工作流短，跨实现/虚拟 IP oracle 仍可做 |
| OSPF | Hello/Dead；Down→Init→2-Way→ExStart→Exchange→Loading→Full；LSA ack/retransmit | 非常高质量，但 raw packet/state database adapter 工程量大，适合长期项目 |
| BGP + Graceful Restart | OPEN/KEEPALIVE/Hold；session restart→stale→EoR/RestartTime→delete | 后果强但默认 timer 长、route/RIB oracle 复杂；可用 FRR+BIRD |
| Raft/Tendermint/HotStuff | election/round timeout、leader/view change、log/commit 顺序 | 主机多节点很容易，但论文/算法描述不是 RFC 式一致性契约，部分同步模型也不给固定现实时间上界；更适合时序调度 fuzz，而非自动抽 MUST-MITL 主 benchmark |
| DTLS | flight→ACK、timeout retransmit、Finished/epoch ordering | timer 初值有 SHOULD/部署例外；版本支持与加密观测增加难度 |
| ICE/STUN | connectivity check、Ta pacing、RTO、nomination | TURN lifetime 比单纯 STUN retransmit更容易形成明确后果；完整 ICE 状态很复杂 |
| NFSv4.1 | lease renewal、SEQUENCE/session slot、reclaim/grace | 数据/锁状态后果强，但 Linux server/client 内部状态观测和 reset 成本高 |
| UPnP/SSDP | advertisement refresh before max-age、byebye、cache expiry | 关键随机响应时限多为 SHOULD；只保留 stale cache/service availability 类强规则 |
| DNS/mDNS cache lifecycle | response→cache→TTL expiry→requery/stop use | stale answer 后果明确且 BIND/Unbound 可主机运行，但工作流偏短；还要区分普通 TTL 与明确启用的 serve-stale 扩展 |
| NTP | request/response、poll/reachability、clock filter/select、KoD | 能运行 chrony/ntpd，但“时间”主要是报文数据与本机时钟估计，不都是 MITL 的事件间隔；时钟调整也使独立 oracle 较难 |
| LLDP、IGMP/MLD | advertisement/query→report→TTL/membership expiry→删除 | Linux/lldpd/netns 很容易，且 stale neighbor/multicast loss 有后果；但状态机短，适合校准或组合性质 |
| RTSP 2.0 | SETUP→PLAY/PAUSE/TEARDOWN、Session timeout/keepalive | 时间值多为协商或 server policy，需谨慎筛 MUST |
| IEC 61850 GOOSE、DNP3、BACnet/IP、KNXnet/IP | retransmission、TTL/confirm、select/operate、connection state | 性质可很好，但标准访问、实现成熟度或二层网络实验成本更高 |
| PostgreSQL replication、Redis Cluster/Sentinel、数据库 2PC | keepalive/node timeout、prepare→commit/abort→recovery | 后果强但 timeout 多为实现配置或运维策略，不是 wire-protocol 的强制时间语义；适合作版本特定实现 fuzz |
| 智能合约 timelock/deadline 协议 | create→wait→execute/cancel、block height/timestamp expiry | 本地主机链可运行，但 block time 通常不是受保证的现实时间，通用性质更像离散步骤/区块序 LTL；只有具体合约规范明确 deadline 与到期后果时才升级 |
| HTTP/2/3、WebSocket、gRPC、Modbus/TCP、普通 AMQP heartbeat | stream/close/ping/request-response | 顺序规则不少，但统一强制响应 deadline 通常缺失或由应用/部署配置；不能为了套 MITL 人工添加时间上界 |
| PTP/TSN、CAN/CAN-FD 链路层 | synchronization、gate schedule、arbitration/error state | 紧时限/链路行为依赖硬件 timestamp、NIC/controller 和物理媒介；纯主机模拟不足以支撑真实链路后果 |

## 4. P0 协议的“规范—fuzz—违反—后果”链

### 4.1 SIP：最佳通用研究对象

**规范闭环。** RFC 3261 要求 UDP 上发送 INVITE 后启动 Timer A=T1，并在 timer 到期时
重传、将 interval 加倍；任何 transport 上启动 Timer B=64*T1。收到响应会使 transaction
进入 Proceeding/Completed/Confirmed/Terminated 等状态；non-2xx final response 需要 ACK；Timer K 等
结束后必须进入 Terminated 并销毁 transaction。另有 BYE、CANCEL、re-INVITE 的顺序和
禁止条件。

**性质形态。** 不是单条“500 ms 重传”，而是：

```text
Calling & INVITE_tx(branch,cseq)
  -> response_before_T1 OR retransmit_same_transaction_at_T1
  -> intervals double while still Calling
  -> final_non2xx -> ACK before dialog/transaction termination
  -> Timer_B expiry without final -> Terminated
  -> no retransmission after termination
```

**fuzz workflow。** PJSIP UAC 和 UAS 之间放置可编程 UDP proxy：选择性丢弃第 n 个
provisional/final/ACK，延迟到 timer 边界，重复旧 response，交叉 branch/CSeq，提前发送
BYE/CANCEL，暂停/重启一端。

**双 oracle。** MITL monitor 判重传、顺序和终止；PJSIP/Kamailio API/log 判 transaction/
dialog 是否释放、是否重复触发会话动作、两端状态是否一致。Level B 是 transaction 永久
残留、重复动作或互操作失败；不能只报告 10 ms timer 偏差。

### 4.2 SCTP：最纯粹的强制状态机候选

**规范闭环。** RFC 9260 明确规定：INIT→INIT ACK→COOKIE ECHO→COOKIE ACK；发送 INIT
进入 COOKIE-WAIT 并启动 T1-init；收到 INIT ACK 后停止 T1-init、发送 COOKIE ECHO、
启动 T1-cookie、进入 COOKIE-ECHOED；COOKIE ACK 后停止 timer 并进入 ESTABLISHED。
T1 到期必须重传，超过 Max.Init.Retransmits 必须 abort 并报告失败。COOKIE ECHO 在收到
COOKIE ACK 前必须是 packet 第一个 chunk，且发送端不得再向 peer 发其他 packet。关闭
还有 SHUTDOWN→SHUTDOWN ACK→SHUTDOWN COMPLETE 和 T2-shutdown。

**fuzz workflow。** 使用 usrsctp userland stack 两端，通过其 UDP encapsulation 或 tun
插入 sequence proxy；丢/重复/乱序四次握手 chunk，修改 Verification Tag/cookie age，
在 COOKIE-ECHOED 注入 DATA，延迟 SACK，制造 simultaneous open/shutdown。

**后果。** association 两端状态分歧、重复 association、DATA 在未建立状态被接受、
T1/T2 不终止、shutdown 卡死、数据 delivery 停滞。usrsctp 的 API/notification 加 pcap
可以同时判断外部消息和内部 association state。

### 4.3 SOME/IP-SD：汽车方向最合适

**规范闭环。** AUTOSAR R24-11 的 server/client 状态机明确使用 Initial Wait、指数
Repetition、Main cyclic Offer；client 收到 Offer 后发 Subscribe Eventgroup，处理 Ack/
Nack；TTL 和 StopOffer/StopSubscribe 决定服务与订阅生命周期。

**fuzz workflow。** 在 vsomeip 与 pysomeip/第二 vsomeip 的 multicast network namespace
之间代理 SD UDP：修改 Entry/Option/TTL、丢/延迟 Offer/Ack、乱序 StopOffer、在 phase
边界重启 provider、并发多个 service/instance/eventgroup。

**后果。** consumer 把已过期 provider 当可用、provider 与 consumer 对 subscription
状态不一致、事件停止但订阅仍 active、恢复后长期发现不到服务。验证应读取应用 availability
callback/event delivery，而不只看 Offer 周期。

### 4.4 CoAP/Observe：已有工作需要质量重审

**高价值候选。** RFC 7252 CON 重传/ACK/RST/cancellation、duplicate detection 与 MID
生命周期；RFC 7641 notification Token/Observe sequence、128 s reorder rule、Max-Age
过期后不得继续假定表示为当前状态、RST/cancel observer。

**fuzz workflow。** 在 libcoap server 与 aiocoap client 间控制 CON/ACK/RST、MID、Token、
Observe value、Max-Age 和通知顺序，并驱动可读写资源改变。后果 oracle 是资源动作是否
重复、client 视图是否长期 stale、observer 是否泄漏、重传是否在 ACK 后继续。

**当前动作。** 现有 13 个 YAML 只做过结构有效性验证；必须逐条补充 MUST 来源、完整
workflow、fuzz 动作、外部后果和 A/B/C 等级，可能删除仅有形式价值的性质。

### 4.5 OPC UA Subscription：业务状态后果最容易展示

**规范闭环。** Publishing cycle 中 server 根据 queued PublishRequest 返回
NotificationMessage；sequence number 不能在 subscription lifetime 内重用；client 用 ACK
和 Republish 处理缺失。达到 MaxKeepAliveCount 时 server 返回 keepalive；连续
LifetimeCount 个周期无 PublishRequest 时必须删除 subscription，且 LifetimeCount 至少为
KeepAliveCount 的三倍。

**fuzz workflow。** 变异 Create/ModifySubscription 参数，暂停 PublishRequest，丢/重复/
重排 PublishResponse 和 ACK，伪造/回放 sequence，断线重连后请求 Republish。

**后果。** client 缺失或重复应用测量值、server 错误保留/删除 subscription、两端对可
republish sequence 集合理解不同。应用节点值和 subscription diagnostic counter 可作为
第二 oracle。

### 4.6 DDS/RTPS：最丰富但最难

**规范闭环。** Reliable Writer 用 HEARTBEAT 声明 sequence 范围；Reader 用 ACKNACK
指出缺失；Writer 以 DATA/DATAFRAG 或 GAP 修复/声明不可用。Liveliness lease、Deadline
和 heartbeat/nack response/suppression timer 提供定量时间语义。

**fuzz workflow。** Fast DDS 与 Cyclone DDS 跨实现，代理 RTPS UDP submessage；针对
writer/reader GUID、sequence bitmap、count、final flag、HEARTBEAT/ACKNACK/DATA/GAP
顺序做字段+时序变异，暂停/重启 writer，改变 QoS lease/deadline。

**后果。** Reliable reader 永久缺 sample、重复交付、错误 GAP 导致数据被跳过、writer
仍活跃却被判失效或反之、DeadlineMissed/LivelinessChanged 状态与实际 trace 不一致。
需要同时使用 DDS status callback 和 RTPS pcap；仅看 callback 可能无法定位 wire 违反。

### 4.7 IPv6 ND/NUD：无需应用 server 的内核状态机候选

**规范闭环。** RFC 4861 给出 INCOMPLETE、REACHABLE、STALE、DELAY、PROBE 的明确状态
转换。最后一次 reachability confirmation 经过 ReachableTime 后进入 STALE；随后有流量
则进入 DELAY，DELAY_FIRST_PROBE_TIME 内仍无确认就发送 NS 并进入 PROBE。地址解析在
MAX_MULTICAST_SOLICIT 次仍无 NA 时必须失败并向排队报文返回 Address Unreachable。
Router Lifetime、Prefix Lifetime 和 RFC 4862 的 address Valid Lifetime 又形成路由/地址
到期后禁止继续使用的闭环。

**fuzz workflow。** 两至三个 Linux network namespace 加 veth/bridge，用 Scapy 或 NFQUEUE
代理 NS/NA/RA：丢第 n 个 probe、延迟确认到 ReachableTime/DELAY 边界，改变 Solicited/
Override/Router flags、link-layer address、router/prefix lifetime，并暂停或重启邻居/路由器。
sysctl/radvd 可将长默认 timer 缩短到可测试值。

**后果。** `ip -6 neigh/route/addr` 是状态 oracle，实际 UDP/TCP delivery 是功能 oracle。
高价值违反包括：NA 后没有进入正确状态、失败后排队报文不终止、过期 router/address
仍被选用、尚有效的邻居被错误判死。只测 RA 周期或随机 delay 不够。

## 5. P1 中最值得保留的闭环

### 5.1 DHCPv4/v6

重点不是“指数退避”单条，而是租约完整生命周期：成功 ACK/Reply 后在 T1 进入 Renew，
未成功则在 T2 进入 Rebind，到 valid lifetime 后停止使用资源；T1<T2<valid lifetime，
DHCPv6 server 返回的各 IA T1/T2 必须一致。fuzzer 控制 ACK/Reply 丢失、延迟、server ID、
transaction ID、IA/lease 值和 link/reconfigure。Level B 是 client 继续使用过期 lease、错误绑定 server、
Renew/Rebind 状态不一致。

### 5.2 MQTT 5

只抽 QoS2 的 PUBLISH→PUBREC→PUBREL→PUBCOMP 会缺少规范 deadline；应选择交叉性质：

- KeepAlive=K 且连接无其他 control packet时 client 必须在 K 内发送 PINGREQ；server 在
  1.5K 未收到 control packet必须关闭连接；
- Session Expiry>0 时断线后必须保留 session，到期后必须删除；
- Message Expiry 经过后若尚未开始向 subscriber 投递，server 必须删除该副本；
- 将 QoS2 packet ID/duplicate sequence 与 Session Expiry、disconnect/reconnect 组合。

有意义后果是到期消息仍被投递、session 提前丢失/过期后复活、同一 QoS2 application
message 重复交付或 transaction 永久残留。

### 5.3 TURN

TURN 比单独 STUN timer 更符合质量门：Allocate 建立 relay state，CreatePermission/
ChannelBind 建立 peer state，Refresh 延长或删除 allocation；permission lifetime 必须为
300 s，到零必须删除；allocation 到期使所有 permission 同时失效。fuzzer 可协商短
allocation lifetime、延迟/丢 Refresh、交叉 allocation/transaction ID、在 expiry 边界
发送 relay data。Level B 是过期 allocation/permission 仍转发，或有效 allocation 被错误
删除导致 relay 连接中断。

### 5.4 DoIP + UDS

AUTOSAR DoIP 将 routing activation、tester source address、alive check、general inactivity
和 socket close 串成强制流程；错误 SourceAddress 的 alive response 必须关闭 connection。
AUTOSAR DCM/UDS 又规定 P2Server/P2*：不能及时完成服务时在 deadline 发送 NRC 0x78，
并用 S3Server 管理 diagnostic session。fuzzer 通过主机 TCP/UDP 改 routing activation、
source address、alive response、UDS request/ResponsePending 顺序和延迟。Level B 是错误
tester 占有 routing connection、session 提前/迟滞退出、请求卡死或响应在错误 session
执行。它比 CAN injection 更适合纯主机实验。

### 5.5 LwM2M

Registration 是 soft state：client 注册 lifetime，在到期前 Update；到期无 Update 时
server 删除 registration。再结合 Observe pmin/pmax 和 Firmware Update object 的状态机，
可构造“注册→更新→失效→禁止继续操作”以及“下载→校验→执行→结果”的工作流。Leshan
server/client 与 Wakaama/Anjay client 可直接在主机运行。必须区分违反属于 LwM2M、CoAP
还是具体 Object 规范，避免重复归因。

### 5.6 QUIC

QUIC 有强制性的 packet-number-space、ACK、loss/PTO 和 handshake anti-deadlock 行为：
PTO 到期 backoff 必须加倍；地址尚未验证且 server 达到 amplification limit 时不得 arm
PTO；client handshake 未确认且 Handshake packet 无 ACK 时必须设置 PTO，并在到期时发送
相应 Initial/Handshake probe。它可造成 handshake 永久停滞或错误 packet-space 恢复，
但 pcap 内容加密，通常要接入 aioquic/ngtcp2 的 qlog/内部 event 才能做可信 oracle。

### 5.7 TCP

RFC 9293 的连接状态机与 RFC 6298 的 RTO 算法有强制规则：收到新 RTT sample 后按固定
顺序更新 RTTVAR/SRTT/RTO；重传 timer 到期后重传最早未确认 segment，并把 RTO 加倍后
重启 timer。fuzzer 在 netns 间控制 ACK/drop/reorder、零窗口、half-close 和 peer restart。
高质量后果不是“RTO 差几十毫秒”，而是连接提前失败、长期不前进、错误重传或在关闭后
继续交付。动态 RTO 必须从 `TCP_INFO`、eBPF tracepoint 或固定的 userland stack 获得，
并关闭 GRO/GSO/TSO 后再用 pcap 交叉验证。

### 5.8 ISO-TP/J1939-TP：能在 vcan 做，但测试对象必须写对

ISO-TP 的多帧传输是 First Frame→Flow Control(CTS/WAIT/OVFLW)→按 BS/STmin 发送
Consecutive Frame，并受 N_As/N_Ar/N_Bs/N_Cr 等时间约束。J1939-TP 是 RTS→CTS→DT→
EOMA/Abort 或 BAM 流程。Linux 已提供真实内核 ISO-TP/J1939 socket，`vcan` 上可用 raw
socket 插入错误 sequence number、FC 状态、block size、STmin、丢帧、延迟和 abort。

这时 PUT 是 **ISO-TP/J1939 传输层**；若 payload 是 UDS，则可另做 **经 ISO-TP 承载的
UDS session/service fuzz**。它不是 CAN 数据链路层 fuzz。`vcan` 不具备真实仲裁、bit
stuffing、ACK slot、error counters 和 bus-off，因此这些 CAN/CAN-FD 链路层性质必须上
物理控制器或专门总线仿真，不能从纯主机结果外推。

### 5.9 ZooKeeper/Kafka：高后果，但属于版本化产品协议

ZooKeeper 可提取 `session established -> no heartbeat for negotiated timeout -> expired ->
ephemeral nodes deleted`，并对“timeout 内重连保持同一 session”作互补检查。Kafka 可
提取 `group join -> heartbeat lease -> missing heartbeat -> member removal -> rebalance ->
new assignment`，以 member epoch 和 partition ownership ledger 判定重复/空缺所有权。
它们都适合单机多节点故障调度 fuzz，后果也强，但公式必须标注 ZooKeeper/Kafka 版本，
不能宣传为跨实现标准一致性。

## 6. 主机 benchmark 建议

| benchmark | PUT 配对 | 拓扑 | fuzzer 控制点 | consequence oracle |
|---|---|---|---|---|
| SIP-Transaction | PJSIP UAC/UAS + Kamailio | 3 netns，中间 UDP/TCP proxy | method/header/branch/CSeq、drop/delay/reorder、restart | transaction/dialog API、应用动作计数、pcap |
| SCTP-Association | 两个 usrsctp app 或 usrsctp+kernel SCTP | UDP encapsulation/tun/netns | chunk/tag/cookie/TSN、setup/shutdown order、ACK loss | association notification、DATA delivery、pcap |
| SOMEIP-SD-Lifecycle | vsomeip + pysomeip/第二 vsomeip | multicast veth bridge | Entry/Option/TTL、phase timing、Offer/Subscribe order | availability callback、event delivery、SD trace |
| CoAP-Workflow | libcoap + aiocoap | 两 netns UDP | MID/Token/type/Observe/Max-Age、drop/duplicate/reorder | resource action、observer count、client representation |
| OPCUA-Subscription | open62541 + asyncua | 两容器 TCP | subscription params、Publish/ACK/Republish sequence | node-value ledger、diagnostic counters、client state |
| DDS-RTPS-Reliability | Fast DDS + Cyclone DDS | 两容器 UDP | submessage/seq/bitmap/count/QoS、loss/delay/restart | delivered-sample ledger、DDS callbacks、pcap |
| IPv6-ND-Lifecycle | Linux kernel + radvd/Scapy peer | host/router/peer netns | NS/NA/RA flags、drop/delay、Reachable/Router/Prefix lifetime | neigh/route/addr state、packet delivery、pcap |
| DHCP-Lease | Kea + two client implementations | client/relay/server netns | txid/DUID/IA/T1/T2/lifetime、ACK/Reply loss、link event | address/route/lease DB and client state |
| MQTT5-Lifecycle | Mosquitto + Paho/second broker | broker+publisher+subscriber | packet ID/QoS/session/expiry/keepalive、disconnect timing | application delivery ledger、broker session state |
| TURN-Lifetime | coturn + PJSIP/libnice client+peer | client/TURN/peer netns | transaction/lifetime/permission/channel、Refresh timing | relay success, allocation/permission state, pcap |
| DoIP-UDS-Session | python-doipclient/udsoncan + host DoIP entity | tester+entity TCP/UDP | routing/alive/source/P2/P2*/S3 sequence | connection/session state、response ledger |
| ISO-TP-Transfer | Linux CAN_ISOTP sockets + can-utils/raw injector | vcan 或两物理 CAN 口 | PCI/FS/BS/STmin/SN、FC/drop/delay/abort | PDU delivery、socket error、frame trace |
| ZooKeeper-Session | 3-node ZooKeeper + two clients | 单机多进程/容器 | heartbeat partition、reconnect/close、session ID/time boundary | session state、ephemeral znode/watch ledger |
| Kafka-Group | Kafka broker/controller + consumers | 单机多进程/容器 | join/heartbeat/member epoch、pause/restart、rebalance timing | assignment epoch、partition ownership/processing ledger |

这些不是协议模拟器：PUT 是真实开源进程/库，network namespace 与 proxy 只负责拓扑和
可重复故障注入。

这里把“可直接在主机实验”分成三种都可接受的形态：

1. **用户态真实 PUT**：SIP、CoAP、SCTP(usrsctp)、SOME/IP、OPC UA、DDS、MQTT 等；
2. **主机内核真实 PUT**：TCP、IPv6 ND、Linux ISO-TP/J1939，netns/veth/vcan 只是媒介；
3. **单机多进程真实集群**：ZooKeeper、Kafka、路由协议实现。

容器、netns、可编程 proxy、`tc netem`、NFQUEUE 和 vcan 都是实验 harness，不等于用协议
模拟器替代 PUT。但如果性质依赖物理仲裁、误码计数、bus-off、硬件 timestamp 或亚毫秒
调度，则“主机可运行”不等于“主机证据充分”，必须降级或上硬件。

## 7. 必须淘汰或降级的“伪高质量”性质

1. 规范只写 SHOULD/MAY 的 random delay，却把窗口外行为当 MUST violation。
2. 规范没有 response deadline，却根据实验平均延迟自行设一个上界。
3. 只检查 heartbeat interval，不检查 missed heartbeat 后的强制状态和实际后果。
4. 只检查 retransmission timestamp，不检查 ACK 后是否停止、次数是否正确、transaction
   是否最终释放。
5. 只检测状态 callback 变化，没有证明 wire sequence、correlation ID 和前置条件。
6. 违反来自 capture 丢包、主机调度、CPU pause 或 epsilon 设置，而非 PUT。
7. 用同一实现两端互相兼容证明规范正确；至少增加一个跨实现组合或规范级 reference
   oracle。
8. 把 crash 当唯一问题；很多最有价值的违反是状态分歧、重复操作、stale state 和
   progress failure。
9. 在 `vcan` 上发送 CAN frame 后声称验证了 arbitration、ACK、error confinement 或
   bus-off；这只能验证 raw socket/上层传输与应用逻辑。
10. 把 Raft election timeout、Kafka/ZooKeeper 配置值或合约 block deadline 无条件当成
    通用协议 MUST；必须标注算法假设、产品版本或具体合约规范。

## 8. 推荐路线

### 路线 1：最快形成可信论文实验

1. 重审现有 CoAP 13 条，留下真正具有 Level-B consequence 的性质；
2. 新建 SIP transaction benchmark；
3. 再建 SCTP association benchmark作为传输层跨域验证。

优点：RFC 全开放、主机部署简单、pcap 可见、timer/state machine 明确。

### 路线 2：汽车方向

1. SOME/IP-SD service/subscription lifecycle；
2. DoIP routing/alive + UDS P2/P2*/S3；
3. DDS/RTPS reliability/liveliness。

这条路线完全可以先在主机运行，不需要 CAN、ECU 或整车；之后再选择性迁移到真实 ECU。

### 路线 3：工业状态一致性

1. OPC UA Subscription；
2. LwM2M registration/firmware lifecycle；
3. IEC 60870-5-104 link state 与 timer。

优点是违反容易映射到 stale measurement、lost update、wrong subscription/registration；
限制是 IEC 规范公开性。

### 最终首选

- 已有对象：CoAP，但必须重新质量审核。
- 下一通用对象：**SIP**。
- 新颖且结构最干净：**SCTP**。
- 汽车方向：**SOME/IP-SD**，随后 DoIP/UDS。
- 丰富系统后果：**OPC UA Subscription**。
- 长期高难度对象：**DDS/RTPS**。
- 内核协议候选：**IPv6 ND/NUD**；若需要 CAN 生态但坚持纯主机，则选择 **ISO-TP**，
  不要声称测试 CAN 链路层。

## 9. 主要规范与实现

- CoAP：[RFC 7252](https://www.rfc-editor.org/rfc/rfc7252.html)、
  [RFC 7641](https://www.rfc-editor.org/rfc/rfc7641.html)、
  [libcoap](https://github.com/obgm/libcoap)、[aiocoap](https://github.com/chrysn/aiocoap)
- SIP：[RFC 3261](https://www.rfc-editor.org/rfc/rfc3261.html)、
  [PJSIP](https://github.com/pjsip/pjproject)、[Kamailio](https://github.com/kamailio/kamailio)
- SCTP：[RFC 9260](https://www.rfc-editor.org/rfc/rfc9260.html)、
  [usrsctp](https://github.com/sctplab/usrsctp)
- SOME/IP-SD：[AUTOSAR R24-11](https://www.autosar.org/fileadmin/standards/R24-11/FO/AUTOSAR_FO_PRS_SOMEIPServiceDiscoveryProtocol.pdf)、
  [vsomeip](https://github.com/COVESA/vsomeip)、[pysomeip](https://github.com/afflux/pysomeip)
- OPC UA：[Part 4 Subscription Services](https://reference.opcfoundation.org/specs/OPC-10000-4/5.14)、
  [open62541](https://github.com/open62541/open62541)、[asyncua](https://github.com/FreeOpcUa/opcua-asyncio)
- DDS/RTPS：[DDSI-RTPS 2.5](https://www.omg.org/spec/DDSI-RTPS/2.5/About-DDSI-RTPS/)、
  [Fast DDS](https://github.com/eProsima/Fast-DDS)、[Cyclone DDS](https://github.com/eclipse-cyclonedds/cyclonedds)
- DHCPv6：[RFC 8415](https://www.rfc-editor.org/rfc/rfc8415.html)、
  [Kea](https://gitlab.isc.org/isc-projects/kea)
- DHCPv4：[RFC 2131](https://www.rfc-editor.org/rfc/rfc2131.html)
- IPv6 ND/SLAAC：[RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html)、
  [RFC 4862](https://www.rfc-editor.org/rfc/rfc4862.html)
- TCP：[RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html)、
  [RFC 6298](https://www.rfc-editor.org/rfc/rfc6298.html)
- MQTT 5：[OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)、
  [Mosquitto](https://github.com/eclipse-mosquitto/mosquitto)、[Paho](https://github.com/eclipse-paho/paho.mqtt.c)
- TURN/ICE：[RFC 8656](https://www.rfc-editor.org/rfc/rfc8656.html)、
  [RFC 8445](https://www.rfc-editor.org/rfc/rfc8445.html)、[coturn](https://github.com/coturn/coturn)
- QUIC：[RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html)、
  [RFC 9002](https://www.rfc-editor.org/rfc/rfc9002.html)、[ngtcp2](https://github.com/ngtcp2/ngtcp2)
- DoIP/UDS：[AUTOSAR DoIP R23-11](https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_DiagnosticOverIP.pdf)、
  [AUTOSAR DCM R24-11](https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf)、
  [python-doipclient](https://github.com/jacobschaer/python-doipclient)
- LwM2M：[OMA LwM2M Core 1.2.2](https://www.openmobilealliance.org/release/LightweightM2M/V1_2_2-20240613-A/HTML-Version/OMA-TS-LightweightM2M_Core-V1_2_2-20240613-A.html)、
  [Leshan](https://eclipse.dev/leshan/)、[Wakaama](https://github.com/eclipse/wakaama)
- IEC 104：[IEC 60870-5-104](https://webstore.iec.ch/en/publication/25054)、
  [lib60870](https://github.com/mz-automation/lib60870)
- CAN 上层：[Linux ISO-TP](https://docs.kernel.org/networking/iso15765-2.html)、
  [Linux J1939](https://docs.kernel.org/networking/j1939.html)、
  [SocketCAN](https://docs.kernel.org/networking/can.html)
- 分布式产品协议：[ZooKeeper session](https://zookeeper.apache.org/doc/current/zookeeperProgrammers.html)、
  [Kafka consumer rebalance protocol](https://kafka.apache.org/42/operations/consumer-rebalance-protocol/)
