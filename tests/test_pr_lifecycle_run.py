"""Unit tests for pr_lifecycle_run plan shape."""

from __future__ import annotations

import copy
import json
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Stub remote/health deps for this module only; restoring sys.modules keeps
# unittest discovery from leaking the stubs into the rest of the suite.
_STUB_NAMES = (
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_pipeline_health",
    "pr_lifecycle_config",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
    "pr_lifecycle_reconcile",
    "pr_lifecycle_feed",
)
_saved_modules = {name: sys.modules.get(name) for name in _STUB_NAMES}
for name in _STUB_NAMES:
    sys.modules[name] = types.ModuleType(name)

sys.modules["pr_lifecycle_support"].ROOT = ROOT
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_pipeline_health"].summarize = (
    lambda *_a, **_k: types.SimpleNamespace(
        salvage_eligible_count=0,
        stage2_work_item_count=0,
        starvation=False,
        reason="ok",
    )
)
sys.modules["pr_lifecycle_pipeline_health"].is_never_touch_key = lambda *_a, **_k: False
sys.modules["pr_lifecycle_pipeline_health"].list_reselect_candidates = (
    lambda *_a, **_k: []
)
sys.modules["pr_lifecycle_pipeline_health"].MECHANICAL_RESELECT_NA = (
    "Recover unique source only on a new focused draft."
)
sys.modules["pr_lifecycle_pipeline_health"].ReselectSignals = (
    lambda **kw: types.SimpleNamespace(
        **{
            "live_mergeable_by_key": None,
            "titles_by_key": None,
            "unique_paths_by_key": None,
            **kw,
        }
    )
)
sys.modules["pr_lifecycle_pipeline_health"].source_pr_prefix = (
    lambda key: str(key or "").split("@", 1)[0]
)
sys.modules["pr_lifecycle_pipeline_health"].non_journal_paths = (
    lambda paths: list(paths or [])
)
sys.modules["pr_lifecycle_pipeline_health"].SALVAGE_OUTCOMES = frozenset(
    {"HOLD_CONTRACT", "HOLD_EVIDENCE", "NOT_RUN"}
)
sys.modules["pr_lifecycle_reconcile"].collect_actions = lambda *_a, **_k: []
sys.modules["pr_lifecycle_feed"].build_feed = lambda *_a, **_k: {
    "empty_with_stock": False,
    "reason": "FEED_OK",
    "work_item_count": 0,
    "eligible_stock_count": 0,
    "work_items": [],
}

import pr_lifecycle_run as run

for _name in _STUB_NAMES:
    _saved = _saved_modules[_name]
    if _saved is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _saved


def _report(**overrides):
    values = {
        "salvage_eligible_count": 0,
        "stage2_work_item_count": 0,
        "starvation": False,
        "reason": "ok",
    }
    values.update(overrides)
    return types.SimpleNamespace(**values)


