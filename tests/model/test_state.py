"""Unit tests for AirportState."""

import pytest

from aom.model.entities import Aircraft, AircraftSize, Direction, Flight, Gate, Passenger
from aom.model.entities import FareClass as Fare
from aom.model.state import AirportState


def _state() -> AirportState:
    s = AirportState("KHI", seed=1)
    s.add_gate(Gate("A1", "A", False, False))
    s.add_gate(Gate("C1", "C", True, True))
    s.add_aircraft(Aircraft("AP-BAA", "PK", "A320", AircraftSize.NARROW, 174, 40))
    s.add_flight(
        Flight("PK300", "PK", "AP-BAA", "LHE", "KHI", Direction.ARRIVAL, 600, 705, False, 174)
    )
    s.add_flight(
        Flight("PK301", "PK", "AP-BAA", "KHI", "ISB", Direction.DEPARTURE, 760, 880, False, 174)
    )
    return s


def test_lookups_by_id() -> None:
    s = _state()
    assert s.flight("PK301").destination == "ISB"
    assert s.gate("C1").wide_body
    assert s.aircraft_by_tail("AP-BAA").seats == 174
    for lookup in (s.flight, s.gate, s.aircraft_by_tail, s.passenger):
        with pytest.raises(KeyError):
            lookup("nope")


def test_rejects_duplicates_and_bad_flights() -> None:
    s = _state()
    with pytest.raises(ValueError):
        s.add_gate(Gate("A1", "A", False, False))
    with pytest.raises(ValueError):
        s.add_aircraft(Aircraft("AP-BAA", "PK", "A320", AircraftSize.NARROW, 174, 40))
    with pytest.raises(ValueError, match="duplicate"):
        s.add_flight(
            Flight("PK301", "PK", "AP-BAA", "KHI", "ISB", Direction.DEPARTURE, 1, 9, False, 9)
        )
    with pytest.raises(ValueError, match="does not touch"):
        s.add_flight(
            Flight("PK9", "PK", "AP-BAA", "LHE", "ISB", Direction.DEPARTURE, 1, 9, False, 9)
        )
    with pytest.raises(ValueError, match="direction"):
        s.add_flight(Flight("PK8", "PK", "AP-BAA", "KHI", "ISB", Direction.ARRIVAL, 1, 9, False, 9))
    with pytest.raises(ValueError, match="unknown aircraft"):
        s.add_flight(
            Flight("PK7", "PK", "AP-XXX", "KHI", "ISB", Direction.DEPARTURE, 1, 9, False, 9)
        )


def test_views() -> None:
    s = _state()
    assert [f.flight_id for f in s.rotation("AP-BAA")] == ["PK300", "PK301"]
    assert [f.flight_id for f in s.arrivals()] == ["PK300"]
    assert [f.flight_id for f in s.departures()] == ["PK301"]
    assert "2 flights" in s.summary()


def test_passengers_are_shared_not_copied() -> None:
    s = _state()
    p = Passenger("ABC234", Fare.ECONOMY, "LHE", "ISB", ("PK300", "PK301"))
    s.add_passenger(p)
    assert s.passenger("ABC234") is p
    s.flight("PK300").est_arr += 30  # a change made through the state is seen everywhere
    assert s.flights[0].delay == 30
