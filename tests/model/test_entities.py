"""Unit tests for the shared records."""

import pytest

from aom.model.entities import (
    Aircraft,
    AircraftSize,
    Direction,
    Event,
    EventKind,
    FareClass,
    Flight,
    FlightStatus,
    Passenger,
    clock,
)


def _flight(**changes: object) -> Flight:
    fields: dict[str, object] = {
        "flight_id": "PK301",
        "airline": "PK",
        "tail": "AP-BAA",
        "origin": "KHI",
        "destination": "LHE",
        "direction": Direction.DEPARTURE,
        "sched_dep": 900,
        "sched_arr": 1005,
        "international": False,
        "capacity": 174,
    }
    fields.update(changes)
    return Flight(**fields)  # type: ignore[arg-type]


def test_clock_formatting() -> None:
    assert clock(0) == "00:00"
    assert clock(905) == "15:05"
    assert clock(1440 + 30) == "00:30+1"
    assert clock(-60) == "23:00-1"


def test_flight_estimates_start_at_schedule() -> None:
    f = _flight()
    assert f.est_dep == 900
    assert f.est_arr == 1005
    assert f.status is FlightStatus.SCHEDULED
    assert f.delay == 0
    assert f.local_time == 900
    assert not f.is_arrival


def test_flight_delay_is_measured_at_home() -> None:
    dep = _flight()
    dep.est_dep += 25
    assert dep.delay == 25
    arr = _flight(
        flight_id="PK300",
        origin="LHE",
        destination="KHI",
        direction=Direction.ARRIVAL,
        sched_dep=600,
        sched_arr=705,
    )
    arr.est_arr = 700  # early is not negative delay
    assert arr.local_time == 705
    assert arr.delay == 0


def test_flight_rejects_arrival_before_departure() -> None:
    with pytest.raises(ValueError):
        _flight(sched_arr=900)


def test_manifest_counts_seats() -> None:
    f = _flight(capacity=3)
    f.manifest.append("ABC234")
    f.manifest.append("XYZ789")
    assert f.booked == 2
    assert f.seats_free == 1


def test_slots_catch_typos() -> None:
    f = _flight()
    with pytest.raises(AttributeError):
        f.est_dpe = 5  # type: ignore[attr-defined]


def test_aircraft_passenger_event() -> None:
    a = Aircraft("A6-EAA", "EK", "B777", AircraftSize.WIDE, 354, 75)
    assert a.is_wide_body
    p = Passenger("7KQ2LM", FareClass.BUSINESS, "DXB", "LHE", ("EK600", "PK305"))
    assert p.is_connecting
    assert p.is_business
    assert not p.special_assistance
    e = Event(870, EventKind.CANCELLATION, "PK785", "storm")
    assert e.kind is EventKind.CANCELLATION
