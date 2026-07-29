"""Data model and validation for timed Buchi guidance records."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from typing import Any, Mapping


class GuidanceInputError(ValueError):
    """Raised when an input artifact violates the guidance data contract."""


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise GuidanceInputError(f"{field} must be a non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GuidanceInputError(f"{field} must be an integer")
    return value


def parse_fraction(value: Any, field: str) -> Fraction:
    if isinstance(value, bool):
        raise GuidanceInputError(f"{field} must be numeric")
    try:
        if isinstance(value, float):
            return Fraction(str(value))
        return Fraction(value)
    except (ValueError, ZeroDivisionError, TypeError) as error:
        raise GuidanceInputError(f"{field} must be numeric: {value!r}") from error


def stable_digest(value: Any) -> str:
    material = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(material).hexdigest()


@dataclass(frozen=True)
class RuntimePrefix:
    run_id: str
    seed_id: str
    prefix_index: int
    time_us: int
    automaton_location: str
    zone_signature: str
    accepting: bool
    accepting_fixpoint: bool
    property_state_digest: str
    event_label: str
    transition_id: str
    monitor_verdict: str

    @property
    def recurrence_key(self) -> tuple[str, str, str]:
        return (
            self.automaton_location,
            self.zone_signature,
            self.property_state_digest,
        )

    @classmethod
    def from_json(
        cls, value: Mapping[str, Any], state_projection_fields: list[str]
    ) -> "RuntimePrefix":
        state = value.get("property_state")
        if not isinstance(state, Mapping):
            raise GuidanceInputError("property_state must be an object")
        if not state_projection_fields:
            raise GuidanceInputError("state_projection_fields must not be empty")
        missing = [name for name in state_projection_fields if name not in state]
        if missing:
            raise GuidanceInputError(
                "property_state is missing projected fields: " + ", ".join(missing)
            )
        projected = {name: state[name] for name in state_projection_fields}

        accepting = value.get("accepting")
        in_fixpoint = value.get("accepting_fixpoint")
        if not isinstance(accepting, bool) or not isinstance(in_fixpoint, bool):
            raise GuidanceInputError(
                "accepting and accepting_fixpoint must be booleans"
            )
        location = value.get("automaton_location")
        if isinstance(location, bool) or not isinstance(location, (int, str)):
            raise GuidanceInputError("automaton_location must be an integer or string")
        if isinstance(location, str) and not location:
            raise GuidanceInputError("automaton_location must not be empty")

        return cls(
            run_id=require_string(value.get("run_id"), "run_id"),
            seed_id=require_string(value.get("seed_id"), "seed_id"),
            prefix_index=require_int(value.get("prefix_index"), "prefix_index"),
            time_us=require_int(value.get("time_us"), "time_us"),
            automaton_location=str(location),
            zone_signature=require_string(
                value.get("zone_signature"), "zone_signature"
            ),
            accepting=accepting,
            accepting_fixpoint=in_fixpoint,
            property_state_digest=stable_digest(projected),
            event_label=str(value.get("event_label", "")),
            transition_id=str(value.get("transition_id", "")),
            monitor_verdict=str(value.get("monitor_verdict", "INCONCLUSIVE")),
        )


@dataclass(frozen=True)
class PrefixCost:
    prefix_index: int
    status: str
    kind: str
    value: Fraction | None
    next_edge_key: str | None
    exact: bool

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "PrefixCost":
        aggregate = value.get("aggregate")
        if not isinstance(aggregate, Mapping):
            raise GuidanceInputError("PTA record aggregate must be an object")
        kind = str(aggregate.get("kind", "unknown"))
        cost = None
        if kind == "finite":
            cost = parse_fraction(aggregate.get("value"), "aggregate.value")
        edge = aggregate.get("next_edge")
        edge_key = None
        if edge is not None:
            if not isinstance(edge, Mapping):
                raise GuidanceInputError("aggregate.next_edge must be an object")
            edge_key = (
                f"{require_int(edge.get('source'), 'next_edge.source')}:"
                f"{require_int(edge.get('ordinal'), 'next_edge.ordinal')}"
            )
        exact = aggregate.get("exact", False)
        if not isinstance(exact, bool):
            raise GuidanceInputError("aggregate.exact must be a boolean")
        return cls(
            prefix_index=require_int(value.get("prefix_index"), "prefix_index"),
            status=str(value.get("domain_status", "unknown")),
            kind=kind,
            value=cost,
            next_edge_key=edge_key,
            exact=exact,
        )


@dataclass(frozen=True)
class LassoCandidate:
    run_id: str
    seed_id: str
    start_prefix: int
    end_prefix: int
    duration_us: int
    signature: str
    accepting_visits: int


@dataclass(frozen=True)
class GuidanceConfig:
    property_id: str
    property_kind: str
    state_projection_fields: list[str]
    min_cycle_time_us: int
    cycle_time_quantum_us: int
    replay_confirmations: int
    edge_mutations: Mapping[str, list[Mapping[str, Any]]]

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "GuidanceConfig":
        if value.get("zone_signature_contract") != "PROPERTY_CLOCKS_ONLY":
            raise GuidanceInputError(
                "zone_signature_contract must be PROPERTY_CLOCKS_ONLY"
            )
        property_kind = require_string(value.get("property_kind"), "property_kind")
        if property_kind not in {"FINITE_PREFIX", "UNBOUNDED_LIVENESS"}:
            raise GuidanceInputError(
                "property_kind must be FINITE_PREFIX or UNBOUNDED_LIVENESS"
            )
        fields = value.get("state_projection_fields")
        if not isinstance(fields, list) or not all(
            isinstance(field, str) and field for field in fields
        ):
            raise GuidanceInputError(
                "state_projection_fields must be a list of non-empty strings"
            )
        minimum = require_int(value.get("min_cycle_time_us"), "min_cycle_time_us")
        quantum = require_int(
            value.get("cycle_time_quantum_us"), "cycle_time_quantum_us"
        )
        confirmations = require_int(
            value.get("replay_confirmations"), "replay_confirmations"
        )
        if minimum <= 0:
            raise GuidanceInputError("min_cycle_time_us must be positive")
        if quantum <= 0:
            raise GuidanceInputError("cycle_time_quantum_us must be positive")
        if confirmations < 2:
            raise GuidanceInputError("replay_confirmations must be at least 2")
        mutations = value.get("edge_mutations", {})
        if not isinstance(mutations, Mapping):
            raise GuidanceInputError("edge_mutations must be an object")
        return cls(
            property_id=require_string(value.get("property_id"), "property_id"),
            property_kind=property_kind,
            state_projection_fields=list(fields),
            min_cycle_time_us=minimum,
            cycle_time_quantum_us=quantum,
            replay_confirmations=confirmations,
            edge_mutations=mutations,
        )
