"""Shared fixtures and helpers for the pr_lifecycle test modules."""

from __future__ import annotations

import copy
import json
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

import yaml

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
    """Build a complete Stage 2 work item with test overrides."""
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
    """Build a minimal runtime ledger from test records."""
    return {
        "ledger_revision": revision,
        "items": items,
        "stage2_work_items": work_items,
    }


def make_queryable_item(**overrides: Any) -> dict[str, Any]:
    """Ledger item plausible enough to consume a live query slot."""
    defaults: dict[str, Any] = {
        "base_sha": "b" * 40,
        "head_sha": "c" * 40,
        "changed_paths": ["src/demo.py"],
    }
    defaults.update(overrides)
    return make_item(**defaults)


def make_gh_proc(
    stdout_dict: dict[str, Any] | str, returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    """Build a gh result from a JSON object or raw stdout and an exit code."""
    stdout = (
        json.dumps(stdout_dict) if isinstance(stdout_dict, dict) else str(stdout_dict)
    )
    return subprocess.CompletedProcess(
        args=["gh", "pr", "view"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class StubRunnerExhausted(BaseException):
    """The stub gh runner was called more times than scripted.

    BaseException subclass: it must escape the producer's ``except Exception``
    guards so an under-scripted test fails loudly instead of degrading into a
    misleading PARTIAL/DEGRADED result.
    """


def stub_gh_runner(
    payload: dict[str, Any] | str | None = None,
    *,
    results: list[Any] | None = None,
    base_sha: str = "b" * 40,
) -> Any:
    """Runner answering `gh pr view` with payload/queued results and `gh api`.

    The producer issues two calls per candidate: `gh pr view --json` for the
    bulk fields and `gh api ... --jq .base.sha` for the live base anchor. This
    stub returns base_sha for every api call and consumes `results` (or repeats
    `payload`) for pr-view calls, raising StubRunnerExhausted once results run
    out — a loud test failure, not a swallowed producer-level degradation.
    """
    queue = list(results or [])

    def runner(cmd: list[str], timeout: float | None = None) -> Any:
        if "api" in cmd:
            return make_gh_proc(base_sha)
        if queue:
            result = queue.pop(0)
            if isinstance(result, BaseException):
                raise result
            return result
        if payload is None:
            raise StubRunnerExhausted("gh pr view called more times than expected")
        return make_gh_proc(payload)

    return runner


def schema_valid_starved_ledger() -> dict[str, Any]:
    """Create a valid ledger with eligible work and no Stage 2 intake."""
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
    """Run the health CLI and capture its output and exit status."""
    return subprocess.run(
        [sys.executable, str(HEALTH_SCRIPT), *cli_args],
        check=False,
        capture_output=True,
        text=True,
    )


def make_health_report(**overrides: object) -> types.SimpleNamespace:
    """Build a health report stub with overridable fields."""
    values: dict[str, object] = {
        "salvage_eligible_count": 0,
        "stage2_work_item_count": 0,
        "reselect_candidate_count": 0,
        "starvation": False,
        "reason": "ok",
    }
    values.update(overrides)
    return types.SimpleNamespace(**values)


# pr_lifecycle_stage_plan is deliberately absent: run imports it inside the
# stub window, so it binds the same stub dep objects run does — keeping
# mock.patch.object(run.health/feed_mod/reconcile_mod, ...) effective inside
# the planner. Do NOT eagerly import it before the stubs (it would bind real
# modules and bypass those patches) and do NOT pop it on restore (a second
# import would create a divergent module instance for patch targets).
_RUN_STUB_NAMES = (
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_pipeline_health",
    "pr_lifecycle_config",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
    "pr_lifecycle_reconcile",
    "pr_lifecycle_feed",
)


def _health_stub_attrs(real_health: Any) -> dict[str, Any]:
    """Provide health module attributes required by runner tests."""
    return {
        "summarize": lambda *_a, **_k: make_health_report(),
        "signal_value": real_health.signal_value,
        "is_never_touch_key": real_health.is_never_touch_key,
        "list_reselect_candidates": lambda *_a, **_k: [],
        "MECHANICAL_RESELECT_NA": real_health.MECHANICAL_RESELECT_NA,
        "ReselectSignals": real_health.ReselectSignals,
        "source_pr_prefix": real_health.source_pr_prefix,
        "non_journal_paths": real_health.non_journal_paths,
        "SALVAGE_OUTCOMES": real_health.SALVAGE_OUTCOMES,
        "NON_SALVAGE_OUTCOMES": real_health.NON_SALVAGE_OUTCOMES,
        "STAGE2_OWNED_STATES": real_health.STAGE2_OWNED_STATES,
        "existing_wi_prefixes": real_health.existing_wi_prefixes,
    }


def _install_run_stubs() -> dict[str, Any]:
    """Install stub modules; return the previous sys.modules entries."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import pr_lifecycle_pipeline_health as real_health
    import pr_lifecycle_reselect_signals  # noqa: F401

    attrs = _health_stub_attrs(real_health)
    saved = {name: sys.modules.get(name) for name in _RUN_STUB_NAMES}
    for name in _RUN_STUB_NAMES:
        sys.modules[name] = types.ModuleType(name)
    for attr, value in attrs.items():
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
    """Restore modules replaced during the runner import."""
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
    """
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    saved = _install_run_stubs()
    try:
        import pr_lifecycle_run as module
    finally:
        _restore_run_stubs(saved)
    return module


# --- unblock fixtures --------------------------------------------------------
# Live below so the pr_lifecycle_unblock import binds after the SCRIPTS path
# insert, matching the layout of every other helper block in this module.

from unittest import mock

import pr_lifecycle_unblock as unblock

UNBLOCK_NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
UNBLOCK_CONFIG = yaml.safe_load(
    (ROOT / "tasks/pr-review-agent.config.yaml").read_text()
)
UNBLOCK_REPO = UNBLOCK_CONFIG["repos"][0]
UNBLOCK_BOT = UNBLOCK_CONFIG["bot_authors"][1]
UNBLOCK_SETTINGS = {
    "advisory_checks": ["CodeScene*", "review"],
    "trigger_expiry_days": 3,
    "lineage_stale_days": 3,
}


def make_unblock_pr(**overrides: object) -> dict[str, object]:
    """Build an overridable open bot PR fixture with no initial blockers."""
    pr: dict[str, object] = {
        "number": 23,
        "repository": UNBLOCK_REPO,
        "url": f"https://github.com/{UNBLOCK_REPO}/pull/23",
        "author": {"login": UNBLOCK_BOT, "type": "Bot"},
        "headRefName": "bot/update",
        "headRefOid": "a" * 40,
        "baseRefName": "main",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "REVIEW_REQUIRED",
        "isDraft": False,
        "checks": [],
        "comments": [],
        "commentsTotalCount": 0,
        "latestReviews": [],
    }
    pr.update(overrides)
    return pr


def route_unblock_pr(
    pr: dict[str, object],
    *,
    author_type: str = "BOT",
    items: list[dict[str, Any]] | None = None,
    ledger: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Route a PR fixture with a fixed clock and default ledger and settings."""
    return unblock.route_pr(
        pr,
        author_type=author_type,
        ledger_items_for_pr=items or [],
        ledger=ledger or {"items": []},
        settings=settings or UNBLOCK_SETTINGS,
        now=UNBLOCK_NOW,
    )


def make_salvage_item(**overrides: object) -> dict[str, object]:
    """Build a merged Stage 2 replacement fixture linked to the original PR."""
    item: dict[str, object] = {
        "key": f"{UNBLOCK_REPO}#90@{'b' * 40}",
        "repository": UNBLOCK_REPO,
        "pr": 90,
        "url": f"https://github.com/{UNBLOCK_REPO}/pull/90",
        "evidence_urls": [f"https://github.com/{UNBLOCK_REPO}/pull/23"],
        "handoffs": ["evt-s2-20261001-salvage"],
        "lifecycle_state": "TERMINAL",
        "terminal_disposition": "MERGED_ROUTINE",
    }
    item.update(overrides)
    return item


def run_unblock_plan(
    live: dict[str, Any] | None = None,
    *,
    apply: bool = False,
    run: Any = None,
    inventory_error: BaseException | None = None,
) -> tuple[dict[str, Any], Any]:
    """Capture a one-repository plan with mocked ledger, inventory, and writes."""
    config = dict(UNBLOCK_CONFIG)
    config["repos"] = [UNBLOCK_REPO]
    ledger = {"ledger_revision": 3, "items": []}
    output: dict[str, Any] = {}
    inventory_patch = (
        mock.patch.object(unblock, "list_open_prs", side_effect=inventory_error)
        if inventory_error is not None
        else mock.patch.object(unblock, "list_open_prs", return_value=[live])
    )
    with (
        mock.patch.object(unblock, "load_yaml", side_effect=[config, ledger]),
        mock.patch.object(
            unblock.cas,
            "run_preflight",
            return_value={"ledger_path": "ledger.yaml"},
        ),
        inventory_patch,
        mock.patch.object(unblock, "_apply_action"),
        mock.patch.object(
            unblock,
            "update_backlog_issue",
            return_value={"action": "NOOP_EMPTY"},
        ) as update_issue,
        mock.patch.object(
            unblock, "_emit", side_effect=lambda plan, _json: output.update(plan)
        ),
    ):
        unblock.run_unblock(
            apply=apply,
            json_out=True,
            repos_filter=[UNBLOCK_REPO],
            limit=0,
            run=run or subprocess.run,
        )
    return output, update_issue
