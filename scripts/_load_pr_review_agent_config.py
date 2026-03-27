#!/usr/bin/env python3
"""Emit repos and bot_authors from tasks/pr-review-agent.config.yaml for get_prs.sh.

Uses PyYAML when installed (same as repository automation). Exits 2 if PyYAML is
missing so the caller can fall back to bash line parsing.

Output format (machine lines for bash):
  repo\towner/name
  bot\tdependabot[bot]
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: _load_pr_review_agent_config.py CONFIG_PATH", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        return 1
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return 2

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return 1

    repos = data.get("repos") or []
    if not isinstance(repos, list):
        return 1
    for item in repos:
        if isinstance(item, str) and item.strip():
            print(f"repo\t{item.strip()}")

    bots = data.get("bot_authors") or []
    if isinstance(bots, list):
        for item in bots:
            if not isinstance(item, str):
                continue
            ent = item.split("#", 1)[0].strip()
            if ent:
                print(f"bot\t{ent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
