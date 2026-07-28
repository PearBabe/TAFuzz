#!/usr/bin/env python3
"""Generate the independent Kamailio/SIP MITL reanalysis packet.

This script intentionally does not read or reuse the historical
analysis/protocol_fuzzing_study/protocols/SIP directory.  Its evidence inputs
are the RFC/Kamailio/ProfuzzBench files freshly cached under
/tmp/tafuzz_sip_kamailio_reanalysis plus the local TAMonitor binary.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path("/home/lqq/project/TAFuzz")
OUT = ROOT / "analysis/protocol_fuzzing_study/independent_reanalysis/sip_kamailio"
CACHE = OUT / "evidence_cache"
PROFUZZ = CACHE / "profuzzbench_kamailio"
TAMONITOR = ROOT / "tool/MightyPPL/build/TAMonitor"
KAM_COMMIT = "2648eb330b133a20f1398d59a28c53532106cad3"
PROFUZZ_COMMIT = "8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074"
ACCESS_DATE = "2026-07-13"
KAM_TARBALL = CACHE / "kamailio_2648eb330b.tar.gz"
KAM_TAR_PREFIX = f"kamailio-{KAM_COMMIT}/"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_url(path: str, line: int) -> str:
    return f"https://github.com/kamailio/kamailio/blob/{KAM_COMMIT}/{path}#L{line}"


@dataclass
class Hook:
    hook_id: str
    file: str
    function: str
    line: int
    phase: str
    event_type: str
    emits: List[str]
    timing: str
    payload: str
    overhead: str
    notes: str = ""

    @property
    def url(self) -> str:
        return source_url(self.file, self.line)


@dataclass
class Prop:
    pid: str
    category: str
    role: str
    requirement: str
    strength: str
    rfc: str
    section: str
    rfc_url: str
    excerpt: str
    time_bound_ms: str
    time_source: str
    kind: str
    trigger: str
    outcome: str
    formula: str
    math_formula: str
    aps: List[str]
    hooks: List[str]
    aux_hooks: List[str]
    correlation_key: str
    positive_trace: List[Tuple[int, List[str]]]
    negative_trace: List[Tuple[int, List[str]]]
    observability: str
    oracle_value: str
    confidence: str
    caveat: str
    review_question: str


HOOKS: Dict[str, Hook] = {
    "HK_RX_PARSE_OK": Hook(
        "HK_RX_PARSE_OK", "src/core/receive.c", "receive_msg", 296,
        "after parse_msg/headers succeed, before routing", "rx_request",
        ["sip_msg_parse_ok", "server_rx_invite_new_tx", "server_rx_noninvite_new_tx"],
        "raw receive timestamp", "direction, method, status, Call-ID hash, CSeq, Via branch hash",
        "single binary event after parser success; no string formatting",
        "Primary receive boundary for black-box packet to white-box transaction correlation.",
    ),
    "HK_TX_NEW": Hook(
        "HK_TX_NEW", "src/modules/tm/t_lookup.c", "t_newtran", 1437,
        "after new_t succeeds and before init_rb/return", "transaction_create",
        ["invite_tx_proceeding", "noninvite_tx_trying"],
        "same monotonic tick as transaction creation", "transaction pointer id, method class, initial RFC state",
        "one event per new transaction", "",
    ),
    "HK_TX_LOOKUP": Hook(
        "HK_TX_LOOKUP", "src/modules/tm/t_lookup.c", "t_lookup_request", 514,
        "after RFC3261 magic-cookie branch lookup path is selected", "transaction_lookup",
        ["request_with_magic_cookie_matches_existing_tx", "tx_lookup_existing_match"],
        "lookup tick", "method class, branch hash, sent-by hash, lookup result",
        "one compact event only on match/mismatch boundary", "",
    ),
    "HK_RETRANSMIT_REPLY": Hook(
        "HK_RETRANSMIT_REPLY", "src/modules/tm/t_reply.c", "t_retransmit_reply", 1689,
        "after SEND_PR_BUFFER for stored reply retransmission succeeds", "reply_retransmit",
        ["uas_retransmit_last_provisional", "noninvite_final_response_retransmitted"],
        "actual send-path tick", "status class, branch, transaction id, send result",
        "emit only after send success", "Do not treat function entry as already sent.",
    ),
    "HK_REPLY_RECEIVED": Hook(
        "HK_REPLY_RECEIVED", "src/modules/tm/t_reply.c", "reply_received", 2293,
        "after upstream response is matched to client transaction", "upstream_response",
        ["proxy_rx_100_trying_response"],
        "response receive tick", "status code/class, branch, transaction id",
        "one event per matched upstream response", "",
    ),
    "HK_RELAY_REPLY": Hook(
        "HK_RELAY_REPLY", "src/modules/tm/t_reply.c", "relay_reply", 1879,
        "when relay_reply classifies response and commits stored UAS status", "reply_process",
        [
            "invite_proceeding_tu_provisional",
            "invite_proceeding_tu_final_300_699",
            "invite_2xx_response_from_tu",
            "noninvite_tu_provisional",
            "noninvite_tu_final_response",
            "noninvite_tx_completed_final_sent",
            "proxy_forward_100_trying",
        ],
        "reply classification tick", "status code/class, branch, decision, stored uas.status",
        "classification-only; actual send is emitted by HK_SEND_PR_BUFFER", "",
    ),
    "HK_SEND_PR_BUFFER": Hook(
        "HK_SEND_PR_BUFFER", "src/modules/tm/t_funcs.c", "send_pr_buffer", 62,
        "after msg_send returns success for reply/request buffer", "wire_send",
        [
            "uas_tx_100_trying",
            "uas_tx_provisional_response",
            "invite_tx_completed_non2xx",
            "cancel_tx_200_ok",
            "original_invite_tx_487",
            "branch_cancel_sent",
        ],
        "actual send-path tick", "direction, method/status, transport, buffer kind, branch",
        "one compact event after send success; payload stores status class not reason phrase", "",
    ),
    "HK_FORWARD_NONACK": Hook(
        "HK_FORWARD_NONACK", "src/modules/tm/t_fwd.c", "t_forward_nonack", 1644,
        "CANCEL path enters original-transaction lookup/e2e_cancel", "cancel_process",
        ["cancel_matches_original_transaction", "cancel_matches_invite_before_final"],
        "CANCEL processing tick", "CANCEL transaction id, original INVITE transaction id if any, match flag",
        "emit only on CANCEL branch", "",
    ),
    "HK_E2E_CANCEL": Hook(
        "HK_E2E_CANCEL", "src/modules/tm/t_fwd.c", "e2e_cancel", 1270,
        "after original INVITE is marked canceled and before branch cancels/replies", "cancel_effect",
        ["original_invite_marked_cancelled", "cancel_tx_200_ok", "original_invite_tx_487"],
        "same callback tick", "original transaction id, cancel transaction id, branch mask, last_received summary",
        "one event per matched CANCEL", "",
    ),
    "HK_CANCEL_BRANCH": Hook(
        "HK_CANCEL_BRANCH", "src/modules/tm/t_cancel.c", "cancel_branch", 206,
        "before/after local branch CANCEL decision and SEND_BUFFER", "branch_cancel",
        ["branch_cancel_requested_without_provisional", "branch_cancel_sent"],
        "branch cancel decision tick", "branch id, last_received, force flag, send result",
        "hot path emits only decision bitset and status", "",
    ),
    "HK_TIMER_ARM": Hook(
        "HK_TIMER_ARM", "src/modules/tm/timer.h", "_set_fr_retr", 212,
        "after timer_add succeeds and rb->timer.t_active is set", "timer_arm",
        ["timer_l_64t1_armed", "timer_h_64t1_armed", "timer_j_64t1_armed"],
        "logical deadline tick stored with current monotonic base", "timer kind, timeout ms, fr_expire, retr_expire",
        "emit successful arm only; no JSON/string formatting", "ProfuzzBench patch disables timer processes, so callback observation needs reference profile.",
    ),
    "HK_TIMER_STOP": Hook(
        "HK_TIMER_STOP", "src/modules/tm/timer.h", "stop_rb_timers", 225,
        "after timer_del/flag mutation for response/request buffer", "timer_cancel",
        ["invite_tx_confirmed_ack_absorbed", "noninvite_retransmission_passed_to_tu"],
        "timer cancellation tick", "timer kind, transaction id, buffer role",
        "macro hook must be compiled as inline binary emission", "",
    ),
    "HK_PUT_ON_WAIT": Hook(
        "HK_PUT_ON_WAIT", "src/modules/tm/t_funcs.c", "put_on_wait", 117,
        "after wait_timer is added and wait_start stored", "wait_state",
        ["invite_tx_terminated_without_ack_or_timer_h", "noninvite_tx_completed_final_sent"],
        "wait-state commit tick", "transaction id, wait_timeout, wait_start, reason",
        "one event per wait transition", "Used to distinguish legal wait/termination from early discard.",
    ),
    "HK_T_REPLY_MATCHING": Hook(
        "HK_T_REPLY_MATCHING", "src/modules/tm/t_lookup.c", "t_reply_matching", 837,
        "after response branch/hash/callid/method matching succeeds", "response_match",
        ["proxy_response_context_matched"],
        "response matching tick", "hash index, branch id, method class, callid hash",
        "only emits on matched/fail boundary", "",
    ),
}


PROPS: List[Prop] = [
    Prop(
        "SIP-KAM-001", "INVITE server transaction", "UAS/server transaction",
        "A newly constructed INVITE server transaction enters Proceeding and exposes the request to the transaction user.",
        "MUST/state-machine", "RFC3261", "17.2.1",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "When a server transaction is constructed for an INVITE request, it starts in Proceeding and the request is passed upward.",
        "2", "adapter microstep expansion for same callback, not an RFC tolerance", "eventual",
        "server_rx_invite_new_tx", "invite_tx_proceeding",
        "G* (server_rx_invite_new_tx -> F [0,2] invite_tx_proceeding)",
        "G(server_rx_invite_new_tx -> F_[0,2ms] invite_tx_proceeding)",
        ["server_rx_invite_new_tx", "invite_tx_proceeding"], ["HK_RX_PARSE_OK", "HK_TX_NEW"], ["HK_TX_LOOKUP"],
        "Call-ID + CSeq number/method + top Via branch/sent-by", [(0, ["server_rx_invite_new_tx"]), (1, ["invite_tx_proceeding"])],
        [(0, ["server_rx_invite_new_tx"]), (3, ["invite_tx_proceeding"])],
        "white-box hook after parser and transaction creation", "high: catches transaction creation/routing regressions", "HIGH", "PENDING",
        "Should the benchmark count parser-rejected INVITEs separately from malformed-message oracles?",
    ),
    Prop(
        "SIP-KAM-002", "INVITE provisional response", "UAS/server transaction",
        "If INVITE processing may take longer than the RFC 200 ms window and no earlier TU response exists, emit 100 Trying.",
        "SHOULD with timer bound", "RFC3261", "17.2.1",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "The server transaction generates 100 Trying unless it knows the TU will respond within 200 ms.",
        "200", "RFC3261 section 17.2.1", "eventual",
        "invite_auto_100_obligation", "uas_tx_100_trying",
        "G* (invite_auto_100_obligation -> F [0,200] uas_tx_100_trying)",
        "G(invite_auto_100_obligation -> F_[0,200ms] uas_tx_100_trying)",
        ["invite_auto_100_obligation", "uas_tx_100_trying"], ["HK_RELAY_REPLY", "HK_SEND_PR_BUFFER"], ["HK_TX_NEW"],
        "same INVITE server transaction", [(0, ["invite_auto_100_obligation"]), (100, ["uas_tx_100_trying"])],
        [(0, ["invite_auto_100_obligation"]), (201, ["uas_tx_100_trying"])],
        "white-box send hook; black-box packet capture can cross-check", "medium/high: detects loss of early provisional feedback", "MEDIUM",
        "Kamailio auto_inv_100 and route-script behavior must be fixed in experiment profile.",
        "Does the chosen Kamailio cfg always enable auto_inv_100, or should this be a profile-specific property?",
    ),
    Prop(
        "SIP-KAM-003", "INVITE provisional relay", "UAS/proxy transaction",
        "A provisional 101-199 response selected by the transaction layer while INVITE is Proceeding is passed to transport.",
        "MUST/state-machine", "RFC3261", "17.2.1",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "In Proceeding, provisional responses from the TU are passed to the transport layer.",
        "2", "adapter microstep expansion", "eventual",
        "invite_proceeding_tu_provisional", "uas_tx_provisional_response",
        "G* (invite_proceeding_tu_provisional -> F [0,2] uas_tx_provisional_response)",
        "G(invite_proceeding_tu_provisional -> F_[0,2ms] uas_tx_provisional_response)",
        ["invite_proceeding_tu_provisional", "uas_tx_provisional_response"], ["HK_RELAY_REPLY", "HK_SEND_PR_BUFFER"], ["HK_REPLY_RECEIVED"],
        "same INVITE transaction and response branch", [(0, ["invite_proceeding_tu_provisional"]), (1, ["uas_tx_provisional_response"])],
        [(0, ["invite_proceeding_tu_provisional"]), (3, ["uas_tx_provisional_response"])],
        "send hook plus optional pcap", "high: detects swallowed provisional responses", "HIGH", "PENDING",
        "Confirm whether ProfuzzBench route exposes upstream provisional responses during fuzzing.",
    ),
    Prop(
        "SIP-KAM-004", "INVITE retransmission suppression", "UAS/server transaction",
        "A retransmitted INVITE in Proceeding retransmits the most recent provisional response instead of creating a fresh TU event.",
        "MUST/state-machine", "RFC3261", "17.2.1",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "If a request retransmission is received in Proceeding, the most recent provisional response is retransmitted.",
        "2", "adapter microstep expansion", "eventual",
        "invite_retransmission_in_proceeding_with_last_prov", "uas_retransmit_last_provisional",
        "G* (invite_retransmission_in_proceeding_with_last_prov -> F [0,2] uas_retransmit_last_provisional)",
        "G(invite_retransmission_in_proceeding_with_last_prov -> F_[0,2ms] uas_retransmit_last_provisional)",
        ["invite_retransmission_in_proceeding_with_last_prov", "uas_retransmit_last_provisional"], ["HK_TX_LOOKUP", "HK_RETRANSMIT_REPLY"], ["HK_SEND_PR_BUFFER"],
        "same branch/sent-by/method transaction key", [(0, ["invite_retransmission_in_proceeding_with_last_prov"]), (1, ["uas_retransmit_last_provisional"])],
        [(0, ["invite_retransmission_in_proceeding_with_last_prov"]), (3, ["uas_retransmit_last_provisional"])],
        "white-box transaction lookup and send hook", "high: catches duplicate transaction/TU re-entry bugs", "HIGH", "PENDING",
        "Need auxiliary counter to prove TU was not re-entered if using this as a bug claim.",
    ),
    Prop(
        "SIP-KAM-005", "INVITE final response", "UAS/server transaction",
        "A 300-699 final response from the TU moves INVITE server transaction to Completed and is sent.",
        "MUST/state-machine", "RFC3261", "17.2.1",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "When a 300 to 699 response is passed to the server transaction, it enters Completed and passes the response to transport.",
        "2", "adapter microstep expansion", "eventual",
        "invite_proceeding_tu_final_300_699", "invite_tx_completed_non2xx",
        "G* (invite_proceeding_tu_final_300_699 -> F [0,2] invite_tx_completed_non2xx)",
        "G(invite_proceeding_tu_final_300_699 -> F_[0,2ms] invite_tx_completed_non2xx)",
        ["invite_proceeding_tu_final_300_699", "invite_tx_completed_non2xx"], ["HK_RELAY_REPLY", "HK_SEND_PR_BUFFER"], ["HK_TIMER_ARM"],
        "same INVITE server transaction", [(0, ["invite_proceeding_tu_final_300_699"]), (1, ["invite_tx_completed_non2xx"])],
        [(0, ["invite_proceeding_tu_final_300_699"]), (3, ["invite_tx_completed_non2xx"])],
        "send hook and transaction status update", "high: detects final-response loss or wrong state", "HIGH", "PENDING",
        "For proxy mode, distinguish final response selected for upstream UAS from downstream branch final.",
    ),
    Prop(
        "SIP-KAM-006", "INVITE Timer H/lifetime", "UAS/server transaction",
        "After non-2xx Completed, the transaction must not be destroyed before ACK or Timer H expiry.",
        "MUST/state-machine timer", "RFC3261", "17.2.1 and Table 4",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "Timer H is 64*T1 for INVITE server transactions in Completed; ACK or timeout governs termination.",
        "32000", "64*T1 using RFC default T1=500 ms", "safety",
        "invite_tx_completed_non2xx", "invite_tx_terminated_without_ack_or_timer_h",
        "G* (invite_tx_completed_non2xx -> G [0,32000) (!invite_tx_terminated_without_ack_or_timer_h))",
        "G(invite_tx_completed_non2xx -> G_[0,32000ms) not early_terminated)",
        ["invite_tx_completed_non2xx", "invite_tx_terminated_without_ack_or_timer_h"], ["HK_SEND_PR_BUFFER", "HK_PUT_ON_WAIT"], ["HK_TIMER_ARM", "HK_TIMER_STOP"],
        "same INVITE server transaction", [(0, ["invite_tx_completed_non2xx"]), (1, [])],
        [(0, ["invite_tx_completed_non2xx"]), (1, ["invite_tx_terminated_without_ack_or_timer_h"])],
        "white-box wait/timer hooks; pcap alone cannot prove early destroy", "medium: detects premature state drop", "MEDIUM",
        "ProfuzzBench patch disables timer processes; callback expiry needs reference build, but early destroy remains observable.",
        "Should a test watchdog close the trace at 32s, or should unfinished obligations be UNKNOWN?",
    ),
    Prop(
        "SIP-KAM-007", "INVITE ACK handling", "UAS/server transaction",
        "An ACK matching a Completed INVITE server transaction moves it to Confirmed and stops response retransmission.",
        "MUST/state-machine", "RFC3261", "17.2.1",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.1",
        "When an ACK is received in Completed, the server transaction transitions to Confirmed.",
        "2", "adapter microstep expansion", "eventual",
        "invite_completed_rx_ack", "invite_tx_confirmed_ack_absorbed",
        "G* (invite_completed_rx_ack -> F [0,2] invite_tx_confirmed_ack_absorbed)",
        "G(invite_completed_rx_ack -> F_[0,2ms] invite_tx_confirmed_ack_absorbed)",
        ["invite_completed_rx_ack", "invite_tx_confirmed_ack_absorbed"], ["HK_TX_LOOKUP", "HK_TIMER_STOP"], ["HK_T_REPLY_MATCHING"],
        "same INVITE transaction; ACK matches INVITE method exception", [(0, ["invite_completed_rx_ack"]), (1, ["invite_tx_confirmed_ack_absorbed"])],
        [(0, ["invite_completed_rx_ack"]), (3, ["invite_tx_confirmed_ack_absorbed"])],
        "white-box lookup/timer-stop hook", "high: detects ACK misclassification", "HIGH", "PENDING",
        "Need separate AP for 2xx ACK, because RFC6026 Accepted ACK is passed upward rather than absorbed.",
    ),
    Prop(
        "SIP-KAM-008", "INVITE 2xx Accepted", "UAS/server transaction",
        "Under RFC6026, a 2xx to INVITE transitions the server transaction to Accepted and arms Timer L.",
        "MUST/update state-machine", "RFC6026", "7.1 and 8.7",
        "https://www.rfc-editor.org/rfc/rfc6026.html#section-7.1",
        "The update adds Accepted and Timer L; 2xx in Proceeding transitions to Accepted and Timer L is 64*T1.",
        "2", "adapter microstep expansion for transition; Timer L value is 64*T1=32000 ms", "eventual",
        "invite_2xx_response_from_tu", "timer_l_64t1_armed",
        "G* (invite_2xx_response_from_tu -> F [0,2] timer_l_64t1_armed)",
        "G(invite_2xx_response_from_tu -> F_[0,2ms] timer_l_64t1_armed)",
        ["invite_2xx_response_from_tu", "timer_l_64t1_armed"], ["HK_RELAY_REPLY", "HK_TIMER_ARM"], ["HK_SEND_PR_BUFFER"],
        "same INVITE server transaction", [(0, ["invite_2xx_response_from_tu"]), (1, ["timer_l_64t1_armed"])],
        [(0, ["invite_2xx_response_from_tu"]), (3, ["timer_l_64t1_armed"])],
        "white-box timer arm and response hook", "medium/high: RFC6026 conformance oracle", "MEDIUM",
        "Likely requires reference profile and manual audit because Kamailio may encode Accepted differently from RFC names.",
        "Can we observe an explicit Timer L equivalent, or must this be an excluded/extended property?",
    ),
    Prop(
        "SIP-KAM-009", "RFC6026 retransmitted INVITE in Accepted", "UAS/server transaction",
        "Retransmitted INVITEs in Accepted are absorbed by the transaction and not re-delivered to the TU.",
        "MUST/update state-machine", "RFC6026", "8.7",
        "https://www.rfc-editor.org/rfc/rfc6026.html#section-8.7",
        "The Accepted state absorbs retransmissions of the original INVITE and does not pass them to the TU.",
        "2", "adapter microstep expansion", "safety",
        "accepted_rx_invite_retransmission", "invite_retransmission_passed_to_tu",
        "G* (accepted_rx_invite_retransmission -> G [0,2] (!invite_retransmission_passed_to_tu))",
        "G(accepted_rx_invite_retransmission -> G_[0,2ms] not passed_to_tu)",
        ["accepted_rx_invite_retransmission", "invite_retransmission_passed_to_tu"], ["HK_TX_LOOKUP", "HK_TX_NEW"], ["HK_RETRANSMIT_REPLY"],
        "same INVITE branch/sent-by/method transaction key", [(0, ["accepted_rx_invite_retransmission"]), (1, [])],
        [(0, ["accepted_rx_invite_retransmission"]), (1, ["invite_retransmission_passed_to_tu"])],
        "white-box lookup plus route/TU boundary hook", "medium: detects duplicate TU delivery", "MEDIUM",
        "Requires route-boundary hook to prove non-delivery; absence of event alone is UNKNOWN if hooks dropped.",
        "Where should the TU delivery hook sit in Kamailio route execution for minimal perturbation?",
    ),
    Prop(
        "SIP-KAM-010", "RFC6026 ACK in Accepted", "UAS/server transaction",
        "ACKs in Accepted are passed directly to the TU rather than absorbed by the transaction layer.",
        "MUST/update state-machine", "RFC6026", "8.7",
        "https://www.rfc-editor.org/rfc/rfc6026.html#section-8.7",
        "ACK requests that match an Accepted transaction are passed directly to the TU.",
        "2", "adapter microstep expansion", "eventual",
        "accepted_rx_ack", "ack_passed_to_tu",
        "G* (accepted_rx_ack -> F [0,2] ack_passed_to_tu)",
        "G(accepted_rx_ack -> F_[0,2ms] ack_passed_to_tu)",
        ["accepted_rx_ack", "ack_passed_to_tu"], ["HK_TX_LOOKUP", "HK_RX_PARSE_OK"], ["HK_TIMER_STOP"],
        "same INVITE accepted transaction and ACK matching key", [(0, ["accepted_rx_ack"]), (1, ["ack_passed_to_tu"])],
        [(0, ["accepted_rx_ack"]), (3, ["ack_passed_to_tu"])],
        "white-box transaction lookup plus route/TU hook", "medium: detects wrong ACK absorption", "MEDIUM",
        "Needs manual confirmation of Kamailio route callback representing TU delivery.",
        "Should ACK-to-TU be considered a route-level event or a tm callback event in this SUT?",
    ),
    Prop(
        "SIP-KAM-011", "non-INVITE server transaction", "UAS/server transaction",
        "A newly constructed non-INVITE server transaction enters Trying and passes the request upward.",
        "MUST/state-machine", "RFC3261", "17.2.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2",
        "For non-INVITE requests, the server transaction starts in Trying and passes the request to the TU.",
        "2", "adapter microstep expansion", "eventual",
        "server_rx_noninvite_new_tx", "noninvite_tx_trying",
        "G* (server_rx_noninvite_new_tx -> F [0,2] noninvite_tx_trying)",
        "G(server_rx_noninvite_new_tx -> F_[0,2ms] noninvite_tx_trying)",
        ["server_rx_noninvite_new_tx", "noninvite_tx_trying"], ["HK_RX_PARSE_OK", "HK_TX_NEW"], ["HK_TX_LOOKUP"],
        "Call-ID + CSeq + top Via branch/sent-by", [(0, ["server_rx_noninvite_new_tx"]), (1, ["noninvite_tx_trying"])],
        [(0, ["server_rx_noninvite_new_tx"]), (3, ["noninvite_tx_trying"])],
        "white-box transaction creation", "high: covers OPTIONS/BYE/CANCEL class setup", "HIGH", "PENDING",
        "CANCEL is handled specially; property should exclude CANCEL when original-transaction semantics are being tested separately.",
    ),
    Prop(
        "SIP-KAM-012", "non-INVITE retransmission discard", "UAS/server transaction",
        "A retransmitted non-INVITE request in Trying is discarded, not delivered again to the TU.",
        "MUST/state-machine", "RFC3261", "17.2.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2",
        "In Trying, retransmissions of non-INVITE requests are discarded.",
        "2", "adapter microstep expansion", "safety",
        "noninvite_retransmission_in_trying", "noninvite_retransmission_passed_to_tu",
        "G* (noninvite_retransmission_in_trying -> G [0,2] (!noninvite_retransmission_passed_to_tu))",
        "G(noninvite_retransmission_in_trying -> G_[0,2ms] not passed_to_tu)",
        ["noninvite_retransmission_in_trying", "noninvite_retransmission_passed_to_tu"], ["HK_TX_LOOKUP", "HK_TIMER_STOP"], ["HK_RX_PARSE_OK"],
        "same non-INVITE transaction key", [(0, ["noninvite_retransmission_in_trying"]), (1, [])],
        [(0, ["noninvite_retransmission_in_trying"]), (1, ["noninvite_retransmission_passed_to_tu"])],
        "white-box lookup plus route/TU boundary hook", "medium/high: detects duplicate request processing", "MEDIUM", "PENDING",
        "Needs a route/TU delivery hook to avoid interpreting missing events under event drop as pass.",
    ),
    Prop(
        "SIP-KAM-013", "non-INVITE provisional response", "UAS/server transaction",
        "A provisional response for a non-INVITE transaction moves it to Proceeding and sends the response.",
        "MUST/state-machine", "RFC3261", "17.2.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2",
        "If a provisional response is passed to the non-INVITE server transaction, it enters Proceeding and passes it to transport.",
        "2", "adapter microstep expansion", "eventual",
        "noninvite_tu_provisional", "noninvite_tx_proceeding_response_sent",
        "G* (noninvite_tu_provisional -> F [0,2] noninvite_tx_proceeding_response_sent)",
        "G(noninvite_tu_provisional -> F_[0,2ms] noninvite_tx_proceeding_response_sent)",
        ["noninvite_tu_provisional", "noninvite_tx_proceeding_response_sent"], ["HK_RELAY_REPLY", "HK_SEND_PR_BUFFER"], ["HK_TX_LOOKUP"],
        "same non-INVITE transaction", [(0, ["noninvite_tu_provisional"]), (1, ["noninvite_tx_proceeding_response_sent"])],
        [(0, ["noninvite_tu_provisional"]), (3, ["noninvite_tx_proceeding_response_sent"])],
        "send hook plus status class", "medium: useful for OPTIONS/BYE provisional edge cases", "MEDIUM", "PENDING",
        "RFC says UAS SHOULD NOT generally send provisional for non-INVITE; this property applies only if TU emits one.",
    ),
    Prop(
        "SIP-KAM-014", "non-INVITE final response", "UAS/server transaction",
        "A final response to a non-INVITE server transaction enters Completed and is sent.",
        "MUST/state-machine", "RFC3261", "17.2.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2",
        "Final responses 200-699 cause Completed and are passed to transport.",
        "2", "adapter microstep expansion", "eventual",
        "noninvite_tu_final_response", "noninvite_tx_completed_final_sent",
        "G* (noninvite_tu_final_response -> F [0,2] noninvite_tx_completed_final_sent)",
        "G(noninvite_tu_final_response -> F_[0,2ms] noninvite_tx_completed_final_sent)",
        ["noninvite_tu_final_response", "noninvite_tx_completed_final_sent"], ["HK_RELAY_REPLY", "HK_SEND_PR_BUFFER"], ["HK_PUT_ON_WAIT"],
        "same non-INVITE transaction", [(0, ["noninvite_tu_final_response"]), (1, ["noninvite_tx_completed_final_sent"])],
        [(0, ["noninvite_tu_final_response"]), (3, ["noninvite_tx_completed_final_sent"])],
        "send hook plus wait-state hook", "high: core non-INVITE response oracle", "HIGH", "PENDING",
        "Need distinguish server-side final response from proxied branch final selected for forwarding.",
    ),
    Prop(
        "SIP-KAM-015", "non-INVITE retransmission in Completed", "UAS/server transaction",
        "A retransmitted non-INVITE request in Completed gets the stored final response retransmitted.",
        "MUST/state-machine", "RFC3261", "17.2.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.2",
        "In Completed, retransmissions are passed the final response previously sent.",
        "2", "adapter microstep expansion", "eventual",
        "noninvite_retransmission_in_completed", "noninvite_final_response_retransmitted",
        "G* (noninvite_retransmission_in_completed -> F [0,2] noninvite_final_response_retransmitted)",
        "G(noninvite_retransmission_in_completed -> F_[0,2ms] noninvite_final_response_retransmitted)",
        ["noninvite_retransmission_in_completed", "noninvite_final_response_retransmitted"], ["HK_TX_LOOKUP", "HK_RETRANSMIT_REPLY"], ["HK_SEND_PR_BUFFER"],
        "same non-INVITE transaction key", [(0, ["noninvite_retransmission_in_completed"]), (1, ["noninvite_final_response_retransmitted"])],
        [(0, ["noninvite_retransmission_in_completed"]), (3, ["noninvite_final_response_retransmitted"])],
        "lookup and send retransmission hook", "high: catches response cache/retransmission bugs", "HIGH", "PENDING",
        "Timer J expiry must be handled as legal supersession in long traces.",
    ),
    Prop(
        "SIP-KAM-016", "transaction matching", "UAS/proxy transaction layer",
        "Requests with RFC3261 magic-cookie branch and matching sent-by/method map to the existing transaction.",
        "MUST/matching rule", "RFC3261", "17.2.3",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-17.2.3",
        "With magic-cookie branch, matching uses branch, sent-by, and method, except ACK matches INVITE.",
        "2", "adapter microstep expansion", "eventual",
        "request_with_magic_cookie_matches_existing_tx", "tx_lookup_existing_match",
        "G* (request_with_magic_cookie_matches_existing_tx -> F [0,2] tx_lookup_existing_match)",
        "G(magic_cookie_match_candidate -> F_[0,2ms] tx_lookup_existing_match)",
        ["request_with_magic_cookie_matches_existing_tx", "tx_lookup_existing_match"], ["HK_TX_LOOKUP"], ["HK_RX_PARSE_OK"],
        "top Via branch/sent-by + CSeq method exception + transaction bucket/hash", [(0, ["request_with_magic_cookie_matches_existing_tx"]), (1, ["tx_lookup_existing_match"])],
        [(0, ["request_with_magic_cookie_matches_existing_tx"]), (3, ["tx_lookup_existing_match"])],
        "white-box lookup; pcap can provide candidate fields", "high: prevents transaction-key explosion/ambiguity", "HIGH", "PENDING",
        "AP names exclude dynamic branch values; fields live only in correlation metadata.",
    ),
    Prop(
        "SIP-KAM-017", "CANCEL matched response", "UAS/proxy transaction layer",
        "A CANCEL that matches an existing transaction receives a 200 OK to the CANCEL itself.",
        "SHOULD/MUST behavior", "RFC3261", "9.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-9.2",
        "If a matching transaction exists, the UAS first processes the CANCEL and then answers the CANCEL with 200 OK.",
        "2", "adapter microstep expansion", "eventual",
        "cancel_matches_original_transaction", "cancel_tx_200_ok",
        "G* (cancel_matches_original_transaction -> F [0,2] cancel_tx_200_ok)",
        "G(cancel_matches_original_transaction -> F_[0,2ms] cancel_tx_200_ok)",
        ["cancel_matches_original_transaction", "cancel_tx_200_ok"], ["HK_FORWARD_NONACK", "HK_E2E_CANCEL", "HK_SEND_PR_BUFFER"], ["HK_TX_LOOKUP"],
        "CANCEL transaction + matched original transaction", [(0, ["cancel_matches_original_transaction"]), (1, ["cancel_tx_200_ok"])],
        [(0, ["cancel_matches_original_transaction"]), (3, ["cancel_tx_200_ok"])],
        "white-box cancel path plus send hook", "high: explicit SIP CANCEL oracle", "HIGH", "PENDING",
        "Separate this from 487 to the original INVITE; both may occur in the same callback.",
    ),
    Prop(
        "SIP-KAM-018", "CANCEL effect on INVITE", "UAS/proxy transaction layer",
        "A matching CANCEL received before final response to an INVITE causes the original INVITE to receive 487.",
        "SHOULD behavior", "RFC3261", "9.2",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-9.2",
        "If no final response has been sent for the INVITE, the UAS behavior SHOULD generate a 487 response.",
        "2", "adapter microstep expansion", "eventual",
        "cancel_matches_invite_before_final", "original_invite_tx_487",
        "G* (cancel_matches_invite_before_final -> F [0,2] original_invite_tx_487)",
        "G(cancel_matches_invite_before_final -> F_[0,2ms] original_invite_tx_487)",
        ["cancel_matches_invite_before_final", "original_invite_tx_487"], ["HK_FORWARD_NONACK", "HK_E2E_CANCEL", "HK_SEND_PR_BUFFER"], ["HK_CANCEL_BRANCH"],
        "CANCEL transaction + original INVITE transaction", [(0, ["cancel_matches_invite_before_final"]), (1, ["original_invite_tx_487"])],
        [(0, ["cancel_matches_invite_before_final"]), (3, ["original_invite_tx_487"])],
        "white-box cancel effect and send hook; pcap cross-check", "high: protocol-visible violation", "HIGH", "PENDING",
        "If downstream branch already sent a final response, this obligation must be suppressed by correlation state.",
    ),
    Prop(
        "SIP-KAM-019", "proxy branch CANCEL gating", "stateful proxy/client transaction",
        "A stateful proxy should only generate branch CANCEL after a provisional response makes that branch cancelable.",
        "MUST/MAY constrained by RFC9.1/16.10", "RFC3261", "9.1 and 16.10",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-16.10",
        "A stateful proxy cancels pending client transactions, subject to the caller-side CANCEL rule that a provisional response was received.",
        "2", "adapter microstep expansion", "safety",
        "branch_cancel_requested_without_provisional", "branch_cancel_sent",
        "G* (branch_cancel_requested_without_provisional -> G [0,2] (!branch_cancel_sent))",
        "G(branch_cancel_requested_without_provisional -> G_[0,2ms] not branch_cancel_sent)",
        ["branch_cancel_requested_without_provisional", "branch_cancel_sent"], ["HK_CANCEL_BRANCH", "HK_E2E_CANCEL"], ["HK_REPLY_RECEIVED"],
        "client branch id derived after transaction correlation", [(0, ["branch_cancel_requested_without_provisional"]), (1, [])],
        [(0, ["branch_cancel_requested_without_provisional"]), (1, ["branch_cancel_sent"])],
        "white-box branch state and send hook", "medium/high: avoids illegal early downstream CANCEL", "MEDIUM",
        "Manual review must classify force/local-cancel modes that intentionally deviate.",
        "Should forced local CANCEL paths be excluded from the main property or modeled as legal supersession?",
    ),
    Prop(
        "SIP-KAM-020", "proxy 100 Trying forwarding", "stateful proxy",
        "A stateful proxy must not immediately forward 100 Trying responses upstream.",
        "MUST NOT/proxy response processing", "RFC3261", "16.7",
        "https://www.rfc-editor.org/rfc/rfc3261.html#section-16.7",
        "Stateful proxies forward provisional responses except 100 Trying; 100 Trying is not immediately forwarded.",
        "2", "adapter microstep expansion", "safety",
        "proxy_rx_100_trying_response", "proxy_forward_100_trying",
        "G* (proxy_rx_100_trying_response -> G [0,2] (!proxy_forward_100_trying))",
        "G(proxy_rx_100_trying_response -> G_[0,2ms] not proxy_forward_100_trying)",
        ["proxy_rx_100_trying_response", "proxy_forward_100_trying"], ["HK_REPLY_RECEIVED", "HK_RELAY_REPLY"], ["HK_SEND_PR_BUFFER"],
        "response branch matched to proxy response context", [(0, ["proxy_rx_100_trying_response"]), (1, [])],
        [(0, ["proxy_rx_100_trying_response"]), (1, ["proxy_forward_100_trying"])],
        "upstream response hook plus actual send hook", "high: externally visible proxy violation", "HIGH", "PENDING",
        "Needs send-direction metadata to avoid confusing downstream 100 generation with upstream forwarding.",
    ),
]


AP_DESCRIPTIONS: Dict[str, str] = {
    "server_rx_invite_new_tx": "Parsed inbound INVITE causes a new server transaction candidate after correlation finds no existing transaction.",
    "invite_tx_proceeding": "Derived RFC state event emitted after Kamailio creates the INVITE server transaction.",
    "invite_auto_100_obligation": "Profile guard: INVITE processing is expected to take longer than 200 ms and no earlier TU response has been emitted.",
    "uas_tx_100_trying": "A 100 Trying response for the correlated INVITE was actually sent.",
    "invite_proceeding_tu_provisional": "Transaction layer receives/selects a 101-199 response while the INVITE transaction is Proceeding.",
    "uas_tx_provisional_response": "A provisional response other than 100 Trying was actually sent for the correlated INVITE.",
    "invite_retransmission_in_proceeding_with_last_prov": "Retransmitted INVITE matches a Proceeding transaction with a stored provisional response.",
    "uas_retransmit_last_provisional": "Stored provisional response was retransmitted for the matched INVITE transaction.",
    "invite_proceeding_tu_final_300_699": "TU/relay provides a 300-699 final response for an INVITE in Proceeding.",
    "invite_tx_completed_non2xx": "A non-2xx final INVITE response was committed and sent; transaction enters Completed profile.",
    "invite_tx_terminated_without_ack_or_timer_h": "Illegal derived event: state is destroyed before matching ACK or Timer H expiry.",
    "invite_completed_rx_ack": "ACK matches an INVITE transaction currently in Completed.",
    "invite_tx_confirmed_ack_absorbed": "ACK is absorbed by transaction layer and response retransmission timers are stopped.",
    "invite_2xx_response_from_tu": "TU/relay emits a 2xx final response for an INVITE server transaction.",
    "timer_l_64t1_armed": "Derived timer event: an RFC6026 Timer L-equivalent 64*T1 retention timer is successfully armed.",
    "accepted_rx_invite_retransmission": "Retransmitted INVITE matches a transaction in RFC6026 Accepted-equivalent retention profile.",
    "invite_retransmission_passed_to_tu": "Illegal derived event: retransmitted INVITE reaches route/TU boundary again.",
    "accepted_rx_ack": "ACK matches an INVITE transaction in RFC6026 Accepted-equivalent profile.",
    "ack_passed_to_tu": "ACK is delivered to the transaction user/route layer.",
    "server_rx_noninvite_new_tx": "Parsed inbound non-INVITE request creates a new non-INVITE server transaction candidate.",
    "noninvite_tx_trying": "Derived RFC state event emitted after non-INVITE server transaction creation.",
    "noninvite_retransmission_in_trying": "Retransmitted non-INVITE request matches a transaction in Trying.",
    "noninvite_retransmission_passed_to_tu": "Illegal derived event: non-INVITE retransmission reaches route/TU boundary again.",
    "noninvite_tu_provisional": "TU emits a provisional response for a non-INVITE server transaction.",
    "noninvite_tx_proceeding_response_sent": "Non-INVITE transaction enters Proceeding profile and sends provisional response.",
    "noninvite_tu_final_response": "TU emits final response for non-INVITE transaction.",
    "noninvite_tx_completed_final_sent": "Final response for non-INVITE transaction was sent and Completed/wait profile begins.",
    "noninvite_retransmission_in_completed": "Retransmitted non-INVITE request matches a Completed transaction.",
    "noninvite_final_response_retransmitted": "Stored final response for non-INVITE transaction was retransmitted.",
    "request_with_magic_cookie_matches_existing_tx": "Incoming request has RFC3261 magic-cookie branch and fields matching an existing transaction.",
    "tx_lookup_existing_match": "Kamailio transaction lookup returns existing transaction rather than creating a new one.",
    "cancel_matches_original_transaction": "CANCEL request is correlated to an existing original transaction.",
    "cancel_tx_200_ok": "200 OK response to the CANCEL request itself was actually sent.",
    "cancel_matches_invite_before_final": "CANCEL matches an original INVITE before a final response has been sent.",
    "original_invite_tx_487": "487 response to the original INVITE was actually sent.",
    "branch_cancel_requested_without_provisional": "Branch cancellation is requested while branch has not received any provisional response.",
    "branch_cancel_sent": "A downstream branch CANCEL request was actually sent.",
    "proxy_rx_100_trying_response": "Stateful proxy receives/matches a downstream 100 Trying response.",
    "proxy_forward_100_trying": "Illegal event: stateful proxy forwards a 100 Trying response upstream.",
}


def trace_text(events: List[Tuple[int, List[str]]]) -> str:
    lines = ["time,props"]
    for t, aps in events:
        if aps:
            lines.append(f"{t},{{{','.join(aps)}}}")
        else:
            lines.append(f"{t},{{}}")
    return "\n".join(lines) + "\n"


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def validate_property(prop: Prop) -> Dict[str, object]:
    vdir = OUT / "validation" / prop.pid
    vdir.mkdir(parents=True, exist_ok=True)
    formula_path = vdir / "formula.mitppl"
    pos_path = vdir / "positive.trace"
    neg_path = vdir / "negative.trace"
    formula_path.write_text(prop.formula + "\n", encoding="utf-8")
    pos_path.write_text(trace_text(prop.positive_trace), encoding="utf-8")
    neg_path.write_text(trace_text(prop.negative_trace), encoding="utf-8")

    build_out = vdir / "build_only"
    rc, stdout, stderr = run_cmd([
        str(TAMONITOR), "--formula", str(formula_path), "--word", "finite",
        "--build-mode", "flatten", "--build-only", "--out", str(build_out)
    ])
    (vdir / "build_only.stdout").write_text(stdout, encoding="utf-8")
    (vdir / "build_only.stderr").write_text(stderr, encoding="utf-8")

    row: Dict[str, object] = {
        "property_id": prop.pid,
        "build_rc": rc,
        "build_status": "PASS" if rc == 0 else "FAIL",
        "positive_symbolic": "SKIPPED",
        "negative_symbolic": "SKIPPED",
        "positive_concrete": "SKIPPED",
        "negative_concrete": "SKIPPED",
        "symbolic_concrete_consistent": "NO",
        "positive_locations": "",
        "positive_edges": "",
        "negative_locations": "",
        "negative_edges": "",
        "positive_clocks": "",
        "negative_clocks": "",
        "proposition_order": "",
        "notes": "",
    }
    if rc != 0:
        row["notes"] = stderr.strip()[:300]
        return row

    verdicts: Dict[str, str] = {}
    metadata_for_stats = None
    for trace_name, trace_path, expected in [
        ("positive", pos_path, "POSITIVE"),
        ("negative", neg_path, "NEGATIVE"),
    ]:
        for state in ["symbolic", "concrete"]:
            out_dir = vdir / f"{trace_name}_{state}"
            rc2, stdout2, stderr2 = run_cmd([
                str(TAMONITOR), "--formula", str(formula_path), "--trace", str(trace_path),
                "--word", "finite", "--build-mode", "flatten", "--state", state,
                "--out", str(out_dir)
            ])
            (vdir / f"{trace_name}_{state}.stdout").write_text(stdout2, encoding="utf-8")
            (vdir / f"{trace_name}_{state}.stderr").write_text(stderr2, encoding="utf-8")
            m = re.search(r"Final verdict: (\w+)", stdout2)
            verdict = m.group(1) if m else f"RC_{rc2}"
            verdicts[f"{trace_name}_{state}"] = verdict
            row[f"{trace_name}_{state}"] = "PASS" if verdict == expected and rc2 == 0 else f"FAIL:{verdict}"
            meta_path = out_dir / "metadata.json"
            if meta_path.exists() and metadata_for_stats is None:
                metadata_for_stats = json.loads(meta_path.read_text(encoding="utf-8"))

    row["symbolic_concrete_consistent"] = (
        "YES" if verdicts.get("positive_symbolic") == verdicts.get("positive_concrete")
        and verdicts.get("negative_symbolic") == verdicts.get("negative_concrete") else "NO"
    )
    if metadata_for_stats:
        ps = metadata_for_stats.get("positive_stats", {})
        ns = metadata_for_stats.get("negative_stats", {})
        row["positive_locations"] = ps.get("locations", "")
        row["positive_edges"] = ps.get("edges", "")
        row["positive_clocks"] = ps.get("clocks", "")
        row["negative_locations"] = ns.get("locations", "")
        row["negative_edges"] = ns.get("edges", "")
        row["negative_clocks"] = ns.get("clocks", "")
        row["proposition_order"] = "|".join(metadata_for_stats.get("proposition_order", []))
    return row


def write_csv(path: Path, rows: List[Dict[str, object]], fields: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def prop_row(p: Prop) -> Dict[str, object]:
    return {
        "property_id": p.pid,
        "category": p.category,
        "role": p.role,
        "requirement": p.requirement,
        "source_strength": p.strength,
        "rfc": p.rfc,
        "section": p.section,
        "rfc_url": p.rfc_url,
        "rfc_excerpt_summary": p.excerpt,
        "time_bound_ms": p.time_bound_ms,
        "time_source": p.time_source,
        "mathematical_mitl": p.math_formula,
        "mightyppl_formula": p.formula,
        "formula_kind": p.kind,
        "trigger_ap": p.trigger,
        "outcome_or_bad_ap": p.outcome,
        "ap_set": "|".join(p.aps),
        "correlation_key": p.correlation_key,
        "primary_hooks": "|".join(p.hooks),
        "auxiliary_hooks": "|".join(p.aux_hooks),
        "positive_timed_word": trace_text(p.positive_trace).replace("\n", "\\n"),
        "negative_timed_word": trace_text(p.negative_trace).replace("\n", "\\n"),
        "observability": p.observability,
        "oracle_value": p.oracle_value,
        "confidence": p.confidence,
        "human_review_status": p.caveat,
        "review_question": p.review_question,
    }


def write_markdown_catalog(path: Path) -> None:
    lines = [
        "# Kamailio/SIP MITL Property Catalog (independent reanalysis)",
        "",
        f"- Generated: {ACCESS_DATE}",
        f"- Kamailio fixed commit: `{KAM_COMMIT}`",
        f"- ProfuzzBench fixed commit: `{PROFUZZ_COMMIT}`",
        "- Scope: SIP server/UAS/stateful-proxy properties for Kamailio/ProfuzzBench; no historical SIP catalog is reused.",
        "- Semantics: pointwise finite timed words, integer milliseconds, complete AP valuation; dynamic SIP IDs are metadata only.",
        "- Review status: every property remains `PENDING` until the user signs off.",
        "",
    ]
    for p in PROPS:
        lines.extend([
            f"## {p.pid}: {p.requirement}",
            "",
            f"- Category/role: {p.category}; {p.role}",
            f"- RFC source: [{p.rfc} {p.section}]({p.rfc_url}) — {p.strength}",
            f"- Evidence summary: {p.excerpt}",
            f"- Time bound: `{p.time_bound_ms}` ms; source: {p.time_source}",
            f"- MightyPPL: `{p.formula}`",
            f"- Mathematical MITL: `{p.math_formula}`",
            f"- APs: `{', '.join(p.aps)}`",
            f"- Correlation: {p.correlation_key}",
            f"- Primary hooks: {', '.join(p.hooks)}",
            f"- Auxiliary hooks: {', '.join(p.aux_hooks)}",
            f"- Positive timed word: `{trace_text(p.positive_trace).strip().replace(chr(10), ' ; ')}`",
            f"- Negative timed word: `{trace_text(p.negative_trace).strip().replace(chr(10), ' ; ')}`",
            f"- Observability/oracle: {p.observability}; {p.oracle_value}",
            f"- Caveat/review: {p.caveat}; {p.review_question}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ap_yaml(path: Path) -> None:
    lines = [
        "# Generated independent AP map for Kamailio/SIP MITL study.",
        "time_unit: ms",
        "valuation_policy: complete_pointwise; absent AP is false",
        "dynamic_fields_policy: Call-ID, CSeq, Via branch, sent-by, branch index, tags are correlation metadata only",
        "atomic_propositions:",
    ]
    used = sorted({ap for p in PROPS for ap in p.aps})
    illegal_aps = {
        "invite_tx_terminated_without_ack_or_timer_h",
        "invite_retransmission_passed_to_tu",
        "noninvite_retransmission_passed_to_tu",
        "branch_cancel_sent",
        "proxy_forward_100_trying",
    }
    for ap in used:
        hook_ids = sorted({hid for hid, h in HOOKS.items() if ap in h.emits})
        if not hook_ids:
            hook_ids = sorted({hid for p in PROPS if ap in p.aps for hid in p.hooks})
        lines.extend([
            f"  - ap: {ap}",
            f"    kind: {'illegal_derived' if ap in illegal_aps else 'observable_or_derived_event'}",
            f"    meaning: {AP_DESCRIPTIONS.get(ap, 'TODO: AP description missing')}",
            f"    primary_hooks: [{', '.join(hook_ids)}]",
            "    correlation_metadata: [call_id_hash, cseq_number, cseq_method, via_branch_hash, sent_by_hash, transaction_id, branch_id]",
            "    alphabet_note: dynamic identifiers never appear in the AP name",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit() -> None:
    sources = [
        ("RFC3261", CACHE / "rfc3261.txt", "https://www.rfc-editor.org/rfc/rfc3261.txt"),
        ("RFC6026", CACHE / "rfc6026.txt", "https://www.rfc-editor.org/rfc/rfc6026.txt"),
        ("RFC3261 errata", CACHE / "rfc3261_errata.html", "https://www.rfc-editor.org/errata/rfc3261"),
        ("RFC6026 errata", CACHE / "rfc6026_errata.html", "https://www.rfc-editor.org/errata/rfc6026"),
        ("Kamailio commit JSON", CACHE / "kamailio_2648eb330b_commit.json", f"https://api.github.com/repos/kamailio/kamailio/commits/{KAM_COMMIT}"),
        ("Kamailio tarball", KAM_TARBALL, f"https://github.com/kamailio/kamailio/archive/{KAM_COMMIT}.tar.gz"),
        ("ProfuzzBench Dockerfile", PROFUZZ / "Dockerfile", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/Dockerfile"),
        ("ProfuzzBench StateAFL Dockerfile", PROFUZZ / "Dockerfile-stateafl", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/Dockerfile-stateafl"),
        ("ProfuzzBench README", PROFUZZ / "README.md", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/README.md"),
        ("ProfuzzBench Kamailio patch", PROFUZZ / "kamailio.patch", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/kamailio.patch"),
        ("ProfuzzBench run.sh", PROFUZZ / "run.sh", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/run.sh"),
        ("ProfuzzBench run-stateafl.sh", PROFUZZ / "run-stateafl.sh", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/run-stateafl.sh"),
        ("ProfuzzBench cov_script.sh", PROFUZZ / "cov_script.sh", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/cov_script.sh"),
        ("ProfuzzBench run_pjsip.sh", PROFUZZ / "run_pjsip.sh", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/run_pjsip.sh"),
        ("ProfuzzBench kamailio-basic.cfg", PROFUZZ / "kamailio-basic.cfg", f"https://github.com/profuzzbench/profuzzbench/blob/{PROFUZZ_COMMIT}/subjects/SIP/Kamailio/kamailio-basic.cfg"),
    ]
    lines = [
        "# SIP/Kamailio RFC and source audit",
        "",
        "This audit is independent of the historical SIP catalog in this workspace.",
        "",
        "## Evidence manifest summary",
        "",
        "| ID | Source | SHA-256 | Access date |",
        "|---|---|---:|---|",
    ]
    yaml = ["access_date: '2026-07-13'", "sources:"]
    for sid, path, url in sources:
        exists = path.exists()
        digest = sha256_file(path) if exists else "MISSING"
        lines.append(f"| {sid} | [{path.name}]({url}) | `{digest}` | {ACCESS_DATE} |")
        yaml.extend([
            f"  - id: {json.dumps(sid)}",
            f"    source_type: {'standard' if sid.startswith('RFC') else 'artifact_or_source'}",
            f"    url: {json.dumps(url)}",
            f"    local_path: {json.dumps(str(path))}",
            f"    sha256: {json.dumps(digest)}",
            f"    access_date: {ACCESS_DATE}",
        ])
    lines.extend([
        "",
        "## Fixed implementation and benchmark facts",
        "",
        f"- Kamailio source commit: `{KAM_COMMIT}` ([GitHub commit](https://github.com/kamailio/kamailio/commit/{KAM_COMMIT})).",
        f"- ProfuzzBench source commit: `{PROFUZZ_COMMIT}`.",
        "- ProfuzzBench SIP/Kamailio Dockerfile pins Kamailio with `git checkout 2648eb3` and builds AFLNet/AFLnwe plus a gcov build.",
        "- ProfuzzBench StateAFL Dockerfile creates a second Kamailio build for StateAFL adaptation.",
        "- `kamailio.patch` disables the normal timer and slow-timer child processes and fixes the PRNG seed. Therefore timer callback properties need a reference build or profile caveat; this catalog does not pretend the patched campaign can observe every timer expiry.",
        "",
        "## RFC sections used",
        "",
        "- RFC3261 §17.2.1 INVITE server transaction: Proceeding/Completed/Confirmed, 100 Trying, retransmission, Timer H/I.",
        "- RFC3261 §17.2.2 non-INVITE server transaction: Trying/Proceeding/Completed, Timer J and retransmission behavior.",
        "- RFC3261 §17.2.3 transaction matching: magic-cookie branch, sent-by, method exception for ACK.",
        "- RFC3261 §9.2 CANCEL server behavior.",
        "- RFC3261 §16.7 and §16.10 stateful proxy response/CANCEL behavior.",
        "- RFC6026 §7.1/§8.7 Accepted state and Timer L update for INVITE 2xx.",
        "",
        "## Source mapping principle",
        "",
        "APs are observable event predicates, not raw C variables.  Hooks are placed after protocol facts are committed: parse success, transaction creation/match, successful timer arm/cancel, and actual send-path success.",
    ])
    (OUT / "sip_kamailio_rfc_source_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "evidence_manifest.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")


def write_source_line_verification() -> None:
    rows: List[Dict[str, object]] = []
    with tarfile.open(KAM_TARBALL, "r:gz") as tar:
        for h in HOOKS.values():
            member_name = KAM_TAR_PREFIX + h.file
            try:
                extracted = tar.extractfile(member_name)
            except KeyError:
                rows.append({
                    "hook_id": h.hook_id,
                    "file": h.file,
                    "line": h.line,
                    "status": "MISSING_FILE_IN_TARBALL",
                    "line_text": "",
                    "function_or_symbol": h.function,
                    "source_url": h.url,
                })
                continue
            assert extracted is not None
            lines = extracted.read().decode("utf-8", errors="replace").splitlines()
            if 1 <= h.line <= len(lines):
                window = "\n".join(lines[max(0, h.line - 220):min(len(lines), h.line + 80)])
                symbol_seen = h.function in window
                status = "PASS" if symbol_seen else "LINE_PASS_SYMBOL_NOT_IN_WINDOW"
                line_text = lines[h.line - 1].strip()
            else:
                status = "BAD_LINE"
                line_text = ""
            rows.append({
                "hook_id": h.hook_id,
                "file": h.file,
                "line": h.line,
                "status": status,
                "line_text": line_text,
                "function_or_symbol": h.function,
                "source_url": h.url,
            })
    write_csv(OUT / "source_line_verification.csv", rows, [
        "hook_id", "file", "line", "status", "line_text", "function_or_symbol", "source_url"
    ])


def write_plan_docs(validation_rows: List[Dict[str, object]]) -> None:
    (OUT / "timed_word_semantics.md").write_text(
        """# Timed-word semantics for Kamailio/SIP reanalysis

