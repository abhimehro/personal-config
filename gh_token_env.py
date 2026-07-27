"""Load GH_TOKEN for local automation without shell-sourcing secret files.

SECURITY: Never use ``source`` on env files in shell scripts (CWE-78 risk when
combined with untrusted input). Parse files in Python and pass via ``subprocess``
``env=`` instead.

Precedence for ``GH_TOKEN``:
1. Existing ``os.environ['GH_TOKEN']`` (e.g. ``export GH_TOKEN=$(gh auth token)``)
2. Optional file from ``GH_TOKEN_ENV_FILE`` or well-known paths (legacy fallback)
"""

import os
import re
import stat
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Mapping

# Legacy path referenced in ABHI-954 / TruffleHog finding (gitignored, out of repo).
# Resolved relative to this source file so it is stable regardless of the process
# working directory.
_BASE_DIR = Path(__file__).resolve().parent
_LEGACY_RELATIVE_ENV = (
    _BASE_DIR.parent / "email-security-pipeline" / "GH_TOKEN.env"
).resolve()

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


def _validate_env_fd(fd: int, path: Path) -> None:
    """Validate ownership and permissions of an already-open env file."""
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):
        raise PermissionError(f"{path}: not a regular file")
    if st.st_uid != os.getuid():
        raise PermissionError(f"{path}: not owned by current user")
    if st.st_mode & 0o077:
        raise PermissionError(f"{path}: permissions too open (want 0600)")


def _parse_env_lines(handle, parsed: dict[str, str]) -> None:
    """Read a dotenv-style file handle into ``parsed``."""
    for line in handle:
        parse_env_line(line, parsed)


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a dotenv-style file with fd-based TOCTOU-safe ownership checks."""
    parsed: dict[str, str] = {}
    fd = -1
    try:
        # SECURITY: O_NOFOLLOW prevents symlink hijacking; fstat validates the
        # fd we actually read, not a path that may have changed since resolve().
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        _validate_env_fd(fd, path)
        with os.fdopen(fd, encoding="utf-8") as handle:
            fd = -1  # ownership transferred; avoid double-close
            _parse_env_lines(handle, parsed)
    except FileNotFoundError:
        return {}
    except PermissionError:
        # Preserve the specific, user-friendly message from fd validation.
        raise
    except OSError as exc:
        # SECURITY: ownership, permission, or symlink (ELOOP) failures must
        # not silently fall back to an empty token.
        raise PermissionError(f"{path}: refusing to load env file ({exc})") from exc
    finally:
        if fd >= 0:
            os.close(fd)
    return parsed


def resolve_gh_token_env_file() -> Path | None:
    """Return the first existing GH_TOKEN env file path, or None."""
    override = os.environ.get("GH_TOKEN_ENV_FILE", "").strip()
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(
            f"GH_TOKEN_ENV_FILE does not exist or is not a file: {candidate}"
        )

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
    """Build an environment dict for ``gh`` subprocess calls.

    Precedence:
    1. ``GH_TOKEN`` already present in ``base``/``os.environ``.
    2. ``GH_TOKEN`` read from ``GH_TOKEN_ENV_FILE`` or a well-known path.
    """
    env = dict(base if base is not None else os.environ)
    if env.get("GH_TOKEN"):
        return env

    used_path = resolve_gh_token_env_file()
    if used_path is None:
        return env
    if used_path == _LEGACY_RELATIVE_ENV:
        warnings.warn(
            f"legacy GH_TOKEN.env path is deprecated: {_LEGACY_RELATIVE_ENV}; "
            "set GH_TOKEN or GH_TOKEN_ENV_FILE instead",
            DeprecationWarning,
            stacklevel=2,
        )

    file_vars = _get_parsed_env_vars_from_file()
    # Only the token value is required for ``gh``; do not inject unrelated keys.
    if "GH_TOKEN" in file_vars:
        env["GH_TOKEN"] = file_vars["GH_TOKEN"]
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
