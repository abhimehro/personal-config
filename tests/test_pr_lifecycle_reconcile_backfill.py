"""Unit tests for the changed_paths backfill in pr_lifecycle_reconcile."""

from __future__ import annotations

import re
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Stub heavy repo modules so classify_item can load without PyYAML / CAS.
# Restoring sys.modules keeps unittest discovery from leaking the stubs into
# the rest of the suite.
_STUB_NAMES = (
    "pr_lifecycle_ledger",
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_config",
    "pr_lifecycle_persist",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
)
_saved_modules = {name: sys.modules.get(name) for name in _STUB_NAMES}
for name in _STUB_NAMES:
    sys.modules[name] = types.ModuleType(name)

sys.modules["pr_lifecycle_ledger"].STATE_OWNERS = {
    "STAGE1_INTAKE": "stage1",
    "STAGE2_QUEUED": "stage2",
    "STAGE2_ACTIVE": "stage2",
    "STAGE3_RECONCILIATION": "stage3",
    "WAITING_HUMAN": "human",
    "TERMINAL": "none",
}
sys.modules["pr_lifecycle_ledger"].apply_transition = lambda *a, **k: None
sys.modules["pr_lifecycle_support"].ROOT = ROOT
sys.modules["pr_lifecycle_support"].SHA_RE = re.compile(r"^[0-9a-f]{40}$")
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_persist"].dump_ledger = lambda *_a, **_k: ""
sys.modules["pr_lifecycle_persist"].strip_in_memory_item_fields = lambda *_a, **_k: 0

import pr_lifecycle_reconcile as reconcile

for _name in _STUB_NAMES:
    _saved = _saved_modules[_name]
    if _saved is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _saved

NOW = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)