- Input model: pointwise finite timed word over complete AP valuations.
- Time unit: integer milliseconds.  RFC constants are converted to ms; 64*T1 uses the RFC default T1=500 ms unless the experiment profile explicitly overrides T1.
- Same-callback protocol events are represented using a deterministic adapter microstep expansion over a small `[0,2]` ms observation window.  This is not a network tolerance and must not be used to excuse late real-time behavior.
- Dynamic SIP identifiers (`Call-ID`, `CSeq`, Via `branch`, tags, sent-by, branch index) are correlation metadata only.  They never enter AP names or the automaton alphabet.
- Adapter order: packet/timer hook -> ProtocolEvent -> correlation -> per-property projection -> complete valuation timed word -> MightyPPL/MoniTAal monitor -> PTA prefix guidance.
- Missing hook data is `UNKNOWN` in the real oracle.  The validation traces here are synthetic positive/negative examples for formula construction only.
- Punctual intervals `[a,a]` are not used in the main catalog.  Deadline-exact claims would need an MTL/MITPPL extended appendix and timestamp-uncertainty policy.
""",
        encoding="utf-8",
    )
    (OUT / "low_overhead_instrumentation_plan.md").write_text(
        """# Low-overhead instrumentation plan

Instrumentation should record compact binary events inside Kamailio and defer all JSON/string work to an offline adapter.

