# Kamailio/SIP 运行时插桩与原子命题实施蓝图

状态：设计冻结候选；尚未修改或构建 Kamailio。  
固定源码：Kamailio `2648eb330b133a20f1398d59a28c53532106cad3`。  
适用范围：TAFuzz 的 SIP/Kamailio 首个真实运行适配器；原则可复用于其他协议。

## 1. 最终架构决策

不能把 MITL 原子命题名直接写进 Kamailio，也不能用“某函数被调用”代替“某协议事实已经发生”。采用以下固定通路：

```text
Kamailio 窄源码 hook / TM callback
  -> 固定 64-byte RAW ProtocolEvent
  -> 每进程 SPSC ring
  -> 独立 sidecar
  -> 完整性、时钟、drop、进程存活检查
  -> message / transaction / branch / timer generation correlation
  -> versioned raw-event-to-AP rules
  -> 每个 obligation instance 的完整 valuation timed word
  -> MITL monitor + validity/closure gate
  -> SATISFIED / VIOLATED / UNKNOWN
  -> 与正式 verdict 分离的在线 guidance snapshot
```

采用 callback-first hybrid：能由 Kamailio TM callback 准确得到的事实优先使用 callback；lookup outcome、事务提交、reply state commit、send 返回值、timer arm/cancel/fire 等 callback 无法准确表达的事实使用少量窄源码 patch。Movec 式 AOP 可借鉴 pointcut/action 分离思想，但不适合直接承担本方案：固定源码中有宏、inline timer、内部状态写入和 send return 语义，而且 Movec 本身不提供 MITL、generation correlation、完整性与多进程 ring 契约。

## 2. 原子命题的设置规则

### 2.1 四类符号

- `ev_*`：瞬时事件，只在某个已经提交的 raw fact 位置为真。
- `st_*`：adapter 根据此前完整事件历史维护的持续状态。
- `cfg_*`：一次 run 内不变的配置事实。
- `cap_*`：采集/执行能力，例如 timer driver 是否运行、send hook 是否启用。

SUT 只产生 raw event；以上 AP 均由 adapter 产生。

### 2.2 每个 AP 必须填写的契约

每个 AP registry 条目至少包含：

```yaml
ap_id: ev_uas_reply_commit_non2xx
kind: event
raw_dependencies: [UAS_REPLY_COMMIT]
predicate: method == INVITE and 300 <= status <= 699
instance_key: [subject_id]
truth_point: raw event commit timestamp
required_capabilities: [CAP_UAS_REPLY_COMMIT]
closure: MSG_PROCESS_END for the same message
controllability: INDIRECT
profile: [KAM-UAS, KAM-PROXY]
source_mapping_status: PROVEN
```

还必须声明合法 supersession、event-loss taint class、角色、方向、时间误差政策和对应固定源码范围。缺任一项的 AP 不进入正式 oracle。

### 2.3 硬规则

1. 一个 AP 只表达一个事实。状态提交、发送尝试、发送成功、timer arm、wait、destroy 必须分开。
2. trigger 和 outcome 必须来自独立证据链。不能让“实现已经正确匹配”同时成为性质 antecedent 和 consequent。
3. trigger 只能依赖当前或过去。禁止 `invite_auto_100_obligation = 预计未来处理超过 200 ms` 这类预知未来的 AP。
4. “没有看到事件”不能直接当成 false。只有到达 message macrostep end、deadline 或对象 close，且 required hooks 完整、无 drop，才能关闭 absence obligation。
5. `passed_to_tu` 只能来自明确的 route/TU marker 或 TM gate 结果，不能由 parse、lookup 或 timer stop 推导。
6. “实际发送”至少要求本机 send 返回成功；函数入口、buffer commit、callback ready 和 `put_on_wait()` 都不能证明发送成功。
7. 实现字段先用实现名，例如 `st_impl_uas_status_1xx`；只有 profile mapping 已证明后才映射成 `st_rfc_invite_proceeding`。
8. 动态 Call-ID、CSeq、Via branch、transaction id 是 correlation metadata，不进入 AP 名字。
9. 同一语义动作的多个事实可有相同物理时间，以 producer sequence 保序；禁止由 adapter 人为添加 1 ms/2 ms。
10. 零 trigger 的 run 是 `NOT_EXERCISED`，不是“性质已满足”。eligibility 与 verdict 分开报告。

