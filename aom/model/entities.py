"""The records every module shares: flights, aircraft, gates, passengers, events.

Times are whole minutes on the home airport's clock, counted from midnight at
the start of the simulated day: 0 is 00:00, 900 is 15:00. A value below 0 is
the previous day and a value of 1440 or more is the next day; this happens
only for the far end of long flights (a 06:00 arrival from London left the
day before). The home airport never sees those times.

Records use ``slots=True``, so a typo such as ``flight.est_dpe = 5`` raises
an error instead of silently creating a new attribute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from aom.core.dynamic_array import DynamicArray

MINUTES_PER_DAY = 1440


def clock(minute: int) -> str:
    """Format a minute of the day as HH:MM, with a +1 or -1 day suffix if needed."""
    day, rest = divmod(minute, MINUTES_PER_DAY)
    text = f"{rest // 60:02d}:{rest % 60:02d}"
    if day > 0:
        return f"{text}+{day}"
    if day < 0:
        return f"{text}{day}"
    return text


class AircraftSize(Enum):
    """Body type, which decides which gates can take the aircraft."""

    NARROW = "narrow"
    WIDE = "wide"


class Direction(Enum):
    """Whether a flight arrives at or departs from the home airport."""

    ARRIVAL = "arrival"
    DEPARTURE = "departure"


class FlightStatus(Enum):
    """Where a flight is in its life cycle."""

    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    DEPARTED = "departed"
    ARRIVED = "arrived"


class FareClass(Enum):
    """Cabin a passenger booked."""

    ECONOMY = "economy"
    BUSINESS = "business"


class EventKind(Enum):
    """Things that can happen during the day. The engine (M5) orders and dispatches them."""

    FLIGHT_ARRIVAL = "flight_arrival"
    FLIGHT_DEPARTURE = "flight_departure"
    DELAY = "delay"
    CANCELLATION = "cancellation"
    GATE_CHANGE = "gate_change"
    WEATHER_CHANGED = "weather_changed"
    SLOT_SHORTAGE = "slot_shortage"
    TICK = "tick"


@dataclass(slots=True)
class Aircraft:
    """One airframe, identified by its tail number."""

    tail: str
    airline: str
    type_code: str
    size: AircraftSize
    seats: int
    min_turn: int  # minimum minutes on the ground between arrival and next departure

    @property
    def is_wide_body(self) -> bool:
        return self.size is AircraftSize.WIDE


@dataclass(slots=True)
class Gate:
    """A stand at the home airport."""

    gate_id: str
    terminal: str
    wide_body: bool  # can take wide-body aircraft
    customs: bool  # has passport control, needed for international flights


@dataclass(slots=True)
class Flight:
    """One flight leg that arrives at or departs from the home airport.

    ``est_dep`` and ``est_arr`` start equal to the scheduled times and are the
    only times that change when delays happen.
    """

    flight_id: str
    airline: str
    tail: str
    origin: str
    destination: str
    direction: Direction
    sched_dep: int
    sched_arr: int
    international: bool
    capacity: int
    est_dep: int = -1
    est_arr: int = -1
    status: FlightStatus = FlightStatus.SCHEDULED
    gate_id: str | None = None
    manifest: DynamicArray[str] = field(default_factory=DynamicArray)  # passenger PNRs

    def __post_init__(self) -> None:
        if self.sched_arr <= self.sched_dep:
            raise ValueError(f"{self.flight_id}: arrival must be after departure")
        if self.est_dep == -1:
            self.est_dep = self.sched_dep
        if self.est_arr == -1:
            self.est_arr = self.sched_arr

    @property
    def local_time(self) -> int:
        """Scheduled time at the home airport: arrival time or departure time."""
        return self.sched_arr if self.direction is Direction.ARRIVAL else self.sched_dep

    @property
    def est_local_time(self) -> int:
        """Estimated time at the home airport, after any delay."""
        return self.est_arr if self.direction is Direction.ARRIVAL else self.est_dep

    @property
    def delay(self) -> int:
        """Minutes late at the home airport (0 if on time)."""
        return max(0, self.est_local_time - self.local_time)

    @property
    def booked(self) -> int:
        return len(self.manifest)

    @property
    def seats_free(self) -> int:
        return self.capacity - len(self.manifest)

    @property
    def is_arrival(self) -> bool:
        return self.direction is Direction.ARRIVAL

    def __str__(self) -> str:
        return (
            f"{self.flight_id} {self.origin}->{self.destination} "
            f"{clock(self.sched_dep)}-{clock(self.sched_arr)} [{self.tail}]"
        )


@dataclass(slots=True)
class Passenger:
    """One traveller and the flights they are booked on, in order.

    ``itinerary`` holds only flights at the home airport: one flight for a
    local passenger, an arrival then a departure for a connecting one.
    """

    pnr: str
    fare_class: FareClass
    origin: str
    destination: str
    itinerary: tuple[str, ...]
    special_assistance: bool = False

    @property
    def is_connecting(self) -> bool:
        return len(self.itinerary) > 1

    @property
    def is_business(self) -> bool:
        return self.fare_class is FareClass.BUSINESS


@dataclass(slots=True)
class Event:
    """Something that happens at a given minute. M5 adds the queue ordering."""

    time: int
    kind: EventKind
    subject: str = ""  # usually a flight id
    detail: str = ""  # free text for the log and dashboard
