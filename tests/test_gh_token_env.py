"""Tests for gh_token_env (ABHI-918 credential hygiene)."""

import os
import tempfile
import unittest
from unittest.mock import patch

from gh_token_env import _get_parsed_env_vars, load_gh_subprocess_env


class TestGhTokenEnv(unittest.TestCase):
    def setUp(self) -> None:
        _get_parsed_env_vars.cache_clear()

    def test_prefers_environment_over_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".env") as handle:
            handle.write("GH_TOKEN='file-token'\n")
            path = handle.name
        self.addCleanup(lambda: os.unlink(path))
        with patch.dict(
            os.environ,
            {"GH_TOKEN": "env-token", "GH_TOKEN_ENV_FILE": path},
            clear=False,
        ):
            env = load_gh_subprocess_env()
        self.assertEqual(env["GH_TOKEN"], "env-token")

    def test_github_token_alias(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "github-actions-token"}, clear=True):
            result = load_gh_subprocess_env()
        self.assertEqual(result["GH_TOKEN"], "github-actions-token")

    def test_no_repo_relative_default_path(self) -> None:
        import gh_token_env as module

        with open(module.__file__, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("email-security-pipeline/GH_TOKEN.env", source)


if __name__ == "__main__":
    unittest.main()
