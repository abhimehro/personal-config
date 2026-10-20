"""Unit tests for title-vs-path/diff security tagging in pr_lifecycle_reconcile."""

from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_reconcile_guards as guards  # noqa: E402
from pr_identity import identity_policy_from_config  # noqa: E402

from tests.pr_lifecycle_helpers import (  # noqa: E402
    load_reconcile_with_stubs,
    reconcile_item,
)

reconcile = load_reconcile_with_stubs()

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
CONFIG = yaml.safe_load((ROOT / "tasks/pr-review-agent.config.yaml").read_text())
POLICY = identity_policy_from_config(CONFIG)
REPO = CONFIG["repos"][0]
_OPEN_LIVE = {"state": "OPEN", "headRefOid": "a" * 40, "baseRefOid": "b" * 40}


def _live_pr(**overrides):
    pr = {
        "number": 587,
        "repository": REPO,
        "url": f"https://github.com/{REPO}/pull/587",
        "title": "🛡️ Sentinel: Refactor logging in export_comparison_sheets",
        "body": "Created automatically by Jules",
        "isDraft": False,
        "headRefName": "sentinel/logging-cleanup",
        "headRefOid": "a" * 40,
        "baseRefName": "main",
        "baseRefOid": "b" * 40,
        "author": {"login": "google-labs-jules[bot]", "type": "Bot"},
        "comments": [],
        "latestReviews": [],
        "commits": [],
        "checks": [],
    }
    pr.update(overrides)
    return pr


def _security_item(**overrides):
    fields = {
        "lifecycle_state": "STAGE1_INTAKE",
        "current_owner": "stage1",
        "next_owner": "stage1",
        "classification": "SECURITY",
        "risk_class": "SENSITIVE",
        "guardrail_outcome": "REVIEW_SECURITY",
        "guardrail_source": "path_eval",
        "changed_paths": ["src/report.py"],
        "next_action": "Review Sentinel title",
    }
    fields.update(overrides)
    if "pr" in overrides:
        fields.setdefault("key", f"{REPO}#{fields['pr']}@{'a' * 40}")
    return reconcile_item(now=NOW, **fields)


