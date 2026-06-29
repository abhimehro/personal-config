import json
import os
import subprocess
from collections import defaultdict
from functools import lru_cache


def _parse_env_line(line, env_dict):
    line = line.strip()
    if not line or line.startswith("#"):
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
    except Exception:
        return None


def _process_pr_result(res, file_groups):
    if not res:
        return
    repo, info = res
    # ⚡ Bolt Optimization: Use generator expression inside sorted() instead of list comprehension to avoid unnecessary memory spikes
    files = tuple(sorted(f["path"] for f in info.get("files", [])))
    file_groups[(repo, files)].append(info)


def _build_graphql_query(chunk):
    query_parts = []
    for j, pr in enumerate(chunk):
        repo, _, pr_id = pr.partition("#")
        try:
            owner, name = repo.split("/")
        except ValueError:
            continue
        query_parts.append(f"""
        pr{j}: repository(owner: "{owner}", name: "{name}") {{
            pullRequest(number: {pr_id}) {{
                number
                title
                files(first: 100) {{
                    nodes {{
                        path
                    }}
                }}
            }}
        }}
        """)
    if not query_parts:
        return None
    return "query { " + " ".join(query_parts) + " }"


def _process_graphql_response(result, chunk, file_groups):
    if not result:
        return
    data = result.get("data", {})
    if not data:
        return
    for j, pr in enumerate(chunk):
        repo, _, _ = pr.partition("#")

        pr_result = data.get(f"pr{j}", {})
        if not pr_result:
            continue

        pr_data = pr_result.get("pullRequest") or {}
        if not pr_data:
            continue

        files_data = pr_data.get("files", {}) or {}
        nodes = files_data.get("nodes", []) or []
        files = [{"path": node["path"]} for node in nodes if "path" in node]

        res = (
            repo,
            {
                "number": pr_data.get("number"),
                "title": pr_data.get("title"),
                "files": files,
            },
        )
        _process_pr_result(res, file_groups)


def _group_prs_by_files(ready_only):
    file_groups = defaultdict(list)
    chunk_size = 50
    for i in range(0, len(ready_only), chunk_size):
        chunk = ready_only[i : i + chunk_size]
        query = _build_graphql_query(chunk)
        if not query:
            continue
        result = run_gh(["gh", "api", "graphql", "-f", f"query={query}"])
        _process_graphql_response(result, chunk, file_groups)
    return file_groups


def _extract_duplicates_from_groups(file_groups):
    duplicates = []
    for (repo, _), pr_list in file_groups.items():
        if len(pr_list) > 1:
            pr_list.sort(key=lambda x: x["number"], reverse=True)
            for pr_info in pr_list[1:]:
                duplicates.append(f"{repo}#{pr_info['number']}")
    return duplicates


def get_duplicates(ready_only):
    file_groups = _group_prs_by_files(ready_only)
    return _extract_duplicates_from_groups(file_groups)


def _get_superseded_text(lines):
    try:
        superseded_start = lines.index("## SUPERSEDED\n") + 1
    except ValueError:
        superseded_start = 0
    try:
        stale_start = lines.index("## STALE\n")
    except ValueError:
        stale_start = len(lines)
    return "".join(lines[superseded_start:stale_start])


def _generate_superseded_section(ready_prs, superseded_text):
    out = ["## SUPERSEDED"]
    for pr in ready_prs:
        if pr in superseded_text:
            out.append(pr if pr.startswith("-") else f"- {pr}")
    return out


def _generate_duplicate_section(duplicates):
    out = ["## DUPLICATE"]
    for d in duplicates:
        out.append(f"- {d}")
    return out


def _generate_ready_section(ready_only, duplicates):
    out = ["## READY"]
    duplicates_set = set(duplicates)
    for pr in ready_only:
        if pr not in duplicates_set:
            out.append(f"- {pr}")
    return out


def rewrite_triage_file(lines, ready_prs, duplicates, ready_only):
    superseded_text = _get_superseded_text(lines)

    sections = [
        "# PR Triage\n",
        *_generate_superseded_section(ready_prs, superseded_text),
        "## STALE",
        "## CONFLICTING",
        "- abhimehro/personal-config#725",
        *_generate_duplicate_section(duplicates),
        *_generate_ready_section(ready_only, duplicates),
    ]

    with open("tasks/pr-triage.md", "w") as f:
        f.write("\n".join(sections) + "\n")


def main():
    try:
        with open("tasks/pr-triage.md", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("tasks/pr-triage.md not found.")
        return

    ready_prs = [line.strip()[2:] for line in lines if line.startswith("- abhimehro/")]

    try:
        ready_idx = lines.index("## READY\n")
        pre_ready_text = "".join(lines[:ready_idx])
    except ValueError:
        pre_ready_text = ""

    ready_only = [pr for pr in ready_prs if pr not in pre_ready_text]

    duplicates = get_duplicates(ready_only)
    print("Duplicates:", duplicates)

    rewrite_triage_file(lines, ready_prs, duplicates, ready_only)
    print("Done")


if __name__ == "__main__":
    main()
