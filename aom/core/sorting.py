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
merge          O(n log n)   O(n log n)   O(n)     yes
quick          O(n log n)   O(n^2)*      O(log n) no
============== ============ ============ ======== ======
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar  # noqa: UP035

from aom.core.dynamic_array import DynamicArray

T = TypeVar("T")

Key = Callable[[Any], Any] | None
_INSERTION_CUTOFF = 12


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


# ----------------------------------------------------------------- merge sort


def merge_sort(items: MutableIndexable[T], key: Key = None) -> None:
    """Stable O(n log n) sort, bottom-up, with one O(n) buffer.

    Runs of width 1, 2, 4, ... are merged pairwise until one run covers the
    whole array. Taking from the left run on ties is what makes it stable.
    """
    k = key or _identity
    n = len(items)
    if n < 2:
        return
    buffer: DynamicArray[T] = DynamicArray(capacity=n)
    for i in range(n):
        buffer.append(items[i])
    width = 1
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            if mid < hi:
                _merge(items, buffer, lo, mid, hi, k)
        width *= 2


def _merge(
    items: MutableIndexable[T],
    buffer: DynamicArray[T],
    lo: int,
    mid: int,
    hi: int,
    k: Callable[[Any], Any],
) -> None:
    """Merge sorted items[lo:mid] and items[mid:hi] back into items[lo:hi]. O(hi - lo)."""
    for i in range(lo, hi):
        buffer[i] = items[i]
    left, right, out = lo, mid, lo
    while left < mid and right < hi:
        if k(buffer[right]) < k(buffer[left]):
            items[out] = buffer[right]
            right += 1
        else:
            items[out] = buffer[left]  # ties take the left run: stable
            left += 1
        out += 1
    while left < mid:
        items[out] = buffer[left]
        left += 1
        out += 1
    while right < hi:
        items[out] = buffer[right]
        right += 1
        out += 1


# ------------------------------------------------------------------ quicksort


def quick_sort(items: MutableIndexable[T], key: Key = None) -> None:
    """Quicksort with median-of-three pivots and Hoare partitioning.

    O(n log n) expected, O(n^2) worst case, not stable. The pivot is the
    median of the first, middle and last elements, so sorted and reversed
    input split evenly. Hoare's two-pointer partition also splits runs of
    equal keys evenly. The smaller side is sorted recursively and the larger
    side by looping, so the recursion depth stays O(log n). Small ranges go
    to insertion sort, which is faster there.
    """
    k = key or _identity
    _quick(items, 0, len(items) - 1, k)


def _quick(items: MutableIndexable[T], lo: int, hi: int, k: Callable[[Any], Any]) -> None:
    while hi - lo + 1 > _INSERTION_CUTOFF:
        mid = (lo + hi) // 2
        # Order items[lo] <= items[mid] <= items[hi], so the median is at mid.
        if k(items[mid]) < k(items[lo]):
            _swap(items, lo, mid)
        if k(items[hi]) < k(items[lo]):
            _swap(items, lo, hi)
        if k(items[hi]) < k(items[mid]):
            _swap(items, mid, hi)
        pivot = k(items[mid])

        i, j = lo - 1, hi + 1
        while True:
            i += 1
            while k(items[i]) < pivot:
                i += 1
            j -= 1
            while pivot < k(items[j]):
                j -= 1
            if i >= j:
                break
            _swap(items, i, j)
        # Now every key in items[lo..j] <= pivot <= every key in items[j+1..hi].

        if j - lo < hi - j:
            _quick(items, lo, j, k)
            lo = j + 1
        else:
            _quick(items, j + 1, hi, k)
            hi = j
    insertion_sort(items, k, lo, hi + 1)
