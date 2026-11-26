"""Unit tests for the sorting algorithms."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from aom.core.dynamic_array import DynamicArray
from aom.core.sorting import (
    bubble_sort,
    insertion_sort,
    is_sorted,
    selection_sort,
)

ALL_SORTS = [insertion_sort, selection_sort, bubble_sort]
STABLE_SORTS = [insertion_sort, bubble_sort]

CASES = [
    [],
    [1],
    [2, 1],
    [5, 3, 8, 1, 9, 2, 7],
    list(range(40)),
    list(range(40, 0, -1)),
    [3] * 30,
    [1, 3, 2, 3, 1, 2] * 7,
]

SortFn = Callable[..., None]


@pytest.mark.parametrize("sort", ALL_SORTS)
@pytest.mark.parametrize("data", CASES)
def test_sorts_plain_lists(sort: SortFn, data: list[int]) -> None:
    items = list(data)
    sort(items)
    assert items == sorted(data)


@pytest.mark.parametrize("sort", ALL_SORTS)
def test_sorts_dynamic_array(sort: SortFn) -> None:
    a = DynamicArray([9, 4, 7, 1, 8, 2, 6, 3, 5, 0, 11, 10, 13, 12])
    sort(a)
    assert a.to_list() == list(range(14))
    assert is_sorted(a)


@pytest.mark.parametrize("sort", ALL_SORTS)
def test_key_function(sort: SortFn) -> None:
    flights = [("PK301", 900), ("EK601", 840), ("QR605", 940), ("PA210", 600)]
    sort(flights, key=lambda f: f[1])
    assert [f[0] for f in flights] == ["PA210", "EK601", "PK301", "QR605"]


@pytest.mark.parametrize("sort", STABLE_SORTS)
def test_stable_sorts_keep_tie_order(sort: SortFn) -> None:
    # (gate, departure): already in departure order; sort by gate only.
    flights: list[tuple[str, int]] = [
        ("B1", 600),
        ("A1", 610),
        ("B1", 620),
        ("A1", 630),
        ("A2", 640),
        ("A1", 650),
    ]
    sort(flights, key=lambda f: f[0])
    assert flights == [
        ("A1", 610),
        ("A1", 630),
        ("A1", 650),
        ("A2", 640),
        ("B1", 600),
        ("B1", 620),
    ]


def test_insertion_sort_subrange() -> None:
    items = [9, 8, 3, 1, 2, 0]
    insertion_sort(items, lo=2, hi=5)
    assert items == [9, 8, 1, 2, 3, 0]
