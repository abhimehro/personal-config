import json
import os
import re
import subprocess
import concurrent.futures
from collections import defaultdict
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

# OPTIMIZATION: Combine lines into a single string for fast C-level substring search
pre_ready_text = "".join(lines[: lines.index("## READY\n")])
ready_only = [
    pr
    for pr in ready_prs
    if pr not in pre_ready_text
]

def fetch_pr_info(pr):
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
    if info:
        return repo, info
    return None

file_groups = defaultdict(list)
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    future_to_pr = {executor.submit(fetch_pr_info, pr): pr for pr in ready_only}
    for future in concurrent.futures.as_completed(future_to_pr):
        res = future.result()
        if res:
            repo, info = res
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
