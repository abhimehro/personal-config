"""Decision-issue checkbox dispositions: parsing, editor gate, head-sha tie."""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pr_lifecycle_dispositions as dispositions
import pr_lifecycle_issue_status as issue_status

REPO = "owner/repo"
NOW = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)


def _ledger() -> dict:
    return {
        "items": [
            {
                "key": f"{REPO}#42@abc1234",
                "repository": REPO,
                "pr": 42,
                "revision": 3,
                "lifecycle_state": "STAGE3_RECONCILIATION",
                "current_owner": "human",
                "next_owner": "human",
                "guardrail_outcome": "REVIEW_SECURITY",
                "terminal_disposition": None,
                "handoffs": [],
            }
        ],
        "events": [],
    }


def _issue(body: str, number: int = 7) -> dict:
    return {"number": number, "title": issue_status.BACKLOG_ISSUE_TITLE, "body": body}


def _state(head: str = "abc1234") -> dict:
    return {
        "first_seen": {},
        "overdue_notified": [],
        "rows_meta": {
            f"{REPO}#42": {"head_sha": head, "suggested_disposition": "CLOSED_STALE"}
        },
    }


class _Run:
    """Fake subprocess.run routing gh calls."""

    def __init__(self, editor="abhimehro", live=None, close_rc=0, total=None):
        self.editor = editor
        self.live = live or {"state": "OPEN", "headRefOid": "abc1234"}
        self.close_rc = close_rc
        self.total = total
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        out = ""
        if cmd[:3] == ["gh", "api", "graphql"]:
            edits: dict = {"nodes": [{"editor": {"login": self.editor}}]}
            if self.total is not None:
                edits["totalCount"] = self.total
            out = json.dumps(
                {"data": {"repository": {"issue": {"userContentEdits": edits}}}}
            )
        elif cmd[:3] == ["gh", "pr", "view"]:
            out = json.dumps(self.live)
        elif cmd[:3] == ["gh", "pr", "close"]:
            return _Done(self.close_rc)
        return _Done(0, out)