def _item(**overrides):
    base = {
        "key": "abhimehro/personal-config#99@" + "a" * 40,
        "repository": "abhimehro/personal-config",
        "pr": 99,
        "head_sha": "a" * 40,
        "base_sha": "b" * 40,
        "author_type": "BOT",
        "guardrail_outcome": "HOLD_EVIDENCE",
        "lifecycle_state": "WAITING_HUMAN",
        "current_owner": "human",
        "next_owner": "human",
        "terminal_disposition": None,
        "revision": 1,
        "handoffs": [],
        "updated_at_utc": (NOW - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_action": "Await human",
    }
    base.update(overrides)
    return base


_OPEN_LIVE = {"state": "OPEN", "headRefOid": "a" * 40}


class PathBackfillTests(unittest.TestCase):
    def test_gh_pr_files_returns_sorted_unique_paths(self):
        completed = types.SimpleNamespace(returncode=0, stdout="b.py\na.py\nb.py\n\n")
        with mock.patch.object(
            reconcile.subprocess, "run", return_value=completed
        ) as run:
            self.assertEqual(reconcile._gh_pr_files("owner/repo", 7), ["a.py", "b.py"])
        cmd = run.call_args.args[0]
        self.assertIn("repos/owner/repo/pulls/7/files", cmd)
        self.assertIn("--paginate", cmd)

    def test_gh_pr_files_requests_previous_filename(self):
        completed = types.SimpleNamespace(
            returncode=0, stdout="docs/x.yml\n.github/workflows/x.yml\n"
        )
        with mock.patch.object(
            reconcile.subprocess, "run", return_value=completed
        ) as run:
            reconcile._gh_pr_files("owner/repo", 7)
        self.assertIn("previous_filename", " ".join(run.call_args.args[0]))

    def test_gh_pr_files_fails_closed(self):
        for completed in (
            types.SimpleNamespace(returncode=1, stdout=""),
            types.SimpleNamespace(returncode=0, stdout="\n"),
        ):
            with self.subTest(completed=completed), mock.patch.object(
                reconcile.subprocess, "run", return_value=completed
            ):
                self.assertIsNone(reconcile._gh_pr_files("owner/repo", 7))
        with mock.patch.object(reconcile.subprocess, "run", side_effect=OSError):
            self.assertIsNone(reconcile._gh_pr_files("owner/repo", 7))

    def test_backfill_action_emitted_for_open_item_missing_paths(self):
        item = _item(lifecycle_state="STAGE1_INTAKE", changed_paths=[])
        with mock.patch.object(
            reconcile, "_gh_pr_files", return_value=["x.py"]
        ) as fetch:
            action = reconcile._path_backfill_action(item, _OPEN_LIVE)
        self.assertEqual(action["action"], "BACKFILL_PATHS")
        self.assertEqual(action["paths"], ["x.py"])
        fetch.assert_called_once_with("abhimehro/personal-config", 99)

    def test_backfill_action_failure_and_skip_cases(self):
        item = _item(changed_paths=[])
        with mock.patch.object(reconcile, "_gh_pr_files", return_value=None):
            action = reconcile._path_backfill_action(item, _OPEN_LIVE)
        self.assertEqual(action["action"], "PATH_BACKFILL_FAILED")
        with mock.patch.object(reconcile, "_gh_pr_files") as fetch:
            self.assertIsNone(
                reconcile._path_backfill_action(
                    _item(changed_paths=["a.py"]), _OPEN_LIVE
                )
            )
            self.assertIsNone(
                reconcile._path_backfill_action(item, {"state": "CLOSED"})
            )
            self.assertIsNone(reconcile._path_backfill_action(item, None))
        fetch.assert_not_called()

    def test_collect_actions_emits_backfill_with_primary(self):
        item = _item(lifecycle_state="STAGE1_INTAKE", changed_paths=[])
        ledger = {"items": [item]}
        live = {
            "state": "OPEN",
            "headRefOid": "a" * 40,
            "baseRefOid": "b" * 40,
        }
        with mock.patch.object(
            reconcile, "_gh_pr_view", return_value=live
        ), mock.patch.object(reconcile, "_gh_pr_files", return_value=["x.py", "y.py"]):
            actions = reconcile.collect_actions(ledger, {"lifecycle": {}}, now=NOW)
        self.assertEqual([action["action"] for action in actions], ["BACKFILL_PATHS"])

    def test_collect_actions_respects_limit_with_backfill(self):
        item = _item(lifecycle_state="STAGE1_INTAKE", changed_paths=[])
        ledger = {"items": [item]}
        live = {
            "state": "OPEN",
            "headRefOid": "a" * 40,
            "baseRefOid": "b" * 40,
        }
        with mock.patch.object(
            reconcile, "_gh_pr_view", return_value=live
        ), mock.patch.object(reconcile, "_gh_pr_files", return_value=["x.py"]):
            actions = reconcile.collect_actions(
                ledger, {"lifecycle": {}}, now=NOW, limit=1
            )
        self.assertLessEqual(len(actions), 1)

    def test_apply_backfills_paths_without_event_or_stale_reset(self):
        item = _item(changed_paths=[])
        stamp = item["updated_at_utc"]
        ledger = {"items": [item], "events": [], "ledger_revision": 5}
        action = {
            "action": "BACKFILL_PATHS",
            "key": item["key"],
            "paths": ["z.py", "a.py", "z.py"],
        }
        result = reconcile.apply_action_to_ledger(ledger, item, action)
        self.assertIsNone(result["event_id"])
        self.assertEqual(item["changed_paths"], ["a.py", "z.py"])
        self.assertEqual(item["revision"], 1)
        self.assertEqual(ledger["events"], [])
        self.assertEqual(ledger["ledger_revision"], 6)
        self.assertEqual(item["updated_at_utc"], stamp)
        with self.assertRaises(reconcile.ReconcileSkip):
            reconcile.apply_action_to_ledger(ledger, item, action)
        with self.assertRaises(reconcile.ReconcileSkip):
            reconcile.apply_action_to_ledger(
                ledger,
                item,
                {"action": "BACKFILL_PATHS", "key": item["key"], "paths": []},
            )

    def test_path_backfill_failed_is_report_only(self):
        item = _item(changed_paths=[])
        ledger = {"items": [item], "ledger_revision": 5}
        failed = {"action": "PATH_BACKFILL_FAILED", "key": item["key"]}
        self.assertEqual(reconcile._apply_actions(ledger, [failed]), [])
        self.assertEqual(item["changed_paths"], [])
        self.assertEqual(ledger["ledger_revision"], 5)


if __name__ == "__main__":
    unittest.main()
