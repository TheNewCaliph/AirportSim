"""Tests for the regional route network generator (aom.modules.rebooking.network)."""

from __future__ import annotations

import ast
import itertools
import random
from pathlib import Path

import pytest

from aom.modules.rebooking.network import (
    MINUTES_PER_DAY,
    Airport,
    NetworkConfig,
    Route,
    RouteNetwork,
    ScheduledFlight,
    clock,
    generate_network,
    great_circle_km,
)

SEEDS = range(15)


def snapshot(net: RouteNetwork) -> list[tuple[object, ...]]:
    return [
        (f.flight_id, f.number, f.airline, f.origin, f.dest, f.dep, f.arr, f.capacity)
        for f in net.flights
    ] + [(r.origin, r.dest, r.distance_km, r.block_minutes) for r in net.routes]


# ------------------------------------------------------------------- geometry


def test_great_circle_known_distances() -> None:
    assert great_circle_km(51.47, -0.4543, 40.6413, -73.7781) == pytest.approx(5540, abs=30)
    assert great_circle_km(10.0, 20.0, 10.0, 20.0) == 0.0
    # A quarter of the equator is a quarter of the circumference.
    assert great_circle_km(0, 0, 0, 90) == pytest.approx(2 * 3.141592653589793 * 6371.0088 / 4)


def test_great_circle_is_symmetric() -> None:
    rng = random.Random(3)
    for _ in range(200):
        a = (rng.uniform(-90, 90), rng.uniform(-180, 180))
        b = (rng.uniform(-90, 90), rng.uniform(-180, 180))
        assert great_circle_km(*a, *b) == pytest.approx(great_circle_km(*b, *a))


def test_clock_format() -> None:
    assert clock(0) == "00:00"
    assert clock(14 * 60 + 30) == "14:30"
    assert clock(MINUTES_PER_DAY + 7 * 60 + 5) == "07:05+1d"


# ------------------------------------------------------------------ catalogue


def test_airport_catalogue() -> None:
    net = generate_network()
    codes = [a.code for a in net.airports]
    assert len(codes) == len(net.airports) == 14
    for i, code in enumerate(codes):
        assert codes.index(code) == i  # unique
        assert net.airport_id(code) == i
    for a in net.airports:
        assert -90 <= a.lat <= 90 and -180 <= a.lon <= 180
    assert sorted(a.code for a in net.airports if a.is_hub) == [
        "AUH",
        "DOH",
        "DXB",
        "IST",
    ]
    with pytest.raises(KeyError):
        net.airport_id("XXX")


# -------------------------------------------------------------- network shape


@pytest.mark.parametrize("seed", SEEDS)
def test_routes_are_symmetric_and_consistent(seed: int) -> None:
    net = generate_network(NetworkConfig(seed=seed))
    assert net.is_connected()
    for r in net.routes:
        assert r.origin != r.dest
        a, b = net.airports[r.origin], net.airports[r.dest]
        assert r.distance_km == pytest.approx(great_circle_km(a.lat, a.lon, b.lat, b.lon))
        back = net.route(r.dest, r.origin)
        assert back is not None
        assert back.distance_km == r.distance_km and back.block_minutes == r.block_minutes
        assert net.route(r.origin, r.dest) is r
    # No pair is served twice in the same direction.
    for i, r in enumerate(net.routes):
        for s in net.routes[i + 1 :]:
            assert (r.origin, r.dest) != (s.origin, s.dest)
    assert net.graph.num_vertices == len(net.airports)
    assert net.graph.num_edges == len(net.routes)


def test_hubs_are_fully_joined_and_trunk_routes_exist() -> None:
    net = generate_network()
    hubs = [i for i, a in enumerate(net.airports) if a.is_hub]
    for a in hubs:
        for b in hubs:
            if a != b:
                assert net.route(a, b) is not None
    khi, lhr = net.airport_id("KHI"), net.airport_id("LHR")
    assert net.route(khi, lhr) is not None  # the direct long-haul option
    assert net.route(khi, net.airport_id("DOH")) is not None  # and the Doha option
    assert net.route(net.airport_id("DOH"), lhr) is not None


