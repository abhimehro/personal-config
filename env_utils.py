import os
from functools import lru_cache

def parse_env_line(line, env_dict):
    """Parses a single line from an .env file and updates env_dict."""
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        return
    key, val = line.split("=", 1)
    env_dict[key] = val.strip("'\"")

@lru_cache(maxsize=None)
def _get_parsed_env_items(env_file="../email-security-pipeline/GH_TOKEN.env"):
    """Reads and parses env vars from a file, returning an immutable tuple of items.

    Caching an immutable tuple (instead of a dict) prevents accidental cache
    poisoning if a caller mutates the returned mapping.
    """
    parsed_vars = {}
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        pass
    return tuple(parsed_vars.items())

def get_parsed_env_vars(env_file="../email-security-pipeline/GH_TOKEN.env"):
    """Returns a fresh dict of environment variables parsed from the given file."""
    return dict(_get_parsed_env_items(env_file))

def load_gh_token_env():
    """Returns a copy of os.environ updated with variables from the GH_TOKEN.env file."""
    env = os.environ.copy()
    env.update(get_parsed_env_vars())
    return env
