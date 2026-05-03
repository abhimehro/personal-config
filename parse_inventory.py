import re
from datetime import datetime, timezone
import json
import subprocess
import os
from functools import lru_cache

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

def run_gh(repo, pr):
    env = _load_gh_token_env()
    cmd = ["gh", "pr", "view", str(pr), "-R", str(repo), "--json", "files,updatedAt,mergeStateStatus"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

def parse_inventory_lines(lines):
    repos = {}
    current_repo = None

    # Repo -> [ (pr_id, author, merge, checks, hints), ... ]
    for line in lines:
        m = re.match(r'^## (.*)', line)
        if m:
            current_repo = m.group(1).strip()
            repos[current_repo] = []
        elif line.startswith('|') and not line.startswith('| # |') and not line.startswith('| ---'):
            parts = line.split('|')
            if len(parts) > 9:
                pr_id = parts[2].strip()
                author = parts[5].strip()
                merge = parts[7].strip()
                checks = parts[8].strip()
                hints = parts[9].strip()
                if author.endswith('[bot]') or hints:
                    if pr_id.isdigit():
                        if current_repo is not None:
                            repos[current_repo].append({'pr': pr_id, 'checks': checks})
    return repos

def main():
    try:
        with open('tasks/pr-inventory.md', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    repos = parse_inventory_lines(lines)

    triage = {
        'SUPERSEDED': [],
        'STALE': [],
        'CONFLICTING': [],
        'READY': []
    }

    for repo, prs in repos.items():
        for pr_info in prs:
            pr = pr_info['pr']
            checks = pr_info['checks']
            print(f"Checking {repo}#{pr}")
            info = run_gh(repo, pr)
            if not info:
                print(f"Failed to fetch {repo}#{pr}")
                continue

            files = info.get('files', [])
            updated_at = info.get('updatedAt', '')
            merge_status = info.get('mergeStateStatus', '')
            
            if not files:
                triage['SUPERSEDED'].append(f"{repo}#{pr}")
                continue
            
            days_old = 0
            if updated_at:
                # ⚡ Bolt Optimization: Replace strptime with fromisoformat for ~40x faster date parsing.
                # Replace 'Z' with '+00:00' to support Python < 3.11 parsing of UTC strings
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                days_old = (now - dt).days

            is_stale = days_old > 30
            
            checks_failing = ('FAIL' in checks) or ('PENDING' in checks)

            if is_stale and checks_failing:
                triage['STALE'].append(f"{repo}#{pr}")
                continue

            if merge_status in ['DIRTY', 'CONFLICTING']:
                triage['CONFLICTING'].append(f"{repo}#{pr}")
                continue

            if merge_status == 'CLEAN' and not checks_failing:
                triage['READY'].append(f"{repo}#{pr}")
                continue

    with open('tasks/pr-triage.md', 'w') as f:
        f.write("# PR Triage\n\n")
        for category, pr_list in triage.items():
            f.write(f"## {category}\n")
            for pr in pr_list:
                f.write(f"- {pr}\n")

    print("Done")

if __name__ == '__main__':
    main()
