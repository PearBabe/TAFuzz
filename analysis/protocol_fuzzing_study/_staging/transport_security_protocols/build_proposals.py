#!/usr/bin/env python3
"""Build the transport/security protocol proposal staging files.

This script is intentionally confined to this staging directory.  It does not
build or modify any SUT.  Source and standard evidence was inspected at the
fixed revisions recorded below on 2026-07-13.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ACCESS_DATE = "2026-07-13"

LINUX_COMMIT = "f4fb100039e96211609dfc44fb24b9e4a8a0f2f9"
NGTCP2_COMMIT = "fcb5cdaba44a8fb1c821319af306e3f38f18e738"
OPENSSL_COMMIT = "0437435a960123be1ced766d18d715f939698345"
OPENSSH_COMMIT = "7cfea58cb313a27b90aa4563cf65904bdf2fc5f3"
DCMTK_COMMIT = "7f8564cf11e5531689dd329523fb16023aeda3ed"
TINYDTLS_COMMIT = "06995d43e9eba892aa7db604b3879b5f91872328"
PROFUZZ_COMMIT = "8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074"


def gh(repo: str, commit: str, path: str, lines: str) -> str:
    start, _, end = lines.partition("-")
    suffix = f"#L{start}" + (f"-L{end}" if end else "")
    return f"https://github.com/{repo}/blob/{commit}/{path}{suffix}"


def source_mapping(
    *,
    role: str,
    repository: str,
    commit: str,
    path: str,
    symbol: str,
    lines: str,
    atomic_propositions: list[str],
    url: str | None = None,
    legacy_exact_url: str | None = None,
) -> dict[str, object]:
    """Build one source-verified AP mapping.

    ``legacy_exact_url`` is used only when an older broad reference points at
    a C++ data-member declaration that the root executable-symbol checker
    cannot validate.  The executable ``url`` still points at a fixed function
    use site, while the exact historical reference remains nested beside it
    instead of surviving as an unstructured top-level ``*_source_url`` field.
    """
    result: dict[str, object] = {
        "role": role,
        "repository": repository,
        "commit": commit,
        "path": path,
        "symbol": symbol,
        "lines": lines,
        "url": url or gh(repository, commit, path, lines),
        "atomic_propositions": atomic_propositions,
    }
    if legacy_exact_url:
        result["legacy_exact_url"] = legacy_exact_url
    return result


def tr(*events: tuple[int, str]) -> list[dict[str, object]]:
    return [{"time": t, "props": p.split() if p else []} for t, p in events]


def property_card(
    *,
    pid: str,
    protocol: str,
    extension: str,
    title: str,
    category: str,
    natural: str,
    strength: str,
    standard: str,
    version: str,
    section: str,
    standard_url: str,
    excerpt: str,
    time_value_ms: str,
    time_parameter: str,
    time_source: str,
    basis: str,
    formula: str,
    aps: dict[str, str],
    correlation: str,
    source_repo: str,
    source_commit: str,
    source_path: str,
    source_symbol: str,
    source_lines: str,
    hook: str,
    positive: list[dict[str, object]],
    negative: list[dict[str, object]],
    observability: str = "HYBRID",
    oracle: str = "HIGH",
    triggerability: str = "HIGH",
    confidence: str = "HIGH",
    review: str = "请确认事务投影、角色条件和固定时间 profile 与实验配置一致。",
    limitations: str = "仅适用于卡片声明的角色、状态与时间 profile。",
    extras: dict[str, object] | None = None,
) -> dict[str, object]:
    p = {
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
        "time_value_ms": time_value_ms,
        "time_parameter": time_parameter,
        "time_source": time_source,
        "instantiation_basis": basis,
        "mathematical_mitl": formula,
        "mightyppl_formula": formula,
        "interval_class": "NON_PUNCTUAL",
        "pointwise_semantics": "strict pointwise; finite word; absolute integer milliseconds",
        "finite_end_semantics": "trace extends beyond the largest bounded obligation; missing AP=false",
        "atomic_propositions": list(aps),
        "ap_definitions": aps,
        "correlation_key": correlation,
        "projection_rule": "correlate first, then project one connection/transaction/flight; dynamic identifiers never enter AP names",
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
        "review_question": review,
        "limitations": limitations,
        "human_review_status": "PENDING",
    }
    if extras:
        p.update(extras)
    return p


TCP = [
    property_card(
        pid="TCP-RTO-01", protocol="TCP", extension="RFC 6298 retransmission timeout",
        title="Initial RTO is one second", category="retransmission timeout",
        natural="尚无 RTT 样本时，首次发送后不得在 1 秒前触发 RTO；未获 ACK 时应在 1 秒触发。",
        strength="SHOULD", standard="RFC 6298", version="RFC 6298",
        section="2.1", standard_url="https://www.rfc-editor.org/rfc/rfc6298.html#section-2.1",
        excerpt="the sender SHOULD set RTO <- 1 second",
        time_value_ms="1000", time_parameter="initial RTO",
        time_source="RFC 6298 Section 2.1 recommended initial value",
        basis="NORMATIVE_RECOMMENDED_DEFAULT",
        formula="G* (tcp_first_segment_sent_without_rtt -> (G [0,1000) (!tcp_rto_fired) && F [0,1000] (tcp_rto_fired || tcp_ack_advanced_snd_una)))",
        aps={
            "tcp_first_segment_sent_without_rtt":"First sequence-carrying segment is transmitted before any valid RTT sample.",
            "tcp_rto_fired":"ICSK_TIME_RETRANS timer dispatches for the correlated socket.",
            "tcp_ack_advanced_snd_una":"An acceptable ACK advances SND.UNA and discharges the initial retransmission obligation.",
        },
        correlation="network namespace + socket cookie + 4-tuple; sequence numbers correlate ACKs but are fields, not AP names",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="include/net/tcp.h", source_symbol="TCP_TIMEOUT_INIT", source_lines="160-173",
        hook="Record the initial RTO after tcp_timeout_init/TCP_TIMEOUT_INIT is assigned; record fire in tcp_write_timer_handler.",
        positive=tr((0,"tcp_first_segment_sent_without_rtt"),(1000,"tcp_rto_fired"),(1001,"")),
        negative=tr((0,"tcp_first_segment_sent_without_rtt"),(999,"tcp_rto_fired"),(1001,"")),
        limitations="Linux can switch to the RFC 6298 3-second fallback after SYN/SYN-ACK loss; that branch needs a separate profile and is excluded here.",
    ),
    property_card(
        pid="TCP-RTO-02", protocol="TCP", extension="RFC 6298 retransmission timeout",
        title="RTO expiry retransmits the earliest unacknowledged segment", category="retransmission action",
        natural="重传计时器到期时，发送方必须重传最早尚未确认的报文段。",
        strength="MUST", standard="RFC 6298", version="RFC 6298",
        section="5.4", standard_url="https://www.rfc-editor.org/rfc/rfc6298.html#section-5",
        excerpt="Retransmit the earliest segment that has not been acknowledged",
        time_value_ms="1000", time_parameter="current RTO (initial profile)",
        time_source="RFC 6298 Sections 2.1 and 5.4",
        basis="NORMATIVE_DEFAULT_PROFILE",
        formula="G* (tcp_rto_fired -> tcp_earliest_unacked_retransmitted)",
        aps={
            "tcp_rto_fired":"Retransmission timer expiry callback begins for a socket with packets_out>0.",
            "tcp_earliest_unacked_retransmitted":"tcp_rtx_queue_head is passed successfully to tcp_retransmit_skb in the same callback microstep.",
        },
        correlation="socket cookie + current SND.UNA; skb sequence is a correlation field",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="net/ipv4/tcp_timer.c", source_symbol="tcp_retransmit_timer", source_lines="603-639",
        hook="Emit both APs after tcp_retransmit_skb returns success; use a pre-call fire marker only for diagnostic fields.",
        positive=tr((0,"tcp_rto_fired tcp_earliest_unacked_retransmitted"),(1,"")),
        negative=tr((0,"tcp_rto_fired"),(1,"")), observability="WHITEBOX",
        limitations="A local-congestion failure takes the resource-probe branch and must be tagged as an excluded environment outcome, not a protocol violation.",
    ),
    property_card(
        pid="TCP-RTO-03", protocol="TCP", extension="RFC 6298 retransmission timeout",
        title="RTO backs off by two after expiry", category="retransmission backoff",
        natural="首次 1 秒 RTO 到期并重传后，下一次无 ACK 超时不得早于 2 秒，并应在 2 秒触发。",
        strength="MUST", standard="RFC 6298", version="RFC 6298",
        section="5.5-5.6", standard_url="https://www.rfc-editor.org/rfc/rfc6298.html#section-5",
        excerpt="The host MUST set RTO <- RTO * 2",
        time_value_ms="2000", time_parameter="second RTO after one backoff",
        time_source="RFC 6298 Section 5.5 applied to initial RTO=1000 ms",
        basis="NORMATIVE_DERIVED",
        formula="G* (tcp_first_rto_retransmission_completed -> (G [0,2000) (!tcp_second_rto_fired) && F [0,2000] (tcp_second_rto_fired || tcp_ack_advanced_snd_una)))",
        aps={
            "tcp_first_rto_retransmission_completed":"First RTO retransmission succeeds and the timer is rearmed.",
            "tcp_second_rto_fired":"The rearmed ICSK_TIME_RETRANS callback fires.",
            "tcp_ack_advanced_snd_una":"An ACK advances SND.UNA before the second expiry.",
        },
        correlation="socket cookie + retransmission generation counter",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="net/ipv4/tcp_timer.c", source_symbol="tcp_retransmit_timer", source_lines="657-685",
        hook="After icsk_rto is doubled and tcp_reset_xmit_timer succeeds, emit the trigger with old/new RTO fields.",
        positive=tr((0,"tcp_first_rto_retransmission_completed"),(2000,"tcp_second_rto_fired"),(2001,"")),
        negative=tr((0,"tcp_first_rto_retransmission_completed"),(1999,"tcp_second_rto_fired"),(2001,"")),
        observability="WHITEBOX",
        limitations="Linux thin-stream linear timeout mode is excluded; the adapter must require the normal exponential-backoff branch.",
    ),
    property_card(
        pid="TCP-ACK-01", protocol="TCP", extension="RFC 9293 delayed acknowledgments",
        title="Delayed ACK remains below 500 ms", category="acknowledgment delay",
        natural="对需要确认且采用 delayed ACK 的报文段，ACK 延迟必须严格小于 500 ms。",
        strength="MUST", standard="RFC 9293", version="RFC 9293",
        section="3.8.6.3", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.3",
        excerpt="the delay MUST be less than 0.5 seconds",
        time_value_ms="500 (strict upper bound)", time_parameter="maximum delayed ACK",
        time_source="RFC 9293 Section 3.8.6.3",
        basis="NORMATIVE_BOUND",
        formula="G* (tcp_delayed_ack_obligation_started -> F [0,500) (tcp_ack_sent))",
        aps={
            "tcp_delayed_ack_obligation_started":"A processed segment requires ACK and enters the delayed-ACK rather than immediate-ACK branch.",
            "tcp_ack_sent":"An ACK covering the correlated receive sequence is handed to IP output.",
        },
        correlation="socket cookie + receive-direction sequence interval",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="net/ipv4/tcp_output.c", source_symbol="tcp_send_delayed_ack", source_lines="4409-4463",
        hook="Emit the trigger immediately before sk_reset_timer; emit ACK after tcp_send_ack/output using the same socket cookie.",
        positive=tr((0,"tcp_delayed_ack_obligation_started"),(499,"tcp_ack_sent"),(501,"")),
        negative=tr((0,"tcp_delayed_ack_obligation_started"),(500,"tcp_ack_sent"),(501,"")),
        observability="HYBRID",
        limitations="The Linux default cap is normally 200 ms, which is stricter; 500 ms remains the protocol oracle.",
    ),
    property_card(
        pid="TCP-ZWP-01", protocol="TCP", extension="RFC 9293 zero-window probing",
        title="First zero-window probe follows one RTO", category="zero-window probe",
        natural="在无 RTT 样本的 1 秒 RTO profile 下，发送窗口持续为零时首个 probe 应在一个 RTO 后发送。",
        strength="SHOULD", standard="RFC 9293", version="RFC 9293",
        section="3.8.6.1", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.1",
        excerpt="SHOULD send the first zero-window probe when a zero window has existed",
        time_value_ms="1000", time_parameter="first zero-window probe interval",
        time_source="RFC 9293 Section 3.8.6.1 + RFC 6298 initial RTO",
        basis="NORMATIVE_DERIVED_PROFILE",
        formula="G* (tcp_zero_window_started_initial_rto -> (G [0,1000) (!tcp_zero_window_probe_sent) && F [0,1000] (tcp_zero_window_probe_sent || tcp_send_window_opened)))",
        aps={
            "tcp_zero_window_started_initial_rto":"Peer-advertised send window becomes zero while unsent data exists and current RTO is 1000 ms.",
            "tcp_zero_window_probe_sent":"A zero-window probe is successfully emitted.",
            "tcp_send_window_opened":"A correlated ACK advertises a nonzero send window.",
        },
        correlation="socket cookie + advertised-window update generation",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="include/net/tcp.h", source_symbol="tcp_check_probe_timer", source_lines="1640-1667",
        hook="Record the zero-window trigger when ICSK_TIME_PROBE0 is armed; record the probe at tcp_send_probe0/tcp_write_wakeup success.",
        positive=tr((0,"tcp_zero_window_started_initial_rto"),(1000,"tcp_zero_window_probe_sent"),(1001,"")),
        negative=tr((0,"tcp_zero_window_started_initial_rto"),(999,"tcp_zero_window_probe_sent"),(1001,"")),
        limitations="Requires current icsk_rto=1000 ms and excludes an earlier RTT-derived RTO or local-resource failure.",
    ),
    property_card(
        pid="TCP-ZWP-02", protocol="TCP", extension="RFC 9293 zero-window probing",
        title="Zero-window probes back off exponentially", category="zero-window probe backoff",
        natural="首个 1 秒 zero-window probe 后，窗口仍为零时下一 probe 应按指数退避至 2 秒。",
        strength="SHOULD", standard="RFC 9293", version="RFC 9293",
        section="3.8.6.1", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.6.1",
        excerpt="increase exponentially the interval between successive probes",
        time_value_ms="2000", time_parameter="second zero-window probe interval",
        time_source="RFC 9293 exponential-backoff requirement instantiated from initial RTO=1000 ms",
        basis="NORMATIVE_DERIVED_PROFILE",
        formula="G* (tcp_first_zero_window_probe_completed -> (G [0,2000) (!tcp_second_zero_window_probe_sent) && F [0,2000] (tcp_second_zero_window_probe_sent || tcp_send_window_opened)))",
        aps={
            "tcp_first_zero_window_probe_completed":"First probe is emitted and probe backoff counter increments from zero to one.",
            "tcp_second_zero_window_probe_sent":"Next zero-window probe is emitted.",
            "tcp_send_window_opened":"Peer advertises a nonzero send window.",
        },
        correlation="socket cookie + zero-window probe generation",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="net/ipv4/tcp_output.c", source_symbol="tcp_send_probe0", source_lines="4601-4635",
        hook="After icsk_backoff increments and tcp_probe0_when computes the next timer, record old/new interval and probe generation.",
        positive=tr((0,"tcp_first_zero_window_probe_completed"),(2000,"tcp_second_zero_window_probe_sent"),(2001,"")),
        negative=tr((0,"tcp_first_zero_window_probe_completed"),(1999,"tcp_second_zero_window_probe_sent"),(2001,"")),
        observability="WHITEBOX",
        limitations="Only the first backoff step is instantiated; later steps are the same obligation and are not duplicated as properties.",
    ),
    property_card(
        pid="TCP-KA-01", protocol="TCP", extension="RFC 9293 keep-alive",
        title="Default keep-alive idle period is at least two hours", category="keep-alive",
        natural="应用显式启用 keep-alive 且使用默认参数时，空闲连接在两小时内不得发送 keep-alive probe。",
        strength="MUST", standard="RFC 9293", version="RFC 9293",
        section="3.8.4", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.4",
        excerpt="MUST default to no less than two hours",
        time_value_ms="7200000", time_parameter="default keep-alive interval",
        time_source="RFC 9293 Section 3.8.4 and Linux TCP_KEEPALIVE_TIME",
        basis="NORMATIVE_DEFAULT_AND_IMPLEMENTATION_DEFAULT",
        formula="G* (tcp_default_keepalive_enabled_on_idle_connection -> G [0,7200000) (!tcp_keepalive_probe_sent))",
        aps={
            "tcp_default_keepalive_enabled_on_idle_connection":"SO_KEEPALIVE becomes active with no per-socket keepidle override and no outstanding data.",
            "tcp_keepalive_probe_sent":"tcp_write_wakeup emits a keep-alive probe for the correlated socket.",
        },
        correlation="network namespace + socket cookie",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="include/net/tcp.h", source_symbol="TCP_KEEPALIVE_TIME", source_lines="175-180",
        hook="Record enablement after tcp_set_keepalive arms the timer; emit probe only after tcp_write_wakeup succeeds.",
        positive=tr((0,"tcp_default_keepalive_enabled_on_idle_connection"),(7200000,"tcp_keepalive_probe_sent"),(7200001,"")),
        negative=tr((0,"tcp_default_keepalive_enabled_on_idle_connection"),(7199999,"tcp_keepalive_probe_sent"),(7200001,"")),
        triggerability="LOW",
        limitations="Keep-alive is optional and disabled unless the application requests it; virtual time is needed for practical fuzzing.",
    ),
    property_card(
        pid="TCP-TW-01", protocol="TCP", extension="RFC 9293 TIME-WAIT",
        title="TIME-WAIT retains state for four minutes", category="connection close retention",
        natural="主动关闭进入 TIME-WAIT 后，按 RFC 9293 的 MSL=2 分钟，至少 2*MSL（4 分钟）内不得销毁状态。",
        strength="MUST", standard="RFC 9293", version="RFC 9293",
        section="3.6.1", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.6.1",
        excerpt="it MUST linger in the TIME-WAIT state for a time 2xMSL",
        time_value_ms="240000", time_parameter="2*MSL",
        time_source="RFC 9293 Sections 3.4.2 and 3.6.1: MSL=2 minutes, TIME-WAIT=2*MSL",
        basis="NORMATIVE_DERIVED",
        formula="G* (tcp_time_wait_entered -> G [0,240000) (!tcp_time_wait_state_destroyed))",
        aps={
            "tcp_time_wait_entered":"The correlated socket/inet_timewait_sock enters TCP_TIME_WAIT after active close.",
            "tcp_time_wait_state_destroyed":"The TIME-WAIT bucket is removed and its tuple is no longer retained.",
        },
        correlation="network namespace + 4-tuple + TIME-WAIT bucket cookie",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="include/net/tcp.h", source_symbol="TCP_TIMEWAIT_LEN", source_lines="140-148",
        hook="Emit entry at tcp_time_wait creation and destruction immediately before inet_twsk_kill/deschedule.",
        positive=tr((0,"tcp_time_wait_entered"),(240000,"tcp_time_wait_state_destroyed"),(240001,"")),
        negative=tr((0,"tcp_time_wait_entered"),(60000,"tcp_time_wait_state_destroyed"),(240001,"")),
        confidence="MEDIUM",
        review="Linux 固定源码使用 TCP_TIMEWAIT_LEN=60 秒；请把该标准—实现差异作为待实测候选，并单独处理 RFC 9293 允许的 guarded TIME-WAIT reuse 例外。",
        limitations="Linux's 60-second constant is shorter than the RFC-derived 240 seconds. RFC 9293 also permits guarded direct reopen from TIME-WAIT under explicit sequence-number safeguards.",
        extras={"msl_source_url":"https://www.rfc-editor.org/rfc/rfc9293.html#section-3.4.2","implementation_deviation":"Linux TCP_TIMEWAIT_LEN=60 seconds"},
    ),
]


QUIC = [
    property_card(
        pid="QUIC-ACK-01", protocol="QUIC", extension="RFC 9000 v1 transport",
        title="1-RTT ACK respects the default 25 ms max_ack_delay", category="acknowledgment delay",
        natural="未显式发送 max_ack_delay 参数时，已解密处理的 ack-eliciting 1-RTT 包必须在 25 ms 内至少确认一次。",
        strength="MUST", standard="RFC 9000", version="RFC 9000 (QUIC v1)",
        section="13.2.1, 18.2", standard_url="https://www.rfc-editor.org/rfc/rfc9000.html#section-13.2.1",
        excerpt="MUST be acknowledged at least once within the maximum delay",
        time_value_ms="25", time_parameter="default max_ack_delay",
        time_source="RFC 9000 Section 18.2 default when max_ack_delay is absent",
        basis="NORMATIVE_DEFAULT",
        formula="G* (quic_1rtt_ack_eliciting_packet_processed_default_ack_delay -> F [0,25] (quic_ack_covering_packet_sent))",
        aps={
            "quic_1rtt_ack_eliciting_packet_processed_default_ack_delay":"Protected 1-RTT packet is fully processed, is ack-eliciting, and local max_ack_delay is the absent-parameter default.",
            "quic_ack_covering_packet_sent":"An outgoing ACK frame contains the correlated packet number.",
        },
        correlation="QUIC connection object + packet number space + packet number; packet numbers stay fields",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="conn_compute_ack_delay", source_lines="1847-1855",
        hook="Start at pktns_commit_recv_pkt_num; finish when ngtcp2_acktr_create_ack_frame output is serialized.",
        positive=tr((0,"quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"),(25,"quic_ack_covering_packet_sent"),(26,"")),
        negative=tr((0,"quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"),(26,"quic_ack_covering_packet_sent"),(27,"")),
        limitations="Initial and Handshake packets use immediate ACK semantics and are excluded from this 25 ms property.",
        extras={"profile_source_url":gh("ngtcp2/ngtcp2",NGTCP2_COMMIT,"lib/includes/ngtcp2/ngtcp2.h","1278-1285")},
    ),
    property_card(
        pid="QUIC-PTO-01", protocol="QUIC", extension="RFC 9002 recovery",
        title="Initial handshake PTO is approximately one second", category="probe timeout",
        natural="无历史 RTT 时发送 Initial/Handshake ack-eliciting 包后，PTO 不得早于 999 ms，且应在 1000 ms 内触发或被 ACK 解除。",
        strength="SHOULD/MUST computation", standard="RFC 9002", version="RFC 9002",
        section="6.2.1-6.2.2", standard_url="https://www.rfc-editor.org/rfc/rfc9002.html#section-6.2.2",
        excerpt="the initial RTT SHOULD be set to 333 milliseconds",
        time_value_ms="999..1000", time_parameter="initial handshake PTO",
        time_source="333 + 4*(333/2) = 999 ms in ngtcp2 integer arithmetic; RFC narrative calls this 1 second",
        basis="NORMATIVE_DERIVED_WITH_DOCUMENTED_ROUNDING",
        formula="G* (quic_initial_ack_eliciting_sent_no_prior_rtt -> (G [0,999) (!quic_pto_fired) && F [0,1000] (quic_pto_fired || quic_ack_newly_acknowledged)))",
        aps={
            "quic_initial_ack_eliciting_sent_no_prior_rtt":"An Initial/Handshake ack-eliciting packet is sent with no resumed-path RTT sample.",
            "quic_pto_fired":"Loss-detection timer dispatches its PTO branch.",
            "quic_ack_newly_acknowledged":"An ACK newly acknowledges an in-flight packet in the correlated packet-number space.",
        },
        correlation="connection object + Initial/Handshake packet-number space",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="conn_compute_initial_pto", source_lines="954-979",
        hook="Record the computed absolute loss_detection_timer and PTO inputs after ngtcp2_conn_set_loss_detection_timer.",
        positive=tr((0,"quic_initial_ack_eliciting_sent_no_prior_rtt"),(999,"quic_pto_fired"),(1001,"")),
        negative=tr((0,"quic_initial_ack_eliciting_sent_no_prior_rtt"),(998,"quic_pto_fired"),(1001,"")),
        confidence="MEDIUM",
        review="请确认接受 RFC 的“1 second”叙述与 ngtcp2 999 ms 整数计算之间的有据范围，而不是把它称为容差。",
        limitations="The 999..1000 range is a documented arithmetic/narrative discrepancy, not an injected epsilon; resumed RTT profiles are outside scope.",
        extras={"initial_rtt_source_url":gh("ngtcp2/ngtcp2",NGTCP2_COMMIT,"lib/includes/ngtcp2/ngtcp2.h","434-439")},
    ),
    property_card(
        pid="QUIC-PTO-02", protocol="QUIC", extension="RFC 9002 recovery",
        title="Consecutive PTO doubles after the first expiry", category="PTO backoff",
        natural="初始 PTO 以 ngtcp2 的 999 ms 计算触发后，下一连续 PTO 必须退避到 1998 ms，除非先收到新 ACK。",
        strength="MUST", standard="RFC 9002", version="RFC 9002",
        section="6.2.1", standard_url="https://www.rfc-editor.org/rfc/rfc9002.html#section-6.2.1",
        excerpt="the PTO period being set to twice its current value",
        time_value_ms="1998", time_parameter="second initial-path PTO",
        time_source="RFC 9002 exponential backoff applied to ngtcp2 initial PTO=999 ms",
        basis="NORMATIVE_DERIVED_IMPLEMENTATION_ARITHMETIC",
        formula="G* (quic_first_pto_completed_initial_profile -> (G [0,1998) (!quic_second_pto_fired) && F [0,1998] (quic_second_pto_fired || quic_ack_newly_acknowledged)))",
        aps={
            "quic_first_pto_completed_initial_profile":"The first PTO branch increments pto_count from zero to one under the initial RTT profile.",
            "quic_second_pto_fired":"The next consecutive PTO branch is entered.",
            "quic_ack_newly_acknowledged":"An ACK newly acknowledges an in-flight packet and resets backoff.",
        },
        correlation="connection object + global PTO generation across packet-number spaces",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="conn_get_earliest_pto_expiry", source_lines="13387-13424",
        hook="Emit first completion after pto_count increments; emit second fire when ngtcp2_conn_on_loss_detection_timer enters the PTO branch again.",
        positive=tr((0,"quic_first_pto_completed_initial_profile"),(1998,"quic_second_pto_fired"),(1999,"")),
        negative=tr((0,"quic_first_pto_completed_initial_profile"),(1997,"quic_second_pto_fired"),(1999,"")),
        observability="WHITEBOX",
        limitations="Uses ngtcp2's exact 999 ms initial computation; implementations rounding the first PTO to 1000 ms need a separately declared 2000 ms profile.",
    ),
    property_card(
        pid="QUIC-PTO-03", protocol="QUIC", extension="RFC 9002 recovery",
        title="PTO expiry schedules an ack-eliciting probe", category="PTO action",
        natural="PTO 到期时，发送方必须在对应包号空间安排至少一个 ack-eliciting probe。",
        strength="MUST", standard="RFC 9002", version="RFC 9002",
        section="6.2.4", standard_url="https://www.rfc-editor.org/rfc/rfc9002.html#section-6.2.4",
        excerpt="a sender MUST send at least one ack-eliciting packet",
        time_value_ms="1000 (initial profile)", time_parameter="initial PTO context",
        time_source="RFC 9002 Section 6.2.2 initial-PTO profile",
        basis="NORMATIVE_ACTION_AT_TIMER_EVENT",
        formula="G* (quic_pto_fired -> quic_ack_eliciting_probe_scheduled)",
        aps={
            "quic_pto_fired":"ngtcp2_conn_on_loss_detection_timer enters the PTO rather than loss-time branch.",
            "quic_ack_eliciting_probe_scheduled":"probe_pkt_left becomes positive in an eligible packet-number space in the same callback microstep.",
        },
        correlation="connection object + PTO generation + selected packet-number space",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="ngtcp2_conn_on_loss_detection_timer", source_lines="13478-13545",
        hook="Emit both APs after probe_pkt_left is set and before the function returns; actual serialization is a diagnostic follow-up event.",
        positive=tr((0,"quic_pto_fired quic_ack_eliciting_probe_scheduled"),(1,"")),
        negative=tr((0,"quic_pto_fired"),(1,"")), observability="WHITEBOX",
        limitations="Anti-amplification-blocked server branches do not arm PTO and therefore do not trigger this property.",
    ),
    property_card(
        pid="QUIC-IDLE-01", protocol="QUIC", extension="RFC 9000 idle timeout; ngtcp2 example profile",
        title="ngtcp2 example profile does not discard state before 30 s idle", category="idle timeout",
        natural="双方使用 ngtcp2 example 的默认 30 秒 max_idle_timeout 时，连接持续空闲满 30 秒以前不得丢弃连接状态。",
        strength="protocol contract + implementation profile", standard="RFC 9000", version="RFC 9000 (QUIC v1)",
        section="10.1", standard_url="https://www.rfc-editor.org/rfc/rfc9000.html#section-10.1",
        excerpt="closed and its state is discarded when it remains idle for longer",
        time_value_ms="30000", time_parameter="max_idle_timeout",
        time_source="ngtcp2 example client/server default timeout=30 seconds",
        basis="IMPLEMENTATION_PROFILE",
        formula="G* (quic_connection_became_idle_ngtcp2_30s_profile -> G [0,30000] (!quic_connection_state_discarded))",
        aps={
            "quic_connection_became_idle_ngtcp2_30s_profile":"Idle timer restarts with both effective transport parameters resolving to 30000 ms.",
            "quic_connection_state_discarded":"Application frees the ngtcp2 connection because ngtcp2_conn_get_idle_expiry has passed.",
        },
        correlation="ngtcp2 connection object + negotiated transport-parameter snapshot",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="ngtcp2_conn_get_idle_expiry", source_lines="14060-14092",
        hook="Emit idle start whenever conn_restart_timer_on_read/write updates idle_ts; emit discard immediately before application connection removal.",
        positive=tr((0,"quic_connection_became_idle_ngtcp2_30s_profile"),(30001,"quic_connection_state_discarded"),(30002,"")),
        negative=tr((0,"quic_connection_became_idle_ngtcp2_30s_profile"),(29999,"quic_connection_state_discarded"),(30001,"")),
        confidence="MEDIUM",
        review="请确认 30 秒只作为 ngtcp2 example profile，而不声称为 RFC 9000 默认值（RFC 缺省为 0/禁用）。",
        limitations="The library computes expiry but the example application performs destruction; this property needs one library hook and one application hook.",
        extras={"profile_source_url":gh("ngtcp2/ngtcp2",NGTCP2_COMMIT,"examples/server_base.h","70-80")},
    ),
    property_card(
        pid="QUIC-PV-01", protocol="QUIC", extension="RFC 9000 path validation; RFC 9002 initial RTT",
        title="Initial-profile path validation timeout is 2997 ms", category="path validation",
        natural="新路径无 RTT 样本且当前路径也使用 initial PTO 时，path validation 不应在 2997 ms 前失败，并应在该期限成功或放弃。",
        strength="RECOMMENDED", standard="RFC 9000", version="RFC 9000 + RFC 9002",
        section="8.2.4", standard_url="https://www.rfc-editor.org/rfc/rfc9000.html#section-8.2.4",
        excerpt="three times the larger of the current PTO or the PTO",
        time_value_ms="2997", time_parameter="path validation timeout",
        time_source="RFC 9000 3*max(PTOs), with ngtcp2/RFC 9002 initial PTO=999 ms",
        basis="NORMATIVE_RECOMMENDED_DERIVED_PROFILE",
        formula="G* (quic_new_path_validation_started_initial_profile -> (G [0,2997) (!quic_path_validation_abandoned) && F [0,2997] (quic_path_validated || quic_path_validation_abandoned)))",
        aps={
            "quic_new_path_validation_started_initial_profile":"PATH_CHALLENGE state is created for a new path with current and new-path PTO both 999 ms.",
            "quic_path_validated":"A PATH_RESPONSE matching the challenge validates the path.",
            "quic_path_validation_abandoned":"The path-validation object expires and the path is marked unusable.",
        },
        correlation="connection object + path tuple + PATH_CHALLENGE token stored only as correlation data",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="conn_compute_pv_timeout_pto", source_lines="995-1012",
        hook="Record the computed pv expiry when the validation object is created; emit success/abandon at matching response or expiry.",
        positive=tr((0,"quic_new_path_validation_started_initial_profile"),(2997,"quic_path_validation_abandoned"),(2998,"")),
        negative=tr((0,"quic_new_path_validation_started_initial_profile"),(2996,"quic_path_validation_abandoned"),(2998,"")),
        confidence="MEDIUM",
        limitations="RFC 9000 labels the 3*PTO value RECOMMENDED, not MUST; migration that supersedes an old validation attempt must be tagged as a non-timeout cancellation.",
    ),
]


TLS = [
    property_card(
        pid="TLS13-TICKET-01", protocol="TLS", extension="TLS 1.3 session tickets",
        title="TLS 1.3 tickets become unusable within seven days", category="session ticket lifetime",
        natural="客户端缓存 TLS 1.3 NewSessionTicket 后，最迟七天内必须使该 ticket 过期或移除，不得继续用于 PSK 恢复。",
        strength="MUST NOT", standard="RFC 8446", version="RFC 8446 (TLS 1.3)",
        section="4.6.1", standard_url="https://www.rfc-editor.org/rfc/rfc8446.html#section-4.6.1",
        excerpt="Clients MUST NOT cache tickets for longer than 7 days",
        time_value_ms="604800000", time_parameter="maximum ticket cache lifetime",
        time_source="RFC 8446 Section 4.6.1: 604800 seconds",
        basis="NORMATIVE_MAXIMUM",
        formula="G* (tls13_ticket_cached -> F [0,604800000] (tls13_ticket_became_unusable || tls13_ticket_removed))",
        aps={
            "tls13_ticket_cached":"A parsed TLS 1.3 NewSessionTicket is admitted to the client session cache.",
            "tls13_ticket_became_unusable":"Adapter/client marks the ticket ineligible at min(ticket_lifetime,604800s).",
            "tls13_ticket_removed":"The correlated session ticket is removed from cache before the maximum age.",
        },
        correlation="SSL_SESSION pointer/cache key + ticket nonce/hash; ticket bytes never become AP names",
        source_repo="openssl/openssl", source_commit=OPENSSL_COMMIT,
        source_path="ssl/statem/extensions_clnt.c", source_symbol="tls_construct_ctos_psk", source_lines="1094-1118",
        hook="Record ticket creation after tls_process_new_session_ticket stores tick_lifetime_hint; emit unusable when the PSK age check first rejects it or adapter expiry fires.",
        positive=tr((0,"tls13_ticket_cached"),(604800000,"tls13_ticket_became_unusable"),(604800001,"")),
        negative=tr((0,"tls13_ticket_cached"),(604800001,"")),
        triggerability="LOW", confidence="MEDIUM",
        review="OpenSSL 0437435a checks the advertised lifetime but does not explicitly expose the RFC seven-day cap;请确认使用 adapter 合成 max-age 事件并把潜在超长 ticket 视为可发现违规。",
        limitations="Requires virtual time. The source hook observes ticket age eligibility; explicit cache eviction may be lazy, so the formal AP is unusable-or-removed rather than memory freed.",
        extras={
            "ticket_parse_source_url":gh("openssl/openssl",OPENSSL_COMMIT,"ssl/statem/statem_clnt.c","2574-2665"),
            "benchmark_source":"ProFuzzBench OpenSSL pin 0437435a960123be1ced766d18d715f939698345",
        },
    ),
]


DTLS = [
    property_card(
        pid="DTLS12-RTX-01", protocol="DTLS", extension="DTLS 1.2 handshake retransmission",
        title="Initial handshake retransmission timer is one second", category="handshake retransmission timer",
        natural="发送一个仍需对端后续 flight 的 DTLS 1.2 flight 后，计时器不应在 1 秒前触发，并应在 1 秒触发或被期望 flight 取消。",
        strength="SHOULD", standard="RFC 6347", version="RFC 6347 (DTLS 1.2)",
        section="4.2.4.1", standard_url="https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1",
        excerpt="Implementations SHOULD use an initial timer value of 1 second",
        time_value_ms="1000", time_parameter="initial retransmit timer",
        time_source="RFC 6347 Section 4.2.4.1 recommended initial value",
        basis="NORMATIVE_RECOMMENDED_DEFAULT",
        formula="G* (dtls12_flight_sent_expect_reply -> (G [0,1000) (!dtls_retransmit_timer_fired) && F [0,1000] (dtls_retransmit_timer_fired || dtls_expected_peer_flight_received)))",
        aps={
            "dtls12_flight_sent_expect_reply":"A complete buffered DTLS 1.2 flight is sent and the state enters WAITING.",
            "dtls_retransmit_timer_fired":"DTLS retransmission timer is observed expired.",
            "dtls_expected_peer_flight_received":"The complete next expected peer flight is accepted, discharging the timer.",
        },
        correlation="SSL object + handshake generation + message_seq range/epoch as fields",
        source_repo="openssl/openssl", source_commit=OPENSSL_COMMIT,
        source_path="ssl/d1_lib.c", source_symbol="dtls1_start_timer", source_lines="242-284",
        hook="Emit trigger after next_timeout is programmed; emit fire in dtls1_handle_timeout or stop when the full expected flight advances state.",
        positive=tr((0,"dtls12_flight_sent_expect_reply"),(1000,"dtls_retransmit_timer_fired"),(1001,"")),
        negative=tr((0,"dtls12_flight_sent_expect_reply"),(999,"dtls_retransmit_timer_fired"),(1001,"")),
        limitations="ProFuzzBench's pinned TinyDTLS fork uses 2000 ms, so it is a known conformance-divergence target and is not the source oracle for this property.",
        extras={"benchmark_version_mismatch":"assist-project/tinydtls-fuzz@06995d43e9eba892aa7db604b3879b5f91872328 sets 2*DTLS_TICKS_PER_SECOND"},
    ),
    property_card(
        pid="DTLS12-RTX-02", protocol="DTLS", extension="DTLS 1.2 handshake retransmission",
        title="Timer expiry retransmits the buffered flight", category="retransmission action",
        natural="WAITING 状态的 retransmit timer 到期后，端点必须重传已缓冲 flight 并重置计时器。",
        strength="state-machine REQUIRED", standard="RFC 6347", version="RFC 6347 (DTLS 1.2)",
        section="4.2.4", standard_url="https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4",
        excerpt="it retransmits the flight, resets the retransmit timer",
        time_value_ms="1000 (initial profile)", time_parameter="current retransmit timer",
        time_source="RFC 6347 Section 4.2.4.1 initial profile",
        basis="NORMATIVE_STATE_MACHINE_ACTION",
        formula="G* (dtls_retransmit_timer_fired -> dtls_buffered_flight_retransmitted)",
        aps={
            "dtls_retransmit_timer_fired":"dtls1_handle_timeout confirms the timer has expired.",
            "dtls_buffered_flight_retransmitted":"dtls1_retransmit_buffered_messages succeeds in the same callback microstep.",
        },
        correlation="SSL object + handshake generation + buffered-flight identifier",
        source_repo="openssl/openssl", source_commit=OPENSSL_COMMIT,
        source_path="ssl/d1_lib.c", source_symbol="dtls1_handle_timeout", source_lines="389-414",
        hook="Emit both APs only after dtls1_retransmit_buffered_messages reports success; retain raw fire/error fields for diagnosis.",
        positive=tr((0,"dtls_retransmit_timer_fired dtls_buffered_flight_retransmitted"),(1,"")),
        negative=tr((0,"dtls_retransmit_timer_fired"),(1,"")), observability="WHITEBOX",
        limitations="A local BIO send failure is an environment outcome and must be separated from a missing retransmission attempt.",
    ),
    property_card(
        pid="DTLS12-RTX-03", protocol="DTLS", extension="DTLS 1.2 handshake retransmission",
        title="First retransmission doubles the next timer to two seconds", category="retransmission backoff",
        natural="首次 1 秒计时器到期并重传后，下一次无响应超时不得早于 2 秒，并应在 2 秒触发。",
        strength="SHOULD", standard="RFC 6347", version="RFC 6347 (DTLS 1.2)",
        section="4.2.4.1", standard_url="https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1",
        excerpt="double the value at each retransmission",
        time_value_ms="2000", time_parameter="second retransmit interval",
        time_source="RFC 6347 backoff applied to initial timer=1000 ms",
        basis="NORMATIVE_DERIVED",
        formula="G* (dtls_first_retransmission_completed -> (G [0,2000) (!dtls_second_timer_fired) && F [0,2000] (dtls_second_timer_fired || dtls_expected_peer_flight_received)))",
        aps={
            "dtls_first_retransmission_completed":"First timeout retransmits the flight and rearms the timer at 2000 ms.",
            "dtls_second_timer_fired":"Rearmed retransmission timer expires.",
            "dtls_expected_peer_flight_received":"Complete expected peer flight cancels the obligation.",
        },
        correlation="SSL object + handshake generation + retransmission count",
        source_repo="openssl/openssl", source_commit=OPENSSL_COMMIT,
        source_path="ssl/d1_lib.c", source_symbol="dtls1_double_timeout", source_lines="344-350",
        hook="Emit trigger after timeout_duration_us doubles and dtls1_start_timer programs next_timeout.",
        positive=tr((0,"dtls_first_retransmission_completed"),(2000,"dtls_second_timer_fired"),(2001,"")),
        negative=tr((0,"dtls_first_retransmission_completed"),(1999,"dtls_second_timer_fired"),(2001,"")), observability="WHITEBOX",
        limitations="Only one representative doubling is a catalog property; 4/8/16/32-second copies are duplicate obligations.",
    ),
    property_card(
        pid="DTLS12-RTX-04", protocol="DTLS", extension="DTLS 1.2 handshake retransmission",
        title="Retransmission timer caps at 60 seconds", category="retransmission cap",
        natural="当前 DTLS 重传计时器已达到 60 秒时，下一次重传后仍不得在 60 秒前再次超时。",
        strength="SHOULD", standard="RFC 6347", version="RFC 6347 (DTLS 1.2)",
        section="4.2.4.1", standard_url="https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4.1",
        excerpt="up to no less than the RFC 6298 maximum of 60 seconds",
        time_value_ms="60000", time_parameter="retransmission timer cap",
        time_source="RFC 6347 Section 4.2.4.1 and RFC 6298 minimum permitted maximum",
        basis="NORMATIVE_RECOMMENDED_CAP_PROFILE",
        formula="G* (dtls_capped_retransmission_completed -> (G [0,60000) (!dtls_capped_timer_fired) && F [0,60000] (dtls_capped_timer_fired || dtls_expected_peer_flight_received)))",
        aps={
            "dtls_capped_retransmission_completed":"A retransmission completes with timeout_duration_us clamped to 60000000.",
            "dtls_capped_timer_fired":"The capped timer expires.",
            "dtls_expected_peer_flight_received":"Complete expected peer flight cancels the timer.",
        },
        correlation="SSL object + handshake generation + retransmission count",
        source_repo="openssl/openssl", source_commit=OPENSSL_COMMIT,
        source_path="ssl/d1_lib.c", source_symbol="dtls1_double_timeout", source_lines="344-350",
        hook="Record the clamp result after timeout_duration_us is limited to 60000000 and the next timer is started.",
        positive=tr((0,"dtls_capped_retransmission_completed"),(60000,"dtls_capped_timer_fired"),(60001,"")),
        negative=tr((0,"dtls_capped_retransmission_completed"),(59999,"dtls_capped_timer_fired"),(60001,"")), observability="WHITEBOX",
        limitations="The RFC wording permits a larger implementation maximum; this exact 60-second property is the OpenSSL profile, not a universal maximum.",
    ),
    property_card(
        pid="DTLS12-FINAL-01", protocol="DTLS", extension="DTLS 1.2 final-flight recovery",
        title="Final-flight sender responds to duplicates for twice TCP MSL", category="final flight retention",
        natural="发送最后一个 handshake flight 的端点在 2*TCP MSL（RFC 793 默认 MSL=2 分钟，即 4 分钟）内收到对端前一 flight 重传时必须重传最后 flight。",
        strength="MUST", standard="RFC 6347", version="RFC 6347 (DTLS 1.2)",
        section="4.2.4", standard_url="https://www.rfc-editor.org/rfc/rfc6347.html#section-4.2.4",
        excerpt="for at least twice the default MSL defined for TCP",
        time_value_ms="240000", time_parameter="2 * TCP default MSL",
        time_source="RFC 6347 references the TCP default MSL; RFC 793 Section 3.3 defines MSL as 2 minutes",
        basis="NORMATIVE_REFERENCED_DEFAULT",
        formula="G* (dtls_final_flight_sent -> G [0,240000] (dtls_peer_previous_flight_duplicate -> dtls_final_flight_retransmitted))",
        aps={
            "dtls_final_flight_sent":"Endpoint successfully sends the last flight and retains its buffered messages.",
            "dtls_peer_previous_flight_duplicate":"A complete duplicate of the peer's prior handshake flight is recognized.",
            "dtls_final_flight_retransmitted":"Buffered final flight is retransmitted in response in the same processing microstep.",
        },
        correlation="SSL object + epoch + handshake generation + message_seq range",
        source_repo="openssl/openssl", source_commit=OPENSSL_COMMIT,
        source_path="ssl/record/rec_layer_d1.c", source_symbol="dtls1_read_bytes", source_lines="662-679",
        hook="At final-flight send retain a generation marker; on repeated Finished emit duplicate and retransmission APs after retransmit succeeds.",
        positive=tr((0,"dtls_final_flight_sent"),(240000,"dtls_peer_previous_flight_duplicate dtls_final_flight_retransmitted"),(240001,"")),
        negative=tr((0,"dtls_final_flight_sent"),(120000,"dtls_peer_previous_flight_duplicate"),(240001,"")),
        confidence="MEDIUM",
        review="请确认沿用 RFC 6347 对 RFC 793 默认 MSL 的规范引用得到 240000 ms，并在论文中声明该历史版本依赖。",
        limitations="RFC 9293 no longer supplies a numeric MSL; this property intentionally follows RFC 6347's contemporaneous RFC 793 reference.",
        extras={"time_source_url":"https://www.rfc-editor.org/rfc/rfc793.html#section-3.3"},
    ),
]


SSH = [
    property_card(
        pid="SSH-REKEY-01", protocol="SSH", extension="SSH Transport Layer Protocol",
        title="Connection keys are changed within one hour", category="time-based rekey",
        natural="认证完成并安装新密钥后，只要连接仍存活，最迟一小时内应启动下一次 key exchange；达到 1GB 可更早触发。",
        strength="RECOMMENDED", standard="RFC 4253", version="RFC 4253",
        section="9", standard_url="https://www.rfc-editor.org/rfc/rfc4253.html#section-9",
        excerpt="keys be changed after each gigabyte or after each hour",
        time_value_ms="3600000", time_parameter="time-based rekey interval",
        time_source="RFC 4253 Section 9 recommended one-hour alternative",
        basis="NORMATIVE_RECOMMENDED_PROFILE",
        formula="G* (ssh_newkeys_installed_authenticated -> F [0,3600000] (ssh_rekey_started || ssh_connection_closed))",
        aps={
            "ssh_newkeys_installed_authenticated":"SSH2_MSG_NEWKEYS completes and rekey_time is set after authentication.",
            "ssh_rekey_started":"kex_start_rekex sends/queues SSH2_MSG_KEXINIT for the correlated connection.",
            "ssh_connection_closed":"Transport connection terminates before the hour deadline.",
        },
        correlation="OpenSSH ssh/session_state pointer + connection tuple; packet sequence counters remain fields",
        source_repo="vegard/openssh-portable", source_commit=OPENSSH_COMMIT,
        source_path="packet.c", source_symbol="ssh_packet_need_rekeying", source_lines="1043-1085",
        hook="Configure RekeyLimit with a one-hour interval; emit start when the time predicate returns true and kex_start_rekex is called.",
        positive=tr((0,"ssh_newkeys_installed_authenticated"),(3600000,"ssh_rekey_started"),(3600001,"")),
        negative=tr((0,"ssh_newkeys_installed_authenticated"),(3600001,"")),
        confidence="MEDIUM", triggerability="LOW",
        review="ProFuzzBench OpenSSH 默认 rekey_interval=0；请确认实验显式配置 RekeyLimit default 1h，并把该差异列为 baseline modification。",
        limitations="The pinned ProFuzzBench build does not enable a time interval by default. This is an RFC-recommended experiment profile, not the untouched benchmark default.",
        extras={
            "rekey_start_source_url":gh("vegard/openssh-portable",OPENSSH_COMMIT,"packet.c","1313-1351"),
            "profile_setter_source_url":gh("vegard/openssh-portable",OPENSSH_COMMIT,"packet.c","2428-2445"),
            "benchmark_default_source_url":gh("vegard/openssh-portable",OPENSSH_COMMIT,"servconf.c","284-289"),
        },
    ),
]


DICOM = [
    property_card(
        pid="DICOM-ARTIM-01", protocol="DICOM", extension="DICOM Upper Layer Protocol for TCP/IP",
        title="DCMTK profile expires ARTIM after 30 seconds awaiting A-ASSOCIATE-RQ", category="association request timer",
        natural="SCP 接受 TCP 连接并启动 ARTIM 后，若 30 秒内未收到 A-ASSOCIATE-RQ，则 ARTIM 应在 30 秒触发；收到请求则取消义务。",
        strength="SHALL timer; duration IMPLEMENTATION_PROFILE", standard="DICOM PS3.8", version="DICOM PS3.8 2026c",
        section="9.1.5, 9.2.2 AE-5/AA-2T", standard_url="https://dicom.nema.org/medical/dicom/current/output/chtml/part08/chapter_9.html#sect_9.1.5",
        excerpt="a timer ARTIM (Association Request/Reject/Release Timer) shall be set",
        time_value_ms="30000", time_parameter="ARTIM/ACSE timeout",
        time_source="DICOM requires configurability; DCMTK DcmSCU/dcmnet application profile defaults ACSE timeout to 30 seconds",
        basis="IMPLEMENTATION_PROFILE",
        formula="G* (dicom_tcp_connection_accepted_dcmtk_30s_profile -> (G [0,30000) (!dicom_artim_expired) && F [0,30000] (dicom_artim_expired || dicom_associate_rq_received)))",
        aps={
            "dicom_tcp_connection_accepted_dcmtk_30s_profile":"DUL acceptor accepts TCP and the association timeout field is 30 seconds.",
            "dicom_artim_expired":"PRV_NextPDUType returns DUL_READTIMEOUT and dispatches ARTIM_TIMER_EXPIRED.",
            "dicom_associate_rq_received":"A valid A-ASSOCIATE-RQ PDU is recognized for the association.",
        },
        correlation="DUL association pointer + TCP 4-tuple; presentation-context IDs stay fields",
        source_repo="DCMTK/dcmtk", source_commit=DCMTK_COMMIT,
        source_path="dcmnet/libsrc/dul.cc", source_symbol="DUL_ReceiveAssociationRQ", source_lines="687-707",
        hook="Emit start after receiveTransportConnection/TRANS_CONN_INDICATION; emit expiry on DUL_READTIMEOUT before state-machine dispatch.",
        positive=tr((0,"dicom_tcp_connection_accepted_dcmtk_30s_profile"),(30000,"dicom_artim_expired"),(30001,"")),
        negative=tr((0,"dicom_tcp_connection_accepted_dcmtk_30s_profile"),(29999,"dicom_artim_expired"),(30001,"")),
        confidence="MEDIUM",
        review="请确认把 30 秒严格标作 DCMTK profile；DICOM PS3.8 只要求 ARTIM 可配置，不给出协议通用数值。",
        limitations="The 2020 DCMTK source predates PS3.8 2026c, but the cited ARTIM actions are unchanged; this is a source/profile mapping, not a claim that 30 seconds is standardized.",
        extras={
            "profile_source_url":gh("DCMTK/dcmtk",DCMTK_COMMIT,"dcmnet/libsrc/scu.cc","34-51"),
            "fsm_action_source_url":gh("DCMTK/dcmtk",DCMTK_COMMIT,"dcmnet/libsrc/dulfsm.cc","1096-1127"),
        },
    ),
]

# RFC 9293 gives two additional non-duplicate R2 lifetime obligations: one
# SHOULD for established-data failure and one MUST for SYN opening.  They are
# safety properties so external RST/ICMP/application abort outcomes are
# explicitly different APs and do not count as R2 expiry.
TCP.extend([
    property_card(
        pid="TCP-R2-01", protocol="TCP", extension="RFC 9293 connection-failure thresholds",
        title="Data retransmission R2 is at least 100 seconds", category="connection failure timeout",
        natural="已建立连接因同一数据持续重传进入默认 R2 计时时，在 100 秒前不应因 excessive retransmission 关闭。",
        strength="SHOULD", standard="RFC 9293", version="RFC 9293",
        section="3.8.3", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.3",
        excerpt="The value of R2 SHOULD correspond to at least 100 seconds",
        time_value_ms="100000", time_parameter="established-data R2 lower bound",
        time_source="RFC 9293 Section 3.8.3",
        basis="NORMATIVE_MINIMUM",
        formula="G* (tcp_data_r2_episode_started -> G [0,100000) (!tcp_closed_by_data_r2_expiry))",
        aps={
            "tcp_data_r2_episode_started":"First retransmission timestamp is established for data in an established connection using default R2 policy.",
            "tcp_closed_by_data_r2_expiry":"tcp_write_timeout reports expired and tcp_write_err closes specifically because the data R2 threshold is reached.",
        },
        correlation="network namespace + socket cookie + retransmission episode",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="net/ipv4/tcp_timer.c", source_symbol="tcp_write_timeout", source_lines="242-305",
        hook="Emit start when retrans_stamp is first set; emit expiry immediately before tcp_write_err with state outside SYN_SENT/SYN_RECV and expired=true.",
        positive=tr((0,"tcp_data_r2_episode_started"),(100000,"tcp_closed_by_data_r2_expiry"),(100001,"")),
        negative=tr((0,"tcp_data_r2_episode_started"),(99999,"tcp_closed_by_data_r2_expiry"),(100001,"")),
        confidence="HIGH", triggerability="LOW",
        limitations="An application-selected TCP_USER_TIMEOUT, external RST/ICMP, resource pressure or application close is not `tcp_closed_by_data_r2_expiry`.",
    ),
    property_card(
        pid="TCP-SYN-01", protocol="TCP", extension="RFC 9293 active-open failure threshold",
        title="SYN retransmission R2 covers at least three minutes", category="connection establishment timeout",
        natural="主动打开在无 RST、ICMP 或应用取消时，不得在首个 SYN 后 180 秒内因 SYN excessive retransmission 的 R2 阈值失败。",
        strength="MUST", standard="RFC 9293", version="RFC 9293",
        section="3.8.3", standard_url="https://www.rfc-editor.org/rfc/rfc9293.html#section-3.8.3",
        excerpt="R2 for a SYN segment MUST be set ... for at least 3 minutes",
        time_value_ms="180000", time_parameter="SYN R2 lower bound",
        time_source="RFC 9293 Section 3.8.3",
        basis="NORMATIVE_MINIMUM",
        formula="G* (tcp_active_open_syn_r2_started -> G [0,180000) (!tcp_open_failed_by_syn_r2_expiry))",
        aps={
            "tcp_active_open_syn_r2_started":"Initial SYN is transmitted for an active open under the stack's default SYN-retry policy.",
            "tcp_open_failed_by_syn_r2_expiry":"tcp_write_timeout closes SYN_SENT specifically because its retransmission R2 threshold expired.",
        },
        correlation="network namespace + socket cookie + active-open attempt",
        source_repo="torvalds/linux", source_commit=LINUX_COMMIT,
        source_path="net/ipv4/tcp_timer.c", source_symbol="tcp_write_timeout", source_lines="242-298",
        hook="Start at initial SYN output; emit failure immediately before tcp_write_err when SYN_SENT and expired is due to retry_until.",
        positive=tr((0,"tcp_active_open_syn_r2_started"),(180000,"tcp_open_failed_by_syn_r2_expiry"),(180001,"")),
        negative=tr((0,"tcp_active_open_syn_r2_started"),(179999,"tcp_open_failed_by_syn_r2_expiry"),(180001,"")),
        confidence="HIGH", triggerability="LOW",
        review="Linux 源码注释称默认 TCP_SYN_RETRIES=6 约 63 秒，可能早于 RFC 180 秒；请把它作为待实测偏差，而非先验宣称 bug。",
        limitations="The RFC allows the application to close sooner; RST, ICMP unreachable and application cancellation are deliberately separate terminal causes.",
        extras={"implementation_deviation_evidence_url":gh("torvalds/linux",LINUX_COMMIT,"include/net/tcp.h","124-131")},
    ),
])

QUIC.extend([
    property_card(
        pid="QUIC-PC-01", protocol="QUIC", extension="RFC 9002 persistent congestion",
        title="Persistent congestion is not declared before three PTO periods", category="persistent congestion",
        natural="在默认 initial RTT 和 max_ack_delay profile 下，连续丢失区间尚未达到 3072 ms 时不得宣告 persistent congestion。",
        strength="RECOMMENDED threshold", standard="RFC 9002", version="RFC 9002",
        section="7.6.1", standard_url="https://www.rfc-editor.org/rfc/rfc9002.html#section-7.6.1",
        excerpt="The RECOMMENDED value for kPersistentCongestionThreshold is 3",
        time_value_ms="3072", time_parameter="persistent congestion duration",
        time_source="(333 + 4*(333/2) + 25) * 3 = 3072 ms under RFC/ngtcp2 defaults",
        basis="NORMATIVE_RECOMMENDED_DERIVED_PROFILE",
        formula="G* (quic_app_loss_run_started_initial_profile -> G [0,3072) (!quic_persistent_congestion_declared))",
        aps={
            "quic_app_loss_run_started_initial_profile":"Oldest packet in a contiguous all-lost application-space run is sent after handshake confirmation with initial RTT and default max_ack_delay.",
            "quic_persistent_congestion_declared":"Congestion controller's on_persistent_congestion callback is invoked for that loss run.",
        },
        correlation="connection object + application packet-number space + contiguous sent-packet range",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_rtb.c", source_symbol="rtb_detect_lost_pkt", source_lines="1045-1085",
        hook="Record the oldest timestamp when the contiguous loss-run candidate begins; emit declaration at on_persistent_congestion.",
        positive=tr((0,"quic_app_loss_run_started_initial_profile"),(3072,"quic_persistent_congestion_declared"),(3073,"")),
        negative=tr((0,"quic_app_loss_run_started_initial_profile"),(3071,"quic_persistent_congestion_declared"),(3073,"")),
        confidence="MEDIUM",
        limitations="This is a no-early-declaration safety oracle. Establishment also requires all relevant ack-eliciting packets in the duration to be declared lost.",
        extras={"threshold_source_url":gh("ngtcp2/ngtcp2",NGTCP2_COMMIT,"lib/ngtcp2_cc.h","34-38"),"declaration_source_url":gh("ngtcp2/ngtcp2",NGTCP2_COMMIT,"lib/ngtcp2_rtb.c","1162-1185")},
    ),
    property_card(
        pid="QUIC-KU-01", protocol="QUIC", extension="RFC 9001 QUIC-TLS key update",
        title="Subsequent key update waits three PTO periods", category="key update spacing",
        natural="前一次 key update 已被 ACK 确认后，在默认 application PTO=1024 ms 的 profile 下，端点不应在 3072 ms 前再主动更新密钥。",
        strength="SHOULD", standard="RFC 9001", version="RFC 9001",
        section="6.5", standard_url="https://www.rfc-editor.org/rfc/rfc9001.html#section-6.5",
        excerpt="Endpoints SHOULD wait three times the PTO before initiating a key update",
        time_value_ms="3072", time_parameter="minimum interval after confirmed key update",
        time_source="3 * (333 + 4*(333/2) + default max_ack_delay 25) = 3072 ms",
        basis="NORMATIVE_RECOMMENDED_DERIVED_PROFILE",
        formula="G* (quic_previous_key_update_confirmed_initial_profile -> G [0,3072) (!quic_local_next_key_update_started))",
        aps={
            "quic_previous_key_update_confirmed_initial_profile":"ACK confirms the previous key phase and current PTO inputs still equal the initial/default application profile.",
            "quic_local_next_key_update_started":"Local endpoint rotates transmit/receive keys to initiate the next key phase.",
        },
        correlation="ngtcp2 connection object + monotonically increasing key-update generation",
        source_repo="ngtcp2/ngtcp2", source_commit=NGTCP2_COMMIT,
        source_path="lib/ngtcp2_conn.c", source_symbol="conn_initiate_key_update", source_lines="11281-11297",
        hook="Emit confirmation when confirmed_ts is assigned; emit next-start after conn_rotate_keys succeeds as initiator.",
        positive=tr((0,"quic_previous_key_update_confirmed_initial_profile"),(3072,"quic_local_next_key_update_started"),(3073,"")),
        negative=tr((0,"quic_previous_key_update_confirmed_initial_profile"),(3071,"quic_local_next_key_update_started"),(3073,"")),
        confidence="MEDIUM", triggerability="MEDIUM",
        limitations="Only applies while current smoothed_rtt/rttvar and peer max_ack_delay equal the declared profile; otherwise the live 3*PTO bound must be projected into a separately instantiated property.",
        extras={"confirmation_source_url":gh("ngtcp2/ngtcp2",NGTCP2_COMMIT,"lib/ngtcp2_conn.c","3455-3474")},
    ),
])

# These three state-machine actions are genuine normative obligations, but the
# current finite G* semantics leaves a missing same-microstep consequent
# INCONCLUSIVE.  Encoding them as F[0,1) would introduce an adapter-resolution
# bound not supplied by the protocol.  Keep them in excluded rather than
# weakening the evidence gate.
TCP = [p for p in TCP if p["id"] != "TCP-RTO-02"]
QUIC = [p for p in QUIC if p["id"] != "QUIC-PTO-03"]
DTLS = [p for p in DTLS if p["id"] != "DTLS12-RTX-02"]


def revise(cards: list[dict[str, object]], pid: str, **changes: object) -> None:
    """Apply evidence-audit corrections without obscuring the original extraction."""
    card = next(p for p in cards if p["id"] == pid)
    card.update(changes)
    if "mightyppl_formula" in changes:
        card["mathematical_mitl"] = changes["mightyppl_formula"]


# Independent audit: five cards are sound as written.  The source APs remain
# events from the implementation; dynamic packet/socket identifiers are only
# correlation fields.
for _pid in ("TCP-ACK-01", "TCP-KA-01", "TCP-R2-01", "TCP-SYN-01"):
    revise(TCP, _pid, independent_audit_status="APPROVE",
           independent_audit_note="Independent standard/formula/source audit approved this card without a semantic correction.")
revise(QUIC, "QUIC-ACK-01", independent_audit_status="APPROVE",
       independent_audit_note="Independent audit confirmed the 25 ms closed upper bound and default-parameter trigger.")

# Timer-window cards are monitored per concrete arm/rearm generation.  The
# trigger therefore asserts the actual configured absolute deadline rather
# than inferring it from a packet send.  Supersession/cancellation discharges
# only the correlated timer generation.
revise(
    TCP, "TCP-RTO-01",
    title="Linux RFC-recommended initial RTO profile arms 1000 ms",
    natural_language="Linux 未采用 3 秒 fallback、thin-stream 或自定义策略且实际按 1000 ms arm 初始 RTO 后，该 timer generation 不得提前到期，并须在 1000 ms 到期或被关联事件替换/取消。",
    mightyppl_formula="G* (tcp_initial_rto_armed_1000ms_profile -> (G [0,1000) (!tcp_initial_rto_deadline_reached) && F [0,1000] (tcp_initial_rto_deadline_reached || tcp_initial_rto_superseded)))",
    atomic_propositions=["tcp_initial_rto_armed_1000ms_profile", "tcp_initial_rto_deadline_reached", "tcp_initial_rto_superseded"],
    ap_definitions={
        "tcp_initial_rto_armed_1000ms_profile":"ICSK_TIME_RETRANS is actually armed with a 1000 ms absolute deadline and fallback/override branches are false.",
        "tcp_initial_rto_deadline_reached":"The absolute deadline of that exact retransmission-timer generation is reached.",
        "tcp_initial_rto_superseded":"A correlated ACK, loss-state change, or explicit timer restart/cancel replaces that exact timer generation.",
    },
    instrumentation_timing="Emit trigger from the timer-arm hook with deadline and generation; emit deadline independently of callback dispatch; emit superseded only when that generation is cancelled/rearmed.",
    positive_trace=tr((0,"tcp_initial_rto_armed_1000ms_profile"),(1000,"tcp_initial_rto_deadline_reached"),(1001,"")),
    negative_trace=tr((0,"tcp_initial_rto_armed_1000ms_profile"),(999,"tcp_initial_rto_deadline_reached"),(1001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"tcp_initial_rto_armed_1000ms_profile"),(1001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Trigger now binds the actual 1000 ms arm generation, excludes fallback, observes deadline rather than callback, and has early plus missing negatives.",
)
revise(
    TCP, "TCP-RTO-03",
    natural_language="正常指数退避分支实际按 2000 ms 重设第二个 RTO generation 后，不得提前到期，并须在 2000 ms 到期或被有效 ACK/重设取消。",
    mightyppl_formula="G* (tcp_second_rto_armed_2000ms_normal_backoff -> (G [0,2000) (!tcp_second_rto_deadline_reached) && F [0,2000] (tcp_second_rto_deadline_reached || tcp_second_rto_superseded)))",
    atomic_propositions=["tcp_second_rto_armed_2000ms_normal_backoff", "tcp_second_rto_deadline_reached", "tcp_second_rto_superseded"],
    ap_definitions={
        "tcp_second_rto_armed_2000ms_normal_backoff":"The normal non-linear, non-thin-stream branch doubles 1000 ms to 2000 ms and arms a new timer generation.",
        "tcp_second_rto_deadline_reached":"The absolute deadline of that exact 2000 ms generation is reached.",
        "tcp_second_rto_superseded":"A qualifying ACK or timer restart/cancel replaces that exact generation.",
    },
    positive_trace=tr((0,"tcp_second_rto_armed_2000ms_normal_backoff"),(2000,"tcp_second_rto_deadline_reached"),(2001,"")),
    negative_trace=tr((0,"tcp_second_rto_armed_2000ms_normal_backoff"),(1999,"tcp_second_rto_deadline_reached"),(2001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"tcp_second_rto_armed_2000ms_normal_backoff"),(2001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Encoded normal-backoff branch, correlated supersession, deadline event, and late/missing negative.",
)
revise(
    TCP, "TCP-ZWP-01",
    natural_language="发送窗口为零且当前 RTO=1000 ms 时，实际 arm 的首个 probe timer 不得提前到期，并须在 1000 ms 到期/尝试发送，或因窗口打开、连接终止而取消。",
    mightyppl_formula="G* (tcp_probe0_timer_armed_1000ms -> (G [0,1000) (!tcp_probe0_deadline_or_attempt) && F [0,1000] (tcp_probe0_deadline_or_attempt || tcp_probe0_superseded)))",
    atomic_propositions=["tcp_probe0_timer_armed_1000ms", "tcp_probe0_deadline_or_attempt", "tcp_probe0_superseded"],
    ap_definitions={
        "tcp_probe0_timer_armed_1000ms":"ICSK_TIME_PROBE0 is actually armed at a 1000 ms deadline for one zero-window generation.",
        "tcp_probe0_deadline_or_attempt":"That generation reaches its deadline and enters the probe-attempt path, independent of local send success.",
        "tcp_probe0_superseded":"Window-open, user-timeout, connection termination, or explicit timer replacement cancels that generation.",
    },
    positive_trace=tr((0,"tcp_probe0_timer_armed_1000ms"),(1000,"tcp_probe0_deadline_or_attempt"),(1001,"")),
    negative_trace=tr((0,"tcp_probe0_timer_armed_1000ms"),(999,"tcp_probe0_deadline_or_attempt"),(1001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"tcp_probe0_timer_armed_1000ms"),(1001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Separated timer/attempt correctness from successful local transmission and encoded correlated cancellation.",
)
revise(
    TCP, "TCP-ZWP-02",
    natural_language="正常 probe 退避分支实际按 2000 ms arm 下一 generation 后，不得提前到期，并须在 2000 ms 到期/尝试发送，或被窗口打开、资源重调度、终止所替换。",
    mightyppl_formula="G* (tcp_probe0_backoff_armed_2000ms -> (G [0,2000) (!tcp_probe0_second_deadline_or_attempt) && F [0,2000] (tcp_probe0_second_deadline_or_attempt || tcp_probe0_second_superseded)))",
    atomic_propositions=["tcp_probe0_backoff_armed_2000ms", "tcp_probe0_second_deadline_or_attempt", "tcp_probe0_second_superseded"],
    ap_definitions={
        "tcp_probe0_backoff_armed_2000ms":"Normal zero-window backoff increments and arms the next timer generation at 2000 ms.",
        "tcp_probe0_second_deadline_or_attempt":"That exact generation reaches deadline and enters its send-attempt path.",
        "tcp_probe0_second_superseded":"Window-open, local-resource reschedule, user-timeout, termination, or explicit rearm replaces the generation.",
    },
    positive_trace=tr((0,"tcp_probe0_backoff_armed_2000ms"),(2000,"tcp_probe0_second_deadline_or_attempt"),(2001,"")),
    negative_trace=tr((0,"tcp_probe0_backoff_armed_2000ms"),(1999,"tcp_probe0_second_deadline_or_attempt"),(2001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"tcp_probe0_backoff_armed_2000ms"),(2001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Uses rearm/deadline/attempt and explicit resource/cancel supersession instead of send success.",
)
revise(
    TCP, "TCP-TW-01",
    title="Linux TIME-WAIT 60-second profile with guarded reopen",
    natural_language="Linux 60 秒 TIME-WAIT profile 中，若未发生 RFC 允许的 guarded reopen/reuse 或管理性清理，状态不得在 60000 ms 前因普通 TIME-WAIT expiry 被销毁。",
    time_value_ms="60000", time_parameter="Linux TCP_TIMEWAIT_LEN", time_source="Linux fixed profile TCP_TIMEWAIT_LEN=60 seconds; RFC 9293 supplies the linger contract but not this implementation value", instantiation_basis="IMPLEMENTATION_PROFILE",
    mightyppl_formula="G* (tcp_time_wait_entered_linux_profile -> G [0,60000) ((!tcp_time_wait_state_destroyed) || tcp_valid_timewait_reopen_or_admin_cleanup))",
    atomic_propositions=["tcp_time_wait_entered_linux_profile", "tcp_time_wait_state_destroyed", "tcp_valid_timewait_reopen_or_admin_cleanup"],
    ap_definitions={
        "tcp_time_wait_entered_linux_profile":"A TIME-WAIT bucket is created with Linux TCP_TIMEWAIT_LEN=60 seconds.",
        "tcp_time_wait_state_destroyed":"The bucket is removed by the ordinary TIME-WAIT expiry path.",
        "tcp_valid_timewait_reopen_or_admin_cleanup":"Guarded RFC reopen/reuse or explicit administrative cleanup causes early removal and is classified separately.",
    },
    positive_trace=tr((0,"tcp_time_wait_entered_linux_profile"),(60000,"tcp_time_wait_state_destroyed"),(60001,"")),
    negative_trace=tr((0,"tcp_time_wait_entered_linux_profile"),(59999,"tcp_time_wait_state_destroyed"),(60001,"")),
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Restored the locked Linux 60 s profile and encoded RFC-permitted guarded reopen/administrative cleanup.",
)

revise(
    QUIC, "QUIC-PTO-01",
    natural_language="ngtcp2 初始 profile 实际 arm 999 ms PTO generation 后，该 generation 不得提前到期，并须在 999 ms 到期或因新的 loss timer/ACK/key discard 重设而失效。",
    mightyppl_formula="G* (quic_pto_armed_999ms_initial_profile -> (G [0,999) (!quic_pto_deadline_reached) && F [0,999] (quic_pto_deadline_reached || quic_pto_generation_superseded)))",
    atomic_propositions=["quic_pto_armed_999ms_initial_profile", "quic_pto_deadline_reached", "quic_pto_generation_superseded"],
    ap_definitions={
        "quic_pto_armed_999ms_initial_profile":"Loss detection actually selects PTO (not time-threshold loss) and arms a generation at 999 ms with pto_count=0.",
        "quic_pto_deadline_reached":"The absolute deadline for that exact PTO generation is reached.",
        "quic_pto_generation_superseded":"A qualifying ACK, later ack-eliciting send, key discard, or loss-timer replacement rearms/cancels that generation.",
    },
    positive_trace=tr((0,"quic_pto_armed_999ms_initial_profile"),(999,"quic_pto_deadline_reached"),(1000,"")),
    negative_trace=tr((0,"quic_pto_armed_999ms_initial_profile"),(998,"quic_pto_deadline_reached"),(1000,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"quic_pto_armed_999ms_initial_profile"),(1000,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Obligation begins at the actual selected PTO arm and is cancelled by all RFC timer-supersession events.",
)
revise(
    QUIC, "QUIC-PTO-02",
    natural_language="pto_count=1 且默认 profile 实际按 1998 ms arm 下一 PTO generation 后，不得提前到期；须到期或被真正重置 backoff 的 ACK/重发事件替换。",
    mightyppl_formula="G* (quic_pto_backoff_armed_1998ms -> (G [0,1998) (!quic_second_pto_deadline_reached) && F [0,1998] (quic_second_pto_deadline_reached || quic_second_pto_superseded)))",
    atomic_propositions=["quic_pto_backoff_armed_1998ms", "quic_second_pto_deadline_reached", "quic_second_pto_superseded"],
    ap_definitions={
        "quic_pto_backoff_armed_1998ms":"After probe transmission pto_count=1 and the selected PTO generation is actually armed at 1998 ms.",
        "quic_second_pto_deadline_reached":"That exact backoff generation reaches its absolute deadline.",
        "quic_second_pto_superseded":"A later send/rearm or an ACK that RFC 9002 says resets PTO backoff replaces that exact generation.",
    },
    positive_trace=tr((0,"quic_pto_backoff_armed_1998ms"),(1998,"quic_second_pto_deadline_reached"),(1999,"")),
    negative_trace=tr((0,"quic_pto_backoff_armed_1998ms"),(1997,"quic_second_pto_deadline_reached"),(1999,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"quic_pto_backoff_armed_1998ms"),(1999,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Trigger is actual pto_count=1 rearm; broad ACK discharge was replaced with generation-specific supersession.",
)
revise(
    QUIC, "QUIC-IDLE-01",
    mightyppl_formula="G* (quic_connection_became_idle_ngtcp2_30s_profile -> G [0,30000] ((!quic_connection_state_discarded) || quic_explicit_close_or_terminal_received))",
    atomic_propositions=["quic_connection_became_idle_ngtcp2_30s_profile", "quic_connection_state_discarded", "quic_explicit_close_or_terminal_received"],
    ap_definitions={
        "quic_connection_became_idle_ngtcp2_30s_profile":"Negotiated effective idle timeout is 30000 ms and the last activity timestamp starts a new idle generation.",
        "quic_connection_state_discarded":"Connection state is disposed specifically by the idle-expiry path.",
        "quic_explicit_close_or_terminal_received":"Application close, peer close/stateless reset, or terminal transport error legitimately ends the open-idle profile.",
    },
    positive_trace=tr((0,"quic_connection_became_idle_ngtcp2_30s_profile"),(30001,"quic_connection_state_discarded"),(30002,"")),
    negative_trace=tr((0,"quic_connection_became_idle_ngtcp2_30s_profile"),(29999,"quic_connection_state_discarded"),(30001,"")),
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Explicit close, stateless reset, and terminal transport outcomes now discharge the idle-only profile.",
)
revise(
    QUIC, "QUIC-PV-01",
    natural_language="两个 PTO 快照均为 999 ms 且实际 arm 2997 ms path-validation generation 后，不得因 timeout 提前放弃；须在期限成功、timeout，或被新迁移/应用决策替换。",
    mightyppl_formula="G* (quic_path_validation_armed_2997ms_profile -> (G [0,2997) (!quic_path_abandoned_by_timeout) && F [0,2997] (quic_path_validated || quic_path_abandoned_by_timeout || quic_path_validation_superseded)))",
    atomic_propositions=["quic_path_validation_armed_2997ms_profile", "quic_path_validated", "quic_path_abandoned_by_timeout", "quic_path_validation_superseded"],
    ap_definitions={
        "quic_path_validation_armed_2997ms_profile":"Path validation is actually armed at 3*max(999,999)=2997 ms with both PTO snapshots recorded.",
        "quic_path_validated":"Matching PATH_RESPONSE validates that path generation.",
        "quic_path_abandoned_by_timeout":"That generation is abandoned specifically because its validation deadline expires.",
        "quic_path_validation_superseded":"New migration/path challenge or explicit application decision replaces that generation.",
    },
    positive_trace=tr((0,"quic_path_validation_armed_2997ms_profile"),(2997,"quic_path_abandoned_by_timeout"),(2998,"")),
    negative_trace=tr((0,"quic_path_validation_armed_2997ms_profile"),(2996,"quic_path_abandoned_by_timeout"),(2998,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"quic_path_validation_armed_2997ms_profile"),(2998,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Separated timeout abandonment from supersession and bound the trigger to both PTO snapshots plus actual arm.",
)

revise(
    DTLS, "DTLS12-RTX-01",
    natural_language="OpenSSL DTLS 1.2 datagram、无 timer_cb override 的默认分支实际按 1000 ms arm 后，不得提前到期，并须在期限到达或被期望 flight/重设取消。",
    mightyppl_formula="G* (dtls12_timer_armed_1000ms_default_profile -> (G [0,1000) (!dtls12_timer_deadline_reached) && F [0,1000] (dtls12_timer_deadline_reached || dtls12_timer_superseded)))",
    atomic_propositions=["dtls12_timer_armed_1000ms_default_profile", "dtls12_timer_deadline_reached", "dtls12_timer_superseded"],
    ap_definitions={
        "dtls12_timer_armed_1000ms_default_profile":"A non-SCTP DTLS 1.2 flight actually arms the default 1-second timer with no timer_cb override.",
        "dtls12_timer_deadline_reached":"The absolute deadline for that timer generation is reached.",
        "dtls12_timer_superseded":"Expected peer flight, stop_timer, or a valid duplicate-flight timer restart replaces that generation.",
    },
    positive_trace=tr((0,"dtls12_timer_armed_1000ms_default_profile"),(1000,"dtls12_timer_deadline_reached"),(1001,"")),
    negative_trace=tr((0,"dtls12_timer_armed_1000ms_default_profile"),(999,"dtls12_timer_deadline_reached"),(1001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"dtls12_timer_armed_1000ms_default_profile"),(1001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Restricted to datagram/no-callback default arm and replaced callback dispatch with deadline/supersession events.",
)
revise(
    DTLS, "DTLS12-RTX-03",
    natural_language="第一次重传后实际按 2000 ms arm 的 DTLS generation 不得提前到期，并须在期限到达或因期望/重复 flight 重启而失效。",
    mightyppl_formula="G* (dtls12_timer_rearmed_2000ms -> (G [0,2000) (!dtls12_second_deadline_reached) && F [0,2000] (dtls12_second_deadline_reached || dtls12_second_timer_superseded)))",
    atomic_propositions=["dtls12_timer_rearmed_2000ms", "dtls12_second_deadline_reached", "dtls12_second_timer_superseded"],
    ap_definitions={
        "dtls12_timer_rearmed_2000ms":"The first retransmission doubles the timeout and actually arms the next timer generation at 2000 ms.",
        "dtls12_second_deadline_reached":"That exact generation reaches its absolute deadline.",
        "dtls12_second_timer_superseded":"Expected next flight, duplicate previous flight, stop_timer, or explicit restart replaces the generation.",
    },
    positive_trace=tr((0,"dtls12_timer_rearmed_2000ms"),(2000,"dtls12_second_deadline_reached"),(2001,"")),
    negative_trace=tr((0,"dtls12_timer_rearmed_2000ms"),(1999,"dtls12_second_deadline_reached"),(2001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"dtls12_timer_rearmed_2000ms"),(2001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Added duplicate-flight restart/supersession and an explicit late/missing oracle.",
)
revise(
    DTLS, "DTLS12-RTX-04",
    natural_language="OpenSSL profile 达到并实际按 60000 ms arm 的 capped generation 不得提前到期，并须到期或因期望/重复 flight 重启而失效。",
    mightyppl_formula="G* (dtls12_timer_rearmed_60000ms_cap -> (G [0,60000) (!dtls12_capped_deadline_reached) && F [0,60000] (dtls12_capped_deadline_reached || dtls12_capped_timer_superseded)))",
    atomic_propositions=["dtls12_timer_rearmed_60000ms_cap", "dtls12_capped_deadline_reached", "dtls12_capped_timer_superseded"],
    ap_definitions={
        "dtls12_timer_rearmed_60000ms_cap":"OpenSSL clamps and actually arms the next DTLS timer generation at its 60-second profile cap.",
        "dtls12_capped_deadline_reached":"That exact capped generation reaches its absolute deadline.",
        "dtls12_capped_timer_superseded":"Expected/duplicate flight, stop_timer, or explicit restart replaces the generation.",
    },
    positive_trace=tr((0,"dtls12_timer_rearmed_60000ms_cap"),(60000,"dtls12_capped_deadline_reached"),(60001,"")),
    negative_trace=tr((0,"dtls12_timer_rearmed_60000ms_cap"),(59999,"dtls12_capped_deadline_reached"),(60001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"dtls12_timer_rearmed_60000ms_cap"),(60001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Bound to actual 60 s rearm and added duplicate-flight/stop supersession plus missing negative.",
)
revise(TLS, "TLS13-TICKET-01", independent_audit_status="REJECT_OR_FIX",
       independent_audit_note="Rejected: consequent was adapter-derived and self-fulfilling; no fixed cache/use transition proves seven-day non-use.")
revise(DTLS, "DTLS12-FINAL-01", independent_audit_status="REJECT_OR_FIX",
       independent_audit_note="Rejected: same-position retransmission invented a zero-delay requirement and source did not prove 240 s state retention.")

revise(
    SSH, "SSH-REKEY-01",
    title="One-hour KEXINIT initiation proxy under a controlled OpenSSH profile",
    natural_language="显式配置一小时 rekey_interval，认证完成、当前不在 KEX、peer 允许 rekey 且已有可发送 packet 时，本地应在一小时内发起 KEXINIT 或连接已关闭。",
    normative_strength="CONTROLLED_PROXY_FOR_RFC_RECOMMENDATION",
    atomic_propositions=["ssh_rekey_eligible_one_hour_profile", "ssh_local_kexinit_started", "ssh_connection_closed"],
    ap_definitions={
        "ssh_rekey_eligible_one_hour_profile":"Authenticated OpenSSH connection has rekey_interval=3600, is not already in KEX, peer permits rekey, and a packet-processing opportunity exists.",
        "ssh_local_kexinit_started":"The local endpoint actually begins KEXINIT for the next key exchange.",
        "ssh_connection_closed":"The correlated SSH transport closes before the local initiation deadline.",
    },
    mightyppl_formula="G* (ssh_rekey_eligible_one_hour_profile -> F [0,3600000] (ssh_local_kexinit_started || ssh_connection_closed))",
    positive_trace=tr((0,"ssh_rekey_eligible_one_hour_profile"),(3600000,"ssh_local_kexinit_started"),(3600001,"")),
    negative_trace=tr((0,"ssh_rekey_eligible_one_hour_profile"),(3600001,"")),
    oracle_value="MEDIUM", confidence="MEDIUM",
    limitations="This is a controllable local-initiation proxy, not proof that new keys were installed; peer stall/completion is classified separately and no RFC-equivalence claim is made.",
    independent_audit_status="APPROVE_WITH_CAVEAT",
    independent_audit_note="Retitled and weakened to a local KEXINIT proxy with all OpenSSH branch preconditions; not presented as completed key change.",
)
revise(
    DICOM, "DICOM-ARTIM-01",
    natural_language="DCMTK storescp 30 秒 acceptor profile 中，接受 TCP 后 ARTIM 不得提前 expiry；须在 30000 ms expiry，或此前收到 A-ASSOCIATE-RQ、连接关闭/解析终止。",
    mightyppl_formula="G* (dicom_tcp_connection_accepted_dcmtk_30s_profile -> (G [0,30000) (!dicom_artim_expired) && F [0,30000] (dicom_artim_expired || dicom_associate_rq_received || dicom_transport_closed_or_parse_abort)))",
    atomic_propositions=["dicom_tcp_connection_accepted_dcmtk_30s_profile", "dicom_artim_expired", "dicom_associate_rq_received", "dicom_transport_closed_or_parse_abort"],
    ap_definitions={
        "dicom_tcp_connection_accepted_dcmtk_30s_profile":"storescp acceptor passes opt_acse_timeout=30 and DUL receives the TCP transport connection.",
        "dicom_artim_expired":"PRV_NextPDUType returns DUL_READTIMEOUT and dispatches ARTIM_TIMER_EXPIRED.",
        "dicom_associate_rq_received":"A valid A-ASSOCIATE-RQ PDU is recognized for this association.",
        "dicom_transport_closed_or_parse_abort":"Peer transport close or terminal malformed-PDU/abort branch ends this waiting generation.",
    },
    positive_trace=tr((0,"dicom_tcp_connection_accepted_dcmtk_30s_profile"),(30000,"dicom_artim_expired"),(30001,"")),
    negative_trace=tr((0,"dicom_tcp_connection_accepted_dcmtk_30s_profile"),(29999,"dicom_artim_expired"),(30001,"")),
    additional_negative_traces={"negative_late_or_missing":tr((0,"dicom_tcp_connection_accepted_dcmtk_30s_profile"),(30001,""))},
    independent_audit_status="FIXED_AFTER_AUDIT",
    independent_audit_note="Added early close/parse-abort outcomes and corrected the 30 s acceptor profile to storescp, not DcmSCU.",
    profile_source_url=gh("DCMTK/dcmtk",DCMTK_COMMIT,"dcmnet/apps/storescp.cc","165-175"),
    profile_use_source_url=gh("DCMTK/dcmtk",DCMTK_COMMIT,"dcmnet/apps/storescp.cc","928-940"),
)

# Two additional no-early safety cards were extracted after the first audit.
# They are retained as root-reviewed, fixed-profile candidates; neither claims
# a universal live-PTO constant.
for _pid in ("QUIC-PC-01", "QUIC-KU-01"):
    revise(QUIC, _pid, independent_audit_status="ROOT_REVIEWED_PROFILE",
           independent_audit_note="Root review confirmed a no-early safety obligation under the explicitly frozen 1024 ms application-PTO profile; reinstantiate if live PTO differs.")


# AP-to-source mappings are applied after all audit revisions so the mapping
# always follows the final admitted alphabet, not the pre-audit draft APs.
SOURCE_AP_MAPPINGS: dict[str, dict[str, object]] = {
    "TCP-RTO-01": {
        "primary": ["tcp_initial_rto_armed_1000ms_profile"],
        "auxiliary": [
            source_mapping(
                role="initial RTO timer arm after active-open send",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_output.c", symbol="tcp_connect", lines="4393-4398",
                atomic_propositions=["tcp_initial_rto_armed_1000ms_profile"],
            ),
            source_mapping(
                role="retransmission timer deadline dispatch",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_timer.c", symbol="tcp_write_timer_handler", lines="695-728",
                atomic_propositions=["tcp_initial_rto_deadline_reached"],
            ),
            source_mapping(
                role="ACK-driven retransmission timer cancellation or replacement",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_input.c", symbol="tcp_rearm_rto", lines="3524-3550",
                atomic_propositions=["tcp_initial_rto_superseded"],
            ),
        ],
    },
    "TCP-RTO-03": {
        "primary": ["tcp_second_rto_armed_2000ms_normal_backoff"],
        "auxiliary": [
            source_mapping(
                role="retransmission timer deadline dispatch",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_timer.c", symbol="tcp_write_timer_handler", lines="695-728",
                atomic_propositions=["tcp_second_rto_deadline_reached"],
            ),
            source_mapping(
                role="ACK-driven retransmission timer cancellation or replacement",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_input.c", symbol="tcp_rearm_rto", lines="3524-3550",
                atomic_propositions=["tcp_second_rto_superseded"],
            ),
        ],
    },
    "TCP-ACK-01": {
        "primary": ["tcp_delayed_ack_obligation_started"],
        "auxiliary": [
            source_mapping(
                role="pure ACK construction and transmission handoff",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_output.c", symbol="__tcp_send_ack", lines="4466-4506",
                atomic_propositions=["tcp_ack_sent"],
            ),
        ],
    },
    "TCP-ZWP-01": {
        "primary": ["tcp_probe0_timer_armed_1000ms"],
        "auxiliary": [
            source_mapping(
                role="PROBE0 deadline dispatch and attempt entry",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_timer.c", symbol="tcp_write_timer_handler", lines="695-728",
                atomic_propositions=["tcp_probe0_deadline_or_attempt"],
            ),
            source_mapping(
                role="window-open clear or probe-timer rearm",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_input.c", symbol="tcp_ack_probe", lines="3807-3828",
                atomic_propositions=["tcp_probe0_superseded"],
            ),
        ],
    },
    "TCP-ZWP-02": {
        "primary": [
            "tcp_probe0_backoff_armed_2000ms",
            "tcp_probe0_second_deadline_or_attempt",
            "tcp_probe0_second_superseded",
        ],
        "auxiliary": [],
    },
    "TCP-KA-01": {
        "primary": ["tcp_default_keepalive_enabled_on_idle_connection"],
        "auxiliary": [
            source_mapping(
                role="SO_KEEPALIVE enable and default timer arm",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_timer.c", symbol="tcp_set_keepalive", lines="768-777",
                atomic_propositions=["tcp_default_keepalive_enabled_on_idle_connection"],
            ),
            source_mapping(
                role="keep-alive expiry and probe send attempt",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_timer.c", symbol="tcp_keepalive_timer", lines="779-866",
                atomic_propositions=["tcp_keepalive_probe_sent"],
            ),
        ],
    },
    "TCP-TW-01": {
        "primary": ["tcp_time_wait_entered_linux_profile"],
        "auxiliary": [
            source_mapping(
                role="TIME-WAIT bucket creation and scheduling",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_minisocks.c", symbol="tcp_time_wait", lines="326-394",
                atomic_propositions=["tcp_time_wait_entered_linux_profile"],
            ),
            source_mapping(
                role="ordinary TIME-WAIT expiry destruction",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/inet_timewait_sock.c", symbol="tw_timer_handler", lines="161-166",
                atomic_propositions=["tcp_time_wait_state_destroyed"],
            ),
            source_mapping(
                role="guarded direct reopen and exceptional early removal classification",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_minisocks.c", symbol="tcp_timewait_state_process", lines="186-261",
                atomic_propositions=["tcp_valid_timewait_reopen_or_admin_cleanup"],
            ),
        ],
        "standard_supporting_references": [
            {"role": "RFC MSL provenance retained from the pre-audit card",
             "url": "https://www.rfc-editor.org/rfc/rfc9293.html#section-3.4.2"},
        ],
    },
    "TCP-R2-01": {
        "primary": ["tcp_closed_by_data_r2_expiry"],
        "auxiliary": [
            source_mapping(
                role="first attempted data retransmission timestamp",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_output.c", symbol="tcp_retransmit_skb", lines="3695-3717",
                atomic_propositions=["tcp_data_r2_episode_started"],
            ),
        ],
    },
    "TCP-SYN-01": {
        "primary": ["tcp_open_failed_by_syn_r2_expiry"],
        "auxiliary": [
            source_mapping(
                role="initial active-open SYN transmission and retransmission timer arm",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="net/ipv4/tcp_output.c", symbol="tcp_connect", lines="4360-4398",
                atomic_propositions=["tcp_active_open_syn_r2_started"],
            ),
            source_mapping(
                role="locked Linux SYN retry-policy deviation evidence",
                repository="torvalds/linux", commit=LINUX_COMMIT,
                path="include/net/tcp.h", symbol="TCP_SYN_RETRIES", lines="124-131",
                atomic_propositions=["tcp_active_open_syn_r2_started", "tcp_open_failed_by_syn_r2_expiry"],
                url=gh("torvalds/linux", LINUX_COMMIT, "include/net/tcp.h", "124-131"),
            ),
        ],
    },
    "QUIC-ACK-01": {
        "primary": ["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"],
        "auxiliary": [
            source_mapping(
                role="default max_ack_delay profile constant",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/includes/ngtcp2/ngtcp2.h", symbol="NGTCP2_DEFAULT_MAX_ACK_DELAY", lines="1278-1285",
                atomic_propositions=["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"],
                url=gh("ngtcp2/ngtcp2", NGTCP2_COMMIT, "lib/includes/ngtcp2/ngtcp2.h", "1278-1285"),
            ),
            source_mapping(
                role="commit fully processed ack-eliciting packet number",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="pktns_commit_recv_pkt_num", lines="6293-6337",
                atomic_propositions=["quic_1rtt_ack_eliciting_packet_processed_default_ack_delay"],
            ),
            source_mapping(
                role="ACK frame range construction for outgoing packet",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_acktr.c", symbol="ngtcp2_acktr_create_ack_frame", lines="340-426",
                atomic_propositions=["quic_ack_covering_packet_sent"],
            ),
        ],
    },
    "QUIC-PTO-01": {
        "primary": ["quic_pto_armed_999ms_initial_profile"],
        "auxiliary": [
            source_mapping(
                role="default initial RTT profile constant",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/includes/ngtcp2/ngtcp2.h", symbol="NGTCP2_DEFAULT_INITIAL_RTT", lines="434-439",
                atomic_propositions=["quic_pto_armed_999ms_initial_profile"],
                url=gh("ngtcp2/ngtcp2", NGTCP2_COMMIT, "lib/includes/ngtcp2/ngtcp2.h", "434-439"),
            ),
            source_mapping(
                role="PTO selection, arm, cancellation, and replacement",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="ngtcp2_conn_set_loss_detection_timer", lines="13427-13469",
                atomic_propositions=["quic_pto_armed_999ms_initial_profile", "quic_pto_generation_superseded"],
            ),
            source_mapping(
                role="loss-detection deadline dispatch",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="ngtcp2_conn_on_loss_detection_timer", lines="13478-13546",
                atomic_propositions=["quic_pto_deadline_reached"],
            ),
        ],
    },
    "QUIC-PTO-02": {
        "primary": ["quic_pto_backoff_armed_1998ms"],
        "auxiliary": [
            source_mapping(
                role="PTO deadline, pto_count increment, and backoff rearm",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="ngtcp2_conn_on_loss_detection_timer", lines="13478-13546",
                atomic_propositions=["quic_pto_backoff_armed_1998ms", "quic_second_pto_deadline_reached"],
            ),
            source_mapping(
                role="backoff timer replacement or cancellation",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="ngtcp2_conn_set_loss_detection_timer", lines="13427-13469",
                atomic_propositions=["quic_second_pto_superseded"],
            ),
        ],
    },
    "QUIC-IDLE-01": {
        "primary": ["quic_connection_became_idle_ngtcp2_30s_profile"],
        "auxiliary": [
            source_mapping(
                role="example server installs configured idle timeout transport parameter",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="examples/server.cc", symbol="Handler::init", lines="817-827",
                atomic_propositions=["quic_connection_became_idle_ngtcp2_30s_profile"],
                legacy_exact_url=gh("ngtcp2/ngtcp2", NGTCP2_COMMIT, "examples/server_base.h", "70-80"),
            ),
            source_mapping(
                role="read activity starts a new idle generation",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_restart_timer_on_read", lines="2163-2166",
                atomic_propositions=["quic_connection_became_idle_ngtcp2_30s_profile"],
            ),
            source_mapping(
                role="write activity starts a new idle generation",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_restart_timer_on_write", lines="2158-2161",
                atomic_propositions=["quic_connection_became_idle_ngtcp2_30s_profile"],
            ),
            source_mapping(
                role="connection-state disposal hook",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="ngtcp2_conn_del", lines="1740-1845",
                atomic_propositions=["quic_connection_state_discarded"],
            ),
            source_mapping(
                role="peer CONNECTION_CLOSE transition to draining",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_recv_connection_close", lines="6054-6084",
                atomic_propositions=["quic_explicit_close_or_terminal_received"],
            ),
            source_mapping(
                role="validated stateless reset transition to draining",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_on_stateless_reset", lines="8046-8074",
                atomic_propositions=["quic_explicit_close_or_terminal_received"],
            ),
            source_mapping(
                role="local CONNECTION_CLOSE transition to closing",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="ngtcp2_conn_write_connection_close_pkt", lines="12688-12749",
                atomic_propositions=["quic_explicit_close_or_terminal_received"],
            ),
        ],
    },
    "QUIC-PV-01": {
        "primary": ["quic_path_validation_armed_2997ms_profile"],
        "auxiliary": [
            source_mapping(
                role="path-validation object creation with timeout",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_pv.c", symbol="ngtcp2_pv_new", lines="46-68",
                atomic_propositions=["quic_path_validation_armed_2997ms_profile"],
            ),
            source_mapping(
                role="matching PATH_RESPONSE validation success",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_recv_path_response", lines="6161-6268",
                atomic_propositions=["quic_path_validated"],
            ),
            source_mapping(
                role="path-validation timeout abandonment",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_write_path_challenge", lines="5203-5232",
                atomic_propositions=["quic_path_abandoned_by_timeout"],
            ),
            source_mapping(
                role="migration/application replacement abort",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_abort_pv", lines="5117-5132",
                atomic_propositions=["quic_path_validation_superseded"],
            ),
        ],
    },
    "QUIC-PC-01": {
        "primary": ["quic_app_loss_run_started_initial_profile"],
        "auxiliary": [
            source_mapping(
                role="persistent-congestion threshold constant",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_cc.h", symbol="NGTCP2_PERSISTENT_CONGESTION_THRESHOLD", lines="34-38",
                atomic_propositions=["quic_app_loss_run_started_initial_profile", "quic_persistent_congestion_declared"],
                url=gh("ngtcp2/ngtcp2", NGTCP2_COMMIT, "lib/ngtcp2_cc.h", "34-38"),
            ),
            source_mapping(
                role="persistent-congestion decision and callback",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_rtb.c", symbol="rtb_detect_lost_pkt", lines="1162-1185",
                atomic_propositions=["quic_persistent_congestion_declared"],
                url=gh("ngtcp2/ngtcp2", NGTCP2_COMMIT, "lib/ngtcp2_rtb.c", "1162-1185"),
            ),
            source_mapping(
                role="default initial RTT input to fixed profile",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/includes/ngtcp2/ngtcp2.h", symbol="NGTCP2_DEFAULT_INITIAL_RTT", lines="434-439",
                atomic_propositions=["quic_app_loss_run_started_initial_profile"],
            ),
            source_mapping(
                role="default max_ack_delay input to fixed profile",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/includes/ngtcp2/ngtcp2.h", symbol="NGTCP2_DEFAULT_MAX_ACK_DELAY", lines="1278-1285",
                atomic_propositions=["quic_app_loss_run_started_initial_profile"],
            ),
        ],
    },
    "QUIC-KU-01": {
        "primary": ["quic_local_next_key_update_started"],
        "auxiliary": [
            source_mapping(
                role="previous key-update ACK confirmation timestamp",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/ngtcp2_conn.c", symbol="conn_handle_unconfirmed_key_update_from_remote", lines="3455-3474",
                atomic_propositions=["quic_previous_key_update_confirmed_initial_profile"],
                url=gh("ngtcp2/ngtcp2", NGTCP2_COMMIT, "lib/ngtcp2_conn.c", "3455-3474"),
            ),
            source_mapping(
                role="default initial RTT input to key-update spacing profile",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/includes/ngtcp2/ngtcp2.h", symbol="NGTCP2_DEFAULT_INITIAL_RTT", lines="434-439",
                atomic_propositions=["quic_previous_key_update_confirmed_initial_profile"],
            ),
            source_mapping(
                role="default max_ack_delay input to key-update spacing profile",
                repository="ngtcp2/ngtcp2", commit=NGTCP2_COMMIT,
                path="lib/includes/ngtcp2/ngtcp2.h", symbol="NGTCP2_DEFAULT_MAX_ACK_DELAY", lines="1278-1285",
                atomic_propositions=["quic_previous_key_update_confirmed_initial_profile"],
            ),
        ],
    },
}


def _nested_urls(value: object) -> set[str]:
    if isinstance(value, str):
        return {value} if value.startswith(("http://", "https://")) else set()
    if isinstance(value, dict):
        return {url for item in value.values() for url in _nested_urls(item)}
    if isinstance(value, list):
        return {url for item in value for url in _nested_urls(item)}
    return set()


def apply_source_mappings(cards: list[dict[str, object]]) -> None:
    """Install final AP mappings and fail if a legacy URL is silently lost."""
    for card in cards:
        pid = str(card["id"])
        patch = SOURCE_AP_MAPPINGS[pid]
        legacy_keys = [
            key for key in card
            if key != "source_url"
            and (key.endswith("_source_url") or key.endswith("_source_urls")
                 or key == "implementation_deviation_evidence_url")
        ]
        legacy_urls = {
            url for key in legacy_keys for url in _nested_urls(card[key])
        }
        structured_urls = _nested_urls(patch)
        missing = sorted(legacy_urls - structured_urls)
        if missing:
            raise ValueError(f"{pid}: legacy source URLs not migrated: {missing}")

        card["primary_source_atomic_propositions"] = patch["primary"]
        card["auxiliary_source_mappings"] = patch["auxiliary"]
        if patch.get("standard_supporting_references"):
            card["standard_supporting_references"] = patch["standard_supporting_references"]
        card["source_mapping_status"] = "COMPLETE_FOR_ADMITTED_CANDIDATE"
        for key in legacy_keys:
            del card[key]


apply_source_mappings(TCP)
apply_source_mappings(QUIC)


EXCLUDED = {
    "tcp": """# TCP excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Live RTT-derived RTO formula for arbitrary connections | `FORMULA_UNSUPPORTED` | The bound is data-dependent (`SRTT + max(G,4*RTTVAR)`) and current MightyPPL intervals are integer constants. |
