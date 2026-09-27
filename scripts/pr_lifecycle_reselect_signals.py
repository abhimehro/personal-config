#!/usr/bin/env python3
"""Produce live GitHub PR reselect signals for Stage 1 and Stage 3 planning.

Queries live PR state, title, mergeability, head/base SHAs, author, and changed
files for prefiltered candidate items. Fully fail-open: errors degrade to
partial or empty signals with ledger fallback; the planner never hard-fails.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess  # nosec B404 - only the fixed gh argv below, never shell=True
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
MAX_CONSECUTIVE_FAILURES = 3
FILE_LIST_TRUNCATION = 100
# baseRefOid is unavailable to `gh pr view --json` before gh v2.63.0, so the
# base SHA is enriched via `gh api` like pr_lifecycle_reconcile.py does.
PR_JSON_FIELDS = "state,mergeable,mergeStateStatus,title,headRefOid,author,files"
SHA_RE = re.compile(r"[0-9a-fA-F]{7,64}")

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


def prefilter_ledger_items(
    ledger: dict[str, Any],
    *,
    max_prs: int = 40,
    author_gate: health.ReselectAuthorGate | None = None,
) -> list[dict[str, Any]]:
    """Return ledger candidates for live queries, prioritizing Stage 1/3 owners.

    Only records that can pass the non-live reselect gates are kept: anchors
    (key/repository/PR plus nonempty base/head SHAs), no usable queued work,
    and every ledger-evaluable eligibility gate (never-touch, lifecycle,
    owner, outcome, identity author, paths) via health.is_reselect_plausible.
    Ledger records carry no title field, so title-gated items stay plausible
    on an allowlisted ledger author. Live signals can only narrow the result.
    Preserve ledger order within each priority group and return the original
    item dictionaries. Apply max_prs as a Python slice stop: zero returns no
    items, and a negative value omits that many items from the end.
    """
    raw_items = ledger.get("items")
    if not isinstance(raw_items, list):
        return []

    gate = (author_gate or health.ReselectAuthorGate()).resolved()
    queued_prefixes = health.existing_wi_prefixes(ledger)
    survivors: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if not _prefilter_anchors(item):
            continue
        if health.source_pr_prefix(item.get("key")) in queued_prefixes:
            continue
        if not health.is_reselect_plausible(item, author_gate=gate):
            continue
        survivors.append(item)

    # Order: keep ledger order, but put current_owner in {stage1, stage3} first
    stage1_3 = [
        item for item in survivors if item.get("current_owner") in {"stage1", "stage3"}
    ]
    others = [
        item
        for item in survivors
        if item.get("current_owner") not in {"stage1", "stage3"}
    ]
    return (stage1_3 + others)[:max_prs]


def _prefilter_anchors(item: dict[str, Any]) -> bool:
    """Ledger records need key, repository, and PR anchors to be queried."""
    return bool(
        item.get("key") and item.get("repository") and item.get("pr") is not None
    )


@dataclass
class _SignalsAccum:
    """Per-key signal maps and outcome state collected while scanning."""

    live_mergeable: dict[str, str] = field(default_factory=dict)
    titles: dict[str, str] = field(default_factory=dict)
    unique_paths: dict[str, list[str]] = field(default_factory=dict)
    live_head_sha: dict[str, str] = field(default_factory=dict)
    live_base_sha: dict[str, str] = field(default_factory=dict)
    author_login: dict[str, str] = field(default_factory=dict)
    closed: set[str] = field(default_factory=set)
    failed: list[str] = field(default_factory=list)
    truncated: list[str] = field(default_factory=list)
    consecutive_failures: int = 0
    timed_out: bool = False
    hard_status: str | None = None

    def to_signals(self) -> health.ReselectSignals:
        """Materialize collected maps into the immutable signal bundle."""
        return health.ReselectSignals(
            live_mergeable_by_key=self.live_mergeable or None,
            titles_by_key=self.titles or None,
            unique_paths_by_key=self.unique_paths or None,
            live_head_sha_by_key=self.live_head_sha or None,
            live_base_sha_by_key=self.live_base_sha or None,
            author_login_by_key=self.author_login or None,
            closed_keys=frozenset(self.closed) or None,
        )


def _fetch_base_sha(
    run_cmd: Callable[[list[str], float], subprocess.CompletedProcess[str]],
    item: dict[str, Any],
    per_call_timeout_s: float,
) -> str | None:
    """Return the PR's live base SHA via gh api, or None on any failure.

    FileNotFoundError (missing gh) propagates like the main query. A nonzero
    exit or a non-SHA stdout (for example an error body) yields None so the
    caller fails the key instead of trusting a stale ledger anchor.
    """
    try:
        base = run_cmd(_base_sha_argv(item), per_call_timeout_s)
    except FileNotFoundError:
        raise
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
) -> dict[str, Any] | None:
    """Run the live queries for one item; return the payload or None.

    `gh pr view` supplies the bulk fields, then a `gh api` REST call enriches
    baseRefOid (unavailable on gh older than v2.63.0) matching the pattern in
    pr_lifecycle_reconcile.py. Fail closed on either call: a partial payload
    risks stamping a stale base anchor into a proposal.

    FileNotFoundError (missing gh) propagates for the caller's immediate
    DEGRADED exit. Every other failure — nonzero exit, invalid JSON,
    non-object payload, or a runner exception — yields None so the caller can
    mark the key failed and keep scanning. Only the exception type is logged;
    messages can echo gh output.
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
        return None
    if completed.returncode != 0:
        return None
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    base_sha = _fetch_base_sha(run_cmd, item, per_call_timeout_s)
    if base_sha is None:
        return None
    parsed["baseRefOid"] = base_sha
    return parsed


