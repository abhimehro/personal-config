import datetime
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

from gh_token_env import load_gh_token_env

repos = [
    "abhimehro/personal-config",
    "abhimehro/ctrld-sync",
    "abhimehro/email-security-pipeline",
    "abhimehro/Seatek_Analysis",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
    "abhimehro/series_correction_project_updated",
]


def run_cmd(cmd):
    env = load_gh_token_env()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
        return res.returncode == 0, res.stdout, res.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout expired"


def _contains_all_keywords(title_lower, lower_kws):
    for kw in lower_kws:
        if kw not in title_lower:
            return False
    return True


def _find_matching_prs(all_prs, repo, title_keywords):
    lower_kws = tuple(kw.lower() for kw in title_keywords)
    matches = []
    for p in all_prs:
        if p["repo"] != repo:
            continue
        title_lower = p.get("title_lower")
        if title_lower is None:
            p["title_lower"] = title_lower = p["title"].lower()

        if _contains_all_keywords(title_lower, lower_kws):
            matches.append(p)
    return matches


def _process_pr_group(matches, repo, rationale, groups):
    if len(matches) > 1:
        matches = sorted(matches, key=lambda x: x["number"], reverse=True)
        groups.append(
            {"repo": repo, "newest": matches[0], "others": matches[1:], "rationale": rationale}
        )
        # Matching titles do not establish duplicate changes or a safe canonical PR.
        for pr in matches:
            pr["status_action"] = "REVIEW"


GROUPING_RULES = [
    # personal-config
    (
        "personal-config",
        ["eval", "cwe-78"],
        "CWE-78 eval title terms",
    ),
    ("personal-config", ["qa & agentic review"], "QA review title terms"),
    (
        "personal-config",
        ["markdown table"],
        "Markdown table title terms",
    ),
    ("personal-config", ["palette", "prompt"], "Palette prompt title terms"),
    # email-security-pipeline
    ("email-security-pipeline", ["empty state"], "Empty state title terms"),
    (
        "email-security-pipeline",
        ["video frame"],
        "Video frame title terms",
    ),
    # series_correction
    (
        "series_correction_project_updated",
        ["itertuples"],
        "itertuples title term",
    ),
    (
        "series_correction_project_updated",
        ["iteration", "performance"],
        "Iteration performance title terms",
    ),
]


def group_prs(all_prs, triage_md):
    # manual grouping logic based on patterns
    groups = []

    for repo, title_keywords, rationale in GROUPING_RULES:
        matches = _find_matching_prs(all_prs, repo, title_keywords)
        _process_pr_group(matches, repo, rationale, groups)

    for g in groups:
        others_str = ", ".join(f"**#{p['number']}**" for p in g["others"])
        triage_md.append(
            f"| {g['repo']} **#{g['newest']['number']}** | {others_str} | {g['rationale']} |"
        )


def _fetch_repo_prs(repo):
    repo_prs = []
    success, stdout, _ = run_cmd(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,author,headRefName,mergeStateStatus,state,createdAt",
        ]
    )
    if success:
        prs = json.loads(stdout)
        for pr in prs:
            # ⚡ Bolt Optimization: Use rpartition() over split() to avoid intermediate list allocation overhead
            pr["repo"] = repo.rpartition("/")[2]
            pr["full_repo"] = repo
            # ⚡ Bolt Optimization: Hoist title lowering out of filtering loops to prevent redundant C-level string allocations
            pr["title_lower"] = pr["title"].lower()
            repo_prs.append(pr)
    return repo_prs


def _process_pr(pr):
    repo = pr["full_repo"]
    num = pr["number"]
    if pr.get("status_action") == "REVIEW":
        print(f"Holding {repo}#{num} (title overlap requires review)")
        return pr, "escalated"
    elif pr["mergeStateStatus"] == "CLEAN" or pr["mergeStateStatus"] == "HAS_HOOKS":
        print(f"Merging {repo}#{num}")
        success, out, err = run_cmd(
            [
                "gh",
                "pr",
                "merge",
                str(num),
                "--repo",
                repo,
                "--squash",
                "--admin",
            ]
        )
        if success:
            return pr, "merged"
        else:
            print(f"Failed to merge: {err}")
            return pr, "escalated"
    else:
        print(f"Holding {repo}#{num} ({pr['mergeStateStatus']})")
        return pr, "escalated"


