import sys
import os
import types
import unittest

# Ensure the scripts directory is in the path
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".github",
        "scripts",
    ),
)

# Stub yaml since we don't need it for truncate and it might not be installed
if "yaml" not in sys.modules:
    _yaml = types.ModuleType("yaml")
    sys.modules["yaml"] = _yaml

import repository_automation_common as rac


class TestTruncate(unittest.TestCase):
    def test_truncate_under_limit(self):
        self.assertEqual(rac.truncate("hello", limit=50), "hello")

    def test_truncate_exact_limit(self):
        text = "a" * 50
        self.assertEqual(rac.truncate(text, limit=50), text)

    def test_truncate_over_limit(self):
        text = "a" * 51
        expected = "a" * 35 + "\n... [truncated]"
        self.assertEqual(rac.truncate(text, limit=50), expected)

    def test_truncate_empty_text(self):
        self.assertEqual(rac.truncate("", limit=50), "")

    def test_truncate_small_limit_negative_slice(self):
        text = "abcdefghijklmnop"
        expected = "abcdefghijk\n... [truncated]"
        self.assertEqual(rac.truncate(text, limit=10), expected)

    def test_truncate_default_limit(self):
        text = "a" * 4001
        expected = "a" * 3985 + "\n... [truncated]"
        self.assertEqual(rac.truncate(text), expected)


if __name__ == "__main__":
    unittest.main()
