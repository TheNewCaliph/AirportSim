"""AVL tree: a self-balancing binary search tree mapping keys to values.

Every node stores its height. After an insert or delete, each node on the way
back up checks its balance factor, height(left) - height(right). If that
reaches +2 or -2, one or two rotations restore it to -1, 0 or +1:

* LL (left child is left-heavy or even): one right rotation.
* RR (right child is right-heavy or even): one left rotation.
* LR (left child is right-heavy): left-rotate the child, then right-rotate.
* RL (right child is left-heavy): right-rotate the child, then left-rotate.

That keeps the height below 1.44 log2(n + 2), so search, insert and delete are
O(log n) even when keys arrive in sorted order, which is exactly how a day's
departure times arrive.

M1 keeps two of these: one keyed by (scheduled departure, flight id) and one by
(estimated departure, flight id). The flight id in the key keeps keys unique
when several flights share a minute.
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar  # noqa: UP035

from aom.core.compare import K
from aom.core.dynamic_array import DynamicArray

V = TypeVar("V")


class _AVLNode(Generic[K, V]):
    __slots__ = ("height", "key", "left", "right", "value")

    def __init__(self, key: K, value: V) -> None:
        self.key = key
        self.value = value
        self.left: _AVLNode[K, V] | None = None
        self.right: _AVLNode[K, V] | None = None
        self.height = 1


def _height(node: _AVLNode[K, V] | None) -> int:
    return 0 if node is None else node.height


def _update(node: _AVLNode[K, V]) -> None:
    node.height = 1 + max(_height(node.left), _height(node.right))


def _balance(node: _AVLNode[K, V]) -> int:
    return _height(node.left) - _height(node.right)


class RotationCounts:
    """How many times each rebalancing case has fired (for tests and the viva)."""

    __slots__ = ("ll", "lr", "rl", "rr")

    def __init__(self) -> None:
        self.ll = 0
        self.rr = 0
        self.lr = 0
        self.rl = 0

    def total(self) -> int:
        """Total rebalancing cases handled. O(1)."""
        return self.ll + self.rr + self.lr + self.rl


class AVLTree(Generic[K, V]):
    """A height-balanced BST map. Keys are unique; inserting an existing key replaces its value."""

    __slots__ = ("_root", "_size", "rotations")

    def __init__(self) -> None:
        """Create an empty tree. O(1)."""
        self._root: _AVLNode[K, V] | None = None
        self._size = 0
        self.rotations = RotationCounts()

    def __len__(self) -> int:
        """Number of keys. O(1)."""
        return self._size

    def __bool__(self) -> bool:
        """True when the tree holds at least one key. O(1)."""
        return self._size > 0

    def is_empty(self) -> bool:
        """True when the tree holds no keys. O(1)."""
        return self._size == 0

    def height(self) -> int:
        """Number of nodes on the longest root-to-leaf path (0 if empty). O(1)."""
        return _height(self._root)

    # --------------------------------------------------------------- rotations

    @staticmethod
    def _rotate_right(y: _AVLNode[K, V]) -> _AVLNode[K, V]:
        """Lift y's left child x above y. O(1).

        ::

                y            x
               / \\          / \\
              x   C   ->   A   y
             / \\              / \\
            A   B            B   C
        """
        x = y.left
        assert x is not None
        y.left = x.right
        x.right = y
        _update(y)
        _update(x)
        return x

    @staticmethod
    def _rotate_left(x: _AVLNode[K, V]) -> _AVLNode[K, V]:
        """Lift x's right child y above x (mirror of _rotate_right). O(1)."""
        y = x.right
        assert y is not None
        x.right = y.left
        y.left = x
        _update(x)
        _update(y)
        return y

    def _rebalance(self, node: _AVLNode[K, V]) -> _AVLNode[K, V]:
        """Fix node's height and, if it is out of balance, rotate. O(1)."""
        _update(node)
        balance = _balance(node)
        if balance > 1:
            assert node.left is not None
            if _balance(node.left) >= 0:
                self.rotations.ll += 1
            else:
                self.rotations.lr += 1
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1:
            assert node.right is not None
            if _balance(node.right) <= 0:
                self.rotations.rr += 1
            else:
                self.rotations.rl += 1
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    # ------------------------------------------------------------------ search

    def _find(self, key: K) -> _AVLNode[K, V] | None:
        node = self._root
        while node is not None:
            if key < node.key:
                node = node.left
            elif node.key < key:
                node = node.right
            else:
                return node
        return None

    def search(self, key: K) -> V | None:
        """Value stored under ``key``, or None if absent. O(log n)."""
        node = self._find(key)
        return None if node is None else node.value

    def __contains__(self, key: K) -> bool:
        """True if ``key`` is in the tree. O(log n)."""
        return self._find(key) is not None

    def min_key(self) -> K:
        """Smallest key. O(log n)."""
        if self._root is None:
            raise KeyError("min_key of empty tree")
        node = self._root
        while node.left is not None:
            node = node.left
        return node.key

    def max_key(self) -> K:
        """Largest key. O(log n)."""
        if self._root is None:
            raise KeyError("max_key of empty tree")
        node = self._root
        while node.right is not None:
            node = node.right
        return node.key

    # ------------------------------------------------------------------ insert

    def insert(self, key: K, value: V) -> bool:
        """Store ``value`` under ``key``, rebalancing on the way up. True if new. O(log n)."""
        size_before = self._size
        self._root = self._insert(self._root, key, value)
        return self._size > size_before

    def _insert(self, node: _AVLNode[K, V] | None, key: K, value: V) -> _AVLNode[K, V]:
        if node is None:
            self._size += 1
            return _AVLNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif node.key < key:
            node.right = self._insert(node.right, key, value)
        else:
            node.value = value
            return node
        return self._rebalance(node)

    # ------------------------------------------------------------------ delete

    def delete(self, key: K) -> bool:
        """Remove ``key`` and its value, rebalancing on the way up. True if present. O(log n)."""
        size_before = self._size
        self._root = self._delete(self._root, key)
        return self._size < size_before

    def _delete(self, node: _AVLNode[K, V] | None, key: K) -> _AVLNode[K, V] | None:
        if node is None:
            return None
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif node.key < key:
            node.right = self._delete(node.right, key)
        else:
            if node.left is None or node.right is None:
                self._size -= 1
                return node.left if node.left is not None else node.right
            succ = node.right
            while succ.left is not None:
                succ = succ.left
            node.key, node.value = succ.key, succ.value
            node.right = self._delete(node.right, succ.key)
        return self._rebalance(node)

    # -------------------------------------------------------------- traversals

    def items(self) -> Iterator[tuple[K, V]]:
        """Yield (key, value) pairs in ascending key order. O(n) in total."""
        stack: DynamicArray[_AVLNode[K, V]] = DynamicArray()
        node = self._root
        while node is not None or not stack.is_empty():
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            yield node.key, node.value
            node = node.right

    def keys(self) -> Iterator[K]:
        """Yield keys in ascending order. O(n) in total."""
        for key, _ in self.items():
            yield key

    def values(self) -> Iterator[V]:
        """Yield values in ascending key order. O(n) in total."""
        for _, value in self.items():
            yield value

    # ------------------------------------------------------------ range query

    def range(self, lo: K | None = None, hi: K | None = None) -> Iterator[tuple[K, V]]:
        """Yield (key, value) pairs with lo <= key <= hi, in ascending order.

        Either bound may be None to leave that side open, so ``range(lo=t)``
        is "everything from t on". O(log n + k) for k results: the walk goes
        down one path to the first key >= lo, then reads keys in order and
        stops at the first key > hi. Subtrees entirely below lo are skipped.
        """
        stack: DynamicArray[_AVLNode[K, V]] = DynamicArray()
        node = self._root
        while node is not None or not stack.is_empty():
            while node is not None:
                if lo is not None and node.key < lo:
                    node = node.right  # node and its left subtree are all < lo
                else:
                    stack.append(node)
                    node = node.left
            if stack.is_empty():
                return
            node = stack.pop()
            if hi is not None and hi < node.key:
                return  # every later key is larger still
            yield node.key, node.value
            node = node.right

    def count_range(self, lo: K | None = None, hi: K | None = None) -> int:
        """Number of keys with lo <= key <= hi. O(log n + k)."""
        count = 0
        for _ in self.range(lo, hi):
            count += 1
        return count