class RunPlanTests(unittest.TestCase):
    def test_stage2_never_merges_in_plan(self):
        ledger = {"ledger_revision": 9, "items": []}
        config = {"lifecycle": {}}

        class FakeReport:
            salvage_eligible_count = 0
            stage2_work_item_count = 0
            starvation = False
            reason = "ok"

        with (
            mock.patch.object(run.health, "summarize", return_value=FakeReport()),
            mock.patch.object(
                run.feed_mod,
                "build_feed",
                return_value={
                    "empty_with_stock": False,
                    "reason": "FEED_OK",
                    "work_item_count": 0,
                    "eligible_stock_count": 0,
                    "work_items": [],
                },
            ),
        ):
            plan = run.build_stage_plan(2, ledger, config)
        self.assertFalse(plan.get("stage2_may_merge"))
        self.assertFalse(plan.get("calibration_enabled"))
        self.assertEqual(plan["stage"], 2)

    def test_stage3_mentions_advisory_bot_threads(self):
        ledger = {"ledger_revision": 9, "items": []}
        config = {"lifecycle": {}}

        class FakeReport:
            salvage_eligible_count = 0
            stage2_work_item_count = 0
            starvation = False
            reason = "ok"

        with mock.patch.object(run.health, "summarize", return_value=FakeReport()):
            plan = run.build_stage_plan(3, ledger, config)
        blob = str(plan).lower()
        self.assertIn("advisory", blob)
        self.assertFalse(plan.get("calibration_enabled"))

    def test_stage1_uses_bounded_reconciliation_and_always_checks_feed(self):
        ledger = {"ledger_revision": 11, "items": []}
        action = {"action": "TERMINAL_CLOSED", "key": "owner/repo#1@sha"}
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.reconcile_mod, "collect_actions", return_value=[action]
            ) as collect,
        ):
            plan = run.build_stage_plan(1, ledger, {"lifecycle": {}})
        collect.assert_called_once_with(ledger, {"lifecycle": {}}, limit=40)
        self.assertEqual(plan["actions"][0], action)
        self.assertEqual(plan["actions"][-1]["action"], "FEED_CHECK")
        self.assertIn("schema-aware only", " ".join(plan["allowed_commands"]))

    def test_stage2_materializes_work_items_without_merge_authority(self):
        work_item = {"source_key": "owner/repo#1@sha", "reason": "SALVAGE_ELIGIBLE"}
        feed_payload = {
            "empty_with_stock": False,
            "reason": "FEED_OK",
            "work_item_count": 1,
            "eligible_stock_count": 1,
            "work_items": [work_item],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["actions"][0]["action"], "FEED_SUMMARY")
        self.assertEqual(plan["actions"][1], {"action": "SALVAGE_WI", "wi": work_item})
        self.assertIsNone(plan["stop_class"])
        self.assertFalse(plan["stage2_may_merge"])

    def test_stage2_empty_feed_with_stock_is_a_logic_stop(self):
        feed_payload = {
            "empty_with_stock": True,
            "reason": "EMPTY_FEED_WITH_ELIGIBLE_STOCK",
            "work_item_count": 0,
            "eligible_stock_count": 2,
            "work_items": [],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")

    def test_invalid_stage_fails_closed_with_no_allowed_commands(self):
        with mock.patch.object(run.health, "summarize", return_value=_report()):
            plan = run.build_stage_plan(99, {"ledger_revision": 2}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "invalid stage 99")
        self.assertEqual(plan["allowed_commands"], [])
        self.assertEqual(plan["actions"], [])

    def test_status_document_is_a_bounded_summary(self):
        plan = {
            "stage": 2,
            "ledger_revision": 12,
            "reason": "FEED_OK",
            "stop_class": None,
            "pipeline_health": {"starvation": False},
            "actions": [{"action": "FEED_SUMMARY"}, {"action": "SALVAGE_WI"}],
        }
        status = run.write_status_doc(plan, "run-fixed")
        self.assertEqual(status["run_id"], "run-fixed")
        self.assertEqual(status["action_count"], 2)
        self.assertFalse(status["calibration_enabled"])
        self.assertNotIn("actions", status)


class RunExecutionTests(unittest.TestCase):
    def test_run_stage_writes_plan_and_status_records(self):
        plan = {
            "stage": 1,
            "ledger_revision": 12,
            "pipeline_health": {"starvation": False},
            "actions": [{"action": "FEED_CHECK"}],
            "reason": "OK",
            "stop_class": None,
            "calibration_enabled": False,
            "stage2_may_merge": False,
            "allowed_commands": [],
        }
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            with (
                mock.patch.object(run, "LOG_DIR", log_dir),
                mock.patch.object(run, "_run_id", return_value="run-fixed"),
                mock.patch.object(
                    run, "load_yaml", side_effect=[{"lifecycle": {}}, {"items": []}]
                ),
                mock.patch.object(run, "validate_config"),
                mock.patch.object(
                    run.cas,
                    "run_preflight",
                    return_value={"ledger_path": "ledger.yaml"},
                    create=True,
                ),
                mock.patch.object(run, "build_stage_plan", return_value=plan.copy()),
            ):
                output = StringIO()
                with redirect_stdout(output):
                    result = run.run_stage(1, dry_run=True, write_status=True)
            self.assertEqual(result, 0)
            emitted = json.loads(output.getvalue())
            self.assertEqual(emitted["run_id"], "run-fixed")
            self.assertTrue(emitted["dry_run"])
            records = [
                json.loads(line)
                for line in (log_dir / "run-fixed.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                [record["event"] for record in records], ["plan", "status"]
            )
            status = json.loads(
                (log_dir / run.STATUS_PATH_ON_BRANCH).read_text(encoding="utf-8")
            )
            self.assertEqual(status["action_count"], 1)

    def test_run_stage_records_transient_preflight_failure(self):
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            with (
                mock.patch.object(run, "LOG_DIR", log_dir),
                mock.patch.object(run, "_run_id", return_value="run-error"),
                mock.patch.object(
                    run, "load_yaml", side_effect=[{"lifecycle": {}}, OSError()]
                ),
                mock.patch.object(run, "validate_config"),
                mock.patch.object(
                    run.cas,
                    "run_preflight",
                    return_value={"ledger_path": "ledger.yaml"},
                    create=True,
                ),
            ):
                output = StringIO()
                with redirect_stdout(output):
                    result = run.run_stage(1, dry_run=True, write_status=False)
            self.assertEqual(result, 1)
            record = json.loads(output.getvalue())
            self.assertEqual(record["stop_class"], "TRANSIENT_RETRY")
            self.assertEqual(record["error"], "OSError")
            self.assertTrue((log_dir / "run-error.jsonl").is_file())

    def test_update_pinned_issue_edits_exact_title_match(self):
        listed = types.SimpleNamespace(
            returncode=0,
            stdout='[{"number": 17, "title": "PR pipeline status"}]',
        )
        edited = types.SimpleNamespace(returncode=0, stdout="")
        with mock.patch("subprocess.run", side_effect=[listed, edited]) as command:
            run.update_pinned_issue(
                {
                    "updated_at_utc": "2026-09-21T18:00:00Z",
                    "run_id": "run-fixed",
                    "stage": 1,
                    "ledger_revision": 12,
                    "reason": "OK",
                    "stop_class": None,
                }
            )
        self.assertEqual(command.call_count, 2)
        argv = command.call_args_list[1].args[0]
        self.assertEqual(argv[2:4], ["edit", "17"])
        self.assertIn("--repo", argv)

    def test_update_pinned_issue_creates_when_listing_is_malformed(self):
        listed = types.SimpleNamespace(returncode=0, stdout="not-json")
        created = types.SimpleNamespace(returncode=0, stdout="")
        with mock.patch("subprocess.run", side_effect=[listed, created]) as command:
            run.update_pinned_issue(
                {
                    "updated_at_utc": "2026-09-21T18:00:00Z",
                    "run_id": "run-fixed",
                    "stage": None,
                    "reason": "manual --status refresh",
                    "stop_class": None,
                }
            )
        self.assertEqual(command.call_args_list[1].args[0][2], "create")

    def test_main_requires_stage_when_not_refreshing_status(self):
        error = StringIO()
        with redirect_stderr(error):
            result = run.main([])
        self.assertEqual(result, 1)
        self.assertIn("--stage is required", error.getvalue())



class Option3RebalancePlanTests(unittest.TestCase):
    def test_stage1_enqueue_cap_and_unique_path_override(self):
        candidates = [
            {
                "key": f"abhimehro/demo#{pr}@head",
                "repository": "abhimehro/demo",
                "pr": pr,
                "base_sha": "a" * 40,
                "head_sha": "b" * 40,
                "changed_paths": ["src/old.py"],
            }
            for pr in range(1, 7)
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates[:5]
        ) as select:
            planned = run.plan_stage2_enqueues(
                {"items": candidates},
                signals=run.health.ReselectSignals(
                    unique_paths_by_key={"abhimehro/demo#1": ["src/unique.py"]}
                ),
            )
        self.assertEqual(select.call_args.kwargs["limit"], 5)
        self.assertEqual(planned["candidate_count"], 5)
        self.assertEqual(planned["enqueued_count"], 5)
        self.assertEqual(
            [action["source_key"] for action in planned["enqueue_actions"]],
            [candidate["key"] for candidate in candidates[:5]],
        )
        first = planned["enqueue_actions"][0]
        self.assertEqual(first["allowed_paths"], ["src/unique.py"])
        self.assertEqual(first["base_sha"], "a" * 40)
        self.assertEqual(first["head_sha"], "b" * 40)
        self.assertEqual(
            first["next_action"], run.health.MECHANICAL_RESELECT_NA
        )
        self.assertTrue(
            all(
                action["action"] == "ENQUEUE_STAGE2_WI"
                for action in planned["enqueue_actions"]
            )
        )

    def test_stage1_partial_enqueue_reports_incomplete_candidate(self):
        complete = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["src/demo.py"],
        }
        incomplete = {**complete, "key": "abhimehro/demo#2@head", "head_sha": ""}
        ledger = {"ledger_revision": 1, "items": [complete, incomplete]}
        original = copy.deepcopy(ledger)
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=ledger["items"]
            ),
        ):
            plan = run.build_stage_plan(1, ledger, {})
        self.assertEqual(ledger, original)
        self.assertEqual(
            [action["action"] for action in plan["actions"]],
            ["ENQUEUE_STAGE2_WI", "FEED_CHECK"],
        )
        self.assertEqual(plan["actions"][0]["source_key"], complete["key"])
        self.assertEqual(plan["actions"][0]["allowed_paths"], ["src/demo.py"])
        self.assertEqual(plan["actions"][1]["reselect_candidates"], 2)
        self.assertEqual(plan["actions"][1]["enqueued"], 1)
        self.assertEqual(
            plan["actions"][1]["skipped_incomplete"],
            [{"source_key": incomplete["key"], "reason": "INCOMPLETE_WI_FIELDS"}],
        )
        self.assertEqual(plan["actions"][1]["grade"], "PASS")
        self.assertIsNone(plan["stop_class"])

    def test_stage1_all_incomplete_candidates_fail_feed_check(self):
        incomplete = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "",
            "changed_paths": ["src/demo.py"],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=[incomplete]
            ),
        ):
            plan = run.build_stage_plan(1, {"items": [incomplete]}, {})
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["FEED_CHECK"]
        )
        self.assertEqual(plan["actions"][0]["grade"], "FAIL")
        self.assertEqual(plan["actions"][0]["enqueued"], 0)
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "FEED_CHECK_FAIL")

    def test_stage2_mixed_feed_salvages_only_usable_sources(self):
        never_touch = {"source_item_key": "abhimehro/Seatek_Analysis#692@head"}
        usable = {"source_key": "abhimehro/demo#8@head"}
        feed_payload = {
            "empty_with_stock": False,
            "reason": "FEED_OK",
            "work_item_count": 2,
            "eligible_stock_count": 1,
            "work_items": [never_touch, usable],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
            mock.patch.object(
                run.health,
                "is_never_touch_key",
                side_effect=lambda key: key.startswith(
                    "abhimehro/Seatek_Analysis#692@"
                ),
            ),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["reason"], "OK")
        self.assertFalse(plan["skip_cursor"])
        self.assertEqual(plan["mechanical_candidate_count"], 1)
        self.assertEqual(
            plan["never_touch_skipped"],
            [{"source_key": never_touch["source_item_key"], "reason": "NEVER_TOUCH"}],
        )
        self.assertEqual(
            [action["action"] for action in plan["actions"]],
            ["FEED_SUMMARY", "SALVAGE_WI"],
        )
        self.assertIs(plan["actions"][1]["wi"], usable)

    def test_stage3_handoff_requires_owner_state_and_salvage_outcome(self):
        base = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        candidates = [
            base,
            {**base, "key": "abhimehro/demo#2@head", "current_owner": "stage1"},
            {
                **base,
                "key": "abhimehro/demo#3@head",
                "lifecycle_state": "WAITING_HUMAN",
            },
            {
                **base,
                "key": "abhimehro/demo#4@head",
                "guardrail_outcome": "REVIEW_SECURITY",
            },
            {
                **base,
                "key": "abhimehro/demo#5@head",
                "guardrail_outcome": "HOLD_EVIDENCE",
            },
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates
        ):
            actions = run.plan_stage3_mechanical_handoffs({"items": candidates})
        self.assertEqual(
            [action["source_key"] for action in actions],
            [candidates[0]["key"], candidates[4]["key"]],
        )
        self.assertTrue(
            all(
                action["action"] == "HANDOFF_MECHANICAL_TO_STAGE2"
                for action in actions
            )
        )
        self.assertEqual(
            [action["reason"] for action in actions],
            ["CONFLICTING_UNIQUE_RESELECT", "CONFLICTING_UNIQUE_RESELECT"],
        )

    def test_stage3_handoff_cap_applies_after_owner_and_outcome_filter(self):
        base = {
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        candidates = [
            {**base, "key": "demo#1@head", "current_owner": "stage1"},
            {**base, "key": "demo#2@head", "guardrail_outcome": "REVIEW_SECURITY"},
            {**base, "key": "demo#3@head"},
            {**base, "key": "demo#4@head"},
            {**base, "key": "demo#5@head"},
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates
        ) as select:
            actions = run.plan_stage3_mechanical_handoffs(
                {"items": candidates}, limit=2
            )
        self.assertNotIn("limit", select.call_args.kwargs)
        self.assertEqual(
            [action["source_key"] for action in actions],
            ["demo#3@head", "demo#4@head"],
        )

    def test_stage2_stop_with_stock_takes_precedence_over_never_touch_filter(self):
        feed_payload = {
            "empty_with_stock": True,
            "reason": "EMPTY_FEED_WITH_ELIGIBLE_STOCK",
            "work_item_count": 1,
            "eligible_stock_count": 1,
            "work_items": [{"source_item_key": "abhimehro/ctrld-sync#1206@head"}],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
            mock.patch.object(run.health, "is_never_touch_key", return_value=True),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 1}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")
        self.assertFalse(plan["skip_cursor"])
        self.assertEqual(plan["mechanical_candidate_count"], 0)
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["FEED_SUMMARY"]
        )

    def test_stage1_emits_enqueue_when_reselect_candidates_exist(self):
        candidate = {
            "key": "abhimehro/personal-config#2069@abc",
            "repository": "abhimehro/personal-config",
            "pr": 2069,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["maintenance/bin/analytics_dashboard.sh"],
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=[candidate]
            ),
        ):
            plan = run.build_stage_plan(1, {"ledger_revision": 1}, {})
        enqueue = [a for a in plan["actions"] if a["action"] == "ENQUEUE_STAGE2_WI"]
        self.assertEqual(len(enqueue), 1)
        self.assertEqual(enqueue[0]["reason"], "CONFLICTING_UNIQUE_RESELECT")
        feed = plan["actions"][-1]
        self.assertEqual(feed["action"], "FEED_CHECK")
        self.assertEqual(feed["grade"], "PASS")
        self.assertEqual(feed["enqueued"], 1)
        self.assertIsNone(plan["stop_class"])

    def test_stage1_feed_check_fails_when_candidates_not_enqueued(self):
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run,
                "plan_stage2_enqueues",
                return_value={
                    "candidate_count": 2,
                    "enqueued_count": 0,
                    "skipped_incomplete": [
                        {
                            "source_key": "owner/repo#1@a",
                            "reason": "INCOMPLETE_WI_FIELDS",
                        }
                    ],
                    "enqueue_actions": [],
                },
            ),
        ):
            plan = run.build_stage_plan(1, {"ledger_revision": 1}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "FEED_CHECK_FAIL")
        feed = plan["actions"][-1]
        self.assertEqual(feed["grade"], "FAIL")

    def test_stage2_skip_if_empty_exits_success_without_docs_pr(self):
        feed_payload = {
            "empty_with_stock": False,
            "reason": "EMPTY_FEED",
            "work_item_count": 0,
            "eligible_stock_count": 0,
            "work_items": [],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["reason"], "EMPTY_INTAKE_SKIP")
        self.assertIsNone(plan["stop_class"])
        self.assertTrue(plan.get("skip_cursor"))
        self.assertTrue(plan.get("empty_intake_skip"))
        self.assertEqual(plan["actions"][0]["action"], "SKIP_IF_EMPTY")
        self.assertFalse(plan["stage2_may_merge"])

    def test_stage2_filters_never_touch_then_may_skip(self):
        feed_payload = {
            "empty_with_stock": False,
            "reason": "FEED_OK",
            "work_item_count": 1,
            "eligible_stock_count": 0,
            "work_items": [
                {
                    "source_key": "abhimehro/ctrld-sync#1206@deadbeef",
                    "reason": "EXPIRED_PACKET_OR_CLOSE_STALE",
                }
            ],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
            mock.patch.object(run.health, "is_never_touch_key", return_value=True),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["reason"], "EMPTY_INTAKE_SKIP")
        self.assertTrue(plan.get("skip_cursor"))
        self.assertEqual(plan["actions"][0]["action"], "SKIP_IF_EMPTY")

    def test_stage3_handoff_and_closed_noop_deferred(self):
        candidate = {
            "key": "abhimehro/personal-config#2092@abc",
            "repository": "abhimehro/personal-config",
            "pr": 2092,
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=[candidate]
            ),
        ):
            plan = run.build_stage_plan(3, {"ledger_revision": 3}, {})
        kinds = [a["action"] for a in plan["actions"]]
        self.assertIn("CLOSED_NOOP_DEFERRED", kinds)
        self.assertIn("HANDOFF_MECHANICAL_TO_STAGE2", kinds)
        self.assertIn("ADVISORY_BOT_THREADS", kinds)



if __name__ == "__main__":
    unittest.main()
