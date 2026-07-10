"""Load GH_TOKEN for local automation without shell-sourcing secret files.

SECURITY: Never use ``source`` on env files in shell scripts (CWE-78 risk when
combined with untrusted input). Parse files in Python and pass via ``subprocess``
``env=`` instead.

Precedence for ``GH_TOKEN``:
1. Existing ``os.environ['GH_TOKEN']`` (e.g. ``export GH_TOKEN=$(gh auth token)``)
2. Optional file from ``GH_TOKEN_ENV_FILE`` or well-known paths (legacy fallback)
"""

import re

import os
from functools import lru_cache
from pathlib import Path
from typing import Mapping

# Legacy path referenced in ABHI-954 / TruffleHog finding (gitignored, out of repo).
_LEGACY_RELATIVE_ENV = Path("../email-security-pipeline/GH_TOKEN.env")

# SECURITY: reject command substitution in parsed values.
_COMMAND_SUBSTITUTION = re.compile(r"\$\(|`")

_RUNBOOK = "docs/github-pat-rotation-runbook.md"


def parse_env_line(line: str, env_dict: dict[str, str]) -> None:
    """Parse a single KEY=VALUE line from a dotenv-style file."""
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    key, sep, val = line.partition("=")
    if not sep:
        return
    value = val.strip().strip("'\"")
    if _COMMAND_SUBSTITUTION.search(value):
        return
    env_dict[key] = value


def _read_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                parse_env_line(line, parsed)
    except OSError:
        return {}
    return parsed


def resolve_gh_token_env_file() -> Path | None:
    """Return the first existing GH_TOKEN env file path, or None."""
    override = os.environ.get("GH_TOKEN_ENV_FILE", "").strip()
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate

    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        xdg_path = Path(xdg).expanduser() / "personal-config" / "GH_TOKEN.env"
        if xdg_path.is_file():
            return xdg_path

    home_config = Path.home() / ".config" / "personal-config" / "GH_TOKEN.env"
    if home_config.is_file():
        return home_config

    legacy = _LEGACY_RELATIVE_ENV
    if legacy.is_file():
        return legacy

    return None


@lru_cache(maxsize=1)
def _get_parsed_env_vars_from_file() -> dict[str, str]:
    path = resolve_gh_token_env_file()
    if path is None:
        return {}
    return _read_env_file(path)


def load_gh_token_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build an environment dict for ``gh`` subprocess calls."""
    env = dict(base if base is not None else os.environ)
    if env.get("GH_TOKEN"):
        return env
    env.update(_get_parsed_env_vars_from_file())
    return env


def clear_gh_token_cache() -> None:
    """Clear cached file reads (for tests after changing GH_TOKEN_ENV_FILE)."""
    _get_parsed_env_vars_from_file.cache_clear()


def missing_gh_token_message() -> str:
    """User-facing hint when GH_TOKEN is absent (no secret values)."""
    path = resolve_gh_token_env_file()
    if path is not None:
        return (
            f"GH_TOKEN is not set. After rotating your PAT, update {path} "
            f"or export GH_TOKEN. See {_RUNBOOK}."
        )
    return (
        "GH_TOKEN is not set. Export GH_TOKEN, use `gh auth login`, or set "
        f"GH_TOKEN_ENV_FILE. See {_RUNBOOK}."
    )
