"""Tests for the manually resized DynamicArray."""

import pytest

from aom.core.dynamic_array import DynamicArray


def test_empty_array_has_default_capacity() -> None:
    array: DynamicArray[int] = DynamicArray()

    assert len(array) == 0
    assert array.capacity == 4


def test_array_accepts_custom_initial_capacity() -> None:
    array: DynamicArray[int] = DynamicArray(initial_capacity=2)

    assert array.capacity == 2


def test_appending_and_retrieving_elements() -> None:
    array: DynamicArray[str] = DynamicArray(initial_capacity=2)
    array.append("first")
    array.append("second")

    assert len(array) == 2
    assert array.get(0) == "first"
    assert array.get(1) == "second"


def test_set_updates_an_existing_element() -> None:
    array: DynamicArray[str] = DynamicArray()
    array.append("before")

    array.set(0, "after")

    assert array.get(0) == "after"


def test_pop_removes_last_item_and_clears_its_storage_slot() -> None:
    array: DynamicArray[str] = DynamicArray()
    array.append("first")
    array.append("last")

    assert array.pop() == "last"
    assert len(array) == 1
    assert array.get(0) == "first"
    assert array._items[1] is None


def test_capacity_doubles_multiple_times() -> None:
    array: DynamicArray[int] = DynamicArray(initial_capacity=1)

    for value in range(9):
        array.append(value)

    assert array.capacity == 16
    assert [array.get(index) for index in range(len(array))] == list(range(9))


@pytest.mark.parametrize("index", [2, 100])
def test_get_rejects_invalid_positive_indexes(index: int) -> None:
    array: DynamicArray[int] = DynamicArray()
    array.append(10)

    with pytest.raises(IndexError):
        array.get(index)


def test_set_rejects_invalid_positive_index() -> None:
    array: DynamicArray[int] = DynamicArray()

    with pytest.raises(IndexError):
        array.set(0, 10)


@pytest.mark.parametrize("index", [-1, -2])
def test_get_rejects_negative_indexes(index: int) -> None:
    array: DynamicArray[int] = DynamicArray()
    array.append(10)

    with pytest.raises(IndexError):
        array.get(index)


def test_set_rejects_negative_index() -> None:
    array: DynamicArray[int] = DynamicArray()
    array.append(10)

    with pytest.raises(IndexError):
        array.set(-1, 20)


def test_pop_rejects_empty_array() -> None:
    array: DynamicArray[int] = DynamicArray()

    with pytest.raises(IndexError):
        array.pop()


@pytest.mark.parametrize("capacity", [0, -1, -10])
def test_initial_capacity_must_be_positive(capacity: int) -> None:
    with pytest.raises(ValueError):
        DynamicArray[int](initial_capacity=capacity)


def test_initial_capacity_must_be_an_integer() -> None:
    with pytest.raises(ValueError):
        DynamicArray[int](initial_capacity=1.5)  # type: ignore[arg-type]


def test_none_is_a_valid_item() -> None:
    array: DynamicArray[str | None] = DynamicArray()
    array.append(None)

    assert len(array) == 1
    assert array.get(0) is None
    assert array.pop() is None


def test_large_number_of_elements_survive_resizing_and_removal() -> None:
    array: DynamicArray[int] = DynamicArray(initial_capacity=2)

    for value in range(1_000):
        array.append(value)

    assert len(array) == 1_000
    assert array.capacity == 1_024
    for value in range(1_000):
        assert array.get(value) == value

    for value in reversed(range(1_000)):
        assert array.pop() == value
    assert len(array) == 0
    assert array.capacity == 1_024
