"""Unit tests for the extracted status issue renderer and GitHub boundary."""

from __future__ import annotations

import copy
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from io import StringIO
from unittest import mock

import pr_lifecycle_issue_status as issue_status

from tests.pr_lifecycle_helpers import NOW, import_lifecycle_run

run = import_lifecycle_run()


class IssueStatusTests(unittest.TestCase):
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

    def test_body_preserves_status_json_and_does_not_mutate_input(self) -> None:
        self.status["reason"] = "needs review\nwith Unicode: café"
        original = copy.deepcopy(self.status)
        body = self.st.issue_body(self.status)
        self.assertTrue(body.startswith("<!-- pr-lifecycle-status -->\n"))
        self.assertIn("signals_status: PARTIAL\ncondition: SIGNALS_DEGRADED\n", body)
        self.assertIn("calibration_enabled: false\n", body)
        encoded = body.split("```json\n", 1)[1].rsplit("\n```", 1)[0]
        self.assertEqual(json.loads(encoded), original)
        self.assertEqual(self.status, original)
        # The calibration line is a hardcoded invariant, not a field echo.
        self.status["calibration_enabled"] = True
        self.assertIn("calibration_enabled: false\n", self.st.issue_body(self.status))
        self.command.assert_not_called()

    def test_body_handles_minimal_status_without_condition(self) -> None:
        body = self.st.issue_body({"updated_at_utc": "2026-08-30T12:00:00Z"})
        header = body.split("```json", 1)[0]
        for field in (
            "run_id",
            "stage",
            "ledger_revision",
            "reason",
            "stop_class",
            "signals_status",
        ):
            with self.subTest(field=field):
                self.assertIn(f"{field}: \n", header)
        self.assertNotIn("condition:", header)

    def test_only_exact_title_match_is_edited_with_fixed_argv(self) -> None:
        rows = [
            {"number": 8, "title": "PR pipeline status archive"},
            {"number": 9, "title": "pr pipeline status"},
            {"number": 17, "title": "PR pipeline status"},
        ]
        self.status["reason"] = "$(touch sentinel); 'quoted'\n--repo other/repo"
        self.command.side_effect = [self.result(json.dumps(rows)), self.result()]
        self.st.update_pinned_issue(self.status)
        list_argv = self.command.call_args_list[0].args[0]
        edit_argv = self.command.call_args_list[1].args[0]
        self.assertEqual(
            list_argv,
            [
                "gh",
                "issue",
                "list",
                "--search",
                'in:title "PR pipeline status"',
                "--json",
                "number,title",
                "--state",
                "all",
                "--limit",
                "1000",
                "--repo",
                "abhimehro/personal-config",
            ],
        )
        self.assertEqual(edit_argv[:4], ["gh", "issue", "edit", "17"])
        # The body must carry the rendered status, not just any string.
        sent_body = edit_argv[edit_argv.index("--body") + 1]
        self.assertIn("<!-- pr-lifecycle-status -->", sent_body)
        self.assertIn(self.status["reason"], sent_body)
        self.assertIn('"run_id": "test-status"', sent_body)
        self.assertEqual(edit_argv[-2:], ["--repo", "abhimehro/personal-config"])

    def test_unmatched_listing_creates_status_issue(self) -> None:
        """A well-formed listing with no exact-title row is the only create path."""
        for listed in (
            self.result("[]"),
            self.result('[{"number": 7, "title": "PR pipeline status old"}]'),
            self.result('[{"number": 8, "title": "pr pipeline status"}]'),
        ):
            with self.subTest(stdout=listed.stdout):
                self.command.reset_mock()
                self.command.side_effect = [listed, self.result()]
                self.st.update_pinned_issue(self.status)
                self.assertEqual(self.command.call_count, 2)
                create_argv = self.command.call_args.args[0]
                self.assertEqual(
                    create_argv[:5],
                    ["gh", "issue", "create", "--title", "PR pipeline status"],
                )
                sent_body = create_argv[create_argv.index("--body") + 1]
                self.assertIn("<!-- pr-lifecycle-status -->", sent_body)
                self.assertIn('"run_id": "test-status"', sent_body)
                self.assertEqual(
                    create_argv[-2:], ["--repo", "abhimehro/personal-config"]
                )

    def test_failed_or_malformed_listing_raises_before_any_create(self) -> None:
        """Untrusted listings fail closed rather than duplicate the pinned issue."""
        for listed in (
            self.result("[]", returncode=1, stderr="gh unavailable"),
            self.result('[{"number": 7, "title": "PR pipeline status"}]', returncode=1),
            self.result(" \n"),
            self.result("not-json"),
            self.result('{"number": 7, "title": "PR pipeline status"}'),
            self.result('["not-a-row"]'),
            self.result('[{"number": null, "title": "PR pipeline status"}]'),
            self.result('[{"number": "17", "title": "PR pipeline status"}]'),
        ):
            with self.subTest(stdout=listed.stdout, returncode=listed.returncode):
                self.command.reset_mock()
                self.command.side_effect = [listed]
                with self.assertRaises(OSError):
                    self.st.update_pinned_issue(self.status)
                self.command.assert_called_once()

    def test_failed_create_and_edit_raise_bounded_error_without_retry(self) -> None:
        for rows, operation in (
            ([], "create"),
            ([{"number": 17, "title": "PR pipeline status"}], "edit"),
        ):
            with self.subTest(operation=operation):
                self.command.reset_mock()
                self.command.side_effect = [
                    self.result(json.dumps(rows)),
                    self.result(returncode=2, stderr="  " + "x" * 250 + "  "),
                ]
                with self.assertRaises(OSError) as caught:
                    self.st.update_pinned_issue(self.status)
                self.assertEqual(
                    str(caught.exception), "gh issue update failed rc=2: " + "x" * 200
                )
                self.assertEqual(self.command.call_count, 2)
                self.assertEqual(self.command.call_args.args[0][2], operation)

    def test_process_exception_stops_before_any_issue_mutation(self) -> None:
        for error in (
            FileNotFoundError("gh missing"),
            subprocess.TimeoutExpired(["gh"], 60),
        ):
            with self.subTest(error=type(error).__name__):
                self.command.reset_mock()
                self.command.side_effect = error
                with self.assertRaises(type(error)):
                    self.st.update_pinned_issue(self.status)
                self.command.assert_called_once()
                self.assertEqual(self.command.call_args.args[0][2], "list")

    def test_backlog_body_renders_decision_table_and_state_block(self) -> None:
        """Render decision rows with a durable first-seen state block."""
        now = NOW
        row = {
            "pr": 42,
            "url": "https://github.com/owner/repo/pull/42",
            "blocker": "required_check_failure",
            "evidence": "Build failed",
            "recommended_action": "Fix checks",
            "safe_default": "Leave open",
            "owner": "human",
            "packet_expiry_close_days": 7,
        }
        body = self.st.backlog_issue_body(
            self.st._BacklogSpec("owner/repo", {}, now), [row]
        )
        self.assertIn("<!-- pr-lifecycle-backlog -->", body)
        self.assertIn("| PR | Blocker | Evidence |", body)
        self.assertIn("[42](https://github.com/owner/repo/pull/42)", body)
        self.assertIn("required_check_failure", body)
        state = json.loads(
            body.split("<!-- pr-lifecycle-backlog-state ", 1)[1].split(" -->", 1)[0]
        )
        self.assertEqual(
            state["first_seen"]["owner/repo#42:required_check_failure"],
            "2026-08-30T12:00:00Z",
        )

    def test_backlog_cells_neutralize_comment_markers_and_mentions(self) -> None:
        """Prevent row text from injecting hidden state markers or user mentions."""
        rendered = self.st._markdown_cell(
            "<!-- pr-lifecycle-backlog-state {} --> @someone"
        )
        self.assertNotIn("<!--", rendered)
        self.assertNotIn("-->", rendered)
        self.assertNotIn("@someone", rendered)

    def test_previous_state_uses_the_last_state_block(self) -> None:
        """Read the final state block when earlier blocks are present in the body."""
        forged = {
            "first_seen": {"forged": "2026-01-01T00:00:00Z"},
            "overdue_notified": ["forged"],
        }
        real = {
            "first_seen": {"real": "2026-02-01T00:00:00Z"},
            "overdue_notified": ["real"],
        }
        body = (
            "<!-- pr-lifecycle-backlog-state "
            + json.dumps(forged)
            + " -->\n<!-- pr-lifecycle-backlog-state "
            + json.dumps(real)
            + " -->"
        )
        self.assertEqual(self.st._previous_state(body), real)

    def test_overdue_comment_neutralizes_row_text_but_keeps_our_mention(self) -> None:
        """Sanitize row content while retaining the intended owner notification."""
        repo = "owner/repo"
        row = {
            "pr": 42,
            "url": "https://github.com/owner/repo/pull/42/<!-- forged -->@someone",
            "blocker": "<!-- forged --> @someone",
            "evidence": "late",
            "recommended_action": "review",
            "safe_default": "leave open",
            "owner": "human",
            "expires": "2026-08-20T00:00:00Z",
        }
        old_body = self.st.backlog_issue_body(
            self.st._BacklogSpec(repo, {}, NOW - timedelta(days=20)), [row]
        )
        self.command.side_effect = [
            self.result(
                json.dumps(
                    [
                        {
                            "number": 51,
                            "title": self.st.BACKLOG_ISSUE_TITLE,
                            "body": old_body,
                        }
                    ]
                )
            ),
            self.result(),
            self.result(),
        ]
        self.st.update_backlog_issue(repo, [row], now=NOW)
        comment_body = self.command.call_args_list[1].args[0][
            self.command.call_args_list[1].args[0].index("--body") + 1
        ]
        self.assertIn("@abhimehro 1 item(s)", comment_body)
        self.assertNotIn("@someone", comment_body)
        self.assertNotIn("<!--", comment_body)
        self.assertNotIn("-->", comment_body)

    def test_backlog_deduplicates_by_pr_and_blocker_without_mutating_inputs(self):
        rows = [
            {"pr": 42, "blocker": "conflict"},
            {"pr": 42, "blocker": "conflict", "evidence": "duplicate"},
            {"pr": 42, "blocker": "security"},
        ]
        state = {"first_seen": {}, "overdue_notified": []}
        before = copy.deepcopy((rows, state))
        prepared, refreshed, overdue = self.st._prepare_backlog_rows(
            self.st._BacklogSpec("owner/repo", state, NOW), rows
        )
        self.assertEqual(
            [row["id"] for row in prepared],
            [
                "owner/repo#42:conflict",
                "owner/repo#42:security",
            ],
        )
        self.assertEqual(set(refreshed["first_seen"]), {row["id"] for row in prepared})
        self.assertEqual(overdue, [])
        self.assertEqual((rows, state), before)

    def test_backlog_expiry_is_inclusive_and_normalizes_timezones(self):
        for expires, expected in (
            ("2026-08-30T12:00:01Z", False),
            ("2026-08-30T12:00:00Z", True),
            ("2026-08-30T14:00:00+02:00", True),
        ):
            with self.subTest(expires=expires):
                prepared, state, overdue = self.st._prepare_backlog_rows(
                    self.st._BacklogSpec("owner/repo", {}, NOW),
                    [{"pr": 42, "blocker": "conflict", "expires": expires}],
                )
                self.assertEqual(prepared[0]["overdue"], expected)
                self.assertEqual(len(overdue), int(expected))
                self.assertEqual(len(state["overdue_notified"]), int(expected))

    def test_invalid_first_seen_and_expiry_recover_to_default_deadline(self):
        key = "owner/repo#42:conflict"
        for expires in (None, "invalid"):
            with self.subTest(expires=expires):
                rows = [
                    {
                        "pr": 42,
                        "blocker": "conflict",
                        "expires": expires,
                        "packet_expiry_close_days": True,
                    }
                ]
                prepared, state, overdue = self.st._prepare_backlog_rows(
                    self.st._BacklogSpec(
                        "owner/repo", {"first_seen": {key: "invalid"}}, NOW
                    ),
                    rows,
                )
                self.assertEqual(state["first_seen"][key], "2026-08-30T12:00:00Z")
                self.assertEqual(prepared[0]["expires"], "2026-09-06T12:00:00Z")
                self.assertEqual(overdue, [])

    def test_invalid_packet_days_default_to_seven_without_boolean_coercion(self):
        for days in (True, False, 0, -1, "2", 1.5):
            with self.subTest(days=days):
                row = dict(self._backlog_row(), packet_expiry_close_days=days)
                prepared, _, overdue = self.st._prepare_backlog_rows(
                    self.st._BacklogSpec("owner/repo", {}, NOW),
                    [row],
                )
                self.assertEqual(prepared[0]["expires"], "2026-09-06T12:00:00Z")
                self.assertFalse(prepared[0]["overdue"])
                self.assertEqual(overdue, [])

    def test_unsafe_link_destinations_do_not_escape_the_backlog_table(self):
        for url in (
            "http://example.com/pr/42",
            "javascript:alert(1)",
            "https://example.com/42) [injected](https://evil.example)",
            "https://example.com/42\n<!-- injected -->",
        ):
            with self.subTest(url=url):
                body = self.st.backlog_issue_body(
                    self.st._BacklogSpec("owner/repo", {}, NOW),
                    [dict(self._backlog_row(), url=url)],
                )
                self.assertIn("| 42 |", body)
                self.assertNotIn(url, body)
                self.assertNotIn("[injected]", body)


class RunStatusCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = run

    def test_status_cli_takes_precedence_over_stage(self) -> None:
        output = StringIO()
        with (
            mock.patch.object(self.runner, "update_pinned_issue") as update,
            mock.patch.object(self.runner, "run_stage") as stage,
            mock.patch.object(self.runner, "_utc_now", return_value=NOW),
            mock.patch.object(self.runner, "_run_id", return_value="manual-status"),
            redirect_stdout(output),
        ):
            code = self.runner.main(["--status", "--stage", "1"])
        self.assertEqual(code, 0)
        status = json.loads(output.getvalue())
        self.assertEqual(status["updated_at_utc"], "2026-08-30T12:00:00Z")
        self.assertEqual(status["run_id"], "manual-status")
        self.assertIsNone(status["stage"])
        self.assertEqual(status["signals_status"], "SKIPPED")
        self.assertFalse(status["calibration_enabled"])
        update.assert_called_once_with(status)
        stage.assert_not_called()

    def test_status_cli_failure_reports_type_without_provider_details(self) -> None:
        for error, expected in (
            (OSError("provider-private-details"), "OSError"),
            # subprocess.TimeoutExpired is a SubprocessError, not an OSError;
            # a gh timeout must still exit 1 rather than traceback.
            (subprocess.TimeoutExpired(["gh"], 60), "TimeoutExpired"),
        ):
            with self.subTest(error=type(error).__name__):
                error_output, output = StringIO(), StringIO()
                with (
                    mock.patch.object(
                        run,
                        "update_pinned_issue",
                        side_effect=error,
                    ),
                    mock.patch.object(self.runner, "run_stage") as stage,
                    redirect_stderr(error_output),
                    redirect_stdout(output),
                ):
                    code = self.runner.main(["--status"])
                self.assertEqual(code, 1)
                self.assertEqual(
                    error_output.getvalue(),
                    f"PR_LIFECYCLE_RUN_ERROR: {expected}\n",
                )
                self.assertEqual(output.getvalue(), "")
                stage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
