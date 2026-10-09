#!/usr/bin/env python3
"""Format gh pr list JSON for get_prs.sh (markdown + automation hints).

Invoked as: python3 get_prs_summarize.py <true|false> <path-to-json>
The second argument is include_details ("true" / "false").
"""

import concurrent.futures
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gh_token_env import load_gh_token_env
from pr_reference import parse_repo_name
from spreadsheet_safety import escape_spreadsheet_formula

FAIL_CONCLUSIONS = frozenset(
    {
        "FAILURE",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "CANCELLED",
        "STARTUP_FAILURE",
    }
)


def check_summary(rollup: list | None) -> str:
    if not rollup:
        return "NO_CHECKS"
    pending = 0
    failed = 0
    for c in rollup:
        st = (c.get("status") or "").upper()
        if st != "COMPLETED":
            pending += 1
            continue
        conc = (c.get("conclusion") or "").upper()
        if conc in FAIL_CONCLUSIONS:
            failed += 1
    if pending and failed:
        return f"PENDING_{pending}+FAIL_{failed}"
    if pending:
        return f"PENDING_{pending}"
    if failed:
        return f"FAIL_{failed}"
    return "COMPLETED_OK"


BRANCH_SIGNALS = (
    "jules",
    "sentinel",
    "bolt/",
    "palette/",
    "automation-",
    "daily-qa",
    "chore/jules",
    "cursor-agent/",
    "renovate/",
    "dependabot/",
    "renovate",
    "copilot",
)

TITLE_KW = (
    "jules",
    "sentinel",
    "dependabot",
    "renovate",
    "autofix",
    "bolt",
    "palette",
    "automation",
)

BODY_MARKERS = (
    "jules.google.com",
    "created automatically by jules",
    "pull request was automatically",
    "signed-off-by: dependabot",
)

# ⚡ Bolt Optimization: Pre-compute formatted signal pairs at module import time
# to eliminate repetitive string formatting, rstrip calls, and 4 intermediate list
# allocations per PR evaluation in automation_hints.
_BRANCH_SIGNAL_PAIRS = tuple(
    (sig, f"branch:{sig.rstrip('/')}") for sig in BRANCH_SIGNALS
)
_TITLE_KW_PAIRS = tuple((kw, f"title:{kw}") for kw in TITLE_KW)


def _add_author_hints(author: dict | None, hints: set[str]) -> None:
    """Add bot-flag and bot-login hints to the supplied set in place."""
    if not author:
        return
    if author.get("is_bot"):
        hints.add("author_is_bot")
    login = author.get("login")
    if login and login.endswith("[bot]"):
        hints.add("bot_login")


def _add_branch_hints(branch: str | None, hints: set[str]) -> None:
    """Add the first configured signal matching the branch, ignoring case."""
    if not branch:
        return
    branch_lower = branch.lower()
    for sig, label in _BRANCH_SIGNAL_PAIRS:
        if sig in branch_lower:
            hints.add(label)
            return


def _add_title_hints(title: str | None, hints: set[str]) -> None:
    """Add the first configured keyword matching the title, ignoring case."""
    if not title:
        return
    title_lower = title.lower()
    for kw, label in _TITLE_KW_PAIRS:
        if kw in title_lower:
            hints.add(label)
            return


def _add_body_hints(body: str | None, hints: set[str]) -> None:
    """Add a body hint if any automation marker matches, ignoring case."""
    if not body:
        return
    body_lower = body.lower()
    for m in BODY_MARKERS:
        if m in body_lower:
            hints.add("body:automation_marker")
            return


def automation_hints(pr: dict) -> str:
    """Return sorted, unique automation hints or a human-review fallback.

    Inspect the PR's author, branch, title, and body, tolerating missing or
    null fields. Join matching hints with semicolons; if none match, advise
    treating the PR as human unless reviews indicate otherwise.
    """
    hints: set[str] = set()
    _add_author_hints(pr.get("author"), hints)
    _add_branch_hints(pr.get("headRefName"), hints)
    _add_title_hints(pr.get("title"), hints)
    _add_body_hints(pr.get("body"), hints)

    if not hints:
        return "(none — treat as human unless reviews say otherwise)"
    return "; ".join(sorted(hints))