def _record_mergeable(acc: _SignalsAccum, key: str, payload: dict[str, Any]) -> None:
    """Map live mergeability into the per-key signal map."""
    mergeable = str(payload.get("mergeable") or "").strip().upper()
    merge_state_status = str(payload.get("mergeStateStatus") or "").strip().upper()
    if mergeable == "CONFLICTING":
        acc.live_mergeable[key] = "CONFLICTING"
    elif merge_state_status == "DIRTY":
        acc.live_mergeable[key] = "DIRTY"
    elif mergeable == "MERGEABLE":
        acc.live_mergeable[key] = "MERGEABLE"
    elif merge_state_status in health.AUTHORITATIVE_MERGEABLE_STATES:
        # e.g. UNKNOWN + BLOCKED: still authoritative; never let stale
        # ledger text resurrect CONFLICTING/DIRTY.
        acc.live_mergeable[key] = merge_state_status


def _record_text(target: dict[str, str], key: str, raw: Any) -> None:
    """Store a stripped nonempty string field under key."""
    if isinstance(raw, str) and raw.strip():
        target[key] = raw.strip()


def _record_identity_fields(
    acc: _SignalsAccum, key: str, payload: dict[str, Any]
) -> None:
    """Map live title, head/base SHAs, and author login into signal maps."""
    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        acc.titles[key] = title
    _record_text(acc.live_head_sha, key, payload.get("headRefOid"))
    _record_text(acc.live_base_sha, key, payload.get("baseRefOid"))
    author = payload.get("author")
    if isinstance(author, dict):
        _record_text(acc.author_login, key, author.get("login"))


def _files_unreliable(files: list[Any]) -> bool:
    """Return True when the file list hit the page cap or has bad entries."""
    if len(files) >= FILE_LIST_TRUNCATION:
        return True
    return any(not isinstance(f, dict) or not f.get("path") for f in files)


def _record_paths(acc: _SignalsAccum, key: str, payload: dict[str, Any]) -> None:
    """Map the changed-file list into unique paths, or mark the key truncated."""
    files = payload.get("files")
    if not isinstance(files, list):
        return
    if _files_unreliable(files):
        acc.truncated.append(key)
        return
    acc.unique_paths[key] = health.non_journal_paths([str(f["path"]) for f in files])


def _fold_payload(acc: _SignalsAccum, key: str, payload: dict[str, Any]) -> None:
    """Fold one successful OPEN payload into the accumulators."""
    state = str(payload.get("state") or "").strip().upper()
    if state in CLOSED_PR_STATES:
        # Authoritative terminal state: exclude from reselect.
        acc.closed.add(key)
        return
    if state != "OPEN":
        # Missing/unknown state: emit nothing; ledger fallback stays active.
        return
    _record_mergeable(acc, key, payload)
    _record_identity_fields(acc, key, payload)
    _record_paths(acc, key, payload)


def _finish(
    start_time: float,
    acc: _SignalsAccum,
    queried_count: int,
) -> SignalsResult:
    """Assemble the SignalsResult from accumulated state.

    Every signal collected so far is retained — including on DEGRADED — so a
    later query failure cannot resurrect an already-excluded ledger candidate;
    ledger fallback applies only to failed or unqueried keys.
    """
    resolved = acc.hard_status or ("PARTIAL" if (acc.timed_out or acc.failed) else "OK")
    return SignalsResult(
        signals=acc.to_signals(),
        status=resolved,
        queried_count=queried_count,
        failed_keys=tuple(acc.failed),
        truncated_keys=tuple(acc.truncated),
        elapsed_s=round(time.monotonic() - start_time, 4),
    )


def _scan_item(
    acc: _SignalsAccum,
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
        payload = _fetch_payload(run_cmd, item, per_call_timeout_s)
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
    _fold_payload(acc, key, payload)


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
    """Query GitHub for live signals on prefiltered ledger candidates.

    Use gh pr view unless runner is supplied; runner receives argv and the
    per-call timeout in seconds. max_prs is passed to prefilter_ledger_items.
    Check total_budget_s before each query, so an in-flight call can exceed
    the total budget. A nonpositive budget prevents queries.

    Return signals keyed by full ledger keys, attempted-query count, failed
    and truncated keys, and elapsed seconds. Closed/merged PRs populate only
    closed_keys; unknown PR states emit no signals. File lists with at least
    100 entries or malformed entries are marked truncated and omitted from
    path signals; accepted lists omit .jules paths and may be empty. These
    paths are changed-file proxies, not verified unique remaining source.

    Return OK if the scan finishes without query failures, including when
    there are no candidates. Query failures or budget exhaustion yield
    PARTIAL with accumulated signals. Missing gh, producer-level exceptions,
    or MAX_CONSECUTIVE_FAILURES straight failures yield DEGRADED; the
    consecutive-failure and missing-gh exits retain every signal collected so
    far while producer-level exceptions emit none. Truncated files and the
    candidate cap alone do not change status; SKIPPED is never returned.
    """
    start_time = time.monotonic()
    run_cmd = runner or _default_runner

    try:
        candidates = prefilter_ledger_items(ledger, max_prs=max_prs)
        acc = _SignalsAccum()
        queried_count = 0
        for item in candidates:
            if time.monotonic() - start_time >= total_budget_s:
                acc.timed_out = True
                break
            queried_count += 1
            _scan_item(acc, run_cmd, item, per_call_timeout_s)
            if acc.hard_status is not None:
                break
        return _finish(start_time, acc, queried_count)
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
