"""Tests for arrival-departure Turns and buffered interval overlap."""

from datetime import datetime, timedelta

import pytest

from aom.model.turn import Turn


def test_turn_creation_stores_arrival_and_departure() -> None:
    arrival = datetime(2026, 11, 22, 9, 0)
    departure = datetime(2026, 11, 22, 10, 0)

    turn = Turn(arrival, departure)

    assert turn.arrival == arrival
    assert turn.departure == departure


def test_buffered_interval_extends_ten_minutes_on_both_sides() -> None:
    arrival = datetime(2026, 11, 22, 9, 0)
    departure = datetime(2026, 11, 22, 10, 0)

    turn = Turn(arrival, departure)

    assert turn.buffered_start == arrival - timedelta(minutes=10)
    assert turn.buffered_end == departure + timedelta(minutes=10)


def test_buffered_interval_handles_midnight_boundary() -> None:
    turn = Turn(datetime(2026, 11, 22, 0, 5), datetime(2026, 11, 22, 1, 0))

    assert turn.buffered_start == datetime(2026, 11, 21, 23, 55)
    assert turn.buffered_end == datetime(2026, 11, 22, 1, 10)


def test_overlapping_turns_overlap() -> None:
    first = Turn(datetime(2026, 11, 22, 9, 0), datetime(2026, 11, 22, 10, 0))
    second = Turn(datetime(2026, 11, 22, 9, 30), datetime(2026, 11, 22, 10, 30))

    assert first.overlaps(second)
    assert second.overlaps(first)


def test_separated_turns_do_not_overlap() -> None:
    first = Turn(datetime(2026, 11, 22, 9, 0), datetime(2026, 11, 22, 10, 0))
    second = Turn(datetime(2026, 11, 22, 10, 21), datetime(2026, 11, 22, 11, 0))

    assert not first.overlaps(second)
    assert not second.overlaps(first)


def test_exactly_touching_buffered_intervals_do_not_overlap() -> None:
    first = Turn(datetime(2026, 11, 22, 9, 0), datetime(2026, 11, 22, 10, 0))
    second = Turn(datetime(2026, 11, 22, 10, 20), datetime(2026, 11, 22, 11, 0))

    assert first.buffered_end == second.buffered_start
    assert not first.overlaps(second)
    assert not second.overlaps(first)


def test_ten_minute_buffer_causes_overlap() -> None:
    first = Turn(datetime(2026, 11, 22, 9, 0), datetime(2026, 11, 22, 10, 0))
    second = Turn(datetime(2026, 11, 22, 10, 5), datetime(2026, 11, 22, 11, 0))

    assert first.departure < second.arrival
    assert first.overlaps(second)


@pytest.mark.parametrize(
    ("arrival", "departure"),
    [
        (datetime(2026, 11, 22, 9, 0), datetime(2026, 11, 22, 9, 0)),
        (datetime(2026, 11, 22, 10, 0), datetime(2026, 11, 22, 9, 0)),
    ],
)
def test_departure_must_be_later_than_arrival(arrival: datetime, departure: datetime) -> None:
    with pytest.raises(ValueError, match="departure must be later than arrival"):
        Turn(arrival, departure)


def test_one_microsecond_overlap_is_detected() -> None:
    first = Turn(datetime(2026, 11, 22, 9, 0), datetime(2026, 11, 22, 10, 0))
    second = Turn(
        datetime(2026, 11, 22, 10, 20) - timedelta(microseconds=1),
        datetime(2026, 11, 22, 11, 0),
    )

    assert first.overlaps(second)
