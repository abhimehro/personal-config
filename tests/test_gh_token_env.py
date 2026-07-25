import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gh_token_env import (
    _read_env_file,
    clear_gh_token_cache,
    load_gh_token_env,
    missing_gh_token_message,
    parse_env_line,
    resolve_gh_token_env_file,
)


def _write_secure_env_file(path: Path, content: str) -> None:
    """Write an env file with owner-only permissions for the parser tests."""
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


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

    def test_parse_env_line_rejects_command_substitution(self):
        env: dict[str, str] = {}
        parse_env_line("GH_TOKEN=$(id)", env)
        self.assertEqual(env, {})

    def test_read_env_file_missing(self):
        self.assertEqual(_read_env_file(Path("/does/not/exist/ever.env")), {})

    def test_read_env_file_rejects_too_permissive(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            _write_secure_env_file(env_file, "GH_TOKEN=secret\n")
            os.chmod(env_file, 0o644)
            with self.assertRaises(PermissionError):
                _read_env_file(env_file)

    def test_read_env_file_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_file = Path(tmp) / "real.env"
            _write_secure_env_file(real_file, "GH_TOKEN=secret\n")
            symlink = Path(tmp) / "GH_TOKEN.env"
            symlink.symlink_to(real_file)
            with self.assertRaises(PermissionError):
                _read_env_file(symlink)

    def test_env_var_takes_precedence_over_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            _write_secure_env_file(env_file, "GH_TOKEN=file_token\n")
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
            _write_secure_env_file(env_file, "export GH_TOKEN=file_token\n")
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                os.environ.pop("GH_TOKEN", None)
                merged = load_gh_token_env()
        self.assertEqual(merged["GH_TOKEN"], "file_token")

    def test_resolve_gh_token_env_file_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "custom.env"
            _write_secure_env_file(env_file, "GH_TOKEN=x\n")
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                self.assertEqual(resolve_gh_token_env_file(), env_file)

    def test_missing_message_mentions_runbook(self):
        with patch("gh_token_env.resolve_gh_token_env_file", return_value=None):
            message = missing_gh_token_message()
        self.assertIn("github-pat-rotation-runbook", message)


if __name__ == "__main__":
    unittest.main()
