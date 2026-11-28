"""Time-dependent rebooking search problem, with BFS and DFS (M3).

A passenger is stranded at an airport at some minute (their flight was
cancelled) and must reach their destination. The network is a timetable, so
a flight only exists at one moment: a passenger ready at 17:00 cannot take a
flight that left at 16:30.

The search problem
------------------
* **State:** ``(airport, ready)``: where the passenger is and the earliest
  minute they can board again.
* **Move:** any later flight from that airport with enough free seats that
  has not been cancelled. It leads to ``(flight.dest, flight.arr + MCT)``,
  where MCT is the minimum connection time.
* **Goal:** the passenger's final airport.
* **Cost:** the time from being ready to arriving, waiting included, plus a
  penalty for every extra connection. Compared with "minutes late against the
  original plan, plus the same penalty", this differs only by a constant per
  passenger (their original lateness baseline), so both rank routes
  identically; this form is additive and never negative, which uniform-cost
  search and A* need. :attr:`SearchResult.lateness` reports the version
  measured against the original plan.

Why a list can serve as the visited table
-----------------------------------------
After taking a flight, the state ``(airport, ready)`` and the cost so far are
fixed by that flight alone (the airport is its destination and the ready time
is its arrival plus MCT). A flight id therefore names a state, and visited
marking is a list of booleans indexed by flight id. The start state gets one
extra slot at the end.

Searches only read seat counts; reserving seats is a separate step.

No ``dict``, ``set``, ``heapq`` or built-in sort is used here.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from aom.modules.rebooking.network import RouteNetwork, ScheduledFlight, clock

DEFAULT_MIN_CONNECTION = 45  # minutes needed to change planes
DEFAULT_CONNECTION_PENALTY = 30  # cost units per extra connection


# --------------------------------------------------------------------- records


@dataclass(frozen=True, slots=True)
class RebookingRequest:
    """One stranded booking that needs a new route."""

    pnr: str
    origin: int  # airport where the passenger is stranded
    dest: int  # final airport
    ready: int  # earliest minute they can board (the cancellation time)
    original_arrival: int  # when they were due to arrive; the lateness baseline
    seats: int = 1  # party size

    def __post_init__(self) -> None:
        if self.origin == self.dest:
            raise ValueError("origin and destination must differ")
        if self.seats < 1:
            raise ValueError("seats must be at least 1")


@dataclass(slots=True)
class SearchStats:
    """How much work a search did; used to compare algorithms."""

    expanded: int = 0  # nodes whose moves were examined
    generated: int = 0  # distinct states created
    max_frontier: int = 0  # largest queue (BFS) or stack depth (DFS)


@dataclass(slots=True)
class Node:
    """A search node: a state plus how it was reached."""

    airport: int
    ready: int  # earliest minute the passenger can board from here
    arrived: int  # actual arrival minute (equals ``ready`` at the start)
    legs: int
    cost: float
    flight: ScheduledFlight | None  # the flight that led here; None at the start
    parent: Node | None


@dataclass(slots=True)
class SearchResult:
    """The outcome of one search."""

    algorithm: str
    request: RebookingRequest
    route: list[ScheduledFlight]  # empty if no route was found
    cost: float  # math.inf if no route was found
    stats: SearchStats = field(default_factory=SearchStats)

    @property
    def found(self) -> bool:
        """True if a route to the destination exists. O(1)."""
        return len(self.route) > 0

    @property
    def legs(self) -> int:
        """Number of flights in the route. O(1)."""
        return len(self.route)

    @property
    def arrival(self) -> int | None:
        """Minute the passenger lands at the destination, or ``None``. O(1)."""
        return self.route[-1].arr if self.route else None

    @property
    def lateness(self) -> int | None:
        """Minutes after the original arrival time, or ``None``. O(1)."""
        arrival = self.arrival
        return None if arrival is None else arrival - self.request.original_arrival


# --------------------------------------------------------------------- problem


class RebookingProblem:
    """The rebooking search problem for one passenger on one timetable."""

    def __init__(
        self,
        network: RouteNetwork,
        request: RebookingRequest,
        *,
        min_connection: int = DEFAULT_MIN_CONNECTION,
        connection_penalty: int = DEFAULT_CONNECTION_PENALTY,
        cancelled: Iterable[int] = (),
    ) -> None:
        """Set up the problem. O(F) for F flights plus the cancelled ids.

        Args:
            cancelled: ids of flights that must not be used.

        Raises:
            IndexError: if an airport or cancelled flight id is out of range.
            ValueError: if ``min_connection`` or ``connection_penalty`` is negative.
        """
        count = len(network.airports)
        if not (0 <= request.origin < count and 0 <= request.dest < count):
            raise IndexError("request airport out of range")
        if min_connection < 0 or connection_penalty < 0:
            raise ValueError("min_connection and connection_penalty must be >= 0")
        self.network = network
        self.request = request
        self.min_connection = min_connection
        self.connection_penalty = connection_penalty
        self._banned = [False] * len(network.flights)
        for flight_id in cancelled:
            if not 0 <= flight_id < len(network.flights):
                raise IndexError(f"cancelled flight id {flight_id} out of range")
            self._banned[flight_id] = True

    def initial_node(self) -> Node:
        """The start: stranded at the origin, ready at the cancellation time. O(1)."""
        r = self.request
        return Node(r.origin, r.ready, r.ready, 0, 0.0, None, None)

    def is_goal(self, node: Node) -> bool:
        """True if the node is at the destination. O(1)."""
        return node.airport == self.request.dest

    def moves(self, node: Node) -> Iterator[ScheduledFlight]:
        """Usable flights from this node, earliest departure first.

        A flight is usable if it leaves at or after the node's ready time, has
        enough free seats and is not cancelled. O(log F_a) to start, then O(1)
        per flight examined.
        """
        seats = self.request.seats
        for flight in self.network.departures_from(node.airport, node.ready):
            if not self._banned[flight.flight_id] and flight.seats_free >= seats:
                yield flight

    def child(self, node: Node, flight: ScheduledFlight) -> Node:
        """The node reached by taking ``flight`` from ``node``. O(1).

        The step cost is the time from arriving at ``node`` to arriving at the
        flight's destination, plus the connection penalty if that destination
        is an intermediate stop rather than the goal.
        """
        at_goal = flight.dest == self.request.dest
        step = (flight.arr - node.arrived) + (0 if at_goal else self.connection_penalty)
        return Node(
            airport=flight.dest,
            ready=flight.arr + self.min_connection,
            arrived=flight.arr,
            legs=node.legs + 1,
            cost=node.cost + step,
            flight=flight,
            parent=node,
        )

    def successors(self, node: Node) -> Iterator[Node]:
        """Child nodes for every usable move, earliest departure first."""
        for flight in self.moves(node):
            yield self.child(node, flight)

    def new_visited(self) -> list[bool]:
        """A fresh visited table: one slot per flight plus one for the start. O(F)."""
        return [False] * (len(self.network.flights) + 1)

    def key(self, node: Node) -> int:
        """Index of this node's state in a visited table. O(1)."""
        if node.flight is None:
            return len(self.network.flights)
        return node.flight.flight_id

    def route_to(self, node: Node) -> list[ScheduledFlight]:
        """Flights from the start to ``node``, in order. O(legs)."""
        flights: list[ScheduledFlight] = []
        cursor: Node | None = node
        while cursor is not None and cursor.flight is not None:
            flights.append(cursor.flight)
            cursor = cursor.parent
        flights.reverse()
        return flights

    def result(self, algorithm: str, goal: Node | None, stats: SearchStats) -> SearchResult:
        """Package a search outcome; ``goal=None`` means no route exists. O(legs)."""
        if goal is None:
            return SearchResult(algorithm, self.request, [], math.inf, stats)
        return SearchResult(algorithm, self.request, self.route_to(goal), goal.cost, stats)