| RTO maximum must be at least 60 s | `TRACE_NOT_DECISIVE` | RFC 6298 constrains an implementation cap; it is a configuration/value invariant, not by itself a timed-event obligation. |
| One failed keep-alive probe must not kill the connection | `NO_NUMERIC_BOUND` | Normative and useful, but the prohibition has no time interval and duplicates a pure state/action oracle. |
| ACK at least every second full-sized segment | `FORMULA_UNSUPPORTED` | This is a packet-count obligation rather than a time-bound obligation. |
| SYN fallback RTO of 3 seconds | `DUPLICATE_OBLIGATION` | RFC 6298 resets to 3 s after SYN/SYN-ACK loss; it is the same RTO scheduling obligation under another explicitly detectable branch. |
| RTO expiry immediately retransmits earliest unacknowledged segment | `TRACE_NOT_DECISIVE` | The same-microstep `G* (fire -> retransmit)` negative trace is INCONCLUSIVE under current finite semantics; `F[0,1)` would invent a non-normative adapter bound. |
| R1 is at least three retransmissions | `FORMULA_UNSUPPORTED` | RFC 9293 defines a count threshold, not an elapsed-time interval. |
| TCP User Timeout Option lower/upper negotiation | `NO_FIXED_SOURCE_MAP` | RFC 5482 has numeric guidance, but the locked Linux source does not provide a directly corresponding on-wire UTO option implementation hook for this catalog. |
| Quiet time of one MSL after loss of sequence-number memory | `NO_FIXED_SOURCE_MAP` | RFC 9293 gives MSL=2 minutes, but no stable Linux TCP hook exposes the rare host-recovery condition and its retained sequence-memory premise. |
| Sender SWS override timeout of 0.1-1.0 seconds | `NO_FIXED_SOURCE_MAP` | RFC 9293 gives a recommended range, but the locked Linux code does not expose a single corresponding timer event separable from zero-window/resource probes. |
| Legacy OPEN-call global user timeout of five minutes | `VERSION_MISMATCH` | RFC 9293 preserves RFC 793 API text, while Linux defaults to stack R2 behavior unless TCP_USER_TIMEOUT is explicitly set. |
""",
    "quic": """# QUIC excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Immediate ACK for Initial/Handshake packets | `PUNCTUAL_ONLY` | RFC 9000 says immediately but provides no numeric non-zero interval; a same-callback Boolean oracle can be kept outside the timed main catalog. |
