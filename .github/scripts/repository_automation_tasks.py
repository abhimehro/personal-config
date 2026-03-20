from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from repository_automation_common import (
    DAILY_WORKFLOW_NAME,
    OUTPUT_ROOT,
    ROOT,
    append_publication_result,
    command_block,
    create_pr_for_current_changes,
    ensure_gh_token,
    gh_json,
    git_output,
    iso_day,
    latest_tag_for_action,
    matches_any,
    now_utc,
    run_shell_command,
    safe_pr_body,
    target_ref,
    write_result,
    writes_allowed,
)

WORKFLOW_PATTERN = re.compile(r"(uses:\s*)([^@\s]+)@([^\s#]+)")
IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__"}


def configured_commands(section: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    buckets = []
    for bucket_name, key in (("setup", "setup_commands"), ("command", "commands"), ("security", "security_commands")):
        for item in section.get(key, []):
            buckets.append((bucket_name, item))
    return buckets


def execute_configured_commands(section: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    setup_entries = []
    command_entries = []
    for bucket_name, item in configured_commands(section):
        entry = {
            "bucket": bucket_name,
            "name": item["name"],
            **run_shell_command(item["run"], int(item.get("timeout_seconds", 1800))),
            "optional": bool(item.get("optional", False)),
        }
        if bucket_name == "setup":
            setup_entries.append(entry)
        else:
            command_entries.append(entry)
    return setup_entries, command_entries


def classify_entries(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    failures = []
    warnings = []
    for entry in entries:
        if entry["exit_code"] == 0:
            continue
        if entry.get("optional"):
            warnings.append(entry)
        else:
            failures.append(entry)
    return failures, warnings


def render_entry_section(title: str, entries: list[dict[str, Any]]) -> list[str]:
    if not entries:
        return []
    lines = [title]
    lines.extend(command_block(entry) for entry in entries)
    lines.append("")
    return lines


def render_review_section(title: str, entries: list[dict[str, Any]], template: str) -> list[str]:
    if not entries:
        return []
    lines = [title]
    lines.extend(template.format(name=entry["name"]) for entry in entries)
    lines.append("")
    return lines


def run_command_set(task_name: str, section: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    setup_entries, command_entries = execute_configured_commands(section)
    failures, warnings = classify_entries(setup_entries + command_entries)
    status = "failure" if failures else "warning" if warnings else "success"
    summary = f"{task_name} executed {len(setup_entries)} setup commands and {len(command_entries)} validation commands."
    body_parts = [
        f"# {task_name.title().replace('-', ' ')}",
        "",
        f"- Status: **{status}**",
        f"- Summary: {summary}",
        "",
    ]
    body_parts.extend(render_entry_section("## Setup commands", setup_entries))
    body_parts.extend(render_entry_section("## Validation commands", command_entries))
    body_parts.extend(
        render_review_section(
            "## Human review required",
            failures,
            "- `{name}` failed and is not marked optional.",
        )
    )
    if not failures:
        body_parts.extend(
            render_review_section(
                "## Optional command warnings",
                warnings,
                "- `{name}` failed but is configured as optional.",
            )
        )
    return status, summary, {
        "setup_results": setup_entries,
        "command_results": command_entries,
        "body": "\n".join(body_parts).strip() + "\n",
    }


def discover_hotspots(limit: int = 5) -> list[tuple[str, int]]:
    candidates = []
    for extension in ("*.py", "*.sh"):
        for path in ROOT.rglob(extension):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            try:
                line_count = path.read_text(encoding="utf-8").count("\n") + 1
            except (UnicodeDecodeError, OSError):
                continue
            candidates.append((str(path.relative_to(ROOT)), line_count))
    return sorted(candidates, key=lambda item: item[1], reverse=True)[:limit]


def workflow_file_plans() -> list[dict[str, Any]]:
    latest_cache: dict[str, str] = {}
    plans = []
    for file_path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = file_path.read_text()
        replacements = []
        for match in WORKFLOW_PATTERN.finditer(text):
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
            replacements.append(
                {
                    "old": match.group(0),
                    "new": f"{match.group(1)}{action_ref}@{proposed}",
                    "file": str(file_path.relative_to(ROOT)),
                    "action": action_ref,
                    "current": current,
                    "target": proposed,
                }
            )
        if replacements:
            plans.append({"path": file_path, "text": text, "replacements": replacements})
    return plans


def flattened_updates(plans: list[dict[str, Any]]) -> list[dict[str, str]]:
    updates = []
    for plan in plans:
        for item in plan["replacements"]:
            updates.append(
                {
                    "file": item["file"],
                    "action": item["action"],
                    "current": item["current"],
                    "target": item["target"],
                }
            )
    return updates


def apply_workflow_updates(plans: list[dict[str, Any]]) -> None:
    for plan in plans:
        updated_text = plan["text"]
        for replacement in plan["replacements"]:
            updated_text = updated_text.replace(replacement["old"], replacement["new"])
        plan["path"].write_text(updated_text)


def restore_workflow_updates(plans: list[dict[str, Any]]) -> None:
    for plan in plans:
        plan["path"].write_text(plan["text"])


def allowed_workflow_updates(updates: list[dict[str, str]], patterns: list[str]) -> bool:
    return all(matches_any(item["file"], patterns) for item in updates)


def render_update_table(updates: list[dict[str, str]]) -> list[str]:
    lines = [
        "## Proposed updates",
        "| File | Action | Previous | Proposed |",
        "| --- | --- | --- | --- |",
    ]
    for item in updates:
        lines.append(f"| `{item['file']}` | `{item['action']}` | `{item['current']}` | `{item['target']}` |")
    lines.append("")
    return lines


def run_workflow_updater(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("workflow_updater", {})
    plans = workflow_file_plans()
    updates = flattened_updates(plans)
    if not updates:
        body = "# Workflow updater\n\n- Status: **success**\n- Summary: No GitHub Action updates were detected.\n"
        return write_result("workflow-updater", "success", "No GitHub Action updates were detected.", body, {"updates": []})

    status = "warning"
    summary = f"Detected {len(updates)} workflow action updates."
    body_parts = ["# Workflow updater", "", f"- Status: **{status}**", f"- Summary: {summary}", ""]
    body_parts.extend(render_update_table(updates))

    can_write = writes_allowed() and ensure_gh_token() and section.get("create_draft_pr", False)
    if not can_write:
        body_parts.extend(["## Write gate", "- Draft PR creation is disabled or writes are not allowed for this run.", ""])
        return write_result("workflow-updater", status, summary, "\n".join(body_parts), {"updates": updates, "pull_request_url": ""})

    allowed_paths = section.get("allowed_paths", [".github/workflows/*.yml", ".github/workflows/*.yaml"])
    if not allowed_workflow_updates(updates, allowed_paths):
        body_parts.extend(["## Human review required", "- Refusing to write because one or more files are outside the allow-list.", ""])
        return write_result("workflow-updater", "needs_review", summary, "\n".join(body_parts), {"updates": updates, "pull_request_url": ""})

    pr_url = ""
    try:
        apply_workflow_updates(plans)
        pr_body = safe_pr_body(
            section.get("pr_title", "Workflow update"),
            updates,
            [
                "Security gate limited changes to allow-listed workflow paths.",
                "No force-push or merge is performed by this automation.",
            ],
        )
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
        restore_workflow_updates(plans)
        status = "failure"
        body_parts.extend(["## Draft PR failure", f"- {exc}", ""])
    return write_result("workflow-updater", status, summary, "\n".join(body_parts), {"updates": updates, "pull_request_url": pr_url})


def run_performance_optimizer(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("performance_optimizer", {})
    status, summary, details = run_command_set("performance-optimizer", {
        "setup_commands": section.get("setup_commands", []),
        "commands": section.get("commands", []),
    })
    hotspots = discover_hotspots()
    lines = [details["body"].rstrip(), "## Static hotspots", "| File | Approximate lines |", "| --- | ---: |"]
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


def run_quality_assurance(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("quality_assurance", {})
    status, summary, details = run_command_set("quality-assurance", section)
    return write_result("quality-assurance", status, summary, details["body"], {"command_results": details["command_results"]})


def parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def age_days(timestamp: str) -> int:
    return (now_utc() - parse_timestamp(timestamp)).days


def render_issue_rows(issues: list[dict[str, Any]]) -> list[str]:
    rows = ["## Open issues (oldest updated first)", "| Issue | Last updated | Age (days) | Labels |", "| --- | --- | ---: | --- |"]
    for item in issues:
        labels = ", ".join(label["name"] for label in item.get("labels", []))
        rows.append(f"| [#{item['number']}]({item['url']}) | {item['updatedAt'][:10]} | {age_days(item['updatedAt'])} | {labels or '-'} |")
    return rows


def render_pr_rows(prs: list[dict[str, Any]]) -> list[str]:
    rows = ["", "## Open pull requests (oldest updated first)", "| PR | Last updated | Age (days) | Draft | Review | Merge state |", "| --- | --- | ---: | --- | --- | --- |"]
    for item in prs:
        rows.append(
            f"| [#{item['number']}]({item['url']}) | {item['updatedAt'][:10]} | {age_days(item['updatedAt'])} | {item.get('isDraft')} | {item.get('reviewDecision') or '-'} | {item.get('mergeStateStatus') or '-'} |"
        )
    return rows


def run_backlog_manager(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("backlog_manager", {})
    max_issues = int(section.get("max_issues", 10))
    max_prs = int(section.get("max_pull_requests", 10))
    issues = gh_json(["issue", "list", "--state", "open", "--limit", str(max_issues), "--json", "number,title,updatedAt,url,labels"], default=[])
    prs = gh_json(["pr", "list", "--state", "open", "--limit", str(max_prs), "--json", "number,title,updatedAt,url,isDraft,reviewDecision,mergeStateStatus"], default=[])
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
    ]
    lines.extend(render_issue_rows(issues))
    lines.extend(render_pr_rows(prs))
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


def load_task_results() -> list[dict[str, Any]]:
    results = []
    for path in sorted(OUTPUT_ROOT.glob("*/result.json")):
        try:
            results.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    return results


def overall_status(results: list[dict[str, Any]]) -> str:
    statuses = [item.get("status") for item in results]
    if "failure" in statuses:
        return "failure"
    if "needs_review" in statuses:
        return "needs_review"
    if "warning" in statuses:
        return "warning"
    return "success"


def status_icon(status: str) -> str:
    return {
        "success": "SUCCESS",
        "warning": "WARNING",
        "failure": "FAILURE",
        "needs_review": "REVIEW",
        "skipped": "SKIPPED",
    }.get(status, status.upper())


def daily_report_lines(config: dict[str, Any], results: list[dict[str, Any]]) -> list[str]:
    open_issues = gh_json(["issue", "list", "--state", "open", "--limit", "200", "--json", "number"], default=[])
    open_prs = gh_json(["pr", "list", "--state", "open", "--limit", "200", "--json", "number"], default=[])
    releases = gh_json(["release", "list", "--limit", "5", "--json", "name,publishedAt,tagName"], default=[])
    overall = overall_status(results)
    lines = [
        f"# Daily Repository Automation Report - {iso_day()}",
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
            name = release.get("name") or release.get("tagName") or "Unnamed release"
            lines.append(f"- {name} published {release.get('publishedAt', '')[:10]}")
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
    return lines


def run_daily_status_report(config: dict[str, Any]) -> dict[str, Any]:
    results = load_task_results()
    summary = f"Daily automation completed with overall status {overall_status(results)}."
    section = config.get("status_report", {})
    title = f"{config.get('reporting', {}).get('daily_issue_prefix', '[repo-automation] Daily Status Report')} - {iso_day()}"
    body = "\n".join(daily_report_lines(config, results))
    body, issue_url, error = append_publication_result(body, title=title, labels=section.get("labels", []), noun="daily issue")
    status = "failure" if error else overall_status(results)
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


def run_safe_adjustment_commands(section: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if not writes_allowed() or not section.get("auto_apply_safe_changes"):
        return [], ""
    command_results = []
    for item in section.get("safe_adjustment_commands", []):
        command_results.append({"name": item["name"], **run_shell_command(item["run"], int(item.get("timeout_seconds", 1200)))})
    changed = [line[3:] for line in git_output("status", "--porcelain").splitlines() if line]
    allowed_paths = section.get("allowed_paths", [".github/workflows/*.yml", ".github/workflows/*.yaml"])
    if not changed or not all(matches_any(path, allowed_paths) for path in changed):
        return command_results, ""
    body = safe_pr_body(
        "Weekly safe workflow tuning",
        [],
        [
            "Generated from weekly retrospective safe_adjustment_commands.",
            "Restricted to allow-listed workflow paths.",
        ],
    )
    url = create_pr_for_current_changes(
        section.get("branch_prefix", "automation/weekly-workflow-tuning"),
        section.get("commit_message", "chore(actions): apply safe weekly automation tuning"),
        "chore(actions): weekly automation tuning",
        body,
    )
    return command_results, url


def recent_daily_runs() -> list[dict[str, Any]]:
    cutoff = now_utc() - dt.timedelta(days=7)
    runs = gh_json(["run", "list", "--workflow", DAILY_WORKFLOW_NAME, "--limit", "20", "--json", "number,createdAt,status,conclusion,url"], default=[])
    return [item for item in runs if parse_timestamp(item["createdAt"]) >= cutoff]


def weekly_markers(prefix: str) -> dict[str, dict[str, int]]:
    cutoff = now_utc() - dt.timedelta(days=7)
    issues = gh_json(["issue", "list", "--state", "all", "--limit", "100", "--json", "title,createdAt,body"], default=[])
    markers: dict[str, dict[str, int]] = {}
    for issue in issues:
        if not issue.get("title", "").startswith(prefix):
            continue
        if parse_timestamp(issue["createdAt"]) < cutoff:
            continue
        for task, value in extract_status_markers(issue.get("body", "")).items():
            markers.setdefault(task, {}).setdefault(value, 0)
            markers[task][value] += 1
    return markers


def weekly_report_lines(config: dict[str, Any], runs: list[dict[str, Any]], markers: dict[str, dict[str, int]], safe_changes: list[dict[str, Any]], safe_pr_url: str) -> tuple[str, list[str]]:
    status = "success"
    if any(item.get("conclusion") not in {"success", "skipped", None} for item in runs):
        status = "warning"
    lines = [
        f"# Weekly Repository Automation Retrospective - {iso_day()}",
        "",
        f"- Status: **{status}**",
        f"- Summary: Reviewed {len(runs)} daily workflow runs from the last 7 days.",
        "",
        "## Daily workflow runs",
        "| Run | Created | Status | Conclusion |",
        "| --- | --- | --- | --- |",
    ]
    for item in runs:
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
    return status, lines


def run_weekly_retrospective(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("weekly_retrospective", {})
    runs = recent_daily_runs()
    markers = weekly_markers(config.get('reporting', {}).get('daily_issue_prefix', '[repo-automation] Daily Status Report'))
    safe_changes = []
    safe_pr_url = ""
    if ensure_gh_token():
        try:
            safe_changes, safe_pr_url = run_safe_adjustment_commands(section)
        except Exception as exc:  # pragma: no cover - runtime integration
            safe_changes = [{"name": "safe-adjustment-commands", "exit_code": 1, "stdout": "", "stderr": str(exc)}]
    status, lines = weekly_report_lines(config, runs, markers, safe_changes, safe_pr_url)
    summary = f"Reviewed {len(runs)} daily workflow runs from the last 7 days."
    title = f"{config.get('reporting', {}).get('weekly_issue_prefix', '[repo-automation] Weekly Retrospective')} - {iso_day()}"
    body = "\n".join(lines) + "\n"
    body, issue_url, error = append_publication_result(body, title=title, labels=section.get("labels", []), noun="weekly issue")
    if error:
        status = "failure"
    return write_result("weekly-retrospective", status, summary, body, {"issue_url": issue_url, "runs": runs, "safe_pr_url": safe_pr_url})