### 2.4 不再使用的复合/非法 AP

- `invite_tx_completed_non2xx` 应拆成 `ev_uas_reply_commit_non2xx`、`ev_local_send_accepted_same_reply` 和 timer/state facts。
- `invite_tx_confirmed_ack_absorbed` 应拆成 `ev_ack_negative_invite_match`、`ev_tm_ack_absorb`、`ev_timer_cancel_result`、`ev_wait_arm_result`。
- `invite_tx_terminated_without_ack_or_timer_h` 不应由 SUT 发出。它是 adapter 对 `TX_HASH_UNLINK/TX_DESTROY` 与历史 ACK/timer fire 的违规分类。
- `noninvite_tx_proceeding_response_sent` 与 `noninvite_tx_completed_final_sent` 必须拆分 state commit、send result 和 wait/timer。
- `branch_cancel_sent`、`cancel_tx_200_ok`、`original_invite_tx_487`、`proxy_forward_100_trying` 都只能由带方向和 provenance 的成功 send fact 派生。

### 2.5 命题与公式的具体写法

不要为了让所有规则看起来像“实时性质”而给同步路径统一塞入 `[0,2] ms`。本方案把义务分成两类：

1. RFC 明确给出真实时间界的义务使用 MITL metric interval，例如 auto-100 的 200 ms。
2. 同一输入 macrostep 内的因果/状态规则使用强 until、finite-instance closure 或 adapter postcondition；它们仍是 MITL/LTL 子集，但没有虚构 wall-clock deadline。

典型写法如下：

```text
# 事务创建：每个 create-attempt 单独建 monitor，MSG_PROCESS_END 为 closure
start_001 := ev_tx_create_attempt_invite
goal_001  := ev_tx_create_commit_invite
rule_001  := goal_001 must occur before ev_msg_process_end_same_message

# auto-100：真实 RFC 时间
G(start_auto100 -> F_[0,200ms]
  (ev_local_send_accepted_100_same_tx OR ev_tu_response_commit_same_tx))

# negative INVITE retention：adapter 维护 waiting 状态
G(st_waiting_for_negative_ack_or_h -> !ev_tx_hash_unlink)

# lookup：expected 由独立 shadow model 产生
G(ev_shadow_expected_match -> lookup FOUND(same subject) before macrostep end)
G(ev_shadow_expected_no_match -> lookup NOT_FOUND before macrostep end)

# branch CANCEL：生命周期安全状态，不是 2 ms 禁止窗口
G(st_branch_open_without_provisional AND !cfg_force_cancel
  -> !ev_downstream_cancel_send_accepted_same_branch)

# proxy 100 suppression
G(st_suppress_100_episode AND cfg_relay_100_off
  -> !ev_upstream_100_send_accepted_same_provenance)
```

这里的 `before macrostep end` 由 per-instance adapter/closure gate 实现，不需要向物理时间加 epsilon。若要全部交给当前 TAMonitor，必须先增加并回归验证“同一 timestamp、不同 producer sequence 的零时延 position”语义；在此之前，同一同步动作中不可区分的 facts 原子合并，需要区分先后的 postcondition 由 adapter 判定。绝不把 sequence ordinal 转换成 1 ms/2 ms。

## 3. 64-byte 事件 ABI

```c
#include <stdint.h>
#include <stdatomic.h>
#include <stdalign.h>

typedef struct {
    uint64_t mono_ns;
    uint64_t run_id;
    uint64_t producer_seq;
    uint64_t corr_hi;
    uint64_t corr_lo;
    uint64_t subject_id;
    uint32_t generation;
    uint32_t arg0;
    uint32_t arg1;
    uint16_t hook_id;
    uint8_t  event_type;
    uint8_t  flags;
} tafuzz_event_t;

_Static_assert(sizeof(tafuzz_event_t) == 64,
               "tafuzz_event_t ABI must remain 64 bytes");

#define TAFUZZ_RING_CAP 4096u
_Static_assert((TAFUZZ_RING_CAP & (TAFUZZ_RING_CAP - 1u)) == 0u,
               "ring capacity must be a power of two");

typedef struct {
    _Alignas(64) _Atomic uint64_t head;
    _Alignas(64) _Atomic uint64_t tail;
    _Alignas(64) _Atomic uint64_t dropped;
    _Atomic uint64_t dropped_class_mask;
    uint32_t producer_id;
    uint32_t producer_epoch;
    tafuzz_event_t slot[TAFUZZ_RING_CAP];
} tafuzz_ring_t;
```

