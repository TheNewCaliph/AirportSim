"""Unit tests for linear and binary search."""

from aom.core.dynamic_array import DynamicArray
from aom.core.searching import binary_search, linear_search, lower_bound, upper_bound


def test_linear_search_any_order() -> None:
    items = DynamicArray([7, 3, 9, 3])
    assert linear_search(items, 3) == 1
    assert linear_search(items, 9) == 2
    assert linear_search(items, 4) == -1
    assert linear_search(DynamicArray[int](), 1) == -1


def test_linear_search_with_key() -> None:
    flights = DynamicArray([("PK301", 900), ("EK601", 840)])
    assert linear_search(flights, "EK601", key=lambda f: f[0]) == 1


def test_binary_search_finds_first_of_duplicates() -> None:
    items = DynamicArray([1, 3, 3, 3, 5, 8])
    assert binary_search(items, 3) == 1
    assert binary_search(items, 8) == 5
    assert binary_search(items, 1) == 0
    assert binary_search(items, 4) == -1
    assert binary_search(items, 0) == -1
    assert binary_search(items, 9) == -1
    assert binary_search(DynamicArray[int](), 1) == -1


def test_bounds_are_insertion_points() -> None:
    items = [10, 20, 20, 30]
    assert lower_bound(items, 20) == 1
    assert upper_bound(items, 20) == 3
    assert lower_bound(items, 5) == 0
    assert lower_bound(items, 35) == 4
    assert upper_bound(items, 30) == 4


def test_first_departure_at_or_after() -> None:
    departures = DynamicArray([("PA210", 600), ("EK601", 840), ("PK301", 900)])
    i = lower_bound(departures, 850, key=lambda f: f[1])
    assert departures[i][0] == "PK301"