def esc_cell(s: str, maxlen: int = 48) -> str:
    s = s.replace("|", "\\|").replace("\n", " ")
    if len(s) > maxlen:
        s = s[: maxlen - 3] + "..."
    return s


def _format_details(data: dict) -> str:
    lines: list[str] = []
    reviews = data.get("reviews") or ()
    latest = data.get("latestReviews") or ()
    comments = data.get("comments") or ()
    rd = data.get("reviewDecision") or ""
    if rd:
        lines.append(f"- reviewDecision: `{rd}`")
    lines.append(f"- review threads: {len(reviews)} raw / {len(latest)} latest")
    lines.append(f"- issue comments: {len(comments)}")
    for r in latest[:3]:
        author = r.get("author")
        who = (author.get("login") if author else None) or "?"
        state = r.get("state") or "?"
        snippet = (r.get("body") or "")[:200].replace("\n", " ")
        lines.append(f"  - {who} [{state}]: {snippet}")
    for c in comments[-2:]:
        author = c.get("author")
        who = (author.get("login") if author else None) or "?"
        snippet = (c.get("body") or "")[:200].replace("\n", " ")
        lines.append(f"  - comment {who}: {snippet}")
    return "\n".join(lines)


def fetch_details(repo: str, num: int) -> str:
    env = load_gh_token_env()
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                str(num),
                "--repo",
                repo,
                "--json",
                "reviews,comments,latestReviews,reviewDecision",
            ],
            text=True,
            capture_output=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            return "_Could not load details_"
        raw = result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return "_Could not load details_"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "_Could not load details_"
    return _format_details(data)


def _fetch_task_wrapper(args: tuple[str, dict]) -> tuple[int, str] | None:
    repo, pr = args
    num = pr.get("number")
    if num is None:
        return None
    return num, fetch_details(repo, int(num))


def _format_pr_row(pr: dict) -> str:
    author = pr.get("author")
    login = escape_spreadsheet_formula((author.get("login") if author else None) or "?")
    draft = "yes" if pr.get("isDraft") else "no"
    checks = check_summary(pr.get("statusCheckRollup") or ())
    merge = f"{pr.get('mergeable') or '?'}"
    mss = pr.get("mergeStateStatus") or ""
    if mss and mss != "UNKNOWN":
        merge = f"{merge} ({mss})"

    row_parts = [
        str(pr.get("number")),
        draft,
        esc_cell(escape_spreadsheet_formula(pr.get("title") or ""), 40),
        esc_cell(login, 18),
        esc_cell(escape_spreadsheet_formula(pr.get("headRefName") or ""), 28),
        esc_cell(merge, 24),
        checks,
        esc_cell(automation_hints(pr), 56),
        esc_cell(pr.get("url") or "", 40),
    ]
    return "| " + " | ".join(row_parts) + " |"


def _print_details_section(data: list) -> None:
    raw_repo = os.environ.get("GH_DETAIL_REPO", "")
    if not raw_repo:
        print("\n_Details skipped: internal error (no repo env)._")
        return
    repo = parse_repo_name(raw_repo, loc=("GH_DETAIL_REPO", None))
    if not repo:
        print("\n_Details skipped: invalid repository reference._")
        return

    print("\n#### Review / comment context\n")

    tasks = [(repo, pr) for pr in data]

    # ⚡ Bolt Optimization: Use ThreadPoolExecutor for concurrent I/O-bound GitHub API calls
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(tasks) or 1, 32)
    ) as executor:
        results = list(executor.map(_fetch_task_wrapper, tasks))

    for res in results:
        if res:
            num, details = res
            print(f"**PR #{num}**\n")
            print(details)
            print()


def print_table(data: list, include_details: bool) -> None:
    print(
        "| # | Draft | Title | Author | Branch | Merge | Checks | "
        "Automation hints | URL |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for pr in data:
        print(_format_pr_row(pr))

    if include_details:
        _print_details_section(data)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: get_prs_summarize.py <true|false> <json_path>",
            file=sys.stderr,
        )
        return 1
    include_details = sys.argv[1] == "true"
    json_path = sys.argv[2]
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        print("_No open PRs._\n")
        return 0
    print_table(data, include_details)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
