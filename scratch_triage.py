import concurrent.futures
import datetime
import json
import subprocess

repos = [
    "abhimehro/personal-config",
    "abhimehro/ctrld-sync",
    "abhimehro/email-security-pipeline",
    "abhimehro/Seatek_Analysis",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
    "abhimehro/series_correction_project_updated",
]


def run_cmd(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr


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
        if _contains_all_keywords(p["title"].lower(), lower_kws):
            matches.append(p)
    return matches


def _process_pr_group(matches, repo, rationale, groups):
    if len(matches) > 1:
        matches = sorted(matches, key=lambda x: x["number"], reverse=True)
        keep = matches[0]
        dups = matches[1:]
        groups.append(
            {"repo": repo, "keep": keep, "dups": dups, "rationale": rationale}
        )
        for d in dups:
            d["status_action"] = "CLOSE"
        keep["status_action"] = "KEEP"


def group_prs(all_prs, triage_md):
    # manual grouping logic based on patterns
    groups = []

    def find_and_group(repo, title_keywords, rationale):
        matches = _find_matching_prs(all_prs, repo, title_keywords)
        _process_pr_group(matches, repo, rationale, groups)

    # personal-config
    find_and_group(
        "personal-config",
        ["eval", "cwe-78"],
        "Same CWE-78 eval injection theme; keep newest",
    )
    find_and_group(
        "personal-config", ["qa & agentic review"], "Duplicate QA reviews; keep newest"
    )
    find_and_group(
        "personal-config",
        ["markdown table"],
        "Bolt perf optimizations for markdown tables; keep newest",
    )
    find_and_group(
        "personal-config", ["palette", "prompt"], "Palette UX prompts; keep newest"
    )

    # email-security-pipeline
    find_and_group(
        "email-security-pipeline", ["empty state"], "Palette empty states; keep newest"
    )
    find_and_group(
        "email-security-pipeline",
        ["video frame"],
        "Bolt video frame performance; keep newest",
    )

    # series_correction
    find_and_group(
        "series_correction_project_updated",
        ["itertuples"],
        "Bolt dataframe iteration perf; keep newest",
    )
    find_and_group(
        "series_correction_project_updated",
        ["iteration", "performance"],
        "Iteration optimizations; handled by above/keep newest",
    )

    for g in groups:
        dups_str = ", ".join([f"**#{d['number']}**" for d in g["dups"]])
        triage_md.append(
            f"| {g['repo']} **#{g['keep']['number']}** | {dups_str} | {g['rationale']} |"
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
            repo_prs.append(pr)
    return repo_prs


def _process_pr(pr):
    repo = pr["full_repo"]
    num = pr["number"]
    if pr.get("status_action") == "CLOSE":
        print(f"Closing {repo}#{num} (duplicate)")
        run_cmd(
            [
                "gh",
                "pr",
                "close",
                str(num),
                "--repo",
                repo,
                "--comment",
                "Closing as superseded/duplicate of newer PR.",
            ]
        )
        return pr, "closed"
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for repo_prs in executor.map(_fetch_repo_prs, repos):
            all_prs.extend(repo_prs)

    merged = []
    closed = []
    escalated = []

    triage_md = [
        f"# PR triage — backlog cleanup test ({datetime.date.today().isoformat()})\n",
        "**Policy:** squash merge, stale_days 30, auto-fix enabled, mode review-and-merge. **No force-push.**\n",
        "## Duplicate / supersede groups\n",
        "| Keep (canonical) | Close as duplicate / superseded | Rationale |",
        "| --- | --- | --- |",
    ]

    group_prs(all_prs, triage_md)

    # Process Actions
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for pr, action in executor.map(
            _process_pr, sorted(all_prs, key=lambda x: (x["repo"], -x["number"]))
        ):
            if action == "closed":
                closed.append(pr)
            elif action == "merged":
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
        triage_md.append(
            f"| {p['repo']} **#{p['number']}** | {p['mergeStateStatus']} status - requires human review or CI fix |"
        )

    triage_md.extend(
        [
            "\n## Outcomes\n",
            f"- **Executed:** {len(closed)} duplicate closures, {len(merged)} squash merges.",
            f"- **Deferred:** {len(escalated)} held.",
        ]
    )

    with open("tasks/pr-triage.md", "w") as f:
        f.write("\n".join(triage_md) + "\n")

    # Session Report
    report_md = [
        f"\n## Run — {datetime.date.today().isoformat()} (backlog cleanup E2E, review-and-merge)\n",
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
            f"| PRs closed (duplicate) | {len(closed)} |",
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

    report_md.append("\n### Closed (duplicate / superseded / zero-diff)\n")
    for p in closed:
        report_md.append(f"- https://github.com/{p['full_repo']}/pull/{p['number']}")

    report_md.append("\n### Held open / escalated\n")
    for p in escalated:
        report_md.append(
            f"- https://github.com/{p['full_repo']}/pull/{p['number']} — {p['mergeStateStatus']}"
        )

    with open("tasks/review-session-reports.md", "a") as f:
        f.write("\n".join(report_md) + "\n")

    print(
        f"Done. Merged: {len(merged)}, Closed: {len(closed)}, Escalated: {len(escalated)}"
    )
