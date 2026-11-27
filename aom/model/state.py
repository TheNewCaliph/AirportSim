"""AirportState: the single source of truth for one simulated day.

Every module reads the day from here and changes it only through here: the
gates, the aircraft, the flights and the passengers, plus the current minute.
Nothing else keeps its own copy of a flight, so a delay written by M4 is
immediately what M2, M3 and the dashboard see.

All collections are our own DynamicArrays. In Sprint 1 the lookups by id are
linear searches. Sprint 2 adds hash-table indexes by id and AVL indexes by
departure time (``aom/modules/schedule``) without changing this interface.
"""

from __future__ import annotations

from aom.core.dynamic_array import DynamicArray
from aom.core.searching import linear_search
from aom.core.sorting import merge_sort
from aom.model.entities import Aircraft, Direction, Flight, Gate, Passenger


class AirportState:
    """Everything known about the day at one airport."""

    def __init__(self, code: str, seed: int | None = None) -> None:
        self.code = code
        self.seed = seed
        self.now = 0  # current simulated minute, advanced by the engine
        self.gates: DynamicArray[Gate] = DynamicArray()
        self.aircraft: DynamicArray[Aircraft] = DynamicArray()
        self.flights: DynamicArray[Flight] = DynamicArray()
        self.passengers: DynamicArray[Passenger] = DynamicArray()

    # ------------------------------------------------------------------ adding

    def add_gate(self, gate: Gate) -> None:
        """Register a gate; ids must be unique. O(g)."""
        if linear_search(self.gates, gate.gate_id, key=lambda g: g.gate_id) != -1:
            raise ValueError(f"duplicate gate {gate.gate_id}")
        self.gates.append(gate)

    def add_aircraft(self, aircraft: Aircraft) -> None:
        """Register an aircraft; tail numbers must be unique. O(a)."""
        if linear_search(self.aircraft, aircraft.tail, key=lambda a: a.tail) != -1:
            raise ValueError(f"duplicate aircraft {aircraft.tail}")
        self.aircraft.append(aircraft)

    def add_flight(self, flight: Flight) -> None:
        """Register a flight; it must touch this airport and use a known aircraft. O(f + a)."""
        if self.code not in (flight.origin, flight.destination):
            raise ValueError(f"{flight.flight_id} does not touch {self.code}")
        expected = flight.destination if flight.is_arrival else flight.origin
        if expected != self.code:
            raise ValueError(f"{flight.flight_id}: direction does not match its airports")
        if linear_search(self.flights, flight.flight_id, key=lambda f: f.flight_id) != -1:
            raise ValueError(f"duplicate flight {flight.flight_id}")
        if linear_search(self.aircraft, flight.tail, key=lambda a: a.tail) == -1:
            raise ValueError(f"{flight.flight_id} uses unknown aircraft {flight.tail}")
        self.flights.append(flight)

    def add_passenger(self, passenger: Passenger) -> None:
        """Register a passenger already placed on their flights' manifests. O(1).

        The generator guarantees unique PNRs; checking here would make loading
        a full day quadratic.
        """
        self.passengers.append(passenger)

    # ----------------------------------------------------------------- lookups

    def flight(self, flight_id: str) -> Flight:
        """The flight with this id. O(f) until Sprint 2's hash index."""
        i = linear_search(self.flights, flight_id, key=lambda f: f.flight_id)
        if i == -1:
            raise KeyError(flight_id)
        return self.flights[i]

    def gate(self, gate_id: str) -> Gate:
        """The gate with this id. O(g)."""
        i = linear_search(self.gates, gate_id, key=lambda g: g.gate_id)
        if i == -1:
            raise KeyError(gate_id)
        return self.gates[i]

    def aircraft_by_tail(self, tail: str) -> Aircraft:
        """The aircraft with this tail number. O(a)."""
        i = linear_search(self.aircraft, tail, key=lambda a: a.tail)
        if i == -1:
            raise KeyError(tail)
        return self.aircraft[i]

    def passenger(self, pnr: str) -> Passenger:
        """The passenger with this PNR. O(p) until Sprint 2's hash index."""
        i = linear_search(self.passengers, pnr, key=lambda p: p.pnr)
        if i == -1:
            raise KeyError(pnr)
        return self.passengers[i]

    # ------------------------------------------------------------------- views

    def rotation(self, tail: str) -> DynamicArray[Flight]:
        """The aircraft's flights at this airport, in time order. O(f + r log r)."""
        legs = self.flights.filter(lambda f: f.tail == tail)
        merge_sort(legs, key=lambda f: f.local_time)
        return legs

    def arrivals(self) -> DynamicArray[Flight]:
        """Flights arriving here, in insertion order. O(f)."""
        return self.flights.filter(lambda f: f.direction is Direction.ARRIVAL)

    def departures(self) -> DynamicArray[Flight]:
        """Flights departing from here, in insertion order. O(f)."""
        return self.flights.filter(lambda f: f.direction is Direction.DEPARTURE)

    def summary(self) -> str:
        """One-line description for logs and the CLI."""
        return (
            f"{self.code} seed={self.seed}: {len(self.flights)} flights "
            f"({len(self.arrivals())} arr, {len(self.departures())} dep), "
            f"{len(self.aircraft)} aircraft, {len(self.gates)} gates, "
            f"{len(self.passengers)} passengers"
        )
