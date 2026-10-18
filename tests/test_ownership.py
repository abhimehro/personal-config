"""Tests for ownership logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails  # noqa: E402
from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


class OwnershipTests(unittest.TestCase):
    """Tests for ownership logic."""

    def test_owned_items_never_evaluated(self) -> None:
        for owner in ("human", "stage2", "stage3"):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(current_owner=owner, changed_paths=["scripts/x.sh"]),
                    clear_standin=True,
                ),
                owner,
            )
        self.assertIsNotNone(
            guardrails.evaluate_item(
                _item(current_owner="stage1", changed_paths=["scripts/x.sh"])
            )
        )

    def test_human_review_items_never_evaluated(self) -> None:
        """risk_class=HUMAN_REVIEW is the ledger's human-hold marker."""
        for clear in (False, True):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        risk_class="HUMAN_REVIEW",
                        changed_paths=["docs/readme.md"],
                    ),
                    clear_standin=clear,
                ),
                f"NOT_RUN item, clear_standin={clear}",
            )
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        guardrail_outcome="REVIEW_SECURITY",
                        risk_class="HUMAN_REVIEW",
                        changed_paths=["docs/readme.md"],
                    ),
                    clear_standin=clear,
                ),
                f"REVIEW_SECURITY item, clear_standin={clear}",
            )


if __name__ == "__main__":
    unittest.main()