class ReconcileSecurityTaggingTests(unittest.TestCase):
    def test_sentinel_title_alone_does_not_classify_as_security(self):
        """'Sentinel' is a Jules persona name, not a standalone security signal."""
        # Pathless intake: stays UNKNOWN, never SECURITY
        intake = reconcile.build_intake_item(_live_pr(), POLICY, NOW)
        self.assertEqual(intake["classification"], "UNKNOWN")
        self.assertEqual(intake["guardrail_outcome"], "NOT_RUN")

        # Non-sensitive paths + Sentinel title + .jules/sentinel.md journal: REFACTOR
        with_paths = _live_pr(
            changed_paths=[
                ".jules/sentinel.md",
                "scripts/export_comparison_sheets.py",
                "scripts/tests/test_export_comparison_sheets_security.py",
            ],
            diff_text=(
                "+++ b/scripts/export_comparison_sheets.py\n"
                "+logger.warning('Skipping invalid sheet %s', sheet_name)\n"
            ),
        )
        intake_with_paths = reconcile.build_intake_item(with_paths, POLICY, NOW)
        self.assertEqual(intake_with_paths["classification"], "REFACTOR")
        self.assertEqual(intake_with_paths["sensitive_paths"], [])
        self.assertEqual(intake_with_paths["guardrail_outcome"], "NOT_RUN")

    def test_sentinel_title_backed_by_security_path_or_diff_classifies_security(self):
        """A Sentinel/security title backed by sensitive paths or diff is SECURITY."""
        # Backed by production security module path
        by_path = _live_pr(
            changed_paths=[
                ".jules/sentinel.md",
                "src/hydrograph_seatek_analysis/utils/security.py",
            ]
        )
        self.assertEqual(reconcile.infer_pr_classification(by_path), "SECURITY")

        # Backed by path-traversal diff in an ordinary module path
        by_diff = _live_pr(
            changed_paths=[
                ".jules/sentinel.md",
                "scripts/batch_correction.py",
                "scripts/tests/test_batch_correction_security.py",
            ],
            diff_text=(
                "+++ b/scripts/batch_correction.py\n"
                "+resolved = os.path.realpath(target)\n"
                "+if os.path.commonpath([base_dir, resolved]) != base_dir:\n"
                "+    raise ValueError('Path traversal detected')\n"
            ),
        )
        self.assertEqual(reconcile.infer_pr_classification(by_diff), "SECURITY")

    def test_test_only_diff_patterns_do_not_back_security_classification(self):
        """Security keywords inside test files alone do not make a PR SECURITY."""
        test_only = _live_pr(
            changed_paths=[
                "Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift"
            ],
            diff_text=(
                "+++ b/Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift\n"
                '+func testRedaction() { let token = "ghp_123456" }\n'
            ),
        )
        self.assertEqual(reconcile.infer_pr_classification(test_only), "REFACTOR")

    def test_reconcile_emits_and_applies_reclassify_for_unbacked_sentinel_item(self):
        """Reconcile clears title-only SECURITY/REVIEW_SECURITY on unbacked BOT items."""
        item = reconcile_item(
            now=NOW,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            next_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            risk_class="SENSITIVE",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            sensitive_paths=["generated_output"],
            changed_paths=[
                ".jules/sentinel.md",
                "scripts/export_comparison_sheets.py",
                "scripts/tests/test_export_comparison_sheets_security.py",
            ],
            next_action=(
                "Stage 1 2026-10-17 AM: REVIEW_SECURITY "
                "(security-themed Sentinel title; Desk standing order)"
            ),
        )
        benign_diff = (
            "+++ b/scripts/export_comparison_sheets.py\n"
            "+logger.info('Exported %d rows', count)\n"
        )
        ledger = {"ledger_revision": 10, "items": [item], "events": []}
        with (
            mock.patch.object(reconcile, "_gh_pr_view", return_value=_OPEN_LIVE),
            mock.patch.object(reconcile, "_gh_pr_diff", return_value=benign_diff),
        ):
            actions = reconcile.collect_actions(ledger, {"lifecycle": {}}, now=NOW)
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "RECLASSIFY_TITLE_SECURITY")
        self.assertEqual(action["to_classification"], "REFACTOR")
        self.assertTrue(action["clear_review_security"])

        result = reconcile.apply_action_to_ledger(ledger, item, action)
        self.assertIsNone(result["event_id"])
        self.assertEqual(item["classification"], "REFACTOR")
        self.assertEqual(item["guardrail_outcome"], "PASS_ROUTINE")
        self.assertEqual(item["risk_class"], "ROUTINE")
        self.assertEqual(item["guardrail_source"], "path_eval")
        self.assertEqual(item["sensitive_paths"], [])
        self.assertEqual(item["revision"], 1)
        self.assertEqual(ledger["ledger_revision"], 11)

        with self.assertRaises(reconcile.ReconcileSkip):
            reconcile.apply_action_to_ledger(ledger, item, action)

    def test_reconcile_keeps_security_when_backed_or_fail_closed(self):
        """Items backed by paths/diff, missing paths, or human-held are never cleared."""
        backed_by_diff = reconcile_item(
            now=NOW,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            next_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            changed_paths=["scripts/batch_correction.py"],
            next_action="Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title)",
        )
        traversal_diff = (
            "+++ b/scripts/batch_correction.py\n"
            "+if os.path.commonpath([base, os.path.realpath(p)]) != base:\n"
            "+    raise ValueError('Path traversal')\n"
        )
        with mock.patch.object(reconcile, "_gh_pr_diff", return_value=traversal_diff):
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(backed_by_diff, _OPEN_LIVE)
            )

        # Missing diff lookup fails closed
        with mock.patch.object(reconcile, "_gh_pr_diff", return_value=None):
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(backed_by_diff, _OPEN_LIVE)
            )

        # Empty changed_paths fails closed without calling _gh_pr_diff
        empty_paths = dict(backed_by_diff, changed_paths=[])
        with mock.patch.object(reconcile, "_gh_pr_diff") as diff_mock:
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(empty_paths, _OPEN_LIVE)
            )
            diff_mock.assert_not_called()

        # Forced human hold is never touched
        forced = dict(
            backed_by_diff,
            next_action="HUMAN_HOLD (PR Desk list): explicit human decision required",
        )
        with mock.patch.object(reconcile, "_gh_pr_diff") as diff_mock:
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(forced, _OPEN_LIVE)
            )
            diff_mock.assert_not_called()

    def test_reconcile_security_tagging_summary_counts_before_and_after(self):
        """Verify before/after summary counts on a mixed ledger fixture."""
        unbacked = reconcile_item(
            now=NOW,
            key=f"{REPO}#1@{'a' * 40}",
            pr=1,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            changed_paths=[".jules/sentinel.md", "scripts/export_comparison_sheets.py"],
            diff_text="+++ b/scripts/export_comparison_sheets.py\n+log.info('ok')\n",
            next_action="Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title)",
        )
        backed = reconcile_item(
            now=NOW,
            key=f"{REPO}#2@{'b' * 40}",
            pr=2,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            changed_paths=[".jules/sentinel.md", "lib/safe_http.py"],
            next_action="Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title)",
        )
        summary = guards.reconcile_security_tagging_summary(
            {"items": [unbacked, backed]}
        )
        self.assertEqual(summary["before_security_count"], 2)
        self.assertEqual(summary["after_security_count"], 1)
        self.assertEqual(summary["before_review_security_count"], 2)
        self.assertEqual(summary["after_review_security_count"], 1)
        self.assertEqual(summary["reclassified_count"], 1)
        self.assertEqual(summary["reclassified_items"][0]["pr"], 1)


