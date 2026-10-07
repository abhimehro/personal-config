"""GraphQL transport and pagination for open-PR inventory.

Repo-name parsing, page queries, transient-error retry, and payload plumbing.
The only module here that shells out (gh api graphql via an injectable runner).
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

from pr_lifecycle_inventory_checks import _nodes
from pr_lifecycle_inventory_norm import _normalize_pr

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


_REPO_RE = re.compile(r"^[^/]+/[^/]+$")


def _split_repo(repo: str) -> tuple[str, str]:
    """Split owner/name, raising OSError for anything else."""
    if not isinstance(repo, str) or _REPO_RE.fullmatch(repo) is None:
        raise OSError("invalid repository")
    owner, name = repo.split("/", 1)
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
        if not _usable_cursor(cursor, seen_cursors):
            raise OSError("gh api graphql returned a malformed payload")
        seen_cursors.add(cursor)


def _usable_cursor(value: Any, seen: set[str]) -> bool:
    """Require a fresh non-empty string cursor."""
    return isinstance(value, str) and bool(value) and value not in seen
