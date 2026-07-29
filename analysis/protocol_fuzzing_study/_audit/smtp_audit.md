# SMTP MITL 性质独立审计

审计日期：2026-07-13（Asia/Shanghai）  
审计对象：`_staging/ietf_app_protocols/smtp/{proposals.json,evidence.json,excluded.md}`  
审计边界：只读核验；未修改 staging、正式 catalog、Exim 或 MightyPPL/MoniTAal 源码，未构建 SUT。

## 结论

七条公式的 RFC 数值、lower-bound 方向、半开区间边界和手工正反 trace 都正确；固定源码 commit 也真实存在，并且正好是 Exim 4.89 tag 指向的 commit。问题集中在两处：

1. `SMTP-TIMEOUT-01`--`06` 是 **SMTP client/outbound transport** 性质，而 ProFuzzBench 的 Exim harness 用 `exim -bd ... -oX 25` fuzz **SMTP server/inbound**；标准 benchmark 不会走 `src/src/transports/smtp.c` 的这六条路径。
2. 多数卡片只锚定了 phase-specific `smtp_read_response()` 调用，没有完整锚定真正产生 `ETIMEDOUT` 的 `smtp_out.c`/`ip.c` 路径；MAIL/RCPT/DATA 在 PIPELINING 下还把“命令 flush”和“开始读取该响应”混成了一个事件。

因此当前严格结论为：**APPROVE 0 / FIX 7 / REJECT 0**。这七条都可修复，不需要因公式或 RFC 证据而永久排除。

| ID | 结论 | 主要原因 | 修复后协议级准入 |
|---|---|---|---|
| `SMTP-TIMEOUT-01` | `FIX` | client 角色未声明；220 wait 起点和 ETIMEDOUT 公共路径未完整映射 | 可准入 client 子目录 |
| `SMTP-TIMEOUT-02` | `FIX` | PIPELINING 下 MAIL flush/read 起点混合；复合 symbol 与 timeout 路径不完整 | 可准入 client 子目录 |
| `SMTP-TIMEOUT-03` | `FIX` | RCPT 响应关联正确，但计时起点晚于实际 flush；第二源码锚点未独立列出 | 可准入 client 子目录 |
| `SMTP-TIMEOUT-04` | `FIX` | DATA flush 与等待 354 的 read 起点不等价；timeout 公共路径缺失 | 可准入 client 子目录 |
| `SMTP-TIMEOUT-05` | `FIX` | `transport.c` 主 hook 真实，但必须限定 SMTP context 且每次函数调用只发一次 start | 可准入 client 子目录 |
| `SMTP-TIMEOUT-06` | `FIX` | RFC 5321 的 final-period 性质被扩展到 BDAT/PRDR/LMTP；timeout 路径缺失 | 限定 classic DATA 后可准入 |
| `SMTP-TIMEOUT-07` | `FIX` | 当前 start hook 只覆盖 plaintext；泛化到 STARTTLS 缺源码锚点；5 分钟 wall-clock 触发性被高估 | 限定 plaintext server 后可准入 |

准入计数解释：

- 若“协议级 catalog”允许按角色分目录，完成下述修改后可恢复为 **7/7**。
- 若主实验坚持现有 ProFuzzBench Exim server harness，则 `01`--`06` 不可作为该 campaign 的可达主性质；只能保留在 client-role 附录或新增 outbound-client harness。现有 harness 下修复后最多 **1/7**（`07`）角色可达。
- `07` 的真实阈值是 5 分钟；不采用虚拟时钟或长连接 campaign 时，它虽然代码可达，通常仍不会在 AFLNet 单 testcase 时间内提供指导信号。不得为了吞吐擅自缩放 RFC 常数。

## 规范与公式核验

[RFC 5321 §4.5.3.2](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.3.2) 先要求客户端具有 per-command timeout 机制，再将七个值表述为推荐的 minimum；服务器 5 分钟项同样是 SHOULD-level minimum。卡片中的 `SHOULD minimum` 没有把软规范提升为 MUST，判定正确。

