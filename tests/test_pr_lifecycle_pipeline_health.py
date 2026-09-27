"""Pipeline health: Stage 2 starvation and salvage-eligible classification.

Install pinned `requirements.txt` (`jsonschema==4.26.0`) before running this
module; Ubuntu system jsonschema is not sufficient.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402

from tests.pr_lifecycle_helpers import (  # noqa: E402
    NOW,
    make_item,
    make_ledger,
    make_work_item,
)

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


class TestSalvageEligibleClassifier(unittest.TestCase):
    def test_classifier_table(self) -> None:
        """Verify salvage eligibility across the classifier cases."""
        for label, overrides, expected in CLASSIFIER_CASES:
            with self.subTest(label):
                actual = health.is_salvage_eligible(make_item(**overrides))
                self.assertEqual(actual, expected)


class TestPipelineHealthSummarize(unittest.TestCase):
    def test_reselect_count_is_independent_of_starvation_eligibility(self) -> None:
        """A soft-sticky reselect candidate must not widen salvage stock."""
        ordinary = make_item(
            key="abhimehro/demo#1@head",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        palette = make_item(
            key="abhimehro/demo#2@head",
            changed_paths=["maintenance/bin/wrap.sh"],
            sensitive_paths=["shell_execution"],
            next_action="Palette wrap CONFLICTING unique remaining",
        )
        blocked = make_item(
            key="abhimehro/Seatek_Analysis#692@head",
            changed_paths=["src/blocked.py"],
            guardrail_outcome="REVIEW_SECURITY",
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        report = health.summarize(
            make_ledger([ordinary, palette, blocked], []), now=NOW
        )
        self.assertEqual(report.reselect_candidate_count, 2)
        self.assertEqual(report.salvage_eligible_count, 1)
        self.assertTrue(report.starvation)

    def test_starvation_when_eligible_and_empty_stage2(self) -> None:
        """Verify eligible stock with empty Stage 2 intake is starvation."""
        report = health.summarize(make_ledger([make_item()], [], revision=30))
        self.assertTrue(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 1)

    def test_no_starvation_when_nothing_is_eligible(self) -> None:
        """Verify no starvation when nothing is eligible."""
        blocked = make_item(
            guardrail_outcome="REVIEW_SECURITY",
            next_action="Human packet",
        )
        report = health.summarize(make_ledger([blocked], []))
        self.assertFalse(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 0)

    def test_work_item_expiry_gates_starvation(self) -> None:
        """Verify only unexpired work items prevent starvation."""
        cases = (
            ("queued future", "2026-08-31T12:00:00Z", False, 1),
            ("expired", "2026-08-29T12:00:00Z", True, 0),
            ("malformed", "not-a-timestamp", True, 0),
            ("far future", "2026-09-01T00:00:00Z", False, 1),
        )
        for label, expiry, starved, wi_count in cases:
            with self.subTest(label):
                report = health.summarize(
                    make_ledger([make_item()], [make_work_item(expiry_utc=expiry)]),
                    now=NOW,
                )
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)

    def test_owned_item_starvation_matrix(self) -> None:
        """Verify Stage 2 ownership and queued work affect starvation separately."""
        owned = make_item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )
        remainder = make_item(key="abhimehro/demo#2@def")
        cases = (
            ("owned no WI plus remainder", [owned, remainder], [], True, 0, 1, 1),
            ("owned no WI no remainder", [owned], [], False, 0, 1, 0),
            (
                "owned plus usable WI plus remainder",
                [owned, remainder],
                [make_work_item()],
                False,
                1,
                1,
                1,
            ),
        )
        for label, items, wis, starved, wi_count, owned_count, eligible in cases:
            with self.subTest(label):
                report = health.summarize(make_ledger(items, wis), now=NOW)
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)
                self.assertEqual(report.stage2_owned_item_count, owned_count)
                self.assertEqual(report.salvage_eligible_count, eligible)

    def test_attempt_count_zero_and_empty_optional_lists_are_usable(self) -> None:
        """Verify attempt count zero and empty optional lists are usable."""
        report = health.summarize(
            make_ledger(
                [make_item()],
                [make_work_item(attempt_count=0, prohibited_paths=[], history=[])],
            ),
            now=NOW,
        )
        self.assertFalse(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 1)

    def test_incomplete_work_item_does_not_suppress_starvation(self) -> None:
        """Verify incomplete work item does not suppress starvation."""
        incomplete = make_work_item()
        del incomplete["repository"]
        report = health.summarize(make_ledger([make_item()], [incomplete]), now=NOW)
        self.assertTrue(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 0)

    def test_empty_required_strings_do_not_suppress_starvation(self) -> None:
        """Verify empty required strings do not suppress starvation."""
        cases = (
            ("empty repair_description", {"repair_description": ""}),
            ("empty work_item_id", {"work_item_id": ""}),
            ("empty required_test_command", {"required_test_command": ""}),
        )
        for label, overrides in cases:
            with self.subTest(label):
                report = health.summarize(
                    make_ledger([make_item()], [make_work_item(**overrides)]),
                    now=NOW,
                )
                self.assertTrue(report.starvation)
                self.assertEqual(report.stage2_work_item_count, 0)

    def test_required_work_item_fields_match_schema(self) -> None:
        schema_path = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = tuple(schema["$defs"]["stage2WorkItem"]["required"])
        self.assertEqual(health.REQUIRED_WORK_ITEM_FIELDS, expected)


class TestPredicateHardening(unittest.TestCase):
    """Tests for #2298: title normalization, UNKNOWN mergeable, head-SHA, author gate."""

    def test_exact_title_signal_overrides_prefix_even_when_empty(self) -> None:
        """Verify exact-key titles override PR prefixes, including empty titles."""
        item = make_item(
            author_type="HUMAN",
            author_login="maintainer",
            next_action="CONFLICTING",
            changed_paths=["src/demo.py"],
        )
        prefix = "abhimehro/demo#1"
        cases = (
            ({prefix: "chore(qa): tests"}, True),
            ({prefix: "chore(qa): tests", item["key"]: ""}, False),
            ({prefix: "chore(qa): tests", item["key"]: "feat: unrelated"}, False),
            ({prefix: "feat: unrelated", item["key"]: "chore(qa): tests"}, True),
        )
        for titles, expected in cases:
            with self.subTest(titles=titles):
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=health.ReselectSignals(titles_by_key=titles),
                        allowed_authors=("maintainer",),
                    ),
                    [item] if expected else [],
                )

    def test_live_path_override_rechecks_sensitive_path_allowlist(self) -> None:
        """Verify live paths must satisfy the sensitive-path allowlist."""
        item = make_item(
            next_action="DIRTY Palette wrap",
            sensitive_paths=["shell_execution"],
            changed_paths=["scripts/analytics_dashboard.sh"],
        )
        cases = (
            (["scripts/analytics_dashboard.sh"], True),
            ([".jules/notes.md", "scripts/analytics_dashboard.sh"], True),
            (["scripts/unrelated.sh"], False),
            (["scripts/analytics_dashboard.sh", "scripts/unrelated.sh"], False),
            ([], False),
        )
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=health.ReselectSignals(
                            unique_paths_by_key={item["key"]: paths}
                        ),
                        allowed_authors=(),
                    ),
                    [item] if expected else [],
                )

    def test_disabling_author_gate_preserves_other_exclusions(self) -> None:
        """Verify bypassing author checks retains title, head, and state gates."""
        cases = (
            ({}, "chore(qa): tests", "abc", True),
            ({}, "feat: unrelated", "abc", False),
            ({}, None, "abc", False),
            ({}, "chore(qa): tests", "new-head", False),
            ({"lifecycle_state": "TERMINAL"}, "chore(qa): tests", "abc", False),
            ({"current_owner": "stage2"}, "chore(qa): tests", "abc", False),
            (
                {"guardrail_outcome": "REVIEW_SECURITY"},
                "chore(qa): tests",
                "abc",
                False,
            ),
        )
        for overrides, title, head, expected in cases:
            with self.subTest(overrides=overrides, title=title, head=head):
                item = make_item(
                    author_type="HUMAN",
                    head_sha="abc",
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                    **overrides,
                )
                signals = health.ReselectSignals(
                    titles_by_key={item["key"]: title},
                    live_head_sha_by_key={item["key"]: head},
                )
                with mock.patch.object(
                    health, "_load_reselect_allowed_authors"
                ) as load:
                    candidates = health.list_reselect_candidates(
                        make_ledger([item], []), signals=signals, author_gate=False
                    )
                load.assert_not_called()
                self.assertEqual(candidates, [item] if expected else [])

    def test_live_exclusions_do_not_consume_candidate_limit(self) -> None:
        """Verify excluded PRs leave room for eligible candidates under the cap."""
        items = [
            make_item(
                key=f"owner/repo#{n}@abc",
                head_sha="abc",
                next_action="CONFLICTING",
                changed_paths=["src/demo.py"],
            )
            for n in range(1, 6)
        ]
        signals = health.ReselectSignals(
            closed_keys=frozenset({items[0]["key"]}),
            live_head_sha_by_key={items[1]["key"]: "new-head"},
            live_mergeable_by_key={items[2]["key"]: "MERGEABLE"},
        )
        self.assertEqual(
            health.list_reselect_candidates(
                make_ledger(items, []), signals=signals, limit=1, allowed_authors=()
            ),
            [items[3]],
        )

    def test_queued_prefixes_expire_at_the_supplied_clock(self) -> None:
        """Verify queued PR prefixes stop blocking at their exact expiry time."""
        for expiry, expected in (
            ("2026-08-30T11:59:59Z", set()),
            ("2026-08-30T12:00:00Z", set()),
            ("2026-08-30T12:00:01Z", {"owner/repo#1"}),
        ):
            with self.subTest(expiry=expiry):
                work_item = make_work_item(
                    source_item_key="owner/repo#1@old-head", expiry_utc=expiry
                )
                self.assertEqual(
                    health.existing_wi_prefixes(make_ledger([], [work_item]), now=NOW),
                    expected,
                )

    def test_all_authoritative_nonconflict_states_override_stale_ledger(self) -> None:
        """Verify known live nonconflict states override stale conflict text."""
        item = make_item(changed_paths=["src/demo.py"], next_action="CONFLICTING")
        for state in (
            "MERGEABLE",
            "CLEAN",
            "BLOCKED",
            "BEHIND",
            "UNSTABLE",
            "HAS_HOOKS",
        ):
            with self.subTest(state=state):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item, live_mergeable=f"  {state.lower()}  ", allowed_authors=()
                    )
                )

    def test_live_head_requires_nonempty_matching_ledger_head(self) -> None:
        """Verify supplied live heads require a nonempty, normalized SHA match."""
        for ledger_head, live_head, expected in (
            (None, "abc", False),
            ("", "abc", False),
            ("  ", "abc", False),
            ("abc", "", False),
            ("abc", "  ", False),
            (" ABC ", " abc ", True),
            (None, None, True),
        ):
            with self.subTest(ledger_head=ledger_head, live_head=live_head):
                item = make_item(
                    head_sha=ledger_head,
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                )
                self.assertEqual(
                    health.is_reselect_salvage_candidate(
                        item, live_head_sha=live_head, allowed_authors=()
                    ),
                    expected,
                )

    def test_ledger_author_formats_and_precedence(self) -> None:
        """Verify author formats, fallback order, and rejection of missing logins."""
        cases = (
            ({"author": {"login": " maintainer "}}, True),
            ({"author": " maintainer "}, True),
            ({"author_login": " maintainer "}, True),
            ({"author": {"login": ""}, "author_login": "maintainer"}, True),
            ({"author": {"login": 12}, "author_login": "maintainer"}, True),
            ({"author": {"login": "outsider"}, "author_login": "maintainer"}, False),
            ({"author": "outsider", "author_login": "maintainer"}, False),
            ({"author_login": 12}, False),
            ({}, False),
        )
        for author_fields, expected in cases:
            with self.subTest(author_fields=author_fields):
                item = make_item(
                    author_type="HUMAN",
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                    **author_fields,
                )
                self.assertEqual(
                    health.is_reselect_salvage_candidate(
                        item,
                        title="chore(qa): add tests",
                        allowed_authors=("maintainer",),
                    ),
                    expected,
                )

    def test_live_author_overrides_ledger_author_in_both_directions(self) -> None:
        """Verify live authors can grant or revoke title-based eligibility."""
        for ledger_author, live_author, expected in (
            ("maintainer", "outsider", False),
            ("outsider", "maintainer", True),
        ):
            with self.subTest(ledger_author=ledger_author, live_author=live_author):
                item = make_item(
                    author_type="HUMAN",
                    author=ledger_author,
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                )
                signals = health.ReselectSignals(
                    titles_by_key={item["key"]: "chore(qa): tests"},
                    author_login_by_key={item["key"]: live_author},
                )
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=signals,
                        allowed_authors=("maintainer",),
                    ),
                    [item] if expected else [],
                )

    def test_full_key_head_and_author_signals_override_prefix_values(self) -> None:
        """Verify exact-key head and author signals take precedence over prefixes."""
        item = make_item(
            head_sha="abc",
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        key = item["key"]
        prefix = "abhimehro/demo#1"
        # Prefix-only signals apply to a current head; exact-head signals win.
        cases = (
            ({prefix: "abc"}, {prefix: "maintainer"}, True),
            ({prefix: "abc", key: "different"}, {prefix: "maintainer"}, False),
            ({prefix: "different", key: "abc"}, {prefix: "maintainer"}, True),
            ({prefix: "abc"}, {prefix: "maintainer", key: "outsider"}, False),
            ({prefix: "abc"}, {prefix: "outsider", key: "maintainer"}, True),
        )
        for heads, authors, expected in cases:
            with self.subTest(heads=heads, authors=authors):
                signals = health.ReselectSignals(
                    titles_by_key={prefix: "chore(qa): tests"},
                    live_head_sha_by_key=heads,
                    author_login_by_key=authors,
                )
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=signals,
                        allowed_authors=("maintainer",),
                    ),
                    [item] if expected else [],
                )

    def test_closed_signal_does_not_exclude_another_head_or_pr(self) -> None:
        """Verify closed signals do not exclude unrelated PR keys or revisions."""
        item = make_item(changed_paths=["src/demo.py"], next_action="CONFLICTING")
        for closed_key in (
            "abhimehro/demo#1@old-head",
            "abhimehro/demo#10",
            "other/demo#1",
        ):
            with self.subTest(closed_key=closed_key):
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=health.ReselectSignals(
                            closed_keys=frozenset({closed_key})
                        ),
                        allowed_authors=(),
                    ),
                    [item],
                )

    def test_author_allowlist_reloads_between_batches_but_not_between_items(
        self,
    ) -> None:
        """Verify each candidate batch loads one fresh author allowlist."""
        items = [
            make_item(
                key=f"demo#{n}@abc",
                author_type="HUMAN",
                author="maintainer",
                changed_paths=["src/demo.py"],
                next_action="CONFLICTING",
            )
            for n in (1, 2)
        ]
        signals = health.ReselectSignals(
            titles_by_key={item["key"]: "chore(qa): tests" for item in items}
        )
        with mock.patch.object(
            health,
            "_load_reselect_allowed_authors",
            side_effect=[("maintainer",), ("other",)],
        ) as loader:
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger(items, []), signals=signals
                ),
                items,
            )
            loader.assert_called_once_with()
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger(items, []), signals=signals
                ),
                [],
            )
            self.assertEqual(loader.call_count, 2)

    def test_explicit_empty_allowlist_does_not_fall_back_to_config(self) -> None:
        """Verify an explicit empty allowlist rejects authors without loading config."""
        item = make_item(
            author_type="HUMAN",
            author="abhimehro",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        signals = health.ReselectSignals(titles_by_key={item["key"]: "⚡ Bolt: test"})
        with mock.patch.object(health, "_load_reselect_allowed_authors") as loader:
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger([item], []), signals=signals, allowed_authors=()
                ),
                [],
            )
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger([item], []), signals=signals, author_gate=False
                ),
                [item],
            )
        loader.assert_not_called()

    def test_explicit_config_authors_take_precedence_over_disk(self) -> None:
        """Verify supplied author configuration avoids reading the disk config."""
        config = {
            "bot_authors": ["custom[bot]"],
            "identity_classification": {"maintainer_token_logins": ["maintainer"]},
        }
        with mock.patch.object(health, "load_yaml") as load:
            self.assertEqual(
                health._load_reselect_allowed_authors(config),
                ("custom[bot]", "maintainer"),
            )
        load.assert_not_called()

    def test_disk_allowlist_supports_bot_only_and_maintainer_only_config(self) -> None:
        """Verify disk config can supply either bots or maintainers independently."""
        cases = (
            (
                {"bot_authors": ["custom[bot]"], "identity_classification": []},
                ("custom[bot]",),
            ),
            (
                {
                    "identity_classification": {
                        "maintainer_token_logins": ["maintainer"]
                    }
                },
                ("maintainer",),
            ),
        )
        for config, expected in cases:
            with self.subTest(config=config), mock.patch.object(
                health, "CONFIG_PATH"
            ) as path, mock.patch.object(health, "load_yaml", return_value=config):
                path.is_file.return_value = True
                self.assertEqual(health._load_reselect_allowed_authors({}), expected)

    def test_title_prefix_normalization(self) -> None:
        """Titles with FE0F, no space, extra spaces, and lowercase all match; feat: Bolt and Bolted do not."""
        matching_titles = (
            "⚡ Bolt: test something",
            "⚡Bolt: test something",
            "⚡\ufe0f Bolt: test variation selector",
            "⚡\ufe0e Bolt: test variation selector",
            "⚡\ufe0fBolt: test compact",
            "⚡\u200bBolt: zero width space",
            "⚡\u200c\u200dBolt: zwnj and zwj",
            "⚡\u2060Bolt: word joiner",
            "⚡   bolt: extra spaces and lowercase",
            "🎨 Palette: update css",
            "🎨Palette: update css",
            "🎨\ufe0f Palette: variation selector",
            "🎨\ufe0fPalette: variation selector",
            "🎨\u200bPalette: zero width space",
            "salvage(pc-100): test salvage",
            "chore(qa): update tests",
            "chore(repo-health): clean up repo",
        )
        non_matching_titles = (
            "feat: Bolt",
            "Bolted",
            "feat: ⚡ Bolt",
            "fix: palette",
            "chore: qa",
            "random title",
            "",
            None,
        )
        for title in matching_titles:
            with self.subTest(matching_title=title):
                self.assertTrue(
                    health._title_is_reselect_bot(title),
                    f"Expected title to match: {title!r}",
                )
        for title in non_matching_titles:
            with self.subTest(non_matching_title=title):
                self.assertFalse(
                    health._title_is_reselect_bot(title),
                    f"Expected title NOT to match: {title!r}",
                )

    def test_live_mergeable_unknown_falls_back_to_next_action(self) -> None:
        """live_mergeable='UNKNOWN' falls back to next_action; 'MERGEABLE' excludes."""
        item = make_item(
            key="abhimehro/demo#1@abc",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        # UNKNOWN should fall back to next_action (which has CONFLICTING) -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="UNKNOWN")
        )
        # empty or None should fall back to next_action -> candidate
        self.assertTrue(health.is_reselect_salvage_candidate(item, live_mergeable=""))
        self.assertTrue(health.is_reselect_salvage_candidate(item, live_mergeable=None))
        # MERGEABLE is authoritative -> excluded (not in CONFLICTING/DIRTY)
        self.assertFalse(
            health.is_reselect_salvage_candidate(item, live_mergeable="MERGEABLE")
        )
        # CLEAN is authoritative -> excluded
        self.assertFalse(
            health.is_reselect_salvage_candidate(item, live_mergeable="CLEAN")
        )
        # DIRTY and CONFLICTING are authoritative -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="DIRTY")
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="CONFLICTING")
        )

    def test_head_sha_mismatch_excludes_item(self) -> None:
        """Head-SHA mismatch excludes item; matching or omitted signal is unchanged."""
        item = make_item(
            key="abhimehro/demo#1@abc1234",
            head_sha="abc1234",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        # Matching head SHA -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_head_sha="abc1234")
        )
        # Case-insensitive match -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_head_sha="ABC1234")
        )
        # No signal (None) -> unchanged candidate
        self.assertTrue(health.is_reselect_salvage_candidate(item, live_head_sha=None))
        # Mismatch -> excluded
        self.assertFalse(
            health.is_reselect_salvage_candidate(item, live_head_sha="def5678")
        )

        # In list_reselect_candidates with ReselectSignals
        ledger = make_ledger([item], [])
        match_signals = health.ReselectSignals(
            live_head_sha_by_key={item["key"]: "abc1234"}
        )
        self.assertEqual(
            len(health.list_reselect_candidates(ledger, signals=match_signals)), 1
        )
        mismatch_signals = health.ReselectSignals(
            live_head_sha_by_key={item["key"]: "drifted_sha"}
        )
        self.assertEqual(
            len(health.list_reselect_candidates(ledger, signals=mismatch_signals)), 0
        )

    def test_author_gate_for_title_only_identity(self) -> None:
        """Title-only with author gate on: maintainer/bot -> candidate; human -> excluded; no live login -> ledger author decides; no login at all -> excluded (fails closed)."""
        item = make_item(
            key="abhimehro/demo#1@abc1234",
            author="abhimehro",
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        title = "⚡ Bolt: fix something"

        # Maintainer login -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, title=title, author_login="abhimehro"
            )
        )
        # Bot login -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, title=title, author_login="google-labs-jules[bot]"
            )
        )
        # Arbitrary human login -> excluded
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                item, title=title, author_login="random-external-user"
            )
        )
        # Missing login signal with maintainer in ledger -> candidate (ledger fallback)
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, title=title, author_login=None)
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, title=title, author_login="")
        )
        # Missing login signal with external human in ledger -> rejected (never for humans)
        human_item = make_item(
            key="abhimehro/demo#1@abc1234",
            author="random-external-user",
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                human_item, title=title, author_login=None
            )
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                human_item, title=title, author_login=""
            )
        )
        # No login signal and no ledger author -> rejected (gate fails closed)
        anon_item = {k: v for k, v in item.items() if k != "author"}
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                anon_item, title=title, author_login=None
            )
        )
        # Author gate disabled -> candidate even with random human
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item,
                title=title,
                author_login="random-external-user",
                author_gate=False,
            )
        )

        # Ledger-BOT item bypasses author gate and title check
        bot_item = make_item(
            key="abhimehro/demo#2@abc1234",
            author_type="BOT",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                bot_item, title="non-matching title", author_login="random-user"
            )
        )

    @mock.patch.object(
        health, "_load_reselect_allowed_authors", return_value=("abhimehro",)
    )
    def test_summarize_threads_signals(self, _allowed_authors: mock.Mock) -> None:
        """summarize() with signals reflects live candidate count."""
        # Non-BOT item that qualifies only with title signal
        item = make_item(
            key="abhimehro/demo#1@abc1234",
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        ledger = make_ledger([item], [])

        # Without signals: titles_by_key is empty, title=None -> 0 reselect candidates
        report_default = health.summarize(ledger)
        self.assertEqual(report_default.reselect_candidate_count, 0)

        # With title signal: qualifies as candidate
        signals = health.ReselectSignals(
            titles_by_key={item["key"]: "⚡ Bolt: live title"},
            author_login_by_key={item["key"]: "abhimehro"},
        )
        report_with_signals = health.summarize(ledger, signals=signals)
        self.assertEqual(report_with_signals.reselect_candidate_count, 1)


class TestReselectRound2(unittest.TestCase):
    """Closed-key exclusion and allowlist-loader error handling."""

    def _conflicting_bot_item(self) -> dict[str, Any]:
        """Build a conflicting bot candidate for testing live closed signals."""
        return make_item(
            key="abhimehro/demo#9@abc",
            author_type="BOT",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )

    def test_closed_keys_exclude_stale_ledger_candidates(self) -> None:
        """A live CLOSED/MERGED key is excluded even if ledger text says CONFLICTING."""
        item = self._conflicting_bot_item()
        ledger = make_ledger([item], [])
        self.assertEqual(len(health.list_reselect_candidates(ledger)), 1)
        for closed in (item["key"], "abhimehro/demo#9"):
            with self.subTest(closed=closed):
                signals = health.ReselectSignals(closed_keys=frozenset({closed}))
                self.assertEqual(
                    health.list_reselect_candidates(ledger, signals=signals), []
                )

    def test_allowlist_invalid_yaml_warns_and_uses_builtin(self) -> None:
        """Unreadable config logs a warning and falls back to the built-in list."""
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "config.yaml"
            bad.write_text("bot_authors: [unclosed\n", encoding="utf-8")
            with mock.patch.object(health, "CONFIG_PATH", bad), self.assertLogs(
                "pr_lifecycle_pipeline_health", level="WARNING"
            ) as logs:
                authors = health._load_reselect_allowed_authors()
        self.assertIn("dependabot[bot]", authors)
        self.assertIn("ValueError", "\n".join(logs.output))

    def test_allowlist_unrelated_errors_propagate(self) -> None:
        """Errors outside OSError/ValueError are not swallowed."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.yaml"
            cfg.write_text("bot_authors: []\n", encoding="utf-8")
            with mock.patch.object(health, "CONFIG_PATH", cfg), mock.patch.object(
                health, "load_yaml", side_effect=RuntimeError("boom")
            ):
                with self.assertRaises(RuntimeError):
                    health._load_reselect_allowed_authors()
