"""Tests for the gate constraint graph builder."""

from aom.core.graph import Graph
from aom.modules.gates.constraint_graph import build_constraint_graph
from aom.modules.gates.turn import Turn


def _turn_for_buffered_interval(start: int, end: int) -> Turn:
    return Turn(start + 10, end - 10)


def _edge_pairs(graph: Graph[Turn, None]) -> set[tuple[int, int]]:
    assert not graph.directed
    pairs: list[tuple[int, int]] = []
    for source in range(graph.num_vertices):
        neighbors = list(graph.neighbors(source))
        assert source not in neighbors
        assert len(neighbors) == len(set(neighbors))
        for target in neighbors:
            assert graph.has_edge(target, source)
            if source < target:
                pairs.append((source, target))
    assert len(pairs) == graph.num_edges
    return set(pairs)


def test_empty_input() -> None:
    graph = build_constraint_graph([])

    assert graph.num_vertices == 0
    assert graph.num_edges == 0
    assert _edge_pairs(graph) == set()


def test_one_turn() -> None:
    turn = Turn(540, 600)

    graph = build_constraint_graph([turn])

    assert graph.num_vertices == 1
    assert graph.label(0) is turn
    assert graph.num_edges == 0
    assert _edge_pairs(graph) == set()


def test_no_overlaps() -> None:
    turns = [
        _turn_for_buffered_interval(50, 90),
        _turn_for_buffered_interval(0, 40),
        _turn_for_buffered_interval(100, 140),
    ]

    graph = build_constraint_graph(turns)

    assert graph.num_edges == 0
    assert _edge_pairs(graph) == set()
    assert [graph.label(vertex_id) for vertex_id in range(graph.num_vertices)] == turns


def test_multiple_overlaps_create_each_edge_once() -> None:
    turns = [
        _turn_for_buffered_interval(0, 50),
        _turn_for_buffered_interval(30, 70),
        _turn_for_buffered_interval(60, 100),
    ]

    graph = build_constraint_graph(turns)

    assert graph.num_edges == 2
    assert _edge_pairs(graph) == {(0, 1), (1, 2)}


def test_nested_intervals_overlap_pairwise() -> None:
    turns = [
        _turn_for_buffered_interval(0, 100),
        _turn_for_buffered_interval(20, 80),
        _turn_for_buffered_interval(35, 60),
    ]

    graph = build_constraint_graph(turns)

    assert graph.num_edges == 3
    assert _edge_pairs(graph) == {(0, 1), (0, 2), (1, 2)}


def test_identical_intervals_have_distinct_vertices_and_all_edges() -> None:
    first = _turn_for_buffered_interval(0, 60)
    second = Turn(first.arrival, first.departure)
    third = Turn(first.arrival, first.departure)
    turns = [first, second, third]

    graph = build_constraint_graph(turns)

    assert first == second == third
    assert len({id(turn) for turn in turns}) == 3
    assert graph.num_vertices == 3
    assert [graph.label(vertex_id) for vertex_id in range(3)] == turns
    assert graph.num_edges == 3
    assert _edge_pairs(graph) == {(0, 1), (0, 2), (1, 2)}


def test_boundary_touching_intervals_do_not_overlap() -> None:
    first = _turn_for_buffered_interval(0, 50)
    second = _turn_for_buffered_interval(50, 90)
    assert first.buffered_end == second.buffered_start

    graph = build_constraint_graph([first, second])

    assert graph.num_edges == 0
    assert _edge_pairs(graph) == set()
