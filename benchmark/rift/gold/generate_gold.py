#!/usr/bin/env python3
"""Generate the deterministic 120-case RIFT mechanical gold corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "rift.mechanical-gold.case.v1"
RELATIONS = (
    ["MUST_INFLUENCE"] * 4
    + ["MAY_INFLUENCE"] * 3
    + ["NO_INFLUENCE"] * 3
)
CATEGORIES = [
    "direct_data",
    "indirect_data",
    "control_only",
    "alias_object_field",
    "config_threshold",
    "message_parser_state",
    "async_timer_callback_queue",
    "setup_mode_prerequisite",
    "timing_drop_repeat_reorder",
    "uncontrollable_false_correlation",
    "one_input_multi_ap",
    "joint_inputs",
]
MARKER = re.compile(r"/\* RIFT_(SOURCE|NODE|AP):([a-z][a-z0-9_]*) \*/")


@dataclass(frozen=True)
class TemplateResult:
    code: str
    sources: list[dict[str, str]]
    aps: list[dict[str, str]]
    relations: list[dict[str, Any]]
    derivation: str


def clean(fragment: str) -> str:
    return textwrap.dedent(fragment).strip() + "\n"


def source(identifier: str, kind: str, controllability: str = "EXTERNAL", scope: str = "PROCESS") -> dict[str, Any]:
    return {
        "id": identifier,
        "symbol": identifier,
        "kind": kind,
        "controllability": controllability,
        "fuzzable_frontier": controllability != "INTERNAL",
        "scope": scope,
    }


def ap(identifier: str, expression: str, role: str = "STATE") -> dict[str, str]:
    return {
        "id": identifier,
        "symbol": identifier,
        "expression": expression,
        "role": role,
    }


def recipe(kind: str, direction: str, values: list[str], window: str | None = None) -> dict[str, Any]:
    return {
        "kind": kind,
        "direction": direction,
        "suggested_values": values,
        "relative_time_window": window,
    }


def relation(
    source_id: str,
    ap_id: str,
    influence: str,
    nodes: list[str],
    edge_kinds: list[str],
    *,
    preconditions: list[str] | None = None,
    mutation: dict[str, Any] | None = None,
    joint_group: list[str] | None = None,
    negative_reason: str | None = None,
) -> dict[str, Any]:
    if influence == "NO_INFLUENCE":
        nodes = []
        edge_kinds = []
        mutation = None
        negative_reason = negative_reason or "The template contains no value, control, event, or lifecycle path from this source to the AP."
    certainty = "may" if influence == "MAY_INFLUENCE" else "must"
    edges = [
        {"from": left, "to": right, "kind": kind, "certainty": certainty}
        for left, right, kind in zip(nodes, nodes[1:], edge_kinds)
    ]
    if len(edge_kinds) != max(0, len(nodes) - 1):
        raise ValueError(f"path length mismatch for {source_id}->{ap_id}")
    return {
        "source_id": source_id,
        "ap_id": ap_id,
        "relation": influence,
        "channels": list(dict.fromkeys(edge_kinds)),
        "path": {"nodes": nodes, "edges": edges},
        "preconditions": preconditions or [],
        "mutation_recipe": mutation,
        "joint_group": joint_group or [],
        "negative_reason": negative_reason,
    }


PREAMBLE = clean(
    r"""
    #include <stdint.h>
    #include <stdio.h>
    #include <stdlib.h>

    static int read_arg(int argc, char **argv, int index, int fallback) {
        if (index >= argc) {
            return fallback;
        }
        char *end = NULL;
        long value = strtol(argv[index], &end, 10);
        return (end == argv[index]) ? fallback : (int)value;
    }
    """
)


def direct_data(influence: str, variant: int) -> TemplateResult:
    threshold = 5 + variant
    sources = [source("source_primary", "external_argument")]
    if influence == "MUST_INFLUENCE":
        main = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            /* RIFT_NODE:node_value */
            int node_value = source_primary;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_value > {threshold});
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        relations = [relation("source_primary", "ap_primary", influence, ["source_primary", "node_value", "ap_primary"], ["data", "data"], mutation=recipe("boundary_crossing", "cross comparison threshold", [str(threshold - 1), str(threshold), str(threshold + 1)]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument"))
        main = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 2, 1);
            /* RIFT_NODE:node_value */
            int node_value = {threshold};
            if (source_gate != 0) {{
                node_value = source_primary;
            }}
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_value > {threshold});
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        relations = [
            relation("source_primary", "ap_primary", influence, ["source_primary", "node_value", "ap_primary"], ["data", "data"], preconditions=["source_gate != 0"], mutation=recipe("boundary_crossing", "cross comparison threshold when enabled", [str(threshold - 1), str(threshold + 1)])),
            relation("source_gate", "ap_primary", influence, ["source_gate", "node_value", "ap_primary"], ["control", "data"], mutation=recipe("boolean_toggle", "toggle enabling guard", ["0", "1"])),
        ]
    else:
        main = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            (void)source_primary;
            /* RIFT_NODE:node_value */
            int node_value = {threshold + 1};
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_value > {threshold});
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        relations = [relation("source_primary", "ap_primary", influence, [], [], negative_reason="The external argument is consumed only by a void cast; the AP reads a constant local value.")]
    return TemplateResult(clean(main), sources, [ap("ap_primary", f"node_value > {threshold}")], relations, "A direct assignment template fixes whether the primary external value reaches the AP expression on every path, on a guarded path, or on no path.")


def indirect_data(influence: str, variant: int) -> TemplateResult:
    bias = 2 + variant
    sources = [source("source_primary", "external_argument")]
    helper = f"""
    static int transform_one(int value) {{ return value + {bias}; }}
    static int transform_two(int value) {{ return value * 2; }}
    """
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 3);
            /* RIFT_NODE:node_stage_one */
            int node_stage_one = transform_one(source_primary);
            /* RIFT_NODE:node_stage_two */
            int node_stage_two = transform_two(node_stage_one);
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_stage_two >= {2 * (bias + 3)});
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        relations = [relation("source_primary", "ap_primary", influence, ["source_primary", "node_stage_one", "node_stage_two", "ap_primary"], ["call", "call", "data"], mutation=recipe("affine_boundary", "solve two-stage affine threshold", ["2", "3", "4"]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 3);
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 2, 1);
            /* RIFT_NODE:node_stage_one */
            int node_stage_one = source_gate ? transform_one(source_primary) : {bias};
            /* RIFT_NODE:node_stage_two */
            int node_stage_two = transform_two(node_stage_one);
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_stage_two >= {2 * (bias + 3)});
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        relations = [
            relation("source_primary", "ap_primary", influence, ["source_primary", "node_stage_one", "node_stage_two", "ap_primary"], ["call", "call", "data"], preconditions=["source_gate != 0"], mutation=recipe("affine_boundary", "cross affine threshold under guard", ["2", "3", "4"])),
            relation("source_gate", "ap_primary", influence, ["source_gate", "node_stage_one", "node_stage_two", "ap_primary"], ["control", "call", "data"], mutation=recipe("boolean_toggle", "select transformed value", ["0", "1"])),
        ]
    else:
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 3);
            (void)transform_one(source_primary);
            /* RIFT_NODE:node_stage_one */
            int node_stage_one = transform_one({bias});
            /* RIFT_NODE:node_stage_two */
            int node_stage_two = transform_two(node_stage_one);
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_stage_two >= {2 * (bias + 1)});
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        relations = [relation("source_primary", "ap_primary", influence, [], [], negative_reason="The source reaches a discarded helper result, while the AP chain starts from a constant.")]
    return TemplateResult(clean(helper + body), sources, [ap("ap_primary", "node_stage_two reaches generated affine threshold")], relations, "Two explicit helper stages mechanically define the interprocedural value path; negative variants use a separate constant-rooted helper chain.")


def control_only(influence: str, variant: int) -> TemplateResult:
    threshold = 3 + variant
    sources = [source("source_primary", "external_argument")]
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            int result = 0;
            if (source_primary > {threshold}) {{ result = 1; }}
            /* RIFT_AP:ap_primary */
            int ap_primary = result;
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        rels = [relation("source_primary", "ap_primary", influence, ["source_primary", "ap_primary"], ["control"], mutation=recipe("guard_flip", "cross guard boundary", [str(threshold), str(threshold + 1)]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 2, 1);
            int result = 0;
            if (source_gate != 0 && source_primary > {threshold}) {{ result = 1; }}
            /* RIFT_AP:ap_primary */
            int ap_primary = result;
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        rels = [
            relation("source_primary", "ap_primary", influence, ["source_primary", "ap_primary"], ["control"], preconditions=["source_gate != 0"], mutation=recipe("guard_flip", "cross guarded boundary", [str(threshold), str(threshold + 1)])),
            relation("source_gate", "ap_primary", influence, ["source_gate", "ap_primary"], ["control"], mutation=recipe("boolean_toggle", "enable guarded assignment", ["0", "1"])),
        ]
    else:
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            (void)source_primary;
            int result = ({variant} % 2);
            /* RIFT_AP:ap_primary */
            int ap_primary = result;
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        rels = [relation("source_primary", "ap_primary", influence, [], [], negative_reason="The similarly positioned source does not guard either AP definition.")]
    return TemplateResult(clean(body), sources, [ap("ap_primary", "branch-selected Boolean", "GUARD")], rels, "The positive templates place the source only in a branch predicate, never in the assigned AP data value; negative variants remove that predicate dependence.")


def alias_object_field(influence: str, variant: int) -> TemplateResult:
    sources = [source("source_primary", "external_argument", scope="OBJECT")]
    support = "struct NeutralRecord { int observed; int shadow; };\n"
    if influence == "MUST_INFLUENCE":
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 7);
            struct NeutralRecord first = {0, 0};
            /* RIFT_NODE:node_alias */
            struct NeutralRecord *node_alias = &first;
            node_alias->observed = source_primary;
            /* RIFT_NODE:node_field */
            int node_field = first.observed;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_field != 0);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [relation("source_primary", "ap_primary", influence, ["source_primary", "node_alias", "node_field", "ap_primary"], ["alias", "field", "data"], mutation=recipe("field_boundary", "toggle aliased field around zero", ["0", "1", "-1"]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument", scope="OBJECT"))
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 7);
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 2, 1);
            struct NeutralRecord first = {0, 0};
            struct NeutralRecord second = {0, 0};
            /* RIFT_NODE:node_alias */
            struct NeutralRecord *node_alias = source_gate ? &first : &second;
            node_alias->observed = source_primary;
            /* RIFT_NODE:node_field */
            int node_field = first.observed;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_field != 0);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [
            relation("source_primary", "ap_primary", influence, ["source_primary", "node_alias", "node_field", "ap_primary"], ["alias", "field", "data"], preconditions=["node_alias points to first"], mutation=recipe("field_boundary", "toggle selected object field", ["0", "1"])),
            relation("source_gate", "ap_primary", influence, ["source_gate", "node_alias", "node_field", "ap_primary"], ["control", "alias", "field"], mutation=recipe("alias_selection", "select AP-observed object", ["0", "1"])),
        ]
    else:
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 7);
            struct NeutralRecord first = {1, 0};
            struct NeutralRecord second = {0, 0};
            /* RIFT_NODE:node_alias */
            struct NeutralRecord *node_alias = &second;
            node_alias->shadow = source_primary;
            /* RIFT_NODE:node_field */
            int node_field = first.observed;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_field != 0);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [relation("source_primary", "ap_primary", influence, [], [], negative_reason="The source writes a different field of a different object than the field read by the AP.")]
    return TemplateResult(clean(support + body), sources, [ap("ap_primary", "first.observed != 0")], rels, "Named objects and fields make the alias oracle exact: positive variants share the AP object/field; negative variants differ in both object and field.")


def config_threshold(influence: str, variant: int) -> TemplateResult:
    fixed = 10 + variant
    sources = [source("source_configuration", "configuration", scope="SESSION"), source("source_observation", "sensor_value", scope="SESSION")]
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_configuration */
            int source_configuration = read_arg(argc, argv, 1, {fixed});
            /* RIFT_SOURCE:source_observation */
            int source_observation = read_arg(argc, argv, 2, {fixed});
            /* RIFT_NODE:node_threshold */
            int node_threshold = source_configuration;
            /* RIFT_NODE:node_observed */
            int node_observed = source_observation;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_observed >= node_threshold);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        config_relation = relation("source_configuration", "ap_primary", influence, ["source_configuration", "node_threshold", "ap_primary"], ["data", "data"], mutation=recipe("dynamic_threshold", "move threshold across observation", [str(fixed - 1), str(fixed), str(fixed + 1)]))
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument", scope="SESSION"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_configuration */
            int source_configuration = read_arg(argc, argv, 1, {fixed});
            /* RIFT_SOURCE:source_observation */
            int source_observation = read_arg(argc, argv, 2, {fixed});
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 3, 1);
            /* RIFT_NODE:node_threshold */
            int node_threshold = source_gate ? source_configuration : {fixed};
            /* RIFT_NODE:node_observed */
            int node_observed = source_observation;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_observed >= node_threshold);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        config_relation = relation("source_configuration", "ap_primary", influence, ["source_configuration", "node_threshold", "ap_primary"], ["data", "data"], preconditions=["source_gate != 0"], mutation=recipe("dynamic_threshold", "move enabled threshold across observation", [str(fixed - 1), str(fixed + 1)]))
    else:
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_configuration */
            int source_configuration = read_arg(argc, argv, 1, {fixed});
            (void)source_configuration;
            /* RIFT_SOURCE:source_observation */
            int source_observation = read_arg(argc, argv, 2, {fixed});
            /* RIFT_NODE:node_threshold */
            int node_threshold = {fixed};
            /* RIFT_NODE:node_observed */
            int node_observed = source_observation;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_observed >= node_threshold);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        config_relation = relation("source_configuration", "ap_primary", influence, [], [], negative_reason="The configuration-like input is shadowed by a fixed threshold; only the observation reaches the AP.")
    rels = [config_relation, relation("source_observation", "ap_primary", "MUST_INFLUENCE", ["source_observation", "node_observed", "ap_primary"], ["data", "data"], mutation=recipe("observation_boundary", "cross active threshold", [str(fixed - 1), str(fixed), str(fixed + 1)]))]
    if influence == "MAY_INFLUENCE":
        rels.append(relation("source_gate", "ap_primary", influence, ["source_gate", "node_threshold", "ap_primary"], ["control", "data"], mutation=recipe("configuration_enable", "toggle configured threshold", ["0", "1"])))
    return TemplateResult(clean(body), sources, [ap("ap_primary", "node_observed >= node_threshold", "BOUND")], rels, "The generated comparison explicitly separates the configurable bound from the observed value; negative variants replace only the bound with a constant.")


def message_parser_state(influence: str, variant: int) -> TemplateResult:
    expected_kind = 20 + variant
    sources = [source("source_message_value", "message_field", scope="SESSION")]
    support = f"""
    struct NeutralMessage {{ int kind; int value; int spare; }};
    static int parse_message(const struct NeutralMessage *message) {{
        return message->kind == {expected_kind} ? message->value : 0;
    }}
    """
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_message_value */
            int source_message_value = read_arg(argc, argv, 1, 4);
            /* RIFT_NODE:node_message */
            struct NeutralMessage node_message = {{{expected_kind}, source_message_value, 0}};
            /* RIFT_NODE:node_state */
            int node_state = parse_message(&node_message);
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_state > 3);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        rels = [relation("source_message_value", "ap_primary", influence, ["source_message_value", "node_message", "node_state", "ap_primary"], ["field", "parse", "state_commit"], mutation=recipe("message_field_boundary", "cross parsed state boundary", ["3", "4"]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_message_kind", "message_field", scope="SESSION"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_message_value */
            int source_message_value = read_arg(argc, argv, 1, 4);
            /* RIFT_SOURCE:source_message_kind */
            int source_message_kind = read_arg(argc, argv, 2, {expected_kind});
            /* RIFT_NODE:node_message */
            struct NeutralMessage node_message = {{source_message_kind, source_message_value, 0}};
            /* RIFT_NODE:node_state */
            int node_state = parse_message(&node_message);
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_state > 3);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        rels = [
            relation("source_message_value", "ap_primary", influence, ["source_message_value", "node_message", "node_state", "ap_primary"], ["field", "parse", "state_commit"], preconditions=[f"source_message_kind == {expected_kind}"], mutation=recipe("message_field_boundary", "cross value boundary for accepted kind", ["3", "4"])),
            relation("source_message_kind", "ap_primary", influence, ["source_message_kind", "node_message", "node_state", "ap_primary"], ["field", "parse", "control"], mutation=recipe("message_kind_selection", "select accepted or rejected kind", [str(expected_kind - 1), str(expected_kind)])),
        ]
    else:
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_message_value */
            int source_message_value = read_arg(argc, argv, 1, 4);
            /* RIFT_NODE:node_message */
            struct NeutralMessage node_message = {{{expected_kind}, 4, source_message_value}};
            /* RIFT_NODE:node_state */
            int node_state = parse_message(&node_message);
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_state > 3);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        rels = [relation("source_message_value", "ap_primary", influence, [], [], negative_reason="The source populates the spare field, while the parser commits only the value field.")]
    return TemplateResult(clean(support + body), sources, [ap("ap_primary", "parsed state > 3")], rels, "A typed message, parser predicate, and state commit make the field-to-state path explicit; the negative template uses a parser-ignored field.")


def async_timer_callback_queue(influence: str, variant: int) -> TemplateResult:
    sources = [source("source_payload", "callback_payload", scope="EVENT_SEQUENCE")]
    support = """
    struct NeutralQueue { int payload; int count; };
    static int enqueue_value(struct NeutralQueue *queue, int value, int accept) {
        if (!accept) { return 0; }
        queue->payload = value;
        queue->count = 1;
        return 1;
    }
    static int dequeue_value(struct NeutralQueue *queue) {
        if (queue->count == 0) { return 0; }
        queue->count = 0;
        return queue->payload;
    }
    struct NeutralTimer { int armed; int due; };
    static int fire_timer(const struct NeutralTimer *timer) {
        return timer->armed && timer->due <= 0;
    }
    static void commit_callback(int payload, int *state) { *state = payload; }
    """
    if influence == "MUST_INFLUENCE":
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_payload */
            int source_payload = read_arg(argc, argv, 1, 6);
            /* RIFT_NODE:node_queue */
            struct NeutralQueue node_queue = {0, 0};
            (void)enqueue_value(&node_queue, source_payload, 1);
            /* RIFT_NODE:node_dequeued */
            int node_dequeued = dequeue_value(&node_queue);
            /* RIFT_NODE:node_timer */
            struct NeutralTimer node_timer = {1, 0};
            int state = 0;
            if (fire_timer(&node_timer)) {
                commit_callback(node_dequeued, &state);
            }
            /* RIFT_NODE:node_callback_state */
            int node_callback_state = state;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_callback_state >= 6);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [relation("source_payload", "ap_primary", influence, ["source_payload", "node_queue", "node_dequeued", "node_timer", "node_callback_state", "ap_primary"], ["enqueue", "dequeue", "timer", "callback", "state_commit"], preconditions=["queue accepts payload", "timer fires", "callback is invoked"], mutation=recipe("async_payload_boundary", "cross callback state threshold", ["5", "6"]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_queue_accept", "queue_operation", scope="EVENT_SEQUENCE"))
        sources.append(source("source_timer_fire", "event_operation", scope="EVENT_SEQUENCE"))
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_payload */
            int source_payload = read_arg(argc, argv, 1, 6);
            /* RIFT_SOURCE:source_queue_accept */
            int source_queue_accept = read_arg(argc, argv, 2, 1);
            /* RIFT_SOURCE:source_timer_fire */
            int source_timer_fire = read_arg(argc, argv, 3, 1);
            /* RIFT_NODE:node_queue */
            struct NeutralQueue node_queue = {0, 0};
            (void)enqueue_value(&node_queue, source_payload, source_queue_accept != 0);
            /* RIFT_NODE:node_dequeued */
            int node_dequeued = dequeue_value(&node_queue);
            /* RIFT_NODE:node_timer */
            struct NeutralTimer node_timer = {source_timer_fire != 0, 0};
            int state = 0;
            if (fire_timer(&node_timer)) {
                commit_callback(node_dequeued, &state);
            }
            /* RIFT_NODE:node_callback_state */
            int node_callback_state = state;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_callback_state >= 6);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [
            relation("source_payload", "ap_primary", influence, ["source_payload", "node_queue", "node_dequeued", "node_timer", "node_callback_state", "ap_primary"], ["enqueue", "dequeue", "timer", "callback", "state_commit"], preconditions=["source_queue_accept != 0", "source_timer_fire != 0"], mutation=recipe("async_payload_boundary", "cross threshold when enqueue succeeds and timer fires", ["5", "6"])),
            relation("source_queue_accept", "ap_primary", influence, ["source_queue_accept", "node_queue", "node_dequeued", "node_timer", "node_callback_state", "ap_primary"], ["control", "dequeue", "timer", "callback", "state_commit"], preconditions=["source_timer_fire != 0"], mutation=recipe("drop_toggle", "accept or drop queued item", ["0", "1"])),
            relation("source_timer_fire", "ap_primary", influence, ["source_timer_fire", "node_timer", "node_callback_state", "ap_primary"], ["timer", "callback", "state_commit"], preconditions=["source_queue_accept != 0"], mutation=recipe("timer_fire", "arm or suppress timer firing", ["0", "1"], "at the queued callback deadline")),
        ]
    else:
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_payload */
            int source_payload = read_arg(argc, argv, 1, 6);
            /* RIFT_NODE:node_queue */
            struct NeutralQueue node_queue = {0, 0};
            (void)enqueue_value(&node_queue, source_payload, 0);
            /* RIFT_NODE:node_dequeued */
            int node_dequeued = dequeue_value(&node_queue);
            (void)node_dequeued;
            /* RIFT_NODE:node_timer */
            struct NeutralTimer node_timer = {1, 0};
            int state = 0;
            if (fire_timer(&node_timer)) {
                commit_callback(6, &state);
            }
            /* RIFT_NODE:node_callback_state */
            int node_callback_state = state;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_callback_state >= 6);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [relation("source_payload", "ap_primary", influence, [], [], negative_reason="The queue rejects the payload and the AP observes an independently initialized callback state.")]
    return TemplateResult(clean(support + body), sources, [ap("ap_primary", "callback-committed state >= 6")], rels, "The template models enqueue, dequeue, timer fire, callback invocation, and state commit as distinct mechanically known stages; the negative path drops before commit.")


def setup_mode_prerequisite(influence: str, variant: int) -> TemplateResult:
    sources = [source("source_primary", "external_argument", scope="SESSION")]
    support = """
    struct NeutralContext { int ready; int mode; int state; };
    static void initialize_context(struct NeutralContext *context) { context->ready = 1; }
    static void select_mode(struct NeutralContext *context, int mode) { context->mode = mode; }
    static void commit_if_ready(struct NeutralContext *context, int value) {
        if (context->ready && context->mode == 2) { context->state = value; }
    }
    """
    if influence == "MUST_INFLUENCE":
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 8);
            /* RIFT_NODE:node_context */
            struct NeutralContext node_context = {0, 0, 0};
            initialize_context(&node_context);
            select_mode(&node_context, 2);
            commit_if_ready(&node_context, source_primary);
            /* RIFT_NODE:node_state */
            int node_state = node_context.state;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_state == 8);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [relation("source_primary", "ap_primary", influence, ["source_primary", "node_context", "node_state", "ap_primary"], ["setup", "state_commit", "data"], preconditions=["initialize_context occurs first", "mode equals 2"], mutation=recipe("state_value", "cross committed-state equality", ["7", "8", "9"]))]
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_setup_mode", "setup_operation", scope="SESSION"))
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 8);
            /* RIFT_SOURCE:source_setup_mode */
            int source_setup_mode = read_arg(argc, argv, 2, 2);
            /* RIFT_NODE:node_context */
            struct NeutralContext node_context = {0, 0, 0};
            initialize_context(&node_context);
            select_mode(&node_context, source_setup_mode);
            commit_if_ready(&node_context, source_primary);
            /* RIFT_NODE:node_state */
            int node_state = node_context.state;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_state == 8);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [
            relation("source_primary", "ap_primary", influence, ["source_primary", "node_context", "node_state", "ap_primary"], ["setup", "state_commit", "data"], preconditions=["source_setup_mode == 2", "initialize_context occurs first"], mutation=recipe("state_value", "mutate value after setup", ["7", "8"])),
            relation("source_setup_mode", "ap_primary", influence, ["source_setup_mode", "node_context", "node_state", "ap_primary"], ["setup", "control", "data"], mutation=recipe("setup_sequence", "select required mode before commit", ["1", "2"])),
        ]
    else:
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, 8);
            /* RIFT_NODE:node_context */
            struct NeutralContext node_context = {0, 0, 0};
            commit_if_ready(&node_context, source_primary);
            initialize_context(&node_context);
            select_mode(&node_context, 2);
            node_context.state = 8;
            /* RIFT_NODE:node_state */
            int node_state = node_context.state;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_state == 8);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
        rels = [relation("source_primary", "ap_primary", influence, [], [], negative_reason="The source is offered before setup and rejected; a later constant write establishes AP state.")]
    return TemplateResult(clean(support + body), sources, [ap("ap_primary", "prepared context state == 8")], rels, "Lifecycle order and required mode are explicit in the template, allowing the oracle to distinguish a valid setup sequence from an ignored pre-setup update.")


def timing_drop_repeat_reorder(influence: str, variant: int) -> TemplateResult:
    operation = ["delay", "drop", "repeat", "reorder"][variant % 4]
    kind = "time_input" if operation == "delay" else "event_operation"
    sources = [source("source_primary", kind, scope="EVENT_SEQUENCE")]
    support = "struct NeutralTimeline { int delay; int delivered; int repeats; int order; };\n"
    field = {"delay": "delay", "drop": "delivered", "repeat": "repeats", "reorder": "order"}[operation]
    expression = {"delay": "node_event_value <= 5", "drop": "node_event_value != 0", "repeat": "node_event_value >= 2", "reorder": "node_event_value == 0"}[operation]
    direction = {"delay": "cross relative deadline", "drop": "drop or deliver event", "repeat": "cross occurrence-count boundary", "reorder": "swap event order"}[operation]
    values = {"delay": ["4", "5", "6"], "drop": ["0", "1"], "repeat": ["1", "2", "3"], "reorder": ["0", "1"]}[operation]
    default = {"delay": 5, "drop": 1, "repeat": 2, "reorder": 0}[operation]
    if influence == "MUST_INFLUENCE":
        assignment = "source_primary"
        gate_code = ""
        preconditions: list[str] = []
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_sequence_gate", "event_operation", scope="EVENT_SEQUENCE"))
        assignment = f"source_sequence_gate ? source_primary : {default}"
        gate_code = """
            /* RIFT_SOURCE:source_sequence_gate */
            int source_sequence_gate = read_arg(argc, argv, 2, 1);
        """
        preconditions = ["source_sequence_gate != 0"]
    else:
        assignment = str(default)
        gate_code = ""
        preconditions = []
    body = f"""
    int main(int argc, char **argv) {{
        /* RIFT_SOURCE:source_primary */
        int source_primary = read_arg(argc, argv, 1, {default});
        {gate_code}
        {"(void)source_primary;" if influence == "NO_INFLUENCE" else ""}
        /* RIFT_NODE:node_timeline */
        struct NeutralTimeline node_timeline = {{5, 1, 2, 0}};
        node_timeline.{field} = {assignment};
        /* RIFT_NODE:node_event_value */
        int node_event_value = node_timeline.{field};
        /* RIFT_AP:ap_primary */
        int ap_primary = ({expression});
        printf("AP_primary=%d\\n", ap_primary);
        return 0;
    }}
    """
    if influence == "NO_INFLUENCE":
        rels = [relation("source_primary", "ap_primary", influence, [], [], negative_reason=f"The {operation} input is read but the timeline field is assigned a generated constant.")]
    else:
        edge_kind = "timing" if operation == "delay" else "event_order"
        rels = [relation("source_primary", "ap_primary", influence, ["source_primary", "node_timeline", "node_event_value", "ap_primary"], [edge_kind, "field", edge_kind], preconditions=preconditions, mutation=recipe(operation, direction, values, "relative to generated deadline" if operation == "delay" else None))]
        if influence == "MAY_INFLUENCE":
            rels.append(relation("source_sequence_gate", "ap_primary", influence, ["source_sequence_gate", "node_timeline", "node_event_value", "ap_primary"], ["control", "field", edge_kind], mutation=recipe("sequence_enable", "enable temporal operation", ["0", "1"])))
    return TemplateResult(clean(support + body), sources, [ap("ap_primary", expression, "TIMING")], rels, f"The {operation} variant maps one explicit event-sequence operation to one timeline field and AP; negative variants overwrite that field independently.")


def uncontrollable_false_correlation(influence: str, variant: int) -> TemplateResult:
    sources = [
        source("source_internal", "internal_state", "INTERNAL", "OBJECT"),
        source("source_external_similar", "external_argument", "EXTERNAL", "OBJECT"),
    ]
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_internal */
            int source_internal = {variant + 1};
            /* RIFT_SOURCE:source_external_similar */
            int source_external_similar = read_arg(argc, argv, 1, {variant + 1});
            (void)source_external_similar;
            /* RIFT_NODE:node_internal_state */
            int node_internal_state = source_internal;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_internal_state > 0);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        internal_relation = relation("source_internal", "ap_primary", influence, ["source_internal", "node_internal_state", "ap_primary"], ["data", "data"], mutation=None)
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument", "EXTERNAL", "OBJECT"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_internal */
            int source_internal = {variant + 1};
            /* RIFT_SOURCE:source_external_similar */
            int source_external_similar = read_arg(argc, argv, 1, {variant + 1});
            (void)source_external_similar;
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 2, 1);
            /* RIFT_NODE:node_internal_state */
            int node_internal_state = source_gate ? source_internal : 0;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_internal_state > 0);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        internal_relation = relation("source_internal", "ap_primary", influence, ["source_internal", "node_internal_state", "ap_primary"], ["data", "data"], preconditions=["source_gate != 0"], mutation=None)
    else:
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_internal */
            int source_internal = {variant + 1};
            /* RIFT_SOURCE:source_external_similar */
            int source_external_similar = read_arg(argc, argv, 1, {variant + 1});
            (void)source_internal;
            (void)source_external_similar;
            /* RIFT_NODE:node_internal_state */
            int node_internal_state = 1;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_internal_state > 0);
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
        internal_relation = relation("source_internal", "ap_primary", influence, [], [], negative_reason="Neither the internal state nor its similarly named external decoy reaches the constant AP state.")
    rels = [
        internal_relation,
        relation("source_external_similar", "ap_primary", "NO_INFLUENCE", [], [], negative_reason="The external source has a correlated name and value but no program-dependence path to the AP."),
    ]
    if influence == "MAY_INFLUENCE":
        rels.append(relation("source_gate", "ap_primary", influence, ["source_gate", "node_internal_state", "ap_primary"], ["control", "data"], mutation=recipe("internal_path_enable", "enable observation of internal state", ["0", "1"])))
    return TemplateResult(clean(body), sources, [ap("ap_primary", "internal state > 0")], rels, "The template deliberately separates a true but uncontrollable internal influencer from a similarly named controllable decoy, making controllability and false correlation independently testable.")


def one_input_multi_ap(influence: str, variant: int) -> TemplateResult:
    threshold = 4 + variant
    sources = [source("source_primary", "external_argument", scope="SESSION")]
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            /* RIFT_NODE:node_shared */
            int node_shared = source_primary * 2;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_shared >= {threshold * 2});
            /* RIFT_AP:ap_secondary */
            int ap_secondary = ((node_shared & 1) == 0 && node_shared != 0);
            printf("AP_primary=%d AP_secondary=%d\\n", ap_primary, ap_secondary);
            return 0;
        }}
        """
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "external_argument", scope="SESSION"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 2, 1);
            /* RIFT_NODE:node_shared */
            int node_shared = source_gate ? source_primary * 2 : 0;
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_shared >= {threshold * 2});
            /* RIFT_AP:ap_secondary */
            int ap_secondary = ((node_shared & 1) == 0 && node_shared != 0);
            printf("AP_primary=%d AP_secondary=%d\\n", ap_primary, ap_secondary);
            return 0;
        }}
        """
    else:
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_primary */
            int source_primary = read_arg(argc, argv, 1, {threshold});
            (void)source_primary;
            /* RIFT_NODE:node_shared */
            int node_shared = {threshold * 2};
            /* RIFT_AP:ap_primary */
            int ap_primary = (node_shared >= {threshold * 2});
            /* RIFT_AP:ap_secondary */
            int ap_secondary = ((node_shared & 1) == 0 && node_shared != 0);
            printf("AP_primary=%d AP_secondary=%d\\n", ap_primary, ap_secondary);
            return 0;
        }}
        """
    aps = [ap("ap_primary", "shared affine value crosses threshold"), ap("ap_secondary", "shared affine value satisfies parity/presence guard", "GUARD")]
    rels: list[dict[str, Any]] = []
    for target in ["ap_primary", "ap_secondary"]:
        if influence == "NO_INFLUENCE":
            rels.append(relation("source_primary", target, influence, [], [], negative_reason="Both APs read a constant shared node rather than the external source."))
        else:
            rels.append(relation("source_primary", target, influence, ["source_primary", "node_shared", target], ["data", "data"], preconditions=["source_gate != 0"] if influence == "MAY_INFLUENCE" else [], mutation=recipe("multi_ap_shared_input", "mutate one source against both AP boundaries", [str(threshold - 1), str(threshold), str(threshold + 1)])))
    if influence == "MAY_INFLUENCE":
        for target in ["ap_primary", "ap_secondary"]:
            rels.append(relation("source_gate", target, influence, ["source_gate", "node_shared", target], ["control", "data"], mutation=recipe("multi_ap_enable", "enable shared propagation", ["0", "1"])))
    return TemplateResult(clean(body), sources, aps, rels, "One shared derived node feeds two independently declared APs; negative variants preserve the fan-out shape but root it at a constant.")


