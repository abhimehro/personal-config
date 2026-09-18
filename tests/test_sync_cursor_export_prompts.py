"""Prompt include expansion for Cursor export sync."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from sync_cursor_export_prompts import (  # noqa: E402
    PromptIncludeError,
    expand_prompt_includes,
    expand_prompt_source,
)

PROMPTS = ROOT / "docs/cursor-automations/prompts"
EXPORTS = ROOT / "docs/cursor-automations/exports"


class TestPromptIncludeExpansion(unittest.TestCase):
    def test_plain_text_is_unchanged(self) -> None:
        text = "No include directive here.\n"
        self.assertEqual(expand_prompt_includes(text, PROMPTS), text)

    def test_expands_multiple_includes_and_preserves_surrounding_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompts_dir = Path(tmp)
            (prompts_dir / "_first.md").write_text(
                "\nfirst shared block\n", encoding="utf-8"
            )
            (prompts_dir / "_second.md").write_text(
                "second shared block\n\n", encoding="utf-8"
            )
            source = (
                "before\n"
                "{{include:_first.md}}\n"
                "between\n"
                "{{include:_second.md}}   \n"
                "after\n"
            )

            expanded = expand_prompt_includes(source, prompts_dir)

            self.assertEqual(
                expanded,
                "before\nfirst shared block\nbetween\nsecond shared block\nafter\n",
            )

    def test_stage_prompts_expand_shared_frame(self) -> None:
        partner = "{{include:_shared-partner-frame.md}}"
        cas = "{{include:_shared-cas-bootstrap.md}}"
        for name in (
            "daily-pr-review.md",
            "daily-pr-salvage.md",
            "daily-pr-completion.md",
        ):
            with self.subTest(name):
                raw = (PROMPTS / name).read_text(encoding="utf-8")
                expanded = expand_prompt_source(PROMPTS / name)
                self.assertEqual(raw.count(partner), 1)
                self.assertEqual(raw.count(cas), 1)
                self.assertNotIn("{{include:", expanded)
                self.assertIn("security-first development partner", expanded)
                self.assertIn("stale-vs-main", expanded)
                self.assertIn("This stage (Stage", expanded)
                self.assertIn("pr_lifecycle_ledger_cas.py preflight", expanded)

    def test_exports_store_expanded_prompt(self) -> None:
        for export_name in (
            "daily-pr-review.json",
            "daily-pr-salvage.json",
            "daily-pr-completion.json",
        ):
            with self.subTest(export_name):
                data = json.loads(
                    (EXPORTS / export_name).read_text(encoding="utf-8")
                )
                prompt = data["prompts"][0]["prompt"]
                self.assertNotIn("{{include:", prompt)
                self.assertIn("security-first development partner", prompt)
                self.assertIn("stale-vs-main", prompt)
                self.assertIn("pr_lifecycle_ledger_cas.py preflight", prompt)

    def test_rejects_path_traversal(self) -> None:
        with self.assertRaises(PromptIncludeError):
            expand_prompt_includes(
                "{{include:_../secrets.md}}\n", PROMPTS
            )

    def test_rejects_dotdot_in_allowlisted_charset(self) -> None:
        """``..`` inside an otherwise allowlisted name is still traversal."""
        with self.assertRaises(PromptIncludeError):
            expand_prompt_includes(
                "{{include:_foo..bar.md}}\n", PROMPTS
            )

    def test_rejects_nested_include(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompts_dir = Path(tmp)
            nested = prompts_dir / "_nested.md"
            nested.write_text("{{include:_other.md}}\n", encoding="utf-8")
            with self.assertRaises(PromptIncludeError):
                expand_prompt_includes(
                    "{{include:_nested.md}}\n", prompts_dir
                )

    def test_rejects_missing_include(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(PromptIncludeError, "include missing"):
                expand_prompt_includes(
                    "{{include:_missing.md}}\n", Path(tmp)
                )

    def test_rejects_symlink_that_escapes_prompts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompts_dir = root / "prompts"
            prompts_dir.mkdir()
            outside = root / "outside.md"
            outside.write_text("must not be included\n", encoding="utf-8")
            (prompts_dir / "_escape.md").symlink_to(outside)

            with self.assertRaisesRegex(
                PromptIncludeError, "include escaped prompts dir"
            ):
                expand_prompt_includes(
                    "{{include:_escape.md}}\n", prompts_dir
                )

    def test_rejects_malformed_include(self) -> None:
        with self.assertRaises(PromptIncludeError):
            expand_prompt_includes(
                "see {{include:_shared-partner-frame.md}}", PROMPTS
            )


if __name__ == "__main__":
    unittest.main()
