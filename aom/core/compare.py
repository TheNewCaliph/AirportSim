"""The one typing rule the ordered structures need: keys support ``<``.

The trees, the sorted linked-list insert and the sorts compare keys only with
``<``. Two keys a and b count as equal when neither ``a < b`` nor ``b < a``.
Integers, floats, strings and tuples of those (such as ``(departure_minute,
flight_id)``) all qualify.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar


class SupportsLessThan(Protocol):
    """Anything that can be compared with ``<``."""

    def __lt__(self, other: Any, /) -> bool: ...


K = TypeVar("K", bound=SupportsLessThan)
