# Airport Operations Manager (AOM)

Joint project for Data Structures and Algorithms and Artificial Intelligence.
AOM simulates one operating day at a mid-sized airport and makes its decisions
automatically: gate assignment (CSP), passenger rebooking (search), delay
prediction (Bayesian network and machine learning), terminal queues (local
search) and runway slot bargaining (minimax with alpha-beta pruning).

**Team:** Abdullah (coordinator), Rayyan, Rabeet

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # add ,ui and ,ml when you need those parts
```

## Checks (CI runs exactly these on every push and pull request)

```bash
ruff check .
ruff format --check .
mypy
pytest --cov=aom/core
```

## Layout

| Folder | Contents |
| --- | --- |
| `aom/core/` | Hand-built data structures. No `dict`, `set`, `heapq`, `bisect`, `collections` or `sorted()` here; a test enforces it |
| `aom/model/` | Entities, airport state, seeded day generator |
| `aom/engine/` | Event types, bus and simulation loop (M5) |
| `aom/modules/` | One package per decision module (M1-M4, M6, M7) |
| `aom/ml/` | M8 data pipeline and models |
| `aom/ui/` | PySide6 dashboard |
| `experiments/` | Benchmark scripts for the report |
| `tests/` | Unit, property-based and integration tests |

## Contributing

One branch per issue (`feat/core-avl`, `fix/m3-seat-count`), small commits in
Conventional Commits style (`feat(core): add AVL range query`), and a pull
request reviewed by one teammate. See the Roadmap and Development Plan for the
full rules.
