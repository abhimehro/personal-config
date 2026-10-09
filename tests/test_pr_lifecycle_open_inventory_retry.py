"""Tests for retry/backoff behavior of the open-PR inventory fetch."""

from __future__ import annotations

import json
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_open_inventory as inventory

from tests.pr_lifecycle_helpers import (
    make_inventory_payload,
    make_inventory_pr,
)


class OpenInventoryRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = types.SimpleNamespace(
            inv=inventory,
            make_pr=make_inventory_pr,
            payload=make_inventory_payload,
        )

    def test_retries_transient_failures_then_succeeds(self):
        """Retry transient process or JSON failures with the configured timeout."""
        valid = subprocess.CompletedProcess(
            ["gh"], 0, json.dumps(self.fx.payload([self.fx.make_pr()])), ""
        )
        failures = (
            subprocess.CompletedProcess(["gh"], 1, "", "temporary failure"),
            subprocess.TimeoutExpired(["gh"], 120),
            OSError("temporary process failure"),
            subprocess.CompletedProcess(["gh"], 0, "{bad", ""),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                responses = [failure, valid]
                sleeps = []
                timeouts = []

                def run(
                    _argv,
                    *,
                    _responses=responses,
                    _timeouts=timeouts,
                    **kwargs,
                ):
                    """Record the timeout and replay the next transient failure or response."""
                    _timeouts.append(kwargs["timeout"])
                    response = _responses.pop(0)
                    if isinstance(response, BaseException):
                        raise response
                    return response

                prs = self.fx.inv.list_open_prs(
                    "owner/repo", run=run, sleep=sleeps.append
                )
                self.assertEqual([pr["number"] for pr in prs], [12])
                self.assertEqual(sleeps, [2])
                self.assertEqual(timeouts, [120, 120])

    def test_retry_exhaustion_without_recorded_error_has_deliberate_fallback(self):
        import pr_lifecycle_inventory_pages as pages

        run = mock.Mock()
        sleep = mock.Mock()
        with mock.patch.object(pages, "range", return_value=(), create=True):
            with self.assertRaisesRegex(OSError, "without a recorded error"):
                pages._graphql_page(["gh"], run=run, sleep=sleep)
        run.assert_not_called()
        sleep.assert_not_called()

    def test_three_transient_failures_raise_oserror(self):
        """Stop after three failed attempts with two backoff delays."""
        failures = [
            subprocess.CompletedProcess(["gh"], 1, "", "temporary failure")
            for _ in range(3)
        ]
        sleeps = []
        with self.assertRaisesRegex(OSError, "rc=1"):
            self.fx.inv.list_open_prs(
                "owner/repo",
                run=lambda *_a, **_k: failures.pop(0),
                sleep=sleeps.append,
            )
        self.assertEqual(sleeps, [2, 4])

    def test_graphql_errors_are_not_retried(self):
        """Raise GraphQL API errors immediately without another request or sleep."""
        result = subprocess.CompletedProcess(
            ["gh"],
            0,
            json.dumps({"errors": [{"message": "API error"}]}),
            "",
        )
        calls = []
        sleeps = []
        with self.assertRaisesRegex(OSError, "API error"):
            self.fx.inv.list_open_prs(
                "owner/repo",
                run=lambda *_a, **_k: calls.append(1) or result,
                sleep=sleeps.append,
            )
        self.assertEqual(calls, [1])
        self.assertEqual(sleeps, [])

    def test_transient_graphql_errors_retry_then_succeed(self):
        rate_limited = subprocess.CompletedProcess(
            ["gh"],
            0,
            json.dumps({"errors": [{"message": "API rate limit exceeded"}]}),
            "",
        )
        valid = subprocess.CompletedProcess(
            ["gh"], 0, json.dumps(self.fx.payload([self.fx.make_pr()])), ""
        )
        responses = [rate_limited, valid]
        sleeps = []
        prs = self.fx.inv.list_open_prs(
            "owner/repo",
            run=lambda *_a, **_k: responses.pop(0),
            sleep=sleeps.append,
        )
        self.assertEqual([pr["number"] for pr in prs], [12])
        self.assertEqual(sleeps, [2])

    def test_persistent_transient_graphql_errors_raise_oserror(self):
        result = subprocess.CompletedProcess(
            ["gh"],
            0,
            json.dumps({"errors": [{"message": "API rate limit exceeded"}]}),
            "",
        )
        sleeps = []
        with self.assertRaisesRegex(OSError, "rate limit"):
            self.fx.inv.list_open_prs(
                "owner/repo",
                run=lambda *_a, **_k: result,
                sleep=sleeps.append,
            )
        self.assertEqual(sleeps, [2, 4])

    def test_graphql_retries_require_every_error_to_be_transient(self):
        """Permanent, unknown, and malformed errors prevent retries."""
        for errors in (
            [{"message": "rate limit exceeded"}, {"message": "access denied"}],
            [{"type": "INTERNAL"}, {"type": "FORBIDDEN"}],
            [{"type": "FORBIDDEN", "message": "internal resource unavailable"}],
            [{"type": "UNKNOWN", "message": "timeout"}],
            [{"type": [], "message": "timeout"}],
            [{"message": "rate"}, {"message": "limit"}],
            [{"message": "timeout"}, None],
            [{"message": ["timeout"]}],
            [],
            None,
            {"message": "timeout"},
        ):
            with self.subTest(errors=errors):
                result = subprocess.CompletedProcess(
                    ["gh"], 0, json.dumps({"errors": errors}), ""
                )
                run = mock.Mock(return_value=result)
                sleep = mock.Mock()
                with self.assertRaisesRegex(OSError, "API error"):
                    self.fx.inv.list_open_prs("owner/repo", run=run, sleep=sleep)
                run.assert_called_once()
                sleep.assert_not_called()

    def test_graphql_structured_types_and_untyped_messages_allow_retries(self):
        """Known transient types work without message markers; all errors count."""
        for errors in (
            [{"type": "RATE_LIMITED", "message": "request rejected"}],
            [{"type": "INTERNAL"}],
            [{"type": "SERVICE_UNAVAILABLE"}],
            [{"type": "TIMEOUT"}],
            [{"type": "INTERNAL"}, {"message": "Temporarily unavailable"}],
            [{"message": "rate limit exceeded"}, {"message": "timed out"}],
        ):
            with self.subTest(errors=errors):
                run = mock.Mock(
                    side_effect=[
                        subprocess.CompletedProcess(
                            ["gh"], 0, json.dumps({"errors": errors}), ""
                        ),
                        subprocess.CompletedProcess(
                            ["gh"],
                            0,
                            json.dumps(self.fx.payload([self.fx.make_pr()])),
                            "",
                        ),
                    ]
                )
                sleep = mock.Mock()
                prs = self.fx.inv.list_open_prs("owner/repo", run=run, sleep=sleep)
                self.assertEqual([pr["number"] for pr in prs], [12])
                self.assertEqual(run.call_count, 2)
                sleep.assert_called_once_with(2)

    def test_api_and_shape_errors_raise_oserror(self):
        """Reject GraphQL errors and malformed inventory response shapes."""
        for payload in (
            {"errors": [{"message": "partial API failure"}]},
            {"data": {"repository": {"pullRequests": {"nodes": []}}}},
        ):
            result = subprocess.CompletedProcess(["gh"], 0, json.dumps(payload), "")
            with self.subTest(payload=payload), self.assertRaises(OSError):
                self.fx.inv.list_open_prs(
                    "owner/repo",
                    run=lambda *_a, _result=result, **_k: _result,
                )

    def test_retry_budget_resets_for_each_page(self):
        failure = subprocess.CompletedProcess(["gh"], 1, "", "retry")
        run = mock.Mock(
            side_effect=[
                failure,
                failure,
                subprocess.CompletedProcess(
                    ["gh"],
                    0,
                    json.dumps(self.fx.payload([self.fx.make_pr()], next_page=True)),
                    "",
                ),
                failure,
                failure,
                subprocess.CompletedProcess(
                    ["gh"], 0, json.dumps(self.fx.payload([self.fx.make_pr(13)])), ""
                ),
            ]
        )
        sleep = mock.Mock()
        prs = self.fx.inv.list_open_prs("owner/repo", run=run, sleep=sleep)
        self.assertEqual([pr["number"] for pr in prs], [12, 13])
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(4)] * 2)
        self.assertEqual(run.call_count, 6)


if __name__ == "__main__":
    unittest.main()
