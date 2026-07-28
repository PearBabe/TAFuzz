#!/usr/bin/env python3
"""Generate and validate the read-only SIP/MITL protocol-fuzzing study.

The script writes only below analysis/protocol_fuzzing_study and invokes the
already-built TAMonitor binary.  It does not build or modify a SUT.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
VALIDATION = OUT / "validation"
TAMONITOR = ROOT / "tool/MightyPPL/build/TAMonitor"
KAM_COMMIT = "2648eb330b133a20f1398d59a28c53532106cad3"
PJSIP_COMMIT = "bba95b8a95c0a9e8c1939166fd20083ae9e3e956"
PROFUZZ_COMMIT = "8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074"
AFLNET_COMMIT = "96032f86d0005dfeeb41ea7b31103f1d1ff8f168"
STATEAFL_COMMIT = "d923e22f7b2688db45b08f3fa3a29a566e7ff3a4"
ACCESS_DATE = "2026-07-13"


def github(owner: str, repo: str, commit: str, path: str, lines: str) -> str:
    return f"https://github.com/{owner}/{repo}/blob/{commit}/{path}#L{lines}"


def exact_schedule(trigger: str, timer: str, stop: str, bound: int) -> str:
    return (
        f"G* ({trigger} -> (G [0,{bound}) (!{timer}) && "
        f"F [0,{bound}] ({timer} || {stop})))"
    )


def exact_wait(trigger: str, bound: int) -> str:
    return (
        f"G* ({trigger} -> (G [0,{bound}) (!transaction_terminated) && "
        f"F [0,{bound}] transaction_terminated))"
    )


def tr(*events: tuple[int, str]) -> list[dict[str, object]]:
    return [{"time": t, "props": p.split() if p else []} for t, p in events]


def prop(
    pid: str,
    title: str,
    category: str,
    requirement: str,
    strength: str,
    section: str,
    excerpt: str,
    time_value: str,
    formula: str,
    aps: list[str],
    positive: list[dict[str, object]],
    negative: list[dict[str, object]],
    source_path: str,
    symbol: str,
    lines: str,
    source_note: str,
    observability: str = "HYBRID",
    confidence: str = "HIGH",
    review_question: str = "请确认该事务投影与 RFC 角色/传输条件一致。",
) -> dict[str, object]:
    return {
        "id": pid,
        "protocol": "SIP",
        "protocol_extension": "RFC 3261 transaction/proxy core",
        "title": title,
        "category": category,
        "natural_language": requirement,
        "normative_strength": strength,
        "standard": "RFC 3261",
        "standard_section": section,
        "standard_url": f"https://www.rfc-editor.org/rfc/rfc3261.html#section-{section}",
        "standard_excerpt": excerpt,
        "time_value_ms": time_value,
        "time_source": "RFC 3261 defaults: T1=500 ms, T2=4000 ms, T4=5000 ms",
        "mathematical_mitl": formula,
        "mightyppl_formula": formula,
        "interval_class": "NON_PUNCTUAL",
        "pointwise_semantics": "strict pointwise; finite word; absolute integer milliseconds",
        "finite_end_semantics": "trace extends through the largest bounded obligation; G* is evaluated on the transaction projection",
        "atomic_propositions": aps,
        "correlation_key": "session_id + Via branch + CSeq number/method; ACK additionally matches RFC 3261 transaction rules",
        "projection_rule": "correlate first, then project one transaction; dynamic identifiers never enter AP names",
        "source_repository": "kamailio/kamailio" if source_path.startswith("src/modules/tm") else "pjsip/pjproject",
        "source_commit": KAM_COMMIT if source_path.startswith("src/modules/tm") else PJSIP_COMMIT,
        "source_path": source_path,
        "source_symbol": symbol,
        "source_lines": lines,
        "source_url": github(
            "kamailio" if source_path.startswith("src/modules/tm") else "pjsip",
            "kamailio" if source_path.startswith("src/modules/tm") else "pjproject",
            KAM_COMMIT if source_path.startswith("src/modules/tm") else PJSIP_COMMIT,
            source_path,
            lines.split("-")[0],
        ),
        "instrumentation_timing": source_note,
        "observability": observability,
        "oracle_value": "HIGH",
        "triggerability": "HIGH" if int(time_value.split("/")[0]) <= 32000 else "MEDIUM",
        "confidence": confidence,
        "positive_trace": positive,
        "negative_trace": negative,
        "human_review_status": "PENDING",
        "review_question": review_question,
    }


PROPERTIES = [
    prop(
        "SIP-TX-01", "Timer A initial schedule", "INVITE UAC retransmission",
        "UDP INVITE 进入 Calling 后，Timer A 在 T1 前不得触发，并应在 T1 时触发或因事务停止而取消。",
        "MUST", "17.1.1.2", "For unreliable transport the client transaction MUST start timer A with T1.",
        "500", exact_schedule("udp_invite_sent", "timer_a_fired", "invite_transaction_stopped", 500),
        ["udp_invite_sent", "timer_a_fired", "invite_transaction_stopped"],
        tr((0, "udp_invite_sent"), (500, "timer_a_fired"), (501, "")),
        tr((0, "udp_invite_sent"), (499, "timer_a_fired"), (501, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_null", "2505-2524",
        "在首次 INVITE 发送和 tsx_schedule_timer(T1) 后原子记录。",
    ),
    prop(
        "SIP-TX-02", "Timer A causes the first INVITE retransmission", "INVITE UAC retransmission",
        "未被响应或停止的 UDP INVITE 必须在首个 T1 周期结束前产生第一次重传。", "MUST", "17.1.1.2",
        "When timer A fires, the client transaction MUST retransmit the request.", "500",
        exact_schedule("udp_invite_sent", "invite_retransmitted", "invite_transaction_stopped", 500),
        ["udp_invite_sent", "invite_retransmitted", "invite_transaction_stopped"],
        tr((0, "udp_invite_sent"), (500, "invite_retransmitted"), (501, "")),
        tr((0, "udp_invite_sent"), (501, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_calling", "2540-2555",
        "在 Timer 回调进入后、tsx_retransmit 返回成功时合并同一 microstep。", "WHITEBOX",
    ),
    prop(
        "SIP-TX-03", "Timer A second interval doubles", "INVITE UAC retransmission",
        "第一次 Timer A 周期完成后，下一次重传间隔必须为 2*T1，除非事务提前停止。", "MUST", "17.1.1.2",
        "The request MUST be retransmitted and the timer reset to 2*T1; intervals continue doubling.", "500",
        exact_schedule("timer_a_first_cycle_completed", "invite_retransmitted", "invite_transaction_stopped", 1000),
        ["timer_a_first_cycle_completed", "invite_retransmitted", "invite_transaction_stopped"],
        tr((0, "timer_a_first_cycle_completed"), (1000, "invite_retransmitted"), (1001, "")),
        tr((0, "timer_a_first_cycle_completed"), (999, "invite_retransmitted"), (1001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_resched_retransmission", "2336-2376",
        "在计算 msec_time 并重新调度之后记录 derived AP；同时保留 old/new interval 字段。", "WHITEBOX",
    ),
    prop(
        "SIP-TX-04", "Timer B transaction deadline", "INVITE UAC timeout",
        "INVITE 客户事务在 64*T1 前不得 Timer B 超时，并应在该时刻前收到最终响应或 Timer B 触发。",
        "MUST/SHOULD", "17.1.1.2", "For any transport the client transaction MUST start timer B with 64*T1.", "32000",
        "G* (invite_client_calling_entered -> (G [0,32000) (!timer_b_fired) && F [0,32000] (timer_b_fired || invite_final_response_received)))",
        ["invite_client_calling_entered", "timer_b_fired", "invite_final_response_received"],
        tr((0, "invite_client_calling_entered"), (32000, "timer_b_fired"), (32001, "")),
        tr((0, "invite_client_calling_entered"), (31999, "timer_b_fired"), (32001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_null/tsx_on_state_calling", "2505-2512;2557-2570",
        "在 timeout_timer 调度与回调处分开记录 start/fire；最终响应为替代终止事件。",
    ),
    prop(
        "SIP-TX-05", "Provisional response stops INVITE retransmission", "INVITE UAC state transition",
        "同一 INVITE 事务收到 1xx 后不应继续重传 INVITE。", "SHOULD NOT", "17.1.1.2",
        "In Proceeding, the client transaction SHOULD NOT retransmit the request any longer.", "32000",
        "G* (invite_provisional_received -> G* (!invite_retransmitted))",
        ["invite_provisional_received", "invite_retransmitted"],
        tr((0, "invite_provisional_received"), (32001, "")),
        tr((0, "invite_provisional_received"), (500, "invite_retransmitted"), (32001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_calling", "2586-2623",
        "收到 1xx、取消 INVITE retransmit timer 后记录；事务投影在结束前封闭。",
        review_question="SHOULD NOT 被用作异常 oracle；请确认是否作为论文主性质或降为软违反。",
    ),
    prop(
        "SIP-TX-06", "Timer D minimum retention", "INVITE UAC completed retention",
        "UDP INVITE 客户事务进入 Completed 后至少 32 秒内不得终止。", "SHOULD", "17.1.1.2",
        "Timer D has a value of at least 32 seconds for unreliable transports.", "32000",
        "G* (udp_invite_client_completed -> G [0,32000) (!transaction_terminated))",
        ["udp_invite_client_completed", "transaction_terminated"],
        tr((0, "udp_invite_client_completed"), (32000, "")),
        tr((0, "udp_invite_client_completed"), (31999, "transaction_terminated"), (32000, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_proceeding_uac", "3131-3196",
        "在 300--699 ACK 发送、Completed 进入和 Timer D 调度处记录。",
    ),
    prop(
        "SIP-TX-07", "Timer E initial schedule", "non-INVITE UAC retransmission",
        "UDP non-INVITE 进入 Trying 后，Timer E 在 T1 前不得触发，并应在 T1 时触发或因最终响应停止。",
        "MUST", "17.1.2.2", "For unreliable transport the client transaction MUST set timer E to fire in T1.", "500",
        exact_schedule("udp_noninvite_sent", "timer_e_fired", "noninvite_final_response_received", 500),
        ["udp_noninvite_sent", "timer_e_fired", "noninvite_final_response_received"],
        tr((0, "udp_noninvite_sent"), (500, "timer_e_fired"), (501, "")),
        tr((0, "udp_noninvite_sent"), (499, "timer_e_fired"), (501, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_null", "2514-2524",
        "按 CSeq method 区分 E 与 A，在 T1 调度后记录。",
    ),
    prop(
        "SIP-TX-08", "Timer E causes the first non-INVITE retransmission", "non-INVITE UAC retransmission",
        "未收到最终响应的 UDP non-INVITE 必须在首个 T1 周期结束前产生第一次重传。", "MUST", "17.1.2.2",
        "If Timer E fires, the request MUST be passed to the transport layer for retransmission.", "500",
        exact_schedule("udp_noninvite_sent", "noninvite_retransmitted", "noninvite_final_response_received", 500),
        ["udp_noninvite_sent", "noninvite_retransmitted", "noninvite_final_response_received"],
        tr((0, "udp_noninvite_sent"), (500, "noninvite_retransmitted"), (501, "")),
        tr((0, "udp_noninvite_sent"), (501, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_calling", "2546-2555",
        "Timer 回调与成功发送在同一 microstep 合并。", "WHITEBOX",
    ),
    prop(
        "SIP-TX-09", "Timer E second interval doubles", "non-INVITE UAC retransmission",
        "第一次 Timer E 周期完成后，下一次重传间隔必须为 MIN(2*T1,T2)。", "MUST", "17.1.2.2",
        "Timer E is reset to MIN(2*T1,T2), then MIN(4*T1,T2), capping at T2.", "500/4000",
        exact_schedule("timer_e_first_cycle_completed", "noninvite_retransmitted", "noninvite_final_response_received", 1000),
        ["timer_e_first_cycle_completed", "noninvite_retransmitted", "noninvite_final_response_received"],
        tr((0, "timer_e_first_cycle_completed"), (1000, "noninvite_retransmitted"), (1001, "")),
        tr((0, "timer_e_first_cycle_completed"), (999, "noninvite_retransmitted"), (1001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_resched_retransmission", "2342-2354",
        "比较 old/new interval，derived AP 仅在 new=min(2*old,T2) 时为真。", "WHITEBOX",
    ),
    prop(
        "SIP-TX-10", "Timer E switches to T2 after provisional", "non-INVITE UAC proceeding",
        "收到 non-INVITE 1xx 后，Timer E 应切换为 T2；在 T2 前不得触发，并在 T2 时触发或被最终响应取消。",
        "MUST", "17.1.2.2", "In Proceeding, Timer E MUST be reset with a value of T2 seconds.", "4000",
        exact_schedule("noninvite_provisional_received", "timer_e_fired", "noninvite_final_response_received", 4000),
        ["noninvite_provisional_received", "timer_e_fired", "noninvite_final_response_received"],
        tr((0, "noninvite_provisional_received"), (4000, "timer_e_fired"), (4001, "")),
        tr((0, "noninvite_provisional_received"), (3999, "timer_e_fired"), (4001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_calling", "2600-2623",
        "1xx 分支取消旧 retransmit timer 并以 t2_timer_val 重排后记录。",
    ),
    prop(
        "SIP-TX-11", "Timer F transaction deadline", "non-INVITE UAC timeout",
        "non-INVITE 客户事务在 64*T1 前不得 Timer F 超时，并应在该时刻前收到最终响应或 Timer F 触发。",
        "SHOULD/MUST", "17.1.2.2", "The client transaction SHOULD set timer F to fire in 64*T1 seconds.", "32000",
        "G* (noninvite_trying_entered -> (G [0,32000) (!timer_f_fired) && F [0,32000] (timer_f_fired || noninvite_final_response_received)))",
        ["noninvite_trying_entered", "timer_f_fired", "noninvite_final_response_received"],
        tr((0, "noninvite_trying_entered"), (32000, "timer_f_fired"), (32001, "")),
        tr((0, "noninvite_trying_entered"), (31999, "timer_f_fired"), (32001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_null/tsx_on_state_calling", "2505-2512;2557-2570",
        "按 method 将 timeout_timer 解释为 F；最终响应是替代完成事件。",
    ),
    prop(
        "SIP-TX-12", "Timer K retention", "non-INVITE UAC completed retention",
        "UDP non-INVITE 客户事务进入 Completed 后保持 T4，然后在 Timer K 触发时终止。", "MUST", "17.1.2.2",
        "Timer K fires in T4 seconds for unreliable transport; then the transaction MUST terminate.", "5000",
        exact_wait("udp_noninvite_client_completed", 5000),
        ["udp_noninvite_client_completed", "transaction_terminated"],
        tr((0, "udp_noninvite_client_completed"), (5000, "transaction_terminated"), (5001, "")),
        tr((0, "udp_noninvite_client_completed"), (4999, "transaction_terminated"), (5001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_proceeding_uac", "3037-3069",
        "在 Completed 状态调度 t4_timer_val 与 timeout 回调终止处记录。",
    ),
    prop(
        "SIP-TX-13", "Timer G initial schedule", "INVITE UAS retransmission",
        "UDP INVITE 服务事务发出 300--699 并进入 Completed 后，Timer G 在 T1 前不得触发。", "MUST", "17.2.1",
        "For unreliable transports, timer G is set to fire in T1 seconds.", "500",
        exact_schedule("udp_invite_server_completed", "timer_g_fired", "ack_received", 500),
        ["udp_invite_server_completed", "timer_g_fired", "ack_received"],
        tr((0, "udp_invite_server_completed"), (500, "timer_g_fired"), (501, "")),
        tr((0, "udp_invite_server_completed"), (499, "timer_g_fired"), (501, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_proceeding_uas", "2865-2915",
        "在 300--699 发送、Completed 进入和 T1 retransmit timer 调度后记录。",
    ),
    prop(
        "SIP-TX-14", "Timer G causes the first final-response retransmission", "INVITE UAS retransmission",
        "未收到 ACK 的 UDP INVITE 服务事务必须在首个 T1 周期结束前重传 300--699 最终响应。", "MUST", "17.2.1",
        "If timer G fires, the response is passed to the transport layer once more.", "500",
        exact_schedule("udp_invite_server_completed", "final_response_retransmitted", "ack_received", 500),
        ["udp_invite_server_completed", "final_response_retransmitted", "ack_received"],
        tr((0, "udp_invite_server_completed"), (500, "final_response_retransmitted"), (501, "")),
        tr((0, "udp_invite_server_completed"), (501, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_proceeding_uas", "2928-2944",
        "Timer G 回调和 tsx_retransmit 成功发送合并为同一 microstep。", "WHITEBOX",
    ),
    prop(
        "SIP-TX-15", "Timer G second interval doubles", "INVITE UAS retransmission",
        "第一次 Timer G 周期完成后，下一次最终响应重传间隔必须为 MIN(2*T1,T2)。", "MUST", "17.2.1",
        "Timer G is reset to MIN(2*T1,T2), then doubles unless exceeding T2.", "500/4000",
        exact_schedule("timer_g_first_cycle_completed", "final_response_retransmitted", "ack_received", 1000),
        ["timer_g_first_cycle_completed", "final_response_retransmitted", "ack_received"],
        tr((0, "timer_g_first_cycle_completed"), (1000, "final_response_retransmitted"), (1001, "")),
        tr((0, "timer_g_first_cycle_completed"), (999, "final_response_retransmitted"), (1001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_resched_retransmission", "2355-2367",
        "记录 UAS old/new interval；只有 new=min(2*old,T2) 时 derived AP 为真。", "WHITEBOX",
    ),
    prop(
        "SIP-TX-16", "Timer H transaction deadline", "INVITE UAS timeout",
        "INVITE 服务事务进入 Completed 后，Timer H 在 64*T1 前不得触发，并应在期限内收到 ACK 或 Timer H 触发。",
        "MUST", "17.2.1", "When Completed is entered, timer H MUST be set to fire in 64*T1 seconds.", "32000",
        "G* (invite_server_completed -> (G [0,32000) (!timer_h_fired) && F [0,32000] (timer_h_fired || ack_received)))",
        ["invite_server_completed", "timer_h_fired", "ack_received"],
        tr((0, "invite_server_completed"), (32000, "timer_h_fired"), (32001, "")),
        tr((0, "invite_server_completed"), (31999, "timer_h_fired"), (32001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_proceeding_uas/tsx_on_state_completed_uas", "2878-2888;3285-3295",
        "在 Completed 状态调度 timeout_timer_val 与回调处区分 H。",
    ),
    prop(
        "SIP-TX-17", "ACK stops Timer G retransmissions", "INVITE UAS confirmed transition",
        "Completed 中收到匹配 ACK 后，最终响应重传必须停止。", "MUST", "17.2.1",
        "On ACK, the transaction MUST enter Confirmed; Timer G is ignored and retransmissions cease.", "5000",
        "G* (ack_received -> G* (!final_response_retransmitted))",
        ["ack_received", "final_response_retransmitted"],
        tr((0, "ack_received"), (5001, "")),
        tr((0, "ack_received"), (500, "final_response_retransmitted"), (5001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_completed_uas", "3232-3271",
        "在 ACK 匹配、取消 retransmit timer、进入 Confirmed 后记录。",
    ),
    prop(
        "SIP-TX-18", "Timer I retention", "INVITE UAS confirmed retention",
        "UDP INVITE 服务事务进入 Confirmed 后保持 T4，并在 Timer I 触发时终止。", "MUST", "17.2.1",
        "Timer I is T4 for unreliable transports; once it fires the server MUST terminate.", "5000",
        exact_wait("udp_invite_server_confirmed", 5000),
        ["udp_invite_server_confirmed", "transaction_terminated"],
        tr((0, "udp_invite_server_confirmed"), (5000, "transaction_terminated"), (5001, "")),
        tr((0, "udp_invite_server_confirmed"), (4999, "transaction_terminated"), (5001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_completed_uas/tsx_on_state_confirmed", "3251-3267;3399-3411",
        "在 Confirmed 进入、T4 调度和 timeout 回调终止处记录。",
    ),
    prop(
        "SIP-TX-19", "Timer J retention", "non-INVITE UAS completed retention",
        "UDP non-INVITE 服务事务进入 Completed 后保持 64*T1，并在 Timer J 触发时终止。", "MUST", "17.2.2",
        "Timer J fires in 64*T1 for unreliable transports; then the transaction MUST terminate.", "32000",
        exact_wait("udp_noninvite_server_completed", 32000),
        ["udp_noninvite_server_completed", "transaction_terminated"],
        tr((0, "udp_noninvite_server_completed"), (32000, "transaction_terminated"), (32001, "")),
        tr((0, "udp_noninvite_server_completed"), (31999, "transaction_terminated"), (32001, "")),
        "pjsip/src/pjsip/sip_transaction.c", "tsx_on_state_proceeding_uas/tsx_on_state_completed_uas", "2889-2897;3299-3303",
        "按 non-INVITE + UDP 区分 J，并在 timeout_timer 回调终止处记录。",
    ),
    prop(
        "SIP-TX-20", "Timer C exceeds three minutes", "stateful proxy INVITE timeout",
        "有状态代理转发每个 INVITE 客户事务时必须设置 Timer C，且 3 分钟内（含边界）不得触发。",
        "MUST", "16.6", "Timer C MUST be set for each proxied INVITE and MUST be larger than 3 minutes.", "180000",
        "G* (proxy_invite_forwarded -> G [0,180000] (!timer_c_fired))",
        ["proxy_invite_forwarded", "timer_c_fired"],
        tr((0, "proxy_invite_forwarded"), (180001, "")),
        tr((0, "proxy_invite_forwarded"), (180000, "timer_c_fired"), (180001, "")),
        "src/modules/tm/timer.h", "_set_fr_retr", "171-200",
        "在建立分支事务并写入 fr_expire/end_of_life 后记录；配置值同时进入事件字段（默认常数见 config.h:61--68）。",
        review_question="RFC 要求严格大于 3 分钟；Kamailio 的 180000 ms 默认值需要人工判断为实现偏差、代理级 lifetime 近似或配置要求。",
    ),
]


PROTOCOL_SCORES = [
    ("SIP", 23, 25, 13, 14, 10, 9, "PASS", "ProFuzzBench Kamailio + 20 RFC 3261 properties"),
    ("DTLS", 19, 24, 13, 13, 9, 9, "FAIL_20", "TinyDTLS benchmark version and modern DTLS timer properties mismatch"),
    ("CoAP", 25, 10, 15, 14, 10, 9, "FAIL_3_BASELINES", "excellent RFC timers, absent from original ProFuzzBench targets"),
    ("MQTT", 14, 14, 15, 13, 8, 9, "FAIL_3_BASELINES", "simple setup but weaker timed transaction corpus"),
    ("TLS", 12, 25, 13, 11, 7, 9, "FAIL_20", "benchmark mature; most core obligations are not bounded timers"),
    ("RTSP", 8, 25, 14, 12, 7, 9, "FAIL_20", "benchmark mature but timed RFC obligations are sparse"),
    ("FTP", 5, 25, 15, 12, 6, 9, "FAIL_20", "strong baselines, weak genuine MITL catalog"),
    ("SMTP", 6, 25, 14, 12, 6, 9, "FAIL_20", "strong baselines, many implementation rather than RFC deadlines"),
    ("DNS", 7, 23, 15, 10, 6, 9, "FAIL_20", "benchmark available, retransmission mostly resolver policy"),
    ("QUIC", 21, 12, 8, 12, 9, 8, "FAIL_SETUP", "rich timers but complex harness and fast-moving implementations"),
    ("DDS/RTPS", 22, 11, 7, 10, 9, 7, "FAIL_SETUP", "rich real-time QoS, heavy ecosystem/adaptation"),
    ("Modbus/TCP", 8, 12, 14, 10, 7, 8, "FAIL_20", "easy SUT, limited normative timed state machine"),
    ("OPC UA", 16, 10, 7, 9, 8, 7, "FAIL_SETUP", "properties exist but stack/conformance setup is heavy"),
    ("CAN/UDS", 15, 9, 6, 8, 8, 6, "FAIL_BASELINE", "good automotive timers, hardware/simulator comparability cost"),
]


BASELINES = [
    ("AFLnwe", "ProFuzzBench", PROFUZZ_COMMIT, "DIRECT", "Kamailio", "Docker/run.sh", "Apache-2.0", "1h tutorial; use 24h x4 full"),
    ("AFLNet", "aflnet/aflnet", AFLNET_COMMIT, "DIRECT", "Kamailio", "ProFuzzBench SIP adapter", "Apache-2.0", "24h x4 in StateAFL/NSFuzz comparisons"),
    ("StateAFL", "stateafl/stateafl", STATEAFL_COMMIT, "DIRECT", "Kamailio", "Dockerfile-stateafl", "GPL-2.0", "13 targets x3 fuzzers x4 repeats x24h"),
    ("NSFuzz", "paper artifact", "DOI:10.1145/3580598", "PAPER_DIRECT", "Kamailio", "all 13 ProFuzzBench targets", "verify artifact", "4 runs x24h; adapter reproduction deferred"),
    ("SGFuzz", "github.com/bajinsheng/SGFuzz", "8f45141", "NOT_DIRECT", "not Kamailio by default", "state-variable annotations", "verify repository", "23h average; secondary only"),
    ("ChatAFL", "Zenodo 10115151", "artifact record", "DEFER_LARGE", "not admitted as primary", "LLM/API + large artifact", "artifact terms", "38.2GB artifact; no download in this phase"),
]


EVIDENCE = [
    {"id": "E01", "type": "standard", "title": "RFC 3261 SIP", "url": "https://www.rfc-editor.org/rfc/rfc3261.html", "version": "RFC 3261", "accessed": ACCESS_DATE},
    {"id": "E02", "type": "standard_update", "title": "RFC 4320 Actions Addressing Issues Identified with SIP Non-INVITE Transaction", "url": "https://www.rfc-editor.org/rfc/rfc4320.html", "version": "RFC 4320", "accessed": ACCESS_DATE},
    {"id": "E03", "type": "standard_update", "title": "RFC 6026 Correct Transaction Handling for 2xx Responses", "url": "https://www.rfc-editor.org/rfc/rfc6026.html", "version": "RFC 6026", "accessed": ACCESS_DATE},
    {"id": "E04", "type": "benchmark", "title": "ProFuzzBench", "url": "https://github.com/profuzzbench/profuzzbench", "version": PROFUZZ_COMMIT, "accessed": ACCESS_DATE},
    {"id": "E05", "type": "source", "title": "Kamailio benchmark SUT", "url": f"https://github.com/kamailio/kamailio/tree/{KAM_COMMIT}", "version": KAM_COMMIT, "accessed": ACCESS_DATE},
    {"id": "E06", "type": "source", "title": "PJSIP benchmark driver/reference endpoint", "url": f"https://github.com/pjsip/pjproject/tree/{PJSIP_COMMIT}", "version": PJSIP_COMMIT, "accessed": ACCESS_DATE},
    {"id": "E07", "type": "paper_artifact", "title": "AFLNet", "url": "https://github.com/aflnet/aflnet", "version": AFLNET_COMMIT, "doi": "10.1109/ICST46399.2020.00062", "accessed": ACCESS_DATE},
    {"id": "E08", "type": "paper_artifact", "title": "StateAFL", "url": "https://github.com/stateafl/stateafl", "version": STATEAFL_COMMIT, "doi": "10.1007/s10664-022-10233-3", "accessed": ACCESS_DATE},
    {"id": "E09", "type": "paper", "title": "NSFuzz", "url": "https://doi.org/10.1145/3580598", "version": "TOSEM 2023", "doi": "10.1145/3580598", "accessed": ACCESS_DATE},
    {"id": "E10", "type": "artifact", "title": "ChatAFL artifact", "url": "https://zenodo.org/records/10115151", "version": "Zenodo 10115151", "accessed": ACCESS_DATE},
]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cooked = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()}
            writer.writerow(cooked)


def trace_text(events: list[dict[str, object]]) -> str:
    lines = ["# absolute integer milliseconds; omitted APs are false", "# time,props"]
    for event in events:
        props = ",".join(event["props"])
        lines.append(f'{event["time"]},{{{props}}}')
    return "\n".join(lines) + "\n"


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode, result.stdout


def validate_property(p: dict[str, object]) -> dict[str, object]:
    d = VALIDATION / str(p["id"])
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "formula.mitl").write_text(str(p["mightyppl_formula"]) + "\n", encoding="utf-8")
    (d / "positive.trace").write_text(trace_text(p["positive_trace"]), encoding="utf-8")
    (d / "negative.trace").write_text(trace_text(p["negative_trace"]), encoding="utf-8")
    command_log = []
    outcomes: dict[str, dict[str, object]] = {}
    cases = [
        ("build_only", None, "symbolic"),
        ("positive_symbolic", "positive.trace", "symbolic"),
        ("negative_symbolic", "negative.trace", "symbolic"),
        ("positive_concrete", "positive.trace", "concrete"),
        ("negative_concrete", "negative.trace", "concrete"),
    ]
    for name, trace, state in cases:
        result_dir = d / name
        cmd = [str(TAMONITOR), "--formula", str(d / "formula.mitl"), "--word", "finite", "--build-mode", "flatten", "--state", state, "--out", str(result_dir)]
        if trace:
            cmd[1:1] = ["--trace", str(d / trace)]
        else:
            cmd.append("--build-only")
        rc, output = run(cmd, ROOT)
        command_log.append("$ " + " ".join(cmd) + "\n" + output.rstrip())
        metadata_path = result_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        outcomes[name] = {"return_code": rc, "stdout": output, "metadata": metadata}
    (d / "commands.log").write_text("\n\n".join(command_log) + "\n", encoding="utf-8")
    ps = outcomes["positive_symbolic"]["metadata"]
    ns = outcomes["negative_symbolic"]["metadata"]
    pc = outcomes["positive_concrete"]["metadata"]
    nc = outcomes["negative_concrete"]["metadata"]
    build_ok = outcomes["build_only"]["return_code"] == 0
    expected_ok = ps.get("final_verdict") == "POSITIVE" and ns.get("final_verdict") == "NEGATIVE"
    consistency = ps.get("final_verdict") == pc.get("final_verdict") and ns.get("final_verdict") == nc.get("final_verdict")
    result = {
        "id": p["id"],
        "build_ok": build_ok,
        "positive_symbolic": ps.get("final_verdict", "NO_OUTPUT"),
        "negative_symbolic": ns.get("final_verdict", "NO_OUTPUT"),
        "positive_concrete": pc.get("final_verdict", "NO_OUTPUT"),
        "negative_concrete": nc.get("final_verdict", "NO_OUTPUT"),
        "expected_oracle_ok": expected_ok,
        "symbolic_concrete_consistent": consistency,
        "ap_order": ps.get("proposition_order", []),
        "positive_locations": ps.get("positive_stats", {}).get("locations"),
        "positive_edges": ps.get("positive_stats", {}).get("edges"),
        "positive_clocks": ps.get("positive_stats", {}).get("clocks"),
        "negative_locations": ps.get("negative_stats", {}).get("locations"),
        "negative_edges": ps.get("negative_stats", {}).get("edges"),
        "negative_clocks": ps.get("negative_stats", {}).get("clocks"),
        "build_ms": ps.get("build_ms"),
        "monitor_ms_positive": ps.get("monitor_ms"),
        "monitor_ms_negative": ns.get("monitor_ms"),
        "status": "PASS" if build_ok and expected_ok and consistency else "FAIL",
    }
    write_json(d / "validation_result.json", result)
    return result


def render_property_catalog_md(results: dict[str, dict[str, object]]) -> str:
    parts = [
        "# SIP MITL 真实性质目录（20 条主目录）",
        "",
        "> 状态：机器构造与手工正反例验证完成；所有人审状态仍为 `PENDING`，不得直接进入论文主张。",
        "",
        "统一语义：按事务关联后投影；绝对整数毫秒；完整 AP valuation；缺失 AP=false；finite + flatten + pointwise；动态事务标识不进入 AP。",
        "",
    ]
    for p in PROPERTIES:
        r = results[p["id"]]
        parts += [
            f'## {p["id"]} — {p["title"]}', "",
            f'- RFC：[{p["standard"]} §{p["standard_section"]}]({p["standard_url"]})；强度 `{p["normative_strength"]}`。',
            f'- 性质：{p["natural_language"]}',
            f'- MightyPPL：`{p["mightyppl_formula"]}`',
            f'- AP：`{", ".join(p["atomic_propositions"])}`',
            f'- 源码：[`{p["source_path"]}:{p["source_lines"]}`]({p["source_url"]})，符号 `{p["source_symbol"]}`。',
            f'- 机器验证：`{r["status"]}`；positive={r["positive_symbolic"]}，negative={r["negative_symbolic"]}，symbolic/concrete={r["symbolic_concrete_consistent"]}。',
            f'- 待审：{p["review_question"]}', "",
        ]
    return "\n".join(parts)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not TAMONITOR.exists():
        raise SystemExit(f"missing TAMonitor: {TAMONITOR}")
    results_list = [validate_property(p) for p in PROPERTIES]
    results = {r["id"]: r for r in results_list}

    # Catalogs and machine-readable interface contracts.
    flat_properties = []
    for p in PROPERTIES:
        row = dict(p)
        row.update({f"validation_{k}": v for k, v in results[p["id"]].items() if k != "id"})
        flat_properties.append(row)
    write_json(OUT / "mitl_property_catalog.json", flat_properties)
    fields = list(flat_properties[0].keys())
    write_csv(OUT / "mitl_property_catalog.csv", flat_properties, fields)
    (OUT / "mitl_property_catalog.md").write_text(render_property_catalog_md(results), encoding="utf-8")
    write_csv(OUT / "formula_validation_summary.csv", results_list, list(results_list[0].keys()))

    ap_entries: dict[str, dict[str, object]] = {}
    for p in PROPERTIES:
        for ap in p["atomic_propositions"]:
            ap_entries.setdefault(ap, {
                "type": "boolean",
                "definition": ap.replace("_", " "),
                "complete_valuation": "false when absent at a timed-word position",
                "source_properties": [],
            })["source_properties"].append(p["id"])
    write_json(OUT / "atomic_proposition_map.yaml", {
        "schema_version": 1,
        "time_unit": "integer_millisecond",
        "correlation_before_projection": True,
        "missing_ap_value": False,
        "atomic_propositions": ap_entries,
    })
    hooks = [{
        "property_id": p["id"], "repository": p["source_repository"], "commit": p["source_commit"],
        "file": p["source_path"], "symbol": p["source_symbol"], "lines": p["source_lines"],
        "hook_timing": p["instrumentation_timing"], "observability": p["observability"], "source_url": p["source_url"],
    } for p in PROPERTIES]
    write_csv(OUT / "instrumentation_hooks.csv", hooks, list(hooks[0].keys()))
    write_json(OUT / "property_spec.json", {"schema_version": 1, "properties": flat_properties})
    write_json(OUT / "protocol_event.schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "ProtocolEvent", "type": "object",
        "required": ["time_tick", "session_id", "transaction_id", "direction", "event_type"],
        "properties": {
            "time_tick": {"type": "integer", "minimum": 0}, "session_id": {"type": "string"},
            "transaction_id": {"type": "string"}, "direction": {"enum": ["in", "out", "internal"]},
            "event_type": {"type": "string"}, "fields": {"type": "object"}, "source_hook": {"type": "string"},
            "microstep": {"type": "integer", "minimum": 0},
        }, "additionalProperties": False,
    })
    (OUT / "protocol_event.example.jsonl").write_text(
        '{"time_tick":0,"session_id":"s1","transaction_id":"branch+cseq","direction":"out","event_type":"udp_invite_sent","fields":{"method":"INVITE"},"source_hook":"tsx_on_state_null","microstep":0}\n', encoding="utf-8")

    # Scoring, sources, and implementation mapping.
    score_rows = []
    for name, a, b, c, d, e, f, gate, note in PROTOCOL_SCORES:
        score_rows.append({"protocol": name, "authentic_properties_25": a, "benchmark_comparability_25": b,
                           "setup_ease_15": c, "observability_15": d, "tafuzz_fit_10": e,
                           "reproducibility_10": f, "total_100": a+b+c+d+e+f, "hard_gate": gate, "evidence_note": note})
    write_csv(OUT / "protocol_scorecard.csv", score_rows, list(score_rows[0].keys()))
    baseline_rows = [{"baseline": x[0], "source": x[1], "version": x[2], "kamailio_compatibility": x[3],
                      "sut": x[4], "adapter": x[5], "license": x[6], "budget_evidence": x[7]} for x in BASELINES]
    write_csv(OUT / "baseline_artifact_matrix.csv", baseline_rows, list(baseline_rows[0].keys()))
    write_json(OUT / "evidence_manifest.yaml", {"schema_version": 1, "access_date": ACCESS_DATE, "sources": EVIDENCE,
                                                  "ccfa_search_result": "NO_UNIQUE_PROTOCOL_FUZZING_PAPER_RESOLVED"})
    map_rows = [{
        "property_id": p["id"], "standard": p["standard"], "section": p["standard_section"],
        "timer_or_transition": p["title"], "default_ms": p["time_value_ms"], "sut": "Kamailio/PJSIP hook map",
        "commit": p["source_commit"], "file": p["source_path"], "symbol": p["source_symbol"],
        "lines": p["source_lines"], "source_url": p["source_url"], "mapping_status": "FIXED_COMMIT_HOOK",
    } for p in PROPERTIES]
    write_csv(OUT / "standard_implementation_map.csv", map_rows, list(map_rows[0].keys()))
    write_json(OUT / "sut_reproducibility_manifest.yaml", {
        "schema_version": 1, "main_sut": {"name": "Kamailio", "commit": KAM_COMMIT, "role": "stateful SIP proxy/server",
        "benchmark": "ProFuzzBench SIP/Kamailio", "build_status": "NOT_BUILT_BY_DESIGN"},
        "driver": {"name": "PJSIP/pjproject", "commit": PJSIP_COMMIT, "role": "benchmark endpoint/traffic driver"},
        "benchmark": {"name": "ProFuzzBench", "commit": PROFUZZ_COMMIT},
        "source_checkout": "/tmp/tafuzz_protocol_sources (ephemeral shallow read-only inspection)",
    })

    # Study reports.
    (OUT / "ccfa_identity_audit.md").write_text(f"""# CCFA 身份核验

