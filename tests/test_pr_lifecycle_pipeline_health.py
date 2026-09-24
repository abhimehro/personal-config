"""Pipeline health: Stage 2 starvation and salvage-eligible classification.

Install pinned `requirements.txt` (`jsonschema==4.26.0`) before running this
module; Ubuntu system jsonschema is not sufficient.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health
import pr_lifecycle_validation as validator
import yaml
from sync_cursor_export_prompts import expand_prompt_source

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
HEALTH_SCRIPT = SCRIPTS / "pr_lifecycle_pipeline_health.py"
EXAMPLE_LEDGER = ROOT / "tasks/pr-lifecycle-ledger.example.yaml"

# (label, item overrides, expected eligible)
CLASSIFIER_CASES: tuple[tuple[str, dict[str, Any], bool], ...] = (
    ("recover unique HOLD_CONTRACT", {}, True),
    (
        "REVIEW_SECURITY",
        {"guardrail_outcome": "REVIEW_SECURITY"},
        False,
    ),
    (
        "lockfile HOLD_CONTRACT",
        {
            "sensitive_paths": ["lockfiles_and_major_dependencies"],
            "next_action": "Stage 3: HOLD_CONTRACT uv.lock. Do not merge.",
        },
        False,
    ),
    (
        "HOLD_CANONICAL",
        {
            "guardrail_outcome": "HOLD_CANONICAL",
            "next_action": "Stage 1 canonical-pick cluster",
        },
        False,
    ),
    ("HUMAN", {"author_type": "HUMAN"}, False),
    (
        "HOLD_PLATFORM Swift",
        {
            "guardrail_outcome": "HOLD_PLATFORM",
            "next_action": "Linux cannot run make guardrails",
        },
        False,
    ),
    (
        "unrecognized sticky",
        {"sensitive_paths": ["network_browser_origins"]},
        False,
    ),
    ("lint repair", {"next_action": "Fix ruff lint on src/foo.py"}, True),
    (
        "import repair",
        {"next_action": "Add TYPE_CHECKING import for Foo"},
        True,
    ),
    ("wrap repair", {"next_action": "wrap export to 88 columns"}, True),
    (
        "non-major pin",
        {"next_action": "non-major pin patch for requests"},
        True,
    ),
    (
        "missing test",
        {"next_action": "Add the missing test named in the work item"},
        True,
    ),
    (
        "conflict marker",
        {"next_action": "Remove conflict markers in src/foo.py"},
        True,
    ),
    (
        "DIRTY unique remaining",
        {"next_action": "DIRTY unique remaining source after 0cs journal"},
        True,
    ),
    (
        "do not import",
        {"next_action": "HOLD_CONTRACT: do not import optional ML deps"},
        False,
    ),
    (
        "NOT_RUN mechanical overflow",
        {"guardrail_outcome": "NOT_RUN"},
        True,
    ),
    (
        "human owner WAITING_HUMAN",
        {
            "current_owner": "human",
            "lifecycle_state": "WAITING_HUMAN",
        },
        False,
    ),
    (
        "stage2 owner",
        {
            "current_owner": "stage2",
            "lifecycle_state": "STAGE2_QUEUED",
        },
        False,
    ),
    ("unknown owner", {"current_owner": "desk"}, False),
    ("none owner", {"current_owner": "none"}, False),
    (
        "stage1 owner",
        {
            "current_owner": "stage1",
            "lifecycle_state": "STAGE1_INTAKE",
        },
        True,
    ),
)


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "key": "abhimehro/demo#1@abc",
        "author_type": "BOT",
        "lifecycle_state": "STAGE3_RECONCILIATION",
        "current_owner": "stage3",
        "guardrail_outcome": "HOLD_CONTRACT",
        "sensitive_paths": ["generated_output"],
        "next_action": (
            "Recover unique source only on a new focused draft that "
            "excludes .jules/journals/"
        ),
    }
    base.update(overrides)
    return base


def _work_item(**overrides: object) -> dict[str, object]:
    sha = "0123456789abcdef0123456789abcdef01234567"
    base: dict[str, object] = {
        "work_item_id": "s2-20260830-demo",
        "source_item_key": f"abhimehro/demo#1@{sha}",
        "repository": "abhimehro/demo",
        "pr": 1,
        "base_sha": sha,
        "head_sha": sha,
        "allowed_paths": ["src/demo.py"],
        "prohibited_paths": [],
        "repair_description": "Repair the demo path.",
        "required_test_command": "python3 -m unittest",
        "expected_test_result": "ok",
        "acceptance_criteria": ["Allowed path changes only."],
        "provenance_urls": ["https://github.com/abhimehro/demo/pull/1"],
        "expiry_utc": "2026-08-31T12:00:00Z",
        "attempt_count": 0,
        "current_owner": "stage2",
        "creation_event_id": "evt-20260830-demo",
        "history": [],
    }
    base.update(overrides)
    return base


def _ledger(
    items: list[dict[str, object]],
    work_items: list[dict[str, object]],
    revision: int = 1,
) -> dict[str, object]:
    return {
        "ledger_revision": revision,
        "items": items,
        "stage2_work_items": work_items,
    }


def _schema_valid_starved_ledger() -> dict[str, Any]:
    ledger = copy.deepcopy(yaml.safe_load(EXAMPLE_LEDGER.read_text(encoding="utf-8")))
    keeper = ledger["items"][0]
    keeper["lifecycle_state"] = "STAGE3_RECONCILIATION"
    keeper["current_owner"] = "stage3"
    keeper["next_owner"] = "stage3"
    keeper["next_action"] = (
        "Recover unique source only on a new focused draft that "
        "excludes .jules/journals/"
    )
    ledger["stage2_work_items"] = []
    events = []
    for event in ledger["events"]:
        if event["event_id"] == "evt-2026-stage2-ack-001":
            continue
        if event["event_id"] == "evt-2026-stage1-stage2-001":
            event = dict(event)
            event["to_owner"] = "stage3"
            event["to_state"] = "STAGE3_RECONCILIATION"
            event["next_owner"] = "stage3"
            event["reason"] = "Stage 1 overflowed salvage-eligible remainder."
        events.append(event)
    ledger["events"] = events
    return ledger


def _run_cli(*cli_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HEALTH_SCRIPT), *cli_args],
        check=False,
        capture_output=True,
        text=True,
    )


class TestSalvageEligibleClassifier(unittest.TestCase):
    def test_classifier_table(self) -> None:
        for label, overrides, expected in CLASSIFIER_CASES:
            with self.subTest(label):
                actual = health.is_salvage_eligible(_item(**overrides))
                self.assertEqual(actual, expected)


class TestPipelineHealthSummarize(unittest.TestCase):
    def test_starvation_when_eligible_and_empty_stage2(self) -> None:
        report = health.summarize(_ledger([_item()], [], revision=30))
        self.assertTrue(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 1)

    def test_no_starvation_when_nothing_is_eligible(self) -> None:
        blocked = _item(
            guardrail_outcome="REVIEW_SECURITY",
            next_action="Human packet",
        )
        report = health.summarize(_ledger([blocked], []))
        self.assertFalse(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 0)

    def test_work_item_expiry_gates_starvation(self) -> None:
        cases = (
            ("queued future", "2026-08-31T12:00:00Z", False, 1),
            ("expired", "2026-08-29T12:00:00Z", True, 0),
            ("malformed", "not-a-timestamp", True, 0),
            ("far future", "2026-09-01T00:00:00Z", False, 1),
        )
        for label, expiry, starved, wi_count in cases:
            with self.subTest(label):
                report = health.summarize(
                    _ledger([_item()], [_work_item(expiry_utc=expiry)]),
                    now=NOW,
                )
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)

    def test_owned_item_starvation_matrix(self) -> None:
        owned = _item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )
        remainder = _item(key="abhimehro/demo#2@def")
        cases = (
            ("owned no WI plus remainder", [owned, remainder], [], True, 0, 1, 1),
            ("owned no WI no remainder", [owned], [], False, 0, 1, 0),
            (
                "owned plus usable WI plus remainder",
                [owned, remainder],
                [_work_item()],
                False,
                1,
                1,
                1,
            ),
        )
        for label, items, wis, starved, wi_count, owned_count, eligible in cases:
            with self.subTest(label):
                report = health.summarize(_ledger(items, wis), now=NOW)
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)
                self.assertEqual(report.stage2_owned_item_count, owned_count)
                self.assertEqual(report.salvage_eligible_count, eligible)

    def test_attempt_count_zero_and_empty_optional_lists_are_usable(self) -> None:
        report = health.summarize(
            _ledger(
                [_item()],
                [_work_item(attempt_count=0, prohibited_paths=[], history=[])],
            ),
            now=NOW,
        )
        self.assertFalse(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 1)

    def test_incomplete_work_item_does_not_suppress_starvation(self) -> None:
        incomplete = _work_item()
        del incomplete["repository"]
        report = health.summarize(_ledger([_item()], [incomplete]), now=NOW)
        self.assertTrue(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 0)

    def test_empty_required_strings_do_not_suppress_starvation(self) -> None:
        cases = (
            ("empty repair_description", {"repair_description": ""}),
            ("empty work_item_id", {"work_item_id": ""}),
            ("empty required_test_command", {"required_test_command": ""}),
        )
        for label, overrides in cases:
            with self.subTest(label):
                report = health.summarize(
                    _ledger([_item()], [_work_item(**overrides)]),
                    now=NOW,
                )
                self.assertTrue(report.starvation)
                self.assertEqual(report.stage2_work_item_count, 0)

    def test_required_work_item_fields_match_schema(self) -> None:
        schema_path = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = tuple(schema["$defs"]["stage2WorkItem"]["required"])
        self.assertEqual(health.REQUIRED_WORK_ITEM_FIELDS, expected)


class TestPipelineHealthCli(unittest.TestCase):
    def _write(self, ledger: dict[str, object]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "runtime-ledger.yaml"
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
        return path

    def test_cli_exit_2_on_starvation(self) -> None:
        path = self._write(_schema_valid_starved_ledger())
        proc = _run_cli(str(path))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("starvation=true", proc.stdout)

    def test_cli_sanitizes_persisted_projection_fields(self) -> None:
        ledger = _schema_valid_starved_ledger()
        ledger["items"][0]["latest_transition"] = "evt-2026-stage1-stage2-001"
        ledger["items"][0]["latest_transition_kind"] = "HANDOFF"
        path = self._write(ledger)
        proc = _run_cli(str(path))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("starvation=true", proc.stdout)

    def test_cli_json_and_exit_0_when_clear(self) -> None:
        proc = _run_cli("--json", str(EXAMPLE_LEDGER))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["starvation"])
        self.assertEqual(payload["stage2_work_item_count"], 0)
        self.assertGreaterEqual(payload["stage2_owned_item_count"], 1)

    def test_cli_exit_1_on_schema_invalid_items_mapping(self) -> None:
        path = self._write({"items": [], "stage2_work_items": []})
        proc = _run_cli(str(path))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PR_LIFECYCLE_HEALTH_ERROR", proc.stderr)

    def test_cli_refuses_pointer_copies_and_non_ledger(self) -> None:
        path_pointer = ROOT / "tasks" / "pr-lifecycle-ledger.yaml"
        self.assertTrue(path_pointer.is_file())
        proc = _run_cli(str(path_pointer))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing main-branch pointer", proc.stderr)

        pointer = yaml.safe_load(path_pointer.read_text(encoding="utf-8"))
        cases = (
            ("copied pointer", pointer, "refusing main-branch pointer"),
            ("arbitrary mapping", {"foo": "bar"}, "not a runtime ledger mapping"),
        )
        for label, document, needle in cases:
            with self.subTest(label):
                copied = self._write(document)
                result = _run_cli(str(copied))
                self.assertEqual(result.returncode, 1)
                self.assertIn(needle, result.stderr)


class TestStagePromptContracts(unittest.TestCase):
    """Stage prompts are thin bootstraps that defer to pr_lifecycle_run plans."""

    def _prompt(self, name: str) -> str:
        return expand_prompt_source(ROOT / "docs/cursor-automations/prompts" / name)

    def test_review_prompt_feeds_stage2_via_runner(self) -> None:
        review = self._prompt("daily-pr-review.md")
        self.assertIn("pr_lifecycle_run.py --stage 1", review)
        self.assertIn("emitted plan", review)
        self.assertIn("pr_lifecycle_feed.py", review)
        self.assertIn("run record", review)

    def test_salvage_prompt_heal_forward_without_merging(self) -> None:
        """The salvage prompt must heal starvation without invented merges."""
        salvage = self._prompt("daily-pr-salvage.md")
        self.assertIn("pr_lifecycle_run.py --stage 2", salvage)
        self.assertIn("never merges", salvage)
        self.assertIn("EMPTY_FEED_WITH_ELIGIBLE_STOCK", salvage)
        self.assertIn("LOGIC_STOP", salvage)
        self.assertIn("heal-forward", salvage)
        self.assertIn("Minimal WI intake", salvage)

    def test_review_prompt_schema_aware_cas_only(self) -> None:
        review = self._prompt("daily-pr-review.md")
        self.assertIn("Schema-aware CAS", review)
        self.assertIn("raw YAML", review)

    def test_completion_prompt_re_reads_predicates(self) -> None:
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("pr_lifecycle_run.py --stage 3", completion)
        self.assertIn("Re-read predicates", completion)

    def test_completion_prompt_bot_thread_advisory(self) -> None:
        """The completion prompt binds the Abhi-approved bot-thread policy."""
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("advisory", completion)
        self.assertIn("Codacy", completion)
        self.assertIn("REVIEW.md", completion)

    def test_completion_prompt_live_stage3_not_calibration(self) -> None:
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("live Stage 3", completion)
        self.assertIn("Calibration stays", completion)

    def test_pr_desk_flags_starvation(self) -> None:
        """The PR Desk profile must expose starvation indicators."""
        profile = (ROOT / "docs/grok-bot/pr-desk.profile.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("salvage-eligible", profile)
        self.assertIn("Write Nothing", profile)
        self.assertIn("66a8e7a8-9c42-11f1-ba66-0e7d0216e441", profile)
        self.assertIn("d9d2c058-9c42-11f1-ba66-0e7d0216e441", profile)

    def test_stage_prompts_shared_ownership(self) -> None:
        """Stage prompts bind the lifecycle contract; ownership prose lives there."""
        for name, stage in (
            ("daily-pr-review.md", "--stage 1"),
            ("daily-pr-salvage.md", "--stage 2"),
            ("daily-pr-completion.md", "--stage 3"),
        ):
            with self.subTest(name):
                text = " ".join(self._prompt(name).split())
                self.assertIn("docs/automated-pr-lifecycle.md", text)
                self.assertIn(f"scripts/pr_lifecycle_run.py {stage}", text)
                self.assertIn("run record", text)
                self.assertIn("Schema-aware CAS", text)
                self.assertIn("force-push", text)
                self.assertIn("Calibration stays", text)
        contract = (ROOT / "docs" / "automated-pr-lifecycle.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Shared ownership", contract)
        self.assertIn("development partners", contract)
        self.assertIn("security-first development partners", contract)
        self.assertIn("`REVIEW.md`", contract)
        self.assertIn("Citing those files is not enough", contract)

    def test_calibration_prompt_keeps_legacy_contract(self) -> None:
        """The calibration prompt is unchanged by the bootstrap rebalance."""
        calibration = self._prompt("daily-pr-completion.calibration.md")
        self.assertIn('--message "automated lifecycle ledger update"', calibration)
        self.assertIn("docs/automated-pr-lifecycle.md", calibration)
        self.assertIn("Memory is enabled", calibration)
        self.assertNotIn("{{include:", calibration)

    def test_stage_caps_are_80_40_10_and_15(self) -> None:
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        caps = config["lifecycle"]["stage_caps"]
        self.assertEqual(caps["stage1_inventory"], 80)
        self.assertEqual(caps["stage1_actions"], 40)
        self.assertEqual(caps["stage2_salvage_candidates"], 10)
        self.assertEqual(caps["stage3_completion_actions"], 15)
        self.assertEqual(config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4")



class ReselectCandidateTests(unittest.TestCase):
    def test_reselect_rejects_terminal_and_non_salvage_outcomes(self):
        base = _item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        for outcome in (
            "REVIEW_SECURITY",
            "HOLD_PLATFORM",
            "HOLD_CANONICAL",
            "PASS_ROUTINE",
            "CLOSE_NONSECURITY_NOOP",
            "ANALYSIS_ERROR",
        ):
            with self.subTest(outcome=outcome):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        {**base, "guardrail_outcome": outcome}
                    )
                )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {**base, "lifecycle_state": "TERMINAL"}
            )
        )

    def test_reselect_requires_non_journal_unique_remaining_paths(self):
        item = _item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT DIRTY unique remaining",
        )
        self.assertTrue(health.is_reselect_salvage_candidate(item))
        for paths in ([], [".jules/journal.md"], ["notes/.jules/journal.md"]):
            with self.subTest(paths=paths):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item, unique_remaining_paths=paths
                    )
                )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, unique_remaining_paths=[".jules/journal.md", "src/unique.py"]
            )
        )

    def test_palette_shell_sticky_requires_only_allowlisted_paths(self):
        item = _item(
            sensitive_paths=["shell_execution"],
            next_action="Palette wrap CONFLICTING unique remaining",
        )
        allowed = (
            "analytics_dashboard.sh",
            "maintenance/bin/refresh.sh",
            "docs/cursor-automations/prompts/daily-pr-review.md",
        )
        for path in allowed:
            with self.subTest(allowed=path):
                self.assertTrue(
                    health.is_reselect_salvage_candidate(
                        item, unique_remaining_paths=[".jules/journal.md", path]
                    )
                )
        for paths in (
            [".jules/journal.md"],
            ["maintenance/bin/refresh.sh", "scripts/deploy.sh"],
            ["maintenance/bin/refresh.py"],
        ):
            with self.subTest(blocked=paths):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item, unique_remaining_paths=paths
                    )
                )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {**item, "next_action": "CONFLICTING unique remaining"},
                unique_remaining_paths=["maintenance/bin/refresh.sh"],
            )
        )

    def test_title_bot_prefixes_do_not_admit_arbitrary_human_titles(self):
        item = _item(
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        for prefix in (
            "⚡ Bolt",
            "🎨 Palette",
            "salvage(",
            "chore(qa)",
            "chore(repo-health)",
        ):
            with self.subTest(prefix=prefix):
                self.assertTrue(
                    health.is_reselect_salvage_candidate(
                        item, title=f"  {prefix} focused repair"
                    )
                )
        for title in (None, "Human repair", "Review ⚡ Bolt repair"):
            with self.subTest(title=title):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(item, title=title)
                )

    def test_reselect_candidate_lookup_accepts_source_prefix_metadata(self):
        key = "abhimehro/demo#7@abc"
        item = _item(
            key=key,
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="Needs live verification",
        )
        ledger = _ledger([item, _item(key="", changed_paths=["src/other.py"])], [])
        selected = health.list_reselect_candidates(
            ledger,
            signals=health.ReselectSignals(
                live_mergeable_by_key={"abhimehro/demo#7": "DIRTY"},
                titles_by_key={"abhimehro/demo#7": "⚡ Bolt: repair"},
                unique_paths_by_key={"abhimehro/demo#7": ["src/unique.py"]},
            ),
        )
        self.assertEqual([entry["key"] for entry in selected], [key])

    def test_palette_conflicting_soft_shell_sticky_is_reselect(self):
        item = _item(
            key="abhimehro/personal-config#2069@abc",
            sensitive_paths=["shell_execution", "generated_output"],
            changed_paths=[
                "maintenance/bin/analytics_dashboard.sh",
                "docs/cursor-automations/prompts/daily-pr-salvage.md",
            ],
            next_action=(
                "HOLD_CONTRACT Palette wrap + analytics_dashboard.sh CONFLICTING."
            ),
        )
        self.assertTrue(health.is_reselect_salvage_candidate(item))
        # Soft sticky still blocks classic salvage_eligible (monitor unchanged).
        self.assertFalse(health.is_salvage_eligible(item))

    def test_never_touch_seatek_692_and_ctrld_1206(self):
        base = _item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {**base, "key": "abhimehro/Seatek_Analysis#692@dead"}
            )
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {
                    **base,
                    "key": "abhimehro/ctrld-sync#1206@dead",
                    "sensitive_paths": ["security_configuration"],
                }
            )
        )
        self.assertTrue(health.is_never_touch_key("abhimehro/ctrld-sync#1206@dead"))

    def test_review_security_and_lockfile_only_blocked(self):
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                _item(
                    guardrail_outcome="REVIEW_SECURITY",
                    next_action="CONFLICTING security twin",
                    changed_paths=["validate_data.py"],
                )
            )
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                _item(
                    sensitive_paths=["lockfiles_and_major_dependencies"],
                    changed_paths=["uv.lock"],
                    next_action="HOLD_CONTRACT CONFLICTING lockfile major-dep",
                )
            )
        )

    def test_live_mergeable_required_conflicting_or_dirty(self):
        item = _item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT do not merge without unique language",
        )
        self.assertFalse(health.is_reselect_salvage_candidate(item))
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="CONFLICTING")
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live_mergeable="DIRTY", unique_remaining_paths=["src/demo.py"]
            )
        )

    def test_live_mergeability_overrides_stale_conflicting_action(self):
        item = _item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(item, live_mergeable="MERGEABLE")
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="dirty")
        )

    def test_explicit_empty_unique_signal_does_not_reselect_stale_paths(self):
        item = _item(
            changed_paths=["src/old.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        selected = health.list_reselect_candidates(
            _ledger([item], []),
            signals=health.ReselectSignals(unique_paths_by_key={item["key"]: []}),
        )
        self.assertEqual(selected, [])

    def test_palette_shell_sticky_rejects_near_match_paths(self):
        item = _item(
            sensitive_paths=["shell_execution", "generated_output"],
            next_action="Palette wrap DIRTY unique remaining",
        )
        for path in (
            "maintenance/bin/refresh.py",
            "docs/cursor-automations-copy/prompt.md",
            "scripts/deploy.sh",
        ):
            with self.subTest(path=path):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item,
                        unique_remaining_paths=["maintenance/bin/refresh.sh", path],
                    )
                )

    def test_title_allowlist_for_non_bot_ledger_author(self):
        item = _item(
            author_type="HUMAN",
            changed_paths=["maintenance/bin/analytics_dashboard.sh"],
            sensitive_paths=["shell_execution", "generated_output"],
            next_action="Palette wrap CONFLICTING",
        )
        self.assertFalse(health.is_reselect_salvage_candidate(item))
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, title="🎨 Palette: wrap analytics dashboard"
            )
        )

    def test_list_reselect_candidates_respects_limit(self):
        items = [
            _item(
                key=f"abhimehro/personal-config#{n}@abc",
                pr=n,
                changed_paths=["src/demo.py"],
                next_action="HOLD_CONTRACT CONFLICTING unique remaining",
                sensitive_paths=["generated_output"],
            )
            for n in (100, 101, 102)
        ]
        ledger = _ledger(items, [])
        got = health.list_reselect_candidates(ledger, limit=2)
        self.assertEqual(len(got), 2)



if __name__ == "__main__":
    unittest.main()
