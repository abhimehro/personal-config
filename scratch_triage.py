import datetime
import json
import subprocess

REPOS = [
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


class PRManager:
    def __init__(self):
        self.all_prs = []
        self.groups = []
        self.merged = []
        self.closed = []
        self.escalated = []

    def load_all_prs(self):
        for repo in REPOS:
            self.all_prs.extend(self._fetch_prs(repo))

    def _fetch_prs(self, repo):
        success, stdout, _ = run_cmd([
            "gh", "pr", "list", "--repo", repo, "--state", "open",
            "--limit", "100", "--json",
            "number,title,author,headRefName,mergeStateStatus,state,createdAt"
        ])
        if not success:
            return []

        prs = json.loads(stdout)
        for pr in prs:
            pr["repo"] = repo.rpartition("/")[2]
            pr["full_repo"] = repo
        return prs

    def group_duplicates(self):
        self._find_and_group("personal-config", ["eval", "cwe-78"], "Same CWE-78 eval injection theme; keep newest")
        self._find_and_group("personal-config", ["qa & agentic review"], "Duplicate QA reviews; keep newest")
        self._find_and_group("personal-config", ["markdown table"], "Bolt perf optimizations for markdown tables; keep newest")
        self._find_and_group("personal-config", ["palette", "prompt"], "Palette UX prompts; keep newest")

        self._find_and_group("email-security-pipeline", ["empty state"], "Palette empty states; keep newest")
        self._find_and_group("email-security-pipeline", ["video frame"], "Bolt video frame performance; keep newest")

        self._find_and_group("series_correction_project_updated", ["itertuples"], "Bolt dataframe iteration perf; keep newest")
        self._find_and_group("series_correction_project_updated", ["iteration", "performance"], "Iteration optimizations; handled by above/keep newest")

    def _find_and_group(self, repo, title_keywords, rationale):
        matches = [
            p for p in self.all_prs
            if p["repo"] == repo and all(kw.lower() in p["title"].lower() for kw in title_keywords)
        ]
        if len(matches) > 1:
            matches.sort(key=lambda x: x["number"], reverse=True)
            keep = matches[0]
            dups = matches[1:]
            self.groups.append({"repo": repo, "keep": keep, "dups": dups, "rationale": rationale})
            for d in dups:
                d["status_action"] = "CLOSE"
            keep["status_action"] = "KEEP"

    def process_all_prs(self):
        self.all_prs.sort(key=lambda x: (x["repo"], -x["number"]))
        for pr in self.all_prs:
            action = self._process_pr(pr)
            if action == "closed":
                self.closed.append(pr)
            elif action == "merged":
                self.merged.append(pr)
            else:
                self.escalated.append(pr)

    def _process_pr(self, pr):
        repo = pr["full_repo"]
        num = pr["number"]

        if pr.get("status_action") == "CLOSE":
            print(f"Closing {repo}#{num} (duplicate)")
            run_cmd(["gh", "pr", "close", str(num), "--repo", repo, "--comment", "Closing as superseded/duplicate of newer PR."])
            return "closed"

        if pr["mergeStateStatus"] in ("CLEAN", "HAS_HOOKS"):
            print(f"Merging {repo}#{num}")
            success, _, err = run_cmd(["gh", "pr", "merge", str(num), "--repo", repo, "--squash", "--admin"])
            if success:
                return "merged"
            print(f"Failed to merge: {err}")
            return "escalated"

        print(f"Holding {repo}#{num} ({pr['mergeStateStatus']})")
        return "escalated"


def write_triage_report(manager: PRManager):
    lines = [
        f"# PR triage — backlog cleanup test ({datetime.date.today().isoformat()})\n",
        "**Policy:** squash merge, stale_days 30, auto-fix enabled, mode review-and-merge. **No force-push.**\n",
        "## Duplicate / supersede groups\n",
        "| Keep (canonical) | Close as duplicate / superseded | Rationale |",
        "| --- | --- | --- |",
    ]
    for g in manager.groups:
        dups_str = ", ".join([f"**#{d['number']}**" for d in g["dups"]])
        lines.append(f"| {g['repo']} **#{g['keep']['number']}** | {dups_str} | {g['rationale']} |")

    lines.extend([
        "\n## Escalate / defer (no autonomous merge)\n",
        "| PR | Reason |",
        "| --- | --- |",
    ])
    for p in manager.escalated:
        lines.append(f"| {p['repo']} **#{p['number']}** | {p['mergeStateStatus']} status - requires human review or CI fix |")

    lines.extend([
        "\n## Outcomes\n",
        f"- **Executed:** {len(manager.closed)} duplicate closures, {len(manager.merged)} squash merges.",
        f"- **Deferred:** {len(manager.escalated)} held.",
    ])
    with open("tasks/pr-triage.md", "w") as f:
        f.write("\n".join(lines) + "\n")


def write_session_report(manager: PRManager):
    lines = [
        f"\n## Run — {datetime.date.today().isoformat()} (backlog cleanup E2E, review-and-merge)\n",
        "### Repos processed\n",
    ]
    for i, r in enumerate(REPOS, 1):
        lines.append(f"{i}. `{r}`")

    lines.extend([
        "\n### Metrics\n",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| PRs inventoried (open) | {len(manager.all_prs)} |",
        f"| PRs merged (squash) | {len(manager.merged)} |",
        f"| PRs closed (duplicate) | {len(manager.closed)} |",
        f"| PRs escalated / held | {len(manager.escalated)} |\n",
        "### Merged (squash)\n",
    ])

    current_repo = None
    for p in manager.merged:
        if p["repo"] != current_repo:
            lines.append(f"\n**{p['repo']}**\n")
            current_repo = p["repo"]
        lines.append(f"- https://github.com/{p['full_repo']}/pull/{p['number']}")

    lines.append("\n### Closed (duplicate / superseded / zero-diff)\n")
    for p in manager.closed:
        lines.append(f"- https://github.com/{p['full_repo']}/pull/{p['number']}")

    lines.append("\n### Held open / escalated\n")
    for p in manager.escalated:
        lines.append(f"- https://github.com/{p['full_repo']}/pull/{p['number']} — {p['mergeStateStatus']}")

    with open("tasks/pr-review-session-reports.md", "a") as f:
        f.write("\n".join(lines) + "\n")


def main():
    mgr = PRManager()
    mgr.load_all_prs()
    mgr.group_duplicates()
    mgr.process_all_prs()

    write_triage_report(mgr)
    write_session_report(mgr)

    print(f"Done. Merged: {len(mgr.merged)}, Closed: {len(mgr.closed)}, Escalated: {len(mgr.escalated)}")

if __name__ == "__main__":
    main()
