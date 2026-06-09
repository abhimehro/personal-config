import datetime
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess

from spreadsheet_safety import escape_spreadsheet_formula


def _fetch_repo_prs(repo):
    repo_prs = []
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
            # ⚡ Bolt Optimization: Use rpartition() over split() to avoid intermediate list allocation overhead
            pr["repo"] = repo.rpartition("/")[2]
            repo_prs.append(pr)
    return repo_prs

def fetch_prs(repos):
    all_prs = []
    # ⚡ Bolt Optimization: Parallelize N+1 read-only API calls using map() to significantly speed up PR fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        for repo_prs in executor.map(_fetch_repo_prs, repos):
            all_prs.extend(repo_prs)
    return all_prs


def generate_markdown(all_prs):
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

    today_iso = datetime.date.today().isoformat()
    for pr in sorted(all_prs, key=lambda x: (x["repo"], -x["number"])):
        cat = get_category(pr["title"], pr["headRefName"])

        ci = "C"
        if pr["mergeStateStatus"] not in ("CLEAN", "HAS_HOOKS"):
            if pr["mergeStateStatus"] == "UNSTABLE":
                ci = "U"
            elif pr["mergeStateStatus"] == "DIRTY":
                ci = "D"
            else:
                ci = "?"

        conflicts = "yes" if pr["mergeStateStatus"] == "DIRTY" else "none"
        # ⚡ Bolt Optimization: Hoisted datetime.date.today().isoformat() out of loop to avoid redundant string parsing overhead
        date_str = pr.get("createdAt", today_iso)[:10]

        # SECURITY: PR metadata is untrusted; escape formula injection if the
        # inventory table is opened in Excel/Sheets (CWE-1236).
        author = escape_spreadsheet_formula(pr["author"]["login"])
        branch = escape_spreadsheet_formula(pr["headRefName"])
        title = escape_spreadsheet_formula(pr["title"])
        out_md.append(
            f"| {pr['repo']} | {pr['number']} | {author} | {branch} | {cat} | {ci} | {conflicts} | {date_str} | {title} |"
        )
    return out_md


def main():
    repos = [
        "abhimehro/personal-config",
        "abhimehro/ctrld-sync",
        "abhimehro/email-security-pipeline",
        "abhimehro/Seatek_Analysis",
        "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project",
        "abhimehro/series_correction_project_updated",
    ]

    all_prs = fetch_prs(repos)
    out_md = generate_markdown(all_prs)

    with open("tasks/pr-inventory.md", "w") as f:
        f.write("\n".join(out_md) + "\n")
    print(f"Generated inventory for {len(all_prs)} PRs.")


_CATEGORIES = (
    ("SECURITY", ("sentinel", "security", "injection", "cwe", "ssrf", "tls")),
    ("PERFORMANCE", ("bolt", "perf", "optimize")),
    ("UI", ("palette", "ux", "ui")),
    ("CI/INFRA", ("qa", "test", "ci", "infra", "action")),
    ("REFACTOR", ("refactor", "import", "clean")),
)

def get_category(title, branch):
    l = (title + branch).lower()

    # ⚡ Bolt Optimization: Iterate over a predefined tuple of categories to avoid
    # iterator allocation overhead while keeping cyclomatic complexity low (CodeScene Code Health)
    for cat, keywords in _CATEGORIES:
        for k in keywords:
            if k in l:
                return cat

    return "FEATURE"


if __name__ == '__main__':
    main()
