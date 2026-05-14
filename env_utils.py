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
def get_parsed_env_vars(env_file="../email-security-pipeline/GH_TOKEN.env"):
    """Reads and parses environment variables from a file, with caching."""
    parsed_vars = {}
    try:
        with open(env_file, "r") as f:
            for line in f:
                parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        pass
    return parsed_vars

def load_gh_token_env():
    """Returns a copy of os.environ updated with variables from the GH_TOKEN.env file."""
    env = os.environ.copy()
    env.update(get_parsed_env_vars())
    return env
