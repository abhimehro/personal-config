"""Tests for backlog issue state persistence and overdue notification."""

from __future__ import annotations

import json
import subprocess
import unittest
from datetime import timedelta
from unittest import mock

import pr_lifecycle_issue_status as issue_status

from tests.pr_lifecycle_helpers import NOW, import_lifecycle_run

run = import_lifecycle_run()


class BacklogStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.st = issue_status
        self.status = {
            "updated_at_utc": "2026-08-30T12:00:00Z",
            "run_id": "test-status",
            "stage": 3,
            "ledger_revision": 12,
            "reason": "OK",
            "stop_class": None,
            "signals_status": "PARTIAL",
            "condition": "SIGNALS_DEGRADED",
            "calibration_enabled": False,
        }
        # Every test mocks the process boundary, including unexpected calls.
        self.command = self.enterContext(mock.patch.object(self.st.subprocess, "run"))

    @staticmethod
    def result(
        stdout: str = "", returncode: int = 0, stderr: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)

    def _backlog_row(self) -> dict:
        """Return a human-decision backlog row fixture for PR 42."""
        return {
            "pr": 42,
            "url": "https://github.com/owner/repo/pull/42",
            "blocker": "required_check_failure",
            "evidence": "Build failed",
            "recommended_action": "Fix checks",
            "safe_default": "Leave open",
            "owner": "human",
            "packet_expiry_close_days": 7,
        }

    def _listing(self, body: str) -> subprocess.CompletedProcess[str]:
        """Return a gh issue list result exposing one backlog issue."""
        return self.result(
            json.dumps(
                [{"number": 51, "title": self.st.BACKLOG_ISSUE_TITLE, "body": body}]
            )
        )

    @staticmethod
    def _state_block(body: str) -> dict:
        """Parse the embedded backlog state block out of an issue body."""
        return json.loads(
            body.split("<!-- pr-lifecycle-backlog-state ", 1)[1].split(" -->", 1)[0]
        )

    def test_removed_rows_prune_overdue_notifications_before_readding(self) -> None:
        """Allow a fresh overdue notification after a row is removed and re-added."""
        repo = "owner/repo"
        key = f"{repo}#42"
        state = {
            "first_seen": {key: "2026-08-01T12:00:00Z"},
            "overdue_notified": [key],
        }
        empty_body = self.st.backlog_issue_body(
            self.st._BacklogSpec(repo, state, NOW), []
        )
        empty_state = self.st._previous_state(empty_body)
        self.assertEqual(empty_state["overdue_notified"], [])

        row = {
            "pr": 42,
            "url": "https://github.com/owner/repo/pull/42",
            "blocker": "required_check_failure",
            "expires": "2026-08-01T12:00:00Z",
        }
        _prepared, refreshed_state, newly_overdue = self.st._prepare_backlog_rows(
            self.st._BacklogSpec(repo, empty_state, NOW), [row]
        )
        self.assertEqual([item["id"] for item in newly_overdue], [key])
        self.assertEqual(refreshed_state["overdue_notified"], [key])

    def test_backlog_refresh_preserves_first_seen_and_notifies_overdue_once(
        self,
    ) -> None:
        """Preserve first-seen dates and avoid repeating an overdue notification."""
        repo = "owner/repo"
        key = f"{repo}#42"
        row = self._backlog_row()
        old_state = {
            "first_seen": {key: "2026-08-01T12:00:00Z"},
            "overdue_notified": [],
        }
        old_body = self.st.backlog_issue_body(
            self.st._BacklogSpec(repo, old_state, NOW - timedelta(days=25)),
            [row],
        )
        self.command.side_effect = [
            self._listing(old_body),
            self.result(),
            self.result(),
        ]
        result = self.st.update_backlog_issue(repo, [row], now=NOW)
        self.assertEqual(result["action"], "EDITED")
        comment_argv = self.command.call_args_list[1].args[0]
        self.assertEqual(comment_argv[2:4], ["comment", "51"])
        comment_body = comment_argv[comment_argv.index("--body") + 1]
        self.assertIn(
            "@abhimehro 1 item(s) passed their decision deadline:", comment_body
        )
        edit_argv = self.command.call_args_list[2].args[0]
        body = edit_argv[edit_argv.index("--body") + 1]
        self.assertIn("2026-08-01T12:00:00Z", body)
        self.assertEqual(self._state_block(body)["overdue_notified"], [key])

        self.command.reset_mock()
        self.command.side_effect = [self._listing(body), self.result()]
        self.st.update_backlog_issue(repo, [row], now=NOW)
        self.assertEqual(self.command.call_count, 2)
        self.assertEqual(self.command.call_args_list[1].args[0][2], "edit")

    def test_empty_backlog_edits_existing_but_does_not_create(self) -> None:
        """Refresh an existing issue to show that its decision backlog is empty."""
        repo = "owner/repo"
        self.command.side_effect = [
            self.result(
                json.dumps(
                    [
                        {
                            "number": 52,
                            "title": self.st.BACKLOG_ISSUE_TITLE,
                            "body": "",
                        }
                    ]
                )
            ),
            self.result(),
        ]
        result = self.st.update_backlog_issue(repo, [], now=NOW)
        self.assertEqual(result["action"], "EDITED")
        argv = self.command.call_args_list[1].args[0]
        self.assertEqual(argv[2:4], ["edit", "52"])
        self.assertIn(
            "No open items needing a human decision",
            argv[argv.index("--body") + 1],
        )
        self.assertEqual(argv[-2:], ["--repo", repo])

    def test_empty_backlog_without_issue_and_failed_listing_do_not_create(self) -> None:
        """Avoid issue creation for an empty backlog or a malformed listing."""
        self.command.side_effect = [self.result("[]")]
        result = self.st.update_backlog_issue("owner/repo", [], now=NOW)
        self.assertEqual(result["action"], "NOOP_EMPTY")
        self.assertEqual(self.command.call_count, 1)
        self.command.reset_mock()
        self.command.side_effect = [self.result("not-json")]
        with self.assertRaises(OSError):
            self.st.update_backlog_issue("owner/repo", [], now=NOW)
        self.assertEqual(self.command.call_count, 1)

    def test_failed_overdue_notification_does_not_persist_notified_state(self):
        repo = "owner/repo"
        row = {"pr": 42, "blocker": "conflict", "expires": "2026-08-01T00:00:00Z"}
        existing = [{"number": 9, "title": self.st.BACKLOG_ISSUE_TITLE, "body": ""}]
        self.command.side_effect = [
            self.result(json.dumps(existing)),
            self.result(returncode=1, stderr="comment rejected"),
        ]
        with self.assertRaisesRegex(OSError, "overdue comment failed"):
            self.st.update_backlog_issue(repo, [row], now=NOW)
        self.assertEqual(self.command.call_count, 2)
        self.assertEqual(
            self.command.call_args_list[1].args[0][1:4], ["issue", "comment", "9"]
        )
        # No edit may claim a notification that GitHub rejected.
        self.assertFalse(
            any("edit" in call.args[0] for call in self.command.call_args_list)
        )

    def test_new_issue_failed_notification_leaves_overdue_state_empty(self):
        repo = "owner/repo"
        row = {"pr": 42, "blocker": "conflict", "expires": "2026-08-01T00:00:00Z"}
        self.command.side_effect = [
            self.result("[]"),
            self.result(f"https://github.com/{repo}/issues/9\n"),
            self.result(returncode=1, stderr="comment rejected"),
        ]
        with self.assertRaisesRegex(OSError, "overdue comment failed"):
            self.st.update_backlog_issue(repo, [row], now=NOW)
        self.assertEqual(
            [call.args[0][2] for call in self.command.call_args_list],
            ["list", "create", "comment"],
        )
        create_argv = self.command.call_args_list[1].args[0]
        body = create_argv[create_argv.index("--body") + 1]
        state = self.st._previous_state(body)
        self.assertEqual(state["overdue_notified"], [])
        self.assertIn("OVERDUE", body)
        _, _, overdue = self.st._prepare_backlog_rows(
            self.st._BacklogSpec(repo, state, NOW), [row]
        )
        self.assertEqual([item["id"] for item in overdue], [f"{repo}#42"])

    def test_new_overdue_issue_is_created_then_notified_and_persisted(self):
        repo = "owner/repo"
        row = {"pr": 42, "blocker": "conflict", "expires": "2026-08-01T00:00:00Z"}
        self.command.side_effect = [
            self.result("[]"),
            self.result(f"https://github.com/{repo}/issues/9\n"),
            self.result(),
            self.result(),
        ]
        result = self.st.update_backlog_issue(repo, [row], now=NOW)
        self.assertEqual(result["action"], "CREATED")
        self.assertEqual(result["issue_number"], 9)
        self.assertEqual(
            [call.args[0][2] for call in self.command.call_args_list],
            ["list", "create", "comment", "edit"],
        )
        self.assertEqual(result["overdue_notified"], [f"{repo}#42"])
        state = self.st._previous_state(result["body"])
        self.assertEqual(state["overdue_notified"], result["overdue_notified"])

    def test_new_overdue_issue_without_returned_url_stops_before_notification(self):
        row = {"pr": 42, "blocker": "conflict", "expires": "2026-08-01T00:00:00Z"}
        self.command.side_effect = [self.result("[]"), self.result("created")]
        with self.assertRaisesRegex(OSError, "did not return the new issue URL"):
            self.st.update_backlog_issue("owner/repo", [row], now=NOW)
        self.assertEqual(self.command.call_count, 2)

    def test_invalid_duplicate_backlog_listing_stops_before_any_write(self):
        """A valid first match must not hide a malformed later title match."""
        for number in (None, True, "52"):
            with self.subTest(number=number):
                self.command.reset_mock()
                self.command.return_value = self.result(
                    json.dumps(
                        [
                            {
                                "number": 51,
                                "title": self.st.BACKLOG_ISSUE_TITLE,
                                "body": "",
                            },
                            {"number": number, "title": self.st.BACKLOG_ISSUE_TITLE},
                        ]
                    )
                )
                with self.assertRaisesRegex(OSError, "without a number"):
                    self.st.update_backlog_issue(
                        "owner/repo", [self._backlog_row()], now=NOW
                    )
                self.command.assert_called_once()


if __name__ == "__main__":
    unittest.main()
