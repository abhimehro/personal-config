import json
import os
import re
import subprocess
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


def run_gh(cmd_list):
    env = _load_gh_token_env()
    result = subprocess.run(cmd_list, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None


lines = open("tasks/pr-triage.md").readlines()
ready_prs = []
for line in lines:
    if line.startswith("- abhimehro/"):
        ready_prs.append(line.strip()[2:])

# ⚡ Bolt Optimization: Replace any() in loop with single substring check against joined string
pre_joined_string = "".join(lines[: lines.index("## READY\n")])
ready_only = [
    pr
    for pr in ready_prs
    if pr not in pre_joined_string
]

file_groups = defaultdict(list)
for pr in ready_only:
    repo, pr_id = pr.split("#")
    info = run_gh(
        [
            "gh",
            "pr",
            "view",
            str(pr_id),
            "-R",
            str(repo),
            "--json",
            "files,title,number",
        ]
    )
    if not info:
        continue
    files = tuple(sorted([f["path"] for f in info.get("files", [])]))
    file_groups[(repo, files)].append(info)

duplicates = []
for (repo, files), pr_list in file_groups.items():
    if len(pr_list) > 1:
        # sort by number descending
        pr_list.sort(key=lambda x: x["number"], reverse=True)
        # keep the newest, close the rest
        for pr_info in pr_list[1:]:
            duplicates.append(f"{repo}#{pr_info['number']}")

print("Duplicates:", duplicates)

with open("tasks/pr-triage.md", "w") as f:
    f.write("# PR Triage\n\n")
    f.write("## SUPERSEDED\n")
    for pr in ready_prs:
        if pr in lines[lines.index("## SUPERSEDED\n") + 1 : lines.index("## STALE\n")]:
            if not pr.startswith("-"):
                pr = "- " + pr
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
