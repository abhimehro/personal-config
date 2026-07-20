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


def automation_hints(pr: dict) -> str:
    hints: list[str] = []
    hints.extend(_get_author_hints(pr.get("author")))
    hints.extend(_get_branch_hints(pr.get("headRefName")))
    hints.extend(_get_title_hints(pr.get("title")))
    hints.extend(_get_body_hints(pr.get("body")))

    if not hints:
        return "(none — treat as human unless reviews say otherwise)"
    return "; ".join(sorted(set(hints)))


def _get_author_hints(author: dict | None) -> list[str]:
    hints: list[str] = []
    if not author:
        return hints
    if author.get("is_bot"):
        hints.append("author_is_bot")
    login = author.get("login")
    if login and login.endswith("[bot]"):
        hints.append("bot_login")
    return hints


def _get_branch_hints(branch: str | None) -> list[str]:
    if not branch:
        return []
    branch_lower = branch.lower()
    for sig in BRANCH_SIGNALS:
        if sig in branch_lower:
            return [f"branch:{sig.rstrip('/')}"]
    return []


def _get_title_hints(title: str | None) -> list[str]:
    if not title:
        return []
    title_lower = title.lower()
    for kw in TITLE_KW:
        if kw in title_lower:
            return [f"title:{kw}"]
    return []


def _get_body_hints(body: str | None) -> list[str]:
    if not body:
        return []
    body_lower = body.lower()
    for m in BODY_MARKERS:
        if m in body_lower:
            return ["body:automation_marker"]
    return []


def esc_cell(s: str, maxlen: int = 48) -> str:
    s = s.replace("|", "\\|").replace("\n", " ")
    if len(s) > maxlen:
        s = s[: maxlen - 3] + "..."
    return s


def fetch_details(repo: str, num: int) -> str:
    try:
        raw = subprocess.check_output(
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
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return "_Could not load details_"
    data = json.loads(raw)
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


def _fetch_task_wrapper(args: tuple[str, dict]) -> tuple[int, str] | None:
    repo, pr = args
    num = pr.get("number")
    if num is None:
        return None
    return num, fetch_details(repo, int(num))


def _format_pr_row(pr: dict) -> str:
    author = pr.get("author")
    login = (author.get("login") if author else None) or "?"
    draft = "yes" if pr.get("isDraft") else "no"
    checks = check_summary(pr.get("statusCheckRollup") or ())
    merge = f"{pr.get('mergeable') or '?'}"
    mss = pr.get("mergeStateStatus") or ""
    if mss and mss != "UNKNOWN":
        merge = f"{merge} ({mss})"

    row_parts = [
        str(pr.get("number")),
        draft,
        esc_cell(pr.get("title") or "", 40),
        esc_cell(login, 18),
        esc_cell(pr.get("headRefName") or "", 28),
        esc_cell(merge, 24),
        checks,
        esc_cell(automation_hints(pr), 56),
        esc_cell(pr.get("url") or "", 40),
    ]
    return "| " + " | ".join(row_parts) + " |"


def _print_details_section(data: list) -> None:
    repo = os.environ.get("GH_DETAIL_REPO", "")
    if not repo:
        print("\n_Details skipped: internal error (no repo env)._")
        return

    print("\n#### Review / comment context\n")

    tasks = [(repo, pr) for pr in data]

    # ⚡ Bolt Optimization: Use ThreadPoolExecutor for concurrent I/O-bound GitHub API calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks) or 1, 32)) as executor:
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
