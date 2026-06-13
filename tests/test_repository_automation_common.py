import os
import sys
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
        expected = "a" * 34 + "\n... [truncated]"
        result = rac.truncate(text, limit=50)
        self.assertEqual(result, expected)
        # Truncated output must never exceed the requested limit.
        self.assertLessEqual(len(result), 50)

    def test_truncate_empty_text(self):
        self.assertEqual(rac.truncate("", limit=50), "")

    def test_truncate_small_limit(self):
        # When limit is smaller than the suffix, the function must still
        # respect the limit rather than growing the output via negative slicing.
        text = "abcdefghijklmnop"
        result = rac.truncate(text, limit=10)
        self.assertEqual(result, "abcdefghij")
        self.assertLessEqual(len(result), 10)

    def test_truncate_default_limit(self):
        text = "a" * 4001
        expected = "a" * 3984 + "\n... [truncated]"
        result = rac.truncate(text)
        self.assertEqual(result, expected)
        self.assertLessEqual(len(result), 4000)


class TestRepositoryAutomationHelpers(unittest.TestCase):
    def test_stable_tags_from_json(self):
        tags = [
            {"name": "v1.2.3"},
            {"name": "v2.0"},
            {"name": "v3.0.0-beta1"},  # Not a fullmatch stable pattern
            {"name": "1.0.0"},
            {"name": "latest"},
        ]
        res = rac._stable_tags_from_json(tags)
        expected = [
            ((1, 2, 3), "v1.2.3"),
            ((2, 0, 0), "v2.0"),
            ((1, 0, 0), "1.0.0"),
        ]
        self.assertEqual(res, expected)

    def test_latest_tag_via_mcp_disabled(self):
        # By default USE_MCP_GITHUB is false, so it should return empty string.
        rac.USE_MCP_GITHUB = False
        self.assertEqual(rac._latest_tag_via_mcp("owner/repo"), "")

    def test_write_result_unpacks_tuple(self):
        from unittest.mock import patch
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            with patch.object(rac, "task_dir", return_value=temp_path), \
                 patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}):
                res = rac.write_result(
                    "test-task",
                    ("success", "Task completed"),
                    "Report body",
                    {"some_extra": 42}
                )
                self.assertEqual(res["task"], "test-task")
                self.assertEqual(res["status"], "success")
                self.assertEqual(res["summary"], "Task completed")
                self.assertEqual(res["some_extra"], 42)
                
                # Check written files
                self.assertTrue((temp_path / "report.md").exists())
                self.assertEqual((temp_path / "report.md").read_text(), "Report body\n")
                self.assertTrue((temp_path / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