| Closing/draining state persists for 3*PTO | `NO_FIXED_SOURCE_MAP` | RFC 9000 gives the duration, but ngtcp2 exposes closing/draining state while application code owns final state disposal; no single fixed library hook proves the full retention lifecycle. |
| Generic max_idle_timeout | `NO_NUMERIC_BOUND` | RFC default is zero/disabled. Only the ngtcp2 example's documented 30 s profile is proposed. |
| Application-data PTO before handshake confirmation must not be armed | `NO_NUMERIC_BOUND` | Strong state prohibition, but it has no numeric interval and is better a Boolean protocol-state oracle. |
| ACK every N packets | `FORMULA_UNSUPPORTED` | ACK frequency/count rules are not time bounds and need counters rather than current MITL AP timing. |
| PTO expiry immediately schedules an ack-eliciting probe | `TRACE_NOT_DECISIVE` | The same-callback action has no numeric interval; its missing-consequent trace is INCONCLUSIVE under current finite `G*`, and adding 1 ms would be artificial. |
| Old read-key discard within 3*PTO | `NO_FIXED_SOURCE_MAP` | RFC 9001 gives a dynamic upper bound, but the locked implementation lazily replaces/deletes key material as update state advances; a single fixed expiry event is not exposed. |
""",
    "tls": """# TLS excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| KeyUpdate response before next application data | `NO_NUMERIC_BOUND` | RFC 8446 orders messages but provides no numeric deadline. |
