"""Focused regression tests for the Antigravity proactive migration."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "configs/antigravity/hooks/proactive-guard.py"
WORKTREE = ROOT / "scripts/proactive-worktree.sh"
CTL = ROOT / "scripts/antigravity-proactive-ctl.sh"
SYNC = ROOT / "scripts/sync_all_configs.sh"
spec = importlib.util.spec_from_file_location("proactive_guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GuardBoundaries(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"HOME": str(self.home)}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.clock = patch.object(guard.time, "time", return_value=100_000)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_conversation_registry_expires_after_one_day(self) -> None:
        registry = guard._reports_dir() / ".sweep-conversations.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({"fresh": 13_601, "expired": 13_600}))
        self.assertTrue(guard._is_proactive_session({"conversationId": "fresh"}))
        self.assertFalse(guard._is_proactive_session({"conversationId": "expired"}))
        self.assertFalse(guard._is_proactive_session({"conversationId": "unknown"}))

    def test_workspace_must_be_inside_worktree_root(self) -> None:
        root = guard._worktrees_dir()
        for workspace, expected in [
            (root / "child", True),
            (Path(str(root) + "-other"), False),
        ]:
            with self.subTest(workspace=workspace):
                self.assertEqual(
                    guard._is_proactive_session(
                        {"workspacePaths": [None, f"file://{workspace}"]}
                    ),
                    expected,
                )

    def test_lease_expiry_and_repository_boundary(self) -> None:
        lease = guard._reports_dir() / ".sentinel-post-merge-lease.json"
        lease.parent.mkdir(parents=True)
        target = self.home / "dev/example/.jules/sentinel.md"
        for expires, repo, expected in [
            (100_001, "example", True),
            (100_000, "example", False),
            (100_001, "example-other", False),
        ]:
            with self.subTest(expires=expires, repo=repo):
                lease.write_text(json.dumps({"repo_name": repo, "expires_at": expires}))
                self.assertEqual(
                    guard._has_valid_sentinel_lease(str(target), target), expected
                )
        lease.write_text("not json")
        self.assertFalse(guard._has_valid_sentinel_lease(str(target), target))

    def test_command_classification(self) -> None:
        for command, push, force in [
            ("git status && git -C /repo push origin feature", True, False),
            ("bash -ec 'git push origin HEAD:refs/heads/trunk --force'", True, True),
            ("git push origin feature --force", True, False),
            ("git push origin +HEAD:feature", True, True),
            ("git log --oneline", False, False),
        ]:
            with self.subTest(command=command):
                self.assertEqual(guard._is_any_git_push(command), push)
                self.assertEqual(guard._is_force_push_to_protected(command), force)

    def test_sentinel_read_is_allowed_but_mutations_require_lease(self) -> None:
        self.assertFalse(guard._mutates_sentinel_in_shell("cat .jules/sentinel.md"))
        for command in (
            "echo x >> .jules/sentinel.md",
            "git add .jules/sentinel.md",
            "cp x .jules/sentinel.md",
        ):
            with self.subTest(command=command):
                self.assertTrue(guard._mutates_sentinel_in_shell(command))
                self.assertFalse(guard._has_valid_sentinel_lease(command))

    def test_gh_api_mutations_blocked_while_get_allowed(self) -> None:
        for cmd, expected in [
            (
                "gh api repos/o/r/issues -f title=x",
                (
                    "deny",
                    "Blocked remote push/PR mutation during local-only (2B) proactive pilot.",
                ),
            ),
            (
                "gh api repos/o/r/issues --field title=x",
                (
                    "deny",
                    "Blocked remote push/PR mutation during local-only (2B) proactive pilot.",
                ),
            ),
            ("gh api repos/o/r", None),
        ]:
            with self.subTest(cmd=cmd):
                self.assertEqual(
                    guard._evaluate_run_command(cmd, True, False),
                    expected,
                )


class ProactiveCliRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = os.environ.copy()
        self.env.update(
            HOME=str(self.home), PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}"
        )
        self.env.pop("BASH_ENV", None)

    def run_script(
        self, script: Path, *args: str | Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(script), *map(str, args)],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=20,
        )

    def test_collision_gate_fails_closed_at_list_limit(self) -> None:
        gh = self.bin / "gh"
        for count, expected in [(99, 0), (100, 5)]:
            with self.subTest(count=count):
                gh.write_text(
                    "#!/bin/sh\nprintf '%s\\n' '"
                    + json.dumps([{"files": [], "changedFiles": 0}] * count)
                    + "'\n"
                )
                gh.chmod(0o755)
                result = self.run_script(
                    WORKTREE,
                    "check-collisions",
                    "--repo",
                    "owner/repo",
                    "--file",
                    "src/x.py",
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected:
                    self.assertIn("100 PR limit", result.stderr)

    def test_collision_gate_requires_complete_files_even_when_other_pr_collides(
        self,
    ) -> None:
        gh = self.bin / "gh"
        data = [
            {"number": 1, "files": [{"path": "src/x.py"}], "changedFiles": 1},
            {"number": 2, "files": [], "changedFiles": 1},
        ]
        gh.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps(data) + "'\n")
        gh.chmod(0o755)
        result = self.run_script(
            WORKTREE, "check-collisions", "--repo", "owner/repo", "--file", "src/x.py"
        )
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertIn("lists 0 of 1", result.stderr)

    def test_missed_audit_preserves_existing_digest(self) -> None:
        reports = self.home / ".gemini/antigravity/proactive-reports"
        reports.mkdir(parents=True)
        digest = reports / "2026-06-01-example.md"
        digest.write_text("existing successful digest\n")
        result = self.run_script(
            CTL, "audit-missed", "--date", "2026-06-01", "--repo", "owner/example"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PRESENT:", result.stdout)
        self.assertEqual(digest.read_text(), "existing successful digest\n")

    def test_sync_links_skills_and_hook_preserves_backups_and_is_idempotent(
        self,
    ) -> None:
        repo = self.root / "repo"
        skills = repo / "configs/antigravity/skills"
        (skills / "proactive-bolt").mkdir(parents=True)
        (skills / "not-a-directory").write_text("ignore")
        hooks = repo / "configs/antigravity/hooks.json"
        hooks.write_text("{}\n")
        config = self.home / ".gemini/config"
        (config / "skills/proactive-bolt").mkdir(parents=True)
        (config / "skills/proactive-bolt/old.txt").write_text("old skill")
        (config / "hooks.json").write_text("old hooks")
        self.env["REPO_ROOT"] = str(repo)
        for _ in range(2):
            result = self.run_script(SYNC)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (config / "skills/proactive-bolt").resolve(),
            (skills / "proactive-bolt").resolve(),
        )
        self.assertEqual((config / "hooks.json").resolve(), hooks.resolve())
        self.assertEqual(
            len(list((config / "skills").glob("proactive-bolt.backup.*"))), 1
        )
        self.assertEqual(
            next((config / "skills").glob("proactive-bolt.backup.*"))
            .joinpath("old.txt")
            .read_text(),
            "old skill",
        )
        self.assertEqual(
            next(config.glob("hooks.json.backup.*")).read_text(), "old hooks"
        )
        self.assertFalse((config / "skills/not-a-directory").exists())
        for name in ("proactive-reports", "worktrees"):
            self.assertEqual(
                (self.home / ".gemini/antigravity" / name).stat().st_mode & 0o777, 0o700
            )

    def test_sync_without_skills_does_not_install_hook(self) -> None:
        repo = self.root / "repo"
        (repo / "configs/antigravity").mkdir(parents=True)
        (repo / "configs/antigravity/hooks.json").write_text("{}")
        self.env["REPO_ROOT"] = str(repo)
        result = self.run_script(SYNC)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / ".gemini/config/hooks.json").exists())

    def test_sync_uses_copy_on_deploy_when_ctl_is_present(self) -> None:
        for script_mode in (0o755, 0o644):
            with self.subTest(script_mode=oct(script_mode)):
                case_root = self.root / f"ctl_{script_mode:o}"
                repo = case_root / "repo"
                home = case_root / "home"
                home.mkdir(parents=True)
                skills = repo / "configs/antigravity/skills"
                for name in (
                    "proactive-sentinel",
                    "proactive-bolt",
                    "proactive-palette",
                    "proactive-code-health",
                    "proactive-repo-sweep",
                ):
                    (skills / name).mkdir(parents=True)
                    (skills / name / "SKILL.md").write_text(f"# {name}\n")
                (repo / "configs/antigravity/hooks").mkdir(parents=True)
                (repo / "configs/antigravity/hooks/proactive-guard.py").write_text(
                    "print('{}')\n"
                )
                (repo / "configs/antigravity/hooks.json").write_text("{}\n")
                scripts_dir = repo / "scripts"
                scripts_dir.mkdir(parents=True)
                for src in (CTL, WORKTREE):
                    dst = scripts_dir / src.name
                    dst.write_text(src.read_text())
                    dst.chmod(script_mode)
                self.env["REPO_ROOT"] = str(repo)
                self.env["HOME"] = str(home)
                try:
                    result = self.run_script(SYNC)
                finally:
                    self.env["HOME"] = str(self.home)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = home / ".gemini/config"
                self.assertFalse((config / "hooks.json").is_symlink())
                self.assertEqual((config / "hooks.json").read_text(), "{}\n")
                self.assertFalse((config / "skills/proactive-bolt").is_symlink())
                self.assertTrue(
                    (config / "proactive/scripts/proactive-worktree.sh").is_file()
                )
                self.assertTrue(
                    (config / "proactive/hooks/proactive-guard.py").is_file()
                )

    def test_sync_refuses_to_activate_deployed_configs_when_ctl_missing(self) -> None:
        repo = self.root / "repo"
        (repo / "configs/antigravity/skills/proactive-bolt").mkdir(parents=True)
        (repo / "configs/antigravity/skills/proactive-bolt/SKILL.md").write_text(
            "`$HOME/.gemini/config/proactive/scripts/proactive-worktree.sh`\n"
        )
        (repo / "configs/antigravity/hooks.json").write_text(
            '{"proactive-safety-guard":{"command":"python3 \\"$HOME/.gemini/config/proactive/hooks/proactive-guard.py\\""}}\n'
        )
        self.env["REPO_ROOT"] = str(repo)
        result = self.run_script(SYNC)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required controller", result.stderr)
        self.assertFalse((self.home / ".gemini/config/hooks.json").exists())
        self.assertFalse((self.home / ".gemini/config/skills/proactive-bolt").exists())


if __name__ == "__main__":
    unittest.main()
