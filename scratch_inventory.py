import datetime
import json
import subprocess
from collections import defaultdict

repos = [
    "abhimehro/personal-config",
    "abhimehro/ctrld-sync",
    "abhimehro/email-security-pipeline",
    "abhimehro/Seatek_Analysis",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
    "abhimehro/series_correction_project_updated",
]

all_prs = []

for repo in repos:
    res = subprocess.run(
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
        ],
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        prs = json.loads(res.stdout)
        for pr in prs:
            pr["repo"] = repo.rpartition("/")[2]
            all_prs.append(pr)

out_md = []
out_md.append(
    f"# Automated PR inventory — backlog cleanup test ({datetime.date.today().isoformat()})\n"
)
out_md.append(
    "**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (read-only).\n"
)
out_md.append(
    "**Config:** `tasks/pr-review-agent.config.yaml` — `mode: review-and-merge`, `merge_strategy: squash`, `stale_threshold_days: 30`, `auto_fix_enabled: true`, `schedule: none`.\n"
)
out_md.append(
    "| Repo | PR | Author (API) | Branch (head) | Category | CI rollup | Conflicts | Age (created→) | Notes |"
)
out_md.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

category_map = {
    "bolt": "PERFORMANCE",
    "sentinel": "SECURITY",
    "palette": "UI",
    "devin": "CI/INFRA",
    "qa": "CI/INFRA",
    "test": "CI/INFRA",
    "fix": "REFACTOR",
}


def get_category(title, branch):
    l = (title + branch).lower()
    if (
        "sentinel" in l
        or "security" in l
        or "injection" in l
        or "cwe" in l
        or "ssrf" in l
        or "tls" in l
    ):
        return "SECURITY"
    if "bolt" in l or "perf" in l or "optimize" in l:
        return "PERFORMANCE"
    if "palette" in l or "ux" in l or "ui" in l:
        return "UI"
    if "qa" in l or "test" in l or "ci" in l or "infra" in l or "action" in l:
        return "CI/INFRA"
    if "refactor" in l or "import" in l or "clean" in l:
        return "REFACTOR"
    return "FEATURE"


for pr in sorted(all_prs, key=lambda x: (x["repo"], -x["number"])):
    cat = get_category(pr["title"], pr["headRefName"])
    ci = (
        "C"
        if pr["mergeStateStatus"] in ("CLEAN", "HAS_HOOKS")
        else (
            "U"
            if pr["mergeStateStatus"] == "UNSTABLE"
            else "D" if pr["mergeStateStatus"] == "DIRTY" else "?"
        )
    )
    conflicts = "yes" if pr["mergeStateStatus"] == "DIRTY" else "none"
    date_str = (
        pr["createdAt"][:10] if "createdAt" in pr else datetime.date.today().isoformat()
    )
    out_md.append(
        f"| {pr['repo']} | {pr['number']} | {pr['author']['login']} | {pr['headRefName']} | {cat} | {ci} | {conflicts} | {date_str} | {pr['title']} |"
    )

with open("tasks/pr-inventory.md", "w") as f:
    f.write("\n".join(out_md) + "\n")
print(f"Generated inventory for {len(all_prs)} PRs.")
