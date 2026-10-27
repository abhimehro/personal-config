"""Replay counts for the guardrail classifier. No network."""

from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrail_replay as replay  # noqa: E402
import pr_lifecycle_guardrails as guardrails  # noqa: E402

from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


def _evidence(
    title: str, head_ref: str, diff_text: str = "", *, head_sha: str | None = None
) -> guardrails.GuardrailEvidence:
    return guardrails.GuardrailEvidence(
        diff_text=diff_text,
        head_sha=head_sha,
        diff_sha256=guardrails.diff_sha256(diff_text) if diff_text else None,
        title=title,
        head_ref=head_ref,
        required_checks_green=True,
        mergeable=True,
    )


def _rules_and_sentinel_scenario():
    journal = _item(
        key="abhimehro/demo#1@" + "a" * 40,
        repository="abhimehro/demo",
        pr=1,
        url="https://github.com/abhimehro/demo/pull/1",
        classification="SECURITY",
        guardrail_outcome="REVIEW_SECURITY",
        sensitive_paths=["generated_output"],
        changed_paths=[".jules/sentinel.md"],
    )
    labeled = _item(
        key="abhimehro/demo#2@" + "b" * 40,
        repository="abhimehro/demo",
        pr=2,
        url="https://github.com/abhimehro/demo/pull/2",
        classification="UNKNOWN",
        guardrail_outcome="REVIEW_SECURITY",
        sensitive_paths=[],
        changed_paths=["README.md"],
    )
    shell = _item(
        key="abhimehro/demo#3@" + "c" * 40,
        repository="abhimehro/demo",
        pr=3,
        url="https://github.com/abhimehro/demo/pull/3",
        classification="SECURITY",
        guardrail_outcome="REVIEW_SECURITY",
        changed_paths=["src/main.py"],
    )
    sha = "0123456789abcdef0123456789abcdef01234567"
    dependabot = _item(
        key="abhimehro/demo#4@" + "d" * 40,
        repository="abhimehro/demo",
        pr=4,
        url="https://github.com/abhimehro/demo/pull/4",
        classification="SECURITY",
        guardrail_outcome="REVIEW_SECURITY",
        changed_paths=[".github/workflows/ci.yml"],
        author={"login": "dependabot[bot]", "identity_source": "github_api"},
    )
    evidence = {
        journal["key"]: _evidence("Sentinel: journal note", "jules/note"),
        labeled["key"]: _evidence("docs only", "chore/docs"),
        shell["key"]: _evidence(
            "Sentinel: stop shelling out",
            "sentinel/fix-shell",
            diff_text=(
                "diff --git a/src/main.py b/src/main.py\n"
                "+++ b/src/main.py\n"
                "@@\n"
                "+subprocess.run(cmd, shell=True)\n"
            ),
        ),
        dependabot["key"]: _evidence(
            "Bump actions/checkout from 4.1.1 to 4.1.2",
            "dependabot/github_actions/checkout-4.1.2",
            diff_text=(
                "diff --git a/.github/workflows/ci.yml "
                "b/.github/workflows/ci.yml\n"
                "+++ b/.github/workflows/ci.yml\n"
                "@@\n"
                f"+        uses: actions/checkout@{sha}\n"
            ),
            head_sha=dependabot["head_sha"],
        ),
    }
    return [journal, labeled, shell, dependabot], evidence


