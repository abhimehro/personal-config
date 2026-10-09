"""Human disposition ticks on the per-repo decision issue.

Each open decision row renders as a task-list checkbox carrying a suggested
disposition and the head SHA the row was rendered against. abhimehro ticks a
checkbox (optionally editing the backticked disposition token) to execute it.
Edits by anyone else are ignored, and ticks are ignored when the PR's live
head no longer matches the rendered head. Every executed disposition is
applied through the shared transition path so it lands as a ledger event.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from pr_lifecycle_reconcile import _gh_pr_view, apply_action_to_ledger

_ALLOWED_EDITORS = {"abhimehro"}
_DISPOSITIONS = {
    "CLOSED_NOOP",
    "CLOSED_DUPLICATE",
    "CLOSED_STALE",
    "CLOSED_SUPERSEDED",
    "CLOSED_UNREVIEWED",
    "KEEP_OPEN",
}
_TICK_RE = re.compile(r"^-\s*\[[xX]\]\s*\*\*([^*\s]+)\*\*")
_TOKEN_RE = re.compile(r"`([A-Z][A-Z0-9_]+)`")
_EDITOR_QUERY = (
    "query($owner: String!, $name: String!, $number: Int!) {"
    " repository(owner: $owner, name: $name) {"
    " issue(number: $number) {"
    " userContentEdits(last: 1) { nodes { editor { login } } } } } }"
)


def parse_ticks(body: str) -> list[dict[str, Any]]:
    """Extract ticked decision rows: row id plus an optional edited token."""
    ticks: list[dict[str, Any]] = []
    for line in str(body or "").splitlines():
        match = _TICK_RE.match(line.strip())
        if match:
            tokens = _TOKEN_RE.findall(line)
            ticks.append({"row_id": match.group(1), "token": tokens[-1] or None})
    return ticks


def latest_editor(repo: str, number: int, *, run: Any = subprocess.run) -> str | None:
    """Return the login of the issue body's most recent editor, or None."""
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
    if proc.returncode != 0:
        return None
    nodes = (
        json.loads(proc.stdout or "{}")
        .get("data", {})
        .get("repository", {})
        .get("issue", {})
        .get("userContentEdits", {})
        .get("nodes", [])
    )
    return nodes[-1].get("editor", {}).get("login") if nodes else None


def _find_item(ledger: dict[str, Any], repo: str, pr: Any) -> dict[str, Any] | None:
    """Return the nonterminal ledger item for repo#pr, preferring the newest."""
    candidates = [
        item
        for item in ledger.get("items") or []
        if isinstance(item, dict)
        and item.get("repository") == repo
        and item.get("pr") == pr
        and item.get("lifecycle_state") != "TERMINAL"
    ]
    candidates.sort(key=lambda i: (int(i.get("revision") or 0)), reverse=True)
    return candidates[0] if candidates else None


def _close_pr(repo: str, pr: Any, run: Any) -> bool:
    """Close a still-open PR; returns True when it ends up closed."""
    proc = run(
        ["gh", "pr", "close", str(pr), "--repo", repo],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return proc.returncode == 0


def _tick_to_action(
    tick: dict[str, Any],
    meta: dict[str, Any],
    item: dict[str, Any],
    ledger: dict[str, Any],
    *,
    run: Any,
) -> dict[str, Any]:
    """Apply one verified tick and return its action record."""
    repo, _, pr_text = tick["row_id"].partition("#")
    pr = int(pr_text)
    disposition = tick.get("token") or meta.get("suggested_disposition")
    live = _gh_pr_view(repo, pr)
    head = str(meta.get("head_sha") or "")
    base = {
        "action": "EXECUTE_DISPOSITION",
        "repository": repo,
        "pr": pr,
        "key": item["key"],
        "disposition": disposition,
    }
    if not live or str(live.get("headRefOid") or "") != head:
        return {**base, "skipped": "head moved since rendered"}
    if disposition == "KEEP_OPEN":
        action = {
            **{k: v for k, v in base.items() if k != "disposition"},
            "to_state": "WAITING_HUMAN",
            "reason": "human disposition KEEP_OPEN via decision issue",
        }
    elif disposition in _DISPOSITIONS:
        closed = live.get("state") == "CLOSED" or _close_pr(repo, pr, run)
        if not closed:
            return {**base, "skipped": "gh pr close failed"}
        action = {
            **base,
            "to_state": "TERMINAL",
            "reason": f"human disposition {disposition} via decision issue",
        }
    else:
        return {**base, "skipped": "unknown disposition"}
    event = apply_action_to_ledger(ledger, item, action)
    return {**action, "event_id": event.get("event_id"), "executed": True}


def execute(
    repo: str,
    issue: dict[str, Any],
    ledger: dict[str, Any],
    state: dict[str, Any],
    *,
    run: Any = subprocess.run,
) -> dict[str, Any]:
    """Execute verified decision-issue ticks for one repository.

    Returns {"accepted": [...], "skipped": [...], "reason": ...}; the ledger
    is mutated in place via apply_action_to_ledger for each accepted tick.
    """
    number = issue.get("number")
    if not isinstance(number, int):
        return {"accepted": [], "skipped": [], "reason": "no decision issue"}
    editor = latest_editor(repo, number, run=run)
    if editor not in _ALLOWED_EDITORS:
        return {
            "accepted": [],
            "skipped": [],
            "reason": f"latest body editor {editor!r} not abhimehro",
        }
    rows_meta = state.get("rows_meta") or {}
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for tick in parse_ticks(issue.get("body") or ""):
        repo_part, _, pr_part = tick["row_id"].partition("#")
        meta = rows_meta.get(tick["row_id"])
        try:
            item = _find_item(ledger, repo_part, int(pr_part or 0))
        except ValueError:
            item = None
        if meta is None or item is None:
            skipped.append({**tick, "skipped": "unknown row"})
            continue
        outcome = _tick_to_action(tick, meta, item, ledger, run=run)
        (accepted if outcome.get("executed") else skipped).append(outcome)
    return {"accepted": accepted, "skipped": skipped}
