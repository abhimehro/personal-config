"""Shared utilities for GitHub CLI automation scripts.

Consolidates env-file loading and `gh` CLI invocation that was previously
duplicated across categorize_ready.py, detect_duplicates.py,
parse_inventory.py, and run_merges.py.

SECURITY: When GH_TOKEN_ENV_PATH is explicitly set, the referenced file
MUST exist and be readable. Failing closed avoids running destructive
GitHub CLI operations with an uninitialized environment. When the env
var is unset (or empty), the default path is used and a missing file is
tolerated to preserve the pre-existing fallback behavior.
"""

import json
import os
import subprocess
from functools import lru_cache
from types import MappingProxyType


DEFAULT_GH_TOKEN_ENV_PATH = "../email-security-pipeline/GH_TOKEN.env"


def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        return
    key, val = line.split("=", 1)
    env_dict[key] = val.strip("'\"")


def _resolve_env_path():
    """Return (resolved_path, was_overridden) for the token env file."""
    override = os.getenv("GH_TOKEN_ENV_PATH")
    return (override or DEFAULT_GH_TOKEN_ENV_PATH, bool(override))


@lru_cache(maxsize=None)
def _parse_env_file(env_path, fail_closed):
    # ⚡ Bolt Optimization: Cache only the parsed variables from the file to
    # prevent redundant IO reads. The cached value is wrapped in
    # MappingProxyType so callers cannot mutate it and poison the cache.
    # Keying on `env_path` ensures that runtime changes to
    # GH_TOKEN_ENV_PATH (e.g. in tests) produce a fresh read instead of
    # silently returning a stale first-call result.
    parsed_vars = {}
    try:
        with open(env_path, "r") as f:
            for line in f:
                _parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        # Fail closed only when the caller explicitly overrode the path. A
        # missing default-path file is tolerated to preserve prior behavior.
        if fail_closed:
            raise
    return MappingProxyType(parsed_vars)


def _get_parsed_env_vars():
    env_path, was_overridden = _resolve_env_path()
    return _parse_env_file(env_path, was_overridden)


def load_gh_token_env():
    """Return a copy of os.environ augmented with vars from the token file."""
    env = os.environ.copy()
    env.update(_get_parsed_env_vars())
    return env


def require_gh_token_env():
    """Fail-closed guard for destructive scripts.

    Raises FileNotFoundError if the resolved token env file is missing.
    Unlike load_gh_token_env(), this enforces presence of the file even
    when the default path is in use (no GH_TOKEN_ENV_PATH override),
    mirroring the fail-closed behavior of the shell scripts.
    """
    env_path, _ = _resolve_env_path()
    if not os.path.isfile(env_path):
        raise FileNotFoundError(
            f"GH token env file is missing or unreadable: {env_path}"
        )
    return load_gh_token_env()


def run_gh(cmd_list):
    """Run a `gh` command and return parsed JSON, or None on failure."""
    env = load_gh_token_env()
    result = subprocess.run(cmd_list, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except (ValueError, json.JSONDecodeError):
        return None
