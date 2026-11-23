"""Unit tests for DynamicArray."""

import pytest

from aom.core.dynamic_array import DynamicArray


def test_starts_empty() -> None:
    a: DynamicArray[int] = DynamicArray()
    assert len(a) == 0
    assert a.is_empty()
    assert not a
    assert a.to_list() == []


def test_append_and_index() -> None:
    a = DynamicArray([10, 20, 30])
    assert len(a) == 3
    assert a[0] == 10
    assert a[2] == 30
    assert a[-1] == 30
    assert a[-3] == 10


def test_capacity_doubles_when_full() -> None:
    a: DynamicArray[int] = DynamicArray(capacity=4)
    capacities = []
    for i in range(17):
        a.append(i)
        capacities.append(a.capacity)
    assert capacities[3] == 4
    assert capacities[4] == 8
    assert capacities[8] == 16
    assert capacities[16] == 32
    assert a.to_list() == list(range(17))


def test_out_of_range_raises() -> None:
    a = DynamicArray([1, 2])
    with pytest.raises(IndexError):
        _ = a[2]
    with pytest.raises(IndexError):
        _ = a[-3]
    with pytest.raises(IndexError):
        a[5] = 0


def test_setitem() -> None:
    a = DynamicArray([1, 2, 3])
    a[1] = 99
    a[-1] = 7
    assert a.to_list() == [1, 99, 7]


def test_insert_shifts_right() -> None:
    a = DynamicArray([1, 2, 4])
    a.insert(2, 3)
    a.insert(0, 0)
    a.insert(len(a), 5)
    assert a.to_list() == [0, 1, 2, 3, 4, 5]
    with pytest.raises(IndexError):
        a.insert(10, 6)


def test_pop_last_and_middle() -> None:
    a = DynamicArray([1, 2, 3, 4])
    assert a.pop() == 4
    assert a.pop(0) == 1
    assert a.to_list() == [2, 3]
    with pytest.raises(IndexError):
        DynamicArray[int]().pop()


def test_shrinks_when_quarter_full() -> None:
    a = DynamicArray(range(64))
    assert a.capacity == 64
    while len(a) > 4:
        a.pop()
    assert a.capacity < 64
    assert a.to_list() == [0, 1, 2, 3]


def test_remove_contains_index_of() -> None:
    a = DynamicArray(["a", "b", "c", "b"])
    assert "b" in a
    assert a.index_of("b") == 1
    assert a.remove("b")
    assert a.to_list() == ["a", "c", "b"]
    assert not a.remove("z")
    assert a.index_of("z") == -1


def test_swap_copy_filter_clear() -> None:
    a = DynamicArray([1, 2, 3, 4])
    a.swap(0, -1)
    assert a.to_list() == [4, 2, 3, 1]
    b = a.copy()
    b[0] = 0
    assert a[0] == 4
    assert a.filter(lambda x: x % 2 == 0).to_list() == [4, 2]
    a.clear()
    assert len(a) == 0


def test_filled_and_equality() -> None:
    a = DynamicArray.filled(3, None)
    assert a.to_list() == [None, None, None]
    assert DynamicArray([1, 2]) == DynamicArray([1, 2])
    assert DynamicArray([1, 2]) != DynamicArray([2, 1])
    assert repr(DynamicArray([1, 2])) == "DynamicArray([1, 2])"


def test_get_and_set_methods() -> None:
    a = DynamicArray([1, 2, 3])
    a.set(0, 9)
    assert a.get(0) == 9
    assert a.get(-1) == 3
    with pytest.raises(IndexError):
        a.get(3)
