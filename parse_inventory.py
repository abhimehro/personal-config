import re
from datetime import datetime, timezone

from gh_utils import run_gh as _run_gh


def run_gh(repo, pr):
    return _run_gh(
        ["gh", "pr", "view", str(pr), "-R", str(repo), "--json", "files,updatedAt,mergeStateStatus"]
    )

lines = open('tasks/pr-inventory.md').readlines()
repos = {}
current_repo = None

# Repo -> [ (pr_id, author, merge, checks, hints), ... ]
for line in lines:
    m = re.match(r'^## (.*)', line)
    if m:
        current_repo = m.group(1).strip()
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
