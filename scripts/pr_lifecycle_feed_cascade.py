#!/usr/bin/env python3
"""Fail-closed Stage 1→2→3 feed cascade decisions.

Encodes the prompt/spec contract: Stage 1 feed fingerprints, Stage 2 FEED_FAIL
short-circuit, and Stage 3 upstream-pause. Pure functions over already-fetched
ledger summaries and run-record fields — no CAS, no Dashboard calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pr_lifecycle_pipeline_health import PipelineHealth, work_item_is_usable

ThroughputGrade = Literal["PASS", "FAIL"]
CascadeAction = Literal["PROCEED", "FEED_FAIL", "EMPTY_INTAKE", "UPSTREAM_PAUSE"]


@dataclass(frozen=True)
class FeedFingerprint:
    """Stage 1 run-record feed fields consumed by Stage 2/3."""

    stage2_queued_count: int
    salvage_eligible_count: int
    throughput_grade: ThroughputGrade


@dataclass(frozen=True)
class CascadeDecision:
    """Downstream short-circuit outcome."""

    action: CascadeAction
    label: str
    reason: str


def _feed_is_starved(queued: int, eligible: int) -> bool:
    """True when salvage-eligible stock remains and nothing was queued."""
    return eligible > 0 and not queued


def _decision(
    action: CascadeAction, label: str, reason: str
) -> CascadeDecision:
    """Build a cascade decision record."""
    return CascadeDecision(action=action, label=label, reason=reason)


def grade_stage1_feed(
    *,
    stage2_queued_count: int,
    salvage_eligible_count: int,
    product_slots_unused_while_bot_grew: bool = False,
    docs_only_bookkeeping: bool = False,
) -> FeedFingerprint:
    """Compute Stage 1 throughput_grade from feed counts and drain signals."""
    starved = _feed_is_starved(stage2_queued_count, salvage_eligible_count)
    drain_fail = product_slots_unused_while_bot_grew or docs_only_bookkeeping
    grade: ThroughputGrade = "FAIL" if starved or drain_fail else "PASS"
    return FeedFingerprint(
        stage2_queued_count=stage2_queued_count,
        salvage_eligible_count=salvage_eligible_count,
        throughput_grade=grade,
    )


def _fingerprint_feed_fail(fingerprint: FeedFingerprint) -> CascadeDecision:
    """FEED_FAIL when today's Stage 1 queued nothing despite eligible stock."""
    return _decision(
        "FEED_FAIL",
        "FEED_FAIL",
        (
            "Stage 1 queued 0 while salvage-eligible > 0 "
            f"(queued={fingerprint.stage2_queued_count}, "
            f"eligible={fingerprint.salvage_eligible_count})"
        ),
    )


def _stage2_feed_or_empty(
    fingerprint: FeedFingerprint | None,
) -> CascadeDecision:
    """FEED_FAIL on starved fingerprint; else EMPTY_INTAKE."""
    # ASSUMES: short-circuit only on starved feed, not every Stage 1 FAIL.
    if fingerprint is not None and _feed_is_starved(
        fingerprint.stage2_queued_count,
        fingerprint.salvage_eligible_count,
    ):
        return _fingerprint_feed_fail(fingerprint)
    return _decision(
        "EMPTY_INTAKE",
        "EMPTY_INTAKE",
        "No usable work items and Stage 1 queued none",
    )


def stage2_cascade_decision(
    health: PipelineHealth,
    fingerprint: FeedFingerprint | None,
    *,
    usable_work_item_count: int,
    stage2_owned_materializable: int = 0,
) -> CascadeDecision:
    """Decide whether Stage 2 proceeds or stops after the first ~30 seconds."""
    # SECURITY: claim queued complete WIs before grading today's feed.
    claimed = usable_work_item_count > 0 or stage2_owned_materializable > 0
    if claimed:
        return _decision(
            "PROCEED", "CLAIM", "Complete unexpired Stage 2 work item available"
        )
    if health.starvation:
        return _decision("FEED_FAIL", "EMPTY_INTAKE_STARVATION", health.reason)
    return _stage2_feed_or_empty(fingerprint)


def _stage3_fingerprint_pause(
    fingerprint: FeedFingerprint | None,
) -> CascadeDecision | None:
    """Pause when same-day Stage 1 fingerprint is missing or FAIL."""
    if fingerprint is None:
        return _decision(
            "UPSTREAM_PAUSE",
            "UPSTREAM_PAUSE",
            "Missing same-day Stage 1 feed fingerprint",
        )
    if fingerprint.throughput_grade == "FAIL":
        return _decision(
            "UPSTREAM_PAUSE",
            "UPSTREAM_PAUSE",
            "Stage 1 throughput_grade FAIL",
        )
    return None


def stage3_cascade_decision(
    health: PipelineHealth,
    fingerprint: FeedFingerprint | None,
    *,
    stage2_feed_fail_same_utc_day: bool,
) -> CascadeDecision:
    """Decide whether Stage 3 spends completion actions or pauses."""
    if stage2_feed_fail_same_utc_day:
        return _decision(
            "UPSTREAM_PAUSE",
            "UPSTREAM_PAUSE",
            "Stage 2 stopped on FEED_FAIL same UTC day",
        )
    if health.starvation:
        return _decision("UPSTREAM_PAUSE", "UPSTREAM_PAUSE", health.reason)
    # Fail closed: missing same-day Stage 1 fingerprint is not "healthy".
    paused = _stage3_fingerprint_pause(fingerprint)
    if paused is not None:
        return paused
    return _decision("PROCEED", "COMPLETE", "Upstream feed healthy")


def claimable_work_items(
    ledger: dict[str, Any], now: Any = None
) -> list[dict[str, Any]]:
    """Return complete unexpired stage2_work_items Stage 2 may claim."""
    raw = ledger.get("stage2_work_items")
    if not isinstance(raw, list):
        return []
    claimed: list[dict[str, Any]] = []
    for entry in raw:
        if isinstance(entry, dict) and work_item_is_usable(entry, now):
            claimed.append(entry)
    return claimed