def joint_inputs(influence: str, variant: int) -> TemplateResult:
    low = 3 + variant
    high = 9 + variant
    sources = [source("source_left", "external_argument", scope="SESSION"), source("source_right", "external_argument", scope="SESSION")]
    if influence == "MUST_INFLUENCE":
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_left */
            int source_left = read_arg(argc, argv, 1, {low + 1});
            /* RIFT_SOURCE:source_right */
            int source_right = read_arg(argc, argv, 2, {high - 1});
            /* RIFT_NODE:node_joint_guard */
            int node_joint_guard = (source_left > {low}) && (source_right < {high});
            /* RIFT_AP:ap_primary */
            int ap_primary = node_joint_guard;
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
    elif influence == "MAY_INFLUENCE":
        sources.append(source("source_gate", "setup_operation", scope="SESSION"))
        body = f"""
        int main(int argc, char **argv) {{
            /* RIFT_SOURCE:source_left */
            int source_left = read_arg(argc, argv, 1, {low + 1});
            /* RIFT_SOURCE:source_right */
            int source_right = read_arg(argc, argv, 2, {high - 1});
            /* RIFT_SOURCE:source_gate */
            int source_gate = read_arg(argc, argv, 3, 1);
            /* RIFT_NODE:node_joint_guard */
            int node_joint_guard = source_gate && (source_left > {low}) && (source_right < {high});
            /* RIFT_AP:ap_primary */
            int ap_primary = node_joint_guard;
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }}
        """
    else:
        body = """
        int main(int argc, char **argv) {
            /* RIFT_SOURCE:source_left */
            int source_left = read_arg(argc, argv, 1, 4);
            /* RIFT_SOURCE:source_right */
            int source_right = read_arg(argc, argv, 2, 8);
            (void)source_left;
            (void)source_right;
            /* RIFT_NODE:node_joint_guard */
            int node_joint_guard = 1;
            /* RIFT_AP:ap_primary */
            int ap_primary = node_joint_guard;
            printf("AP_primary=%d\\n", ap_primary);
            return 0;
        }
        """
    rels = []
    for source_id in ["source_left", "source_right"]:
        if influence == "NO_INFLUENCE":
            rels.append(relation(source_id, "ap_primary", influence, [], [], negative_reason="The joint guard is constant and ignores both externally supplied operands."))
        else:
            rels.append(relation(source_id, "ap_primary", influence, [source_id, "node_joint_guard", "ap_primary"], ["control", "data"], preconditions=["the other joint operand satisfies its guard"] + (["source_gate != 0"] if influence == "MAY_INFLUENCE" else []), mutation=recipe("joint_boundary", "mutate with the other operand held in its satisfying region", [str(low), str(low + 1), str(high - 1), str(high)]), joint_group=["source_left", "source_right"]))
    if influence == "MAY_INFLUENCE":
        rels.append(relation("source_gate", "ap_primary", influence, ["source_gate", "node_joint_guard", "ap_primary"], ["control", "data"], mutation=recipe("joint_enable", "enable joint predicate", ["0", "1"]), joint_group=["source_left", "source_right", "source_gate"]))
    return TemplateResult(clean(body), sources, [ap("ap_primary", f"source_left > {low} and source_right < {high}", "GUARD")], rels, "The AP is a conjunction whose truth-change requires satisfying regions for both inputs; the oracle records the joint group instead of pretending either mutation is sufficient alone.")


