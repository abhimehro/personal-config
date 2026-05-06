import unittest
import sys
import os

# Ensure the project root is in the path so we can import parse_inventory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parse_inventory import _parse_env_line, parse_inventory_lines

class TestParseInventory(unittest.TestCase):

    def test_parse_env_line_basic(self):
        env = {}
        _parse_env_line("FOO=bar", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_with_export(self):
        env = {}
        _parse_env_line("export FOO=bar", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_with_quotes(self):
        env = {}
        _parse_env_line("export FOO=\"bar\"", env)
        self.assertEqual(env, {"FOO": "bar"})

        env = {}
        _parse_env_line("export FOO='bar'", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_comments_and_empty(self):
        env = {"FOO": "bar"}
        _parse_env_line("# export BAZ=qux", env)
        self.assertEqual(env, {"FOO": "bar"})

        _parse_env_line("   ", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_inventory_lines(self):
        lines = [
            "## repoA\n",
            "| Repo | PR | Author (API) | Branch | Category | CI rollup | Conflicts | Age | Notes |\n",
            "|---|---|---|---|---|---|---|---|---|\n",
            "| repoA | 123 | some_user[bot] | branch | cat | SUCCESS | none | age | |\n",
            "| repoA | 456 | human | branch | cat | FAIL | none | age | has-hints |\n",
            "| repoA | 789 | human | branch | cat | SUCCESS | none | age | |\n",
            "## repoB\n",
            "| | 101 | | | another[bot] | | CLEAN | SUCCESS | |\n"
        ]
        repos = parse_inventory_lines(lines)

        self.assertIn("repoA", repos)
        self.assertIn("repoB", repos)

        # repoA should have 123 (bot) and 456 (hints), but not 789 (human, no hints)
        self.assertEqual(len(repos["repoA"]), 2)
        self.assertEqual(repos["repoA"][0]["pr"], "123")
        self.assertEqual(repos["repoA"][0]["checks"], "SUCCESS")

        self.assertEqual(repos["repoA"][1]["pr"], "456")
        self.assertEqual(repos["repoA"][1]["checks"], "FAIL")

        # repoB should have 101 (bot)
        self.assertEqual(len(repos["repoB"]), 1)
        self.assertEqual(repos["repoB"][0]["pr"], "101")
        self.assertEqual(repos["repoB"][0]["checks"], "SUCCESS")

    def test_parse_inventory_lines_missing_repo(self):
        # Edge case: No current_repo when matching lines
        lines = [
            "| | 123 | | | some_user[bot] | | CLEAN | SUCCESS | |\n",
        ]
        repos = parse_inventory_lines(lines)
        self.assertEqual(repos, {})

    def test_parse_inventory_lines_malformed(self):
        lines = [
            "## repoA\n",
            "| | 123 | | | some_user[bot] | | CLEAN | \n", # Missing columns
        ]
        repos = parse_inventory_lines(lines)
        self.assertEqual(repos["repoA"], [])

if __name__ == '__main__':
    unittest.main()