结论：截至 {ACCESS_DATE}，以 CCFA、协议模糊测试、coverage-guided/stateful protocol fuzzing 等组合检索，未能唯一解析出一篇题名或工具名为 **CCFA** 且满足用户描述的公开论文。现有 TAFuzz 调研中的“CCF-A-facing”是实验标准定位，不是论文缩写。

因此本研究采用可审计的操作性定义：**CCFA 类 = 面向有状态网络协议、使用代码或协议状态反馈进行种子/状态调度，并按高水平安全/软件工程论文 artifact 标准比较的 coverage-guided fuzzing**。主比较锚点为 AFLNet、StateAFL、NSFuzz 与 ProFuzzBench；SGFuzz、ChatAFL 只作次级方法，因为并非都能直接复用同一 Kamailio SUT。

该定义不是声称存在“CCFA 方法”，而是消除缩写歧义。若用户能提供原论文题名/截图，应重新打开此门并更新矩阵。
""", encoding="utf-8")
    (OUT / "protocol_selection_report.md").write_text("""# 协议筛选结论

首选是 **SIP 事务层/有状态代理生态**，主 SUT 为 ProFuzzBench 固定的 Kamailio，PJSIP 为同 benchmark 的端点/参考实现。它是候选中唯一同时通过四个关键门的协议：20 条 RFC 级性质、固定可插桩源码、单机容器 benchmark、至少 AFLnwe/AFLNet/StateAFL 三条同 SUT 路径。