class SecurityIntakeTests(unittest.TestCase):
    def test_intake_normalizes_paths_without_mutating_live_pr(self):
        live = _live_pr(
            changed_paths=[
                " src/report.py ",
                " .env.local ",
                "src/report.py",
                "",
                None,
                7,
            ]
        )
        before = deepcopy(live)
        item = reconcile.build_intake_item(live, POLICY, NOW)
        self.assertEqual(item["changed_paths"], [".env.local", "src/report.py"])
        self.assertEqual(item["sensitive_paths"], ["secrets"])
        self.assertEqual(item["classification"], "SECURITY")
        self.assertEqual(item["guardrail_outcome"], "NOT_RUN")
        self.assertEqual(item["risk_class"], "UNKNOWN")
        self.assertEqual(live, before)

    def test_intake_rejects_nonlist_path_collections(self):
        for paths in (None, ".env", {"path": ".env"}, (".env",)):
            with self.subTest(paths=paths):
                item = reconcile.build_intake_item(
                    _live_pr(changed_paths=paths), POLICY, NOW
                )
                self.assertEqual(item["changed_paths"], [])
                self.assertEqual(item["sensitive_paths"], [])
                self.assertEqual(item["classification"], "UNKNOWN")

    def test_intake_uses_production_diff_evidence(self):
        item = reconcile.build_intake_item(
            _live_pr(
                title="Fix report handling",
                headRefName="fix/report",
                changed_paths=["src/report.py"],
                diff_text="+++ b/src/report.py\n-allow_redirects=True\n+allow_redirects=False\n",
            ),
            POLICY,
            NOW,
        )
        self.assertEqual(item["classification"], "SECURITY")
        self.assertEqual(item["sensitive_paths"], [])
        self.assertEqual(item["guardrail_outcome"], "NOT_RUN")


