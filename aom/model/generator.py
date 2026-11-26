"""Seeded generator for one operating day at the home airport.

The same seed always produces exactly the same day, which is what makes runs,
tests and experiments repeatable.

How a day is built:

1. **Gates.** Terminal A has narrow-body domestic stands, terminal B has
   narrow-body stands with customs, terminal C has wide-body stands with
   customs.
2. **Aircraft and rotations.** Aircraft are added one at a time, each from an
   airline's fleet, until the day has ``n_flights`` legs. Each aircraft flies a
   rotation of 2-4 legs through the home airport, alternating arrivals and
   departures. Pakistani carriers' aircraft may start the day at home; foreign
   carriers' aircraft fly in from their hub and back.
3. **Peak-hour timing.** Each rotation's first event is drawn from a mixture:
   most around the morning and evening peaks, the rest spread across the day.
   Every later event follows from block times, the aircraft's minimum turn
   time and some random slack, so the ground times are always feasible.

All times are minutes on the home airport's clock (see ``entities``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from aom.model.entities import Aircraft, AircraftSize, Direction, Flight, Gate
from aom.model.passengers import PassengerConfig, generate_passengers
from aom.model.state import AirportState

# --------------------------------------------------------------------- tables


@dataclass(frozen=True, slots=True)
class Route:
    """A destination served from the home airport."""

    code: str
    block: int  # scheduled flight time in minutes
    international: bool


@dataclass(frozen=True, slots=True)
class FleetType:
    """One aircraft type flown by one airline, and where it goes."""

    airline: str
    type_code: str
    size: AircraftSize
    seats: int
    min_turn: int
    weight: int  # relative share of the aircraft added to the day
    routes: tuple[Route, ...]
    home_based: bool  # True if some of these aircraft start the day at the home airport


LHE = Route("LHE", 105, False)
ISB = Route("ISB", 120, False)
PEW = Route("PEW", 130, False)
MUX = Route("MUX", 85, False)
SKT = Route("SKT", 115, False)
UET = Route("UET", 75, False)
LYP = Route("LYP", 95, False)
DXB = Route("DXB", 125, True)
AUH = Route("AUH", 120, True)
SHJ = Route("SHJ", 120, True)
DOH = Route("DOH", 135, True)
MCT = Route("MCT", 95, True)
RUH = Route("RUH", 240, True)
JED = Route("JED", 270, True)
IST = Route("IST", 390, True)
LHR = Route("LHR", 540, True)

DOMESTIC = (LHE, ISB, PEW, MUX, SKT, UET, LYP)
NARROW = AircraftSize.NARROW
WIDE = AircraftSize.WIDE

DEFAULT_FLEETS: tuple[FleetType, ...] = (
    FleetType("PK", "A320", NARROW, 174, 40, 10, (*DOMESTIC, DXB, DOH, MCT, AUH), True),
    FleetType("PK", "B777", WIDE, 330, 75, 3, (JED, RUH, LHR), True),
    FleetType("PA", "A320", NARROW, 174, 40, 6, (*DOMESTIC, DXB, SHJ, AUH), True),
    FleetType("PA", "A321", NARROW, 194, 45, 3, (*DOMESTIC, DXB, SHJ, JED), True),
    FleetType("9P", "A320", NARROW, 180, 35, 6, (*DOMESTIC, MCT, SHJ), True),
    FleetType("ER", "B737", NARROW, 189, 40, 4, (*DOMESTIC, DXB, SHJ), True),
    FleetType("ER", "A330", WIDE, 377, 70, 1, (JED, RUH), True),
    FleetType("EK", "B777", WIDE, 354, 75, 3, (DXB,), False),
    FleetType("QR", "B787", WIDE, 254, 70, 2, (DOH,), False),
    FleetType("QR", "A320", NARROW, 144, 45, 1, (DOH,), False),
    FleetType("FZ", "B737", NARROW, 189, 40, 3, (DXB,), False),
    FleetType("G9", "A320", NARROW, 168, 40, 2, (SHJ,), False),
    FleetType("TK", "A330", WIDE, 289, 70, 1, (IST,), False),
)

# Plain dicts are fine outside aom/core: these are small constant tables, not
# the day's data.
FIRST_FLIGHT_NUMBER = {
    "PK": 300, "PA": 200, "9P": 840, "ER": 500, "EK": 600,
    "QR": 604, "FZ": 330, "G9": 540, "TK": 708,
}  # fmt: skip

TAIL_PREFIX = {
    "PK": "AP-B", "PA": "AP-B", "9P": "AP-B", "ER": "AP-B", "EK": "A6-E",
    "QR": "A7-A", "FZ": "A6-F", "G9": "A6-A", "TK": "TC-J",
}  # fmt: skip


@dataclass(frozen=True, slots=True)
class DayConfig:
    """Everything that shapes a generated day. The defaults give the demo day."""

    home: str = "KHI"
    n_flights: int = 200
    first_minute: int = 5 * 60  # no home-airport movements before 05:00
    last_minute: int = 23 * 60 + 30  # or after 23:30
    peaks: tuple[tuple[int, int], ...] = ((8 * 60, 75), (19 * 60, 90))  # (mean, std dev)
    peak_share: float = 0.65  # share of rotations that start near a peak
    home_based_share: float = 0.5  # share of home carriers' aircraft parked at home overnight
    leg_counts: tuple[int, ...] = (2, 3, 4)
    leg_weights: tuple[int, ...] = (5, 2, 3)
    max_slack: int = 120  # extra minutes on the ground beyond the minimum turn
    mean_slack: int = 30
    gates_domestic: int = 8  # terminal A
    gates_international: int = 8  # terminal B
    gates_wide: int = 6  # terminal C
    fleets: tuple[FleetType, ...] = DEFAULT_FLEETS


# ------------------------------------------------------------------ generator


def build_gates(config: DayConfig) -> list[Gate]:
    """Terminal A narrow domestic, B narrow with customs, C wide with customs."""
    gates = [Gate(f"A{i}", "A", False, False) for i in range(1, config.gates_domestic + 1)]
    gates += [Gate(f"B{i}", "B", False, True) for i in range(1, config.gates_international + 1)]
    gates += [Gate(f"C{i}", "C", True, True) for i in range(1, config.gates_wide + 1)]
    return gates


class _Namer:
    """Hands out unique tail numbers and flight numbers."""

    def __init__(self) -> None:
        self._tails: list[tuple[str, int]] = []
        self._numbers: list[tuple[str, int]] = []

    @staticmethod
    def _next(counters: list[tuple[str, int]], key: str, start: int) -> int:
        for i, (k, value) in enumerate(counters):
            if k == key:
                counters[i] = (k, value + 1)
                return value + 1
        counters.append((key, start))
        return start

    def tail(self, airline: str) -> str:
        prefix = TAIL_PREFIX[airline]
        n = self._next(self._tails, prefix, 0)
        letters = chr(ord("A") + (n // 26) % 26) + chr(ord("A") + n % 26)
        return prefix + letters

    def flight_id(self, airline: str) -> str:
        start = FIRST_FLIGHT_NUMBER[airline]
        return f"{airline}{self._next(self._numbers, airline, start)}"


def _first_event_time(rng: random.Random, config: DayConfig) -> int:
    """Draw the minute of a rotation's first home-airport event, favouring the peaks."""
    if rng.random() < config.peak_share:
        mean, std = rng.choice(config.peaks)
        minute = int(rng.gauss(mean, std))
    else:
        minute = rng.randint(config.first_minute, config.last_minute)
    return max(config.first_minute, min(config.last_minute, minute))


