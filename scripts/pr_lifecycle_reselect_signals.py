#!/usr/bin/env python3
"""Produce live GitHub PR reselect signals for Stage 1 and Stage 3 planning.

Queries live PR state, title, mergeability, headRefOid, author, and changed files
for prefiltered candidate items. Fully fail-open: errors degrade to empty signals
or ledger fallback without failing the planner.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pr_lifecycle_pipeline_health as health

LOGGER = logging.getLogger(__name__)
CLOSED_PR_STATES = frozenset({"CLOSED", "MERGED"})

NON_SALVAGE_OUTCOMES = getattr(
    health,
    "NON_SALVAGE_OUTCOMES",
    frozenset(
        {
            "REVIEW_SECURITY",
            "HOLD_PLATFORM",
            "HOLD_CANONICAL",
            "PASS_ROUTINE",
            "CLOSE_NONSECURITY_NOOP",
            "ANALYSIS_ERROR",
        }
    ),
)
STAGE2_OWNED_STATES = getattr(
    health, "STAGE2_OWNED_STATES", frozenset({"STAGE2_QUEUED", "STAGE2_ACTIVE"})
)

__all__ = [
    "SignalsResult",
    "prefilter_ledger_items",
    "produce_reselect_signals",
]


@dataclass(frozen=True)
class SignalsResult:
    """Result of live reselect signals production."""

    signals: health.ReselectSignals = field(default_factory=health.ReselectSignals)
    status: str = "OK"  # "OK" | "PARTIAL" | "DEGRADED" | "SKIPPED"
    queried_count: int = 0
    failed_keys: tuple[str, ...] = ()
    truncated_keys: tuple[str, ...] = ()
    elapsed_s: float = 0.0


def _default_runner(
    cmd: list[str], timeout_s: float
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, check=False, capture_output=True, text=True, timeout=timeout_s
    )


def prefilter_ledger_items(
    ledger: dict[str, Any],
    *,
    max_prs: int = 40,
) -> list[dict[str, Any]]:
    """Return survivor items using cheap ledger checks only.

    Do not filter on author_type, next_action, or paths.
    """
    queued_prefixes = health.existing_wi_prefixes(ledger)
    raw_items = ledger.get("items")
    if not isinstance(raw_items, list):
        return []

    survivors: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        repo = item.get("repository")
        pr = item.get("pr")
        if not key or not repo or pr is None:
            continue
        if health.is_never_touch_key(key):
            continue
        if item.get("lifecycle_state") == "TERMINAL":
            continue
        if (
            item.get("current_owner") == "stage2"
            or item.get("lifecycle_state") in STAGE2_OWNED_STATES
        ):
            continue
        if (item.get("guardrail_outcome") or "") in NON_SALVAGE_OUTCOMES:
            continue
        if health.source_pr_prefix(key) in queued_prefixes:
            continue
        survivors.append(item)

    # Order: keep ledger order, but put current_owner in {stage1, stage3} items first
    stage1_3 = [
        item for item in survivors if item.get("current_owner") in {"stage1", "stage3"}
    ]
    others = [
        item
        for item in survivors
        if item.get("current_owner") not in {"stage1", "stage3"}
    ]
    return (stage1_3 + others)[:max_prs]


def produce_reselect_signals(
    ledger: dict[str, Any],
    *,
    runner: (
        Callable[[list[str], float], subprocess.CompletedProcess[str]] | None
    ) = None,
    max_prs: int = 40,
    per_call_timeout_s: float = 20.0,
    total_budget_s: float = 120.0,
) -> SignalsResult:
    """Produce live reselect signals for prefiltered ledger items."""
    start_time = time.monotonic()
    run_cmd = runner or _default_runner

    try:
        candidates = prefilter_ledger_items(ledger, max_prs=max_prs)
        if not candidates:
            return SignalsResult(
                signals=health.ReselectSignals(),
                status="OK",
                queried_count=0,
                failed_keys=(),
                truncated_keys=(),
                elapsed_s=round(time.monotonic() - start_time, 4),
            )

        live_mergeable_by_key: dict[str, str] = {}
        titles_by_key: dict[str, str] = {}
        unique_paths_by_key: dict[str, list[str]] = {}
        live_head_sha_by_key: dict[str, str] = {}
        author_login_by_key: dict[str, str] = {}
        closed_keys: set[str] = set()

        failed_keys: list[str] = []
        truncated_keys: list[str] = []
        queried_count = 0
        consecutive_failures = 0
        timed_out = False

        for item in candidates:
            elapsed = time.monotonic() - start_time
            if elapsed >= total_budget_s:
                timed_out = True
                break

            key = str(item.get("key") or "")
            repo = str(item.get("repository") or "")
            pr = item.get("pr")

            cmd = [
                "gh",
                "pr",
                "view",
                str(pr),
                "--repo",
                repo,
                "--json",
                "state,mergeable,mergeStateStatus,title,headRefOid,author,files",
            ]

            queried_count += 1
            payload: dict[str, Any] | None = None
            try:
                completed = run_cmd(cmd, per_call_timeout_s)
                if completed.returncode != 0:
                    failed_keys.append(key)
                    consecutive_failures += 1
                else:
                    try:
                        parsed = json.loads(completed.stdout)
                        if isinstance(parsed, dict):
                            payload = parsed
                            consecutive_failures = 0
                        else:
                            failed_keys.append(key)
                            consecutive_failures += 1
                    except json.JSONDecodeError:
                        failed_keys.append(key)
                        consecutive_failures += 1
            except FileNotFoundError:
                # gh missing -> global degradation immediately
                return SignalsResult(
                    signals=health.ReselectSignals(),
                    status="DEGRADED",
                    queried_count=queried_count,
                    failed_keys=tuple(failed_keys + [key]),
                    truncated_keys=tuple(truncated_keys),
                    elapsed_s=round(time.monotonic() - start_time, 4),
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # Fail open per key. Log the type only: messages can echo gh output.
                LOGGER.warning(
                    "reselect signals: query failed for one PR (%s)",
                    type(exc).__name__,
                )
                failed_keys.append(key)
                consecutive_failures += 1

            if consecutive_failures >= 3:
                # 3 consecutive failures -> DEGRADED with empty signals
                return SignalsResult(
                    signals=health.ReselectSignals(),
                    status="DEGRADED",
                    queried_count=queried_count,
                    failed_keys=tuple(failed_keys),
                    truncated_keys=tuple(truncated_keys),
                    elapsed_s=round(time.monotonic() - start_time, 4),
                )

            if payload is None:
                continue

            state = str(payload.get("state") or "").strip().upper()
            if state in CLOSED_PR_STATES:
                # Authoritative terminal state: exclude from reselect.
                closed_keys.add(key)
                continue
            if state != "OPEN":
                # Missing/unknown state: emit nothing; ledger fallback stays active.
                continue

            # Mergeability mapping
            mergeable = str(payload.get("mergeable") or "").strip().upper()
            merge_state_status = (
                str(payload.get("mergeStateStatus") or "").strip().upper()
            )
            if mergeable == "CONFLICTING":
                live_mergeable_by_key[key] = "CONFLICTING"
            elif merge_state_status == "DIRTY":
                live_mergeable_by_key[key] = "DIRTY"
            elif mergeable == "MERGEABLE":
                live_mergeable_by_key[key] = "MERGEABLE"
            elif merge_state_status in health.AUTHORITATIVE_MERGEABLE_STATES:
                # e.g. UNKNOWN + BLOCKED: still authoritative; never let stale
                # ledger text resurrect CONFLICTING/DIRTY.
                live_mergeable_by_key[key] = merge_state_status

            # Title mapping
            title = payload.get("title")
            if isinstance(title, str) and title.strip():
                titles_by_key[key] = title

            # Head SHA mapping
            head_ref_oid = payload.get("headRefOid")
            if isinstance(head_ref_oid, str) and head_ref_oid.strip():
                live_head_sha_by_key[key] = head_ref_oid.strip()

            # Author login mapping
            author = payload.get("author")
            if isinstance(author, dict):
                login = str(author.get("login") or "").strip()
                if login:
                    author_login_by_key[key] = login

            # Unique paths mapping
            files = payload.get("files")
            if isinstance(files, list):
                if len(files) >= 100 or any(
                    not isinstance(f, dict) or not f.get("path") for f in files
                ):
                    truncated_keys.append(key)
                else:
                    paths = [str(f["path"]) for f in files]
                    unique_paths_by_key[key] = health.non_journal_paths(paths)

        elapsed_total = round(time.monotonic() - start_time, 4)
        status = "PARTIAL" if (timed_out or len(failed_keys) > 0) else "OK"
        signals = health.ReselectSignals(
            live_mergeable_by_key=live_mergeable_by_key or None,
            titles_by_key=titles_by_key or None,
            unique_paths_by_key=unique_paths_by_key or None,
            live_head_sha_by_key=live_head_sha_by_key or None,
            author_login_by_key=author_login_by_key or None,
            closed_keys=frozenset(closed_keys) or None,
        )
        return SignalsResult(
            signals=signals,
            status=status,
            queried_count=queried_count,
            failed_keys=tuple(failed_keys),
            truncated_keys=tuple(truncated_keys),
            elapsed_s=elapsed_total,
        )

    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Global fail-open. Log the type only, no message/traceback.
        LOGGER.warning(
            "reselect signals: producer DEGRADED (%s)", type(exc).__name__
        )
        return SignalsResult(
            signals=health.ReselectSignals(),
            status="DEGRADED",
            queried_count=0,
            failed_keys=(),
            truncated_keys=(),
            elapsed_s=round(time.monotonic() - start_time, 4),
        )