## Hot-path event record

Recommended fixed-size fields:

`timestamp_tick, session_id, transaction_id, branch_id, hook_id, direction, event_type, method_or_status_class, flags, correlation_hashes`

Use a single monotonic clock source for all hooks.  If pcap timestamps are also used, keep both timestamps plus uncertainty metadata; do not coerce uncertain time into a precise formal verdict.

## Emission strategy

- Thread-local or per-process SPSC ring buffer.
- No global lock in send/lookup hot paths.
- No heap allocation, JSON, reason-phrase formatting, or dynamic AP name generation in Kamailio.
- Batch export to sidecar; dropped events mark affected properties `UNKNOWN`.
- Hook after facts are committed: parse success, transaction creation/match, successful send, successful timer arm/cancel.

## Timer caveat

ProfuzzBench's Kamailio patch disables timer child processes.  Timer-arm and early-destroy properties can still be observed in the patched target, but timer-expiry/callback claims need a reference profile.  Fuzzing guidance may use PTA cost with uncertain timestamps; formal verdicts must remain three-valued when timestamp error overlaps a deadline.

## Performance gate

Measure hooks/event, bytes/test, monitor overhead, and PTA prefix query P50/P95/P99.  If synchronous guidance P95 exceeds 1 ms, switch to batch/asynchronous guidance and keep crash/MITL verdict replay offline.
""",
        encoding="utf-8",
    )
    (OUT / "kamailio_baseline_comparison_plan.md").write_text(
        f"""# Kamailio baseline comparison plan

