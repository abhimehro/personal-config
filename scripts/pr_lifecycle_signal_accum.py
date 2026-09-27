#!/usr/bin/env python3
"""Signal accumulation for the live reselect-signals producer.

Per-key maps plus closed/truncated/failed bookkeeping, folded from successful
gh payloads. Closed or merged PRs populate only closed_keys; truncated file
lists (page cap or malformed entries) mark the key and omit path signals;
accepted file lists omit .jules paths and may be empty.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pr_lifecycle_pipeline_health as health  # noqa: E402

CLOSED_PR_STATES = frozenset({"CLOSED", "MERGED"})
FILE_LIST_TRUNCATION = 100


@dataclass
class SignalsAccum:
    """Per-key signal maps and outcome state collected while scanning."""

    live_mergeable: dict[str, str] = field(default_factory=dict)
    titles: dict[str, str] = field(default_factory=dict)
    unique_paths: dict[str, list[str]] = field(default_factory=dict)
    live_head_sha: dict[str, str] = field(default_factory=dict)
    live_base_sha: dict[str, str] = field(default_factory=dict)
    author_login: dict[str, str] = field(default_factory=dict)
    closed: set[str] = field(default_factory=set)
    truncated: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    consecutive_failures: int = 0
    timed_out: bool = False
    hard_status: str | None = None
    base_enriched: int = 0

    def to_signals(self) -> health.ReselectSignals:
        return health.ReselectSignals(
            live_mergeable_by_key=_non_empty(self.live_mergeable),
            titles_by_key=_non_empty(self.titles),
            unique_paths_by_key=_non_empty(self.unique_paths),
            live_head_sha_by_key=_non_empty(self.live_head_sha),
            live_base_sha_by_key=_non_empty(self.live_base_sha),
            author_login_by_key=_non_empty(self.author_login),
            closed_keys=_non_empty(frozenset(self.closed)),
        )


_T = TypeVar("_T")


def _non_empty(collection: _T) -> _T | None:
    return collection or None


def _record_mergeable(acc: SignalsAccum, key: str, payload: dict[str, Any]) -> None:
    mergeable = str(payload.get("mergeable") or "").strip().upper()
    merge_state_status = str(payload.get("mergeStateStatus") or "").strip().upper()
    if mergeable == "CONFLICTING":
        acc.live_mergeable[key] = "CONFLICTING"
    elif merge_state_status == "DIRTY":
        acc.live_mergeable[key] = "DIRTY"
    elif mergeable == "MERGEABLE":
        acc.live_mergeable[key] = "MERGEABLE"
    elif merge_state_status in health.AUTHORITATIVE_MERGEABLE_STATES:
        acc.live_mergeable[key] = merge_state_status


def _record_text(target: dict[str, str], key: str, raw: Any) -> None:
    if isinstance(raw, str) and raw.strip():
        target[key] = raw.strip()


def _record_identity_fields(
    acc: SignalsAccum, key: str, payload: dict[str, Any]
) -> None:
    """Map live title, head/base SHAs, and author login into signal maps."""
    _record_text(acc.titles, key, payload.get("title"))
    _record_text(acc.live_head_sha, key, payload.get("headRefOid"))
    _record_text(acc.live_base_sha, key, payload.get("baseRefOid"))
    author = payload.get("author")
    if isinstance(author, dict):
        _record_text(acc.author_login, key, author.get("login"))


def _file_entry_ok(entry: Any) -> bool:
    return isinstance(entry, dict) and bool(entry.get("path"))


def _files_unreliable(files: list[Any]) -> bool:
    """Return True when the file list hit the page cap or has bad entries."""
    return len(files) >= FILE_LIST_TRUNCATION or not all(
        _file_entry_ok(entry) for entry in files
    )


def _record_paths(acc: SignalsAccum, key: str, payload: dict[str, Any]) -> None:
    """Map the changed-file list into unique paths, or mark the key truncated."""
    files = payload.get("files")
    if not isinstance(files, list):
        return
    if _files_unreliable(files):
        acc.truncated.append(key)
        return
    acc.unique_paths[key] = health.non_journal_paths([str(f["path"]) for f in files])


def fold_payload(acc: SignalsAccum, key: str, payload: dict[str, Any]) -> None:
    """Fold one live payload into the accumulator for an open-or-closed PR."""
    state = str(payload.get("state") or "").strip().upper()
    if state in CLOSED_PR_STATES:
        acc.closed.add(key)
        return
    if state != "OPEN":
        return
    _record_mergeable(acc, key, payload)
    _record_identity_fields(acc, key, payload)
    _record_paths(acc, key, payload)
