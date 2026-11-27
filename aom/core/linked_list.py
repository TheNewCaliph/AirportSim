"""Singly linked list with a tail pointer.

Each node holds a value and a reference to the next node. Keeping a pointer to
the last node as well as the first makes appending O(1), which is what a FIFO
queue needs. ``insert_sorted`` walks from the head to the first larger value,
so the list can be kept in order without ever sorting it.

Used by: the queue in this package, and Rabeet's graph (adjacency lists).
"""

from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, Iterator, TypeVar  # noqa: UP035

T = TypeVar("T")


def _identity(item: Any) -> Any:
    return item


class _Node(Generic[T]):
    """One link: a value and the next node (or None at the end)."""

    __slots__ = ("next", "value")

    def __init__(self, value: T, next_node: _Node[T] | None = None) -> None:
        self.value = value
        self.next = next_node


class SinglyLinkedList(Generic[T]):
    """A chain of nodes with O(1) access to both ends."""

    __slots__ = ("_head", "_size", "_tail")

    def __init__(self, items: Iterable[T] | None = None) -> None:
        """Create an empty list, or one holding ``items`` in order. O(n)."""
        self._head: _Node[T] | None = None
        self._tail: _Node[T] | None = None
        self._size = 0
        if items is not None:
            for item in items:
                self.append(item)

    # ------------------------------------------------------------------ queries

    def __len__(self) -> int:
        """Number of nodes. O(1)."""
        return self._size

    def __bool__(self) -> bool:
        """True when the list has at least one node. O(1)."""
        return self._size > 0

    def is_empty(self) -> bool:
        """True when the list has no nodes. O(1)."""
        return self._size == 0

    def __iter__(self) -> Iterator[T]:
        """Yield values from head to tail. O(n) for the full walk."""
        node = self._head
        while node is not None:
            yield node.value
            node = node.next

    def __contains__(self, value: object) -> bool:
        """True if some node holds ``value``. O(n)."""
        return any(item == value for item in self)

    def __repr__(self) -> str:
        """Readable form such as ``SinglyLinkedList([1, 2, 3])``. O(n)."""
        return "SinglyLinkedList([" + ", ".join(repr(v) for v in self) + "])"

    def peek_front(self) -> T:
        """Value at the head. O(1)."""
        if self._head is None:
            raise IndexError("peek at empty SinglyLinkedList")
        return self._head.value

    def peek_back(self) -> T:
        """Value at the tail. O(1)."""
        if self._tail is None:
            raise IndexError("peek at empty SinglyLinkedList")
        return self._tail.value

    def find(self, matches: Callable[[T], bool]) -> T | None:
        """First value for which ``matches`` is true, or None. O(n)."""
        for value in self:
            if matches(value):
                return value
        return None

    def to_list(self) -> list[T]:
        """Copy the values into a Python list (for tests and printing). O(n)."""
        out: list[T] = []
        for value in self:
            out.append(value)
        return out

    # ---------------------------------------------------------------- mutations

    def prepend(self, value: T) -> None:
        """Add ``value`` at the head. O(1)."""
        node = _Node(value, self._head)
        self._head = node
        if self._tail is None:
            self._tail = node
        self._size += 1

    def append(self, value: T) -> None:
        """Add ``value`` at the tail, using the tail pointer. O(1)."""
        node: _Node[T] = _Node(value)
        if self._tail is None:
            self._head = node
        else:
            self._tail.next = node
        self._tail = node
        self._size += 1

    def pop_front(self) -> T:
        """Remove and return the head value. O(1)."""
        if self._head is None:
            raise IndexError("pop from empty SinglyLinkedList")
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return node.value

    def insert_sorted(self, value: T, key: Callable[[T], Any] | None = None) -> None:
        """Insert ``value`` after every value whose key is <= its key. O(n).

        If the list is already in ascending key order it stays in order, and
        equal keys keep their insertion order (the insert is stable). Appending
        a value that belongs at the end costs O(1) thanks to the tail check.
        """
        kf: Callable[[T], Any] = key if key is not None else _identity
        k = kf(value)
        if self._head is None or k < kf(self._head.value):
            self.prepend(value)
            return
        assert self._tail is not None
        if not k < kf(self._tail.value):
            self.append(value)
            return
        prev = self._head
        while prev.next is not None and not k < kf(prev.next.value):
            prev = prev.next
        prev.next = _Node(value, prev.next)
        self._size += 1

    def remove(self, value: T) -> bool:
        """Unlink the first node holding ``value``; False if absent. O(n)."""
        return self.remove_first(lambda item: item == value)

    def remove_first(self, matches: Callable[[T], bool]) -> bool:
        """Unlink the first node for which ``matches`` is true. O(n)."""
        prev: _Node[T] | None = None
        node = self._head
        while node is not None:
            if matches(node.value):
                if prev is None:
                    self._head = node.next
                else:
                    prev.next = node.next
                if node is self._tail:
                    self._tail = prev
                self._size -= 1
                return True
            prev = node
            node = node.next
        return False

    def clear(self) -> None:
        """Drop every node. O(1)."""
        self._head = None
        self._tail = None
        self._size = 0
