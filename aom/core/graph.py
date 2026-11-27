"""Adjacency-list graph with BFS and DFS.

Used for the airport route network (M3), aircraft rotation chains (M4) and the
gate constraint graph (M2).

Design notes
------------
* Vertices are dense integer ids ``0 .. n-1`` handed out by ``add_vertex``.
  Each vertex may carry a label (an airport code, a turn id, ...). Mapping a
  label to its id is the caller's job; once the core hash table lands, callers
  can keep that mapping there. Keeping ids integral means this module needs no
  other core structure, and ``visited`` bookkeeping is a plain list.
* Directed or undirected, chosen at construction. Parallel edges are allowed
  (two flights between the same airports are two edges) and so are self-loops.
  Every edge may carry a payload (a flight, a weight, ...).
* Neighbours are visited in insertion order, so traversals are deterministic.
* No ``heapq``, ``dict``, ``set`` or ``collections`` containers are used
  (banned inside ``aom/core``). Adjacency lists are plain lists and the BFS
  queue is a list with a head index; both can be swapped for the core linked
  list and queue once those land, without changing the algorithms.
* DFS is iterative (an explicit stack of frames), so deep graphs cannot hit
  Python's recursion limit. Its order equals that of the textbook recursion.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Generic, TypeVar, overload

V = TypeVar("V")  # vertex label
E = TypeVar("E")  # edge payload

NONE = -1  # "no vertex" in parent arrays; "unreachable" in distance arrays


class Edge(Generic[E]):
    """One outgoing edge: the target vertex id and the edge's payload."""

    __slots__ = ("data", "target")

    def __init__(self, target: int, data: E) -> None:
        self.target = target
        self.data = data

    def __repr__(self) -> str:
        return f"Edge(target={self.target}, data={self.data!r})"


class BFSResult:
    """Outcome of a breadth-first search from ``start``.

    Attributes:
        order: reachable vertices in the order they were dequeued.
        dist: ``dist[v]`` is the fewest edges from ``start`` to ``v``,
            or ``-1`` if ``v`` is unreachable.
        parent: ``parent[v]`` is the vertex that first discovered ``v``,
            or ``-1`` for ``start`` and unreachable vertices.
    """

    __slots__ = ("dist", "order", "parent", "start")

    def __init__(self, start: int, order: list[int], dist: list[int], parent: list[int]) -> None:
        self.start = start
        self.order = order
        self.dist = dist
        self.parent = parent

    def path_to(self, target: int) -> list[int] | None:
        """Fewest-edges path ``start .. target`` as vertex ids, or ``None``.

        Time O(path length).
        """
        if target < 0 or target >= len(self.dist):
            raise IndexError(f"vertex {target} out of range")
        if self.dist[target] == NONE:
            return None
        path = [target]
        while path[-1] != self.start:
            path.append(self.parent[path[-1]])
        path.reverse()
        return path


class DFSResult:
    """Outcome of a depth-first search from ``start``.

    Attributes:
        preorder: reachable vertices in discovery order.
        postorder: reachable vertices in finishing order.
        parent: DFS-tree parent of each vertex, ``-1`` for ``start`` and
            unreachable vertices.
    """

    __slots__ = ("parent", "postorder", "preorder", "start")

    def __init__(
        self, start: int, preorder: list[int], postorder: list[int], parent: list[int]
    ) -> None:
        self.start = start
        self.preorder = preorder
        self.postorder = postorder
        self.parent = parent