CoAP 的 MITL 性质质量最高，但不在原始 ProFuzzBench 目标集中，首轮无法低成本获得三个公平 baseline；因此列为备用协议。DTLS/TinyDTLS 的 benchmark 成熟，但 ProFuzzBench 固定实现与较新的 DTLS 定时规范版本不齐，列为第二备用。

评分是研究决策量表，不是统计测量。硬门优先于总分；完整分项见 `protocol_scorecard.csv`。
""", encoding="utf-8")
    (OUT / "semantic_exclusions.md").write_text("""# 语义与版本排除

- 不使用 `[a,a]` singleton。当前 MightyPPL 对试探公式 `G* (x -> F [500,500] y)` 返回 `map::at`；20 条主性质全部使用宽度大于零的区间或非定界全局投影，未擅自加入 epsilon。
- 不引入 STL/ZOH/连续信号语义。输入仍是 pointwise timed word；同一协议回调内的事件先原子合并，确有顺序差异时用确定 microstep。
- RFC 4320 的“Timer E reaches T2”候选和 RFC 6026 Timer L/M 暂列 V2：它们是真实标准义务，但与 ProFuzzBench 固定 Kamailio/PJSIP 版本的直接源码映射需要额外 conformance/版本审计，不能为凑 20 条而冒充已验证主性质。
- Timer C 的 RFC 条件是严格大于 180000 ms，而 Kamailio 固定提交的 `MAX_INV_LIFETIME` 默认是 180000 ms。SIP-TX-20 机器验证的是 RFC 投影；实现是否偏差必须人工签字。
- `SHOULD/SHOULD NOT` 条目是软规范违反，不等同于安全漏洞或 crash oracle。
- 未运行 PTA prefix cost：当前阶段没有经人工审核的 property-specific cost model。正式 verdict 已由正/负 MITL monitor 验证；伪造统一权重会违反“启发式不得冒充形式结论”。
""", encoding="utf-8")
    (OUT / "adapter_design.md").write_text("""# 协议适配与数据流设计

