"""Queue, circular queue and deque.

* ``Queue``: first in, first out, on our singly linked list. Enqueue at the
  tail and dequeue at the head are both O(1), with no size limit.
* ``CircularQueue``: FIFO with a fixed capacity, on a fixed block of our
  dynamic array. ``front`` and the size wrap around with modulo arithmetic, so
  no element is ever shifted. M6 uses one per check-in counter, because a real
  queue area holds only so many people.
* ``Deque``: double-ended queue on a circular buffer that doubles when full.
  O(1) amortised push and pop at both ends. M6 uses one per security lane, so
  a passenger about to miss their flight can be pushed to the front.
"""

from __future__ import annotations

from typing import Any, Generic, Iterable, Iterator, TypeVar  # noqa: UP035

from aom.core.dynamic_array import DynamicArray
from aom.core.linked_list import SinglyLinkedList

T = TypeVar("T")


class Queue(Generic[T]):
    """Unbounded FIFO queue on a singly linked list."""

    __slots__ = ("_items",)

    def __init__(self, items: Iterable[T] | None = None) -> None:
        """Create an empty queue, or one holding ``items`` front to back. O(n)."""
        self._items: SinglyLinkedList[T] = SinglyLinkedList(items)

    def __len__(self) -> int:
        """Number of waiting elements. O(1)."""
        return len(self._items)

    def __bool__(self) -> bool:
        """True when something is waiting. O(1)."""
        return not self._items.is_empty()

    def is_empty(self) -> bool:
        """True when nothing is waiting. O(1)."""
        return self._items.is_empty()

    def __iter__(self) -> Iterator[T]:
        """Yield elements from front to back without removing them. O(n)."""
        return iter(self._items)

    def enqueue(self, value: T) -> None:
        """Add ``value`` at the back. O(1)."""
        self._items.append(value)

    def dequeue(self) -> T:
        """Remove and return the front element. O(1)."""
        if self._items.is_empty():
            raise IndexError("dequeue from empty Queue")
        return self._items.pop_front()

    def peek(self) -> T:
        """Front element without removing it. O(1)."""
        if self._items.is_empty():
            raise IndexError("peek at empty Queue")
        return self._items.peek_front()


class CircularQueue(Generic[T]):
    """Fixed-capacity FIFO queue on a ring of slots."""

    __slots__ = ("_capacity", "_front", "_size", "_slots")

    def __init__(self, capacity: int) -> None:
        """Create an empty ring with room for ``capacity`` elements. O(capacity)."""
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._slots: DynamicArray[Any] = DynamicArray.filled(capacity, None)
        self._front = 0
        self._size = 0

    @property
    def capacity(self) -> int:
        """Maximum number of elements. O(1)."""
        return self._capacity

    def __len__(self) -> int:
        """Number of waiting elements. O(1)."""
        return self._size

    def __bool__(self) -> bool:
        """True when something is waiting. O(1)."""
        return self._size > 0

    def is_empty(self) -> bool:
        """True when nothing is waiting. O(1)."""
        return self._size == 0

    def is_full(self) -> bool:
        """True when no slot is free. O(1)."""
        return self._size == self._capacity

    def __iter__(self) -> Iterator[T]:
        """Yield elements from front to back without removing them. O(n)."""
        for i in range(self._size):
            value: T = self._slots[(self._front + i) % self._capacity]
            yield value

    def enqueue(self, value: T) -> None:
        """Add ``value`` at the back. O(1). Raises OverflowError when full."""
        if self._size == self._capacity:
            raise OverflowError("enqueue on full CircularQueue")
        self._slots[(self._front + self._size) % self._capacity] = value
        self._size += 1

    def try_enqueue(self, value: T) -> bool:
        """Add ``value`` if there is room; return whether it was added. O(1)."""
        if self._size == self._capacity:
            return False
        self.enqueue(value)
        return True

    def dequeue(self) -> T:
        """Remove and return the front element. O(1)."""
        if self._size == 0:
            raise IndexError("dequeue from empty CircularQueue")
        value: T = self._slots[self._front]
        self._slots[self._front] = None
        self._front = (self._front + 1) % self._capacity
        self._size -= 1
        return value

    def peek(self) -> T:
        """Front element without removing it. O(1)."""
        if self._size == 0:
            raise IndexError("peek at empty CircularQueue")
        value: T = self._slots[self._front]
        return value


class Deque(Generic[T]):
    """Double-ended queue on a circular buffer that grows by doubling."""

    __slots__ = ("_capacity", "_front", "_size", "_slots")

    _INITIAL_CAPACITY = 8

    def __init__(self, items: Iterable[T] | None = None) -> None:
        """Create an empty deque, or one holding ``items`` front to back. O(n)."""
        self._capacity = self._INITIAL_CAPACITY
        self._slots: DynamicArray[Any] = DynamicArray.filled(self._capacity, None)
        self._front = 0
        self._size = 0
        if items is not None:
            for item in items:
                self.push_back(item)

    def _grow(self) -> None:
        """Copy into a ring twice as large, unwrapping to start at slot 0. O(n)."""
        new_capacity = 2 * self._capacity
        new_slots: DynamicArray[Any] = DynamicArray.filled(new_capacity, None)
        for i in range(self._size):
            new_slots[i] = self._slots[(self._front + i) % self._capacity]
        self._slots = new_slots
        self._capacity = new_capacity
        self._front = 0

    def __len__(self) -> int:
        """Number of elements. O(1)."""
        return self._size

    def __bool__(self) -> bool:
        """True when the deque is not empty. O(1)."""
        return self._size > 0

    def is_empty(self) -> bool:
        """True when the deque is empty. O(1)."""
        return self._size == 0

    def __iter__(self) -> Iterator[T]:
        """Yield elements from front to back without removing them. O(n)."""
        for i in range(self._size):
            value: T = self._slots[(self._front + i) % self._capacity]
            yield value

    def __getitem__(self, index: int) -> T:
        """Element ``index`` places from the front (negative from the back). O(1)."""
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("Deque index out of range")
        value: T = self._slots[(self._front + index) % self._capacity]
        return value

    def push_back(self, value: T) -> None:
        """Add ``value`` at the back. O(1) amortised."""
        if self._size == self._capacity:
            self._grow()
        self._slots[(self._front + self._size) % self._capacity] = value
        self._size += 1

    def push_front(self, value: T) -> None:
        """Add ``value`` at the front. O(1) amortised."""
        if self._size == self._capacity:
            self._grow()
        self._front = (self._front - 1) % self._capacity
        self._slots[self._front] = value
        self._size += 1

    def pop_front(self) -> T:
        """Remove and return the front element. O(1)."""
        if self._size == 0:
            raise IndexError("pop from empty Deque")
        value: T = self._slots[self._front]
        self._slots[self._front] = None
        self._front = (self._front + 1) % self._capacity
        self._size -= 1
        return value

    def pop_back(self) -> T:
        """Remove and return the back element. O(1)."""
        if self._size == 0:
            raise IndexError("pop from empty Deque")
        position = (self._front + self._size - 1) % self._capacity
        value: T = self._slots[position]
        self._slots[position] = None
        self._size -= 1
        return value

    def peek_front(self) -> T:
        """Front element without removing it. O(1)."""
        if self._size == 0:
            raise IndexError("peek at empty Deque")
        value: T = self._slots[self._front]
        return value

    def peek_back(self) -> T:
        """Back element without removing it. O(1)."""
        if self._size == 0:
            raise IndexError("peek at empty Deque")
        value: T = self._slots[(self._front + self._size - 1) % self._capacity]
        return value
