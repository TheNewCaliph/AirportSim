"""Binary min-heap with decrease-key.

Used by the simulation engine's event queue (M5), the A*/UCS frontier and the
rebooking priority queue (M3), and the service-completion heap (M6).

Design notes
------------
* ``push`` returns a :class:`HeapEntry` handle. The handle stores its own array
  index, so ``decrease_key`` and ``remove`` find their entry in O(1) without a
  hash table (the core library has no cross-dependencies).
* Ordering is ``(priority, insertion sequence)``. Equal priorities therefore
  pop in FIFO order, which keeps runs deterministic for a given seed. Only
  ``<`` is required of priorities, so tuples such as
  ``(time, event_priority, seq)`` work directly.
* No ``heapq``, ``dict`` or ``set`` is used here (banned inside ``aom/core``).
  The backing store is a plain list used only through ``append``, ``pop``,
  indexing and ``len``, so it can be swapped for ``DynamicArray`` once that
  lands without touching the algorithms.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Generic, Protocol, TypeVar


class SupportsLessThan(Protocol):
    """Anything orderable with ``<`` (ints, floats, tuples of them, ...)."""

    def __lt__(self, other: Any, /) -> bool: ...


K = TypeVar("K", bound=SupportsLessThan)
T = TypeVar("T")


class HeapEntry(Generic[K, T]):
    """Handle to one element of a :class:`MinHeap`.

    Read ``priority`` and ``item`` freely. Never modify them directly; use
    :meth:`MinHeap.decrease_key`. ``in_heap`` tells whether it is still queued.
    """

    __slots__ = ("_index", "_owner", "_seq", "item", "priority")

    def __init__(self, priority: K, item: T, seq: int, index: int, owner: Any) -> None:
        self.priority = priority
        self.item = item
        self._seq = seq
        self._index = index
        self._owner = owner

    @property
    def in_heap(self) -> bool:
        """True while the entry is queued in a heap. O(1)."""
        return self._owner is not None

    def __repr__(self) -> str:
        state = "queued" if self.in_heap else "detached"
        return f"HeapEntry(priority={self.priority!r}, item={self.item!r}, {state})"


def _less(a: HeapEntry[Any, Any], b: HeapEntry[Any, Any]) -> bool:
    """Strict order on (priority, seq); needs only ``<`` on priorities."""
    if a.priority < b.priority:
        return True
    if b.priority < a.priority:
        return False
    return a._seq < b._seq


class MinHeap(Generic[K, T]):
    """Array-backed binary min-heap with O(log n) decrease-key and removal."""

    def __init__(self, entries: Iterable[tuple[K, T]] | None = None) -> None:
        """Create a heap, optionally from ``(priority, item)`` pairs.

        Building from ``n`` pairs uses bottom-up heapify: O(n).
        Starting empty: O(1).
        """
        self._a: list[HeapEntry[K, T]] = []
        self._next_seq = 0
        if entries is not None:
            for priority, item in entries:
                self._a.append(self._make(priority, item, len(self._a)))
            for i in range(len(self._a) // 2 - 1, -1, -1):
                self._sift_down(i)

    # ------------------------------------------------------------------ queries

    def __len__(self) -> int:
        """Number of queued entries. O(1)."""
        return len(self._a)

    def __bool__(self) -> bool:
        """True if the heap is non-empty. O(1)."""
        return len(self._a) > 0

    def is_empty(self) -> bool:
        """True if the heap holds nothing. O(1)."""
        return len(self._a) == 0

    def contains(self, entry: HeapEntry[K, T]) -> bool:
        """True if ``entry`` is currently queued in *this* heap. O(1)."""
        return entry._owner is self

    def peek(self) -> HeapEntry[K, T]:
        """Return the minimum entry without removing it. O(1).

        Raises:
            IndexError: if the heap is empty.
        """
        if not self._a:
            raise IndexError("peek from empty heap")
        return self._a[0]

    # ---------------------------------------------------------------- mutations

    def push(self, priority: K, item: T) -> HeapEntry[K, T]:
        """Insert ``item`` and return its handle. O(log n) worst case."""
        entry = self._make(priority, item, len(self._a))
        self._a.append(entry)
        self._sift_up(entry._index)
        return entry

    def pop(self) -> HeapEntry[K, T]:
        """Remove and return the minimum entry. O(log n).

        Raises:
            IndexError: if the heap is empty.
        """
        if not self._a:
            raise IndexError("pop from empty heap")
        top = self._a[0]
        last = self._a.pop()
        if self._a:
            self._a[0] = last
            last._index = 0
            self._sift_down(0)
        self._detach(top)
        return top

    def decrease_key(self, entry: HeapEntry[K, T], new_priority: K) -> None:
        """Lower ``entry``'s priority and restore order. O(log n).

        Setting an equal priority is a no-op.

        Raises:
            ValueError: if ``entry`` is not queued in this heap, or if
                ``new_priority`` is greater than the current priority.
        """
        self._require_owned(entry)
        if entry.priority < new_priority:
            raise ValueError("decrease_key cannot increase a priority")
        entry.priority = new_priority
        self._sift_up(entry._index)

    def remove(self, entry: HeapEntry[K, T]) -> None:
        """Delete an arbitrary queued entry. O(log n).

        Raises:
            ValueError: if ``entry`` is not queued in this heap.
        """
        self._require_owned(entry)
        i = entry._index
        last = self._a.pop()
        if last is not entry:
            self._a[i] = last
            last._index = i
            if self._sift_up(i) == i:
                self._sift_down(i)
        self._detach(entry)

    def clear(self) -> None:
        """Remove everything and invalidate all outstanding handles. O(n)."""
        for entry in self._a:
            self._detach(entry)
        self._a.clear()

    # ---------------------------------------------------------------- debugging

    def check_invariant(self) -> None:
        """Assert heap order and handle/index consistency. O(n). For tests."""
        for i, entry in enumerate(self._a):
            assert entry._index == i, f"stale index at {i}"
            assert entry._owner is self, f"wrong owner at {i}"
            if i > 0:
                parent = self._a[(i - 1) // 2]
                assert not _less(entry, parent), f"heap order broken at {i}"

    # ---------------------------------------------------------------- internals

    def _make(self, priority: K, item: T, index: int) -> HeapEntry[K, T]:
        entry = HeapEntry(priority, item, self._next_seq, index, self)
        self._next_seq += 1
        return entry

    @staticmethod
    def _detach(entry: HeapEntry[K, T]) -> None:
        entry._owner = None
        entry._index = -1

    def _require_owned(self, entry: HeapEntry[K, T]) -> None:
        if entry._owner is not self:
            raise ValueError("entry is not queued in this heap")

    def _sift_up(self, i: int) -> int:
        """Move the entry at ``i`` up until ordered; return its final index."""
        a = self._a
        entry = a[i]
        while i > 0:
            parent_i = (i - 1) // 2
            parent = a[parent_i]
            if not _less(entry, parent):
                break
            a[i] = parent
            parent._index = i
            i = parent_i
        a[i] = entry
        entry._index = i
        return i

    def _sift_down(self, i: int) -> None:
        """Move the entry at ``i`` down until ordered."""
        a = self._a
        n = len(a)
        entry = a[i]
        while True:
            child_i = 2 * i + 1
            if child_i >= n:
                break
            right_i = child_i + 1
            if right_i < n and _less(a[right_i], a[child_i]):
                child_i = right_i
            child = a[child_i]
            if not _less(child, entry):
                break
            a[i] = child
            child._index = i
            i = child_i
        a[i] = entry
        entry._index = i
