"""A manually resized, array-backed sequence."""

from typing import Generic, TypeVar, cast

T = TypeVar("T")


class DynamicArray(Generic[T]):
    """A resizable array backed by fixed-capacity list storage."""

    def __init__(self, initial_capacity: int = 4) -> None:
        """Create an empty array with positive capacity. Time: O(initial_capacity)."""
        if (
            isinstance(initial_capacity, bool)
            or not isinstance(initial_capacity, int)
            or initial_capacity <= 0
        ):
            raise ValueError("initial_capacity must be a positive integer")

        self._items: list[T | None] = [None] * initial_capacity
        self._size = 0
        self._capacity = initial_capacity

    @property
    def capacity(self) -> int:
        """Return the allocated storage capacity. Time: O(1)."""
        return self._capacity

    def __len__(self) -> int:
        """Return the number of stored items. Time: O(1)."""
        return self._size

    def append(self, item: T) -> None:
        """Add an item, doubling storage if full. Amortized time: O(1); worst case: O(n)."""
        if self._size == self._capacity:
            new_capacity = self._capacity * 2
            new_items: list[T | None] = [None] * new_capacity
            for index in range(self._size):
                new_items[index] = self._items[index]
            self._items = new_items
            self._capacity = new_capacity

        self._items[self._size] = item
        self._size += 1

    def get(self, index: int) -> T:
        """Return the item at index. Time: O(1)."""
        if index < 0 or index >= self._size:
            raise IndexError("DynamicArray index out of range")
        return cast(T, self._items[index])

    def set(self, index: int, item: T) -> None:
        """Replace the item at index. Time: O(1)."""
        if index < 0 or index >= self._size:
            raise IndexError("DynamicArray index out of range")
        self._items[index] = item

    def pop(self) -> T:
        """Remove and return the final item without shrinking storage. Time: O(1)."""
        if self._size == 0:
            raise IndexError("pop from empty DynamicArray")

        self._size -= 1
        item = self._items[self._size]
        self._items[self._size] = None
        return cast(T, item)
