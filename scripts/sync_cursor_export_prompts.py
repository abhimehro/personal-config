#!/usr/bin/env python3
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
        export_path = exports / export_name
        prompt_path = prompts / prompt_name
        try:
            export = json.loads(export_path.read_text(encoding="utf-8"))
            prompt = prompt_path.read_text(encoding="utf-8").strip() + "\n"
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{export_name}: {exc}")
            continue
        entries = export.get("prompts")
        if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
            errors.append(f"{export_name}: expected one prompt entry")
            continue
        if entries[0].get("prompt") == prompt:
            continue
        if not write:
            errors.append(f"{export_name}: prompt differs from {prompt_name}")
            continue
        entries[0]["prompt"] = prompt
        export_path.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    return errors


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
