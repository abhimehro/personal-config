#!/usr/bin/env python3
"""Find open Octopus finding issues linked to pull requests."""

from __future__ import annotations

import json
import re
from typing import Any

OCTOPUS_ISSUE_AUTHOR = "octopus-review[bot]"


def linked_prs(repo: str, body: object) -> set[int]:
    """Return same-repository PR numbers in Octopus's structured body forms."""
    if not isinstance(body, str):
        return set()
    url_pattern = re.compile(
        rf"https?://github\.com/{re.escape(repo)}/pull/(\d+)\b",
        re.IGNORECASE,
    )
    pull_request_pattern = re.compile(
        r"^Pull Request:.*\(#(\d+)\)\s*$",
        re.MULTILINE,
    )
    numbers = {int(match.group(1)) for match in url_pattern.finditer(body)}
    numbers.update(int(match.group(1)) for match in pull_request_pattern.finditer(body))
    return numbers


def _query_issue_payload(repo: str, run: Any) -> Any:
    """Fetch and decode the paginated Octopus issue response."""
    endpoint = (
        f"repos/{repo}/issues?state=open&creator=octopus-review%5Bbot%5D&per_page=100"
    )
    result = run(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            endpoint,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise OSError(f"gh api Octopus issues failed rc={result.returncode}")
    try:
        return json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise OSError("malformed Octopus issue JSON") from exc


def _is_octopus_issue(issue: dict[str, Any]) -> bool:
    """Return whether an issue object belongs to the Octopus bot."""
    user = issue.get("user")
    return (
        "pull_request" not in issue
        and isinstance(user, dict)
        and user.get("login") == OCTOPUS_ISSUE_AUTHOR
    )


def _issue_number(issue: dict[str, Any]) -> int:
    """Return a valid Octopus issue number."""
    number = issue.get("number")
    if type(number) is not int or number < 1:
        raise OSError("malformed Octopus issue number")
    return number


def fetch_open_octopus_issues(repo: str, *, run: Any) -> dict[int, list[int]]:
    """Fetch open Octopus issues, returning linked PR numbers to issue numbers."""
    items = _issue_items(_query_issue_payload(repo, run))

    issues_by_pr: dict[int, set[int]] = {}
    for issue in items:
        if not _is_octopus_issue(issue):
            continue
        issue_number = _issue_number(issue)
        for pr_number in linked_prs(repo, issue.get("body")):
            issues_by_pr.setdefault(pr_number, set()).add(issue_number)
    return {
        pr_number: sorted(issue_numbers)
        for pr_number, issue_numbers in issues_by_pr.items()
    }


def _issue_items(payload: Any) -> list[dict[str, Any]]:
    """Flatten a --slurp page list or validate a flat issue list."""
    if not isinstance(payload, list):
        raise OSError("malformed Octopus issue payload")
    items = (
        [issue for page in payload for issue in page]
        if payload and all(isinstance(page, list) for page in payload)
        else payload
    )
    if not all(isinstance(issue, dict) for issue in items):
        raise OSError("malformed Octopus issue payload")
    return items


def attach_octopus_issues(
    prs: list[dict[str, Any]], issues_by_pr: dict[int, list[int]]
) -> None:
    """Attach open finding issue numbers to their linked PR inventory entries."""
    for pr in prs:
        pr["openOctopusIssues"] = issues_by_pr.get(pr["number"], [])
