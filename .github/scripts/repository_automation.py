#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - installed in workflow
    raise SystemExit(f"PyYAML is required: {exc}")


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github" / "repository-automation.yml"
OUTPUT_ROOT = ROOT / ".automation-output"
DAILY_WORKFLOW_NAME = "Repository Automation - Daily"


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_day(value: dt.datetime | None = None) -> str:
    return (value or now_utc()).date().isoformat()


def load_config() -> dict:
    data = yaml.safe_load(CONFIG_PATH.read_text())
    return data.get("automation", {})


def task_dir(task: str) -> Path:
    path = OUTPUT_ROOT / task
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 15] + "\n... [truncated]"


def run_command(command: str, timeout: int = 1800) -> dict:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        shell=True,
        executable="/bin/bash",
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "GH_PAGER": "cat"},
    )
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": truncate(proc.stdout),
        "stderr": truncate(proc.stderr),
    }


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GH_PAGER": "cat"},
    )


def gh_json(args: list[str], default=None):
    proc = subprocess.run(
        ["gh", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "GH_PAGER": "cat"},
    )
    if proc.returncode != 0:
        if default is not None:
            return default
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    output = proc.stdout.strip()
    if not output:
        return default
    return json.loads(output)


def gh_text(args: list[str], default: str = "") -> str:
    proc = subprocess.run(
        ["gh", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "GH_PAGER": "cat"},
    )
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def writes_allowed() -> bool:
    raw = os.environ.get("AUTOMATION_ALLOW_WRITES", "false").lower()
    return raw in {"1", "true", "yes", "on"}


def ensure_gh_token() -> bool:
    return bool(os.environ.get("GH_TOKEN"))


def normalise_status(status: str) -> str:
    if status not in {"success", "warning", "failure", "needs_review", "skipped"}:
        return "warning"
    return status


def write_result(task: str, status: str, summary: str, body: str, extra: dict | None = None) -> dict:
    result = {
        "task": task,
        "status": normalise_status(status),
        "summary": summary,
        "generated_at": now_utc().isoformat(),
    }
    if extra:
        result.update(extra)
    directory = task_dir(task)
    (directory / "report.md").write_text(body.rstrip() + "\n")
    (directory / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(body)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(body.rstrip() + "\n\n")
    return result


def enforce_result(path_str: str) -> int:
    path = Path(path_str)
    if not path.exists():
        print(f"Missing task result: {path}")
        return 1
    data = json.loads(path.read_text())
    return 1 if data.get("status") in {"failure", "needs_review"} else 0


def command_block(entry: dict) -> str:
    pieces = [f"- **{entry['name']}** -> exit `{entry['exit_code']}`"]
    if entry.get("stdout"):
        pieces.append("```text\n" + entry["stdout"].strip() + "\n```")
    if entry.get("stderr"):
        pieces.append("```text\n" + entry["stderr"].strip() + "\n```")
    return "\n".join(pieces)


def run_command_set(task_name: str, section: dict) -> tuple[str, str, dict]:
    setup_entries = []
    command_entries = []
    failures = []
    warnings = []
    for bucket_name, target in (
        ("setup", section.get("setup_commands", [])),
        ("command", section.get("commands", [])),
        ("security", section.get("security_commands", [])),
    ):
        for item in target:
            result = run_command(item["run"], int(item.get("timeout_seconds", 1800)))
            entry = {
                "bucket": bucket_name,
                "name": item["name"],
                **result,
                "optional": bool(item.get("optional", False)),
            }
            if bucket_name == "setup":
                setup_entries.append(entry)
            else:
                command_entries.append(entry)
            if result["exit_code"] != 0:
                if entry["optional"]:
                    warnings.append(entry)
                else:
                    failures.append(entry)
    status = "success"
    if failures:
        status = "failure"
    elif warnings:
        status = "warning"
    summary = f"{task_name} executed {len(setup_entries)} setup commands and {len(command_entries)} validation commands."
    body_parts = [
        f"# {task_name.title().replace('-', ' ')}",
        "",
        f"- Status: **{status}**",
        f"- Summary: {summary}",
        "",
    ]
    if setup_entries:
        body_parts.append("## Setup commands")
        body_parts.extend(command_block(entry) for entry in setup_entries)
        body_parts.append("")
    if command_entries:
        body_parts.append("## Validation commands")
        body_parts.extend(command_block(entry) for entry in command_entries)
        body_parts.append("")
    if failures:
        body_parts.append("## Human review required")
        for entry in failures:
            body_parts.append(f"- `{entry['name']}` failed and is not marked optional.")
        body_parts.append("")
    elif warnings:
        body_parts.append("## Optional command warnings")
        for entry in warnings:
            body_parts.append(f"- `{entry['name']}` failed but is configured as optional.")
        body_parts.append("")
    return status, summary, {
        "setup_results": setup_entries,
        "command_results": command_entries,
        "body": "\n".join(body_parts).strip() + "\n",
    }


def discover_hotspots(limit: int = 5) -> list[tuple[str, int]]:
    candidates = []
    for extension in ("*.py", "*.sh"):
        for path in ROOT.rglob(extension):
            parts = set(path.parts)
            if ".git" in parts or ".venv" in parts or "node_modules" in parts or "__pycache__" in parts:
                continue
            try:
                line_count = path.read_text(encoding="utf-8").count("\n") + 1
            except UnicodeDecodeError:
                continue
            candidates.append((str(path.relative_to(ROOT)), line_count))
    return sorted(candidates, key=lambda item: item[1], reverse=True)[:limit]


def matches_any(path_str: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path_str, pattern) for pattern in patterns)


