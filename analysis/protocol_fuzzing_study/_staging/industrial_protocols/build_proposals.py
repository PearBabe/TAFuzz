#!/usr/bin/env python3
"""Generate industrial-protocol proposal JSON inside this staging directory only."""

from __future__ import annotations

import json
from pathlib import Path

from source_mapping_enrichment import enrich_cards


HERE = Path(__file__).resolve().parent
OPEN62541 = "76e425ee963e8c16c0414f2f6bd0c7a5761a92c3"
FASTDDS = "94940169442298e2736af79720ef05d89a1b2a7d"
CYCLONE = "2cdd114cbd18340c606573b4cc8dc20cc161ec5a"
ISOTP = "7b44c5282ee390df4977b710218564eb73e2dc2a"
ISO14229 = "b0e92b14fcc384d42bfd01ecd7f745addb6bf761"


def gh(repo: str, commit: str, path: str, lines: str) -> str:
    start, _, end = lines.partition("-")
    suffix = f"#L{start}" + (f"-L{end}" if end else "")
    return f"https://github.com/{repo}/blob/{commit}/{path}{suffix}"


def tr(*events: tuple[int, str]) -> list[dict[str, object]]:
    return [{"time": tick, "props": props.split() if props else []} for tick, props in events]


def card(
    *, pid: str, protocol: str, extension: str, title: str, category: str,
    natural: str, strength: str, standard: str, version: str, section: str,
    standard_url: str, excerpt: str, time_value: str, parameter: str,
    time_source: str, basis: str, formula: str, aps: dict[str, str],
    correlation: str, source_repo: str, source_commit: str, source_path: str,
    source_symbol: str, source_lines: str, hook: str,
    positive: list[dict[str, object]], negative: list[dict[str, object]],
    projection: str, observability: str = "HYBRID", oracle: str = "HIGH",
    triggerability: str = "MEDIUM", confidence: str = "HIGH",
    review: str = "请确认角色、计时起点、profile 常数、AP 和 correlation 映射。",
    limitations: str = "仅适用于卡片声明的角色、状态和固定时间 profile。",
    audit_status: str = "FIXED_AFTER_AUDIT", audit_note: str = "",
    additional_negative: dict[str, list[dict[str, object]]] | None = None,
    additional_positive: dict[str, list[dict[str, object]]] | None = None,
    negative_kind: str = "PRIMARY_ORACLE",
    cancellation_aps: tuple[str, ...] = (),
    aux_sources: dict[str, tuple[str, str, str]] | None = None,
    timer_semantics: str = (
        "The protocol verdict uses the declared logical deadline and observes whether the "
        "correlated action occurred; actual callback/dispatch time is retained separately."
    ),
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": pid,
        "protocol": protocol,
        "protocol_extension": extension,
        "title": title,
        "category": category,
        "natural_language": natural,
        "normative_strength": strength,
        "standard": standard,
        "standard_version": version,
        "standard_section": section,
        "standard_url": standard_url,
        "standard_excerpt": excerpt,
        "time_value_ms": time_value,
        "time_parameter": parameter,
        "time_source": time_source,
        "instantiation_basis": basis,
        "mathematical_mitl": formula,
        "mightyppl_formula": formula,
        "interval_class": "NON_PUNCTUAL",
        "pointwise_semantics": "strict pointwise; finite word; absolute integer milliseconds",
        "finite_end_semantics": "trace extends beyond the largest bounded obligation; omitted APs are false",
        "atomic_propositions": list(aps),
        "ap_definitions": aps,
        "correlation_key": correlation,
        "projection_rule": (
            "EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD; each reset/restart closes the old "
            "generation and opens a separately monitored generation. " + projection
        ),
        "projection_cardinality": "EXACTLY_ONE_TRIGGER_PER_PROJECTED_WORD",
        "trigger_event_semantics": (
            "Emit the trigger only after every role/state/profile precondition has been checked; "
            "never emit two trigger valuations in the same projected word."
        ),
        "cancellation_or_supersession_aps": list(cancellation_aps),
        "timer_observation_semantics": timer_semantics,
        "source_repository": source_repo,
        "source_commit": source_commit,
        "source_path": source_path,
        "source_symbol": source_symbol,
        "source_lines": source_lines,
        "source_url": gh(source_repo, source_commit, source_path, source_lines),
        "instrumentation_timing": hook,
        "observability": observability,
        "oracle_value": oracle,
        "triggerability": triggerability,
        "confidence": confidence,
        "positive_trace": positive,
        "negative_trace": negative,
        "negative_trace_kind": negative_kind,
        "additional_negative_traces": additional_negative or {},
        "additional_positive_traces": additional_positive or {},
        "independent_audit_status": audit_status,
        "independent_audit_report": "analysis/protocol_fuzzing_study/_audit/industrial_audit.md",
        "independent_audit_note": audit_note,
        "human_review_status": "PENDING",
        "review_question": review,
        "limitations": limitations,
    }
    for role, (path, lines, description) in (aux_sources or {}).items():
        result[f"{role}_source_path"] = path
        result[f"{role}_source_lines"] = lines
        result[f"{role}_source_url"] = gh(source_repo, source_commit, path, lines)
        result[f"{role}_source_description"] = description
    return result