Primary comparable target: ProfuzzBench SIP/Kamailio at commit `{PROFUZZ_COMMIT}`, which pins Kamailio `{KAM_COMMIT[:7]}`.

## Two required experiment profiles

### PFB-COMPAT

Use the original ProfuzzBench subject without restoring timer children.  This profile is for coverage/throughput comparison with public artifacts only.  It must not be used to claim RFC timer-expiry conformance because `kamailio.patch` disables the main and slow timer processes and the fuzzer run kills the SUT after short testcases.

### MITL-VALID

Keep the same Kamailio commit but use a reference profile that restores timer behavior, fixes the route script/peer behavior needed by the selected properties, and records the same ProtocolEvent stream for every fuzzer.  This profile is for MITL violation/time-to-first-violation claims.

## Baselines

1. AFLNet through ProfuzzBench SIP/Kamailio.  Subject README runs 4 AFLNet instances for 3600 s and 5 repeats with `-P SIP -l 5061 -D 50000 -q 3 -s 3 -E -K`.
2. AFLnwe through the same ProfuzzBench subject as the no-state-feedback control.
3. StateAFL through `Dockerfile-stateafl` in the same subject.  It is a same-SUT public state-feedback baseline, but its original Kamailio state signal is weak and should not be described as a strong protocol-state oracle.
4. NSFuzz is the preferred third advanced baseline if the official artifact can be audited locally: it reports the same Kamailio `2648eb3` line and has public Kamailio scripts/images, but the large image must be downloaded and hashed before being promoted from `CONDITIONAL`.
5. ChatAFL is a backup/appendix baseline: it has Kamailio scripts but uses a different Kamailio commit, depends on external LLM behavior, and also disables timers in its compatibility setup.
6. SGFuzz should be excluded from the main comparison unless a new adapter is built and disclosed; its public setup does not provide a Kamailio/SIP UDP/fork-compatible path.

