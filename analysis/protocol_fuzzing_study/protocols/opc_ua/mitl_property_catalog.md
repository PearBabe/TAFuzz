# OPC UA MITL 真实性质目录

> 主目录只包含通过规范证据、固定源码映射、MightyPPL 构造和正反 trace oracle 的条目；所有人工状态仍为 `PENDING`。

- 合格性质：8
- 自动拒绝/待修：0
- 语义：数学字段用标准 MITL；执行字段用 MightyPPL weak finite `G*`；pointwise 绝对整数毫秒；先 correlation，再按单一 obligation generation 投影；缺失 AP=false。

## OPCUA-PUB-01 — Publish request is not cancelled before timeoutHint

- 性质：timeoutHint=5000 ms 的 Publish 请求排队后，服务器在前 5000 ms 内不得以 Bad_Timeout 取消它；规范不要求到点必须取消。
- 规范：[OPC 10000-4: Services 1.05.07 §7.32](https://reference.opcfoundation.org/specs/OPC-10000-4/7.32)；强度 `SHOULD / SHALL check`；时间 `5000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“The Server should wait at minimum the timeout after he received the request before cancelling”
- 数学 MITL：`G (publish_request_queued_timeout_hint_5000 -> G [0,5000) (!publish_bad_timeout))`
- MightyPPL（finite weak outer global）：`G* (publish_request_queued_timeout_hint_5000 -> G [0,5000) (!publish_bad_timeout))`
- AP：`publish_request_queued_timeout_hint_5000, publish_bad_timeout`
- AP 定义：{"publish_request_queued_timeout_hint_5000": "Service_Publish queues a request whose RequestHeader.timeoutHint equals 5000 ms.", "publish_bad_timeout": "The server sends a PublishResponse with serviceResult Bad_Timeout for that requestId."}
- Correlation：Session + Publish requestId; requestId remains an event field
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one queued Publish request; normal response, Session close, or request cancellation ends that request generation without creating another trigger in the same word.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/server/ua_subscription.c:427-452`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L427-L452)；符号 `UA_Subscription_publish`。
- 主源码映射 AP：`["publish_bad_timeout"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "Publish timeoutHint deadline and queue", "path": "src/server/ua_services_subscription.c", "symbol": "Service_Publish", "lines": "304-315", "atomic_propositions": ["publish_request_queued_timeout_hint_5000"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L304-L315"}]`
- Hook：Record queue time/maxTime at the fixed Service_Publish producer; emit Bad_Timeout immediately before sendResponse at lines 441-447 using actual monotonic time.
- 正例 timed word：`[{"time": 0, "props": ["publish_request_queued_timeout_hint_5000"]}, {"time": 5001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["publish_request_queued_timeout_hint_5000"]}, {"time": 4999, "props": ["publish_bad_timeout"]}, {"time": 5001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`APPROVE`；Approved: the formula is safety-only and does not invent an exact timeout action; a fixed queue/maxTime producer hook was added.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：This is only a no-early-cancellation safety property. timeoutHint is a hint, so no eventual Bad_Timeout at exactly 5000 ms is claimed; cancellation at the endpoint is allowed.

## OPCUA-SC-01 — SecureChannel token renewal occurs after 75% and before expiry

- 性质：锁定 open62541 默认 600000 ms token lifetime 后，客户端在 450000 ms 前不得续期，并应在 [450000,600000) ms 内续期；channel 关闭或该 generation 被取消可解除窗口。
- 规范：[OPC 10000-4: Services 1.05.07 §5.6.2.1](https://reference.opcfoundation.org/specs/OPC-10000-4/5.6.2.1)；强度 `SHOULD`；时间 `450000 ms`（`IMPLEMENTATION_PROFILE_DERIVED`）。
- 规范短摘录：“Clients should request a new SecurityToken after 75 % of its lifetime has elapsed”
- 数学 MITL：`G (security_token_issued_default_lifetime -> (G [0,450000) (!secure_channel_renew_requested) && F [0,600000) (secure_channel_renew_requested || secure_channel_closed || security_token_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (security_token_issued_default_lifetime -> (G [0,450000) (!secure_channel_renew_requested) && F [0,600000) (secure_channel_renew_requested || secure_channel_closed || security_token_generation_cancelled)))`
- AP：`security_token_issued_default_lifetime, secure_channel_renew_requested, secure_channel_closed, security_token_generation_cancelled`
- AP 定义：{"security_token_issued_default_lifetime": "OpenSecureChannel response installs a token whose revisedLifetime is 600000 ms.", "secure_channel_renew_requested": "An OpenSecureChannelRequest with requestType=RENEW is handed to the channel send path.", "secure_channel_closed": "The correlated SecureChannel closes before renewal and discharges this window.", "security_token_generation_cancelled": "A later successful processOPNResponse replaces the correlated current token with a new token before this generation's renewal-request observation; the adapter closes the old token generation at that replacement."}
- Correlation：client connection + SecureChannelId + current tokenId; tokenId is an event field, never an AP suffix
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Correlate by channel/token; only revisedLifetime=600000 enters this property. Close on successful renewal, channel close, explicit cancellation, or expiry.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/client/ua_client_connect.c:495-589`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/client/ua_client_connect.c#L495-L589)；符号 `processOPNResponse`。
- 主源码映射 AP：`["security_token_issued_default_lifetime", "security_token_generation_cancelled"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "RENEW OpenSecureChannelRequest send", "path": "src/client/ua_client_connect.c", "symbol": "sendOPNAsync", "lines": "593-646", "atomic_propositions": ["secure_channel_renew_requested"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/client/ua_client_connect.c#L593-L646"}, {"role": "SecureChannel close lifecycle", "path": "src/client/ua_client_connect.c", "symbol": "closeSecureChannel", "lines": "2198-2236", "atomic_propositions": ["secure_channel_closed"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/client/ua_client_connect.c#L2198-L2236"}, {"role": "600000 ms client lifetime profile", "path": "plugins/ua_config_default.c", "symbol": "UA_ClientConfig_setDefault", "lines": "1115-1118", "atomic_propositions": ["security_token_issued_default_lifetime"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/plugins/ua_config_default.c#L1115-L1118"}]`
- Hook：Record token installation and nextChannelRenewal at lines 560-565; record RENEW only after UA_SecureChannel_sendAsymmetricOPNMessage succeeds at lines 625-640. Store logical threshold/expiry and actual send time separately.
- 正例 timed word：`[{"time": 0, "props": ["security_token_issued_default_lifetime"]}, {"time": 450000, "props": ["secure_channel_renew_requested"]}, {"time": 450001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["security_token_issued_default_lifetime"]}, {"time": 449999, "props": ["secure_channel_renew_requested"]}, {"time": 450001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["security_token_issued_default_lifetime"]}, {"time": 600000, "props": ["secure_channel_renew_requested"]}, {"time": 600001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["security_token_issued_default_lifetime"]}, {"time": 600001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: after-75% interval replaces the incorrect exact-75% deadline; early and late/missing oracles and explicit cancellation were added.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The 75% rule is SHOULD-level guidance. 600000 ms is the locked open62541 default, not an OPC UA universal lifetime; the formula no longer invents an exact action at 75%.

## OPCUA-SC-02 — Expired old-token messages remain acceptable for 25% lifetime

- 性质：旧 token 到期后的 150000 ms 重叠窗口内，使用该旧 token 且密码学校验成功的消息应被客户端接受。
- 规范：[OPC 10000-4: Services 1.05.07 §5.6.2.1](https://reference.opcfoundation.org/specs/OPC-10000-4/5.6.2.1)；强度 `SHOULD`；时间 `150000 ms`（`IMPLEMENTATION_PROFILE_DERIVED`）。
- 规范短摘录：“Clients should accept Messages secured by an expired SecurityToken for up to 25 % of the token lifetime”
- 数学 MITL：`G (old_security_token_expired_default_lifetime -> G [0,150000] (old_token_message_received -> old_token_message_accepted))`
- MightyPPL（finite weak outer global）：`G* (old_security_token_expired_default_lifetime -> G [0,150000] (old_token_message_received -> old_token_message_accepted))`
- AP：`old_security_token_expired_default_lifetime, old_token_message_received, old_token_message_accepted`
- AP 定义：{"old_security_token_expired_default_lifetime": "The old token reaches createdAt+600000 ms while it remains the alternate token after renewal.", "old_token_message_received": "A message with the correlated old tokenId reaches checkSymHeader and passes framing/cryptographic preconditions.", "old_token_message_accepted": "checkSymHeader returns GOOD for that old-token message in the same merged callback valuation."}
- Correlation：SecureChannelId + old tokenId + message requestId; identifiers remain fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one SecureChannel and one expired old token; retain only messages carrying that tokenId during the 25% window and end on explicit close/rollover.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/ua_securechannel_crypto.c:506-569`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/ua_securechannel_crypto.c#L506-L569)；符号 `checkSymHeader`。
- 主源码映射 AP：`["old_token_message_received", "old_token_message_accepted"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "old-token installation and expiry-field snapshot", "path": "src/client/ua_client_connect.c", "symbol": "processOPNResponse", "lines": "495-589", "atomic_propositions": ["old_security_token_expired_default_lifetime"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/client/ua_client_connect.c#L495-L589"}, {"role": "600000 ms client lifetime profile", "path": "plugins/ua_config_default.c", "symbol": "UA_ClientConfig_setDefault", "lines": "1115-1118", "atomic_propositions": ["old_security_token_expired_default_lifetime"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/plugins/ua_config_default.c#L1115-L1118"}]`
- Hook：Emit received on entry with tokenId matching altSecurityToken; merge accepted into the same timestamp only if checkSymHeader returns GOOD. End the token projection on explicit channel close or old-token rollover.
- 正例 timed word：`[{"time": 0, "props": ["old_security_token_expired_default_lifetime"]}, {"time": 100000, "props": ["old_token_message_received", "old_token_message_accepted"]}, {"time": 150001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["old_security_token_expired_default_lifetime"]}, {"time": 100000, "props": ["old_token_message_received"]}, {"time": 150001, "props": []}]`
- 附加反例：`{}`
- 独立审计：`APPROVE`；Approved with caveat: explicit close/rollover terminates the single-token projection, and the 150000 ms closed endpoint requires human sign-off.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`WHITEBOX` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The locked checkSymHeader code appears not to implement the 25% grace period; this is intentionally a conformance oracle. Human review must retain the declared closed 150000 ms integer endpoint convention.

## OPCUA-SESS-01 — Inactive Session terminates at revised 1200000 ms timeout

- 性质：revisedSessionTimeout 为 1200000 ms 的会话从最后一次服务活动后开始空闲；此前不得超时终止，到期时必须终止或已有新活动重置窗口。
- 规范：[OPC 10000-4: Services 1.05.07 §5.7.2.2](https://reference.opcfoundation.org/specs/OPC-10000-4/5.7.2.2)；强度 `SHALL`；时间 `1200000 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“the Server shall automatically terminate the Client Session”
- 数学 MITL：`G (session_idle_window_started_1200000 -> (G [0,1200000) (!session_timeout_terminated) && F [0,1200000] (session_timeout_terminated || session_service_activity || session_idle_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (session_idle_window_started_1200000 -> (G [0,1200000) (!session_timeout_terminated) && F [0,1200000] (session_timeout_terminated || session_service_activity || session_idle_generation_cancelled)))`
- AP：`session_idle_window_started_1200000, session_timeout_terminated, session_service_activity, session_idle_generation_cancelled`
- AP 定义：{"session_idle_window_started_1200000": "After UA_Session_updateLifetime for a Session whose revised timeout is 1200000 ms, the adapter opens a fresh idle window.", "session_timeout_terminated": "UA_Server_cleanupSessions removes that Session with shutdown reason TIMEOUT.", "session_service_activity": "A valid correlated Service request updates the Session lifetime before expiry.", "session_idle_generation_cancelled": "Service_CloseSession removes the correlated Session with CLOSE rather than TIMEOUT, or an equivalent server purge/removal lifecycle ends it before the idle deadline."}
- Correlation：server instance + authenticationToken/sessionId; dynamic NodeIds remain fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Correlate one Session generation; each valid Service activity satisfies the old generation and starts a new projected word; explicit close/shutdown cancels it.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/server/ua_services_session.c:115-126`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_session.c#L115-L126)；符号 `UA_Server_cleanupSessions`。
- 主源码映射 AP：`["session_timeout_terminated"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "Session logical idle deadline", "path": "src/server/ua_session.c", "symbol": "UA_Session_updateLifetime", "lines": "125-131", "atomic_propositions": ["session_idle_window_started_1200000", "session_service_activity"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_session.c#L125-L131"}, {"role": "valid Service activity refresh", "path": "src/server/ua_server_binary.c", "symbol": "processMSGDecoded", "lines": "716-865", "atomic_propositions": ["session_service_activity"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_server_binary.c#L716-L865"}, {"role": "revised Session timeout creation", "path": "src/server/ua_services_session.c", "symbol": "UA_Server_createSession / Service_CreateSession", "lines": "224-260;263-393", "atomic_propositions": ["session_idle_window_started_1200000"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_session.c#L224-L260"}, {"role": "explicit CloseSession and removal", "path": "src/server/ua_services_session.c", "symbol": "Service_CloseSession / UA_Server_removeSession", "lines": "29-98;918-960", "atomic_propositions": ["session_idle_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_session.c#L29-L98"}, {"role": "1200000 ms requested client profile", "path": "plugins/ua_config_default.c", "symbol": "UA_ClientConfig_setDefault", "lines": "1173-1174", "atomic_propositions": ["session_idle_window_started_1200000"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/plugins/ua_config_default.c#L1173-L1174"}]`
- Hook：Open/reset from UA_Session_updateLifetime and the valid Service dispatch hook; emit timeout immediately before UA_Server_removeSession. Store session.validTill as the logical deadline and cleanup callback time separately.
- 正例 timed word：`[{"time": 0, "props": ["session_idle_window_started_1200000"]}, {"time": 1200000, "props": ["session_timeout_terminated"]}, {"time": 1200001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["session_idle_window_started_1200000"]}, {"time": 1199999, "props": ["session_timeout_terminated"]}, {"time": 1200001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["session_idle_window_started_1200000"]}, {"time": 1200001, "props": ["session_timeout_terminated"]}, {"time": 1200002, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["session_idle_window_started_1200000"]}, {"time": 1200001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: explicit normal cancellation, fixed trigger/activity hooks, logical deadline versus cleanup callback, and late/missing oracle were added.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：1200000 ms is an open62541 client request default; trigger only when the server-returned revisedSessionTimeout is exactly 1200000. The strict validTill < now cleanup may expose a real one-tick/source scheduling discrepancy; no epsilon is added.

## OPCUA-SUB-01 — First Publish response occurs after the first 500 ms cycle

- 性质：默认 publishingInterval=500 ms 且已有 Publish 请求时，Subscription 创建后的首个消息不得早于首周期结束，并应在 500 ms 返回通知或 keep-alive。
- 规范：[OPC 10000-4: Services 1.05.07 §5.14.1.1](https://reference.opcfoundation.org/specs/OPC-10000-4/5.14.1.1)；强度 `NORMATIVE BEHAVIOR`；时间 `500 ms`（`IMPLEMENTATION_PROFILE`）。
- 规范短摘录：“the first Message is sent at the end of the first publishing cycle”
- 数学 MITL：`G (default_subscription_first_cycle_started -> (G [0,500) (!first_publish_response) && F [0,500] (first_publish_response || first_cycle_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (default_subscription_first_cycle_started -> (G [0,500) (!first_publish_response) && F [0,500] (first_publish_response || first_cycle_generation_cancelled)))`
- AP：`default_subscription_first_cycle_started, first_publish_response, first_cycle_generation_cancelled`
- AP 定义：{"default_subscription_first_cycle_started": "CreateSubscription succeeds with revisedPublishingInterval=500 ms and at least one Publish request is queued before the first cycle.", "first_publish_response": "The first correlated PublishResponse is sent, containing either notifications or an empty keep-alive message.", "first_cycle_generation_cancelled": "The correlated Subscription is deleted, its revised interval is changed by ModifySubscription, or its Session-close path deletes the Subscription before the first-cycle response."}
- Correlation：Session authenticationToken + subscriptionId + Publish requestId; IDs remain event fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one Subscription first-cycle generation; close, deletion, or revised-setting change emits first_cycle_generation_cancelled and ends it.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/server/ua_subscription.c:730-759`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L730-L759)；符号 `Subscription_setState`。
- 主源码映射 AP：`["default_subscription_first_cycle_started"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "CreateSubscription revised values", "path": "src/server/ua_services_subscription.c", "symbol": "Service_CreateSubscription", "lines": "55-127", "atomic_propositions": ["default_subscription_first_cycle_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L55-L127"}, {"role": "Publish request queue prerequisite", "path": "src/server/ua_services_subscription.c", "symbol": "Service_Publish", "lines": "236-355", "atomic_propositions": ["default_subscription_first_cycle_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L236-L355"}, {"role": "first notification or keep-alive response", "path": "src/server/ua_subscription.c", "symbol": "UA_Subscription_publish", "lines": "427-648", "atomic_propositions": ["first_publish_response"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L427-L648"}, {"role": "Subscription deletion or setting change", "path": "src/server/ua_subscription.c", "symbol": "UA_Subscription_delete", "lines": "53-115", "atomic_propositions": ["first_cycle_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L53-L115"}, {"role": "revised interval change", "path": "src/server/ua_services_subscription.c", "symbol": "Service_ModifySubscription", "lines": "130-193", "atomic_propositions": ["first_cycle_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L130-L193"}, {"role": "500 ms client request profile", "path": "include/open62541/client_subscriptions.h", "symbol": "UA_CreateSubscriptionRequest_default", "lines": "43-63", "atomic_propositions": ["default_subscription_first_cycle_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/include/open62541/client_subscriptions.h#L43-L63"}]`
- Hook：Start only after CreateSubscription returns revisedPublishingInterval=500, callback registration succeeds, and a Publish request is queued. Record the scheduled first-cycle deadline; emit response at the actual sendResponse handoff and keep callback time separately.
- 正例 timed word：`[{"time": 0, "props": ["default_subscription_first_cycle_started"]}, {"time": 500, "props": ["first_publish_response"]}, {"time": 501, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["default_subscription_first_cycle_started"]}, {"time": 499, "props": ["first_publish_response"]}, {"time": 501, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["default_subscription_first_cycle_started"]}, {"time": 501, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["default_subscription_first_cycle_started"]}, {"time": 501, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: queue/Session/setting cancellation is explicit, revised-value and response hooks are fixed, and a late/missing oracle was added.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The 500 ms request default is not enough: this property triggers only when the CreateSubscription response reports revisedPublishingInterval=500 and a Publish request remains available or is explicitly cancelled.

## OPCUA-SUB-02 — No-notification keep-alive is due after ten 500 ms cycles

- 性质：首个消息之后，在无通知且 Publish 请求持续可用的默认 profile 中，不得在 5000 ms 前发 keep-alive；到十个周期时应发 keep-alive，若中途有通知则结束该窗口。
- 规范：[OPC 10000-4: Services 1.05.07 §5.14.1.1; 5.14.2.2](https://reference.opcfoundation.org/specs/OPC-10000-4/5.14.1.1)；强度 `NORMATIVE BEHAVIOR`；时间 `5000 ms`（`IMPLEMENTATION_PROFILE_DERIVED`）。
- 规范短摘录：“When the maximum keep-alive count is reached, a Publish request is de-queued”
- 数学 MITL：`G (default_keepalive_window_started -> (G [0,5000) (!keepalive_response) && F [0,5000] (keepalive_response || notification_response || keepalive_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (default_keepalive_window_started -> (G [0,5000) (!keepalive_response) && F [0,5000] (keepalive_response || notification_response || keepalive_generation_cancelled)))`
- AP：`default_keepalive_window_started, keepalive_response, notification_response, keepalive_generation_cancelled`
- AP 定义：{"default_keepalive_window_started": "After a prior message/reset, the adapter observes revised interval=500, maxKeepAliveCount=10, no queued notifications, and a Publish request remains available.", "keepalive_response": "A correlated PublishResponse with zero notifications is sent as keep-alive.", "notification_response": "A correlated PublishResponse containing at least one notification ends this no-notification window.", "keepalive_generation_cancelled": "The correlated Subscription is deleted, ModifySubscription changes its revised interval/count, or its Session-close path deletes the Subscription before this keep-alive generation completes."}
- Correlation：Session + subscriptionId + Publish request queue; sequence numbers/requestIds are fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one keep-alive counter generation; notification satisfies it, while deletion, setting modification, or Session close emits keepalive_generation_cancelled.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/server/ua_subscription.c:477-610`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L477-L610)；符号 `UA_Subscription_publish`。
- 主源码映射 AP：`["default_keepalive_window_started", "keepalive_response", "notification_response"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "revised keep-alive settings", "path": "src/server/ua_services_subscription.c", "symbol": "setSubscriptionSettings / Service_CreateSubscription", "lines": "26-52;55-127", "atomic_propositions": ["default_keepalive_window_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L26-L52"}, {"role": "Subscription deletion", "path": "src/server/ua_subscription.c", "symbol": "UA_Subscription_delete", "lines": "53-115", "atomic_propositions": ["keepalive_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L53-L115"}, {"role": "revised interval/count change", "path": "src/server/ua_services_subscription.c", "symbol": "Service_ModifySubscription", "lines": "130-193", "atomic_propositions": ["keepalive_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L130-L193"}, {"role": "default 500 ms by 10 client profile", "path": "include/open62541/client_subscriptions.h", "symbol": "UA_CreateSubscriptionRequest_default", "lines": "43-63", "atomic_propositions": ["default_keepalive_window_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/include/open62541/client_subscriptions.h#L43-L63"}]`
- Hook：Emit a new generation after lines 609-610 reset currentKeepAliveCount and preconditions are rechecked. Store the tenth publishing-cycle deadline; emit keepalive/notification at sendResponse and retain callback time separately.
- 正例 timed word：`[{"time": 0, "props": ["default_keepalive_window_started"]}, {"time": 5000, "props": ["keepalive_response"]}, {"time": 5001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["default_keepalive_window_started"]}, {"time": 4999, "props": ["keepalive_response"]}, {"time": 5001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["default_keepalive_window_started"]}, {"time": 5001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["default_keepalive_window_started"]}, {"time": 5001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: all cancellation paths are represented by an AP, one counter generation is monitored per word, deadline/callback timestamps are separated, and late/missing is tested.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：Both inputs must be server-revised values (500 ms and 10), not merely client requests. The logical tenth-cycle deadline and actual callback/send times are separate; no scheduler epsilon is invented.

## OPCUA-SUB-03 — Subscription without Publish requests closes after 10000 cycles

- 性质：默认 500 ms publishing interval、lifetimeCount=10000 时，从无 Publish 请求窗口开始到 5000000 ms 前不得因 lifetime 超时关闭；到期时应关闭或已被服务活动重置。
- 规范：[OPC 10000-4: Services 1.05.07 §5.14.1.1; 5.14.2.2](https://reference.opcfoundation.org/specs/OPC-10000-4/5.14.2.2)；强度 `SHALL`；时间 `5000000 ms`（`IMPLEMENTATION_PROFILE_DERIVED`）。
- 规范短摘录：“then the Subscription shall be deleted by the Server”
- 数学 MITL：`G (default_subscription_no_publish_window_started -> (G [0,5000000) (!subscription_timeout_closed) && F [0,5000000] (subscription_timeout_closed || subscription_lifetime_reset || subscription_lifetime_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (default_subscription_no_publish_window_started -> (G [0,5000000) (!subscription_timeout_closed) && F [0,5000000] (subscription_timeout_closed || subscription_lifetime_reset || subscription_lifetime_generation_cancelled)))`
- AP：`default_subscription_no_publish_window_started, subscription_timeout_closed, subscription_lifetime_reset, subscription_lifetime_generation_cancelled`
- AP 定义：{"default_subscription_no_publish_window_started": "No Publish request is available immediately after a lifetime reset for a subscription with revised 500 ms and lifetimeCount 10000.", "subscription_timeout_closed": "The server marks Bad_Timeout and executes the timeout-close/delete path for the correlated subscription.", "subscription_lifetime_reset": "A qualifying Subscription service or processed Publish response resets the lifetime counter.", "subscription_lifetime_generation_cancelled": "Manual UA_Subscription_delete or a ModifySubscription revised-setting change ends the correlated lifetime generation without the Bad_Timeout cause."}
- Correlation：Session + subscriptionId; Publish requestIds and sequence numbers remain fields
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one lifetime-counter generation; reset satisfies and starts a separate generation, while manual deletion/transfer/setting change emits cancellation.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/server/ua_subscription.c:455-474`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L455-L474)；符号 `UA_Subscription_publish`。
- 主源码映射 AP：`["default_subscription_no_publish_window_started", "subscription_timeout_closed"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "Subscription lifetime reset", "path": "src/server/ua_subscription.c", "symbol": "Subscription_resetLifetime", "lines": "118-120", "atomic_propositions": ["subscription_lifetime_reset"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L118-L120"}, {"role": "manual Subscription deletion", "path": "src/server/ua_subscription.c", "symbol": "UA_Subscription_delete", "lines": "53-115", "atomic_propositions": ["subscription_lifetime_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L53-L115"}, {"role": "service reset or revised-setting change", "path": "src/server/ua_services_subscription.c", "symbol": "Service_ModifySubscription / Service_Republish", "lines": "130-193;393-433", "atomic_propositions": ["subscription_lifetime_reset", "subscription_lifetime_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L130-L193"}, {"role": "default revised-value source", "path": "src/server/ua_services_subscription.c", "symbol": "setSubscriptionSettings / Service_CreateSubscription", "lines": "26-52;55-127", "atomic_propositions": ["default_subscription_no_publish_window_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L26-L52"}, {"role": "500 ms and 10000-count client profile", "path": "include/open62541/client_subscriptions.h", "symbol": "UA_CreateSubscriptionRequest_default", "lines": "43-63", "atomic_propositions": ["default_subscription_no_publish_window_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/include/open62541/client_subscriptions.h#L43-L63"}]`
- Hook：Start immediately after Subscription_resetLifetime when the Publish queue is empty and revised values are 500/10000. Store the 10000th-cycle logical deadline; emit timeout-close when statusChange becomes BADTIMEOUT and record callback time separately.
- 正例 timed word：`[{"time": 0, "props": ["default_subscription_no_publish_window_started"]}, {"time": 5000000, "props": ["subscription_timeout_closed"]}, {"time": 5000001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["default_subscription_no_publish_window_started"]}, {"time": 4999999, "props": ["subscription_timeout_closed"]}, {"time": 5000001, "props": []}]`
- 附加反例：`{"late_or_missing": [{"time": 0, "props": ["default_subscription_no_publish_window_started"]}, {"time": 5000001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["default_subscription_no_publish_window_started"]}, {"time": 5000001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: early and late/missing oracles now cover both halves, cancellation/reset is explicit, hooks are fixed, and the source off-by-one remains a deliberate conformance target.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：open62541 v1.4.14 checks currentLifetimeCount > lifeTimeCount while the standard closes when the counter reaches the value. The 5000000 ms oracle intentionally exposes that possible one-cycle discrepancy; it is not relaxed to match source.

## OPCUA-SUB-04 — Disabled publishing suppresses notifications but retains keep-alives

- 性质：publishing 被禁用且 revised interval/count=500/10 的单个 generation 内不得发送通知或提前 keep-alive，并应在 5000 ms 发送 keep-alive；re-enable、删除、参数变化或 Publish 队列消失会显式取消。
- 规范：[OPC 10000-4: Services 1.05.07 §5.14.1.1](https://reference.opcfoundation.org/specs/OPC-10000-4/5.14.1.1)；强度 `NORMATIVE BEHAVIOR`；时间 `5000 ms`（`IMPLEMENTATION_PROFILE_DERIVED`）。
- 规范短摘录：“the Subscription continues to execute cyclically and continues to send keep-alive Messages”
- 数学 MITL：`G (disabled_keepalive_window_started -> (G [0,5000] (!notification_response_while_disabled) && G [0,5000) (!keepalive_response_while_disabled) && F [0,5000] (keepalive_response_while_disabled || disabled_keepalive_generation_cancelled)))`
- MightyPPL（finite weak outer global）：`G* (disabled_keepalive_window_started -> (G [0,5000] (!notification_response_while_disabled) && G [0,5000) (!keepalive_response_while_disabled) && F [0,5000] (keepalive_response_while_disabled || disabled_keepalive_generation_cancelled)))`
- AP：`disabled_keepalive_window_started, notification_response_while_disabled, keepalive_response_while_disabled, disabled_keepalive_generation_cancelled`
- AP 定义：{"disabled_keepalive_window_started": "Adapter observes publishing disabled at a keep-alive counter reset/boundary, revised interval=500, count=10, and queued Publish availability.", "notification_response_while_disabled": "A PublishResponse for this disabled subscription contains any notification.", "keepalive_response_while_disabled": "A zero-notification keep-alive PublishResponse is sent while publishing remains disabled.", "disabled_keepalive_generation_cancelled": "Operation_SetPublishingMode re-enables the Subscription, it is deleted, or ModifySubscription changes the revised interval/count before the disabled keep-alive generation completes."}
- Correlation：Session + subscriptionId + publishing mode epoch
- 投影：EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old generation and opens a separately monitored generation. Project one disabled-mode keep-alive generation; cancellation is emitted on re-enable, deletion, revised-setting change, Session close, or Publish-queue loss.
- 监控实例：one correlated obligation instance per timed word; if the trigger can repeat, the adapter spawns a new projection keyed by timer/request generation
- 源码：[open62541/open62541@76e425ee963e `src/server/ua_subscription.c:477-610`](https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L477-L610)；符号 `UA_Subscription_publish`。
- 主源码映射 AP：`["notification_response_while_disabled", "keepalive_response_while_disabled"]`
- 辅助源码锚点：`{}`
- 结构化辅助映射：`[{"role": "disable/re-enable and lifetime reset", "path": "src/server/ua_services_subscription.c", "symbol": "Operation_SetPublishingMode", "lines": "196-214", "atomic_propositions": ["disabled_keepalive_window_started", "disabled_keepalive_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L196-L214"}, {"role": "Subscription deletion", "path": "src/server/ua_subscription.c", "symbol": "UA_Subscription_delete", "lines": "53-115", "atomic_propositions": ["disabled_keepalive_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_subscription.c#L53-L115"}, {"role": "revised interval/count change", "path": "src/server/ua_services_subscription.c", "symbol": "Service_ModifySubscription", "lines": "130-193", "atomic_propositions": ["disabled_keepalive_generation_cancelled"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L130-L193"}, {"role": "default revised-value source", "path": "src/server/ua_services_subscription.c", "symbol": "setSubscriptionSettings / Service_CreateSubscription", "lines": "26-52;55-127", "atomic_propositions": ["disabled_keepalive_window_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/src/server/ua_services_subscription.c#L26-L52"}, {"role": "500 ms by 10 client profile", "path": "include/open62541/client_subscriptions.h", "symbol": "UA_CreateSubscriptionRequest_default", "lines": "43-63", "atomic_propositions": ["disabled_keepalive_window_started"], "url": "https://github.com/open62541/open62541/blob/76e425ee963e8c16c0414f2f6bd0c7a5761a92c3/include/open62541/client_subscriptions.h#L43-L63"}]`
- Hook：Read disabled state and notifications=0 at lines 477-479; store the tenth-cycle logical deadline and emit keepalive at sendResponse. Emit cancellation atomically before a re-enable/delete/settings/queue transition and record callback time separately.
- 正例 timed word：`[{"time": 0, "props": ["disabled_keepalive_window_started"]}, {"time": 5000, "props": ["keepalive_response_while_disabled"]}, {"time": 5001, "props": []}]`
- 附加正例/合法 supersession：`{}`
- 反例 timed word：`[{"time": 0, "props": ["disabled_keepalive_window_started"]}, {"time": 1000, "props": ["notification_response_while_disabled"]}, {"time": 5000, "props": ["keepalive_response_while_disabled"]}, {"time": 5001, "props": []}]`
- 附加反例：`{"early_keepalive": [{"time": 0, "props": ["disabled_keepalive_window_started"]}, {"time": 4999, "props": ["keepalive_response_while_disabled"]}, {"time": 5001, "props": []}], "late_or_missing": [{"time": 0, "props": ["disabled_keepalive_window_started"]}, {"time": 5001, "props": []}], "negative_late_or_missing": [{"time": 0, "props": ["disabled_keepalive_window_started"]}, {"time": 5001, "props": []}]}`
- 独立审计：`FIXED_AFTER_AUDIT`；Original audit disposition=FIX; fixed after audit: re-enable/delete/settings/queue cancellation is explicit, early keep-alive and late/missing are separately tested, and mode/reset hooks are fixed.
- 被测角色/benchmark 可达性/范围：`未限定` / `未单独评估` / 见性质与限制字段。
- 可观测性/价值/置信度：`HYBRID` / `HIGH` / `HIGH`。
- 验证：build=`True`，positive=`POSITIVE`，negative=`NEGATIVE`，symbolic/concrete=`True`。
- 限制/待审：The trigger remains a counter-boundary event, not raw SetPublishingMode reception, because the current-cycle phase is otherwise unknown. The distinct claim is disabled-mode notification suppression; the keep-alive timer reuses the same revised counter semantics as OPCUA-SUB-02.
