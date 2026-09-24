"""Shared fixtures and helpers for the pr_lifecycle test modules."""

from __future__ import annotations

import copy
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import yaml  # noqa: E402

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
HEALTH_SCRIPT = SCRIPTS / "pr_lifecycle_pipeline_health.py"
EXAMPLE_LEDGER = ROOT / "tasks/pr-lifecycle-ledger.example.yaml"


def make_item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "key": "abhimehro/demo#1@abc",
        "author_type": "BOT",
        "lifecycle_state": "STAGE3_RECONCILIATION",
        "current_owner": "stage3",
        "guardrail_outcome": "HOLD_CONTRACT",
        "sensitive_paths": ["generated_output"],
        "next_action": (
            "Recover unique source only on a new focused draft that "
            "excludes .jules/journals/"
        ),
    }
    base.update(overrides)
    return base


def make_work_item(**overrides: object) -> dict[str, object]:
    sha = "0123456789abcdef0123456789abcdef01234567"
    base: dict[str, object] = {
        "work_item_id": "s2-20260830-demo",
        "source_item_key": f"abhimehro/demo#1@{sha}",
        "repository": "abhimehro/demo",
        "pr": 1,
        "base_sha": sha,
        "head_sha": sha,
        "allowed_paths": ["src/demo.py"],
        "prohibited_paths": [],
        "repair_description": "Repair the demo path.",
        "required_test_command": "python3 -m unittest",
        "expected_test_result": "ok",
        "acceptance_criteria": ["Allowed path changes only."],
        "provenance_urls": ["https://github.com/abhimehro/demo/pull/1"],
        "expiry_utc": "2026-08-31T12:00:00Z",
        "attempt_count": 0,
        "current_owner": "stage2",
        "creation_event_id": "evt-20260830-demo",
        "history": [],
    }
    base.update(overrides)
    return base


def make_ledger(
    items: list[dict[str, object]],
    work_items: list[dict[str, object]],
    revision: int = 1,
) -> dict[str, object]:
    return {
        "ledger_revision": revision,
        "items": items,
        "stage2_work_items": work_items,
    }


def schema_valid_starved_ledger() -> dict[str, Any]:
    ledger = copy.deepcopy(yaml.safe_load(EXAMPLE_LEDGER.read_text(encoding="utf-8")))
    keeper = ledger["items"][0]
    keeper["lifecycle_state"] = "STAGE3_RECONCILIATION"
    keeper["current_owner"] = "stage3"
    keeper["next_owner"] = "stage3"
    keeper["next_action"] = (
        "Recover unique source only on a new focused draft that "
        "excludes .jules/journals/"
    )
    ledger["stage2_work_items"] = []
    events = []
    for event in ledger["events"]:
        if event["event_id"] == "evt-2026-stage2-ack-001":
            continue
        if event["event_id"] == "evt-2026-stage1-stage2-001":
            event = dict(event)
            event["to_owner"] = "stage3"
            event["to_state"] = "STAGE3_RECONCILIATION"
            event["next_owner"] = "stage3"
            event["reason"] = "Stage 1 overflowed salvage-eligible remainder."
        events.append(event)
    ledger["events"] = events
    return ledger


def run_health_cli(*cli_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HEALTH_SCRIPT), *cli_args],
        check=False,
        capture_output=True,
        text=True,
    )
