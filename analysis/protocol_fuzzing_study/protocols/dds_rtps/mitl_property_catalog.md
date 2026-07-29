# DDS/RTPS MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：5
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## DDS-WRITE-01 — Blocked reliable write returns within 100 ms

- 性质：使用 DDS 默认 max_blocking_time=100 ms 的 RELIABLE DataWriter 在资源压力下进入阻塞后，write 应在 100 ms 内以成功、TIMEOUT 或规范允许的 OUT_OF_RESOURCES 返回。
- 规范：[OMG Data Distribution Service DDS 1.4 formal/2015-04-10 §2.2.2.4.2.11; 2.2.3.14](https://www.omg.org/spec/DDS/1.4/PDF)；强度 `NORMATIVE MAXIMUM`；时间 `100 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“The default max_blocking_time=100ms”
- 数学 MITL：`G (reliable_write_resource_wait_started_default -> F [0,100] (write_returned_from_blocking))`
- MightyPPL（finite weak outer global）：`G* (reliable_write_resource_wait_started_default -> F [0,100] (write_returned_from_blocking))`
- AP：`reliable_write_resource_wait_started_default, write_returned_from_blocking`
- AP 定义：{"reliable_write_resource_wait_started_default": "A RELIABLE DataWriter with max_blocking_time=100 ms reaches DataWriterHistory::prepare_change and is about to wait_for_acknowledgement because resource/history space is unavailable.", "write_returned_from_blocking": "The correlated write returns OK, TIMEOUT, or the explicitly permitted OUT_OF_RESOURCES result."}
- Correlation：DataWriter entity GUID + calling thread operation sequence + instance handle as a field
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one synchronous write operation and exactly one actual resource-wait episode; precondition/serialization work before waiting is excluded, and the API return ends it.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eProsima/Fast-DDS@949401694422 `src/cpp/fastdds/publisher/DataWriterHistory.cpp:148-234`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/fastdds/publisher/DataWriterHistory.cpp#L148-L234)；符号 `DataWriterHistory::prepare_change`。
- 主源码映射 AP：`["reliable_write_resource_wait_started_default"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "absolute max-blocking deadline and API return", "path": "src/cpp/fastdds/publisher/DataWriterImpl.cpp", "symbol": "DataWriterImpl::perform_create_new_change", "lines": "1003-1107", "atomic_propositions": ["reliable_write_resource_wait_started_default", "write_returned_from_blocking"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/fastdds/publisher/DataWriterImpl.cpp#L1003-L1107"}, {"role": "templated history caller return", "path": "src/cpp/fastdds/publisher/DataWriterHistory.hpp", "symbol": "add_pub_change_with_commit_hook", "lines": "142-170", "atomic_propositions": ["write_returned_from_blocking"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/fastdds/publisher/DataWriterHistory.hpp#L142-L170"}]`
- Hook：Emit trigger immediately before wait_for_acknowledgement at lines 230-234 after confirming the 100 ms QoS/deadline snapshot. Emit the correlated API return at DataWriterImpl; serialization/precondition time before the resource wait is not mislabeled as waiting time.
- 正例 timed word：`[{"time": 0, "props": ["reliable_write_resource_wait_started_default"]}, {"time": 100, "props": ["write_returned_from_blocking"]}, {"time": 101, "props": []}]`
- 附加正例/合法 supersession：`{"immediate_out_of_resources": [{"time": 0, "props": ["reliable_write_resource_wait_started_default"]}, {"time": 1, "props": ["write_returned_from_blocking"]}, {"time": 2, "props": []}]}`
- 反例 timed word：`[{"time": 0, "props": ["reliable_write_resource_wait_started_default"]}, {"time": 101, "props": []}]`
- 附加反例：`{"negative_late_or_missing": [{"time": 0, "props": ["reliable_write_resource_wait_started_default"]}, {"time": 101, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: the primary source now proves the real wait predicate; total write execution is no longer conflated with resource waiting, and caller/deadline/return hooks plus immediate OUT_OF_RESOURCES coverage were added.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The standard permits immediate OUT_OF_RESOURCES in hopeless-resource cases. The formula constrains only an observed resource wait and does not treat total serialization/function execution as max_blocking_time.

## RTPS-DISC-01 — Periodic SPDP announcement interval is 30 seconds

- 性质：完成启动期 directed announcements 后，在 SPDP reference-default profile 中，相邻周期性 multicast announcement 不得早于 30000 ms，且下一次应在 30000 ms 发送。
- 规范：[OMG DDSI-RTPS 2.5 formal/2022-04-01 §9.6.2.4](https://www.omg.org/spec/DDSI-RTPS/2.5/PDF)；强度 `SPECIFIED DEFAULT`；时间 `30000 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“The default rate by which SPDP periodic announcements are sent equals 30 seconds”
- 数学 MITL：`G (periodic_spdp_generation_started_30000 -> (G [0,30000) (!next_periodic_spdp_announcement_sent) && F [0,30000] (next_periodic_spdp_announcement_sent || spdp_period_generation_superseded || local_participant_stopped)))`
- MightyPPL（finite weak outer global）：`G* (periodic_spdp_generation_started_30000 -> (G [0,30000) (!next_periodic_spdp_announcement_sent) && F [0,30000] (next_periodic_spdp_announcement_sent || spdp_period_generation_superseded || local_participant_stopped)))`
- AP：`periodic_spdp_generation_started_30000, next_periodic_spdp_announcement_sent, spdp_period_generation_superseded, local_participant_stopped`
- AP 定义：{"periodic_spdp_generation_started_30000": "A steady-state non-directed SPDP announcement is sent and the next periodic generation is armed with resendPeriod=30 s.", "next_periodic_spdp_announcement_sent": "The next steady-state non-directed periodic SPDP announcement is actually handed to announceParticipantState(false); logical deadline and callback/send time are retained.", "spdp_period_generation_superseded": "A configuration/reset operation replaces the scheduled periodic generation before its deadline.", "local_participant_stopped": "The local DomainParticipant is disabled/deleted before the next period."}
- Correlation：domainId + local participant GUID prefix; directed destination GUIDs remain fields and are filtered out
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one steady-state periodic generation for one local participant; exclude startup bursts/directed sends and explicitly close on reconfiguration or participant stop.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eProsima/Fast-DDS@949401694422 `src/cpp/rtps/builtin/discovery/participant/PDP.cpp:1534-1546`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/builtin/discovery/participant/PDP.cpp#L1534-L1546)；符号 `PDP::set_next_announcement_interval`。
- 主源码映射 AP：`["periodic_spdp_generation_started_30000"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "periodic SPDP announcement action", "path": "src/cpp/rtps/builtin/discovery/participant/PDP.cpp", "symbol": "PDP::announceParticipantState", "lines": "576-692", "atomic_propositions": ["next_periodic_spdp_announcement_sent"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/builtin/discovery/participant/PDP.cpp#L576-L692"}, {"role": "periodic announcement generation reset", "path": "src/cpp/rtps/builtin/discovery/participant/PDP.cpp", "symbol": "PDP::resetParticipantAnnouncement", "lines": "702-708", "atomic_propositions": ["spdp_period_generation_superseded"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/builtin/discovery/participant/PDP.cpp#L702-L708"}, {"role": "participant stop and timer cancellation", "path": "src/cpp/rtps/builtin/discovery/participant/PDP.cpp", "symbol": "PDP::stopParticipantAnnouncement / PDP::disable", "lines": "558-574;694-700", "atomic_propositions": ["local_participant_stopped"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/builtin/discovery/participant/PDP.cpp#L558-L574"}]`
- Hook：After startup announcements are exhausted and resendPeriod=30 s is verified, each observed announceParticipantState(false) closes the old generation and arms a new one. Stamp an observed next send with the stored logical deadline; retain actual callback time separately.
- 正例 timed word：`[{"time": 0, "props": ["periodic_spdp_generation_started_30000"]}, {"time": 30000, "props": ["next_periodic_spdp_announcement_sent"]}, {"time": 30001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["periodic_spdp_generation_started_30000"]}, {"time": 29999, "props": ["next_periodic_spdp_announcement_sent"]}, {"time": 30001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["periodic_spdp_generation_started_30000"]}, {"time": 30001, "props": ["next_periodic_spdp_announcement_sent"]}, {"time": 30002, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["periodic_spdp_generation_started_30000"]}, {"time": 30001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: the main hook now covers the actual periodic send callback, interval configuration is a second fixed hook, and early/late plus supersession are explicit.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Fast-DDS v3.3.0 stock announcement period is 3 s. The benchmark explicitly selects the RTPS 30 s reference profile; actual callback delay remains diagnostic rather than an undocumented tolerance.

## RTPS-DISC-02 — Remote participant is not lease-removed before the 100-second default lease

- 性质：远端 SPDP 未携带 lease-duration PID、使用独立 participant 100000 ms 默认租约时，在该 lease generation 到期前不得仅因 lease expiry 删除；规范不要求恰在 100000 ms 完成物理删除。
- 规范：[OMG DDSI-RTPS 2.5 formal/2022-04-01 §8.5.5.2; 9.6.3 Table 9.18](https://www.omg.org/spec/DDSI-RTPS/2.5/PDF)；强度 `DEFAULT LEASE / NO-EARLY SAFETY`；时间 `100000 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“SPDPdiscoveredParticipantData::leaseDuration {100, 0}”
- 数学 MITL：`G (remote_participant_default_lease_started -> G [0,100000) (!remote_participant_removed_due_to_lease || remote_spdp_refresh_supersedes_lease || remote_lease_generation_cancelled))`
- MightyPPL（finite weak outer global）：`G* (remote_participant_default_lease_started -> G [0,100000) (!remote_participant_removed_due_to_lease || remote_spdp_refresh_supersedes_lease || remote_lease_generation_cancelled))`
- AP：`remote_participant_default_lease_started, remote_participant_removed_due_to_lease, remote_spdp_refresh_supersedes_lease, remote_lease_generation_cancelled`
- AP 定义：{"remote_participant_default_lease_started": "A valid SPDP sample without PID_PARTICIPANT_LEASE_DURATION creates/renews an independent, non-privileged-dependent remote participant using 100 s.", "remote_participant_removed_due_to_lease": "Lease expiration, rather than explicit disposal or another cause, invokes deletion/reconfiguration for that proxy participant.", "remote_spdp_refresh_supersedes_lease": "A newer valid SPDP sample closes this lease generation and starts a separately projected 100 s generation.", "remote_lease_generation_cancelled": "A correlated SPDP dispose/unregister reaches handle_spdp_dead and deletes the proxy participant before lease expiry; domain shutdown is recorded only through its corresponding proxy-deletion lifecycle."}
- Correlation：domain + remote participant GUID prefix + SPDP sequence number; GUID is a field
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one lease generation for one independent remote participant; SPDP refresh emits supersession and opens another word, while explicit disposal emits cancellation.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eclipse-cyclonedds/cyclonedds@2cdd114cbd18 `src/core/ddsi/src/q_lease.c:218-292`](https://github.com/eclipse-cyclonedds/cyclonedds/blob/2cdd114cbd18340c606573b4cc8dc20cc161ec5a/src/core/ddsi/src/q_lease.c#L218-L292)；符号 `check_and_handle_lease_expiration`。
- 主源码映射 AP：`["remote_participant_removed_due_to_lease"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "default lease creation and SPDP refresh", "path": "src/core/ddsi/src/q_ddsi_discovery.c", "symbol": "handle_spdp_alive", "lines": "723-981", "atomic_propositions": ["remote_participant_default_lease_started", "remote_spdp_refresh_supersedes_lease"], "url": "https://github.com/eclipse-cyclonedds/cyclonedds/blob/2cdd114cbd18340c606573b4cc8dc20cc161ec5a/src/core/ddsi/src/q_ddsi_discovery.c#L723-L981"}, {"role": "explicit SPDP dispose cancellation", "path": "src/core/ddsi/src/q_ddsi_discovery.c", "symbol": "handle_spdp_dead", "lines": "638-671", "atomic_propositions": ["remote_lease_generation_cancelled"], "url": "https://github.com/eclipse-cyclonedds/cyclonedds/blob/2cdd114cbd18340c606573b4cc8dc20cc161ec5a/src/core/ddsi/src/q_ddsi_discovery.c#L638-L671"}, {"role": "privileged participant lease exception", "path": "src/core/ddsi/src/q_lease.c", "symbol": "check_and_handle_lease_expiration", "lines": "247-281", "atomic_propositions": ["remote_participant_default_lease_started"], "url": "https://github.com/eclipse-cyclonedds/cyclonedds/blob/2cdd114cbd18340c606573b4cc8dc20cc161ec5a/src/core/ddsi/src/q_lease.c#L247-L281"}]`
- Hook：Emit start only after the omitted PID is defaulted to 100 s and privileged/dependency postponement is excluded. A refresh/cancel closes this word. Emit lease-removal cause immediately before ddsi_delete_proxy_participant_by_guid; do not require a callback at exactly 100 s.
- 正例 timed word：`[{"time": 0, "props": ["remote_participant_default_lease_started"]}, {"time": 100000, "props": []}, {"time": 100001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["remote_participant_default_lease_started"]}, {"time": 99999, "props": ["remote_participant_removed_due_to_lease"]}, {"time": 100001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: unsupported exact-removal liveness was removed; the card is now a cause-specific no-early safety property with refresh/cancel generation boundaries and fixed default/exception hooks.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This is deliberately safety-only: RTPS permits considering the participant gone after the lease but does not impose exact physical removal at 100 s. CycloneDDS privileged/dependency postponement cases are trigger-false and excluded.

## RTPS-REL-01 — Writer-wide ACKNACK response timer generation is due at 200 ms

- 性质：可靠 StatefulWriter 在显式 200 ms reference-default profile 中为 pending-reader set 启动一个 writer-wide nack-response timer generation；不得提前执行，并应在逻辑 deadline 执行，或由新 generation、unmatch/empty-set、writer stop 显式解除。
- 规范：[OMG DDSI-RTPS 2.5 formal/2022-04-01 §8.4.7.1; 8.4.9.2.11](https://www.omg.org/spec/DDSI-RTPS/2.5/PDF)；强度 `SPECIFIED DEFAULT`；时间 `200 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“nackResponseDelay.nanosec = 200 * 1000 * 1000; //200 milliseconds”
- 数学 MITL：`G (writer_nack_timer_generation_started_200 -> (G [0,200) (!nack_response_action_observed) && F [0,200] (nack_response_action_observed || nack_response_generation_superseded || rtps_pending_reader_set_empty || rtps_writer_stopped)))`
- MightyPPL（finite weak outer global）：`G* (writer_nack_timer_generation_started_200 -> (G [0,200) (!nack_response_action_observed) && F [0,200] (nack_response_action_observed || nack_response_generation_superseded || rtps_pending_reader_set_empty || rtps_writer_stopped)))`
- AP：`writer_nack_timer_generation_started_200, nack_response_action_observed, nack_response_generation_superseded, rtps_pending_reader_set_empty, rtps_writer_stopped`
- AP 定义：{"writer_nack_timer_generation_started_200": "A fresh ACKNACK makes the writer-wide pending-reader set non-empty and restart_timer arms nackResponseDelay=200 ms.", "nack_response_action_observed": "The corresponding TimedEvent callback is observed and perform_nack_response begins; the event is stamped with the stored logical deadline and also records actual callback time.", "nack_response_generation_superseded": "A newer qualifying ACKNACK restarts the same writer-wide timer; it closes this generation and starts a separately projected generation.", "rtps_pending_reader_set_empty": "All requested repairs disappear or relevant readers are unmatched before the deadline.", "rtps_writer_stopped": "The writer is disabled/deleted before the deadline."}
- Correlation：writer GUID + timer generation + pending reader GUID/count set; ACKNACK counts and sequence numbers remain fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one writer-wide timer generation, not one ReaderProxy. A newer restart atomically supersedes the old generation before opening the next word.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eProsima/Fast-DDS@949401694422 `src/cpp/rtps/writer/StatefulWriter.cpp:1921-1960`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L1921-L1960)；符号 `StatefulWriter::process_acknack`。
- 主源码映射 AP：`["writer_nack_timer_generation_started_200", "nack_response_generation_superseded", "rtps_pending_reader_set_empty"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "writer nack-response callback action", "path": "src/cpp/rtps/writer/StatefulWriter.cpp", "symbol": "StatefulWriter::perform_nack_response", "lines": "1880-1900", "atomic_propositions": ["nack_response_action_observed"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L1880-L1900"}, {"role": "TimedEvent callback binding", "path": "src/cpp/rtps/writer/StatefulWriter.cpp", "symbol": "StatefulWriter::init", "lines": "225-232", "atomic_propositions": ["nack_response_action_observed"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L225-L232"}, {"role": "reader unmatch can empty pending-reader set", "path": "src/cpp/rtps/writer/StatefulWriter.cpp", "symbol": "StatefulWriter::matched_reader_remove", "lines": "1211-1302", "atomic_propositions": ["rtps_pending_reader_set_empty"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L1211-L1302"}, {"role": "writer removal stops timer and reader proxies", "path": "src/cpp/rtps/writer/StatefulWriter.cpp", "symbol": "StatefulWriter::local_actions_on_writer_removed", "lines": "256-315", "atomic_propositions": ["rtps_writer_stopped"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/writer/StatefulWriter.cpp#L256-L315"}]`
- Hook：Require harness WriterTimes.nack_response_delay=200 ms. Emit trigger at restart_timer; a later restart first emits superseded. Emit the action only if the callback is observed, stamp it with the stored logical deadline, and retain actual callback time for overhead/jitter analysis.
- 正例 timed word：`[{"time": 0, "props": ["writer_nack_timer_generation_started_200"]}, {"time": 200, "props": ["nack_response_action_observed"]}, {"time": 201, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["writer_nack_timer_generation_started_200"]}, {"time": 199, "props": ["nack_response_action_observed"]}, {"time": 201, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["writer_nack_timer_generation_started_200"]}, {"time": 201, "props": ["nack_response_action_observed"]}, {"time": 202, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["writer_nack_timer_generation_started_200"]}, {"time": 201, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: correlation is writer-wide, restart/unmatch/stop are explicit, one timer generation is projected per word, and early plus late/missing callback oracles are present.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Fast-DDS v3.3.0 stock WriterTimes is 5 ms, not 200 ms. The benchmark explicitly configures 200 ms. The reference state transition and Fast-DDS restart-on-new-ACKNACK behavior are distinguished by timer-generation events.

## RTPS-REL-02 — HEARTBEAT response ACKNACK is sent after 500 ms

- 性质：可靠 StatefulReader 收到表明有缺失数据的 HEARTBEAT 后，在 reference-default profile 中不得于 500 ms 前发送 ACKNACK，并应在 500 ms 发送或匹配已解除。
- 规范：[OMG DDSI-RTPS 2.5 formal/2022-04-01 §8.4.10.1; 8.4.12.2.5](https://www.omg.org/spec/DDSI-RTPS/2.5/PDF)；强度 `SPECIFIED DEFAULT`；时间 `500 ms`（`NORMATIVE_DEFAULT`）。
- 规范短摘录：“heartbeatResponseDelay.nanosec = 500 * 1000 * 1000; // 500 milliseconds”
- 数学 MITL：`G (heartbeat_response_generation_started_500 -> (G [0,500) (!heartbeat_acknack_sent) && F [0,500] (heartbeat_acknack_sent || heartbeat_response_generation_superseded || rtps_writer_unmatched || rtps_reader_stopped)))`
- MightyPPL（finite weak outer global）：`G* (heartbeat_response_generation_started_500 -> (G [0,500) (!heartbeat_acknack_sent) && F [0,500] (heartbeat_acknack_sent || heartbeat_response_generation_superseded || rtps_writer_unmatched || rtps_reader_stopped)))`
- AP：`heartbeat_response_generation_started_500, heartbeat_acknack_sent, heartbeat_response_generation_superseded, rtps_writer_unmatched, rtps_reader_stopped`
- AP 定义：{"heartbeat_response_generation_started_500": "A fresh HEARTBEAT enters must_send_ack and restart_timer arms this WriterProxy generation with heartbeatResponseDelay=500 ms.", "heartbeat_acknack_sent": "The heartbeat-response callback is observed handing the correlated ACKNACK to the RTPS send path; logical deadline and actual callback/send time are both retained.", "heartbeat_response_generation_superseded": "A newer qualifying HEARTBEAT restarts/coalesces the WriterProxy timer and closes this generation before starting another projected word.", "rtps_writer_unmatched": "The WriterProxy is removed before response and discharges the window.", "rtps_reader_stopped": "The local reader is disabled/deleted before response."}
- Correlation：reader GUID + writer GUID + HEARTBEAT count; sequence-number set is a field
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project exactly one WriterProxy heartbeat timer generation; newer HEARTBEAT restart, unmatch, or reader stop closes it explicitly.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[eProsima/Fast-DDS@949401694422 `src/cpp/rtps/reader/WriterProxy.cpp:550-615`](https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/reader/WriterProxy.cpp#L550-L615)；符号 `WriterProxy::process_heartbeat`。
- 主源码映射 AP：`["heartbeat_response_generation_started_500", "heartbeat_response_generation_superseded"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "heartbeat-response ACKNACK handoff", "path": "src/cpp/rtps/reader/WriterProxy.cpp", "symbol": "WriterProxy::perform_heartbeat_response", "lines": "535-548", "atomic_propositions": ["heartbeat_acknack_sent"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/reader/WriterProxy.cpp#L535-L548"}, {"role": "remote writer unmatch", "path": "src/cpp/rtps/reader/StatefulReader.cpp", "symbol": "StatefulReader::matched_writer_remove", "lines": "381-482", "atomic_propositions": ["rtps_writer_unmatched"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/reader/StatefulReader.cpp#L381-L482"}, {"role": "WriterProxy timer cancellation", "path": "src/cpp/rtps/reader/WriterProxy.cpp", "symbol": "WriterProxy::stop", "lines": "170-187", "atomic_propositions": ["rtps_writer_unmatched", "rtps_reader_stopped"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/reader/WriterProxy.cpp#L170-L187"}, {"role": "local reader removal lifecycle", "path": "src/cpp/rtps/reader/BaseReader.cpp", "symbol": "BaseReader::local_actions_on_reader_removed", "lines": "109-112", "atomic_propositions": ["rtps_reader_stopped"], "url": "https://github.com/eProsima/Fast-DDS/blob/94940169442298e2736af79720ef05d89a1b2a7d/src/cpp/rtps/reader/BaseReader.cpp#L109-L112"}]`
- Hook：Set ReaderTimes.heartbeat_response_delay=500 ms; emit trigger at restart_timer. A later restart first emits superseded. Emit ACKNACK only after send_acknack is called, stamp with the logical deadline, and retain callback/send time separately.
- 正例 timed word：`[{"time": 0, "props": ["heartbeat_response_generation_started_500"]}, {"time": 500, "props": ["heartbeat_acknack_sent"]}, {"time": 501, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["heartbeat_response_generation_started_500"]}, {"time": 499, "props": ["heartbeat_acknack_sent"]}, {"time": 501, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["heartbeat_response_generation_started_500"]}, {"time": 501, "props": ["heartbeat_acknack_sent"]}, {"time": 502, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["heartbeat_response_generation_started_500"]}, {"time": 501, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: restart/coalescing is an explicit generation supersession, reader stop is covered, and both early and late/missing response traces are present.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Fast-DDS v3.3.0 stock ReaderTimes is 5 ms. The harness explicitly selects 500 ms; actual scheduler delay is recorded separately and never hidden as epsilon.
