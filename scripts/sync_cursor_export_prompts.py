"""Synchronize Cursor export prompt fields with their reviewed Markdown sources.

Run with --write to update the checked-in exports, or --check to fail if the
runtime-copy source would drift. The script uses only the observed Cursor export
schema and does not call Cursor or mutate any dashboard automation.

Markdown sources may include a whole-line
``{{include:_allowlisted.md}}`` directive. Exports store the expanded prompt
so Dashboard paste is a complete body, never a raw include token.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = {
    "daily-pr-review.json": "daily-pr-review.md",
    "daily-pr-salvage.json": "daily-pr-salvage.md",
    "daily-pr-completion.calibration.json": "daily-pr-completion.calibration.md",
    "daily-pr-completion.json": "daily-pr-completion.md",
}

# SECURITY: only underscore-prefixed files in the prompts directory.
INCLUDE_NAME_RE = re.compile(r"^_[A-Za-z0-9][A-Za-z0-9_.-]{0,62}\.md$")
INCLUDE_LINE_RE = re.compile(
    r"^\{\{include:(_[A-Za-z0-9][A-Za-z0-9_.-]{0,62}\.md)\}\}\s*$",
    re.MULTILINE,
)


class PromptIncludeError(ValueError):
    """Raised when a prompt include is missing, nested, or not allowlisted."""


@dataclass
class PromptReconciliation:
    export: dict[str, object]
    entry: dict[str, object]
    export_path: Path
    prompt_name: str
    prompt: str


_TRAVERSAL_MARKERS = ("..", "/", "\\")


def _include_name_allowed(name: str) -> bool:
    """Return True when the include name matches the prompts-dir allowlist."""
    return INCLUDE_NAME_RE.fullmatch(name) is not None


def _include_name_has_traversal(name: str) -> bool:
    """Return True when the include name contains a separator or parent token."""
    return any(marker in name for marker in _TRAVERSAL_MARKERS)


def _path_stays_in_prompts(prompts_dir: Path, target: Path) -> bool:
    """Return True when resolved target stays inside the prompts directory."""
    try:
        target.relative_to(prompts_dir)
    except ValueError:
        return False
    return True


def _resolved_include_path(prompts_dir: Path, name: str) -> Path:
    """SECURITY: allowlisted relative markdown only; reject traversal."""
    if not _include_name_allowed(name):
        raise PromptIncludeError(f"include not allowlisted: {name}")
    if _include_name_has_traversal(name):
        raise PromptIncludeError(f"include path rejected: {name}")
    target = (prompts_dir / name).resolve()
    if not _path_stays_in_prompts(prompts_dir, target):
        raise PromptIncludeError(f"include escaped prompts dir: {name}")
    return target


def _read_include(prompts_dir: Path, name: str) -> str:
    """Read one allowlisted include; nested tokens are forbidden."""
    target = _resolved_include_path(prompts_dir, name)
    if not target.is_file():
        raise PromptIncludeError(f"include missing: {name}")
    included = target.read_text(encoding="utf-8")
    if "{{include:" in included:
        raise PromptIncludeError(f"nested include forbidden: {name}")
    return included.strip()


def expand_prompt_includes(text: str, prompts_dir: Path) -> str:
    """Replace allowlisted whole-line include directives with file contents.

    SECURITY: reject ``..``, absolute paths, nested includes, and any name
    outside the prompts directory allowlist. Fail closed on malformed tokens.
    """
    prompts_dir = prompts_dir.resolve()
    if "{{include:" in text and INCLUDE_LINE_RE.search(text) is None:
        raise PromptIncludeError("malformed include; must be a whole line")
    expanded = INCLUDE_LINE_RE.sub(
        lambda match: _read_include(prompts_dir, match.group(1)), text
    )
    if "{{include:" in expanded:
        raise PromptIncludeError("unexpanded include remains")
    return expanded


def expand_prompt_source(prompt_path: Path) -> str:
    """Read a prompt markdown file and expand allowlisted includes."""
    return expand_prompt_includes(
        prompt_path.read_text(encoding="utf-8"), prompt_path.parent
    )


def sync(write: bool) -> list[str]:
    errors: list[str] = []
    exports = ROOT / "docs/cursor-automations/exports"
    prompts = ROOT / "docs/cursor-automations/prompts"
    for export_name, prompt_name in MAPPINGS.items():
        error = sync_one(exports / export_name, prompts / prompt_name, write)
        if error:
            errors.append(error)
    return errors


def sync_one(export_path: Path, prompt_path: Path, write: bool) -> str | None:
    reconciliation = load_prompt_reconciliation(export_path, prompt_path)
    if isinstance(reconciliation, str):
        return reconciliation
    if reconciliation.entry.get("prompt") == reconciliation.prompt:
        return None
    return reconcile_prompt(reconciliation, write)


def load_prompt_reconciliation(
    export_path: Path, prompt_path: Path
) -> PromptReconciliation | str:
    try:
        export = json.loads(export_path.read_text(encoding="utf-8"))
        prompt = expand_prompt_source(prompt_path).strip() + "\n"
    except (OSError, json.JSONDecodeError, PromptIncludeError) as exc:
        return f"{export_path.name}: {exc}"
    entry = get_single_prompt_entry(export, export_path.name)
    if isinstance(entry, str):
        return entry
    return PromptReconciliation(export, entry, export_path, prompt_path.name, prompt)


def get_single_prompt_entry(
    export: dict[str, object], export_name: str
) -> dict[str, object] | str:
    entries = export.get("prompts")
    valid = isinstance(entries, list) and len(entries) == 1
    valid = valid and isinstance(entries[0], dict)
    if not valid:
        return f"{export_name}: expected one prompt entry"
    return entries[0]


def reconcile_prompt(reconciliation: PromptReconciliation, write: bool) -> str | None:
    if not write:
        return (
            f"{reconciliation.export_path.name}: prompt differs from "
            f"{reconciliation.prompt_name}"
        )
    reconciliation.entry["prompt"] = reconciliation.prompt
    reconciliation.export_path.write_text(
        json.dumps(reconciliation.export, indent=2) + "\n", encoding="utf-8"
    )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = sync(write=args.write)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(
        "CURSOR_EXPORT_PROMPTS_SYNCHRONIZED"
        if args.write
        else "CURSOR_EXPORT_PROMPTS_MATCH"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
