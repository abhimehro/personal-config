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
    except json.JSONDecodeError:
        return None


def _should_skip_table_row(line):
    if not line.startswith("|"):
        return True
    if line.startswith("| # |"):
        return True
    if line.startswith("| ---"):
        return True
    return False


def _parse_repo_name(line):
    m = re.match(r"^## (.*)", line)
    return m.group(1).strip() if m else None


def _is_valid_pr_row(pr_id, author, hints):
    if not pr_id.isdigit():
        return False
    return author.endswith("[bot]") or hints


def _extract_pr_row_fields(parts):
    repo_col = parts[1].strip()
    if repo_col:
        return repo_col, parts[2].strip(), parts[3].strip(), parts[6].strip(), parts[9].strip()
    return "", parts[2].strip(), parts[5].strip(), parts[8].strip(), parts[9].strip()


def _ensure_repo_bucket(repo_name, repos):
    if repo_name not in repos:
        repos[repo_name] = []


def _parse_row_record(line, current_repo):
    parts = line.split("|")
    if len(parts) <= 9:
        return None
    repo_col, pr_id, author, checks, hints = _extract_pr_row_fields(parts)
    effective_repo = repo_col or current_repo
    if effective_repo is None:
        return None
    if not _is_valid_pr_row(pr_id, author, hints):
        return None
    return effective_repo, {"pr": pr_id, "checks": checks}


def _process_inventory_line(line, current_repo, repos):
    repo_name = _parse_repo_name(line)
    if repo_name:
        _ensure_repo_bucket(repo_name, repos)
        return repo_name

    if _should_skip_table_row(line):
        return current_repo

    row_record = _parse_row_record(line, current_repo)
    if row_record:
        effective_repo, payload = row_record
        _ensure_repo_bucket(effective_repo, repos)
        repos[effective_repo].append(payload)

    return current_repo


def parse_inventory_lines(lines):
    repos = {}
    current_repo = None
    for line in lines:
        current_repo = _process_inventory_line(line, current_repo, repos)
    return repos


def _is_pr_stale(updated_at):
    if not updated_at:
        return False
    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - dt).days > 30


def _is_checks_failing(checks):
    # Substring matching is intentional: the inventory file uses markdown-formatted
    # statuses (e.g., "**U**") as well as plain codes, so exact equality would miss them.
    return ("FAIL" in checks) or ("PENDING" in checks) or ("U" in checks)


def _get_pr_category(info, checks):
    if not info.get("files", []):
        return "SUPERSEDED"

    merge_status = info.get("mergeStateStatus", "")
    is_stale = _is_pr_stale(info.get("updatedAt", ""))
    checks_failing = _is_checks_failing(checks)

    if is_stale and checks_failing:
        return "STALE"

    if merge_status in ["DIRTY", "CONFLICTING"]:
        return "CONFLICTING"

    if merge_status == "CLEAN" and not checks_failing:
        return "READY"

    return None


def _categorize_pr(repo, pr_info, triage):
    pr = pr_info["pr"]
    checks = pr_info["checks"]
    print(f"Checking {repo}#{pr}")

    info = run_gh(repo, pr)
    if not info:
        print(f"Failed to fetch {repo}#{pr}")
        return

    category = _get_pr_category(info, checks)
    if category:
        triage[category].append(f"{repo}#{pr}")


def _load_inventory_lines(filepath):
    try:
        with open(filepath, "r") as f:
            return f.readlines()
    except FileNotFoundError:
        return []


def _write_triage_report(filepath, triage):
    with open(filepath, "w") as f:
        f.write("# PR Triage\n\n")
        for category, pr_list in triage.items():
            f.write(f"## {category}\n")
            for pr in pr_list:
                f.write(f"- {pr}\n")


def main():
    lines = _load_inventory_lines("tasks/pr-inventory.md")
    if not lines:
        return

    repos = parse_inventory_lines(lines)
    triage = {"SUPERSEDED": [], "STALE": [], "CONFLICTING": [], "READY": []}

    for repo, prs in repos.items():
        for pr_info in prs:
            _categorize_pr(repo, pr_info, triage)

    _write_triage_report("tasks/pr-triage.md", triage)
    print("Done")


if __name__ == "__main__":
    main()
