#!/usr/bin/env python3
"""Find open Octopus finding issues linked to pull requests."""

from __future__ import annotations

import json
import re
from typing import Any

OCTOPUS_ISSUE_AUTHOR = "octopus-review[bot]"
_PULL_REQUEST_LINE = re.compile(
    r"^Pull Request:.*\(#(\d+)\)\s*$",
    re.MULTILINE,
)


def _same_repo_pr_numbers(repo: str, body: str) -> set[int]:
    """Return PR numbers from same-repository GitHub pull URLs."""
    # SECURITY: a body that only mentions another repo's PR must not block it.
    pattern = re.compile(
        rf"https?://github\.com/{re.escape(repo)}/pull/(\d+)\b",
        re.IGNORECASE,
    )
    return {int(match.group(1)) for match in pattern.finditer(body)}


def _pull_request_line_numbers(body: str) -> set[int]:
    """Return PR numbers from Octopus's structured Pull Request lines."""
    return {int(match.group(1)) for match in _PULL_REQUEST_LINE.finditer(body)}


def linked_prs(repo: str, body: object) -> set[int]:
    """Return same-repository PR numbers in Octopus's structured body forms."""
    if not isinstance(body, str):
        return set()
    return _same_repo_pr_numbers(repo, body) | _pull_request_line_numbers(body)


def _issue_endpoint(repo: str) -> str:
    """Return the open-issue query limited to the Octopus bot."""
    return (
        f"repos/{repo}/issues?state=open&creator=octopus-review%5Bbot%5D&per_page=100"
    )


def _run_issue_query(run: Any, endpoint: str) -> Any:
    """Run the paginated issue query. check=False so the caller types the error."""
    return run(
        ["gh", "api", "--paginate", "--slurp", endpoint],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _decode_issue_stdout(stdout: str) -> Any:
    """Decode issue JSON, or raise OSError when the payload is not JSON."""
    try:
        return json.loads(stdout)
    except (TypeError, ValueError) as exc:
        raise OSError("malformed Octopus issue JSON") from exc


def _query_issue_payload(repo: str, run: Any) -> Any:
    """Fetch and decode the paginated Octopus issue response."""
    result = _run_issue_query(run, _issue_endpoint(repo))
    if result.returncode != 0:
        raise OSError(f"gh api Octopus issues failed rc={result.returncode}")
    return _decode_issue_stdout(result.stdout)


def _author_is_octopus(issue: dict[str, Any]) -> bool:
    """Return whether the issue user is the Octopus bot."""
    user = issue.get("user")
    return isinstance(user, dict) and user.get("login") == OCTOPUS_ISSUE_AUTHOR


def _is_octopus_issue(issue: dict[str, Any]) -> bool:
    """Return whether an issue object belongs to the Octopus bot."""
    return "pull_request" not in issue and _author_is_octopus(issue)


def _issue_number(issue: dict[str, Any]) -> int:
    """Return a valid Octopus issue number."""
    number = issue.get("number")
    if type(number) is not int or number < 1:
        raise OSError("malformed Octopus issue number")
    return number


def _remember_issue(
    issues_by_pr: dict[int, set[int]], repo: str, issue: dict[str, Any]
) -> None:
    """Record one Octopus issue against each PR it links."""
    if not _is_octopus_issue(issue):
        return
    issue_number = _issue_number(issue)
    for pr_number in linked_prs(repo, issue.get("body")):
        issues_by_pr.setdefault(pr_number, set()).add(issue_number)


def _sorted_issue_map(issues_by_pr: dict[int, set[int]]) -> dict[int, list[int]]:
    """Return linked PR numbers mapped to sorted issue numbers."""
    return {
        pr_number: sorted(issue_numbers)
        for pr_number, issue_numbers in issues_by_pr.items()
    }


def fetch_open_octopus_issues(repo: str, *, run: Any) -> dict[int, list[int]]:
    """Fetch open Octopus issues, returning linked PR numbers to issue numbers."""
    issues_by_pr: dict[int, set[int]] = {}
    for issue in _issue_items(_query_issue_payload(repo, run)):
        _remember_issue(issues_by_pr, repo, issue)
    return _sorted_issue_map(issues_by_pr)


def _payload_is_pages(payload: list) -> bool:
    """Return whether --slurp returned a list of pages."""
    return bool(payload) and all(isinstance(page, list) for page in payload)


def _concat_pages(payload: list) -> list:
    """Flatten a list of issue pages into one list."""
    return [issue for page in payload for issue in page]


def _flatten_pages(payload: list) -> list:
    """Flatten --slurp pages when the payload contains page lists."""
    if _payload_is_pages(payload):
        return _concat_pages(payload)
    return payload


def _require_issue_dicts(items: list) -> list[dict[str, Any]]:
    """Reject a payload that is not a list of issue objects."""
    if not all(isinstance(issue, dict) for issue in items):
        raise OSError("malformed Octopus issue payload")
    return items


def _issue_items(payload: Any) -> list[dict[str, Any]]:
    """Validate the flattened Octopus issue payload."""
    if not isinstance(payload, list):
        raise OSError("malformed Octopus issue payload")
    return _require_issue_dicts(_flatten_pages(payload))


def attach_octopus_issues(
    prs: list[dict[str, Any]], issues_by_pr: dict[int, list[int]]
) -> None:
    """Attach open finding issue numbers to their linked PR inventory entries."""
    for pr in prs:
        pr["openOctopusIssues"] = issues_by_pr.get(pr["number"], [])
