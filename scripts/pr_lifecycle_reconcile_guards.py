"""Apply-time guards for reconcile: partial-inventory abort, per-save cap, CAS replan."""

# Kept separate from pr_lifecycle_reconcile so the planner stays unchanged and the
# guards can be tested without GitHub.

from __future__ import annotations

import os
import random
import time
from typing import Any

# Report-only actions never mutate the ledger and never count against the cap.
REPORT_ONLY_ACTIONS = frozenset(
    {
        "LIVE_LOOKUP_FAILED",
        "INGEST_SKIPPED",
        "TERMINAL_BUT_OPEN",
        "INVENTORY_FAILED",
        "PATH_BACKFILL_FAILED",
    }
)
DEFAULT_MAX_APPLY = 60
MAX_CAS_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 20.0
INVENTORY_ABORT_EXIT = 3
CAS_CONFLICT_EXIT = 4


def max_apply_from_env(explicit: int | None = None) -> int:
    """Return the per-save mutation cap (CLI value, then env, then default)."""
    if explicit is not None:
        return max(1, explicit)
    raw = os.environ.get("PR_LIFECYCLE_MAX_APPLY", "")
    try:
        return max(1, int(raw)) if raw.strip() else DEFAULT_MAX_APPLY
    except ValueError:
        return DEFAULT_MAX_APPLY


def action_priority(action: dict[str, Any]) -> int:
    """Lower sorts first: terminal bookkeeping, stale closes, re-anchors, intake."""
    name = str(action.get("action", ""))
    if name.startswith("TERMINAL_"):
        return 0
    if name == "CLOSE_STALE":
        return 1
    if name in {"REANCHOR_HEAD", "SHA_DRIFT_REINTAKE"}:
        return 2
    if name == "INGEST_OPEN_PR":
        return 4
    return 3


def select_batch(
    actions: list[dict[str, Any]], cap: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split actions into (selected, deferred) with at most cap mutating actions."""
    # Report-only actions are always kept so the plan still reports them. The
    # sort is stable, so the planner's order holds within a priority band.
    report = [a for a in actions if a.get("action") in REPORT_ONLY_ACTIONS]
    mutating = [a for a in actions if a.get("action") not in REPORT_ONLY_ACTIONS]
    mutating.sort(key=action_priority)
    return report + mutating[:cap], mutating[cap:]


def backoff_seconds(attempt: int, *, rng: Any = random.random) -> float:
    """Jittered exponential backoff: ~20s, ~40s, ~80s for attempts 1..3."""
    base = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    return base * (0.75 + 0.5 * rng())


# Patchable sleep reference for tests.
sleep = time.sleep