TEMPLATES: dict[str, Callable[[str, int], TemplateResult]] = {
    "direct_data": direct_data,
    "indirect_data": indirect_data,
    "control_only": control_only,
    "alias_object_field": alias_object_field,
    "config_threshold": config_threshold,
    "message_parser_state": message_parser_state,
    "async_timer_callback_queue": async_timer_callback_queue,
    "setup_mode_prerequisite": setup_mode_prerequisite,
    "timing_drop_repeat_reorder": timing_drop_repeat_reorder,
    "uncontrollable_false_correlation": uncontrollable_false_correlation,
    "one_input_multi_ap": one_input_multi_ap,
    "joint_inputs": joint_inputs,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dump_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def locations(code: str, relative_file: str) -> dict[str, dict[str, Any]]:
    lines = code.splitlines()
    result: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(lines):
        match = MARKER.search(line)
        if not match:
            continue
        kind, token = match.groups()
        if token in result:
            raise ValueError(f"duplicate marker {token}")
        target_index = index + 1
        while target_index < len(lines) and not lines[target_index].strip():
            target_index += 1
        if target_index >= len(lines) or token not in lines[target_index]:
            raise ValueError(f"marker {token} is not followed by a line containing its token")
        result[token] = {
            "kind": kind,
            "token": token,
            "location": {
                "file": relative_file,
                "line": target_index + 1,
                "column": lines[target_index].index(token) + 1,
            },
        }
    return result


def ensure_generated_set(directory: Path, expected: set[str], patterns: tuple[str, ...]) -> None:
    existing = {
        path.name
        for pattern in patterns
        for path in directory.glob(pattern)
        if path.is_file()
    }
    stale = existing - expected
    if stale:
        raise RuntimeError(f"refusing to delete stale generated files in {directory}: {sorted(stale)}")


def generate(output: Path, command_root: Path) -> None:
    output = output.resolve()
    command_root = command_root.resolve()
    cases_dir = output / "cases"
    truth_dir = output / "ground_truth"
    build_dir = output / "build"
    cases_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    case_names: set[str] = set()
    truth_names: set[str] = set()
    pending: list[tuple[Path, bytes]] = []
    commands: list[dict[str, Any]] = []
    manifest_entries: list[dict[str, Any]] = []
    case_number = 0

    for category in CATEGORIES:
        template = TEMPLATES[category]
        for variant, case_relation in enumerate(RELATIONS):
            case_number += 1
            case_id = f"RIFT-GOLD-{case_number:03d}"
            language = "c11" if variant % 2 == 0 else "c++20"
            extension = "c" if language == "c11" else "cpp"
            relation_tag = {"MUST_INFLUENCE": "must", "MAY_INFLUENCE": "may", "NO_INFLUENCE": "negative"}[case_relation]
            stem = f"{case_number:03d}_{category}_{relation_tag}_v{variant}"
            source_name = f"{stem}.{extension}"
            truth_name = f"{stem}.json"
            relative_source = f"cases/{source_name}"
            rendered = template(case_relation, variant)
            header = clean(
                f"""
                /*
                 * {case_id}: {category}, variant {variant}, {case_relation}
                 * Generated by RIFT mechanical gold generator {GENERATOR_VERSION}.
                 * Ground truth is template-derived; it is not a human label.
                 */
                """
            )
            code = header + PREAMBLE + rendered.code
            code_bytes = code.encode("utf-8")
            anchor_map = locations(code, relative_source)

            source_records = []
            for item in rendered.sources:
                if item["id"] not in anchor_map or anchor_map[item["id"]]["kind"] != "SOURCE":
                    raise ValueError(f"missing source marker {item['id']} in {case_id}")
                source_records.append({**item, "location": anchor_map[item["id"]]["location"]})
            ap_records = []
            for item in rendered.aps:
                if item["id"] not in anchor_map or anchor_map[item["id"]]["kind"] != "AP":
                    raise ValueError(f"missing AP marker {item['id']} in {case_id}")
                ap_records.append({**item, "location": anchor_map[item["id"]]["location"]})
            for expected in rendered.relations:
                for node in expected["path"]["nodes"]:
                    if node not in anchor_map:
                        raise ValueError(f"unknown path anchor {node} in {case_id}")

            truth = {
                "schema_version": SCHEMA_VERSION,
                "case_id": case_id,
                "category": category,
                "language": language,
                "case_relation": case_relation,
                "source_file": relative_source,
                "source_sha256": sha256_bytes(code_bytes),
                "entry_point": "main",
                "sources": source_records,
                "aps": ap_records,
                "relations": rendered.relations,
                "anchors": anchor_map,
                "oracle": {
                    "kind": "MECHANICAL_TEMPLATE_ORACLE",
                    "generator_version": GENERATOR_VERSION,
                    "template_id": category,
                    "variant": variant,
                    "derivation": rendered.derivation,
                    "limitations": [
                        "The oracle is exact only for the generated template and declared source/AP pairs.",
                        "Compilation does not independently prove semantic influence or mutation effectiveness.",
                    ],
                },
                "human_validation": {
                    "status": "PENDING",
                    "required_annotators": 2,
                    "arbitration_required": True,
                    "note": "Real-project labels require two independent human annotations and arbitration; none are claimed here.",
                },
            }
            truth_bytes = dump_json(truth)
            case_names.add(source_name)
            truth_names.add(truth_name)
            pending.extend([(cases_dir / source_name, code_bytes), (truth_dir / truth_name, truth_bytes)])

            compiler = "clang-18" if language == "c11" else "clang++-18"
            standard = "-std=c11" if language == "c11" else "-std=c++20"
            command_source = command_root / "cases" / source_name
            command_output = command_root / "build" / f"{stem}.o"
            arguments = [
                compiler,
                standard,
                "-O0",
                "-g",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-c",
                str(command_source),
                "-o",
                str(command_output),
            ]
            commands.append({"directory": str(command_root), "file": str(command_source), "arguments": arguments})
            manifest_entries.append(
                {
                    "case_id": case_id,
                    "category": category,
                    "variant": variant,
                    "case_relation": case_relation,
                    "language": language,
                    "source_file": relative_source,
                    "ground_truth_file": f"ground_truth/{truth_name}",
                    "source_sha256": sha256_bytes(code_bytes),
                    "ground_truth_sha256": sha256_bytes(truth_bytes),
                }
            )

    ensure_generated_set(cases_dir, case_names, ("*.c", "*.cpp"))
    ensure_generated_set(truth_dir, truth_names, ("*.json",))
    for path, content in pending:
        path.write_bytes(content)

    compile_bytes = dump_json(commands)
    (output / "compile_commands.json").write_bytes(compile_bytes)
    distribution = {
        category: {
            "total": 10,
            "must": 4,
            "may": 3,
            "negative": 3,
            "c11": 5,
            "c++20": 5,
        }
        for category in CATEGORIES
    }
    schema_path = Path(__file__).resolve().with_name("ground_truth.schema.json")
    manifest = {
        "schema_version": "rift.mechanical-gold.manifest.v1",
        "corpus_id": "RIFT-GOLD-120-v1",
        "generator_version": GENERATOR_VERSION,
        "generator_sha256": sha256_file(Path(__file__).resolve()),
        "ground_truth_schema_sha256": sha256_file(schema_path),
        "command_root": str(command_root),
        "case_count": case_number,
        "categories": CATEGORIES,
        "distribution": distribution,
        "compile_commands_sha256": sha256_bytes(compile_bytes),
        "oracle": {
            "kind": "MECHANICAL_TEMPLATE_ORACLE",
            "claim": "Expected influence relations are constructed directly from template topology and are not inferred by an analyzer under test.",
            "not_claimed": [
                "No real-project precision or recall is implied.",
                "No human agreement score is implied.",
                "A positive static relation does not promise every concrete mutation flips an AP.",
            ],
        },
        "real_project_human_annotation": {
            "status": "PENDING",
            "required_annotators": 2,
            "arbitration_required": True,
        },
        "entries": manifest_entries,
    }
    (output / "manifest.json").write_bytes(dump_json(manifest))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--command-root", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    generate(output, (args.command_root or output).resolve())
    print(f"generated 120 cases under {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
