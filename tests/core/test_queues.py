"""Unit tests for Queue, CircularQueue and Deque."""

import pytest

from aom.core.queues import CircularQueue, Deque, Queue


def test_queue_is_fifo() -> None:
    q: Queue[int] = Queue()
    for i in range(5):
        q.enqueue(i)
    assert q.peek() == 0
    assert [q.dequeue() for _ in range(5)] == [0, 1, 2, 3, 4]
    assert q.is_empty()
    with pytest.raises(IndexError):
        q.dequeue()
    with pytest.raises(IndexError):
        q.peek()


def test_circular_queue_wraps_around() -> None:
    q: CircularQueue[int] = CircularQueue(3)
    q.enqueue(1)
    q.enqueue(2)
    q.enqueue(3)
    assert q.is_full()
    with pytest.raises(OverflowError):
        q.enqueue(4)
    assert not q.try_enqueue(4)
    assert q.dequeue() == 1
    q.enqueue(4)  # goes into the slot freed at the start of the ring
    assert list(q) == [2, 3, 4]
    assert [q.dequeue() for _ in range(3)] == [2, 3, 4]
    with pytest.raises(IndexError):
        q.dequeue()


def test_circular_queue_rejects_bad_capacity() -> None:
    with pytest.raises(ValueError):
        CircularQueue[int](0)


def test_deque_both_ends() -> None:
    d: Deque[int] = Deque()
    d.push_back(2)
    d.push_front(1)
    d.push_back(3)
    d.push_front(0)
    assert list(d) == [0, 1, 2, 3]
    assert d.peek_front() == 0
    assert d.peek_back() == 3
    assert d[1] == 1
    assert d[-1] == 3
    assert d.pop_back() == 3
    assert d.pop_front() == 0
    assert list(d) == [1, 2]


def test_deque_grows_past_initial_capacity() -> None:
    d: Deque[int] = Deque()
    for i in range(50):
        if i % 2:
            d.push_front(i)
        else:
            d.push_back(i)
    expected_front = list(range(49, 0, -2))
    expected_back = list(range(0, 50, 2))
    assert list(d) == expected_front + expected_back
    assert len(d) == 50


def test_deque_empty_errors() -> None:
    d: Deque[int] = Deque()
    for method in (d.pop_front, d.pop_back, d.peek_front, d.peek_back):
        with pytest.raises(IndexError):
            method()
    with pytest.raises(IndexError):
        _ = d[0]
