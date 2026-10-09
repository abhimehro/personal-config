"""Decision-issue body editor history: GraphQL fetch plus truncation gate."""

import json
import subprocess
from typing import Any

_EDITOR_QUERY = (
    "query($owner: String!, $name: String!, $number: Int!) {"
    " repository(owner: $owner, name: $name) {"
    " issue(number: $number) {"
    " userContentEdits(first: 100) { totalCount nodes { editor { login } } } } } }"
)


def _graphql_stdout(repo: str, number: int, run: Any) -> str | None:
    """Run the editor-history GraphQL query; None on nonzero exit."""
    owner, _, name = repo.partition("/")
    proc = run(
        [
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
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode:
        return None
    return proc.stdout or ""


def _graphql_json(repo: str, number: int, run: Any) -> dict[str, Any] | None:
    """Fetch the editor-history payload, or None on transport/parse failure."""
    stdout = _graphql_stdout(repo, number, run)
    if stdout is None:
        return None
    try:
        data = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _editor_nodes(repo: str, number: int, run: Any) -> list[Any] | None:
    """Fetch raw userContentEdits nodes, or None on any failure."""
    # A truncated edit history is not the whole gate: refuse when the API
    # reports more edits than the 100-node window returned.
    data = _graphql_json(repo, number, run)
    if data is None:
        return None
    issue = ((data.get("data") or {}).get("repository") or {}).get("issue") or {}
    edits = issue.get("userContentEdits") or {}
    nodes = edits.get("nodes") or []
    total = edits.get("totalCount")
    if isinstance(total, int) and total > len(nodes):
        return None
    return nodes


def _editor_login(node: Any) -> str | None:
    """Return one edit node's editor login, or None when absent."""
    if not isinstance(node, dict):
        return None
    editor = node.get("editor")
    if not isinstance(editor, dict):
        return None
    login = editor.get("login")
    return login if isinstance(login, str) else None


def editors(repo: str, number: int, *, run: Any = subprocess.run) -> set[str] | None:
    """Return every recorded body editor login, or None on any failure."""
    nodes = _editor_nodes(repo, number, run)
    if nodes is None:
        return None
    return {login for node in nodes if (login := _editor_login(node))}
