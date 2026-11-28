"""Static gate compatibility domains derived with forward-chaining rules."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from aom.model.entities import Aircraft, Direction, Flight, Gate
from aom.modules.gates.rules import Fact, ForwardChainer, HornRule, Variable
from aom.modules.gates.turn import Turn


@dataclass(frozen=True, slots=True)
class TurnContext:
    """Associate a temporal turn with its aircraft and arrival/departure flights."""

    turn_id: str
    turn: Turn
    aircraft: Aircraft
    arrival: Flight
    departure: Flight

    def __post_init__(self) -> None:
        if not self.turn_id:
            raise ValueError("turn_id must not be empty")
        if self.arrival.direction is not Direction.ARRIVAL:
            raise ValueError("arrival flight must have Direction.ARRIVAL")
        if self.departure.direction is not Direction.DEPARTURE:
            raise ValueError("departure flight must have Direction.DEPARTURE")
        if self.arrival.tail != self.aircraft.tail:
            raise ValueError("arrival flight tail must match aircraft tail")
        if self.departure.tail != self.aircraft.tail:
            raise ValueError("departure flight tail must match aircraft tail")


@dataclass(frozen=True, slots=True)
class TurnGateDomain:
    """The gates statically compatible with one turn context."""

    context: TurnContext
    gates: tuple[Gate, ...]


def derive_gate_domains(
    contexts: Iterable[TurnContext], gates: Iterable[Gate]
) -> tuple[TurnGateDomain, ...]:
    """Derive static gate domains without applying temporal overlap constraints."""
    turn_contexts = tuple(contexts)
    gate_list = tuple(gates)

    turn_ids: list[str] = []
    for context in turn_contexts:
        if context.turn_id in turn_ids:
            raise ValueError(f"duplicate turn_id {context.turn_id!r}")
        turn_ids.append(context.turn_id)

    facts: list[Fact] = []
    for context in turn_contexts:
        turn_id = context.turn_id
        facts.append(Fact("turn", (turn_id,)))
        facts.append(
            Fact("turn_wide", (turn_id,))
            if context.aircraft.is_wide_body
            else Fact("turn_narrow", (turn_id,))
        )
        facts.append(Fact("turn_arrival", (turn_id, context.arrival.flight_id)))
        facts.append(Fact("turn_departure", (turn_id, context.departure.flight_id)))
        for flight in (context.arrival, context.departure):
            predicate = "flight_international" if flight.international else "flight_domestic"
            facts.append(Fact(predicate, (turn_id, flight.flight_id)))

    gate_keys: list[tuple[str, Gate]] = []
    for index, gate in enumerate(gate_list):
        gate_key = f"gate-{index}"
        gate_keys.append((gate_key, gate))
        facts.append(Fact("gate", (gate_key,)))
        facts.append(Fact("gate_accepts_narrow", (gate_key,)))
        if gate.wide_body:
            facts.append(Fact("gate_accepts_wide", (gate_key,)))
        facts.append(Fact("gate_has_customs" if gate.customs else "gate_no_customs", (gate_key,)))

    inferred = ForwardChainer(facts, _gate_rules()).run()

    domains: list[TurnGateDomain] = []
    for context in turn_contexts:
        compatible_gates = tuple(
            gate
            for gate_key, gate in gate_keys
            if Fact("compatible", (context.turn_id, gate_key)) in inferred
        )
        domains.append(TurnGateDomain(context, compatible_gates))
    return tuple(domains)


def _gate_rules() -> tuple[HornRule, ...]:
    """Return the positive Horn clauses for aircraft size and customs."""
    turn = Variable("turn")
    flight = Variable("flight")
    arrival_flight = Variable("arrival_flight")
    departure_flight = Variable("departure_flight")
    gate = Variable("gate")

    return (
        HornRule(
            Fact("turn_requires_customs", (turn,)),
            (
                Fact("turn_arrival", (turn, flight)),
                Fact("flight_international", (turn, flight)),
            ),
        ),
        HornRule(
            Fact("turn_requires_customs", (turn,)),
            (
                Fact("turn_departure", (turn, flight)),
                Fact("flight_international", (turn, flight)),
            ),
        ),
        HornRule(
            Fact("turn_customs_optional", (turn,)),
            (
                Fact("turn_arrival", (turn, arrival_flight)),
                Fact("flight_domestic", (turn, arrival_flight)),
                Fact("turn_departure", (turn, departure_flight)),
                Fact("flight_domestic", (turn, departure_flight)),
            ),
        ),
        HornRule(
            Fact("size_compatible", (turn, gate)),
            (Fact("turn_wide", (turn,)), Fact("gate_accepts_wide", (gate,))),
        ),
        HornRule(
            Fact("size_compatible", (turn, gate)),
            (Fact("turn_narrow", (turn,)), Fact("gate_accepts_narrow", (gate,))),
        ),
        HornRule(
            Fact("customs_compatible", (turn, gate)),
            (Fact("turn_requires_customs", (turn,)), Fact("gate_has_customs", (gate,))),
        ),
        HornRule(
            Fact("customs_compatible", (turn, gate)),
            (Fact("turn_customs_optional", (turn,)), Fact("gate_has_customs", (gate,))),
        ),
        HornRule(
            Fact("customs_compatible", (turn, gate)),
            (Fact("turn_customs_optional", (turn,)), Fact("gate_no_customs", (gate,))),
        ),
        HornRule(
            Fact("compatible", (turn, gate)),
            (
                Fact("turn", (turn,)),
                Fact("gate", (gate,)),
                Fact("size_compatible", (turn, gate)),
                Fact("customs_compatible", (turn, gate)),
            ),
        ),
    )
