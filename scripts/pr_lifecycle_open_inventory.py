#!/usr/bin/env python3
"""Fetch and normalize paginated open pull-request inventory."""

from __future__ import annotations

import json
import re
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
        latestReviews(first: 20) { nodes { author { login __typename } state } }
        comments(last: 50) { totalCount nodes { author { login __typename } body createdAt } }
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

# Structured types take precedence; message markers cover untyped errors only.
# The "temporar" marker requires a word boundary and no leading "not " so an
# explicit "not temporary" error does not count as transient.
_TRANSIENT_GQL_TYPES = {"RATE_LIMITED", "INTERNAL", "SERVICE_UNAVAILABLE", "TIMEOUT"}
_TRANSIENT_GQL_RE = re.compile(
    r"rate limit|timeout|timed out|unavailable|internal|(?<!not )\btemporar"
)


def _is_transient_gql_error(error: Any) -> bool:
    """Classify one API error, rejecting unknown types and malformed entries."""
    if not isinstance(error, dict):
        return False
    error_type = error.get("type")
    if error_type is not None:
        return isinstance(error_type, str) and error_type in _TRANSIENT_GQL_TYPES
    message = error.get("message")
    return isinstance(message, str) and bool(_TRANSIENT_GQL_RE.search(message.lower()))


def _check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a check run or legacy status to a name/state pair.

    Return None for unsupported context types or missing string names.
    """
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
    """Return connection nodes or raise OSError for malformed node lists."""
    if not isinstance(connection, dict) or not isinstance(
        connection.get("nodes"), list
    ):
        raise OSError(f"malformed {label}")
    nodes = connection["nodes"]
    if not all(isinstance(node, dict) for node in nodes):
        raise OSError(f"malformed {label}")
    return nodes


def _author_login(author: Any) -> str:
    """Return a login with the REST-style '[bot]' suffix for GraphQL Bot actors.

    Return an empty string when author data or the login is missing.
    """
    if not isinstance(author, dict):
        return ""
    login = str(author.get("login") or "")
    if author.get("__typename") == "Bot" and login and not login.endswith("[bot]"):
        return f"{login}[bot]"
    return login


def _require_identity(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw PR's identity fields; return its author mapping.

    Raise OSError for a non-mapping author, a non-string login or body, or
    malformed number/url/isDraft fields. A null author normalizes to {}.
    """
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
    return author


