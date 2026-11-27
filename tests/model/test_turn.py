"""Tests for arrival-departure Turns and buffered interval overlap."""

import pytest

from aom.modules.gates.turn import Turn


def test_turn_creation_stores_arrival_and_departure() -> None:
    turn = Turn(540, 600)

    assert turn.arrival == 540
    assert turn.departure == 600


def test_buffered_interval_extends_ten_minutes_on_both_sides() -> None:
    turn = Turn(540, 600)

    assert turn.buffered_start == 530
    assert turn.buffered_end == 610


def test_buffered_interval_handles_midnight_boundary() -> None:
    turn = Turn(5, 60)

    assert turn.buffered_start == -5
    assert turn.buffered_end == 70


def test_overlapping_turns_overlap() -> None:
    first = Turn(540, 600)
    second = Turn(570, 630)

    assert first.overlaps(second)
    assert second.overlaps(first)


def test_separated_turns_do_not_overlap() -> None:
    first = Turn(540, 600)
    second = Turn(621, 660)

    assert not first.overlaps(second)
    assert not second.overlaps(first)


def test_exactly_touching_buffered_intervals_do_not_overlap() -> None:
    first = Turn(540, 600)
    second = Turn(620, 660)

    assert first.buffered_end == second.buffered_start
    assert not first.overlaps(second)
    assert not second.overlaps(first)


def test_ten_minute_buffer_causes_overlap() -> None:
    first = Turn(540, 600)
    second = Turn(605, 660)

    assert first.departure < second.arrival
    assert first.overlaps(second)


@pytest.mark.parametrize(
    ("arrival", "departure"),
    [
        (540, 540),
        (600, 540),
    ],
)
def test_departure_must_be_later_than_arrival(arrival: int, departure: int) -> None:
    with pytest.raises(ValueError, match="departure must be later than arrival"):
        Turn(arrival, departure)


def test_one_minute_overlap_is_detected() -> None:
    first = Turn(540, 600)
    second = Turn(619, 660)

    assert first.overlaps(second)
