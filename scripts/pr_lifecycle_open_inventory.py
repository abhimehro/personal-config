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

_TRUNCATED_CHECK = {"name": "statusCheckRollup truncated", "state": "PENDING"}

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


def _concluded_state(conclusion: str) -> str:
    """Map a COMPLETED CheckRun conclusion to a normalized state."""
    if conclusion == "SUCCESS":
        return "SUCCESS"
    return conclusion if conclusion in {"SKIPPED", "NEUTRAL"} else "NEUTRAL"


def _check_run_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a CheckRun context to a name/state pair, or None if nameless."""
    name = context.get("name")
    if not isinstance(name, str):
        return None
    conclusion = str(context.get("conclusion") or "").upper()
    if conclusion in _FAILURE_CONCLUSIONS:
        return name, "FAILURE"
    status = str(context.get("status") or "").upper()
    if status != "COMPLETED":
        return name, "PENDING"
    return name, _concluded_state(conclusion)


def _status_context_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a legacy StatusContext to a name/state pair, or None if nameless."""
    name = context.get("context")
    if not isinstance(name, str):
        return None
    status = str(context.get("state") or "").upper()
    if status in {"FAILURE", "ERROR"}:
        return name, "FAILURE"
    if status in {"PENDING", "EXPECTED"}:
        return name, "PENDING"
    if status == "SUCCESS":
        return name, "SUCCESS"
    return name, "NEUTRAL"


def _check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a check run or legacy status to a name/state pair.

    Return None for unsupported context types or missing string names.
    """
    typename = context.get("__typename")
    if typename == "CheckRun":
        return _check_run_state(context)
    if typename == "StatusContext":
        return _status_context_state(context)
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
    if author.get("__typename") != "Bot":
        return login
    if not login or login.endswith("[bot]"):
        return login
    return f"{login}[bot]"


def _require_identity(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw PR's identity fields; return its author mapping.

    Raise OSError for a non-mapping author, a non-string login or body, or
    malformed number/url/isDraft fields. A null author normalizes to {}.
    """
    author = _require_author(raw)
    _require_str(author.get("login"), "malformed pull request author")
    _require_str(raw.get("body"), "malformed pull request body")
    if not _valid_identity_fields(raw):
        raise OSError("malformed pull request identity")
    return author


def _require_author(raw: dict[str, Any]) -> dict[str, Any]:
    """Return the author mapping, raising OSError for a non-mapping value."""
    author = raw.get("author")
    if author is not None and not isinstance(author, dict):
        raise OSError("malformed pull request author")
    return author or {}


def _require_str(value: Any, error: str) -> None:
    """Raise OSError when a field is present but not a string."""
    if value is not None and not isinstance(value, str):
        raise OSError(error)


def _valid_identity_fields(raw: dict[str, Any]) -> bool:
    """Require a positive int number, an https url, and a boolean isDraft."""
    number = raw.get("number")
    url = raw.get("url")
    return (
        isinstance(number, int)
        and not isinstance(number, bool)
        and number >= 1
        and isinstance(url, str)
        and url.startswith("https://")
        and isinstance(raw.get("isDraft"), bool)
    )


