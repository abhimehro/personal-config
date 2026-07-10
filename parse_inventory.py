import json
import re
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
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
    # ⚡ Bolt Optimization: Use partition() over split() to avoid intermediate list allocation overhead
    key, sep, val = line.partition("=")
    if not sep:
        return
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
    # ⚡ Bolt Optimization: Use fast index checking to avoid function overhead for lines not starting with |,
    # and use a tuple with .startswith() to collapse sequential checks and avoid redundant allocations
    if not line or line[0] != "|":
        return True
    return line.startswith(("| # |", "| ---"))


_REPO_LINK_PATTERN = re.compile(r'\[(.*?)\]\(.*?\)')

def _parse_repo_name(line):
    if line.startswith("### "):
        match = _REPO_LINK_PATTERN.search(line)
        if match:
            return match.group(1).strip()
        return None
    return line[3:].strip() if line.startswith("## ") else None


def _is_valid_pr_row(pr_id, author, hints):
    if not pr_id.isdigit():
        return False
    return author.endswith("[bot]") or hints


def _extract_pr_row_fields(parts):
    repo_col = parts[1].strip()
    if repo_col:
        return (
            repo_col,
            parts[2].strip(),
            parts[3].strip(),
            parts[6].strip(),
            parts[9].strip(),
        )
    return "", parts[2].strip(), parts[3].strip(), parts[6].strip(), parts[9].strip()


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
    # For the single-letter unstable code, normalize away surrounding markdown/whitespace
    # so we do not treat unrelated statuses containing "U" (e.g. "SUCCESS") as failing.
    if ("FAIL" in checks) or ("PENDING" in checks):
        return True
    return checks.strip(" *_") == "U"


def _get_pr_category(info, checks):
    if not info.get("files", []):
        return "SUPERSEDED"

    merge_status = info.get("mergeStateStatus", "")
    # ⚡ Bolt Optimization: Delay expensive datetime parsing by short-circuiting behind checks_failing
    checks_failing = _is_checks_failing(checks)

    if checks_failing and _is_pr_stale(info.get("updatedAt", "")):
        return "STALE"

    if merge_status in ["DIRTY", "CONFLICTING"]:
        return "CONFLICTING"

    if merge_status == "CLEAN" and not checks_failing:
        return "READY"

    return None


def _categorize_pr_task(args):
    repo, pr_info = args
    pr = pr_info["pr"]
    checks = pr_info["checks"]
    print(f"Checking {repo}#{pr}")

    info = run_gh(repo, pr)
    if not info:
        print(f"Failed to fetch {repo}#{pr}")
        return None

    category = _get_pr_category(info, checks)
    if category:
        return category, f"{repo}#{pr}"
    return None


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

    # ⚡ Bolt Optimization: Parallelize N+1 read-only API calls using map() to significantly speed up categorization
    tasks = [(repo, pr_info) for repo, prs in repos.items() for pr_info in prs]

    with ThreadPoolExecutor(max_workers=10) as executor:
        for result in executor.map(_categorize_pr_task, tasks):
            if result:
                category, pr_str = result
                triage[category].append(pr_str)

    _write_triage_report("tasks/pr-triage.md", triage)
    print("Done")


if __name__ == "__main__":
    main()
