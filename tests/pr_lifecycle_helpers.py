"""Shared fixtures and helpers for the pr_lifecycle test modules."""

from __future__ import annotations

import copy
import subprocess
import sys
import types
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


def make_health_report(**overrides: object) -> types.SimpleNamespace:
    values: dict[str, object] = {
        "salvage_eligible_count": 0,
        "stage2_work_item_count": 0,
        "starvation": False,
        "reason": "ok",
    }
    values.update(overrides)
    return types.SimpleNamespace(**values)


_RUN_STUB_NAMES = (
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_pipeline_health",
    "pr_lifecycle_config",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
    "pr_lifecycle_reconcile",
    "pr_lifecycle_feed",
)


def _signal_value_stub(mapping: Any, key: str) -> Any:
    if not mapping:
        return None
    if key in mapping:
        return mapping[key]
    return mapping.get(str(key or "").split("@", 1)[0])


def _health_stub_attrs() -> dict[str, Any]:
    return {
        "summarize": lambda *_a, **_k: make_health_report(),
        "signal_value": _signal_value_stub,
        "is_never_touch_key": lambda *_a, **_k: False,
        "list_reselect_candidates": lambda *_a, **_k: [],
        "MECHANICAL_RESELECT_NA": (
            "Recover unique source only on a new focused draft."
        ),
        "ReselectSignals": lambda **kw: types.SimpleNamespace(
            **{
                "live_mergeable_by_key": None,
                "titles_by_key": None,
                "unique_paths_by_key": None,
                **kw,
            }
        ),
        "source_pr_prefix": lambda key: str(key or "").split("@", 1)[0],
        "non_journal_paths": lambda paths: list(paths or []),
        "SALVAGE_OUTCOMES": frozenset(
            {"HOLD_CONTRACT", "HOLD_EVIDENCE", "NOT_RUN"}
        ),
    }


def _install_run_stubs() -> dict[str, Any]:
    """Install stub modules; return the previous sys.modules entries."""
    saved = {name: sys.modules.get(name) for name in _RUN_STUB_NAMES}
    for name in _RUN_STUB_NAMES:
        sys.modules[name] = types.ModuleType(name)
    for attr, value in _health_stub_attrs().items():
        setattr(sys.modules["pr_lifecycle_pipeline_health"], attr, value)
    sys.modules["pr_lifecycle_support"].ROOT = ROOT
    sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
    sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
    sys.modules["pr_lifecycle_reconcile"].collect_actions = lambda *_a, **_k: []
    sys.modules["pr_lifecycle_feed"].build_feed = lambda *_a, **_k: {
        "empty_with_stock": False,
        "reason": "FEED_OK",
        "work_item_count": 0,
        "eligible_stock_count": 0,
        "work_items": [],
    }
    return saved


def _restore_run_stubs(saved: dict[str, Any]) -> None:
    for name, previous in saved.items():
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


def import_lifecycle_run() -> Any:
    """Import pr_lifecycle_run with its remote/health deps stubbed.

    Stubs live in sys.modules only for the duration of the import so discovery
    does not leak them into the rest of the suite; run.health and friends stay
    patchable via mock.patch.object afterwards.
    saved = _install_run_stubs()
    try:
        import pr_lifecycle_run as module
    finally:
        _restore_run_stubs(saved)
    import pr_lifecycle_run as module

    _restore_run_stubs(saved)
    return module