固定通路：报文/定时器 → SIP 解析与事务关联 → `ProtocolEvent` → 按性质投影 → 完整 valuation timed word → 正/负自动机 → MoniTAal → PTA prefix cost-to-go → 变异/种子调度。

事务键采用 `session_id + top Via branch + CSeq number/method`，必要时加入 sent-by；先关联再投影。事件 JSONL 只携带动态 ID 字段，AP 仍是固定布尔字母表。相同回调内的 timer-fire、send 和 interval-update 合并为一个位置；跨回调竞争按 `(time_tick, microstep, capture_sequence)` 稳定排序。

建议分数：`w_code*C_code + w_proto*C_state + w_aut*C_automaton + w_cost*(1-normalized_cost)`。各项先在当前 campaign 内归一化；MITL verdict 单独记录，不能由该分数替代。
""", encoding="utf-8")
    (OUT / "baseline_adapter_plan.md").write_text("""# Baseline 适配计划

主对比只采用能复用相同 Kamailio 容器与 seed/reset/cov 脚本的 AFLnwe、AFLNet、StateAFL。TAFuzz 只新增旁路 trace adapter 与 monitor，不改变 SUT 协议行为。NSFuzz 作为第四候选，待其 artifact 在不更换 SUT 的前提下复现后再加入；SGFuzz/ChatAFL 不进入首轮主表。