class ReplayItemsTests(unittest.TestCase):
    def test_empty_and_non_item_entries_have_no_moves(self) -> None:
        for items in ([], [None, "invalid", 42, []]):
            with self.subTest(items=items):
                report = replay.replay_items(items, {})
                self.assertEqual(0, report["unique_move_count"])
                self.assertEqual([], report["fetch_failed"])
                self.assertEqual([], report["sentinel_persona"])
                self.assertEqual(
                    {
                        "classification_without_sensitive_path",
                        "jules_journal",
                        "dependabot_routine",
                    },
                    set(report["rules"]),
                )
                for rule in report["rules"].values():
                    self.assertEqual({"count": 0, "items": []}, rule)

    def test_failed_fetch_is_reported_and_does_not_count_as_a_move(self) -> None:
        item = _item(guardrail_outcome="REVIEW_SECURITY", classification="SECURITY")
        before = copy.deepcopy(item)
        report = replay.replay_items(
            [item], {item["key"]: guardrails.GuardrailEvidence(diff_fetch_failed=True)}
        )
        self.assertEqual([item["key"]], report["fetch_failed"])
        self.assertEqual(0, report["unique_move_count"])
        self.assertEqual(before, item)

    def test_standin_is_audited_without_live_title_and_preserves_protected_items(
        self,
    ) -> None:
        standin = _item(
            guardrail_source="manual",
            guardrail_outcome="REVIEW_SECURITY",
            next_action="Stage 1: SECURITY-THEMED SENTINEL TITLE; review",
            changed_paths=[".jules/sentinel.md"],
        )
        human = _item(
            key="owner/repo#2@def",
            author_type="HUMAN",
            guardrail_outcome="REVIEW_SECURITY",
        )
        items = [standin, human]
        before = copy.deepcopy(items)
        report = replay.replay_items(items, {})
        self.assertEqual(1, report["unique_move_count"])
        self.assertEqual(1, len(report["sentinel_persona"]))
        row = report["sentinel_persona"][0]
        self.assertTrue(row["morning_reflagged"])
        self.assertIsNone(row["title"])
        self.assertIsNone(row["head_ref"])
        self.assertEqual("PASS_ROUTINE", row["new"])
        self.assertEqual([], row["sensitive_paths"])
        self.assertEqual(before, items)

    def test_new_routine_items_are_not_counted_as_cleared_holds(self) -> None:
        report = replay.replay_items([_item(guardrail_outcome="NOT_RUN")], {})
        self.assertEqual(0, report["unique_move_count"])

    def test_rules_and_sentinel_table_use_paths_and_diff_not_the_title(self) -> None:
        items, evidence = _rules_and_sentinel_scenario()
        report = replay.replay_items(items, evidence)
        self.assertEqual(1, report["rules"]["jules_journal"]["count"])
        self.assertEqual(
            1, report["rules"]["classification_without_sensitive_path"]["count"]
        )
        self.assertEqual(1, report["rules"]["dependabot_routine"]["count"])
        self.assertEqual(3, report["unique_move_count"])
        by_pr = {row["pr"]: row for row in report["sentinel_persona"]}
        self.assertEqual({"1", "3"}, {str(pr) for pr in by_pr})
        self.assertEqual("PASS_ROUTINE", by_pr[1]["new"])
        self.assertEqual("REVIEW_SECURITY", by_pr[1]["old"])
        self.assertEqual("REVIEW_SECURITY", by_pr[3]["new"])
        self.assertIn("shell_execution", by_pr[3]["sensitive_paths"])
        self.assertNotIn(2, by_pr)
        self.assertNotIn(4, by_pr)

    def test_title_sentinel_on_an_ordinary_branch_is_not_the_persona_table(
        self,
    ) -> None:
        self.assertFalse(
            replay.is_sentinel_persona("Sentinel: fix eval", "feat/cleanup")
        )
        self.assertTrue(replay.is_sentinel_persona("Sentinel: note", "jules/note"))
        self.assertTrue(replay.is_sentinel_persona("sentinel note", "sentinel-fix"))

    def test_owner_held_routine_stamp_preserves_reported_outcome(self) -> None:
        item = _item(
            current_owner="stage3",
            guardrail_outcome="PASS_ROUTINE",
            changed_paths=["README.md"],
        )
        self.assertNotIn("guardrail_evidence", item)

        report = replay.replay_items(
            [item], {item["key"]: _evidence("Sentinel: routine note", "jules/note")}
        )

        row = report["sentinel_persona"][0]
        self.assertEqual(("PASS_ROUTINE", "PASS_ROUTINE"), (row["old"], row["new"]))


