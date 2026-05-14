import unittest
from unittest.mock import patch, mock_open
import os
from env_utils import parse_env_line, get_parsed_env_vars, load_gh_token_env

class TestEnvUtils(unittest.TestCase):
    def test_parse_env_line(self):
        env = {}
        parse_env_line("KEY=VAL", env)
        self.assertEqual(env["KEY"], "VAL")

        parse_env_line("  EXPORTED_KEY=VAL  ", env)
        self.assertEqual(env["EXPORTED_KEY"], "VAL")

        parse_env_line("export COMMAND_KEY=VAL", env)
        self.assertEqual(env["COMMAND_KEY"], "VAL")

        parse_env_line("# COMMENT=IGNORE", env)
        self.assertNotIn("COMMENT", env)

        parse_env_line("QUOTED='VALUE'", env)
        self.assertEqual(env["QUOTED"], "VALUE")

        parse_env_line('DOUBLE_QUOTED="VALUE"', env)
        self.assertEqual(env["DOUBLE_QUOTED"], "VALUE")

    @patch("builtins.open", new_callable=mock_open, read_data="FOO=BAR\nBAZ=QUX")
    def test_get_parsed_env_vars(self, mock_file):
        # Clear cache for testing
        get_parsed_env_vars.cache_clear()
        vars = get_parsed_env_vars("fake.env")
        self.assertEqual(vars, {"FOO": "BAR", "BAZ": "QUX"})

    @patch("env_utils.get_parsed_env_vars")
    @patch.dict(os.environ, {"ORIGINAL": "VALUE"}, clear=True)
    def test_load_gh_token_env(self, mock_get_vars):
        mock_get_vars.return_value = {"GH_TOKEN": "secret"}
        env = load_gh_token_env()
        self.assertEqual(env["ORIGINAL"], "VALUE")
        self.assertEqual(env["GH_TOKEN"], "secret")

if __name__ == "__main__":
    unittest.main()
