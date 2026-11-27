"""Unit tests for AVLTree: rotations, balance and deletes."""

from __future__ import annotations

import math
from typing import Any

from aom.core.avl import AVLTree, _AVLNode


def _check_invariants(node: _AVLNode[Any, Any] | None, lo: Any = None, hi: Any = None) -> int:
    """Return the subtree height, asserting order, stored heights and balance."""
    if node is None:
        return 0
    assert lo is None or lo < node.key
    assert hi is None or node.key < hi
    left = _check_invariants(node.left, lo, node.key)
    right = _check_invariants(node.right, node.key, hi)
    assert node.height == 1 + max(left, right)
    assert abs(left - right) <= 1
    return node.height


def _tree(keys: list[int]) -> AVLTree[int, int]:
    t: AVLTree[int, int] = AVLTree()
    for k in keys:
        t.insert(k, k * 10)
    return t


def test_ll_case_rotates_right() -> None:
    t = _tree([3, 2, 1])
    assert t.rotations.ll == 1
    assert t._root is not None and t._root.key == 2
    _check_invariants(t._root)


def test_rr_case_rotates_left() -> None:
    t = _tree([1, 2, 3])
    assert t.rotations.rr == 1
    assert t._root is not None and t._root.key == 2


def test_lr_case_double_rotation() -> None:
    t = _tree([3, 1, 2])
    assert t.rotations.lr == 1
    assert t._root is not None and t._root.key == 2


def test_rl_case_double_rotation() -> None:
    t = _tree([1, 3, 2])
    assert t.rotations.rl == 1
    assert t._root is not None and t._root.key == 2


def test_viva_exercise_insert_1_to_7() -> None:
    """Team Guide exercise: 1..7 in order gives a perfect tree after 4 RR rotations."""
    t = _tree([1, 2, 3, 4, 5, 6, 7])
    assert t.rotations.rr == 4
    assert t.rotations.total() == 4
    assert t.height() == 3
    assert t._root is not None and t._root.key == 4


def test_sorted_inserts_stay_logarithmic() -> None:
    n = 10_000
    t = _tree(list(range(n)))
    _check_invariants(t._root)
    assert t.height() <= 1.45 * math.log2(n + 2)
    assert t.search(9_999) == 99_990


def test_delete_rebalances() -> None:
    t = _tree(list(range(1, 32)))
    for k in range(1, 32, 2):
        assert t.delete(k)
        _check_invariants(t._root)
    assert list(t.keys()) == list(range(2, 32, 2))
    assert not t.delete(1)
    assert len(t) == 15


def test_replace_value_and_min_max() -> None:
    t = _tree([5, 3, 8])
    assert not t.insert(3, -1)
    assert t.search(3) == -1
    assert t.min_key() == 3
    assert t.max_key() == 8
    assert list(t.values()) == [-1, 50, 80]


def test_tuple_keys_allow_shared_minutes() -> None:
    """How M1 uses it: (departure minute, flight id) keeps keys unique."""
    t: AVLTree[tuple[int, str], str] = AVLTree()
    for minute, fid in [(900, "PK301"), (900, "EK601"), (840, "PA210")]:
        t.insert((minute, fid), fid)
    assert list(t.values()) == ["PA210", "EK601", "PK301"]