def test_block_time_is_physically_plausible() -> None:
    for seed in SEEDS:
        net = generate_network(NetworkConfig(seed=seed))
        for r in net.routes:
            speed = r.distance_km / (r.block_minutes / 60)
            assert speed <= net.max_speed_kmh + 1e-9
            assert r.block_minutes >= 40 and r.block_minutes % 5 == 0
        assert any(
            r.distance_km / (r.block_minutes / 60) == pytest.approx(net.max_speed_kmh)
            for r in net.routes
        )
        assert 500 < net.max_speed_kmh < 900  # never faster than a real airliner


# ------------------------------------------------------------------ timetable


@pytest.mark.parametrize("seed", SEEDS)
def test_flights_are_consistent(seed: int) -> None:
    cfg = NetworkConfig(seed=seed)
    net = generate_network(cfg)
    last = cfg.last_departure + (cfg.days - 1) * MINUTES_PER_DAY
    for i, f in enumerate(net.flights):
        assert f.flight_id == i
        route = net.route(f.origin, f.dest)
        assert route is not None
        assert f.arr - f.dep == route.block_minutes
        assert cfg.first_departure - 5 <= f.dep <= last + 5
        assert f.seats_free == f.capacity and f.capacity in {
            120,
            150,
            180,
            220,
            250,
            280,
            320,
            360,
        }
        origin, dest = net.airports[f.origin], net.airports[f.dest]
        assert f.airline in (origin.carrier, dest.carrier)
        assert f.number.startswith(f.airline)


@pytest.mark.parametrize("seed", SEEDS)
def test_every_route_has_daily_service_and_it_repeats(seed: int) -> None:
    cfg = NetworkConfig(seed=seed, days=3)
    net = generate_network(cfg)
    per_day = len(net.flights) // 3
    for r in net.routes:
        for day in range(3):
            lo, hi = day * MINUTES_PER_DAY, (day + 1) * MINUTES_PER_DAY
            n = sum(
                1
                for f in net.flights
                if (f.origin, f.dest) == (r.origin, r.dest) and lo <= f.dep < hi
            )
            assert n >= 1
    # Day d+1 repeats day d exactly: same numbers, same times of day, same seats.
    for i in range(per_day):
        f0, f1 = net.flights[i], net.flights[i + per_day]
        assert (f1.number, f1.origin, f1.dest, f1.capacity) == (
            f0.number,
            f0.origin,
            f0.dest,
            f0.capacity,
        )
        assert f1.dep == f0.dep + MINUTES_PER_DAY and f1.arr == f0.arr + MINUTES_PER_DAY


def test_default_day_is_about_the_size_of_the_m1_day() -> None:
    net = generate_network()
    per_day = len(net.flights) // 2
    assert 150 <= per_day <= 350


def test_flight_numbers_identify_a_flight_within_a_day() -> None:
    net = generate_network()
    per_day = len(net.flights) // 2
    numbers = [f.number for f in net.flights[:per_day]]
    for i, n in enumerate(numbers):
        assert numbers.index(n) == i


def test_frequency_scale_changes_traffic() -> None:
    light = generate_network(NetworkConfig(frequency_scale=0.4))
    heavy = generate_network(NetworkConfig(frequency_scale=2.0))
    assert len(light.flights) < len(generate_network().flights) < len(heavy.flights)
    for r in light.routes:  # even the lightest network keeps one flight a day
        assert any((f.origin, f.dest) == (r.origin, r.dest) for f in light.flights)


# ---------------------------------------------------------------- determinism


def test_same_seed_gives_identical_network() -> None:
    assert snapshot(generate_network(NetworkConfig(seed=7))) == snapshot(
        generate_network(NetworkConfig(seed=7))
    )


def test_different_seeds_differ() -> None:
    assert snapshot(generate_network(NetworkConfig(seed=1))) != snapshot(
        generate_network(NetworkConfig(seed=2))
    )


