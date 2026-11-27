"""Passengers, cabin classes and flight manifests for a generated day.

1. Every flight gets a target load of 70-95% of its seats.
2. **Connections first.** About a third of each arriving flight's target
   passengers continue on a later departure: one leaving at least
   ``min_connection`` and at most ``max_connection`` minutes after the arrival,
   not flying back where they came from, and with target seats left. The
   departures are kept sorted by time in our DynamicArray, and a binary search
   (``lower_bound``) finds the first one inside the window. Because each
   connecting passenger uses two seats, this makes roughly 20% of all
   passengers connecting.
3. **Local passengers** fill the remaining target seats on every flight.
4. About 10% fly business and about 2% need special assistance; both raise a
   passenger's priority when M3 rebooks them.

Every passenger's PNR is added to the manifest of each flight they are on.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from aom.core.dynamic_array import DynamicArray
from aom.core.searching import lower_bound
from aom.core.sorting import merge_sort
from aom.model.entities import FareClass, Flight, Passenger
from aom.model.state import AirportState

_PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0 or 1: easy to read aloud
_PNR_SPACE = len(_PNR_ALPHABET) ** 6  # 32^6, about 1.07 billion codes
_PNR_STEP = 387_420_489  # 3^18: odd, so coprime with 2^30, so i -> i*step is a bijection


@dataclass(frozen=True, slots=True)
class PassengerConfig:
    """Everything that shapes the passenger mix."""

    load_min: float = 0.70
    load_max: float = 0.95
    connect_share: float = 1 / 3  # share of an arrival's target load that connects
    min_connection: int = 60  # minimum connection time in minutes
    max_connection: int = 300
    business_share: float = 0.10
    assistance_share: float = 0.02


def pnr_for(index: int, salt: int) -> str:
    """The six-character booking code of passenger number ``index``.

    Multiplying by an odd step modulo 32^6 visits every code exactly once, so
    codes are unique for over a billion passengers without keeping a set of
    the ones already used, yet they look random.
    """
    value = (index * _PNR_STEP + salt) % _PNR_SPACE
    chars = []
    for _ in range(6):
        value, digit = divmod(value, len(_PNR_ALPHABET))
        chars.append(_PNR_ALPHABET[digit])
    return "".join(chars)


class _Booker:
    """Creates passengers and puts them on manifests."""

    def __init__(self, state: AirportState, rng: random.Random, config: PassengerConfig) -> None:
        self.state = state
        self.rng = rng
        self.config = config
        self.salt = rng.randrange(_PNR_SPACE)
        self.count = 0

    def book(self, origin: str, destination: str, flights: tuple[Flight, ...]) -> None:
        rng, config = self.rng, self.config
        business = rng.random() < config.business_share
        passenger = Passenger(
            pnr=pnr_for(self.count, self.salt),
            fare_class=FareClass.BUSINESS if business else FareClass.ECONOMY,
            origin=origin,
            destination=destination,
            itinerary=tuple(f.flight_id for f in flights),
            special_assistance=rng.random() < config.assistance_share,
        )
        self.count += 1
        for flight in flights:
            flight.manifest.append(passenger.pnr)
        self.state.add_passenger(passenger)


def generate_passengers(
    state: AirportState, rng: random.Random, config: PassengerConfig | None = None
) -> None:
    """Fill every flight in ``state`` with passengers, connections first."""
    config = config or PassengerConfig()
    booker = _Booker(state, rng, config)

    # (flight, target load) pairs, so a flight's target travels with it.
    planned: DynamicArray[tuple[Flight, int]] = DynamicArray()
    for flight in state.flights:
        load = rng.uniform(config.load_min, config.load_max)
        planned.append((flight, round(flight.capacity * load)))

    departures = planned.filter(lambda p: not p[0].is_arrival)
    merge_sort(departures, key=_dep_time)
    arrivals = planned.filter(lambda p: p[0].is_arrival)
    merge_sort(arrivals, key=lambda p: p[0].sched_arr)

    for arrival, arrival_target in arrivals:
        earliest = arrival.sched_arr + config.min_connection
        latest = arrival.sched_arr + config.max_connection
        window: DynamicArray[tuple[Flight, int]] = DynamicArray()
        i = lower_bound(departures, earliest, key=_dep_time)
        while i < len(departures) and departures[i][0].sched_dep <= latest:
            if departures[i][0].destination != arrival.origin:
                window.append(departures[i])
            i += 1
        for _ in range(round(arrival_target * config.connect_share)):
            open_seats = window.filter(lambda p: p[0].booked < p[1])
            if open_seats.is_empty():
                break
            onward = open_seats[rng.randrange(len(open_seats))][0]
            booker.book(arrival.origin, onward.destination, (arrival, onward))

    for flight, flight_target in planned:
        for _ in range(flight_target - flight.booked):
            booker.book(flight.origin, flight.destination, (flight,))


def _dep_time(pair: tuple[Flight, int]) -> int:
    return pair[0].sched_dep
