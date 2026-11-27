"""Unit tests for AVLTree.range and count_range."""

from aom.core.avl import AVLTree


def _tree(keys: list[int]) -> AVLTree[int, str]:
    t: AVLTree[int, str] = AVLTree()
    for k in keys:
        t.insert(k, f"v{k}")
    return t


def test_closed_range_inclusive() -> None:
    t = _tree(list(range(0, 100, 5)))
    assert [k for k, _ in t.range(12, 31)] == [15, 20, 25, 30]
    assert [k for k, _ in t.range(15, 30)] == [15, 20, 25, 30]
    assert t.count_range(15, 30) == 4


def test_open_ended_ranges() -> None:
    t = _tree(list(range(10)))
    assert [k for k, _ in t.range(lo=7)] == [7, 8, 9]
    assert [k for k, _ in t.range(hi=2)] == [0, 1, 2]
    assert [k for k, _ in t.range()] == list(range(10))


def test_empty_results() -> None:
    t = _tree([10, 20, 30])
    assert list(t.range(11, 19)) == []
    assert list(t.range(31, 99)) == []
    assert list(t.range(5, 1)) == []
    assert list(AVLTree[int, str]().range(0, 10)) == []


def test_departures_after_three_pm() -> None:
    """Team Guide example: every flight leaving at or after 15:00."""
    t: AVLTree[tuple[int, str], str] = AVLTree()
    for minute, fid in [(870, "PK300"), (900, "PK301"), (915, "EK601"), (1200, "QR605")]:
        t.insert((minute, fid), fid)
    after = [fid for _, fid in t.range(lo=(900, ""))]
    assert after == ["PK301", "EK601", "QR605"]