`arg0/arg1/flags` 由 event schema 解释，禁止 C bit-field、raw pointer identity、动态字符串和 AP 名字。文件头保存 schema version、endianness、Kamailio commit、hook table hash、AP ruleset hash、profile、clock id/resolution、producer 角色和 keyed hash 信息。

4096 个槽位为每 producer 256 KiB；32 个 producer 约 8 MiB。

### 3.1 时间

- 统一使用 `clock_gettime(CLOCK_MONOTONIC, ...)`，同时保存 Kamailio logical tick/deadline 作为 timer payload。
- 同 producer 按 `(mono_ns, producer_seq)` 排序。
- 不同 producer 若缺乏因果 link，且不同合法线性化会给出不同 verdict，则报告 `UNKNOWN_AMBIGUOUS_ORDER`。
- 纳秒转换 integer-ms 时保留外包区间；若量化不确定性跨越 deadline，报告 `UNKNOWN_TIMESTAMP_BOUNDARY`。
- clock 失败置 `CLOCK_INVALID`，不能写时间 0 继续判定。

### 3.2 Correlation 和 testcase 归属

- `corr_hi/corr_lo` 是对规范化 Call-ID、CSeq number/method、top Via branch、sent-by 的带 campaign nonce 的 128-bit keyed digest。
- 事务成功创建后，用共享 64-bit counter 分配 `subject_id`，并存入 transaction cell；禁止用可复用指针作持久 ID。
- branch、timer 和 retransmission buffer 继承 `subject_id`；每次成功 arm/re-arm 递增 `generation`。
- 异步 callback 继承对象创建时的 `run_id`，不能读取当时的全局 current run，否则旧 testcase timer 会污染新 testcase。
- 新消息仍携带当前 message/run id，因此“case B 的重传命中 case A 创建的事务”可同时保留输入归属和对象归属。
- monitor 实例使用 `H(property_id, subject_id, generation, trigger_seq)`，overlapping trigger 不能共享实例。

## 4. Raw event 集合

### 4.1 生命周期与完整性

`PRODUCER_START`、`PRODUCER_STOP`、`RUN_BEGIN`、`RUN_END`、`WATCHDOG_CLOSE`、`RX_SIP_PARSED`、`MSG_PROCESS_END`、`CAPABILITY_SNAPSHOT`、`TIMER_DRIVER_START/TICK`。

### 4.2 事务与路由

`TX_CREATE_ATTEMPT`、`TX_CREATE_COMMIT`、`TX_READY`、`TX_LOOKUP_RESULT`、`TM_GATE_RESULT`、`TU_BOUNDARY_MARK`、`REQ_RETRANSMISSION_MATCH`、`ACK_MATCH`。

### 4.3 Reply 与 send

`RESPONSE_MATCH_RESULT`、`REPLY_INPUT`、`RESPONSE_DECISION_COMMIT`、`UAS_REPLY_COMMIT`、`TM_SEND_RESULT`。

`TM_SEND_RESULT` 至少带：direction、method/status、buffer role、branch、`is_retr`、provenance、transport、return code 和 buffer digest。`ret >= 0` 只能命名为 `local_send_accepted`；若论文主张对端实际收到，另用 pcap/peer-RX 证据确认。环境丢包不能直接归咎 SUT。

### 4.4 Timer 与销毁

`TIMER_ARM_RESULT`、`TIMER_CANCEL_RESULT`、`TIMER_FIRE`、`WAIT_ARM_RESULT`、`WAIT_FIRE`、`TX_HASH_UNLINK`、`TX_DESTROY`。

