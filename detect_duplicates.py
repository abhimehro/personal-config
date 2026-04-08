import re
import json
import subprocess
from collections import defaultdict

def run_gh(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

lines = open('tasks/pr-triage.md').readlines()
ready_prs = []
for line in lines:
    if line.startswith('- abhimehro/'):
        ready_prs.append(line.strip()[2:])

ready_only = [pr for pr in ready_prs if not any(pr in l for l in lines[:lines.index('## READY\n')])]

file_groups = defaultdict(list)
for pr in ready_only:
    repo, pr_id = pr.split('#')
    info = run_gh(f"source ../email-security-pipeline/GH_TOKEN.env && gh pr view {pr_id} -R {repo} --json files,title,number")
    if not info:
        continue
    files = tuple(sorted([f['path'] for f in info.get('files', [])]))
    file_groups[(repo, files)].append(info)

duplicates = []
for (repo, files), pr_list in file_groups.items():
    if len(pr_list) > 1:
        # sort by number descending
        pr_list.sort(key=lambda x: x['number'], reverse=True)
        # keep the newest, close the rest
        for pr_info in pr_list[1:]:
            duplicates.append(f"{repo}#{pr_info['number']}")

print("Duplicates:", duplicates)

with open('tasks/pr-triage.md', 'w') as f:
    f.write("# PR Triage\n\n")
    f.write("## SUPERSEDED\n")
    for pr in ready_prs:
        if pr in lines[lines.index('## SUPERSEDED\n')+1:lines.index('## STALE\n')]:
            if not pr.startswith('-'): pr = "- " + pr
            f.write(f"{pr}\n")
    f.write("## STALE\n")
    f.write("## CONFLICTING\n")
    f.write("- abhimehro/personal-config#725\n")
    f.write("## DUPLICATE\n")
    for d in duplicates:
        f.write(f"- {d}\n")
    f.write("## READY\n")
    for pr in ready_only:
        if pr not in duplicates:
            f.write(f"- {pr}\n")

print("Done")