class ReplayLedgerTests(unittest.TestCase):
    def test_no_fetch_keeps_snapshot_unchanged_and_never_calls_github(self) -> None:
        ledger = {
            "ledger_revision": 19,
            "items": [_item(guardrail_outcome="REVIEW_SECURITY")],
            "events": [],
        }
        before = copy.deepcopy(ledger)
        with mock.patch.object(replay, "_load_config", return_value={}):
            with mock.patch.object(guardrails, "fetch_guardrail_evidence") as fetch:
                report = replay.replay_ledger(ledger, fetch=False)
        fetch.assert_not_called()
        self.assertEqual(1, report["unique_move_count"])
        self.assertEqual(19, report["ledger_revision"])
        self.assertEqual(before, ledger)

    def test_fetch_selects_eligible_items_and_requests_diff_only_when_needed(
        self,
    ) -> None:
        clean_hold = _item(key="clean", guardrail_outcome="REVIEW_SECURITY")
        sticky = _item(
            key="sticky", classification="SECURITY", changed_paths=["src/task.sh"]
        )
        dependabot = _item(
            key="dependabot",
            author={"login": "dependabot[bot]"},
            changed_paths=["uv.lock"],
        )
        ledger = {
            "ledger_revision": 19,
            "items": [
                None,
                clean_hold,
                sticky,
                dependabot,
                _item(key="ordinary"),
                _item(
                    key="terminal",
                    lifecycle_state="TERMINAL",
                    classification="SECURITY",
                ),
                _item(key="human", author_type="HUMAN", classification="SECURITY"),
                _item(key="unknown", author_type="UNKNOWN", classification="SECURITY"),
            ],
        }
        before = copy.deepcopy(ledger)
        patterns = ["review", "CodeScene*"]
        config = {"lifecycle": {"unblock": {"advisory_checks": patterns}}}

        def evidence_for(
            item: dict, patterns: list[str], *, include_diff: bool
        ) -> guardrails.GuardrailEvidence:
            return guardrails.GuardrailEvidence(
                diff_fetch_failed=item["key"] == "clean"
            )

        with mock.patch.object(replay, "_load_config", return_value=config):
            with mock.patch.object(
                guardrails, "fetch_guardrail_evidence", side_effect=evidence_for
            ) as fetch:
                report = replay.replay_ledger(ledger, fetch=True)
        fetch.assert_has_calls(
            [
                mock.call(clean_hold, patterns, include_diff=True),
                mock.call(sticky, patterns, include_diff=False),
                mock.call(dependabot, patterns, include_diff=True),
            ],
            any_order=True,
        )
        self.assertEqual(3, fetch.call_count)
        self.assertEqual(["clean"], report["fetch_failed"])
        self.assertEqual(before, ledger)

    def test_advisory_config_defaults_and_normalization(self) -> None:
        for config, expected in (
            ({}, []),
            ({"lifecycle": None}, []),
            ({"lifecycle": {"unblock": {"advisory_checks": "review"}}}, []),
            (
                {"lifecycle": {"unblock": {"advisory_checks": ["review", 17]}}},
                ["review", "17"],
            ),
        ):
            with self.subTest(config=config):
                self.assertEqual(expected, replay._advisory_patterns(config))

    def test_sentinel_persona_requires_both_title_and_branch(self) -> None:
        for branch in ("sentinel/fix", "sentinel-fix", "jules/fix", "JULES-FIX"):
            with self.subTest(branch=branch):
                self.assertTrue(replay.is_sentinel_persona("SENTINEL: cleanup", branch))
                self.assertFalse(replay.is_sentinel_persona("cleanup", branch))
        for branch in ("", "feature/sentinel/fix", "sentinelfix", "julestest"):
            with self.subTest(branch=branch):
                self.assertFalse(replay.is_sentinel_persona("Sentinel", branch))


