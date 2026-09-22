#!/usr/bin/env python3
"""Stage 2 intake feed: minimal work items from ledger + live identity.

Emits minimal WIs (source key, SHAs, paths, reason). Heavy fields are Stage 2
outputs. Exit 2 with named reason when the feed is empty AND salvage-eligible
stock remains (including expired-packet WAITING_HUMAN BOT non-REVIEW_SECURITY).

Does not CAS-write. Stage 2 never merges.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
import pr_lifecycle_ledger_cas as cas
import pr_lifecycle_pipeline_health as health
from pr_lifecycle_config import validate_config
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_EMPTY_WITH_STOCK = 2
DEFAULT_EXPIRY_DAYS = 7


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _parse_utc(value: object) -> datetime | None:
    """Parse a Z-suffixed timestamp as UTC, or return None if invalid."""
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def _expiry_days(config: dict[str, Any]) -> int:
    """Return the configured positive packet expiry or the default."""
    lifecycle = config.get("lifecycle") or {}
    raw = lifecycle.get("packet_expiry_close_days", DEFAULT_EXPIRY_DAYS)
    if not isinstance(raw, int) or raw < 1:
        return DEFAULT_EXPIRY_DAYS
    return raw


def is_expired_packet_salvage(
    item: dict[str, Any], *, expiry_days: int, now: datetime
) -> bool:
    """WAITING_HUMAN BOT non-REVIEW_SECURITY past expiry → salvage-eligible."""
    if item.get("lifecycle_state") != "WAITING_HUMAN":
        return False
    if item.get("author_type") != "BOT":
        return False
    if item.get("guardrail_outcome") == "REVIEW_SECURITY":
        return False
    stamp = _parse_utc(item.get("updated_at_utc"))
    if stamp is None:
        return False
    age = (now - stamp).total_seconds() / 86400.0
    return age > expiry_days


def minimal_work_item(item: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Minimal WI schema: source key, SHAs, paths, reason."""
    return {
        "source_key": item.get("key"),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "base_sha": item.get("base_sha"),
        "head_sha": item.get("head_sha"),
        "paths": list(item.get("changed_paths") or item.get("paths") or []),
        "reason": reason,
        "author_type": item.get("author_type"),
        "guardrail_outcome": item.get("guardrail_outcome"),
        "lifecycle_state": item.get("lifecycle_state"),
        "next_action": item.get("next_action"),
    }


def _reason_for_item(
    item: dict[str, Any], *, expiry: int, clock: datetime
) -> str | None:
    if health.is_salvage_eligible(item):
        return "SALVAGE_ELIGIBLE"
    if is_expired_packet_salvage(item, expiry_days=expiry, now=clock):
        return "EXPIRED_PACKET_OR_CLOSE_STALE"
    return None


def _queued_stage2_work_items(
    ledger: dict[str, Any], clock: datetime
) -> tuple[list[dict[str, Any]], set[str]]:
    """Complete, unexpired stage2_work_items re-enter the feed ahead of new WIs."""
    work_items: list[dict[str, Any]] = []
    source_keys: set[str] = set()
    for wi in ledger.get("stage2_work_items") or []:
        if not isinstance(wi, dict) or not health.work_item_is_usable(wi, clock):
            continue
        source_key = str(wi.get("source_item_key") or "")
        item = dict(wi)
        item["source_key"] = source_key or wi.get("work_item_id")
        item["reason"] = "QUEUED_STAGE2_WORK_ITEM"
        work_items.append(item)
        if source_key:
            source_keys.add(source_key)
    return work_items, source_keys


def _collect_work_items(
    ledger: dict[str, Any], *, expiry: int, clock: datetime, limit: int | None
) -> list[dict[str, Any]]:
    """Queued stage2_work_items first, then unique salvage items, in order."""
    work_items, seen = _queued_stage2_work_items(ledger, clock)
    for item in ledger.get("items") or []:
        if limit is not None and len(work_items) >= limit:
            break
        wi = _item_work_entry(item, seen, expiry=expiry, clock=clock)
        if wi is not None:
            work_items.append(wi)
    if limit is not None:
        return work_items[:limit]
    return work_items


def _item_work_entry(
    item: Any, seen: set[str], *, expiry: int, clock: datetime
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    key = str(item.get("key") or "")
    reason = _reason_for_item(item, expiry=expiry, clock=clock)
    if not key or key in seen or reason is None:
        return None
    seen.add(key)
    return minimal_work_item(item, reason=reason)


def _expired_only_stock(ledger: dict[str, Any], *, expiry: int, clock: datetime) -> int:
    """Count expired packets not already considered salvage-eligible."""
    return sum(
        1
        for item in ledger.get("items") or []
        if isinstance(item, dict)
        and is_expired_packet_salvage(item, expiry_days=expiry, now=clock)
        and not health.is_salvage_eligible(item)
    )


def build_feed(
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    now: datetime | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build the Stage 2 intake feed and its empty-stock diagnostic."""
    clock = now or _utc_now()
    expiry = _expiry_days(config)
    report = health.summarize(ledger, now=clock)
    work_items = _collect_work_items(ledger, expiry=expiry, clock=clock, limit=limit)
    eligible_stock = report.salvage_eligible_count + _expired_only_stock(
        ledger, expiry=expiry, clock=clock
    )
    return {
        "generated_at_utc": clock.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledger_revision": ledger.get("ledger_revision"),
        "work_item_count": len(work_items),
        "salvage_eligible_count": report.salvage_eligible_count,
        "eligible_stock_count": eligible_stock,
        "work_items": work_items,
        "empty_with_stock": len(work_items) == 0 and eligible_stock > 0,
        "reason": (
            "EMPTY_FEED_WITH_ELIGIBLE_STOCK"
            if len(work_items) == 0 and eligible_stock > 0
            else ("EMPTY_FEED" if not work_items else "FEED_OK")
        ),
    }


def run_feed(*, limit: int | None, json_out: bool) -> int:
    """Fetch the runtime ledger, emit its feed, and return a feed exit code."""
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-feed-") as tmp:
        out = Path(tmp) / "ledger.yaml"
        fetch = cas.run_preflight(out)
        ledger = load_yaml(Path(fetch["ledger_path"]))
        payload = build_feed(ledger, config, limit=limit)
    if json_out:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"reason={payload['reason']}")
        print(f"work_item_count={payload['work_item_count']}")
        print(f"eligible_stock_count={payload['eligible_stock_count']}")
        for item in payload["work_items"]:
            paths = item.get("paths") or item.get("allowed_paths") or []
            print(
                f"wi source_key={item.get('source_key')} "
                f"reason={item.get('reason')} paths={len(paths)}"
            )
    if payload["empty_with_stock"]:
        return EXIT_EMPTY_WITH_STOCK
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """Build the Stage 2 feed command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the feed CLI, mapping expected failures to ``EXIT_ERROR``."""
    args = build_parser().parse_args(argv)
    try:
        return run_feed(limit=args.limit, json_out=args.json)
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_FEED_ERROR: {type(exc).__name__}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())


# Alias used by pr_lifecycle_run
build_feed = build_feed

# Public aliases
is_expired_packet_salvage = is_expired_packet_salvage
minimal_work_item = minimal_work_item
build_feed = build_feed
