#!/usr/bin/env python3
"""Fetch and normalize paginated open pull-request inventory."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 50, states: OPEN, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number url title body isDraft headRefName headRefOid baseRefName baseRefOid
        author { login __typename }
        mergeable mergeStateStatus reviewDecision createdAt updatedAt
        latestReviews(first: 20) { nodes { author { login } state } }
        comments(last: 50) { totalCount nodes { author { login } body createdAt } }
        commits(last: 1) {
          nodes {
            commit {
              author { email }
              statusCheckRollup {
                contexts(first: 100) {
                  pageInfo { hasNextPage }
                  nodes {
                    __typename
                    ... on CheckRun { name conclusion status }
                    ... on StatusContext { context state }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

_FAILURE_CONCLUSIONS = {
    "FAILURE",
    "TIMED_OUT",
    "CANCELLED",
    "ACTION_REQUIRED",
    "STARTUP_FAILURE",
}


def _check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    typename = context.get("__typename")
    if typename == "CheckRun":
        name = context.get("name")
        if not isinstance(name, str):
            return None
        conclusion = str(context.get("conclusion") or "").upper()
        status = str(context.get("status") or "").upper()
        if conclusion in _FAILURE_CONCLUSIONS:
            state = "FAILURE"
        elif status != "COMPLETED":
            state = "PENDING"
        elif conclusion == "SUCCESS":
            state = "SUCCESS"
        elif conclusion in {"SKIPPED", "NEUTRAL"}:
            state = conclusion
        else:
            state = "NEUTRAL"
        return name, state
    if typename == "StatusContext":
        name = context.get("context")
        status = str(context.get("state") or "").upper()
        if not isinstance(name, str):
            return None
        if status in {"FAILURE", "ERROR"}:
            state = "FAILURE"
        elif status in {"PENDING", "EXPECTED"}:
            state = "PENDING"
        elif status == "SUCCESS":
            state = "SUCCESS"
        else:
            state = "NEUTRAL"
        return name, state
    return None


def _nodes(connection: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(connection, dict) or not isinstance(
        connection.get("nodes"), list
    ):
        raise OSError(f"malformed {label}")
    nodes = connection["nodes"]
    if not all(isinstance(node, dict) for node in nodes):
        raise OSError(f"malformed {label}")
    return nodes


def _normalize_pr(raw: dict[str, Any], repository: str) -> dict[str, Any]:
    author = raw.get("author")
    if author is not None and not isinstance(author, dict):
        raise OSError("malformed pull request author")
    if author is None:
        author = {}
    login = author.get("login")
    if login is not None and not isinstance(login, str):
        raise OSError("malformed pull request author")
    if raw.get("body") is not None and not isinstance(raw.get("body"), str):
        raise OSError("malformed pull request body")
    if (
        not isinstance(raw.get("number"), int)
        or isinstance(raw.get("number"), bool)
        or raw["number"] < 1
        or not isinstance(raw.get("url"), str)
        or not raw["url"].startswith("https://")
        or not isinstance(raw.get("isDraft"), bool)
    ):
        raise OSError("malformed pull request identity")
    normalized_author = {"login": author.get("login") or ""}
    if author.get("__typename") == "Bot":
        normalized_author["type"] = "Bot"

    reviews = [
        {
            "author": {"login": (review.get("author") or {}).get("login") or ""},
            "state": review.get("state"),
        }
        for review in _nodes(raw.get("latestReviews"), "latestReviews")
    ]
    comment_connection = raw.get("comments")
    comment_nodes = _nodes(comment_connection, "comments")
    comments = [
        {
            "author": {"login": (comment.get("author") or {}).get("login") or ""},
            "body": comment.get("body") or "",
            "createdAt": comment.get("createdAt"),
        }
        for comment in comment_nodes
    ]
    comments_total_count = (
        comment_connection.get("totalCount")
        if isinstance(comment_connection, dict)
        and isinstance(comment_connection.get("totalCount"), int)
        and not isinstance(comment_connection.get("totalCount"), bool)
        and comment_connection["totalCount"] >= 0
        else None
    )

    commits = _nodes(raw.get("commits"), "commits")
    normalized_commits: list[dict[str, Any]] = []
    checks: list[dict[str, str]] = []
    checks_incomplete = True
    if commits:
        commit = commits[-1].get("commit")
        if not isinstance(commit, dict):
            raise OSError("malformed commit")
        commit_author = commit.get("author") or {}
        if not isinstance(commit_author, dict):
            raise OSError("malformed commit author")
        normalized_commits.append(
            {"commit": {"author": {"email": commit_author.get("email")}}}
        )
        rollup = commit.get("statusCheckRollup")
        if rollup is not None:
            if not isinstance(rollup, dict):
                raise OSError("malformed statusCheckRollup")
            contexts_connection = rollup.get("contexts")
            page_info = (
                contexts_connection.get("pageInfo")
                if isinstance(contexts_connection, dict)
                else None
            )
            if isinstance(page_info, dict) and isinstance(
                page_info.get("hasNextPage"), bool
            ):
                checks_incomplete = page_info["hasNextPage"]
            if isinstance(contexts_connection, dict):
                contexts = _nodes(contexts_connection, "status check contexts")
                for context in contexts:
                    normalized = _check_state(context)
                    if normalized is not None:
                        checks.append({"name": normalized[0], "state": normalized[1]})
    if checks_incomplete:
        checks.append({"name": "statusCheckRollup truncated", "state": "PENDING"})

    normalized_pr = {
        "number": raw.get("number"),
        "url": raw.get("url"),
        "title": raw.get("title") or "",
        "body": str(raw.get("body") or "")[:2000],
        "isDraft": bool(raw.get("isDraft")),
        "headRefName": raw.get("headRefName") or "",
        "headRefOid": raw.get("headRefOid") or "",
        "baseRefName": raw.get("baseRefName") or "",
        "baseRefOid": raw.get("baseRefOid") or "",
        "author": normalized_author,
        "mergeable": raw.get("mergeable"),
        "mergeStateStatus": raw.get("mergeStateStatus"),
        "reviewDecision": raw.get("reviewDecision"),
        "createdAt": raw.get("createdAt"),
        "updatedAt": raw.get("updatedAt"),
        "latestReviews": reviews,
        "comments": comments,
        "commentsTotalCount": comments_total_count,
        "commits": normalized_commits,
        "checks": checks,
        "checksIncomplete": checks_incomplete,
        "repository": repository,
    }
    if (
        not isinstance(normalized_pr["title"], str)
        or not isinstance(normalized_pr["headRefName"], str)
        or not isinstance(normalized_pr["headRefOid"], str)
        or not isinstance(normalized_pr["baseRefName"], str)
        or not isinstance(normalized_pr["baseRefOid"], str)
    ):
        raise OSError("malformed pull request fields")
    return normalized_pr


def list_open_prs(
    repo: str,
    *,
    run: Any = subprocess.run,
    sleep: Any = time.sleep,
) -> list[dict[str, Any]]:
    """Return all open PRs in ``repo``; any API or payload failure raises OSError."""
    try:
        owner, name = repo.split("/", 1)
        if not owner or not name or "/" in name:
            raise ValueError("repository must be owner/name")
    except (AttributeError, ValueError) as exc:
        raise OSError("invalid repository") from exc

    prs: list[dict[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        command = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
        ]
        if cursor is not None:
            command.extend(["-F", f"cursor={cursor}"])
        payload: Any = None
        last_error: OSError | None = None
        for attempt in range(3):
            try:
                result = run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                last_error = OSError(
                    f"gh api graphql process failed: {type(exc).__name__}: {exc}"
                )
            else:
                if result.returncode != 0:
                    stderr = (result.stderr or "").strip()
                    last_error = OSError(
                        f"gh api graphql failed rc={result.returncode}: {stderr[:160]}"
                    )
                else:
                    try:
                        payload = json.loads(result.stdout)
                    except (TypeError, json.JSONDecodeError) as exc:
                        last_error = OSError(
                            f"gh api graphql returned invalid JSON: {exc}"
                        )
                    else:
                        break
            if attempt < 2:
                sleep((2, 5)[attempt])
        else:
            assert last_error is not None
            raise last_error
        if not isinstance(payload, dict):
            raise OSError("gh api graphql returned a malformed payload")
        if "errors" in payload:
            raise OSError("gh api graphql returned an API error")
        try:
            data = payload["data"]
            repository_data = data["repository"]
            connection = repository_data["pullRequests"]
            page_info = connection["pageInfo"]
            if not isinstance(page_info.get("hasNextPage"), bool):
                raise TypeError
            nodes = _nodes(connection, "pull requests")
            prs.extend(_normalize_pr(pr, repo) for pr in nodes)
            if not page_info["hasNextPage"]:
                return prs
            cursor = page_info.get("endCursor")
            if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
                raise TypeError
            seen_cursors.add(cursor)
        except (KeyError, TypeError, AttributeError) as exc:
            raise OSError("gh api graphql returned a malformed payload") from exc


def check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Expose check normalization for callers and tests."""
    return _check_state(context)
