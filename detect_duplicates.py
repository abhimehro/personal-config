import re
import json
import subprocess
import os
from collections import defaultdict

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
        with open("../email-security-pipeline/GH_TOKEN.env", "r") as f:
            for line in f:
                _parse_env_line(line, env)
    except FileNotFoundError:
        pass
    return env

def run_gh(args):
    env = _load_gh_token_env()
    env["GH_PAGER"] = "cat"
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

def get_ready_prs(lines):
    ready_prs = []
    for line in lines:
        if line.startswith('- abhimehro/'):
            ready_prs.append(line.strip()[2:])
    return ready_prs

def group_prs_by_files(ready_only):
    file_groups = defaultdict(list)
    for pr in ready_only:
        repo, pr_id = pr.split('#')
        info = run_gh(["pr", "view", pr_id, "-R", repo, "--json", "files,title,number"])
        if not info:
            continue
        files = tuple(sorted([f['path'] for f in info.get('files', [])]))
        file_groups[(repo, files)].append(info)
    return file_groups

def find_duplicates(file_groups):
    duplicates = []
    for (repo, files), pr_list in file_groups.items():
        if len(pr_list) > 1:
            # sort by number descending
            pr_list.sort(key=lambda x: x['number'], reverse=True)
            # keep the newest, close the rest
            for pr_info in pr_list[1:]:
                duplicates.append(f"{repo}#{pr_info['number']}")
    return duplicates

def _write_superseded(f, ready_prs, lines):
    f.write("## SUPERSEDED\n")
    try:
        sup_idx = lines.index('## SUPERSEDED\n')
        stale_idx = lines.index('## STALE\n')
        for pr in ready_prs:
            if pr in lines[sup_idx+1:stale_idx]:
                if not pr.startswith('-'): pr = "- " + pr
                f.write(f"{pr}\n")
    except ValueError:
        pass

def _write_ready(f, ready_only, duplicates):
    f.write("## READY\n")
    for pr in ready_only:
        if pr not in duplicates:
            f.write(f"- {pr}\n")

def write_triage_report(ready_prs, ready_only, duplicates, lines):
    with open('tasks/pr-triage.md', 'w') as f:
        f.write("# PR Triage\n\n")
        _write_superseded(f, ready_prs, lines)
        f.write("## STALE\n")
        f.write("## CONFLICTING\n")
        f.write("- abhimehro/personal-config#725\n")
        f.write("## DUPLICATE\n")
        for d in duplicates:
            f.write(f"- {d}\n")
        _write_ready(f, ready_only, duplicates)

def main():
    try:
        with open('tasks/pr-triage.md') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return

    ready_prs = get_ready_prs(lines)

    try:
        ready_start_idx = lines.index('## READY\n')
        ready_only = [pr for pr in ready_prs if not any(pr in l for l in lines[:ready_start_idx])]
    except ValueError:
        ready_only = []

    file_groups = group_prs_by_files(ready_only)
    duplicates = find_duplicates(file_groups)

    print("Duplicates:", duplicates)
    write_triage_report(ready_prs, ready_only, duplicates, lines)
    print("Done")

if __name__ == "__main__":
    main()
