from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github" / "repository-automation.yml"
OUTPUT_ROOT = ROOT / ".automation-output"
DAILY_WORKFLOW_NAME = "Repository Automation - Daily"

BASH_BIN = shutil.which("bash") or "/bin/bash"
GH_BIN = shutil.which("gh") or "gh"
GIT_BIN = shutil.which("git") or "git"

ALLOWED_STATUSES = {"success", "warning", "failure", "needs_review", "skipped"}


def command_env() -> dict[str, str]:
    return {**os.environ, "GH_PAGER": "cat"}


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_day(value: dt.datetime | None = None) -> str:
    return (value or now_utc()).date().isoformat()


def load_config() -> dict[str, Any]:
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


def run_process(
    command: list[str],
    *,
    input_text: str | None = None,
    timeout: int | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=timeout,
        env=command_env(),
    )


def run_shell_command(command: str, timeout: int = 1800) -> dict[str, Any]:
    # Commands originate from repository-controlled configuration, not user input.
    proc = run_process([BASH_BIN, "-lc", command], timeout=timeout)
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": truncate(proc.stdout),
        "stderr": truncate(proc.stderr),
    }


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return run_process(command, check=True)


def warn_on_default(tool: str, args: list[str], proc: subprocess.CompletedProcess[str]) -> None:
    error_text = proc.stderr.strip() or proc.stdout.strip()
    print(
        f"Warning: `{tool} {' '.join(args)}` failed with exit code {proc.returncode}. {error_text}",
        file=sys.stderr,
    )


def gh_json(args: list[str], default=None):
    proc = run_process([GH_BIN, *args])
    if proc.returncode != 0:
        if default is not None:
            warn_on_default("gh", args, proc)
            return default
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    output = proc.stdout.strip()
    if not output:
        return default
    return json.loads(output)


def gh_text(args: list[str], default: str = "") -> str:
    proc = run_process([GH_BIN, *args])
    if proc.returncode != 0:
        warn_on_default("gh", args, proc)
        return default
    return proc.stdout.strip()


def writes_allowed() -> bool:
    raw = os.environ.get("AUTOMATION_ALLOW_WRITES", "false").lower()
    return raw in {"1", "true", "yes", "on"}


def ensure_gh_token() -> bool:
    return bool(os.environ.get("GH_TOKEN"))


def normalise_status(status: str) -> str:
    return status if status in ALLOWED_STATUSES else "warning"


def build_result(task: str, status: str, summary: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "task": task,
        "status": normalise_status(status),
        "summary": summary,
        "generated_at": now_utc().isoformat(),
    }
    if extra:
        result.update(extra)
    return result


def write_result(task: str, status: str, summary: str, body: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result = build_result(task, status, summary, extra)
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


def command_block(entry: dict[str, Any]) -> str:
    pieces = [f"- **{entry['name']}** -> exit `{entry['exit_code']}`"]
    if entry.get("stdout"):
        pieces.append("```text\n" + entry["stdout"].strip() + "\n```")
    if entry.get("stderr"):
        pieces.append("```text\n" + entry["stderr"].strip() + "\n```")
    return "\n".join(pieces)


def matches_any(path_str: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path_str, pattern) for pattern in patterns)


def git_output(*args: str) -> str:
    return run_checked([GIT_BIN, *args]).stdout.strip()


def safe_pr_body(title: str, updates: list[dict[str, str]], notes: list[str]) -> str:
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


def normalize_label_specs(labels: list[Any]) -> list[dict[str, str]]:
    if not labels:
        return []
    specs = []
    for entry in labels:
        if isinstance(entry, str):
            specs.append({"name": entry, "color": "1d76db", "description": ""})
        elif isinstance(entry, dict) and entry.get("name"):
            specs.append(
                {
                    "name": str(entry["name"]),
                    "color": str(entry.get("color", "1d76db")),
                    "description": str(entry.get("description", "")),
                }
            )
    return specs


