"""Unit tests for the changed_paths backfill in pr_lifecycle_reconcile."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from tests.pr_lifecycle_helpers import (
    load_reconcile_with_stubs,
    reconcile_item,
)

reconcile = load_reconcile_with_stubs()

NOW = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)


def _item(**overrides):
    return reconcile_item(now=NOW, **overrides)


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

    def test_gh_pr_files_fails_closed_at_api_cap(self):
        out = "\n".join(f"f{i}.py" for i in range(3000)) + "\n"
        completed = types.SimpleNamespace(returncode=0, stdout=out)
        with mock.patch.object(reconcile.subprocess, "run", return_value=completed):
            self.assertIsNone(reconcile._gh_pr_files("owner/repo", 7))

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

    def _collect(self, item, live, files, limit=None):
        with mock.patch.object(
            reconcile, "_gh_pr_view", return_value=live
        ), mock.patch.object(reconcile, "_gh_pr_files", return_value=files):
            return reconcile.collect_actions(
                {"items": [item]}, {"lifecycle": {}}, now=NOW, limit=limit
            )

    def test_collect_actions_emits_backfill_with_primary(self):
        item = _item(lifecycle_state="STAGE1_INTAKE", changed_paths=[])
        actions = self._collect(
            item,
            {"state": "OPEN", "headRefOid": "a" * 40, "baseRefOid": "b" * 40},
            ["x.py", "y.py"],
        )
        self.assertEqual([action["action"] for action in actions], ["BACKFILL_PATHS"])

    def test_collect_actions_limit_truncates_backfill_pair(self):
        item = _item(lifecycle_state="STAGE1_INTAKE", changed_paths=[])
        live = {"state": "OPEN", "headRefOid": "c" * 40, "baseRefOid": "b" * 40}
        full = self._collect(item, live, ["x.py"])
        capped = self._collect(item, live, ["x.py"], limit=1)
        self.assertEqual(len(full), 2)
        self.assertEqual(capped, full[:1])

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
