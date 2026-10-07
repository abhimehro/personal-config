"""Tests for fail-closed open-PR intake and ledger application."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_ledger as ledger_module

_SPEC = importlib.util.spec_from_file_location(
    "pr_lifecycle_reconcile_ingest_tests", SCRIPTS / "pr_lifecycle_reconcile.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("cannot load pr_lifecycle_reconcile for intake tests")
reconcile = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = reconcile
_SPEC.loader.exec_module(reconcile)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
CONFIG = yaml.safe_load((ROOT / "tasks/pr-review-agent.config.yaml").read_text())
REPO = CONFIG["repos"][0]


def _live(**overrides):
    """Build an overridable bot PR fixture with valid intake identity anchors."""
    pr = {
        "number": 9876,
        "repository": REPO,
        "url": f"https://github.com/{REPO}/pull/9876",
        "title": "Update dependency",
        "body": "",
        "isDraft": True,
        "headRefName": "dependabot/npm/package-1",
        "headRefOid": "a" * 40,
        "baseRefName": "main",
        "baseRefOid": "b" * 40,
        "author": {"login": CONFIG["bot_authors"][0], "type": "Bot"},
        "comments": [],
        "latestReviews": [],
        "commits": [],
        "checks": [],
    }
    pr.update(overrides)
    return pr


def _terminal_item(key: str, **overrides):
    """Build an overridable terminal ledger item for the supplied key."""
    item = {
        "key": key,
        "repository": REPO,
        "pr": 9876,
        "lifecycle_state": "TERMINAL",
        "terminal_disposition": "CLOSED_NOOP",
    }
    item.update(overrides)
    return item


class OpenPrIngestTests(unittest.TestCase):
    def setUp(self):
        """Start each intake test with an empty ledger and a valid open bot PR."""
        self.ledger = {"ledger_revision": 4, "items": [], "events": []}
        self.live = _live()

    def test_untracked_pr_builds_schema_valid_fail_closed_intake(self):
        """Require new intake items to satisfy the schema with unevaluated guardrails."""
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
        )
        self.assertEqual(actions[0]["action"], "INGEST_OPEN_PR")
        item = actions[0]["item"]
        ledger_module.validate_item(item, set())
        schema = json.loads(
            (ROOT / "schemas/pr-lifecycle-ledger.schema.json").read_text()
        )
        item_schema = {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            **schema["$defs"]["item"],
        }
        jsonschema.Draft202012Validator(item_schema).validate(item)
        projection = ledger_module.initial_projection()
        for field, value in projection.items():
            if field in item:
                self.assertEqual(item[field], value)
        self.assertEqual(item["risk_class"], "UNKNOWN")
        self.assertEqual(item["guardrail_outcome"], "NOT_RUN")
        self.assertTrue(item["safe_default"].startswith("Leave open"))

    def test_nonterminal_pr_is_not_ingested(self):
        """Avoid duplicate intake while the PR already has an active ledger item."""
        self.ledger["items"] = [
            _terminal_item(
                f"{REPO}#9876@{'a' * 40}",
                lifecycle_state="STAGE1_INTAKE",
                terminal_disposition=None,
            )
        ]
        self.assertEqual(
            reconcile.collect_ingest_actions(
                self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
            ),
            [],
        )

    def test_terminal_at_same_head_is_reported_but_old_head_is_reingested(self):
        """Report a terminal current head and allow intake after the head changes."""
        key = f"{REPO}#9876@{'a' * 40}"
        self.ledger["items"] = [_terminal_item(key)]
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
        )
        self.assertEqual(actions[0]["action"], "TERMINAL_BUT_OPEN")
        old_terminal = _terminal_item(f"{REPO}#9876@{'c' * 40}")
        self.ledger["items"] = [old_terminal]
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
        )
        self.assertEqual(actions[0]["action"], "INGEST_OPEN_PR")

    def test_invalid_anchors_and_empty_login_are_reported_as_skipped(self):
        """Skip intake when either SHA anchor or the author login is invalid."""
        bad_sha = _live(headRefOid="bad")
        bad_base = _live(baseRefOid="bad")
        no_login = _live(author={"login": ""})
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [bad_sha, bad_base, no_login]}, now=NOW
        )
        self.assertEqual([item["action"] for item in actions], ["INGEST_SKIPPED"] * 3)

    def test_apply_is_idempotent_and_advances_revision_once_per_batch(self):
        """Apply intake once and advance the ledger revision once for the batch."""
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
        )
        applied = reconcile._apply_ingest_actions(self.ledger, actions)
        self.assertEqual(len(applied), 1)
        self.assertEqual(self.ledger["ledger_revision"], 5)
        self.assertEqual(self.ledger["events"], [])
        again = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
        )
        self.assertEqual(again, [])
        self.assertEqual(len(self.ledger["items"]), 1)

    def test_full_example_ledger_with_intake_item_passes_runtime_validator(self):
        """Validate a complete example ledger after appending a new intake item."""
        ledger = yaml.safe_load(
            (ROOT / "tasks/pr-lifecycle-ledger.example.yaml").read_text()
        )
        ledger["items"].append(
            reconcile.collect_ingest_actions(
                ledger, CONFIG, {REPO: [self.live]}, now=NOW
            )[0]["item"]
        )
        ledger_module.validate_runtime_records(ledger, CONFIG)

    def test_inventory_oserror_is_emitted_as_inventory_failed(self):
        """Include inventory failures and their reasons in the reconciliation plan."""
        output = {}
        fetch = {"ledger_path": ROOT / "tasks/pr-lifecycle-ledger.example.yaml"}
        with (
            mock.patch.object(reconcile.cas, "run_preflight", return_value=fetch),
            mock.patch.object(
                reconcile,
                "load_yaml",
                side_effect=[CONFIG, self.ledger],
            ),
            mock.patch.object(reconcile, "collect_actions", return_value=[]),
            mock.patch.object(
                reconcile,
                "list_open_prs",
                side_effect=OSError("network"),
            ),
            mock.patch.object(
                reconcile, "_emit", side_effect=lambda plan, _json: output.update(plan)
            ),
        ):
            reconcile.run_reconcile(apply=False, limit=None, json_out=True, ingest=True)
        self.assertEqual(len(output["inventory_failed"]), len(CONFIG["repos"]))
        self.assertEqual(output["inventory_failed"][0]["action"], "INVENTORY_FAILED")
        self.assertEqual(output["inventory_failed"][0]["reason"], "OSError: network")

    def test_duplicate_inventory_is_planned_once_without_mutating_inputs(self):
        before = copy.deepcopy((self.ledger, self.live))
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live, self.live]}, now=NOW
        )
        self.assertEqual([action["action"] for action in actions], ["INGEST_OPEN_PR"])
        self.assertEqual((self.ledger, self.live), before)

    def test_invalid_numbers_and_urls_are_skipped(self):
        for overrides in (
            {"number": True},
            {"number": 0},
            {"number": -1},
            {"number": "9876"},
            {"url": None},
            {"url": "http://github.com/owner/repo/pull/1"},
        ):
            with self.subTest(overrides=overrides):
                actions = reconcile.collect_ingest_actions(
                    self.ledger, CONFIG, {REPO: [_live(**overrides)]}, now=NOW
                )
                self.assertEqual(len(actions), 1)
                self.assertEqual(actions[0]["action"], "INGEST_SKIPPED")
                self.assertNotIn("item", actions[0])

    def test_unconfigured_repository_is_not_ingested(self):
        actions = reconcile.collect_ingest_actions(
            self.ledger,
            CONFIG,
            {"unconfigured/repo": [_live(repository="unconfigured/repo")]},
            now=NOW,
        )
        self.assertEqual(actions, [])

    def test_nonterminal_old_head_prevents_parallel_intake(self):
        self.ledger["items"] = [
            _terminal_item(
                f"{REPO}#9876@{'c' * 40}",
                lifecycle_state="STAGE2_ACTIVE",
                terminal_disposition=None,
            )
        ]
        actions = reconcile.collect_ingest_actions(
            self.ledger, CONFIG, {REPO: [self.live]}, now=NOW
        )
        self.assertEqual(actions, [])

    def test_apply_batch_deduplicates_and_replay_does_not_bump_revision(self):
        actions = reconcile.collect_ingest_actions(
            self.ledger,
            CONFIG,
            {
                REPO: [
                    self.live,
                    _live(number=9877, url=f"https://github.com/{REPO}/pull/9877"),
                ]
            },
            now=NOW,
        )
        actions.append(copy.deepcopy(actions[0]))
        actions.append({"action": "INVENTORY_FAILED", "repository": REPO})
        applied = reconcile._apply_ingest_actions(self.ledger, actions)
        self.assertEqual(len(applied), 2)
        self.assertEqual(len(self.ledger["items"]), 2)
        self.assertEqual(self.ledger["ledger_revision"], 5)
        self.assertEqual(actions[2]["skipped"], "duplicate key")
        before = copy.deepcopy(self.ledger)
        self.assertEqual(reconcile._apply_ingest_actions(self.ledger, actions), [])
        self.assertEqual(self.ledger, before)

    def test_no_ingest_preserves_closed_bookkeeping_without_inventory(self):
        output = {}
        action = {"action": "TERMINAL_CLOSED", "disposition": "CLOSED_NOOP"}
        with (
            mock.patch.object(
                reconcile.cas,
                "run_preflight",
                return_value={"ledger_path": "ledger.yaml"},
            ),
            mock.patch.object(
                reconcile, "load_yaml", side_effect=[CONFIG, self.ledger]
            ),
            mock.patch.object(reconcile, "collect_actions", return_value=[action]),
            mock.patch.object(reconcile, "list_open_prs") as inventory,
            mock.patch.object(reconcile.cas, "run_commit") as commit,
            mock.patch.object(
                reconcile, "_emit", side_effect=lambda plan, _json: output.update(plan)
            ),
        ):
            result = reconcile.run_reconcile(
                apply=False, limit=None, json_out=True, ingest=False
            )
        self.assertEqual(result, 0)
        inventory.assert_not_called()
        commit.assert_not_called()
        self.assertEqual(output["actions"], [action])
        self.assertEqual(output["ingest_count"], 0)
        self.assertEqual(output["inventory_failed"], [])


if __name__ == "__main__":
    unittest.main()