class _Done:
    def __init__(self, rc=0, stdout=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = ""


class ParseTickTests(unittest.TestCase):
    def test_unticked_and_ticked_rows(self):
        body = (
            "- [ ] **owner/repo#1** — suggested `CLOSED_STALE` · head `aaaaaaa`\n"
            "- [x] **owner/repo#2** — suggested `KEEP_OPEN` · head `bbbbbbb`\n"
            "- [X] **owner/repo#3** — `CLOSED_DUPLICATE` · head `ccccccc`\n"
        )
        ticks = dispositions.parse_ticks(body)
        self.assertEqual([t["row_id"] for t in ticks], ["owner/repo#2", "owner/repo#3"])
        self.assertEqual(ticks[1]["token"], "CLOSED_DUPLICATE")

    def test_no_edit_history_means_no_execution(self):
        run = _Run(editor=None)
        body = f"- [x] **{REPO}#42** — `CLOSED_STALE`\n"
        ctx = dispositions.ExecCtx(REPO, _issue(body), _ledger(), _state(), run)
        result = dispositions.execute(ctx)
        self.assertEqual(result["accepted"], [])
        self.assertIn("not abhimehro", result["reason"])

    def test_ticked_row_without_token_falls_back(self):
        ticks = dispositions.parse_ticks("- [x] **owner/repo#2** — no token\n")
        self.assertEqual(ticks, [{"row_id": "owner/repo#2", "token": None}])

    def test_null_editor_fields_return_empty(self):
        self.assertEqual(dispositions.editors(REPO, 7, run=_Run(editor=None)), set())

    def test_truncated_editor_history_is_refused(self):
        run = _Run(total=150)
        body = f"- [x] **{REPO}#42** — `CLOSED_STALE`\n"
        ctx = dispositions.ExecCtx(REPO, _issue(body), _ledger(), _state(), run)
        result = dispositions.execute(ctx)
        self.assertEqual(result["accepted"], [])
        self.assertIn("unreadable", result["reason"])


class ExecuteTests(unittest.TestCase):
    def _run(self, body, live=None, **kw):
        run = _Run(**kw)
        live = live or {"state": "OPEN", "headRefOid": "abc1234"}
        ledger = _ledger()
        ctx = dispositions.ExecCtx(REPO, _issue(body), ledger, _state(), run)
        with mock.patch.object(dispositions, "_gh_pr_view", lambda repo, pr: live):
            result = dispositions.execute(ctx)
        return result, run, ledger

    def test_editor_gate_rejects_other_users(self):
        body = f"- [x] **{REPO}#42** — `CLOSED_STALE`\n"
        result, _, _ = self._run(body, editor="other-user")
        self.assertEqual(result["accepted"], [])
        self.assertIn("not abhimehro", result["reason"])

    def test_head_moved_ignores_tick(self):
        body = f"- [x] **{REPO}#42** — `CLOSED_STALE`\n"
        result, _, _ = self._run(body, live={"state": "OPEN", "headRefOid": "deadbeef"})
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["skipped"][0]["skipped"], "head moved since rendered")

    def test_close_disposition_terminates_with_event(self):
        body = f"- [x] **{REPO}#42** — `CLOSED_STALE`\n"
        result, run, ledger = self._run(body)
        item = ledger["items"][0]
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(item["lifecycle_state"], "TERMINAL")
        self.assertEqual(item["terminal_disposition"], "CLOSED_STALE")
        self.assertEqual(item["revision"], 4)
        self.assertEqual(len(ledger["events"]), 1)
        self.assertIn(["gh", "pr", "close", "42", "--repo", REPO], run.calls)

    def test_keep_open_hands_back_to_human_without_close(self):
        body = f"- [x] **{REPO}#42** — `KEEP_OPEN`\n"
        result, run, ledger = self._run(body)
        item = ledger["items"][0]
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(item["lifecycle_state"], "WAITING_HUMAN")
        self.assertIsNone(item["terminal_disposition"])
        self.assertNotIn(["gh", "pr", "close", "42", "--repo", REPO], run.calls)

    def test_keep_open_on_closed_pr_is_skipped(self):
        body = f"- [x] **{REPO}#42** — `KEEP_OPEN`\n"
        result, _, ledger = self._run(
            body, live={"state": "MERGED", "headRefOid": "abc1234"}
        )
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["skipped"][0]["skipped"], "PR no longer open")
        self.assertEqual(ledger["items"][0]["lifecycle_state"], "STAGE3_RECONCILIATION")

    def test_cross_repo_row_is_skipped(self):
        body = "- [x] **other/repo#42** — `CLOSED_STALE`\n"
        result, run, _ = self._run(body)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["skipped"][0]["skipped"], "row repository mismatch")
        self.assertNotIn(["gh", "pr", "close", "42", "--repo", "other/repo"], run.calls)

    def test_unknown_row_and_terminal_item_are_skipped(self):
        body = (
            "- [x] **owner/repo#99** — `CLOSED_STALE`\n"
            "- [x] **owner/repo#42** — `CLOSED_STALE`\n"
        )
        result, _, ledger = self._run(body)
        ledger["items"][0]["lifecycle_state"] = "TERMINAL"
        ctx = dispositions.ExecCtx(REPO, _issue(body), ledger, _state(), _Run())
        with mock.patch.object(
            dispositions, "_gh_pr_view", lambda repo, pr: {"state": "OPEN"}
        ):
            second = dispositions.execute(ctx)
        self.assertEqual(
            [s.get("skipped") for s in second["skipped"]],
            ["unknown row", "unknown row"],
        )
        self.assertEqual(result["accepted"][0]["pr"], 42)
        self.assertEqual(len(ledger["events"]), 1)


class RenderedDecisionsTests(unittest.TestCase):
    def test_decision_lines_render_checkbox_head_and_suggestion(self):
        spec = issue_status._BacklogSpec(REPO, {}, issue_status._utc(NOW))
        rows = [
            {
                "pr": 42,
                "blocker": "REVIEW_SECURITY",
                "head_sha": "abc1234def",
                "suggested_disposition": "CLOSED_STALE",
            }
        ]
        body = issue_status.backlog_issue_body(spec, rows)
        self.assertIn("- [ ] **owner/repo#42**", body)
        self.assertIn("`CLOSED_STALE`", body)
        self.assertIn("`abc1234`", body)
        state = json.loads(
            body.split("<!-- pr-lifecycle-backlog-state ", 1)[1].split(" -->", 1)[0]
        )
        self.assertEqual(state["rows_meta"]["owner/repo#42"]["head_sha"], "abc1234def")

    def test_legacy_blocker_keys_migrate_to_pr_keys(self):
        body = (
            "<!-- pr-lifecycle-backlog-state "
            + json.dumps(
                {
                    "first_seen": {"owner/repo#42:conflict": "2026-01-01T00:00:00Z"},
                    "overdue_notified": ["owner/repo#42:conflict"],
                }
            )
            + " -->"
        )
        state = issue_status._previous_state(body)
        self.assertEqual(state["first_seen"], {"owner/repo#42": "2026-01-01T00:00:00Z"})
        self.assertEqual(state["overdue_notified"], ["owner/repo#42"])

    def test_no_decision_header_without_tickable_rows(self):
        spec = issue_status._BacklogSpec(REPO, {}, issue_status._utc(NOW))
        body = issue_status.backlog_issue_body(
            spec, [{"pr": 42, "blocker": "some blocker"}]
        )
        self.assertNotIn("tick a checkbox", body)


if __name__ == "__main__":
    unittest.main()