公平性记录项：baseline commit、SUT commit、编译器/flags、seed hash、CPU pinning、reset 成功率、端口、超时、coverage 采样周期、所有 patch。任何 baseline 特有修改单列，不把适配工作算作方法优势。
""", encoding="utf-8")
    (OUT / "experiment_design.md").write_text("""# CCFA 类对比实验设计

研究问题：在相同 Kamailio SUT、seed、reset、硬件和预算下，MITL 自动机覆盖与 PTA cost-to-go 是否改善协议状态/代码覆盖、真实性质违反发现速度和独特性？

主 baseline：AFLnwe、AFLNet、StateAFL。消融：无 MITL、Boolean verdict、自动机覆盖、PTA cost-to-go、完整 TAFuzz。指标：edge/branch、协议状态/转移、自动机状态/边/region、unique violation、unique crash、time-to-first、exec/s、monitor overhead。

工程 smoke 为 1h×1，仅排错；pilot 为 2h24m×3（24h 的 10%）；full 为 24h×4，复用 StateAFL/NSFuzz 对 ProFuzzBench 的公开规模。进入 full 前必须完成 20 条人工签字和 baseline adapter smoke。
""", encoding="utf-8")
    ablations = [
        {"variant": "NO_MITL", "verdict": 0, "automaton_coverage": 0, "pta_cost": 0, "code_coverage": 1, "protocol_state": 1},
        {"variant": "BOOLEAN_VERDICT", "verdict": 1, "automaton_coverage": 0, "pta_cost": 0, "code_coverage": 1, "protocol_state": 1},
        {"variant": "AUTOMATON_COVERAGE", "verdict": 1, "automaton_coverage": 1, "pta_cost": 0, "code_coverage": 1, "protocol_state": 1},
        {"variant": "PTA_COST_TO_GO", "verdict": 1, "automaton_coverage": 0, "pta_cost": 1, "code_coverage": 1, "protocol_state": 1},
        {"variant": "FULL_TAFUZZ", "verdict": 1, "automaton_coverage": 1, "pta_cost": 1, "code_coverage": 1, "protocol_state": 1},
    ]
    write_csv(OUT / "ablation_matrix.csv", ablations, list(ablations[0].keys()))
    (OUT / "statistics_protocol.md").write_text("""# 统计协议

