"""A generic hash table implemented with separate chaining."""

from __future__ import annotations

from collections.abc import Hashable
from typing import Generic, TypeVar

from aom.core.dynamic_array import DynamicArray

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class _Node(Generic[K, V]):
    """A key-value pair linked to the next entry in a bucket."""

    def __init__(self, key: K, value: V, next_node: _Node[K, V] | None = None) -> None:
        self.key = key
        self.value = value
        self.next = next_node


class HashTable(Generic[K, V]):
    """A hash table that resolves collisions with linked chains."""

    def __init__(self) -> None:
        """Create an empty table with four buckets. Time: O(1)."""
        self._buckets: DynamicArray[_Node[K, V] | None] = DynamicArray(capacity=4)
        for _ in range(4):
            self._buckets.append(None)
        self._size = 0

    def put(self, key: K, value: V) -> None:
        """Insert or update a value. Average time: O(1); worst case: O(n)."""
        bucket_count = len(self._buckets)
        index = hash(key) % bucket_count
        node = self._buckets.get(index)

        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        if (self._size + 1) * 4 >= bucket_count * 3:
            self._resize()
            bucket_count = len(self._buckets)
            index = hash(key) % bucket_count

        self._buckets.set(index, _Node(key, value, self._buckets.get(index)))
        self._size += 1

    def get(self, key: K) -> V:
        """Return the value for a key or raise KeyError. Average time: O(1); worst: O(n)."""
        index = hash(key) % len(self._buckets)
        node = self._buckets.get(index)

        while node is not None:
            if node.key == key:
                return node.value
            node = node.next

        raise KeyError(key)

    def remove(self, key: K) -> V:
        """Remove and return a key's value or raise KeyError. Average time: O(1); worst: O(n)."""
        index = hash(key) % len(self._buckets)
        previous: _Node[K, V] | None = None
        node = self._buckets.get(index)

        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets.set(index, node.next)
                else:
                    previous.next = node.next
                self._size -= 1
                return node.value
            previous = node
            node = node.next

        raise KeyError(key)

    def __len__(self) -> int:
        """Return the number of stored key-value pairs. Time: O(1)."""
        return self._size

    def _resize(self) -> None:
        """Double the bucket count and rehash every entry. Time: O(n)."""
        old_buckets = self._buckets
        new_bucket_count = len(old_buckets) * 2
        new_buckets: DynamicArray[_Node[K, V] | None] = DynamicArray(capacity=new_bucket_count)
        for _ in range(new_bucket_count):
            new_buckets.append(None)

        for old_index in range(len(old_buckets)):
            node = old_buckets.get(old_index)
            while node is not None:
                next_node = node.next
                new_index = hash(node.key) % new_bucket_count
                node.next = new_buckets.get(new_index)
                new_buckets.set(new_index, node)
                node = next_node

        self._buckets = new_buckets
