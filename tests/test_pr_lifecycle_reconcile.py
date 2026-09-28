"""Unit tests for pr_lifecycle_reconcile classification (no network)."""

from __future__ import annotations

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
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_persist"].dump_ledger = lambda *_a, **_k: ""
sys.modules["pr_lifecycle_persist"].strip_in_memory_item_fields = lambda *_a, **_k: 0

import pr_lifecycle_reconcile as reconcile  # noqa: E402

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
_DEFAULT = object()


def _classify(item_overrides=None, live=_DEFAULT):
    return reconcile.classify_item(
        _item(**(item_overrides or {})),
        _OPEN_LIVE if live is _DEFAULT else live,
        expiry_days=7,
        now=NOW,
    )


class ClassifyItemTests(unittest.TestCase):
    def test_evidence_backed_live_states_go_terminal(self):
        cases = (
            (
                {"lifecycle_state": "STAGE1_INTAKE"},
                {
                    "state": "MERGED",
                    "headRefOid": "a" * 40,
                    "mergedBy": {"login": "someuser"},
                },
                "TERMINAL_MERGED",
                "MERGED_ROUTINE",
            ),
            (
                {"lifecycle_state": "STAGE2_QUEUED"},
                {
                    "state": "CLOSED",
                    "headRefOid": "a" * 40,
                    "labels": [{"name": "duplicate"}],
                },
                "TERMINAL_CLOSED",
                "CLOSED_DUPLICATE",
            ),
        )
        for overrides, live, action_name, disposition in cases:
            with self.subTest(action_name=action_name):
                action = _classify(overrides, live)
                self.assertEqual(action["action"], action_name)
                self.assertEqual(action["disposition"], disposition)

    def test_sha_drift_reintake(self):
        action = _classify(
            {"lifecycle_state": "STAGE2_QUEUED"},
            {"state": "OPEN", "headRefOid": "c" * 40},
        )
        self.assertEqual(action["action"], "SHA_DRIFT_REINTAKE")
        self.assertEqual(action["to_state"], "STAGE1_INTAKE")

    def test_stale_waiting_human_bot(self):
        action = _classify()
        self.assertEqual(action["action"], "CLOSE_STALE")
        self.assertEqual(action["disposition"], "CLOSED_STALE")

    def test_review_security_not_stale_closed(self):
        self.assertIsNone(_classify({"guardrail_outcome": "REVIEW_SECURITY"}))

    def test_fresh_waiting_human_not_stale(self):
        stamp = (NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertIsNone(_classify({"updated_at_utc": stamp}))

    def test_terminal_item_is_ignored_even_when_lookup_failed(self):
        self.assertIsNone(_classify({"lifecycle_state": "TERMINAL"}, None))

    def test_lookup_failure_is_reported_without_mutation_fields(self):
        action = _classify({"lifecycle_state": "STAGE1_INTAKE"}, None)
        self.assertEqual(action["action"], "LIVE_LOOKUP_FAILED")
        self.assertNotIn("to_state", action)

    def test_live_terminal_state_takes_precedence_over_sha_drift(self):
        action = _classify(
            {"lifecycle_state": "STAGE2_QUEUED"},
            {
                "state": "merged",
                "headRefOid": "c" * 40,
                "mergedBy": {"login": "someuser"},
            },
        )
        self.assertEqual(action["action"], "TERMINAL_MERGED")

    def test_sha_comparison_is_case_insensitive(self):
        action = _classify(
            {
                "lifecycle_state": "STAGE2_QUEUED",
                "head_sha": "abcdef" * 6 + "abcd",
            },
            {"state": "OPEN", "headRefOid": "ABCDEF" * 6 + "ABCD"},
        )
        self.assertIsNone(action)

    def test_stale_cutoff_is_exclusive(self):
        stamp = (NOW - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertIsNone(_classify({"updated_at_utc": stamp}))

    def test_merged_stage3_owned_is_bounded_completion(self):
        for overrides in (
            {"lifecycle_state": "STAGE3_RECONCILIATION"},
            {"lifecycle_state": "STAGE2_QUEUED", "current_owner": "stage3"},
        ):
            with self.subTest(overrides=overrides):
                action = _classify(
                    overrides,
                    {
                        "state": "MERGED",
                        "headRefOid": "a" * 40,
                        "mergedBy": {"login": "someuser"},
                    },
                )
                self.assertEqual(action["disposition"], "MERGED_BOUNDED_COMPLETION")

    def test_merged_without_merger_evidence_routes_to_stage3_pending(self):
        action = _classify(
            {"lifecycle_state": "WAITING_HUMAN"},
            {"state": "MERGED", "headRefOid": "a" * 40},
        )
        self.assertEqual(action["action"], "TERMINAL_PENDING")
        self.assertEqual(action["to_state"], "STAGE3_RECONCILIATION")
        self.assertIsNone(action["disposition"])
        self.assertEqual(action["observed_state"], "MERGED")

    def test_closed_label_dispositions(self):
        cases = (
            ("duplicate", "CLOSED_DUPLICATE"),
            ("superseded", "CLOSED_SUPERSEDED"),
            ("stale-auto-closed", "CLOSED_STALE"),
            ("wontfix", "HUMAN_REJECTED"),
            ("declined", "HUMAN_REJECTED"),
        )
        for label, expected in cases:
            with self.subTest(label=label):
                action = _classify(
                    {"lifecycle_state": "STAGE2_QUEUED"},
                    {
                        "state": "CLOSED",
                        "headRefOid": "a" * 40,
                        "labels": [{"name": label}],
                    },
                )
                self.assertEqual(action["action"], "TERMINAL_CLOSED")
                self.assertEqual(action["disposition"], expected)

    def test_closed_without_evidence_routes_to_stage3_pending(self):
        for labels in (None, [], [{"name": "enhancement"}]):
            with self.subTest(labels=labels):
                live = {"state": "CLOSED", "headRefOid": "a" * 40}
                if labels is not None:
                    live["labels"] = labels
                action = _classify({"lifecycle_state": "STAGE1_INTAKE"}, live)
                self.assertEqual(action["action"], "TERMINAL_PENDING")
                self.assertEqual(action["to_state"], "STAGE3_RECONCILIATION")
                self.assertIsNone(action["disposition"])

    def test_pending_observed_stage3_item_notes_in_place(self):
        action = _classify(
            {"lifecycle_state": "STAGE3_RECONCILIATION"},
            {"state": "CLOSED", "headRefOid": "a" * 40},
        )
        self.assertEqual(action["action"], "TERMINAL_OBSERVED")
        self.assertNotIn("to_state", action)
        self.assertEqual(action["observed_state"], "CLOSED")

    def test_repeat_reconcile_does_not_reclassify_pending_observation(self):
        action = _classify(
            {
                "lifecycle_state": "STAGE3_RECONCILIATION",
                "next_action": "Observed CLOSED unclassified: no label",
            },
            {"state": "CLOSED", "headRefOid": "a" * 40},
        )
        self.assertIsNone(action)

    def test_stale_close_requires_parseable_bot_packet(self):
        cases = (
            {"author_type": "HUMAN"},
            {"lifecycle_state": "STAGE2_QUEUED"},
            {"updated_at_utc": "not-a-timestamp"},
            {"updated_at_utc": "2026-09-01T00:00:00+00:00"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertIsNone(_classify(overrides))


def _transition_effect(event, projected):
    projected.update(
        revision=event["resulting_item_revision"],
        lifecycle_state=event["to_state"],
        current_owner=event["to_owner"],
        next_owner=event["next_owner"],
        terminal_disposition=event["terminal_disposition"],
    )
    projected["handoffs"].append(event["event_id"])


def _apply_with_mocks(ledger, item, action):
    with mock.patch.object(
        reconcile.ledger_mod, "apply_transition", side_effect=_transition_effect
    ):
        with mock.patch.object(reconcile, "_event_id", return_value="evt-fixed"):
            with mock.patch.object(reconcile, "_utc_now", return_value=NOW):
                return reconcile.apply_action_to_ledger(ledger, item, action)


class ReconcileHelpersTests(unittest.TestCase):
    def test_collect_actions_skips_invalid_and_terminal_items_and_honors_limit(self):
        ledger = {
            "items": [
                "invalid",
                _item(key="terminal", lifecycle_state="TERMINAL"),
                _item(key="first", lifecycle_state="STAGE1_INTAKE"),
                _item(key="second", lifecycle_state="STAGE2_QUEUED"),
            ]
        }
        live = {"state": "CLOSED", "headRefOid": "a" * 40}
        with mock.patch.object(reconcile, "_gh_pr_view", return_value=live) as view:
            actions = reconcile.collect_actions(
                ledger,
                {"lifecycle": {"packet_expiry_close_days": 7}},
                now=NOW,
                limit=1,
            )
        self.assertEqual([action["key"] for action in actions], ["first"])
        view.assert_called_once_with("abhimehro/personal-config", 99)

    def test_build_transition_event_preserves_revision_and_owner_contract(self):
        action = {
            "to_state": "TERMINAL",
            "disposition": "CLOSED_NOOP",
            "reason": "closed upstream",
        }
        with mock.patch.object(reconcile, "_event_id", return_value="evt-fixed"):
            with mock.patch.object(reconcile, "_utc_now", return_value=NOW):
                event = reconcile.build_transition_event(
                    _item(lifecycle_state="STAGE2_QUEUED", current_owner="stage2"),
                    action,
                    kind="TERMINAL",
                )
        self.assertEqual(event["event_id"], "evt-fixed")
        self.assertEqual(event["expected_item_revision"], 1)
        self.assertEqual(event["resulting_item_revision"], 2)
        self.assertEqual(event["to_owner"], "none")
        self.assertEqual(event["next_owner"], "none")
        self.assertEqual(event["created_at_utc"], "2026-09-21T18:00:00Z")

    def test_apply_sha_drift_action_updates_projection_and_records_event(self):
        ledger = {"ledger_revision": 4, "events": []}
        item = _item(lifecycle_state="STAGE2_QUEUED", current_owner="stage2")
        action = {
            "action": "SHA_DRIFT_REINTAKE",
            "to_state": "STAGE1_INTAKE",
            "disposition": None,
            "reason": "head changed",
            "live_head_sha": "c" * 40,
        }
        event = _apply_with_mocks(ledger, item, action)
        self.assertEqual(item["revision"], 2)
        self.assertEqual(item["lifecycle_state"], "STAGE1_INTAKE")
        self.assertEqual(item["current_owner"], "stage1")
        self.assertEqual(item["handoffs"], ["evt-fixed"])
        self.assertIn("c" * 40, item["next_action"])
        self.assertEqual(ledger["ledger_revision"], 5)
        self.assertIs(ledger["events"][0], event)

    def test_apply_terminal_pending_handoffs_to_stage3_with_marker(self):
        ledger = {"ledger_revision": 4, "events": []}
        item = _item(lifecycle_state="WAITING_HUMAN", current_owner="human")
        action = {
            "action": "TERMINAL_PENDING",
            "to_state": "STAGE3_RECONCILIATION",
            "disposition": None,
            "observed_state": "CLOSED",
            "reason": "closed without classifying evidence",
        }
        event = _apply_with_mocks(ledger, item, action)
        self.assertEqual(event["kind"], "HANDOFF")
        self.assertEqual(item["lifecycle_state"], "STAGE3_RECONCILIATION")
        self.assertEqual(item["current_owner"], "stage3")
        self.assertIsNone(item["terminal_disposition"])
        self.assertIn("Observed CLOSED unclassified", item["next_action"])
        self.assertEqual(ledger["events"], [event])

    def test_apply_terminal_observed_notes_in_place_without_event(self):
        ledger = {"ledger_revision": 4, "events": []}
        item = _item(
            lifecycle_state="STAGE3_RECONCILIATION", current_owner="stage3"
        )
        action = {
            "action": "TERMINAL_OBSERVED",
            "observed_state": "MERGED",
            "reason": "Observed MERGED unclassified: mergedBy unavailable",
        }
        with mock.patch.object(reconcile, "_utc_now", return_value=NOW):
            result = reconcile.apply_action_to_ledger(ledger, item, action)
        self.assertIsNone(result["event_id"])
        self.assertEqual(item["revision"], 2)
        self.assertEqual(item["lifecycle_state"], "STAGE3_RECONCILIATION")
        self.assertIn("Observed MERGED unclassified", item["next_action"])
        self.assertEqual(ledger["events"], [])
        self.assertEqual(ledger["ledger_revision"], 5)

    def test_gh_pr_view_handles_success_bad_json_and_command_failure(self):
        # Success path uses two gh calls: pr view --json (no baseRefOid) then
        # REST api for base.sha, mapped into payload["baseRefOid"].
        # Fail closed (None) if either call fails.
        view_ok = types.SimpleNamespace(
            returncode=0,
            stdout='{"state": "OPEN", "headRefOid": "abc"}',
        )
        base_ok = types.SimpleNamespace(returncode=0, stdout="def456\n")
        with mock.patch.object(
            reconcile.subprocess, "run", side_effect=[view_ok, base_ok]
        ) as run:
            payload = reconcile._gh_pr_view("owner/repo", 7)
            self.assertEqual(payload["headRefOid"], "abc")
            self.assertEqual(payload["baseRefOid"], "def456")
            self.assertEqual(run.call_count, 2)
            self.assertNotIn("baseRefOid", run.call_args_list[0].args[0][6])
            self.assertIn("repos/owner/repo/pulls/7", run.call_args_list[1].args[0])

        # View fails (returncode / bad json / non-dict) → None
        for completed in (
            types.SimpleNamespace(returncode=1, stdout=""),
            types.SimpleNamespace(returncode=0, stdout="not-json"),
            types.SimpleNamespace(returncode=0, stdout="[]"),
        ):
            with self.subTest(completed=completed):
                with mock.patch.object(
                    reconcile.subprocess, "run", return_value=completed
                ):
                    self.assertIsNone(reconcile._gh_pr_view("owner/repo", 7))

        with mock.patch.object(reconcile.subprocess, "run", side_effect=OSError):
            self.assertIsNone(reconcile._gh_pr_view("owner/repo", 7))

        # Base REST fails / empty → fail closed None (view already succeeded)
        base_fail = types.SimpleNamespace(returncode=1, stdout="")
        base_empty = types.SimpleNamespace(returncode=0, stdout="\n")
        for base_resp in (base_fail, base_empty):
            with self.subTest(base=base_resp):
                with mock.patch.object(
                    reconcile.subprocess,
                    "run",
                    side_effect=[view_ok, base_resp],
                ):
                    self.assertIsNone(reconcile._gh_pr_view("owner/repo", 7))

        with mock.patch.object(
            reconcile.subprocess,
            "run",
            side_effect=[view_ok, OSError("boom")],
        ):
            self.assertIsNone(reconcile._gh_pr_view("owner/repo", 7))

    def test_close_stale_github_validates_identity_and_runs_all_steps(self):
        self.assertEqual(
            reconcile._close_stale_github({}),
            (["skip github close: missing repository/pr"], False),
        )
        completed = [
            types.SimpleNamespace(returncode=0),
            types.SimpleNamespace(returncode=1),
            types.SimpleNamespace(returncode=2),
        ]
        with mock.patch.object(
            reconcile.subprocess, "run", side_effect=completed
        ) as command:
            steps, confirmed = reconcile._close_stale_github(
                {"repository": "owner/repo", "pr": 7}
            )
        self.assertEqual(steps, ["comment exit=0", "label exit=1", "close exit=2"])
        self.assertFalse(confirmed)
        self.assertEqual(
            [call.args[0][2] for call in command.call_args_list],
            ["comment", "edit", "close"],
        )


if __name__ == "__main__":
    unittest.main()
