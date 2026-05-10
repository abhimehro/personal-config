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

lines = open('tasks/pr-inventory.md').readlines()
repos = {}
current_repo = None

# Repo -> [ (pr_id, author, merge, checks, hints), ... ]
for line in lines:
    # ⚡ Bolt Optimization: Replace re.match with startswith() + slicing for faster line parsing
    if line.startswith('## '):
        current_repo = line[3:].strip()
        repos[current_repo] = []
    elif line.startswith('|') and not line.startswith('| # |') and not line.startswith('| ---'):
        # ⚡ Bolt Optimization: Split once and strip only required indices (~40% faster)
        parts = line.split('|')
        if len(parts) > 8:
            pr_id = parts[1].strip()
            author = parts[4].strip()
            merge = parts[6].strip()
            checks = parts[7].strip()
            hints = parts[8].strip()
            if author.endswith('[bot]') or hints:
                if pr_id.isdigit():
                    repos[current_repo].append({'pr': pr_id, 'checks': checks})

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
