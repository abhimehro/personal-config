import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from gh_token_env import load_gh_token_env, run_gh
from pr_reference import PRReference


# ⚡ Bolt Optimization: Module-level tuple constant avoids re-instantiating list objects on every loop iteration
_UNMERGEABLE_STATUSES = ("DIRTY", "CONFLICTING")

ready_prs = [
    "abhimehro/personal-config#744",
    "abhimehro/personal-config#743",
    "abhimehro/personal-config#741",
    "abhimehro/personal-config#740",
    "abhimehro/personal-config#738",
    "abhimehro/personal-config#733",
    "abhimehro/personal-config#732",
    "abhimehro/personal-config#730",  # Note: 730 is unstable, check later
    "abhimehro/personal-config#724",
    "abhimehro/ctrld-sync#707",
    "abhimehro/ctrld-sync#706",
    "abhimehro/ctrld-sync#703",
    "abhimehro/ctrld-sync#702",
    "abhimehro/ctrld-sync#700",
    "abhimehro/ctrld-sync#697",
    "abhimehro/email-security-pipeline#642",
    "abhimehro/email-security-pipeline#640",
    "abhimehro/email-security-pipeline#639",
    "abhimehro/email-security-pipeline#632",
    "abhimehro/email-security-pipeline#630",
    "abhimehro/Seatek_Analysis#127",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#108",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#107",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#104",
    "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#102",
]


_CATEGORIES = (
    ("SECURITY", ("sentinel", "security", "cve", "xxe")),
    ("DEPENDENCY", ("dependabot", "renovate")),
    ("CI/INFRA", ("chore", "ci", "automation", "action", "trunk")),
)


def get_category_from_title(title: str) -> str:
    title = title.lower()
    for cat_name, keywords in _CATEGORIES:
        for kw in keywords:
            if kw in title:
                return cat_name
    return "PERFORMANCE/REFACTOR/UI/FEATURE"


categorized = {
    "SECURITY": [],
    "DEPENDENCY": [],
    "CI/INFRA": [],
    "PERFORMANCE/REFACTOR/UI/FEATURE": [],
}


def fetch_pr_info(pr):
    ref = PRReference.from_string(pr)
    info = run_gh(
        [
            "gh",
            "pr",
            "view",
            str(ref.number),
            "-R",
            ref.repo,
            "--json",
            "title,mergeStateStatus",
        ]
    )
    return pr, info


with ThreadPoolExecutor(max_workers=min(len(ready_prs) or 1, 32)) as executor:
    results = executor.map(fetch_pr_info, ready_prs)

for pr, info in results:
    if not info:
        continue

    # ⚡ Bolt Optimization: Store mergeStateStatus in a local variable to avoid redundant dict lookups and list allocations per iteration
    status = info.get("mergeStateStatus")
    if status in _UNMERGEABLE_STATUSES:
        print(f"Skipping {pr} because it is {status}")
        continue

    title = info.get("title", "")
    cat = get_category_from_title(title)

    categorized[cat].append((pr, title))

for cat, items in categorized.items():
    print(f"\n{cat}:")
    for pr, title in items:
        print(f"  - {pr}: {title}")