## Common experiment contract

- Same Kamailio commit, ProfuzzBench patch, seeds, reset script, UDP endpoint, timeout, hardware, and coverage collector.
- For MITL-VALID, the same reference timer patch/profile, route script, peer, reset, and ProtocolEvent collector must be used by all tools.
- Metrics: edge/branch coverage, protocol state/transition coverage, automaton state/edge coverage, unique MITL violation, unique crash, sanitizer finding, time-to-first, exec/s, monitor overhead.
- Ablations: no MITL, boolean verdict only, automaton coverage, PTA cost-to-go only, full TAFuzz.
- Pilot: 10% of full campaign time, 3 repeats, debugging only.  Full budget should follow the newest complete artifact using this same SUT.
- Statistics: median, IQR, bootstrap 95% CI, Mann-Whitney U with Holm correction, Vargha-Delaney A12.

## Fairness caveats

- Run the MITL oracle offline for all tools, not only TAFuzz, otherwise inputs that violate a property but do not increase ordinary coverage will be undercounted for baselines.
- AFLNet's SIP framing in the public fork recognizes only a small method subset; MITL-VALID should use a unified SIP start-line/header/Content-Length framer for every tool.
- StateAFL/NSFuzz state counts are not directly comparable to MITL automaton-state coverage; report them in separate columns.
""",
        encoding="utf-8",
    )
    (OUT / "semantic_exclusions.md").write_text(
        """# Semantic exclusions and caveats

