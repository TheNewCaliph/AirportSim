"""Tests for aom.core.heap.MinHeap, including property tests against oracles."""

from __future__ import annotations

import heapq
import random
from pathlib import Path

import pytest

from aom.core.heap import HeapEntry, MinHeap


def drain(h: MinHeap[int, str]) -> list[tuple[int, str]]:
    out = []
    while h:
        e = h.pop()
        out.append((e.priority, e.item))
    return out


# ------------------------------------------------------------------ basics


def test_empty_heap() -> None:
    h: MinHeap[int, str] = MinHeap()
    assert len(h) == 0 and not h and h.is_empty()
    with pytest.raises(IndexError):
        h.pop()
    with pytest.raises(IndexError):
        h.peek()


def test_push_pop_sorted() -> None:
    h: MinHeap[int, str] = MinHeap()
    for p in [5, 3, 8, 1, 9, 2]:
        h.push(p, f"x{p}")
        h.check_invariant()
    assert h.peek().priority == 1
    assert [p for p, _ in drain(h)] == [1, 2, 3, 5, 8, 9]


def test_equal_priorities_pop_fifo() -> None:
    h: MinHeap[int, str] = MinHeap()
    for name in "abcdef":
        h.push(1, name)
    assert [item for _, item in drain(h)] == list("abcdef")


def test_tuple_priorities_like_event_queue() -> None:
    h: MinHeap[tuple[int, int, int], str] = MinHeap()
    h.push((840, 1, 0), "arrival")
    h.push((840, 0, 1), "departure")  # departure frees the gate first
    h.push((839, 5, 2), "tick")
    assert [h.pop().item for _ in range(3)] == ["tick", "departure", "arrival"]


def test_heapify_constructor() -> None:
    rng = random.Random(1)
    data = [(rng.randrange(100), f"i{i}") for i in range(200)]
    h = MinHeap(data)
    h.check_invariant()
    assert [p for p, _ in drain(h)] == sorted(p for p, _ in data)


# ------------------------------------------------------------- decrease-key


def test_decrease_key_moves_entry_to_front() -> None:
    h: MinHeap[int, str] = MinHeap()
    handles = {n: h.push(p, n) for n, p in [("a", 10), ("b", 20), ("c", 30), ("d", 40)]}
    h.decrease_key(handles["d"], 5)
    h.check_invariant()
    assert h.peek().item == "d" and h.peek().priority == 5


def test_decrease_key_equal_is_noop() -> None:
    h: MinHeap[int, str] = MinHeap()
    e = h.push(3, "a")
    h.decrease_key(e, 3)
    h.check_invariant()
    assert h.peek() is e


def test_decrease_key_rejects_increase() -> None:
    h: MinHeap[int, str] = MinHeap()
    e = h.push(3, "a")
    with pytest.raises(ValueError):
        h.decrease_key(e, 4)
    assert e.priority == 3


def test_stale_and_foreign_handles_rejected() -> None:
    h1: MinHeap[int, str] = MinHeap()
    h2: MinHeap[int, str] = MinHeap()
    e = h1.push(1, "a")
    foreign = h2.push(1, "b")
    with pytest.raises(ValueError):
        h1.decrease_key(foreign, 0)
    with pytest.raises(ValueError):
        h1.remove(foreign)
    h1.pop()
    assert not e.in_heap and not h1.contains(e)
    with pytest.raises(ValueError):
        h1.decrease_key(e, 0)
    with pytest.raises(ValueError):
        h1.remove(e)


# ------------------------------------------------------------------- remove


def test_remove_middle_and_last() -> None:
    h: MinHeap[int, str] = MinHeap()
    hs = [h.push(p, str(p)) for p in range(10)]
    h.remove(hs[4])
    h.check_invariant()
    h.remove(hs[9])
    h.check_invariant()
    assert [p for p, _ in drain(h)] == [0, 1, 2, 3, 5, 6, 7, 8]


def test_clear_invalidates_handles() -> None:
    h: MinHeap[int, str] = MinHeap()
    e = h.push(1, "a")
    h.clear()
    assert len(h) == 0 and not e.in_heap
    with pytest.raises(ValueError):
        h.decrease_key(e, 0)


# --------------------------------------------------- property tests (oracles)


@pytest.mark.parametrize("seed", range(20))
def test_matches_heapq_on_random_push_pop(seed: int) -> None:
    """Oracle: heapq on (priority, seq, item) pops the same sequence."""
    rng = random.Random(seed)
    mine: MinHeap[int, int] = MinHeap()
    oracle: list[tuple[int, int, int]] = []
    seq = 0
    for _ in range(2000):
        if oracle and rng.random() < 0.4:
            p, _s, item = heapq.heappop(oracle)
            got = mine.pop()
            assert (got.priority, got.item) == (p, item)
        else:
            p = rng.randrange(50)  # many ties on purpose
            mine.push(p, seq)
            heapq.heappush(oracle, (p, seq, seq))
            seq += 1
        assert len(mine) == len(oracle)
        if oracle:
            assert mine.peek().priority == oracle[0][0]
    mine.check_invariant()


@pytest.mark.parametrize("seed", range(20))
def test_matches_model_with_decrease_key_and_remove(seed: int) -> None:
    """Oracle: a plain list of live entries; min by (priority, seq)."""
    rng = random.Random(1000 + seed)
    h: MinHeap[int, int] = MinHeap()
    live: list[tuple[HeapEntry[int, int], int]] = []  # (handle, seq)
    seq = 0
    for _ in range(1500):
        r = rng.random()
        if r < 0.40 or not live:
            e = h.push(rng.randrange(1000), seq)
            live.append((e, seq))
            seq += 1
        elif r < 0.60:
            i = rng.randrange(len(live))
            e, _ = live[i]
            h.decrease_key(e, e.priority - rng.randrange(0, 200))
        elif r < 0.70:
            i = rng.randrange(len(live))
            e, _ = live.pop(i)
            h.remove(e)
            assert not e.in_heap
        else:
            expected = min(live, key=lambda t: (t[0].priority, t[1]))
            got = h.pop()
            assert got is expected[0]
            live.remove(expected)
        assert len(h) == len(live)
        if seed < 3:
            h.check_invariant()
    h.check_invariant()
    while live:
        expected = min(live, key=lambda t: (t[0].priority, t[1]))
        assert h.pop() is expected[0]
        live.remove(expected)


def test_large_sort() -> None:
    rng = random.Random(7)
    data = [rng.randrange(10**6) for _ in range(20_000)]
    h: MinHeap[int, None] = MinHeap()
    for x in data:
        h.push(x, None)
    assert [h.pop().priority for _ in range(len(data))] == sorted(data)


# ------------------------------------------------------------ project rules


def test_source_avoids_banned_builtins() -> None:
    src = Path(__file__).resolve().parents[2] / "aom" / "core" / "heap.py"
    code = "\n".join(
        line
        for line in src.read_text().splitlines()
        if not line.lstrip().startswith(("#", '"', "*"))
    )
    for banned in ("import heapq", "from heapq", "dict(", "set(", "{}"):
        assert banned not in code, f"aom/core must not use {banned!r}"