def ensure_label_exists(spec: dict[str, str], known_labels: set[str]) -> None:
    name = spec["name"]
    if name in known_labels or not writes_allowed():
        return
    args = [GH_BIN, "label", "create", name, "--color", spec["color"]]
    if spec["description"]:
        args.extend(["--description", spec["description"]])
    proc = run_process(args)
    if proc.returncode != 0:
        warn_on_default("gh", args[1:], proc)
        return
    known_labels.add(name)


def filter_existing_labels(labels: list[Any]) -> list[str]:
    specs = normalize_label_specs(labels)
    if not specs:
        return []
    label_rows = gh_json(["label", "list", "--limit", "100", "--json", "name"], default=[])
    known = {row.get("name") for row in label_rows}
    for spec in specs:
        ensure_label_exists(spec, known)
    return [spec["name"] for spec in specs if spec["name"] in known]


def gh_with_body(args: list[str], body: str) -> str:
    proc = run_process([GH_BIN, *args], input_text=body)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def create_or_update_issue(title: str, body: str, labels: list[Any]) -> str:
    search = gh_json(["issue", "list", "--state", "all", "--limit", "100", "--json", "number,title,url"], default=[])
    existing = next((item for item in search if item.get("title") == title), None)
    existing_labels = filter_existing_labels(labels)
    if existing:
        command = ["issue", "edit", str(existing["number"]), "--body-file", "-"]
        if existing_labels:
            command.extend(["--add-label", ",".join(existing_labels)])
        gh_with_body(command, body)
        return existing["url"]
    create_command = ["issue", "create", "--title", title, "--body-file", "-"]
    for label in existing_labels:
        create_command.extend(["--label", label])
    return gh_with_body(create_command, body)


def create_pr_for_current_changes(branch_prefix: str, commit_message: str, pr_title: str, pr_body: str) -> str:
    existing = gh_json(["pr", "list", "--state", "open", "--json", "title,url"], default=[])
    existing_match = next((item for item in existing if item.get("title") == pr_title), None)
    if existing_match:
        return existing_match["url"]
    branch_name = f"{branch_prefix.replace('/', '-')}-{now_utc().strftime('%Y%m%d')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    run_checked([GIT_BIN, "config", "user.name", "repository-automation[bot]"])
    run_checked([GIT_BIN, "config", "user.email", "repository-automation[bot]@users.noreply.github.com"])
    run_checked([GIT_BIN, "checkout", "-b", branch_name])
    run_checked([GIT_BIN, "add", "-A"])
    run_checked([GIT_BIN, "commit", "-m", commit_message])
    run_checked([GIT_BIN, "push", "--set-upstream", "origin", branch_name])
    return gh_with_body(["pr", "create", "--draft", "--title", pr_title, "--body-file", "-"], pr_body)


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
    if not current_v or not latest_v:
        return None
    if latest_v <= current_v:
        return None
    if re.fullmatch(r"v?\d+", current):
        prefix = "v" if current.startswith("v") or latest.startswith("v") else ""
        return f"{prefix}{latest_v[0]}"
    return latest


def append_publication_result(
    body: str,
    *,
    title: str,
    labels: list[Any],
    noun: str,
) -> tuple[str, str, str | None]:
    if not writes_allowed():
        body += f"\n## Write gate\n- {noun} publication skipped because this run is in report-only mode.\n"
        return body, "", None
    if not ensure_gh_token():
        body += f"\n## Publishing failure\n- GH_TOKEN is missing, so the {noun} could not be created.\n"
        return body, "", "missing GH_TOKEN"
    try:
        issue_url = create_or_update_issue(title, body, labels)
        body += f"\n## Published issue\n- {issue_url}\n"
        return body, issue_url, None
    except Exception as exc:  # pragma: no cover - runtime integration
        body += f"\n## Publishing failure\n- {exc}\n"
        return body, "", str(exc)
