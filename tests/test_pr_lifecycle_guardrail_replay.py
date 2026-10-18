"""Replay counts for the guardrail classifier. No network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrail_replay as replay  # noqa: E402
import pr_lifecycle_guardrails as guardrails  # noqa: E402

from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


def _evidence(
    title: str, head_ref: str, diff_text: str = ""
) -> guardrails.GuardrailEvidence:
    return guardrails.GuardrailEvidence(
        diff_text=diff_text,
        title=title,
        head_ref=head_ref,
        required_checks_green=True,
        mergeable=True,
    )


class ReplayItemsTests(unittest.TestCase):
    def test_rules_and_sentinel_table_use_paths_and_diff_not_the_title(self) -> None:
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
                    "diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n"
                    "+++ b/.github/workflows/ci.yml\n"
                    "@@\n"
                    f"+        uses: actions/checkout@{sha}\n"
                ),
            ),
        }
        report = replay.replay_items([journal, labeled, shell, dependabot], evidence)
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


if __name__ == "__main__":
    unittest.main()
