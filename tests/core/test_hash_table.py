"""Tests for the separately chained HashTable."""

from collections.abc import Hashable
from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aom.core.hash_table import HashTable


@dataclass(frozen=True)
class _CollisionKey:
    value: int

    def __hash__(self) -> int:
        return 7


@dataclass(frozen=True)
class _NegativeHashKey:
    value: int

    def __hash__(self) -> int:
        return -7


def test_empty_hash_table_has_zero_length() -> None:
    table: HashTable[str, int] = HashTable()

    assert len(table) == 0


def test_put_and_get_values() -> None:
    table: HashTable[str, int] = HashTable()

    table.put("flight", 42)

    assert table.get("flight") == 42
    assert len(table) == 1


def test_put_updates_existing_key_without_resizing() -> None:
    table: HashTable[str, int] = HashTable()
    table.put("first", 1)
    table.put("second", 2)

    table.put("first", 3)

    assert table.get("first") == 3
    assert len(table) == 2
    assert table._buckets.capacity == 4


def test_remove_returns_value_and_updates_length() -> None:
    table: HashTable[str, int] = HashTable()
    table.put("flight", 42)

    assert table.remove("flight") == 42
    assert len(table) == 0


@pytest.mark.parametrize("operation", ["get", "remove"])
def test_missing_key_raises_key_error(operation: str) -> None:
    table: HashTable[str, int] = HashTable()

    with pytest.raises(KeyError):
        if operation == "get":
            table.get("missing")
        else:
            table.remove("missing")


def test_collisions_are_stored_and_removed_from_their_chain() -> None:
    table: HashTable[_CollisionKey, str] = HashTable()
    first = _CollisionKey(1)
    middle = _CollisionKey(2)
    last = _CollisionKey(3)

    table.put(first, "one")
    table.put(middle, "two")
    table.put(last, "three")

    assert table.get(first) == "one"
    assert table.get(middle) == "two"
    assert table.get(last) == "three"
    assert table.remove(middle) == "two"
    assert table.get(first) == "one"
    assert table.get(last) == "three"
    assert len(table) == 2


def test_resize_occurs_when_insertion_would_reach_load_factor() -> None:
    table: HashTable[int, str] = HashTable()
    table.put(1, "one")
    table.put(2, "two")

    table.put(3, "three")

    assert table._buckets.capacity == 8
    assert len(table) == 3
    assert table.get(1) == "one"
    assert table.get(2) == "two"
    assert table.get(3) == "three"


def test_multiple_resizes_keep_all_entries() -> None:
    table: HashTable[int, int] = HashTable()

    for value in range(100):
        table.put(value, value * 10)

    assert table._buckets.capacity > 8
    assert len(table) == 100
    for value in range(100):
        assert table.get(value) == value * 10


def test_negative_hash_value_selects_valid_bucket() -> None:
    table: HashTable[_NegativeHashKey, str] = HashTable()
    key = _NegativeHashKey(1)

    table.put(key, "negative")

    assert table.get(key) == "negative"


def test_none_is_a_valid_value() -> None:
    table: HashTable[str, int | None] = HashTable()
    table.put("empty", None)

    assert table.get("empty") is None
    assert table.remove("empty") is None


def test_different_hashable_key_types() -> None:
    table: HashTable[Hashable, str] = HashTable()
    keys: tuple[Hashable, ...] = (5, "five", ("five", 5))

    for key in keys:
        table.put(key, "value")

    for key in keys:
        assert table.get(key) == "value"
    assert len(table) == 3


def test_length_tracks_insert_update_and_remove() -> None:
    table: HashTable[int, str] = HashTable()

    table.put(1, "one")
    table.put(2, "two")
    table.put(1, "updated")
    assert len(table) == 2

    table.remove(1)
    assert len(table) == 1


@given(
    st.lists(
        st.tuples(
            st.sampled_from(("put", "get", "remove")),
            st.integers(),
            st.one_of(st.none(), st.integers()),
        ),
        max_size=100,
    )
)
def test_operations_match_python_dict(
    operations: list[tuple[str, int, int | None]],
) -> None:
    table: HashTable[int, int | None] = HashTable()
    reference: dict[int, int | None] = {}

    for operation, key, value in operations:
        if operation == "put":
            table.put(key, value)
            reference[key] = value
        elif operation == "get":
            if key in reference:
                assert table.get(key) == reference[key]
            else:
                with pytest.raises(KeyError):
                    table.get(key)
        elif key in reference:
            assert table.remove(key) == reference.pop(key)
        else:
            with pytest.raises(KeyError):
                table.remove(key)

        assert len(table) == len(reference)
        for stored_key, stored_value in reference.items():
            assert table.get(stored_key) == stored_value
