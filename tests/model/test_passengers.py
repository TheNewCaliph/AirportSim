"""Tests for passengers, classes and manifests."""

from __future__ import annotations

import pytest

from aom.model.generator import generate_day
from aom.model.passengers import PassengerConfig, pnr_for
from aom.model.state import AirportState


@pytest.fixture(scope="module", params=[7, 2026])
def day(request: pytest.FixtureRequest) -> AirportState:
    return generate_day(request.param)


def test_loads_between_70_and_95_percent(day: AirportState) -> None:
    for f in day.flights:
        load = f.booked / f.capacity
        assert 0.69 <= load <= 0.96, f"{f.flight_id} load {load:.2f}"
        assert f.seats_free >= 0


def test_manifests_match_itineraries(day: AirportState) -> None:
    on_manifests = sum(f.booked for f in day.flights)
    seats_used = sum(len(p.itinerary) for p in day.passengers)
    assert on_manifests == seats_used
    for p in list(day.passengers)[::50]:
        for fid in p.itinerary:
            assert p.pnr in day.flight(fid).manifest


def test_pnrs_unique(day: AirportState) -> None:
    pnrs = [p.pnr for p in day.passengers]
    assert len(set(pnrs)) == len(pnrs)
    assert all(len(code) == 6 for code in pnrs[:100])


def test_mix_of_classes_and_connections(day: AirportState) -> None:
    n = len(day.passengers)
    business = sum(p.is_business for p in day.passengers) / n
    connecting = sum(p.is_connecting for p in day.passengers) / n
    assistance = sum(p.special_assistance for p in day.passengers) / n
    assert 0.08 <= business <= 0.12
    assert 0.12 <= connecting <= 0.28
    assert 0.01 <= assistance <= 0.03


def test_connections_are_feasible(day: AirportState) -> None:
    config = PassengerConfig()
    for p in day.passengers:
        if not p.is_connecting:
            continue
        inbound, onward = (day.flight(fid) for fid in p.itinerary)
        assert inbound.is_arrival and not onward.is_arrival
        gap = onward.sched_dep - inbound.sched_arr
        assert config.min_connection <= gap <= config.max_connection
        assert onward.destination != inbound.origin
        assert (p.origin, p.destination) == (inbound.origin, onward.destination)


def test_schedule_unchanged_by_passenger_settings() -> None:
    a = generate_day(11)
    b = generate_day(11, passengers=PassengerConfig(connect_share=0.0))
    assert [str(f) for f in a.flights] == [str(f) for f in b.flights]
    assert not any(p.is_connecting for p in b.passengers)


def test_pnr_codes_are_distinct_for_consecutive_numbers() -> None:
    codes = [pnr_for(i, 12345) for i in range(10_000)]
    assert len(set(codes)) == len(codes)
