"""A last-in, first-out stack backed by a DynamicArray."""

from typing import Generic, TypeVar

from aom.core.dynamic_array import DynamicArray

T = TypeVar("T")


class Stack(Generic[T]):
    """A last-in, first-out collection."""

    def __init__(self) -> None:
        """Create an empty stack. Time: O(1)."""
        self._items: DynamicArray[T] = DynamicArray()

    def push(self, item: T) -> None:
        """Add an item to the top. Amortized time: O(1)."""
        self._items.append(item)

    def pop(self) -> T:
        """Remove and return the top item. Time: O(1)."""
        if len(self._items) == 0:
            raise IndexError("pop from empty Stack")
        return self._items.pop()

    def peek(self) -> T:
        """Return the top item without removing it. Time: O(1)."""
        if len(self._items) == 0:
            raise IndexError("peek from empty Stack")
        return self._items.get(len(self._items) - 1)
