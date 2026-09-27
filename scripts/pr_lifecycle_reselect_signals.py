#!/usr/bin/env python3
"""Produce live GitHub PR reselect signals for Stage 1 and Stage 3 planning.

Queries live PR state, title, mergeability, head/base SHAs, author, and changed
files for prefiltered candidate items. Fully fail-open: errors degrade to
partial or empty signals with ledger fallback; the planner never hard-fails.
Payload folding lives in pr_lifecycle_signal_accum.py.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess  # nosec B404 - only the fixed gh argv below, never shell=True
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pr_lifecycle_pipeline_health as health
from pr_lifecycle_signal_accum import SignalsAccum, fold_payload

LOGGER = logging.getLogger(__name__)
MAX_CONSECUTIVE_FAILURES = 3
# baseRefOid is unavailable to `gh pr view --json` before gh v2.63.0, so the
# base SHA is enriched via `gh api` like pr_lifecycle_reconcile.py does.
PR_JSON_FIELDS = "state,mergeable,mergeStateStatus,title,headRefOid,author,files"
SHA_RE = re.compile(r"[0-9a-fA-F]{7,64}")

__all__ = [
    "SignalQueryLimits",
    "SignalsResult",
    "prefilter_ledger_items",
    "produce_reselect_signals",
]


@dataclass(frozen=True)
class SignalQueryLimits:
    """Scan bounds for produce_reselect_signals."""

    max_prs: int = 40
    per_call_timeout_s: float = 20.0
    total_budget_s: float = 120.0


_DEFAULT_LIMITS = SignalQueryLimits()


@dataclass(frozen=True)
class SignalsResult:
    """Result of live reselect signals production."""

    signals: health.ReselectSignals = field(default_factory=health.ReselectSignals)
    status: str = "OK"  # "OK" | "PARTIAL" | "DEGRADED" | "SKIPPED"
    queried_count: int = 0
    failed_keys: tuple[str, ...] = ()
    truncated_keys: tuple[str, ...] = ()
    elapsed_s: float = 0.0
    # Successful `gh api` base-SHA enrichments; zero after open-PR view
    # successes means a systemic REST outage (missing scope, rate limit,
    # GHES) is in play. Non-OPEN payloads skip the enrichment entirely.
    base_enriched_count: int = 0
    # Total budget elapsed mid-scan; unqueried candidates keep ledger values.
    timed_out: bool = False
    # Plausible ledger candidates before the max_prs cap. When the cap
    # clips the set, the surplus lands in signals.unqueried_keys — the
    # planner excludes those keys rather than acting on stale ledger state —
    # and the status floors at PARTIAL so the coverage gap is visible.
    candidate_count: int = 0
    # Open-PR payloads folded; the base-enrichment floor and the degraded
    # note's enriched denominator count only these keys.
    open_count: int = 0


def _default_runner(
    cmd: list[str], timeout_s: float
) -> subprocess.CompletedProcess[str]:
    """Run argv without a shell and capture stdout and stderr as text.

    Pass the timeout in seconds to subprocess.run. Nonzero exits are returned;
    OSError, TimeoutExpired, and output decoding errors propagate to the caller.
    """
    # argv list, no shell; repository/pr are schema-constrained ledger fields.
    return subprocess.run(  # nosec B603
        cmd, check=False, capture_output=True, text=True, timeout=timeout_s
    )


def _query_argv(item: dict[str, Any]) -> list[str]:
    """Return the fixed gh pr view argv for one ledger item's live lookup."""
    return [
        "gh",
        "pr",
        "view",
        str(item.get("pr")),
        "--repo",
        str(item.get("repository") or ""),
        "--json",
        PR_JSON_FIELDS,
    ]


def _base_sha_argv(item: dict[str, Any]) -> list[str]:
    """Return the fixed gh api argv for one ledger item's live base SHA."""
    return [
        "gh",
        "api",
        f"repos/{item.get('repository')}/pulls/{item.get('pr')}",
        "--jq",
        ".base.sha",
    ]


def _prefilter_anchors(item: dict[str, Any]) -> bool:
    """Ledger records need key, repository, and PR anchors to be queried."""
    return bool(
        item.get("key") and item.get("repository") and item.get("pr") is not None
    )


def _prefilter_survivors(
    raw_items: list[Any],
    queued_prefixes: set[str],
) -> list[dict[str, Any]]:
    """Keep records able to yield a query and a salvage action, in order."""
    survivors: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if not _prefilter_anchors(item):
            continue
        if health.source_pr_prefix(item.get("key")) in queued_prefixes:
            continue
        if not health.is_reselect_plausible(item):
            continue
        survivors.append(item)
    return survivors


