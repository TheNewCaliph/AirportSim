"""Sorting algorithms, all in place, all on anything indexable.

Each function sorts ``items`` in ascending order of ``key(item)`` (or of the
items themselves when ``key`` is None). ``items`` can be our DynamicArray or a
plain list in tests: anything with ``len``, ``items[i]`` and ``items[i] = x``.

============== ============ ============ ======== ======
Algorithm      Best         Worst        Memory   Stable
============== ============ ============ ======== ======
insertion      O(n)         O(n^2)       O(1)     yes
selection      O(n^2)       O(n^2)       O(1)     no
bubble         O(n)         O(n^2)       O(1)     yes
============== ============ ============ ======== ======
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar  # noqa: UP035

T = TypeVar("T")

Key = Callable[[Any], Any] | None


class MutableIndexable(Protocol[T]):
    """Anything with a length and integer get/set, such as DynamicArray or list."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int, /) -> T: ...

    def __setitem__(self, index: int, value: T, /) -> None: ...


def _identity(item: Any) -> Any:
    return item


def _swap(items: MutableIndexable[T], i: int, j: int) -> None:
    items[i], items[j] = items[j], items[i]


def is_sorted(items: MutableIndexable[T], key: Key = None) -> bool:
    """True if every element's key is <= the next one's. O(n)."""
    k = key or _identity
    return all(not k(items[i + 1]) < k(items[i]) for i in range(len(items) - 1))


# --------------------------------------------------------------- simple sorts


def insertion_sort(
    items: MutableIndexable[T], key: Key = None, lo: int = 0, hi: int | None = None
) -> None:
    """Sort items[lo:hi] by growing a sorted prefix one element at a time.

    Each new element is shifted left past every larger one. O(n^2) worst case,
    O(n) on already sorted input, O(1) extra memory, stable.
    """
    k = key or _identity
    end = len(items) if hi is None else hi
    for i in range(lo + 1, end):
        current = items[i]
        current_key = k(current)
        j = i - 1
        while j >= lo and current_key < k(items[j]):
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = current


def selection_sort(items: MutableIndexable[T], key: Key = None) -> None:
    """Sort by repeatedly swapping the smallest remaining element into place.

    Always O(n^2) comparisons but at most n - 1 swaps. O(1) extra memory,
    not stable.
    """
    k = key or _identity
    n = len(items)
    for i in range(n - 1):
        smallest = i
        for j in range(i + 1, n):
            if k(items[j]) < k(items[smallest]):
                smallest = j
        if smallest != i:
            _swap(items, i, smallest)


def bubble_sort(items: MutableIndexable[T], key: Key = None) -> None:
    """Sort by swapping adjacent out-of-order pairs, pass after pass.

    Each pass bubbles the largest remaining element to the end; a pass with
    no swaps means the array is sorted, so sorted input takes one pass. O(n^2)
    worst case, O(n) best case, O(1) extra memory, stable.
    """
    k = key or _identity
    n = len(items)
    for end in range(n - 1, 0, -1):
        swapped = False
        for j in range(end):
            if k(items[j + 1]) < k(items[j]):
                _swap(items, j, j + 1)
                swapped = True
        if not swapped:
            return