raw timer payload 使用 `rb_role/rbtype/retr_enabled/retr_expire/fr_expire/delta/result`。adapter 只有在 profile mapping 已证明时，才把 raw timer 映射为 H/J/L；不能看到 `_set_fr_retr()` 就直接发 `timer_l_64t1_armed`。

### 4.5 CANCEL

`CANCEL_MATCH_RESULT`、`CANCEL_APPLIED`、`CANCEL_BRANCH_SET`、`BRANCH_CANCEL_DECISION`。200/487/CANCEL 是否发出统一由 `TM_SEND_RESULT` 证明。

## 5. 固定源码插桩位置

下表中的“后”指事实已提交后的第一处安全位置，不是函数入口。

| 位置 | raw fact | 精确要求 |
|---|---|---|
| `src/core/receive.c:313–359` | `RX_SIP_PARSED` | `parse_msg` 成功，相关 headers/Via 可安全使用；缺关键字段时记录 reject/invalid，而不是虚构 correlation |
| `src/core/receive.c:526` 及 error exits | `MSG_PROCESS_END` | 在 `free_sip_msg()` 前，带 normal/drop/error outcome，作为同步 macrostep closure |
| `src/modules/tm/t_lookup.c:663–693` | `TX_LOOKUP_RESULT` | 在 NOT_FOUND、E2E_ACK、FOUND、parse-error 各 return 分支分别发；`has_magic_cookie` 只是 payload guard |
| `src/modules/tm/t_lookup.c:1430–1462` | `TX_CREATE_ATTEMPT/COMMIT/READY` | attempt 在 `new_t` 前；commit 在 `new_t` 成功后；ready 在 `init_rb` 成功后，三者不能合并 |
| `src/modules/tm/t_hooks.h` callbacks | retransmission、ACK、response、destroy facts | 注册 `REQ_RETR_IN`、`ACK_NEG_IN`、`E2EACK_IN/RETR`、`RESPONSE_IN`、`E2ECANCEL_IN`、`REQUEST/RESPONSE_OUT/SENT`、`DESTROY`；callback 中不得分配内存或加 reply lock |
| benchmark route config 的 TM gate 后 | `TU_BOUNDARY_MARK` | 增加显式 `tafuzz_mark("after_tm_gate")`；固定 PFB route 应放在 retransmission gate 之后、应用分发之前。`receive.c` 的 route entry 不是 TU delivery |
| `src/modules/tm/t_reply.c:1912–1920` | `RESPONSE_DECISION_COMMIT` | `t_should_relay_response` 返回以后，记录 RPS decision、relay branch、status before/after |
| `src/modules/tm/t_reply.c:2060–2070` | proxied `UAS_REPLY_COMMIT` | buffer、rbtype、`uas.status` 和 relayed branch 已提交后 |
| `src/modules/tm/t_reply.c:_reply_light:487–510` | local `UAS_REPLY_COMMIT` | local response buffer/status 已有效后；不能只覆盖 `relay_reply` |
| `relay_reply:2114–2141`、`_reply_light:543–632`、`t_retransmit_reply:1689`、`cancel_branch:328–334` | `TM_SEND_RESULT` | 保存实际 send return；成功/失败都记录。固定源码的 retransmit path 在失败后仍可能调用 `RESPONSE_SENT` callback，因此 retransmit 必须以直接 return 为准 |
| `src/modules/tm/t_fwd.c:t_lookupOriginalT/e2e_cancel` | `CANCEL_MATCH_RESULT/CANCEL_APPLIED` | original match 返回后；`T_CANCELED` 真正写入后；CANCEL/INVITE 双 subject correlation |
| `src/modules/tm/t_cancel.c:231–338` | `BRANCH_CANCEL_DECISION` | 分开记录 no-provisional skip、forced send、build failure 和 actual send result |
| `src/modules/tm/timer.h:_set_fr_retr:200–220` | `TIMER_ARM_RESULT` | `timer_add` 返回后；成功仅在 `ret==0 && t_active==1` |
| `src/modules/tm/timer.h:stop_rb_timers` | `TIMER_CANCEL_RESULT` | 把宏改为可审计 inline helper，记录 `was_active`、delete flag 和 delete result |
| `src/modules/tm/timer.c:496–549` | `TIMER_FIRE` | 分开 CANCELLED_SKIP、FR_DUE、RETR_DUE；callback entry 不等于 timer expiry |
| `src/modules/tm/t_funcs.c:142–150` | `WAIT_ARM_RESULT` | `put_on_wait()` 只表示 wait timer arm/已有 timer，不表示销毁 |
| `src/modules/tm/timer.c:588–645` | `WAIT_FIRE/TX_HASH_UNLINK` | 分开 wait recycle、强制 unlink、ready-to-destroy |
| `src/modules/tm/h_table.c:123–165` | `TX_DESTROY` | 通过早期 return 检查后、真正释放前，或使用经核对的 `TMCB_DESTROY` |

