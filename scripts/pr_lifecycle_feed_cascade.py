#!/usr/bin/env python3
"""Heal-forward Stage 1→2→3 feed cascade decisions (no CAS / Dashboard I/O)."""

# Encodes Stage 1 fingerprints, Stage 2 HEAL_THEN_PROCEED on a starved feed,
# and Stage 3 heal-then-continue over already-fetched ledger summaries.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pr_lifecycle_pipeline_health import PipelineHealth, work_item_is_usable

ThroughputGrade = Literal["PASS", "FAIL"]
CascadeAction = Literal["PROCEED", "HEAL_THEN_PROCEED", "EMPTY_INTAKE"]


@dataclass(frozen=True)
class FeedFingerprint:
    """Stage 1 run-record feed fields consumed by Stage 2/3."""

    stage2_queued_count: int
    salvage_eligible_count: int
    throughput_grade: ThroughputGrade


@dataclass(frozen=True)
class CascadeDecision:
    """Downstream heal-or-proceed outcome."""

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


def unhealthy_stage2_feed(decision: CascadeDecision) -> bool:
    """True when Stage 2 is healing a starved or failed feed."""
    return decision.action == "HEAL_THEN_PROCEED" and decision.label in {
        "FEED_FAIL",
        "EMPTY_INTAKE_STARVATION",
    }


def _fingerprint_feed_fail(fingerprint: FeedFingerprint) -> CascadeDecision:
    """HEAL_THEN_PROCEED when Stage 1 queued nothing despite eligible stock."""
    return _decision(
        "HEAL_THEN_PROCEED",
        "FEED_FAIL",
        (
            "Stage 1 queued 0 while salvage-eligible > 0 "
            f"(queued={fingerprint.stage2_queued_count}, "
            f"eligible={fingerprint.salvage_eligible_count}); "
            "heal leftover Stage 1 feed then continue"
        ),
    )


def _stage2_feed_or_empty(
    fingerprint: FeedFingerprint | None,
) -> CascadeDecision:
    """Heal a starved fingerprint; else EMPTY_INTAKE."""
    # ASSUMES: heal only on starved feed, not every Stage 1 FAIL.
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


def _find_claimable_stage2_work(
    usable_work_item_count: int,
    stage2_owned_materializable: int,
) -> CascadeDecision | None:
    """Return CLAIM when usable or materializable Stage 2 work exists."""
    if usable_work_item_count > 0:
        return _decision(
            "PROCEED",
            "CLAIM",
            "Complete unexpired Stage 2 work item available",
        )
    if stage2_owned_materializable > 0:
        return _decision(
            "PROCEED",
            "CLAIM",
            "Stage-2-owned ledger item can materialize a work item",
        )
    return None


def stage2_cascade_decision(
    health: PipelineHealth,
    fingerprint: FeedFingerprint | None,
    *,
    usable_work_item_count: int,
    stage2_owned_materializable: int = 0,
) -> CascadeDecision:
    """Decide Stage 2 proceed, heal a broken feed, or empty-intake."""
    # SECURITY: claim leftover complete WIs before grading today's feed.
    claimed = _find_claimable_stage2_work(
        usable_work_item_count, stage2_owned_materializable
    )
    if claimed is not None:
        return claimed
    if health.starvation:
        return _decision(
            "HEAL_THEN_PROCEED", "EMPTY_INTAKE_STARVATION", health.reason
        )
    return _stage2_feed_or_empty(fingerprint)


def _stage3_fingerprint_heal(
    fingerprint: FeedFingerprint | None,
) -> CascadeDecision | None:
    """Heal when same-day Stage 1 fingerprint is missing or FAIL."""
    if fingerprint is None:
        return _decision(
            "HEAL_THEN_PROCEED",
            "UPSTREAM_HEAL",
            "Missing same-day Stage 1 feed fingerprint; heal then continue",
        )
    if fingerprint.throughput_grade == "FAIL":
        return _decision(
            "HEAL_THEN_PROCEED",
            "UPSTREAM_HEAL",
            "Stage 1 throughput_grade FAIL; heal leftover drain then continue",
        )
    return None


def stage3_cascade_decision(
    health: PipelineHealth,
    fingerprint: FeedFingerprint | None,
    *,
    stage2_feed_fail_same_utc_day: bool,
) -> CascadeDecision:
    """Decide whether Stage 3 completes now or heals upstream first."""
    if stage2_feed_fail_same_utc_day:
        return _decision(
            "HEAL_THEN_PROCEED",
            "UPSTREAM_HEAL",
            "Stage 2 recorded FEED_FAIL same UTC day; heal then continue",
        )
    if health.starvation:
        return _decision("HEAL_THEN_PROCEED", "UPSTREAM_HEAL", health.reason)
    healed = _stage3_fingerprint_heal(fingerprint)
    if healed is not None:
        return healed
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