class Graph(Generic[V, E]):
    """Adjacency-list graph over integer vertex ids."""

    def __init__(self, *, directed: bool = False) -> None:
        """Create an empty graph. O(1)."""
        self._directed = directed
        self._labels: list[V] = []
        self._adj: list[list[Edge[E]]] = []
        self._num_edges = 0

    @staticmethod
    def from_edges(
        n: int, edges: Iterable[tuple[int, int]], *, directed: bool = False
    ) -> Graph[int, None]:
        """Build an unlabelled graph on ``n`` vertices. O(n + m)."""
        g: Graph[int, None] = Graph(directed=directed)
        for i in range(n):
            g.add_vertex(i)
        for u, v in edges:
            g.add_edge(u, v)
        return g

    # ------------------------------------------------------------------ queries

    @property
    def directed(self) -> bool:
        """Whether edges are one-way. O(1)."""
        return self._directed

    @property
    def num_vertices(self) -> int:
        """Number of vertices. O(1)."""
        return len(self._adj)

    @property
    def num_edges(self) -> int:
        """Number of edges; an undirected edge counts once. O(1)."""
        return self._num_edges

    def label(self, v: int) -> V:
        """Label given to vertex ``v`` when it was added. O(1)."""
        self._check(v)
        return self._labels[v]

    def out_edges(self, v: int) -> Iterator[Edge[E]]:
        """Iterate ``v``'s outgoing edges in insertion order.

        O(1) to start, O(out-degree) to exhaust.
        """
        self._check(v)
        return iter(self._adj[v])

    def neighbors(self, v: int) -> Iterator[int]:
        """Iterate the targets of ``v``'s outgoing edges (repeats for parallel
        edges). O(1) to start, O(out-degree) to exhaust.
        """
        self._check(v)
        return (e.target for e in self._adj[v])

    def out_degree(self, v: int) -> int:
        """Number of outgoing edges of ``v``. O(1)."""
        self._check(v)
        return len(self._adj[v])

    def has_edge(self, u: int, v: int) -> bool:
        """True if an edge ``u -> v`` exists. O(out-degree of u)."""
        self._check(u)
        self._check(v)
        return any(e.target == v for e in self._adj[u])

    # ---------------------------------------------------------------- mutations

    @overload
    def add_vertex(self: Graph[None, E]) -> int: ...
    @overload
    def add_vertex(self, label: V) -> int: ...
    def add_vertex(self, label: Any = None) -> int:
        """Add a vertex and return its id (ids are 0, 1, 2, ...). O(1) amortised."""
        self._labels.append(label)
        self._adj.append([])
        return len(self._adj) - 1

    @overload
    def add_edge(self: Graph[V, None], u: int, v: int) -> None: ...
    @overload
    def add_edge(self, u: int, v: int, data: E) -> None: ...
    def add_edge(self, u: int, v: int, data: Any = None) -> None:
        """Add an edge ``u -> v`` (and ``v -> u`` if undirected). O(1) amortised.

        Parallel edges and self-loops are allowed. In an undirected graph both
        directions share the same payload, and a self-loop is stored once.

        Raises:
            IndexError: if ``u`` or ``v`` is not a vertex id.
        """
        self._check(u)
        self._check(v)
        self._adj[u].append(Edge(v, data))
        if not self._directed and u != v:
            self._adj[v].append(Edge(u, data))
        self._num_edges += 1

    # --------------------------------------------------------------- traversals

    def bfs(self, start: int) -> BFSResult:
        """Breadth-first search from ``start``.

        Finds the fewest-edges distance and a shortest path to every reachable
        vertex. Time O(V + E), extra space O(V).
        """
        self._check(start)
        n = len(self._adj)
        dist = [NONE] * n
        parent = [NONE] * n
        dist[start] = 0
        queue = [start]  # doubles as the visit order; ``head`` is the front
        head = 0
        while head < len(queue):
            v = queue[head]
            head += 1
            for e in self._adj[v]:
                w = e.target
                if dist[w] == NONE:
                    dist[w] = dist[v] + 1
                    parent[w] = v
                    queue.append(w)
        return BFSResult(start, queue, dist, parent)

    def dfs(self, start: int) -> DFSResult:
        """Depth-first search from ``start`` (iterative, explicit stack).

        Visits neighbours in insertion order, exactly like the recursive
        algorithm, without using Python's call stack. Time O(V + E), extra
        space O(V).
        """
        self._check(start)
        n = len(self._adj)
        seen = [False] * n
        parent = [NONE] * n
        pre: list[int] = []
        post: list[int] = []
        seen[start] = True
        pre.append(start)
        stack_v = [start]  # vertex of each active frame
        stack_i = [0]  # next edge index to try in that frame
        while stack_v:
            v = stack_v[-1]
            i = stack_i[-1]
            edges = self._adj[v]
            if i < len(edges):
                stack_i[-1] = i + 1
                w = edges[i].target
                if not seen[w]:
                    seen[w] = True
                    parent[w] = v
                    pre.append(w)
                    stack_v.append(w)
                    stack_i.append(0)
            else:
                post.append(v)
                stack_v.pop()
                stack_i.pop()
        return DFSResult(start, pre, post, parent)

    # ---------------------------------------------------------------- internals

    def _check(self, v: int) -> None:
        if v < 0 or v >= len(self._adj):
            raise IndexError(f"vertex {v} out of range (0..{len(self._adj) - 1})")