现有 `instrumentation_hooks.csv` 只能作为旧候选锚点，不能直接生成 patch；其中很多行虽然“可解析”，却锚在函数入口或调用条件而不是提交点。

## 6. Profile 与能力隔离

必须拆成至少两个 profile，不能把 local UAS 与 stateful proxy 混成一个 oracle：

### 6.1 `PFB-COMPAT/KAM-PROXY-FAST`

- 保持 ProfuzzBench 的吞吐/覆盖配置和 timer-off patch。
- 只启用 parse、lookup、transaction、reply decision/commit、send、retransmission、ACK、CANCEL 和 route/TU macrostep 性质。
- 所有依赖 timer callback/expiry/destroy horizon 的性质为 `INAPPLICABLE_PROFILE`，不是 SATISFIED。
- 用于在线 prefix guidance 和高吞吐发现；长期 timer 不在每 testcase 等待。

### 6.2 `MITL-VALID/KAM-PROXY-TIMER`

- 恢复 main/slow timer process，冻结 route、peer、T1/T2/FR/wait 参数。
- 启动前 sentinel timer 必须观察到 ARM→FIRE。
- 仅用于隔离重放有希望的 seed、正式长期 timer verdict 和漏洞确认。
- 所有 baseline 重放使用相同构建、collector、horizon 和 oracle。

### 6.3 `MITL-VALID/KAM-UAS`

- 使用最小、本地 UAS route，显式标记 TU boundary，并由 harness 控制早期/最终应答与延迟。
- 用于 auto-100、本地 3xx–6xx、ACK/CANCEL 等角色明确的性质。
- 不把 proxy 分支选择、downstream response 策略混入本地 UAS 结论。

`CAPABILITY_SNAPSHOT` 至少包含 timer driver、clock、route profile、auto-100、relay-100、send hook、TU marker、schema/hook hash 和配置 hash。

## 7. 现有 20 条性质的处理结论

“宏步”指当前消息从接收到 `MSG_PROCESS_END` 的同步执行，不是人为 2 ms。

