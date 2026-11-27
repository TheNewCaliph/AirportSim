"""Arrival-departure turns and their buffered intervals."""

from dataclasses import dataclass

_BUFFER = 10


@dataclass(frozen=True, slots=True)
class Turn:
    """A flight's arrival and departure times in minutes."""

    arrival: int
    departure: int

    def __post_init__(self) -> None:
        if self.departure <= self.arrival:
            raise ValueError("departure must be later than arrival")

    @property
    def buffered_start(self) -> int:
        """Return the start of the turn's 10-minute buffered interval."""
        return self.arrival - _BUFFER

    @property
    def buffered_end(self) -> int:
        """Return the end of the turn's 10-minute buffered interval."""
        return self.departure + _BUFFER

    def overlaps(self, other: "Turn") -> bool:
        """Return whether this turn's buffered interval overlaps another's."""
        return self.buffered_start < other.buffered_end and other.buffered_start < self.buffered_end
