"""Tests for guardrail ledger writes, schema surface, and CLI parsing."""

from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails  # noqa: E402

from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


class EvaluateLedgerTests(unittest.TestCase):
    def test_owner_held_routine_stamp_is_evaluated_in_place(self) -> None:
        item = _item(
            current_owner="stage3",
            guardrail_outcome="PASS_ROUTINE",
            changed_paths=["src/worker.py"],
            revision=7,
        )
        ledger = {"items": [item], "events": [], "ledger_revision": 19}
        diff_text = (
            "diff --git a/src/worker.py b/src/worker.py\n"
            "--- a/src/worker.py\n"
            "+++ b/src/worker.py\n"
            "@@\n"
            "+print('ready')\n"
        )
        evidence = guardrails.GuardrailEvidence(
            diff_text=diff_text,
            head_sha=item["head_sha"],
            diff_sha256=hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
        )

        _, summary = guardrails.evaluate_ledger(
            ledger, None, evidence_for=lambda _item: evidence
        )

        self.assertEqual(
            {
                "head_sha": item["head_sha"],
                "basis": "head_bound_diff",
                "diff_sha256": evidence.diff_sha256,
            },
            item["guardrail_evidence"],
        )
        self.assertEqual("PASS_ROUTINE", item["guardrail_outcome"])
        self.assertEqual([], ledger["events"])
        self.assertEqual(7, item["revision"])
        self.assertEqual(19, ledger["ledger_revision"])
        self.assertEqual(1, summary["evidence_stamped"])
        self.assertEqual(1, summary["outcomes_unchanged"])
        self.assertEqual([], summary["unstamped_routine"])

    def test_evidence_callback_applies_diff_signals_only_to_selected_repo(self) -> None:
        selected = _item(
            key="owner/repo#1@abc",
            guardrail_outcome="REVIEW_SECURITY",
            classification="SECURITY",
            changed_paths=["src/main.py"],
            revision=7,
        )
        excluded = _item(repository="other/repo", key="other/repo#1@def")
        ledger = {
            "items": [None, selected, excluded],
            "ledger_revision": 19,
            "events": [],
        }
        original_excluded = copy.deepcopy(excluded)
        evidence_for = mock.Mock(
            return_value=guardrails.GuardrailEvidence(
                diff_text="+++ b/src/main.py\n+html.escape(value)\n"
            )
        )
        result, summary = guardrails.evaluate_ledger(
            ledger, {"owner/repo"}, evidence_for=evidence_for
        )
        evidence_for.assert_called_once_with(selected)
        self.assertIs(result, ledger)
        self.assertEqual("REVIEW_SECURITY", selected["guardrail_outcome"])
        self.assertEqual(["security_configuration"], selected["sensitive_paths"])
        self.assertEqual("SENSITIVE", selected["risk_class"])
        self.assertEqual(7, selected["revision"])
        self.assertEqual(19, ledger["ledger_revision"])
        self.assertEqual([], ledger["events"])
        self.assertEqual(original_excluded, excluded)
        self.assertEqual(1, summary["evaluated"])
        self.assertEqual(1, summary["outcomes_unchanged"])
        self.assertEqual([], summary["changes"])

    def test_metadata_repair_preserves_revision_events_and_reports_no_flip(
        self,
    ) -> None:
        """A SECURITY label with only docs downgrades and does not bump revision."""
        now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
        item = _item(
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="stand_in",
            sensitive_paths=["security_configuration"],
            risk_class="UNKNOWN",
            revision=7,
            updated_at_utc="2026-10-08T12:00:00Z",
        )
        ledger = {"items": [item], "events": [], "ledger_revision": 19}
        before = copy.deepcopy(ledger)
        with mock.patch.object(guardrails, "datetime") as clock:
            clock.now.return_value = now
            result, summary = guardrails.evaluate_ledger(ledger, None)

        self.assertIs(result, ledger)
        expected = copy.deepcopy(before)
        expected["items"][0].update(
            sensitive_paths=[],
            guardrail_outcome="PASS_ROUTINE",
            guardrail_source="path_eval",
            risk_class="ROUTINE",
            guardrail_evidence={
                "head_sha": item["head_sha"],
                "basis": "non_executable_paths",
                "diff_sha256": None,
            },
            updated_at_utc="2026-10-09T12:00:00Z",
        )
        self.assertEqual(expected, ledger)
        self.assertEqual(
            {
                "evaluated": 1,
                "outcomes_unchanged": 0,
                "skipped": 0,
                "by_outcome": {"REVIEW_SECURITY": 0, "PASS_ROUTINE": 1},
                "evidence_stamped": 1,
                "unstamped_routine": [],
                "changes": [
                    {
                        "key": item["key"],
                        "from": "REVIEW_SECURITY",
                        "to": "PASS_ROUTINE",
                        "sensitive_paths": [],
                    }
                ],
            },
            summary,
        )

        # A second evaluation must not refresh timestamps or count another repair.
        with mock.patch.object(guardrails, "datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 10, tzinfo=timezone.utc)
            _, repeated = guardrails.evaluate_ledger(ledger, None, clear_standin=True)
        self.assertEqual(expected, ledger)
        self.assertEqual(0, repeated["evaluated"])
        self.assertEqual(1, repeated["skipped"])
        self.assertEqual([], repeated["changes"])

    def test_outcome_changes_preserve_item_revision(self) -> None:
        for revision, paths, outcome in product(
            (0, 1, 42),
            (["docs/a.md"], ["scripts/fix.sh"]),
            (None, "NOT_RUN"),
        ):
            with self.subTest(revision=revision, paths=paths, outcome=outcome):
                item = _item(
                    revision=revision, changed_paths=paths, guardrail_outcome=outcome
                )
                ledger = {"items": [item], "events": [], "ledger_revision": 10}
                _, summary = guardrails.evaluate_ledger(ledger, None)
                expected_outcome = (
                    "PASS_ROUTINE" if paths == ["docs/a.md"] else "REVIEW_SECURITY"
                )
                self.assertEqual(revision, item["revision"])
                self.assertEqual([], ledger["events"])
                self.assertEqual(10, ledger["ledger_revision"])
                self.assertEqual(1, summary["evaluated"])
                self.assertEqual(0, summary["outcomes_unchanged"])
                self.assertEqual(1, summary["by_outcome"][expected_outcome])
                self.assertEqual(
                    [
                        {
                            "key": item["key"],
                            "from": outcome,
                            "to": expected_outcome,
                            "sensitive_paths": (
                                []
                                if expected_outcome == "PASS_ROUTINE"
                                else ["shell_execution"]
                            ),
                        }
                    ],
                    summary["changes"],
                )

    def test_non_bot_items_remain_unchanged_in_mixed_ledger(self) -> None:
        excluded = [
            _item(author_type=author_type, guardrail_outcome="REVIEW_SECURITY")
            for author_type in ("HUMAN", "UNKNOWN", None)
        ]
        missing_author = _item()
        del missing_author["author_type"]
        excluded.append(missing_author)
        before = copy.deepcopy(excluded)
        bot = _item(guardrail_outcome="REVIEW_SECURITY", classification="DEPENDENCY")
        ledger = {"items": [*excluded, bot]}

        _, summary = guardrails.evaluate_ledger(ledger, None, clear_standin=True)

        self.assertEqual(before, excluded)
        self.assertEqual("PASS_ROUTINE", bot["guardrail_outcome"])
        self.assertEqual(1, summary["evaluated"])
        self.assertEqual(4, summary["skipped"])

    def test_preserves_revision_and_filters_repos(self) -> None:
        """revision is a projection of transition events — evaluation must
        not bump it without logging one (ledger consistency check)."""
        ledger = {
            "items": [
                _item(
                    repository="owner/a",
                    pr=1,
                    changed_paths=["scripts/x.sh"],
                    revision=2,
                ),
                _item(
                    repository="owner/b",
                    pr=2,
                    changed_paths=["scripts/x.sh"],
                    revision=1,
                ),
            ]
        }
        _, summary = guardrails.evaluate_ledger(ledger, {"owner/a"})
        self.assertEqual(1, summary["evaluated"])
        a, b = ledger["items"]
        self.assertEqual(2, a["revision"])
        self.assertEqual(1, b["revision"])
        self.assertIn("updated_at_utc", a)
        self.assertNotIn("updated_at_utc", b)

    def test_evaluated_example_ledger_passes_validation(self) -> None:
        """End-to-end: run evaluation on a schema-valid ledger, then the
        real schema + runtime-record validators accept the write."""
        from pr_lifecycle_ledger import validate_runtime_records
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        from tests.pr_lifecycle_helpers import schema_valid_starved_ledger

        ledger = schema_valid_starved_ledger()
        item = ledger["items"][0]
        # Move the item back to STAGE1_INTAKE with a legal HANDOFF event so
        # the projected fields (state/owner/revision/handoffs) stay
        # consistent with the event log.
        return_event = {
            "event_id": "evt-2026-stage3-return-001",
            "kind": "HANDOFF",
            "item_key": item["key"],
            "from_owner": "stage3",
            "to_owner": "stage1",
            "from_state": "STAGE3_RECONCILIATION",
            "to_state": "STAGE1_INTAKE",
            "next_owner": "stage1",
            "terminal_disposition": None,
            "parent_event_id": None,
            "expected_item_revision": 1,
            "resulting_item_revision": 2,
            "idempotency_key": f"{item['key']}:evt-2026-stage3-return-001",
            "status": "PROJECTED",
            "created_at_utc": "2026-10-09T12:00:00Z",
            "acknowledged_at_utc": None,
            "reason": "Stage 3 handed it back for re-evaluation.",
        }
        ledger["events"].insert(2, return_event)
        item.update(
            {
                "author_type": "BOT",
                "lifecycle_state": "STAGE1_INTAKE",
                "current_owner": "stage1",
                "next_owner": "stage1",
                "revision": 2,
                "handoffs": [*item["handoffs"], "evt-2026-stage3-return-001"],
                "guardrail_outcome": "REVIEW_SECURITY",
                "changed_paths": ["docs/plan.md"],
            }
        )
        guardrails.evaluate_ledger(ledger, None, clear_standin=True)
        self.assertEqual("PASS_ROUTINE", item["guardrail_outcome"])
        self.assertEqual("path_eval", item["guardrail_source"])
        validate_schema(ledger)
        config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        validate_runtime_records(ledger, config)


class ClosedUnreviewedSchemaTests(unittest.TestCase):
    def test_closed_unreviewed_is_a_valid_terminal_disposition(self) -> None:
        """Validator accepts CLOSED_UNREVIEWED on item and event surfaces."""
        from pr_lifecycle_ledger import TERMINAL_DISPOSITIONS
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        self.assertIn("CLOSED_UNREVIEWED", TERMINAL_DISPOSITIONS)
        ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
        surfaces = [
            e
            for e in ledger.get("events") or []
            if isinstance(e, dict) and e.get("kind") == "TERMINAL"
        ]
        surfaces += [
            i
            for i in ledger.get("items") or []
            if isinstance(i, dict) and i.get("lifecycle_state") == "TERMINAL"
        ]
        self.assertTrue(surfaces)
        for surface in surfaces:
            surface["terminal_disposition"] = "CLOSED_UNREVIEWED"
        validate_schema(ledger)


class GuardrailSourceSchemaTests(unittest.TestCase):
    def test_all_documented_sources_are_accepted(self) -> None:
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        for source in ("path_eval", "stand_in", "manual", "review", "human", "octopus"):
            with self.subTest(source=source):
                ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
                ledger["items"][0]["guardrail_source"] = source
                validate_schema(ledger)

    def test_source_is_optional_for_existing_ledgers(self) -> None:
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
        for item in ledger["items"]:
            item.pop("guardrail_source", None)
        validate_schema(ledger)

    def test_invalid_sources_are_rejected_at_the_item_field(self) -> None:
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        for source in ("", "PATH_EVAL", "unknown", None, 1, True, [], {}):
            with self.subTest(source=source):
                ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
                ledger["items"][0]["guardrail_source"] = source
                with self.assertRaisesRegex(
                    ValueError, r"schema items\.0\.guardrail_source:"
                ):
                    validate_schema(ledger)


class ArgParseTests(unittest.TestCase):
    def test_json_flag_accepted(self) -> None:
        args = guardrails.build_parser().parse_args(["--json"])
        self.assertTrue(args.json_out)
        self.assertFalse(args.apply)
        self.assertFalse(args.clear_standin)

    def test_clear_stand_in_flag_accepted(self) -> None:
        args = guardrails.build_parser().parse_args(
            ["--apply", "--json", "--clear-stand-in"]
        )
        self.assertTrue(args.clear_standin)


if __name__ == "__main__":
    unittest.main()