| ID | 处理 | 新义务起点与关键事实 |
|---|---|---|
| 001 | 重写后首批 | lookup NOT_FOUND 后的 create attempt -> `TX_CREATE_COMMIT(INVITE)`；TU delivery 单列，不与 Proceeding 捆绑 |
| 002 | UAS profile 后启用 | `TX_READY(INVITE) && cfg_auto100 && harness_delays_tu` -> 200 ms 内 `SEND_OK(100)` 或更早 TU response；删除预测未来的 trigger |
| 003 | peer emulator 后启用 | 101–199 被选择 relay -> 同 reply state commit + actual send |
| 004 | peer emulator 后启用 | 独立 shadow matcher 证明 retransmission candidate，且 stored provisional 已知 -> cached buffer actual retransmit；同时禁止再次越过 TU gate |
| 005 | 首批，先拆角色 | local/proxy 已选择 300–699 -> status commit、actual same-response send、timer arm 分别检查 |
| 006 | 暂停正式 verdict | non-2xx send + proven H-equivalent arm 后，直到 ACK 或对应 generation fire 前禁止真实 unlink/destroy；需 timer/destroy/full horizon |
| 007 | 首批 | negative-final retention 中 ACK match -> ACK absorb + timer cancel/release/wait；同时检查未越过 TU gate |
| 008 | 禁用待证 | 固定源码没有可证明的 RFC6026 Accepted/Timer L mapping，不能由 generic timer arm 冒充 |
| 009 | 禁用待证 | 同上；若将来保留，只能先定义并证明 Kamailio accepted-equivalent profile |
| 010 | 禁用待证 | 同上；还必须区分 local UAS ACK 与 proxy e2e ACK/TU delivery |
| 011 | 重写后首批 | eligible non-INVITE NOT_FOUND -> transaction commit；TU delivery 单列 |
| 012 | peer/TU marker 后启用 | shadow+lookup 证明 live retransmission -> 禁止该 message 越过 TM gate或新建事务 |
| 013 | peer emulator 后启用 | non-INVITE 101–199 被选择 -> status commit + actual send |
| 014 | 首批，先 local UAS | final response input/selection -> final commit + actual send + wait arm 分别检查 |
| 015 | 首批 | shadow+lookup 证明 Completed retransmission 且 cached final 已知 -> actual cached retransmit |
| 016 | 首批且双向 | 独立 shadow matcher `expected_match` 与真实 lookup 对照；补 `expected_no_match -> NOT_FOUND`，消除循环自证 |
| 017 | peer/CANCEL profile 后启用 | original match 成功 -> CANCEL transaction 的 actual 200 send |
| 018 | 暂停并拆角色 | local UAS 可检查 actual 487；proxy 应检查 downstream CANCEL/最终响应链，不能统一要求 2 ms 487 |
| 019 | 暂停待重写 | branch open 起，收到 provisional 前禁止 downstream CANCEL；直到 provisional/final/branch close，不是只禁 2 ms；force mode 单列 |
| 020 | peer emulator 后启用 | matched downstream 100 的处理 episode 内，禁止同 provenance 的 upstream actual 100 send；`relay_100=1` profile 不适用 |

建议第一批只实现 001/011（拆分后）、005/014（local profile）、007、015、016。事件管线稳定后再加入 003/004/012/013/017/020。002、006、018、019 在专门 profile 完成后启用；008–010 在当前 fixed implementation 中禁用。

## 8. 三值 verdict、闭包和 drop

正式 verdict 仅为：

```text
SATISFIED
VIOLATED
UNKNOWN
```

独立 eligibility：

```text
ENABLED
INAPPLICABLE_PROFILE
DISABLED_PENDING_REVIEW
NOT_EXERCISED
```

UNKNOWN reason bitset：`EVENT_LOSS`、`CLOCK_INVALID`、`TIMESTAMP_BOUNDARY`、`AMBIGUOUS_ORDER`、`CORRELATION_AMBIGUOUS`、`CAPABILITY_FAILED`、`HORIZON_OPEN`、`PRODUCER_DIED`、`SUT_CRASHED`、`ORACLE_RESOURCE_LIMIT`。

规则：

- ring full 时 producer 不阻塞；递增 dropped counter、消耗 sequence 并设置 event-class mask。
- 初版只要 drop class 与性质 required hook mask 相交，该性质整次 run 为 `UNKNOWN_EVENT_LOSS`。
- `RUN_END` 不自动关闭 bounded eventuality。必须观察 supersession，或 watchdog time 已超过 trigger+deadline，且所有 producer watermark 已 drain。
- SUT crash 单独报告；crash 后未关闭的 obligation 为 UNKNOWN，不能同时算 MITL violation。
- 每次 run 输出 `eligible_stimuli_count`、`trigger_count`、`closed_count`、`violation_count`、`drop_count` 和 capability snapshot。

## 9. 与 fuzzer 的接口

形式 oracle 与 guidance 分离。sidecar 在线输出：

```text
run_id
property_id
instance_id
prefix_watermark
verdict
taint_reason
optimistic_existential_cost
predicted_observation_class
actionability
goal_probability
confidence
recommended_fuzzer_action_id
```

`predicted_observation_class` 可以是内部事件；`recommended_fuzzer_action_id` 必须是 fuzzer/harness 实际能执行的动作：mutate、send、wait-until、drop、delay、reorder、peer-response、reset。

每条边标注控制类别：

- `DIRECT`：报文字段、报文序列、发送时机。
- `PEER_HARNESS`：受控下游/上游响应。
- `SCHEDULER_HARNESS`：delay/drop/reorder/virtual-time 或明确 wait。
- `INDIRECT`：内部状态，可由前序输入提高到达概率。
- `AUTONOMOUS`：timer/GC，仅可等待或先建立 enabling state。
- `IMPOSSIBLE_PROFILE`：当前配置不可发生。

