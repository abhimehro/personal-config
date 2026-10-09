"""gh api graphql transport: repo query text, retry, and page execution."""

from __future__ import annotations

import re
from typing import Any

_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 50, states: OPEN, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number url title body isDraft isCrossRepository headRefName headRefOid baseRefName baseRefOid
        author { login __typename }
        mergeable mergeStateStatus reviewDecision createdAt updatedAt
        latestReviews(first: 20) { nodes { author { login __typename } state } }
        comments(last: 50) { totalCount nodes { author { login __typename } body createdAt } }
        reviewThreads(first: 50) {
          pageInfo { hasNextPage }
          nodes {
            isResolved isOutdated
            comments(first: 1) { nodes { author { login __typename } } }
          }
        }
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


def _graphql_command(owner: str, name: str, cursor: str | None) -> list[str]:
    """Build the gh api graphql argv for one pullRequests page."""
    command = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={_QUERY}",
        "-f",
        f"owner={owner}",
        "-f",
        f"name={name}",
    ]
    if cursor is not None:
        command.extend(["-f", f"cursor={cursor}"])
    return command