- No STL/ZOH continuous signal semantics are introduced.
- No dynamic SIP identifier enters the AP alphabet.
- Timer callback/expiry properties are not claimed for the ProfuzzBench patched Kamailio target unless a reference timer profile is used.
- Unfinished obligations at test end are `UNKNOWN` unless the harness explicitly closes the trace with a watchdog timeout event.
- RFC6026 Accepted/Timer L properties are retained as review candidates.  They require manual confirmation that Kamailio's internal retention state is equivalent to the RFC Accepted state.
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    validation_rows = [validate_property(p) for p in PROPS]

    prop_rows = [prop_row(p) for p in PROPS]
    write_csv(OUT / "mitl_property_catalog.csv", prop_rows, list(prop_rows[0].keys()))
    (OUT / "mitl_property_catalog.json").write_text(json.dumps([p.__dict__ for p in PROPS], ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_catalog(OUT / "mitl_property_catalog.md")

    hook_rows = [
        {
            "hook_id": h.hook_id,
            "file": h.file,
            "function": h.function,
            "line": h.line,
            "source_url": h.url,
            "phase": h.phase,
            "event_type": h.event_type,
            "emits": "|".join(h.emits),
            "timing": h.timing,
            "payload": h.payload,
            "overhead": h.overhead,
            "notes": h.notes,
        }
        for h in HOOKS.values()
    ]
    write_csv(OUT / "instrumentation_hooks.csv", hook_rows, list(hook_rows[0].keys()))
    write_ap_yaml(OUT / "atomic_proposition_map.yaml")

    write_csv(OUT / "formula_validation_summary.csv", validation_rows, list(validation_rows[0].keys()))
    write_source_line_verification()
    write_audit()
    write_plan_docs(validation_rows)

    print(f"Generated {len(PROPS)} properties in {OUT}")
    print("Validation status counts:")
    counts: Dict[str, int] = {}
    for r in validation_rows:
        status = (
            "PASS" if r["build_status"] == "PASS"
            and r["positive_symbolic"] == "PASS"
            and r["negative_symbolic"] == "PASS"
            and r["positive_concrete"] == "PASS"
            and r["negative_concrete"] == "PASS"
            and r["symbolic_concrete_consistent"] == "YES"
            else "FAIL"
        )
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
