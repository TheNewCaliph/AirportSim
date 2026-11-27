"""Binary search tree (unbalanced) mapping keys to values.

Every node's left subtree holds smaller keys and its right subtree larger
ones, so search, insert and delete follow one root-to-leaf path: O(h), where h
is the height. For random keys h is about 1.39 log2 n, but keys inserted in
sorted order (like a day's departure times) produce a chain with h = n. This
tree is the baseline for the BST-versus-AVL experiment, which is why it is
kept deliberately simple and unbalanced.

All operations are iterative, so even a degenerate tree of 100 000 nodes
never hits Python's recursion limit.
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar  # noqa: UP035

from aom.core.compare import K
from aom.core.dynamic_array import DynamicArray
from aom.core.queues import Queue

V = TypeVar("V")


class _BSTNode(Generic[K, V]):
    __slots__ = ("key", "left", "right", "value")

    def __init__(self, key: K, value: V) -> None:
        self.key = key
        self.value = value
        self.left: _BSTNode[K, V] | None = None
        self.right: _BSTNode[K, V] | None = None


class BinarySearchTree(Generic[K, V]):
    """An unbalanced BST map. Keys are unique; inserting an existing key replaces its value."""

    __slots__ = ("_root", "_size")

    def __init__(self) -> None:
        """Create an empty tree. O(1)."""
        self._root: _BSTNode[K, V] | None = None
        self._size = 0

    def __len__(self) -> int:
        """Number of keys. O(1)."""
        return self._size

    def __bool__(self) -> bool:
        """True when the tree holds at least one key. O(1)."""
        return self._size > 0

    def is_empty(self) -> bool:
        """True when the tree holds no keys. O(1)."""
        return self._size == 0

    # ------------------------------------------------------------------ search

    def _find(self, key: K) -> _BSTNode[K, V] | None:
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
        """Value stored under ``key``, or None if absent. O(h)."""
        node = self._find(key)
        return None if node is None else node.value

    def __contains__(self, key: K) -> bool:
        """True if ``key`` is in the tree. O(h)."""
        return self._find(key) is not None

    def min_key(self) -> K:
        """Smallest key: keep going left. O(h)."""
        if self._root is None:
            raise KeyError("min_key of empty tree")
        node = self._root
        while node.left is not None:
            node = node.left
        return node.key

    def max_key(self) -> K:
        """Largest key: keep going right. O(h)."""
        if self._root is None:
            raise KeyError("max_key of empty tree")
        node = self._root
        while node.right is not None:
            node = node.right
        return node.key

    # ------------------------------------------------------------------ insert

    def insert(self, key: K, value: V) -> bool:
        """Store ``value`` under ``key``. True if the key is new. O(h)."""
        if self._root is None:
            self._root = _BSTNode(key, value)
            self._size = 1
            return True
        node = self._root
        while True:
            if key < node.key:
                if node.left is None:
                    node.left = _BSTNode(key, value)
                    break
                node = node.left
            elif node.key < key:
                if node.right is None:
                    node.right = _BSTNode(key, value)
                    break
                node = node.right
            else:
                node.value = value
                return False
        self._size += 1
        return True

    # ------------------------------------------------------------------ delete

    def delete(self, key: K) -> bool:
        """Remove ``key`` and its value. True if it was present. O(h).

        Three cases: a leaf is simply unlinked; a node with one child is
        replaced by that child; a node with two children takes the key and
        value of its in-order successor (the smallest key in its right
        subtree), and the successor, which has no left child, is unlinked.
        """
        parent: _BSTNode[K, V] | None = None
        node = self._root
        while node is not None:
            if key < node.key:
                parent, node = node, node.left
            elif node.key < key:
                parent, node = node, node.right
            else:
                break
        if node is None:
            return False

        if node.left is not None and node.right is not None:
            succ_parent = node
            succ = node.right
            while succ.left is not None:
                succ_parent, succ = succ, succ.left
            node.key, node.value = succ.key, succ.value
            parent, node = succ_parent, succ  # now delete the successor instead

        child = node.left if node.left is not None else node.right
        if parent is None:
            self._root = child
        elif parent.left is node:
            parent.left = child
        else:
            parent.right = child
        self._size -= 1
        return True

    # -------------------------------------------------------------- traversals

    def items(self) -> Iterator[tuple[K, V]]:
        """Yield (key, value) pairs in ascending key order. O(n) in total.

        In-order traversal with an explicit stack: walk left pushing nodes,
        visit the top, then move to its right subtree.
        """
        stack: DynamicArray[_BSTNode[K, V]] = DynamicArray()
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

    def height(self) -> int:
        """Number of nodes on the longest root-to-leaf path (0 if empty). O(n).

        Level-order traversal with our queue, counting levels.
        """
        if self._root is None:
            return 0
        level: Queue[_BSTNode[K, V]] = Queue([self._root])
        height = 0
        while not level.is_empty():
            height += 1
            next_level: Queue[_BSTNode[K, V]] = Queue()
            while not level.is_empty():
                node = level.dequeue()
                if node.left is not None:
                    next_level.enqueue(node.left)
                if node.right is not None:
                    next_level.enqueue(node.right)
            level = next_level
        return height