| PSK ticket-age freshness tolerance | `NO_NUMERIC_BOUND` | The acceptance tolerance is implementation-defined. |
| TLS handshake timeout | `NO_PUBLIC_NORMATIVE_TEXT` | RFC 8446 defines no general numeric handshake timeout. |
| close_notify timing | `NO_NUMERIC_BOUND` | The alert ordering requirement has no numeric interval. |
| Record/key usage limits | `FORMULA_UNSUPPORTED` | Limits are record/byte counters, not elapsed-time obligations. |
| Server ticket_lifetime field <= 604800 | `TRACE_NOT_DECISIVE` | This is a message-field invariant; the timed catalog instead monitors client usability/cache lifetime. |
| Client ticket usability/cache lifetime | `INDEPENDENT_AUDIT_REJECT` | The first extraction used an adapter-derived `became_unusable` event, making the consequent self-fulfilling; the locked source has no fixed cache/use transition that proves expiry at seven days. |
""",
    "dtls": """# DTLS excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| RFC 9147 DTLS 1.3 ACK delay <= RTO/4 | `VERSION_MISMATCH` | ProFuzzBench TinyDTLS and OpenSSL 0437435a implement DTLS 1.2, not DTLS 1.3. |
| RFC 9147 DTLS 1.3 ACK/retransmission state machine | `VERSION_MISMATCH` | No selected mature benchmark implementation at the locked revision implements the RFC 9147 state machine. |
| TinyDTLS initial 1-second timer mapping | `VERSION_MISMATCH` | `assist-project/tinydtls-fuzz@06995d4...` sets `n->timeout = 2 * DTLS_TICKS_PER_SECOND`, while RFC 6347 recommends 1 second. It is retained as a differential test target, not source evidence for the 1-second oracle. |
| Duplicate peer flight causes immediate retransmission | `PUNCTUAL_ONLY` | RFC 6347 says transition/retransmit on receipt but has no positive numeric bound. |
| Complete expected flight cancels timer | `NO_NUMERIC_BOUND` | Normative state-machine behavior but no numeric interval; it is already used as a discharge event in bounded timer properties. |
| Reset timer after long idle >=10*current timer | `NO_NUMERIC_BOUND` | The timer is dynamic and the action is optional (`may`), so a fixed main-catalog verdict would overclaim. |
| Separate 4/8/16/32-second backoff entries | `DUPLICATE_OBLIGATION` | They mechanically repeat the same doubling requirement represented by DTLS12-RTX-03. |
| Timer expiry immediately retransmits buffered flight | `TRACE_NOT_DECISIVE` | The action is same-microstep and has no normative positive delay; current finite `G*` does not produce a NEGATIVE trace without an invented interval. |
| Final-flight retransmission and 240-second retention | `INDEPENDENT_AUDIT_REJECT` | The candidate invented a same-position retransmission obligation, while the selected source hook did not prove that final-flight state remains retained for the claimed 240 seconds. |
""",
    "ssh": """# SSH excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Rekey after 1 GB | `FORMULA_UNSUPPORTED` | RFC 4253's alternative threshold is byte-count based, not elapsed time. |
