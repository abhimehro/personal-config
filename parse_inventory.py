import json
import os
import re
import subprocess
from datetime import datetime, timezone
from functools import lru_cache


def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line:
        return
    if line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        return
    key, val = line.split("=", 1)
    env_dict[key] = val.strip("'\"")


@lru_cache(maxsize=None)
def _get_parsed_env_vars():
    # ⚡ Bolt Optimization: Cache only the parsed variables from the file to prevent redundant IO reads, while keeping it safe from mutable dictionary cache poisoning
    parsed_vars = {}
    try:
        with open("../email-security-pipeline/GH_TOKEN.env", "r") as f:
            for line in f:
                _parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        pass
    return parsed_vars


def _load_gh_token_env():
    env = os.environ.copy()
    env.update(_get_parsed_env_vars())
    return env


def run_gh(repo, pr):
    env = _load_gh_token_env()
    cmd = [
        "gh",
        "pr",
        "view",
        str(pr),
        "-R",
        str(repo),
        "--json",
        "files,updatedAt,mergeStateStatus",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None


def _process_inventory_line(line, current_repo, repos):
    m = re.match(r"^## (.*)", line)
    if m:
        repo_name = m.group(1).strip()
        if repo_name not in repos:
            repos[repo_name] = []
        return repo_name

    if not line.startswith("|"):
        return current_repo
    if line.startswith("| # |") or line.startswith("| ---"):
        return current_repo

    parts = line.split("|")
    if len(parts) <= 9:
        return current_repo

    pr_id = parts[2].strip()
    author = parts[5].strip()
    checks = parts[8].strip()
    hints = parts[9].strip()

    if not pr_id.isdigit():
        return current_repo

    if not (author.endswith("[bot]") or hints):
        return current_repo

    if current_repo is not None:
        repos[current_repo].append({"pr": pr_id, "checks": checks})

    return current_repo


def parse_inventory_lines(lines):
    repos = {}
    current_repo = None
    for line in lines:
        current_repo = _process_inventory_line(line, current_repo, repos)
    return repos


def _process_pr(repo, pr_info, triage):
    pr = pr_info["pr"]
    checks = pr_info["checks"]
    print(f"Checking {repo}#{pr}")

    info = run_gh(repo, pr)
    if not info:
        print(f"Failed to fetch {repo}#{pr}")
        return

    files = info.get("files", [])
    if not files:
        triage["SUPERSEDED"].append(f"{repo}#{pr}")
        return

    updated_at = info.get("updatedAt", "")
    merge_status = info.get("mergeStateStatus", "")

    days_old = 0
    if updated_at:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_old = (now - dt).days

    is_stale = days_old > 30
    checks_failing = ("FAIL" in checks) or ("PENDING" in checks)

    if is_stale and checks_failing:
        triage["STALE"].append(f"{repo}#{pr}")
        return

    if merge_status in ["DIRTY", "CONFLICTING"]:
        triage["CONFLICTING"].append(f"{repo}#{pr}")
        return

    if merge_status == "CLEAN" and not checks_failing:
        triage["READY"].append(f"{repo}#{pr}")
        return


def main():
    try:
        with open("tasks/pr-inventory.md", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    repos = parse_inventory_lines(lines)

    triage = {"SUPERSEDED": [], "STALE": [], "CONFLICTING": [], "READY": []}

    for repo, prs in repos.items():
        for pr_info in prs:
            _process_pr(repo, pr_info, triage)

    with open("tasks/pr-triage.md", "w") as f:
        f.write("# PR Triage\n\n")
        for category, pr_list in triage.items():
            f.write(f"## {category}\n")
            for pr in pr_list:
                f.write(f"- {pr}\n")

    print("Done")


if __name__ == "__main__":
    main()
