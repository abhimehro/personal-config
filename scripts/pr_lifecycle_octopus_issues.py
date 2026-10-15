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


def fetch_open_octopus_issues(repo: str, *, run: Any) -> dict[int, list[int]]:
    """Fetch open Octopus issues, returning linked PR numbers to issue numbers."""
    result = run(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            (
                f"repos/{repo}/issues?state=open&creator="
                "octopus-review%5Bbot%5D&per_page=100"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise OSError(f"gh api Octopus issues failed rc={result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise OSError("malformed Octopus issue JSON") from exc
    items = _issue_items(payload)

    issues_by_pr: dict[int, set[int]] = {}
    for issue in items:
        if "pull_request" in issue:
            continue
        user = issue.get("user")
        if not isinstance(user, dict) or user.get("login") != OCTOPUS_ISSUE_AUTHOR:
            continue
        issue_number = issue.get("number")
        if (
            not isinstance(issue_number, int)
            or isinstance(issue_number, bool)
            or issue_number < 1
        ):
            raise OSError("malformed Octopus issue number")
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
    if all(isinstance(page, list) for page in payload):
        items = [issue for page in payload for issue in page]
    elif all(isinstance(issue, dict) for issue in payload):
        items = payload
    else:
        raise OSError("malformed Octopus issue payload")
    if not all(isinstance(issue, dict) for issue in items):
        raise OSError("malformed Octopus issue payload")
    return items


def attach_octopus_issues(
    prs: list[dict[str, Any]], issues_by_pr: dict[int, list[int]]
) -> None:
    """Attach open finding issue numbers to their linked PR inventory entries."""
    for pr in prs:
        pr["openOctopusIssues"] = issues_by_pr.get(pr["number"], [])
