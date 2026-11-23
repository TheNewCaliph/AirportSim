"""Dynamic array: a growable array built on a fixed-capacity raw block.

Python's list is only used here as a raw block of memory that never changes
size: ``[None] * capacity``. All growth, shrinking and bounds checking is our
own code. When the block is full, we allocate one twice as large and copy the
elements across, which makes ``append`` O(1) amortised: over n appends the
total copying work is at most 1 + 2 + 4 + ... + n < 2n.

Every other structure that needs contiguous storage (stack, heap, deque,
circular queue, the sorting routines' buffers) is built on this class.
"""

from __future__ import annotations

# collections.abc is off limits in aom/core (the guard test bans the whole
# collections package), so the abstract types come from typing.
from typing import Any, Callable, Generic, Iterable, Iterator, TypeVar  # noqa: UP035

T = TypeVar("T")

_MIN_CAPACITY = 4


class DynamicArray(Generic[T]):
    """A resizable array with O(1) indexing and O(1) amortised append."""

    __slots__ = ("_block", "_capacity", "_size")

    def __init__(self, items: Iterable[T] | None = None, capacity: int = _MIN_CAPACITY) -> None:
        """Create an empty array, or one holding ``items`` in order. O(n)."""
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._size = 0
        self._block: list[Any] = self._allocate(capacity)
        if items is not None:
            for item in items:
                self.append(item)

    @classmethod
    def filled(cls, length: int, value: T) -> DynamicArray[T]:
        """Return an array of ``length`` copies of ``value``. O(n)."""
        if length < 0:
            raise ValueError("length must not be negative")
        array: DynamicArray[T] = cls(capacity=max(length, _MIN_CAPACITY))
        for _ in range(length):
            array.append(value)
        return array

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _allocate(capacity: int) -> list[Any]:
        """Return a raw block of ``capacity`` empty slots. O(capacity)."""
        return [None] * capacity

    def _resize(self, new_capacity: int) -> None:
        """Move the elements into a new block of ``new_capacity`` slots. O(n)."""
        new_block = self._allocate(new_capacity)
        for i in range(self._size):
            new_block[i] = self._block[i]
        self._block = new_block
        self._capacity = new_capacity

    def _check_index(self, index: int) -> int:
        """Turn a possibly negative index into a valid position. O(1)."""
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("DynamicArray index out of range")
        return index

    # ------------------------------------------------------------------ queries

    def __len__(self) -> int:
        """Number of elements stored. O(1)."""
        return self._size

    def __bool__(self) -> bool:
        """True when the array holds at least one element. O(1)."""
        return self._size > 0

    @property
    def capacity(self) -> int:
        """Number of slots in the current block. O(1)."""
        return self._capacity

    def is_empty(self) -> bool:
        """True when the array holds no elements. O(1)."""
        return self._size == 0

    def __getitem__(self, index: int) -> T:
        """Element at ``index`` (negative counts from the end). O(1)."""
        value: T = self._block[self._check_index(index)]
        return value

    def __iter__(self) -> Iterator[T]:
        """Yield the elements from first to last. O(n) for the full walk."""
        for i in range(self._size):
            value: T = self._block[i]
            yield value

    def __contains__(self, value: object) -> bool:
        """True if some element equals ``value``. O(n)."""
        return any(self._block[i] == value for i in range(self._size))

    def __eq__(self, other: object) -> bool:
        """Element-wise equality with another DynamicArray. O(n)."""
        if not isinstance(other, DynamicArray):
            return NotImplemented
        if len(self) != len(other):
            return False
        return all(self._block[i] == other._block[i] for i in range(self._size))

    def __repr__(self) -> str:
        """Readable form such as ``DynamicArray([1, 2, 3])``. O(n)."""
        inside = ", ".join(repr(self._block[i]) for i in range(self._size))
        return f"DynamicArray([{inside}])"

    def to_list(self) -> list[T]:
        """Copy the elements into a new Python list (for tests and printing). O(n)."""
        out: list[T] = []
        for i in range(self._size):
            out.append(self._block[i])
        return out

    def index_of(self, value: T) -> int:
        """Position of the first element equal to ``value``, or -1. O(n)."""
        for i in range(self._size):
            if self._block[i] == value:
                return i
        return -1

    # ---------------------------------------------------------------- mutations

    def __setitem__(self, index: int, value: T) -> None:
        """Overwrite the element at ``index``. O(1)."""
        self._block[self._check_index(index)] = value

    def append(self, value: T) -> None:
        """Add ``value`` at the end, doubling the block when full. O(1) amortised."""
        if self._size == self._capacity:
            self._resize(2 * self._capacity)
        self._block[self._size] = value
        self._size += 1

    def extend(self, items: Iterable[T]) -> None:
        """Append every element of ``items`` in order. O(k) amortised."""
        for item in items:
            self.append(item)

    def insert(self, index: int, value: T) -> None:
        """Insert ``value`` before position ``index``, shifting the rest right. O(n).

        ``index`` may equal ``len(self)`` to insert at the end.
        """
        if index < 0:
            index += self._size
        if index < 0 or index > self._size:
            raise IndexError("DynamicArray insert index out of range")
        if self._size == self._capacity:
            self._resize(2 * self._capacity)
        for i in range(self._size, index, -1):
            self._block[i] = self._block[i - 1]
        self._block[index] = value
        self._size += 1

    def pop(self, index: int = -1) -> T:
        """Remove and return the element at ``index`` (default: the last).

        O(1) for the last element, O(n) otherwise. Halves the block when it is
        only a quarter full, so memory stays proportional to the size.
        """
        if self._size == 0:
            raise IndexError("pop from empty DynamicArray")
        index = self._check_index(index)
        value: T = self._block[index]
        for i in range(index, self._size - 1):
            self._block[i] = self._block[i + 1]
        self._size -= 1
        self._block[self._size] = None  # let the old reference be collected
        if self._capacity > _MIN_CAPACITY and self._size <= self._capacity // 4:
            self._resize(max(_MIN_CAPACITY, self._capacity // 2))
        return value

    def remove(self, value: T) -> bool:
        """Delete the first element equal to ``value``; False if absent. O(n)."""
        position = self.index_of(value)
        if position == -1:
            return False
        self.pop(position)
        return True

    def swap(self, i: int, j: int) -> None:
        """Exchange the elements at positions ``i`` and ``j``. O(1)."""
        i = self._check_index(i)
        j = self._check_index(j)
        self._block[i], self._block[j] = self._block[j], self._block[i]

    def clear(self) -> None:
        """Remove every element and return to the minimum capacity. O(1)."""
        self._block = self._allocate(_MIN_CAPACITY)
        self._capacity = _MIN_CAPACITY
        self._size = 0

    def copy(self) -> DynamicArray[T]:
        """Shallow copy with the same elements in the same order. O(n)."""
        return DynamicArray(self, capacity=max(self._capacity, _MIN_CAPACITY))

    def filter(self, keep: Callable[[T], bool]) -> DynamicArray[T]:
        """New array with only the elements for which ``keep`` is true. O(n)."""
        out: DynamicArray[T] = DynamicArray()
        for i in range(self._size):
            if keep(self._block[i]):
                out.append(self._block[i])
        return out

    def get(self, index: int) -> T:
        """Element at ``index``; same as ``array[index]``. O(1)."""
        return self[index]

    def set(self, index: int, value: T) -> None:
        """Overwrite the element at ``index``; same as ``array[index] = value``. O(1)."""
        self[index] = value
