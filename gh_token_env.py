"""GitHub token environment helpers for local ``gh`` subprocess calls.

SECURITY: Never read token files from fixed paths inside this repository.
Use ``GH_TOKEN`` / ``GITHUB_TOKEN``, ``gh auth token``, or an explicit
``GH_TOKEN_ENV_FILE`` pointing to a user-managed file outside the repo tree.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _parse_env_line(line: str, env_dict: dict[str, str]) -> None:
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    key, sep, val = line.partition("=")
    if not sep:
        return
    env_dict[key] = val.strip("'\"")


def _token_env_file_path() -> Path | None:
    explicit = os.environ.get("GH_TOKEN_ENV_FILE", "").strip()
    if not explicit:
        return None
    return Path(explicit).expanduser()


@lru_cache(maxsize=None)
def _get_parsed_env_vars() -> dict[str, str]:
    parsed_vars: dict[str, str] = {}
    path = _token_env_file_path()
    if path is None:
        return parsed_vars
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                _parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        pass
    return parsed_vars


def load_gh_subprocess_env() -> dict[str, str]:
    """Return a copy of ``os.environ`` suitable for ``subprocess`` ``gh`` calls."""
    env = os.environ.copy()
    for key, value in _get_parsed_env_vars().items():
        env.setdefault(key, value)
    if not env.get("GH_TOKEN") and env.get("GITHUB_TOKEN"):
        env["GH_TOKEN"] = env["GITHUB_TOKEN"]
    return env
