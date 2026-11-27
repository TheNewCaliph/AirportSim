"""Linear and binary search on anything indexable.

``linear_search`` works on any order. The binary searches need the sequence
sorted by the same ``key`` and halve the remaining range each step, so they
take at most about log2(n) + 1 comparisons: 8 for a 200-flight day.

``lower_bound`` and ``upper_bound`` return insertion points rather than -1,
which is what "first flight at or after 15:00" needs.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar  # noqa: UP035

T_co = TypeVar("T_co", covariant=True)

Key = Callable[[Any], Any] | None


class Indexable(Protocol[T_co]):
    """Anything with a length and integer indexing, such as DynamicArray or list."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int, /) -> T_co: ...


def _identity(item: Any) -> Any:
    return item


def linear_search(items: Indexable[Any], target: Any, key: Key = None) -> int:
    """Index of the first element whose key equals ``target``, or -1. O(n)."""
    k = key or _identity
    for i in range(len(items)):
        if k(items[i]) == target:
            return i
    return -1


def lower_bound(items: Indexable[Any], target: Any, key: Key = None) -> int:
    """First index whose key is >= ``target`` (len(items) if none). O(log n)."""
    k = key or _identity
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi) // 2
        if k(items[mid]) < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def upper_bound(items: Indexable[Any], target: Any, key: Key = None) -> int:
    """First index whose key is > ``target`` (len(items) if none). O(log n)."""
    k = key or _identity
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi) // 2
        if target < k(items[mid]):
            hi = mid
        else:
            lo = mid + 1
    return lo


def binary_search(items: Indexable[Any], target: Any, key: Key = None) -> int:
    """Index of the first element whose key equals ``target``, or -1. O(log n).

    ``items`` must be sorted in ascending order of ``key``.
    """
    k = key or _identity
    i = lower_bound(items, target, k)
    if i < len(items) and not target < k(items[i]):
        return i
    return -1
