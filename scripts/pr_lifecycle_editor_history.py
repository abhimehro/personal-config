"""Decision-issue body editor history: GraphQL fetch plus truncation gate."""

import json
from typing import Any

__all__ = ["editors"]

_EDITOR_QUERY = (
    "query($owner: String!, $name: String!, $number: Int!, $cursor: String) {"
    " repository(owner: $owner, name: $name) {"
    " issue(number: $number) {"
    " userContentEdits(first: 100, after: $cursor) {"
    " pageInfo { hasNextPage endCursor } nodes { editor { login } } } } } }"
)


def _graphql_stdout(
    repo: str, number: int, run: Any, cursor: str | None = None
) -> str | None:
    """Run the editor-history GraphQL query; None on nonzero exit."""
    owner, _, name = repo.partition("/")
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={_EDITOR_QUERY}",
        "-f",
        f"owner={owner}",
        "-f",
        f"name={name}",
        "-F",
        f"number={number}",
    ]
    if cursor:
        cmd += ["-f", f"cursor={cursor}"]
    proc = run(cmd, capture_output=True, text=True, check=False, timeout=30)
    if proc.returncode:
        return None
    return proc.stdout or ""


def _graphql_json(
    repo: str, number: int, run: Any, cursor: str | None = None
) -> dict[str, Any] | None:
    """Fetch the editor-history payload, or None on transport/parse failure."""
    stdout = _graphql_stdout(repo, number, run, cursor)
    if stdout is None:
        return None
    try:
        data = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _nested(value: Any, *keys: str) -> Any:
    """Walk nested dict keys; None when any level is not a dict."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _edit_page(
    repo: str, number: int, run: Any, cursor: str | None
) -> dict[str, Any] | None:
    """Fetch one userContentEdits page, or None on any failure."""
    data = _graphql_json(repo, number, run, cursor)
    if not isinstance(data, dict):
        return None
    edits = _nested(data, "data", "repository", "issue", "userContentEdits")
    return edits if isinstance(edits, dict) else None


def _editor_nodes(repo: str, number: int, run: Any) -> list[Any] | None:
    """Fetch every userContentEdits node across pages; None on any failure."""
    # The decision-issue body is edited by the automation on every apply run,
    # so the history grows past a single 100-node page over time: paginate to
    # the end and only refuse when a page or its cursor is missing.
    nodes: list[Any] = []
    cursor: str | None = None
    while True:
        edits = _edit_page(repo, number, run, cursor)
        if edits is None:
            return None
        nodes.extend(edits.get("nodes") or [])
        info = edits.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return nodes
        cursor = info.get("endCursor")
        if not cursor:
            return None


def _editor_login(node: Any) -> str | None:
    """Return one edit node's editor login, or None when absent."""
    if not isinstance(node, dict):
        return None
    editor = node.get("editor")
    if not isinstance(editor, dict):
        return None
    login = editor.get("login")
    return login if isinstance(login, str) else None


def editors(repo: str, number: int, *, run: Any) -> set[str] | None:
    """Return every recorded body editor login, or None on any failure."""
    nodes = _editor_nodes(repo, number, run)
    if nodes is None:
        return None
    return {login for node in nodes if (login := _editor_login(node))}
