"""Tests for the Python setup commands in the Devin blueprint."""

import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
BLUEPRINT = REPO / ".devin" / "blueprint.yaml"


class TestDevinBlueprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = list(yaml.safe_load_all(BLUEPRINT.read_text()))

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home folder"
        self.home.mkdir()
        self.envrc = self.root / "session envrc"
        self.envrc.write_text("# existing session settings\n")
        self.prefix = self.root / "brew prefix"
        self.mock_bin = self.root / "mock-bin"
        self.mock_bin.mkdir()
        self.python_calls = self.root / "python-calls"
        self.brew_calls = self.root / "brew-calls"
        self.pip_calls = self.root / "pip-calls"
        self.git_calls = self.root / "git-calls"
        self._executable(
            self.mock_bin / "git",
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$GIT_CALLS"\n',
        )
        self.fake_python = self.root / "fake-python3.12"
        self._executable(
            self.fake_python,
            '#!/bin/sh\nprintf "%s|%s|%s\\n" "$1" "$2" "$3" >> "$PYTHON_CALLS"\n',
        )
        self._executable(
            self.mock_bin / "brew",
            """#!/bin/sh
printf '%s\\n' "$*" >> "$BREW_CALLS"
case "$1" in
  --prefix) printf '%s\\n' "$BREW_PREFIX" ;;
  install)
    [ "${BREW_INSTALL_FAIL:-0}" = 0 ] || exit 1
    mkdir -p "$BREW_PREFIX/bin"
    cp "$FAKE_PYTHON" "$BREW_PREFIX/bin/python3.12" ;;
  *) exit 2 ;;
esac
""",
        )
        self.environment = {
            **os.environ,
            "HOME": str(self.home),
            "ENVRC": str(self.envrc),
            "PATH": f"{self.mock_bin}:{os.environ['PATH']}",
            "BREW_PREFIX": str(self.prefix),
            "FAKE_PYTHON": str(self.fake_python),
            "PYTHON_CALLS": str(self.python_calls),
            "BREW_CALLS": str(self.brew_calls),
            "PIP_CALLS": str(self.pip_calls),
            "GIT_CALLS": str(self.git_calls),
        }
        self.environment.pop("BASH_ENV", None)
        self.environment.pop("ENV", None)

    @staticmethod
    def _executable(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(0o755)

    def _tokens(self, line: str, needle: str, document: int) -> list:
        try:
            return shlex.split(line)
        except ValueError:
            if needle in line:
                self.fail(
                    f"unparseable maintenance line in document " f"{document}: {line!r}"
                )
            return []

    def _run(self, command, **env):
        return subprocess.run(
            ["bash", "-c", command],
            cwd=REPO,
            env={**self.environment, **env},
            capture_output=True,
            text=True,
            check=False,
        )

    def _install_python(self):
        self._executable(
            self.prefix / "bin" / "python3.12", self.fake_python.read_text()
        )

    def test_platform_documents_keep_linux_default_and_macos_override(self):
        self.assertEqual(len(self.documents), 2)
        self.assertNotIn("runs-on", self.documents[0])
        self.assertEqual(self.documents[1]["runs-on"], "macos")

    def test_both_platforms_deinit_devin_handoff(self):
        expected = ["git", "submodule", "deinit", "-f", "devin-handoff"]
        for index, document in enumerate(self.documents):
            with self.subTest(document=index):
                lines = [
                    line
                    for line in document["maintenance"].splitlines()
                    if not line.lstrip().startswith("#")
                ]
                self.assertTrue(
                    any(
                        self._tokens(line, "submodule", index)[:5] == expected
                        for line in lines
                    ),
                    "maintenance must unregister devin-handoff so later "
                    "in-session pulls cannot fetch it",
                )

    def test_both_platforms_install_the_same_pinned_dependencies(self):
        def pip_line(text: str, document: int) -> list[str]:
            for line in text.splitlines():
                if line.lstrip().startswith("#"):
                    continue
                tokens = self._tokens(line, "pip", document)
                if "install" not in tokens:
                    continue
                if any(t == "pip" or t.endswith("/pip") for t in tokens):
                    return tokens
            self.fail("no pip install line in maintenance block")

        linux = pip_line(self.documents[0]["maintenance"], 0)
        macos = pip_line(self.documents[1]["maintenance"], 1)
        self.assertEqual(linux[:4], ["python3.12", "-m", "pip", "install"])
        self.assertEqual(macos[:2], ["$HOME/.venv-pc/bin/pip", "install"])
        self.assertEqual(linux[4:], macos[2:])
        self.assertEqual(
            macos[2:],
            ["-r", "requirements.txt", "ruff==0.16.8", "bandit", "black", "radon"],
        )

    def test_existing_brew_python_creates_venv_and_preserves_envrc(self):
        self._install_python()
        result = self._run(self.documents[1]["initialize"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.brew_calls.read_text().splitlines(), ["--prefix"])
        self.assertEqual(
            self.python_calls.read_text().splitlines(),
            [f"-m|venv|{self.home / '.venv-pc'}"],
        )
        self.assertEqual(
            self.envrc.read_text(),
            f"# existing session settings\nPATH={self.home}/.venv-pc/bin:{self.environment['PATH']}\n",
        )

    def test_missing_brew_python_is_installed_and_repeated_setup_does_not_duplicate_path(
        self,
    ):
        for _ in range(2):
            result = self._run(self.documents[1]["initialize"])
            self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(
            self.brew_calls.read_text().splitlines(),
            ["--prefix", "install python@3.12", "--prefix"],
        )
        self.assertEqual(len(self.python_calls.read_text().splitlines()), 2)
        self.assertEqual(self.envrc.read_text().count(".venv-pc/bin"), 1)

    def test_initialize_creates_missing_envrc(self):
        self._install_python()
        self.envrc.unlink()

        result = self._run(self.documents[1]["initialize"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.envrc.read_text(),
            f"PATH={self.home}/.venv-pc/bin:{self.environment['PATH']}\n",
        )

    def test_brew_install_failure_stops_before_venv_or_envrc_changes(self):
        result = self._run(self.documents[1]["initialize"], BREW_INSTALL_FAIL="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed to install Python 3.12", result.stdout)
        self.assertFalse(self.python_calls.exists())
        self.assertEqual(self.envrc.read_text(), "# existing session settings\n")

    def test_macos_maintenance_uses_venv_pip_and_propagates_failure(self):
        self._executable(
            self.home / ".venv-pc" / "bin" / "pip",
            '#!/bin/sh\nprintf "%s\\n" "$@" > "$PIP_CALLS"\nexit "${PIP_EXIT_CODE:-0}"\n',
        )
        for index, exit_code in enumerate((0, 7)):
            with self.subTest(exit_code=exit_code):
                result = self._run(
                    self.documents[1]["maintenance"], PIP_EXIT_CODE=str(exit_code)
                )
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(
                    self.pip_calls.read_text().splitlines(),
                    [
                        "install",
                        "-r",
                        "requirements.txt",
                        "ruff==0.16.8",
                        "bandit",
                        "black",
                        "radon",
                    ],
                )
                self.assertEqual(
                    self.git_calls.read_text().splitlines(),
                    ["submodule deinit -f devin-handoff"] * (index + 1),
                    "maintenance should unregister devin-handoff once per run",
                )
