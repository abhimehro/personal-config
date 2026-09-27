"""Unit regressions for isolation and conservative signal accumulation."""

from __future__ import annotations

import copy
import unittest

from tests.pr_lifecycle_helpers import make_ledger  # Sets up scripts imports.

from pr_lifecycle_signal_accum import SignalsAccum, fold_payload


class SignalAccumTests(unittest.TestCase):
    def test_instances_do_not_share_mutable_signal_or_failure_state(self) -> None:
        first, second = SignalsAccum(), SignalsAccum()
        fold_payload(
            first,
            "demo#1@head",
            {
                "state": "OPEN",
                "mergeable": "CONFLICTING",
                "title": "Bolt",
                "headRefOid": "head",
                "baseRefOid": "base",
                "author": {"login": "bot"},
                "files": [{"path": "src/demo.py"}],
            },
        )
        fold_payload(first, "demo#2@head", {"state": "CLOSED"})
        first.failed.append("demo#3@head")
        first.truncated.append("demo#4@head")
        first.consecutive_failures = 1
        self.assertEqual(second, SignalsAccum())
        self.assertEqual(second.to_signals().closed_keys, None)
        self.assertEqual(second.failed, [])
        self.assertEqual(second.truncated, [])

    def test_empty_path_evidence_is_distinct_from_no_path_evidence(self) -> None:
        acc = SignalsAccum()
        for key, payload in (
            ("empty", {"files": []}),
            ("journal", {"files": [{"path": ".jules/bolt.md"}]}),
            ("missing", {}),
            ("invalid", {"files": None}),
        ):
            fold_payload(acc, key, {"state": "OPEN", **payload})
        signals = acc.to_signals()
        self.assertEqual(signals.unique_paths_by_key, {"empty": [], "journal": []})
        self.assertIsNone(signals.live_mergeable_by_key)
        self.assertIsNone(signals.live_head_sha_by_key)
        self.assertIsNone(signals.author_login_by_key)
        self.assertEqual(acc.truncated, [])

    def test_mixed_payloads_keep_exclusions_and_evidence_on_their_own_keys(
        self,
    ) -> None:
        acc = SignalsAccum()
        payload = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "title": "  Bolt: fix  ",
            "headRefOid": "head",
            "baseRefOid": "base",
            "author": {"login": "bot"},
            "files": [{"path": "src/demo.py"}],
        }
        payloads = make_ledger(
            [
                {**payload, "key": "open"},
                {**payload, "key": "closed", "state": " merged "},
                {**payload, "key": "unknown", "state": "UNKNOWN"},
                {**payload, "key": "truncated", "files": [{"path": "src/demo.py"}, {}]},
            ],
            [],
        )
        original = copy.deepcopy(payloads)
        for item in payloads["items"]:
            fold_payload(acc, item["key"], item)
        signals = acc.to_signals()
        self.assertEqual(signals.closed_keys, frozenset({"closed"}))
        self.assertEqual(
            signals.titles_by_key, {"open": "Bolt: fix", "truncated": "Bolt: fix"}
        )
        self.assertEqual(
            signals.live_mergeable_by_key,
            {"open": "CONFLICTING", "truncated": "CONFLICTING"},
        )
        self.assertEqual(signals.unique_paths_by_key, {"open": ["src/demo.py"]})
        self.assertEqual(acc.truncated, ["truncated"])
        self.assertEqual(payloads, original)

    def test_malformed_file_entry_discards_entire_path_list_only(self) -> None:
        for entry in (None, "src/not-a-dict.py", {}, {"path": None}, {"path": ""}):
            with self.subTest(entry=entry):
                acc = SignalsAccum()
                fold_payload(
                    acc,
                    "key",
                    {
                        "state": "OPEN",
                        "headRefOid": "new-head",
                        "baseRefOid": "new-base",
                        "mergeable": "MERGEABLE",
                        "files": [{"path": "src/valid.py"}, entry],
                    },
                )
                signals = acc.to_signals()
                self.assertIsNone(signals.unique_paths_by_key)
                self.assertEqual(signals.live_head_sha_by_key, {"key": "new-head"})
                self.assertEqual(signals.live_base_sha_by_key, {"key": "new-base"})
                self.assertEqual(signals.live_mergeable_by_key, {"key": "MERGEABLE"})
                self.assertEqual(acc.truncated, ["key"])

    def test_file_cap_counts_journals_before_filtering(self) -> None:
        for count in (99, 100, 101):
            with self.subTest(count=count):
                acc = SignalsAccum()
                fold_payload(
                    acc,
                    "key",
                    {
                        "state": "OPEN",
                        "files": [
                            {"path": f".jules/{index}.md"} for index in range(count - 1)
                        ]
                        + [{"path": "src/only-source.py"}],
                    },
                )
                if count == 99:
                    self.assertEqual(
                        acc.to_signals().unique_paths_by_key,
                        {"key": ["src/only-source.py"]},
                    )
                    self.assertEqual(acc.truncated, [])
                else:
                    self.assertIsNone(acc.to_signals().unique_paths_by_key)
                    self.assertEqual(acc.truncated, ["key"])

    def test_non_string_identity_values_are_not_coerced_into_evidence(self) -> None:
        for raw in (None, False, 17, ["value"], {"value": "value"}):
            with self.subTest(raw=raw):
                acc = SignalsAccum()
                fold_payload(
                    acc,
                    "key",
                    {
                        "state": "OPEN",
                        "title": raw,
                        "headRefOid": raw,
                        "baseRefOid": raw,
                        "author": {"login": raw},
                    },
                )
                signals = acc.to_signals()
                self.assertIsNone(signals.titles_by_key)
                self.assertIsNone(signals.live_head_sha_by_key)
                self.assertIsNone(signals.live_base_sha_by_key)
                self.assertIsNone(signals.author_login_by_key)


if __name__ == "__main__":
    unittest.main()