| RFC 小节 | 卡片值 | 核验 | 边界解释 |
|---|---:|---|---|
| §4.5.3.2.1 Initial 220 | 300000 ms | 正确 | `[0,300000)` 禁止早退，恰在 300000 ms 允许 |
| §4.5.3.2.2 MAIL | 300000 ms | 正确 | 同上 |
| §4.5.3.2.3 RCPT | 300000 ms | 正确 | 每个 RCPT 独立 |
| §4.5.3.2.4 DATA initiation | 120000 ms | 正确 | 仅等待 354 |
| §4.5.3.2.5 Data block | 180000 ms | 正确 | 每个数据块/TCP SEND 独立 |
| §4.5.3.2.6 DATA termination | 600000 ms | 正确 | classic DATA final period 后等待 250 |
| §4.5.3.2.7 Server | 300000 ms | 正确 | 等待发送方下一命令的 minimum |

七条公式均为：

```text
G* (start -> G [0,T) (!timeout))
```

这个方向只禁止 **early timeout**，不要求在 `T` 时刻 timeout，也不禁止晚于 `T` timeout。因此：

- 当前 `timeout@T` 正例和 `timeout@(T-1)` 反例都是决定性的；
- 不需要“late negative”，因为晚 timeout 是该性质允许的行为；
- 可选增加“response/cancel 后无 timeout”的正例，但它不是准入必需项；
- 必须继续维持“一次 obligation generation 一个投影词”。否则当前 TAMonitor 的已知 overlapping-trigger 限制可能掩盖违反。

## 固定实现与 benchmark 核验

- GitHub commit API 能解析 `38903fb5b864ee99904d035337c66891604d9678`；annotated tag `exim-4_89` 的 object 正是该 commit。
- ProFuzzBench commit `8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074` 的 `subjects/SMTP/Exim/Dockerfile:82-102` 两次执行 `git checkout 38903fb`，所以 evidence 中的 benchmark pin 真实。
- 同一 Dockerfile 施加四个 patch。审阅 patch 后，计时相关的 `smtp.c`、`smtp_in.c`、`smtp_out.c`、`ip.c` 没有被改；`transport.c` patch 只改 1081 行附近，`globals.c` patch 只改 1237 行附近，因此本报告所列 timer 行号未漂移。
- ProFuzzBench `subjects/SMTP/Exim/run.sh:25-35` 启动 daemon 并让 AFLNet 连接 TCP/25；这是 server/inbound campaign，不会自然执行 outbound client transport。

固定源码 SHA-256（从上述 commit 的 raw 文件取得）：

| 文件 | SHA-256 |
|---|---|
| `src/src/transports/smtp.c` | `a0f2003d56da728a40fc42ce1d9dba25c8628c3de3448095de4a97b40432a2b8` |
| `src/src/transport.c` | `772556af220e58cfefa801c9915fe95f3fac6b5389604a955d8d7560aa9c8c85` |
| `src/src/smtp_in.c` | `678abb6ff0fbd9133308afbc2ce8f44aaac97285c71bfe987d36b0f556f16` |
| `src/src/globals.c` | `9234720ecaa8d4f42c7ca3afa69b2f360c2ae0018ae75fda1d2395cc1133e984` |

所有 response-timeout 卡片应补充下列公共源码证据：

