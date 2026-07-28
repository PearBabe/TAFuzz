#!/usr/bin/env python3
"""Derive an M5 predicate-occurrence probe from the frozen COAP-TX-01 IR.

The M4 property binds AP program phases through composite selectors.  M5 also
needs exact source occurrences for the values used by the AP predicates.  This
script preserves the formula and the M4 selector groups, then adds typed,
project-external source-location selectors for those predicate operands.

This is benchmark input construction, not analyzer knowledge.  No libcoap name
or location is compiled into the RIFT core.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


BOOL = {"kind": "bool", "canonical": "_Bool", "bit_width": 8, "signed": False}
ULONG = {
    "kind": "integer",
    "canonical": "unsigned long",
    "bit_width": 64,
    "signed": False,
}
QUEUE_PTR = {
    "kind": "pointer",
    "canonical": "struct coap_queue_t *",
    "bit_width": 64,
}


def source_selector(
    selector_id: str,
    file: str,
    line: int,
    column: int,
    value_type: dict[str, Any],
) -> dict[str, Any]:
    return {
        "selector_id": selector_id,
        "kind": "source_location",
        "value_type": value_type,
        "location": {
            "file": file,
            "line": line,
            "column": column,
            "location_kind": "spelling",
        },
    }


def reference(selector_id: str, value_type: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_kind": "reference",
        "operator": "decl_ref_or_member",
        "value_type": value_type,
        "referenced_selector_id": selector_id,
        "operands": [],
    }


def pointer_bool(selector_id: str) -> dict[str, Any]:
    return {
        "node_kind": "cast",
        "operator": "PointerToBoolean",
        "value_type": BOOL,
        "operands": [reference(selector_id, QUEUE_PTR)],
    }


def binary(
    node_kind: str,
    operator: str,
    value_type: dict[str, Any],
    *operands: dict[str, Any],
) -> dict[str, Any]:
    return {
        "node_kind": node_kind,
        "operator": operator,
        "value_type": value_type,
        "operands": list(operands),
    }


def attach_state_group(
    ap: dict[str, Any], group_id: str, selector_ids: list[str]
) -> None:
    if "state" not in ap["roles"]:
        ap["roles"].append("state")
    ap["role_selector_groups"].append(
        {"group_id": group_id, "role": "state", "all_of": selector_ids}
    )


def derive(base: dict[str, Any]) -> dict[str, Any]:
    if base.get("schema_version") != "2.0.0":
        raise ValueError("expected typed Property IR 2.0.0")
    if base.get("property_id") != "COAP-TX-01":
        raise ValueError("expected the frozen COAP-TX-01 base property")

    net = "src/coap_net.c"
    io = "src/coap_io.c"
    selectors = [
        source_selector("selector.m5.trigger.queue_node", net, 1409, 41, QUEUE_PTR),
        source_selector("selector.m5.deadline.now_guard", io, 366, 21, ULONG),
        source_selector("selector.m5.deadline.basetime_guard", io, 366, 33, ULONG),
        source_selector("selector.m5.deadline.queue_delta", io, 367, 19, ULONG),
        source_selector("selector.m5.deadline.now_due", io, 367, 24, ULONG),
        source_selector("selector.m5.deadline.basetime_due", io, 367, 35, ULONG),
        source_selector("selector.m5.ack.sent", net, 4789, 9, QUEUE_PTR),
        source_selector("selector.m5.rst.sent", net, 4945, 9, QUEUE_PTR),
        source_selector("selector.m5.cancel.head", net, 3279, 26, QUEUE_PTR),
        source_selector("selector.m5.cancel.tail", net, 3296, 28, QUEUE_PTR),
        source_selector("selector.m5.cancel.token", net, 3330, 28, QUEUE_PTR),
    ]
    existing = {selector["selector_id"] for selector in base["selectors"]}
    overlap = existing.intersection(selector["selector_id"] for selector in selectors)
    if overlap:
        raise ValueError(f"derived selector ID collision: {sorted(overlap)}")
    base["selectors"].extend(selectors)

    aps = {ap["ap_id"]: ap for ap in base["atomic_propositions"]}
    expected = {
        "coap_con_wait_started",
        "coap_first_retransmit_deadline_reached",
        "coap_matching_ack_or_reset_received",
        "coap_attempt_cancelled",
    }
    if set(aps) != expected:
        raise ValueError("unexpected COAP-TX-01 AP set")

    trigger_ids = ["selector.m5.trigger.queue_node"]
    aps["coap_con_wait_started"]["predicate"] = pointer_bool(trigger_ids[0])
    attach_state_group(
        aps["coap_con_wait_started"],
        "binding-group.m5.wait-start.predicate-operands",
        trigger_ids,
    )

    deadline_ids = [
        "selector.m5.deadline.now_guard",
        "selector.m5.deadline.basetime_guard",
        "selector.m5.deadline.queue_delta",
        "selector.m5.deadline.now_due",
        "selector.m5.deadline.basetime_due",
    ]
    deadline = binary(
        "comparison",
        ">=",
        BOOL,
        reference(deadline_ids[0], ULONG),
        reference(deadline_ids[1], ULONG),
    )
    deadline = binary(
        "boolean",
        "and",
        BOOL,
        deadline,
        binary(
            "comparison",
            "<=",
            BOOL,
            reference(deadline_ids[2], ULONG),
            binary(
                "binary",
                "-",
                ULONG,
                reference(deadline_ids[3], ULONG),
                reference(deadline_ids[4], ULONG),
            ),
        ),
    )
    aps["coap_first_retransmit_deadline_reached"]["predicate"] = deadline
    attach_state_group(
        aps["coap_first_retransmit_deadline_reached"],
        "binding-group.m5.deadline.predicate-operands",
        deadline_ids,
    )

    ack_ids = ["selector.m5.ack.sent", "selector.m5.rst.sent"]
    aps["coap_matching_ack_or_reset_received"]["predicate"] = binary(
        "boolean", "or", BOOL, *(pointer_bool(selector_id) for selector_id in ack_ids)
    )
    attach_state_group(
        aps["coap_matching_ack_or_reset_received"],
        "binding-group.m5.ack-rst.predicate-operands",
        ack_ids,
    )

    cancel_ids = [
        "selector.m5.cancel.head",
        "selector.m5.cancel.tail",
        "selector.m5.cancel.token",
    ]
    cancel = pointer_bool(cancel_ids[0])
    for selector_id in cancel_ids[1:]:
        cancel = binary("boolean", "or", BOOL, cancel, pointer_bool(selector_id))
    aps["coap_attempt_cancelled"]["predicate"] = cancel
    attach_state_group(
        aps["coap_attempt_cancelled"],
        "binding-group.m5.local-cancel.predicate-operands",
        cancel_ids,
    )

    base["artifact_id"] = "rift.m5.coap_tx_01.portability_property"
    for ap in base["atomic_propositions"]:
        ap["description"] += (
            " M5 portability input adds typed predicate occurrences; it does not "
            "change the frozen MITL formula or claim a real-project gold label."
        )
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    options = parser.parse_args()
    base = json.loads(options.base.read_text(encoding="utf-8"))
    derived = derive(base)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(derived, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
