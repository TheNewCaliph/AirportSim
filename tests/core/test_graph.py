"""Tests for aom.core.graph.Graph, with BFS/DFS checked against reference oracles."""

from __future__ import annotations

import ast
import itertools
import random
from collections import deque
from pathlib import Path

import pytest

from aom.core.graph import BFSResult, Graph


def make(n: int, edges: list[tuple[int, int]], directed: bool) -> Graph[int, None]:
    return Graph.from_edges(n, edges, directed=directed)


# ------------------------------------------------------------ reference oracles
# Independent implementations on built-in dict/deque (allowed in tests only).


def ref_adj(n: int, edges: list[tuple[int, int]], directed: bool) -> dict[int, list[int]]:
    adj: dict[int, list[int]] = {v: [] for v in range(n)}
    for u, v in edges:
        adj[u].append(v)
        if not directed and u != v:
            adj[v].append(u)
    return adj


def ref_bfs(adj: dict[int, list[int]], s: int) -> tuple[list[int], dict[int, int], dict[int, int]]:
    dist = {s: 0}
    parent: dict[int, int] = {}
    order = []
    dq = deque([s])
    while dq:
        v = dq.popleft()
        order.append(v)
        for w in adj[v]:
            if w not in dist:
                dist[w] = dist[v] + 1
                parent[w] = v
                dq.append(w)
    return order, dist, parent


def ref_dfs(adj: dict[int, list[int]], s: int) -> tuple[list[int], list[int], dict[int, int]]:
    seen = {s}
    pre: list[int] = []
    post: list[int] = []
    parent: dict[int, int] = {}

    def visit(v: int) -> None:
        pre.append(v)
        for w in adj[v]:
            if w not in seen:
                seen.add(w)
                parent[w] = v
                visit(w)
        post.append(v)

    visit(s)
    return pre, post, parent


# --------------------------------------------------------------------- structure


def test_empty_graph() -> None:
    g: Graph[str, None] = Graph()
    assert g.num_vertices == 0 and g.num_edges == 0 and not g.directed
    with pytest.raises(IndexError):
        g.bfs(0)
    with pytest.raises(IndexError):
        g.dfs(0)


def test_labels_and_ids() -> None:
    g: Graph[str, float] = Graph()
    ids = [g.add_vertex(c) for c in ("KHI", "DOH", "LHR")]
    assert ids == [0, 1, 2]
    assert [g.label(i) for i in ids] == ["KHI", "DOH", "LHR"]
    g.add_edge(0, 1, 3.5)
    assert [(e.target, e.data) for e in g.out_edges(0)] == [(1, 3.5)]


def test_directed_vs_undirected_edges() -> None:
    d = make(3, [(0, 1), (1, 2)], directed=True)
    u = make(3, [(0, 1), (1, 2)], directed=False)
    assert d.num_edges == u.num_edges == 2
    assert d.has_edge(0, 1) and not d.has_edge(1, 0)
    assert u.has_edge(0, 1) and u.has_edge(1, 0)
    assert list(d.neighbors(1)) == [2]
    assert list(u.neighbors(1)) == [0, 2]
    assert u.out_degree(1) == 2


def test_parallel_edges_and_self_loops() -> None:
    g: Graph[int, str] = Graph()
    for i in range(2):
        g.add_vertex(i)
    g.add_edge(0, 1, "PK1")
    g.add_edge(0, 1, "PK2")
    g.add_edge(0, 0, "loop")
    assert g.num_edges == 3
    assert [e.data for e in g.out_edges(0)] == ["PK1", "PK2", "loop"]
    assert [e.data for e in g.out_edges(1)] == ["PK1", "PK2"]  # loop stored once


def test_invalid_vertices_rejected() -> None:
    g = make(3, [], directed=False)
    for bad in (-1, 3, 99):
        with pytest.raises(IndexError):
            g.add_edge(0, bad)
        with pytest.raises(IndexError):
            g.add_edge(bad, 0)
        with pytest.raises(IndexError):
            g.out_degree(bad)
        with pytest.raises(IndexError):
            g.bfs(bad)
        with pytest.raises(IndexError):
            g.dfs(bad)
        with pytest.raises(IndexError):
            g.label(bad)
    assert g.num_edges == 0


# ---------------------------------------------------------------------- BFS/DFS


