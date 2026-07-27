import os
import stat
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

    def test_load_rejects_group_or_world_writable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            env_file.write_text("GH_TOKEN=file_token\n", encoding="utf-8")
            env_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                with self.assertRaises(PermissionError):
                    load_gh_token_env()

    def test_load_rejects_file_not_owned_by_current_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            _write_secure_env_file(env_file, "GH_TOKEN=file_token\n")
            with patch("gh_token_env.os.getuid", return_value=os.getuid() + 1):
                with patch.dict(
                    os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
                ):
                    with self.assertRaises(PermissionError):
                        load_gh_token_env()

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

    def test_explicit_env_file_missing_does_not_fall_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.env"
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(missing)}, clear=True
            ):
                with self.assertRaises(FileNotFoundError):
                    resolve_gh_token_env_file()

    def test_missing_message_mentions_runbook(self):
        with patch("gh_token_env.resolve_gh_token_env_file", return_value=None):
            message = missing_gh_token_message()
        self.assertIn("github-pat-rotation-runbook", message)

    def test_load_from_file_only_injects_gh_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            _write_secure_env_file(
                env_file, "GH_TOKEN=file_token\nOTHER_VAR=do_not_inject\n"
            )
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                os.environ.pop("GH_TOKEN", None)
                merged = load_gh_token_env()
        self.assertEqual(merged["GH_TOKEN"], "file_token")
        self.assertNotIn("OTHER_VAR", merged)

    def test_load_gh_token_env_does_not_mutate_global_environ(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "GH_TOKEN.env"
            _write_secure_env_file(env_file, "GH_TOKEN=file_token\n")
            with patch.dict(
                os.environ, {"GH_TOKEN_ENV_FILE": str(env_file)}, clear=True
            ):
                original = os.environ.copy()
                load_gh_token_env()
                self.assertEqual(os.environ, original)

    def test_legacy_path_is_script_relative(self):
        import gh_token_env as gte

        legacy = gte._LEGACY_RELATIVE_ENV
        self.assertTrue(legacy.is_absolute())
        # The legacy file is a sibling of the repo containing gh_token_env.py.
        self.assertIn("email-security-pipeline", str(legacy))

    def test_resolve_gh_token_env_file_finds_legacy_from_different_cwd(self):
        import gh_token_env as gte

        with tempfile.TemporaryDirectory() as tmp:
            legacy_dir = Path(tmp) / "email-security-pipeline"
            legacy_dir.mkdir()
            legacy_file = legacy_dir / "GH_TOKEN.env"
            _write_secure_env_file(legacy_file, "GH_TOKEN=legacy_token\n")

            # Simulate the repo being a sibling of the legacy dir.
            fake_repo = Path(tmp) / "personal-config"
            fake_repo.mkdir()
            with patch.object(gte, "_LEGACY_RELATIVE_ENV", legacy_file):
                with patch("os.getcwd", return_value=str(tmp)):
                    found = resolve_gh_token_env_file()
            self.assertEqual(found, legacy_file)

    def test_cache_reset_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.env"
            _write_secure_env_file(first, "GH_TOKEN=first\n")
            second = Path(tmp) / "second.env"
            _write_secure_env_file(second, "GH_TOKEN=second\n")

            with patch.dict(os.environ, {"GH_TOKEN_ENV_FILE": str(first)}, clear=True):
                os.environ.pop("GH_TOKEN", None)
                self.assertEqual(load_gh_token_env()["GH_TOKEN"], "first")

            clear_gh_token_cache()
            with patch.dict(os.environ, {"GH_TOKEN_ENV_FILE": str(second)}, clear=True):
                os.environ.pop("GH_TOKEN", None)
                self.assertEqual(load_gh_token_env()["GH_TOKEN"], "second")


if __name__ == "__main__":
    unittest.main()
