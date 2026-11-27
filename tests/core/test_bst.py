"""Unit tests for BinarySearchTree."""

import pytest

from aom.core.bst import BinarySearchTree


def _tree(keys: list[int]) -> BinarySearchTree[int, str]:
    t: BinarySearchTree[int, str] = BinarySearchTree()
    for k in keys:
        t.insert(k, f"v{k}")
    return t


def test_insert_search_and_order() -> None:
    t = _tree([50, 30, 70, 20, 40, 60, 80])
    assert len(t) == 7
    assert t.search(40) == "v40"
    assert t.search(45) is None
    assert 60 in t
    assert list(t.keys()) == [20, 30, 40, 50, 60, 70, 80]
    assert t.min_key() == 20
    assert t.max_key() == 80
    assert t.height() == 3


def test_insert_existing_key_replaces_value() -> None:
    t = _tree([1, 2])
    assert not t.insert(2, "new")
    assert t.search(2) == "new"
    assert len(t) == 2


def test_delete_leaf_one_child_two_children() -> None:
    t = _tree([50, 30, 70, 20, 40, 60, 80, 65])
    assert t.delete(20)  # leaf
    assert t.delete(60)  # one child (65)
    assert t.delete(50)  # two children: the root takes its successor
    assert not t.delete(999)
    assert list(t.keys()) == [30, 40, 65, 70, 80]
    assert len(t) == 5
    assert t.search(65) == "v65"


def test_delete_down_to_empty() -> None:
    t = _tree([2, 1, 3])
    for k in (2, 1, 3):
        assert t.delete(k)
    assert t.is_empty()
    assert t.height() == 0
    with pytest.raises(KeyError):
        t.min_key()


def test_sorted_inserts_make_a_chain() -> None:
    """The weakness the AVL tree fixes: sorted keys give height n."""
    t = _tree(list(range(1, 501)))
    assert t.height() == 500
    assert t.search(500) == "v500"