| Key-exchange completion timeout | `NO_NUMERIC_BOUND` | RFC 4253 does not assign a numeric KEX completion deadline. |
| ServerAliveInterval/ClientAliveInterval | `NO_PUBLIC_NORMATIVE_TEXT` | These are OpenSSH implementation options, not SSH transport protocol constants. |
| Identification-string exchange timeout | `NO_NUMERIC_BOUND` | RFC 4253 specifies order/format but not a numeric timeout. |
| Authentication timeout | `NO_PUBLIC_NORMATIVE_TEXT` | LoginGraceTime is an OpenSSH server policy, not a transport-layer RFC 4253 timer. |
""",
    "dicom": """# DICOM excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Protocol-wide numeric ARTIM value | `NO_NUMERIC_BOUND` | DICOM PS3.8 Section 9.1.5 requires ARTIM to be configurable and intentionally gives no universal number. |
| Use ARTIM to bound association establishment/release | `NO_PUBLIC_NORMATIVE_TEXT` | PS3.8 explicitly says ARTIM should not oversee Association Establishment or Release at the application layer. |
| DIMSE response timeout | `NO_NUMERIC_BOUND` | PS3.8 upper-layer state machine provides no universal DIMSE response deadline; DCMTK's DIMSE timeout is configurable/unlimited by default. |
| A-RELEASE-RP / A-ABORT post-send exact timeout | `NO_FIXED_SOURCE_MAP` | DCMTK's path uses `PRV_DEFAULTTIMEOUT=-1` in relevant reads; no stable numeric default matches a main MITL property. |
| End-of-study timeout | `NO_PUBLIC_NORMATIVE_TEXT` | DCMTK application behavior, not a DICOM Upper Layer normative timer. |
""",
}


EVIDENCE = {
    "tcp": {
        "protocol":"TCP", "access_date":ACCESS_DATE, "status":"COMPLETE_WITH_INDEPENDENT_AUDIT",
        "standards":[
            {"id":"RFC6298","title":"Computing TCP's Retransmission Timer","url":"https://www.rfc-editor.org/rfc/rfc6298.html","sections":["2.1","5"],"source_type":"IETF Standards Track"},
            {"id":"RFC9293","title":"Transmission Control Protocol","url":"https://www.rfc-editor.org/rfc/rfc9293.html","sections":["3.6.1","3.8.3","3.8.4","3.8.6.1","3.8.6.3"],"source_type":"IETF Internet Standard"},
        ],
        "sources":[{"repository":"torvalds/linux","commit":LINUX_COMMIT,"url":f"https://github.com/torvalds/linux/tree/{LINUX_COMMIT}","role":"fixed implementation source"}],
        "method":"Exhaustive keyword/section screening plus independent standard/formula/source audit of RTO, retransmission, delayed ACK, zero-window, keep-alive and TIME-WAIT timers; rejected cards remain in the exclusion ledger.",
        "independent_audit":"analysis/protocol_fuzzing_study/_audit/transport_security_audit.md",
    },
    "quic": {
        "protocol":"QUIC", "access_date":ACCESS_DATE, "status":"COMPLETE_WITH_INDEPENDENT_AUDIT_AND_ROOT_PROFILE_REVIEW",
        "standards":[
            {"id":"RFC9000","title":"QUIC: A UDP-Based Multiplexed and Secure Transport","url":"https://www.rfc-editor.org/rfc/rfc9000.html","sections":["8.2.4","10.1","13.2.1","18.2"],"source_type":"IETF Standards Track"},
            {"id":"RFC9002","title":"QUIC Loss Detection and Congestion Control","url":"https://www.rfc-editor.org/rfc/rfc9002.html","sections":["6.2.1","6.2.2","6.2.4"],"source_type":"IETF Standards Track"},
            {"id":"RFC9001","title":"Using TLS to Secure QUIC","url":"https://www.rfc-editor.org/rfc/rfc9001.html","sections":["6.5"],"source_type":"IETF Standards Track"},
        ],
        "sources":[{"repository":"ngtcp2/ngtcp2","commit":NGTCP2_COMMIT,"url":f"https://github.com/ngtcp2/ngtcp2/tree/{NGTCP2_COMMIT}","role":"mature QUIC v1 implementation and example profile"}],
        "method":"Screened ACK delay, PTO/backoff, persistent congestion, path validation, idle, closing/draining and key-update timers; independently audited the initial set and root-reviewed two later fixed-profile no-early cards.",
        "independent_audit":"analysis/protocol_fuzzing_study/_audit/transport_security_audit.md",
    },
    "tls": {
        "protocol":"TLS", "access_date":ACCESS_DATE, "status":"SCREENED_NO_ADMITTED_MITL_AFTER_INDEPENDENT_AUDIT",
        "standards":[{"id":"RFC8446","title":"The Transport Layer Security (TLS) Protocol Version 1.3","url":"https://www.rfc-editor.org/rfc/rfc8446.html","sections":["4.6.1"],"source_type":"IETF Standards Track"}],
        "sources":[
            {"repository":"openssl/openssl","commit":OPENSSL_COMMIT,"url":f"https://github.com/openssl/openssl/tree/{OPENSSL_COMMIT}","role":"ProFuzzBench-pinned TLS implementation"},
            {"repository":"ProFuzzBench/ProFuzzBench","commit":PROFUZZ_COMMIT,"url":gh("ProFuzzBench/ProFuzzBench",PROFUZZ_COMMIT,"subjects/TLS/OpenSSL/Dockerfile","73-88"),"role":"benchmark pin evidence"},
        ],
        "method":"Screened handshake, KeyUpdate, tickets/PSK, close and record limits. The only numeric-time candidate was rejected because its adapter-derived expiry AP was self-fulfilling and no fixed source transition proved the lifetime oracle.",
        "independent_audit":"analysis/protocol_fuzzing_study/_audit/transport_security_audit.md",
    },
    "dtls": {
        "protocol":"DTLS", "access_date":ACCESS_DATE, "status":"COMPLETE_WITH_INDEPENDENT_AUDIT_EXCLUSION",
        "standards":[
            {"id":"RFC6347","title":"Datagram Transport Layer Security Version 1.2","url":"https://www.rfc-editor.org/rfc/rfc6347.html","sections":["4.2.4","4.2.4.1"],"source_type":"IETF Standards Track"},
            {"id":"RFC9147","title":"The Datagram Transport Layer Security (DTLS) Protocol Version 1.3","url":"https://www.rfc-editor.org/rfc/rfc9147.html","sections":["5.8"],"source_type":"IETF Standards Track; excluded for implementation-version mismatch"},
        ],
        "sources":[
            {"repository":"openssl/openssl","commit":OPENSSL_COMMIT,"url":f"https://github.com/openssl/openssl/tree/{OPENSSL_COMMIT}","role":"DTLS 1.2 conforming timer source"},
            {"repository":"assist-project/tinydtls-fuzz","commit":TINYDTLS_COMMIT,"url":f"https://github.com/assist-project/tinydtls-fuzz/tree/{TINYDTLS_COMMIT}","role":"ProFuzzBench SUT; 2-second initial-timer divergence"},
            {"repository":"ProFuzzBench/ProFuzzBench","commit":PROFUZZ_COMMIT,"url":gh("ProFuzzBench/ProFuzzBench",PROFUZZ_COMMIT,"subjects/DTLS/TinyDTLS/Dockerfile","71-87"),"role":"benchmark pin evidence"},
        ],
        "version_caveat":"RFC 9147 properties are excluded because neither locked benchmark TinyDTLS nor OpenSSL 0437435a implements DTLS 1.3.",
        "method":"Screened and independently audited flight retransmission arm/backoff/cap, duplicate-flight response and final-flight retention; the unsupported final-flight retention card was rejected and duplicate constant steps removed.",
        "independent_audit":"analysis/protocol_fuzzing_study/_audit/transport_security_audit.md",
    },
    "ssh": {
        "protocol":"SSH", "access_date":ACCESS_DATE, "status":"COMPLETE_WITH_INDEPENDENT_AUDIT_CAVEAT",
        "standards":[{"id":"RFC4253","title":"The Secure Shell (SSH) Transport Layer Protocol","url":"https://www.rfc-editor.org/rfc/rfc4253.html","sections":["9"],"source_type":"IETF Standards Track"}],
        "sources":[
            {"repository":"vegard/openssh-portable","commit":OPENSSH_COMMIT,"url":f"https://github.com/vegard/openssh-portable/tree/{OPENSSH_COMMIT}","role":"ProFuzzBench-pinned OpenSSH implementation"},
            {"repository":"ProFuzzBench/ProFuzzBench","commit":PROFUZZ_COMMIT,"url":gh("ProFuzzBench/ProFuzzBench",PROFUZZ_COMMIT,"subjects/SSH/OpenSSH/Dockerfile","89-111"),"role":"benchmark pin evidence"},
        ],
        "profile_caveat":"RFC 4253 recommends one hour, but the pinned OpenSSH default rekey_interval is zero. The experiment must explicitly configure the one-hour profile.",
        "method":"Screened transport KEX/rekey, identification, liveness and authentication timers; independent audit retained only a controlled local-KEXINIT proxy for the one-hour recommendation.",
        "independent_audit":"analysis/protocol_fuzzing_study/_audit/transport_security_audit.md",
    },
    "dicom": {
        "protocol":"DICOM", "access_date":ACCESS_DATE, "status":"COMPLETE_WITH_INDEPENDENT_AUDIT_PROFILE_CAVEAT",
        "standards":[{"id":"DICOM-PS3.8-2026c","title":"Network Communication Support for Message Exchange","url":"https://dicom.nema.org/medical/dicom/current/output/chtml/part08/chapter_9.html","sections":["9.1.5","9.2.2"],"source_type":"NEMA DICOM formal standard"}],
        "sources":[
            {"repository":"DCMTK/dcmtk","commit":DCMTK_COMMIT,"url":f"https://github.com/DCMTK/dcmtk/tree/{DCMTK_COMMIT}","role":"ProFuzzBench-pinned DICOM implementation/profile"},
            {"repository":"ProFuzzBench/ProFuzzBench","commit":PROFUZZ_COMMIT,"url":gh("ProFuzzBench/ProFuzzBench",PROFUZZ_COMMIT,"subjects/DICOM/Dcmtk/Dockerfile","75-88"),"role":"benchmark pin evidence"},
        ],
        "profile_caveat":"DICOM mandates a configurable ARTIM timer but no numeric value; 30 seconds is the locked DCMTK profile only.",
        "method":"Screened all ARTIM start/stop/expiry actions and DCMTK ACSE/DIMSE defaults; independent audit corrected the role to storescp acceptor and retained only its locked 30-second profile.",
        "independent_audit":"analysis/protocol_fuzzing_study/_audit/transport_security_audit.md",
    },
}

# The staging evidence records what the builder guarantees.  The root
# publication pass independently re-fetches every file and re-runs symbol-span
# verification; this note does not substitute for that check.
for _slug, _cards in (("tcp", TCP), ("quic", QUIC)):
    EVIDENCE[_slug]["atomic_proposition_source_mapping"] = {
        "schema": "primary_source_atomic_propositions + auxiliary_source_mappings[]",
        "status": "COMPLETE_FOR_ALL_ADMITTED_CANDIDATES",
        "property_count": len(_cards),
        "atomic_proposition_count": sum(len(card["atomic_propositions"]) for card in _cards),
        "policy": "Every declared AP has at least one fixed-commit executable source mapping; dynamic identifiers remain correlation fields.",
        "root_verification": "generate_multi_protocol_catalog.py candidate_gate_errors + verify_source + verify_auxiliary_sources",
    }


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    groups = {"tcp": TCP, "quic": QUIC, "tls": TLS, "dtls": DTLS, "ssh": SSH, "dicom": DICOM}
    for slug, cards in groups.items():
        d = HERE / slug
        write_json(d / "proposals.json", cards)
        write_json(d / "evidence.json", EVIDENCE[slug])
        (d / "excluded.md").write_text(EXCLUDED[slug], encoding="utf-8")
        # The root integration schema calls the final file excluded_properties.md.
        (d / "excluded_properties.md").write_text(EXCLUDED[slug], encoding="utf-8")

    manifest = {
        "generated_at": ACCESS_DATE,
        "counts": {slug: len(cards) for slug, cards in groups.items()},
        "total": sum(map(len, groups.values())),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    write_json(HERE / "generation_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