class SecurityReclassificationTests(unittest.TestCase):
    def test_drifted_head_reanchors_without_reclassifying_on_mixed_evidence(self):
        item = _security_item(
            head_sha="a" * 40, base_sha="b" * 40, diff_text="+++ b/src/x.py\n+x = 1\n"
        )
        before = deepcopy(item)
        live = {**_OPEN_LIVE, "baseRefOid": "c" * 40}
        with mock.patch.object(reconcile, "_gh_pr_view", return_value=live):
            actions = reconcile.collect_actions(
                {"items": [item]}, {"lifecycle": {}}, now=NOW
            )
        self.assertEqual([action["action"] for action in actions], ["REANCHOR_HEAD"])
        self.assertEqual(item, before)

    def test_path_backfill_does_not_clear_security_before_paths_are_applied(self):
        item = _security_item(changed_paths=[])
        with (
            mock.patch.object(reconcile, "_gh_pr_view", return_value=_OPEN_LIVE),
            mock.patch.object(
                reconcile, "_gh_pr_files", return_value=["src/report.py"]
            ),
            mock.patch.object(reconcile, "_gh_pr_diff") as diff_fetch,
        ):
            actions = reconcile.collect_actions(
                {"items": [item]}, {"lifecycle": {}}, now=NOW
            )
        self.assertEqual([action["action"] for action in actions], ["BACKFILL_PATHS"])
        self.assertEqual(item["changed_paths"], [])
        self.assertEqual(item["classification"], "SECURITY")
        diff_fetch.assert_not_called()

    def test_forced_holds_preserve_classification_without_fetching(self):
        overrides = (
            {"risk_class": "HUMAN_REVIEW"},
            *({"current_owner": owner} for owner in ("human", "stage2", "stage3")),
            *(
                {"guardrail_source": source}
                for source in ("review", "human", "octopus")
            ),
            {"next_action": "HUMAN_HOLD pending decision"},
            {"next_action": "PR Desk forced hold: wait"},
        )
        for fields in overrides:
            with (
                self.subTest(fields=fields),
                mock.patch.object(reconcile, "_gh_pr_diff") as fetch,
            ):
                item = _security_item(**fields)
                self.assertTrue(guards.is_forced_security_hold(item))
                self.assertIsNone(
                    guards.evaluate_security_tag_reconcile(item, diff_text="")
                )
                self.assertIsNone(
                    reconcile._security_tag_reconcile_action(item, _OPEN_LIVE)
                )
                fetch.assert_not_called()

    def test_ineligible_items_never_fetch_diff(self):
        cases = (
            ({"lifecycle_state": "TERMINAL"}, _OPEN_LIVE),
            ({"author_type": "HUMAN"}, _OPEN_LIVE),
            ({"classification": "REFACTOR"}, _OPEN_LIVE),
            ({"changed_paths": []}, _OPEN_LIVE),
            ({"changed_paths": "src/report.py"}, _OPEN_LIVE),
            ({"changed_paths": ["lib/safe_http.py"]}, _OPEN_LIVE),
            ({}, None),
            ({}, []),
            ({}, {"state": "CLOSED"}),
            ({}, {"state": "MERGED"}),
        )
        for fields, live in cases:
            with (
                self.subTest(fields=fields, live=live),
                mock.patch.object(reconcile, "_gh_pr_diff") as fetch,
            ):
                self.assertIsNone(
                    reconcile._security_tag_reconcile_action(
                        _security_item(**fields), live
                    )
                )
                fetch.assert_not_called()

    def test_live_head_drift_from_ledger_anchor_skips_reclassification(self):
        benign = "+++ b/src/report.py\n+log.info(1)\n"
        anchored = {"head_sha": "a" * 40, "base_sha": "b" * 40, "diff_text": benign}
        self.assertIsNotNone(
            reconcile._security_tag_reconcile_action(
                _security_item(**anchored), _OPEN_LIVE
            )
        )
        for live in (
            {**_OPEN_LIVE, "headRefOid": "c" * 40},
            {**_OPEN_LIVE, "baseRefOid": "c" * 40},
        ):
            item = _security_item(**anchored)
            with (
                self.subTest(live=live),
                mock.patch.object(reconcile, "_gh_pr_diff") as fetch,
            ):
                self.assertIsNone(reconcile._security_tag_reconcile_action(item, live))
                fetch.assert_not_called()

    def test_invalid_lookup_identity_fails_closed(self):
        for fields in (
            {"repository": ""},
            {"pr": None},
            {"pr": 0},
            {"pr": -1},
            {"pr": "bad"},
            {"pr": True},
        ):
            with (
                self.subTest(fields=fields),
                mock.patch.object(reconcile, "_gh_pr_diff") as fetch,
            ):
                self.assertIsNone(
                    reconcile._security_tag_reconcile_action(
                        _security_item(**fields), _OPEN_LIVE
                    )
                )
                fetch.assert_not_called()

    def test_cached_item_diff_precedes_live_diff_and_empty_fails_closed(self):
        security_diff = "+++ b/src/report.py\n+authenticate(user)\n"
        for item_diff, live_diff, reclassify in (
            ("", security_diff, False),
            (security_diff, "", False),
            ("+++ b/src/report.py\n+log.info(1)\n", security_diff, True),
        ):
            with (
                self.subTest(item_diff=item_diff),
                mock.patch.object(reconcile, "_gh_pr_diff") as fetch,
            ):
                action = reconcile._security_tag_reconcile_action(
                    _security_item(diff_text=item_diff),
                    {**_OPEN_LIVE, "diff_text": live_diff},
                )
                self.assertEqual(action is not None, reclassify)
                fetch.assert_not_called()

    def test_live_diff_precedes_fetch_when_item_diff_is_missing(self):
        for diff, reclassify in (
            ("", False),
            ("+++ b/src/report.py\n+log.info(1)\n", True),
            ("+++ b/src/report.py\n+authenticate(user)\n", False),
        ):
            with (
                self.subTest(diff=diff),
                mock.patch.object(reconcile, "_gh_pr_diff") as fetch,
            ):
                action = reconcile._security_tag_reconcile_action(
                    _security_item(diff_text=None), {**_OPEN_LIVE, "diff_text": diff}
                )
                self.assertEqual(action is not None, reclassify)
                fetch.assert_not_called()

    def test_diff_fetch_failure_preserves_item_and_success_produces_action(self):
        for diff, reclassify in (
            (None, False),
            ("", False),
            ("+++ b/src/report.py\n+log.info(1)\n", True),
            ("+++ b/src/report.py\n+authenticate(user)\n", False),
        ):
            item = _security_item()
            before = deepcopy(item)
            with (
                self.subTest(diff=diff),
                mock.patch.object(reconcile, "_gh_pr_diff", return_value=diff) as fetch,
            ):
                action = reconcile._security_tag_reconcile_action(item, _OPEN_LIVE)
                fetch.assert_called_once_with(item["repository"], item["pr"])
                self.assertEqual(action is not None, reclassify)
                self.assertEqual(item, before)

    def test_only_title_derived_review_security_outcomes_are_clearable(self):
        cases = (
            ("manual", "Review security-themed title", "REVIEW_SECURITY", True),
            ("manual", "Review Sentinel title", "REVIEW_SECURITY", True),
            ("manual", "Explicit security review required", "REVIEW_SECURITY", False),
            ("path_eval", "Review", "REVIEW_SECURITY", True),
            ("stand_in", "Review", "REVIEW_SECURITY", True),
            (None, "Review", "REVIEW_SECURITY", True),
            ("other", "Review", "REVIEW_SECURITY", False),
            ("path_eval", "Review", "HOLD_EVIDENCE", False),
        )
        for source, next_action, outcome, clear in cases:
            with self.subTest(source=source, next_action=next_action, outcome=outcome):
                item = _security_item(
                    guardrail_source=source,
                    next_action=next_action,
                    guardrail_outcome=outcome,
                )
                action = guards.evaluate_security_tag_reconcile(item, diff_text="")
                self.assertEqual(action["clear_review_security"], clear)
                self.assertEqual(action["to_classification"], "REFACTOR")

    def test_reclassification_preserves_unrelated_review_and_lifecycle_fields(self):
        item = _security_item(
            guardrail_source="manual", next_action="Explicit security review required"
        )
        before = deepcopy(item)
        action = guards.evaluate_security_tag_reconcile(item, diff_text="")
        ledger = {
            "ledger_revision": 8,
            "items": [item],
            "events": [{"event_id": "existing"}],
        }
        self.assertEqual(
            reconcile.apply_action_to_ledger(ledger, item, action), {"event_id": None}
        )
        self.assertEqual(
            item, {**before, "classification": "REFACTOR", "sensitive_paths": []}
        )
        self.assertEqual(ledger["ledger_revision"], 9)
        self.assertEqual(ledger["events"], [{"event_id": "existing"}])
        after = deepcopy(ledger)
        with self.assertRaisesRegex(reconcile.ReconcileSkip, "reclassify_noop"):
            reconcile.apply_action_to_ledger(ledger, item, action)
        self.assertEqual(ledger, after)

    def test_reclassification_uses_dependency_identity_without_lifecycle_transition(
        self,
    ):
        item = _security_item(author={"login": "renovate[bot]"})
        before = deepcopy(item)
        action = guards.evaluate_security_tag_reconcile(item, diff_text="")
        self.assertEqual(action["to_classification"], "DEPENDENCY")
        ledger = {"ledger_revision": 8, "items": [item], "events": []}
        reconcile.apply_action_to_ledger(ledger, item, action)
        self.assertEqual(item["classification"], "DEPENDENCY")
        self.assertEqual(item["guardrail_outcome"], "PASS_ROUTINE")
        for field in (
            "revision",
            "lifecycle_state",
            "current_owner",
            "next_owner",
            "updated_at_utc",
            "handoffs",
        ):
            with self.subTest(field=field):
                self.assertEqual(item[field], before[field])
        self.assertEqual(ledger["events"], [])


