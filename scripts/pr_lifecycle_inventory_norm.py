"""Field normalization for open-PR inventory.

Raw GraphQL pullRequest nodes become validated, normalized dicts. Pure
functions only — no GitHub or subprocess calls live here.
"""

from __future__ import annotations

from typing import Any

from pr_lifecycle_inventory_checks import _commit_checks, _nodes


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
        "isCrossRepository": bool(raw.get("isCrossRepository")),
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
