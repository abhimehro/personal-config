import datetime
import json
import subprocess
import asyncio

from gh_token_env import load_gh_token_env

repos = [
    "abhimehro/personal-config",
    "abhimehro/ctrld-sync",
    "abhimehro/email-security-pipeline",
    "abhimehro/Seatek_Analysis",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
    "abhimehro/series_correction_project_updated",
]

_GH_ENV = None
_SEMAPHORE = None

def _get_gh_env():
    global _GH_ENV
    if _GH_ENV is None:
        _GH_ENV = load_gh_token_env()
    return _GH_ENV

def _get_semaphore():
    global _SEMAPHORE
    if _SEMAPHORE is None:
        _SEMAPHORE = asyncio.Semaphore(32)
    return _SEMAPHORE

async def run_cmd(cmd):
    async with _get_semaphore():
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=_get_gh_env()
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return proc.returncode == 0, stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:
            try:
                proc.terminate()
                await proc.wait()
            except ProcessLookupError:
                pass
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


async def _fetch_repo_prs(repo):
    repo_prs = []
    success, stdout, _ = await run_cmd(
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


async def _process_pr(pr):
    repo = pr["full_repo"]
    num = pr["number"]
    if pr.get("status_action") == "CLOSE":
        print(f"Closing {repo}#{num} (duplicate)")
        await run_cmd(
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
        success, out, err = await run_cmd(
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
    today_iso = datetime.date.today().isoformat()

    async def main_async():
        all_prs = []
        fetch_tasks = [_fetch_repo_prs(r) for r in repos]
        results = await asyncio.gather(*fetch_tasks)
        for repo_prs in results:
            all_prs.extend(repo_prs)

        merged = []
        closed = []
        escalated = []

        triage_md = [
            f"# PR triage — backlog cleanup test ({today_iso})\n",
            "**Policy:** squash merge, stale_days 30, auto-fix enabled, mode review-and-merge. **No force-push.**\n",
            "## Duplicate / supersede groups\n",
            "| Keep (canonical) | Close as duplicate / superseded | Rationale |",
            "| --- | --- | --- |",
        ]

        group_prs(all_prs, triage_md)

        process_tasks = [_process_pr(pr) for pr in sorted(all_prs, key=lambda x: (x["repo"], -x["number"]))]
        action_results = await asyncio.gather(*process_tasks)
        for pr, action in action_results:
            if action == "closed":
                closed.append(pr)
            elif action == "merged":
                merged.append(pr)
            elif action == "escalated":
                escalated.append(pr)

        return merged, closed, escalated, triage_md, all_prs

    merged, closed, escalated, triage_md, all_prs = asyncio.run(main_async())

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
