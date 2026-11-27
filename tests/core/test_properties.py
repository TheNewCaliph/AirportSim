"""Property tests: each structure against a built-in oracle.

Hypothesis generates hundreds of random operation sequences per test and
shrinks any failure to the smallest sequence that breaks. Built-ins (list,
collections.deque, dict, sorted, bisect) are allowed here because they are
only the reference answer, never part of aom/core.
"""

from __future__ import annotations

import bisect
from collections import deque
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from aom.core.avl import AVLTree, _AVLNode
from aom.core.bst import BinarySearchTree
from aom.core.dynamic_array import DynamicArray
from aom.core.linked_list import SinglyLinkedList
from aom.core.queues import CircularQueue, Deque, Queue
from aom.core.searching import binary_search, linear_search, lower_bound, upper_bound
from aom.core.sorting import (
    bubble_sort,
    insertion_sort,
    merge_sort,
    quick_sort,
    selection_sort,
)

small_ints = st.integers(min_value=-50, max_value=50)
keys = st.integers(min_value=0, max_value=60)

# --------------------------------------------------------------- dynamic array

array_ops = st.lists(
    st.one_of(
        st.tuples(st.just("append"), small_ints),
        st.tuples(st.just("pop"), st.integers(0, 100)),
        st.tuples(st.just("insert"), st.integers(0, 100), small_ints),
        st.tuples(st.just("set"), st.integers(0, 100), small_ints),
        st.tuples(st.just("remove"), small_ints),
    ),
    max_size=200,
)


@given(array_ops)
def test_dynamic_array_matches_list(ops: list[tuple[Any, ...]]) -> None:
    ours: DynamicArray[int] = DynamicArray()
    oracle: list[int] = []
    for op in ops:
        if op[0] == "append":
            ours.append(op[1])
            oracle.append(op[1])
        elif op[0] == "pop" and oracle:
            i = op[1] % len(oracle)
            assert ours.pop(i) == oracle.pop(i)
        elif op[0] == "insert":
            i = op[1] % (len(oracle) + 1)
            ours.insert(i, op[2])
            oracle.insert(i, op[2])
        elif op[0] == "set" and oracle:
            i = op[1] % len(oracle)
            ours[i] = op[2]
            oracle[i] = op[2]
        elif op[0] == "remove":
            expected = op[1] in oracle
            if expected:
                oracle.remove(op[1])
            assert ours.remove(op[1]) == expected
        assert len(ours) == len(oracle)
        assert ours.capacity >= len(ours)
    assert ours.to_list() == oracle


# ----------------------------------------------------------------- linked list


@given(st.lists(small_ints, max_size=100))
def test_insert_sorted_matches_sorted(values: list[int]) -> None:
    lst: SinglyLinkedList[int] = SinglyLinkedList()
    for v in values:
        lst.insert_sorted(v)
    assert lst.to_list() == sorted(values)
    assert len(lst) == len(values)


@given(st.lists(st.tuples(st.booleans(), small_ints), max_size=150))
def test_linked_list_ends_match_deque(ops: list[tuple[bool, int]]) -> None:
    lst: SinglyLinkedList[int] = SinglyLinkedList()
    oracle: deque[int] = deque()
    for push, value in ops:
        if push:
            lst.append(value)
            oracle.append(value)
        elif oracle:
            assert lst.pop_front() == oracle.popleft()
    assert lst.to_list() == list(oracle)


# ---------------------------------------------------------------------- queues


@given(st.lists(st.one_of(small_ints, st.none()), max_size=200))
def test_queue_matches_deque(ops: list[int | None]) -> None:
    q: Queue[int] = Queue()
    oracle: deque[int] = deque()
    for op in ops:
        if op is None:
            if oracle:
                assert q.dequeue() == oracle.popleft()
        else:
            q.enqueue(op)
            oracle.append(op)
    assert list(q) == list(oracle)


@given(st.integers(1, 8), st.lists(st.one_of(small_ints, st.none()), max_size=200))
def test_circular_queue_matches_bounded_deque(capacity: int, ops: list[int | None]) -> None:
    q: CircularQueue[int] = CircularQueue(capacity)
    oracle: deque[int] = deque()
    for op in ops:
        if op is None:
            if oracle:
                assert q.dequeue() == oracle.popleft()
        else:
            accepted = len(oracle) < capacity
            if accepted:
                oracle.append(op)
            assert q.try_enqueue(op) == accepted
        assert len(q) == len(oracle)
    assert list(q) == list(oracle)