def create_or_update_issue(title: str, body: str, labels: list[str]) -> str:
    search = gh_json(["issue", "list", "--state", "all", "--limit", "100", "--json", "number,title,url"], default=[])
    existing = next((item for item in search if item.get("title") == title), None)
    existing_labels = []
    if labels:
        label_rows = gh_json(["label", "list", "--limit", "100", "--json", "name"], default=[])
        existing_labels = [label for label in labels if any(row.get("name") == label for row in label_rows)]
    if existing:
        command = ["issue", "edit", str(existing["number"]), "--body-file", "-"]
        if existing_labels:
            command.extend(["--add-label", ",".join(existing_labels)])
        proc = subprocess.run(
            ["gh", *command],
            input=body,
            text=True,
            cwd=ROOT,
            env={**os.environ, "GH_PAGER": "cat"},
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        return existing["url"]
    command = ["gh", "issue", "create", "--title", title, "--body-file", "-"]
    for label in existing_labels:
        command.extend(["--label", label])
    proc = subprocess.run(
        command,
        input=body,
        text=True,
        cwd=ROOT,
        env={**os.environ, "GH_PAGER": "cat"},
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def git_output(*args: str) -> str:
    return run_checked(["git", *args]).stdout.strip()


def safe_pr_body(title: str, updates: list[dict], notes: list[str]) -> str:
    lines = [
        f"## {title}",
        "",
        "This draft PR was created by the consolidated repository automation workflow.",
        "",
    ]
    if updates:
        lines.extend(
            [
                "### Updates",
                "| File | Action reference | Previous | Proposed |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in updates:
            lines.append(
                f"| `{item['file']}` | `{item['action']}` | `{item['current']}` | `{item['target']}` |"
            )
    if notes:
        lines.extend(["", "### Guardrails"])
        lines.extend(f"- {note}" for note in notes)
    lines.extend(["", "### Safety notes", "- Draft PR only", "- No force-pushes", "- No automatic merges"])
    return "\n".join(lines) + "\n"


def create_pr_for_current_changes(branch_prefix: str, commit_message: str, pr_title: str, pr_body: str) -> str:
    existing = gh_json(["pr", "list", "--state", "open", "--json", "title,url"], default=[])
    existing_match = next((item for item in existing if item.get("title") == pr_title), None)
    if existing_match:
        return existing_match["url"]
    branch_name = f"{branch_prefix.replace('/', '-')}-{now_utc().strftime('%Y%m%d')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    run_checked(["git", "config", "user.name", "repository-automation[bot]"])
    run_checked(["git", "config", "user.email", "repository-automation[bot]@users.noreply.github.com"])
    run_checked(["git", "checkout", "-b", branch_name])
    run_checked(["git", "add", "-A"])
    run_checked(["git", "commit", "-m", commit_message])
    run_checked(["git", "push", "--set-upstream", "origin", branch_name])
    proc = subprocess.run(
        ["gh", "pr", "create", "--draft", "--title", pr_title, "--body-file", "-"],
        input=pr_body,
        text=True,
        cwd=ROOT,
        capture_output=True,
        env={**os.environ, "GH_PAGER": "cat"},
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def latest_tag_for_action(repo_id: str) -> str:
    latest = gh_text(["api", f"repos/{repo_id}/releases/latest", "--jq", ".tag_name"])
    if latest:
        return latest
    return gh_text(["api", f"repos/{repo_id}/tags?per_page=1", "--jq", ".[0].name"])


def numeric_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(group or 0) for group in match.groups())


def target_ref(current: str, latest: str) -> str | None:
    current_v = numeric_version(current)
    latest_v = numeric_version(latest)
    if not current_v or not latest_v or latest_v <= current_v:
        return None
    if re.fullmatch(r"v?\d+", current):
        prefix = "v" if current.startswith("v") or latest.startswith("v") else ""
        return f"{prefix}{latest_v[0]}"
    return latest


def run_workflow_updater(config: dict) -> dict:
    section = config.get("workflow_updater", {})
    updates = []
    latest_cache = {}
    allowed_paths = section.get("allowed_paths", [".github/workflows/*.yml", ".github/workflows/*.yaml"])
    pattern = re.compile(r"(uses:\s*)([^@\s]+)@([^\s#]+)")
    files = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
    for file_path in files:
        relative = str(file_path.relative_to(ROOT))
        text = file_path.read_text()
        replacements = []
        for match in pattern.finditer(text):
            action_ref = match.group(2)
            current = match.group(3)
            if action_ref.startswith("./") or action_ref.startswith("docker://"):
                continue
            parts = action_ref.split("/")
            if len(parts) < 2:
                continue
            repo_id = "/".join(parts[:2])
            latest = latest_cache.get(repo_id)
            if latest is None:
                latest = latest_tag_for_action(repo_id)
                latest_cache[repo_id] = latest
            proposed = target_ref(current, latest)
            if not proposed or proposed == current:
                continue
            replacements.append((match.group(0), f"{match.group(1)}{action_ref}@{proposed}", action_ref, current, proposed))
        if replacements:
            for old, new, action_ref, current, proposed in replacements:
                text = text.replace(old, new)
                updates.append(
                    {
                        "file": relative,
                        "action": action_ref,
                        "current": current,
                        "target": proposed,
                    }
                )
            file_path.write_text(text)
    status = "success"
    summary = "No GitHub Action updates were detected."
    body_parts = ["# Workflow updater", ""]
    pr_url = ""
    if updates:
        status = "warning"
        summary = f"Detected {len(updates)} workflow action updates."
        body_parts.extend(
            [
                f"- Status: **{status}**",
                f"- Summary: {summary}",
                "",
                "## Proposed updates",
                "| File | Action | Previous | Proposed |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in updates:
            body_parts.append(f"| `{item['file']}` | `{item['action']}` | `{item['current']}` | `{item['target']}` |")
        body_parts.append("")
        if writes_allowed() and ensure_gh_token() and section.get("create_draft_pr", False):
            for item in updates:
                if not matches_any(item["file"], allowed_paths):
                    status = "needs_review"
                    body_parts.extend(
                        [
                            "## Human review required",
                            f"- Refusing to write because `{item['file']}` is outside the allow-list.",
                            "",
                        ]
                    )
                    break
            if status != "needs_review":
                pr_body = safe_pr_body(
                    section.get("pr_title", "Workflow update"),
                    updates,
                    [
                        "Security gate limited changes to allow-listed workflow paths.",
                        "No force-push or merge is performed by this automation.",
                    ],
                )
                try:
                    pr_url = create_pr_for_current_changes(
                        section.get("branch_prefix", "automation/workflow-updates"),
                        section.get("commit_message", "chore(actions): update workflow dependencies"),
                        section.get("pr_title", "chore(actions): update workflow dependencies"),
                        pr_body,
                    )
                    status = "success"
                    summary = f"Detected {len(updates)} workflow action updates and prepared a draft PR."
                    body_parts.extend(["## Draft PR", f"- {pr_url}", ""])
                except Exception as exc:  # pragma: no cover - runtime integration
                    status = "failure"
                    body_parts.extend(["## Draft PR failure", f"- {exc}", ""])
        else:
            body_parts.extend(
                [
                    "## Write gate",
                    "- Draft PR creation is disabled or writes are not allowed for this run.",
                    "",
                ]
            )
    else:
        body_parts.extend([f"- Status: **{status}**", f"- Summary: {summary}", ""])
    return write_result("workflow-updater", status, summary, "\n".join(body_parts), {"updates": updates, "pull_request_url": pr_url})


def run_performance_optimizer(config: dict) -> dict:
    section = config.get("performance_optimizer", {})
    commands = {
        "setup_commands": section.get("setup_commands", []),
        "commands": section.get("commands", []),
    }
    status, summary, details = run_command_set("performance-optimizer", commands)
    hotspots = discover_hotspots()
    body = details["body"]
    lines = [body.rstrip(), "## Static hotspots", "| File | Approximate lines |", "| --- | ---: |"]
    for file_name, count in hotspots:
        lines.append(f"| `{file_name}` | {count} |")
    suggestions = section.get("suggestions", [])
    if suggestions:
        lines.extend(["", "## Suggestions"])
        lines.extend(f"- {item}" for item in suggestions)
    return write_result(
        "performance-optimizer",
        status,
        summary,
        "\n".join(lines) + "\n",
        {"hotspots": hotspots, "command_results": details["command_results"]},
    )


def run_quality_assurance(config: dict) -> dict:
    section = config.get("quality_assurance", {})
    status, summary, details = run_command_set("quality-assurance", section)
    return write_result("quality-assurance", status, summary, details["body"], {"command_results": details["command_results"]})


def parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def age_days(timestamp: str) -> int:
    return (now_utc() - parse_timestamp(timestamp)).days


def run_backlog_manager(config: dict) -> dict:
    section = config.get("backlog_manager", {})
    max_issues = int(section.get("max_issues", 10))
    max_prs = int(section.get("max_pull_requests", 10))
    issues = gh_json(["issue", "list", "--state", "open", "--limit", str(max_issues), "--json", "number,title,updatedAt,url,labels"], default=[])
    prs = gh_json(
        ["pr", "list", "--state", "open", "--limit", str(max_prs), "--json", "number,title,updatedAt,url,isDraft,reviewDecision,mergeStateStatus"],
        default=[],
    )
    issues = sorted(issues, key=lambda item: item.get("updatedAt", ""))
    prs = sorted(prs, key=lambda item: item.get("updatedAt", ""))
    stale_days = int(section.get("stale_days", 14))
    stale_issues = [item for item in issues if age_days(item["updatedAt"]) >= stale_days]
    stale_prs = [item for item in prs if age_days(item["updatedAt"]) >= stale_days]
    status = "warning" if stale_issues or stale_prs else "success"
    summary = f"Backlog scan found {len(issues)} open issues and {len(prs)} open PRs in the sampled set."
    lines = [
        "# Backlog manager",
        "",
        f"- Status: **{status}**",
        f"- Summary: {summary}",
        f"- Stale threshold: **{stale_days} days**",
        "",
        "## Open issues (oldest updated first)",
        "| Issue | Last updated | Age (days) | Labels |",
        "| --- | --- | ---: | --- |",
    ]
    for item in issues:
        labels = ", ".join(label["name"] for label in item.get("labels", []))
        lines.append(f"| [#{item['number']}]({item['url']}) | {item['updatedAt'][:10]} | {age_days(item['updatedAt'])} | {labels or '-'} |")
    lines.extend(
        [
            "",
            "## Open pull requests (oldest updated first)",
            "| PR | Last updated | Age (days) | Draft | Review | Merge state |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for item in prs:
        lines.append(
            f"| [#{item['number']}]({item['url']}) | {item['updatedAt'][:10]} | {age_days(item['updatedAt'])} | {item.get('isDraft')} | {item.get('reviewDecision') or '-'} | {item.get('mergeStateStatus') or '-'} |"
        )
    if stale_issues or stale_prs:
        lines.extend(["", "## Human review candidates"])
        for item in stale_issues:
            lines.append(f"- Issue #{item['number']} has been quiet for {age_days(item['updatedAt'])} days: {item['title']}")
        for item in stale_prs:
            lines.append(f"- PR #{item['number']} has been quiet for {age_days(item['updatedAt'])} days: {item['title']}")
    return write_result(
        "backlog-manager",
        status,
        summary,
        "\n".join(lines) + "\n",
        {"issues": issues, "pull_requests": prs, "stale_issues": stale_issues, "stale_pull_requests": stale_prs},
    )


def load_task_results() -> list[dict]:
    results = []
    for path in sorted(OUTPUT_ROOT.glob("*/result.json")):
        try:
            results.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    return results


def status_icon(status: str) -> str:
    return {
        "success": "SUCCESS",
        "warning": "WARNING",
        "failure": "FAILURE",
        "needs_review": "REVIEW",
        "skipped": "SKIPPED",
    }.get(status, status.upper())


def run_daily_status_report(config: dict) -> dict:
    section = config.get("status_report", {})
    results = load_task_results()
    open_issues = gh_json(["issue", "list", "--state", "open", "--limit", "200", "--json", "number"], default=[])
    open_prs = gh_json(["pr", "list", "--state", "open", "--limit", "200", "--json", "number"], default=[])
    releases = gh_json(["release", "list", "--limit", "5", "--json", "name,publishedAt,url"], default=[])
    overall = "success"
    if any(item.get("status") == "failure" for item in results):
        overall = "failure"
    elif any(item.get("status") == "needs_review" for item in results):
        overall = "needs_review"
    elif any(item.get("status") == "warning" for item in results):
        overall = "warning"
    summary = f"Daily automation completed with overall status {overall}."
    date_value = iso_day()
    title = f"{config.get('reporting', {}).get('daily_issue_prefix', '[repo-automation] Daily Status Report')} - {date_value}"
    lines = [
        f"# Daily Repository Automation Report - {date_value}",
        "",
        f"- Overall status: **{overall}**",
        f"- Open issues: **{len(open_issues)}**",
        f"- Open pull requests: **{len(open_prs)}**",
        "",
        "## Task outcomes",
        "| Task | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for item in results:
        lines.append(f"| `{item['task']}` | {status_icon(item['status'])} | {item['summary']} |")
    lines.extend(["", "## Recent releases"])
    if releases:
        for release in releases:
            name = release.get("name") or release.get("url")
            lines.append(f"- [{name}]({release['url']}) published {release.get('publishedAt', '')[:10]}")
    else:
        lines.append("- No recent releases returned by the API.")
    lines.extend(["", "## Recommendations"])
    if overall == "success":
        lines.append("- No blocking findings. Review the status report issue and any workflow-updater draft PR before merging.")
    else:
        lines.append("- Review the failing or warning tasks before trusting any generated changes.")
    if any(item.get("status") in {"failure", "needs_review"} for item in results):
        lines.append("- Human review is required for at least one task; no silent automation escalation was performed.")
    lines.extend(["", "<!-- repository-automation:task-status"])
    for item in results:
        lines.append(f"{item['task']}={item['status']}")
    lines.extend(["-->", ""])
    body = "\n".join(lines)
    issue_url = ""
    status = overall
    if section.get("publish_issue", True):
        if not writes_allowed():
            body += "\n## Write gate\n- Issue publication skipped because this run is in report-only mode.\n"
        elif not ensure_gh_token():
            status = "failure"
            body += "\n## Publishing failure\n- GH_TOKEN is missing, so the daily issue could not be created.\n"
        else:
            try:
                issue_url = create_or_update_issue(title, body, section.get("labels", []))
                body += f"\n## Published issue\n- {issue_url}\n"
            except Exception as exc:  # pragma: no cover - runtime integration
                status = "failure"
                body += f"\n## Publishing failure\n- {exc}\n"
    return write_result("daily-status-report", status, summary, body, {"issue_url": issue_url, "task_results": results})


def extract_status_markers(issue_body: str) -> dict[str, str]:
    match = re.search(r"<!-- repository-automation:task-status\n(.*?)\n-->", issue_body, re.S)
    if not match:
        return {}
    markers = {}
    for line in match.group(1).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            markers[key.strip()] = value.strip()
    return markers


def run_safe_adjustment_commands(section: dict) -> tuple[list[dict], str]:
    if not writes_allowed() or not section.get("auto_apply_safe_changes"):
        return [], ""
    command_results = []
    for item in section.get("safe_adjustment_commands", []):
        command_results.append({"name": item["name"], **run_command(item["run"], int(item.get("timeout_seconds", 1200)))})
    diff_files = git_output("status", "--porcelain")
    changed = [line[3:] for line in diff_files.splitlines() if line]
    if not changed:
        return command_results, ""
    allowed_paths = section.get("allowed_paths", [".github/**"])
    if not all(matches_any(path, allowed_paths) for path in changed):
        return command_results, ""
    body = safe_pr_body(
        "Weekly safe workflow tuning",
        [],
        [
            "Generated from weekly retrospective safe_adjustment_commands.",
            "Restricted to .github-only allow-listed paths.",
        ],
    )
    url = create_pr_for_current_changes(
        section.get("branch_prefix", "automation/weekly-workflow-tuning"),
        section.get("commit_message", "chore(actions): apply safe weekly automation tuning"),
        "chore(actions): weekly automation tuning",
        body,
    )
    return command_results, url


def run_weekly_retrospective(config: dict) -> dict:
    section = config.get("weekly_retrospective", {})
    cutoff = now_utc() - dt.timedelta(days=7)
    runs = gh_json(
        ["run", "list", "--workflow", DAILY_WORKFLOW_NAME, "--limit", "20", "--json", "number,createdAt,status,conclusion,url,displayTitle"],
        default=[],
    )
    recent_runs = [item for item in runs if parse_timestamp(item["createdAt"]) >= cutoff]
    issues = gh_json(["issue", "list", "--state", "all", "--limit", "100", "--json", "title,createdAt,body"], default=[])
    prefix = config.get("reporting", {}).get("daily_issue_prefix", "[repo-automation] Daily Status Report")
    markers = {}
    for issue in issues:
        if not issue.get("title", "").startswith(prefix):
            continue
        created = parse_timestamp(issue["createdAt"])
        if created < cutoff:
            continue
        for task, value in extract_status_markers(issue.get("body", "")).items():
            markers.setdefault(task, {}).setdefault(value, 0)
            markers[task][value] += 1
    safe_changes = []
    safe_pr_url = ""
    if ensure_gh_token():
        try:
            safe_changes, safe_pr_url = run_safe_adjustment_commands(section)
        except Exception as exc:  # pragma: no cover - runtime integration
            safe_changes = [{"name": "safe-adjustment-commands", "exit_code": 1, "stdout": "", "stderr": str(exc)}]
    status = "success"
    if any(item.get("conclusion") not in {"success", "skipped", None} for item in recent_runs):
        status = "warning"
    summary = f"Reviewed {len(recent_runs)} daily workflow runs from the last 7 days."
    title = f"{config.get('reporting', {}).get('weekly_issue_prefix', '[repo-automation] Weekly Retrospective')} - {iso_day()}"
    lines = [
        f"# Weekly Repository Automation Retrospective - {iso_day()}",
        "",
        f"- Status: **{status}**",
        f"- Summary: {summary}",
        "",
        "## Daily workflow runs",
        "| Run | Created | Status | Conclusion |",
        "| --- | --- | --- | --- |",
    ]
    for item in recent_runs:
        lines.append(f"| [#{item['number']}]({item['url']}) | {item['createdAt'][:10]} | {item.get('status') or '-'} | {item.get('conclusion') or '-'} |")
    lines.extend(["", "## Recurring task patterns"])
    if markers:
        lines.append("| Task | Status counts |")
        lines.append("| --- | --- |")
        for task_name, counts in sorted(markers.items()):
            rendered = ", ".join(f"{name}: {count}" for name, count in sorted(counts.items()))
            lines.append(f"| `{task_name}` | {rendered} |")
    else:
        lines.append("- No machine-readable task markers were found in the last week's daily status issues.")
    lines.extend(["", "## Recommendations"])
    if status == "success":
        lines.append("- The consolidated automation was stable this week. Keep manual review on for writes that touch protected areas.")
    else:
        lines.append("- Review repeated warning or failure patterns before increasing automation scope.")
    if safe_changes:
        lines.extend(["", "## Safe adjustment command results"])
        for entry in safe_changes:
            lines.append(f"- `{entry['name']}` -> exit `{entry['exit_code']}`")
    if safe_pr_url:
        lines.extend(["", "## Safe auto-apply draft PR", f"- {safe_pr_url}"])
    body = "\n".join(lines) + "\n"
    issue_url = ""
    if section.get("publish_issue", True):
        if not writes_allowed():
            body += "\n## Write gate\n- Issue publication skipped because this run is in report-only mode.\n"
        elif not ensure_gh_token():
            status = "failure"
            body += "\n## Publishing failure\n- GH_TOKEN is missing, so the weekly issue could not be created.\n"
        else:
            try:
                issue_url = create_or_update_issue(title, body, section.get("labels", []))
                body += f"\n## Published issue\n- {issue_url}\n"
            except Exception as exc:  # pragma: no cover - runtime integration
                status = "failure"
                body += f"\n## Publishing failure\n- {exc}\n"
    return write_result("weekly-retrospective", status, summary, body, {"issue_url": issue_url, "runs": recent_runs, "safe_pr_url": safe_pr_url})


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidated repository automation runner")
    parser.add_argument("task")
    parser.add_argument("result_path", nargs="?")
    args = parser.parse_args()

    if args.task == "enforce":
        if not args.result_path:
            print("enforce requires a result path")
            return 1
        return enforce_result(args.result_path)

    config = load_config()
    task = args.task
    if task == "workflow-updater":
        run_workflow_updater(config)
    elif task == "performance-optimizer":
        run_performance_optimizer(config)
    elif task == "quality-assurance":
        run_quality_assurance(config)
    elif task == "backlog-manager":
        run_backlog_manager(config)
    elif task == "daily-status-report":
        run_daily_status_report(config)
    elif task == "weekly-retrospective":
        run_weekly_retrospective(config)
    else:
        print(f"Unknown task: {task}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
