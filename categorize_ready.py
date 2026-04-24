import subprocess
import json
import os

def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line:
        return
    if line.startswith("#"):
        return
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        return
    key, val = line.split("=", 1)
    env_dict[key] = val.strip("'\"")

def _load_gh_token_env():
    env = os.environ.copy()
    try:
        # Resolve path relative to script location if needed, but here it's fine
        with open("../email-security-pipeline/GH_TOKEN.env", "r") as f:
            for line in f:
                _parse_env_line(line, env)
    except FileNotFoundError:
        pass
    return env

def run_gh(args):
    env = _load_gh_token_env()
    # Ensure GH_PAGER is cat to avoid interactive prompts
    env["GH_PAGER"] = "cat"
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

def _is_security_pr(title):
    keywords = {'sentinel', 'security', 'cve', 'xxe'}
    return any(kw in title for kw in keywords)

def _is_dependency_pr(title):
    keywords = {'dependabot', 'renovate'}
    return any(kw in title for kw in keywords)

def _is_infra_pr(title):
    keywords = {'chore', 'ci', 'automation', 'action', 'trunk'}
    return any(kw in title for kw in keywords)

def get_category(title):
    title = title.lower()
    if _is_security_pr(title):
        return 'SECURITY'
    if _is_dependency_pr(title):
        return 'DEPENDENCY'
    if _is_infra_pr(title):
        return 'CI/INFRA'
    return 'PERFORMANCE/REFACTOR/UI/FEATURE'

def process_pr(pr, categorized):
    repo, pr_id = pr.split('#')
    info = run_gh(["pr", "view", pr_id, "-R", repo, "--json", "title,mergeStateStatus"])
    if not info:
        return

    # Exclude unstable/dirty
    status = info.get('mergeStateStatus')
    if status == 'DIRTY' or status == 'CONFLICTING':
        print(f"Skipping {pr} because it is {status}")
        return

    title = info.get('title', '')
    cat = get_category(title)
    categorized[cat].append((pr, title))

def main():
    ready_prs = [
        "abhimehro/personal-config#744",
        "abhimehro/personal-config#743",
        "abhimehro/personal-config#741",
        "abhimehro/personal-config#740",
        "abhimehro/personal-config#738",
        "abhimehro/personal-config#733",
        "abhimehro/personal-config#732",
        "abhimehro/personal-config#730", # Note: 730 is unstable, check later
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
        'SECURITY': [],
        'DEPENDENCY': [],
        'CI/INFRA': [],
        'PERFORMANCE/REFACTOR/UI/FEATURE': []
    }

    for pr in ready_prs:
        process_pr(pr, categorized)

    for cat, items in categorized.items():
        print(f"\n{cat}:")
        for pr, title in items:
            print(f"  - {pr}: {title}")

if __name__ == "__main__":
    main()
