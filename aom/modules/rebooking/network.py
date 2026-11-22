"""Regional route network and timetable generator (M3).

Builds the world the rebooking search runs in: a fixed catalogue of regional
airports, a route network joining them, and a seeded timetable of timed
flights with seats. A passenger stranded by a cancellation is rebooked by
searching this network (see the search problem, built on top of this module).

Model
-----
* **Airports** are the places. Four are hubs (DXB, DOH, AUH, IST). Hubs are
  joined to each other, every other airport is joined to its nearest hubs,
  and a list of direct "trunk" routes (KHI-LHR, KHI-JED, BKK-SIN, ...) adds
  point-to-point service. Every route exists in both directions, so the
  network is always connected.
* **Routes** are static: distance and block time are fixed per route.
* **Flights** are the timed roads. A route's daily pattern (departure times,
  aircraft size, airline, flight number) repeats on every simulated day.
* **Time** is whole minutes since 00:00 on day 0, on one clock for the whole
  network (time zones are ignored). Arrivals past 1440 fall on the next day.

Determinism
-----------
Everything random comes from ``random.Random(config.seed)``, drawn in a fixed
order, and nothing iterates a hash container. The same configuration always
gives the same network.

Structures
----------
Routes live in a :class:`aom.core.graph.Graph`. Flights are kept in
per-airport lists ordered by departure time, filled by a hand-written binary
search insert and queried by a hand-written binary search; no built-in sort,
``dict`` or ``set`` is used. Airport-code lookup is a linear scan over about
fourteen airports; it can move to the core hash table once that lands.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass

from aom.core.graph import Graph

MINUTES_PER_DAY = 1440
EARTH_RADIUS_KM = 6371.0088

# code, city, country, latitude, longitude, flag carrier, is_hub
_AIRPORT_ROWS: tuple[tuple[str, str, str, float, float, str, bool], ...] = (
    ("KHI", "Karachi", "PK", 24.9065, 67.1608, "PK", False),
    ("LHE", "Lahore", "PK", 31.5216, 74.4036, "PK", False),
    ("ISB", "Islamabad", "PK", 33.5605, 72.8526, "PK", False),
    ("DXB", "Dubai", "AE", 25.2532, 55.3657, "EK", True),
    ("DOH", "Doha", "QA", 25.2731, 51.6081, "QR", True),
    ("AUH", "Abu Dhabi", "AE", 24.4330, 54.6511, "EY", True),
    ("IST", "Istanbul", "TR", 41.2753, 28.7519, "TK", True),
    ("JED", "Jeddah", "SA", 21.6796, 39.1565, "SV", False),
    ("RUH", "Riyadh", "SA", 24.9576, 46.6988, "SV", False),
    ("LHR", "London", "GB", 51.4700, -0.4543, "BA", False),
    ("MAN", "Manchester", "GB", 53.3537, -2.2750, "BA", False),
    ("BKK", "Bangkok", "TH", 13.6900, 100.7501, "TG", False),
    ("KUL", "Kuala Lumpur", "MY", 2.7456, 101.7072, "MH", False),
    ("SIN", "Singapore", "SG", 1.3644, 103.9915, "SQ", False),
)

# Direct point-to-point routes between non-hub airports:
# (code, code, fewest daily departures each way, most daily departures each way)
_TRUNK_ROWS: tuple[tuple[str, str, int, int], ...] = (
    ("KHI", "LHE", 4, 6),
    ("KHI", "ISB", 3, 5),
    ("KHI", "LHR", 1, 2),
    ("KHI", "MAN", 1, 1),
    ("LHE", "LHR", 1, 2),
    ("ISB", "LHR", 1, 2),
    ("LHE", "MAN", 1, 1),
    ("KHI", "JED", 1, 3),
    ("KHI", "RUH", 1, 2),
    ("LHE", "JED", 1, 2),
    ("ISB", "JED", 1, 2),
    ("KHI", "BKK", 1, 2),
    ("KHI", "KUL", 1, 1),
    ("BKK", "KUL", 2, 4),
    ("BKK", "SIN", 2, 4),
    ("KUL", "SIN", 3, 5),
    ("JED", "RUH", 3, 5),
)

_HUB_HUB_FREQUENCY = (3, 5)
_SPOKE_HUB_FREQUENCY = (1, 3)

_BLOCK_OVERHEAD_MIN = 35  # taxi, climb and approach on top of cruise time
_MIN_BLOCK_MIN = 40


# --------------------------------------------------------------------- records


@dataclass(frozen=True, slots=True)
class Airport:
    """A place in the network."""

    code: str
    city: str
    country: str
    lat: float
    lon: float
    carrier: str  # flag carrier's two-letter code
    is_hub: bool


@dataclass(frozen=True, slots=True)
class Route:
    """A one-way connection between two airports, by airport id."""

    origin: int
    dest: int
    distance_km: float
    block_minutes: int


@dataclass(slots=True)
class ScheduledFlight:
    """One timed flight. ``seats_free`` falls as passengers are booked."""

    flight_id: int  # unique; equals the flight's index in ``RouteNetwork.flights``
    number: str  # e.g. "PK301"; the same number flies every day
    airline: str
    origin: int
    dest: int
    dep: int  # minutes since 00:00 on day 0
    arr: int
    capacity: int
    seats_free: int


@dataclass(frozen=True, slots=True)
class NetworkConfig:
    """Knobs for :func:`generate_network`."""

    seed: int = 0
    days: int = 2  # timetable length; 2 lets a 14:30 cancellation see tomorrow
    first_departure: int = 5 * 60
    last_departure: int = 23 * 60
    hub_links: int = 3  # each non-hub airport is joined to this many nearest hubs
    frequency_scale: float = 1.0  # multiplies every route's daily departures

    def __post_init__(self) -> None:
        if self.days < 1:
            raise ValueError("days must be at least 1")
        if not 0 <= self.first_departure < self.last_departure < MINUTES_PER_DAY:
            raise ValueError("need 0 <= first_departure < last_departure < 1440")
        if self.hub_links < 1:
            raise ValueError("hub_links must be at least 1")
        if self.frequency_scale <= 0:
            raise ValueError("frequency_scale must be positive")


# -------------------------------------------------------------------- geometry


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two points in degrees, in km. O(1)."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def clock(minute: int) -> str:
    """Format network minutes as ``HH:MM``, with ``+Nd`` after day 0. O(1)."""
    day, rest = divmod(minute, MINUTES_PER_DAY)
    text = f"{rest // 60:02d}:{rest % 60:02d}"
    return text if day == 0 else f"{text}+{day}d"


# --------------------------------------------------------------------- network


class RouteNetwork:
    """Airports, routes and a timetable, with the lookups the search needs.

    Build one with :func:`generate_network`, or directly from hand-made lists
    (for a toy network in tests). Flight ids must equal list positions.
    """

    def __init__(
        self,
        airports: list[Airport],
        routes: list[Route],
        flights: list[ScheduledFlight],
    ) -> None:
        """Index the given records. O(A + R + F log F)."""
        self.airports = airports
        self.routes = routes
        self.flights = flights
        self.graph: Graph[str, Route] = Graph(directed=True)
        for airport in airports:
            self.graph.add_vertex(airport.code)
        for route in routes:
            self.graph.add_edge(route.origin, route.dest, route)
        self._by_origin: list[list[ScheduledFlight]] = [[] for _ in airports]
        for position, flight in enumerate(flights):
            if flight.flight_id != position:
                raise ValueError("flight_id must equal the flight's list position")
            _insert_by_departure(self._by_origin[flight.origin], flight)
        fastest = 0.0
        for route in routes:
            speed = route.distance_km / (route.block_minutes / 60)
            fastest = max(fastest, speed)
        self.max_speed_kmh = fastest

    def airport_id(self, code: str) -> int:
        """Id of the airport with this code. O(A).

        Raises:
            KeyError: if no airport has that code.
        """
        for i, airport in enumerate(self.airports):
            if airport.code == code:
                return i
        raise KeyError(code)

    def route(self, origin: int, dest: int) -> Route | None:
        """The route ``origin -> dest``, or ``None``. O(out-degree of origin)."""
        for edge in self.graph.out_edges(origin):
            if edge.target == dest:
                return edge.data
        return None

    def flights_from(self, airport: int) -> list[ScheduledFlight]:
        """All flights leaving ``airport``, ordered by departure time.

        Returns the internal list; do not modify it. O(1).
        """
        return self._by_origin[airport]

    def departures_from(self, airport: int, ready: int) -> Iterator[ScheduledFlight]:
        """Flights leaving ``airport`` at or after minute ``ready``, in order.

        O(log F_a) to find the start, then O(1) per flight yielded.
        """
        flights = self._by_origin[airport]
        for i in range(_first_at_or_after(flights, ready), len(flights)):
            yield flights[i]

    def is_connected(self) -> bool:
        """True if every airport can reach every other. O(A + R).

        Routes come in pairs, so reaching everything from airport 0 is enough.
        """
        if not self.airports:
            return True
        return all(d != -1 for d in self.graph.bfs(0).dist)


def _insert_by_departure(
    flights: list[ScheduledFlight], flight: ScheduledFlight
) -> None:
    """Insert after any flight with an equal or earlier departure. O(n)."""
    lo, hi = 0, len(flights)
    while lo < hi:
        mid = (lo + hi) // 2
        if flights[mid].dep <= flight.dep:
            lo = mid + 1
        else:
            hi = mid
    flights.insert(lo, flight)


def _first_at_or_after(flights: list[ScheduledFlight], minute: int) -> int:
    """Index of the first flight departing at or after ``minute``. O(log n)."""
    lo, hi = 0, len(flights)
    while lo < hi:
        mid = (lo + hi) // 2
        if flights[mid].dep < minute:
            lo = mid + 1
        else:
            hi = mid
    return lo


# ------------------------------------------------------------------- generator


def generate_network(config: NetworkConfig | None = None) -> RouteNetwork:
    """Generate the regional network and its timetable from ``config.seed``.

    Time O(P log F + F) for P route pairs and F flights; the same
    configuration always returns the same network.
    """
    cfg = config if config is not None else NetworkConfig()
    rng = random.Random(cfg.seed)
    airports = [Airport(*row) for row in _AIRPORT_ROWS]

    plan = _plan_route_pairs(airports, cfg.hub_links)

    routes: list[Route] = []
    templates: list[_Template] = []
    carriers: list[str] = []
    for airport in airports:
        if airport.carrier not in carriers:
            carriers.append(airport.carrier)
    counters = [100] * len(carriers)

    for a, b, lo, hi in plan:
        km = great_circle_km(
            airports[a].lat, airports[a].lon, airports[b].lat, airports[b].lon
        )
        speed = rng.uniform(720.0, 850.0)
        block = max(_MIN_BLOCK_MIN, _round5(_BLOCK_OVERHEAD_MIN + km / speed * 60))
        routes.append(Route(a, b, km, block))
        routes.append(Route(b, a, km, block))
        for origin, dest in ((a, b), (b, a)):
            n = max(1, round(rng.randint(lo, hi) * cfg.frequency_scale))
            span = cfg.last_departure - cfg.first_departure
            slot = span / n
            for k in range(n):
                centre = cfg.first_departure + slot * (k + 0.5)
                dep = _round5(centre + rng.uniform(-slot / 3, slot / 3))
                airline = (
                    airports[origin].carrier
                    if rng.random() < 0.5
                    else airports[dest].carrier
                )
                ci = carriers.index(airline)
                number = f"{airline}{counters[ci]}"
                counters[ci] += 1
                templates.append(
                    _Template(
                        origin,
                        dest,
                        dep,
                        dep + block,
                        airline,
                        number,
                        _capacity(rng, km),
                    )
                )

    flights: list[ScheduledFlight] = []
    for day in range(cfg.days):
        offset = day * MINUTES_PER_DAY
        for t in templates:
            flights.append(
                ScheduledFlight(
                    flight_id=len(flights),
                    number=t.number,
                    airline=t.airline,
                    origin=t.origin,
                    dest=t.dest,
                    dep=t.dep + offset,
                    arr=t.arr + offset,
                    capacity=t.capacity,
                    seats_free=t.capacity,
                )
            )
    return RouteNetwork(airports, routes, flights)


@dataclass(frozen=True, slots=True)
class _Template:
    """A flight's daily pattern, before it is repeated over the days."""

    origin: int
    dest: int
    dep: int
    arr: int
    airline: str
    number: str
    capacity: int


