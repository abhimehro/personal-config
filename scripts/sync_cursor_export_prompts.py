"""Synchronize Cursor export prompt fields with their reviewed Markdown sources.

Run with --write to update the checked-in exports, or --check to fail if the
runtime-copy source would drift. The script uses only the observed Cursor export
schema and does not call Cursor or mutate any dashboard automation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = {
    "daily-pr-review.json": "daily-pr-review.md",
    "daily-pr-salvage.json": "daily-pr-salvage.md",
    "daily-pr-completion.calibration.json": "daily-pr-completion.calibration.md",
    "daily-pr-completion.json": "daily-pr-completion.md",
}


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
    try:
        export = json.loads(export_path.read_text(encoding="utf-8"))
        prompt = prompt_path.read_text(encoding="utf-8").strip() + "\n"
    except (OSError, json.JSONDecodeError) as exc:
        return f"{export_path.name}: {exc}"
    entry = get_single_prompt_entry(export, export_path.name)
    if isinstance(entry, str):
        return entry
    if entry.get("prompt") == prompt:
        return None
    return reconcile_prompt(entry, export, export_path, prompt_path.name, prompt, write)


def get_single_prompt_entry(export: dict[str, object], export_name: str) -> dict[str, object] | str:
    entries = export.get("prompts")
    valid = isinstance(entries, list) and len(entries) == 1
    valid = valid and isinstance(entries[0], dict)
    if not valid:
        return f"{export_name}: expected one prompt entry"
    return entries[0]


def reconcile_prompt(
    entry: dict[str, object],
    export: dict[str, object],
    export_path: Path,
    prompt_name: str,
    prompt: str,
    write: bool,
) -> str | None:
    if not write:
        return f"{export_path.name}: prompt differs from {prompt_name}"
    entry["prompt"] = prompt
    export_path.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
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
    print("CURSOR_EXPORT_PROMPTS_SYNCHRONIZED" if args.write else "CURSOR_EXPORT_PROMPTS_MATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