def _normalize_reviews(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Return latestReviews nodes as {author.login, state} dicts."""
    return [
        {
            "author": {"login": _author_login(review.get("author"))},
            "state": review.get("state"),
        }
        for review in _nodes(raw.get("latestReviews"), "latestReviews")
    ]


def _normalize_comments(
    raw: dict[str, Any],
) -> tuple[list[dict[str, Any]], int | None]:
    """Return (comment dicts, totalCount or None when unknown/invalid)."""
    connection = raw.get("comments")
    comments = [
        {
            "author": {"login": _author_login(comment.get("author"))},
            "body": comment.get("body") or "",
            "createdAt": comment.get("createdAt"),
        }
        for comment in _nodes(connection, "comments")
    ]
    total = connection.get("totalCount") if isinstance(connection, dict) else None
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = None
    return comments, total


def _checks_truncated(connection: Any) -> bool:
    """True when the contexts pageInfo is absent or reports a next page."""
    page_info = connection.get("pageInfo") if isinstance(connection, dict) else None
    if isinstance(page_info, dict) and isinstance(page_info.get("hasNextPage"), bool):
        return page_info["hasNextPage"]
    return True


def _commit_checks(
    raw: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], bool]:
    """Return (normalized commits, checks, checks_incomplete) for a raw PR.

    Only the last commit is normalized. An absent commit, non-dict commit or
    commit author, or a non-dict statusCheckRollup fails closed: missing
    rollups mark checks incomplete and a synthetic PENDING check is appended.
    """
    commits = _nodes(raw.get("commits"), "commits")
    if not commits:
        return [], [{"name": "statusCheckRollup truncated", "state": "PENDING"}], True
    commit = commits[-1].get("commit")
    if not isinstance(commit, dict):
        raise OSError("malformed commit")
    commit_author = commit.get("author") or {}
    if not isinstance(commit_author, dict):
        raise OSError("malformed commit author")
    normalized_commits = [{"commit": {"author": {"email": commit_author.get("email")}}}]
    checks: list[dict[str, str]] = []
    checks_incomplete = True
    rollup = commit.get("statusCheckRollup")
    if rollup is not None:
        if not isinstance(rollup, dict):
            raise OSError("malformed statusCheckRollup")
        connection = rollup.get("contexts")
        checks_incomplete = _checks_truncated(connection)
        if isinstance(connection, dict):
            for context in _nodes(connection, "status check contexts"):
                normalized = _check_state(context)
                if normalized is not None:
                    checks.append({"name": normalized[0], "state": normalized[1]})
    if checks_incomplete:
        checks.append({"name": "statusCheckRollup truncated", "state": "PENDING"})
    return normalized_commits, checks, checks_incomplete


def _normalize_pr(raw: dict[str, Any], repository: str) -> dict[str, Any]:
    """Validate and normalize a GraphQL PR for identity and blocker routing.

    Raise OSError for malformed fields. Mark incomplete check rollups as
    pending and preserve unknown comment counts so callers fail closed.
    """
    author = _require_identity(raw)
    normalized_author = {"login": _author_login(author)}
    if author.get("__typename") == "Bot":
        normalized_author["type"] = "Bot"
    comments, comments_total_count = _normalize_comments(raw)
    commits, checks, checks_incomplete = _commit_checks(raw)

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
        "latestReviews": _normalize_reviews(raw),
        "comments": comments,
        "commentsTotalCount": comments_total_count,
        "commits": commits,
        "checks": checks,
        "checksIncomplete": checks_incomplete,
        "repository": repository,
    }
    if not all(
        isinstance(normalized_pr[key], str)
        for key in ("title", "headRefName", "headRefOid", "baseRefName", "baseRefOid")
    ):
        raise OSError("malformed pull request fields")
    return normalized_pr


def _split_repo(repo: str) -> tuple[str, str]:
    """Split owner/name, raising OSError for anything else."""
    try:
        owner, name = repo.split("/", 1)
        if not owner or not name or "/" in name:
            raise ValueError("repository must be owner/name")
    except (AttributeError, ValueError) as exc:
        raise OSError("invalid repository") from exc
    return owner, name


def _graphql_command(owner: str, name: str, cursor: str | None) -> list[str]:
    """Build the gh api graphql argv for one pullRequests page."""
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
    return command


def _page_result(
    result: subprocess.CompletedProcess[str],
) -> tuple[OSError | None, Any]:
    """Classify one gh api graphql response.

    Return (retryable OSError, None) for failures worth retrying, or
    (None, payload) on success. A GraphQL errors payload whose messages
    are not transient raises immediately rather than retrying.
    """
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return (
            OSError(f"gh api graphql failed rc={result.returncode}: {stderr[:160]}"),
            None,
        )
    try:
        payload = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        return OSError(f"gh api graphql returned invalid JSON: {exc}"), None
    if not (isinstance(payload, dict) and "errors" in payload):
        return None, payload
    errors = payload["errors"]
    if (
        not isinstance(errors, list)
        or not errors
        or not all(_is_transient_gql_error(err) for err in errors)
    ):
        raise OSError("gh api graphql returned an API error")
    messages = " ".join(str(err.get("message", "")) for err in errors).lower()
    return OSError(f"gh api graphql transient error: {messages[:160]}"), None


def _graphql_page(command: list[str], *, run: Any, sleep: Any) -> Any:
    """Fetch one GraphQL page, retrying transient failures up to 3 times."""
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
            last_error, payload = _page_result(result)
            if last_error is None:
                return payload
        if attempt < 2:
            sleep(2 ** (attempt + 1))
    assert last_error is not None
    raise last_error


def _page_connection(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (pullRequests connection, pageInfo); raise on a bad payload."""
    if not isinstance(payload, dict):
        raise OSError("gh api graphql returned a malformed payload")
    if "errors" in payload:
        raise OSError("gh api graphql returned an API error")
    try:
        connection = payload["data"]["repository"]["pullRequests"]
        page_info = connection["pageInfo"]
        if not isinstance(page_info.get("hasNextPage"), bool):
            raise TypeError
    except (KeyError, TypeError, AttributeError) as exc:
        raise OSError("gh api graphql returned a malformed payload") from exc
    return connection, page_info


def list_open_prs(
    repo: str,
    *,
    run: Any = subprocess.run,
    sleep: Any = time.sleep,
) -> list[dict[str, Any]]:
    """Return normalized open PRs in an owner/name repository, including drafts.

    Each page gets up to three attempts for process failures, nonzero exits,
    invalid JSON, or transient API errors, with 2- and 4-second waits.
    Nontransient API errors and rejected inventory or pagination data raise
    OSError immediately; exhausted retries also raise OSError. Invalid repo
    names raise OSError before any request. A later-page failure never returns
    a partial inventory.
    """
    owner, name = _split_repo(repo)
    prs: list[dict[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        payload = _graphql_page(
            _graphql_command(owner, name, cursor), run=run, sleep=sleep
        )
        connection, page_info = _page_connection(payload)
        prs.extend(
            _normalize_pr(pr, repo) for pr in _nodes(connection, "pull requests")
        )
        if not page_info["hasNextPage"]:
            return prs
        cursor = page_info.get("endCursor")
        if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
            raise OSError("gh api graphql returned a malformed payload")
        seen_cursors.add(cursor)


def check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Return a check name/state pair.

    Return None for unsupported context types or non-string names.
    """
    return _check_state(context)
