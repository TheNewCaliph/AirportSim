"""Tests for the rebooking search problem with BFS and DFS (rebooking.search)."""

from __future__ import annotations

import ast
import itertools
import math
import random
from pathlib import Path

import pytest

from aom.modules.rebooking.network import (
    Airport,
    NetworkConfig,
    Route,
    RouteNetwork,
    ScheduledFlight,
    generate_network,
)
from aom.modules.rebooking.search import (
    DEFAULT_CONNECTION_PENALTY,
    DEFAULT_MIN_CONNECTION,
    RebookingProblem,
    RebookingRequest,
    SearchResult,
    bfs,
    dfs,
    format_itinerary,
)

# ----------------------------------------------------------------- toy network
# (number, origin, dest, dep, arr, free seats), times in minutes since 00:00 day 0.
KARACHI: list[tuple[str, str, str, int, int, int]] = [
    ("PK300", "KHI", "LHR", 900, 1440, 100),  # 15:00 -> 24:00, the cancelled flight
    ("PK302", "KHI", "LHR", 1500, 2040, 100),  # direct, tomorrow 01:00 -> 10:00
    ("TG1", "KHI", "BKK", 930, 1230, 100),  # earliest way out, but the wrong way
    ("QR605", "KHI", "DOH", 940, 1015, 100),  # 15:40 -> 16:55
    ("QR7", "DOH", "LHR", 1110, 1390, 100),  # 18:30 -> 23:10
    ("TG2", "BKK", "KUL", 1320, 1400, 100),
    ("MH1", "KUL", "SIN", 1450, 1500, 100),
    ("SQ1", "SIN", "LHR", 1560, 2100, 100),
]


def make_toy(specs: list[tuple[str, str, str, int, int, int]]) -> RouteNetwork:
    codes: list[str] = []
    for _, o, d, _, _, _ in specs:
        for c in (o, d):
            if c not in codes:
                codes.append(c)
    airports = [Airport(c, c, "XX", float(i), float(i), "XX", False) for i, c in enumerate(codes)]
    routes: list[Route] = []
    flights: list[ScheduledFlight] = []
    for i, (number, o, d, dep, arr, free) in enumerate(specs):
        oi, di = codes.index(o), codes.index(d)
        if not any(r.origin == oi and r.dest == di for r in routes):
            routes.append(Route(oi, di, 1000.0, max(40, arr - dep)))
        flights.append(ScheduledFlight(i, number, number[:2], oi, di, dep, arr, free, free))
    return RouteNetwork(airports, routes, flights)


def karachi_problem(
    *,
    cancelled: tuple[int, ...] = (0,),
    ready: int = 870,
    seats: int = 1,
    min_connection: int = DEFAULT_MIN_CONNECTION,
    specs: list[tuple[str, str, str, int, int, int]] | None = None,
) -> RebookingProblem:
    net = make_toy(specs if specs is not None else KARACHI)
    request = RebookingRequest(
        "7KQ2LM", net.airport_id("KHI"), net.airport_id("LHR"), ready, 1440, seats
    )
    return RebookingProblem(net, request, min_connection=min_connection, cancelled=cancelled)


def numbers(result: SearchResult) -> list[str]:
    return [f.number for f in result.route]


# ------------------------------------------------------------- the toy story


def test_bfs_returns_fewest_legs_even_if_it_arrives_much_later() -> None:
    """The guide's example: BFS picks the direct flight, tomorrow morning."""
    res = bfs(karachi_problem())
    assert numbers(res) == ["PK302"]
    assert res.legs == 1 and res.arrival == 2040
    assert res.lateness == 600
    assert res.cost == 2040 - 870  # no extra connections, so cost is elapsed time


def test_dfs_dives_down_the_earliest_path_and_returns_a_bad_route() -> None:
    res = dfs(karachi_problem())
    assert numbers(res) == ["TG1", "TG2", "MH1", "SQ1"]
    assert res.legs == 4 and res.arrival == 2100
    assert res.cost == (2100 - 870) + 3 * DEFAULT_CONNECTION_PENALTY
    # Worse on both counts than BFS, and far worse than the Doha route (cost 550).
    assert res.cost > bfs(karachi_problem()).cost > 550


def test_bfs_takes_the_doha_route_once_the_direct_flight_is_gone() -> None:
    res = bfs(karachi_problem(cancelled=(0, 1)))
    assert numbers(res) == ["QR605", "QR7"]
    assert res.arrival == 1390 and res.lateness == -50
    assert res.cost == (1390 - 870) + DEFAULT_CONNECTION_PENALTY