if __name__ == "__main__":
    all_prs = []
    # ⚡ Bolt Optimization: Parallelize N+1 read-only API calls using map() to significantly speed up PR fetching
    # ⚡ Bolt Optimization: Dynamic thread concurrency to eliminate batching latency
    with ThreadPoolExecutor(max_workers=min(len(repos) or 1, 32)) as executor:
        for repo_prs in executor.map(_fetch_repo_prs, repos):
            all_prs.extend(repo_prs)

    merged = []
    escalated = []

    # ⚡ Bolt Optimization: Hoisted datetime.date.today().isoformat() out of formatting blocks to avoid redundant parsing overhead
    today_iso = datetime.date.today().isoformat()

    triage_md = [
        f"# PR triage — backlog cleanup test ({today_iso})\n",
        "**Policy:** squash merge, stale_days 30, auto-fix enabled, mode review-and-merge. **No force-push.**\n",
        "## Possible overlap by title (review changes before action)\n",
        "| Newest match | Other matches | Shared title terms |",
        "| --- | --- | --- |",
    ]

    group_prs(all_prs, triage_md)

    # Process Actions
    # ⚡ Bolt Optimization: Dynamic thread concurrency to eliminate batching latency
    with ThreadPoolExecutor(max_workers=min(len(all_prs) or 1, 32)) as executor:
        for pr, action in executor.map(
            _process_pr, sorted(all_prs, key=lambda x: (x["repo"], -x["number"]))
        ):
            if action == "merged":
                merged.append(pr)
            elif action == "escalated":
                escalated.append(pr)

    triage_md.extend(
        [
            "\n## Escalate / defer (no autonomous merge)\n",
            "| PR | Reason |",
            "| --- | --- |",
        ]
    )
    for p in escalated:
        reason = (
            "Title overlap requires change review"
            if p.get("status_action") == "REVIEW"
            else f"{p['mergeStateStatus']} status - requires human review or CI fix"
        )
        triage_md.append(
            f"| {p['repo']} **#{p['number']}** | {reason} |"
        )

    triage_md.extend(
        [
            "\n## Outcomes\n",
            f"- **Executed:** {len(merged)} squash merges.",
            f"- **Deferred:** {len(escalated)} held.",
        ]
    )

    with open("tasks/pr-triage.md", "w") as f:
        f.write("\n".join(triage_md) + "\n")

    # Session Report
    report_md = [
        f"\n## Run — {today_iso} (backlog cleanup E2E, review-and-merge)\n",
        "### Repos processed\n",
    ]
    for i, r in enumerate(repos, 1):
        report_md.append(f"{i}. `{r}`")

    report_md.extend(
        [
            "\n### Metrics\n",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| PRs inventoried (open) | {len(all_prs)} |",
            f"| PRs merged (squash) | {len(merged)} |",
            f"| PRs escalated / held | {len(escalated)} |\n",
            "### Merged (squash)\n",
        ]
    )

    current_repo = None
    for p in merged:
        if p["repo"] != current_repo:
            report_md.append(f"\n**{p['repo']}**\n")
            current_repo = p["repo"]
        report_md.append(f"- https://github.com/{p['full_repo']}/pull/{p['number']}")

    report_md.append("\n### Held open / escalated\n")
    for p in escalated:
        reason = (
            "title overlap requires change review"
            if p.get("status_action") == "REVIEW"
            else p["mergeStateStatus"]
        )
        report_md.append(
            f"- https://github.com/{p['full_repo']}/pull/{p['number']} — {reason}"
        )

    with open("tasks/review-session-reports.md", "a") as f:
        f.write("\n".join(report_md) + "\n")

    print(
        f"Done. Merged: {len(merged)}, Escalated: {len(escalated)}"
    )
