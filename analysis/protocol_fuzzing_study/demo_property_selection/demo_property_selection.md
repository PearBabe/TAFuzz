# ProfuzzBench 首个 MITL demo 性质选择（更正版）

## 结论

撤回上一版把 **`SIP-TX-20` / Kamailio Timer C** 作为首个“真实 bug/真实违反”demo 的建议。

原因很简单：ProfuzzBench 中 `fr_inv_timer=120000` 是 benchmark 配置，它可以证明“这个 profile 不满足 RFC 3261 Timer C strict > 3 minutes 的配置合规要求”，但不能把 fuzzing 输入触发的 crash 或漏洞说成“实现发现了协议 bug”。如果同一个输入只因为我们换配置就从 `NEGATIVE` 变成非违反，那它首先是 `CONFIG_CONFORMANCE_CHECK`，不是 fuzzing oracle。

严格限定在当前 80 条性质、ProfuzzBench 原始 subject、真实运行事件和“demo 的违反必须来自 SUT 实际事件序列”这几个条件下，首个 demo 选择：

**`RTSP-SESSION-01` / Live555 65-second session-liveness no-early callback**

这不是因为它一定会找出 bug；恰恰相反，它是更诚实的 demo：正常情况下应当看到 `POSITIVE` 或未违反，只有实际 callback 在 65000 ms 之前进入，才报告 `NEGATIVE`。

## 新的 demo 选择门槛

这次更正后，demo 不能再用“固定配置短于规范常数”冒充 fuzzing 发现。一个性质进入首个 demo，必须同时满足：

- 协议在 ProfuzzBench subject 中，且性质映射到同一个 pinned SUT。
- AP 是真实运行事件谓词，不是人为注入的短 deadline 或 synthetic callback。
- 违反必须由 replay/fuzz 输入驱动出的真实事件序列触发。
- 只修改配置就能翻转 verdict 的条目，降级为配置合规检查，不作为真实 bug demo。
- 如果 benchmark patch 关闭了 timer callback 进程，则不能声称测试了 callback/expiry runtime 语义。
- 负例 timed word 可以用于 monitor 语义验证，但不能当作真实 SUT bug 证据。

## 80 条性质重新筛选

ProfuzzBench 固定提交 `8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074` 的 subject 包含 DAAP、DICOM、DNS、DTLS、FTP、RTSP、SIP、SMTP、SSH、TLS。现有 80 条目录没有 DAAP 性质；与其余 subject 协议重合的已收录性质共有 36 条：DICOM 1、DTLS 3、RTSP 1、SIP 23、SMTP 7、SSH 1。DNS、FTP、TLS 在本轮真实性门下均为 0 条。

继续加上“同 SUT、同角色、真实 runtime demo”门槛后：

- DTLS 3 条映射 OpenSSL，但 ProfuzzBench SUT 是 TinyDTLS，排除。
- SIP 23 条中，16 条映射 PJSIP、6 条映射 Doubango；它们不是 ProfuzzBench 被测的 Kamailio。唯一 Kamailio 条目 `SIP-TX-20` 降级为配置合规检查。
- DICOM `DICOM-ARTIM-01` 目录映射 DCMTK `storescp` 30 秒 acceptor profile；若 ProfuzzBench harness 启动的不是同一 executable/同一 timeout profile，需要先重映射，不能直接作为首个 demo。
- SMTP 6 条是 outbound client 路径，ProfuzzBench Exim fuzz 的是 inbound server；`SMTP-TIMEOUT-07` 可达但真实阈值 300000 ms。
- SSH `SSH-REKEY-01` 映射 OpenSSH，但需要非默认一小时 rekey profile，不适合首个短 demo。
- RTSP `RTSP-SESSION-01` 映射 ProfuzzBench Live555，AP 是真实 task arm 与 callback 事件，ProfuzzBench patch 未显示禁用该 liveness task 路径，因此保留。

评分与降级原因见 `profuzzbench_demo_candidate_ranking.csv`。

## 为什么现在选 RTSP-SESSION-01

性质：

```text
G* (rtsp_liveness_generation_armed_65 ->
    G [0,65000) (!rtsp_inactivity_reclaim_callback_entered))
```

它表达的是：在锁定 Live555 `timeout=65` profile 中，某个 client-session liveness task generation 被真实 re-arm 后，同一个 task-token generation 的 inactivity callback 不得在 65000 ms 之前进入。

AP 是真实事件：

- `rtsp_liveness_generation_armed_65`：成功 SETUP 已声明 `timeout=65` 后，后续 `noteLiveness()` 调用完成 `rescheduleDelayedTask()`，捕获新的 `fLivenessCheckTask` token generation。
- `rtsp_inactivity_reclaim_callback_entered`：同一个 token generation 的 `livenessTimeoutTask()` 实际进入，且在删除 session 前发出。

这里没有把“应该 65 秒”伪造成已经发生的 callback，也没有缩短 timer。真实 demo 应该等待真实 callback；若 callback 在 65000 ms 之前出现才是违反。

## demo 输入流程

最小流程：

1. 启动 ProfuzzBench Live555 subject。
2. 用真实 RTSP seed 建立 session，至少走到 successful `SETUP`，响应中声明 `timeout=65`。
3. 发送一个合法的带 Session 的后续请求，触发 `noteLiveness()` 重新 arm 当前 session 的 liveness task。
4. hook 在 `rescheduleDelayedTask()` 返回后记录 `rtsp_liveness_generation_armed_65`，并保存 task token generation。
5. 让 session 空闲，等待真实 scheduler callback。
6. 如果 `livenessTimeoutTask()` 对同一 token generation 在 `<65000 ms` 进入，monitor 给出 `NEGATIVE`；如果在 `65000 ms` 或之后进入，则该 no-early 性质不违反。

这个 demo 的代价是慢：一次真实观察约 65 秒。它适合做 end-to-end correctness smoke，不适合直接作为高吞吐 fuzz campaign 的默认内循环。

## SIP 应该怎么处理

`SIP-TX-20` 仍然有研究价值，但名称要摆正：

- 它可以做 `CONFIG_CONFORMANCE_CHECK`：ProfuzzBench Kamailio profile 的 Timer C 配置与 RFC 3261 strict `>180000 ms` 不一致。
- 它不能作为“fuzz 输入触发的漏洞 demo”。
- 由于 ProfuzzBench Kamailio patch 关闭 main/slow timer process，原始 PFB profile 也不能测试真实 timer callback/expiry 行为。

如果目标明确是“测试 SIP timer runtime”，正确路线不是继续用 `fr_inv_timer=120000` 当负例，而是切到独立 Kamailio MITL-VALID reference profile：恢复 timer 进程，固定 route/peer，选择 `SIP-KAM-006` 这类 Timer H/J runtime 性质，发送非 2xx final response 后 withheld ACK，观察真实 timer callback 与 transaction termination。这个性质不属于原 80 条 ProfuzzBench-strict demo 候选，需要作为 Kamailio/SIP 独立 reanalysis 的下一阶段 demo。

## 本轮验证状态

已验证 RTSP 公式的机器语义：

- build-only：PASS。
- 正例 trace：callback 在 `65000 ms`，verdict `POSITIVE`。
- 反例 trace：callback 在 `64999 ms`，verdict `NEGATIVE`。

这些 trace 只验证 monitor 语义。真实 demo 必须由 Live555 hook 产生同名事件后才能报告 bug/violation。
