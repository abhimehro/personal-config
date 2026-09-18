#!/usr/bin/env python3
"""Verify Stage 1→2 handoff via sample WI emission and Stage 2 claim path."""

# Read-only against a fetched runtime ledger by default. With --inject-sample,
# writes a temporary copy that appends one complete stage2_work_item so health
# and claim logic can be proven without CAS-writing the live automation branch.
#
#   python3 scripts/pr_lifecycle_feed_cascade_verify.py \
#     --ledger /tmp/pr-lifecycle-ledger.yaml
#
#   python3 scripts/pr_lifecycle_feed_cascade_verify.py \
#     --ledger /tmp/pr-lifecycle-ledger.yaml --inject-sample

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
from pr_lifecycle_feed_cascade import (
    CascadeDecision,
    FeedFingerprint,
    claimable_work_items,
    grade_stage1_feed,
    stage2_cascade_decision,
    stage3_cascade_decision,
    unhealthy_stage2_feed,
)
from pr_lifecycle_pipeline_health import (
    PipelineHealth,
    _load_runtime_ledger,
    summarize,
)
from pr_lifecycle_yaml import load_yaml

_SAMPLE_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@dataclass(frozen=True)
class DecisionSnapshot:
    """Bundled verify outputs so printers stay under CodeScene arg limits."""

    health: PipelineHealth
    fingerprint: FeedFingerprint
    stage2_decision: CascadeDecision
    stage3_decision: CascadeDecision
    claimable: list[dict[str, Any]]


def _sample_expiry(now: datetime) -> str:
    """UTC expiry two days ahead, always ending in Z."""
    expiry = now + timedelta(days=2)
    return expiry.isoformat().replace("+00:00", "Z")


def _sample_identity(sha: str) -> dict[str, Any]:
    """Identity fields for the synthetic Stage 2 work item."""
    return {
        "work_item_id": "s2-sample-feed-cascade",
        "source_item_key": f"abhimehro/personal-config#1@{sha}",
        "repository": "abhimehro/personal-config",
        "pr": 1,
        "base_sha": sha,
        "head_sha": sha,
    }


def _sample_repair_fields() -> dict[str, Any]:
    """Repair / acceptance fields for the synthetic Stage 2 work item."""
    return {
        "allowed_paths": ["scripts/pr_lifecycle_feed_cascade.py"],
        "prohibited_paths": [".github/workflows/"],
        "repair_description": "Sample complete WI for feed-cascade verify.",
        "required_test_command": (
            "python3 -m unittest tests.test_pr_lifecycle_feed_cascade"
        ),
        "expected_test_result": "ok",
        "acceptance_criteria": ["Health starvation=false after inject."],
        "provenance_urls": [
            "https://github.com/abhimehro/personal-config/pull/1",
        ],
    }


def _sample_work_item(now: datetime) -> dict[str, Any]:
    """Build one schema-complete synthetic Stage 2 work item."""
    item = _sample_identity(_SAMPLE_SHA)
    item.update(_sample_repair_fields())
    item.update(
        {
            "expiry_utc": _sample_expiry(now),
            "attempt_count": 0,
            "current_owner": "stage2",
            "creation_event_id": "evt-sample-feed-cascade",
            "history": [],
        }
    )
    return item


def _print_report(label: str, payload: dict[str, Any]) -> None:
    print(f"== {label} ==")
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _health_payload(health: PipelineHealth) -> dict[str, Any]:
    return {
        "ledger_revision": health.ledger_revision,
        "stage2_work_item_count": health.stage2_work_item_count,
        "salvage_eligible_count": health.salvage_eligible_count,
        "starvation": health.starvation,
        "reason": health.reason,
    }


def _fingerprint_payload(fingerprint: FeedFingerprint) -> dict[str, Any]:
    return {
        "stage2_queued_count": fingerprint.stage2_queued_count,
        "salvage_eligible_count": fingerprint.salvage_eligible_count,
        "throughput_grade": fingerprint.throughput_grade,
    }


def _decision_payload(decision: CascadeDecision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "label": decision.label,
        "reason": decision.reason,
    }


def _claimable_payload(claimable: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(claimable),
        "ids": [work_item["work_item_id"] for work_item in claimable],
    }


def _print_decision_reports(snapshot: DecisionSnapshot) -> None:
    """Emit JSON sections for health, fingerprint, cascade, and claimable."""
    _print_report("health", _health_payload(snapshot.health))
    _print_report("fingerprint", _fingerprint_payload(snapshot.fingerprint))
    _print_report("stage2", _decision_payload(snapshot.stage2_decision))
    _print_report("stage3", _decision_payload(snapshot.stage3_decision))
    _print_report("claimable", _claimable_payload(snapshot.claimable))


def _stage_decisions(
    health: PipelineHealth,
    fingerprint: FeedFingerprint,
    claimable: list[dict[str, Any]],
) -> tuple[CascadeDecision, CascadeDecision]:
    """Run Stage 2 then Stage 3 cascade decisions for one snapshot."""
    stage2_decision = stage2_cascade_decision(
        health,
        fingerprint,
        usable_work_item_count=len(claimable),
        stage2_owned_materializable=health.stage2_owned_item_count,
    )
    stage3_decision = stage3_cascade_decision(
        health,
        fingerprint,
        stage2_feed_fail_same_utc_day=unhealthy_stage2_feed(stage2_decision),
    )
    return stage2_decision, stage3_decision