# ------------------------------------------------------------------- searches


def bfs(problem: RebookingProblem) -> SearchResult:
    """Breadth-first search: the route with the fewest flights.

    Explores one leg at a time and stops as soon as a goal is generated, so it
    returns a fewest-legs route even if that route arrives much later than a
    route with more legs. Among equal-legs routes it returns the first found in
    earliest-departure order. Complete: it finds a route whenever one exists.

    Time O(F * F_a) in the worst case (F flights, F_a flights leaving one
    airport); space O(F).
    """
    stats = SearchStats()
    visited = problem.new_visited()
    root = problem.initial_node()
    visited[problem.key(root)] = True
    queue = [root]  # list with a head index; the front is queue[head]
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        stats.expanded += 1
        for flight in problem.moves(node):
            if visited[flight.flight_id]:
                continue
            visited[flight.flight_id] = True
            stats.generated += 1
            child = problem.child(node, flight)
            if problem.is_goal(child):
                return problem.result("BFS", child, stats)
            queue.append(child)
            stats.max_frontier = max(stats.max_frontier, len(queue) - head)
    return problem.result("BFS", None, stats)


def dfs(problem: RebookingProblem) -> SearchResult:
    """Depth-first search: dives down one path and returns the first route found.

    Takes the earliest departure at every step, so it can wander through many
    airports and return a long, late route. It exists to show why BFS and the
    cost-aware searches are needed. Complete (each state is visited once), but
    not optimal. Iterative, so route length cannot hit Python's recursion limit.

    Time O(F * F_a) in the worst case; space O(F).
    """
    stats = SearchStats()
    visited = problem.new_visited()
    root = problem.initial_node()
    visited[problem.key(root)] = True
    nodes = [root]  # the current path
    moves = [problem.moves(root)]  # one lazy iterator of moves per node on the path
    stats.expanded = 1
    stats.max_frontier = 1
    while nodes:
        flight = next(moves[-1], None)
        if flight is None:  # this node is exhausted: back up one step
            nodes.pop()
            moves.pop()
            continue
        if visited[flight.flight_id]:
            continue
        visited[flight.flight_id] = True
        stats.generated += 1
        child = problem.child(nodes[-1], flight)
        if problem.is_goal(child):
            return problem.result("DFS", child, stats)
        nodes.append(child)
        moves.append(problem.moves(child))
        stats.expanded += 1
        stats.max_frontier = max(stats.max_frontier, len(nodes))
    return problem.result("DFS", None, stats)


def format_itinerary(network: RouteNetwork, result: SearchResult) -> str:
    """Readable multi-line description of a result, for the UI and logs. O(legs)."""
    r = result.request
    head = f"{result.algorithm} for {r.pnr}: "
    if not result.found:
        return head + "no route found"
    lines = [
        head + f"{result.legs} leg(s), cost {result.cost:g}, "
        f"arrives {clock(result.route[-1].arr)} ({result.lateness:+d} min vs original)"
    ]
    for f in result.route:
        lines.append(
            f"  {f.number} {network.airports[f.origin].code} {clock(f.dep)}"
            f" -> {network.airports[f.dest].code} {clock(f.arr)}"
        )
    return "\n".join(lines)
