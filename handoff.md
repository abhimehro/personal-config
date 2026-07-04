========== ELIR ==========
PURPOSE: Removed unused `_load_gh_token_env` functions across scripts (`categorize_ready.py`, `detect_duplicates.py`, `parse_inventory.py`, `run_merges.py`) and standardizes them to import and use the central `load_gh_token_env` from `gh_token_env.py`.
SECURITY: Reduces the attack surface of environment parsing logic by consolidating to a single, well-tested module. Ensures token loading maintains safe practices (does not use `source` in shell).
FAILS IF: `gh_token_env.py` has import errors or behaves differently from the legacy duplicate code (but our tests verify behavioral equivalence).
VERIFY: Ensure all automated tests (`make test-all`) pass and that scripts no longer redefine `_load_gh_token_env`.
MAINTAIN: Going forward, any new Python script that needs a GH_TOKEN for subprocess calls MUST import and use `load_gh_token_env` from `gh_token_env.py`.