def test_cancelled_flight_is_never_used() -> None:
    for algorithm in (bfs, dfs):
        assert "PK300" not in numbers(algorithm(karachi_problem(cancelled=(0,))))
    # Without banning it, BFS takes the cancelled flight (it leaves 15:00, after 14:30).
    assert numbers(bfs(karachi_problem(cancelled=()))) == ["PK300"]


def test_flights_that_already_left_are_unusable() -> None:
    res = bfs(karachi_problem(ready=1100))  # QR605 and TG1 are gone
    assert numbers(res) == ["PK302"]
    assert not bfs(karachi_problem(ready=1600)).found  # nothing leaves KHI after 26:40


def test_minimum_connection_time_is_enforced() -> None:
    # QR605 lands 16:55 (1015); QR7 leaves 18:30 (1110): a 95 minute gap.
    ok = bfs(karachi_problem(cancelled=(0, 1), min_connection=95))
    assert numbers(ok) == ["QR605", "QR7"]
    too_tight = bfs(karachi_problem(cancelled=(0, 1), min_connection=96))
    assert not too_tight.found  # and the Bangkok chain misses its connection too


def test_seats_are_respected() -> None:
    specs = [(n, o, d, dep, arr, 1 if n == "QR7" else s) for n, o, d, dep, arr, s in KARACHI]
    # Block the direct flights and the Bangkok chain (SQ1) so Doha is the only way.
    blocked = (0, 1, 7)
    one = bfs(karachi_problem(cancelled=blocked, specs=specs, seats=1))
    assert numbers(one) == ["QR605", "QR7"]
    two = bfs(karachi_problem(cancelled=blocked, specs=specs, seats=2))  # QR7: one seat
    assert not two.found


def test_no_route_found_result() -> None:
    # Ban both direct flights, QR7 and SQ1: no way to London remains.
    for algorithm in (bfs, dfs):
        res = algorithm(karachi_problem(cancelled=(0, 1, 4, 7)))
        assert not res.found and res.route == [] and res.cost == math.inf
        assert res.arrival is None and res.lateness is None
        assert res.stats.expanded >= 1
    # Leave QR7 usable and the Doha route is found again.
    assert bfs(karachi_problem(cancelled=(0, 1, 7))).found


def test_stats_are_recorded() -> None:
    res = bfs(karachi_problem())
    assert res.stats.expanded == 1  # the direct flight is a goal on the first expansion
    assert res.stats.generated >= 1 and res.stats.max_frontier >= 1
    deep = dfs(karachi_problem())
    assert deep.stats.max_frontier == 4  # start plus the three intermediate stops
    assert deep.stats.expanded >= 4


def test_format_itinerary() -> None:
    problem = karachi_problem(cancelled=(0, 1))
    text = format_itinerary(problem.network, bfs(problem))
    assert "2 leg(s)" in text and "QR605 KHI 15:40 -> DOH 16:55" in text
    assert "QR7 DOH 18:30 -> LHR 23:10" in text
    none = format_itinerary(problem.network, dfs(karachi_problem(cancelled=(0, 1, 4, 7))))
    assert none.endswith("no route found")


# ------------------------------------------------------------ problem object


def test_problem_validation() -> None:
    net = make_toy(KARACHI)
    with pytest.raises(ValueError):
        RebookingRequest("X", 0, 0, 0, 0)
    with pytest.raises(ValueError):
        RebookingRequest("X", 0, 1, 0, 0, seats=0)
    request = RebookingRequest("X", 0, 1, 0, 0)
    with pytest.raises(IndexError):
        RebookingProblem(net, RebookingRequest("X", 0, 99, 0, 0))
    with pytest.raises(IndexError):
        RebookingProblem(net, request, cancelled=[999])
    with pytest.raises(ValueError):
        RebookingProblem(net, request, min_connection=-1)
    with pytest.raises(ValueError):
        RebookingProblem(net, request, connection_penalty=-1)


def test_problem_successors_and_goal() -> None:
    p = karachi_problem()
    root = p.initial_node()
    assert not p.is_goal(root) and p.key(root) == len(p.network.flights)
    kids = list(p.successors(root))
    # Cancelled PK300 (dep 900) is skipped; the rest come in departure order.
    assert [k.flight.number for k in kids if k.flight] == ["TG1", "QR605", "PK302"]
    assert [p.is_goal(k) for k in kids] == [False, False, True]
    doha = kids[1]
    assert (doha.legs, doha.ready, doha.arrived) == (1, 1015 + 45, 1015)
    assert doha.cost == (1015 - 870) + DEFAULT_CONNECTION_PENALTY
    assert p.route_to(doha) == [doha.flight]
    assert p.route_to(root) == []