class SecurityDiffLookupTests(unittest.TestCase):
    def test_successful_lookup_returns_stdout_and_empty_output_fails_closed(self):
        command = ["gh", "pr", "diff", "99", "--repo", REPO]
        for diff, expected in (
            ("", None),
            ("  \n", None),
            (
                "+++ b/src/report.py\n+authenticate(user)\n",
                "+++ b/src/report.py\n+authenticate(user)\n",
            ),
        ):
            result = reconcile.subprocess.CompletedProcess(command, 0, stdout=diff)
            with (
                self.subTest(diff=diff),
                mock.patch.object(
                    reconcile.subprocess, "run", return_value=result
                ) as run,
            ):
                self.assertEqual(reconcile._gh_pr_diff(REPO, 99), expected)
                run.assert_called_once_with(
                    command, check=False, capture_output=True, text=True, timeout=60
                )

    def test_failed_lookup_returns_none_even_if_partial_stdout_exists(self):
        result = reconcile.subprocess.CompletedProcess([], 1, stdout="partial diff")
        with mock.patch.object(reconcile.subprocess, "run", return_value=result):
            self.assertIsNone(reconcile._gh_pr_diff(REPO, 99))
        for error in (
            OSError("gh unavailable"),
            reconcile.subprocess.TimeoutExpired("gh", 60),
        ):
            with (
                self.subTest(error=error),
                mock.patch.object(reconcile.subprocess, "run", side_effect=error),
            ):
                self.assertIsNone(reconcile._gh_pr_diff(REPO, 99))


