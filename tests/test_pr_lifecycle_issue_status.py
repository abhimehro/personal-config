"""Unit tests for the extracted status issue renderer and GitHub boundary."""

from __future__ import annotations

import copy
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import mock

from tests.pr_lifecycle_helpers import NOW, import_lifecycle_run

import pr_lifecycle_issue_status as issue_status

run = import_lifecycle_run()


class IssueStatusTests(unittest.TestCase):
    def setUp(self) -> None:
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
        self.command = self.enterContext(
            mock.patch.object(issue_status.subprocess, "run")
        )

    @staticmethod
    def result(
        stdout: str = "", returncode: int = 0, stderr: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)

    def test_body_preserves_status_json_and_does_not_mutate_input(self) -> None:
        self.status["reason"] = "needs review\nwith Unicode: café"
        original = copy.deepcopy(self.status)
        body = issue_status.issue_body(self.status)
        self.assertTrue(body.startswith("<!-- pr-lifecycle-status -->\n"))
        self.assertIn("signals_status: PARTIAL\ncondition: SIGNALS_DEGRADED\n", body)
        self.assertIn("calibration_enabled: false\n", body)
        encoded = body.split("```json\n", 1)[1].rsplit("\n```", 1)[0]
        self.assertEqual(json.loads(encoded), original)
        self.assertEqual(self.status, original)
        # The calibration line is a hardcoded invariant, not a field echo.
        self.status["calibration_enabled"] = True
        self.assertIn(
            "calibration_enabled: false\n", issue_status.issue_body(self.status)
        )
        self.command.assert_not_called()

    def test_body_handles_minimal_status_without_condition(self) -> None:
        body = issue_status.issue_body({"updated_at_utc": "2026-08-30T12:00:00Z"})
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
        issue_status.update_pinned_issue(self.status)
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
                "--limit",
                "20",
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
                issue_status.update_pinned_issue(self.status)
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
                    issue_status.update_pinned_issue(self.status)
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
                    issue_status.update_pinned_issue(self.status)
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
                    issue_status.update_pinned_issue(self.status)
                self.command.assert_called_once()
                self.assertEqual(self.command.call_args.args[0][2], "list")

    def test_status_cli_takes_precedence_over_stage(self) -> None:
        output = StringIO()
        with (
            mock.patch.object(run, "update_pinned_issue") as update,
            mock.patch.object(run, "run_stage") as stage,
            mock.patch.object(run, "_utc_now", return_value=NOW),
            mock.patch.object(run, "_run_id", return_value="manual-status"),
            redirect_stdout(output),
        ):
            code = run.main(["--status", "--stage", "1"])
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
                    mock.patch.object(run, "run_stage") as stage,
                    redirect_stderr(error_output),
                    redirect_stdout(output),
                ):
                    code = run.main(["--status"])
                self.assertEqual(code, 1)
                self.assertEqual(
                    error_output.getvalue(),
                    f"PR_LIFECYCLE_RUN_ERROR: {expected}\n",
                )
                self.assertEqual(output.getvalue(), "")
                stage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
