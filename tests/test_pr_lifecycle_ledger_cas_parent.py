"""Integration tests: preflight parent must match live ref tip at commit."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS_LIB = ROOT / "tests" / "lib"
for path in (SCRIPTS, TESTS_LIB):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pr_lifecycle_ledger_cas as cas  # noqa: E402
from git_cas_local_backend import LocalGitCasBackend  # noqa: E402
from pr_lifecycle_github_http import OPERATOR_CONFLICT  # noqa: E402


class LedgerCasParentCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = LocalGitCasBackend()
        self.addCleanup(self.backend.cleanup)
        example = (ROOT / "tasks/pr-lifecycle-ledger.example.yaml").read_text(
            encoding="utf-8"
        )
        self.parent_a = self.backend.seed_ledger(example)
        self.runtime = {
            "data_branch": self.backend.branch,
            "data_path": self.backend.data_path,
            "last_known_data_commit": self.parent_a,
        }
        self.ledger_v1 = example
        self.ledger_v2 = example.replace("ledger_revision: 42", "ledger_revision: 43", 1)

    def test_commit_succeeds_when_parent_matches_preflight(self) -> None:
        with (
            mock.patch.object(cas, "github_request", self.backend.request),
            mock.patch.object(cas, "pointer_runtime", return_value=self.runtime),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.yaml"
                path.write_text(self.ledger_v2, encoding="utf-8")
                result = cas.run_commit(
                    path,
                    "stage test commit",
                    bump_revision=False,
                    expected_parent_sha=self.parent_a,
                )
        self.assertNotEqual(result["commit_sha"], self.parent_a)
        self.assertEqual(result["parent_sha"], self.parent_a)
        self.assertIn("ledger_revision: 43", self.backend.ledger_bytes_at_tip())

    def test_commit_aborts_stale_preflight_parent_and_preserves_concurrent_tip(
        self,
    ) -> None:
        with (
            mock.patch.object(cas, "github_request", self.backend.request),
            mock.patch.object(cas, "pointer_runtime", return_value=self.runtime),
        ):
            concurrent = cas.cas_commit(
                self.runtime,
                self.ledger_v2,
                "writer two",
                expected_parent_sha=self.parent_a,
            )
            tip_b = concurrent["commit_sha"]
            self.assertEqual(self.backend.tip(), tip_b)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "stale.yaml"
                path.write_text(self.ledger_v1, encoding="utf-8")
                with self.assertRaises(cas.CasError) as raised:
                    cas.run_commit(
                        path,
                        "stale writer",
                        bump_revision=False,
                        expected_parent_sha=self.parent_a,
                    )
        self.assertEqual(raised.exception.code, OPERATOR_CONFLICT)
        self.assertEqual(self.backend.tip(), tip_b)
        self.assertIn("ledger_revision: 43", self.backend.ledger_bytes_at_tip())

    def test_cli_commit_requires_expected_parent(self) -> None:
        with self.assertRaises(SystemExit):
            cas.build_parser().parse_args(["commit", "--file", "ledger.yaml"])


if __name__ == "__main__":
  unittest.main()