def test_toy_route_network_bfs_prefers_fewest_legs() -> None:
    """The Part 3 example: BFS returns the direct KHI -> LHR flight."""
    g: Graph[str, None] = Graph(directed=True)
    khi, doh, lhr, dxb = (g.add_vertex(c) for c in ("KHI", "DOH", "LHR", "DXB"))
    g.add_edge(khi, doh)
    g.add_edge(doh, lhr)
    g.add_edge(khi, dxb)
    g.add_edge(dxb, lhr)
    g.add_edge(khi, lhr)
    res = g.bfs(khi)
    assert res.dist[lhr] == 1
    assert res.path_to(lhr) == [khi, lhr]
    assert [g.label(v) for v in res.order] == ["KHI", "DOH", "DXB", "LHR"]


def test_small_known_traversals() -> None:
    #   0 - 1 - 3
    #   |   |
    #   2 - 4      5 (isolated)
    g = make(6, [(0, 1), (0, 2), (1, 3), (1, 4), (2, 4)], directed=False)
    b = g.bfs(0)
    assert b.order == [0, 1, 2, 3, 4]
    assert b.dist == [0, 1, 1, 2, 2, -1]
    assert b.parent == [-1, 0, 0, 1, 1, -1]
    assert b.path_to(5) is None
    assert b.path_to(0) == [0]
    d = g.dfs(0)
    assert d.preorder == [0, 1, 3, 4, 2]
    assert d.postorder == [3, 2, 4, 1, 0]
    assert d.parent == [-1, 0, 4, 1, 1, -1]


def test_directed_reachability_is_one_way() -> None:
    g = make(3, [(0, 1), (2, 1)], directed=True)
    assert g.bfs(0).order == [0, 1]
    assert g.bfs(1).order == [1]
    assert g.dfs(2).preorder == [2, 1]


def assert_valid_paths(g: Graph[int, None], res: BFSResult) -> None:
    for t in range(g.num_vertices):
        path = res.path_to(t)
        if res.dist[t] == -1:
            assert path is None
            continue
        assert path is not None
        assert path[0] == res.start and path[-1] == t
        assert len(path) - 1 == res.dist[t]
        for a, b in itertools.pairwise(path):
            assert g.has_edge(a, b)


@pytest.mark.parametrize("seed", range(40))
def test_matches_reference_on_random_graphs(seed: int) -> None:
    rng = random.Random(seed)
    n = rng.randrange(1, 40)
    m = rng.randrange(0, 3 * n)
    directed = rng.random() < 0.5
    # Duplicates and self-loops are included on purpose.
    edges = [(rng.randrange(n), rng.randrange(n)) for _ in range(m)]
    g = make(n, edges, directed)
    adj = ref_adj(n, edges, directed)
    assert g.num_edges == m
    for s in range(n):
        order, dist, parent = ref_bfs(adj, s)
        b = g.bfs(s)
        assert b.order == order
        assert b.dist == [dist.get(v, -1) for v in range(n)]
        assert b.parent == [parent.get(v, -1) for v in range(n)]
        assert_valid_paths(g, b)
        pre, post, dparent = ref_dfs(adj, s)
        d = g.dfs(s)
        assert d.preorder == pre
        assert d.postorder == post
        assert d.parent == [dparent.get(v, -1) for v in range(n)]


def test_dfs_is_not_limited_by_recursion_depth() -> None:
    n = 50_000  # far beyond Python's default recursion limit
    g = make(n, [(i, i + 1) for i in range(n - 1)], directed=True)
    d = g.dfs(0)
    assert d.preorder == list(range(n))
    assert d.postorder == list(range(n - 1, -1, -1))
    assert g.bfs(0).dist[n - 1] == n - 1


# ------------------------------------------------------------ project rules


def test_source_avoids_banned_builtins() -> None:
    """aom/core may not use heapq, dict, set or collections containers."""
    src = Path(__file__).resolve().parents[2] / "aom" / "core" / "graph.py"
    tree = ast.parse(src.read_text())
    banned_calls = {"dict", "set", "frozenset", "defaultdict", "deque", "Counter"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in {"heapq", "collections", "queue"}, alias.name
        elif isinstance(node, ast.ImportFrom):
            assert node.module in {"__future__", "collections.abc", "typing"}, node.module
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls, node.func.id
        assert not isinstance(node, ast.Dict | ast.Set | ast.DictComp | ast.SetComp)