# ------------------------------------------------------------------- lookups


@pytest.mark.parametrize("seed", range(5))
def test_flights_from_sorted_and_complete(seed: int) -> None:
    net = generate_network(NetworkConfig(seed=seed))
    total = 0
    for a in range(len(net.airports)):
        fl = net.flights_from(a)
        total += len(fl)
        assert all(f.origin == a for f in fl)
        assert all(x.dep <= y.dep for x, y in itertools.pairwise(fl))
    assert total == len(net.flights)


@pytest.mark.parametrize("seed", range(5))
def test_departures_from_matches_linear_filter(seed: int) -> None:
    """Oracle: filter the full flight list, ordered by (departure, id)."""
    rng = random.Random(seed)
    net = generate_network(NetworkConfig(seed=seed))
    for _ in range(150):
        a = rng.randrange(len(net.airports))
        ready = rng.randrange(-60, 3 * MINUTES_PER_DAY)
        expected = sorted(
            (f for f in net.flights if f.origin == a and f.dep >= ready),
            key=lambda f: (f.dep, f.flight_id),
        )
        got = list(net.departures_from(a, ready))
        assert [f.flight_id for f in got] == [f.flight_id for f in expected]


def test_departures_from_edges() -> None:
    net = generate_network()
    a = net.airport_id("KHI")
    assert len(list(net.departures_from(a, 0))) == len(net.flights_from(a))
    assert list(net.departures_from(a, 10 * MINUTES_PER_DAY)) == []
    first = net.flights_from(a)[0]
    assert next(net.departures_from(a, first.dep)) is first  # "at or after" is inclusive


# ----------------------------------------------------------- hand-built toys


def test_hand_built_toy_network() -> None:
    airports = [
        Airport("AAA", "A", "XX", 0.0, 0.0, "XA", False),
        Airport("BBB", "B", "XX", 0.0, 10.0, "XB", False),
    ]
    routes = [Route(0, 1, 1111.0, 90), Route(1, 0, 1111.0, 90)]
    flights = [
        ScheduledFlight(0, "XA1", "XA", 0, 1, 600, 690, 100, 100),
        ScheduledFlight(1, "XB1", "XB", 1, 0, 500, 590, 100, 100),
        ScheduledFlight(2, "XA2", "XA", 0, 1, 300, 390, 100, 100),
    ]
    net = RouteNetwork(airports, routes, flights)
    assert [f.number for f in net.flights_from(0)] == ["XA2", "XA1"]
    assert net.max_speed_kmh == pytest.approx(1111.0 / 1.5)
    assert net.is_connected()
    with pytest.raises(ValueError):
        RouteNetwork(airports, routes, [ScheduledFlight(5, "X", "XA", 0, 1, 1, 2, 1, 1)])


# ------------------------------------------------------------------- config


@pytest.mark.parametrize(
    "bad",
    [
        {"days": 0},
        {"first_departure": -1},
        {"first_departure": 600, "last_departure": 600},
        {"last_departure": 1440},
        {"hub_links": 0},
        {"frequency_scale": 0.0},
    ],
)
def test_config_validation(bad: dict[str, int | float]) -> None:
    with pytest.raises(ValueError):
        NetworkConfig(**bad)  # type: ignore[arg-type]


# ------------------------------------------------------------ project rules


def test_source_avoids_banned_builtins() -> None:
    """M3 keeps its data in lists, the core graph and dataclasses only."""
    src = Path(__file__).resolve().parents[3] / "aom" / "modules" / "rebooking" / "network.py"
    tree = ast.parse(src.read_text())
    banned_calls = {
        "dict",
        "set",
        "frozenset",
        "defaultdict",
        "deque",
        "Counter",
        "sorted",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in {"heapq", "collections", "queue"}, alias.name
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls, node.func.id
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr != "sort"
        assert not isinstance(node, ast.Dict | ast.Set | ast.DictComp | ast.SetComp)
