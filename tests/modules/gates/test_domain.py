"""Tests for deriving static gate domains from airport model entities."""

import pytest

from aom.model.entities import Aircraft, AircraftSize, Direction, Flight, Gate
from aom.modules.gates import TurnContext, TurnGateDomain, derive_gate_domains
from aom.modules.gates.turn import Turn


def _aircraft(size: AircraftSize = AircraftSize.NARROW) -> Aircraft:
    return Aircraft("TAIL-1", "XY", "A320", size, 180, 45)


def _flight(
    flight_id: str,
    direction: Direction,
    *,
    international: bool = False,
    tail: str = "TAIL-1",
    local_minute: int | None = None,
) -> Flight:
    if direction is Direction.ARRIVAL:
        arrival = 540 if local_minute is None else local_minute
        departure = arrival - 100
    else:
        departure = 600 if local_minute is None else local_minute
        arrival = departure + 100
    return Flight(
        flight_id,
        "XY",
        tail,
        "AAA",
        "BBB",
        direction,
        departure,
        arrival,
        international,
        180,
    )


def _context(
    turn_id: str = "turn-1",
    *,
    size: AircraftSize = AircraftSize.NARROW,
    arrival_international: bool = False,
    departure_international: bool = False,
    arrival_minute: int = 540,
    departure_minute: int = 600,
) -> TurnContext:
    return TurnContext(
        turn_id,
        Turn(arrival_minute, departure_minute),
        _aircraft(size),
        _flight(
            f"{turn_id}-arrival",
            Direction.ARRIVAL,
            international=arrival_international,
            local_minute=arrival_minute,
        ),
        _flight(
            f"{turn_id}-departure",
            Direction.DEPARTURE,
            international=departure_international,
            local_minute=departure_minute,
        ),
    )


def _gates() -> list[Gate]:
    return [
        Gate("N0", "A", False, False),
        Gate("N1", "B", False, True),
        Gate("W0", "C", True, True),
        Gate("W1", "D", True, False),
    ]


def _gate_ids(domain: TurnGateDomain) -> list[str]:
    return [gate.gate_id for gate in domain.gates]


def test_narrow_body_domestic_turn_can_use_all_gate_types() -> None:
    result = derive_gate_domains([_context()], _gates())

    assert _gate_ids(result[0]) == ["N0", "N1", "W0", "W1"]


def test_narrow_body_international_turn_requires_customs() -> None:
    result = derive_gate_domains([_context(arrival_international=True)], _gates())

    assert _gate_ids(result[0]) == ["N1", "W0"]


def test_wide_body_domestic_turn_requires_wide_body_support() -> None:
    result = derive_gate_domains([_context(size=AircraftSize.WIDE)], _gates())

    assert _gate_ids(result[0]) == ["W0", "W1"]


def test_wide_body_international_turn_requires_both_capabilities() -> None:
    result = derive_gate_domains(
        [_context(size=AircraftSize.WIDE, departure_international=True)], _gates()
    )

    assert _gate_ids(result[0]) == ["W0"]


@pytest.mark.parametrize(
    ("arrival_international", "departure_international"),
    [(True, False), (False, True)],
)
def test_either_international_flight_requires_customs(
    arrival_international: bool, departure_international: bool
) -> None:
    result = derive_gate_domains(
        [
            _context(
                arrival_international=arrival_international,
                departure_international=departure_international,
            )
        ],
        _gates(),
    )

    assert _gate_ids(result[0]) == ["N1", "W0"]


def test_empty_gate_input_returns_an_empty_domain() -> None:
    result = derive_gate_domains([_context()], [])

    assert len(result) == 1
    assert result[0].gates == ()


def test_turn_without_compatible_gate_has_empty_domain() -> None:
    incompatible = [Gate("N-CUSTOMS", "A", False, True), Gate("W-NO-CUSTOMS", "C", True, False)]
    result = derive_gate_domains(
        [_context(size=AircraftSize.WIDE, arrival_international=True)], incompatible
    )

    assert result[0].gates == ()


def test_multiple_turns_receive_independent_domains() -> None:
    contexts = [
        _context("narrow", size=AircraftSize.NARROW),
        _context("wide-international", size=AircraftSize.WIDE, arrival_international=True),
    ]

    results = derive_gate_domains(contexts, _gates())

    assert [result.context.turn_id for result in results] == ["narrow", "wide-international"]
    assert [_gate_ids(result) for result in results] == [
        ["N0", "N1", "W0", "W1"],
        ["W0"],
    ]


def test_repeated_flight_ids_do_not_share_facts_between_turns() -> None:
    international = _context("international", arrival_international=True)
    domestic = _context("domestic")
    domestic.arrival.flight_id = international.arrival.flight_id
    domestic.departure.flight_id = international.departure.flight_id

    results = derive_gate_domains([international, domestic], _gates())

    assert [_gate_ids(result) for result in results] == [
        ["N1", "W0"],
        ["N0", "N1", "W0", "W1"],
    ]


def test_overlapping_turns_keep_independent_static_domains() -> None:
    first = _context("first", size=AircraftSize.NARROW)
    second = _context(
        "second",
        size=AircraftSize.WIDE,
        arrival_international=True,
        arrival_minute=580,
        departure_minute=620,
    )
    assert first.turn.overlaps(second.turn)

    results = derive_gate_domains([first, second], _gates())

    assert [_gate_ids(result) for result in results] == [
        ["N0", "N1", "W0", "W1"],
        ["W0"],
    ]


def test_invalid_arrival_direction_is_rejected() -> None:
    with pytest.raises(ValueError, match="arrival flight"):
        TurnContext(
            "bad-arrival",
            Turn(540, 600),
            _aircraft(),
            _flight("arrival", Direction.DEPARTURE),
            _flight("departure", Direction.DEPARTURE),
        )


def test_invalid_departure_direction_is_rejected() -> None:
    with pytest.raises(ValueError, match="departure flight"):
        TurnContext(
            "bad-departure",
            Turn(540, 600),
            _aircraft(),
            _flight("arrival", Direction.ARRIVAL),
            _flight("departure", Direction.ARRIVAL),
        )


@pytest.mark.parametrize("mismatched_flight", ["arrival", "departure"])
def test_flight_tail_must_match_aircraft(mismatched_flight: str) -> None:
    aircraft = _aircraft()
    arrival_tail = "OTHER" if mismatched_flight == "arrival" else aircraft.tail
    departure_tail = "OTHER" if mismatched_flight == "departure" else aircraft.tail

    with pytest.raises(ValueError, match="tail must match"):
        TurnContext(
            "bad-tail",
            Turn(540, 600),
            aircraft,
            _flight("arrival", Direction.ARRIVAL, tail=arrival_tail),
            _flight("departure", Direction.DEPARTURE, tail=departure_tail),
        )


def test_duplicate_turn_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate turn_id"):
        derive_gate_domains([_context("same"), _context("same")], _gates())


def test_gate_input_order_is_preserved_and_inputs_are_not_modified() -> None:
    contexts = [_context()]
    gates = list(reversed(_gates()))
    original_contexts = contexts.copy()
    original_gates = gates.copy()

    result = derive_gate_domains(contexts, gates)

    assert _gate_ids(result[0]) == [gate.gate_id for gate in gates]
    assert contexts == original_contexts
    assert gates == original_gates
