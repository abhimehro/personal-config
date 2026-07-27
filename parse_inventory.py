import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from gh_token_env import load_gh_token_env
from pr_reference import parse_pr_reference, parse_repo_name


def run_gh(repo, pr):
    """Call ``gh pr view`` and return JSON, or None on failure/timeout."""
    env = load_gh_token_env()
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
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"gh pr view timed out for {repo}#{pr}", file=sys.stderr)
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _should_skip_table_row(line):
    if not line or line[0] != "|":
        return True
    return line.startswith(("| # |", "| ---"))


_REPO_LINK_PATTERN = re.compile(r"\[(.*?)\]\(.*?\)")


def _parse_repo_name(line):
    if line.startswith("### "):
        match = _REPO_LINK_PATTERN.search(line)
        if match:
            return parse_repo_name(
                match.group(1).strip(), source="tasks/pr-inventory.md"
            )
        return None
    if line.startswith("## "):
        return parse_repo_name(line[3:].strip(), source="tasks/pr-inventory.md")
    return None


def _is_valid_pr_row(author, hints):
    return author.endswith("[bot]") or hints


def _extract_pr_row_fields(parts):
    repo_col = parts[1].strip()
    return (
        repo_col,
        parts[2].strip(),
        parts[3].strip(),
        parts[6].strip(),
        parts[9].strip(),
    )


def _ensure_repo_bucket(repo_name, repos):
    if repo_name not in repos:
        repos[repo_name] = []


def _parse_row_record(line, current_repo, line_number):
    parts = line.split("|")
    if len(parts) <= 9:
        return None
    repo_col, pr_id, author, checks, hints = _extract_pr_row_fields(parts)
    if repo_col:
        effective_repo = parse_repo_name(
            repo_col, source="tasks/pr-inventory.md", line=line_number
        )
    else:
        effective_repo = current_repo
    if effective_repo is None:
        return None
    if not _is_valid_pr_row(author, hints):
        return None
    ref = parse_pr_reference(
        effective_repo, pr_id, source="tasks/pr-inventory.md", line=line_number
    )
    if ref is None:
        return None
    return ref.repo, {"pr": str(ref.number), "checks": checks}


def _process_inventory_line(line, current_repo, repos, line_number):
    repo_name = _parse_repo_name(line)
    if repo_name:
        _ensure_repo_bucket(repo_name, repos)
        return repo_name

    if _should_skip_table_row(line):
        return current_repo

    row_record = _parse_row_record(line, current_repo, line_number)
    if row_record:
        effective_repo, payload = row_record
        _ensure_repo_bucket(effective_repo, repos)
        repos[effective_repo].append(payload)

    return current_repo


def parse_inventory_lines(lines, *, source="tasks/pr-inventory.md"):
    repos = {}
    current_repo = None
    for line_number, line in enumerate(lines, start=1):
        current_repo = _process_inventory_line(line, current_repo, repos, line_number)
    return repos


def _is_pr_stale(updated_at, now=None):
    if not updated_at:
        return False
    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    if now is None:
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


def _get_pr_category(info, checks, now=None):
    if not info.get("files", ()):
        return "SUPERSEDED"

    merge_status = info.get("mergeStateStatus", "")
    # Delay expensive datetime parsing by short-circuiting behind checks_failing
    checks_failing = _is_checks_failing(checks)

    if checks_failing and _is_pr_stale(info.get("updatedAt", ""), now):
        return "STALE"

    if merge_status in ["DIRTY", "CONFLICTING"]:
        return "CONFLICTING"

    if merge_status == "CLEAN" and not checks_failing:
        return "READY"

    return None


def _categorize_pr_task(args):
    repo, pr_info, now = args
    pr = pr_info["pr"]
    checks = pr_info["checks"]
    print(f"Checking {repo}#{pr}")

    info = run_gh(repo, pr)
    if not info:
        print(f"Failed to fetch {repo}#{pr}")
        return None

    category = _get_pr_category(info, checks, now)
    if category:
        return category, f"{repo}#{pr}"
    return None


def _load_inventory_lines(filepath):
    try:
        with open(filepath, "r") as f:
            yield from f
    except FileNotFoundError:
        return


def _write_triage_report(filepath, triage):
    with open(filepath, "w") as f:
        f.write("# PR Triage\n\n")
        for category, pr_list in triage.items():
            f.write(f"## {category}\n")
            for pr in pr_list:
                f.write(f"- {pr}\n")


def main():
    lines = _load_inventory_lines("tasks/pr-inventory.md")
    repos = parse_inventory_lines(lines)
    if not repos:
        return
    triage = {"SUPERSEDED": [], "STALE": [], "CONFLICTING": [], "READY": []}

    now = datetime.now(timezone.utc)
    tasks = [(repo, pr_info, now) for repo, prs in repos.items() for pr_info in prs]

    with ThreadPoolExecutor(max_workers=min(len(tasks) or 1, 32)) as executor:
        for result in executor.map(_categorize_pr_task, tasks):
            if result:
                category, pr_str = result
                triage[category].append(pr_str)

    _write_triage_report("tasks/pr-triage.md", triage)
    print("Done")


if __name__ == "__main__":
    main()
