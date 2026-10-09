"""Decision-issue checkbox dispositions with editor and head verification."""

# Each decision row renders as a task-list checkbox carrying a suggested
# disposition and the head SHA the row was rendered against. abhimehro ticks a
# checkbox (optionally editing the backticked disposition token) to execute it.
# Ticks are honored only when every recorded body editor is abhimehro and the
# live head still matches the rendered head. Every executed disposition goes
# through apply_action_to_ledger so it lands as a ledger event.

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
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
    " userContentEdits(first: 100) { nodes { editor { login } } } } } }"
)


def parse_ticks(body: str) -> list[dict[str, Any]]:
    """Extract ticked decision rows: row id plus an optional edited token."""
    ticks: list[dict[str, Any]] = []
    for line in str(body or "").splitlines():
        match = _TICK_RE.match(line.strip())
        if match:
            tokens = _TOKEN_RE.findall(line)
            ticks.append(
                {"row_id": match.group(1), "token": tokens[-1] if tokens else None}
            )
    return ticks


def editors(repo: str, number: int, *, run: Any = subprocess.run) -> set[str] | None:
    """Return every recorded body editor login, or None on any failure."""
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
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    issue = ((data.get("data") or {}).get("repository") or {}).get("issue") or {}
    nodes = (issue.get("userContentEdits") or {}).get("nodes") or []
    return {(node.get("editor") or {}).get("login") for node in nodes} - {None}


def _find_item(ledger: dict[str, Any], repo: str, pr_num: Any) -> dict[str, Any] | None:
    """Return the nonterminal ledger item for repo#pr, preferring the newest."""
    candidates = [
        item
        for item in ledger.get("items") or []
        if isinstance(item, dict)
        and item.get("repository") == repo
        and item.get("pr") == pr_num
        and item.get("lifecycle_state") != "TERMINAL"
    ]
    candidates.sort(key=lambda i: (int(i.get("revision") or 0)), reverse=True)
    return candidates[0] if candidates else None


def _close_pr(repo: str, pr_num: Any, run: Any) -> bool:
    """Close a still-open PR; returns True when it ends up closed."""
    proc = run(
        ["gh", "pr", "close", str(pr_num), "--repo", repo],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return not proc.returncode


@dataclass(frozen=True)
class _TickCtx:
    """One verified tick plus the ledger item and execution context."""

    tick: dict[str, Any]
    meta: dict[str, Any]
    item: dict[str, Any]
    ledger: dict[str, Any]
    run: Any


def _resolve_action(ctx: _TickCtx, base: dict[str, Any], live: dict[str, Any]) -> dict:
    """Map a verified disposition to its ledger action or a skip record."""
    disposition = base["disposition"]
    if disposition == "KEEP_OPEN":
        return {
            **{k: v for k, v in base.items() if k != "disposition"},
            "to_state": "WAITING_HUMAN",
            "reason": "human disposition KEEP_OPEN via decision issue",
        }
    if disposition not in _DISPOSITIONS:
        return {**base, "skipped": "unknown disposition"}
    if live.get("state") != "CLOSED" and not _close_pr(
        base["repository"], base["pr"], ctx.run
    ):
        return {**base, "skipped": "gh pr close failed"}
    return {
        **base,
        "to_state": "TERMINAL",
        "reason": f"human disposition {disposition} via decision issue",
    }


def _tick_to_action(ctx: _TickCtx) -> dict[str, Any]:
    """Apply one verified tick and return its action record."""
    repo, _, pr_text = ctx.tick["row_id"].partition("#")
    base = {
        "action": "EXECUTE_DISPOSITION",
        "repository": repo,
        "pr": int(pr_text),
        "key": ctx.item["key"],
        "disposition": ctx.tick.get("token") or ctx.meta.get("suggested_disposition"),
    }
    live = _gh_pr_view(repo, int(pr_text))
    if not live or str(live.get("headRefOid") or "") != str(
        ctx.meta.get("head_sha") or ""
    ):
        return {**base, "skipped": "head moved since rendered"}
    action = _resolve_action(ctx, base, live)
    if "to_state" not in action:
        return action
    event = apply_action_to_ledger(ctx.ledger, ctx.item, action)
    return {**action, "event_id": event.get("event_id"), "executed": True}


def _process_tick(tick: dict[str, Any], ctx: "_ExecCtx") -> dict[str, Any]:
    """Resolve one tick to an executed or skipped outcome record."""
    repo_part, _, pr_part = tick["row_id"].partition("#")
    meta = (ctx.state.get("rows_meta") or {}).get(tick["row_id"])
    try:
        item = _find_item(ctx.ledger, repo_part, int(pr_part or 0))
    except ValueError:
        item = None
    if meta is None or item is None:
        return {**tick, "skipped": "unknown row"}
    return _tick_to_action(_TickCtx(tick, meta, item, ctx.ledger, ctx.run))


@dataclass(frozen=True)
class _ExecCtx:
    """Inputs for one repository's tick execution pass."""

    repo: str
    issue: dict[str, Any]
    ledger: dict[str, Any]
    state: dict[str, Any]
    run: Any


def execute(ctx: _ExecCtx) -> dict[str, Any]:
    """Execute verified decision-issue ticks for one repository."""
    # Returns {"accepted": [...], "skipped": [...], "reason": ...}; the ledger
    # is mutated in place via apply_action_to_ledger for each accepted tick.
    number = ctx.issue.get("number")
    if not isinstance(number, int):
        return {"accepted": [], "skipped": [], "reason": "no decision issue"}
    logins = editors(ctx.repo, number, run=ctx.run)
    if logins is None:
        return {"accepted": [], "skipped": [], "reason": "editor history unreadable"}
    if not logins or logins - _ALLOWED_EDITORS:
        return {
            "accepted": [],
            "skipped": [],
            "reason": f"body editors {sorted(logins)!r} not abhimehro-only",
        }
    outcomes = [
        _process_tick(tick, ctx) for tick in parse_ticks(ctx.issue.get("body") or "")
    ]
    return {
        "accepted": [o for o in outcomes if o.get("executed")],
        "skipped": [o for o in outcomes if not o.get("executed")],
    }
