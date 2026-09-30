"""Exercise the opt-in submodule policy with disposable, local Git repositories.

Run with: python3 -m unittest tests.test_devin_handoff_submodule
No GitHub access, credentials, or populated devin-handoff checkout is needed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")
SUBMODULE = "devin-handoff"
POLICY = f"submodule.{SUBMODULE}"


@unittest.skipUnless(GIT, "Git is required for submodule integration tests")
class TestDevinHandoffSubmodule(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="submodule policy ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") and key not in {"BASH_ENV", "ENV"}
        }
        config = self.root / "gitconfig"
        config.write_text(
            "[user]\n name = Test User\n email = test@example.invalid\n"
            "[init]\n defaultBranch = main\n"
            "[commit]\n gpgSign = false\n",
            encoding="utf-8",
        )
        self.environment.update(
            GIT_CONFIG_GLOBAL=str(config),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_TERMINAL_PROMPT="0",
            # Only fixture repositories are reachable, including in child Git processes.
            GIT_ALLOW_PROTOCOL="file",
            GIT_TEMPLATE_DIR=str(self.root / "empty-template"),
            LC_ALL="C",
        )
        (self.root / "empty-template").mkdir()
        self.git(
            self.root,
            "config",
            "--file",
            str(config),
            "core.hooksPath",
            str(self.root / "empty-template"),
        )
        self.source = self.root / "handoff source"
        self.upstream = self.root / "superproject"
        self.checkout = self.root / "session checkout"
        self.unavailable = self.root / "missing handoff repository"
        self.git(self.root, "init", str(self.source))
        (self.source / "handoff.txt").write_text("first revision\n", encoding="utf-8")
        self.first = self.commit(self.source)
        (self.source / "handoff.txt").write_text("second revision\n", encoding="utf-8")
        self.second = self.commit(self.source)

        self.git(self.root, "init", str(self.upstream))
        shutil.copyfile(ROOT / ".gitmodules", self.upstream / ".gitmodules")
        self.set_url(self.unavailable)
        self.set_gitlink(self.first)
        self.commit(self.upstream)

    def git(
        self, directory: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [GIT, *arguments],
            cwd=directory,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if check:
            self.assertEqual(
                result.returncode,
                0,
                f"git {arguments!r} in {directory}:\n{result.stdout}\n{result.stderr}",
            )
        return result

    def commit(self, directory: Path) -> str:
        self.git(directory, "add", "--all")
        self.git(directory, "commit", "--quiet", "-m", "Fixture revision")
        return self.git(directory, "rev-parse", "HEAD").stdout.strip()

    def set_url(self, path: Path) -> None:
        self.git(
            self.upstream, "config", "-f", ".gitmodules", f"{POLICY}.url", str(path)
        )

    def set_gitlink(self, revision: str) -> None:
        self.git(
            self.upstream,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{revision},{SUBMODULE}",
        )
        # Preserve the staged gitlink when commit() stages the working tree.
        (self.upstream / SUBMODULE).mkdir(exist_ok=True)

    def clone(self) -> None:
        self.git(self.root, "clone", "--no-local", str(self.upstream), str(self.checkout))

    def opt_in(self) -> None:
        self.git(
            self.checkout,
            "-c",
            f"{POLICY}.update=checkout",
            "submodule",
            "update",
            "--init",
            SUBMODULE,
        )

    def startup_chain(self) -> None:
        self.git(self.checkout, "pull", "--ff-only", "--recurse-submodules")
        self.git(self.checkout, "submodule", "sync", "--recursive")
        self.git(self.checkout, "submodule", "update", "--init", "--recursive")

    def assert_uninitialized(self, revision: str) -> None:
        status = self.git(self.checkout, "submodule", "status", SUBMODULE).stdout
        self.assertEqual(status.strip(), f"-{revision} {SUBMODULE}")
        self.assertFalse((self.checkout / SUBMODULE / ".git").exists())
        self.assertFalse((self.checkout / ".git" / "modules" / SUBMODULE).exists())

    def test_git_parses_both_opt_out_settings(self) -> None:
        for key, flags, expected in (
            ("update", [], "none"),
            ("fetchRecurseSubmodules", ["--bool"], "false"),
        ):
            with self.subTest(key=key):
                result = self.git(
                    self.root,
                    "config",
                    "-f",
                    str(ROOT / ".gitmodules"),
                    *flags,
                    "--get",
                    f"{POLICY}.{key}",
                )
                self.assertEqual(result.stdout.strip(), expected)

    def test_repeated_recursive_update_skips_unavailable_submodule(self) -> None:
        self.clone()
        for _ in range(2):
            self.git(self.checkout, "submodule", "sync", "--recursive")
            self.git(self.checkout, "submodule", "update", "--init", "--recursive")
            self.assert_uninitialized(self.first)
        update = self.git(self.checkout, "config", "--get", f"{POLICY}.update")
        self.assertEqual(update.stdout.strip(), "none")

    def test_startup_chain_fast_forwards_with_unavailable_submodule(self) -> None:
        self.clone()
        self.set_gitlink(self.second)
        target = self.commit(self.upstream)

        self.startup_chain()

        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD").stdout.strip(), target)
        self.assert_uninitialized(self.second)

    def test_startup_chain_can_pull_the_opt_out_policy_itself(self) -> None:
        policy = (self.upstream / ".gitmodules").read_bytes()
        for key in ("update", "fetchRecurseSubmodules"):
            self.git(
                self.upstream,
                "config",
                "-f",
                ".gitmodules",
                "--unset",
                f"{POLICY}.{key}",
            )
        self.commit(self.upstream)
        self.clone()
        (self.upstream / ".gitmodules").write_bytes(policy)
        self.set_gitlink(self.second)
        target = self.commit(self.upstream)

        self.startup_chain()

        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD").stdout.strip(), target)
        self.assertEqual((self.checkout / ".gitmodules").read_bytes(), policy)
        self.assert_uninitialized(self.second)

    def test_explicit_opt_in_checks_out_pinned_revision_without_changing_default(
        self,
    ) -> None:
        self.set_url(self.source)
        self.commit(self.upstream)
        self.clone()
        self.git(self.checkout, "submodule", "update", "--init", "--recursive")
        policy = (self.checkout / ".gitmodules").read_bytes()

        self.opt_in()

        handoff = self.checkout / SUBMODULE
        self.assertEqual(self.git(handoff, "rev-parse", "HEAD").stdout.strip(), self.first)
        self.assertEqual((handoff / "handoff.txt").read_text(), "first revision\n")
        self.assertEqual((self.checkout / ".gitmodules").read_bytes(), policy)
        self.assertEqual(
            self.git(self.checkout, "config", "--get", f"{POLICY}.update").stdout.strip(),
            "none",
        )

        self.set_gitlink(self.second)
        self.commit(self.upstream)
        self.git(self.checkout, "fetch", "origin")
        self.git(self.checkout, "merge", "--ff-only", "origin/main")
        self.git(self.checkout, "submodule", "update", "--init", "--recursive")
        self.assertEqual(self.git(handoff, "rev-parse", "HEAD").stdout.strip(), self.first)
        self.opt_in()
        self.assertEqual(self.git(handoff, "rev-parse", "HEAD").stdout.strip(), self.second)
        self.assertEqual((handoff / "handoff.txt").read_text(), "second revision\n")

    def test_explicit_opt_in_reports_unavailable_repository(self) -> None:
        self.clone()
        result = self.git(
            self.checkout,
            "-c",
            f"{POLICY}.update=checkout",
            "submodule",
            "update",
            "--init",
            SUBMODULE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.unavailable), result.stderr)
        self.assertFalse((self.checkout / SUBMODULE / ".git").exists())

    def prepare_populated_checkout_with_unavailable_remote(self) -> str:
        self.set_url(self.source)
        self.commit(self.upstream)
        self.clone()
        self.opt_in()
        # The new gitlink must be absent locally to trigger on-demand fetching
        # if fetchRecurseSubmodules=false is removed from the policy.
        (self.source / "handoff.txt").write_text("third revision\n", encoding="utf-8")
        missing_revision = self.commit(self.source)
        self.source.rename(self.root / "offline handoff source")
        self.set_gitlink(missing_revision)
        return self.commit(self.upstream)

    def test_default_fetch_skips_unavailable_submodule_with_missing_commit(self) -> None:
        target = self.prepare_populated_checkout_with_unavailable_remote()

        self.git(self.checkout, "fetch", "origin")

        self.assertEqual(
            self.git(self.checkout, "rev-parse", "origin/main").stdout.strip(), target
        )
        # Negative control: enabling recursion for this submodule must fail.
        result = self.git(
            self.checkout,
            "-c",
            f"{POLICY}.fetchRecurseSubmodules=true",
            "fetch",
            "origin",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.source), result.stderr)

    def test_explicit_recursive_pull_overrides_opt_out_for_populated_submodule(
        self,
    ) -> None:
        # Boundary: --recurse-submodules forces a fetch even with the policy.
        # An unavailable populated submodule still breaks session startup.
        self.prepare_populated_checkout_with_unavailable_remote()
        previous = self.git(self.checkout, "rev-parse", "HEAD").stdout

        result = self.git(
            self.checkout, "pull", "--ff-only", "--recurse-submodules", check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.source), result.stderr)
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD").stdout, previous)


if __name__ == "__main__":
    unittest.main()
