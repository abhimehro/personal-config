"""Guard Trunk pinact at 4.1.1 until plugins pass --format (v5)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUNK_YAML = ROOT / ".trunk/trunk.yaml"


class TestTrunkPinactPin(unittest.TestCase):
    def test_pinact_stays_on_4_1_1_until_plugins_emit_double_dash_format(self) -> None:
        """
        pinact v5 rejects -format from trunk plugins v1.11.0 pinact_run.py.

        a19a9d93 bumped the pin to 5.0.0 and broke Workflow Integrity on every
        PR. Keep 4.1.1 until plugins emit --format.
        """
        text = TRUNK_YAML.read_text(encoding="utf-8")
        pins = [
            line.strip()
            for line in text.splitlines()
            if line.strip().startswith("- pinact@")
        ]
        self.assertEqual(pins, ["- pinact@4.1.1"], pins)


if __name__ == "__main__":
    unittest.main()