def _normalize_reviews(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Return latestReviews nodes as {author.login, state} dicts."""
    return [
        {
            "author": {"login": _author_login(review.get("author"))},
            "state": review.get("state"),
        }
        for review in _nodes(raw.get("latestReviews"), "latestReviews")
    ]


def _nonneg_int(value: Any) -> bool:
    """Require a non-negative int value (bool excluded)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


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
    return comments, total if _nonneg_int(total) else None


def _checks_truncated(connection: Any) -> bool:
    """True when the contexts pageInfo is absent or reports a next page."""
    page_info = connection.get("pageInfo") if isinstance(connection, dict) else None
    if isinstance(page_info, dict) and isinstance(page_info.get("hasNextPage"), bool):
        return page_info["hasNextPage"]
    return True


def _normalized_commit(commit: Any) -> list[dict[str, Any]]:
    """Return the single-commit normalized list, raising on malformed input."""
    if not isinstance(commit, dict):
        raise OSError("malformed commit")
    commit_author = commit.get("author") or {}
    if not isinstance(commit_author, dict):
        raise OSError("malformed commit author")
    return [{"commit": {"author": {"email": commit_author.get("email")}}}]


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
        return [], [dict(_TRUNCATED_CHECK)], True
    commit = commits[-1].get("commit")
    normalized_commits = _normalized_commit(commit)
    rollup = commit.get("statusCheckRollup")
    if rollup is None:
        return normalized_commits, [dict(_TRUNCATED_CHECK)], True
    if not isinstance(rollup, dict):
        raise OSError("malformed statusCheckRollup")
    checks, checks_incomplete = _rollup_checks(rollup)
    return normalized_commits, checks, checks_incomplete


def _rollup_checks(rollup: dict[str, Any]) -> tuple[list[dict[str, str]], bool]:
    """Return (normalized checks, checks_incomplete) from a statusCheckRollup."""
    connection = rollup.get("contexts")
    checks_incomplete = _checks_truncated(connection)
    checks: list[dict[str, str]] = []
    if isinstance(connection, dict):
        for context in _nodes(connection, "status check contexts"):
            normalized = _check_state(context)
            if normalized is not None:
                checks.append({"name": normalized[0], "state": normalized[1]})
    if checks_incomplete:
        checks.append(dict(_TRUNCATED_CHECK))
    return checks, checks_incomplete


def _normalized_author(author: dict[str, Any]) -> dict[str, Any]:
    """Return the normalized author mapping, marking Bot typenames."""
    normalized = {"login": _author_login(author)}
    if author.get("__typename") == "Bot":
        normalized["type"] = "Bot"
    return normalized


def _base_fields(raw: dict[str, Any], repository: str) -> dict[str, Any]:
    """Return the normalized PR's scalar and repository fields."""
    return {
        "number": raw.get("number"),
        "url": raw.get("url"),
        "title": raw.get("title") or "",
        "body": str(raw.get("body") or "")[:2000],
        "isDraft": bool(raw.get("isDraft")),
        "headRefName": raw.get("headRefName") or "",
        "headRefOid": raw.get("headRefOid") or "",
        "baseRefName": raw.get("baseRefName") or "",
        "baseRefOid": raw.get("baseRefOid") or "",
        "mergeable": raw.get("mergeable"),
        "mergeStateStatus": raw.get("mergeStateStatus"),
        "reviewDecision": raw.get("reviewDecision"),
        "createdAt": raw.get("createdAt"),
        "updatedAt": raw.get("updatedAt"),
        "repository": repository,
    }


def _validate_pr_fields(normalized_pr: dict[str, Any]) -> None:
    """Require the branch/ref string fields, raising OSError when malformed."""
    string_keys = ("title", "headRefName", "headRefOid", "baseRefName", "baseRefOid")
    if not all(isinstance(normalized_pr[key], str) for key in string_keys):
        raise OSError("malformed pull request fields")


def _normalize_pr(raw: dict[str, Any], repository: str) -> dict[str, Any]:
    """Validate and normalize a GraphQL PR for identity and blocker routing.

    Raise OSError for malformed fields. Mark incomplete check rollups as
    pending and preserve unknown comment counts so callers fail closed.
    """
    normalized_pr = _base_fields(raw, repository)
    normalized_pr["author"] = _normalized_author(_require_identity(raw))
    comments, comments_total_count = _normalize_comments(raw)
    commits, checks, checks_incomplete = _commit_checks(raw)
    normalized_pr.update(
        {
            "latestReviews": _normalize_reviews(raw),
            "comments": comments,
            "commentsTotalCount": comments_total_count,
            "commits": commits,
            "checks": checks,
            "checksIncomplete": checks_incomplete,
        }
    )
    _validate_pr_fields(normalized_pr)
    return normalized_pr


def _split_repo(repo: str) -> tuple[str, str]:
    """Split owner/name, raising OSError for anything else."""
    try:
        owner, name = repo.split("/", 1)
        if not owner:
            raise ValueError("repository must be owner/name")
        if not name:
            raise ValueError("repository must be owner/name")
        if "/" in name:
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


def _all_transient(errors: Any) -> bool:
    """True only for a non-empty list of transient GraphQL errors."""
    return (
        isinstance(errors, list)
        and bool(errors)
        and all(_is_transient_gql_error(err) for err in errors)
    )


def _transient_errors(payload: Any) -> list[Any] | None:
    """Return the all-transient errors list, or None when the payload has none.

    Raise OSError when a GraphQL errors payload is not fully transient.
    """
    if not (isinstance(payload, dict) and "errors" in payload):
        return None
    errors = payload["errors"]
    if not _all_transient(errors):
        raise OSError("gh api graphql returned an API error")
    return errors


def _parse_payload(stdout: str) -> tuple[OSError | None, Any]:
    """Return (None, decoded JSON) or (OSError, None) for invalid JSON."""
    try:
        return None, json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        return OSError(f"gh api graphql returned invalid JSON: {exc}"), None


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
    error, payload = _parse_payload(result.stdout)
    if error is not None:
        return error, None
    errors = _transient_errors(payload)
    if errors is None:
        return None, payload
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


def _conn_parts(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract (pullRequests connection, pageInfo); raise on bad shape."""
    try:
        connection = payload["data"]["repository"]["pullRequests"]
        page_info = connection["pageInfo"]
    except (KeyError, TypeError, AttributeError) as exc:
        raise OSError("gh api graphql returned a malformed payload") from exc
    if not isinstance(page_info.get("hasNextPage"), bool):
        raise OSError("gh api graphql returned a malformed payload")
    return connection, page_info


def _page_connection(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (pullRequests connection, pageInfo); raise on a bad payload."""
    if not isinstance(payload, dict):
        raise OSError("gh api graphql returned a malformed payload")
    if "errors" in payload:
        raise OSError("gh api graphql returned an API error")
    return _conn_parts(payload)


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
