"""Shared utilities for invoking the GitHub CLI (`gh`)."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from gh_token_env import load_gh_token_env

__all__ = ["run_gh"]


def run_gh(cmd_list: list[str], *, raw_fallback: bool = False) -> Any | None:
    """Call ``gh`` and return parsed JSON, or None on failure/timeout.

    If ``raw_fallback`` is True, returns raw stdout string when JSON decoding fails.
    """
    env = load_gh_token_env()
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        cmd_name = cmd_list[0] if cmd_list else cmd_list
        print(
            f"gh command failed or timed out ({type(exc).__name__}): {cmd_name}",
            file=sys.stderr,
        )
        return None

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout if raw_fallback else None