# ---------------------------------------------------- random tests with oracles


def valid_route(problem: RebookingProblem, route: list[ScheduledFlight]) -> bool:
    r = problem.request
    if not route or route[0].origin != r.origin or route[-1].dest != r.dest:
        return False
    if route[0].dep < r.ready:
        return False
    for prev, nxt in itertools.pairwise(route):
        if nxt.origin != prev.dest or nxt.dep < prev.arr + problem.min_connection:
            return False
    banned = {f.flight_id for f in problem.network.flights if problem._banned[f.flight_id]}
    return all(f.seats_free >= r.seats and f.flight_id not in banned for f in route)


def oracle_min_legs(problem: RebookingProblem) -> int | None:
    """Independent DP: fewest legs over every feasible itinerary, or None.

    Flights are processed by departure time. ``legs[f]`` is the fewest flights
    of any feasible itinerary that ends with flight ``f``.
    """
    r = problem.request
    net = problem.network
    usable = [
        f for f in net.flights if not problem._banned[f.flight_id] and f.seats_free >= r.seats
    ]
    usable.sort(key=lambda f: (f.dep, f.flight_id))
    best: list[tuple[ScheduledFlight, int]] = []
    answer: int | None = None
    for f in usable:
        legs: int | None = 1 if f.origin == r.origin and f.dep >= r.ready else None
        for g, g_legs in best:
            can_connect = g.dest == f.origin and g.arr + problem.min_connection <= f.dep
            if can_connect and (legs is None or g_legs + 1 < legs):
                legs = g_legs + 1
        if legs is not None:
            best.append((f, legs))
            if f.dest == r.dest and (answer is None or legs < answer):
                answer = legs
    return answer


@pytest.mark.parametrize("seed", range(6))
def test_matches_oracle_on_generated_networks(seed: int) -> None:
    rng = random.Random(seed)
    net = generate_network(NetworkConfig(seed=seed, days=2))
    for f in net.flights:  # some flights are full
        if rng.random() < 0.15:
            f.seats_free = rng.randrange(0, 3)
    for _ in range(8):
        origin, dest = rng.sample(range(len(net.airports)), 2)
        request = RebookingRequest(
            "TEST", origin, dest, rng.randrange(0, 1800), 0, seats=rng.choice((1, 1, 2))
        )
        cancelled = [rng.randrange(len(net.flights)) for _ in range(rng.randrange(0, 12))]
        problem = RebookingProblem(
            net,
            request,
            min_connection=rng.choice((30, 45, 90)),
            connection_penalty=rng.choice((0, 30, 120)),
            cancelled=cancelled,
        )
        expected = oracle_min_legs(problem)
        b, d = bfs(problem), dfs(problem)
        assert b.found == d.found == (expected is not None)
        if expected is None:
            assert b.cost == d.cost == math.inf
            continue
        assert valid_route(problem, b.route) and valid_route(problem, d.route)
        assert b.legs == expected  # BFS: fewest flights
        assert d.legs >= expected  # DFS: never fewer, often many more
        for res in (b, d):
            elapsed = res.route[-1].arr - request.ready
            assert res.cost == elapsed + problem.connection_penalty * (res.legs - 1)
            assert res.lateness == res.route[-1].arr - request.original_arrival
            assert res.stats.expanded >= 1 and res.stats.generated >= res.legs


def test_search_does_not_change_seat_counts() -> None:
    net = generate_network(NetworkConfig(seed=3))
    before = [f.seats_free for f in net.flights]
    problem = RebookingProblem(net, RebookingRequest("T", 0, 9, 600, 0))
    bfs(problem)
    dfs(problem)
    assert [f.seats_free for f in net.flights] == before


def test_dfs_is_not_limited_by_recursion_depth() -> None:
    """A long chain of single flights: DFS must follow it without recursing."""
    n = 3000
    specs = [(f"ZZ{i}", f"C{i}", f"C{i + 1}", 100 + 100 * i, 150 + 100 * i, 10) for i in range(n)]
    net = make_toy(specs)
    request = RebookingRequest("LONG", 0, n, 0, 0)
    for algorithm in (bfs, dfs):
        res = algorithm(RebookingProblem(net, request, min_connection=0))
        assert res.legs == n and valid_route(
            RebookingProblem(net, request, min_connection=0), res.route
        )


# ------------------------------------------------------------ project rules


def test_source_avoids_banned_builtins() -> None:
    src = Path(__file__).resolve().parents[3] / "aom" / "modules" / "rebooking" / "search.py"
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