每个 target×fuzzer×variant 报告中位数、IQR 和按 run 重采样的 bootstrap 95% CI。成对方法比较使用双侧 Mann–Whitney U；同一指标族用 Holm 校正；效应量报告 Vargha–Delaney A12 及方向。覆盖时间序列同时报告终点和 AUC，不能把每分钟采样点当作独立重复。

crash 先按栈签名/根因去重，MITL violation 按 `(property_id, normalized transaction prefix, terminal transition)` 去重。超时/启动失败保留为失败 run，不静默重跑。所有分析脚本在看到 full 数据前冻结。
""", encoding="utf-8")
    write_json(OUT / "experiment_manifest.yaml", {
        "schema_version": 1, "status": "DESIGN_ONLY", "sut_commit": KAM_COMMIT,
        "baseline_commits": {"AFLNet": AFLNET_COMMIT, "StateAFL": STATEAFL_COMMIT, "ProFuzzBench": PROFUZZ_COMMIT},
        "budgets": {"smoke": "1h x1", "pilot": "2h24m x3", "full": "24h x4"},
        "controls": ["same SUT", "same seeds", "same reset", "same hardware", "same wall-clock", "same coverage collector"],
        "not_executed": True,
    })

    # Reproducibility ledger hashes every generated non-validation artifact.
    artifacts = []
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name not in {"reproducibility_manifest.json", "human_review_packet.xlsx"}:
            artifacts.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    write_json(OUT / "reproducibility_manifest.json", {
        "generated_on": str(date.today()), "generator": "generate_study.py", "tamonitor": str(TAMONITOR),
        "command": "python3 analysis/protocol_fuzzing_study/generate_study.py", "artifacts": artifacts,
        "validation_count": len(results_list), "validation_pass": sum(r["status"] == "PASS" for r in results_list),
    })
    all_pass = all(r["status"] == "PASS" for r in results_list)
    print(f"generated {len(PROPERTIES)} properties; validation pass={sum(r['status']=='PASS' for r in results_list)}/{len(results_list)}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
