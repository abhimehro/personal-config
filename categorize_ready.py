import concurrent.futures
import json
import os
import subprocess
from functools import lru_cache


def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line:
        return
    if line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    # ⚡ Bolt Optimization: Use partition() over split() to avoid intermediate list allocation overhead
    key, sep, val = line.partition("=")
    if not sep:
        return
    env_dict[key] = val.strip("'\"")


@lru_cache(maxsize=None)
def _get_parsed_env_vars():
    # ⚡ Bolt Optimization: Cache only the parsed variables from the file to prevent redundant IO reads, while keeping it safe from mutable dictionary cache poisoning
    parsed_vars = {}
    try:
        with open("../email-security-pipeline/GH_TOKEN.env", "r") as f:
            for line in f:
                _parse_env_line(line, parsed_vars)
    except FileNotFoundError:
        pass
    return parsed_vars


def _load_gh_token_env():
    env = os.environ.copy()
    env.update(_get_parsed_env_vars())
    return env


def run_gh(cmd_list):
    env = _load_gh_token_env()
    result = subprocess.run(cmd_list, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None


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


def get_category_from_title(title: str) -> str:
    title = title.lower()
    cat = "PERFORMANCE/REFACTOR/UI/FEATURE"
    for sec_kw in ("sentinel", "security", "cve", "xxe"):
        if sec_kw in title:
            return "SECURITY"
    for dep_kw in ("dependabot", "renovate"):
        if dep_kw in title:
            return "DEPENDENCY"
    for ci_kw in ("chore", "ci", "automation", "action", "trunk"):
        if ci_kw in title:
            return "CI/INFRA"
    return cat


categorized = {
    "SECURITY": [],
    "DEPENDENCY": [],
    "CI/INFRA": [],
    "PERFORMANCE/REFACTOR/UI/FEATURE": [],
}


def fetch_pr_info(pr):
    # ⚡ Bolt Optimization: Use partition() over split() to avoid intermediate list allocation overhead
    repo, _, pr_id = pr.partition("#")
    info = run_gh(
        [
            "gh",
            "pr",
            "view",
            str(pr_id),
            "-R",
            str(repo),
            "--json",
            "title,mergeStateStatus",
        ]
    )
    return pr, info


with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # ⚡ Bolt Optimization: Parallelize N+1 read-only API calls while preserving order using map()
    results = executor.map(fetch_pr_info, ready_prs)

for pr, info in results:
    if not info:
        continue

    # Exclude unstable/dirty
    if info.get("mergeStateStatus") in ["DIRTY", "CONFLICTING"]:
        print(f"Skipping {pr} because it is {info.get('mergeStateStatus')}")
        continue

    title = info.get("title", "")
    cat = get_category_from_title(title)

    categorized[cat].append((pr, info.get("title")))

for cat, items in categorized.items():
    print(f"\n{cat}:")
    for pr, title in items:
        print(f"  - {pr}: {title}")
