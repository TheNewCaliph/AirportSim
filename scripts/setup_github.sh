#!/usr/bin/env bash
# One-time GitHub setup for AOM: repo settings, labels, sprint milestones,
# project board and all Sprint 1 issues.
#
# Needs the GitHub CLI (https://cli.github.com), signed in with project access:
#   gh auth login
#   gh auth refresh -s project
#
# Run it from inside the cloned repository, AFTER the first push to main
# (branch protection needs main to exist):
#   bash scripts/setup_github.sh
#
# Fill in the three GitHub usernames first. Rayyan and Rabeet must have
# accepted their collaborator invitations, or assigning them fails.

set -euo pipefail

ABDULLAH="your-github-username"
RAYYAN="rayyans-github-username"
RABEET="rabeets-github-username"

OWNER="$(gh repo view --json owner --jq .owner.login)"
REPO="$(gh repo view --json name --jq .name)"
echo "Setting up ${OWNER}/${REPO}"

# ---------------------------------------------------------------------------
# 1. Repository settings: keep every commit (no squash), tidy branches
# ---------------------------------------------------------------------------
gh repo edit \
  --enable-merge-commit \
  --enable-rebase-merge \
  --enable-squash-merge=false \
  --delete-branch-on-merge

# ---------------------------------------------------------------------------
# 2. Protect main: pull requests only, one approval, CI green, no force-push.
#    Free accounts can protect PUBLIC repos; a private repo needs GitHub Pro
#    (free for students through the GitHub Student Developer Pack).
#    The check names match the CI job matrix: "check (3.11)", "check (3.12)".
# ---------------------------------------------------------------------------
gh api --method PUT "repos/${OWNER}/${REPO}/branches/main/protection" \
  --input - <<'JSON' || echo "WARNING: branch protection failed (private repo on a free plan?)"
{
  "required_status_checks": { "strict": true, "contexts": ["check (3.11)", "check (3.12)"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

# ---------------------------------------------------------------------------
# 3. Labels: one per scope, plus kinds
# ---------------------------------------------------------------------------
label() { gh label create "$1" --color "$2" --description "$3" --force >/dev/null; }
label core     "1d76db" "Core data-structure library"
label m1       "0e8a16" "Schedule and data"
label m2       "5319e7" "Gate assignment"
label m3       "b60205" "Rebooking"
label m4       "fbca04" "Delay prediction"
label m5       "006b75" "Simulation engine"
label m6       "c2e0c6" "Terminal flow"
label m7       "d93f0b" "Slot bargaining"
label ml       "0052cc" "M8 machine learning"
label ui       "bfd4f2" "Dashboard"
label infra    "cccccc" "Repo, CI and tooling"
label exp      "f9d0c4" "Experiments"
label report   "fef2c0" "Report and docs"
label bug      "ee0701" "Something is broken"

# ---------------------------------------------------------------------------
# 4. Milestones: one per sprint, due at the Sunday grand review
# ---------------------------------------------------------------------------
milestone() {
  gh api --method POST "repos/${OWNER}/${REPO}/milestones" \
    -f title="$1" -f due_on="$2" -f description="$3" >/dev/null \
    || echo "  (milestone '$1' may already exist)"
}
milestone "Sprint 1 - Foundations"  "2026-11-15T18:00:00Z" "GR1: core library tested, seeded day generated"
milestone "Sprint 2 - Algorithms"   "2026-11-22T18:00:00Z" "GR2: gate plan, A* = UCS, headless engine"
milestone "Sprint 3 - MVP"          "2026-11-29T18:00:00Z" "GR3: delay repair and rebooking live in the dashboard"
milestone "Sprint 4 - Full system"  "2026-12-06T18:00:00Z" "GR4: feature freeze, demo runs end to end"
milestone "Release"                 "2026-12-08T18:00:00Z" "v1.0"

# ---------------------------------------------------------------------------
# 5. Project board (GitHub Projects) linked to the repo
# ---------------------------------------------------------------------------
PROJECT="$(gh project create --owner "$OWNER" --title "AOM Sprint Board" --format json --jq .number)"
gh project link "$PROJECT" --owner "$OWNER" --repo "${OWNER}/${REPO}" >/dev/null
echo "Project board #${PROJECT} created"

# ---------------------------------------------------------------------------
# 6. Sprint 1 issues, each added to the board
# ---------------------------------------------------------------------------
S1="Sprint 1 - Foundations"
issue() {  # title, label, assignee, body
  local url
  url="$(gh issue create --title "$1" --label "$2" --assignee "$3" \
          --milestone "$S1" --body "$4")"
  gh project item-add "$PROJECT" --owner "$OWNER" --url "$url" >/dev/null
  echo "  $url"
}

echo "Creating Sprint 1 issues for Abdullah"
issue "Scaffold repo: pyproject, ruff, mypy, pytest" infra "$ABDULLAH" "Package skeleton, tooling config, README. Commit: chore: scaffold aom package with pyproject, ruff, mypy and pytest"
issue "CI: lint, type check and tests on every push" infra "$ABDULLAH" "GitHub Actions workflow on 3.11 and 3.12. Commit: ci: run lint, type check and tests on every push"
issue "Core: dynamic array with amortised doubling" core "$ABDULLAH" "get/set/append/pop; O(1) amortised append. Property test against list."
issue "Core: singly linked list with tail pointer and sorted insert" core "$ABDULLAH" "append O(1), insert_sorted O(n), remove, iteration."
issue "Core: queue, circular queue and deque" core "$ABDULLAH" "O(1) at both ends; circular queue has fixed capacity. Oracle: collections.deque (tests only)."
issue "Core: BST with insert, search and delete" core "$ABDULLAH" "Baseline for the BST-vs-AVL experiment."
issue "Core: AVL tree with rotations and range query" core "$ABDULLAH" "LL/RR/LR/RL rotations; range(lo, hi) in O(log n + k). Property test: balanced, ordered, height bound."
issue "Core: sorting algorithms" core "$ABDULLAH" "Insertion, selection, bubble, merge (stable), quicksort (median of three). Oracle: sorted() (tests only)."
issue "Core: linear and binary search" core "$ABDULLAH" "O(n) and O(log n) on our dynamic array."
issue "M1: entities and AirportState" m1 "$ABDULLAH" "Flight, Aircraft, Gate, Passenger, Event records (dataclass slots=True); AirportState as single source of truth."
issue "M1: seeded day generator" m1 "$ABDULLAH" "Rotations, peak-hour departures, passengers and manifests. Same seed gives identical day."
issue "M8: download 2025 BTS monthly files" ml "$ABDULLAH" "Script under scripts/; files saved to data/raw/ (git-ignored)."

echo "Creating Sprint 1 issues for Rayyan"
issue "Core: array-backed stack" core "$RAYYAN" "push/pop/peek O(1) amortised, on the dynamic array."
issue "Core: hash table with chaining and resize at 0.75" core "$RAYYAN" "put/get/remove O(1) average. Property test against dict (tests only)."
issue "M2: turns as half-open intervals with buffers" m2 "$RAYYAN" "Arrival-departure pairs; 10-minute buffers either side."
issue "M2: gate facts and Horn-clause rules engine" m2 "$RAYYAN" "Forward chaining derives each turn's gate domain."
issue "M2: constraint graph with a sweep line" m2 "$RAYYAN" "Edges between overlapping turns in O(n log n + E)."

echo "Creating Sprint 1 issues for Rabeet"
issue "Core: binary min-heap with decrease-key" core "$RABEET" "push/pop O(log n), peek O(1). Property test against heapq (tests only)."
issue "Core: adjacency-list graph with BFS and DFS" core "$RABEET" "Adjacency lists on our linked list; iterative DFS on our stack."
issue "M3: regional route network generator" m3 "$RABEET" "About 25 airports with real coordinates, about 600 flights a day."
issue "M3: rebooking search problem with BFS and DFS" m3 "$RABEET" "State = (airport, ready time); toy-network tests."

echo "Done. Open the board, switch it to Board layout and group by Status."