- [`smtp_out.c:457-520`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L457-L520)：`read_response_line()` 调用 `ip_recv()` 并保留 `errno`；
- [`smtp_out.c:548-608`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/smtp_out.c#L548-L608)：`smtp_read_response()` 的失败返回；
- [`ip.c:478-524`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L478-L524)：`fd_ready()` 使用绝对剩余时间并在到期时设置 `ETIMEDOUT`；
- [`ip.c:548-570`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/ip.c#L548-L570)：`ip_recv()` 将结果返回上层；
- [`smtp.c:508-525`](https://github.com/Exim/exim/blob/38903fb5b864ee99904d035337c66891604d9678/src/src/transports/smtp.c#L508-L525)：`check_response()` 将 `ETIMEDOUT` 分类成 SMTP timeout。

## 逐条修复要求

### SMTP-TIMEOUT-01 — `FIX`

RFC 值和公式正确。Exim 默认 `command_timeout=5*60` 位于 `smtp.c:222`，初始 greeting read 位于 `smtp_setup_conn():1638-1643`，均真实。

必须修改：

- 新增 `sut_role: SMTP_CLIENT`、`benchmark_reachability: NOT_REACHED_BY_PROFUZZBENCH_EXIM_SERVER`。
- 将 `smtp_waiting_initial_220` 定义为：`smtp_connect()` 成功返回 socket（`smtp.c:1544-1549`）后创建一次初始 greeting obligation；不要把较晚的 `smtp_read_response()` 调用冒充 TCP 建连时刻。
- 将 `source_lines` 扩为 `1544-1643;2095-2099`，并加入上述 `smtp_out.c`/`ip.c` auxiliary anchors。
- 将 `instrumentation_timing` 改为：connect 成功后发 start；`smtp_read_response()` 返回 false 且 `errno==ETIMEDOUT` 时、进入 `RESPONSE_FAILED` 前发 timeout。当前文本所称“its ETIMEDOUT branch”在 `1631-1643` 内并不存在。
- wall-clock `triggerability` 从 `HIGH` 降为 `LOW`；只有引入可信虚拟时钟时才能另记 profile 级 `HIGH`。

### SMTP-TIMEOUT-02 — `FIX`

MAIL 的 5 分钟 minimum 与两个 response-read 位置真实：pipelined `sync_responses():742-750`，直接路径 `smtp_write_mail_and_rcpt_cmds():2383-2396`。

必须修改：

- 新增 client 角色与当前 server benchmark 不可达标记。
- `source_symbol` 不应写成不存在的单一符号 `sync_responses/smtp_write_mail_and_rcpt_cmds`；改成主 symbol + `auxiliary_source_mappings` 两个真实函数。
- `smtp_mail_response_wait_started` 必须绑定 **成功 flush MAIL command** 的时刻。PIPELINING 时命令可先进入 buffer，真正 flush 在 `smtp_out.c:326-349`；适配器需在一次 flush 后为其中每个命令建立 ordinal，再投影 MAIL generation。
- timeout 事件仍由该 MAIL generation 的 `smtp_read_response()` false + `errno==ETIMEDOUT` 产生，并补公共 timeout anchors。
- `triggerability` 降为 `LOW`。

### SMTP-TIMEOUT-03 — `FIX`

这是七条中 response/ordinal 关联最完整的一条：`sync_responses():786-825` 按下一个 `PENDING_DEFER` 地址匹配 RCPT，并有明确 `errno == ETIMEDOUT` 分支。公式和 per-RCPT projection 正确。

必须修改：

- 新增 client 角色与当前 server benchmark 不可达标记。
- 把第一个源码范围从 `786-820` 延长到 `786-825`，使完整 timeout outcome/return 可见；将 `smtp_write_mail_and_rcpt_cmds():2440-2480` 作为独立 auxiliary mapping，而不是复合 symbol。
- start 事件绑定 `flush_buffer()` 实际发送该 RCPT 的时刻；`sync_responses()` 的 read 位置用于 response ordinal/timeout 关联，不能替代 wire-send 起点。
- `triggerability` 降为 `LOW`。

### SMTP-TIMEOUT-04 — `FIX`

RFC 的 2 分钟值与 Exim 使用更长的 300 秒 `command_timeout` 均正确。`smtp.c:2659-2665` 发送并 flush DATA，`sync_responses():911-916` 读取期望 3xx 的 response。

必须修改：

- 新增 client 角色与当前 server benchmark 不可达标记。
- start 绑定 `smtp_write_command(..., FALSE, "DATA\\r\\n")` 成功 flush；PIPELINING 下 `sync_responses()` 会先消费 MAIL/RCPT response，因此“开始读 DATA response”不是 DATA 发送时刻。
- 将两个真实函数分成主/auxiliary mappings，并补 `smtp_out.c`/`ip.c` timeout anchors。
- timeout 只在 pending-DATA response generation 返回 `ETIMEDOUT` 时发，不把 4xx/5xx、EOF 或其他 I/O error 合并进 AP。
- `triggerability` 降为 `LOW`。

### SMTP-TIMEOUT-05 — `FIX`（主 hook 真实性确认）

把主 hook 改到 `src/src/transport.c:216-306` 是 **正确且必要** 的。`transport_write_block()` 在 219 行复制 `transport_write_timeout`，248 行按剩余时间 arm alarm，257-260 行把 SIGALRM 转为 `ETIMEDOUT`，302-306 行处理 incomplete write 耗尽剩余时间。`smtp.c:2736-2749` 在消息发送前把 `transport_write_timeout` 设为 `data_timeout`；默认值 300 秒在 `smtp.c:224`。这比只锚定 `smtp_deliver()` 更接近 RFC 所说的每个 data buffer/TCP SEND。

必须修改的只是事件契约：

- 新增 client 角色与当前 server benchmark 不可达标记。
- 将 start AP 改名/定义为“SMTP DATA context 中一次 timed `transport_write_block()` invocation 开始”，不要声称 hook 时已经知道 write 会阻塞。
- 在函数每次 invocation **只发一次** start（首个 timed write 前）；循环中重试时的 `alarm(local_timeout)` 不得产生新的 trigger。timeout 仅在 `257-260` 或 `302-306` 两个 `ETIMEDOUT` return 发出。
- 因 `transport_write_block()` 是通用 transport 函数，hook 必须由 SMTP outbound context、目标 fd、`smtp_command == "sending data block"`/等价显式上下文和 block ordinal 共同 guard，不能采集 pipe/appendfile 等调用。
- wall-clock `triggerability` 从 `MEDIUM` 降为 `LOW`；若有虚拟时钟 profile，另行记录。

修完这些字段后该卡无需改变公式、T 值或正反 trace。

### SMTP-TIMEOUT-06 — `FIX`

classic DATA 的 10 分钟 minimum、Exim `final_timeout=10*60` 以及 `smtp.c:2820-2821` 的 final response read 都正确。

必须修改：

- 新增 client 角色与当前 server benchmark 不可达标记。
- 当前 AP/自然语言把 `final period/last BDAT` 合并，但标准证据只有 RFC 5321 classic DATA。将 scope 明确为 `SMTP classic DATA; CHUNKING/BDAT, PRDR and LMTP excluded`，删去 `last BDAT`；或者另取 RFC 3030/PRDR/LMTP 证据做不同卡片，不能借用本卡常数。
- source 主范围收窄并明确为 `smtp_deliver():2766-2772;2815-2827`；start 在包含 final period 的最后数据 buffer 成功发送后，timeout 在对应 non-LMTP final read 返回 `ETIMEDOUT` 时发。
- 补公共 timeout anchors，`triggerability` 降为 `LOW`。

### SMTP-TIMEOUT-07 — `FIX`

RFC server minimum、`smtp_receive_timeout=5*60`（`globals.c:1325`）、plaintext `smtp_getc():416-430` 和 `command_timeout_handler():838-850` 均真实。per-generation projection 也正确。

必须修改：

- 新增 `sut_role: SMTP_SERVER`。
- 当前源码 start hook 只覆盖 plaintext。主实验若沿用 ProFuzzBench plaintext TCP/25，应把 scope/limitations 明确写成 `PLAINTEXT_EXIM_SERVER_PROFILE`，并加入 `smtp_read_command():1424-1450` 作为 handler 安装与 command-phase 证据。
- 若仍声称覆盖 STARTTLS，则还必须加入固定 build variant 及 `tls-openssl.c:2370-2410`、`tls-gnu.c:2166-2217` 的 `tls_getc()` timer-arm 路径；不能只留一个 review question。
- start 只在输入 buffer 为空、即将执行 timed read 时发；timeout 只取 command-phase `command_timeout_handler`，不得混入 DATA-phase receive timeout。
- `triggerability` 从 `HIGH` 降为 `LOW`（真实 300 秒）；角色/代码可达与 fuzzing 时间上可触发是两件事。

## `evidence.json` 与 `excluded.md` 审计

`evidence.json` 的 RFC section 列表和 Exim tag/commit 正确，但应补：

- `sut_roles`: client（01--06）与 server（07）；
- ProFuzzBench commit、Dockerfile pin、server daemon run command，以及“六条 outbound client 性质不被当前 harness 覆盖”的明示；
- 公共 timeout 源 `smtp_out.c`、`ip.c`；
- plaintext/TLS variant 边界；
- patch audit 结论（相关 timer 行未被 benchmark patch 改动）。

`excluded.md` 有一处事实错误：其“Retry schedule ... `NO_NUMERIC_BOUND`”不成立。[RFC 5321 §4.5.4.1](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.5.4.1) 给出一般 retry interval 至少 30 分钟的 SHOULD-level 指导，也给出 4--5 天 give-up 的较弱建议。正确处理应是：

- 将 reason 改为 `CONTEXT_DEPENDENT_SOFT_GUIDANCE`，说明 30 分钟带有“in general”和 reason-aware variable strategy 例外，4--5 天不是精确单值规范；或
- 另建条件性质，例如仅在 adapter 能证明“普通消息 + 通用策略 + 无 reason-specific exception”时使用 1800000 ms lower bound。

Exim 4.89 的示例默认 retry rule 位于 `src/src/configure.default:773-790`，前两小时是 15 分钟；实际计算/`next_try` 更新在 `src/src/retry.c:574-827`。这进一步说明不能把 30 分钟无条件套到当前 Exim profile，但也不能说 RFC 没有数值。

其余三项排除理由正确：minimum 不等于 exact deadline；RFC 明确反对 whole-transaction timeout；TCP connect timeout 应留在 TCP catalog。

## MightyPPL/TAMonitor 独立验证

使用现有 `tool/MightyPPL/build/TAMonitor`，对七条 staging 公式分别运行：

```text
TAMonitor --formula <formula.mitl> --word finite --build-mode flatten --state symbolic --build-only --out <dir>
TAMonitor --trace <positive.trace> --formula <formula.mitl> --word finite --build-mode flatten --state symbolic --out <dir>
TAMonitor --trace <negative.trace> --formula <formula.mitl> --word finite --build-mode flatten --state symbolic --out <dir>
TAMonitor --trace <positive.trace> --formula <formula.mitl> --word finite --build-mode flatten --state concrete --out <dir>
TAMonitor --trace <negative.trace> --formula <formula.mitl> --word finite --build-mode flatten --state concrete --out <dir>
```

临时结果位于 `/tmp/tafuzz_smtp_audit_validation/validation/`，不属于交付物。观测结果：

| ID | build | positive symbolic/concrete | negative symbolic/concrete | 一致性 |
|---|---|---|---|---|
| SMTP-TIMEOUT-01 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |
| SMTP-TIMEOUT-02 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |
| SMTP-TIMEOUT-03 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |
| SMTP-TIMEOUT-04 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |
| SMTP-TIMEOUT-05 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |
| SMTP-TIMEOUT-06 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |
| SMTP-TIMEOUT-07 | PASS | POSITIVE / POSITIVE | NEGATIVE / NEGATIVE | PASS |

这只证明公式/trace 与当前 monitor 自洽，不替代 RFC、角色可达性和源码事件映射审计。

## 未决问题

1. 最终 catalog 是否允许同一协议拆成 `client`/`server` 两个角色？若不允许，`01`--`06` 应移到非主实验附录，而不是与 `07` 混在一个 Exim-server 主目录。
2. 是否会提供可信虚拟时钟/时间注入？若没有，七条 2--10 分钟性质不适合高吞吐同步 guidance，只适合作为长 trace/offline oracle。
3. `SMTP-TIMEOUT-06` 是否需要覆盖 CHUNKING/BDAT？若需要，必须另做 RFC 3030 性质与源码卡片。
4. RFC 5321 30 分钟 retry 指导是做 caveated candidate，还是以 `CONTEXT_DEPENDENT_SOFT_GUIDANCE` 保留在排除表？二者都比当前 `NO_NUMERIC_BOUND` 准确。

## 复核命令与写入范围

核心只读命令：

```text
curl -fsSL https://www.rfc-editor.org/rfc/rfc5321.txt
curl -fsSL https://raw.githubusercontent.com/Exim/exim/38903fb5b864ee99904d035337c66891604d9678/<path>
git -C /tmp/tafuzz_profuzzbench_index show 8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074:subjects/SMTP/Exim/Dockerfile
git -C /tmp/tafuzz_profuzzbench_index show 8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074:subjects/SMTP/Exim/run.sh
python3 <temporary validation driver using generate_multi_protocol_catalog.validate_property>
```

唯一工作区写入：`analysis/protocol_fuzzing_study/_audit/smtp_audit.md`。Agent Reach CLI 在本环境不存在（`command not found`），因此版本检查未执行；互联网核验使用其文档规定的 official-web/GitHub `curl` 路径完成。
