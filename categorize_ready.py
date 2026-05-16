import json
import os
import concurrent.futures
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

categorized = {
    "SECURITY": [],
    "DEPENDENCY": [],
    "CI/INFRA": [],
    "PERFORMANCE/REFACTOR/UI/FEATURE": [],
}

def _process_pr(pr):
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
    if not info:
        return None

    # Exclude unstable/dirty
    status = info.get("mergeStateStatus")
    if status in ["DIRTY", "CONFLICTING"]:
        return pr, "SKIP", status

    title = info.get("title", "")
    title_lower = title.lower()
    cat = "PERFORMANCE/REFACTOR/UI/FEATURE"
    if "sentinel" in title_lower or "security" in title_lower or "cve" in title_lower or "xxe" in title_lower:
        cat = "SECURITY"
    elif "dependabot" in title_lower or "renovate" in title_lower:
        cat = "DEPENDENCY"
    elif (
        "chore" in title_lower
        or "ci" in title_lower
        or "automation" in title_lower
        or "action" in title_lower
        or "trunk" in title_lower
    ):
        cat = "CI/INFRA"

    return pr, cat, title

# ⚡ Bolt Optimization: Execute independent network API calls concurrently to avoid N+1 bottleneck
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # Use map to preserve the original PR priority order
    for result in executor.map(_process_pr, ready_prs):
        if not result:
            continue
        pr, cat, title = result
        if cat == "SKIP":
            print(f"Skipping {pr} because it is {title}")
        else:
            categorized[cat].append((pr, title))

for cat, items in categorized.items():
    print(f"\n{cat}:")
    for pr, title in items:
        print(f"  - {pr}: {title}")