class SecurityTaggingSummaryTests(unittest.TestCase):
    def test_summary_fetches_only_missing_eligible_evidence_and_never_mutates_ledger(
        self,
    ):
        items = [
            _security_item(pr=1),
            _security_item(pr=2),
            _security_item(pr=3),
            _security_item(pr=4, diff_text=""),
            _security_item(pr=5, changed_paths=["lib/safe_http.py"]),
            _security_item(pr=6, current_owner="human"),
            _security_item(pr=7, changed_paths=[]),
            _security_item(pr=8, classification="REFACTOR"),
            _security_item(pr=9, lifecycle_state="TERMINAL"),
            _security_item(
                pr=10,
                diff_text="",
                guardrail_source="manual",
                next_action="Explicit review",
            ),
            None,
        ]
        ledger = {"items": items, "ledger_revision": 12}
        before = deepcopy(ledger)
        fetch = mock.Mock(
            side_effect=[None, "+++ b/src/report.py\n+authenticate(user)\n", ""]
        )
        summary = guards.reconcile_security_tagging_summary(ledger, diff_fetcher=fetch)
        self.assertEqual(
            fetch.call_args_list, [mock.call(REPO, pr) for pr in (1, 2, 3)]
        )
        self.assertEqual(summary["nonterminal_count"], 9)
        self.assertEqual(summary["before_security_count"], 8)
        self.assertEqual(summary["after_security_count"], 5)
        self.assertEqual(summary["before_review_security_count"], 9)
        self.assertEqual(summary["after_review_security_count"], 7)
        self.assertEqual(summary["reclassified_count"], 3)
        self.assertEqual(summary["downgraded_review_security_count"], 2)
        self.assertEqual(
            [row["pr"] for row in summary["reclassified_items"]], [3, 4, 10]
        )
        self.assertEqual(
            [row["to_outcome"] for row in summary["reclassified_items"]],
            ["PASS_ROUTINE", "PASS_ROUTINE", "REVIEW_SECURITY"],
        )
        self.assertEqual(ledger, before)

    def test_empty_summary_has_zero_counts_and_no_fetches(self):
        for ledger in (
            {},
            {"items": []},
            {"items": [None, "bad", {"lifecycle_state": "TERMINAL"}]},
        ):
            with self.subTest(ledger=ledger):
                fetch = mock.Mock()
                summary = guards.reconcile_security_tagging_summary(
                    ledger, diff_fetcher=fetch
                )
                self.assertEqual(summary["reclassified_items"], [])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in summary.items()
                        if key.endswith("_count")
                    )
                )
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