def _build_snapshot(ledger: dict[str, Any], *, now: datetime) -> DecisionSnapshot:
    """Compute health, fingerprint, and Stage 2/3 decisions for one ledger."""
    health = summarize(ledger, now=now)
    claimable = claimable_work_items(ledger, now=now)
    fingerprint = grade_stage1_feed(
        stage2_queued_count=health.stage2_work_item_count,
        salvage_eligible_count=health.salvage_eligible_count,
    )
    stage2_decision, stage3_decision = _stage_decisions(health, fingerprint, claimable)
    return DecisionSnapshot(
        health=health,
        fingerprint=fingerprint,
        stage2_decision=stage2_decision,
        stage3_decision=stage3_decision,
        claimable=claimable,
    )


def _verify_exit_code(snapshot: DecisionSnapshot) -> int:
    """Map a snapshot to the verify process exit code.

    Return 0 for a claimed proceed or non-starved stop, 1 for a claimless
    proceed, and 2 for a starved stop.
    """
    # CLAIM (usable WI or Stage-2-owned materializable) beats observational
    # starvation so verify does not idle-fail a heal-forward run.
    if snapshot.stage2_decision.action == "PROCEED":
        owned = snapshot.health.stage2_owned_item_count
        if snapshot.claimable or owned > 0:
            return 0
        return 1
    if snapshot.health.starvation:
        return 2
    return 0


def verify_ledger(ledger: dict[str, Any], *, now: datetime) -> int:
    """Print cascade decisions and return the verify exit code."""
    snapshot = _build_snapshot(ledger, now=now)
    _print_decision_reports(snapshot)
    return _verify_exit_code(snapshot)


def _load_validated_ledger(path: Path) -> dict[str, Any] | None:
    """Load YAML and apply the same runtime-ledger gates as the health CLI."""
    ledger, status = _load_runtime_ledger(path)
    if ledger is None:
        print(
            "PR_LIFECYCLE_FEED_VERIFY_ERROR: "
            f"ledger validation failed for {path} (exit {status})",
            file=sys.stderr,
        )
        return None
    return ledger


def _append_sample(ledger: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy ledger and append one Stage 2 work item."""
    mutated = copy.deepcopy(ledger)
    items = mutated.get("stage2_work_items")
    if not isinstance(items, list):
        items = []
        mutated["stage2_work_items"] = items
    items.append(sample)
    return mutated


def _write_injected_ledger(ledger: dict[str, Any], sample: dict[str, Any]) -> Path:
    """Write mutated ledger to a temp file; caller owns deletion."""
    mutated = _append_sample(ledger, sample)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write("# sample inject (json-as-yaml subset)\n")
        json.dump(mutated, handle, default=str)
        handle.flush()
        return Path(handle.name)


def _reload_injected(temp_path: Path) -> dict[str, Any] | None:
    """Reload an injected temp ledger; delete the file afterward."""
    try:
        reloaded = load_yaml(temp_path)
    except (OSError, ValueError, KeyError) as exc:
        print(
            f"PR_LIFECYCLE_FEED_VERIFY_ERROR: inject reload: {exc}",
            file=sys.stderr,
        )
        return None
    finally:
        temp_path.unlink(missing_ok=True)
    if reloaded is None or not isinstance(reloaded, dict):
        print(
            "PR_LIFECYCLE_FEED_VERIFY_ERROR: inject reload empty",
            file=sys.stderr,
        )
        return None
    return reloaded


def _print_missing_ledger(path: Path) -> None:
    print(
        "PR_LIFECYCLE_FEED_VERIFY_ERROR: "
        f"{path}: file not found. Fetch first:\n"
        '  gh api "repos/abhimehro/personal-config/contents/'
        'pr-lifecycle-ledger.yaml?ref=automation/pr-lifecycle-ledger" '
        '-H "Accept: application/vnd.github.raw+json" '
        "> /tmp/pr-lifecycle-ledger.yaml",
        file=sys.stderr,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        required=True,
        help="Fetched runtime ledger path (not the main-branch pointer)",
    )
    parser.add_argument(
        "--inject-sample",
        action="store_true",
        help="Temp-copy + append one complete WI; prove claim path",
    )
    return parser.parse_args(argv)


def _maybe_inject(
    ledger: dict[str, Any], *, inject: bool, now: datetime
) -> dict[str, Any] | None:
    """Optionally append a sample WI via temp file; return ledger to verify."""
    if not inject:
        return ledger
    temp_path = _write_injected_ledger(ledger, _sample_work_item(now))
    print(f"injected_sample_path={temp_path}")
    # Inject path skips full schema re-validate: sample WI is synthetic and
    # health summarize()/claimable_work_items already gate usability.
    return _reload_injected(temp_path)


def main() -> int:
    """CLI entry: validate ledger, optional inject, print cascade status."""
    args = _parse_args()
    if not args.ledger.is_file():
        _print_missing_ledger(args.ledger)
        return 1
    now = datetime.now(timezone.utc)
    ledger = _load_validated_ledger(args.ledger)
    if ledger is None:
        return 1
    ledger = _maybe_inject(ledger, inject=args.inject_sample, now=now)
    if ledger is None:
        return 1
    return verify_ledger(ledger, now=now)


if __name__ == "__main__":
    sys.exit(main())
