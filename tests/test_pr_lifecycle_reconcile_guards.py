"""Tests for reconcile apply guards: inventory abort, per-save cap, CAS replan."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_reconcile as reconcile  # noqa: E402
import pr_lifecycle_reconcile_guards as guards  # noqa: E402
from pr_lifecycle_github_http import OPERATOR_CONFLICT, CasError  # noqa: E402

CONFIG = yaml.safe_load((ROOT / "tasks/pr-review-agent.config.yaml").read_text())


def _plan(actions, inventory_failed=None):
    return (
        {
            "dry_run": False,
            "ledger_revision": 1,
            "action_count": len(actions),
            "actions": actions,
            "ingest_count": 0,
            "terminal_but_open_count": 0,
            "inventory_failed": inventory_failed or [],
        },
        {"items": [], "events": []},
        actions,
    )


class SelectBatchTest(unittest.TestCase):
    def test_terminal_first_and_cap_excludes_report_only(self):
        actions = [
            {"action": "INGEST_OPEN_PR", "id": 1},
            {"action": "REANCHOR_HEAD", "id": 2},
            {"action": "PATH_BACKFILL_FAILED", "id": 3},
            {"action": "TERMINAL_MERGED", "id": 4},
            {"action": "CLOSE_STALE", "id": 5},
            {"action": "TERMINAL_CLOSED", "id": 6},
        ]
        selected, deferred = guards.select_batch(actions, 3)
        self.assertEqual([a["id"] for a in selected], [3, 4, 6, 5])
        self.assertEqual([a["id"] for a in deferred], [2, 1])

    def test_cap_env_and_floor(self):
        with mock.patch.dict("os.environ", {"PR_LIFECYCLE_MAX_APPLY": "7"}):
            self.assertEqual(guards.max_apply_from_env(), 7)
        with mock.patch.dict("os.environ", {"PR_LIFECYCLE_MAX_APPLY": "x"}):
            self.assertEqual(guards.max_apply_from_env(), guards.DEFAULT_MAX_APPLY)
        self.assertEqual(guards.max_apply_from_env(0), 1)

    def test_backoff_grows(self):
        mid = lambda: 0.5  # noqa: E731
        self.assertEqual(guards.backoff_seconds(1, rng=mid), 20.0)
        self.assertEqual(guards.backoff_seconds(3, rng=mid), 80.0)


class RunReconcileGuardTest(unittest.TestCase):
    def _run(self, plans, commit_side_effect=None, **kw):
        out = {}
        with (
            mock.patch.object(reconcile, "load_yaml", return_value=CONFIG),
            mock.patch.object(reconcile, "_build_plan", side_effect=plans) as build,
            mock.patch.object(reconcile, "_apply_actions", return_value=[]) as apply_,
            mock.patch.object(reconcile, "_apply_ingest_actions", return_value=[]),
            mock.patch.object(reconcile, "dump_ledger", return_value="x: 1\n"),
            mock.patch.object(
                reconcile.cas, "run_commit", side_effect=commit_side_effect
            ) as commit,
            mock.patch.object(guards, "sleep") as sleep,
            mock.patch.object(
                reconcile, "_emit", side_effect=lambda p, _j: out.update(p)
            ),
        ):
            env = {"PR_LIFECYCLE_MAX_APPLY": str(kw.get("max_apply", 60))}
            with mock.patch.dict("os.environ", env):
                rc = reconcile.run_reconcile(apply=True, limit=None, json_out=True)
        return rc, out, build, apply_, commit, sleep

    def test_inventory_failure_aborts_before_mutation(self):
        failed = [{"action": "INVENTORY_FAILED", "repository": "a/b", "reason": "x"}]
        rc, out, _b, apply_, commit, _s = self._run(
            [_plan([{"action": "TERMINAL_CLOSED"}] + failed, failed)]
        )
        self.assertEqual(rc, guards.INVENTORY_ABORT_EXIT)
        self.assertEqual(out["aborted"], "INVENTORY_FAILED")
        apply_.assert_not_called()
        commit.assert_not_called()

    def test_cap_defers_remainder(self):
        actions = [{"action": "TERMINAL_CLOSED"} for _ in range(5)]
        rc, out, _b, apply_, commit, _s = self._run(
            [_plan(actions)], commit_side_effect=[{"commit_sha": "c"}], max_apply=2
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out["deferred_count"], 3)
        self.assertEqual(len(apply_.call_args.args[1]), 2)
        commit.assert_called_once()

    def test_conflict_replans_then_succeeds(self):
        conflict = CasError(OPERATOR_CONFLICT)
        rc, out, build, _a, commit, sleep = self._run(
            [_plan([]), _plan([])],
            commit_side_effect=[conflict, {"commit_sha": "c"}],
        )
        self.assertEqual(rc, 0)
        self.assertEqual(build.call_count, 2)
        self.assertEqual(commit.call_count, 2)
        self.assertEqual(out["cas_attempt"], 2)
        sleep.assert_called_once()

    def test_conflict_exhausted(self):
        conflict = CasError(OPERATOR_CONFLICT)
        rc, out, build, _a, _c, sleep = self._run(
            [_plan([]) for _ in range(3)], commit_side_effect=[conflict] * 3
        )
        self.assertEqual(rc, guards.CAS_CONFLICT_EXIT)
        self.assertEqual(out["aborted"], "CAS_CONFLICT_EXHAUSTED")
        self.assertEqual(build.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_non_conflict_cas_error_propagates(self):
        with self.assertRaises(CasError):
            self._run([_plan([])], commit_side_effect=[CasError("OTHER")])


if __name__ == "__main__":
    unittest.main()