deque_ops = st.lists(
    st.one_of(
        st.tuples(st.sampled_from(["push_front", "push_back"]), small_ints),
        st.tuples(st.sampled_from(["pop_front", "pop_back"]), st.just(0)),
    ),
    max_size=300,
)


@given(deque_ops)
def test_deque_matches_collections_deque(ops: list[tuple[str, int]]) -> None:
    d: Deque[int] = Deque()
    oracle: deque[int] = deque()
    for name, value in ops:
        if name == "push_front":
            d.push_front(value)
            oracle.appendleft(value)
        elif name == "push_back":
            d.push_back(value)
            oracle.append(value)
        elif oracle:
            if name == "pop_front":
                assert d.pop_front() == oracle.popleft()
            else:
                assert d.pop_back() == oracle.pop()
    assert list(d) == list(oracle)


# ----------------------------------------------------------------------- trees

tree_ops = st.lists(st.tuples(st.booleans(), keys), max_size=300)


def _avl_height(node: _AVLNode[Any, Any] | None) -> int:
    if node is None:
        return 0
    left, right = _avl_height(node.left), _avl_height(node.right)
    assert node.height == 1 + max(left, right)
    assert abs(left - right) <= 1
    return node.height


@given(tree_ops)
def test_bst_matches_dict(ops: list[tuple[bool, int]]) -> None:
    tree: BinarySearchTree[int, int] = BinarySearchTree()
    oracle: dict[int, int] = {}
    for step, (insert, key) in enumerate(ops):
        if insert:
            assert tree.insert(key, step) == (key not in oracle)
            oracle[key] = step
        else:
            assert tree.delete(key) == (key in oracle)
            oracle.pop(key, None)
    assert list(tree.items()) == sorted(oracle.items())
    for key in range(61):
        assert tree.search(key) == oracle.get(key)


@settings(max_examples=200)
@given(tree_ops)
def test_avl_matches_dict_and_stays_balanced(ops: list[tuple[bool, int]]) -> None:
    tree: AVLTree[int, int] = AVLTree()
    oracle: dict[int, int] = {}
    for step, (insert, key) in enumerate(ops):
        if insert:
            assert tree.insert(key, step) == (key not in oracle)
            oracle[key] = step
        else:
            assert tree.delete(key) == (key in oracle)
            oracle.pop(key, None)
        assert len(tree) == len(oracle)
    _avl_height(tree._root)
    assert list(tree.items()) == sorted(oracle.items())


@given(st.lists(keys, max_size=150), keys, keys)
def test_avl_range_matches_filter(values: list[int], a: int, b: int) -> None:
    tree: AVLTree[int, None] = AVLTree()
    for v in values:
        tree.insert(v, None)
    lo, hi = min(a, b), max(a, b)
    expected = sorted({v for v in values if lo <= v <= hi})
    assert [k for k, _ in tree.range(lo, hi)] == expected
    assert [k for k, _ in tree.range(lo=lo)] == sorted({v for v in values if v >= lo})


# ------------------------------------------------------------ sorts and search

pairs = st.lists(st.tuples(st.integers(0, 10), st.integers()), max_size=120)


@given(pairs)
def test_every_sort_matches_sorted(data: list[tuple[int, int]]) -> None:
    for sort in (insertion_sort, selection_sort, bubble_sort, merge_sort, quick_sort):
        items = DynamicArray(data)
        sort(items, key=lambda p: p[0])
        assert [p[0] for p in items] == sorted(p[0] for p in data)


@given(pairs)
def test_stable_sorts_match_sorted_exactly(data: list[tuple[int, int]]) -> None:
    expected = sorted(data, key=lambda p: p[0])  # Python's sort is stable
    for sort in (insertion_sort, bubble_sort, merge_sort):
        items = list(data)
        sort(items, key=lambda p: p[0])
        assert items == expected


@given(st.lists(small_ints, max_size=100), small_ints)
def test_searches_match_bisect(values: list[int], target: int) -> None:
    data = sorted(values)
    items = DynamicArray(data)
    assert lower_bound(items, target) == bisect.bisect_left(data, target)
    assert upper_bound(items, target) == bisect.bisect_right(data, target)
    expected = data.index(target) if target in data else -1
    assert binary_search(items, target) == expected
    assert linear_search(items, target) == expected
