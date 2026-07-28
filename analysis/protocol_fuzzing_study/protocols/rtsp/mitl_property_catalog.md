# RTSP MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：1
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## RTSP-SESSION-01 — LIVE555 65-second session-liveness generation is not reclaimed early

- 性质：在锁定 LIVE555 的默认 profile 中，一个 client-session liveness task generation 以 65 秒重新 arm 后，与该 task-token generation 相关的 inactivity reclamation callback 在 65000 ms 前不得进入。RFC 2326 只允许服务端在声明的无活动间隔后选择回收，本性质不要求届时必须回收。
- 规范：[RFC 2326 RFC 2326 (April 1998, RTSP/1.0) §12.37; Appendix A.2](https://www.rfc-editor.org/rfc/rfc2326.html#section-12.37)；强度 `CONDITIONAL MAY instantiated as IMPLEMENTATION_PROFILE no-early consistency`；时间 `65000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“The server uses it to indicate to the client how long the server is prepared to wait”
- 数学 MITL：`G (rtsp_liveness_generation_armed_65 -> G [0,65000) (!rtsp_inactivity_reclaim_callback_entered))`
- MightyPPL（finite weak outer global）：`G* (rtsp_liveness_generation_armed_65 -> G [0,65000) (!rtsp_inactivity_reclaim_callback_entered))`
- AP：`rtsp_liveness_generation_armed_65, rtsp_inactivity_reclaim_callback_entered`
- AP 定义：{"rtsp_liveness_generation_armed_65": "After GenericMediaServer::ClientSession::noteLiveness returns from rescheduleDelayedTask for an established ClientSession whose successful SETUP response already declared timeout=65, the new non-null fLivenessCheckTask token defines this generation; the constructor's pre-response arm is excluded.", "rtsp_inactivity_reclaim_callback_entered": "GenericMediaServer::ClientSession::livenessTimeoutTask is entered for the exact captured fLivenessCheckTask generation, immediately before deletion of that ClientSession."}
- Correlation：GenericMediaServer::ClientSession pointer + fOurSessionId + captured fLivenessCheckTask token generation; pointer, session ID, and token remain event fields and never enter AP names
- 投影：after a successful SETUP response has established the Session and declared timeout=65, spawn one projection after each later liveness-task reschedule; project only a callback carrying the same task-token generation, and finalize the old projection when reschedule or destruction supersedes that token
- 监控实例：one correlated ClientSession task-token generation per finite timed word; the trigger occurs exactly once, every reschedule creates a new monitor instance, and a callback is projected only to its matching generation
- 源码：[rgaufman/live555@ceeb4f462709 `liveMedia/GenericMediaServer.cpp:283-297;303-312`](https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/GenericMediaServer.cpp#L283-L297)；符号 `GenericMediaServer::ClientSession::noteLiveness / GenericMediaServer::ClientSession::livenessTimeoutTask`。
- 主源码映射 AP：`["rtsp_liveness_generation_armed_65", "rtsp_inactivity_reclaim_callback_entered"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "65-second server profile declaration", "path": "liveMedia/include/RTSPServer.hh", "symbol": "reclamationSeconds", "lines": "31-41", "atomic_propositions": ["rtsp_liveness_generation_armed_65"], "url": "https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/include/RTSPServer.hh#L31-L41"}, {"role": "Session timeout advertisement", "path": "liveMedia/RTSPServer.cpp", "symbol": "RTSPServer::RTSPClientSession::handleCmd_SETUP", "lines": "1416-1499", "atomic_propositions": ["rtsp_liveness_generation_armed_65"], "url": "https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L1416-L1499"}, {"role": "valid Session request liveness refresh", "path": "liveMedia/RTSPServer.cpp", "symbol": "RTSPServer::RTSPClientConnection::handleRequestBytes", "lines": "726-733", "atomic_propositions": ["rtsp_liveness_generation_armed_65"], "url": "https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/liveMedia/RTSPServer.cpp#L726-L733"}, {"role": "task reschedule", "path": "UsageEnvironment/UsageEnvironment.cpp", "symbol": "TaskScheduler::rescheduleDelayedTask", "lines": "52-57", "atomic_propositions": ["rtsp_liveness_generation_armed_65"], "url": "https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/UsageEnvironment/UsageEnvironment.cpp#L52-L57"}, {"role": "delayed-task queue insertion", "path": "BasicUsageEnvironment/BasicTaskScheduler0.cpp", "symbol": "BasicTaskScheduler0::scheduleDelayedTask", "lines": "59-68", "atomic_propositions": ["rtsp_liveness_generation_armed_65"], "url": "https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/BasicUsageEnvironment/BasicTaskScheduler0.cpp#L59-L68"}, {"role": "due delayed-task dispatch", "path": "BasicUsageEnvironment/DelayQueue.cpp", "symbol": "DelayQueue::handleAlarm", "lines": "179-189", "atomic_propositions": ["rtsp_inactivity_reclaim_callback_entered"], "url": "https://github.com/rgaufman/live555/blob/ceeb4f462709695b145852de309d8cd25e2dca01/BasicUsageEnvironment/DelayQueue.cpp#L179-L189"}]`
- Hook：Track that the ClientSession has completed a successful SETUP response declaring timeout=65; on a later noteLiveness call, emit the trigger after rescheduleDelayedTask returns and capture the new fLivenessCheckTask token. Emit the callback AP at livenessTimeoutTask entry before delete, only for that captured token generation. Do not synthesize a deadline from callback dispatch time.
- 正例 timed word：`[{"time": 0, "props": ["rtsp_liveness_generation_armed_65"]}, {"time": 65000, "props": ["rtsp_inactivity_reclaim_callback_entered"]}, {"time": 65001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["rtsp_liveness_generation_armed_65"]}, {"time": 64999, "props": ["rtsp_inactivity_reclaim_callback_entered"]}, {"time": 65001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`ROOT_REVIEWED_WITH_CAVEAT`；Root review admits only the no-early implementation-profile invariant. RFC 2326 makes inactivity teardown optional, and scheduler callback dispatch is not treated as a must-fire deadline.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This is not a universal RTSP 65-second constant and not an eventual-reclamation property. The constructor's pre-SETUP-response arm and non-inactivity teardown paths are outside the property. LIVE555 DelayQueue uses gettimeofday; adapter timestamps must use a compatible nondecreasing basis or explicitly flag forward wall-clock jumps that can appear early relative to an independent monotonic clock.
