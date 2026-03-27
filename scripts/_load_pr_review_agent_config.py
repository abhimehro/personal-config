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
from typing import Any


def _try_import_yaml():
    try:
        import yaml  # type: ignore[import-untyped]

        return yaml
    except ImportError:
        return None


def _load_mapping(path: Path) -> dict[str, Any] | None:
    yaml = _try_import_yaml()
    if yaml is None:
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def _emit_repos(repos: Any) -> bool:
    if not isinstance(repos, list):
        return False
    for item in repos:
        if isinstance(item, str) and item.strip():
            print(f"repo\t{item.strip()}")
    return True


def _emit_bot_authors(bots: Any) -> None:
    if not isinstance(bots, list):
        return
    for item in bots:
        if not isinstance(item, str):
            continue
        ent = item.split("#", 1)[0].strip()
        if ent:
            print(f"bot\t{ent}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: _load_pr_review_agent_config.py CONFIG_PATH", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        return 1

    data = _load_mapping(path)
    if data is None:
        return 2 if _try_import_yaml() is None else 1

    if not _emit_repos(data.get("repos") or []):
        return 1
    _emit_bot_authors(data.get("bot_authors") or [])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
