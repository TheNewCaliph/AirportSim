"""Tests for the seeded schedule generator."""

from __future__ import annotations

import pytest

from aom.model.entities import Direction
from aom.model.generator import DayConfig, build_gates, generate_schedule
from aom.model.state import AirportState

SEEDS = [1, 7, 42, 2026]


@pytest.fixture(scope="module", params=SEEDS)
def day(request: pytest.FixtureRequest) -> AirportState:
    return generate_schedule(request.param)


def test_exactly_n_flights(day: AirportState) -> None:
    assert len(day.flights) == 200
    ids = [f.flight_id for f in day.flights]
    assert len(set(ids)) == len(ids)


def test_home_movements_inside_operating_hours(day: AirportState) -> None:
    config = DayConfig()
    for f in day.flights:
        assert config.first_minute <= f.local_time <= config.last_minute, str(f)
        assert f.sched_arr > f.sched_dep


def test_rotations_alternate_and_respect_turn_times(day: AirportState) -> None:
    for aircraft in day.aircraft:
        legs = day.rotation(aircraft.tail)
        assert 1 <= len(legs) <= 4
        for prev, nxt in zip(legs, list(legs)[1:], strict=False):
            assert prev.direction is not nxt.direction
            if prev.direction is Direction.ARRIVAL:
                # ground time at home is at least the aircraft's minimum turn
                assert nxt.sched_dep - prev.sched_arr >= aircraft.min_turn
                assert nxt.origin == day.code
            else:
                # it comes back from where it went
                assert nxt.origin == prev.destination
                assert nxt.sched_dep - prev.sched_arr >= aircraft.min_turn


def test_capacity_matches_aircraft(day: AirportState) -> None:
    for f in day.flights:
        assert f.capacity == day.aircraft_by_tail(f.tail).seats


def test_wide_bodies_fly_long_routes_only(day: AirportState) -> None:
    for f in day.flights:
        if day.aircraft_by_tail(f.tail).is_wide_body:
            assert f.international


def test_departures_cluster_at_peaks(day: AirportState) -> None:
    def in_hours(lo: int, hi: int) -> int:
        return sum(1 for f in day.departures() if lo * 60 <= f.sched_dep < hi * 60)

    morning, midday, evening = in_hours(7, 10), in_hours(12, 15), in_hours(18, 21)
    assert morning > midday
    assert evening > midday


def test_gates_by_terminal() -> None:
    gates = build_gates(DayConfig())
    assert len(gates) == 22
    assert all(not g.customs and not g.wide_body for g in gates if g.terminal == "A")
    assert all(g.customs and not g.wide_body for g in gates if g.terminal == "B")
    assert all(g.customs and g.wide_body for g in gates if g.terminal == "C")


def test_config_changes_flight_count() -> None:
    small = generate_schedule(3, DayConfig(n_flights=40))
    assert len(small.flights) == 40
