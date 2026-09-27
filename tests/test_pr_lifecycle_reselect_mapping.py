#!/usr/bin/env python3
"""Tests for pr_lifecycle_reselect_signals.py live-payload signal folding."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402
from pr_lifecycle_reselect_signals import produce_reselect_signals  # noqa: E402

from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_gh_proc,
    make_ledger,
    make_queryable_item,
    stub_gh_runner,
)


class TestReselectSignalMapping(unittest.TestCase):
    def test_blank_optional_fields_do_not_override_ledger_fallbacks(self) -> None:
        """Verify invalid optional fields preserve fallback to ledger values."""
        item = make_queryable_item(repository="owner/repo", pr=1)
        for title, head, author in (
            (None, None, None),
            ("  ", "\t", {"login": "  "}),
            (42, [], "maintainer"),
        ):
            with self.subTest(title=title, head=head, author=author):
                runner = stub_gh_runner(
                    {
                        "state": "OPEN",
                        "mergeable": "CONFLICTING",
                        "title": title,
                        "headRefOid": head,
                        "author": author,
                    }
                )
                result = produce_reselect_signals(
                    make_ledger([item], []), runner=runner
                )
                self.assertEqual(result.status, "OK")
                self.assertEqual(
                    result.signals,
                    health.ReselectSignals(
                        live_mergeable_by_key={item["key"]: "CONFLICTING"},
                        live_base_sha_by_key={item["key"]: "b" * 40},
                    ),
                )

    def test_files_boundary_and_missing_files_preserve_ledger_fallback(self) -> None:
        """Verify only complete file lists override ledger paths and eligibility."""
        item = make_queryable_item(
            repository="abhimehro/demo",
            pr=1,
            changed_paths=["src/ledger.py"],
            next_action="CONFLICTING",
        )
        cases = (
            ([], [], False, False),
            (
                [{"path": f"src/{n}.py"} for n in range(99)],
                [f"src/{n}.py" for n in range(99)],
                False,
                True,
            ),
            ([{"path": f"src/{n}.py"} for n in range(100)], None, True, True),
            ([{"path": "src/ok.py"}, {}], None, True, True),
            ([{"path": ""}], None, True, True),
            (None, None, False, True),
            ({}, None, False, True),
        )
        for files, expected_paths, truncated, eligible in cases:
            with self.subTest(files=files):
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=stub_gh_runner({"state": "OPEN", "files": files}),
                )
                self.assertEqual(result.status, "OK")
                self.assertEqual(
                    result.truncated_keys, (item["key"],) if truncated else ()
                )
                self.assertEqual(
                    result.signals.unique_paths_by_key,
                    None if expected_paths is None else {item["key"]: expected_paths},
                )
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=result.signals,
                        author_gate=health.ReselectAuthorGate(allowed_authors=()),
                    ),
                    [item] if eligible else [],
                )

    def test_unknown_pr_state_does_not_leak_other_payload_fields(self) -> None:
        """Verify unrecognized PR states contribute no other response fields."""
        item = make_queryable_item(repository="abhimehro/demo", pr=1)
        for state in (None, "", "DRAFT", "unknown"):
            with self.subTest(state=state):
                payload = {
                    "state": state,
                    "mergeable": "CONFLICTING",
                    "title": "⚡ Bolt: stale",
                    "headRefOid": "new-head",
                    "author": {"login": "abhimehro"},
                    "files": [{"path": "src/demo.py"}],
                }
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=stub_gh_runner(payload),
                )
                self.assertEqual(result.status, "OK")
                self.assertEqual(result.signals, health.ReselectSignals())

    def test_merge_state_precedence_and_normalization(self) -> None:
        """Verify mergeability normalization, conflict precedence, and fallback."""
        item = make_queryable_item(repository="abhimehro/demo", pr=1)
        cases = (
            (" mergeable ", " dirty ", "DIRTY"),
            (" conflicting ", " blocked ", "CONFLICTING"),
            ("UNKNOWN", " behind ", "BEHIND"),
            (None, "unstable", "UNSTABLE"),
            ("UNKNOWN", "has_hooks", "HAS_HOOKS"),
            ("UNKNOWN", "unrecognized", None),
        )
        for mergeable, merge_status, expected in cases:
            with self.subTest(mergeable=mergeable, merge_status=merge_status):
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=stub_gh_runner(
                        {
                            "state": " open ",
                            "mergeable": mergeable,
                            "mergeStateStatus": merge_status,
                        }
                    ),
                )
                self.assertEqual(
                    result.signals.live_mergeable_by_key,
                    {item["key"]: expected} if expected else None,
                )

    def test_successful_mapping_of_all_fields(self) -> None:
        """Live PR response populates mergeable, title, headRefOid, author, and non-journal files."""
        item = make_queryable_item(
            key="abhimehro/personal-config#100@old-sha",
            repository="abhimehro/personal-config",
            pr=100,
        )
        ledger = make_ledger([item], [])

        fake_resp = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "DIRTY",
            "title": "⚡ Bolt: optimize startup",
            "headRefOid": "live-sha-999",
            "author": {"login": "google-labs-jules[bot]"},
            "files": [
                {"path": ".jules/journal.md"},
                {"path": "scripts/startup.sh"},
            ],
        }

        def fake_runner(
            cmd: list[str], timeout_s: float
        ) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                return make_gh_proc("d" * 40)
            self.assertIn("100", cmd)
            self.assertIn("abhimehro/personal-config", cmd)
            return make_gh_proc(fake_resp)

        result = produce_reselect_signals(ledger, runner=fake_runner)

        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(result.truncated_keys, ())
        self.assertGreaterEqual(result.elapsed_s, 0.0)

        signals = result.signals
        key = item["key"]
        self.assertEqual(signals.live_mergeable_by_key, {key: "CONFLICTING"})
        self.assertEqual(signals.titles_by_key, {key: "⚡ Bolt: optimize startup"})
        self.assertEqual(signals.live_head_sha_by_key, {key: "live-sha-999"})
        # The base anchor arrives via the `gh api` enrichment call.
        self.assertEqual(signals.live_base_sha_by_key, {key: "d" * 40})
        self.assertEqual(signals.author_login_by_key, {key: "google-labs-jules[bot]"})
        self.assertEqual(signals.unique_paths_by_key, {key: ["scripts/startup.sh"]})

    def test_mergeable_and_merge_state_status_priority(self) -> None:
        """Mapping: CONFLICTING, DIRTY, MERGEABLE, other authoritative mergeStateStatus; UNKNOWN -> omitted."""
        cases = (
            ("CONFLICTING", "CLEAN", "CONFLICTING"),
            ("UNKNOWN", "DIRTY", "DIRTY"),
            ("MERGEABLE", "CLEAN", "MERGEABLE"),
            ("UNKNOWN", "BLOCKED", "BLOCKED"),  # authoritative mergeStateStatus wins
            ("UNKNOWN", "UNKNOWN", None),  # UNKNOWN is omitted
        )
        for mergeable, m_status, expected in cases:
            with self.subTest(mergeable=mergeable, m_status=m_status):
                item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)
                ledger = make_ledger([item], [])
                resp = {
                    "state": "OPEN",
                    "mergeable": mergeable,
                    "mergeStateStatus": m_status,
                    "title": "demo title",
                }
                result = produce_reselect_signals(ledger, runner=stub_gh_runner(resp))
                if expected:
                    self.assertEqual(
                        result.signals.live_mergeable_by_key, {item["key"]: expected}
                    )
                else:
                    self.assertIsNone(result.signals.live_mergeable_by_key)

    def test_files_truncation_and_journal_only(self) -> None:
        """Files >= 100 -> omitted from unique_paths_by_key, in truncated_keys; journal only -> []."""
        # Truncated case
        item1 = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)
        resp1 = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "files": [{"path": f"src/file_{i}.py"} for i in range(100)],
        }
        res1 = produce_reselect_signals(
            make_ledger([item1], []), runner=stub_gh_runner(resp1)
        )
        self.assertIsNone(res1.signals.unique_paths_by_key)
        self.assertEqual(res1.truncated_keys, (item1["key"],))

        # Journal-only case
        item2 = make_queryable_item(key="demo#2@sha", repository="demo", pr=2)
        resp2 = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "files": [{"path": ".jules/journal.md"}, {"path": "sub/.jules/note.md"}],
        }
        res2 = produce_reselect_signals(
            make_ledger([item2], []), runner=stub_gh_runner(resp2)
        )
        self.assertEqual(res2.signals.unique_paths_by_key, {item2["key"]: []})
        self.assertEqual(res2.truncated_keys, ())

        # Corrupted / incomplete file entry case
        item3 = make_queryable_item(key="demo#3@sha", repository="demo", pr=3)
        resp3 = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "files": [{"path": "src/ok.py"}, "not-a-dict"],
        }
        res3 = produce_reselect_signals(
            make_ledger([item3], []), runner=stub_gh_runner(resp3)
        )
        self.assertIsNone(res3.signals.unique_paths_by_key)
        self.assertEqual(res3.truncated_keys, (item3["key"],))

    def test_closed_or_merged_pr_emits_no_signals(self) -> None:
        """Closed or merged PR emits no signals for that key."""
        item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)
        resp = {
            "state": "MERGED",
            "mergeable": "MERGEABLE",
            "title": "⚡ Bolt: already merged",
            "files": [{"path": "src/demo.py"}],
        }
        result = produce_reselect_signals(
            make_ledger([item], []), runner=stub_gh_runner(resp)
        )
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.failed_keys, ())
        self.assertIsNone(result.signals.live_mergeable_by_key)
        self.assertIsNone(result.signals.titles_by_key)
        self.assertIsNone(result.signals.unique_paths_by_key)
        self.assertEqual(result.signals.closed_keys, frozenset({item["key"]}))

    def test_closed_keys_only_for_authoritative_terminal_states(self) -> None:
        """CLOSED/MERGED populate closed_keys; missing/unknown state stays unclassified."""
        cases = (("CLOSED", True), ("merged", True), ("", False), ("DRAFT", False))
        for state, closed in cases:
            with self.subTest(state=state):
                item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)
                resp = {"state": state, "mergeable": "CONFLICTING"}
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=stub_gh_runner(resp),
                )
                if closed:
                    self.assertEqual(
                        result.signals.closed_keys, frozenset({item["key"]})
                    )
                else:
                    self.assertIsNone(result.signals.closed_keys)
                self.assertIsNone(result.signals.live_mergeable_by_key)


if __name__ == "__main__":
    unittest.main()