class ReplayCommandTests(unittest.TestCase):
    def test_local_json_replay_does_not_modify_ledger_or_fetch(self) -> None:
        snapshot = "ledger_revision: 19\nitems: []\nevents: []\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.yaml"
            path.write_text(snapshot, encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(guardrails, "fetch_guardrail_evidence") as fetch:
                with mock.patch.object(replay.cas, "run_preflight") as preflight:
                    with redirect_stdout(output):
                        result = replay.main(
                            ["--ledger", str(path), "--no-fetch", "--json"]
                        )
            self.assertEqual(snapshot.encode(), path.read_bytes())
        self.assertEqual(0, result)
        self.assertEqual(19, json.loads(output.getvalue())["ledger_revision"])
        fetch.assert_not_called()
        preflight.assert_not_called()

    def test_non_mapping_snapshot_reports_error(self) -> None:
        for value in (None, [], "invalid", 17):
            with self.subTest(value=value):
                output, error = io.StringIO(), io.StringIO()
                with mock.patch.object(replay, "load_yaml", return_value=value):
                    with mock.patch.object(replay, "replay_ledger") as evaluate:
                        with redirect_stdout(output), redirect_stderr(error):
                            result = replay.main(
                                ["--ledger", "snapshot.yaml", "--no-fetch"]
                            )
                self.assertEqual(1, result)
                self.assertEqual("", output.getvalue())
                self.assertIn(
                    "PR_LIFECYCLE_REPLAY_ERROR: ledger_not_mapping", error.getvalue()
                )
                evaluate.assert_not_called()

    def test_default_snapshot_is_temporary_and_never_committed(self) -> None:
        observed_paths = []

        def preflight(path: Path) -> None:
            observed_paths.append(path)
            path.write_text("ledger_revision: 42\nitems: []\n", encoding="utf-8")

        with mock.patch.object(
            replay.cas, "run_preflight", side_effect=preflight
        ) as load:
            with mock.patch.object(replay.cas, "run_commit") as commit:
                with redirect_stdout(io.StringIO()) as output:
                    result = replay.main(["--no-fetch"])
        self.assertEqual(0, result)
        load.assert_called_once()
        commit.assert_not_called()
        self.assertFalse(observed_paths[0].exists())
        self.assertIn("Ledger revision: 42", output.getvalue())

    def test_markdown_report_contains_moves_failures_and_sentinel_reasons(self) -> None:
        cleared = _item(
            key="cleared",
            pr=1,
            guardrail_outcome="REVIEW_SECURITY",
            url="https://example.test/pr/1",
        )
        held = _item(
            key="held",
            pr=2,
            guardrail_outcome="REVIEW_SECURITY",
            changed_paths=["src/task.sh"],
        )
        empty = _item(
            key="empty", pr=3, guardrail_outcome="REVIEW_SECURITY", changed_paths=[]
        )
        evidence = {
            item["key"]: _evidence("Sentinel: note", "jules/note")
            for item in (cleared, held, empty)
        }
        evidence["empty"] = guardrails.GuardrailEvidence(
            diff_fetch_failed=True, title="Sentinel: note", head_ref="jules/note"
        )
        report = replay.replay_items([cleared, held, empty], evidence)
        report["ledger_revision"] = 19
        rendered = replay._format_report(report)
        self.assertIn("| unique items | 1 |", rendered)
        self.assertIn(
            "https://example.test/pr/1 (REVIEW_SECURITY → PASS_ROUTINE)", rendered
        )
        self.assertIn("Diff fetch failed (kept held): 1", rendered)
        self.assertIn(
            "| owner/repo#1 | no | REVIEW_SECURITY | PASS_ROUTINE | — |", rendered
        )
        self.assertIn(
            "| owner/repo#2 | no | REVIEW_SECURITY | REVIEW_SECURITY | shell_execution |",
            rendered,
        )
        self.assertIn(
            "| owner/repo#3 | no | REVIEW_SECURITY | REVIEW_SECURITY | empty changed_paths (fail-closed) |",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