def _plan_route_pairs(
    airports: list[Airport], hub_links: int
) -> list[tuple[int, int, int, int]]:
    """Choose which airport pairs get service: (a, b, min/day, max/day)."""
    plan: list[tuple[int, int, int, int]] = []
    hubs = [i for i, a in enumerate(airports) if a.is_hub]
    for x in range(len(hubs)):
        for y in range(x + 1, len(hubs)):
            plan.append((hubs[x], hubs[y], *_HUB_HUB_FREQUENCY))
    for i, airport in enumerate(airports):
        if airport.is_hub:
            continue
        # Pick the nearest hubs by repeated selection (no sort needed).
        remaining = [
            (
                great_circle_km(
                    airport.lat, airport.lon, airports[h].lat, airports[h].lon
                ),
                h,
            )
            for h in hubs
        ]
        for _ in range(min(hub_links, len(remaining))):
            best = 0
            for j in range(1, len(remaining)):
                if remaining[j][0] < remaining[best][0]:
                    best = j
            _, hub = remaining.pop(best)
            plan.append((i, hub, *_SPOKE_HUB_FREQUENCY))
    for code_a, code_b, lo, hi in _TRUNK_ROWS:
        a = _index_of(airports, code_a)
        b = _index_of(airports, code_b)
        if not _has_pair(plan, a, b):
            plan.append((a, b, lo, hi))
    return plan


def _index_of(airports: list[Airport], code: str) -> int:
    for i, airport in enumerate(airports):
        if airport.code == code:
            return i
    raise KeyError(code)


def _has_pair(plan: list[tuple[int, int, int, int]], a: int, b: int) -> bool:
    for x, y, _, _ in plan:
        if (x == a and y == b) or (x == b and y == a):
            return True
    return False


def _round5(minutes: float) -> int:
    return round(minutes / 5.0) * 5


def _capacity(rng: random.Random, km: float) -> int:
    """Seats by stage length: narrow-body short, wide-body long."""
    if km < 1800:
        return rng.choice((120, 150, 180))
    if km < 4500:
        return rng.choice((180, 220, 250))
    return rng.choice((280, 320, 360))