def _slack(rng: random.Random, config: DayConfig) -> int:
    """Extra ground time beyond the minimum: usually short, sometimes long."""
    return min(config.max_slack, int(rng.expovariate(1 / config.mean_slack)))


def _rotation(
    rng: random.Random, config: DayConfig, fleet: FleetType, aircraft: Aircraft, namer: _Namer
) -> list[Flight]:
    """One aircraft's legs through the home airport, alternating arrival and departure."""
    home = config.home
    legs = rng.choices(config.leg_counts, weights=config.leg_weights)[0]
    starts_at_home = fleet.home_based and rng.random() < config.home_based_share
    direction = Direction.DEPARTURE if starts_at_home else Direction.ARRIVAL
    local = _first_event_time(rng, config)  # time of the next event at home
    away = rng.choice(fleet.routes)  # where the aircraft is (or is going)

    flights: list[Flight] = []
    while len(flights) < legs and local <= config.last_minute:
        fid = namer.flight_id(fleet.airline)
        if direction is Direction.ARRIVAL:
            flights.append(
                Flight(
                    flight_id=fid,
                    airline=fleet.airline,
                    tail=aircraft.tail,
                    origin=away.code,
                    destination=home,
                    direction=direction,
                    sched_dep=local - away.block,
                    sched_arr=local,
                    international=away.international,
                    capacity=aircraft.seats,
                )
            )
            local += aircraft.min_turn + _slack(rng, config)
            away = rng.choice(fleet.routes)  # next departure may go somewhere new
            direction = Direction.DEPARTURE
        else:
            flights.append(
                Flight(
                    flight_id=fid,
                    airline=fleet.airline,
                    tail=aircraft.tail,
                    origin=home,
                    destination=away.code,
                    direction=direction,
                    sched_dep=local,
                    sched_arr=local + away.block,
                    international=away.international,
                    capacity=aircraft.seats,
                )
            )
            turn_away = aircraft.min_turn + rng.randint(0, 25)
            local += 2 * away.block + turn_away  # out, turn at the far end, back
            direction = Direction.ARRIVAL  # it comes back from the same place
    return flights


def generate_schedule(seed: int, config: DayConfig | None = None) -> AirportState:
    """Build the gates, aircraft and flights for one day. Deterministic in ``seed``."""
    config = config or DayConfig()
    rng = random.Random(seed)
    state = AirportState(config.home, seed)
    for gate in build_gates(config):
        state.add_gate(gate)

    namer = _Namer()
    weights = [f.weight for f in config.fleets]
    while len(state.flights) < config.n_flights:
        fleet = rng.choices(config.fleets, weights=weights)[0]
        aircraft = Aircraft(
            tail=namer.tail(fleet.airline),
            airline=fleet.airline,
            type_code=fleet.type_code,
            size=fleet.size,
            seats=fleet.seats,
            min_turn=fleet.min_turn,
        )
        legs = _rotation(rng, config, fleet, aircraft, namer)
        if not legs:
            continue
        legs = legs[: config.n_flights - len(state.flights)]  # stop exactly at n_flights
        state.add_aircraft(aircraft)
        for flight in legs:
            state.add_flight(flight)
    return state


def generate_day(
    seed: int, config: DayConfig | None = None, passengers: PassengerConfig | None = None
) -> AirportState:
    """The full seeded day: gates, aircraft, flights, passengers and manifests.

    Passengers use their own random stream derived from the seed, so changing
    the passenger settings never changes the flight schedule.
    """
    state = generate_schedule(seed, config)
    generate_passengers(state, random.Random(f"passengers-{seed}"), passengers)
    return state
