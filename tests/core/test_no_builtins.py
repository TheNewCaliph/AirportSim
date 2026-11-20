"""Fail the build if aom/core uses Python's built-in containers or helpers.

The DSA course grades our own implementations, so inside aom/core we may not
import heapq, bisect, collections, etc., call dict()/set()/sorted(), or write
dict/set literals and comprehensions. Plain list literals are allowed only as
raw fixed-capacity arrays inside our dynamic array. Type annotations such as
`dict[str, int]` are not calls and are not flagged.
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "aom" / "core"

BANNED_MODULES = {"heapq", "bisect", "collections", "queue", "array", "sortedcontainers"}
BANNED_CALLS = {"dict", "set", "frozenset", "sorted", "reversed"}

# collections.abc holds only abstract types for annotations (Iterable, Iterator, ...),
# not containers, and ruff (UP035) requires it over typing.Iterable.
ALLOWED_MODULES = {"collections.abc"}


def _banned(module: str) -> bool:
    return module not in ALLOWED_MODULES and module.split(".")[0] in BANNED_MODULES


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        where = f"{path.name}:{getattr(node, 'lineno', '?')}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _banned(alias.name):
                    found.append(f"{where} imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and _banned(node.module):
                found.append(f"{where} imports from {node.module}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
                found.append(f"{where} calls {node.func.id}()")
        elif isinstance(node, (ast.Dict, ast.DictComp)):
            found.append(f"{where} uses a dict literal or comprehension")
        elif isinstance(node, (ast.Set, ast.SetComp)):
            found.append(f"{where} uses a set literal or comprehension")
    return found


def test_core_uses_only_our_own_structures() -> None:
    problems: list[str] = []
    for path in sorted(CORE.rglob("*.py")):  # sorted() is fine here: this is a test
        problems.extend(_violations(path))
    assert not problems, "Built-ins found in aom/core:\n" + "\n".join(problems)
