#!/usr/bin/env python3
"""Deterministically add AP-to-source mappings to the IETF staging cards.

The proposal JSON files predate the structured mapping gate.  This script keeps
the source evidence reproducible without changing any formal-protocol output.
Every mapping names only APs that are actually observable at that hook.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def gh(repo: str, commit: str, path: str, lines: str) -> str:
    first = lines.split(";", 1)[0]
    start, _, end = first.partition("-")
    suffix = f"#L{start}" + (f"-L{end}" if end else "")
    return f"https://github.com/{repo}/blob/{commit}/{path}{suffix}"


def mapping(role: str, path: str, symbol: str, lines: str,
            aps: list[str]) -> dict[str, Any]:
    return {
        "role": role,
        "path": path,
        "symbol": symbol,
        "lines": lines,
        "atomic_propositions": aps,
    }


CANONICAL_DEFINITIONS = {
    "coap_matching_ack_or_reset_received": (
        "coap_dispatch receives an ACK or RST whose endpoint and Message ID match "
        "the current exchange, and coap_remove_from_queue removes that exact "
        "queue-node generation."
    ),
    "coap_attempt_cancelled": (
        "An allowed non-ACK/RST local cancellation path removes the current "
        "queue-node generation before its stored deadline."
    ),
    "coap_same_con_retransmitted": (
        "coap_send_pdu successfully writes a later datagram for the same "
        "queue-node generation and Message ID."
    ),
    "mqtt_network_connection_closed": (
        "The correlated connection generation transitions from connected to "
        "inactive at net__socket_close; a broker Keep Alive reason, when present, "
        "is retained as an event field."
    ),
}


SPECS: dict[str, dict[str, Any]] = {
    "COAP-TX-01": {
        "primary": ["coap_con_wait_started", "coap_first_retransmit_deadline_reached"],
        "aux": [
            mapping("matching ACK/RST queue removal", "src/coap_net.c", "coap_dispatch",
                    "3983-3993;4128-4133", ["coap_matching_ack_or_reset_received"]),
            mapping("explicit local exchange cancellation", "src/coap_net.c",
                    "coap_cancel_session_messages / coap_cancel_all_messages",
                    "2573-2613;2616-2646", ["coap_attempt_cancelled"]),
        ],
    },
    "COAP-TX-02": {
        "primary": ["coap_first_retransmission_completed", "coap_second_retransmit_deadline_reached"],
        "aux": [
            mapping("matching ACK/RST queue removal", "src/coap_net.c", "coap_dispatch",
                    "3983-3993;4128-4133", ["coap_matching_ack_or_reset_received"]),
            mapping("explicit local exchange cancellation", "src/coap_net.c",
                    "coap_cancel_session_messages / coap_cancel_all_messages",
                    "2573-2613;2616-2646", ["coap_attempt_cancelled"]),
        ],
    },
    "COAP-TX-03": {
        "primary": [
            "coap_fourth_retransmission_completed", "coap_final_wait_deadline_reached",
            "coap_fifth_retransmission_sent",
        ],
        "aux": [
            mapping("matching ACK/RST queue removal", "src/coap_net.c", "coap_dispatch",
                    "3983-3993;4128-4133", ["coap_matching_ack_or_reset_received"]),
            mapping("explicit local exchange cancellation", "src/coap_net.c",
                    "coap_cancel_session_messages / coap_cancel_all_messages",
                    "2573-2613;2616-2646", ["coap_attempt_cancelled"]),
        ],
    },
    "COAP-TX-04": {
        "primary": ["coap_con_initial_sent", "coap_same_con_retransmitted"],
        "aux": [
            mapping("MAX_TRANSMIT_SPAN implementation expression",
                    "include/coap3/coap_session_internal.h", "COAP_MAX_TRANSMIT_SPAN",
                    "618-628", ["coap_con_initial_sent"]),
        ],
    },
    "COAP-TX-05": {
        "primary": ["coap_matching_ack_or_reset_received"],
        "aux": [
            mapping("subsequent send for the same queue-node generation", "src/coap_net.c",
                    "coap_retransmit", "1908-1969", ["coap_same_con_retransmitted"]),
        ],
    },
    "COAP-MID-01": {
        "source": ("src/coap_net.c", "coap_send_pdu", "1014-1050"),
        "primary": ["coap_mid_first_used", "coap_same_mid_reused"],
        "aux": [
            mapping("Message ID allocation prerequisite", "src/coap_session.c",
                    "coap_new_message_id_lkd", "1909-1915",
                    ["coap_mid_first_used", "coap_same_mid_reused"]),
        ],
    },
    "COAP-MCAST-01": {
        "primary": ["coap_multicast_response_committed_default_leisure"],
        "aux": [
            mapping("delayed multicast response send", "src/coap_net.c", "coap_retransmit",
                    "1908-1969", ["coap_multicast_response_sent"]),
        ],
    },
    "MQTT-KA-01": {
        "source": ("lib/packet_mosq.c", "packet__write", "227-358"),
        "primary": [
            "mqtt_client_outbound_window_started", "mqtt_pingreq_started",
            "mqtt_other_control_packet_started",
        ],
        "aux": [
            mapping("Keep Alive scheduling eligibility", "lib/util_mosq.c",
                    "mosquitto__check_keepalive", "62-143",
                    ["mqtt_client_outbound_window_started", "mqtt_pingreq_started"]),
            mapping("network connection generation close", "lib/net_mosq.c",
                    "net__socket_close", "214-267", ["mqtt_network_connection_closed"]),
        ],
    },
    "MQTT-KA-02": {
        "source": ("lib/packet_mosq.c", "packet__read", "361-589"),
        "primary": ["mqtt_server_inbound_window_started", "mqtt_client_control_packet_received"],
        "aux": [
            mapping("broker Keep Alive expiry decision", "src/keepalive.c", "keepalive__check",
                    "127-175", ["mqtt_network_connection_closed"]),
            mapping("network connection generation close", "lib/net_mosq.c",
                    "net__socket_close", "214-267", ["mqtt_network_connection_closed"]),
        ],
    },
    "MQTT-RTX-01": {
        "primary": ["mqtt_publish_negative_ack_received"],
        "aux": [
            mapping("negative PUBACK state completion", "lib/handle_pubackcomp.c",
                    "handle__pubackcomp", "41-168", ["mqtt_publish_negative_ack_received"]),
            mapping("later PUBLISH send for retained message generation", "lib/send_publish.c",
                    "send__publish / send__real_publish", "42-134;137-221",
                    ["mqtt_same_publish_retransmitted"]),
        ],
    },
    "RTSP-SESSION-01": {
        "source_lines": "283-297;303-312",
        "primary": ["rtsp_liveness_generation_armed_65", "rtsp_inactivity_reclaim_callback_entered"],
        "aux": [
            mapping("65-second server profile declaration", "liveMedia/include/RTSPServer.hh",
                    "reclamationSeconds", "31-41", ["rtsp_liveness_generation_armed_65"]),
            mapping("Session timeout advertisement", "liveMedia/RTSPServer.cpp",
                    "RTSPServer::RTSPClientSession::handleCmd_SETUP", "1416-1499",
                    ["rtsp_liveness_generation_armed_65"]),
            mapping("valid Session request liveness refresh", "liveMedia/RTSPServer.cpp",
                    "RTSPServer::RTSPClientConnection::handleRequestBytes", "726-733",
                    ["rtsp_liveness_generation_armed_65"]),
            mapping("task reschedule", "UsageEnvironment/UsageEnvironment.cpp",
                    "TaskScheduler::rescheduleDelayedTask", "52-57",
                    ["rtsp_liveness_generation_armed_65"]),
            mapping("delayed-task queue insertion", "BasicUsageEnvironment/BasicTaskScheduler0.cpp",
                    "BasicTaskScheduler0::scheduleDelayedTask", "59-68",
                    ["rtsp_liveness_generation_armed_65"]),
            mapping("due delayed-task dispatch", "BasicUsageEnvironment/DelayQueue.cpp",
                    "DelayQueue::handleAlarm", "179-189",
                    ["rtsp_inactivity_reclaim_callback_entered"]),
        ],
    },
}


SMTP_APS = {
    "SMTP-TIMEOUT-01": {
        "primary": ["smtp_waiting_initial_220"],
        "roles": {
            "response reader and errno propagation": ["smtp_initial_220_timeout"],
            "absolute read deadline and ETIMEDOUT": ["smtp_initial_220_timeout"],
            "SMTP timeout classification": ["smtp_initial_220_timeout"],
        },
    },
    "SMTP-TIMEOUT-02": {
        "primary": ["smtp_mail_response_wait_started"],
        "roles": {
            "pipelined MAIL response slot": ["smtp_mail_response_wait_started", "smtp_mail_response_timeout"],
            "MAIL command and direct response path": ["smtp_mail_response_wait_started"],
            "response reader and errno propagation": ["smtp_mail_response_timeout"],
            "absolute read deadline and ETIMEDOUT": ["smtp_mail_response_timeout"],
            "SMTP timeout classification": ["smtp_mail_response_timeout"],
        },
    },
    "SMTP-TIMEOUT-03": {
        "primary": ["smtp_rcpt_response_wait_started", "smtp_rcpt_response_timeout"],
        "roles": {
            "RCPT command enqueue/flush and sync invocation": ["smtp_rcpt_response_wait_started"],
            "actual pipelined command-buffer flush": ["smtp_rcpt_response_wait_started"],
            "response reader and errno propagation": ["smtp_rcpt_response_timeout"],
            "absolute read deadline and ETIMEDOUT": ["smtp_rcpt_response_timeout"],
        },
    },
    "SMTP-TIMEOUT-04": {
        "primary": ["smtp_data_354_wait_started"],
        "roles": {
            "pending DATA response slot": ["smtp_data_354_wait_started", "smtp_data_354_timeout"],
            "actual command-buffer flush": ["smtp_data_354_wait_started"],
            "response reader and errno propagation": ["smtp_data_354_timeout"],
            "absolute read deadline and ETIMEDOUT": ["smtp_data_354_timeout"],
            "SMTP timeout classification": ["smtp_data_354_timeout"],
        },
    },
    "SMTP-TIMEOUT-05": {
        "primary": ["smtp_data_block_send_wait_started", "smtp_data_block_send_timeout"],
        "roles": {
            "SMTP data-timeout selection and outbound message write": ["smtp_data_block_send_wait_started"],
            "buffer flushes that invoke the primary hook": ["smtp_data_block_send_wait_started"],
        },
    },
    "SMTP-TIMEOUT-06": {
        "primary": ["smtp_final_250_wait_started", "smtp_final_250_timeout"],
        "roles": {
            "response reader and errno propagation": ["smtp_final_250_timeout"],
            "absolute read deadline and ETIMEDOUT": ["smtp_final_250_timeout"],
            "SMTP timeout classification": ["smtp_final_250_timeout"],
        },
    },
    "SMTP-TIMEOUT-07": {
        "primary": ["smtp_server_command_wait_started"],
        "roles": {
            "command-phase signal-handler installation and read loop": ["smtp_server_command_wait_started"],
            "command timeout outcome and connection close": ["smtp_server_command_idle_timeout"],
            "default timeout profile": ["smtp_server_command_wait_started"],
        },
    },
}


def enrich_card(card: dict[str, Any]) -> None:
    pid = card["id"]
    spec = SPECS.get(pid)
    if spec:
        if "source" in spec:
            card["source_path"], card["source_symbol"], card["source_lines"] = spec["source"]
        if "source_lines" in spec:
            card["source_lines"] = spec["source_lines"]
        card["source_url"] = gh(card["source_repository"], card["source_commit"],
                                card["source_path"], card["source_lines"])
        card["primary_source_atomic_propositions"] = spec["primary"]
        card["auxiliary_source_mappings"] = spec["aux"]

    if pid in SMTP_APS:
        smtp_spec = SMTP_APS[pid]
        card["primary_source_atomic_propositions"] = smtp_spec["primary"]
        existing = [
            item for item in card.get("auxiliary_source_mappings", [])
            if item.get("role") != "fixed timeout profile"
        ]
        for item in existing:
            item["atomic_propositions"] = smtp_spec["roles"][item["role"]]
        profile_ap = card["atomic_propositions"][0]
        profile_path = "src/src/globals.c" if pid == "SMTP-TIMEOUT-07" else "src/src/transports/smtp.c"
        profile_symbol = "smtp_receive_timeout" if pid == "SMTP-TIMEOUT-07" else "smtp_transport_option_defaults"
        profile_lines = "1325" if pid == "SMTP-TIMEOUT-07" else "189-225"
        existing.append(mapping("fixed timeout profile", profile_path, profile_symbol,
                                profile_lines, [profile_ap]))
        card["auxiliary_source_mappings"] = existing

    for ap, definition in CANONICAL_DEFINITIONS.items():
        if ap in card.get("atomic_propositions", []):
            card["ap_definitions"][ap] = definition

    # Source-code links now live only in the structured mapping schema.  Keep
    # standards links, which do not use the *_source_url legacy names here.
    for key in list(card):
        if key != "source_url" and (key.endswith("_source_url") or key.endswith("_source_urls")):
            del card[key]

    for item in card.get("auxiliary_source_mappings", []):
        item["url"] = gh(item.get("repository", card["source_repository"]),
                         item.get("commit", card["source_commit"]),
                         item["path"], item["lines"])


def main() -> None:
    for path in sorted(HERE.rglob("proposals.json")):
        cards = json.loads(path.read_text(encoding="utf-8"))
        for card in cards:
            enrich_card(card)
        path.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{path.relative_to(HERE)}: {len(cards)} cards")


if __name__ == "__main__":
    main()
