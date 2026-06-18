import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gh_token_env import (
    clear_gh_token_cache,
    gh_token_configured,
    load_gh_token_env,
    missing_gh_token_message,
    parse_env_line,
    resolve_gh_token_env_file,
)


class TestGhTokenEnv(unittest.TestCase):
    def setUp(self):
        clear_gh_token_cache()

    def test_parse_env_line_basic(self):
        env: dict[str, str] = {}
        parse_env_line("FOO=bar", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_with_export_and_quotes(self):
        env: dict[str, str] = {}
        parse_env_line('export FOO="bar"', env)
        self.assertEqual(env, {"FOO": "bar"})
        parse_env_line("export BAZ='qux'", env)
        self.assertEqual(env["BAZ"], "qux")

    def test_env_var_takes_precedence_over_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            env_file.write_text("GH_TOKEN=file_token\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"GH_TOKEN": "env_token", "GH_TOKEN_ENV_FILE": str(env_file)},
                clear=False,
            ):
                merged = load_gh_token_env()
        self.assertEqual(merged["GH_TOKEN"], "env_token")

    def test_load_from_file_when_env_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            env_file.write_text("export GH_TOKEN=file_token\n", encoding="utf-8")
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                os.environ.pop("GH_TOKEN", None)
                merged = load_gh_token_env()
        self.assertEqual(merged["GH_TOKEN"], "file_token")

    def test_resolve_gh_token_env_file_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "custom.env"
            env_file.write_text("GH_TOKEN=x\n", encoding="utf-8")
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                self.assertEqual(resolve_gh_token_env_file(), env_file)

    def test_missing_message_mentions_runbook(self):
        with patch("gh_token_env.resolve_gh_token_env_file", return_value=None):
            message = missing_gh_token_message()
        self.assertIn("github-pat-rotation-runbook", message)

    def test_gh_token_configured_from_env(self):
        with patch.dict(os.environ, {"GH_TOKEN": "present"}, clear=False):
            self.assertTrue(gh_token_configured())


if __name__ == "__main__":
    unittest.main()