OPC_URL = "https://reference.opcfoundation.org/specs/OPC-10000-4"
OPC_UA = [
    card(
        pid="OPCUA-SC-01", protocol="OPC UA", extension="OPC UA SecureChannel client, open62541 default profile",
        title="SecureChannel token renewal occurs after 75% and before expiry", category="security-token renewal",
        natural="锁定 open62541 默认 600000 ms token lifetime 后，客户端在 450000 ms 前不得续期，并应在 [450000,600000) ms 内续期；channel 关闭或该 generation 被取消可解除窗口。",
        strength="SHOULD", standard="OPC 10000-4: Services", version="1.05.07", section="5.6.2.1",
        standard_url=f"{OPC_URL}/5.6.2.1", excerpt="Clients should request a new SecurityToken after 75 % of its lifetime has elapsed",
        time_value="450000", parameter="0.75 * revisedLifetime",
        time_source="OPC 10000-4 75% rule applied to open62541 secureChannelLifeTime default 600000 ms",
        basis="IMPLEMENTATION_PROFILE_DERIVED", formula="G* (security_token_issued_default_lifetime -> (G [0,450000) (!secure_channel_renew_requested) && F [0,600000) (secure_channel_renew_requested || secure_channel_closed || security_token_generation_cancelled)))",
        aps={
            "security_token_issued_default_lifetime":"OpenSecureChannel response installs a token whose revisedLifetime is 600000 ms.",
            "secure_channel_renew_requested":"An OpenSecureChannelRequest with requestType=RENEW is handed to the channel send path.",
            "secure_channel_closed":"The correlated SecureChannel closes before renewal and discharges this window.",
            "security_token_generation_cancelled":"Harness reset or an independently observed token-generation replacement makes this generation unobservable before renewal.",
        },
        correlation="client connection + SecureChannelId + current tokenId; tokenId is an event field, never an AP suffix",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/client/ua_client_connect.c", source_symbol="__Client_renewSecureChannel", source_lines="560-660",
        hook="Record token installation and nextChannelRenewal at lines 560-565; record RENEW only after UA_SecureChannel_sendAsymmetricOPNMessage succeeds at lines 625-640. Store logical threshold/expiry and actual send time separately.",
        positive=tr((0,"security_token_issued_default_lifetime"),(450000,"secure_channel_renew_requested"),(450001,"")),
        negative=tr((0,"security_token_issued_default_lifetime"),(449999,"secure_channel_renew_requested"),(450001,"")),
        projection="Correlate by channel/token; only revisedLifetime=600000 enters this property. Close on successful renewal, channel close, explicit cancellation, or expiry.",
        triggerability="HIGH",
        limitations="The 75% rule is SHOULD-level guidance. 600000 ms is the locked open62541 default, not an OPC UA universal lifetime; the formula no longer invents an exact action at 75%.",
        additional_negative={
            "late_or_missing": tr((0,"security_token_issued_default_lifetime"),(600000,"secure_channel_renew_requested"),(600001,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("secure_channel_closed", "security_token_generation_cancelled"),
        aux_sources={
            "lifetime_configuration": ("plugins/ua_config_default.c", "1115-1118", "Open62541 client default secureChannelLifeTime=600000 ms."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: after-75% interval replaces the incorrect exact-75% deadline; early and late/missing oracles and explicit cancellation were added.",
    ),
    card(
        pid="OPCUA-SC-02", protocol="OPC UA", extension="OPC UA SecureChannel client, open62541 default profile",
        title="Expired old-token messages remain acceptable for 25% lifetime", category="security-token overlap",
        natural="旧 token 到期后的 150000 ms 重叠窗口内，使用该旧 token 且密码学校验成功的消息应被客户端接受。",
        strength="SHOULD", standard="OPC 10000-4: Services", version="1.05.07", section="5.6.2.1",
        standard_url=f"{OPC_URL}/5.6.2.1", excerpt="Clients should accept Messages secured by an expired SecurityToken for up to 25 % of the token lifetime",
        time_value="150000", parameter="0.25 * revisedLifetime",
        time_source="OPC 10000-4 25% overlap applied to open62541 600000 ms default token lifetime",
        basis="IMPLEMENTATION_PROFILE_DERIVED", formula="G* (old_security_token_expired_default_lifetime -> G [0,150000] (old_token_message_received -> old_token_message_accepted))",
        aps={
            "old_security_token_expired_default_lifetime":"The old token reaches createdAt+600000 ms while it remains the alternate token after renewal.",
            "old_token_message_received":"A message with the correlated old tokenId reaches checkSymHeader and passes framing/cryptographic preconditions.",
            "old_token_message_accepted":"checkSymHeader returns GOOD for that old-token message in the same merged callback valuation.",
        },
        correlation="SecureChannelId + old tokenId + message requestId; identifiers remain fields",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/ua_securechannel_crypto.c", source_symbol="checkSymHeader", source_lines="505-568",
        hook="Emit received on entry with tokenId matching altSecurityToken; merge accepted into the same timestamp only if checkSymHeader returns GOOD. End the token projection on explicit channel close or old-token rollover.",
        positive=tr((0,"old_security_token_expired_default_lifetime"),(100000,"old_token_message_received old_token_message_accepted"),(150001,"")),
        negative=tr((0,"old_security_token_expired_default_lifetime"),(100000,"old_token_message_received"),(150001,"")),
        projection="Project one SecureChannel and one expired old token; retain only messages carrying that tokenId during the 25% window and end on explicit close/rollover.",
        observability="WHITEBOX", triggerability="MEDIUM", confidence="HIGH",
        limitations="The locked checkSymHeader code appears not to implement the 25% grace period; this is intentionally a conformance oracle. Human review must retain the declared closed 150000 ms integer endpoint convention.",
        audit_status="APPROVE",
        audit_note="Approved with caveat: explicit close/rollover terminates the single-token projection, and the 150000 ms closed endpoint requires human sign-off.",
        aux_sources={
            "lifetime_configuration": ("plugins/ua_config_default.c", "1115-1118", "Open62541 default 600000 ms lifetime used to derive the 150000 ms overlap."),
        },
        timer_semantics="Token expiry and the 25% logical overlap are derived from createdAt/revisedLifetime; message acceptance is merged with the actual checkSymHeader return callback.",
    ),
    card(
        pid="OPCUA-SESS-01", protocol="OPC UA", extension="OPC UA Session server, open62541 client-default requested timeout",
        title="Inactive Session terminates at revised 1200000 ms timeout", category="session inactivity",
        natural="revisedSessionTimeout 为 1200000 ms 的会话从最后一次服务活动后开始空闲；此前不得超时终止，到期时必须终止或已有新活动重置窗口。",
        strength="SHALL", standard="OPC 10000-4: Services", version="1.05.07", section="5.7.2.2",
        standard_url=f"{OPC_URL}/5.7.2.2", excerpt="the Server shall automatically terminate the Client Session",
        time_value="1200000", parameter="revisedSessionTimeout",
        time_source="open62541 requestedSessionTimeout default 1200000 ms, accepted when below the server maximum",
        basis="IMPLEMENTATION_PROFILE", formula="G* (session_idle_window_started_1200000 -> (G [0,1200000) (!session_timeout_terminated) && F [0,1200000] (session_timeout_terminated || session_service_activity || session_idle_generation_cancelled)))",
        aps={
            "session_idle_window_started_1200000":"After UA_Session_updateLifetime for a Session whose revised timeout is 1200000 ms, the adapter opens a fresh idle window.",
            "session_timeout_terminated":"UA_Server_cleanupSessions removes that Session with shutdown reason TIMEOUT.",
            "session_service_activity":"A valid correlated Service request updates the Session lifetime before expiry.",
            "session_idle_generation_cancelled":"Explicit CloseSession, server shutdown, or harness reset ends observation without asserting an inactivity timeout.",
        },
        correlation="server instance + authenticationToken/sessionId; dynamic NodeIds remain fields",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/server/ua_services_session.c", source_symbol="UA_Server_cleanupSessions", source_lines="114-125",
        hook="Open/reset from UA_Session_updateLifetime and the valid Service dispatch hook; emit timeout immediately before UA_Server_removeSession. Store session.validTill as the logical deadline and cleanup callback time separately.",
        positive=tr((0,"session_idle_window_started_1200000"),(1200000,"session_timeout_terminated"),(1200001,"")),
        negative=tr((0,"session_idle_window_started_1200000"),(1199999,"session_timeout_terminated"),(1200001,"")),
        projection="Correlate one Session generation; each valid Service activity satisfies the old generation and starts a new projected word; explicit close/shutdown cancels it.",
        triggerability="MEDIUM",
        limitations="1200000 ms is an open62541 client request default; trigger only when the server-returned revisedSessionTimeout is exactly 1200000. The strict validTill < now cleanup may expose a real one-tick/source scheduling discrepancy; no epsilon is added.",
        additional_negative={
            "late_or_missing": tr((0,"session_idle_window_started_1200000"),(1200001,"session_timeout_terminated"),(1200002,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("session_service_activity", "session_idle_generation_cancelled"),
        aux_sources={
            "trigger": ("src/server/ua_session.c", "125-131", "UA_Session_updateLifetime computes session.validTill from the revised timeout."),
            "activity": ("src/server/ua_server_binary.c", "809-810", "A valid Service dispatch refreshes the Session lifetime."),
            "requested_profile": ("plugins/ua_config_default.c", "1173-1174", "Client requestedSessionTimeout default; not itself the revised value."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: explicit normal cancellation, fixed trigger/activity hooks, logical deadline versus cleanup callback, and late/missing oracle were added.",
    ),
    card(
        pid="OPCUA-SUB-01", protocol="OPC UA", extension="OPC UA Subscription, open62541 default CreateSubscription profile",
        title="First Publish response occurs after the first 500 ms cycle", category="subscription first cycle",
        natural="默认 publishingInterval=500 ms 且已有 Publish 请求时，Subscription 创建后的首个消息不得早于首周期结束，并应在 500 ms 返回通知或 keep-alive。",
        strength="NORMATIVE BEHAVIOR", standard="OPC 10000-4: Services", version="1.05.07", section="5.14.1.1",
        standard_url=f"{OPC_URL}/5.14.1.1", excerpt="the first Message is sent at the end of the first publishing cycle",
        time_value="500", parameter="revisedPublishingInterval",
        time_source="open62541 UA_CreateSubscriptionRequest_default requestedPublishingInterval=500 ms",
        basis="IMPLEMENTATION_PROFILE", formula="G* (default_subscription_first_cycle_started -> (G [0,500) (!first_publish_response) && F [0,500] (first_publish_response || first_cycle_generation_cancelled)))",
        aps={
            "default_subscription_first_cycle_started":"CreateSubscription succeeds with revisedPublishingInterval=500 ms and at least one Publish request is queued before the first cycle.",
            "first_publish_response":"The first correlated PublishResponse is sent, containing either notifications or an empty keep-alive message.",
            "first_cycle_generation_cancelled":"The Session/Subscription closes or the revised interval changes before the first-cycle deadline.",
        },
        correlation="Session authenticationToken + subscriptionId + Publish requestId; IDs remain event fields",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/server/ua_subscription.c", source_symbol="Subscription_setState", source_lines="707-758",
        hook="Start only after CreateSubscription returns revisedPublishingInterval=500, callback registration succeeds, and a Publish request is queued. Record the scheduled first-cycle deadline; emit response at the actual sendResponse handoff and keep callback time separately.",
        positive=tr((0,"default_subscription_first_cycle_started"),(500,"first_publish_response"),(501,"")),
        negative=tr((0,"default_subscription_first_cycle_started"),(499,"first_publish_response"),(501,"")),
        projection="Project one Subscription first-cycle generation; close, deletion, or revised-setting change emits first_cycle_generation_cancelled and ends it.",
        triggerability="HIGH",
        limitations="The 500 ms request default is not enough: this property triggers only when the CreateSubscription response reports revisedPublishingInterval=500 and a Publish request remains available or is explicitly cancelled.",
        additional_negative={
            "late_or_missing": tr((0,"default_subscription_first_cycle_started"),(501,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("first_cycle_generation_cancelled",),
        aux_sources={
            "create_and_revised": ("src/server/ua_services_subscription.c", "55-127", "CreateSubscription sets the state and returns revised interval/count values."),
            "request_profile": ("include/open62541/client_subscriptions.h", "43-62", "Client request defaults; the adapter still checks the revised response."),
            "response": ("src/server/ua_subscription.c", "477-610", "Publish/keep-alive decision, sendResponse handoff, and keep-alive reset."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: queue/Session/setting cancellation is explicit, revised-value and response hooks are fixed, and a late/missing oracle was added.",
    ),
    card(
        pid="OPCUA-SUB-02", protocol="OPC UA", extension="OPC UA Subscription, open62541 default keep-alive profile",
        title="No-notification keep-alive is due after ten 500 ms cycles", category="subscription keep-alive",
        natural="首个消息之后，在无通知且 Publish 请求持续可用的默认 profile 中，不得在 5000 ms 前发 keep-alive；到十个周期时应发 keep-alive，若中途有通知则结束该窗口。",
        strength="NORMATIVE BEHAVIOR", standard="OPC 10000-4: Services", version="1.05.07", section="5.14.1.1; 5.14.2.2",
        standard_url=f"{OPC_URL}/5.14.1.1", excerpt="When the maximum keep-alive count is reached, a Publish request is de-queued",
        time_value="5000", parameter="revisedMaxKeepAliveCount * revisedPublishingInterval",
        time_source="open62541 defaults: 10 cycles * 500 ms",
        basis="IMPLEMENTATION_PROFILE_DERIVED", formula="G* (default_keepalive_window_started -> (G [0,5000) (!keepalive_response) && F [0,5000] (keepalive_response || notification_response || keepalive_generation_cancelled)))",
        aps={
            "default_keepalive_window_started":"After a prior message/reset, the adapter observes revised interval=500, maxKeepAliveCount=10, no queued notifications, and a Publish request remains available.",
            "keepalive_response":"A correlated PublishResponse with zero notifications is sent as keep-alive.",
            "notification_response":"A correlated PublishResponse containing at least one notification ends this no-notification window.",
            "keepalive_generation_cancelled":"Subscription deletion, revised interval/count change, or Session close cancels this generation.",
        },
        correlation="Session + subscriptionId + Publish request queue; sequence numbers/requestIds are fields",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/server/ua_subscription.c", source_symbol="UA_Subscription_publish", source_lines="477-510",
        hook="Emit a new generation after lines 609-610 reset currentKeepAliveCount and preconditions are rechecked. Store the tenth publishing-cycle deadline; emit keepalive/notification at sendResponse and retain callback time separately.",
        positive=tr((0,"default_keepalive_window_started"),(5000,"keepalive_response"),(5001,"")),
        negative=tr((0,"default_keepalive_window_started"),(4999,"keepalive_response"),(5001,"")),
        projection="Project one keep-alive counter generation; notification satisfies it, while deletion, setting modification, or Session close emits keepalive_generation_cancelled.",
        triggerability="HIGH",
        limitations="Both inputs must be server-revised values (500 ms and 10), not merely client requests. The logical tenth-cycle deadline and actual callback/send times are separate; no scheduler epsilon is invented.",
        additional_negative={
            "late_or_missing": tr((0,"default_keepalive_window_started"),(5001,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("notification_response", "keepalive_generation_cancelled"),
        aux_sources={
            "counter_reset": ("src/server/ua_subscription.c", "595-610", "A successful Publish response resets currentKeepAliveCount."),
            "request_profile": ("include/open62541/client_subscriptions.h", "43-62", "Client defaults; runtime precondition uses revised values."),
            "revised_settings": ("src/server/ua_services_subscription.c", "40-46", "Server bounds and revises keep-alive/lifetime settings."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: all cancellation paths are represented by an AP, one counter generation is monitored per word, deadline/callback timestamps are separated, and late/missing is tested.",
    ),
    card(
        pid="OPCUA-SUB-03", protocol="OPC UA", extension="OPC UA Subscription, open62541 default lifetime profile",
        title="Subscription without Publish requests closes after 10000 cycles", category="subscription lifetime",
        natural="默认 500 ms publishing interval、lifetimeCount=10000 时，从无 Publish 请求窗口开始到 5000000 ms 前不得因 lifetime 超时关闭；到期时应关闭或已被服务活动重置。",
        strength="SHALL", standard="OPC 10000-4: Services", version="1.05.07", section="5.14.1.1; 5.14.2.2",
        standard_url=f"{OPC_URL}/5.14.2.2", excerpt="then the Subscription shall be deleted by the Server",
        time_value="5000000", parameter="revisedLifetimeCount * revisedPublishingInterval",
        time_source="open62541 defaults: 10000 cycles * 500 ms",
        basis="IMPLEMENTATION_PROFILE_DERIVED", formula="G* (default_subscription_no_publish_window_started -> (G [0,5000000) (!subscription_timeout_closed) && F [0,5000000] (subscription_timeout_closed || subscription_lifetime_reset || subscription_lifetime_generation_cancelled)))",
        aps={
            "default_subscription_no_publish_window_started":"No Publish request is available immediately after a lifetime reset for a subscription with revised 500 ms and lifetimeCount 10000.",
            "subscription_timeout_closed":"The server marks Bad_Timeout and executes the timeout-close/delete path for the correlated subscription.",
            "subscription_lifetime_reset":"A qualifying Subscription service or processed Publish response resets the lifetime counter.",
            "subscription_lifetime_generation_cancelled":"Manual deletion, transfer, Session close, revised-setting change, or harness reset ends this generation without a lifetime timeout.",
        },
        correlation="Session + subscriptionId; Publish requestIds and sequence numbers remain fields",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/server/ua_subscription.c", source_symbol="UA_Subscription_publish", source_lines="455-474",
        hook="Start immediately after Subscription_resetLifetime when the Publish queue is empty and revised values are 500/10000. Store the 10000th-cycle logical deadline; emit timeout-close when statusChange becomes BADTIMEOUT and record callback time separately.",
        positive=tr((0,"default_subscription_no_publish_window_started"),(5000000,"subscription_timeout_closed"),(5000001,"")),
        negative=tr((0,"default_subscription_no_publish_window_started"),(4999999,"subscription_timeout_closed"),(5000001,"")),
        projection="Project one lifetime-counter generation; reset satisfies and starts a separate generation, while manual deletion/transfer/setting change emits cancellation.",
        triggerability="MEDIUM",
        limitations="open62541 v1.4.14 checks currentLifetimeCount > lifeTimeCount while the standard closes when the counter reaches the value. The 5000000 ms oracle intentionally exposes that possible one-cycle discrepancy; it is not relaxed to match source.",
        additional_negative={
            "late_or_missing": tr((0,"default_subscription_no_publish_window_started"),(5000001,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("subscription_lifetime_reset", "subscription_lifetime_generation_cancelled"),
        aux_sources={
            "counter_reset": ("src/server/ua_subscription.c", "117-120", "Subscription_resetLifetime starts a new counter generation."),
            "request_profile": ("include/open62541/client_subscriptions.h", "43-62", "Client request defaults; runtime precondition requires revised 500/10000."),
            "revised_settings": ("src/server/ua_services_subscription.c", "40-46", "Server-revised interval/count bounds used by the trigger."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: early and late/missing oracles now cover both halves, cancellation/reset is explicit, hooks are fixed, and the source off-by-one remains a deliberate conformance target.",
    ),
    card(
        pid="OPCUA-SUB-04", protocol="OPC UA", extension="OPC UA disabled Subscription, open62541 default profile",
        title="Disabled publishing suppresses notifications but retains keep-alives", category="disabled-subscription keep-alive",
        natural="publishing 被禁用且 revised interval/count=500/10 的单个 generation 内不得发送通知或提前 keep-alive，并应在 5000 ms 发送 keep-alive；re-enable、删除、参数变化或 Publish 队列消失会显式取消。",
        strength="NORMATIVE BEHAVIOR", standard="OPC 10000-4: Services", version="1.05.07", section="5.14.1.1",
        standard_url=f"{OPC_URL}/5.14.1.1", excerpt="the Subscription continues to execute cyclically and continues to send keep-alive Messages",
        time_value="5000", parameter="disabled maxKeepAliveCount * publishingInterval",
        time_source="open62541 defaults: 10 * 500 ms after a disabled keep-alive window boundary",
        basis="IMPLEMENTATION_PROFILE_DERIVED", formula="G* (disabled_keepalive_window_started -> (G [0,5000] (!notification_response_while_disabled) && G [0,5000) (!keepalive_response_while_disabled) && F [0,5000] (keepalive_response_while_disabled || disabled_keepalive_generation_cancelled)))",
        aps={
            "disabled_keepalive_window_started":"Adapter observes publishing disabled at a keep-alive counter reset/boundary, revised interval=500, count=10, and queued Publish availability.",
            "notification_response_while_disabled":"A PublishResponse for this disabled subscription contains any notification.",
            "keepalive_response_while_disabled":"A zero-notification keep-alive PublishResponse is sent while publishing remains disabled.",
            "disabled_keepalive_generation_cancelled":"Re-enable, deletion, revised-setting change, or Session close ends the disabled generation.",
        },
        correlation="Session + subscriptionId + publishing mode epoch",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/server/ua_subscription.c", source_symbol="UA_Subscription_publish", source_lines="477-510",
        hook="Read disabled state and notifications=0 at lines 477-479; store the tenth-cycle logical deadline and emit keepalive at sendResponse. Emit cancellation atomically before a re-enable/delete/settings/queue transition and record callback time separately.",
        positive=tr((0,"disabled_keepalive_window_started"),(5000,"keepalive_response_while_disabled"),(5001,"")),
        negative=tr((0,"disabled_keepalive_window_started"),(1000,"notification_response_while_disabled"),(5000,"keepalive_response_while_disabled"),(5001,"")),
        projection="Project one disabled-mode keep-alive generation; cancellation is emitted on re-enable, deletion, revised-setting change, Session close, or Publish-queue loss.",
        triggerability="HIGH",
        limitations="The trigger remains a counter-boundary event, not raw SetPublishingMode reception, because the current-cycle phase is otherwise unknown. The distinct claim is disabled-mode notification suppression; the keep-alive timer reuses the same revised counter semantics as OPCUA-SUB-02.",
        additional_negative={
            "early_keepalive": tr((0,"disabled_keepalive_window_started"),(4999,"keepalive_response_while_disabled"),(5001,"")),
            "late_or_missing": tr((0,"disabled_keepalive_window_started"),(5001,"")),
        },
        negative_kind="NOTIFICATION_WHILE_DISABLED",
        cancellation_aps=("disabled_keepalive_generation_cancelled",),
        aux_sources={
            "mode_transition": ("src/server/ua_services_subscription.c", "195-213", "SetPublishingMode changes state and resets lifetime."),
            "request_profile": ("include/open62541/client_subscriptions.h", "43-62", "Client request defaults; runtime precondition uses revised values."),
            "counter_reset": ("src/server/ua_subscription.c", "595-610", "A response resets the keep-alive counter for the next generation."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: re-enable/delete/settings/queue cancellation is explicit, early keep-alive and late/missing are separately tested, and mode/reset hooks are fixed.",
    ),
    card(
        pid="OPCUA-PUB-01", protocol="OPC UA", extension="OPC UA Publish timeoutHint, open62541 5000 ms client-default profile",
        title="Publish request is not cancelled before timeoutHint", category="Publish request timeout",
        natural="timeoutHint=5000 ms 的 Publish 请求排队后，服务器在前 5000 ms 内不得以 Bad_Timeout 取消它；规范不要求到点必须取消。",
        strength="SHOULD / SHALL check", standard="OPC 10000-4: Services", version="1.05.07", section="7.32",
        standard_url=f"{OPC_URL}/7.32", excerpt="The Server should wait at minimum the timeout after he received the request before cancelling",
        time_value="5000", parameter="RequestHeader.timeoutHint",
        time_source="open62541 client timeout default 5000 ms used as the locked Publish request profile",
        basis="IMPLEMENTATION_PROFILE", formula="G* (publish_request_queued_timeout_hint_5000 -> G [0,5000) (!publish_bad_timeout))",
        aps={
            "publish_request_queued_timeout_hint_5000":"Service_Publish queues a request whose RequestHeader.timeoutHint equals 5000 ms.",
            "publish_bad_timeout":"The server sends a PublishResponse with serviceResult Bad_Timeout for that requestId.",
        },
        correlation="Session + Publish requestId; requestId remains an event field",
        source_repo="open62541/open62541", source_commit=OPEN62541,
        source_path="src/server/ua_subscription.c", source_symbol="UA_Subscription_publish", source_lines="427-452",
        hook="Record queue time/maxTime at the fixed Service_Publish producer; emit Bad_Timeout immediately before sendResponse at lines 441-447 using actual monotonic time.",
        positive=tr((0,"publish_request_queued_timeout_hint_5000"),(5001,"")),
        negative=tr((0,"publish_request_queued_timeout_hint_5000"),(4999,"publish_bad_timeout"),(5001,"")),
        projection="Project one queued Publish request; normal response, Session close, or request cancellation ends that request generation without creating another trigger in the same word.",
        triggerability="HIGH",
        limitations="This is only a no-early-cancellation safety property. timeoutHint is a hint, so no eventual Bad_Timeout at exactly 5000 ms is claimed; cancellation at the endpoint is allowed.",
        audit_status="APPROVE",
        audit_note="Approved: the formula is safety-only and does not invent an exact timeout action; a fixed queue/maxTime producer hook was added.",
        aux_sources={
            "queue_and_deadline": ("src/server/ua_services_subscription.c", "304-315", "Service_Publish computes maxTime from timeoutHint and queues the request."),
        },
        timer_semantics="The timed word uses actual request queue time and actual Bad_Timeout send time; maxTime is stored for boundary audit. This safety property does not observe or require a deadline callback.",
    ),
]


RTPS_PDF = "https://www.omg.org/spec/DDSI-RTPS/2.5/PDF"
DDS_PDF = "https://www.omg.org/spec/DDS/1.4/PDF"
DDS_RTPS = [
    card(
        pid="RTPS-REL-01", protocol="DDS/RTPS", extension="DDSI-RTPS reliable StatefulWriter reference-default profile",
        title="Writer-wide ACKNACK response timer generation is due at 200 ms", category="reliability repair delay",
        natural="可靠 StatefulWriter 在显式 200 ms reference-default profile 中为 pending-reader set 启动一个 writer-wide nack-response timer generation；不得提前执行，并应在逻辑 deadline 执行，或由新 generation、unmatch/empty-set、writer stop 显式解除。",
        strength="SPECIFIED DEFAULT", standard="OMG DDSI-RTPS", version="2.5 formal/2022-04-01",
        section="8.4.7.1; 8.4.9.2.11", standard_url=RTPS_PDF,
        excerpt="nackResponseDelay.nanosec = 200 * 1000 * 1000; //200 milliseconds",
        time_value="200", parameter="Writer::nackResponseDelay",
        time_source="DDSI-RTPS 2.5 RTPS Writer default timing-related value",
        basis="NORMATIVE_DEFAULT", formula="G* (writer_nack_timer_generation_started_200 -> (G [0,200) (!nack_response_action_observed) && F [0,200] (nack_response_action_observed || nack_response_generation_superseded || rtps_pending_reader_set_empty || rtps_writer_stopped)))",
        aps={
            "writer_nack_timer_generation_started_200":"A fresh ACKNACK makes the writer-wide pending-reader set non-empty and restart_timer arms nackResponseDelay=200 ms.",
            "nack_response_action_observed":"The corresponding TimedEvent callback is observed and perform_nack_response begins; the event is stamped with the stored logical deadline and also records actual callback time.",
            "nack_response_generation_superseded":"A newer qualifying ACKNACK restarts the same writer-wide timer; it closes this generation and starts a separately projected generation.",
            "rtps_pending_reader_set_empty":"All requested repairs disappear or relevant readers are unmatched before the deadline.",
            "rtps_writer_stopped":"The writer is disabled/deleted before the deadline.",
        },
        correlation="writer GUID + timer generation + pending reader GUID/count set; ACKNACK counts and sequence numbers remain fields",
        source_repo="eProsima/Fast-DDS", source_commit=FASTDDS,
        source_path="src/cpp/rtps/writer/StatefulWriter.cpp", source_symbol="StatefulWriter::process_acknack", source_lines="1921-1960",
        hook="Require harness WriterTimes.nack_response_delay=200 ms. Emit trigger at restart_timer; a later restart first emits superseded. Emit the action only if the callback is observed, stamp it with the stored logical deadline, and retain actual callback time for overhead/jitter analysis.",
        positive=tr((0,"writer_nack_timer_generation_started_200"),(200,"nack_response_action_observed"),(201,"")),
        negative=tr((0,"writer_nack_timer_generation_started_200"),(199,"nack_response_action_observed"),(201,"")),
        projection="Project one writer-wide timer generation, not one ReaderProxy. A newer restart atomically supersedes the old generation before opening the next word.",
        observability="WHITEBOX", triggerability="HIGH",
        limitations="Fast-DDS v3.3.0 stock WriterTimes is 5 ms, not 200 ms. The benchmark explicitly configures 200 ms. The reference state transition and Fast-DDS restart-on-new-ACKNACK behavior are distinguished by timer-generation events.",
        additional_negative={
            "late_or_missing": tr((0,"writer_nack_timer_generation_started_200"),(201,"nack_response_action_observed"),(202,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("nack_response_generation_superseded", "rtps_pending_reader_set_empty", "rtps_writer_stopped"),
        aux_sources={
            "callback": ("src/cpp/rtps/writer/StatefulWriter.cpp", "225-232", "TimedEvent callback invokes perform_nack_response."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: correlation is writer-wide, restart/unmatch/stop are explicit, one timer generation is projected per word, and early plus late/missing callback oracles are present.",
    ),
    card(
        pid="RTPS-REL-02", protocol="DDS/RTPS", extension="DDSI-RTPS reliable StatefulReader reference-default profile",
        title="HEARTBEAT response ACKNACK is sent after 500 ms", category="reliability acknowledgment delay",
        natural="可靠 StatefulReader 收到表明有缺失数据的 HEARTBEAT 后，在 reference-default profile 中不得于 500 ms 前发送 ACKNACK，并应在 500 ms 发送或匹配已解除。",
        strength="SPECIFIED DEFAULT", standard="OMG DDSI-RTPS", version="2.5 formal/2022-04-01",
        section="8.4.10.1; 8.4.12.2.5", standard_url=RTPS_PDF,
        excerpt="heartbeatResponseDelay.nanosec = 500 * 1000 * 1000; // 500 milliseconds",
        time_value="500", parameter="Reader::heartbeatResponseDelay",
        time_source="DDSI-RTPS 2.5 RTPS Reader default timing-related value",
        basis="NORMATIVE_DEFAULT", formula="G* (heartbeat_response_generation_started_500 -> (G [0,500) (!heartbeat_acknack_sent) && F [0,500] (heartbeat_acknack_sent || heartbeat_response_generation_superseded || rtps_writer_unmatched || rtps_reader_stopped)))",
        aps={
            "heartbeat_response_generation_started_500":"A fresh HEARTBEAT enters must_send_ack and restart_timer arms this WriterProxy generation with heartbeatResponseDelay=500 ms.",
            "heartbeat_acknack_sent":"The heartbeat-response callback is observed handing the correlated ACKNACK to the RTPS send path; logical deadline and actual callback/send time are both retained.",
            "heartbeat_response_generation_superseded":"A newer qualifying HEARTBEAT restarts/coalesces the WriterProxy timer and closes this generation before starting another projected word.",
            "rtps_writer_unmatched":"The WriterProxy is removed before response and discharges the window.",
            "rtps_reader_stopped":"The local reader is disabled/deleted before response.",
        },
        correlation="reader GUID + writer GUID + HEARTBEAT count; sequence-number set is a field",
        source_repo="eProsima/Fast-DDS", source_commit=FASTDDS,
        source_path="src/cpp/rtps/reader/WriterProxy.cpp", source_symbol="WriterProxy::process_heartbeat", source_lines="535-593",
        hook="Set ReaderTimes.heartbeat_response_delay=500 ms; emit trigger at restart_timer. A later restart first emits superseded. Emit ACKNACK only after send_acknack is called, stamp with the logical deadline, and retain callback/send time separately.",
        positive=tr((0,"heartbeat_response_generation_started_500"),(500,"heartbeat_acknack_sent"),(501,"")),
        negative=tr((0,"heartbeat_response_generation_started_500"),(499,"heartbeat_acknack_sent"),(501,"")),
        projection="Project exactly one WriterProxy heartbeat timer generation; newer HEARTBEAT restart, unmatch, or reader stop closes it explicitly.",
        triggerability="HIGH",
        limitations="Fast-DDS v3.3.0 stock ReaderTimes is 5 ms. The harness explicitly selects 500 ms; actual scheduler delay is recorded separately and never hidden as epsilon.",
        additional_negative={
            "late_or_missing": tr((0,"heartbeat_response_generation_started_500"),(501,"heartbeat_acknack_sent"),(502,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("heartbeat_response_generation_superseded", "rtps_writer_unmatched", "rtps_reader_stopped"),
        aux_sources={
            "response": ("src/cpp/rtps/reader/WriterProxy.cpp", "535-548", "perform_heartbeat_response hands ACKNACK to the send path."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: restart/coalescing is an explicit generation supersession, reader stop is covered, and both early and late/missing response traces are present.",
    ),
    card(
        pid="RTPS-DISC-01", protocol="DDS/RTPS", extension="DDSI-RTPS SPDP reference-default profile",
        title="Periodic SPDP announcement interval is 30 seconds", category="participant discovery announcement",
        natural="完成启动期 directed announcements 后，在 SPDP reference-default profile 中，相邻周期性 multicast announcement 不得早于 30000 ms，且下一次应在 30000 ms 发送。",
        strength="SPECIFIED DEFAULT", standard="OMG DDSI-RTPS", version="2.5 formal/2022-04-01",
        section="9.6.2.4", standard_url=RTPS_PDF,
        excerpt="The default rate by which SPDP periodic announcements are sent equals 30 seconds",
        time_value="30000", parameter="SPDPbuiltinParticipantWriter.resendPeriod",
        time_source="DDSI-RTPS 2.5 SPDP default announcement rate",
        basis="NORMATIVE_DEFAULT", formula="G* (periodic_spdp_generation_started_30000 -> (G [0,30000) (!next_periodic_spdp_announcement_sent) && F [0,30000] (next_periodic_spdp_announcement_sent || spdp_period_generation_superseded || local_participant_stopped)))",
        aps={
            "periodic_spdp_generation_started_30000":"A steady-state non-directed SPDP announcement is sent and the next periodic generation is armed with resendPeriod=30 s.",
            "next_periodic_spdp_announcement_sent":"The next steady-state non-directed periodic SPDP announcement is actually handed to announceParticipantState(false); logical deadline and callback/send time are retained.",
            "spdp_period_generation_superseded":"A configuration/reset operation replaces the scheduled periodic generation before its deadline.",
            "local_participant_stopped":"The local DomainParticipant is disabled/deleted before the next period.",
        },
        correlation="domainId + local participant GUID prefix; directed destination GUIDs remain fields and are filtered out",
        source_repo="eProsima/Fast-DDS", source_commit=FASTDDS,
        source_path="src/cpp/rtps/builtin/discovery/participant/PDP.cpp", source_symbol="PDP::enable", source_lines="512-545",
        hook="After startup announcements are exhausted and resendPeriod=30 s is verified, each observed announceParticipantState(false) closes the old generation and arms a new one. Stamp an observed next send with the stored logical deadline; retain actual callback time separately.",
        positive=tr((0,"periodic_spdp_generation_started_30000"),(30000,"next_periodic_spdp_announcement_sent"),(30001,"")),
        negative=tr((0,"periodic_spdp_generation_started_30000"),(29999,"next_periodic_spdp_announcement_sent"),(30001,"")),
        projection="Project one steady-state periodic generation for one local participant; exclude startup bursts/directed sends and explicitly close on reconfiguration or participant stop.",
        triggerability="HIGH",
        limitations="Fast-DDS v3.3.0 stock announcement period is 3 s. The benchmark explicitly selects the RTPS 30 s reference profile; actual callback delay remains diagnostic rather than an undocumented tolerance.",
        additional_negative={
            "late_or_missing": tr((0,"periodic_spdp_generation_started_30000"),(30001,"next_periodic_spdp_announcement_sent"),(30002,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("spdp_period_generation_superseded", "local_participant_stopped"),
        aux_sources={
            "interval": ("src/cpp/rtps/builtin/discovery/participant/PDP.cpp", "1534-1545", "Steady-state timer interval is updated from leaseDuration_announcementperiod."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: the main hook now covers the actual periodic send callback, interval configuration is a second fixed hook, and early/late plus supersession are explicit.",
    ),
    card(
        pid="RTPS-DISC-02", protocol="DDS/RTPS", extension="DDSI-RTPS remote participant with omitted lease PID",
        title="Remote participant is not lease-removed before the 100-second default lease", category="participant lease safety",
        natural="远端 SPDP 未携带 lease-duration PID、使用独立 participant 100000 ms 默认租约时，在该 lease generation 到期前不得仅因 lease expiry 删除；规范不要求恰在 100000 ms 完成物理删除。",
        strength="DEFAULT LEASE / NO-EARLY SAFETY", standard="OMG DDSI-RTPS", version="2.5 formal/2022-04-01",
        section="8.5.5.2; 9.6.3 Table 9.18", standard_url=RTPS_PDF,
        excerpt="SPDPdiscoveredParticipantData::leaseDuration {100, 0}",
        time_value="100000", parameter="ParticipantProxy::leaseDuration default when PID omitted",
        time_source="DDSI-RTPS 2.5 PID_PARTICIPANT_LEASE_DURATION default {100,0}",
        basis="NORMATIVE_DEFAULT", formula="G* (remote_participant_default_lease_started -> G [0,100000) (!remote_participant_removed_due_to_lease || remote_spdp_refresh_supersedes_lease || remote_lease_generation_cancelled))",
        aps={
            "remote_participant_default_lease_started":"A valid SPDP sample without PID_PARTICIPANT_LEASE_DURATION creates/renews an independent, non-privileged-dependent remote participant using 100 s.",
            "remote_participant_removed_due_to_lease":"Lease expiration, rather than explicit disposal or another cause, invokes deletion/reconfiguration for that proxy participant.",
            "remote_spdp_refresh_supersedes_lease":"A newer valid SPDP sample closes this lease generation and starts a separately projected 100 s generation.",
            "remote_lease_generation_cancelled":"Explicit participant disposal or harness reset ends this generation without asserting lease expiry.",
        },
        correlation="domain + remote participant GUID prefix + SPDP sequence number; GUID is a field",
        source_repo="eclipse-cyclonedds/cyclonedds", source_commit=CYCLONE,
        source_path="src/core/ddsi/src/q_lease.c", source_symbol="check_and_handle_lease_expiration", source_lines="218-292",
        hook="Emit start only after the omitted PID is defaulted to 100 s and privileged/dependency postponement is excluded. A refresh/cancel closes this word. Emit lease-removal cause immediately before ddsi_delete_proxy_participant_by_guid; do not require a callback at exactly 100 s.",
        positive=tr((0,"remote_participant_default_lease_started"),(100000,""),(100001,"")),
        negative=tr((0,"remote_participant_default_lease_started"),(99999,"remote_participant_removed_due_to_lease"),(100001,"")),
        projection="Project one lease generation for one independent remote participant; SPDP refresh emits supersession and opens another word, while explicit disposal emits cancellation.",
        triggerability="MEDIUM",
        limitations="This is deliberately safety-only: RTPS permits considering the participant gone after the lease but does not impose exact physical removal at 100 s. CycloneDDS privileged/dependency postponement cases are trigger-false and excluded.",
        cancellation_aps=("remote_spdp_refresh_supersedes_lease", "remote_lease_generation_cancelled"),
        aux_sources={
            "default_lease": ("src/core/ddsi/src/q_ddsi_discovery.c", "835-840", "Omitted PID_PARTICIPANT_LEASE_DURATION defaults to DDS_SECS(100)."),
            "dependency_exception": ("src/core/ddsi/src/q_lease.c", "247-281", "Privileged participant dependency can postpone lease handling by 200 ms."),
        },
        timer_semantics="The formula observes only cause-specific early removal against the stored 100 s lease deadline. Callback/removal after the deadline is recorded but is not a protocol liveness verdict.",
        audit_note="Original audit disposition=FIX; fixed after audit: unsupported exact-removal liveness was removed; the card is now a cause-specific no-early safety property with refresh/cancel generation boundaries and fixed default/exception hooks.",
    ),
    card(
        pid="DDS-WRITE-01", protocol="DDS/RTPS", extension="DDS 1.4 reliable DataWriter default QoS",
        title="Blocked reliable write returns within 100 ms", category="DataWriter blocking bound",
        natural="使用 DDS 默认 max_blocking_time=100 ms 的 RELIABLE DataWriter 在资源压力下进入阻塞后，write 应在 100 ms 内以成功、TIMEOUT 或规范允许的 OUT_OF_RESOURCES 返回。",
        strength="NORMATIVE MAXIMUM", standard="OMG Data Distribution Service", version="DDS 1.4 formal/2015-04-10",
        section="2.2.2.4.2.11; 2.2.3.14", standard_url=DDS_PDF,
        excerpt="The default max_blocking_time=100ms",
        time_value="100", parameter="ReliabilityQosPolicy.max_blocking_time",
        time_source="DDS 1.4 default Reliability QoS max_blocking_time",
        basis="NORMATIVE_DEFAULT", formula="G* (reliable_write_resource_wait_started_default -> F [0,100] (write_returned_from_blocking))",
        aps={
            "reliable_write_resource_wait_started_default":"A RELIABLE DataWriter with max_blocking_time=100 ms reaches DataWriterHistory::prepare_change and is about to wait_for_acknowledgement because resource/history space is unavailable.",
            "write_returned_from_blocking":"The correlated write returns OK, TIMEOUT, or the explicitly permitted OUT_OF_RESOURCES result.",
        },
        correlation="DataWriter entity GUID + calling thread operation sequence + instance handle as a field",
        source_repo="eProsima/Fast-DDS", source_commit=FASTDDS,
        source_path="src/cpp/fastdds/publisher/DataWriterHistory.cpp", source_symbol="DataWriterHistory::prepare_change", source_lines="148-234",
        hook="Emit trigger immediately before wait_for_acknowledgement at lines 230-234 after confirming the 100 ms QoS/deadline snapshot. Emit the correlated API return at DataWriterImpl; serialization/precondition time before the resource wait is not mislabeled as waiting time.",
        positive=tr((0,"reliable_write_resource_wait_started_default"),(100,"write_returned_from_blocking"),(101,"")),
        negative=tr((0,"reliable_write_resource_wait_started_default"),(101,"")),
        projection="Project one synchronous write operation and exactly one actual resource-wait episode; precondition/serialization work before waiting is excluded, and the API return ends it.",
        observability="WHITEBOX", triggerability="MEDIUM",
        limitations="The standard permits immediate OUT_OF_RESOURCES in hopeless-resource cases. The formula constrains only an observed resource wait and does not treat total serialization/function execution as max_blocking_time.",
        additional_positive={
            "immediate_out_of_resources": tr((0,"reliable_write_resource_wait_started_default"),(1,"write_returned_from_blocking"),(2,"")),
        },
        negative_kind="LATE_OR_MISSING_RETURN",
        cancellation_aps=(),
        aux_sources={
            "deadline_and_return": ("src/cpp/fastdds/publisher/DataWriterImpl.cpp", "1003-1071", "The caller computes the absolute max-blocking deadline, enters history, and maps failure to RETCODE_TIMEOUT."),
            "templated_wait_caller": ("src/cpp/fastdds/publisher/DataWriterHistory.hpp", "142-169", "The filtered-writer path also calls prepare_change with the same deadline."),
        },
        timer_semantics="The trigger is the actual resource-wait entry. The timed word uses actual wait-entry and API-return times; the earlier absolute deadline computed at write entry is retained to show the implementation is at least as strict as the 100 ms wait bound.",
        audit_note="Original audit disposition=FIX; fixed after audit: the primary source now proves the real wait predicate; total write execution is no longer conflated with resource waiting, and caller/deadline/return hooks plus immediate OUT_OF_RESOURCES coverage were added.",
    ),
]


CANTP_PDF = "https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_CANTransportLayer.pdf"
DCM_PDF = "https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DiagnosticCommunicationManager.pdf"
CAN_UDS = [
    card(
        pid="CANTP-NBS-01", protocol="CAN/UDS", extension="AUTOSAR CAN-TP sender, python-can-isotp default profile",
        title="Waiting for FlowControl ends or aborts at N_Bs=1000 ms", category="CAN-TP N_Bs timeout",
        natural="python-can-isotp 默认 N_Bs profile 中，发送方进入 WAIT_FC 后，1000 ms 前不得以 N_Bs 超时中止；到期前必须收到 FlowControl 或执行中止。",
        strength="SHALL", standard="AUTOSAR SWS CAN Transport Layer", version="R24-11", section="7.2.3 [SWS_CanTp_00315-SWS_CanTp_00316]; 10.2 [ECUC_CanTp_00264]",
        standard_url=CANTP_PDF, excerpt="abort transmission of this message and notify the upper layer",
        time_value="1000", parameter="N_Bs / rx_flowcontrol_timeout",
        time_source="python-can-isotp default rx_flowcontrol_timeout=1000 ms; AUTOSAR defines N_Bs as configurable with no default",
        basis="IMPLEMENTATION_PROFILE", formula="G* (n_bs_timer_generation_started_1000 -> (G [0,1000) (!tx_aborted_n_bs) && F [0,1000] (flow_control_received || tx_aborted_n_bs || n_bs_generation_cancelled)))",
        aps={
            "n_bs_timer_generation_started_1000":"The implementation enters WAIT_FC and starts timer_rx_fc with configured 1000 ms; adapter records whether this precedes an AUTOSAR Tx-confirmation start.",
            "flow_control_received":"A valid correlated FC(CTS/WAIT/OVFLW) is decoded before N_Bs expiry; WAIT begins a new correlated wait window.",
            "tx_aborted_n_bs":"FlowControlTimeoutError is raised and _stop_sending(success=False) executes for that transfer.",
            "n_bs_generation_cancelled":"Application cancellation, transport reset, profile change, or harness reset ends this timer generation without an N_Bs timeout.",
        },
        correlation="ISO-TP addressing tuple + CAN channel + active send-request generation; CAN IDs and sequence numbers remain fields",
        source_repo="pylessard/python-can-isotp", source_commit=ISOTP,
        source_path="isotp/protocol.py", source_symbol="def _process_tx", source_lines="987-1051",
        hook="Emit trigger at _start_rx_fc_timer and record the implementation start plus any external Tx-confirmation timestamp. FC(WAIT) first satisfies the old word, then starts a new word. Emit abort only when the source action is observed; stamp its logical deadline and keep actual callback time.",
        positive=tr((0,"n_bs_timer_generation_started_1000"),(1000,"tx_aborted_n_bs"),(1001,"")),
        negative=tr((0,"n_bs_timer_generation_started_1000"),(999,"tx_aborted_n_bs"),(1001,"")),
        projection="Project one segmented-send N_Bs timer generation; FC(WAIT) closes it and creates another word, CTS/OVFLW/abort/cancel closes it without overlap.",
        observability="WHITEBOX", triggerability="HIGH",
        limitations="1000 ms is a python-can-isotp profile, not an AUTOSAR/ISO default. AUTOSAR starts N_Bs from Tx confirmation, while this library may start earlier; both timestamps are retained and the claim is explicitly implementation-profile-scoped. Timer::is_timed_out uses strict >, so the exact-bound oracle may expose a source discrepancy.",
        additional_negative={
            "late_or_missing": tr((0,"n_bs_timer_generation_started_1000"),(1001,"tx_aborted_n_bs"),(1002,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("flow_control_received", "n_bs_generation_cancelled"),
        aux_sources={
            "timer_start": ("isotp/protocol.py", "1250-1252", "_start_rx_fc_timer creates and starts the 1000 ms timer."),
            "profile_configuration": ("isotp/protocol.py", "349-354", "python-can-isotp default N_Bs/N_Cr profile values."),
            "timeout_predicate": ("isotp/tools.py", "48-52", "Timer::is_timed_out uses elapsed > timeout."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: AUTOSAR start clause, implementation-vs-Tx-confirmation start, cancellation, per-generation projection, fixed helper hooks, and early/late traces are explicit.",
    ),
    card(
        pid="CANTP-NCR-01", protocol="CAN/UDS", extension="AUTOSAR CAN-TP receiver, python-can-isotp default profile",
        title="Waiting for ConsecutiveFrame ends or aborts at N_Cr=1000 ms", category="CAN-TP N_Cr timeout",
        natural="python-can-isotp 默认 N_Cr profile 中，接收方等待下一 ConsecutiveFrame 后，1000 ms 前不得以 N_Cr 超时中止；到期前必须收到下一帧或执行中止。",
        strength="SHALL", standard="AUTOSAR SWS CAN Transport Layer", version="R24-11", section="7.2.2 [SWS_CanTp_00312-SWS_CanTp_00313]; 10.2 [ECUC_CanTp_00279]",
        standard_url=CANTP_PDF, excerpt="abort reception and notify the upper layer of this failure",
        time_value="1000", parameter="N_Cr / rx_consecutive_frame_timeout",
        time_source="python-can-isotp default rx_consecutive_frame_timeout=1000 ms; AUTOSAR defines N_Cr as configurable with no default",
        basis="IMPLEMENTATION_PROFILE", formula="G* (n_cr_timer_generation_started_1000 -> (G [0,1000) (!rx_aborted_n_cr) && F [0,1000] (consecutive_frame_received || rx_aborted_n_cr || n_cr_generation_cancelled)))",
        aps={
            "n_cr_timer_generation_started_1000":"A valid FirstFrame/non-final ConsecutiveFrame, or the local FC-send path, starts timer_rx_cf with configured 1000 ms; start provenance is recorded.",
            "consecutive_frame_received":"The next correctly sequenced correlated ConsecutiveFrame is accepted; if more data remains, it starts a new N_Cr window.",
            "rx_aborted_n_cr":"ConsecutiveFrameTimeoutError is raised and _stop_receiving executes for this transfer.",
            "n_cr_generation_cancelled":"Receive reset, transfer cancellation/completion by another terminal cause, profile change, or harness reset ends this generation.",
        },
        correlation="ISO-TP addressing tuple + CAN channel + receive generation + expected sequence number as a field",
        source_repo="pylessard/python-can-isotp", source_commit=ISOTP,
        source_path="isotp/protocol.py", source_symbol="def _check_timeouts_rx", source_lines="890-894",
        hook="Emit start at _start_rx_cf_timer with its provenance; accepted CF is emitted only after sequence validation and first satisfies the old word before starting another. Emit abort only when observed, stamp its logical deadline, and retain callback time.",
        positive=tr((0,"n_cr_timer_generation_started_1000"),(1000,"rx_aborted_n_cr"),(1001,"")),
        negative=tr((0,"n_cr_timer_generation_started_1000"),(999,"rx_aborted_n_cr"),(1001,"")),
        projection="Project one segmented-receive N_Cr generation; each accepted non-final CF closes it and creates another word, while completion/error/cancel ends it.",
        observability="WHITEBOX", triggerability="HIGH",
        limitations="1000 ms is a python-can-isotp profile, not an AUTOSAR/ISO default. The library timer may start in the local FC path rather than an external transmission confirmation, and strict elapsed > timeout may expose an exact-bound discrepancy.",
        additional_negative={
            "late_or_missing": tr((0,"n_cr_timer_generation_started_1000"),(1001,"rx_aborted_n_cr"),(1002,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("consecutive_frame_received", "n_cr_generation_cancelled"),
        aux_sources={
            "accepted_cf": ("isotp/protocol.py", "895-984", "Sequence validation and accepted non-final CF restart path."),
            "timer_start": ("isotp/protocol.py", "1254-1256", "_start_rx_cf_timer creates and starts the N_Cr timer."),
            "profile_configuration": ("isotp/protocol.py", "349-354", "python-can-isotp default N_Bs/N_Cr profile values."),
            "timeout_predicate": ("isotp/tools.py", "48-52", "Timer::is_timed_out uses elapsed > timeout."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: AUTOSAR start clause, timer-start provenance, cancellation, accepted-CF/restart hook, per-generation projection, and early/late traces were added.",
    ),
    card(
        pid="UDS-P2-01", protocol="CAN/UDS", extension="AUTOSAR DCM server, iso14229 default P2 profile",
        title="Initial diagnostic response or NRC 0x78 arrives within P2=50 ms", category="UDS P2 server response",
        natural="iso14229 默认 server P2=50 ms 时，服务器接收并开始处理诊断请求后，应在 50 ms 内发送最终响应；若仍需处理，则发送 NRC 0x78。",
        strength="SHALL", standard="AUTOSAR SWS Diagnostic Communication Manager", version="R24-11", section="7.2.4.6 [SWS_Dcm_00024]",
        standard_url=DCM_PDF, excerpt="shall send a negative response with NRC 0x78 when reaching the response time",
        time_value="50", parameter="P2ServerMax profile",
        time_source="driftregion/iso14229 UDS_SERVER_DEFAULT_P2_MS=50 with profile adjustment=0; AUTOSAR makes P2ServerMax and adjustment configurable",
        basis="IMPLEMENTATION_PROFILE", formula="G* (uds_request_processing_started_p2_50_adjust0 -> F [0,50] (uds_final_response_sent || uds_nrc78_sent || uds_p2_generation_cancelled))",
        aps={
            "uds_request_processing_started_p2_50_adjust0":"A complete valid request is accepted by UDSServerPoll with srv->p2_ms=50, normative server adjustment=0, and response suppression not selected; adapter snapshots request tick and implementation p2_timer.",
            "uds_final_response_sent":"UDSTpSend is invoked with a final positive or non-0x78 negative response for the correlated request.",
            "uds_nrc78_sent":"UDSTpSend is invoked with NRC RequestCorrectlyReceived-ResponsePending (0x78) for that request.",
            "uds_p2_generation_cancelled":"Transport teardown, server/harness reset, or request cancellation makes this request generation unobservable before a response handoff.",
        },
        correlation="transport connection + tester/source address + request generation + SID/subfunction as fields",
        source_repo="driftregion/iso14229", source_commit=ISO14229,
        source_path="src/server.c", source_symbol="UDSServerPoll", source_lines="1581-1660",
        hook="Emit trigger after lines 1653-1658 accept/evaluate the request and snapshot request+50 plus srv->p2_timer. Emit response only at actual UDSTpSend handoff; classify NRC 0x78 versus final. Suppressed-positive requests are trigger-false; teardown/reset emits cancellation.",
        positive=tr((0,"uds_request_processing_started_p2_50_adjust0"),(50,"uds_nrc78_sent"),(51,"")),
        negative=tr((0,"uds_request_processing_started_p2_50_adjust0"),(51,"")),
        projection="Project one accepted server request generation; repeated/new requests cannot share a word, and teardown/reset emits explicit cancellation.",
        observability="HYBRID", triggerability="HIGH",
        limitations="50 ms is the locked iso14229 profile and this card explicitly assumes server adjustment=0. Other DCMs must instantiate active P2ServerMax-adjust. The source's p2_timer can predate request acceptance, so both the normative request+50 deadline and implementation snapshot are retained.",
        negative_kind="LATE_OR_MISSING_RESPONSE",
        cancellation_aps=("uds_p2_generation_cancelled",),
        aux_sources={
            "profile_configuration": ("src/config.h", "42-49", "iso14229 server P2=50 ms and P2*=5000 ms defaults."),
            "deadline_predicate": ("src/util.h", "13", "UDSTimeAfter uses a strict greater-than comparison."),
            "response_handoff": ("src/server.c", "1617-1621", "UDSTpSend handoff for the current response."),
        },
        timer_semantics="The formula uses request-acceptance tick plus 50 ms as the normative profile deadline. The implementation p2_timer and actual UDSTpSend time are retained separately; a poll callback is not itself a response.",
        audit_note="Original audit disposition=FIX; fixed after audit: adjustment=0 is a trigger precondition, request and response hooks are in fixed ranges, cancellation is explicit, and normative versus implementation deadlines are separated.",
    ),
    card(
        pid="UDS-P2STAR-01", protocol="CAN/UDS", extension="AUTOSAR DCM server, iso14229 default P2* profile",
        title="After NRC 0x78 another response arrives within P2*=5000 ms", category="UDS P2-star response",
        natural="iso14229 默认 P2*=5000 ms 时，服务器发送 NRC 0x78 后，应在 5000 ms 内发送最终响应或新的 NRC 0x78。",
        strength="SHALL", standard="AUTOSAR SWS Diagnostic Communication Manager", version="R24-11", section="7.2.4.6 [SWS_Dcm_00024]",
        standard_url=DCM_PDF, excerpt="when reaching the response time DcmDspSessionP2StarServerMax",
        time_value="5000", parameter="P2StarServerMax profile",
        time_source="driftregion/iso14229 UDS_SERVER_DEFAULT_P2_STAR_MS=5000; AUTOSAR makes P2* session-configurable",
        basis="IMPLEMENTATION_PROFILE", formula="G* (uds_nrc78_sent_p2star_5000_adjust0 -> F [0,5000] (uds_final_response_after_nrc78 || uds_nrc78_repeated || uds_p2star_generation_cancelled))",
        aps={
            "uds_nrc78_sent_p2star_5000_adjust0":"An NRC 0x78 is successfully handed to transport for a request with p2_star_ms=5000 and server adjustment=0.",
            "uds_final_response_after_nrc78":"A final correlated response is handed to the transport after that NRC 0x78.",
            "uds_nrc78_repeated":"Another correlated NRC 0x78 is handed to the transport, starting the next P2* window.",
            "uds_p2star_generation_cancelled":"Transport teardown, server/harness reset, or explicit request cancellation ends this response generation.",
        },
        correlation="same server request generation + tester/source address; consecutive NRCs are ordered fields",
        source_repo="driftregion/iso14229", source_commit=ISO14229,
        source_path="src/server.c", source_symbol="UDSServerPoll", source_lines="1598-1638",
        hook="Classify each successful UDSTpSend at lines 1617-1637; a repeated NRC atomically satisfies the old word before opening another. Store the P2* logical deadline and actual handoff time; poll callback time is not the response event.",
        positive=tr((0,"uds_nrc78_sent_p2star_5000_adjust0"),(5000,"uds_final_response_after_nrc78"),(5001,"")),
        negative=tr((0,"uds_nrc78_sent_p2star_5000_adjust0"),(5001,"")),
        projection="Project one post-NRC response generation; each repeated NRC satisfies it and starts a separate word for the same request, while teardown/reset cancels it.",
        observability="HYBRID", triggerability="HIGH",
        limitations="The implementation normally repeats NRC 0x78 at 0.3*P2*=1500 ms. 5000 ms and adjustment=0 are locked implementation preconditions, not AUTOSAR universal defaults.",
        audit_status="APPROVE",
        audit_note="Approved with caveat: adjustment=0 and successful transport handoff are explicit, and every repeated NRC closes one generation before starting the next.",
        cancellation_aps=("uds_nrc78_repeated", "uds_p2star_generation_cancelled"),
        aux_sources={
            "profile_configuration": ("src/config.h", "42-49", "iso14229 server P2/P2* defaults."),
            "deadline_predicate": ("src/util.h", "13", "UDSTimeAfter strict comparison used by polling."),
        },
        timer_semantics="The logical P2* deadline is derived from successful NRC handoff plus 5000 ms. Actual repeated/final response handoff is the observed action; callback/poll time is retained separately.",
    ),
    card(
        pid="UDS-S3-01", protocol="CAN/UDS", extension="AUTOSAR DCM non-default session, driftregion/iso14229 S3 profile",
        title="Idle non-default session returns to default at S3=5100 ms", category="UDS S3 session timeout",
        natural="锁定 iso14229 S3=5100 ms profile 后，非默认会话不得在 5100 ms 前因 S3 timeout 回到默认会话；到 deadline 应因 S3 切回，或由 owner 有效活动重置、显式会话操作/停止取消该 generation。",
        strength="SHALL", standard="AUTOSAR SWS Diagnostic Communication Manager", version="R24-11", section="7.2.4.13 [SWS_Dcm_01670]; 7.2.4.14 [SWS_Dcm_01680]",
        standard_url=DCM_PDF, excerpt="If the S3Server elapses, the Dcm shall switch back to default session",
        time_value="5100", parameter="S3Server implementation profile",
        time_source="driftregion/iso14229 UDS_SERVER_DEFAULT_S3_MS=5100; treated as a locked configured/overwrite profile",
        basis="IMPLEMENTATION_PROFILE", formula="G* (non_default_session_idle_started_s3_5100 -> (G [0,5100) (!default_session_entered_due_to_s3) && F [0,5100] (default_session_entered_due_to_s3 || s3_resetting_activity_received || s3_generation_cancelled)))",
        aps={
            "non_default_session_idle_started_s3_5100":"A non-default session begins a fresh idle S3 window with srv->s3_ms=5100 after a qualifying activity/reset.",
            "default_session_entered_due_to_s3":"UDSServerPoll changes sessionType to UDS_LEV_DS_DS specifically because the S3 timer elapsed.",
            "s3_resetting_activity_received":"A valid request from the owning tester/connection that normatively resets S3 is processed before expiry.",
            "s3_generation_cancelled":"Explicit session change, server stop, profile change, or harness reset ends this idle generation without an S3-timeout cause.",
        },
        correlation="server instance + transport connection + tester/source address + non-default session epoch",
        source_repo="driftregion/iso14229", source_commit=ISO14229,
        source_path="src/server.c", source_symbol="UDSServerPoll", source_lines="1581-1588",
        hook="Start only from a fixed s3_session_timeout_timer assignment owned by the current tester/session. A reset first satisfies the old word and then opens another. Emit cause-specific timeout at lines 1583-1587, stamp logical deadline, and retain actual poll time.",
        positive=tr((0,"non_default_session_idle_started_s3_5100"),(5100,"default_session_entered_due_to_s3"),(5101,"")),
        negative=tr((0,"non_default_session_idle_started_s3_5100"),(5099,"default_session_entered_due_to_s3"),(5101,"")),
        projection="Project one owner-scoped non-default-session idle generation; owner reset creates another word, while explicit session action/stop/profile change cancels it.",
        observability="WHITEBOX", triggerability="HIGH",
        limitations="AUTOSAR's unoverwritten default is 5000 ms; 5100 ms is an iso14229 configured profile. UDSTimeAfter is strict >, so the exact 5100 ms conformance oracle may expose a one-tick implementation discrepancy without adding tolerance.",
        additional_negative={
            "late_or_missing": tr((0,"non_default_session_idle_started_s3_5100"),(5101,"default_session_entered_due_to_s3"),(5102,"")),
        },
        negative_kind="EARLY_ACTION",
        cancellation_aps=("s3_resetting_activity_received", "s3_generation_cancelled"),
        aux_sources={
            "session_entry_start": ("src/server.c", "59-66", "Entering a non-default session assigns the S3 deadline."),
            "tester_present_reset": ("src/server.c", "1304-1317", "Valid TesterPresent assigns a fresh S3 deadline."),
            "initialization": ("src/server.c", "1569-1574", "Server initialization loads the S3 profile and deadline."),
            "profile_configuration": ("src/config.h", "47-53", "iso14229 P2*/S3 default profile constants."),
            "deadline_predicate": ("src/util.h", "13", "UDSTimeAfter uses strict greater-than."),
        },
        audit_note="Original audit disposition=FIX; fixed after audit: timeout cause is separated from explicit default-session entry, all start/reset/cancel hooks are fixed, and early plus late/missing boundary oracles are included.",
    ),
    card(
        pid="UDS-S3-02", protocol="CAN/UDS", extension="AUTOSAR concurrent TesterPresent, driftregion/iso14229 S3 profile",
        title="Valid TesterPresent restarts the 5100 ms S3 window", category="UDS TesterPresent keep-alive",
        natural="同一连接上的有效 TesterPresent 被处理后，非默认会话在新的 5100 ms S3 窗口内不得提前切回默认会话；若无后续重置活动，应在窗口结束时切回。",
        strength="SHALL", standard="AUTOSAR SWS Diagnostic Communication Manager", version="R24-11", section="7.2.4.3 [SWS_Dcm_01666-SWS_Dcm_01667]",
        standard_url=DCM_PDF, excerpt="The purpose is to keep the non-default session active and reset the S3 timer",
        time_value="5100", parameter="S3Server after TesterPresent",
        time_source="driftregion/iso14229 S3 profile 5100 ms, restarted by Handle_0x3E_TesterPresent",
        basis="IMPLEMENTATION_PROFILE", formula="G* (valid_tester_present_restarts_s3_5100 -> (G [0,5100) (!default_session_entered_after_tester_present) && F [0,5100] (default_session_entered_after_tester_present || subsequent_s3_resetting_activity)))",
        aps={
            "valid_tester_present_restarts_s3_5100":"Handle_0x3E accepts subfunction 0x00/0x80 on the connection owning the non-default session and assigns now+5100 to the S3 timer.",
            "default_session_entered_after_tester_present":"That session later changes to default because the restarted S3 timer elapsed.",
            "subsequent_s3_resetting_activity":"A later qualifying request resets S3 again and ends this TesterPresent-derived window.",
        },
        correlation="owning DcmDslConnection analogue + tester/source address + session epoch; SID/subfunction are fields",
        source_repo="driftregion/iso14229", source_commit=ISO14229,
        source_path="src/server.c", source_symbol="Handle_0x3E_TesterPresent", source_lines="1304-1317",
        hook="Emit trigger only after line 1313 resets s3_session_timeout_timer for a valid TesterPresent; emit session defaulting in UDSServerPoll:1583-1587.",
        positive=tr((0,"valid_tester_present_restarts_s3_5100"),(5100,"default_session_entered_after_tester_present"),(5101,"")),
        negative=tr((0,"valid_tester_present_restarts_s3_5100"),(5099,"default_session_entered_after_tester_present"),(5101,"")),
        projection="project one accepted TesterPresent on the connection that owns the non-default session; a later valid reset event starts a new window",
        observability="WHITEBOX", triggerability="HIGH",
        limitations="The AUTOSAR concurrent-TesterPresent rule is connection-scoped. driftregion/iso14229 does not model multiple DcmDslConnections, so multi-tester experiments require adapter-side ownership enforcement or a different SUT.",
        audit_status="REJECT_OR_FIX",
        audit_note="Rejected from proposals: this is a logical subset of UDS-S3-01 and does not test the cited foreign/owning-connection TesterPresent obligation on a multi-connection SUT.",
    ),
]

# Retain the rejected source record above so the exclusion decision remains reproducible,
# but never emit it as a proposal or count it toward the catalogue.
CAN_UDS = [p for p in CAN_UDS if p["independent_audit_status"] != "REJECT_OR_FIX"]


MODBUS_TCP: list[dict[str, object]] = []
AUDIT_REPORT = "analysis/protocol_fuzzing_study/_audit/industrial_audit.md"

REJECTED_CANDIDATES: dict[str, list[dict[str, str]]] = {
    "can_uds": [
        {
            "id": "UDS-S3-02",
            "independent_audit_status": "REJECT_OR_FIX",
            "decision_code": "DUPLICATE_OBLIGATION_AND_UNSUPPORTED_MULTI_CONNECTION",
            "reason": (
                "Current formula is a TesterPresent-specialized subset of UDS-S3-01 and never "
                "tests the cited owner-versus-foreign DcmDslConnection obligation; the locked SUT "
                "does not model multiple DcmDslConnections."
            ),
            "repair_gate": (
                "Use a multi-connection SUT or an explicit owner/foreign model and test that a "
                "foreign TesterPresent does not reset the owner's S3 generation."
            ),
        }
    ],
    "modbus_tcp": [
        {
            "id": "MODBUS-TCP-01",
            "independent_audit_status": "REJECT_OR_FIX",
            "decision_code": "NO_PROTOCOL_BOUND_AND_INCORRECT_IMPLEMENTATION_ORACLE",
            "reason": (
                "MODBUS/TCP V1.0b deliberately defines no universal response time. In libmodbus, "
                "response_timeout governs the initial read and byte_timeout is reloaded for "
                "subsequent chunks, so a full confirmation need not complete within 500 ms."
            ),
            "repair_gate": (
                "Keep only an implementation appendix split into initial-response and inter-byte "
                "timer generations; it cannot count as a normative Modbus/TCP property."
            ),
        }
    ],
}


def evidence_manifests() -> dict[str, dict[str, object]]:
    return {
        "can_uds": {
            "protocol": "AUTOSAR CAN-TP/DCM profiles (catalogue label CAN/UDS)",
            "access_date": "2026-07-13",
            "status": "COMPLETE_WITH_INDEPENDENT_AUDIT",
            "independent_audit_report": AUDIT_REPORT,
            "scope": (
                "Public AUTOSAR R24-11 obligations instantiated with locked python-can-isotp and "
                "driftregion/iso14229 profiles. No paid ISO 15765/14229 text or secondary paraphrase "
                "is used as normative evidence; claims must not be generalized to all ISO implementations."
            ),
            "proposal_summary": {"emitted": len(CAN_UDS), "approve": 1, "fix_applied": 4, "rejected": 1},
            "standards": [
                {
                    "title": "AUTOSAR SWS CAN Transport Layer",
                    "version": "R24-11",
                    "url": CANTP_PDF,
                    "sha256": "7334d633b02c443aacbe0ca25e20c319e977104eeb4bf8e67ac0358cfea34a22",
                    "sections_reviewed": [
                        "7.2.2 [SWS_CanTp_00312-SWS_CanTp_00313]",
                        "7.2.3 [SWS_CanTp_00315-SWS_CanTp_00316]",
                        "10.2 [ECUC_CanTp_00264, ECUC_CanTp_00279]",
                    ],
                },
                {
                    "title": "AUTOSAR SWS Diagnostic Communication Manager",
                    "version": "R24-11",
                    "url": DCM_PDF,
                    "sha256": "cf5aeee78fda6e5a25f982f04cb146ce4a75586de7ba41913d46b0cea1cc2407",
                    "sections_reviewed": [
                        "7.2.4.3 [SWS_Dcm_01666-SWS_Dcm_01667]",
                        "7.2.4.6 [SWS_Dcm_00024]",
                        "7.2.4.13 [SWS_Dcm_01670]",
                        "7.2.4.14 [SWS_Dcm_01679-SWS_Dcm_01680]",
                    ],
                },
            ],
            "sources": [
                {"repository": "pylessard/python-can-isotp", "commit": ISOTP, "url": "https://github.com/pylessard/python-can-isotp"},
                {"repository": "driftregion/iso14229", "commit": ISO14229, "url": "https://github.com/driftregion/iso14229"},
            ],
            "profile_differences": [
                "AUTOSAR defines N_Bs/N_Cr as configurable and supplies no 1000 ms default; 1000 ms is python-can-isotp.",
                "AUTOSAR timer starts use transmission confirmations; python-can-isotp may start its local timer earlier.",
                "AUTOSAR unoverwritten S3 default is 5000 ms; driftregion/iso14229 uses 5100 ms.",
                "P2/P2* cards explicitly fix server adjustment=0 and use implementation defaults 50/5000 ms.",
            ],
            "rejected_candidates": REJECTED_CANDIDATES["can_uds"],
        },
        "dds_rtps": {
            "protocol": "DDS 1.4 / DDSI-RTPS 2.5",
            "access_date": "2026-07-13",
            "status": "COMPLETE_WITH_INDEPENDENT_AUDIT",
            "independent_audit_report": AUDIT_REPORT,
            "scope": (
                "Official OMG reference/default timing relationships instantiated on locked Fast-DDS "
                "and CycloneDDS commits. Harness configuration differences are explicit trigger preconditions."
            ),
            "proposal_summary": {"emitted": len(DDS_RTPS), "approve": 0, "fix_applied": 5, "rejected": 0},
            "standards": [
                {
                    "title": "The Real-time Publish-Subscribe Protocol DDS Interoperability Wire Protocol Specification",
                    "version": "DDSI-RTPS 2.5 formal/2022-04-01",
                    "url": RTPS_PDF,
                    "sha256": "c362eaa590c9c95fc6223359ce1ebfa57776cf7ea1e47824f58d48dc16907088",
                    "sections_reviewed": [
                        "8.4.7.1", "8.4.9.2.11", "8.4.10.1", "8.4.12.2.5",
                        "8.5.3.2.3", "8.5.5.2", "9.6.2.4", "9.6.3 Table 9.18",
                    ],
                },
                {
                    "title": "Data Distribution Service",
                    "version": "DDS 1.4 formal/2015-04-10",
                    "url": DDS_PDF,
                    "sha256": "16d6f8385c2ba79f7346dc18c867b624bc6dcc8fcf7c2ec52c55b7ae3dc113f2",
                    "sections_reviewed": ["2.2.2.4.2.11", "2.2.3.14"],
                },
            ],
            "sources": [
                {"repository": "eProsima/Fast-DDS", "version": "v3.3.0", "commit": FASTDDS, "url": "https://github.com/eProsima/Fast-DDS"},
                {"repository": "eclipse-cyclonedds/cyclonedds", "version": "0.10.5", "commit": CYCLONE, "url": "https://github.com/eclipse-cyclonedds/cyclonedds"},
            ],
            "profile_differences": [
                "Fast-DDS stock writer/reader response delays are 5 ms; reference-profile tests set 200/500 ms.",
                "Fast-DDS stock SPDP period/lease are 3 s/20 s; the SPDP card sets the 30 s RTPS reference rate.",
                "Fast-DDS writer nack response timer is writer-wide, so pending-reader set plus timer generation is the correlation unit.",
                "CycloneDDS can postpone dependent proxy participants; those cases are trigger-false for the 100 s safety card.",
            ],
            "rejected_candidates": [],
        },
        "modbus_tcp": {
            "protocol": "Modbus/TCP",
            "access_date": "2026-07-13",
            "status": "COMPLETE_WITH_INDEPENDENT_AUDIT",
            "independent_audit_report": AUDIT_REPORT,
            "scope": "Official V1.0b timing screening plus a locked libmodbus implementation check; no normative numeric MITL property survived audit.",
            "proposal_summary": {"emitted": 0, "approve": 0, "fix_applied": 0, "rejected": 1},
            "standards": [
                {
                    "title": "MODBUS Messaging on TCP/IP Implementation Guide",
                    "version": "V1.0b (2006-10-24)",
                    "url": "https://www.modbus.org/file/secure/messagingimplementationguide.pdf",
                    "sha256": "065d71170475642e82f370c648bf5135263cb20f61ce92c921add975fab6f669",
                    "sections_reviewed": ["4.3.2", "4.4.1.4"],
                    "finding": "Section 4.4.1.4 deliberately specifies no required transaction response time.",
                }
            ],
            "sources": [
                {"repository": "stephane/libmodbus", "version": "v3.1.11", "commit": "5190e5e141780ae481f24be16d7b39a5f3ad8f8f", "url": "https://github.com/stephane/libmodbus"}
            ],
            "profile_differences": [
                "libmodbus defaults response_timeout and byte_timeout to 500 ms, but they are separate timer generations.",
                "After initial bytes arrive, _modbus_receive_msg reloads byte_timeout; full confirmation may exceed 500 ms.",
            ],
            "rejected_candidates": REJECTED_CANDIDATES["modbus_tcp"],
        },
        "opc_ua": {
            "protocol": "OPC UA",
            "access_date": "2026-07-13",
            "status": "COMPLETE_WITH_INDEPENDENT_AUDIT",
            "independent_audit_report": AUDIT_REPORT,
            "scope": "OPC 10000-4 v1.05.07 relationships instantiated only after checking server-revised values on open62541 v1.4.14.",
            "proposal_summary": {"emitted": len(OPC_UA), "approve": 2, "fix_applied": 6, "rejected": 0},
            "standards": [
                {
                    "title": "OPC 10000-4: Services",
                    "version": "1.05.07",
                    "url": "https://reference.opcfoundation.org/Core/Part4/v105/docs/",
                    "sections_reviewed": ["5.6.2.1", "5.7.2.2", "5.14.1.1", "5.14.1.2", "5.14.2.2", "7.32"],
                }
            ],
            "sources": [
                {"repository": "open62541/open62541", "version": "v1.4.14", "commit": OPEN62541, "url": "https://github.com/open62541/open62541"}
            ],
            "profile_differences": [
                "Client requested defaults are never treated as revised values; every trigger checks the server-returned value.",
                "SecureChannel renewal is an after-75% SHOULD interval, not an exact action at 75%.",
                "Session cleanup and Subscription lifetime source use strict/greater-than checks that may expose exact-bound discrepancies.",
                "Subscription queue loss, re-enable, transfer/deletion, setting change, and normal close are explicit generation boundaries.",
            ],
            "rejected_candidates": [],
        },
    }


EXCLUDED_MARKDOWN: dict[str, str] = {
    "can_uds": """# CAN/UDS excluded candidates

Scope: public AUTOSAR R24-11 CAN-TP/DCM obligations instantiated on locked open-source profiles. Paid ISO-only text is not used as a normative anchor.

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| UDS-S3-02 valid TesterPresent restarts 5100 ms window | `REJECT_OR_FIX` | `DUPLICATE_OBLIGATION_AND_UNSUPPORTED_MULTI_CONNECTION` | Current formula is a logical subset of UDS-S3-01 and does not test the cited owner/foreign DcmDslConnection rule; iso14229 has no multi-connection model. | Use a multi-connection SUT and test that foreign TesterPresent does not reset the owner's S3 generation. |
| Universal N_Bs/N_Cr=1000 ms | `KEEP_EXCLUDED` | `NO_NORMATIVE_DEFAULT` | AUTOSAR makes both parameters configurable; 1000 ms belongs only to python-can-isotp. | Instantiate the active configuration and label the implementation profile. |
| Universal S3=5100 ms | `KEEP_EXCLUDED` | `IMPLEMENTATION_PROFILE_ONLY` | AUTOSAR's unoverwritten default is 5000 ms; 5100 ms is the locked iso14229 configuration. | Keep explicit profile trigger; never claim an AUTOSAR universal default. |
| ISO 15765/14229-wide restatement | `KEEP_EXCLUDED` | `NO_PUBLIC_NORMATIVE_TEXT_USED` | This evidence package intentionally uses public AUTOSAR clauses, not paid ISO text or third-party excerpts. | Obtain and independently review authorized primary ISO text. |
| TesterPresent on foreign connection | `DEFER_TO_V2` | `SUT_CAPABILITY_MISSING` | The locked SUT cannot represent multiple DcmDslConnections. | Select a multi-connection DCM or implement an independently reviewable ownership adapter. |

The emitted catalogue contains five cards; rejected UDS-S3-02 is not retained to satisfy a property count.
""",
    "dds_rtps": """# DDS/RTPS excluded candidates

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| Exact physical participant deletion at 100 s | `REJECT_OR_FIX` | `NO_EXACT_REMOVAL_DEADLINE` | RTPS permits considering a participant gone after its lease and requires reconfiguration after that conclusion; it does not bound physical cleanup callback latency. | Use the retained no-early safety card, or supply a separate implementation scanner bound. |
| Stock Fast-DDS 200/500 ms response delays | `KEEP_EXCLUDED` | `PROFILE_MISMATCH` | Fast-DDS v3.3.0 stock delays are 5 ms; 200/500 ms are RTPS reference defaults selected by the harness. | Record explicit QoS/timing configuration in the experiment manifest. |
| Stock Fast-DDS 30 s SPDP period | `KEEP_EXCLUDED` | `PROFILE_MISMATCH` | Stock period is 3 s, not the RTPS 30 s reference setting. | Configure 30 s and verify the revised runtime attribute before trigger. |
| Infinite/default DDS QoS durations | `KEEP_EXCLUDED` | `NO_FINITE_BOUND` | Many DDS QoS durations are infinite or application-configured, so they do not yield a finite numeric MITL interval without a profile. | Supply a normative finite profile and observable source hooks. |
| Per-ReaderProxy Fast-DDS writer nack timer | `KEEP_EXCLUDED` | `IMPLEMENTATION_MODEL_MISMATCH` | Fast-DDS uses a writer-wide timer affected by multiple readers. | Use writer GUID + timer generation + pending reader set, as in the repaired card. |
| Dependent CycloneDDS participant exact expiry | `KEEP_EXCLUDED` | `NORMATIVE_EXCEPTION` | Privileged-participant dependency may postpone handling by 200 ms. | Exclude dependency cases or model the dependency as a separate property. |

All five emitted cards are `FIXED_AFTER_AUDIT` and still require human review; none is silently upgraded to independently approved.
""",
    "modbus_tcp": """# Modbus/TCP excluded candidates

The official V1.0b guide states in §4.4.1.4 that no required transaction response time is specified. Therefore this protocol contributes zero normative numeric MITL cards after independent audit.

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| MODBUS-TCP-01 full confirmation within 500 ms | `REJECT_OR_FIX` | `NO_PROTOCOL_BOUND_AND_INCORRECT_IMPLEMENTATION_ORACLE` | 500 ms is a libmodbus default, not a protocol value; response_timeout governs the initial read and byte_timeout is reloaded for remaining chunks, so full confirmation may exceed 500 ms. | Split into initial-response and per-byte implementation profiles and keep them outside the normative main catalogue. |
| Universal MODBUS/TCP response deadline | `KEEP_EXCLUDED` | `NO_NUMERIC_BOUND` | §4.4.1.4 deliberately defines none. | A deployment-specific profile may be studied but cannot be generalized. |
| Universal retry deadline | `KEEP_EXCLUDED` | `NO_NUMERIC_BOUND` | The guide only requires a reasonable timeout based on expected transport delay. | Provide a locked deployment profile and mark it non-normative. |
| 500 ms byte-to-byte protocol timeout | `KEEP_EXCLUDED` | `IMPLEMENTATION_PROFILE_ONLY` | `_BYTE_TIMEOUT` is a libmodbus default with no Modbus/TCP normative requirement. | Keep only as a libmodbus appendix property. |
| 75 s TCP connect/keepalive/RTO properties | `KEEP_EXCLUDED` | `DUPLICATE_TRANSPORT_OBLIGATION` | These are TCP behavior, not Modbus application semantics. | Compare in the TCP catalogue, not here. |
| Server indication timeout | `KEEP_EXCLUDED` | `NO_FINITE_DEFAULT` | libmodbus leaves it unset and the guide provides no number. | Supply an explicit application profile. |

`MODBUS-TCP-01` is not emitted in `proposals.json` and is not counted toward catalogue size.
""",
    "opc_ua": """# OPC UA excluded candidates

| Candidate | Independent audit status | Decision code | Evidence-based reason | Re-entry gate |
|---|---|---|---|---|
| Renewal exactly at 75% | `REJECT_OR_FIX` | `OVERSTRONG_EXACT_BOUNDARY` | OPC 10000-4 says request after 75%; it does not require the request at the exact 75% instant. | Use the repaired [75%,100%) profile interval and preserve SHOULD strength. |
| Requested timeout/count treated as revised | `KEEP_EXCLUDED` | `NEGOTIATION_IGNORED` | Server may revise Session and Subscription parameters. | Trigger only on the returned revised value, as the repaired cards do. |
| Session cleanup callback exactly at timeout | `KEEP_EXCLUDED` | `DEADLINE_CALLBACK_CONFLATION` | The normative maximum and periodic cleanup callback are different observations. | Preserve the deadline oracle and record callback latency separately without invented epsilon. |
| Subscription generation without queue/close/reset cancellation | `KEEP_EXCLUDED` | `MISSING_PROTOCOL_EXCEPTION` | Queue loss, normal close, re-enable, transfer/deletion, or setting change can end a generation. | Use explicit cancellation APs and one trigger per projected word. |
| Disabled keep-alive timing as a duplicate standalone card | `KEEP_EXCLUDED` | `DUPLICATE_OBLIGATION` | Its timing half shares SUB-02; the distinct retained value is no notifications while disabled. | Keep disabled safety explicit and state the shared counter semantics. |
| timeoutHint exact cancellation at 5000 ms | `KEEP_EXCLUDED` | `HINT_NOT_DEADLINE` | timeoutHint permits cancellation only after waiting at least the hint; it does not require eventual cancellation. | Retain only OPCUA-PUB-01 no-early safety. |

Eight cards are emitted: two independently approved with caveats and six `FIXED_AFTER_AUDIT` cards awaiting human review.
""",
}


def main() -> None:
    outputs = {
        "opc_ua": OPC_UA,
        "dds_rtps": DDS_RTPS,
        "can_uds": CAN_UDS,
        "modbus_tcp": MODBUS_TCP,
    }
    for cards in outputs.values():
        enrich_cards(cards)
    manifests = evidence_manifests()
    for slug, cards in outputs.items():
        protocol_dir = HERE / slug
        proposals_path = protocol_dir / "proposals.json"
        evidence_path = protocol_dir / "evidence.json"
        excluded_path = protocol_dir / "excluded.md"
        proposals_path.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        evidence_path.write_text(json.dumps(manifests[slug], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        excluded_path.write_text(EXCLUDED_MARKDOWN[slug].rstrip() + "\n", encoding="utf-8")
        print(
            f"{slug}: {len(cards)} proposals, evidence={manifests[slug]['status']}, "
            f"excluded={len(REJECTED_CANDIDATES.get(slug, []))} rejected -> {protocol_dir}"
        )


if __name__ == "__main__":
    main()
