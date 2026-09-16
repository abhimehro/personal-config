#!/usr/bin/env python3
"""Verify Stage 1→2 handoff: sample WI emission + Stage 2 claim path.

Read-only against a fetched runtime ledger by default. With --inject-sample,
writes a temporary copy that appends one complete stage2_work_item so health
and claim logic can be proven without CAS-writing the live automation branch.

  python3 scripts/pr_lifecycle_feed_cascade_verify.py \\
    --ledger /tmp/pr-lifecycle-ledger.yaml

  python3 scripts/pr_lifecycle_feed_cascade_verify.py \\
    --ledger /tmp/pr-lifecycle-ledger.yaml --inject-sample
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
from pr_lifecycle_feed_cascade import (  # noqa: E402
    claimable_work_items,
    grade_stage1_feed,
    stage2_cascade_decision,
    stage3_cascade_decision,
)
from pr_lifecycle_pipeline_health import summarize  # noqa: E402
from pr_lifecycle_yaml import load_yaml  # noqa: E402


def _sample_work_item(now: datetime) -> dict[str, Any]:
    sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    expiry = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "work_item_id": "s2-sample-feed-cascade",
        "source_item_key": f"abhimehro/personal-config#1@{sha}",
        "repository": "abhimehro/personal-config",
        "pr": 1,
        "base_sha": sha,
        "head_sha": sha,
        "allowed_paths": ["scripts/pr_lifecycle_feed_cascade.py"],
        "prohibited_paths": [".github/workflows/"],
        "repair_description": "Sample complete WI for feed-cascade verify.",
        "required_test_command": "python3 -m unittest tests.test_pr_lifecycle_feed_cascade",
        "expected_test_result": "ok",
        "acceptance_criteria": ["Health starvation=false after inject."],
        "provenance_urls": [
            "https://github.com/abhimehro/personal-config/pull/1",
        ],
        "expiry_utc": expiry,
        "attempt_count": 0,
        "current_owner": "stage2",
        "creation_event_id": "evt-sample-feed-cascade",
        "history": [],
    }


def _print_report(label: str, payload: dict[str, Any]) -> None:
    print(f"== {label} ==")
    print(json.dumps(payload, indent=2, sort_keys=True))


def verify_ledger(ledger: dict[str, Any], *, now: datetime) -> int:
    health = summarize(ledger, now=now)
    claimable = claimable_work_items(ledger, now=now)
    fingerprint = grade_stage1_feed(
        stage2_queued_count=health.stage2_work_item_count,
        salvage_eligible_count=health.salvage_eligible_count,
    )
    s2 = stage2_cascade_decision(
        health,
        fingerprint,
        usable_work_item_count=len(claimable),
    )
    s3 = stage3_cascade_decision(
        health,
        fingerprint,
        stage2_feed_fail_same_utc_day=s2.action == "FEED_FAIL",
    )
    _print_report(
        "health",
        {
            "ledger_revision": health.ledger_revision,
            "stage2_work_item_count": health.stage2_work_item_count,
            "salvage_eligible_count": health.salvage_eligible_count,
            "starvation": health.starvation,
            "reason": health.reason,
        },
    )
    _print_report(
        "fingerprint",
        {
            "stage2_queued_count": fingerprint.stage2_queued_count,
            "salvage_eligible_count": fingerprint.salvage_eligible_count,
            "throughput_grade": fingerprint.throughput_grade,
        },
    )
    _print_report(
        "stage2",
        {"action": s2.action, "label": s2.label, "reason": s2.reason},
    )
    _print_report(
        "stage3",
        {"action": s3.action, "label": s3.label, "reason": s3.reason},
    )
    _print_report(
        "claimable",
        {"count": len(claimable), "ids": [w["work_item_id"] for w in claimable]},
    )
    if health.starvation:
        return 2
    if s2.action == "PROCEED" and len(claimable) < 1:
        return 1
    return 0


def main() -> int:
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
    args = parser.parse_args()
    if not args.ledger.is_file():
        print(
            "PR_LIFECYCLE_FEED_VERIFY_ERROR: "
            f"{args.ledger}: file not found. Fetch first:\n"
            '  gh api "repos/abhimehro/personal-config/contents/'
            'pr-lifecycle-ledger.yaml?ref=automation/pr-lifecycle-ledger" '
            '-H "Accept: application/vnd.github.raw+json" '
            "> /tmp/pr-lifecycle-ledger.yaml",
            file=sys.stderr,
        )
        return 1
    now = datetime.now(timezone.utc)
    ledger = load_yaml(args.ledger)
    if args.inject_sample:
        mutated = copy.deepcopy(ledger)
        items = mutated.get("stage2_work_items")
        if not isinstance(items, list):
            items = []
            mutated["stage2_work_items"] = items
        items.append(_sample_work_item(now))
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            encoding="utf-8",
        ) as handle:
            # Keep verify self-contained: dump via json for stable structure.
            handle.write("# sample inject (json-as-yaml subset)\n")
            json.dump(mutated, handle)
            temp_path = Path(handle.name)
        print(f"injected_sample_path={temp_path}")
        # Re-load through yaml loader for parity with health CLI.
        ledger = load_yaml(temp_path)
    return verify_ledger(ledger, now=now)


if __name__ == "__main__":
    sys.exit(main())
