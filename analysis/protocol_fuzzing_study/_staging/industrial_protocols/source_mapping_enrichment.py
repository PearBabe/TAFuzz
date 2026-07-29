"""Structured AP-to-source mappings for industrial staging proposals."""

from __future__ import annotations

from typing import Any


def gh(repo: str, commit: str, path: str, lines: str) -> str:
    first = lines.split(";", 1)[0]
    start, _, end = first.partition("-")
    suffix = f"#L{start}" + (f"-L{end}" if end else "")
    return f"https://github.com/{repo}/blob/{commit}/{path}{suffix}"


def m(role: str, path: str, symbol: str, lines: str, *aps: str,
      repository: str = "", commit: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {
        "role": role, "path": path, "symbol": symbol, "lines": lines,
        "atomic_propositions": list(aps),
    }
    if repository:
        result["repository"] = repository
    if commit:
        result["commit"] = commit
    return result


SPECS: dict[str, dict[str, Any]] = {
    "OPCUA-SC-01": {
        "source": ("src/client/ua_client_connect.c", "processOPNResponse", "495-589"),
        "primary": [
            "security_token_issued_default_lifetime",
            "security_token_generation_cancelled",
        ],
        "aux": [
            m("RENEW OpenSecureChannelRequest send", "src/client/ua_client_connect.c",
              "sendOPNAsync", "593-646", "secure_channel_renew_requested"),
            m("SecureChannel close lifecycle", "src/client/ua_client_connect.c",
              "closeSecureChannel", "2198-2236", "secure_channel_closed"),
            m("600000 ms client lifetime profile", "plugins/ua_config_default.c",
              "UA_ClientConfig_setDefault", "1115-1118",
              "security_token_issued_default_lifetime"),
        ],
        "definitions": {
            "security_token_generation_cancelled": (
                "A later successful processOPNResponse replaces the correlated current token "
                "with a new token before this generation's renewal-request observation; the "
                "adapter closes the old token generation at that replacement."
            ),
        },
    },
    "OPCUA-SC-02": {
        "source": ("src/ua_securechannel_crypto.c", "checkSymHeader", "506-569"),
        "primary": ["old_token_message_received", "old_token_message_accepted"],
        "aux": [
            m("old-token installation and expiry-field snapshot",
              "src/client/ua_client_connect.c", "processOPNResponse", "495-589",
              "old_security_token_expired_default_lifetime"),
            m("600000 ms client lifetime profile", "plugins/ua_config_default.c",
              "UA_ClientConfig_setDefault", "1115-1118",
              "old_security_token_expired_default_lifetime"),
        ],
    },
    "OPCUA-SESS-01": {
        "source": ("src/server/ua_services_session.c", "UA_Server_cleanupSessions", "115-126"),
        "primary": ["session_timeout_terminated"],
        "aux": [
            m("Session logical idle deadline", "src/server/ua_session.c",
              "UA_Session_updateLifetime", "125-131",
              "session_idle_window_started_1200000", "session_service_activity"),
            m("valid Service activity refresh", "src/server/ua_server_binary.c",
              "processMSGDecoded", "716-865", "session_service_activity"),
            m("revised Session timeout creation", "src/server/ua_services_session.c",
              "UA_Server_createSession / Service_CreateSession", "224-260;263-393",
              "session_idle_window_started_1200000"),
            m("explicit CloseSession and removal", "src/server/ua_services_session.c",
              "Service_CloseSession / UA_Server_removeSession", "29-98;918-960",
              "session_idle_generation_cancelled"),
            m("1200000 ms requested client profile", "plugins/ua_config_default.c",
              "UA_ClientConfig_setDefault", "1173-1174",
              "session_idle_window_started_1200000"),
        ],
        "definitions": {
            "session_idle_generation_cancelled": (
                "Service_CloseSession removes the correlated Session with CLOSE rather than "
                "TIMEOUT, or an equivalent server purge/removal lifecycle ends it before the "
                "idle deadline."
            ),
        },
    },
    "OPCUA-SUB-01": {
        "source": ("src/server/ua_subscription.c", "Subscription_setState", "730-759"),
        "primary": ["default_subscription_first_cycle_started"],
        "aux": [
            m("CreateSubscription revised values", "src/server/ua_services_subscription.c",
              "Service_CreateSubscription", "55-127", "default_subscription_first_cycle_started"),
            m("Publish request queue prerequisite", "src/server/ua_services_subscription.c",
              "Service_Publish", "236-355", "default_subscription_first_cycle_started"),
            m("first notification or keep-alive response", "src/server/ua_subscription.c",
              "UA_Subscription_publish", "427-648", "first_publish_response"),
            m("Subscription deletion or setting change", "src/server/ua_subscription.c",
              "UA_Subscription_delete", "53-115", "first_cycle_generation_cancelled"),
            m("revised interval change", "src/server/ua_services_subscription.c",
              "Service_ModifySubscription", "130-193", "first_cycle_generation_cancelled"),
            m("500 ms client request profile", "include/open62541/client_subscriptions.h",
              "UA_CreateSubscriptionRequest_default", "43-63",
              "default_subscription_first_cycle_started"),
        ],
        "definitions": {
            "first_cycle_generation_cancelled": (
                "The correlated Subscription is deleted, its revised interval is changed by "
                "ModifySubscription, or its Session-close path deletes the Subscription before "
                "the first-cycle response."
            ),
        },
    },
    "OPCUA-SUB-02": {
        "source": ("src/server/ua_subscription.c", "UA_Subscription_publish", "477-610"),
        "primary": [
            "default_keepalive_window_started", "keepalive_response", "notification_response",
        ],
        "aux": [
            m("revised keep-alive settings", "src/server/ua_services_subscription.c",
              "setSubscriptionSettings / Service_CreateSubscription",
              "26-52;55-127", "default_keepalive_window_started"),
            m("Subscription deletion", "src/server/ua_subscription.c",
              "UA_Subscription_delete", "53-115", "keepalive_generation_cancelled"),
            m("revised interval/count change", "src/server/ua_services_subscription.c",
              "Service_ModifySubscription", "130-193", "keepalive_generation_cancelled"),
            m("default 500 ms by 10 client profile", "include/open62541/client_subscriptions.h",
              "UA_CreateSubscriptionRequest_default", "43-63",
              "default_keepalive_window_started"),
        ],
        "definitions": {
            "keepalive_generation_cancelled": (
                "The correlated Subscription is deleted, ModifySubscription changes its "
                "revised interval/count, or its Session-close path deletes the Subscription "
                "before this keep-alive generation completes."
            ),
        },
    },
    "OPCUA-SUB-03": {
        "source": ("src/server/ua_subscription.c", "UA_Subscription_publish", "455-474"),
        "primary": ["default_subscription_no_publish_window_started", "subscription_timeout_closed"],
        "aux": [
            m("Subscription lifetime reset", "src/server/ua_subscription.c",
              "Subscription_resetLifetime", "118-120", "subscription_lifetime_reset"),
            m("manual Subscription deletion", "src/server/ua_subscription.c",
              "UA_Subscription_delete", "53-115", "subscription_lifetime_generation_cancelled"),
            m("service reset or revised-setting change", "src/server/ua_services_subscription.c",
              "Service_ModifySubscription / Service_Republish", "130-193;393-433",
              "subscription_lifetime_reset", "subscription_lifetime_generation_cancelled"),
            m("default revised-value source", "src/server/ua_services_subscription.c",
              "setSubscriptionSettings / Service_CreateSubscription", "26-52;55-127",
              "default_subscription_no_publish_window_started"),
            m("500 ms and 10000-count client profile", "include/open62541/client_subscriptions.h",
              "UA_CreateSubscriptionRequest_default", "43-63",
              "default_subscription_no_publish_window_started"),
        ],
        "definitions": {
            "subscription_lifetime_generation_cancelled": (
                "Manual UA_Subscription_delete or a ModifySubscription revised-setting change "
                "ends the correlated lifetime generation without the Bad_Timeout cause."
            ),
        },
    },
    "OPCUA-SUB-04": {
        "source": ("src/server/ua_subscription.c", "UA_Subscription_publish", "477-610"),
        "primary": ["notification_response_while_disabled", "keepalive_response_while_disabled"],
        "aux": [
            m("disable/re-enable and lifetime reset", "src/server/ua_services_subscription.c",
              "Operation_SetPublishingMode", "196-214", "disabled_keepalive_window_started",
              "disabled_keepalive_generation_cancelled"),
            m("Subscription deletion", "src/server/ua_subscription.c",
              "UA_Subscription_delete", "53-115", "disabled_keepalive_generation_cancelled"),
            m("revised interval/count change", "src/server/ua_services_subscription.c",
              "Service_ModifySubscription", "130-193", "disabled_keepalive_generation_cancelled"),
            m("default revised-value source", "src/server/ua_services_subscription.c",
              "setSubscriptionSettings / Service_CreateSubscription", "26-52;55-127",
              "disabled_keepalive_window_started"),
            m("500 ms by 10 client profile", "include/open62541/client_subscriptions.h",
              "UA_CreateSubscriptionRequest_default", "43-63",
              "disabled_keepalive_window_started"),
        ],
        "definitions": {
            "disabled_keepalive_generation_cancelled": (
                "Operation_SetPublishingMode re-enables the Subscription, it is deleted, or "
                "ModifySubscription changes the revised interval/count before the disabled "
                "keep-alive generation completes."
            ),
        },
    },
    "OPCUA-PUB-01": {
        "source": ("src/server/ua_subscription.c", "UA_Subscription_publish", "427-452"),
        "primary": ["publish_bad_timeout"],
        "aux": [
            m("Publish timeoutHint deadline and queue", "src/server/ua_services_subscription.c",
              "Service_Publish", "304-315", "publish_request_queued_timeout_hint_5000"),
        ],
    },
    "RTPS-REL-01": {
        "primary": [
            "writer_nack_timer_generation_started_200",
            "nack_response_generation_superseded",
            "rtps_pending_reader_set_empty",
        ],
        "aux": [
            m("writer nack-response callback action", "src/cpp/rtps/writer/StatefulWriter.cpp",
              "StatefulWriter::perform_nack_response", "1880-1900",
              "nack_response_action_observed"),
            m("TimedEvent callback binding", "src/cpp/rtps/writer/StatefulWriter.cpp",
              "StatefulWriter::init", "225-232", "nack_response_action_observed"),
            m("reader unmatch can empty pending-reader set",
              "src/cpp/rtps/writer/StatefulWriter.cpp",
              "StatefulWriter::matched_reader_remove", "1211-1302",
              "rtps_pending_reader_set_empty"),
            m("writer removal stops timer and reader proxies",
              "src/cpp/rtps/writer/StatefulWriter.cpp",
              "StatefulWriter::local_actions_on_writer_removed", "256-315",
              "rtps_writer_stopped"),
        ],
    },
    "RTPS-REL-02": {
        "source": ("src/cpp/rtps/reader/WriterProxy.cpp",
                   "WriterProxy::process_heartbeat", "550-615"),
        "primary": [
            "heartbeat_response_generation_started_500",
            "heartbeat_response_generation_superseded",
        ],
        "aux": [
            m("heartbeat-response ACKNACK handoff", "src/cpp/rtps/reader/WriterProxy.cpp",
              "WriterProxy::perform_heartbeat_response", "535-548",
              "heartbeat_acknack_sent"),
            m("remote writer unmatch", "src/cpp/rtps/reader/StatefulReader.cpp",
              "StatefulReader::matched_writer_remove", "381-482", "rtps_writer_unmatched"),
            m("WriterProxy timer cancellation", "src/cpp/rtps/reader/WriterProxy.cpp",
              "WriterProxy::stop", "170-187", "rtps_writer_unmatched", "rtps_reader_stopped"),
            m("local reader removal lifecycle", "src/cpp/rtps/reader/BaseReader.cpp",
              "BaseReader::local_actions_on_reader_removed", "109-112", "rtps_reader_stopped"),
        ],
    },
    "RTPS-DISC-01": {
        "source": ("src/cpp/rtps/builtin/discovery/participant/PDP.cpp",
                   "PDP::set_next_announcement_interval", "1534-1546"),
        "primary": ["periodic_spdp_generation_started_30000"],
        "aux": [
            m("periodic SPDP announcement action",
              "src/cpp/rtps/builtin/discovery/participant/PDP.cpp",
              "PDP::announceParticipantState", "576-692",
              "next_periodic_spdp_announcement_sent"),
            m("periodic announcement generation reset",
              "src/cpp/rtps/builtin/discovery/participant/PDP.cpp",
              "PDP::resetParticipantAnnouncement", "702-708",
              "spdp_period_generation_superseded"),
            m("participant stop and timer cancellation",
              "src/cpp/rtps/builtin/discovery/participant/PDP.cpp",
              "PDP::stopParticipantAnnouncement / PDP::disable", "558-574;694-700",
              "local_participant_stopped"),
        ],
    },
    "RTPS-DISC-02": {
        "primary": ["remote_participant_removed_due_to_lease"],
        "aux": [
            m("default lease creation and SPDP refresh",
              "src/core/ddsi/src/q_ddsi_discovery.c", "handle_spdp_alive", "723-981",
              "remote_participant_default_lease_started",
              "remote_spdp_refresh_supersedes_lease"),
            m("explicit SPDP dispose cancellation", "src/core/ddsi/src/q_ddsi_discovery.c",
              "handle_spdp_dead", "638-671", "remote_lease_generation_cancelled"),
            m("privileged participant lease exception", "src/core/ddsi/src/q_lease.c",
              "check_and_handle_lease_expiration", "247-281",
              "remote_participant_default_lease_started"),
        ],
        "definitions": {
            "remote_lease_generation_cancelled": (
                "A correlated SPDP dispose/unregister reaches handle_spdp_dead and deletes "
                "the proxy participant before lease expiry; domain shutdown is recorded only "
                "through its corresponding proxy-deletion lifecycle."
            ),
        },
    },
    "DDS-WRITE-01": {
        "primary": ["reliable_write_resource_wait_started_default"],
        "aux": [
            m("absolute max-blocking deadline and API return",
              "src/cpp/fastdds/publisher/DataWriterImpl.cpp",
              "DataWriterImpl::perform_create_new_change", "1003-1107",
              "reliable_write_resource_wait_started_default", "write_returned_from_blocking"),
            m("templated history caller return",
              "src/cpp/fastdds/publisher/DataWriterHistory.hpp",
              "add_pub_change_with_commit_hook", "142-170", "write_returned_from_blocking"),
        ],
    },
    "CANTP-NBS-01": {
        "primary": ["flow_control_received", "tx_aborted_n_bs"],
        "aux": [
            m("N_Bs timer generation start", "isotp/protocol.py", "_start_rx_fc_timer",
              "1250-1253", "n_bs_timer_generation_started_1000"),
            m("1000 ms receive-flow-control profile", "isotp/protocol.py", "__init__",
              "349-354", "n_bs_timer_generation_started_1000"),
            m("strict elapsed timeout predicate", "isotp/tools.py", "is_timed_out",
              "48-53", "tx_aborted_n_bs"),
            m("explicit send cancellation or layer reset", "isotp/protocol.py",
              "stop_sending / reset", "1321-1325;1406-1415", "n_bs_generation_cancelled"),
        ],
        "definitions": {
            "n_bs_generation_cancelled": (
                "The public stop_sending path or TransportLayerLogic.reset ends the current "
                "WAIT_FC generation before its timeout; a harness process reset is accepted "
                "only when it records the same transfer generation."
            ),
        },
    },
    "CANTP-NCR-01": {
        "primary": ["rx_aborted_n_cr"],
        "aux": [
            m("accepted consecutive-frame path", "isotp/protocol.py", "_process_rx",
              "895-984", "n_cr_timer_generation_started_1000", "consecutive_frame_received"),
            m("N_Cr timer generation start", "isotp/protocol.py", "_start_rx_cf_timer",
              "1254-1257", "n_cr_timer_generation_started_1000"),
            m("1000 ms consecutive-frame profile", "isotp/protocol.py", "__init__",
              "349-354", "n_cr_timer_generation_started_1000"),
            m("strict elapsed timeout predicate", "isotp/tools.py", "is_timed_out",
              "48-53", "rx_aborted_n_cr"),
            m("explicit receive cancellation or layer reset", "isotp/protocol.py",
              "stop_receiving / reset", "1341-1346;1406-1415", "n_cr_generation_cancelled"),
        ],
        "definitions": {
            "n_cr_generation_cancelled": (
                "The public stop_receiving path or TransportLayerLogic.reset ends the current "
                "WAIT_CF generation before timeout; normal successful completion is retained "
                "as a distinct terminal cause by the adapter."
            ),
        },
    },
    "UDS-P2-01": {
        "primary": [
            "uds_request_processing_started_p2_50_adjust0", "uds_final_response_sent",
            "uds_nrc78_sent",
        ],
        "aux": [
            m("50 ms P2 implementation profile", "src/config.h", "UDS_SERVER_DEFAULT_P2_MS",
              "42-43", "uds_request_processing_started_p2_50_adjust0"),
            m("strict logical deadline predicate", "src/util.h", "UDSTimeAfter", "13",
              "uds_final_response_sent", "uds_nrc78_sent"),
            m("response transport handoff", "src/server.c", "UDSServerPoll", "1617-1621",
              "uds_final_response_sent", "uds_nrc78_sent"),
            m("server reset cancellation", "src/server.c", "UDSServerInit", "1564-1579",
              "uds_p2_generation_cancelled"),
        ],
        "definitions": {
            "uds_p2_generation_cancelled": (
                "UDSServerInit resets the server while the correlated request is outstanding, "
                "or the harness records transport teardown for that request generation before "
                "a response handoff."
            ),
        },
    },
    "UDS-P2STAR-01": {
        "primary": [
            "uds_nrc78_sent_p2star_5000_adjust0", "uds_final_response_after_nrc78",
            "uds_nrc78_repeated",
        ],
        "aux": [
            m("5000 ms P2-star implementation profile", "src/config.h",
              "UDS_SERVER_DEFAULT_P2_STAR_MS", "47-48",
              "uds_nrc78_sent_p2star_5000_adjust0"),
            m("strict logical deadline predicate", "src/util.h", "UDSTimeAfter", "13",
              "uds_final_response_after_nrc78", "uds_nrc78_repeated"),
            m("server reset cancellation", "src/server.c", "UDSServerInit", "1564-1579",
              "uds_p2star_generation_cancelled"),
        ],
        "definitions": {
            "uds_p2star_generation_cancelled": (
                "UDSServerInit resets the server while the post-0x78 response is outstanding, "
                "or the harness records transport teardown for that exact request generation."
            ),
        },
    },
    "UDS-S3-01": {
        "primary": ["default_session_entered_due_to_s3"],
        "aux": [
            m("non-default session entry and explicit session change", "src/server.c",
              "Handle_0x10_DiagnosticSessionControl", "38-83",
              "non_default_session_idle_started_s3_5100", "s3_generation_cancelled"),
            m("TesterPresent S3 refresh", "src/server.c", "Handle_0x3E_TesterPresent",
              "1304-1321", "s3_resetting_activity_received"),
            m("server initialization and reset", "src/server.c", "UDSServerInit",
              "1564-1579", "non_default_session_idle_started_s3_5100",
              "s3_generation_cancelled"),
            m("5100 ms S3 implementation profile", "src/config.h",
              "UDS_SERVER_DEFAULT_S3_MS", "51-53", "non_default_session_idle_started_s3_5100"),
            m("strict S3 deadline predicate", "src/util.h", "UDSTimeAfter", "13",
              "default_session_entered_due_to_s3"),
        ],
        "definitions": {
            "s3_generation_cancelled": (
                "A valid DiagnosticSessionControl changes the session generation, or "
                "UDSServerInit resets the server, before the old S3 timeout cause occurs."
            ),
        },
    },
}


def enrich_cards(cards: list[dict[str, Any]]) -> None:
    for card in cards:
        spec = SPECS.get(str(card.get("id")))
        if not spec:
            continue
        if "source" in spec:
            card["source_path"], card["source_symbol"], card["source_lines"] = spec["source"]
        card["source_url"] = gh(card["source_repository"], card["source_commit"],
                                card["source_path"], card["source_lines"])
        card["primary_source_atomic_propositions"] = spec["primary"]
        card["auxiliary_source_mappings"] = spec["aux"]
        card["ap_definitions"].update(spec.get("definitions", {}))

        # The builder's legacy role fields are intentionally converted, not
        # retained beside the structured schema.
        for key in list(card):
            if key != "source_url" and (key.endswith("_source_url") or key.endswith("_source_urls")):
                del card[key]
            elif key.endswith("_source_path") or key.endswith("_source_lines") or key.endswith("_source_description"):
                del card[key]

        for item in card["auxiliary_source_mappings"]:
            repo = item.get("repository", card["source_repository"])
            commit = item.get("commit", card["source_commit"])
            item["url"] = gh(repo, commit, item["path"], item["lines"])

        declared = set(card["atomic_propositions"])
        covered = set(card["primary_source_atomic_propositions"])
        for item in card["auxiliary_source_mappings"]:
            covered.update(item["atomic_propositions"])
        if covered != declared:
            raise ValueError(f"{card['id']}: source AP coverage mismatch: {covered ^ declared}")
