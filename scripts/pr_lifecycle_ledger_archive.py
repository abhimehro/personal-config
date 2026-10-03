#!/usr/bin/env python3
"""Archive TERMINAL ledger items older than 30 days.

Dry-run by default. ``--apply`` rewrites the active ledger (CAS) and writes
``archive/YYYY-MM.yaml`` siblings on the data branch layout. Validator accepts
archives; active ledger target size < 1MB.

Does not close or merge PRs.
"""

from __future__ import annotations

import argparse
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
import pr_lifecycle_ledger_cas as cas
from pr_lifecycle_config import validate_config
from pr_lifecycle_persist import dump_ledger, strip_in_memory_item_fields
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

ACTIVE_LEDGER_MAX_BYTES = 1_000_000
DEFAULT_ARCHIVE_AFTER_DAYS = 30


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


def select_archive_items(
    ledger: dict[str, Any],
    *,
    after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Select terminal items updated on or before the age cutoff."""
    clock = now or _utc_now()
    cutoff = clock - timedelta(days=after_days)
    selected: list[dict[str, Any]] = []
    for item in ledger.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("lifecycle_state") != "TERMINAL":
            continue
        stamp = _parse_utc(item.get("updated_at_utc"))
        if stamp is None:
            continue
        if stamp <= cutoff:
            selected.append(item)
    return selected


def partition_by_month(
    items: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group timestamped items by their UTC update month."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        stamp = _parse_utc(item.get("updated_at_utc"))
        if stamp is None:
            continue
        key = stamp.strftime("%Y-%m")
        buckets.setdefault(key, []).append(item)
    return buckets


def build_archive_document(
    month: str,
    items: list[dict[str, Any]],
    *,
    source_revision: Any,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a monthly archive document for the supplied ledger items."""
    return {
        "archive_format_version": 1,
        "month": month,
        "archived_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_ledger_revision": source_revision,
        "item_count": len(items),
        "items": items,
        "events": events or [],
    }


def plan_archive(
    ledger: dict[str, Any],
    *,
    after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Summarize archive candidates and the projected active-ledger size."""
    selected = select_archive_items(ledger, after_days=after_days, now=now)
    buckets = partition_by_month(selected)
    remaining = [
        item
        for item in ledger.get("items") or []
        if not isinstance(item, dict)
        or item.get("key") not in {i.get("key") for i in selected}
    ]
    preview = dict(ledger)
    preview["items"] = remaining
    strip_in_memory_item_fields(preview)
    preview_text = dump_ledger(preview)
    return {
        "dry_run": True,
        "archive_after_days": after_days,
        "selected_count": len(selected),
        "remaining_count": len(remaining),
        "active_ledger_bytes_preview": len(preview_text.encode("utf-8")),
        "active_ledger_max_bytes": ACTIVE_LEDGER_MAX_BYTES,
        "months": {
            month: {
                "count": len(items),
                "path": f"archive/{month}.yaml",
            }
            for month, items in sorted(buckets.items())
        },
        "selected_keys": [str(i.get("key")) for i in selected],
    }


def _drop_events_for_items(
    ledger: dict[str, Any], archived_keys: set[Any]
) -> list[dict[str, Any]]:
    """Remove events for archived item keys; return the dropped events."""
    # Dropped events move into the month archive docs.
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for event in ledger.get("events") or []:
        if isinstance(event, dict) and event.get("item_key") in archived_keys:
            dropped.append(event)
        else:
            kept.append(event)
    ledger["events"] = kept
    return dropped


def _month_events(
    dropped: list[dict[str, Any]], buckets: dict[str, list[dict[str, Any]]]
) -> dict[str, list[dict[str, Any]]]:
    month_by_key = {
        item.get("key"): month for month, items in buckets.items() for item in items
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in dropped:
        month = month_by_key.get(event.get("item_key"))
        if month is not None:
            grouped.setdefault(month, []).append(event)
    return grouped


def _write_month_archives(
    buckets: dict[str, list[dict[str, Any]]],
    out_dir: Path,
    ledger: dict[str, Any],
    dropped_events: list[dict[str, Any]],
) -> dict[str, str]:
    """Write one YAML archive per month and return the written paths."""
    written: dict[str, str] = {}
    events_by_month = _month_events(dropped_events, buckets)
    for month, items in sorted(buckets.items()):
        doc = build_archive_document(
            month,
            items,
            source_revision=ledger.get("ledger_revision"),
            events=events_by_month.get(month),
        )
        path = out_dir / "archive" / f"{month}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Reuse dump_ledger shape for YAML stability.
        path.write_text(dump_ledger(doc), encoding="utf-8")
        written[month] = str(path)
    return written


def apply_archive(
    ledger: dict[str, Any],
    *,
    after_days: int,
    out_dir: Path,
) -> dict[str, Any]:
    """Mutate the ledger to remove eligible items and events, then write outputs."""
    selected = select_archive_items(ledger, after_days=after_days)
    buckets = partition_by_month(selected)
    selected_keys = {item.get("key") for item in selected}
    ledger["items"] = [
        item
        for item in ledger.get("items") or []
        if not isinstance(item, dict) or item.get("key") not in selected_keys
    ]
    dropped_events = _drop_events_for_items(ledger, selected_keys)
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    strip_in_memory_item_fields(ledger)
    written = _write_month_archives(buckets, out_dir, ledger, dropped_events)

    active_text = dump_ledger(ledger)
    active_path = out_dir / "pr-lifecycle-ledger.yaml"
    active_path.write_text(active_text, encoding="utf-8")
    return {
        "active_path": str(active_path),
        "active_bytes": len(active_text.encode("utf-8")),
        "archives": written,
        "selected_count": len(selected),
        "remaining_count": len(ledger.get("items") or []),
    }


def run_archive(*, apply: bool, after_days: int, json_out: bool) -> int:
    """Emit an archive plan, or write archives and CAS-commit the active ledger."""
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-archive-") as tmp:
        out = Path(tmp) / "ledger.yaml"
        fetch = cas.run_preflight(out)
        ledger = load_yaml(Path(fetch["ledger_path"]))
        plan = plan_archive(ledger, after_days=after_days)
        plan["dry_run"] = not apply
        if not apply:
            _emit_plan(plan, json_out)
            return 0
        payload, result = _apply_payload(ledger, plan, tmp, after_days)
        _emit_apply(payload, result, json_out)
    return 0


def _emit_plan(plan: dict[str, Any], json_out: bool) -> None:
    """Print an archive plan as JSON or concise text."""
    if json_out:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    print(f"dry_run=true selected_count={plan['selected_count']}")
    print(f"active_ledger_bytes_preview={plan['active_ledger_bytes_preview']}")
    for month, meta in plan["months"].items():
        print(f"archive month={month} count={meta['count']} path={meta['path']}")


def _emit_apply(
    payload: dict[str, Any], result: dict[str, Any], json_out: bool
) -> None:
    """Print applied archive results as JSON or concise text."""
    if json_out:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"dry_run=false selected_count={result['selected_count']}")
    print(f"active_bytes={result['active_bytes']}")
    for commit in payload.get("archive_commits") or []:
        print(f"archive_commit={commit['path']} sha={commit['commit_sha'][:12]}")
    print(f"ledger_commit={payload['cas']['commit_sha'][:12]}")


def _cas_commit_path(
    runtime: dict[str, Any], path: str, content: str, message: str
) -> dict[str, Any]:
    """Fast-forward CAS commit of one file at an arbitrary branch path.

    Mirrors ``cas.cas_commit`` but targets ``path`` instead of the pointer's
    ``data_path`` — archive docs bypass the active-ledger schema validate.
    """
    branch = str(runtime["data_branch"])
    ensured = cas.ensure_data_ref(runtime)
    parent_sha = cas.object_sha(ensured["ref"])
    parent = cas.read_commit(parent_sha)
    blob_sha = cas.create_blob(content)
    new_tree = cas.create_tree(cas.tree_sha(parent), path, blob_sha)
    commit_sha = cas.create_commit(message, new_tree, parent_sha)
    try:
        cas.update_ref(branch, commit_sha, parent_sha)
    except cas.CasError as exc:
        if cas.is_stale_tip_error(exc):
            raise cas.CasError(cas.OPERATOR_CONFLICT, http_code=exc.http_code) from None
        raise
    return {"commit_sha": commit_sha, "path": path}


def _apply_payload(
    ledger: dict[str, Any], plan: dict[str, Any], tmp: str, after_days: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_archive(ledger, after_days=after_days, out_dir=Path(tmp))
    runtime = cas.pointer_runtime()
    # Commit each archive/YYYY-MM.yaml before the active-ledger rewrite so a
    # later failure leaves duplication (re-archivable), never silent loss.
    archive_commits: list[dict[str, Any]] = []
    for month, file_path in sorted(result["archives"].items()):
        rel = str(Path(file_path).relative_to(tmp))
        text = Path(file_path).read_text(encoding="utf-8")
        archive_commits.append(
            _cas_commit_path(
                runtime,
                rel,
                text,
                f"archive: {month} TERMINAL items (>{after_days}d)",
            )
        )
    cas_result = cas.run_commit(
        Path(result["active_path"]),
        "archive: move TERMINAL items older than "
        f"{after_days}d into archive/YYYY-MM.yaml",
        bump_revision=False,
    )
    payload = {
        **plan,
        "apply_result": result,
        "archive_commits": archive_commits,
        "cas": cas_result,
    }
    if result["active_bytes"] > ACTIVE_LEDGER_MAX_BYTES:
        payload["warning"] = "active ledger still exceeds 1MB after archive"
    return payload, result


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the ledger archive command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--after-days", type=_non_negative_int, default=DEFAULT_ARCHIVE_AFTER_DAYS
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the archive CLI, returning 1 for expected operational errors."""
    args = build_parser().parse_args(argv)
    try:
        return run_archive(
            apply=args.apply, after_days=args.after_days, json_out=args.json
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_ARCHIVE_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
