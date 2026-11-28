"""Build gate constraints between turns whose buffered intervals overlap."""

from collections.abc import Iterable

from aom.core.graph import Graph
from aom.core.heap import MinHeap
from aom.core.sorting import merge_sort
from aom.modules.gates.turn import Turn


def build_constraint_graph(turns: Iterable[Turn]) -> Graph[Turn, None]:
    """Build an undirected graph of turn pairs that cannot share a gate.

    Vertex ids follow input order. Runs in O(n log n + E) time and O(n + E)
    space, where E is the number of overlapping turn pairs.
    """
    graph: Graph[Turn, None] = Graph(directed=False)
    intervals: list[tuple[int, int, int]] = []
    for vertex_id, turn in enumerate(turns):
        graph.add_vertex(turn)
        intervals.append((turn.buffered_start, turn.buffered_end, vertex_id))

    merge_sort(intervals)

    active_ids: list[int] = []
    active_positions = [-1] * len(intervals)
    expirations: MinHeap[int, int] = MinHeap()

    for start, end, vertex_id in intervals:
        while expirations and expirations.peek().priority <= start:
            expired_id = expirations.pop().item
            active_index = active_positions[expired_id]
            last_active_id = active_ids.pop()
            if active_index < len(active_ids):
                active_ids[active_index] = last_active_id
                active_positions[last_active_id] = active_index
            active_positions[expired_id] = -1

        for active_id in active_ids:
            graph.add_edge(active_id, vertex_id)

        active_positions[vertex_id] = len(active_ids)
        active_ids.append(vertex_id)
        expirations.push(end, vertex_id)

    return graph
