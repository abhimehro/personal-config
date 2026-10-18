"""Tests for terminal outcome logic."""

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


class TerminalOutcomeTests(unittest.TestCase):
    """Tests for terminal outcome logic."""

    def test_terminal_and_manual_outcomes_untouched(self) -> None:
        for outcome in (
            "PASS_ROUTINE",
            "HOLD_CONTRACT",
            "HOLD_EVIDENCE",
            "HOLD_PLATFORM",
            "HOLD_CANONICAL",
            "CLOSE_NONSECURITY_NOOP",
            "ANALYSIS_ERROR",
        ):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        guardrail_outcome=outcome,
                        changed_paths=["scripts/x.sh"],
                    )
                ),
                outcome,
            )
        self.assertIsNone(
            guardrails.evaluate_item(
                _item(lifecycle_state="TERMINAL", changed_paths=["x.sh"])
            )
        )


if __name__ == "__main__":
    unittest.main()