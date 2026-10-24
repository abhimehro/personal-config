"""Executable-path and evidence-stamp validity tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails

from tests.pr_lifecycle_helpers import guardrail_item

HEAD_SHA = "a" * 40


class ExecutablePathTests(unittest.TestCase):
    def test_suffix_samples_and_unknown_extensions_are_executable(self) -> None:
        for path in (
            "lib/Foo.pm",
            "src/App.vue",
            "nb.ipynb",
            "flake.nix",
            "config.yaml",
            "package.json",
            "x.PY",
            "CMakeLists.txt",
            "src/cmakelists.TXT",
            "constraints.txt",
            "constraints-dev.txt",
            "requirements-dev.txt",
            ".gitconfig.bak",
            "assets/icon.svg",
            "src/data.json",
            "bin/tool.pyc",
            "x.v",
            "x.d",
        ):
            with self.subTest(path=path):
                self.assertTrue(guardrails.is_executable_path(path))

    def test_executable_basenames_and_suffixless_paths(self) -> None:
        for path in (
            "Makefile",
            "pkg/Dockerfile",
            "Justfile",
            "pkg/Rakefile",
            "GNUmakefile",
            "Gemfile",
            "Vagrantfile",
            "Jenkinsfile",
            "Containerfile",
            "Procfile",
            "Taskfile",
            "Podfile",
            "Fastfile",
            "Dangerfile",
            "Brewfile",
            "bin/tool",
            "pkg/scripts/run",
            "src/bin/test_helper",
            "tools/deploy",
            "run",
            "sbin/tool",
            "mybin/tool",
            "Scripts/run",
            "configs/.zshrc",
            "configs/.config/agent-shell/zshrc",
            "configs/.bash_profile",
            ".bash_aliases",
            ".xprofile",
            "aliases",
            "functions",
            ".shrc",
            ".mkshrc",
            "configs/.gitconfig",
            "gitconfig",
            "mygitconfig",
            "work.gitconfig",
            "foo.GITCONFIG",
            "configs/.config/git/config",
            "Git/Config",
            ".cshrc",
            "configs/.tcshrc",
            "x.ksh",
            "x.psm1",
            "x.mts",
            "x.awk",
            ".husky/pre-commit",
        ):
            with self.subTest(path=path):
                self.assertTrue(guardrails.is_executable_path(path))

    def test_document_and_metadata_paths_are_non_executable(self) -> None:
        for path in (
            "README.md",
            "docs/a.TXT",
            "notes.txt",
            "docs/README.txt",
            "data.csv",
            "img.png",
            "LICENSE",
            ".gitignore",
            "README",
            "docs/readme.md",
            "mygitconfig.txt",
        ):
            with self.subTest(path=path):
                self.assertFalse(guardrails.is_executable_path(path))


class EvidenceStampValidityTests(unittest.TestCase):
    def test_current_stamp_requires_valid_head_and_compatible_basis(self) -> None:
        invalid_stamps = (
            guardrail_item(
                head_sha=None,
                changed_paths=["README.md"],
                guardrail_evidence={
                    "head_sha": None,
                    "basis": "head_bound_diff",
                    "diff_sha256": None,
                },
            ),
            guardrail_item(
                head_sha="invalid",
                changed_paths=["README.md"],
                guardrail_evidence={
                    "head_sha": "invalid",
                    "basis": "head_bound_diff",
                    "diff_sha256": None,
                },
            ),
            guardrail_item(
                changed_paths=["src/worker.py"],
                guardrail_evidence={
                    "head_sha": HEAD_SHA,
                    "basis": "non_executable_paths",
                    "diff_sha256": None,
                },
            ),
        )
        for item in invalid_stamps:
            with self.subTest(item=item):
                self.assertFalse(guardrails.has_current_evidence_stamp(item))
