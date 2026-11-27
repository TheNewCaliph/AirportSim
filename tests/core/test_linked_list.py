"""Unit tests for SinglyLinkedList."""

import pytest

from aom.core.linked_list import SinglyLinkedList


def test_append_prepend_order() -> None:
    lst: SinglyLinkedList[int] = SinglyLinkedList()
    lst.append(2)
    lst.append(3)
    lst.prepend(1)
    assert lst.to_list() == [1, 2, 3]
    assert len(lst) == 3
    assert lst.peek_front() == 1
    assert lst.peek_back() == 3


def test_pop_front_until_empty_resets_tail() -> None:
    lst = SinglyLinkedList([1, 2])
    assert lst.pop_front() == 1
    assert lst.pop_front() == 2
    assert lst.is_empty()
    with pytest.raises(IndexError):
        lst.pop_front()
    lst.append(5)  # tail must have been reset, or this would be lost
    assert lst.to_list() == [5]
    assert lst.peek_back() == 5


def test_insert_sorted_keeps_order() -> None:
    lst: SinglyLinkedList[int] = SinglyLinkedList()
    for x in [5, 1, 4, 2, 3, 0, 6]:
        lst.insert_sorted(x)
    assert lst.to_list() == [0, 1, 2, 3, 4, 5, 6]
    assert lst.peek_back() == 6


def test_insert_sorted_is_stable_with_key() -> None:
    lst: SinglyLinkedList[tuple[int, str]] = SinglyLinkedList()
    for item in [(2, "a"), (1, "b"), (2, "c"), (1, "d")]:
        lst.insert_sorted(item, key=lambda pair: pair[0])
    assert lst.to_list() == [(1, "b"), (1, "d"), (2, "a"), (2, "c")]


def test_remove_head_middle_tail() -> None:
    lst = SinglyLinkedList([1, 2, 3, 4])
    assert lst.remove(1)
    assert lst.remove(3)
    assert lst.remove(4)
    assert not lst.remove(9)
    assert lst.to_list() == [2]
    assert lst.peek_back() == 2
    lst.append(7)
    assert lst.to_list() == [2, 7]


def test_find_contains_clear() -> None:
    lst = SinglyLinkedList(["KHI", "LHE", "ISB"])
    assert "LHE" in lst
    assert lst.find(lambda s: s.startswith("I")) == "ISB"
    assert lst.find(lambda s: s == "DXB") is None
    lst.clear()
    assert len(lst) == 0
    with pytest.raises(IndexError):
        lst.peek_front()