现有 PTA `optimistic_existential_cost` 只表示逻辑自动机中存在见证，不保证程序实际走该路径。动作选择层需要加入 empirical reachability，例如对不可控边使用 `-log P(observation | state, action)` 惩罚；每观察一个真实事件就滚动重规划。timer driver 缺失时不得推荐 wait。正式 verdict 永远不依赖 cost 或概率。

## 10. 实施文件与顺序

建议新增：

```text
Kamailio patch tree
  src/core/tafuzz_event.h            # 64-byte ABI、event ids、no-op macro
  src/core/tafuzz_ring.c/.h          # pre-fork registry、per-process ring
  src/modules/tafuzz_trace/          # callback 注册、route marker/config
  narrow patches in receive.c and tm sources

TAFuzz
  adapter/kamailio/schema.yaml
  adapter/kamailio/ap_rules.yaml
  adapter/kamailio/capabilities.yaml
  adapter/kamailio/correlator.*
  adapter/kamailio/sidecar.*
  adapter/kamailio/golden_traces/
```

执行顺序：

1. 冻结 raw schema、AP rules、profile、required capabilities、supersession 和 closure 表。
2. 先实现 ABI/ring/sidecar/drop/watermark/run epoch，不接 Kamailio。
3. 接 RX、MSG_END、lookup、create、reply commit、send return，完成首批非 timer golden trace。
4. 实现 correlation、shadow matcher、per-generation projection 和三值 validity gate。
5. 增加 route/TU marker、ACK/retransmission/CANCEL callbacks。
6. 增加 timer arm/cancel/fire、wait/unlink/destroy。
7. 建立 PFB-COMPAT 与 MITL-VALID calibrator；长期 seed 隔离重放。
8. 离线 oracle、语义透明和性能 pilot 通过后，再接在线 PTA guidance。

## 11. 验收门

| 层 | 必须通过的门 |
|---|---|
| Compile-off | 关闭 `TAFUZZ_EVENTS` 时 emit path 为零；与原 binary 的 exec/s 无统计显著差异 |
| Hot emit | CPU pinning 下单事件 P99 不高于 1 us；无 heap、format、global lock、每事件 syscall |
| Throughput | instrumentation-only median exec/s 至少为 baseline 97%；bootstrap 95% CI 下界不低于 95% |
| Burst/drop | 2 倍实测 P99 event rate 持续 60 s，formal profile relevant drop 为 0 |
| Correlation | 并发相同 Call-ID/CSeq、重传、pointer reuse、timer re-arm generation 不串实例 |
| Time | clock 无回退；deadline B-1/B/B+1 ms 边界与不确定性政策一致 |
| Capability | timer-off 必须拒绝 timer verdict；MITL-VALID sentinel ARM→FIRE 必须通过 |
| Drop semantics | 极小 ring 注入 drop 后相关性质必须 UNKNOWN，不能 SATISFIED |
| Transparency | 固定 replay corpus 的 wire output、transaction decision、crash 分类与未插桩构建一致 |
| Adapter | raw→AP golden traces覆盖正例、反例、supersession、same-time、watchdog、producer death |
| Guidance | 完整 prefix guidance P95 不高于 1 ms、P99 不高于 5 ms；超限切异步/batch |

## 12. 当前 artifact 的处理

- `mitl_property_catalog.*` 保留为规范候选和历史验证输入，20 条继续保持 `PENDING`。
- `instrumentation_hooks.csv` 标为 pre-audit candidate，不作为 patch generator 输入。
- `atomic_proposition_map.yaml` 当前还存在未加引号冒号导致的 YAML 解析错误，并混有上述复合 AP；不能只修语法后就投入实现，必须按本蓝图重建 versioned AP registry。
- 现有 synthetic positive/negative timed word 只能证明公式工具链能运行，不能证明真实 hook、correlation、timing 或 Kamailio 合规。

只有完成 source mapping、raw trace 人工对照、capability calibration、drop/closure 门和 isolated replay 后，性质才可从 `PENDING` 提升为正式 runtime oracle。