def _ledger_survivors(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every plausible record in owner-priority order, before the cap.

    Only records that can pass the non-live reselect gates are kept: anchors
    (key/repository/PR plus nonempty base/head SHAs), no usable queued work,
    and every ledger-evaluable eligibility gate (never-touch, lifecycle,
    owner, outcome) via health.is_reselect_plausible. Path eligibility and
    title/author identity defer to the selector: an empty or stale ledger
    changed_paths or author cannot disprove what the live file list and
    author login may show. Live signals can only narrow the result.
    """
    raw_items = ledger.get("items")
    if not isinstance(raw_items, list):
        return []
    survivors = _prefilter_survivors(raw_items, health.existing_wi_prefixes(ledger))
    stage1_3 = [
        item for item in survivors if item.get("current_owner") in {"stage1", "stage3"}
    ]
    others = [
        item
        for item in survivors
        if item.get("current_owner") not in {"stage1", "stage3"}
    ]
    return stage1_3 + others


def prefilter_ledger_items(
    ledger: dict[str, Any],
    *,
    max_prs: int = 40,
) -> list[dict[str, Any]]:
    """Return ledger candidates for live queries, prioritizing Stage 1/3 owners.

    Candidates are the first max_prs of _ledger_survivors. Apply max_prs as a
    Python slice stop: zero returns no items, and a negative value omits that
    many items from the end.
    """
    return _ledger_survivors(ledger)[:max_prs]


def _fetch_base_sha(
    run_cmd: Callable[[list[str], float], subprocess.CompletedProcess[str]],
    item: dict[str, Any],
    per_call_timeout_s: float,
) -> str | None:
    """Return the PR's live base SHA via gh api, or None on any failure.

    The base SHA is advisory — the ledger anchor already covers WI assembly
    and reconcile owns base re-anchoring — so a nonzero exit, non-SHA stdout,
    or any runner exception (including a gh binary vanishing mid-scan) just
    drops the enrichment instead of failing the key.
    """
    try:
        base = run_cmd(_base_sha_argv(item), per_call_timeout_s)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        LOGGER.warning(
            "reselect signals: base query failed for one PR (%s)",
            type(exc).__name__,
        )
        return None
    if base.returncode != 0:
        return None
    sha = str(base.stdout or "").strip()
    return sha if SHA_RE.fullmatch(sha) else None


def _fetch_payload(
    run_cmd: Callable[[list[str], float], subprocess.CompletedProcess[str]],
    item: dict[str, Any],
    per_call_timeout_s: float,
) -> tuple[dict[str, Any] | None, bool]:
    """Run the live queries for one item; return (payload, base_enriched).

    `gh pr view` supplies the bulk fields, then a `gh api` REST call enriches
    baseRefOid (unavailable on gh older than v2.63.0) matching the pattern in
    pr_lifecycle_reconcile.py. The base enrichment is additive: its failure
    only omits live_base_sha for the key — the primary payload still counts,
    so a systemic REST outage (missing scope, rate limit, GHES) cannot trip
    the consecutive-failure breaker or discard collected narrowing signals.

    FileNotFoundError (missing gh) propagates for the caller's immediate
    DEGRADED exit. Every other failure — nonzero exit, invalid JSON,
    non-object payload, or a runner exception — yields (None, False) so the
    caller can mark the key failed and keep scanning. Only the exception type
    is logged; messages can echo gh output.
    """
    try:
        completed = run_cmd(_query_argv(item), per_call_timeout_s)
    except FileNotFoundError:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        LOGGER.warning(
            "reselect signals: query failed for one PR (%s)",
            type(exc).__name__,
        )
        return None, False
    parsed = _parse_payload(completed)
    if parsed is None:
        return None, False
    if str(parsed.get("state") or "").strip().upper() != "OPEN":
        # Closed or unknown-state payloads emit no signals, so their base SHA
        # is never used; skipping the enrichment keeps the budget for open
        # candidates, and open_scanned keeps closed-only scans off the
        # base-enrichment floor.
        return parsed, False
    base_sha = _fetch_base_sha(run_cmd, item, per_call_timeout_s)
    if base_sha is not None:
        parsed["baseRefOid"] = base_sha
    return parsed, base_sha is not None


def _parse_payload(
    completed: subprocess.CompletedProcess[str],
) -> dict[str, Any] | None:
    """Decode a `gh pr view` stdout payload; unusable output yields None."""
    if completed.returncode != 0:
        return None
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _finish(
    start_time: float,
    acc: SignalsAccum,
    queried_count: int,
    candidate_count: int,
    unqueried_keys: frozenset[str],
) -> SignalsResult:
    """Assemble the SignalsResult from accumulated state.

    Every signal collected so far is retained — including on DEGRADED — so a
    later query failure cannot resurrect an already-excluded ledger candidate;
    ledger fallback applies only to failed keys and keys the scan left
    unqueried without being cap-clipped (budget/abort). unqueried_keys are
    the plausible records the max_prs cap clipped before any query — they
    carry no live evidence, so they ride the signals bundle and the planner
    excludes them rather than authorizing stale-ledger reselects. View
    successes with zero base enrichments on open PRs also floor at PARTIAL
    so a systemic REST outage is visible instead of reading as a clean scan,
    and a nonempty unqueried_keys floors at PARTIAL so a capped scan does
    not silently drop surplus records.
    """
    signals = acc.to_signals()
    if unqueried_keys:
        signals = replace(signals, unqueried_keys=unqueried_keys)
    return SignalsResult(
        signals=signals,
        status=_resolved_status(acc, bool(unqueried_keys)),
        queried_count=queried_count,
        failed_keys=tuple(acc.failed),
        truncated_keys=tuple(acc.truncated),
        elapsed_s=round(time.monotonic() - start_time, 4),
        base_enriched_count=acc.base_enriched,
        timed_out=acc.timed_out,
        candidate_count=candidate_count,
        open_count=acc.open_scanned,
    )


def _resolved_status(acc: SignalsAccum, clipped: bool) -> str:
    """Resolve the scan status; coverage gaps floor at PARTIAL."""
    if acc.hard_status is not None:
        return acc.hard_status
    if acc.timed_out:
        return "PARTIAL"
    if acc.failed or clipped:
        return "PARTIAL"
    if acc.open_scanned > 0:
        if acc.base_enriched == 0:
            return "PARTIAL"
    return "OK"


def _scan_item(
    acc: SignalsAccum,
    run_cmd: Callable[[list[str], float], subprocess.CompletedProcess[str]],
    item: dict[str, Any],
    per_call_timeout_s: float,
) -> None:
    """Query one candidate and record the outcome; set hard_status on stops.

    A missing gh binary (FileNotFoundError) or MAX_CONSECUTIVE_FAILURES in a
    row flips hard_status to DEGRADED, which the caller turns into an early
    exit. All collected signals stay in acc either way.
    """
    key = str(item.get("key") or "")
    try:
        payload, base_enriched = _fetch_payload(run_cmd, item, per_call_timeout_s)
    except FileNotFoundError:
        # gh missing -> global degradation immediately.
        acc.failed.append(key)
        acc.hard_status = "DEGRADED"
        return
    if payload is None:
        acc.failed.append(key)
        acc.consecutive_failures += 1
        if acc.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            acc.hard_status = "DEGRADED"
        return
    acc.consecutive_failures = 0
    acc.base_enriched += int(base_enriched)
    fold_payload(acc, key, payload)


def produce_reselect_signals(
    ledger: dict[str, Any],
    *,
    runner: (
        Callable[[list[str], float], subprocess.CompletedProcess[str]] | None
    ) = None,
    limits: SignalQueryLimits = _DEFAULT_LIMITS,
) -> SignalsResult:
    """Query GitHub for live signals on prefiltered ledger candidates.

    Use gh pr view unless runner is supplied; runner receives argv and the
    per-call timeout in seconds. limits.max_prs bounds the candidate slice
    taken from _ledger_survivors; the clipped surplus lands in
    signals.unqueried_keys. Check limits.total_budget_s before each query,
    so an in-flight call can exceed the total budget. A nonpositive budget
    prevents queries.

    Return signals keyed by full ledger keys, attempted-query count, failed
    and truncated keys, and elapsed seconds. Closed/merged PRs populate only
    closed_keys; unknown PR states emit no signals. File lists with at least
    100 entries or malformed entries are marked truncated and omitted from
    path signals; accepted lists omit .jules paths and may be empty. These
    paths are changed-file proxies, not verified unique remaining source.

    Return OK if the scan finishes without primary-query failures, queried
    every candidate within limits.max_prs, and at least one base enrichment
    succeeded (or nothing was scanned). View-call failures, budget
    exhaustion, the max_prs cap clipping the candidate set, or a full
    base-enrichment gap — every open-PR view succeeded yet no `gh api` base
    SHA came back, the observable signature of a systemic REST outage —
    yield PARTIAL with accumulated signals. Non-OPEN payloads emit no
    signals and skip the base enrichment entirely, so a scan of closed PRs
    is not miscounted as a REST outage. The base enrichment itself stays
    advisory: failures never fail a key.
    Missing gh on a view call, producer-level exceptions, or
    MAX_CONSECUTIVE_FAILURES straight view failures yield DEGRADED; the
    consecutive-failure and missing-gh exits retain every signal collected
    so far while producer-level exceptions emit none. Truncated files alone
    do not change status; SKIPPED is never returned.
    """
    start_time = time.monotonic()
    run_cmd = runner or _default_runner

    try:
        survivors = _ledger_survivors(ledger)
        candidates = survivors[: limits.max_prs]
        acc = SignalsAccum()
        queried_count = 0
        for item in candidates:
            if time.monotonic() - start_time >= limits.total_budget_s:
                acc.timed_out = True
                break
            queried_count += 1
            _scan_item(acc, run_cmd, item, limits.per_call_timeout_s)
            if acc.hard_status is not None:
                break
        unqueried = frozenset(
            key
            for item in survivors[limits.max_prs :]
            if (key := str(item.get("key") or ""))
        )
        return _finish(start_time, acc, queried_count, len(survivors), unqueried)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Global fail-open. Log the type only, no message/traceback.
        LOGGER.warning("reselect signals: producer DEGRADED (%s)", type(exc).__name__)
        return SignalsResult(
            signals=health.ReselectSignals(),
            status="DEGRADED",
            queried_count=0,
            failed_keys=(),
            truncated_keys=(),
            elapsed_s=round(time.monotonic() - start_time, 4),
        )
