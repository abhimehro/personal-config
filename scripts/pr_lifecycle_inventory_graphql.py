"""GraphQL transport and pagination for open-PR inventory.

Repo-name parsing, page queries, transient-error retry, and payload plumbing.
The only module here that shells out (gh api graphql via an injectable runner).
"""

from __future__ import annotations

import re
import subprocess
import time
from typing import Any

from pr_lifecycle_inventory_checks import _nodes
from pr_lifecycle_inventory_norm import _normalize_pr
from pr_lifecycle_inventory_pages import _graphql_page
from pr_lifecycle_inventory_transport import _graphql_command

_REPO_RE = re.compile(r"^[^/]+/[^/]+$")


def _split_repo(repo: str) -> tuple[str, str]:
    """Split owner/name, raising OSError for anything else."""
    if not isinstance(repo, str) or _REPO_RE.fullmatch(repo) is None:
        raise OSError("invalid repository")
    owner, name = repo.split("/", 1)
    return owner, name


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
